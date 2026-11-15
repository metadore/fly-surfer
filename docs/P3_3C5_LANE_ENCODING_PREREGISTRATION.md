# P3-3C.5 — Lane Encoding Preregistration (Frozen Protocol)

**Status: FROZEN PROTOCOL — AMENDED 2026-11-14; NOT EXECUTED; IMPLEMENTATION AND EXECUTION NOT AUTHORISED.**

**Freeze date.** 2026-11-14.

**Amendment.** Amended on 2026-11-14 under the recorded protocol amendment in
`docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md`: gate E11 is withdrawn, E2 and E10
are clarified, and §3.5 and §15 record that stimulus-sequence reversal does not
imply input-current reversal under the causal scheduler. The frozen hash before
amendment was
`1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857`; the
amended SHA-256 is recorded in the amendment record. No stimulus sequence,
seed, metric, scheduler behaviour or run count is changed.

**Identifier.** The Phase 3C design and the Phase 3 roadmap enumerate this
experiment as **3C.5**. The file uses that identifier. The project task label is
**P3-3C.5**.

**Authority.** The protocol below applies the decisions explicitly approved by
the user on 2026-11-14: D1 = C1–C4 with C1/C2 primary; D6 = drop the optional
20-frame-shuffle reference; D7 = no p-values, significance claims or
95th-percentile threshold; D9 = exclude the optional `visual_any` pool-matched
mapping; seeds 20261104/5/6 main and 20261107 pilot; 2-of-3 is descriptive
consistency only; negative results are reported without reframing; D10 =
implementation and execution remain separate future authorisations.

**Provenance.** Derived from
`docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md`
(SHA-256 `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284`),
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION_DRAFT.md`
(`3ceda5ece8017fc753a0f3aa9360a963efb58393717a89505d6efd08c3372438`),
`docs/P3_3C5_PREREGISTRATION_REVIEW.md`
(`f50fb2b7eec9a7577bbc28155ccd3e22d3b623d986fbc75b739311b89f3a973a`)
and
`docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md`
(`b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7`).
The proposal, draft and review are historical records and are not modified by
this document. The freeze record is
`docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md`.

**Freeze declaration.** This is the operative protocol. Any change after the
freeze requires a recorded protocol amendment and a new SHA-256 before a main
run. The document does not create a configuration, a runner, a test or a
result, and no simulation has been executed.

**One-sentence claim this experiment can support at most.** Under a fixed
one-hot lane encoder, a fixed 12-neuron mapping and a deterministic LIF
network, the CENTER-group spike rate in the first 150 ms after CENTER onset
differs depending on whether the immediately preceding lane was LEFT or RIGHT,
in at least two of three mapping realisations, and the difference is not
explained by the current lane, dwell, transition type, total current or
mapping. Nothing about perception, learning, a neural code or biology follows.

---

## 0. Approved decision summary

| Item | Frozen value | Status |
|---|---|---|
| D1 — four conditions | C1–C4; C1/C2 are the literal pair and the **primary** contrast; C3/C4 are the endpoint-matched extension | **approved** |
| D2 — closed extension | C3 `L→C→R→L`, C4 `L→R→C→L` | **approved** |
| D3 — scheduler | T1 step (`transition_ms=0`) primary; T1 50 ms crossfade robustness for C1–C4 plus the four additional 3-transition closed sequences (8 distinct crossfade sequences) | **approved** |
| D4 — seeds | main 20261104, 20261105, 20261106; pilot 20261107 excluded from the main result | **approved** |
| D5 — active features | `player_lane` only; exactly 12 stimulated neurons; 800 pA total | **approved** |
| D6 — controls | constants, no-input, 6 linear permutations, 12 closed sequences, 12 single-transition runs; the optional 20 frame-shuffle reference is **dropped** | **approved** |
| D7 — threshold | **no** p-value, significance claim or 95th-percentile threshold; descriptive effect size + sign replication + reference-range comparison | **approved** |
| D8 — pilot | 20261107; excluded; checks runtime, capacity, reference degeneracy and metric computability; no threshold tuning | **approved** |
| D9 — pool-matched control | `visual_any` control **excluded**; the pool asymmetry is a stated limitation | **approved** |
| D10 — authorisation | implementation and execution are separate future authorisations; **not authorised here** | **open (procedural)** |
| Primary contrast | C1 vs C2, CENTER block, state-relative 0–150 ms (absolute 200–350 ms) | approved |
| Primary statistic | `Δ_C(C1,C2)` in Hz (M6′) | approved |
| Auxiliary | `K_C` (CENTER onset from rest), with the absolute-time limitation | approved |
| Replication | 2-of-3 descriptive consistency, exact per-seed values and range; no SD, CI or significance | approved |
| Negative results | reported in full without reframing or threshold changes | approved |

---

## 1. Research question and scope

### 1.1 Primary question

**Q-P.** With the player held in CENTER, does the 12-neuron lane readout's
response in the first 150 ms after CENTER onset depend on whether CENTER was
entered from LEFT or from RIGHT, when the current lane, time since onset,
transition type (adjacent), dwell, injected current, stimulated neurons,
background, noise and mapping seed are held fixed?

This is the local, causally clean form of "order sensitivity of lane changes"
for the delivered encoder. The future suffix of the sequence is outside the
measured window and cannot influence it in a causal simulator.

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
- A "lane-order code", a decoder or a downstream task.
- Generalisation beyond three mapping realisations.
- Statistical significance, p-values or confidence intervals.
- T2/T3 temporal encodings and T5 lane-change pulses (not implemented).
- The full 14-feature input regime (it ignites the network; P3-T2 C3).
- The optional `visual_any` pool-matched mapping (D9 excluded).

### 1.4 Why C1/C2 at the CENTER block is primary

- C1 is `L L L L | C C C C | R R R R`; C2 is `R R R R | C C C C | L L L L`.
- CENTER starts at 200 ms in both and is the current lane from 200 to 400 ms.
- The next transition (to RIGHT in C1, to LEFT in C2) is at 400 ms.
- A causal simulator cannot let input at 400 ms affect spikes before 400 ms.
- In 200–350 ms the two conditions differ only in the first 200 ms: LEFT in C1
  versus RIGHT in C2. The CENTER group, its 200 pA per neuron, the adjacent
  transition into CENTER and the 200 ms dwell are identical.
- The single-transition controls `L→C` and `R→C` (200 ms pre, transition at
  200 ms) have exactly the same input as C1 and C2 for `t < 400 ms`, so by
  determinism the CENTER-block spike trains must match exactly (gate E16). This
  proves the window contains no suffix contribution; it does not add
  independent evidence.

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

**H2c — Transition-onset alternative.** The predecessor effect is
distinguishable from a non-specific transition-onset effect, using `K_C`
(CENTER onset from rest) as the no-predecessor reference. If C1 ≈ C2 ≠ K_C, the
effect is attributed to transition onset, not predecessor identity.

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

## 3. Conditions, stimuli and timing

### 3.1 Common timing and bins

- `duration_ms = 600.5`, `dt_ms = 0.5`; the simulator runs
  `round(600.5 / 0.5) = 1,201` steps.
- Frame interval 50 ms; 12 frames at 0, 50, …, 550 ms; the state at 550 ms
  holds to 600.5 ms.
- Absolute analysis bins 0–11 are half-open: bin `b` is `[50b, 50(b+1))` for
  `b = 0…10` and `[550, 600)` for `b = 11`. A spike at exactly a boundary
  belongs to the bin that starts at that boundary. The final 0.5 ms
  (`[600, 600.5)`) is outside the bins and is reported separately as a tail,
  not analysed.
- State-relative bins: for a lane onset at `t0`, bin `s` is
  `[t0 + 50s, t0 + 50(s+1))`.
- Total injected lane current is 800 pA at every step in every condition
  (4 active neurons × 200 pA), including during a crossfade; gate E3 asserts
  it.

### 3.2 The four core conditions

| ID | Sequence | Frames | Start → end | Dwell | Transitions |
|---|---|---|---|---|---|
| C1 | `L→C→R` | `L L L L  C C C C  R R R R` | L → R | 200 ms | 2 adjacent |
| C2 | `R→C→L` | `R R R R  C C C C  L L L L` | R → L | 200 ms | 2 adjacent |
| C3 | `L→C→R→L` | `L L L  C C C  R R R  L L L` | L → L | 150 ms | adjacent, adjacent, direct |
| C4 | `L→R→C→L` | `L L L  R R R  C C C  L L L` | L → L | 150 ms | direct, adjacent, adjacent |

C2 is the exact time reverse of C1 and C4 of C3 under
`t'_i = (12 − 1 − i) × 50 ms`; the state multiset and dwell are preserved.

