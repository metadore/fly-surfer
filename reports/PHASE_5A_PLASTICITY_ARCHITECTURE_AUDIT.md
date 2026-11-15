# Phase 5A — Plasticity architecture audit and design

**Status:** design only. No reward signal, eligibility trace, weight update or
plasticity mechanism is implemented in this phase. No simulator, experiment,
config, dataset or completed report is modified.

**Date:** 2026-11-09
**Repository:** `C:/Users/Hp/fruitfly/FLY-SURFER`
**Machine-readable counterpart:** `reports/PHASE_5A_PLASTICITY_ARCHITECTURE_AUDIT.json`

---

## 1. Purpose and scope

Phase 5 introduces reward-modulated synaptic plasticity. Phase 5A is the
gate before any implementation. Its job is to answer, from the repository as it
actually exists:

1. what the current simulation architecture is;
2. which components can be reused without modification;
3. which interfaces are missing;
4. what the plasticity design should be;
5. which scientific assumptions that design makes;
6. how the design could break the existing system;
7. how it must be tested;
8. in what order it should be implemented.

The phase therefore produces exactly two artifacts, this report and its JSON
counterpart. It implements no learning. It stops at GATE 1 and waits for
approval before Phase 5B.

Phase 5 is gated in the order **5A → 5B → 5C → 5D → 5E → 5F → 5G**. This
report does not start 5B and does not create a Phase 4I.

### 1.1 Repository rules in force

- The root `README.md` is never modified.
- Existing datasets and processed connectomes are preserved.
- Completed Phase 4 reports and results are not overwritten.
- The Phase 4H experiments are not modified to improve their outcomes.
- The original fixed-weight simulator behaviour does not change by default.
- `git add .` and `git add -A` are never used; only explicitly intended files
  are staged.
- Nothing is committed or pushed without explicit authorization.
- Existing experiment outputs are not deleted.
- Large datasets are not downloaded without approval.
- No unnecessary dependency is introduced.
- Backward compatibility is preserved wherever possible.
- Simulation defaults do not change silently.
- FAFB and BANC graphs are never combined by assuming neuron IDs correspond.
- BANC predicted neurotransmitters are not treated as verified physiology.
- Learned weights are kept separate from original structural synapse counts.
- The original structural connectome is never altered to represent learned
  weights.
- The Phase 4H.4 negative result is preserved: its results are not modified,
  its conclusions are not rewritten, and the pathway is not presented as
  functional.

### 1.2 Scientific status of this document

This is an architecture document, not an experiment. It reports no new
simulation result. It proposes interfaces and constraints for a computational
model. It does not claim that any proposed mechanism exists in a fly, that a
weight change is learning, or that a decoder label is a motor command.

---

## 2. Scientific non-claims

These statements are binding on Phases 5B–5G as well.

- No reward signal, eligibility trace or weight update is implemented in
  Phase 5A.
- No biological dopamine, neuromodulator, receptor or plasticity mechanism is
  modelled.
- A computational reward is not a biological reward.
- A prediction error is a model variable, not a measured neural signal.
- A weight change is not evidence of learning.
- Synthetic-task improvement would not demonstrate Subway Surfers performance.
- LEFT, RIGHT and JUMP are decoder labels, not identified biological motor
  commands; ROLL and DUCK remain unimplemented.
- Phase 4H.4 did not demonstrate a functional sensory-to-motor pathway, and
  this document does not reinterpret it.
- FAFB and BANC are separate datasets with separate graphs; identities are
  never merged.
- Predicted BANC neurotransmitters are not verified physiological facts.
- Structural synapse counts are not conductances.
- Learned weights must never be written into, or presented as, the structural
  connectome.
- Determinism is not robustness, and a single seed is not evidence.
- No claim of biological realism, biological learning or behavioural
  competence is made by this architecture.

---

## 3. Existing architecture

### 3.1 Two independent simulation stacks

The repository contains two stacks that share the neuron model, the spike
recorder and the observation layer, but not a graph or an identity space.

