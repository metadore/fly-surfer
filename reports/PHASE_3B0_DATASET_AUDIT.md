# Phase 3B.0 — Subway Surfers visual dataset forensics

Audit date: 2026-11-04. Status: **audit complete; no model was trained,
fine-tuned or deployed.**

Dataset root requested: `datasets/external/subway surfers/roboflow_v15_yolov8/`

## Executive summary

The local copy contains **501 images, 501 label files and 1,936 bounding
boxes** in YOLOv8 text format. The extracted dataset has only `train` (400
images) and `valid` (101 images) splits. There is **no test split and no
`data.yaml`**, so the 17 observed numeric class IDs cannot be mapped to class
names from the local files.

The local copy is **not v15**. The folder, archive and `README.roboflow.txt`
all identify **version v4** of `subway surfers object dataset`, dated
2022-08-04 and exported on 2026-09-23. The requested `roboflow_v15_yolov8`
name is therefore a provenance mismatch that must be resolved before any
results are attributed to v15.

Annotation formatting is clean: no malformed lines, no missing or orphan
label files, no empty labels, no duplicate lines, no out-of-range coordinates
and no boxes outside the image. All 501 images are readable 606 × 1050 RGB
JPEGs. The substantive problems are semantic and statistical:

- **Class semantics are unknown** because `data.yaml` is absent.
- **Class imbalance is extreme**: class 13 accounts for 746 of 1,936 objects
  (38.5%), while seven classes have fewer than 10 objects each.
- **The train/valid split leaks**: all frames come from one video, and the
  split is random at frame level. Of 197 consecutive-frame pairs present in
  the data, **68 (34.5%) are split across train and valid**. Nineteen
  cross-split perceptual near-duplicate pairs were found, 13 of them within
  five frames.
- **Coins are incompletely labelled**: sampled frames contain visible coin
  trails with no corresponding boxes.
- **Lane, player and track identity are not labelled.**
- Images are full BlueStacks emulator screenshots with HUD and toolbar chrome.

**Decision:** this dataset can support format-level and geometry prototyping,
but it is **not yet suitable for semantic detector training or model-accuracy
claims** for Phase 3B.1. The blocking items are the missing class map, the
leaked split, the class imbalance, and the unverified semantic coverage of
coins, power-ups, player and lanes.

## Dataset provenance and licence

| Item | Finding |
|---|---|
| Source | `https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset` |
| Local name | `subway surfers object dataset.v4i.yolov8` |
| Declared version | v4, dated 2022-08-04 |
| Export date in README | 2026-09-23 06:25 GMT |
| Licence asserted in `README.dataset.txt` | CC BY 4.0 |
| Provider | “Provided by a Roboflow user” (no individual author named in the local metadata) |
| Separate licence file | none found |
| Original archive | `subway surfers object dataset.v4i.yolov8.zip`, 47,348,785 bytes |
| Archive SHA-256 | `fbd100568c4d516f5e2fedf0022f0a80e644fa050840328156b97c92f207eebd` |
| Archive integrity | `testzip()` passed; 1,004 entries |

The local metadata asserts CC BY 4.0, but no licence text or author
attribution is bundled beyond the two README files. The READMEs were preserved
unchanged. Anyone redistributing the images must confirm the attribution
requirements directly with the Roboflow project; this audit does not verify
the licence independently.

The archive and the extracted folder are both retained. The archive hash above
is the reference value for detecting later modification.

## Dataset structure

```
roboflow_v15_yolov8/
  subway surfers object dataset.v4i.yolov8.zip
  subway surfers object dataset.v4i.yolov8/
    README.dataset.txt
    README.roboflow.txt
    train/
      images/   400 .jpg
      labels/   400 .txt
    valid/
      images/   101 .jpg
      labels/   101 .txt
```