### 3.3 Mandatory controls and references

The optional 20-frame-shuffle reference is **dropped** (D6). The `visual_any`
control is **excluded** (D9).

| Block | Sequences | Runs per seed | Mode | Purpose |
|---|---|---|---|---|
| Constant lane | `K_L`, `K_C`, `K_R`: 12 frames of one lane | 3 | step | Static per-lane response; `K_C` is the CENTER-onset reference |
| No input | `N0`: no schedule at all | 1 | none | Zero-spike validity |
| Linear 200 ms | all 6 permutations of the 200 ms blocks `{L,C,R}` | 6 (C1/C2 included) | step | Dwell-matched predecessor reference for P1 |
| Closed 150 ms | all 12 distinct arrangements of 150 ms blocks with multiset `{L,L,C,R}` | 12 (C3/C4 included) | step | Predecessor reference for P2 |
| Single-transition 200/400 | `L→C`, `R→C`, `L→R`, `C→R`, `R→L`, `C→L`; 200 ms pre, transition at 200 ms, 400 ms post | 6 | step | Exact causal decomposition of C1/C2 and route response |
| Single-transition 150/450 | the same six routes; 150 ms pre, transition at 150 ms, 450 ms post | 6 | step | Route response matched to C3/C4 block duration; stationarity |
| Crossfade replay | C1–C4 plus the four additional 3-transition closed sequences | 8 | crossfade | Robustness to `transition_ms = 50` |

The 12 closed sequences are:

```
C L L R   C L R L   C R L L
L C L R   L C R L   R C L L
L L C R   L R C L   R L C L
L L R C   L R L C   R L L C
```

C3 is `L C R L`; C4 is `L R C L`. The six 3-transition closed sequences are
`C L R L`, `L C L R`, `L C R L` (C3), `L R C L` (C4), `R L C L` and
`L R L C`. The four additional crossfade sequences are `C L R L`, `L C L R`,
`R L C L` and `L R L C`.

The six 200 ms permutations are `L C R` (C1), `R C L` (C2), `C L R`, `C R L`,
`L R C` and `R L C`.

### 3.4 Predecessor classification of the CENTER block

**Linear 200 ms set (R200).** CENTER is preceded by LEFT in `R L C`, by RIGHT in
`L R C`, and has no predecessor in `C L R` and `C R L`. Excluding the focal C1
and C2 leaves one pred-LEFT value and one pred-RIGHT value.

**Closed 150 ms set (R150).**

| CENTER position | Predecessor LEFT | Predecessor RIGHT | No predecessor |
|---|---|---|---|
| 2 | `L C L R`, `L C R L` (C3) | `R C L L` | — |
| 3 | `L L C R`, `R L C L` | `L R C L` (C4) | — |
| 4 | `L R L C`, `R L L C` | `L L R C` | — |
| 1 | — | — | `C L L R`, `C L R L`, `C R L L` |

Totals: pred-LEFT 6, pred-RIGHT 3, none 3. Excluding C3 and C4 leaves 5 and 2.
This is a small deterministic reference set, not a sampling distribution.

### 3.5 Scheduler modes

- **Primary: T1 step, `transition_ms = 0`.** At a frame boundary the new lane's
  four neurons receive the full 200 pA immediately; the old lane's four drop to
  zero. Total current is preserved.
- **Robustness: T1 linear crossfade, `transition_ms = 50`.** During the first
  50 ms after a change, `values = (1−α)·previous + α·current`, with
  `α = (t − t0)/50`. At `α = 0.5`, eight neurons receive 100 pA each, below the
  150 pA rheobase. The crossfade can suppress direct drive; it is a robustness
  condition, not the primary.

The blend is causal and one-sided: it exists only in the 50 ms after a change,
never before it. It is therefore not time-reversal equivariant. Reversing the
frame sequence does not reverse the input-current waveform: the C4
input-current vector is not the time reverse of the C3 vector, even though the
C4 frame sequence is the reverse of the C3 frame sequence (E8). No execution
gate requires input-current reversal; E8 checks the frame sequences and E3
checks current conservation.

- **Not used:** `TemporalActivationScheduler` sample-and-hold. With no lane
  pulse it produces piecewise-constant current that jumps at frame starts, the
  same direct-current profile as the step, and adds no lane event.

