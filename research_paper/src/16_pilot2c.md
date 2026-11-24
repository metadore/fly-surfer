# Chapter 16. Pilot 2-C: Floor and Identity Certification

## 16.1 Authorisation and the resolved preflight blocker

Pilot 2-C is the amended Phase 8 pilot defined by decision record D3 and the Pilot 2-C amendment, SHA-256 `832ef485…67ad`, bound to REV4 (`e4aa9e0f…1547c`). It is not the confirmatory campaign and is not campaign evidence. Its declared purpose is `floor_and_identity_certification`, and its evidence kind is `pilot`. It was executed on 2026-11-23 under an explicit owner authorisation covering exactly the 54-entry grid and nothing else.

The authorisation chain was verified before execution. D1 was approved and bound to REV4; D2 remained valid for Pilot 1 only; D3 was applicable and matched the amendment on disk; D4 was applicable; D5 and D6 were valid and all six trained artifacts were bound; the stage authorisation reported `authorized = true` with no blockers. Three gates nevertheless remained closed and were reported as closed: the global training gate still refused further training, the campaign gate still refused, and no randomized graph was constructed, read or substituted. Pilot 2-C trains nothing, so the training gate is not a precondition for it; the campaign gate is untouched by it.

One preflight blocker had to be resolved legitimately before execution. A training-stage refusal had been folded into the pilot's stage blockers, which made the pilot appear non-executable for a reason that does not apply to a stage that trains nothing. The refusal was moved to `training_blockers`, where it is still reported, D5/D6 applicability was made the real precondition, and the runner now injects the six loaded artifacts. Regression tests cover both the reporting and the refusal when D5 is not applicable. The global training gate and the campaign gate were not altered. The full Phase 8 suite passed after the change, 531 tests. This resolution is what separates the end-of-D5 preflight, which returned `executable = false`, from the execution preflight, which returned `executable = true` with an empty blocker list.

The execution preflight recorded `uses_randomized_graph = false`, `constructs_randomized_graph = false`, and a free destination. The six artifacts loaded with `origins = ["trained"]`, `complete = true`, `missing = []`, `require_trained = true`, and `synthetic_allowed = false`. The run-time memory gate reported 6.115 GB available against the frozen 4.00 GB gate, at 60.1% used, and was not waived. No C, C′, or D arm was run, no training occurred, and no `n_seeds_selected` value was written.

## 16.2 The 54-entry grid and its execution

Table 18 reports the design. There are 45 neural episodes — five conditions at three evaluation seeds and three episodes each — and nine substrate-free floor replays paired to the same environment seeds. The environment seed is derived from master seed 20261116 and the `(seed, episode)` pair, so the floor replay faces the same game trajectory as the five neural arms at that pair.

**Table 18.** Pilot 2-C design grid. The design is the D3 scope: five neural arms and a substrate-free floor, three evaluation seeds, three episodes per seed, 54 entries in total. No randomized-graph arm and no campaign condition are present. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` and `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/pilot_plan.json`; full machine-readable table in `tables/T12_pilot2c_design.csv`.

| Arm | Substrate | Weights | Readout | Seeds | Episodes per seed | Purpose |
|---|---|---|---|---|---|---|
| A | biological BANC t5 | fixed | none | 3 | 3 | reference |
| B | biological BANC t5 | three-factor plasticity (η = 0.5) | none | 3 | 3 | plasticity |
| F | biological BANC t5 | fixed substrate | trained linear readout | 3 | 3 | readout |
| F_beta | biological BANC t5 | fixed substrate | trained bias-only readout | 3 | 3 | readout control |
| A_prime | biological BANC t5 | three-factor with η = 0 | none | 3 | 3 | identity control |
| floor | none | none | constant NO_ACTION | 3 | 3 | substrate-free floor |

The run is `pilot2c_d3_20261123`. Its first row was written at 03:37:44Z and its last at 04:35:36Z, with a total episode wall time of 3,458.8 s. The summary records `planned = 54`, `rows_executed = 54`, `rows_stored = 54`, `complete = true`, `evidence_kind = pilot`, `experimental_evidence = true`, and `merged_into_campaign = false`. No row carries an error status, no episode was retried, and no substitution occurred. The episode file contains 54 schema-valid rows and has SHA-256 `a14fd3bb…778991`; the manifest is `43710d38…020534`, the plan `63d51f61…ddcab`, and the summary `44dc5c05…520c5`.

## 16.3 The nine distinct game trajectories

The 54 rows reduce to nine distinct game trajectories, because every arm made the same decision at every step. Table 19 reports those nine `(seed, episode)` outcomes; each row applies identically to all six arms.

**Table 19.** Pilot 2-C per-episode outcomes. Steps equal the survival score, which is the number of game updates completed before collision. The nine rows are identical for all six arms because every arm took NO_ACTION on every decision, so the trajectory is determined by the environment seed alone. The floor rows' action digests differ from the neural rows and are not compared as identical. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`; full machine-readable table in `tables/T13_pilot2c_outcomes.csv`.

