# Appendix A. Repository Map and Artifact Inventory

## A.1 Scope and the read-only rule

The appendix documents where the evidence used in this paper lives. It does not add evidence. The repository's data, model artifacts, reports, protocols, and records are treated as read-only inputs; this paper's own products are confined to the `research_paper/` directory. Where a historical record contains an inconsistency, the record is identified and the inconsistency is disclosed rather than repaired.

**Table A1.** Repository components and their roles. Each path is a directory in the repository root. The "evidence role" column states what the paper uses the component for, not what the component claims about biology. Source: repository tree at the time of writing.

| Path | Contents | Evidence role in this paper |
|---|---|---|
| `datasets/` | Raw, processed, and exported data; manifest and audit records | Structural inputs and provenance |
| `configs/` | Frozen YAML configuration for neurons, synapses, decoder, plasticity, sensory mapping, Phase 6, and Phase 8 | Declared parameter values |
| `brain/` | BANC graph construction, BANC sensory adapter, BANC simulation adapter, simulator | Connectome loading and simulation |
| `sensory/` | Game state, population encoder, input scheduler, sensory experiment | Sensory encoding (Phase 3A) |
| `perception/` | Detector pipeline, observation layer, tracking, event encoding | Perception (Phase 3B.2A–3B.2C) |
| `motor/` | Motor populations, threshold decoder, action selection | Motor decoding (Phase 4F) |
| `plasticity/` | Reward, modulation, eligibility traces, three-factor rule, checkpoints | Plasticity (Phase 5) |
| `learning/` | Dopamine and synaptic-plasticity scaffolding, mutual information helpers | Exploratory learning machinery |
| `information/` | Entropy, mutual information, bias correction, permutation, bootstrap | Phase 6 estimators |
| `environment/` | Standalone-game adapter, action mapping, closed-loop bridge | Phase 7 and Phase 8 game binding |
| `readout/` | Motor feature vector, linear and bias-only readouts, REINFORCE trainer | Phase 8 conditions F and Fβ |
| `evaluation/` | Conventional learner (condition E) and viability reporting | Phase 8 G7 machinery |
| `experiments/` | Phase runners and stored results, including `experiments/results/` | Executed measurements |
| `reports/` | Phase reports, audit records, owner approvals, certification JSON | Primary written evidence |
| `docs/` | Protocols, preregistrations, design audits, including REV4 | Declared design |
| `tests/` | Focused and integration test suites | Implementation verification |
| `models/` | Exported YOLO11n ONNX detector and registry | Perception model |
| `external/` | Third-party reference repositories, including `endless-surfer` | Controlled game code |
| `references/` | Reference index and provenance notes | Citation anchors |
| `research_paper/` | This paper, its figures, tables, and validation records | Paper products |

## A.2 Executed-evidence directories

**Table A2.** Executed-evidence directories and their authoritative records. Hashes are SHA-256 prefixes as recorded in the corresponding reports. "Scope" states what the directory may be used for in this paper.

