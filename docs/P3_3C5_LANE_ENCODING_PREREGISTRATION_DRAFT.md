# P3-3C.5 — Lane Encoding Preregistration (Draft)

**Status: DRAFT — NOT APPROVED, NOT EXECUTED, NOT A RESULT.**

This document is a candidate freeze of the Phase 3C.5 lane-encoding protocol. It
has not been approved by the user, no configuration or runner exists, and no
simulation has been executed. It does not replace, modify or supersede any
existing result. Approval is requested in §17. Implementation and execution are
separate future tasks.

**Identifier.** The roadmap and the Phase 3C design enumerate this experiment
as **3C.5**. The file uses that identifier. The project task label is
**P3-3C.5**.

**Provenance.** Reviewed from
`docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md`
(SHA-256 `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284`),
the Phase 3C design, the Phase 3 roadmap, the Phase 3 sensory-encoding document,
the 3C.5/6/8 audit, the four relevant configuration files, the six relevant
implementation modules, and the P3-T2, P3-T3, P3-T4.1 and T7 artifacts. The
review report is `docs/P3_3C5_PREREGISTRATION_REVIEW.md`.

**What changed from the proposal.** The proposal's primary metric (M6, a
state-residual Euclidean distance over bins 4–8) is not a valid order contrast:
in that window C3 and C4 are always in different lanes, so the distance compares
residuals supported on different neuron groups. The proposal's 95th-percentile
rule is also not a statistical test: six deterministic block permutations give
14 non-focal distances and are not exchangeable. This draft replaces both. The
scientific question, the four conditions, the lane-only feature set, the
step/crossfade logic, the three-seed plan, the execution-validity gates and the
negative-result rules are retained. Every change is explained in the review.

---

## 0. Decision summary

| Item | Frozen candidate | Status |
|---|---|---|
| Primary question | Does the spiking response to lane CENTER depend on which lane preceded it, with current lane, time since onset, transition type, dwell, current and mapping held constant? | narrowed from Q4 |
| Conditions | C1 `L→C→R`, C2 `R→C→L`, C3 `L→C→R→L`, C4 `L→R→C→L` | C1/C2 original; C3/C4 new |
| Primary contrast | C1 vs C2, CENTER block, state-relative 0–150 ms (absolute 200–350 ms) | new use of the original pair |
| Secondary contrast | C3 vs C4, CENTER block (150 ms dwell); final LEFT block; RIGHT block | new |
| Primary statistic | `Δ_C = mean over 3 state-relative bins of [r_C1(C,s) − r_C2(C,s)]`, Hz | new metric M6′ |
| Auxiliary reference | `K_C` (CENTER onset from rest) to separate transition-onset from predecessor identity | new |
| Scheduler | T1 step (`transition_ms = 0`) primary; T1 50 ms crossfade for C1–C4 and the six 3-transition closed sequences | step new primary |
| Active features | `player_lane` only | new |
| Stimulated neurons | exactly 12 (4 per lane), 800 pA total at every step | implementation-supported |
| Seeds | 20261104, 20261105, 20261106; pilot 20261107 | 20261104 original; three-seed plan new |
| Reference method | descriptive, stratified: 6 linear + 12 closed + 2×6 single-transition + 3 constant + no-input; no p-values | replaces percentile test |
| Decision rule | effect size + sign consistency in ≥2/3 seeds + reference-range separation in the expected direction | descriptive |
| Validity gates | E1–E15, including `stimulus=None`, prefix identity, 800 pA audit | extended |
| Outcome classes | `HISTORY_EFFECT_PRESENT`, `HISTORY_EFFECT_DWELL_DEPENDENT`, `TRANSITION_ONSET_ONLY`, `NO_HISTORY_EFFECT`, `ROUTE_ONLY`, `ENDPOINT_EXPLAINED`, `INCONCLUSIVE_SILENT_C`, `INCONCLUSIVE_OUTSIDE`, `INCONCLUSIVE_REFERENCE_DEGENERATE`, `INVALID_EXECUTION` | new |
| Approval | ten decisions in §15; checklist in §17 | **pending** |

**One-sentence claim this experiment can support at most:** under a fixed
one-hot lane encoder, a fixed 12-neuron mapping and a deterministic LIF network,
the CENTER-group spike rate in the first 150 ms after CENTER onset differs
depending on whether the immediately preceding lane was LEFT or RIGHT, in at
least two of three mapping realizations, and the difference is not explained by
the current lane, dwell, transition type, total current or mapping. Nothing
about perception, learning, a task code or a biological mechanism follows.

---

## 1. Research question and scope

### 1.1 Primary question

**Q-P.** With the player held in CENTER, does the 12-neuron lane readout's
response in the first 150 ms after CENTER onset depend on whether CENTER was
entered from LEFT or from RIGHT, when the current lane, time since onset,
transition type (adjacent), dwell, injected current, stimulated neurons,
background, noise and mapping seed are held fixed?

This is the local, causally clean form of "order sensitivity of lane changes".
The original 3C.5 asks about a left→center→right sequence and its reverse. The
local instantiation asks the same question at one transition, where the future
suffix cannot influence the measured window.

### 1.2 Secondary questions

- **Q-S1 (dwell replication).** Does the same predecessor contrast appear at
  150 ms dwell in C3/C4?
- **Q-S2 (longer history).** At the matched final LEFT state (450–600 ms), does
  the response depend on the preceding sequence (C3 `L→C→R→L` vs C4
  `L→R→C→L`)?
- **Q-S3 (transition route).** Do adjacent and direct transitions produce
  different post-transition responses at the same new lane?
- **Q-S4 (whole-sequence).** Across the full 12-bin trajectory, do C3 and C4
  differ in the same-lane, state-relative responses, and is the difference
  confined to transition windows?
- **Q-S5 (mapping stability).** Is the sign of the primary contrast the same
  across three mapping seeds?

### 1.3 Out of scope

- Biological lane perception, visual processing or behaviour.
- Learning, plasticity or adaptation (the model has none).
- A "lane-order code", a decoder, or a downstream task.
- Generalisation beyond three mapping realisations.
- Statistical significance, p-values or confidence intervals.
- T2/T3 temporal encodings and T5 lane-change pulses (not implemented).
- The full 14-feature input regime (it ignites the network; P3-T2 C3).

### 1.4 Why the primary is C1/C2 at the CENTER block

C1 and C2 are exact time reverses, but their whole-sequence comparison is
endpoint-confounded. That confound does **not** apply inside the CENTER block:

- C1 is `L L L L | C C C C | R R R R`; C2 is `R R R R | C C C C | L L L L`.
- CENTER starts at 200 ms in both and is the current lane from 200 to 400 ms.
- The second transition (to RIGHT in C1, to LEFT in C2) occurs at 400 ms.
- The simulator is causal: the state at times < 400 ms cannot depend on input
  at 400 ms. Therefore, in the window 200–350 ms, the future endpoint cannot
  influence the response.
- In that window the two conditions differ only in the first 200 ms: LEFT in C1
  versus RIGHT in C2. The CENTER group, its current (200 pA per neuron), the
  transition type into CENTER (adjacent) and the dwell are identical.

This is the cleanest predecessor contrast available with the delivered encoder.
C3/C4 provide the endpoint-matched whole-sequence test and the 150 ms-dwell
replication, but their CENTER blocks occur at different absolute times (150 vs
300 ms) and after different prefix lengths, so they are a weaker primary.

---

## 2. Hypotheses

