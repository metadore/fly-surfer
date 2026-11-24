# YOLO11n Training Provenance Recovery

**Recovery date:** 2026-11-25
**Task type:** evidence recovery only — no training was run, no weights were modified,
no ONNX graph was regenerated, no dataset was altered, no licence was changed, and
nothing was uploaded, committed or pushed.
**Subject:** the deployed 14-class YOLO11n object detector recorded in
`models/YOLO11/deployment/yolo11n_v1_deployment/` and documented in
`FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md`.
**Companion document:** `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md`
(licensing analysis; **not** modified by this recovery).

---

## 0. Executive summary

**Verdict: the notebook is a genuine, internally consistent execution record of the
run that produced the deployed artifacts, and it is sufficient to document the model.
It is not sufficient, on its own, to guarantee a bit-exact retrain.**

What the recovered evidence establishes:

1. **The notebook is the record of the right run.** Its own SHA-256 dumps — taken at
   the end of the run — of `best.pt` (`1b47a433…`), `best.onnx` (`e6ad18f9…`) and
   `metrics_summary.json` (`57ba3ccb…`) are byte-identical to the three files now in
   the repository. Its recorded dataset archive SHA-256 (`c04058ad…39eff`) is
   byte-identical to the ZIP published as the audited HF dataset package. That is
   four byte-identical artifact identities (three run outputs plus the dataset
   archive); a fifth, the base checkpoint hash (`0ebbc80d…4ee1`), matches a
   repository copy, though the main run re-downloaded rather than loading that file
   (§4).
2. **The training configuration is fully recoverable.** The `train()` call, the
   resolved trainer arguments (printed by Ultralytics), the auto-selected optimiser
   and learning rate, the augmentation defaults, the seed, the epochs, the batch
   size, the image size and the patience are all present in cell stdout, not merely
   in prose.
3. **The environment is fully recoverable.** Python 3.13.16, PyTorch 2.11.0+cu130,
   torchvision 0.26.0+cu130, CUDA 13.0, Ultralytics 8.4.202, ONNX 1.23.2,
   ONNX Runtime 1.31.1, Tesla T4 (14.56 GB, 40 SMs), 12.67 GB system RAM.
4. **The export is fully recoverable.** The exact `model.export(...)` call, the ONNX
   opset, and the ONNX file's own embedded metadata (version, licence, description,
   export timestamp, export args) are recorded.

What the recovered evidence does **not** establish:

1. **Bit-exact retraining.** The run used `deterministic=False`; the optimiser was
   chosen automatically (`optimizer=auto`); the base checkpoint download was never
   hashed at download time; `results.csv`, `args.yaml` and all training plots were
   written to Google Drive and are not preserved locally or in the notebook file.
2. **Which epoch produced `best.pt`.** `results.csv` is not preserved, and the best
   validation mAP50-95 is tied at 0.689 on epochs 48 and 49.
3. **Governance.** `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` declared
   training **BLOCKED** pending a licensing decision and an approved export. The
   notebook shows the training was executed on 2026-11-06 with no approval record.
   This recovery records the fact and does not resolve it.
4. **A verifiable Colab origin.** The notebook carries no Colab file id and no
   notebook URL; `metadata.colab.provenance` is empty. There is no cryptographic
   binding between this `.ipynb` and the Colab execution it describes — only
   self-consistency plus independent artifact hashes.

Recommendation: treat the notebook as the primary training record, publish it (or a
copy) as part of the release evidence, and correct the repository's public prose that
claims the detector was not trained here (§12, I1–I3) before any model release. See
§14 for the sufficiency assessment.

---

## 1. The original notebook: location and file identity

### 1.1 Canonical location

| Item | Value |
|---|---|
| Path | `C:\Users\Hp\fruitfly\FLY-SURFER_YOLO11n_Training.ipynb` |
| Location relative to repositories | outside both Git worktrees (sibling of `FLY-SURFER`) — **not tracked** |
| Size | 971,997 bytes |
| SHA-256 | `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da` |
| File modified (local) | 2026-11-25 00:47:17 |
| Format | nbformat 4.0 (no cell ids) |
| Cells | 40 code cells, **0 markdown cells** |
| Kernel | `python3` / "Python 3" |
| Colab metadata | `provenance: []`, `gpuType: "T4"`, `accelerator: "GPU"`, `authorship_tag: "ABX9TyMyhrgsbW47vlxvY7iaSpxn"` |
| Colab URL / notebook id | **not present anywhere in the file or on this machine** |

The local file modification time (2026-11-25) is when the notebook was saved to disk
on this machine; it is **not** the training date. The training date is established
independently as **2026-11-06** by three records inside the run: the dataset export
timestamp `2026-11-06T15:23:36+00:00` (metadata of the exported dataset), the ONNX
export timestamp `2026-11-06T17:01:02.116695+00:00` (inside `best.onnx`), and the
smoke-test backup directory name `smoke_test_20261106`.

### 1.2 Preserved evidence copy

| Item | Value |
|---|---|
| Designated location | `C:\Users\Hp\fruitfly\EVIDENCE-RECOVERY\yolo11n-training\` |
| Preserved file | `FLY-SURFER_YOLO11n_Training.ipynb` |
| Size | 971,997 bytes (identical) |
| SHA-256 | `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da` (identical, verified before and after write-protection) |
| Modified time | preserved (2026-11-25 00:47:17) |
| Attributes | write-protected (read-only) |

The copy is byte-identical to the source. The original file was **not** modified,
moved or renamed — it is left exactly as received.

### 1.3 Execution structure (a caution for readers)

Cell indices below are **0-based**, in file order. Execution counts are not
contiguous and do not start at cell 0:

- Cells 8, 11–18 and 20–39 carry execution counts **1–29** in file order.
- Cells 0–7, 9–10 and 19 carry **no** `execution_count`, yet cells 0, 2, 3, 4, 5, 6,
  7, 9 and 10 hold saved outputs.
- Cells 33 and 34 hold a placeholder output: *"Output hidden; open in
  https://colab.research.google.com to view."* Their plot images are therefore lost.

Reading (labelled as inference, not fact): the most consistent explanation is that
cells 0–7 were executed in an earlier kernel session in which the Drive mount failed,
then the runtime was restarted; the recorded run then begins at cell 8 (execution 1)
with a fresh counter and a successful mount. Whatever the cause, **the saved outputs
are not the product of one uninterrupted top-to-bottom execution**, and the notebook
alone cannot prove execution order independently of the printed text.

---

## 2. Training environment (fully recorded)

Every value below is printed by the notebook itself.

### 2.1 Runtime

| Component | Value | Source |
|---|---|---|
| Python | 3.13.16 (main, Oct 1 2026, 15:40:24) [GCC 13.3.0] | cell 0, 7, 16 |
| Platform | `Linux-6.6.159+-x86_64-with-glibc2.39` | cell 0, 7 |
| PyTorch | 2.11.0+cu130 | cell 0, 7, 20 |
| torchvision | 0.26.0+cu130 | cell 7, 16, 20 |
| CUDA (torch build) | 13.0 | cell 7, 16, 20 |
| GPU | Tesla T4, 14.56 GB, 40 multiprocessors | cell 0, 7 |
| System RAM | 12.67 GB total, 11.08 GB available | cell 7 |
| Colab disk | 112.64 GB total, 112.54 GB free | cell 2, 7 |
| CPU (used for ONNX validation) | Intel Xeon CPU @ 2.00 GHz | cell 37 |
| Ultralytics before install | **NOT INSTALLED** | cell 7, 16 |

### 2.2 Installed for the run

| Package | Version | Note |
|---|---|---|
| ultralytics | 8.4.202 | `%pip install ultralytics==8.4.202` (cell 18); 8.4.203 was already available and deliberately not taken |
| ultralytics-platform | 0.1.104 | dependency |
| ultralytics-thop | 2.2.5 | dependency |
| onnx | 1.23.2 | installed inside the export cell (cell 35) because `find_spec("onnx")` was `None` |
| onnxruntime | 1.31.1 | auto-installed by Ultralytics during the PT/ONNX comparison (cell 36) |
| numpy | 2.4.6 | pre-installed |
| matplotlib | 3.10.0 | pre-installed |
| opencv-python | 5.0.0.93 | pre-installed |
| pillow | 11.3.0 | pre-installed |
| requests | 2.32.4 | pre-installed |
| psutil | 5.9.5 | pre-installed |
| polars | 1.35.2 | pre-installed |
| protobuf | 6.33.6 | pre-installed |
| ml_dtypes | 0.6.0 | pre-installed |

The dry-run in cell 17 (`pip install --dry-run ultralytics==8.4.202`) predicted
exactly these resolutions before the real install, which makes the environment
record internally checkable.

### 2.3 Environment versus the project's own specification

`reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:508` specified Python **3.10–3.12**
for broad wheel support. The run used **3.13.16**. The audit's specification was not
updated before or after the run; this is recorded, not corrected (I10).

---

## 3. Dataset provenance

### 3.1 Source

| Field | Value |
|---|---|
| Dataset | Subway Surfers Object Dataset |
| Version | 15 |
| Workspace / project | `horizon-cgt2k` / `subway-surfers-object-dataset` |
| URL | `https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset/dataset/15` |
| Licence | CC BY 4.0 (as declared by the dataset) |
| Source YAML path | `…\roboflow_v15_yolov8\subway surfers object dataset.v15-added.yolov8\data.yaml` |
| Source YAML SHA-256 | `f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423` |
| Source split manifest | `reports/PHASE_3B1_SPLIT_MANIFEST.json` |
| Source manifest SHA-256 | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` |

