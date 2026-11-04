"""Synapse sign assignment, weight transform, sparse propagation and delay."""

from __future__ import annotations

import numpy as np
import pytest

from brain.synapse_model import SynapseParameters, SynapseModel


def make_synapses(graph, **overrides) -> SynapseModel:
    values = dict(
        weight_transform="linear",
        weight_scale_pa_per_synapse=0.5,
        weight_exponent=0.75,
        tau_exc_ms=5.0,
        tau_inh_ms=8.0,
        delay_ms=0.5,
    )
    values.update(overrides)
    return SynapseModel(graph, SynapseParameters(**values), 0.5)


def test_sign_assignment_and_linear_weights(graph_factory) -> None:
    graph = graph_factory(
        4,
        [(0, 1, 4), (1, 2, 9), (2, 0, 1), (3, 2, 2)],
        nt_codes=np.array([0, 1, 2, 3]),  # ACH, GABA, DA (unknown), GLUT
    )
    model = make_synapses(graph)
    assert model.signs.tolist() == [1, -1, 1, 1]
    assert model.has_inhibition
    assert model.edge_exc_weight.tolist() == pytest.approx([2.0, 0.0, 0.5, 1.0])
    assert model.edge_inh_weight.tolist() == pytest.approx([0.0, 4.5, 0.0, 0.0])
    assert np.count_nonzero(model.edge_exc_weight) == 3
    assert np.count_nonzero(model.edge_inh_weight) == 1


def test_power_transform(graph_factory) -> None:
    graph = graph_factory(4, [(0, 1, 4), (1, 2, 9), (2, 0, 1), (3, 2, 2)])
    model = make_synapses(
        graph, weight_transform="power", weight_scale_pa_per_synapse=2.0,
        weight_exponent=0.5,
    )
    expected = 2.0 * np.sqrt(np.array([4.0, 9.0, 1.0, 2.0]))
    assert model.edge_exc_weight.tolist() == pytest.approx(expected.tolist())


def test_unknown_and_unlabeled_sign_policies(graph_factory) -> None:
    graph = graph_factory(
        2,
        [(0, 1, 3)],
        nt_codes=np.array([2, 99]),  # DA and an out-of-vocabulary label
    )
    model = make_synapses(
        graph, unknown_nt_sign="inhibitory", unlabeled_sign="silent"
    )
    assert model.signs.tolist() == [-1, 0]


def test_delay_buffer_and_current_delivery(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 5)])
    model = make_synapses(graph, delay_ms=1.0)
    assert model.effective_delay_ms == pytest.approx(1.0)
    assert model.propagate(np.array([0], dtype=np.int32)) == 1
    assert model.excitatory_current_pa.tolist() == [0.0, 0.0]
    model.advance()
    assert model.excitatory_current_pa.tolist() == [0.0, 0.0]
    model.advance()
    assert model.excitatory_current_pa.tolist() == pytest.approx([0.0, 2.5])


def test_minimum_delay_is_one_timestep(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 4)])
    model = make_synapses(graph, delay_ms=0.5)
    assert model.effective_delay_ms == pytest.approx(0.5)
    model.propagate(np.array([0], dtype=np.int32))
    model.advance()
    assert model.excitatory_current_pa[1] == pytest.approx(2.0)


def test_sparse_propagation_matches_manual_destination_sums(graph_factory) -> None:
    graph = graph_factory(3, [(0, 2, 4), (1, 0, 1), (1, 2, 9)])
    model = make_synapses(graph)
    assert model.propagate(np.array([0, 1], dtype=np.int32)) == 3
    model.advance()
    assert model.excitatory_current_pa.tolist() == pytest.approx([0.5, 0.0, 6.5])
    assert model.total_transmissions == 3


def test_spikes_without_outgoing_edges_transmit_nothing(graph_factory) -> None:
    graph = graph_factory(3, [(0, 1, 2)])
    model = make_synapses(graph)
    assert model.propagate(np.array([2], dtype=np.int32)) == 0
    assert model.propagate(np.empty(0, dtype=np.int32)) == 0
    assert model.total_transmissions == 0


def test_exponential_current_decay(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 4)])
    model = make_synapses(graph)
    model.propagate(np.array([0], dtype=np.int32))
    model.advance()
    delivered = float(model.excitatory_current_pa[1])
    model.advance()
    assert model.excitatory_current_pa[1] == pytest.approx(
        delivered * np.exp(-0.5 / 5.0), rel=1e-6
    )


def test_inhibitory_current_is_subtracted(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 4)], nt_codes=np.array([1, 1]))
    model = make_synapses(graph)
    model.propagate(np.array([0], dtype=np.int32))
    model.advance()
    assert model.inhibitory_current_pa[1] == pytest.approx(2.0)
    assert model.synaptic_current_pa[1] == pytest.approx(-2.0)


def test_reset_clears_pending_and_currents(graph_factory) -> None:
    graph = graph_factory(2, [(0, 1, 4)])
    model = make_synapses(graph, delay_ms=1.0)
    model.propagate(np.array([0], dtype=np.int32))
    model.advance()
    model.reset()
    assert np.all(model.excitatory_current_pa == 0.0)
    assert np.all(model.inhibitory_current_pa == 0.0)
    assert model.total_transmissions == 0
    model.advance()
    model.advance()
    assert np.all(model.excitatory_current_pa == 0.0)


def test_parameter_validation() -> None:
    with pytest.raises(ValueError):
        SynapseParameters(weight_transform="sqrt")
    with pytest.raises(ValueError):
        SynapseParameters(weight_scale_pa_per_synapse=-1.0)
    with pytest.raises(ValueError):
        SynapseParameters(weight_exponent=0.0)
    with pytest.raises(ValueError):
        SynapseParameters(tau_exc_ms=0.0)
    with pytest.raises(ValueError):
        SynapseParameters(unknown_nt_sign="modulatory")
    with pytest.raises(ValueError):
        SynapseParameters(nt_signs={"ACH": "sometimes"})


def test_from_config_merges_transmitter_policies() -> None:
    params = SynapseParameters.from_config(
        {"nt_signs": {"gaba": "silent"}, "delay_ms": 2.0}
    )
    assert params.nt_signs["GABA"] == "silent"
    assert params.nt_signs["ACH"] == "excitatory"
    assert params.delay_ms == pytest.approx(2.0)
