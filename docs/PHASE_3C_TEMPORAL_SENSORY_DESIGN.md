# Phase 3C — integrated temporal sensory processing (proposed design)

Status: **proposed design, definition proposed by this document. Not
implemented.** No prior Phase 3C specification exists in this repository, in
`docs/PROJECT_VISION.md`, in the root README, or in the external reference
repositories. The name, scope and acceptance criteria below are therefore a
proposal for review, not an established project definition.

## 1. Definition status

The repository was searched before writing this document:

| Source | Finding |
|---|---|
| Root `README.md` | Describes Phases 0–2.5 and names sensory encoding and a motor interface as future work; no 3A/3B/3C split and no temporal milestone |
| `docs/PROJECT_VISION.md` | Broad development phases 0–9; its "Phase 3" is a sensory system, not this 3A/3B/3C decomposition |
| `docs/PHASE_3_SENSORY_ENCODING.md` | Phase 3A only; static `GameState` segments and a linear crossfade |
| `docs/PHASE_3A5_SENSORY_CALIBRATION_DESIGN.md` | Calibration only; explicitly defers the temporal study to 3C |
| `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md` | Per-frame perception; `track_id` is reserved "used only in Phase 3C" |
| External references | No temporal-processing stage, benchmark or definition to adopt |

Consequently, "Phase 3C — integrated temporal sensory processing" is a
**proposed** label. If the project later adopts a different definition, this
document must be revised rather than reinterpreted.

## 2. Why temporal processing is a separate milestone

Phase 3A encodes one `GameState` at a time and the scheduler blends between
consecutive states. Phase 3A.5 calibrates static operating points. Phase 3B
produces one scene per frame. None of them specifies how a *sequence* of scenes
becomes a sensory drive, or whether the neural response distinguishes temporal
structure at all.

The timescales make this a real question rather than a formatting detail:

- membrane time constant 20 ms, synaptic decay 5 ms (excitatory) and 8 ms
  (inhibitory), uniform delay 1 ms, timestep 0.5 ms;
- a 20 FPS capture interval is 50 ms, i.e. 2.5 membrane time constants;
- Phase 3A used 300 ms conditions, and its only temporal control was a linear
  crossfade of encoded activations.

If frames arrive every 50 ms and the membrane filters over 20 ms, the network
sees a sequence of quasi-static drives plus transients, not a continuous
signal. Whether that is adequate, and how frame rate changes the response, is
exactly what 3C must measure. It must not be assumed.

## 3. Scope and non-goals

**In scope**

- A causal, deterministic temporal encoder that consumes timestamped
  `GameState` sequences (from synthetic scripts or from Phase 3B output) and
  produces sensory drive through the existing Phase 3A mapping and scheduler
  interfaces.
- Explicit representation of temporal events: onset, offset, persistence,
  entry/exit, lane change, speed change, jump/roll intervals.
- Controlled experiments on synthetic sequences with known ground truth.
- Offline replay of Phase 3B sequences once 3B exists.
- Measured frame-rate sensitivity, latency, separability, seed variability,
  runtime and memory.
- A documented decision on whether temporal structure is distinguishable in
  this model.

**Out of scope**

- Motor decoding, action selection, reward, plasticity or learning.
- Improving perception or adding detectors; that is Phase 3B.
- Live capture, browser automation or real-time game control.
- Changing the connectome artifact, neuron indexing or synapse model.
- Adding dense connectivity or a second neural simulator.
- FlyVis or any external visual model.
- Closed-loop feedback from spikes to sensory input.
- Claiming biological temporal coding from model output.

## 4. Temporal information (F1)

### 4.1 What a sequence adds

A sequence can express quantities that a single snapshot cannot. Each must be
defined from recorded fields, not inferred from wall-clock timing.

| Quantity | Definition from available data | Status |
|---|---|---|
| Object position | Per-frame lane and normalised distance from `GameState` | Available in 3A |
| Approach / retreat | Sign of distance change between consecutive frames; magnitude is `Δdistance` per frame | Available, **ordinal** |
| Entry / exit | Presence changing `False → True` or `True → False` | Available |
| Lane change | Player lane differing between consecutive frames | Available |
| Speed change | Player speed differing between frames | Available, normalised units |
| Jump / roll interval | Boolean onset, duration in ms, offset | Available |
| Object type at closest approach | Obstacle type in the frame with minimum distance | Available |
| Multiple simultaneous objects | Requires more than one obstacle/train/coin per frame | **Not representable** in `GameState` |
| Relative timing of two objects | Requires the multi-object schema above | **Not representable** yet |
| Time to contact | `distance / max(speed, ε)` as a dimensionless approach index | **Proposed proxy**, not seconds |
| Physical velocity / metres | Requires calibrated camera model and known object geometry | **Unavailable** |

