# FLY-SURFER — Phase 4H Experimental Protocol

Status: frozen before confirmatory execution.
Phase: 4H (Robustness, Statistical Validation and Sensory Round-Trip).
Baseline commit state: `main`, 64 working-tree entries, 0 staged (recorded in
`experiments/phase_4h/baseline_integrity.json`).

This document defines the hypotheses, units of replication, sample sizes,
seeds, endpoints, statistics, exclusions and stopping rules for Phase 4H. It
was written before any Phase 4H simulation was executed. Sub-phase 4H.3 has an
additional, separately hashed pre-registration.

Nothing here changes the FAFB connectome, the BANC graph artifacts, the raw
datasets, the Phase 4D graph construction, the Phase 4E analysis, the Phase 4F
motor populations and decoder, the Phase 4G simulator behaviour, the Phase 3
sensory pipeline, or the root `README.md`.

---

## 1. Scientific position entering Phase 4H

The Phase 4G.5 experiment drove 64 connectivity-ranked verified-excitatory
ventral-nerve-cord intrinsic neurons at 300 pA for 200 ms. It recorded 1,296
spikes, 492 of them in motor neurons, and the unchanged Phase 4F decoder
returned JUMP in four of five 50 ms windows. Six conditions were run once each
and all showed reproducible spike and decision hashes.

That result is a single experiment. It is compatible with at least four
explanations that Phase 4G could not separate:

1. the specific 64 neurons have downstream connectivity that favours the JUMP
   pool;
2. any 64 strongly motor-projecting neurons would do so;
3. any 64 verified-excitatory neurons would do so, because the stimulation
   itself is large;
4. the result is a consequence of the weight transform, the sign policy, the
   drive amplitude, or the 20-neuron size of the JUMP pool.

Phase 4H exists to separate these explanations with controls, replicates and
pre-registered sensitivity analyses. It is a validation phase, not an
optimization phase.

### Standing distinctions

Structural connectivity is not physiological connectivity. Synapse count is not
conductance. Transmitter prediction is not verified annotation. Transmitter
identity is not a universal postsynaptic effect. A simulated motor response is
not a biological motor command. A decoder classification is not proof of
perception. Deterministic execution is not statistical robustness. A single
successful experiment is not generalisation. Being distinguishable from one
control is not being distinguishable from all alternatives.

---

## 2. Fixed experimental conditions

Every confirmatory run in 4H.1–4H.3 uses, unless a factor is the variable under
test:

| Item | Value |
| --- | --- |
| graph | BANC v888 threshold 5 (`banc_graph_t5.npz`) |
| nodes / edges / synapses | 172,433 / 1,535,710 / 18,552,546 |
| sign policy | verified-only; ACh/glutamate excitatory, GABA/glycine inhibitory; modulators and conflicts unknown; predicted fallback off; unknown edges excluded |
| weight transform | power, exponent 0.75, scale 5.0 pA, cap 300 pA (Phase 4G primary) |
| LIF | C 200 pF, g 10 nS, rest −65 mV, threshold −50 mV, reset −68 mV, refractory 2 ms |
| synapses | tau_exc 5 ms, tau_inh 8 ms, delay 1.0 ms (2 steps) |
| dt | 0.5 ms |
| duration | 300.0 ms |
| stimulation window | 50.0 ≤ t < 250.0 ms |
| stimulation amplitude | 300.0 pA (nominal) |
| background / noise | 0 pA / 0 pA, except the declared noise condition |
| decoder | Phase 4F config unchanged: 50 ms window, 50 ms step, activation 0.20, release 0.10, ≥5 spikes, ≥3 active neurons, priority LEFT/RIGHT/JUMP |
| decode window | 50.0 ≤ t ≤ 300.0 ms (five half-open windows) |
| spike recording cap | 5,000,000 events |
| populations | LEFT 185, RIGHT 186, JUMP 20, motor 805, unassigned 414 |

The reference condition is Phase 4G condition C: the 64 highest-ranked
verified-excitatory, non-motor, `super_class == ventral_nerve_cord_intrinsic`
neurons by total signed synapse count onto the 805 motor neurons. The Phase 4H
harness must reproduce the Phase 4G.5 condition C spike hash exactly; if it
does not, 4H.1 stops and reports the discrepancy instead of proceeding.

Because the primary conditions use zero noise, the simulator RNG has no
influence on the dynamics. **The unit of replication in 4H.1–4H.3 is therefore
the candidate-set draw (the selection seed), not a stochastic simulation
seed.** This is stated in every result file. Independent seeds that select the
same neuron set produce bit-identical spikes; that is a property of the
deterministic simulator, not evidence of robustness.

---

## 3. Sub-phase 4H.1 — multiple random control draws

