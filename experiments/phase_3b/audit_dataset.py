#!/usr/bin/env python3
"""Read-only forensic audit of the local Subway Surfers YOLOv8 dataset.

Phase 3B.0. The script never writes into the dataset directory: it opens
images read-only, stores per-image metadata only, verifies each image and
decodes it one at a time. Previews, JSON and any report assets go to separate
output directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    import yaml
except ImportError:  # pragma: no cover - reported instead of installing
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = (
    PROJECT_ROOT
    / "datasets"
    / "external"
    / "subway surfers"
    / "roboflow_v15_yolov8"
)
DEFAULT_OUTDIR = PROJECT_ROOT / "experiments" / "phase_3b"
DEFAULT_JSON = PROJECT_ROOT / "reports" / "PHASE_3B0_DATASET_AUDIT.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
CLASS_PALETTE = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
    "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def describe_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    count = len(ordered)

    def percentile(fraction: float) -> float:
        if count == 1:
            return float(ordered[0])
        position = fraction * (count - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return float(ordered[lower])
        weight = position - lower
        return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)

    return {
        "count": count,
        "min": round(float(ordered[0]), 6),
        "p01": round(percentile(0.01), 6),
        "p05": round(percentile(0.05), 6),
        "p25": round(percentile(0.25), 6),
        "p50": round(percentile(0.50), 6),
        "p75": round(percentile(0.75), 6),
        "p95": round(percentile(0.95), 6),
        "p99": round(percentile(0.99), 6),
        "max": round(float(ordered[-1]), 6),
        "mean": round(float(statistics.fmean(ordered)), 6),
        "std": round(float(statistics.pstdev(ordered)), 6),
    }


def discover_layout(dataset_dir: Path) -> dict:
    """Find the directory that actually contains split subdirectories."""
    if not dataset_dir.exists():
        raise SystemExit(f"dataset path does not exist: {dataset_dir}")
    candidates = [dataset_dir]
    candidates += [path for path in sorted(dataset_dir.iterdir()) if path.is_dir()]
    roots = []
    for candidate in candidates:
        splits = {
            path.name
            for path in candidate.iterdir()
            if path.is_dir() and (path / "images").is_dir()
        }
        if splits:
            roots.append((candidate, sorted(splits)))
    if not roots:
        raise SystemExit(f"no YOLO split directory found under {dataset_dir}")
    if len(roots) > 1:
        raise SystemExit(f"ambiguous dataset roots: {roots}")
    root, splits = roots[0]
    notes = []
    if root != dataset_dir:
        notes.append(
            f"requested directory contains a nested dataset root named {root.name!r}"
        )
    return {"row": root, "splits": splits, "notes": notes}


def find_metadata_files(root: Path) -> list[Path]:
    patterns = ("*.yaml", "*.yml", "*.json", "README*", "*.txt")
    found = []
    for pattern in patterns:
        found.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(found), key=lambda path: path.name.lower())


def load_declared_classes(root: Path) -> dict:
    yaml_paths = [
        path
        for path in sorted(root.glob("*"))
        if path.suffix.lower() in {".yaml", ".yml"}
    ]
    if not yaml_paths:
        return {
            "present": False,
            "paths": [],
            "names": None,
            "payload": None,
            "error": "no data.yaml or other YAML file found in the dataset root",
        }
    path = yaml_paths[0]
    if yaml is None:
        return {
            "present": True,
            "paths": [str(path.relative_to(root))],
            "names": None,
            "payload": None,
            "error": "PyYAML is not installed, so the YAML could not be parsed",
        }
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - recorded, not repaired
        return {
            "present": True,
            "paths": [str(path.relative_to(root))],
            "names": None,
            "payload": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    names = payload.get("names") if isinstance(payload, dict) else None
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=lambda value: int(value))]
    elif isinstance(names, list):
        names = [str(name) for name in names]
    else:
        names = None
    return {
        "present": True,
        "paths": [str(path.relative_to(root))],
        "names": names,
        "payload": payload,
        "error": None,
    }


def parse_label_file(path: Path) -> dict:
    objects = []
    errors = []
    blank_lines = 0
    duplicates = []
    seen = set()
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            blank_lines += 1
            continue
        fields = line.split()
        if len(fields) != 5:
            errors.append(
                {
                    "line": line_number,
                    "reason": "expected 5 fields",
                    "content": raw[:160],
                }
            )
            continue
        class_field, *coordinate_fields = fields
        try:
            class_id = int(class_field)
        except ValueError:
            errors.append(
                {
                    "line": line_number,
                    "reason": "class id is not an integer",
                    "content": raw[:160],
                }
            )
            continue
        try:
            x_center, y_center, width, height = (
                float(value) for value in coordinate_fields
            )
        except ValueError:
            errors.append(
                {
                    "line": line_number,
                    "reason": "coordinate is not numeric",
                    "content": raw[:160],
                }
            )
            continue
        non_finite = not all(
            math.isfinite(value)
            for value in (x_center, y_center, width, height)
        )
        out_of_range = (
            non_finite
            or not (0.0 <= x_center <= 1.0)
            or not (0.0 <= y_center <= 1.0)
            or not (0.0 < width <= 1.0)
            or not (0.0 < height <= 1.0)
        )
        box_outside = (
            not non_finite
            and (
                x_center - width / 2.0 < -1e-9
                or x_center + width / 2.0 > 1.0 + 1e-9
                or y_center - height / 2.0 < -1e-9
                or y_center + height / 2.0 > 1.0 + 1e-9
            )
        )
        record = {
            "line": line_number,
            "class_id": class_id,
            "x": x_center,
            "y": y_center,
            "w": width,
            "h": height,
            "non_finite": non_finite,
            "out_of_range": out_of_range,
            "box_outside": box_outside,
        }
        key = (class_id, x_center, y_center, width, height)
        if key in seen:
            duplicates.append({"line": line_number, "record": record})
        seen.add(key)
        objects.append(record)
    return {
        "objects": objects,
        "errors": errors,
        "blank_lines": blank_lines,
        "duplicate_lines": duplicates,
    }


def sequence_name(name: str) -> str:
    return name.split("_jpg.rf.")[0].split("_mp4-")[0]


def frame_number(name: str) -> int | None:
    marker = "_mp4-"
    if marker not in name:
        return None
    tail = name.split(marker, 1)[1]
    digits = ""
    for character in tail:
        if character.isdigit():
            digits += character
        else:
            break
    return int(digits) if digits else None


def dhash_64(image: Image.Image) -> int:
    gray = image.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
    pixels = list(gray.getdata())
    value = 0
    bit = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            if pixels[offset + column] > pixels[offset + column + 1]:
                value |= 1 << bit
            bit += 1
    return value


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def box_iou(left: dict, right: dict) -> float:
    left_x0 = left["x"] - left["w"] / 2.0
    left_y0 = left["y"] - left["h"] / 2.0
    left_x1 = left["x"] + left["w"] / 2.0
    left_y1 = left["y"] + left["h"] / 2.0
    right_x0 = right["x"] - right["w"] / 2.0
    right_y0 = right["y"] - right["h"] / 2.0
    right_x1 = right["x"] + right["w"] / 2.0
    right_y1 = right["y"] + right["h"] / 2.0
    inter_width = max(0.0, min(left_x1, right_x1) - max(left_x0, right_x0))
    inter_height = max(0.0, min(left_y1, right_y1) - max(left_y0, right_y0))
    intersection = inter_width * inter_height
    union = left["w"] * left["h"] + right["w"] * right["h"] - intersection
    return intersection / union if union > 0 else 0.0


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            result[order[index]] = average
        position = end + 1
    return result


def correlation(left: list[float], right: list[float], *, rank: bool) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    x = ranks(left) if rank else left
    y = ranks(right) if rank else right
    x_mean = statistics.fmean(x)
    y_mean = statistics.fmean(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    x_var = sum((a - x_mean) ** 2 for a in x)
    y_var = sum((b - y_mean) ** 2 for b in y)
    denominator = math.sqrt(x_var * y_var)
    return round(numerator / denominator, 6) if denominator > 0 else None


def histogram(values: list[float], bins: int, minimum: float, maximum: float) -> dict:
    counts = [0] * bins
    if not values:
        return {"bins": [], "counts": counts}
    width = (maximum - minimum) / bins
    for value in values:
        index = int((value - minimum) / width)
        index = min(max(index, 0), bins - 1)
        counts[index] += 1
    edges = [round(minimum + index * width, 3) for index in range(bins + 1)]
    return {"bins": edges, "counts": counts}


def render_previews(
    records: list[dict],
    root: Path,
    preview_dir: Path,
    per_split: int,
    seed: int,
    max_width: int,
) -> list[dict]:
    preview_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    created = []
    by_split: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record["label_objects"]:
            by_split[record["split"]].append(record)
    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover - Pillow fallback
        font = None
    for split, rows in sorted(by_split.items()):
        chosen = []
        chosen.append(max(rows, key=lambda row: len(row["objects"])))
        chosen.append(min(rows, key=lambda row: len(row["objects"])))
        chosen.append(
            max(rows, key=lambda row: sum(obj["w"] * obj["h"] for obj in row["objects"]))
        )
        chosen.append(
            min(rows, key=lambda row: sum(obj["w"] * obj["h"] for obj in row["objects"]))
        )
        remaining = [row for row in rows if row not in chosen]
        rng.shuffle(remaining)
        chosen.extend(remaining[: max(0, per_split - len(chosen))])
        unique = []
        for row in chosen:
            if row not in unique:
                unique.append(row)
        for index, row in enumerate(unique, start=1):
            image_path = root / row["relative_path"]
            with Image.open(image_path) as source:
                image = source.convert("RGB")
            width, height = image.size
            scale = min(1.0, max_width / max(1, width))
            if scale < 1.0:
                image = image.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )
            draw = ImageDraw.Draw(image)
            draw_width = max(1, int(round(min(image.size) / 180)))
            for obj in row["objects"]:
                color = CLASS_PALETTE[obj["class_id"] % len(CLASS_PALETTE)]
                x0 = (obj["x"] - obj["w"] / 2.0) * image.size[0]
                y0 = (obj["y"] - obj["h"] / 2.0) * image.size[1]
                x1 = (obj["x"] + obj["w"] / 2.0) * image.size[0]
                y1 = (obj["y"] + obj["h"] / 2.0) * image.size[1]
                draw.rectangle([x0, y0, x1, y1], outline=color, width=draw_width)
                label = f"c{obj['class_id']}"
                if font is not None:
                    text_box = draw.textbbox((x0, y0), label, font=font)
                    draw.rectangle(
                        [x0, y0 - (text_box[3] - text_box[1]) - 3, x0 + (text_box[2] - text_box[0]) + 4, y0],
                        fill=color,
                    )
                    draw.text((x0 + 2, y0 - (text_box[3] - text_box[1]) - 2), label, fill="#ffffff", font=font)
            target = preview_dir / f"{split}_{index:02d}_{Path(row['relative_path']).stem}.jpg"
            image.save(target, quality=85)
            created.append(
                {
                    "split": split,
                    "source": row["relative_path"],
                    "objects": len(row["objects"]),
                    "preview": str(target.relative_to(PROJECT_ROOT)),
                }
            )
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--previews",
        type=Path,
        default=None,
        help="preview directory (default: <outdir>/previews)",
    )
    parser.add_argument("--phase", default="3B.0")
    parser.add_argument("--preview-count", type=int, default=6)
    parser.add_argument("--preview-width", type=int, default=420)
    parser.add_argument("--near-threshold", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--skip-previews", action="store_true")
    args = parser.parse_args(argv)

    dataset_dir = args.dataset.resolve()
    outdir = args.outdir.resolve()
    json_path = args.json.resolve()
    preview_dir = (
        args.previews.resolve() if args.previews is not None else outdir / "previews"
    )
    if outdir == dataset_dir or dataset_dir in outdir.parents:
        raise SystemExit("output directory must not be inside the dataset")
    if json_path == dataset_dir or dataset_dir in json_path.parents:
        raise SystemExit("JSON output must not be inside the dataset")
    if preview_dir == dataset_dir or dataset_dir in preview_dir.parents:
        raise SystemExit("preview directory must not be inside the dataset")

    layout = discover_layout(dataset_dir)
    root = layout["row"]
    metadata_files = find_metadata_files(root)
    declared = load_declared_classes(root)

    records: list[dict] = []
    label_files: dict[Path, tuple[str, str]] = {}
    image_stems: dict[str, set[str]] = defaultdict(set)
    image_extensions = Counter()
    label_extension_counts = Counter()
    file_sizes = []
    warnings = []

    for split in layout["splits"]:
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        if not labels_dir.is_dir():
            warnings.append(f"split {split!r} has no labels directory")
        for label_path in sorted(labels_dir.glob("*.txt")) if labels_dir.is_dir() else []:
            label_extension_counts[label_path.suffix.lower()] += 1
        for image_path in sorted(images_dir.iterdir()):
            if not image_path.is_file():
                continue
            extension = image_path.suffix.lower()
            image_extensions[extension] += 1
            if extension not in IMAGE_EXTENSIONS:
                warnings.append(f"unexpected image extension: {image_path}")
                continue
            image_stems[split].add(image_path.stem)
            relative = str(image_path.relative_to(root))
            label_path = labels_dir / f"{image_path.stem}.txt"
            parsed = None
            if label_path.is_file():
                parsed = parse_label_file(label_path)
                label_files[label_path] = (split, relative)
            image_error = None
            width = height = None
            mode = None
            image_format = None
            try:
                with Image.open(image_path) as image:
                    width, height = image.size
                    mode = image.mode
                    image_format = image.format
                    image.verify()
                with Image.open(image_path) as image:
                    phash = dhash_64(image)
            except Exception as exc:  # noqa: BLE001 - recorded, not repaired
                image_error = f"{type(exc).__name__}: {exc}"
                phash = None
            records.append(
                {
                    "split": split,
                    "relative_path": relative,
                    "stem": image_path.stem,
                    "file_size": image_path.stat().st_size,
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "format": image_format,
                    "sha256": sha256_file(image_path),
                    "dhash": phash,
                    "image_error": image_error,
                    "label_relative_path": (
                        str(label_path.relative_to(root)) if label_path.is_file() else None
                    ),
                    "label_exists": parsed is not None,
                    "label_empty": parsed is not None and not parsed["objects"],
                    "label_error_count": len(parsed["errors"]) if parsed else 0,
                    "label_errors": parsed["errors"] if parsed else [],
                    "label_duplicate_count": len(parsed["duplicate_lines"]) if parsed else 0,
                    "label_duplicate_lines": parsed["duplicate_lines"] if parsed else [],
                    "label_blank_lines": parsed["blank_lines"] if parsed else 0,
                    "objects": parsed["objects"] if parsed else [],
                    "label_objects": len(parsed["objects"]) if parsed else 0,
                    "frame": frame_number(image_path.name),
                }
            )
            file_sizes.append(image_path.stat().st_size)

    orphan_labels = []
    for split in layout["splits"]:
        labels_dir = root / split / "labels"
        if not labels_dir.is_dir():
            continue
        for label_path in sorted(labels_dir.glob("*.txt")):
            if label_path.stem not in image_stems[split]:
                orphan_labels.append(
                    {"split": split, "label": str(label_path.relative_to(root))}
                )
    all_files = [path for path in root.rglob("*") if path.is_file()]
    extension_counts = Counter(path.suffix.lower() or "<none>" for path in all_files)
    total_bytes = sum(path.stat().st_size for path in all_files)

    class_counts = Counter()
    class_counts_by_split: dict[str, Counter] = defaultdict(Counter)
    widths = []
    heights = []
    areas = []
    objects_per_image = Counter()
    center_x = []
    center_y = []
    bottom_edges = []
    observed_class_ids = set()
    images_with_objects = 0
    images_without_objects = 0
    multi_object_images = 0
    for record in records:
        count = record["label_objects"]
        objects_per_image[count] += 1
        if count:
            images_with_objects += 1
            if count > 1:
                multi_object_images += 1
        else:
            images_without_objects += 1
        for obj in record["objects"]:
            observed_class_ids.add(obj["class_id"])
            class_counts[obj["class_id"]] += 1
            class_counts_by_split[record["split"]][obj["class_id"]] += 1
            widths.append(obj["w"])
            heights.append(obj["h"])
            areas.append(obj["w"] * obj["h"])
            center_x.append(obj["x"])
            center_y.append(obj["y"])
            bottom_edges.append(obj["y"] + obj["h"] / 2.0)

    dimensions = Counter(
        (record["width"], record["height"])
        for record in records
        if record["width"] is not None
    )
    formats = Counter(record["format"] for record in records if record["format"])
    modes = Counter(record["mode"] for record in records if record["mode"])
    corrupt = [
        {"path": record["relative_path"], "error": record["image_error"]}
        for record in records
        if record["image_error"]
    ]

    image_hashes = defaultdict(list)
    label_hashes = defaultdict(list)
    for record in records:
        image_hashes[record["sha256"]].append(record)
        if record["label_relative_path"]:
            label_path = root / record["label_relative_path"]
            label_hashes[sha256_file(label_path)].append(record)
    exact_image_groups = [
        group for group in image_hashes.values() if len(group) > 1
    ]
    exact_label_groups = [
        group for group in label_hashes.values() if len(group) > 1
    ]
    exact_cross_split = [
        group
        for group in exact_image_groups
        if len({record["split"] for record in group}) > 1
    ]

    hashed = [record for record in records if record["dhash"] is not None]
    near_pairs = []
    for left_index in range(len(hashed)):
        left = hashed[left_index]
        for right_index in range(left_index + 1, len(hashed)):
            right = hashed[right_index]
            distance = hamming(left["dhash"], right["dhash"])
            if distance <= args.near_threshold:
                near_pairs.append(
                    {
                        "distance": distance,
                        "left_split": left["split"],
                        "left": left["relative_path"],
                        "right_split": right["split"],
                        "right": right["relative_path"],
                        "left_frame": left["frame"],
                        "right_frame": right["frame"],
                        "cross_split": left["split"] != right["split"],
                        "same_sequence": (
                            sequence_name(left["stem"]) == sequence_name(right["stem"])
                        ),
                        "frame_gap": (
                            abs(left["frame"] - right["frame"])
                            if left["frame"] is not None
                            and right["frame"] is not None
                            and sequence_name(left["stem"]) == sequence_name(right["stem"])
                            else None
                        ),
                    }
                )
    near_pairs.sort(key=lambda pair: (pair["distance"], pair["left"], pair["right"]))
    near_cross_split = [pair for pair in near_pairs if pair["cross_split"]]
    near_cross_images = {
        (split, path)
        for pair in near_cross_split
        for split, path in (
            (pair["left_split"], pair["left"]),
            (pair["right_split"], pair["right"]),
        )
    }
    near_adjacent_cross_split = [
        pair
        for pair in near_cross_split
        if pair["frame_gap"] is not None and pair["frame_gap"] <= 5
    ]

    frame_ranges = {}
    for split in layout["splits"]:
        frames = [
            record["frame"]
            for record in records
            if record["split"] == split and record["frame"] is not None
        ]
        if frames:
            frame_ranges[split] = {
                "min": min(frames),
                "max": max(frames),
                "count": len(frames),
            }
    frames_by_sequence: dict[str, dict[int, str]] = defaultdict(dict)
    for record in records:
        if record["frame"] is not None:
            frames_by_sequence[sequence_name(record["stem"])][record["frame"]] = record[
                "split"
            ]
    adjacent_present = [
        (sequence, frame, frame + 1, mapping[frame], mapping[frame + 1])
        for sequence, mapping in sorted(frames_by_sequence.items())
        for frame in sorted(mapping)
        if frame + 1 in mapping
    ]
    adjacent_cross_split = [
        pair for pair in adjacent_present if pair[3] != pair[4]
    ]
    frame_ranges_by_sequence = {
        sequence: {
            "min": min(mapping),
            "max": max(mapping),
            "count": len(mapping),
            "splits": sorted(set(mapping.values())),
        }
        for sequence, mapping in sorted(frames_by_sequence.items())
    }
    sequences = Counter(sequence_name(record["stem"]) for record in records)

    class_rows = []
    for class_id in sorted(observed_class_ids):
        name = None
        if declared["names"] and 0 <= class_id < len(declared["names"]):
            name = declared["names"][class_id]
        class_rows.append(
            {
                "class_id": class_id,
                "declared_name": name,
                "objects": class_counts[class_id],
                "images": sum(
                    1
                    for record in records
                    if any(obj["class_id"] == class_id for obj in record["objects"])
                ),
                "per_split": {
                    split: class_counts_by_split[split][class_id]
                    for split in layout["splits"]
                },
            }
        )
    total_objects = sum(class_counts.values())
    imbalance = {
        "total_objects": total_objects,
        "n_classes_observed": len(observed_class_ids),
        "largest_class_objects": max(class_counts.values()) if class_counts else 0,
        "smallest_class_objects": min(class_counts.values()) if class_counts else 0,
        "max_min_ratio": (
            round(max(class_counts.values()) / min(class_counts.values()), 4)
            if class_counts and min(class_counts.values()) > 0
            else None
        ),
    }

    previews = []
    if not args.skip_previews:
        previews = render_previews(
            records,
            root,
            preview_dir,
            args.preview_count,
            args.seed,
            args.preview_width,
        )

    overlap_pairs = []
    for record in records:
        objects = record["objects"]
        for left_index in range(len(objects)):
            for right_index in range(left_index + 1, len(objects)):
                iou = box_iou(objects[left_index], objects[right_index])
                if iou < 0.5:
                    continue
                overlap_pairs.append(
                    {
                        "image": record["relative_path"],
                        "left_line": objects[left_index]["line"],
                        "right_line": objects[right_index]["line"],
                        "left_class": objects[left_index]["class_id"],
                        "right_class": objects[right_index]["class_id"],
                        "same_class": (
                            objects[left_index]["class_id"]
                            == objects[right_index]["class_id"]
                        ),
                        "iou": round(iou, 6),
                    }
                )
    overlap_pairs.sort(key=lambda pair: pair["iou"], reverse=True)
    near_identical = [pair for pair in overlap_pairs if pair["iou"] >= 0.8]
    geometry = {
        "area_vs_center_y_pearson": correlation(areas, center_y, rank=False),
        "area_vs_center_y_spearman": correlation(areas, center_y, rank=True),
        "area_vs_bottom_edge_spearman": correlation(
            areas, bottom_edges, rank=True
        ),
        "near_field_center_x_histogram": histogram(
            [
                obj["x"]
                for record in records
                for obj in record["objects"]
                if obj["y"] >= 0.6
            ],
            10,
            0.0,
            1.0,
        ),
    }

    zip_candidates = sorted(dataset_dir.glob("*.zip"))
    zip_info = []
    for zip_path in zip_candidates:
        info = {
            "path": str(zip_path.relative_to(PROJECT_ROOT)),
            "bytes": zip_path.stat().st_size,
            "sha256": sha256_file(zip_path),
            "entries": None,
            "integrity": "not tested",
        }
        try:
            with zipfile.ZipFile(zip_path) as archive:
                info["entries"] = len(archive.namelist())
                bad = archive.testzip()
                info["integrity"] = "ok" if bad is None else f"corrupt entry: {bad}"
        except Exception as exc:  # noqa: BLE001 - recorded
            info["integrity"] = f"{type(exc).__name__}: {exc}"
        zip_info.append(info)

    split_counts = {
        split: {
            "images": sum(1 for record in records if record["split"] == split),
            "labels": sum(
                1
                for record in records
                if record["split"] == split and record["label_exists"]
            ),
            "objects": sum(
                record["label_objects"]
                for record in records
                if record["split"] == split
            ),
            "images_missing_labels": sum(
                1
                for record in records
                if record["split"] == split and not record["label_exists"]
            ),
        }
        for split in layout["splits"]
    }

    annot_errors = [
        {
            "image": record["relative_path"],
            "line": error["line"],
            "reason": error["reason"],
            "content": error["content"],
        }
        for record in records
        for error in record["label_errors"]
    ]
    duplicate_annotation_lines = [
        {
            "image": record["relative_path"],
            "line": duplicate["line"],
            "class_id": duplicate["record"]["class_id"],
        }
        for record in records
        for duplicate in record["label_duplicate_lines"]
    ]
    out_of_range_objects = [
        {
            "image": record["relative_path"],
            "line": obj["line"],
            "class_id": obj["class_id"],
            "x": obj["x"],
            "y": obj["y"],
            "w": obj["w"],
            "h": obj["h"],
        }
        for record in records
        for obj in record["objects"]
        if obj["out_of_range"]
    ]
    outside_image_boxes = [
        {
            "image": record["relative_path"],
            "line": obj["line"],
            "class_id": obj["class_id"],
            "box": [obj["x"], obj["y"], obj["w"], obj["h"]],
        }
        for record in records
        for obj in record["objects"]
        if obj["box_outside"]
    ]
    undeclared_class_objects = []
    if declared["names"]:
        undeclared_class_objects = [
            {
                "image": record["relative_path"],
                "line": obj["line"],
                "class_id": obj["class_id"],
            }
            for record in records
            for obj in record["objects"]
            if not 0 <= obj["class_id"] < len(declared["names"])
        ]

    payload = {
        "phase": args.phase,
        "generated_at_utc": utc_now(),
        "command": " ".join([Path(sys.executable).name, *sys.argv]),
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "pillow": Image.__version__,
            "pyyaml": getattr(yaml, "__version__", None) if yaml else None,
        },
        "dataset": {
            "requested_path": str(dataset_dir.relative_to(PROJECT_ROOT)),
            "discovered_root": str(root.relative_to(PROJECT_ROOT)),
            "layout_notes": layout["notes"],
            "folder_bytes": total_bytes,
            "disk": {
                "total": shutil.disk_usage(dataset_dir).total,
                "used": shutil.disk_usage(dataset_dir).used,
                "free": shutil.disk_usage(dataset_dir).free,
            },
            "zip": zip_info,
        },
        "metadata": {
            "files": [str(path.relative_to(root)) for path in metadata_files],
            "data_yaml": declared,
            "declared_split_paths": (
                {
                    key: declared["payload"].get(key)
                    for key in ("train", "val", "test")
                    if isinstance(declared["payload"], dict)
                }
                if isinstance(declared["payload"], dict)
                else {}
            ),
            "present_splits": layout["splits"],
        },
        "inventory": {
            "file_count": len(all_files),
            "image_count": len(records),
            "label_file_count": sum(label_extension_counts.values()),
            "extension_counts": dict(sorted(extension_counts.items())),
            "image_extension_counts": dict(sorted(image_extensions.items())),
            "label_extension_counts": dict(sorted(label_extension_counts.items())),
            "total_bytes": total_bytes,
            "image_bytes": sum(file_sizes),
            "split_counts": split_counts,
        },
        "images": {
            "dimensions": [
                {"width": width, "height": height, "count": count}
                for (width, height), count in dimensions.most_common()
            ],
            "formats": dict(formats),
            "modes": dict(modes),
            "corrupt": corrupt,
            "size_bytes": describe_stats([float(value) for value in file_sizes]),
        },
        "classes": {
            "declared_names": declared["names"],
            "declared_count": len(declared["names"]) if declared["names"] else None,
            "observed_ids": sorted(observed_class_ids),
            "observed_min": min(observed_class_ids) if observed_class_ids else None,
            "observed_max": max(observed_class_ids) if observed_class_ids else None,
            "rows": class_rows,
            "imbalance": imbalance,
            "undeclared_class_objects": undeclared_class_objects,
        },
        "annotations": {
            "object_count": total_objects,
            "empty_label_files": [
                record["relative_path"]
                for record in records
                if record["label_exists"] and record["label_empty"]
            ],
            "missing_label_files": [
                record["relative_path"]
                for record in records
                if not record["label_exists"]
            ],
            "orphan_label_files": orphan_labels,
            "malformed_lines": annot_errors,
            "duplicate_lines": duplicate_annotation_lines,
            "out_of_range_objects": out_of_range_objects,
            "boxes_outside_image": outside_image_boxes,
            "images_with_objects": images_with_objects,
            "images_without_objects": images_without_objects,
            "multi_object_images": multi_object_images,
        },
        "boxes": {
            "width": describe_stats(widths),
            "height": describe_stats(heights),
            "area": describe_stats(areas),
            "objects_per_image": [
                {"objects": count, "images": images}
                for count, images in sorted(objects_per_image.items())
            ],
        },
        "spatial": {
            "center_x_histogram": histogram(center_x, 10, 0.0, 1.0),
            "center_y_histogram": histogram(center_y, 10, 0.0, 1.0),
            "center_x": describe_stats(center_x),
            "center_y": describe_stats(center_y),
        },
        "duplicates": {
            "exact_image_groups": len(exact_image_groups),
            "exact_image_duplicate_images": sum(
                len(group) for group in exact_image_groups
            ),
            "exact_image_examples": [
                [
                    {"split": record["split"], "path": record["relative_path"]}
                    for record in group
                ]
                for group in exact_image_groups[:20]
            ],
            "exact_cross_split_groups": len(exact_cross_split),
            "exact_label_groups": len(exact_label_groups),
            "exact_label_duplicate_files": sum(
                len(group) for group in exact_label_groups
            ),
            "near_threshold": args.near_threshold,
            "near_pair_count": len(near_pairs),
            "near_cross_split_count": len(near_cross_split),
            "near_cross_split_adjacent_count": len(near_adjacent_cross_split),
            "near_cross_split_images_by_split": {
                split: sum(1 for item in near_cross_images if item[0] == split)
                for split in layout["splits"]
            },
            "near_pairs": near_pairs[:50],
        },
        "overlaps": {
            "pair_count_iou_ge_0p50": len(overlap_pairs),
            "pair_count_iou_ge_0p80": len(near_identical),
            "same_class_iou_ge_0p80": sum(
                1 for pair in near_identical if pair["same_class"]
            ),
            "different_class_iou_ge_0p80": sum(
                1 for pair in near_identical if not pair["same_class"]
            ),
            "images_with_iou_ge_0p80": len(
                {pair["image"] for pair in near_identical}
            ),
            "examples": overlap_pairs[:50],
        },
        "geometry": geometry,
        "sequence": {
            "video_sequences": dict(sequences),
            "frame_ranges": frame_ranges,
            "frame_ranges_by_sequence": frame_ranges_by_sequence,
            "all_frames": {
                "min": min(record["frame"] for record in records if record["frame"] is not None),
                "max": max(record["frame"] for record in records if record["frame"] is not None),
            },
            "adjacent_frame_pairs_total": len(adjacent_present),
            "adjacent_frame_pairs_cross_split": len(adjacent_cross_split),
            "adjacent_frame_cross_split_examples": [
                {
                    "sequence": sequence,
                    "left_frame": left,
                    "right_frame": right,
                    "left_split": left_split,
                    "right_split": right_split,
                }
                for sequence, left, right, left_split, right_split in adjacent_cross_split[:20]
            ],
        },
        "previews": previews,
        "warnings": warnings,
        "limitations": [
            "Class semantics are unresolved when data.yaml is absent; numeric IDs are reported without names.",
            "Bounding-box size is an image-space proxy and is not calibrated physical distance.",
            "Perceptual hashes detect visual similarity, not confirmed duplicate provenance.",
            "The audit does not train, evaluate or infer any detector.",
            "Frame ordering is inferred from filenames; no timestamp metadata is present.",
        ],
    }

    outdir.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"images={len(records)} labels={len(label_files)} objects={total_objects}")
    print(f"classes={sorted(observed_class_ids)} declared={declared['names']}")
    print(f"exact_duplicate_groups={len(exact_image_groups)} near_pairs={len(near_pairs)}")
    print(f"json={json_path}")
    if previews:
        print(f"previews={len(previews)} in {preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
