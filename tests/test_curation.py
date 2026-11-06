"""Phase 3B.1 grouped-split and curation invariants."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "phase_3b"))

import curate_dataset as cd  # noqa: E402


def record(
    group: str,
    frame: int,
    objects: int,
    *,
    split: str = "train",
    class_ids: tuple[int, ...] = (),
) -> dict:
    path = f"{split}/images/{group}_mp4-{frame}_jpg.rf.{frame:032x}.jpg"
    return {
        "split": split,
        "path": path,
        "group": group,
        "prefix": group,
        "canonical_id": f"{group}_mp4-{frame}",
        "frame": frame,
        "objects": objects,
        "class_counts": {class_id: 1 for class_id in class_ids},
        "class_ids": list(class_ids),
        "label_errors": 0,
    }


def test_fixed_split_never_puts_a_group_on_both_sides():
    records = [
        record("alpha", 1, 2),
        record("alpha", 2, 1, split="valid"),
        record("beta", 1, 3, split="valid"),
    ]
    assignments = cd.build_fixed_assignments(
        records, ["alpha"], ["beta"], set()
    )
    assert set(assignments) == {row["path"] for row in records}
    assert {side for row, side in assignments.items() if "alpha" in row} == {"train"}
    assert {side for row, side in assignments.items() if "beta" in row} == {"valid"}

    with pytest.raises(SystemExit):
        cd.build_fixed_assignments(records, ["alpha", "beta"], ["beta"], set())


def test_logo_folds_cover_every_group_once_as_validation():
    folds = cd.propose_logo_folds(["alpha", "beta", "gamma"])
    assert [fold["valid_group"] for fold in folds] == ["alpha", "beta", "gamma"]
    for fold in folds:
        assert fold["valid_group"] not in fold["train_groups"]
        assert set(fold["train_groups"]) | {fold["valid_group"]} == {
            "alpha",
            "beta",
            "gamma",
        }


def test_empty_run_is_probable_gap_and_isolated_empty_is_plausible():
    records = [
        record("alpha", 0, 2),
        record("alpha", 1, 0),
        record("alpha", 2, 0),
        record("alpha", 3, 0),
        record("alpha", 4, 3),
        record("alpha", 10, 0),
        record("alpha", 11, 2),
    ]
    audit = cd.classify_empty_frames(records, max_bracket_gap=3)
    by_frame = {row["frame"]: row for row in audit}
    assert by_frame[1]["classification"] == "probable_gap"
    assert by_frame[2]["classification"] == "probable_gap"
    assert by_frame[3]["classification"] == "probable_gap"
    assert by_frame[1]["run_length"] == 3
    assert by_frame[1]["left_nonempty_frame"] == 0
    assert by_frame[1]["right_nonempty_frame"] == 4
    assert by_frame[10]["classification"] == "isolated_plausible"


def test_group_inventory_detects_duplicate_frame_ids_across_splits():
    records = [
        record("alpha", 5, 1, split="train"),
        record("alpha", 5, 2, split="valid"),
    ]
    inventory = cd.group_inventory(records)["alpha"]
    assert inventory["duplicate_frame_ids"] == 1
    assert inventory["extra_images_on_duplicate_ids"] == 1
    assert inventory["duplicate_id_pairs_cross_split"] == 1


def test_exclusions_are_never_assigned_and_coverage_reports_missing_classes():
    records = [
        record("alpha", 0, 1, class_ids=(0,)),
        record("alpha", 1, 0),
        record("beta", 0, 1, split="valid", class_ids=(1,)),
    ]
    excluded = {records[1]["path"]}
    assignments = cd.build_fixed_assignments(records, ["alpha"], ["beta"], excluded)
    assert records[1]["path"] not in assignments

    coverage = cd.class_coverage(records, ["a", "b", "c"])
    train = cd.coverage_for_groups(
        coverage, ["alpha"], ["a", "b", "c"], records, excluded
    )
    assert train["images"] == 1
    assert train["per_class"]["a"]["boxes"] == 1
    assert train["missing_classes"] == ["b", "c"]


def test_validation_rejects_excluded_or_leaking_assignments():
    records = [
        record("alpha", 0, 1),
        record("alpha", 1, 1),
    ]
    excluded = {records[1]["path"]}
    leaking = {records[0]["path"]: "train", records[1]["path"]: "valid"}
    with pytest.raises(SystemExit):
        cd.validate_assignments(
            records, leaking, excluded, cd.propose_logo_folds(["alpha"])
        )

    same_group_both_sides = {
        records[0]["path"]: "train",
        records[1]["path"]: "valid",
    }
    with pytest.raises(SystemExit):
        cd.validate_assignments(
            records,
            same_group_both_sides,
            set(),
            cd.propose_logo_folds(["alpha"]),
        )
