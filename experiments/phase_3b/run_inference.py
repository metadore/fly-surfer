#!/usr/bin/env python3
"""Run the Phase 3B perception pipeline on one screenshot.

Two explicit modes:

``--mode mock`` (default)
    Feed a JSON list of scripted detections, or nothing, through the real
    validation, lane-assignment, scene and GameState code. This is test
    plumbing, not visual recognition.

``--mode onnx``
    Run the configured local ONNX detector. The model artifact is verified by
    SHA-256 before the session is created, and every detection is still
    validated downstream. A single-image result is a visual estimate, not
    gameplay accuracy or biological perception.

The curated split is looked up in reports/PHASE_3B1_SPLIT_MANIFEST.json. The
Roboflow train/valid folder is never used as a split source.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from perception.config import load_perception_config  # noqa: E402
from perception.detector import MockDetector  # noqa: E402
from perception.detector_config import (  # noqa: E402
    DetectorConfigError,
    load_detector_config,
)
from perception.inference import DetectorOutputError, OnnxRuntimeDetector  # noqa: E402
from perception.manifest import ManifestError, SplitManifest  # noqa: E402
from perception.pipeline import PerceptionPipeline  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
DEFAULT_DETECTOR_CONFIG = PROJECT_ROOT / "configs" / "detector_config.yaml"
DEFAULT_MANIFEST = PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"

MOCK_CLAIM = (
    "Scripted detections exercise the pipeline plumbing and are not model "
    "predictions, visual recognition or accuracy evidence."
)
ONNX_CLAIM = (
    "Detections come from a locally executed ONNX detector and are validated "
    "downstream. A single-image result is a visual estimate, not gameplay "
    "accuracy or biological perception."
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


def _onnx_detector(args, perception_config):
    detector_config = load_detector_config(args.detector_config)
    overrides = {}
    if args.model_path is not None:
        overrides["model_path"] = args.model_path
    if args.model_sha256 is not None:
        overrides["model_sha256"] = args.model_sha256
    if args.confidence_threshold is not None:
        overrides["confidence_threshold"] = args.confidence_threshold
    if args.nms_iou_threshold is not None:
        overrides["nms_iou_threshold"] = args.nms_iou_threshold
    if overrides:
        detector_config = replace(detector_config, **overrides)
    try:
        return OnnxRuntimeDetector(detector_config, perception_config.schema)
    except DetectorConfigError as exc:
        raise SystemExit(f"ONNX detector unavailable: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 3B perception plumbing: scripted (mock) or local ONNX "
            "detections on one screenshot."
        )
    )
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument(
        "--mode",
        choices=("mock", "onnx"),
        default="mock",
        help="mock: scripted/empty detections; onnx: local ONNX model",
    )
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--detector-config", type=Path, default=DEFAULT_DETECTOR_CONFIG
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="override detector.model_path (relative paths use the repo root)",
    )
    parser.add_argument("--model-sha256", default=None)
    parser.add_argument("--confidence-threshold", type=float, default=None)
    parser.add_argument("--nms-iou-threshold", type=float, default=None)
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

    if args.mode == "onnx":
        if args.predictions is not None:
            raise SystemExit("--predictions is only valid with --mode mock")
        detector = _onnx_detector(args, config)
        detections = None
        input_mode = "onnx_model"
        claim = ONNX_CLAIM
    else:
        if args.predictions is not None:
            detections = _load_predictions(args.predictions)
            input_mode = "scripted_predictions"
        else:
            detections = []
            input_mode = "empty_no_detector"
        detector = MockDetector(detections)
        claim = MOCK_CLAIM

    pipeline = PerceptionPipeline(config, detector)
    try:
        result = pipeline.run_path(
            image,
            frame_id=args.frame_id,
            timestamp_ms=args.timestamp_ms,
            detections=detections,
        )
    except DetectorOutputError as exc:
        raise SystemExit(f"ONNX detector returned an unusable output: {exc}")

    payload = result.as_dict()
    description = pipeline.describe()
    payload["input"] = {
        "image": str(image),
        "mode": input_mode,
        "predictions": str(args.predictions) if args.predictions else None,
        "detector_config": (
            str(args.detector_config) if args.mode == "onnx" else None
        ),
    }
    payload["visual_recognition_available"] = description[
        "visual_recognition_available"
    ]
    payload["detector_test_only"] = description["detector_test_only"]
    payload["curation"] = curation
    payload["claim"] = claim

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
