"""Phase 5D: the independent plastic simulator, its eta = 0 contract and checkpoints."""

from __future__ import annotations

import numpy as np
import pytest

from brain.banc_simulator import BancSimulator, BancStimulation
from plasticity.checkpoint import (
    graph_checksum,
    load_checkpoint,
    save_checkpoint,
)
from plasticity.diagnostics import spike_hash
from plasticity.engine import PlasticityEngine
from plasticity.plastic_simulator import PlasticSimulator
from plasticity.reward import TabularValuePredictor
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.synthetic import synthetic_graph, synthetic_policy, synthetic_substrate
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


class StepRewards:
    """Return a reward on named steps and None elsewhere (no event)."""

    def __init__(self, rewards: dict[int, float]) -> None:
        self.rewards = dict(rewards)
        self._seen: set[int] = set()

    def reset(self) -> None:
        self._seen.clear()

    def step(self, step: int, time_ms: float, context=None):
        del time_ms, context
        if step in self.rewards and step not in self._seen:
            self._seen.add(step)
            return float(self.rewards[step])
        return None


def build_pair(
    *,
    eta: float = 0.0,
    rewards: dict[int, float] | None = None,
    enable_traces: bool = True,
    noise_std_pa: float = 25.0,
    duration_ms: float = 80.0,
    seed: int = 7,
    graph=None,
    policy=None,
):
    if graph is None or policy is None:
        graph, policy = synthetic_substrate(n_nodes=64, n_edges=800, seed=5)
    stimulation = BancStimulation(np.arange(16), 500.0, 0.0, duration_ms)
    common = {
        "dt_ms": 0.5,
        "duration_ms": duration_ms,
        "seed": seed,
        "noise_std_pa": noise_std_pa,
        "stimulation": stimulation,
        "max_recorded_spikes": 200_000,
    }
    fixed = BancSimulator(graph, policy, **common).run()
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=eta), state)
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config() if enable_traces else None,
        enable_traces=enable_traces,
        reward_provider=StepRewards(rewards or {}),
        **common,
    )
    return fixed, simulator, state


# -- the required eta = 0 contract -----------------------------------------


def test_eta_zero_reproduces_fixed_weight_spikes_byte_for_byte():
    fixed, simulator, state = build_pair(eta=0.0, rewards={40: 1.0})
    result = simulator.run()
    assert np.array_equal(
        result.recorder.spike_times_ms, fixed.recorder.spike_times_ms
    )
    assert np.array_equal(
        result.recorder.spike_neuron_indices, fixed.recorder.spike_neuron_indices
    )
    assert result.spike_hash == spike_hash(fixed.recorder)
    assert state.delta_digest() == WeightState(
        simulator.graph, simulator.policy
    ).delta_digest()
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)
    assert state.n_update_calls == 0


def test_eta_zero_with_traces_disabled_is_also_identical():
    fixed, simulator, state = build_pair(
        eta=0.0, rewards={40: -1.0}, enable_traces=False
    )
    result = simulator.run()
    assert result.spike_hash == spike_hash(fixed.recorder)
    assert result.summary["plasticity"]["traces"]["enabled"] is False
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)


def test_eta_zero_is_repeatable_and_keeps_weights_fixed():
    _, simulator, state = build_pair(eta=0.0, rewards={20: 1.0, 60: -1.0})
    first = simulator.run()
    first_digest = state.digest()
    second = simulator.run()
    assert first.spike_hash == second.spike_hash
    assert state.digest() == first_digest == WeightState(
        simulator.graph, simulator.policy
    ).digest()


# -- nonzero eta ------------------------------------------------------------


def test_positive_eta_updates_only_plastic_edges_and_preserves_signs():
    fixed, simulator, state = build_pair(
        eta=0.05, rewards={159: 1.0}, noise_std_pa=40.0
    )
    result = simulator.run()
    assert len(result.update_reports) == 1
    report = result.update_reports[0]
    assert report.n_slots > 0
    assert result.summary["plasticity"]["traces"]["n_coincident_tags"] > 0
    assert state.n_update_calls == 1
    assert np.all(state.delta_exc[~state.plastic] == 0)
    assert np.all(state.delta_inh[~state.plastic] == 0)
    assert np.all(state.effective_exc >= 0)
    assert np.all(state.effective_inh >= 0)
    assert np.all(state.sign_class[state.delta_exc != 0] == 1)
    assert np.all(state.sign_class[state.delta_inh != 0] == -1)
    assert state.assert_invariants()["within_declared_bounds"]
    assert state.structural_digest() == WeightState(
        simulator.graph, simulator.policy
    ).structural_digest()
    # The reward is delivered on the last step, after propagation, so no
    # weight change can retroactively alter this run's spikes.
    assert result.spike_hash == spike_hash(fixed.recorder)
    assert np.all(np.isfinite(state.effective_exc))