| Seed | Episode | Environment seed | Steps | Reward | Termination | Motor spikes | NO_ACTION fraction | Survival score |
|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 9001 | 0 | 563774599 | 323 | 5.22 | collision | 0 | 1.0 | 323 |
| 9001 | 1 | 2911696168 | 620 | 10.19 | collision | 0 | 1.0 | 620 |
| 9001 | 2 | 4240939637 | 323 | 4.22 | collision | 0 | 1.0 | 323 |
| 9002 | 0 | 2632356062 | 620 | 7.19 | collision | 0 | 1.0 | 620 |
| 9002 | 1 | 307060235 | 426 | 3.25 | collision | 0 | 1.0 | 426 |
| 9002 | 2 | 4241804999 | 620 | 8.19 | collision | 0 | 1.0 | 620 |
| 9003 | 0 | 2839813884 | 213 | 3.12 | collision | 0 | 1.0 | 213 |
| 9003 | 1 | 756850162 | 426 | 4.25 | collision | 0 | 1.0 | 426 |
| 9003 | 2 | 2981106662 | 213 | 2.12 | collision | 0 | 1.0 | 213 |

Each arm therefore has nine episodes, a mean survival of 420.44 updates, zero motor spikes, and no error rows. The per-seed means are 422.00 at 9001, 555.33 at 9002, and 284.00 at 9003, with total rewards of 19.63, 18.63, and 9.49. Every arm produced 3,784 decisions and every decision was NO_ACTION. Figure 34 shows the six arms overlaid; the bars coincide exactly.

This is a measured property of the grid, not an assumption. The amendment anticipated a motor-silent substrate, and P2C-5 exists to verify that the silence is recorded rather than inferred. It reproduces Pilot 1's result on the same nine environment seeds, which is expected because the same condition A substrate and decoder are used. It is not a new biological finding.

![Figure 34. Pilot 2-C survival by arm and cell. All six arms — A, B, F, F_beta, A_prime, and floor — produce the same survival score at each of the nine `(seed, episode)` cells, because every arm takes NO_ACTION on every decision. Mean survival is 420.44 updates. The coincidence is a property of a motor-silent grid; it is not evidence of equivalent learning or equivalent decoding. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`.](figures/F28_pilot2c_outcomes.png)

Figure 33 shows the design grid as executed: six arms by nine cells, all present.

![Figure 33. Pilot 2-C design grid as executed. Rows are arms, columns are the nine evaluation-seed by episode cells, and every cell is filled: 45 neural episodes plus 9 floor replays, 54 entries in total. All 54 executed and none was retried or substituted. No campaign contrast is estimated from this grid. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`.](figures/F27_pilot2c_design.png)

## 16.4 A′ identity

The A_prime control is a three-factor rule executed with η = 0. It is not a disabled pathway: the rule runs, eligibility slots are touched, and the applied update is exactly zero. The identity requirement is that A_prime reproduce A exactly, and it does, in all nine pairs.

The comparison covers nineteen declared fields per cell, denoted P1–P19: spike times, spike indices, spike digest, action and reward digest, the full record sequence, the survival and termination summary, action and decoder counts, reward components, neural and game timing, per-decision motor activity, structural, initial, learned-delta, and effective weight digests, maximum absolute delta, changed edges, clamp and saturation counts, the weight fingerprint, and resets. Tolerance is none; the requirement is exact equality.