### 3.1 Question

Is Phase 4G condition C's motor activity and JUMP output distinguishable from
repeated draws of matched random controls?

### 3.2 Control families

All families deliver 64 neurons, 300 pA, 50–250 ms, under the fixed conditions
of section 2. Membership is disjoint from the motor population in every family.

| Family | Pool | Draw rule |
| --- | --- | --- |
| A `vnc_intrinsic_random` | verified-excitatory, non-motor, VNC-intrinsic neurons (n = 5,622, minus the 64 C neurons) | uniform 64 without replacement |
| B `motor_projecting_random` | verified-excitatory, non-motor neurons with ≥1 signed edge to a motor neuron (n = 4,810) | uniform 64 without replacement |
| C `all_verified_excitatory_random` | all verified-excitatory, non-motor neurons (n = 53,957) | uniform 64 without replacement |
| D `rank_stratum_shuffled` | VNC-intrinsic eligible neurons ranked 65–256 by motor synapses (n = 192) | uniform 64 without replacement |
| E `connectivity_annotation_matched` | VNC-intrinsic eligible pool | stratified: within each (motor-synapse quintile × cell_class-present) stratum, draw the number of neurons that C contributes to that stratum |

Family E is a matching attempt, not an exact match. Where a stratum in C has
more neurons than remain in the pool after removing C, the stratum allocation
is capped at what is available, the shortage is recorded, and the draw is
topped up from the remaining eligible pool so that every draw still contains
64 neurons. The realised matching quality is reported as the standardised
difference between each draw and C on motor-synapse count, in-degree, out-degree
and `cell_class` presence. C occupies the extreme tail of the motor-synapse
distribution, so exact connectivity matching is impossible; the realised
standardised differences are reported rather than assumed away.

Family D tests whether membership in the high-connectivity stratum is
sufficient; family E tests whether matching on connectivity and annotation
completeness reproduces C's activity.

### 3.3 Sample size

100 independent draws per family, 100 per family is the pre-registered target.
Justification: one draw is one 300 ms simulation at roughly 3 s wall time, so
500 draws cost about 25–30 minutes. With n = 100 the smallest attainable
one-sided empirical p-value is 1/101 = 0.0099, which is below the smallest Holm
threshold for five tests (0.01). A pilot sample below 100 would not be
described as strong evidence.

Seed rule: draw seed = `20261109 + 1000 * family_ordinal + draw_index`, with
`family_ordinal` A=1 … E=5 and `draw_index` 0–99. All 500 seeds are written to
the result JSON.

### 3.4 Endpoints

Primary (confirmatory):

- P1 `motor_spikes`: spikes in the 805 motor neurons over the whole recording.
- P2 `jump_windows`: number of decoder windows whose decoded state is JUMP.

Secondary (descriptive, reported with unadjusted p-values labelled
exploratory):

total spikes, stimulated spikes, non-stimulated spikes, active neurons,
non-stimulated active neurons, motor active neurons, LEFT/RIGHT/JUMP spikes and
active fractions (whole span and per-window peak), NEUTRAL windows, time to
first motor spike, time to first non-NEUTRAL decision, post-stimulation spikes,
and the Phase 4F scores (raw and normalised).

### 3.5 Statistics

For each family and endpoint:

- empirical one-sided p = (1 + #{control ≥ C}) / (1 + n);
- Cliff's delta and its 95% bootstrap interval;
- ratio of means with a percentile bootstrap 95% CI (10,000 resamples, seed
  20261109);
- for binary endpoints, the proportion and a Wilson 95% interval.

Holm–Bonferroni correction is applied across the five families separately for
P1 and P2 at α = 0.05. A result is called a confirmatory difference only if it
survives Holm. All other p-values are labelled exploratory and not used for
inference.

### 3.6 Exclusions and stopping

No draw is excluded. A draw that fails to execute is recorded as a failure with
its exception message and counted; it is not silently dropped. If the C
reference does not reproduce the Phase 4G.5 spike hash, 4H.1 stops.

---

## 4. Sub-phase 4H.2 — population size and selection sensitivity

### 4.1 Question

How do activity and decoder output depend on the number of driven neurons and
on the rule used to select them?

### 4.2 Factors

Sizes: 8, 16, 32, 48, 64, 96, 128. All sizes are feasible because the eligible
VNC-intrinsic pool contains 5,622 neurons; the result file reports the pool
size beside every size.

Selection rules:

| Rule | Definition |
| --- | --- |
| `connectivity_ranked` | top-N by signed motor-synapse count within the VNC-intrinsic eligible pool (the Phase 4G rule) |
| `random_eligible` | uniform draw from the same pool |
| `in_degree_ranked` | top-N by threshold-graph in-degree |
| `out_degree_ranked` | top-N by threshold-graph out-degree |
| `combined_degree_ranked` | top-N by in-degree + out-degree |
| `verified_excitatory_all_classes` | top-N by signed motor-synapse count among all verified-excitatory non-motor neurons (drops the VNC restriction) |
| `annotation_stratified_random` | uniform draw within `cell_class` strata, with allocation equal to the ranked pool's stratum composition |

Ties in a ranked rule are broken by ascending graph node index, matching the
Phase 4G rule.

Random rules are repeated with 10 draws per (rule, size); ranked rules are
deterministic and run once. Every (rule, size) is also accompanied by 10
matched `random_eligible` draws at the same size as the control. Seeds:
`20261109 + 200000 + 1000 * size + 10 * rule_ordinal + draw_index`.

Degree is a structural graph property. No biological interpretation of degree
is made.

### 4.3 Endpoints

The full activity profile, not only the final action: total spikes, motor
spikes, per-action spikes and active fractions, NEUTRAL and action windows,
peak per-window active fraction, time to first motor spike. The result is a
size × rule surface, reported in full.

### 4.4 JUMP pool imbalance

LEFT 185, RIGHT 186, JUMP 20. The decoder scores an active fraction, so one
active JUMP neuron is 0.05 while one active LEFT neuron is 0.0054. Phase 4H.2
reports:

- active counts, active fractions and per-neuron rates for all three pools;
- for each run, the JUMP active fraction placed against the empirical
  distribution of active fractions of 10,000 random size-matched (20-neuron)
  subsets of the 805 motor neurons, using the recorded motor spike counts;
- the same null comparison for equal-size 20-neuron subsets of the leg motor
  neurons, to separate pool size from pool identity.

These are descriptive metrics. The decoder thresholds and populations are not
modified. Any alternative decision rule would be a separate exploratory model
and is not fitted here.

### 4.5 Statistics

One pre-registered confirmatory comparison: at size 64, `connectivity_ranked`
versus `random_eligible` (n = 100 draws, which reuses the 4H.1 family A draws),
one-sided empirical p for motor spikes and JUMP windows, Holm-corrected over
the two endpoints. All other size and rule comparisons are descriptive with
bootstrap intervals and are labelled exploratory.

---

## 5. Sub-phase 4H.3 — pre-registered weight transformation experiment

The full pre-registration is `reports/PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md`.
Its SHA-256 is recorded in `experiments/results/phase_4h/weight_sensitivity.json`.
Summary:

- Transform families: Phase 4G primary (power 0.75), linear capped, log1p,
  power 0.5, power 1.0, uncapped power, `min(count, 60)` capped linear, and a
  graph-local target-normalised approximation. The dataset's `count/post_count`
  field is unavailable because the raw edge table is not present in the
  repository; this is reported as unavailable and not substituted silently.
- Sign policies: verified primary (reference), predicted fallback, unknown-zero
  equivalence check, candidate sign reversal (adversarial), global sign
  reversal (adversarial).
- Two drive conditions: fixed nominal 300 pA, and drive amplitude scaled to
  match the reference aggregate outgoing signed weight from the candidate group.
- 10 draws per configuration, seeds `20261109 + 300000 + 100 * config + i`.
- No configuration search. The grid is executed once and every cell is
  reported, including cells with no activity and cells with no action.

---

## 6. Sub-phase 4H.4 — sensory-to-BANC round-trip

### 6.1 Inputs

- The archived Phase 3B.2C replay (`experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`):
  100 frames, 215 lifecycle events, 43 pulses, 30 fps assumed.
- Two additional non-overlapping segments of the same recording (frames 0–99
  and 200–299) are extracted with the unchanged Phase 3B perception functions
  and archived under `experiments/phase_4h/sequences/`. They are segments of
  one recording group, not independent recordings.

### 6.2 Mapping

`configs/banc_sensory_mapping.yaml` maps feature groups to BANC annotation
pools (`super_class`, `cell_function`, `body_part_sensory`,
`peripheral_target_type`, `region`, `flow`, `side`). Every mapping entry carries
an evidence label (`published annotation`, `connectivity hypothesis`,
`computational convention`) and a hypothesis identifier. No FAFB root ID is
transferred. A visual annotation is not treated as evidence of a direct visual
pathway to motor control. Every mapped population is validated to exclude the
805 motor neurons and the LEFT/RIGHT/JUMP masks.

Coins and player pose are absent from the v15 detector schema and are reported
as unmapped, not invented.

### 6.3 Adapter

`brain/banc_sensory_adapter.py` implements the existing `input_schedule`
contract (`apply(step, time_ms, current)` and `stimulated_indices`) and is
passed to the unchanged `BancSimulator`. It:

- accepts the archived event dictionaries and validates required fields;
- rejects unknown features, unknown event kinds, negative or non-monotone
  timestamps, and indices outside the graph;
- preserves event order, timestamps, feature identity, lane, distance proxy and
  track id;
- adds current only to mapped sensory neurons and never to motor neurons;
- is deterministic and exposes a signature for reproducibility.

Drive is event-pulsed: each event contributes an encoded feature response
scaled by the feature current amplitude and decays linearly over 150 ms. No
held per-frame state is used because the archived replay exposes events, not
per-frame GameState features; this is recorded as a limitation. No action is
selected.

### 6.4 Conditions

A no events; B actual sequence; C temporally shuffled (the sorted time array is
permuted across events); D feature-identity shuffled (feature group assignment
permuted across events, times preserved); E random matched mapping (annotation
pools replaced by seeded size-matched non-motor pools); F constant neutral drive
with the same total injected charge; G background 50 pA plus 50 pA Gaussian
noise and no events.

Each condition runs on the full sequence and on both segments, with a repeat
run for B and G to verify determinism.

### 6.5 Endpoints

Total, stimulated, non-stimulated and motor spikes; decoder states; event-locked
spike counts in [t, t+50 ms); latency to the first downstream spike after each
event; alignment between event density and spike density at lags 0–200 ms;
real-versus-shuffled differences; reproducibility hashes.

### 6.6 Inference

The segments come from one recording and are not independent sequences. With
three non-independent streams, condition differences are reported descriptively
with intervals; no confirmatory p-value is claimed. Evidence level E4 is not
claimed on this basis.

---

## 7. Sub-phase 4H.5 — evidence classification

Twelve questions:

1. Is condition C distinguishable from multiple matched random controls?
2. How does the result depend on driven-group size?
3. How does it depend on the selection rule?
4. Does JUMP survive accounting for the 20-neuron pool size?
5. Is it stable across pre-registered weight transforms?
6. Does it depend on the sign policy?
7. Are thresholds 1/5/10 comparable?
8. Is the sensory round-trip reproducible?
9. Does the real event sequence differ from temporally shuffled events?
10. Are decoder outputs reproducible across repeated runs?
11. Does any effect survive matched random controls?
12. What conclusions are justified, and what remains unknown?

Evidence levels:

- E0: no reproducible effect.
- E1: a reproducible difference from the no-stimulation baseline.
- E2: a reproducible difference from matched random controls.
- E3: decoder outputs are reproducibly distinguishable from controls.
- E4: sensory event structure produces distinguishable propagated responses
  across independent sequences and controls.

E4 is not claimed unless independent sequences exist. The verdict is PASS,
PASS WITH LIMITATIONS, PARTIALLY COMPLETE or FAIL. JUMP alone does not qualify
as PASS.

---

## 8. Reproducibility recording

Every run records: software versions, configuration SHA-256, graph threshold
and artifact SHA-256, node/edge counts, sign policy, weight transform,
stimulation group and selection rule, amplitude, duration, dt, recording
window, seed, total spikes, active neurons, motor statistics, decoder output,
runtime and retained memory. Spike, decision, activity and configuration hashes
are compared between repeats. Exploratory and confirmatory results are written
to separate files. Phase 4G outputs are never overwritten.

## 9. Performance and resumability

Sparse CSR propagation only; no dense matrices, no graph copies. One graph and
one policy are loaded per process and reused. Recording is bounded at
5,000,000 spikes. Each experiment writes a checkpoint JSON after every completed
draw so an interrupted run can resume without re-running completed draws. No
sample size is reduced silently; if a run cannot complete, the completed
portion is reported with an explicit statement of what remains.

## 10. Testing

Focused tests cover random-control construction (determinism, size, uniqueness,
eligibility, family separation), population sensitivity (size handling, empty
and insufficient pools, ties, unequal motor pools), weight sensitivity
(transforms, zero and extreme weights, invalid parameters, normalisation, sign
handling, reproducibility), the sensory adapter (valid mapping, unknown
rejection, invalid timestamps, ordering, temporal preservation, empty and
repeated events, deterministic schedule) and integration (no motor stimulation,
correct BANC indices, spike recording, decoder input, NEUTRAL, deterministic
repeat). The focused 4H tests, the 4G/4F/4E/BANC graph tests and the full suite
are run and their pass/fail/skip counts recorded.

## 11. Deviations

Any deviation from this protocol after execution begins is recorded in
`experiments/results/phase_4h/deviations.json` with the reason, the affected
runs, and whether it was decided before or after seeing the affected result.
The protocol file is not edited after execution; a deviation is an appended
record, and if the change is substantive a versioned amendment file is created.
