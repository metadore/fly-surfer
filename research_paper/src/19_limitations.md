# Chapter 19. Limitations and Threats to Validity

## 19.1 What this chapter covers

The limitations of FLY-SURFER are not a single list appended to the results. They operate at different levels: some concern whether the model measures the construct it claims to measure, some concern whether the comparisons are internally valid, some concern whether the findings generalise, some concern the statistical design, and some concern the documentation itself. This chapter separates those levels, then reports the recorded deviations and the consolidated limitations register. It does not propose fixes; the future questions in Chapter 21 state what would be required to address each limitation, and the execution boundaries of the programme forbid changing a frozen parameter or protocol in response to a result.

## 19.2 Construct validity: what the model measures

The most fundamental limitation is that structural connectivity is not physiological connectivity. An edge in FAFB or BANC reports synapses between identified neurons; it does not report conductance, reversal potential, short-term dynamics, or whether the synapse is excitatory or inhibitory in a particular behavioural state. Every propagation result in this paper is therefore a statement about a graph plus a declared model, not a measurement of information flow in a fly.

The sign policy makes the gap concrete. On BANC t5, only 44.48% of edges, 683,100 of 1,535,710, receive a verified sign under the declared policy; the remaining 55.52% are excluded from simulation. A structurally present path can therefore carry no modelled current, and the model's effective graph is sparser than the anatomical graph. The exclusion is conservative and declared, but it means that the measured first-hop current is a lower bound under this policy, not an estimate of biological current.

The weight transform is another declared choice. FAFB weights are 12 · count^0.75 pA and BANC weights are min(5.0 · count^0.75, 300) pA, with exponential synapses of 5 ms excitatory and 8 ms inhibitory decay and a uniform 1 ms delay. No measurement fixes the scale, the exponent, or the cap. The transform was chosen to place currents on a workable scale, not fitted to electrophysiology. The 164.443 pA peak first-hop current and the 6.926 mV shortfall are properties of this transform.

The neuron model is a single uniform LIF parameter set: C = 200 pF, g = 10 nS, τ = 20 ms, V_rest = −65 mV, V_th = −50 mV, V_reset = −68 mV, a 2 ms refractory period, a −90 mV floor, and a 0.5 ms timestep. It has no cell-type-specific physiology, no adaptation, no bursting, and no morphology. Inhibition is a hyperpolarising current rather than a conductance, so there is no shunting inhibition and no reversal potential. These choices make the simulation tractable and auditable, but they also mean that the first-hop shortfall could be an artefact of the parameterisation. The paper reports the shortfall as a property of the model, not as a fact about the fly.

The sensory mapping is a convention. Seven features are mapped onto 232 identified BANC sensory neurons, with 48 neurons for train lane, 48 for obstacle lane, 24 for obstacle type, 24 for train presence, 24 for obstacle presence, 32 for train distance, and 32 for obstacle distance. Player pose and coins are not mapped. The assignments are computational hypotheses, including those whose pools come from published annotations. There is no receptive-field map, and the mapping's adequacy has not been measured against optic-lobe physiology.

Finally, the motor labels are annotation-derived. LEFT, RIGHT, and JUMP are decoder-defined pools of 185, 186, and 20 neurons, with 414 unassigned motor neurons; ROLL and DUCK are unsupported. A decoder label is not an identified motor command, and the positive control that drives the pools directly is a test of the decoder, not a demonstration of a biological motor code.

## 19.3 Internal validity: whether the comparisons support their claims

The programme's strongest internal-validity safeguard is that its confirmatory family was declared before estimation. Phase 6 fixed two paired plastic-versus-fixed contrasts and applied an exact two-sided sign-flip test with Holm correction over that family. The result was not rejected, and the paper does not reinterpret an exploratory endpoint as confirmatory.

Sample size is the main internal limitation. The Phase 6 confirmatory contrasts use ten seeds and forty held-out episodes per arm. The exploratory sensory-coding endpoint uses nine observations in three clusters, with about one observation per table cell; the identical response across mapping seeds means the effective replication is three, not nine. The population-size sweep shares one mapping seed and is a sensitivity analysis, not an independent replication. The neural-to-motor endpoint uses 330 windows nested in 66 runs and is circular because the decoder thresholds the same pool activity used as the predictor. The reward-ablation contrasts have three matched replicates, and with three pairs the smallest attainable two-sided p is 0.25, so no contrast can approach significance. These design facts bound every conclusion, and the paper labels the endpoints exploratory or descriptive accordingly.