| Evidence | Directory or file | Recorded hash | Scope |
|---|---|---|---|
| Pilot 1 episodes (9 rows) | `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl` | `ee479e5b…68f9` | A-condition viability; no contrast |
| Pilot 1 driver record | `reports/PHASE_8_PILOT1_EXECUTION.json` | `d3392b9c…e1e` | Execution provenance |
| D5/D6 trained artifacts (6) | `experiments/results/phase_8/training/{F,F_beta}/seed_{9001,9002,9003}/` | per-artifact digests in Table I4 | Certified, behaviourally null training |
| D5 recovery reference | `experiments/results/phase_8/training_recovery_reference/F/seed_9001/equivalence.json` | `f236d070…52bf8` | Interrupted-versus-resumed equivalence |
| Pilot 2-C episodes (54 rows) | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl` | `a14fd3bb…778991` | Floor and identity certification |
| Pilot 2-C manifest | `…/pilot2c_d3_20261123/manifest.json` | `43710d38…020534` | Run provenance |
| Pilot 2-C plan | `…/pilot2c_d3_20261123/pilot_plan.json` | `63d51f61…ddcab` | Authorised grid |
| Pilot 2-C summary | `…/pilot2c_d3_20261123/pilot_summary.json` | `44dc5c05…520c5` | Completion record |
| Pilot 2-C certification | `reports/PHASE_8_PILOT2C_CERTIFICATION.json` | `bc5effaa…aa357` | Recomputable claims P2C-1–P2C-8 |
| Certified null graphs (16) | `datasets/processed/banc_v888_random/` | certificates per seed | Constructed; not used in any executed arm |

## A.3 What the repository does not contain

The paper's negative and unavailable statements depend on absences that must be stated precisely. The repository contains no per-neuron Pilot 1 spike split, no Pilot 1 membrane-potential trace, no raw per-frame spike array from the 3B.2C replay, and no independent detector test set. It contains no recording from a living fly, no intracellular or extracellular physiology, and no measured synaptic conductance. The commercial Subway Surfers application was never instrumented or controlled. Where a figure would require one of these, it is marked unavailable rather than approximated.

---

# Appendix B. Data Provenance and Inventory

## B.1 FlyWire FAFB v783

The FAFB materialisation is the FlyWire adult female brain connectome. The audit records 15 complete datasets, four incomplete downloads, 29,231,539 total rows, 368,874,372 compressed bytes, and 1,598,217,407 uncompressed bytes. The filtered connection table has 5,342,446 rows and 3,732,460 unique directed pairs, each pair being the sum of `syn_count` across neuropils for one `(pre_root_id, post_root_id)` pair. The pair-level synapse total is 50,666,648, with minimum 5, median 8, mean 13.575, 95th percentile 38, 99th percentile 87, and maximum 2,633. There are 620,180 directed reciprocal pairs and 671 isolated nodes. The processed artifact `connectome.npz` is 28,013,212 bytes with SHA-256 `3f568f24…5f33d8`; it is treated as read-only.

The audit is explicit about provenance limits. The version is inferred as v783 from an incomplete download filename, not attested by the completed files; no download log or source URL is stored with the files; and the audit recommends confirming the release and DOI before publication. The paper therefore cites the dataset version [4] and reports the audit's caveat rather than presenting the version as independently confirmed.

**Table B1.** FAFB node composition by `super_class`, in neurons. These are annotation counts from the published node table, not functional assignments made here. Source: `datasets/processed/` node annotations summarised in the connectome reports.

| `super_class` | Neurons |
|---|---:|
| optic | 77,873 |
| central | 32,381 |
| sensory | 16,938 |
| visual_projection | 7,684 |
| ascending | 1,750 |
| descending | 1,305 |
| sensory_ascending | 612 |
| visual_centrifugal | 522 |
| motor | 110 |
| endocrine | 80 |

Of 139,255 neurons, 119,597 carry annotations and 19,658 have a missing neurotransmitter label. The FAFB volume is brain-only: it contains 110 neurons annotated as motor, but no limb motor neurons, so it cannot supply a brain-to-muscle pathway. This is why the motor stage was rebuilt on BANC.

## B.2 BANC v888

The BANC export begins with 188,508 metadata rows. Sixteen thousand and seventy-five metadata-only rows are excluded, leaving 172,433 endpoint nodes. The original edge table has 11,752,828 edges; 156,311 self-edges (carrying 1,422,866 self-loop synapses) are removed, leaving 11,596,517 non-self edges. Three synapse-count thresholds are materialised, and the five-synapse graph is the primary substrate.

**Table B2.** BANC v888 threshold sensitivity. "Retention" is relative to the non-self edge list. Source: `datasets/processed/banc_v888/banc_construction_report.json`.

| Threshold | Directed edges | Summed synapses | Isolated nodes | Mean synapses per edge | Max synapses per edge |
|---|---:|---:|---:|---:|---:|
| t1 (≥1) | 11,596,517 | 34,310,230 | 6,232 | 2.9587 | 913 |
| t5 (≥5) | 1,535,710 | 18,552,546 | 24,320 | 12.0808 | 913 |
| t10 (≥10) | 570,721 | 12,397,230 | 62,551 | 21.7220 | 913 |

The t5 graph retains 13.2429% of non-self directed pairs and 54.0729% of non-self synapses. Annotation coverage is uneven and is reported rather than filled: `super_class` 88.069%, `cell_type` 68.2045%, `side` 91.7429%, `body_part_effector` 0.5968%, and `proofread` 100%. A neurotransmitter label exists for 89.27% of nodes when predictions are admitted, but only 37.87% when restricted to verified labels. Under the primary verified-only policy, 683,100 of 1,535,710 t5 edges (44.48%, 8,426,168 synapses) carry a sign; 852,610 edges are excluded.

**Table B3.** BANC `super_class` composition, in nodes. Source: `datasets/processed/banc_v888/banc_nodes.csv.gz`.

| `super_class` | Nodes |
|---|---:|
| optic_lobe_intrinsic | 72,826 |
| central_brain_intrinsic | 31,347 |
| unannotated | 20,573 |
| sensory | 15,956 |
| ventral_nerve_cord_intrinsic | 12,850 |
| visual_projection | 7,284 |
| glia | 6,281 |
| ascending | 1,849 |
| descending | 1,316 |
| motor | 805 |
| sensory_ascending | 514 |
| visual_centrifugal | 470 |
| visceral_circulatory | 221 |
| trachea | 83 |
| not_a_neuron | 40 |
| sensory_descending | 13 |
| ascending_visceral_circulatory | 5 |

Sixteen degree- and sign-preserving null graphs were constructed and certified, one per campaign seed, sharing the same 1,535,710-edge count. They are recorded as constructed infrastructure. No automated arm used one; the G3 memory deviation is recorded because the graphs were generated below the 4 GB gate.

## B.3 Detector dataset and model

The detector dataset is Roboflow v15: 2,328 images, 2,328 label files, 8,666 bounding boxes, and 14 classes, drawn from five recording groups. The official split is 1,825 training and 503 validation images with no test split. Twelve label files are empty. Of 1,724 adjacent frame pairs, 554 (32.1%) cross the official split boundary, and 224 near-duplicate images exist, 58 of them across the boundary. A sequence-grouped re-split was therefore constructed at 1,188 training and 1,128 validation images; no independent test set exists in either split.

The deployed detector is a YOLO11n exported to ONNX, 10,636,871 bytes, SHA-256 `e6ad18f9…6aa77`, input `[1, 3, 640, 640]` float32 NCHW, output `[1, 18, 8400]`, with confidence 0.426 and NMS IoU 0.7. Its reported validation metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, mAP50-95 0.687726 — were produced during training outside this repository and are reported as provenance, not re-measured. The metrics are computed on the curated validation split, not on an independent test set.

## B.4 Controlled game

The game is the standalone `endless-surfer` implementation, not the commercial Subway Surfers application. Its declared constants are a 900-step cap, initial speed 7.0, maximum speed 16.0, coin reward +1.0, collision penalty −1.0, survival reward +0.01 per step, obstacle reward 0.0, and a 25.0-unit observation horizon in normalised game-world units. The reward is a synthetic task scalar, not a dopamine measurement.

## B.5 Dataset separation

FAFB v783 and BANC v888 are separate graphs with separate identifiers and separate annotations. They are never merged, joined, or cross-referenced at the level of individual neurons. FAFB supplies the brain graph used in the perception and propagation studies; BANC supplies the brain-plus-ventral-nerve-cord graph used from Phase 4 onward because it contains motor neurons. The Male CNS dataset is reference-only. The detector dataset and the game code are third-party materials with their own licences, recorded in `THIRD_PARTY_NOTICES.md`.

---

# Appendix C. Model and Simulation Parameters

Every value below is a declared modelling parameter. None is a measured membrane property, conductance, or biological learning constant.

## C.1 Neuron model

The membrane follows

C_m dV/dt = −g_L (V − E_L) + I(t),  (C.1)

integrated with the exact exponential-Euler step

V(t + dt) = E_L + (V(t) − E_L + I/g_L) e^{−dt/τ_m} − I/g_L,  (C.2)

with τ_m = C_m/g_L, followed by threshold, reset, refractory, and floor rules.

**Table C1.** Leaky integrate-and-fire parameters. All values are assumed, not measured in this project. Source: `configs/neuron_config.yaml`.

| Parameter | Symbol | Value | Unit |
|---|---|---:|---|
| Membrane capacitance | C_m | 200 | pF |
| Leak conductance | g_L | 10 | nS |
| Membrane time constant | τ_m | 20 | ms |
| Resting potential | E_L | −65 | mV |
| Threshold | V_th | −50 | mV |
| Reset potential | V_reset | −68 | mV |
| Refractory period | — | 2 | ms |
| Membrane floor | — | −90 | mV |
| Rheobase, steady state | — | 150 | pA |
| Timestep | dt | 0.5 | ms |

The rheobase is derived, not fitted: 15 mV × 10 nS = 150 pA. The floor at −90 mV represents unmodelled leak and voltage-gated currents and exists to keep the state finite under sustained inhibition.

## C.2 Synapses, signs, and weights

Synaptic events are exponential currents with separate excitatory and inhibitory time constants, a uniform delay rounded to whole timesteps, and a sparse CSR representation. The weight transformation is

w_FAFB = 12 · count^{0.75} pA,  (C.3)

w_BANC = min(5.0 · count^{0.75}, 300) pA,  (C.4)

where `count` is the integer pair-level synapse count. Equation (C.4) makes an edge with 20 synapses contribute about 47 pA, roughly one third of rheobase, so temporal summation is required to fire.

**Table C2.** Synapse and sign-policy parameters. Source: `configs/simulation_config.yaml`, `configs/banc_synapse_policy.yaml`.

| Item | Value | Status |
|---|---|---|
| FAFB weight transform | 12 · count^{0.75} pA | calibration |
| BANC weight transform | min(5.0 · count^{0.75}, 300) pA | calibration |
| Excitatory decay | 5 ms | assumed |
| Inhibitory decay | 8 ms | assumed |
| Uniform delay | 1 ms | assumed |
| Acetylcholine, glutamate | excitatory | predicted transmitter |
| GABA, glycine | inhibitory | predicted transmitter |
| Dopamine, serotonin, octopamine, tyramine, histamine, nitric oxide | unknown / excluded | declared |
| Edges with no verified sign | excluded, zero current | 55.52% of BANC t5 edges |
| Verified-sign edges | 683,100 of 1,535,710 | 44.48%, 8,426,168 synapses |

Three sensitivity transforms are declared for the BANC weight policy — linear-capped, log1p, half-power, unit-power, and uncapped power — and the calibration grid is {0.5, 1.0, 2.0, 5.0, 20.0, 50.0} pA. The selection rule forbids choosing a scale on the basis of a decoder label; no such tuning was performed.

## C.3 Motor decoder

The decoder scores each motor pool over a half-open 50 ms window. The score is the active fraction of the population,

a_P(t) = |{i ∈ P : neuron i spiked in [t, t+50 ms)}| / |P|,  (C.5)

and a pool is eligible when it has at least 5 spikes and at least 3 active neurons. If any pool is eligible, the highest active fraction wins; ties are broken in the fixed order LEFT, RIGHT, JUMP. Otherwise the decoder returns NO_ACTION.

**Table C3.** Motor pools and decoder constants. Pool sizes are annotation counts, not functional assignments. Source: `configs/motor_decoder.yaml`, `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md`.

| Item | Value | Basis |
|---|---|---|
| LEFT pool | 185 neurons | left leg effectors |
| RIGHT pool | 186 neurons | right leg effectors |
| JUMP pool | 20 neurons | tergotrochanter extensor candidates |
| Unassigned motor neurons | 414 | never decoded |
| Total motor neurons | 805 | annotation |
| Window | 50 ms, half-open | declared |
| Activation threshold | 0.20 active fraction | declared |
| Release threshold (hysteresis only) | 0.10 | declared |
| Eligibility gate | ≥5 spikes and ≥3 active neurons | declared |
| Tie order | LEFT → RIGHT → JUMP | declared |
| ROLL, DUCK | unsupported | no annotation |

## C.4 Plasticity and sensory drive

The three-factor rule is

Δw_ij = η · M(t) · e_ij(t),  (C.6)

with an eligibility trace

e_ij(t) = λ e_ij(t−1) + f(pre_i, post_j), λ = exp(−dt/τ_e),  (C.7)

a decaying modulation

M(t) = clip(M(t−dt) e^{−dt/τ_M} + gain · r(t), −5, +5),  (C.8)

and bounds 0.5–2.0 times the initial weight, a 5 pA per-update cap, and a sign-flip abort. Only verified-sign edges are plastic.

**Table C4.** Plasticity and sensory-drive parameters. Source: `configs/plasticity_banc.yaml`, `configs/banc_sensory_mapping.yaml`, `configs/phase_8/conditions.yaml`.

| Parameter | Value | Status |
|---|---|---|
| Learning rate η, Phase 8 arms B and D | 0.5 | declared |
| Identity learning rate η, A′ and C′ | 0.0 | declared |
| Learning rate η, Phase 5F plastic condition | 1.0 | declared |
| Eligibility time constant τ_e | 20 ms | assumed |
| Modulation decay τ_M | 50 ms | assumed |
| Modulation gain and clip | 1.0, ±5 | declared |
| Weight bounds | 0.5–2.0 × initial | assumed |
| Maximum absolute update | 5 pA | assumed |
| Sensory current per active feature | 200 pA | declared |
| Pulse decay | 150 ms | declared |
| Mapped sensory neurons | 232 across 7 features | convention |

The 232 mapped neurons are: train_lane 48, obstacle_lane 48, obstacle_type 24, train_present 24, obstacle_present 24, train_distance 32, and obstacle_distance 32. Player pose and coin features are unmapped because the v15 event schema has no such fields. The mapping is a declared convention; no receptive-field map exists in the repository.

---

# Appendix D. Phase-by-Phase Implementation and Validation Evidence

## D.1 Recorded outcomes

**Table D1.** Phase-by-phase outcomes. "Status" reproduces the status recorded in the phase reports; "evidence class" is the paper's classification of what the result can support. Source: `tables/T07_phase_validation_summary.csv` and the individual phase reports.

| Phase | Objective | Key recorded result | Status | Evidence class |
|---|---|---|---|---|
| 0 | Audit the raw FAFB export | 11/11 audit and 8/8 round-trip checks | PASS | Data provenance |
| 1 | Build the connectome artifact | 139,255 nodes; 3,732,460 edges; 50,666,648 synapses | PASS | Data construction |
| 2 | LIF simulation on 800 neurons | 1,564 spikes; 79/800 active | PASS | Implementation test |
| 2.5 | Scale to the full graph | Full graph 138.3 steps/s; 349,846 spikes | PASS WITH LIMITATIONS | Benchmark |
| 3A | Map 14 features to 138 sensory neurons | Driven neurons spike | PASS WITH LIMITATIONS | Implementation test |
| 3A.5 | Calibrate the sensory operating point | 200 pA, σ 0.20, 4 neurons; 2/6/7 spikes; d′ 2.357 | PASS WITH LIMITATIONS | Implementation test |
| 3B.1 | Curate the detector dataset | 2,328 images; 8,666 boxes; 5 groups | PASS WITH LIMITATIONS | Data audit |
| 3B.2A | Perception architecture | Screenshot to GameState contract | PASS | Implementation test |
| 3B.2B.3 | Integrate YOLO11n ONNX | 2 of 13 smoke detections rejected by bounds | PASS WITH LIMITATIONS | Implementation test |
| 3B.2C | Replay 100 frames through perception and FAFB | 15,654,631 spikes; 25.84% active; 99.976% stimulated | PASS WITH LIMITATIONS | Instrumented replay |
| 3C | Temporal features and event scheduler | 50 synthetic sequences; continuity 0.944 | PASS (synthetic) | Implementation test |
| 4A | Dataset compatibility | 139,241 shared root IDs; 14 FAFB-only; 7 annotation-only | PARTIALLY COMPATIBLE | Data audit |
| 4B | Locomotor pathway investigation | No VNC motor neurons in FAFB | COMPLETE | Data audit |
| 4C.5 | BANC integrity audit | 172,433 endpoints | PASS WITH LIMITATIONS | Data audit |
| 4D | Construct the BANC graph | t5: 1,535,710 edges; five source hashes match | PASS WITH LIMITATIONS | Data construction |
| 4E | Motor populations and pathways | 805 motor; 1,316 descending; 1,849 ascending; 17,745 DN→MN t1 edges | PASS WITH LIMITATIONS | Structural analysis |
| 4F | Fixed motor decoder | 11 scenarios × 6 amplitudes | PASS WITH LIMITATIONS | Implementation test |
| 4G | Propagate through BANC and decode | Condition C: 1,296 spikes, 492 motor, JUMP ×4 | PASS WITH LIMITATIONS | Controlled simulation |
| 4H.4 | Sensory-to-motor round trip | 3,562 spikes, all stimulated; 0 motor | PASS WITH LIMITATIONS | Instrumented experiment |
| 5 | Reward, eligibility, three-factor rule | Synthetic task: plastic 0.945 vs fixed 0.795 | PASS (software); INCONCLUSIVE (biology) | Model experiment |
| 6 | Information-theoretic evaluation | Plastic − fixed cue→action MI = −0.0863 bits; p = 0.125 | NOT SUPPORTED | Archived-data analysis |
| 7 | Closed-loop game integration | Seed 42: 213 updates, 2,852 spikes, 0 motor | INTEGRATION PASS | Controlled simulation |
| 8 Pilot 1 | A-condition viability | 9 episodes; 73,880 spikes; 0 motor | EXECUTED; NOT FREEZE-READY | Pilot |
| 8 D5/D6 | Train F and Fβ readouts | 6 artifacts; 120/120 episodes; null behaviour | CERTIFIED | Pilot training |
| 8 Pilot 2-C | Floor and identity certification | 54/54 rows; A′ exact ×9; all arms motor-null | EXECUTED AND CERTIFIED | Pilot |

## D.2 Test-suite record

**Table D2.** Cumulative test-suite counts recorded at each phase boundary. These counts verify software behaviour; they are not biological evidence, and a passing test says nothing about whether a model claim is true. Source: `tables/T20_test_suite_summary.csv`.

| Phase boundary | Tests | Result | Note |
|---|---:|---|---|
| Phase 2 | 68 | passed | LIF, synapses, sampling, recorder, simulator, configs |
| Phase 4D | 331 | passed | Cumulative at BANC graph construction |
| Phase 4E | 345 | passed | Cumulative at pathway analysis |
| Phase 4F | 397 | passed | Cumulative at decoder development |
| Phase 4G | 440 | passed | Cumulative at BANC propagation |
| Phase 5G | 683 | passed | Cumulative at plasticity validation |
| Phase 6C | 748 | passed | Cumulative at MI analysis |
| Phase 6 final | 999 | passed, 3 skipped | Information analysis and integration |
| Phase 7 | 1,012 | passed, 3 skipped, 6 failed | Six pre-existing README-hash failures |
| Phase 8 D5/D6 | 530 | passed | After the pilot training path |
| Phase 8 Pilot 2-C | 531 | passed | After preflight blocker resolution |

The six Phase 7 failures are pre-existing and unrelated to Phase 7: three protected-hash checks report the README drift, two smoke-mode labels report `SMOKE INVALID` instead of `SMOKE ONLY`, and one C0 cache assertion fails. They are disclosed in the paper's deviation register (DEV-8) and were not suppressed.

## D.3 Interpretation rule

Every row in Table D1 that concerns software is an implementation test, including the 4F decoder matrix, the 4G propagation conditions, and the 5F synthetic task. Rows that concern executed model runs on the connectome — 3B.2C, 4H.4, Phase 6, Phase 7, Pilot 1, D5/D6, Pilot 2-C — are model-experiment evidence. None is physiological evidence, and no row establishes that the model matches a living fly.

---

# Appendix E. Phase 6 Estimator Definitions and Declared Analysis

## E.1 Estimators

With log base 2, the plug-in entropy of a variable X over n complete observations is

Ĥ(X) = −Σ_x p̂(x) log₂ p̂(x),  (E.1)

and the plug-in mutual information is

Î(X;Y) = Σ_{x,y} p̂(x,y) log₂ [p̂(x,y) / (p̂(x) p̂(y))].  (E.2)

The first-order upward bias of Î for a table with k_x and k_y declared levels is reported, not removed:

B(k_x, k_y, N) = (k_x − 1)(k_y − 1) / (2 N ln 2).  (E.3)

The corrected value is max(0, Î − B) and is labelled a first-order correction, not a substitute for sample size. Normalised MI divides the raw Î by min(Ĥ(X), Ĥ(Y)) and is withheld when that denominator is at or below the declared entropy floor of 0.05 bits. The uncertainty coefficient divides by Ĥ(Y). Conditional MI is the sample-weighted mean of within-stratum estimates, with a minimum stratum size of 50 observations.

## E.2 Declared inference and support rules

**Table E1.** Phase 6 declared analysis constants. Source: `configs/phase_6_information.yaml`.

| Item | Value |
|---|---|
| Log base | 2 |
| Confirmatory minimum observations | 100 |
| Confirmatory minimum clusters | 10 |
| Minimum clusters for an interval | 3 |
| Minimum expected observations per cell | 5 |
| Minimum marginal entropy for normalised MI | 0.05 bits |
| Minimum observations per conditional-MI stratum | 50 |
| Confirmatory permutations | 5,000 |
| Exploratory permutations | 2,000 |
| Permutation scheme | Cluster-preserving block, when observations share a run, seed, or replicate |
| Bootstrap resamples | 2,000 |
| α | 0.05 |

The only confirmatory family is the pair of paired plastic-versus-fixed contrasts in Phase 5F, complete and random wiring, with Holm correction over m = 2. Everything else is exploratory or descriptive and is labelled as such in the results.

## E.3 Confirmatory and exploratory values

**Table E2.** Phase 6 recorded estimates. Confirmatory rows are the declared family; the remaining rows are exploratory or descriptive and carry no inferential claim. Source: `experiments/results/phase_6/information_analysis.json`; `tables/T08_phase6_information.csv`.

| Endpoint | Estimate | Uncertainty | Decision |
|---|---|---|---|
| Cue→action MI, complete wiring, plastic − fixed | −0.0863 bits | 95% CI [−0.1751, 0.0052]; exact p = 0.125 | Not rejected; Holm 0.250 |
| Cue→action MI, random wiring, plastic − fixed | −0.0025 bits | 95% CI [−0.0075, 0.0000]; exact p = 1.000 | Not rejected |
| Fixed complete wiring, checkpoint 160 | 0.6126 bits | descriptive | — |
| Plastic complete wiring, checkpoint 160 | 0.5262 bits | descriptive | — |
| Fixed random wiring, checkpoint 160 | 1.3547 bits | descriptive | — |
| Plastic random wiring, checkpoint 160 | 1.3522 bits | descriptive | — |
| Distance→population code, Phase 3A.5 | 1.5849625 bits (log₂ 3) | bias floor 0.3206; corrected 1.2644; p = 0.0278 | Exploratory |
| Neural pool→decoded action, Phase 4F | 1.1841 bits | floor 0.0459; corrected 1.1382; normalised 0.8128; p = 0.0005 | Descriptive, circular |
| Conditional cue→action MI, six conditions | 0.6040 bits | floor 0.0135; corrected 0.5905; p = 0.0005 | Exploratory |
| Marginal cue→action MI, pooled | 0.3841 bits | descriptive | Exploratory |
| Reward ablation B − A | −0.0605 bits | exact p = 0.5 | Exploratory, three pairs |
| Reward ablation B − D | −0.0486 bits | exact p = 0.5 | Exploratory, three pairs |

The checkpoint-0 paired contrast is exactly zero for both wiring conditions because the arms have identical weights at that checkpoint. That equality is a matched-control check, not a finding.

## E.4 Endpoints declared unavailable

**Table E3.** Phase 6 endpoints that could not be estimated from the archive, with the recorded reason. These are results about the archive, not failures to compute. Source: `configs/phase_6_information.yaml`.

| ID | Endpoint | Reason |
|---|---|---|
| U01 | Real-replay sensory→neural MI | The 3B.2C replay persists aggregate counts only; no per-neuron or per-frame arrays exist |
| U02 | Spike-train entropy | No archived run persists raw spike times at sufficient scale; available arrays are single trials with few spikes per neuron |
| U03 | Membrane-potential entropy | Membrane potentials were never persisted |
| U04 | Neural-level plasticity information | The Phase 5 BANC run stores three distinct spike hashes and one decoded-state sequence; repeats are deterministic, not independent |
| U05 | Neural-level reward modulation | No arm persists independent per-neuron activity |
| U06 | Cue→neural response | Per-episode cue spike count is the constant 8 and the total is 12 (11 or 12 in E); a constant cannot carry cue information |
| U07 | Neural→reward | Per-episode counts are constant in conditions A–F; no neural predictor of reward exists without inventing an observation |

---

# Appendix F. Phase 8 Statistical Design Details

## F.1 Contrasts and hypotheses

**Table F1.** Confirmatory contrasts, mapped hypotheses, and the interpretation each would license. Source: `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` sections 3, 5, and 7.

| ID | Contrast | Hypothesis | Licensed interpretation if significant |
|---|---|---|---|
| C1 | F − A | H3 | A readout over the fixed substrate beats the fixed decoder |
| C2 | B − A | H1 | Three-factor plasticity changes survival on the biological substrate |
| C3 | A − C | H2 | Biological topology outperforms a degree- and sign-matched random graph |
| C4 | F − Fβ | Decoding gate | The readout uses motor information rather than a constant bias |

H1 ↔ C2, H2 ↔ C3, H3 ↔ C1. H4 (E-matched above floor) is an explanatory reference and is not in the Holm family. H5, the interaction (B − A) − (D − C), is exploratory. H6, that every non-NO_ACTION action is preceded by a matching motor spike, is descriptive. Neither H5 nor H6 can be promoted to confirmatory status after seeing data.

## F.2 Primary outcome and smallest effect of interest

The primary outcome is the capped survival score

Y = min(observed updates, 900),  (F.1)

averaged over the K = 10 evaluation episodes within a seed, so the seed is the independent unit. The smallest effect of interest is 100 updates, about 11% of the cap and about 1.5 times the three-seed random-agent standard deviation of 67.3 updates. It is a declared convention: the obstacle cadence was not measured, so no behavioural distance was derivable.

## F.3 Pairing and random streams

Episode j of seed s uses the environment seed derived from master seed 20261116 and the `(s, j)` pair, independent of condition. Four separate streams — environment, network, learning, and structure — are derived from the same master seed. The environment and structure streams omit the condition because pairing requires a shared environment and one graph per seed; the network and learning streams include it. Reusing one stream across purposes is forbidden. Each episode performs a full reset with no state carried between episodes.

## F.4 Sample-size rule

The primary design is N = 16 paired seeds. The N = 10 fallback is permitted only if

2.8016 · σ_max / √10 ≤ 100,  (F.2)

equivalently σ_max ≤ 112.87 updates, where σ_max is the pilot's largest paired standard deviation among C1–C4. Equation (F.2) is the normal-theory minimum detectable effect rearranged,

MDE = 2.8016 · σ_max / √N,  (F.3)

and is an approximation, not exact power for the sign-flip test. At N = 16 with an assumed σ of 60, the normal-theory MDE is about 42 updates and the Holm step-1 MDE is about 50 updates. The value 60 is an assumption placed between the Phase 7 random-agent and rule-based between-seed standard deviations; it is not a measurement. The N decision is made once, before the campaign. `design.n_seeds_selected` remained null after both pilots, so the campaign could not start.

## F.5 Exact sign-flip test

Let d_1 … d_N be the paired per-seed differences. The two-sided exact sign-flip p-value is

p = (1 / 2^N) · Σ_{ε ∈ {−1,+1}^N} 1[ |mean(ε_i d_i)| ≥ |mean(d_i)| ].  (F.4)

There is no Monte Carlo sampling and no normal approximation. At N = 16 there are 65,536 sign vectors and the minimum attainable two-sided p is 2/65,536 = 0.0000305176; at N = 10 there are 1,024 vectors and the minimum is 2/1,024 = 0.001953125. The minimum is attained by the extremal vectors `sign(d)` and `−sign(d)`. Holm correction is applied over m = 4 for C1–C4, so the step-1 threshold is α/4 = 0.0125.

A paired difference of exactly zero is retained and contributes nothing to any sign vector. If every difference is zero, every sign vector has the same statistic, p = 1.0 by construction, and the test is uninformative. The protocol required that this case be reported as "no power against a difference between two floored conditions", not as equivalence.

## F.6 Identity and integrity gates

A′ and C′ must reproduce A and C exactly on nineteen declared fields at η = 0, with no tolerance. On a mismatch, the corresponding plastic arm is marked invalid, its result is retained but excluded from aggregates, and the campaign stops. The protected 37-file baseline is checked before and after; the connectome fingerprint is asserted unchanged in A, C, and F; in B and D only the weight state may change, and the full digest chain is recorded.

---

# Appendix G. Pilot 1 Checks and the 72,880 / 73,880 Disclosure

## G.1 Arithmetic from the stored rows

**Table G1.** Pilot 1 row sums. Values are the stored per-episode fields, summed without modification. Source: `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`.

| Quantity | Row values | Sum |
|---|---|---:|
| Game updates | 323, 620, 323, 620, 426, 620, 213, 426, 213 | 3,784 |
| Neural steps | 10,767, 20,667, 10,767, 20,667, 14,200, 20,667, 7,100, 14,200, 7,100 | 126,135 |
| Total spikes | 4,764, 14,348, 4,764, 14,911, 8,396, 13,139, 2,850, 7,856, 2,852 | **73,880** |
| Motor spikes | 0 in all nine rows | 0 |
| Reward | 5.22, 10.19, 4.22, 7.19, 3.25, 8.19, 3.12, 4.25, 2.12 | 47.75 |

## G.2 The discrepancy

The Pilot 1 execution report's prose states a total of **72,880** spikes, and repeats that figure in its discussion of the zero-motor result. The nine stored rows sum to **73,880**. The difference is exactly 1,000 spikes, or 1.3537% of the row sum. It is a transcription error in prose: all nine rows are present, the other row-level fields are consistent with the run summary, and no episode value is missing or duplicated.

This paper uses 73,880 everywhere the Pilot 1 total is reported, including the abstract, Chapter 13, Table 16, Chapter 17, and Table 21. The historical report is preserved unmodified and is not silently corrected. The discrepancy is registered as DEV-1 in Table 22 and repeated in Appendix G so that a reader comparing the paper with the report sees the same rows and understands why the totals differ. No scientific claim in this paper depends on the difference: the load-bearing quantities are the zero motor spikes, the 3,784 NO_ACTION decisions, and the per-episode spike counts, all of which are identical in both records.

## G.3 Execution and integrity checks

**Table G2.** Pilot 1 recorded checks. Source: `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` and the pilot manifest.

| Check | Recorded value |
|---|---|
| Planned / executed / stored episodes | 9 / 9 / 9 |
| Complete | true |
| Evidence kind | pilot |
| Estimates contrasts | false |
| Merged into campaign | false |
| Wall time | 357.0 s, 10:58:51Z to 11:04:48Z on 2026-11-20 |
| Memory gate at start | 5.745 GiB available against 4.0 GiB |
| Passive memory samples | 177 at 2 s intervals |
| Maximum process RSS | 0.3725 GiB |
| Minimum system-available memory | 4.1997 GiB |
| Weight fingerprint | `4923f0cd…945d5`, identical before and after every episode |
| Truncated episodes | 0 |
| Protected-baseline match | 35 of 37 files |
| Protectable-baseline drifts | `README.md`; `motor/__init__.py` (commit `3c74ae8`, 2026-11-19) |
| Integrity result | `pass = false`; manifest `integrity.checked = false` |
| Freeze status | Not freeze-ready |

The drift was not created by the D2 implementation or by Pilot 1. It was not altered to make the pilot pass, and no restoration was performed. The episode rows remain valid measurements of the model; the protocol's publication gate is not passed.

---

# Appendix H. Motor-Bottleneck Measurements and Controls

## H.1 Structural funnel

**Table H1.** Signed structural reachability from the 232 stimulated sensory neurons under the verified-only sign policy. "First hop" counts targets of the stimulated set; "second hop" counts targets of the first hop. Source: `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`, a read-only analysis.

| Quantity | Count |
|---|---:|
| Stimulated sensory neurons | 232 |
| Signed outgoing first-hop edges | 662 |
| Distinct first-hop targets | 608 |
| Non-stimulated first-hop targets | 607 |
| Recurrent stimulated targets | 1 |
| First-hop targets that are motor neurons | 0 |
| Signed outgoing second-hop edges | 5,259 |
| Distinct second-hop targets | 3,865 |
| Non-stimulated second-hop targets | 3,576 |
| Second-hop targets that are motor neurons | 4 (2 JUMP; 0 LEFT/RIGHT) |
| Motor neurons with at least one signed incoming edge | 735 of 805 |

## H.2 Current and membrane at the first hop

**Table H2.** Recorded first-hop current and membrane values from the instrumented Phase 4H.4 run, which used the same seven frozen input hashes as Pilot 1. Source: `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`; Phase 4H.4 round-trip report.

| Quantity | Value |
|---|---:|
| Stimulated neurons that fired (Phase 4H.4) | 171 of 232 |
| Spikes recorded | 3,562, all from stimulated neurons |
| First-hop targets receiving current | 473 of 607 |
| Median first-hop current | 0 pA |
| 95th percentile first-hop current | 80.87 pA |
| Maximum first-hop current | 164.443 pA |
| Largest static signed first-hop sum | 167.041 pA (node 125949) |
| Rest potential | −65 mV |
| Threshold | −50 mV |
| Required depolarisation | 15 mV |
| Peak first-hop membrane | −56.926 mV |
| Peak depolarisation | 8.074 mV |
| Shortfall to threshold | 6.926 mV |
| First-hop neurons that fired | 0 of 473 |
| Second-hop current delivered | 0 pA |
| Descending-neuron maximum current | 67.208 pA |
| Descending-neuron peak membrane | −62.158 mV (12.158 mV short) |
| Ascending, second-hop, and motor neurons | 0 pA; −65 mV |
| Spike transmissions recorded | 25,332, of which 9,499 signed |

The current peak exceeds the 150 pA steady-state rheobase, but the current is transient: a 164 pA event with τ = 5 ms carries about 0.82 pC, or about 4.1 mV on a 200 pF membrane, and overlapping events reach the recorded 8.074 mV. That charge calculation is an order-of-magnitude consistency check, not a new measurement.

## H.3 Negative controls

**Table H3.** Phase 4H.4 control conditions. Every control produced zero non-stimulated spikes. Source: Phase 4H.4 report.

| Control | Result |
|---|---|
| Temporal shuffle | 0 non-stimulated spikes |
| Feature-identity shuffle | 0 non-stimulated spikes |
| Random matched mapping | 0 non-stimulated spikes |
| Constant matched charge | 0 non-stimulated spikes |
| 50 pA background + 50 pA noise | 0 non-stimulated spikes; closest neuron still 7.35 mV short |
| No-event baseline | 0 non-stimulated spikes |

## H.4 Positive controls on the decoder and motor tissue

**Table H4.** Positive controls showing that the decoder and motor populations can produce actions when driven directly. These demonstrate that the decoder is functional; they are not sensory pathways. Source: `reports/PHASE_4G_BANC_NEURAL_PROPAGATION.md`, `reports/PHASE_4G4_PROPAGATION_VALIDATION.md`.

| Condition | Total spikes | Motor spikes | Active motor neurons | Decoded action |
|---|---:|---:|---:|---|
| B, descending drive | 781 | 18 | — | NEUTRAL ×5 (all 18 in unassigned motor neurons) |
| C, 64 VNC intrinsic neurons at 300 pA | 1,296 | 492 | 82 | JUMP in 4 of 5 windows |
| D | 704 | 0 | 0 | NEUTRAL |
| E | 728 | 0 | 0 | NEUTRAL |

## H.5 What the bottleneck analysis does not establish

The first-hop values come from Phase 4H.4, not from Pilot 1's stored rows, which do not persist a per-neuron split or any membrane potential. The transfer rests on four convergent facts: byte-identical frozen inputs across seven hashes, the same production loop with zero background and zero noise, a structural query that reproduces the target set from the frozen graph, and a same-design replication in Phase 7 that persisted 2,852 stimulated spikes, zero non-stimulated spikes, and zero motor spikes. The values are a convergent inference about the same frozen model, not a per-neuron measurement of Pilot 1.

---

# Appendix I. D5/D6 Training and Checkpoint Record Schema

## I.1 Artifact layout

Each trained readout artifact occupies `experiments/results/phase_8/training/{condition}/seed_{evaluation_seed}/` and contains `training_run.json`, `manifest.json`, `parameters.npz`, and twenty checkpoint directories (`checkpoints/episode_001` … `episode_020`). For F/9001, the interrupted run's original provenance record is preserved as `training_run.incomplete_provenance.json`; the corrected record is `training_run.json`.

**Table I1.** Top-level sections of `training_run.json`. Source: `experiments/results/phase_8/training/F/seed_9001/training_run.json` and the D5/D6 report.

| Section | Contents |
|---|---|
| `kind`, `origin`, `evidence_kind` | `pilot_training_run`; `trained`; `experimental` |
| `condition_id`, `evaluation_seed`, `training_seed`, `pool_index` | Condition and B3 pairing identity |
| `identity` | Model kind, feature count (3), pool index, training seed |
| `authorisation` | D5/D6 paths and hashes, B3 digest, approval date, substrate, explicit non-authorisations |
| `frozen_inputs` | Seven frozen input paths |
| `master_seed`, `campaign_seed`, `init_seed` | Seed derivation record |
| `budget` | 20 episodes |
| `checkpoint_policy` | One checkpoint per completed episode; keep all intermediates and the final checkpoint; schema version 2 |
| `optimizer` | Optimizer state checkpointed; per-episode optimizer digests |
| `created` | UTC timestamp; Python 3.13.14, NumPy 2.3.4, PyTorch 2.10.0 |
| `digest` | Initial, state, and trainable parameter digests |
| `episodes`, `episodes_completed` | Twenty per-episode records |
| `checkpoints` | Twenty checkpoint ledger entries |
| `artifacts` | Manifest and parameter file names, sizes, SHA-256 |
| `provenance_correction` | Recovery ledger: equivalence report path and hash, re-verified checkpoints, corrected UTC |
| `limitations` | Declared scope limits |

## I.2 Episode record fields

**Table I2.** Fields recorded for each training episode. Source: `training_run.json` episode entries.

| Field | Meaning |
|---|---|
| `episode`, `steps`, `n_decisions` | Episode index, game updates, decoder decisions |
| `environment_seed`, `network_seed` | Derived seeds for the episode |
| `total_spikes`, `motor_spikes` | Network and motor-population totals |
| `action_counts` | Counts for LEFT, RIGHT, JUMP, NO_ACTION |
| `episode_reward`, `mean_return` | Reward scalar and mean return |
| `updates_applied`, `updates_after` | Readout updates applied and cumulative |
| `loss`, `policy_loss`, `value_loss`, `entropy`, `grad_norm` | Training diagnostics |
| `parameter_digest_before`, `parameter_digest_after` | Readout parameter digests |
| `state_digest_after` | Full readout state digest |
| `weights_before`, `weights_after` | Substrate weight fingerprint, unchanged |
| `behaviour_sha256` | Episode action/reward digest |
| `terminated`, `truncated`, `termination_reason` | Termination record |
| `substrate` | `biological_graph` |

## I.3 Checkpoint ledger

**Table I3.** Fields recorded for each checkpoint entry. Source: `training_run.json` checkpoint entries.

| Field | Meaning |
|---|---|
| `episode`, `directory` | Episode index and checkpoint path |
| `schema_version` | Checkpoint schema version (2) |
| `digest.state`, `digest.trainable`, `digest.optimizer` | State, trainable-parameter, and optimizer digests |
| `parameters_sha256`, `components_sha256`, `manifest_sha256` | File hashes for `parameters.npz`, `components.npz`, `checkpoint.json` |
| `rng_checkpointed`, `optimizer_state_checkpointed`, `environment_present` | State-capture flags |
| `integrity_verified`, `retained` | Verification and retention flags |

## I.4 Six artifacts and their pairing

**Table I4.** The six D5/D6 artifacts. Evaluation seeds are disjoint from training seeds and from the campaign seed list. Source: `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md`; `tables/T11_d5_training_artifacts.csv`.

| Condition | Evaluation seed | Training seed | Pool index | Init seed | Episodes | Parameter digest (state/trainable) |
|---|---:|---:|---:|---:|---:|---|
| F | 9001 | 1008 | 7 | 1350278753 | 20 | `bd50cc73…9a8883` |
| F | 9002 | 1014 | 13 | 3449218186 | 20 | `e1c25034…dadce` |
| F | 9003 | 1005 | 4 | 3297997184 | 20 | `2e188b78…d9961` |
| F_beta | 9001 | 1008 | 7 | 1849113230 | 20 | state `b9e5b6e3…7d712`; trainable `0975693e…1f76e` |
| F_beta | 9002 | 1014 | 13 | 992595534 | 20 | state `5842826f…a5b4e`; trainable `5f03c88b…ff5b9` |
| F_beta | 9003 | 1005 | 4 | 56964545 | 20 | state `409410cc…103f84`; trainable `b157ae1e…6ca120` |

All six are `origin = trained`, read-only, and were neither retrained nor substituted during Pilot 2-C.

## I.5 Recovery and equivalence

The F/9001 run was interrupted by a logging `KeyError` after episode 1. It was resumed, and the completed run was compared with an uninterrupted reference run at the same declared budget and seeds. The equivalence report records 20 compared episodes and 12 compared fields — `n_decisions`, `steps`, `updates_applied`, `updates_after`, `loss`, `mean_return`, `episode_reward`, `policy_loss`, `value_loss`, `entropy`, `grad_norm`, and `parameter_digest_after` — with zero differences and `equivalent = true`.

The original provenance record listed 19 of 20 checkpoints. It is preserved unmodified as `training_run.incomplete_provenance.json`, with SHA-256 `a385aabd…`. The corrected record `training_run.json`, SHA-256 `fd30434b…`, adds the missing ledger entry and re-verifies all twenty checkpoints. No parameter, digest, episode metric, or checkpoint byte changed. The correction is registered as DEV-3, and a regression test covers the ledger.

## I.6 Why the training was behaviourally null

The readout sees three motor active fractions. On a motor-silent substrate every feature is zero, so the feature vector is identically zero and the logits reduce to the bias. F's feature weights never receive a gradient because the input is zero, and Fβ's feature weights are fixed at zero by construction. Both biases start at zero and receive the same update under the same training seed, so the two conditions remain bit-identical in policy. Zero motor spikes were recorded in all 120 episodes, the substrate weight fingerprint never changed, and F and Fβ produced identical actions, rewards, and decision counts for every paired `(seed, episode)`.

---

# Appendix J. Pilot 2-C Claim Definitions and Identity Fields

## J.1 Authorisation binding

Pilot 2-C is bound to REV4 (`e4aa9e0f…1547c`), D3 (`74f11d2c…48df8`), and the Pilot 2-C amendment (`832ef485…67ad`). Its stage purpose is `floor_and_identity_certification`, its evidence kind is `pilot`, and its summary records `experimental_evidence = true` and `merged_into_campaign = false`. The grid is five neural arms and a substrate-free floor at three evaluation seeds and three episodes, 54 entries. No C, C′, or D arm was run; no randomized graph was read or substituted; no training occurred; `n_seeds_selected` was not written.

## J.2 Operational definition of each claim

**Table J1.** Pilot 2-C claims and the observation that would falsify each. All eight passed when recomputed from the 54 stored rows and the manifest. Source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json`.

