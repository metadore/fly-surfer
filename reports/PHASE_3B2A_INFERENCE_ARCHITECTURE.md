# Phase 3B.2A — Visual Perception Inference Architecture

**Status:** architecture and plumbing implemented; no detector has been trained
or integrated. Nothing in this phase performs visual recognition, and no
accuracy is reported.

**Scope:** convert one Subway Surfers screenshot into the existing Phase 3A
`GameState`, while keeping image processing independent of the connectome
simulator.

---

## 1. Architecture and module responsibilities

A new standalone package `perception/` separates the pipeline into modules
with one responsibility each.

| Module | Responsibility |
| --- | --- |
| `perception/config.py` | Typed configuration: preprocessing, validation, three-lane geometry, distance policy, detector class schema. Rejects malformed values at load time. |
| `perception/image.py` | `ImageFrame`, `ImagePreprocessor`. Loads an image, applies optional crop/resize, and retains the transform between processed, screen and viewport coordinates. |
| `perception/geometry.py` | `BoundingBox` (screen pixels) and `NormalizedBox` (viewport fractions) as separate types; `bottom_edge_distance` proxy. |
| `perception/detection.py` | Untrusted `RawDetection`, validated `Detection`, `RejectedDetection`, `ValidationResult`, `DetectionValidator`. |
| `perception/detector.py` | `Detector` protocol for future models; `MockDetector`, explicitly labelled test-only. |
| `perception/lanes.py` | `LaneAssigner` and `LaneAssignment`: configurable boundaries, per-lane overlap fractions, majority rule, explicit ambiguity. |
| `perception/scene.py` | `PerceivedScene`, `SceneObject`, `LaneOccupancy`, `ModalityAvailability`, `SceneUncertainty`, `SceneBuilder`. |
| `perception/game_state_adapter.py` | `GameStateAdapter`: builds the existing Phase 3A `GameState` and records assumptions, estimated fields and unrepresented objects. |
| `perception/manifest.py` | Exact lookup in `reports/PHASE_3B1_SPLIT_MANIFEST.json` by filename group. No train/valid folder inference and no fallback. |
| `perception/pipeline.py` | `PerceptionPipeline`, `PerceptionResult`: orchestration and JSON-safe audit output. |
| `perception/__init__.py` | Public exports. |

`PerceivedScene` carries detected obstacles, trains, coins, player information,
per-lane occupancy, uncertainty counts, rejection records, the frame identifier
and timestamp, and original/viewport sizes.

A validated `Detection` contains class ID, class name, confidence, screen
coordinates, normalized coordinates, box centre and dimensions in both
coordinate systems, role, GameState role, clamping metadata and raw index.

## 2. Data flow

```
screenshot
  -> ImagePreprocessor
       ImageFrame: processed pixels + crop/resize transform
  -> Detector.detect(frame)
       RawDetection records in processed-image pixels (untrusted)
  -> coerce_raw_detections + DetectionValidator
       class/name/confidence/bounds checks
       accepted Detection: screen Box + NormalizedBox
       rejected reasons retained
  -> LaneAssigner
       per-lane overlap fractions, lane or explicit None, ambiguity flag
  -> SceneBuilder
       PerceivedScene: objects, occupancy, modalities, uncertainty
  -> GameStateAdapter
       GameStateConversion: existing GameState + assumptions + warnings
  -> JSON / caller
```

Perception imports `sensory.game_state` for the schema only. It does not import
`brain.brain_simulator`, does not construct a simulator, and has no scheduler
or neural-mapping dependency.

## 3. Existing components reused

- **Phase 3A `GameState`** (`sensory/game_state.py`) is used unchanged:
  `PlayerState`, `ObstacleState`, `TrainState`, `CoinState`, `Lane`,
  `ObstacleType` and the 0-near/1-far distance convention. Its validation was
  not relaxed.
- **Phase 3A encoders/mapping/scheduler** were inspected and left untouched.
  `GameState.features()` remains the interface for any later encoding step.
- **Phase 3A.5 calibration configuration** was inspected and is not used by the
  perception package.
- **Phase 3B.0/3B.1 audit and curation scripts** were inspected; their output
  report and manifest are read-only inputs.
- **v15 `data.yaml`** supplied the 14 class names and IDs copied into
  `configs/perception_config.yaml`.
- **`reports/PHASE_3B1_SPLIT_MANIFEST.json`** is the only split source.
- **Pillow 12.0.0**, NumPy and PyYAML were already installed. No functionality
  was duplicated from the Phase 3A scheduler, encoders or mapping.

## 4. New files created

