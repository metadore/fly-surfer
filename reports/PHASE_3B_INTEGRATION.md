# Phase 3B — Perception to Sensory Integration

**Status (2026-11-06):** scripted-detection integration **PASS**;
trained-detector integration **BLOCKED at that date** (no weights at the time).
No visual recognition is claimed.

**Date:** 2026-11-06

> **Later update (2026-11-07).** A trained YOLO11n ONNX detector now exists and
> was replayed over 100 real frames; see
> `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` and
> `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`. That replay is engineering
> evidence (deterministic pipeline, latency, spike totals), not independent
> detection accuracy. The scripted result in this document is preserved
> unchanged.

---

## 1. Implemented chain

```
RawDetection
  -> DetectionValidator          (confidence, geometry, bounds, class schema)
  -> PerceivedScene              (lane assignment, geometry)
  -> GameStateAdapter            (nearest object per kind, explicit unknowns)
  -> GameState                   (unchanged Phase 3A contract, 14 features)
  -> SpatialFeatureBridge        (feature vector + per-group provenance)
  -> FrameObservations           (all detections, frame-independent fields)
  -> TemporalSequenceProcessor   (Phase 3C, tracker + events)
  -> TemporalActivationScheduler
  -> BrainSimulator (connectome)
```

Perception never imports the simulator, the scheduler or the mapping modules.
The simulator and connectome artifact are unchanged. No action is selected.

## 2. Object/observation contract (3B.4)

`perception/observations.py::VisualObservation` carries:

- stable-within-frame `object_index`;
- `class_id`, `class_name`, `role`, `game_state_role`;
- `lane`;
- screen-pixel bounding box and normalised box;
- centre position (normalised and screen);
- `relative_horizontal_position` and `relative_vertical_position` in [-1, 1];
- `distance_proxy` and `normalized_proximity`;
- `confidence`;
- `valid` plus `invalid_reason`;
- `visibility` (`UNKNOWN` / visible / partial / out-of-frame categories);
- `frame_id` and `timestamp_ms`;
- `clamped`, `raw_index`, `source`.

`FrameObservations` keeps **every** observation of the frame and exposes
`obstacles()`, `trains()`, `coins()`, `player_objects()`, `other_objects()`,
`valid_observations()` and `invalid_observations()`. This is the multi-object
representation.

### 2.1 Backwards compatibility

`sensory/game_state.py` keeps the Phase 3A schema: one player, one obstacle,
one train, one coin. The adapter selects the **nearest** eligible object of
each kind and records everything else as `UnrepresentedObject` with a reason.
The dataset carries no player or coin labels, so the adapter does **not**
observe those fields: it fills player lane with `CENTER` (unless exactly one
player object is detected), speed with `0.5`, and `jumping`/`rolling` with
`False`, and lists `player.lane`, `player.speed`, `player.jumping` and
`player.rolling` in `estimated_fields`. Coin features default to absent.
These are schema defaults, not measurements. Existing encoders accept the
resulting 14-feature vector unchanged.

### 2.2 Scene roles

Configured class roles: `train`/`boxtrain` → train; low obstacles
(`jump-barrier`, `jump-electric`, `jump-hedge`, `jump-roll-barrier`,
`jump-trash`) → obstacle_low; high obstacles (`roll-barrier`,
`undercover-barrier`) → obstacle_high; terrain (`ledge`, `ramp`) and other
classes are tracked but not representable in `GameState`; power-ups and
boundary classes are unsupported. Roles are name-derived hypotheses.

## 3. Encoder connection (3B.5)

- `SpatialFeatureBridge` builds the existing 14-feature dict from the
  `GameState` and links each feature group to the observation that supplied
  it, including confidence, visibility, lane and distance proxy.
- No encoder was duplicated, no neuron mapping was changed, and no new
  biological role was assigned.
- Missing player/coin labels produce explicit `player_known = false` /
  `coins_available = false` flags; the encoder defaults are documented, not
  presented as perception. They are nevertheless encoded and scheduled like
  observations.

## 4. Scripted end-to-end evidence

`experiments/phase_3c/integration_check.py` runs ten scripted frames through
the real `PerceptionPipeline`, tracker, temporal encoder, scheduler and the
full connectome simulation. The detections are scripted, not recognised from
pixels.

| Check | Result |
| --- | --- |
| 10 frames processed, 0 rejected | PASS |
| Train and obstacle tracked, stable IDs | PASS |
| Train APPEARED / APPROACHING / OCCLUDED | PASS |
| One-frame flicker never confirmed | PASS |
| Terrain tracked but unrepresented | PASS |
| 14-feature GameState | PASS |
| Scheduler targets mapped neurons, pulse events present | PASS |
| Scheduler and spike-count determinism | PASS |
| Simulation stable at the protocol duration | PASS |
| Protected artifact hashes | PASS (4/4) |

All 16 integration checks pass. The full numeric record is
`experiments/phase_3c/results/integration.json`; it is discussed in
`reports/PHASE_3C_EVALUATION.md`.

## 5. Tests

| Area | File | Tests |
| --- | --- | ---: |
| Dataset contract | `tests/test_dataset_interface.py` | 8 |
| Detector backend and inference | `tests/test_detector_backend.py` | 12 |
| Observation layer | `tests/test_observations.py` | 12 |
| Pipeline, scene, GameState conversion | `tests/test_perception.py` | 38 |
| Evaluation harness | `tests/test_evaluation.py` | 13 |
| Tracking | `tests/test_tracking.py` | 12 |
| Curation | `tests/test_curation.py` | 6 |
| 3B + 3C chain | `tests/test_integration_3b_3c.py` | 5 |

Total suite: **265 passed** (2026-11-06).

## 6. Limitations

**Status at 2026-11-06.**

- Integrations in this document use scripted or `MockDetector` detections; no
  pixel recognition occurred.
- Lane assignment and distance are image geometry, not game semantics.
- The single-object `GameState` cannot carry multiple obstacles/trains; the
  observation layer does, but downstream encoding uses the nearest object.
- Player and coin states are unobserved; their schema defaults are
  nevertheless encoded and scheduled (see Section 2.1).
- At that date no real detector error had been propagated into the neural
  chain.

**Later replay (2026-11-07).** `experiments/phase_3b/real_sequence_replay.py`
propagated ONNX detector output through the tracker, temporal encoder,
`TemporalActivationScheduler` and the full connectome over 100 real frames
(334 candidates, 327 accepted, 7 rejected as out of bounds; 3,300.5 simulated
ms, 6,601 steps, 15,654,631 spikes; see
`reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`). Detector output therefore did
enter the neural chain. Detector-error propagation was still **not**
independently evaluated: the replayed sequence has no annotated object
identities, no independent test split exists, and the replay is engineering
evidence rather than an accuracy measurement.

## 7. Evidence files

- `perception/` modules
- `configs/perception_config.yaml`, `configs/detector_config.yaml`
- `experiments/phase_3b/results/*.json`
- `experiments/phase_3c/integration_check.py`,
  `experiments/phase_3c/results/integration.json`
- `tests/test_integration_3b_3c.py`