**H1 — Static identity (precondition).** Constant LEFT, CENTER and RIGHT
produce distinguishable per-lane group responses. Falsified if a group is
silent or all three are indistinguishable. A silent CENTER group makes the
primary inconclusive, not negative.

**H2 — Predecessor effect (primary).** The CENTER-group response in the first
150 ms after CENTER onset differs between C1 (entered from LEFT) and C2
(entered from RIGHT), at the same absolute time, dwell, transition type and
current. Prediction: uncertain; the encoder is memoryless and the neuron has no
adaptation, so any effect must come from synaptic filtering (5/8 ms), spike
reset/refractory nonlinearity or recurrent input. Falsified if `Δ_C` is zero or
sign-inconsistent across seeds, or if it does not exceed the reference ranges.

**H2b — Dwell replication.** The same sign of the predecessor contrast appears
in C3/C4 at 150 ms dwell. Falsified if the sign differs or `Δ_C` is zero.

**H2c — Transition-onset alternative.** The predecessor effect is distinguishable
from a non-specific transition-onset effect, using `K_C` (CENTER onset from
rest) as the no-predecessor reference. If C1 ≈ C2 ≠ K_C, the effect is
attributed to transition onset, not predecessor identity.

**H3 — Longer history at a matched state.** In the final LEFT block (450–600
ms), C3 and C4 have the same current lane, same onset time and same total
current, but different prior sequences. A difference here is a history effect
beyond the current state. Falsified if the settled bins (500–600 ms) do not
differ. This contrast is confounded with the last transition route (`R→L` in C3
vs `C→L` in C4) and is secondary.

**H4 — Transition route.** Adjacent and direct transitions differ in their
post-transition response at the same new lane. Prediction: true at the input
level by construction; the question is whether the spiking readout preserves it
beyond the new lane's static response. Falsified if route-matched and
route-mismatched transitions are indistinguishable.

**H5 — Sparse direct regime (validity).** Lane-only input leaves most of the
network silent, so the 12-neuron readout is not dominated by recurrent
ignition. Prediction: near-zero outside spikes, consistent with P3-T2 C1's
player block (0 outside) and P3-T4.1 (0 outside across 72 runs). Falsified if
outside activity dominates; the result is then a network-regime observation,
not a lane result.

**H6 — Reverse-time symmetry (diagnostic).** For a linear time-invariant system
with time-symmetric input, the response to a reversed sequence is the
time-reverse of the response. A nonzero reverse-time difference indicates
nonlinearity (spike threshold/reset/refraction), not an order code. Reported as
a diagnostic, not a success criterion.

---

## 3. Conditions and exact stimuli

### 3.1 Common timing

- Simulation `duration_ms = 600.5`, `dt_ms = 0.5`; the simulator runs
  `round(600.5 / 0.5) = 1,201` steps, i.e. 600.5 ms.
- Frame interval 50 ms; 12 frames at 0, 50, …, 550 ms; the state at 550 ms
  holds to 600.5 ms.
- Analysis bins 0–11 are half-open: bin `b` is `[50b, 50(b+1))` for `b = 0…10`
  and `[550, 600)` for `b = 11`. The final 0.5 ms (`[600, 600.5)`) is outside
  the bins and is reported separately as a tail, not analysed.
- State-relative bins: for a lane onset at `t0`, bin `s` is
  `[t0 + 50s, t0 + 50(s+1))`.
- Total injected lane current is 800 pA at every step in every condition
  (4 active neurons × 200 pA), including during a crossfade; E3 asserts it.

### 3.2 The four core conditions

| ID | Sequence | Frames | Start → end | Dwell | Transitions |
|---|---|---|---|---|---|
| C1 | `L→C→R` | `L L L L  C C C C  R R R R` | L → R | 200 ms | 2 adjacent |
| C2 | `R→C→L` | `R R R R  C C C C  L L L L` | R → L | 200 ms | 2 adjacent |
| C3 | `L→C→R→L` | `L L L  C C C  R R R  L L L` | L → L | 150 ms | adjacent, adjacent, direct |
| C4 | `L→R→C→L` | `L L L  R R R  C C C  L L L` | L → L | 150 ms | direct, adjacent, adjacent |

C2 is the exact time reverse of C1 and C4 of C3 under
`t'_i = (12 − 1 − i) × 50 ms`; the state multiset and dwell are preserved.

### 3.3 Controls and reference sequences

| Block | Sequences | Count per seed | Purpose |
|---|---|---|---|
| Constant lane | `K_L`, `K_C`, `K_R`: 12 frames of one lane | 3 | Static per-lane response; `K_C` is the CENTER-onset-from-rest reference |
| No input | `N0`: no schedule at all | 1 | Zero-spike validity (T7 3C.9 = 0) |
| Linear reference | all 6 permutations of 200 ms blocks `{L,C,R}` | 6 (C1/C2 included) | C1/C2 reference; endpoint and dwell differ |
| Closed reference | all 12 distinct arrangements of 150 ms blocks with multiset `{L,L,C,R}` | 12 (C3/C4 included) | Predecessor-stratified CENTER-block reference |
| Single-transition, 200/400 | `L→C`, `R→C`, `L→R`, `C→R`, `R→L`, `C→L`; 200 ms pre, transition at 200 ms, 400 ms post | 6 | Route response matched to C1/C2 block duration; `L→C` and `R→C` reproduce the C1/C2 prefixes |
| Single-transition, 150/450 | the same six routes; 150 ms pre, transition at 150 ms, 450 ms post | 6 | Route response matched to C3/C4 block duration; stationarity check |
| Crossfade replay | C1–C4 plus the six 3-transition closed sequences | 10 | Robustness to `transition_ms = 50` |
| Frame shuffle (optional) | 20 pre-registered permutations of the 12-frame multiset `{L×6, C×3, R×3}` | 20 | Order-destroyed descriptive reference; not part of the primary rule |

The 12 closed sequences are:

```
C L L R   C L R L   C R L L
L C L R   L C R L   R C L L
L L C R   L R C L   R L C L
L L R C   L R L C   R L L C
```

C3 is `L C R L`; C4 is `L R C L`. The six with the two LEFT blocks non-adjacent
(all with three transitions) are `L C L R`, `L R L C`, `L C R L`, `L R C L`,
`R L C L`, `C L R L`.

### 3.4 CENTER-block predecessor classification

For each closed sequence, the CENTER block has a predecessor (the preceding
block) or none if CENTER is first:

| CENTER position | Predecessor LEFT | Predecessor RIGHT | No predecessor |
|---|---|---|---|
| 2 | `L C L R`, `L C R L` (C3) | `R C L L` | — |
| 3 | `L L C R`, `R L C L` | `L R C L` (C4) | — |
| 4 | `L R L C`, `R L L C` | `L L R C` | — |
| 1 | — | — | `C L L R`, `C L R L`, `C R L L` |

Totals: predecessor LEFT = 6, predecessor RIGHT = 3, no predecessor = 3.
Excluding the focal sequences C3 and C4 leaves 5 and 2 respectively. This is
small and is **not** a sampling distribution; see §9.

### 3.5 Scheduler modes

- **Primary: T1 step, `transition_ms = 0`.** At a frame boundary the new lane's
  four neurons receive the full 200 pA immediately; the old lane's four drop to
  zero. Total current is preserved.
- **Robustness: T1 linear crossfade, `transition_ms = 50`.** During the first
  50 ms after a change, `values = (1−α)·previous + α·current`, with
  `α = (t − t0)/50`. At `α = 0.5`, eight neurons receive 100 pA each, which is
  below the 150 pA rheobase. The crossfade can therefore suppress direct drive;
  it is a robustness condition, not the primary.