def test_positive_eta_without_reward_events_changes_nothing():
    _, simulator, state = build_pair(eta=0.05, rewards={})
    result = simulator.run()
    assert result.update_reports == ()
    assert state.delta_digest() == WeightState(
        simulator.graph, simulator.policy
    ).delta_digest()
    assert result.summary["plasticity"]["updates"]["n_update_events"] == 0


def test_negative_reward_reduces_excitatory_weights():
    _, simulator, state = build_pair(eta=0.05, rewards={159: -5.0})
    simulator.run()
    negative_exc = state.delta_exc[state.delta_exc < 0]
    positive_exc = state.delta_exc[state.delta_exc > 0]
    assert negative_exc.size > 0
    assert positive_exc.size == 0


def test_every_step_cadence_logs_a_zero_error_update_per_step():
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=48, seed=8)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(
        RuleConfig(eta=0.01, update_cadence="every_step"), state
    )
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config(),
        dt_ms=0.5,
        duration_ms=4.0,
        seed=1,
    )
    result = simulator.run()
    assert len(result.update_reports) == result.n_steps
    assert all(report.delta_t == 0.0 for report in result.update_reports)
    assert all(report.n_updates == 0 for report in result.update_reports)
    assert state.digest() == WeightState(graph, policy).digest()


# -- controlled coincidence and rule wiring --------------------------------


def simple_chain():
    # Hand-written chain 0 -> 2, 1 -> 2, 2 -> 3.
    import numpy as np

    edge_src = np.array([0, 1, 2], dtype=np.int32)
    edge_dst = np.array([2, 2, 3], dtype=np.int32)
    from brain.banc_graph import BancConnectome

    weight = np.array([6, 8, 10], dtype=np.int32)
    out = np.zeros(5, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=4), out=out[1:])
    inn = np.zeros(5, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=4), out=inn[1:])
    ordered = BancConnectome(
        root_ids=np.arange(900_000, 900_004, dtype=np.int64),
        out_indptr=out,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=weight,
        in_indptr=inn,
        in_edge_idx=np.argsort(edge_dst, kind="stable").astype(np.int32),
        threshold=1,
    )
    return ordered, synthetic_policy(ordered)


def test_delay_matched_coincidence_tags_the_delivered_presynaptic_edges():
    graph, policy = simple_chain()
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.1), state)
    engine = PlasticityEngine(
        graph,
        state,
        rule,
        trace_config(),
        dt_ms=0.5,
        delay_steps=2,
    )
    outgoing = {
        node: np.arange(graph.out_indptr[node], graph.out_indptr[node + 1])
        for node in range(graph.n_nodes)
    }
    assert engine.observe_step(0, np.array([0]), outgoing[0]) == 0
    assert engine.observe_step(1, np.array([1]), outgoing[1]) == 0
    # At step 2 the packet from step 0 is delivered while node 2 spikes.
    assert engine.observe_step(2, np.array([2]), outgoing[2]) == 1
    # At step 3 the packet from step 1 arrives; node 2 must spike again.
    assert engine.observe_step(3, np.array([2]), outgoing[2]) == 1
    assert engine.n_delivered_edges == 2
    assert engine.n_coincident_tags == 2
    report = engine.learn(3, 1.0)
    assert report is not None
    assert report.n_slots == 2
    assert report.n_updates == 2
    # Only the two convergent plastic edges can change; 2 -> 3 was never tagged.
    changed = np.flatnonzero((state.delta_exc != 0) | (state.delta_inh != 0))
    assert changed.tolist() == [0, 1]
    assert state.effective_exc[2] == state.initial_exc[2]
    assert report.mean_eligibility > 0


def test_delay_mismatch_does_not_tag():
    graph, policy = simple_chain()
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.1), state)
    engine = PlasticityEngine(
        graph, state, rule, trace_config(), dt_ms=0.5, delay_steps=2
    )
    outgoing = {
        node: np.arange(graph.out_indptr[node], graph.out_indptr[node + 1])
        for node in range(graph.n_nodes)
    }
    engine.observe_step(0, np.array([0]), outgoing[0])
    # Node 2 spikes one step too early: the packet is not yet delivered.
    assert engine.observe_step(1, np.array([2]), outgoing[2]) == 0
    # At step 2 the packet is delivered but node 2 is silent.
    assert engine.observe_step(2, np.array([], dtype=np.int64), np.empty(0, dtype=np.int64)) == 0
    assert engine.n_coincident_tags == 0


