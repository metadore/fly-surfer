# Phase 6A - Information-Theoretic Analysis: Architecture, Data and Feasibility Audit

**Status:** AUDIT COMPLETE - NO ENTROPY OR MUTUAL-INFORMATION COMPUTATION PERFORMED  
**Phase:** 6A  
**Project root:** `C:/Users/Hp/fruitfly/FLY-SURFER`  
**Generated (UTC):** 2026-11-10T00:00:00+00:00

This audit determines what Phase 6 can legitimately measure before any information-theoretic quantity is estimated. It inventories the architecture, the stored experiment artifacts, every variable that could enter an entropy or mutual-information endpoint, and the statistical machinery required to make such estimates defensible. It performs **no** entropy or mutual-information computation on any dataset, runs **no** new simulation, and modifies **no** protected file.

## Scope

Audit existing architecture, experiment outputs, available variables and statistical requirements so Phases 6B-6G can be specified without inventing capability that does not exist.

**Research question.** What task-relevant information is present in neural activity, and how does it relate to sensory inputs, motor outputs and reward?

**Framework.** Shannon information theory: H(X), H(X,Y), I(X;Y), I(X;Y|Z).

**Explicitly not performed in this phase:**

- no entropy computed on any dataset
- no mutual information computed on any dataset
- no new simulation run
- no new recording campaign
- no modification of Phase 3, Phase 4 or Phase 5 source files
- no modification of completed experiment outputs
- no modification of datasets or connectomes
- no staging, commit or push

## Definitions declared for later phases

| Symbol | Definition |
|---|---|
| H(X) | Shannon entropy of a discrete variable X in bits, base-2 logarithm. |
| H(X,Y) | Joint Shannon entropy using the same marginal discretisation each variable uses individually. |
| I(X;Y) | H(X) + H(Y) - H(X,Y); non-negative in expectation, upward-biased under plug-in estimation. |
| I(X;Y\|Z) | Conditional MI, evaluated as a weighted average of within-stratum I(X;Y) over discrete strata of Z. |
| normalised_mi | I(X;Y) / min(H(X), H(Y)); reported only when min entropy exceeds a declared floor. |
| uncertainty_coefficient | I(X;Y) / H(Y); asymmetric, direction explicit. |

## Preserved findings (unchanged)

These statements are carried forward exactly as established. Phase 6A does not reinterpret them.

| ID | Phase | Finding | Consequence for Phase 6 |
|---|---|---|---|
| PF-01 | 4H | Sensory neurons were stimulated, but effective downstream propagation to motor populations was not established. Actual sensory events did not produce a distinguishable propagated response against the tested controls. Highest evidence grade E2. | Constrains 6D and 6E: no established sensory-to-motor channel exists to measure information over. |
| PF-02 | 4H | Round-trip condition totals: B (stimulated) 3562, C (shuffled timing) 3760, D (random placement) 3648, E (intact control) 3561, F 0, G 0. | Quantifies null-like spacing between stimulated and control conditions; a claimed information gain must exceed this spacing. |
| PF-03 | 5F | Fixed complete 0.795 +/- 0.084; plastic complete 0.945 +/- 0.023; paired difference +0.150; Holm-adjusted p = 0.00781; Cohen dz = 2.012. | The only established behavioural effect in the project; 6F must explain it in information terms without altering it. |
| PF-04 | 5E | Action selectivity 0.192, below the 0.25 chance level. | Warns that action selection is not demonstrably selective; neural-to-action information endpoints may be uninformative by construction. |
| PF-05 | 5G | Biological interpretation of the plasticity result is INCONCLUSIVE. | Phase 6 language about biological plausibility must remain inconclusive absent new evidence. |

## 1. Existing architecture

The repository is a layered simulation stack. Each layer is implemented and has completed experiment outputs behind it, except `learning/`, which contains docstring-only stubs.

| Package | Status | Key types | Role |
|---|---|---|---|
| brain | implemented | LIFPopulation, Synapse, BrainSimulator, SpikeRecorder | LIF dynamics, connectivity, spike recording, generic simulation loop. |
| sensory | implemented | game state encoders, population mapping, activation scheduler | Game-state observation to sensory population activation; 138 mapped neurons (12x8 + 6x6). |
| perception | implemented | detector backend, tracker, temporal feature encoder, event encoder | Detection and tracking to discrete temporal events (appeared, approaching, receding, occluded, disappeared). |
| motor | implemented | MotorDecoder, decode_series, decode_recorder | Reads BANC population activity windows and produces per-action decision scores. |
| plasticity | implemented | PlasticSimulator, reward system, eligibility traces, statistics | RPE, three-factor rule, per-step callback, paired statistics utilities. |
| learning | placeholders | mutual_information.py, dopamine.py, synaptic_plasticity.py | Docstring-only stubs. Unimported by any runner. Must be reported as placeholders, not capability. |
| experiments | implemented | phase_3, phase_3_5, phase_3b, phase_3c, phase_4f, phase_4g, phase_4h, phase_5 | Runners, configs, results and reports for completed phases. |

**Data flow.** game/sequence -> sensory encoders -> activation scheduler -> BrainSimulator (LIF) -> optional BANC adapter -> MotorDecoder -> action scores; phase 5 adds reward -> RPE -> eligibility trace -> weight delta.

### Recording interfaces

The single most important architectural fact for Phase 6 is that instrumentation is uneven. Spikes can be saved by an existing API, but membrane potentials and eligibility traces are never persisted, and only one simulator exposes a per-step hook.

