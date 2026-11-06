"""Validated access to the curated v15 detection dataset.

The split is taken from ``reports/PHASE_3B1_SPLIT_MANIFEST.json`` by filename
group; the Roboflow ``train``/``valid`` folders are only storage locations.
Quarantined images are skipped, never repaired. Every included image must have
a parseable YOLO label; an included empty label is an inconsistency, not a
negative example.

Class IDs, class names, group membership and the fixed split are treated as
read-only. This module reads the dataset and never writes to it.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image, UnidentifiedImageError

from perception.manifest import ManifestError, SplitManifest

_COORDINATE_TOLERANCE = 1e-6
_YOLO_FIELDS = 5


class DatasetError(ValueError):
    """Raised when the curated dataset or one of its annotations is invalid."""


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DatasetError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise DatasetError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class BoxAnnotation:
    """One YOLO box in normalised image coordinates."""

    class_id: int
    cx: float
    cy: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise DatasetError("class_id must be an integer")
        if self.class_id < 0:
            raise DatasetError("class_id must be non-negative")
        for name in ("cx", "cy", "width", "height"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.width <= 0.0 or self.height <= 0.0:
            raise DatasetError("box width and height must be positive")
        if self.width > 1.0 + _COORDINATE_TOLERANCE or self.height > 1.0 + _COORDINATE_TOLERANCE:
            raise DatasetError("box width and height must not exceed 1")
        if not 0.0 <= self.cx <= 1.0 or not 0.0 <= self.cy <= 1.0:
            raise DatasetError("box centre must lie in [0, 1]")
        low_x = self.cx - self.width / 2.0
        low_y = self.cy - self.height / 2.0
        high_x = self.cx + self.width / 2.0
        high_y = self.cy + self.height / 2.0
        if (
            low_x < -_COORDINATE_TOLERANCE
            or low_y < -_COORDINATE_TOLERANCE
            or high_x > 1.0 + _COORDINATE_TOLERANCE
            or high_y > 1.0 + _COORDINATE_TOLERANCE
        ):
            raise DatasetError("box extends outside the normalised image")

    @property
    def x1(self) -> float:
        return self.cx - self.width / 2.0

    @property
    def y1(self) -> float:
        return self.cy - self.height / 2.0

    @property
    def x2(self) -> float:
        return self.cx + self.width / 2.0

    @property
    def y2(self) -> float:
        return self.cy + self.height / 2.0

    @property
    def area(self) -> float:
        return self.width * self.height

    def as_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "cx": round(self.cx, 6),
            "cy": round(self.cy, 6),
            "width": round(self.width, 6),
            "height": round(self.height, 6),
        }

    def as_yolo_line(self) -> str:
        return (
            f"{self.class_id} {self.cx:.10g} {self.cy:.10g} "
            f"{self.width:.10g} {self.height:.10g}"
        )


@dataclass(frozen=True)
class DatasetImage:
    """One included image with its validated annotations."""

    path: Path
    relative_path: str
    label_path: Path
    group: str
    split: str
    image_size: tuple[int, int]
    boxes: tuple[BoxAnnotation, ...]

    @property
    def n_boxes(self) -> int:
        return len(self.boxes)

    def class_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for box in self.boxes:
            counts[box.class_id] = counts.get(box.class_id, 0) + 1
        return counts

    def as_dict(self, *, include_boxes: bool = False) -> dict:
        payload = {
            "path": self.relative_path,
            "group": self.group,
            "split": self.split,
            "image_size": list(self.image_size),
            "n_boxes": self.n_boxes,
            "class_counts": {
                str(class_id): count
                for class_id, count in sorted(self.class_counts().items())
            },
        }
        if include_boxes:
            payload["boxes"] = [box.as_dict() for box in self.boxes]
        return payload


@dataclass(frozen=True)
class LogoFold:
    """One leave-one-group-out view of the dataset."""

    fold: int
    valid_group: str
    train_groups: tuple[str, ...]
    train_images: tuple[DatasetImage, ...]
    valid_images: tuple[DatasetImage, ...]

    def apply(self, images: Iterable[DatasetImage]) -> tuple[tuple[DatasetImage, ...], tuple[DatasetImage, ...]]:
        """Return (train, valid) selections for an arbitrary image sequence."""
        train = tuple(image for image in images if image.group in self.train_groups)
        valid = tuple(image for image in images if image.group == self.valid_group)
        return train, valid

    def as_dict(self) -> dict:
        return {
            "fold": self.fold,
            "valid_group": self.valid_group,
            "train_groups": list(self.train_groups),
            "n_train_images": len(self.train_images),
            "n_valid_images": len(self.valid_images),
            "n_train_boxes": sum(image.n_boxes for image in self.train_images),
            "n_valid_boxes": sum(image.n_boxes for image in self.valid_images),
        }


@dataclass(frozen=True)
class SplitStatistics:
    """Aggregate counts for one split or fold view."""

    name: str
    images: int
    boxes: int
    images_without_boxes: int
    per_class_boxes: dict[str, int]
    per_class_images: dict[str, int]
    missing_classes: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "images": self.images,
            "boxes": self.boxes,
            "images_without_boxes": self.images_without_boxes,
            "per_class_boxes": dict(sorted(self.per_class_boxes.items())),
            "per_class_images": dict(sorted(self.per_class_images.items())),
            "missing_classes": list(self.missing_classes),
        }


def parse_yolo_label(
    path: Path,
    *,
    class_names: tuple[str, ...],
) -> tuple[BoxAnnotation, ...]:
    """Parse and validate one YOLO label file.

    Raises ``DatasetError`` with the file name, line number and reason. Nothing
    is clamped or dropped.
    """
    path = Path(path)
    if not path.is_file():
        raise DatasetError(f"label not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DatasetError(f"cannot read label {path}: {exc}") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise DatasetError(f"label {path.name} is empty; empty labels are quarantined")
    boxes: list[BoxAnnotation] = []
    seen: set[tuple[int, float, float, float, float]] = set()
    for number, line in enumerate(lines, start=1):
        fields = line.split()
        if len(fields) != _YOLO_FIELDS:
            raise DatasetError(
                f"{path.name}:{number}: expected {_YOLO_FIELDS} fields, "
                f"got {len(fields)}"
            )
        try:
            class_id = int(fields[0])
        except ValueError as exc:
            raise DatasetError(
                f"{path.name}:{number}: class id is not an integer"
            ) from exc
        if not 0 <= class_id < len(class_names):
            raise DatasetError(
                f"{path.name}:{number}: class id {class_id} is outside "
                f"[0, {len(class_names) - 1}]"
            )
        values = tuple(float(value) for value in fields[1:])
        box = BoxAnnotation(
            class_id=class_id,
            cx=values[0],
            cy=values[1],
            width=values[2],
            height=values[3],
        )
        key = (box.class_id, box.cx, box.cy, box.width, box.height)
        if key in seen:
            raise DatasetError(f"{path.name}:{number}: duplicate box")
        seen.add(key)
        boxes.append(box)
    return tuple(boxes)


def _read_image_size(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise DatasetError(f"image not found: {path}")
    try:
        with Image.open(path) as opened:
            width, height = opened.size
    except (OSError, UnidentifiedImageError) as exc:
        raise DatasetError(f"cannot read image {path}: {exc}") from exc
    if width < 1 or height < 1:
        raise DatasetError(f"image {path} has a non-positive size")
    return (int(width), int(height))


class CuratedDataset:
    """Immutable, deterministic view of the curated dataset."""

    def __init__(
        self,
        manifest: SplitManifest,
        *,
        images: tuple[DatasetImage, ...],
        excluded: tuple[str, ...],
        folds: tuple[LogoFold, ...],
        manifest_sha256: str,
    ) -> None:
        if not images:
            raise DatasetError("the curated dataset contains no images")
        self.manifest = manifest
        self.images = images
        self.excluded = excluded
        self.folds = folds
        self.manifest_sha256 = manifest_sha256
        self.class_names = tuple(manifest.class_names)
        if not self.class_names:
            raise DatasetError("the manifest declares no class names")

    @classmethod
    def load(
        cls,
        manifest_path: str | Path | None = None,
        *,
        dataset_root: str | Path | None = None,
        verify_images: bool = True,
        repo_root: str | Path | None = None,
    ) -> "CuratedDataset":
        manifest = SplitManifest.load(manifest_path, repo_root=repo_root)
        root = (
            Path(dataset_root).resolve()
            if dataset_root is not None
            else manifest.dataset_root_path
        )
        if not root.is_dir():
            raise DatasetError(f"dataset root not found: {root}")
        class_names = tuple(manifest.class_names)
        if not class_names:
            raise DatasetError("the manifest declares no class names")

        included: list[DatasetImage] = []
        excluded: list[str] = []
        for split in ("train", "valid"):
            for image_path in sorted((root / split / "images").glob("*")):
                if not image_path.is_file():
                    continue
                assignment = manifest.resolve(image_path)
                if assignment.excluded:
                    excluded.append(assignment.path)
                    continue
                label_path = root / split / "labels" / f"{image_path.stem}.txt"
                boxes = parse_yolo_label(label_path, class_names=class_names)
                size = _read_image_size(image_path) if verify_images else (0, 0)
                included.append(
                    DatasetImage(
                        path=image_path,
                        relative_path=assignment.path,
                        label_path=label_path,
                        group=assignment.group,
                        split=assignment.split,
                        image_size=size,
                        boxes=boxes,
                    )
                )

        if not included:
            raise DatasetError("no included images were found")

        fold_payloads = manifest.payload.get("logo_folds")
        if not isinstance(fold_payloads, list) or not fold_payloads:
            raise DatasetError("the manifest declares no LOGO folds")
        folds: list[LogoFold] = []
        for payload in fold_payloads:
            if not isinstance(payload, Mapping):
                raise DatasetError("each LOGO fold must be an object")
            valid_group = str(payload.get("valid_group", ""))
            train_groups = tuple(str(value) for value in payload.get("train_groups", ()))
            if not valid_group or not train_groups:
                raise DatasetError("a LOGO fold must define valid and train groups")
            if valid_group in train_groups:
                raise DatasetError(
                    f"LOGO fold {payload.get('fold')} uses {valid_group!r} in both splits"
                )
            fold_images = tuple(image for image in included if image.group == valid_group)
            train_images = tuple(image for image in included if image.group in train_groups)
            other = {
                image.group
                for image in included
                if image.group != valid_group and image.group not in train_groups
            }
            if other:
                raise DatasetError(
                    f"LOGO fold {payload.get('fold')} leaves groups unassigned: "
                    f"{sorted(other)}"
                )
            folds.append(
                LogoFold(
                    fold=int(payload.get("fold", len(folds) + 1)),
                    valid_group=valid_group,
                    train_groups=train_groups,
                    train_images=train_images,
                    valid_images=fold_images,
                )
            )

        assignment_payload = manifest.payload.get("fixed_split", {}).get("assignments")
        if isinstance(assignment_payload, Mapping):
            for image in included:
                expected = assignment_payload.get(image.relative_path)
                if expected is not None and expected != image.split:
                    raise DatasetError(
                        f"manifest split mismatch for {image.relative_path}: "
                        f"{image.split} != {expected}"
                    )

        digest = hashlib.sha256(Path(manifest.source_path).read_bytes()).hexdigest()
        return cls(
            manifest,
            images=tuple(included),
            excluded=tuple(excluded),
            folds=tuple(folds),
            manifest_sha256=digest,
        )

    def for_split(self, split: str) -> tuple[DatasetImage, ...]:
        if split not in ("train", "valid"):
            raise DatasetError("split must be 'train' or 'valid'")
        return tuple(image for image in self.images if image.split == split)

    def for_fold(self, fold: int) -> LogoFold:
        for candidate in self.folds:
            if candidate.fold == fold:
                return candidate
        raise DatasetError(f"unknown LOGO fold {fold}")

    def statistics(self, images: Iterable[DatasetImage], name: str) -> SplitStatistics:
        selection = tuple(images)
        per_class_boxes = {class_name: 0 for class_name in self.class_names}
        per_class_images = {class_name: 0 for class_name in self.class_names}
        without_boxes = 0
        for image in selection:
            counts = image.class_counts()
            if not counts:
                without_boxes += 1
            for class_id, count in counts.items():
                class_name = self.class_names[class_id]
                per_class_boxes[class_name] += count
                per_class_images[class_name] += 1
        missing = tuple(
            class_name
            for class_name, count in per_class_boxes.items()
            if count == 0
        )
        return SplitStatistics(
            name=name,
            images=len(selection),
            boxes=sum(image.n_boxes for image in selection),
            images_without_boxes=without_boxes,
            per_class_boxes=per_class_boxes,
            per_class_images=per_class_images,
            missing_classes=missing,
        )

    def split_statistics(self, split: str) -> SplitStatistics:
        return self.statistics(self.for_split(split), split)

    def fold_statistics(self, fold: int) -> dict:
        view = self.for_fold(fold)
        return {
            "fold": view.fold,
            "valid_group": view.valid_group,
            "train": self.statistics(view.train_images, f"fold_{view.fold}_train").as_dict(),
            "valid": self.statistics(view.valid_images, f"fold_{view.fold}_valid").as_dict(),
        }

    def describe(self) -> dict:
        dataset = self.manifest.payload.get("dataset", {})
        return {
            "dataset_root": str(self.manifest.dataset_root_path),
            "manifest": str(self.manifest.source_path),
            "manifest_sha256": self.manifest_sha256,
            "class_names": list(self.class_names),
            "n_images": len(self.images),
            "n_boxes": sum(image.n_boxes for image in self.images),
            "n_excluded": len(self.excluded),
            "groups": sorted({image.group for image in self.images}),
            "fixed_split": {
                "train_groups": list(self.manifest.train_groups),
                "valid_groups": list(self.manifest.valid_groups),
            },
            "logo_folds": [fold.as_dict() for fold in self.folds],
            "attribution": {
                "version": dataset.get("version"),
                "requested_path": dataset.get("requested_path"),
                "discovered_root": dataset.get("discovered_root"),
                "policy": self.manifest.payload.get("policy"),
                "limitations": self.manifest.payload.get("limitations", []),
            },
            "split_source": "curation_manifest_filename_groups",
            "dataset_modified": False,
        }