| | FAFB stack | BANC stack |
|---|---|---|
| Entry point | `brain/brain_simulator.py` | `brain/banc_simulator.py` |
| Graph | `brain/subgraph.py::GraphView` | `brain/banc_graph.py::BancConnectome` |
| Synapses | `brain/synapse_model.py::SynapseModel` | `brain/banc_simulator.py::BancSignedSynapses` |
| Weights | derived from integer edge weights and a configured transform | `BancSynapsePolicy` exc/inh float32 arrays built from annotations |
| Neurons | `brain/neuron_model.py::LIFPopulation` | same class |
| Recorder | `brain/neural_activity.py::SpikeRecorder` | same class |
| Plasticity | none | none |

The BANC graph at the primary threshold (5) has **172,433 nodes, 1,535,710
edges and 18,552,546 synapses**. The verified-only sign policy yields
**683,100 signed edges (44.4811%)**. These figures are facts about the stored
artifact, not properties of a biological circuit.

Phase 5 targets the **BANC stack**. The FAFB stack is not the substrate for
Phase 5 learning and must remain behaviourally frozen.

### 3.2 The integration step loop

`BancSimulator.run` at `brain/banc_simulator.py:440-483` executes, in order:

1. `synapses.advance()` — decay existing excitatory and inhibitory currents and
   deliver the delayed spike packet (`banc_simulator.py:169-182`);
2. build `current = noise + background + synaptic + stimulation`;
3. `input_schedule.apply(step, step * dt_ms, current)` adds scheduled current
   in place (`banc_simulator.py:463-464`);
4. `spikes = neurons.step(current)` returns the indices of neurons that fired
   (`neuron_model.py:122`);
5. `recorder.record(step, spikes, dt_ms)`;
6. `synapses.propagate(spikes)` routes spikes into the delay buffer
   (`banc_simulator.py:184-221`).

Two consequences matter for plasticity:

- **Both spike sets are available at the loop boundary.** The presynaptic
  spikes are the argument to `propagate`; the postsynaptic spikes are the
  return value of `neurons.step`. No neuron API change is needed.
- **Per-edge attribution is missing.** `propagate` computes the active edge
  index internally at `banc_simulator.py:199-205` but returns only a
  transmission count. An eligibility mechanism needs that index vector.

### 3.3 Interfaces relevant to plasticity

| Interface | Contract | Source | Plasticity relevance |
|---|---|---|---|
| input schedule | `apply(step, time_ms, current_pa) -> None`, mutates in place; `stimulated_indices` | `sensory/temporal_scheduler.py:255`, `brain/banc_sensory_adapter.py` | reusable as an input driver; not a reward source |
| neuron step | `LIFPopulation.step(current_pa) -> ndarray[int]` | `brain/neuron_model.py:122` | supplies pre- and post-spike sets |
| synaptic propagation | `propagate(spike_indices) -> int` | `brain/synapse_model.py:192`, `brain/banc_simulator.py:184` | insufficient for per-edge credit assignment |
| activity adapter | `BancActivityAdapter(...).decode(decoder, start_ms, end_ms)` | `brain/banc_simulation_adapter.py:46-102` | read-only outcome measurement |
| decoder | `MotorDecoder.decode_window / decode_series / decode_recorder` | `motor/motor_decoder.py:241-341` | diagnostic only; never the primary reward |

### 3.4 Weight lifecycle and the aliasing hazard

1. `BancConnectome` stores integer edge synapse counts (`edge_weight`, int32)
   and CSR indices. It is built once and loaded read-only.
2. `build_synapse_policy(...)` at `brain/banc_synapse_policy.py:354` produces
   float32 `edge_exc_weight` and `edge_inh_weight`. In the primary policy the
   sign comes from **verified annotations only**; unknown-sign edges carry
   zero.
3. `BancSignedSynapses.__init__` assigns
   `self.edge_exc_weight = policy.edge_exc_weight` and
   `self.edge_inh_weight = policy.edge_inh_weight`
   (`brain/banc_simulator.py:107-108`). The docstring at lines 77-78 states
   explicitly that the arrays are **shared with the policy, not copied**.
4. `propagate` reads those arrays but never writes them. They are immutable by
   convention only: there is no write protection and no API boundary.

This is the single most important integration fact in the audit. Any plasticity
implementation that updates `self.edge_exc_weight` in place would silently
corrupt the shared policy object and every subsequent run that reuses it. The
design below therefore **copies** weights into an owned layer and never writes
to the policy or the graph.

### 3.5 Determinism and observation

- Each run constructs a fresh `np.random.default_rng(seed)` at
  `brain/banc_simulator.py:404`. The simulator loop does not use a global RNG.