def test_traces_disabled_engine_never_updates():
    graph, policy = simple_chain()
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.1), state)
    engine = PlasticityEngine(
        graph,
        state,
        rule,
        None,
        dt_ms=0.5,
        delay_steps=2,
        enable_traces=False,
    )
    engine.observe_step(0, np.array([0]), np.array([0]))
    assert engine.learn(0, 1.0) is None
    assert state.n_update_calls == 0


# -- reward predictor separation -------------------------------------------


def test_predictor_error_drives_the_rule_without_touching_the_schedule():
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=48, seed=8)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.001), state)
    predictor = TabularValuePredictor(gamma=0.0, learning_rate=0.5)
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config(),
        reward_provider=StepRewards({10: 2.0, 20: 2.0}),
        predictor=predictor,
        dt_ms=0.5,
        duration_ms=12.0,
        seed=3,
    )
    result = simulator.run()
    assert len(result.update_reports) == 2
    first, second = result.update_reports
    assert first.delta_t == pytest.approx(2.0)
    assert second.delta_t == pytest.approx(1.0)  # V(episode) is now 1.0
    assert predictor.value("episode") == pytest.approx(1.5)


# -- step callback reward source -------------------------------------------


class TimedRewardCallback:
    """Return a reward on named steps and None elsewhere."""

    def __init__(self, rewards: dict[int, float]) -> None:
        self.rewards = dict(rewards)
        self.calls = 0

    def reset(self) -> None:
        self.calls = 0

    def __call__(self, step: int, time_ms: float, spikes, simulator=None):
        del time_ms, spikes, simulator
        self.calls += 1
        return self.rewards.get(step)


def test_step_callback_reward_takes_precedence_over_the_provider():
    graph, policy = synthetic_substrate(n_nodes=64, n_edges=800, seed=5)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.05), state)
    callback = TimedRewardCallback({10: 0.0, 79: -1.0})
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config(),
        step_callback=callback,
        reward_provider=StepRewards({10: 5.0}),
        dt_ms=0.5,
        duration_ms=40.0,
        seed=7,
        noise_std_pa=40.0,
        stimulation=BancStimulation(np.arange(16), 500.0, 0.0, 40.0),
    )
    result = simulator.run()
    assert callback.calls == result.n_steps
    assert [report.step for report in result.update_reports] == [10, 79]
    assert result.update_reports[0].delta_t == 0.0
    assert result.update_reports[0].n_slots == 0
    assert result.update_reports[1].delta_t == pytest.approx(-1.0)
    # The zero-error event carries no eligible slots, so only step 79 applies.
    assert state.n_update_calls == 1
    assert np.any(state.delta_exc < 0)
    assert not np.any(state.delta_exc > 0)


def test_step_callback_with_eta_zero_changes_nothing():
    graph, policy = synthetic_substrate(n_nodes=64, n_edges=800, seed=5)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.0), state)
    callback = TimedRewardCallback({10: 1.0})
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config(),
        step_callback=callback,
        dt_ms=0.5,
        duration_ms=20.0,
        seed=7,
        noise_std_pa=40.0,
        stimulation=BancStimulation(np.arange(16), 500.0, 0.0, 20.0),
    )
    result = simulator.run()
    assert callback.calls == result.n_steps
    # eta = 0 still reports the scheduled event, but applies no update.
    assert len(result.update_reports) == 1
    assert result.update_reports[0].step == 10
    assert result.update_reports[0].n_updates == 0
    assert state.n_update_calls == 0
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)


def test_step_callback_must_be_callable():
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=48, seed=8)
    with pytest.raises(TypeError, match="step_callback"):
        PlasticSimulator(graph, policy, step_callback=3)


# -- checkpoints ------------------------------------------------------------