- **Not used:** `TemporalActivationScheduler` sample-and-hold. With no lane
  pulse it produces piecewise-constant current that jumps at frame starts, the
  same direct-current profile as the step, and adds no lane event.

---

## 4. What C3 and C4 match — and do not match

| Stimulus property | C3 | C4 | Matched? |
|---|---|---|---|
| Duration / frame grid | 600.5 ms, 12×50 ms | same | yes |
| Dwell per block | 150 ms | 150 ms | yes |
| Lane occupancy | L×6, C×3, R×3 frames | L×6, R×3, C×3 frames | yes (same multiset) |
| Start / end lane | L / L | L / L | yes |
| Transition times | 150, 300, 450 ms | 150, 300, 450 ms | yes |
| Transition count | 3 | 3 | yes |
| Transition magnitudes (step) | 4 off / 4 on, 800 pA | 4 off / 4 on, 800 pA | yes |
| Transition magnitudes (crossfade) | 8 partial, 800 pA total | same | yes |
| Total current | 800 pA every step | 800 pA | yes |
| Active neurons per block | 4 | 4 | yes |
| Mapping (within a seed) | same 12 neurons | same 12 neurons | yes |
| Background / noise | 0 / 0 | 0 / 0 | yes |
| Initial 0–150 ms input | L | L | yes (identical) |
| Transition directions | `L→C, C→R, R→L` | `L→R, R→C, C→L` | no (order manipulation) |
| Transition-type order | adjacent, adjacent, direct | direct, adjacent, adjacent | no |
| Lane at each time | L, C, R, L | L, R, C, L | no (order manipulation) |
| Prior sequence at the final L | `L→C→R` | `L→R→C` | no (history manipulation) |

**Verdict.** C3/C4 are matched on duration, grid, dwell, occupancy, endpoints,
transition times and count, total and per-transition current, stimulated
neurons, background, noise and initial prefix. They are not matched on the
order of transition types (adjacent/direct) or on the lane active at each time.
Those two differences are unavoidable consequences of asking an order question
with three lanes and four blocks. No 4-block design over three lanes can match
them while differing in order. The experiment must therefore not claim that C3
and C4 are "perfectly matched", and must not attribute a C3/C4 difference to
"lane order" as a mechanism distinct from "transition-route order".

**How the design handles it.**

- C1/C2 CENTER block (primary): same current lane, same absolute time, same
  onset, same transition type (adjacent), same dwell, different predecessor
  (LEFT vs RIGHT). The immediate transition type is matched; only the
  predecessor lane differs.
- C3/C4 CENTER block (secondary): same as above at 150 ms dwell, but the
  CENTER block occurs at 150 ms in C3 and 300 ms in C4, so absolute time and
  prefix length differ. This is a dwell replication, not the cleanest primary.
- C3/C4 final LEFT block (secondary): same current lane, same absolute time,
  same onset, different prior sequence; the last transition route differs
  (`R→L` vs `C→L`) and is stated.
- The RIGHT block is route-confounded (`C→R` vs `L→R`) and is descriptive only.

---

## 5. Implementation inputs

### 5.1 Active features and stimulated neurons

- `active_features = ["player_lane"]`. All other features are encoded but
  masked to zero current.
- `SensoryInputScheduler._stimulated_indices` is built from `active_features`
  only (`sensory/input_scheduler.py` lines 126–131), so `stimulated_indices`
  has exactly 12 entries.
- `apply` adds values only at the mapped indices; all other features' values are
  zero. E2 asserts that exactly 12 neurons receive nonzero current and that no
  other neuron receives nonzero sensory current.

### 5.2 Encoder and mapping

- `LanePopulation.encode(lane)` writes amplitude 1.0 into the contiguous
  4-unit block `[4·lane, 4·lane+4)` and leaves baseline 0.0 elsewhere
  (`sensory/population_encoder.py` lines 188–200).
- Mapping groups are consumed in lane-code order left→center→right
  (`sensory/sensory_mapping.py` lines 83–97; `configs/sensory_config.yaml`
  lines 147–159). Group order must be asserted against lane codes 0/1/2 (E6).
- Pools: `visual_left` 5,892, `visual_center` 76, `visual_right` 5,458,
  `visual_any` 11,426, `mechanosensory` 2,674, on a 139,255-node graph. These
  are predicted annotation counts, not verified sensory pathways.
- The CENTER pool is 76 neurons versus 5,892/5,458 for LEFT/RIGHT. This is a
  systematic asymmetry: the CENTER group is drawn from a much smaller pool, so
  its connectivity neighbourhood may differ. Report the per-seed indices and
  root IDs. Do not interpret a CENTER-specific effect as a lane code.

### 5.3 Simulator settings

| Parameter | Value | Source |
|---|---|---|
| `dt_ms` | 0.5 | `configs/sensory_config.yaml` line 15 |
| `duration_ms` | 600.5 | protocol |
| Neuron | LIF, `C = 200 pF`, `g = 10 nS`, `tau = 20 ms` | `configs/neuron_config.yaml` |
| Rest / threshold / reset | −65 / −50 / −68 mV | same |
| Refractory | 2 ms | same |
| Rheobase | 150 pA | `(threshold − rest) × g` |
| Adaptation / STP | none | neuron model |
| Synapses | exponential, `tau_exc = 5 ms`, `tau_inh = 8 ms`, delay 1 ms | `configs/simulation_config.yaml` |
| Weight transform | power, 12 pA per synapse, exponent 0.75 | same (assumed, not measured) |
| Background current | 0.0 pA | `external_input.background_current_pa` |
| Noise | 0.0 pA | `external_input.noise_std_pa` |
| Phase 2 stimulus | **disabled**: `stimulus=None` | runner contract |
| Simulation seed | fixed and recorded | protocol |
| Spike capacity | 5,000,000 | `max_recorded_spikes` |

**Critical hazard.** `configs/simulation_config.yaml` contains
`external_input.stimulus.enabled: true` with 64 highest-degree neurons at
180 pA from 100 to 800 ms. That is a Phase 2 default and is **not** part of
3C.5. The runner must pass `stimulus=None` explicitly (the P3-T2
`causal_control.py` pattern) and assert `simulator.stimulus is None`. If the
Phase 2 stimulus is active, the run is invalid (E2), because 64 additional
neurons receive current and the "12 stimulated neurons / 800 pA" premise is
false.

**No-input control.** `SensoryInputScheduler` rejects an empty
`active_features` set. `N0` must therefore be a run with no input schedule at
all (`input_schedule=None`, `stimulus=None`), not a scheduler with zero active
features. E5 asserts this.

### 5.4 External artifacts and protected files

- `datasets/processed/connectome.npz` SHA-256
  `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`.
- `README.md` SHA-256
  `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563`.
- Existing Phase 3 results are never overwritten; new artifacts get new names.

---

## 6. Seeds and repeats

- Main mapping seeds: **20261104, 20261105, 20261106**. The first is the
  delivered Phase 3A/3A.5 seed; the other two are the P3-T4.1 draws.
- Pilot mapping seed: **20261107**, a new draw, used only for runtime,
  capacity, reference-degeneracy and metric-computability checks. Pilot data
  never enter the main result.
- One run per condition per seed. A second run in a fresh subprocess for
  `C1`, `C2`, `C3`, `C4`, `N0` and `K_C` is a determinism check, not an
  independent replicate.
