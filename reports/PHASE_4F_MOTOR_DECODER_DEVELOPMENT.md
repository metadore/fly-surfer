# Phase 4F — Motor Decoder Development

**Phase:** 4F
**Status:** Complete
**Verdict:** **PASS WITH LIMITATIONS**
**Decoder modules:** `motor/populations.py`, `motor/motor_decoder.py`
**Configuration:** `configs/motor_decoder.yaml`
**Experiment:** `experiments/phase_4f/run_decoder_experiment.py`
**Results:** `experiments/results/phase_4f/motor_decoder_experiment.json`
**Focused tests:** `tests/test_motor_populations.py`, `tests/test_motor_decoder.py`, `tests/test_motor_decoder_experiment.py`

This phase builds an independent, deterministic decoder that maps BANC
motor-neuron population activity to the abstract labels LEFT, RIGHT, JUMP and
NEUTRAL. The labels are decoder outputs derived from published effector
annotations. They are not identified biological motor commands, and nothing in
this phase is connected to Subway Surfers, keyboard automation or any game
runtime.

---

## 1. Executive verdict

**PASS WITH LIMITATIONS.**

All required decoder, configuration, test and experiment deliverables exist
and run. The decoder consumes the exact spike arrays produced by the existing
`SpikeRecorder`, never reads a graph edge, records the BANC threshold in every
result, and returns deterministic output for identical input. The 52 focused
tests pass, the full suite passes at 397 tests, and every protected artifact is
unchanged.

The limitations are scientific and architectural rather than mechanical:

1. The BANC graph cannot be run through the existing `BrainSimulator` without a
   transmitter-sign and weight policy that this phase did not adopt, so the
   controlled experiment drives motor pools with explicit current instead of
   propagating spikes through the connectome.
2. The decoder labels are annotation-derived abstractions, and the tergotrochanter
   pool is a jump-associated candidate pool, not a validated jump command.
3. With a 25 pA per-neuron jitter, 24 of 66 controlled runs change their primary
   label sequence, although most remain inside the correct active set. That is a
   genuine robustness limit of a fixed priority tie-break near equal active
   fractions.

No result in this phase shows that the connectome can control a game.

---

## 2. Inputs and protected artifacts

All BANC inputs were read read-only. The experiment verified the Phase 4D
manifest (10 checks, 0 failures) at the end of the run and compared its own
input hashes before and after; nothing changed.

| Input | Bytes | SHA-256 (prefix) |
|---|---:|---|
| `banc_graph_t1.npz` | 79,829,070 | `fee8e5e7f7dbd9b6…` |
| `banc_graph_t5.npz` | 13,484,120 | `6d47f2592a6d07f2…` |
| `banc_graph_t10.npz` | 6,699,534 | `00b3f447e2755660…` |
| `banc_nodes.csv.gz` | 3,800,401 | `144a2eb09aa1ed2b…` |
| `banc_id_map.csv.gz` | 1,098,539 | `ede93fa7f33f34d0…` |
| `banc_manifest.json` | 8,052 | `32d5afb4d24bbece…` |

The five raw BANC inputs, the FAFB artifacts, the root `README.md` and the
Phase 4D/4E reports are byte-identical to their pre-phase state (section 12).

Protected code was not modified: `brain/neuron_model.py`,
`brain/synapse_model.py`, `brain/brain_simulator.py`, `brain/neural_activity.py`,
`brain/banc_graph.py` and the Phase 4D artifacts are untouched. The pre-existing
placeholder `motor/action_decoder.py` was also left unmodified; it is not used
by this phase because its docstring names game actions, which would contradict
the explicit no-game-integration scope. The Phase 4F decoder lives in
`motor/motor_decoder.py`.

---

## 3. Part A — Decoder architecture

The decoder is a standalone package with two modules and no import of the
simulator internals beyond the recorder contract.

```text
motor/
├── __init__.py          package docstring
├── populations.py       annotation → boolean node masks
└── motor_decoder.py     signal extraction and action selection
```

Interface:

| Entry point | Signature | Purpose |
|---|---|---|
| `build_populations` | `(nodes, *, n_neurons=None, threshold=5, options=None)` | Build masks from a node table |
| `load_banc_populations` | `(nodes_path=None, graph_path=None, *, threshold=5, options=None)` | Load masks from Phase 4D artifacts and assert node-order equality |
| `MotorDecoder` | `(populations, config=None)` | Stateful decoder |
| `decode_window` | `(spike_times_ms, spike_neuron_indices, start_ms, end_ms)` | One half-open window |
| `decode_series` | `(…, start_ms, end_ms, *, include_partial=True)` | Consecutive windows |
| `decode_recorder` | `(recorder, start_ms, end_ms, *, include_partial=True)` | Accept a `SpikeRecorder` directly |
| `ActionDecision.as_dict` | — | Machine-readable output |

`decode_recorder` accepts any object exposing `spike_times_ms`,
`spike_neuron_indices` and `n_neurons`, which is exactly the shape of
`brain.neural_activity.SpikeRecorder`. The decoder therefore consumes existing
simulation output without changes to the simulator. Neuron indices are CSR node
indices, and `load_banc_populations` verifies that the node table order equals
`BancConnectome.root_ids`, so no `banc_888_id` lookup is needed at decode time.

The decoder holds no reference to a graph, an edge array, a weight or a
threshold. It sees only spike times, node indices and the boolean masks.

---

## 4. Part B — Action populations

Membership is defined only by published annotation columns. No edge, simulator
state or predicted neurotransmitter is used, and no neuron is moved by a
connectivity result.

| Population | Rule |
|---|---|
| `LEFT` | `super_class == "motor"` and `side == "left"` and `body_part_effector ∈ {front_leg, middle_leg, hind_leg}` |
| `RIGHT` | the same rule for `side == "right"` |
| `JUMP` | `super_class == "motor"` and `peripheral_target_type == "tergotrochanter_extensor_muscle"` |

All 20 tergotrochanter candidates are also leg motor neurons. The default
policy keeps the pools disjoint by removing the jump candidates from the leg
pools; an inclusive policy is configurable and both compositions are reported.

| Policy | LEFT | RIGHT | JUMP | Assigned | Unassigned motor |
|---|---:|---:|---:|---:|---:|
| Disjoint (default, `jump_membership_in_leg_pools: false`) | 185 | 186 | 20 | 391 | 414 |
| Inclusive (`true`) | 195 | 196 | 20 | 391 | 414 |

Under the inclusive policy the jump candidates are counted twice: all 20 are leg
motor neurons (10 left, 10 right), so LEFT gains 10 and RIGHT gains 10 while the
assigned union and the 414 unassigned neurons are unchanged.

Composition of the default pools:

| Pool | Effecters | Side | Proofread |
|---|---|---|---|
| LEFT 185 | front 65, middle 60, hind 60 | 185 left | 185/185 |
| RIGHT 186 | front 66, middle 60, hind 60 | 186 right | 186/186 |
| JUMP 20 | front 8, middle 6, hind 6 | 10 left, 10 right | 20/20 |

The 414 unassigned motor neurons (51.4% of 805) are not forced into a label.
They include the abdomen, wing, neck, haltere, proboscis, pharynx, spiracle,
antenna, crop, uterus, eye, salivary-gland and unknown pools. Neurons with
unknown `side` or unknown effector stay unassigned.

`ROLL` and `DUCK` have **no** population. `UNSUPPORTED_ACTIONS` records the
reason in the module and in every population report: no published annotation in
this export defines them, so implementing them would require evidence the
structural tables do not contain. This is reported as unsupported, not
approximated with a proxy.

---

## 5. Part C — Signals

The decision signal is the **active neuron fraction**: neurons in the
population that emitted at least one spike in the window, divided by population
size.

```text
active_fraction = |{i ∈ population : spike_i ∈ [start, end)}| / |population|
```

It is bounded in [0, 1] and cannot grow with population size, so the 186-neuron
RIGHT pool cannot outscore the 20-neuron JUMP pool merely by having more
neurons. Spike count and mean firing rate are reported as descriptive evidence
in `PopulationEvidence` but are **not** used for arbitration.

Evidence gate. A population is sufficient only if it produced at least
`min_spikes` spikes **and** at least `min_active_neurons` active neurons. An
insufficient population scores exactly zero. This prevents a single recruited
neuron in a small pool from producing a high fraction.

