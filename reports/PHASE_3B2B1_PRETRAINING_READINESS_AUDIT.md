# Phase 3B.2B.1 — Pre-training Readiness Audit

**Status:** audit only. No model was trained, no package was installed, no file
was downloaded, no image, label, YAML, manifest, connectome, simulator or
reference repository was modified, and nothing was staged, committed or
pushed.

**Date:** 2026-11-06

**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`

**Question:** is FLY-SURFER ready to export its curated Subway Surfers dataset
and train a custom YOLO11n detector in Google Colab?

**Verdict: BLOCKED — not ready.** The dataset contract is valid and the
evaluation protocol is defined, but there is no export, no accepted licensing
decision, no YOLO11-specific training or decoding configuration that has been
tested, and the checkpoint is not excluded from Git. Existence of
`models/YOLO11/yolo11n.pt` is **not** evidence of training readiness.

---

## 1. Executive summary

| Area | Finding | Status |
| --- | --- | --- |
| Curated dataset | Manifest verified directly against 2,328 raw images and labels; 2,316 curated images / 8,666 boxes; group-atomic split; every path resolves | **PASS** |
| Independent test split | Impossible with five recordings; fixed split and LOGO folds are group-held-out validation only | **FAIL** (structural) |
| Dataset export | `datasets/exports/` does not exist; no `dataset.yaml`, image/label tree or attribution bundle | **FAIL** (missing) |
| Checkpoint | Real Ultralytics YOLO11n checkpoint, SHA-256 recorded, COCO metadata present, AGPL-3.0 metadata present | **PASS** (identified) |
| Checkpoint use for transfer learning | Requires `ultralytics` (not installed locally), a licence decision, and a re-trained 14-class head | **BLOCKED** |
| Git handling of checkpoint | `models/` is neither tracked nor ignored; the checkpoint shows as untracked | **FAIL** |
| Detector interface and ONNX decoding | Implemented with letterbox, inverse mapping, NMS, confidence filtering and class mapping; tested with synthetic tensors only | **PASS** (implemented) |
| YOLO11 `.pt` loader | Not implemented; the only backend is ONNX Runtime | **FAIL** (missing) |
| ONNX path with real YOLO11 weights | Not exercised; shipped config targets `has_objectness: true` at 416, which does not match a YOLO11 export | **BLOCKED** (untested) |
| Evaluation harness | Precision, recall, F1, AP@0.5, AP@0.5:0.95, per-class, confusion, FP/FN, latency, memory, fixed split and five LOGO folds | **PASS** (implemented) |
| Ultralytics results adapter | Missing; harness consumes `EvaluationBox` mappings or a prediction JSON only | **FAIL** (missing) |
| Local training environment | Python 3.13, CPU-only PyTorch, no torchvision, no OpenCV, no Ultralytics, no CUDA runtime | **FAIL** |
| YOLOX reference source | Complete extraction, Apache-2.0, version 0.3.0, no pretrained weights present | **PASS** (reference only) |
| Licensing | Dataset declares CC BY 4.0 but attribution is not recorded in project notices; YOLO11 is AGPL-3.0 and no decision is recorded | **BLOCKED** |
| Overall Colab training readiness | Valid export, training config, adapter, licence decision and safety rule all outstanding | **BLOCKED** |

**Overall audit status: BLOCKED.** Four gating conditions are unmet: a valid
curated export, a verified YOLO11 training/decoding configuration, an accepted
licensing decision, and Git exclusion of model weights. The evaluation plan
exists but has never processed real detector predictions.

---

## 2. Scope, method and protection-rule verification

All checks were read-only. The dataset manifest and raw label files were parsed
in memory with `python -B`; the checkpoint was inspected with `zipfile` and
`hashlib`; no pickle object was deserialized; YOLOX was neither installed nor
executed.

A previous attempt to identify the checkpoint with the `file` utility caused a
segmentation fault in Git Bash. `file` was not used again and no state was
changed by that failure.

| Protection rule | Verification | Result |
| --- | --- | --- |
| Root `README.md` byte-identical | SHA-256 `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` | **PASS** |
| Raw Subway Surfers images, labels, YAML unmodified | Read-only access; 2,328 images and the raw `data.yaml` parsed, never written | **PASS** |
| Phase 3B.1 split manifest unmodified | SHA-256 `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` | **PASS** |
| Connectome and neural simulation unmodified | No write outside the two audit files; no simulator run | **PASS** |
| External reference repositories unmodified | YOLOX listed and read only | **PASS** |
| No staging, commit or push | `git diff --cached` empty; branch `main`; no Git write command executed | **PASS** |
| Existing reports not overwritten | Both audit filenames did not exist before this run | **PASS** |
| No additional checkpoint downloaded | Only the pre-existing local `yolo11n.pt` was inspected | **PASS** |
| Presence verified, not assumed | Every path below was checked on disk during this audit | **PASS** |

The audit created exactly two new files: this report and its JSON mirror.

---

## 3. Actual directory structure (relevant subset)

```text
FLY-SURFER/
  README.md                                  (protected, hash matches)
  requirements.txt                           (286 bytes; no torch/ultralytics)
  configs/
    perception_config.yaml                   (14-class schema)
    detector_config.yaml                     (ONNX, yolo_raw, objectness=true, 416)
    phase_3b1_curation.yaml
  perception/
    config.py  dataset.py  detection.py  detector.py  detector_config.py
    evaluation.py  game_state_adapter.py  geometry.py  image.py  inference.py
    lanes.py  manifest.py  observations.py  pipeline.py  scene.py
    sensory_bridge.py  serialization.py  temporal.py  tracking.py
  experiments/phase_3b/
    audit_dataset.py  curate_dataset.py  evaluate_detector.py
    run_inference.py  validate_dataset.py  previews/  previews_v15/  results/
  models/
    YOLO11/
      yolo11n.pt                             (5,613,764 bytes; untracked, not ignored)
  datasets/
    README.md  manifest.json
    external/subway surfers/roboflow_v15_yolov8/
      subway surfers object dataset.v15-added.yolov8/
        README.dataset.txt  README.roboflow.txt  data.yaml  train/  valid/
    exports/                                 (DOES NOT EXIST)
    processed/  raw/
  references/
    YOLOX-main/                              (ignored; contains nested YOLOX-main/)
    YOLOX-main.zip                           (4,490,945 bytes; ignored)
  reports/
    PHASE_3B2B0_DETECTOR_FEASIBILITY.md
    PHASE_3B1_SPLIT_MANIFEST.json
    ... (existing reports, untouched)