| Interface | File | Capability | Persistence | Scope |
|---|---|---|---|---|
| SpikeRecorder | `brain/neural_activity.py` | records (time_ms, neuron_index) pairs during a run | save() writes npz keys spike_times_ms, spike_neuron_indices, n_neurons, duration_ms, capacity | spikes only; no membrane potentials; bounded capacity buffer |
| BancActivityAdapter | `motor / experiments` | windowed readout of BANC population activity | window summaries consumed by MotorDecoder; windows are not persisted as raw traces |  |
| MotorDecoder | `motor/decoder.py` | decode_series / decode_recorder produce per-window raw and smoothed action scores | written inside experiment JSON records |  |
| PlasticSimulator.step_callback | `plasticity/plastic_simulator.py` | called every step as step_callback(step, step*dt_ms, spikes, simulator) | whatever the callback chooses; existing runners store reduced metrics | the only per-step instrumentation hook in the codebase |
| LIFPopulation.membrane_potential | `brain/neuron_model.py` | property exposing the voltage vector | in-memory only; never serialised by any runner |  |
| BrainSimulator / BancSimulator | `brain/simulator.py` | run loop with spike recording | no per-step callback hook; adding one would modify Phase 4 source |  |

### Statistics utilities already present

| File | Role |
|---|---|
| `experiments/phase_4h/common.py` | integrity_snapshot() over experiments/phase_4h/baseline_integrity.json (37 entries) |
| `experiments/phase_4h/control_draws.py` | seeded random control draw construction |
| `experiments/phase_5/comparative.py` | paired contrast, bootstrap CI of means, sign-flip test |
| `plasticity/statistics.py` | Holm-Bonferroni, effect sizes, descriptive summaries |
| `experiments/phase_5/final_assessment.py` | integrity validation and git cleanliness checks |

### Structural gaps

- No persisted membrane potentials anywhere in the repository.
- No persisted eligibility traces; only per-condition summaries.
- No per-step hook outside PlasticSimulator, so BrainSimulator/BancSimulator runs cannot emit step-level traces without source changes.
- learning/mutual_information.py is a stub and provides no estimator.
- No experiment stores per-neuron spike trains except the Phase 4G smoke NPZ.
- Phase 4H recorded zero non-stimulated downstream spikes, so downstream variability needed for MI is absent in stored data.
- No trial-level repetition of identical stimuli with independent noise in the stored data.

## 2. Experiment and data inventory

Twenty-four artifacts were inventoried. **9 of 24** carry any time-structured content at all, and most of those are event streams or per-episode records rather than neural traces. Only `DI-10` contains raw spikes, and only 74 of them. Everything else is a summary, an aggregate, a score series or a weight snapshot.

| ID | Path | Bytes | Class | Time series | Temporal resolution | Records |
|---|---|---|---|---|---|---|
| `DI-01` | `experiments/phase_3/results/summary.json` | 120,493 | aggregate_summary | no | per-condition aggregate (no per-step array) | 23 condition records |
| `DI-02` | `experiments/phase_3/results/conditions/*.json` | n/a | per_condition_summary | yes | per-step schedule indices; metrics aggregated | 23 files |
| `DI-03` | `experiments/phase_3_5/results/calibration_summary.json` | 4,919 | aggregate_summary | no | not applicable | 1 summary |
| `DI-04` | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | 607,622 | event_stream | yes | per-frame (10 fps sequence) plus event timestamps | 100 frames / 215 events |
| `DI-05` | `experiments/phase_3c/results/temporal_calibration.json` | 33,766 | aggregate_summary | no | per-family aggregate | 10 families |
| `DI-06` | `experiments/phase_3c/results/integration.json` | 19,659 | per_condition_summary | yes | per-frame feature table (10 rows) | 10 frames |
| `DI-07` | `experiments/results/phase_4f/motor_decoder_experiment.json` | 538,744 | per_condition_summary | yes | 5 windows per run (fixed analysis windows) | 132 runs, 660 window rows |
| `DI-08` | `experiments/results/phase_4g/phase_4g_experiment.json` | 193,917 | aggregate_summary | no | per-run aggregate | experiment-defined run list |
| `DI-09` | `experiments/results/phase_4g/phase_4g_summary.json` | 25,124 | aggregate_summary | no | not applicable | 1 summary |
| `DI-10` | `experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108/activity.npz` | 1,290 | spike_times | yes | spike times in ms | 74 spikes |
| `DI-11` | `experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108/run_metadata.json` | n/a | aggregate_summary | no | not applicable | 1 record |
| `DI-12` | `experiments/results/phase_4h/sensory_roundtrip.json` | 2,908,139 | aggregate_summary | no | per-run aggregate | 27 runs |
| `DI-13` | `experiments/results/phase_4h/control_draws.json` | 4,752,502 | aggregate_summary | no | per-run aggregate | 500 runs |
| `DI-14` | `experiments/results/phase_4h/population_sensitivity.json` | 3,043,241 | aggregate_summary | no | per-run aggregate | 175 runs |
| `DI-15` | `experiments/results/phase_4h/weight_sensitivity.json` | 1,624,140 | aggregate_summary | no | per-run aggregate | 220 runs |
| `DI-16` | `experiments/phase_4h/sequences/events_0_99.json` | 60,984 | event_stream | yes | event timestamps at sequence frame rate | 148 events |
| `DI-17` | `experiments/phase_4h/sequences/events_200_299.json` | 63,790 | event_stream | yes | event timestamps at sequence frame rate | 152 events |
| `DI-18` | `experiments/results/phase_5b/reward_system.json` | n/a | aggregate_summary | no | per-episode aggregate | validation record set |
| `DI-19` | `experiments/results/phase_5c/trace_benchmark.json` | n/a | aggregate_summary | no | per-benchmark-case aggregate | benchmark cases |
| `DI-20` | `experiments/results/phase_5d/plasticity_unit_experiments.json` | n/a | aggregate_summary | no | per-unit-case aggregate | unit cases |
| `DI-21` | `experiments/results/phase_5e/controlled_learning_raw.json` | 5,853,538 | per_condition_summary | yes | per-episode records (24 ms episodes, 48 steps) | 7560 records |
| `DI-22` | `experiments/results/phase_5e/checkpoints/condition_B_replicate_0.npz` | 2,181 | weight_state | no | snapshot at checkpoint, not a trace | 1 checkpoint |
| `DI-23` | `experiments/results/phase_5f/comparison_raw.json` | 29,625,280 | per_condition_summary | yes | per-episode records | 33120 records |
| `DI-24` | `experiments/results/phase_5g/final_assessment.json` | 19,519 | statistical_summary | no | not applicable | 1 assessment |