### 3.6 Exact input and model specification

| Parameter | Frozen value | Source |
|---|---|---|
| Active features | `["player_lane"]` | D5 |
| Lane encoding | one-hot, 3 lanes × 4 neurons, amplitude 1.0, baseline 0.0 | `configs/sensory_config.yaml` lines 29–35 |
| Current | `current_pa = {"player_lane": 200.0}`; all other features 0.0 | same, line 35 |
| Scheduler | `SensoryInputScheduler`, `onset_ms=0`, `offset_ms=600.5`, `duration_ms=600.5` | `sensory/input_scheduler.py` |
| Mapping | full `SensoryMapping` from `configs/sensory_config.yaml`; seed overridden per run | `sensory/sensory_mapping.py` |
| Lane pools | left→`visual_left` (5,892), center→`visual_center` (76), right→`visual_right` (5,458) | config lines 147–159; read-only counts on the 139,255-node graph |
| `dt_ms` | 0.5 | `configs/sensory_config.yaml` line 15 |
| Neuron | LIF: `C=200 pF`, `g=10 nS`, `tau=20 ms`; rest −65, threshold −50, reset −68 mV; refractory 2 ms; minimum −90 mV | `configs/neuron_config.yaml` |
| Rheobase | 150 pA | `(threshold − rest) × g` |
| Adaptation / STP | none | neuron model |
| Synapses | exponential, `tau_exc=5 ms`, `tau_inh=8 ms`, delay 1 ms | `configs/simulation_config.yaml` |
| Weight transform | power, 12 pA per synapse, exponent 0.75 (assumed, not measured) | same |
| Background / noise | 0.0 / 0.0 | same |
| Phase 2 stimulus | **disabled**: `stimulus=None`; assert `simulator.stimulus is None` | runner contract |
| Spike capacity | 5,000,000 | `configs/sensory_config.yaml` line 19 |
| Recorded outputs | spike times and neuron indices; per-neuron counts derivable | simulator |
| Simulator seed | fixed and recorded (does not affect zero-noise results) | protocol |

**State construction.** Each timeline entry is
`GameState(player=PlayerState(lane=<Lane>), time_ms=<timestamp>)`, with
`obstacle`, `train` and `coin` absent and all other player fields at their
documented defaults. Only `player_lane` is active, so all other encoders are
masked to zero current. The canonical sequence list is the source of truth and
is hashed before the run (Appendix A).

**Mapping construction hazard.** Build the full mapping from the delivered
configuration, not a reduced one containing only `player_lane`. Override only
the mapping seed. The lane groups are allocated in lane-code order
left→center→right; the runner asserts this order against lane codes 0/1/2.
Record the per-seed indices and root IDs.

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
neurons, background, noise and initial prefix. They are **not** matched on the
order of transition types (adjacent/direct) or on the lane active at each time.
Those differences are unavoidable consequences of asking an order question
with three lanes and four blocks. No 4-block design over three lanes can match
them while differing in order. The experiment must not claim that C3 and C4 are
"perfectly matched", and must not attribute a C3/C4 difference to "lane order"
as a mechanism distinct from "transition-route order".

**How the design handles it.**

- **C1/C2 CENTER block (primary):** same current lane, same absolute time,
  same onset, same transition type (adjacent), same dwell, different
  predecessor (LEFT vs RIGHT). The immediate transition type is matched; only
  the predecessor lane differs.
- **C3/C4 CENTER block (secondary):** same comparison at 150 ms dwell, but the
  CENTER block occurs at 150 ms in C3 and 300 ms in C4, so absolute time and
  prefix length differ. This is a dwell replication, not the cleanest primary.
- **C3/C4 final LEFT block (secondary):** same current lane, same absolute
  time, same onset, different prior sequence; the last transition route differs
  (`R→L` vs `C→L`) and is stated.
- **RIGHT block:** route-confounded (`C→R` vs `L→R`) and descriptive only.

---

## 5. Implementation contract and hazards

1. **Disable the Phase 2 stimulus.** `configs/simulation_config.yaml` contains
   `external_input.stimulus.enabled: true` with 64 highest-degree neurons at
   180 pA from 100 to 800 ms. The runner must pass `stimulus=None` and assert
   `simulator.stimulus is None` (E2). If the Phase 2 stimulus is active, the
   run is invalid.
2. **No-input control.** `SensoryInputScheduler` rejects an empty
   `active_features` set. `N0` must be a run with `input_schedule=None` and
   `stimulus=None`, not a scheduler with zero active features (E5).
3. **Stimulated set has exactly 12 indices.** `_stimulated_indices` is built
   from `active_features` only (`sensory/input_scheduler.py` lines 126–131),
   so a lane-only schedule has exactly 12 indices. Assert this (E2). This is a
   set-level statement: it does not mean all 12 neurons receive nonzero current
   at every step. `K_L`, `K_C`, `K_R` and every step-mode schedule drive four
   neurons; a crossfade drives four at `α = 0` and at/after the 50 ms window
   and eight for `0 < α < 1`; `N0` has no schedule and drives none.
4. **Total current.** The scheduler computes `activation × current_pa`; the
   active lane's four neurons each receive 1.0 × 200 pA = 200 pA, for 800 pA
   total. Assert 800 pA at every step to `1e-9` pA (E3).
5. **Prefix identity.** C3 and C4 have identical input for 0–150 ms and the
   same initial state, so their spike trains must be identical in that window
   (E9). Any difference is a runner or simulator failure.
6. **Causal decomposition.** C1 and the `L→C` single-transition run have
   identical input for `t < 400 ms`; C2 and `R→C` likewise. Their spike trains
   must be identical for `t < 400 ms` (E16). This is a correctness gate, not an
   additional comparison.
7. **Crossfade construction (no reversal requirement).** In crossfade mode,
   the C4 frame sequence is the reverse of the C3 frame sequence on the 50 ms
   grid (E8), and the same §3.5 causal blend is applied after each change. The
   injected current vector at time `t` is not required to equal the C3 vector
   at `600 − t`; the one-sided blend is not time-reversal equivariant. Total
   current remains 800 pA (E3), and the `α = 0.5` local check remains (§14.4).
8. **Half-open bins.** Do not mix the tail `[600, 600.5)` into bin 11 (E15).
9. **Group order.** Assert left, center, right against lane codes 0, 1, 2; fail
   loudly if the configuration order changes (E6).
