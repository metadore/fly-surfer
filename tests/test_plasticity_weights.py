"""Phase 5D: separated weight layers, bounds and sign preservation."""

from __future__ import annotations

import numpy as np
import pytest

from plasticity.synthetic import synthetic_substrate
from plasticity.weights import WeightBounds, WeightState


@pytest.fixture()
def substrate():
    return synthetic_substrate()


@pytest.fixture()
def state(substrate):
    graph, policy = substrate
    return WeightState(graph, policy)


# -- construction -----------------------------------------------------------


def test_layers_are_owned_copies_and_read_only(state, substrate):
    graph, policy = substrate
    assert state.n_edges == graph.n_edges
    assert not np.shares_memory(state.structural_count, graph.edge_weight)
    assert not np.shares_memory(state.initial_exc, policy.edge_exc_weight)
    assert not np.shares_memory(state.initial_inh, policy.edge_inh_weight)
    assert np.array_equal(state.structural_count, graph.edge_weight)
    assert np.array_equal(state.initial_exc, policy.edge_exc_weight)
    assert np.array_equal(state.initial_inh, policy.edge_inh_weight)
    with pytest.raises(ValueError):
        state.structural_count[0] = 0
    with pytest.raises(ValueError):
        state.initial_exc[0] = 999.0


def test_effective_layer_starts_at_initial_weights(state):
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)
    assert not np.any(state.delta_exc)
    assert not np.any(state.delta_inh)


def test_only_verified_sign_edges_are_plastic(state, substrate):
    graph, policy = substrate
    expected = (policy.edge_exc_weight > 0) | (policy.edge_inh_weight > 0)
    assert np.array_equal(state.plastic, expected)
    assert state.n_plastic == int(expected.sum())
    assert state.n_plastic > 0
    assert state.n_plastic < state.n_edges
    signs = state.sign_class
    assert np.all(signs[state.plastic] != 0)
    assert np.all(signs[~state.plastic] == 0)
    expected_signs = np.where(
        policy.edge_exc_weight > 0,
        1,
        np.where(policy.edge_inh_weight > 0, -1, 0),
    )
    assert np.array_equal(signs, expected_signs)


def test_invalid_bounds_are_rejected():
    for payload in (
        {"lower_factor": -0.1},
        {"upper_factor": 0.5},
        {"lower_factor": 1.5},
        {"lower_factor": 2.0, "upper_factor": 1.0},
        {"absolute_min_pa": 5.0, "absolute_max_pa": 1.0},
        {"max_abs_update_pa": 0.0},
        {"max_abs_update_pa": -1.0},
    ):
        with pytest.raises(ValueError):
            WeightBounds(**payload)


def test_state_rejects_mismatched_policy(substrate):
    graph, _ = substrate
    _, other_policy = synthetic_substrate(n_nodes=20, n_edges=60, seed=12)
    with pytest.raises(ValueError):
        WeightState(graph, other_policy)


# -- updates ----------------------------------------------------------------


def test_update_splits_channels_and_tracks_both_signs(state):
    exc_edges = np.flatnonzero(state.sign_class == 1)[:3]
    inh_edges = np.flatnonzero(state.sign_class == -1)[:2]
    slots = np.concatenate([exc_edges, inh_edges])
    initial_exc = state.initial_exc[exc_edges].copy()
    initial_inh = state.initial_inh[inh_edges].copy()
    report = state.apply_update(slots, np.full(slots.size, 0.5))
    assert report["n_slots"] == slots.size
    assert report["n_updates"] == slots.size
    assert np.allclose(
        state.delta_exc[exc_edges], 0.5, rtol=0, atol=float(np.finfo(np.float32).eps)
    )
    assert np.allclose(
        state.delta_inh[inh_edges], 0.5, rtol=0, atol=float(np.finfo(np.float32).eps)
    )
    assert np.allclose(state.effective_exc[exc_edges], initial_exc + 0.5, atol=1e-6)
    assert np.allclose(state.effective_inh[inh_edges], initial_inh + 0.5, atol=1e-6)
    assert np.all(state.sign_class[slots] != 0)
    assert state.assert_invariants()["effective_matches_layers"]


def test_update_clamps_to_declared_bounds(state):
    edge = int(np.flatnonzero(state.sign_class == 1)[0])
    initial = float(state.initial_exc[edge])
    report = state.apply_update([edge], [1e6])
    upper_delta = initial
    assert report["clamp_hits"] == 1
    assert state.effective_exc[edge] == pytest.approx(2.0 * initial, rel=1e-6)
    assert state.delta_exc[edge] == pytest.approx(upper_delta, rel=1e-6)
    report = state.apply_update([edge], [-1e6])
    assert report["clamp_hits"] == 1
    assert state.effective_exc[edge] == pytest.approx(0.5 * initial, rel=1e-6)
    assert state.effective_exc[edge] >= 0
    assert state.assert_invariants()["within_declared_bounds"]