### 3.2 Portable export actually used

| Field | Value |
|---|---|
| Export phase | 3B.2B.1 |
| Created (UTC) | `2026-11-06T15:23:36+00:00` |
| Export script | `experiments/phase_3b/export_yolo11_dataset.py` |
| Archive on Drive | `/content/drive/MyDrive/FLY-SURFER/datasets/exports/phase_3b2b1_yolo11n.zip` |
| Archive size | 201.73 MiB (211,529,060 bytes) |
| Archive SHA-256 | `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff` |
| Integrity check | `zipfile.testzip()` → `None` (PASS), 4,638 members |
| Extracted to | `/content/FLY-SURFER/phase_3b2b1_yolo11n/` |

**Cross-reference:** this archive SHA-256 is identical to the `dataset.zip` published
in the audited HF dataset package `metadore/fly-surfer-yolo11n-dataset`
(`c04058ad…39eff`, 211,529,060 bytes). The data used for training is therefore
publicly retrievable and hash-verifiable.

### 3.3 Dataset configuration

The archive contains exactly one YAML, `phase_3b2b1_yolo11n/dataset.yaml`, with:

```yaml
path: '.'
train: train/images
val: valid/images
nc: 14
names: {0: boots-powerup, 1: boxtrain, 2: jump-barrier, 3: jump-electric,
        4: jump-hedge, 5: jump-roll-barrier, 6: jump-trash, 7: ledge,
        8: pogstick-powerup, 9: ramp, 10: roll-barrier, 11: train,
        12: undercover-barrier, 13: wall}
```

`path: '.'` is resolved against the current working directory by Ultralytics, which
caused the first training attempt to fail (I8). The notebook therefore wrote a
**second** YAML, `/content/FLY-SURFER/dataset_colab.yaml`, identical except that
`path` was set to the absolute root:

```yaml
path: /content/FLY-SURFER/phase_3b2b1_yolo11n
train: train/images
val: valid/images
nc: 14
names: { ...same 14 classes... }
```

All training, validation and export in the notebook uses **`dataset_colab.yaml`**.
This is why the ONNX file's embedded description names `dataset_colab.yaml` rather
than `dataset.yaml`.

### 3.4 Counts (verified twice, cells 14 and 15)

| Split | Images | Label files | Bounding boxes |
|---|---:|---:|---:|
| train | 1,188 | 1,188 | 4,704 |
| valid | 1,128 | 1,128 | 3,962 |
| **total** | **2,316** | **2,316** | **8,666** |

Images without boxes: 0.

### 3.5 Per-class distribution (from the export's own `dataset_summary.json`)

| ID | Class | train boxes | valid boxes |
|---:|---|---:|---:|
| 0 | boots-powerup | 24 | **0** |
| 1 | boxtrain | 625 | 749 |
| 2 | jump-barrier | 254 | 163 |
| 3 | jump-electric | 14 | **0** |
| 4 | jump-hedge | 18 | 26 |
| 5 | jump-roll-barrier | 407 | 356 |
| 6 | jump-trash | 34 | 62 |
| 7 | ledge | 87 | 48 |
| 8 | pogstick-powerup | 53 | 65 |
| 9 | ramp | 606 | 617 |
| 10 | roll-barrier | 147 | 162 |
| 11 | train | 1,617 | 1,174 |
| 12 | undercover-barrier | 196 | 19 |
| 13 | wall | 622 | 521 |

The split is group-held-out by recording, not random: `datasetfootage` (504 images)
and `subwayy1_1` (624 images) are validation; `subwayavitomp4` (501),
`subwayedited2` (392) and `subwayedtied` (295) are training. Twelve images were
quarantined during curation (9 `probable_gap`, 3 `isolated_plausible`).

The two zero-validation classes are the origin of the registry's limitation
statement and of an artefact visible in the validation printout (§7, I6).

---

## 4. Base checkpoint provenance

### 4.1 The local checkpoint that was inspected

Before training, the notebook searched Google Drive for a checkpoint (cells 21–25):

- The expected path `…/FLY-SURFER/models/YOLO11/yolo11n.pt` **did not exist**
  (`AssertionError: Checkpoint missing`, cell 21).
- A Drive-wide walk found exactly one match:
  `/content/drive/MyDrive/FLY-SURFER/training_results/YOLO11n/yolo11n.pt`.
- That file: 5.35 MB, SHA-256
  `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`,
  task `detect`, **80 COCO classes**, loaded successfully with Ultralytics 8.4.202.

This hash is identical to the current repository file `models/YOLO11/yolo11n.pt`
(5,613,764 bytes, `0ebbc80d…4ee1`).

### 4.2 The checkpoint the main training actually started from

The full training run (cell 31) did **not** point at that Drive file. It set

```python
WEIGHTS = "yolo11n.pt"   # official COCO-pretrained, auto-downloaded
```

and Ultralytics fetched it during the run:

```
Downloading https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt
to 'yolo11n.pt': 100% ━━━━━━━━━━━━ 5.4MB 64.2MB/s 0.1s
```

The notebook **never hashed that download**. Identity between the downloaded bytes and
`0ebbc80d…` is therefore strongly plausible (same versioned asset URL, same size class,
and the repository copy carries the 80-class COCO head) but is **not proven by the
notebook** (I11). The one-epoch smoke test (cell 29) did use the Drive copy via the
global `WEIGHTS`, so the two runs referenced different path objects.

### 4.3 Head re-initialisation

The printed trainer output records what happened to the pretrained head:

```
Overriding model.yaml nc=80 with nc=14
...
Remapped 1/14 cls head rows from pretrained weights by class name
Transferred 499/499 items from pretrained weights
Freezing layer 'model.23.dfl.conv.weight'
YOLO11n summary: 181 layers, 2,592,570 parameters, 2,592,554 gradients, 6.5 GFLOPs
```

So the classification head was re-sized from 80 to 14 classes, and only **one** of the
fourteen new class rows could be mapped from COCO by name (almost certainly `train`).
The detector is therefore a fine-tune of the COCO backbone/neck with a substantially
fresh class head — relevant to both the model's capability claims and to licence
analysis. The fused model at validation has 2,600,210 parameters (101 layers).

---

## 5. Complete recovered training configuration

### 5.1 The training call, verbatim (cell 31)

```python
DATA_YAML = "/content/FLY-SURFER/dataset_colab.yaml"
PROJECT   = "/content/drive/MyDrive/FLY-SURFER/training_results/YOLO11n"
RUN_NAME  = "yolo11n_14class_grouped_v1"
WEIGHTS   = "yolo11n.pt"

model = YOLO(WEIGHTS)
results = model.train(
    data=DATA_YAML,
    epochs=50,
    patience=15,
    imgsz=640,
    batch=16,
    workers=2,
    device=0,
    amp=True,
    cache="ram",
    optimizer="auto",
    seed=20261106,
    deterministic=False,
    val=True,
    plots=True,
    save=True,
    save_period=5,
    close_mosaic=10,
    project=PROJECT,
    name=RUN_NAME,
    exist_ok=True,
    verbose=True,
)
```

The cell also contains a resume branch (`if last.pt exists: model.train(resume=True)`).
The recorded run took the `else` branch — the output begins `Starting new YOLO11n
training...` and never prints `Found previous run, resuming`. The printed
`save_dir=…/yolo11n_14class_grouped_v1` and `exist_ok=True` mean a *previous* run of
the same name could have been overwritten without being resumed; the notebook cannot
prove this was the first run in that directory (I13).

### 5.2 Resolved trainer arguments

Printed verbatim by Ultralytics immediately before training (cell 31). Core fields:

| Argument | Resolved value |
|---|---|
| `mode` | `train` |
| `model` | `yolo11n.pt` |
| `data` | `/content/FLY-SURFER/dataset_colab.yaml` |
| `epochs` | `50` |
| `batch` | `16` |
| `nbs` (nominal batch) | `64` |
| `imgsz` | `640` |
| `workers` | `2` |
| `device` | `0` |
| `amp` | `True` |
| `cache` | `ram` |
| `optimizer` | `auto` (resolved to AdamW, §5.3) |
| `lr0` | `0.01` (present but **ignored** because `optimizer=auto`) |
| `lrf` | `0.01` |
| `momentum` | `0.937` (default; AdamW used `0.9`) |
| `weight_decay` | `0.0005` |
| `warmup_epochs` | `3.0` |
| `warmup_momentum` | `0.8` |
| `warmup_bias_lr` | `0.1` |
| `cos_lr` | `False` |
| `seed` | `20261106` |
| `deterministic` | `False` |
| `patience` | `15` |
| `fraction` | `1.0` |
| `close_mosaic` | `10` |
| `save_period` | `5` |
| `val` | `True` |
| `plots` | `True` |
| `pretrained` | `True` |
| `single_cls` | `False` |
| `rect` | `False` |
| `freeze` | `None` |
| `resume` | `False` |
| `project` | `…/FLY-SURFER/training_results/YOLO11n` |
| `name` | `yolo11n_14class_grouped_v1` |
| `exist_ok` | `True` |
| `save_dir` | `…/training_results/YOLO11n/yolo11n_14class_grouped_v1` |
| Loss gains | `box=7.5`, `cls=0.5`, `dfl=1.5` |
| NMS/val | `iou=0.7`, `max_det=300` |

### 5.3 Optimiser and learning rate — recorded only in stdout

```
optimizer: 'optimizer=auto' found, ignoring 'lr0=0.01' and determining best
           'optimizer' and 'lr0' automatically...
optimizer: AdamW(lr=0.000556, momentum=0.9) with parameter groups
           81 weight(decay=0.0), 88 weight(decay=0.0005), 87 bias(decay=0.0)
```

- Optimiser actually used: **AdamW**, initial LR **5.56 × 10⁻⁴**, momentum 0.9,
  weight decay 5 × 10⁻⁴ on decayed groups, 0.0 on weight/bias groups.
- The same `lr0=0.000556` was selected for the smoke test with `batch=4` and
  `fraction=0.05`, i.e. the auto rule in 8.4.202 produced the same value for both
  batch sizes. The LR is a **derived** value, not a chosen one.
- Neither the optimiser name nor the LR is written to any persisted artifact
  (`model_config.json` does not contain them; `args.yaml` is not preserved).

### 5.4 Augmentation settings (resolved defaults)

| Parameter | Value | Comment |
|---|---:|---|
| `mosaic` | 1.0 | enabled for epochs 1–40, disabled at `close_mosaic=10` |
| `close_mosaic` | 10 | "Closing dataloader mosaic" printed before epoch 41 |
| `fliplr` | 0.5 | |
| `flipud` | 0.0 | |
| `hsv_h` / `hsv_s` / `hsv_v` | 0.015 / 0.7 / 0.4 | |
| `degrees` | 0.0 | |
| `translate` | 0.1 | |
| `scale` | 0.5 | |
| `shear` | 0.0 | |
| `perspective` | 0.0 | |
| `mixup` | 0.0 | |
| `cutmix` | 0.0 | |
| `copy_paste` | 0.0 | |
| `erasing` | 0.4 | |
| `auto_augment` | `randaugment` | |
| `augment` | `False` | |

A separate Albumentations block was also active (printed before training and again
after mosaic closed):

```
Blur(p=0.01, blur_limit=(3, 7)), MedianBlur(p=0.01, blur_limit=(3, 7)),
ToGray(p=0.01, method='weighted_average', num_output_channels=3),
CLAHE(p=0.01, clip_limit=(1.0, 4.0), tile_grid_size=(8, 8))
```

These are Ultralytics 8.4.202 defaults; the notebook does not override them.

### 5.5 The one-epoch smoke test (separate, not the deployed model)

Cell 29 trained for **1 epoch** with `batch=4`, `fraction=0.05`, `val=False`,
`plots=False`, `project=/content/FLY-SURFER/training_smoke`,
`name=yolo11n_14class_smoke`, using the Drive checkpoint. It consumed only
**59 training images** and 15 iterations. Its validation (run automatically at the end
of training despite `val=False`) produced `all 0.0494 / 0.0449 / 0.0283 / 0.0188`
(P/R/mAP50/mAP50-95) — i.e. essentially untrained. Its outputs were copied to
`…/training_results/YOLO11n/smoke_test_20261106/` (args.yaml, results.csv,
weights/best.pt, weights/last.pt; best/last 5,356.21 KB each).

This smoke run is **not** the deployed model and must not be confused with it. It is
useful only as evidence that the full pipeline (dataset, AMP, optimiser, validation,
Drive write) worked before the 50-epoch run.

### 5.6 Other resolved defaults worth noting

