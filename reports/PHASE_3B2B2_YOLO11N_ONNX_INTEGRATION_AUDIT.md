# Phase 3B.2B.2 — Trained YOLO11n ONNX Integration Audit

**Audit date:** 2026-11-06
**Scope:** Read-only audit of the existing perception/detector implementation and a precise integration plan for the trained YOLO11n deployment artifact.
**Verdict:** **READY WITH FIXES**

This audit did not implement the integration, install or upgrade packages, change configuration, modify tests, modify the dataset or connectome, or write/stage/commit anything except this report. The `.pt` checkpoint was never loaded or executed. The ONNX artifact was opened read-only with ONNX Runtime for metadata inspection and one synthetic (non-dataset) input to verify the output contract. No dataset-wide inference was run.

---

## 1. Executive verdict

**READY WITH FIXES.**

The existing ONNX Runtime backend is structurally compatible with the trained YOLO11n model and can be reused without rewriting the detector, decoder, NMS, coordinate transform, validator, scene builder, GameState adapter, or evaluation harness.

The integration is not yet "ready" because:

1. `configs/detector_config.yaml` still declares a 416×416 input and an objectness field; the deployed model is 640×640 with no objectness.
2. The committed detector config has no model path or model hash, and `run_inference.py` has no model mode.
3. `onnxruntime` is installed locally but is not declared in `requirements.txt`; `Pillow` is also imported but undeclared.
4. Several user-facing claims still say "no trained detector is integrated" and `PerceptionPipeline.describe()` hardcodes `visual_recognition_available: False`.
5. The evaluation `--model` path bypasses `DetectionValidator`, so its metrics can include detections that the production pipeline would reject.
6. The threshold and NMS policy (0.25/0.45 in config versus 0.426/0.7 in `model_config.json`) has not been decided explicitly.
7. Tests still assert the old 416×416 default and do not cover the actual `[1, 18, 8400]` contract.

None of these is an architectural blocker. They are configuration, dependency-declaration, CLI, truthfulness, evaluation-consistency, and test gaps.

**Do not start implementation until the user explicitly approves these findings.**

---

## 2. Actual existing architecture

The perception package is already layered and injectable:

```text
image file
  -> ImagePreprocessor / ImageFrame          (crop, resize, coordinate transform)
  -> Detector protocol                       (MockDetector or OnnxRuntimeDetector)
  -> RawDetection                            (untrusted, processed-image pixels)
  -> DetectionValidator                      (class, confidence, geometry, bounds)
  -> ValidationResult                        (accepted + rejected with reasons)
  -> SceneBuilder / LaneAssigner             (normalized boxes -> lanes)
  -> PerceivedScene                          (objects, occupancy, modality, uncertainty)
  -> GameStateAdapter                        (existing Phase 3A GameState)
  -> ObservationBuilder / SpatialFeatureBridge
  -> tracking / temporal / scheduler
```

Key properties:

| Component | Existing behavior |
|---|---|
| `perception/detector.py` | `Detector` protocol requires `detect(frame)` and `describe()`. `MockDetector` is deterministic and test-only. |
| `perception/pipeline.py` | `PerceptionPipeline` accepts any object with a callable `detect`; no architecture change is needed to inject an ONNX detector. |
| `perception/inference.py` | `OnnxRuntimeDetector` already exists, with letterbox, decoding, NMS, class mapping, SHA-256 verification, and lazy `onnxruntime` import. |
| `perception/detection.py` | `DetectionValidator` is the single trust boundary for detector output. |
| `perception/image.py` | `ImageFrame` owns the processed-image to screen-pixel to normalized-viewport transform. |
| `perception/evaluation.py` | Model-agnostic metrics; explicit zero-support handling; grouped-validation limitations in notes. |
| `experiments/phase_3b/evaluate_detector.py` | Already has a `--model` path that constructs `OnnxRuntimeDetector`. |
| `experiments/phase_3b/run_inference.py` | Scripted/mock only; no model mode. |
| Connectome | The perception package never imports the simulator. |

The pipeline already supports:

- injection of a real detector without changing `PerceptionPipeline`;
- scripted detections via `MockDetector` or the `detections=` override;
- fail-fast missing-model behavior (`model_path is None` or file absent);
- lazy `onnxruntime` import (module import does not load ORT or weights);
- deterministic NMS and deterministic validation order.

---

## 3. Existing ONNX backend audit

### 3.1 `OnnxRuntimeDetector`

`perception/inference.py:467` implements the detector.

| Concern | Implementation | Audit result |
|---|---|---|
| Model required | Raises `DetectorConfigError` if `model_path` is `None` or the file is absent | Correct and explicit |
| Hash verification | SHA-256 computed over the file; optional expected hash check | Correct |
| ORT import | Imported inside `__init__`, not at module import | Lazy and safe |
| Session options | `intra_op_num_threads` from config | CPU-friendly |
| Providers | `providers` from config, default `CPUExecutionProvider` | Correct for this environment |
| Input | Uses the first declared model input | Sufficient for this single-input model |
| Class count | `len(class_id_map)` if non-empty, else `len(schema.classes)` | Correct when schema has 14 classes and map is empty or identity |
| Output layout | `yolo_raw`, `boxes_scores`, `nanodet_plus` | `yolo_raw` is the correct family for this model |
| Description | Reports path, hash, input size, layout, providers, class names, thresholds, timing | Useful; one stale note discussed below |

### 3.2 `detect()` flow

`perception/inference.py:552` does:

1. `prepare_input(frame, config)` — RGB, `/255`, letterbox to `input_size`, NCHW, batch 1, float32.
2. `session.run(...)`.
3. `_decode(outputs)`.
4. Confidence mask.
5. `batched_nms(...)`.
6. Map model class index to schema class ID.
7. Invert the letterbox transform to processed-image pixels.
8. Return `RawDetection` values (still untrusted).

This is the correct order. The validator and scene builder remain downstream.

### 3.3 Decoder

`decode_yolo_raw` (`perception/inference.py:273`) already supports both `[cx, cy, w, h, obj?, classes...]` and `[cx, cy, w, h, classes...]`:

```python
class_offset = 5 if config.has_objectness else 4
expected = class_offset + num_model_classes
array = _columns(array, expected, "yolo_raw output")
...
objectness = array[:, 4] if config.has_objectness else np.ones(array.shape[0])
class_scores = array[:, class_offset:]
class_indices = np.argmax(class_scores, axis=1)
scores = objectness * best_scores
```

`_columns` accepts either `(N, expected)` or `(expected, N)` and transposes the latter. For the actual output `[1, 18, 8400]`:

- `_squeeze_predictions` removes the batch axis → `(18, 8400)`;
- `has_objectness=False` → `expected = 4 + 14 = 18`;
- `_columns` sees `array.shape[0] == 18` and transposes → `(8400, 18)`.

That is exactly the required orientation. No decoder rewrite is required.

### 3.4 NMS

`batched_nms` (`perception/inference.py:194`) performs per-class NMS, then a global score-ordered cap at `max_detections`. This matches the usual Ultralytics default (`agnostic_nms=False`, `max_det=300`).

Consequence: overlapping boxes of different classes are not suppressed against each other. This is expected and is consistent with the class-aware evaluation protocol, but it must be documented. If class-agnostic NMS is ever desired, it should be an explicit, evaluated option, not a silent change.

### 3.5 Preprocessing and coordinate inversion

`prepare_input` (`perception/inference.py:122`) and `fit_image` (`perception/inference.py:80`) implement:

- RGB conversion;
- letterbox with `pad_value=114`;
- bilinear resize;
- float32 `/255`;
- HWC → CHW → NCHW with batch 1.

`LetterboxTransform.to_source` inverts the letterbox, then `ImageFrame.processed_box_to_screen` and `ImageFrame.screen_box_to_normalized` map to screen pixels and viewport fractions. This matches the model export assumptions and the existing dataset normalization when preprocessing crop/resize is disabled (the current `perception_config.yaml` disables both).

### 3.6 Backend weaknesses found

| Weakness | Impact | Recommended fix |
|---|---|---|
| No validation of ONNX metadata class names | A silently reordered model would map wrong names | Compare `session.get_modelmeta().custom_metadata_map["names"]` with the schema; fail or warn |
| `class_activation` is not applied by `decode_yolo_raw` | Config says `sigmoid`, but the graph already applies it; future code could double-activate | Set `class_activation: none` and document that `yolo_raw` treats scores as already activated |
| `last_inference_ms` covers preprocessing + inference + decode + NMS | Not comparable to Colab's inference-only 135.4 ms | Rename or add per-stage timings in the implementation phase |
| No model mode in `run_inference.py` | Cannot exercise the real detector through the CLI | Add `--model` / `--model-path` |
| Relative `model_path` depends on the current working directory | Running from another directory fails | Resolve relative to repository root or require an explicit override |
| Detector output is not passed through `DetectionValidator` in `evaluate_detector.py --model` | Metrics may include boxes the production pipeline rejects | Apply the validator in the evaluation path or explicitly label metrics as pre-validation |
| No explicit class map | Empty map means identity; correct now, but relies on matching order | Set explicit `[0..13]` and/or validate metadata |

---

## 4. Exact comparison: current implementation vs actual YOLO11n contract

The actual ONNX artifact was inspected read-only with ONNX Runtime 1.29.0. Model metadata:

| Item | Actual value |
|---|---|
| Producer | `pytorch` |
| Ultralytics version | `8.4.202` |
| Task | `detect` |
| Input | `images [1, 3, 640, 640] tensor(float)` |
| Output | `output0 [1, 18, 8400] tensor(float)` |
| `imgsz` | `[640, 640]` |
| `stride` | `32` |
| `batch` | `1` |
| `end2end` | `False` |
| `nms` | `None` |
| `opset` | `17` |
| `names` | `{0: 'boots-powerup', 1: 'boxtrain', 2: 'jump-barrier', 3: 'jump-electric', 4: 'jump-hedge', 5: 'jump-roll-barrier', 6: 'jump-trash', 7: 'ledge', 8: 'pogstick-powerup', 9: 'ramp', 10: 'roll-barrier', 11: 'train', 12: 'undercover-barrier', 13: 'wall'}` |
| License | `AGPL-3.0` |

Single synthetic-input inspection (zeros and fixed-seed random, not dataset images):

- output shape `(1, 18, 8400)`, dtype `float32`;
- class-score rows 4–17 were within `[0, 1]`, never negative, and per-anchor sums were not 1;
- box rows 0–3 were within `0..640` pixels.

Therefore:

- class scores are already sigmoid-activated in the graph;
- boxes are `cx, cy, w, h` in input pixels;
- there is no objectness row;
- NMS is external.

### Contract comparison