10. **No feature leakage.** Every non-lane encoder is masked; assert that no
    neuron outside the 12 receives nonzero sensory current (E2).

---

## 6. Seeds and the run matrix

### 6.1 Seeds

- Main mapping seeds: **20261104, 20261105, 20261106**. The first is the
  delivered Phase 3A/3A.5 seed; the other two are the P3-T4.1 draws.
- Pilot mapping seed: **20261107**, a new draw, used only for runtime,
  capacity, reference-degeneracy and metric-computability checks. Pilot data
  never enter the main result.
- One run per condition per seed. One repeat run in a fresh subprocess for the
  step-mode `C1`, `C2`, `C3` and `C4`, plus `N0` and `K_C`, is a determinism
  check, not an independent replicate. Do not report three seeds × two runs as
  six samples.
- The mapping is built once per seed and reused across conditions after its
  hash is verified. Encoders, scheduler and simulator are fresh per condition.
- The simulator seed is fixed; with zero noise it does not affect the result,
  but it is recorded.

### 6.2 Planned run matrix

| Set | Distinct runs per seed | Seeds | Run instances |
|---|---|---|---|
| Core C1–C4 | 4 | 3 | 12 |
| Additional linear 200 ms (`C L R`, `C R L`, `L R C`, `R L C`) | 4 | 3 | 12 |
| Additional closed 150 ms (10 non-focal) | 10 | 3 | 30 |
| Constants `K_L`, `K_C`, `K_R` | 3 | 3 | 9 |
| No input `N0` | 1 | 3 | 3 |
| Single-transition 200/400 | 6 | 3 | 18 |
| Single-transition 150/450 | 6 | 3 | 18 |
| Crossfade (C1–C4 + four additional closed) | 8 | 3 | 24 |
| **Main total** | **42** | **3** | **126** |
| Determinism repeats (fresh subprocess; step-mode C1–C4, N0, K_C) | 6 | 3 | 18 |
| Pilot (full 42-run matrix) | 42 | 1 | 42 |
| **Planned total** | | | **186** |

Failed attempts are preserved and reported; they are not replaced silently.

### 6.3 What three seeds do and do not support

Three mapping realisations test whether the sign and approximate magnitude of
the effect survive a change of which physical neurons are drawn. They do not
estimate a population variance, do not support a confidence interval, a
standard error, a p-value or a claim of "robustness", and do not generalise to
other connectome samples or to the fly. With `n = 3`, report the exact per-seed
values and their range, not a standard deviation.

---

## 7. Primary metric M6′

### 7.1 Definition

Let `G_C` be the four stimulated CENTER neurons (lane code 1). Let `n_c(i, s)`
be the spike count of neuron `i` in condition `c` during state-relative bin `s`
after CENTER onset. The CENTER onset is `t_C = 200 ms` in C1 and C2;
`t_C = 150 ms` in C3; `t_C = 300 ms` in C4; `t_C = 0` in `K_C`.
State-relative bin `s = 0,1,2` covers `[t_C + 50s, t_C + 50(s+1))`.

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
- Dimensions: the full record is 42 run instances × 12 absolute bins × 12
  stimulated neurons per seed; the primary uses 2 conditions × 3 state-relative
  bins × 4 CENTER neurons and returns one scalar plus 3 per-bin and 4
  per-neuron values per seed.
- Time alignment is state-relative for P2; for P1 the two conditions have the
  same absolute onset (200 ms), so state-relative and absolute alignment
  coincide.

### 7.3 Baseline subtraction, normalization and aggregation

- **No baseline subtraction** for P1: both conditions are in CENTER for the
  same time since onset, so the static lane response is common to both and
  cancels in the difference. `K_C` is reported as a separate reference, not
  subtracted.
- **No normalization** for the primary: the unit is Hz and the magnitude is
  interpretable. A dimensionless descriptive ratio may be reported for
  readability, never as the primary and never in the decision rule.
- Aggregation: arithmetic mean over the 3 state-relative bins and the 4 CENTER
  neurons. Per-bin and per-neuron values are always reported; no variance
  inference and no weighting.

### 7.4 Inactive neurons, zeros and denominators

- All four CENTER neurons are included; a silent neuron contributes zero.
- If all four CENTER neurons are silent in C1 or C2, `Δ_C = 0` and the seed is
  classified `INCONCLUSIVE_SILENT_C`, not negative. The same rule applies if
  the CENTER group is silent in `K_C` when the auxiliary comparison is made.
- There is no division by a data-dependent quantity in the primary, so there is
  no zero-denominator case.
- No cosine distance is used on signed or sparse rate vectors. Cosine is
  undefined or unstable for zero vectors and is not an order metric here.

### 7.5 Sensitivity to magnitude and identity

- The metric is **sensitive to firing-rate magnitude** (Hz). That is intended:
  a predecessor effect that changes the rate is the object of study. It is not
  a standardised effect size and is not comparable across operating points.
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

### 9.1 Why no p-value is computed

- Six deterministic permutations produce 15 pairwise contrasts, 14 after
  removing the focal pair. A 95th percentile of 14 numbers is effectively the
  maximum and is not a stable tail estimate.
- The sequences are not exchangeable under any null: they differ in endpoint,
  transition count and transition-type order.
- The simulator is deterministic, so the permutations are fixed numerical
  objects, not random draws. A permutation p-value would be invalid even with
  a larger count.
- The word "null" is therefore replaced by "reference". No p-value, no
  confidence interval and no "significant" label is produced.

### 9.2 Reference sets

1. **Causal decomposition (exact).** `L→C` and `R→C` at 200/400 ms are the
   exact causal decomposition of C1 and C2 for `t < 400 ms` (gate E16). They
   confirm that the CENTER window contains no suffix contribution. They are
   not independent evidence and are not counted as replicates.
2. **Dwell-matched predecessor reference R200 (P1).** The six 200 ms
   permutations. Excluding C1/C2, pred-LEFT is `R L C` (one value) and pred-RIGHT
   is `L R C` (one value); `C L R` and `C R L` have no predecessor. This is a
   one-versus-one comparison, not a distribution, and the CENTER block is at a
   different position and absolute time. It is a weak descriptive cross-check.
3. **Closed predecessor reference R150 (P2).** The twelve 150 ms closed
   sequences. Excluding C3/C4, pred-LEFT has 5 values and pred-RIGHT has 2; the
   three sequences beginning with CENTER have no predecessor. Report the focal
   C3/C4 values against these small ranges.
