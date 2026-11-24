# Phase 3 — P3-T5 / P3-T6 evidence recovery audit

Audit date: 2026-11-15
Scope: evidence only. No dataset, model, label, config, report or protocol was
modified. No campaign was executed. This report asks one question: *can the
evidence that already exists in this repository resolve the two outstanding
Phase 3 blockers?*

| Task | Requirement (roadmap §4.3) | Verdict |
|---|---|---|
| **P3-T5** | Deterministic processing of the frozen **test** split; measured detection / classification / localisation / distance errors | **BLOCKED** |
| **P3-T6** | Per-class P/R, mAP@0.5, classification, IoU, centre error, lane accuracy, distance MAE/monotonicity; gates in §4.3 | **PARTIAL** |

Both verdicts agree with the two prior audits
(`experiments/phase_3c/results/p3_t5_t11_acceptance_audit.md:30-31`,
`experiments/phase_3c/results/p3_final_phase3_audit.md:55-56`). This audit adds
the per-requirement evidence trace, not a new verdict. It does not revise any
acceptance criterion.

---

## 1. P3-T5 verdict — BLOCKED

### 1.1 Original requirement

The authoritative text is the roadmap, not the later summaries.

- Protocol: "session-level 60/20/20 split; pilot about 1,000 frames from at
  least 10 sessions; full study 5,000–10,000 frames from 20–40 sessions"
  (`docs/PHASE_3_ROADMAP.md:185-188`).
- Acceptance: "Deterministic processing of the frozen test split; measured
  detection/classification/localisation/distance errors"
  (`docs/PHASE_3_ROADMAP.md:195-199`).
- Design §5.3: "Split by recording session, never by random frame… 60% train,
  20% validation, 20% frozen test, stratified by session and scene category"
  (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:259-264`).
- Design §7.1: "Screenshots from the frozen test split can be processed
  consistently and deterministically" (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:343-344`).

The unit of separation is a **recording session**. A split that holds out
frames from a recording already seen elsewhere is not independent at that
unit.

### 1.2 Available evidence

| Fact | Evidence |
|---|---|
| The v15 export declares `test: ../test/images` in `data.yaml`, but no `test/` directory exists | `.../subway surfers object dataset.v15-added.yolov8/data.yaml` (SHA-256 `f6e51bf6…be423`); directory listing |
| Only two splits are present: `train` 1,825 and `valid` 503 images | `reports/PHASE_3B1_SPLIT_MANIFEST.json` → `dataset.splits_present = ["train","valid"]` (SHA-256 `ff3f9119…aa357d`); `reports/PHASE_3B02_V15_DATASET_AUDIT.json` → `inventory.split_counts` |
| The curated split is **two-way**, not 60/20/20: train 3 groups / 1,188 images / 4,704 boxes; valid 2 groups / 1,128 images / 3,962 boxes | `reports/PHASE_3B1_SPLIT_MANIFEST.json` → `fixed_split`; `reports/PHASE_3B1_DATASET_CURATION.md:203-241` |
| Split assignment is group-atomic: 0 groups cross the split | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` → `duplicates.exact_cross_split_groups = 0`; manifest policy |
| Group identity is derived from filenames, not capture metadata; there are exactly five groups | `reports/PHASE_3B1_SPLIT_MANIFEST.json` → `groups`; `reports/PHASE_3B02_V15_DATASET_AUDIT.json` → limitations ("Frame ordering is inferred from filenames; no timestamp metadata is present") |
| One group, `subwayy1_1`, contains two recordings that collide on frame IDs (296 same-ID pairs) | `reports/PHASE_3B1_DATASET_CURATION.md:73-84`; `reports/PHASE_3B1_DATASET_CURATION.json` → `duplicate_frame_ids` |
| The only alternative allocation is 5 leave-one-group-out folds, explicitly for variance, not testing | `reports/PHASE_3B1_SPLIT_MANIFEST.json` → `logo_folds`; `reports/PHASE_3B1_DATASET_CURATION.md:203-212` |
| The repository already states no test split exists | `reports/PHASE_3B1_DATASET_CURATION.md:12-13`; `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:431-433`; `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:777`; `datasets/exports/phase_3b2b1_yolo11n/provenance/dataset_summary.json` → `independent_test_set: false` |
| Detection evaluation is formally recorded as blocked | `experiments/phase_3b/results/detector_evaluation.json` (SHA-256 `96b0176a…bbfacd`): `status: "blocked"`, `protocol.test_split: false`, `predictions_source: null`, `metrics: null` |

Independent-image evidence:

- **0 exact duplicate images** across all 2,328 files (full SHA-256 comparison).
  `reports/PHASE_3B02_V15_DATASET_AUDIT.json` →
  `duplicates.exact_image_duplicate_images = 0`,
  `exact_image_groups = 0`.
- The Roboflow folders themselves are **not** session-independent: 554 of
  1,724 adjacent-frame pairs and 58 near-threshold (dHash ≤ 4) pairs cross the
  original train/valid boundary, 35 of them adjacent
  (`reports/PHASE_3B02_V15_DATASET_AUDIT.json` → `sequence.*`, `duplicates.*`).
  The curated grouped split exists precisely to remove that leakage; it does
  not create a third partition.
- A dHash recheck performed during this audit confirms perceptual hashes are
  saturated by the nearly constant game composition (HUD, rails, sky): the
  distance-0 cross-group pair shows visibly different game states (score,
  coin count, character pose). dHash counts are therefore treated as a
  **screening signal, not provenance proof**. The hard evidence is the exact
  SHA-256 result and the structural group analysis.

### 1.3 What is missing

1. A frozen test partition in the required sense: a set of entire recording
   sessions never used for training, threshold selection, fold inspection or
   replay.
2. Enough distinct sessions. The export has five filename groups containing
   approximately six recordings (`subwayy1_1` = 2). The pilot minimum is ten
   sessions (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:263-264`); the full
   study minimum is twenty.
