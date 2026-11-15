# P3-T5 to P3-T11 — Phase 3 acceptance audit

Generated: 2026-11-14
Repository HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`)
Working-tree entries at audit time: 196

This audit covers the remaining Phase 3 acceptance gates in the order
requested by the Phase 3 completion programme. It does not change any
scientific assumption, connectome artifact, Phase 4–6 file or root README.
Criteria are quoted from `docs/PHASE_3_ROADMAP.md`,
`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` and the reports named under each
task. Where the original plan has no criterion, that is stated rather than
invented.

Status labels distinguish four different things:

- **Implemented**: code exists.
- **Tested**: automated tests exercise the code.
- **Experimentally validated**: an experiment produced evidence under the
  stated protocol.
- **Accepted**: the original acceptance criterion is met, not merely
  addressed.

A task is not called complete because code exists.

## 1. Acceptance matrix

| Task | Original criterion (abridged) | Implemented | Tested | Experimentally validated | Verdict |
|---|---|---|---|---|---|
| P3-T5 | Deterministic processing of the frozen **test** split; measured detection/classification/localisation/distance errors | Yes | Yes (harness) | No independent test split exists | **BLOCKED** |
| P3-T6 | Per-class P/R, mAP@0.5, classification, IoU, centre error, lane accuracy, distance MAE/monotonicity; gates in §4.3 | IoU/AP/confusion/latency only | Yes (13 evaluation tests) | Validation-run metrics only; no lane/centre/distance labels | **PARTIALLY COMPLETE** |
| P3-T7 | 3C decision rule 1–5 and 3C acceptance sentence | Yes (new) | Yes (10 new tests) | Yes, 23 conditions; **negative result** | **PARTIALLY COMPLETE** |
| P3-T8 | Deterministic replay and reproducibility hashes; CI is not a roadmap criterion | Yes | Yes | Yes (bit-identical replays) | **COMPLETE WITH LIMITATIONS** |
| P3-T9 | p95 ≤ 50 ms at 640×360 CPU if achievable, otherwise report the measured value | Yes | Yes | Yes (measured) | **COMPLETE WITH LIMITATIONS** |
| P3-T10 | No unsupported claim; defaults and provenance preserved | Yes | Partly | Yes (documented) | **COMPLETE WITH LIMITATIONS** |
| P3-T11 | Valid `GameState`, Phase 3A interface unchanged, adapter reports unrepresented objects; integration corrections | Yes | Yes | Yes | **COMPLETE WITH LIMITATIONS** |

Summary: 0 complete without limitation, 4 complete with limitations, 2
partially complete, 1 blocked.

## 2. P3-T5 — independent detector test set / held-out evaluation

**Criterion.** "Deterministic processing of the frozen test split; measured
detection/classification/localisation/distance errors" and the provisional
detector gates (`docs/PHASE_3_ROADMAP.md` §4.3). The roadmap already records
Phase 3B as "implemented; independent detector metrics blocked".

**Implementation.** The evaluation harness, grouped split tooling and ONNX
adapter exist. `perception/evaluation.py` implements greedy IoU matching,
per-class precision/recall/F1, AP@0.5, mAP@0.5:0.95, a background confusion
matrix, taxonomies, bootstrap intervals and latency summaries.

**Evidence.**
- `reports/PHASE_3B1_SPLIT_MANIFEST.json` (`ff3f9119…`): only `train` and
  `valid` splits; five filename groups; zero cross-split groups. There is no
  frozen independent test split.
- `experiments/phase_3b/results/detector_evaluation.json` (`96b0176a…`):
  `status: blocked`, empty `metrics`, `protocol.test_split: false`, and the
  stated limitation "There is no independent test split; these are held-out
  recordings, not an independent test set."
- Validation metrics in `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md`
  (precision 0.937310, recall 0.810829, mAP@0.5 0.897776, mAP@0.5:0.95
  0.687726 on 1,128 images) are **training-run** numbers. The smoke
  evaluations cover 2–3 images (`phase_3b2b3_smoke_eval_fold1.json`,
  `…fold5.json`) and say so.

**Why blocked.** The dataset contains five filename groups and no independent
test split; the manifest states that none can be formed. Producing one would
require new capture and annotation, or a decision to hold out a group and
retrain. Neither is scientific work that can be fabricated from existing data.
No independent detection-accuracy number is claimed.

## 3. P3-T6 — lane, IoU, centre and classification metrics

**Criterion.** Per-class precision/recall, mAP@0.5, classification accuracy and
confusion matrix, localisation IoU and centre error, player-lane accuracy,
jump/roll accuracy where visible, normalised distance error and monotonicity
(`docs/PHASE_3_ROADMAP.md` §4.3). Provisional gates: lane ≥ 0.95, per-class
P/R ≥ 0.85, mAP@0.5 ≥ 0.75, classification ≥ 0.85, median IoU ≥ 0.5, centre
error ≤ 5% diagonal, distance MAE ≤ 0.10 with ρ ≥ 0.8.

**Implemented and tested.**
- IoU, greedy matching, AP, mAP over the IoU sweep, per-class P/R/F1, a
  class-agnostic confusion matrix with background, failure taxonomy,
  bootstrap intervals, latency and memory helpers (`perception/evaluation.py`,
  `88103c5a…`).
- `tests/test_evaluation.py` covers matching, AP, mAP, confusion, taxonomies,
  bootstrap, latency and memory.

**Not implemented or not measurable.**
- No player-lane accuracy metric.
- No centre-error metric.
- No distance MAE or monotonicity metric.
- No gameplay-state classification accuracy (jump/roll) — the v15 dataset has
  no player or action labels.
- `reports/PHASE_3B_EVALUATION.md` (`13daf389…`) states explicitly that "mAP
  does not measure lane behaviour, distance accuracy, temporal stability".

**Why partially complete.** The detection metrics that can be computed have
implemented, tested code and validation-run values. The remaining roadmap
metrics require labels that do not exist in the dataset (player, lane, action,
calibrated distance), and an independent prediction set that does not exist.
The provisional gates cannot be evaluated. No value is reported for an
undefined metric.

## 4. P3-T7 — temporal controls and acceptance experiments

**Criterion.** `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.4:

1. no numerical, capacity or validation failure;
2. 3C.1 constant-sequence equivalence holds;
3. approach and retreat separate above the seed-to-seed spread in at least two
   of three mapping seeds;
4. at least one frame-rate comparison is quantified;
5. reversed or shuffled sequences produce a measurable difference, or the
   absence is reported as a negative result.

The roadmap acceptance sentence additionally requires static-equivalence,
onset/offset/persistence measurement, frame-rate quantification, unchanged
interfaces, all tests passing, sparse full graph only, and no reframing of
negative results.

**What existed before this work package.** The encoder, scheduler, tracking,
50-sequence synthetic calibration and two engineering replays. The design
document states: "Execution status (2026-11-13): none of the 3C.1–3C.9
conditions has been run." `configs/temporal_sensory.yaml` and an acceptance
runner did not exist.

**What was implemented.** Because the design fixes comparisons but not exact
stimuli, the sequences were pre-registered in `configs/temporal_sensory.yaml`
(`ef68efb1…`) before execution:
- 600.5 ms horizon, 50 ms frame interval, 200 pA (asserted equal to the sensory
  config), zero background and noise;
- mapping seeds `20261104`, `20261105`, `20261106`;
- 3C.1 constant distances 0.15/0.55/0.90;
- 3C.2 approach 0.90→0.15 vs retreat 0.15→0.90 at identical endpoints;
- 3C.3 entry at 100/200/300 ms; 3C.4 exit at 200/400 ms;
- 3C.7 the same trajectory sampled at 200/100/50 ms;
- 3C.9 no input, a fixed 13-frame shuffle, and a dropped frame;
- pre-registered d′ threshold 1.0 and cosine-distance threshold 0.01.

`experiments/phase_3c/temporal_acceptance.py` (`41f4b09e…`) executes 23
conditions over the sparse full connectome in 110.92 s and writes
`experiments/phase_3c/results/temporal_acceptance.json` (`4eda97fe…`) and
`…_report.md`. `tests/test_temporal_acceptance.py` (`7a101f14…`) adds 10
focused tests; all pass.

**Results.**

| Decision item | Result |
|---|---|
| 1. No failure | Pass — all runs completed, finite, within capacity |
| 2. 3C.1 static equivalence | **Pass** — max current difference 0.0 pA at all 1,201 steps and identical spike counts at all three distances (463/459/459) |
| 3. 3C.2 approach vs retreat | **Fail** — signed d′ = 0.0 in all three seeds; identical total spikes (460/460); seed spread 0.0 |
| 4. 3C.7 frame-rate | **Quantified** — current RMS difference 0.395 pA (200 ms) and 0.155 pA (100 ms) vs 50 ms; max 105.7/37.6 pA; spike-profile cosine distance 0.060/0.070; total spike ratio 1.002/1.004 |
| 5. 3C.9 controls | **Measurable difference** — no input 0 spikes; shuffled distance-profile cosine 0.0735; reversed 0.0145 |

