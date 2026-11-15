# Phase 3 — final independent audit

Generated: 2026-11-14
Repository HEAD: `62a64309cadc0db7353c856607cee5369993bd65`
Branch: `main`
Working tree before this report was written: 201 entries — 21 tracked
modifications (all pre-existing in this session), 180 untracked, 0 staged.
After writing this report: 202 entries. Root `README.md` is unmodified.

This audit covers the Phase 3 completion programme tasks P3-T2 through P3-T12
and the Phase 3 milestone gates. It does not start Phase 4, 5 or 6 work, does
not modify any Phase 4–6 file, and does not stage, commit or push. Criteria are
quoted from `docs/PHASE_3_ROADMAP.md`,
`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md`,
`docs/PHASE_3C_CAUSAL_CONTROL_PROTOCOL.md`,
`docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md` and the reports named
below. No criterion is invented. P3-T1 has no task definition, protocol or
artifact anywhere in the repository, so it is not audited and is not counted.

Status labels distinguish four independent things:

- **Implemented** — code exists.
- **Tested** — automated tests exercise the code.
- **Experimentally validated** — an experiment produced evidence under the
  stated protocol.
- **Accepted** — the original criterion is met, not merely addressed.

A task is not called complete because code exists.

## 1. Integrity verification

| Check | Result |
|---|---|
| Root `README.md` SHA-256 | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` — matches every protected-hash block; file unmodified in Git |
| Connectome `datasets/processed/connectome.npz` SHA-256 | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` — unchanged |
| P3-T2 artifact | `p3_t2_full.json` `dd27c5d2…70afd`, verdict `VALID`, 0 triggered invalidations, archive gate evaluated; C3 spike-count hash equals the archived digest |
| P3-T3 raw artifact | `p3_t3_ablation.json` `6fbe3263…b8956`, verdict `VALID`, 0 triggered invalidations; hash equals the hash recorded by P3-T3.1 before and after generation |
| P3-T3.1 consistency | Regenerating the classification from the current P3-T3 payload produced a byte-identical payload after removing timestamps; counts `none` 1 / `sparse` 1 / `population_scale` 13; source hash `6fbe3263…` |
| Phase 3C sidecars | 13/13 reference an existing artifact; `config_sha256` and `cache_sha256` recomputed |
| Embedded hash blocks | 113/113 expected-vs-actual comparisons pass across P3-T2, P3-T3, P3-T12, P3-T4 and P3-T7 payloads (README, connectome, sensory/simulation/neuron configs, experiment configs, calibration inputs) |
| Cache chain | `p3_t2_visual_frames.json` SHA-256 `9f950472…b82154` = manifest = P3-T2 sidecar; `frames_digest` `2a857471…29166` = P3-T2 archived temporal digest = 3B2C replay temporal digest; scheduler digest `1c3ab12d…08840` = archived scheduler = 3B2C replay |
| P3-T12 equivalence | Full-duration C3 reproduces the archived P3-T2 C3 exactly: 9/9 equivalence checks pass, subprocess repeats identical, prefix gate identical |
| Report hash references | Every 64-hex string quoted in the P3-T2/T3.1/T12/T4/T7 reports resolves to its named artifact; no dangling hash |
| Focused tests | `tests/test_ignition_reporting.py`, `test_network_characterization.py`, `test_p3_t4_calibration.py`, `test_temporal_acceptance.py`, `test_causal_control.py`, `test_feature_ablation.py` — 75 passed in 22.32 s |
| Full test suite | **823 passed, 0 failed** in 73.86 s |

## 2. Acceptance matrix

