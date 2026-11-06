# Phase 3B.2B.1 — YOLO11n Dataset Export

**Status: PASS — data preparation only.**

**Date:** 2026-11-06

**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`

**Export directory:** `datasets\exports\phase_3b2b1_yolo11n\`

**ZIP:** `datasets\exports\phase_3b2b1_yolo11n.zip`

No package was installed, no model weight was downloaded, no training run was
started, no ONNX export was produced, the perception pipeline, GameState,
sensory encoders, connectome and simulator were not modified, and no Git write
operation was performed.

---

## 1. Files created

Only the following new files were created. No existing file was overwritten,
renamed, moved or deleted.

| Path | Purpose |
| --- | --- |
| `experiments/phase_3b/export_yolo11_dataset.py` | Reproducible export and `--verify-only` verification script |
| `tests/test_export_yolo11.py` | 15 focused export tests on synthetic fixtures |
| `datasets/exports/phase_3b2b1_yolo11n/dataset.yaml` | Portable Ultralytics dataset configuration |
| `datasets/exports/phase_3b2b1_yolo11n/train/images/` | 1,188 copied training images |
| `datasets/exports/phase_3b2b1_yolo11n/train/labels/` | 1,188 copied training labels |
| `datasets/exports/phase_3b2b1_yolo11n/valid/images/` | 1,128 copied validation images |
| `datasets/exports/phase_3b2b1_yolo11n/valid/labels/` | 1,128 copied validation labels |
| `datasets/exports/phase_3b2b1_yolo11n/provenance/split_manifest.json` | Derived export manifest with source identity, group, split and quarantine state |
| `datasets/exports/phase_3b2b1_yolo11n/provenance/dataset_summary.json` | Machine-readable export statistics |
| `datasets/exports/phase_3b2b1_yolo11n/provenance/attribution.txt` | CC BY 4.0 attribution and modification statement |
| `datasets/exports/phase_3b2b1_yolo11n/provenance/SHA256SUMS.txt` | 4,636 relative-path SHA-256 entries |
| `datasets/exports/phase_3b2b1_yolo11n.zip` | Archive containing the export directory root |
| `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` | This report |
| `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.json` | Machine-readable mirror of this report |

Export file counts: 2,316 images + 2,316 labels + `dataset.yaml` + 4 provenance
files = **4,637 files**. The checksum file covers the other **4,636** files and
excludes itself, as required.

---

## 2. Source manifest authority and hash

The Phase 3B.1 manifest is the sole authority for train/validation membership.
It was read only and is byte-identical to its previously recorded state.

| Property | Value |
| --- | --- |
| Source manifest | `reports/PHASE_3B1_SPLIT_MANIFEST.json` |
| SHA-256 | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` |
| Source dataset root | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8` |
| Dataset version | 15 |
| Raw source images | 2,328 |
| Curated images | 2,316 |
| Quarantined images | 12 |
| Classes | 14 |
| Bounding boxes | 8,666 |

The original Roboflow `train`/`valid` folders were used only as storage
locations. The export split is the manifest's `fixed_split.assignments`, and
that was re-checked for every exported image.

Evidence that the original Roboflow split was not reused:

| Source folder → curated split | Images |
| --- | ---: |
| `train` → `train` | 913 |
| `train` → `valid` | 903 |
| `valid` → `train` | 275 |
| `valid` → `valid` | 225 |
| **Total** | **2,316** |

---

## 3. Export counts and per-class statistics

| Property | Required | Measured | Result |
| --- | ---: | ---: | --- |
| Original v15 images | 2,328 | 2,328 | PASS |
| Curated images | 2,316 | 2,316 | PASS |
| Training images | 1,188 | 1,188 | PASS |
| Validation images | 1,128 | 1,128 | PASS |
| Quarantined images | 12 | 12 | PASS |
| Classes | 14 | 14 | PASS |
| Bounding boxes | 8,666 | 8,666 | PASS |
| Training boxes | — | 4,704 | measured |
| Validation boxes | — | 3,962 | measured |
| Images without boxes | 0 | 0 | PASS |
| Image dimensions | — | 606 × 1050 RGB JPEG (all 2,316) | measured |

Per-class boxes and image support (class IDs are contiguous 0–13 in the audited
order):

| ID | Class | Train boxes | Train images | Valid boxes | Valid images |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | boots-powerup | 24 | 24 | 0 | 0 |
| 1 | boxtrain | 625 | 482 | 749 | 538 |
| 2 | jump-barrier | 254 | 221 | 163 | 148 |
| 3 | jump-electric | 14 | 14 | 0 | 0 |
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
| | **Total** | **4,704** | — | **3,962** | — |

Per-class image counts do not sum to the split image totals because an image can
contain several classes.

**Classes with no validation examples:** `boots-powerup` (24 train boxes) and
`jump-electric` (14 train boxes). These are train-only on this split and cannot
be evaluated on `valid`. This matches the Phase 3B.2B.1 readiness audit; the
export does not pretend they have validation coverage.

---

## 4. Train/validation group membership

| Group | Split | Images | Boxes | Notes |
| --- | --- | ---: | ---: | --- |
| `subwayavitomp4` | train | 501 | 1,798 | |
| `subwayedited2` | train | 392 | 1,580 | |
| `subwayedtied` | train | 295 | 1,326 | 9 quarantined images excluded |
| `datasetfootage` | valid | 504 | 1,681 | |
| `subwayy1_1` | valid | 624 | 2,281 | 3 quarantined images excluded |
| **Total** | | **2,316** | **8,666** | |

No group appears in both splits. Every group is atomic: all of its exported
images are on one side. The derived export manifest records the group of every
entry, and the verification rejects any group with more than one split.

---

## 5. Quarantine handling

All 12 manifest exclusions were excluded. None was copied into the export.

| Reason | Count | Group | Frames |
| --- | ---: | --- | --- |
| `probable_gap` | 9 | `subwayedtied` | 293–301 |
| `isolated_plausible` | 3 | `subwayy1_1` | 213, 217, 262 |
| **Total** | **12** | | |

The quarantined source images had empty labels. They were not repaired,
relabelled or converted into negative examples; they are simply absent from the
export. The derived `split_manifest.json` records each one with
`status: "quarantined"`, its group, reason, source image and source label, and
`exported_image: null`. The source manifest is unchanged.

The export contains no empty label files. The verifier rejects any empty label
because the manifest quarantines them rather than permitting them.

---

## 6. Image and label integrity results

| Check | Result |
| --- | --- |
| Every copied image exists and is readable | PASS (2,316 JPEGs) |
| Every copied label exists | PASS (2,316 `.txt` files) |
| One label for every image | PASS (stem sets match per split) |
| No unexpected files | PASS (only `dataset.yaml`, split images/labels, four provenance files) |
| No duplicate output paths | PASS (4,632 unique image/label paths) |
| No overwritten files | PASS (export root and ZIP did not exist; copies refuse existing destinations) |
| No missing files | PASS |
| Every non-empty label row has exactly five fields | PASS |
| Class IDs are integers in 0–13 | PASS |
| Normalized coordinates and dimensions are valid | PASS |
| Boxes lie within normalized image bounds | PASS |
| Source and destination SHA-256 match | PASS for all 2,316 images and 2,316 labels (4,632 comparisons) |
| Quarantined files absent | PASS |
| Original Roboflow split not used | PASS (see section 2) |
| No group in both splits | PASS |
| Every expected manifest entry appears exactly once | PASS (2,316 unique source identities) |

The image/label pair remains associated through a shared filename stem in the
same split directory. Collision handling is deterministic: if two images in the
same split would produce the same stem, the later one receives
`<stem>__<group>` and, if necessary, `__<counter>`. No collision occurred in
this export (`renamed: 0` for all 2,316 entries), but the rule is covered by a
synthetic test.

---

## 7. YAML validation

`dataset.yaml` is valid Ultralytics YAML and was parsed during verification:

```yaml
path: .
train: train/images
val: valid/images