def test_update_can_clip_the_raw_increment():
    graph, policy = synthetic_substrate()
    state = WeightState(graph, policy, WeightBounds(max_abs_update_pa=0.25))
    edge = int(np.flatnonzero(state.sign_class == 1)[0])
    report = state.apply_update([edge], [10.0])
    assert report["update_clip_hits"] == 1
    assert state.delta_exc[edge] == pytest.approx(0.25, abs=1e-6)


def test_repeated_updates_keep_layer_identity_and_bounds(state):
    rng = np.random.default_rng(7)
    plastic = state.plastic_positions
    for _ in range(200):
        slots = rng.choice(plastic, size=8, replace=False)
        state.apply_update(slots, rng.normal(0.0, 0.3, size=slots.size))
    assert np.array_equal(
        state.effective_exc, state.initial_exc + state.delta_exc
    )
    assert np.array_equal(
        state.effective_inh, state.initial_inh + state.delta_inh
    )
    assert state.assert_invariants()["within_declared_bounds"]


def test_update_rejects_invalid_slots_and_values(state):
    plastic = int(np.flatnonzero(state.plastic)[0])
    with pytest.raises(ValueError):
        state.apply_update([plastic, plastic], [0.1, 0.1])
    with pytest.raises(ValueError):
        state.apply_update([state.n_edges], [0.1])
    with pytest.raises(ValueError):
        state.apply_update([-1], [0.1])
    with pytest.raises(ValueError):
        state.apply_update([plastic], [float("nan")])
    unknown = np.flatnonzero(~state.plastic)
    with pytest.raises(ValueError):
        state.apply_update(unknown[:1], [0.1])


def test_structural_layer_never_changes(state, substrate):
    graph, _ = substrate
    before = state.structural_count.copy()
    edges = np.flatnonzero(state.plastic)[:10]
    state.apply_update(edges, np.linspace(0.1, 1.0, edges.size))
    state.decay_learned(0.5)
    assert np.array_equal(state.structural_count, before)
    assert np.array_equal(state.structural_count, graph.edge_weight)
    assert state.structural_digest() == state.structural_digest()


def test_decay_scales_learned_layer_only(state):
    edges = np.flatnonzero(state.plastic)[:4]
    state.apply_update(edges, np.full(edges.size, 0.8))
    delta_before = state.delta_exc[edges].copy()
    assert state.decay_learned(1.0) == 0
    assert np.array_equal(state.delta_exc[edges], delta_before)
    changed = state.decay_learned(0.5)
    assert changed == int(np.count_nonzero(delta_before))
    assert np.allclose(state.delta_exc[edges], delta_before * 0.5, rtol=1e-6)
    assert state.assert_invariants()["effective_matches_layers"]
    for factor in (-0.1, 1.1, float("nan")):
        with pytest.raises(ValueError):
            state.decay_learned(factor)


def test_restore_deltas_validates_every_layer(state):
    edges = np.flatnonzero(state.plastic)[:3]
    state.apply_update(edges, np.full(edges.size, 0.4))
    exc = state.delta_exc.copy()
    inh = state.delta_inh.copy()
    # Restoring the same arrays is allowed and reproduces the effective layer.
    digest = state.delta_digest()
    state.restore_deltas(exc, inh)
    assert state.delta_digest() == digest
    assert np.array_equal(
        state.effective_exc, (state.initial_exc + exc).astype(np.float32)
    )
    bad = exc.copy()
    unknown = int(np.flatnonzero(~state.plastic)[0])
    bad[unknown] = 0.1
    with pytest.raises(ValueError):
        state.restore_deltas(bad, inh)
    wrong_channel = inh.copy()
    wrong_channel[int(np.flatnonzero(state.sign_class == 1)[0])] = 0.1
    with pytest.raises(ValueError):
        state.restore_deltas(exc, wrong_channel)
    out_of_bounds = exc.copy()
    out_of_bounds[edges[0]] = 1e6
    with pytest.raises(ValueError):
        state.restore_deltas(out_of_bounds, inh)
    with pytest.raises(ValueError):
        state.restore_deltas(exc[:-1], inh)


def test_digests_and_description(state):
    description = state.describe()
    assert description["n_edges"] == state.n_edges
    assert description["n_plastic"] == state.n_plastic
    assert description["n_unknown"] == state.n_edges - state.n_plastic
    assert description["n_changed_edges"] == 0
    assert description["delta_sum_pa"] == 0.0
    digest = state.digest()
    assert digest == state.delta_digest()
    assert len(digest) == 64
    assert description["digests"]["structural"] == state.structural_digest()
    assert description["classification"].startswith("computational")
    edges = np.flatnonzero(state.plastic)[:2]
    state.apply_update(edges, [0.3, -0.2])
    assert state.digest() != digest
    assert state.describe()["n_changed_edges"] == 2
