# YOLO11n Release Readiness and Documentation Reconciliation

**Date:** 2026-11-25
**Task type (at creation):** read-only investigation plus one new proposal document. No
existing document was modified; the notebook and all model artifacts were left
unchanged; no licence was altered; nothing was uploaded; no repository was created; no
Git operation was run; no training or export was performed and no package was installed.
**Primary evidence:** `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` (the
recovery report; I1–I17) and the preserved notebook
`C:\Users\Hp\fruitfly\EVIDENCE-RECOVERY\yolo11n-training\FLY-SURFER_YOLO11n_Training.ipynb`
(SHA-256 `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da`).
**Licensing source:** `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md`
(read-only here; **not** modified, and **not** superseded by this document).

> **Status of this document.** It was written as a *proposal*: every replacement
> wording was a recommendation for the owner. **The owner approved implementation on
> 2026-11-25.** The corrections proposed here for the simulation and data repositories
> were then applied; the applied changes, verification results and any deliberately
> unedited items are recorded in
> `YOLO11N_DOCUMENTATION_RECONCILIATION_IMPLEMENTATION_REPORT.md`. The published
> research paper (Zenodo version 1.1) is protected and was **not** modified; its
> corrections are proposed separately in
> `RESEARCH_PAPER_V11_PROVENANCE_CORRECTION_PROPOSAL.md`.

---

## 0. Executive summary

**Verdict: the documentation reconciliation is ready for owner approval and
application; the model publication is NOT ready.** Two separate gates move
independently:

1. **Documentation gate — READY TO APPLY.** The recovered notebook is sufficient to
   state the detector's true provenance and to fix all public contradictions in the
   simulation repository. This document proposes exact replacement wording for every
   affected location (I1–I4, I17 and the additional occurrences in §4.2). Applying
   them is a documentation change only; it needs no retraining, no re-export and no
   artifact change.

2. **Publication gate — BLOCKED.** Republishing the *weights* in a new AGPL-3.0 model
   repository remains blocked by licensing and governance items that no technical step
   can clear: the absence of any recorded licence decision (I5), the absence of a
   written position from Ultralytics or counsel on whether fine-tuned weights are a
   covered work and what their Corresponding Source is, and the unresolved underlying
   game-image rights. Notebook recovery **narrows** the Corresponding-Source gap — it
   supplies the training source, the full hyperparameter record and the export
   command that the AGPL audit recorded as missing — but it does **not** resolve the
   licensing question, and must not be presented as doing so.

**What changed since the licensing audit.** That audit (`T_AGPL §6.3`, `§8`) recorded
the training notebook/script, the full hyperparameters and the export command as
"missing". They are now recovered and hash-verified. The three evidentiary gaps that
remain are: an **official** upstream checksum for `yolo11n.pt` (only a local hash
exists, I11), a **recorded licence decision** (I5), and the **game-imagery** question.
The first is closable by recording an accepted upstream hash; the other two require
the owner and, for the licensing one, a written position.

**What is never promised.** Bit-exact reproduction of `best.pt`. The run used
`deterministic=False`, an auto-selected optimiser, a never-hashed base download, and
its `results.csv`/`args.yaml` were not preserved. A third party can reproduce the
**procedure** and should expect metrics in the same range; byte-identical weights are
not guaranteed and must not be claimed.

---

## 1. Scope, method, and evidence base

### 1.1 Method

The recovery report was treated as the primary statement of fact. For each of its
seventeen inconsistencies the affected document was reopened and the **current text
re-read at the cited line** before any replacement was drafted, so the matrix below
quotes what is actually in the repository today, not a paraphrase. The two research
deliverables were then used as the fixed points of the canonical record (§2). The
licensing audit was consulted only for the boundary section; its conclusions are
carried forward unchanged.

### 1.2 Files inspected for this proposal (all read-only)

| File | Purpose |
|---|---|
| `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` | I1–I17, canonical values |
| `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` | licensing boundary |
| `README.md` (503 lines; claims at 194, 239–240, 494; licence table 355–365) | public prose |
| `THIRD_PARTY_NOTICES.md` (133 lines; 7–27, 76–93, 95–105) | notices |
| `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` (§1.3, §1.6, §1.7, §1.8, §1.9) | registry |
| `FLY-SURFER-DATA/documentation/PROJECT_DATA_OVERVIEW.md` §D | secondary description |
| `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` (508, 521, 543–550, 729–747) | readiness / governance |
| `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` (429–443) | export guidance |
| `reports/PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md` (§4; 155, 495–514) | ONNX contract, timings |
| `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` (4, 12, 32, 50–53, 336–337) | integration record |
| `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md` (575–577) | threshold provenance |
| `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` (93, 219, 339, 543) | metric attribution |
| `docs/PHASE_3_ROADMAP.md` (232–242) | roadmap metric attribution |
| `research_paper/src/03_data.md` (5), `05_perception.md` (7, 13, 29, 51, 120) | paper claims |
| `research_paper/src/FLY_SURFER_COMPLETE_RESEARCH_PAPER.md` (538, 760, 766, 782, 804, 873, 2023, 2269) | rendered paper |
| `research_paper/figures/yolo11_visuals/FIGURE_INDEX.md` (13) | figure provenance |
| `research_paper/RESEARCH_PAPER_VALIDATION_REPORT.md` (285) | scoped scope statement |
| `configs/detector_config.yaml` (44–55) | runtime thresholds + "not calibrated" label |

### 1.3 Files created by this task

| File | SHA-256 |
|---|---|
| `docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md` | this document |

---

## 2. Canonical training record

This is the single record against which every other statement should be checked. It is
built only from the recovered notebook and the recovery report. **The three evaluation
stages are kept strictly separate (§2.8)**; no number in this section mixes them.

### 2.1 Base model and checkpoint provenance

| Field | Value | Evidence strength |
|---|---|---|
| Base model | Ultralytics YOLO11n, COCO-pretrained (80 classes), task `detect` | notebook cell 21/31 |
| Download URL used by the main run | `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt` | printed in cell 31 |
| Local Drive copy found before training | `…/FLY-SURFER/training_results/YOLO11n/yolo11n.pt`, 5.35 MB, 80 COCO classes | cell 25 |
| Local Drive copy SHA-256 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | notebook hashed it (cell 25/38) |
| Repository copy | `models/YOLO11/yolo11n.pt`, 5,613,764 bytes, same SHA-256 | recomputed in recovery |
| Bytes actually downloaded in the main run | **never hashed** | — **unproven** (I11) |
| Expected-path miss | `models/YOLO11/yolo11n.pt` did not exist on Drive at run time | cell 21 |
| Head re-initialisation | `Overriding model.yaml nc=80 with nc=14`; `Remapped 1/14 cls head rows from pretrained weights by class name`; `Transferred 499/499 items` | printed by trainer |
| Model size | 181 layers, 2,592,570 parameters (fused at val: 2,600,210, 101 layers), 6.5 GFLOPs | printed |