3. Session metadata (timestamps, capture IDs). Frame ordering and group
   identity are inferred from filenames; the v15 audit states "no timestamp
   metadata is present".

### 1.4 Why existing data cannot resolve it

- **The validation side is already consumed.** The 1,128 valid images have been
  used for model selection (training-time validation) and reporting
  (post-training ONNX CPU re-validation metrics: precision 0.937310, recall
  0.810829, mAP@0.5 0.897776, mAP@0.5:0.95 0.687726 on 1,128 images, from
  `models/YOLO11/deployment/yolo11n_v1_deployment/metrics_summary.json`,
  SHA-256 `57ba3ccb…cd615`), threshold choice
  (confidence 0.426, IoU 0.7 in `configs/detector_config.yaml:49-50`), smoke
  folds (`experiments/phase_3b/results/phase_3b2b3_smoke_eval_fold1.json`,
  `..._fold5.json`), and the 100-frame replay
  (`reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`), whose frames all come from
  `datasetfootage`, a valid-side group. `model_config.json` records
  `independent_test_set: false`. A set used this way is a development
  validation set; relabelling it "test" would silently reinterpret the
  acceptance criterion.
- **A third partition cannot be made from five groups.** Holding out one group
  as test leaves four for train+valid, and either
  `boots-powerup` becomes untrainable (it exists only in `subwayedtied`) or
  `jump-electric` / `jump-hedge` / `jump-trash` / `ledge` /
  `undercover-barrier` lose all validation support. The curation report
  tabulates this class-by-class (`reports/PHASE_3B1_DATASET_CURATION.md`,
  LOGO folds). Splitting inside groups reintroduces the 554 adjacent-frame
  crossings and the 296 duplicate-ID pairs.
- **No resampling or relabelling helps.** The deficiency is recording
  diversity and test-use history, not image count. The dataset already exceeds
  the pilot's 1,000-frame count (2,316 curated images), so adding more frames
  from the same six recordings adds no independence.

### 1.5 Verdict

**P3-T5 = BLOCKED.** The requirement is not "a held-out folder exists"; it is
a frozen test split at the recording-session unit. No such split exists, none
can be constructed from the five groups without breaking class coverage or
group atomicity, and the existing validation side has been used for model
selection. Existing data cannot resolve this blocker. T5-specific restriction
honoured: the validation split is not called an independent test split
anywhere in this report.

---

## 2. P3-T6 verdict — PARTIAL

### 2.1 Original requirement

- Metrics: "Per-class precision/recall, mAP@0.5, classification accuracy and
  confusion matrix, localisation IoU and centre error, player-lane accuracy,
  jump/roll accuracy where visible, normalised distance error and monotonicity,
  schema validity, p50/p95 latency, throughput, failure taxonomy"
  (`docs/PHASE_3_ROADMAP.md:190-193`).
- Gates: "Lane accuracy ≥ 0.95; per-class precision/recall ≥ 0.85; mAP@0.5
  ≥ 0.75; classification ≥ 0.85; median IoU ≥ 0.5; centre error ≤ 5% of
  diagonal; distance MAE ≤ 0.10 with ρ ≥ 0.8; 100% schema validity; p95
  latency ≤ 50 ms at 640×360 CPU if achievable, otherwise report the measured
  value" (`docs/PHASE_3_ROADMAP.md:201-205`; expanded in
  `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:287-301`).