- Do not report three seeds × two runs as six samples.
- The mapping is built once per seed and reused across conditions after its
  hash is verified. Encoders, scheduler and simulator are fresh per condition.
- The simulator seed is fixed; with zero noise it does not affect the result,
  but it is recorded.

**What three seeds do and do not support.** Three mapping realisations test
whether the sign and approximate magnitude of the effect survive a change of
which physical neurons are drawn. They do not estimate a population variance,
do not support a confidence interval, a standard error, a p-value or a claim of
"robustness", and do not generalise to other connectome samples or to the fly.
With `n = 3`, report the exact per-seed values and their range, not a standard
deviation.

---

## 7. Primary metric M6′ — state-relative predecessor contrast

### 7.1 Definition

Let `G_C` be the four stimulated CENTER neurons. Let `n_c(i, s)` be the spike
count of neuron `i` in condition `c` during state-relative bin `s` after CENTER
onset. The CENTER onset is `t_C = 200 ms` in C1 and C2; `t_C = 150 ms` in C3;
`t_C = 300 ms` in C4; `t_C = 0` in `K_C`. State-relative bin `s = 0,1,2` covers
`[t_C + 50s, t_C + 50(s+1))`.

Per-neuron rate:

```
r_c(i, s) = n_c(i, s) / 0.05            # Hz
```

Group mean:

```
r_c(C, s) = (1/4) * sum_{i in G_C} r_c(i, s)
```

Primary statistic:

```
Δ_C(c1, c2) = (1/3) * sum_{s=0..2} [ r_c1(C, s) - r_c2(C, s) ]     # Hz
```

- **P1 (primary):** `Δ_C(C1, C2)`.
- **P2 (dwell replication):** `Δ_C(C3, C4)`.
- **Auxiliary:** `Δ_C(C1, K_C)` and `Δ_C(C2, K_C)`, with the absolute-time
  caveat in §7.6.

Report per-bin `δ_s = r_c1(C,s) − r_c2(C,s)` and per-neuron
`Δ_C(i) = (1/3) Σ_s [r_c1(i,s) − r_c2(i,s)]` for all four CENTER neurons.

### 7.2 Inputs and dimensions

- Input: the simulator's recorded spike times and neuron indices, the mapping's
  four CENTER indices, and the known frame timeline. No simulator change is
  required.
- Dimensions: 12 conditions/sequences × 12 absolute bins × 12 stimulated
  neurons is the full record; the primary uses 2 conditions × 3 state-relative
  bins × 4 CENTER neurons and returns one scalar plus 3 per-bin and 4
  per-neuron values per seed.
- Time alignment is state-relative, not absolute, for P2; for P1 the two
  conditions have the same absolute onset (200 ms), so state-relative and
  absolute alignment coincide.

### 7.3 Baseline subtraction, normalization and aggregation

- **No baseline subtraction** for P1: both conditions are in CENTER for the
  same time since onset, so the static lane response is common to both and
  cancels in the difference. `K_C` is reported as a separate reference, not
  subtracted.
- **No normalization** for the primary: the unit is Hz and the magnitude is
  interpretable. An optional dimensionless complement
  `Δ_C / (r_C1 + r_C2 + 1 Hz)` is reported for readability, never as the
  primary.
- Aggregation: arithmetic mean over the 3 state-relative bins and the 4 CENTER
  neurons. Per-bin and per-neuron values are always reported; no variance
  inference and no weighting.

### 7.4 Inactive neurons, zeros and denominators

- All four CENTER neurons are included; a silent neuron contributes zero.
- If all four CENTER neurons are silent in C1 or C2, `Δ_C = 0` and the seed is
  classified `INCONCLUSIVE_SILENT_C`, not negative. The same rule applies if
  the CENTER group is silent in `K_C` when the auxiliary comparison is made.
- There is no division by a data-dependent quantity in the primary, so there is
  no zero-denominator case. The optional normalized complement uses an additive
  `1 Hz` in the denominator; it is never used for the decision.
- No cosine distance is used on signed or sparse rate vectors. Cosine is
  undefined or unstable for zero vectors and is not an order metric here.

### 7.5 Sensitivity to magnitude and identity

- The metric is **sensitive to firing-rate magnitude** (Hz). That is intended:
  a predecessor effect that changes the rate is the object of study. It is not
  a standardized effect size and is not comparable across operating points.
- The metric is **insensitive to neuron identity within a seed**, because the
  same four physical CENTER neurons are compared in both conditions (the
  mapping is reused). Across seeds the identities differ; the metric compares
  rates, never neuron labels. No neuron-identity matching across seeds is done.
- The metric is **sensitive to which cells within the CENTER group carry the
  response**. Per-neuron values are reported; a group-mean-only result that
  hides redistribution is not acceptable.

### 7.6 Why this is an order/history metric and not a static-lane metric

- P1 compares the same lane (CENTER), the same four neurons, the same current
  (200 pA each), the same onset time (200 ms), the same transition type
  (adjacent) and the same dwell (200 ms). The only difference is the first
  200 ms: LEFT in C1 versus RIGHT in C2. The measured window ends at 350 ms,
  before the second transition at 400 ms; causality excludes any future-input
  effect. Therefore a nonzero `Δ_C` cannot be a static lane effect or an
  endpoint effect.
- P1 can still reflect a **transition-onset** effect rather than a
  **predecessor-identity** effect. `K_C` (CENTER onset from rest) is the
  auxiliary reference: if C1 ≈ C2 but both differ from `K_C`, the effect is
  attributed to transition onset; if C1 and C2 differ from each other, it is a
  predecessor effect. `K_C` has a different absolute time (0–150 ms) from
  C1/C2 (200–350 ms); this is a stated limitation, not a matched control.
- P2 (C3/C4) repeats the contrast at 150 ms dwell but confounds absolute time
  (150 vs 300 ms) and prefix length (150 vs 300 ms). It is a replication, not
  the primary.
- The final-LEFT contrast (P3) holds the current state, absolute time and onset
  fixed, but confounds the last transition route (`R→L` vs `C→L`). It tests
  longer history only under that caveat.

### 7.7 Worked example (illustrative, not measured)

Suppose, in one mapping seed, the CENTER group's state-relative rates are:

| Condition | s=0 | s=1 | s=2 | mean |
|---|---|---|---|---|
| C1 (from LEFT) | 8.0 | 6.0 | 6.0 | 6.667 Hz |
| C2 (from RIGHT) | 4.0 | 4.0 | 2.0 | 3.333 Hz |
| K_C (from rest) | 5.0 | 4.0 | 4.0 | 4.333 Hz |

Then:

```
Δ_C(C1,C2) = 6.667 - 3.333 = 3.334 Hz
δ_s        = [4.0, 2.0, 4.0] Hz
Δ_C(C1,K_C) = 2.334 Hz
Δ_C(C2,K_C) = -1.000 Hz
```

The per-bin values show the difference is not confined to one bin. The `K_C`
values show C1 and C2 lie on opposite sides of the no-predecessor reference,
which is the pattern expected for a predecessor-identity effect rather than a
generic transition-onset effect. If instead C1 = C2 = 1.0 Hz and K_C = 5.0 Hz,
the pattern would be a transition-onset effect.

These numbers are invented to show the arithmetic. No result is implied.

---

## 8. Secondary metrics

