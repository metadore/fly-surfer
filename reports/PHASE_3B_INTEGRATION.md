# Phase 3B — Perception to Sensory Integration

**Status:** scripted-detection integration **PASS**; trained-detector
integration **BLOCKED** (no weights). No visual recognition is claimed.

**Date:** 2026-11-06

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
No field is invented for player or coin, because the dataset has no such
labels. Existing encoders accept the resulting 14-feature vector unchanged.

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
  presented as perception.

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

- Integrations use scripted or `MockDetector` detections; no pixel
  recognition occurred.
- Lane assignment and distance are image geometry, not game semantics.
- The single-object `GameState` cannot carry multiple obstacles/trains; the
  observation layer does, but downstream encoding uses the nearest object.
- Player and coin states remain unknown.
- No real detector error has been propagated into the neural chain.

## 7. Evidence files

- `perception/` modules
- `configs/perception_config.yaml`, `configs/detector_config.yaml`
- `experiments/phase_3b/results/*.json`
- `experiments/phase_3c/integration_check.py`,
  `experiments/phase_3c/results/integration.json`
- `tests/test_integration_3b_3c.py`
