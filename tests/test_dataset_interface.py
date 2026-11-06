"""Tests for the curated dataset interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from perception.dataset import (
    BoxAnnotation,
    CuratedDataset,
    DatasetError,
    parse_yolo_label,
)

CLASS_NAMES = ["alpha", "beta"]


def _manifest(
    root: Path,
    *,
    excluded: list[dict] | None = None,
    folds: list[dict] | None = None,
) -> Path:
    payload = {
        "phase": "3B.1",
        "dataset": {
            "requested_path": "data",
            "discovered_root": "data",
            "version": 15,
            "class_names": CLASS_NAMES,
            "splits_present": ["train", "valid"],
        },
        "policy": {"exclude": "all"},
        "groups": {
            "ga": {"prefixes": ["a"]},
            "gb": {"prefixes": ["b"]},
            "gc": {"prefixes": ["c"]},
        },
        "fixed_split": {
            "train_groups": ["ga"],
            "valid_groups": ["gb"],
            "assignments": {},
        },
        "logo_folds": folds
        or [
            {"fold": 1, "valid_group": "ga", "train_groups": ["gb"]},
            {"fold": 2, "valid_group": "gb", "train_groups": ["ga"]},
        ],
        "exclusions": excluded or [],
        "limitations": ["synthetic fixture"],
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _make_dataset(root: Path) -> Path:
    for split, name, label in (
        ("train", "a_1", "0 0.5 0.5 0.4 0.4\n"),
        ("valid", "b_1", "1 0.25 0.75 0.2 0.3\n"),
        ("train", "c_1", "0 0.5 0.5 0.2 0.2\n"),
    ):
        (root / "data" / split / "images").mkdir(parents=True, exist_ok=True)
        (root / "data" / split / "labels").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (12, 8), color=(10, 20, 30)).save(
            root / "data" / split / "images" / f"{name}.png"
        )
        (root / "data" / split / "labels" / f"{name}.txt").write_text(
            label, encoding="utf-8"
        )
    return _manifest(
        root,
        excluded=[{"path": "train/images/c_1.png", "reason": "empty_label"}],
    )


def test_loads_manifest_authoritative_split(tmp_path: Path) -> None:
    manifest_path = _make_dataset(tmp_path)
    dataset = CuratedDataset.load(manifest_path, repo_root=tmp_path)

    assert len(dataset.images) == 2
    assert dataset.excluded == ("train/images/c_1.png",)
    assert [image.group for image in dataset.images] == ["ga", "gb"]
    assert [image.split for image in dataset.images] == ["train", "valid"]
    assert dataset.images[0].image_size == (12, 8)
    assert dataset.images[0].boxes[0].class_id == 0

    train = dataset.split_statistics("train")
    valid = dataset.split_statistics("valid")
    assert (train.images, train.boxes) == (1, 1)
    assert (valid.images, valid.boxes) == (1, 1)
    assert train.missing_classes == ("beta",)
    assert valid.missing_classes == ("alpha",)
    assert len(dataset.folds) == 2
    assert dataset.manifest_sha256 == dataset.describe()["manifest_sha256"]


def test_fold_views_partition_atomic_groups(tmp_path: Path) -> None:
    manifest_path = _make_dataset(tmp_path)
    dataset = CuratedDataset.load(manifest_path, repo_root=tmp_path)
    fold = dataset.for_fold(1)
    assert fold.valid_group == "ga"
    assert [image.group for image in fold.train_images] == ["gb"]
    assert [image.group for image in fold.valid_images] == ["ga"]
    stats = dataset.fold_statistics(1)
    assert stats["train"]["images"] == 1
    assert stats["valid"]["images"] == 1


def test_rejects_included_empty_label(tmp_path: Path) -> None:
    manifest_path = _make_dataset(tmp_path)
    (tmp_path / "data/train/labels/a_1.txt").write_text("", encoding="utf-8")
    with pytest.raises(DatasetError, match="empty"):
        CuratedDataset.load(manifest_path, repo_root=tmp_path)


def test_rejects_missing_label(tmp_path: Path) -> None:
    manifest_path = _make_dataset(tmp_path)
    (tmp_path / "data/valid/labels/b_1.txt").unlink()
    with pytest.raises(DatasetError, match="label not found"):
        CuratedDataset.load(manifest_path, repo_root=tmp_path)


def test_rejects_out_of_range_box(tmp_path: Path) -> None:
    manifest_path = _make_dataset(tmp_path)
    (tmp_path / "data/valid/labels/b_1.txt").write_text(
        "1 0.95 0.5 0.3 0.2\n", encoding="utf-8"
    )
    with pytest.raises(DatasetError, match="outside"):
        CuratedDataset.load(manifest_path, repo_root=tmp_path)


def test_rejects_unknown_class_and_duplicate(tmp_path: Path) -> None:
    label = tmp_path / "label.txt"
    label.write_text("2 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="class id 2"):
        parse_yolo_label(label, class_names=CLASS_NAMES)
    label.write_text("0 0.5 0.5 0.2 0.2\n0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="duplicate"):
        parse_yolo_label(label, class_names=CLASS_NAMES)


def test_box_annotation_geometry() -> None:
    box = BoxAnnotation(class_id=0, cx=0.5, cy=0.5, width=0.4, height=0.2)
    assert box.x1 == pytest.approx(0.3)
    assert box.y2 == pytest.approx(0.6)
    assert box.area == pytest.approx(0.08)
    assert box.as_yolo_line() == "0 0.5 0.5 0.4 0.2"


def test_real_manifest_matches_phase_3b2b0_counts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"
    dataset_root = (
        repo_root
        / "datasets"
        / "external"
        / "subway surfers"
        / "roboflow_v15_yolov8"
        / "subway surfers object dataset.v15-added.yolov8"
    )
    if not manifest_path.is_file() or not dataset_root.is_dir():
        pytest.skip("the curated dataset is not available in this checkout")
    dataset = CuratedDataset.load(
        manifest_path, dataset_root=dataset_root, verify_images=False
    )
    train = dataset.split_statistics("train")
    valid = dataset.split_statistics("valid")
    assert (train.images, train.boxes) == (1188, 4704)
    assert (valid.images, valid.boxes) == (1128, 3962)
    assert len(dataset.images) == 2316
    assert sum(image.n_boxes for image in dataset.images) == 8666
    assert len(dataset.folds) == 5
    assert valid.missing_classes == ("boots-powerup", "jump-electric")
