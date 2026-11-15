# P3-3C.5 — Lane Encoding: Experimental Design Proposal

**Status: DESIGN ONLY.** This document proposes an experiment. It is not a
pre-registration, it has not been executed, and it produces no result. No
configuration, runner, test, result or existing document is changed by it.

**Identifier.** The roadmap and the Phase 3C design enumerate this experiment
as **3C.5**, not as "P3-T3C5". The file therefore uses the roadmap identifier:
`P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md`. The project task label used here is
**P3-3C.5**.

**Relationship to the prior audit.** `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md`
returned the verdict **3C.5 — NEEDS DESIGN CLARIFICATION**. This document
resolves that verdict by supplying the missing experimental definitions. It
does not overturn the audit's finding that 3C.5 is unexecuted.

**Date.** 2026-11-14.

**Labels used throughout.** Every experimental choice carries one of:

- **[ORIGINAL]** — stated in the Phase 3C design, the roadmap, the encoding
  document or the delivered configuration.
- **[SUPPORTED]** — not stated in the 3C.5 row, but expressible with the
  delivered code without changing the simulator, encoder or mapping semantics.
- **[NEW]** — a design decision introduced by this proposal. It is not an
  original requirement and must not be reported as one.

A choice is never presented as original merely because it is convenient.

---

## 1. Source audit

### 1.1 Normative and design documents