- `SpikeRecorder.record` writes float32 times at `(step + 1) * dt_ms`.
- Phase 4H records `spike_hash` and `decision_hash` for every condition, so any
  change in RNG draw order or float accumulation order changes published
  hashes even when no learning occurs.
- Edge ordering is fixed by the CSR layout. Any update vector must follow the
  same ordering.

### 3.6 Observation layer and the preserved negative result

`MotorPopulations` defines LEFT (185), RIGHT (186), JUMP (20), motor (805) and
unassigned (414). The decoder uses 50 ms half-open windows, step 50 ms,
activation 0.20, release 0.10, at least 3 active neurons and 5 spikes, with a
deterministic LEFT/RIGHT/JUMP priority.

Phase 4H.4 produced **0 non-stimulated spikes, 0 second-hop spikes, 0
descending spikes, 0 motor spikes and 67/67 NEUTRAL decoder windows**. This is
a negative result about the tested pathway. Phase 5 does not reinterpret it,
and Phase 5E must not use that pathway as evidence that a sensory-to-motor
route works.

---

## 4. Reusable components

| Component | Reuse | Constraint |
|---|---|---|
| `LIFParameters`, `LIFPopulation` | unchanged | membrane state stays independent of traces and reward |
| `SpikeRecorder` | unchanged | observation log, not a training buffer |
| `BancConnectome` CSR arrays | read-only | `edge_weight` is a structural count and is never rewritten |
| `BancSynapsePolicy` | read-only initial-weight source | plasticity copies the arrays; policy stays byte-identical |
| `BancSignedSynapses` | reference implementation / subclass base | must re-bind to owned copies after `super().__init__` |
| `BancSimulator` | fixed-weight reference and golden oracle | no default behaviour change |
| `BancActivityAdapter` | unchanged | diagnostic only |
| `MotorPopulations` | unchanged | labels are not biological motor commands |
| `experiments/phase_4h/common.py` | selective | `execute()`, `World`, `condition_metrics` and the statistics helpers are reusable; `execute()` has no plasticity hook and must not be edited |
| Phase 4H integrity pattern | pattern only | a new Phase 5 baseline is created; the 4H baseline is not edited |

The statistics helpers — `summary_stats`, `wilson_interval`, `bootstrap_ci`,
`cliffs_delta`, `empirical_p_greater`, `empirical_p_two_sided`,
`empirical_percentile`, `hedges_g`, `holm`, `permutation_test` — are directly
reusable for Phase 5F and avoid re-implementing inference code.

---

## 5. Missing interfaces

| ID | Missing | Proposed contract | Phase |
|---|---|---|---|
| M01 | reward signal representation | `RewardProvider.step(step, time_ms, context) -> float`; positive, negative, zero and delayed reward, configurable magnitude and timing, finite and unit-documented, per-run digest | 5B |
| M02 | reward predictor and RPE | `RewardPredictor.value(step, state, context) -> float`; `delta_t = r_t + gamma * V(s_next) - V(s_t)`; configurable and separate from plasticity | 5B |
| M03 | reward and learning log schema | per-step timestep, reward, predicted reward, prediction error, configuration and seed | 5B |
| M04 | eligibility store | `decay(dt)`, `accumulate(pre, post, edge_index)`, `value(edge_index)`, `reset()`, `memory_bytes`, `sparsity_report()`; edge-indexed, never N×N | 5C |
| M05 | trace benchmark and sparse-index contract | measured memory, runtime, update complexity, storage and reset behaviour; edge mapping asserted against the CSR layout | 5C |
| M06 | effective weight layer | `WeightSet(structural_pa, initial_pa, learned_delta_pa, effective_pa, sign_class, bounds)`, immutable structural arrays, `digest()` | 5D |
| M07 | update rule and weight constraints | `ThreeFactorRule.update(...) -> UpdateReport` with configurable `eta`, min/max weight, optional decay and normalization, clipping, numerical safety and sign preservation | 5D |
| M08 | checkpoint / resume | save learned weights, optional traces, predictor state, config and graph checksum; refuse on mismatch | 5D |
| M09 | plastic simulator and step hook | `PlasticSimulator.run()` mirroring the fixed loop, plus per-edge attribution from `propagate` | 5D |
| M10 | diagnostics | trace mass, weight drift, saturation, clamp hits, sign flips, timing and memory | 5D |
| M11 | controlled task, split and controls | explicit states, actions, reward function and success metric; disjoint train/eval seeds; conditions A–G or justified exclusions; outcome independent of the decoder | 5E |
| M12 | comparison and robustness statistics | pre-registered schema with effect size, CI, Holm-adjusted p-value and a robustness grid; no timestep treated as an independent sample | 5F |
| M13 | provenance for learned artifacts | dataset, graph checksum, policy and config digests plus a model-output label | 5D–5G |

