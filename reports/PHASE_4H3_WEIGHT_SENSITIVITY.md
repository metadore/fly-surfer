# FLY-SURFER — Phase 4H.3 Pre-Registered Weight and Sign Sensitivity

Status: **PASS WITH LIMITATIONS**
Date: 2026-11-08
Phase: 4H.3
Parent protocol: `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`
Pre-registration: `reports/PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md`

Phase 4H.3 asks whether the Phase 4G motor result survives the pre-registered
weight transforms, whether it depends on the transmitter sign policy, and
whether it is a transformation effect, a gain effect or a stimulation-amplitude
effect. It runs the full 22-configuration grid once, reports every cell and
selects no configuration as best. It is a sensitivity analysis of a simulated
decoder output, not evidence of biological motor control.

The headline is that the JUMP output is **not invariant to the weight
transform at fixed nominal amplitude**: only W0, the uncapped W0 (W5) and the
count-capped W6 produce it at 300 pA. But the disappearance under W1–W4 and W7
at nominal drive is largely a **gain** effect: when the injected amplitude is
raised so the aggregate outgoing synaptic weight matches the reference, W1–W6
all produce JUMP windows, and only W7 (whose matched amplitude was clipped)
remains silent. The result also depends on the candidate neurons being
excitatory: reversing signs silences it.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4h/weight_sensitivity.py` | Executes the 22-configuration grid and writes the analysis |
| `experiments/phase_4h/common.py` | Shared world loader, policies, simulator, metrics, hashing, permutations |
| `experiments/results/phase_4h/weight_sensitivity.json` | All 220 run records, policy definitions, summaries, tests, integrity |
| `experiments/results/phase_4h/weight_sensitivity.checkpoint.jsonl` | Append-only per-run checkpoint (220 records) |
| `reports/PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md` | Frozen design, endpoints and analysis (SHA-256 `372ec71c…bece1994`) |
| `tests/test_phase_4h_runners.py` | Focused tests for statistics and hash-equivalence helpers |

Run:

```
python -m experiments.phase_4h.weight_sensitivity
```

220 runs (22 configurations × 10 repeats), 0 failures. The 219 uninterrupted
runs summed to 445.3 s (mean 2.03 s, median 2.01 s, max 3.74 s). One run
(`D0_W0_S2`, draw 9) recorded 8,704.9 s of ambient wall time because the
machine was suspended; it is an instrumentation artefact, not simulation time,
and it dominates the reported total of 9,219.7 s.

## 1. Question and design

Phase 4G.5 reported that the condition C JUMP output disappeared under
`linear` and `log1p` transforms and under power exponent 0.5, but survived the
uncapped power transform. Those checks were one run each, with a single seed,
and were not corrected for multiple comparisons. 4H.3 turns them into a frozen
grid:

1. Is any decoder output stable across the pre-registered weight transforms?
2. Does the result depend on the sign policy?
3. Does replacing nominal stimulation amplitude with matched aggregate synaptic
   input change the answer?
4. Is the JUMP result an artefact of the cap, the exponent or the drive
   amplitude?

The candidate group is fixed: the Phase 4G condition C set of 64
connectivity-ranked verified-excitatory VNC intrinsic neurons (candidate index
SHA-256 `670139f67e804e2705b1e05f5b45bd47258a1efefe6f79cc47d6f3a9cee457f1`).
Only weight, sign and drive vary.

The grid was frozen and hashed before execution. The runner aborts on a
protocol or pre-registration hash mismatch. The stored pre-registration hash is
`372ec71cd171431e4b7c4f1940eaf54dce9a19742c463373f1da39cdbece1994`, matching
the frozen file.

## 2. Fixed conditions

| Item | Value |
| --- | --- |
| Graph | BANC v888, threshold 5, 172,433 nodes, 1,535,710 edges, 18,552,546 synapses, 24,320 isolated |
| Graph artifact | `datasets/processed/banc_v888/banc_graph_t5.npz`, SHA-256 `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Candidate set | Phase 4G condition C, 64 fixed neurons |
| Stimulation window | 50–250 ms, all candidate neurons |
| Integration | dt 0.5 ms, 300 ms duration, 600 steps |
| Decoder | Phase 4F, unchanged: 50 ms windows, step 50 ms, activation 0.20, release 0.10, ≥5 spikes and ≥3 active neurons, priority LEFT/RIGHT/JUMP |
| Background / noise | 0 pA / 0 pA |
| Spike recording cap | 5,000,000 |
| Sign policy | S0 verified-only unless sign is the factor under test |
| Weight reference | W0 `min(5.0 * count^0.75, 300 pA)` |
| Mapping config | SHA-256 `a3d57abf1d2e3aad7f9a1fc33567b95ca62e065b6b20a7835e5e7988a51f6ebd` |
| Seeds | `20261109 + 300000 + 100*config_ordinal + draw_index` |