| Claim | Operational definition | Falsifier |
|---|---|---|
| P2C-1 | Nine floor replays present; every decision NO_ACTION; motor spikes 0; weights null; `neural_substrate = none`; `spikes_read = false` | Any floor row with a non-neutral action, a spike, or a weight |
| P2C-2 | A′ equals A exactly on P1–P19 in 9/9; η = 0; changed edges 0; max |Δw| 0.0; one opening reset; zero in-episode resets | Any mismatch on any field, or any nonzero delta |
| P2C-3 | Fβ has zero nonzero feature weights; trainable set exactly `["bias"]`; identical logits for zero and saturated feature vectors; one action on every decision | A nonzero feature weight or any feature-dependent logit |
| P2C-4 | F has 12 nonzero feature-weight entries; weights frozen; parameter and feature-weight digests identical before and after every episode | A digest change, or zero feature weights (which would make F an Fβ replica by construction) |
| P2C-5 | Every neural episode records a per-decision motor block and a consistent motor-spike count; zero reported as zero | A missing block or an inconsistent count |
| P2C-6 | A′ reports exactly zero delta in all nine; B reports eligible edges, changed edges, maximum absolute delta, update reports, and hook calls for every episode; zero clamp hits; zero sign violations | An A′ nonzero delta, or a B episode without its attribution record |
| P2C-7 | Every row records seven input hashes, three config hashes, seed plan, evidence kind, stage purpose, and D3/amendment binding; F/Fβ rows add artifact condition, seeds, digests, and parameter-file hash | A missing hash or binding |
| P2C-8 | 54 planned, 54 stored, 0 missing, 0 error rows, every row schema-valid with a survival score; nothing skipped, retried, or substituted | A missing or error row, a retry, or a substitution |

