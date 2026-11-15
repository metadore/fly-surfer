"""Focused tests for the P3-T3 leave-one-feature-out ablation runner.

These tests validate plumbing only: condition construction, removal
semantics of the scheduler mask, reference/active-set reporting, the
baseline archive gate, capacity invalidation and reproducibility. The
preregistered 3300.5 ms ablation campaign is not executed here; the
longest simulation in this file is a 100 ms smoke window.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from experiments.phase_3c import causal_control as cc
from experiments.phase_3c import feature_ablation as fa

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "feature_ablation_config.yaml"


@pytest.fixture(scope="module")
def cfg() -> fa.AblationConfig:
    return fa.AblationConfig.load(CONFIG_PATH)


@pytest.fixture(scope="module")
def causal(cfg) -> cc.CausalControlConfig:
    return cfg.causal


@pytest.fixture(scope="module")
def loaded(causal):
    return cc._load_setup(causal)


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
def cache(causal) -> cc.CausalFrameCache:
    if not (cc.PROJECT_ROOT / causal.cache["path"]).is_file():
        pytest.skip("run `--build-cache` before the cache-dependent tests")
    return cc.load_cache(causal)


# --------------------------------------------------------------------------
# condition construction
# --------------------------------------------------------------------------


def test_ablations_remove_exactly_one_feature(cfg) -> None:
    features = tuple(cfg.all_features)
    assert len(features) == 14
    assert len(cfg.removed_features) == 14
    for feature in features:
        spec = cfg.spec_for(fa.ablation_name(feature))
        assert spec.frame_source == "cached"
        assert set(features) - set(spec.active_features) == {feature}
        assert len(spec.active_features) == 13
        assert feature not in spec.active_features
    baseline = cfg.spec_for(fa.BASELINE_NAME)
    assert baseline.active_features is None
    assert cfg.condition_names() == [fa.BASELINE_NAME] + [
        fa.ablation_name(feature) for feature in features
    ]


def test_thirteen_features_remain_active_in_canonical_order(cfg) -> None:
    features = tuple(cfg.all_features)
    for feature in features:
        spec = cfg.spec_for(fa.ablation_name(feature))
        assert spec.active_features == tuple(
            f for f in features if f != feature
        )


def test_config_load_rejects_incomplete_removal_list(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "  - player_lane\n", ""
    )
    bad = tmp_path / "bad_ablation.yaml"
    bad.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        fa.AblationConfig.load(bad)


# --------------------------------------------------------------------------
# removal semantics on synthetic frames
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def synthetic_frame(cache):
    """A cached-frame replica anchored at t=0 with a pulse on player_speed."""
    source = next(
        frame
        for frame in cache.frames
        if frame.features["obstacle_present"]
        and frame.features["train_present"]
        and frame.features["player_speed"] > 0.0
    )
    payload = {
        "frame_index": source.frame_index,
        "frame_id": source.frame_id,
        "timestamp_ms": 0.0,
        "time_ms": 0.0,
        "dt_ms": source.dt_ms,
        "is_gap": False,
        "features": dict(source.features),
        "game_state": {
            "features": dict(source.features),
            "time_ms": 0.0,
        },
        "unrepresented_tracks": 0,
        "notes": [],
        "events": [
            {
                "track_id": 1,
                "frame_index": source.frame_index,
                "timestamp_ms": 0.0,
                "time_ms": 0.0,
                "event": "appeared",
                "class_id": 0,
                "class_name": "train",
                "role": "train",
                "lane": source.features["train_lane"],
                "confidence": 0.9,
                "distance_proxy": source.features["train_distance"],
                "feature_values": {"player_speed": source.features["player_speed"]},
                "is_pulse": True,
                "detail": "test pulse",
            }
        ],
    }
    return cc._frame_from_dict(payload)


def _peaks_by_feature(setup, causal, frame, active_features):
    spec = cc.ConditionSpec(
        name="probe",
        description="probe",
        frame_source="cached",
        active_features=active_features,
    )
    scheduler = cc.build_scheduler(spec, setup, (frame,))
    audit = cc.audit_currents(
        scheduler,
        n_nodes=setup.mapping.graph.n_nodes,
        n_steps=20,
        dt_ms=0.5,
        feature_indices=cc.feature_index_map(setup),
        active_indices=cc.indices_for_features(setup, active_features),
        pulse_windows=((0.0, 7.5),),
    )
    probe = fa.pulse_window_peak_by_feature(
        scheduler, setup, n_steps=20, dt_ms=0.5
    )
    return audit, probe


def test_removed_feature_gets_no_hold_or_pulse_current(
    setup, causal, synthetic_frame
) -> None:
    features = tuple(causal.all_features)
    removed = "player_speed"
    active = tuple(f for f in features if f != removed)
    full_audit, _ = _peaks_by_feature(setup, causal, synthetic_frame, features)
    ablated_audit, ablated_probe = _peaks_by_feature(
        setup, causal, synthetic_frame, active
    )
    assert full_audit["peak_feature_current_pa"][removed] > 0.0
    assert ablated_audit["peak_feature_current_pa"][removed] == 0.0
    assert ablated_audit["hold_only_peak_feature_current_pa"][removed] == 0.0
    assert ablated_probe[removed] == 0.0
    for feature in active:
        assert ablated_audit["peak_feature_current_pa"][feature] == pytest.approx(
            full_audit["peak_feature_current_pa"][feature], abs=1e-6
        )
    held = [
        feature
        for feature in active
        if full_audit["peak_feature_current_pa"][feature] > 0.0
    ]
    assert held, "the synthetic frame must drive at least one kept feature"


def test_pulse_windows_survive_feature_removal(setup, causal, synthetic_frame) -> None:
    removed = "player_speed"
    active = tuple(f for f in causal.all_features if f != removed)
    spec = cc.ConditionSpec(
        name="probe",
        description="probe",
        frame_source="cached",
        active_features=active,
    )
    scheduler = cc.build_scheduler(spec, setup, (synthetic_frame,))
    assert len(cc.pulse_windows(scheduler)) == 1
    stats = scheduler.input_statistics()
    assert stats["n_pulse_events"] == 1
    assert scheduler.stimulated_indices.size == cc.indices_for_features(
        setup, active
    ).size


# --------------------------------------------------------------------------
# cached frames, reference population and active sets
# --------------------------------------------------------------------------


def test_all_ablations_share_the_cached_frames(causal, cfg, cache) -> None:
    for name in cfg.condition_names():
        frames = cc.resolve_frames(
            cfg.spec_for(name), causal, cache, smoke_ms=None
        )
        assert frames == cache.frames


def test_reference_population_is_fixed_and_active_set_condition_local(
    setup, causal, cfg
) -> None:
    reference = cc.indices_for_features(setup, tuple(causal.all_features))
    assert reference.size == 138
    for feature in causal.all_features:
        spec = cfg.spec_for(fa.ablation_name(feature))
        active = cc.indices_for_features(setup, spec.active_features)
        expected = 138 - int(causal.feature_neurons[feature])
        assert active.size == expected
        assert set(reference) - set(active) == set(
            cc.indices_for_features(setup, (feature,))
        )
    baseline = cfg.spec_for(fa.BASELINE_NAME)
    baseline_active = cc.indices_for_features(
        setup, cc.active_feature_names(baseline, setup)
    )
    assert baseline_active.size == reference.size


# --------------------------------------------------------------------------
# baseline archive gate
# --------------------------------------------------------------------------


def test_baseline_scheduler_signature_matches_archived_reference(
    setup, causal, cache
) -> None:
    spec = cc.ConditionSpec(
        name=fa.BASELINE_NAME,
        description="baseline",
        frame_source="cached",
        active_features=None,
    )
    frames = cc.resolve_frames(spec, causal, cache, smoke_ms=None)
    scheduler = cc.build_scheduler(spec, setup, frames)
    digest = cc.scheduler_signature_digest(scheduler)
    assert digest == causal.archived["scheduler_sha256"]
    assert cache.frames_digest == causal.archived["temporal_sha256"]


def test_smoke_window_never_invokes_the_archive_gate(cfg, causal, cache) -> None:
    payload = fa.run_ablation_experiment(
        condition_names=[fa.BASELINE_NAME, fa.ablation_name("player_lane")],
        cfg=cfg,
        smoke_ms=100.0,
        repeats=1,
    )
    assert payload["verdict"] == "SMOKE ONLY (infrastructure validation)"
    assert payload["invalidations"]["triggered"] == []
    baseline = payload["conditions"][fa.BASELINE_NAME]
    ablated = payload["conditions"]["no-player_lane"]
    assert baseline["ignition"] is not None
    assert ablated["removed_feature"] == "player_lane"
    assert ablated["n_active_neurons"] == 138 - int(
        causal.feature_neurons["player_lane"]
    )
    assert baseline["cache_frames_digest"] == ablated["cache_frames_digest"]
    assert payload["contrasts_vs_baseline"]["available"] is True


# --------------------------------------------------------------------------
# capacity invalidation and reproducibility
# --------------------------------------------------------------------------


def test_recorder_overflow_invalidates_an_ablation_run(
    setup, causal, neuron_params, synapse_params, cache, cfg
) -> None:
    spec = cfg.spec_for("no-player_lane")
    tiny = dataclasses.replace(
        causal,
        reference={**causal.reference, "max_recorded_spikes": 2},
    )
    item = cc.run_once(
        spec,
        tiny,
        setup,
        neuron_params,
        synapse_params,
        cache,
        duration_ms=100.0,
        smoke_ms=100.0,
    )
    assert item["spike_capacity_exceeded"] is True
    item["reproducibility"] = {"identical": True, "differences": []}
    report = fa.evaluate_ablation_invalidations(
        {"no-player_lane": item}, {"no-player_lane": {}}, cfg, {}, mode="smoke"
    )
    rules = [entry["rule"] for entry in report["triggered"]]
    assert "spike_capacity_exceeded" in rules


def test_repeated_ablation_runs_are_reproducible(
    setup, causal, neuron_params, synapse_params, cache, cfg
) -> None:
    spec = cfg.spec_for("no-train_present")
    item = cc.run_condition(
        spec,
        causal,
        setup,
        neuron_params,
        synapse_params,
        cache,
        duration_ms=100.0,
        smoke_ms=100.0,
        repeats=2,
    )
    assert item["reproducibility"]["identical"] is True
    assert item["reproducibility"]["differences"] == []
