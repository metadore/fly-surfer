"""LIF membrane integration, threshold, reset and refractory behaviour."""

from __future__ import annotations

import numpy as np
import pytest

from brain.neuron_model import LIFParameters, LIFPopulation


def default_params(**overrides) -> LIFParameters:
    values = dict(
        capacitance_pf=200.0,
        leak_conductance_ns=10.0,
        resting_potential_mv=-65.0,
        threshold_mv=-50.0,
        reset_potential_mv=-68.0,
        refractory_ms=2.0,
        initial_potential_mv=-65.0,
        minimum_potential_mv=-90.0,
    )
    values.update(overrides)
    return LIFParameters.from_config(values)


def test_parameters_derived_values() -> None:
    params = default_params()
    assert params.tau_m_ms == pytest.approx(20.0)
    assert params.rheobase_pa == pytest.approx(150.0)


def test_parameter_validation() -> None:
    with pytest.raises(ValueError):
        default_params(threshold_mv=-70.0)
    with pytest.raises(ValueError):
        default_params(refractory_ms=-1.0)
    with pytest.raises(ValueError):
        default_params(capacitance_pf=0.0)
    with pytest.raises(ValueError):
        default_params(minimum_potential_mv=-60.0)
    with pytest.raises(ValueError):
        LIFPopulation(0, default_params(), 0.5)
    with pytest.raises(ValueError):
        LIFPopulation(1, default_params(), 0.0)


def test_passive_decay_matches_analytic_solution() -> None:
    params = default_params()
    dt = 0.5
    population = LIFPopulation(1, params, dt)
    population.reset(initial_potential_mv=-70.0)
    steps = 40  # 20 ms, exactly one membrane time constant
    for _ in range(steps):
        assert population.step(0.0).size == 0
    expected = params.resting_potential_mv + (
        -70.0 - params.resting_potential_mv
    ) * np.exp(-steps * dt / params.tau_m_ms)
    assert population.membrane_potential[0] == pytest.approx(expected, abs=1e-10)


def test_subthreshold_current_reaches_steady_state_without_spiking() -> None:
    params = default_params()
    population = LIFPopulation(1, params, 0.5)
    current = 100.0
    for _ in range(2000):  # 1000 ms
        population.step(current)
    assert population.spike_count == 0
    assert population.membrane_potential[0] == pytest.approx(
        population.steady_state_potential(current), abs=1e-6
    )


def test_suprathreshold_current_spikes_at_expected_timestep() -> None:
    params = default_params()
    dt = 0.5
    population = LIFPopulation(1, params, dt)
    first_step = None
    for step in range(100):
        if population.step(200.0).size:
            first_step = step
            break
    assert first_step is not None
    steady_state = params.resting_potential_mv + 200.0 / params.leak_conductance_ns
    analytic_ms = params.tau_m_ms * np.log(
        (steady_state - params.resting_potential_mv)
        / (steady_state - params.threshold_mv)
    )
    assert (first_step + 1) * dt == pytest.approx(
        np.ceil(analytic_ms / dt) * dt, abs=1e-9
    )


def test_threshold_crossing_resets_membrane() -> None:
    params = default_params()
    population = LIFPopulation(1, params, 0.5)
    for _ in range(100):
        spikes = population.step(4000.0)
        if spikes.size:
            assert spikes.tolist() == [0]
            assert population.membrane_potential[0] == params.reset_potential_mv
            return
    pytest.fail("neuron never crossed threshold")


def test_refractory_period_blocks_consecutive_spikes() -> None:
    params = default_params()
    dt = 0.5
    population = LIFPopulation(1, params, dt)
    spike_steps: list[int] = []
    for step in range(200):
        if population.step(4000.0).size:
            spike_steps.append(step)
    assert len(spike_steps) >= 3
    assert population.effective_refractory_ms == pytest.approx(2.0)
    intervals_ms = np.diff(spike_steps) * dt
    assert np.all(intervals_ms >= population.effective_refractory_ms - 1e-9)


def test_minimum_potential_floor_limits_hyperpolarization() -> None:
    params = default_params()
    population = LIFPopulation(1, params, 0.5)
    for _ in range(100):
        population.step(-10_000.0)
    assert population.membrane_potential[0] == pytest.approx(
        params.minimum_potential_mv
    )


def test_population_is_vectorised() -> None:
    params = default_params()
    population = LIFPopulation(3, params, 0.5)
    currents = np.array([0.0, 100.0, 4000.0])
    for _ in range(40):
        population.step(currents)
    assert population.membrane_potential[0] == pytest.approx(-65.0)
    assert -65.0 < population.membrane_potential[1] < params.threshold_mv
    assert population.spike_count > 0


def test_memory_bytes_reports_persistent_state() -> None:
    population = LIFPopulation(10, default_params(), 0.5)
    expected = 10 * np.dtype(np.float64).itemsize + 10 * np.dtype(
        np.int32
    ).itemsize
    assert population.memory_bytes == expected


def test_current_shape_is_validated() -> None:
    population = LIFPopulation(2, default_params(), 0.5)
    with pytest.raises(ValueError):
        population.step(np.zeros(3))


def test_reset_restores_initial_state() -> None:
    population = LIFPopulation(2, default_params(), 0.5)
    for _ in range(20):
        population.step(1000.0)
    assert population.spike_count > 0
    population.reset()
    assert population.spike_count == 0
    assert np.all(population.membrane_potential == -65.0)
    assert np.all(population.refractory_steps == 0)
