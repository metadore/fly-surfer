# Phase 3C Remaining Experiments — Design and Dependency Audit

**Date:** 2026-11-14
**Scope:** 3C.5 (lane ordering), 3C.6 (jump/roll onset/offset intervals),
3C.8 (T1 vs T2 vs T3 encoding ablation)
**Status of this document:** audit only. No experiment was executed, no
simulation was run, no existing file was modified, and nothing was staged,
committed or pushed.
**Repository HEAD at audit time:** `62a64309cadc0db7353c856607cee5369993bd65`
(branch `main`)

---

## 0. Method, vocabulary and governing constraint

### 0.1 What was inspected

- The original Phase 3C design,
  `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md`.
- The Phase 3 roadmap, `docs/PHASE_3_ROADMAP.md`.
- The sensory encoding document,
  `docs/PHASE_3_SENSORY_ENCODING.md`.
- The Phase 3A.5 calibration design,
  `docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md`.
- Phase 3C configuration and runners under `configs/` and
  `experiments/phase_3c/`.
- The temporal encoder and scheduler, `perception/temporal.py`,
  `sensory/temporal_scheduler.py`, `sensory/input_scheduler.py`.
- The population encoders and mapping, `sensory/population_encoder.py`,
  `sensory/sensory_mapping.py`, `sensory/sensory_experiment.py`.
- The Phase 3B replay path, `experiments/phase_3b/real_sequence_replay.py`,
  and the Phase 3C causal-control replay,
  `experiments/phase_3c/causal_control.py`.
- P3-T2, P3-T3, P3-T4, P3-T4.1, P3-T7 and P3-T12 artifacts and sidecars.
- Existing tests: `tests/test_temporal.py`,
  `tests/test_temporal_scheduler.py`,
  `tests/test_temporal_acceptance.py`,
  `tests/test_p3_t4_1_four_neuron_validation.py`.
- The Phase 3 final audit,
  `experiments/phase_3c/results/p3_final_phase3_audit.md`.

No experiment was executed. The only code execution performed for this audit
was read-only inspection and one read-only measurement of annotation-pool
sizes by loading the frozen connectome.

### 0.2 Vocabulary

| Term | Meaning in this report |
|---|---|
| **Specified** | Stated in an original project document. |
| **Implemented** | Code exists in the repository. |
| **Tested** | A unit/integration test exercises the code. |
| **Executed** | A runner has been run and an artifact exists. |
| **Accepted** | The project's own acceptance criteria are satisfied. |
| **Proposed** | Written by this audit, not an original requirement. |

"Implemented" does not mean "experimentally validated". "Executed" does not
mean "accepted". "Model output" does not mean "biological measurement".

### 0.3 Governing constraint on definitions

