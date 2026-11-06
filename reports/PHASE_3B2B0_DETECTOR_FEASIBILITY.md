# Phase 3B.2B.0 — Detector Selection and Experiment Design

**Status:** audit and design only. No detector was trained, no weights were
downloaded, no package was installed, and no image or label was modified.
Nothing in this report is a detection-accuracy result.

**Date:** 2026-11-05

**Scope:** decide whether a trained detector can be built on this machine,
select a shortlist of suitable detectors, define a leakage-free evaluation
protocol for the curated v15 split, and specify how a real detector would
implement the existing Phase 3B.2A `Detector` protocol.

**Non-goals:** training, weight download, dependency installation, changes to
`perception/`, GameState semantics, simulator integration, temporal
association, reinforcement learning, or game automation.

---

## 1. What this phase establishes

1. The current machine is expected to be able to run tiny detectors on CPU,
   but this was not measured, and it cannot train or run them on the GPU
   without a CUDA-enabled framework that is not installed. Free disk and
   available RAM are the binding constraints.
2. The v15 data supports a **14-class obstacle/train detection experiment**
   on a group-held-out split. It does **not** support complete game
   perception: there are no player, coin, lane, speed, jump, roll, metric
   distance or object-identity labels.
3. The preferred permissive-license model is **NanoDet-Plus-m** at 416×416.
   Its training stack is old (PyTorch < 2.0, PyTorch Lightning < 2.0) and is
   incompatible with the installed Python 3.13 / PyTorch 2.10 environment, so
   training requires a separate environment or external hardware. The
   lowest-friction local permissive fallback is **YOLOX-Nano**, subject to a
   one-epoch smoke test.
4. There is **no independent test split** and it cannot be manufactured from
   the five available recordings. Fixed-split and LOGO results are
   group-held-out validation, not test performance.
5. The recommendation is **MODIFY**: the design is ready, but Phase 3B.2B.1
   must not start until the memory/disk gate, dependency approval, weight
   download approval and training-environment choice are resolved.

---

## 2. Hardware and software audit

### 2.1 Machine

| Item | Measured value | Note |
| --- | --- | --- |
| CPU | AMD Ryzen 5 5600H with Radeon Graphics | 6 physical cores / 12 logical |
| RAM | 15.34 GiB total, **1.02 GiB available** at audit time | Available fluctuates with other applications |
| Disk | C: 463.8 GiB total, **2.19 GiB free** | Measured at audit time |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU | 4,096 MiB total, 3,955 MiB free, driver 592.27 |
| OS | Windows 11, 10.0.26200 | x64 |

### 2.2 GPU status

The GPU is present but **not usable for PyTorch or ONNX Runtime inference** in
the current environment:

- `torch.__version__` is `2.10.0+cpu`; `torch.cuda.is_available()` is `False`.
- `torch.version.cuda` is `None`.
- `nvcc` is not on `PATH`.
- ONNX Runtime 1.29.0 exposes only `AzureExecutionProvider` and
  `CPUExecutionProvider`.
- No CUDA Toolkit was found (`nvcc` is absent), and no CUDA-enabled PyTorch
  or ONNX Runtime provider is available.

**Missing GPU information:** board partner, clocks, power limit, memory type
and bandwidth, PCIe generation, and CUDA compute capability were not queried.
No CUDA diagnostic was run because no CUDA runtime is installed. The 4,096
MiB figure is the driver-reported total, not a verified usable training
budget.

Installing a CUDA-enabled PyTorch stack would require roughly 2.5–3+ GB of
additional disk for the wheel and NVIDIA runtime libraries. That exceeds the
2.19 GiB currently free and was **not attempted**.

### 2.3 Installed software

| Component | Version | Relevance |
| --- | --- | --- |
| Python | 3.13.14 | Some detector training repositories predate 3.13 |
| PyTorch | 2.10.0+cpu | CPU training/inference only |
| ONNX Runtime | 1.29.0 (CPU) | Viable deployment runtime for exported models |
| TensorFlow | 2.21.0 | Present, not selected for this experiment |
| Pillow | 12.0.0 | Used by `perception/` |
| NumPy | 2.3.4 | Used by `perception/` |
| PyYAML | 6.0.3 | Used by `perception/` |
| psutil | 7.1.2 | Available for memory measurement |
| torchvision | **missing** | Needed by most PyTorch detectors |
| OpenCV (`cv2`) | **missing** | Needed by NanoDet/YOLOX training pipelines |
| `ultralytics` | **missing** | Not installed |

No package was installed or upgraded during this audit.

### 2.4 Consequences

| Workload | Feasible now? | Constraint |
| --- | --- | --- |
| CPU inference, NanoDet/YOLOX-Nano at 416 | Likely, must be measured | RAM is likely sufficient; peak RSS and latency unknown |
| CPU inference, YOLO11n/YOLOv8n at 640 | Likely but slower | Must be measured; no real-time claim |
| CPU training, nano model at 416 | **Unverified / likely blocked** | 1.02 GiB available RAM is below a safe training budget |
| GPU training or inference | **No** | No CUDA-enabled framework; disk insufficient to install one |
| RT-DETR-R18 training/inference | **No** | 20M parameters, 60 GFLOPs, transformer training cost |
| Large-model or high-resolution training | **No** | Disk, RAM and GPU constraints |

The machine is expected to be adequate for **evaluation of a small exported
model** and possibly for **nano-scale CPU training after memory/disk
remediation**, not for a conventional GPU training run.

### 2.5 Feasible model sizes (estimates, not measurements)

| Device | Usable now? | Comfortable envelope | Marginal envelope | Not suitable |
| --- | --- | --- | --- | --- |
| CPU (6C/12T, CPU-only PyTorch/ONNX Runtime) | Yes for inference | 0.9–2.6M params, about 1–1.5 GFLOPs at 416 (NanoDet-Plus-m, YOLOX-Nano) | 2.6–5M params, about 6–9 GFLOPs at 640 (YOLO11n, YOLOv8n, YOLOX-Tiny); latency must be measured | 20M params / 60 GFLOPs (RT-DETR-R18) for per-frame use |
| GPU (RTX 3050, 4 GB) | **No** — no CUDA-enabled framework installed | If a CUDA stack were available, 0.9–5M params at 416–640, batch 1 inference would likely fit in 4 GB | A 20M-parameter RT-DETR inference at batch 1 might fit in 4 GB, but is untested; 20M-parameter training at 640 in 4 GB is doubtful | Large models and high-resolution training |