The Phase 8 pilots are not campaign evidence. Pilot 1 has three seeds and three episodes; Pilot 2-C has three seeds and three episodes per arm; D5 has twenty training episodes per artifact. None estimates a contrast, and the pilot grid's motor silence makes C1, C2, and C4 degenerate and C3 undefined. The N = 16 confirmatory campaign was not executed, no value of `n_seeds_selected` was written, and the exact sign-flip test's minimum p-value at N = 16, 2/65,536, remains a design property rather than an achieved result.

The F/F_beta identity is a further internal limitation. The two conditions were intended to differ in whether the readout uses motor information. In the executed grid they did not differ behaviourally, because the motor feature vector was always zero. The certification confirms the wiring difference, but the experiment cannot discriminate the conditions' behavioural consequences. This is not a flaw in the controls; it is a limitation of running them on a motor-silent substrate.

## 19.4 External validity: whether the findings generalise

The controlled environment is a standalone endless-runner implementation, not the commercial Subway Surfers game. The commercial game was never instrumented, controlled, or played. Results about collision timing, coin collection, and survival in this environment do not transfer to the commercial product, and the paper does not claim that they do.

The substrate is also specific. FAFB and BANC are separate reconstructions and were not merged; FAFB is brain-only and contains no limb motor neurons, which is why the motor stage uses BANC. The BANC graph was thresholded at five synapses, retaining 1,535,710 of 11,596,517 non-self edges and 18,552,546 of 34,310,230 synapses, or 13.2429% of pairs and 54.0729% of synapses. A different threshold would produce a different graph and possibly a different first-hop current.

The detector was trained outside the repository, and its published metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, mAP50-95 0.687726 — are provenance, not re-measured results. The dataset has no independent test set: the curated split provides 1,188 training and 1,128 validation images, and 554 of 1,724 adjacent pairs (32.1%) cross the official split, with 224 near-duplicates, 58 of them across splits. The perception results are therefore bounded by a validation set that is not fully independent of training.

The parameter set is uniform across all neurons and all phases. A different LIF parameterisation, a different weight exponent, or a conductance-based inhibitory model could change the first-hop result. The paper does not generalise the shortfall beyond the tested operating point, and it does not claim that the connectome is incapable of supporting behaviour.

## 19.5 Statistical validity

The statistical design is conservative. Phase 6 reports the analytic bias floor rather than removing it, uses cluster-preserving block permutation and a cluster bootstrap, and applies an exact sign-flip test to the ten-pair contrasts with Holm correction. The observational unit is the seed or run, never the timestep or episode. The paper does not treat deterministic repeats as independent replicates.

The limitations are those of the data, not the tests. A non-significant exact test does not establish the null; it fails to reject. The Phase 6 estimate of −0.0863 bits has a descriptive interval that includes zero, and the paper reports the point estimate and the interval rather than a binary verdict alone. The exploratory p-values, such as 0.0278 for the sensory-coding endpoint and 0.0005 for the neural-to-motor endpoint, are reported with their design caveats: one observation per cell in the first case, circularity in the second. The Holm correction applies only to the declared confirmatory family; it does not license inference on exploratory endpoints.

The Phase 8 design fixed a smallest effect of interest of 100 updates, an N = 16 primary sample with an N = 10 fallback if σ_max ≤ 112.87, four seed streams, K = 10, and a primary outcome of min(updates, 900). None of those quantities was estimated from data because the campaign did not run. The minimum attainable p-value and the MDE are design properties, not achieved power.

## 19.6 Documentation and evidence-status limitations

The programme maintains a strict evidence vocabulary, and several limitations follow from it. An implementation test checks software behaviour on fixtures or synthetic inputs; it is not biological evidence. A pilot is an authorised small execution, not a confirmatory campaign. A certification PASS concerns artifact identity, schema, pairing, and recovery; it is not evidence of biological learning. The paper applies those labels consistently, which means that many results that might be read as successes are explicitly not scientific successes.

The documentation also contains known discrepancies, disclosed rather than repaired. The Pilot 1 report's prose total is 72,880 spikes while the nine rows sum to 73,880. The original report is preserved; the paper uses 73,880. The F/9001 training artifact required a provenance correction; the original bytes are preserved beside the corrected record. The Pilot 2-C floor rows have different action digests from the neural rows while their outcomes are identical. The Pilot 1 plan copy still says `executed = false`; the summary, manifest, and rows record execution. The Phase 7 demonstration contains an unexplained equality between a neural seed-42 row and a random seed-42 row with very different action streams; the paper flags it and does not use it as evidence.

