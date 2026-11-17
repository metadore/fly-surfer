"""Focused tests for the Phase 8 live plastic stepper (work package G1).

The synthetic substrate keeps these tests lightweight: no BANC-scale graph is
loaded and no campaign is run. The point is the contract, not a scientific
result:

* with ``eta = 0`` the plastic pathway must reproduce the fixed-weight
  pathway bit for bit;
* with ``eta > 0`` the declared update may change the effective weights, and
  the change is reproducible for a fixed seed;
* ``reset`` clears the neural, trace and delay state but preserves the learned
  weight layer, so training can continue across episodes.
"""

from __future__ import annotations

import numpy as np
import pytest

from brain.banc_simulator import BancStimulation
from environment.live_loop import LiveBancStepper
from plasticity.live_stepper import LivePlasticStepper
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.synthetic import synthetic_substrate
from plasticity.traces import TraceConfig
from plasticity.weights import WeightState

TRACE_SECTION = {
    "traces": {
        "tau_e_ms": 20.0,
        "dt_ms": 0.5,
        "dtype": "float32",
        "prune_threshold": 1.0e-4,
        "prune_interval_steps": 50,
        "coincidence": "delay_matched",
    }
}


def trace_config() -> TraceConfig:
    return TraceConfig(TRACE_SECTION)


def build_steppers(
    *,
    eta: float = 0.0,
    n_steps: int = 200,
    seed: int = 7,
    enable_traces: bool = True,
):
    graph, policy = synthetic_substrate(n_nodes=32, n_edges=160, seed=5)
    stimulation = BancStimulation(np.arange(16), 500.0, 0.0, n_steps * 0.5)
    common = {
        "dt_ms": 0.5,
        "duration_ms": 60_000.0,
        "seed": seed,
        "background_current_pa": 0.0,
        "noise_std_pa": 0.0,
        "stimulation": stimulation,
    }
    fixed = LiveBancStepper(graph, policy, **common)
    state = WeightState(graph, policy)
    plastic = LivePlasticStepper(
        graph,
        policy,
        weight_state=state,
        rule=ThreeFactorRule(RuleConfig(eta=eta), state),
        trace_config=trace_config() if enable_traces else None,
        enable_traces=enable_traces,
        **common,
    )
    return fixed, plastic, state


def spike_arrays(stepper):
    return (
        np.array(stepper.recorder.spike_times_ms, copy=True),
        np.array(stepper.recorder.spike_neuron_indices, copy=True),
    )


def test_plastic_stepper_is_an_additive_parent_subclass():
    _, plastic, _ = build_steppers()
    assert isinstance(plastic, LiveBancStepper)
    assert plastic.step_observer is not None
    assert plastic.engine is not None
    assert plastic.synapses.weight_state is plastic.weight_state


def test_eta_zero_reproduces_fixed_weight_spikes_and_fingerprint():
    fixed, plastic, state = build_steppers(eta=0.0)
    fixed.advance_to_step(200)
    plastic.advance_to_step(200)

    fixed_times, fixed_indices = spike_arrays(fixed)
    plastic_times, plastic_indices = spike_arrays(plastic)
    assert np.array_equal(fixed_times, plastic_times)
    assert np.array_equal(fixed_indices, plastic_indices)
    assert fixed.transmitted_spikes == plastic.transmitted_spikes
    assert fixed.weight_fingerprint() == plastic.weight_fingerprint()

    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)
    assert state.delta_digest() == WeightState(
        plastic.graph, plastic.policy
    ).delta_digest()
    assert state.n_update_calls == 0
    assert 0 < state.n_plastic <= int(plastic.graph.n_edges)
    assert state.n_plastic == int(np.count_nonzero(state.sign_class))


def test_engine_observes_every_step_and_reset_clears_trace_state():
    _, plastic, _ = build_steppers(eta=0.0)
    plastic.advance_to_step(60)
    assert plastic.step_index == 60
    assert plastic.engine.n_pushed_edges > 0
    assert plastic.engine.n_delivered_edges > 0

    plastic.reset()
    assert plastic.step_index == 0
    assert plastic.resets == 1
    assert plastic.engine.n_pushed_edges == 0
    assert plastic.engine.n_delivered_edges == 0
    assert plastic.engine.trace_store.clock == 0
    assert plastic.recorder.n_spikes == 0


def test_learn_at_eta_zero_reports_no_applied_update():
    _, plastic, state = build_steppers(eta=0.0)
    plastic.advance_to_step(60)
    report = plastic.learn(1.0)
    assert report is not None
    assert report.eta == 0.0
    assert report.n_updates == 0
    assert state.n_update_calls == 0
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)


def test_learn_with_eta_positive_changes_weights_reproducibly():
    digests = []
    for _ in range(2):
        fixed, plastic, state = build_steppers(eta=5.0)
        for _ in range(12):
            plastic.advance_to_step(plastic.step_index + 20)
            plastic.learn(1.0)
        digests.append(state.delta_digest())
        assert state.n_update_calls > 0
        assert not np.array_equal(state.effective_exc, state.initial_exc)
        assert plastic.weight_fingerprint() != fixed.weight_fingerprint()
        assert state.assert_invariants()["effective_matches_layers"]
    assert digests[0] == digests[1]


def test_learning_survives_reset_but_the_network_does_not():
    _, plastic, state = build_steppers(eta=5.0)
    for _ in range(12):
        plastic.advance_to_step(plastic.step_index + 20)
        plastic.learn(1.0)
    learned = state.delta_digest()
    assert learned != WeightState(plastic.graph, plastic.policy).delta_digest()

    plastic.reset()
    assert state.delta_digest() == learned
    assert plastic.step_index == 0
    assert plastic.engine.trace_store.active_edges.size == 0


def test_traces_disabled_runs_without_learning_pathway():
    fixed, plastic, state = build_steppers(eta=0.0, enable_traces=False)
    plastic.advance_to_step(100)
    assert plastic.engine.learn(0, 1.0) is None
    assert plastic.learn(1.0) is None
    assert plastic.update_reports == ()
    assert fixed.weight_fingerprint() == plastic.weight_fingerprint()


def test_rule_and_weight_state_must_match():
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=80, seed=3)
    state = WeightState(graph, policy)
    other = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=1.0), other)
    with pytest.raises(ValueError, match="share one weight state"):
        LivePlasticStepper(
            graph,
            policy,
            weight_state=state,
            rule=rule,
            trace_config=trace_config(),
        )


def test_describe_reports_the_plastic_pathway():
    _, plastic, _ = build_steppers(eta=0.0)
    payload = plastic.describe()
    assert payload["kind"] == "live_plastic_stepper"
    assert payload["pathway"] == "plastic_three_factor"
    assert payload["eta"] == 0.0
    assert payload["n_plastic_edges"] == plastic.weight_state.n_plastic
    assert payload["limitations"]
