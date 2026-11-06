# Phase 3 roadmap — sensory, perception and temporal processing

Status: **living roadmap.** Phase 3A and Phase 3A.5 are implemented and
validated. Phase 3B is implemented up to a scripted perception chain, but the
trained detector remains blocked by approvals and resources. Phase 3C is
implemented and calibrated on synthetic and scripted sequences; real-sequence
replay is blocked on the Phase 3B detector. This roadmap does not modify the
root README, the datasets, the validated connectome artifact or the external
reference repositories.

The milestone names 3A.5, 3B and 3C are a project planning convention. The
repository already contains Phase 3A; the other three names are defined here
and in the linked design documents, and are proposed rather than inherited from
an external specification.

## 1. Milestones

| Milestone | Scope | Dependency |
|---|---|---|
| 3A | Structured sensory encoding | Phase 2 |
| 3A.5 | Sensory calibration | 3A |
| 3B | Visual perception | 3A and 3A.5 |
| 3C | Integrated temporal sensory processing | 3B |

## 2. Current status

| Milestone | Status | Evidence |
|---|---|---|
| Phase 2 | Complete | 68 tests at the time, 800-neuron 1 s experiment, reproducibility |
| Phase 2.5 | Complete | 800 → 139,255 neurons, full-graph stability and memory reports |
| 3A | Complete | 14 features, 138 mapped neurons, 23-condition run, 106 passing tests, subprocess reproducibility |
| 3A.5 | Complete | 84-condition full-graph sweep, 114 passing tests, selected 200 pA / sigma 0.20 / 4 neurons, 3/3 ordered seeds, subprocess reproducibility |
| 3B | Implemented, detector blocked | Perception package, curated split, evaluation harness, scripted end-to-end integration, 265 passing tests; no trained-detector result |
| 3C | Implemented on synthetic/scripted data | Tracking, temporal features, lifecycle events, activation scheduler, 50-sequence calibration, scripted connectome run; real replay blocked |

The Phase 3B/3C code, configurations, tests and reports exist in the working
tree. They have not been staged or committed. The trained detector has not
been run: no weights were downloaded, no package was installed and no training
was started. Evidence is in `reports/PHASE_3B_3C_FINAL_VERIFICATION.md`.

## 3. Dependency graph

```
Phase 2 (simulator) ──> 3A (structured encoding, complete)
                              |
                              +──> 3A.5 (calibration, complete)
                              |        |
                              |        +──> 3B integration gate
                              |
                              +──> 3B perception layer (parallel, interface only)
                                       |
                                       +──> 3B (perception validated)
                                                |
                                                +──> 3C (real-sequence replay)

3C temporal encoder + synthetic-sequence harness
    may start after 3A.5, in parallel with 3B
```

## 4. Milestone detail

### 4.1 Phase 3A — structured sensory encoding (complete)

**Objective.** Convert a validated game-state snapshot into deterministic
current injection into mapped FAFB populations, without changing the
connectome or the simulator.

**Architecture.** `GameState` → population encoders → seeded annotated mapping
→ `SensoryInputScheduler` → `BrainSimulator`. Perception, motor output and
learning are absent.

**Dependencies.** Phase 2 simulator, the validated FAFB artifact, predicted
FlyWire annotations. No external sensory model.

**Protocol.** 14 features, 138 neurons, Gaussian/lane/boolean encoders,
200 pA reference drive, 300 ms conditions, zero background current and noise,
23 conditions plus baseline, three subprocess reproducibility checks.

**Metrics.** Configurable spike counts, active neurons, per-feature currents,
latency proxies, runtime, retained arrays, input and spike hashes.

**Acceptance.** Met: full run completes, all conditions validate, parent and
two subprocesses agree (285 spikes in the reference combined condition), all
106 tests pass, Phase 2/2.5 behaviour unchanged.

**Risks recorded.** Threshold dominance (near-identical spike counts across
distance levels), no separate sensory pathway validation, single-object schema,
mapping seed dependence.

