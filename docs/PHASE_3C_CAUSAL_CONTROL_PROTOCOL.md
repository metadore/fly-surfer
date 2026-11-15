# P3-T2 — Same-Graph Causal-Control Protocol (Preregistration)

Status: **preregistered, not executed.** This document fixes the scientific
question, the four conditions, the constants, the comparison partitions, the
metrics and the invalidation rules *before* the 3300.5 ms four-condition run.
The runner in `experiments/phase_3c/causal_control.py` implements exactly this
document; the machine-readable twin is `configs/causal_control_config.yaml`.
The runner validates the YAML against the repository on every invocation, so a
drift in any constant below aborts the run instead of silently changing the
experiment.

## 1. Question

Under a fixed connectome, fixed simulation parameters and a fixed initial
membrane state, does sensory stimulation produce downstream neural activity
**beyond the directly stimulated sensory neurons**, and how does that activity
depend on the kind of input that is delivered?

This phase is **infrastructure and protocol only**. No result in this document
is a scientific claim: the full experiment has not been run. Only a 100 ms
smoke window and focused unit tests were executed to validate the machinery.

## 2. What "downstream" can and cannot mean here

Every condition runs on the same 139,255-neuron FAFB brain graph, the same
synapse model, the same seed and the same initial potential. The only thing
that differs is the current injected into the 138 mapped sensory neurons. Any
difference in activity outside that set is therefore attributable to the
injected current **through this model**, not to a biological mechanism.

Three limitations are frozen into the design:

* The graph is the FlyWire FAFB v783 materialisation, not a measured
  physiological network. Synapse weights are a computational transformation of
  structural contact counts (`configs/simulation_config.yaml`), so "causal"
  means causal *within this model*.
* The chain ends at sensory current injection. No motor output, no behaviour
  and no action selection are simulated or scored.
* A difference in total spike count is not evidence of information routing.
  This phase reports counts, partitions and latencies descriptively; it does
  not run significance tests.

## 3. Conditions

All four conditions share graph, topology, synapse configuration, timestep,
duration, seed, initial potential, background current (0 pA) and noise (0 pA).
They differ only in `input_schedule` and in which features the schedule may
activate.

| ID | Frames | Active features | Purpose |
|----|--------|-----------------|---------|
| C0 | none — `input_schedule=None` | — | no-input floor |
| C1 | 100 neutral frames at 30 FPS | the 4 player-default features | stimulation *scaffold*: constant player currents only |
| C2 | the same 100 cached visual frames as C3 | the 10 non-player features | visual hold + visual event pulses, with every player-default feature explicitly disabled |
| C3 | the same 100 cached visual frames as C2 | all 14 features | full existing sensory replay |

Fixed by `CausalControlConfig.load()`:

* C0 must have `frame_source == "none"` and an empty active set, and the
  runner constructs no scheduler for it. `BrainSimulator` therefore receives
  `input_schedule=None`, which is the documented default in
  `brain/brain_simulator.py:82`.
* C1 must use `frame_source == "neutral"` and exactly the four player
  features; any other list aborts the load.
* C2 must use `frame_source == "cached"` and exactly the ten non-player
  features; it is explicitly *not* a pulses-only condition (see §7).
* C3 must use `frame_source == "cached"` with `active_features: null`, i.e. the
  scheduler's own default of every encoder.
* C2 and C3 must load the same cache file, verified by a canonical digest of
  the frame payload.

### 3.1 C0 — no input

`input_schedule=None`. With zero background, zero noise and every neuron
starting at −65 mV, this condition measures how much the network fires with no
drive at all. It is the denominator for "is anything happening?" It is expected
to be silent, but silence is *measured*, not assumed: the runner records the
total spike count and the membrane diagnostics like any other condition.

### 3.2 C1 — neutral visual scaffold

`neutral_frames(100, 30.0)` builds one `TemporalFrame` per cache frame time
(0, 33.333…, 66.667…, …, 3300 ms) from `GameState.neutral(time_ms)`: player in
the centre lane, speed 0.5, not jumping, not rolling, and no obstacle, train or
coin. The frames carry no tracks and no lifecycle events.

Only `player_lane`, `player_speed`, `jumping` and `rolling` are active. Because
the neutral state is constant, this yields the sample-and-hold component with
no pulses and no non-player current. The runner asserts the injected current is
identical on every step and matches the archived frame values
`player_lane = 800.0 pA` and `player_speed = 1096.360925 pA`.

C1 is the relevant control for "does the brain respond to *any* structured
sensory current of comparable magnitude", not for "does it respond to the
game".

### 3.3 C2 — visual hold + visual event pulses

The same cached frames as C3, with `active_features` set to exactly the ten
non-player features. This is a property of the existing scheduler, not a new
mode: `TemporalActivationScheduler` already accepts `active_features` and masks
both the sample-and-hold values and the decayed event pulses to those features
(`sensory/temporal_scheduler.py`). No scheduler semantics are changed.

Consequences that the runner verifies from the current audit:

* all four player features inject exactly 0 pA on every step;
* at least one pulse is present and injects current;
* a sample-and-hold component is present outside every pulse window, so the
  condition is not a pulses-only replay.

C2 therefore isolates the non-player visual drive. It is *not* "the same visual
input minus events": events are included. It is "the same visual input minus
the player-default channels".

### 3.4 C3 — full sensory replay

Reproduces the existing Phase 3B.2C 100-frame replay. The runner accepts this
condition only if it can reproduce the archive:

* the canonical digest of the cached frame payload equals the archived
  `temporal_sha256`;
* the scheduler signature digest equals the archived `scheduler_sha256`;
* at the full duration the spike-count hash equals the archived
  `spike_counts_sha256`.

None of these reference values is computed by this phase; all three are read
from `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`.

## 4. Frozen constants and where they come from

| Constant | Value | Source |
|----------|-------|--------|
| Connectome | `datasets/processed/connectome.npz`, SHA-256 `3f568f24…f33d8` | file; archived in `experiments/phase_3c/integration_check.py` `PROTECTED` |
| Mapping / encoder seed | 20261104 | `configs/sensory_config.yaml:18`, `:132` |
| Simulation seed | 20261106 | `experiments/phase_3b/real_sequence_replay.py:82` |
| Timestep | 0.5 ms | `configs/simulation_config.yaml` |
| Duration | 3300.5 ms = last cached frame (3300.0 ms) + 0.5 ms | `real_sequence_replay.py:666` |
| Steps | 6601 | 3300.5 / 0.5 |
| Initial potential | −65 mV | `configs/neuron_config.yaml` |
| Threshold / reset / floor | −50 / −68 / −90 mV | `configs/neuron_config.yaml` |
| Background / noise | 0 / 0 pA | this protocol; asserted by the config loader |
| Spike capacity | 30,000,000 | `real_sequence_replay.py:83` |
| Frames | 100, datasetfootage 100–199, 30 FPS, bounds tolerance 1.0 px | `real_sequence_replay.py:75-77`; `configs/causal_control_config.yaml` |
| Reference population R | 138 mapped sensory neurons | `configs/sensory_config.yaml`, per-feature counts |
| Bins | 100 ms | this protocol |
| In-process repeats | 2 per condition | this protocol |
| Subprocess repeats | C0 and C3, one fresh interpreter each | this protocol |

### 4.1 The 14 features and the 138 neurons

The registry is `GameState.features()` (`sensory/game_state.py:249`), flattened
in encoder order. There are **14 features**, of which **4 are player fields**
and therefore **10 are non-player features** (not eleven):

* player (36 neurons): `player_lane` 12, `player_speed` 12, `jumping` 6,
  `rolling` 6.
* non-player (102 neurons): `obstacle_present` 6, `obstacle_lane` 12,
  `obstacle_distance` 12, `obstacle_type` 12, `train_present` 6,
  `train_lane` 12, `train_distance` 12, `coin_present` 6, `coin_lane` 12,
  `coin_distance` 12.

Counts are declared in `configs/sensory_config.yaml:29-123` and are verified
against `SensorySetup` (`sensory/sensory_experiment.py:62`, `:138`) at load
time: 36 + 102 = 138. `CausalControlConfig.load()` rejects any split that is
not exactly 4 + 10, in that encoder order, with these sums.

### 4.2 Archived C3 reference

From `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`,
`reproducibility` block:

| Key | Value |
|-----|-------|
| `scheduler_sha256` | `1c3ab12d2afbc396da9d77215d75c4e397da3909d1767ecec5a9f24cfc608840` |
| `spike_counts_sha256` | `09611c7dc5c37d435f7713f5b0ce42b9ab90bdf2b12efeb6c91125b0e0978305` |
| `temporal_sha256` | `2a85747165f9833f73a0c5f85af5a7966b23ecc007f530a7dbc8ba8303229166` |
| `detections_sha256` | `8719fb3f70cd0ea7274ebe0b2afd9f90251664d5f57336594bc4ffc580862e9b` |
| Total spikes | 15,654,631 |
| Stimulated spikes / active | 3,710 on 72 of 138 |
| Unstimulated spikes | 15,650,921 |

The scheduler digest algorithm is copied byte-for-byte from
`real_sequence_replay.py:572`; the JSON and array digests from `:141` and
`:148`. The cache builder re-derives the frame digest and scheduler digest from
detector output without running the simulator, so the frozen input is verified
before any simulation of C2 or C3.

## 5. Comparison partitions

The stimulated population differs between conditions, so a comparison limited
to each condition's own active set would not be comparable across conditions.
Every condition is therefore scored against **two** partitions:

* **R vs outside R** — R is the fixed set of all 138 mapped sensory neurons,
  the same set in C0, C1, C2 and C3. "Outside R" is the rest of the graph.
* **A_c vs outside A_c** — A_c is that condition's own *mapped active set*
  (C0: 0, C1: 36, C2: 102, C3: 138 neurons), i.e. the neurons the condition is
  allowed to stimulate. It is not the set that happened to spike: "active
  neurons" in the metrics below always means neurons with at least one spike.