| ID | Metric | Definition | Role |
|---|---|---|---|
| S1 | `Δ_C(C3,C4)` | Same formula, CENTER onset 150 ms (C3) / 300 ms (C4) | Dwell-150 replication |
| S2 | `Δ_L` | C3 vs C4, final LEFT block, state-relative bins s=1,2 (settled 500–600 ms) | Longer history; route-confounded |
| S3 | `Δ_R` | C3 vs C4, RIGHT block, state-relative s=0..2 | Route-confounded (`C→R` vs `L→R`) |
| S4 | `Δ_adj` | `Δ_C(C3,C4)` minus the `R→C` minus `L→C` 150/450 control difference | Route-adjusted sensitivity analysis |
| S5 | Per-lane trajectories | `r_c(l,b)` for l ∈ {L,C,R}, b = 0..11 | Full time-resolved readout, not only totals |
| S6 | Active counts | Active neurons per group per bin, indices and root IDs | Silence vs low rate |
| S7 | Outside activity | Non-stimulated spikes, active outside neurons, outside fraction | Recurrent recruitment |
| S8 | Total current | Injected sensory current per step; 800 pA assertion | Magnitude control |
| S9 | Reverse-time | `D_rev = mean_s |s_C3(s) − s_C4(2−s)|` on state-relative profiles | Nonlinearity diagnostic |
| S10 | Latency / peak | First spike, first 10 ms bin above pre-onset mean + SD, peak rate/time, decay | Transition characterization |
| S11 | Seed consistency | Per-seed `Δ_C` sign, per-lane rate rank correlations, range | Replication description |
| S12 | Route response | Single-transition controls, post-onset 0–150 ms by route and pre-duration | H4, S4, stationarity |

**Not used:** `d′` for the order contrast. `d′` requires a noise model; with
three deterministic seeds it would be a ratio of a between-condition difference
to a seed spread that is not a sampling distribution. The design document lists
`d′` for approach/retreat and frame-rate separability, not for lane order; it
must not be imported. `P3-T7`'s `d′ = 0.0` and `P3-T4.1`'s `P4 d′ = 0.1183`,
`P12 d′ = 0.0`, `P12S d′ = −0.184828` are prior evidence about a different
question and are not thresholds for 3C.5.

---

## 9. Reference methodology — descriptive, not a significance test

### 9.1 Why the proposal's null cannot be used

Six deterministic block permutations produce 15 pairwise distances, 14 after
removing the focal pair. The 95th percentile of 14 numbers is effectively the
maximum; it is not a stable tail estimate. The sequences are not exchangeable
under any null: they differ in endpoint, transition count and transition-type
order. A permutation p-value would be invalid even if the count were larger,
because the simulator is deterministic and the permutations are not random
draws. The word "null" is therefore replaced by "reference".

### 9.2 What is used instead

1. **Predecessor-stratified CENTER-block reference (primary reference).**
   From the 12 closed sequences, compute the CENTER-block response in
   state-relative bins 0–2 and classify each by predecessor (LEFT, RIGHT,
   none). Report the focal C3 and C4 values against the ranges of the
   non-focal sequences with the same predecessor. Excluding C3/C4, the
   predecessor-LEFT set has 5 values and predecessor-RIGHT has 2. This is a
   small, deterministic reference, not a distribution. It can show whether the
   focal values lie inside or outside the range of other sequences with the
   same predecessor; it cannot assign a probability.
2. **Constant-lane reference.** `K_L`, `K_C`, `K_R` give the steady-state
   response and `K_C` gives the CENTER-from-rest onset reference. The absolute
   time of `K_C`'s onset differs from C1/C2's; the state-relative onset is
   matched.
3. **Single-transition reference.** The 12 route runs (six routes at 200/400
   and six at 150/450) give the post-onset response for each route with a
   constant pre-lane. They are used for route characterization, for `Δ_adj`,
   and for a stationarity check (compare the first 150 ms post-onset with the
   last 150 ms; if they differ materially, slow drift is present and
   absolute-time comparisons are caveated).
4. **Linear reference.** The six 200 ms permutations give an independent
   qualitative check of the CENTER-block predecessor effect at a different
   dwell; only C1/C2 are onset-matched at 200 ms, so this is descriptive.
5. **Optional order-destroyed reference.** 20 fixed frame permutations of the
   multiset `{L×6, C×3, R×3}` preserve the frame counts but destroy dwell and
   transition structure. They are a secondary reference for the whole-trial
   per-lane trajectory, not a null for `Δ_C`. They are not part of the primary
   decision. The fixed permutation list is generated by a recorded seed and
   hashed before the main run.

### 9.3 Properties preserved and not preserved

| Reference | Duration | Dwell | Occupancy | Transition count | Endpoint | Transition-type order |
|---|---|---|---|---|---|---|
| Linear permutations | yes | 200 ms | yes | 2 | no | no |
| Closed permutations | yes | 150 ms | yes | 3 | only C3/C4 | no |
| Single-transition | yes | pre only | no | 1 | n/a | one route |
| Constant | yes | n/a | one lane | 0 | n/a | n/a |
| Frame shuffles | yes | no | yes | no | no | no |

No reference preserves every property. This is why none is called a null and no
p-value is computed.

### 9.4 What the reference can and cannot say

- **Can:** whether the focal value lies inside or outside the range of other
  sequences matched on the property of interest; whether the predecessor-LEFT
  and predecessor-RIGHT ranges overlap; whether a route control predicts the
  sequence response.
- **Cannot:** assign a false-positive rate, a p-value, a confidence interval or
  a "significant" label; generalise to unrun sequences; substitute for
  replication across seeds.

### 9.5 Optional linear-superposition residual (secondary, pilot-gated)

For each condition, predict the 12-neuron rate trajectory by summing the
responses to its constituent transitions measured in the single-transition
runs, aligned at the transition times. For a linear system the prediction is
exact; the residual measures nonlinear interaction. The single-transition runs
have a constant pre-lane, so the prediction is approximate. This analysis is
pre-registered as secondary and is not part of the decision rule. It is
reported only if the pilot confirms the runs are available and the alignment is
implementable.

---

## 10. Decision rule and outcome classes

### 10.1 Per-seed computation

For each seed:

1. Verify E1–E15. Any failure → `INVALID_EXECUTION`.
2. Compute `Δ_C(C1,C2)` (P1), `Δ_C(C3,C4)` (P2), `Δ_L`, `Δ_R`, the per-bin and
   per-neuron values, the active counts, the outside fraction and the total
   current.
3. Compute the non-focal predecessor-LEFT and predecessor-RIGHT CENTER-block
   ranges from the closed reference.
4. Define `SEPARATED_LEFT_RIGHT` if the predecessor-LEFT range lies entirely
   above the predecessor-RIGHT range, or entirely below it.
5. Define `FOCAL_CONSISTENT` if C1's value lies in the predecessor-LEFT range
   and C2's in the predecessor-RIGHT range (with C3/C4 excluded from the
   ranges), and the signs agree with `Δ_C`.

### 10.2 Cross-seed rule (descriptive, not significance)

- **Sign replication:** `sign(Δ_C(C1,C2))` is the same in at least 2 of 3
  seeds.
- **Reference replication:** `SEPARATED_LEFT_RIGHT` occurs in the same
  direction in at least 2 of 3 seeds.
- **Focal consistency:** `FOCAL_CONSISTENT` in at least 2 of 3 seeds.
- **Dwell consistency:** `sign(Δ_C(C3,C4))` equals `sign(Δ_C(C1,C2))` in at
  least 2 of 3 seeds.

A 2-of-3 pattern is reported as "2 of 3 mapping realisations", never as
"significant", "robust" or "confirmed". The exact per-seed values and ranges
are always reported.