- Ground truth required: "player lane and jump/roll state"; per object
  "category, bounding box, lane, distance bin or normalised distance proxy";
  "Distance labels are **not metres**… Physical distance requires a calibrated
  camera model and known object geometry, neither of which exists yet"
  (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:242-255`).

T6 is a bundle of independent requirements. Some are supported by existing
evidence; some are not. Hence the mixed verdict.

### 2.2 What exists, per label type

| Label type | Annotated count in v15 | Status |
|---|---:|---|
| Player identity / bounding box / lane | **0** | absent |
| Lane / rail annotations | **0** | absent |
| Player action (jump / roll) | **0** | absent |
| Calibrated or ordinal distance | **0** | absent |
| Object bounding boxes, 14 classes | 8,666 | present |

Supporting facts:

- **Player.** The 14-class vocabulary contains no player class
  (`.../data.yaml` → `names`). `configs/perception_config.yaml:11` states
  "v15 has no player class and no coin class"; line 67 sets
  `player_class_ids: []`. `ClassRole.PLAYER` exists in
  `perception/config.py:32` but is never assigned. `perception/scene.py:142-143`
  (`player_objects`) therefore always returns empty. The adapter substitutes
  `Lane.CENTER` (`perception/game_state_adapter.py:228`) and appends
  `player.lane` (`:229`), `player.speed`, `player.jumping`, `player.rolling`
  (`:245`) to an `estimated` list. These are declared defaults, not labels.
- **Lane.** No lane or rail annotation exists. `perception/lanes.py:62`
  (`LaneAssigner`) assigns lanes by geometric band overlap with three equal
  boundaries `[0, 0.3333, 0.6667, 1.0]`, `min_overlap 0.15`, `majority 0.75`
  (`configs/perception_config.yaml:34-42`), and "is never forced into a lane"
  (`perception/lanes.py:5`). The feasibility report classifies obstacle-lane
  agreement as "Yes, but weak — same geometry on both sides; not independent
  lane truth" and lane assignment accuracy as "**No** — requires new
  annotation work" (`reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:551-553`).
- **Action.** `jump-*` and `roll-*` are obstacle class names, not player
  actions (`reports/PHASE_3B1_DATASET_CURATION.md` role table §6.3). The
  feasibility report marks "Speed / jump / roll" as "**No** … Not observable
  from one frame" (`reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:561`).
- **Distance.** The configured mode is `bottom_edge_proxy`: 0 at the viewport
  bottom (near), 1 at `horizon_fraction 0.15` (far)
  (`configs/perception_config.yaml:44-48`; `perception/config.py:203-224`).
  The docstring says "It is not a metric distance"
  (`perception/config.py:208`), and the config comment says "Not a metric or
  in-game distance" (`configs/perception_config.yaml:46`). The feasibility
  report calls distance-proxy error "Box-bottom accuracy, not game or metric
  distance" (`reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:554`). No camera
  model or known object geometry exists. Per the T6 restriction, bounding-box
  size is **not** used here to claim calibrated distance.

### 2.3 What exists, per metric

| Metric | Implementation | Measured evidence | Status |
|---|---|---|---|
| Per-class precision / recall | `perception/evaluation.py:251` (`ClassMetrics`), `:545` (`evaluate_detections`) | ONNX re-validation macro P 0.937310 / R 0.810829 on 1,128 validation images (`metrics_summary.json`); not re-measured independently | **Available with limitation** |
| mAP@0.5 / mAP@0.5:0.95 | same harness | 0.897776 / 0.687726, same evaluation and split | **Available with limitation** |
| Confusion matrix (class-aware, with background) | `perception/evaluation.py:345` (`_taxonomies`); 13 evaluation tests | Harness only; not reported per class in a final table | **Available with limitation** |
| Classification accuracy (scalar) | Derivable from the class-aware confusion matrix | Not reported as a scalar; gate ≥ 0.85 untested | **Computable, not yet computed** |
| Localisation IoU | IoU matching inside `evaluate_detections`; AP integrates IoU | mAP@0.5:0.95 reported | **Partial** |
| Median IoU | Not reported as a statistic | — | **Computable, not yet computed** |
| Centre error | **Not implemented** | — | **Computable from existing GT boxes; no new labels needed** |
| Player-lane accuracy | Not implementable: no player, no lane labels | — | **BLOCKED** |
| Jump/roll accuracy | Not implementable: no action labels | — | **BLOCKED** |
| Distance MAE / monotonicity ρ | Proxy error computable; calibrated distance and annotated ordering absent | — | **BLOCKED** for the gate |
| Schema validity | `GameStateAdapter` validation | 16/16 scripted integration checks; 12/12 replay checks (`reports/PHASE_3B_3C_FINAL_VERIFICATION.md:42,109`; `experiments/phase_3c/results/p3_final_phase3_audit.md:61`) | **COMPLETE** |
| p50/p95 latency | `perception/evaluation.py:756` (`summarize_latency`) | p95 153.463 ms at 606×1050 (`reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md:250`) | **COMPLETE WITH LIMITATIONS** (not at 640×360, so the ≤ 50 ms "if achievable" clause resolves to reporting the measured value) |
| Throughput | derivable from latency | — | **Partial** |
| Failure taxonomy | `_taxonomies` FP/FN categories, class-aware | Harness only | **Partial** |
| Independent test metrics | — | — | **BLOCKED** (same root cause as T5) |

Important limitation on the measured detection numbers: they are the
**post-training ONNX CPU re-validation metrics**, imported via
`models/YOLO11/deployment/yolo11n_v1_deployment/metrics_summary.json`
(SHA-256 `57ba3ccb…cd615`). The integration report states they were "not
re-measured by this phase"
(`reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:50`), and the stored
evaluation result remains `status: blocked`
(`experiments/phase_3b/results/detector_evaluation.json`). They are not
independent test performance and are not presented as such.

### 2.4 What is missing

1. Player annotations (box and/or fixed-camera lane) — blocks player-lane
   accuracy and the ≥ 0.95 gate.
2. Human-verified lane labels — blocks lane-assignment accuracy (weak
   geometric agreement is the only available proxy).
3. Action labels (jump / roll per frame) — blocks jump/roll accuracy.
4. Annotated distance bins or a validated calibration with known object
   geometry — blocks distance MAE ≤ 0.10 and monotonicity ρ ≥ 0.8.
5. A frozen test split — blocks the independent-evaluation component shared
   with T5.
6. Implementation-only gaps (no new data required): centre-error statistic,
   median-IoU statistic, scalar classification accuracy, distance-proxy error
   on GT boxes. These are code/reporting work, not evidence gaps.

### 2.5 Verdict

**P3-T6 = PARTIAL.** Detection and localisation metrics are implemented and
partly measured (validation-run only); schema validity and latency are
measured; the classification scalar, median IoU and centre error are
computable from existing ground truth. Player lane, action and calibrated
distance cannot be evaluated from any existing annotation and are not
derivable without new annotation; box geometry is explicitly not a permitted
substitute in this audit.

---

## 3. Dataset and annotation inventory

### 3.1 Two unrelated dataset families

| Family | Location | Content | Relevant to T5/T6? |
|---|---|---|---|
| FlyWire/FAFB connectome audit | `datasets/raw`, `datasets/processed`, `datasets/manifest.json`, `datasets/README.md` | v783 audit: 15 datasets, 139,255 neurons, directed edges, no self-connections | No — no game frames or perception labels |
| Subway Surfers game frames | `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8/`; derived export under `datasets/exports/phase_3b2b1_yolo11n/` | 2,328 images, 2,328 label files, 14 classes, 8,666 boxes | Yes — the sole perception dataset |

`datasets/manifest.json` does not describe the game dataset; the game
dataset's provenance is carried by the v15 export READMEs and the derived
export provenance files.

### 3.2 v15 export contents

| Item | Value | Source |
|---|---|---|
| Format | Roboflow YOLOv8 detection export, version 15, "added" | `README.roboflow.txt`, `data.yaml` |
| Export date | 2024-05-05 06:32 GMT | `README.roboflow.txt` |
| Licence | CC BY 4.0 (as declared by Roboflow) | `data.yaml` → `roboflow.license` |
| Images | 2,328 JPEG, all 606 × 1050 | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` → `images` |
| Label files | 2,328 (12 empty) | same |
| Boxes | 8,666 | same |
| Preprocessing | auto-orient only | `README.dataset.txt` |
| Augmentation | none | `README.dataset.txt` |
| Declared splits | train, valid, test | `data.yaml` |
| Actual splits | train 1,825 / valid 503; no test directory | directory listing; `dataset.splits_present` |

### 3.3 Classes and support

Class order and totals (from `data.yaml` → `names` and the label files):

| id | class | train | valid | total |
|---:|---|---:|---:|---:|
| 0 | boots-powerup | 24 | 0 | 24 |
| 1 | boxtrain | 625 | 749 | 1,374 |
| 2 | jump-barrier | 254 | 163 | 417 |
| 3 | jump-electric | 14 | 0 | 14 |
| 4 | jump-hedge | 18 | 26 | 44 |
| 5 | jump-roll-barrier | 407 | 356 | 763 |
| 6 | jump-trash | 34 | 62 | 96 |
| 7 | ledge | 87 | 48 | 135 |
| 8 | pogstick-powerup | 53 | 65 | 118 |
| 9 | ramp | 606 | 617 | 1,223 |
| 10 | roll-barrier | 147 | 162 | 309 |
| 11 | train | 1,617 | 1,174 | 2,791 |
| 12 | undercover-barrier | 196 | 19 | 215 |
| 13 | wall | 622 | 521 | 1,143 |
| | **total** | **4,704** | **3,962** | **8,666** |

Per-split counts above are computed by this audit from the derived export's
`split_manifest.json` entries and labels; they match the manifest totals
(1,188 train images / 1,128 valid images). `boots-powerup` and
`jump-electric` have zero validation boxes; `undercover-barrier` (19),
`jump-hedge` (26), `ledge` (48), `jump-trash` (62) and `pogstick-powerup` (65)
have weak validation support.

### 3.4 Group structure

| Group | Images | Character |
|---|---:|---|
| datasetfootage | 504 | contiguous frame IDs |
| subwayavitomp4 | 501 | sparse, 304 runs, longest run 5 |
| subwayedited2 | 392 | contiguous |
| subwayedtied | 304 | contiguous |
| subwayy1_1 | 627 (331 IDs) | two recordings colliding on 296 IDs |

Source: `reports/PHASE_3B1_DATASET_CURATION.md` §3, `reports/PHASE_3B02_V15_DATASET_AUDIT.json`
→ `sequence.frame_ranges_by_sequence`. Group identity is inferred from
filenames; no capture metadata exists.

### 3.5 Derived artifacts in use

| Artifact | Path | SHA-256 (recomputed in this audit) |
|---|---|---|
| Curated split manifest | `reports/PHASE_3B1_SPLIT_MANIFEST.json` | `ff3f91192e59…aa357d` |
| v15 raw audit | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` | `2050b6893592…0d1b4` |
| Derived export manifest | `datasets/exports/phase_3b2b1_yolo11n/provenance/split_manifest.json` | `7f288906e504…e3739` |
| Derived export summary | `datasets/exports/phase_3b2b1_yolo11n/provenance/dataset_summary.json` | `173ddca8c1fb…a9891` |
| Detector evaluation (blocked) | `experiments/phase_3b/results/detector_evaluation.json` | `96b0176ac199…bbfacd` |
| Evaluation harness | `perception/evaluation.py` | `88103c5a7d23…d8a36f` |
| Detector config | `configs/detector_config.yaml` | `f31add2ad45f…3c5aa0` |
| Perception config | `configs/perception_config.yaml` | `bb51060575b1…ee01c` |
| GameState adapter | `perception/game_state_adapter.py` | `e59fa0bb3666…735d67` |
| ONNX re-validation metrics | `models/YOLO11/deployment/yolo11n_v1_deployment/metrics_summary.json` | `57ba3ccb3fe7…cd615` |
| ONNX weights | `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | `e6ad18f90cd0…b6aa77` |
| Phase 3B evaluation protocol | `reports/PHASE_3B_EVALUATION.md` | `13daf389784d…fc1b6` |

The derived export is a copy of the v15 files in the curated grouping; the
original Roboflow tree is unmodified.

---

## 4. Exact file paths and source references

### 4.1 Requirements and specifications

- `docs/PHASE_3_ROADMAP.md:185-205` — 3B protocol, metrics, acceptance,
  provisional gates.
- `docs/PHASE_3_ROADMAP.md:220-242` — measured outcomes; records "no
  independent test split exists".
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:242-255` — ground-truth schema;
  distance is not metres; no camera model or geometry.
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:257-267` — session-level splits;
  pilot ≥ 10 sessions; full 20–40 sessions; double annotation.
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:269-285` — metric definitions.
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:287-301` — thresholds.
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:339-358` — eight acceptance
  criteria.

### 4.2 Dataset artifacts

- `datasets/external/subway surfers/roboflow_v15_yolov8/subway surfers object dataset.v15-added.yolov8/data.yaml`
- `.../README.dataset.txt`, `.../README.roboflow.txt`
- `reports/PHASE_3B1_SPLIT_MANIFEST.json`
- `reports/PHASE_3B1_DATASET_CURATION.md` / `.json`
- `reports/PHASE_3B02_V15_DATASET_AUDIT.md` / `.json`
- `datasets/exports/phase_3b2b1_yolo11n/provenance/{dataset_summary.json,split_manifest.json,SHA256SUMS.txt}`

### 4.3 Implementation

- `perception/evaluation.py:251,287,345,506,545,756` — metrics and taxonomy.
- `perception/config.py:26,32,157,203-224` — roles, lane and distance config.
- `configs/perception_config.yaml:11,34-48,50-67` — lanes, distance proxy,
  `player_class_ids: []`.
- `perception/lanes.py:5,62,77` — geometric lane assignment.
- `perception/game_state_adapter.py:134,195,224-229,245,345` — distance and
  estimated-player fields.
- `perception/scene.py:142-143` — `player_objects`.
- `configs/detector_config.yaml:24,49-50` — model hash and thresholds.
- `experiments/phase_3b/results/detector_evaluation.json` — blocked status.
- `models/YOLO11/deployment/yolo11n_v1_deployment/{metrics_summary.json,model_config.json,SHA256SUMS.json}`.

### 4.4 Prior audits (unchanged, cited for continuity)

- `experiments/phase_3c/results/p3_t5_t11_acceptance_audit.md:30-31,41-73`
- `experiments/phase_3c/results/p3_final_phase3_audit.md:55-56,292-305`
- `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:408-436,542-562,777`
- `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:50`
- `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md:250`

---

## 5. Evidence coverage tables

### 5.1 T5 coverage

| Requirement element | Evidence present | Evidence missing | Status |
|---|---|---|---|
| Deterministic processing of a frozen test split | Determinism demonstrated on validation/replay (bit-identical replays; 12/12 checks) | A frozen test split | BLOCKED |
| Test split at recording-session unit | Group-atomic curated split (0 cross-split groups) | A third partition; ≥ 10 sessions | BLOCKED |
| Measured detection errors | Validation-run P/R/mAP | Independent test measurement | BLOCKED |
| Measured classification errors | Confusion matrix implemented | Independent test measurement; scalar accuracy | BLOCKED |
| Measured localisation errors | IoU/AP implemented | Centre error statistic; independent test measurement | PARTIAL |
| Measured distance errors | Box-bottom proxy available | Calibrated/annotated distance; independent test | BLOCKED |
| Frozen-test determinism evidence | none | all | BLOCKED |

### 5.2 T6 per-label-type coverage

| Requirement | Annotation source | Count | Units / coordinate system | Human / inferred / predicted | Coverage | Status |
|---|---|---:|---|---|---|---|
| Player identity & location | none | 0 | — | adapter default (`Lane.CENTER`), flagged `estimated` | 0 of 2,316 curated images | BLOCKED |
| Lane identity (player or object) | none | 0 | lane ∈ {left, center, right} via geometric bands | geometric inference (`LaneAssigner`) | 0 human-verified | BLOCKED |
| Player action (jump/roll) | none | 0 | — | — | 0 | BLOCKED |
| Calibrated distance | none | 0 | normalised proxy 0..1, **not metric** | geometry proxy | 0 annotated | BLOCKED |
| Obstacle boxes | Roboflow v15 | 8,666 | YOLO cx/cy/w/h, normalised | human-annotated (per dataset declaration) | 2,316 curated images | COMPLETE WITH LIMITATIONS |

Double annotation: the design requires 10–20% double annotation and
inter-annotator agreement (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:267`).
No inter-annotator record exists in the repository for v15. This is a further
T6 limitation for any accuracy claim, though it does not block metric
computation against the existing single-annotator labels.

