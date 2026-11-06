#!/usr/bin/env python3
"""Read-only Phase 3B.1 curation and grouped-split design for Subway Surfers v15.

The script never writes into the dataset. It reads image names and label files,
builds atomic source groups, inventories sequence structure, classifies empty
labels, checks class coverage, and emits a group-aware split manifest plus a
machine-readable curation report.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image

from audit_dataset import (
    PROJECT_ROOT,
    dhash_64,
    discover_layout,
    frame_number,
    hamming,
    parse_label_file,
    sequence_name,
    sha256_file,
    utc_now,
)

DEFAULT_DATASET = (
    PROJECT_ROOT
    / "datasets"
    / "external"
    / "subway surfers"
    / "roboflow_v15_yolov8"
)
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "phase_3b1_curation.yaml"
DEFAULT_JSON = PROJECT_ROOT / "reports" / "PHASE_3B1_DATASET_CURATION.json"
DEFAULT_MANIFEST = PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"config must be a mapping: {path}")
    return payload


def load_dataset_metadata(root: Path) -> tuple[list[str], int | None]:
    yaml_path = root / "data.yaml"
    if not yaml_path.is_file():
        raise SystemExit(f"data.yaml not found under {root}; class names are required")
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = payload.get("names") if isinstance(payload, dict) else None
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=lambda value: int(value))]
    if not isinstance(names, list) or not names:
        raise SystemExit("data.yaml does not declare a non-empty class list")
    roboflow = payload.get("roboflow", {}) if isinstance(payload, dict) else {}
    version = roboflow.get("version") if isinstance(roboflow, dict) else None
    return [str(name) for name in names], int(version) if version is not None else None


def collect_records(
    root: Path,
    splits: list[str],
    prefix_to_group: dict[str, str],
) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    warnings: list[str] = []
    for split in splits:
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        if not images_dir.is_dir():
            warnings.append(f"split {split!r} has no images directory")
            continue
        for image_path in sorted(images_dir.iterdir()):
            if not image_path.is_file():
                continue
            canonical = sequence_name(image_path.name)
            prefix = canonical.split("_mp4-")[0]
            group = prefix_to_group.get(prefix)
            if group is None:
                group = "ungrouped"
                warnings.append(f"unmapped prefix {prefix!r}: {image_path.name}")
            label_path = labels_dir / f"{image_path.stem}.txt"
            if label_path.is_file():
                parsed = parse_label_file(label_path)
                objects = len(parsed["objects"])
                class_counts = Counter(obj["class_id"] for obj in parsed["objects"])
                class_ids = sorted(class_counts)
                label_errors = len(parsed["errors"])
            else:
                objects = 0
                class_counts = Counter()
                class_ids = []
                label_errors = 0
                warnings.append(f"missing label file: {label_path}")
            records.append(
                {
                    "split": split,
                    "path": str(image_path.relative_to(root)).replace("\\", "/"),
                    "group": group,
                    "prefix": prefix,
                    "canonical_id": canonical,
                    "frame": frame_number(image_path.name),
                    "objects": objects,
                    "class_counts": dict(class_counts),
                    "class_ids": class_ids,
                    "label_errors": label_errors,
                }
            )
    return records, warnings


def group_inventory(records: list[dict]) -> dict:
    by_group: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_group[record["group"]].append(record)
    inventory = {}
    for group in sorted(by_group):
        rows = by_group[group]
        frames = sorted({row["frame"] for row in rows if row["frame"] is not None})
        gaps = [right - left for left, right in zip(frames, frames[1:])]
        runs = 1 if frames else 0
        longest = 1 if frames else 0
        current = 1
        for gap in gaps:
            if gap == 1:
                current += 1
                longest = max(longest, current)
            else:
                runs += 1
                current = 1
        frame_counts = Counter(row["frame"] for row in rows)
        duplicate_frames = {
            frame: count for frame, count in frame_counts.items() if count > 1
        }
        cross_split_same_id = 0
        for frame, count in duplicate_frames.items():
            splits = {row["split"] for row in rows if row["frame"] == frame}
            if count > 1 and len(splits) > 1:
                cross_split_same_id += 1
        inventory[group] = {
            "prefixes": sorted({row["prefix"] for row in rows}),
            "images": len(rows),
            "train_images": sum(1 for row in rows if row["split"] == "train"),
            "valid_images": sum(1 for row in rows if row["split"] == "valid"),
            "boxes": sum(row["objects"] for row in rows),
            "empty_labels": sum(1 for row in rows if row["objects"] == 0),
            "unique_frame_ids": len(frames),
            "duplicate_frame_ids": len(duplicate_frames),
            "extra_images_on_duplicate_ids": sum(
                count - 1 for count in duplicate_frames.values()
            ),
            "duplicate_id_pairs_cross_split": cross_split_same_id,
            "frame_min": min(frames) if frames else None,
            "frame_max": max(frames) if frames else None,
            "contiguous_runs": runs,
            "longest_contiguous_run": longest,
            "median_frame_gap": statistics.median(gaps) if gaps else None,
            "max_frame_gap": max(gaps) if gaps else None,
        }
    return inventory


def classify_empty_frames(records: list[dict], max_bracket_gap: int) -> list[dict]:
    by_group: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_group[record["group"]].append(record)
    results = []
    for group in sorted(by_group):
        rows = by_group[group]
        empty_frames = sorted({row["frame"] for row in rows if row["objects"] == 0})
        nonempty_objects: dict[int, int] = {}
        for row in rows:
            if row["objects"] > 0:
                nonempty_objects[row["frame"]] = max(
                    nonempty_objects.get(row["frame"], 0), row["objects"]
                )
        runs = []
        start = previous = None
        for frame in empty_frames:
            if start is None:
                start = previous = frame
            elif frame == previous + 1:
                previous = frame
            else:
                runs.append((start, previous))
                start = previous = frame
        if start is not None:
            runs.append((start, previous))
        run_of_frame = {}
        for run_start, run_end in runs:
            for frame in range(run_start, run_end + 1):
                run_of_frame[frame] = (run_start, run_end)
        for row in rows:
            if row["objects"] != 0:
                continue
            run_start, run_end = run_of_frame[row["frame"]]
            left = max(
                (
                    frame
                    for frame in nonempty_objects
                    if frame < run_start and run_start - frame <= max_bracket_gap
                ),
                default=None,
            )
            right = min(
                (
                    frame
                    for frame in nonempty_objects
                    if frame > run_end and frame - run_end <= max_bracket_gap
                ),
                default=None,
            )
            run_length = run_end - run_start + 1
            probable = (
                run_length >= 2 and left is not None and right is not None
            )
            results.append(
                {
                    "path": row["path"],
                    "group": group,
                    "split": row["split"],
                    "canonical_id": row["canonical_id"],
                    "frame": row["frame"],
                    "classification": (
                        "probable_gap" if probable else "isolated_plausible"
                    ),
                    "run_start": run_start,
                    "run_end": run_end,
                    "run_length": run_length,
                    "left_nonempty_frame": left,
                    "left_nonempty_objects": (
                        nonempty_objects[left] if left is not None else None
                    ),
                    "right_nonempty_frame": right,
                    "right_nonempty_objects": (
                        nonempty_objects[right] if right is not None else None
                    ),
                    "same_frame_labelled_copies": sum(
                        1
                        for other in rows
                        if other["frame"] == row["frame"] and other["objects"] > 0
                    ),
                }
            )
    results.sort(key=lambda item: (item["group"], item["frame"], item["path"]))
    return results


def measure_duplicate_id_similarity(records: list[dict], root: Path) -> dict:
    by_group_frame: dict[tuple[str, int], list[dict]] = defaultdict(list)
    frame_totals = Counter((row["group"], row["frame"]) for row in records)
    for row in records:
        if frame_totals[(row["group"], row["frame"])] > 1:
            by_group_frame[(row["group"], row["frame"])].append(row)

    results: dict[str, list[dict]] = defaultdict(list)
    for (group, frame), rows in sorted(by_group_frame.items()):
        hashes = []
        label_hashes = []
        for row in rows:
            with Image.open(root / row["path"]) as image:
                hashes.append(dhash_64(image))
            label_path = root / row["path"].replace("/images/", "/labels/")
            label_hashes.append(sha256_file(label_path.with_suffix(".txt")))
        for left in range(len(rows)):
            for right in range(left + 1, len(rows)):
                results[group].append(
                    {
                        "frame": frame,
                        "distance": hamming(hashes[left], hashes[right]),
                        "cross_split": rows[left]["split"] != rows[right]["split"],
                        "labels_identical": label_hashes[left] == label_hashes[right],
                    }
                )

    summary = {}
    for group, pairs in sorted(results.items()):
        distances = sorted(pair["distance"] for pair in pairs)
        summary[group] = {
            "pairs": len(pairs),
            "min_distance": distances[0],
            "p25_distance": distances[len(distances) // 4],
            "median_distance": statistics.median(distances),
            "p75_distance": distances[(3 * len(distances)) // 4],
            "max_distance": distances[-1],
            "distance_histogram_le_4": sum(1 for value in distances if value <= 4),
            "distance_histogram_5_to_8": sum(
                1 for value in distances if 5 <= value <= 8
            ),
            "distance_histogram_9_to_16": sum(
                1 for value in distances if 9 <= value <= 16
            ),
            "distance_over_16": sum(1 for value in distances if value > 16),
            "cross_split_pairs": sum(1 for pair in pairs if pair["cross_split"]),
            "label_identical_pairs": sum(
                1 for pair in pairs if pair["labels_identical"]
            ),
        }
    return summary


def class_coverage(records: list[dict], class_names: list[str]) -> dict:
    by_group: dict[str, dict] = {}
    for record in records:
        group = by_group.setdefault(
            record["group"],
            {"boxes": Counter(), "images": Counter()},
        )
        for class_id, count in record["class_counts"].items():
            group["boxes"][int(class_id)] += count
        for class_id in record["class_ids"]:
            group["images"][int(class_id)] += 1
    output = {}
    for group in sorted(by_group):
        boxes = by_group[group]["boxes"]
        images = by_group[group]["images"]
        output[group] = {
            "per_class": {
                name: {
                    "boxes": boxes[class_id],
                    "images": images[class_id],
                }
                for class_id, name in enumerate(class_names)
            },
            "missing_classes": [
                name for class_id, name in enumerate(class_names) if boxes[class_id] == 0
            ],
        }
    return output


def coverage_for_groups(
    coverage_by_group: dict,
    groups: list[str],
    class_names: list[str],
    records: list[dict],
    excluded_paths: set[str],
) -> dict:
    boxes = {name: 0 for name in class_names}
    images = {name: 0 for name in class_names}
    for group in groups:
        for name, values in coverage_by_group[group]["per_class"].items():
            boxes[name] += values["boxes"]
            images[name] += values["images"]
    side_records = [
        record
        for record in records
        if record["group"] in groups and record["path"] not in excluded_paths
    ]
    return {
        "groups": groups,
        "images": len(side_records),
        "boxes": sum(record["objects"] for record in side_records),
        "per_class": {
            name: {"boxes": boxes[name], "images": images[name]}
            for name in class_names
        },
        "missing_classes": [name for name in class_names if boxes[name] == 0],
        "classes_without_images": [name for name in class_names if images[name] == 0],
    }


def propose_logo_folds(groups: list[str]) -> list[dict]:
    ordered = sorted(groups)
    return [
        {
            "fold": index,
            "valid_group": group,
            "train_groups": [other for other in ordered if other != group],
        }
        for index, group in enumerate(ordered, start=1)
    ]


def build_fixed_assignments(
    records: list[dict],
    train_groups: list[str],
    valid_groups: list[str],
    excluded_paths: set[str],
) -> dict[str, str]:
    overlap = set(train_groups) & set(valid_groups)
    if overlap:
        raise SystemExit(f"groups on both sides of the fixed split: {sorted(overlap)}")
    assignments = {}
    for record in records:
        if record["path"] in excluded_paths:
            continue
        if record["group"] in train_groups:
            assignments[record["path"]] = "train"
        elif record["group"] in valid_groups:
            assignments[record["path"]] = "valid"
        else:
            raise SystemExit(
                f"record group {record['group']!r} is in neither split side: "
                f"{record['path']}"
            )
    return assignments


def validate_assignments(
    records: list[dict],
    fixed_assignments: dict[str, str],
    excluded_paths: set[str],
    logo_folds: list[dict],
) -> None:
    excluded_in_split = excluded_paths & set(fixed_assignments)
    if excluded_in_split:
        raise SystemExit(
            f"excluded labels still assigned: {sorted(excluded_in_split)[:5]}"
        )
    expected = {record["path"] for record in records} - excluded_paths
    missing = expected - set(fixed_assignments)
    if missing:
        raise SystemExit(f"records missing from fixed split: {sorted(missing)[:5]}")
    group_sides: dict[str, set[str]] = defaultdict(set)
    for record in records:
        side = fixed_assignments.get(record["path"])
        if side is not None:
            group_sides[record["group"]].add(side)
    leaking = [group for group, sides in group_sides.items() if len(sides) > 1]
    if leaking:
        raise SystemExit(f"groups appear on both fixed-split sides: {sorted(leaking)}")
    folds = [fold["valid_group"] for fold in logo_folds]
    if len(folds) != len(set(folds)):
        raise SystemExit("a group is used as a validation fold more than once")
    all_groups = set(group_sides)
    for fold in logo_folds:
        if set(fold["train_groups"]) & {fold["valid_group"]}:
            raise SystemExit(f"LOGO fold leaks its validation group: {fold['valid_group']}")
        if set(fold["train_groups"]) | {fold["valid_group"]} != all_groups:
            raise SystemExit(f"LOGO fold does not cover all groups: {fold['fold']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    dataset_dir = args.dataset.resolve()
    json_path = args.json.resolve()
    manifest_path = args.manifest.resolve()
    for target, label in ((json_path, "JSON"), (manifest_path, "manifest")):
        if target == dataset_dir or dataset_dir in target.parents:
            raise SystemExit(f"{label} output must not be inside the dataset")

    config = load_config(args.config.resolve())
    layout = discover_layout(dataset_dir)
    root = layout["row"]
    class_names, dataset_version = load_dataset_metadata(root)

    group_config = config.get("groups", {})
    if not isinstance(group_config, dict) or not group_config:
        raise SystemExit("config must define a non-empty groups mapping")
    prefix_to_group = {}
    for group, prefixes in group_config.items():
        for prefix in prefixes:
            if prefix in prefix_to_group:
                raise SystemExit(f"prefix declared in two groups: {prefix}")
            prefix_to_group[str(prefix)] = str(group)

    records, warnings = collect_records(root, layout["splits"], prefix_to_group)
    if any(record["group"] == "ungrouped" for record in records):
        raise SystemExit("some images could not be assigned to a configured group")

    inventory = group_inventory(records)
    empty_audit = classify_empty_frames(
        records,
        int(config.get("empty_label_policy", {}).get("probable_gap_max_bracket_gap", 3)),
    )
    coverage_by_group = class_coverage(records, class_names)
    groups = sorted(inventory)
    logo_folds = propose_logo_folds(groups)

    fixed = config.get("fixed_split", {})
    train_groups = [str(group) for group in fixed.get("train", [])]
    valid_groups = [str(group) for group in fixed.get("valid", [])]
    unknown = set(train_groups + valid_groups) - set(groups)
    if unknown:
        raise SystemExit(f"fixed split names unknown groups: {sorted(unknown)}")
    if set(train_groups) | set(valid_groups) != set(groups):
        raise SystemExit("fixed split must cover every configured group exactly once")

    excluded_paths = {item["path"] for item in empty_audit}
    for item in empty_audit:
        record = next(record for record in records if record["path"] == item["path"])
        if record["objects"] != 0:
            raise SystemExit(f"refusing to exclude a non-empty label: {item['path']}")

    fixed_assignments = build_fixed_assignments(
        records, train_groups, valid_groups, excluded_paths
    )
    validate_assignments(records, fixed_assignments, excluded_paths, logo_folds)

    train_coverage = coverage_for_groups(
        coverage_by_group, train_groups, class_names, records, excluded_paths
    )
    valid_coverage = coverage_for_groups(
        coverage_by_group, valid_groups, class_names, records, excluded_paths
    )
    if train_coverage["missing_classes"]:
        raise SystemExit(
            "training side lacks classes: "
            f"{train_coverage['missing_classes']}"
        )

    fold_details = []
    for fold in logo_folds:
        valid = coverage_for_groups(
            coverage_by_group,
            [fold["valid_group"]],
            class_names,
            records,
            excluded_paths,
        )
        train = coverage_for_groups(
            coverage_by_group,
            fold["train_groups"],
            class_names,
            records,
            excluded_paths,
        )
        fold_details.append(
            {
                **fold,
                "train_images": train["images"],
                "valid_images": valid["images"],
                "train_boxes": train["boxes"],
                "valid_boxes": valid["boxes"],
                "train_missing_classes": train["missing_classes"],
                "valid_missing_classes": valid["missing_classes"],
                "classes_untrainable_in_fold": [
                    name
                    for name in class_names
                    if train["per_class"][name]["boxes"] == 0
                ],
                "classes_unevaluable_in_fold": [
                    name
                    for name in class_names
                    if valid["per_class"][name]["boxes"] == 0
                ],
            }
        )

    duplicate_id_details = {
        group: {
            "duplicate_frame_ids": inventory[group]["duplicate_frame_ids"],
            "extra_images_on_duplicate_ids": inventory[group][
                "extra_images_on_duplicate_ids"
            ],
            "duplicate_id_pairs_cross_split": inventory[group][
                "duplicate_id_pairs_cross_split"
            ],
        }
        for group in groups
        if inventory[group]["duplicate_frame_ids"]
    }
    for group in duplicate_id_details:
        frame_counts = Counter(
            record["frame"] for record in records if record["group"] == group
        )
        duplicate_frames = sorted(
            frame for frame, count in frame_counts.items() if count > 1
        )
        duplicate_id_details[group]["examples"] = [
            {
                "canonical_id": f"{group}_mp4-{frame}",
                "copies": [
                    {
                        "split": record["split"],
                        "path": record["path"],
                        "objects": record["objects"],
                    }
                    for record in records
                    if record["group"] == group and record["frame"] == frame
                ],
            }
            for frame in duplicate_frames[:5]
        ]

    duplicate_id_similarity = measure_duplicate_id_similarity(records, root)

    common = {
        "phase": "3B.1",
        "generated_at_utc": utc_now(),
        "dataset": {
            "requested_path": str(dataset_dir.relative_to(PROJECT_ROOT)),
            "discovered_root": str(root.relative_to(PROJECT_ROOT)),
            "version": dataset_version,
            "class_names": class_names,
            "splits_present": layout["splits"],
        },
        "policy": config.get("empty_label_policy", {}),
        "groups": inventory,
        "exclusions": empty_audit,
        "fixed_split": {
            "train_groups": train_groups,
            "valid_groups": valid_groups,
            "train": {
                key: train_coverage[key]
                for key in ("images", "boxes", "missing_classes", "classes_without_images")
            },
            "valid": {
                key: valid_coverage[key]
                for key in ("images", "boxes", "missing_classes", "classes_without_images")
            },
        },
        "logo_folds": fold_details,
        "warnings": warnings,
        "limitations": [
            "Only five filename groups exist, so no independent test split can be formed.",
            "subwayy1_1 contains two recordings that share frame IDs; it is treated as one atomic group.",
            "boots-powerup occurs only in subwayedtied, so it cannot be both trained and evaluated in a group-held-out split.",
            "Class roles are derived from declared names and are not verified game mechanics.",
            "Empty labels are quarantined, not repaired; the dataset remains unmodified.",
            "Box geometry is not a calibrated distance measure.",
        ],
    }

    curation = {
        **common,
        "class_coverage_by_group": coverage_by_group,
        "class_roles": config.get("class_roles", {}),
        "missing_modalities": config.get("missing_modalities", {}),
        "duplicate_frame_ids": duplicate_id_details,
        "duplicate_id_similarity": duplicate_id_similarity,
        "empty_label_summary": {
            "total": len(empty_audit),
            "probable_gap": sum(
                1 for item in empty_audit if item["classification"] == "probable_gap"
            ),
            "isolated_plausible": sum(
                1
                for item in empty_audit
                if item["classification"] == "isolated_plausible"
            ),
        },
        "command": " ".join([Path(sys.executable).name, *sys.argv]),
    }

    manifest = {
        **common,
        "fixed_split": {
            **common["fixed_split"],
            "assignments": fixed_assignments,
        },
        "exclusions": [
            {
                "path": item["path"],
                "group": item["group"],
                "reason": item["classification"],
            }
            for item in empty_audit
        ],
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(curation, indent=1), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    print(f"groups={len(groups)} images={len(records)} boxes={sum(r['objects'] for r in records)}")
    print(
        "fixed train={} valid={} excluded={}".format(
            train_coverage["images"], valid_coverage["images"], len(empty_audit)
        )
    )
    print(
        "train_missing={} valid_missing={}".format(
            train_coverage["missing_classes"], valid_coverage["missing_classes"]
        )
    )
    print(f"empty probable_gap={curation['empty_label_summary']['probable_gap']} "
          f"isolated_plausible={curation['empty_label_summary']['isolated_plausible']}")
    print(f"json={json_path}")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