## J.3 The nineteen identity fields

**Table J2.** The P1–P19 exact-comparison fields used by the A′ and C′ controls. Tolerance is none. Source: `experiments/phase_8/controls/equivalence.py` (REV4 section 3.8.3).

| Field | Requirement |
|---|---|
| P1 | Spike times, exact array equality |
| P2 | Spike neuron indices, exact array equality |
| P3 | Spike SHA-256 |
| P4 | Action and reward SHA-256 |
| P5 | Full record sequence, canonical JSON |
| P6 | Survival and termination summary |
| P7 | Action and decoder-state counts |
| P8 | Reward total and every component |
| P9 | Neural steps, neural time, game time |
| P10 | Motor activity per decision |
| P11 | Structural weight digest |
| P12 | Initial weight digest |
| P13 | Learned-delta digest and exact zero delta |
| P14 | Effective weight digest equals the initial digest |
| P15 | Maximum absolute weight change exactly 0.0 |
| P16 | Changed edges exactly 0 |
| P17 | Clamp hits and saturation count exactly 0 |
| P18 | Stepper weight fingerprint equal before and after |
| P19 | Resets during the episode |

All nine A′ pairs matched on all nineteen fields. The store-level reduced comparison — P3, P4, P6, P7, P8, P10, P12, and P14 — also reported no mismatch. The hard stop that would refuse an A′ episode on mismatch was never triggered, and B was not invalidated.

