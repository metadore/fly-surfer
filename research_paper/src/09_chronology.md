# Chapter 9. Project Development and Experimental Chronology

## 9.1 Why the chronology is part of the evidence

The FLY-SURFER record is a sequence of gated phases, each with its own protocol, implementation, validation, and report. The sequence matters for two reasons. First, later phases were designed in response to earlier failures: the dataset switch to BANC, the motor decoder, the sensory-to-motor round trip, and the Phase 8 protocol all exist because an earlier attempt did not work. Second, the record preserves several deviations and one freeze-readiness failure that cannot be understood from a results table alone. This chapter reconstructs the sequence from the stored reports and execution records. It adds no experiment and changes no conclusion.

The chronology is also the place to state what was *not* done. The Phase 8 confirmatory campaign with N = 16 seed pairs was never executed. The paper reports a design, two pilots, and six trained artifacts, not a completed campaign. No commercial Subway Surfers process was controlled at any point; the game is a standalone open-source endless runner. No fly was recorded, stimulated, or observed.

## 9.2 Phase map

Table 11 is the phase-by-phase backbone, reproduced from the project's validation summary. It lists the objective, implementation, validation, status, key result, and test count for every phase that appears in this paper.

**Table 11.** Phase-by-phase implementation and validation summary. Statuses are the values recorded in the phase reports; "PASS WITH LIMITATIONS" is a recorded status, not an editorial softening. Test counts are cumulative full-suite counts at the time of the phase and are not independent samples. Data source: `reports/` phase reports and execution records; full machine-readable table in `tables/T07_phase_validation_summary.csv`.

| Phase | Objective | Implementation | Validation | Status | Key result | Tests |
|---|---|---|---|---|---|---|
| 0 | Audit the raw FAFB export | dataset audit | 11/11 audit, 8/8 round-trip | PASS | artifact trusted as read-only | — |
| 1 | Build the connectome artifact | `connectome.npz` | 139,255 nodes; 3,732,460 edges; 50,666,648 synapses | PASS | exact counts reproduced | — |
| 2 | LIF simulation over 800 neurons | LIF, sparse CSR synapses, recorder | 1,564 spikes; 79/800 active | PASS | recruitment inside the sample | 68 |
| 2.5 | Scalability to the full graph | benchmark suite | 800–139,255 neurons; stability checks pass | PASS WITH LIMITATIONS | 349,846 spikes at full size | — |
| 3A | Map game features to sensory populations | 14 features, 138 neurons | scripted scene protocols | PASS WITH LIMITATIONS | driven neurons spike; mapping is a convention | — |
| 3A.5 | Calibrate the sensory operating point | amplitude/sigma/population sweep | 200 pA, σ 0.20, 4 neurons; 2/6/7 spikes | PASS WITH LIMITATIONS | small threshold-sensitive code | — |
| 3B.1 | Curate the detector dataset | sequence-grouped split | 2,328 images; 8,666 boxes; 14 classes | PASS WITH LIMITATIONS | no independent test split | 6 |
| 3B.2A | Perception inference architecture | perception package + mock detector | screenshot → GameState contract | PASS | no accuracy claim | 38 |
| 3B.2B.3 | Integrate YOLO11n ONNX | ONNX runtime decoder | one image + five-image smoke slice | PASS WITH LIMITATIONS | 2/13 detections rejected by bounds | 13 new |
| 3B.2C | Replay 100 real frames | end-to-end replay | 15,654,631 spikes; 99.976% non-stimulated | PASS WITH LIMITATIONS | not a gameplay result | 12 checks |
| 3C | Temporal features and scheduler | tracker, lifecycle, scheduler | 50 synthetic sequences; 175/0/0 events | PASS (synthetic) | direction 0.996; continuity 0.944 | — |
| 4A | Check dataset compatibility | read-only audit | 139,241 shared IDs; 14 FAFB-only; 7 annotation-only | PARTIALLY COMPATIBLE | FAFB is brain-only | — |
| 4B | Investigate locomotor pathways | read-only pathway analysis | BANC motor/descending inventory | COMPLETE | no local VNC motor neurons in FAFB | — |
| 4C.5 | Audit BANC integrity | ID/edge/annotation audit | 172,433 endpoints | PASS WITH LIMITATIONS | read-ready with limits | — |
| 4D | Construct BANC graphs | `banc_graph.py` | t1/t5/t10; t5 1,535,710 edges | PASS WITH LIMITATIONS | 5 source hashes match | 20 focused / 331 total |
| 4E | Analyse motor populations | Phase 4E analysis | 805 motor; 1,316 descending; 1,849 ascending | PASS WITH LIMITATIONS | 17,745 direct DN→MN edges at t1 | 14 focused / 345 total |
| 4F | Build a fixed motor decoder | populations + `motor_decoder` | 11 scenarios × 6 amplitudes = 66 runs | PASS WITH LIMITATIONS | correct sets from 180 pA | 52 focused / 397 total |
| 4G | Propagate spikes and decode | BANC simulator + adapter | condition C: 1,296 spikes, 492 motor, JUMP ×4 | PASS WITH LIMITATIONS | positive control works; descending route does not | 140 focused / 440 total |
| 4H.4 | Sensory-to-motor round trip | archived event pulses → BANC | 3,562 spikes, all stimulated; 0 motor | PASS WITH LIMITATIONS | first hop does not spike | 47/47 config checks |
| 5 | Reward, eligibility, three-factor plasticity | plastic simulator; synthetic task | 10 seeds; plastic 0.945 vs fixed 0.795 | PASS (software); INCONCLUSIVE (biology) | conditioned response, not action selection | 186 focused / 683 total |
| 6 | Information-theoretic evaluation | entropy and MI estimators | plastic − fixed cue→action MI = −0.0863 bits; p = 0.125 | NOT SUPPORTED | no information gain from plasticity | 65 focused / 748 total |
| 7 | Closed-loop game integration | environment adapters + live loop | seed 42: 213 updates, 2,852 spikes, 0 motor | INTEGRATION PASS | NO_ACTION ×213; reward 3.12 | 19 focused; 1,012 passed / 6 pre-existing failures |
| 8 Pilot 1 | A-condition viability grid | production episode runner | 9 episodes; 73,880 spikes; 0 motor | EXECUTED; NOT FREEZE-READY | viability only; baseline drift | — |
| 8 D5/D6 | Train F and F-beta readouts | training engine + checkpointing | 6 artifacts; 120/120 episodes | CERTIFIED | behaviourally null training | 71 focused / 530 total |
| 8 Pilot 2-C | Floor and identity certification | Pilot 2-C runner | 54/54 rows; A′ exact ×9; all arms motor-null | EXECUTED AND CERTIFIED | C1–C4 and H1–H3 unevaluable | 531 total |

