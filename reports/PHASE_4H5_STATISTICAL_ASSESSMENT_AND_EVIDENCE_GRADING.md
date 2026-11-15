# Phase 4H.5 — Statistical Assessment and Evidence Grading

**Date:** 2026-11-08
**Scope:** Assessment of Phase 4H.1–4H.4 only. No new simulations and no parameter changes were made in this phase.
**Assessment script:** `experiments/phase_4h/assess_phase_4h.py`
**Machine-readable output:** `reports/PHASE_4H5_STATISTICAL_ASSESSMENT_AND_EVIDENCE_GRADING.json`

## 1. Executive summary

Phase 4H is complete. All four sub-studies executed the runs they planned and left verifiable artifacts, and Phase 4H.4 completed the full 27-run sensory-to-BANC matrix with 27 hash-verified replays, 47/47 configuration checks and 6/6 deterministic repeat pairs. All 37 protected-file integrity checks pass in every phase.

The evidence supports **E0–E2 only**:

- **E0 (infrastructure):** integrity, configuration verification and determinism all hold.
- **E1 (computational activity):** the model produces reproducible activity in the directly stimulated populations, and condition C produces a reproducible simulated motor/JUMP decoder output.
- **E2 (population-level sensitivity):** decoder output changes reproducibly with population identity, population size and selection rule, and with weight transform, sign policy and drive amplitude.

The sensory round-trip does **not** support E3 or E4:

- Synaptic current from the 232 stimulated neurons reaches 473 of 607 downstream first-hop targets, but the closest first-hop neuron remains **6.926 mV** below threshold, and **no non-stimulated neuron ever spikes**.
- Second-hop current is zero, so there is no second-hop activity at all.
- Descending neurons receive current (9 neurons, closest 12.158 mV short) but never spike. Motor neurons receive no current and produce no spikes.
- All 67 decoder windows in condition B are NEUTRAL.
- Actual event structure differs from shuffled controls only in the total spike count of the stimulated neurons, not in any downstream or decoder response.

The overall Phase 4H verdict is **PASS WITH LIMITATIONS**. The motor-silent sensory result is a controlled negative result about this model at this drive, not an execution failure, and it must not be described as a failure of the biological pathway.

## 2. Audit of Phase 4H.1–4H.4

The assessment reads the stored artifacts directly. Nothing was reconstructed from memory, summaries or preliminary smoke tests. All ten audited artifacts were present; the missing-artifact list is empty.

| Sub-study | Artifact | Runs | Failures | Integrity | Key outcome |
|---|---|---|---:|---:|---|---|
| 4H.1 random controls | `experiments/results/phase_4h/control_draws.json` (4.75 MB) | 500 draws (5 families × 100) | 0 | 37/37 | Condition C: 492 motor spikes, 4 JUMP windows; p = 0.00990099 (design floor) against every family; Holm rejects all 10 comparisons; spike hash matches Phase 4G |
| 4H.2 population sensitivity | `experiments/results/phase_4h/population_sensitivity.json` (3.04 MB) | 175 | 0 | 37/37 | Monotone size curve 8→128 neurons (5→1,126 motor spikes); JUMP first appears at size 48; size-64 confirmatory p = 0.00990099, Holm-adjusted 0.0198 |
| 4H.3 weight sensitivity | `experiments/results/phase_4h/weight_sensitivity.json` (1.62 MB) | 220 (22 configs × 10 seeds) | 0 | 37/37 | Pre-registration SHA-256 `372ec71c…` matches; motor output present for 4 nominal configs and silent for 7; S2 ≡ S0, W4 ≡ W1 |
| 4H.4 sensory round-trip | `experiments/results/phase_4h/sensory_roundtrip.json` (2.91 MB) + `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` (0.93 MB) | 27 (7 conditions × 3 streams, plus 6 repeats) | 0 | 37/37 | 27/27 matrix complete; 47/47 configuration checks pass; 6/6 repeat pairs hash-equal; zero non-stimulated spikes; all decoder windows NEUTRAL |

Reports audited: `reports/PHASE_4H1_RANDOM_CONTROL_VALIDATION.md`, `reports/PHASE_4H2_POPULATION_SENSITIVITY.md`, `reports/PHASE_4H3_WEIGHT_SENSITIVITY.md`, `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md`, and the protocol `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`.

Two design facts limit how the four sub-studies can be combined:

1. **The 4H.1–4H.3 reference and the 4H.4 sensory group are different driven populations.** The 492-spike / 4-JUMP reference drives a 64-neuron VNC-intrinsic group tonically at 300 pA. Phase 4H.4 drives 232 sensory-mapped neurons with 200 pA event pulses. Their divergence is expected and is not an inconsistency.
2. **4H.1 and 4H.2 reuse the same 100 family-A control draws.** They are not independent replications of each other.

## 3. Statistical robustness

The replication unit throughout Phase 4H is the **simulation run**, not the neuron or the timestep. This is the only unit for which a genuinely independent repeat exists (a re-run with the same seed). Neurons and timesteps are strongly dependent and are never treated as replicates.

