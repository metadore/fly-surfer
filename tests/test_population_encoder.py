"""Population encoders: Gaussian tuning, lane and boolean populations."""

from __future__ import annotations

import numpy as np
import pytest

from sensory.population_encoder import (
    BooleanPopulation,
    EncoderSpec,
    GaussianPopulation,
    LanePopulation,
    build_encoder,
    build_encoders,
    encode_state,
)


def test_gaussian_population_preferred_and_sigma() -> None:
    spec = EncoderSpec(
        kind="gaussian", n_neurons=5, minimum=0.0, maximum=1.0,
        sigma_fraction=0.2, amplitude=1.0,
    )
    population = GaussianPopulation(spec)
    assert np.allclose(population.preferred, np.linspace(0.0, 1.0, 5))
    assert population.sigma == pytest.approx(0.2)
    assert spec.output_size == 5


def test_gaussian_encode_peaks_and_baseline() -> None:
    spec = EncoderSpec(
        kind="gaussian", n_neurons=5, minimum=0.0, maximum=1.0,
        sigma_fraction=0.2, amplitude=1.0, baseline=0.5,
    )
    population = GaussianPopulation(spec)
    response = population.encode(0.0)
    assert response[0] == pytest.approx(1.0)
    assert np.all(response[1:] < response[0])
    assert np.all(response >= 0.5)
    assert np.all(population.baseline_response() == 0.5)
    assert np.all(population.encode(0.3) < 1.0)


def test_gaussian_rejects_bad_input() -> None:
    population = GaussianPopulation(
        EncoderSpec(kind="gaussian", n_neurons=3)
    )
    for value in (-0.1, 1.1, float("nan"), True, "near"):
        with pytest.raises(ValueError):
            population.encode(value)


def test_lane_population_is_one_hot_by_group() -> None:
    population = LanePopulation(
        EncoderSpec(kind="lane", lanes=3, neurons_per_lane=2)
    )
    assert population.spec.output_size == 6
    response = population.encode(2)
    assert response.tolist() == [0.0, 0.0, 0.0, 0.0, 1.0, 1.0]
    assert np.all(population.baseline_response() == 0.0)
    with pytest.raises(ValueError):
        population.encode(3)
    with pytest.raises(ValueError):
        population.encode(True)


def test_boolean_population() -> None:
    population = BooleanPopulation(
        EncoderSpec(kind="boolean", n_neurons=4, amplitude=1.0, baseline=0.1)
    )
    assert np.all(population.encode(True) == 1.0)
    assert np.all(population.encode(False) == 0.1)
    assert np.all(population.encode(1) == 1.0)
    assert np.all(population.encode(0) == 0.1)
    for value in (0.5, 2, "yes"):
        with pytest.raises(ValueError):
            population.encode(value)


def test_encode_state_uses_baseline_for_absent_values() -> None:
    encoders = {
        "distance": build_encoder(
            {"kind": "gaussian", "n_neurons": 3, "baseline": 0.0}
        ),
        "lane": build_encoder(
            {"kind": "lane", "lanes": 3, "neurons_per_lane": 2}
        ),
    }
    responses = encode_state({"distance": None, "lane": 1}, encoders)
    assert np.all(responses["distance"] == 0.0)
    assert responses["lane"].tolist() == [0.0, 0.0, 1.0, 1.0, 0.0, 0.0]
    with pytest.raises(ValueError):
        encode_state({"distance": 0.5}, encoders)


def test_encoder_spec_validation_and_order() -> None:
    with pytest.raises(ValueError):
        EncoderSpec(kind="linear")
    with pytest.raises(ValueError):
        EncoderSpec(kind="gaussian")
    with pytest.raises(ValueError):
        EncoderSpec(kind="gaussian", n_neurons=3, minimum=1.0, maximum=1.0)
    with pytest.raises(ValueError):
        EncoderSpec(kind="gaussian", n_neurons=3, sigma_fraction=0.0)
    with pytest.raises(ValueError):
        EncoderSpec(kind="boolean", n_neurons=0)
    with pytest.raises(ValueError):
        EncoderSpec(kind="lane", lanes=0)
    with pytest.raises(ValueError):
        EncoderSpec(kind="gaussian", n_neurons=3, amplitude=0.5, baseline=1.0)

    encoders = build_encoders(
        {
            "second": {"kind": "boolean", "n_neurons": 2},
            "first": {"kind": "gaussian", "n_neurons": 3},
        }
    )
    assert list(encoders) == ["second", "first"]
    with pytest.raises(ValueError):
        build_encoders({})