## J.4 Recorded attribution values

B ran at η = 0.5 with 683,100 eligible edges. Four of its nine episodes applied updates — 42, 45, 24, and 12 applied updates — and each changed exactly one edge. The maximum absolute delta was 0.03265 pA, the maximum applied update 0.01022 pA, and there were zero clamp hits and zero sign violations. Each neural arm recorded 3,784 decisions and zero decisions with a motor spike; the 50 ms motor window block was present in every episode. These are weight-level and accounting facts. They are not a behavioural effect, and the amendment forbids reading them as one.

## J.5 What the certification does not license

A passing P2C-1–P2C-8 certifies that the floor executes, that the plastic path is an identity at η = 0, that Fβ is provably constant, that F is wired and frozen, that motor activity is accounted for, that plasticity is attributable, that provenance is complete, and that the grid is viable. It does not certify learning, decoding, or behavioural competence. C1–C4 were not estimated; C2 is a structural zero; C3 is undefined; H1–H3 are unevaluable; H4 and H5 were not evaluated; H6 has no subject. σ_max and dispersion were not estimated, U7 remains open, and N remains the predeclared 16.

---

# Appendix K. Reproduction, Environment, and Frozen Hashes

## K.1 Software environment

**Table K1.** Recorded software versions. The project dependencies are pinned; the training artifact records the interpreter and numerical-library versions used for D5/D6. Source: `requirements.txt`, `datasets/manifest.json`, `training_run.json` creation block.