| File | SHA-256 (working tree) | Relevant locations |
|---|---|---|
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` | §4.1 line 91 (lane-change definition); §6.1 line 245 (3C.5 row); §6.2 lines 265–272 (sequence, reversal, shuffle, fresh state); §6.3 lines 289–299 (metrics); §6.4 lines 318–319 (criterion 5); §8 line 365 (negative results); §5.1 lines 136–150 (T1–T5, implemented status); §5.3 lines 197–203 (delivery options) |
| `docs/PHASE_3_ROADMAP.md` | `ab6d3e66f1c84946c44a94c9d6519f4d04a4419a0fdd82d046d035bee00c29e5` | §4.4 lines 265–269 (3C.1–3C.9 coverage), lines 271–274 (metrics), lines 276–281 (acceptance), lines 322–327 (not executed) |
| `docs/PHASE_3_SENSORY_ENCODING.md` | `d1d9f659b4c2012c33f47175691dacee37e110079bfef1de5811f106cabae8d2` | lines 82–83 (feature families), lines 123–125 (lane geometry/default), lines 155–160 (lane encoder), lines 195–211 (populations/pools), lines 213–221 (4-vs-12 operating point), lines 223–238 (scheduler, crossfade, active-feature masking) |
| `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md` | `b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7` | Prior audit; verdict 3C.5 NEEDS DESIGN CLARIFICATION |

The Phase 3C design's own status sentence at lines 258–261 ("none of the
3C.1–3C.9 conditions has been run") is stale: the P3-T7 suite subsequently ran
3C.1, 3C.2, 3C.3, 3C.4, 3C.7 and 3C.9 and explicitly left 3C.5, 3C.6 and 3C.8
unexecuted (`configs/temporal_sensory.yaml`, lines 62–69;
`experiments/phase_3c/results/p3_final_phase3_audit.md`). This proposal uses the
current artifact status, not the stale sentence.

### 1.2 Configuration and implementation

| File | SHA-256 | Relevant locations |
|---|---|---|
| `configs/sensory_config.yaml` | `26d782a3b5910c05d433fa6678557f7c806dc9947ee8ad279e246fa34f4e96db` | lines 15–23 (`dt_ms` 0.5, `duration_ms` 300, `transition_ms` 50, seed 20261104, 200 pA); lines 29–35 (`player_lane`: 3 lanes, 4 neurons/lane, amplitude 1.0, baseline 0.0, 200 pA); lines 138–159 (pools; lane pools left→`visual_left`, center→`visual_center`, right→`visual_right`) |
| `configs/neuron_config.yaml` | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` | `tau_m` 20 ms, rheobase 150 pA, threshold −50 mV, reset −68 mV, refractory 2 ms; no adaptation |
| `configs/simulation_config.yaml` | `be0571b9d6ede75b752a79fce3d8136960034f78f2a961fa3c447e31b7d769e3` | zero background/noise; excitatory/inhibitory synaptic time constants 5/8 ms; weight transform; 1 ms delay |
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` | lines 62–69: 3C.5/6/8 marked not executed; note says they "characterize the encoder" and "must not be described as completed" |
| `sensory/game_state.py` | `2562617f978c145af82ce8707210de577318de04c6749994df1edac078c7bb43` | lines 25–28 (`Lane` 0/1/2); lines 36–43 (`parse_lane`); lines 83–100 (`PlayerState` default CENTER, speed 0.5, jumping/rolling false); lines 249–263 (`features`, `player_lane` line 260) |
| `sensory/population_encoder.py` | `9b4594255935ef950ac639f24580dc85e174f54b95cc913addc2103b8b582134` | `EncoderSpec` lanes 54–55; `LanePopulation` lines 177–205; `encode` lines 188–197; `baseline_response` 199–200; `build_encoders` 242–251; `encode_state` 254–273 |
| `sensory/sensory_mapping.py` | `c655c14a7831a968d56c0e5dc7f5dc85e4d6170118e6439caaa0999d3755aaa8` | `PopulationPlan` 76–124; lane branch 83–97; group-order comment line 92; `NeuralPopulation` 127–188; index concatenation 145–147; `SensoryMapping` 208–246; `_choose` 258–274; `validate` 276–295 |
| `sensory/input_scheduler.py` | `223bce3738ac02f6f8de736209158df7aafa639cf1f05d9791f559a500e5cc07` | constructor 33–130 (`active_features`, `_stimulated_indices` from active features only); `_values_at` 162–174 (linear crossfade); `apply` 176–180 (additive); `signature` 221; `describe` 239+ |
| `sensory/temporal_scheduler.py` | `3be4ac9a7f04749cfcacdb62c47c254114e601579fd94b6ebc0f66ac3020641c` | config 48–70 (`max_hold_ms` 250, `pulse_gain` 0.5, `pulse_decay_ms` 150); `_add_at` 238–253 (sample-and-hold + pulses); `apply` 255–257 |
| `perception/temporal.py` | — | `Lifecycle` 50–58 (appeared/persisting/approaching/receding/disappeared/occluded/uncertain); `PULSE_EVENTS` 70–72 (appeared/approaching/receding only) |
| `brain/brain_simulator.py` | — | `__init__` 71–112 (input-schedule contract); `run` 192; `input_schedule.apply` 252–253 (additive) |
| `experiments/phase_3c/temporal_acceptance.py` | `41f4b09effbed172502bcd06c8abc32f879b2a0168ced20bf0ec09838adc0543` | `DISTANCE_FEATURE = "obstacle_distance"` line 67; limitations 80–100 (sample-and-hold only; 3C.5 not executed) |

**Pool sizes (measured read-only on the delivered graph, 139,255 nodes).**
`visual_left` 5,892; `visual_center` 76; `visual_right` 5,458; `visual_any`
11,426; `mechanosensory` 2,674. These are counts of predicted annotations, not
verified sensory pathways.

### 1.3 Prior experiment artifacts consulted

| Artifact | SHA-256 | Facts used |
|---|---|---|
| `experiments/phase_3c/results/temporal_acceptance.json` | `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc` | T7 verdict `NEGATIVE_RESULT`; criterion 3 false; no-input control 0 spikes; 3C.7 and 3C.9 values; `not_executed` includes 3C.5 |
| `experiments/phase_3c/results/p3_t2_full.json` | `dd27c5d2708be3e92c5f85b6de259206e974f2a1ed4f753b64c61802e9770afd` | C1 player block: 702 spikes, 36 stimulated neurons, 8 active, 0 outside; `player_lane` 404 spikes, `player_speed` 298; peak `player_lane` current 800 pA. C3 full input: 15,654,631 spikes, 3,710 stimulated, 15,650,921 outside (99.976%), 72/138 stimulated active |
| `experiments/phase_3c/results/p3_t3_ablation.json` | `6fbe3263de49d5a2db830f4118814a5e45889dd0698f05e070f46fe6566b8956` | Removing `player_lane` (12 neurons) from the full 14-feature input: total delta −15,651,773; outside delta −15,650,921; reference-spike delta −852. This is a regime change, not a lane-code measurement |
| `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json` | `6b88c734bbb5538deb0bc02db9af47bc412440727d2bce89f430c2fc85b579f8` | P4 5/12/14 spikes at constant 0.15/0.55/0.90; P12 51/47/47; P12S 51/0/0; approach/retreat d′ 0.1183; 0 outside spikes across 72 runs; P4 and P12 are different encoder banks, not nested |
| `experiments/phase_3c/results/p3_final_phase3_audit.md` | `f813ed605ecf65fd7a4d302ebd62700f73254a7decbe9664f9403841f1ac1047` | Phase 3C not accepted; 3C.5/6/8 unexecuted; 3C.2 negative; 3C.7 quantified |

### 1.4 What the sources establish and what they do not

Established:

- Lane is categorical, not Gaussian. Three lanes, four dedicated neurons per
  lane, one-hot activation, 200 pA per active neuron.
- `player_lane` is an integer enum 0/1/2; the default is CENTER.
- The mapping allocates disjoint visual neurons, one group per lane, in
  lane-code order.
- The delivered Phase 3A scheduler (`SensoryInputScheduler`) supports a linear
  crossfade of encoded activations; the Phase 3C scheduler
  (`TemporalActivationScheduler`) is sample-and-hold plus object-lifecycle
  pulses.
- 3C.5 has never been run, and no lane-sequence runner, lane metric or
  lane-specific result exists.

Not established:

- The four conditions of 3C.5. The design names only "left→center→right and
  reversed" and gives the count `4`.
- The per-lane dwell time, the transition duration, the active feature set, the
  number of mapping seeds for 3C.5, the primary metric and any acceptance
  threshold.
- Any lane-change event encoding. The design's T5 proposal mentions "lane/jump
  transitions" (line 142), but the implemented `PULSE_EVENTS` contains only
  appeared/approaching/receding. There is no lane-change pulse.

---

## 2. Existing lane implementation

### 2.1 State

`GameState` exposes 14 features; `player_lane` is `int(self.player.lane)` with
`Lane.LEFT = 0`, `Lane.CENTER = 1`, `Lane.RIGHT = 2`
(`sensory/game_state.py` lines 25–28, 260). `PlayerState` defaults to CENTER,
speed 0.5, not jumping, not rolling (lines 83–100). A state cannot be both
jumping and rolling (lines 97–98). When an object feature is absent, `features`
returns `None`, and `encode_state` substitutes the encoder's baseline response
(`sensory/population_encoder.py` lines 254–273). This matters for the control
conditions: absent object features emit zeros, not fabricated lanes.

### 2.2 Encoder

`LanePopulation.encode(lane)` starts from an all-baseline vector and writes
`amplitude` into the contiguous block
`[lane * neurons_per_lane : (lane+1) * neurons_per_lane]`
(`sensory/population_encoder.py` lines 188–197). With the delivered config this
is three blocks of four units, amplitude 1.0, baseline 0.0. The encoder is
memoryless: its output depends only on the current lane, never on the previous
lane. It therefore emits no lane-change signal and no order information.

### 2.3 Mapping

`PopulationPlan` builds lane groups from `lane_pools.items()` in insertion
order, with the comment "Group order is lane-code order: the i-th entry feeds
encoder lane i" (`sensory/sensory_mapping.py` lines 83–97). `NeuralPopulation`
concatenates the group indices in that order (lines 145–147), so the first four
mapped indices are encoder lane 0, the next four lane 1, the next four lane 2.
The delivered config orders the pools left, center, right
(`configs/sensory_config.yaml` lines 154–159).

Allocation is seeded, disjoint and greedy: each group receives the first unused
indices in a seeded permutation of its annotation pool; capacity exhaustion
raises `ValueError` (`sensory/sensory_mapping.py` lines 258–274). With the
delivered config and seed, `player_lane` is allocated 12 neurons, four from each
of `visual_left`, `visual_center`, `visual_right`. The center pool has only 76
neurons, versus 5,892 left and 5,458 right; this is a systematic anatomical
asymmetry that must be reported, not assumed away.

### 2.4 Scheduler and current injection

`SensoryInputScheduler` holds `(start_ms, GameState)` segments. For each
simulation time it finds the latest segment start, encodes that state, masks
features outside `active_features` to zero, and converts activations to pA
(`sensory/input_scheduler.py` lines 96–150). `_stimulated_indices` is built from
the active features only (lines 128–135), so a lane-only run has
`n_stimulated_neurons = 12`, not 138.

During the first `transition_ms` after a segment start, the scheduler linearly
interpolates between the previous and current encoded value vectors
(`sensory/input_scheduler.py` lines 162–174):

```
values = (1 - alpha) * previous + alpha * current
alpha  = (time_ms - segment_start) / transition_ms
```

The crossfade operates on encoded activations, not on interpolated `GameState`
fields. It is applied to every active feature, and `apply` adds the resulting
current to the simulator's current array rather than overwriting unrelated
input (lines 176–180).

`TemporalActivationScheduler` instead holds each frame's activations for up to
`max_hold_ms = 250` and adds decaying pulses for the three object-lifecycle
events (`sensory/temporal_scheduler.py` lines 238–257; `perception/temporal.py`
lines 50–72). A lane change is not a lifecycle event, so it produces no pulse.
For a lane-only timeline with no pulses, sample-and-hold and the T1 step both
produce piecewise-constant current that jumps at frame starts; the T1 crossfade
is not equivalent to either at a transition.

### 2.5 Simulator

`BrainSimulator` accepts any input schedule that provides
`apply(step, time_ms, current_pa)` and `stimulated_indices`
(`brain/brain_simulator.py` lines 98–112). It adds background, noise, synaptic
current and the schedule current before stepping the neurons (lines 245–259).
The neuron is a homogeneous LIF with `tau_m = 20 ms`, rheobase 150 pA, reset
−68 mV, refractory 2 ms, and no adaptation or short-term plasticity
(`configs/neuron_config.yaml`). Synapses are exponential with 5 ms / 8 ms time
constants and 1 ms delay (`configs/simulation_config.yaml`). The network is
recurrent; the simulator is deterministic under zero background and zero noise.

### 2.6 Existing empirical evidence relevant to lanes

- **P3-T2 C1 (player block).** With `player_lane`, `player_speed`, `jumping` and
  `rolling` active, 702 spikes were recorded: 404 attributed to `player_lane`,
  298 to `player_speed`. 8 of 36 stimulated neurons were active; 0 non-stimulated
  spikes; peak `player_lane` current 800 pA. This is *not* a lane-only result:
  `player_speed` is a 12-neuron Gaussian population at 200 pA that contributes
  298 of the 702 spikes and up to 1,096 pA.
- **P3-T2 C3 (full input).** 15,654,631 spikes, 3,710 stimulated and 15,650,921
  non-stimulated (99.976%); 72 of 138 stimulated neurons active. The full-input
  regime is an ignited network, not a sparse sensory readout.
- **P3-T3 ablation.** Removing `player_lane` from the full input removes the
  ignition regime (total delta −15,651,773; outside delta −15,650,921, reference
  delta −852). This shows that the lane population can change a network regime;
  it does not show that the network encodes lane identity or lane order.
- **P3-T4.1.** At the obstacle-distance operating point, four neurons produce
  5/12/14 spikes at 0.15/0.55/0.90, twelve neurons produce 51/47/47, and a
  twelve-neuron bank driven only at the four-neuron mapping produces 51/0/0.
  Approach/retreat d′ is 0.1183; outside spikes are 0 across 72 runs. The
  lesson for 3C.5 is that active-cell count, population size and which cells are
  driven can each change the result; the four- and twelve-neuron banks are
  different encoders, not nested. No superiority of four over twelve is claimed.

### 2.7 What is absent

- No lane-sequence builder. The delivered sequence builder varies
  obstacle/coin distance (`sensory/sensory_experiment.py` lines 302–334); it
  does not vary player lane.
- No lane-change event. `Lifecycle` has no lane-change member; `PULSE_EVENTS`
  excludes lane changes.
- No lane metric, no lane result, no lane test.
- No runner that isolates `player_lane` as the only active feature for a full
  600 ms sequence.

---

## 3. Original requirements versus missing definitions

### 3.1 The original text

The 3C.5 row is, verbatim (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` line 245):