### Q1. Is the motor decoder deterministic? — Yes (E0)

Identical inputs reproduce identical spike, decision and drive hashes across all 4H.3 repeat configurations and all 6 4H.4 repeat pairs. The 4H.1 reference spike hash equals the stored Phase 4G hash. Determinism is a software property and says nothing about biological reproducibility.

### Q2. Is the output robust to random control draws? — Yes, with limits (E2)

Condition C exceeds all 500 draws from five matched random families on both primary endpoints. Every p-value is 0.00990099, which is the smallest value attainable with 100 draws per family ((0+1)/(100+1)); it is not a precise p-value. Holm–Bonferroni rejects all ten hypotheses at α = 0.05.

Limits: the controls are matched approximations, not a random sample of the connectome; and **condition C was selected on the same motor-synapse rank used to build one of the control families**, so the comparison is partly circular. The correct reading is "distinguishable from these matched controls", not "the best possible population".

### Q3. Is the output sensitive to population selection and size? — Yes (E2)

The connectivity-ranked size surface rises monotonically from 5 motor spikes at size 8 to 1,126 at size 128, and JUMP windows appear from size 48 onward. Only the size-64 cell is pre-registered; the rest of the surface is exploratory and should not be used for confirmatory claims. The same surface also shows the result is not a threshold artefact of the decoder: motor spiking changes smoothly while JUMP switches on later.

### Q4. Is the output stable across weight transformations? — No

At nominal drive (D0), JUMP is present only for W0, W5 and W6 and absent for W1, W2, W3, W4 and W7; W2, W3, W7 are fully silent, and W1/W4 produce 5 motor spikes with zero JUMP windows. Sign policy matters as much: S2 is numerically identical to S0 (unknown edges retained at zero weight), while S3 and S4 are silent at nominal drive. Drive amplitude also changes the answer (D1 1000 pA restores motor spikes for transforms that are silent at D0). The decoder result is therefore **assumption-dependent**, and no transform can be named biologically correct from this study.

### Q5. Does sensory stimulation produce downstream propagation? — No

At 200 pA per feature, current reaches the first hop but not threshold. The closest of 607 downstream first-hop targets stays 6.926 mV below threshold, and none of the 473 receiving neurons spikes. There is no second-hop current and therefore no second-hop activity. E3 requires propagation to the intended output population; that is not observed.

### Q6. Is the actual event structure distinguishable from shuffled controls? — Only at the input

Condition totals for the full stream are B 3,562, C 3,760, D 3,648, E 3,561, F 0, G 0 spikes. The differences exist only inside the stimulated sensory mask, they change sign across streams (B−C = −198 / +117 / +108; B−D = −86 / −1 / +294), and no downstream group or decoder window distinguishes B from C, D, E, F or G. There is no propagated or decoder-level sensory specificity.

### Q7. Does activity reach descending and motor populations? — No

Descending neurons receive first-hop current (9 neurons, closest 12.158 mV short) but do not spike. Motor neurons receive no current and do not spike, although 4 motor neurons sit two signed hops from the stimulated group. All 67 decoder windows in condition B are NEUTRAL.

### Q8. Are the effects dependent on model assumptions? — Yes

The weight, sign and drive sweeps (Q4) show large, reproducible changes in motor output; the mapping is an annotation-defined hypothesis; and 44.5% of threshold-5 edges carry a verified transmitter sign, with the rest excluded. Any statement about this network is conditional on those assumptions.

## 4. Cross-phase comparison

| Phase | Question | Result | Dimension | Grade |
|---|---|---|---|---|
| 4H.1 | Is condition C distinguishable from matched random controls? | Yes, at the design p-floor; 5 families all rejected | statistical robustness | E2 |
| 4H.2 | Does population size and selection rule matter? | Yes, monotone size curve; size-64 confirmatory | statistical robustness | E2 |
| 4H.3 | Is the result stable across weight/sign/drive? | No; output present in 4 nominal configs and absent in 7 | parameter sensitivity | E2 |
| 4H.4 | Does sensory input propagate to descending and motor output? | No; first hop subthreshold, second hop silent, decoder NEUTRAL | downstream propagation / motor output | E0–E1 only |

The four phases are mutually consistent once their driven populations are kept distinct. 4H.1–4H.3 show that the decoder **can** be driven to LEFT/RIGHT/JUMP when a suitable population is driven directly. 4H.4 shows that the specific sensory-mapped population at 200 pA does **not** reach that state. The second result does not retract the first; it bounds where the first applies.

## 5. Evidence grades per claim

E0–E4 are **internal computational evidence grades defined for this project**, not an established neuroscience standard. Each claim is graded separately on the highest criterion it actually satisfies. A claim with no supporting criterion remains ungraded even when the underlying simulation runs.