**Measured compute.** 300 ms condition means: baseline 1.9325 s / 310.48
steps/s; sensory 2.2964 s / 266.15 steps/s; added 0.3639 s (18.83%). An
earlier run measured 0.072 s (3.63%), so wall-clock overhead is noisy.
Retained arrays 134.73 MB; mean RSS change −0.531 MB.

**Deliverables (done).** `sensory/` modules, `experiments/phase_3/`,
`docs/PHASE_3_SENSORY_ENCODING.md`, generated report and plots.

### 4.2 Phase 3A.5 — sensory calibration (complete)

**Objective.** Replace the single 200 pA reference point with a measured,
documented operating point, and determine whether graded recruitment or
threshold-dominated saturation describes the model.

**Architecture.** No new neural machinery. The existing encoder, mapping and
scheduler are swept through configuration; results are condition JSON plus a
calibration summary.

**Dependencies.** 3A only. Independent of 3B and 3C.

**Protocol.** One-factor-at-a-time sweeps:

- current 100–300 pA;
- `sigma_fraction` 0.05–0.50;
- population size 4–24;
- baseline 0–0.2;
- transition 0–100 ms;
- three mapping seeds;
- three feature levels per continuous feature.

Sub-experiments 3A.5.1–3A.5.8 cover amplitude × distance, recruitment,
tuning width, population size, seed sensitivity, additivity, transition,
baseline activation, plus sub-rheobase and saturation controls. The implemented
sweep ran 84 full-graph conditions.

**Metrics.** Peak and total current, active-unit fraction, saturation,
recruitment fraction, spikes per stimulated neuron, first-spike latency,
dynamic range, Spearman monotonicity, `d'`, additivity index, runtime, memory,
reproducibility hashes.

**Acceptance.** All factor levels configurable; full graph and frozen artifact;
controls behave or are explained; mapping disjoint and reproducible at every
size; operating point justified by measured recruitment and discrimination;
equal hashes across processes; Phase 2/2.5/3A and all tests still pass; a
negative result is reported without reframing.

**Risks.** Sweep cost; mapping pool capacity at 24 neurons; comparability with
the Phase 3A mapping; threshold behaviour mistaken for coding; seed sensitivity.

**Compute.** The implemented sweep ran 84 conditions at roughly 1.3–2.2 s per
300 ms condition, i.e. minutes of simulation per sweep plus graph load and
reporting. Sequence conditions are longer.

**Measured outcome (2026-11-04).** All 84 conditions completed without failures
and the suite passed (114 tests). The gate passed at 200 pA,
`sigma_fraction` 0.20, four obstacle-distance neurons, seed 20261104 and zero
baseline: counts were 2/6/7 at distances 0.15/0.55/0.90, identical for all
three mapping seeds, with a descriptive Poisson d' proxy of 2.357 and matching
parent/subprocess hashes. Amplitude and tuning width produced no strictly
monotone response and were retained as explicit fallbacks; population ordering
appeared only at four neurons, so the result is a small, threshold-sensitive
operating point rather than a graded distance code. Additivity was 0.0 for the
tested obstacle/coin pair, and 100 pA controls produced no spikes. Runtime is
noisy (0.246 s added in the final run, negative in an earlier run). Full detail
is in `experiments/phase_3_5/PHASE_3_5_REPORT.md`.

**Deliverables (done).** `configs/sensory_calibration.yaml`,
`experiments/phase_3_5/`, calibration and stage summaries, plots, report,
`tests/test_calibration.py`, and one recommended operating point with the
unresolved factors recorded as negative results.

### 4.3 Phase 3B — visual perception

**Objective.** Convert Subway Surfers screenshots into validated `GameState`
objects, keeping perception strictly separate from the simulator.

**Architecture.** Capture → preprocess → detection → classification →
geometry → `PerceivedScene` → `GameState` adapter. Classical OpenCV baseline
first; an optional permissively licensed learned detector only after the
dataset exists. FlyVis is audited and deferred.

**Dependencies.** 3A for the `GameState` contract and 3A.5 for the integration
operating point. The perception layer itself can be built in parallel with
3A.5 behind the interface, because it only needs to emit valid states. Dataset
capture and annotation are independent of both.

