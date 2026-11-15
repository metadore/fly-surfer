# P3-T4.1 — Four-neuron calibration-point validation (pre-registration)

Status: **pre-registered before execution**
Written: 2026-11-14
Phase: P3-T4.1
Protocol config: `configs/p3_t4_1_four_neuron_validation.yaml`
Config SHA-256: `59f92c89813a11ac1e8812fdb5a23da789fc1cb124b210eadbfa7aba8bc4fd25`
Preflight artifact: `experiments/phase_3c/results/p3_t4_1_preflight.json`
Preflight SHA-256: `5ff98102450496e4e5fa137bfdd3744d235ae40ade03f6afd0609e0eb6c556d9`
Runner at registration:
`experiments/phase_3c/p3_t4_1_four_neuron_validation.py`
Runner SHA-256: `f3e5dc1ec2afdd957869079c7654a832ede8e088da472a16d9e7d1f218b8a163`

This file fixes the comparison before any simulation is run. It is an
experiment document, not a result. Results, including negative results, are
reported in
`experiments/phase_3c/results/p3_t4_1_four_neuron_validation_report.md`.

## 1. Question

Phase 3A.5 selected a four-neuron obstacle-distance population because its
static 300 ms spike counts were strictly ordered across distances 0.15, 0.55
and 0.90, while the twelve-neuron population was not. That selection was made
on a static 300 ms timeline with all features present.

P3-T4.1 asks: **under the Phase 3C temporal stimulus framework, does the
four-neuron configuration produce a measurably different or better
obstacle-distance response than the frozen twelve-neuron configuration?**

This is a validation experiment. It is not a search for a configuration that
passes, and no neuron, synaptic, connectome or global simulation parameter is
changed to obtain a favourable result.

## 2. Preflight findings (evidence, not inference)

### 2.1 What the Phase 3A.5 selection actually chose

`experiments/phase_3_5/results/selection.json` contains:

- `amplitude_pa: 200.0` with source `fallback_no_ordered_amplitude`;
- `sigma_fraction: 0.2` with source `fallback_no_ordered_tuning`;
- `population_size: 4` with source `ordered`;
- `mapping_seed: 20261104`, `baseline: 0.0`.

The selection rule in `experiments/phase_3_5/calibration.py` ranks factor
groups that are eligible (at least one spike at every level, not fully
recruited) and strictly ordered across the three distances. **It selects a
population size, not a set of neuron IDs.** `selection.json` contains no
neuron identifiers.

The "four selected neurons" are therefore the four neurons produced by the
frozen mapping at seed `20261104` when `n_neurons = 4`:
`[64890, 87389, 107895, 108078]` in sorted order, or
`[87389, 108078, 64890, 107895]` in mapping (permutation) order. They are the
first four indices of the same seeded permutation that produces the
twelve-neuron mapping, so the four-neuron set is a prefix of, and a subset
of, the twelve-neuron set.

### 2.2 Exact populations

Mapping order, with root IDs, for the three pre-registered seeds
(`experiments/phase_3c/results/p3_t4_1_preflight.json`):

| Seed | P4 indices | P4 root IDs |
|---|---|---|
| 20261104 | 87389, 108078, 64890, 107895 | 720575940628230223, 720575940632256015, 720575940624132095, 720575940632208971 |
| 20261105 | 14480, 135717, 3324, 68984 | 720575940612538517, 720575940646382190, 720575940606492350, 720575940624887881 |
| 20261106 | 128884, 100241, 49729, 1400 | 720575940639975733, 720575940630657792, 720575940621487195, 720575940605179360 |

| Seed | P12 indices (mapping order) |
|---|---|
| 20261104 | 87389, 108078, 64890, 107895, 104235, 52604, 87805, 91895, 7411, 88721, 91920, 125025 |
| 20261105 | 14480, 135717, 3324, 68984, 106520, 63388, 12735, 36976, 14892, 48939, 56757, 79823 |
| 20261106 | 128884, 100241, 49729, 1400, 116364, 68586, 55737, 38473, 62434, 102596, 70748, 93847 |

For seed 20261104 the sorted twelve-neuron set is
`[7411, 52604, 64890, 87389, 87805, 88721, 91895, 91920, 104235, 107895, 108078, 125025]`.

### 2.3 Index-order provenance (resolved)

P3-T4 recorded sorted index lists
(`experiments/phase_3c/results/p3_t4_calibration_discrepancy.json`,
`mapping.comparison.indices_4` and `indices_12`). The P3-T4 runner sorts
`population.indices` (`mapping_indices`, line 126). Regenerating the mappings
at seed `20261104` from the frozen config produces exactly the recorded sorted
lists (verified: `indices_4` and `indices_12` both match). The apparent earlier
mismatch was an ordering difference only, not a different population.

### 2.4 What the twelve-neuron configuration has been tested on