| File | Lines |
| --- | ---: |
| `perception/__init__.py` | 96 |
| `perception/config.py` | 458 |
| `perception/geometry.py` | 130 |
| `perception/image.py` | 199 |
| `perception/detection.py` | 455 |
| `perception/detector.py` | 125 |
| `perception/lanes.py` | 126 |
| `perception/scene.py` | 323 |
| `perception/game_state_adapter.py` | 350 |
| `perception/manifest.py` | 227 |
| `perception/pipeline.py` | 162 |
| `configs/perception_config.yaml` | 68 |
| `experiments/phase_3b/run_inference.py` | 150 |
| `tests/test_perception.py` | 575 |
| `reports/PHASE_3B2A_INFERENCE_ARCHITECTURE.md` | this report |

All 14 v15 classes are configured. Name-derived roles follow the Phase 3B.1
curation policy (`collision_low`, `collision_overhead`, `terrain`, `boundary`,
`powerup`), which remains a hypothesis rather than verified game mechanics.
`player_class_ids` and `coin_class_ids` are empty because v15 labels neither.

## 5. Tests and results

```text
python -m pytest tests/test_perception.py -q
38 passed in 0.54s

python -m pytest -q
158 passed in 4.04s
```

The suite was 120 tests before this phase; 38 perception tests were added and
all existing Phase 3A/3A.5/3B.1 tests still pass. Test fixtures are synthetic
Pillow images generated in memory. No Roboflow image or label is used as a
validation input.

Required coverage and where it is tested:

| Requirement | Test(s) |
| --- | --- |
| Image preprocessing | crop/resize transform, viewport mapping, missing/corrupt files |
| Valid and invalid bounding boxes | valid roles/coordinates; reversed, NaN, out-of-bounds, tiny boxes |
| Confidence filtering | inclusive threshold; out-of-range rejection |
| Class mapping | ID 0, unknown ID, name mismatch, non-integer ID, v15 ID/name order |
| Lane assignment | left/center/right, boundary behavior, majority rule |
| Overlapping objects | two objects in one lane counted separately |
| Ambiguous lane assignments | majority-but-ambiguous and straddling/unassigned |
| Missing player detection | schema-unavailable, supported-but-absent, multi-player |
| Missing coin detection | schema-unavailable, supported-but-absent, detected coin |
| Empty detection results | empty scene, unoccupied lanes, neutral objects |
| GameState conversion | nearest object, unsupported/uncertain objects, time, distance mode `none`, defaults |
| Deterministic mock detector | repeated calls, pixel independence, frame-keyed records |
| Curation manifest | group-derived split, exclusions, unknown-group refusal |
| Simulator independence | no `brain_simulator` import in any perception module |

## 6. Known limitations

- **No trained detector and no recognition claim.** `MockDetector` ignores
  pixels. Every scripted detection is test input, not a prediction.
- **No accuracy measurement.** There is no precision, recall, mAP or per-class
  evaluation; that requires an integrated detector and the curated valid split.
- **v15 does not label player, coins, lanes or metric distance.** Player and
  coin modalities are therefore unavailable by default and are reported as
  such. Missing player information falls back to documented `PlayerState`
  defaults and is listed in `estimated_fields` and `warnings`; it is never
  claimed as observed.
- **Player speed, jumping and rolling are never observed** from a single frame.
  They always use schema defaults and are always reported as estimated.
- **Lane assignment is geometric.** Horizontal overlap is used; perspective,
  camera motion, occlusion and 3D track geometry are not modelled. Uniform
  boundaries are configurable but not calibrated to the game camera.
- **Distance is an uncalibrated proxy.** `bottom_edge_proxy` maps box bottom
  position between the frame bottom and a horizon fraction. It is not a metric
  or in-game distance.
- **Single-object schema.** `GameState` holds at most one obstacle, train and
  coin. Only the nearest candidate of each kind is represented; others are
  recorded in `unrepresented`.
- **Single-frame only.** There is no temporal association or tracking; that is
  outside 3B.2A.
- **Class roles are name-derived hypotheses**, consistent with Phase 3B.1, not
  verified mechanics.
- **Pillow is imported directly but declared only transitively** through
  matplotlib. `requirements.txt` was not changed; this is flagged for a future
  dependency decision.
- **Excluded images are blocked by default.** The CLI refuses an image that the
  curation manifest excludes unless `--allow-excluded` is passed explicitly.

## 7. Future detector integration requirements

1. Implement the `Detector` protocol: `detect(frame: ImageFrame) -> sequence of
   records in processed-image pixels` and `describe() -> mapping`.
2. Declare `test_only: false` and a real name in `describe()`.
3. Match detector class IDs and names to `configs/perception_config.yaml`, or
   update the schema deliberately; every mismatch is rejected, never remapped.
4. Resolve weights licensing, storage location and any new dependency with
   explicit approval before installation or download. Do not commit weights.
5. Evaluate only on the curated manifest split, group-held-out, excluding
   quarantined images. Never use the Roboflow `train`/`valid` folder as the
   split source.
6. Report per-class detection counts and failures, including classes with no
   valid boxes (`boots-powerup`, `jump-electric`).
7. Calibrate lane boundaries and the distance policy for the actual capture
   geometry before using `GameState` values as experimental input.