**Protocol.** One documented game version per dataset release; session-level
60/20/20 split; pilot about 1,000 frames from at least 10 sessions; full study
5,000–10,000 frames from 20–40 sessions; double annotation on 10–20%;
sub-stages 3B.0–3B.4.

**Metrics.** Per-class precision/recall, mAP@0.5, classification accuracy and
confusion matrix, localisation IoU and centre error, player-lane accuracy,
jump/roll accuracy where visible, normalised distance error and monotonicity,
schema validity, p50/p95 latency, throughput, failure taxonomy.

**Acceptance.** Deterministic processing of the frozen test split; measured
detection/classification/localisation/distance errors; valid `GameState`
output; existing Phase 3A encoders accept it unchanged; perception testable
without the simulator and vice versa; no real-time or biological claim without
measured latency and validation.

**Provisional gates.** Lane accuracy ≥ 0.95; per-class precision/recall
≥ 0.85; mAP@0.5 ≥ 0.75; classification ≥ 0.85; median IoU ≥ 0.5; centre error
≤ 5% of diagonal; distance MAE ≤ 0.10 with ρ ≥ 0.8; 100% schema validity;
p95 latency ≤ 50 ms at 640×360 CPU if achievable, otherwise report the
measured value.

**Risks.** No annotated data yet; screenshots may be copyrighted or restricted;
game-version domain shift; hand-tuned CV overfitting; AGPL contamination from
Ultralytics YOLO; distance reported as metres without calibration;
`GameState` cannot represent multiple objects or power-ups.

**Compute.** Human annotation dominates. Classical baseline is CPU-only.
A learned detector needs one small training run and inference, GPU recommended
but not assumed. FlyVis is excluded.

**Deliverables (proposed).** `perception/` modules, dataset manifest and split,
evaluation report, compatibility test with 3A, documented unrepresented objects
and unmet gates.

**Measured outcome (2026-11-06).** Dataset validation passed: 2,316 curated
images, 8,666 boxes, group-atomic split with 0 cross-split groups, 5 LOGO
folds; `boots-powerup` and `jump-electric` have no fixed-split validation
boxes. The perception package, detector adapter, observation layer,
GameState/sensory bridge and evaluation harness are implemented and tested.
The trained detector is **blocked**: no weight or dependency approval, 1.02
GiB available RAM, 2.19 GiB free disk, and NanoDet's training stack conflicts
with Python 3.13 / PyTorch 2.10. No detection metric is reported. A scripted
10-frame chain through the real pipeline, tracker, scheduler and connectome
passes 16/16 checks. Full detail is in
`reports/PHASE_3B_3C_FINAL_VERIFICATION.md`.

### 4.4 Phase 3C — integrated temporal sensory processing

**Objective.** Define and test how sequences of scenes become sensory drive,
and whether the model distinguishes temporal structure. The definition is
proposed because no prior 3C specification exists.

**Architecture.** Timestamped `GameState`/`PerceivedScene` sequence → causal
temporal encoder → activation frames → either the existing scheduler
(T1 crossfade) or an activation scheduler with the same `apply` contract
(T2 smoothing, T3 ON/OFF). The simulator and `GameState` schema are unchanged.

**Dependencies.** 3A for encoding; 3A.5 for the operating point; 3B for real
session replay. The encoder and synthetic-sequence harness can be developed in
parallel with 3B after 3A.5.

**Protocol.** 600 ms synthetic sequences with known ground truth, zero
background and noise, calibrated operating point. Experiments 3C.1–3C.9 cover
static equivalence, approach vs retreat, entry/exit timing, lane ordering,
jump/roll intervals, frame-rate sensitivity at 200/100/50 ms, encoding
ablations and controls (no input, reversed, shuffled, dropped frame). About
57 conditions plus roughly 15 seed repeats.

**Metrics.** Activation trajectory range, event transients, windowed spike
counts, latency, peak time, response duration, population-vector similarity,
`d'`, leave-one-seed-out nearest-centroid separability, forward/reverse order
sensitivity, runtime, memory, reproducibility hashes.