### 5.3 T6 metric coverage summary

| Metric | Gate | Computable now? | Measured? | Blocking evidence |
|---|---|---|---|---|
| Per-class P/R | ≥ 0.85 | yes | validation-run only | independent test |
| mAP@0.5 | ≥ 0.75 | yes | 0.897776 (validation) | independent test |
| Classification accuracy | ≥ 0.85 | yes (from confusion) | no | reporting step |
| Median IoU | ≥ 0.5 | yes | no | reporting step |
| Centre error | ≤ 5% diagonal | yes (GT boxes exist) | no | metric implementation |
| Player-lane accuracy | ≥ 0.95 | no | no | player + lane labels |
| Jump/roll accuracy | reported | no | no | action labels |
| Distance MAE | ≤ 0.10 | no (gate sense) | no | annotated/calibrated distance |
| Distance monotonicity ρ | ≥ 0.8 | no | no | annotated ordering |
| Schema validity | 100% | yes | yes (16/16, 12/12) | — |
| p95 latency | ≤ 50 ms if achievable | yes | 153.463 ms | hardware/resolution; clause permits reporting |
| Failure taxonomy | reported | partially | partially | class-aware taxonomy implemented; not summarized in a final table |

### 5.4 Traceability: original requirement → available evidence → missing evidence → status

