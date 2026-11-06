"""Phase 3B evaluation-harness tests.

All boxes are synthetic normalized coordinates. No trained model is involved,
so these tests verify metric arithmetic and matching logic, not detector
accuracy.
"""

from __future__ import annotations

import math

import pytest

from perception.evaluation import (
    BACKGROUND_LABEL,
    EvaluationBox,
    average_precision,
    evaluate_detections,
    iou,
    match_boxes,
    peak_memory_mb,
    summarize_latency,
)

CLASS_NAMES = {0: "train", 1: "jump-barrier", 2: "roll-barrier"}


def box(class_id, confidence, x1, y1, x2, y2):
    return EvaluationBox(class_id, confidence, x1, y1, x2, y2)


def truth(class_id, x1, y1, x2, y2):
    return EvaluationBox(class_id, 1.0, x1, y1, x2, y2)


A = (0.10, 0.10, 0.30, 0.30)
B = (0.50, 0.50, 0.70, 0.70)


def test_iou_and_empty_match() -> None:
    assert iou(truth(0, *A), truth(0, *A)) == pytest.approx(1.0)
    assert iou(truth(0, *A), truth(0, *B)) == 0.0
    matches, unmatched_gt, unmatched_pred = match_boxes(
        [truth(0, *A)], [box(0, 0.9, *B)], iou_threshold=0.5
    )
    assert matches == []
    assert unmatched_gt == [0]
    assert unmatched_pred == [0]


def test_perfect_predictions() -> None:
    ground_truth = {
        "img1": [truth(0, *A), truth(1, *B)],
    }
    predictions = {
        "img1": [box(0, 0.9, *A), box(1, 0.8, *B)],
    }
    result = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=50
    )
    assert result.n_images == 1
    assert result.n_ground_truth == 2
    assert result.n_predictions == 2
    assert result.micro.precision == pytest.approx(1.0)
    assert result.micro.recall == pytest.approx(1.0)
    assert result.micro.f1 == pytest.approx(1.0)
    assert result.map50 == pytest.approx(1.0)
    assert result.map50_95 == pytest.approx(1.0)
    assert result.false_positives["total"] == 0
    assert result.false_negatives["total"] == 0
    assert result.confusion["matrix"]["train"]["train"] == 1
    assert result.confusion["matrix"]["jump-barrier"]["jump-barrier"] == 1
    assert result.unevaluated_classes == ("roll-barrier",)


def test_false_positive_and_missed_ground_truth() -> None:
    ground_truth = {"img1": [truth(0, *A), truth(0, *B)]}
    predictions = {
        "img1": [
            box(0, 0.9, *A),
            box(0, 0.8, 0.80, 0.80, 0.90, 0.90),
        ]
    }
    result = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=50
    )
    train = next(item for item in result.classes if item.class_id == 0)
    assert train.support == 2
    assert train.true_positives == 1
    assert train.false_positives == 1
    assert train.false_negatives == 1
    assert train.precision == pytest.approx(0.5)
    assert train.recall == pytest.approx(0.5)
    assert train.f1 == pytest.approx(0.5)
    assert train.ap50 == pytest.approx(0.5)
    assert result.false_positives["counts"]["background"] == 1
    assert result.false_negatives["counts"]["no_prediction"] == 1
    assert result.confusion["matrix"][BACKGROUND_LABEL]["train"] == 1
    assert result.confusion["matrix"]["train"][BACKGROUND_LABEL] == 1


def test_below_threshold_and_ap_uses_all_predictions() -> None:
    ground_truth = {"img1": [truth(0, *A)]}
    predictions = {"img1": [box(0, 0.10, *A)]}
    result = evaluate_detections(
        ground_truth,
        predictions,
        CLASS_NAMES,
        operating_confidence=0.25,
        bootstrap_resamples=50,
    )
    train = next(item for item in result.classes if item.class_id == 0)
    assert train.true_positives == 0
    assert train.false_negatives == 1
    assert train.ap50 == pytest.approx(1.0)
    assert result.n_predictions == 0
    assert result.false_negatives["counts"]["below_threshold_prediction"] == 1


def test_duplicate_prediction_taxonomy() -> None:
    ground_truth = {"img1": [truth(0, *A)]}
    predictions = {
        "img1": [
            box(0, 0.9, *A),
            box(0, 0.8, 0.105, 0.105, 0.305, 0.305),
        ]
    }
    result = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=50
    )
    train = next(item for item in result.classes if item.class_id == 0)
    assert train.true_positives == 1
    assert train.false_positives == 1
    assert result.false_positives["counts"]["duplicate"] == 1
    assert result.confusion["matrix"]["train"]["train"] == 1


def test_class_confusion_is_fp_and_fn() -> None:
    ground_truth = {"img1": [truth(0, *A)]}
    predictions = {"img1": [box(1, 0.9, *A)]}
    result = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=50
    )
    train = next(item for item in result.classes if item.class_id == 0)
    jump = next(item for item in result.classes if item.class_id == 1)
    assert train.false_negatives == 1
    assert jump.false_positives == 1
    assert jump.support == 0
    assert jump.evaluated is False
    assert result.false_positives["counts"]["class_confusion"] == 1
    assert result.false_negatives["counts"]["class_mismatch"] == 1
    assert result.confusion["matrix"]["train"]["jump-barrier"] == 1


