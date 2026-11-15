"""Focused tests for the P3-T2 same-graph causal-control infrastructure.

These tests validate the runner's plumbing only: condition construction, the
fixed reference set, the current audit, per-feature attribution, hashing and
invalidation. They run at most a 100 ms smoke window; the preregistered
3300.5 ms experiment is not executed here.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from brain.brain_simulator import BrainSimulator
from experiments.phase_3c import causal_control as cc
from sensory.game_state import GameState, PlayerState

TWELVE = 1000.0 / 30.0


@pytest.fixture(scope="module")
def config() -> cc.CausalControlConfig:
    return cc.CausalControlConfig.load()


@pytest.fixture(scope="module")
def loaded(config):
    return cc._load_setup(config)


@pytest.fixture(scope="module")
def setup(loaded):
    return loaded[0]


@pytest.fixture(scope="module")
def neuron_params(loaded):
    return loaded[1]


@pytest.fixture(scope="module")
def synapse_params(loaded):
    return loaded[2]


@pytest.fixture(scope="module")
def cache(config) -> cc.CausalFrameCache:
    if not (cc.PROJECT_ROOT / config.cache["path"]).is_file():
        pytest.skip("run `--build-cache` before the cache-dependent tests")
    return cc.load_cache(config)


@pytest.fixture(scope="module")
def smoke(config, cache) -> dict:
    return cc.run_experiment(
        condition_names=["C0", "C1", "C2", "C3"],
        config=config,
        smoke_ms=100.0,
        repeats=1,
    )


def test_config_preregisters_exact_feature_split(config) -> None:
    assert len(config.all_features) == 14
    assert len(config.non_player_features) == 10
    assert len(config.player_features) == 4
    assert sum(config.feature_neurons.values()) == 138
    assert sum(config.feature_neurons[name] for name in config.player_features) == 36
    assert (
        sum(config.feature_neurons[name] for name in config.non_player_features) == 102
    )
    assert config.all_features == cc.FEATURES
    assert config.reference["n_steps"] * config.reference["dt_ms"] == pytest.approx(
        config.reference["duration_ms"]
    )
    with pytest.raises(ValueError):
        config.condition("C9")


def test_condition_definitions_are_fixed(config) -> None:
    c0 = config.condition("C0")
    assert c0.frame_source == "none"
    assert c0.active_features == ()
    c1 = config.condition("C1")
    assert c1.frame_source == "neutral"
    assert c1.active_features == config.player_features
    c2 = config.condition("C2")
    assert c2.frame_source == "cached"
    assert c2.active_features == config.non_player_features
    c3 = config.condition("C3")
    assert c3.frame_source == "cached"
    assert c3.active_features is None


def test_c0_has_no_input_schedule(config, setup, smoke) -> None:
    assert cc.build_scheduler(config.condition("C0"), setup, ()) is None
    assert cc.resolve_frames(config.condition("C0"), config, None, smoke_ms=None) == ()
    item = smoke["conditions"]["C0"]
    assert item["scheduler"]["present"] is False
    assert item["scheduler"]["n_stimulated_neurons"] == 0
    assert item["n_active_neurons"] == 0
    audit = item["current_audit"]
    assert audit["total_injected_pa_steps"] == 0.0
    assert audit["n_neurons_with_nonzero_current"] == 0
    assert item["simulation"]["spikes_total"] == 0


def test_c0_simulator_receives_no_schedule(
    config, setup, neuron_params, synapse_params
) -> None:
    scheduler = cc.build_scheduler(config.condition("C0"), setup, ())
    simulator = BrainSimulator(
        setup.mapping.graph,
        neuron_params,
        synapse_params,
        dt_ms=config.reference["dt_ms"],
        duration_ms=1.0,
        seed=config.reference["simulation_seed"],
        input_schedule=scheduler,
    )
    assert simulator.input_schedule is None


def test_neutral_frames_are_player_defaults(config) -> None:
    frames = cc.neutral_frames(100, 30.0)
    assert len(frames) == 100
    assert frames[0].time_ms == pytest.approx(0.0)
    assert frames[1].time_ms == pytest.approx(TWELVE, abs=1e-9)
    for frame in frames:
        assert frame.state == GameState.neutral(frame.time_ms)
        assert frame.state.player == PlayerState()
        assert not frame.events
        assert frame.tracks == ()
        assert frame.features == frame.state.features()


def test_c1_neutral_currents_are_constant_and_player_only(config, smoke) -> None:
    item = smoke["conditions"]["C1"]
    audit = item["current_audit"]
    expected = config.reference["expected_neutral_current_pa"]
    assert audit["n_steps"] == 200
    assert audit["steps_with_current"] == 200
    assert audit["min_step_current_pa"] == pytest.approx(
        audit["max_step_current_pa"], abs=1e-6
    )
    assert audit["pulse_steps"] == 0
    assert audit["pulse_pa_steps"] == 0.0
    peaks = audit["peak_feature_current_pa"]
    assert peaks["player_lane"] == pytest.approx(expected["player_lane"], abs=1e-6)
    assert peaks["player_speed"] == pytest.approx(
        expected["player_speed"], abs=1e-6
    )
    assert peaks["jumping"] == 0.0 and peaks["rolling"] == 0.0
    for feature in config.non_player_features:
        assert peaks[feature] == 0.0, feature
    assert audit["n_indices_outside_active"] == 0
    assert item["n_active_neurons"] == 36
    assert item["scheduler"]["n_stimulated_neurons"] == 36


def test_c2_excludes_every_player_feature(config, smoke) -> None:
    item = smoke["conditions"]["C2"]
    assert set(item["active_features"]) == set(config.non_player_features)
    assert not set(item["active_features"]) & set(config.player_features)
    assert item["n_active_neurons"] == 102
    audit = item["current_audit"]
    for feature in config.player_features:
        assert audit["peak_feature_current_pa"][feature] == 0.0, feature
        assert audit["hold_only_peak_feature_current_pa"][feature] == 0.0, feature
    assert audit["n_indices_outside_active"] == 0
    assert item["n_active_neurons"] == 102


def test_c2_and_c3_share_the_same_cached_frames(config, cache, smoke) -> None:
    c2 = smoke["conditions"]["C2"]
    c3 = smoke["conditions"]["C3"]
    assert c2["cache_frames_digest"] == c3["cache_frames_digest"]
    assert c2["cache_frames_digest"] == cache.frames_digest
    assert c2["scheduler"]["n_frames"] == c3["scheduler"]["n_frames"]
    assert c3["n_reference_neurons"] == 138
    assert c3["n_active_neurons"] == c3["n_reference_neurons"]
    # The schedulers legitimately differ because C2 masks the player features.
    assert c2["scheduler"]["signature_sha256"] != c3["scheduler"]["signature_sha256"]


def test_cached_frames_match_the_archived_phase_3b2c_reference(config, cache) -> None:
    assert len(cache.frames) == int(config.reference["n_frames"])
    assert cache.frames[-1].time_ms == pytest.approx(3300.0)
    assert cache.frames_digest == config.archived["temporal_sha256"]
    assert cache.scheduler_signature_sha256 == config.archived["scheduler_sha256"]
    assert cache.manifest["matches_archived_temporal"] is True
    assert cache.manifest["matches_archived_scheduler"] is True
    assert cache.n_pulse_events == 43


def test_fixed_reference_set_accounting(smoke) -> None:
    total_neurons = None
    for name, item in smoke["conditions"].items():
        partitions = item["partitions"]
        total = partitions["total"]
        if total_neurons is None:
            total_neurons = total["n_neurons"]
        assert total["n_neurons"] == total_neurons, name
        assert total["spikes"] == (
            partitions["reference"]["spikes"]
            + partitions["outside_reference"]["spikes"]
        ), name
        assert total["spikes"] == (
            partitions["active"]["spikes"]
            + partitions["outside_active"]["spikes"]
        ), name
        assert partitions["reference"]["n_neurons"] == 138
        assert partitions["active"]["n_neurons"] == item["n_active_neurons"]
        n_bins = len(total["bins"])
        for partition in (
            "reference",
            "outside_reference",
            "active",
            "outside_active",
        ):
            assert len(partitions[partition]["bins"]) == n_bins, (name, partition)
        assert item["n_reference_neurons"] == 138


def test_reference_partition_uses_the_same_fixed_set(smoke) -> None:
    sizes = {
        item["partitions"]["total"]["n_neurons"]
        for item in smoke["conditions"].values()
    }
    assert len(sizes) == 1
    graph_neurons = sizes.pop()
    for item in smoke["conditions"].values():
        assert item["partitions"]["reference"]["n_neurons"] == 138
        assert (
            item["partitions"]["outside_reference"]["n_neurons"]
            == graph_neurons - 138
        )


def test_spikes_by_feature_attribution(smoke, config) -> None:
    for name, item in smoke["conditions"].items():
        by_feature = item["spikes_by_feature"]
        assert set(by_feature) == set(config.all_features), name
        assert sum(by_feature.values()) == (
            item["partitions"]["reference"]["spikes"]
        ), name
    assert all(
        value == 0 for value in smoke["conditions"]["C0"]["spikes_by_feature"].values()
    )


def test_in_process_repetitions_produce_identical_hashes(config) -> None:
    payload = cc.run_experiment(
        condition_names=["C1"], config=config, smoke_ms=5.0, repeats=2
    )
    item = payload["conditions"]["C1"]
    assert item["reproducibility"]["identical"] is True
    assert item["reproducibility"]["differences"] == []
    hashes = item["reproducibility_hashes"]
    assert len(hashes["spike_counts_sha256"]) == 64
    assert len(hashes["current_trace_sha256"]) == 64
    assert len(hashes["scheduler_signature_sha256"]) == 64


def _fake_item(**overrides) -> dict:
    item = {
        "spike_capacity_exceeded": False,
        "simulation": {
            "diagnostics": {
                "finite_state": True,
                "min_membrane_mv": -90.0,
                "max_membrane_mv": -50.0,
            }
        },
        "reproducibility": {"identical": True, "differences": []},
        "current_audit": {"n_indices_outside_active": 0},
        "cache_frames_digest": None,
        "scheduler": {"signature_sha256": None},
        "reproducibility_hashes": {"spike_counts_sha256": None},
        "initial_conditions": {"seed": 1},
        "condition": "X",
    }
    item.update(overrides)
    return item


def _protected_matching(config) -> dict:
    return {name: {"match": True} for name in cc.protected_hashes(config)}


def test_invalidations_accept_a_clean_payload(config) -> None:
    items = {"C0": _fake_item()}
    checks = {"C0": {"no_scheduler": True}}
    result = cc.evaluate_invalidations(
        items,
        checks,
        config,
        mode="smoke",
        protected=_protected_matching(config),
    )
    assert result["valid"] is True
    assert result["triggered"] == []
    assert result["archive_gate"] == "not applicable in smoke mode"


@pytest.mark.parametrize(
    ("overrides", "rule"),
    [
        ({"spike_capacity_exceeded": True}, "spike_capacity_exceeded"),
        (
            {"simulation": {"diagnostics": {"finite_state": False}}},
            "non_finite_state",
        ),
        (
            {
                "simulation": {
                    "diagnostics": {
                        "finite_state": True,
                        "min_membrane_mv": -120.0,
                        "max_membrane_mv": -50.0,
                    }
                }
            },
            "membrane_below_floor",
        ),
        (
            {
                "simulation": {
                    "diagnostics": {
                        "finite_state": True,
                        "min_membrane_mv": -90.0,
                        "max_membrane_mv": -10.0,
                    }
                }
            },
            "membrane_above_threshold",
        ),
        (
            {"reproducibility": {"identical": False, "differences": ["spikes_total"]}},
            "repeated_runs_differ",
        ),
        (
            {"current_audit": {"n_indices_outside_active": 3}},
            "current_outside_active_set",
        ),
    ],
)
def test_invalidations_detect_failures(config, overrides, rule) -> None:
    items = {"C1": _fake_item(**overrides)}
    checks = {"C1": {"no_scheduler": True}}
    result = cc.evaluate_invalidations(
        items,
        checks,
        config,
        mode="smoke",
        protected=_protected_matching(config),
    )
    assert result["valid"] is False
    assert rule in {entry["rule"] for entry in result["triggered"]}


def test_invalidations_detect_condition_and_input_failures(config) -> None:
    items = {
        "C2": _fake_item(cache_frames_digest="aaa"),
        "C3": _fake_item(cache_frames_digest="bbb"),
    }
    checks = {"C2": {"player_current_zero": False}, "C3": {"all_features_active": True}}
    protected = _protected_matching(config)
    protected["connectome"] = {"match": False}
    result = cc.evaluate_invalidations(
        items, checks, config, mode="smoke", protected=protected
    )
    rules = {entry["rule"] for entry in result["triggered"]}
    assert "condition_definition_violation" in rules
    assert "protected_hash_changed" in rules
    assert "cached_frames_differ_between_C2_and_C3" in rules
    assert "initial_conditions_differ" not in rules


def test_full_mode_enforces_the_c3_archive_gate(config) -> None:
    items = {
        "C3": _fake_item(
            scheduler={"signature_sha256": "0" * 64},
            reproducibility_hashes={"spike_counts_sha256": "1" * 64},
        )
    }
    result = cc.evaluate_invalidations(
        items,
        {"C3": {}},
        config,
        mode="full",
        protected=_protected_matching(config),
    )
    rules = {entry["rule"] for entry in result["triggered"]}
    assert "c3_scheduler_signature_mismatch" in rules
    assert "c3_spike_counts_mismatch" in rules
    assert result["archive_gate"] == "evaluated"


def test_smoke_100ms_runs_every_condition(smoke, config) -> None:
    assert list(smoke["conditions"]) == ["C0", "C1", "C2", "C3"]
    assert smoke["mode"] == "smoke"
    assert smoke["verdict"] == "SMOKE ONLY (infrastructure validation)"
    assert smoke["invalidations"]["triggered"] == []
    signatures = {
        json.dumps(item["initial_conditions"], sort_keys=True)
        for item in smoke["conditions"].values()
    }
    assert len(signatures) == 1
    for item in smoke["conditions"].values():
        assert item["simulation"]["n_steps"] == 200
        assert item["simulation"]["duration_ms"] == pytest.approx(100.0)
        assert item["simulation"]["diagnostics"]["finite_state"] is True
        assert item["reproducibility"]["identical"] is True
    assert smoke["conditions"]["C0"]["simulation"]["spikes_total"] == 0
    assert smoke["conditions"]["C1"]["simulation"]["spikes_total"] > 0


def test_smoke_marks_unobservable_c2_hold_components(smoke) -> None:
    item = smoke["conditions"]["C2"]
    checks = item["condition_checks"]
    assert item["condition_checks_not_evaluated"] == [
        "hold_component_included",
        "not_pulses_only",
    ]
    assert "hold_component_included" not in checks
    assert item["current_audit"]["pulse_pa_steps"] > 0.0


def test_smoke_600ms_observes_both_c2_components(config) -> None:
    payload = cc.run_experiment(
        condition_names=["C2"], config=config, smoke_ms=600.0, repeats=1
    )
    item = payload["conditions"]["C2"]
    assert item["condition_checks_not_evaluated"] == []
    assert item["condition_checks"]["hold_component_included"] is True
    assert item["condition_checks"]["not_pulses_only"] is True
    assert item["current_audit"]["hold_only_pa_steps"] > 0.0
    assert item["current_audit"]["pulse_pa_steps"] > 0.0


def test_audit_detects_current_outside_the_active_set(setup, config) -> None:
    frames = cc.neutral_frames(2, 30.0)
    full = cc.build_scheduler(config.condition("C1"), setup, frames)
    indices = cc.feature_index_map(setup)
    narrowed = cc.indices_for_features(setup, config.non_player_features)
    audit = cc.audit_currents(
        full,
        n_nodes=setup.mapping.graph.n_nodes,
        n_steps=4,
        dt_ms=0.5,
        feature_indices=indices,
        active_indices=narrowed,
    )
    player = set(
        int(index)
        for index in cc.indices_for_features(setup, config.player_features)
    )
    assert 0 < audit["n_indices_outside_active"] <= len(player)
    assert set(audit["indices_outside_active_first"]) <= player


def test_audit_partitions_steps_into_hold_and_pulse_windows(setup, config) -> None:
    frames = cc.neutral_frames(1, 30.0)
    scheduler = cc.build_scheduler(config.condition("C1"), setup, frames)
    indices = cc.feature_index_map(setup)
    active = cc.indices_for_features(setup, config.player_features)
    audit = cc.audit_currents(
        scheduler,
        n_nodes=setup.mapping.graph.n_nodes,
        n_steps=20,
        dt_ms=0.5,
        feature_indices=indices,
        active_indices=active,
        pulse_windows=((0.0, 5.0),),
    )
    assert audit["pulse_steps"] == 10
    assert audit["hold_only_steps"] == 10
    assert audit["hold_only_time_ms"] == pytest.approx(5.0)
    assert audit["pulse_pa_steps"] > 0.0
    assert audit["hold_only_pa_steps"] > 0.0
    assert audit["pulse_pa_steps"] + audit["hold_only_pa_steps"] == pytest.approx(
        audit["total_injected_pa_steps"], abs=1e-6
    )


def test_write_outputs_refuses_to_overwrite(tmp_path: Path) -> None:
    payload = {
        "phase": "P3-T2",
        "version": "v",
        "verdict": "SMOKE ONLY (infrastructure validation)",
        "mode": "smoke",
        "generated_at_utc": "now",
        "git": {},
        "config": {"sha256": "a" * 64},
        "cache": None,
        "invalidations": {"triggered": []},
    }
    target = tmp_path / "run.json"
    cc.write_outputs(payload, target)
    sidecar = tmp_path / "run.sidecar.json"
    assert target.is_file() and sidecar.is_file()
    with pytest.raises(FileExistsError):
        cc.write_outputs(payload, target)
    cc.write_outputs(payload, target, overwrite=True)
    assert sidecar.is_file()


def test_partition_metrics_are_consistent_with_counts() -> None:
    counts = np.array([0, 2, 1, 0], dtype=np.int64)
    spike_times = np.array([1.0, 2.0, 50.0], dtype=np.float64)
    spike_neurons = np.array([1, 1, 2], dtype=np.int64)
    mask = np.array([False, True, False, False])
    metrics = cc.partition_metrics(
        counts,
        spike_times,
        spike_neurons,
        mask,
        duration_ms=100.0,
        bin_ms=100.0,
    )
    assert metrics["n_neurons"] == 1
    assert metrics["spikes"] == 2
    assert metrics["active_neurons"] == 1
    assert metrics["bins"] == [2]
    assert metrics["first_spike_ms"] == 1.0
    assert metrics["last_spike_ms"] == 2.0


def test_current_exposure_units_and_arithmetic(setup, config) -> None:
    frames = cc.neutral_frames(1, 30.0)
    scheduler = cc.build_scheduler(config.condition("C1"), setup, frames)
    n_steps = 40
    dt_ms = float(config.reference["dt_ms"])
    audit = cc.audit_currents(
        scheduler,
        n_nodes=setup.mapping.graph.n_nodes,
        n_steps=n_steps,
        dt_ms=dt_ms,
        feature_indices=cc.feature_index_map(setup),
        active_indices=cc.indices_for_features(setup, config.player_features),
    )
    expected = config.reference["expected_neutral_current_pa"]
    per_step = expected["player_lane"] + expected["player_speed"]
    assert audit["units"]["step_current_pa"].startswith("instantaneous")
    assert "multiply by dt_ms" in audit["units"]["injected_pa_steps"]
    assert audit["min_step_current_pa"] == pytest.approx(
        audit["max_step_current_pa"], abs=1e-6
    )
    assert audit["max_step_current_pa"] == pytest.approx(per_step, abs=1e-6)
    assert audit["total_injected_pa_steps"] == pytest.approx(
        n_steps * per_step, abs=1e-4
    )
    assert audit["hold_only_pa_steps"] == pytest.approx(
        audit["total_injected_pa_steps"], abs=1e-6
    )
    assert audit["pulse_pa_steps"] == 0.0
    pA_ms = audit["total_injected_pa_steps"] * dt_ms
    assert pA_ms == pytest.approx(n_steps * per_step * dt_ms, rel=1e-6)


def test_feature_peaks_are_instantaneous_not_cumulative(setup, config) -> None:
    frames = cc.neutral_frames(1, 30.0)
    scheduler = cc.build_scheduler(config.condition("C1"), setup, frames)
    n_steps = 40
    dt_ms = float(config.reference["dt_ms"])
    audit = cc.audit_currents(
        scheduler,
        n_nodes=setup.mapping.graph.n_nodes,
        n_steps=n_steps,
        dt_ms=dt_ms,
        feature_indices=cc.feature_index_map(setup),
        active_indices=cc.indices_for_features(setup, config.player_features),
    )
    expected = config.reference["expected_neutral_current_pa"]
    peaks = audit["peak_feature_current_pa"]
    assert peaks["player_lane"] == pytest.approx(expected["player_lane"], abs=1e-6)
    assert peaks["player_speed"] == pytest.approx(expected["player_speed"], abs=1e-6)
    assert peaks["jumping"] == 0.0
    assert peaks["rolling"] == 0.0
    means = audit["mean_feature_current_pa"]
    for name in ("player_lane", "player_speed"):
        assert means[name] == pytest.approx(peaks[name], abs=1e-6)
    total = sum(peaks.values())
    assert total == pytest.approx(audit["max_step_current_pa"], abs=1e-6)


def test_require_cache_matches_archive_gates_full_mode(config, cache) -> None:
    cc.require_cache_matches_archive(config, cache)
    with pytest.raises(ValueError):
        cc.require_cache_matches_archive(config, None)
    tampered = dataclasses.replace(cache, frames_digest="0" * 64)
    with pytest.raises(ValueError):
        cc.require_cache_matches_archive(config, tampered)
    unsigned = dataclasses.replace(cache, scheduler_signature_sha256=None)
    with pytest.raises(ValueError):
        cc.require_cache_matches_archive(config, unsigned)


def test_c0_only_full_mode_requires_no_cache(config) -> None:
    payload = cc.run_experiment(condition_names=["C0"], config=config, repeats=1)
    assert payload["conditions"]["C0"]["simulation"]["spikes_total"] == 0
    assert payload["invalidations"]["triggered"] == []