| Contract item | Actual model | Current implementation | Status |
|---|---|---|---|
| Input shape | `[1, 3, 640, 640]` | `prepare_input` builds NCHW batch 1; committed config uses `[416, 416]` | **Config mismatch** |
| Input layout | NCHW | NCHW | Match |
| Color | RGB | RGB conversion in `ImagePreprocessor` and `prepare_input` | Match |
| Data type | float32 | `np.float32` | Match |
| Normalization | `/255` | `/255` | Match |
| Resize | letterbox | `fit_image` letterbox, `pad_value=114` | Match |
| Batch | 1 | Batch 1 | Match |
| Output shape | `[1, 18, 8400]` | `_squeeze_predictions` + `_columns` transpose to `(8400, 18)` | Match |
| Box components | 4 (`cx, cy, w, h`) | First 4 columns decoded as `cxcywh` | Match |
| Box units | input pixels | `box_format: pixels` | Match |
| Class components | 14 scores | Remaining 14 columns | Match |
| Objectness | none | Committed config `has_objectness: true` → expects 19 columns and fails loudly | **Config mismatch** |
| Class activation | already sigmoid | `decode_yolo_raw` does not apply activation; config says `sigmoid` but it is unused for `yolo_raw` | Functionally match; config is misleading |
| NMS | required outside graph | `batched_nms`, per-class, max 300 | Match |
| Class IDs/names | 0–13 exactly as listed | `perception_config.yaml` 0–13 exactly as listed; empty class map is identity | Match; explicit map recommended |
| Threshold policy | `model_config.json` initial 0.426 / IoU 0.7 | Config 0.25 / 0.45 | **Policy decision required** |
| End-to-end flag | `False` | Raw-output decoder | Match |

---

## 5. Identified mismatches

### Required fixes

**M1 — Input size is 416×416 in config.**
`configs/detector_config.yaml:20` declares `input_size: [416, 416]`. The ONNX model requires `640×640`. With the wrong size, ORT will reject the input shape or the letterbox will be wrong. Fix to `[640, 640]`.

**M2 — Objectness is enabled in config.**
`configs/detector_config.yaml:27` declares `has_objectness: true`. The actual output has 18 rows = 4 box + 14 class, no objectness. With `true`, `decode_yolo_raw` expects 19 columns and raises `DetectorOutputError`; the failure is loud, not silent, but it is a blocker until fixed. Set `has_objectness: false`.

**M3 — No model path or hash is configured.**
`configs/detector_config.yaml:17-19` has `model_path: null` and `model_sha256: null`. The deployment artifact exists locally at `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` with SHA-256 `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77`. The implementation phase must supply the path (CLI/local override recommended) and set the expected hash.

**M4 — `class_activation: sigmoid` is misleading.**
The graph already applies sigmoid. `decode_yolo_raw` does not apply `class_activation`; only the NanoDet decoder uses it (`perception/inference.py:410-412`). There is no double activation today, but the config implies an operation that is not performed. Set `class_activation: none` and document that `yolo_raw` scores are already activated; add a guard/test so a future decoder change cannot silently double-sigmoid.

**M5 — `run_inference.py` has no model mode.**
`experiments/phase_3b/run_inference.py:121` always constructs `MockDetector`; `--predictions` only feeds scripted records. The pipeline can already accept a real detector, but the CLI cannot construct one. Add `--model`, `--model-path`, and `--detector-config`, while preserving the scripted path.

**M6 — `PerceptionPipeline.describe()` hardcodes stale claims.**
`perception/pipeline.py:163-164` returns `integrated_with_simulator: False` and `visual_recognition_available: False` unconditionally. Once a real detector is injected, the second claim is false. Derive it from the detector description (for example, `test_only is False` and `weights_loaded is True`) while keeping `integrated_with_simulator` accurate. Also update the stale module docstrings/claims in `perception/pipeline.py`, `perception/__init__.py`, and `run_inference.py`'s `CLAIM` to be conditional rather than blanket statements.

**M7 — `onnxruntime` is undeclared.**
`requirements.txt` does not list `onnxruntime`, although version 1.29.0 is installed locally and the code imports it lazily. `Pillow` is also imported by `perception/image.py` but undeclared (installed 12.0.0). Declare the CPU ONNX Runtime package (and Pillow, if reproducible installs are intended) in the implementation phase. Do not install or upgrade anything during this audit.

**M8 — Evaluation bypasses validation.**
`experiments/phase_3b/evaluate_detector.py:161-179` consumes `detector.detect(frame)` directly and converts boxes, without `DetectionValidator`. The production pipeline may reject out-of-bounds or tiny boxes. This means `--model` metrics and production behavior can diverge. Either run the validator in the evaluation path and record accepted/rejected counts, or explicitly label the metrics as pre-validation and add a second validated-metric block. This is a correctness/clarity requirement, not a model blocker.

**M9 — Tests assert the old contract.**
`tests/test_detector_backend.py:72-80` expects `[416, 416]` and `model_path is None`. It must be updated for 640×640 and no objectness, and new tests must cover the real `[1, 18, 8400]` contract.

### Policy decisions

**M10 — Confidence/NMS thresholds.**
`configs/detector_config.yaml:38-40` uses `confidence_threshold: 0.25`, `nms_iou_threshold: 0.45`, `max_detections: 300`. `model_config.json` records `confidence_threshold_initial: 0.426`, `iou_threshold_initial: 0.7`. Neither pair is inherently wrong; they serve different purposes (evaluation protocol vs deployment initial values). The implementation phase must choose explicitly and record the choice. Keep both configurable; do not hardcode.