| # | Original requirement | Available evidence | Missing evidence | Acceptance status |
|---:|---|---|---|---|
| 1 | Frozen test split, session-level | Group-atomic curated 2-way split; 0 exact duplicates; 5 groups/≈6 recordings; 5 LOGO folds | Third partition; ≥ 10 sessions; unused-for-selection history | **BLOCKED** |
| 2 | Deterministic test-split processing | Deterministic replay on validation frames | Test-split data | **BLOCKED** |
| 3 | Detection P/R, mAP | Validation-run metrics; harness with 13 tests | Independent test measurement | **PARTIAL** |
| 4 | Classification accuracy + confusion matrix | Class-aware confusion matrix implemented | Scalar accuracy; test measurement | **PARTIAL** (computable) |
| 5 | Localisation IoU + centre error | IoU matching, AP; GT boxes | Median IoU statistic; centre-error implementation; test measurement | **PARTIAL** (computable) |
| 6 | Player-lane accuracy ≥ 0.95 | Adapter defaults player to CENTER, flags `estimated` | Player box/lane labels | **BLOCKED** |
| 7 | Jump/roll accuracy | — | Action labels | **BLOCKED** |
| 8 | Normalised distance MAE ≤ 0.10, ρ ≥ 0.8 | Box-bottom proxy (not metric) | Annotated distance bins or validated calibration | **BLOCKED** |
| 9 | 100% schema validity | 16/16 scripted, 12/12 replay | — | **COMPLETE WITH LIMITATIONS** |
| 10 | p95 latency ≤ 50 ms at 640×360 if achievable | p95 153.463 ms at 606×1050 | 640×360 measurement (clause permits reporting measured value) | **COMPLETE WITH LIMITATIONS** |
| 11 | Throughput | Derivable from latency | Explicit reporting | **PARTIAL** |
| 12 | Failure taxonomy | FP/FN class-aware taxonomy implemented | Final summarized table | **PARTIAL** |
| 13 | Inter-annotator agreement (10–20% double annotation) | — | Double-annotation record | **BLOCKED** |