| Component | Version | Role |
|---|---|---|
| Python | 3.13.14 | Interpreter |
| NumPy | 2.3.4 | Numerical arrays, simulation core |
| pandas | 2.3.3 | Tabular analysis |
| Matplotlib | 3.10.7 | Figures |
| PyYAML | 6.0.3 | Configuration parsing |
| psutil | 7.1.2 | Memory instrumentation and gate |
| Pillow | 12.0.0 | Image loading for perception |
| onnxruntime | 1.29.0 | CPU ONNX detector backend |
| PyTorch | 2.10.0 | Linear readout and REINFORCE training |
| pytest | 7.4.3 | Test runner; anyio plugin disabled in `pytest.ini` |
| Platform | Windows 11 x64 | Recorded host platform |

The ONNX backend is CPU-only; no GPU package is installed. The full-graph simulation reaches 138.3 steps/s on this host with 134.7 MB retained, and the Phase 2.5 benchmarks record the scaling curve from 800 to 139,255 neurons.

## K.2 Read-only verification commands

The following entry points exist and write nothing. They reproduce checks, not experiments.

```bash
python -m experiments.phase_8.run_campaign --pretty check
python -m experiments.phase_8.run_campaign --pretty seeds --seed 1
python -m experiments.phase_8.run_campaign --pretty graphs --seed 1 --verify
python -m experiments.phase_8.stages.run_stage --list
python -m experiments.phase_8.stages.pilot2c evaluate
python -m pytest
```