Time window. Every window is half-open, `start_ms <= t < end_ms`, so a spike at
exactly a boundary belongs to exactly one window.

Reported evidence per population per window:

| Field | Meaning |
|---|---|
| `size` | population size |
| `spikes` | spike count in the window |
| `active_neurons` | neurons with ≥ 1 spike |
| `active_fraction` | `active_neurons / size` |
| `mean_rate_hz` | `spikes / size / window_seconds` |
| `sufficient` | evidence gate passed |
| `reason` | `ok`, `empty_population`, `spikes_below_minimum`, `active_neurons_below_minimum`, or a `+`-joined combination |

Thresholds are declared a priori in the config and validated. They were not
fitted to a successful example; the experiment sweeps independent variables
(current amplitude and jitter) instead of tuning the decoder.

Configured values:

| Parameter | Value |
|---|---|
| `window_ms` | 50.0 |
| `step_ms` | 50.0 |
| `activation_threshold` | 0.20 |
| `release_threshold` | 0.10 |
| `min_active_neurons` | 3 |
| `min_spikes` | 5 |
| `tie_tolerance` | 1e-9 |

---

## 6. Part D — Action selection

Selection is deterministic and fully explicit.

1. Gate every population to a score in [0, 1] (section 5).
2. Optionally apply a moving average over the last `smoothing_windows` scores.
3. Mark each action active when `score > 0` and `score >= activation_threshold`,
   or, when hysteresis is enabled and the action was already active, when
   `score > 0` and `score >= release_threshold`.
4. Sort active actions by descending score; ties within `tie_tolerance` are
   broken by the configured `priority` (default `LEFT, RIGHT, JUMP`).
5. Report `active_actions` and one `primary_action`. NEUTRAL is the state when
   no action is active.

Arbitration modes:

| Mode | Behaviour |
|---|---|
| `all_above_threshold` (default) | Report every active action; simultaneous activity is *not* treated as mutually exclusive commands |
| `single` | Report only the primary action |

Reasons are explicit: `single_action`, `tie_broken_by_priority`,
`simultaneous_actions`, `neutral_no_activation`. The decision also carries a
`lateralization` value `(LEFT − RIGHT) / (LEFT + RIGHT)` or `None` when both are
zero.

Temporal smoothing and hysteresis are separate optional features, off by
default, and each is unit-tested in isolation. The decoder never forces an
action when the evidence is insufficient: `weak_left` and `weak_jump` remain
NEUTRAL across the whole amplitude sweep.

---

## 7. Part E — Calibration and synthetic testing

Thirty decoder tests cover the required cases. They validate the mapping and
mechanics; they do **not** calibrate the decoder biologically.

| Fixture | Decoder result |
|---|---|
| No motor spikes | NEUTRAL |
| Left only | LEFT |
| Right only | RIGHT |
| Jump only | JUMP |
| Bilateral | LEFT + RIGHT, primary LEFT (tie → priority) |
| Left + jump | LEFT + JUMP, primary LEFT (tie → priority) |
| Right + jump | RIGHT + JUMP, primary RIGHT (tie → priority) |
| Weak subthreshold | NEUTRAL |
| Uniform background | all active pools reported, primary LEFT |
| Ambiguous competing | documented priority tie-break, reversible by config |
| Sparse noisy | NEUTRAL unless gate and threshold are met |
| Unequal populations | 15-spike LEFT fraction 1.0 beats 30-spike RIGHT fraction 0.2 |

Test coverage includes mapping, normalisation, gate behaviour, threshold
behaviour, ties and priority reversal, neutral fallback, determinism, half-open
window boundaries, smoothing, hysteresis hold and release, state reset, single
arbitration, empty populations, lateralization, partial windows, recorder
equivalence and mismatch, invalid arrays and invalid configuration.

`tests/test_motor_populations.py` also runs against the real artifacts when they
are present and asserts: 172,433 nodes, threshold-5 edge count 1,535,710, sizes
185/186/20, motor 805, assigned 391, unassigned 414, jump 10/10 with effectors
8/6/6, inclusive sizes 195/196/20, and membership identity across thresholds.