### 4.2 Unit and interpretation rules

- `Δdistance` per frame is **not** velocity. Dividing by frame interval gives
  normalised units per second at best, and only if the frame interval is known
  and regular.
- The approach index `distance / max(speed, ε)` is a monotone design proxy. It
  is not time-to-contact in seconds and must be labelled as an index in every
  report and figure.
- The game speed field is a normalised 0–1 convention from Phase 3A, not m/s.
- Temporal comparisons are only valid when frame intervals, mapping, seed,
  amplitude and duration are matched.
- Where Phase 3B emits a `track_id`, the temporal layer may use it to keep
  events separate. If the `GameState` adapter has already collapsed two objects
  of the same family into one, the temporal layer cannot recover them; the
  conversion report must state that.

## 5. Temporal encoding (F2)

### 5.1 Candidate representations

All are **proposed**; none is implemented.

| ID | Representation | How it maps onto current code | Extra mapping neurons | Cost |
|---|---|---|---|---|
| T1 | Step + linear crossfade | Existing `SensoryInputScheduler(transition_ms=...)` | None | Already implemented |
| T2 | First-order smoothing of activations | Exponential low-pass on encoded activations with time constant `tau_enc` | None | Small CPU |
| T3 | Onset / offset (phasic) channels | Rising and falling activation changes drive separate ON and OFF sub-populations | Yes, doubles affected features | Medium |
| T4 | Delay line / history taps | Each tap (e.g. 0, 50, 100 ms) drives a distinct sub-population | Yes, × number of taps | Medium–high |
| T5 | Event pulses | Short pulses at presence/lane/jump transitions | Can reuse T3 populations | Small |

T1 is the Phase 3A behaviour and remains the control. T2 and T3 are the
proposed first implementation because they add temporal sensitivity without
requiring a new representation of the scene. T4 is a later option if T2/T3
fail to separate sequences, and it needs a capacity check on the mapping pools.
T5 is only a convenience if T3 populations exist.

### 5.2 Proposed encoder interface

```
TemporalEncoder.step(timestamp_ms, GameState) -> ActivationFrame
ActivationFrame: feature -> per-neuron activation in [0, 1], plus events
```

Proposed module: `sensory/temporal_encoder.py`. It must:

- be causal: output at time `t` may use only frames with timestamp ≤ `t`;
- reject duplicate or decreasing timestamps;
- require explicit timestamps from the data, never `time.time()`;
- keep all activations dimensionless and in `[0, 1]` before the scheduler
  multiplies by pA;
- expose the filter state so runs start from a defined zero state;
- declare the frame interval and flag irregular spacing;
- not import the simulator, OpenCV, screenshots or the game.

### 5.3 Drive delivery without changing the simulator

The existing `SensoryInputScheduler.apply(step, time_ms, current_pa)` is the
integration point. Two delivery options are proposed, in order:

1. **Timeline expansion (T1/T2).** The temporal encoder emits a list of
   `(time_ms, GameState)` segments. T2 cannot be expressed this way exactly,
   because the scheduler re-encodes each state; interpolating game states is not
   the same as filtering activations. Use this only for T1 and for
   approximately sampled versions of T2, and label the approximation.
2. **Activation scheduler (T2/T3).** A new class with the same
   `apply(step, time_ms, current_pa)` signature, built from precomputed
   per-feature activation trajectories and the existing `SensoryMapping`
   indices. It contains **no** neuron, synapse or time-step logic; it only adds
   currents to the provided array. The simulator is unchanged and remains
   unaware of the temporal layer.

Both options must satisfy:

- additive injection, never overwriting background or noise;
- the same `stimulated_indices` contract and deterministic `signature()`;
- an equivalence test: with `tau_enc → 0` and no phasic channels, T2 reproduces
  T1 exactly (same input hash) on a fixed sequence.

No interface change to `BrainSimulator` is permitted in 3C.

### 5.4 Timing consistency and frame rate

- The temporal layer receives timestamps from the sequence, not from the
  simulation loop. A 50 ms frame may be held for 100 simulation steps.
- Irregular intervals must raise or be explicitly flagged; silent resampling is
  forbidden.
- Missing frames are a gap, not a zero-distance frame.
- The nominal capture rate is a declared factor, not a hidden constant.
- Any smoothing time constant is expressed in milliseconds and reported.

### 5.5 Persistence and deactivation

- A feature that leaves view must produce an explicit decay or OFF event;
  silence must not be indistinguishable from "object still present" by
  accident.
- The zero state must be defined: no input is not the same as an all-zero
  activation if a baseline is configured.
- State carried across runs is forbidden; each run constructs a fresh encoder.

## 6. Experimental design (F3)

