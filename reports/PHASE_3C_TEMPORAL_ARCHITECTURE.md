# Phase 3C — Temporal Sensory Architecture

**Status:** implemented **PASS** (synthetic/scripted sequences). No action is
selected, no simulator was replaced and the Phase 3A.5 operating point is
unchanged.

**Date:** 2026-11-06

---

## 1. Position in the chain

```
FrameObservations (all detections, frame timestamp)
  -> MultiObjectTracker
  -> TemporalFeatureEncoder
  -> TemporalFrame (per track features, lifecycle events, GameState)
  -> TemporalActivationScheduler
  -> BrainSimulator.apply(step, time_ms, current)
```

The scheduler implements the same `apply` contract as the Phase 3A
`SensoryInputScheduler` and only **adds** current; it never overwrites
unrelated input. Perception and connectome dynamics remain separate.

## 2. Tracking

`perception/tracking.py::MultiObjectTracker`:

| Parameter | Value |
| --- | ---: |
| IoU threshold | 0.30 |
| Centre-gate distance | 0.35 |
| Duplicate IoU | 0.75 |
| `max_age` | 2 frames |
| `min_hits` | 2 |
| History limit | 32 frames |
| Class-aware | yes |
| Max live / retired tracks | 128 / 64 |

States: `TENTATIVE`, `CONFIRMED`, `OCCLUDED`, `LOST`. A tentative track never
drives `GameState`. Duplicate same-class detections are suppressed. Track IDs
are stable while a track survives; a track lost beyond `max_age` is re-created
with a new ID and that re-identification is reported as an ID switch, not
hidden.

## 3. Per-track features

`TrackTemporalFeatures` reports, per frame:

- `delta_x`, `delta_y` in normalised viewport units;
- `velocity_x`, `velocity_y` per frame or per second when timestamps exist;
- current and previous `distance_proxy`, `distance_delta`;
- `approaching` / `receding` booleans;
- `visibility`, `valid`, `hits`, `misses`, `confirmed`, `is_new`, `is_gap`.

Velocity is image-space, not physical. The distance proxy is the
bottom-edge projection, not metres.

## 4. Lifecycle and transition rules

States: `APPEARED`, `PERSISTING`, `APPROACHING`, `RECEDING`, `DISAPPEARED`,
`OCCLUDED`, `UNCERTAIN`.

| Rule |
| --- |
| tentative or below-confidence-floor track → `UNCERTAIN` |
| new confirmed track → `APPEARED` once |
| distance-proxy decrease ≥ 0.02 → `APPROACHING` |
| distance-proxy increase ≥ 0.02 → `RECEDING` |
| confirmed track without significant change → `PERSISTING`; a run no longer than the cooldown keeps the previous direction |
| missed association within `max_age` → `OCCLUDED` on first miss |
| missed association beyond `max_age` → `DISAPPEARED` once |

The PERSISTING hold is a configured debounce: a brief threshold dip inside an
ongoing approach/recede does not emit a second direction event. It is a rule
of this implementation, not evidence about fly motion processing.

## 5. Events and duplicate suppression

`LifecycleEvent` carries `track_id`, frame index, absolute `time_ms` and
`timestamp_ms`, event kind, class, role, lane, confidence, distance proxy,
feature values, `is_pulse` and a detail string.

- Pulse events: `APPEARED`, `APPROACHING`, `RECEDING`. They re-use the
  existing 14 feature names and are encoded by the existing encoders.
- Cooldown: 2 frames per event kind and track.
- Confidence floor: 0.25.
- Event priority is fixed (`APPEARED` highest, `PERSISTING` lowest) so
  ordering is deterministic.
- Non-increasing timestamps are rejected.

## 6. Scheduler

`TemporalActivationScheduler` (`sensory/temporal_scheduler.py`),
version `phase_3c_temporal_scheduler_v1`:

| Parameter | Value |
| --- | ---: |
| `max_hold_ms` | 250 |
| `pulse_gain` | 0.5 |
| `pulse_decay_ms` | 150 |
| Drive amplitude | Phase 3A.5 operating point (200 pA) |

Two additive components:

1. **Sample-and-hold:** the encoded `GameState` of the newest frame at or
   before the simulation time. Absolute timestamps are used, so irregular
   intervals and dropped frames do not shift the schedule. After
   `max_hold_ms` without a frame, drive stops; no state is extrapolated.
2. **Event pulses:** encoded feature drive from `APPEARED`, `APPROACHING` and
   `RECEDING`, scaled by `pulse_gain` and decaying linearly over
   `pulse_decay_ms`.

The scheduler exposes `signature()` (indices, per-frame values, frame times,
pulse values, pulse onsets) for reproducibility checks. Its temporary
per-feature buffer spans global neuron indices, so real mappings with sparse
indices work; this was a genuine bug found and fixed by the integration test.

## 7. Interface preservation

- `GameState` schema unchanged; multi-object input is reduced to the nearest
  eligible track per kind, with unrepresented tracks counted and noted.
- `BrainSimulator` unchanged except for the already-approved
  `input_schedule` hook; current is zeroed each step and the scheduler adds.
- Phase 3A `SensoryInputScheduler` untouched.
- Phase 3A.5 baseline (200 pA, sigma 0.20, four neurons, seed 20261104)
  untouched.
- New parameters are versioned in `TemporalSchedulerConfig`, independent of
  the Phase 3A.5 calibration.

## 8. Determinism and irregular input

- Same frames and seed produce an identical scheduler signature and identical
  spike counts (verified twice in the integration run).
- Frames carry absolute `time_ms`; gaps are flagged when the interval exceeds
  100 ms.
- The tracker tolerates `max_age = 2` missed frames; a longer absence becomes
  `DISAPPEARED` and later a new ID.
- Missing frames do not trigger re-timed holds: the schedule follows the
  timestamps actually supplied.

## 9. Tests

| File | Tests |
| --- | ---: |
| `tests/test_tracking.py` | 12 |
| `tests/test_temporal.py` | 20 |
| `tests/test_temporal_scheduler.py` | 13 |
| `tests/test_temporal_calibration.py` | 12 |
| `tests/test_integration_3b_3c.py` | 5 |

The suite also includes the pre-existing Phase 2/3A/3A.5 tests, for
**265 passed** in total.

## 10. Limitations

- No trained detector output has been replayed; the temporal layer has only
  seen scripted and synthetic boxes.
- The distance proxy is uncalibrated; approach/recede is a threshold on that
  proxy.
- Occlusion is inferred from missed associations, not observed.
- The single-object `GameState` still limits downstream encoding to the
  nearest object of each kind.
- Pulse drive is extra input; it is not evidence of a biological event code.
- No action, motor decoding, learning or reward is implemented.
