"""Detection evaluation for the Phase 3B protocol.

The functions here are model-agnostic: they compare ground-truth boxes with
predictions supplied by any detector, including the test-only scripted
detector. They do not run a model and cannot produce model accuracy without
predictions.

Metrics follow the protocol frozen in
``reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md`` section 5: precision, recall
and F1 at IoU 0.5, AP@0.5, AP@0.5:0.95, per-class support, a confusion matrix
with background, false-positive/false-negative taxonomies, bootstrap
confidence intervals over images, and latency/memory summaries.

There is no independent test split. Results from the fixed validation groups
must not be reported as independent test performance.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import psutil

IOU_SWEEP = tuple(round(0.50 + 0.05 * index, 2) for index in range(10))
BACKGROUND_LABEL = "background"

FP_CATEGORIES = (
    "duplicate",
    "localization_error",
    "class_confusion",
    "background",
)
FN_CATEGORIES = (
    "no_prediction",
    "below_threshold_prediction",
    "localization_below_iou",
    "class_mismatch",
)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class EvaluationBox:
    """One normalized xyxy box used for matching.

    ``confidence`` is 1.0 for ground truth. Coordinates are viewport
    fractions, matching ``NormalizedBox``, so predictions and ground truth
    must be converted at the image boundary before evaluation.
    """

    class_id: int
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise ValueError("class_id must be an integer")
        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")
        confidence = _finite(self.confidence, "confidence")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        object.__setattr__(self, "confidence", confidence)
        coords = {
            "x1": _finite(self.x1, "x1"),
            "y1": _finite(self.y1, "y1"),
            "x2": _finite(self.x2, "x2"),
            "y2": _finite(self.y2, "y2"),
        }
        if any(not 0.0 <= value <= 1.0 for value in coords.values()):
            raise ValueError("evaluation boxes must use normalized coordinates")
        if coords["x2"] <= coords["x1"] or coords["y2"] <= coords["y1"]:
            raise ValueError("box must have positive width and height")
        for name, value in coords.items():
            object.__setattr__(self, name, value)

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @classmethod
    def from_record(
        cls,
        record: Mapping[str, Any],
        *,
        class_names: Mapping[int, str] | None = None,
    ) -> "EvaluationBox":
        """Build a box from a JSON-style prediction or annotation record."""
        if not isinstance(record, Mapping):
            raise ValueError("box record must be a mapping")
        class_id = record.get("class_id", record.get("class"))
        if isinstance(class_id, bool) or not isinstance(class_id, int):
            raise ValueError("class_id must be an integer")
        if class_names is not None and class_id not in class_names:
            raise ValueError(f"class_id {class_id} is not in the class list")
        confidence = record.get("confidence", 1.0)
        bbox = record.get("bbox")
        if bbox is not None:
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                raise ValueError("bbox must contain four normalized values")
            x1, y1, x2, y2 = bbox
        else:
            missing = [
                key for key in ("x1", "y1", "x2", "y2") if key not in record
            ]
            if missing:
                raise ValueError(f"box record is missing {missing}")
            x1, y1, x2, y2 = (
                record["x1"],
                record["y1"],
                record["x2"],
                record["y2"],
            )
        return cls(class_id, confidence, x1, y1, x2, y2)

    def as_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "confidence": self.confidence,
            "bbox": [self.x1, self.y1, self.x2, self.y2],
        }


def iou(first: EvaluationBox, second: EvaluationBox) -> float:
    """IoU of two normalized xyxy boxes."""
    left = max(first.x1, second.x1)
    top = max(first.y1, second.y1)
    right = min(first.x2, second.x2)
    bottom = min(first.y2, second.y2)
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = first.area + second.area - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


def match_boxes(
    ground_truth: Sequence[EvaluationBox],
    predictions: Sequence[EvaluationBox],
    *,
    iou_threshold: float,
    class_aware: bool = True,
    confidence_threshold: float = 0.0,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Greedy confidence-ordered matching.

    Returns ``(matches, unmatched_gt_indices, unmatched_prediction_indices)``
    where each match is ``(gt_index, prediction_index, iou)``. Predictions
    below ``confidence_threshold`` are not considered.
    """
    threshold = _finite(iou_threshold, "iou_threshold")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("iou_threshold must be in [0, 1]")
    floor = _finite(confidence_threshold, "confidence_threshold")
    if not 0.0 <= floor <= 1.0:
        raise ValueError("confidence_threshold must be in [0, 1]")
    order = sorted(
        (index for index, item in enumerate(predictions) if item.confidence >= floor),
        key=lambda index: (-predictions[index].confidence, index),
    )
    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for pred_index in order:
        prediction = predictions[pred_index]
        best_index = None
        best_iou = -1.0
        for gt_index, truth in enumerate(ground_truth):
            if gt_index in matched_gt:
                continue
            if class_aware and truth.class_id != prediction.class_id:
                continue
            value = iou(truth, prediction)
            if value > best_iou:
                best_iou = value
                best_index = gt_index
        if best_index is not None and best_iou >= threshold:
            matched_gt.add(best_index)
            matched_pred.add(pred_index)
            matches.append((best_index, pred_index, best_iou))
    unmatched_gt = [
        index for index in range(len(ground_truth)) if index not in matched_gt
    ]
    unmatched_pred = [
        index for index, item in enumerate(predictions)
        if item.confidence >= floor and index not in matched_pred
    ]
    return matches, unmatched_gt, unmatched_pred