All experiments use synthetic timestamped sequences with known ground truth,
the frozen connectome artifact, zero background current and zero noise, and the
calibrated operating point from Phase 3A.5. Sequence length is 600 ms unless
stated. The 3A.5 recommendation governs amplitude, tuning and population size.

### 6.1 Conditions

| ID | Comparison | Purpose | Conditions |
|---|---|---|---|
| 3C.1 | Constant sequence vs static schedule | Implementation equivalence of the temporal path; must match T1 when smoothing is zero | 3 |
| 3C.2 | Approach vs retreat with identical start/end distances | Shows whether direction, not just position, is represented | 6 |
| 3C.3 | Entry timing: object appears at 100/200/300 ms | Onset latency and transient magnitude | 6 |
| 3C.4 | Exit timing and persistence: object leaves at 200/400 ms | Offset response, decay, return to baseline | 6 |
| 3C.5 | Lane sequence left→center→right and reversed | Order sensitivity of lane changes | 4 |
| 3C.6 | Jump and roll onset/offset intervals | Transient response to discrete events | 6 |
| 3C.7 | Frame-rate sensitivity: same trajectory at 200/100/50 ms intervals | Aliasing and membrane filtering | 9 |
| 3C.8 | Encoding ablation: T1 vs T2 vs T3 on the same sequences | Whether temporal encoding changes separability | 9 |
| 3C.9 | Controls: no input, shuffled frames, reversed sequence, dropped frame | Guards against artefacts of frame statistics | 8 |

Proposed total: about 57 conditions, with the seed-sensitivity subset
(3C.2 and 3C.7) repeated for three mapping seeds, adding about 15 runs.

A full factorial across every factor is not proposed. Each experiment varies
one factor against a fixed control, and all runs share the same mapping unless
the factor is the mapping seed.

### 6.2 Protocols

- Sequences are defined as `(timestamp_ms, GameState)` lists in configuration
  or a validated JSON file, not hard-coded in the runner.
- Reversed sequences reverse the time order and timestamps, not the object
  contents, so frame statistics are preserved while order is destroyed.
- Shuffled sequences permute frames but keep timestamps; this tests whether a
  response is driven by temporal order or by the marginal distribution.
- Dropped-frame conditions remove one entry without re-timing the others.
- Every condition constructs a fresh encoder, scheduler and simulator.
- Baseline (no schedule) runs are interleaved to separate runtime noise from
  real overhead.

### 6.3 Metrics

**Input side**

- Activation trajectory: per-feature minimum, maximum, mean and total change.
- Number of distinct activation levels per feature.
- ON/OFF transient magnitude (T3) and decay time constant.
- Sampling interval and any irregularity flag.

**Neural**

- Spikes and active neurons in fixed windows aligned to events (e.g. 0–50,
  50–100, 100–200 ms after onset).
- First-spike latency after onset: median, IQR, p95.
- Peak population rate and time of peak.
- Response duration and time to return to baseline after offset.
- Population-vector cosine similarity between conditions.
- Separability `d'` between approach and retreat, and between frame rates,
  using seed-to-seed spread as the noise estimate.
- Nearest-centroid classification of condition label from population vectors,
  with leave-one-seed-out evaluation. This is a descriptive separability
  measure, not learning.
- Order sensitivity: similarity of forward vs reversed sequences.
- Non-stimulated spike share, to show downstream recruitment.

**Operational**

- Wall time, steps/s, scheduler memory, retained arrays, RSS change.
- Deterministic input and spike hashes across a parent and two subprocesses.
- Finite-state and membrane-bound diagnostics.

### 6.4 Analysis and decision rule

The milestone produces a table of temporal conditions, not a single score.
Temporal processing is considered to carry measurable information only if:

1. no numerical, capacity or validation failure occurs;
2. the constant-sequence equivalence (3C.1) holds within the stated tolerance;
3. approach and retreat separate above the seed-to-seed spread in at least two
   of three mapping seeds;
4. at least one frame-rate comparison is quantified, including the case where
   the response does **not** change;
5. reversed or shuffled sequences produce a measurable difference, or the
   absence of one is reported as a negative result.

If criterion 3 fails, the correct conclusion is that this model does not
distinguish direction at the tested operating point. That must be reported as a
negative result; it must not be reframed as "temporal coding".

## 7. Integration boundaries (F4)

| Layer | May consume | May produce | Must not do |
|---|---|---|---|
| Perception (3B) | Screenshots, annotations | `PerceivedScene`, `GameState`, `track_id` | Import the simulator or write currents |
| Temporal encoder (3C, new) | Timestamped `GameState`/`PerceivedScene` | Activation frames and events | Touch neurons, spikes, OpenCV or wall-clock time |
| Activation scheduler (3C, new) | Activation frames, `SensoryMapping` | Current increments via `apply` | Simulate dynamics or overwrite background |
| `SensoryInputScheduler` (3A) | Timeline and encoders | Current increments | Gain temporal filter state |
| `BrainSimulator` (Phase 2) | Current array | Spikes | Know about frames, perception or temporal events |
| Experiments (3C) | All of the above | JSON, plots, report | Hide dropped frames or failed conditions |

