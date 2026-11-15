# Phase 3A — structured sensory encoding

This document describes the Phase 3A sensory-input layer added to FLY-SURFER.
It covers the game-state schema, the population encoders, the feature-to-neuron
mapping, the input scheduler, the experiment suite and the scientific limits of
what the resulting activity means. Companion documents are
`docs/RESEARCH_REFERENCE_REVIEW.md` (external repositories, read-only review)
and the generated `experiments/phase_3/PHASE_3_REPORT.md` (measured results).

## Scientific status

| Element | Status |
|---|---|
| Connectome edges, neuron indices, synapse counts | Fixed, validated FLY-SURFER artifact derived from FlyWire FAFB v783 |
| `class`, `side`, `super_class`, `nt_type` labels | Predicted FlyWire annotations, not verified physiology |
| Feature assignment to a cell class or side | Experimental choice made for this project |
| Game states | Experimenter-defined scenes; no screenshot, vision or game is used |
| Gaussian / lane / boolean coding | Computational assumption, not a measured sensory code |
| Scheduled currents | Model input chosen to cross a model threshold |
| Spikes, rates, transmissions | Simulated activity, never a biological recording |

Phase 3A adds an input layer. It does not add perception, motor decoding,
learning, reward, or any connection to a running game.

## Pipeline

```
GameState  ->  population encoders  ->  SensoryMapping  ->  SensoryInputScheduler
(features)     (dimensionless)          (root IDs)          (pA per neuron)
                                                                    |
                                                          BrainSimulator (existing)
                                                                    |
                                                          recorded simulated spikes
```

Each stage has one job:

- `sensory/game_state.py` validates a scene and exposes named features.
- `sensory/population_encoder.py` converts one feature value into a
  dimensionless activation vector in `[baseline, amplitude]`.
- `sensory/sensory_mapping.py` assigns each encoding unit to a distinct real
  neuron index, drawn from predicted annotation pools.
- `sensory/input_scheduler.py` converts activations to pA and produces the
  current vector for a simulation step.
- `brain/brain_simulator.py` consumes the schedule through the existing
  `input_schedule.apply(step, time_ms, current)` hook. No second simulator
  exists and the connectome is not modified.

The scheduler is an object with `apply` and `stimulated_indices`, exactly the
interface the simulator already validated in Phase 2. Stimulus, background and
scheduled input remain additive; the scheduler does not replace the old
`Stimulus` path.

## Game-state schema

`sensory/game_state.py` defines strict, frozen dataclasses:

- `PlayerState(lane, speed, jumping, rolling)`
- `ObstacleState(present, lane, distance, obstacle_type)`
- `TrainState(present, lane, distance)`
- `CoinState(present, lane, distance)`
- `GameState(player, obstacle, train, coin, time_ms)`

`Lane` is a three-value enum (`left`, `center`, `right`); `ObstacleType` is
`low` or `high`. `parse_lane` and `parse_obstacle_type` accept enum members or
strings and reject anything else. `GameState.from_dict` does **not** require a
`player` block and does **not** reject unknown keys: a missing player block,
or missing player fields, is filled with the schema defaults `Lane.CENTER`,
speed `0.5`, `jumping=False` and `rolling=False`; unknown keys are ignored;
absent obstacle/train/coin blocks become `present=False`.

`GameState.neutral()` is the defined zero state: an empty track with the player
centred at speed `0.5`. These defaults are schema values, not observations.
Callers that need to know which values were observed must read the
`estimated_fields` provenance from `perception/game_state_adapter.py`, not
infer it from the state itself.

`GameState.features()` returns 14 keys:

| Family | Features |
|---|---|
| player | `player_lane`, `player_speed`, `jumping`, `rolling` |
| obstacle | `obstacle_present`, `obstacle_lane`, `obstacle_distance`, `obstacle_type` |
| train | `train_present`, `train_lane`, `train_distance` |
| coin | `coin_present`, `coin_lane`, `coin_distance` |

`None` marks a feature whose object is absent. The encoder then emits its
baseline response; the scheduler also masks features outside a condition's
active set. Within `GameState` and the encoders, no lane or distance is
fabricated for an absent object. That guarantee is narrower than "no feature
is ever invented": the perception adapter fills fields it cannot observe with
schema defaults (for example player lane `CENTER`, speed `0.5`, and
`jumping`/`rolling` false) and lists them in `estimated_fields`. Those
defaulted values are then encoded like observations. The
`SpatialFeatureBridge` docstring's statement that "feature values are never
repaired or invented" therefore holds only for absent objects, not for player
fields the dataset cannot label.