4. **Constant-lane reference.** `K_L`, `K_C`, `K_R` give the steady-state
   response and `K_C` gives the CENTER-from-rest onset reference. The absolute
   time of `K_C`'s onset differs from C1/C2's; the state-relative onset is
   matched.
5. **Single-transition reference.** The 12 route runs (six routes at 200/400
   and six at 150/450) give the post-onset response for each route with a
   constant pre-lane. They are used for route characterization, for `Δ_adj`,
   and for a stationarity check (compare the first 150 ms post-onset with the
   last 150 ms; if they differ materially, slow drift is present and
   absolute-time comparisons are caveated).

### 9.3 Properties preserved and not preserved

| Reference | Duration | Dwell | Occupancy | Transition count | Endpoint | Transition-type order |
|---|---|---|---|---|---|---|
| R200 linear | yes | 200 ms | yes | 2 | no | no |
| R150 closed | yes | 150 ms | yes | 3 | only C3/C4 | no |
| Single-transition | yes | pre only | no | 1 | n/a | one route |
| Constant | yes | n/a | one lane | 0 | n/a | n/a |

No reference preserves every property. This is why none is called a null and no
p-value is computed.

### 9.4 What the reference can and cannot say

- **Can:** whether the focal value lies inside or outside the range of other
  sequences matched on the property of interest; whether the pred-LEFT and
  pred-RIGHT values separate and in which direction; whether a route control
  predicts the sequence response.
- **Cannot:** assign a false-positive rate, a p-value, a confidence interval or
  a "significant" label; generalise to unrun sequences; substitute for
  replication across seeds.

### 9.5 Optional linear-superposition residual (secondary, pilot-gated)

For each condition, predict the 12-neuron rate trajectory by summing the
responses to its constituent transitions measured in the single-transition
runs, aligned at the transition times. For a linear system the prediction is
exact; the residual measures nonlinear interaction. The single-transition runs
have a constant pre-lane, so the prediction is approximate. This analysis is
secondary and is not part of the decision rule. It is reported only if the
pilot confirms the runs are available and the alignment is implementable.

---

## 10. Decision rule and outcome classes

### 10.1 Per-seed computation

For each seed:

1. Verify the applicable gates E1–E10 and E12–E16 (E11 is withdrawn). Any
   failure → `INVALID_EXECUTION`.
2. Compute `Δ_C(C1,C2)` (P1), `Δ_C(C3,C4)` (P2), `Δ_L`, `Δ_R`, the per-bin and
   per-neuron values, the active counts, the outside fraction and the total
   current.
3. Compute the R200 predecessor values (pred-LEFT `R L C`; pred-RIGHT `L R C`)
   and the R150 predecessor values (pred-LEFT 5, pred-RIGHT 2).
4. `SEPARATED_200` is true if the R200 pred-LEFT value lies strictly above the
   pred-RIGHT value, or strictly below it; the direction is recorded.
   `SEPARATED_150` is defined analogously from the R150 ranges.
5. `FOCAL_200` is true if C1 lies on the pred-LEFT side of the R200 split and
   C2 on the pred-RIGHT side, and the signs agree with `P1`. `FOCAL_150` is
   defined analogously for C3/C4 and `P2`.

All predicates are set-based. No numeric effect-size cut-off is invented.

### 10.2 Cross-seed rule (descriptive, not significance)

- **Sign replication:** `sign(Δ_C(C1,C2))` is the same in at least 2 of 3
  seeds.
- **Reference replication:** `SEPARATED_200` occurs in the same direction in at
  least 2 of 3 seeds.
- **Focal consistency:** `FOCAL_200` is true in at least 2 of 3 seeds.
- **Dwell consistency:** `sign(Δ_C(C3,C4))` equals `sign(Δ_C(C1,C2))` in at
  least 2 of 3 seeds.

A 2-of-3 pattern is reported as "2 of 3 mapping realisations", never as
"significant", "robust" or "confirmed". The exact per-seed values and ranges
are always reported. There is no SD, standard error or confidence interval.

### 10.3 Outcome classes

Classes are assigned in the order below; the first matching class wins. This
order prevents a positive from being assigned to an invalid, silent or
degenerate run.

| Order | Outcome | Group | Criteria | Reporting |
|---|---|---|---|---|
| 1 | `INVALID_EXECUTION` | invalid | Any applicable-gate failure (E1–E10, E12–E16; E11 withdrawn) | Report the failure and stop; do not interpret |
| 2 | `INCONCLUSIVE_SILENT_C` | ambiguous | The CENTER group is silent in C1, C2 or `K_C` in ≥2/3 seeds | Capacity/threshold limitation; not a negative order result |
| 3 | `INCONCLUSIVE_OUTSIDE` | ambiguous | Outside spikes exceed CENTER-group spikes in the 200–350 ms window in ≥2/3 seeds | Network-regime observation; no lane claim |
| 4 | `INCONCLUSIVE_REFERENCE_DEGENERATE` | ambiguous | The R200 pred-LEFT and pred-RIGHT values are identical, or the R150 ranges are degenerate, in ≥2/3 seeds | Report the degeneracy; no separation claim |
| 5 | `HISTORY_EFFECT_PRESENT` | positive | E pass; P1 sign replicated ≥2/3; `SEPARATED_200` in the expected direction ≥2/3; `FOCAL_200` ≥2/3; dwell consistency ≥2/3 | Descriptive predecessor/history effect under the configured model; no mechanism or code claim |
| 6 | `HISTORY_EFFECT_DWELL_DEPENDENT` | positive | P1 criteria as in row 5, but dwell consistency fails | Effect at 200 ms dwell only; report both dwells |
| 7 | `NEGATIVE_PRIMARY_DWELL_DEPENDENT` | ambiguous | P1 fails, but P2 is positive with consistent sign in ≥2/3 | Primary negative; report the 150 ms discrepancy without promoting it |
| 8 | `TRANSITION_ONSET_ONLY` | negative | P1 fails, and both C1 and C2 lie outside the R200 union on the same side as `K_C` in ≥2/3 | Attribute to transition onset, not predecessor identity |
| 9 | `ROUTE_ONLY` | negative | P1 fails, but `Δ_R` or the single-transition route contrasts show a predecessor-independent route difference with a consistent direction in ≥2/3 | Attribute to transition route, not predecessor/order |
| 10 | `ENDPOINT_EXPLAINED` | negative | P1 fails, but the C1/C2 whole-trial trajectories differ and the difference is confined to the final block (bins 8–11) in ≥2/3 | Attribute to endpoint/last-state, not order |
| 11 | `NO_HISTORY_EFFECT` | negative | E pass; P1 sign not replicated, or `SEPARATED_200`/`FOCAL_200` fail in ≥2/3, and no row-8–10 pattern applies | Negative result, reported without reframing |