> `| 3C.5 | Lane sequence left→center→right and reversed | Order sensitivity of lane changes | 4 |`

The lane-change definition is, verbatim (line 91):

> `| Lane change | Player lane differing between consecutive frames | Available |`

The suite protocol says sequences are `(timestamp_ms, GameState)` lists in
configuration or validated JSON, reversed sequences reverse time order and
timestamps but not object contents, and every condition constructs a fresh
encoder, scheduler and simulator (lines 265–272). The suite acceptance says:

> "reversed or shuffled sequences produce a measurable difference, or the
> absence of one is reported as a negative result" (lines 318–319).

and:

> "A negative result, if any, is reported without reframing it as success"
> (line 365).

The roadmap says 3C.1–3C.9 cover "lane ordering" and that about 57 conditions
plus roughly 15 seed repeats are proposed (lines 265–269). It does not define
3C.5's four conditions.

The last column of the design table is not defined. For 3C.1 it equals the
three distances; for 3C.5 it is `4`. This proposal reads it as a condition
count and supplies four conditions. That reading is an interpretation, not a
quotation; it is listed as a decision required in §11.

### 3.2 Resolution table

| Definition | Status | Proposed resolution | Basis |
|---|---|---|---|
| Lane states | ORIGINAL | `LEFT=0`, `CENTER=1`, `RIGHT=2`; one-hot | `game_state.py` 25–28; `population_encoder.py` 188–197 |
| Sequence contents | ORIGINAL for forward/reverse | C1 `L→C→R`; C2 `R→C→L`; both retained | design line 245; reversal rule lines 267–268 |
| Additional conditions | NEW | C3 `L→C→R→L`; C4 `L→R→C→L`; exact time reverses, endpoint-matched | new design decision; rationale in §5 |
| Number of conditions | ORIGINAL count only | Four sequence conditions, C1–C4 | design line 245; count interpretation flagged |
| Sequence duration | ORIGINAL 600 ms suite envelope; NEW exact grid | 600.5 ms, 12 frames at 50 ms | roadmap 600 ms; T7 `duration_ms` 600.5, `frame_interval_ms` 50 |
| Per-lane dwell | MISSING | Linear 200 ms (4 frames); cyclic 150 ms (3 frames) | NEW; chosen to fill 600 ms with 12 frames |
| Transition encoding | ORIGINAL that T1 exists and is the Phase 3A control; NEW for 3C.5 | Primary: T1 step (`transition_ms=0`); robustness: T1 crossfade (`transition_ms=50`) | `input_scheduler.py` 162–174; config line 17; rheobase arithmetic in §7.9 |
| Active features | MISSING | `player_lane` only | NEW; avoids the `player_speed` confound in P3-T2 C1 |
| Amplitude / baseline | ORIGINAL | 200 pA per active neuron; activation amplitude 1.0; baseline 0.0 | config lines 29–35 |
| Tuning width | ORIGINAL (none for lane) | No Gaussian sigma; lane is categorical | encoding doc 155–160 |
| Mapping seeds | ORIGINAL delivered seed 20261104; NEW three-seed plan for 3C.5 | 20261104, 20261105, 20261106 | config line 18; T4.1 seed set |
| Repetitions | MISSING | One run per condition per seed; a second subprocess run for determinism only | NEW; deterministic simulator |
| Fresh state | ORIGINAL | Fresh encoder, scheduler, simulator; mapping rebuilt per seed and hash-checked | design line 272 |
| Inter-stimulus interval | NOT APPLICABLE | One sequence per run; simulator reset between runs | NEW clarification |
| Baseline controls | ORIGINAL no-input control (3C.9) | No-input run plus constant-lane runs `K_L`, `K_C`, `K_R` | T7 3C.9; NEW constant controls |
| Primary metric | ORIGINAL population-vector similarity | State-residual, per-lane, time-resolved distance | design line 298; §6 |
| Acceptance threshold | MISSING | Pilot/null method; no invented numeric threshold | §8 |
| Lane-change pulses (T5) | PROPOSED, NOT IMPLEMENTED | Out of scope; lane-change event coding is untested | design line 142; `PULSE_EVENTS` 70–72 |
| Feature-set scope | MISSING | Lane-only; no object, train, coin, speed, jump or roll | NEW |

The distinction is important. C1 and C2 are the literal original experiment.
C3 and C4 are new, endpoint-matched controls that make the order contrast
identifiable. The primary inferential contrast is C3 vs C4; C1 vs C2 is a
required secondary contrast. Neither is dropped.

---

## 4. Research question and hypotheses

### 4.1 Five separate questions

**Q1 — Static lane identity.** When the player holds a lane, does the
lane-only stimulated population produce a per-lane response that is
distinguishable across LEFT, CENTER and RIGHT?

**Q2 — Forward transitions.** When the player moves `L→C` and `C→R`, what is
the time-resolved response of the newly active group, the previously active
group, and the rest of the population?

**Q3 — Reverse transitions.** When the player moves `R→C` and `C→L`, does the
response differ from the corresponding forward transitions beyond the identity
of the lanes involved?

**Q4 — Temporal response and order.** Does the population response depend on
the order of lane states over time, beyond the current lane, the static
response magnitude, the endpoint state, and the mapping seed?

**Q5 — Stability across mappings.** Are the per-lane and order effects stable
across mapping seeds, given that each seed activates a different set of
physical neurons?

### 4.2 Scope recommendation

**Primary question: Q4.** The original 3C.5 is explicitly "order sensitivity of
lane changes". Q1 is a manipulation check, not the primary question: the
one-hot encoder guarantees that the *input* differs by lane, so a positive
identity result at the input level is true by construction. The scientific
question is whether the spiking network preserves identity and adds
order-dependent structure. Q2 and Q3 are the two halves of the original
sequence and are mechanistically necessary, but neither is order sensitivity by
itself. Q5 is replication, not a separate scientific question.

The primary comparison is **C3 vs C4**, because they are exact time reverses
with the same start lane, end lane, state multiset, dwell times and number of
transitions. The literal original pair **C1 vs C2** is retained as a required
secondary comparison, but it cannot separate order from endpoint: C1 starts L
and ends R, C2 starts R and ends L. No pair of three-state permutations can
match endpoints while differing in order. C3/C4 solves this by closing the
sequence with a return to L.

**What is recommended for inclusion:** Q1 as a precondition, Q2/Q3 as
transition characterization, Q4 as the primary, Q5 as the replication
criterion. **What is recommended for exclusion:** any claim about biological
perception, task performance, a downstream decoder's accuracy, or an
anatomically verified lane pathway. The experiment characterizes an
experimental input population; it does not establish what the fly computes.

### 4.3 Hypotheses

**H1 — Static identity (precondition).** Constant LEFT, CENTER and RIGHT
produce distinguishable per-lane group responses. Prediction: likely if each
group has at least one active cell, but not guaranteed; P3-T4.1's P12S control
(51/0/0) shows that a driven group can be silent at this operating point.
Falsified if a lane group is silent or all three groups are indistinguishable.

**H2 — Literal order (C1 vs C2).** Forward and reverse differ beyond the
constant-lane endpoint responses. Prediction: uncertain; the endpoint swap is a
plausible complete explanation. Falsified if the difference disappears when the
endpoint contribution is subtracted.

**H3 — Endpoint-matched order (C3 vs C4).** The state-residual response differs
between C3 and C4 beyond the block-permutation null in at least two of three
mapping seeds, and the difference survives restriction to the interior window
(200–450 ms, bins 4–8). Prediction: the encoder is memoryless and the neuron has no adaptation;
the only sources of order dependence are causal synaptic filtering (5/8 ms),
the spike reset/refractory nonlinearity, recurrent dynamics, and the transition
overlap. Over 150–200 ms dwells these may be small. **A negative result is a
live possibility and is an acceptable outcome.**