**M11 — Bounds tolerance.**
`configs/perception_config.yaml:32` sets `bounds_tolerance_pixels: 0.0`. Letterbox inversion can produce slightly negative or over-size boxes when a detection reaches the padded edge; with zero tolerance those are rejected. Measure the rejection rate on a small sample before changing this. A small tolerance (for example, 2 px) may be appropriate, but it must be an explicit, tested decision.

**M12 — NMS class-awareness.**
`batched_nms` is per-class. Overlapping different classes survive. This matches Ultralytics defaults and class-aware evaluation, but should be documented so cross-class duplicates are not mistaken for a bug. Do not switch to class-agnostic NMS without an evaluated reason.

### Documentation/operational notes

**M13 — Relative model path.**
`OnnxRuntimeDetector` uses `Path(config.model_path)` as-is. A relative path is resolved against the current working directory, not the repository root. `evaluate_detector.py` resolves it before use, but a general CLI should do the same. Prefer an explicit `--model-path` that is resolved against the project root, or document that the config path must be absolute.

**M14 — Preprocess resize.**
`configs/perception_config.yaml` currently has `preprocessing.resize: null` and zero crops. Keep it that way for the first integration: `prepare_input` already letterboxes to 640. Setting `preprocessing.resize` to 640 would resize twice and perturb coordinates.

**M15 — Zero-validation classes.**
`boots-powerup` and `jump-electric` have zero validation examples. The model still has 14 output classes. The evaluation harness already reports zero-support classes as `evaluated: False` and lists them in `unevaluated_classes`. The implementation report must not claim class-specific validation performance for those two classes.

**M16 — Metrics provenance.**
The supplied `metrics_summary.json` values (P 0.9373, R 0.8108, mAP50 0.8978, mAP50-95 0.6877) are grouped-validation ONNX CPU results from the training environment. They are not local Windows results and not independent test-set results. A local re-run may differ.

---

## 6. File-by-file implementation plan

The plan below is for the next phase only. No file was changed in this audit.

| File | Change | Why | Risk |
|---|---|---|---|
| `configs/detector_config.yaml` | Set `input_size: [640, 640]`; `has_objectness: false`; `class_activation: none`; add `model_sha256`; supply model path via CLI or a local override; explicit identity `class_id_map: [0..13]`; decide threshold/IoU policy and document it | Match the actual model contract | Low; wrong values fail loudly |
| `requirements.txt` | Add a pinned CPU `onnxruntime==1.29.0`; optionally add `Pillow==12.0.0` | Make the runtime reproducible; ORT is currently undeclared | Low; do not change installed environment during audit |
| `perception/detector_config.py` | Optional: document that `class_activation` is unused for `yolo_raw`; optional model-path resolution helper; no decoder changes | Reduce configuration ambiguity | Low |
| `perception/inference.py` | Optional: validate ONNX metadata `names` against the schema; add per-stage timing fields; keep `decode_yolo_raw` unchanged | Prevent silent class reordering; make local timings interpretable | Low; metadata validation can be a warning if names are absent |
| `perception/pipeline.py` | Derive `visual_recognition_available` from the detector description; keep `integrated_with_simulator` accurate | Avoid a false claim once a real detector is injected | Low |
| `experiments/phase_3b/run_inference.py` | Add `--model`, `--model-path`, `--detector-config`, optional `--limit`; construct `OnnxRuntimeDetector`; preserve `MockDetector` for scripted mode; make the claim conditional | Exercise the real model through the existing pipeline | Medium; keep scripted behavior unchanged |
| `experiments/phase_3b/evaluate_detector.py` | Apply `DetectionValidator` in `_run_model` (or label metrics as pre-validation); add `--model-path`; add a `--limit` smoke option; separate preprocessing/inference/postprocessing timings; keep zero-support reporting | Align metrics with production validation; enable bounded smoke runs | Medium; metric definition must be explicit |
| `tests/test_detector_backend.py` | Update the default-config test for 640/no-objectness; add `[1,18,8400]` decoding, fake-session no-objectness, SHA mismatch, missing-ORT, and metadata-name tests | Pin the actual contract | Low |
| `tests/test_perception.py` | Add a pipeline-injection test with a fake ONNX detector; assert `test_only`/`visual_recognition_available` behavior; keep MockDetector tests | Prove no architecture change is needed | Low |
| `tests/test_evaluation.py` | Add a detector-path evaluation test and an explicit zero-support assertion for the two unevaluable classes | Keep metrics honest | Low |
| New `tests/test_yolo11_onnx_integration.py` | Real-model metadata/contract test (skip if the ignored artifact is absent); synthetic one-image smoke; class-name/schema comparison; optional actual-output sanity check | Local integration coverage without committing weights | Low; must skip cleanly on machines without `best.onnx` |
| `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` | Next-phase implementation report | Record local results and limitations | Required by the roadmap |

**No changes are expected in:** `perception/image.py`, `perception/detection.py`, `perception/scene.py`, `perception/game_state_adapter.py`, `perception/lanes.py`, `perception/observations.py`, `perception/sensory_bridge.py`, `perception/tracking.py`, `perception/temporal.py`, or any `sensory/`, `brain/`, or connectome code. The existing abstractions already cover the integration.

---

## 7. Required configuration changes

### 7.1 `configs/detector_config.yaml`