## 3. Weight families

Weight is a monotone transform of the integer structural synapse count
`count`. It is never `norm` and never a conductance.

| ID | Definition | Reference role |
| --- | --- | --- |
| W0 | `min(5.0 * count^0.75, 300)` | Phase 4G primary |
| W1 | `min(0.5 * count, 300)` | linear, capped |
| W2 | `10 * log(1 + count)` | log1p, uncapped |
| W3 | `min(5.0 * count^0.5, 300)` | power 0.5 |
| W4 | `min(0.5 * count, 300)` | power 1.0; declared equivalent to W1 |
| W5 | `5.0 * count^0.75` | uncapped W0 |
| W6 | `5.0 * min(count, 60)` | count capped at 60 synapses |
| W7 | `min(150 * count / in_synapse_sum(dst), 300)` | graph-local approximation of `count / post_count` |

W4 is included to verify the declared equivalence with W1: W1 and W4 produced
bit-identical spike and decision hashes for all ten repeats
(`w4_equals_w1` true).

W7 is explicitly an approximation. The dataset's `post_count` field is not in
the repository, so the original `count / post_count` family is reported as
**unavailable**, not silently replaced. W7 uses the sum of in-edge synapse
counts in the threshold-5 graph as the denominator and is a separate, labelled
family.

## 4. Sign policies

| ID | Policy | Definition |
| --- | --- | --- |
| S0 | verified primary | verified-only; predicted fallback off; unknown edges excluded |
| S1 | predicted fallback | predicted labels may supply a sign when no verified label exists |
| S2 | unknown zero | unknown-sign edges retained with zero weight; must equal S0 |
| S3 | candidate sign reversal | adversarial: reverse every edge whose source is in the candidate group |
| S4 | global sign reversal | adversarial: reverse every signed edge |

S2 is a numerical check: retaining unknown edges at zero weight must be
identical to excluding them. It is: spike hash, decision hash and every metric
are equal (`s2_equals_s0` true).

S1 adds a large number of edges: under S0 the policy signs 683,100 edges and
leaves 107,141 neurons unannotated; under S1 it signs 1,391,473 edges, of which
62,096 neurons are predicted-excitatory, 12,410 predicted-inhibitory and 14,962
predicted-modulator-only. This makes the S1 comparison informative about the
network, but note that all candidate neurons are already verified-excitatory,
so the aggregate outgoing weight from the candidate group is unchanged by S1.

## 5. Drive conditions

D0 is the nominal 300 pA into every candidate neuron. D1 matches the aggregate
outgoing signed synaptic weight from the candidate group to the reference:

```
A_x = clip(300 * sum_out_W0 / sum_out_Wx, 100, 1000) pA
```

| Weight | Aggregate out (pA) | Ratio W0/Wx | D1 amplitude (pA) | Clipped |
| --- | ---: | ---: | ---: | --- |
| W0 | 243,230.23 | 1.000 | 300.0 | no |
| W1 | 60,724.50 | 4.005 | 1,000.0 | yes (required 1,201.64) |
| W2 | 137,608.57 | 1.768 | 530.27 | no |
| W3 | 106,619.02 | 2.281 | 684.39 | no |
| W4 | 60,724.50 | 4.005 | 1,000.0 | yes (required 1,201.64) |
| W5 | 244,432.55 | 0.995 | 298.52 | no |
| W6 | 478,895.00 | 0.508 | 152.37 | no |
| W7 | 21,171.84 | 11.488 | 1,000.0 | yes (required 3,446.51) |

D1 matches total synaptic input from the candidate group, not total injected
current. Clipping is declared before execution and recorded. The W1/W4 and W7
D1 tests are therefore partial matches: W1/W4 reach 83% of the required
amplitude and W7 reaches 29%.

## 6. Results at nominal drive (D0, S0)

Ten repeats per configuration; all ten spike and decision hashes are identical
inside every configuration, so the table is the realised value.