All nine pairs match on all nineteen fields with zero mismatches. Every A_prime episode has η = 0, `changed_edges = 0`, and `max_abs_delta_pa = 0.0`; each records `rule_executed_zero_delta`, meaning the rule executed and applied nothing. Each episode has exactly one opening stepper reset and zero in-episode resets, matching A. The store-level reduced comparison also reports no mismatch. The hard stop that would refuse an A_prime episode on identity failure was never triggered, and B's status was not invalidated.

Figure 35 plots A against A_prime survival; every point lies on the identity line, but the figure is weaker than the underlying comparison. The identity claim is exact on the nineteen declared fields, not on every stored byte; for example, the floor rows' action digests are not compared as identical to the neural rows. The paper states the narrower claim.

![Figure 35. Pilot 2-C A_prime identity check. Each point compares A and A_prime survival at one `(seed, episode)` cell; all nine lie on the identity line. The exact claim is stronger than the plot: equality on all nineteen declared fields P1–P19, zero weight delta at η = 0, one opening reset, and no in-episode reset. Identity is exact on the declared fields, not on every stored byte. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` (P2C-2) and the Pilot 2-C episode file.](figures/F29_pilot2c_a_prime.png)

## 16.5 The eight certification claims

Table 20 reports the eight claims, recomputed from the stored rows and the manifest by the certification evaluator. All eight pass. The claims concern machinery: floor execution, identity, control constancy, readout wiring, motor accounting, plasticity attribution, provenance, and viability.

**Table 20.** Pilot 2-C certification claims P2C-1 through P2C-8. The evaluator recomputes each claim from the 54 stored rows and the manifest and writes nothing else. A PASS certifies the experiment's machinery, not biological learning, behavioural competence, or motor decoding. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json`, SHA-256 `bc5effaa…aa357`; full machine-readable table in `tables/T14_pilot2c_certification.csv`.

| Claim | Title | Result | Evidence |
|---|---|---|---|
| P2C-1 | floor execution | PASS | 9/9 substrate-free replays take NO_ACTION; own no spike or weight |
| P2C-2 | A-prime identity | PASS | A′ reproduces A on P1–P19 in 9/9 (η = 0, zero delta) |
| P2C-3 | F-beta constancy | PASS | 0 feature weights; bias-only readout; state-independent logits |
| P2C-4 | F behaviour | PASS | 12 non-zero feature weights; weights unchanged within episodes |
| P2C-5 | motor accounting | PASS | every neural episode records a motor block; 0 reported as 0 |
| P2C-6 | plasticity attribution | PASS | A′ delta 0; B 683,100 eligible, 1 edge changed in 4/9, max 0.03265 pA |
| P2C-7 | provenance | PASS | 7 input hashes + 3 config hashes + evidence kind on every row |
| P2C-8 | viability | PASS | 54 planned, 54 stored, 0 error rows, survival score recorded |

The claims are worth reading individually, because each one is narrower than its title suggests.

**P2C-1, floor execution.** The nine substrate-free replays are schema-valid, take NO_ACTION on every decision, read no spike, and own no weights. The floor is not a neural arm: `neural_substrate = "none"`, `is_neural_arm = false`, and `spikes_read = false`. It provides the behavioural baseline for the same nine environment seeds, and it matches the neural arms' trajectories exactly.

**P2C-2, A′ identity.** The nine pairs are exact on P1–P19, with no tolerance, η = 0, zero changed edges, zero clamp hits, and one opening reset per episode. In episodes where eligibility slots were touched, between 12 and 45 slots, nothing was applied because η = 0. The rule executed; the delta was zero.

**P2C-3, F_beta constancy.** F_beta has zero non-zero feature weights, its only trainable parameter is the bias, its logits for a zero feature vector and a saturated feature vector are identical, and it selects one action on every decision. This is provable state independence, not an empirical tendency.

**P2C-4, F behaviour.** F is state-dependent: its readout has twelve non-zero feature-weight entries. Its weights are frozen during evaluation, and its parameter and feature-weight digests are identical before and after every episode. The claim certifies that F is wired to the motor features and frozen, not that the features carried information. In this grid the feature vector was always zero, so F's logits reduced to its bias and its behaviour coincided with F_beta's.

**P2C-5, motor accounting.** Every neural episode records a per-decision motor block with the decision count, the decisions with a motor spike, the per-population spike counts for LEFT, RIGHT, and JUMP, and a 50 ms window. The recorded motor-spike count is consistent with the row. Each arm has 3,784 decisions and zero with a motor spike; zero is reported as zero rather than omitted.

**P2C-6, plasticity attribution.** A′ reports zero delta in all nine episodes. B reports `eligible_edges = 683,100` at η = 0.5 and records changed edges, maximum absolute delta, update reports, and hook calls per episode. Four of the nine B episodes applied updates — 42, 45, 24, and 12 applied updates — and each changed exactly one edge. The maximum absolute delta is 0.03265 pA, the maximum applied update is 0.01022 pA, and there are zero clamp hits and zero sign violations. These are weight-level changes only. They produced no motor spikes and no behavioural difference in this grid, which is exactly the distinction P2C-6 exists to make attributable: the plastic rule can be shown to execute and change a weight without any behavioural consequence.

**P2C-7, provenance.** Every row carries the seven frozen-input hashes, the three configuration hashes, the seed plan, the evidence kind, the stage purpose, and the D3 and amendment bindings. Every F and F_beta row additionally records its artifact's condition, evaluation seed, training seed, parameter digest, and parameter-file SHA-256. The seven frozen-input hashes are graph `6d47f259…e2192`, nodes `144a2eb0…53e5f`, neuron config `9b652bde…8b77`, synapse policy `88f64492…dc399e`, plasticity `616288a4…9e5f70`, sensory mapping `64c716a4…cdfc4ff`, and motor decoder `525f25e9…0d9fae`; the three configuration hashes are campaign `b9a2d3d5…477e19`, conditions `9a93f047…42f671`, and environment `b391ecf7…3281dc`.

**P2C-8, viability.** Fifty-four rows were planned, fifty-four stored, none missing, no error rows, and every row is schema-valid with a survival score. Nothing was skipped, retried, or substituted.

Figure 36 displays the eight results. The figure's value is completeness, not effect size; all eight claims are machinery claims, and none is a measurement of learning.

![Figure 36. Pilot 2-C certification claims P2C-1 through P2C-8. All eight claims pass when recomputed from the 54 stored rows and the manifest. The claims certify floor execution, A_prime identity, F_beta constancy, F wiring, motor accounting, plasticity attribution, provenance, and viability. A passing certification is not evidence of biological learning or behavioural competence. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` (claims).](figures/F30_certification_matrix.png)

## 16.6 C1–C4 and H1–H3: what Pilot 2-C could not evaluate

Pilot 2-C estimates no contrast and tests no hypothesis. The amendment declares this explicitly, and the data cannot support anything else. The status of each campaign quantity is as follows.

C1 = F − A is not estimated. The rows show a zero descriptive difference, because both arms execute NO_ACTION on every decision, but a zero difference on a motor-silent substrate is degenerate. The amendment declares C1 estimable but degenerate; three pilot seeds with three episodes are not the campaign design, and no inferential statement is made.

C2 = B − A is a structural zero and is not estimated. On a substrate that produces no motor output, the B/A difference has no behavioural channel. The observed row equality is expected and carries no information about plasticity.

C3 = A − C is undefined and is not estimated. Condition C is excluded from Pilot 2-C, and no randomized graph was constructed, read, or substituted.

C4 = F − F_beta is not estimated. The rows show a zero descriptive difference because both trained readouts selected NO_ACTION on every decision: F's feature vector was always zero on the motor-silent substrate, so its logits reduced to its bias, and F_beta is bias-only by construction. The pilot cannot support a decoding claim, and none is made.

The hypotheses inherit those statuses. H1 (B − A ≠ 0) is unevaluable because C2 is a structural zero here. H2 (A − C > 0) is unevaluable because C3 is undefined and C is absent. H3 (F − A > 0) is unevaluable because C1 is degenerate on this substrate; the absence of a difference is not a refutation of H3 at the campaign operating point. H4 (E-matched > floor) is not evaluated because E is not in the grid. H5, the difference-in-differences contrast involving C and D, is not evaluated because neither is in the grid. H6 has no subject, because no non-NO_ACTION update exists in the grid and its descriptive antecedent never occurs.

The dispersion and design quantities are also unestimated. σ_max, the paired dispersion, and the upper confidence limit were not computed; U7 remains open; N remains the predeclared 16 with `design.n_seeds_selected` unset. Bootstrap, Holm, α, and the smallest effect of interest were not used here and remain frozen for the campaign.

Any reading of Pilot 2-C as evidence for or against H1–H3 would contradict both the amendment and the information content of the data. The correct statement is that the pilot could not put those hypotheses at risk.

## 16.7 Deviations, failures, and the one run-time anomaly

No stop condition was triggered. There was no identity mismatch, no memory-gate failure, no refusal during execution, and no schema error. No entry failed or went missing, and there were no retries or substitutions.

One pre-execution deviation was resolved and recorded: the mis-scoped training refusal described in Section 16.1. It was corrected in the stage module with two regression tests before execution. The earlier final-preflight files were preserved unmodified, and the execution preflight supersedes them with the resolution recorded.

One run-time anomaly was recorded with no effect on any row. The episode `F_beta:9001:0` took 1,653.9 s of wall time, 47.8% of the total run, while the next longest episode took 304.8 s. All fields of that episode are internally consistent — 323 steps, NO_ACTION, collision, zero motor spikes — and the report classifies the delay as a host-scheduling observation rather than a behavioural or simulation deviation. The paper repeats that classification and draws no scientific inference from it.

Historical evidence was untouched. No original artifact, row, manifest, record, report, or README was modified or deleted, and no parameter, threshold, learning rate, statistical constant, N, U7 value, or frozen protocol was changed.

## 16.8 What Pilot 2-C established and what it did not

Pilot 2-C established that the authorised 54-entry grid executes exactly as declared, that the machinery the campaign depends on behaves as specified, and that the motor silence is measured rather than assumed. The floor takes NO_ACTION and owns no spike or weight; A′ at η = 0 is an exact in-process identity on the declared fields; F_beta is a provable bias-only readout; F is state-dependent and frozen during evaluation; plasticity is attributable to its declared rule, with A′ exactly zero and B reporting eligible edges, changed edges, and a maximum applied update; provenance is complete on every row; and every arm completes its planned episodes.

It did not establish a biological claim, a decoding claim, a contrast, a hypothesis conclusion, or a sample-size decision. Nothing in the pilot shows that the connectome learned, adapted, or is capable of behaviour. The readouts' biases chose NO_ACTION, and the substrate produced no motor spikes. C1–C4 are not estimated, C2 is a structural zero, and C3 is undefined. F and F_beta are behaviourally indistinguishable in this grid, so C4 is not estimated and H3 is neither supported nor refuted.

The defining fact is that every arm, including the floor, produced the same game trajectory for a given environment seed. The zero between-arm differences are a property of a motor-silent grid, not a result about learning, decoding, or connectivity. Pilot 2-C certifies a floor and an identity. It is infrastructure evidence that the experiment which will test H1–H3 can be built, paired, stored, and audited as declared. It is not behavioural evidence about a fly, and the eight PASS results must never be described as proof of biological learning or behavioural competence.

## 16.9 Summary

Pilot 2-C executed all 54 authorised entries on 2026-11-23: 45 neural episodes across five arms and 9 substrate-free floor replays, in 3,458.8 s of episode wall time. Every arm produced 3,784 NO_ACTION decisions, zero motor spikes, and collision termination; mean survival was 420.44 updates. A_prime reproduced A exactly on nineteen declared fields with η = 0 and zero weight delta. All eight certification claims passed, including the attribution result that B's plasticity changed one edge in four of nine episodes with a maximum delta of 0.03265 pA and no behavioural effect. No contrast C1–C4 was estimated, no hypothesis H1–H6 was evaluated, σ_max and dispersion were not computed, U7 remains open, and N remains the predeclared 16. The pilot certifies machinery and a floor; it does not certify learning.
