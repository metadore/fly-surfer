# Phase 6B - Shannon Entropy of Archived FLY-SURFER Variables

**Status:** COMPLETE - ARCHIVED-DATA ENTROPY ONLY, NO NEW RECORDING  
**Phase:** 6B  
**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`  
**Generated (UTC):** 2026-11-10T08:57:50+00:00  
**Log base:** 2 (bits)  
**Config:** `configs\information_theory.yaml` SHA-256 `6770f4274037f08b2a324ecbfbd1c419235b062d61536f97b7e7b26ef6d19726`

## 1. Scope

Every quantity below is estimated from artifacts written by earlier phases.
No neural recording was performed, no simulation was run, and no missing
observation was imputed or synthesised.

## 2. Definitions

| Symbol | Definition |
|---|---|
| `H(X)` | plug-in Shannon entropy `-sum p(x) log2 p(x)` in bits |
| `H(X,Y)` | plug-in joint entropy over the product support |
| `H(X|Y)` | `H(X,Y) - H(Y)`, clipped at zero |
| `I(X;Y)` | `H(X) + H(Y) - H(X,Y)` (Phase 6C) |
| Miller-Madow | `+ (K_obs - 1) / (2 N ln 2)` bits, first-order bias correction |

## 3. Data sources

| Archived source | SHA-256 prefix |
|---|---|
| replay_0101 | `4a4d6ea656fe6f6a...` |
| segment_0_99 | `a0f7f4917b5588d6...` |
| segment_200_299 | `c42b31464e655d5e...` |

## 4. Discretisation declared before estimation

| Endpoint | Levels | Rule |
|---|---|---|
| E-01 event class | 6 | archived event label, declared order |
| E-02 frame event count | 4 | distinct event classes per frame, capped at 3 |
| E-03 decoder state | 4 | archived decoded state per 50 ms window |
| E-04 decoder score | 3 | equal-width bins over the declared [0, 1] range |
| E-05 reward | 3 | declared levels {-1, 0, +1} |

## 5. Marginal entropy

| Endpoint | Provenance | N | k | H plug-in | H MM | 95% CI | Clusters |
|---|---|---|---|---|---|---|---|
| E01_event_class_marginal | measured | 515 | 6/6 | 2.4766 | 2.4836 | [2.4146, 2.5100] | 231 |
| E02_frame_event_count | derived | 300 | 4/4 | 1.8960 | 1.9033 | [1.8080, 1.9483] | 30 |
| E03_decoder_state | simulated | 330 | 4/4 | 1.4568 | 1.4634 | [1.1998, 1.6330] | 66 |
| E04_decoder_score_bin | simulated | 330 | 3/3 | 1.0907 | 1.0950 | [0.8659, 1.2515] | 66 |

Reward entropy per Phase 5E condition:

| Cond | Label | N | H plug-in | H MM | 95% CI | Clusters |
|---|---|---|---|---|---|---|
| A | fixed_weights_outcome_reward | 480 | 0.7177 | 0.7192 | [0.6098, 0.8113] | 3 |
| B | plastic_outcome_reward | 480 | 0.4821 | 0.4836 | [0.3612, 0.6690] | 3 |
| C | plastic_zero_reward | 480 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 3 |
| D | plastic_shuffled_reward | 480 | 1.5085 | 1.5115 | [1.4502, 1.5589] | 3 |
| E | plastic_random_connectivity | 480 | 0.4949 | 0.4964 | [0.4489, 0.5436] | 3 |
| F | plastic_traces_disabled | 480 | 0.7177 | 0.7192 | [0.6098, 0.8113] | 3 |
| G | conventional_perceptron | 480 | 0.1344 | 0.1359 | [0.1344, 0.1344] | 3 |

## 6. Joint and conditional entropy

- H(event class, segment) = 4.0356 bits
- H(event class) = 2.4766 bits
- H(event class | segment) = 2.4729 bits
- I(event class; segment) = 0.0037 bits

H(event) - H(event|segment) is the information the segment label carries about the event class; it is reported here as a descriptive quantity, not a hypothesis test.

## 7. Bias-correction comparison

| Endpoint | N | H plug-in | H Miller-Madow | Delta (bits) | Delta / H |
|---|---|---|---|---|---|
| event_class_marginal | 515 | 2.4766 | 2.4836 | +0.0070 | +0.0028 |
| frame_event_count | 300 | 1.8960 | 1.9033 | +0.0072 | +0.0038 |
| decoder_state | 330 | 1.4568 | 1.4634 | +0.0066 | +0.0045 |
| decoder_max_score_bin | 330 | 1.0907 | 1.0950 | +0.0044 | +0.0040 |

Miller-Madow is a first-order correction. It reduces the systematic
underestimate of entropy at small samples; it does not create information
about unobserved levels and does not fix an inadequate sample size.

## 8. Uncertainty

Confidence intervals are percentile intervals from 2000 cluster bootstrap resamples (seed 20261110).
The resampling unit is the run for decoder windows, the frame for events,
a 10-frame block for the frame code, and the replicate for Phase 5E.

Entropy has no exchangeability null, so no permutation test is performed in 6B. Uncertainty is reported with a cluster bootstrap.

## 9. Sensitivity to the declared discretisation

Frame event-count cap:

| Cap | Declared k | H plug-in |
|---|---|---|
| 1 | 2 | 0.7780 |
| 2 | 3 | 1.5442 |
| 3 | 4 | 1.8960 |
| 5 | 6 | 1.8960 |

Decoder score bins:

| Bins | H plug-in | Bin counts |
|---|---|---|
| 2 | 0.9024 | [225, 105] |
| 3 | 1.0907 | [225, 15, 90] |
| 4 | 1.3316 | [210, 15, 15, 90] |
| 5 | 1.3316 | [210, 15, 15, 0, 90] |

Per-segment event-class entropy:

| Segment | N | H plug-in | H MM | Frame clusters |
|---|---|---|---|---|
| replay_0101 | 215 | 2.4786 | 2.4954 | 83 |
| segment_0_99 | 148 | 2.4628 | 2.4871 | 71 |
| segment_200_299 | 152 | 2.4746 | 2.4983 | 77 |

The cap and bin sweeps are reported for transparency. The declared values
(cap 3, 3 bins) were fixed in `configs/information_theory.yaml` before any
estimate was produced and are the ones carried into Phase 6C.

## 10. Endpoints the archived data cannot support

| ID | Endpoint | Recorded reason |
|---|---|---|
| U01 | spike_train_entropy | The only archived recording with individual spike times is a single replay run (74 spikes). Entropy of a spike train needs repeated trials or a declared time-discretisation with enough samples per bin; neither exists here. |
| U02 | population_response_entropy | The 138-neuron sensory population has a nominal support of 2^138 and no archived repeat structure. Plug-in entropy over that support is not estimable at any available sample size. |
| U03 | membrane_potential_entropy | Membrane potentials were never recorded; only spike counts and times. |
| U04 | cue_to_population_code_mi | Aggregate spike counts per episode are constant within conditions A-F, so no neural response variable exists to relate to the cue. |

## 11. Validation

`tests/test_information.py` contains 49 synthetic unit tests covering
constant and maximum entropy, hand-computed joint and conditional values,
MI symmetry and non-negativity, deterministic discretisation, missing and
empty observations, Miller-Madow and bias-floor arithmetic, permutation
reproducibility, channel-sensitive nulls and bootstrap interval behaviour.
Synthetic observations exist only inside those tests.

`tests/test_information_analysis.py` adds 16 focused tests: reader shape
and hash checks, contingency sums, per-seed helper purity, report/JSON
agreement and recorded unavailable endpoints. The full suite passes with
748 tests and no failures.

## 12. Limitations

- Event-class entropy describes the detector's abstract event vocabulary,
  not biological coding. The classes are produced by the Phase 3C rule set.
- The frame event-count code treats an absent event record as no event. It
  is a derived code and inherits any extractor omission.
- Decoder windows overlap within a run; the run is the independent unit and
  the number of independent runs is 66.
- Phase 5E has three replicate clusters per condition, so its intervals are
  wide and should not be read as precise.
- Only 515 events and 330 decoder windows exist. These are small samples for
  6- and 4-level variables respectively.

## 13. Integrity and reproducibility

- Protected baseline files checked: 37, failures: 0
- Protected paths dirty: 0
- Staged files: 0
- Pre-existing modified tracked files: 13
- Runtime: 3.653 s

Re-run with `python experiments/phase_6b/run_entropy_analysis.py` then
`python experiments/phase_6b/build_report.py`. Bootstrap, permutation and
bootstrap seeds are recorded in the configuration and in every interval.