Rules:

- The neural simulator remains runnable with no perception, no screenshots and
  no temporal encoder.
- The temporal encoder remains testable with pure Python states and no neural
  simulation.
- Phase 3B and Phase 3A.5 can proceed in parallel with the temporal encoder's
  synthetic-sequence harness; only the final replay needs 3B output.
- No closed loop: spikes never change the sequence mid-run.
- Sequence files and outputs stay local; screenshots are not redistributed.

## 8. Acceptance criteria (F5)

Phase 3C is accepted only when all of the following hold:

1. A causal, deterministic temporal encoder exists with explicit timestamps,
   duplicate/ordering validation and a defined zero state.
2. The static-equivalence test passes: a constant sequence reproduces the
   static Phase 3A schedule exactly when temporal filtering is disabled.
3. Approach and retreat are compared at matched endpoints, with the result
   stated in terms of seed variability rather than a single run.
4. Onset, offset and persistence are represented explicitly, and latency and
   decay are measured.
5. Frame-rate sensitivity is measured at three intervals, including a
   documented aliasing limit.
6. The simulator, `GameState` schema and Phase 3A interfaces are unchanged;
   all existing tests pass.
7. The full graph, sparse propagation and frozen connectome artifact are used;
   no dense matrices, raw CSV reloads or connectome modifications.
8. A negative result, if any, is reported without reframing it as success.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Frame rate aliases the membrane filter | Test 50/100/200 ms intervals; report the limit; do not claim continuity |
| Threshold dominance inherited from 3A hides temporal coding | Use the 3A.5 operating point; report saturation and monotonicity |
| `GameState` cannot express multiple objects | Restrict 3C claims to single-object sequences until the schema extension; log unrepresented objects |
| Temporal filtering creates artificial smoothness | Include T1 control and zero-filter equivalence test |
| Non-additivity confounds comparisons | Match mapping, seed, amplitude and duration; report additivity index |
| Sequence runs are expensive | Keep 600 ms conditions; split by subcommand; run seeds on a subset |
| Reversed/shuffled controls accidentally differ for trivial reasons | Match frame intervals and marginal statistics; report input-side differences |
| Nearest-centroid separability is over-interpreted | Label it descriptive; no learning claim; report seed spread |
| Temporal encoder drifts into a second simulator | Restrict it to activations and current increments; no membrane state |

## 10. Expected computational cost

Using the Phase 3A rate of roughly 2–2.5 s per 300 ms full-graph condition on
the development machine, a 600 ms condition is expected to take about 4–5 s of
simulation plus graph load. About 57 conditions plus roughly 15 seed repeats is
therefore on the order of 5–10 minutes of simulation per full sweep, excluding
reporting and plotting. Longer sequences or additional taps in T4 would scale
linearly. Memory is expected to stay close to the Phase 3A retained footprint
(about 135 MB) plus small activation buffers; this must be measured, not
assumed.

## 11. Deliverables

- This design document.
- A proposed `configs/temporal_sensory.yaml` and sequence-file schema.
- `sensory/temporal_encoder.py`, an activation scheduler if approved, and unit
  tests, if the milestone is implemented.
- `experiments/phase_3c/` runner, condition JSON, plots and a generated report.
- A documented decision on temporal separability, including negative results.
- No changes to the root README, datasets, connectome artifact, Phase 3A
  results or external references.

## 12. Open questions for review

1. Is "integrated temporal sensory processing" the intended definition, or does
   the project mean something narrower (for example, only crossfade timing)?
2. Should T3 (ON/OFF populations) be included in the first implementation, or
   should 3C begin with T1/T2 and add phasic channels only if needed?
3. Is a 600 ms sequence long enough, given 50 ms frames and a 20 ms membrane
   time constant?
4. Should 3C replay real 3B sessions in its acceptance gate, or is synthetic
   sequence validation sufficient with 3B replay reported separately?
5. Is a multi-object `GameState` extension a prerequisite for 3C, or a later
   3B sub-stage?

## 13. Claims this design does not make

- It does not claim that the project previously defined Phase 3C.
- It does not claim that the proposed temporal encoder matches fly sensory
  processing.
- It does not claim that `Δdistance` per frame is velocity or physical motion.
- It does not claim that the approach index is time-to-contact in seconds.
- It does not claim that frame-by-frame replay is equivalent to continuous
  visual input.
- It does not claim that separability in this model is a biological result.