`agnostic_nms=False`, `compile=False`, `dynamic=False`, `dropout=0.0`,
`multi_scale=0.0`, `rect=False`, `retina_masks=False`, `overlap_mask=True` (irrelevant
to detection), `simplify=True`, `opset=None` (exported separately in cell 35),
`format=torchscript` (unused), `save_json=False`, `save_txt=False`,
`save_conf=False`, `save_crop=False`, `profile=False`, `visualize=False`,
`verbose=True`. The printed argument list also contains parameters that are not part
of the YOLO11 detection recipe (`kobj`, `dgrad`, `dis`, `dlam`, `dlog`, `rle`, `pose`,
`tracker=tracktrack.yaml`); they are version defaults in 8.4.202 and were not set by
the notebook.

---

## 6. Training execution record

### 6.1 Run facts

| Item | Value |
|---|---|
| Run directory | `/content/drive/MyDrive/FLY-SURFER/training_results/YOLO11n/yolo11n_14class_grouped_v1` |
| Epochs completed | 50 / 50 |
| Wall time | `0.374 hours` (~22.4 min) |
| Iterations per epoch | 75 (= ⌈1188 / 16⌉) |
| Validation iterations | 36 (= ⌈1128 / 32⌉, validation batch = 2 × train batch) |
| GPU memory | 2.53 GB at epoch 1, 2.68 GB thereafter |
| AMP checks | passed |
| Label cache | built for train (1,188) and valid (1,128); "0 backgrounds, 0 corrupt" |
| Caching | train 0.8 GB RAM, valid 0.7 GB RAM |

### 6.2 Per-epoch validation history (the only surviving copy of `results.csv`)

Metrics are EMA validation on the 1,128-image validation split:
P = precision, R = recall, mAP50 and mAP50-95 as printed.

| Epoch | box_loss | cls_loss | dfl_loss | P | R | mAP50 | mAP50-95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.476 | 4.058 | 1.392 | 0.532 | 0.284 | 0.284 | 0.201 |
| 2 | 1.068 | 1.474 | 1.122 | 0.659 | 0.491 | 0.512 | 0.363 |
| 3 | 0.9854 | 1.099 | 1.073 | 0.850 | 0.557 | 0.616 | 0.441 |
| 4 | 0.9372 | 0.9573 | 1.048 | 0.877 | 0.586 | 0.678 | 0.497 |
| 5 | 0.9077 | 0.8873 | 1.035 | 0.868 | 0.644 | 0.715 | 0.526 |
| 6 | 0.8666 | 0.8266 | 1.020 | 0.841 | 0.665 | 0.735 | 0.538 |
| 7 | 0.8474 | 0.7920 | 1.013 | 0.878 | 0.678 | 0.766 | 0.572 |
| 8 | 0.8266 | 0.7466 | 1.002 | 0.836 | 0.743 | 0.800 | 0.583 |
| 9 | 0.8084 | 0.7196 | 0.9937 | 0.828 | 0.737 | 0.794 | 0.578 |
| 10 | 0.8017 | 0.6931 | 0.9909 | 0.875 | 0.747 | 0.830 | 0.598 |
| 11 | 0.7890 | 0.6920 | 0.9851 | 0.889 | 0.739 | 0.826 | 0.605 |
| 12 | 0.7803 | 0.6739 | 0.9774 | 0.881 | 0.740 | 0.820 | 0.602 |
| 13 | 0.7659 | 0.6493 | 0.9810 | 0.893 | 0.757 | 0.847 | 0.622 |
| 14 | 0.7453 | 0.6383 | 0.9710 | 0.853 | 0.778 | 0.840 | 0.618 |
| 15 | 0.7339 | 0.6246 | 0.9576 | 0.874 | 0.784 | 0.855 | 0.630 |
| 16 | 0.7351 | 0.6253 | 0.9634 | 0.892 | 0.788 | 0.854 | 0.621 |
| 17 | 0.7361 | 0.6127 | 0.9643 | 0.887 | 0.752 | 0.854 | 0.628 |
| 18 | 0.7164 | 0.5967 | 0.9527 | 0.863 | 0.802 | 0.861 | 0.638 |
| 19 | 0.7030 | 0.5798 | 0.9510 | 0.920 | 0.736 | 0.845 | 0.627 |
| 20 | 0.7160 | 0.5913 | 0.9569 | 0.858 | 0.777 | 0.860 | 0.636 |
| 21 | 0.6947 | 0.5742 | 0.9505 | 0.855 | 0.830 | 0.875 | 0.644 |
| 22 | 0.6927 | 0.5675 | 0.9455 | 0.909 | 0.792 | 0.866 | 0.649 |
| 23 | 0.6892 | 0.5633 | 0.9420 | 0.866 | 0.836 | 0.880 | 0.661 |
| 24 | 0.6791 | 0.5561 | 0.9449 | 0.882 | 0.818 | 0.879 | 0.651 |
| 25 | 0.6669 | 0.5454 | 0.9328 | 0.860 | 0.791 | 0.866 | 0.651 |
| 26 | 0.6707 | 0.5500 | 0.9323 | 0.881 | 0.813 | 0.874 | 0.660 |
| 27 | 0.6721 | 0.5398 | 0.9349 | 0.882 | 0.790 | 0.872 | 0.652 |
| 28 | 0.6638 | 0.5333 | 0.9287 | 0.881 | 0.806 | 0.883 | 0.663 |
| 29 | 0.6428 | 0.5177 | 0.9243 | 0.875 | 0.825 | 0.877 | 0.660 |
| 30 | 0.6448 | 0.5065 | 0.9298 | 0.922 | 0.794 | 0.887 | 0.667 |
| 31 | 0.6527 | 0.5113 | 0.9292 | 0.898 | 0.828 | 0.888 | 0.663 |
| 32 | 0.6529 | 0.5209 | 0.9306 | 0.899 | 0.821 | 0.888 | 0.670 |
| 33 | 0.6338 | 0.5004 | 0.9180 | 0.880 | 0.813 | 0.883 | 0.667 |
| 34 | 0.6363 | 0.4955 | 0.9203 | 0.896 | 0.826 | 0.882 | 0.668 |
| 35 | 0.6181 | 0.4766 | 0.9153 | 0.874 | 0.819 | 0.891 | 0.673 |
| 36 | 0.6222 | 0.4813 | 0.9212 | 0.925 | 0.820 | 0.892 | 0.674 |
| 37 | 0.6118 | 0.4711 | 0.9117 | 0.908 | 0.818 | 0.890 | 0.678 |
| 38 | 0.6125 | 0.4704 | 0.9122 | 0.896 | 0.842 | 0.891 | 0.678 |
| 39 | 0.5975 | 0.4599 | 0.9076 | 0.932 | 0.801 | 0.890 | 0.681 |
| 40 | 0.6053 | 0.4691 | 0.9116 | 0.887 | 0.829 | 0.888 | 0.684 |
| 41 | 0.5966 | 0.4364 | 0.8896 | 0.908 | 0.829 | 0.892 | 0.672 |
| 42 | 0.5775 | 0.4085 | 0.8866 | 0.902 | 0.822 | 0.886 | 0.674 |
| 43 | 0.5652 | 0.4004 | 0.8784 | 0.902 | 0.832 | 0.891 | 0.682 |
| 44 | 0.5598 | 0.3911 | 0.8727 | 0.901 | 0.833 | 0.898 | 0.684 |
| 45 | 0.5524 | 0.3893 | 0.8749 | 0.924 | 0.826 | 0.892 | 0.682 |
| 46 | 0.5415 | 0.3798 | 0.8705 | 0.915 | 0.841 | 0.898 | 0.686 |
| 47 | 0.5383 | 0.3785 | 0.8691 | 0.915 | 0.829 | 0.892 | 0.683 |
| 48 | 0.5328 | 0.3730 | 0.8677 | 0.930 | 0.825 | 0.899 | **0.689** |
| 49 | 0.5319 | 0.3665 | 0.8654 | 0.908 | 0.830 | 0.893 | **0.689** |
| 50 | 0.5292 | 0.3625 | 0.8634 | 0.917 | 0.827 | 0.895 | 0.687 |

