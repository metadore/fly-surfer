"""Phase 5: reward provenance, modulation and reward-modulated plasticity.

These tests exercise the additive Phase 5 components on small synthetic
BANC-format substrates. They never touch ``datasets/``. A weight here is a
transformed structural synapse count in pA, not a conductance.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from brain.banc_simulator import BancSimulator, BancStimulation
from plasticity.checkpoint import (
    graph_checksum,
    load_checkpoint,
    policy_digest,
    save_checkpoint,
)
from plasticity.diagnostics import spike_hash, summarize_updates
from plasticity.modulation import (
    REWARD_SOURCE_EXPERIMENTAL,
    REWARD_SOURCE_UNAVAILABLE,
    ModulationConfig,
    ModulationRewardProvider,
    RewardDelivery,
    RewardModulation,
    RewardStream,
)
from plasticity.plastic_simulator import PlasticSimulator
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.synthetic import synthetic_substrate
from plasticity.traces import TraceConfig
from plasticity.weights import WeightBounds, WeightState

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = (
    PROJECT_ROOT / "experiments" / "phase_5" / "run_banc_reward_plasticity.py"
)
EXPERIMENT_CONFIG = PROJECT_ROOT / "configs" / "plasticity_banc.yaml"

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


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "phase5_banc_reward_plasticity", RUNNER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return load_runner()


@pytest.fixture(scope="module")
def substrate():
    return synthetic_substrate(n_nodes=64, n_edges=800, seed=5)


def simulate(
    graph,
    policy,
    state,
    *,
    eta: float,
    provider=None,
    traces: bool = True,
    duration_ms: float = 80.0,
    stim: np.ndarray | None = None,
    current_pa: float = 500.0,
    seed: int = 7,
):
    stimulation = BancStimulation(
        np.arange(16) if stim is None else np.asarray(stim, dtype=np.int64),
        current_pa,
        0.0,
        duration_ms,
    )
    return PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=ThreeFactorRule(RuleConfig(eta=eta), state),
        trace_config=trace_config() if traces else None,
        enable_traces=traces,
        reward_provider=provider,
        dt_ms=0.5,
        duration_ms=duration_ms,
        seed=seed,
        noise_std_pa=25.0,
        stimulation=stimulation,
        max_recorded_spikes=200_000,
    ).run()


def changed_edges(state: WeightState) -> int:
    return int(np.count_nonzero(state.delta_exc + state.delta_inh))


def plastic_edge(state: WeightState, sign: int) -> int:
    positions = np.flatnonzero(state.sign_class == sign)
    assert positions.size
    return int(positions[0])


# -- reward provenance and classification ----------------------------------


def test_stream_classifies_positive_negative_neutral_and_missing():
    stream = RewardStream(
        [
            RewardDelivery(1.0, 1.0),
            RewardDelivery(2.0, -0.5),
            RewardDelivery(3.0, 0.0),
            RewardDelivery(4.0, None, source=REWARD_SOURCE_UNAVAILABLE),
        ],
        provenance="declared test events",
    )
    counts = stream.counts()
    assert counts == {"positive": 1, "negative": 1, "neutral": 1, "missing": 1}
    assert stream.total() == pytest.approx(0.5)
    events = stream.describe()["events"]
    assert events[3]["available"] is False
    assert events[3]["magnitude"] is None
    assert events[2]["available"] is True
    assert events[2]["magnitude"] == 0.0
    assert all(item["source"] == REWARD_SOURCE_EXPERIMENTAL for item in events[:3])


def test_tuple_events_carry_source_and_derive_missing_source():
    stream = RewardStream(
        [
            (5.0, 1.0),
            (6.0, 0.0, "external", "neutral", "declared"),
            (7.0, None),
        ]
    )
    sources = [item.source for item in stream.deliveries]
    assert sources == [
        REWARD_SOURCE_EXPERIMENTAL,
        "external",
        REWARD_SOURCE_UNAVAILABLE,
    ]
    assert stream.deliveries[1].label == "neutral"
    assert stream.deliveries[1].provenance == "declared"


@pytest.mark.parametrize(
    "time_ms, magnitude, source",
    [
        (1.0, None, REWARD_SOURCE_EXPERIMENTAL),
        (1.0, 0.0, REWARD_SOURCE_UNAVAILABLE),
        (1.0, 1.0, "gamepad"),
        (-1.0, 1.0, REWARD_SOURCE_EXPERIMENTAL),
    ],
)
def test_invalid_reward_deliveries_are_rejected(time_ms, magnitude, source):
    with pytest.raises(ValueError):
        RewardDelivery(time_ms, magnitude, source=source)


def test_stream_sorts_events_and_preserves_digest():
    first = RewardStream([(9.0, 1.0), (2.0, -1.0)])
    second = RewardStream([(2.0, -1.0), (9.0, 1.0)])
    assert [item.time_ms for item in first.deliveries] == [2.0, 9.0]
    assert first.digest() == second.digest()


def test_due_between_is_half_open():
    stream = RewardStream([(10.0, 1.0), (20.0, 1.0)])
    assert stream.due_between(9.0, 10.0) == (stream.deliveries[0],)
    assert stream.due_between(10.0, 20.0) == (stream.deliveries[1],)
    assert stream.due_between(20.0, 20.0) == ()
    assert stream.due_between(20.1, 30.0) == ()


# -- modulation ------------------------------------------------------------


def test_modulation_decays_exponentially_between_events():
    modulation = RewardModulation(ModulationConfig(decay_tau_ms=100.0))
    first = modulation.deliver(RewardDelivery(0.0, 1.0), step=0)
    assert first.phasic_modulation == 1.0
    assert modulation.value == pytest.approx(1.0)
    second = modulation.deliver(RewardDelivery(100.0, 1.0), step=10)
    state_at_100 = 1.0 + np.exp(-1.0)
    assert second.modulation_state == pytest.approx(state_at_100)
    assert modulation.value_at(200.0) == pytest.approx(state_at_100 * np.exp(-1.0))
    series = modulation.series([0.0, 100.0, 200.0])
    assert series[0] == pytest.approx(1.0, abs=1e-9)
    assert series[1] == pytest.approx(state_at_100, abs=1e-9)
    assert series[2] == pytest.approx(state_at_100 * np.exp(-1.0), abs=1e-9)


def test_modulation_clips_and_applies_gain():
    modulation = RewardModulation(
        ModulationConfig(gain=2.0, decay_tau_ms=50.0, clip_abs=0.5)
    )
    record = modulation.deliver(RewardDelivery(0.0, 4.0))
    assert record.phasic_modulation == 0.5
    assert record.modulation_state == 0.5
    with pytest.raises(ValueError):
        RewardModulation(ModulationConfig(decay_tau_ms=0.0))
    with pytest.raises(ValueError):
        ModulationConfig.from_config({"decay_tau_ms": 10.0, "gamma": 1.0})


def test_missing_delivery_decays_but_emits_no_phasic_value():
    modulation = RewardModulation(ModulationConfig(decay_tau_ms=100.0))
    modulation.deliver(RewardDelivery(0.0, 1.0))
    record = modulation.deliver(
        RewardDelivery(100.0, None, source=REWARD_SOURCE_UNAVAILABLE)
    )
    assert record.phasic_modulation is None
    assert record.available is False
    assert record.modulation_state == pytest.approx(np.exp(-1.0))
    assert modulation.n_missing == 1


def test_modulation_is_reproducible_from_the_same_event_log():
    def build():
        return RewardModulation(ModulationConfig(decay_tau_ms=25.0))

    def feed(modulation):
        for time, magnitude in ((0.0, 1.0), (10.0, -0.5), (40.0, 0.25)):
            modulation.deliver(RewardDelivery(time, magnitude))

    left, right = build(), build()
    feed(left)
    feed(right)
    assert left.digest() == right.digest()
    assert left.describe() == right.describe()


# -- provider semantics ----------------------------------------------------


def make_provider(events, *, tau=50.0):
    return ModulationRewardProvider(
        RewardStream(events), RewardModulation(ModulationConfig(decay_tau_ms=tau))
    )


def drive(provider, duration_ms, dt_ms=0.5):
    values = []
    n_steps = int(round(duration_ms / dt_ms))
    for step in range(n_steps):
        values.append(provider.step(step, step * dt_ms))
    return values


def test_provider_emits_only_at_available_events_and_logs_missing():
    provider = make_provider(
        [
            (10.0, 1.0),
            (20.0, -1.0),
            (30.0, 0.0),
            (40.0, None),
        ]
    )
    values = drive(provider, 50.0)
    nonzero = [(index, value) for index, value in enumerate(values) if value is not None]
    assert nonzero == [(20, 1.0), (40, -1.0), (60, 0.0)]
    assert provider.n_update_steps == 3
    assert provider.n_missing_events == 1
    assert provider.n_steps_without_reward == 97
    assert provider.emitted_modulation == pytest.approx(0.0)
    assert provider.modulation.n_missing == 1


def test_provider_returns_none_when_only_missing_reward_is_due():
    provider = make_provider([(10.0, None)])
    values = drive(provider, 20.0)
    assert all(value is None for value in values)
    assert provider.n_update_steps == 0
    assert provider.n_missing_events == 1
    assert provider.modulation.n_events == 1


def test_provider_neutral_reward_is_not_treated_as_missing():
    provider = make_provider([(10.0, 0.0)])
    values = drive(provider, 20.0)
    assert values[20] == 0.0
    assert provider.n_update_steps == 1
    assert provider.n_missing_events == 0


def test_provider_rejects_time_regression():
    provider = make_provider([(10.0, 1.0)])
    provider.step(5, 5.0)
    with pytest.raises(ValueError):
        provider.step(1, 1.0)


# -- update arithmetic and bounds -----------------------------------------


def test_three_factor_update_matches_declared_arithmetic(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=2.0), state)
    exc_edge = plastic_edge(state, 1)
    inh_edge = plastic_edge(state, -1)
    initial_exc = float(state.initial_exc[exc_edge])
    initial_inh = float(state.initial_inh[inh_edge])
    report = rule.apply(0, [exc_edge, inh_edge], [0.25, 0.25], delta_t=4.0)
    assert report.n_slots == 2
    assert report.n_updates == 2
    assert report.sum_abs_applied_pa == pytest.approx(4.0)
    assert state.delta_exc[exc_edge] == pytest.approx(2.0, abs=1e-6)
    assert state.delta_inh[inh_edge] == pytest.approx(2.0, abs=1e-6)
    assert state.effective_exc[exc_edge] == pytest.approx(initial_exc + 2.0, abs=1e-5)
    assert state.effective_inh[inh_edge] == pytest.approx(initial_inh + 2.0, abs=1e-5)
    assert state.n_update_calls == 1


def test_zero_eta_never_writes_weights(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=0.0), state)
    edge = plastic_edge(state, 1)
    report = rule.apply(0, [edge], [0.5], delta_t=10.0)
    assert report.n_updates == 0
    assert state.n_update_calls == 0
    assert changed_edges(state) == 0


def test_weight_bounds_clamp_the_effective_weight(substrate):
    graph, policy = substrate
    state = WeightState(
        graph, policy, WeightBounds(lower_factor=0.5, upper_factor=2.0)
    )
    rule = ThreeFactorRule(RuleConfig(eta=1.0), state)
    edge = plastic_edge(state, 1)
    initial = float(state.initial_exc[edge])
    upper = rule.apply(0, [edge], [1.0], delta_t=1.0e6)
    assert state.effective_exc[edge] == pytest.approx(2.0 * initial, rel=1e-6)
    assert upper.clamp_hits == 1
    lower = rule.apply(1, [edge], [1.0], delta_t=-1.0e6)
    assert state.effective_exc[edge] == pytest.approx(0.5 * initial, rel=1e-6)
    assert lower.clamp_hits == 1
    state.assert_invariants()


def test_max_abs_update_pa_clips_one_update(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy, WeightBounds(max_abs_update_pa=2.0))
    rule = ThreeFactorRule(RuleConfig(eta=1.0), state)
    edge = plastic_edge(state, 1)
    initial = float(state.initial_exc[edge])
    report = rule.apply(0, [edge], [1.0], delta_t=100.0)
    assert report.update_clip_hits == 1
    assert report.sum_abs_applied_pa == pytest.approx(2.0, abs=1e-6)
    assert state.delta_exc[edge] == pytest.approx(2.0, abs=1e-6)
    assert state.effective_exc[edge] == pytest.approx(initial + 2.0, abs=1e-5)


def test_no_activity_produces_no_weight_update(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=5.0), state)
    report = rule.apply(0, np.empty(0, dtype=np.int64), np.empty(0), delta_t=1.0)
    assert report.n_slots == 0
    assert report.n_updates == 0
    assert state.n_update_calls == 0
    assert changed_edges(state) == 0


def test_simulation_without_spikes_changes_nothing(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    provider = make_provider([(5.0, 1.0)])
    result = simulate(
        graph,
        policy,
        state,
        eta=5.0,
        provider=provider,
        duration_ms=10.0,
        stim=np.arange(4),
        current_pa=0.0,
    )
    assert result.summary["activity"]["n_spikes"] == 0
    assert changed_edges(state) == 0
    assert state.n_update_calls == 0
    assert provider.n_update_steps == 1


def test_missing_reward_triggers_no_update_even_with_spikes(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    provider = make_provider([(20.0, None)])
    result = simulate(graph, policy, state, eta=5.0, provider=provider)
    assert result.summary["activity"]["n_spikes"] > 0
    assert provider.modulation.n_events == 1
    assert result.update_reports == ()
    assert state.n_update_calls == 0
    assert changed_edges(state) == 0


# -- graph immutability and checkpoints -----------------------------------


def test_structural_graph_and_policy_are_not_modified(substrate):
    graph, policy = substrate
    before_edges = np.array(graph.edge_weight, copy=True)
    before_src = np.array(graph.edge_src, copy=True)
    before_dst = np.array(graph.edge_dst, copy=True)
    before_roots = np.array(graph.root_ids, copy=True)
    before_checksum = graph_checksum(graph)
    before_policy = policy_digest(policy)
    before_initial = np.array(policy.edge_exc_weight, copy=True)

    state = WeightState(graph, policy)
    structural_digest = state.structural_digest()
    initial_digest = state.initial_digest()
    provider = make_provider([(20.0, 1.0), (40.0, -1.0)])
    simulate(graph, policy, state, eta=5.0, provider=provider)

    assert changed_edges(state) > 0
    assert np.array_equal(graph.edge_weight, before_edges)
    assert np.array_equal(graph.edge_src, before_src)
    assert np.array_equal(graph.edge_dst, before_dst)
    assert np.array_equal(graph.root_ids, before_roots)
    assert np.array_equal(policy.edge_exc_weight, before_initial)
    assert graph_checksum(graph) == before_checksum
    assert policy_digest(policy) == before_policy
    assert state.structural_digest() == structural_digest
    assert state.initial_digest() == initial_digest
    assert state.structural_count.flags.writeable is False


def test_checkpoint_roundtrip_restores_learned_weights(substrate, tmp_path):
    graph, policy = substrate
    trained = WeightState(graph, policy)
    provider = make_provider([(20.0, 1.0), (40.0, 1.0)])
    simulate(graph, policy, trained, eta=5.0, provider=provider)
    assert changed_edges(trained) > 0

    path = tmp_path / "checkpoint.npz"
    metadata = save_checkpoint(
        path,
        weight_state=trained,
        graph=graph,
        policy=policy,
        config={"experiment": "test"},
        step=160,
        seed=7,
    )
    assert metadata["delta_digest"] == trained.delta_digest()

    restored = WeightState(graph, policy)
    loaded = load_checkpoint(path, weight_state=restored, graph=graph, policy=policy)
    assert loaded["weight_digest"] == trained.delta_digest()
    assert np.array_equal(restored.delta_exc, trained.delta_exc)
    assert np.array_equal(restored.delta_inh, trained.delta_inh)
    assert np.array_equal(restored.effective_exc, trained.effective_exc)
    assert loaded["effective_digest"] == trained.effective_digest()


def test_checkpoint_refuses_a_different_graph(substrate, tmp_path):
    graph, policy = substrate
    other_graph, other_policy = synthetic_substrate(
        n_nodes=64, n_edges=800, seed=6
    )
    state = WeightState(graph, policy)
    simulate(
        graph,
        policy,
        state,
        eta=5.0,
        provider=make_provider([(20.0, 1.0)]),
    )
    path = tmp_path / "checkpoint.npz"
    save_checkpoint(
        path,
        weight_state=state,
        graph=graph,
        policy=policy,
        config={},
    )
    with pytest.raises(ValueError):
        load_checkpoint(
            path,
            weight_state=WeightState(other_graph, other_policy),
            graph=other_graph,
            policy=other_policy,
        )


def test_checkpoint_refuses_tampered_deltas(substrate, tmp_path):
    graph, policy = substrate
    state = WeightState(graph, policy)
    simulate(
        graph,
        policy,
        state,
        eta=5.0,
        provider=make_provider([(20.0, 1.0)]),
    )
    path = tmp_path / "checkpoint.npz"
    save_checkpoint(path, weight_state=state, graph=graph, policy=policy, config={})
    with np.load(path, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    touched = np.flatnonzero(arrays["delta_exc"])
    assert touched.size
    arrays["delta_exc"] = arrays["delta_exc"].copy()
    arrays["delta_exc"][touched[0]] += 1.0
    np.savez_compressed(path, **arrays)
    with pytest.raises(ValueError):
        load_checkpoint(
            path,
            weight_state=WeightState(graph, policy),
            graph=graph,
            policy=policy,
        )


# -- controls and end-to-end integration ----------------------------------


def test_no_plasticity_control_reproduces_fixed_weight_spikes(substrate):
    graph, policy = substrate
    stimulation = BancStimulation(np.arange(16), 500.0, 0.0, 80.0)
    fixed = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=80.0,
        seed=7,
        noise_std_pa=25.0,
        stimulation=stimulation,
        max_recorded_spikes=200_000,
    ).run()
    state = WeightState(graph, policy)
    provider = make_provider([(20.0, 1.0), (40.0, -1.0)])
    control = simulate(graph, policy, state, eta=0.0, provider=provider)
    assert control.spike_hash == spike_hash(fixed.recorder)
    assert np.array_equal(
        control.recorder.spike_times_ms, fixed.recorder.spike_times_ms
    )
    assert np.array_equal(
        control.recorder.spike_neuron_indices, fixed.recorder.spike_neuron_indices
    )
    assert provider.n_update_steps == 2
    assert len(control.update_reports) == 2
    assert all(report.n_updates == 0 for report in control.update_reports)
    assert state.n_update_calls == 0
    assert changed_edges(state) == 0


def test_reward_training_changes_weights_and_subsequent_spike_timing(substrate, runner):
    graph, policy = substrate
    events = [
        (10.0, 1.0),
        (20.0, 1.0),
        (30.0, 1.0),
        (40.0, -1.0),
        (50.0, 0.0),
    ]
    baseline_state = WeightState(graph, policy)
    baseline = simulate(graph, policy, baseline_state, eta=0.0)

    trained = WeightState(graph, policy)
    training_provider = make_provider(events)
    training = simulate(graph, policy, trained, eta=5.0, provider=training_provider)
    assert len(training.update_reports) == 5
    assert changed_edges(trained) > 0
    assert trained.delta_digest() != baseline_state.delta_digest()

    post = simulate(graph, policy, trained, eta=0.0, traces=False)
    assert post.spike_hash != baseline.spike_hash
    assert not np.array_equal(
        post.recorder.spike_times_ms, baseline.recorder.spike_times_ms
    )
    difference = runner.spike_sequence_difference(baseline, post)
    assert (
        difference["n_neurons_with_timing_change"] > 0
        or difference["n_neurons_with_count_change"] > 0
    )
    assert difference["max_abs_timing_shift_ms"] > 0.0

    # A second identical training run is deterministic in weights, spikes and
    # modulation log.
    repeat_state = WeightState(graph, policy)
    repeat_provider = make_provider(events)
    repeat = simulate(
        graph, policy, repeat_state, eta=5.0, provider=repeat_provider
    )
    assert repeat.spike_hash == training.spike_hash
    assert repeat_state.delta_digest() == trained.delta_digest()
    assert repeat_provider.modulation.digest() == training_provider.modulation.digest()

    # Post-control with the original weights reproduces the baseline exactly.
    post_control = simulate(graph, policy, WeightState(graph, policy), eta=0.0, traces=False)
    assert post_control.spike_hash == baseline.spike_hash
    control_difference = runner.spike_sequence_difference(baseline, post_control)
    assert control_difference["n_neurons_with_count_change"] == 0
    assert control_difference["n_neurons_with_timing_change"] == 0
    assert control_difference["max_abs_timing_shift_ms"] == 0.0


def test_exported_weights_drive_the_same_post_update_activity(substrate, tmp_path):
    graph, policy = substrate
    state = WeightState(graph, policy)
    simulate(
        graph,
        policy,
        state,
        eta=5.0,
        provider=make_provider([(20.0, 1.0), (40.0, 1.0)]),
    )
    direct = simulate(graph, policy, state, eta=0.0, traces=False)

    path = tmp_path / "learned.npz"
    save_checkpoint(path, weight_state=state, graph=graph, policy=policy, config={})
    reloaded_state = WeightState(graph, policy)
    load_checkpoint(path, weight_state=reloaded_state, graph=graph, policy=policy)
    reloaded = simulate(graph, policy, reloaded_state, eta=0.0, traces=False)
    assert reloaded.spike_hash == direct.spike_hash


def test_update_diagnostics_aggregate_the_event_reports(substrate):
    graph, policy = substrate
    state = WeightState(graph, policy)
    provider = make_provider([(20.0, 1.0), (40.0, -1.0), (60.0, 0.0)])
    result = simulate(graph, policy, state, eta=5.0, provider=provider)
    summary = summarize_updates(result.update_reports)
    assert summary["n_update_events"] == 3
    assert summary["n_changed_events"] >= 1
    assert summary["sum_abs_applied_pa"] > 0.0
    assert len(summary["records"]) == 3


# -- experiment runner helpers -------------------------------------------


def test_declared_experiment_config_builds_the_expected_reward_stream(runner):
    config = runner.load_experiment_config(EXPERIMENT_CONFIG)
    provider = runner.build_provider(config["reward"], config["modulation"])
    assert provider.stream.counts() == {
        "positive": 2,
        "negative": 1,
        "neutral": 1,
        "missing": 1,
    }
    values = drive(provider, 300.0)
    events = [
        (index * 0.5, value)
        for index, value in enumerate(values)
        if value is not None
    ]
    assert events == [(100.0, 1.0), (160.0, -1.0), (220.0, 1.0), (250.0, 0.0)]
    assert provider.n_update_steps == 4
    assert provider.n_missing_events == 1
    assert provider.n_steps_without_reward == 596
    assert provider.emitted_modulation == pytest.approx(1.0)


def test_declared_config_rejects_weak_controls(runner, tmp_path):
    payload = EXPERIMENT_CONFIG.read_text(encoding="utf-8")
    broken = tmp_path / "config.yaml"
    broken.write_text(
        payload.replace("control_eta: 0.0", "control_eta: 0.25"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        runner.load_experiment_config(broken)


def test_weight_change_statistics_report_changed_edges(runner):
    graph, policy = synthetic_substrate(n_nodes=32, n_edges=192, seed=11)
    state = WeightState(graph, policy)
    rule = ThreeFactorRule(RuleConfig(eta=1.0), state)
    exc = np.flatnonzero(state.sign_class == 1)[:4]
    rule.apply(0, exc, np.full(exc.size, 0.5), delta_t=2.0)
    stats = runner.weight_change_statistics(state)
    assert stats["n_changed_edges"] == 4
    assert stats["mean_abs_pa"] == pytest.approx(1.0, abs=1e-6)
    assert stats["max_abs_pa"] == pytest.approx(1.0, abs=1e-6)
    assert stats["positive_changes"] == 4
    assert sum(stats["histogram"]["counts"]) == 4
    assert stats["digests"]["learned_delta"] == state.delta_digest()


def test_comparison_helper_reports_activity_and_decoder_deltas(runner):
    reference = {
        "label": "baseline",
        "spike_hash": "a",
        "activity": {
            key: 10
            for key in (
                "total_spikes",
                "motor_spikes",
                "motor_active_neurons",
                "non_motor_spikes",
                "stimulated_spikes",
                "downstream_spikes",
                "active_neurons",
            )
        },
        "populations": {"motor": {}},
        "decode_window": {"populations": {"motor": {"spikes": 4}}},
        "decoder_outputs": [{"window_start_ms": 0.0, "state": "NO_ACTION"}],
        "decoded_state_counts": {"NO_ACTION": 1},
        "weights": {"digests": {"learned_delta": "d"}},
    }
    candidate = json.loads(json.dumps(reference))
    candidate["label"] = "post_update"
    candidate["spike_hash"] = "b"
    candidate["activity"]["total_spikes"] = 12
    candidate["decode_window"]["populations"]["motor"]["spikes"] = 6
    candidate["decoder_outputs"][0]["state"] = "JUMP"
    candidate["decoded_state_counts"] = {"JUMP": 1}
    candidate["weights"]["digests"]["learned_delta"] = "e"

    compared = runner.compare(reference, candidate)
    assert compared["spike_hash_equal"] is False
    assert compared["activity_delta"]["total_spikes"] == 2
    assert compared["population_spike_delta"]["motor"] == 2
    assert compared["decoded_state_counts_equal"] is False
    assert compared["decoder_window_mismatches"] == 1
    assert compared["weight_digest_equal"] is False