**Attribution classes** (rows 8–10) are assigned only when the stated
set-based pattern is unambiguous; otherwise the outcome is
`NO_HISTORY_EFFECT` with all values reported. No numeric threshold is invented
for these attributions.

### 10.4 Negative-result rule

If C1/C2 do not separate, or the effect does not replicate, or the reference
does not separate, the correct output is `NO_HISTORY_EFFECT` (or the relevant
inconclusive class). It is reported with the same detail as a positive: all
per-seed values, per-bin and per-neuron tables, the reference values, the
active counts, the outside fraction and the total current. It must not be
reframed as "the network uses a temporal code", "the encoder is sufficient" or
"a trend". The original negative-result rule (design lines 318–319 and 365)
governs.

---

## 11. Execution validity E1–E16 (E11 withdrawn)

| ID | Criterion |
|---|---|
| E1 | All core, control and reference runs complete without numerical, capacity or validation failure. |
| E2 | Stimulated set and per-step current. For every run with a lane schedule, `stimulated_indices` has exactly 12 entries (the `player_lane` population); all neurons outside that set receive 0 pA sensory current; `simulator.stimulus is None`; background = 0; noise = 0. The number of neurons receiving nonzero sensory current at a step depends on the mode: 4 for `K_L`, `K_C`, `K_R` and every step-mode schedule; 4 or 8 during a crossfade (4 at `α = 0` and at/after the end of the 50 ms window, 8 for `0 < α < 1`); 0 for `N0`, which has no input schedule. Total injected sensory current is 800 pA at every step where a schedule is active (E3). |
| E3 | Total injected sensory current is 800 pA at every step within `1e-9` pA, for holds and for crossfades. |
| E4 | Constant-lane runs activate exactly the intended group; a silent group is recorded, not hidden. |
| E5 | `N0` has `input_schedule=None`, `stimulus=None`, 0 background, 0 noise and 0 spikes. |
| E6 | Lane group order is asserted left, center, right against lane codes 0, 1, 2; the assertion fails loudly if the config order changes. |
| E7 | Lane groups are disjoint, four neurons each, inside their annotation pools; per-seed indices and root IDs are recorded. |
| E8 | C2 = reverse(C1) and C4 = reverse(C3) on the 50 ms grid; the sequence hashes differ and the state multiset is identical. |
| E9 | Prefix identity: C3 and C4 produce identical spike trains for 0–150 ms. Any difference is a runner/simulator failure. |
| E10 | Determinism. For the determinism subset — the step-mode runs of `C1`, `C2`, `C3` and `C4`, plus `N0` and `K_C` — each parent run is repeated once in a fresh subprocess. The parent and its repeat must produce identical input-schedule signatures and identical spike hashes; `N0` records an empty schedule signature. This is 6 conditions × 3 seeds = 18 repeat instances. With 126 main runs and 42 pilot runs, the planned total is 186 run instances. The repeat is a determinism check, not an independent replicate, and the two runs are not two samples. |
| E11 | **Withdrawn by the approved protocol amendment (2026-11-14).** The crossfade is causal and one-sided; the C4 input-current vector is not required to equal the C3 vector at `600 − t`. Frame-sequence reversal is checked by E8, total current by E3, and the local crossfade formula by §14.4. |
| E12 | The existing test suite passes unchanged; no simulator, encoder, mapping or scheduler semantics are modified. |
| E13 | All source/config/connectome/protected hashes and the git block are recorded in a sidecar; `git status` before and after shows no unintended change. |
| E14 | Outside activity is reported separately; if nonzero, the report states that the readout includes recurrent input and does not claim a direct-drive-only result. |
| E15 | The analysis bins are half-open and cover exactly `[0, 600)` ms; the `[600, 600.5)` tail is excluded from binning and reported. |
| E16 | Causal decomposition: C1 and `L→C` (200/400) produce identical spike trains for `t < 400 ms`; C2 and `R→C` likewise. Any difference is a runner/simulator failure. |

The applicable gates E1–E10 and E12–E16 are execution validity, not scientific
success. E11 is withdrawn (§3.5, §5.7). A valid run can yield a negative
result.

---

## 12. Exclusion rules

- A run with a numerical, capacity or validation failure is invalid; it is
  reported and not imputed.
- A run with nonzero background/noise, an active Phase 2 stimulus, or more than
  12 neurons receiving nonzero sensory current is invalid.
- A run whose C3/C4 prefix (0–150 ms) differs is invalid (E9).
- A run whose causal decomposition (E16) fails is invalid.
- A run where the total current differs from 800 pA is invalid.
- A run where the mapping is not disjoint, the group order is not
  left/center/right, or a group is outside its pool is invalid.
- A seed where the CENTER group is silent is not excluded; it is classified
  `INCONCLUSIVE_SILENT_C` and the other seeds are reported.
- Runs are never excluded because their outcome is inconvenient. No seed is
  dropped for a negative or inconsistent result.
- Pilot seed 20261107 is excluded from the main result by construction.

---

## 13. Reporting requirements

### 13.1 Per-run record (JSON)

For every run, record:

- `condition_id`, `sequence` (the canonical lane list), `mode`
  (`step`/`crossfade`/`none`), `seed`, `timestamp_ms` list;
- SHA-256 of the canonical sequence list and the scheduler `signature()`;
- the 12 stimulated indices and their root IDs, grouped by lane;
- per-neuron spike times and counts per absolute bin and per state-relative
  bin;
- per-lane group counts and rates per bin;
- active-neuron counts per group per bin;
- outside spikes and active outside neurons;
- total injected sensory current minimum and maximum per step, and the 800 pA
  assertion result;
- capacity, recorded spike count, wall time and environment;
- the gate results for the applicable gates E1–E10 and E12–E16 (E11
  withdrawn);

### 13.2 Per-seed analysis record (JSON)

- P1, P2, `Δ_L`, `Δ_R`, per-bin `δ_s` and per-neuron `Δ_C(i)`;
- `K_C` values and the two auxiliary contrasts;
- R200 pred-LEFT (`R L C`), pred-RIGHT (`L R C`) and none values;
- R150 pred-LEFT (5), pred-RIGHT (2) and none values;
- `SEPARATED_200`, `SEPARATED_150`, `FOCAL_200`, `FOCAL_150`, dwell
  consistency;