**Class breakdown.**

- `aggregate_summary`: 13
- `event_stream`: 3
- `per_condition_summary`: 5
- `spike_times`: 1
- `statistical_summary`: 1
- `weight_state`: 1

The decisive observation: no completed experiment stored a per-neuron spike train alongside its stimulus inputs. Any Phase 6 endpoint that requires both sides simultaneously must generate a new recording; it cannot be recovered from disk.

## 3. Available variables

Every variable is tagged with its provenance. `measured` means derived from recorded or detector data, `simulated` means produced by the model, `derived` means computed from other stored quantities, and `recorded` means run metadata. No variable below is inferred from the architecture; each one is tied to a specific artifact ID or interface.

### Inputs

| ID | Variable | Source | Resolution | Samples | Missingness | Provenance | MI feasibility |
|---|---|---|---|---|---|---|---|
| IN-01 | raw sensory observation (game state / detector boxes) | generated at run time by sensory encoders and perception pipeline | per frame | not stored | absent from all persisted artifacts | derived | low - must be regenerated or re-derived |
| IN-02 | sensory population activation (138 mapped neurons) | scheduler output feeding BrainSimulator | per step (0.5 ms) within episode | aggregated only | per-step vector never serialised | simulated | low without a new recording campaign |
| IN-03 | stimulus identity / event class | 5-class event encoder (appeared, approaching, receding, occluded, disappeared) | per event | 215 events in replay, 300 events in 4H sequences | none in event files | measured (detector-derived) | high at event level |
| IN-04 | stimulus timing | events_0_99.json, events_200_299.json, 3B.2C replay | frame index and ms | 300 events | none | measured | high |
| IN-05 | task state / episode phase | Phase 5E and 5F episode records | per episode (24 ms, 48 steps) | 7560 and 33120 records | none within stored records | simulated | high |
| IN-06 | reward event | Phase 5B reward system, 5E and 5F records | per episode | 7560 and 33120 records | none | simulated | high |
| IN-07 | cue population identity (4 cue populations x 8 neurons) | Phase 5 task substrate, 128 cue-to-action edges | per episode | 7560 and 33120 records | none | simulated | high |
| IN-08 | action set (4 actions) | Phase 5 task substrate | per episode | 7560 and 33120 records | none | simulated | high |
| IN-09 | sequence frame index and timestamps | 3B.2C replay and 3C integration | per frame (10 fps) | 100 frames, 10 feature rows | none | measured | high |
| IN-10 | reward prediction error | Phase 5B and 5E derived quantities | per episode | stored per record where computed | only in phases that computed it | derived | high |
| IN-11 | sensory condition label (B, C, D, E, F, G) | Phase 4H experiment records | per run | 27 + 500 + 175 + 220 runs | none | simulated | high |
| IN-12 | seed / replicate identifier | all experiment metadata | per run | all runs | none | recorded | high (defines replication unit) |

### Neural variables

| ID | Variable | Source | Resolution | Samples | Missingness | Provenance | MI feasibility |
|---|---|---|---|---|---|---|---|
| NE-01 | neuron identity within population | activity.npz spike_neuron_indices (n_neurons 172433); mapping tables in phase_3 config | per spike | 74 spikes in smoke run | absent for every other run | simulated | high only for the smoke run |
| NE-02 | population identity (mapping table) | Phase 3 sensory mapping (96 + 36 neurons); 4H neuron class lists | static per run | 138 mapped neurons; 4H class lists | none | derived from connectome | high |
| NE-03 | spike times | activity.npz spike_times_ms | 0.5 ms step resolution | 74 spikes over 100 ms | single smoke run only; no phase 4H or 5 spike trains | simulated | high for smoke run, absent elsewhere |
| NE-04 | spike counts per window | derivable from activity.npz; decoder windows otherwise consume activity not counts | per decoder window (5 per run) | 660 window rows in 4F | counts not stored | derived | high where spikes exist |
| NE-05 | firing rates | not persisted | would be per window or per step | none | absent | derived | low without new campaign |
| NE-06 | membrane potentials | LIFPopulation.membrane_potential (in-memory property) | per step (0.5 ms) | none | never serialised by any runner | simulated | not feasible without new recording code |
| NE-07 | eligibility traces | plasticity trace implementation | per step | none | only per-condition summaries stored | simulated | not feasible from stored data |
| NE-08 | structural and initial synaptic weights | connectome graph loader; structural_count layer | static per run | 128 cue-to-action edges in the Phase 5 task substrate | none | derived from connectome | high |
| NE-09 | effective weights | checkpoint npz (delta_exc/delta_inh length 128); weight layer summaries | snapshot per checkpoint | 1 checkpoint in 5E | only checkpoint snapshots, not trajectories | simulated | medium - snapshots only |
| NE-10 | weight deltas | checkpoint npz | snapshot per checkpoint | 128 + 128 values | sparse coverage | simulated | medium |
| NE-11 | downstream BANC population activity | 4H round-trip records; 4G adapter windows | per run aggregate and per window | 27 + 500 + 175 + 220 runs | raw activity not stored; zero non-stimulated spikes reported | simulated | low - no variability to measure |

