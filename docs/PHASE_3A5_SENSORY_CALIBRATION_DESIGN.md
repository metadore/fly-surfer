# Phase 3A.5 — sensory calibration (design and implementation status)

Status: **implemented and validated on 2026-11-04.** The calibration pipeline,
configuration, tests, full 84-condition sweep and report exist in the
repository. The measured outcome is recorded at the end of this document. The
design below is retained as the pre-registered rationale and selection rule; it
does not change the Phase 3A configuration, simulator code or connectome.

## Why this milestone exists

Phase 3A established that the sensory pipeline runs end to end, but it also
exposed a calibration problem. The default drive is 200 pA and the LIF rheobase
for the configured parameters is 150 pA. A single stimulated neuron therefore
sits well above threshold, and the number of recruited neurons is dominated by
the threshold rather than by the shape of the tuning curve. The Phase 3A report
recorded this explicitly: obstacle-distance sweeps produced 167, 167 and 168
spikes, coin-distance sweeps 113, 113 and 114, and player-speed sweeps 59, 60
and 59.

Those near-identical counts are a property of this operating point. They are
not evidence that the encoded features are indistinguishable to the network,
and they are not evidence of biological coding. Before a perception layer is
connected, the project needs to know:

1. Which drive amplitudes produce graded recruitment and which saturate.
2. How tuning width and population size affect discriminability.
3. What response latency and active-neuron fraction to expect.
4. Whether combined features interact non-additively.
5. How sensitive results are to the mapping seed.
6. Which calibrated operating point Phase 3B should use.

## Scope and non-goals

**In scope**

- Static, controlled calibration of the existing Phase 3A encoders, mapping and
  scheduler on the validated connectome artifact.
- Input-current, tuning and population-size sweeps.
- Per-neuron recruitment, latency, dynamic range and saturation measurements.
- Mapping-seed sensitivity and subprocess reproducibility.
- Additivity checks for simultaneous features.
- A recommendation for a Phase 3B operating point.

**Out of scope**

- New sensory modalities, screenshot processing or perception.
- Motor decoding, reward, plasticity or reinforcement learning.
- Changes to the connectome, neuron indexing or synapse model.
- Replacing the Phase 3A results; 3A remains the frozen baseline.
- Selecting features by mutual information.
- FlyVis or any external visual model.

## Questions and hypotheses

| ID | Question | Hypothesis to test (not assumed true) |
|---|---|---|
| Q1 | At what current does recruitment become graded? | Lower amplitudes near rheobase will recruit fewer tuned units and expose tuning; high amplitudes will saturate. |
| Q2 | Does narrower tuning improve separation? | Narrower `sigma_fraction` will reduce overlap between distance levels but may reduce the number of active units. |
| Q3 | Does population size change discriminability? | Larger populations may improve population-vector separation until saturation or pool limits dominate. |
| Q4 | How does latency depend on drive? | Higher currents will produce earlier first spikes; latency will vary across neurons. |
| Q5 | Are simultaneous features additive? | Network recurrence and shared downstream targets will make combined responses at least partly non-additive. |
| Q6 | How much do mapping seeds matter? | Different seeded neuron selections will produce different spike counts and population vectors. |

These are hypotheses. A negative result is a valid outcome and must be reported.

## Fixed conditions

The calibration uses the existing pipeline unchanged:

- Validated FAFB artifact: 139,255 neurons, 3,732,460 directed edges.
- LIF parameters from `configs/neuron_config.yaml`.
- Synapse parameters from `configs/simulation_config.yaml`.
- 0.5 ms timestep, zero background current, zero noise.
- Seed handling and subprocess hashing as in Phase 3A.
- Full graph, sparse CSR propagation; no subgraph sampling and no raw CSV.

Two reference calculations frame the sweep. With `C = 200 pF`,
`gL = 10 nS`, rest `-65 mV` and threshold `-50 mV`:

```
steady state = -65 + I / 10 nS  [mV, I in pA]
time to threshold = -20 ms * ln(1 - 15 / (I / 10))
```

At 150 pA the steady state is exactly `-50 mV`, so threshold is only approached
asymptotically; at 175 pA the ideal time is about 33 ms, at 200 pA about 28 ms,
and at 300 pA about 14 ms. Recurrent input and reset change the realised values,
so these are design guides, not predictions of measured latency.

## Experimental design

### Factor table

| Factor | Levels | Notes |
|---|---|---|
| Current amplitude | 100, 125, 150, 175, 200, 225, 250, 300 pA | 100–150 pA are sub/supra-rheobase controls |
| Gaussian `sigma_fraction` | 0.05, 0.10, 0.20, 0.30, 0.50 | Applied to distance features |
| Population size | 4, 8, 12, 16, 24 | Mapping must still allocate disjointly |
| Baseline activation | 0.0, 0.1, 0.2 | Must remain ≤ amplitude |
| Transition | 0, 10, 25, 50, 100 ms | Static calibration; full temporal study belongs to 3C |
| Mapping seed | 3 seeds | Simulation noise remains zero |
| Feature levels | 3 per continuous feature | Low / middle / high |

