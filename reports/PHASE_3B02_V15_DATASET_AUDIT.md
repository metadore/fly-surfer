# Phase 3B.02 — Subway Surfers v15 dataset forensics

Audit date: 2026-11-04. Status: **audit complete; no model was trained,
fine-tuned, evaluated or deployed.**

Dataset root requested: `datasets/external/subway surfers/roboflow_v15_yolov8/`

Machine-readable output: `reports/PHASE_3B02_V15_DATASET_AUDIT.json`
Visual previews: `experiments/phase_3b/previews_v15/`

## Executive summary

The local copy is a genuine **version 15** export of
`subway surfers object dataset`: `data.yaml` declares
`roboflow.version: 15`, the extracted root is named `v15-added`, and both
README files agree. The folder name is therefore consistent with the metadata
this time, unlike the previous v4 copy.

The dataset contains **2,328 images, 2,328 label files and 8,666 bounding
boxes** in YOLOv8 text format. It has `train` (1,825 images) and `valid`
(503 images) splits. `data.yaml` also declares a `test: ../test/images`
entry, but **no test directory or test images exist locally**. The archive
that produced the extraction is **not present** anywhere under the project or
the home directory.

Annotation *formatting* is clean: no malformed lines, no missing or orphan
label files, no duplicate lines, no out-of-range coordinates, no boxes
outside the image and no corrupt images. The substantive problems are
semantic, statistical and methodological:

- **Class names now exist** (14 classes, IDs 0–13), but coverage is severely
  imbalanced: `train` has 2,791 boxes while `jump-electric` has 14
  (199:1). The top five classes hold 84.2% of all boxes.
- **Twelve label files are empty.** Phase 3B.1 inspected all twelve: nine
  (`subwayedtied` frames 293–301) sit in a contiguous unlabelled run bracketed
  by labelled frames and contain visibly annotatable obstacles, so they are
  almost certainly annotation gaps. The other three (`subwayy1_1` frames 213,
  217, 262) are plausibly correct empty labels but could not be confirmed.
  Either way, empty does not reliably mean an empty scene here.
- **Coins and the player are not annotated at all.** Coins are prominent in
  almost every sampled frame, and the player character is always visible, but
  neither appears in the 14-class schema.
- **Lane geometry is not annotated.** Rails and lane boundaries are only
  implicit in the image.
- **The train/valid split leaks badly.** Five source videos are all split
  across both sets, and **554 of 1,724 consecutive-frame pairs (32.1%) cross
  the split boundary**. The split is random at frame level, not grouped by
  video or time.
- **224 perceptual near-duplicate pairs** were found at Hamming distance ≤ 4,
  of which **58 cross the split** and 35 of those are within five frames.
- Images are full BlueStacks emulator screenshots with game HUD, pause
  button and toolbar chrome.

**Decision:** v15 is materially better documented than v4 (it has a class map
and 4.6× the images) and can support format-level, geometry and scene-graph
prototyping. It is **still not suitable for semantic detector training or
model-accuracy claims** for Phase 3B.1, because of the leaked split, missing
coin/player/lane coverage, nine probable annotation gaps (plus three ambiguous
empty labels) and the extreme class imbalance.

## Version verification

The folder name was not trusted. Version was confirmed from three independent
metadata sources:

| Source | Evidence |
|---|---|
| `data.yaml` → `roboflow.version` | `15` |
| `data.yaml` → `roboflow.project` | `subway-surfers-object-dataset` |
| `data.yaml` → `roboflow.workspace` | `horizon-cgt2k` |
| `data.yaml` → `roboflow.url` | `https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset/dataset/15` |
| Extracted root name | `subway surfers object dataset.v15-added.yolov8` |
| `README.roboflow.txt` title | `subway surfers object dataset - v15 added` |
| Export date in README | 2024-05-05 06:32 GMT |
| Image count claimed in README | 2,328 |
| Image count measured | 2,328 |

**Conclusion: version 15 is confirmed.** The README's image-count claim
matches the extraction exactly.

## Dataset provenance and licence