def average_precision(
    records: Sequence[tuple[float, bool]], support: int
) -> float | None:
    """All-point interpolated AP; ``None`` when the class has no ground truth."""
    if support == 0:
        return None
    if not records:
        return 0.0
    ordered = sorted(records, key=lambda item: (-item[0], not item[1]))
    true_positives = 0
    false_positives = 0
    recalls: list[float] = []
    precisions: list[float] = []
    for _confidence, is_true_positive in ordered:
        if is_true_positive:
            true_positives += 1
        else:
            false_positives += 1
        recalls.append(true_positives / support)
        precisions.append(true_positives / (true_positives + false_positives))
    mrec = [0.0] + recalls + [1.0]
    mpre = [0.0] + precisions + [0.0]
    for index in range(len(mpre) - 2, -1, -1):
        mpre[index] = max(mpre[index], mpre[index + 1])
    ap = 0.0
    for index in range(1, len(mrec)):
        if mrec[index] != mrec[index - 1]:
            ap += (mrec[index] - mrec[index - 1]) * mpre[index]
    return max(0.0, min(1.0, ap))


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class ClassMetrics:
    class_id: int
    class_name: str
    support: int
    n_predictions: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None
    ap50: float | None
    ap50_95: float | None
    low_support: bool
    evaluated: bool

    def as_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "support": self.support,
            "n_predictions": self.n_predictions,
            "tp": self.true_positives,
            "fp": self.false_positives,
            "fn": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "ap50": self.ap50,
            "ap50_95": self.ap50_95,
            "low_support": self.low_support,
            "evaluated": self.evaluated,
        }


@dataclass(frozen=True)
class AggregateMetrics:
    precision: float | None
    recall: float | None
    f1: float | None
    true_positives: int
    false_positives: int
    false_negatives: int
    support: int

    def as_dict(self) -> dict:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "tp": self.true_positives,
            "fp": self.false_positives,
            "fn": self.false_negatives,
            "support": self.support,
        }


def _aggregate(
    tp: int, fp: int, fn: int, support: int
) -> AggregateMetrics:
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    return AggregateMetrics(
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        support=support,
    )