| Key | Current | Required / recommended | Reason |
|---|---|---|---|
| `detector.model_path` | `null` | Supply the local ONNX path through `--model-path` or a local deployment override; do not commit weights | `models/` is ignored; a fresh checkout must not silently depend on a missing artifact |
| `detector.model_sha256` | `null` | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | Verify the approved artifact |
| `detector.input_size` | `[416, 416]` | `[640, 640]` | Actual model input |
| `detector.resize_mode` | `letterbox` | Keep `letterbox` | Matches export |
| `detector.pad_value` | `114` | Keep `114` | Matches Ultralytics letterbox |
| `detector.color_order` | `rgb` | Keep `rgb` | Matches export |
| `output.layout` | `yolo_raw` | Keep `yolo_raw` | Raw anchor output |
| `output.has_objectness` | `true` | `false` | 18 columns = 4 + 14 |
| `output.box_format` | `pixels` | Keep `pixels` | Boxes are 0–640 pixels |
| `output.class_activation` | `sigmoid` | `none` (document that the graph already activates) | Avoid implying a second activation |
| `decoding.confidence_threshold` | `0.25` | Keep `0.25` for evaluation parity, or choose `0.426` for deployment; make it explicit | Policy decision |
| `decoding.nms_iou_threshold` | `0.45` | Keep `0.45`, or choose `0.7` to match `model_config.json`; make it explicit | Policy decision |
| `decoding.max_detections` | `300` | Keep `300` | Standard default |
| `decoding.class_id_map` | `[]` | Explicit `[0, 1, ..., 13]` (recommended) | Empty map is identity today, but explicit mapping is self-documenting and guarded |
| `runtime.providers` | `[CPUExecutionProvider]` | Keep CPU only | No CUDA assumed |
| `runtime.intra_op_threads` | `1` | Keep `1` initially; benchmark before changing | Determinism and predictable resource use |

**Model-path strategy:** Do not hardcode a machine-local absolute path in a committed config. Recommended options, in order:

1. Keep `model_path: null` in the committed config and add `--model-path` to the CLIs, resolving relative paths against the repository root.
2. Use a local, untracked deployment config that sets `model_path` to the deployment artifact; never commit the weights.
3. If a committed default is preferred, use a repository-relative path and ensure the error message on a fresh checkout clearly says the local artifact is absent.

### 7.2 `configs/perception_config.yaml`

| Key | Current | Recommendation | Reason |
|---|---|---|---|
| `preprocessing.*` crops | `0.0` | Keep `0.0` | Ground-truth and prediction coordinates remain consistent |
| `preprocessing.resize` | `null` | Keep `null` | Avoid double resizing; detector letterboxes to 640 |
| `validation.confidence_threshold` | `0.25` | Keep, or align with the chosen detector operating point | Two-stage thresholding must be understood |
| `validation.bounds_tolerance_pixels` | `0.0` | Measure edge-box rejections; consider a small tolerance only after evidence | Zero tolerance may reject valid edge detections after letterbox inversion |
| `lanes`, `distance`, `classes` | Current | No change | 0–13 already match the model |

---

## 8. Required dependency changes

| Dependency | Current state | Required change | Notes |
|---|---|---|---|
| `onnxruntime` | Installed 1.29.0; **not declared** in `requirements.txt` | Add a pinned CPU package, e.g. `onnxruntime==1.29.0` | Do not install/upgrade during the audit; no GPU package |
| `Pillow` | Installed 12.0.0; imported by `perception/image.py`; **not declared** | Add a pin if reproducible installs are intended, e.g. `Pillow==12.0.0` | Pre-existing declaration gap, not specific to ONNX |
| `numpy` | Declared `2.3.4`; installed `2.3.4` | No change | ORT 1.29.0 loaded and ran successfully with this version |
| `PyYAML` | Declared `6.0.3` | No change | Used by config loaders |
| `psutil` | Declared `7.1.2` | No change | Used by evaluation memory reporting |
| `torch` | Installed 2.10.0; not needed for ONNX inference | Do not add to runtime requirements | The `.pt` checkpoint must not be loaded |
| `ultralytics` | Not installed; not needed for ONNX inference | Do not add | Export/training dependency only |
| `onnxruntime-gpu` | Not installed | Do not add | No CUDA assumption; CPU provider is the initial backend |

**No package installation or upgrade was performed during this audit.**

---

## 9. Unit and integration tests to add or update

### Update existing tests

1. **`tests/test_detector_backend.py::test_default_config_loads_without_weights`**
   - Expect `input_size == (640, 640)`.
   - Expect `has_objectness is False`.
   - Expect `class_activation == "none"` (or document the chosen value).
   - Keep the assertion that constructing a detector without a path raises explicitly; if the committed config keeps `model_path: null`, retain the "no detector weights" assertion. If the config points at a local artifact, use a temporary config or tolerate "model not found" explicitly.

2. **`tests/test_detector_backend.py::test_decode_yolo_raw_pixels_and_normalized`**
   - Add a case for a `(1, 18, 8400)`-style tensor with 14 classes and `has_objectness=False`.
   - Assert the transpose path and that the score is the best class score, not multiplied by an objectness value.

3. **`tests/test_detector_backend.py::test_detector_end_to_end_with_fake_session`**
   - Add a no-objectness fake session variant with 14 classes and a realistic `(1, 18, N)` output.
   - Assert class mapping, thresholding, NMS, and coordinate inversion.

### New tests

4. **Real-model contract test** (new `tests/test_yolo11_onnx_integration.py`)
   - `pytest.mark.skipif` when `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` is absent.
   - Assert input name/shape `[1, 3, 640, 640]`, output shape `[1, 18, 8400]`.
   - Assert metadata `names` exactly matches `perception_config.yaml` class order (0–13).
   - Assert metadata `imgsz == [640, 640]`, `batch == 1`, `end2end is False`, `nms is None`.
   - Run one fixed synthetic tensor and assert scores in `[0, 1]`, boxes in `[0, 640]`, and no non-finite values. Do not use dataset images.