No interface above exists today in any form.

---

## 6. Recommended Phase 5 architecture

### 6.1 Design principles

1. **Fixed-weight behaviour is the default and the reference.** Plasticity is
   opt-in and lives outside `brain/` wherever possible.
2. **Structural counts and initial transformed weights are immutable.** The
   learned weight is a separate layer.
3. **Zero learning must be bit-identical to the fixed-weight pathway** for the
   same seed and inputs.
4. **Reward is a computational scalar from an external task.** It is not
   dopamine and not a biological reinforcement signal.
5. **Eligibility traces are a model of short-lived synaptic tagging**, not a
   measured synaptic state.
6. **Sign is preserved by construction.** A structural excitatory edge never
   becomes inhibitory.
7. **Only verified-sign edges are plastic.** Unknown-sign edges carry zero and
   stay zero.
8. **Train and evaluation are separated by seed**, and no evaluation seed is
   used for an update.
9. **Every run is reproducible from recorded state**: config, dataset, policy,
   initial weights, RNG streams and final weights.

### 6.2 Module map

```
plasticity/
  __init__.py            exports only                                  5B
  reward.py              reward signal + predictor + RPE + logging    5B
  traces.py              EligibilityStore, edge-indexed sparse trace  5C
  weights.py             WeightSet, bounds, sign masks, digests        5D
  rules.py               ThreeFactorRule, constraints, clipping        5D
  checkpoint.py          weights, traces, predictor, graph checksum    5D
  engine.py              PlasticityEngine orchestration                5D
  plastic_synapses.py    PlasticSignedSynapses (owned copy + attribution) 5D
  plastic_simulator.py   PlasticSimulator loop                         5D
  diagnostics.py         JSON-serialisable measurements                5D
  tasks.py               controlled task, seed splits, controls        5E

configs/plasticity.yaml  declared a priori parameters, by section
experiments/phase_5/     per-step runners, pre-registration, results,
                         analysis and plots
tests/                   one focused module per new layer
```

Each module is introduced in its own step and tested before it is coupled to
the simulator: reward in 5B, traces in 5C, weight state, rule, persistence and
simulator integration in 5D, the controlled task in 5E.

### 6.3 Weight state (5D)

Five layers, with strict write permissions:

| Layer | dtype | Writable | Meaning |
|---|---|---|---|
| `structural_count` | int32 | no | integer synapse count from the graph |
| `structural_pa` | float32 | no | transformed policy weight |
| `initial_pa` | float32 | no | copy of `structural_pa` at run start |
| `learned_delta_pa` | float32 | yes | additive learned change |
| `effective_pa` | float32 | yes | clipped `structural_pa + learned_delta_pa` |

Invariants:

- structural, initial and policy arrays are never written after construction;
- `learned_delta_pa` is zero on every edge excluded by the sign policy;
- an excitatory edge never has negative `effective_pa`, and an inhibitory edge
  never has positive `effective_pa`;
- `effective_pa` stays in `[0.5 × initial_pa, 2.0 × initial_pa]` for every edge
  with a nonzero initial weight;
- clipping is reported, not hidden;
- the sum and maximum absolute update are recorded each step.

The 0.5–2.0 range is a **declared a priori modelling choice**. It is not
measured, and it must not be tuned against any evaluation result.

### 6.4 Eligibility traces (5C)

- One float32 value per plastic edge, in CSR edge order.
- Decay: `e_ij(t) = lambda * e_ij(t-1)` with
  `lambda = exp(-dt_ms / tau_e_ms)`; `tau_e_ms` is declared in config.
- Accumulation on edges whose presynaptic neuron fired, paired with
  postsynaptic spikes under a **declared coincidence convention**.
