# Phase 5D — Three-Factor Plasticity, Weight State and Persistence

**Status:** complete
**Date:** 2026-11-09
**Repository:** FLY-SURFER
**Preceding phase:** 5C (sparse edge-indexed eligibility traces)
**Successful:** all ten declared 5D checks pass; two limited-scope results are
recorded explicitly (Section 7.6 and Section 11)
**Scope:** separated weight layers, a bounded three-factor update rule, an
independent plastic simulator that mirrors the fixed-weight loop, checkpoints,
and the `eta = 0` equivalence contract. No biological measurement is made.

---

## 1. Purpose

Phase 5D couples the 5B reward prediction error and the 5C eligibility trace
into a declared three-factor weight change:

```
delta_w_ij = eta * delta_t * e_ij
```

The phase must satisfy the approved 5A architecture constraints:

- `brain/` stays unchanged and the fixed-weight `BancSimulator` stays available
  as the oracle;
- learned state lives in an independent `plasticity/` package and an independent
  `PlasticSimulator`;
- structural counts, initial weights, learned deltas and effective weights are
  separate layers with strict write permissions;
- bounds, sign preservation and structural immutability are enforced, not
  asserted;
- only edges with a verified sign are plastic; unknown-sign edges keep a zero
  learned delta;
- reward is an external controlled-task scalar, never derived from
  `MotorDecoder`;
- checkpoints carry graph identity and refuse mismatches;
- **`eta = 0` must reproduce the fixed-weight spike hash exactly.**

The last item is the load-bearing software contract of the phase. It is checked
on a synthetic substrate at two trace settings and on the real BANC t5 graph at
two noise levels.

---

## 2. Scientific status and non-claims

| Element | What it is | What it is not |
|---|---|---|
| weight in pA | a transformed structural synapse count | not a conductance, not a measured synaptic efficacy |
| `WeightState` | five owned arrays with declared write permissions | not a biological weight variable |
| `delta_w = eta * delta_t * e` | a computational update rule | not a biological learning law |
| `eta` | a declared learning rate | not fitted to any experiment |
| `delta_t` | the error of a declared value model | not a dopamine, octopamine or serotonin measurement |
| eligibility `e_ij` | a short-lived model tag on one edge | not a measured synaptic tag |
| bounds 0.5x–2.0x | declared modelling limits around the initial weight | not measured physiological limits |
| a nonzero learned delta | a model output | **not evidence of learning** |

No learning curve, behavioural improvement or biological plasticity claim is
made in this phase. The plastic smoke run only demonstrates that the rule,
bounds, sign channels and persistence operate as declared.

---

## 3. Implemented interfaces

| ID | Interface | Implementation |
|---|---|---|
| M06 | effective weight layer | `plasticity/weights.py`: `WeightBounds`, `WeightState`, `graph_signature` |
| M07 | update rule and constraints | `plasticity/rules.py`: `RuleConfig`, `ThreeFactorRule`, `UpdateReport` |
| M08 | checkpoint / resume | `plasticity/checkpoint.py`: `save_checkpoint`, `load_checkpoint`, `graph_checksum`, `policy_digest` |
| M09 | plastic simulator and step hook | `plasticity/engine.py`, `plastic_synapses.py`, `plastic_simulator.py` |
| M10 | diagnostics | `plasticity/diagnostics.py`: `spike_hash`, `summarize_updates`, `weight_diagnostics`, `trace_diagnostics`, `memory_breakdown` |

### 3.1 Modules

```
plasticity/weights.py            five separated weight layers, bounds,
                                 sign-channel updates, invariants, digests
plasticity/rules.py              RuleConfig, ThreeFactorRule, UpdateReport
plasticity/engine.py             trace clock, delay-matched coincidence,
                                 slot-to-CSR mapping, update cadence
plasticity/plastic_synapses.py   PlasticSignedSynapses over owned arrays
plasticity/plastic_simulator.py  PlasticSimulator, PlasticSimulationResult
plasticity/checkpoint.py         graph-bound checkpoint save/load
plasticity/config.py             configs/plasticity.yaml validation
plasticity/synthetic.py          deterministic validation fixture
plasticity/diagnostics.py        hashes, update summaries, memory accounting
configs/plasticity.yaml          weights, rule and simulation sections added
experiments/phase_5/run_plasticity_unit_experiments.py
tests/test_plasticity_weights.py      13 tests
tests/test_plasticity_rules.py         9 tests
tests/test_plasticity_simulator.py    16 tests
tests/test_plasticity_config.py        6 tests
```