**H4 — Transition route.** Adjacent transitions (`L→C`, `C→R`, `R→C`, `C→L`)
and direct transitions (`L→R`, `R→L`) differ in overlap and latency; a direct
transition co-activates the two extreme groups without the center group during
the crossfade. Prediction: true at the encoder/current level by construction;
the question is whether the spiking readout preserves it. Falsified if the
spiking responses to adjacent and direct transitions are indistinguishable.

**H5 — Seed stability.** Per-lane rate profiles and the sign of the C3−C4
residual difference are consistent across seeds, even though the active neuron
identities differ. Prediction: magnitudes may vary, especially for CENTER,
because its pool is only 76 neurons. Falsified if the lane ordering or the sign
of the order effect flips across seeds.

**H6 — Sparse direct regime (validity).** Lane-only input leaves most of the
network silent, so the stimulated 12-neuron readout is not dominated by
recurrent ignition. Prediction: near-zero outside spikes, consistent with the
P3-T2 C1 player block (0 outside over 3.3 s). Falsified if outside activity is
large; in that case the result is reported as a network-regime observation, not
as direct lane coding.

### 4.4 Evidence standards

- A **positive order** claim requires H3 (or H2 with endpoint subtraction),
  H1 satisfied and H6 satisfied, in at least two of three seeds, with the
  interior-window effect surviving.
- A **negative order** result requires H1 and H6 satisfied, and H3 not
  exceeding the null in at least two of three seeds. It is reported as a
  negative result without reframing.
- If H1 fails (a lane group is silent), the correct outcome is
  **inconclusive for order**, not negative: the experiment did not have the
  capacity to express the contrast.
- If H2 is positive but H3 is negative, the correct attribution is
  **endpoint effect**, not order.

---

## 5. Four-condition proposal

### 5.1 Design logic

Three one-hot states in three positions cannot simultaneously match endpoints
and differ in order: every distinct permutation of `{L,C,R}` has a different
first and last state. The original pair C1/C2 is therefore endpoint-confounded.
The proposal keeps the literal pair and adds a closed-loop pair whose first and
last state are both L. The closed-loop pair is the primary order test; the
literal pair is the original-specification test.

### 5.2 Conditions

All conditions use 12 frames at 0, 50, …, 550 ms and a 600.5 ms run. The frame
at 550 ms is held to 600.5 ms.

| ID | Sequence | Frames (lane per 50 ms frame) | Start → end | Dwell | Transitions | Purpose |
|---|---|---|---|---|---|---|
| C1 | `L→C→R` | L L L L C C C C R R R R | L → R | 200 ms | 2 adjacent | literal 3C.5 forward |
| C2 | `R→C→L` | R R R R C C C C L L L L | R → L | 200 ms | 2 adjacent | literal 3C.5 reverse; exact reverse of C1 |
| C3 | `L→C→R→L` | L L L C C C R R R L L L | L → L | 150 ms | adjacent, adjacent, direct | endpoint-matched forward |
| C4 | `L→R→C→L` | L L L R R R C C C L L L | L → L | 150 ms | direct, adjacent, adjacent | endpoint-matched reverse; exact reverse of C3 |

C4 is exactly the time reverse of C3 under the convention
`t'_i = (N−1−i) × 50 ms`, `N = 12`. C2 is exactly the time reverse of C1 under
the same convention. The reversal preserves the frame grid, the state multiset
and the dwell times; it reverses the order and the transition sequence.

### 5.3 Why these four

- C1/C2 are the only pair the original document names. Dropping them would
  abandon the specification.
- C3/C4 are the smallest extension that removes the endpoint confound. They
  add one return transition to the original sequence; they do not introduce a
  new lane, a new feature or a new encoder.
- The four conditions form two matched forward/reverse pairs at two sequence
  topologies (open and closed). The open pair tests the literal experiment; the
  closed pair tests order with endpoints and dwell matched.
- A four-condition budget is respected. The controls in §5.8 are a
  separate control block, not additional 3C.5 conditions.

Alternatives considered and rejected:

- **All six permutations of `{L,C,R}`.** More conditions, but every pair still
  has unmatched endpoints, and the four-condition budget is exceeded.
- **Two sequences × two schedulers (step/crossfade) as the four conditions.**
  This conflates 3C.5 with the scheduler ablation (3C.8) and still leaves the
  endpoint confound. The scheduler is handled as a robustness factor instead.
- **Two sequences × two seeds.** The seed plan for 3C.5 is separately resolved
  in §5.7; using seeds as conditions would reduce the sequence contrast to two.

### 5.4 Primary and secondary contrasts

| Contrast | Conditions | Status | Interpretation |
|---|---|---|---|
| Primary order | C3 vs C4 | NEW | Endpoint-, dwell-, multiset- and transition-count-matched order test |
| Secondary order | C1 vs C2 | ORIGINAL | Literal forward/reverse; endpoint-confounded; interpreted only with endpoint subtraction |
| Topology | C1/C2 vs C3/C4 | NEW, descriptive | Differs in dwell and transition count; not a causal order contrast |
| Transition route | C3 vs C4 at 150 ms; C3 vs C4 at 450 ms | NEW, descriptive | Adjacent vs direct from the same start/end lane |
| State-matched history | C1 vs C2 during the C hold (200–400 ms) | NEW | Both are in CENTER but arrived from different lanes |

### 5.5 Timing, bins and windows

- Simulation `dt_ms = 0.5`; 1,201 steps for 600.5 ms.
- Frame interval 50 ms; 12 frames.
- Primary analysis bin 50 ms (12 bins), aligned to frames.
- Latency analysis bin 10 ms, only for event-aligned descriptive traces.
- Interior window for order: 200–450 ms (bins 4–8). It starts 50 ms after the
  first transition (150 ms) and ends at the start of the final return (450 ms),
  so both boundary transients are excluded. The middle transition (`C→R` in C3,
  `R→C` in C4, at 300 ms) is inside this window. Bins are half-open:
  `[50b, 50(b+1))`.
- Boundary windows: 0–200 ms (bins 0–3) and 450–600.5 ms (bins 9–11), reported
  separately. Differences confined to these windows are attributed to transition
  route/boundary, not to order.

### 5.6 Scheduler choice

The original suite does not fix a lane-transition duration. The delivered
config uses `transition_ms = 50`, and the Phase 3A scheduler implements T1 as
step plus linear crossfade. The design's T2/T3 are not implemented and are out
of scope for 3C.5.

**Recommendation:**

- **Primary mode: T1 step, `transition_ms = 0`.** A discrete lane change is a
  step; this mode gives the new lane group the full 200 pA immediately and does
  not split the drive below rheobase.
- **Robustness mode: T1 crossfade, `transition_ms = 50`.** This is the
  configured Phase 3A default. It is run for the four core conditions and the
  four extra closed-null sequences, so the primary C3-vs-C4 contrast and its
  matched null are both available under smoothing. It is not run for the
  constant, no-input, linear-null or single-transition controls.
- **Not used: `TemporalActivationScheduler` sample-and-hold.** For a lane-only
  timeline with no pulses it holds one encoded frame until the next frame, so
  the injected current is piecewise constant and jumps at frame starts — the
  same direct-current profile the step mode produces, with no pulse added. T7
  used this scheduler for the obstacle-distance suite, not for 3C.5.

The reason to separate the modes is arithmetic, not a result. With four active
neurons at 200 pA, the total injected current for one lane is 800 pA. During a
50 ms crossfade between two lanes the scheduler puts `(1−α)·200` pA on four old
neurons and `α·200` pA on four new neurons, so the total remains 800 pA but at
`α = 0.5` every stimulated neuron receives 100 pA, below the 150 pA rheobase.
The direct drive can therefore be subthreshold for part of every crossfaded
transition. A step does not have this drive gap. A negative result under the
crossfade would be ambiguous between "no order code" and "the crossfade
removed the drive"; the step mode removes that ambiguity. The crossfade mode
then asks whether the configured smoothing preserves or abolishes whatever the
step mode shows.

This is a **[NEW]** decision. It does not modify the encoder, the neuron model,
the synapse model or any global simulation parameter.

### 5.7 Seeds and repetitions