```

The raw dataset root contains only `train` and `valid`, despite its
`data.yaml` declaring `test: ../test/images`. That declared test directory does
not exist. See section 6.

---

## 4. Audit A — model weights

### 4.1 Facts

| Property | Measured value | Method |
| --- | --- | --- |
| Path | `models/YOLO11/yolo11n.pt` | Directory listing |
| Exists | Yes | `os.path.isfile` / listing |
| Size | 5,613,764 bytes | Filesystem |
| SHA-256 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | `hashlib.sha256` |
| Container | ZIP / PyTorch archive, 507 members | `zipfile` |
| Pickle member | `yolo11n/data.pkl`, 203,281 bytes | `zipfile` metadata |
| Tensor members | `yolo11n/data/0` … `yolo11n/data/502` | `zipfile` metadata |
| Archive version member | `yolo11n/version` = `3` | Read as bytes |
| Ultralytics metadata (plain strings) | version `8.2.100`, date `2024-09-25T21:10:26`, licence string `AGPL-3.0 License (https://ultralytics.com/license)` | ASCII scan of `data.pkl`, no unpickling |
| Model class markers | `DetectionModel`, `ultralytics.nn.tasks`, COCO name markers present | ASCII scan of `data.pkl` |
| Git ignored | **No** (`git check-ignore` returned no match) | `git check-ignore -v` |
| Git tracked | **No** | `git ls-files --error-unmatch` |
| Git status | `?? models/YOLO11/yolo11n.pt` | `git status --short` |
| Sidecar licence or hash file | None; directory contains only the checkpoint | Listing |

### 4.2 Readiness assessment

- The file is a genuine modern Ultralytics detection checkpoint, not a renamed
  or empty artifact. Its internal metadata and tensor count are consistent with
  a YOLO11n model.
- It is a stock COCO-pretrained checkpoint by metadata, not a Subway Surfers
  detector. A 14-class head must be trained; this is expected for transfer
  learning, but no such training has occurred.
- The class-name and argument dictionaries live inside `data.pkl`. They were
  deliberately **not** unpickled. COCO markers were observed as plain strings,
  but the exact class list and training arguments remain unverified.
- Loading it requires the `ultralytics` package, which is **not installed**.
  The repository has no Ultralytics loader; its only artifact loader is ONNX
  Runtime.
- The checkpoint's own licence metadata says AGPL-3.0. Whether a fine-tuned
  derivative may be distributed or hosted is a project decision, not an audit
  conclusion (section 11).
- No official-release checksum was available offline, so provenance is
  established by format and internal metadata only.

**Status:** checkpoint identified and safely inspected — **PASS**; ready for
transfer learning and distribution — **BLOCKED** (missing runtime, missing
export/loader, unresolved licence and Git handling).

---

## 5. Audit B — YOLOX reference repository

### 5.1 Structure

The archive was extracted into a nested directory:
`references/YOLOX-main/YOLOX-main/`. A sibling `references/YOLOX-main.zip`
(4,490,945 bytes) is also present. The nested tree contains 169 files; the ZIP
lists 229 entries including directory records.

| Required element | Present | Notes |
| --- | --- | --- |
| `setup.py` | Yes | 2,710 bytes; `python_requires=">=3.6"` |
| `requirements.txt` | Yes | 277 bytes |
| `exps/` | Yes | `default/` contains `yolox_nano.py`, `yolox_tiny.py`, `yolox_s.py`, `yolox_m.py`, `yolox_l.py`, `yolox_x.py`, `yolov3.py`; `example/` present |
| `yolox/` | Yes | `core`, `data`, `evaluators`, `exp`, `layers`, `models`, `tools`, `utils` |
| `tools/` | Yes | `train.py`, `eval.py`, `demo.py`, `export_onnx.py`, `export_torchscript.py`, `trt.py`, `visualize_assign.py` |
| `LICENSE` | Yes | Apache License 2.0 |
| `README.md` | Yes | 13,314 bytes |
| `tests/`, `docs/`, `demo/`, `assets/` | Yes | Present |
| Pretrained weights | **No** | No `.pth`, `.pt`, `.onnx` or `.ckpt` anywhere in the tree |

Version declared in `yolox/__init__.py`: `0.3.0`.

### 5.2 Dependencies

`requirements.txt` declares: `numpy` (unpinned), `torch>=1.7`,
`opencv_python`, `loguru`, `tqdm`, `torchvision`, `thop`, `ninja`, `tabulate`,
`psutil`, `tensorboard`, `pycocotools>=2.0.2`, `onnx>=1.13.0`,
`onnx-simplifier==0.4.10`. Several versions are unpinned, including NumPy and
PyTorch.

### 5.3 Assessment

- This is a complete source extraction, not a partial download.
- YOLOX is **not** an approved dependency of FLY-SURFER and remains a
  read-only alternative reference. It was not installed or executed.
- Its loose pins and native COCO-JSON training path make it a fallback, not the
  selected YOLO11 route.
- The absence of pretrained YOLOX-Nano weights means any YOLOX experiment would
  require a separate download approval.

**Status:** source verified complete and Apache-2.0 — **PASS**; approved for use
in this project — **BLOCKED** (no approval, no install, no weights).

---

## 6. Audit C — dataset contract

### 6.1 Authoritative source

`reports/PHASE_3B1_SPLIT_MANIFEST.json`, SHA-256
`ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d`,
generated 2026-11-04. It was read, never regenerated or written.

Dataset root resolved from the manifest:
`datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8`.
The directory exists and contains `train/`, `valid/`, `data.yaml`,
`README.dataset.txt` and `README.roboflow.txt`.

### 6.2 Counts verified directly from disk

| Check | Manifest value | Recomputed | Status |
| --- | ---: | ---: | --- |
| Raw images on disk | 2,328 | 2,328 | **PASS** |
| Curated assignments | 2,316 | 2,316 | **PASS** |
| Quarantined images | 12 | 12 | **PASS** |
| Curated boxes | 8,666 | 8,666 | **PASS** |
| Train images / boxes | 1,188 / 4,704 | 1,188 / 4,704 | **PASS** |
| Valid images / boxes | 1,128 / 3,962 | 1,128 / 3,962 | **PASS** |
| Class IDs / names | 14 | 14, IDs 0–13 | **PASS** |
| Assignment keys unique | — | Yes | **PASS** |
| Assignment images resolve on disk | — | 2,316 / 2,316 | **PASS** |
| Assignment labels resolve on disk | — | 2,316 / 2,316 | **PASS** |
| Empty labels inside assignments | 0 | 0 | **PASS** |
| Out-of-range class IDs | 0 | 0 | **PASS** |
| Assignment ∩ quarantine | 0 | 0 | **PASS** |
| Curated + quarantine = raw | 2,328 | 2,328 | **PASS** |
| Group leakage | 0 | 0 | **PASS** |

The 12 exclusions are 9 `probable_gap` images in `subwayedtied` and 3
`isolated_plausible` images in `subwayy1_1`. Every excluded path resolves and
every excluded label is empty. None appears in the assignments.

### 6.3 Group atomicity and original-split independence

| Group | Images | Boxes | Fixed split |
| --- | ---: | ---: | --- |
| `subwayavitomp4` | 501 | 1,798 | train |
| `subwayedited2` | 392 | 1,580 | train |
| `subwayedtied` | 295 | 1,326 | train |
| `datasetfootage` | 504 | 1,681 | valid |
| `subwayy1_1` | 624 | 2,281 | valid |

Every image in a group is assigned to exactly one split, so there are zero
cross-split adjacent-frame pairs by construction.

The original Roboflow folder is not the split:

- 903 images located in the raw `train/images` folder are assigned to **valid**;
- 275 images located in the raw `valid/images` folder are assigned to **train**.

This confirms that evaluation must use the manifest assignments, not folder
names.

### 6.4 Per-class support (recomputed from labels)

| ID | Class | Train boxes | Train images | Valid boxes | Valid images |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | boots-powerup | 24 | 24 | **0** | **0** |
| 1 | boxtrain | 625 | 482 | 749 | 538 |
| 2 | jump-barrier | 254 | 221 | 163 | 148 |
| 3 | jump-electric | 14 | 14 | **0** | **0** |
| 4 | jump-hedge | 18 | 17 | 26 | 21 |
| 5 | jump-roll-barrier | 407 | 359 | 356 | 287 |
| 6 | jump-trash | 34 | 33 | 62 | 44 |
| 7 | ledge | 87 | 57 | 48 | 32 |
| 8 | pogstick-powerup | 53 | 53 | 65 | 65 |
| 9 | ramp | 606 | 444 | 617 | 501 |
| 10 | roll-barrier | 147 | 141 | 162 | 149 |
| 11 | train | 1,617 | 883 | 1,174 | 839 |
| 12 | undercover-barrier | 196 | 84 | 19 | 15 |
| 13 | wall | 622 | 279 | 521 | 247 |

All 14 classes are represented in training. `boots-powerup` and
`jump-electric` have **zero validation boxes** and are therefore unevaluable in
the fixed valid split; their per-class AP is undefined, not zero.
`undercover-barrier` (19 valid boxes) and `jump-hedge` (26) are low-support and
must be reported with support counts.

### 6.5 Class-schema agreement

`configs/perception_config.yaml` defines 14 classes with IDs 0–13 in exactly the
same order as the manifest. A runtime load in this audit confirmed
`names == manifest.class_names`.

### 6.6 Test split

The raw `data.yaml` declares `test: ../test/images`, but:

- the dataset root contains only `train/` and `valid/`;
- the manifest records `splits_present: ["train", "valid"]`;
- five recordings cannot supply an independent test group.

There is **no test split**. Fixed-split and LOGO results are group-held-out
validation and must never be described as test performance.

**Status:** dataset contract — **PASS**; independent test split — **FAIL**
(structurally impossible with the available recordings).

---

## 7. Audit D — Colab dataset export

### 7.1 Presence check

`datasets/exports/` **does not exist**. `ls` returned
`No such file or directory`; a repository-wide search found no exported
`dataset.yaml` outside the raw dataset.

Therefore none of the following exists:

| Export requirement | Status |
| --- | --- |
| `dataset.yaml` with 14 classes and split paths | **FAIL** (missing) |
| `images/train`, `images/valid` | **FAIL** (missing) |
| `labels/train`, `labels/valid` | **FAIL** (missing) |
| One label per exported image, one image per label | **FAIL** (missing) |
| Class ordering identical to manifest / perception schema | **FAIL** (missing) |
| No quarantined image in the export | **FAIL** (missing) |
| No duplicate or colliding filenames | **FAIL** (missing) |
| Portable relative paths for Colab | **FAIL** (missing) |
| CC BY 4.0 source attribution retained | **FAIL** (missing) |
| Export manifest with source hashes and counts | **FAIL** (missing) |

No export script exists either. The Phase 3B.1 curation tooling reads the
manifest but does not materialize a training tree.

### 7.2 Required export shape (not created)

If approved later, the export must be derived only from
`reports/PHASE_3B1_SPLIT_MANIFEST.json`, must copy files rather than modify the
raw dataset, and must use portable relative paths:

```yaml
path: .
train: images/train
val: images/valid
nc: 14
names: [boots-powerup, boxtrain, jump-barrier, jump-electric, jump-hedge,
        jump-roll-barrier, jump-trash, ledge, pogstick-powerup, ramp,
        roll-barrier, train, undercover-barrier, wall]
```

Expected counts: 1,188 train images / 4,704 boxes and 1,128 valid images /
3,962 boxes, 2,316 images total, 14 classes, zero quarantined images.

**Status:** export — **FAIL** (missing). Training cannot begin without it.

---

## 8. Audit E — detector implementation compatibility

### 8.1 Components present

| Component | Location | Behaviour | Status |
| --- | --- | --- | --- |
| `Detector` protocol | `perception/detector.py:20` | `detect(frame) -> Sequence[Any]`, `describe()` | **PASS** |
| `MockDetector` | `perception/detector.py:52` | Test-only scripted detections, no pixel inspection | **PASS** |
| Model config | `perception/detector_config.py:47` | Validates path, SHA-256, input, output layout, thresholds, class map, providers | **PASS** |
| Missing-model failure | `perception/detector_config.py` / `perception/inference.py:481` | Raises explicit `DetectorConfigError`; verified by construction | **PASS** |
| Letterbox and inverse transform | `perception/inference.py:80`, `:35` | Resize with padding and explicit inverse box mapping | **PASS** |
| YOLO raw decoding | `perception/inference.py:273` | `[cx, cy, w, h, obj?, classes...]`, optional transposition, no objectness when configured | **PASS** |
| NMS | `perception/inference.py:163`, `:194` | Per-class batched NMS with score ordering | **PASS** |
| Confidence filtering | `perception/inference.py:559` | Threshold before NMS | **PASS** |
| Class mapping | `perception/detector_config.py:150` | Model index → schema ID, `-1` to ignore | **PASS** |
| SHA-256 verification at load | `perception/inference.py:489` | Optional configured digest checked against file | **PASS** |
| ONNX Runtime backend | `perception/inference.py:467` | Loads a local `.onnx` file only | **PASS** |
| Ultralytics `.pt` backend | — | **Not implemented** | **FAIL** |
| GPU provider selection | config `runtime.providers` | Configurable, but the installed ONNX Runtime exposes only CPU and Azure providers | **FAIL** (no usable GPU) |
| Real-model test | — | No real weights were run; tests use synthetic tensors | **BLOCKED** |

### 8.2 YOLO11-specific gaps

1. **Format.** The configured `backend: onnx` is the only model backend. A
   `.pt` checkpoint cannot be passed to `OnnxRuntimeDetector`; it would fail
   as an unreadable ONNX graph. A YOLO11 path requires either an ONNX export or
   a new Ultralytics-backed detector.
2. **Output layout.** `configs/detector_config.yaml` sets
   `has_objectness: true`, which expects `4 + 1 + nc` columns. A standard
   YOLO11 detection export emits `4 + nc` columns with sigmoid-applied class
   scores. For a 14-class model the expected tensor is `[1, 18, 8400]` at 640.
   The decoder can transpose such a tensor (`_columns`), but only if
   `has_objectness: false`; the shipped default is wrong for YOLO11.
3. **Input size.** The shipped `input_size` is `[416, 416]`. YOLO11n is
   normally trained and exported at 640. This must be changed explicitly.
4. **Class activation.** `class_activation` is validated but not applied by
   `decode_yolo_raw`; for YOLO11 exports this is acceptable because scores are
   already sigmoided, but the setting must not be read as a transform.
5. **Class map.** The configured `class_id_map` is empty, which means identity
   mapping to the 14 schema IDs. That is correct only for a model whose output
   order matches the manifest. This must be verified after training.
6. **Resize convention.** YOLO11 export uses a 114 grey letterbox and RGB
   `[0, 1]` NCHW input, which matches `pad_value: 114`, `color_order: rgb`
   and `prepare_input`. This part is compatible.
7. **Class-aware NMS** runs on model indices before mapping, which is correct.
8. **No test with YOLO11 weights.** All inference tests use synthetic tensors;
   no ONNX file exists in the repository.

**Status:** interface and ONNX machinery — **PASS** (implemented and
synthetically tested); YOLO11 end-to-end compatibility — **BLOCKED** (requires
export/adapter, config change and a real smoke test).

---

## 9. Audit F — evaluation compatibility

### 9.1 Capabilities

`perception/evaluation.py` implements:

| Requirement | Evidence | Status |
| --- | --- | --- |
| Precision, recall, F1 | `ClassMetrics`, micro and macro aggregates | **PASS** |
| AP@0.5 | `map50` from the IoU sweep | **PASS** |
| AP@0.5:0.95 | `map50_95` over the sweep | **PASS** |
| Per-class results | `classes: tuple[ClassMetrics, ...]` | **PASS** |
| Confusion matrix | `confusion` block | **PASS** |
| False-positive taxonomy | `false_positives` block | **PASS** |
| False-negative taxonomy | `false_negatives` block | **PASS** |
| Latency | `summarize_latency` with p50/p95/p99 | **PASS** |
| Peak memory | `peak_memory_mb` | **PASS** |
| Grouped validation | `--split train/valid` and `--fold 0..4` from the manifest | **PASS** |
| Bootstrap confidence intervals | Seeded resampling | **PASS** |
| Low-support flagging | Threshold and `unevaluated_classes` | **PASS** |
| Independent test evaluation | No test split exists | **FAIL** (structural) |
| Ultralytics `Results` ingestion | Not implemented | **FAIL** (missing) |
| Real predictions evaluated | No weights or predictions exist | **BLOCKED** |

### 9.2 Integration gap

`experiments/phase_3b/evaluate_detector.py` accepts exactly two sources:

- `--model`, which constructs `OnnxRuntimeDetector` only; or
- `--predictions`, a JSON object mapping image paths to normalized
  `[class_id, confidence, x1, y1, x2, y2]` boxes.

There is no converter from an Ultralytics `Results` object, `results.csv`,
`predictions.json` produced by `model.predict`, or a YOLO11 `.pt` file. Such an
adapter is a small, well-bounded component, but it does not exist today.

The fixed valid split is explicitly labelled model selection, not test
evaluation. LOGO folds estimate group sensitivity; they are not a substitute
for a test set.

**Status:** metrics harness — **PASS** (implemented, synthetic data only);
YOLO11 evaluation path — **BLOCKED** (adapter missing, no real predictions).

---

## 10. Audit G — training environment

### 10.1 Local measurements at audit time

| Item | Value |
| --- | --- |
| Python | 3.13.14 (AMD64) |
| PyTorch | 2.10.0+cpu |
| `torch.cuda.is_available()` | `False` |
| `torch.version.cuda` | `None` |
| ONNX Runtime | 1.29.0; providers `AzureExecutionProvider`, `CPUExecutionProvider` |
| torchvision | **not installed** |
| OpenCV (`cv2`) | **not installed** |
| Ultralytics | **not installed** |
| `onnx` | **not installed** |
| GPU | NVIDIA GeForce RTX 3050 Laptop, 4,096 MiB, driver 592.27, no CUDA runtime |
| CPU | 6 physical / 12 logical |
| RAM | 15.34 GiB total, 3.31 GiB available |
| Disk C: | 37.15 GiB free of 463.81 GiB |
| `pip check` | Two unrelated conflicts outside this project's declared requirements: `esptool` vs `cryptography`, `streamlit` vs `protobuf` |

`requirements.txt` pins NumPy, pandas, Matplotlib, PyYAML, psutil and pytest.
It does **not** declare PyTorch, Pillow or ONNX Runtime even though the code
imports them. There is no `pyproject.toml`, `setup.py` or environment lock for
the Python project.

### 10.2 Consequence

Local training is not possible in the current environment: Ultralytics and
torchvision are absent, PyTorch is CPU-only, and the installed ONNX Runtime has
no CUDA provider. This matches the earlier feasibility report, although free
disk has improved since that report (37.15 GiB now versus 2.19 GiB then).
Resource figures are point-in-time measurements and fluctuate.

### 10.3 Proposed Colab environment (proposal only; nothing was installed)

This is deliberately separate from the local environment.

| Item | Proposed value | Reason |
| --- | --- | --- |
| Runtime | GPU (T4 16 GB or better) | CPU-only local PyTorch is unsuitable |
| Python | 3.10–3.12 | Broad Ultralytics/PyTorch wheel support |
| Core | CUDA-enabled `torch` + matching `torchvision` | Provided by the Colab image; verify at runtime |
| Detector | `ultralytics` pinned to an explicit version | Needed to load `yolo11n.pt`, train and export ONNX |
| Support | `numpy`, `PyYAML`, `Pillow`, `opencv-python-headless`, `onnx`, `onnxruntime` | Export and local evaluation |
| Data | Upload the approved export archive; unzip under `/content/` | No raw dataset upload, no repo modification |
| Configuration | `imgsz=640`, single GPU, fixed seed, deterministic settings where supported | Match the 606×1050 portrait data and YOLO11 defaults |
| Outputs | `best.pt`, `last.pt`, `results.csv`, run metadata, ONNX export | Reproducible evidence |
| Provenance | Record package versions, dataset export hash, manifest hash, Git commit | Audit trail |

A starting training invocation (not executed) would be:

```python
from ultralytics import YOLO
model = YOLO("yolo11n.pt")
model.train(data="dataset.yaml", imgsz=640, epochs=100, batch=16,
            seed=20261106, deterministic=True, device=0,
            project="fly_surfer", name="yolo11n_v15")
```

Epochs and batch size are a starting point to be pre-registered, not a
measured recommendation. Training in Colab must not be described as
reproducible until versions, seed, export hash and evaluation commands are
recorded.

**Status:** local environment — **FAIL** for training; Colab specification —
**PASS** (defined); Colab training — **BLOCKED** (no export, no licence
decision, no approval).

---

## 11. Audit H — licensing and provenance

### 11.1 Facts

| Item | Evidence | Status |
| --- | --- | --- |
| Dataset licence | Raw `data.yaml` declares `license: CC BY 4.0`, workspace `horizon-cgt2k`, version 15 | **PASS** |
| Dataset attribution in project notices | `THIRD_PARTY_NOTICES.md`, `REFERENCES.md` and `datasets/README.md` document FlyWire only; no Subway Surfers/Roboflow entry | **FAIL** |
| YOLO11 licence | Checkpoint metadata string: `AGPL-3.0 License (https://ultralytics.com/license)` | **PASS** |
| YOLOX licence | `LICENSE` is Apache-2.0 | **PASS** |
| YOLOX weights licence | No weights present, so no checkpoint licence to verify | **NOT APPLICABLE** |
| Accepted licence decision for YOLO11 training | No record in the repository | **BLOCKED** |
| Official checksum for `yolo11n.pt` | Not available offline; only the local SHA-256 was computed | **BLOCKED** (provenance unconfirmed) |
| Game screenshot/IP rights | The Roboflow uploader declares CC BY 4.0, but the underlying game imagery rights are not addressed | **BLOCKED** (unresolved) |

### 11.2 Considerations (not legal conclusions)

- CC BY 4.0 requires attribution when the images or derivatives are shared.
  An export intended for Colab should carry the dataset name, source URL,
  version and licence notice. The raw dataset already contains
  `README.dataset.txt` and `README.roboflow.txt`; the export does not yet
  include them.
- The YOLO11 checkpoint and the Ultralytics training stack are AGPL-3.0.
  AGPL has network-use copyleft implications for distributed or hosted
  services. Whether that is acceptable for this project is an owner decision.
- Fine-tuned weights may inherit licensing obligations from both the base
  checkpoint and the training code. No position is asserted here.
- The dataset is a set of screenshots of a commercial game. A CC BY 4.0
  declaration by the uploader does not by itself settle underlying IP rights.
- YOLOX is Apache-2.0 and is the permissive fallback if the AGPL route is
  rejected, but it is not approved, installed or supplied with weights.

**Status:** licences identified — **PASS**; licensing decision recorded and
attribution packaged — **BLOCKED**.

---

## 12. Audit I — Git and data safety

| Check | Result | Status |
| --- | --- | --- |
| Branch | `main` | — |
| Staged changes | `git diff --cached` empty | **PASS** |
| Commit or push performed | None | **PASS** |
| `models/YOLO11/yolo11n.pt` tracked | No | **PASS** |
| `models/YOLO11/yolo11n.pt` ignored | **No** (`?? models/YOLO11/yolo11n.pt`) | **FAIL** |
| Any weight file tracked | `git ls-files` finds no `.pt`, `.pth`, `.onnx` or `.ckpt` | **PASS** |
| Raw dataset tracked | `git ls-files datasets/external` is empty; rule `datasets/external/subway surfers/` is active | **PASS** |
| References tracked | `references/` rule is active; both the tree and ZIP are ignored | **PASS** |
| Export directory handling | Directory absent and no ignore rule for `datasets/exports/` | **FAIL** |
| Pre-existing modifications preserved | `.gitignore` (+3 lines), `brain/brain_simulator.py` (+28), `sensory/game_state.py` (+285/−1) remain as found | **PASS** |
| Audit wrote outside its two report files | No | **PASS** |

The working tree has 43 status entries: the three pre-existing tracked
modifications plus untracked Phase 3 artifacts. None was altered by this audit.

Two safety actions are required before any training artifact is created:

1. ignore `models/` or `models/**/*.pt` so checkpoints cannot be committed;
2. decide explicitly whether `datasets/exports/` is ignored (recommended) or
   tracked as a small manifest-only directory with images excluded.

**Status:** repository safety — **FAIL** until the checkpoint and export
handling are fixed.

---

## 13. Readiness classification

### 13.1 Already implemented

- `Detector` protocol and test-only `MockDetector`.
- ONNX Runtime detector with letterbox, inverse transform, YOLO raw decoding,
  class-aware NMS, confidence filtering and class-ID mapping.
- Detector configuration validation, optional SHA-256 verification and explicit
  missing-model errors.
- Evaluation harness with precision, recall, F1, AP@0.5, AP@0.5:0.95,
  per-class metrics, confusion, FP/FN taxonomies, bootstrap intervals, latency
  and memory.
- Fixed-split and five-fold LOGO evaluation CLI driven by the frozen manifest.
- Dataset curation, manifest lookup and contract validation.
- Perception → `GameState`, observation, tracking and temporal layers.

### 13.2 Verified working during this audit

- Manifest counts, path resolution, quarantine exclusion, class support and
  group atomicity recomputed from disk.
- Perception class schema (14 IDs, order) matches the manifest exactly.
- Missing-model construction raises the documented error.
- Checkpoint is a valid Ultralytics ZIP archive with recorded SHA-256.
- YOLOX extraction is complete and Apache-2.0.
- Root README and manifest hashes match their protected values.
- No staged changes and no tracked weights.

### 13.3 Implemented but not tested with YOLO11

- `OnnxRuntimeDetector` end-to-end (synthetic tensors only).
- `decode_yolo_raw` with a real `[1, 4+nc, anchors]` YOLO11 export.
- Evaluation harness with real detector predictions.
- Class-map identity for a 14-class trained head.
- Latency and memory measurement on real YOLO11 inference.

### 13.4 Missing

- `datasets/exports/` and every file it should contain.
- Export tooling and export verification.
- Ultralytics ONNX export step.
- Ultralytics `.pt` detector adapter (or an approved ONNX-only workflow).
- Ultralytics results → prediction JSON converter.
- YOLO11-specific detector configuration (`has_objectness: false`, 640 input).
- Colab notebook or environment manifest.
- Licence decision record and dataset attribution in project notices.
- Git ignore rule for model weights; export handling policy.
- Independent test split (cannot be created from five recordings).

### 13.5 Blocked pending approval

- Installing Ultralytics (AGPL-3.0) or any training dependency.
- Accepting the YOLO11/AGPL route versus the YOLOX/Apache-2.0 fallback.
- Creating the dataset export.
- Training on Colab and downloading resulting weights.
- Committing any checkpoint or export.
- Making detection or perception claims from a trained model.

---

## 14. Risks and blockers

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Weights could be committed accidentally | Repository bloat and licence exposure | Add a `models/` ignore rule before training |
| Export drifts from the manifest | Split leakage or wrong counts | Generate only from `PHASE_3B1_SPLIT_MANIFEST.json`; verify 1,188/1,128 and 4,704/3,962 |
| Raw folder names used as the split | 903 train-folder images are valid and 275 valid-folder images are train | Use manifest assignments exclusively |
| YOLO11 output mis-decoded | Silent wrong boxes or scores | Set `has_objectness: false`, 640 input; smoke-test a known export |
| Class order mismatch | Every class metric becomes wrong | Assert model `names` equals manifest order before evaluation |
| `boots-powerup` / `jump-electric` absent from valid | Undefined AP reported as zero | Mark as unevaluable with support counts |
| Fixed valid split treated as test | Overstated generalisation | Label all results group-held-out validation; no test claim |
| AGPL obligations ignored | Distribution/hosting constraints | Record an explicit licence decision before training |
| Game imagery rights unresolved | Redistribution risk | Keep the dataset local; do not redistribute screenshots without review |
| Colab session loss | Lost training run | Save checkpoints and metadata to Drive; record versions and hashes |
| Small dataset (2,316 images) | High variance, weak small-object recall | Report per-class support, LOGO variance and confidence intervals |
| Portrait images letterboxed to 640 | Small objects shrink | Report size-stratified recall; consider portrait input only as a pre-registered follow-up |

**Hard blockers:** no export; no accepted licence decision; no YOLO11-tested
training or decoding path; checkpoint not ignored.

---

## 15. Exact next actions, in execution order

1. **Approve the licensing route.** Decide whether AGPL-3.0 YOLO11 training is
   acceptable, or switch to the Apache-2.0 YOLOX fallback. Record the decision
   and the dataset's CC BY 4.0 attribution in `THIRD_PARTY_NOTICES.md` and
   `REFERENCES.md`. No legal conclusion is implied by this audit.
2. **Fix Git safety.** Add `models/` (or `models/**/*.pt`) to `.gitignore` and
   decide the `datasets/exports/` policy. Verify with `git check-ignore -v` and
   confirm no weight is tracked. Do this before creating any export or weights.
3. **Implement the export.** Write a script that reads only
   `reports/PHASE_3B1_SPLIT_MANIFEST.json`, copies the 1,188 train and 1,128
   valid images and labels into `datasets/exports/yolo11_v15/`, writes a
   portable `dataset.yaml` with `path: .`, and copies the dataset attribution.
   Do not modify or move raw files.
4. **Verify the export.** Recompute counts (2,316 images, 8,666 boxes, 1,188 /
   1,128 split), assert 14 class names in manifest order, assert zero
   quarantined images, assert one label per image and no collisions, and record
   a SHA-256 export manifest.
5. **Add the YOLO11 path.** Either implement an Ultralytics `.pt` detector or
   make ONNX export the approved route. Set `has_objectness: false`,
   `input_size: [640, 640]`, keep the 114 letterbox and RGB order, and add a
   synthetic `[1, 18, 8400]` decoding test before touching real weights.
6. **Add the results adapter.** Convert Ultralytics predictions to the
   evaluation CLI's JSON/`EvaluationBox` form, preserving original-image
   coordinates and class IDs.
7. **Prepare Colab.** Pin versions, verify CUDA, upload the verified export,
   record the export hash and manifest hash, and pre-register epochs, batch
   size and seed.
8. **Train and export.** Fine-tune from `yolo11n.pt`, save `best.pt`,
   `results.csv` and run metadata, then export ONNX at 640 with a recorded
   opset.
9. **Evaluate locally.** Run `experiments/phase_3b/evaluate_detector.py` on the
   fixed valid split, report per-class metrics with support counts, mark
   `boots-powerup` and `jump-electric` as unevaluable, and optionally run the
   five LOGO folds for variance.
10. **Report honestly.** Label results as group-held-out validation, not test
    performance. Do not connect a detector to the connectome or claim
    biological perception until perception accuracy, licence and integration
    gates are all satisfied.

---

## 16. Audit J — final readiness decision

| Gate | Status |
| --- | --- |
| Curated dataset valid and leakage-free | **PASS** |
| Independent test split available | **FAIL** (structural, cannot be fixed) |
| Colab export exists and is verified | **FAIL** (missing) |
| Class mapping verified | **PASS** for schema; **BLOCKED** for a trained model |
| YOLO11 training configuration tested | **BLOCKED** |
| YOLO11 decoding/evaluation tested | **BLOCKED** |
| Colab environment specified | **PASS** (proposal only) |
| Licensing decision accepted and attribution recorded | **BLOCKED** |
| Git safety for weights and exports | **FAIL** |
| Reproducible evaluation plan | **PASS** (defined, not yet exercised with real predictions) |

**Final decision: BLOCKED — not ready to train.** The project has a valid
dataset contract, a working ONNX inference/evaluation architecture and a real
YOLO11n checkpoint, but it lacks the export, the YOLO11-specific adapter and
configuration, the licensing decision, and the Git safety rules that training
readiness requires. The next action is not a training run; it is approval of
the licensing route, Git hygiene, and a verified export.

---

## 17. Evidence index

| Evidence | Value or location |
| --- | --- |
| Root README SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` |
| Split manifest SHA-256 | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` |
| Checkpoint SHA-256 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` |
| Checkpoint size | 5,613,764 bytes |
| Checkpoint archive | 507 ZIP members; `version` = 3 |
| Ultralytics metadata | 8.2.100, 2024-09-25, AGPL-3.0 string |
| Raw dataset root | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8` |
| Raw images / curated / quarantined | 2,328 / 2,316 / 12 |
| Boxes / train / valid | 8,666 / 4,704 / 3,962 |
| YOLOX tree | `references/YOLOX-main/YOLOX-main`, 169 files, Apache-2.0, v0.3.0, no weights |
| Local Python / PyTorch | 3.13.14 / 2.10.0+cpu, CUDA unavailable |
| Local missing packages | torchvision, OpenCV, Ultralytics, onnx |
| Local resources | 15.34 GiB RAM (3.31 GiB available), 37.15 GiB free disk, RTX 3050 4 GB without CUDA |
| Existing modifications | `.gitignore`, `brain/brain_simulator.py`, `sensory/game_state.py` — preserved |
| Staged changes | None |
| Audit deliverables | This report and `PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.json` |