A full factorial would be unnecessarily large. The proposed sequence is
one-factor-at-a-time with a small interaction check:

1. **3A.5.1 Amplitude × distance.** `obstacle_distance` at 0.15, 0.55 and 0.90,
   eight amplitudes, standard mapping and tuning. 24 conditions.
2. **3A.5.2 Recruitment curve.** For each amplitude, report active fraction and
   spikes per stimulated neuron. No extra runs; reuse 3A.5.1.
3. **3A.5.3 Tuning width.** Best two amplitudes from 3A.5.1, five
   `sigma_fraction` values, three distances. 30 conditions.
4. **3A.5.4 Population size.** Best amplitude and width, five population sizes,
   three distances. 15 conditions. Mapping reallocation is part of the factor.
5. **3A.5.5 Seed sensitivity.** Best configuration, three mapping seeds, three
   distances. 9 conditions.
6. **3A.5.6 Additivity.** Best configuration, obstacle and coin separately and
   together, plus no-input baseline. 4 conditions.
7. **3A.5.7 Transition.** Best configuration, five transition lengths on a
   two-state distance sequence. 5 conditions.
8. **Controls.** No-input baseline, a sub-rheobase (100 pA) run and a
   supra-saturation (300 pA) run for every primary feature.

Estimated total: about 85 full-graph conditions. At the Phase 3A rate of
roughly 2–2.5 s per 300 ms condition, this is a few minutes of simulation per
sweep once the graph is loaded. Sequence conditions are longer. The plan should
be split into subcommands so a failure does not invalidate the whole sweep.

### Protocols

Each condition reuses one `GameState` per segment, the existing encoders and
the existing `SensoryInputScheduler`. The only changes are configuration
values and, for population-size runs, the mapping size. Conditions must not
share mutable scheduler state; each run constructs a fresh scheduler and
simulator.

For additivity, the three runs must use identical mapping, amplitudes, timing,
seed and duration. The combined state contains both objects; the single-object
runs contain one object and an absent second object.

## Metrics

### Input-side

- Peak per-neuron current (pA) and total scheduled current (pA).
- Number of active encoding units and activation sparsity/entropy.
- Overlap between tuning curves at the tested feature levels.
- Saturation fraction: active stimulated neurons / stimulated neurons.
- Mapping sizes, selected root IDs and mapping seed.

### Neural

- Recorded spikes and active neurons.
- Mean and maximum firing rate.
- Recruitment fraction among directly stimulated neurons.
- Spikes per stimulated neuron.
- First-spike latency after onset: median, interquartile range and p95.
- Response duration and time to return to baseline after offset.
- Dynamic range: maximum minus minimum population response across levels.
- Monotonicity: Spearman rank correlation between feature level and response.
- Discriminability `d'` between low and high levels using the spread across
  mapping seeds/repeats, plus cosine distance between mean population vectors.
- Additivity index for combined versus single-feature responses.
- Per-feature spike attribution and downstream (non-stimulated) spike share.

### Operational

- Wall runtime, steps/s, retained arrays, scheduler memory and RSS change.
- Deterministic hashes of the scheduler signature and spike arrays.
- Finite-state and membrane-bound diagnostics.

All metrics are descriptive. A larger `d'` in this model is not a biological
result.

## Analysis and decision rule

The calibration produces a table of operating points, not a single "best"
number. The recommendation for Phase 3B should satisfy, in order:

1. No numerical, capacity or validation failures.
2. Reproducible input and spike hashes across a parent and two subprocesses.
3. At least one operating point shows an ordered population response across
   the three tested feature levels in at least two of three mapping seeds.
4. The chosen point avoids complete saturation (not every stimulated neuron
   active at every level) and avoids the sub-rheobase regime.
5. Runtime overhead remains within a documented budget relative to the
   no-schedule baseline.
6. Combined-feature non-additivity is measured and reported, not hidden.

If no operating point meets criterion 3, the correct outcome is a documented
negative result: keep 200 pA as the Phase 3A reference, label the readout
threshold-dominated, and do not claim graded coding in Phase 3B.

## Outputs as implemented

```
configs/sensory_calibration.yaml
experiments/phase_3_5/
  __init__.py
  calibration.py
  run_all.py
  results/conditions/<stage>/*.json
  results/baseline.json
  results/selection.json
  results/stage_amplitude.json
  results/stage_tuning.json
  results/stage_population.json
  results/stage_seeds.json
  results/stage_additivity.json
  results/stage_transition.json
  results/stage_baseline.json
  results/stage_controls.json
  results/additivity.json
  results/transition.json
  results/baseline_activation.json
  results/controls.json
  results/reproducibility.json
  results/summary.json
  results/calibration_summary.json
  plots/recruitment_vs_current.png
  plots/discriminability.png
  plots/tuning_width.png
  plots/population_size.png
  plots/seed_variability.png
  plots/additivity.png
  plots/transition_response.png
  plots/baseline_activation.png
  PHASE_3_5_REPORT.md
tests/test_calibration.py
```