- the outcome class and the ordered assignment trace;
- single-transition route values and the stationarity check.

### 13.3 Report (Markdown)

The report must contain:

1. The outcome class and a one-paragraph plain statement of what it does and
   does not mean.
2. A table of every per-seed value for P1, P2, the references and `K_C`, plus
   the range across seeds. No SD, no standard error, no CI.
3. Per-bin and per-neuron tables for the primary contrast.
4. The reference values and the separation predicates, with the small-set
   caveat.
5. Active counts, outside fraction and total-current audit.
6. The gate results and any invalid or failed attempts.
7. The limitations in §15.
8. An explicit statement that no p-value, significance claim, biological
   claim, learning claim, code claim or generalisation is made.

### 13.4 Wording prohibitions

The report must not use "significant", "p <", "confidence interval", "robust",
"confirmed", "validated code", "the network perceives", "the network learns" or
"generalises". A 2-of-3 pattern is written as "2 of 3 mapping realisations".
A descriptive effect is written as "under the configured model".

---

## 14. Reproducibility, artifacts and tests

### 14.1 Frozen configuration

A future implementation adds one new file, proposed as
`configs/p3_3c5_lane_encoding.yaml`, containing:

- protocol: `duration_ms: 600.5`, `frame_interval_ms: 50.0`, `dt_ms: 0.5`,
  `current_pa: 200.0`, `transition_ms: 0` and `50`, zero background/noise,
  `stimulus: none`, spike capacity 5,000,000;
- the C1–C4, constant, no-input, linear, closed and single-transition
  sequences as explicit `(timestamp_ms, GameState)` lists, not code;
- seeds 20261104/5/6 and pilot 20261107;
- analysis parameters: state-relative windows, bins, reference sets, seed rule.

The file does not exist yet. This document does not create it.

### 14.2 Artifacts

- `experiments/phase_3c/results/p3_3c5_lane_encoding.json`: per-run,
  per-condition, per-seed, per-bin counts; active indices and root IDs;
  current audit; outside activity; per-bin and per-neuron `Δ_C`; reference
  values; outcome class.
- `experiments/phase_3c/results/p3_3c5_lane_encoding.sidecar.json`: hashes,
  git block, environment, protected hashes.
- `experiments/phase_3c/results/p3_3c5_lane_encoding_report.md`: report with
  the decision, all per-seed values and limitations.

Existing Phase 3 results are never overwritten. A rerun gets a new versioned
name and a supersession note.

### 14.3 Hashes recorded per run

- SHA-256 of the configuration file.
- SHA-256 of the canonical JSON sequence list.
- The scheduler's `signature()` for the input schedule.
- SHA-256 of the encoder, mapping, scheduler, simulator, neuron and synapse
  source files used.
- SHA-256 of `datasets/processed/connectome.npz`.
- SHA-256 of protected files (`README.md`, connectome).
- The git commit and a `git status` block.
- The environment (Python, NumPy, OS) and the simulator seed.

### 14.4 Determinism and regression tests

- The sequence builder produces the exact 12-frame timelines and hashes.
- C2 = reverse(C1) and C4 = reverse(C3) on the 50 ms grid.
- Lane-only masking yields exactly 12 stimulated neurons and 800 pA.
- `stimulus=None`, background 0, noise 0 are asserted.
- `N0` has no schedule and 0 spikes.
- Group order is left, center, right and fails if the config order changes.
- A crossfade at `α = 0.5` puts 100 pA on eight neurons.
- C3 and C4 produce identical prefix spikes for 0–150 ms.
- C1 ≡ `L→C` and C2 ≡ `R→C` for `t < 400 ms`.
- Parent and subprocess spike/schedule hashes match.
- The existing test suite passes unchanged.

No test may be weakened to obtain a favourable result. The neuron model,
synapse model and global simulation parameters are not changed to obtain a
favourable result.

### 14.5 Pre-registration sequence

1. Approve this frozen protocol and the freeze record (done: 2026-11-14).
2. Implement the runner/config/tests in a separate authorised task; verify the
   applicable gates E1–E10 and E12–E16 on a smoke run. E11 is withdrawn.
3. Run the pilot on seed 20261107; verify runtime, capacity, reference
   non-degeneracy and metric computability. Do not use pilot data in the main
   result.
4. Confirm the frozen protocol hash and the implementation hashes.
5. Run the main matrix on seeds 20261104/5/6.
6. Analyse and report, including negative results and limitations.

No main-run execution may occur before steps 1–4.

---

## 15. Limitations and interpretation boundaries

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
5. **The `visual_any` pool-matched control is not run.** D9 excludes it, so the
   pool asymmetry is not experimentally addressed. It is reported, not
   corrected.
6. **P1 absolute time and `K_C`.** C1/C2 are matched in absolute time; `K_C`
   (CENTER from rest) is matched in time since onset but not in absolute time.
   The transition-onset attribution is therefore caveated.
7. **R200 is a one-versus-one reference.** It cannot support a range-based or
   distributional interpretation; it is a weak descriptive cross-check.
8. **P2 is not perfectly matched.** C3/C4 CENTER blocks occur at 150 and 300 ms
   after different prefix lengths. P2 is a dwell replication, not the cleanest
   primary.
9. **P3 is route-confounded.** The final LEFT block is preceded by `R→L` in C3
   and `C→L` in C4. A difference is a history effect that includes the last
   transition route.
10. **C3/C4 are not perfectly matched.** Transition-type order and per-time
    lane differ; they are the order manipulation itself and cannot be matched
    by any 4-block design over three lanes.
11. **No causal separation of direct and recurrent input.** There is no
    synapse-block control in the current interface. Outside activity is
    measured, not subtracted; a large outside fraction makes the result a
    network-regime observation.
12. **Lane-only is not the natural regime.** The full 14-feature input ignites
    the network (99.976% outside spikes in P3-T2 C3). The lane-only result does
    not generalise to the full sensory context.
13. **No adaptation or short-term plasticity.** Any history effect comes from
    synaptic filtering (5/8 ms), spike reset/refractory nonlinearity and
    recurrent dynamics. The model cannot show a persistent sequence memory.
14. **T5 lane pulses are not implemented.** The experiment cannot test an
    event-pulse hypothesis; T2/T3 are out of scope.