5. **SHA-256 verification test**
   - With the real artifact (skip if absent), assert the computed digest equals `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77`.
   - With a temporary file and a wrong expected digest, assert `DetectorConfigError`.
   - With a temporary file and a correct digest, assert construction proceeds with a fake session.

6. **Missing-`onnxruntime` test**
   - Monkeypatch the import or run in a subprocess with the module unavailable; assert `DetectorConfigError` with the explicit "onnxruntime is not installed" message.

7. **No-model-load-at-import test**
   - In a subprocess, import `perception.inference` without constructing a detector; assert `onnxruntime` is not imported and the model file is not read. This pins the lazy-init requirement.

8. **Pipeline injection test**
   - Construct `PerceptionPipeline` with a fake ONNX detector (fake session) and run one frame.
   - Assert `validation.accepted` is non-empty, `scene.objects` is populated, `conversion.state` is produced, and `detector.test_only is False`.
   - Assert `PerceptionPipeline.describe()` reports visual recognition truthfully after the describe fix.

9. **Class-map test**
   - Assert the explicit identity map `[0..13]` maps every model index to the same schema class ID.
   - Assert a negative entry (`-1`) drops that class, preserving the existing behavior.

10. **Evaluation-path test**
    - Add a small synthetic test for `evaluate_detector._run_model`-style conversion using a fake detector, asserting:
      - predictions are normalized correctly through the frame transform;
      - if the validator is applied, rejected detections are counted and excluded;
      - zero-support classes are `evaluated: False`;
      - `unevaluated_classes` includes `boots-powerup` and `jump-electric` for the real valid split.
    - Do not run the full 1,128-image validation in unit tests.

11. **Determinism test**
    - Run the same frame through the fake detector twice and assert identical `RawDetection` outputs and identical NMS ordering. CPU ORT determinism should be checked in the smoke test, not asserted across machine architectures.

### Test policy

- Do not weaken or delete existing tests.
- Keep all real-model tests skipped when the ignored ONNX artifact is absent.
- Do not require `torch`, `ultralytics`, or GPU packages in tests.
- Do not add dataset-wide inference to the unit test suite.

---

## 10. Smoke-test procedure

Run only after the implementation phase is approved. The purpose is to prove the wiring and the actual output contract, not to produce final metrics.

### Step 0 — Preflight (read-only)

1. Confirm `README.md` SHA-256 is `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10`.
2. Confirm `best.onnx` SHA-256 is `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77`.
3. Confirm `SHA256SUMS.json` matches the deployment files.
4. Confirm `git status` has no unexpected modifications and `models/` remains ignored.
5. Do not open, load, or execute `best.pt`.

### Step 1 — Import and construction

```bash
python -c "import perception.inference; print('import ok')"
```

- Assert the import does not load ONNX Runtime or the model.
- Construct `OnnxRuntimeDetector` with the local ONNX path and `perception_config.yaml` schema.
- Assert the SHA-256 check passes and the input/output metadata is `[1,3,640,640]` / `[1,18,8400]`.

### Step 2 — One synthetic frame

- Use a synthetic 640×640 or 1280×720 image, not a dataset image.
- Run one detection.
- Assert:
  - no exception;
  - all returned boxes are finite;
  - normalized boxes lie in `[0, 1]` after the frame transform;
  - scores lie in `[0, 1]`;
  - `last_decoded_count` and returned count are consistent;
  - at least the empty case is handled without a crash.

### Step 3 — One curated image

- Run `run_inference.py` on one non-quarantined image.
- Assert the output contains the detector description, accepted detections, scene, GameState conversion, and honest limitations.
- Do not interpret the result as accuracy.

### Step 4 — Small evaluation slice

- Run `evaluate_detector.py --model` on 5–10 validation images first (add `--limit` if needed).
- Assert prediction coverage matches the selected images.
- Check accepted/rejected counts, per-class support, and zero-support classes.
- Do not run the full validation split until the small slice is clean.

### Step 5 — Full grouped validation (only after explicit approval)

- Run on the fixed grouped validation split (1,128 images).
- Record local Windows CPU timings separately from the supplied Colab timings.
- Report per-class results and explicitly mark `boots-powerup` and `jump-electric` as having zero validation support.
- State that these are grouped-validation results, not independent test-set or gameplay-generalization results.

### Stop conditions

- Any shape or dtype mismatch.
- Any class-name/schema mismatch.
- Any non-finite output.
- Any unexpected rejection spike at the bounds check.
- Any model hash mismatch.
- Any attempt to load `.pt`.

---

## 11. Performance and resource risks

