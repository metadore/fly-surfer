"""Phase 4H.4: matrix reconciliation, aggregation and propagation diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from experiments.phase_4h import analyse_sensory_roundtrip as analysis
from experiments.phase_4h import common


def fake_run(
    stream: str,
    condition: str,
    *,
    total: int,
    stimulated: int,
    non_stimulated: int,
    motor: int,
    seed: int | None = None,
    duration: float = 3300.5,
    spike_hash: str = "a",
    decision_hash: str = "b",
    drive_hash: str | None = "c",
    states: dict | None = None,
    locked: int = 0,
    alignment_r: float | None = None,
) -> dict:
    return {
        "stream": stream,
        "condition": condition,
        "events_used": 215,
        "pulses_used": 43,
        "events_metadata_sha256": "metadata",
        "mapping_used": "annotation",
        "n_stimulated_neurons": 232,
        "seed": analysis.expected_seed(stream, condition)
        if seed is None
        else seed,
        "duration_ms": duration,
        "background_pa": 0.0,
        "noise_std_pa": 0.0,
        "metrics": {
            "n_spikes": total,
            "stimulated_spikes": stimulated,
            "non_stimulated_spikes": non_stimulated,
            "active_neurons": stimulated + non_stimulated,
            "stimulated_active_neurons": stimulated,
            "non_stimulated_active_neurons": non_stimulated,
            "motor": {"spikes": motor, "active_neurons": motor},
            "decoded_state_counts": states or {"NEUTRAL": 67},
            "n_windows": 67,
            "jump_windows": 0,
            "left_windows": 0,
            "right_windows": 0,
            "spike_time_min_ms": 10.0,
            "spike_time_max_ms": 3000.0,
        },
        "event_locked": {
            "n_events": 215,
            "total_spikes_in_window": locked,
            "events_with_zero_spikes": 215 - locked,
        },
        "alignment": {
            "best": None if alignment_r is None else {"pearson_r": alignment_r}
        },
        "hashes": {
            "spike_sha256": spike_hash,
            "decision_sha256": decision_hash,
            "drive_sha256": drive_hash,
        },
        "wall_time_s": 1.0,
    }


def test_expected_seed_matches_runner_rule():
    assert analysis.expected_seed("full_100_199", "B_actual") == 20661110
    assert analysis.expected_seed("seg_0_99", "A_no_events") == 20661209
    assert analysis.expected_seed("seg_200_299", "G_background_noise_repeat") == (
        common.SEED_ROOT + 400000 + 200 + 6
    )


def test_reconcile_accepts_complete_matrix():
    keys = (("full_100_199", "B_actual"),)
    runs = [
        fake_run(
            "full_100_199",
            "B_actual",
            total=10,
            stimulated=10,
            non_stimulated=0,
            motor=0,
        )
    ]
    result = analysis.reconcile(runs, expected_keys=keys)
    assert result["complete"] is True
    assert result["missing"] == []
    assert result["seed_mismatches"] == []


def test_reconcile_flags_missing_duplicate_and_bad_seed():
    keys = (
        ("full_100_199", "A_no_events"),
        ("full_100_199", "B_actual"),
    )
    first = fake_run(
        "full_100_199",
        "A_no_events",
        total=0,
        stimulated=0,
        non_stimulated=0,
        motor=0,
    )
    duplicate = dict(first)
    wrong_seed = fake_run(
        "full_100_199",
        "B_actual",
        total=1,
        stimulated=1,
        non_stimulated=0,
        motor=0,
        seed=1,
    )
    result = analysis.reconcile(
        [first, duplicate, wrong_seed], expected_keys=keys
    )
    assert result["complete"] is False
    assert result["duplicates"] == [["full_100_199", "A_no_events"]]
    assert result["seed_mismatches"][0]["stored"] == 1


def test_condition_tables_excludes_repeats_and_maps_endpoints():
    runs = [
        fake_run(
            "full_100_199",
            "B_actual",
            total=3562,
            stimulated=3562,
            non_stimulated=0,
            motor=0,
        ),
        fake_run(
            "full_100_199",
            "B_actual_repeat",
            total=3562,
            stimulated=3562,
            non_stimulated=0,
            motor=0,
        ),
    ]
    table = analysis.condition_tables(runs)
    assert list(table["full_100_199"]) == ["B_actual"]
    row = table["full_100_199"]["B_actual"]
    assert row["total_spikes"] == 3562
    assert row["motor_spikes"] == 0
    assert row["decoded_state_counts"] == {"NEUTRAL": 67}


def test_numeric_summary_reports_mean_sd_median_iqr():
    summary = analysis.numeric_summary([0.0, 10.0, 20.0])
    assert summary["n"] == 3
    assert summary["mean"] == pytest.approx(10.0)
    assert summary["sd"] == pytest.approx(10.0)
    assert summary["median"] == pytest.approx(10.0)
    assert summary["q1"] == pytest.approx(5.0)
    assert summary["q3"] == pytest.approx(15.0)


def test_compare_pair_handles_zero_variance_control():
    b = {
        stream: {"total_spikes": value}
        for stream, value in zip(
            analysis.STREAMS, (3562.0, 1990.0, 2374.0), strict=True
        )
    }
    x = {stream: {"total_spikes": 0.0} for stream in analysis.STREAMS}
    result = analysis.compare_pair(
        b, x, "total_spikes", preregistered_primary=True
    )
    assert result["zero_variance"] is True
    assert result["degenerate"] is True
    assert result["hedges_g_b_minus_x"] is None
    assert result["sign_pattern"] == "all_positive"
    assert result["per_stream"]["full_100_199"]["ratio"] is None
    assert result["difference_summary"]["mean"] == pytest.approx(2642.0)


def test_compare_pair_reports_mixed_signs_without_inference():
    b = {
        stream: {"x": value}
        for stream, value in zip(analysis.STREAMS, (10.0, 0.0, 5.0), strict=True)
    }
    x = {
        stream: {"x": value}
        for stream, value in zip(analysis.STREAMS, (8.0, 2.0, 4.0), strict=True)
    }
    result = analysis.compare_pair(
        b, x, "x", preregistered_primary=False
    )
    assert result["sign_pattern"] == "mixed"
    assert result["difference_summary"]["mean"] == pytest.approx(1.0 / 3.0)
    assert "descriptive" in result["inference"]


def test_event_locked_stimulated_counts_and_latency():
    events = [{"time_ms": 0.0}, {"time_ms": 100.0}]
    spikes = np.array([10.0, 40.0, 150.0])
    result = analysis.event_locked_stimulated(events, spikes, window_ms=50.0)
    assert result["total_spikes_in_window"] == 2
    assert result["events_with_zero_spikes"] == 1
    assert result["latency_ms"]["median"] == pytest.approx(30.0)
    assert result["mean_spikes_per_event"] == pytest.approx(1.0)


def test_group_stats_threshold_proximity():
    n = 10
    mask = np.zeros(n, dtype=bool)
    mask[:5] = True
    spike_counts = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int64)
    max_v = np.array(
        [-50.0, -50.0, -56.0, -60.0, -64.0, -65.0, -65.0, -65.0, -65.0, -65.0]
    )
    max_syn = np.array(
        [100.0, 90.0, 80.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dtype=np.float32,
    )
    result = analysis.group_stats(
        mask, spike_counts, max_v, max_syn, -50.0, -65.0
    )
    assert result["n"] == 5
    assert result["spikes"] == 2
    assert result["active_neurons"] == 2
    assert result["receiving_neurons"] == 4
    assert result["max_synaptic_current_pa"] == pytest.approx(100.0)
    assert result["max_membrane_mv"] == pytest.approx(-50.0)
    assert result["closest_deficit_mv"] == pytest.approx(6.0)
    assert result["n_within_10mv"] == 2
    assert result["n_within_5mv"] == 0


def test_signed_outgoing_uses_out_indptr():
    class Graph:
        out_indptr = np.array([0, 2, 3, 3], dtype=np.int64)
        edge_dst = np.array([1, 2, 2], dtype=np.int64)

    exc = np.array([1.0, 0.0, 2.0])
    inh = np.array([0.0, 0.0, 0.0])
    edge_index, signed = analysis.signed_outgoing(np.array([0]), Graph(), exc, inh)
    assert edge_index.tolist() == [0, 1]
    assert signed.tolist() == [True, False]
    empty_index, empty_signed = analysis.signed_outgoing(
        np.array([], dtype=np.int64), Graph(), exc, inh
    )
    assert empty_index.size == 0
    assert empty_signed.size == 0