| Inventory item | Count |
|---|---:|
| Files in extracted root | 1,004 |
| Images | 501 |
| Label files | 501 |
| README files | 2 |
| `.jpg` files | 501 |
| `.txt` files | 503 (501 labels + 2 READMEs) |
| Extracted folder size | 47,191,407 bytes (45.01 MB) |
| Parent folder size (with ZIP) | 93 MB |
| Free disk space at audit | 3,212,214,272 bytes (~3.0 GB) |

Unexpected or missing structure:

- No `data.yaml`, `data.yml`, JSON metadata or other YAML file anywhere in the
  extracted dataset.
- No `test` split.
- No extra directories, no non-JPEG images and no stray files in the split
  folders.
- The requested directory contains one nested dataset root whose name reports
  v4. The audit script discovers this nested root rather than assuming the
  requested path is the dataset root.

## Image and annotation statistics

| Split | Images | Labels | Objects | Images missing labels |
|---|---:|---:|---:|---:|
| train | 400 | 400 | 1,570 | 0 |
| valid | 101 | 101 | 366 | 0 |
| **Total** | **501** | **501** | **1,936** | **0** |

All images are **606 × 1050**, RGB, JPEG. No corrupt or unreadable image was
found. Mean objects per image is **3.864**; the distribution is 1 object in 36
images, 2 in 82, 3 in 98, 4 in 112, 5 in 84, 6 in 60, 7 in 18 and 8 in 11.
**465 of 501 images (92.8%) contain more than one labelled object**; 36 images
(7.2%) contain exactly one. No image has an empty label file.

Bounding boxes, normalised to image width and height:

| Statistic | Width | Height | Area |
|---|---:|---:|---:|
| Minimum | 0.010875 | 0.013562 | 0.000316 |
| p01 | 0.016672 | 0.020363 | 0.000586 |
| p05 | 0.023816 | 0.028850 | 0.001153 |
| Median | 0.121774 | 0.101162 | 0.011443 |
| Mean | 0.189521 | 0.194118 | 0.061083 |
| p95 | 0.551972 | 0.659898 | 0.288871 |
| p99 | 0.672978 | 0.717759 | 0.353232 |
| Maximum | 0.948663 | 0.959962 | 0.496481 |

The size distribution is strongly bimodal in effect: many small objects
(5% of boxes cover less than 0.12% of the image area) and a minority of very
large boxes that cover 30–50% of the frame. The large boxes correspond
visually to whole train bodies rather than small object parts.

Spatial distribution: the overall horizontal centre histogram peaks in the
0.3–0.5 band. For near-field objects (`y_center >= 0.6`) the histogram has
peaks near 0.1, 0.3–0.5 and 0.7, consistent with three visual lanes, but the
distribution is broad and no lane label exists. Bounding-box area correlates
with image-space depth proxies: Pearson 0.737 with centre `y`, Spearman 0.686
with centre `y`, and Spearman 0.856 with the bottom edge. This supports an
**uncalibrated image-space size/depth proxy**, not physical distance.

## Class distribution

`data.yaml` is absent, so no class name or declared class count is available.
The audit observed **17 distinct numeric IDs, 0 through 16**. The local files
do not establish whether this is the full class set or whether additional
classes are defined but unattested.

| Class ID | Objects | Share of objects | Images containing it | Train objects | Valid objects |
|---:|---:|---:|---:|---:|---:|
| 13 | 746 | 38.5% | 377 | 599 | 147 |
| 2 | 290 | 15.0% | 217 | 229 | 61 |
| 6 | 184 | 9.5% | 157 | 152 | 32 |
| 10 | 180 | 9.3% | 123 | 144 | 36 |
| 14 | 159 | 8.2% | 59 | 141 | 18 |
| 12 | 135 | 7.0% | 120 | 111 | 24 |
| 3 | 87 | 4.5% | 87 | 70 | 17 |
| 11 | 70 | 3.6% | 68 | 60 | 10 |
| 16 | 28 | 1.4% | 28 | 20 | 8 |
| 15 | 23 | 1.2% | 23 | 17 | 6 |
| 7 | 9 | 0.5% | 9 | 8 | 1 |
| 8 | 9 | 0.5% | 5 | 8 | 1 |
| 9 | 6 | 0.3% | 6 | 2 | 4 |
| 5 | 5 | 0.3% | 5 | 5 | 0 |
| 1 | 2 | 0.1% | 2 | 1 | 1 |
| 4 | 2 | 0.1% | 2 | 2 | 0 |
| 0 | 1 | 0.1% | 1 | 1 | 0 |