- Mapping seeds: 20261104, 20261105, 20261106. The first is the delivered
  Phase 3A/3A.5 seed; the other two are the T4.1 draws.
- The original 3C.5 row is single-seed in the design's seed plan (only 3C.2 and
  3C.7 are repeated for three seeds, lines 251–252). Using three seeds for 3C.5
  is **[NEW]**. Justification: the simulator is deterministic with zero noise,
  so the only noise estimate is mapping-realisation spread; a single seed
  cannot distinguish an order effect from a mapping artifact.
- One run per condition per seed. A second run in a fresh subprocess is a
  determinism check, not an independent replicate. Do not report three seeds ×
  two runs as six samples.
- Mapping is built once per seed and reused across conditions after its hash is
  verified; encoders, scheduler and simulator are fresh per condition.

### 5.8 Controls

| Control | Runs | Purpose |
|---|---|---|
| `K_L`, `K_C`, `K_R` (constant lane, 600.5 ms) | 3 conditions × 3 seeds | Static per-lane baseline and endpoint response; supplies the state-residual baseline |
| `N0` (no input schedule, zero background/noise) | 1 × 3 seeds | Zero-spike validity, as T7 3C.9 no-input (0 spikes) |
| Linear null: all six permutations of the three 200 ms blocks | 6 × 3 seeds (C1/C2 reused) | Order-null distribution for C1/C2 |
| Closed null: all six block sequences of `{L,L,C,R}` with the two L blocks non-adjacent | 6 × 3 seeds (C3/C4 reused) | Order-null distribution for C3/C4; all six have three transitions |
| Single-transition bank: `L→C`, `L→R`, `C→R`, `R→C`, `R→L`, `C→L` (300 ms pre, 300 ms post) | 6 × 3 seeds | Isolates each transition route; separates transition response from sequence composition |
| Step vs crossfade replay | C1–C4 plus the four extra closed-null sequences | 8 × 3 seeds (crossfade only); C1–C4 reused | Tests whether the configured smoothing preserves the step-mode result and its matched null |

The closed null is the important one. The multiset `{L,L,C,R}` has 12 distinct
block sequences; six have the two L blocks adjacent (which removes a
transition). The six with non-adjacent L blocks all have exactly three
transitions, the same 150 ms dwell blocks and the same state multiset. C3 and
C4 are two of these six. The other four are the order-null ensemble. This is a
matched null for the primary contrast, not a generic shuffle. "Closed" here
refers to the four-block cyclic design over three lanes, not to every null
sequence returning to L.

Only C3 and C4 start and end on the same lane (L). The other four null
sequences start or end on a different lane, so they are transition-count- and
dwell-matched but not endpoint-matched. The state-residual metric subtracts the
constant-lane response for whatever lane is active in each bin, which controls
static lane identity at that bin but not endpoint history. If the unmatched
endpoints inflate null distances, the percentile bar is raised and the test
becomes conservative; the direction of that bias is stated in the report rather
than corrected.

All null sequences use the same 12-frame, 600.5 ms grid and the same scheduler
mode as the condition they control.

**Not included:** a full 14-feature replay. The full-input regime ignites
(99.976% outside spikes) and cannot answer a lane-specific question. If a
full-input replay is run later for context, it must be labeled a different
regime and must not be pooled with 3C.5.

---

## 6. Metrics

### 6.1 Primary metrics

**M1 — Per-lane rate by bin.** For each condition, seed and 50 ms bin, the
mean spike rate of the four neurons in each lane group:

```
r[l, b] = (spikes in group l during bin b) / (4 neurons × 0.05 s)
```

Report the full 3 × 12 matrix, not only totals. This is the basic
time-resolved, per-lane readout.

**M2 — Active-cell identities and counts.** For each lane group and bin,
report the number of active neurons, their global indices and their root IDs.
This distinguishes a group that is silent from a group that is active at a low
rate. It also records which physical neurons carry the response in each seed.

**M3 — 12-dimensional population vector.** Flatten M1 into
`s[b] = [r_L1..r_L4, r_C1..r_C4, r_R1..r_R4]` (per-neuron rates, not group
means). Report Euclidean distance and cosine distance with an epsilon for zero
vectors. Group means alone can hide within-group redistribution.

**M4 — Static lane separability.** From `K_L`, `K_C`, `K_R`, compute pairwise
d′ between lane groups using the per-bin group rates, with seed-to-seed spread
as the noise estimate. Also run a leave-one-seed-out nearest-centroid
classification of the lane label from the 12-dimensional vector. Both are
descriptive; the classification is not learning and does not establish a
downstream decoder.

**M5 — Transition latency and overlap.** For each transition time `t0`, report:
first spike in the newly active group after `t0`; first 10 ms bin in which the
new group's rate exceeds its pre-transition mean by more than its pre-transition
standard deviation (a descriptive z-score, not an acceptance threshold); the
time course of the old group's decay; and the number of bins in which old and
new groups are simultaneously active. Direct and adjacent transitions are
reported separately.

**M6 — State-residual order distance (primary).** The raw C3/C4 difference is
confounded because the active lane differs at each time. Subtract the
constant-lane response at the same absolute time:

```
resid_condition[l, b] = r_condition[l, b] - r_static(lane_condition(b), l, b)
```

where `r_static(lane, l, b)` is the per-lane rate from `K_lane` at the same
bin. Then compute the distance between the C3 and C4 residual vectors:

```
D_order = mean_b  d( resid_C3[:, b], resid_C4[:, b] )
```

with `d` reported as both Euclidean and cosine. Compute `D_order` over the full
window and over the interior 200–450 ms window. The interior value is the
primary statistic; the full-window value diagnoses boundary effects.

**M7 — Reverse-time symmetry.** Compute `D_rev = mean_b d(s_C3[b],
s_C4[11−b])`. If the system were exactly time-reversal symmetric, this would be
zero (up to boundary conventions). A large `D_order` with a near-zero `D_rev`
means the response is time-reversed, not order-selective; a large `D_rev` means
the dynamics break time-reversal symmetry. Report both. This is a diagnostic,
not a success criterion by itself.

**M8 — Null percentile.** Compute `D_order` for every pair of sequences in the
matched null ensemble (six linear permutations; six closed permutations) under
the same seed and scheduler mode. Report the observed C3/C4 (and C1/C2)
distance as a percentile of the null pairwise-distance distribution, excluding
the focal pair itself. This is the primary inferential scale. It avoids a
fabricated numeric threshold.

**M9 — Cross-seed consistency.** Report `D_order` per seed; the sign of the
C3−C4 residual difference per lane and bin; Spearman rank correlation of
per-lane total counts across seeds; and the coefficient of variation of each
lane's total. Neuron identity is never compared across seeds, because the
mappings are disjoint. The consistency criterion is on the response profile,
not on which cells fire.

**M10 — Outside activity.** Non-stimulated spikes, active outside neurons and
outside spike fraction, per condition and bin. This measures recurrent
recruitment. The primary per-lane metrics use stimulated neurons only; outside
activity is reported separately and is not subtracted.

**M11 — Magnitude controls.** Total stimulated spikes and total injected
sensory current per bin. Under the one-hot encoder and a single active lane,
the injected total is 800 pA at every step, including during a crossfade
between two lanes. Measure it and assert it. Any condition-level difference in
total spikes is therefore not a total-current effect; it must come from the
distribution of current across neurons, spike nonlinearity or recurrence.

**M12 — Crossfade drive gap.** For each transition window and simulation step,
count stimulated neurons receiving at least 150 pA. Report the fraction of
steps in which no stimulated neuron reaches rheobase. This is 0 for a step and
can approach 1 near `α = 0.5` for the 50 ms crossfade. It quantifies the
scheduler confound directly.

### 6.2 Secondary metrics

- First-spike latency, peak rate and peak time per lane group.
- Response duration and return-to-baseline time after each transition.
- Membrane voltage traces for the 12 stimulated neurons, if the simulator's
  recording interface exposes them; otherwise report spike times only.
- Active-cell count per group per condition.
- Wall time, steps/s, scheduler memory, retained arrays and RSS change.
- Deterministic input-schedule and spike hashes.

### 6.3 How the metrics separate the four things that could differ