## 9.3 The first arc: connectome and simulator (Phases 0–2.5)

Phase 0 audited the raw FAFB export and its round-trip integrity. Phase 1 built the read-only connectome artifact used by every FAFB run: 139,255 neurons, 3,732,460 directed pairs after the ≥5 summed-synapse threshold, and 50,666,648 synapses. The artifact hash is `3f568f24…5f33d8`, and the arrays are described in Chapter 3. Phase 1's claim is narrow — exact counts were reproduced from the source export — and it does not claim that the thresholded graph is a physiological wiring diagram.

Phase 2 implemented the LIF neuron, sparse current-based synapses, a recorder, a simulator, and configuration validation, and ran an 800-neuron subset. It produced 1,564 spikes with 79 of 800 neurons active and passed 68 tests. Phase 2.5 scaled the same engine from 800 to the full 139,255 neurons. The full graph ran at 138.3 steps/s, retained 134.7 MB of simulation arrays, produced 349,846 spikes with 33,261 active neurons, and passed its stability checks. The phase also recorded the nonlinear scaling and the very high non-stimulated spike share at large subgraphs; Chapter 6 reports those measurements without attributing a mechanism.

The chronology of these two phases matters because they set the simulator's scope. The model was always a current-based LIF network over a structural graph, never a conductance-based or physiologically calibrated model. Later phases inherited that scope.

## 9.4 Perception and dataset work (Phases 3A–3C)

Phase 3A mapped 14 game features to 138 FAFB neurons and showed that scripted feature drive evokes spikes. Phase 3A.5 swept amplitude, input noise, and population size to pick a workable operating point: 200 pA, σ = 0.20, four neurons, producing spike counts of 2, 6, and 7 at three distances across three seeds. The counts were ordered at every seed, with a reported d′ of 2.357, but the amplitude and tuning searches fell back to declared defaults. The calibration therefore established a small, threshold-sensitive code, not an optimised encoder.

The perception side began with Phase 3B.1, which curated a 2,328-image detector dataset with 8,666 boxes and 14 classes, and produced a group-aware split. Phase 3B.2A defined the screenshot-to-`GameState` contract with a mock detector and made no accuracy claim. Phase 3B.2B.3 integrated a trained YOLO11n ONNX model and ran a one-image plus five-image smoke slice; two of 13 detections were rejected by bounds. Phase 3B.2C then replayed 100 real frames through perception, tracking, the sensory mapping, and the full FAFB graph. The replay produced 15,654,631 spikes, 99.976% of them from non-stimulated neurons, and ended at the sensory-injection stage with no action selection. Chapter 5 explains why that share is expected and why it is not evidence of network computation.