- **Recommended convention: delay-matched.** The simulator delivers a
  presynaptic spike after the configured delay (1 ms, two steps at 0.5 ms), so
  a presynaptic spike at step `t` is paired with postsynaptic spikes at the
  step where the packet is delivered. This must be validated on a two-neuron
  hand-computed case. Same-step pairing is an alternative but must not be left
  implicit.
- Storage: a dense per-edge float32 trace is
  `1,535,710 × 4 = 6,142,840 bytes` (about 5.86 MiB). Per-neuron traces are
  negligible.
- Cost control: dense decay of every edge every step is about **921 million
  element updates per 300 ms run** (600 steps). The recommended default is
  lazy decay with per-edge timestamps, plus reward-driven updates only at
  reward events. Both strategies are benchmarked in Phase 5C before the default
  is fixed.

### 6.5 Reward signal and prediction error (5B)

- **Reward representation:** positive, negative, zero and delayed reward, with
  configurable magnitude and timing. Values must be finite and bounded, and
  the units are those of the controlled task, not dopamine.
- **Primary signal:** a task outcome independent of `MotorDecoder`. Rewarding
  the decoder's own output would optimize the measurement and make the
  experiment circular.
- **Predictor:** a configurable, separate module estimates `V(s)`. The
  prediction error is `delta_t = r_t + gamma * V(s_{t+1}) - V(s_t)`; `gamma`,
  the state representation and the value-update rule are declared a priori.
  The temporal-difference form is one model of reward prediction, not the only
  biologically plausible one.
- **Separation:** the predictor and reward provider do not import or depend on
  the plasticity rule, the eligibility store or the motor decoder.
- **Logging:** every step records timestep, reward, predicted reward,
  prediction error, reward configuration and seed.
- **Prohibited sources:** decoder labels as primary reward; any biological
  neuromodulator measurement (unavailable); Phase 4H sensory event labels
  presented as verified reward predictors.
- **Validation:** finite, bounded, unit-documented, with a per-run reward
  digest and deterministic output for fixed inputs.

### 6.6 Three-factor update rule and constraints (5D)

```
Delta_w_ij = eta * delta_t * e_ij(t)
```

applied to `learned_delta_pa`, then bounded and sign-clipped. The rule consumes
an eligibility value and a prediction error; it does not hardcode reward
polarity or synaptic sign, and it does not import the motor decoder.

Updates are applied at **reward events** by default, using the accumulated
prediction error; the cadence is configurable. This keeps the per-step cost off
the full edge set.

Configurable constraints:

- learning rate `eta`;
- absolute minimum and maximum weight;
- relative bounds `lower_factor` and `upper_factor` around the initial weight;
- optional weight decay (default disabled);
- optional normalization (default none);
- update clipping;
- numerical safety checks and abort on non-finite state;
- sign preservation for baseline magnitude plasticity.

`tau_e_ms`, `gamma` and an optional post-rate baseline constant are declared in
the same configuration file.

**Zero-reward contract:** zero reward with zero prediction error produces zero
update.

**Zero-learning contract:** `eta = 0` must reproduce the structural weights and
the fixed-weight spike hash for the same seed and inputs.

A nonzero update is not evidence of learning. Only held-out task improvement
over matched controls can support that claim.

### 6.7 Integration mode

**Recommended:** a separate `PlasticSimulator` in
`plasticity/plastic_simulator.py` that mirrors
`brain/banc_simulator.py:440-483` and composes `LIFPopulation`,
`SpikeRecorder`, `PlasticSignedSynapses` and `PlasticityEngine`.

Why not patch the core first: the fixed-weight loop is a validated artifact
with published spike hashes. Duplicating the loop in a new package leaves
`brain/` untouched and makes equivalence directly testable. If duplication
later becomes a maintenance risk, a keyword-only optional hook with a `None`
default can be considered, but that requires separate approval and a
bit-identical regression test. It is not part of 5A.

`PlasticSignedSynapses` subclasses `BancSignedSynapses`, calls
`super().__init__`, then re-binds `edge_exc_weight` and `edge_inh_weight` to
owned copies. Its `propagate` reproduces the parent arithmetic exactly and
additionally exposes the active `edge_index` for trace accumulation.

### 6.8 Checkpointing and provenance (5D)

A checkpoint contains the learned delta or effective weights, eligibility
traces when the checkpoint requires them, the reward predictor state, the
learning configuration, the seed and RNG stream states, experiment metadata,
the initial weight digest, the structural graph checksum, the policy digest,
the phase identifier and code version, and an explicit label that learned
weights are model outputs.