The five largest classes account for **80.5%** of all objects; the largest to
smallest ratio is **746:1**. Seven classes have fewer than ten objects, and
classes 0, 4 and 5 have no valid-split instances. Per-class training or
evaluation on those classes is not statistically meaningful with this split.

Visual inspection suggests, but does not establish, that the frequent large
boxes (class 13 and related train-like classes) cover train bodies, that
classes 10 and 12 cover coin-like objects in some frames, and that class 14
covers red-white barriers. These are **visual associations only** and must not
be treated as class names until an authoritative `data.yaml` is recovered.

## Annotation validation

| Check | Result |
|---|---|
| Declared class range available | **No** — `data.yaml` absent |
| Class IDs non-negative integers | Pass; all observed IDs 0–16 |
| Lines with exactly five fields | Pass; 0 malformed lines |
| Coordinates finite and in `[0,1]` | Pass; 0 out-of-range objects |
| Positive width and height | Pass; 0 non-positive boxes |
| Boxes fully inside the image | Pass; 0 outside-image boxes |
| Empty label files | 0 |
| Missing label files | 0 |
| Orphan label files | 0 |
| Images without annotations | 0 |
| Duplicate annotation lines | 0 |
| Overlapping boxes, IoU ≥ 0.8 | 0 pairs |
| Overlapping boxes, IoU ≥ 0.5 | 1 pair |

The single IoU ≥ 0.5 pair is one train/class-13 box and one class-14 box at
IoU 0.503 in `train/images/subwayavitomp4_mp4-476_jpg.rf.e439cf97695c81cb3361f3e4205b67d3.jpg`.
Visual inspection of the previews shows nested-looking boxes in some frames,
but they are mostly distinct objects seen at different depths, not duplicate
annotations. No annotation was corrected, removed or rewritten.

The warning that cannot be evaluated is **class-range membership**: because
the declared class count is missing, the audit can only confirm that IDs are
non-negative integers, not that every ID is declared.

## Duplicate and leakage audit

Exact-file results:

- Exact duplicate image groups: **0**
- Exact duplicate label groups: **0**
- Exact duplicate images across splits: **0**

Perceptual results using a 64-bit difference hash (dHash), threshold Hamming
distance ≤ 4:

- Near-duplicate pairs: **55**
- Cross-split near-duplicate pairs: **19**
- Cross-split pairs within five frames: **13**
- Unique images involved in cross-split pairs: **17 train, 15 valid**
- The 50 stored pair examples are a capped list; the counts above come from
  the full 55-pair computation.

The stronger leakage measurement does not depend on perceptual hashing. All
501 files come from one sequence (`subwayavitomp4`), spanning frames 34–1202.
Train covers frames 34–1202 and valid covers 37–1195, so the ranges overlap.
There are **197 consecutive-frame pairs present in the data**, and **68 of them
(34.5%) have one frame in train and the next in valid**. Examples include
frames 101/102, 126/127, 257/258 and 612/613.

Representative cross-split perceptual pairs:

| dHash distance | Train frame | Valid frame | Frame gap |
|---:|---:|---:|---:|
| 1 | 386 | 384 | 2 |
| 1 | 612 | 613 | 1 |
| 2 | 259 | 258 | 1 |
| 2 | 484 | 530 | 46 |
| 3 | 383 | 384 | 1 |
| 3 | 497 | 462 | 35 |
| 4 | 307 | 308 | 1 |
| 4 | 411 | 407 | 4 |
| 4 | 412 | 407 | 5 |
| 4 | 621 | 623 | 2 |