Phase 3C built and calibrated the tracker, the object lifecycle, and the temporal activation scheduler on 50 synthetic sequences, with 175 true positives, zero false positives, and zero false negatives. Those numbers are an implementation calibration on synthetic sequences. They are not detector performance on real video, and the paper labels them accordingly.

A parallel Phase 3 follow-up programme produced a frozen lane-encoding preregistration (P3-3C.5), a 42-instance pilot, and a recorded finding that one acceptance criterion in the earlier protocol revision was unsatisfiable. That work is documented in the repository. It is not part of the causal chain reported here, and this paper neither relies on it nor reinterprets it.

## 9.5 The dataset switch (Phases 4A–4H)

Phase 4A audited compatibility between FAFB and BANC. The decisive finding was that FAFB is a brain-only volume: it contains 110 motor-super-class neurons, none of them the limb motor neurons required for a walking or jumping readout, because the ventral nerve cord is absent. BANC contains 805 motor neurons, including leg effectors. Phase 4B confirmed the absence of local VNC motor neurons in FAFB and mapped the descending and ascending populations. Phase 4C.5 audited BANC identifiers, edges, and annotations and found the resource read-ready with limitations: 172,433 endpoint nodes after excluding metadata-only rows and self-edges.

Phase 4D constructed the BANC graph at three thresholds. At t5 the graph has 1,535,710 edges and 18,552,546 synapses; 683,100 edges (44.48%) carry a verified sign. Phase 4E analysed motor populations and pathways and found 805 motor neurons, 1,316 descending, and 1,849 ascending neurons, with 17,745 direct descending-to-motor edges at t1. Phase 4F built the three-pool decoder and characterised it on 11 scenarios at six amplitudes, with and without jitter. Phase 4G connected the decoder to the BANC graph and produced the positive control: driving 64 VNC intrinsic neurons recruited motor tissue and produced four JUMP windows, while descending candidates, random groups, and shuffled groups did not.

Phase 4H.4 then ran the actual seven-feature sensory mapping on BANC. It stimulated 232 neurons, obtained 3,562 spikes all in stimulated neurons, and recorded zero motor spikes. The first hop received weak current and the second hop received none. This is the pivot of the project: the decoder works when driven directly, but the sensory mapping does not deliver enough current to the motor pools. Chapters 7 and 14 treat the positive control and the null round trip as separate results and never merge them.

## 9.6 Plasticity and information (Phases 5 and 6)

Phase 5 built the reward scheduler, the eligibility traces, the three-factor rule, the synthetic cued-response task, and the comparative evaluation. Chapter 8 reports the results. The chronology point is that the entire Phase 5 programme ran on synthetic graphs of tens of nodes; no BANC edge was read, modified, or simulated. The 0.945 versus 0.795 success comparison is a result about the rule and the task, not about the connectome.

Phase 6 then analysed archived Phase 3, 4, 5 artifacts for entropy and mutual information. The only confirmatory family was two paired plastic-versus-fixed contrasts. Both were null: the complete-wiring contrast was −0.0863 bits (p = 0.125, Holm 0.25), and the random-wiring contrast was −0.0025 bits with nine exact zeros (p = 1.0). The analysis also declared three endpoints unavailable rather than approximating them. Chapter 10 reports the full result, including the dissociation between the Phase 5 success increase and the absence of an information increase.

## 9.7 Closed loop (Phase 7)

Phase 7 integrated the standalone game with the Phase 3 observation schema, the Phase 4 motor adapter, and the Phase 5 reward interface. It ran fixed-seed demonstrations with a random agent, a rule-based agent, a recorded Phase 4 replay, and a live neural loop. The live loop advanced 213 game updates over 7,100 neural steps, recorded 2,852 spikes all in stimulated neurons, and produced zero motor spikes. All 213 decoded states were NO_ACTION. The weights were unchanged by SHA-256.

The Phase 7 report also records a pre-existing repository condition: the full suite had six failures on README hash pins. Those failures are disclosed in the deviations register and are unrelated to the game integration. The paper uses them as a fact about the repository state, not as a result.

## 9.8 Phase 8 design and authorization (REV3 → REV4 → D1–D6)

Phase 8 was designed as a confirmatory campaign with controls, a pre-registered contrast family, and a fixed analysis plan. The protocol went through REV3 and a REV4 revision that resolved seven residual ambiguities without changing any hypothesis, contrast, outcome, seed count, α, SEI, K, cap, or coefficient. REV4's hash is `e4aa9e0f…1547c`; a later amendment, `832ef485…667ad`, defines Pilot 2-C.