`brain/`, `motor/`, `sensory/`, `perception/`, `experiments/phase_4*` and the
existing `tests/` are untouched. The package top level does not import the
simulator or `brain`; the simulator is imported explicitly from its submodule.
This preserves the 5B package-isolation invariant.

### 3.2 Weight layers and permissions

Every CSR edge carries:

| Layer | dtype | Permission | Content |
|---|---|---|---|
| `structural_count` | int32 | read-only | integer synapse count from the graph |
| `initial_exc` / `initial_inh` | float32 | read-only | copy of the policy weights |
| `delta_exc` / `delta_inh` | float32 | writable | learned change |
| `effective_exc` / `effective_inh` | float32 | writable | bounded initial + learned |
| `sign_class` | int8 | read-only | +1 excitatory, -1 inhibitory, 0 unknown |

- `plastic = (initial_exc > 0) | (initial_inh > 0)`; the plastic positions are
  stored once as an int64 index and are read-only.
- Updates are split by `sign_class`. An excitatory update touches only
  `delta_exc` / `effective_exc`; an inhibitory update touches only the `_inh`
  pair. An update on an unknown-sign edge raises.
- Bounds constrain the **effective** weight. They are shifted into delta space
  before clipping (`lower_for(initial) - initial`, `upper_for(initial) -
  initial`), so a positive update is not incorrectly clamped up to
  `lower_factor * initial`.
- `max_abs_update_pa` optionally clips the raw increment before the bound
  clamp; both events are counted separately.
- `restore_deltas` re-validates shape, finiteness, sign channel, zero delta on
  non-plastic edges and the declared bounds before writing.
- `assert_invariants` checks finiteness, zero delta off plastic edges, channel
  exclusivity, non-negative effective weights, exact layer composition and
  bounds compliance; it raises on the first failure.

### 3.3 Rule and constraints

```python
RuleConfig(eta=0.01, update_cadence="reward_event",
           weight_decay_per_ms=0.0, normalization="none",
           abort_on_sign_flip=True)
```

- `eta = 0` returns an all-zero `UpdateReport` **before** decay and before any
  array write. It does not call `decay_learned`.
- `dw = eta * delta_t * eligibility`; non-finite `dw` raises.
- Optional weight decay multiplies the learned layer by
  `exp(-weight_decay_per_ms * dt)` before the update.
- Normalization is a declared exclusion: only `"none"` is accepted, because a
  normalization step would couple edges and change the `eta = 0` contract.
- A detected sign violation aborts with `FloatingPointError` when
  `abort_on_sign_flip` is set.
- Zero eligibility leaves weights unchanged even with positive `eta`.

### 3.4 Engine and simulator

- The engine stores traces on compact plastic slots. Only at `learn` does it map
  slots back to CSR edges (`edges = plastic_positions[slots]`). Traces and
  weights therefore share one index space without an `N x N` object.
- Coincidence is delay-matched: a presynaptic packet is tagged only when the
  postsynaptic cell spikes at the packet delivery step. The delay line is the
  same uniform 1 ms (2 steps at `dt = 0.5 ms`) used by the fixed simulator.
- `PlasticSignedSynapses` re-binds the policy weight views to the owned
  `WeightState.effective_*` arrays and refuses a weight state built from a
  different structural graph (`graph_signature`).
- `PlasticSimulator.run` mirrors `BancSimulator.run` operation for operation:
  the same RNG call order, current assembly, LIF integration, spike recording
  and propagation. The additions are `engine.observe_step` after propagation
  and an optional reward-event update.
