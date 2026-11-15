# Phase 3B.2B.3 — Trained YOLO11n ONNX Integration

**Implementation date:** 2026-11-07
**Scope:** Integrate the trained 14-class YOLO11n ONNX artifact into the existing
Phase 3B perception pipeline, with production-consistent validation, truthful
reporting, explicit CLI modes, and tests.
**Verdict:** **PASS WITH LIMITATIONS**

The detector is integrated and exercised on one image plus a five-image,
two-group validation slice. The integration is ready for a controlled
real-sequence replay, but it is **not** ready for accuracy or gameplay claims:
the 0.426 confidence and 0.7 IoU values are training-run candidates, not
calibrated thresholds, and the production zero-tolerance bounds rule rejected
2 of 13 raw detections in the smoke slice.

No full-dataset inference was run. No weights were loaded from `best.pt`, and
no package was installed, staged, committed, or pushed.

---

## 1. Deployment artifact and verified contract

Artifact directory (Git-ignored):

`models/YOLO11/deployment/yolo11n_v1_deployment/`

| File | Size (bytes) | SHA-256 | Use |
|---|---:|---|---|
| `best.onnx` | 10,636,871 | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | Inference target |
| `best.pt` | 5,491,034 | `1b47a43325b18c59b52b9a29cdd45c029d079ee134a7283b49cd0e86366bdef8` | **Never loaded or executed** |
| `model_config.json` | 1,249 | — | Declares input/output/classes/threshold candidates |
| `metrics_summary.json` | 216 | — | Training-run metrics, not reproduced here |
| `dataset_attribution.txt` | 1,529 | — | Provenance |
| `SHA256SUMS.json` | 734 | — | Deployment checksums |

The ONNX contract used by the integration:

```text
input   [1, 3, 640, 640]  float32, NCHW, RGB, values in [0, 1]
output  [1, 18, 8400]     4 box values + 14 class scores
boxes   cx, cy, w, h in 640-pixel input space
scores  sigmoid already applied inside the exported graph
NMS     external, per class
```

`class_activation: none` is therefore correct for the `yolo_raw` decoder: the
graph supplies probabilities, not logits. The decoder accepts the transposed
`(18, 8400)` layout and the absence of an objectness channel.

Training-run reference metrics in `metrics_summary.json` (not re-measured by
this phase): precision 0.937310, recall 0.810829, mAP50 0.897776,
mAP50-95 0.687726 on 1,128 validation images. These are the training run's
numbers and are **not** produced by this integration.

---

## 2. Files changed and created

Modified:

1. `configs/detector_config.yaml` — deployed contract, SHA, thresholds, identity class map.
2. `perception/detector_config.py` — repository-root-relative model path resolution.
3. `perception/inference.py` — split detector timing and honest timing scope.
4. `perception/pipeline.py` — real availability reporting; description captured after detection.
5. `experiments/phase_3b/run_inference.py` — explicit `mock` / `onnx` modes.
6. `experiments/phase_3b/evaluate_detector.py` — production validation rules, rejection accounting, `--limit`, model overrides, separated timings, correct fold choices.
7. `requirements.txt` — declared CPU ONNX Runtime and Pillow.
8. `tests/test_detector_backend.py` — updated contract tests plus 13 new tests.
9. `tests/test_evaluation.py` — zero-support support-block test.
10. `experiments/phase_3c/integration_check.py` — updated a **stale** protected README hash (see section 9).

Created:

1. `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` (this report).
2. `experiments/phase_3b/results/phase_3b2b3_smoke_single.json`.
3. `experiments/phase_3b/results/phase_3b2b3_smoke_mock.json`.
4. `experiments/phase_3b/results/phase_3b2b3_smoke_eval_fold1.json`.
5. `experiments/phase_3b/results/phase_3b2b3_smoke_eval_fold5.json`.

The result JSON files are generated smoke evidence, not source changes.

---

## 3. Configuration changes