There is no pre-existing Phase 3C specification. The roadmap states that the
3C definition is proposed because no prior 3C specification exists
(`docs/PHASE_3_ROADMAP.md` §4.4, lines 246–248), and the design document
explicitly says it does not claim the project previously defined Phase 3C
(`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §13, line 441).

Consequently, the "original definition" of 3C.5, 3C.6 and 3C.8 is exactly what
the design document and roadmap say — no more. This audit does **not**
reconstruct missing details from task numbers, from the condition counts, or
from what would be convenient to implement.

---

## 1. Original definitions of 3C.5, 3C.6 and 3C.8

### 1.1 3C.5 — lane ordering

**Original row** (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.1, line 245):

> `3C.5 | Lane sequence left→center→right and reversed | Order sensitivity of
> lane changes | 4`

**Original supporting definitions:**

- **Lane change** is defined as "Player lane differing between consecutive
  frames" (§4.1, line 91). The table marks it "Available".
- **Sequences** are "defined as `(timestamp_ms, GameState)` lists in
  configuration or a validated JSON file, not hard-coded in the runner"
  (§6.2, line 265–266).
- **Reversed sequences** "reverse the time order and timestamps, not the
  object contents, so frame statistics are preserved while order is
  destroyed" (§6.2, lines 267–268).
- **Shuffled sequences** "permute frames but keep timestamps; this tests
  whether a response is driven by temporal order or by the marginal
  distribution" (§6.2, lines 269–270).
- **Fresh state** is required for every condition: "Every condition
  constructs a fresh encoder, scheduler and simulator" (§6.2, line 272).
- **Metrics** include population-vector cosine similarity between conditions
  and "Order sensitivity: similarity of forward vs reversed sequences"
  (§6.3, lines 292 and 298), in addition to windowed spikes, latency, peak
  time, response duration, non-stimulated spike share, runtime, memory and
  deterministic hashes.
- **Decision-rule relevance:** criterion 5 says reversed or shuffled
  sequences must produce a measurable difference, or the absence must be
  reported as a negative result (§6.4, lines 318–319).
- **Acceptance relevance:** criterion 8 says a negative result must be
  reported without reframing it as success (§8, line 365). There is no
  separate lane-ordering acceptance criterion.

**What the original text does not define:**

- Which lane feature is meant: `player_lane` or `obstacle_lane`. The lane
  change definition names the player lane, but the table row does not.
- The four conditions. "Left→center→right and reversed" suggests two, not
  four; the other two are not enumerated.
- The dwell time in each lane, the total duration, the frame interval, or the
  transition/crossfade duration.
- A hypothesis about what order sensitivity should look like.
- A primary metric among the several listed in §6.3.
- Any numeric threshold for "measurable difference".
- Whether 3C.5 is single-seed (the seed-repeat sentence names only 3C.2 and
  3C.7; §6.1, lines 251–252).

**Original rationale (as written, not inferred):** lane is categorical and
the project can observe lane changes; the experiment asks whether the order
of lane changes, not only the momentary lane, is represented. The design does
not state a directional hypothesis or a predicted outcome.

### 1.2 3C.6 — jump and roll onset/offset intervals

**Original row** (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.1, line 246):

> `3C.6 | Jump and roll onset/offset intervals | Transient response to
> discrete events | 6`

**Original supporting definitions:**

- **Jump / roll interval** is defined as "Boolean onset, duration in ms,
  offset" (§4.1, line 93). The table marks it "Available".
- **Persistence and deactivation:** "A feature that leaves view must produce
  an explicit decay or OFF event; silence must not be indistinguishable from
  'object still present' by accident" (§5.5, lines 214–216). "The zero state
  must be defined" and "State carried across runs is forbidden; each run
  constructs a fresh encoder" (§5.5, lines 217–219).
- **Metrics** include spikes and active neurons in fixed windows aligned to
  events, first-spike latency (median, IQR, p95), peak population rate and
  time, response duration and time to return to baseline after offset
  (§6.3, lines 287–296).
- **Acceptance relevance:** criterion 4 requires "Onset, offset and
  persistence are represented explicitly, and latency and decay are
  measured" (§8, lines 357–358).
- **Protocol:** all experiments use synthetic timestamped sequences with
  known ground truth, the frozen connectome, zero background and noise, and
  the Phase 3A.5 amplitude/tuning settings (§6, lines 221–226).

**What the original text does not define:**

- The six conditions. A natural reading is jump and roll × three intervals,
  but the design does not enumerate them. This audit does not adopt that
  reading as a definition.
- The onset times, interval durations and offsets.
- Whether "transient response" means the LIF step response (onset latency and
  offset cessation), the partial T5 event-pulse layer, or T3 ON/OFF phasic
  channels. T3 is separately a 3C.8 object.
- Whether the experiment may use only synthetic `GameState` sequences or must
  also use perceived scenes. The general protocol says synthetic, but 3C.6's
  use of player body state makes the perceived path relevant.
- A numeric transient-magnitude or decay-time threshold.
- Whether 3C.6 is single-seed (the seed-repeat sentence names only 3C.2 and
  3C.7).

**Original rationale (as written, not inferred):** jump and roll are discrete
body-state events with a Boolean onset, a duration and an offset, so the
experiment asks whether the model responds transiently to discrete events and
returns to baseline. The design does not state whether a transient is
expected to be phasic or merely a step response.

### 1.3 3C.8 — T1 vs T2 vs T3 encoding ablation

**Original row** (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.1, line 248):

> `3C.8 | Encoding ablation: T1 vs T2 vs T3 on the same sequences | Whether
> temporal encoding changes separability | 9`

**Original definitions of the three encodings** (§5.1, lines 136–142):

| ID | Representation | How it maps onto current code | Extra mapping neurons |
|---|---|---|---|
| T1 | Step + linear crossfade | Existing `SensoryInputScheduler(transition_ms=...)` | None |
| T2 | First-order smoothing of activations | Exponential low-pass on encoded activations with time constant `tau_enc` | None |
| T3 | Onset / offset (phasic) channels | Rising and falling activation changes drive separate ON and OFF sub-populations | Yes, doubles affected features |

The design adds that T1 is the Phase 3A behaviour and remains the control, and
that T2 and T3 are the proposed first implementation because they add
temporal sensitivity without requiring a new representation of the scene
(§5.1, lines 144–147).

**Original supporting definitions:**

- **Delivery:** T2/T3 are to use an activation scheduler with the same
  `apply(step, time_ms, current_pa)` signature, built from precomputed
  per-feature activation trajectories and the existing `SensoryMapping`
  indices; it contains no neuron, synapse or time-step logic and only adds
  currents to the provided array (§5.3, lines 182–187).
- **Equivalence:** "with `tau_enc → 0` and no phasic channels, T2 reproduces
  T1 exactly (same input hash) on a fixed sequence" (§5.3, lines 197–198).
- **Metrics:** activation trajectory min/max/mean/total change, distinct
  activation levels, ON/OFF transient magnitude (T3), decay time constant,
  sampling interval and irregularity; neural metrics including separability
  `d'` and nearest-centroid classification with leave-one-seed-out
  evaluation; operational metrics including deterministic input and spike
  hashes (§6.3, lines 278–305).
- **Decision rule:** the 3C milestone decision rule (§6.4, lines 307–323)
  names approach-vs-retreat separation and frame-rate quantification. It does
  not name T1/T2/T3 ablations, lane ordering or jump/roll intervals.
- **Acceptance relevance:** criteria 1 and 2 require a causal, deterministic
  temporal encoder with explicit timestamps and a static-equivalence test
  (§8, lines 349–354). There is no separate encoding-ablation criterion.

**What the original text does not define:**

- "The same sequences": which sequences. The design does not say whether
  these are 3C.5/3C.6 sequences, 3C.2 approach/retreat, or a new set.
- The nine conditions. Three encodings × three sequences is a plausible
  reading, but the design does not enumerate it. This audit does not adopt
  that reading as a definition.
- The T2 time constant, its units beyond milliseconds, its grid, or how it is
  selected.
- The T3 onset/offset definition: edge threshold, sign convention, gain,
  decay, whether ON and OFF are symmetric, and whether both are stimulated at
  200 pA.
- How the mapping is extended for T3, how many neurons are added, and how
  capacity is checked.
- The primary separability contrast and label set ("separability" of what).
- A numeric threshold for "changes separability".
- Whether T3 must also satisfy a `zero phasic gain → T1` equivalence test.
- Whether 3C.8 is single-seed; the seed-repeat sentence names only 3C.2 and
  3C.7.
- Whether T5 event pulses may be combined with any encoding.

### 1.4 Original execution status and seed plan

The design's execution-status sentence is explicit:

> "Execution status (2026-11-13): none of the 3C.1–3C.9 conditions has been
> run." (§6.1, lines 258–261)

That sentence is now stale for 3C.1–3C.4, 3C.7 and 3C.9, which were executed
by P3-T7 on 2026-11-14. It remains correct for 3C.5, 3C.6 and 3C.8, which the
T7 configuration marks as not executed (`configs/temporal_sensory.yaml`,
lines 62–69).

The original seed plan repeats only 3C.2 and 3C.7 for three mapping seeds and
adds about 15 runs (§6.1, lines 251–252). 3C.5, 3C.6 and 3C.8 are therefore
single-seed in the original proposal. This audit records that as the original
plan and flags the consequence in §6.7; it does not silently change it.

---

## 2. Source references

### 2.1 Documents

| Source | Working-tree SHA-256 | Sections used |
|---|---|---|
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` | §4.1, §5.1, §5.3–§5.5, §6.1–§6.4, §8, §12, §13 |
| `docs/PHASE_3_ROADMAP.md` | `ab6d3e66f1c84946c44a94c9d6519f4d04a4419a0fdd82d046d035bee00c29e5` | §4.4 (lines 244–327) |
| `docs/PHASE_3_SENSORY_ENCODING.md` | `d1d9f659b4c2012c33f47175691dacee37e110079bfef1de5811f106cabae8d2` | Feature schema; Lane; Boolean; Configured populations; Operating-point mismatch; Input scheduler |
| `docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md` | `cf0ed979ee53dc623232f4e416029481c0b57e53e9fb9aab1fb70e967072c08d` | Analysis and decision rule; Outputs |
| `experiments/phase_3c/results/p3_final_phase3_audit.md` | `f813ed60…` (recorded in the artifact) | P3-T7; Phase 3 status; unmet criteria |

### 2.2 Configuration and code

| Source | Working-tree SHA-256 | Relevance |
|---|---|---|
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` | Frozen T7 matrix; lines 62–69 mark 3C.5/6/8 not executed |
| `configs/sensory_config.yaml` | `26d782a3b5910c05d433fa6678557f7c806dc9947ee8ad279e246fa34f4e96db` | 14 features, 138 neurons, lane/boolean populations, mapping pools |
| `sensory/input_scheduler.py` | `223bce3738ac02f6f8de736209158df7aafa639cf1f05d9791f559a500e5cc07` | T1 crossfade implementation |
| `sensory/temporal_scheduler.py` | `3be4ac9a7f04749cfcacdb62c47c254114e601579fd94b6ebc0f66ac3020641c` | Sample-and-hold + event pulses; no T2/T3 |
| `perception/temporal.py` | `ed4b3de1f1c92edb81237b76d4b764aaceb876c74c83826dbfb1764531f91421` | Lifecycle enum; `build_state`; player defaults |
| `sensory/population_encoder.py` | `9b4594255935ef950ac639f24580dc85e174f54b95cc913addc2103b8b582134` | Lane, Boolean and Gaussian encoders |
| `sensory/sensory_mapping.py` | `c655c14a7831a968d56c0e5dc7f5dc85e4d6170118e6439caaa0999d3755aaa8` | Seeded disjoint allocation and capacity check |
| `sensory/sensory_experiment.py` | `…` (inspected at HEAD working tree) | Feature families; static jump/roll/lane conditions; distance-only sequence builder |
| `experiments/phase_3c/temporal_acceptance.py` | `41f4b09effbed172502bcd06c8abc32f879b2a0168ced20bf0ec09838adc0543` | T7 runner; obstacle-distance-only state builder |
| `experiments/phase_3b/real_sequence_replay.py` | `…` (inspected at HEAD working tree) | v15 schema has no player, jump or roll observability |
| `experiments/phase_3c/causal_control.py` | `…` (inspected at HEAD working tree) | Cached 14-feature inversion; jump/roll come from replay defaults |

### 2.3 Result artifacts

| Artifact | Key content used |
|---|---|
| `experiments/phase_3c/results/temporal_acceptance.json` | Verdict `NEGATIVE_RESULT`; criterion 3 fails; 3C.5/6/8 not executed |
| `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json` | Verdict `PASS` (execution); P4/P12/P12S results; 72 runs |
| `experiments/phase_3c/results/p3_t3_ablation.json` | Verdict `VALID`; 15 conditions; jump/roll ablation deltas 0 |
| `experiments/phase_3c/results/p3_t2_full.json` | C3 full replay: 15,654,631 spikes, 99.976% non-stimulated |
| `experiments/phase_3c/results/p3_t12_network_characterization.json` | Ignition characterization |
| `experiments/phase_3c/results/p3_final_phase3_audit.md` | 3C not accepted; 3C.5/6/8 unrun |

---

## 3. Current implementation status

### 3.1 Status matrix

| Capability | Status | Evidence |
|---|---|---|
| Lane encoder (`LanePopulation`, one group per lane) | Implemented and tested | `sensory/population_encoder.py`; Phase 3A tests |
| Boolean encoder (`BooleanPopulation`) | Implemented and tested | `sensory/population_encoder.py`; Phase 3A tests |
| Seeded disjoint mapping with capacity check | Implemented and tested | `sensory/sensory_mapping.py:208+`, `_choose` |
| T1 step + linear crossfade | Implemented and tested | `sensory/input_scheduler.py`; Phase 3A |
| Sample-and-hold temporal scheduler | Implemented and tested | `sensory/temporal_scheduler.py`; 13 tests |
| T5-style lifecycle pulses (appeared/approaching/receding only) | Partially implemented | `perception/temporal.py:70`; `sensory/temporal_scheduler.py` |
| Lane-change lifecycle event | Not implemented | `Lifecycle` enum has no lane event (`perception/temporal.py:50–58`) |
| Jump/roll lifecycle event | Not implemented | `Lifecycle` enum has no jump/roll event |
| T2 exponential activation smoothing | Not implemented | `TemporalSchedulerConfig` has no `tau_enc` |
| T3 ON/OFF sub-populations | Not implemented | No phasic channels; no mapping extension |
| Sequence builder for lane timelines | Not implemented | `sensory/sensory_experiment.py` sequence builder handles obstacle/coin distance only |
| Sequence builder for jump/roll intervals | Not implemented | Only static `jumping`/`rolling` single-feature conditions exist |
| Generic 3C sequence runner | Not implemented | T7 runner is obstacle-distance-specific |
| T1/T2/T3 ablation runner | Not implemented | No runner; no nine-condition matrix |
| Per-lane time-resolved metrics | Not implemented | T7 masks the distance population only |
| Outside-spike accounting in 3C runners | Implemented in T2/T3/T4.1; not in T7 | T7 reports network/distance profiles, not outside spikes |
| Formal result schema | Not present | Per-runner ad hoc JSON plus sidecars |
| Tests for lane sequences, jump/roll sequences, T2, T3 | Not present | Four relevant test files exist, none cover these |

### 3.2 3C.5 — what exists and what is missing

**Exists:**

- `player_lane` and `obstacle_lane` are lane features with 12 neurons each
  (3 lanes × 4 neurons), using disjoint visual left/center/right pools
  (`configs/sensory_config.yaml`).
- `SensoryInputScheduler` can inject lane activations through the T1 path,
  including a linear crossfade (`transition_ms`).
- `SensoryMapping` allocates lane groups deterministically from a seed and
  fails loudly if a pool is too small.
- The Phase 3A builder can create a static obstacle-in-lane condition
  (`single_obstacle_lane_*`), but not a timed lane sequence.
- The T7 metrics infrastructure provides a pattern for windowed spike
  profiles, cosine distance and deterministic hashes.

**Missing:**

- A decision on whether the lane sequence is `player_lane` or
  `obstacle_lane`; the two are not equivalent. `player_lane` has no presence
  feature and changes one-hot group; `obstacle_lane` requires an obstacle and
  co-varies with `obstacle_present`, `obstacle_distance` and
  `obstacle_type` unless those are masked.
- The four-condition enumeration, dwell times, timestamps, frame interval,
  duration and crossfade duration.
- A sequence builder that emits a lane timeline with an explicit
  `active_features` set that includes the lane feature for the whole run.
- A runner that records per-lane time-resolved activity, not only aggregate
  totals.
- A defined order-sensitivity metric and decision rule. The design lists
  "similarity of forward vs reversed sequences" but no threshold and no
  primary metric.
- Tests for lane timeline construction, feature masking, per-lane metric
  behaviour and determinism.

**Status: PARTIAL.** The encoder, mapping and T1 scheduler exist; the
experiment does not.

### 3.3 3C.6 — what exists and what is missing

**Exists:**

- `jumping` and `rolling` are Boolean features with 6 neurons each, mapped
  disjointly from the mechanosensory pool (`configs/sensory_config.yaml`).
- `GameState` validates that `jumping` and `rolling` cannot both be true
  (`sensory/game_state.py:89–97`), so the two events are mutually exclusive.
- The Phase 3A builder can create static `jumping=True/False` and
  `rolling=True/False` conditions.
- T1 can inject Boolean activations.
- The T7 runner demonstrates windowed onset/offset metrics for a different
  feature.

**Missing:**

- The six-condition enumeration, onset times, durations and offsets.
- A definition of "transient": LIF onset/offset response, T5 pulse, or T3
  phasic channel. The current scheduler emits pulses only for
  appeared/approaching/receding; jump and roll produce no pulse.
- A sequence builder for Boolean intervals. `_active_for_payload` includes
  `jumping`/`rolling` only if the initial state is true
  (`sensory/sensory_experiment.py:156–171`); a jump interval must set
  `active_features` explicitly for the whole run.
- A runner and tests.
- For the perceived-scene path: jump and roll are not observable. The v15
  dataset has no player class and the replay states explicitly that jumping
  and rolling are "not observable; no action or jump state is inferred"
  (`experiments/phase_3b/real_sequence_replay.py:122–123, 882–883`).
  `build_state` constructs `PlayerState()` with defaults, so jumping and
  rolling are false (`perception/temporal.py:834+`). There is no jump/roll
  lifecycle event. The C3 full replay's jump/roll ablations changed 0 spikes
  for this reason (`p3_t3_ablation.json`).

**Status: PARTIAL for synthetic `GameState` sequences. BLOCKED for perceived
scenes.**

### 3.4 3C.8 — what exists and what is missing

**Exists:**

- T1 step + linear crossfade is implemented in `SensoryInputScheduler`.
- T1 is the Phase 3A control and is tested.
- The mapping allocates features deterministically and checks capacity.
- The 3C design specifies the T2/T3 interface and the T2 equivalence test.
- The T7 runner provides a pattern for deterministic multi-condition runs.

**Missing:**

- T2: no exponential low-pass on encoded activations, no `tau_enc`, no
  activation-trajectory scheduler that filters rather than re-encodes states.
- T3: no ON/OFF edge detection, no phasic sub-populations, no mapping
  extension, no gain/decay parameters, no capacity check for the doubled
  features.
- The T2 equivalence test (`tau_enc → 0` reproduces T1 exactly, same input
  hash) does not exist because T2 does not exist.
- A T3 equivalent of the zero-filter equivalence test is not specified in the
  design and does not exist.
- The nine-condition matrix and the "same sequences" set.
- A primary separability contrast and metric.
- A current/neuron budget policy for comparing T1, T2 and T3.
- A runner, result schema and tests.

**Status: BLOCKED.** The experiment cannot be executed without new
implementation, and the implementation cannot be specified without design
decisions that the original documents do not contain.

### 3.5 A documentation inconsistency that affects the audit

Two project documents are stale in ways that matter:

1. `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6.1 says none of 3C.1–3C.9 has
   been run, and §11 says the 3C.1–3C.9 suite and
   `configs/temporal_sensory.yaml` were not delivered. Both statements are
   contradicted by the T7 run and by the existing configuration.
2. The Phase 3 final audit says "the design's T1 crossfade and T2 smoothing
   variants are not implemented"
   (`p3_final_phase3_audit.md:207–208, 314–316`). This is correct for the 3C
   sample-and-hold scheduler, but the T1 crossfade **does** exist in
   `SensoryInputScheduler` and is the Phase 3A control. The correct statement
   is: T1 exists, but no 3C runner exercises it; T2 and T3 do not exist.

This audit does not modify those documents. Any correction is a separate
documentation task requiring approval.

---

## 4. Accounting for P3-T4.1

P3-T4.1 compared the calibrated four-neuron `obstacle_distance` population
(P4), the shipped twelve-neuron population (P12), and a twelve-neuron encoder
bank restricted to the four P4 cells (P12S), over 72 runs (3 populations × 3
mapping seeds × 8 conditions), plus three determinism replays. Its execution
verdict is PASS; that verdict covers execution and validity, not a scientific
claim of superiority.

The findings that matter for 3C.5, 3C.6 and 3C.8 are:

1. **P4 reproduces static distance ordering in 3/3 seeds.** Stimulated spike
   counts were 5 / 12 / 14 at distances 0.15 / 0.55 / 0.90 in every seed.
2. **P12 has an identity code despite unordered totals.** Totals were
   51 / 47 / 47, not ordered. But the active cells were disjoint by level:
   approximately cells 1–4 at 0.15, cells 6–9 at 0.55, and cells 10–12 at
   0.90. A population total can therefore hide a cell-identity code. This is
   directly relevant to 3C.5, where aggregate totals may be order-invariant
   even when per-lane identity differs.
3. **P12S isolates the encoder bank.** With the four P4 cells but the
   twelve-neuron encoder bank, counts were 51 / 0 / 0. The P4 ordering is
   therefore a property of the encoder bank and threshold geometry, not of
   "four neurons" as such.
4. **None of the three populations distinguishes approach from retreat.**
   Stimulated d′ was 0.1183 (P4), 0.0 (P12) and −0.184828 (P12S); all are
   below the pre-registered 1.0 threshold. No separation was claimed.
5. **No recurrent activity outside the stimulated population.** Across all
   72 runs, the maximum `n_spikes_outside` was 0. This is a sparse,
   feed-forward-like regime for the single distance feature.

**What this accounting does not license:**

- It does not make P4 superior. P4's ordering is a threshold-sensitive
  small-population effect, and P12 carries a different, disjoint-cell code.
- It does not supply a temporal result. It used static and ramp
  `obstacle_distance` sequences under T1, not T1/T2/T3 encodings.
- It does not show approach/retreat coding. The d′ values are descriptive and
  do not separate.
- It must not be repeated as a new 3C.5/3C.6/3C.8 experiment. The audit uses
  it only to predict confounds and to justify per-lane/identity metrics.

For 3C.8 specifically, P4/P12/P12S must not be reused as the T1/T2/T3
ablation. They compare population size and encoder-bank alignment, not
temporal encoding schemes.

---

## 5. Missing dependencies

### 5.1 3C.5

| Dependency | State | Consequence |
|---|---|---|
| Decision: `player_lane` or `obstacle_lane` | Missing | Changes the active feature set and whether presence/distance co-vary |
| Four-condition enumeration | Missing | Cannot preregister |
| Exact timestamps, dwell, frame interval, duration, crossfade | Missing | Cannot match forward/reversed timing |
| Lane sequence builder | Missing | No runner input |
| Explicit `active_features` including the lane feature | Missing | A false/absent lane may be masked to zero |
| Per-lane time-resolved metric | Missing | Aggregate totals are not identifiable (see §6.1) |
| Order-sensitivity threshold or descriptive rule | Missing | Cannot make a binary call without inventing one |
| Runner and tests | Missing | No artifact |

### 5.2 3C.6

| Dependency | State | Consequence |
|---|---|---|
| Six-condition enumeration | Missing | Cannot preregister |
| Exact onset/duration/offset | Missing | Cannot align windows |
| Definition of "transient" | Missing | LIF step, T5 pulse and T3 phasic are different experiments |
| Boolean interval sequence builder | Missing | Static conditions only |
| Explicit `active_features` for the whole run | Missing | Jump/roll may be masked at onset |
| Runner and tests | Missing | No artifact |
| Perceived-scene jump/roll observability | Blocked | v15 has no player/jump/roll; `build_state` defaults false |
| Jump/roll lifecycle event | Missing | No event-pulse path |
| T3 phasic channels (if required) | Missing | Depends on 3C.8 |

### 5.3 3C.8

| Dependency | State | Consequence |
|---|---|---|
| T2 exponential smoothing | Missing | No T2 condition |
| `tau_enc` specification | Missing | No preregistered filter |
| Activation-trajectory scheduler | Missing | Re-encoding interpolated states is not T2 (design §5.3) |
| T3 ON/OFF sub-populations | Missing | No T3 condition |
| T3 edge/gain/decay specification | Missing | Cannot implement or preregister |
| Mapping extension for T3 | Missing | Doubles affected features; capacity must be checked |
| T2 equivalence test | Missing | Acceptance criterion 2 not extendable to T2 |
| T3 zero-gain equivalence test | Missing and unspecified | No control for added channels |
| "Same sequences" set | Missing | Depends on 3C.5/3C.6 |
| Nine-condition matrix | Missing | No runner input |
| Primary separability contrast | Missing | "Separability" is ambiguous |
| Current/neuron budget policy | Missing | T3 changes the input budget |
| Runner, schema and tests | Missing | No artifact |

### 5.4 Shared dependencies

- **Frozen inputs:** sparse full connectome, frozen artifact
  `datasets/processed/connectome.npz`, zero background, zero noise, 200 pA,
  `sigma_fraction` 0.20, 0.5 ms timestep, declared frame interval.
- **Reproducibility:** input and spike hashes across a parent and two
  subprocesses; deterministic scheduler signature; sidecar with SHA-256
  hashes and a git block.
- **Outside-spike accounting:** every run must report stimulated and
  non-stimulated spikes, because the full 14-feature replay ignited
  (15,654,631 spikes, 99.976% non-stimulated; `p3_t2_full.json`).
- **Result schema:** no formal schema exists. New runners should either
  declare a versioned schema or follow the existing ad hoc JSON + sidecar
  convention consistently.

**Pool capacity (measured read-only for this audit):**

| Pool | Available neurons |
|---|---:|
| `visual_left` | 5,892 |
| `visual_center` | 76 |
| `visual_right` | 5,458 |
| `visual_any` | 11,426 |
| `mechanosensory` | 2,674 |

T3 doubling of a 12-neuron lane population or a 6-neuron Boolean population
fits in principle. But `visual_center` is small (76), and T3 must still be
capacity-checked at the chosen seed with the existing disjoint-allocation
rule. Capacity is necessary, not sufficient: the P12S result shows that
changing the encoder bank changes the ordering.

---

## 6. Scientific risks, confounds and identifiability

### 6.1 3C.5 — order sensitivity

**Primary risk: the proposed comparison may not be identifiable from
aggregate activity.**

The lane encoding is one-hot with 4 neurons per lane, all lanes use the same
200 pA amplitude, and the neuron and synapse models have no adaptation or
short-term plasticity. A forward sequence L→C→R and its reverse R→C→L contain
the same multiset of lane activations. If the readout is total spikes or a
time-aggregated population vector, the two can be identical or nearly so even
when the temporal order is different. The P12 result is a warning: equal
totals (47/47) coexisted with a disjoint cell-identity code.

**Confounds:**

1. **Feature choice.** `player_lane` vs `obstacle_lane`. If obstacle lane is
   used and the full obstacle family is active, presence, distance and type
   co-vary with lane. The lane effect is then not isolated.
2. **Timing.** Reversal changes which lane is first and last, not only the
   order of the middle. Any difference may be an onset/offset effect. A
   palindrome or a matched-dwell design is needed to separate order from
   endpoint identity.
3. **Transition duration.** `transition_ms=50` and a 50 ms frame interval
   mean the crossfade occupies one full frame; lane activations overlap. A
   different dwell changes the overlap. The design does not fix this.
4. **Mapping asymmetry.** `visual_center` has 76 neurons vs 5,892 left and
   5,458 right. Disjoint seeded allocation can give center neurons different
   thresholds or partners, so center-vs-side differences may be mapping
   effects. Per-lane mapping indices must be reported.
5. **No adaptation.** Without adaptation, repeated lane visits do not produce
   history-dependent fatigue. Any "order" effect is likely a timing or
   recurrent-network effect, not a within-channel adaptation effect.
6. **Recurrent activity.** At 12 lane neurons the network is likely sparse,
   but any outside spikes must be reported; if they dominate, the comparison
   is not a direct sensory response.

**Identifiability verdict:** a time-resolved, per-lane metric (spike counts,
first-spike latency, and per-lane population vectors in windows aligned to
each lane transition) can identify order sensitivity. Aggregate totals alone
cannot. This must be preregistered before execution.

**Suitable controls:**

- no input;
- constant lane (L→L→L) at the same duration;
- forward and reversed sequences with matched dwell and endpoints;
- shuffled lane frames with timestamps preserved;
- same transition count but different order (e.g. L→C→R→C vs L→R→C→R);
- per-lane mapping and per-lane active-neuron report;
- 3 mapping seeds if the user approves a seed extension; otherwise state that
  the result is one mapping realization.

### 6.2 3C.6 — jump/roll intervals

**Primary risk: "transient" may be a trivial step response.**

The LIF membrane has `tau_m = 20 ms`, a 150 pA rheobase and no adaptation.
A 200 pA Boolean step will drive sustained firing for the whole true
interval; the observable transients are onset latency and offset cessation.
There is no phasic channel and no jump/roll event pulse. If the experiment
reports a "transient response" without separating the sustained level, it may
be describing the first-order membrane response, not event encoding.

**Confounds:**

1. **Step vs pulse vs phasic.** T1 gives a step; T5 gives pulses for other
   events; T3 gives ON/OFF channels. These are different mechanisms. The
   design does not choose.
2. **No event layer for jump/roll.** `Lifecycle` has no jump/roll event, and
   `PULSE_EVENTS` contains only appeared/approaching/receding. A jump or roll
   will not produce an event pulse even with the temporal scheduler.
3. **Mutual exclusivity.** `GameState` forbids simultaneous jumping and
   rolling, so the six conditions cannot include an interaction.
4. **Masking.** `_active_for_payload` includes a Boolean feature only if the
   initial state is true. A jump interval that starts false will be masked
   unless `active_features` is set explicitly.
5. **Frame quantization.** A 50 ms frame grid cannot represent an onset or
   offset between frames. The design requires explicit timestamps and forbids
   silent resampling; the experiment must either put events on the grid or
   report the quantization.
6. **Perceived path is unidentifiable.** The v15 replay has no player, jump
   or roll observations; `build_state` defaults them false. A perceived-scene
   3C.6 would compare two identical zero channels.
7. **Seed plan.** A single mapping seed gives one realization of the
   mechanosensory allocation. The original design is single-seed for 3C.6;
   this is a known limitation, not a reason to add seeds silently.

**Identifiability verdict:** onset and offset are identifiable from synthetic
timestamps if the channel is active and the metric is windowed. "Transient
magnitude" is identifiable only relative to the sustained level. Without T3,
a nonzero onset response is not evidence of phasic encoding.

**Suitable controls:**

- no input;
- constant false and constant true at the same duration;
- onset-only and offset-only schedules;
- reversed interval (offset before onset is not physically meaningful, but
  reversing the whole sequence tests time-order sensitivity);
- jump vs roll at matched duration;
- frame-grid-aligned vs off-grid onset, to quantify quantization;
- outside-spike accounting.

### 6.3 3C.8 — encoding ablation

**Primary risk: this is not a single-factor ablation.**

T1, T2 and T3 differ in:

- scheduler class (crossfade vs activation filter vs phasic channels);
- filter state (none vs exponential vs edge detector);
- neuron count (T3 doubles affected features);
- total injected current (unless explicitly normalized);
- mapping (T3 needs new neurons);
- input-side activation trajectory.

A difference in separability therefore cannot be attributed to "temporal
encoding" alone. The P12S result is a direct warning: changing the encoder
bank changed the ordering from 51/47/47 to 51/0/0.

**Confounds:**

1. **Input budget.** If each T3 ON/OFF neuron receives 200 pA, total current
   doubles. If it is split, per-neuron current halves. Either choice changes
   the comparison. A matched-budget control is required, or the input-side
   difference must be reported and no superiority claim made.
2. **Neuron count.** More neurons can increase the number of active cells and
   the probability of recurrent recruitment. Report both.
3. **T2 tau.** The design does not fix `tau_enc`. A post-hoc tau would make
   the result exploratory. Pre-register a primary tau and, if desired, a
   descriptive grid.
4. **T3 specification.** Edge threshold, sign, gain, decay and symmetry are
   unspecified. Without them, T3 is not reproducible.
5. **Sequence set.** "Same sequences" is undefined. Using 3C.5/3C.6 sequences
   is a reasonable proposal, but it is not an original requirement.
6. **Separability label.** Approach vs retreat, forward vs reversed, lane
   order, and frame rate are all mentioned in §6.3. The ablation's primary
   contrast is not specified.
7. **Ignition.** The full 14-feature C3 replay ignited (99.976%
   non-stimulated). T3 adds neurons and could increase ignition. A
   separability difference dominated by recurrent spikes is not a sensory
   encoding result.
8. **Seeds.** The original 3C.8 plan is single-seed. The deterministic
   simulator means one mapping realization; a single seed cannot estimate
   mapping spread.
9. **T2 delivery.** The design warns that timeline expansion is not exact T2;
   smoothing must operate on activations, not interpolated GameStates
   (§5.3, lines 177–181).

**Identifiability verdict:** a difference in a preregistered separability
metric between T1, T2 and T3 is identifiable as a model-level descriptive
difference **only if** the input-side trajectories, neuron counts, current
budget and outside spikes are reported. It is not identifiable as "temporal
encoding is better" or as a biological claim. A null result is equally
informative and must be preserved.

**Suitable controls:**

- T1 baseline on the same sequences, mapping seed, duration and frame
  interval;
- T2 `tau_enc → 0` equivalence to T1 (same input hash);
- T3 zero-phasic-gain equivalence to T1, if T3 is implemented;
- matched total current and/or matched neuron count;
- no input;
- outside-spike accounting and an ignition flag;
- forward/reversed and shuffled controls for each encoding;
- 3 mapping seeds if approved; otherwise a documented single-seed limitation.

### 6.4 Cross-cutting safeguards

- **Direct vs recurrent:** every run must report stimulated and
  non-stimulated spikes. A result with a large outside share is a network
  result, not a direct sensory response.
- **Thresholds:** the original documents do not give numeric thresholds for
  these three experiments. The only existing numbers are T7's pre-registered
  `d' = 1.0` and cosine distance `0.01`, both of which the T7 artifact labels
  as new operationalizations. Reusing them for 3C.5/6/8 is a **new**
  operationalization and must be labelled as such, or the result must be
  reported descriptively. This audit does not invent a threshold.
- **Negative results:** a null, reversed, or unmeasurable outcome is a
  reportable result. No condition may be dropped after seeing results.
- **Model vs biology:** spikes are model output under assumed LIF, synapse
  and mapping parameters. No recognition, biological coding, routing or
  action claim follows.
- **No action:** none of these experiments selects an action.

---

## 7. Proposed preregistration requirements

These are audit proposals, not original requirements. They should be approved
before any implementation or execution.

### 7.1 Shared block (all three experiments)

1. **Exact sequences.** A list of `(timestamp_ms, GameState)` entries with
   all 14 feature values, or a validated JSON file. No hard-coded sequences
   in the runner.
2. **Active features.** The exact `active_features` set, including features
   that are false for part of the run. State which features are masked and
   why.
3. **Timing.** Duration, frame interval, timestep, transition duration (T1),
   `tau_enc` (T2), T3 gain/decay (T3), and whether events are on the frame
   grid.
4. **Stimulation.** 200 pA per active neuron, `sigma_fraction` 0.20, zero
   background, zero noise, initial potential −65 mV, frozen connectome.
5. **Mapping.** Seed(s), exact population sizes, pool names, and the resolved
   stimulated indices or a hash of them.
6. **Controls.** The specific controls from §6, not a generic "controls"
   label.
7. **Metrics.** Primary and secondary metrics, window boundaries, bin width,
   cosine/d′/nearest-centroid definitions, and whether d′ is signed or
   directionless.
8. **Decision rule.** A no-failure gate, a reproducibility gate, and either
   (a) a descriptive report with no binary threshold, or (b) an explicitly
   new, labelled threshold. Do not import a threshold silently.
9. **Seed plan.** State whether the run is single-seed (original plan) or a
   three-seed extension. If extended, say why and how many conditions are
   added.
10. **Exclusions and deviations.** No condition may be removed after results.
    Failed attempts must be preserved with `_attemptN_*` names and a sidecar.
11. **Artifacts.** Versioned JSON, Markdown report, sidecar with SHA-256
    hashes, git HEAD, environment and protected-file hashes.
12. **Negative-result policy.** State in advance that a null or reversed
    result will be reported as such, without reframing.

### 7.2 3C.5-specific

- State `player_lane` or `obstacle_lane`. If `obstacle_lane`, mask
  `obstacle_distance`, `obstacle_type` and `obstacle_present` unless they are
  part of the question.
- Define the four conditions explicitly, with matched dwell and endpoints.
- Pre-register a per-lane, time-resolved primary metric. Aggregate totals
  alone are insufficient.
- Pre-register the forward/reversed and shuffled comparisons.
- Report per-lane mapping indices and per-lane active neurons.

### 7.3 3C.6-specific

- State whether the experiment is synthetic-only. If perceived scenes are
  intended, the experiment is blocked; do not substitute defaulted false
  values for observations.
- Define "transient" as LIF step response, T5 pulse, or T3 phasic. If T3,
  defer to 3C.8.
- Define the six conditions explicitly, with onset, duration and offset.
- Set `active_features` explicitly for the whole interval.
- Report sustained rate during the interval, not only onset/offset
  transients.
- Report frame-grid quantization if any event is off-grid.

### 7.4 3C.8-specific

- State the sequence set. If it reuses 3C.5/3C.6 sequences, cite their
  preregistration hashes.
- Define the nine conditions explicitly.
- Define T2 `tau_enc` and the equivalence test at `tau_enc → 0`.
- Define T3 edge threshold, sign, gain, decay, symmetry, mapping extension
  and capacity check.
- Define a T3 zero-gain equivalence test, or state why it is not required.
- Define the primary separability contrast and metric.
- Define the current/neuron budget policy. Report input-side activation
  differences.
- Report outside spikes and flag ignition.
- Do not reuse P4/P12/P12S as the ablation.

---

## 8. Recommended execution order

### 8.1 Order

1. **3C.5 — lane ordering.**
2. **3C.6 — jump/roll intervals.**
3. **3C.8 — T1/T2/T3 encoding ablation.**

3C.5 and 3C.6 may be run in parallel **after** both are preregistered and the
shared sequence/control/metric infrastructure exists. Sequential execution is
recommended for the first pass because it reuses the same runner and metrics
and keeps the artifact chain easy to audit.

### 8.2 Justification

- **3C.5 first.** It needs no new encoder or mapping. It exercises the
  smallest feature set and forces the project to define the per-lane,
  time-resolved order metric. That metric is also needed to interpret any
  later T1/T2/T3 difference.
- **3C.6 second.** It shares the T1 path and the windowed-metric
  infrastructure. It is the experiment most likely to reveal that "transient"
  has no implemented mechanism beyond the LIF step. That finding should shape
  whether T3 is required for 3C.8, rather than discovering it after T2/T3
  implementation.
- **3C.8 last.** It is the only one that requires new code (T2, T3, mapping
  extension, equivalence tests). It also depends on the "same sequences"
  chosen for 3C.5/3C.6, and it needs their T1 baselines. Starting it first
  would mean implementing temporal encodings before knowing which sequences
  and which transient/order metrics they must be compared on.
- **Risk containment.** If 3C.5 or 3C.6 produces a clear negative result, that
  is a valid stopping point for the T2/T3 implementation decision. The design
  says T4 is a later option if T2/T3 fail to separate sequences; the same
  logic applies here.

### 8.3 What execution must not be used for

Completing 3C.5/6/8 will **not** make Phase 3C accepted. The T7 result fails
decision-rule criterion 3 (approach vs retreat d′ = 0.0; 460/460 spikes), and
the T7 configuration explicitly says 3C.5/6/8 "characterize the encoder rather
than the milestone decision rule" (`configs/temporal_sensory.yaml:62–69`).
The negative direction result stands. 3C.5/6/8 can be reported as encoder
characterization, not as a rescue of the 3C acceptance sentence.

---

## 9. Readiness verdicts

| Experiment | Verdict | Reason |
|---|---|---|
| **3C.5** | **NEEDS DESIGN CLARIFICATION** | The lane feature, four conditions, timing, primary metric and threshold are unspecified. The T1 path, lane encoder and mapping exist, so this is not blocked on code. |
| **3C.6** | **NEEDS DESIGN CLARIFICATION** (synthetic path); **BLOCKED** for a perceived-scene version | The six conditions, transient definition and timing are unspecified. Synthetic Boolean intervals are implementable with existing encoders and T1. Perceived jump/roll are unobservable and have no lifecycle events. |
| **3C.8** | **BLOCKED** (also needs design clarification) | T2 and T3 do not exist; the mapping extension, equivalence tests, `tau_enc`, T3 specification, sequence set and separability contrast are undefined. |
| **Overall Phase 3C** | **NOT ACCEPTED** | T7 criterion 3 fails; 3C.5/6/8 are unexecuted; the 3C acceptance sentence is not satisfied. |

No experiment is READY in the sense of "preregistered and executable now."
The distinction matters:

- 3C.5 is **not blocked by code**; it is blocked by missing experimental
  definitions.
- 3C.6 is **not blocked for synthetic input**; it is blocked by missing
  definitions and, for perceived input, by missing observability.
- 3C.8 is **blocked by code and definitions**; it is the only one that
  requires a new temporal encoding implementation.

---

## 10. Repository and protected-file integrity

### 10.1 Git state at audit time

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `62a64309cadc0db7353c856607cee5369993bd65` |
| Staged changes | 0 files |
| Status entries | 211 (21 modified tracked, 190 untracked) |
| Pre-existing modified tracked files | 21, observed at the start and unchanged by this audit |
| New files created by this audit | 1 (this report) |

The 21 modified tracked files are pre-existing working-tree modifications,
including `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md`,
`docs/PHASE_3_ROADMAP.md`, `perception/temporal.py` and several Phase 3B/3C
reports. This audit did not edit any of them.

### 10.2 Protected hashes

| File | SHA-256 |
|---|---|
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |

Both match the hashes recorded by P3-T4.1 and P3-T7. The connectome was read
only for the pool-size measurement; it was not modified.

### 10.3 What this audit did not do

- Did not execute a simulation or an experiment.
- Did not modify an existing file.
- Did not modify the root README, the connectome, the neuron model, the
  synapse model, the mapping, the scheduler or any Phase 4–6 artifact.
- Did not stage, commit or push.
- Did not use `git add .`, `git add -A`, `git reset`, `git clean`,
  `git stash` or `git checkout`.
- Did not delete or overwrite any result artifact.

### 10.4 Post-write verification

After this report is written, re-running `git status --porcelain` must show
exactly one additional untracked file,
`docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md`, and no new staged or
modified tracked file. The report's own SHA-256 is recorded in the delivery
message, not inside the report, to avoid a self-referential hash.

---

## 11. Claims this audit does not make

- It does not claim 3C.5, 3C.6 or 3C.8 has been executed.
- It does not claim Phase 3C is accepted.
- It does not claim T2 or T3 exists.
- It does not claim the T1 crossfade is exercised by any 3C runner.
- It does not claim P4 is superior to P12 or P12S.
- It does not claim the P3-T4.1 findings are a temporal or sensory-coding
  result.
- It does not claim lane order, jump/roll transients or encoding differences
  are represented in the model.
- It does not claim any biological, recognition, routing or action result.
- It does not invent thresholds or condition enumerations that the original
  documents do not contain.

---

## 12. Decisions required before implementation

1. For 3C.5: is the lane sequence `player_lane` or `obstacle_lane`?
2. For 3C.5: what are the four conditions, and what are the dwell, duration,
   frame interval and crossfade?
3. For 3C.5: what is the primary order-sensitivity metric, and is a numeric
   threshold approved or is the result descriptive?
4. For 3C.6: is the experiment synthetic-only, or must it use perceived
   scenes? If perceived, it is blocked.
5. For 3C.6: does "transient" mean LIF step response, T5 pulse, or T3 phasic?
6. For 3C.6: what are the six conditions and the exact intervals?
7. For 3C.8: which sequences are "the same sequences"?
8. For 3C.8: what is the nine-condition matrix?
9. For 3C.8: what is `tau_enc`, and is a tau grid required?
10. For 3C.8: what is the full T3 specification (edge threshold, sign, gain,
    decay, mapping extension)?
11. For 3C.8: what is the primary separability contrast and metric?
12. For all three: is the original single-seed plan retained, or is a
    three-seed mapping extension approved?
13. For all three: are the T7 thresholds (`d' = 1.0`, cosine `0.01`) approved
    as new operationalizations, or is the result descriptive only?

Until these are answered, the correct state is: **3C.5 and 3C.6 need design
clarification; 3C.8 is blocked; Phase 3C remains not accepted.**
