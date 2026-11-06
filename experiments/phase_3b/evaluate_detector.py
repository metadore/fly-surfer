#!/usr/bin/env python3
"""Evaluate detector predictions on the curated split or one LOGO fold.

Without approved model weights or a predictions file this script writes the
frozen evaluation protocol and class support only, with status ``blocked``.
It never invents detector metrics.

Prediction files are JSON objects mapping dataset-relative image paths to
lists of normalized boxes::

    {"test/abc.jpg": [{"class_id": 11, "confidence": 0.9,
                       "bbox": [0.4, 0.5, 0.6, 0.8]}]}

Metrics from externally supplied predictions describe those predictions, not
a trained detector unless the file was produced by one.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from perception.config import load_perception_config  # noqa: E402
from perception.dataset import CuratedDataset  # noqa: E402
from perception.detector_config import load_detector_config  # noqa: E402
from perception.evaluation import (  # noqa: E402
    EvaluationBox,
    evaluate_detections,
    peak_memory_mb,
    summarize_latency,
)
from perception.image import ImagePreprocessor  # noqa: E402
from perception.inference import OnnxRuntimeDetector  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
DEFAULT_DETECTOR_CONFIG = PROJECT_ROOT / "configs" / "detector_config.yaml"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "phase_3b" / "results" / "detector_evaluation.json"
)

PROTOCOL = {
    "source": "reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md section 5",
    "split_source": "reports/PHASE_3B1_SPLIT_MANIFEST.json",
    "test_split": False,
    "fixed_split_role": "model selection",
    "logo_role": "variance and group sensitivity",
    "iou_threshold": 0.5,
    "iou_sweep": [round(0.5 + 0.05 * index, 2) for index in range(10)],
    "operating_confidence": 0.25,
    "evaluation_confidence_floor": 0.05,
    "confusion_matrix": "class-agnostic IoU 0.5 with background",
    "bootstrap": {"resamples": 1000, "seed": 20261105},
    "low_support_boxes": 20,
    "excluded_images": 12,
    "rules": [
        "Never use Roboflow train/valid folder names as the split.",
        "Never train or evaluate on quarantined images.",
        "Do not tune on LOGO validation.",
        "Do not describe validation results as independent test performance.",
        "Report per-fold results, not only a pooled mean.",
    ],
}


def _load_predictions(path: Path, expected: set[str], class_names: dict) -> dict:
    if not path.is_file():
        raise SystemExit(f"predictions file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read predictions {path}: {exc}")
    if isinstance(payload, dict) and isinstance(payload.get("images"), dict):
        payload = payload["images"]
    if not isinstance(payload, dict):
        raise SystemExit(
            "predictions must be an object mapping image paths to box lists"
        )
    keys = set(payload)
    missing = sorted(expected - keys)
    extra = sorted(keys - expected)
    if missing or extra:
        raise SystemExit(
            "prediction coverage does not match the evaluated images; "
            f"missing={len(missing)} extra={len(extra)}"
            + (f" first_missing={missing[0]}" if missing else "")
            + (f" first_extra={extra[0]}" if extra else "")
        )
    converted = {}
    for image_id in sorted(payload):
        records = payload[image_id]
        if not isinstance(records, list):
            raise SystemExit(f"predictions for {image_id} must be a list")
        converted[image_id] = tuple(
            EvaluationBox.from_record(record, class_names=class_names)
            for record in records
        )
    return converted


def _ground_truth(dataset: CuratedDataset, images) -> dict:
    mapping = {}
    for image in images:
        mapping[image.relative_path] = tuple(
            EvaluationBox(
                class_id=annotation.class_id,
                confidence=1.0,
                x1=annotation.x1,
                y1=annotation.y1,
                x2=annotation.x2,
                y2=annotation.y2,
            )
            for annotation in image.boxes
        )
    return mapping


def _support_block(statistics: dict, threshold: int = 20) -> dict:
    per_class = statistics["per_class_boxes"]
    return {
        "images": statistics["images"],
        "boxes": statistics["boxes"],
        "images_without_boxes": statistics["images_without_boxes"],
        "per_class_boxes": per_class,
        "per_class_images": statistics["per_class_images"],
        "missing_classes": statistics["missing_classes"],
        "low_support_classes": sorted(
            name for name, count in per_class.items() if 0 < count < threshold
        ),
        "unevaluable_classes": sorted(
            name for name, count in per_class.items() if count == 0
        ),
    }


def _run_model(args, images, perception_config):
    config = load_detector_config(args.detector_config)
    if config.model_path is None:
        raise SystemExit(
            "detector weights are not configured; model evaluation is blocked "
            "(no weights are downloaded automatically)"
        )
    eval_config = replace(
        config,
        confidence_threshold=args.confidence_floor,
        model_path=str(Path(config.model_path).resolve()),
    )
    detector = OnnxRuntimeDetector(eval_config, perception_config.schema)
    preprocessor = ImagePreprocessor(perception_config.preprocess)
    predictions = {}
    latencies = []
    for image in images:
        frame = preprocessor.load(image.path, frame_id=Path(image.relative_path).stem)
        raws = detector.detect(frame)
        latencies.append(float(detector.last_inference_ms or 0.0))
        boxes = []
        for raw in raws:
            screen = frame.processed_box_to_screen(
                float(raw.x1), float(raw.y1), float(raw.x2), float(raw.y2)
            )
            normalized = frame.screen_box_to_normalized(screen)
            boxes.append(
                EvaluationBox(
                    raw.class_id,
                    float(raw.confidence),
                    normalized.x1,
                    normalized.y1,
                    normalized.x2,
                    normalized.y2,
                )
            )
        predictions[image.relative_path] = tuple(boxes)
    return predictions, latencies, detector.describe()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--model", action="store_true", help="run a local ONNX model")
    parser.add_argument("--detector-config", type=Path, default=DEFAULT_DETECTOR_CONFIG)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--split", choices=("train", "valid"), default="valid")
    parser.add_argument("--fold", type=int, default=None, choices=range(5))
    parser.add_argument("--operating-confidence", type=float, default=0.25)
    parser.add_argument("--confidence-floor", type=float, default=0.05)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if args.predictions is not None and args.model:
        raise SystemExit("choose either --predictions or --model, not both")

    dataset = CuratedDataset.load(repo_root=PROJECT_ROOT)
    perception_config = load_perception_config(args.config)
    class_names = {
        definition.class_id: definition.name
        for definition in perception_config.schema.classes
    }

    if args.fold is None:
        images = dataset.for_split(args.split)
        statistics = dataset.split_statistics(args.split)
        selection = {"split": args.split, "fold": None}
    else:
        view = dataset.for_fold(args.fold)
        images = view.valid_images
        statistics = dataset.statistics(images, f"fold_{args.fold}_valid")
        selection = {
            "split": "valid",
            "fold": args.fold,
            "valid_group": view.valid_group,
        }

    payload = {
        "phase": "3B.6",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked",
        "claim": (
            "No trained detector metrics are produced without approved "
            "weights or supplied predictions."
        ),
        "selection": selection,
        "dataset": {
            "dataset_root": str(dataset.manifest.dataset_root_path),
            "manifest": str(dataset.manifest.source_path),
            "manifest_sha256": dataset.manifest_sha256,
            "class_names": list(class_names.values()),
        },
        "support": _support_block(statistics.as_dict()),
        "protocol": PROTOCOL,
        "predictions_source": None,
        "metrics": None,
        "latency": None,
        "memory": peak_memory_mb(),
        "limitations": [
            "There is no independent test split; these are held-out "
            "recordings, not an independent test set.",
            "Player and coin classes are absent from the dataset.",
            "boots-powerup and jump-electric have no validation images in the "
            "fixed split, so their validation AP is undefined.",
        ],
    }

    if args.predictions is not None or args.model:
        if args.model:
            predictions, latencies, detector_description = _run_model(
                args, images, perception_config
            )
            source = "local_onnx_model"
            payload["predictions_source"] = {
                "kind": source,
                "detector": detector_description,
                "confidence_floor": args.confidence_floor,
            }
            payload["status"] = "evaluated_local_onnx_model"
            payload["claim"] = (
                "Metrics describe a locally executed ONNX model on held-out "
                "validation groups; they are not independent test results and "
                "the weights were not trained in this repository."
            )
        else:
            predictions = _load_predictions(
                args.predictions,
                {image.relative_path for image in images},
                class_names,
            )
            latencies = []
            source = "external_predictions"
            payload["predictions_source"] = {
                "kind": source,
                "path": str(args.predictions),
            }
            payload["status"] = "evaluated_external_predictions"
            payload["claim"] = (
                "Metrics describe user-supplied predictions. They are not a "
                "trained-detector result unless the file came from one."
            )
        ground_truth = _ground_truth(dataset, images)
        evaluation = evaluate_detections(
            ground_truth,
            predictions,
            class_names,
            operating_confidence=args.operating_confidence,
            bootstrap_resamples=args.bootstrap,
        )
        payload["metrics"] = evaluation.as_dict()
        if latencies:
            payload["latency"] = summarize_latency(latencies)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"status={payload['status']} images={len(images)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