**Reading.** The deployed model is a COCO→14-class fine-tune. The base checkpoint's
local hash is known and matches the repository copy, but the notebook never hashed the
bytes it downloaded, so identity between "the bytes Ultralytics fetched" and
`0ebbc80d…` is strongly plausible (same versioned URL, same size class, 80-class head)
yet **not proven** and **not anchored to an official upstream checksum** (I11).

### 2.2 Dataset: version and split

| Field | Value |
|---|---|
| Dataset | Subway Surfers Object Dataset, Roboflow Universe, workspace `horizon-cgt2k`, **version 15** |
| Dataset licence | CC BY 4.0, as declared by the uploader (`horizon-cgt2k`); underlying game-imagery rights unresolved |
| Source YAML SHA-256 | `f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423` |
| Portable export used | Phase 3B.2B.1 export, created `2026-11-06T15:23:36+00:00` |
| Export archive SHA-256 | `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff` (211,529,060 bytes, 4,638 members) |
| Public availability | identical to `dataset.zip` in HF dataset repo `metadore/fly-surfer-yolo11n-dataset` |
| Split method | **group-held-out by recording**, not random |
| Training groups | `subwayavitomp4` (501), `subwayedited2` (392), `subwayedtied` (295) |
| Validation groups | `datasetfootage` (504), `subwayy1_1` (624) |
| Train split | 1,188 images / 1,188 labels / 4,704 boxes |
| Validation split | 1,128 images / 1,128 labels / 3,962 boxes |
| Total | 2,316 images / 8,666 boxes / 14 classes; 0 images without boxes |
| Classes with zero validation boxes | `boots-powerup` (ID 0), `jump-electric` (ID 3) |

### 2.3 Training environment (all printed by the notebook)

| Component | Value |
|---|---|
| Python | 3.13.16 (main, Oct 1 2026) [GCC 13.3.0] |
| Platform | `Linux-6.6.159+-x86_64-with-glibc2.39` |
| PyTorch / torchvision | 2.11.0+cu130 / 0.26.0+cu130 |
| CUDA (torch build) | 13.0 |
| GPU | Tesla T4, 14.56 GB, 40 multiprocessors |
| System RAM | 12.67 GB total |
| Colab disk | 112.64 GB |
| CPU (ONNX validation) | Intel Xeon @ 2.00 GHz |
| Ultralytics | **8.4.202** (`%pip install ultralytics==8.4.202`; 8.4.203 was available and not taken) |
| Ultralytics dependencies added | `ultralytics-platform` 0.1.104, `ultralytics-thop` 2.2.5 |
| ONNX / ONNX Runtime | onnx 1.23.2 (installed in the export cell) / onnxruntime 1.31.1 (auto-installed by Ultralytics) |
| Other pinned | numpy 2.4.6, matplotlib 3.10.0, opencv-python 5.0.0.93, pillow 11.3.0, requests 2.32.4, psutil 5.9.5, polars 1.35.2, protobuf 6.33.6, ml_dtypes 0.6.0 |
| Project specification mismatch | readiness audit specified Python 3.10–3.12; the run used 3.13.16 (I10) |

### 2.4 Training arguments (exactly as executed, cell 31)

```python
model = YOLO("yolo11n.pt")                 # auto-downloaded from the v8.4.0 release
model.train(
    data="/content/FLY-SURFER/dataset_colab.yaml",   # runtime YAML, not the archive's dataset.yaml
    epochs=50, patience=15, imgsz=640, batch=16, workers=2, device=0,
    amp=True, cache="ram", optimizer="auto", seed=20261106,
    deterministic=False, val=True, plots=True, save=True, save_period=5,
    close_mosaic=10,
    project="/content/drive/MyDrive/FLY-SURFER/training_results/YOLO11n",
    name="yolo11n_14class_grouped_v1", exist_ok=True, verbose=True,
)
```

Key **resolved** defaults printed by Ultralytics 8.4.202 (not chosen by the notebook):
`nbs=64`, `lrf=0.01`, `momentum=0.937`, `weight_decay=0.0005`, `warmup_epochs=3.0`,
`warmup_momentum=0.8`, `warmup_bias_lr=0.1`, `cos_lr=False`, `fraction=1.0`,
`pretrained=True`, `single_cls=False`, `rect=False`, `freeze=None`, `resume=False`,
`box=7.5`, `cls=0.5`, `dfl=1.5`, `iou=0.7`, `max_det=300`.

Augmentation defaults in force: `mosaic=1.0` (off for the last 10 epochs via
`close_mosaic=10`), `fliplr=0.5`, `flipud=0.0`, `hsv_h/s/v=0.015/0.7/0.4`,
`degrees=0`, `translate=0.1`, `scale=0.5`, `shear=0`, `perspective=0`, `mixup=0`,
`cutmix=0`, `copy_paste=0`, `erasing=0.4`, `auto_augment=randaugment`, `augment=False`;
plus an Albumentations block at `p=0.01` (Blur, MedianBlur, ToGray, CLAHE).

Run facts: 50/50 epochs; `0.374 h` wall time; 75 iterations/epoch; 36 validation
iterations; GPU memory 2.53→2.68 GB; AMP checks passed.

### 2.5 Actual optimiser and resolved learning rate (stdout only)

```
optimizer: 'optimizer=auto' found, ignoring 'lr0=0.01' and determining best 'optimizer' and 'lr0' automatically...
optimizer: AdamW(lr=0.000556, momentum=0.9) with parameter groups 81 weight(decay=0.0), 88 weight(decay=0.0005), 87 bias(decay=0.0)
```

- Optimiser actually used: **AdamW**, initial LR **5.56 × 10⁻⁴**, momentum 0.9,
  weight decay 5 × 10⁻⁴ on decayed groups and 0.0 on weight/bias groups.
- The configured `lr0=0.01` was **ignored** because `optimizer=auto`.
- The value is a **derived** rule output, not a chosen hyperparameter; the same value
  was produced for the smoke test at `batch=4`.
- Neither the optimiser name nor the LR exists in any persisted artifact
  (`model_config.json` omits both; `args.yaml` was not preserved).

### 2.6 Export configuration (cell 35)

```python
onnx_path = model.export(format="onnx", imgsz=640, opset=17,
                         simplify=False, dynamic=False, half=False, device=0)
```

Export log: input `(1, 3, 640, 640)` BCHW → output `(1, 18, 8400)`; `onnx 1.23.2`,
`opset 17`; success in ~1.1 s; file 10.1 MB.

### 2.7 ONNX input/output contract (from the artifact's own metadata)

| Item | Value |
|---|---|
| Input | `images`, `[1, 3, 640, 640]`, NCHW, RGB, float32 in `[0,1]` |
| Output | `output0`, `[1, 18, 8400]` = 4 box values (`cx, cy, w, h` in 640-px) + 14 class scores |
| Objectness | none |
| Class activation | sigmoid already inside the graph; do not re-apply |
| NMS | external, per class |
| `imgsz` / `stride` | `[640, 640]` / `32` |
| `batch` / `end2end` | `1` / `False` |
| `names` | 14-class identity map, IDs 0–13 |
| `task` / `head` | `detect` / `Detect` |
| Embedded `license` | `AGPL-3.0 License (https://ultralytics.com/license)` |
| Embedded `version` | `8.4.202` |
| Embedded `description` | `Ultralytics YOLO11n model trained on /content/FLY-SURFER/dataset_colab.yaml` |
| Embedded `date` | `2026-11-06T17:01:02.116695+00:00` |
| Embedded export `args` | `{'data': None, 'batch': 1, 'fraction': 1.0, 'quantize': None, 'nms': None, 'dynamic': False, 'simplify': False, 'opset': 17}` |