### 10.3 Outcome classes

| Outcome | Criteria | Reporting |
|---|---|---|
| `HISTORY_EFFECT_PRESENT` | E pass; P1 sign replicated ≥2/3; reference separation in the expected direction ≥2/3; focal consistency ≥2/3; dwell consistency ≥2/3 | Descriptive predecessor/history effect under the configured model; no mechanism or code claim |
| `HISTORY_EFFECT_DWELL_DEPENDENT` | P1 positive as above, but dwell consistency fails | Effect at 200 ms dwell only; report both dwells |
| `NEGATIVE_PRIMARY_DWELL_DEPENDENT` | P1 negative, but P2 is positive with consistent sign | Primary is negative; report the 150 ms discrepancy without promoting it to the primary |
| `TRANSITION_ONSET_ONLY` | C1 ≈ C2 but both differ from `K_C` in the same direction in ≥2/3 | Attribute to transition onset, not predecessor identity |
| `NO_HISTORY_EFFECT` | E pass; P1 sign not replicated or reference ranges overlap in ≥2/3 | Negative result, reported without reframing |
| `ROUTE_ONLY` | P1 ≈ 0 but `Δ_R` or the single-transition route contrasts are nonzero | Attribute to transition route, not predecessor/order |
| `ENDPOINT_EXPLAINED` | C1/C2 whole-sequence difference but no CENTER-block effect, and the difference is within the constant-lane endpoint spread | Attribute to endpoint, not order |
| `INCONCLUSIVE_SILENT_C` | The CENTER group is silent in C1, C2 or `K_C` in ≥2/3 seeds | Capacity/threshold limitation; not a negative order result |
| `INCONCLUSIVE_OUTSIDE` | Outside activity dominates and the 12-neuron readout is not separable | Network-regime observation; no lane claim |
| `INCONCLUSIVE_REFERENCE_DEGENERATE` | All non-focal predecessor values are identical in ≥2/3 seeds | Report the degeneracy; no separation claim |
| `INVALID_EXECUTION` | Any E1–E15 failure | Report the failure and stop; do not interpret |

### 10.4 Negative-result rule

If C1/C2 do not separate, or the effect does not replicate, or the reference
ranges overlap, the correct output is `NO_HISTORY_EFFECT` (or the relevant
inconclusive class). It is reported with the same detail as a positive: all
per-seed values, per-bin and per-neuron tables, the reference ranges, the
active counts, the outside fraction and the total current. It must not be
reframed as "the network uses a temporal code", "the encoder is sufficient" or
"a trend". The original negative-result rule (design lines 318–319 and 365)
governs.

---

## 11. Execution validity E1–E15

| ID | Criterion |
|---|---|
| E1 | All core, control and reference runs complete without numerical, capacity or validation failure. |
| E2 | Exactly 12 neurons receive nonzero sensory current (`player_lane` only); `stimulated_indices` has 12 entries; all other neurons receive 0 pA sensory current; `simulator.stimulus is None`; background = 0; noise = 0. |
| E3 | Total injected sensory current is 800 pA at every step within `1e-9` pA, for holds and for crossfades. |
| E4 | Constant-lane runs activate exactly the intended group; a silent group is recorded, not hidden. |
| E5 | `N0` has `input_schedule=None`, `stimulus=None`, 0 background, 0 noise and 0 spikes. |
| E6 | Lane group order is asserted left, center, right against lane codes 0, 1, 2; the assertion fails loudly if the config order changes. |
| E7 | Lane groups are disjoint, four neurons each, inside their annotation pools; per-seed indices and root IDs are recorded. |
| E8 | C2 = reverse(C1) and C4 = reverse(C3) on the 50 ms grid; the sequence hashes differ and the state multiset is identical. |
| E9 | Prefix identity: C3 and C4 produce identical spike trains for 0–150 ms (same input, same initial state, deterministic simulator). Any difference is a runner/simulator failure. |
| E10 | A parent run and two fresh-subprocess runs produce identical input-schedule signatures and spike hashes for the determinism subset. |
| E11 | Crossfade reversal: for the crossfade mode, the C4 input-current vector at time `t` equals the C3 vector at `600 − t` within `1e-9` pA on the simulation grid. |
| E12 | The existing test suite passes unchanged; no simulator, encoder, mapping or scheduler semantics are modified. |
| E13 | All source/config/connectome/protected hashes and the git block are recorded in a sidecar; `git status` before and after shows no unintended change. |
| E14 | Outside activity is reported separately; if nonzero, the report states that the readout includes recurrent input and does not claim a direct-drive-only result. |
| E15 | The analysis bins are half-open and cover exactly `[0, 600)` ms; the `[600, 600.5)` tail is excluded from binning and reported. |

E1–E15 are execution validity, not scientific success. A valid run can yield a
negative result.

---

## 12. Exclusion rules

- A run with a numerical, capacity or validation failure is invalid; it is
  reported and not imputed.
- A run with nonzero background/noise, an active Phase 2 stimulus, or more than
  12 neurons receiving nonzero sensory current is invalid.
- A run whose C3/C4 prefix (0–150 ms) differs is invalid (E9).
- A run where the total current differs from 800 pA, or the crossfade reversal
  fails (E11), is invalid.
- A run where the mapping is not disjoint, the group order is not
  left/center/right, or a group is outside its pool is invalid.
- A seed where the CENTER group is silent is not excluded; it is classified
  `INCONCLUSIVE_SILENT_C` and the other seeds are reported.
- Runs are never excluded because their outcome is inconvenient. No seed is
  dropped for a negative or inconsistent result.
- Pilot seed 20261107 is excluded from the main result by construction.

---

## 13. Artifacts, hashes and reproducibility

### 13.1 Frozen configuration

A future implementation adds one new file, proposed as
`configs/p3_3c5_lane_encoding.yaml`, containing:

- protocol: `duration_ms: 600.5`, `frame_interval_ms: 50.0`, `bin_ms: 50.0`,
  `dt_ms: 0.5`, `current_pa: 200.0`, `transition_ms: 0` and `50`, zero
  background/noise, `stimulus: none`, spike capacity;
- the C1–C4, constant, no-input, linear, closed, single-transition and optional
  shuffle sequences as explicit `(timestamp_ms, GameState)` lists, not code;
- seeds 20261104/5/6 and pilot 20261107;
- analysis parameters: state-relative windows, bins, reference sets, seed rule.

The file does not exist yet. This document does not create it.

### 13.2 Artifacts

- `experiments/phase_3c/results/p3_3c5_lane_encoding.json`: per-run,
  per-condition, per-seed, per-bin counts; active indices and root IDs; current
  audit; outside activity; per-bin and per-neuron `Δ_C`; reference ranges;
  outcome class.
- `experiments/phase_3c/results/p3_3c5_lane_encoding.sidecar.json`: hashes,
  git block, environment, protected hashes.
- `experiments/phase_3c/results/p3_3c5_lane_encoding_report.md`: report with
  the decision, all per-seed values and limitations.
- The hashed preregistration itself (a later frozen file, not this draft).

Existing Phase 3 results are never overwritten. A rerun gets a new versioned
name and a supersession note.

### 13.3 Hashes recorded per run

- SHA-256 of the configuration file.
- SHA-256 of the canonical JSON sequence list, including the optional shuffle
  list.
- The scheduler's `signature()` for the input schedule.
- SHA-256 of the encoder, mapping, scheduler, simulator, neuron and synapse
  source files used.