| Item | Value / assessment |
|---|---|
| Model size | 10,636,871 bytes (`best.onnx`) |
| Input | `1 × 3 × 640 × 640` float32 |
| Output | `1 × 18 × 8400` float32 (about 0.6 MB before decode) |
| Backend | ONNX Runtime CPU, 1.29.0 |
| Providers | `CPUExecutionProvider` only; no CUDA assumed |
| Supplied Colab timings | preprocess 1.7 ms/image, inference 135.4 ms/image, postprocess 1.2 ms/image |
| Local Windows timings | **Unknown**; must be measured, not assumed |
| `last_inference_ms` semantics | Currently includes preprocessing + inference + decode + NMS; not comparable to inference-only 135.4 ms |
| Batch size | 1; no batching |
| Full validation estimate | 1,128 images × roughly 135 ms ≈ 2.5 minutes of pure inference at Colab speed, plus preprocessing, I/O, and NMS; slower local CPU may take materially longer |
| Memory | Model ~10.6 MB; one image tensor ~4.9 MB at 640×640×3 float32; output/decode ~0.6 MB; NMS arrays modest; bounded at batch 1 |
| NMS cost | 8,400 anchors, thresholded; per-class NMS; worst-case quadratic but small in practice |
| Preprocessing | Pillow resize/crop; one frame at a time |
| Dataset-wide inference | Not permitted in the initial integration; add `--limit` and run a smoke slice first |
| Model load | Lazy at detector construction; module import does not load weights |
| Determinism | CPU ORT and deterministic NMS should be stable on the same machine; do not assume identical floating-point outputs across ORT versions or CPUs |
| Threading | `intra_op_threads=1`; increasing it may improve throughput but can alter timing and determinism; benchmark before changing |
| Disk | The ONNX artifact is ignored and local; do not commit it |

**Risk:** the Colab timings are not local Windows timings. The implementation report must label them as supplied training-environment measurements and report local measurements separately.

---

## 12. Git and artifact safety verification

### Verified hashes

