# Phase 3B — Evaluation Harness and Result Status

**Status:** evaluation harness **PASS** (implemented and tested); trained
detector **BLOCKED** (no weights). No detection-accuracy number exists.

**Date:** 2026-11-06

---

## 1. Protocol

Frozen from `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md` section 5:

- Split source: `reports/PHASE_3B1_SPLIT_MANIFEST.json`; group-atomic.
- Fixed split (train groups → valid groups) is **model selection**, not test.
- Five LOGO folds are **variance and group sensitivity**, not test.
- No independent test split exists.
- IoU threshold 0.5; IoU sweep 0.50–0.95 in 0.05 steps.
- Operating confidence 0.25; evaluation confidence floor 0.05.
- Class-agnostic IoU 0.5 confusion matrix with background.
- Bootstrap 1,000 resamples, seed 20261105.
- Classes with fewer than 20 valid boxes are low-support; classes with zero
  validation support are unevaluable, not zero.

## 2. Implemented harness

`perception/evaluation.py`:

- greedy IoU matching;
- per-class precision, recall, F1 with support;
- micro and macro aggregates;
- AP@0.5 per class and mAP@0.5;
- mAP@0.5:0.95 over the IoU sweep;
- confusion matrix including background;
- false-positive taxonomy (duplicate, localisation, background, class
  confusion);
- false-negative taxonomy (no prediction, below threshold, localisation,
  class mismatch);
- bootstrap confidence intervals over images;
- latency summarisation with p50/p95/p99;
- peak-memory measurement.

`experiments/phase_3b/evaluate_detector.py`:

- resolves images only through the manifest;
- loads the optional detector via `configs/detector_config.yaml`;
- without approved weights or a predictions file it writes the frozen
  protocol plus class support with status `blocked`;
- never substitutes synthetic predictions for a trained model.

## 3. Recorded status

`experiments/phase_3b/results/detector_evaluation.json`:

| Field | Value |
| --- | --- |
| status | `blocked` |
| predictions_source | `null` |
| metrics | `null` |
| latency | `null` |
| evaluation images | 1,128 |
| ground-truth boxes | 3,962 |
| unevaluable classes | `boots-powerup`, `jump-electric` |
| low-support classes | `undercover-barrier` (19 boxes) |
| harness peak working set | 56.96 MB (process memory, not a model measurement) |

The 56.96 MB figure measures the evaluation CLI process on the frozen support
scan. It is **not** detector memory and must not be cited as such.

## 4. What is deliberately absent

- No precision, recall, F1, mAP, confusion matrix, per-class AP, latency or
  model-size number for a trained detector.
- No validation result presented as test performance.
- No zero-filled metrics for unevaluable classes.
- No `MockDetector` output promoted to an accuracy baseline.

## 5. Requirements before any metric may be reported

1. Approved checkpoint license and SHA-256; weights stored locally, not
   committed.
2. Approved dependency set and a passing one-epoch or one-batch resource
   smoke test.
3. Frozen protocol and operating-point rule (already written).
4. Predictions emitted down to confidence 0.05 and evaluated on the fixed
   valid split, then LOGO folds where compute permits.
5. Every table carries image/box support, the split name, and the statement
   that it is group-held-out validation, not independent test performance.

## 6. Harness verification

`tests/test_evaluation.py` — 13 tests covering matching, AP, mAP over the IoU
sweep, confusion, taxonomies, bootstrap, latency and memory helpers, and
invalid-input rejection. The harness is exercised only with synthetic boxes;
those tests verify the metric code, not a detector.

## 7. Limitations

- The harness has not processed a real model's predictions.
- The distance proxy and lane assignment are geometric conversions, not
  verified game quantities.
- mAP does not measure lane behaviour, distance accuracy, temporal stability
  or latency; those require separate game-specific metrics.
- No independent test split can be manufactured from the five recordings.