- The default rule is `eta = 0.0`; the fixed-weight pathway is the default
  configuration of the plastic simulator as well as the unchanged
  `BancSimulator`.
- `reset()` clears neurons, synapses, recorder, engine, reports and the reward
  provider, but deliberately keeps learned weights, so consecutive runs
  continue from the same learned state.

### 3.5 Checkpoints

A checkpoint stores the metadata JSON plus learned delta arrays and, when
present, trace arrays and predictor state. Loading verifies, before any
mutation:

1. `format_version`;
2. non-negative `step`;
3. `graph_checksum` against the supplied graph;
4. `policy_digest` against the supplied policy;
5. structural and initial digests against the supplied weight state;
6. the incoming delta digest against the stored `delta_digest`;
7. after restore, the delta digest again;
8. trace state, including its own digest rollback on mismatch.

Wrong-graph, wrong-policy, tampered-delta and mismatched-trace loads raise;
there is no silent partial load.

---

## 4. The `eta = 0` contract

`BancSimulator` is the oracle and was not modified. Equality is checked by
SHA-256 over the exact recorded spike times and neuron indices
(`plasticity.diagnostics.spike_hash`), not by summary counts.

Why the loop mirrors the oracle exactly:

- the RNG is created and consumed in the same order (noise draw first, only
  when `noise_std_pa > 0`);
- the same `LIFPopulation.step` and `SpikeRecorder.record` calls are used;
- `PlasticSignedSynapses.advance`, `synaptic_current_pa`, `propagate` and the
  delay buffer follow `BancSignedSynapses`;
- at `eta = 0` the trace update and the rule's `learn` still run, but the rule
  early-returns without touching either weight array;
- traces enabled and traces disabled must give the same spikes, because traces
  never feed back into the neuron or synapse state.

The equality was demonstrated, not assumed: the checks below fail if the
hashes differ or if the run produced no spikes (which would make equality
vacuous).

---

## 5. Configuration

`configs/plasticity.yaml`, SHA-256
`f4674cee4656526511e9e14d92d626bdc81f3a70abacba96d7f393251bc1ba20`
(config digest `20326602b22b517ef2bed9dfc9e0e27c121ee419b22f303fc06ef0b8633791b1`).
The 5B reward and 5C trace sections are unchanged.

| Key | Value |
|---|---|
| `weights.bounds.lower_factor` | 0.5 |
| `weights.bounds.upper_factor` | 2.0 |
| `weights.bounds.max_abs_update_pa` | 5.0 |
| `weights.bounds.absolute_min_pa` / `absolute_max_pa` | null |
| `weights.fixed_mode_eta` | 0.0 (must remain exactly zero) |
| `weights.primary_threshold` | 5 |
| `rule.eta` | 0.01 |
| `rule.update_cadence` | `reward_event` |
| `rule.weight_decay_per_ms` | 0.0 |
| `rule.normalization` | `none` |
| `rule.abort_on_sign_flip` | true |
| `simulation.dt_ms` | 0.5 |
| `simulation.duration_ms` | 100.0 |
| `simulation.tau_exc_ms` / `tau_inh_ms` | 5.0 / 8.0 |
| `simulation.delay_ms` | 1.0 |
| `simulation.background_current_pa` / `noise_std_pa` | 0.0 / 0.0 |
| `simulation.max_recorded_spikes` | 200000 |

`load_plasticity_config` rejects an unknown key, a negative or non-finite
value, an infeasible bound pair and any `fixed_mode_eta` other than exactly
`0.0`. The error text states that the `eta = 0` contract cannot be weakened.

---

## 6. Validation command

```
python -m experiments.phase_5.run_plasticity_unit_experiments
```

Result: `experiments/results/phase_5d/plasticity_unit_experiments.json`
Generated: 2026-11-09T16:31:03 UTC
Total runner wall time: **6.96 s**
Python 3.13.14 / NumPy 2.3.4 / pandas 2.3.3 / Windows 11.