**Conclusion: the current validation split is not independent.** Adjacent
frames from one continuous video are distributed across both splits. Metrics
computed on this valid split would measure near-frame recall, not
generalisation to a new scene or session. No duplicate or near-duplicate file
was removed or moved.

## Visual quality observations

Twelve annotated previews were generated in
`experiments/phase_3b/previews/` from both splits. Selection was deterministic:
largest and smallest object count, largest and smallest total box area, plus
seeded random samples, with duplicates removed. The previews are copies with
boxes drawn on top; originals were not modified.

Observed:

- **Framing.** Every image is a full BlueStacks emulator screenshot. A top
  application bar and a narrow right-side toolbar are present, and the game
  HUD overlays the top of the play area (score, coin counter, top-run panel,
  pause control). These regions are irrelevant to game-object detection and
  are plausible false-positive sources.
- **Clarity.** Images are clear, saturated and consistently sized. No motion
  blur was obvious in the sampled frames, but the single-video sample cannot
  establish the full range.
- **Box alignment.** Large obstacle/train boxes generally track the visible
  bodies, including boxes that run off the play-field edges. Boxes are
  sometimes much larger than the visible object face because they cover the
  whole train body. Small boxes on distant objects are harder to judge.
- **Occlusion.** Trains and barriers frequently occlude one another and the
  player. Several frames show only a sliver of an object or an object behind
  another, which makes box boundaries ambiguous.
- **Small objects.** Five percent of boxes have area below 0.0012 of the
  frame, and the smallest is 0.000316. Distant coins and barriers can be only
  a few pixels wide after the 606 × 1050 export.
- **Label consistency.** The most serious visual issue is **incomplete coin
  labelling**. For example, `train_02` shows five visible coins but only one
  labelled object (a distant train). Other sampled frames show some coin
  trails boxed and adjacent trails unboxed. The dataset therefore cannot be
  treated as a complete coin detector training set without re-annotation or
  an explicit scope restriction.
- **Player.** The player is visible in the sampled previews but no box was
  drawn around the player. No confirmed player class was identified.
- **Lanes.** Three lanes are visually distinguishable in clear frames, but
  perspective, train occlusion and the fixed camera make lane boundaries
  approximate. No lane label exists in the annotations, so lane assignment
  would require a geometric rule plus validation.
- **Environment.** The single video moves through visually different game
  environments (city, tunnel, park). This gives some appearance variety but
  not session-level or version-level variety.

## Scientific suitability for Phase 3B

| Task | Classification | Evidence and caveat |
|---|---|---|
| 1. Obstacle detection | **Potentially derivable from bounding boxes**, conditional on recovering class names | 1,936 boxes exist and format validation passes; the class-to-obstacle mapping is unknown, so semantic detection cannot be confirmed. |
| 2. Train detection | **Potentially derivable from bounding boxes**, conditional on recovering class names | Frequent large boxes are visually train-like, but this association is not metadata. |
| 3. Lane assignment | **Requires additional annotation** | No lane labels; three lanes are visible in samples but perspective and occlusion make a hand-written rule unvalidated. |
| 4. Power-up detection | **Requires additional annotation** | No class name indicates a power-up; no power-up label was confirmed in the sampled previews. |
| 5. Coin detection | **Requires additional annotation or verification** | Some coin-like boxes exist, but visible coins are unlabelled in sampled frames; the label set is incomplete. |
| 6. Player detection | **Not supported by observed labels** | The player is visible but no player box appeared in the sampled previews; a dedicated annotation pass is needed. |
| 7. Approximate distance estimation | **Potentially derivable as an uncalibrated image-space proxy** | Box area and bottom-edge position correlate with visual depth (Spearman 0.856 for area vs bottom edge), but there is no physical scale or distance ground truth. Bounding-box size is not calibrated physical distance. |
| 8. Temporal object tracking | **Requires additional annotation** | Filenames provide frame order for one video, but there are no track IDs or timestamps and the train/valid split leaks adjacent frames. Tracking could be prototyped, not evaluated, without new labels. |

These classifications describe what the local labels can support. They do not
claim that any detector trained on this dataset would generalise.

