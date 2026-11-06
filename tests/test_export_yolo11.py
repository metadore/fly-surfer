"""Phase 3B.2B.1 YOLO11 dataset export invariants.

All fixtures are synthetic and live in temporary directories. The read-only
v15 dataset is never modified; the only real-data assertion reads the Phase
3B.1 manifest as the split authority.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "phase_3b"))

import export_yolo11_dataset as export  # noqa: E402
from perception.dataset import (  # noqa: E402
    BoxAnnotation,
    DatasetError,
    DatasetImage,
)

CLASS_NAMES = ("alpha-class", "beta-class", "gamma-class")

SYNTHETIC_EXPECTED = {
    "source_images": 5,
    "total_images": 4,
    "train_images": 3,
    "valid_images": 1,
    "total_boxes": 5,
    "train_boxes": 4,
    "valid_boxes": 1,
    "classes": 3,
    "quarantined": 1,
    "source_split_mismatches": {
        "train_to_valid": 1,
        "valid_to_train": 1,
    },
}

EXCLUDED_RELATIVE = "train/images/gamma_1.jpg"


def _label_relative(image_relative: str) -> str:
    return (
        image_relative.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    )


def _write_image(path: Path, color: tuple[int, int, int] = (10, 20, 30)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), color).save(path, format="JPEG", quality=90)


def _write_label(path: Path, rows: tuple[tuple[float, ...], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(" ".join(str(value) for value in row) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def _synthetic_dataset(tmp_path: Path) -> SimpleNamespace:
    dataset_root = tmp_path / "dataset"
    files = (
        # Stored in Roboflow train, curated train.
        (
            "train/images/alpha_0.jpg",
            "train",
            "alpha",
            ((0, 0.5, 0.5, 0.2, 0.2), (1, 0.4, 0.4, 0.1, 0.1)),
        ),
        # Stored in Roboflow valid, curated train.
        ("valid/images/alpha_1.jpg", "train", "alpha", ((2, 0.6, 0.6, 0.3, 0.3),)),
        ("train/images/beta_0.jpg", "train", "beta", ((0, 0.3, 0.3, 0.2, 0.2),)),
        # Stored in Roboflow train, curated valid.
        ("train/images/gamma_0.jpg", "valid", "gamma", ((1, 0.7, 0.7, 0.1, 0.1),)),
    )
    assignments: dict[str, str] = {}
    for relative, split, _group, rows in files:
        _write_image(dataset_root / relative)
        _write_label(dataset_root / _label_relative(relative), rows)
        assignments[relative] = split

    _write_image(dataset_root / EXCLUDED_RELATIVE)
    _write_label(dataset_root / _label_relative(EXCLUDED_RELATIVE), ())

    (dataset_root / "data.yaml").write_text(
        yaml.safe_dump(
            {
                "nc": len(CLASS_NAMES),
                "names": list(CLASS_NAMES),
                "roboflow": {
                    "workspace": "synthetic-workspace",
                    "project": "synthetic-project",
                    "version": 15,
                    "license": "CC BY 4.0",
                    "url": "https://example.invalid/synthetic/15",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    manifest = {
        "phase": "synthetic",
        "dataset": {
            "discovered_root": str(dataset_root.resolve()).replace("\\", "/"),
            "version": 15,
            "class_names": list(CLASS_NAMES),
            "splits_present": ["train", "valid"],
        },
        "policy": {"exclude": "all"},
        "groups": {
            "alpha": {"prefixes": ["alpha"]},
            "beta": {"prefixes": ["beta"]},
            "gamma": {"prefixes": ["gamma"]},
        },
        "exclusions": [
            {
                "path": EXCLUDED_RELATIVE,
                "group": "gamma",
                "reason": "synthetic_empty_label",
            }
        ],
        "fixed_split": {
            "train_groups": ["alpha", "beta"],
            "valid_groups": ["gamma"],
            "assignments": assignments,
        },
        "logo_folds": [
            {"fold": 1, "valid_group": "alpha", "train_groups": ["beta", "gamma"]},
            {"fold": 2, "valid_group": "beta", "train_groups": ["alpha", "gamma"]},
            {"fold": 3, "valid_group": "gamma", "train_groups": ["alpha", "beta"]},
        ],
        "warnings": [],
        "limitations": [],
    }
    manifest_path = tmp_path / "split_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    export_root = tmp_path / "exports" / "synthetic_yolo"
    zip_path = tmp_path / "exports" / "synthetic_yolo.zip"
    result = export.export_dataset(
        export_root=export_root,
        zip_path=zip_path,
        manifest_path=manifest_path,
        expected=SYNTHETIC_EXPECTED,
    )
    return SimpleNamespace(
        dataset_root=dataset_root,
        manifest=manifest,
        manifest_path=manifest_path,
        export_root=export_root,
        zip_path=zip_path,
        result=result,
    )


@pytest.fixture()
def synthetic(tmp_path: Path) -> SimpleNamespace:
    return _synthetic_dataset(tmp_path)


def _verify(root: Path, manifest_path: Path, **overrides) -> dict:
    options = {
        "manifest_path": manifest_path,
        "expected": SYNTHETIC_EXPECTED,
        "require_checksums": False,
        "require_summary": False,
        "verify_source_hashes": False,
    }
    options.update(overrides)
    return export.verify_export(root, **options)


def test_real_manifest_matches_expected_membership():
    payload = json.loads(
        export.DEFAULT_MANIFEST.read_text(encoding="utf-8")
    )
    assignments = payload["fixed_split"]["assignments"]
    assert len(assignments) == export.EXPECTED["total_images"] == 2316
    assert sum(value == "train" for value in assignments.values()) == 1188
    assert sum(value == "valid" for value in assignments.values()) == 1128
    assert len(payload["exclusions"]) == export.EXPECTED["quarantined"] == 12
    assert len(payload["dataset"]["class_names"]) == export.EXPECTED["classes"] == 14
    assert payload["fixed_split"]["train"]["boxes"] == 4704
    assert payload["fixed_split"]["valid"]["boxes"] == 3962
    assert (
        payload["fixed_split"]["train"]["images"]
        + payload["fixed_split"]["valid"]["images"]
        == 2316
    )
    assert not set(assignments) & {
        entry["path"] for entry in payload["exclusions"]
    }


def test_export_membership_and_exact_counts(synthetic):
    derived = json.loads(
        (synthetic.export_root / "provenance" / "split_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    sources = [entry["source_image"] for entry in derived["entries"]]
    assert len(sources) == len(set(sources)) == 4
    assert set(sources) == set(synthetic.manifest["fixed_split"]["assignments"])
    assert all(entry["status"] == "exported" for entry in derived["entries"])

    result = _verify(
        synthetic.export_root,
        synthetic.manifest_path,
        require_checksums=True,
        require_summary=True,
    )
    assert result["status"] == "PASS"
    assert result["counts"]["train_images"] == 3
    assert result["counts"]["valid_images"] == 1
    assert result["counts"]["train_boxes"] == 4
    assert result["counts"]["valid_boxes"] == 1
    assert result["counts"]["total_boxes"] == 5
    assert result["counts"]["quarantined"] == 1
    assert result["counts"]["source_images"] == 5


def test_quarantined_images_are_never_exported(synthetic):
    exported = [
        path.relative_to(synthetic.export_root).as_posix()
        for path in (synthetic.export_root).rglob("*")
        if path.is_file()
    ]
    assert not any(path.endswith("gamma_1.jpg") for path in exported)
    assert not any(path.endswith("gamma_1.txt") for path in exported)

    derived = json.loads(
        (synthetic.export_root / "provenance" / "split_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert [entry["source_image"] for entry in derived["quarantine"]] == [
        EXCLUDED_RELATIVE
    ]
    assert derived["quarantine"][0]["status"] == "quarantined"
    assert derived["quarantine"][0]["exported_image"] is None

    for split in ("train", "valid"):
        for label in (synthetic.export_root / split / "labels").glob("*.txt"):
            assert label.read_text(encoding="utf-8").strip(), f"empty label {label}"


def test_group_membership_never_crosses_splits(synthetic):
    derived = json.loads(
        (synthetic.export_root / "provenance" / "split_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    by_group: dict[str, set[str]] = {}
    for entry in derived["entries"]:
        by_group.setdefault(entry["group"], set()).add(entry["split"])
    assert by_group == {"alpha": {"train"}, "beta": {"train"}, "gamma": {"valid"}}
    assert set(derived["fixed_split"]["train_groups"]).isdisjoint(
        derived["fixed_split"]["valid_groups"]
    )


def test_filename_collisions_are_renamed_without_overwrite(tmp_path):
    first = tmp_path / "one" / "alpha_0.jpg"
    second = tmp_path / "two" / "alpha_0.png"
    boxes = (BoxAnnotation(0, 0.5, 0.5, 0.2, 0.2),)
    dataset = SimpleNamespace(
        images=(
            DatasetImage(
                path=first,
                relative_path="train/images/alpha_0.jpg",
                label_path=first.with_suffix(".txt"),
                group="alpha",
                split="train",
                image_size=(32, 24),
                boxes=boxes,
            ),
            DatasetImage(
                path=second,
                relative_path="train/images/beta_0.png",
                label_path=second.with_suffix(".txt"),
                group="beta",
                split="train",
                image_size=(32, 24),
                boxes=boxes,
            ),
        )
    )
    plan = export.build_export_plan(dataset)
    images = [item["exported_image"] for item in plan]
    labels = [item["exported_label"] for item in plan]
    assert len(images) == len(set(images)) == 2
    assert len(labels) == len(set(labels)) == 2
    assert sum(item["renamed"] for item in plan) == 1
    assert images == [
        "train/images/alpha_0.jpg",
        "train/images/alpha_0__beta.png",
    ]


def test_every_exported_image_has_a_matching_label(synthetic):
    for split in ("train", "valid"):
        images = {
            path.stem for path in (synthetic.export_root / split / "images").glob("*")
        }
        labels = {
            path.stem for path in (synthetic.export_root / split / "labels").glob("*.txt")
        }
        assert images == labels
        assert images


def test_invalid_class_id_is_rejected(synthetic):
    label = synthetic.export_root / "train" / "labels" / "alpha_0.txt"
    rows = label.read_text(encoding="utf-8").splitlines()
    fields = rows[0].split()
    fields[0] = "99"
    rows[0] = " ".join(fields)
    label.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises((DatasetError, export.ExportError), match="class id"):
        _verify(synthetic.export_root, synthetic.manifest_path)


def test_invalid_normalised_coordinates_are_rejected(synthetic):
    label = synthetic.export_root / "valid" / "labels" / "gamma_0.txt"
    label.write_text("1 1.5 0.5 0.1 0.1\n", encoding="utf-8")
    with pytest.raises((DatasetError, export.ExportError), match="centre"):
        _verify(synthetic.export_root, synthetic.manifest_path)


def test_missing_label_is_rejected(synthetic):
    (synthetic.export_root / "train" / "labels" / "beta_0.txt").unlink()
    with pytest.raises(export.ExportError, match="image/label mismatch"):
        _verify(synthetic.export_root, synthetic.manifest_path)


def test_checksum_mismatch_is_rejected(synthetic):
    attribution = synthetic.export_root / "provenance" / "attribution.txt"
    attribution.write_text(
        attribution.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8"
    )
    with pytest.raises(export.ExportError, match="checksum mismatch"):
        _verify(
            synthetic.export_root,
            synthetic.manifest_path,
            require_checksums=True,
            require_summary=False,
        )


def test_source_content_change_is_detected(synthetic):
    image = synthetic.export_root / "train" / "images" / "alpha_0.jpg"
    Image.new("RGB", (32, 24), (200, 0, 0)).save(image, format="JPEG", quality=90)
    with pytest.raises(export.ExportError, match="content changed"):
        _verify(
            synthetic.export_root,
            synthetic.manifest_path,
            verify_source_hashes=True,
        )


def test_dataset_yaml_resolves_after_zip_extraction(synthetic, tmp_path):
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(synthetic.zip_path) as archive:
        archive.extractall(extract_dir)
    extracted_root = extract_dir / synthetic.export_root.name
    yaml_path = extracted_root / "dataset.yaml"
    assert yaml_path.is_file()

    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert payload["path"] == "."
    assert payload["train"] == "train/images"
    assert payload["val"] == "valid/images"
    assert payload["nc"] == 3
    assert [payload["names"][index] for index in range(3)] == list(CLASS_NAMES)
    for key in ("train", "val"):
        assert (extracted_root / payload[key]).is_dir()

    result = export.verify_export(
        extracted_root,
        manifest_path=synthetic.manifest_path,
        expected=SYNTHETIC_EXPECTED,
        require_checksums=True,
        require_summary=True,
        verify_source_hashes=True,
    )
    assert result["status"] == "PASS"


def test_wrong_expected_counts_fail_verification(synthetic):
    wrong = dict(SYNTHETIC_EXPECTED)
    wrong["train_images"] = 999
    with pytest.raises(export.ExportError, match="count mismatch"):
        _verify(synthetic.export_root, synthetic.manifest_path, expected=wrong)


def test_zip_contains_root_directory_and_no_checkpoint(synthetic):
    with zipfile.ZipFile(synthetic.zip_path) as archive:
        names = archive.namelist()
    root_prefix = f"{synthetic.export_root.name}/"
    assert root_prefix in names
    assert f"{root_prefix}dataset.yaml" in names
    assert f"{root_prefix}provenance/SHA256SUMS.txt" in names
    assert all(name.startswith(root_prefix) for name in names)
    assert not any(
        Path(name).suffix.lower() in {".pt", ".pth", ".onnx", ".ckpt"}
        for name in names
    )
    result = export.verify_zip(synthetic.zip_path, synthetic.export_root)
    assert result["status"] == "PASS"


def test_existing_export_is_never_overwritten(synthetic):
    with pytest.raises(export.ExportError, match="already exists"):
        export.export_dataset(
            export_root=synthetic.export_root,
            zip_path=synthetic.zip_path,
            manifest_path=synthetic.manifest_path,
            expected=SYNTHETIC_EXPECTED,
        )