The report separates configured input, simulated neural response and
interpretation. It retains the Phase 3A baseline for comparison.

## Acceptance criteria

1. Every factor level is expressed in configuration, not hard-coded.
2. The full graph, sparse propagation and frozen connectome artifact are used.
3. Sub-rheobase and saturation controls behave as expected or the deviation is
   explained.
4. Mapping remains disjoint and reproducible for every population size tested.
5. The chosen operating point is justified by measured recruitment and
   discrimination, not by visual inspection of one raster.
6. Repeat runs in separate processes produce equal input and spike hashes.
7. Phase 2, Phase 2.5, Phase 3A and the full test suite still pass.
8. A negative result is reported without reframing it as a success.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Large sweep becomes expensive | Split by subcommand; cache graph load; stop a sweep early on validation failure |
| Mapping pool too small for 24 neurons per feature | Validate pool capacity before running; reduce maximum size and record the limit |
| Changing mapping size breaks comparability | Keep the Phase 3A mapping as a fixed control and report normalized responses |
| Runtime noise obscures small overheads | Interleave baseline runs; report medians and ranges, not one wall time |
| Threshold behaviour is mistaken for coding | Pre-register the decision rule; report saturation and monotonicity |
| Seed sensitivity is ignored | Use at least three mapping seeds for the chosen point |
| Calibration overfits one feature | Repeat the chosen point for a lane and a boolean feature |

## Deliverables

- `docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md` (this document).
- `configs/sensory_calibration.yaml`, `experiments/phase_3_5/` and
  `tests/test_calibration.py` (done).
- A generated report with all condition-level JSON and plots (done).
- A single recommended Phase 3B operating point, with the factors that did not
  produce an ordered response recorded as negative results (done).
- No changes to the root README, datasets, connectome artifact or external
  references.

## Measured outcome (2026-11-04)

The sweep ran 84 full-graph conditions at 300 ms and 0.5 ms timesteps on the
validated artifact (139,255 neurons, 3,732,460 edges, 50,666,648 summed
synapses). All conditions completed without setup or runtime failures, and the
full test suite passed (114 tests).

**Gate result: PASS, within the model's assumptions.** The selected operating
point is 200 pA, `sigma_fraction` 0.20, four mapped obstacle-distance neurons,
mapping seed 20261104 and zero baseline activation. At this point the three
distance levels produced 2, 6 and 7 spikes (0.15, 0.55 and 0.90), and all three
mapping seeds produced exactly the same counts. The descriptive Poisson d'
proxy is 2.357. Input and spike hashes matched between the parent and two
subprocesses.

The result is narrower than "the network encodes distance":

- **Amplitude was not ordered.** No tested current from 175 to 300 pA produced
  a strictly monotone three-level response (175: 12/14/14; 200: 24/23/23;
  225: 35/32/33; 250: 43/46/41; 300: 62/63/55). Currents of 100–150 pA
  produced no spikes in the stimulated population. The reference 200 pA was
  therefore retained; this is a recorded fallback, not a selected optimum.
- **Tuning width was not ordered.** No tested `sigma_fraction` from 0.05 to
  0.50 produced a monotone response at 200 pA. The reference 0.20 was
  retained as a fallback.
- **Population size was ordered only at four neurons.** Responses were
  2/6/7 at four neurons, 15/14/15 at eight, 24/23/23 at twelve, 32/32/32 at
  sixteen and 48/50/47 at twenty-four. The pre-registered rule selects the
  largest d' among ordered groups, which is the four-neuron setting; the
  ordering is therefore a small-population, threshold-sensitive effect.
- **The effect survives remapping.** At four neurons, all three mapping seeds
  gave identical counts, so the selected point is not an artifact of one
  random allocation.
- **Additivity is zero at the tested levels.** Obstacle alone produced 9 spikes,
  coin alone 23 and both 32; the additivity index is 0.0 for this pair. Network
  recurrence still affects the interpretation.
- **Sub-rheobase controls behaved as expected.** Coin and player-speed
  populations produced no spikes at 100 pA and 63–64 spikes at 300 pA.
- **Transition crossfades did not change the rank order.** The far-to-near
  crossfade produced 4, 4, 4, 4 and 3 spikes at 0, 10, 25, 50 and 100 ms.
  First-spike latency was 38 ms in every case.
- **Runtime is noisy.** In the final run the single no-schedule baseline was
  1.175 s and the calibration mean was 1.421 s (0.246 s added, 20.95%).
  Earlier runs measured a negative added time, so this is a noisy wall-clock
  estimate, not a stable overhead claim.

The measured outcome is therefore a positive discrimination result at one
small, threshold-sensitive operating point, together with explicit negative
results for current amplitude and tuning width. It does not establish a
graded distance code, a biological sensory pathway or a perceptual capability.
Phase 3B may use the selected point, but must not describe it as a validated
neural code.

## Next milestone interaction

Phase 3B can be developed against the Phase 3A interfaces before 3A.5 finishes,
because perception only needs to emit validated `GameState` objects. The Phase
3B integration gate should use the calibrated operating point from 3A.5, not
silently inherit 200 pA.
