# Phase 6 Information Analysis (archived artifacts)

Status: **complete** (analysis only; no simulation, training or archived file was modified).

Reproduce:

```
python -m experiments.phase_6.run_information_analysis
```

Add `--quick` for a reduced-permutation smoke run and `--no-figures` to skip plots.

Machine-readable output: `experiments/results/phase_6/information_analysis.json`
Figures: `experiments/results/phase_6/figures/*.png`
Config (declared before estimation): `configs/phase_6_information.yaml`
Runner: `experiments/phase_6/run_information_analysis.py`

The runner recorded and re-verified the SHA-256 of every source artifact it
read; all seven hashes matched the files on disk. Two full runs produced
byte-identical results after removing `generated_at_utc` and `runtime_s`.

## Estimators and inference

- Plug-in discrete Shannon entropy and mutual information in bits, each
  reported with its analytic bias floor `(k_x-1)(k_y-1)/(2 N ln 2)`.
- Cluster-preserving block permutation whenever repeated observations share a
  run, seed or replicate; free permutation when each observation is its own
  cluster. `permutation_null` now ignores cluster labels under `scheme="free"`
  (previously a free request with singleton clusters was silently a no-op).
- Exact enumeration replaces Monte Carlo when the number of within-cluster
  assignments is at most 10,000. The 3-seed sensory design therefore reports
  the exact p (6/216), not a Monte Carlo approximation.
- Cluster bootstrap percentile intervals (2,000 resamples), withheld below
  three clusters.
- Holm correction over the declared confirmatory family (two contrasts) and
  over the four exploratory reward contrasts.
- Every endpoint records n, missing count, declared levels, observed levels,
  expected per-cell support, the full contingency table, the permutation
  scheme and seed, and warnings. Unsupported endpoints are recorded with a
  reason instead of a number.

## A. Sensory input -> neural population (Phase 3A.5)

| Endpoint | n | clusters | MI (bits) | bias floor | exact p |
|---|---|---|---|---|---|
| exact four-neuron vector | 9 | 3 (mapping seeds) | 1.5850 | 0.3206 | 0.0278 |
| binary / cap 1 / 2 / 4 / 8 | 9 | 3 | 1.5850 | 0.3206 | 0.0278 |

The response is a deterministic, one-to-one function of distance under every
declared code; all six discretisations return the identical estimate. The
table has 9 observations in 9 cells (expected 1 per cell) and is flagged
sparse. This checks that the archived encoding is invertible; it is not a
statistical discovery and cannot be a confirmatory claim. The cluster
bootstrap interval collapses to the point estimate because the three mapping
seeds produce identical response vectors.

Population-size sweep (descriptive; one mapping seed, 3 runs per size):

| size | joint MI | sum of individual MI | best individual |
|---|---|---|---|
| 4 | 1.5850 | 2.7549 | 0.9183 |
| 8 | 1.5850 | 6.4281 | 0.9183 |
| 12 | 1.5850 | 9.1830 | 0.9183 |
| 16 | 1.5850 | 12.8561 | 0.9183 |
| 24 | 1.5850 | 18.3659 | 0.9183 |

The joint code stays at `log2(3)` bits while summed single-neuron estimates
grow linearly because the active neurons repeat the same distance identity.
The sum double-counts shared information and is reported only as descriptive
bookkeeping. With three observations per size the joint bias floor is 0.962
bits; no inference is attached to this sweep.

## B. Baseline versus plasticity (Phase 5F, the only confirmatory family)

Observational unit: seed (10); each seed contributes 40 evaluation episodes to
both arms. Per-seed bias floor 0.1623 bits, common to both arms with equal
episode counts, so it cancels in the paired difference.

| Condition | pooled MI at checkpoint 160 | per-seed mean (sd) |
|---|---|---|
| fixed_complete | 0.5128 | 0.6126 (0.1551) |
| plastic_complete | 0.4462 | 0.5262 (0.1123) |
| fixed_random | 1.2930 | 1.3547 (0.0692) |
| plastic_random | 1.2907 | 1.3522 (0.0698) |

Paired contrasts (exact two-sided sign-flip over 10 pairs):

| Contrast | mean Δ (bits) | bootstrap 95% CI | pairs +/- | p | Holm p | rejected |
|---|---|---|---|---|---|---|
| plastic - fixed, complete | -0.0863 | [-0.1751, 0.0052] | 4 / 6 | 0.125 | 0.250 | no |
| plastic - fixed, random | -0.0025 | [-0.0075, 0.0000] | 0 / 1 (9 ties) | 1.000 | 1.000 | no |

Checkpoint-0 control: fixed and plastic weights are identical, and all ten
paired differences are exactly 0.0 in both comparisons. The complete-wiring
contrast is negative and not rejected; the random-wiring control shows nine
exactly zero paired differences and one small negative difference. Neither
contrast supports a claim that plasticity increased cue->action information in
this task. The exact sign-flip test cannot report p below 0.002 with ten pairs.

## C. Reward-modulation ablation (Phase 5E, exploratory)

Matched validation confirmed that A, B, C, D and F share the identical cue
stream by replicate and episode. G is excluded because it records no chosen
action. Three replicates; the exact sign-flip test has eight assignments and
cannot report p below 0.25.