Phase 3A.5 measured the twelve-neuron population only at the single mapping
seed `20261104` (population stage: counts `[24, 23, 23]`, not ordered; d'
proxy 0.206). The three-seed stage was run only at the selected size 4
(counts `[2, 6, 7]` at every seed). No prior artifact evaluates the
twelve-neuron configuration across the three mapping seeds.

### 2.5 Encoder bank is part of the configuration

The frozen Phase 3A gaussian encoder places `n_neurons` preferred stimuli on
`np.linspace(minimum, maximum, n_neurons)` with
`sigma = sigma_fraction * (maximum - minimum) = 0.20`
(`sensory/population_encoder.py`, lines 138–140). Consequently:

- the four-unit bank has preferred distances `[0, 0.333, 0.667, 1]`;
- the twelve-unit bank has preferred distances `[0, 0.091, ..., 1]`;
- the four units are **not** a four-unit subset of the twelve-unit bank.

`SensorySetup` requires encoder output size to equal mapping size, so no
"four neurons with a twelve-unit encoder" configuration exists in the frozen
code. The primary contrast is therefore configuration-level: the selected
four-neuron point versus the frozen twelve-neuron point.

Total injected distance current at the three constant distances, at 200 pA per
neuron (preflight, seed-independent):

| Distance | P4 total pA | P12 total pA | Ratio |
|---|---|---|---|
| 0.15 | 289.493 | 924.120 | 3.19 |
| 0.55 | 300.400 | 1094.569 | 3.64 |
| 0.90 | 281.387 | 847.499 | 3.01 |

Total current is non-monotone in distance in both banks. The current is not
normalised; per-neuron amplitude is held at the frozen 200 pA.

### 2.6 Relation to the Phase 3C stimuli

P3-T7 activated all features, so its frames also carried neutral player
defaults (constant `player_lane` and `player_speed` current). P3-T4.1 sets
`active_features = ["obstacle_distance"]`; every other population receives
zero current. This isolates the obstacle-distance population and prevents the
five feature mappings that shift when the population size changes
(`obstacle_distance`, `train_present`, `train_distance`, `coin_present`,
`coin_distance`) from contributing current.

P3-T7's 3C.2 approach/retreat comparison on the twelve-neuron population
reported signed d' = 0.0 in all three seeds and equal total spikes
(460/460). P3-T4.1 tests whether the four-neuron point behaves differently
under the same operationalisation, with a distance-only stimulus.

## 3. Populations under test

| Name | Mapping | Encoder bank | Driven cells | Role |
|---|---|---|---|---|
| P4 | 4 neurons | 4 units | all 4 | selected Phase 3A.5 point |
| P12 | 12 neurons | 12 units | all 12 | frozen Phase 3C point |
| P12S | 12 neurons | 12 units | the 4 P4 cells only | decomposition control |

P12S keeps the twelve-neuron encoder and mapping but zeroes current in the
eight cells that are not in the four-neuron mapping. It is reported
descriptively to separate "more driven cells" from "four-cell retuning". It
does not replace the primary contrast.

## 4. Stimuli and timing

All values are copied from `configs/temporal_sensory.yaml` and asserted at
run time.

| Condition | Definition |
|---|---|
| `constant_0.15` | obstacle at distance 0.15 for the whole run |
| `constant_0.55` | obstacle at distance 0.55 |
| `constant_0.90` | obstacle at distance 0.90 |
| `approach` | distance 0.90 → 0.15 linearly over 600 ms, 50 ms frames |
| `retreat` | distance 0.15 → 0.90 linearly over 600 ms, 50 ms frames |
| `frame_rate_100` | `approach` sampled at 100 ms frames |
| `frame_rate_200` | `approach` sampled at 200 ms frames |
| `control_no_input` | no obstacle present, zero distance current |

Protocol: duration 600.5 ms (one extra 0.5 ms step so the last frame applies),
dt 0.5 ms, bin 50 ms, obstacle lane `center`, obstacle type `low`,
200 pA per neuron, baseline 0 pA, zero background current, zero noise,
recorder capacity 6,000,000 spikes.

## 5. Seeds, repeats and determinism

Mapping seeds: `20261104` (the Phase 3A.5 seed), `20261105`, `20261106`.

The simulator is deterministic with zero background and zero noise, so there
are no stochastic repeats. Each population/seed/condition is run once.
Determinism is checked by rerunning `approach` at seed `20261104` for every
population; the spike digest (SHA-256 over spike times and neuron indices)
must be identical.

The three mapping seeds are three anatomical draws of the visual pool. They
are not biological replicates and are not independent samples from a
population; no p-value or confidence interval is computed.

## 6. Metrics

### 6.1 Primary

1. `total_spikes`: all network spikes in a condition.
2. `stimulated_spikes`: spikes in the driven obstacle-distance cells.
3. `stimulated_active_neurons`: number of driven cells with at least one
   spike.
4. `outside_spikes`: all network spikes outside the driven cells (recurrent
   activity proxy).