| Artifact | SHA-256 | Status |
|---|---|---|
| `README.md` | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` | Matches required value |
| `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | Matches user-verified value |
| `models/YOLO11/deployment/yolo11n_v1_deployment/best.pt` | `1b47a43325b18c59b52b9a29cdd45c029d079ee134a7283b49cd0e86366bdef8` | Matches user-verified value; never loaded |
| `dataset_attribution.txt` | `5290ac7664c662d71c255ade0edb88e49428e25a14228b81374de47381abfe0d` | Matches `SHA256SUMS.json` |
| `metrics_summary.json` | `57ba3ccb3fe7ffb882109775c3f76c092078f46bf7c9f82065f8b96bb18cd615` | Matches `SHA256SUMS.json` |
| `model_config.json` | `b48710e5dcc1f75cf02fc78920530e9dbeb6a1b15e7e2df2e23a64dadba22a8c` | Matches `SHA256SUMS.json` |
| `reports/PHASE_3B1_SPLIT_MANIFEST.json` | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` | Matches recorded value |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | Matches recorded value |
| `datasets/exports/phase_3b2b1_yolo11n.zip` | `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff` | Matches Phase 3B.2B.1 report |

### Git state

- `git status --porcelain` was clean at audit time.
- No files were staged.
- No commits were created.
- No pushes were made.
- No Git history was modified.
- `models/` is ignored by `.gitignore`; `git ls-files models/` returned nothing, so no model weights are tracked.
- `datasets/exports/phase_3b2b1_yolo11n/` and the ZIP are ignored.
- No weights were staged or committed.
- No `.pt` checkpoint was loaded or executed.

### Protected directories

`datasets/raw/`, `datasets/external/`, `datasets/processed/`, and `references/` were not modified during this audit. `datasets/raw/`, `datasets/external/`, and `datasets/processed/` had modification times from 2026-11-04; `references/` from 2026-11-06 19:56, before this session. The tracked processed artifacts match their recorded hashes and `git status` is clean.

### Package installation

No package installation, upgrade, downgrade, or environment modification was performed. The packages used for inspection (`onnxruntime 1.29.0`, `numpy 2.3.4`, `Pillow 12.0.0`, `PyYAML 6.0.3`, `psutil 7.1.2`, `pytest 7.4.3`, `torch 2.10.0`) were already present. `torch` was not used.

### Files created

Only this report was created:

`reports/PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md`

No JSON report was created.

---

## 13. Explicit list of files that must remain untouched

### Root and documentation

- `README.md` — must remain byte-for-byte identical.
- `REFERENCES.md`
- `THIRD_PARTY_NOTICES.md`
- `GITHUB_PREPARATION_REPORT.md`
- `datasets/README.md`
- Any other README file.

### Datasets and references

- `datasets/raw/**`
- `datasets/external/**`
- `datasets/processed/**` (including `connectome.npz`, `nodes.csv.gz`, `connectome_report.json`)
- `datasets/manifest.json`
- `datasets/exports/phase_3b2b1_yolo11n/**`
- `datasets/exports/phase_3b2b1_yolo11n.zip`
- `reports/PHASE_3B1_SPLIT_MANIFEST.json`
- `references/**`

### Model artifacts

- `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` (read-only until implementation)
- `models/YOLO11/deployment/yolo11n_v1_deployment/best.pt` (must never be loaded/run)
- `models/YOLO11/deployment/yolo11n_v1_deployment/metrics_summary.json`
- `models/YOLO11/deployment/yolo11n_v1_deployment/model_config.json`
- `models/YOLO11/deployment/yolo11n_v1_deployment/dataset_attribution.txt`
- `models/YOLO11/deployment/yolo11n_v1_deployment/SHA256SUMS.json`
- `models/YOLO11/yolo11n.pt` (base checkpoint; must never be loaded/run)
- Any other file under `models/`.

### Connectome and simulator

- `brain/**`
- `sensory/**` (including `sensory/game_state.py`)
- `learning/**`
- `motor/**`
- `datasets/processed/connectome.npz`
- `datasets/processed/nodes.csv.gz`
- `datasets/processed/connectome_report.json`

### Existing code and tests not part of the next phase

- `perception/image.py`
- `perception/detection.py`
- `perception/scene.py`
- `perception/game_state_adapter.py`
- `perception/lanes.py`
- `perception/observations.py`
- `perception/sensory_bridge.py`
- `perception/tracking.py`
- `perception/temporal.py`
- `experiments/phase_3b/export_yolo11_dataset.py`
- `tests/test_export_yolo11.py`
- `tests/test_dataset_interface.py`
- `tests/test_integration_3b_3c.py`
- `tests/test_temporal.py`
- `tests/test_tracking.py`
- `configs/perception_config.yaml` (unless the user approves a specific bounds/resize change)
- `.gitignore`
- `.gitattributes`

### Git

- Existing commits, branches, tags, and remote state.
- No staging, committing, pushing, amending, or force-pushing.

---

## 14. Recommended next implementation phase and acceptance criteria

### Phase 3B.2B.3 — Trained YOLO11n ONNX integration

**Scope:** Wire the approved local `best.onnx` artifact into the existing `OnnxRuntimeDetector` and `PerceptionPipeline`, without changing the perception architecture, dataset, connectome, or evaluation definition.

**Non-goals:**

- Do not load or use `best.pt`.
- Do not install CUDA or `onnxruntime-gpu`.
- Do not run dataset-wide inference before the smoke slice passes.
- Do not claim independent test-set or gameplay-generalization performance.
- Do not claim class-specific validation performance for `boots-powerup` or `jump-electric`.
- Do not change class IDs, class names, or dataset splits.
- Do not commit model weights.

### Acceptance criteria

1. `configs/detector_config.yaml` matches the actual contract: 640×640, no objectness, `class_activation: none`, explicit identity class map, documented threshold/NMS choice.
2. The model path is supplied explicitly (CLI or local override), resolved consistently, and the SHA-256 check passes against `e6ad18f9...`.
3. `requirements.txt` declares the CPU ONNX Runtime dependency (and Pillow if the project intends reproducible installs); no GPU dependency is added.
4. `run_inference.py` supports a real model mode and preserves the scripted mode; its output claims are conditional and truthful.
5. `PerceptionPipeline.describe()` reports visual recognition availability based on the injected detector, not a hardcoded `False`.
6. `evaluate_detector.py --model` either applies `DetectionValidator` or explicitly labels its metrics as pre-validation; accepted/rejected counts are recorded.
7. Real-model tests are added and skip cleanly when the ignored ONNX artifact is absent.
8. Fake-session tests cover the `[1, 18, 8400]` no-objectness contract, class mapping, NMS, and coordinate inversion.
9. Zero-support classes are reported as `evaluated: False` and listed in `unevaluable_classes`.
10. A one-image smoke test and a 5–10-image evaluation slice pass before any full validation run.
11. Full grouped-validation results, if run, include per-class support and local Windows timings, with the Colab timings labeled as supplied training-environment measurements.
12. The full test suite passes; no existing test is weakened or deleted.
13. `README.md`, `datasets/raw/`, `datasets/external/`, `datasets/processed/`, `references/`, the connectome artifacts, and all model hashes remain unchanged.
14. `git status` shows only intended implementation files; no weights are staged or committed.
15. The implementation report `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` is created with accurate limitations and no overclaiming.

### Recommended deliverables

- Updated `configs/detector_config.yaml`.
- Updated `requirements.txt`.
- Updated `run_inference.py` and `evaluate_detector.py`.
- Updated `perception/pipeline.py` (truthful description) and, only if needed, `perception/inference.py` (metadata validation/timings).
- Updated/new tests as listed in section 9.
- `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md`.
- Optional JSON companion report in the next phase if the project's reporting convention requires it; no JSON report was created in this audit.

### Stop and escalate if

- The ONNX model hash or metadata does not match.
- The class order does not match `perception_config.yaml`.
- The model requires a shape or preprocessing not described here.
- The local rejection rate at `bounds_tolerance_pixels: 0.0` is material.
- Any step would require loading `best.pt`, installing GPU packages, or running dataset-wide inference before the smoke slice passes.

---

## Appendix A — ONNX inspection evidence

Read-only ONNX Runtime inspection:

```text
INPUTS:
  images [1, 3, 640, 640] tensor(float)
OUTPUTS:
  output0 [1, 18, 8400] tensor(float)

CUSTOM METADATA:
  version = 8.4.202
  task = detect
  imgsz = [640, 640]
  stride = 32
  batch = 1
  head = Detect
  end2end = False
  args = {'batch': 1, 'dynamic': False, 'nms': None, 'opset': 17, ...}
  names = {0: 'boots-powerup', ..., 13: 'wall'}
  license = AGPL-3.0 License (https://ultralytics.com/license)
```

Synthetic input results:

| Input | Class-score range | Class-score sums | Box range | Interpretation |
|---|---|---|---|---|
| zeros | `0.0 .. 0.01097` | not 1; max 0.0135 | `0..640` px | Scores already in `[0,1]`, boxes are pixel `cxcywh` |
| fixed-seed random | `0.0 .. 0.00756` | not 1; max 0.0082 | `0..640` px | Same conclusion; no objectness row |

The synthetic inputs are not dataset images and the resulting scores are not accuracy evidence. They were used only to verify activation and coordinate convention.

## Appendix B — Audit execution notes

- `.pt` checkpoint: **not loaded, not executed**.
- Dataset-wide inference: **not run**.
- Package installation/upgrade: **none**.
- Files modified outside this report: **none**.
- JSON report: **not created**.
- Git history: **not modified**.
- Deployment hashes, README hash, split-manifest hash, connectome hash, and export ZIP hash were verified as listed in section 12.