Patience was 15, but mAP50-95 kept improving late, so no early stop occurred; all 50
epochs ran.

**Which epoch is in `best.pt`?** Not determinable from the evidence. The maximum
validation mAP50-95 (0.689) occurs at both epoch 48 and epoch 49. Ultralytics selects
`best.pt` by a weighted fitness of mAP50 and mAP50-95, which could also select epoch
46 (mAP50 0.898, mAP50-95 0.686) or 44 (0.898/0.684). Without `results.csv` or the
`best.pt` checkpoint metadata, the epoch is unresolved (I12).

### 6.3 Artifacts written to Drive (cell 32 audit)

```
BoxF1_curve.png, BoxPR_curve.png, BoxP_curve.png, BoxR_curve.png,
args.yaml, confusion_matrix.png, confusion_matrix_normalized.png, labels.jpg,
results.csv, results.png,
train_batch0/1/2.jpg, train_batch3000/3001/3002.jpg,
val_batch0/1/2_labels.jpg, val_batch0/1/2_pred.jpg,
weights/best.pt (5,362.34 KB), weights/last.pt (5,362.34 KB),
weights/epoch0.pt … epoch45.pt (≈25,976–25,982 KB each; every 5 epochs)
```

`best.pt` and `last.pt` are small (5.36 MB) because the optimiser state was stripped
after training; the `epoch*.pt` files retain it. **None of these files is preserved on
this machine.** Only `best.pt`, `best.onnx`, `metrics_summary.json`,
`model_config.json`, `dataset_attribution.txt` and `SHA256SUMS.json` were carried into
the repository deployment bundle; `args.yaml`, `results.csv` and all plots exist only
on the (unverified) Google Drive.

---

## 7. Export procedure and ONNX configuration

### 7.1 Export call, verbatim (cell 35)

```python
model = YOLO(str(BEST))           # BEST = .../yolo11n_14class_grouped_v1/weights/best.pt
print("Classes:", model.names)    # asserted len == 14
onnx_path = model.export(
    format="onnx",
    imgsz=640,
    opset=17,
    simplify=False,
    dynamic=False,
    half=False,
    device=0,
)
```

`onnx` was installed first (`onnx==1.23.2`) because `find_spec("onnx")` was `None`.
A deprecation warning was emitted: `'half' is deprecated and will be removed in the
future. Use 'quantize' instead.` — the argument was still honoured as `half=False`.

Export log:

```
PyTorch: starting from '…/weights/best.pt' with input shape (1, 3, 640, 640) BCHW
         and output shape(s) (1, 18, 8400) (5.2 MB)
ONNX: starting export with onnx 1.23.2 opset 17...
ONNX: export success ✅ 1.1s, saved as '…/weights/best.onnx' (10.1 MB)
Export complete (1.8s)
```

### 7.2 ONNX embedded metadata (read directly from the file during this recovery)

| Key | Value |
|---|---|
| `description` | `Ultralytics YOLO11n model trained on /content/FLY-SURFER/dataset_colab.yaml` |
| `author` | `Ultralytics` |
| `version` | `8.4.202` |
| `license` | `AGPL-3.0 License (https://ultralytics.com/license)` |
| `docs` | `https://docs.ultralytics.com` |
| `date` | `2026-11-06T17:01:02.116695+00:00` |
| `args` | `{'data': None, 'batch': 1, 'fraction': 1.0, 'quantize': None, 'nms': None, 'dynamic': False, 'simplify': False, 'opset': 17}` |
| `task` / `head` | `detect` / `Detect` |
| `imgsz` / `stride` | `[640, 640]` / `32` |
| `batch` / `end2end` | `1` / `False` |
| `names` | the 14-class map, IDs 0–13 in schema order |

Two readings to avoid:

- The `args` dictionary in the ONNX metadata describes **export-time** arguments, not
  training arguments. `batch: 1` here is the exported graph's fixed batch, not the
  training batch of 16. `fraction: 1.0` is the export default.
- The description names `dataset_colab.yaml`, which is the notebook's corrected YAML
  (§3.3), not the archive's own `dataset.yaml`.

The `task`, `stride`, `head` and `end2end` values were also verified independently in
`reports/PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md` §4 (read-only ONNX Runtime
inspection).

### 7.3 PyTorch vs ONNX agreement check (cell 36)

On the first validation image with `conf=0.25`, `iou=0.7`:

- 3 PyTorch detections, 3 ONNX detections, 3 matched at IoU ≥ 0.5;
- mean matched IoU **0.9798**; mean confidence difference **0.00241**.

This is a smoke equivalence check on one image, not an accuracy measurement.

---

## 8. Validation results — three different numbers

The run produced **three distinct evaluations** of the fine-tuned model. They are
sometimes conflated in the repository; the table keeps them separate.

| # | Evaluation | Backend / batch | Images | P | R | mAP50 | mAP50-95 |
|---|---|---|---:|---:|---:|---:|---:|
| A | Last in-training validation (epoch 50) | PyTorch, batch 32 | 1,128 | 0.917 | 0.827 | 0.895 | 0.687 |
| B | Post-training `best.pt` validation (cell 31, `plots=True`) | PyTorch, batch 16 | 1,128 | 0.927 | 0.827 | 0.899 | 0.688 |
| C | **ONNX full validation** (cell 37, `batch=8` → forced 1) | ONNX Runtime 1.31.1 CPU | 1,128 | **0.9373102206978658** | **0.8108289132772389** | **0.8977760737241655** | **0.6877264204606104** |

Evaluation **C** is the one written to `onnx_validation/metrics_summary.json` and
carried into `MODEL_REGISTRY.md` §1.6 and the paper. Its JSON body is:

```json
{
  "backend": "ONNX Runtime CPU",
  "images": 1128,
  "classes": 14,
  "mAP50": 0.8977760737241655,
  "mAP50_95": 0.6877264204606104,
  "precision": 0.9373102206978658,
  "recall": 0.8108289132772389
}
```

Note that `MODEL_REGISTRY.md` §1.6 says these are "Reported by the training run and
copied into `metrics_summary.json`". That sentence is imprecise: the values are the
**ONNX CPU re-validation**, not the training run's own validation (A or B). The
difference is small but real — precision 0.9373 (C) versus 0.927 (B) — and is not
explainable as rounding.

### 8.1 Per-class validation — `best.pt` (evaluation B, cell 31)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| boxtrain | 538 | 749 | 0.911 | 0.810 | 0.843 | 0.700 |
| jump-barrier | 148 | 163 | 0.842 | 0.853 | 0.861 | 0.639 |
| jump-hedge | 21 | 26 | 1.000 | 0.632 | 0.885 | 0.599 |
| jump-roll-barrier | 287 | 356 | 0.920 | 0.911 | 0.959 | 0.809 |
| jump-trash | 44 | 62 | 0.977 | 0.581 | 0.787 | 0.490 |
| ledge | 32 | 48 | 0.923 | 0.896 | 0.919 | 0.699 |
| pogstick-powerup | 65 | 65 | 0.934 | 0.648 | 0.840 | 0.378 |
| ramp | 501 | 617 | 0.941 | 0.935 | 0.964 | 0.836 |
| roll-barrier | 149 | 162 | 0.950 | 0.938 | 0.959 | 0.817 |
| train | 839 | 1,174 | 0.872 | 0.901 | 0.914 | 0.757 |
| undercover-barrier | 15 | 19 | 0.977 | 0.895 | 0.895 | 0.741 |
| wall | 247 | 521 | 0.882 | 0.922 | 0.957 | 0.795 |

