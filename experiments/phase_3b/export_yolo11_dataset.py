#!/usr/bin/env python3
"""Export the Phase 3B.1 curated split as a portable YOLO11 dataset.

The Phase 3B.1 manifest is the only authority for train/validation membership.
Images and labels are copied byte-for-byte from the read-only v15 extraction
into ``datasets/exports/phase_3b2b1_yolo11n`` and packaged as a ZIP whose root
is the export directory itself. No source file is moved or modified, and no
model, package or training run is involved.

Usage::

    python experiments/phase_3b/export_yolo11_dataset.py
    python experiments/phase_3b/export_yolo11_dataset.py --verify-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402
from PIL import Image, UnidentifiedImageError  # noqa: E402

from perception.dataset import (  # noqa: E402
    CuratedDataset,
    DatasetError,
    parse_yolo_label,
)
from perception.manifest import ManifestError, SplitManifest  # noqa: E402

DEFAULT_MANIFEST = PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"
DEFAULT_EXPORT_ROOT = (
    PROJECT_ROOT / "datasets" / "exports" / "phase_3b2b1_yolo11n"
)
DEFAULT_ZIP_PATH = (
    PROJECT_ROOT / "datasets" / "exports" / "phase_3b2b1_yolo11n.zip"
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
CHECKSUM_NAME = "SHA256SUMS.txt"
PROVENANCE_FILES = (
    "split_manifest.json",
    "dataset_summary.json",
    "attribution.txt",
    CHECKSUM_NAME,
)

EXPECTED = {
    "source_images": 2328,
    "total_images": 2316,
    "train_images": 1188,
    "valid_images": 1128,
    "total_boxes": 8666,
    "train_boxes": 4704,
    "valid_boxes": 3962,
    "classes": 14,
    "quarantined": 12,
    "source_split_mismatches": {
        "train_to_valid": 903,
        "valid_to_train": 275,
    },
}

KNOWN_LIMITATIONS = (
    "There is no independent test split; the validation groups are held out "
    "for development only.",
    "boots-powerup and jump-electric have zero validation boxes and are "
    "unevaluable on this split.",
    "undercover-barrier, jump-hedge, ledge, jump-trash and pogstick-powerup "
    "have low validation support and must be reported with support counts.",
    "The 12 empty labels were quarantined, not repaired; empty is not "
    "evidence of an empty scene in this dataset.",
    "Player, coins, lanes and metric distance are not annotated and are not "
    "part of this export.",
    "Annotations are copied unchanged, including any original annotation "
    "errors that survived curation.",
)


class ExportError(RuntimeError):
    """Raised when the export or its verification cannot satisfy the contract."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _normalise(value: str) -> str:
    text = str(value).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _class_names(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        try:
            keys = sorted(value, key=lambda key: int(key))
        except (TypeError, ValueError) as exc:
            raise ExportError("class names must use integer keys") from exc
        return [str(value[key]) for key in keys]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    raise ExportError("class names must be a list or an integer-keyed mapping")


def _label_relative(image_relative: str) -> str:
    relative = _normalise(image_relative)
    if "/images/" not in relative:
        raise ExportError(f"image path is not inside an images directory: {relative}")
    return f"{relative.replace('/images/', '/labels/').rsplit('.', 1)[0]}.txt"


def load_source_metadata(dataset_root: Path) -> dict:
    """Read the read-only v15 metadata used for provenance and class checks."""
    root = Path(dataset_root)
    yaml_path = root / "data.yaml"
    if not yaml_path.is_file():
        raise ExportError(f"source data.yaml not found: {yaml_path}")
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ExportError("source data.yaml must be a mapping")
    names = _class_names(payload.get("names"))
    nc = payload.get("nc")
    if nc is not None and int(nc) != len(names):
        raise ExportError("source data.yaml nc does not match its class list")
    roboflow = payload.get("roboflow") or {}
    if not isinstance(roboflow, Mapping):
        raise ExportError("source data.yaml roboflow block must be a mapping")
    return {
        "class_names": names,
        "nc": len(names),
        "version": roboflow.get("version"),
        "workspace": roboflow.get("workspace"),
        "project": roboflow.get("project"),
        "url": roboflow.get("url"),
        "licence": roboflow.get("license"),
        "source_yaml": str(yaml_path),
        "source_yaml_sha256": sha256_file(yaml_path),
    }


def build_export_plan(dataset: CuratedDataset) -> list[dict]:
    """Build a deterministic, collision-free copy plan from the curated dataset."""
    plan: list[dict] = []
    used: dict[str, set[str]] = {"train": set(), "valid": set()}
    output_paths: set[str] = set()
    for image in sorted(dataset.images, key=lambda item: (item.split, item.relative_path)):
        if image.split not in used:
            raise ExportError(f"unexpected split {image.split!r}")
        suffix = image.path.suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise ExportError(f"unsupported image suffix {suffix!r}: {image.path}")
        stem = image.path.stem
        candidate = stem
        if candidate.casefold() in used[image.split]:
            candidate = f"{stem}__{image.group}"
            counter = 2
            while candidate.casefold() in used[image.split]:
                candidate = f"{stem}__{image.group}__{counter}"
                counter += 1
        used[image.split].add(candidate.casefold())
        image_name = f"{candidate}{suffix}"
        label_name = f"{candidate}.txt"
        exported_image = f"{image.split}/images/{image_name}"
        exported_label = f"{image.split}/labels/{label_name}"
        if exported_image in output_paths or exported_label in output_paths:
            raise ExportError(f"duplicate output path: {exported_image}")
        output_paths.add(exported_image)
        output_paths.add(exported_label)
        source_relative = _normalise(image.relative_path)
        plan.append(
            {
                "split": image.split,
                "group": image.group,
                "source_image": source_relative,
                "source_label": _label_relative(source_relative),
                "exported_image": exported_image,
                "exported_label": exported_label,
                "original_basename": image.path.name,
                "renamed": candidate != stem,
                "n_boxes": image.n_boxes,
                "class_counts": image.class_counts(),
                "image_size": list(image.image_size),
                "sha256_image": None,
                "sha256_label": None,
            }
        )
    if not plan:
        raise ExportError("the export plan is empty")
    return plan


def build_counts(plan: Sequence[Mapping[str, Any]]) -> dict:
    counts = {
        "total_images": len(plan),
        "train_images": 0,
        "valid_images": 0,
        "total_boxes": 0,
        "train_boxes": 0,
        "valid_boxes": 0,
    }
    for item in plan:
        split = item["split"]
        counts[f"{split}_images"] += 1
        counts[f"{split}_boxes"] += int(item["n_boxes"])
        counts["total_boxes"] += int(item["n_boxes"])
    counts["images_without_boxes"] = sum(1 for item in plan if item["n_boxes"] == 0)
    return counts


def _assert_expected(counts: Mapping[str, Any], expected: Mapping[str, Any] | None) -> None:
    if not expected:
        return
    for key, value in expected.items():
        if key in counts and counts[key] != value:
            raise ExportError(
                f"count mismatch for {key}: expected {value}, got {counts[key]}"
            )


def write_dataset_yaml(path: Path, class_names: Sequence[str]) -> None:
    names = list(class_names)
    if not names:
        raise ExportError("class name list is empty")
    payload = {
        "path": ".",
        "train": "train/images",
        "val": "valid/images",
        "nc": len(names),
        "names": {index: name for index, name in enumerate(names)},
    }
    header = (
        "# Phase 3B.2B.1 portable YOLO11 dataset export.\n"
        "# Paths are relative to this file and resolve after ZIP extraction.\n"
        "# There is no independent test split; 'val' is group-held-out.\n"
    )
    text = header + yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")


def write_attribution(path: Path, metadata: Mapping[str, Any]) -> None:
    text = f"""Subway Surfers Object Dataset — Phase 3B.2B.1 export attribution

Dataset name: Subway Surfers Object Dataset
Roboflow project: {metadata['project']}
Roboflow workspace: {metadata['workspace']}
Dataset version: {metadata['version']}
Original export date: 2024-05-05 (README.roboflow.txt: May 5, 2024 at 6:32 AM GMT)
Dataset licence: CC BY 4.0 (as declared by the Roboflow export)
Source URL: {metadata['url']}
Licence text: https://creativecommons.org/licenses/by/4.0/

Attribution:
Provided by a Roboflow user in workspace {metadata['workspace']}. The local
metadata does not name an individual creator or publisher beyond that
statement. Credit the dataset publisher and the Roboflow source URL above when
redistributing this export or derivatives of it.

Modifications made for this export:
- Sequence/group-based re-splitting from the Phase 3B.1 curation manifest.
- 12 quarantined images excluded (9 probable annotation gaps in
  subwayedtied, 3 ambiguous empty labels in subwayy1_1).
- Images and labels copied into a portable YOLO directory structure.
- No original annotation values were intentionally changed.
- Filenames are unchanged unless a collision required a deterministic suffix;
  no collision occurred in this export.

This export does not create an independent test set. The validation split is
group-held-out development data.

The YOLO11n model checkpoint is a separate work under AGPL-3.0 and is not part
of this dataset or its licence.
"""
    path.write_text(text, encoding="utf-8")


def build_split_manifest(
    dataset: CuratedDataset,
    plan: Sequence[Mapping[str, Any]],
    *,
    class_names: Sequence[str],
) -> dict:
    assignments = {
        _normalise(str(key)): value
        for key, value in dataset.manifest.payload["fixed_split"]["assignments"].items()
    }
    exclusions = {
        _normalise(entry["path"]): entry
        for entry in dataset.manifest.payload.get("exclusions", [])
    }
    entries = []
    for item in plan:
        expected_split = assignments.get(item["source_image"])
        if expected_split != item["split"]:
            raise ExportError(
                f"manifest split mismatch for {item['source_image']}: "
                f"{item['split']} != {expected_split}"
            )
        entries.append(
            {
                "source_image": item["source_image"],
                "source_label": item["source_label"],
                "group": item["group"],
                "split": item["split"],
                "status": "exported",
                "roboflow_split": item["source_image"].split("/")[0],
                "exported_image": item["exported_image"],
                "exported_label": item["exported_label"],
                "renamed": item["renamed"],
                "sha256_image": item["sha256_image"],
                "sha256_label": item["sha256_label"],
            }
        )
    quarantine = []
    for relative in sorted(dataset.excluded):
        source = _normalise(relative)
        entry = exclusions.get(source)
        if entry is None:
            raise ExportError(f"excluded image has no manifest reason: {source}")
        group = entry.get("group")
        if group is None:
            group = dataset.manifest.group_for(Path(source).name)
        quarantine.append(
            {
                "source_image": source,
                "source_label": _label_relative(source),
                "group": str(group),
                "reason": str(entry.get("reason", "excluded")),
                "status": "quarantined",
                "exported_image": None,
                "exported_label": None,
            }
        )
    return {
        "phase": "3B.2B.1",
        "kind": "derived_export_manifest",
        "derived_from": "reports/PHASE_3B1_SPLIT_MANIFEST.json",
        "source_manifest_sha256": dataset.manifest_sha256,
        "source_manifest_policy": dataset.manifest.payload.get("policy"),
        "class_names": list(class_names),
        "fixed_split": {
            "train_groups": list(dataset.manifest.train_groups),
            "valid_groups": list(dataset.manifest.valid_groups),
            "counts": build_counts(plan),
        },
        "entries": entries,
        "quarantine": quarantine,
        "notes": [
            "Membership is taken only from the Phase 3B.1 fixed_split assignments.",
            "The original Roboflow train/valid folders are storage locations, not the split.",
            "Quarantined entries are recorded here and are not exported.",
            "source_image and source_label are relative to the v15 dataset root.",
        ],
    }


def _copy_verified(source: Path, destination: Path) -> str:
    if not source.is_file():
        raise ExportError(f"source file not found: {source}")
    if destination.exists():
        raise ExportError(f"refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    source_hash = sha256_file(source)
    destination_hash = sha256_file(destination)
    if source_hash != destination_hash:
        raise ExportError(f"copy hash mismatch: {source} -> {destination}")
    return destination_hash


def _verify_image(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as opened:
            opened.verify()
        with Image.open(path) as opened:
            width, height = opened.size
    except (OSError, UnidentifiedImageError) as exc:
        raise ExportError(f"image is not readable: {path}: {exc}") from exc
    if width < 1 or height < 1:
        raise ExportError(f"image has a non-positive size: {path}")
    return int(width), int(height)


def _export_files(root: Path) -> list[Path]:
    files = [root / "dataset.yaml"]
    for split in ("train", "valid"):
        for kind in ("images", "labels"):
            directory = root / split / kind
            if not directory.is_dir():
                raise ExportError(f"missing export directory: {directory}")
            files.extend(sorted(path for path in directory.iterdir() if path.is_file()))
    provenance = root / "provenance"
    if not provenance.is_dir():
        raise ExportError(f"missing provenance directory: {provenance}")
    for name in ("split_manifest.json", "dataset_summary.json", "attribution.txt"):
        path = provenance / name
        if not path.is_file():
            raise ExportError(f"missing provenance file: {path}")
        files.append(path)
    return files


def write_checksums(root: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for path in _export_files(root):
        relative = path.relative_to(root).as_posix()
        checksums[relative] = sha256_file(path)
    checksums = dict(sorted(checksums.items()))
    lines = [f"{digest}  {relative}\n" for relative, digest in checksums.items()]
    (root / "provenance" / CHECKSUM_NAME).write_text("".join(lines), encoding="utf-8")
    return checksums


def read_checksums(root: Path) -> dict[str, str]:
    path = root / "provenance" / CHECKSUM_NAME
    if not path.is_file():
        raise ExportError(f"checksum file not found: {path}")
    checksums: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if "  " not in line:
            raise ExportError(f"{path.name}:{number}: malformed checksum line")
        digest, relative = line.split("  ", 1)
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ExportError(f"{path.name}:{number}: invalid SHA-256 digest")
        if relative == CHECKSUM_NAME or relative.startswith("/") or ".." in Path(relative).parts:
            raise ExportError(f"{path.name}:{number}: invalid relative path {relative!r}")
        if relative in checksums:
            raise ExportError(f"{path.name}:{number}: duplicate path {relative!r}")
        checksums[relative] = digest
    if not checksums:
        raise ExportError("checksum file is empty")
    return checksums


def build_dataset_summary(
    dataset: CuratedDataset,
    plan: Sequence[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any],
    verification: Mapping[str, Any],
    export_root: Path,
    zip_path: Path,
    created_at: str,
) -> dict:
    class_names = list(dataset.class_names)
    per_class = {
        str(index): {
            "id": index,
            "name": name,
            "train_boxes": 0,
            "train_images": 0,
            "valid_boxes": 0,
            "valid_images": 0,
        }
        for index, name in enumerate(class_names)
    }
    for item in plan:
        split = item["split"]
        for class_id, count in item["class_counts"].items():
            row = per_class[str(class_id)]
            row[f"{split}_boxes"] += int(count)
            row[f"{split}_images"] += 1
    groups: dict[str, dict] = {}
    for item in plan:
        row = groups.setdefault(
            item["group"],
            {"split": item["split"], "images": 0, "boxes": 0},
        )
        if row["split"] != item["split"]:
            raise ExportError(f"group {item['group']} appears in both splits")
        row["images"] += 1
        row["boxes"] += int(item["n_boxes"])
    dimensions = Counter(
        f"{item['image_size'][0]}x{item['image_size'][1]}" for item in plan
    )
    counts = build_counts(plan)
    quarantine_reasons = Counter(
        str(entry.get("reason", "excluded"))
        for entry in dataset.manifest.payload.get("exclusions", [])
    )
    return {
        "phase": "3B.2B.1",
        "source": {
            "dataset_name": "Subway Surfers Object Dataset",
            "version": metadata["version"],
            "workspace": metadata["workspace"],
            "project": metadata["project"],
            "url": metadata["url"],
            "licence": metadata["licence"],
            "source_yaml": metadata["source_yaml"],
            "source_yaml_sha256": metadata["source_yaml_sha256"],
            "dataset_root": str(dataset.manifest.dataset_root_path),
            "source_manifest": str(dataset.manifest.source_path),
            "source_manifest_sha256": dataset.manifest_sha256,
        },
        "export": {
            "created_at_utc": created_at,
            "directory": export_root.name,
            "zip": zip_path.name,
            "script": "experiments/phase_3b/export_yolo11_dataset.py",
        },
        "counts": counts,
        "per_class": per_class,
        "groups": dict(sorted(groups.items())),
        "quarantine": {
            "count": len(dataset.excluded),
            "by_reason": dict(sorted(quarantine_reasons.items())),
            "source_images": list(dataset.excluded),
        },
        "image_dimensions": dict(sorted(dimensions.items())),
        "file_counts": {
            "images": counts["total_images"],
            "labels": counts["total_images"],
            "dataset_yaml": 1,
            "provenance_files": 4,
            "total_files": counts["total_images"] * 2 + 5,
        },
        "class_mapping": [
            {"id": index, "name": name} for index, name in enumerate(class_names)
        ],
        "source_manifest_sha256": dataset.manifest_sha256,
        "verification": dict(verification),
        "known_limitations": list(KNOWN_LIMITATIONS),
        "independent_test_set": False,
    }


def _allowed_relative(relative: str) -> bool:
    if relative == "dataset.yaml":
        return True
    parts = relative.split("/")
    if len(parts) == 3 and parts[0] in ("train", "valid") and parts[1] in ("images", "labels"):
        return True
    if len(parts) == 2 and parts[0] == "provenance" and parts[1] in PROVENANCE_FILES:
        return True
    return False


def verify_export(
    export_root: str | Path,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    class_names: Sequence[str] | None = None,
    expected: Mapping[str, Any] | None = None,
    require_checksums: bool = True,
    require_summary: bool = True,
    verify_source_hashes: bool = True,
) -> dict:
    """Verify an exported directory against its manifest and source files."""
    root = Path(export_root).resolve()
    if not root.is_dir():
        raise ExportError(f"export directory not found: {root}")
    manifest = SplitManifest.load(manifest_path)
    source_root = manifest.dataset_root_path
    names = tuple(class_names or manifest.class_names)
    required_classes = (
        int(expected["classes"]) if expected and "classes" in expected else 14
    )
    if len(names) != required_classes:
        raise ExportError(
            f"expected {required_classes} class names, got {len(names)}"
        )

    yaml_path = root / "dataset.yaml"
    if not yaml_path.is_file():
        raise ExportError("dataset.yaml is missing")
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ExportError("dataset.yaml must be a mapping")
    if str(payload.get("path")) != ".":
        raise ExportError("dataset.yaml path must be '.' for portability")
    if payload.get("train") != "train/images" or payload.get("val") != "valid/images":
        raise ExportError("dataset.yaml must use train/images and valid/images")
    if int(payload.get("nc", -1)) != len(names):
        raise ExportError("dataset.yaml nc does not match the class list")
    if tuple(_class_names(payload.get("names"))) != names:
        raise ExportError("dataset.yaml class names do not match the manifest")
    for key in ("train", "val"):
        relative = Path(str(payload[key]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ExportError(f"dataset.yaml {key} path is not portable: {relative}")
        if not (root / relative).is_dir():
            raise ExportError(f"dataset.yaml {key} path does not resolve: {relative}")

    if not (root / "provenance" / "attribution.txt").is_file():
        raise ExportError("provenance/attribution.txt is missing")
    derived_path = root / "provenance" / "split_manifest.json"
    if not derived_path.is_file():
        raise ExportError("provenance/split_manifest.json is missing")
    derived = json.loads(derived_path.read_text(encoding="utf-8"))
    if not isinstance(derived, Mapping):
        raise ExportError("derived split manifest must be an object")
    source_manifest_sha256 = sha256_file(manifest.source_path)
    if derived.get("source_manifest_sha256") != source_manifest_sha256:
        raise ExportError("derived split manifest source hash does not match")
    source_metadata = load_source_metadata(source_root)
    if tuple(source_metadata["class_names"]) != names:
        raise ExportError(
            "dataset.yaml class mapping does not match the audited v15 metadata"
        )

    raw_assignments = manifest.payload["fixed_split"].get("assignments")
    if not isinstance(raw_assignments, Mapping):
        raise ExportError("manifest fixed_split.assignments must be a mapping")
    assignments = {
        _normalise(str(key)): value for key, value in raw_assignments.items()
    }
    exclusions = {
        _normalise(entry["path"]): entry
        for entry in manifest.payload.get("exclusions", [])
    }
    if set(assignments) & set(exclusions):
        raise ExportError("manifest assigns a quarantined image")

    entries = derived.get("entries")
    quarantine = derived.get("quarantine")
    if not isinstance(entries, list) or not isinstance(quarantine, list):
        raise ExportError("derived split manifest must contain entries and quarantine")
    by_source: dict[str, Mapping[str, Any]] = {}
    groups: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ExportError("derived manifest entries must be objects")
        source = _normalise(str(entry.get("source_image", "")))
        if not source:
            raise ExportError("derived manifest entry has no source image")
        if source in by_source:
            raise ExportError(f"duplicate derived manifest entry: {source}")
        split = entry.get("split")
        if split not in ("train", "valid"):
            raise ExportError(f"invalid export split for {source}: {split!r}")
        if assignments.get(source) != split:
            raise ExportError(f"export split differs from manifest for {source}")
        group = str(entry.get("group", ""))
        expected_group = manifest.group_for(Path(source).name)
        if group != expected_group:
            raise ExportError(f"group mismatch for {source}: {group} != {expected_group}")
        if entry.get("status") != "exported":
            raise ExportError(f"entry is not marked exported: {source}")
        by_source[source] = entry
        groups[group].add(split)
    if set(by_source) != set(assignments):
        missing = sorted(set(assignments) - set(by_source))
        extra = sorted(set(by_source) - set(assignments))
        raise ExportError(
            f"derived manifest membership mismatch; missing={missing[:3]} "
            f"extra={extra[:3]}"
        )
    for group, splits in groups.items():
        if len(splits) > 1:
            raise ExportError(f"group {group!r} appears in both splits")

    quarantined_sources = set()
    for entry in quarantine:
        if not isinstance(entry, Mapping):
            raise ExportError("quarantine entries must be objects")
        source = _normalise(str(entry.get("source_image", "")))
        if source not in exclusions:
            raise ExportError(f"unexpected quarantined image: {source}")
        if entry.get("status") != "quarantined" or entry.get("exported_image") is not None:
            raise ExportError(f"quarantined image is not excluded: {source}")
        quarantined_sources.add(source)
    if quarantined_sources != set(exclusions):
        raise ExportError("quarantine list does not match the manifest exclusions")

    actual_files = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }
    for relative in actual_files:
        if not _allowed_relative(relative):
            raise ExportError(f"unexpected file in export: {relative}")

    counts = {"train_images": 0, "valid_images": 0, "train_boxes": 0, "valid_boxes": 0}
    exported_images: set[str] = set()
    exported_labels: set[str] = set()
    referenced_images: set[str] = set()
    referenced_labels: set[str] = set()
    dimensions: Counter = Counter()
    source_mismatches: Counter = Counter()
    per_class = {
        index: {
            "id": index,
            "name": name,
            "train_boxes": 0,
            "train_images": 0,
            "valid_boxes": 0,
            "valid_images": 0,
        }
        for index, name in enumerate(names)
    }
    for split in ("train", "valid"):
        image_dir = root / split / "images"
        label_dir = root / split / "labels"
        images = [path for path in image_dir.iterdir() if path.is_file()]
        labels = [path for path in label_dir.iterdir() if path.is_file()]
        image_by_stem: dict[str, Path] = {}
        for path in images:
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                raise ExportError(f"unsupported image file: {path.name}")
            if path.stem.casefold() in image_by_stem:
                raise ExportError(f"duplicate image stem in {split}: {path.stem}")
            image_by_stem[path.stem.casefold()] = path
        label_by_stem: dict[str, Path] = {}
        for path in labels:
            if path.suffix.lower() != ".txt":
                raise ExportError(f"unsupported label file: {path.name}")
            if path.stem.casefold() in label_by_stem:
                raise ExportError(f"duplicate label stem in {split}: {path.stem}")
            label_by_stem[path.stem.casefold()] = path
        if set(image_by_stem) != set(label_by_stem):
            missing_images = sorted(set(label_by_stem) - set(image_by_stem))
            missing_labels = sorted(set(image_by_stem) - set(label_by_stem))
            raise ExportError(
                f"{split} image/label mismatch; missing images={missing_images[:3]} "
                f"missing labels={missing_labels[:3]}"
            )
        for stem, image_path in image_by_stem.items():
            label_path = label_by_stem[stem]
            width, height = _verify_image(image_path)
            dimensions[f"{width}x{height}"] += 1
            boxes = parse_yolo_label(label_path, class_names=names)
            if not boxes:
                raise ExportError(f"empty label in export: {label_path}")
            counts[f"{split}_images"] += 1
            counts[f"{split}_boxes"] += len(boxes)
            exported_images.add(image_path.relative_to(root).as_posix())
            exported_labels.add(label_path.relative_to(root).as_posix())
            present_classes: set[int] = set()
            for box in boxes:
                per_class[box.class_id][f"{split}_boxes"] += 1
                present_classes.add(box.class_id)
            for class_id in present_classes:
                per_class[class_id][f"{split}_images"] += 1

    expected_images = len(entries)
    if counts["train_images"] + counts["valid_images"] != expected_images:
        raise ExportError("exported image count does not match the derived manifest")
    for source, entry in by_source.items():
        split = entry["split"]
        image_relative = _normalise(str(entry.get("exported_image", "")))
        label_relative = _normalise(str(entry.get("exported_label", "")))
        if image_relative not in exported_images or label_relative not in exported_labels:
            raise ExportError(f"exported files are missing for {source}")
        if image_relative in referenced_images or label_relative in referenced_labels:
            raise ExportError(f"duplicate exported path reference for {source}")
        referenced_images.add(image_relative)
        referenced_labels.add(label_relative)
        if image_relative.split("/")[0] != split or label_relative.split("/")[0] != split:
            raise ExportError(f"exported path has the wrong split for {source}")
        if Path(label_relative).stem != Path(image_relative).stem:
            raise ExportError(f"image/label stem mismatch for {source}")
        image_path = root / image_relative
        label_path = root / label_relative
        if verify_source_hashes:
            source_image = source_root / source
            source_label = source_root / _label_relative(source)
            if not source_image.is_file() or not source_label.is_file():
                raise ExportError(f"source file is missing for {source}")
            if sha256_file(source_image) != sha256_file(image_path):
                raise ExportError(f"image content changed: {source}")
            if sha256_file(source_label) != sha256_file(label_path):
                raise ExportError(f"label content changed: {source}")
        if entry.get("sha256_image") not in (None, sha256_file(image_path)):
            raise ExportError(f"recorded image hash mismatch: {source}")
        if entry.get("sha256_label") not in (None, sha256_file(label_path)):
            raise ExportError(f"recorded label hash mismatch: {source}")
        source_mismatches[f"{source.split('/')[0]}_to_{split}"] += 1

    if referenced_images != exported_images or referenced_labels != exported_labels:
        raise ExportError(
            "derived manifest does not reference every exported file exactly once"
        )

    total_images = counts["train_images"] + counts["valid_images"]
    total_boxes = counts["train_boxes"] + counts["valid_boxes"]
    computed = {
        "total_images": total_images,
        "total_boxes": total_boxes,
        "classes": len(names),
        "quarantined": len(exclusions),
        "source_images": total_images + len(exclusions),
        **counts,
    }
    _assert_expected(computed, expected)
    if expected and "source_split_mismatches" in expected:
        for key, value in expected["source_split_mismatches"].items():
            if source_mismatches.get(key, 0) != value:
                raise ExportError(
                    f"source split mismatch count for {key}: "
                    f"expected {value}, got {source_mismatches.get(key, 0)}"
                )

    if require_checksums:
        checksums = read_checksums(root)
        expected_files = {
            path.relative_to(root).as_posix()
            for path in _export_files(root)
            if path.name != CHECKSUM_NAME
        }
        if set(checksums) != expected_files:
            raise ExportError("checksum file does not cover exactly the export files")
        for relative, digest in checksums.items():
            if sha256_file(root / relative) != digest:
                raise ExportError(f"checksum mismatch: {relative}")

    if require_summary:
        summary_path = root / "provenance" / "dataset_summary.json"
        if not summary_path.is_file():
            raise ExportError("provenance/dataset_summary.json is missing")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("source_manifest_sha256") != sha256_file(manifest.source_path):
            raise ExportError("dataset summary source manifest hash does not match")
        if summary.get("counts", {}).get("total_images") != total_images:
            raise ExportError("dataset summary image count does not match the export")
        if summary.get("verification", {}).get("status") != "PASS":
            raise ExportError("dataset summary does not record a passing verification")

    per_class_payload = {
        str(index): {
            "name": row["name"],
            "train_boxes": row["train_boxes"],
            "train_images": row["train_images"],
            "valid_boxes": row["valid_boxes"],
            "valid_images": row["valid_images"],
        }
        for index, row in sorted(per_class.items())
    }
    return {
        "status": "PASS",
        "counts": computed,
        "per_class": per_class_payload,
        "classes_without_train_boxes": [
            row["name"] for row in per_class.values() if row["train_boxes"] == 0
        ],
        "classes_without_valid_boxes": [
            row["name"] for row in per_class.values() if row["valid_boxes"] == 0
        ],
        "source_split_mismatches": dict(sorted(source_mismatches.items())),
        "image_dimensions": dict(sorted(dimensions.items())),
        "source_manifest_sha256": source_manifest_sha256,
    }


def create_zip(export_root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        raise ExportError(f"refusing to overwrite existing ZIP: {zip_path}")
    root_name = export_root.name
    checksums = read_checksums(export_root)
    checksum_relative = f"provenance/{CHECKSUM_NAME}"
    members = dict(checksums)
    members[checksum_relative] = sha256_file(export_root / checksum_relative)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
    ) as archive:
        directory = zipfile.ZipInfo(f"{root_name}/", date_time=(1980, 1, 1, 0, 0, 0))
        directory.external_attr = (0o40755 << 16) | 0x10
        archive.writestr(directory, b"")
        for relative in sorted(members):
            info = zipfile.ZipInfo(
                f"{root_name}/{relative}", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (export_root / relative).read_bytes())


def verify_zip(zip_path: str | Path, export_root: str | Path) -> dict:
    zip_path = Path(zip_path)
    root = Path(export_root).resolve()
    if not zip_path.is_file():
        raise ExportError(f"ZIP not found: {zip_path}")
    checksums = read_checksums(root)
    root_name = root.name
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ExportError(f"ZIP integrity failure at {bad}")
        names = archive.namelist()
        if f"{root_name}/" not in names:
            raise ExportError("ZIP does not contain the export directory root")
        members = [name for name in names if name != f"{root_name}/"]
        for name in members:
            if not name.startswith(f"{root_name}/"):
                raise ExportError(f"ZIP entry is outside the export root: {name}")
            relative = name[len(root_name) + 1 :]
            if relative.startswith("/") or ".." in Path(relative).parts:
                raise ExportError(f"unsafe ZIP path: {name}")
            if Path(relative).suffix.lower() in {".pt", ".pth", ".onnx", ".ckpt"}:
                raise ExportError(f"model checkpoint in dataset ZIP: {name}")
        checksum_relative = f"provenance/{CHECKSUM_NAME}"
        expected = set(checksums) | {checksum_relative}
        actual = {name[len(root_name) + 1 :] for name in members}
        if actual != expected:
            raise ExportError("ZIP contents do not match the checksum manifest")
        for relative, digest in checksums.items():
            if _sha256_bytes(archive.read(f"{root_name}/{relative}")) != digest:
                raise ExportError(f"ZIP member hash mismatch: {relative}")
        if archive.read(f"{root_name}/{checksum_relative}") != (
            root / checksum_relative
        ).read_bytes():
            raise ExportError("ZIP checksum file differs from the export directory")
        if f"{root_name}/dataset.yaml" not in names:
            raise ExportError("ZIP does not contain dataset.yaml at its root")
    return {
        "status": "PASS",
        "files": len(expected),
        "entries": len(members) + 1,
        "size_bytes": zip_path.stat().st_size,
        "root": f"{root_name}/",
    }


def export_dataset(
    *,
    export_root: str | Path = DEFAULT_EXPORT_ROOT,
    zip_path: str | Path = DEFAULT_ZIP_PATH,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    expected: Mapping[str, Any] | None = EXPECTED,
) -> dict:
    root = Path(export_root).resolve()
    zip_file = Path(zip_path).resolve()
    if root.exists():
        raise ExportError(f"export directory already exists: {root}")
    if zip_file.exists():
        raise ExportError(f"export ZIP already exists: {zip_file}")

    dataset = CuratedDataset.load(manifest_path, verify_images=True)
    metadata = load_source_metadata(dataset.manifest.dataset_root_path)
    if tuple(metadata["class_names"]) != tuple(dataset.class_names):
        raise ExportError("source data.yaml class names do not match the manifest")
    if expected and "classes" in expected:
        if len(dataset.class_names) != int(expected["classes"]):
            raise ExportError(
                f"expected {expected['classes']} classes, "
                f"got {len(dataset.class_names)}"
            )
    if expected and "quarantined" in expected:
        if len(dataset.excluded) != int(expected["quarantined"]):
            raise ExportError(
                f"expected {expected['quarantined']} quarantined images, "
                f"got {len(dataset.excluded)}"
            )
    if expected and "source_images" in expected:
        if len(dataset.images) + len(dataset.excluded) != int(
            expected["source_images"]
        ):
            raise ExportError(
                "curated plus quarantined images do not equal the expected "
                "source image count"
            )
    plan = build_export_plan(dataset)
    counts = build_counts(plan)
    _assert_expected(counts, expected)

    root.mkdir(parents=True, exist_ok=False)
    for item in plan:
        source_image = dataset.manifest.dataset_root_path / item["source_image"]
        source_label = dataset.manifest.dataset_root_path / item["source_label"]
        item["sha256_image"] = _copy_verified(
            source_image, root / item["exported_image"]
        )
        item["sha256_label"] = _copy_verified(
            source_label, root / item["exported_label"]
        )

    write_dataset_yaml(root / "dataset.yaml", dataset.class_names)
    (root / "provenance").mkdir(parents=True, exist_ok=True)
    write_attribution(root / "provenance" / "attribution.txt", metadata)
    _write_json(
        root / "provenance" / "split_manifest.json",
        build_split_manifest(dataset, plan, class_names=dataset.class_names),
    )

    preliminary = verify_export(
        root,
        manifest_path=manifest_path,
        class_names=dataset.class_names,
        expected=expected,
        require_checksums=False,
        require_summary=False,
    )
    created_at = _utc_now()
    summary = build_dataset_summary(
        dataset,
        plan,
        metadata=metadata,
        verification=preliminary,
        export_root=root,
        zip_path=zip_file,
        created_at=created_at,
    )
    _write_json(root / "provenance" / "dataset_summary.json", summary)
    write_checksums(root)
    final = verify_export(
        root,
        manifest_path=manifest_path,
        class_names=dataset.class_names,
        expected=expected,
        require_checksums=True,
        require_summary=True,
    )
    create_zip(root, zip_file)
    zip_result = verify_zip(zip_file, root)
    return {
        "status": "PASS",
        "export_root": str(root),
        "zip_path": str(zip_file),
        "directory_verification": final,
        "zip_verification": zip_result,
        "counts": counts,
        "quarantined": len(dataset.excluded),
        "source_manifest_sha256": dataset.manifest_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--skip-source-hashes",
        action="store_true",
        help="skip comparison with the read-only source files (extracted copies)",
    )
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            manifest = SplitManifest.load(args.manifest)
            directory = verify_export(
                args.export_root,
                manifest_path=args.manifest,
                expected=EXPECTED,
                require_checksums=True,
                require_summary=True,
                verify_source_hashes=not args.skip_source_hashes,
            )
            archive = verify_zip(args.zip_path, args.export_root)
            payload = {
                "status": "PASS",
                "export_root": str(Path(args.export_root).resolve()),
                "zip_path": str(Path(args.zip_path).resolve()),
                "directory_verification": directory,
                "zip_verification": archive,
                "source_manifest_sha256": sha256_file(manifest.source_path),
            }
        else:
            payload = export_dataset(
                export_root=args.export_root,
                zip_path=args.zip_path,
                manifest_path=args.manifest,
            )
    except (ExportError, DatasetError, ManifestError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