| Condition | cue->action MI (n=480) | per-replicate values |
|---|---|---|
| A fixed weights, outcome reward | 0.4821 | 0.5137, 0.4430, 0.5165 |
| B plastic, outcome reward | 0.4215 | 0.3754, 0.3963, 0.5200 |
| C plastic, zero reward | 0.4821 | identical to A |
| D plastic, shuffled reward | 0.4668 | 0.5009, 0.3949, 0.5417 |
| F plastic, traces disabled | 0.4821 | identical to A |

| Contrast | mean Δ (bits) | exact p | Holm p |
|---|---|---|---|
| B - A (outcome vs fixed) | -0.0605 | 0.50 | 1.0 |
| B - C (outcome vs zero reward) | -0.0605 | 0.50 | 1.0 |
| B - D (outcome vs shuffled reward) | -0.0486 | 0.50 | 1.0 |
| B - F (outcome vs traces disabled) | -0.0605 | 0.50 | 1.0 |

A, C and F produce identical chosen actions in every replicate, so their
contrasts with B coincide and are not independent evidence. No significance
claim is possible from this ablation.

## D. Neural pool activity -> decoded motor output (Phase 4F, descriptive)

330 decoder windows nested in 66 runs; five sequential 50 ms windows per run.
The decoder thresholds the same pool activity used as the predictor, so every
estimate is circular by construction and is labelled as an internal-consistency
check.

| Predictor code | MI (bits) | bias floor | corrected | p | run-bootstrap 95% CI |
|---|---|---|---|---|---|
| any pool active, whole-row pattern | 1.1841 | 0.0459 | 1.1382 | 0.0005 | [0.9712, 1.3945] |
| pool spike count capped at 4 | 1.2750 | 0.0590 | 1.2160 | 0.0005 | [1.0330, 1.4725] |
| gate level 0.10 | 1.3659 | 0.0459 | 1.3200 | 0.0005 | [1.1405, 1.5480] |
| gate level 0.20 | 1.3659 | 0.0459 | 1.3200 | 0.0005 | [1.1319, 1.5538] |

Gate cuts 0.10 and 0.20 yield identical code vectors because no observed
active fraction lies strictly between them; the runner records this note.
By window (free permutation, 66 runs each):

| Window | MI (bits) | p |
|---|---|---|
| 0: 50-100 ms | 1.1841 | 0.0005 |
| 1: 100-150 ms | 1.3172 | 0.0005 |
| 2: 150-200 ms | 1.3172 | 0.0005 |
| 3: 200-250 ms | 1.3172 | 0.0005 |
| 4: 250-300 ms | not estimable | - |

Window index 4 has every state NEUTRAL and no pool activity, so both variables
are constant and no permutation distribution exists. The high MI values show
that the decoder is internally consistent; they do not show that the brain
transmits motor commands, and the sequential windows in a run are not
independent trials.

## E. Conditional mutual information (Phase 5E, exploratory)

`I(cue; action | condition)` over conditions A-F, 2,880 training episodes
nested in 18 replicate clusters (6 conditions x 3 replicates; coverage
validated exactly).

| Quantity | Value |
|---|---|
| marginal I(cue; action) | 0.3841 bits |
| conditional I(cue; action | condition) | 0.6040 bits |
| mean per-stratum bias floor | 0.0135 bits |
| corrected conditional MI | 0.5905 bits |
| stratified permutation p | 0.0005 |
| cluster-bootstrap 95% CI | [0.4743, 0.7710] |

Conditioning increases the estimate because within a condition the cue-action
relation is stronger than in the pooled table. Conditioning removes
between-condition composition; it does not identify a causal pathway. This
analysis is exploratory and has 18 clusters.

## Unavailable endpoints

Every entry carries machine-checked evidence in the JSON.

| ID | Endpoint | Reason |
|---|---|---|
| U01 | sensory input -> neural activity in real replay | Phase 3B2C stores aggregate spike counts only; no per-neuron/per-frame arrays |
| U02 | spike-train entropy | Archived raw-spike arrays are single trials with at most a few spikes per neuron |
| U03 | membrane-potential entropy | Membrane potentials were never persisted |
| U04 | neural-level baseline vs plasticity | Phase 5 BANC has six named conditions but three distinct spike hashes, five sequential windows and one decoded sequence; deterministic repeats are not independent replicates |
| U05 | neural-level reward modulation | Same Phase 5 BANC limitation; no independent per-neuron arm |
| U06 | cue -> neural response | Per-episode cue spike count is constant (8), so a constant response cannot carry cue information |
| U07 | neural -> reward | Per-episode spike counts are constant in conditions A-F |

No comparison was manufactured to fill these gaps.

## Interpretation limits

- Mutual information does not establish causation or biological perception.
- Decoding does not prove the brain uses the decoded information.
- Structural connectivity does not establish physiological information flow.
- Phase 5 weight changes are outputs of a declared three-factor rule, not
  evidence of biological learning; no behavioural evidence exists.
- Deterministic repeated runs are not independent replicates and were never
  treated as such.
- The Phase 4F motor estimate is circular by construction; the random-wiring
  and reward-ablation analyses have too few independent replicates for
  significance claims.

## Verification

- `tests/test_phase_6_information.py` adds 25 focused tests (population coding,
  matching validation, endpoint policy, free/exact permutation semantics,
  reproducibility, matched Phase 5 conditions).
- Information test files: 90 passed.
- Full suite: 999 passed, 3 skipped.
- Two runs of the default command produced identical results after excluding
  timestamps and runtime.