Rerun verification: the runner was executed twice more after later edits to
`plasticity/weights.py` and `plasticity/plastic_simulator.py`. Both runs
reproduced every spike hash, every weight digest and all ten checks. The only
changed numbers are the reported per-event applied sums, which now derive from
the stored float32 learned deltas rather than the unbounded float64 proposal;
the difference is below 1e-8 relative and no stored weight changed.

### 6.1 Declared checks

| Check | Result | Evidence |
|---|---|---|
| `toy_rule_arithmetic` | pass | five hand-computed deltas match within 2.38e-08 pA |
| `eta_zero_no_op` | pass | zero report, zero array change, decay skipped |
| `synthetic_eta_zero_hashes` | pass | 77 spikes; identical hash with traces on and off |
| `plastic_invariants` | pass | all eight invariant flags true; sign and structural counts preserved |
| `checkpoint_round_trip` | pass | learned deltas, effective layer and traces restored |
| `checkpoint_wrong_graph_rejected` | pass | raises "checkpoint belongs to a different structural graph" |
| `checkpoint_tamper_rejected` | pass | raises "checkpoint learned deltas do not match their digest"; state untouched |
| `banc_eta_zero_hashes` | pass | 64 spikes at both noise levels; fixed and plastic hashes identical |
| `banc_conditions_produced_spikes` | pass | both conditions produced 64 spikes (equality is not vacuous) |
| `integrity` | pass | Phase 4H snapshot 37/37 unchanged |

`all_checks_passed: true`; `failures: []`.

### 6.2 Toy rule arithmetic

Synthetic state, five slots, eligibility `[1, 2, 3, 1, 0.5]`, `eta = 0.1`,
`delta_t = -2`, no decay, no clip:

| Expected delta (pA) | Applied delta (float32, pA) |
|---:|---:|
| -0.2 | -0.20000000298023224 |
| -0.4 | -0.4000000059604645 |
| -0.6 | -0.6000000238418579 |
| -0.2 | -0.20000000298023224 |
| -0.1 | -0.10000000149011612 |

Maximum absolute error: **2.3841857821338408e-08 pA** (float32 representation).
Negative prediction error reduced the excitatory weights; the `eta = 0` path
produced no change.

### 6.3 Synthetic `eta = 0` equivalence

64 nodes, 800 edges, 502 verified-sign plastic edges, seed 5. Simulation:
50 ms (100 steps), seed 7, noise 25 pA, 16 stimulated neurons at 500 pA,
reward events at steps 33 and 99.

| Condition | Spikes | Transmissions | Update events | Applied updates | Spike hash | Matches fixed |
|---|---:|---:|---:|---:|---|---|
| traces enabled | 77 | 947 | 2 | 0 | `be6e3a7f12606f1362fe4f085cd3f297041e511b32307519fc9fed5373ca23e8` | yes |
| traces disabled | 77 | 947 | 0 | 0 | `be6e3a7f12606f1362fe4f085cd3f297041e511b32307519fc9fed5373ca23e8` | yes |

`effective_equals_initial: true` in both conditions (`np.array_equal` on the
arrays). The trace store touched 9 of 502 slots (10 coincident tags, 582 edges
pushed, 565 delivered), so the equality holds with a live trace store, not with
traces bypassed.

Fixed simulator runtime: 0.012 s; plastic: 0.0147 s (traces on) and 0.0119 s
(traces off). Single run; not a benchmark.

### 6.4 Nonzero-`eta` plastic smoke

64 nodes, 800 edges, 502 plastic, 80 ms (160 steps), seed 5, noise 40 pA,
16 stimulated neurons at 500 pA, rewards `+1` at step 53 and `-1` at step 159,
`eta = 0.02`, declared bounds 0.5x/2.0x, `max_abs_update_pa = 5.0`.