def test_localization_error_taxonomy() -> None:
    ground_truth = {"img1": [truth(0, 0.10, 0.10, 0.50, 0.50)]}
    predictions = {"img1": [box(0, 0.9, 0.10, 0.10, 0.25, 0.50)]}
    candidate = box(0, 0.9, 0.10, 0.10, 0.25, 0.50)
    overlapping = truth(0, 0.10, 0.10, 0.50, 0.50)
    assert 0.1 <= iou(candidate, overlapping) < 0.5
    result = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=50
    )
    assert result.false_positives["counts"]["localization_error"] == 1
    assert result.false_negatives["counts"]["localization_below_iou"] == 1
    train = next(item for item in result.classes if item.class_id == 0)
    assert train.ap50 == pytest.approx(0.0)


def test_ap_interpolation_and_no_support() -> None:
    assert average_precision([], 0) is None
    assert average_precision([], 2) == 0.0
    assert average_precision([(0.9, True)], 1) == pytest.approx(1.0)
    # One TP at 0.9 and one FP at 0.8 with support 2.
    assert average_precision([(0.9, True), (0.8, False)], 2) == pytest.approx(0.5)


def test_matching_prefers_higher_confidence_and_class_awareness() -> None:
    gt = [truth(0, *A), truth(1, *B)]
    preds = [box(0, 0.5, *A), box(0, 0.9, *A), box(1, 0.7, *B)]
    matches, unmatched_gt, unmatched_pred = match_boxes(
        gt, preds, iou_threshold=0.5
    )
    assert sorted(matches) == [(0, 1, 1.0), (1, 2, 1.0)]
    assert unmatched_gt == []
    assert unmatched_pred == [0]


def test_unknown_images_and_classes_are_rejected() -> None:
    ground_truth = {"img1": [truth(0, *A)]}
    with pytest.raises(ValueError, match="outside the evaluated set"):
        evaluate_detections(
            ground_truth,
            {"img2": [box(0, 0.9, *A)]},
            CLASS_NAMES,
            bootstrap_resamples=10,
        )
    with pytest.raises(ValueError, match="not in the class list"):
        evaluate_detections(
            ground_truth,
            {"img1": [box(9, 0.9, *A)]},
            CLASS_NAMES,
            bootstrap_resamples=10,
        )
    with pytest.raises(ValueError, match="non-empty"):
        evaluate_detections({}, {}, CLASS_NAMES, bootstrap_resamples=10)


def test_bootstrap_is_deterministic_and_bounded() -> None:
    ground_truth = {
        f"img{index}": [truth(0, *A)] for index in range(5)
    }
    predictions = {
        f"img{index}": [box(0, 0.9 if index % 2 == 0 else 0.1, *A)]
        for index in range(5)
    }
    first = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=100
    )
    second = evaluate_detections(
        ground_truth, predictions, CLASS_NAMES, bootstrap_resamples=100
    )
    assert first.confidence_intervals == second.confidence_intervals
    interval = first.confidence_intervals["precision"]
    assert 0.0 <= interval["low"] <= interval["high"] <= 1.0
    assert first.confidence_intervals["seed"] == 20261105


def test_evaluation_box_record_parsing_and_validation() -> None:
    parsed = EvaluationBox.from_record(
        {"class_id": 0, "confidence": 0.5, "bbox": [0.1, 0.1, 0.2, 0.2]},
        class_names=CLASS_NAMES,
    )
    assert parsed.class_id == 0
    assert parsed.as_dict()["bbox"] == [0.1, 0.1, 0.2, 0.2]
    with pytest.raises(ValueError, match="normalized"):
        EvaluationBox.from_record({"class_id": 0, "bbox": [0, 0, 10, 10]})
    with pytest.raises(ValueError, match="not in the class list"):
        EvaluationBox.from_record(
            {"class_id": 99, "bbox": [0.1, 0.1, 0.2, 0.2]},
            class_names=CLASS_NAMES,
        )
    with pytest.raises(ValueError, match="positive width"):
        EvaluationBox(0, 0.5, 0.2, 0.1, 0.2, 0.4)


def test_latency_summary_and_memory() -> None:
    summary = summarize_latency([1.0, 2.0, 3.0, 4.0])
    assert summary["count"] == 4
    assert summary["mean_ms"] == pytest.approx(2.5)
    assert summary["p50_ms"] == pytest.approx(2.5)
    assert summary["p95_ms"] >= summary["p50_ms"]
    assert summary["p99_ms"] >= summary["p95_ms"]
    assert summary["min_ms"] == 1.0
    assert summary["max_ms"] == 4.0
    empty = summarize_latency([])
    assert empty["mean_ms"] is None
    memory = peak_memory_mb()
    assert memory["platform_note"]
    if memory["rss_mb"] is not None:
        assert memory["rss_mb"] > 0