The campaign design declares six conditions A–F, three controls A′, C′, Fβ, an F-init refinement, and a floor condition; four contrasts C1–C4; three hypotheses H1–H3 with Holm correction over m = 4; a primary outcome of min(updates, 900); N = 16 seed pairs (N = 10 if the pilot variance is low enough); K = 10 episodes; a master seed of 20261116; and an exact sign-flip test whose minimum attainable p is 2/65,536 at N = 16 and 2/1,024 at N = 10. Chapter 12 describes the design.

Execution was gated by six owner decisions, D1 through D6, each recorded with an approval identifier and date. D1 and D2 authorized specific stages; D3 amended Pilot 2-C; D4 bound the training contracts; D5 and D6 authorized the six training artifacts and the Pilot 2-C grid. The gates were not bypassed: when the Pilot 2-C preflight refused because the global training gate was unsatisfied, the refusal was recorded and resolved through a recorded decision rather than by weakening the gate.

## 9.9 The execution arc (2026-11-20 to 2026-11-23)

Pilot 1 executed nine episodes on 20 November 2026. It produced 3,784 updates, 126,135 neural steps, and 73,880 spikes, with zero motor spikes, and ended at the reward-conditioned A arm. Its execution report is explicitly not freeze-ready: two of 37 protected files drifted from their recorded pins, and the run manifest could not check the baseline at run time. The drift predates the pilot and was not caused by it. The motor-bottleneck investigation of the same date analysed the saved run without simulating anything and found that the first-hop current peaked at 164.443 pA, delivering a peak membrane potential of −56.926 mV against a −50 mV threshold, 6.926 mV short, with zero second-hop current and zero of 473 current-receiving targets firing.

On 23 November the six D5/D6 training artifacts were executed: F and F-beta readouts for seeds 9001, 9002, and 9003, each for 20 episodes and 20 checkpoints. All 120 episodes ended in collision with zero motor spikes and no weight change. The F/9001 artifact's resume ledger required a provenance correction; the original record was preserved and a regression test was added. Pilot 2-C then executed all 54 rows of the amended grid: six arms (A, B, F, Fβ, A′, floor) × three seeds × three episodes. Survival scores were identical across arms, A′ reproduced the fixed-weight reference exactly on the declared 19 fields, and all eight P2C claims passed certification. Certification is a statement about the machinery; it is not evidence of learning.

The chronology ends before the N = 16 confirmatory campaign. That campaign was not executed, and the paper does not report its contrasts as results.

## 9.10 Validation history

Table 12 lists the cumulative test-suite counts at each major gate. The counts are not independent evidence: each later suite contains the earlier tests, and the same test can appear at several gates. They are useful as a record of when the software was checked and what was known at the time.

**Table 12.** Cumulative test-suite counts at major gates. Counts include tests inherited from earlier phases. The Phase 7 row includes six pre-existing README-hash failures that are unrelated to the integration. Data source: phase reports and `reports/PHASE_5_FINAL_ASSESSMENT.md`; full machine-readable table in `tables/T20_test_suite_summary.csv`.

| Phase | Tests | Status | Note |
|---|---:|---|---|
| Phase 2 | 68 | passed | LIF, synapses, sampling, recorder, simulator, configs |
| Phase 4D | 331 | passed | full suite at BANC graph construction |
| Phase 4E | 345 | passed | full suite at pathway analysis |
| Phase 4F | 397 | passed | full suite at decoder development |
| Phase 4G | 440 | passed | full suite at BANC propagation |
| Phase 5G | 683 | passed | full suite at plasticity validation |
| Phase 6C | 748 | passed | full suite at MI analysis |
| Phase 6 final | 999 | passed, 3 skipped | information analysis and integration |
| Phase 7 | 1,012 | passed, 3 skipped, 6 failed | six pre-existing README-hash failures |
| Phase 8 D5/D6 | 530 | passed | after pilot training path |
| Phase 8 Pilot 2-C | 531 | passed | after preflight blocker resolution |

The drop from 1,012 at Phase 7 to 530 at Phase 8 D5/D6 is not a regression in coverage. The Phase 7 count includes a different collection and the six README failures; the Phase 8 counts come from the suites run for the training path. The paper reports the values as recorded and does not reconstruct a single monotone series.

## 9.11 What the chronology shows

Three patterns run through the record. First, the project repeatedly narrowed its claims rather than widening them: from a connectome simulation to a structural simulation, from a 14-feature FAFB encoder to a 7-feature BANC mapping, from a conditioning task to a pilot, and from a campaign to a design. Second, every failure is preserved: the negative Phase 5C wall-clock benchmark, the Phase 4H.4 null round trip, the Phase 6 null information contrasts, the Phase 7 zero-motor loop, the Pilot 1 freeze-readiness failure, and the behaviourally null training. Third, the machinery was tested far more thoroughly than the science was confirmed. That asymmetry is the project's actual state, and the remaining chapters report it without repairing it.