- SHA-256 of `datasets/processed/connectome.npz`.
- SHA-256 of protected files (`README.md`, connectome).
- The git commit and a `git status` block.
- The environment (Python, NumPy, OS) and the simulator seed.

### 13.4 Determinism and regression tests

- The sequence builder produces the exact 12-frame timelines and hashes.
- C2 = reverse(C1) and C4 = reverse(C3) on the 50 ms grid.
- Lane-only masking yields exactly 12 stimulated neurons and 800 pA.
- `stimulus=None`, background 0, noise 0 are asserted.
- `N0` has no schedule and 0 spikes.
- Group order is left, center, right and fails if the config order changes.
- A crossfade at `α = 0.5` puts 100 pA on eight neurons (the drive-gap
  arithmetic).
- C3 and C4 produce identical prefix spikes for 0–150 ms.
- Parent and subprocess spike/schedule hashes match.
- The existing test suite passes unchanged.
- No test may be weakened to obtain a favourable result. The neuron model,
  synapse model and global simulation parameters are not changed to obtain a
  favourable result.

### 13.5 Pre-registration sequence

1. Approve this draft and the ten decisions.
2. Write and hash the frozen preregistration (protocol, conditions, controls,
   metrics, reference method, outcome classes, limitations).
3. Implement the runner/config/tests in a separate task; verify E1–E15 on a
   smoke run.
4. Run the pilot on seed 20261107; verify runtime, capacity, reference
   non-degeneracy and metric computability. Do not use pilot data in the main
   result.
5. Freeze the protocol and the decision rule; record the preregistration hash.
6. Run the main matrix on seeds 20261104/5/6.
7. Analyse and report, including negative results and limitations.

No main-run execution may occur before steps 1–5.

---

## 14. Limitations and interpretation boundaries

1. **Descriptive, not inferential.** There is no p-value, confidence interval
   or significance claim. The reference sets are deterministic and small.
2. **Three mapping seeds, four neurons per group.** No population inference;
   the exact per-seed values and range are reported. Three seeds do not
   establish robustness.
3. **One-hot encoder.** Lane identity is trivial at the input by construction.
   The experiment tests the spiking readout's history dependence, not how a
   fly encodes lane.
4. **Predecessor identity is confounded with predecessor pool.** LEFT and
   RIGHT are different annotation pools (5,892 vs 5,458 neurons), so "entered
   from LEFT" also means "entered from the visual-left pool". The contrast
   cannot separate lane label from pool identity. CENTER's pool is only 76
   neurons, a further asymmetry.
5. **P1 absolute time and `K_C`.** C1/C2 are matched in absolute time; `K_C`
   (CENTER from rest) is matched in time since onset but not in absolute time.
   The transition-onset attribution is therefore caveated.
6. **P2 is not perfectly matched.** C3/C4 CENTER blocks occur at 150 and 300 ms
   after different prefix lengths. P2 is a dwell replication, not the cleanest
   primary.
7. **P3 is route-confounded.** The final LEFT block is preceded by `R→L` in C3
   and `C→L` in C4. A difference is a history effect that includes the last
   transition route.
8. **No causal separation of direct and recurrent input.** There is no
   synapse-block control in the current interface. Outside activity is
   measured, not subtracted; a large outside fraction makes the result a
   network-regime observation.
9. **Lane-only is not the natural regime.** The full 14-feature input ignites
   the network (99.976% outside spikes in P3-T2 C3). The lane-only result does
   not generalise to the full sensory context.
10. **No adaptation or short-term plasticity.** Any history effect comes from
    synaptic filtering (5/8 ms), spike reset/refractory nonlinearity and
    recurrent dynamics. The model cannot show a persistent sequence memory.
11. **T5 lane pulses are not implemented.** The experiment cannot test an
    event-pulse hypothesis; T2/T3 are out of scope.
12. **Structural data are not physiological.** The connectome is measured
    structure; synapses are a computational approximation; weights are assumed,
    not measured. Pool annotations are predicted, not verified pathways.
13. **The 0.5 ms tail is not analysed.** Bins cover [0, 600) ms; the final
    0.5 ms is reported separately.
14. **The reference set cannot substitute for more sequences.** A larger
    matched reference requires a different block design (e.g. 6 blocks of
    100 ms) or more mapping seeds; neither is part of this freeze.
15. **Determinism is not robustness.** Identical repeat hashes show the runner
    is deterministic, not that the result generalises.

---

## 15. Ten-decision resolution table

The ten decisions are those in §11.2 of the proposal. Labels: **[ORIGINAL]**,
**[SUPPORTED]**, **[NEW]**. "Necessary" means required for the scientific
question; "operational" means required only to run or report.

| # | Original question | Resolution | Evidence | Necessary or operational | Limitation |
|---|---|---|---|---|---|
| D1 | What do the four conditions of 3C.5 mean? | Four sequence conditions C1–C4; C1/C2 the literal pair, C3/C4 the endpoint-matched extension. Primary is C1 vs C2 at the CENTER block; C3/C4 is the whole-sequence secondary. | Design line 245 (`4`, unnamed); no other definition; the four conditions are the minimal set that keeps the literal pair and adds an endpoint-matched pair. **[NEW]** interpretation of an **[ORIGINAL]** count. | Necessary to make the question identifiable. | The interpretation could be wrong (e.g. 4 = 2 sequences × 2 seeds). User must confirm. |
| D2 | Accept the cyclic C3/C4 extension? | Accept. C3 `L→C→R→L`, C4 `L→R→C→L`. | Three one-hot states in three positions cannot match endpoints while differing in order; the closed pair is the minimal fix; arbitrary timelines are supported by `input_scheduler.py`. **[NEW]**. | Necessary for the endpoint-matched whole-sequence test; operational cost of two conditions. | Adds a return transition; dwell changes 200→150 ms; C3/C4 are not directly comparable to C1/C2 on dwell; transition-type order is confounded. |
| D3 | Which scheduler? | T1 step `transition_ms=0` primary; T1 crossfade `transition_ms=50` for C1–C4 and the six 3-transition closed sequences. | `transition_ms` is a supported argument (`input_scheduler.py` 36–70, 162–174); at `α=0.5`, eight neurons receive 100 pA, below the 150 pA rheobase. **[ORIGINAL]** that T1 exists; **[NEW]** step as primary. | Necessary: the crossfade can suppress direct drive, so the step is the clean test. | The step is not the delivered Phase 3A default; the crossfade robustness block checks transfer. |
| D4 | How many seeds? | Three mapping seeds 20261104/5/6; pilot 20261107. | Original seed plan repeats only 3C.2/3C.7 (design lines 251–252); the deterministic simulator makes mapping spread the only variation; the roadmap's 2-of-3 convention exists for separability. **[ORIGINAL]** first seed; **[NEW]** three-seed plan. | Necessary for a replication description; operational cost 3×. | `n=3`, no CI/SD inference; seeds are not biological replicates; 2-of-3 is not significance. |
| D5 | Which active features? | `player_lane` only; 12 stimulated neurons. | P3-T2 C1: `player_speed` contributes 298 of 702 spikes and up to 1,096 pA; full input ignites (99.976% outside). Scheduler masks inactive features and builds `stimulated_indices` from active features (`input_scheduler.py` 126–131). **[NEW]**. | Necessary to isolate lane. | Not the natural full-input regime; lane-only may still recruit the network; measured, not assumed. |
| D6 | Which controls? | `K_L/K_C/K_R`, `N0`, 6 linear, 12 closed, 6 routes at 200/400, 6 routes at 150/450, crossfade replay; optional 20 frame shuffles. | T7 3C.9 no-input = 0; constant lanes needed for static identity and `K_C`; single-transition runs needed for route and stationarity; closed set needed for the predecessor reference. **[ORIGINAL]** no-input; **[NEW]** the rest. | Necessary for confound separation; operational cost. | No synapse-block or full-input replay; the single-transition pre-lane is constant, unlike the sequence context. |
| D7 | Which threshold? | **Revised.** No p-value and no 95th percentile. Descriptive effect size + sign replication + reference-range separation. | Six permutations → 14 distances; deterministic and non-exchangeable; design criterion 5 is qualitative (measurable difference or reported absence). **[NEW]**. | Necessary to avoid a false significance claim. | No false-positive rate; the decision is descriptive; small reference sets. |
| D8 | Is there a pilot? | Yes, seed 20261107, excluded from the main result. | No pilot in the original plan; deterministic simulator makes a pilot safe; it checks runtime, capacity, reference degeneracy and metric computability. **[NEW]**. | Operational only. | A different seed cannot validate the main mappings; the pilot must not tune thresholds. |
| D9 | Add a pool-matched (`visual_any`) control? | **Unresolved.** Recommended as optional, not core. | CENTER pool 76 vs LEFT 5,892 / RIGHT 5,458; a `visual_any` mapping is configurable but would change the mapping and needs its own runs. **[NEW]**. | Not necessary for the core; it addresses the pool asymmetry. | Without it, a CENTER-specific effect cannot be separated from pool size/identity. |
| D10 | Authorise implementation? | **Unresolved.** Requires explicit user approval and a separate task. | No config/runner exists; this document is design only. **[NEW]**. | Operational/procedural. | No scientific limitation; no run may start before approval and the frozen preregistration hash. |