| Task | Original acceptance criterion (abridged) | Implemented | Tested | Experimentally validated | Verdict |
|---|---|---|---|---|---|
| P3-T2 | Four same-graph conditions (C0–C3) at 3,300.5 ms; 11 invalidation rules; archive gate; subprocess repeats | Yes | Yes | Yes — `VALID`, 0 invalidations | **COMPLETE WITH LIMITATIONS** |
| P3-T3 | 15-condition one-factor feature ablation on the frozen cache; archive gate; invalidations; contrasts vs baseline | Yes | Yes | Yes — `VALID`, 0 invalidations | **COMPLETE WITH LIMITATIONS** |
| P3-T3.1 | Additive reclassification of ignition; raw payload unmodified; legacy field preserved | Yes | Yes (8 tests) | Yes — regeneration identical | **COMPLETE** |
| P3-T4 | Explain and decide the 4-vs-12 neuron discrepancy from archived data; no re-simulation | Yes | Yes | Yes — matched archive comparison | **COMPLETE WITH LIMITATIONS** |
| P3-T5 | Deterministic processing of the frozen **test** split; measured detection/classification/localisation/distance errors | Yes (harness) | Yes | **No independent test split** | **BLOCKED** |
| P3-T6 | Per-class P/R, mAP@0.5, classification, IoU, centre error, lane accuracy, distance MAE/ρ; provisional gates | IoU/AP/confusion/latency only | Yes | Validation-run metrics only | **PARTIALLY COMPLETE** |
| P3-T7 | 3C decision rule 1–5 and the 3C acceptance sentence | Yes | Yes (10 tests) | Yes, 23 conditions; criterion 3 fails | **PARTIALLY COMPLETE** |
| P3-T8 | Deterministic replay and reproducibility hashes (CI is not a roadmap criterion) | Yes | Yes | Yes — bit-identical replays | **COMPLETE WITH LIMITATIONS** |
| P3-T9 | p95 ≤ 50 ms at 640×360 CPU if achievable, otherwise report the measured value | Yes | Yes | Yes — 153.463 ms measured | **COMPLETE WITH LIMITATIONS** |
| P3-T10 | No unsupported feature claim; preserve default/provenance labelling | Yes | Partly | Yes — documented | **COMPLETE WITH LIMITATIONS** |
| P3-T11 | Valid `GameState`; Phase 3A interface unchanged; adapter reports unrepresented objects | Yes | Yes | Yes — 16/16 + 12/12 integration checks | **COMPLETE WITH LIMITATIONS** |
| P3-T12 | Eight pre-registered criteria: protocol/runner/tests, equivalence, 7 conditions × 2 repeats + subprocesses, invalidations, items 1–11, T3.1 classification, report, byte-identical P3-T2/T3 | Yes | Yes | Yes — `VALID`, 0 invalidations | **COMPLETE WITH LIMITATIONS** |

Summary: 1 complete, 9 complete with limitations, 2 partially complete,
1 blocked. No task is accepted on code existence alone.

For the detailed T5–T11 evidence, limitations and the four open decisions, see
`experiments/phase_3c/results/p3_t5_t11_acceptance_audit.md` (`d695f7f3…`).
The sections below record the full-chain evidence and the remaining verdicts.

## 3. Task evidence

### P3-T2 — same-graph causal control

**Criterion.** Four conditions on one frozen frame cache and one mapping:
C0 no input, C1 four neutral player features, C2 ten visual features with every
player default disabled, C3 all fourteen. Eleven invalidation rules
(capacity, non-finite state, membrane bounds, repeat divergence, current outside
the active set, condition-definition violation, protected hash, initial
conditions, cache identity, scheduler and spike hashes). No additivity
assumption. No mechanism claim.

**Result.** `VALID`; no invalidation triggered. Spike totals: C0 = 0,
C1 = 702, C2 = 2,560, C3 = 15,654,631. C1 and C2 produce **zero** spikes
outside the 138-neuron reference set; only C3 ignites (15,650,921 outside-R
spikes, 35,907 active neurons). Subprocess repeats are identical.

**Limitation.** A difference outside R is a difference in this model's spike
counts under assumed LIF parameters, a sign-by-transmitter policy and
transformed structural synapse counts. It is not evidence of a biological
pathway, information routing or behaviour. The chain ends at current injection;
no action is selected. The cached scenes are one scripted set, not a sampled
distribution of scenes.

### P3-T3 — one-factor feature ablation

**Criterion.** Measure necessity of each of the fourteen features by removing it
from the same 3,300.5 ms cached schedule, with the same archive gate and
invalidation rules, reporting contrasts against the full-input baseline.

**Result.** `VALID`; 15 conditions completed; 0 invalidations; archive gate
evaluated; contrasts reported. The raw payload is preserved byte-identically
(`6fbe3263…b8956`).

**Limitation.** Removing a feature measures necessity within this schedule; it
does not establish sufficiency. Reduced recurrent activity is not automatically
better behaviour. Network ignition is not sensory routing, and downstream
spikes are not proof of meaningful information transmission.

### P3-T3.1 — ignition reporting correction

**Criterion.** The legacy `ignition.ignited` flag means "at least one spike
outside R". Correct the misleading report additively, without editing the raw
payload or inventing an absolute threshold.

