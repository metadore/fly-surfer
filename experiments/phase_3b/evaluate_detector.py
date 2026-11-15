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

The ``--model`` path runs the configured local ONNX detector. Its output is
passed through the same ``DetectionValidator`` rules as the production
pipeline; only the confidence threshold is lowered to the evaluation floor so
low-confidence boxes are still available for AP. Rejected detections are
counted and never enter the metrics. Zero-support classes are reported with
undefined AP rather than invented scores.

``--limit`` evaluates only the first N selected images. It exists for smoke
runs; results from a limited slice are not split-level performance.
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
from perception.detection import (  # noqa: E402
    DetectionValidator,
    RejectedDetection,
)
from perception.detector_config import (  # noqa: E402
    DetectorConfigError,
    load_detector_config,
)
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

TIMING_SCOPE = (
    "detector call wall time = preprocessing + session.run + "
    "decode/NMS/coordinate inversion; session_run is the ONNX Runtime call only"
)


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


def _validate_detections(frame, raws, validation_config, schema, source):
    """Apply the production validation rules to raw detector output."""
    validator = DetectionValidator(
        validation_config, schema, frame, source=source
    )
    accepted = []
    rejected = []
    for index, raw in enumerate(raws):
        outcome = validator.validate_one(raw, index)
        if isinstance(outcome, RejectedDetection):
            rejected.append(outcome)
        else:
            accepted.append(outcome)
    return accepted, rejected