`run_campaign check` reports conformance, approval, design resolution, certified graph count, and the memory preflight; while the approval and memory gates are unmet it returns `executable = false` and exit code 1. `pilot2c evaluate` recomputes P2C-1–P2C-8 from the stored rows and manifest and writes nothing else. `pytest` runs the repository suite under `pytest.ini`.

Executing a pilot, training job, or campaign is a different matter. It requires the applicable dated owner authorisation, the frozen protocol and amendment, and the 4.0 GB free-memory gate, and it is outside the scope of this paper. The authoritative reproduction of the executed runs is the stored artifacts themselves: the episode rows, manifests, summaries, certification records, and hashes listed in Appendix A and below. Re-running a simulation to "check" a reported value would create a new result, not reproduce the recorded one.

## K.3 Frozen input and configuration hashes

**Table K2.** Frozen input and configuration hashes recorded in every Pilot 2-C row. Source: `reports/PHASE_8_PILOT2C_EXECUTION_REPORT.md` section 9.2.

| Input | SHA-256 prefix |
|---|---|
| BANC graph, t5 | `6d47f259…e2192` |
| BANC node table | `144a2eb0…53e5f` |
| Neuron configuration | `9b652bde…8b77` |
| Synapse policy | `88f64492…dc399e` |
| Plasticity configuration | `616288a4…9e5f70` |
| Sensory mapping | `64c716a4…cdfc4ff` |
| Motor decoder | `525f25e9…0d9fae` |
| Campaign configuration | `b9a2d3d5…477e19` |
| Conditions configuration | `9a93f047…42f671` |
| Environment configuration | `b391ecf7…3281dc` |

