# Phase 6C - Mutual Information Between Archived FLY-SURFER Variables

**Status:** COMPLETE - ARCHIVED-DATA MI ONLY, NO NEW RECORDING  
**Phase:** 6C  
**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`  
**Generated (UTC):** 2026-11-10T08:57:51+00:00  
**Log base:** 2 (bits)  
**Config:** `configs\information_theory.yaml` SHA-256 `6770f4274037f08b2a324ecbfbd1c419235b062d61536f97b7e7b26ef6d19726`

## 1. Scope

`I(X;Y) = H(X) + H(Y) - H(X,Y)` and `I(X;Y|Z)` are estimated on artifacts
written by Phases 3B, 4F and 5E/5F. Nothing is simulated here, no
observation is synthesised, and every endpoint the archive cannot support
is recorded with its reason instead of being proxied.

## 2. Estimators

| Quantity | Definition |
|---|---|
| `I_plugin` | plug-in MI from empirical joint and marginal counts, bits |
| `bias_floor` | `(k_x - 1)(k_y - 1) / (2 N ln 2)` bits |
| `I_corrected` | `max(0, I_plugin - bias_floor)` |
| `normalised_mi` | `I / min(H_x, H_y)`, withheld below the entropy floor |
| `I(X;Y|Z)` | sample-weighted mean of the within-stratum plug-in MI |

## 3. Endpoint results

| Endpoint | Levels | N | Clusters | Raw MI | Bias floor | Corrected | Norm. MI | 95% CI |
|---|---|---|---|---|---|---|---|---|
| C01_decoder_mediated | 2x2 | 330 | 66 | 0.4336 | 0.0022 | 0.4314 | 0.6339 | [0.2660, 0.6133] |
| C02_disjoint_control | 2x2 | 330 | 66 | 0.0305 | 0.0022 | 0.0283 | 0.1144 | [0.0067, 0.0652] |
| C-03 fixed_complete | 4x4 | 400 | 10 | 0.5128 | 0.0162 | 0.4966 | 0.3144 | [0.4359, 0.6270] |
| C-03 plastic_complete | 4x4 | 400 | 10 | 0.4462 | 0.0162 | 0.4300 | 0.3014 | [0.3853, 0.5260] |
| C-03 fixed_random | 4x4 | 400 | 10 | 1.2930 | 0.0162 | 1.2767 | 0.7041 | [1.2519, 1.3503] |
| C-03 plastic_random | 4x4 | 400 | 10 | 1.2907 | 0.0162 | 1.2744 | 0.7051 | [1.2504, 1.3471] |
| C-07 | 4x4 | 2880 | 18 | 0.6040 | 0.0135 | 0.5905 | 0.3603 | [0.4763, 0.7625] |

Permutation null and p-value for the same endpoints:

| Endpoint | Null mean | Null sd | Null q95 | Null max | Observed | p |
|---|---|---|---|---|---|---|
| C01_decoder_mediated | 0.1743 | 0.0226 | 0.2176 | 0.2628 | 0.4336 | 0.00020 |
| C02_disjoint_control | 0.0305 | 0.0000 | 0.0305 | 0.0305 | 0.0305 | 1.00000 |
| C-03 fixed_complete | 0.0167 | 0.0076 | 0.0309 | 0.0534 | 0.5128 | 0.00020 |
| C-03 plastic_complete | 0.0166 | 0.0078 | 0.0313 | 0.0624 | 0.4462 | 0.00020 |
| C-03 fixed_random | 0.0165 | 0.0079 | 0.0309 | 0.0602 | 1.2930 | 0.00020 |
| C-03 plastic_random | 0.0166 | 0.0079 | 0.0311 | 0.0607 | 1.2907 | 0.00020 |
| C-07 | 0.0137 | 0.0026 | 0.0184 | 0.0254 | 0.6040 | 0.00020 |

## 4. Decoder-mediated information is not biological motor information

The Phase 4F decoder declares LEFT when LEFT-pool activity clears its gates, so this MI is induced by the decoder definition. It measures internal consistency of a computational map, not biological motor information.

The LEFT-pool association reaches 0.4336 bits (corrected 0.4314), which is a consistency check of the Phase 4F decision rule.
The disjoint control (C-02) reaches 0.0305 bits (corrected 0.0283) with a degenerate block null, so its p-value is uninformative and only the interval is meaningful.

## 5. Fixed versus plastic task information

Each seed contributes 40 evaluation episodes to a 4x4 table, whose analytic MI bias floor is 0.1623 bits. The per-seed contrast is therefore exploratory: the correction is first-order and does not repair the sample size.

| Contrast | Pairs | Mean diff | SD | Positive | Sign-flip p | Holm p |
|---|---|---|---|---|---|---|
| complete | 10 | -0.0863 | 0.1581 | 4/10 | 0.1250 | 0.2500 |
| random | 10 | -0.0025 | 0.0080 | 0/10 | 1.0000 | 1.0000 |

Per-condition per-seed MI (checkpoint 160) is listed in the JSON report.
A negative mean difference is reported as found: plastic training did not
increase cue-to-action mutual information relative to fixed weights.

## 6. Conditional information

`I(cue; action | condition) = 0.6040` bits over 2880 episodes in 6 strata (marginal pooled MI 0.3841 bits).
The conditional value exceeds the marginal because condition E carries a much stronger cue-to-action mapping than the other conditions; pooling mixtures across conditions masks that structure. This is a property of the synthetic task, not of any biological circuit.

## 7. Endpoints the archive cannot support

| Endpoint | Status | Reason |
|---|---|---|
| cue_to_neural_spike_count | unavailable | n_cue_spikes is the constant 8 in every archived 5E and 5F episode |
| neural_to_reward | unavailable | Per-episode spike counts carry no variation in conditions A-F (constant 12, or 11/12 in E), so a neural predictor of reward cannot be formed without inventing an observation. |

Both are recorded rather than replaced by a proxy variable.

## 8. Statistical decisions

- Permutation nulls use 5000 cluster-preserving draws.
- Confidence intervals use 2000 cluster bootstrap resamples.
- Multiple comparisons: Holm-Bonferroni over the two C-06 contrasts.
- Smallest attainable p with this null is 0.00020.
- The independent unit is the run for 4F windows, the seed for 5F episodes and
  the replicate for 5E episodes. Correlated windows are never treated as
  independent observations.

## 9. Validation

`tests/test_information.py` holds 49 synthetic unit tests. They cover MI
symmetry, non-negativity, hand-computed 2x2 values, perfect dependence and
independence, conditional MI with a confounder and with a collider, bias
floors, permutation reproducibility and degenerate nulls, and bootstrap
interval behaviour. No synthetic observation enters this report.

`tests/test_information_analysis.py` adds 16 focused tests over the
readers and report files, including a JSON/Markdown agreement check on
every endpoint value. The full suite passes with 748 tests and no
failures.

## 10. Limitations

- Every neural variable here is a decoder-derived score or an aggregate spike
  count, never a recorded population response.
- The C-01 association is produced by the decoder definition itself.
- The C-02 block null is degenerate; the interval is the only usable summary.
- Per-seed 5F tables hold 40 episodes for 16 cells, so their MI bias floor is
  0.1623 bits and the paired contrast is exploratory.
- Phase 5E supplies three replicates per condition, so its conditional
  interval rests on 18 clusters.
- No claim is made about biological coding, representational efficiency or
  information transmission in the fly nervous system.

## 11. Integrity and reproducibility

- Protected baseline files checked: 37, failures: 0
- Protected paths dirty: 0
- Staged files: 0
- Pre-existing modified tracked files: 13
- Runtime: 31.487 s

Re-run with `python experiments/phase_6c/run_mutual_information.py` then
`python experiments/phase_6c/build_report.py`. Permutation, bootstrap and
configuration seeds are recorded in the configuration and every result.