def _run_model(args, images, perception_config):
    config = load_detector_config(args.detector_config)
    overrides = {}
    if args.model_path is not None:
        overrides["model_path"] = args.model_path
    if args.model_sha256 is not None:
        overrides["model_sha256"] = args.model_sha256
    if overrides:
        config = replace(config, **overrides)
    if config.model_path is None:
        raise SystemExit(
            "detector weights are not configured; model evaluation is blocked "
            "(no weights are downloaded automatically)"
        )
    # Lower only the confidence threshold: every other validation rule is the
    # production rule, so rejected detections are the same ones the pipeline
    # would reject.
    eval_config = replace(
        config, confidence_threshold=args.confidence_floor
    )
    try:
        detector = OnnxRuntimeDetector(eval_config, perception_config.schema)
    except DetectorConfigError as exc:
        raise SystemExit(f"ONNX detector unavailable: {exc}")

    validation_config = replace(
        perception_config.validation,
        confidence_threshold=args.confidence_floor,
    )
    preprocessor = ImagePreprocessor(perception_config.preprocess)
    detector_name = str(detector.describe().get("name", "onnx-runtime-detector"))
    predictions = {}
    detector_call_ms = []
    session_run_ms = []
    preprocess_ms = []
    postprocess_ms = []
    rejection_counts: dict[str, int] = {}
    rejection_examples: list[dict] = []
    n_raw = n_accepted = n_rejected = 0

    for image in images:
        frame = preprocessor.load(
            image.path, frame_id=Path(image.relative_path).stem
        )
        raws = detector.detect(frame)
        detector_call_ms.append(float(detector.last_detector_call_ms or 0.0))
        session_run_ms.append(float(detector.last_session_run_ms or 0.0))
        preprocess_ms.append(float(detector.last_preprocess_ms or 0.0))
        postprocess_ms.append(float(detector.last_postprocess_ms or 0.0))
        accepted, rejected = _validate_detections(
            frame,
            raws,
            validation_config,
            perception_config.schema,
            detector_name,
        )
        boxes = []
        for outcome in accepted:
            normalized = outcome.normalized_box
            boxes.append(
                EvaluationBox(
                    outcome.class_id,
                    outcome.confidence,
                    normalized.x1,
                    normalized.y1,
                    normalized.x2,
                    normalized.y2,
                )
            )
        n_accepted += len(accepted)
        n_rejected += len(rejected)
        for outcome in rejected:
            reason = outcome.reason.value
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            if len(rejection_examples) < 20:
                rejection_examples.append(
                    {"image": image.relative_path, **outcome.as_dict()}
                )
        n_raw += len(raws)
        predictions[image.relative_path] = tuple(boxes)

    timing = {
        "scope": TIMING_SCOPE,
        "detector_call": summarize_latency(detector_call_ms),
        "session_run": summarize_latency(session_run_ms),
        "preprocess": summarize_latency(preprocess_ms),
        "postprocess": summarize_latency(postprocess_ms),
    }
    validation = {
        "confidence_threshold": args.confidence_floor,
        "rules": (
            "same DetectionValidator rules as the production pipeline; only "
            "the confidence threshold is the evaluation floor"
        ),
        "n_raw_detections": n_raw,
        "n_accepted": n_accepted,
        "n_rejected": n_rejected,
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "rejection_examples": rejection_examples,
    }
    return predictions, timing, validation, detector.describe()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--model", action="store_true", help="run a local ONNX model")
    parser.add_argument("--detector-config", type=Path, default=DEFAULT_DETECTOR_CONFIG)
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="override detector.model_path (relative paths use the repo root)",
    )
    parser.add_argument("--model-sha256", default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--split", choices=("train", "valid"), default="valid")
    parser.add_argument("--fold", type=int, default=None, choices=range(1, 6))
    parser.add_argument("--operating-confidence", type=float, default=0.25)
    parser.add_argument("--confidence-floor", type=float, default=0.05)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="evaluate only the first N selected images (smoke runs)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if args.predictions is not None and args.model:
        raise SystemExit("choose either --predictions or --model, not both")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be a positive integer")

    dataset = CuratedDataset.load(repo_root=PROJECT_ROOT)
    perception_config = load_perception_config(args.config)
    class_names = {
        definition.class_id: definition.name
        for definition in perception_config.schema.classes
    }

    if args.fold is None:
        source_images = dataset.for_split(args.split)
        statistics_name = args.split
        selection = {"split": args.split, "fold": None}
    else:
        view = dataset.for_fold(args.fold)
        source_images = view.valid_images
        statistics_name = f"fold_{args.fold}_valid"
        selection = {
            "split": "valid",
            "fold": args.fold,
            "valid_group": view.valid_group,
        }
    if args.limit is not None:
        source_images = tuple(source_images[: args.limit])
        statistics_name = f"{statistics_name}_first{args.limit}"
        selection["limit"] = args.limit
    images = tuple(source_images)
    selection["n_images"] = len(images)
    statistics = dataset.statistics(images, statistics_name)
    support = _support_block(statistics.as_dict())

    limitations = [
        "There is no independent test split; these are held-out "
        "recordings, not an independent test set.",
        "Player and coin classes are absent from the dataset.",
    ]
    if support["unevaluable_classes"]:
        limitations.append(
            "Zero-support classes in this selection: "
            + ", ".join(support["unevaluable_classes"])
            + ". Their AP is undefined; no performance is claimed for them."
        )
    if args.limit is not None:
        limitations.append(
            f"Only the first {args.limit} selected images were evaluated; this "
            "is a smoke run, not split-level performance."
        )

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
        "support": support,
        "zero_support_classes": support["unevaluable_classes"],
        "protocol": PROTOCOL,
        "predictions_source": None,
        "metrics": None,
        "latency": None,
        "timing": None,
        "timing_scope": TIMING_SCOPE,
        "validation": None,
        "memory": peak_memory_mb(),
        "limitations": limitations,
    }

    if args.predictions is not None or args.model:
        if args.model:
            predictions, timing, validation, detector_description = _run_model(
                args, images, perception_config
            )
            source = "local_onnx_model"
            payload["predictions_source"] = {
                "kind": source,
                "detector": detector_description,
                "confidence_floor": args.confidence_floor,
            }
            payload["validation"] = validation
            payload["timing"] = timing
            payload["status"] = "evaluated_local_onnx_model"
            payload["claim"] = (
                "Metrics describe a locally executed ONNX model on held-out "
                "validation groups; they are not independent test results and "
                "the weights were not trained in this repository. Detections "
                "rejected by the production validator are excluded."
            )
            if args.limit is not None:
                payload["claim"] += (
                    f" Only {args.limit} images were evaluated (smoke run)."
                )
        else:
            predictions = _load_predictions(
                args.predictions,
                {image.relative_path for image in images},
                class_names,
            )
            timing = None
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
        if timing is not None:
            payload["latency"] = timing["detector_call"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"status={payload['status']} images={len(images)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