| Config | Weight | Amplitude (pA) | Motor spikes | JUMP windows | Total spikes | JUMP active fraction | Label |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| D0_W0_S0 | W0 | 300.0 | 492 | 4 | 1,296 | 0.60 | action |
| D0_W1_S0 | W1 | 300.0 | 5 | 0 | 723 | 0.00 | NEUTRAL-only |
| D0_W2_S0 | W2 | 300.0 | 0 | 0 | 755 | 0.00 | silent |
| D0_W3_S0 | W3 | 300.0 | 0 | 0 | 740 | 0.00 | silent |
| D0_W4_S0 | W4 | 300.0 | 5 | 0 | 723 | 0.00 | NEUTRAL-only |
| D0_W5_S0 | W5 | 300.0 | 481 | 4 | 1,281 | 0.60 | action |
| D0_W6_S0 | W6 | 300.0 | 1,295 | 4 | 2,204 | 0.95 | action |
| D0_W7_S0 | W7 | 300.0 | 0 | 0 | 704 | 0.00 | silent |

Three observations:

1. **The cap is not the cause.** W5 is W0 without the 300 pA cap and is nearly
   identical (481 vs 492 motor spikes, both 4 JUMP windows, same JUMP active
   fraction 0.60). Only 643 of 1,535,710 edges (0.042%) reach the W0 cap, at a
   structural count of about 234.9 synapses. The uncapped and capped power
   transforms therefore describe almost the same network.
2. **The exponent and the linear scale matter at fixed amplitude.** W3 (power
   0.5) and W1/W4 (linear 0.5 pA per synapse) are much weaker than W0 at the
   same 300 pA. W1/W4 produce 5 motor spikes in 5 NEUTRAL windows; W3 is
   completely silent at the motor pool. W2 (log1p) is also silent at the motor
   pool, although it records 755 total spikes.
3. **W6 is stronger, not equivalent.** Capping `count` at 60 synapses instead
   of capping the transformed weight raises the aggregate outgoing weight to
   478,895 pA (1.97× the reference), and produces 1,295 motor spikes and a JUMP
   active fraction of 0.95. It preserves the decoder label but not the
   magnitude.

No configuration produced LEFT or RIGHT windows. Every non-silent
configuration produced NEUTRAL windows in the other decoder windows.

## 7. Sign-policy results (D0)

| Config | Weight | Policy | Motor spikes | JUMP windows | Total spikes | Label |
| --- | --- | --- | ---: | ---: | ---: | --- |
| D0_W0_S0 | W0 | S0 | 492 | 4 | 1,296 | action |
| D0_W1_S1 | W1 | S1 predicted fallback | 5 | 0 | 723 | NEUTRAL-only |
| D0_W2_S1 | W2 | S1 predicted fallback | 0 | 0 | 755 | silent |
| D0_W3_S1 | W3 | S1 predicted fallback | 0 | 0 | 740 | silent |
| D0_W0_S2 | W0 | S2 unknown zero | 492 | 4 | 1,296 | action |
| D0_W0_S3 | W0 | S3 candidate reversal | 0 | 0 | 605 | silent |
| D0_W0_S4 | W0 | S4 global reversal | 0 | 0 | 605 | silent |

- S1 is bit-identical to S0 for W1, W2 and W3, despite adding 708,373 signed
  edges to the policy. The extra predicted edges are downstream of
  non-candidate neurons and do not change the output within 300 ms in these
  near-silent configurations. S1 was not run with W0, so this does **not**
  establish that the reference result is invariant to predicted fallback.
- S3 reverses the sign of 5,028 edges whose source is in the candidate group.
  The response is completely silenced (0 motor spikes, 605 total spikes, 5
  NEUTRAL windows). The reference result therefore depends on the candidate
  neurons being excitatory under the verified annotation.
- S4 reverses all 683,100 signed edges and also silences the response (0 motor
  spikes, 605 total spikes). The equality of S3 and S4 total spikes is not
  interpreted: both are network-wide perturbations that remove the motor
  response, and their detailed spike patterns differ.
- S2 equals S0 on every metric, as required. Any difference would have been a
  bug, not a result.

## 8. Matched-drive results (D1, S0)