The ONNX `args.batch=1` is the exported graph's fixed batch, **not** the training batch
of 16.

### 2.8 Three distinct evaluation stages (never merge these)

| # | Stage | Backend / batch | Images | P | R | mAP50 | mAP50-95 | Where it lives |
|---|---|---|---:|---:|---:|---:|---:|---|
| **A** | Last in-training validation (epoch 50) | PyTorch, batch 32 | 1,128 | 0.917 | 0.827 | 0.895 | 0.687 | notebook epoch table only |
| **B** | Post-training `best.pt` validation (cell 31) | PyTorch, batch 16 | 1,128 | 0.927 | 0.827 | 0.899 | 0.688 | notebook only |
| **C** | **ONNX full validation (cell 37)** | ONNX Runtime 1.31.1 CPU | 1,128 | **0.9373102206978658** | **0.8108289132772389** | **0.8977760737241655** | **0.6877264204606104** | `metrics_summary.json`; registry §1.6; paper |

**Stage C is the published number**, and it is an ONNX CPU **re-validation**, not the
training run's own validation. Precision differs materially between B and C
(0.927 vs 0.9373) and is not rounding. Per-class tables exist for **B** and **C**
separately (recovery report §8.1/§8.2); only 12 classes appear because
`boots-powerup` and `jump-electric` have zero validation boxes and are unevaluable.

Production thresholds are **initial candidates** carried from
`model_config.json`: confidence **0.426**, IoU **0.7**, `max_det=300`. The 0.426 literal
has **no recorded derivation** (I14) and `configs/detector_config.yaml` correctly labels
both "not calibrated".

### 2.9 Reproducibility limitations (summary; expanded in §5)

1. `deterministic=False`; no deterministic-algorithm/cuBLAS setting recorded.
2. Optimiser and LR chosen by Ultralytics 8.4.202 internals (version-dependent rule).
3. Base checkpoint's downloaded bytes never hashed; no official upstream checksum.
4. `results.csv`, `args.yaml`, all plots and the per-epoch `epoch*.pt` files not
   preserved; the epoch that produced `best.pt` is therefore unknown (tied best at
   epochs 48/49).
5. The Colab image is a moving target; no container digest recorded.
6. GPU-level non-determinism (atomic reductions, cuDNN autotuning) uncontrolled.

---

## 3. Inconsistency resolutions (I1–I17)

**Severity scale used below**

| Code | Meaning | Publication effect |
|---|---|---|
| **S1** | Public factual contradiction (states the opposite of the evidence) | Must fix before publication |
| **S2** | Public metric/provenance misattribution | Must fix before publication |
| **S3** | Governance gap (process, not prose) | Must resolve before publication |
| **S4** | Verifiability gap (cannot be settled from evidence) | Must be disclosed; prose alone cannot fix it |
| **S5** | Documentation precision / staleness | Should fix; non-blocking |
| **S6** | Internal evidence-hygiene note (notebook, not repo) | Record only; no repo edit |

For each item: **Location**, the **current claim** (re-read at the line), the
**recovered evidence**, **why it is inconsistent**, a **proposed replacement**, and
**severity / blocking**.

### I1 — README says the dataset was not used to train

- **Location:** `README.md:194` (§ "How it was used").
- **Current claim:** "The dataset was **not** used to train, fine-tune or tune any project model."
- **Recovered evidence:** 50 epochs on 1,188 curated training images; `pretrained=True`;
  `Overriding model.yaml nc=80 with nc=14`; ONNX metadata description names
  `/content/FLY-SURFER/dataset_colab.yaml`.
- **Why inconsistent:** direct factual contradiction — the dataset trained the project's
  detector.
- **Proposed replacement:**
  > The dataset was used to train the project's YOLO11n detector — a 50-epoch fine-tune
  > of a COCO-pretrained checkpoint on the 1,188-image group-held-out training side,
  > run in Google Colab on 2026-11-06 with Ultralytics 8.4.202 — and to evaluate it on
  > the 1,128-image validation side. Raw images and the derived export are excluded by
  > `.gitignore` and are not redistributed; only the six visual-documentation figures
  > and their provenance index are tracked. The trained weights and ONNX export are
  > likewise not redistributed (see §8).
- **Severity:** **S1**. **Correction required before publication: YES.**

### I2 — README says the detector was not fine-tuned

- **Location:** `README.md:239–240`.
- **Current claim:** "The detector is used as a fixed, externally trained component and was not retrained or fine-tuned."
- **Recovered evidence:** COCO→14-class fine-tune with a re-initialised head
  (`Remapped 1/14 cls head rows…`, `Transferred 499/499 items`), 50 epochs.
- **Why inconsistent:** the model *is* a fine-tune. It is true only that the simulation
  code does not retrain it.
- **Proposed replacement:**
  > The detector was fine-tuned once for this project — COCO-pretrained YOLO11n to 14
  > classes, in Colab on 2026-11-06 — outside this repository, then frozen as a versioned
  > ONNX artifact. It is not retrained or fine-tuned by the simulation code.
- **Severity:** **S1**. **Correction required: YES.**

### I3 — README limitations repeat the claim

- **Location:** `README.md:494` (numbered limitations list).
- **Current claim:** "The detector was not trained or calibrated here; its reported metrics are provenance from its training environment."
- **Recovered evidence:** training happened outside the repo (not "here" in the
  filesystem sense) but *for* the project; the second clause is accurate.
- **Why inconsistent:** the first clause reads as "never trained", which the notebook
  contradicts; "here" is ambiguous between "in this repository" and "by this project".
- **Proposed replacement:**
  > The detector was trained outside this repository (a 50-epoch 14-class fine-tune in
  > Colab, 2026-11-06) and is consumed here as a fixed ONNX artifact; it is not
  > retrained or recalibrated by this repository's code. Its reported metrics are
  > validation results from that training environment, not re-measured here.
- **Severity:** **S1**. **Correction required: YES.**

### I4 — Model registry misattributes the metrics

- **Location:** `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md:78` (§1.6).
- **Current claim:** "Reported by the training run and copied into `metrics_summary.json`; measured on 1,128 grouped-validation images with the ONNX CPU backend:"
- **Recovered evidence:** the numbers are **evaluation C**, a separate post-training
  ONNX CPU re-validation; the training run's own validation is A (epoch 50,
  P=0.917) and B (`best.pt`, P=0.927), both different from C (P=0.9373).
- **Why inconsistent:** the backend clause is right; the provenance clause assigns the
  numbers to the wrong stage. "Reported by the training run" conflates the in-training
  PyTorch validation with the later ONNX re-validation.