| Measure | Value |
|---|---|
| spikes | 123 |
| spike hash | `152ba21fe2b90df3d55fc6538f57ba497a40d1782eeaa98c5d6a3293a162268f` |
| runtime | 0.0231 s (6,911.5 steps/s) |
| update events | 2 (both changed weights) |
| update at step 53 | 6 slots, 6 updates, `delta_t = +1`, +0.083455923013 pA total, max 0.020000000000 pA, mean eligibility 0.6955 |
| update at step 159 | 12 slots, 12 updates, `delta_t = -1`, -0.083300651051 pA total, max 0.034148123115 pA, mean eligibility 0.3471 |
| total absolute applied | 0.166756574064 pA |
| changed edges | 12 of 502 (2.39%) |
| initial weight sum | 14,148.737869 pA |
| effective weight sum | 14,148.738027 pA |
| learned delta sum | 0.000155272 pA |
| relative delta (changed edges) | mean -0.000209, min -0.004061, max 0.001375 |
| clamp hits / update clips | 0 / 0 |
| saturated edges | 0 |
| sign violations | 0 |
| structural counts immutable | true |
| sign preserved | true |
| invariant flags | all eight true |

The deltas are small because `eta = 0.02` and eligibility is order one; the
declared bounds were never approached. This is a correctness smoke test, not
an exhibition of learning.

The trace store ended with 12 touched slots, 15 coincident tags, 928 pushed and
928 delivered edges, L1 = 4.165032702, peak = 1.707406247, clock 160.

### 6.5 BANC t5 `eta = 0` equivalence

Graph: `datasets/processed/banc_v888/banc_graph_t5.npz`, SHA-256
`6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192`,
threshold 5: **172,433 nodes, 1,535,710 edges, 18,552,546 synapses,
683,100 verified-sign plastic edges**.

Simulation: 30 ms (60 steps), seed 20261114, 64 stimulated neurons at 300 pA,
reward events at steps 30 and 59, `eta = 0`.

| Condition | Fixed spikes | Plastic spikes | Fixed hash | Plastic hash | Identical | Transmissions |
|---|---:|---:|---|---|---|---:|
| no noise | 64 | 64 | `4fc92a14bbf3fd8535717b447bac54c8d43fe8e41031aa1c3f060ea8625bc30c` | same | yes | 3 |
| noise 25 pA | 64 | 64 | `b2e70eaf6d1bfb735e64962b5840bad70c54f35c639da260f4c0e441abcde38b` | same | yes | 3 |

- Graph load and policy build: 3.883 s.
- Weight-state construction: 0.0632 s (no noise) / 0.0724 s (noise).
- Run time: fixed 0.2854 s, plastic 0.4660 s (128.8 steps/s) without noise;
  fixed 0.7640 s, plastic 0.6418 s (93.5 steps/s) with noise. These are single
  runs; the noise condition is dominated by RNG generation, and no speed claim
  is made.
- 2 update events, 0 applied updates, `effective_equals_initial: true`
  (`np.array_equal`), `structural_equals_graph: true` in both conditions.
- Initial digest `8d19c706…`, effective digest `dc544f7a…`, delta digest
  `b88628a1…`. The effective digest differs from the initial digest **by
  construction** because `_digest_arrays` hashes array names as well as
  contents; array equality is verified separately with `np.array_equal`.

**Scope limitation, recorded:** this 30 ms window produces one spike per
stimulated neuron (64 spikes) and only 3 spike transmissions. The equivalence
is proven for this window, seeds and inputs, not for every possible BANC
configuration. It is a software contract, not a statement about connectome
dynamics.

### 6.6 Checkpoint experiment

24 nodes, 120 edges, seed 9; `eta = 0.05`, rewards at steps 16 and 49, 25 ms,
seed 4, three stimulated neurons.

- The run produced 2 update events but **0 changed edges**: no coincident tag
  was present at either reward step in this small fixture.
- Because an all-zero delta layer would not exercise restoration, a
  deterministic fixture update (`eta`, eligibility 1, `delta_t = 1`) was
  applied to the first four plastic edges and is recorded as
  `fixture_update_applied: true`. Four edges were saved.
- Round-trip: `true`; traces restored: `true`; checkpoint graph checksum
  `10141f9f…` equals the expected checksum; step 50.
- Wrong graph: rejected with "checkpoint belongs to a different structural
  graph".
- Tampered `delta_exc`: rejected with "checkpoint learned deltas do not match
  their digest"; the in-memory state was left untouched.