Both partitions are reported for every condition. Reports must not substitute
the local active set for R.

## 6. Metrics recorded per condition

* Total spikes; spikes inside R and outside R; spikes inside A_c and outside
  A_c; active-neuron counts for the same four partitions.
* Firing rates (spikes / neuron / second) per partition, using the actual
  simulated duration.
* 100 ms bin counts per partition.
* First and last spike time per partition; first-spike latency.
* Spikes per feature, summed over that feature's mapped neurons.
* Current-injection audit: cumulative exposure totals — `total_injected_pa_steps`,
  `hold_only_pa_steps`, `pulse_pa_steps` — are neuron-step exposures in pA·steps
  (instantaneous pA summed over stimulated neurons and steps; multiply by the
  0.5 ms step to convert to pA·ms). Instantaneous quantities — `min/max_step_current_pa`,
  `max_per_neuron_current_pa`, per-feature peak/mean — are pA delivered during a
  single 0.5 ms step. Also: number of neurons that ever received current, and the
  exact number of indices that received current outside A_c.
* Runtime, steps/second, RSS before/after/delta and the simulator's memory
  breakdown.
* Full membrane diagnostics from the simulator.

## 7. Reproducibility and hashes

Per condition the runner records: simulator spike-count hash, activity-summary
hash, current-trace hash (per-feature matrix plus injected totals), scheduler
signature hash, cache-frame digest, total spike count and first/last spike
times. The frame cache, its manifest, the config file and the nine protected
inputs are hashed in the same report.

Every condition is run **twice in the same process** and the recorded keys must
match exactly. C0 and C3 are additionally re-run in **fresh subprocesses** and
compared against the parent report. Git HEAD, branch and `git status
--porcelain` (plus staged-change presence) are written to the JSON payload and
the sidecar so the working tree is reconstructible.

The cache manifest records `matches_archived_temporal` and
`matches_archived_scheduler`; the runner refuses to use a cache whose manifest
does not match its own bytes.

## 8. Invalidation rules

A run is marked **INVALID** if any of the following holds. Every rule is
implemented in `evaluate_invalidations()` and exercised by
`tests/test_causal_control.py`.

1. `spike_capacity_exceeded` — the 30M recorder capacity was hit.
2. `non_finite_state` — the simulator reports non-finite membrane state.
3. `membrane_below_floor` / `membrane_above_threshold` — a potential left
   [−90, −50] mV beyond 1e-6.
4. `repeated_runs_differ` — the two in-process runs disagree on any recorded
   key.
5. `current_outside_active_set` — any neuron outside A_c received current.
6. `condition_definition_violation` — any per-condition check is false
   (C0 has no schedule; C1 constant player-only current; C2 excludes every
   player feature and includes both hold and pulses; C3 active set == R).
7. `protected_hash_changed` — the README, connectome, sensory/simulation/
   neuron/perception/detector configs, split manifest or detector model differ
   from the recorded hashes.
8. `initial_conditions_differ` — graph size, mapping digest, seeds, timestep,
   duration, LIF/synapse parameters or capacity differ between conditions.
9. `cached_frames_differ_between_C2_and_C3` — the two conditions did not use
   the same frame digest.
10. `c3_scheduler_signature_mismatch` — full runs only: C3's scheduler
    signature differs from the archived Phase 3B.2C value.
11. `c3_spike_counts_mismatch` — full runs only: C3's spike-count hash differs
    from the archived value.
12. `subprocess_runs_differ` — added by the driver when a fresh-subprocess
    repeat disagrees with the in-process report.

In smoke mode the C3 archive gate is not applicable (the cached frames are
truncated to the smoke window) and is reported as
`"archive_gate": "not applicable in smoke mode"`. Any other rule still applies.

## 9. Analysis policy

* **Descriptive only.** Report counts, rates, partitions, bins and latencies.
  No p-values, no effect sizes, no significance language.
* **Both partitions, always.** R-vs-outside-R answers "is anything downstream
  active at all"; A_c-vs-outside-A_c answers "how much of the activity is on
  the neurons we drove". Neither replaces the other.
* **No additivity assumption.** C3 is not C1 + C2. C2 removes the player
  channels that C3 has; C1 has no visual objects. The reported contrasts are
  C1−C0, C2−C0, C3−C0, C2−C1 and C3−C1, and the payload states explicitly that
  these differences are not additive decompositions.
* **Silence is a result.** If C0 is silent, that is the no-input floor and must
  be reported as measured, not as a failed run.
* **No mechanism claims.** A difference outside R is a difference in this
  model's spike counts. It is not evidence of a biological pathway, of
  information routing, or of behaviour.

## 10. Scope

In scope: the runner, the config, this protocol, focused tests, the frozen
frame cache, and short smoke runs used to validate them.

Out of scope for this phase: executing the 3300.5 ms four-condition experiment;
training or calibration; changing the connectome; changing the LIF or synapse
model; changing scheduler semantics; touching Phase 4, 5 or 6; editing the root
README; replacing or deleting any existing result.
