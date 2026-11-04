"""YAML configuration loading and parameter construction."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load(name: str) -> dict:
    with (PROJECT_ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_neuron_config_constructs_parameters() -> None:
    params = LIFParameters.from_config(load("neuron_config.yaml")["neuron"])
    assert params.capacitance_pf == pytest.approx(200.0)
    assert params.leak_conductance_ns == pytest.approx(10.0)
    assert params.threshold_mv > params.reset_potential_mv
    assert params.tau_m_ms == pytest.approx(20.0)
    assert params.rheobase_pa == pytest.approx(150.0)
    assert params.refractory_ms == pytest.approx(2.0)


def test_simulation_config_is_complete_and_valid() -> None:
    config = load("simulation_config.yaml")
    assert (PROJECT_ROOT / config["connectome"]["path"]).exists()
    simulation = config["simulation"]
    assert simulation["duration_ms"] > 0
    assert simulation["dt_ms"] > 0
    assert simulation["max_recorded_spikes"] >= 1_000_000
    experiment = config["experiment"]
    assert 500 <= experiment["n_neurons"] <= 1000
    assert experiment["min_degree"] >= 0

    synapse = SynapseParameters.from_config(config["synapse"])
    assert synapse.weight_transform in {"linear", "power"}
    assert synapse.weight_scale_pa_per_synapse > 0
    assert synapse.tau_exc_ms > 0 and synapse.tau_inh_ms > 0
    assert synapse.nt_signs["GABA"] == "inhibitory"

    stimulus = config["external_input"]["stimulus"]
    assert stimulus["enabled"] is True
    assert 0 < stimulus["n_neurons"] < experiment["n_neurons"]
    assert stimulus["end_ms"] > stimulus["start_ms"]


def test_configs_do_not_contain_placeholder_values() -> None:
    config = load("simulation_config.yaml")
    assert config["external_input"]["background_current_pa"] >= 0
    assert config["external_input"]["noise_std_pa"] >= 0
    assert config["simulation"]["seed"] == int(config["simulation"]["seed"])
    assert config["experiment"]["sampling_seed"] == int(
        config["experiment"]["sampling_seed"]
    )