Onset: first distance-population spike 28 ms after entry, median 35 ms across
three spiking neurons, zero pre-onset spikes, and the peak bin tracks the
entry time (250/350/450 ms). Exit: zero post-offset distance-population spikes
in both conditions; the scheduler selects the most recent frame, so an absent
frame replaces the present state immediately and persistence is zero by
construction, not a membrane after-discharge measurement.

**Conclusion.** Under the pre-registered d′ criterion, approach and retreat do
not separate. This is the negative result the design requires: at this
operating point the network response to a time-reversed distance trajectory is
the time reverse of the forward response, with identical spike totals and
identical binned mean/variance. The nearest-centroid accuracy of 1.0 is
descriptive of bin order, not evidence of a direction code, and is not
reframed as temporal coding. Frame-rate changes the scheduled current but not
the aggregate spike profile materially; all tested intervals exceed the 20 ms
membrane constant.

**Limitations and unexecuted work.**
- Synthetic `GameState` input; no detector or tracker is in this experiment.
- The distance population is the shipped 12 neurons, not the 4-neuron
  calibrated point (P3-T4).
- Only the mapping seed varies; no biological or runtime noise.
- The d′ threshold is a new operationalisation because the design gives no
  numeric cut-off.
- Bins are not independent samples.
- The scheduler is sample-and-hold plus decaying pulses; the design's T1
  crossfade and T2 smoothing variants are not implemented, so 3C.1 is an
  equivalence test of the implemented path only.
- **3C.5 (lane ordering), 3C.6 (jump/roll intervals) and 3C.8 (T1/T2/T3
  ablation) were not executed.** They characterize the encoder rather than the
  decision rule and remain open.
- The 3C milestone cannot be declared accepted: criterion 3 fails and three
  conditions are unrun.

## 5. P3-T8 — replay determinism and CI

**Criterion.** The roadmap requires deterministic processing and
reproducibility hashes. It contains **no CI requirement**; no CI system is
specified anywhere in Phase 3 documentation.

**Evidence.**
- `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`
  (`4a4d6ea6…`): two replays are identical; detections SHA-256
  `8719fb3f…e9b` twice; temporal SHA-256 `2a857471…166` twice; scheduler and
  spike-count hashes identical; 15,654,631 spikes both times; model SHA-256
  `e6ad18f9…a77` both times; 12/12 checks pass.
- `experiments/phase_3c/results/integration.json`: scheduler and simulation
  determinism checks pass; protected hashes match; 16/16 checks pass.
- The three connectome conditions of P3-T2 and the 15 conditions of P3-T3 are
  hash-verified by their preserved runners and reports.

**Not done.** No `.github/workflows`, GitLab CI, Jenkins or other pipeline
exists. If the programme intended CI as a new requirement, it is not
implemented; it was not an original Phase 3 acceptance criterion, so this
audit does not fail T8 for its absence. Determinism is demonstrated directly,
not by a CI gate.

## 6. P3-T9 — p95 latency

**Criterion.** "p95 latency ≤ 50 ms at 640×360 CPU if achievable, otherwise
report the measured value" (`docs/PHASE_3_ROADMAP.md` §4.3).

**Measured.**
- 100 detector calls, CPU, image size 606×1050: full detector call p95
  **153.463 ms** (mean 138.087 ms), ONNX `session.run` p95 138.764 ms,
  preprocessing p95 13.367 ms, decode/NMS/inversion p95 3.030 ms.
- Source: `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md` (`1d280615…`) §4.

The ≤ 50 ms gate is **not met**. The criterion explicitly permits reporting
the measured value when the target is not achievable. The measurement is at
606×1050, not 640×360, so it is not a direct test of the stated gate;
downscaling would change both accuracy and latency and was not performed.

## 7. P3-T10 — unsupported and defaulted feature claims

**Criterion.** No unsupported player/coin claim; preserve feature provenance.
The roadmap requires that perception not make real-time or biological claims
without measured latency and validation, and that unrepresented objects be
documented.