## Limitations

- The audit did not train, evaluate or deploy a model.
- `data.yaml` is missing, so class names, declared class count and class
  semantics are unresolved.
- The local copy is v4, not the reported v15; no v15 files were present to
  compare.
- Perceptual near-duplicates use a dHash threshold and were not all manually
  adjudicated.
- Visual quality was assessed on 12 deterministic previews plus the label
  statistics; it is not a full manual review of 501 frames.
- There is no ground truth for lanes, physical distance, player state or
  tracks, so those suitability judgements are structural, not empirical.
- The dataset contains one source video; no session-level or game-version
  holdout exists.
- `cv2` and `imagehash` are not installed. They were not needed: Pillow and
  PyYAML were sufficient. No package was installed.
- Disk free space is low (~3.0 GB); outputs were kept small and no image
  copies were made into the repository.

## Recommendations for Phase 3B.1

Blocking items, in order:

1. **Recover the authoritative class map.** Obtain the original `data.yaml`
   (or the Roboflow class list) for this exact export and record the class
   names, declared count and licence attribution. Do not assign semantic names
   from visual guesswork.
2. **Resolve the version discrepancy.** Re-export or locate the intended v15
   dataset if v15 is actually required; do not label the current v4 files as
   v15.
3. **Build a leak-free split.** Split by contiguous time blocks or, preferably,
   by independent capture sessions. A random frame-level split of one video is
   not a validation set. Reserve a separate video/session for the final test
   set.
4. **Curate or scope the classes.** Exclude or merge classes with fewer than
   about ten instances from training and evaluation, and report per-class
   metrics for the remainder. Decide explicitly whether the task is obstacle
   detection only or a broader object detector.
5. **Re-annotate or scope coins, player, lanes and power-ups.** If Phase 3B
   needs these as outputs, add a targeted annotation pass and measure
   inter-annotator agreement. Otherwise record them as out of scope.

Then, before any detector training:

6. **Preprocess deliberately.** Crop or mask the emulator chrome and HUD,
   preserve the full play field, and document the crop rectangle. Do not crop
   distant objects out of the top of the frame.
7. **Validate the distance proxy.** Treat box area/position as an image-space
   proxy only. Calibrate against game geometry or collect explicit distance
   labels before making any distance claim.
8. **Start with the OpenCV baseline**, as planned in the 3B design, against the
   corrected split. A learned detector should wait until the class map and
   leak-free split exist.

## Reproduction and outputs

Audit command:

```bash
python experiments/phase_3b/audit_dataset.py
```

Environment: Python 3.13.14, Pillow 12.0.0, PyYAML 6.0.3, Windows (`win32`).
The script opens dataset files read-only, streams image hashing and decodes
one image at a time, and writes only outside the dataset directory.

Outputs:

- `reports/PHASE_3B0_DATASET_AUDIT.md` — this report.
- `reports/PHASE_3B0_DATASET_AUDIT.json` — machine-readable results.
- `experiments/phase_3b/audit_dataset.py` — reproducible audit script.
- `experiments/phase_3b/previews/` — 12 annotated preview images.

## Verification

- Original dataset archive SHA-256:
  `fbd100568c4d516f5e2fedf0022f0a80e644fa050840328156b97c92f207eebd`.
- Dataset READMEs, images and labels were not modified, renamed, moved or
  deleted; the audit script only reads them.
- The dataset directory is ignored by the narrowly scoped rule
  `datasets/external/subway surfers/` in `.gitignore`; the rest of
  `datasets/` is not ignored.
- Root `README.md` SHA-256:
  `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10`.
- No model was trained or deployed. No commit, push or stage operation was
  performed.

## Explicit non-claims

- No pathway here is anatomically verified, and nothing in this audit is a
  biological finding.
- Bounding-box size is an image-space proxy, not calibrated physical distance.
- The 17 numeric class IDs are not interpreted as object names without an
  authoritative class map.
- The dataset’s CC BY 4.0 assertion comes from its bundled README; it was not
  independently verified.