These tests demonstrate that the implementation follows its specification. They
cannot demonstrate that the specification matches fly motor control.

---

## 8. Part F — Threshold sensitivity

The decoder supports BANC thresholds `count >= 1`, `>= 5` (primary) and `>= 10`.
`build_populations` and `load_banc_populations` require an explicit threshold,
and `MotorPopulations.threshold` is embedded in every population and experiment
result. No code path mixes thresholds.

| Threshold | Edges | LEFT | RIGHT | JUMP | Mask bytes equal |
|---:|---:|---:|---:|---:|---|
| 1 | 11,596,517 | 185 | 186 | 20 | yes |
| 5 | 1,535,710 | 185 | 186 | 20 | yes |
| 10 | 570,721 | 185 | 186 | 20 | yes |

Membership is invariant because Phase 4D retains every endpoint node at every
threshold and membership depends only on annotations. The decoder never reads an
edge, so a threshold cannot change a score. The threshold is still recorded so
that any future decoder that does use edges cannot silently mix graphs.

---

## 9. Part G — Reproducible controlled experiment

### 9.1 Interface limitation

`BrainSimulator` was constructed on `banc_graph_t5.npz` before the experiment
and failed:

```text
AttributeError: 'BancConnectome' object has no attribute 'vocabulary'
```

`SynapseModel.__init__` requires `graph.vocabulary` and `graph.nt_code` to
assign transmitter signs. `BancConnectome` provides neither, and Phase 4E
deliberately deferred any transmitter-sign policy. Supplying them would have
required an unapproved sign and weight policy, so the integration was stopped
and documented rather than forced, as the phase rules require.

The experiment therefore uses the **unmodified** `LIFPopulation` with an
explicit experimenter current into the declared motor pools, and the decoder
receives spike times and node indices in `SpikeRecorder` format. No synapse,
edge or connectome propagation is involved. The probe result is stored under
`interface.simulator_compatibility` in the results JSON.

### 9.2 Design

| Parameter | Value |
|---|---|
| Seed | 20261108 |
| `dt_ms` | 0.5 |
| Duration | 300 ms |
| Drive window | 50–250 ms |
| Decode window | 50–300 ms |
| Decoder windows | 50 ms, step 50 ms (5 windows) |
| Current amplitudes | 120, 140, 160, 180, 200, 220 pA |
| Rheobase (unmodified LIF) | 150 pA |
| Initial potential | −65 mV |
| Drive jitter (declared grid) | 0 pA |
| Jitter sensitivity | 25 pA per-neuron, seeded |
| Scenarios | 11 |

Scenarios: `baseline` (no drive), `left`, `right`, `jump`, `left_jump`,
`right_jump`, `bilateral`, `ambiguous_competition` (0.5 of LEFT and RIGHT),
`uniform` (0.3 of every pool), `weak_left` (0.02 of LEFT), `weak_jump` (0.05 of
JUMP). Each scenario is run at six amplitudes in both conditions: 66 declared
runs plus 66 jitter runs.

Driven neurons are chosen by ascending node index (`take = max(1, round(fraction × size))`),
which is deterministic and independent of graph structure. The declared grid is
jitter-free so that active fraction equals driven fraction and the response can
be interpreted directly; jitter is a separate robustness condition.

### 9.3 Response matrix (declared grid, primary label per drive window)

Windows are `[50,100)`, `[100,150)`, `[150,200)`, `[200,250)`; the fifth
window `[250,300)` is post-drive. `N` = NEUTRAL.

| Scenario | 120 pA | 140 pA | 160 pA | 180 pA | 200 pA | 220 pA |
|---|---|---|---|---|---|---|
| baseline | N N N N | N N N N | N N N N | N N N N | N N N N | N N N N |
| left | N N N N | N N N N | N L L L | L L L L | L L L L | L L L L |
| right | N N N N | N N N N | N R R R | R R R R | R R R R | R R R R |
| jump | N N N N | N N N N | N J J J | J J J J | J J J J | J J J J |
| left_jump | N N N N | N N N N | N L L L | L L L L | L L L L | L L L L |
| right_jump | N N N N | N N N N | N R R R | R R R R | R R R R | R R R R |
| bilateral | N N N N | N N N N | N L L L | L L L L | L L L L | L L L L |
| ambiguous_competition | N N N N | N N N N | N R R R | R R R R | R R R R | R R R R |
| uniform | N N N N | N N N N | N L L L | L L L L | L L L L | L L L L |
| weak_left | N N N N | N N N N | N N N N | N N N N | N N N N | N N N N |
| weak_jump | N N N N | N N N N | N N N N | N N N N | N N N N | N N N N |