### 8.2 Per-class validation — ONNX (evaluation C, cell 37)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| boxtrain | 538 | 749 | 0.919 | 0.804 | 0.843 | 0.704 |
| jump-barrier | 148 | 163 | 0.870 | 0.840 | 0.866 | 0.643 |
| jump-hedge | 21 | 26 | 1.000 | 0.588 | 0.872 | 0.605 |
| jump-roll-barrier | 287 | 356 | 0.910 | 0.909 | 0.960 | 0.809 |
| jump-trash | 44 | 62 | 0.971 | 0.549 | 0.822 | 0.505 |
| ledge | 32 | 48 | 0.957 | 0.875 | 0.918 | 0.690 |
| pogstick-powerup | 65 | 65 | 0.926 | 0.577 | 0.797 | 0.356 |
| ramp | 501 | 617 | 0.951 | 0.932 | 0.972 | 0.839 |
| roll-barrier | 149 | 162 | 0.967 | 0.938 | 0.956 | 0.816 |
| train | 839 | 1,174 | 0.892 | 0.901 | 0.913 | 0.755 |
| undercover-barrier | 15 | 19 | 0.982 | 0.895 | 0.902 | 0.741 |
| wall | 247 | 521 | 0.903 | 0.921 | 0.952 | 0.788 |

Only 12 classes appear in either table. `boots-powerup` (ID 0) and `jump-electric`
(ID 3) have zero validation instances and cannot be evaluated on this split — the
limitation already recorded in `MODEL_REGISTRY.md` §1.7.

---

## 9. Deployment packaging (cell 39)

`model_config.json`, `metrics_summary.json` and `best.pt`/`best.onnx` were assembled on
Drive into `…/FLY-SURFER/deployment/yolo11n_v1/`, with `dataset_attribution.txt`
copied from the dataset export's `provenance/attribution.txt`, a generated
`SHA256SUMS.json`, and a ZIP `deployment/yolo11n_v1_deployment.zip` (13.56 MB,
integrity PASS). The bundle is the direct ancestor of the repository's
`models/YOLO11/deployment/yolo11n_v1_deployment/` directory.

`model_config.json` was **constructed in this cell**, not derived from a training
artifact. It therefore records exactly what the notebook author chose to write:

- `confidence_threshold_initial: 0.426` and `iou_threshold_initial: 0.7` are **hard-coded
  literals**. No cell computes, searches or justifies 0.426; its derivation is not
  recoverable (I14). `configs/detector_config.yaml` repeats it and correctly labels it
  "not calibrated".
- `dataset.version: 15`, `training_images: 1188`, `validation_images: 1128`,
  `independent_test_set: false`.
- `training: {epochs: 50, image_size: 640, seed: 20261106, ultralytics_version: "8.4.202"}`.

Consequently `model_config.json` **omits** batch size, optimiser, learning rate,
weight decay, warm-up, augmentation, patience, AMP, cache mode, worker count,
deterministic flag, hardware and the base-checkpoint identity. All of those are
recoverable from the notebook but not from the deployment bundle.

The deployment ZIP (13.56 MB, weights + config + metrics + attribution) is a different
archive from the dataset ZIP (201.73 MB) published on Hugging Face; they must not be
confused.

---

## 10. Cross-check against repository records

### 10.1 Byte-level agreement (strongest evidence)

| Artifact | Notebook record (cell 38/24) | Repository record | Status |
|---|---|---|---|
| `best.pt` | printed 5.237 MB; SHA `1b47a43325b18c59b52b9a29cdd45c029d079ee134a7283b49cd0e86366bdef8` | 5,491,034 B; `1b47a433…def8` | **IDENTICAL** |
| `best.onnx` | 10.144 MB; SHA `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | 10,636,871 B; `e6ad18f9…aa77` | **IDENTICAL** |
| `metrics_summary.json` | 0.0 MB (<1 KB); SHA `57ba3ccb3fe7ffb882109775c3f76c092078f46bf7c9f82065f8b96bb18cd615` | 216 B; `57ba3ccb…d615` | **IDENTICAL** |
| `model_config.json` | not hashed in notebook | 1,249 B; `b48710e5…2a8c` | consistent (built in cell 39, later committed) |
| `dataset_attribution.txt` | copied from dataset export | 1,529 B; `5290ac76…fe0d` | consistent |
| `yolo11n.pt` | 5.35 MB; SHA `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | 5,613,764 B; `0ebbc80d…4ee1` | **IDENTICAL** (repo copy) |
| Dataset ZIP | 201.73 MB; SHA `c04058ad…39eff` | HF `dataset.zip`: 211,529,060 B; `c04058ad…39eff` | **IDENTICAL** |

The three artifact hashes were recomputed during this recovery directly from the
repository files and matched the values printed by the notebook. This is the core
chain of evidence: the notebook's own end-of-run audit and the deployed bytes agree.

### 10.2 Value-level agreement and disagreement

| Item | Notebook | Repository record | Assessment |
|---|---|---|---|
| 14 classes, schema order | yes | `model_config.json`, `MODEL_REGISTRY.md` §1.5, `configs/detector_config.yaml` | agree |
| 1,188 / 1,128 images | yes | `model_config.json`, §1.2, export report | agree |
| 8,666 boxes | yes (4,704 + 3,962) | §1.2 | agree |
| 50 epochs, imgsz 640, seed 20261106, Ultralytics 8.4.202 | yes | `model_config.json`, §1.3 | agree |
| Base checkpoint `yolo11n.pt` SHA `0ebbc80d…` | local Drive copy only | §1.8 | agree as a file; **download identity unproven** |
| ONNX opset 17, no simplify, no dynamic, fp32 | yes | ONNX metadata; §1.4 | agree |
| Input [1,3,640,640] NCHW RGB, output [1,18,8400] | yes (export log + contract) | §1.4, `detector_config.yaml` | agree |
| mAP50 0.8978 / mAP50-95 0.6877 / P 0.9373 / R 0.8108 | evaluation C | §1.6, `metrics_summary.json` | agree numerically; **attribution to "the training run" is wrong** (I4) |
| "Model licence AGPL-3.0" | ONNX metadata `license` field only | §1.1 | agree |
| Dataset "not used to train" | **contradicted** — used for 50 epochs | `README.md:194` | **contradiction** (I1) |
| "was not retrained or fine-tuned" | **contradicted** | `README.md:239–240` | **contradiction** (I2) |
| "detector was not trained … here" | **contradicted** | `README.md:494` | **contradiction** (I3) |
| Training must be BLOCKED | training executed | `PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:742` | **governance gap** (I5) |

`reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:4` already calls the artifact
"trained 14-class", and the Phase 3B2B2 audit already quotes "Colab's inference-only
135.4 ms" — both consistent with the notebook. The contradiction is confined to the
README prose and the registry's metric attribution.

---

## 11. Recorded versus unavailable information

Status legend: **R** recorded in the notebook; **P** partially recorded; **U**
unavailable.