| Claim | Claim summary | Dimension | Grade | Status |
|---|---|---|---|---|
| C01 | Data integrity and deterministic execution | reproducibility | **E0** | supported |
| C02 | Event drive produces reproducible sensory spikes | computational activity | **E1** | supported |
| C03 | Condition C produces reproducible motor spikes / JUMP windows | computational activity | **E1** | supported |
| C04 | Condition C differs from five matched random families | statistical robustness | **E2** | supported with limits |
| C05 | Motor output depends on population size and selection rule | statistical robustness | **E2** | supported |
| C06 | Output is sensitive to weight transform, sign policy and drive | parameter sensitivity | **E2** | supported |
| C07 | Sensory stimulation propagates beyond the stimulated neurons | downstream propagation | — | contradicted |
| C08 | Actual events produce a distinguishable propagated response | sensory specificity | — | not supported |
| C09 | Sensory activity reaches descending and motor neurons | motor output | — | contradicted |
| C10 | A decoder label is a validated motor command / behaviour | motor output | — | not supported |
| C11 | The game-feature mapping is a measured pathway | biological plausibility | — | not supported |
| C12 | The reported effects are invariant to model assumptions | parameter sensitivity | — | contradicted |

The next grade for each ungraded claim is recorded in the JSON (`highest_grade_not_awarded`): C07, C08, C09, C11 and C12 would require E3 evidence; C10 would require E4. E3 is not awarded merely because the decoder emits labels, and E4 is not awarded without controlled behavioural learning and independent validation.

## 6. Strongest supported conclusion

Under the fixed verified-only sign policy (S0) and W0 weight transform, a 64-neuron VNC-intrinsic group selected on motor-synapse rank produces a reproducible simulated motor/JUMP decoder output that is distinguishable from five matched random-control families (E2). The output is strongly dependent on weight transform, sign policy and drive amplitude.

Sensory stimulation at the tested 200 pA per-feature drive produces spikes only in the stimulated sensory neurons. Synaptic current reaches first-hop targets but does not bring any of them to threshold, so there is no propagation to descending or motor populations and no E3 functional-pathway evidence.

## 7. Unsupported claims that must not be made

1. That sensory events drive descending or motor-neuron activity in this model.
2. That actual event structure produces a distinguishable propagated response compared with shuffled controls.
3. That 662 signed outgoing edges imply effective downstream activation.
4. That a LEFT, RIGHT or JUMP decoder label is a biological motor command or observed behaviour.
5. That the game-feature-to-BANC mapping is a measured visual pathway.
6. That the Phase 4G JUMP result is invariant to weight transform or sign policy.
7. That the model provides E3 functional-pathway evidence or E4 behavioural evidence.
8. That stationary or constant-charge drive is equivalent to the actual event sequence.

## 8. Remaining uncertainties

- Structural connectivity is not physiological connectivity: sign, weight and delay are model priors.
- 44.5% of threshold-5 edges carry a verified transmitter sign; the rest are excluded and may change propagation.
- Synaptic weights are monotone transforms of structural synapse counts, not measured conductances.
- The 232-neuron sensory mapping is an annotation-defined hypothesis, not a measured receptive-field map.
- BANC is one specimen and one dataset export; annotation completeness and proofreading are limited.
- Event timestamps are synthesized at 30 fps because the source images carry no timestamps.
- No validated biological labels exist for LEFT, RIGHT or JUMP.
- The absence of propagation at 200 pA does not prove that the network cannot propagate at other drives or weights.
- The three streams are non-overlapping segments of one recording group, not independent recordings.
- A motor-neuron spike in the simulator is not a validated motor command or behaviour.

## 9. Recommended next experiment

**Pre-registered sensory-drive threshold and propagation calibration.**

Rationale: the current experiment establishes that 200 pA per-feature pulses reach first-hop membranes but remain subthreshold. The next step is to estimate the input level at which the first hop crosses threshold — not to search for a setting that produces motor activity.

Design:

1. Pre-register a fixed geometric drive series (for example 200, 400, 800, 1,200 pA per feature) with all seven conditions A–G on all three streams.
2. Record the same first-hop, second-hop, descending and motor diagnostics with hash-verified replays.
3. Report every cell, including silent cells; do not select a drive after observing motor output.
4. Add a direct first-hop current-injection positive control to verify that first-hop neurons can spike under the model.
5. Add a single-first-hop-spike test to measure whether one first-hop spike produces any second-hop current or spike.
6. Repeat the analysis on an independent recording or a second specimen before any E3/E4 claim.

Decision rule: the experiment succeeds if it estimates a threshold and reports it, regardless of whether motor activity appears.

## 10. Overall Phase 4H verdict

**PASS WITH LIMITATIONS.**

Phase 4H was executed as specified: all planned runs completed, no run was rerun unnecessarily, all results are hash-verified and all protected artifacts are unchanged. The evidence supports E0–E2 and does not support E3 or E4. The sensory round-trip is reproducibly motor-silent at the tested drive, and that negative result is preserved rather than tuned away.

The limitations that produce this verdict are the matched-but-not-random control families, the non-independent sensory streams, the post-hoc nature of the internal grading, the p-value design floor, the selection bias in condition C, and the fact that sign, weight and delay remain model priors. These are recorded in the JSON and in Section 8.

Phase 4H.4 and Phase 4H.5 therefore close with a controlled negative result: **the model can be driven to a decoder output, but the tested sensory pathway does not reach it.**