**Acceptance.** Causal deterministic encoder with explicit timestamps and a
defined zero state; static-equivalence test passes; approach vs retreat
separates above seed spread in at least two of three seeds or is reported as a
negative result; onset/offset/persistence measured; frame-rate sensitivity
quantified with an aliasing limit; simulator and 3A interfaces unchanged; all
existing tests pass; sparse full-graph only; negative results not reframed.

**Risks.** Frame rate aliases the 20 ms membrane; threshold dominance inherited
from 3A; single-object schema; artificial smoothness from filtering;
non-additivity; sequence cost; over-interpreting nearest-centroid separability;
scope creep into a second simulator.

**Compute.** About 5–10 minutes of simulation per full sweep at roughly 4–5 s
per 600 ms condition, plus graph load and reporting. Memory close to the Phase
3A footprint plus small activation buffers; to be measured.

**Deliverables (proposed).** `sensory/temporal_encoder.py`, an activation
scheduler if approved, `configs/temporal_sensory.yaml`, sequence schema,
`experiments/phase_3c/`, report, decision on temporal separability.

**Measured outcome (2026-11-06).** Tracking, causal temporal features,
lifecycle events and a versioned `TemporalActivationScheduler` are
implemented in `perception/tracking.py`, `perception/temporal.py` and
`sensory/temporal_scheduler.py` (the temporal encoder moved to the perception
layer so it can consume tracker output directly). Calibration on 10 synthetic families (50 sequences, seed
20261106) gives 175 TP / 0 FP / 0 FN against rule-derived expectations,
direction accuracy 0.9961, tracking continuity 0.9442 with 5 reported ID
switches, all 6 adversarial checks passing and identical repeated output.
Scheduler `apply` p95 is 9.5 µs over 41,115 calls. A 10-frame scripted chain
through the full connectome produces 560 spikes (444 stimulated) in 300.5 ms
with deterministic signatures and matching protected hashes. Agreement is
rule consistency, not independent recognition, and no trained-detector
sequence has been replayed. Full detail is in
`reports/PHASE_3C_EVALUATION.md`.

## 5. Independent and dependent work

| Work item | Depends on | Can run in parallel with | Integration gate |
|---|---|---|---|
| 3A.5 calibration sweeps | 3A | 3B dataset capture; 3B perception code behind the `GameState` interface | None beyond 3A |
| 3B dataset schema and pilot annotations | Game terms review | 3A.5 | 3B.0 exit |
| 3B classical detector and preprocessing | 3B dataset | 3A.5 | 3B.1 |
| 3B learned detector (optional) | 3B dataset, licence decision | 3A.5 | 3B.2 |
| 3B `PerceivedScene`/`GameState` adapter | 3A contract | 3A.5 | 3B.3 |
| 3B end-to-end neural integration | 3A.5 operating point | — | 3B.4 |
| 3C temporal encoder and synthetic harness | 3A, 3A.5 | 3B | 3C static equivalence |
| 3C real-sequence replay | 3B | — | 3C.9 |
| 3C final acceptance | 3B and calibrated point | — | 3C |

Key points:

- **3A.5 and 3B are independent** in their core work. 3B's only 3A.5
  dependency is the choice of operating point used in the final neural
  integration test.
- **3B can start before 3A.5 finishes** as long as it emits validated
  `GameState` objects and does not assume a drive amplitude.
- **3C is not fully independent of 3B.** Its encoder and synthetic experiments
  can start earlier, but acceptance requires replaying real 3B sequences and
  reporting perception-error propagation.
- **No milestone depends on FlyVis, Motor or learning.** Those remain separate
  decisions.

## 6. Recommended sequencing

1. Approve or amend the definitions in the three design documents.
2. Implement 3A.5 and produce the calibrated operating point (or the negative
   result). **Done 2026-11-04.**
3. In parallel, freeze the 3B dataset schema and capture the pilot set.
4. Build and evaluate the 3B classical baseline and adapter; integrate with 3A
   using the calibrated point.