| Item | Finding |
|---|---|
| Source | `https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset` |
| Local root | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8/` |
| Declared version | v15 |
| Export date | 2024-05-05 06:32 GMT |
| Licence asserted in `data.yaml` | CC BY 4.0 |
| Licence asserted in `README.dataset.txt` | CC BY 4.0 |
| Provider | "Provided by a Roboflow user" (no individual author named) |
| Separate licence file | none found |
| Pre-processing | auto-orientation with EXIF stripping |
| Augmentation | none, per README |
| Original archive | **not present** |
| Archive SHA-256 | **not computable — no ZIP found** |

CC BY 4.0 is asserted consistently in both metadata files, but no licence
text or named author is bundled. Attribution requirements must be confirmed
with the Roboflow project before redistribution. This audit does not verify
the licence independently.

Because no archive is present, archive integrity and hash stability cannot be
audited. See "Verification" for the consequence.

## Dataset structure

The requested directory contains a single nested dataset root. Measured
inventory:

| Item | Count |
|---|---|
| Total files under extracted root | 4,659 |
| JPEG images | 2,328 |
| YOLO label `.txt` files | 2,328 |
| Other `.txt` files | 2 (two READMEs) |
| YAML files | 1 (`data.yaml`) |
| Total bytes | 215,392,200 (205.4 MiB) |
| Image bytes | 214,699,661 |

| Split | Images | Labels | Objects | Images missing labels |
|---|---:|---:|---:|---:|
| `train` | 1,825 | 1,825 | 6,844 | 0 |
| `valid` | 503 | 503 | 1,822 | 0 |
| `test` | **0** | **0** | **0** | — |

`data.yaml` declares `train`, `val` and `test` paths. Only `train/` and
`valid/` exist. The declared `test` split is therefore a dangling reference;
any pipeline that trusts the YAML will fail or silently create an empty test
set.

There is no archive, no separate licence file and no additional metadata
beyond `data.yaml` and the two READMEs.

## Image and annotation statistics

All 2,328 images are **606 × 1,050 RGB JPEG**, i.e. one uniform resolution and
format. None failed `PIL.Image.verify()`, and all were decodable for perceptual
hashing.

| Image file size | Bytes |
|---|---:|
| minimum | 45,932 |
| p05 | 70,885 |
| median | 94,256 |
| p95 | 107,758 |
| maximum | 118,175 |
| mean | 92,225 |

| Statistic | Value |
|---|---:|
| Total bounding boxes | 8,666 |
| Images with ≥ 1 object | 2,316 |
| Images with 0 objects | 12 |
| Multi-object images | 2,189 |
| Single-object images | 127 |
| Mean objects per image (all) | 3.723 |
| Mean objects per labelled image | 3.742 |
| Multi-object share of labelled images | 94.5% |
| Train share of boxes | 79.0% |
| Valid share of boxes | 21.0% |

Objects per image range from 0 to 9. The mode is 3 objects (595 images),
followed by 4 (585) and 2 (365). Only 12 images have zero annotations and all
12 are **empty label files, not missing files**.

## Class distribution

`data.yaml` declares 14 classes. All IDs 0–13 are observed, all are present in
both splits, and no undeclared class ID appears.

| ID | Name | Boxes | Images | Train | Valid |
|---:|---|---:|---:|---:|---:|
| 0 | boots-powerup | 24 | 24 | 20 | 4 |
| 1 | boxtrain | 1,374 | 1,020 | 1,081 | 293 |
| 2 | jump-barrier | 417 | 369 | 326 | 91 |
| 3 | jump-electric | 14 | 14 | 9 | 5 |
| 4 | jump-hedge | 44 | 38 | 36 | 8 |
| 5 | jump-roll-barrier | 763 | 646 | 623 | 140 |
| 6 | jump-trash | 96 | 77 | 76 | 20 |
| 7 | ledge | 135 | 89 | 109 | 26 |
| 8 | pogstick-powerup | 118 | 118 | 86 | 32 |
| 9 | ramp | 1,223 | 945 | 987 | 236 |
| 10 | roll-barrier | 309 | 290 | 256 | 53 |
| 11 | train | 2,791 | 1,722 | 2,155 | 636 |
| 12 | undercover-barrier | 215 | 99 | 178 | 37 |
| 13 | wall | 1,143 | 526 | 902 | 241 |

Imbalance summary:

| Metric | Value |
|---|---:|
| Largest class | 2,791 (`train`) |
| Smallest class | 14 (`jump-electric`) |
| Max:min ratio | 199.36 : 1 |
| Top-1 share | 32.2% |
| Top-5 share | 84.2% |
| Classes with < 30 boxes | 2 (`jump-electric` 14, `boots-powerup` 24) |
| Classes absent from `valid` | 0 |

Imbalance is less extreme than v4's 746:1, but the absolute concentration is
worse at the top: five classes now account for 84.2% of boxes versus 80.5% in
v4. `jump-electric` and `boots-powerup` are too rare for reliable per-class
validation: the valid split contains only 5 and 4 instances respectively.

## Annotation validation

Checks performed on all 2,328 label files:

| Check | Result |
|---|---|
| Fields per line | all 5 |
| Integer class IDs | all valid |
| Finite coordinates | all valid |
| Coordinates in `[0, 1]` | all valid |
| Positive width and height | all valid |
| Boxes inside image bounds | 0 violations |
| Malformed lines | 0 |
| Duplicate annotation lines | 0 |
| Missing label files | 0 |
| Orphan label files | 0 |
| Empty label files | **12** |
| Corrupt images | 0 |
| Exact duplicate label files | 1 group of 12 (the empty files) |

The 12 empty labels were investigated individually in Phase 3B.1:

| Frames | Group | Classification | Evidence |
|---|---|---|---|
| 293–301 (9) | `subwayedtied`, train except 298 in valid | **probable annotation gap** | contiguous run bracketed by frame 292 (4 boxes) and frame 302 (5 boxes); previews show trains, wagons and barriers |
| 213, 217 (2) | `subwayy1_1` | plausibly valid, unconfirmed | each has a second same-ID copy with 4 boxes; the 217 copy is a near-blank transition frame |
| 262 (1) | `subwayy1_1` | plausibly valid, unconfirmed | cutscene/coin frame; the second same-ID copy has 4 boxes |

All 12 are quarantined from the Phase 3B.1 splits pending re-annotation or
review. The dataset itself was not modified. This remains a label-quality
defect, not a formatting defect.

No other structural annotation problem was found. In particular, the 0
out-of-range and 0 out-of-image results are genuine; the validator also checks
box corners, not just centres.

## Duplicate and leakage audit

### Exact duplicates

No byte-identical image pairs exist (`exact_image_groups = 0`). The single
exact label group is the 12 identical empty files.

### Duplicate canonical frame IDs in `subwayy1_1`

Phase 3B.1 found a leakage channel that the perceptual hash threshold misses.
`subwayy1_1` has **627 images but only 331 unique canonical frame IDs**
(filename stem before `_jpg.rf.`, after stripping the `_mp4-` frame number).
Frames 0–295 appear twice, giving **296 duplicate-ID images**:

| Same-ID pair placement | Pairs |
|---|---:|
| both in `train` | 192 |
| one in `train`, one in `valid` | **91** |
| both in `valid` | 13 |

These are **not** copies of the same frame. Paired images differ at dHash
Hamming distance 9–39 (median 26; 283/296 above 16; none ≤ 8), and all 296
label pairs differ. They are two separate recordings whose exported filenames
collide. Consequences:

- frame-ID deduplication is unsafe here — the same ID identifies two scenes;
- the 91 cross-split same-ID pairs are a second leakage route independent of
  the 58 cross-split near-duplicate pairs;
- `subwayy1_1` must be treated as one atomic group, not merged into other
  sequences or split internally.

The 1,724 adjacent-pair count collapses each duplicate ID to a single split,
so 554/1,724 is a conservative adjacency estimate for `subwayy1_1`.

### Perceptual near-duplicates

64-bit dHash, Hamming distance ≤ 4:

| Metric | Value |
|---|---:|
| Near-duplicate pairs | 224 |
| Pairs crossing train/valid | **58** |
| Cross-split pairs within ≤ 5 frames | **35** |
| Unique cross-split images in `train` | 54 |
| Unique cross-split images in `valid` | 42 |

Near-duplicates are not confined to one video: pairs occur in all five
sequence families. Cross-split pairs at frame gaps of 0 and 1 confirm
near-identical adjacent frames appearing on both sides of the split.

### Box overlap

| Metric | Value |
|---|---:|
| Box pairs with IoU ≥ 0.50 | 6 |
| Box pairs with IoU ≥ 0.80 | 0 |
| Same-class pairs at IoU ≥ 0.80 | 0 |
| Different-class pairs at IoU ≥ 0.80 | 0 |

There is no evidence of near-identical duplicate boxes within an image. The
six IoU ≥ 0.5 pairs are legitimate overlap between distinct structures.

### Temporal leakage

Five video sequences are present:

| Sequence | Images | Train | Valid | Valid share |
|---|---:|---:|---:|---:|
| `datasetfootage` | 504 | 403 | 101 | 20.0% |
| `subwayavitomp4` | 501 | 350 | 151 | 30.1% |
| `subwayedited2` | 392 | 313 | 79 | 20.2% |
| `subwayedtied` | 304 | 258 | 46 | 15.1% |
| `subwayy1_1` | 627 | 501 | 126 | 20.1% |

**Every sequence appears in both train and valid.** Consecutive-frame pairs
within each sequence were counted per sequence (frame numbers are not
comparable across videos):

| Sequence | Adjacent-frame pairs | Cross-split | Cross-split rate |
|---|---:|---:|---:|
| `datasetfootage` | 503 | 167 | 33.2% |
| `subwayavitomp4` | 197 | 31 | 15.7% |
| `subwayedited2` | 391 | 123 | 31.5% |
| `subwayedtied` | 303 | 78 | 25.7% |
| `subwayy1_1` | 330 | 155 | 47.0% |
| **Total** | **1,724** | **554** | **32.1%** |

The split is random at frame level. A model can see frame *n* during training
and frame *n+1* during validation, so validation metrics would be optimistic
by an unknown margin. This invalidates any accuracy claim made on the shipped
split.

## Bounding-box geometry and alignment

All coordinates are normalised to image width and height.

| Statistic | Width | Height | Area |
|---|---:|---:|---:|
| minimum | 0.0141 | 0.0118 | 0.00035 |
| p05 | 0.0463 | 0.0304 | 0.00157 |
| median | 0.1471 | 0.1095 | 0.01605 |
| p95 | 0.5644 | 0.6982 | 0.30989 |
| maximum | 0.9505 | 0.9790 | 0.65335 |
| mean | 0.2081 | 0.2149 | 0.07084 |

- **Size is widely distributed**, from very small objects (5% of boxes cover
  under 0.16% of the image) to near-full-frame structures (max area 65%).
- **Area correlates with vertical position**: Pearson 0.704 and Spearman 0.649
  against centre-y, and Spearman **0.859** against the box's bottom edge.
  This is consistent with perspective, but it is an image-space correlation,
  not metric distance.
- **Near-field boxes cluster horizontally** at x ≈ 0.1 (387), 0.4 (194) and
  0.7 (370), consistent with three visual lanes. Lane identity is not
  annotated.
- **Box alignment** was checked visually on 20 previews. Boxes generally
  enclose the intended obstacle or train, but large boxes on walls and trains
  are loose and sometimes cover substantial background. There is no
  independent ground truth, so alignment cannot be quantified.

Bounding-box size must not be treated as physical distance. It is an
uncalibrated proxy that also depends on obstacle class, camera motion, jump
state and occlusion.

## Object coverage, including player and coins

| Element | Annotated? | Evidence |
|---|---|---|
| Obstacles / barriers | Partially | 9 class labels, but 2 classes < 30 boxes |
| Trains / wagons | Yes | `train` 2,791, `boxtrain` 1,374 |
| Ramps / ledges / walls | Yes | 3 classes |
| Power-ups | Partially | `boots-powerup` 24, `pogstick-powerup` 118 |
| **Coins** | **No** | no class in schema; coin trails visibly unlabelled |
| **Player** | **No** | player model visible in every sampled frame, never boxed |
| **Lanes / rails** | **No** | no class; lane position only implicit |
| **HUD / UI chrome** | **No** | emulator score bar, pause button and toolbar are present but unlabelled |
| **Distance** | **No** | not a class and not a scalar label |

The empty-label frames are direct evidence of missed obstacles: the inspected
`subwayedtied_mp4-293` frame contains a yellow train, freight wagons and a
barrier, all unlabelled, and frames 293–301 form an unbroken empty run between
labelled frames. This means "no box" cannot be interpreted as "no object"
anywhere in the dataset.

Coins are especially problematic for Phase 3B. The game's central collectible
is visually salient and present in nearly every preview, but the dataset
provides no coin boxes, so a detector trained on it would learn to ignore
coins. Conversely, coin trails would act as unmodelled distractors.

## Visual quality observations

The audit script rendered twenty previews: sixteen selected by the audit script
(eight per split, spanning maximum/minimum object count and maximum/minimum box
area) plus four explicit empty-label frames. Phase 3B.1 added eleven more
(five remaining `subwayedtied` empty frames, and six empty/labelled pairs from
`subwayy1_1`), so `experiments/phase_3b/previews_v15/` now holds 31 JPEGs.
Observations:

- All images are BlueStacks emulator screenshots at a fixed 606 × 1050
  portrait resolution.
- The top ~10–12% of each frame is a persistent HUD (score, coins, high
  score), and a right-side toolbar plus pause button are always present.
  Detectors will learn this chrome unless it is cropped or masked.
- The game view is legible and well exposed; JPEG artifacts are mild.
- Scene composition includes strong perspective, motion blur in some frames,
  heavy occlusion (trains behind trains) and many small distant objects.
- Annotated boxes are broadly sensible, but some large wall/train boxes are
  loose and enclose background.
- Coins, the player, lane boundaries and the HUD are consistently unlabelled.
- The nine `subwayedtied` empty labels are visually populated frames, confirming
  missed annotations; the three `subwayy1_1` empties are ambiguous (see above).

## Scientific suitability for Phase 3B

| Task | Suitability | Reason |
|---|---|---|
| Lane / relative-position estimation | **Low** | lanes are not labelled; only geometric inference possible |
| Obstacle detection | **Partial** | 14 named classes, but 2 are extremely rare and 9 labels have probable annotation gaps |
| Train detection | **Best-supported** | 2,791 `train` boxes (1,722 images) plus 1,374 `boxtrain` boxes (1,020 images) |
| Coin / collectible detection | **None** | coins have no class or boxes |
| Metric distance estimation | **None as labelled** | only an uncalibrated box-size proxy; no distance ground truth |
| Multi-object GameState construction | **Partial** | 94.0% of images are multi-object (94.5% of labelled images), but player, coins and lanes are missing |
| Temporal tracking / prediction | **Not valid as split** | all five sequences and 32.1% of adjacent frames cross the split |
| End-to-end detector training / benchmarking | **Not ready** | leakage, coverage gaps, imbalance and label omissions |

## Comparison with the v4 audit

The v4 report (`reports/PHASE_3B0_DATASET_AUDIT.md`) is preserved unchanged.

| Metric | v4 | v15 | Change |
|---|---:|---:|---|
| Declared version | 4 | **15** | confirmed from metadata |
| Images | 501 | 2,328 | ×4.65 |
| Labels | 501 | 2,328 | ×4.65 |
| Boxes | 1,936 | 8,666 | ×4.48 |
| `data.yaml` | absent | present | class names now available |
| Classes | 17 unnamed IDs (0–16) | 14 named IDs (0–13) | **incompatible schema** |
| Splits present | train, valid | train, valid | test still absent |
| Empty labels | 0 | **12** | new defect |
| Malformed lines | 0 | 0 | unchanged |
| Missing / orphan labels | 0 | 0 | unchanged |
| Max:min imbalance | 746 : 1 | 199.36 : 1 | improved |
| Top-5 share | 80.5% | 84.2% | worse |
| Near-duplicate pairs (≤4) | 55 | 224 | ×4.07 |
| Near pairs crossing split | 19 | 58 | ×3.05 |
| Cross-split pairs ≤ 5 frames | 13 | 35 | ×2.69 |
| Adjacent-frame pairs | 197 | 1,724 | ×8.75 |
| Adjacent pairs crossing split | 68 (34.5%) | 554 (32.1%) | similar rate, far more pairs |
| Multi-object images | 465 (92.8%) | 2,189 (94.0%) | similar |
| Mean objects/image | 3.864 | 3.723 | slightly lower |
| Resolution | 606 × 1050 | 606 × 1050 | unchanged |
| Corrupt images | 0 | 0 | unchanged |

Narrative comparison:

1. **v15 is a new export, not a relabelled v4.** v4 was dated 2022-08-04 and
   re-exported 2026-09-23; v15 was exported 2024-05-05. v15 adds a 14-class
   `data.yaml`, which removes v4's biggest blocker (unknown class semantics).
2. **The class maps are not interchangeable.** v4 observed 17 numeric IDs
   (0–16) with no names; v15 declares 14 named IDs (0–13). v4 annotations
   cannot be interpreted with the v15 class list and must not be merged or
   reused.
3. **v15 contains the v4 footage but re-split it.** All 79 frame IDs that the
   v4 audit explicitly referenced are present in v15, and `subwayavitomp4`
   still has exactly 501 images, consistent with v15 retaining the full v4
   sequence. However, the valid share for that sequence changed from 101/501
   (20.2%) to 151/501 (30.1%), and the class IDs changed, so the split and
   annotations were regenerated rather than preserved byte-for-byte.
4. **v15 adds four more video sequences** (`datasetfootage`,
   `subwayedited2`, `subwayedtied`, `subwayy1_1`), which explains most of the
   image growth.
5. **Leakage persists and grows in absolute terms.** Because every sequence is
   randomly split, v15 has 554 cross-split adjacent pairs versus v4's 68, and
   58 cross-split near-duplicates versus 19.
6. **Annotation quality did not improve uniformly.** v15 has 12 empty labels
   where v4 had none (9 probable gaps, 3 ambiguous), and still has no coin,
   player or lane annotations.
7. **The v4 extracted dataset is no longer on disk.** The v4 audit recorded
   its root as
   `roboflow_v15_yolov8/subway surfers object dataset.v4i.yolov8`; that
   folder, and the v4 ZIP, are now absent. The v4 reports and previews remain
   intact. Consequently the v4 extraction cannot be byte-compared to v15 and
   its archive hash cannot be re-verified.

## Limitations

- **No archive:** no v15 ZIP was found in the project or in a bounded
  home-directory search, so archive integrity, entry count and SHA-256 cannot
  be audited.
- **No v4 extraction:** the previously audited v4 folder and archive are
  absent, so cross-version file-level comparison is limited to the statistics
  and 79 frame IDs recorded in the v4 report.
- **No baseline manifest:** the extraction was not hashed before this audit,
  so "unchanged" is supported by file count, mtimes and the script's read-only
  design, not by a before/after hash manifest.
- **No test split:** `data.yaml` declares one that does not exist.
- **Class semantics are declared, not proven.** Names come from Roboflow
  metadata; this audit did not exhaustively verify every box's semantic
  correctness.
- **Annotations are incomplete.** Nine empty labels are probable annotation
  gaps and three are ambiguous; the true miss rate is unknown because no
  exhaustive manual count was done.
- **Distance is not labelled.** Box size is an image-space proxy only.
- **dHash similarity is not provenance.** Near-duplicate pairs indicate visual
  similarity, not confirmed shared source frames, although frame-gap evidence
  strongly supports temporal relatedness.
- **Frame order is inferred from filenames.** No timestamps are present.
- **Preview sampling is not exhaustive:** 31 of 2,328 images were inspected
  (20 in the audit, 11 added during the Phase 3B.1 empty-label investigation).

## Recommendations for Phase 3B.1

1. **Preserve a canonical v15 archive and record its SHA-256** before any
   further work. The current extraction has no archive to verify against.
2. **Regenerate the split by sequence and time block.** A grouped split by
   video, or better by contiguous time windows, is mandatory before any
   validation metric is meaningful.
3. **Freeze a versioned class schema.** Decide explicitly whether coins, the
   player, lanes and HUD are in scope. If Phase 3B needs them, they must be
   annotated or handled by a separate non-learned component.
4. **Repair or exclude the empty labels.** They currently teach the model
   that populated frames can have no objects. Phase 3B.1 quarantines all 12
   pending review.
5. **Stratify or exclude rare classes.** `jump-electric` (14) and
   `boots-powerup` (24) cannot support reliable per-class metrics; either
   collect more instances or report them as unsupported.
6. **Do not claim detector accuracy on the shipped split.** Use it only for
   pipeline, format and geometry prototyping until items 1–5 are resolved.
7. **Do not reuse v4 annotations.** Their class IDs are incompatible with the
   v15 schema.
8. **Crop or mask the emulator HUD** for any perception experiment, and state
   the crop in the experiment configuration.

## Reproduction and outputs

Command used:

```text
python experiments/phase_3b/audit_dataset.py \
  --dataset "datasets/external/subway surfers/roboflow_v15_yolov8" \
  --outdir experiments/phase_3b \
  --json reports/PHASE_3B02_V15_DATASET_AUDIT.json \
  --previews experiments/phase_3b/previews_v15 \
  --preview-count 8 \
  --phase 3B.02