8. Add temporal association before claiming scene continuity, and only then
   consider connecting perception to the simulator.
9. Keep `MockDetector` and scripted fixtures for deterministic tests; never
   present their output as model accuracy.

## 8. Confirmation that raw data and protected files remain unchanged

| Check | Result |
| --- | --- |
| Root `README.md` SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` — matches the required value |
| `references/` | no working-tree changes (`git status` empty for the path) |
| Raw v15 dataset | read-only in code; no images, labels, YAML or metadata written |
| v15 `data.yaml` SHA-256 | `f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423` |
| Validated connectome artifact SHA-256 | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` (`datasets/processed/connectome.npz`) |
| Phase 3A retraining/recalibration | none; existing tests pass |
| Simulator integration | none; `tests/test_perception.py` asserts no perception module imports `brain_simulator` |
| Dependencies | none added; `requirements.txt` unchanged |
| GPL-derived code | none copied; implementation is original |
| Git commit/staging | none performed |

Working-tree status at verification (the uncommitted Phase 3A/3A.5/3B.0/3B.1
work predates 3B.2A; 3B.2A added the untracked `perception/` package,
`configs/perception_config.yaml`, the CLI, the test file and this report):

```text
 M .gitignore
 M brain/brain_simulator.py
 M sensory/game_state.py
?? configs/perception_config.yaml
?? configs/phase_3b1_curation.yaml
?? configs/sensory_calibration.yaml
?? configs/sensory_config.yaml
?? docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md
?? docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md
?? docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md
?? docs/PHASE_3_ROADMAP.md
?? docs/PHASE_3_SENSORY_ENCODING.md
?? docs/RESEARCH_REFERENCE_REVIEW.md
?? experiments/phase_3/
?? experiments/phase_3_5/
?? experiments/phase_3b/
?? perception/
?? reports/
?? sensory/input_scheduler.py
?? sensory/population_encoder.py
?? sensory/sensory_experiment.py
?? sensory/sensory_mapping.py
?? tests/test_calibration.py
?? tests/test_curation.py
?? tests/test_game_state.py
?? tests/test_input_scheduler.py
?? tests/test_perception.py
?? tests/test_population_encoder.py
?? tests/test_sensory_experiment.py
?? tests/test_sensory_mapping.py
```

`git diff --stat` for the three modified tracked files:

```text
 .gitignore               |   3 +
 brain/brain_simulator.py |  28 +++++
 sensory/game_state.py    | 285 ++++++++++++++++++++++++++++++++++++++++++++++-
```

No commits or staging were performed.

---

## Dependency changes

None. No package was installed or upgraded. Existing versions used:

```text
Pillow 12.0.0
numpy 2.3.4
PyYAML 6.0.3
```

Pillow was already present as a matplotlib dependency and is available in the
current environment, but it is not declared directly in `requirements.txt`;
adding that declaration is left for approval rather than done silently.

## Exact commands for a sample inference run

The commands below use a synthetic image outside the dataset. They exercise the
full plumbing and must not be interpreted as recognition results.

```bash
cd C:/Users/Hp/fruitfly/FLY-SURFER

TMPD=$(mktemp -d)

python - "$TMPD" <<'PY'
import json, sys
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1])
Image.new("RGB", (360, 720), (12, 18, 30)).save(root / "synthetic_screenshot.png")
json.dump(
    [
        {"class_id": 11, "class_name": "train", "confidence": 0.91,
         "bbox": [130, 120, 230, 330]},
        {"class_id": 2, "class_name": "jump-barrier", "confidence": 0.77,
         "bbox": [20, 420, 100, 500]},
        {"class_id": 7, "class_name": "ledge", "confidence": 0.66,
         "bbox": [280, 380, 350, 450]},
    ],
    open(root / "scripted_predictions.json", "w"),
)
PY

# Scripted detections through the real validation/scene/GameState code.
python experiments/phase_3b/run_inference.py \
  --image "$TMPD/synthetic_screenshot.png" \
  --predictions "$TMPD/scripted_predictions.json" \
  --output "$TMPD/inference.json"

# No detector integrated: empty detection list, explicit non-recognition output.
python experiments/phase_3b/run_inference.py \
  --image "$TMPD/synthetic_screenshot.png" \
  --output "$TMPD/inference_empty.json"
```

A curated image can be passed instead. Its split is read from the manifest:

```bash
python experiments/phase_3b/run_inference.py \
  --image "datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8/valid/images/<curated-image>.jpg" \
  --output experiments/phase_3b/inference.json
```

Without `--predictions` the output reports `"mode": "empty_no_detector"`, an
empty scene and the explicit claim that no trained detector is integrated. With
`--predictions`, the output reports `"mode": "scripted_predictions"` and the
detector description keeps `"test_only": true`.

Run the tests with:

```bash
python -m pytest tests/test_perception.py -q
python -m pytest -q
```
