"""Synthetic calibration of the Phase 3C temporal layer."""

from __future__ import annotations

import pytest

from experiments.phase_3c.temporal_calibration import (
    ADVERSARIAL,
    EVENT_TYPES,
    FAMILIES,
    Lifecycle,
    calibrate,
    evaluate_sequence,
    _canonical,
)
from experiments.phase_3c.temporal_calibration import (
    _adversarial_boundary_noise,
    _adversarial_dropout,
    _adversarial_duplicates,
    _adversarial_noise,
    _adversarial_stale_hold,
    _adversarial_timestamp_regression,
)

SEED = 20261106


@pytest.fixture(scope="module")
def payload():
    return calibrate(seed=SEED, trials=2)


def test_all_ten_families_are_present() -> None:
    assert len(FAMILIES) == 10
    assert set(FAMILIES) == {
        "static",
        "approaching",
        "receding",
        "sudden_appearance",
        "disappearance",
        "two_objects",
        "temporary_occlusion",
        "noisy_detections",
        "irregular_intervals",
        "missing_frames",
    }


def test_every_adversarial_check_passes(payload) -> None:
    assert set(ADVERSARIAL) == {
        "noise_only",
        "duplicate_detections",
        "single_frame_dropout",
        "threshold_boundary_noise",
        "timestamp_regression",
        "stale_frame_hold",
    }
    for name, result in payload["adversarial"].items():
        assert result["pass"] is True, (name, result)


def test_metric_structure_and_sanity(payload) -> None:
    families = payload["families"]
    assert len(families) == 10
    for name, family in families.items():
        assert family["n_sequences"] == 2
        assert set(family["event_metrics"]) == {
            kind.value for kind in EVENT_TYPES
        }
        for kind, metrics in family["event_metrics"].items():
            assert set(metrics) == {"tp", "fp", "fn", "precision", "recall", "f1"}
            assert metrics["tp"] >= 0
            assert metrics["fp"] >= 0
            assert metrics["fn"] >= 0
        direction = family["direction_accuracy"]
        assert direction["total"] > 0
        assert 0.0 <= direction["accuracy"] <= 1.0
        tracking = family["tracking"]
        assert tracking["visible_frames"] > 0
        assert 0.0 <= tracking["continuity"] <= 1.0
        assert tracking["id_switches"] >= 0
        apply = family["scheduler"]["apply_us"]
        assert apply["n"] > 0
        assert apply["p50"] is not None and apply["p50"] >= 0.0
        assert family["scheduler"]["n_steps"] > 0

    aggregate = payload["aggregate"]
    assert aggregate["n_families"] == 10
    assert aggregate["n_sequences"] == 20
    assert aggregate["micro"]["f1"] >= 0.9
    assert aggregate["direction_accuracy"]["accuracy"] >= 0.95
    assert aggregate["tracking"]["continuity"] >= 0.85
    assert aggregate["scheduler_apply_us"]["n"] > 0


def test_reported_counts_are_internally_consistent(payload) -> None:
    for family in payload["families"].values():
        expected = family["event_counts"]["expected"]
        emitted = family["event_counts"]["emitted"]
        for kind in EVENT_TYPES:
            metrics = family["event_metrics"][kind.value]
            assert metrics["tp"] <= expected[kind.value]
            assert metrics["fp"] <= emitted[kind.value]
            assert metrics["fn"] == expected[kind.value] - metrics["tp"]
            assert (
                metrics["fp"] == emitted[kind.value] - metrics["tp"]
            )


def test_calibration_is_deterministic(payload) -> None:
    repeated = calibrate(seed=SEED, trials=2)
    assert _canonical(payload) == _canonical(repeated)


def test_same_seed_reproduces_family_metrics(payload) -> None:
    again = calibrate(seed=SEED, trials=2)["families"]
    for name, family in payload["families"].items():
        assert family["event_metrics"] == again[name]["event_metrics"]
        assert family["direction_accuracy"] == again[name]["direction_accuracy"]
        assert family["tracking"] == again[name]["tracking"]


def test_uncertainty_is_reported_separately(payload) -> None:
    for family in payload["families"].values():
        assert "uncertainty_events" in family
        assert family["uncertainty_events"] >= 0
        assert set(family["event_counts"]["emitted"]) == {
            kind.value for kind in EVENT_TYPES
        }


def test_noise_only_never_confirms_objects() -> None:
    result = _adversarial_noise(SEED)
    assert result["pass"] is True
    assert result["observed"]["forbidden_events"] == []
    counts = result["observed"]["event_counts"]
    assert counts["uncertain"] > 0
    assert counts["appeared"] == 0


def test_duplicates_and_dropout_behaviour() -> None:
    duplicates = _adversarial_duplicates(SEED)
    assert duplicates["pass"] is True
    assert duplicates["observed"]["appeared_events"] == 1
    dropout = _adversarial_dropout(SEED)
    assert dropout["pass"] is True
    assert dropout["observed"]["event_counts"]["occluded"] == 1
    assert dropout["observed"]["event_counts"]["disappeared"] == 0


def test_boundary_noise_and_timestamp_regression() -> None:
    assert _adversarial_boundary_noise(SEED)["pass"] is True
    assert _adversarial_timestamp_regression(SEED)["pass"] is True


def test_stale_frame_hold() -> None:
    result = _adversarial_stale_hold(SEED)
    assert result["pass"] is True
    assert result["observed"]["at_last_frame_ms"] > 0.0
    assert result["observed"]["at_last_plus_150ms"] == 0.0


def test_evaluate_sequence_returns_lifecycle_events() -> None:
    from experiments.phase_3c.temporal_calibration import (
        DetectionSpec,
        TRAIN,
        FrameSpec,
        _box,
        _times,
    )

    frames = [
        FrameSpec(
            time_ms=time_ms,
            detections=(DetectionSpec(0, TRAIN, 1, _box(0.5), 0.9),),
            truth_boxes={0: _box(0.5)},
        )
        for time_ms in _times(6)
    ]
    result = evaluate_sequence(frames)
    events = [event.event for event, _object in result.emitted]
    assert Lifecycle.APPEARED in events
    assert result.emitted_counts[Lifecycle.APPEARED] == 1
    assert result.matched[Lifecycle.APPEARED]