5. Implement the 3C temporal encoder and synthetic harness; replay 3B sessions
   and report temporal separability.
6. Revisit motor decoding and learning only after 3B and 3C are validated.

Each step is gated by its own acceptance criteria. A failed gate stops the
sequence rather than being papered over.

## 7. Cross-milestone risks

| Risk | Affects | Mitigation |
|---|---|---|
| Threshold-dominated responses are mistaken for coding | 3A.5, 3B integration, 3C | Calibrate first; report saturation and monotonicity; pre-register decision rules |
| Perception errors propagate silently into neural claims | 3B, 3C | Compare perceived vs ground-truth schedules; report error propagation |
| Multi-object scenes exceed the schema | 3B, 3C | Explicit conversion report; additive schema extension with its own tests |
| Distance and velocity are confused with physical quantities | 3B, 3C | Normalised proxies and approach indices only; no metres or m/s claims |
| Licence contamination (AGPL, GPL) | 3B | Classical baseline and permissive detectors; deliberate review before any AGPL use |
| Compute creep from perception or visual models | 3B, 3C | Offline replay; measure p95; exclude FlyVis from the MVP |
| Scope creep into motor control, reward or RL | All | Explicit non-goals in every design document |
| Reference repositories influence validated structure | All | Read-only use; no IDs, mappings or parameters copied; artifact unchanged |
| Reproducibility lost in longer sequences | 3C | Fixed seeds, explicit timestamps, subprocess hashes, no wall-clock use |

## 8. Scientific-integrity rules for every milestone

- Separate measured structure, predicted annotations, model assumptions,
  computational approximations and simulated activity in every report.
- Never present spike counts as evidence of biological coding.
- Never use summed synapses, connection counts and physiological conductance
  interchangeably.
- Report negative results, unmet gates and saturation explicitly.
- Keep the root README, datasets, connectome artifact and external references
  unmodified.
- Do not install or execute reference code merely to advance a milestone; any
  integration requires an explicit decision and a licence review.

## 9. Explicitly not planned in this roadmap

- Motor decoding, action selection, keyboard control or game automation.
- Reward, dopamine, plasticity or reinforcement learning.
- Live browser capture or real-time closed-loop control.
- FlyVis integration into the live simulation.
- Changes to the validated connectome, neuron indexing or simulator dynamics.
- A second independent neural simulator or dense N × N connectivity.

## 10. Review decision points

Before any implementation begins, the project owner should confirm:

1. The 3A.5 factor ranges and the negative-result rule.
2. The 3B dataset size, capture source, and the licence route for any learned
   detector.
3. The proposed 3C definition, especially whether ON/OFF populations belong in
   the first implementation.
4. Whether the multi-object `GameState` extension is a 3B sub-stage or a
   prerequisite for 3C.

## 11. Document map

| Document | Role |
|---|---|
| `docs/PHASE_3_SENSORY_ENCODING.md` | Implemented Phase 3A design and results |
| `docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md` | Implemented calibration design, selection rule and measured outcome |
| `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md` | Proposed perception milestone |
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | Proposed temporal milestone |
| `reports/PHASE_3B_DATASET_AND_DETECTOR.md` | Curated dataset and detector status |
| `reports/PHASE_3B_EVALUATION.md` | Evaluation protocol, harness and blocked result |
| `reports/PHASE_3B_INTEGRATION.md` | Perception-to-encoder integration |
| `reports/PHASE_3C_TEMPORAL_ARCHITECTURE.md` | Implemented temporal architecture |
| `reports/PHASE_3C_CALIBRATION.md` | Synthetic temporal calibration |
| `reports/PHASE_3C_EVALUATION.md` | Temporal and end-to-end measurements |
| `reports/PHASE_3B_3C_FINAL_VERIFICATION.md` | Consolidated status and verification |
| `docs/RESEARCH_REFERENCE_REVIEW.md` | Reference repository and licensing audit |
| `docs/PHASE_3_ROADMAP.md` | This document |