These are size envelopes, not latency guarantees. CPU latency for the
"comfortable" envelope is expected to be tens of milliseconds, but the only
admissible numbers are local measurements on this machine. The GPU row is
counterfactual because no CUDA runtime is installed; it is included only to
answer the model-size question, not to claim usable GPU capacity.

---

## 3. Detector candidates

### 3.1 Method and caveats

Candidates were screened from official repositories and documentation. The
numbers below are the vendors' published COCO values on their own hardware
and backends. They are **not** v15 accuracy, and CPU latency figures are not
directly comparable across vendors.

Selection criteria, in order:

1. Permissive license suitable for a public research repository.
2. Small parameter count, weight size, memory and CPU latency.
3. Compatibility with YOLO-format labels or a low-cost conversion.
4. A clean path to the Phase 3B.2A `Detector` protocol.
5. Reproducible, offline evaluation.

### 3.2 Comparison

| Candidate | License | Params | FLOPs | Input | COCO mAP@0.5:0.95 | Vendor CPU latency | Weight size | Training labels |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **NanoDet-Plus-m** | Apache-2.0 | 1.17M | 0.9G / 1.52G | 320 / 416 | 27.0 / 30.4 | 5.25 / 8.32 ms (i7-8700) | 2.3 MB FP16 | YOLO TXT, VOC XML or COCO JSON |
| **NanoDet-Plus-m-1.5x** | Apache-2.0 | 2.44M | 1.75G / 2.97G | 320 / 416 | 29.9 / 34.1 | 7.21 / 11.50 ms | 4.7 MB FP16 | same |
| **YOLOX-Nano** | Apache-2.0 | 0.91M | 1.08G | 416 | 25.8 | 23.08 ms on ARM (third-party table) | ~1.8 MB FP16 | COCO JSON (conversion required) |
| **YOLOX-Tiny** | Apache-2.0 | 5.06M | 6.45G | 416 | 32.8 | not published in the screened source | ~10 MB FP16 (computed) | COCO JSON |
| **YOLO11n** | AGPL-3.0 | 2.6M | 6.5G | 640 | 39.5 | 56.1 ms CPU ONNX, 1.5 ms T4 | ~5–7 MB checkpoint | YOLO TXT (native) |
| **YOLOv8n** | AGPL-3.0 | 3.2M | 8.7G | 640 | 37.3 | 80.4 ms CPU ONNX | 6.53 MB checkpoint | YOLO TXT (native) |
| **RT-DETR-R18** | Apache-2.0 | 20M | 60G | 640 | 46.5 | not CPU-oriented | ~80 MB FP32 (computed) | COCO JSON |