| Question | Metric | What it rules out |
|---|---|---|
| Lane identity | M1, M2, M4 (constant lanes) | A difference that is only a total-magnitude difference |
| Transition response | M5, M12 | A difference that is only a static lane effect |
| Order beyond state | M6 (state residual), M8 | A difference explained by the different active lane at each time |
| Magnitude | M11 | Total current or total spike count as a lane code |
| Recurrence | M10 | A stimulated readout contaminated by network ignition |
| Mapping artifact | M9 | A single-seed effect that does not replicate |
| Boundary/onset | M6 interior vs full, M7 | A difference confined to the first/last transition |

The logic is deliberately subtractive. A raw C3/C4 difference is not evidence
of order; it is expected because C3 and C4 are in different lanes at each time.
The state residual removes the static lane response. A residual difference is
still not proof of an order code; it may be causal synaptic filtering or spike
reset. The null ensemble and the reverse-time diagnostic bound those
explanations. What remains is a descriptive history effect. No claim of a
"lane-order code" beyond that is made.

### 6.4 Deliberately not used

- Total spike counts alone. They are lane-invariant at the current level and
  can hide redistribution across the four neurons.
- Aggregate population cosine alone. With 12 stimulated neurons and zeros, it
  is unstable and can be dominated by one group.
- Neuron-identity matching across seeds. The mappings are disjoint.
- Accuracy of a trained decoder. The nearest-centroid measure is descriptive
  and leave-one-seed-out only; it is not learning.
- Any metric computed on the full 139,255-neuron spike count as if it were the
  sensory readout. Outside activity is reported separately.

---

## 7. Controls and confounds

### 7.1 Population size

The lane bank is fixed at 12 neurons (4 per lane) across all conditions. The
experiment never compares 4-neuron and 12-neuron lane banks. P3-T4.1 is used
only as evidence that population size and active-cell count can change spike
counts and ordering: P4 produced 5/12/14, P12 51/47/47, and P12S 51/0/0. The
four- and twelve-neuron obstacle-distance banks are different encoders, not
nested sets. No claim that four neurons are superior to twelve is made here,
and none should be inferred from this design.

### 7.2 Encoder bank

The lane encoder is categorical: amplitude 1.0, baseline 0.0, no Gaussian
sigma. The Phase 3A.5 `sigma_fraction = 0.20` applies to the obstacle-distance
Gaussian bank, not to lane. Do not import that tuning assumption. The relevant
encoder-level confound is group size and which physical neurons are drawn, not
a tuning width.

### 7.3 Total current

For one active lane, four neurons receive 200 pA each: 800 pA. During a linear
crossfade between two lanes, four old neurons receive `200(1−α)` and four new
neurons receive `200α`; the sum is still 800 pA. Therefore total injected
current is invariant to lane identity and to the crossfade. M11 measures this
invariant; a violation is an execution failure. Total current cannot explain a
per-lane difference. Only the distribution across neurons can.

### 7.4 Active-cell counts and threshold dominance

A lane group with zero active cells cannot encode that lane. The design reports
active counts per group per bin and treats a silent group as an
**inconclusive** capacity result, not as a negative order result. This is
directly motivated by P3-T4.1's P12S 51/0/0: a driven four-neuron mapping can
be silent while the twelve-neuron bank is active. The lane analog is measured,
not assumed.

### 7.5 Mapping seed and anatomical asymmetry

The three lane groups are drawn from different annotation pools:
`visual_left` (5,892), `visual_center` (76), `visual_right` (5,458). The center
group is drawn from a much smaller pool, so its connectivity neighborhood may
differ systematically. Consequences:

- Report the per-seed indices and root IDs for all three groups.
- Treat LEFT/CENTER/RIGHT as three mapped experimental populations, not as
  anatomically matched lane channels.
- Use the constant-lane controls to estimate each group's own baseline; never
  compare raw center rates to left/right rates without that baseline.
- Do not interpret a center-specific effect as a lane code until it replicates
  across seeds and survives the state-residual analysis.

An optional pool-matched control (all three groups drawn from `visual_any`,
11,426 neurons) would test whether the center-pool asymmetry drives the result.
It requires a new mapping configuration and is not part of the four-condition
core; it is listed as a decision in §11, not as a required run.

### 7.6 Zero-noise determinism

The simulator is deterministic with zero background and zero noise. Seed spread
is mapping-realisation spread, not biological or runtime variability. A second
run in a fresh subprocess must produce the identical spike hash and input
schedule signature. Any within-seed variation is a bug, not a replicate.

### 7.7 Neuron identity versus rate code

Because the three groups are disjoint, a downstream reader could identify the
lane from *which* four neurons are active, with no rate code at all. This is a
consequence of the one-hot wiring, not a network computation. The experiment
therefore reports:

- an identity readout (which group is active/most active), as a manipulation
  check;
- a rate readout (per-neuron rates within the active group), as the
  informative signal;
- a state-residual/order readout (M6), as the primary question.

A positive identity readout is expected by construction and is not evidence of
a network code. The design does not claim otherwise.

### 7.8 Recurrent activity

The full 14-feature input ignites the network (P3-T2 C3: 99.976% outside
spikes). 3C.5 therefore uses lane-only input. The P3-T2 C1 player block had 0
outside spikes over 3.3 s, but C1 also drove `player_speed`; lane-only may
differ. Outside activity is measured (M10), not assumed. No synapse-block
control exists in the current interface; the experiment cannot causally
separate direct drive from recurrent input onto the stimulated neurons. It can
report recruitment and treat a large outside fraction as a regime observation.
A future synapse-block control would require a simulator option and is out of
scope.

### 7.9 Scheduler and crossfade

This is the most consequential confound. At `α = 0.5` during a 50 ms
crossfade, each of the eight transition neurons receives 100 pA, below the
150 pA rheobase. The direct drive can be subthreshold for a substantial part of
each transition. The step mode does not have this gap. M12 measures the gap.
The primary mode is the step; the crossfade is a robustness condition. A
negative result under the crossfade is not interpreted as a negative order
result unless the step mode also fails.

The crossfade is linear and time-symmetric, so at the input-current level the
reverse sequence's current is the time reverse of the forward current. Any
output asymmetry under the crossfade therefore comes from the neuron/synapse
dynamics and the spike nonlinearity, not from an asymmetric input encoding.
This is exactly why M7 (reverse-time symmetry) is reported alongside M6.

### 7.10 Endpoint, dwell and transition count

- C1/C2 endpoints differ. The design subtracts the constant-lane endpoint
  response and treats C3/C4 as the primary order test.
- C1/C2 have 200 ms dwell; C3/C4 have 150 ms dwell. Linear-vs-cyclic
  comparisons are descriptive only; dwell is not a causal factor in the
  primary contrast.
- C1/C2 have two transitions; C3/C4 have three. The closed null matches the
  three-transition count; the linear null matches the two-transition count.
  Do not compare across the two nulls as if they were one distribution.

### 7.11 Feature-set confounds

- `player_speed` is a 12-neuron Gaussian population at 200 pA. P3-T2 C1 shows
  it contributes 298 of 702 spikes and up to 1,096 pA. It is **inactive** in
  3C.5.
- Object, train and coin features are absent; their encoders emit baseline
  zeros, and the scheduler masks them. They are not active.
- `jumping` and `rolling` are false; they are not active.
- A full 14-feature replay is a different regime and is not part of 3C.5.

### 7.12 What P3-T4.1 does and does not contribute

P3-T4.1 contributes three confound lessons: population size changes counts
(P4 vs P12), which cells are driven changes counts (P12 vs P12S), and the
four-neuron and twelve-neuron banks are different encoders. It does **not**
establish that four neurons are better, that a smaller population is superior,
or that the lane bank should be resized. 3C.5 holds the lane bank fixed at 12
and reports active-cell counts. No P4-superiority claim is made.

---

## 8. Acceptance criteria

### 8.1 Execution validity (must pass before any scientific interpretation)

