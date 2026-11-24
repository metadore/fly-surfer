# Phase 3B.2C — Real Subway Surfers Sequence Replay

**Implementation date:** 2026-11-07
**Scope:** Drive one contiguous 100-frame sequence from a single held-out recording
through the existing visual perception, tracking, temporal encoding, activation
scheduling and connectome simulation chain.
**Machine-readable evidence:**
`experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`
**Smoke evidence:** `experiments/phase_3b/results/phase_3b2c_smoke.json`
**Verdict:** **PASS WITH LIMITATIONS**

This is an engineering integration experiment. It shows that real frames can
travel through the existing chain without crashing and that the chain is
deterministic. It is **not** evidence of gameplay success, detector accuracy on
an independent test set, annotated identity tracking, or biological perception.

No full-dataset inference was run. `best.pt` was never loaded or executed. No
package, model, dataset, connectome, README or annotation was modified, and
nothing was staged, committed or pushed.

---

## 1. Sequence selection and pre-inference verification

### 1.1 Selected sequence

| Item | Value |
|---|---|
| Dataset export | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8` |
| Recording group | `datasetfootage` |
| Frame range | 100–199 inclusive |
| Frame count | 100 consecutive frames |
| Image size | 606 × 1050 (all frames) |
| Source naming | `datasetfootage_mp4-<n>_jpg.rf.<hash>.jpg` |
| Frame IDs used downstream | `datasetfootage-0100` … `datasetfootage-0199` |
| Group size | 504 images, frame numbers 0–503, one contiguous run, no duplicate IDs |
| Group labels | 1,681 boxes, 0 empty label files |
| Split under the fixed grouped split | `valid` for all 504 images |
| LOGO fold 1 | Holds out the entire `datasetfootage` group (504 images, 1,681 boxes) |

The runner verified before inference that:

1. The 100 file names parse to frame numbers 100–199 with no gaps, duplicates
   or out-of-order entries.
2. Every frame belongs to the same prefix (`datasetfootage`), so no two
   recordings are combined.
3. Every frame has an image and a label file.
4. Every frame is assigned to `valid` by the fixed grouped split.
5. All images have the same dimensions.
6. SHA-256 was computed for every image and every label and is stored in the
   JSON `sequence.frames` records.

### 1.2 Physical folder vs. grouped split

Only 23 of the 100 selected frames physically live under `valid/images`; the
other 77 live under `train/images`. This is expected and is not a data leak:

- Roboflow's original export split `datasetfootage` across both physical
  folders (403 images under `train`, 101 under `valid`).
- Phase 3B.1 replaced folder-based splitting with a recording-group split.
  The fixed split assigns the entire `datasetfootage` group to validation
  regardless of its physical folder.
- LOGO fold 1 independently holds out the same entire group.

The sequence is therefore held out **by recording group**, not by physical
folder. The folder counts are reported explicitly so the distinction is not
hidden.

### 1.3 Labels in the selected range

The 100 frames contain 350 labeled boxes:

| Class | Labels |
|---|---:|
| `boxtrain` | 68 |
| `jump-barrier` | 11 |
| `jump-roll-barrier` | 44 |
| `ramp` | 65 |
| `train` | 126 |
| `wall` | 36 |
| **Total** | **350** |

Labels are recorded for provenance and later diagnostics only. This phase does
not compute or claim detection accuracy.

### 1.4 Timestamps

The images carry no source timestamps. Timestamps were synthesized at an
assumed 30 fps:

```text
timestamp_ms(local_index) = local_index * 1000 / 30
frame_interval_ms          = 33.333333333333336
```

The first processed frame is `datasetfootage-0100` at 0 ms; the last is
`datasetfootage-0199` at 3300 ms. This assumption is a known limitation, not a
measurement.

---

## 2. Boundary tolerance investigation

### 2.1 Observation

With the production zero-tolerance rule, the first 10 frames produced 27
post-NMS candidates: 25 accepted and 2 rejected as `out_of_bounds`. The
rejections were boxes whose true edge fell a fraction of a pixel outside the
processed image after letterbox inversion.

### 2.2 Policy tested

| Condition | Decision |
|---|---|
| Inside the viewport, or exactly on the boundary | Accept without clipping |
| Outside by more than 0 and at most 1 px | Accept, clip to the viewport, record both boxes |
| Outside by more than 1 px | Reject as `out_of_bounds` |
| Negative coordinates beyond the tolerance | Reject |
| Degenerate box before clipping | Reject |
| Box that collapses after clipping | Reject |

Every accepted detection now carries:

- `raw_box_pixels` — the coordinates as produced by the detector;
- `clipped_box_pixels` — the coordinates actually used downstream;
- `clip_distance_pixels` — the maximum overflow before clipping.

Clipping is therefore auditable rather than silent. Rejections retain the
original coordinates and the measured overflow in their detail message.

### 2.3 Production behavior is unchanged

`configs/perception_config.yaml` still sets `bounds_tolerance_pixels: 0.0`.
The 1.0 px policy exists only as an in-memory override in this experiment, and
the runner asserts that production remains 0.0. Adopting the policy in
production would be a separate, reviewed configuration change.

### 2.4 Tests added

Six tests were added to `tests/test_perception.py`:

| Test | Coverage |
|---|---|
| `test_exact_viewport_boundary_is_accepted_without_clipping` | Exact boundary |
| `test_subpixel_overflow_is_accepted_and_both_boxes_are_recorded` | Slight overflow, both boxes, clip distance |
| `test_overflow_above_one_pixel_is_rejected_with_original_coordinates` | > 1 px rejection |
| `test_negative_coordinates_beyond_tolerance_are_rejected` | Negative coordinates |
| `test_degenerate_box_is_rejected_before_bounds_handling` | Degenerate before clipping |
| `test_box_that_collapses_after_clipping_is_rejected` | Invalid after clipping |

The full suite passes: **300 passed**.

### 2.5 Behaviour in the replay

- 334 post-NMS candidates.
- 327 accepted.
- 7 rejected, all `out_of_bounds`, with overflow between 1.132 px and 2.808 px.
- 18 accepted boxes clipped on 17 frames; clip distances ranged from
  0.035748 px to 0.939618 px.
- No accepted box exceeded 1.0 px of overflow.

Example clipped detection (`datasetfootage-0102`, `ramp`):

```text
raw     [-0.829859, 292.130960, 207.023758, 603.641077]
clipped [ 0.000000, 292.130960, 207.023758, 603.641077]
clip_distance_pixels = 0.829859
```

Smoke comparison on the same 10 frames:

| Tolerance | Accepted | Rejected | Clipped | Max clip (px) |
|---|---:|---:|---:|---:|
| 0.0 px | 25 | 2 | 0 | 0 |
| 1.0 px | 26 | 1 | 1 | 0.829859 |

The 1.0 px policy recovers only genuine sub-pixel overflows; the remaining
rejection is a real 2.8 px overflow.

---

## 3. Experiment configuration

| Parameter | Value |
|---|---|
| Model | `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` |
| Model SHA-256 | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` |
| SHA verified before session creation | Yes |
| Runtime | ONNX Runtime, `CPUExecutionProvider` |
| Threads | `intra_op_threads = 1` |
| Batch size | 1 |
| Input | 640 × 640 letterbox, RGB, float32 NCHW, values in [0, 1] |
| Output | `[1, 18, 8400]`, 4 box + 14 class scores, no objectness |
| Confidence threshold | 0.426 |
| NMS | External, per class, IoU 0.7 |
| Class map | Identity, 14 classes |
| Bounds tolerance | 1.0 px (experiment only) |
| Tracker | Existing `MultiObjectTracker`, class-aware, IoU 0.3, gate 0.35, max age 2, min hits 2 |
| Temporal encoder | Existing `TemporalSequenceProcessor`, 30 fps interval, gap threshold 100 ms |
| Scheduler | `phase_3c_temporal_scheduler_v1`, max hold 250 ms, pulse gain 0.5, pulse decay 150 ms |
| Simulation | `dt = 0.5 ms`, duration 3300.5 ms, 6,601 steps |
| Background current | 0 pA |
| Noise | 0 pA (`noise_std_pa = 0`) |
| Seed | 20261106 |
| Plasticity | None |
| Connectome | Fixed, 139,255 neurons, 3,732,460 edges |