### Outputs

| ID | Variable | Source | Resolution | Samples | Missingness | Provenance | MI feasibility |
|---|---|---|---|---|---|---|---|
| OUT-01 | motor population activity | BANC adapter windows consumed by MotorDecoder | per decoder window | 660 rows in 4F | raw window vectors not stored | simulated | low without new campaign |
| OUT-02 | decoder output (raw and smoothed scores) | 4F, 4G, 4H records | 5 windows per run | 660 rows in 4F; per-run scores in 4H | none | simulated | high |
| OUT-03 | selected action | 5E and 5F episode records | per episode | 7560 and 33120 records | none | simulated | high |
| OUT-04 | task outcome (correct / incorrect) | 5E and 5F episode records | per episode | 7560 and 33120 records | none | simulated | high |
| OUT-05 | reward received | 5E and 5F episode records | per episode | 7560 and 33120 records | none | simulated | high |
| OUT-06 | completion performance | 5F comparison records (complete-condition performance) | per run aggregate | core and robustness run sets | none | simulated | high |
| OUT-07 | propagation evidence decision | 4H round-trip and 4H5 grading | per run | 27 + 500 + 175 + 220 runs | none | derived | medium |

## 4. Missing data

The gaps below are the binding constraints on Phase 6. They are listed as data-availability statements, not as criticism of earlier phases: each earlier phase stored exactly what it needed for its own question, and none of those questions required entropy estimation.

| ID | Gap | Consequence | Remedy |
|---|---|---|---|
| MD-01 | Raw spike trains for every completed experiment except the Phase 4G smoke run | Entropy of neural spike trains and MI from spikes cannot be estimated from stored data. | Recording campaign in 6B using existing SpikeRecorder.save(); no source modification required. |
| MD-02 | Per-step membrane potentials | No continuous-valued neural variable; any neural entropy must use discrete spike counts. | Requires new instrumentation via PlasticSimulator.step_callback; BrainSimulator has no hook. |
| MD-03 | Per-step eligibility traces | 6F cannot relate information content to trace magnitude at step level. | Only obtainable by extending PlasticSimulator callback payload, which is already available. |
| MD-04 | Trial-level repeated identical stimuli with independent noise | Trial-independence assumption cannot be satisfied by resampling correlated timesteps. | Design repeated-stimulus trials in 6B; seed defines the replication unit. |
| MD-05 | Non-zero downstream (BANC) spike variability in the 4H stimulated configuration | 6D condition contrast is degenerate: control and stimulated conditions both lack downstream events. | Report 6D as infeasible until a propagation-positive configuration exists. |
| MD-06 | Stored sensory population activation vectors | Sensory-to-neural MI (6C-1) has no neural-side partner variable in storage. | Regenerate activations and spikes together in a single instrumented run. |
| MD-07 | Per-run spike data for Phase 5 fixed vs plastic comparison | 6F can only be run at task-outcome level, not at spike-train level. | Re-run 5E/5F configurations with recording enabled; eta=0 reproduces fixed hashes so provenance is preserved. |
| MD-08 | Action-selective neural readout | With selectivity 0.192 below 0.25 chance, neural-to-action information may be uninformative by construction. | Pre-declare a null-information outcome as an acceptable, reportable result. |

## 5. Feasible analyses

Of the 14 candidate endpoints, **9** can be attempted with what exists today, most of them with declared limitations. One (6B-2) is estimable only under a declared coarse code, and four (6B-3, 6C-1, 6D-1, 6F-2) are not estimable from stored data. The three tiers are: estimable now, estimable only under a declared coarse code, and not estimable without new data.

| ID | Phase | Question | Verdict | Limitation | Blocking dependency |
|---|---|---|---|---|---|
| 6B-1 | 6B | Entropy of the sensory state | **FEASIBLE WITH LIMITATIONS** | Raw observation vectors are not stored; only the coarse event code is available. | None for the coarse code; full-state entropy needs regeneration. |
| 6B-2 | 6B | Entropy of the sensory population | **FEASIBLE ONLY AS A DECLARED COARSE CODE** | A 138-neuron binary state has 2^138 states; only a declared low-dimensional summary (e.g. population count in 2-4 bins) is estimable. | Regeneration of per-step activation vectors. |
| 6B-3 | 6B | Entropy of a neural spike train | **NOT FEASIBLE FROM STORED DATA; FEASIBLE AFTER 6B RECORDING** | One 100 ms smoke run with 74 spikes cannot support entropy estimation beyond a few bins. | A recording campaign using existing APIs. |
| 6B-4 | 6B | Entropy of the motor output | **FEASIBLE NOW** | Scores are decoder outputs, not ground-truth motor command; must be labelled as decoder-derived. | None. |
| 6B-5 | 6B | Entropy of the reward signal | **FEASIBLE NOW** | Small alphabet; near-deterministic in complete conditions, so entropy may be near zero. | None. |
| 6C-1 | 6C | Mutual information sensory -> neural | **NOT FEASIBLE FROM STORED DATA** | No stored run contains sensory inputs and neural spikes jointly. | A single instrumented run recording inputs and spikes together. |
| 6C-2 | 6C | Mutual information neural -> motor | **FEASIBLE WITH LIMITATIONS** | The decoder defines the mapping, so MI partly reflects decoder construction; circularity must be declared. | None, but interpretation is constrained. |
| 6C-3 | 6C | Mutual information neural -> reward | **FEASIBLE WITH LIMITATIONS** | No neural variable is stored at episode level; only condition-level identifiers. | Recording neural summaries per episode. |
| 6C-4 | 6C | Mutual information sensory -> motor | **FEASIBLE WITH LIMITATIONS** | Phase 4H found no distinguishable propagated response, so any estimate is expected near the null. | None, but a near-zero result is the pre-declared expectation. |
| 6D-1 | 6D | Actual sensory conditions versus shuffled and matched controls | **NOT FEASIBLE NOW - DEGENERATE** | 4H recorded zero downstream spikes outside stimulated neurons, so both arms carry no downstream information to compare; MI would be 0 by construction. | A propagation-positive configuration must exist first. |
| 6E-1 | 6E | Neural-to-motor information using decoder output | **FEASIBLE WITH LIMITATIONS** | Decoder output is not ground truth: MI measures consistency with the decoder, not with the true motor command. | None, but the report must state this explicitly. |
| 6F-1 | 6F | Fixed versus plastic information at task level | **FEASIBLE** | Task-level only; no neural-level counterpart is stored. | None. |
| 6F-2 | 6F | Fixed versus plastic information at neural level | **NOT FEASIBLE FROM STORED DATA** | No spike trains were saved for either condition; checkpoint npz holds weights only. | Recording campaign; eta=0 reproduces fixed hashes so comparability is preserved. |
| 6G-1 | 6G | Statistical validation of information estimates | **REQUIRED IN EVERY PHASE** | No existing module implements plug-in entropy or MI; new code is required. | None. |