| ID | Criterion |
|---|---|
| E1 | All core, control and null runs complete without numerical, capacity or validation failure. |
| E2 | Each run has exactly 12 stimulated neurons (`player_lane` only); no other feature contributes current. |
| E3 | Total injected sensory current is 800 pA at every step within `1e-9` pA, for holds and for crossfades. |
| E4 | Constant-lane runs activate exactly the intended four-neuron group; any silent group is reported, not hidden. |
| E5 | The no-input run produces 0 spikes, matching the T7 3C.9 no-input control. |
| E6 | Lane group order is asserted to be left, center, right against lane codes 0, 1, 2; the assertion fails loudly if the config order changes. |
| E7 | Lane groups are disjoint, each has four neurons, and all indices lie inside their annotation pools. Per-seed indices and root IDs are recorded. |
| E8 | Reverse sequences are exact time reverses on the 50 ms grid; the sequence hash differs from the forward hash and the state multiset is identical. |
| E9 | A parent run and two fresh-subprocess runs produce identical input-schedule signatures and spike hashes. |
| E10 | The existing test suite passes; no simulator, encoder, mapping or scheduler semantics are changed. |
| E11 | All artifacts and source/config/connectome/protected hashes are recorded in a sidecar; `git status` before and after shows no unintended change. |
| E12 | Outside activity is reported separately; if it is nonzero, the report states that the stimulated readout includes recurrent input and does not claim a direct-drive-only result. |

E1–E12 are execution validity, not scientific success. A run can be valid and
the scientific outcome can still be negative.

### 8.2 Scientific outcome classes

| Outcome | Criteria | Reporting |
|---|---|---|
| `POSITIVE_ORDER` | H1 and H6 satisfied; C3/C4 state-residual distance exceeds the matched-null envelope in ≥2/3 seeds; the interior-window effect survives; the sign is consistent across seeds | Report as a descriptive history/order effect, not as perception or a task code |
| `NEGATIVE_ORDER` | H1 and H6 satisfied; C3/C4 distance does not exceed the null in ≥2/3 seeds, or the effect vanishes when boundary bins are excluded | Report as a negative result without reframing; state the operating point and the crossfade/step mode |
| `ENDPOINT_EXPLAINED` | C1/C2 differ, but C3/C4 do not, and the C1/C2 difference is within the constant-lane endpoint spread | Attribute to endpoint/last-state, not order |
| `TRANSITION_ONLY` | Differences are confined to the transition windows and vanish in the hold/interior windows | Attribute to transition route/filtering, not sequence order |
| `INCONCLUSIVE_SILENT_LANE` | One or more lane groups have zero active cells, or static identity (H1) fails | Report as a capacity/threshold limitation; do not call it negative order |
| `INCONCLUSIVE_OUTSIDE_DOMINATED` | Outside activity dominates and the stimulated readout is not separable from network recruitment | Report as a network-regime observation; do not claim lane coding |
| `INVALID_EXECUTION` | Any E1–E12 failure | Report the failure and stop; do not interpret |

### 8.3 Thresholds: no original number exists

The 3C.5 row has no numeric threshold. The suite's criterion 5 is qualitative:
a measurable difference, or a reported absence. The T7 `d′ = 1.0` and cosine
`0.01` are explicitly **new operationalizations** for the obstacle-distance
suite (`temporal_acceptance.json` limitations; T7 runner limitations lines
80–100). They are not 3C.5 thresholds and must not be imported as if they
were.

Proposed method for a defensible threshold:

1. Build the matched null ensemble before looking at the main result: six
   linear permutations for C1/C2, six closed permutations for C3/C4, each under
   the same seed and scheduler mode.
2. Compute the null distribution of the state-residual pairwise distance among
   the six sequences, excluding the focal forward/reverse pair.
3. Pre-register the decision rule as: the observed focal distance must exceed
   the **95th percentile** of the matched null distribution in at least two of
   three seeds, and the interior-window value must do so as well. Report the
   maximum null distance as a sensitivity check.
4. If the null ensemble is degenerate (all pairwise distances zero), the
   percentile rule is uninformative; fall back to the seed-spread rule and
   report the degeneracy. This fallback is fixed before execution.
5. Do not set a numeric effect-size cut-off from the main data. The percentile
   is a pre-registered statistical convention, not an estimated effect size.

The 95th percentile and the two-of-three seed rule are **new** choices. The
two-of-three convention is borrowed from the roadmap's 3C.2 acceptance
language; applying it to 3C.5 is new. Both are fixed before the main run. A
pilot may check runtime, capacity, null non-degeneracy and whether the 95th
percentile is estimable with six sequences; the pilot must use a separate
mapping seed (proposed 20261107) and must not contribute to the main result.

The null ensemble is small: six sequences give 15 pairs, 14 after removing the
focal pair, so the attainable percentiles are coarse (multiples of about 1/15)
and the 95th percentile is close to the largest null distance. This is
disclosed rather than hidden. The maximum null distance is reported alongside
so the reader can see how close the two rules are, and the pilot checks that a
non-degenerate null exists before the main run. A larger null ensemble cannot
be manufactured from the same three-state, four-block design without changing
dwell or transition count, which would break the match to C3/C4.

### 8.4 A valid negative result remains possible

The design deliberately does not guarantee a positive. If C3/C4 do not separate
beyond the matched null, or if the effect is confined to boundaries, the
correct output is `NEGATIVE_ORDER` or `TRANSITION_ONLY`. It must be reported
with the same detail as a positive, including the per-lane traces, the null
distribution and the seed-level values. It must not be reframed as "the network
uses a temporal code" or "the encoder is sufficient." The original design's
negative-result rule (lines 318–319, 365) governs.

---

## 9. Reproducibility and pre-registration

### 9.1 Frozen configuration

A future implementation should add one new configuration file, proposed as
`configs/p3_3c5_lane_encoding.yaml`, containing:

- protocol: `duration_ms: 600.5`, `frame_interval_ms: 50.0`, `bin_ms: 50.0`,
  `dt_ms: 0.5`, `current_pa: 200.0`, `transition_ms` for the step and crossfade
  modes, zero background/noise, spike capacity;
- the four C1–C4 timelines as explicit `(timestamp_ms, GameState)` lists, not
  code;
- the constant, no-input, single-transition and null sequences;
- seeds 20261104/5/6 and the pilot seed;
- analysis parameters: interior window, bins, null percentile, seed rule.

The file does not exist yet; this proposal does not create it.

### 9.2 Seeds and repeats

- Mapping seeds: 20261104, 20261105, 20261106.
- Pilot mapping seed: 20261107 (new draw; not part of the main result).
- One run per condition per seed, plus one fresh-subprocess repeat for
  determinism. The repeat is not an independent sample.
- The simulator seed is fixed; with zero noise, it does not affect the result,
  but it is recorded.

### 9.3 Hashes and signatures

For every run, record:

- SHA-256 of the configuration file;
- SHA-256 of the canonical JSON sequence list;
- the scheduler's `signature()` for the input schedule;
- SHA-256 of the encoder, mapping, scheduler, simulator, neuron and synapse
  source files used;
- SHA-256 of `datasets/processed/connectome.npz`
  (`3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`);
- SHA-256 of protected files (README
  `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563`;
  connectome as above);
- the git commit and a `git status` block.

### 9.4 Expected artifacts

Proposed new, clearly named artifacts (none created by this proposal):

- `experiments/phase_3c/results/p3_3c5_lane_encoding.json` — per-run,
  per-condition, per-seed, per-bin counts; active indices; current audit;
  outside activity; null distances; outcome class.
- `experiments/phase_3c/results/p3_3c5_lane_encoding.sidecar.json` — hashes,
  git block, environment, protected hashes.
- `experiments/phase_3c/results/p3_3c5_lane_encoding_report.md` — report with
  the decision and limitations.
- `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` — the frozen protocol and
  decision rule, hashed before the main run.

Existing Phase 3 results are never overwritten. If a rerun is needed, it gets a
new versioned name and a note explaining the supersession.

### 9.5 Determinism and regression tests

A future implementation should add focused tests:

- sequence builder produces the exact 12-frame timelines and hashes;
- reverse of C1 equals C2 and reverse of C3 equals C4 on the 50 ms grid;
- lane-only active-feature masking yields exactly 12 stimulated neurons;
- total injected current is 800 pA for holds and crossfades;
- group order is left, center, right and fails if the config order changes;
- crossfade at `α = 0.5` puts 100 pA on eight neurons (the drive-gap
  arithmetic);