15. **Structural data are not physiological.** The connectome is measured
    structure; synapses are a computational approximation; weights are assumed,
    not measured. Pool annotations are predicted, not verified pathways.
16. **The 0.5 ms tail is not analysed.** Bins cover `[0, 600)` ms; the final
    0.5 ms is reported separately.
17. **The reference set cannot substitute for more sequences.** A larger
    matched reference requires a different block design or more mapping seeds;
    neither is part of this freeze.
18. **Determinism is not robustness.** Identical repeat hashes show the runner
    is deterministic, not that the result generalises.
19. **The causal decomposition is not independent evidence.** C1/C2 and the
    single-transition pair are the same computation for `t < 400 ms` by
    construction; E16 checks correctness, not a new result.
20. **Summary statistics.** With `n = 3`, a standard deviation or standard
    error is not reported; the exact values and their range are reported.
21. **The crossfade is causal, not time-symmetric.** The 50 ms blend ramps only
    after a change, never before it, so the scheduler is not time-reversal
    equivariant. The C3/C4 crossfade input-current vectors are not expected to
    be time reverses of each other, and the crossfade C3/C4 contrast includes
    the ramp asymmetry. It is descriptive, not a matched reversal.
22. **Reversing the stimulus does not reverse the current waveform.** E8
    establishes that C2 = reverse(C1) and C4 = reverse(C3) on the 50 ms frame
    grid. It does not establish that the injected current vector at time `t`
    equals the mirrored current vector at `600 − t`; under the causal scheduler
    the two differ, so stimulus-sequence reversal does not establish
    current-waveform reversal.
23. **Half-open frame boundaries add endpoint mismatches.** Even in step mode,
    a right-continuous piecewise-constant schedule is not exactly
    time-reversal symmetric at the three transition instants. The reversal
    claim is a statement about the 50 ms frame sequence, not about continuous
    time; no continuous-time reversal is claimed.
24. **C3/C4 remain secondary route/order comparisons.** C3 and C4 are matched
    on duration, grid, dwell, occupancy, endpoints and transition count, but
    not on transition-type order or per-time lane. Their comparison is
    secondary and descriptive, and no claim of perfect matching is made.

---

## 16. Claims not made

- 3C.5 has not been run, completed or accepted.
- Phase 3C is not complete.
- The network does not perceive lanes, select actions or perform a task.
- The visual annotation pools are not an anatomically verified lane pathway.
- Four neurons are not claimed superior to twelve; the lane bank is fixed at
  12.
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
- No p-value, significance claim or confidence interval is made.
- No claim is made that the C3/C4 crossfade input-current vectors are time
  reverses or that the crossfade block is a matched reversal control.
- No claim of perfect matching between C3 and C4 is made.

---

## 17. Authorisation status and residual underspecification

### 17.1 Approved and recorded

- [x] D1 — C1–C4, C1/C2 primary.
- [x] D2 — closed C3/C4 extension.
- [x] D3 — step primary; crossfade robustness for C1–C4 plus four additional
      closed sequences (8 distinct).
- [x] D4 — main seeds 20261104/5/6; pilot 20261107 excluded.
- [x] D5 — `player_lane` only.
- [x] D6 — mandatory controls; 20-frame-shuffle reference dropped.
- [x] D7 — no p-values, significance claims or 95th-percentile threshold.
- [x] D8 — pilot seed and exclusion.
- [x] D9 — `visual_any` pool-matched mapping excluded.
- [x] Primary metric M6′.
- [x] Outcome classes and the 2-of-3 descriptive rule.
- [x] Negative-result policy.
- [x] Artifact names and no-overwrite rule.

### 17.2 Not authorised

- [ ] **D10 — implementation.** No configuration, runner, test or analysis code
      may be written under this document. It requires a separate task.
- [ ] **Execution.** No main run may occur without a separate execution
      authorisation after the implementation and the frozen hash are verified.
- [ ] **Protocol amendment.** Any change to this document requires a recorded
      amendment and a new SHA-256 before a main run.

### 17.3 Residual underspecification

No scientific design decision remains unresolved after the approved decisions.
The remaining items are not missing values:

- The exact per-seed neuron indices and root IDs are **outputs** of the seeded
  mapping, not design values; they are recorded per run.
- The implementation file layout, JSON field names and code structure are
  operational and must conform to §13 and §14; they do not change the protocol.
- The `K_C` absolute-time mismatch, the small R200 reference, the C3/C4
  transition-type-order difference and the pool asymmetry are **stated
  limitations**, not unresolved choices.
- The `visual_any` control and the 20-frame-shuffle reference are **excluded by
  decision**, not deferred.

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

Single-transition controls (12 frames each; the post-lane holds from the
transition to 600.5 ms):

| Route | 200/400 pre frames | 200/400 post frames | 150/450 pre frames | 150/450 post frames |
|---|---|---|---|---|
| L→C | 4 | 8 | 3 | 9 |
| R→C | 4 | 8 | 3 | 9 |
| L→R | 4 | 8 | 3 | 9 |
| C→R | 4 | 8 | 3 | 9 |
| R→L | 4 | 8 | 3 | 9 |
| C→L | 4 | 8 | 3 | 9 |

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
| Lane pools left/center/right | `configs/sensory_config.yaml` 147–159; `sensory/sensory_mapping.py` 83–97 |
| Active-feature masking / 12 indices | `sensory/input_scheduler.py` 126–131 |
| Crossfade formula | `sensory/input_scheduler.py` 162–174 |
| `GameState` fields and lane enum | `sensory/game_state.py` 25–28, 83–100, 182–213, 249–263 |
| LIF parameters | `configs/neuron_config.yaml` |
| Zero background/noise; Phase 2 stimulus default | `configs/simulation_config.yaml` |
| Spike capacity 5,000,000 | `configs/sensory_config.yaml` line 19 |
| Simulator step count and stimulus handling | `brain/brain_simulator.py` `run` |
| No lane-change pulse | `perception/temporal.py` 50–72; `sensory/temporal_scheduler.py` 238–257 |
| P3-T2 C1 player block | `experiments/phase_3c/results/p3_t2_full.json` |
| P3-T3 ablation | `experiments/phase_3c/results/p3_t3_ablation.json` |
| P3-T4.1 counts and d′ | `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json` |
| T7 no-input and d′ = 0.0 | `experiments/phase_3c/results/temporal_acceptance.json` |
| Connectome and README hashes | `README.md` `8ab6a8cc…90563`; connectome `3f568f24…5f33d8` |