A lane feature and a numeric distance are not interchangeable quantities. Lane
and obstacle type use categorical populations, not Gaussian tuning.

### Feature provenance

Not every `GameState` feature has the same evidential status in the perception
path. The categories are:

- **measured** — supplied directly by the experimenter in synthetic or scripted
  scenes, with no perception stage involved;
- **detector-derived** — a presence flag or class/type read from a detector box
  and its class label; the observation's confidence is carried alongside. The
  class role (for example `jump-barrier` → low obstacle) is a name-derived
  hypothesis, not a verified game quantity;
- **geometry-derived** — computed from box geometry: lane from the box centre
  column, distance from the box's vertical position as a normalised proxy;
- **defaulted** — no observation exists, so a schema default is substituted;
- **unsupported** — the dataset or scene carries no source for the feature at
  all.

| Feature(s) | Source in the perception path | Class |
|---|---|---|
| `obstacle_present`, `train_present` | a detector box whose class maps to that family exists in the frame | detector-derived |
| `obstacle_type` | detector class name mapped to `low`/`high` (name-derived hypothesis) | detector-derived |
| `obstacle_lane`, `train_lane` | box centre → image column thirds | geometry-derived |
| `obstacle_distance`, `train_distance` | box vertical position → normalised proxy | geometry-derived |
| `player_lane` | no player label; adapter defaults to `CENTER` unless exactly one player object is detected, in which case its box-derived lane is used | defaulted (geometry-derived if a player object is detected) |
| `player_speed` | schema default `0.5`; the adapter records it as estimated | defaulted |
| `jumping`, `rolling` | schema default `False` | defaulted |
| `coin_present`, `coin_lane`, `coin_distance` | replay scenes contain no coin detections and the dataset has no coin labels | unsupported (defaults to absent) |

Confidence and visibility are not among the 14 features. They are carried per
observation (`VisualObservation.confidence`) and linked to feature groups by
`SpatialFeatureBridge`; presence and class are detector-derived while lane and
distance are geometry-derived.

Terrain classes (`ledge`, `ramp`) are tracked by the observation layer but are
not representable in `GameState`. The adapter selects the nearest eligible
object of each kind and records the rest as `UnrepresentedObject`.

## Population coding

### Gaussian

For feature `x`, unit `i` and preferred value `mu_i`:

```
r_i(x) = baseline + (amplitude - baseline) * exp(-(x - mu_i)^2 / (2 sigma^2))
sigma   = sigma_fraction * (maximum - minimum)
```

Preferred values are evenly spaced over `[minimum, maximum]`. The configuration
controls population size, range, `sigma_fraction`, amplitude and baseline.
Activations are dimensionless and validated to lie in `[0, 1]` with
`baseline <= amplitude`. Out-of-range or non-finite inputs raise `ValueError`.

### Lane

`LanePopulation` gives every lane a dedicated group of `neurons_per_lane`
units. The active lane's group is set to `amplitude`; all other units sit at
`baseline`. Lane index is categorical, so a Gaussian curve would be
meaningless.

### Boolean

`BooleanPopulation` sets all its units to `amplitude` when the state is true
and to `baseline` when false. It accepts a `bool` or exactly `0`/`1`.

### Determinism

Encoding is a pure function of the validated state and the configuration.
There is no randomness in the encoders.

## Feature-to-neuron mapping

`sensory/sensory_mapping.py` performs a seeded allocation over predicted
annotations from the validated graph:

1. `AnnotationFilter` selects neurons whose predicted `class` and `side` match
   a named pool. Empty selections are rejected.
2. Populations are allocated in configuration order. Groups that share a pool
   consume a seeded permutation without replacement, so allocations are
   disjoint unless `allow_duplicates` is explicitly enabled.
3. Each lane group maps to its own pool (`visual_left`, `visual_center`,
   `visual_right`); scalar Gaussian and boolean populations map to one pool.
4. `SensoryMapping.validate()` checks feature/encoder sizes, duplicate
   allocation and index bounds.
5. `SensoryMapping.report()` records, per feature group, the pool, filter,
   selected size, root IDs and predicted evidence, together with the
   classification (`predicted annotation`) and explicit limitations.

No root ID is hard-coded anywhere in source or configuration. The mapping is
reproducible for a fixed seed and graph. Per-condition JSON files record the
resolved schedule description together with deterministic input and spike
digests.

### Configured populations

The delivered `configs/sensory_config.yaml` uses 14 features and 138 mapped
neurons:

| Encoding | Features | Units each | Total |
|---|---|---:|---:|
| Lane (3 lanes x 4) | `player_lane`, `obstacle_lane`, `train_lane`, `coin_lane` | 12 | 48 |
| Lane (2 types x 6) | `obstacle_type` | 12 | 12 |
| Boolean | `jumping`, `rolling`, `obstacle_present`, `train_present`, `coin_present` | 6 | 30 |
| Gaussian (12) | `player_speed`, `obstacle_distance`, `train_distance`, `coin_distance` | 12 | 48 |

Lane groups draw from the visual left/center/right pools. `obstacle_type`
draws from all visual neurons. Body-state booleans (`jumping`, `rolling`) draw
from the predicted mechanosensory pool as an experimental choice; the other
features draw from the visual pool. With this configuration and seed, the
pools are large enough for the allocation to remain disjoint.

**Operating-point mismatch (4 versus 12 neurons).** The Phase 3A.5 calibration
(`configs/sensory_calibration.yaml`) selected **four** `obstacle_distance`
neurons at 200 pA, `sigma_fraction` 0.20 and seed 20261104. The delivered
`sensory_config.yaml` — and therefore the Phase 3B/3C replays — uses **12**
`obstacle_distance` neurons. Only the 200 pA amplitude is shared. The
recruitment, discrimination and ordering results measured at four neurons are
not a validation of the 12-neuron configuration; the population size, mapping
indices and threshold geometry all differ. This is an open operating-point
discrepancy, not a calibrated equivalence.

## Input scheduler

`SensoryInputScheduler` holds the resolved spike-free input timeline:

- Timeline entries are `(start_ms, GameState)`. For each time point the
  scheduler finds the latest segment start (`searchsorted(..., side="right")`)
  and encodes that state.
- Activations become currents through a per-feature amplitude map
  (`current_pa` in each feature block, default 200 pA). The scheduler never
  treats an activation as a firing rate.
- A transition of `transition_ms` linearly crossfades from the previous
  segment to the new one. At the exact segment start the blend factor is 0, so
  the previous state still applies; it reaches the new state after
  `transition_ms`.
- Features outside the condition's `active_features` are masked to zero, which
  keeps unrelated populations from receiving current. Stimulation is gated to
  `[0, duration_ms)`.
- Currents are written additively into the simulator's current vector.
  `stimulated_indices` is the union of mapped neurons for active features, and
  `signature()` returns the resolved indices, values and segment starts for
  hashing.

`plot_input_activity` renders the scheduled current per feature, which makes
onset, crossfade and masking visible without inspecting spikes.

## Experiments

The suite is driven by `experiments/phase_3/run_all.py` and configured in
`configs/sensory_config.yaml`. All conditions use the existing sparse
`BrainSimulator` with dt 0.5 ms, the fixed connectome artifact, zero background
current and zero noise; only the schedule changes.

| Experiment | Contents |
|---|---|
| 3A.1 individual features | Obstacle distance 0.90/0.55/0.15, obstacle lane left/center/right, coin distance 0.90/0.55/0.15, player speed 0.20/0.50/0.90, jumping false/true, rolling false/true |
| 3A.2 combined features | Obstacle + coin (other lane), train + player center (same lane), high speed + near high obstacle, obstacle + coin (same lane), jumping + approaching train |
| 3A.3 changing states | `obstacle_approach` and `coin_approach`: four 200 ms segments stepping distance 0.95 → 0.60 → 0.25 → absent |
| 3A.4 reproducibility | The representative combined condition is run twice in separate subprocesses; scheduler and spike hashes are compared with the parent process |

Single-feature conditions last 300 ms; sequences last 800 ms. Every condition
records summary activity, per-feature stimulated spike counts, synapse
transmissions, finite-state diagnostics, wall runtime, memory and the declared
input statistics.

### Commands

```bash
python -m experiments.phase_3.run_all
python -m experiments.phase_3.run_all --conditions single_ player_speed
python -m experiments.phase_3.run_all --condition combined_obstacle_and_coin_other_lane \
    --hash-out experiments/phase_3/results/hashes.json
python -m experiments.phase_3.run_all --skip-reproducibility
```

The first command regenerates everything under `experiments/phase_3/`. The
`--condition` form runs one condition without touching the results tree and is
what the reproducibility subprocesses call.

### Outputs

```
experiments/phase_3/
  PHASE_3_REPORT.md
  results/
    baseline.json
    mapping_report.json
    reproducibility.json
    summary.json
    conditions/<condition>.json
  plots/
    tuning_curves.png
    input_activity_representative.png
    spikes_by_condition.png
    active_by_condition.png
    mean_rate_by_condition.png
    raster_<condition>.png
    firing_rates_<condition>.png
```