Interpretation of the sequence, not of the biology:

- **120 and 140 pA are below rheobase.** No driven neuron spikes, so the decoder
  is correctly NEUTRAL in every scenario.
- **160 pA is at threshold.** Driven neurons first spike after the first decode
  window: at `[50,100)` the LEFT pool has 0 spikes, at `[100,150)` it has 185.
  The first non-neutral window is therefore the second one. This is LIF charging
  latency, not a decoder delay; the decoder reports the empty window as
  `spikes_below_minimum`.
- **180–220 pA** recruit every driven neuron in every drive window, and each
  scenario returns its declared active set.

At 180 pA:

| Scenario | Driven neurons | Spikes | Active actions | Primary |
|---|---|---:|---|---|
| baseline | 0 | 0 | — | NEUTRAL |
| left | 185 | 925 | LEFT | LEFT |
| right | 186 | 930 | RIGHT | RIGHT |
| jump | 20 | 100 | JUMP | JUMP |
| left_jump | 185 + 20 | 1,025 | LEFT, JUMP | LEFT |
| right_jump | 186 + 20 | 1,030 | RIGHT, JUMP | RIGHT |
| bilateral | 185 + 186 | 1,855 | LEFT, RIGHT | LEFT |
| ambiguous_competition | 92 + 93 | 925 | LEFT, RIGHT | RIGHT |
| uniform | 56 + 56 + 6 | 590 | LEFT, RIGHT, JUMP | LEFT |
| weak_left | 4 | 20 | — | NEUTRAL |
| weak_jump | 1 | 5 | — | NEUTRAL |

Two behaviours are worth stating precisely:

- `ambiguous_competition` requests 0.5 of each pool, but `round(0.5 × 185) = 92`
  and `round(0.5 × 186) = 93`, so the fractions are 0.4973 and 0.5000. RIGHT is
  the strictly higher fraction; this is a rounding artefact of whole neurons,
  not a decoder preference for RIGHT.
- `uniform` reports all three pools and still names LEFT because 56/185 = 0.3027
  is the highest fraction. The reason field is `simultaneous_actions`, which
  flags that this is arbitration, not a biological decision.

**Every post-drive window is NEUTRAL** in every run. The decoder does not
continue an action after activity stops, which is the intended stateless
behaviour with smoothing and hysteresis disabled.

### 9.4 Jitter sensitivity

A second identical grid adds a seeded per-neuron current offset of ±25 pA.

| Measure | Count |
|---|---:|
| Runs with a changed primary sequence | 24 / 66 |
| — of which the active-set tuple also changed | 15 |
| — of which only the primary label changed | 9 |
| Runs with a changed active-set sequence | 15 / 66 |
| Runs fully identical (primary and active sets) | 42 / 66 |

Per scenario, identical sequences:

| Scenario | Identical |
|---|---|
| baseline | 6 / 6 |
| weak_left | 6 / 6 |
| weak_jump | 6 / 6 |
| ambiguous_competition | 4 / 6 |
| jump | 4 / 6 |
| left | 4 / 6 |
| right | 4 / 6 |
| right_jump | 3 / 6 |
| uniform | 3 / 6 |
| bilateral | 1 / 6 |
| left_jump | 1 / 6 |

The changes are almost entirely of two kinds:

1. **Onset shift.** At 140–160 pA a small offset pushes a subset of neurons
   above rheobase earlier, so an action appears one window sooner. This changes
   the sequence but not the identity of the active pool.
2. **Near-tie arbitration.** Bilateral, left+jump and uniform pools have active
   fractions that differ by less than a few percent, and the jitter flips which
   one is highest. The active-set tuple changes in only 15 cases, and no run
   produces an action whose pool produced no spikes.