The test suite separately exercises the checkpoint with **real learned deltas
from a simulation** (24 nodes/120 edges, `eta = 0.05`, two reward events, two
updates), so the fixture is a runner safeguard, not the only evidence.

### 6.7 Numerical behaviour

- `delta_w` and restored deltas must be finite; non-finite values raise.
- Effective weights must be non-negative; a sign violation is counted and, by
  default, aborts the update.
- Effective weights are computed in float64 and stored in float32; the
  invariant check recomputes the composition in float32, so the equality is
  exact at storage precision.
- `max_abs_update_pa` clips the raw increment; the bound clamp is counted
  separately. Both counters are zero in the smoke run.
- `WeightState.apply_update` rejects duplicate or out-of-range edges and an
  update on an unknown-sign edge.
- `load_checkpoint` verifies every digest before mutating state and rolls back
  a mismatched trace restore.

---

## 7. Tests

| Suite | Result |
|---|---|
| `tests/test_plasticity_weights.py` (new) | **13 passed** |
| `tests/test_plasticity_rules.py` (new) | **9 passed** |
| `tests/test_plasticity_simulator.py` (new) | **16 passed** |
| `tests/test_plasticity_config.py` (new) | **6 passed** |
| focused Phase 5 suite (six files) | **153 passed in 3.30 s** |
| full suite | **645 passed in 34.48 s** |

The 44 new tests cover: owned copies and read-only layers; initial/effective
composition; plastic-edge selection by verified sign; bounds validation;
mismatched policy rejection; per-channel updates; bound clamping; raw-increment
clipping; slot/value validation; structural immutability; decay of the learned
layer only; restore validation; digests and description; rule validation;
strict `eta = 0` no-op including skipped decay; exact rule arithmetic; negative
prediction error; clip-before-clamp; invalid inputs; zero traces; decay before
update; byte-for-byte `eta = 0` equivalence with traces on and off;
repeatability and fixed weights; positive/negative updates only on plastic
edges with preserved signs; no reward means no change; every-step cadence;
delay-matched and delay-mismatched coincidence; traces disabled; predictor
driven error; checkpoint round-trip with traces; wrong-graph rejection; tamper
rejection; memory double-count guard; summary status and digests; config
loading and rejection; and plastic-synapse ownership and foreign-state
rejection.

No existing test was modified.

---

## 8. Resources

| Measure | Value |
|---|---|
| runner wall time | 7.09 s |
| BANC retained arrays | 78,816,128 B (75.16 MiB) |
| BANC weight state | 51,536,100 B (49.15 MiB) |
| BANC engine (traces) | 17,072,440 B (16.28 MiB) |
| BANC synapse arrays | 1,379,464 B plus 12,285,680 B shared effective weights |
| BANC delay buffer | 2,758,928 B |
| BANC spike recorder | 4,000,000 B |
| BANC trace capacity | 5,464,800 B (5.21 MiB) for 683,100 slots |
| peak process working set | 286.31 MB |
| synthetic smoke retained | 841,600 B (0.80 MiB) |
| data touched | BANC t5 graph and policy, read-only |
| Python / NumPy | 3.13.14 / 2.3.4 |

`memory_breakdown` counts the effective arrays once: they are owned by the
weight state and merely viewed by the synapse object. The retained total
subtracts that shared 12,285,680 B.

The machine is a 16 GB Windows 11 laptop; the run is a single run and the
timings are indicative, not a statistical benchmark.

---

## 9. Integrity

Phase 4H protected-file integrity: **37/37 unchanged**, including root
`README.md`, Phase 4H reports and results, datasets and processed connectomes.

No file in `brain/`, `motor/`, `sensory/`, `perception/`,
`experiments/phase_4*` or the existing `tests/` was modified. No dataset or
model artifact was written by this phase. No commit, stage or push was made.

---

## 10. Files created and modified

Created:

- `plasticity/weights.py`
- `plasticity/rules.py`
- `plasticity/engine.py`
- `plasticity/plastic_synapses.py`
- `plasticity/plastic_simulator.py`
- `plasticity/config.py`
- `plasticity/synthetic.py`
- `tests/test_plasticity_weights.py`
- `tests/test_plasticity_rules.py`
- `tests/test_plasticity_simulator.py`
- `tests/test_plasticity_config.py`
- `experiments/phase_5/run_plasticity_unit_experiments.py`
- `experiments/results/phase_5d/plasticity_unit_experiments.json`
- `reports/PHASE_5D_THREE_FACTOR_PLASTICITY.md`
- `reports/PHASE_5D_THREE_FACTOR_PLASTICITY.json`

Modified:

- `plasticity/__init__.py` (adds 5D exports; deliberately does **not** export
  the simulator, preserving the 5B package-isolation invariant)
- `plasticity/checkpoint.py` (graph-bound checkpoint implementation completed)
- `plasticity/diagnostics.py` (shared-effective-array memory accounting)
- `configs/plasticity.yaml` (adds `weights`, `rule` and `simulation` sections)

No commit or push was made.

---

## 11. Limitations

1. The synthetic substrate is a deterministic validation fixture, not a brain
   circuit. A nonzero delta there is not evidence of learning.
2. `eta = 0` equality is verified for the recorded seeds, durations, stimulation
   and noise settings only. It is not a proof for every configuration.
3. The BANC equivalence window is short (30 ms, 64 stimulated neurons, 64
   spikes, 3 transmissions). It validates the software contract, not
   connectome dynamics.
4. The runner's checkpoint case produced no changed edges from simulation, so a
   deterministic fixture update was applied to exercise restoration. The test
   suite covers the real learned-delta path.
5. The plastic smoke deltas are tiny (0.000155 pA net) and far from the bounds;
   saturation and clamp behaviour are tested synthetically but not exercised at
   BANC scale.
6. Normalization is not implemented. It is a declared exclusion because it
   would couple edges and change the `eta = 0` contract.
7. Rewards are external computational scalars. No dopamine, octopamine or
   serotonin quantity was measured or modelled.
8. Timings are single runs on one machine. No variance or confidence interval
   is claimed.
9. The fixed-weight and plastic runs share the same LIF neuron and synapse
   implementation. Equality at `eta = 0` therefore validates the plastic
   pathway and its indexing, not the correctness of the underlying neuron
   model.
10. The checkpoint format is version 1 and stores deltas and optional trace
    state; it does not store neuron membrane state, RNG state or a resumable
    simulator snapshot.

---

## 12. Exit criteria

| 5D requirement | Status |
|---|---|
| separated structural / initial / learned / effective layers | implemented and tested |
| owned mutable weight arrays | implemented; structural and initial layers read-only |
| only verified-sign edges plastic | enforced; unknown-sign updates raise |
| bounds (relative, optional absolute, optional update clip) | implemented and tested |
| sign preservation | enforced per channel; aborts on violation |
| structural counts immutable | read-only array plus invariant |
| three-factor rule `eta * delta_t * e` | implemented and hand-computed test |
| configurable learning rate | `RuleConfig.eta`, validated |
| optional decay | implemented (default 0) |
| optional normalization | declared exclusion (`none`) |
| numerical stability | finite checks, float64 compute, float32 storage |
| checkpoint round-trip | implemented and tested |
| checkpoint graph identity / wrong-graph rejection | implemented and tested |
| tamper rejection | implemented and tested |
| fixed-weight mode available | default `eta = 0`; `BancSimulator` unchanged |
| `eta = 0` exact spike-hash equivalence | verified synthetically and on BANC t5 |
| diagnostics (weights, traces, updates, memory, spike hash) | implemented |
| focused and full tests | 153 focused / 645 full passed |
| reports MD and JSON | delivered |
| 37-file integrity | pass |

Phase 5D passes its declared checks. The contract that `eta = 0` reproduces
the fixed-weight spike hashes exactly holds for every tested condition. The
recorded scope limits are carried forward to Phase 5E: nonzero weight changes
are model outputs, not learning evidence. Proceeding to Phase 5E (controlled
learning task).