**Result.** New classification: `none` (zero outside-R spikes, definitional),
`sparse`, and `population_scale` (outside-R active neurons > |R| and outside-R
firing rate ≥ reference firing rate). Counts 1/1/13. The raw P3-T3 payload is
unchanged; its hash is identical before and after. The stored artifact
regenerates identically from the current payload. Eight focused tests pass.

**Limitation.** `population_scale` is a **provisional, post-hoc relational**
criterion; no preregistered absolute ignition threshold exists. It must always
be quoted as provisional. It does not change any simulation result.

### P3-T4 — four-versus-twelve neuron calibration discrepancy

**Criterion.** Establish what happened, quantify the difference with archived
data, and recommend whether to change the configuration; do not re-simulate.

**Result.** The population was 12 in the Phase 3A configuration before
calibration. Phase 3A.5 selected 4 into a results file that no runner reads, so
the shipped point remained 12. The four-neuron mapping is a subset of the
twelve-neuron mapping (4/4 shared), but shrinking the population reassigns
eight `visual_any` neurons to later features, so a full-network 4-vs-12
comparison is not single-factor without a mapping override. Archived data:
4 neurons meet the original ordering rule in 3/3 mapping seeds; 12 neurons meet
it in 0/1 measured seeds. Neither is a credible graded distance code. The
recommendation is to retain 12 for the frozen evidence chain, stop calling it
calibrated, and leave distance decoding open under a pre-registered comparison.

**Limitation.** No new simulation was run; the 12-neuron arm has one measured
seed. The conclusion is about the archived operating point, not about all
possible 4- or 12-neuron mappings.

### P3-T5 — independent detector evaluation

**Criterion.** "Deterministic processing of the frozen test split; measured
detection/classification/localisation/distance errors."

**Result.** **BLOCKED.** `reports/PHASE_3B1_SPLIT_MANIFEST.json` contains only
`train` and `valid` splits (five filename groups, zero cross-split groups);
there is no independent test split. `experiments/phase_3b/results/detector_evaluation.json`
records `status: blocked`, empty metrics, `protocol.test_split: false`. The
validation metrics in the integration report (precision 0.937310, recall
0.810829, mAP@0.5 0.897776, mAP@0.5:0.95 0.687726 on 1,128 images) are
training-run numbers, not independent-test accuracy. The smoke evaluations
cover two to three images. No independent number is claimed.

### P3-T6 — game-specific metrics

**Criterion.** Per-class precision/recall, mAP@0.5, classification accuracy and
confusion matrix, localisation IoU and centre error, player-lane accuracy,
jump/roll accuracy where visible, normalised distance error and monotonicity.
Provisional gates: lane ≥ 0.95, per-class P/R ≥ 0.85, mAP@0.5 ≥ 0.75,
classification ≥ 0.85, median IoU ≥ 0.5, centre error ≤ 5% diagonal, distance
MAE ≤ 0.10 with ρ ≥ 0.8; 100% schema validity.

**Result.** **PARTIALLY COMPLETE.** IoU, greedy matching, AP, mAP, per-class
P/R/F1, a class-agnostic confusion matrix, failure taxonomy, bootstrap
intervals and latency are implemented and tested. No player-lane, centre-error,
distance-MAE or gameplay-classification metric exists, and the dataset has no
player, lane, action or calibrated-distance labels. The existing evaluation
report states that mAP does not measure lane behaviour, distance accuracy or
temporal stability. No gate value is reported for an undefined metric.

### P3-T7 — temporal acceptance

