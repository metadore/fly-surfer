# Phase 3C — Evaluation

**Status (2026-11-06):** synthetic temporal evaluation **PASS**; scripted
end-to-end integration **PASS** (16/16 checks); real-sequence replay with a
trained detector **BLOCKED** at the time (no weights).

**Date:** 2026-11-06

> **Later update (2026-11-07).** A trained YOLO11n ONNX detector was integrated
> and a 100-frame real-frame replay was run
> (`reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`). That replay is an engineering
> exercise of the pipeline — deterministic output, latency and spike totals —
> not a Phase 3C temporal-separability evaluation and not independent
> perception accuracy. The 3C.1–3C.9 acceptance experiments remain unexecuted,
> so the 3C acceptance status in this document is unchanged.

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

**Stimulated-spike attribution (recorded payload).** The 444 stimulated spikes
are not all object-driven. `simulation.spikes_by_feature` in
`integration.json` decomposes them exactly:

| Feature | Spikes | Provenance in this scripted run |
| --- | ---: | --- |
| `player_lane` | 36 | defaulted — no player label |
| `player_speed` | 24 | defaulted — schema value `0.5` |
| `obstacle_present` | 62 | scripted object label |
| `obstacle_type` | 60 | scripted object label |
| `obstacle_lane` | 41 | geometry-derived proxy |
| `obstacle_distance` | 31 | geometry-derived proxy |
| `train_present` | 84 | scripted object label |
| `train_lane` | 56 | geometry-derived proxy |
| `train_distance` | 50 | geometry-derived proxy |
| `jumping`, `rolling`, `coin_*` | 0 | absent or defaulted |
| **Total** | **444** | |

60 of the 444 (13.5%) come from the two defaulted player features. The
remaining 384 come from the object features of the scripted scenes: 206 from
scripted presence/type labels and 178 from geometry-derived lane and distance
proxies. They are **not** detector-derived here, because the detections are
scripted rather than recognised from pixels. In the 2026-11-07 real-frame
replay the corresponding object features are detector-derived, but the reported
payload for that run does not decompose its stimulated spikes per feature.

Events observed: `uncertain` at frame 0 for the three tracks, `appeared`
(frame 1), `approaching` (frame 2), a one-frame `uncertain` flicker (frame 3,
never confirmed), `occluded` (frame 5) and `approaching` again (frame 6).

Determinism: a second scheduler and a second simulation with the same seed
produced an identical signature, identical spike counts and identical
activity summary. All four protected artifact hashes match.

### 3.1 Scheduled current

Per-feature values are population sums of the maximum scheduled current, not
simultaneous totals. Per-neuron peak is 200 pA, the amplitude selected by
Phase 3A.5. This run uses **12** `obstacle_distance` neurons, whereas the 3A.5
calibration selected **four**; only the amplitude is shared, so this is not the
calibrated four-neuron operating point (see
`docs/PHASE_3_SENSORY_ENCODING.md`, "Operating-point mismatch"). The highest
population peak is `train_present` at 2,264 pA summed over its population. The
simulator's recorded maximum absolute total current was 1,715.36 pA, i.e. the
features do not all peak at the same instant. Feature sums in the scheduler
statistics are therefore an upper bound, not a simultaneous current.

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

**Status at 2026-11-06**, the date of every measurement in Sections 2–3.

- No trained detector had produced the input measured here; no pixel
  recognition occurred in these runs.
- No real game recording had been replayed.
- No independent ground truth for temporal events exists; calibration uses
  rule-derived expectations.
- No biological coding claim is made from spike counts.
- No latency claim is made for the perception pipeline; scheduler timing is
  Python scheduling overhead only.
- `boots-powerup` and `jump-electric` remained unevaluable in detection terms,
  and no independent detection metric existed.

**Later context (2026-11-07).** `experiments/phase_3b/real_sequence_replay.py`
did replay 100 real detector frames through the same tracker, temporal encoder,
scheduler and connectome (327 accepted detections, 3,300.5 simulated ms,
6,601 steps, 15,654,631 spikes; see
`reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`). That run is engineering evidence
for a deterministic pipeline. It does not evaluate temporal separability,
supplies no independent detection accuracy, carries no annotated identities for
the replayed sequence, and does not execute any of the 3C.1–3C.9 conditions.
The statements above therefore remain true for the measurements in this report.

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