- no-input run yields zero spikes;
- parent and subprocess spike/schedule hashes match;
- the existing test suite passes unchanged.

No test may be weakened to obtain a favourable result. The neuron model,
synapse model and global simulation parameters are not modified merely to
obtain a favourable result.

### 9.6 Pre-registration sequence

1. Approve this design and the decisions in §11.
2. Write and hash the pre-registration document (protocol, conditions,
   controls, metrics, null rule, outcome classes, limitations).
3. Implement the runner/config/tests in a separate task; verify E1–E12 on a
   smoke run.
4. Run the pilot on seed 20261107; verify runtime, capacity, null
   non-degeneracy and that the 95th-percentile rule is estimable. Do not use
   pilot data in the main result.
5. Freeze the protocol and threshold rule; record the pre-registration hash.
6. Run the main matrix on seeds 20261104/5/6.
7. Analyze and report, including negative results and limitations.

No main-run execution may occur before steps 1–5.

---

## 10. Repository safety and integrity

This task is design only. The following are not done and must not be done in
this task:

- modify any existing file, including `README.md`, the roadmap, the Phase 3C
  design, the encoding document, the prior audit, the sensory configs, the
  neuron/synapse configs, the simulator, the encoders, the mapping, the
  schedulers or the tests;
- modify Phase 4–6 artifacts;
- modify the connectome or any trained model;
- execute any simulation or experiment;
- stage, commit or push;
- use `git add .` or `git add -A`;
- delete, stash, reset, clean or checkout anything;
- overwrite a completed result.

The only file added by this task is this document. All pre-existing tracked
modifications and untracked files are preserved. The implementation and
execution are separate future tasks.

---

## 11. Claims not made, and decisions required

### 11.1 Claims not made

- This document does not claim that 3C.5 has been run, completed or accepted.
- It does not claim that Phase 3C is complete.
- It does not claim that the network perceives lanes, selects actions or
  performs a task.
- It does not claim that the visual annotation pools are an anatomically
  verified lane pathway.
- It does not claim that four neurons are superior to twelve, or that a smaller
  population is better.
- It does not claim that a one-hot encoder is how the fly encodes lane.
- It does not claim that a measured C3/C4 difference is a "lane-order code";
  at most it is a descriptive history effect under the configured model.
- It does not claim that T1, T2, T3 or T5 is the correct temporal encoding.
  T2/T3 are out of scope; T5 lane pulses are not implemented.

### 11.2 Decisions required before implementation

1. **Four-condition interpretation.** Accept C1–C4 as the four conditions, with
   C3/C4 as the primary order contrast and C1/C2 as the literal original
   contrast. If the intended `4` means something else (e.g., two sequences ×
   two seeds), say so before implementation.
2. **Cyclic extension.** Accept the closed-loop C3/C4 sequences as a new
   design decision. They add one return transition to the original sequence.
3. **Scheduler.** Accept T1 step as the primary mode and T1 50 ms crossfade as
   the robustness mode. The proposal runs the crossfade for C1–C4 and the four
   extra closed-null sequences (the primary contrast and its matched null), and
   not for the constant, no-input, linear-null or single-transition controls.
   Overriding that scope is a decision the user must make before implementation.
4. **Seeds.** Accept three mapping seeds for 3C.5, although the original seed
   plan repeats only 3C.2 and 3C.7.
5. **Feature set.** Accept lane-only input, excluding `player_speed` and all
   object/body-state features.
6. **Controls.** Accept the constant-lane, no-input, single-transition and
   matched-null control blocks, and their run-count cost.
7. **Threshold method.** Accept the matched-null 95th-percentile rule with the
   two-of-three seed requirement, the max-distance sensitivity check, and the
   no-main-data-tuning rule.
8. **Pilot.** Accept a separate pilot seed (20261107) that is excluded from the
   main result.
9. **Pool-matched control.** Decide whether to add the optional `visual_any`
   mapping control for the center-pool asymmetry. It is not required for the
   core.
10. **Implementation task.** Authorize a separate task to write the
    configuration, runner, tests and pre-registration. This proposal does not
    implement them.

Until these decisions are recorded, this document remains a proposal, not a
pre-registration.

---

## Appendix A — Explicit timelines

Timestamps are milliseconds; the state at each timestamp holds until the next
timestamp; the 550 ms state holds to 600.5 ms.

| t | 0 | 50 | 100 | 150 | 200 | 250 | 300 | 350 | 400 | 450 | 500 | 550 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | L | L | L | L | C | C | C | C | R | R | R | R |
| C2 | R | R | R | R | C | C | C | C | L | L | L | L |
| C3 | L | L | L | C | C | C | R | R | R | L | L | L |
| C4 | L | L | L | R | R | R | C | C | C | L | L | L |
| K_L | L | L | L | L | L | L | L | L | L | L | L | L |
| K_C | C | C | C | C | C | C | C | C | C | C | C | C |
| K_R | R | R | R | R | R | R | R | R | R | R | R | R |

Reverse convention: `t'_i = (12 − 1 − i) × 50 ms`. Under this convention
`reverse(C1) = C2` and `reverse(C3) = C4`, with identical state multisets and
dwell times.

## Appendix B — Metric definitions

Let `n_i(b)` be the spike count of stimulated neuron `i` in bin `b` (50 ms),
and let `G_l` be the four neurons of lane group `l`.

```
r_l(b)      = sum_{i in G_l} n_i(b) / (4 * 0.05)          # Hz, group mean
s(b)        = [n_i(b) / 0.05 for i in 12 stimulated]       # Hz, per neuron
d_E(x, y)   = ||x - y||_2
d_cos(x, y) = 1 - (x·y) / (||x|| ||y|| + eps)
resid_c(l,b)= r_c(l,b) - r_static(lane_c(b), l, b)
D_order     = mean_b d(resid_C3(:,b), resid_C4(:,b))
D_rev       = mean_b d(s_C3(b), s_C4(11-b))
```

`r_static(lane, l, b)` is read from `K_lane` at the same absolute bin `b`, so
the onset transient is matched as well as the lane identity. `d` is reported
both as `d_E` and `d_cos`. The primary `D_order` uses the interior bins 4–8
(200–450 ms); the full-window value is reported as a diagnostic.

The null percentile is the rank of the observed focal `D_order` among the
matched-null pairwise `D_order` values, excluding the focal pair, per seed.
The decision rule uses the 95th percentile and the maximum as a sensitivity
check.

## Appendix C — Cross-reference of source claims

| Claim in this proposal | Source |
|---|---|
| Lane is one-hot, 3 × 4, 200 pA | `configs/sensory_config.yaml` 29–35; `sensory/population_encoder.py` 188–197 |
| Lane pools left/center/right | `configs/sensory_config.yaml` 154–159; `sensory/sensory_mapping.py` 83–97 |
| Center pool has 76 neurons | read-only annotation count on the delivered graph |
| Total lane current 800 pA | 4 neurons × 200 pA; corroborated by P3-T2 C1 `peak_frame_feature_current_pa.player_lane = 800.0` |
| Crossfade formula | `sensory/input_scheduler.py` 162–174 |
| No lane-change pulse | `perception/temporal.py` 50–72; `sensory/temporal_scheduler.py` 238–257 |
| Fresh state per condition | `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` 272 |
| Reversal rule | same, 267–268 |
| Negative-result rule | same, 318–319, 365 |
| 3C.5 count is 4 | same, 245 |
| 3C.5/6/8 unexecuted | `configs/temporal_sensory.yaml` 62–69; `experiments/phase_3c/results/p3_final_phase3_audit.md` |
| T7 thresholds are new | `experiments/phase_3c/temporal_acceptance.py` 80–100 |
| P4/P12/P12S counts and d′ | `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json` |
| C1 player-block and C3 full-input counts | `experiments/phase_3c/results/p3_t2_full.json` |
| Lane-ablation regime change | `experiments/phase_3c/results/p3_t3_ablation.json` |
| LIF rheobase 150 pA, tau 20 ms | `configs/neuron_config.yaml` |
| Zero background/noise | `configs/simulation_config.yaml` |
