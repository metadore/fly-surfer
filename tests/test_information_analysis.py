"""Focused tests for the Phase 6B/6C analysis layer.

These tests read the archived artifacts but compute no research result: they
check that the readers return the structures the reports rely on, that the
report JSON and Markdown agree, and that the endpoint helpers are pure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from information.artifact_readers import (  # noqa: E402
    load_decoder_windows,
    load_events,
    load_frame_event_counts,
    load_phase5e,
    load_phase5f,
)

PHASE_6B_JSON = ROOT / "reports" / "PHASE_6B_SHANNON_ENTROPY.json"
PHASE_6B_MD = ROOT / "reports" / "PHASE_6B_SHANNON_ENTROPY.md"
PHASE_6C_JSON = ROOT / "reports" / "PHASE_6C_MUTUAL_INFORMATION.json"
PHASE_6C_MD = ROOT / "reports" / "PHASE_6C_MUTUAL_INFORMATION.md"
PHASE_6B_RESULTS = ROOT / "experiments" / "results" / "phase_6b" / "entropy_results.json"
PHASE_6C_RESULTS = ROOT / "experiments" / "results" / "phase_6c" / "mutual_information_results.json"


def test_event_reader_returns_all_archived_events():
    data = load_events()
    assert data["class_codes"].size == 515
    assert data["frame_clusters"].size == 515
    assert len(data["segment_names"]) == 3
    counts = np.bincount(data["class_codes"], minlength=6)
    assert counts.sum() == 515
    assert sum(data["per_segment"][name]["n"] for name in data["segment_names"]) == 515


def test_event_reader_hashes_are_recorded():
    data = load_events()
    assert set(data["source_hashes"]) == set(data["segment_names"])
    assert all(len(value) == 64 for value in data["source_hashes"].values())


def test_frame_event_counts_cover_every_frame():
    data = load_frame_event_counts()
    assert data["counts"].size == 300
    assert np.all(data["counts"] >= 0)
    assert np.all(data["counts"] <= 3)
    assert len(set(data["block_clusters"].tolist())) == 30


def test_decoder_reader_counts():
    data = load_decoder_windows()
    assert data["state_codes"].size == 330
    assert data["n_runs"] == 66
    assert np.bincount(data["state_codes"], minlength=4).tolist() == [210, 60, 45, 15]
    assert data["left_active"].sum() == 90
    assert data["jump_active"].sum() == 75


def test_decoder_reader_marks_missing_actions_as_missing():
    data = load_phase5e()
    assert data["conditions"]["G"]["action"].min() == -1
    assert data["conditions"]["A"]["action"].min() == 0


def test_phase5e_reader_shapes():
    data = load_phase5e()
    assert set(data["conditions"]) == set("ABCDEFG")
    for block in data["conditions"].values():
        assert block["cue"].size == 480
        assert block["n_spikes"].size == 480
        assert block["n_cue_spikes"].size == 480
    assert data["n_replicates"] == 3


def test_phase5e_cue_spike_counts_are_constant():
    data = load_phase5e()
    for condition in "ABCDEF":
        assert len(np.unique(data["conditions"][condition]["n_cue_spikes"])) == 1


def test_phase5f_reader_shapes():
    data = load_phase5f()
    assert data["n_seeds"] == 10
    for block in data["conditions"].values():
        for checkpoint in data["checkpoints"]:
            payload = block["per_checkpoint"][checkpoint]
            assert payload["cue"].size == 400
            assert len(np.unique(payload["seed_clusters"])) == 10


def test_contingency_sums_to_sample():
    from experiments.phase_6c.run_mutual_information import contingency

    x = np.array([0, 0, 1, 1, 1])
    y = np.array([0, 1, 0, 1, 1])
    table = contingency(x, y, 2, 2)
    assert np.asarray(table).sum() == 5
    assert table == [[1, 1], [1, 2]]


def test_per_seed_mi_returns_one_value_per_seed():
    from experiments.phase_6c.run_mutual_information import per_seed_mi

    data = load_phase5f()
    payload = data["conditions"]["fixed_complete"]["per_checkpoint"]["160"]
    values = per_seed_mi(payload)
    assert len(values) == 10
    assert all(value >= 0.0 for value in values.values())


@pytest.mark.parametrize(
    "results_path,report_json,report_md",
    [
        (PHASE_6B_RESULTS, PHASE_6B_JSON, PHASE_6B_MD),
        (PHASE_6C_RESULTS, PHASE_6C_JSON, PHASE_6C_MD),
    ],
)
def test_reports_exist_and_parse(results_path, report_json, report_md):
    assert results_path.is_file()
    assert report_json.is_file()
    assert report_md.is_file()
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["phase"] == report["phase"]
    assert payload["config_sha256"] == report["config"]["sha256"]


def test_phase_6b_markdown_matches_json():
    report = json.loads(PHASE_6B_JSON.read_text(encoding="utf-8"))
    markdown = PHASE_6B_MD.read_text(encoding="utf-8")
    for row in report["marginal_entropy"]:
        assert f"{row['H_plugin'] + 0.0:.4f}" in markdown
    for row in report["reward_entropy"]:
        assert f"{row['H_plugin'] + 0.0:.4f}" in markdown


def test_phase_6c_markdown_matches_json():
    report = json.loads(PHASE_6C_JSON.read_text(encoding="utf-8"))
    markdown = PHASE_6C_MD.read_text(encoding="utf-8")
    for row in report["endpoint_rows"]:
        assert f"{row['raw_mi_bits'] + 0.0:.4f}" in markdown
        assert f"{row['bias_floor_bits'] + 0.0:.4f}" in markdown


def test_phase_6c_unavailable_endpoints_are_recorded():
    report = json.loads(PHASE_6C_JSON.read_text(encoding="utf-8"))
    assert report["unavailable"]["C04"]["status"] == "unavailable"
    assert report["unavailable"]["C05"]["status"] == "unavailable"


def test_phase_6b_unavailable_endpoints_are_recorded():
    report = json.loads(PHASE_6B_JSON.read_text(encoding="utf-8"))
    identifiers = {item["id"] for item in report["unavailable"]}
    assert {"U01", "U02", "U03", "U04"} <= identifiers
