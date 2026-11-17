"""Focused tests for the read-only U1 viability report (G7, REV3 §12 U1).

The cases are synthetic rows only. No game, simulator or floor replay is run;
the floor is represented by stored constant-``NO_ACTION`` rows exactly as U10
says it would be. The report must never upgrade an arm from an assumption and
must never mark blocked work as complete.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.viability import (
    U1_CASES,
    ViabilityError,
    arm_gate,
    case_table,
    evaluate_store,
    evaluate_viability,
    phase7_summary,
    phase7_summary_from_path,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEEDS = (1, 2, 3)
EPISODES = 2


def rows_for(
    make_row,
    *,
    a_steps,
    f_steps,
    e_steps=None,
    floor_steps=2,
    a_actions=True,
    f_actions=True,
    e_actions=True,
):
    rows = []
    for seed in SEEDS:
        for episode in range(EPISODES):
            rows.append(
                make_row(
                    "A",
                    seed,
                    episode,
                    steps=a_steps + seed,
                    non_no_action=2 if a_actions else 0,
                )
            )
            rows.append(
                make_row(
                    "F",
                    seed,
                    episode,
                    steps=f_steps + seed,
                    non_no_action=2 if f_actions else 0,
                )
            )
            if e_steps is not None:
                rows.append(
                    make_row(
                        "E",
                        seed,
                        episode,
                        steps=e_steps + seed,
                        non_no_action=2 if e_actions else 0,
                    )
                )
            if floor_steps is not None:
                rows.append(make_row("floor", seed, episode, steps=floor_steps))
    return rows


def test_case_table_declares_five_rows_and_u1b_options():
    table = {row["id"]: row for row in case_table()}
    assert list(table) == ["U1-A", "U1-B", "U1-C", "U1-D", "U1-E"]
    assert set(U1_CASES[0]) == {
        "id",
        "a",
        "f",
        "e_matched",
        "label",
        "action",
    }
    assert len(table["U1-B"]["options"]) == 4
    assert "option 2" in table["U1-B"]["recommendation"]


def test_arm_gate_zero_actions_is_floored_without_a_floor(phase_8_row):
    rows = [
        phase_8_row("A", seed, episode, steps=10)
        for seed in SEEDS
        for episode in range(EPISODES)
    ]
    gate = arm_gate(rows, "A", seeds=SEEDS, episodes_per_seed=EPISODES)
    assert gate["status"] == "floored"
    assert gate["floored"] is True
    assert gate["above_floor"] is False
    assert gate["floor_measured"] is False
    assert gate["non_no_action_decisions"] == 0


def test_arm_gate_needs_a_measured_floor_to_be_above_it(phase_8_row):
    rows = rows_for(phase_8_row, a_steps=10, f_steps=20, floor_steps=None)
    gate = arm_gate(rows, "A", seeds=SEEDS, episodes_per_seed=EPISODES)
    assert gate["status"] == "indeterminate"
    assert gate["above_floor"] is False
    assert gate["floored"] is False


def test_arm_gate_above_floor_when_the_measured_floor_is_lower(phase_8_row):
    rows = rows_for(phase_8_row, a_steps=10, f_steps=20)
    gate = arm_gate(rows, "A", seeds=SEEDS, episodes_per_seed=EPISODES)
    assert gate["status"] == "above floor"
    assert gate["above_floor"] is True
    assert gate["seeds_paired_with_floor"] == len(SEEDS)
    # A scores 11, 12, 13 against a constant floor of 2: mean difference 10.0.
    assert gate["mean_difference_from_floor"] == pytest.approx(10.0)


def test_u1a_when_a_and_f_are_above_the_floor(phase_8_row):
    rows = rows_for(phase_8_row, a_steps=10, f_steps=20)
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-A"
    assert report["action"] == "proceed; the gate is passed"
    assert report["complete"] is True
    assert report["blocked"] is False
    assert report["provisional"] is False
    assert report["protocol_status"].startswith("PROPOSED")


def test_u1b_is_provisional_when_e_matched_is_absent(phase_8_row):
    rows = rows_for(
        phase_8_row,
        a_steps=0,
        f_steps=0,
        e_steps=None,
        a_actions=False,
        f_actions=False,
    )
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-B"
    assert report["provisional"] is True
    assert report["complete"] is False
    assert report["blocked"] is True
    assert any("E-matched" in reason for reason in report["blocked_by"])


def test_u1b_is_complete_when_e_matched_is_floored(phase_8_row):
    rows = rows_for(
        phase_8_row,
        a_steps=0,
        f_steps=0,
        e_steps=0,
        a_actions=False,
        f_actions=False,
        e_actions=False,
    )
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-B"
    assert report["complete"] is True
    assert report["provisional"] is False
    assert "stop" in report["action"]


def test_u1e_when_e_matched_is_above_the_floor(phase_8_row):
    rows = rows_for(
        phase_8_row,
        a_steps=0,
        f_steps=0,
        e_steps=20,
        a_actions=False,
        f_actions=False,
        e_actions=True,
    )
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-E"
    assert report["complete"] is True
    assert "interface limitation" in report["action"]


def test_u1c_readout_rescues_the_platform(phase_8_row):
    rows = rows_for(
        phase_8_row,
        a_steps=0,
        f_steps=20,
        a_actions=False,
        f_actions=True,
    )
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-C"
    assert report["complete"] is True
    assert "readout-specific" in report["action"]


def test_u1d_readout_harms(phase_8_row):
    rows = rows_for(
        phase_8_row,
        a_steps=20,
        f_steps=0,
        a_actions=True,
        f_actions=False,
    )
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] == "U1-D"
    assert report["complete"] is True
    assert "do not treat Fβ as the floor" in report["action"]


def test_missing_floor_blocks_classification(phase_8_row):
    rows = rows_for(phase_8_row, a_steps=10, f_steps=20, floor_steps=None)
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] is None
    assert report["complete"] is False
    assert report["blocked"] is True
    assert any("floor" in reason for reason in report["blocked_by"])
    assert report["evidence"] == {
        "A": "indeterminate",
        "F": "indeterminate",
        "E_matched": "not run",
    }


def test_missing_f_blocks_the_gate(phase_8_row):
    rows = [
        row
        for row in rows_for(phase_8_row, a_steps=10, f_steps=20)
        if row["condition"] != "F"
    ]
    report = evaluate_viability(rows, seeds=SEEDS, episodes_per_seed=EPISODES)
    assert report["case"] is None
    assert report["complete"] is False
    assert any("F is not run" in reason for reason in report["blocked_by"])


def test_evaluate_store_reads_jsonl_and_writes_nothing(tmp_path, phase_8_row):
    rows = rows_for(phase_8_row, a_steps=10, f_steps=20)
    store = tmp_path / "episodes.jsonl"
    store.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    before = store.read_text(encoding="utf-8")
    files_before = sorted(path.name for path in tmp_path.iterdir())

    report = evaluate_store(store, seeds=SEEDS, episodes_per_seed=EPISODES)

    assert report["case"] == "U1-A"
    assert report["store"] == str(store)
    assert store.read_text(encoding="utf-8") == before
    assert sorted(path.name for path in tmp_path.iterdir()) == files_before


def test_phase7_summary_reads_the_frozen_baseline():
    report = phase7_summary_from_path(
        PROJECT_ROOT / "experiments" / "results" / "phase_7" / "neural_closed_loop.json"
    )
    assert report["is_campaign_arm"] is False
    assert report["updates"] == 213
    assert report["action_counts"] == {"NO_ACTION": 213}
    assert report["non_no_action_decisions"] == 0
    assert report["motor_spikes"] == 0
    assert report["total_spikes"] == 2852
    assert report["non_stimulated_spikes"] == 0
    assert report["floored_by_actions"] is True
    assert report["weights_before_sha256"].startswith("4923f0cd")
    assert report["weights_before_sha256"] == report["weights_after_sha256"]


def test_phase7_summary_rejects_an_artifact_without_run_summary():
    with pytest.raises(ViabilityError):
        phase7_summary({"run": {}})
    with pytest.raises(ViabilityError):
        phase7_summary({})