def _mean(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = fraction * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _taxonomies(
    ground_truth: Mapping[str, Sequence[EvaluationBox]],
    predictions: Mapping[str, Sequence[EvaluationBox]],
    class_names: Mapping[int, str],
    *,
    iou_threshold: float,
    confidence_threshold: float,
    localization_floor: float,
) -> tuple[dict, dict, dict]:
    """Automatic geometric taxonomy at the operating threshold.

    A prediction that overlaps a ground-truth box of another class counts as
    both a false positive (class confusion) and a false negative (class
    mismatch), which is how class-aware metrics already penalise it.
    """
    fp_counts = {category: 0 for category in FP_CATEGORIES}
    fn_counts = {category: 0 for category in FN_CATEGORIES}

    used_classes = sorted(
        {
            item.class_id
            for boxes in list(ground_truth.values()) + list(predictions.values())
            for item in boxes
        }
    )
    labels = [class_names[class_id] for class_id in used_classes]
    labels.append(BACKGROUND_LABEL)
    matrix = {row: {column: 0 for column in labels} for row in labels}

    for image_id in sorted(ground_truth):
        truth = list(ground_truth[image_id])
        all_preds = list(predictions.get(image_id, ()))
        active = [
            item for item in all_preds if item.confidence >= confidence_threshold
        ]
        matches, unmatched_gt, unmatched_pred = match_boxes(
            truth,
            active,
            iou_threshold=iou_threshold,
            class_aware=False,
            confidence_threshold=confidence_threshold,
        )
        matched_gt_indices = {gt for gt, _, _ in matches}

        for gt_index, pred_index, _value in matches:
            truth_class = truth[gt_index].class_id
            pred_class = active[pred_index].class_id
            matrix[class_names[truth_class]][class_names[pred_class]] += 1
            if truth_class != pred_class:
                fp_counts["class_confusion"] += 1
                fn_counts["class_mismatch"] += 1

        for gt_index in unmatched_gt:
            item = truth[gt_index]
            same_class = [
                pred for pred in all_preds if pred.class_id == item.class_id
            ]
            same_class_iou = max(
                (iou(item, pred) for pred in same_class), default=0.0
            )
            any_class_iou = max(
                (iou(item, pred) for pred in all_preds), default=0.0
            )
            if any(
                pred.confidence < confidence_threshold
                and iou(item, pred) >= iou_threshold
                for pred in same_class
            ):
                category = "below_threshold_prediction"
            elif same_class_iou >= localization_floor:
                category = "localization_below_iou"
            elif any_class_iou >= iou_threshold:
                category = "class_mismatch"
            else:
                category = "no_prediction"
            fn_counts[category] += 1
            matrix[class_names[item.class_id]][BACKGROUND_LABEL] += 1

        for pred_index in unmatched_pred:
            item = active[pred_index]
            same_class = [
                gt for gt in truth if gt.class_id == item.class_id
            ]
            is_duplicate = any(
                gt_index in matched_gt_indices
                and truth[gt_index].class_id == item.class_id
                and iou(truth[gt_index], item) >= iou_threshold
                for gt_index in range(len(truth))
            )
            if is_duplicate:
                category = "duplicate"
            elif same_class and max(
                (iou(gt, item) for gt in same_class), default=0.0
            ) >= localization_floor:
                category = "localization_error"
            else:
                category = "background"
            fp_counts[category] += 1
            matrix[BACKGROUND_LABEL][class_names[item.class_id]] += 1

    return (
        {"counts": fp_counts, "total": sum(fp_counts.values())},
        {"counts": fn_counts, "total": sum(fn_counts.values())},
        {"labels": labels, "matrix": matrix},
    )


def _bootstrap_ci(
    per_image: Sequence[tuple[int, int, int]],
    *,
    resamples: int,
    seed: int,
) -> dict:
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if not per_image:
        return {
            "precision": None,
            "recall": None,
            "resamples": 0,
            "seed": seed,
        }
    rng = random.Random(seed)
    precision_samples: list[float] = []
    recall_samples: list[float] = []
    for _ in range(resamples):
        tp = fp = fn = 0
        for _index in range(len(per_image)):
            sample = per_image[rng.randrange(len(per_image))]
            tp += sample[0]
            fp += sample[1]
            fn += sample[2]
        if tp + fp > 0:
            precision_samples.append(tp / (tp + fp))
        if tp + fn > 0:
            recall_samples.append(tp / (tp + fn))
    precision_samples.sort()
    recall_samples.sort()
    return {
        "precision": (
            {
                "low": _percentile(precision_samples, 0.025),
                "high": _percentile(precision_samples, 0.975),
            }
            if precision_samples
            else None
        ),
        "recall": (
            {
                "low": _percentile(recall_samples, 0.025),
                "high": _percentile(recall_samples, 0.975),
            }
            if recall_samples
            else None
        ),
        "resamples": resamples,
        "seed": seed,
    }


@dataclass(frozen=True)
class DetectionEvaluation:
    n_images: int
    n_ground_truth: int
    n_predictions: int
    operating_confidence: float
    iou_threshold: float
    classes: tuple[ClassMetrics, ...]
    micro: AggregateMetrics
    macro: AggregateMetrics
    map50: float | None
    map50_95: float | None
    confusion: dict
    false_positives: dict
    false_negatives: dict
    confidence_intervals: dict
    unevaluated_classes: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "n_images": self.n_images,
            "n_ground_truth": self.n_ground_truth,
            "n_predictions": self.n_predictions,
            "operating_confidence": self.operating_confidence,
            "iou_threshold": self.iou_threshold,
            "classes": [item.as_dict() for item in self.classes],
            "micro": self.micro.as_dict(),
            "macro": self.macro.as_dict(),
            "map50": self.map50,
            "map50_95": self.map50_95,
            "confusion": self.confusion,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "confidence_intervals": self.confidence_intervals,
            "unevaluated_classes": list(self.unevaluated_classes),
            "notes": list(self.notes),
        }