---

## 16. Claims not made

- 3C.5 has not been run, completed or accepted.
- Phase 3C is not complete.
- The network does not perceive lanes, select actions or perform a task.
- The visual annotation pools are not an anatomically verified lane pathway.
- Four neurons are not claimed superior to twelve; the lane bank is fixed at 12.
- A one-hot encoder is not claimed to be how the fly encodes lane.
- A measured `Δ_C` is not a "lane-order code"; at most it is a descriptive
  predecessor/history effect under the configured model.
- A positive result does not imply a transition-route code, a sensory-routing
  claim, learning, motor behaviour or generalisation.
- T1, T2, T3 or T5 is not claimed to be the correct temporal encoding; T2/T3
  are out of scope and T5 lane pulses are not implemented.
- Deterministic repeatability is not robustness; three seeds are not a
  population.
- P3-T7 `d′ = 0.0` and P3-T4.1's non-separating `d′` values are prior negative
  evidence, not thresholds or positive lane evidence.

---

## 17. USER APPROVAL REQUIRED

The draft is not executable. Approval is required for each item below before
implementation, and no main run may occur before the frozen preregistration is
hashed.

- [ ] **D1** Four-condition interpretation: C1–C4 as the four conditions, with
      C1/C2 primary at the CENTER block and C3/C4 secondary.
- [ ] **D2** Closed C3/C4 extension.
- [ ] **D3** Step primary, crossfade robustness for C1–C4 plus the six
      3-transition closed sequences.
- [ ] **D4** Three mapping seeds 20261104/5/6 and pilot 20261107.
- [ ] **D5** `player_lane` only.
- [ ] **D6** Control/reference blocks, including both single-transition
      pre-durations; decide whether the optional 20-shuffle block is included.
- [ ] **D7 Revised** Abandon the 95th-percentile significance rule; use the
      descriptive effect-size + sign + reference-range rule.
- [ ] **D8** Pilot seed and exclusion.
- [ ] **D9** Decide whether to add the optional `visual_any` pool-matched
      control (unresolved).
- [ ] **D10** Authorise a separate implementation task; authorise a separate
      execution task after the frozen hash.
- [ ] **Primary metric** Approve M6′ (state-relative predecessor contrast at the
      CENTER block), replacing the proposal's cross-lane residual distance.
- [ ] **Decision rule** Approve the outcome classes and the 2-of-3 descriptive
      rule, and confirm that no p-value or significance claim will be made.
- [ ] **Negative result** Confirm that a negative or inconsistent result will be
      reported without reframing.
- [ ] **Artifacts** Approve the new artifact names and the no-overwrite rule.

Until these are checked, this document remains a draft, not a preregistration.

---

## Appendix A — Explicit timelines

Timestamps in ms; each state holds until the next timestamp; the 550 ms state
holds to 600.5 ms.

| t | 0 | 50 | 100 | 150 | 200 | 250 | 300 | 350 | 400 | 450 | 500 | 550 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | L | L | L | L | C | C | C | C | R | R | R | R |
| C2 | R | R | R | R | C | C | C | C | L | L | L | L |
| C3 | L | L | L | C | C | C | R | R | R | L | L | L |
| C4 | L | L | L | R | R | R | C | C | C | L | L | L |
| K_L | L | L | L | L | L | L | L | L | L | L | L | L |
| K_C | C | C | C | C | C | C | C | C | C | C | C | C |
| K_R | R | R | R | R | R | R | R | R | R | R | R | R |

State-relative CENTER windows:

| Condition | CENTER onset | s=0 | s=1 | s=2 | Extra |
|---|---|---|---|---|---|
| C1 | 200 | 200–250 | 250–300 | 300–350 | 350–400 (s=3) |
| C2 | 200 | 200–250 | 250–300 | 300–350 | 350–400 (s=3) |
| C3 | 150 | 150–200 | 200–250 | 250–300 | — |
| C4 | 300 | 300–350 | 350–400 | 400–450 | — |
| K_C | 0 | 0–50 | 50–100 | 100–150 | — |

## Appendix B — Source cross-reference

| Claim | Source |
|---|---|
| 3C.5 row and count `4` | `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` line 245 |
| Lane-change definition | same, line 91 |
| Reversal and fresh-state protocol | same, lines 265–272 |
| Criterion 5 and negative rules | same, lines 318–319, 365 |
| Seed plan (3C.2/3C.7 only) | same, lines 251–252 |
| 3C.5/6/8 unexecuted | `configs/temporal_sensory.yaml` lines 62–69; `p3_final_phase3_audit.md` |
| Lane one-hot, 3×4, 200 pA | `configs/sensory_config.yaml` lines 29–35; `sensory/population_encoder.py` 188–200 |
| Lane pools left/center/right | `configs/sensory_config.yaml` lines 147–159; `sensory/sensory_mapping.py` 83–97 |
| Active-feature masking / 12 indices | `sensory/input_scheduler.py` 126–131 |
| Crossfade formula | `sensory/input_scheduler.py` 162–174 |
| LIF parameters | `configs/neuron_config.yaml` |
| Zero background/noise; Phase 2 stimulus default | `configs/simulation_config.yaml` lines 51–60 |
| Simulator step count and stimulus handling | `brain/brain_simulator.py` `run` 192–260 |
| No lane-change pulse | `perception/temporal.py` 50–72; `sensory/temporal_scheduler.py` 238–257 |
| P3-T2 C1 player block | `experiments/phase_3c/results/p3_t2_full.json` |
| P3-T3 ablation | `experiments/phase_3c/results/p3_t3_ablation.json` |
| P3-T4.1 counts and d′ | `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json` |
| T7 no-input and d′ = 0.0 | `experiments/phase_3c/results/temporal_acceptance.json` |
| Connectome and README hashes | protected-file hashes in §5.4 |
