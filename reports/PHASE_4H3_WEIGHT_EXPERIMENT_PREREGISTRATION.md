# FLY-SURFER — Phase 4H.3 Weight Transformation Experiment Pre-Registration

Status: frozen before execution.
Phase: 4H.3.
Parent protocol: `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`.

This file fixes the weight-transformation and sign-policy grid, the drive
normalisation, the seeds, the endpoints and the analysis before any 4H.3
simulation is executed. It is hashed; the SHA-256 is written into
`experiments/results/phase_4h/weight_sensitivity.json`. The file is not edited
after results are seen. Any change becomes a separate, dated amendment file.

---

## 1. Question

Phase 4G.5 reported that the JUMP decoder output from condition C disappeared
under `linear` and `log1p` transforms and under power exponent 0.5, but
survived the uncapped power transform. Those checks were one run each, with a
single seed, and were not corrected for multiple comparisons.

Phase 4H.3 asks, with repeated draws and a fixed grid:

1. Is any decoder output stable across the pre-registered weight transforms?
2. Does the result depend on the sign policy?
3. Does replacing nominal stimulation amplitude with matched aggregate synaptic
   input change the answer?
4. Is the JUMP result an artefact of the cap, the exponent, or the drive
   amplitude?

The grid is executed once. No configuration is selected because it produces a
favourable label. Every cell, including silent cells and NEUTRAL-only cells, is
reported.

---

## 2. Fixed conditions

Identical to the parent protocol section 2: BANC v888 threshold 5, verified-only
sign policy unless it is the factor under test, dt 0.5 ms, 300 ms duration,
50–250 ms drive, 5,000,000 spike cap, unchanged Phase 4F decoder and
populations.

Candidate group: the Phase 4G condition C set of 64 neurons (fixed identities,
recomputed from the node table and asserted equal to the Phase 4G record).
Only the candidate set is held fixed here; this experiment does not vary
selection.

---

## 3. Weight families

Weight is a monotone transform of the integer structural synapse count
`count`. It is never `norm`, and it is never a conductance.

| ID | Family | Definition | Parameters | Normalisation |
| --- | --- | --- | --- | --- |
| W0 | `phase4g_primary` | `min(5.0 * count^0.75, 300)` | exponent 0.75, scale 5.0, cap 300 pA | reference |
| W1 | `linear_capped` | `min(0.5 * count, 300)` | linear, scale 0.5, cap 300 pA | Phase 4G declared sensitivity |
| W2 | `log1p` | `10 * log(1 + count)` | log1p, scale 10, no cap | Phase 4G declared sensitivity |
| W3 | `power_half` | `min(5.0 * count^0.5, 300)` | exponent 0.5, scale 5.0, cap 300 pA | Phase 4G declared sensitivity |
| W4 | `power_one` | `min(0.5 * count, 300)` | power exponent 1.0, scale 0.5, cap 300 pA | equals linear; run to verify the equivalence |
| W5 | `uncapped_power` | `5.0 * count^0.75` | exponent 0.75, scale 5.0, no cap | Phase 4G declared sensitivity |
| W6 | `min_count_60` | `5.0 * min(count, 60)` | cap 60 synapses, scale 5.0 | capped linear as `min(count, cap)` |
| W7 | `target_normalized_graph_local` | `min(150 * count / in_synapse_sum(dst), 300)` | scale 150 pA, cap 300 pA | approximation of `count / post_count` |

W4 is included because the Phase 4G sensitivity suite declared both a
`power_1` entry and a `linear` entry with the same parameters; running both
verifies that they are numerically identical.

W7 is an explicit approximation. The dataset's `post_count` (total input
synapses to the postsynaptic neuron) is not present in the repository: the raw
edge table is empty and the graph artifact stores only integer counts. A
graph-local denominator, the sum of in-edge synapse counts in the threshold-5
graph, is the only reproducible substitute. It is not the dataset's `post_count`
and is labelled as an approximation. Scale 150 pA is the LIF rheobase; a
postsynaptic neuron receiving all of its threshold-graph input from one partner
would receive 150 pA. This scale is declared here and not fitted.

The original `count/post_count` family is reported as **unavailable**, with the
reason, in the result JSON. It is not replaced silently by W7; W7 is a separate,
named family.

## 4. Sign policies

