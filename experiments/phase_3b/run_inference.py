#!/usr/bin/env python3
"""Run the Phase 3B.2A perception architecture on one screenshot.

There is no trained detector in this phase. With ``--predictions`` the script
feeds a JSON list of detections through the real validation, lane-assignment,
scene and GameState code; without it the detection list is empty. Either way
nothing here is visual recognition, and the output says so.

The curated split is looked up in reports/PHASE_3B1_SPLIT_MANIFEST.json. The
Roboflow train/valid folder is never used as a split source.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from perception.config import load_perception_config  # noqa: E402
from perception.detector import MockDetector  # noqa: E402
from perception.manifest import ManifestError, SplitManifest  # noqa: E402
from perception.pipeline import PerceptionPipeline  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
DEFAULT_MANIFEST = PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"

CLAIM = (
    "No trained detector is integrated. Scripted detections exercise the "
    "pipeline plumbing and are not model predictions or accuracy evidence."
)


def _load_predictions(path: Path) -> list:
    if not path.is_file():
        raise SystemExit(f"predictions file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read predictions {path}: {exc}")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("detections"), list):
        return payload["detections"]
    raise SystemExit(
        "predictions must be a JSON list or an object with a 'detections' list"
    )


def _curation_block(image: Path, manifest_path: Path, allow_excluded: bool) -> dict:
    manifest = SplitManifest.load(manifest_path, repo_root=PROJECT_ROOT)
    try:
        assignment = manifest.resolve(image)
    except ManifestError as exc:
        try:
            image.resolve().relative_to(manifest.dataset_root_path)
            inside_dataset = True
        except ValueError:
            inside_dataset = False
        if inside_dataset:
            raise SystemExit(
                f"cannot resolve curated group for dataset image: {exc}"
            )
        return {
            "status": "external_input",
            "detail": (
                "Image is not a curated dataset image; no manifest split "
                "applies. " + str(exc)
            ),
            "manifest": manifest.describe(),
        }
    if assignment.excluded and not allow_excluded:
        raise SystemExit(
            f"image is excluded by the curation manifest "
            f"({assignment.exclusion_reason}); pass --allow-excluded to override"
        )
    return {
        "status": "curated",
        "assignment": assignment.as_dict(),
        "manifest": manifest.describe(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 3B.2A perception plumbing. No trained detector is included."
        )
    )
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--frame-id", default=None)
    parser.add_argument("--timestamp-ms", type=float, default=None)
    parser.add_argument(
        "--allow-excluded",
        action="store_true",
        help="permit an image the curation manifest excludes",
    )
    args = parser.parse_args(argv)

    image = args.image
    if not image.is_file():
        raise SystemExit(f"image not found: {image}")

    curation = _curation_block(image, args.manifest, args.allow_excluded)
    config = load_perception_config(args.config)

    if args.predictions is not None:
        detections = _load_predictions(args.predictions)
        input_mode = "scripted_predictions"
    else:
        detections = []
        input_mode = "empty_no_detector"
    detector = MockDetector(detections)
    pipeline = PerceptionPipeline(config, detector)
    result = pipeline.run_path(
        image,
        frame_id=args.frame_id,
        timestamp_ms=args.timestamp_ms,
        detections=detections,
    )

    payload = result.as_dict()
    payload["input"] = {
        "image": str(image),
        "predictions": str(args.predictions) if args.predictions else None,
        "mode": input_mode,
    }
    payload["curation"] = curation
    payload["claim"] = CLAIM

    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