---

## 6. Missing requirements

Consolidated, deduplicated list:

1. **Independent test recordings.** New capture sessions, disjoint from the
   five groups, at the pilot minimum of ten sessions / ~1,000 annotated
   frames, or the full-study 20–40 sessions.
2. **Test-split freeze and non-use discipline.** A written declaration that the
   frozen split is not used for training, thresholding, fold inspection or
   replay, with a hash manifest.
3. **Player annotations.** Bounding box per frame, or a fixed-camera position
   assumption recorded as such. Required for player-lane accuracy.
4. **Human lane labels.** Left / centre / right per frame, human-verified.
5. **Action labels.** Jump / roll / neither per frame, with an explicit
   `unknown` class.
6. **Distance supervision.** Either calibrated geometry (camera model, known
   object sizes, calibration protocol) or ordinal distance bins annotated per
   object, consistently defined.
7. **Inter-annotator agreement.** 10–20% double annotation with box IoU and
   category/lane agreement.
8. **Metric implementations (no new data).** Centre error, median IoU, scalar
   classification accuracy, distance-proxy MAE/bias on GT boxes, summarized
   failure taxonomy.
9. **640×360 latency measurement** if the ≤ 50 ms gate is to be assessed at
   that resolution.

Items 8 and 9 are engineering work against existing data. Items 1–7 require new
capture or annotation and cannot be manufactured from the current repository.