## 6. Infeasible analyses and reasons

These analyses are excluded from Phase 6 unless new data are generated. Recorded here so that their absence in later reports is a deliberate decision rather than an omission.

| ID | Analysis | Reason | What would be required |
|---|---|---|---|
| IF-01 | Spike-train entropy from completed experiment outputs | Only 74 spikes in one 100 ms smoke run were persisted; capacity-limited recorder and no per-run spike dumps elsewhere. | A recording campaign invoking SpikeRecorder.save() per run. |
| IF-02 | Sensory-to-neural MI from completed experiment outputs | No stored artifact contains stimulus identity and neural spikes jointly. | Joint instrumentation of the activation scheduler and the spike recorder in the same run. |
| IF-03 | Membrane-potential entropy or potential-based MI | Potentials exist only in memory via LIFPopulation.membrane_potential and are never serialised. | New recording callback; BrainSimulator has no per-step hook. |
| IF-04 | Information carried by eligibility traces | Traces are computed but only per-condition summaries were saved. | PlasticSimulator.step_callback writing trace vectors, which is supported without source changes. |
| IF-05 | Phase 4H condition-contrast MI (stimulated vs shuffled vs random) | Zero non-stimulated downstream spikes means both arms have degenerate distributions; MI is 0 by construction. | A configuration where sensory stimulation produces distinguishable downstream activity. |
| IF-06 | Joint entropy of the full 138-neuron sensory population | State space is 2^138; no sample size can populate it. | A pre-declared coarse code (population count in 2-4 bins, or a small cluster label). |
| IF-07 | MI computed by pooling every timestep as an independent sample | Timesteps are autocorrelated within an episode; treating them as independent inflates effective N and understates bias. | Block bootstrap or episode-level aggregation before inference. |
| IF-08 | Causal interpretation of any MI estimate | MI is symmetric and observational; it does not identify direction or mechanism. | Perturbation or intervention design; MI may only be described as information shared. |
| IF-09 | Fixed versus plastic neural-level MI from stored data | Neither condition saved spike trains; only task records and one weight checkpoint exist. | Re-running both conditions with recording enabled. |


## 7. Recommended estimators

### Primary estimator

**plug-in (maximum likelihood) discrete entropy and mutual information**

- Entropy: `H(X) = -sum_x p(x) log2 p(x)`
- Mutual information: `I(X;Y) = sum_x sum_y p(x,y) log2 [ p(x,y) / (p(x) p(y)) ]`
- Rationale: Transparent, deterministic and auditable; all later corrections are reported relative to it.
- Known defect: Upward bias of order (|X|-1)(|Y|-1)/(2 N ln 2) bits for MI.

### Bias corrections

| Correction | Use |
|---|---|
| Miller-Madow | first-order entropy correction, (K-1)/(2 N ln 2) with K observed non-empty bins |
| analytic bias subtraction | subtract the (\|X\|-1)(\|Y\|-1)/(2 N ln 2) MI floor and report the raw value alongside |
| Chao-Shen coverage-adjusted | optional check on undersampled discrete entropy; reported only as sensitivity |
| NSB | listed as future option only; not implemented and not required for 6B-6G |

### Discretisation

Every continuous quantity is converted to a declared discrete code before estimation; the code is part of the pre-registration, never chosen after seeing results.

- Schemes: equal-width after rank transform; quantile bins; fixed physiological thresholds where they exist
- Bin counts reported for every endpoint: 2, 3, 4
- Sensitivity: All three bin counts are reported for every endpoint; no single binning is presented as the result.
- Prohibition: Bins chosen to maximise MI are not permitted.

### Normalisation

- NMI: `I(X;Y) / min(H(X), H(Y))`
- Uncertainty coefficient: `I(X;Y) / H(Y), reported with explicit direction`
- Floor rule: If min(H(X), H(Y)) is below 0.1 bits, report normalised values as undefined rather than inflated.

### Conditional information

- Method: weighted average of within-stratum I(X;Y) over discrete strata of Z
- Guard: Strata with fewer than the declared minimum samples are pooled or dropped, and the decision is reported.

### Exclusions

- No continuous-density estimators (KSG and similar) in 6B-6G; all variables are discretised first.
- No scipy dependency added for the estimator core.
- Negative corrected estimates are clipped to zero and flagged, never reported as negative information.

## 8. Statistical validation plan

