"""Phase 5D: validated configuration and synapse ownership."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from plasticity.config import load_plasticity_config
from plasticity.plastic_synapses import PlasticSignedSynapses
from plasticity.synthetic import synthetic_substrate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"


def test_declared_configuration_loads_and_is_consistent():
    config = load_plasticity_config(CONFIG_PATH)
    assert config.fixed_mode_eta == 0.0
    assert config.bounds.lower_factor == 0.5
    assert config.bounds.upper_factor == 2.0
    assert config.bounds.max_abs_update_pa == 5.0
    assert config.rule.eta == 0.01
    assert config.rule.update_cadence == "reward_event"
    assert config.rule.normalization == "none"
    assert config.primary_threshold == 5
    assert config.simulation["dt_ms"] == 0.5
    assert config.traces.tau_e_ms == 20.0
    description = config.describe()
    assert description["rule"]["rule"] == "delta_w = eta * delta_t * e_ij"
    assert "weights" in description and "simulation" in description


def test_fixed_mode_eta_cannot_be_weakened(tmp_path):
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["weights"]["fixed_mode_eta"] = 0.0001
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be weakened"):
        load_plasticity_config(path)


def test_unknown_simulation_key_is_rejected(tmp_path):
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["simulation"]["made_up"] = 1
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown simulation key"):
        load_plasticity_config(path)


def test_invalid_bounds_in_config_are_rejected(tmp_path):
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["weights"]["bounds"]["upper_factor"] = 0.5
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_plasticity_config(path)


def test_plastic_synapses_own_effective_arrays_and_attribute_edges():
    graph, policy = synthetic_substrate(n_nodes=24, n_edges=120, seed=13)
    config = load_plasticity_config(CONFIG_PATH)
    state = config.weight_state(graph, policy)
    synapses = PlasticSignedSynapses(graph, policy, state, 0.5)
    assert synapses.edge_exc_weight is state.effective_exc
    assert synapses.edge_inh_weight is state.effective_inh
    assert not np.shares_memory(synapses.edge_exc_weight, policy.edge_exc_weight)
    assert not np.shares_memory(synapses.edge_inh_weight, policy.edge_inh_weight)
    spikes = np.array([0, 3, 7], dtype=np.int64)
    edges = synapses.active_edges_for(spikes)
    expected = np.concatenate(
        [
            np.arange(graph.out_indptr[node], graph.out_indptr[node + 1])
            for node in spikes
        ]
    )
    assert np.array_equal(edges, expected)
    assert np.array_equal(synapses.active_edges_for(np.array([], dtype=np.int64)), [])
    with pytest.raises(ValueError):
        synapses.active_edges_for(np.array([graph.n_nodes]))
    assert synapses.weight_memory_bytes == (
        state.effective_exc.nbytes + state.effective_inh.nbytes
    )


def test_plastic_synapses_reject_a_foreign_weight_state():
    graph, policy = synthetic_substrate(n_nodes=24, n_edges=120, seed=13)
    other_graph, other_policy = synthetic_substrate(
        n_nodes=24, n_edges=120, seed=14
    )
    from plasticity.weights import WeightState

    other_state = WeightState(other_graph, other_policy)
    with pytest.raises(ValueError, match="different structural graph"):
        PlasticSignedSynapses(graph, policy, other_state, 0.5)