The Phase 7 full suite recorded six failures on README hash pins, and Pilot 1's protected-baseline check found two drifts, README.md and `motor/__init__.py`, so `check_integrity()` returned `pass = false` and Pilot 1 is not freeze-ready. The drift pre-dates Pilot 1 and was not created by it, but it remains unresolved. The G3 memory deviation is also open: sixteen random graphs were generated and certified while free memory was below the 4 GB gate, the gate was not weakened, and the graphs were not accepted for data collection. B7 is unaccepted. These are documentation and governance limitations, not measurement errors, but they bound what the programme can claim about readiness.

## 19.7 Deviations register

Table 22 records the nine deviations identified across the programme.

**Table 22.** Deviations register. Each entry states the recorded item, the source record, the nature of the deviation, its effect, and its resolution. "Open" means the deviation remains unresolved and no restoration or amendment was performed. Data source: the reports and execution records cited in each row; full machine-readable table in `tables/T15_deviations_register.csv`.

| ID | Item | Record | Nature | Effect | Resolution |
|---|---|---|---|---|---|
| DEV-1 | Pilot 1 execution report prose total | `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` §6 | report says 72,880; nine rows sum to 73,880 | 1,000-spike arithmetic typo in prose only; per-episode values correct | disclosed; original not edited; corrected total used |
| DEV-2 | G3 memory gate during randomisation | `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` | 16 graphs generated and certified below the 4 GB gate | deviation recorded; gate not weakened; graphs not accepted for data collection | open; B7 unaccepted; Pilot 2-C uses no random graphs |
| DEV-3 | F/9001 resume ledger provenance | `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md` §3.2 | resumed artifact listed 19 of 20 checkpoints | original preserved; corrected record; no parameter or metric changed | resolved; regression test added |
| DEV-4 | Protected baseline drift (README, `motor/__init__.py`) | `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` §7.1 | 2 of 37 protected files differ from pins | `check_integrity()` returns `pass = false`; Pilot 1 not freeze-ready | open; not caused by the pilot; no restoration performed |
| DEV-5 | Floor vs neural action digest | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl` | floor rows have a different `action_sha256` from neural arms | different recording path; outcomes, counts, and rewards identical | disclosed; paper says identical outcomes, not identical digests |
| DEV-6 | Pilot 2-C preflight blocker | `reports/PHASE_8_PILOT2C_EXECUTION_PREFLIGHT.md` | global training-gate refusal folded into pilot stage blockers | pilot trains nothing; blocker moved to `training_blockers` | resolved before execution; superseded preflight preserved |
| DEV-7 | F_beta 9001 episode 0 wall time | `reports/PHASE_8_PILOT2C_EXECUTION_REPORT.md` §8 | 1,653.9 s for one episode, 47.8% of run wall time | host-scheduling observation; row fields consistent | recorded; no behavioural or simulation deviation |
| DEV-8 | Phase 7 full-suite failures | `reports/PHASE_7_GAME_INTEGRATION.md` | 6 tests fail on README hash pins | pre-existing README drift, unrelated to Phase 7 | disclosed; pins not edited |
| DEV-9 | Pilot 1 plan label | `experiments/results/phase_8/pilot1/pilot1/pilot_plan.json` | plan copy still says `executed = false` / construction-only | pre-execution plan copy; summary, manifest, and rows record execution | recorded, not rewritten |

## 19.8 Consolidated limitations register

Table 23 consolidates the fifteen limitations that bound the programme's conclusions. It is organised by scope rather than by phase, because the same limitation often affects several results.

**Table 23.** Consolidated limitations register. Each row states a limitation, its scope, and its consequence for interpretation. The register is descriptive; it does not rank limitations by severity. Data source: the phase reports and configuration documents cited in Chapters 3–16; full machine-readable table in `tables/T17_limitations.csv`.

| ID | Limitation | Scope | Consequence |
|---|---|---|---|
| L1 | Structural connectivity is not physiological connectivity | all connectome results | edge existence and synapse counts do not establish conductance, sign, or function |
| L2 | Transmitter signs are predictions; 55.52% of BANC t5 edges are unsigned | BANC propagation | a structural path may carry no modelled current |
| L3 | Weights are an arbitrary calibrated transform | all simulations | no measurement fixes the scale, exponent, or cap |
| L4 | One uniform LIF parameter set | all simulations | no cell-type-specific physiology, adaptation, or bursting |
| L5 | Inhibition is a hyperpolarising current, not a conductance | all simulations | no shunting inhibition or reversal potential |
| L6 | Uniform 1 ms delay; no morphology | all simulations | conduction distance and dendritic filtering are absent |
| L7 | Sensory mapping is a convention | Phase 3A.5, 4H.4, 8 | 232 neurons for 7 features; no receptive-field map |
| L8 | The game is not Subway Surfers | Phases 7–8 | `endless-surfer` is a separate controlled implementation |
| L9 | Decoder labels are annotation-derived | Phases 4F–8 | LEFT/RIGHT/JUMP are not identified motor commands; ROLL/DUCK unsupported |
| L10 | Motor silence blocks the experimental chain | Phase 4H.4, 7, 8 | no motor spikes means no action, no reward channel, no behavioural contrast |
| L11 | Pilot evidence is not campaign evidence | Phase 8 | 3 seeds × 3 episodes; no C1–C4 estimate; N not selected |
| L12 | Synthetic calibration and decoder tests are not biological evidence | Phase 3C, 4F, 4G | they test machinery only |
| L13 | MI is descriptive and does not establish causation | Phase 6 | circular decoder estimate; small replicate counts; bias floor |
| L14 | Training was behaviourally null | D5/D6 | zero motor spikes, zero weight change, identical F/F_beta outcomes |
| L15 | FAFB is brain-only; the VNC comes from a different dataset | Chapter 3 | no limb motor neurons in FAFB; BANC is not merged with FAFB |

## 19.9 Unresolved documentation issues

Five documentation issues remain unresolved at the close of the programme, and the paper records them rather than resolving them editorially.

First, the protected-baseline drift (DEV-4) leaves Pilot 1 not freeze-ready. README.md drifted during Phase 7, and `motor/__init__.py` was changed by commit `3c74ae8` on 2026-11-19, before Pilot 1. Because `motor/__init__.py` is a non-README failure, the integrity check returns `pass = false`. Resolving it requires an authorised amendment or a compliant restoration, neither of which was performed.

Second, the G3 memory deviation (DEV-2) remains open. Sixteen random graphs were generated and certified below the 4 GB gate; the gate was not weakened, and the graphs were not accepted for data collection. B7 is unaccepted. This does not affect Pilot 2-C, which uses no random graph, but it blocks C3 and therefore H2.

Third, the Pilot 1 report's 72,880 prose total (DEV-1) is preserved unchanged. The paper uses 73,880, the row sum, and discloses the difference. A reader comparing the paper with the report will see different totals for the same nine episodes; the explanation is the transcription error, not a difference in data.

Fourth, the Pilot 1 plan copy still says `executed = false` (DEV-9). The pre-execution plan was not rewritten. The authoritative records are the summary, manifest, and nine episode rows, all of which record the run as executed.

Fifth, the Phase 7 demonstration contains an unexplained equality between the neural seed-42 run and the random seed-42 run. The two have very different action streams — the random run contains JUMP, LEFT, RIGHT, ROLL, and NO_ACTION, while the neural run is entirely NO_ACTION — yet they report the same 213 updates, 2 coins, 1 collision, reward 5.55, and survival 3.12. The equality was flagged during analysis and is not used as evidence. It remains a documentation issue, not a scientific result.

A sixth issue is not a discrepancy but a scope limitation that readers may mistake for one: the detector's validation metrics are provenance from its training environment, not re-measured here, and there is no independent test set. The paper states this wherever the metrics appear.

## 19.10 Summary

The limitations fall into five groups. Construct validity is bounded by the gap between structural and physiological connectivity, the unsigned-edge fraction, the calibrated weight transform, the uniform LIF model, and the conventional sensory mapping. Internal validity is bounded by small samples, pilots that are not campaigns, a degenerate motor-silent grid, and a readout control that could not discriminate. External validity is bounded by a single controlled game, a single substrate threshold, and a detector validation set that is not fully independent. Statistical validity is bounded by the difference between failing to reject and establishing a null. Documentation is bounded by two open governance deviations, a preserved prose typo, a stale plan label, an unexplained Phase 7 equality, and a protected-baseline drift that leaves Pilot 1 not freeze-ready. None of these limitations is hidden, and none is repaired by changing a frozen parameter after the fact.