**Replication unit.** The seed, not the timestep and not the window. Every inferential statement is computed over independent seeds; all timesteps and windows within a seed are treated as clustered observations.

**Independence rules.**

- Timesteps inside an episode are autocorrelated and are never counted as independent samples.
- Decoder windows overlap in origin and are clustered by run.
- Condition contrast uses paired seeds where the design is paired.
- Any analysis that cannot respect clustering is reported as descriptive only.

### Finite-sample bias

`E[I_hat] - I >= (|X|-1)(|Y|-1) / (2 N ln 2) bits`

| N (4x4 table) | Bias floor (bits) | Usable for inference |
|---|---|---|
| 5 | 1.298 | no |
| 10 | 0.649 | no |
| 40 | 0.162 | no |
| 100 | 0.065 | yes |
| 400 | 0.016 | yes |
| 1000 | 0.006 | yes |

- Bias <= 0.10 bits requires N >= 65
- Bias <= 0.01 bits requires N >= 649
- Below roughly N=50 the asymptotic expression understates the real bias; a per-run 5-window cell cannot support a 4x4 table.
- Mitigation: Pool within seed to a 2x2 endpoint or aggregate across seeds before estimation; report the raw and corrected values together.

### Autocorrelation

- Handling: Block bootstrap over contiguous episode blocks, block length declared before analysis; no i.i.d. resampling of timesteps.
- Diagnostic: Lag-1 autocorrelation reported for every continuous variable used.

### Null models

| Null | Description |
|---|---|
| time shuffle | permute the time axis of one variable, destroying temporal pairing and preserving marginals |
| trial shuffle | permute labels across independent trials or seeds |
| matched control draws | reuse the Phase 4H control-draw construction so null and real share the same wiring statistics |
| surrogate spike trains | rate-matched Poisson surrogates preserving per-neuron mean rate |

### Confidence intervals, multiplicity and effect sizes

- Percentile bootstrap over seeds with a declared resample count; report 2.5 and 97.5 percentiles and the number of seeds.
- Holm-Bonferroni over the pre-declared core endpoint family per phase, exactly as Phase 5F; exploratory endpoints are descriptive only.
- Effect sizes: I in bits, normalised MI, uncertainty coefficient, paired difference in bits with CI
- A near-zero MI is a reportable result when the null distribution is documented. No endpoint may be dropped for being null.
- Every 6B-6G phase declares endpoints, bin counts, N thresholds, null models and the Holm family before any estimate is computed.

### Interpretation rules

- Information shared is not causal influence.
- Decoder-derived MI measures consistency with the decoder, not with the true motor command.
- Correlated timesteps are never counted as independent samples.
- A bias-corrected negative estimate is clipped to zero and flagged.

## 9. Proposed 6B-6G architecture

### 6B - Entropy of sensory state, neural population, spike trains, motor output and reward

- **Objective:** Establish estimable entropy endpoints with declared discretisations and sample-size gates.
- **Endpoints:** H(sensory event class); H(coarse sensory population code); H(spike count per declared window); H(motor score bin); H(reward)
- **Controls:** shuffle null; rate-matched surrogate
- **Gate:** Each endpoint must reach its declared N threshold (>=65 for a 4x4 table) before any corrected value is reported.

### 6C - Mutual information between the four declared variable pairs

- **Objective:** Estimate I(sensory;neural), I(neural;motor), I(neural;reward), I(sensory;motor).
- **Endpoints:** I(sensory;neural); I(neural;motor); I(neural;reward); I(sensory;motor)
- **Controls:** time shuffle; trial shuffle; matched control draws
- **Gate:** Bias-corrected estimate must exceed the 95th percentile of its null distribution to be called present.

### 6D - Actual sensory conditions versus shuffled and matched controls

- **Objective:** Test whether real sensory conditions carry more downstream information than shuffled or matched controls.
- **Endpoints:** I(condition;downstream) difference, actual minus shuffled; same versus matched draws
- **Controls:** Phase 4H shuffled-time condition C; random-placement condition D; 500 control draws
- **Gate:** BLOCKED until a propagation-positive configuration exists; the stored 4H data have zero downstream events in the control arms.

### 6E - Neural-to-motor information using decoder output

- **Objective:** Quantify how much action-score information is present in population activity.
- **Endpoints:** I(neural;decoder score); uncertainty coefficient of score given neural state
- **Controls:** shuffle null; decoder ablation baseline
- **Gate:** Every result must carry the label decoder-derived; no claim about the true motor command is permitted.

### 6F - Fixed versus plastic information

- **Objective:** Compare information in fixed and plastic conditions at task level, and at neural level once recording exists.
- **Endpoints:** task-level H(outcome) and I(cue;action) fixed vs plastic; neural-level I(cue;spikes) fixed vs plastic (requires recording)
- **Controls:** paired seeds; eta=0 fixed reproduction
- **Gate:** Task-level is feasible now; neural-level is gated on the 6B recording campaign. The preserved +0.150 difference must be explained, not re-derived.

### 6G - Statistical validation and reporting

- **Objective:** Apply bias correction, permutation nulls, block bootstrap, Holm correction and effect sizes uniformly, and publish negative results.
- **Endpoints:** corrected estimate table; null comparison table; Holm-adjusted p per core endpoint; CI table
- **Controls:** all null models from every phase
- **Gate:** No phase is considered complete until its 6G block exists.

## 10. Required modules and interfaces

All Phase 6 code is additive. A new `information/` package holds the estimator surface; nothing in `brain/`, `sensory/`, `perception/`, `motor/`, `plasticity/`, `learning/` or the Phase 3/4/5 experiment trees is edited. Additive only. No edit to brain/, sensory/, perception/, motor/, plasticity/, learning/ or experiments/phase_3*, phase_4*, phase_5*.