Loading verifies that the saved state belongs to the correct graph and refuses
on any digest or checksum mismatch. There is no silent partial load.

### 6.9 Diagnostics and cost

Per step: trace L1, trace nonzeros, mean and maximum absolute update, clamp
hits, sign flips.

End of run: relative weight-drift distribution, saturation fraction, effective
weight range, spike hash, weight digest, wall time and peak memory.

Abort criteria are declared before the run: non-finite weight or trace, any
sign flip, non-finite membrane or current, or firing rate above a declared
ceiling.

Estimated memory: four float32 arrays over all edges are about 23.4 MiB; over
only signed edges about 10.4 MiB. These are estimates: Phase 5C benchmarks trace
cost, and Phase 5D measures a full plastic run.

### 6.10 Experimental strategy (5E–5F)

**Substrate.** The first learning experiments use controlled synthetic inputs and
outputs. They do not depend on the unproven Phase 4H sensory-to-motor pathway,
and they do not treat that pathway as evidence. FAFB and BANC remain separate;
BANC data is not forced into the FAFB simulator without a validated adapter.

**Primary task (5E).** One task is chosen before any run from: input-to-action
association, delayed-reward association, a two-choice task, or a simple
sequential decision task. The written justification must cover why the task can
distinguish the plasticity rule from its controls. The task has explicit input
states, defined actions, a known reward function, a measurable success
condition and repeatable episodes.

**Conditions (5E).**

| Label | Condition |
|---|---|
| A | fixed-weight network |
| B | plastic network with reward modulation |
| C | plastic network with zero reward |
| D | plastic network with shuffled rewards |
| E | plastic network with randomized connectivity |
| F | plastic network with disabled eligibility traces |
| G | an appropriate non-biological learning baseline, if feasible |

Conditions that cannot be implemented fairly are documented as excluded rather
than approximated.

**Metrics (5E).** Episode reward, task success rate, action accuracy, learning
curve, episodes to criterion, synaptic weight changes and distribution,
eligibility trace statistics, reward prediction error, simulation runtime and
memory usage.

**Design (5E).** Multiple independent seeds; training and evaluation separated;
training performance never reported as generalisation; identical task
conditions across comparable groups; the fixed-weight baseline preserved.

**Learning verification.** An improvement is only described as learning if it
is repeatable, greater than matched controls, dependent on reward, dependent on
eligibility traces, stable across seeds and retained during evaluation. If
learning does not occur, the negative result is reported; success criteria are
not changed after seeing results.

**Comparison (5F).** Biological-connectome-derived fixed and plastic networks,
random-connectivity fixed and plastic controls, and a conventional learning
baseline where a fair comparison is possible. Inputs, outputs, training budgets
and evaluation protocols are kept comparable.

**Robustness and statistics (5F).** Sensitivity to learning rate, eligibility
time constant, reward magnitude, weight limits, initial weights, network size,
connectivity threshold and reward delay. Report mean, standard deviation,
median, confidence intervals, effect size, appropriate tests, the number of
independent runs and multiple-comparison correction. No timestep from one
simulation is treated as an independent sample. Silent, unstable or ineffective
configurations are reported, not discarded.

---

## 7. Scientific assumptions

| ID | Assumption | Status |
|---|---|---|
| A01 | The existing LIF and exponential synapse dynamics remain valid for a plastic network | assumption; the neuron itself is unchanged |
| A02 | A scalar computational reward can stand in for a reinforcement signal | computational convention; no neuromodulator physiology |
| A03 | A short-lived eligibility trace is a useful model of synaptic tagging | model assumption; `tau_e` is declared |
| A04 | A three-factor product of eligibility and prediction error is adequate | model assumption; not a biological validation |
| A05 | Sign preservation is the correct constraint | design decision; avoids inventing sign changes from annotation priors |
| A06 | 0.5×–2× relative bounds are reasonable | modelling choice; not measured |
| A07 | Only verified-sign edges are plastic in the primary condition | consequence of the Phase 4G.2 policy |
| A08 | Transformed synapse counts are an acceptable initial scale | modelling choice; counts are not conductances |
| A09 | A synthetic task with disjoint train/eval seeds is an appropriate first test | experimental design; not Subway Surfers |
| A10 | Uniform 1 ms delay is adequate for delay-matched pairing | model limitation; per-edge delay is unavailable |
| A11 | The candidate subgraph is an acceptable learning substrate | inherited limitation; boundary edges are cut |
| A12 | Deterministic replay is sufficient for reproducibility | engineering assumption; determinism is not robustness |