`configs/detector_config.yaml` now describes the deployed model rather than a
generic YOLO family:

| Setting | Before | After |
|---|---|---|
| `model_path` | `null` | `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` |
| `model_sha256` | `null` | `e6ad18f9…b6aa77` |
| `input_size` | `[416, 416]` | `[640, 640]` |
| `has_objectness` | `true` | `false` |
| `class_activation` | `sigmoid` | `none` |
| `confidence_threshold` | `0.25` | `0.426` |
| `nms_iou_threshold` | `0.45` | `0.7` |
| `class_id_map` | `[]` (identity) | explicit `[0, …, 13]` identity |

The threshold values are copied from `model_config.json` and are documented in
the YAML as **initial candidates, not calibrated operating thresholds**. They
remain configurable through the YAML and through CLI overrides; no calibration
was performed in this phase.

`perception/detector_config.py` now resolves a relative `model_path` against
`PROJECT_ROOT` (the repository root), never the current working directory:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def resolve_model_path(value):
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
```

This was verified by loading the configuration from an unrelated working
directory: the model path resolved to the absolute deployment path.

---

## 4. Dependency changes

`requirements.txt` now declares packages that were already present locally and
already imported by the perception code:

```text
Pillow==12.0.0
onnxruntime==1.29.0
```

Notes:

- CPU `onnxruntime` only; no GPU package was added.
- No unrelated package was upgraded.
- No installation was performed in this phase.
- `torch`, `ultralytics`, and `best.pt` are not needed for inference.

---

## 5. Implementation details

### 5.1 Detector timing

`OnnxRuntimeDetector` now records four separate stages:

| Field | Meaning |
|---|---|
| `last_preprocess_ms` | RGB/letterbox/`/255`/NCHW preparation |
| `last_session_run_ms` | The ONNX Runtime `session.run` call |
| `last_postprocess_ms` | Decode, threshold, NMS, class map, coordinate inversion |
| `last_detector_call_ms` | Total wall time of the detector call |
| `last_inference_ms` | Legacy alias for the total detector call |

`describe()` publishes `timing_scope` explicitly:

> detector call wall time: preprocessing + session.run + decode/NMS/coordinate
> inversion; not pure ONNX inference time

The single-image smoke run measured 128.31 ms total, of which 112.27 ms was the
session call.

### 5.2 Pipeline reporting

`PerceptionPipeline.describe()` no longer hardcodes
`visual_recognition_available: False`. It derives availability from the
detector description:

```python
available = bool(detector.get("weights_loaded", False)) and not detector.get("test_only", False)
```

It also reports `detector_name`, `detector_kind`, and `detector_test_only`.
`PerceptionPipeline.run()` now captures the detector description **after**
detection, so timing fields in `PerceptionResult.detector` belong to the current
call rather than the previous one.

Scripted `MockDetector` output is still reported as unavailable and test-only.

### 5.3 `run_inference.py`

Two explicit modes:

- `--mode mock` (default): unchanged scripted/empty behavior, labeled as test
  plumbing.
- `--mode onnx`: constructs `OnnxRuntimeDetector` from the detector config,
  verifies the artifact SHA-256, runs the model, and passes output through the
  normal validator.

Onnx-mode overrides: `--detector-config`, `--model-path`, `--model-sha256`,
`--confidence-threshold`, `--nms-iou-threshold`. Relative model paths use the
repository root.

Failure behavior was verified:

- Missing model file →
  `ONNX detector unavailable: detector model not found: …\models\does_not_exist.onnx`
- Missing `onnxruntime` → explicit `onnxruntime is not installed` config error.
- SHA mismatch → explicit `model SHA-256 mismatch` before a session is created.
- `--predictions` with `--mode onnx` is rejected.

Mock mode was re-run on the same image and still reports
`visual_recognition_available: false`, `detector_test_only: true`, zero
accepted detections.

### 5.4 `evaluate_detector.py`

The `--model` path now:

- constructs the detector with the confidence threshold lowered to
  `--confidence-floor` (default 0.05) so AP still sees low-confidence boxes;
- passes every raw detection through `DetectionValidator` using the production
  `ValidationConfig`, changing **only** the confidence threshold;
- converts only accepted `Detection.normalized_box` values into `EvaluationBox`;
- reports `n_raw_detections`, `n_accepted`, `n_rejected`, rejection counts by
  reason, and up to 20 rejection examples;
- reports zero-support classes explicitly at top level
  (`zero_support_classes`) and in limitations, with undefined AP rather than
  invented values;
- adds `--limit N` for smoke slices and reslices support statistics to the
  evaluated images;
- adds `--model-path` and `--model-sha256` overrides;
- reports `timing.detector_call`, `timing.session_run`, `timing.preprocess`,
  and `timing.postprocess` separately, with an explicit scope string.

A second, pre-existing CLI bug was fixed: `--fold` offered `0–4` while the
dataset folds are `1–5`. It now offers `1–5`.

---

## 6. Test results

Full suite:

```text
294 passed in 10.90s
```

Targeted detector/evaluation suite:

```text
39 passed in 0.87s
```

New coverage added (14 tests):

- deployed YAML contract: 640×640, no objectness, activation `none`, 14-class
  identity map, configured SHA;
- repository-root-relative model path resolution;
- missing model path, missing file, missing ONNX Runtime, SHA mismatch;
- `[1, 18, 8400]` transposed decoding with no objectness;
- wrong column counts (17 and 19) rejected;
- class-aware NMS;
- letterbox inversion on a non-square frame;
- fake-session pipeline injection with a real `[1,18,8400]` tensor;
- pipeline availability reporting for real vs mock detectors;
- evaluation validator agreement with pipeline validation and rejection
  reasons;
- zero-support class reporting;
- real ONNX smoke test that skips cleanly when the Git-ignored artifact is
  absent.

No existing test was deleted or weakened. The only pre-existing failure found
was the stale README protected hash described in section 9; it was fixed at its
root cause, not skipped.

---

## 7. Smoke-test results

### 7.1 Single image

Input: `train/images/datasetfootage_mp4-0_jpg.rf.0097bea70e5bd8e7224782e5df9ff31e.jpg`
(606×1050).

| Field | Value |
|---|---|
| Mode | `onnx_model` |
| Visual recognition available | `true` |
| Detector | `onnx-runtime-detector`, not test-only |
| SHA verified | `e6ad18f9…b6aa77` |
| Input size | 640×640 |
| Objectness / activation | `false` / `none` |
| Model classes | 14 |
| Confidence / NMS | 0.426 / 0.7 |
| Candidates above threshold | 29 |
| Raw detections after NMS | 3 |
| Accepted | 2 (`train` 0.9459, `boxtrain` 0.9232) |
| Rejected | 1 `out_of_bounds` (0.215 px outside the 606×1050 image) |
| Total detector call | 128.31 ms |
| — preprocessing | 14.01 ms |
| — session.run | 112.27 ms |
| — postprocess | 2.03 ms |

### 7.2 Five-image, two-group slice

No full validation-set inference was run. Two folds were sampled:

| Fold | Group | Images | Raw | Accepted | Rejected | Detector call mean | session.run mean |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `datasetfootage` | 3 | 9 | 7 | 2 (`out_of_bounds`) | 121.35 ms | 108.46 ms |
| 5 | `subwayy1_1` | 2 | 4 | 4 | 0 | 136.66 ms | 121.72 ms |
| **Total** | 2 groups | **5** | **13** | **11** | **2** | — | — |

Zero-support reporting worked as intended: fold 1 reported 11 classes with no
ground-truth support in that slice; fold 5 reported 12. Their AP is `null` and
no performance is claimed for them.

The five-image metric outputs exist in the result JSON for plumbing inspection
only. They are **not** performance estimates, because five images cannot
represent 1,128 validation images and the model was not validated against an
independent test set.

---

## 8. Known limitations

1. **Thresholds are not calibrated.** 0.426 confidence and 0.7 IoU come from the
   training run. No threshold sweep was performed.
2. **Zero bounds tolerance rejects sub-pixel overflow.** The production
   validator uses `bounds_tolerance_pixels: 0.0`; 2 of 13 raw detections in the
   smoke slice were rejected for lying 0.2–0.3 px outside the image. This is
   production-consistent behavior, not a bug, but the policy should be decided
   before a performance-oriented replay. Changing it would alter existing
   validation semantics and was not done here.
3. **No independent test split.** Validation groups are held-out recordings,
   not a test set.
4. **Zero-support classes depend on the evaluated selection.** Only classes
   present in the slice can be scored; all others are reported as undefined.
5. **Activation assumption.** `class_activation: none` reflects the audited
   export. The runtime checks the output shape, not the graph's sigmoid node.
6. **Timing is not pure model latency.** `session.run` is reported separately;
   totals include preprocessing and postprocessing.
7. **CPU, batch 1.** No GPU path, batching, or throughput claim.
8. **Not connected to the connectome.** The detector feeds the existing
   perception/GameState layer only; no biological perception is claimed.
9. **Training-run metrics are not reproduced here.** `metrics_summary.json`
   remains the training run's own validation result.
10. **`best.pt` remains unused.** The PyTorch checkpoint was never loaded or
    executed.

---

## 9. Protected artifacts and Git state

Hashes verified after implementation:

| Artifact | SHA-256 | Match |
|---|---|---|
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | yes (equals HEAD; not modified by this phase) |
| `best.onnx` | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | yes |
| `best.pt` | `1b47a43325b18c59b52b9a29cdd45c029d079ee134a7283b49cd0e86366bdef8` | yes |
| `reports/PHASE_3B1_SPLIT_MANIFEST.json` | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` | yes |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | yes |
| `datasets/exports/phase_3b2b1_yolo11n.zip` | `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff` | yes |

