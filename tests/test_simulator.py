"""End-to-end simulation: stimulation, propagation, determinism, saving."""

from __future__ import annotations

import json

import numpy as np
import pytest

from brain.brain_simulator import BrainSimulator, Stimulus
from brain.neuron_model import LIFParameters, LIFPopulation
from brain.synapse_model import SynapseParameters


def neuron_params() -> LIFParameters:
    return LIFParameters.from_config(
        {
            "capacitance_pf": 200.0,
            "leak_conductance_ns": 10.0,
            "resting_potential_mv": -65.0,
            "threshold_mv": -50.0,
            "reset_potential_mv": -68.0,
            "refractory_ms": 2.0,
            "initial_potential_mv": -65.0,
        }
    )


def synapse_params(**overrides) -> SynapseParameters:
    values = dict(
        weight_transform="linear",
        weight_scale_pa_per_synapse=1.0,
        weight_exponent=0.75,
        tau_exc_ms=5.0,
        tau_inh_ms=8.0,
        delay_ms=1.0,
    )
    values.update(overrides)
    return SynapseParameters(**values)


def test_stimulus_validation() -> None:
    with pytest.raises(ValueError):
        Stimulus(indices=np.array([], dtype=np.int64), current_pa=1.0,
                 start_ms=0.0, end_ms=1.0)
    with pytest.raises(ValueError):
        Stimulus(indices=np.array([0]), current_pa=1.0,
                 start_ms=2.0, end_ms=1.0)
    with pytest.raises(ValueError):
        Stimulus(indices=np.array([0]), current_pa=1.0,
                 start_ms=-1.0, end_ms=1.0)


def test_stimulated_neuron_matches_standalone_lif(graph_factory) -> None:
    graph = graph_factory(2, [])
    stimulus = Stimulus(
        indices=np.array([0]), current_pa=4000.0, start_ms=0.0, end_ms=20.0
    )
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5,
        duration_ms=20.0, seed=1, stimulus=stimulus,
    )
    result = simulator.run(progress=False)

    reference = LIFPopulation(2, neuron_params(), 0.5)
    expected_steps: list[int] = []
    for step in range(40):
        if reference.step(np.array([4000.0, 0.0])).size:
            expected_steps.append(step)
    assert result.recorder.n_spikes == reference.spike_count == len(expected_steps)
    assert np.all(result.recorder.spike_neuron_indices == 0)
    expected_times = [(step + 1) * 0.5 for step in expected_steps]
    assert result.recorder.spike_times_ms.tolist() == pytest.approx(expected_times)


def test_no_input_produces_no_spikes(graph_factory) -> None:
    graph = graph_factory(5, [(0, 1, 10), (1, 2, 10)])
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5,
        duration_ms=100.0, seed=0,
    )
    result = simulator.run(progress=False)
    assert result.recorder.n_spikes == 0
    assert result.summary["activity"]["active_neurons"] == 0
    assert result.summary["activity_by_stimulation"]["stimulated_neurons"] == 0
    assert result.summary["activity_by_stimulation"]["non_stimulated_spikes"] == 0


def test_synaptic_input_recruits_postsynaptic_neuron(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 200)], nt_codes=np.array([0, 0]))
    stimulus = Stimulus(
        indices=np.array([0]), current_pa=4000.0, start_ms=0.0, end_ms=20.0
    )
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5,
        duration_ms=60.0, seed=0, stimulus=stimulus,
    )
    result = simulator.run(progress=False)
    indices = result.recorder.spike_neuron_indices
    times = result.recorder.spike_times_ms
    assert np.count_nonzero(indices == 0) > 0
    assert np.count_nonzero(indices == 1) > 0
    assert times[indices == 1].min() > times[indices == 0].min()
    assert result.summary["synapses"]["spike_transmissions"] > 0
    breakdown = result.summary["activity_by_stimulation"]
    assert breakdown["stimulated_active_neurons"] == 1
    assert breakdown["non_stimulated_active_neurons"] == 1
    assert breakdown["non_stimulated_spikes"] > 0


def test_runs_are_reproducible_with_the_same_seed(graph_factory) -> None:
    graph = graph_factory(4, [(0, 1, 20), (1, 2, 20), (2, 3, 20), (3, 1, 20)])
    stimulus = Stimulus(
        indices=np.array([0]), current_pa=2500.0, start_ms=0.0, end_ms=30.0
    )
    def run_once():
        simulator = BrainSimulator(
            graph, neuron_params(), synapse_params(), dt_ms=0.5,
            duration_ms=50.0, seed=99, stimulus=stimulus,
        )
        return simulator.run(progress=False)

    first, second = run_once(), run_once()
    assert np.array_equal(
        first.recorder.spike_times_ms, second.recorder.spike_times_ms
    )
    assert np.array_equal(
        first.recorder.spike_neuron_indices, second.recorder.spike_neuron_indices
    )