---

## 8. Integration risks

| ID | Risk | Severity | Mitigation | Test |
|---|---|---|---|---|
| R01 | In-place learning corrupts the shared policy arrays (`banc_simulator.py:107-108`) | high | owned copy, read-only flags, digest before/after | policy and structural digests unchanged; writes raise |
| R02 | Fixed-weight reference behaviour changes | high | separate loop; `eta = 0` equivalence | identical spike and decision hashes |
| R03 | RNG draw order changes | high | separate `SeedSequence` child streams; never draw from the simulator RNG | same seed twice gives identical digests |
| R04 | Dense trace decay too expensive at 1.5 M edges | medium | lazy or sparse decay; updates at reward events | measured time and memory against a declared budget |
| R05 | Delay misattribution of pre/post pairs | high | declare and test delay-matched pairing | hand-computed two-neuron case |
| R06 | Reward derived from the decoder is circular | high | external synthetic task outcome; decoder is diagnostic only | reward stream does not import `MotorDecoder` |
| R07 | Credit assignment crosses the subgraph cut | medium | plastic edges are internal only; report counts | endpoint and edge-count assertions |
| R08 | Reward scale interacts with pA weights | medium | declared `eta`, clip and bounds; firing ceiling | clip and saturation tests |
| R09 | Train/eval leakage | high | disjoint seed pools fixed before running | empty seed intersection; eval cannot write |
| R10 | Learned weights mistaken for connectivity | high | separate files and fields; provenance label | schema requires label; graph SHA unchanged |
| R11 | Phase 4H artifacts or README modified | high | new output directories and a new baseline | 4H integrity 37/37; git diff clean |
| R12 | Float reproducibility differs across machines | low | avoid BLAS for per-edge updates; record digests | same-machine repeat; documented caveat |

---

## 9. Test strategy

The strategy is contract-first: each layer is tested before it is coupled to
the simulator, and every numerical claim gets a hand-computed case. Every
learning claim is tested against zero-reward, shuffled-reward, frozen-weight,
randomized-connectivity and disabled-eligibility controls where feasible.

| Tier | Phase | Coverage |
|---|---|---|
| T01 reward signal and RPE | 5B | positive, negative, zero, delayed and repeated reward; configurable magnitude and timing; hand-computed `delta_t`; prediction convergence; numerical stability and boundaries; deterministic output; required log fields; predictor separate from plasticity; no structural change |
| T02 eligibility traces | 5C | creation and edge mapping; accumulation; closed-form decay; reset; no activity, pre-only, post-only and coincident activity; delayed-reward compatibility; sparse index consistency; fixed-seed reproduction; numerical stability |
| T03 trace benchmark | 5C | measured memory, runtime, update complexity, storage and reset behaviour; no N×N matrix is allocated |
| T04 weight state and persistence | 5D | structural, initial, learned and effective layers are separate; read-only structural arrays; absolute and relative bounds; sign preservation; zero learned delta on excluded edges; checkpoint round-trip including traces and predictor; wrong-graph refusal |
| T05 three-factor rule and constraints | 5D | hand-computed `eta * delta * e`; positive, negative and zero reward; no eligibility means no update; delayed reward; learning-rate sensitivity; min/max weight; optional decay and normalization; clipping; sign preservation; checkpoint reproducibility |
| T06 simulator equivalence | 5D | `PlasticSignedSynapses` versus `BancSignedSynapses` currents at every step; `PlasticSimulator` versus `BancSimulator` spike hash, decision hash and summary counters at `eta = 0`; identical transmission counts and exposed edge indices; the fixed-weight path remains available and unchanged |
| T07 controlled task, split and controls | 5E | explicit states, actions, reward function and success metric; disjoint train/eval seeds; evaluation cannot write; conditions A–G implemented or exclusions justified; reward does not import the decoder; required metrics recorded |
| T08 comparative statistics and robustness | 5F | independent seeds, no timestep treated as a sample; mean, SD, median, CI and effect size; multiple-comparison correction; sensitivity to learning rate, `tau_e`, reward magnitude, weight limits, initial weights, network size, threshold and reward delay; silent or unstable configurations reported |
| T09 final validation | 5G | the ten Phase 5 scientific questions answered separately from software status; focused tests, full suite, configuration validation and checkpoint round-trip; determinism and numerical stability; report and JSON agree |
| T10 regression and integrity | 5B–5G | full existing suite; focused Phase 4H subset; 4H integrity 37/37 including README; structural connectomes, datasets and Phase 4 reports byte-identical; no unintended tracked-file change; model artifacts not staged |