The 24/66 figure is reported as a robustness limitation, not as noise to be
tuned away. Any change to the priority or to the tie tolerance must be declared
before, not after, such a measurement.

### 9.5 Determinism

Both conditions were executed twice with the same seed. The two repeats are
byte-identical after JSON serialisation (`determinism.identical = true`,
2 repeats × 2 conditions).

### 9.6 Runtime

| Stage | Seconds |
|---|---:|
| Experiment wall clock | 23.392 |

Results file: 538,744 bytes,
SHA-256 `9fa64fe5fc65e6868c38b28b61fff54e6cbe7622ae8860cdc028e8e3745e56bc`.

---

## 10. Part H — Deliverables

| Artifact | Path | Bytes | SHA-256 (prefix) |
|---|---|---:|---|
| Package init | `motor/__init__.py` | 217 | `17ac008ce39627b2…` |
| Populations | `motor/populations.py` | 11,856 | `6652d14cf51b3c44…` |
| Decoder | `motor/motor_decoder.py` | 17,852 | `3b1c9ce0f62c1332…` |
| Config | `configs/motor_decoder.yaml` | 3,265 | `525f25e9e0d334e5…` |
| Experiment | `experiments/phase_4f/run_decoder_experiment.py` | 19,828 | `548f04305682e008…` |
| Results | `experiments/results/phase_4f/motor_decoder_experiment.json` | 538,744 | `9fa64fe5fc65e686…` |
| Test — populations | `tests/test_motor_populations.py` | 16 tests | — |
| Test — decoder | `tests/test_motor_decoder.py` | 30 tests | — |
| Test — experiment | `tests/test_motor_decoder_experiment.py` | 6 tests | — |
| Report | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | this file | — |

The results JSON records: phase, generation timestamp, verdict, canonical ID
field, input hashes, population composition and provenance, decoder
configuration, interface probe, threshold sensitivity, experiment design,
per-run and aggregate outputs, jitter sensitivity, determinism, integrity
checks, limitations and software versions. Every run records its graph
threshold and decoder configuration.

Naming follows the existing convention: `motor/` for modules, `configs/` for
YAML, `experiments/phase_4f/` for the runner, `experiments/results/phase_4f/`
for machine-readable output and `reports/PHASE_4F_*.md` for the report.

---

## 11. Part I — Scientific interpretation

The phase keeps six kinds of claim separate.

| Claim type | Status in this phase |
|---|---|
| Published annotation | `super_class`, `side`, `body_part_effector`, `peripheral_target_type` come from the BANC v888 metadata table |
| Structural connectivity | Not used for membership and not used by the decoder; Phase 4D/4E adjacency remains separate |
| Simulated activity | Produced by the unmodified LIF model under an experimenter current, not by the connectome |
| Decoder score | Active neuron fraction of an annotation-defined pool in a declared window |
| Abstract output | LEFT, RIGHT, JUMP, NEUTRAL — computational labels |
| Biological hypothesis | None asserted; the tergotrochanter pool is a candidate, not a command |

What may be said:

- The decoder implementation behaves as specified on synthetic and controlled
  inputs.
- Left-, right-, jump-, bilateral- and simultaneous-population activity can be
  distinguished when the pools are driven.
- Subthreshold and sparse activity produce NEUTRAL.
- Threshold choice does not affect decoder membership or scores in this phase.

What may not be said:

- That LEFT/RIGHT/JUMP correspond to fly turns or jumps.
- That the 20 tergotrochanter candidates command jumping.
- That the connectome can drive the decoder, or the game, end-to-end.
- That the 25 pA jitter result estimates biological noise.
- That the response matrix is a calibration.

No plasticity, learning or weight change is introduced. No game action,
keyboard event or external process is produced.

---

## 12. Part J — Validation

### 12.1 Tests

| Suite | Result |
|---|---|
| Phase 4F focused (`test_motor_populations`, `test_motor_decoder`, `test_motor_decoder_experiment`) | **52 passed in 10.52 s** |
| Full repository suite | **397 passed in 31.42 s** |

The full suite previously contained 345 tests; Phase 4F adds 52, and none of the
existing tests were removed, skipped or weakened. A prior identical full-suite
run took 55.15 s, so wall-clock timing varies with filesystem cache state; the
test count is the stable measurement.