## K.4 Protocol and authorisation hashes

**Table K3.** Protocol and authorisation hashes. Source: `reports/phase_8_owner_approvals/`, the execution preflights, and `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md`.

| Record | SHA-256 prefix |
|---|---|
| REV4 protocol (1,915 lines) | `e4aa9e0f…1547c` |
| Pilot 2-C amendment | `832ef485…67ad` |
| D1 approval | `5c183c99…d489` |
| D2 decision | `b5b0c229…7327` |
| D3 amendment decision | `74f11d2c…48df8` |
| D5 approval | `015598e8…bfe3f` |
| D6 record | `6a342504…d8325` |
| B3 training pairing digest | `bc231c79…1f980` |

## K.5 Resource and timing record

**Table K4.** Recorded resource and timing facts for the executed stages. These are host observations, not model properties. Source: execution reports and the Pilot 2-C preflight.

| Stage | Record |
|---|---|
| Pilot 1 wall time | 357.0 s |
| Pilot 1 peak process RSS | 0.3725 GiB |
| Pilot 1 minimum system-available memory | 4.1997 GiB |
| Pilot 2-C episode wall time | 3,458.8 s total; first row 03:37:44Z, last 04:35:36Z on 2026-11-23 |
| Pilot 2-C memory gate | 6.115 GB available against 4.00 GB, 60.1% used |
| Pilot 2-C longest episode | `F_beta:9001:0`, 1,653.9 s (47.8% of run wall time) |
| Next longest Pilot 2-C episode | 304.8 s |
| Full-graph simulation throughput | 138.3 steps/s |
| Full-graph retained memory | 134.7317 MB |

## K.6 Closing note on reproducibility

The project's reproducibility claim is narrower than "anyone can rerun this and get the same numbers". It is that every reported value is stored with its provenance, that the identity and accounting claims can be recomputed from the stored rows, and that the code paths that produced the values are pinned by configuration hashes and test suites. Where a value cannot be recomputed — because the relevant per-neuron state was not persisted, or because no independent test set exists — the paper marks it unavailable rather than reconstructing it.