def evaluate_detections(
    ground_truth: Mapping[str, Sequence[EvaluationBox]],
    predictions: Mapping[str, Sequence[EvaluationBox]],
    class_names: Mapping[int, str],
    *,
    operating_confidence: float = 0.25,
    iou_threshold: float = 0.5,
    iou_sweep: Sequence[float] = IOU_SWEEP,
    low_support_threshold: int = 20,
    localization_floor: float = 0.1,
    bootstrap_resamples: int = 1000,
    bootstrap_seed: int = 20261105,
) -> DetectionEvaluation:
    """Evaluate predictions against ground truth on a fixed image set."""
    if not isinstance(ground_truth, Mapping) or not ground_truth:
        raise ValueError("ground_truth must be a non-empty mapping")
    if not isinstance(predictions, Mapping):
        raise ValueError("predictions must be a mapping")
    unknown_images = sorted(set(predictions) - set(ground_truth))
    if unknown_images:
        raise ValueError(
            f"predictions contain images outside the evaluated set: "
            f"{unknown_images[:5]}"
        )
    threshold = _finite(operating_confidence, "operating_confidence")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("operating_confidence must be in [0, 1]")
    iou_floor = _finite(iou_threshold, "iou_threshold")
    if not 0.0 < iou_floor <= 1.0:
        raise ValueError("iou_threshold must be in (0, 1]")
    sweep = tuple(float(value) for value in iou_sweep)
    if not sweep or any(not 0.0 < value <= 1.0 for value in sweep):
        raise ValueError("iou_sweep values must be in (0, 1]")

    gt: dict[str, tuple[EvaluationBox, ...]] = {}
    preds: dict[str, tuple[EvaluationBox, ...]] = {}
    for image_id, boxes in ground_truth.items():
        if not isinstance(image_id, str):
            raise ValueError("ground-truth image ids must be strings")
        if any(not isinstance(item, EvaluationBox) for item in boxes):
            raise ValueError("ground-truth boxes must be EvaluationBox")
        gt[image_id] = tuple(boxes)
    for image_id, boxes in predictions.items():
        if any(not isinstance(item, EvaluationBox) for item in boxes):
            raise ValueError("prediction boxes must be EvaluationBox")
        preds[image_id] = tuple(boxes)

    known_classes = set(class_names)
    for image_id, boxes in preds.items():
        unknown = sorted({item.class_id for item in boxes} - known_classes)
        if unknown:
            raise ValueError(
                f"prediction class ids {unknown} are not in the class list"
            )
    for boxes in gt.values():
        unknown = sorted({item.class_id for item in boxes} - known_classes)
        if unknown:
            raise ValueError(
                f"ground-truth class ids {unknown} are not in the class list"
            )

    classes: list[ClassMetrics] = []
    per_image: list[tuple[int, int, int]] = []
    for image_id in sorted(gt):
        truth = gt[image_id]
        active = [
            item
            for item in preds.get(image_id, ())
            if item.confidence >= threshold
        ]
        matches, unmatched_gt, unmatched_pred = match_boxes(
            truth,
            active,
            iou_threshold=iou_floor,
            class_aware=True,
            confidence_threshold=threshold,
        )
        per_image.append(
            (len(matches), len(unmatched_pred), len(unmatched_gt))
        )

    for class_id in sorted(known_classes):
        records_at: dict[float, list[tuple[float, bool]]] = {}
        support = 0
        n_predictions = 0
        tp = fp = fn = 0
        for image_id in sorted(gt):
            truth = [item for item in gt[image_id] if item.class_id == class_id]
            all_preds = [
                item
                for item in preds.get(image_id, ())
                if item.class_id == class_id
            ]
            support += len(truth)
            n_predictions += sum(
                1 for item in all_preds if item.confidence >= threshold
            )
            active = [
                item for item in all_preds if item.confidence >= threshold
            ]
            matches, unmatched_gt, unmatched_pred = match_boxes(
                truth,
                active,
                iou_threshold=iou_floor,
                confidence_threshold=threshold,
            )
            tp += len(matches)
            fp += len(unmatched_pred)
            fn += len(unmatched_gt)
            for value in sweep:
                matches_at, _, _ = match_boxes(
                    truth, all_preds, iou_threshold=value
                )
                matched = {pred for _, pred, _ in matches_at}
                records_at.setdefault(value, []).extend(
                    (item.confidence, index in matched)
                    for index, item in enumerate(all_preds)
                )
        ap_values = {
            value: average_precision(records_at.get(value, ()), support)
            for value in sweep
        }
        ap50 = ap_values.get(0.5)
        ap50_95 = _mean(list(ap_values.values()))
        precision = _safe_ratio(tp, tp + fp)
        recall = _safe_ratio(tp, support)
        classes.append(
            ClassMetrics(
                class_id=class_id,
                class_name=class_names[class_id],
                support=support,
                n_predictions=n_predictions,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=precision,
                recall=recall,
                f1=_f1(precision, recall),
                ap50=ap50,
                ap50_95=ap50_95,
                low_support=support < low_support_threshold,
                evaluated=support > 0,
            )
        )

    evaluated = [item for item in classes if item.evaluated]
    micro = _aggregate(
        sum(item.true_positives for item in classes),
        sum(item.false_positives for item in classes),
        sum(item.false_negatives for item in classes),
        sum(item.support for item in classes),
    )
    macro = AggregateMetrics(
        precision=_mean([item.precision for item in evaluated]),
        recall=_mean([item.recall for item in evaluated]),
        f1=_mean([item.f1 for item in evaluated]),
        true_positives=micro.true_positives,
        false_positives=micro.false_positives,
        false_negatives=micro.false_negatives,
        support=micro.support,
    )

    fp_taxonomy, fn_taxonomy, confusion = _taxonomies(
        gt,
        preds,
        class_names,
        iou_threshold=iou_floor,
        confidence_threshold=threshold,
        localization_floor=localization_floor,
    )
    intervals = _bootstrap_ci(
        per_image,
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )

    notes = [
        "Validation-group results are not independent test performance.",
        "Classes with zero support are reported but their AP is undefined.",
        "False-positive and false-negative taxonomies are automatic "
        "geometric assignments, not manual inspection.",
        "Predictions must be converted to normalized viewport coordinates "
        "with the same crop/resize transform used for ground truth.",
    ]
    return DetectionEvaluation(
        n_images=len(gt),
        n_ground_truth=sum(len(boxes) for boxes in gt.values()),
        n_predictions=sum(
            1
            for boxes in preds.values()
            for item in boxes
            if item.confidence >= threshold
        ),
        operating_confidence=threshold,
        iou_threshold=iou_floor,
        classes=tuple(classes),
        micro=micro,
        macro=macro,
        map50=_mean([item.ap50 for item in evaluated]),
        map50_95=_mean([item.ap50_95 for item in evaluated]),
        confusion=confusion,
        false_positives=fp_taxonomy,
        false_negatives=fn_taxonomy,
        confidence_intervals=intervals,
        unevaluated_classes=tuple(
            item.class_name for item in classes if not item.evaluated
        ),
        notes=tuple(notes),
    )


def summarize_latency(samples_ms: Sequence[float]) -> dict:
    """Mean/p50/p95/p99/min/max for measured per-image latencies."""
    values = [_finite(value, "latency") for value in samples_ms]
    if any(value < 0 for value in values):
        raise ValueError("latency samples must be non-negative")
    ordered = sorted(values)
    if not ordered:
        return {
            "count": 0,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    return {
        "count": len(ordered),
        "mean_ms": sum(ordered) / len(ordered),
        "p50_ms": _percentile(ordered, 0.50),
        "p95_ms": _percentile(ordered, 0.95),
        "p99_ms": _percentile(ordered, 0.99),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
    }


def peak_memory_mb() -> dict:
    """Process peak working set, when the platform exposes it."""
    process = psutil.Process()
    info = process.memory_info()
    peak = getattr(info, "peak_wset", None)
    rss = getattr(info, "rss", None)
    return {
        "peak_wset_mb": (
            round(float(peak) / (1024 * 1024), 2) if peak is not None else None
        ),
        "rss_mb": (
            round(float(rss) / (1024 * 1024), 2) if rss is not None else None
        ),
        "platform_note": (
            "peak_wset is available on Windows; on other platforms only RSS "
            "is reported."
        ),
    }