| # | Requested item | Value found | Status |
|---:|---|---|---|
| 1 | Base checkpoint / source | `yolo11n.pt` from `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt`; local copy SHA `0ebbc80d…`, 80 COCO classes | **P** (URL + local hash; downloaded bytes never hashed) |
| 2 | Dataset source / version | Subway Surfers Object Dataset v15, `horizon-cgt2k`, CC BY 4.0, source YAML SHA `f6e51bf6…` | **R** |
| 3 | Dataset configuration | 14 classes, `train/images`, `valid/images`; archive YAML + runtime `dataset_colab.yaml` contents printed | **P** (the `dataset_colab.yaml` file itself is not preserved, but is reconstructible from the printed content) |
| 4 | Training command and actual arguments | `model.train(...)` quoted; full resolved arg list printed | **R** |
| 5 | Epochs, batch size, image size | 50, 16, 640 | **R** |
| 6 | Learning rate and optimiser | `optimizer=auto` → **AdamW, lr 5.56e-4, momentum 0.9, wd 5e-4**, `lrf=0.01`, warm-up 3 epochs | **P** (stdout only; not in any artifact file) |
| 7 | Augmentation settings | full resolved defaults incl. mosaic 1.0, close_mosaic 10, fliplr 0.5, hsv, rand augment, erasing 0.4, Albumentations block | **R** |
| 8 | Random seed | `seed=20261106`, `deterministic=False` | **R** |
| 9 | Python / PyTorch / CUDA / Ultralytics versions | 3.13.16 / 2.11.0+cu130 / 13.0 / 8.4.202 (plus torchvision, ONNX, ORT) | **R** |
| 10 | Hardware | Tesla T4 14.56 GB, 40 SMs; 12.67 GB RAM; 112.64 GB disk; Xeon 2.00 GHz CPU for ONNX | **R** |
| 11 | Training outputs and validation metrics | 50-epoch metric history (transcribed in §6.2); three evaluations; per-class tables; artifact listing | **P** (metrics yes; `results.csv`, `args.yaml`, plots and 10 `epoch*.pt` files not preserved; cells 33–34 outputs hidden) |
| 12 | Export command and ONNX configuration | `model.export(format="onnx", imgsz=640, opset=17, simplify=False, dynamic=False, half=False, device=0)`; metadata in §7.2 | **R** |

Additional unavailable items:

| Item | Status |
|---|---|
| Colab notebook URL / file id / account | **U** — absent from the file, the machine and the session history |
| Execution timestamps per cell | **U** |
| `results.csv` (full 50×~12 columns) | **U** — content partially recoverable from stdout |
| `args.yaml` (the run's own resolved-args file) | **U** — content reconstructible from the trainer log, but the original file is not available |
| `confusion_matrix*.png`, `Box*_curve.png`, `results.png`, `val_batch*` images | **U** — cells 33/34 outputs were never embedded |
| `epoch0.pt … epoch45.pt` | **U** |
| Which epoch produced `best.pt` | **U** |
| Derivation of confidence 0.426 | **U** |
| Operator identity, authorisation to train, licence approval | **U** |
| Whether the run directory already contained an earlier run | **U** (`exist_ok=True`, no resume log line) |

---

## 12. Inconsistencies and unresolved items

These are recorded as found. **Nothing has been corrected** in any existing file.

**I1 — README claims the dataset was not used for training.**
`README.md:194`: *"The dataset was **not** used to train, fine-tune or tune any project
model."* The notebook shows 50 epochs of training on 1,188 images from that dataset.
This is a direct factual contradiction.

**I2 — README claims the detector was not fine-tuned.**
`README.md:239–240`: *"The detector is used as a fixed, externally trained component
and was not retrained or fine-tuned."* The notebook shows a COCO→14-class fine-tune
with `pretrained=True` and a re-initialised head.

**I3 — README limitations repeat the claim.**
`README.md:494`: *"The detector was not trained or calibrated here; its reported
metrics are provenance from its training environment."* The second clause is accurate;
the first is contradicted.

**I4 — Model registry misattributes the metrics.**
`MODEL_REGISTRY.md` §1.6: *"Reported by the training run and copied into
`metrics_summary.json`"*. The published numbers are from a **separate ONNX CPU
validation** (evaluation C), not from the training run's validation (A/B). The backend
sentence in the same section is correct; the provenance sentence is not.

**I5 — Training was executed while the readiness audit said BLOCKED.**
`reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:548–550, 742`: no accepted licence
decision (BLOCKED), no verified official checkpoint checksum (BLOCKED), no resolved
game screenshot/IP position (BLOCKED), and *"Final decision: BLOCKED — not ready to
train."* The notebook contains no approval record; the run happened on 2026-11-06.

**I6 — Zero-instance classes receive a non-zero per-class figure.**
In cell 31's printed per-class list, `boots-powerup` and `jump-electric` — which have
zero validation boxes — are printed with mAP50-95 **0.688**, exactly the overall
mAP50-95. The validation table itself omits both classes. This is an artefact of how
the printed loop indexes `metrics.box.maps` (the two absent classes carry the overall
value rather than a per-class measurement). Anyone reading the printed list could
mistake 0.688 for a measured per-class score. The registry's §1.7 statement ("zero
validation boxes … unevaluable") is the correct reading.

**I7 — The first training attempt failed on dataset paths.**
Cell 27 (`RuntimeError: … images not found, missing path '/content/valid/images'`)
because the archive YAML has `path: '.'`. Cell 28 created `dataset_colab.yaml` and
cell 29 succeeded. The failed attempt is preserved in the notebook, which is good
evidence hygiene, but it means the archive's own YAML cannot be used as-is from
`/content/FLY-SURFER/phase_3b2b1_yolo11n/`.

**I8 — Drive state is inconsistent across the early cells.**
Cell 3 fails with `MessageError: credential propagation was unsuccessful`; cell 4
reports Drive connected `False`; cell 5 nonetheless reports folders created; cell 6
reports all `True`; cell 7 reports `os.path.ismount("/content/drive")` **False** while
the project folder is `True`; cell 8 then mounts successfully and cell 9 lists
`['datasets', 'training_results']`. The most consistent reading is that cells 0–7 ran
in a pre-restart session in which `makedirs` created a local directory at the mount
path; that reading is an inference, not a recorded fact.

**I9 — Execution counts are not a clean sequence.** See §1.3. The outputs are not the
product of a single top-to-bottom run.

**I10 — Environment exceeds the project's own specification.**
The readiness audit specified Python 3.10–3.12; the run used 3.13.16. The audit also
anticipated `epochs=100` as a "starting invocation" and `data="dataset.yaml"`; the
executed run used 50 epochs and `dataset_colab.yaml`. The dataset-export report
(`PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md:437`) prescribes a third variant
(`data="/content/datasets/phase_3b2b1_yolo11n/dataset.yaml"`, `project="/content/runs"`).
Three different command variants exist across the repository and the notebook; the
notebook is the only one that actually ran.

**I11 — Base checkpoint identity is inferred, not proven.**
The main run downloaded `yolo11n.pt` and never hashed it. The local Drive copy
(`0ebbc80d…`) is the same file as the repository copy, but the notebook does not prove
that the downloaded bytes were that file. The readiness audit also states that no
official checksum for `yolo11n.pt` was available offline, so the local hash is not
anchored to an upstream authority.

**I12 — `best.pt`'s epoch is unknown.** §6.2. Without `results.csv`, the selected
epoch cannot be fixed.

**I13 — The run may not have been the first in its directory.** `exist_ok=True` plus a
missing resume branch means a previous `yolo11n_14class_grouped_v1` run could have
been overwritten. The notebook cannot exclude this.

**I14 — The 0.426 confidence threshold has no recorded derivation.** It is a literal in
cell 39. It is repeated in `model_config.json` and `configs/detector_config.yaml` but
is never computed, searched or justified in the notebook.

**I15 — Notebook acquisition date versus run date.** The file's local mtime is
2026-11-25 00:47; the run is dated 2026-11-06. The earlier date is the true run date.
Anyone citing the file's mtime as the training date would be wrong.

**I16 — No Colab-side attestation.** There is no URL, file id, account record or cell
timing. The chain from "this `.ipynb`" to "the Colab execution" rests on internal
consistency and on the artifact hashes in §10.1.

**I17 — Phase 3B2B3 recorded a "trained 14-class" artifact but the README did not.**
The integration report (`:4`) and the AGPL audit already describe a locally trained
model, while `README.md` and `THIRD_PARTY_NOTICES.md` describe an external one. The
public documentation set is internally inconsistent about the detector's origin.

---

## 13. What the notebook does *not* record about intent

The notebook is an execution artifact, not a laboratory record. It contains:

- no hypothesis, pre-registration or success criterion;
- no rationale for choosing 50 epochs, batch 16, patience 15 or `close_mosaic=10`
  (these are Ultralytics defaults or round numbers);
- no record of a licence decision or of authorisation to fine-tune an AGPL-3.0 model;
- no record of who ran it or on whose Colab account;
- no record of why `models/YOLO11/yolo11n.pt` was missing from Drive (cell 21) while
  the copy existed under `training_results/YOLO11n/`.

These omissions matter for a release narrative but do not affect the technical
sufficiency assessment below.

---

## 14. Sufficiency assessment for a reproducible model release

### 14.1 Sufficient for a **documented** model release

The following can be stated with evidence and verified by a third party:

1. **Artifact identity** — the exact deployed bytes and their SHA-256 values.
2. **Environment** — every framework and runtime version needed to load, export and
   evaluate the model, including the exact Ultralytics version that produced the ONNX
   metadata.
3. **Data identity** — the exact dataset archive by SHA-256, publicly retrievable from
   the audited HF dataset package, with source attribution and split structure.
4. **Training recipe** — the exact `train()` call and the full resolved hyperparameter
   set, including the auto-selected AdamW learning rate and all augmentation defaults.
5. **Export recipe** — the exact `model.export(...)` call and the ONNX metadata.
6. **Evaluation provenance** — three validation runs, their settings, and the exact
   numbers that were published, with per-class detail and the two unevaluable classes.

That is enough to publish the detector with an honest model card: what it is, what it
was trained on, how, in what environment, with what measured validation performance
and with what limits (group-held-out validation only, no test set, two classes
unevaluable, AGPL-3.0 obligations).

### 14.2 Insufficient for **bit-exact retraining**

Even with the notebook, an independent retrain cannot be guaranteed to reproduce
`best.pt` byte-for-byte, because:

1. `deterministic=False` was set explicitly, and no deterministic-algorithm or
   deterministic-cuBLAS setting is recorded.
2. The optimiser and LR were chosen automatically by Ultralytics 8.4.202 internals;
   the rule depends on package internals and on dataset/model size.
3. The base checkpoint's downloaded bytes were never hashed.
4. `results.csv`, `args.yaml` and the checkpoints other than `best.pt`/`last.pt` were
   not preserved, so the exact epoch history and the selected epoch are unverifiable.
5. The Colab image (Python 3.13.16 built 2026-10-01, CUDA 13.0, cuDNN 9.19, Triton
   3.6.0) is a moving target; no container digest is recorded.
6. GPU-level non-determinism (atomic reductions, cuDNN autotuning) is not controlled.

A third party could reproduce the **procedure** and expect metrics in the same range,
but should not be promised bit-identical weights.

### 14.3 Release blockers independent of technical sufficiency

1. The public documentation contradicts the notebook (I1–I3, I17). A release that
   repeats "not trained here" while publishing a trained model is not truthful.
2. The licensing position was never recorded as approved (I5); the AGPL obligations of
   distributing or network-serving these weights need an explicit decision, which is
   the subject of the companion audit.
3. The metric attribution in the registry should distinguish the ONNX re-validation
   from the training-run validation (I4).

### 14.4 What would close the remaining gaps (not performed here)

- Retrieve from Google Drive and preserve: `args.yaml`, `results.csv`, the run's
  `best.pt` metadata (epoch), and the plot images.
- Record the SHA-256 of the `yolo11n.pt` actually downloaded during the run (if the
  Drive copy of the run's working directory still exists).
- Re-evaluate `best.onnx` once in a pinned environment and archive the raw
  `metrics_summary.json` plus per-class outputs.
- Obtain and record the Colab notebook URL or file id for attestation.
- Add a licence/approval record covering the fine-tune.

None of these require retraining, and none was done in this recovery.

### 14.5 One-line verdict

**The recovered evidence is sufficient to publish the model with a fully documented
provenance chain and to reproduce the training procedure, but it is not sufficient to
guarantee bit-exact reproduction of `best.pt`; the release must also resolve the
documentation contradictions and the unrecorded licence approval before publication.**

---

## 15. Evidence inventory

Files read during this recovery (all read-only except the two new files listed at the
end):

| File | Role |
|---|---|
| `C:\Users\Hp\fruitfly\FLY-SURFER_YOLO11n_Training.ipynb` | primary record (40 code cells, all outputs that survive) |
| `FLY-SURFER\models\YOLO11\deployment\yolo11n_v1_deployment\best.onnx` | deployed graph; metadata + SHA-256 recomputed |
| `FLY-SURFER\models\YOLO11\deployment\yolo11n_v1_deployment\best.pt` | trained checkpoint; SHA-256 recomputed |
| `FLY-SURFER\models\YOLO11\deployment\yolo11n_v1_deployment\model_config.json` | deployment contract |
| `FLY-SURFER\models\YOLO11\deployment\yolo11n_v1_deployment\metrics_summary.json` | published metrics |
| `FLY-SURFER\models\YOLO11\deployment\yolo11n_v1_deployment\SHA256SUMS.json` | bundle manifest |
| `FLY-SURFER\models\YOLO11\yolo11n.pt` | base checkpoint copy; SHA-256 recomputed |
| `FLY-SURFER\configs\detector_config.yaml` | runtime contract, thresholds |
| `FLY-SURFER\README.md` | public claims (lines 194, 239–240, 355–365, 494) |
| `FLY-SURFER\THIRD_PARTY_NOTICES.md` | licence scope |
| `FLY-SURFER\reports\PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` | recommended training command |
| `FLY-SURFER\reports\PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` | BLOCKED decision, environment spec |
| `FLY-SURFER\reports\PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md` | ONNX contract inspection |
| `FLY-SURFER\reports\PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` | "trained 14-class" statement |
| `FLY-SURFER\docs\research\YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` | companion licensing audit (not modified) |
| `FLY-SURFER-DATA\documentation\MODEL_REGISTRY.md` | registry (§1.1–§1.9) |
| `C:\Users\Hp\fruitfly\HF-PUBLICATION\fly-surfer-yolo11n-dataset\dataset.zip` | published dataset archive; SHA-256 recomputed |

Files created by this recovery:

| File | SHA-256 |
|---|---|
| `C:\Users\Hp\fruitfly\EVIDENCE-RECOVERY\yolo11n-training\FLY-SURFER_YOLO11n_Training.ipynb` | `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da` |
| `FLY-SURFER\docs\research\YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` | this document |

Files modified: none. Files deleted: none belonging to the project (two temporary
notebook dumps created for this analysis were removed).

**Recovery date:** 2026-11-25