nc: 14

names:
  0: boots-powerup
  1: boxtrain
  2: jump-barrier
  3: jump-electric
  4: jump-hedge
  5: jump-roll-barrier
  6: jump-trash
  7: ledge
  8: pogstick-powerup
  9: ramp
  10: roll-barrier
  11: train
  12: undercover-barrier
  13: wall
```

Verification confirmed:

- `path` is `"."` and all dataset paths are relative.
- `train` resolves to `train/images` and `val` resolves to `valid/images` from
  the export directory.
- `nc` equals 14 and agrees with the names mapping.
- IDs are contiguous 0–13 in the audited order; no class was reordered.
- The mapping matches the manifest and the audited v15 `data.yaml`.
- The same paths resolve after extracting the ZIP into a different directory;
  this is covered by a test that extracts the archive and verifies the copy.

The source `data.yaml` declares `test: ../test/images`, but the v15 extraction
has no `test` directory. The export deliberately omits `test`; it does not
invent one.

---

## 8. Checksum verification

`provenance/SHA256SUMS.txt` contains **4,636** lines, one for every exported
file except the checksum file itself.

| Covered content | Count |
| --- | ---: |
| Training images | 1,188 |
| Training labels | 1,188 |
| Validation images | 1,128 |
| Validation labels | 1,128 |
| `dataset.yaml` | 1 |
| `split_manifest.json`, `dataset_summary.json`, `attribution.txt` | 3 |
| **Total** | **4,636** |

All paths are relative to the export root. Verification recomputed every hash
and compared it with the recorded value; all matched. The checksum file's own
SHA-256 is:

`fd1b0711685e8ea77eff9b8e2281742e70cc3547449dd1e8b03707e965fe5cf2`

The checksum manifest was also used to verify every ZIP member. This makes the
export independently checkable after extraction with:

```bash
cd phase_3b2b1_yolo11n
sha256sum -c provenance/SHA256SUMS.txt
```

---

## 9. ZIP integrity and contents

| Property | Value |
| --- | --- |
| Path | `datasets/exports/phase_3b2b1_yolo11n.zip` |
| Size | 211,529,060 bytes (201.73 MiB) |
| SHA-256 | `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff` |
| Archive integrity (`testzip`) | PASS (no bad member) |
| Members | 4,638 (1 root directory entry + 4,637 files) |
| Root | `phase_3b2b1_yolo11n/` |
| `phase_3b2b1_yolo11n/dataset.yaml` | present |
| `phase_3b2b1_yolo11n/provenance/SHA256SUMS.txt` | present |
| Entries outside the root | none |
| `.pt` / `.pth` / `.onnx` / `.ckpt` members | none |

The ZIP was written with fixed 1980-01-01 timestamps so repeated exports of the
same content are byte-stable apart from the timestamped summary metadata. The
YOLO11n checkpoint is not included.

---

## 10. Test results

A new focused suite was added at `tests/test_export_yolo11.py`, using synthetic
temporary datasets. It covers:

- real Phase 3B.1 manifest membership and exact expected counts;
- manifest-to-export membership and uniqueness;
- quarantine exclusion;
- group separation;
- filename collision handling and no-overwrite behavior;
- image/label matching;
- invalid class IDs;
- invalid normalized coordinates;
- missing labels;
- checksum mismatch;
- source content change;
- YAML path resolution after ZIP extraction;
- exact-count mismatch rejection;
- ZIP root, checksum inclusion and absence of checkpoints;
- refusal to overwrite an existing export.

| Suite | Result |
| --- | --- |
| New tests: `tests/test_export_yolo11.py` | **15 passed** |
| Full suite: `python -B -m pytest -q` | **280 passed in 20.35s** |

The 265 pre-existing tests still pass. No existing test was modified.

---

## 11. Dataset licence and attribution status

The dataset is **CC BY 4.0**. The export contains
`provenance/attribution.txt`, which records:

- Dataset name: Subway Surfers Object Dataset.
- Roboflow workspace: `horizon-cgt2k`.
- Roboflow project: `subway-surfers-object-dataset`.
- Dataset version: 15.
- Original export date: 2024-05-05, confirmed by `README.roboflow.txt`
  ("May 5, 2024 at 6:32 AM GMT").
- Dataset licence: CC BY 4.0, confirmed by `README.dataset.txt` and
  `data.yaml`.
- Source URL:
  `https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset/dataset/15`.
- Licence link: `https://creativecommons.org/licenses/by/4.0/`.
- Attribution: "Provided by a Roboflow user" in workspace `horizon-cgt2k`.
  The local metadata does not name an individual creator or publisher beyond
  that statement.