---

## 7. Can existing data resolve each blocker?

| Blocker | Resolvable with existing data? | Reason |
|---|---|---|
| No independent test split (T5) | **No** | Five groups; one contains two recordings; a third partition breaks class coverage or group atomicity; validation used for selection |
| Validation called "test" | **No (and not permitted)** | Would silently reinterpret the acceptance criterion |
| Detection metrics (T6) | **Yes, for validation-side reporting** | Harness and GT exist; not independent |
| Classification accuracy | **Yes** | Derivable from the existing confusion matrix |
| Median IoU / centre error | **Yes** | Existing GT boxes; implementation work only |
| Player-lane accuracy | **No** | Zero player and zero lane annotations |
| Jump/roll accuracy | **No** | Zero action annotations |
| Calibrated distance MAE/ρ | **No** | Zero distance annotations; no camera model or geometry; box-size inference not permitted by this audit |
| Box-bottom proxy error | **Yes, as a proxy only** | GT boxes + horizon config exist; result measures box geometry, not distance |
| Schema validity | **Yes** | Already measured |
| Latency | **Yes** | Already measured at 606×1050; 640×360 not measured |
| Inter-annotator agreement | **No** | No double annotation exists |

---

## 8. Minimum legitimate next action for each incomplete requirement

"Minimum legitimate" means the smallest action that can satisfy the original
written requirement without changing it.