**Pre-existing protected-hash issue.** The full suite initially failed
`test_protected_artifacts_unchanged` because `PROTECTED["README.md"]` still held
hash `6277ffbb…`, recorded before commit `2745cf7` ("Update section title in
README for clarity"). That commit changed one heading from
`## Recommended next milestone` to `## Recommended `. The worktree README is
clean and byte-identical to HEAD. The expected constant in
`experiments/phase_3c/integration_check.py` was updated to the committed HEAD
hash with an explanatory comment. This is a baseline refresh for an intentional,
already-committed README change, not a change to the README or a skipped test.

Git state after implementation:

- Modified: 10 files (listed in section 2).
- New: this report and four generated smoke JSON files.
- No model weights are tracked (`git ls-files models` returns 0 entries).
- No raw dataset, annotation, connectome, reference, or export file changed.
- Nothing was staged, committed, or pushed.

---

## 10. Readiness for real-sequence replay

**PASS WITH LIMITATIONS — ready for a controlled small real-sequence replay at
the plumbing level.**

What is proven:

- the deployed ONNX artifact loads on CPU, its SHA-256 matches the committed
  expectation, and it produces the expected `[1, 18, 8400]` output;
- decoding, class mapping, NMS, letterbox inversion, and validation work on real
  model output;
- the pipeline reports real detector availability and separates timing stages;
- evaluation and production validation now agree on which detections are
  accepted or rejected;
- mock/scripted behavior remains backward compatible.

What must be decided before any performance-oriented evaluation:

1. calibrate or explicitly accept the confidence and NMS thresholds;
2. decide whether the zero-tolerance bounds rule or a small tolerance is the
   intended production policy for sub-pixel box overflow;
3. run the approved full validation evaluation only after those decisions, and
   keep describing results as grouped-validation evidence, not independent test
   performance;
4. keep the replay small and sequential until CPU latency and memory behavior
   are characterized on real sequences.