- Modifications: group-based re-splitting; 12 quarantined images excluded;
  images and labels copied into a portable YOLO directory structure; no
  original annotation values intentionally changed; filenames unchanged unless
  a collision required a deterministic suffix (none occurred).
- Statement that this export does not create an independent test set; `valid`
  is group-held-out development data.

`README.dataset.txt` also records the pre-processing applied by Roboflow:
auto-orientation with EXIF stripping and no image augmentation.

---

## 12. Model licence status

The existing local checkpoint `models/YOLO11/yolo11n.pt` (5,613,764 bytes) is a
separate work under **AGPL-3.0**. It is not part of this dataset, is not covered
by CC BY 4.0, and is not included in the export directory or ZIP.

The dataset attribution states the dataset's CC BY 4.0 status and explicitly
separates the model's licence; it does not relicence the dataset as AGPL-3.0.
Any use of the checkpoint or Ultralytics YOLO11 in Colab must comply with
AGPL-3.0 in addition to the dataset's CC BY 4.0 terms.

---

## 13. Known limitations

1. There is no independent test split. Five recordings cannot form one; the
   validation split is group-held-out development data.
2. `boots-powerup` and `jump-electric` have zero validation boxes and are
   unevaluable on this split.
3. Low validation support requires explicit support counts:
   `undercover-barrier` 19 boxes / 15 images, `jump-hedge` 26 / 21, `ledge`
   48 / 32, `jump-trash` 62 / 44, `pogstick-powerup` 65 / 65.