| Incomplete requirement | Minimum legitimate next action |
|---|---|
| T5 independent test split | Record new gameplay sessions, disjoint from all five existing groups, at ≥ 10 sessions and ≈ 1,000 frames for a pilot; label with the existing schema; freeze the test split by session; hash-manifest it; then run `experiments/phase_3b/evaluate_detector.py` unchanged against it. Re-dividing v15 cannot substitute. |
| T5 determinism on test data | Once the frozen split exists, run the existing deterministic replay twice and compare hashes, as already done on validation frames. |
| Player identity/location | New annotation pass adding a player box per frame, or a recorded fixed-camera assumption; then compute player-lane accuracy against human lane labels. |
| Lane identity | New human lane annotation pass (left/centre/right per frame). The geometric `LaneAssigner` remains a detection-conditioning aid, not lane truth. |
| Action labels | New per-frame annotation of jump / roll / neither (with `unknown`), or multi-frame sequence annotation; single frames cannot support this. |
| Calibrated distance | Either (a) define and annotate ordinal distance bins per object under a written protocol, or (b) build and validate a camera/geometry calibration. Bounding-box size alone is not sufficient under the current design text, and this audit does not authorise it as calibrated distance. |
| Distance MAE / monotonicity | After (a) or (b), compute against the annotated target; the existing box-bottom proxy can serve only as an uncalibrated sensitivity check, clearly labelled. |
| Classification accuracy, median IoU, centre error, proxy MAE, failure taxonomy | Implement/report against existing GT boxes and the existing harness; no new data. Must be labelled validation-side, not test. |
| Inter-annotator agreement | Double-annotate 10–20% of frames and record box IoU and category/lane agreement. |
| 640×360 latency | Measure the existing pipeline at 640×360 CPU and report p50/p95; the gate's fallback clause then applies. |

Not permitted as next actions: relabelling validation as test; deriving
calibrated distance from box size without an amended, validated protocol;
treating detector output as new ground truth; synthesising player, lane,
action or distance labels.

---

## 9. What this audit does not claim

- It does not claim the detector is accurate or inaccurate. The only numbers
  quoted are the post-training ONNX CPU re-validation metrics, explicitly marked
  as such.
- It does not claim the geometric lane assignment is wrong; it claims it is not
  a lane label.
- It does not claim box-bottom geometry is unrelated to distance; it claims it
  is not a calibrated or annotated distance and cannot satisfy the distance
  gate.
- It does not claim the v15 annotations are erroneous; it records that no
  inter-annotator evidence exists.
- It does not revise any acceptance criterion, threshold or protocol. The
  requirement texts quoted in §1.1 and §2.1 are the authoritative ones.
- It does not modify datasets, models, labels, configs, frozen P3-3C.5
  artifacts or the working tree beyond adding this report.

---

## 10. Conclusions

1. **P3-T5 is BLOCKED.** No frozen test split exists at the required
   recording-session unit, no third partition can be formed from the five
   filename groups without destroying class coverage or group atomicity, and
   the existing validation side has already been used for model selection. The
   blocker is a data-acquisition problem, not an analysis problem.
2. **P3-T6 is PARTIAL.** Detection, localisation and schema metrics are
   implemented, and several are measured on the validation side; three more
   (classification accuracy, median IoU, centre error) are computable from
   existing boxes with implementation work only. Player lane, action and
   calibrated distance are unsupported by any existing annotation and are not
   derivable from box geometry under the current protocol.
3. **Existing data cannot resolve either blocker.** The repository contains
   sufficient evidence to describe its own limits precisely, and insufficient
   evidence to close them.

Status: audit complete. No implementation performed. Stop here.