- **Proposed replacement:**
  > Produced by a post-training re-validation of the exported ONNX graph with ONNX
  > Runtime (CPU) on the 1,128 group-held-out validation images, and written to
  > `metrics_summary.json`. These are **not** the in-training PyTorch validation
  > numbers; the ONNX re-validation reports a higher precision (0.9373 vs 0.927),
  > which is not rounding.
- **Recommended companion edit (§1.7, line 90):** keep "produced in the training
  environment" (accurate) but add: "The published figures are the ONNX CPU
  re-validation (stage C); the PyTorch `best.pt` validation was 0.927 / 0.827 /
  0.899 / 0.688."
- **Severity:** **S2**. **Correction required: YES.**

### I5 — Training executed while the readiness audit said BLOCKED

- **Location:** `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:548–550, 742`.
- **Current claim:** "Accepted licence decision for YOLO11 training — No record in the
  repository — BLOCKED"; "Official checksum for `yolo11n.pt` … BLOCKED"; "Game
  screenshot/IP rights … BLOCKED"; "Final decision: BLOCKED — not ready to train."
- **Recovered evidence:** the training ran on 2026-11-06; the notebook contains no
  approval record, no licence decision, no operator identity.
- **Why inconsistent:** the project's own governance gate said "not ready to train"
  and the training happened anyway. This is a **process** gap, not a text error.
- **Proposed resolution (not a retroactive approval):** create a dated **governance
  record** (e.g. `docs/research/YOLO11N_TRAINING_AUTHORISATION_RECORD.md`) stating:
  > Training was executed on 2026-11-06 before the readiness audit's BLOCKED items
  > were cleared. This record documents the actual execution and its date; it does not
  > constitute retroactive approval. The licence route for the resulting weights is
  > addressed in `YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` and the owner's
  > subsequent decision.

  The readiness audit itself stays as written (it is a historical record); the new
  record sits beside it.
- **Severity:** **S3**. **Resolution required before publication: YES** (the licence
  decision, not just the note).

### I6 — Zero-instance classes receive a non-zero per-class figure

- **Location:** notebook cell 31 printed per-class list (not a repository file).
- **Current claim (implicit):** `boots-powerup` and `jump-electric` print mAP50-95
  **0.688**, identical to the overall value.
- **Recovered evidence:** both classes have **zero** validation boxes; the validation
  table omits them; `MODEL_REGISTRY.md` §1.7 already says they are "unevaluable".
- **Why inconsistent:** a reader of the raw printout could mistake 0.688 for a measured
  per-class score; it is an indexing artefact of `metrics.box.maps`.
- **Proposed resolution:** no existing-file edit required (the registry is already
  correct). The **model card** must state explicitly:
  > `boots-powerup` (ID 0) and `jump-electric` (ID 3) have no validation instances on
  > this split and are unevaluable. Any printed per-class value for them is an
  > artefact and not a measurement.
- **Severity:** **S4**. **Disclosure required in model card: YES.**

### I7 — First training attempt failed on dataset paths

- **Location:** notebook cells 27–28.
- **Current claim (implicit):** the archive's `dataset.yaml` has `path: '.'`.
- **Recovered evidence:** running from `/content/FLY-SURFER/phase_3b2b1_yolo11n/`
  looked for `/content/valid/images` and failed; cell 28 wrote `dataset_colab.yaml`
  with an absolute `path`.
- **Why inconsistent:** not a contradiction — a reproducibility trap. The archive YAML
  cannot be used as-is from an arbitrary working directory.
- **Proposed resolution:** optional clarifying note in the export report or model repo:
  > The exported `dataset.yaml` uses `path: '.'`; resolve it to an absolute root (or
  > run from the export directory) before training. The recorded run used
  > `dataset_colab.yaml`, identical except for an absolute `path`.
- **Severity:** **S5**. **Correction required: NO** (recommended for the model repo's
  training notes).

### I8 — Drive state inconsistent across the early cells

- **Location:** notebook cells 3–9.
- **Current claim:** contradictory Drive-connected / mount flags across those cells.
- **Recovered evidence:** cell 3 credential error, cell 4 connected `False`, cell 7
  `ismount` `False`, cell 8 mounts successfully.
- **Why inconsistent:** the most consistent reading is a pre-restart session where
  `makedirs` created a local directory at the mount path — an **inference, not a fact**.
- **Proposed resolution:** none to repository text; the recovery report already records
  it. Readers of the notebook should read cell 8 as the start of the recorded run.
- **Severity:** **S6**. **Correction required: NO.**

### I9 — Execution counts are not a clean sequence

- **Location:** notebook metadata (cells 8, 11–18, 20–39 carry counts 1–29; others none
  yet hold outputs; cells 33/34 outputs are "hidden").
- **Current claim (implicit):** a reader might assume a single top-to-bottom run.
- **Recovered evidence:** outputs are not the product of one uninterrupted execution.
- **Why inconsistent:** sequencing metadata contradicts a naive reading.
- **Proposed resolution:** none to repository text; the recovery report §1.3 documents
  the caution. Any citation of the notebook must not claim a clean single run.
- **Severity:** **S6**. **Correction required: NO.**

### I10 — Environment/command exceeds the project's own specification

- **Location:** `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:508, 521` and
  `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md:429–443`.
- **Current claim:** audit proposes Python 3.10–3.12 and `epochs=100, deterministic=True,
  data="dataset.yaml", project="fly_surfer", name="yolo11n_v15"`; export report
  prescribes `data="/content/datasets/phase_3b2b1_yolo11n/dataset.yaml",
  project="/content/runs"`.
- **Recovered evidence:** the executed run used Python 3.13.16, `epochs=50`,
  `deterministic=False`, `data=dataset_colab.yaml`, `project=…/training_results/YOLO11n`,
  `name=yolo11n_14class_grouped_v1`.