| ID | Policy | Definition |
| --- | --- | --- |
| S0 | `verified_primary` | Phase 4G verified-only; predicted fallback off; unknown edges excluded |
| S1 | `predicted_fallback` | predicted labels may supply a sign when no verified label exists |
| S2 | `unknown_zero` | unknown-sign edges retained with zero weight; must be numerically identical to S0 |
| S3 | `candidate_sign_reversal` | adversarial: the sign of every edge whose source is in the candidate group is reversed; all other edges unchanged |
| S4 | `global_sign_reversal` | adversarial: every signed edge is reversed |

S1 is a sensitivity condition measuring dependence on unverified annotation, not
a biological claim. S3 and S4 are adversarial tests: if the C effect depends on
the candidate neurons being excitatory, S3 should suppress it. They are not
proposed as alternatives to the primary policy.

## 5. Drive conditions

| ID | Condition | Definition |
| --- | --- | --- |
| D0 | `nominal` | 300 pA into every candidate neuron, 50–250 ms |
| D1 | `aggregate_matched` | amplitude chosen so that the aggregate outgoing signed weight from the candidate group equals the reference aggregate |

D1 is defined as:

```
A_x = clip(300 * sum_out_W0 / sum_out_Wx, 100, 1000)   pA
```

where `sum_out_Wx` is the total signed outgoing weight in pA from the candidate
group to any postsynaptic neuron in the threshold-5 graph under weight family x.
The clip bounds are declared to prevent a degenerate amplitude; a clipped value
is recorded. D1 is run for W0–W7. It separates a change in relative edge
weights from a change in total drive.

The stimulation itself is not a synaptic weight; its current is injected
directly. D1 therefore matches aggregate *synaptic* input from the candidate
group, not total injected current.

## 6. Grid and sample size

- Transform × sign at nominal drive (D0): W0–W7 × S0, plus W1/W2/W3 × S1, plus
  W0 × S2/S3/S4. That is 8 + 3 + 3 = 14 configurations.
- Matched drive (D1): W0–W7 × S0, 8 configurations.
- Total: 22 configurations.
- 10 draws per configuration. Ranked selection is fixed, so the draws are
  independent seeds for the simulator RNG only; with zero noise the simulator
  is deterministic and the 10 repeats are expected to be bit-identical. They
  are run to measure that expectation, and the result reports whether all 10
  hashes agree. They are **not** 10 independent biological replicates and are
  not treated as such.

Seed rule: `20261109 + 300000 + 100 * config_ordinal + draw_index`.

## 7. Endpoints

Primary:

- P1 total motor spikes;
- P2 number of JUMP-decoded windows.

Secondary: total spikes, non-stimulated spikes, active neurons, per-action
active fractions and peak per-window active fraction, NEUTRAL windows, LEFT and
RIGHT windows, time to first motor spike, aggregate outgoing weight from the
candidate group, and the derived amplitude for D1.

## 8. Analysis

- Each configuration is summarised by the mean of its 10 repeats (which are
  deterministic, so this is the single realised value) and by its range.
- A configuration is described as `silent` if it records zero motor spikes and
  `neutral_only` if no window decodes an action.
- For the primary endpoints, each non-reference transform at D0/S0 is compared
  with W0 using a two-sample permutation test over the 10 repeats of each
  configuration (10,000 permutations, seed 20261109). Because the repeats are
  expected to be identical, this test is reported but **not** interpreted as
  evidence of a distributional difference; it is a numerical equivalence check.
  The substantive comparison is the realised value under each transform, which
  is exactly reproducible.
- Holm–Bonferroni correction across the seven non-reference transforms at
  D0/S0.
- S2 must equal S0 exactly; any difference is a bug and is reported as a
  failure, not as a scientific result.
- No transform is selected as "best". The full table is reported.

## 9. Exclusions

None. A configuration that errors is recorded with its exception and counted.
A configuration with zero spikes is a result, not a missing value.

## 10. What this experiment cannot establish

- That any transform is the correct model of synaptic strength.
- That a synaptically driven response generalises beyond the fixed candidate
  group.
- That a JUMP decoder label corresponds to a biological jump command.
- That a sign policy change reflects biology; it reflects an annotation
  assumption.

## 11. Amendments

None at freeze time. Amendments, if any, are separate files named
`PHASE_4H3_WEIGHT_EXPERIMENT_AMENDMENT_<n>.md`, hashed, and referenced from the
result JSON.