Every result file is generated from a run; none is hand-edited. The report
distinguishes the measured graph structure, predicted annotations, configured
encoding assumptions and simulated activity.

## Performance measurement

`run_all.py` measures:

- a baseline run with no schedule, same dt and duration;
- each sensory condition, with wall runtime and steps/s;
- retained simulation arrays from `BrainSimulator.memory_breakdown()`;
- scheduler `memory_bytes` (indices, starts and per-step values);
- process RSS change before and after each run.

The headline comparison uses only conditions whose duration matches the
baseline. RSS change is descriptive: allocator reuse can make it zero or
negative, and it is not a peak-memory measurement.

## Validation

Phase 3A adds tests for:

- game-state validation, parsing, absence handling and feature keys;
- Gaussian, lane and boolean encoders, including out-of-range rejection;
- seeded mapping determinism, disjoint allocation and index bounds;
- scheduler transitions, crossfade, masking and additive current;
- protocol expansion for single, combined and sequence conditions;
- integration with `BrainSimulator` on small synthetic graphs, including the
  declaration that the connectome artifact is not modified;
- deterministic digests and report generation;
- the full suite alongside the 68 pre-existing tests.

The validated Phase 2 and Phase 2.5 commands continue to run unchanged. No
previous test was modified, weakened or deleted.

## Later replay observations (Phase 3B.2C / 3C)

These are recorded observations from later phases, not Phase 3A results, and
they do not upgrade the sensory claims above.

- **Real-sequence replay (2026-11-07,
  `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md`).** 100 detector frames over
  3,300.5 simulated ms produced 15,654,631 spikes, of which 15,650,921
  (99.976%) arose on non-stimulated neurons. This describes recurrent network
  activity under sustained drive. It is not evidence that the sensory code is
  carried by the stimulated population, not a signal-to-noise measurement for
  the connectome, and not a perception result.
- **Duration sensitivity (Phase 3C scripted integration,
  `reports/PHASE_3C_EVALUATION.md`).** Holding the same scripted drive to
  400 ms raised total spikes from 560 to 233,203 and non-stimulated spikes from
  116 to 232,639, while stimulated spikes moved only 444 → 564. The network
  enters a high-activity regime between 300.5 ms and 400 ms. The reported
  protocol stops at 300.5 ms; the 400 ms probe is an observation and must not
  be read as a perception or coding result.

## Scientific limitations

- **Threshold-dominated readout.** The 200 pA peak drive sits above the 150 pA
  LIF rheobase. Neurons whose tuning lies within a small fraction of the
  stimulus range can cross threshold, so spike counts across a feature sweep
  can be nearly identical. That is a property of this calibration, not
  evidence of graded sensory coding.
- **Predicted, not verified, targets.** Mapped neurons come from predicted
  `class` and `side` labels. Assigning visual neurons to an obstacle distance
  or mechanosensory neurons to a jump flag is a modelling choice; those cells
  may not process that feature in a real fly.
- **No sensory physiology.** Tuning width, preferred values, population sizes
  and current amplitudes are assumptions. No adaptation, receptor dynamics,
  sensory transduction or synaptic plasticity is modelled.
- **Synthetic percepts.** Game states are written by the experimenter. Phase 3A
  contains no screenshot capture, computer vision, game integration or browser
  automation, so no perception error is measured.
- **No motor or behavioural claim.** The connectome is an adult female FAFB
  brain without a complete ventral nerve cord. Phase 3A does not decode motor
  commands, select actions, assign reward or learn.
- **One selected operating point, with measured sensitivity limits.** Phase
  3A.5 swept amplitude, tuning width, population size, baseline, transition
  and seed (84 conditions) and selected 200 pA, `sigma_fraction` 0.20, four
  obstacle-distance neurons, seed 20261104 and zero baseline. Amplitude and
  tuning width produced no strictly monotone response and were retained as
  explicit fallbacks; population ordering appeared only at four neurons, so
  the selection is a small, threshold-sensitive point rather than a graded
  distance code. The delivered `sensory_config.yaml` uses 12 obstacle-distance
  neurons, so the calibrated point and the shipped population size differ (see
  "Operating-point mismatch" above).
- **External work is not reproduced.** Findings from Fly Hero, Eon fly-brain,
  Drosophila Brain Model and FlyVis are reviewed as external observations in
  `docs/RESEARCH_REFERENCE_REVIEW.md`. No external code, data or result is
  presented as a FLY-SURFER result, and no external repository is modified,
  vendored or executed.