**Evidence.**
- `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md` final `GameState` table labels
  `player_lane` and `player_speed` as neutral `PlayerState` defaults,
  `jumping`/`rolling` as unavailable, and coins as unavailable, not observed
  absent.
- The same report states that the defaults were actually scheduled:
  `player_lane` contributed a constant 800 pA and `player_speed`
  1,096.361 pA, so the simulated current "is not purely visual". Coin channels
  contributed zero.
- `configs/detector_config.yaml` (`f31add2a…`) describes confidence 0.426 and
  NMS IoU 0.7 as "starting points, not calibrated" thresholds.
- `perception/game_state_adapter.py` (`e59fa0bb…`) records
  `estimated_fields`, `unrepresented` objects and `warnings` instead of
  dropping them silently.

**Verdict.** Claims are correctly qualified and provenance is preserved.
Limitation: the neural input includes constant non-visual player defaults, so
the replay is not a purely visual drive. No unsupported feature is reported as
observed.

## 8. P3-T11 — adapter and integration corrections

**Criterion.** Valid `GameState` output; existing Phase 3A encoders accept it
unchanged; perception testable without the simulator and vice versa; adapter
corrections completed or explicitly outstanding.

**Evidence.**
- Boundary tolerance implemented and documented: accept ≤1 px overflow with
  clipping, reject beyond; every detection keeps `raw_box_pixels`,
  `clipped_box_pixels`, `clip_distance_pixels`
  (`reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md`, `daf9bb46…`).
- The adapter reports unrepresented objects and estimated fields; the 3B2C
  replay records 0–6 unrepresented tracks per frame (mean 2.61) because the
  schema holds one obstacle, one train and one coin.
- Integration checks pass (16/16 scripted; 12/12 replay).
- The 3B2B3 report records four decisions still required: (1) calibrate or
  accept the confidence/NMS thresholds; (2) choose the production bounds
  policy for sub-pixel overflow; (3) run the full validation evaluation only
  after those decisions, describing it as grouped validation; (4) keep replay
  small and sequential until latency/memory are understood.

**Verdict.** Adapter corrections are implemented and tested. Two scientific
decisions (thresholds and bounds policy) remain open and are not made here.

## 9. Cross-cutting limitations

- No independent test split exists, so no detection or classification number
  in Phase 3 is independent-test performance.
- The dataset has no player, coin, lane, action or calibrated-distance labels.
- The 12-neuron obstacle-distance population is not the 4-neuron calibrated
  point; P3-T4 documents the discrepancy and recommends retaining 12 for the
  frozen evidence chain without calling it calibrated.
- All neural results are model output on synthetic or scripted input, not
  measured biological activity.
- No motor or action selection is evaluated.

## 10. New artifacts in this work package

| Path | SHA-256 |
|---|---|
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` |
| `experiments/phase_3c/temporal_acceptance.py` | `41f4b09effbed172502bcd06c8abc32f879b2a0168ced20bf0ec09838adc0543` |
| `tests/test_temporal_acceptance.py` | `7a101f14f1c77144353854059eda6dcd24c6597ec55eea4d987bfdbcce722796` |
| `experiments/phase_3c/results/temporal_acceptance.json` | `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc` |
| `experiments/phase_3c/results/temporal_acceptance_report.md` | `610fc44e2b2ff02f66f7b96451b34916ad44ed95fe5ffd9304117ffb4824942c` |
| `experiments/phase_3c/results/temporal_acceptance.sidecar.json` | `b893746c2bc790b575e9073831bc2f03b54145c92f07ceca17742ed94c6f7788` |

## 11. Decisions needed

1. **Independent evaluation set (T5/T6).** Capture and annotate new recordings
   from unseen sessions, or designate a held-out group and retrain. Until
   then, no independent detector metric can exist.
2. **Metric labels (T6).** Player/lane/action labels and a calibrated distance
   reference do not exist. Either add them or formally drop the corresponding
   gates; do not substitute geometric proxies for accuracy.
3. **3C residual (T7).** Decide whether to execute 3C.5/3C.6/3C.8 and whether
   to investigate why approach/retreat produce identical spike totals at this
   operating point (e.g. the uncalibrated 12-neuron population or the absence
   of adaptation). The current result is negative, not a coding claim.
4. **Detector thresholds and bounds policy (T11).** Calibrate or explicitly
   accept the confidence/NMS values and the ≤1 px tolerance before any
   performance evaluation.