- **Why inconsistent:** three different command variants exist; only the notebook ran.
  Both reports explicitly frame their commands as *proposals* ("not executed", "a
  starting point"), so they are not false — but a reader could mistake them for the
  recipe.
- **Proposed resolution:** do not rewrite the historical proposals. Instead, the model
  repo's training record uses the notebook's actual call (§2.4), and the provenance
  report remains the authority. Optionally append one line to the export report:
  > **Superseded by the executed run:** see `YOLO11N_TRAINING_PROVENANCE_RECOVERY.md`
  > for the command that actually ran (50 epochs, Python 3.13.16, `dataset_colab.yaml`).
- **Severity:** **S5**. **Correction required: NO** (historical proposals; the model
  repo supersedes them).

### I11 — Base checkpoint identity is inferred, not proven

- **Location:** notebook cell 31 (download) and `PHASE_3B2B1…:549`.
- **Current claim:** readiness audit says no official checksum for `yolo11n.pt` was
  available offline.
- **Recovered evidence:** local Drive copy SHA-256 `0ebbc80d…4ee1` matches the
  repository copy; the main run auto-downloaded and **never hashed** its download.
- **Why inconsistent/insufficient:** the local hash is not anchored to an official
  source, and identity of the downloaded bytes is inferred.
- **Proposed resolution:** record both facts and do not overclaim. Model card line:
  > Base checkpoint: official COCO-pretrained YOLO11n, fetched by Ultralytics 8.4.202
  > from the v8.4.0 release. A local copy hashes to `0ebbc80d…4ee1`, identical to the
  > repository copy; the bytes fetched during the run were not hashed, and no official
  > upstream checksum was recorded.
- **Severity:** **S4**. **Disclosure required: YES.** Optional follow-up: obtain and
  record an accepted upstream SHA-256 for the v8.4.0 `yolo11n.pt`.

### I12 — `best.pt`'s epoch is unknown

- **Location:** notebook / recovery report §6.2.
- **Current claim (implicit):** `best.pt` is "the best-epoch checkpoint".
- **Recovered evidence:** best validation mAP50-95 (0.689) ties at epochs 48 and 49;
  Ultralytics selects by weighted fitness; `results.csv` not preserved.
- **Why inconsistent/insufficient:** the selected epoch cannot be fixed from evidence.
- **Proposed resolution:** model card line:
  > The producing epoch of `best.pt` is not recorded; validation mAP50-95 peaked at
  > 0.689 on both epoch 48 and epoch 49. `results.csv` was written to cloud storage and
  > was not preserved.
- **Severity:** **S4**. **Disclosure required: YES.**

### I13 — The run may not have been the first in its directory

- **Location:** notebook cell 31 (`exist_ok=True`, resume branch not taken).
- **Current claim (implicit):** this was the first and only run of that name.
- **Recovered evidence:** `exist_ok=True` plus a missing resume log line means a prior
  `yolo11n_14class_grouped_v1` run could have been overwritten.
- **Why inconsistent/insufficient:** the notebook cannot exclude a prior run.
- **Proposed resolution:** model card line:
  > The run used `exist_ok=True`; the notebook cannot exclude an earlier run of the
  > same name having been overwritten.
- **Severity:** **S4**. **Disclosure required: YES.**

### I14 — 0.426 confidence threshold has no recorded derivation

- **Location:** notebook cell 39 → `model_config.json` →
  `configs/detector_config.yaml:44–55`.
- **Current claim:** "Initial candidates copied from the training run's `model_config.json`
  (confidence 0.426, IoU 0.7). They are starting points, not calibrated operating
  thresholds…" (config correctly labels them not calibrated).
- **Recovered evidence:** 0.426 is a hard-coded literal in cell 39; no cell computes,
  searches or justifies it.
- **Why inconsistent/insufficient:** the derivation is unrecoverable; only the value
  is recorded.
- **Proposed resolution:** model card line:
  > Confidence 0.426 and NMS IoU 0.7 are initial, uncalibrated candidates recorded in
  > the deployment config. The derivation of 0.426 is not documented.
- **Severity:** **S4**. **Disclosure required: YES.**

### I15 — Notebook acquisition date versus run date

- **Location:** preserved notebook file metadata.
- **Current claim (implicit):** citing the file's mtime as the training date.
- **Recovered evidence:** local mtime 2026-11-25 00:47; the run is dated **2026-11-06**
  by dataset-export timestamp, ONNX `date`, and the `smoke_test_20261106` directory.
- **Why inconsistent:** the mtime is when the file was saved locally, not the run date.
- **Proposed resolution:** no file edit required; every release document cites
  **2026-11-06** and must not cite the file mtime.
- **Severity:** **S5**. **Correction required: NO** (citation hygiene).

### I16 — No Colab-side attestation

- **Location:** notebook metadata.
- **Current claim (implicit):** the `.ipynb` is a record of a specific Colab execution.
- **Recovered evidence:** `metadata.colab.provenance` is empty; no URL, file id,
  account or per-cell timestamps.
- **Why inconsistent/insufficient:** the link from "this file" to "the execution" rests
  on internal consistency plus artifact hashes, not cryptographic attestation.
- **Proposed resolution:** model card line:
  > The notebook carries no Colab file id or provenance record. Artifact identity is
  > established by SHA-256 agreement between the notebook's own end-of-run hashes and
  > the deployed files, not by a third-party-signed execution record.
- **Severity:** **S4**. **Disclosure required: YES.**

### I17 — Phase 3B2B3 recorded a "trained 14-class" artifact but the README did not

- **Location:** `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:4` vs
  `README.md` / `THIRD_PARTY_NOTICES.md`.
- **Current claim:** the integration report calls the artifact "trained 14-class";
  the public prose calls it external and not trained.
- **Recovered evidence:** the artifact is a project fine-tune; the integration report is
  correct.
- **Why inconsistent:** the public documentation set is internally inconsistent about
  the detector's origin.
- **Proposed resolution:** resolved mechanically by applying I1–I3 and the §4.2 edits so
  all documents describe one provenance.
- **Severity:** **S1**. **Correction required: YES** (via I1–I3).

### 3.1 Summary table

| ID | Location | Class | Severity | Blocking? |
|---|---|---|---|---|
| I1 | `README.md:194` | dataset "not used to train" | S1 | **Yes** |
| I2 | `README.md:239–240` | "not retrained or fine-tuned" | S1 | **Yes** |
| I3 | `README.md:494` | "not trained … here" | S1 | **Yes** |
| I4 | `MODEL_REGISTRY.md:78` | metrics attributed to training run | S2 | **Yes** |
| I5 | `PHASE_3B2B1…:548–550,742` | BLOCKED but executed | S3 | **Yes** |
| I6 | notebook cell 31 | zero-class 0.688 artefact | S4 | Disclose |
| I7 | notebook cells 27–28 | `path: '.'` trap | S5 | No |
| I8 | notebook cells 3–9 | Drive-state inconsistency | S6 | No |
| I9 | notebook metadata | non-contiguous execution | S6 | No |
| I10 | audit `:508,521`; export `:429–443` | three command variants | S5 | No |
| I11 | notebook cell 31; audit `:549` | base hash unproven | S4 | Disclose |
| I12 | notebook §6.2 | unknown best epoch | S4 | Disclose |
| I13 | notebook cell 31 | possible prior run | S4 | Disclose |
| I14 | notebook cell 39 | 0.426 unexplained | S4 | Disclose |
| I15 | notebook mtime | date confusion | S5 | No |
| I16 | notebook metadata | no Colab attestation | S4 | Disclose |
| I17 | `PHASE_3B2B3:4` vs README | internal inconsistency | S1 | **Yes** |

---

## 4. Documentation correction matrix

### 4.1 Required documents (the minimum set the task names)

| Document | Location | Issue(s) | Proposed action | Severity | Blocking |
|---|---|---|---|---|---|
| `README.md` | 194 | I1 | Replace with §3/I1 text | S1 | Yes |
| `README.md` | 239–240 | I2 | Replace with §3/I2 text | S1 | Yes |
| `README.md` | 494 | I3 | Replace with §3/I3 text | S1 | Yes |
| `README.md` | 355–365 (licence table) | — | **No change**: row "YOLO11n weights / ONNX export — AGPL-3.0, not redistributed" is correct | — | No |
| `THIRD_PARTY_NOTICES.md` | 84–86 | I1-equivalent (A9) | Replace "The dataset is not used to train…; the detector weights come from the third-party YOLO11n release" with the notice-style wording in §4.2/A9 | S1 | Yes |
| `THIRD_PARTY_NOTICES.md` | 95–105 | — | **No change** beyond adding the notebook as a training-source artifact in the model-repo NOTICE (§6) | — | No |
| `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` | 78 (§1.6) | I4 | Replace with §3/I4 text; add stage-B values to §1.7 | S2 | Yes |
| `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` | 34 (§1.3 title) | precision | Retitle/annotate: "(partial — `model_config.json` records only epochs, image size, seed and framework version; the full recipe is in the recovered notebook, SHA `3eb5fef6…c5da`)" | S5 | No |
| `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` | 116 (§1.9) | staleness | Add the recovered notebook to the reproduction materials | S5 | No |
| `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` | 32, 50–53, 336–337 | I4-equivalent | Change "Training-run metrics" → "ONNX re-validation metrics (post-training, CPU)" | S2 | Yes |
| `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` | 548–550, 742 | I5 | **Do not edit** (historical record). Add the separate governance record (§3/I5) | S3 | Yes (decision) |
| `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` | 429–443 | I10 | Optional "superseded by executed run" line (§3/I10) | S5 | No |
| `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` | — | — | **Already correct**; it is the authority and needs no change | — | No |
| `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` | §6.3, §8 | staleness | **Do not edit here.** Its "missing training source / hyperparameters / export command" now have a recovered answer; update only in a new record or on owner instruction | — | No |

### 4.2 Additional contradictory statements found (not in I1–I17)

These repeat the same errors in other tracked files. All are public-facing except the
internal audits.

| # | Location | Current phrase | Proposed replacement | Severity | Blocking |
|---|---|---|---|---|---|
| A1 | `research_paper/src/05_perception.md:7`; `FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:760` | "used as a fixed, externally trained component and was not retrained, fine-tuned, or calibrated **during this project**" | "The detector was fine-tuned once for this project, outside the repository, before this paper's preparation; it was not retrained, fine-tuned, or calibrated to produce any figure or result reported here." | S1 | Yes |
| A2 | `research_paper/src/03_data.md:5`; `FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:538` | "two published connectomes and one externally trained detector" | "two published connectomes and one frozen detector, fine-tuned once outside this repository (Chapter 5)" | S5 | No |
| A3 | `research_paper/src/05_perception.md:120`; `FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:873` | "The detector is externally trained and its reported accuracy is not a result of this project." | "The detector was fine-tuned once outside the repository; its reported accuracy is a property of that training run and is not re-measured here." | S1 | Yes |
| A4 | `research_paper/figures/yolo11_visuals/FIGURE_INDEX.md:13` | "The model was not retrained, fine-tuned or calibrated **during this task**." | "The model was not retrained, fine-tuned or calibrated during this figure-generation task." (narrow, already largely true) | S5 | No |
| A5 | `reports/PHASE_3_ROADMAP.md:236` | "validation-split metrics **taken from the training run**" | "validation-split metrics from a **post-training ONNX CPU re-validation**" | S2 | Yes |
| A6 | `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md:93, 219, 339, 543` | "training-run metrics" / "the **training run's own** validation metrics" | "post-training ONNX CPU re-validation metrics" | S2 | Yes |
| A7 | `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:52` | "These are the training run's numbers" | "These are the post-training ONNX re-validation numbers" | S2 | Yes |
| A8 | `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md:576` | thresholds "carried over as candidates **from the training run**" | "carried over from the deployment config produced in the training notebook" | S5 | No |
| A9 | `THIRD_PARTY_NOTICES.md:84–86` | "The dataset is not used to train, fine-tune or tune any project model; the detector weights come from the third-party YOLO11n release" | "The dataset was used to fine-tune the project's YOLO11n detector (50 epochs, 2026-11-06); the weights and ONNX export are not redistributed and remain AGPL-3.0 (see below)." | S1 | Yes |

`FLY-SURFER-DATA/documentation/PROJECT_DATA_OVERVIEW.md` §D (lines 129–132) is **already
accurate** and needs no change.

### 4.3 Statements verified correct — do not over-correct

These look similar to the errors above but are true as written. They should be
**left alone** so the correction does not introduce new inaccuracies.

| Location | Text | Why it is correct |
|---|---|---|
| `research_paper/src/05_perception.md:29, 51`; complete paper `:782, :804` | "not retrained, fine-tuned, or calibrated **to produce any of these panels/for this figure**" | The figures were produced by forward inference only; no training occurred during figure generation. |
| `research_paper/src/05_perception.md:13`; complete paper `:766` | "These values were produced in the training environment; they were not re-measured on this host" | Accurate: ONNX validation ran in Colab (stage C). |
| `research_paper/RESEARCH_PAPER_VALIDATION_REPORT.md:285` | "No training … was executed. The YOLO11n detector was not retrained, fine-tuned, recalibrated, or modified" | Scoped to *that validation task's* actions, which is true. |
| `README.md:355–365` | "YOLO11n weights / ONNX export — AGPL-3.0, not redistributed" | Correct licence and distribution status. |
| `configs/detector_config.yaml:44–55` | "starting points, not calibrated operating thresholds" | Correct. |
| `MODEL_REGISTRY.md` §1.7 (zero-class, no test set) | "unevaluable without additional held-out captures" | Correct. |

---

## 5. Reproducibility assessment

### 5.1 What the recovered notebook lets a third party reproduce

1. **The training procedure** — the exact `train()` call, dataset YAML contents, class
   map, seed, epochs, batch, image size, patience, `close_mosaic`, and the full resolved
   hyperparameter set (including the auto-selected AdamW LR).
2. **The dataset identity** — archive SHA-256 `c04058ad…39eff`, publicly retrievable
   from the CC BY 4.0 HF dataset repo, with per-split and per-class counts.
3. **The export procedure** — the exact `model.export(...)` call and the ONNX metadata
   (opset 17, no simplify, no dynamic axes, fp32).
4. **The evaluation protocol** — three stages, their backends, batch sizes and the exact
   published numbers (stage C).
5. **The environment** — every version needed to load, export and evaluate.

That supports a **documented, procedure-level reproduction**: an independent run can be
executed and should land in the same metric range.

### 5.2 What cannot be guaranteed

| Gap | Why it blocks bit-exactness |
|---|---|
| `deterministic=False` | No deterministic-algorithm or cuBLAS setting; cuDNN autotuning and atomic reductions vary run to run. |
| Auto-resolved optimiser/LR | `optimizer=auto` selected AdamW at `lr=5.56e-4` by a version-specific internal rule; a different Ultralytics build or dataset size could pick another optimiser or LR. |
| Base checkpoint never hashed | The downloaded bytes were not hashed at run time; identity with `0ebbc80d…` is inferred. There is no official upstream checksum to anchor it. |
| `results.csv` and `args.yaml` missing | The exact per-epoch history and the run's own resolved-args file were not preserved; the selected epoch is unknown (tied at 48/49). |
| Non-preserved checkpoints/plots | `epoch*.pt`, all curves and confusion matrices exist only on unverified cloud storage. |
| Colab image drift | Python 3.13.16 (built 2026-10-01), CUDA 13.0, cuDNN 9.19, Triton 3.6.0; no container digest recorded. |
| No Colab attestation | `metadata.colab.provenance` empty; no URL/file id; the chain rests on internal consistency plus artifact hashes. |

### 5.3 The honest reproducibility claim

> The training **procedure** is fully documented and reproducible; metrics in the same
> range are expected. Bit-exact reproduction of `best.pt` is **not** claimed and should
> not be promised, because the run was non-deterministic, the optimiser was
> auto-selected, the base download was not hashed, and the training logs were not
> preserved.

Closing the gaps that are closable (they need no retraining):

- Retrieve and preserve `args.yaml`, `results.csv`, the run's `best.pt` metadata and the
  plot images from Drive, if the account still holds them.
- Record the SHA-256 of the `yolo11n.pt` actually downloaded, if the run's working copy
  survives.
- Record an **accepted upstream** SHA-256 for the v8.4.0 `yolo11n.pt`.
- Obtain the Colab notebook URL/file id for attestation.
- Re-pin the evaluation environment and archive the raw `metrics_summary.json`.

Bit-exactness itself would require re-running with `deterministic=True`, a pinned
container digest and full log preservation — a new experiment, out of scope here.

---

## 6. Proposed model-release package (separate repository, not created)

### 6.1 Design constraints

1. **Separate repository.** The weights, the notebook and the AGPL notices live in a
   new AGPL-3.0 repository, never in the MIT simulation repository (aggregate argument,
   licensing audit §5.2).
2. **No AGPL material in the MIT repo.** Do **not** add `best.pt`, `best.onnx`, the
   training notebook, or any `import ultralytics` code to `FLY-SURFER`. The notebook in
   particular imports Ultralytics and belongs only in the model repository.
3. **The dataset is not copied.** It stays under CC BY 4.0 in its own HF repository and
   is referenced by URL and SHA-256. Do not relicense it.
4. **Licensing is still pending.** Nothing here is authorised to be built or published
   until §7 clears.

### 6.2 Proposed directory structure

```
fly-surfer-yolo11n/                      # NEW separate AGPL-3.0 repository (not created)
├── LICENSE                              # AGPL-3.0 full text
├── NOTICE                               # Ultralytics copyright + AGPL declaration + dataset attribution
├── README.md                            # what the model is, how to load it, scope and limits
├── MODEL_CARD.md                        # HF-style card (see §6.4)
├── SHA256SUMS.json                      # manifest over every file in this repo
├── provenance/
│   ├── FLY-SURFER_YOLO11n_Training.ipynb     # byte-identical original (SHA 3eb5fef6…c5da)
│   ├── YOLO11N_TRAINING_PROVENANCE_RECOVERY.md
│   ├── ENVIRONMENT.md                        # §2.3
│   ├── train_args.yaml                       # RECONSTRUCTED from notebook (label it so)
│   ├── EXPORT.md                             # §2.6–2.7
│   └── REPRODUCIBILITY.md                    # §5
├── deployment/
│   ├── best.pt
│   ├── best.onnx
│   ├── model_config.json
│   ├── metrics_summary.json
│   └── dataset_attribution.txt
└── evaluation/
    └── PER_CLASS_ONNX.md                     # stage-C per-class table (recovery §8.2)
```

### 6.3 File inventory and status

| File | Source | Status now | SHA-256 |
|---|---|---|---|
| `LICENSE` | AGPL-3.0 text | exists upstream; copy | — |
| `NOTICE` | new | **must be written** | — |
| `README.md` | new | **must be written** | — |
| `MODEL_CARD.md` | new | **must be written** | — |
| `provenance/FLY-SURFER_YOLO11n_Training.ipynb` | preserved copy | exists | `3eb5fef6…c5da` |
| `provenance/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` | recovery report | exists | (this task's input) |
| `provenance/ENVIRONMENT.md` | from §2.3 | **must be written** | — |
| `provenance/train_args.yaml` | reconstructed from cell 31 stdout | **must be produced** (label "reconstructed; original `args.yaml` not preserved") | — |
| `provenance/EXPORT.md` | from §2.6–2.7 | **must be written** | — |
| `provenance/REPRODUCIBILITY.md` | from §5 | **must be written** | — |
| `deployment/best.pt` | main repo | exists | `1b47a433…def8` |
| `deployment/best.onnx` | main repo | exists | `e6ad18f9…aa77` |
| `deployment/model_config.json` | main repo | exists | `b48710e5…2a8c` |
| `deployment/metrics_summary.json` | main repo | exists | `57ba3ccb…d615` |
| `deployment/dataset_attribution.txt` | main repo | exists | `5290ac76…fe0d` |
| `evaluation/PER_CLASS_ONNX.md` | recovery §8.2 | **must be written** | — |
| `SHA256SUMS.json` | new | **must be generated over this repo only** | — |

"The bundle" (`SHA256SUMS.json` 734 B, `1e02a815…eae1`) from the main repo covers only
the six deployment files; the model repo needs a **new, repo-wide** manifest that also
hashes the notebook and provenance files.

### 6.4 Model-card content requirements

Minimum fields the model card must carry (all traceable to this document):

- `license: agpl-3.0`; `base_model: Ultralytics/YOLO11` (nano); `datasets:
  metadore/fly-surfer-yolo11n-dataset`; `pipeline_tag: object-detection`.
- **Provenance:** 50-epoch 14-class fine-tune, 2026-11-06, Ultralytics 8.4.202, Colab
  T4; base checkpoint v8.4.0 release (I11 caveat).
- **Data:** v15, group-held-out 1,188/1,128, 8,666 boxes, CC BY 4.0, dataset SHA.
- **Metrics:** **stage C only**, quoted with the `metrics_summary.json` body, explicitly
  labelled "post-training ONNX Runtime CPU re-validation on the group-held-out
  validation split (not an independent test set)". Optionally list stage B separately as
  "PyTorch `best.pt` validation" with its own numbers — never merged.
- **Limitations:** no test set; two classes unevaluable (I6); best epoch unknown (I12);
  possible prior-run overwrite (I13); 0.426 uncalibrated and unexplained (I14); base
  download unhashed (I11); no Colab attestation (I16); bit-exact reproduction not
  claimed (§5).
- **Ethics/rights:** screenshots of a commercial game; uploader's CC BY 4.0 does not
  settle underlying rights.

### 6.5 Corresponding Source package (per the licensing audit §6.2)

The model repo, to be AGPL-compliant, must carry or offer: the licence text and
notices; the training notebook/script (now available); the pinned environment; the base
checkpoint identity and checksum (local hash now; **official** hash still open); the
dataset by reference (already public CC BY 4.0); the export record; `model_config.json`,
metrics and class map; and `best.pt`. **After recovery, only the official base-checkpoint
checksum is missing from this list** — the others are now supplyable. That is exactly
why the licensing audit's §8 items 2–4 are no longer strictly "missing", while items 1
and 6 remain the real blockers (§7).

---

## 7. Licensing boundary

### 7.1 What notebook recovery does and does not do

| It **does** | It **does not** |
|---|---|
| Supply the training source and exact command (audit §6.3 "missing") | Change the licence of the weights |
| Supply the full hyperparameter record (optimiser, LR, batch, augmentation, freeze policy) | Establish that fine-tuned weights are or are not a "covered work" |
| Supply the export command and ONNX configuration | Define Corresponding Source for a trained network |
| Confirm the data is the already-public CC BY 4.0 export | Resolve the underlying game-imagery rights |
| Make the §6.2 source package nearly assemblable | Constitute a recorded licence decision (I5) |
| Remove the "no training source" objection | Satisfy Ultralytics' "entire project" position for the MIT repo |

**Explicit statement to carry forward:** the recovery report and this proposal are
**evidence**, not a licence grant and not legal advice. They must not be cited as
settling the licensing question.

### 7.2 The four remaining questions

1. **Ultralytics-trained weights — covered work or not?** The model is a fine-tune of an
   AGPL checkpoint, and the ONNX file *itself* embeds
   `license=AGPL-3.0 License (https://ultralytics.com/license)`. The conservative,
   defensible position (already adopted in `THIRD_PARTY_NOTICES.md`) is to treat the
   weights as AGPL-3.0. Whether that is legally required is unsettled; it is a question
   for counsel/Ultralytics, not for this document.
2. **Corresponding Source.** For a trained network the licence predates ML and the FSF
   has published no definitive interpretation. The defensible package is §6.5. The
   recovery closes most of it; the **official** base-checksum item and the choice of
   "accompanying source vs written offer vs network server" (AGPL §6) remain decisions.
3. **ONNX redistribution.** Conveying `best.onnx` alone is conveying object code and
   triggers §6; publishing ONNX without `best.pt` and the training materials is *worse*
   compliance, not better (audit §5.4). Publish both, with the source package, or
   neither.
4. **Integration with the MIT FLY-SURFER project.** The MIT repo has no Ultralytics
   import and no weights; its only contact is reading a SHA-verified ONNX file through
   ONNX Runtime behind a model-agnostic interface. That supports the **aggregate**
   reading (AGPL §5 last paragraph). The risk is that Ultralytics' public "entire
   project" gloss is broader than the licence text; resolving that needs a written
   position. Practical guardrails until then: keep the notebook and all AGPL material
   out of the MIT repo; do not describe the MIT repo as "including" or "powered by" the
   detector; attach a source offer to any hosted demo (§13).

### 7.3 Blockers no technical step can clear

| Blocker | Owner | Status |
|---|---|---|
| Recorded licence decision authorising the fine-tune (I5) | Owner | **Missing** |
| Written position: are fine-tuned weights covered; what is their Corresponding Source | Ultralytics or counsel | **Missing** |
| Underlying game-imagery rights (uploader's CC BY 4.0 may not bind the game's rights-holders) | Owner / counsel | **Unresolved** |

### 7.4 Effect on the existing licensing audit

The audit is **not modified** and its verdicts stand. Its evidence table (§6.3) should,
however, be read as superseded on three rows: training notebook/script, full
hyperparameters and export command are now **recovered** (not "missing"). Its three
executive verdicts are unchanged: MIT preservation is "compatible with conditions";
publishing the model today is "insufficient evidence"; and whether the MIT app is a
combined work "requires written clarification".

---

## 8. Release readiness verdict

### 8.1 Gate status

| Gate | Status | Basis |
|---|---|---|
| Canonical training record established | **PASS** | §2 |
| All 17 inconsistencies analysed with proposed resolutions | **PASS** | §3 |
| Additional contradictions located | **PASS** | §4.2 |
| Corrections **applied** to the repository | **NOT DONE** | proposal only; owner approval required |
| Public prose internally consistent | **FAIL** (until §4 applied) | I1–I3, I17, A1, A3, A9 |
| Metric attribution corrected | **FAIL** (until §4 applied) | I4, A5–A7 |
| Recorded licence decision | **FAIL** | I5 |
| Licensing clarifications obtained | **FAIL** | §7.3 |
| Corresponding Source assemblable | **PARTIAL** | notebook closes most; official base hash + decisions open |
| Bit-exact reproducibility | **NOT CLAIMED / FAIL** | §5 |
| Model repository assembled | **NOT STARTED** | §6 |

### 8.2 Decision

**Documentation: READY FOR OWNER APPROVAL.** The replacement wording in §3 and §4 is
complete and can be applied without touching any artifact. Applying it is a prerequisite
for any publication and also improves the existing repository on its own terms, because
the current public prose is factually wrong about the detector's origin.

**Model publication: NOT READY.** Do not build or publish the model repository yet. The
release is blocked by (1) the un-applied documentation corrections, (2) the absence of a
recorded licence decision, (3) the absence of a written position on weights /
Corresponding Source / "entire project", and (4) the unresolved game-imagery rights.
The status quo — MIT repository with weights local — remains the only arrangement free
of new obligations.

### 8.3 Ordered next actions

1. **Owner:** approve and apply §3/I1–I4, §3/I17 (via I1–I3) and §4.2 (A1, A3, A5–A7,
   A9). Verify no §4.3 statement is accidentally changed.
2. **Owner:** create the governance record for I5 (documents execution; not retroactive
   approval) and record the licence decision it references.
3. **Owner → Ultralytics/counsel:** obtain written answers to §7.2 questions 1 and 4, and
   the Corresponding-Source position (§7.2 question 2).
4. **Owner:** record an accepted upstream SHA-256 for the v8.4.0 `yolo11n.pt` (closes the
   last source-package gap, I11).
5. **If 1–4 clear:** assemble the model repository per §6 and publish under §5.2 of the
   licensing audit, with the full source package and a model card that quotes **stage C
   only** as the headline metric.
6. **If they do not clear:** adopt the audit's "no redistribution" position (§5.5) and
   state in the paper and repository that the weights are withheld for licensing
   reasons.

### 8.4 Non-promises (state these explicitly in any release)

- Not bit-exact reproducible (§5.2).
- Not independently tested — group-held-out validation only (§2.2).
- Two of fourteen classes unevaluable (§2.8, I6).
- The producing epoch of `best.pt` is unknown (I12).
- The base download is unhashed and unanchored to an official checksum (I11).
- The 0.426 threshold is uncalibrated and its derivation undocumented (I14).
- No cryptographic attestation of the Colab execution (I16).
- The notebook is evidence, not a licence grant or legal advice (§7.1).

---

## 9. Evidence inventory

**Read (read-only):** the eighteen files listed in §1.2, plus the preserved notebook and
the five deployment-bundle files (`best.onnx`, `best.pt`, `model_config.json`,
`metrics_summary.json`, `dataset_attribution.txt`, `SHA256SUMS.json`) whose hashes were
already recomputed in the recovery.

**Created:** `docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md`
(this document).

**Modified:** none. **Deleted:** none. **Git operations:** none. **Uploads:** none.
**Training/export/installs:** none.

**Date:** 2026-11-25