| Config | Weight | Amplitude (pA) | Motor spikes | JUMP windows | Total spikes | JUMP active fraction | Label |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| D1_W0_S0 | W0 | 300.0 | 492 | 4 | 1,296 | 0.60 | action |
| D1_W1_S0 | W1 | 1,000.0 | 399 | 4 | 2,752 | 0.40 | action |
| D1_W2_S0 | W2 | 530.3 | 220 | 4 | 1,649 | 0.65 | action |
| D1_W3_S0 | W3 | 684.4 | 317 | 4 | 2,089 | 0.60 | action |
| D1_W4_S0 | W4 | 1,000.0 | 399 | 4 | 2,752 | 0.40 | action |
| D1_W5_S0 | W5 | 298.5 | 486 | 4 | 1,283 | 0.60 | action |
| D1_W6_S0 | W6 | 152.4 | 162 | 2 | 328 | 0.70 | action |
| D1_W7_S0 | W7 | 1,000.0 | 0 | 0 | 2,304 | 0.00 | silent |

At matched aggregate input, every transform except W7 produces at least two
JUMP windows. W1/W4 recover from 5 motor spikes and 0 JUMP windows to 399 motor
spikes and 4 JUMP windows, even though their amplitude was clipped below the
exact match. W2 recovers from silence to 220 motor spikes and 4 JUMP windows;
W3 from silence to 317 and 4. W5 and W6 remain action-producing, with slightly
different magnitudes.

W7 remains silent with 2,304 total spikes and no JUMP neuron active. Its
matched amplitude would be 3,446.5 pA, but the declared clip at 1,000 pA
delivers only 29% of the reference aggregate. The D1 test for W7 is therefore
inconclusive: it does not establish that target-normalised weights cannot
produce the decoder output, only that they do not at one third of the matched
amplitude. This is reported as a limitation, not as a rejection of W7.

## 9. Transformation, gain or amplitude?

The grid separates three factors:

- **Transformation.** At fixed 300 pA the output ranges from silence (W2, W3,
  W7) through a weak NEUTRAL-only response (W1, W4) to the full action response
  (W0, W5, W6). The transform changes the relative weighting of strong and weak
  edges and therefore the recruited circuit.
- **Gain.** The disappearance of JUMP under W1–W4 at D0 is largely a gain
  effect. When the injected amplitude is increased to match aggregate outgoing
  weight, those configurations produce JUMP windows. The *qualitative* decoder
  output is restored by compensating for the weaker transform.
- **Amplitude.** W6 shows the converse: at a matched amplitude of only 152.4 pA
  it still produces 162 motor spikes and 2 JUMP windows, because its weight
  distribution is concentrated differently (many edges at the 60-synapse cap).
  W2 needs 530.3 pA and produces 220 motor spikes and 4 JUMP windows. Amplitude
  alone does not order the outcomes; the interaction between amplitude and the
  weight distribution does.

- **Cap.** W5 (uncapped W0) is nearly identical to W0, and the cap binds on
  0.042% of edges. The JUMP result under W0 is not a cap artefact.

The correct summary is therefore not "JUMP survives all transforms" or "JUMP
survives only the power transform". At the pre-registered nominal amplitude,
JUMP survives only W0, W5 and W6. At matched aggregate input, it survives W1–W6
and not W7, whose match was clipped. The result is gain-sensitive and
transform-sensitive, and it is not established for target-normalised weights
within the declared amplitude bounds.

## 10. Permutation tests and Holm correction

The pre-registration specifies a two-sample permutation test over the ten
repeats of each configuration, with 10,000 permutations, as a numerical
equivalence check. Because the ten repeats are bit-identical under zero noise,
any non-zero difference between two configurations yields the minimum
attainable p of 1/10,001 = 0.0001. The test therefore does not provide
distributional evidence; it records whether the realised values differ.

| Endpoint | W1 | W2 | W3 | W4 | W5 | W6 | W7 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 observed difference (vs W0) | 487 | 492 | 492 | 487 | 11 | −803 | 492 |
| P1 p | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0001 |
| P2 observed difference | 4 | 4 | 4 | 4 | 0 | 0 | 4 |
| P2 p | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 1.0 | 1.0 | 0.0001 |
| Holm-adjusted P1 | 0.0007 | 0.0007 | 0.0007 | 0.0007 | 0.0007 | 0.0007 | 0.0007 |
| Holm-adjusted P2 | 0.0007 | 0.0007 | 0.0007 | 0.0007 | 1.0 | 1.0 | 0.0007 |