4. The 12 empty labels were quarantined, not repaired. An empty label is not
   evidence of an empty scene in this dataset.
5. Original annotations are copied unchanged, including any annotation errors
   that survived curation.
6. Player, coins, lanes and metric distance are not annotated and are not part
   of this export.
7. The source `data.yaml` declares a `test` path, but no test images exist; the
   export has no test split.
8. The ZIP is about 202 MiB, so Colab upload may require Google Drive rather
   than a direct browser upload.
9. No detector was trained or evaluated here. This report makes no accuracy or
   generalisation claim.

---

## 14. Exact steps to upload and use this ZIP in Google Colab

The ZIP contains the export directory itself, so extraction produces
`phase_3b2b1_yolo11n/dataset.yaml`.

1. Upload `datasets/exports/phase_3b2b1_yolo11n.zip` to Colab or Google Drive.
   For a Drive upload, mount Drive first:

   ```python
   from google.colab import drive
   drive.mount("/content/drive")
   ```

2. Extract the archive:

   ```bash
   !unzip -q /content/drive/MyDrive/phase_3b2b1_yolo11n.zip -d /content/datasets
   ```

3. Verify the extracted export before training:

   ```bash
   !cd /content/datasets/phase_3b2b1_yolo11n && \
     sha256sum -c provenance/SHA256SUMS.txt
   ```

4. Install Ultralytics in the Colab runtime (this is a Colab step; no package
   was installed in the local FLY-SURFER environment):

   ```bash
   !pip install -q ultralytics
   ```

5. The ZIP does not include `yolo11n.pt`. If transfer learning from the local
   checkpoint is intended, upload `models/YOLO11/yolo11n.pt` separately and
   comply with its AGPL-3.0 licence. Otherwise let Ultralytics fetch its own
   checkpoint under its own terms.

6. Train against the exported YAML:

   ```python
   from ultralytics import YOLO

   model = YOLO("/content/yolo11n.pt")  # or "yolo11n.pt"
   model.train(
       data="/content/datasets/phase_3b2b1_yolo11n/dataset.yaml",
       epochs=50,
       imgsz=640,
       batch=16,
       project="/content/runs",
       name="fly_surfer_yolo11n",
   )
   ```

   `imgsz=640` is a starting choice, not a tuned result. The source images are
   606 × 1050.

7. Validate on the group-held-out validation split:

   ```python
   metrics = model.val(
       data="/content/datasets/phase_3b2b1_yolo11n/dataset.yaml",
       split="val",
   )
   ```

8. Report per-class precision, recall, AP and support. Do not report accuracy
   for `boots-powerup` or `jump-electric` on this split, and do not describe
   `valid` as an independent test set.

9. If the project is redistributed, retain `provenance/attribution.txt` and the
   CC BY 4.0 notice. Model artefacts remain separately licensed under
   AGPL-3.0.

---

## 15. Protection verification and prohibitions

| Protection rule | Verification | Result |
| --- | --- | --- |
| Root `README.md` byte-identical | SHA-256 `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` | PASS |
| Phase 3B.1 split manifest unmodified | SHA-256 `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` | PASS |
| `datasets/raw/` unmodified | Read-only access; no write | PASS |
| `datasets/processed/connectome.npz` unmodified | Read-only access; no write | PASS |
| `datasets/external/subway surfers/` unmodified | Read-only access; source images and labels copied, never moved or written | PASS |
| `references/` unmodified | Read-only access; no write | PASS |
| Existing `models/YOLO11/` checkpoint unmodified | Listed only; not copied into the export or ZIP | PASS |
| Original annotations and original dataset YAML unmodified | No write to the source tree | PASS |
| No package installed | No installer command executed | PASS |
| No weights downloaded | No download command executed | PASS |
| No training, ONNX export or simulator run | No such command executed | PASS |
| No perception, GameState, sensory, connectome or simulator change | No such file written | PASS |
| No Git staging, commit, push, stash, reset or amend | No Git write command executed | PASS |
| No existing export overwritten | Target directory and ZIP did not exist before this run | PASS |

---

## 16. Final verdict

**PASS.** The export directory and ZIP exist, all required counts match exactly,
all source/destination SHA-256 comparisons match, the manifest membership is
exact, the YAML is valid and portable after extraction, attribution is present,
the 15 new tests pass, all 280 tests pass, protected files are unchanged, and no
training, installation or Git write operation occurred.

**Exact ZIP path:**

`C:\Users\Hp\fruitfly\FLY-SURFER\datasets\exports\phase_3b2b1_yolo11n.zip`