```

Environment: Python 3.13.14, Pillow 12.0.0, PyYAML 6.0.3, Windows. No package
was installed for this audit.

Changes to the shared audit script, all backward-compatible:

- added `--previews` to write previews outside the v4 directory;
- added `--phase` so the JSON identifies the audit;
- frame adjacency is now computed **per video sequence** instead of globally
  (identical behaviour for v4, which had one sequence);
- near-duplicate pairs now record whether the two frames share a sequence and
  only compute a frame gap when they do;
- `metadata` now records declared vs present split names.

Defaults (`--outdir`, `--json`, preview path, `--phase 3B.0`) are unchanged,
so the original v4 command remains valid. The v15 run used explicit paths and
did not overwrite anything.

Outputs:

- `reports/PHASE_3B02_V15_DATASET_AUDIT.md` (this file)
- `reports/PHASE_3B02_V15_DATASET_AUDIT.json`
- `experiments/phase_3b/previews_v15/` — 20 JPEGs from this audit
  (16 script-selected plus 4 explicit empty-label frames); Phase 3B.1 added
  11 more for the full empty-label review, for 31 total

## Verification

| Check | Result |
|---|---|
| Root `README.md` SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` — unchanged |
| Dataset files before audit | 4,659 |
| Dataset files after audit | 4,659 |
| Newest dataset file mtime | 2026-11-04 23:42 (extraction time; no later writes) |
| Outputs written inside dataset | none; the script rejects paths under the dataset |
| v4 report SHA-256 | MD `edde79ad…b88a6`, JSON `86a24b54…45095` — not modified |
| v4 report mtimes | 23:23 and 23:24; v4 previews 23:19 — all predate this audit |
| v15 ZIP found | none |
| v4 ZIP found | none |
| v4 extracted folder found | none |
| Staged changes | none (`git diff --cached` empty) |
| HEAD | `c08d0a4` — unchanged |
| Training or evaluation run | none |
| Packages installed | none |
| Model files created | none |

Git status shows the earlier Phase 3A/3A.5 working-tree changes and the
3B.0/3B.02 audit outputs; nothing was staged or committed. The only change to
an existing tracked file in this audit is `experiments/phase_3b/audit_dataset.py`.

## Explicit non-claims

- No model was trained, fine-tuned, evaluated, quantised or deployed.
- No accuracy, precision, recall, mAP or robustness number is reported.
- The class names are reported as declared by Roboflow; their semantic
  correctness was not exhaustively verified.
- Box-size correlations are image-space statistics, not distance measurements.
- Near-duplicate detection indicates visual similarity, not confirmed
  duplicate provenance.
- The audit did not verify the CC BY 4.0 licence independently.
- Nine of the 12 empty labels (the `subwayedtied` run) are probable annotation
  gaps; the three `subwayy1_1` empties are ambiguous. The total miss rate is
  unknown.
- This audit was written before Phase 3B.1 and authorised no follow-on work
  on its own; the later curation decisions are recorded in
  `reports/PHASE_3B1_DATASET_CURATION.md`.
