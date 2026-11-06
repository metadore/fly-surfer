# Phase 3C — Evaluation

**Status:** synthetic temporal evaluation **PASS**; scripted end-to-end
integration **PASS** (16/16 checks); real-sequence replay with a trained
detector **BLOCKED** (no weights).

**Date:** 2026-11-06

---

## 1. What was measured

1. **Temporal calibration** on 10 synthetic sequence families
   (`experiments/phase_3c/results/temporal_calibration.json`).
2. **End-to-end integration** on 10 scripted detections through the real
   perception pipeline, tracker, temporal encoder, scheduler and full
   connectome (`experiments/phase_3c/results/integration.json`).

Neither uses a trained detector. Neither is an independent perception result.

## 2. Temporal calibration summary

Full detail and limitations: `reports/PHASE_3C_CALIBRATION.md`.

| Metric | Value |
| --- | ---: |
| Sequences | 50 (10 families × 5 trials) |
| Event micro TP / FP / FN | 175 / 0 / 0 |
| Event micro F1 | 1.000 |
| Direction accuracy | 1,011 / 1,015 = 0.9961 |
| Tracking continuity | 1,015 / 1,075 = 0.9442 |
| ID switches | 5 |
| Adversarial checks | 6 / 6 |
| Determinism (same seed) | identical |
| Scheduler `apply` n | 41,115 |
| Scheduler `apply` p50 / p95 / p99 | 3.5 / 9.5 / 15.7 µs |

Perfect event F1 is agreement with the documented lifecycle rules applied to
ground-truth boxes; it is not recognition accuracy. The direction misses are
4/1,015 and confined to the noisy family, where the debounce is active.

## 3. End-to-end integration

Scripted sequence: 10 frames at 30 fps (300 ms), 1280×720, one approaching
center train (skipped at frame 5), one static left barrier, one right ledge,
and a one-frame right-lane train flicker at frame 3.

| Item | Value |
| --- | ---: |
| Frames processed / rejected | 10 / 0 |
| Lifecycle events | 10 |
| Track IDs | 4 |
| GameState features | 14 |
| Simulation duration | 300.5 ms (601 steps at 0.5 ms) |
| Spikes total | 560 |
| Stimulated spikes | 444 |
| Non-stimulated spikes | 116 (20.7%) |
| Active neurons | 73 / 139,255 |
| Simulation wall time | 1.23 s (489 steps/s) |
| Connectome | 139,255 neurons / 3,732,460 edges / 50,666,648 synapses |
| Scheduler horizon | 550 ms (last frame + 250 ms hold) |
| Scheduler memory | 16,672 bytes |
| Integration checks | **16 / 16 pass** |

Events observed: `uncertain` at frame 0 for the three tracks, `appeared`
(frame 1), `approaching` (frame 2), a one-frame `uncertain` flicker (frame 3,
never confirmed), `occluded` (frame 5) and `approaching` again (frame 6).

Determinism: a second scheduler and a second simulation with the same seed
produced an identical signature, identical spike counts and identical
activity summary. All four protected artifact hashes match.

### 3.1 Scheduled current

Per-feature values are population sums of the maximum scheduled current, not
simultaneous totals. Per-neuron peak is 200 pA (the Phase 3A.5 operating
point). The highest population peak is `train_present` at 2,264 pA summed
over its population. The simulator's recorded maximum absolute total current
was 1,715.36 pA, i.e. the features do not all peak at the same instant.
Feature sums in the scheduler statistics are therefore an upper bound, not a
simultaneous current.

Coin currents are exactly zero because the dataset and the scripted scenes
contain no coin detections.

### 3.2 Duration sensitivity (recorded observation)

The protocol duration is the scripted sequence length. The payload also
records the same scheduled drive held to 400 ms:

| Duration | Total spikes | Stimulated | Non-stimulated |
| ---: | ---: | ---: | ---: |
| 300.5 ms (protocol) | 560 | 444 | 116 |
| 400 ms (probe) | 233,203 | 564 | 232,639 |

Stimulated spikes barely change (444 → 564), while non-stimulated spikes grow
by three orders of magnitude. In this configuration the recurrent network
enters a high-activity regime between the two durations under sustained
drive. The probe is recorded as an observation only; it is not a perception
result, and the reported protocol does not extend into that regime.

## 4. What is NOT evaluated

- No trained detector has produced the input; no pixel recognition occurred.
- No real game recording has been replayed.
- No independent ground truth for temporal events exists; calibration uses
  rule-derived expectations.
- No biological coding claim is made from spike counts.
- No latency claim is made for the perception pipeline; scheduler timing is
  Python scheduling overhead only.
- `boots-powerup` and `jump-electric` remain unevaluable in detection terms,
  and no detection metric exists at all yet.

## 5. Limitations

- Synthetic and scripted boxes are idealized and do not reproduce detector
  noise, misses or domain shift.
- The 30 fps assumption and the uncalibrated distance proxy shape direction
  labels.
- Scripted scenes exercise plumbing, not perception quality.
- The single-object `GameState` reduces multi-object scenes to the nearest
  object of each kind.
- The avalanche observation shows that long sustained synthetic drive is not
  a validated operating regime for this network.

## 6. Tests

Full suite: **265 passed** on 2026-11-06. Phase 3C files:
`test_temporal.py` (20), `test_temporal_calibration.py` (12),
`test_temporal_scheduler.py` (13), `test_integration_3b_3c.py` (5), plus
`test_tracking.py` (12) shared with Phase 3B.
