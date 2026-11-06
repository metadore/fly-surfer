"""Validate the curated v15 dataset and write a machine-readable summary.

Usage::

    python -m experiments.phase_3b.validate_dataset
    python -m experiments.phase_3b.validate_dataset --skip-image-sizes
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from perception.dataset import CuratedDataset

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "phase_3b" / "results" / "dataset_validation.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the curated v15 detection dataset."
    )
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"),
    )
    parser.add_argument("--dataset-root", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--skip-image-sizes",
        action="store_true",
        help="do not open images; labels and split membership are still validated",
    )
    args = parser.parse_args(argv)

    dataset = CuratedDataset.load(
        args.manifest,
        dataset_root=args.dataset_root,
        repo_root=PROJECT_ROOT,
        verify_images=not args.skip_image_sizes,
    )
    summary = {
        "phase": "3B.1",
        "generated_at_utc": _utc_now(),
        "status": "PASS",
        "validation": dataset.describe(),
        "splits": {
            "train": dataset.split_statistics("train").as_dict(),
            "valid": dataset.split_statistics("valid").as_dict(),
        },
        "folds": [dataset.fold_statistics(fold.fold) for fold in dataset.folds],
        "excluded": list(dataset.excluded),
        "checks": {
            "annotations_parsed": True,
            "boxes_within_normalised_image": True,
            "duplicate_boxes": 0,
            "empty_included_labels": 0,
            "manifest_split_consistent": True,
            "image_files_opened": not args.skip_image_sizes,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    train = summary["splits"]["train"]
    valid = summary["splits"]["valid"]
    print(
        f"images={len(dataset.images)} boxes={train['boxes'] + valid['boxes']} "
        f"train={train['images']}/{train['boxes']} "
        f"valid={valid['images']}/{valid['boxes']} "
        f"excluded={len(dataset.excluded)} folds={len(dataset.folds)}",
        flush=True,
    )
    print(
        f"valid missing classes: {', '.join(valid['missing_classes']) or 'none'}",
        flush=True,
    )
    print(f"written: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