Two failures were found and fixed during development:

1. Three hysteresis tests placed second-window spikes outside the window; the
   fixtures were corrected to `time_ms=75.0`/`125.0`.
2. An empty-population test expected a single reason; the decoder was corrected
   to report `empty_population` alone instead of appending gate reasons.

One test expectation was also corrected to match the probe's actual wording
(`transmitter sign policy` rather than a string that never existed).

### 12.2 Integrity verification

| Check | Result |
|---|---|
| `verify_manifest` on `banc_manifest.json` | 10 checks passed, 0 failures |
| BANC threshold graphs t1/t5/t10 | hashes unchanged |
| `banc_nodes.csv.gz`, `banc_id_map.csv.gz` | hashes unchanged |
| Five raw BANC inputs | hashes unchanged |
| FAFB `connectome.npz`, `nodes.csv.gz`, `connectome_report.json`, `datasets/manifest.json` | hashes unchanged |
| Root `README.md` | `8ab6a8cc…90563`, unchanged |
| Phase 4D report | `19ebe33172b9937c…`, unchanged |
| Phase 4E report | `71c7aa48bcd01065…`, unchanged |
| Phase 4E results JSON | `c593e221dd1300a4…`, unchanged |
| Experiment-before/after input snapshot | unchanged |

`git status` shows **no staged files** and no commit or push was performed. The
only working-tree modifications are the pre-existing Phase 3B.2B.3 edits dated
2026-11-07, which this phase did not touch; all Phase 4F files are untracked.

---

## 13. Limitations

1. The BANC graph cannot be simulated by the existing `BrainSimulator` without
   a transmitter-sign and weight policy. Activity in the experiment comes from
   direct current into motor pools, not from synaptic propagation.
2. LEFT, RIGHT and JUMP are decoder labels derived from published effector
   annotations, not identified biological motor commands.
3. The tergotrochanter pool is a jump-associated candidate pool. Its 20 members
   are all leg motor neurons and eight carry `LR_TYPE_CONFLICT`.
4. 414 of 805 motor neurons are unassigned; the decoder says nothing about them.
5. Every driven neuron in a pool receives the same current amplitude; the
   experiment does not model physiological recruitment.
6. The fixed priority tie-break is not robust near equal active fractions; the
   25 pA jitter condition changes 24 of 66 primary sequences.
7. Smoothing and hysteresis are implemented and unit-tested but are not used in
   the controlled experiment.
8. ROLL and DUCK are unsupported; no proxy population was invented.
9. No Subway Surfers action, keyboard output or game control is produced or
   claimed, and the decoder was not integrated with any game code.

---

## 14. Verdict and next milestone

**Verdict: PASS WITH LIMITATIONS.**

The decoder is standalone, deterministic, documented and tested; it consumes
existing simulation output without modifying the simulator; it preserves
unassigned and unsupported annotations; it records the graph threshold in every
result; and it does not overstate what its abstract labels mean. The controlled
experiment is reproducible with a fixed seed and explicit initial conditions.

The limitations are the scientific ones above. The decisive one is that BANC
activity in this phase is experimenter-injected, so no statement about the
connectome's ability to drive the decoder is supported.

Recommended next milestone (not started): define an explicit, documented
transmitter-sign and weight policy for `BancConnectome` so the unmodified
`BrainSimulator` can propagate spikes through BANC edges, then re-run the same
decoder unchanged against propagated motor activity. That is the smallest
change that would test whether the structural graph can recruit the motor pools
at all. Phase 4G is not started in this task.

---

## 15. Reproducibility

```bash
# Focused tests
python -m pytest tests/test_motor_populations.py tests/test_motor_decoder.py \
    tests/test_motor_decoder_experiment.py -q -p no:anyio

# Full suite
python -m pytest -q -p no:anyio

# Controlled experiment (writes experiments/results/phase_4f/)
python experiments/phase_4f/run_decoder_experiment.py
```

Software: Python 3.13.14, NumPy 2.3.4, pandas 2.3.3, PyArrow 21.0.0,
Windows 11 (10.0.26200).
