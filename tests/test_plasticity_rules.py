"""Phase 5D: the three-factor rule, its eta = 0 contract and its constraints."""

from __future__ import annotations

import numpy as np
import pytest

from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.synthetic import synthetic_substrate
from plasticity.weights import WeightBounds, WeightState


def make_rule(eta: float = 0.1, **kwargs):
    graph, policy = synthetic_substrate()
    state = WeightState(graph, policy, WeightBounds(max_abs_update_pa=None))
    config = RuleConfig(eta=eta, **kwargs)
    return ThreeFactorRule(config, state), state


def test_rule_configuration_is_validated():
    for payload in (
        {"eta": -0.01},
        {"eta": float("nan")},
        {"update_cadence": "sometimes"},
        {"weight_decay_per_ms": -0.1},
        {"normalization": "l2"},
        {"abort_on_sign_flip": "yes"},
    ):
        with pytest.raises(ValueError):
            RuleConfig(**payload)


def test_eta_zero_is_a_strict_no_op():
    rule, state = make_rule(eta=0.0)
    edges = np.flatnonzero(state.plastic)[:5]
    before = state.digest()
    report = rule.apply(3, edges, np.full(edges.size, 5.0), delta_t=10.0)
    assert report.n_slots == edges.size
    assert report.n_updates == 0
    assert report.sum_applied_pa == 0.0
    assert report.max_abs_applied_pa == 0.0
    assert report.mean_eligibility == pytest.approx(5.0)
    assert state.digest() == before
    assert not np.any(state.delta_exc)
    assert not np.any(state.delta_inh)
    assert state.n_update_calls == 0


def test_eta_zero_skips_weight_decay_too():
    rule, state = make_rule(eta=0.0, weight_decay_per_ms=1.0)
    edges = np.flatnonzero(state.plastic)[:3]
    rule.apply(0, edges, np.ones(edges.size), delta_t=1.0)
    assert state.n_update_calls == 0


def test_update_follows_the_declared_rule_exactly():
    eta = 0.05
    rule, state = make_rule(eta=eta)
    edges = np.flatnonzero(state.plastic)[:4]
    traces = np.array([2.0, 0.5, 1.0, 4.0])
    rpe = 3.0
    report = rule.apply(7, edges, traces, delta_t=rpe)
    expected = eta * rpe * traces
    delta = state.delta_exc[edges] + state.delta_inh[edges]
    assert np.allclose(delta, expected, rtol=1e-6, atol=1e-7)
    assert report.n_updates == edges.size
    assert report.sum_applied_pa == pytest.approx(expected.sum(), rel=1e-6)
    assert report.delta_t == rpe
    assert report.step == 7


def test_negative_prediction_error_reduces_excitatory_weights():
    rule, state = make_rule(eta=0.1)
    edge = int(np.flatnonzero(state.sign_class == 1)[0])
    initial = float(state.effective_exc[edge])
    rule.apply(0, [edge], [1.0], delta_t=-2.0)
    assert state.effective_exc[edge] < initial
    assert state.effective_exc[edge] >= 0.5 * initial - 1e-6
    assert state.assert_invariants()["effective_non_negative"]


def test_a_single_large_update_is_clipped_before_clamping():
    graph, policy = synthetic_substrate()
    state = WeightState(graph, policy, WeightBounds(max_abs_update_pa=0.5))
    rule = ThreeFactorRule(RuleConfig(eta=100.0), state)
    edge = int(np.flatnonzero(state.plastic)[0])
    report = rule.apply(0, [edge], [10.0], delta_t=1.0)
    assert report.update_clip_hits == 1
    assert abs(report.max_abs_applied_pa) <= 0.5 + 1e-6


def test_rule_rejects_invalid_inputs():
    rule, state = make_rule()
    edges = np.flatnonzero(state.plastic)[:2]
    with pytest.raises(ValueError):
        rule.apply(0, edges, [1.0], delta_t=1.0)
    with pytest.raises(ValueError):
        rule.apply(0, edges, [1.0, -1.0], delta_t=1.0)
    with pytest.raises(ValueError):
        rule.apply(0, edges, [float("nan"), 1.0], delta_t=1.0)
    with pytest.raises(ValueError):
        rule.apply(0, edges, [1.0, 1.0], delta_t=float("inf"))
    with pytest.raises(ValueError):
        rule.apply(0, edges, [1.0, 1.0], delta_t=1.0, dt_ms=0.0)
    unknown = np.flatnonzero(~state.plastic)[:1]
    with pytest.raises(ValueError):
        rule.apply(0, unknown, [1.0], delta_t=1.0)


def test_zero_traces_leave_weights_unchanged_even_with_positive_eta():
    rule, state = make_rule(eta=0.1)
    edges = np.flatnonzero(state.plastic)[:3]
    before = state.digest()
    report = rule.apply(0, edges, np.zeros(edges.size), delta_t=2.0)
    assert report.n_updates == 0
    assert state.digest() == before


def test_weight_decay_is_applied_before_the_update():
    import math

    rule, state = make_rule(eta=0.1, weight_decay_per_ms=1.0)
    edge = int(np.flatnonzero(state.plastic)[0])
    rule.apply(0, [edge], [1.0], delta_t=1.0)
    first = float(state.delta_exc[edge] + state.delta_inh[edge])
    assert first == pytest.approx(0.1, rel=1e-6)
    report = rule.apply(1, [edge], [0.0], delta_t=1.0)
    factor = math.exp(-1.0 * 0.5)
    second = float(state.delta_exc[edge] + state.delta_inh[edge])
    assert report.decayed_edges == 1
    assert second == pytest.approx(first * factor, rel=1e-6)
    assert rule.describe()["rule"] == "delta_w = eta * delta_t * e_ij"
    assert "declared exclusion" in rule.describe()["normalization_status"]
