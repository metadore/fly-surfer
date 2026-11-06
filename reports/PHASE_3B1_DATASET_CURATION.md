# Phase 3B.1 — dataset curation and sequence-level split design

Status: **complete research artifact.** No model was trained. No dataset file
was modified. No package was installed. No commit was made.

This phase answers a narrower question than "build a detector": *given the
five source sequences in the v15 export, can we construct a defensible
development split and define what the data can and cannot support?* The answer
is yes for a grouped development split, no for an independent test split, and
no for player, coin, lane or metric-distance supervision.

## 1. Inputs

| Item | Value |
|---|---|
| Dataset | Roboflow Subway Surfers Object Detection, v15, YOLOv8 export |
| Root | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8/` |
| Version evidence | `data.yaml` → `roboflow.version: 15`; README export date 2024-05-05 |
| Licence | CC BY 4.0 (as declared by Roboflow) |
| Files | 4,659 (2,328 images, 2,328 labels, 3 metadata files); 217 MB |
| Images | 2,328 JPEG, all 606 × 1050 RGB |
| Boxes | 8,666 across 14 classes |
| Splits present | `train` 1,825, `valid` 503; no `test` despite the YAML entry |
| Prior audit | `reports/PHASE_3B02_V15_DATASET_AUDIT.md` (retained; its empty-label conclusions were corrected here) |

The v4 report and files were not touched. The v4 extraction is absent from
disk; only its reports and previews survive, so no v4/v15 byte comparison was
attempted here.

## 2. Method

Two read-only tools were added:

- `experiments/phase_3b/curate_dataset.py` — builds the group inventory,
  classifies empty labels, measures duplicate-ID similarity, computes class
  coverage and emits the split manifest.
- `tests/test_curation.py` — six tests covering group atomicity, LOGO
  coverage, empty-label classification, duplicate-ID detection, exclusion
  handling and leak rejection.

The audit script `experiments/phase_3b/audit_dataset.py` was extended
additively so it could still reproduce the v4 audit unchanged. Dataset files
were opened read-only; nothing was written under `datasets/`.

**Canonical frame ID** = filename stem up to `_jpg.rf.`. **Group prefix** =
the canonical ID before `_mp4-`. Each group is treated as atomic: it may not
appear on both sides of any split.

## 3. Sequence inventory

| Group | Images | train / valid | Boxes | Empty labels | Unique frame IDs | Duplicate IDs | Contiguous runs | Longest run | Median gap | Max gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `datasetfootage` | 504 | 403 / 101 | 1,681 | 0 | 504 | 0 | 1 | 504 | 1 | 1 |
| `subwayavitomp4` | 501 | 350 / 151 | 1,798 | 0 | 501 | 0 | 304 | 5 | 2 | 14 |
| `subwayedited2` | 392 | 313 / 79 | 1,580 | 0 | 392 | 0 | 1 | 392 | 1 | 1 |
| `subwayedtied` | 304 | 258 / 46 | 1,326 | 9 | 304 | 0 | 1 | 304 | 1 | 1 |
| `subwayy1_1` | 627 | 501 / 126 | 2,281 | 3 | 331 | 296 | 1 | 331 | 1 | 1 |

Key structural findings:

- **The five sequences are not equally sampled.** Three are dense frame
  sequences (gap 1); `subwayavitomp4` is a sparse sample (304 runs, longest
  run 5, median gap 2, max gap 14). Temporal models will see very different
  sampling intervals across groups.
- **`datasetfootage` and `subwayedited2` have overlapping-looking frame ranges
  but are distinct groups**; filenames, not frame numbers, define identity.
- **`subwayy1_1` is not a simple 331-frame sequence.** It contains 627 images
  for 331 frame IDs, i.e. two recordings colliding on filenames (Section 4).
- The original v15 split cuts every group across train and valid. Grouping by
  prefix removes this leakage at the group level, which is the entire point of
  this phase.

## 4. Duplicate canonical frame IDs in `subwayy1_1`

| Same-ID pair placement | Pairs |
|---|---:|
| both in original `train` | 192 |
| original `train` / `valid` | **91** |
| both in original `valid` | 13 |
| total | **296** |

The 296 pairs are *not* duplicate frames. Paired images differ at 64-bit dHash
Hamming distance 9–39 (median 26; p25 23, p75 29; 283/296 above 16; none at
≤ 8), and **all 296 label pairs differ**. They are two separate recordings
exported under the same frame filenames.

Consequences:

- deduplicating by frame ID would silently delete 296 real images;
- the 91 cross-split same-ID pairs are a leakage channel that the dHash ≤ 4
  near-duplicate audit does not see;
- `subwayy1_1` must stay one atomic group. It is never split internally and is
  never merged with another prefix.

The v15 adjacency statistic (554 of 1,724 consecutive pairs cross the split)
collapses each duplicate ID to one split, so it is a conservative estimate for
this group.

## 5. Empty-label investigation

All 12 empty label files were inspected (previews in
`experiments/phase_3b/previews_v15/`).

| Frames | Group | Classification | Evidence |
|---|---|---|---|
| 293–301 (9) | `subwayedtied` | **probable annotation gap** | contiguous run bracketed by frame 292 (4 boxes) and 302 (5 boxes); previews show trains, wagons and barriers; 8 in train, frame 298 in valid |
| 213 | `subwayy1_1` (train copy) | ambiguous, plausibly valid | the other same-ID copy (valid) has 4 boxes; different moment in a two-recording collision |
| 217 | `subwayy1_1` (valid copy) | ambiguous, plausibly valid | near-blank transition frame; other copy has 4 boxes |
| 262 | `subwayy1_1` (valid copy) | ambiguous, plausibly valid | cutscene/coin frame; other copy has 4 boxes |

Policy: **all 12 are excluded from the curated splits**, regardless of
classification. The exclusion is conservative because nine are almost
certainly gaps and three cannot be confirmed. Exclusion removes only empty
label files (zero boxes), so class totals are unchanged. The dataset itself
was not repaired or modified.

The practical rule for Phase 3B.2 is: an empty label in this dataset is not
evidence of an empty scene. Evaluation must not treat unlabelled obstacles as
true negatives without review.

## 6. Class support and roles

### 6.1 Overall counts and curated-split counts

| ID | Class | All boxes | Train boxes | Valid boxes | Support judgement |
|---:|---|---:|---:|---:|---|
| 0 | `boots-powerup` | 24 | 24 | **0** | too rare; train-only |
| 1 | `boxtrain` | 1,374 | 625 | 749 | strong |
| 2 | `jump-barrier` | 417 | 254 | 163 | strong |
| 3 | `jump-electric` | 14 | 14 | **0** | too rare; train-only |
| 4 | `jump-hedge` | 44 | 18 | 26 | weak |
| 5 | `jump-roll-barrier` | 763 | 407 | 356 | strong |
| 6 | `jump-trash` | 96 | 34 | 62 | weak |
| 7 | `ledge` | 135 | 87 | 48 | moderate |
| 8 | `pogstick-powerup` | 118 | 53 | 65 | moderate |
| 9 | `ramp` | 1,223 | 606 | 617 | strong |
| 10 | `roll-barrier` | 309 | 147 | 162 | strong |
| 11 | `train` | 2,791 | 1,617 | 1,174 | strong |
| 12 | `undercover-barrier` | 215 | 196 | 19 | moderate overall, weak in validation |
| 13 | `wall` | 1,143 | 622 | 521 | strong |
| | **total** | **8,666** | **4,704** | **3,962** | |

The extremes are unchanged from the audit: `train` : `jump-electric` =
199.4 : 1; the top five classes hold 84.2% of boxes. No threshold here is
statistically derived; "weak" means a per-class validation metric would rest
on a few dozen boxes and should be reported as unstable.

### 6.2 Coverage by group

| Class | footage | avi | edited2 | edtied | y1_1 |
|---|---:|---:|---:|---:|---:|
| `boots-powerup` | 0 | 0 | 0 | **24** | 0 |
| `boxtrain` | 421 | 290 | 166 | 169 | 328 |
| `jump-barrier` | 52 | 87 | 97 | 70 | 111 |
| `jump-electric` | 0 | 2 | **12** | 0 | 0 |
| `jump-hedge` | 1 | 5 | 13 | 0 | 25 |
| `jump-roll-barrier` | 150 | 184 | 161 | 62 | 206 |
| `jump-trash` | 0 | 9 | 25 | 0 | 62 |
| `ledge` | 0 | 9 | 78 | 0 | 48 |
| `pogstick-powerup` | 2 | 6 | 10 | 37 | 63 |
| `ramp` | 244 | 180 | 132 | 294 | 373 |
| `roll-barrier` | 45 | 70 | 37 | 40 | 117 |
| `train` | 542 | 746 | 348 | 523 | 632 |
| `undercover-barrier` | 0 | 159 | 37 | 0 | 19 |
| `wall` | 224 | 51 | 464 | 107 | 297 |

Two classes determine the split geometry:

- `boots-powerup` exists **only** in `subwayedtied` (24 boxes). Any split with
  that group in validation cannot also train the class.
- `jump-electric` exists only in `subwayavitomp4` (2) and `subwayedited2` (12).
  Any validation side lacking both cannot evaluate it.

### 6.3 Declared roles (hypotheses, not verified mechanics)

| Role | Classes |
|---|---|
| large collision | `train`, `boxtrain` |
| low collision (jump) | `jump-barrier`, `jump-electric`, `jump-hedge`, `jump-roll-barrier`, `jump-trash` |
| overhead collision (roll) | `roll-barrier`, `undercover-barrier` |
| terrain | `ramp`, `ledge` |
| boundary | `wall` |
| collectible power-up | `boots-powerup`, `pogstick-powerup` |

These mappings come from the class names and are stored in
`configs/phase_3b1_curation.yaml` as hypotheses for the eventual GameState
adapter. They are **not** verified game mechanics and were not used to alter
any label.

## 7. Split design

### 7.1 Why not a conventional train/validation/test split

There are five source groups, no sixth independent recording, and no held-out
capture. A three-way split would either:

- hold out one group as test, leaving four groups for train+validation and
  making one class untrainable (if `subwayedtied` is held out) or making rare
  classes unevaluable; or
- split within groups, reintroducing the frame-level leakage this phase
  exists to remove.

With five groups, the defensible design is a **grouped development split**
plus **leave-one-group-out (LOGO)** folds for variance estimation. There is no
independent test set. Any final accuracy claim requires a new recording or a
previously unseen sequence.

### 7.2 Fixed development split

| Side | Groups | Images | Boxes | Missing classes |
|---|---|---:|---:|---|
| train | `subwayavitomp4`, `subwayedited2`, `subwayedtied` | 1,188 | 4,704 | none |
| valid | `datasetfootage`, `subwayy1_1` | 1,128 | 3,962 | `boots-powerup`, `jump-electric` |

Reasons for this assignment:

1. **All 14 classes are trainable.** `boots-powerup` requires
   `subwayedtied` on the training side.
2. **Related edited variants stay together.** `subwayedited2` and
   `subwayedtied` share an edited-export naming family; keeping them on the
   train side avoids a validation set dominated by one processing provenance.
3. **`subwayy1_1` stays atomic**, so its duplicate-ID pairs never cross the
   split.
4. **Validation is a cross-domain check**: `datasetfootage` (name implies raw
   capture) and `subwayy1_1` (a separate recording) are both unseen in
   training. This is a design rationale, not a verified capture history.
5. **The 12 empty labels are excluded** (9 from the train side, 3 from the
   valid side), leaving 2,316 assignments.

Validation caveats: `boots-powerup` and `jump-electric` cannot be evaluated at
all; `undercover-barrier` (19 boxes), `jump-hedge` (26), `ledge` (48),
`jump-trash` (62) and `pogstick-powerup` (65) have weak support. These classes
must be reported separately or marked unsupported rather than folded into a
single mAP.

### 7.3 Leave-one-group-out folds

Each fold uses one group as validation and the other four (minus exclusions)
as training. This is for variance estimation, not for selecting a final model.

| Fold | Validation group | Train images | Valid images | Train boxes | Valid boxes | Validation classes with zero support |
|---:|---|---:|---:|---:|---:|---|
| 1 | `datasetfootage` | 1,812 | 504 | 6,985 | 1,681 | boots, electric, trash, ledge, undercover |
| 2 | `subwayavitomp4` | 1,815 | 501 | 6,868 | 1,798 | boots |
| 3 | `subwayedited2` | 1,924 | 392 | 7,086 | 1,580 | boots |
| 4 | `subwayedtied` | 2,021 | 295 | 7,340 | 1,326 | electric, hedge, trash, ledge, undercover |
| 5 | `subwayy1_1` | 1,692 | 624 | 6,385 | 2,281 | boots, electric |

Fold 4 also has **no training instances of `boots-powerup`**, because that
class occurs only in the fold's validation group. This is exactly the coverage
limit the fixed split avoids; it is preserved in the fold table rather than
hidden.

### 7.4 Manifest semantics

`reports/PHASE_3B1_SPLIT_MANIFEST.json` records, for each of the 2,316
included images, the assigned side, the group, and the exclusion list with
reasons. The assignment is by group, so no group appears on both sides. The
manifest is a *design artifact*: Phase 3B.2 must copy or symlink files into a
derived working directory and leave the original dataset untouched.

## 8. Missing modalities

| Modality | Status in v15 | Implication |
|---|---|---|
| Player | unlabelled | `GameState.player` cannot be derived from detector output; needs a fixed-camera assumption or separate localisation |
| Coins | no class, no boxes | coin collection cannot be supervised or detected; coin trails are unmodelled distractors |
| Lanes / rails | no annotations | lane index requires geometric inference, not detection |
| Metric distance | no labels | box size/bottom edge is an uncalibrated proxy; GameState distance remains a design convention |
| HUD / emulator chrome | unlabelled | crop or mask before perception, or it becomes spurious input |

The 14 detector classes therefore cover obstacles, terrain, boundaries and two
power-ups only. This is sufficient for the obstacle half of `GameState`, not
for a complete game state.

## 9. Implications for Phase 3B.2

1. Train and evaluate on the fixed grouped split in the manifest; never use
   the original Roboflow train/valid folders as-is.
2. Report per-class results only where validation support exists; explicitly
   mark `boots-powerup` and `jump-electric` as unevaluable.
3. Treat `jump-hedge`, `jump-trash`, `ledge`, `pogstick-powerup` and
   `undercover-barrier` as low-support classes.
4. Do not derive player position, coins or lane index from this dataset
   without a separate component or annotation pass.
5. Keep perception output separate from the connectome simulation: the
   detector produces a structured `PerceivedScene`; a separate adapter
   validates and maps it to `GameState`; the Phase 3A encoders remain the only
   route into neural activity.
6. Use LOGO folds to quantify how much performance depends on the source
   sequence, not to tune a single number upward.

## 10. Reproduction

```bash
python experiments/phase_3b/curate_dataset.py \
  --dataset "datasets/external/subway surfers/roboflow_v15_yolov8" \
  --config configs/phase_3b1_curation.yaml \
  --json reports/PHASE_3B1_DATASET_CURATION.json \
  --manifest reports/PHASE_3B1_SPLIT_MANIFEST.json