**Criterion.** `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.4: (1) no failure;
(2) 3C.1 constant-sequence equivalence; (3) approach vs retreat separates above
the seed-to-seed spread in ≥ 2 of 3 mapping seeds; (4) ≥ 1 frame-rate
comparison quantified; (5) controls produce a measurable difference or the
absence is reported as a negative result. If criterion 3 fails, report a
negative result and do not reframe it as temporal coding.

**Result.** **PARTIALLY COMPLETE with a negative primary result.** 23
conditions were pre-registered in `configs/temporal_sensory.yaml` and executed
over the sparse full connectome.
- Criterion 1: pass, all runs finite and within capacity.
- Criterion 2: **pass** — temporal and static schedulers differ by 0.0 pA at
  all 1,201 steps and produce identical spike counts (463/459/459 at
  distances 0.15/0.55/0.90).
- Criterion 3: **fail** — signed d′ = 0.0 in all three seeds; approach and
  retreat each produce 460 spikes; total network d′ = 0.0; seed spread 0.0.
  Leave-one-seed-out nearest-centroid accuracy 1.0 reflects bin order, not a
  direction code.
- Criterion 4: **quantified** — current RMS difference 0.394752 pA at 200 ms
  and 0.154800 pA at 100 ms versus 50 ms; max 105.665/37.600 pA; spike-profile
  cosine distance 0.060238/0.069728; total spike ratio 1.002174/1.004348.
- Criterion 5: **measurable** — no input 0 spikes; shuffled distance-profile
  cosine 0.073544; reversed 0.014517 (threshold 0.01).

Onset: first distance-population spike 28 ms, median 35 ms across three spiking
neurons, zero pre-onset spikes, peak bin tracks entry (250/350/450 ms).
Exit: zero post-offset spikes; persistence is zero by scheduler construction
(sample-and-hold selects the most recent frame), not a membrane measurement.
**3C.5, 3C.6 and 3C.8 were not executed.** The design's T1 crossfade and T2
smoothing variants are not implemented, so 3C.1 tests the implemented path only.

### P3-T8 — replay determinism

**Criterion.** Deterministic processing and reproducibility hashes. The roadmap
contains **no CI requirement**, and no CI system is specified anywhere in the
Phase 3 documentation.

**Result.** **COMPLETE WITH LIMITATIONS.** The 3B.2C replay produced identical
detections (`8719fb3f…`), temporal (`2a857471…`), scheduler (`1c3ab12d…`) and
spike-count (`09611c7d…`) hashes twice, 15,654,631 spikes both times, model
`e6ad18f9…`, 12/12 checks. The integration check passes 16/16. P3-T2 and
P3-T12 reproduce the same C3 spike hash. No CI pipeline exists; determinism is
demonstrated directly, not by a CI gate.

### P3-T9 — latency

**Criterion.** p95 ≤ 50 ms at 640×360 CPU if achievable, otherwise report the
measured value.

**Result.** **COMPLETE WITH LIMITATIONS.** 100 CPU calls at 606×1050: full
detector p95 **153.463 ms** (mean 138.087 ms), ONNX `session.run` p95
138.764 ms, preprocessing 13.367 ms, decode/NMS 3.030 ms. The 50 ms target is
not met; the criterion explicitly permits reporting the measured value. The
measurement is not at 640×360, so it is not a direct test of the stated gate.

### P3-T10 — unsupported feature claims

**Criterion.** No unsupported player/coin claim; preserve default and feature
provenance; document unrepresented objects.

**Result.** **COMPLETE WITH LIMITATIONS.** The replay labels `player_lane` and
`player_speed` as neutral defaults, `jumping`/`rolling` and coins as
unavailable (not observed absent). It also records that the defaults were
actually scheduled (`player_lane` 800 pA, `player_speed` 1,096.361 pA), so the
simulated current is not purely visual. Detector confidence 0.426 and NMS IoU
0.7 are documented as starting points, not calibrated. The adapter records
estimated fields, unrepresented objects and warnings.

### P3-T11 — adapter and integration corrections

**Criterion.** Valid `GameState`; existing Phase 3A encoders accept it
unchanged; perception testable independently of the simulator; boundary and
adapter corrections completed or explicitly outstanding.

**Result.** **COMPLETE WITH LIMITATIONS.** Boundary tolerance is implemented and
documented (accept ≤ 1 px overflow with clipping, reject beyond; raw, clipped
and clip-distance boxes retained). The adapter reports 0–6 unrepresented tracks
per frame (mean 2.61). Integration passes 16/16 scripted and 12/12 replay
checks. Two scientific decisions remain open: confidence/NMS calibration and
the production bounds policy.

### P3-T12 — network ignition and stability

**Criterion.** Eight pre-registered criteria (`docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md`
§9), including loop equivalence, seven full-duration conditions with two
identical in-process repeats and fresh-subprocess repeats for C3 and
C3-washout, no unreported invalidation, items 1–11 reported, unchanged T3.1
classification, a report, and byte-identical P3-T2/P3-T3 artifacts.

**Result.** **COMPLETE WITH LIMITATIONS.** `VALID`; no invalidation; 11 rules
evaluated; full-duration C3 equivalence 9/9; subprocess repeats identical;
prefix gate identical. Spike totals: C0 0, C1 702, C2 2,560, C3 15,654,631,
`no-player_lane` 2,858, `no-train_lane` 2,802, C3-washout 19,503,284. T3.1
classification applied unchanged: `none` 4, `sparse` 1, `population_scale` 2.
The report exists with stability, firing-rate and spatial analyses.

**Limitation.** Spikes are model output under assumed parameters. Outside the
eligible set means "not eligible for direct current injection", not proof of a
synaptic cause. Hop distance is structural, not axonal. Membrane sampling every
10 ms summarises 139,255 neurons; per-neuron traces are not retained. The
washout extension lies outside the validated 3,300.5 ms window. No action is
selected, and no perception, learning, decision, routing or behaviour claim is
made.

## 4. Milestone-level verdicts

| Milestone | Roadmap status before this programme | Evidence after this programme | Verdict |
|---|---|---|---|
| Phase 3A — sensory encoding | Complete | 23 conditions, reproducibility hashes, tests pass | **COMPLETE** |
| Phase 3A.5 — calibration | Complete with recorded negative results | 84 conditions; 200 pA / σ 0.20 / 4 neurons / seed 20261104; ordering only at four neurons | **COMPLETE WITH LIMITATIONS** |
| Phase 3B — visual perception | Implemented; gates unmet | ONNX detector integrated; validation metrics only; no independent test; lane/centre/distance/classification unmeasured; p95 153 ms | **PARTIALLY COMPLETE** |
| Phase 3C — temporal sensory | Partially implemented; acceptance pending | Encoder/scheduler/replay exist; 3C.1 passes; 3C.2 negative; 3C.7 quantified; 3C.9 measurable; 3C.5/6/8 unrun; T1/T2 variants unimplemented | **PARTIALLY COMPLETE** |

## 5. Is Phase 3 complete?

**No.** The acceptance sentence for Phase 3C is not satisfied (criterion 3 fails
and three conditions are unexecuted), and the Phase 3B acceptance requires
measured detection, classification, localisation and distance errors on a
frozen test split, which do not exist. The engineering chain is implemented,
tested, deterministic and internally consistent; the scientific gates are not
all met.

### Acceptance criteria still unmet

1. No independent test split, therefore no independent detection,
   classification, localisation or distance accuracy (P3-T5).
2. Lane ≥ 0.95, per-class P/R ≥ 0.85 on an independent set, mAP@0.5 ≥ 0.75,
   classification ≥ 0.85, median IoU ≥ 0.5, centre error ≤ 5% diagonal,
   distance MAE ≤ 0.10 with ρ ≥ 0.8 are unmeasured (P3-T6).
3. p95 ≤ 50 ms at 640×360 is not achieved; 153.463 ms was measured at
   606×1050 and reported under the fallback clause (P3-T9).
4. 3C criterion 3 fails: approach and retreat do not separate above seed spread
   (P3-T7).
5. 3C.5 (lane ordering), 3C.6 (jump/roll intervals) and 3C.8 (T1/T2/T3
   ablation) were not executed (P3-T7).
6. The design's T1 crossfade and T2 smoothing scheduler variants are not
   implemented; 3C.1 proves equivalence only for the implemented
   sample-and-hold path (P3-T7).
7. The obstacle-distance population is the shipped 12 neurons, not the
   4-neuron calibrated point; the 12-neuron point is not calibrated (P3-T4).

### Scientific limitations that remain

- All neural results are simulated model output on synthetic or scripted input,
  not measured biological activity.
- Perception accuracy is unmeasured independently; validation-run metrics are
  not test accuracy.
- The dataset has no player, coin, lane, action or calibrated-distance labels.
- The temporal direction result is negative at the tested operating point; no
  temporal code is claimed.
- The simulated current in the real-frame replay includes constant non-visual
  player defaults.
- One obstacle, one train and one coin per frame; the schema cannot represent
  multiple objects or power-ups.
- No motor or action selection is evaluated anywhere in Phase 3.

## 6. Readiness for controlled motor-system integration

**As an engineering interface: ready.** `GameState` output validates, the
Phase 3A encoders accept it unchanged, the scheduler is deterministic, the
connectome and simulator are unchanged, and the integration and replay checks
pass. A controlled integration experiment can be built on this chain without
modifying Phase 3 code.

**As a scientifically validated sensory front end: not ready.** Independent
perception accuracy is unknown, the temporal direction criterion returned a
negative result, and the distance population is not at the calibrated point.
Any motor-system result would therefore be conditional on unvalidated input.
Motor integration may proceed only as a **controlled engineering integration**
with those conditions stated, not as evidence that the sensory pipeline
accurately perceives or temporally encodes the game.

## 7. Next justified research step

The next step that changes a scientific conclusion, in priority order:

1. **Run 3C.2 at the calibrated four-neuron operating point and execute
   3C.5/3C.6/3C.8** with the existing runner and a newly pre-registered
   configuration. This is the smallest step that can turn the negative
   direction result into a calibrated, complete 3C statement without new data.
2. **Acquire an independent evaluation set** — new sessions, or a held-out
   group with retraining — and record lane/player/action/calibrated-distance
   labels. This unblocks P3-T5 and the missing P3-T6 metrics.
3. **Decide the 4-vs-12 operating point** under a pre-registered comparison
   before any distance-decoding or motor-integration claim.

Do not begin Phase 4, 5, 6, 7, 8 or 9 work on the basis of this audit.

## 8. Verification log

| Command / check | Outcome |
|---|---|
| `git rev-parse HEAD`, `git branch --show-current` | `62a64309…`, `main` |
| `git status --porcelain` | 201 entries before this report: 21 tracked modified, 180 untracked, 0 staged; 202 including this report; README clean |
| `sha256sum README.md` and connectome | Match protected values |
| P3-T3.1 regeneration to a temporary path | Payload identical after removing timestamps; counts unchanged |
| Sidecar scan (13 phase-3C sidecars) | 13/13 artifacts exist; config and cache hashes recomputed |
| Embedded hash scan | 113/113 checks pass |
| Cache and archive digest cross-check | File, manifest, P3-T2 archived, 3B2C replay all consistent |
| Report hash scan (5 reports) | All referenced hashes resolve |
| `pytest` focused set | 75 passed in 22.32 s |
| `pytest` full suite | **823 passed in 73.86 s** |

## 9. Artifact hashes (this audit)

| Path | SHA-256 |
|---|---|
| `experiments/phase_3c/results/p3_final_phase3_audit.md` | `4479b421874c5cfa54fb6d99c1eabc1bd6c73a7c7a5ea0a576f9d79119a9cbaf` (self-hash before this row was inserted) |
| `experiments/phase_3c/results/p3_t5_t11_acceptance_audit.md` | `d695f7f32ce864cae9819c845c8d8599d8cec78319a59bcd78cf4fc4b2c98065` |
| `experiments/phase_3c/results/temporal_acceptance.json` | `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc` |
| `experiments/phase_3c/results/temporal_acceptance_report.md` | `610fc44e2b2ff02f66f7b96451b34916ad44ed95fe5ffd9304117ffb4824942c` |
| `experiments/phase_3c/results/temporal_acceptance.sidecar.json` | `b893746c2bc790b575e9073831bc2f03b54145c92f07ceca17742ed94c6f7788` |
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` |
| `experiments/phase_3c/temporal_acceptance.py` | `41f4b09effbed172502bcd06c8abc32f879b2a0168ced20bf0ec09838adc0543` |
| `tests/test_temporal_acceptance.py` | `7a101f14f1c77144353854059eda6dcd24c6597ec55eea4d987bfdbcce722796` |
| `experiments/phase_3c/results/p3_t2_full.json` | `dd27c5d2708be3e92c5f85b6de259206e974f2a1ed4f753b64c61802e9770afd` |
| `experiments/phase_3c/results/p3_t3_ablation.json` | `6fbe3263de49d5a2db830f4118814a5e45889dd0698f05e070f46fe6566b8956` |
| `experiments/phase_3c/results/p3_t3_1_ignition_classification.json` | `6c84a8842438b43fd95df4f6bb6ef06aea624e364ef848fdd6c81acf9940923b` |
| `experiments/phase_3c/results/p3_t12_network_characterization.json` | `c1555968258cc90fb731147543a032bc94f0a102d980c219b55319a4c60f465b` |
| `experiments/phase_3c/results/p3_t12_analysis_summary.json` | `da0272969fbfd97eab987124d9dcdd78edcf088f58e20ab36ed15ffee3536a4d` |
| `experiments/phase_3c/results/p3_t4_calibration_discrepancy.json` | `265a3a6c9782b954802f2bb8cae679fbc669e86b72e675d94b1d27714e573585` |

No experiment result was overwritten during this audit. The only new file is
this report. Nothing was staged, committed or pushed.
