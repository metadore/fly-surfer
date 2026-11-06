# Phase 3B — Dataset and Detector Status

**Status:** dataset contract and validation **PASS**; trained detector
**BLOCKED** (no approved weights, no dependency approval, no training run).

**Date:** 2026-11-06

**Scope:** record the curated dataset contract, the detector selection and the
reason no trained-detector result exists. Nothing in this report is a
detection-accuracy result. No model was trained, no weight was downloaded and
no package was installed, upgraded or removed.

---

## 1. Dataset contract

Source: `datasets/external/subway surfers/roboflow_v15_yolov8/...v15-added.yolov8`,
used read-only. The authoritative split is
`reports/PHASE_3B1_SPLIT_MANIFEST.json`
(SHA-256 `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d`).
The Roboflow `train`/`valid` folder names are **not** used as the split.

| Item | Value |
| --- | ---: |
| Raw images / label files | 2,328 / 2,328 |
| Quarantined empty labels | 12 |
| Curated images | 2,316 |
| Curated boxes | 8,666 |
| Classes | 14 |
| Image size | 606 × 1050 RGB, all included images |
| Groups | 5 (`subwayavitomp4`, `subwayedited2`, `subwayedtied`, `datasetfootage`, `subwayy1_1`) |
| Cross-split groups | 0 |
| Fixed split | train 1,188 images / 4,704 boxes; valid 1,128 / 3,962 |
| LOGO folds | 5, one held-out group each |

Duplicate boxes: 0. Boxes outside the normalised image: 0. Empty included
labels: 0. Image files opened: all. Validation status: **PASS**
(`experiments/phase_3b/results/dataset_validation.json`).

### 1.1 Classes that cannot be evaluated in the fixed split

- `boots-powerup`: 24 train boxes, **0 valid boxes**.
- `jump-electric`: 14 train boxes, **0 valid boxes**.

These are reported as *unevaluable*, not as zero. Low-support classes in valid
(`undercover-barrier` 19 boxes, `jump-hedge` 26, `ledge` 48, `jump-trash` 62,
`pogstick-powerup` 65) are flagged with their support counts.

### 1.2 What the labels do not contain

No player boxes, no coin boxes, no lane labels, no metric distance, no speed,
jump or roll labels, and no temporal object identities. The supported
experiment is **obstacle/train detection**, optionally terrain. It is not
complete game perception.

---

## 2. Detector decision

The full comparison is in `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md`.
Ranking on model merit and hardware fit:

1. **NanoDet-Plus-m @416** — 1.17M params, Apache-2.0, native YOLO labels.
   Training stack pins `torch<2.0`, incompatible with the installed Python
   3.13 / PyTorch 2.10.
2. **YOLOX-Nano @416** — 0.91M params, Apache-2.0, requires COCO JSON and a
   one-epoch smoke test.
3. **YOLOX-Tiny @416** — 5.06M params, Apache-2.0.
4. **YOLO11n / YOLOv8n @640** — AGPL-3.0; requires an explicit licensing
   decision. Not used.
5. **RT-DETR-R18** — 20M params / 60 GFLOPs; not a CPU-only 4 GB-laptop
   candidate. Not used.

Runtime target: ONNX Runtime 1.29.0 CPU, batch 1, explicit local weights, no
automatic download.

## 3. Environment facts at audit time

| Item | Value |
| --- | --- |
| Python | 3.13.14 |
| PyTorch | 2.10.0+cpu (`torch.cuda.is_available()` = False) |
| ONNX Runtime | 1.29.0, `CPUExecutionProvider` only |
| Available RAM | 1.02 GiB |
| Free disk (C:) | 2.19 GiB |
| torchvision / OpenCV / ultralytics | not installed |

No package was installed to change this state.

---

## 4. Why trained-detector acceptance is BLOCKED

1. **Weight approval:** no checkpoint license was accepted and no weight was
   downloaded.
2. **Dependency approval:** torchvision, OpenCV, pycocotools/ultralytics would
   be new dependencies; installing them was not approved.
3. **Training environment:** NanoDet's pinned stack conflicts with Python
   3.13 / PyTorch 2.10; a separate 1.5–2.5 GB environment was not created.
4. **Resource gate:** 1.02 GiB available RAM and 2.19 GiB free disk are below a
   safe training budget (planning estimate 1.5–4 GB training RSS).
5. **Protocol freeze:** the pre-registered protocol is written, but no run was
   approved to start.

These are approval/resource blockers, not model failures. No detector metric
is fabricated to fill the gap.

---

## 5. Placeholder used by the implemented chain

`perception/detector.py` provides `MockDetector` for plumbing tests only. It
returns scripted records; it ignores pixels. It is **never** an accuracy
baseline and its output must not be described as recognition.

A real adapter (`OnnxRuntimeDetector` in `perception/inference.py`) is
implemented for letterboxing, decoding, class-wise NMS, inverse mapping and
provenance checks, and is exercised with synthetic tensor outputs in tests.
It has not been run against model weights.

---

## 6. Limitations

- No independent test split exists; any future fixed-split or LOGO result is
  group-held-out validation, not test performance.
- Class roles are name-derived hypotheses, not verified game mechanics.
- Many obstacle/terrain classes have p10 heights of 15–27 px; at 416 square
  that becomes 6–11 px, so misses are likely.
- Severe class imbalance (1,617 `train` boxes vs 14 `jump-electric`).
- Complete game perception is not achievable with these labels (no player,
  coin, lane, speed, distance or temporal identity labels).

## 7. Evidence files

- `reports/PHASE_3B0_DATASET_AUDIT.md` / `.json`
- `reports/PHASE_3B02_V15_DATASET_AUDIT.md` / `.json`
- `reports/PHASE_3B1_DATASET_CURATION.md` / `.json`
- `reports/PHASE_3B1_SPLIT_MANIFEST.json`
- `reports/PHASE_3B2A_INFERENCE_ARCHITECTURE.md`
- `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md` / `.json`
- `experiments/phase_3b/results/dataset_validation.json` (status `PASS`)
- `experiments/phase_3b/results/detector_evaluation.json` (status `blocked`)
