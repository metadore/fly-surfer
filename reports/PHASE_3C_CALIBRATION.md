# Phase 3C — Temporal Calibration

**Status:** **PASS** on synthetic sequences. Agreement is with the documented
lifecycle rules, not with independently recorded game events.

**Date:** 2026-11-06

**Artifact:** `experiments/phase_3c/results/temporal_calibration.json`
(seed 20261106, 5 trials per family, 10 families, 50 sequences).

**Command:** `python -m experiments.phase_3c.temporal_calibration`

---

## 1. Families

| Family | Sequences | TP / FP / FN | Direction acc. | Continuity | ID switches | Pulse events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 5 | 5 / 0 / 0 | 1.000 | 0.950 | 0 | 5 |
| approaching | 5 | 10 / 0 / 0 | 1.000 | 0.955 | 0 | 10 |
| receding | 5 | 10 / 0 / 0 | 1.000 | 0.955 | 0 | 10 |
| sudden_appearance | 5 | 5 / 0 / 0 | 1.000 | 0.945 | 0 | 5 |
| disappearance | 5 | 15 / 0 / 0 | 1.000 | 0.907 | 0 | 5 |
| two_objects | 5 | 20 / 0 / 0 | 1.000 | 0.950 | 0 | 20 |
| temporary_occlusion | 5 | 20 / 0 / 0 | 1.000 | 0.955 | 0 | 15 |
| noisy_detections | 5 | 10 / 0 / 0 | 0.958 | 0.950 | 0 | 10 |
| irregular_intervals | 5 | 10 / 0 / 0 | 1.000 | 0.950 | 0 | 10 |
| missing_frames | 5 | 70 / 0 / 0 | 1.000 | 0.900 | 5 | 40 |
| **Aggregate** | **50** | **175 / 0 / 0** | **0.996** | **0.944** | **5** | **130** |

Aggregate micro precision, recall and F1 are **1.000** on the documented
event labels (175 TP, 0 FP, 0 FN).

Direction accuracy: 1,011 / 1,015 correct. The four misses are all in
`noisy_detections`, where the direction-hold debounce intentionally ignores a
quiet run of up to two frames.

Tracking continuity: 1,015 matched of 1,075 visible frames. The metric counts
the first tentative frame and every frame of a gap as unmatched, so it cannot
reach 1.0 by construction. Five ID switches occur in `missing_frames`, where
the object is absent longer than `max_age = 2`; they are reported rather than
hidden.

## 2. Event latency

Median event latency in ms after the triggering frame:

| Family | appeared | approaching | receding | occluded | disappeared |
| --- | ---: | ---: | ---: | ---: | ---: |
| static | 33.3 | — | — | — | — |
| approaching | 33.3 | 0.0 | — | — | — |
| receding | 33.3 | — | 0.0 | — | — |
| sudden_appearance | 33.3 | — | — | — | — |
| disappearance | 33.3 | — | — | 0.0 | 66.7 |
| two_objects | 33.3 | 0.0 | 0.0 | — | — |
| temporary_occlusion | 33.3 | 0.0 | — | 0.0 | — |
| noisy_detections | 33.3 | 0.0 | — | — | — |
| irregular_intervals | 90.0 | 0.0 | — | — | — |
| missing_frames | 33.3 | 0.0 | — | 0.0 | 66.7 |

`appeared` takes one extra frame because a track must reach `min_hits = 2`
before confirmation. `disappeared` follows the `max_age` window. The 90 ms
value in `irregular_intervals` is the interval actually supplied by that
family, not an added delay.

## 3. Scheduler overhead

`scheduler.apply` over all sequences, measured in microseconds:

| Statistic | Value |
| --- | ---: |
| n | 41,115 |
| mean | 5.195 µs |
| p50 | 3.5 µs |
| p95 | 9.5 µs |
| p99 | 15.7 µs |
| max | 1,315.4 µs |

Construction cost per sequence: 1.5–3.4 ms mean. The maximum is an isolated
Python/GC outlier; p95 and p99 are the useful figures. No connectome was
simulated in this calibration, so these numbers measure scheduling overhead
only.

## 4. Adversarial checks (6/6 pass)

| Check | Expectation | Observed |
| --- | --- | --- |
| `noise_only` | single-frame noise never confirms or emits object events | 40 `uncertain`, 0 confirmations/events |
| `duplicate_detections` | same-class duplicates become one track | 1 `appeared`, 1 track ID, 11/12 matched |
| `single_frame_dropout` | one miss is `OCCLUDED`, ID stable | 1 `appeared`, 1 `occluded`, 0 `disappeared`, 0 ID switches |
| `threshold_boundary_noise` | sub-threshold jitter emits no direction event | 0 `approaching`, 0 `receding` |
| `timestamp_regression` | non-increasing timestamps are rejected | raised |
| `stale_frame_hold` | drive held to `max_hold_ms`, then zero | 300 ms: > 0; 450 ms with `max_hold_ms = 100`: 0 |

## 5. Determinism

Two full calibrations with the same seed produced identical payloads
(`identical: True`). Same-seed metrics match exactly. Randomized families use
`numpy.random.default_rng(seed)` only.

## 6. Interpretation

- The perfect event F1 is **rule consistency**: expected events are generated
  from the same documented lifecycle and direction rules applied to
  ground-truth boxes. It is not independent recognition performance.
- The direction-hold is a configured debounce. It reduces duplicate direction
  events under noise and costs 4/1,015 direction labels in that family.
- The five ID switches are the expected consequence of re-identifying a track
  after a loss longer than `max_age`; they are not a hidden failure.
- The synthetic boxes use an uncalibrated bottom-edge distance proxy and a
  fixed 30 fps frame interval unless a family overrides it.

## 7. Recorded limitations

1. Sequences are synthetic and use idealized boxes; they are not detector
   output.
2. Expected events implement the documented rules from ground-truth boxes, so
   agreement checks consistency, not independently recorded game events.
3. The direction hold is a configured debounce, not evidence about fly motion
   processing.
4. Direction labels use the uncalibrated distance proxy.
5. Tracking continuity counts the first tentative frame and gap frames as
   unmatched; it cannot reach 1.0.
6. A track lost beyond `max_age` is re-created with a new ID; these are
   reported as ID switches.
7. Scheduler latency is Python overhead only; no connectome is simulated.
8. The ten families are a design probe, not a representative game sample.

## 8. Tests

`tests/test_temporal_calibration.py` (12 tests) re-runs a two-trial
calibration and asserts family coverage, metric structure, minimum aggregate
quality, count identities, uncertainty reporting, per-check adversarial
behaviour, determinism and lifecycle event production.