Holm rejects all seven transforms for P1 and W1–W4 and W7 for P2; W5 and W6
are not rejected for P2 because their JUMP window count equals the reference.
These labels describe numerical inequality, not sampling evidence. In
particular, W5 differs by 11 motor spikes and is still "significant" at the
permutation floor; the reader should use the observed values, not the p column,
as the result.

## 11. What 4H.3 shows and does not show

**Shows.** At the pre-registered nominal 300 pA drive, the Phase 4G JUMP output
is not stable across the eight weight families: only W0, W5 and W6 produce it.
The cap is not responsible; uncapped W0 is nearly identical. The result is
sensitive to the candidate sign: reversing candidate-source or all signed edges
silences it. It is also gain-sensitive: matching aggregate outgoing weight
restores JUMP under W1–W6, so the nominal-amplitude failures of W1–W4 are not
evidence that those transforms cannot drive the decoder. W4 and W1 are exactly
equivalent, and S2 and S0 are exactly equivalent, as designed. All ten repeats
are bit-identical in every configuration, confirming determinism at zero noise.

**Does not show.** It does not establish which transform is biologically
correct, because none is a conductance and all are structural-count
approximations. It does not establish that the result generalises beyond the
fixed condition C candidate group. It does not resolve W7: the target-normalised
family is tested only at 29% of its matched amplitude, and the dataset's
`count / post_count` family is unavailable. It does not provide distributional
evidence: the ten repeats are deterministic and the permutation p-values are
numerical checks. It does not show that predicted transmitter labels are
irrelevant to the reference result: S1 was run only with W1–W3, whose outputs
happen to be unchanged. It does not show that a JUMP decoder label is a
biological jump command.

## 12. Integrity and reproducibility

Before and after execution the runner checked 37 protected paths covering the
root README, FAFB and BANC processed artifacts, dataset manifests, Phase 4D–4G
code and outputs, the Phase 3 sensory pipeline, and the parent protocol. All 37
passed before and after; `protected_unchanged` is true. No Phase 4G output was
overwritten. No file was staged, committed or pushed.

Reproducibility fields recorded: protocol and pre-registration SHA-256, mapping
config SHA-256, graph artifact SHA-256, graph threshold and counts, candidate
index SHA-256, every policy definition, per-configuration aggregate outgoing
weight, per-configuration amplitude, seed rule, per-run seeds, spike and
decision hashes, per-run wall time and memory. Software: Python 3.13.14,
NumPy 2.3.4, pandas 2.3.3, Windows 11.

Runtime: 220 runs, 0 failures. The 219 uninterrupted runs summed to 445.3 s
(mean 2.03 s, median 2.01 s, max 3.74 s). One run recorded 8,704.9 s because
the machine was suspended; total ambient wall time 9,219.7 s includes that
suspension and should not be read as compute cost. Maximum retained simulation
arrays 109.19 MB. Sparse graph operations only; bounded 5,000,000-spike
recorder; no dense matrices or graph copies.

## 13. Limitations

1. No transform is established as the correct model of synaptic strength.
   Weights are monotone transforms of structural synapse counts, not
   conductances.
2. The result is conditional on the fixed Phase 4G condition C group. 4H.2
   shows that other rules and sizes can also produce JUMP, so 4H.3 is not a
   claim about selection.
3. The target-normalised family using the dataset's `post_count` is
   unavailable. W7 is a labelled graph-local approximation and its matched-drive
   test is clipped to 29% of the required amplitude.
4. Sign policies are annotation assumptions, not measured biology. S1 adds
   predicted labels but was run only with W1–W3; it is not a test of the
   reference configuration.
5. The ten repeats are deterministic and provide no inferential replication.
   Permutation tests are numerical equivalence checks with a p floor of 0.0001.
6. The D1 drive matches aggregate *synaptic* input from the candidate group, not
   total injected current, and it is clipped to 100–1,000 pA by design.
7. A JUMP decoder label is not a biological jump command, and a silent motor
   pool is not evidence that the network is biologically inactive.

## 14. Reproduction

```
python -m experiments.phase_4h.weight_sensitivity
python -m experiments.phase_4h.weight_sensitivity --configs D0_W0_S0,D0_W1_S0 --repeats 2
```

The runner resumes from `weight_sensitivity.checkpoint.jsonl`. The output is
written atomically to `experiments/results/phase_4h/weight_sensitivity.json`.
Focused tests:

```
python -m pytest tests/test_phase_4h_runners.py -q -p no:anyio
```