def test_noise_is_reproducible_for_a_fixed_seed(graph_factory) -> None:
    graph = graph_factory(1, [])
    def run_once():
        simulator = BrainSimulator(
            graph, neuron_params(), synapse_params(), dt_ms=0.5,
            duration_ms=200.0, seed=123, background_current_pa=170.0,
            noise_std_pa=20.0,
        )
        return simulator.run(progress=False)

    first, second = run_once(), run_once()
    assert first.recorder.n_spikes > 0
    assert np.array_equal(
        first.recorder.spike_times_ms, second.recorder.spike_times_ms
    )


def test_result_saves_activity_and_metadata(graph_factory, tmp_path) -> None:
    graph = graph_factory(1, [])
    stimulus = Stimulus(
        indices=np.array([0]), current_pa=4000.0, start_ms=0.0, end_ms=20.0
    )
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5,
        duration_ms=20.0, seed=5, stimulus=stimulus,
    )
    result = simulator.run(progress=False)
    paths = result.save(tmp_path)
    assert (tmp_path / "activity.npz").exists()
    assert (tmp_path / "simulation_metadata.json").exists()
    metadata = json.loads(
        (tmp_path / "simulation_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["graph"]["n_nodes"] == 1
    assert metadata["simulation"]["n_steps"] == 40
    assert metadata["stimulus"]["root_ids"] == [1000]
    assert metadata["diagnostics"]["finite_state"] is True
    assert set(paths) == {"activity", "metadata"}


def test_summary_reports_model_and_effective_delay(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 4)])
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5, duration_ms=10.0
    )
    result = simulator.run(progress=False)
    summary = result.summary
    assert summary["model"]["synapse"]["delay_ms"] == pytest.approx(1.0)
    assert summary["synapses"]["effective_delay_ms"] == pytest.approx(1.0)
    assert summary["graph"]["n_synapses"] == 4
    assert summary["activity"]["n_neurons"] == 2


def test_profiling_and_memory_breakdown(graph_factory) -> None:
    graph = graph_factory(4, [(0, 1, 20), (1, 2, 20), (2, 3, 20)])
    simulator = BrainSimulator(
        graph, neuron_params(), synapse_params(), dt_ms=0.5,
        duration_ms=20.0, seed=2, max_recorded_spikes=100,
        profile_timing=True,
    )
    result = simulator.run(progress=False)
    timing = result.summary["timing_s"]
    assert set(timing) == {
        "synaptic_update_s", "input_s", "integration_s", "recording_s",
        "propagation_s", "diagnostics_s", "total_s",
    }
    assert timing["total_s"] > 0
    assert timing["integration_s"] >= 0

    breakdown = simulator.memory_breakdown()
    components = (
        breakdown["graph_arrays_bytes"]
        + breakdown["neuron_state_bytes"]
        + breakdown["synapse_state_bytes"]
        + breakdown["spike_recorder_bytes"]
    )
    assert breakdown["retained_arrays_bytes"] == components
    assert breakdown["synapse_state_bytes"] == (
        breakdown["synapse_arrays_bytes"] + breakdown["delay_buffer_bytes"]
    )
    assert breakdown["synapse_arrays_bytes"] > 0
    assert breakdown["spike_recorder_bytes"] == (
        breakdown["recorder_capacity"] * 8
    )
    assert breakdown["max_out_degree"] == 1
    assert breakdown["single_hub_propagation_temporary_bytes"] > 0
    assert breakdown["delay_buffer_bytes"] > 0

    diagnostics = result.summary["diagnostics"]
    assert diagnostics["min_membrane_mv"] >= -90.0
    assert diagnostics["max_membrane_mv"] <= -50.0


def test_stimulus_outside_graph_is_rejected(graph_factory) -> None:
    graph = graph_factory(2, [])
    stimulus = Stimulus(
        indices=np.array([5]), current_pa=1.0, start_ms=0.0, end_ms=1.0
    )
    with pytest.raises(ValueError):
        BrainSimulator(
            graph, neuron_params(), synapse_params(), dt_ms=0.5,
            duration_ms=10.0, stimulus=stimulus,
        )