No implementation of tracking, temporal encoding or simulation was duplicated.
The runner imports and calls the existing components.

---

## 4. Detection results

All 100 frames were processed. Frame `datasetfootage-0100` produced no
accepted detections; the other 99 frames produced at least one.

| Metric | Value |
|---|---:|
| Frames | 100 |
| Decoded boxes above threshold, before NMS | 2,769 |
| Post-NMS candidates | 334 |
| Accepted | 327 |
| Rejected | 7 |
| Clipped | 18 |
| Frames with clipping | 17 |
| Frames with a rejection | 7 |
| Accepted per frame: mean / median / min / max | 3.27 / 3 / 0 / 8 |

Accepted detections by class:

| Class | Accepted |
|---|---:|
| `boxtrain` | 63 |
| `jump-barrier` | 6 |
| `jump-roll-barrier` | 37 |
| `ramp` | 60 |
| `train` | 120 |
| `wall` | 41 |
| **Total** | **327** |

Rejections were all `out_of_bounds`; there were no class, confidence, format or
geometry rejections. Per-frame accepted/rejected records, including original
and clipped coordinates, are in `detection_frames` in the JSON.

Detector timing over 100 calls:

| Stage | Mean (ms) | Median (ms) | p95 (ms) | Min (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|
| Full detector call | 138.087 | 137.994 | 153.463 | 118.982 | 161.278 |
| Preprocessing | 11.147 | 11.073 | 13.367 | 8.221 | 15.373 |
| ONNX `session.run` | 124.914 | 124.988 | 138.764 | 106.049 | 146.156 |
| Decode / NMS / inversion | 2.026 | 1.943 | 3.030 | 1.194 | 4.571 |

The detector-call figure is wall time for preprocessing, inference and
postprocessing, not pure model inference time.

---

## 5. Tracking results

The existing tracker consumed the accepted detections only.

| Metric | Value |
|---|---:|
| Frames | 100 |
| Track IDs created | 46 |
| Track observations | 475 |
| Occluded observations | 106 |
| Tracks lost by end | 42 |
| Duplicate detections suppressed | 0 |
| Frames with no tracks | 1 (`datasetfootage-0100`) |

Track state observations:

| State | Count |
|---|---:|
| Confirmed | 281 |
| Tentative | 46 |
| Occluded | 106 |
| Lost | 42 |
| **Total** | **475** |

Lifecycle observations recorded by the tracker:

| Lifecycle | Count |
|---|---:|
| Appeared | 39 |
| Approaching | 90 |
| Disappeared | 35 |
| Occluded | 87 |
| Persisting | 141 |
| Receding | 11 |
| Uncertain | 72 |
| **Total** | **475** |

Forty-two tracks were lost, but four tracks (IDs 42, 44, 45 and 46) were still
confirmed at the final frame. A track being `occluded` means the tracker
did not associate a detection for the configured number of frames; it is not a
direct observation of occlusion. Each frame's record in `tracking_frames`
contains the frame ID, active track IDs, state counts, created/occluded/lost
track IDs, duplicate count and lifecycle observations.

### ID switches

ID switches cannot be measured. There are no annotated object identities for
these frames, so a tracker-ID change cannot be distinguished from a real object
entering, leaving or being re-detected. Class-aware association also prevents
cross-class switching by construction. Every reported ID is a **tracker ID, not
an object identity**.

---

## 6. Temporal features and events

The existing temporal encoder produced 215 events over 100 frames.

| Event type | Count |
|---|---:|
| `appeared` | 39 |
| `approaching` | 34 |
| `disappeared` | 35 |
| `occluded` | 50 |
| `receding` | 11 |
| `uncertain` | 46 |
| **Total** | **215** |

Events by class:

| Class | Events |
|---|---:|
| `boxtrain` | 39 |
| `jump-barrier` | 7 |
| `jump-roll-barrier` | 24 |
| `ramp` | 44 |
| `train` | 81 |
| `wall` | 20 |
| **Total** | **215** |

Additional temporal facts:

- 43 events were marked as pulses.
- 0 frames were classified as gaps.
- 5 observable lane changes were recorded for tracked objects:
  - track 3 (`train`), lane 0 → 1, frames 4 → 5;
  - track 12 (`boxtrain`), lane 1 → 2, frames 35 → 36;
  - track 13 (`train`), lane 1 → 0, frames 32 → 33;
  - track 31 (`train`), lane 1 → 0, frames 65 → 66;
  - track 38 (`ramp`), lane 2 → 1, frames 79 → 80.
- Per-frame unrepresented tracks ranged from 0 to 6 (mean 2.61), because the
  existing single-object `GameState` can represent at most one obstacle, one
  train and one coin.

These lane changes are changes in the geometric lane assignment of tracked
objects. They are **not** observations of player movement. Relative movement
and obstacle-proximity changes are recorded per track in the JSON
`track_summaries` (distance-proxy deltas, normalized x/y deltas, and
approaching/receding frame counts).

### Final GameState

| Feature | Value | Meaning |
|---|---:|---|
| `player_lane` | 1 | Neutral `PlayerState` default |
| `player_speed` | 0.5 | Neutral `PlayerState` default |
| `jumping` | 0 | Unavailable |
| `rolling` | 0 | Unavailable |
| `obstacle_present` | 0 | No eligible obstacle at the final frame |
| `obstacle_lane` | null | — |
| `obstacle_distance` | null | — |
| `obstacle_type` | null | — |
| `train_present` | 1 | A train was present |
| `train_lane` | 1 | Geometric lane assignment |
| `train_distance` | 0.736249 | Uncalibrated bottom-edge proxy |
| `coin_present` | 0 | Unavailable in the v15 schema |
| `coin_lane` | null | — |
| `coin_distance` | null | — |

The v15 schema has no player class and no coin class. Player lane, speed,
jumping and rolling are therefore neutral defaults, not inferences. Coin
features are unavailable, not observed absent.

---

## 7. Activation scheduling and simulation

### 7.1 Scheduler

| Metric | Value |
|---|---:|
| Frames scheduled | 100 |
| Scheduled samples | 6,601 |
| Horizon | 3,550 ms |
| Stimulated neurons | 138 |
| Active features | 14 |
| Pulse events | 43 |
| Scheduler memory | 160,120 bytes |
| Peak frame current | 9,288.797 pA |
| Peak pulse current | 3,696.218 pA |
| Peak per-neuron current | 200.0 pA |
| Signature SHA-256 | `1c3ab12d2afbc396da9d77215d75c4e397da3909d1767ecec5a9f24cfc608840` |

All 14 features are configured in the scheduler's encoder map. Being listed as
active means the feature has neuron targets, not that an observation existed.
The unavailable player channels still carry the neutral `PlayerState` defaults,
and those defaults were actually scheduled: `player_lane` contributed a
constant 800 pA and `player_speed` a constant 1,096.361 pA. The simulated
sensory current is therefore not purely visual. The coin channels carried zero
values and contributed no current.

### 7.2 Simulation

| Metric | Value |
|---|---:|
| Duration | 3,300.5 ms |
| Steps | 6,601 (`dt = 0.5 ms`) |
| Wall runtime | 80.57 s |
| Throughput | 81.93 steps/s |
| Neurons | 139,255 |
| Edges | 3,732,460 |
| Excitatory / inhibitory edges | 2,955,795 / 776,665 |
| Excitatory / inhibitory neurons | 123,238 / 16,017 |
| Effective delay | 1.0 ms |
| Spike transmissions | 996,524,829 |
| Total spikes | 15,654,631 |

Activity:

| Metric | Value |
|---|---:|
| Active neurons | 35,979 |
| Silent neurons | 103,276 |
| Active fraction | 0.258368 (25.84%) |
| Mean rate | 34.0606 Hz |
| Population rate | 33.9628 Hz |
| Population-rate peak | 37.0184 Hz |
| Median neuron rate | 0.0 Hz |
| 90th / 95th / 99th percentile rate | 123.31 / 231.18 / 461.14 Hz |
| Max neuron rate | 469.63 Hz |

Diagnostics: `finite_state = true`, membrane potential in
[−90.0, −50.0] mV, maximum absolute total current 178,691.05 pA.

### 7.3 Stimulated vs. non-stimulated activity

| Metric | Value |
|---|---:|
| Stimulated neurons | 138 |
| Stimulated neurons that spiked | 72 |
| Stimulated active fraction | 0.521739 (52.17%) |
| Stimulated spikes | 3,710 |
| Non-stimulated neurons that spiked | 35,907 |
| Non-stimulated spikes | 15,650,921 |
| Non-stimulated spike fraction | 0.999763 (99.976%) |
| Stimulated-neuron fraction of the connectome | 0.000237 (0.024%) |

This is the central scientific caveat of the replay. The network has a high
baseline level of activity under the configured dynamics, and almost all spikes
come from neurons that were not targeted by the sensory scheduler. The data
show that the stimulus reaches the configured targets; they do **not** show
that network activity is driven by, or encodes, the visual sequence. Only 72 of
138 stimulated neurons spiked at all during the 3.3 s window.

No plasticity was used. No action was selected. The chain ends at sensory
current injection.

---

## 8. Reproducibility

Two full runs each created a new ONNX session, perception pipeline, tracker,
temporal encoder, scheduler and simulator from the same inputs, configuration
and seed.

| Artifact | Run A | Run B | Identical |
|---|---|---|---|
| Detections SHA-256 | `8719fb3f70cd0ea7274ebe0b2afd9f90251664d5f57336594bc4ffc580862e9b` | same | Yes |
| Temporal SHA-256 | `2a85747165f9833f73a0c5f85af5a7966b23ecc007f530a7dbc8ba8303229166` | same | Yes |
| Scheduler SHA-256 | `1c3ab12d2afbc396da9d77215d75c4e397da3909d1767ecec5a9f24cfc608840` | same | Yes |
| Spike-counts SHA-256 | `09611c7dc5c37d435f7713f5b0ce42b9ab90bdf2b12efeb6c91125b0e0978305` | same | Yes |
| Total spikes | 15,654,631 | 15,654,631 | Yes |

`reproducibility.identical = true`, with an empty differences list. Run-to-run
wall time is not expected to be identical; it was 80.57 s and 72.27 s for the
two simulations.

The 12 experiment checks all pass: sequence contiguous, all frames in the
validation split, single recording, model SHA verified, production tolerance
unchanged, no accepted box beyond tolerance, every rejected box beyond
tolerance, all frames processed, scheduler targets mapped neurons, simulation
finite, simulation within spike-recorder capacity, and runs identical.

---

## 9. Runtime and memory

| Metric | Value |
|---|---:|
| Total experiment wall time (two full runs plus smoke) | 188.117 s |
| Detection wall time, 100 frames at 138.087 ms mean | ≈ 13.8 s per run |
| Simulation wall time, run A / run B | 80.57 s / 72.27 s |
| RSS before simulation | 366.359 MB |
| RSS after simulation | 530.156 MB |
| RSS delta | +163.797 MB |
| Retained simulator arrays | 341,276,476 bytes (325.47 MB) |
| Graph arrays | 66,264,361 bytes (63.19 MB) |
| Neuron state | 1,671,060 bytes (1.59 MB) |
| Synapse state | 33,341,055 bytes (31.80 MB) |
| Delay buffers | 2,228,080 bytes (2.12 MB) |
| Spike recorder capacity | 30,000,000 spikes / 240,000,000 bytes |
| Worst-case propagation temporary memory | 48,131,640 bytes (45.90 MB) |

The spike recorder capacity was raised for this experiment because the real
sequence produces substantially more activity than the 10-frame scripted
integration. It is an experiment setting, not a production default. The
recorded total (15.65 million spikes) remained within the 30 million capacity.

Environment: Python 3.13.14, NumPy 2.3.4, Windows 11 (10.0.26200), CPU
execution.

---

## 10. Files created and modified

Created:

1. `experiments/phase_3b/real_sequence_replay.py` — the replay runner.
2. `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` — full
   two-run evidence, including per-frame detection and tracking records.
3. `experiments/phase_3b/results/phase_3b2c_smoke.json` — 10-frame, 0.0 px and
   1.0 px tolerance evidence.
4. `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md` (this report).

Modified:

1. `perception/detection.py` — records raw box, clipped box and clip distance.
2. `tests/test_perception.py` — six boundary-tolerance tests.
3. `perception/temporal.py` — exposes per-frame created, occluded, lost and
   duplicate records in `TemporalFrame`.

Not modified: root `README.md`, datasets, annotations, connectome, model
weights, `configs/perception_config.yaml`, or any existing tracking, temporal
encoding or simulator implementation.

---

## 11. Known limitations

1. **Engineering integration only.** No gameplay success or biological
   perception is claimed.
2. **Synthetic timestamps.** The images have no timestamps; 30 fps is assumed.
   Temporal rates and event timing depend on that assumption.
3. **No independent test set.** The sequence is held out by recording group in
   the fixed split and LOGO fold 1, but the detector was trained on the same
   recording groups. The physical folder distribution (23 valid / 77 train)
   does not match the grouped assignment; the grouped split is authoritative.
4. **No annotated identities.** Tracker IDs are not object identities, and ID
   switches are not measurable.
5. **Unavailable modalities.** The v15 schema has no player or coin class.
   Player lane and speed are neutral defaults; jumping, rolling and coins are
   unavailable and are not inferred. The neutral player defaults were still
   scheduled and injected constant current, so the simulation input is not
   purely visual.
6. **Geometric semantics.** Lane assignment is image geometry without
   perspective modeling. Distance is an uncalibrated bottom-edge proxy, not
   metres.
7. **Occlusion is inferred** from missed associations, not observed directly.
8. **High baseline network activity.** 99.976% of spikes came from
   non-stimulated neurons, and only 72 of 138 stimulated neurons spiked. This
   replay does not establish stimulus-driven coding.
9. **Fixed connectome, no plasticity, no action selection.** Spikes are model
   output under the configured dynamics, not measured biological activity.
10. **Boundary policy not promoted to production.** The 1.0 px tolerance is an
    in-memory experiment setting; production remains at 0.0 px.
11. **Thresholds not recalibrated.** Confidence 0.426 and NMS IoU 0.7 are
    carried over from the deployment config produced in the training notebook;
    this phase did not tune them.
12. **Single-object state.** The existing `GameState` represents at most one
    obstacle, train and coin. Up to 6 eligible tracks per frame were counted
    as unrepresented rather than silently dropped.
13. **Experiment spike capacity.** The 30 million spike recorder is larger than
    would be needed for short integration checks; memory figures reflect that
    setting.

---

## 12. Final verdict

**PASS WITH LIMITATIONS**

The experiment meets its engineering objective:

- one contiguous, single-recording, group-held-out 100-frame sequence was
  verified before inference;
- the trained ONNX model was SHA-verified and run on CPU with batch size 1;
- the sub-pixel boundary policy was tested and applied without changing
  production behavior, with both raw and clipped coordinates retained;
- all 100 frames moved through the existing perception, tracking, temporal
  encoding, scheduling and simulation components without duplicate
  implementations;
- two runs produced identical detection, temporal, scheduler and spike
  hashes;
- all 12 checks passed and the full test suite passed (300 tests).

The limitations above prevent stronger claims. In particular, the very high
non-stimulated spike fraction means this replay is evidence of a working,
deterministic pipeline, not evidence that the connectome represents the visual
sequence.