```

Expected console summary:

```
groups=5 images=2328 boxes=8666
fixed train=1188 valid=1128 excluded=12
train_missing=[] valid_missing=['boots-powerup', 'jump-electric']
empty probable_gap=9 isolated_plausible=3
```

Tests:

```bash
python -m pytest tests/test_curation.py -q
python -m pytest -q
```

## 11. Verification

| Check | Result |
|---|---|
| Root `README.md` SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` (unchanged) |
| Dataset file count | 4,659 (unchanged) |
| Dataset size | 217 MB |
| Dataset files written | none |
| v4 audit report SHA-256 | `edde79ad...b88a6` (md), `86a24b54...45095` (json); untouched |
| v15 audit JSON | regenerated with per-sequence adjacency; `PHASE_3B02` md corrected for the 9/3 empty-label split |
| Models trained | none |
| Packages installed | none |
| Git staged changes | none |
| Commits / pushes | none |

## 12. Non-claims

- No detector was trained, evaluated or benchmarked.
- The split is a design, not evidence that a model generalises.
- The nine empty labels are probable gaps, not a measured miss rate; the
  three `subwayy1_1` empties remain ambiguous.
- Duplicate-ID similarity is perceptual, not proof of provenance; the two
  recordings are inferred from differing labels and dHash distance.
- Class roles are name-derived hypotheses.
- Nothing here authorises Phase 3B.2; that requires separate approval.