Sources: [NanoDet model table](https://github.com/RangiLyu/nanodet),
[YOLOX model table](https://github.com/Megvii-BaseDetection/YOLOX),
[Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/),
[Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/),
[RT-DETR](https://github.com/lyuwenyu/RT-DETR). Weight sizes marked
"computed" are parameter counts times two (FP16) or four (FP32) bytes and are
approximate; they are not downloaded-file measurements.

**Weight availability and storage.** NanoDet COCO checkpoints are distributed
through the repository's release links and linked Google Drive entries; YOLOX
weights through GitHub releases; Ultralytics weights through its official
assets; RT-DETR weights through the official repository and Hugging Face. None
was downloaded in this phase. All are in the 2–80 MB range and fit in a local
artifact directory outside version control; each needs a SHA-256 and a license
sidecar, and none should be committed.

### 3.3 Training-format compatibility

| Candidate | Native label format | Conversion needed | Verified in this audit |
| --- | --- | --- | --- |
| NanoDet-Plus | YOLO Darknet TXT, VOC XML, COCO JSON | None for YOLO TXT | Yes, repository config `nanodet-plus-m_416-yolo.yml` |
| YOLOX | COCO JSON | YOLO TXT → COCO JSON | Yes, README states COCO format |
| YOLO11 / YOLOv8 | YOLO TXT | None | Yes, Ultralytics documentation |
| RT-DETR | COCO JSON | YOLO TXT → COCO JSON | Yes, official table uses COCO |
| EfficientDet-Lite | TFRecord / COCO | Not YOLO-format; TF Object Detection API | Screened out |

A conversion step is acceptable only if it is deterministic, writes derived
annotations outside the raw dataset, records the source label hashes, and is
validated by round-tripping a sample. It must never modify
`datasets/external/...`.

### 3.4 Licensing

- **NanoDet code:** Apache-2.0. The repository `LICENSE` file was checked
  directly. The license of the COCO checkpoints must be verified separately
  before download.
- **YOLOX code:** Apache-2.0. Checkpoint license must be checked separately.
- **RT-DETR code:** Apache-2.0.
- **Ultralytics YOLO11 / YOLOv8:** AGPL-3.0. AGPL network-use copyleft has
  consequences for a distributed or hosted project. It requires an explicit
  licensing decision, not an implicit one.
- **YOLOv7-tiny:** GPL-3.0; not shortlisted.
- **YOLOv5:** AGPL-3.0; not shortlisted.
- **EfficientDet (TensorFlow Models):** Apache-2.0 for the repository; the
  training pipeline and TFRecord format are the practical blockers.

No license was accepted or rejected on the user's behalf in this phase.

### 3.5 Screened out

| Candidate | Reason |
| --- | --- |
| EfficientDet-Lite0 | Tiny and permissive, but the TF Object Detection API/TFRecord pipeline is a large integration and training cost, and it is not YOLO-format. |
| YOLOv7-tiny | GPL-3.0. |
| YOLOv5n | AGPL-3.0; older architecture. |
| SSD MobileNet / SSDLite | COCO/TF or torchvision training pipeline; no YOLO-format path; weaker small-object behavior. |
| Newer Ultralytics generations | Same AGPL-3.0 constraint; no gain for this decision. They were not evaluated in detail. |

### 3.6 Ranked shortlist

**Ranking on model merit and fit to the hardware (assuming training can be
arranged):**

1. **NanoDet-Plus-m @416** — 1.17M parameters, 1.52 GFLOPs, 30.4 COCO mAP,
   8.3 ms vendor CPU latency, 2.3 MB FP16, Apache-2.0, native YOLO labels.
   Best size/accuracy/latency balance and the cleanest label path.
2. **YOLOX-Nano @416** — 0.91M, 1.08G, 25.8 mAP, Apache-2.0, ONNX Runtime
   demo. Lower accuracy and requires COCO JSON, but no Lightning dependency
   and a smaller training stack.
3. **YOLOX-Tiny @416** — 5.06M, 6.45G, 32.8 mAP. More accurate and still
   CPU-plausible, but roughly six times the compute of Nano and a larger
   training cost.
4. **YOLO11n @640** — 2.6M, 6.5G, 39.5 mAP, best tooling and native YOLO
   labels, but AGPL-3.0 and a 640 input that is slower on CPU.
5. **YOLOv8n @640** — 3.2M, 8.7G, 37.3 mAP, mature but AGPL-3.0 and slower
   than YOLO11n.
6. **RT-DETR-R18 @640** — 20M, 60G, 46.5 AP, Apache-2.0 but not a CPU-only,
   4 GB-laptop candidate and far heavier to train.

**Ranking if training must use the existing Python 3.13 / PyTorch 2.10
environment without a new interpreter:**

1. **YOLOX-Nano** — its requirements have no upper PyTorch pin; it still
   needs torchvision, OpenCV and pycocotools, and Python 3.13 compatibility
   is unverified. A one-epoch smoke test would be mandatory.
2. **YOLOX-Tiny** — same path, higher accuracy, higher cost.
3. **YOLO11n / YOLOv8n** — technically easiest, but AGPL-3.0.
4. **NanoDet-Plus** — **blocked** in this environment: its requirements pin
   `torch>=1.10,<2.0` and `pytorch-lightning>=1.9,<2.0`, which have no
   Python 3.13 support and would attempt to replace the installed PyTorch
   2.10. Training it locally requires a separate Python 3.10 environment or
   relaxed, untested pins.

The two rankings differ only because NanoDet's training stack is old. That is
an environment fact, not a model-quality judgement.

---

## 4. Dataset feasibility

### 4.1 Curation and fixed split

The authoritative manifest is
`reports/PHASE_3B1_SPLIT_MANIFEST.json` (SHA-256
`ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d`). The
raw dataset contains 2,328 images and 2,328 label files. Twelve empty labels
are quarantined, leaving **2,316 curated images** and **8,666 boxes**.

| Group | Images | Boxes | Fixed split |
| --- | ---: | ---: | --- |
| `subwayavitomp4` | 501 | 1,798 | train |
| `subwayedited2` | 392 | 1,580 | train |
| `subwayedtied` | 295 | 1,326 | train |
| `datasetfootage` | 504 | 1,681 | valid |
| `subwayy1_1` | 624 | 2,281 | valid |
| **Total** | **2,316** | **8,666** | |

Fixed split totals: **1,188 train images / 4,704 boxes** and **1,128 valid
images / 3,962 boxes**. Every included image is RGB and exactly **606×1050**
pixels. No included label is empty (minimum one box per image; maximum nine).

The split is group-atomic. A programmatic check found no group with images in
both splits, so there are **zero cross-split adjacent-frame pairs** by
construction. The original Roboflow `train`/`valid` folders are not used as
the evaluation split.

### 4.2 Per-class support

"Train" and "valid" are the fixed split from the manifest. Image counts are
images containing at least one box of that class. Median and p10 heights are
in original screenshot pixels.

| Class | GameState role (hypothesis) | Train boxes | Train images | Valid boxes | Valid images | Median H | p10 H | % H < 10 px at 416 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| boots-powerup | unsupported | 24 | 24 | **0** | **0** | 31.7 | 20.6 | 29.2% |
| boxtrain | train | 625 | 482 | 749 | 538 | 141.6 | 49.5 | 0.1% |
| jump-barrier | obstacle_low | 254 | 221 | 163 | 148 | 41.6 | 20.6 | 18.7% |
| jump-electric | obstacle_low | 14 | 14 | **0** | **0** | 43.9 | 15.5 | 28.6% |
| jump-hedge | obstacle_low | 18 | 17 | 26 | 21 | 49.9 | 22.5 | 15.9% |
| jump-roll-barrier | obstacle_low | 407 | 359 | 356 | 287 | 57.1 | 27.4 | 7.3% |
| jump-trash | obstacle_low | 34 | 33 | 62 | 44 | 46.7 | 21.7 | 17.7% |
| ledge | unsupported | 87 | 57 | 48 | 32 | 35.7 | 16.9 | 34.8% |
| pogstick-powerup | unsupported | 53 | 53 | 65 | 65 | 65.2 | 33.1 | 0.8% |
| ramp | unsupported | 606 | 444 | 617 | 501 | 116.2 | 51.9 | 0.0% |
| roll-barrier | obstacle_high | 147 | 141 | 162 | 149 | 109.3 | 49.4 | 0.3% |
| train | train | 1,617 | 883 | 1,174 | 839 | 180.0 | 50.0 | 0.0% |
| undercover-barrier | obstacle_high | 196 | 84 | 19 | 15 | 79.0 | 34.8 | 1.4% |
| wall | unsupported | 622 | 279 | 521 | 247 | 157.6 | 72.9 | 0.0% |

Role aggregates:

| Role group | Train boxes | Valid boxes |
| --- | ---: | ---: |
| `obstacle_low` | 727 | 607 |
| `obstacle_high` | 343 | 181 |
| `train` | 2,242 | 1,923 |
| unsupported / other | 1,392 | 1,251 |

Obstacle and train classes account for **70.4% of train boxes** and **68.4% of
valid boxes**. The unsupported classes are still present in the labels and
can be trained and evaluated as objects, but they do not map to the current
`GameState` obstacle/train schema.

### 4.3 Classes that cannot be evaluated in the fixed split

- `boots-powerup`: 24 train boxes, **0 valid boxes**.
- `jump-electric`: 14 train boxes, **0 valid boxes**.

These two classes are trainable but **unevaluable in the fixed valid split**.
Any fixed-split per-class AP for them is undefined, not zero. They must be
reported as "insufficient validation support", not silently omitted.

Low-support classes also need explicit flags: `jump-hedge` (26 valid boxes),
`undercover-barrier` (19 valid boxes, 15 images), `jump-trash` (62),
`ledge` (48), `pogstick-powerup` (65). Per-class metrics for these are
unstable and must carry their support counts.

### 4.4 LOGO folds

The five LOGO folds are defined in the manifest. Each fold trains on four
groups and validates on the fifth.

| Fold | Held-out group | Valid images | Valid boxes | Classes absent from held-out group | Classes absent from fold training |
| --- | --- | ---: | ---: | --- | --- |
| 1 | `datasetfootage` | 504 | 1,681 | boots-powerup, jump-electric, jump-trash, ledge, undercover-barrier | none |
| 2 | `subwayavitomp4` | 501 | 1,798 | boots-powerup | none |
| 3 | `subwayedited2` | 392 | 1,580 | boots-powerup | none |
| 4 | `subwayedtied` | 295 | 1,326 | jump-electric, jump-hedge, jump-trash, ledge, undercover-barrier | boots-powerup |
| 5 | `subwayy1_1` | 624 | 2,281 | boots-powerup, jump-electric | none |

Fold 4 is the only fold with `boots-powerup` boxes (24) in validation, and
that class is absent from its training groups, so it is untrainable in that
fold. `jump-electric` appears in validation only in folds 2 (2 boxes) and 3
(12 boxes). No fold provides a well-supported estimate for either class.

The LOGO folds are for variance and group-sensitivity analysis, not for
hyperparameter tuning and not as a substitute for a test set.

### 4.5 Object size and input resolution

All images are portrait 606×1050. A square 416 input letterboxes the content
to about 240×416 (scale 0.396); a square 640 input gives about 369×640
(scale 0.610). At 416, 7–35% of several obstacle/terrain classes have a
height below 10 pixels (table above). At 640 those fractions fall to roughly
0–8%.

Implications:

- **320×320 is too small** for this dataset. The p10 height of
  `jump-barrier` would be about 6 px.
- **416×416 is the practical minimum** for a first CPU-feasible experiment.
- **640×640** is the safer small-object setting for YOLO11n/YOLOv8n, at a
  higher CPU cost.
- A **portrait input such as 416×736** (both divisible by 32) preserves more
  vertical scale than 416×416 at about 1.77× the pixels. It is a reasonable
  pre-registered follow-up if the 416 baseline's false-negative analysis
  shows a small-object floor. It is not the first run because published
  baselines and pretrained weights assume square inputs, and the extra cost
  has not been measured.

### 4.6 What the dataset cannot support

v15 labels only the 14 object classes. It contains:

- **no player boxes** and no player state;
- **no coin boxes**;
- **no lane labels**;
- **no metric distance, speed, jump or roll labels**;
- **no temporal object identities**.

Therefore:

- Player and coin modalities remain unavailable and must be reported as such.
- Lane metrics can only use geometric assignment from box coordinates. They
  measure consistency with the configured lane geometry, not true lane
  semantics.
- Distance can only be the uncalibrated `bottom_edge_proxy`, not a game or
  metric distance.
- Jumping, rolling and speed cannot be observed from one frame and must stay
  at documented defaults.
- "Complete game perception" is not an achievable claim from this dataset.

### 4.7 Consequence for the first experiment

The first experiment is **v15 object detection with emphasis on obstacle and
train classes**. It is not "the game is perceived" and not a model of fly
vision. A successful run can establish only that a detector recovers some
labelled objects on group-held-out footage with measured error rates.

---

## 5. Evaluation protocol

### 5.1 Data rules

1. Resolve every image through `reports/PHASE_3B1_SPLIT_MANIFEST.json`.
   Never use the Roboflow `train`/`valid` folder names as the split.
2. Never train or evaluate on the 12 quarantined images.
3. Assert group-atomicity before every run: no group may appear in both
   train and validation.
4. Keep raw images, labels, `data.yaml` and the manifest read-only. Derived
   annotation files (COCO JSON or dataset lists) go in a separate derived
   directory outside the raw dataset.
5. Record SHA-256 hashes of the manifest, `data.yaml`, derived annotations
   and weights in the run metadata.

### 5.2 Training and model-selection protocol

- **Primary run:** train on the fixed train groups, evaluate on the fixed
  valid groups. This is the model-selection split.
- **Variance:** train one model per LOGO fold and report mean ± standard
  deviation across the five held-out groups. These models have larger
  training sets (1,812–1,815 images) than the primary run, so their absolute
  scores are not directly comparable to the fixed split.
- **No test split exists.** No result from this protocol may be described as
  independent test performance. A new recording is required for that claim.
- **No tuning on LOGO validation.** Hyperparameters and the confidence
  operating point are selected on the fixed valid split only.
- **If compute prevents all five LOGO folds,** report exactly which folds
  were run and do not claim a variance estimate. Do not average a subset and
  present it as five-fold variance.

Pre-registered primary selection rule:

> Select the operating point that maximises macro recall over
> `obstacle_low`, `obstacle_high` and `train` classes, subject to
> micro-averaged precision ≥ 0.80 at IoU 0.5. If no threshold satisfies the
> precision constraint, report the best achievable F1 and state that the
> constraint failed.

This favours not missing obstacles, while preventing a degenerate
"detect everything" solution. It must be fixed before validation results are
inspected.

### 5.3 Detection metrics

Report all of the following on the fixed valid split:

- **Precision, recall and F1** at IoU 0.5, micro and macro, with support
  counts.
- **AP@0.5** per class and **mAP@0.5** over classes with defined support.
- **mAP@0.5:0.95** using the COCO IoU sweep, per class and overall.
- **Per-class AP with support counts**; mark classes with fewer than 20
  validation boxes as low-support and unstable.
- **Confusion matrix at IoU 0.5**, including unmatched predictions as
  background and unmatched ground truth as false negatives.
- **False-positive taxonomy:** duplicate, localization error, background,
  class confusion.
- **False-negative taxonomy:** no prediction, below-threshold prediction,
  localization below IoU threshold, class mismatch. A manual sample is
  needed to identify genuinely unlabelled objects; annotation noise must be
  reported as such, not silently counted as a model success or failure.
- **PR curves** over a confidence sweep, not only a single threshold.

mAP alone is insufficient. It does not measure lane behaviour, distance
consistency, temporal stability or latency, so those are reported separately
in Section 6.

### 5.4 Confidence and NMS

- The pipeline's validation threshold is 0.25
  (`configs/perception_config.yaml`). Report game-facing metrics at 0.25 and
  at the pre-registered selected operating point.
- For evaluation, the detector should emit predictions down to a low floor
  (for example 0.05) so the PR curve is not truncated. The runtime may use a
  higher pre-filter, but the evaluation setting must be recorded.
- NMS is class-wise with a fixed IoU threshold (0.5 or 0.6, recorded per
  model) and a fixed maximum detection count. NMS settings are part of the
  model configuration and must not be tuned on validation after the fact.

### 5.5 Latency and memory

Measure in a fresh process, batch size 1, fixed thread count:

- **Detector-only latency:** preprocess + forward + decode + NMS.
- **Pipeline latency:** `PerceptionPipeline.run` on a loaded `ImageFrame`,
  including validation, lane assignment, scene building and GameState
  conversion.
- **End-to-end latency:** optionally include image decode.
- Warm up 20 iterations, then measure at least 200 images (or the full valid
  split). Report p50, p95 and p99, not only the mean.
- Record CPU model, thread count, Python/PyTorch/ONNX Runtime versions, and
  whether the GPU was used.
- **Peak memory:** process peak working set on Windows (for example
  `psutil.Process().memory_info().peak_wset`) for CPU. VRAM is not
  measurable in the current environment because no CUDA runtime is active.
- Do not compare the measured latency to a game frame budget unless the game
  frame rate has been independently established. 16.7 ms, 33.3 ms and 50 ms
  may be reported as reference budgets, not as verified game requirements.

### 5.6 Statistics and reproducibility

- Bootstrap 95% confidence intervals over images (for example 1,000
  resamples) for precision and recall. Report the number of images and boxes
  behind every number.
- Report per-fold results, not only a pooled mean.
- Fix random seeds and record them. CPU training may still be
  non-deterministic; report any observed run-to-run variation.
- Record: git commit (if any), manifest hash, config hash, derived-label
  hash, weight hash, package versions, hardware, thread count, exact
  commands and training duration.
- Preserve the test-only `MockDetector` and its tests. It is a plumbing
  fixture, never a baseline accuracy result.

### 5.7 Claims allowed and not allowed

Allowed after a completed run:

- "The detector achieved precision X and recall Y on the group-held-out
  validation groups, with the stated support and confidence intervals."
- "These classes had insufficient validation support and were not evaluated."
- "This is validation performance on the held-out recordings (two groups in
  the fixed split; five folds in LOGO), not independent test performance."

Not allowed:

- "The model perceives the game" or "the fly sees".
- "The detector generalises to Subway Surfers" beyond the measured groups.
- "mAP proves lane understanding, distance estimation or temporal
  continuity."
- Any claim that detector success demonstrates biological perception or
  neural coding.

---

## 6. Game-specific metrics

The current v15 labels make some game-relevant measurements possible and
others impossible. The distinction is explicit below.

| Metric | Definition | Data needed | Measurable now? | Caveat |
| --- | --- | --- | --- | --- |
| Obstacle recall | Micro recall over GT boxes whose configured `game_state_role` is `obstacle_low` or `obstacle_high` | GT boxes + config role map | **Yes** | Roles are name-derived hypotheses, not verified mechanics |
| Train recall | Micro recall over `boxtrain` and `train` | GT boxes | **Yes** | — |
| Per-lane recall / precision | Assign GT and predicted boxes with the same `LaneAssigner`; report per lane | GT boxes + lane config | **Yes** | Measures detection conditional on geometric lane, not true lane |
| Lane assignment agreement | Fraction of matched detections whose assigned lane equals the GT box's assigned lane | Matched boxes + lane config | **Yes, but weak** | Same geometry on both sides; not independent lane truth |
| Lane assignment accuracy | Agreement with human-verified lane labels | Manual lane annotation | **No** | Requires new annotation work |
| Distance-proxy error | MAE and bias between predicted and GT `bottom_edge_distance` for matched boxes | GT boxes + horizon config | **Yes** | Box-bottom accuracy, not game or metric distance |
| Temporal stability | Detection persistence, class-flip rate, lane-flip rate and box jitter across adjacent frames | Adjacent frames + association heuristic | **Partial** | Valid split has 833 candidate adjacent-frame pairs (an upper bound, because `subwayy1_1` collides frame IDs across two recordings), but no object-identity ground truth; requires new association code |
| False negatives for near obstacles | FN rate for `obstacle_low`/`obstacle_high` boxes with distance proxy ≤ 0.4 | GT boxes + distance config | **Yes, by definition** | "Dangerous" is a design threshold, not a verified game rule; report sensitivity at 0.3/0.4/0.5 |
| End-to-end latency | Pipeline time per frame, p50/p95/p99 | Timed runs | **Yes** | No verified game frame-rate requirement |
| Downstream GameState agreement | Agreement between predicted and GT-derived `GameState` (presence, type, lane, distance bucket, nearest object) | GT boxes + same adapter | **Yes** | GT-derived GameState is a deterministic label conversion, not true game state |
| Player detection | — | Player labels | **No** | v15 has no player class |
| Coin detection | — | Coin labels | **No** | v15 has no coin class |
| Speed / jump / roll | — | Temporal state labels | **No** | Not observable from one frame |
| Biological perception | — | — | **No** | Outside the scope of this project phase |

### 6.1 Downstream GameState agreement

This is the most useful bridge between detection metrics and the existing
Phase 3A interface. For each validation frame:

1. Build a **GT-derived GameState** by running the existing `GameStateAdapter`
   on ground-truth boxes, using the same config and lane geometry.
2. Build the **predicted GameState** by running the full perception pipeline
   on detector output.
3. Compare: obstacle present, obstacle type, obstacle lane, obstacle distance
   bucket, train present, train lane, and nearest-object selection.

Report exact-match rate and per-field agreement. This measures whether
detector errors change the downstream state, which mAP does not. It does not
make the GT-derived state "ground truth game state"; it is a label-derived
reference built by the same assumptions.

A nearest-object error is especially important: the adapter keeps only the
nearest obstacle and train. A detector that misses the nearest object can
have acceptable mAP but a wrong GameState. Report nearest-object misses
separately.

---

## 7. Integration plan

No integration code is written in this phase. This section specifies what a
future detector adapter must do.

### 7.1 Contract

`perception/detector.py` defines the protocol:

```python
class Detector(Protocol):
    def detect(self, frame: ImageFrame) -> Sequence[Any]: ...
    def describe(self) -> dict: ...
```

- `detect` receives the already cropped/resized `ImageFrame` and must return
  records in **processed-image pixels**.
- `detect` must not return screen pixels, normalized coordinates or model
  input pixels.
- `describe` must be JSON-safe and must identify the model, runtime, weight
  hash, license and `test_only: false`.
- The adapter must not import `brain.brain_simulator`, the sensory scheduler
  or any neural-mapping module.

### 7.2 Adapter algorithm

A future `NanoDetDetector` (or `YOLOXDetector`) should:

1. Read `frame.pixels` as an RGB `PIL.Image`; convert to a NumPy array.
2. Letterbox to the model input size, preserving aspect ratio, aligning to
   the model stride, and recording scale and padding.
3. Convert color order and normalization to exactly what the training
   pipeline used (see 7.3).
4. Run the backend (ONNX Runtime CPU preferred; PyTorch optional).
5. Decode boxes, scores and class IDs.
6. Apply class-wise NMS with a fixed, recorded IoU threshold.
7. Map boxes back through the inverse letterbox to processed-image pixels.
8. Return `RawDetection` values (or mappings accepted by
   `RawDetection.from_mapping`) with integer class IDs, float confidences and
   `x1, y1, x2, y2`.
9. Do not clamp, round to plausible values, or drop malformed boxes
   silently. The existing `DetectionValidator` is responsible for rejection
   with an explicit reason.

The existing `ImageFrame.processed_box_to_screen` then maps processed pixels
to screen pixels, and `screen_box_to_normalized` maps to viewport fractions
for lane assignment. The adapter must not duplicate or bypass that mapping.

### 7.3 Preprocessing and color order

This is a high-risk integration detail:

- The perception package supplies **RGB** pixels (`ImageFrame.pixels`, mode
  `RGB` by default).
- Many OpenCV-based detector training pipelines read images as **BGR** and
  normalize with BGR-ordered means.
- If the model was trained in BGR and is fed RGB, accuracy can degrade
  silently. The adapter must either convert RGB→BGR or train in RGB
  consistently, and must include a parity test on a fixed image against the
  training-time preprocessing.

Also fix and record:

- letterbox pad value (for example 114 or 0);
- interpolation method;
- mean/std normalization;
- input size and stride alignment;
- whether the model expects `uint8` or `float32`.

The perception config currently uses no crop and no resize
(`configs/perception_config.yaml`). If those values change later, the
detector still receives the processed image and returns processed-pixel
boxes; the existing scale factors handle the rest. Do not apply a second
resize in the caller.

### 7.4 Class IDs and names

- Train with the v15 IDs 0–13 in the exact order in
  `configs/perception_config.yaml`.
- Store the class-name list and class count in the exported model metadata.
- At load time, compare the model's class list with the configured
  `ClassSchema`. If the count, order or names differ, fail fast with a clear
  error. Never remap IDs silently.
- `class_name` may be included in the raw record, but the validator checks it
  against the schema. A mismatch is rejected, not corrected.

### 7.5 Confidence and NMS

- The detector should expose a configurable score floor, defaulting low
  enough for evaluation (for example 0.05). The pipeline's 0.25 threshold is
  authoritative downstream.
- Do not apply a hidden high threshold inside the detector that makes the
  configured threshold meaningless.
- NMS is class-wise. Record the IoU threshold and maximum detections.
- Do not use test-time augmentation in the first experiment; it multiplies
  latency and complicates reproducibility.

### 7.6 Bounding-box conversion

- Decode to `x1, y1, x2, y2` in model-input pixels.
- Undo padding and scaling: `x = (x_model - pad_x) / scale`.
- Do not clip to the letterboxed content rectangle before returning. A box
  that extends into padding should become an out-of-bounds processed-image
  box and be rejected by the validator with `OUT_OF_BOUNDS`. Clipping it
  would fabricate a valid detection.
- Return floats; the validator handles finite-value and geometry checks.

### 7.7 Device and runtime

- Default to CPU.
- Prefer ONNX Runtime `CPUExecutionProvider` for deployment: it is already
  installed, keeps the runtime dependency-light, and avoids importing
  PyTorch in the perception package.
- If a CUDA provider is requested and unavailable, fail clearly. Do not
  silently fall back to CPU while reporting GPU use.
- Record the provider actually used in `describe()`.
- Set the intra-op thread count explicitly for reproducible latency.
- Batch size is 1 per frame. Micro-batching is an evaluation optimization,
  not part of the per-frame contract.

### 7.8 Model loading and provenance

- Load weights from an explicit local path. **No automatic download.**
- Verify a recorded SHA-256 before loading; refuse a mismatch.
- Keep weights outside version control (or in an ignored artifact
  directory); never commit weights.
- Store the code license, weight license/source and export command in a
  sidecar metadata file.
- Verify ONNX export parity against the training framework on a fixed set of
  images before trusting the exported model.

### 7.9 Error handling

Use explicit exceptions, not empty results:

| Condition | Behaviour |
| --- | --- |
| Weight file missing | Raise a load error; do not run |
| Weight hash mismatch | Raise a provenance error; do not run |
| Class list/count mismatch | Raise a schema error; do not run |
| Unsupported input shape or mode | Raise an input error |
| Backend/provider failure | Raise an inference error |
| Backend returns structurally invalid output | Raise a decode error |
| Model returns no detections | Return an empty list (a legitimate result) |

A detector failure must never be converted into an empty scene. "No objects"
and "the detector broke" are different scientific outcomes.

### 7.10 Inference timing

Record `time.perf_counter()` around the full `detect` call. If a CUDA backend
is ever used, synchronize before stopping the timer. Keep model load time out
of per-frame latency and report it separately. A `last_timing_ms` attribute
or an evaluation-harness measurement is preferable to changing the
`Detector` return type.

### 7.11 Recommended interface additions (not implemented)

These are recommendations for a later, separately approved change:

- an optional `warmup()` method on the detector;
- structured metadata fields in `describe()` for weight hash, license,
  runtime, provider, input size and color order;
- a shared detector exception base class in `perception.detector`;
- an optional detector section in `configs/perception_config.yaml`
  (model path, device, score floor, NMS IoU, thread count).

None of these is required to implement the current protocol. They must not
be added in this phase.

### 7.12 Scientific boundary

The detector is a **measurement instrument for labelled objects**. It is not
a model of the fly brain, and its training is not a claim about biological
learning. It must not be connected to:

- `brain/brain_simulator.py`;
- the Phase 3A sensory scheduler or population encoders;
- neural activity analysis;
- reward-modulated plasticity.

The fixed-connectome baseline and the Phase 3A calibration remain untouched.
A future connection, if ever proposed, requires a separate phase, a separate
scientific question and explicit approval.

---

## 8. Risks and limitations

1. **No independent test split.** Five recordings cannot yield one. All
   reported scores are group-held-out validation.
2. **Environment is training-hostile.** 1.02 GiB available RAM and 2.19 GiB
   free disk at audit time are below a safe training budget. NanoDet's
   pinned PyTorch/Lightning versions conflict with Python 3.13 and PyTorch
   2.10.
3. **GPU is present but unusable.** No CUDA-enabled PyTorch or ONNX Runtime;
   installing one exceeds current free disk.
4. **Small objects.** Many obstacle and terrain classes have p10 heights of
   15–27 px; at 416 square that becomes 6–11 px. Misses are likely,
   especially for `jump-electric`, `jump-hedge`, `jump-barrier` and `ledge`.
5. **Severe class imbalance.** 1,617 `train` boxes versus 14
   `jump-electric` and 24 `boots-powerup` boxes in train. Macro metrics are
   unstable.
6. **Zero validation support** for `boots-powerup` and `jump-electric` in
   the fixed split; LOGO coverage is also sparse. These classes cannot
   support a generalisation claim.
7. **Annotation semantics are hypotheses.** Class roles are derived from
   names under the Phase 3B.1 policy; they are not verified game mechanics.
8. **No player, coin, lane, distance, speed, jump or roll labels.** Complete
   game perception is out of reach with v15.
9. **Internal redundancy.** `subwayy1_1` contains two recordings with
   colliding frame IDs (296 duplicate-ID pairs). Treating it as one atomic
   group prevents train/valid leakage, but the effective sample size is
   smaller than the image count suggests.
10. **Domain shift.** Fixed validation uses two recordings that are absent
    from training. That is a useful stress test but makes the score a
    cross-recording result, not a random-sample estimate.
11. **Preprocessing mismatch (RGB/BGR, letterbox, normalization)** can
    silently reduce accuracy. A parity test is mandatory.
12. **ONNX export drift.** Decode, NMS and output ordering can differ from
    the training framework. Verify parity before evaluation.
13. **AGPL-3.0.** Ultralytics models require a licensing decision before
    use in a distributed or hosted project.
14. **Metric misuse.** mAP does not measure lane behaviour, distance,
    temporal stability or latency. Game-specific metrics must be reported
    separately.
15. **No temporal model.** Single-frame detections can flicker. Temporal
    stability is only partially measurable now and is not implemented.
16. **Latency claims.** Vendor CPU numbers are from different hardware and
    backends. Only local measurements are admissible.

---

## 9. Estimated resource requirements

These are planning estimates, not measurements. They must be replaced by a
one-epoch or one-batch smoke test before any full training run.

| Resource | Estimate | Basis / caveat |
| --- | --- | --- |
| Model artifact, NanoDet-Plus-m | 2.3 MB FP16, ~4.7 MB FP32 | Vendor table / parameter count |
| Model artifact, YOLOX-Nano | ~1.8 MB FP16 | Vendor/third-party table |
| ONNX export | Same order as the weight file | Verify after export |
| Derived annotations / dataset lists | ~2–10 MB | COCO JSON or file lists |
| Logs and checkpoints | ~20–100 MB | Depends on checkpoint retention |
| New Python 3.10 environment for NanoDet | **~1.5–2.5 GB** | Python, PyTorch 1.13 CPU, Lightning, OpenCV, deps; verify before installing |
| CUDA PyTorch stack | **~2.5–3+ GB** | Exceeds current free disk; not attempted |
| Inference RSS, tiny model | ~300–800 MB | Estimate; measure in a fresh process |
| Training RSS, nano model, batch 4–8 @416 | **~1.5–4 GB** | Estimate; current 1.02 GiB available is likely insufficient |
| CPU latency, NanoDet-Plus-m @416 | ~10–25 ms | Vendor 8.32 ms on i7-8700; local backend differs |
| CPU latency, YOLOX-Nano @416 | ~15–35 ms | No comparable x86 vendor number; measure |
| CPU latency, YOLO11n @640 | ~60–120 ms | Vendor 56.1 ms on unspecified CPU; measure |
| Training time, nano model, 100 epochs, CPU | ~2–10 h per model | Rough estimate; depends on RAM, threads and augmentation |
| LOGO training, five folds | ~10–50 h | Five times the per-model estimate; likely impractical without remediation |
| GPU training, RTX 3050 4 GB | Not available now | Would require a CUDA stack; 4 GB would likely be enough for a nano model at 416, batch 8–16, but this is unverified |

A first experiment should therefore be **one model on the fixed split**, not
five LOGO models at once. LOGO is a follow-up only after the smoke test
establishes feasible per-epoch time and memory.

---

## 10. Recommendation

**Recommendation: MODIFY.**

Proceed with the design, but do **not** start Phase 3B.2B.1 under the current
environment. The detector choice and evaluation protocol are ready; the
execution preconditions are not.

### 10.1 Preferred technical choice

- **Model:** NanoDet-Plus-m, Apache-2.0, 416×416, starting from COCO
  pretrained weights (after license verification and download approval).
- **Fallback if local training is mandatory in the existing Python 3.13 /
  PyTorch 2.10 environment:** YOLOX-Nano at 416×416, subject to a one-epoch
  smoke test. YOLOX-Tiny is the accuracy-oriented fallback.
- **Not recommended now:** YOLO11n/YOLOv8n unless AGPL-3.0 is explicitly
  accepted; RT-DETR-R18 on this hardware.
- **Runtime:** ONNX Runtime CPU, batch 1, explicit local weights, no
  auto-download.
- **Scope:** 14-class v15 detection with obstacle/train emphasis. Not
  complete game perception.

### 10.2 Preconditions for Phase 3B.2B.1

1. **Memory and disk:** free at least ~4 GB of RAM for training and at least
   ~5 GB of disk; otherwise plan external training. Re-measure immediately
   before the run.
2. **Environment decision:** either
   - a separate Python 3.10 environment for NanoDet (with pinned PyTorch
     1.13 / Lightning 1.9), or
   - a smoke-tested YOLOX path in the current environment, or
   - external GPU training with the resulting ONNX weights brought back for
     local evaluation.
3. **Dependency approval:** explicitly approve every new package and version
   before installation. Do not upgrade the existing PyTorch, NumPy, Pillow or
   ONNX Runtime without a separate decision.
4. **Weight approval:** verify the checkpoint license and source; record the
   SHA-256; download only with approval; do not commit weights.
5. **Data approval:** approve the derived-annotation directory and confirm
   that the raw dataset, `data.yaml` and manifest remain read-only.
6. **Protocol approval:** freeze the fixed-split/LOGO protocol, the
   pre-registered operating-point rule and the class-support handling before
   inspecting results.
7. **Resource smoke test:** one epoch (or a fixed small number of batches)
   with measured time, peak RSS and disk use must pass before a full run.
   If it fails, stop and report the failure; do not reduce the scientific
   protocol to fit the machine silently.

If these conditions cannot be met, the correct outcome is **STOP before
training**, retaining this design. A design-only result is preferable to an
uncontrolled run whose memory, split or evaluation protocol cannot be
trusted.

### 10.3 What must not happen

- Do not train on the Roboflow folder split.
- Do not use the validation split as a test set in the report language.
- Do not report COCO mAP as v15 accuracy.
- Do not infer player, coin, lane, speed or distance ground truth that the
  labels do not contain.
- Do not connect the detector to the simulator, scheduler or plasticity
  code.
- Do not claim biological perception from object-detection accuracy.
- Do not begin Phase 3B.2B.1 without explicit approval.

---

## 11. Verification

### 11.1 Files created in this phase

| File | Purpose |
| --- | --- |
| `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md` | This report |
| `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.json` | Machine-readable mirror |

No source file, test, config, dataset file or existing report was modified.

### 11.2 Dependencies

No package was installed, upgraded or removed. The verified environment is:

```text
Python 3.13.14
torch 2.10.0+cpu
onnxruntime 1.29.0 (CPUExecutionProvider)
tensorflow 2.21.0
Pillow 12.0.0
numpy 2.3.4
PyYAML 6.0.3
psutil 7.1.2
torchvision: not installed
opencv-python: not installed
ultralytics: not installed
```

### 11.3 No model training or weight download

- No training command was run.
- No weight file was downloaded.
- A bounded maxdepth-4 workspace search found no `.pt`, `.pth`, `.onnx`,
  `.ckpt`, `.tflite`, `.engine` or `.safetensors` file.
- The only detector-related execution was read-only inspection of official
  repositories and documentation.

### 11.4 Protected files and data

| Check | Result |
| --- | --- |
| `README.md` SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` — matches |
| `references/` working tree | no changes |
| Raw v15 images | 2,328 images, unchanged; no file written |
| Raw v15 labels | 2,328 label files, unchanged; no file written |
| v15 `data.yaml` SHA-256 | `f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423` |
| Split manifest SHA-256 | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` |
| Connectome artifact SHA-256 | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |
| Phase 3A calibration artifacts | untouched |
| `configs/perception_config.yaml` | untouched |
| `perception/` code | untouched |

Raw dataset inventory at audit time: 2,328 images and 2,328 label files,
split by the original folders as 1,825 train / 503 valid. The curated
manifest, not these folders, defines the experiment split.

### 11.5 Tests

```text
python -m pytest -q
158 passed in 12.53s
```

All existing Phase 3A/3A.5/3B.0/3B.1/3B.2A tests still pass. No test was
added or changed in this phase.

### 11.6 Git state

No staging and no commit were performed. The pre-existing uncommitted
Phase 3A/3A.5/3B work remains as it was. The two new report files are inside
the untracked `reports/` directory, which `git status --short` collapses to:

```text
?? reports/
```

The files themselves are:

```text
reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md
reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.json
```

The previously reported tracked modifications remain:

```text
 M .gitignore
 M brain/brain_simulator.py
 M sensory/game_state.py
```

No destructive Git command was run.

---

## 12. Stop point

This phase stops here. Phase 3B.2B.1 (training) has **not** begun and must
not begin without explicit approval, a resolved training environment and the
preconditions in Section 10.2.