### 9.1 Verification performed for Phase 5A

- Focused Phase 4H/BANC tests: **68 passed in 6.32 s**
  (`test_phase_4h5_assessment.py`, `test_phase_4h_runners.py`,
  `test_banc_simulator.py`, `test_banc_synapse_policy.py`,
  `test_phase_4h4_analysis.py`).
- Full suite: **492 passed in 56.94 s**.
- Phase 4H protected-file integrity: **37/37 unchanged**, including
  `README.md`, the Phase 4 reports and results, the datasets and the processed
  connectomes.
- Working tree: the only changes made by Phase 5A are the two new report
  files; no source, config, test or data file is modified by this phase. The
  modified Phase 3B/3C files and untracked Phase 4 artifacts visible in `git
  status` pre-date Phase 5A and are untouched.

---

## 10. Implementation sequence

| Phase | Work | New modules and artifacts | Exit criteria |
|---|---|---|---|
| 5A | this audit and design | the two reports only | approval at GATE 1 |
| 5B | reward signal and reward prediction error | `plasticity/reward.py`; reward and predictor sections of `configs/plasticity.yaml`; `experiments/phase_5/run_reward.py`; `tests/test_plasticity_reward.py`; 5B report MD and JSON | T01, T10; deterministic reward and correct RPE |
| 5C | eligibility traces | `plasticity/traces.py`; trace section of the config; `experiments/phase_5/benchmark_traces.py`; `tests/test_plasticity_traces.py`; 5C report MD and JSON | T02, T03, T10; sparse storage benchmarked |
| 5D | three-factor plasticity, weight state and persistence | `plasticity/weights.py`, `rules.py`, `checkpoint.py`, `engine.py`, `plastic_synapses.py`, `plastic_simulator.py`, `diagnostics.py`; weight and rule config sections; `experiments/phase_5/run_plasticity_unit_experiments.py`; `tests/test_plasticity_weights.py`, `tests/test_plasticity_simulator.py`; 5D report MD and JSON | T04, T05, T06, T10; all ten required 5D experiments reported |
| 5E | controlled learning experiments | `plasticity/tasks.py`; `experiments/phase_5/controlled_task.py`, runner, analysis and plots; `configs/plasticity_task.yaml`; raw results; `tests/test_plasticity_task.py`; 5E report MD and JSON | T07, T10; train/eval separated; conditions A–G or justified exclusions; negative results preserved |
| 5F | fixed-weight versus plastic comparison | comparison and robustness runners; statistical analysis; figures; reproducibility metadata; 5F report MD and JSON | T08, T10; fair comparisons, independent seeds, effect sizes and CIs, corrected p-values |
| 5G | final validation and research assessment | `reports/PHASE_5_FINAL_ASSESSMENT.md` and `.json`; complete test results; experiment and reproducibility summary; limitations | T09, T10; software and scientific status reported separately |

Each phase ends with the focused tests, the full suite and the integrity check.
Nothing is committed or pushed without explicit authorization, and only
explicitly intended files are ever staged.

---

## 11. Phase 5A acceptance

| Criterion | Status |
|---|---|
| Existing tests pass | yes — 492 passed |
| No existing behaviour modified | yes — no source, config or test file changed by Phase 5A |
| No protected file changed | yes — 37/37 integrity pass |
| All proposed interfaces documented | yes — M01–M13 |
| No unsupported biological claim | yes — Section 2 |
| Reward, traces and plasticity not implemented | yes |
| Deliverables limited to the two reports | yes |
| No commit or push | yes |

---

## 12. Artifacts

- `reports/PHASE_5A_PLASTICITY_ARCHITECTURE_AUDIT.md` (this file)
- `reports/PHASE_5A_PLASTICITY_ARCHITECTURE_AUDIT.json`

**Next action: stop at GATE 1 and wait for approval before Phase 5B.**