5. `distance_ordering_stimulated`: strict increase of stimulated spike counts
   across 0.15, 0.55, 0.90 (the Phase 3A.5 ordering criterion, applied at the
   3C horizon).
6. `approach_retreat_dprime_stimulated`: d' on 50 ms binned stimulated spike
   profiles for `approach` versus `retreat`, with the Phase 3C threshold 1.0.

### 6.2 Secondary

- `outside_active_neurons`, `approach_retreat_dprime_network`;
- `approach_retreat_cosine_stimulated` and network profile cosine distance;
- frame-rate current RMS difference and spike-profile cosine distance to the
  50 ms reference (stimulated and network);
- first and median first spike latency of driven cells;
- voltage summaries (mean, SD, min, p10, median, p90, max in mV) for driven
  and outside neurons after the steps at 0, 100, 300 and 600 ms;
- per-neuron spike counts for every driven cell, including the four P4 cells
  when they are embedded in P12.

### 6.3 Interpretive rules fixed in advance

A larger spike count is **not** automatically better. "Better sensory
response" in this experiment means only one of:

- strict distance ordering present in P4 and absent in P12; or
- approach/retreat separation (|d'| > 1.0) present in P4 and absent in P12.

"Measurably different" means a nonzero paired difference under identical
deterministic input. Because there is no noise, any nonzero difference is a
deterministic difference; its size is reported as an absolute difference and a
ratio, not as a significance claim.

## 7. Statistical method

No hypothesis test is used. Results are exact deterministic values.
Across-seed consistency is defined as the same sign in all three seeds. A
claim of replication uses the pre-existing "at least 2 of 3 seeds" rule from
Phase 3A.5 and Phase 3C. Seed-to-seed differences are reported, not tested.

## 8. Exclusion criteria

No run is excluded because of its result. A run is invalid only if:

- the simulation raises an exception, including spike-capacity overflow;
- the recorded spike arrays are non-finite;
- the configuration-equivalence check fails (anything other than
  `features.obstacle_distance.n_neurons` and
  `mapping.populations.obstacle_distance.n_neurons` differs between P4 and
  P12);
- the determinism rerun digest differs.

An invalid run is retried once with identical settings. If it fails again, the
experiment is reported BLOCKED with the failing condition named.

## 9. Decision rules and verdict mapping

### 9.1 Hypotheses

- **H1 — ordering replicates.** P4 stimulated counts strictly increase across
  0.15/0.55/0.90 in at least 2 of 3 seeds, and P12 does not.
- **H2 — temporal separation.** |d'| for approach versus retreat exceeds 1.0 in
  at least 2 of 3 seeds in P4, and not in P12.
- **H3 — measurable difference.** P12 minus P4 total spikes has the same sign
  in all three seeds for at least one condition (expected mechanically because
  P12 drives more cells; reported as magnitude and direction, not as merit).
- **H4 — frame-rate sensitivity.** Reported per population; a stimulated
  profile cosine distance above 0.01 is the Phase 3C threshold for "measurable
  difference".

If a hypothesis is not supported, the negative result is reported without
reframing. H1 and H2 may each be true, false, or mixed by seed; all three
seeds are tabulated.

### 9.2 Experiment verdict

- **PASS** — config equivalence, complete runs, determinism and protected
  hashes all hold, and at least one primary metric is defined. Hypothesis
  direction does not change this verdict.
- **INCONCLUSIVE** — execution checks hold but no primary condition produces
  any spike, or approach/retreat d' is undefined in every population and seed.
- **BLOCKED** — an execution check fails after the single retry described in
  section 8, or a protected file changed.

## 10. Limitations fixed in advance

- The four-neuron point changes both the driven cells and the encoder bank;
  the primary contrast cannot attribute a difference to one of those alone.
- P12 injects about three times the total current of P4 at the same per-neuron
  amplitude.
- P12S isolates the number of driven cells at fixed per-neuron currents but
  still uses the twelve-unit tuning bank for the four shared cells.
- Distances are dimensionless Phase 3A proxies, not metres.
- Stimuli are synthetic `GameState` lists; no perception stage is involved.
- The 600.5 ms horizon differs from the 300 ms horizon used to select the
  four-neuron point in Phase 3A.5. H1 is therefore a new test at the 3C
  horizon, not a confirmation of the original selection measurement.
- The d' threshold 1.0 and cosine threshold 0.01 are copied from the Phase 3C
  pre-registration; the Phase 3C design itself fixed no numeric cut-off.
- Bins within one run are not independent samples.
- Spikes and voltages are model output; no biological activity or biological
  superiority is claimed.
- No motor or action selection is involved.

## 11. Deviations

Any deviation from this document is recorded in the result JSON under
`deviations` and in the final report. Protocol values are additionally
asserted against frozen constants in the runner, so a silent config edit
cannot change the experiment. If the runner is edited after registration, the
final runner hash and the reason are recorded; edits that change a stimulus,
seed, metric definition or decision rule are reported as deviations.