| File | Responsibility |
|---|---|
| `information/discretization.py` | rank transform, equal-width and quantile binning, declared bin-count contract, bin audit output |
| `information/entropy.py` | plug-in H(X) and H(X,Y), Miller-Madow correction, coverage reporting |
| `information/mutual_information.py` | plug-in I(X;Y) and I(X;Y\|Z), normalised MI and uncertainty coefficient |
| `information/bias.py` | analytic bias floor, threshold checks, N planning helper |
| `information/nulls.py` | time shuffle, trial shuffle, Poisson rate-matched surrogates, matched draws |
| `information/stats.py` | block bootstrap, Holm-Bonferroni, effect sizes, CI assembly |
| `information/recording.py` | recording bundles built on SpikeRecorder and PlasticSimulator.step_callback; no source edits |
| `information/sources.py` | readers for the 24 inventoried artifacts with explicit provenance tags |
| `information/reporting.py` | deterministic JSON and Markdown emission with identifier cross-check |

**Configuration.** `configs/information_theory.yaml` holds: bin counts per endpoint, minimum N per endpoint, null model choices, Holm family definition, seed list, provenance labels.

**Phase runners.**

- `experiments/phase_6b/run_entropy.py`
- `experiments/phase_6c/run_mutual_information.py`
- `experiments/phase_6d/run_condition_contrast.py`
- `experiments/phase_6e/run_neural_motor.py`
- `experiments/phase_6f/run_fixed_vs_plastic.py`
- `experiments/phase_6g/run_validation.py`

**Tests.**

- `tests/test_phase_6a_information_audit.py`
- `tests/test_phase_6b_entropy.py`
- `tests/test_phase_6c_mutual_information.py`

**Interfaces.**

| Interface | Fields |
|---|---|
| RecordingBundle | source_id, variable_ids, provenance, temporal_resolution, arrays, seed, missingness |
| EntropyResult | variable_id, bins, N, H_plugin, H_corrected, H_max, coverage |
| MutualInformationResult | x_id, y_id, z_id, bins, N, I_plugin, I_corrected, null_quantiles, p_value, nmi, uncertainty_coefficient |

## 11. Risks and scientific assumptions

### Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RK-01 | Finite-sample MI bias is reported as information | A 4x4 table at N=40 carries 0.162 bits of pure bias, comparable to many real effects. | Report raw and corrected values together; enforce the N>=65 gate. |
| RK-02 | Autocorrelated timesteps inflate effective sample size | Confidence intervals become too narrow and nulls are rejected spuriously. | Block bootstrap and seed-level clustering; lag-1 autocorrelation reported. |
| RK-03 | Binning sensitivity dictates the conclusion | The same data can appear informative or uninformative depending on bins. | Pre-register bins, report 2/3/4 bins for every endpoint, forbid post-hoc bin search. |
| RK-04 | Decoder circularity in neural-to-motor MI | MI reflects the linear decoder rather than the population's motor content. | Label all such endpoints decoder-derived; add a shuffled-decoder baseline. |
| RK-05 | Phase 4H control arms have zero downstream events | 6D contrasts are degenerate and any MI is zero by construction. | Mark 6D blocked; do not report a null as evidence of absence of propagation beyond the existing E2 grade. |
| RK-06 | Per-step instrumentation would require editing Phase 4 source | Would violate the protection constraint on brain/ and phase 4 files. | Use only PlasticSimulator.step_callback, which already exists, or record outside the simulator. |
| RK-07 | Memory exhaustion during recording | Full-population potentials at 0.5 ms over 3.3 s need about 4.55 GB per run; only 0.97 GiB was available at audit. | Record pools only (about 27.4 MB per run for 1037 neurons) and stream to disk. |
| RK-08 | SpikeRecorder capacity limits truncate long runs | Silent loss of spikes would corrupt entropy estimates. | Check recorded count against capacity on every save; fail loudly on overflow. |
| RK-09 | MI is read as causal influence | Scientific overclaim and contradiction of Phase 4H evidence grading. | Standing interpretation rule; every report repeats the non-causal caveat. |
| RK-10 | Near-deterministic reward gives near-zero entropy | 6B-5 may return ~0 bits and look like a failure. | Pre-declare zero as an acceptable result and report the full distribution. |
| RK-11 | Action selectivity below chance (0.192) | Neural-to-action endpoints may be structurally uninformative. | Pre-declare a null outcome as publishable. |
| RK-12 | Mixing aggregate and simulated provenance in one table | False comparisons between quantities measured under different conditions. | Every row carries source_id and provenance from the inventory; sources.py enforces the tag. |

### Assumptions

| ID | Assumption | If violated |
|---|---|---|
| AS-01 | Discrete alphabets of 2-4 bins are an adequate summary of each continuous variable. | Estimates understate true information; binning sensitivity tables reveal it. |
| AS-02 | Each episode is approximately stationary. | Entropy varies within episode; report per-segment estimates. |
| AS-03 | Runs with different seeds are independent replicates. | Permutation and bootstrap invalid; must fall back to descriptive reporting. |
| AS-04 | The connectome and mapping are fixed across the analysis. | MI would mix structural with activity variability. |
| AS-05 | Decoder scores are an acceptable proxy for motor output only when labelled decoder-derived. | Neural-to-motor conclusions would be circular. |
| AS-06 | Event labels from the perception pipeline are the sensory identity ground truth. | Sensory entropy measures detector error, not stimulus entropy. |
| AS-07 | No task-relevant latent variable is omitted. | Conditional MI is reported as a lower bound only. |
| AS-08 | The analytic 4x4 bias expression is applicable at the declared N. | Report uncorrected values with the small-sample warning attached. |


## 12. Resource estimates

### Measured at audit