def test_checkpoint_round_trip_restores_learned_and_trace_state(tmp_path):
    graph, policy = synthetic_substrate(n_nodes=24, n_edges=120, seed=9)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.05), state)
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=trace_config(),
        reward_provider=StepRewards({20: 1.0, 40: -1.0}),
        dt_ms=0.5,
        duration_ms=25.0,
        seed=4,
        stimulation=BancStimulation(np.array([0, 1]), 500.0, 0.0, 25.0),
    )
    result = simulator.run()
    assert len(result.update_reports) == 2
    path = tmp_path / "checkpoint.npz"
    payload = save_checkpoint(
        path,
        weight_state=state,
        graph=graph,
        policy=policy,
        config={"eta": 0.05},
        trace_store=simulator.engine.trace_store,
        step=result.n_steps,
        seed=4,
    )
    assert payload["graph_checksum"] == graph_checksum(graph)

    restored_state = WeightState(graph, policy)
    restored_rule = ThreeFactorRule(RuleConfig(eta=0.05), restored_state)
    restored = PlasticSimulator(
        graph,
        policy,
        weight_state=restored_state,
        rule=restored_rule,
        trace_config=trace_config(),
        dt_ms=0.5,
        duration_ms=1.0,
        seed=4,
    )
    info = load_checkpoint(
        path,
        weight_state=restored_state,
        graph=graph,
        policy=policy,
        trace_store=restored.engine.trace_store,
    )
    assert info["weight_digest"] == state.delta_digest()
    assert info["effective_digest"] == state.effective_digest()
    assert restored_state.delta_digest() == state.delta_digest()
    assert (
        restored.engine.trace_store.digest()
        == simulator.engine.trace_store.digest()
    )
    assert info["restored_traces"] is True
    assert info["metadata"]["step"] == result.n_steps


def test_checkpoint_rejects_a_different_graph(tmp_path):
    graph, policy = synthetic_substrate(n_nodes=24, n_edges=120, seed=9)
    state = WeightState(graph, policy)
    state.apply_update(np.flatnonzero(state.plastic)[:2], [0.2, 0.2])
    path = tmp_path / "checkpoint.npz"
    save_checkpoint(
        path, weight_state=state, graph=graph, policy=policy, config={}
    )
    other_graph, other_policy = synthetic_substrate(
        n_nodes=24, n_edges=120, seed=10
    )
    other_state = WeightState(other_graph, other_policy)
    with pytest.raises(ValueError, match="different structural graph"):
        load_checkpoint(
            path, weight_state=other_state, graph=other_graph, policy=other_policy
        )


def test_checkpoint_rejects_tampered_weights(tmp_path):
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=60, seed=11)
    state = WeightState(graph, policy)
    state.apply_update(np.flatnonzero(state.plastic)[:2], [0.2, 0.2])
    path = tmp_path / "checkpoint.npz"
    save_checkpoint(
        path, weight_state=state, graph=graph, policy=policy, config={}
    )
    original = np.load(path, allow_pickle=False)
    arrays = {key: original[key] for key in original.files}
    original.close()
    tampered = arrays["delta_exc"].copy()
    tampered[np.flatnonzero(state.plastic)[0]] += 0.5
    arrays["delta_exc"] = tampered
    tampered_path = tmp_path / "tampered.npz"
    np.savez_compressed(tampered_path, **arrays)
    fresh = WeightState(graph, policy)
    with pytest.raises(ValueError, match="do not match their digest"):
        load_checkpoint(
            tampered_path, weight_state=fresh, graph=graph, policy=policy
        )
    assert fresh.delta_digest() == WeightState(graph, policy).delta_digest()


# -- memory and summary -----------------------------------------------------


def test_memory_breakdown_counts_shared_effective_arrays_once():
    _, simulator, _ = build_pair(eta=0.0, duration_ms=2.0)
    result = simulator.run()
    memory = result.summary["memory"]
    recomputed = (
        memory["weight_state_bytes"]
        + memory["engine_bytes"]
        + memory["neuron_state_bytes"]
        + memory["synapse_state_bytes"]
        - memory["shared_effective_weight_bytes"]
        + memory["spike_recorder_bytes"]
    )
    assert memory["retained_arrays_bytes"] == recomputed
    assert memory["shared_effective_weight_bytes"] > 0


def test_summary_records_model_status_and_digests():
    _, simulator, state = build_pair(eta=0.0, duration_ms=3.0)
    result = simulator.run()
    summary = result.summary
    assert summary["simulation"]["pathway"] == "plastic_three_factor"
    assert summary["model"]["rule"]["eta"] == 0.0
    assert summary["plasticity"]["weight_state"]["digests"]["learned_delta"] == (
        state.digest()
    )
    assert summary["diagnostics"]["spike_hash"] == result.spike_hash
    assert summary["activity"]["n_neurons"] == simulator.n_neurons
