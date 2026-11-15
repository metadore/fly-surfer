"""Focused tests for the P3-T3.1 provisional ignition classification."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.phase_3c import ignition_reporting as ir

PAYLOAD = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "phase_3c"
    / "results"
    / "p3_t3_ablation.json"
)


def _condition(
    *,
    condition: str = "synthetic",
    removed_feature=None,
    outside_spikes: int,
    outside_active: int,
    outside_rate: float,
    reference_rate: float = 8.145,
    reference_active: int = 72,
    reference_spikes: int = 3710,
    n_reference: int = 138,
    first_outside: float | None = None,
    last_outside: float | None = None,
    ignited: bool | None = None,
    bins: list[int] | None = None,
    n_neurons: int = 139255,
) -> dict:
    if bins is None:
        bins = [outside_spikes] if outside_spikes else [0, 0]
    return {
        "condition": condition,
        "removed_feature": removed_feature,
        "n_reference_neurons": n_reference,
        "partitions": {
            "total": {
                "n_neurons": n_neurons,
                "spikes": outside_spikes + reference_spikes,
                "active_neurons": outside_active + reference_active,
                "firing_rate_hz": 34.0,
                "bins": [0, outside_spikes],
                "first_spike_ms": 28.0,
                "last_spike_ms": 3300.5,
            },
            "reference": {
                "n_neurons": n_reference,
                "spikes": reference_spikes,
                "active_neurons": reference_active,
                "firing_rate_hz": reference_rate,
                "bins": [0, reference_spikes],
                "first_spike_ms": 28.0,
                "last_spike_ms": 3300.5,
            },
            "outside_reference": {
                "n_neurons": n_neurons - n_reference,
                "spikes": outside_spikes,
                "active_neurons": outside_active,
                "firing_rate_hz": outside_rate,
                "bin_ms": 100.0,
                "bins": bins,
                "first_spike_ms": first_outside,
                "last_spike_ms": last_outside,
            },
        },
        "simulation": {
            "activity": {
                "n_neurons": n_neurons,
                "population_rate_peak_hz": 37.0,
            }
        },
        "ignition": {
            "ignited": (outside_spikes > 0) if ignited is None else ignited,
            "first_spike_outside_reference_ms": first_outside,
        },
    }


def test_zero_outside_reference_spikes_is_none() -> None:
    item = ir.classify_condition(
        _condition(outside_spikes=0, outside_active=0, outside_rate=0.0)
    )
    assert item["activity_detected_outside_reference"] is False
    assert item["activity_regime"] == ir.REGIME_NONE
    assert item["activity_regime_status"] == "definitional"
    assert item["legacy_activity_detection"]["value"] is False


def test_four_spikes_on_two_neurons_is_sparse() -> None:
    item = ir.classify_condition(
        _condition(
            condition="no-train_lane",
            outside_spikes=4,
            outside_active=2,
            outside_rate=0.0,
            reference_rate=6.143,
            first_outside=1467.0,
            last_outside=1467.0,
        )
    )
    assert item["activity_detected_outside_reference"] is True
    assert item["activity_regime"] == ir.REGIME_SPARSE
    assert item["activity_regime_status"] == "provisional"
    assert (
        item["population_scale_basis"][
            "outside_active_exceeds_reference_population"
        ]
        is False
    )
    # The legacy field still reports activity detection, unchanged.
    assert item["legacy_activity_detection"]["value"] is True
    assert item["legacy_activity_detection"]["consistent_with_measurement"]


def test_p3_t3_baseline_is_population_scale() -> None:
    item = ir.classify_condition(
        _condition(
            condition="full-input",
            outside_spikes=15_650_921,
            outside_active=35_907,
            outside_rate=34.086,
            reference_rate=8.145,
            first_outside=101.5,
            last_outside=3300.0,
            bins=[0, 99, 248_612, 512_983],
        )
    )
    assert item["activity_regime"] == ir.REGIME_POPULATION
    assert item["activity_regime_status"] == "provisional"
    assert item["population_scale_basis"] == {
        "outside_active_exceeds_reference_population": True,
        "outside_rate_at_least_reference_rate": True,
    }
    assert item["measurements"]["outside_reference_bins_occupied"] == 3


def test_intermediate_activity_below_population_criterion_is_sparse() -> None:
    # More outside-R neurons than R, but far below the reference rate.
    item = ir.classify_condition(
        _condition(
            outside_spikes=100_000,
            outside_active=500,
            outside_rate=3.0,
            reference_rate=8.145,
            first_outside=200.0,
            last_outside=2500.0,
        )
    )
    assert item["activity_regime"] == ir.REGIME_SPARSE
    assert (
        item["population_scale_basis"][
            "outside_active_exceeds_reference_population"
        ]
        is True
    )
    assert (
        item["population_scale_basis"]["outside_rate_at_least_reference_rate"]
        is False
    )


def test_high_rate_without_recruitment_is_sparse() -> None:
    # Above the reference rate, but fewer outside-R neurons than R.
    item = ir.classify_condition(
        _condition(
            outside_spikes=50_000,
            outside_active=100,
            outside_rate=40.0,
            reference_rate=8.145,
            first_outside=150.0,
            last_outside=3000.0,
        )
    )
    assert item["activity_regime"] == ir.REGIME_SPARSE
    assert (
        item["population_scale_basis"][
            "outside_active_exceeds_reference_population"
        ]
        is False
    )


def test_classification_does_not_mutate_the_input() -> None:
    condition = _condition(
        condition="no-train_lane",
        outside_spikes=4,
        outside_active=2,
        outside_rate=0.0,
        first_outside=1467.0,
        last_outside=1467.0,
    )
    before = copy.deepcopy(condition)
    ir.classify_condition(condition)
    assert condition == before


@pytest.mark.skipif(not PAYLOAD.exists(), reason="archived P3-T3 payload absent")
def test_archived_p3_t3_classification() -> None:
    report = ir.build_classification_report(PAYLOAD)
    assert report["counts"] == {ir.REGIME_NONE: 1, ir.REGIME_SPARSE: 1, ir.REGIME_POPULATION: 13}
    assert report["conditions"]["no-player_lane"]["activity_regime"] == ir.REGIME_NONE
    assert report["conditions"]["no-train_lane"]["activity_regime"] == ir.REGIME_SPARSE
    assert (
        report["conditions"]["no-train_lane"]["legacy_activity_detection"]["value"]
        is True
    )
    assert (
        report["conditions"]["full-input"]["activity_regime"]
        == ir.REGIME_POPULATION
    )
    for name, item in report["conditions"].items():
        if name in ("no-player_lane", "no-train_lane"):
            continue
        assert item["activity_regime"] == ir.REGIME_POPULATION, name
    assert report["source"]["unmodified"] is True
    assert report["source"]["sha256"] == hashlib.sha256(PAYLOAD.read_bytes()).hexdigest()
    assert report["source"]["verdict"] == "VALID"


def test_write_report_refuses_overwrite(tmp_path) -> None:
    report = ir.build_classification_report(PAYLOAD)
    output = tmp_path / "classification.json"
    ir.write_report(report, output)
    with pytest.raises(FileExistsError):
        ir.write_report(report, output)
    ir.write_report(report, output, overwrite=True)
    reloaded = json.loads(output.read_text(encoding="utf-8"))
    assert reloaded["counts"] == report["counts"]