| Item | Value |
|---|---|
| python | 3.13.14 |
| numpy | 2.3.4 |
| pandas | 2.3.3 |
| pytest | 7.4.3 |
| os | Windows 11 (10.0.26200) |
| cpus | 12 |
| ram total gib | 15.34 |
| ram available gib | 0.97 |
| disk free gib | 31.68 |
| pytest suite | 683 passed in 61.15 s |
| note | scipy is installed but deliberately not used by the planned estimators. |

### Measured recording cost

| Quantity | Value |
|---|---|
| full potentials 3p3s run gb | 4.55 |
| pool only 1037 neurons mb per run | 27.4 |
| banc 3p3s wall s | 18.9 |
| banc retained mb | 109 |
| banc peak mb | 264 |

Full-population potential recording is the one option that must be ruled out on hardware grounds: a single 3.3 s run would need about 4.55 GB, while only 0.97 GiB was available when this audit ran. Pool-only recording at about 27.4 MB per run is the only viable route.

### Estimates for 6B-6G

These are planning estimates, not measurements.

| Item | Estimate | Basis |
|---|---|---|
| recording campaign, 200 instrumented runs, pool-only | about 5.5 GB and 25-40 min wall time | 27.4 MB/run and 200 runs plus BANC overhead |
| entropy and MI estimation over stored records | under 5 min total | all alphabets <= 4 and N <= 33120 |
| implementation of information/ package | 9 modules, 3 test files, about 1200-1600 lines | comparable to the phase 5 statistics surface |
| peak memory during estimation | under 0.5 GiB | tables of at most 16 cells over at most 33120 rows |

### Constraints

- No new heavy dependency; NumPy and the standard library only.
- Estimated disk use must stay below the 31.68 GiB free measured at audit.
- Recording must stream to disk rather than hold full-population arrays in memory.

## 13. Exact implementation sequence

| Step | Action | Gated |
|---|---|---|
| 1 | Freeze the 6A audit and record the integrity snapshot (37 baseline entries, 17 Phase 5 files, 4 Phase 4H JSONs). | no |
| 2 | Implement information/discretization.py with the declared bin contract and bin audit output; add tests. | no |
| 3 | Implement information/entropy.py and information/bias.py (plug-in H, Miller-Madow, thresholds); add tests including the 4x4 analytic bias table. | no |
| 4 | Implement information/mutual_information.py with I(X;Y), I(X;Y\|Z), NMI and uncertainty coefficient; add tests on synthetic known-answer tables. | no |
| 5 | Implement information/nulls.py and information/stats.py (time shuffle, trial shuffle, surrogates, block bootstrap, Holm); add tests. | no |
| 6 | Implement information/sources.py readers for the 24 inventoried artifacts with mandatory provenance tags; verify each reader against the recorded byte sizes. | no |
| 7 | Implement information/recording.py on SpikeRecorder and PlasticSimulator.step_callback only; no edits to protected source. | no |
| 8 | Run 6B on stored variables only: H(motor score bin), H(reward), H(event class), H(coarse sensory code). | no |
| 9 | Run 6C on stored pairs that actually exist: event class to decoder score, decoder score to outcome, condition to outcome. | no |
| 10 | Recording campaign unlocking 6B-3 (spike-train entropy), 6C-1 (sensory to neural) and 6F-2 (neural-level fixed vs plastic). **Gate:** Generates new artifacts and requires disk and runtime beyond the audit; needs explicit approval. | yes |
| 11 | Run 6D once a propagation-positive configuration exists. **Gate:** Blocked by zero downstream events in the stored 4H control arms. | yes |
| 12 | Run 6G validation and emit the final 6B-6G report with bias-corrected tables, null comparisons, Holm-adjusted p values and CIs. | no |

Steps 1-9 and 12 are executable without any new artifact. Steps 10 and 11 generate new data or depend on a propagation-positive configuration and therefore require explicit approval before they run.

## Validation record

- Test suite: `python -m pytest -q` -> 683 passed in 61.15 s (exit 0).
- Baseline integrity: 37 entries checked, pass = true, failures = 0.
- Phase 5 artifacts: 17 files hashed, 39,276,746 bytes; Phase 4H: 4 JSON files hashed.
- Protected-set dirty paths: 0; staged paths: 0.
- Repo-wide modified tracked files: 13; created by this phase: 0; latest modification 2026-11-07T10:11:02.
- Thirteen tracked files carry pre-existing edits dated 2026-11-07, three days before this audit: configs/detector_config.yaml, requirements.txt, perception/{detection,detector_config,inference,pipeline,temporal}.py, experiments/phase_3b/{evaluate_detector,run_inference}.py, experiments/phase_3c/integration_check.py and three tests. They belong to the earlier Phase 3B/3C detector work. Phase 6A did not touch them; the only files Phase 6A created are the two reports.
- JSON deliverable parses with `json.load`; every identifier family in the JSON also appears in this report.
- No entropy or mutual-information value appears in either deliverable.
- Nothing staged, committed or pushed.

## Summary

Phase 6 can begin immediately on stored data, but only on a narrow band: event-class entropy, coarse sensory codes, decoder-score entropy, reward entropy, and decoder-mediated information. The central limitation is not statistical but archival: no completed experiment persisted spike trains together with their sensory inputs, so sensory-to-neural information, spike-train entropy, membrane-potential information and neural-level fixed-versus-plastic comparisons all require a new recording campaign built on `SpikeRecorder` and `PlasticSimulator.step_callback`. Phase 6D is blocked outright by the zero downstream-event counts recorded in Phase 4H, and that block stands until a propagation-positive configuration exists. Any reporting that presents mutual information as causal influence, or that counts autocorrelated timesteps as independent samples, would misstate what the model supports.

