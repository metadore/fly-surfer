# Phase 8 — Training and Comparison: Experimental Protocol (DRAFT)

| field | value |
|---|---|
| status | **DESIGN / PREREGISTRATION DRAFT — NOT APPROVED, NOT EXECUTABLE** |
| date | 2026-11-16 |
| scope | design and preregistration only |
| executes anything | no — no training, no episodes, no weight change, no plasticity, no installs |
| supersedes | nothing |
| blocking gate | human approval of §12 before any code is written |

## What this document is

A preregistration proposal for the Phase 8 comparison of six experimental conditions on the
controlled endless-surfer game. It defines the conditions, hypotheses, outcomes, controls,
statistics, reproducibility requirements, compute budget, implementation sequence and open
decisions.

## What this document is not

It is not evidence that Phase 8 is ready to run. §2 records the implementation gaps that must be
closed first, and §0 records the single most important prediction: on present evidence, five of the
six conditions will execute `NO_ACTION` on every update, exactly as the Phase 7 baseline did.

## Scientific status declaration

Every quantity in this document is one of:

- **measured** — read from a committed artifact in this repository, with the artifact named;
- **declared** — an experimenter convention fixed before the run (thresholds, sample sizes,
  effect sizes of interest, seed derivations);
- **assumed** — an estimate used for planning that the run itself must replace.

No measured claim is made about fly learning, fly motor control, gameplay competence, or biological
dopamine. The reward signal is a synthetic task reward. The weights are transformed structural
synapse counts in pA. The "dopamine-inspired" rule is a three-factor Hebbian mechanism with a
scalar modulation term; it is not a dopamine measurement.

---

## 0. Readiness summary

**Verdict: design-ready, NOT execution-ready.** The six conditions can be specified against real,
verified interfaces, but the closed loop does not yet exist for four of them.

| ID | Gap | Blocks | Effort |
|---|---|---|---|
| G1 | No incremental plastic stepper. `PlasticSimulator` is batch-only (`run()` calls `reset()`); the closed loop needs `advance_to_step` / `step_index` / `weight_fingerprint` semantics. | B, D | medium |
| G2 | No live readout. `NeuralClosedLoop` always routes motor activity through the fixed-threshold `GameActionDecoder`. | F | medium |
| G3 | No degree-preserving random graph null at BANC t5 scale, with sign policy and valid CSR invariants. | C, D | medium |
| G4 | No matched conventional-learner baseline. The Phase 5F perceptron is `privileged: true`, `matched_control: false`; Gymnasium / Stable-Baselines3 are absent. | E | medium |
| G5 | No multi-episode, multi-seed campaign harness (per-episode JSONL, error capture, artifact manifest, resume). | all | medium |
| G6 | No Phase 8 artifact reader / analysis layer. | all | small |
| G7 | No verified viability check that any neural condition can emit a non-`NO_ACTION` action. | A–D, F | small |

Measured facts that shape the design:

- The Phase 7 fixed-weight closed loop produced **2,852 spikes, all in stimulated sensory neurons,
  0 non-stimulated spikes, 0 motor-population spikes, and `NO_ACTION` on all 213 updates**, with
  weights bit-identical before and after (`sha256 4923f0cd…d945d5`). Source:
  `experiments/results/phase_7/neural_closed_loop.json`.
- Total injected sensory current peaked at **13,476.67 pA** across 232 stimulus neurons, of which
  only **71** fired. The drive is large but the recruited population is tiny.
- The BANC t5 graph has **1,535,710 edges of which 683,100 (44.48%) have a verified transmitter
  sign**; 852,610 edges are unsigned and excluded from propagation.
- A random agent survived 213 / 332 / 218 updates on seeds 42 / 7 / 123 (mean 254.3, sd 67.3);
  a rule-based agent survived 432 / 531 / 432 (mean 465.0, sd 57.2). Source:
  `experiments/results/phase_7/game_integration_demo.json`.
- The Phase 6 confirmatory contrast (plastic minus fixed task mutual information) was **−0.0863
  bits, exact sign-flip p = 0.125, Holm 0.25, not rejected**. This result is frozen and is not
  reinterpreted anywhere in this protocol.

**The preregistered expectation is therefore that A, B, C, D and (probably) F will terminate early
with all-`NO_ACTION` traces.** A floor result is an acceptable, reportable outcome. It is **not**
grounds for tuning the network, enlarging the drive, or relaxing the decoder gate to manufacture
actions. See §6.9 and §12 (U1).

---

## 1. Original roadmap requirements

Source: `docs/PROJECT_VISION.md`, Phase 8 section.

### 1.1 Stated goal and tasks

> **Goal:** Conduct the main scientific experiments.

Tasks as written:

1. Train the biological network with plasticity.
2. Test the fixed biological network.
3. Test randomised networks.
4. Test a conventional AI baseline.
5. Compare performance across multiple episodes.
6. Analyse firing patterns.
7. Analyse weight changes.
8. Analyse information measures.
9. Record experimental configurations.
10. Generate graphs and reports.

### 1.2 Stated file layout

```
experiments/baseline/
experiments/connectome/
experiments/plasticity/
experiments/random_network/
experiments/results/
src/fly_surfer/evaluation/
```

### 1.3 Stated completion criteria

- All major experimental conditions implemented.
- Results reproducible.
- Comparisons use equivalent environments.
- Statistical results documented.

### 1.4 Stated dependencies

Stable-Baselines3 is listed as an experimental dependency for Phase 8; Gymnasium for Phase 7;
PyTorch across Phases 2–8.

### 1.5 Roadmap ↔ repository discrepancies (documented, not silently changed)

| Roadmap says | Repository actually has | Consequence |
|---|---|---|
| `experiments/baseline/` | `experiments/baseline.py` — a 526-line **Phase 2** subgraph simulation runner | Path collision; a new Phase 8 baseline package would shadow or be shadowed. Resolved by a Phase 8 namespace (§10). |
| `experiments/connectome/` | does not exist; the equivalent logic is `experiments/phase_4h/common.py::load_world()` | Reuse, do not duplicate. |
| `experiments/plasticity/` | does not exist; the substrate is `plasticity/` plus `experiments/phase_5/controlled_task.py` | Reuse. |
| `experiments/random_network/` | does not exist; only `plasticity/synthetic.py::synthetic_graph` (32 nodes, test fixture) | G3 is real, not cosmetic. |
| `experiments/results/` | exists and is in use, subfoldered per phase | Phase 8 writes `experiments/results/phase_8/`. |
| `src/fly_surfer/evaluation/` | **no `src/` tree at all** | Roadmap layout is not implementable as written; the project uses flat top-level packages. |
| Stable-Baselines3 | not installed; no Gymnasium-style wrapper exists | E must be built against the existing 5-tuple API, or SB3+Gymnasium must be installed (U5). |
| "information measures" | Phase 6 exists and returned a **negative** confirmatory result | Phase 8 information analysis is descriptive only; it cannot upgrade Phase 6 (§5.4). |
| PyTorch Phases 2–8 | torch is present and used only by the Phase 3B detector path | E and F may use torch; A–D must not. |

The roadmap's intent (six conditions, equivalent environments, reproducible, statistically
documented) is preserved without modification. Only the file layout and the dependency list are
adjusted, and both adjustments are recorded here rather than applied silently.

---

## 2. Current implementation readiness

### 2.1 Verified component inventory

Every row was read from source in this session. "Reuse" means Phase 8 calls it unchanged.

| Need | Existing component | Status | Notes |
|---|---|---|---|
| BANC structural graph | `brain/banc_graph.py::BancConnectome`, `datasets/processed/banc_v888/banc_graph_t5.npz` | reuse | 172,433 nodes; 1,535,710 edges; 18,552,546 synapses; 24,320 isolated nodes; strictly ascending `root_ids`; no self-edges; weights ≥ threshold |
| Weight → pA | `brain/banc_synapse_policy.py` | reuse | `min(5.0 · count^0.75, 300)`; verified-only signs; unsigned edges excluded |
| LIF simulation | `brain/banc_simulator.py::BancSimulator` | reuse | dt 0.5 ms; no `vocabulary` / `nt_code`, so FAFB `BrainSimulator` paths do not apply |
| Incremental stepping | `environment/live_loop.py::LiveBancStepper` | reuse for A, C, F | `advance_to_step(target)` absolute + monotonic; `resets`; `weight_fingerprint()` |
| **Incremental *plastic* stepping** | — | **G1** | `plasticity/plastic_simulator.py` exposes only `reset()` and batch `run()`; `run()` calls `reset()` internally |
| Sensory encoding | `sensory/population_encoder.py::build_encoders/encode_state`; `configs/banc_sensory_mapping.yaml`; `BancSensoryMapping` | reuse | 7 of 14 features mapped onto 232 neurons at 200 pA; 805 motor neurons excluded; zero action/motor overlap |
| Live sensory drive | `environment/live_loop.py::LiveSensoryDrive` | reuse | zero-order hold; `apply(step, time_ms, current_pa)`; `stimulated_indices` |
| Game environment | `environment/subway_environment.py::ControlledGameEnvironment` | reuse | `reset(seed)`; `step(action)` → 5-tuple; `reward_components`; `save_recording` |
| Action mapping | `environment/action_adapter.py` | reuse | `UNMAPPED` and `DUCK` → `NO_ACTION` with explicit reasons |
| Motor decoding | `motor/action_decoder.py::GameActionDecoder`; `configs/motor_decoder.yaml` | reuse for A–D; **replace** in F | LEFT 185 / RIGHT 186 / JUMP 20; 50 ms half-open window; activation 0.20 / release 0.10; min 3 active ∧ 5 spikes; priority LEFT→RIGHT→JUMP |
| Reward bridge | `environment/reward_function.py` | reuse | `GameRewardFunction.schedule(delay_ms)` and `.modulation_provider(config)`; component-sum verified; provenance recorded; value **not** recomputed |
| Plasticity rule | `plasticity/engine.py`, `plasticity/rules.py`, `plasticity/traces.py` | reuse (G1 wrapper) | `dw = eta · modulation · trace`; `eta = 0` is an exact-zero contract |
| Weight bookkeeping | `plasticity/weights.py::WeightState` | reuse | `digest()`, clamps, saturation, per-edge deltas |
| Reward modulation | `plasticity/reward.py` | reuse | `ModulationRewardProvider.step(step, time_ms, context)` / `.reset()` |
| Plasticity config | `configs/plasticity_banc.yaml` | reuse | eta 0.5; bounds 0.5–2.0×; max 5 pA/update; τe 20 ms; modulation gain 1.0, τ 50 ms, clip 5 |
| World assembly | `experiments/phase_4h/common.py::load_world()` | reuse | graph + nodes + policy + populations + decoder config + neuron params |
| Multi-episode campaign | — | **G5** | `experiments/phase_5/controlled_task.py` runs one episode with a seed; no campaign harness |
| Random graph null | — | **G3** | only a 32-node test fixture |
| Matched conventional learner | — | **G4** | Phase 5F perceptron is privileged and unmatched |
| Readout | — | **G2** | no readout module, no readout training |
| Information analysis | `information/` | reuse (read-only) | entropy / MI / bias correction / permutation / bootstrap |

### 2.2 Measured performance envelope

From `experiments/results/phase_7/neural_closed_loop.json` (213 updates, 7,100 neural steps,
22.345 s wall, deterministic over two repeats):

| Quantity | Measured |
|---|---|
| wall time per game update | 0.1049 s |
| wall time per neural step | 3.15 ms |
| neural steps per game update | 33.333 (clock target `round(game_ms / 0.5)`) |
| worst-case episode (900-update cap) | ≈ 94.4 s |
| observed episode (213 updates, collision) | 22.3 s |

Memory: the t5 artifact is 13,484,120 bytes on disk; Phase 4D construction peaked at 1,710.8 MB.
Elasticity traces for 683,100 plastic edges at float32 are ≈ 2.7 MB; effective weights
1,535,710 × float32 ≈ 6.1 MB. The substrate is not memory-bound; the **machine** is (15.34 GB
total, 0.5 GB available at audit time).

### 2.3 Verified environment

| Item | Value |
|---|---|
| Python | 3.13.14 |
| platform | Windows-11-10.0.26200, x86-64, 12 logical CPUs |
| numpy / pandas / matplotlib / PyYAML | 2.3.4 / 2.3.3 / 3.10.7 / 6.0.3 |
| torch | 2.10.0+cpu (present, used by the Phase 3B detector path only) |
| scipy / scikit-learn | present, unpinned |
| gymnasium / Stable-Baselines3 | **absent** |
| RAM | 15.34 GB total, 0.5 GB available at audit |
| disk free | 17.93 GB |

### 2.4 Repository state at design time

The working tree is **dirty and must be preserved**. Untracked: `environment/`,
`experiments/phase_7/`, `experiments/results/phase_7/`, `configs/phase_7_*.yaml`,
`datasets/processed/banc_v888/`, `datasets/external/`. Modified: `environment/subway_environment.py`.
Nothing in this phase will stage, commit, stash, clean or delete any of it.

Known pre-existing condition: **6 of the full test suite fail on one cause only** — the
`README.md` SHA-256 pin. Pinned `8ab6a8cc…f90563` (14,921 bytes); current `8a79d44d…4164`
(14,938 bytes). All 36 other pinned files match; `integrity/non_readme_failures = []`. This is a
repository decision that predates Phase 8 and is not fixed here.

---

## 3. Six experimental conditions

All six share: the same `ControlledGameEnvironment`, the same reward definition, the same action
vocabulary `{LEFT, RIGHT, JUMP, ROLL, DUCK, NO_ACTION}`, the same termination rules, the same
maximum of 900 game updates, and the same evaluation seed schedule. They differ only in what
proposes the action and what, if anything, is allowed to change.

The one deliberate interface asymmetry is stated up front and is not hidden: the neural conditions
receive **7 of 14** observation features through `BancSensoryMapping`, because 7 features have no
mapped population. Condition E is therefore run twice — **E-matched** on the same 7 features
(confirmatory) and **E-full** on 14 features (exploratory ceiling). See §6.6.

### 3.1 Condition A — Biological connectome, fixed weights

| # | Aspect | Specification |
|---|---|---|
| 1 | Network architecture | BANC v888 t5 sparse graph, 172,433 nodes, 1,535,710 edges; LIF, dt 0.5 ms; 232 mapped sensory neurons; 805 motor neurons; 414 motor neurons carry no LEFT/RIGHT/JUMP label |
| 2 | Connectivity source | `datasets/processed/banc_v888/banc_graph_t5.npz` (integer synapse `count`, never `norm`), recorded by SHA-256 |
| 3 | Weight initialization | Deterministic, not trained: `min(5.0 · count^0.75, 300)` pA, verified-only signs; unsigned edges inert. Fingerprint `4923f0cd…d945d5` |
| 4 | Weights fixed or changing | **Fixed.** No plasticity object is constructed. Asserted by `weight_fingerprint` equality before/after each episode |
| 5 | Learning algorithm | none |
| 6 | Inputs / observations | 7 encoded features → `LiveSensoryDrive`, zero-order hold, 200 pA per active feature, additive |
| 7 | Action selection | `GameActionDecoder`: active-fraction in a 50 ms half-open window, activation 0.20, release 0.10, gate ≥3 active ∧ ≥5 spikes, priority LEFT→RIGHT→JUMP, else `NO_ACTION` |
| 8 | Reward handling | Logged only. Reward never reaches the network |
| 9 | Training / evaluation | No training. K evaluation episodes per seed |
| 10 | Required recordings | All 20 `RECORD_FIELDS`; per-episode weights digest; action counts; decoder states; motor-population spikes; spike SHA-256 |
| 11 | Potential confounds | Zero motor recruitment (Phase 7); 44.5% of edges unsigned; 24,320 isolated nodes; 7 of 14 features unmapped; single fixed decoder threshold set |
| 12 | Scientific question | What does the biological connectome, read through a fixed decoder, do with no learning and no readout? **This is the reference condition.** |

### 3.2 Condition B — Biological connectome, dopamine-inspired plasticity

Rows 1–3, 6–7, 10–11 identical to A. Differences:

| # | Aspect | Specification |
|---|---|---|
| 4 | Weights fixed or changing | **Changing.** `WeightState` initialized from the same deterministic structural weights; bounds 0.5–2.0× initial; max |Δw| 5 pA per update; every edge's clamp/saturation recorded |
| 5 | Learning algorithm | Phase 5 three-factor rule, unchanged: `Δw = eta · M(t) · e(t)`, eta **0.5** (declared, not tuned), τe 20 ms, delay-matched coincidence, prune 1e-4 every 50 steps; signed verified edges only |
| 8 | Reward handling | `GameRewardFunction` → `schedule(delay_ms)` → `ModulationRewardProvider`; modulation gain 1.0, decay τ 50 ms, clip ±5. Delivered at the neural step matching the game update |
| 9 | Training / evaluation | No separate training phase: plasticity runs **during** evaluation. Training-stream RNG is separate from environment and network streams |
| — | Internal validity arm **A′** | A executed through the plastic simulator with `eta = 0`. Must reproduce A's spike SHA-256 and `action_reward_sha256` **bit-identically**. If it does not, B is not interpretable and the campaign stops |
| 12 | Scientific question | Does reward-modulated structural plasticity change behaviour, holding connectivity, drive and decoder constant? |

### 3.3 Condition C — Random network, fixed weights

Rows 1, 4–7, 10 identical to A except topology.

| # | Aspect | Specification |
|---|---|---|
| 2 | Connectivity source | **Declared null**: a signed, degree-preserving directed randomization of the BANC t5 edge list |
| 3 | Weight initialization | The original weight multiset is preserved and permuted with the edges; node identities, annotations and signs are **unchanged** |
| — | Null construction | Directed double-edge swaps on `(source, target)` with rejection of duplicates and self-loops; seeded; ≥ 10·E attempted swaps; t5 threshold re-applied if any edge weight falls below 5 |
| — | Preserved exactly | Per-node out-degree; per-node in-degree; the global weight multiset; per-node transmitter sign and every annotation column; therefore the LEFT 185 / RIGHT 186 / JUMP 20 populations and every motor neuron's in-degree |
| — | Not preserved (declared) | Weak-component sizes and the identity of which neuron talks to which; per-neuron *sum* of outgoing weight |
| — | Validation gate | Final graph must satisfy every `BancConnectome` invariant; in/out degree sequences must equal the original exactly; zero duplicate pairs; zero self-edges; weight sum must equal 18,552,546 synapses |
| 11 | Potential confounds | A rewire changes global connectivity as well as local wiring; the null therefore conflates "which neurons connect" with "how the graph fragments". A component-preserving variant is listed as exploratory (U4) |
| 12 | Scientific question | Does the specific biological wiring matter, or would any graph with the same degrees and signs do as well? |

### 3.4 Condition D — Random network, dopamine-inspired plasticity

Identical to C in rows 1–3, 6–7, 10–11; identical to B in rows 4, 5, 8, 9. Same eta, same bounds,
same trace constants, same reward cadence, same seed schedule as B.

| # | Aspect | Specification |
|---|---|---|
| 12 | Scientific question | Does plasticity help **on this substrate**, or is any apparent benefit an artefact of the biological topology? C vs D is the matched test of plasticity that does not depend on the connectome being real |

### 3.5 Condition E — Conventional artificial neural network, conventional training

| # | Aspect | Specification |
|---|---|---|
| 1 | Network architecture | Small MLP: input = the same 7 encoded features as the neural conditions (E-matched), 2×64 tanh hidden units, output = 4 logits {LEFT, RIGHT, JUMP, NO_ACTION}. A 14-feature variant (E-full) is exploratory |
| 2 | Connectivity source | none — fully connected, initialized by torch default with a declared seed |
| 3 | Weight initialization | `torch.nn.init` defaults under a seeded generator; recorded |
| 4 | Weights fixed or changing | **Changing** — this is the conventional-training condition |
| 5 | Learning algorithm | REINFORCE with a learned value baseline (or PPO-clip if approval prefers), Adam, declared LR and entropy coefficient; discount applied to the per-update task reward. Declared in config, not tuned per seed |
| 6 | Inputs / observations | The **same** `GameState.features()` subset the neural conditions receive. No pixels, no privileged state, no future objects |
| 7 | Action selection | Categorical sample during training; argmax during evaluation |
| 8 | Reward handling | The identical `reward_components` scalar the neural conditions log. No shaping |
| 9 | Training / evaluation | Train on training seeds; evaluate on **disjoint** evaluation seeds. Same episode cap and termination rules |
| 10 | Required recordings | Per-update observation, logits, sampled action, reward, value; parameter checkpoints; per-episode return and survival |
| 11 | Potential confounds | E is a dense learner with direct credit assignment to its own parameters; A–D have no such pathway. This asymmetry is intrinsic to the comparison and is stated, not corrected. E is a **reference point**, not a matched control for plasticity |
| 12 | Scientific question | Can a conventional learner with equivalent observations and actions solve this task at all? If E also sits at the floor, the environment is not solvable from this observation interface and no neural result is interpretable as a competence failure |

### 3.6 Condition F — Biological connectivity with trainable readout

| # | Aspect | Specification |
|---|---|---|
| 1 | Network architecture | BANC t5 graph **unchanged**, `LiveBancStepper` **unchanged**, plus a trainable readout that replaces `GameActionDecoder` |
| 2 | Connectivity source | same artifact and fingerprint as A |
| 3 | Weight initialization | Connectome: deterministic as A. Readout: seeded small initialization; the **only** trainable tensors in the condition |
| 4 | Weights fixed or changing | **Connectome fixed, readout changes.** Asserted three ways per episode: connectome `weight_fingerprint` identical before/after; `WeightState` absent; the set of trainable tensors is exactly the readout parameter list |
| 5 | Learning algorithm | REINFORCE over the readout only. Features = per-update motor-population activity (LEFT/RIGHT/JUMP spike counts in the trailing 50 ms, plus total and per-population firing rate, plus the decoder's raw activation scores). Optional linear or one-hidden-layer readout; declared in config |
| 6 | Inputs / observations | Same 7-feature sensory drive as A |
| 7 | Action selection | Readout over {LEFT, RIGHT, JUMP, NO_ACTION}. **ROLL and DUCK are excluded**: no motor population exists for them in this export, so a readout "learning" them would be ungrounded |
| 8 | Reward handling | Same task reward; used only as the readout's learning signal, never as a synaptic modulator |
| 9 | Training / evaluation | Train readout on training seeds; evaluate on disjoint seeds. Connectome is never reset between updates within an episode; the readout is frozen at evaluation |
| 10 | Required recordings | Everything in A, plus: readout inputs, logits, sampled action, readout parameters per checkpoint, and an explicit `connectome_unchanged` boolean with both fingerprints |
| 11 | Potential confounds | Readout training is **not** synaptic plasticity and must never be reported as such. The readout sees only what the motor populations produce; if those are silent (Phase 7: 0 motor spikes), the readout has no signal and can only learn to prefer `NO_ACTION`. That is a prediction, not a bug. A readout with a bias-only path could in principle learn a constant action — this is a real alternative explanation and is reported, not suppressed |
| 12 | Scientific question | Is the failure of the fixed loop a **decoder** problem or a **network** problem? F is the cleanest test in this phase |

### 3.7 Condition summary

| | topology | weights | decoder | learns |
|---|---|---|---|---|
| A | biological | fixed | fixed threshold | nothing |
| B | biological | plastic | fixed threshold | synapses (3-factor) |
| C | randomized, degree+sign preserved | fixed | fixed threshold | nothing |
| D | randomized, degree+sign preserved | plastic | fixed threshold | synapses (3-factor) |
| E | none (MLP) | trained | argmax over 4 logits | all parameters (policy gradient) |
| F | biological | **fixed** | **trained readout** | readout only |
| A′ (control) | biological | fixed, via plastic simulator at eta = 0 | fixed threshold | nothing (must equal A) |

---

## 4. Scientific hypotheses

Falsifiable, with the direction of the predicted effect and the observation that would refute it.
H1 and H2 are confirmatory; H3–H6 are exploratory/descriptive and cannot be promoted later.

**H1 (plasticity, within-substrate).** Reward-modulated three-factor plasticity changes survival on
the biological substrate.
*Prediction:* B − A ≠ 0 in mean survival.
*Refuted if:* the paired difference is indistinguishable from zero, or the direction is negative.
*Prior expectation:* near-zero. Phase 6's confirmatory MI contrast was negative and not rejected;
the Phase 7 loop never recruited a motor neuron, so eligibility traces exist mainly on sensory
neurons whose spikes are stimulus-locked, not outcome-locked. H1 is expected to **fail**, and a
failure is a reportable result.

**H2 (biological specificity of connectivity).** The biological graph outperforms a degree- and
sign-matched random graph.
*Prediction:* A − C > 0.
*Refuted if:* A − C ≤ 0 or is indistinguishable from zero.
*Note:* a null result here is the single most likely outcome given a floor, and would mean the
comparison carries no information about biological specificity at this operating point.

**H3 (readout sufficiency).** A trainable readout over the same fixed biological substrate beats
the fixed threshold decoder.
*Prediction:* F − A > 0.
*Refuted if:* F − A ≤ 0.
*Prior expectation:* low but non-zero. If the motor populations are silent, the readout cannot
exceed the constant-action baseline.

**H4 (conventional-learner reference).** A conventional learner on the same 7-feature interface
reaches above the no-action floor.
*Prediction:* E-matched survival > no-action floor.
*Refuted if:* E-matched ≤ floor. A refutation here means the environment is not solvable from the
neural observation interface, and no neural condition's poor performance can be attributed to the
connectome alone.

**H5 (matched plasticity control).** Plasticity benefits, if any, are not specific to biological
topology.
*Prediction:* (B − A) − (D − C) ≈ 0.
*Exploratory.* A non-zero value would be a topology×plasticity interaction that this sample size
cannot confirm.

**H6 (descriptive).** Motor-population activity is the necessary substrate for non-`NO_ACTION`
actions.
*Prediction:* across all conditions and episodes, every non-`NO_ACTION` update in A–D, F is
preceded by ≥1 spike in the corresponding population within the decoding window.
*Descriptive only.* This is a mechanical consistency check, not a scientific discovery.

**Frozen prior result.** The Phase 6 confirmatory finding (plastic minus fixed task MI = −0.0863
bits, exact sign-flip p = 0.125, Holm 0.25, not rejected) remains exactly as published. H1 is a
**new** hypothesis in a **different** substrate (`BANC` + game task, not the Phase 5 substrate).
Nothing in Phase 8 may be described as confirming, repairing, or overturning Phase 6.

---

## 5. Primary and secondary outcomes

### 5.1 Primary outcome (confirmatory, single)

**Mean survival time in game updates per evaluation episode, right-censored at the 900-update
truncation cap**, averaged over K evaluation episodes within a seed in which the agent is random.

Definitions fixed before the run:

- *survival* = number of game updates completed before `terminated` (collision) or `truncated`
  (900-update cap);
- an episode that reaches 900 updates enters as 900 and is flagged `truncated`;
- an episode that raises an exception is recorded with `status: "error"` and a reason, **retained**,
  and excluded from the complete-case primary with a pre-specified sensitivity analysis (§7.6);
- an all-`NO_ACTION` episode is a **valid observation**, not a failed run. It is scored normally.

Rationale: survival is the only outcome that is (a) defined identically for all six conditions,
(b) produced by the environment rather than by a model of the environment, (c) unaffected by the
neural/ANN interface asymmetry, and (d) already measured for the Phase 7 baseline and for the two
non-neural pilot agents.

### 5.2 Declared smallest effect of interest

**SEI = 100 updates** (≈ 1.67 s of game time; ≈ 11% of the cap; ≈ 1.5× the 3-seed random-agent
standard deviation of 67.3). This is a **declared convention**, chosen so that a difference is on
the scale of at least one additional obstacle-clearing cycle. The obstacle cadence has not been
measured, so this is not a derived quantity. §7.4 states the power consequences.

### 5.3 Confirmatory family (three contrasts, Holm-corrected)

| ID | Contrast | Interpretation |
|---|---|---|
| C1 | **F − A** | contribution of a trainable readout on the biological substrate |
| C2 | **B − A** | contribution of three-factor synaptic plasticity on the biological substrate |
| C3 | **A − C** | contribution of biological over degree+sign-matched random connectivity |

These three are the confirmatory family and nothing else is. Family size m = 3, α = 0.05
family-wise. The remaining conditions are reported but cannot be promoted to confirmatory status
after seeing the data.

### 5.4 Secondary and exploratory outcomes

| Outcome | Status | Notes |
|---|---|---|
| D − C (plasticity on random substrate) | exploratory | completes the 2×2 |
| A vs E-matched | explanatory reference | E is not a matched control |
| E-full vs E-matched | exploratory | value of the 7 unmapped features |
| A′ vs A | **integrity check** | must be exactly equal; a mismatch invalidates B |
| Total task reward per episode | secondary | reward is coin-dominated: coin +1, collision −1, survival +0.01/step, obstacle 0.0 (the obstacle component is configured to zero and is therefore inert) |
| Coins collected per episode | secondary | unmodelled in the sensory drive — no coin population exists |
| Collisions per episode | secondary | survival and collision count are near-redundant at this cap; reported but not tested separately |
| Obstacles avoided | **not available** | the reward component is configured to 0.0 and no per-obstacle outcome is recorded; must not be invented |
| Action distribution per condition | secondary | primary diagnostic of the floor |
| Fraction of updates with `NO_ACTION` | secondary | expected ≈ 1.0 for A–D |
| Motor-population activity (spikes/update, active neurons) | secondary | expected 0 for A–D |
| Mean firing rate, sensory-population recruitment | secondary | descriptive |
| Weight change: L1, changed-edge count, saturation count, clamp hits | secondary (B, D) | must be exactly 0 for A, C, F |
| Training stability (return curve, gradient norm, KL) | secondary (E, F) | descriptive |
| Inference latency per update | engineering metric | separates "cannot act" from "cannot act in time" |
| Event-class entropy, decoder-state entropy | exploratory | Phase 6 estimators, descriptive only |
| Cue/feature → action mutual information | **exploratory, non-confirmatory** | cannot alter the Phase 6 conclusion; must be labelled "in a new substrate" |

---

## 6. Experimental controls

### 6.1 Environment equivalence

One config file, `configs/phase_8/environment.yaml`, is the single source for: `max_steps` 900,
`initial_speed` 7.0, `max_speed` 16.0, `coin_reward` 1.0, `collision_penalty` −1.0,
`survival_reward` 0.01, `obstacle_reward` 0.0, `distance_horizon` 25.0, `render_mode` null,
observation schema v1. It is hashed into every episode record. No condition may override it.

### 6.2 Paired environment seeds

Evaluation episodes are paired across conditions: episode *j* of seed *s* uses environment seed
`derive(master, s, j, "env")` — independent of the condition. All six conditions therefore face
identical initial layouts per paired episode. Pairing is recorded per episode, not assumed.

### 6.3 Three independent seed streams

Never share one RNG across purposes. Each is
`np.random.SeedSequence([MASTER_SEED, condition_id, seed, stream])` with
`stream ∈ {"environment", "network", "learning"}`:

| stream | used by | examples |
|---|---|---|
| environment | `ControlledGameEnvironment.reset(seed)` | obstacle/coin placement, speed |
| network | `BancSimulator` noise (`noise_std_pa = 0` at present) | membrane noise, any synaptic stochasticity |
| learning | readout init, action sampling, training batch order | E, F |

Separating them is what makes the pairing in §6.2 valid even though F consumes many extra training
episodes.

### 6.4 Identical termination and truncation

`terminated` on collision; `truncated` at `max_steps`. Both stop the loop identically for all six
conditions. Neither may be disabled, softened, or extended per condition.

### 6.5 Consistent reward definition

`reward_components` are produced by the game and **not recomputed** by FLY-SURFER. The sum
invariant is asserted per step. The reward used for learning in B/D/E/F is the same scalar that is
logged, with an optional declared delay for B/D (`schedule(delay_ms)`) that is recorded per
delivery.

### 6.6 Observation-interface matching

The neural conditions receive 7 features. E-matched receives exactly those 7, from the same
`GameState`. E-full receives all 14 and is explicitly exploratory. No condition receives pixels,
future obstacle positions, hidden game state, lane indices of unspawned objects, or the
`reward_components` before the action is applied.

### 6.7 Train/evaluation separation

Training seeds and evaluation seeds are drawn from disjoint ranges and the disjointness is asserted
at run start. Evaluation uses a frozen parameter set: frozen readout (F), frozen policy (E), frozen
connectome (all). No evaluation episode may update anything.

### 6.8 Independent evaluation episodes

K = 10 evaluation episodes per seed, each with its own environment seed and a full reset. No state
carries between evaluation episodes. Repeated measurements within a seed are averaged before the
primary test so that the **seed** remains the independent unit; the episode-level analysis is a
declared secondary (§7.5).

### 6.9 Handling degeneracy (the Phase 7 result)

Three pre-specified rules, none of which modifies the network:

1. **All-`NO_ACTION` episodes are retained and scored.** They are not filtered, down-weighted or
   re-run.
2. **Zero motor activity is a measurement, not an error.** The condition's `motor_spikes` field is
   reported per episode.
3. **No drive tuning.** If the floor is reached, the response is a floor report plus a request for
   a scope decision (U1). Changing stimulus amplitude, decoder activation threshold, or mapping
   after seeing the floor result would break the preregistration.

### 6.10 Artifact integrity controls

- Connectome fingerprint recorded before and after every episode and asserted equal in A, C, F.
- In B and D, only the `WeightState` may differ, and the exact digest chain (structural → initial →
  learned delta → effective) is recorded.
- `A′` (eta = 0 through the plastic path) must reproduce A **bit-identically**; a mismatch stops the
  campaign.
- The 37-file protected hash baseline is checked before and after the campaign. The known
  `README.md` pin drift is reported as a pre-existing condition, not re-litigated.
- Phase 3–6 result files, `datasets/`, `external/`, and the standalone game repository are
  read-only. Phase 8 writes only under `experiments/phase_8/`, `experiments/results/phase_8/`,
  `configs/phase_8/`, `readout/`, `experiments/phase_8_random/`, `evaluation/` (see §10).

### 6.11 Compute-asymmetry control

Every condition records wall time, per-update latency, and CPU time. The primary outcome is
behaviour, not speed, so asymmetry is reported rather than equalized. Where latency differences
exist they must be shown to be ≥ 10× below the game update period (16.67 ms) before any condition
is declared unable to act; if not, a latency-capped variant is reported as a secondary.

---

## 7. Statistical analysis plan

### 7.1 Design

Paired, within-seed comparison. N = 10 seeds, K = 10 evaluation episodes per seed per condition,
6 conditions (plus A′ on 2 pilot seeds).

### 7.2 Unit of analysis

The **seed**. Per seed and condition, the outcome is the mean over K episodes of the censored
survival. Episode-level values are also retained for the secondary analysis.

### 7.3 Primary test

Two-sided **exact sign-flip permutation test** on the 10 paired per-seed differences
(2^10 = 1024 assignments; smallest attainable p = 0.000977). No normal approximation, no
asymptotics. Applied to C1, C2, C3.

### 7.4 Sample size and power

| Quantity | Value |
|---|---|
| design | N = 10 paired seeds |
| α (two-sided, per contrast) | 0.05 |
| power | 0.80 |
| MDE formula | `MDE = (z₀.₉₇₅ + z₀.₈) · σ_paired / √N = 2.8016 · σ_paired / √N` |
| declared SEI | 100 updates |
| assumed σ_paired | 60 updates |
| MDE at N = 10, σ = 60 | **≈ 53 updates** |
| σ_paired supported at N = 10 for MDE = 100 | **≈ 113 updates** |
| escalation rule | if the pilot paired sd exceeds 113, set N = ⌈(2.8016·σ/100)²⌉ and re-run the pilot analysis before the campaign |

**Where σ_paired = 60 comes from.** It is an **assumption**, not a measurement. The only available
dispersion evidence is the 3-seed Phase 7 pilot: random agent sd 67.3, rule-based agent sd 57.2
across seeds. These are between-seed sd of a *single* episode, not the sd of a *paired difference*.
A paired difference removes the shared environment layout, so the true σ_paired is expected to be
**smaller**; 60 is deliberately the conservative end. The pilot (§10, step 8.3) measures the real
value on 3 seeds and the escalation rule applies.

### 7.5 Multiplicity

Holm–Bonferroni over the three confirmatory contrasts, α = 0.05 family-wise. Ordering by raw p.
With 1024 sign-flip assignments the smallest attainable adjusted p is 3 × 0.000977 = 0.00293, so
Holm is not vacuous at this N. Exploratory outcomes receive no correction and are labelled
exploratory in every table, caption and sentence.

### 7.6 Missing, failed and censored runs

| Situation | Handling |
|---|---|
| episode raises an exception | record `status: "error"`, keep the partial trace and the traceback, include the row in the dataset |
| episode hits the 900 cap | `truncated: true`, survival = 900, censored, included |
| episode collides on update 1 | valid, survival = 1, included |
| a whole seed×condition cell errors | primary analysis uses complete pairs only; sensitivity analysis re-runs with errors scored at their last completed update |
| a condition is structurally impossible to run | the campaign halts and the report says so; the condition is not silently replaced |

**No unsuccessful episode is discarded at any stage.** The dataset is append-only JSONL; the
analysis reads it and reports counts of every status.

### 7.7 Uncertainty

- Paired percentile bootstrap over seeds (10,000 resamples) for the difference, reported as
  *approximate* at N = 10; the exact attainable interval is also printed.
- Secondary: two-level cluster bootstrap (episodes within seed) for the episode-level estimate.
- Effect sizes: paired mean difference, median difference, Cohen's dz, and the win/loss/tie count.
  At N = 10 a win/loss count can be 10–0 and still give p = 0.00195 two-sided; this is stated
  rather than hidden.

### 7.8 Degeneracy-aware analysis (pre-specified)

If the primary outcome is at floor in ≥ 4 of 6 conditions:

- the confirmatory tests are still reported, with the note that the design has **no power against
  a difference between two floored conditions**;
- the report's headline becomes the floor finding plus the reason (which of: no motor spikes, no
  sustained activity, decoder gate never met), decomposed per condition;
- no confirmatory claim of "plasticity does not work" is made from a floored design — absence of
  an effect under a floor is not evidence of absence, and is described exactly that way.

---

## 8. Reproducibility requirements

1. **Config-only constants.** Every threshold, seed, LR, eta, bound, episode count, and cap lives
   in `configs/phase_8/*.yaml`, hashed into every episode record and every report.
2. **Declared seeds.** `MASTER_SEED` in config; per-condition/per-seed/per-stream values derived
   as in §6.3 and printed in the run manifest.
3. **Append-only episode store.** `experiments/results/phase_8/episodes.jsonl`, one row per
   episode, never rewritten. Resume is by (condition, seed, episode) key.
4. **Deterministic replay.** One seed × one episode per condition is re-run in a fresh process and
   must reproduce the spike SHA-256 (neural conditions) or the action/reward SHA-256 (E) exactly.
   This mirrors the Phase 7 check that already passes (`cca811f3…b2fb` reproduced).
5. **Input hashes.** Graph artifact, node table, synapse policy, neuron config, sensory mapping,
   motor decoder, environment config, plasticity config — all recorded as SHA-256 per episode.
6. **Environment capture.** Python, numpy, pandas, torch, platform, CPU count, peak RSS, wall time,
   recorded in the run manifest.
7. **Artifact schema.** A versioned JSON schema for episode rows and for the run manifest, with a
   validator that runs before any analysis.
8. **No silent overwrite.** An existing result directory is refused unless
   `--new-run-id` is supplied; previous runs are never deleted.
9. **Report generation from data.** All tables and figures regenerate from the JSONL. No number is
   typed by hand into a report.
10. **Frozen-file guarantee.** The campaign asserts the 37-file integrity baseline before and after
    and refuses to publish a report if any non-README pinned file changed.

---

## 9. Compute and dependency assessment

### 9.1 Genuinely required dependencies

| Package | Present | Needed by | Verdict |
|---|---|---|---|
| numpy | 2.3.4 | all | present, required |
| pandas | 2.3.3 | analysis, tables | present, required |
| matplotlib | 3.10.7 | figures | present, required |
| PyYAML | 6.0.3 | configs | present, required |
| psutil | 7.1.2 | memory/perf | present, optional |
| pytest | 7.4.3 | tests | present, required for dev |
| **torch** | 2.10.0+cpu | E, F readout | present. Required **only** for E and F |
| scipy | present, unpinned | optional (bootstrap convenience) | **not required** — bootstrap and sign-flip are implementable in numpy; keep unpinned use out of the critical path |
| scikit-learn | present, unpinned | not needed | **not required** |
| **gymnasium** | **absent** | would be needed only to wrap the game for SB3 | **not required** if E is implemented directly against the existing 5-tuple API |
| **Stable-Baselines3** | **absent** | roadmap lists it for Phase 8 | **not required** for the recommended E; would be required only for the SB3 variant (U5) |

**Nothing needs to be installed for the recommended design.** A–D need only numpy and the existing
FLY-SURFER packages. F needs torch (present). E can be a ~150-line REINFORCE implementation against
`ControlledGameEnvironment` — the game is not a Gymnasium environment, has no `spaces`, and adding
a Gymnasium dependency would be a new surface with no scientific benefit.

### 9.2 Compute budget (measured rates, declared extrapolation)

Rates from §2.2. Neural conditions = A, B, C, D, F.

| Scope | Assumption | Wall time |
|---|---|---|
| one 213-update episode | measured | 22.3 s |
| one 900-update episode | measured rate × cap | 94.4 s |
| one seed, 10 eval episodes | measured rate | 3.7 min |
| one seed, 10 eval episodes | worst case | 15.7 min |
| 5 neural conditions × 10 seeds, eval only | measured rate | **≈ 3.1 h** |
| 5 neural conditions × 10 seeds, eval only | worst case | **≈ 13.1 h** |
| F training rollouts (20 episodes/seed) | measured rate | +6.2 h to +26.2 h |
| B/D plasticity overhead | assumed +20–40% (trace update on ≤683,100 edges) | +0.6 h to +5.2 h |
| random-graph construction (once per seed, C/D) | assumed 2–15 min per graph | 0.3–2.5 h |
| E training and evaluation | torch CPU, 7 or 14 inputs, 4 outputs | < 10 min total |
| analysis, figures, replay checks | | < 30 min |

**Declared budget:** ≈ 10–45 h wall, single process. Label every non-measured figure as an
assumption. Parallelism across 12 CPUs could reduce wall time by up to ~8× but introduces
determinism risk (BLAS thread counts, per-process memory) and is **not** part of the primary plan.

### 9.3 Blocking operational constraint

At audit time only **0.5 GB of 15.34 GB RAM was available**. The t5 substrate plus traces is on the
order of a few hundred MB, so the substrate is not the problem, but the machine is. The campaign
must **re-check free memory immediately before starting** and record it. If < 4 GB is free, the
campaign does not start and reports the reason rather than failing mid-run (this is the Phase 2.5
"never silently skip" rule applied here).

---

## 10. Implementation sequence

Nothing below is implemented. Each step is additive, test-guarded, and gated.

| Step | Deliverable | Reuses | Gate before proceeding |
|---|---|---|---|
| **8.0** Protocol approval | this document → frozen with a SHA-256 and a freeze record | — | user approval of §12 |
| **8.1** Campaign skeleton | `experiments/phase_8/` (namespace, avoids the `experiments/baseline.py` collision), config loader, episode JSONL writer, seed derivation, run manifest, artifact schema + validator | `experiments/phase_4h/common.py`, Phase 7 runner structure | schema validator rejects a malformed row; a 1-update dummy episode round-trips |
| **8.2** Condition A | `conditions/a_fixed.py` — a refactor of the Phase 7 loop into a callable episode function with an explicit seed | `LiveBancStepper`, `LiveSensoryDrive`, `GameActionDecoder`, `NeuralClosedLoop` | A reproduces the Phase 7 fingerprint `cca811f3…b2fb` on seed 42, 213 updates |
| **8.3** Pilot | 3 seeds × 3 conditions (A, C, F) × 3 episodes | 8.1–8.2 | measures the true σ_paired; applies the §7.4 escalation rule; applies the §0 viability gate |
| **8.4** Condition C | `experiments/phase_8_random/` degree-preserving signed rewire + validator | `brain/banc_graph.py` invariants | invariants pass; degree sequences identical; weight sum identical; ≤ 15 min per graph |
| **8.5** Condition F | `readout/` module + `conditions/f_readout.py` | torch; `GameActionDecoder` retained as the feature extractor | connectome fingerprint identical before/after; trainable-parameter set == readout params only |
| **8.6** Conditions B and D | `plasticity/live_stepper.py` (additive subclass; **no edit to `PlasticSimulator`**) + `conditions/b_plastic.py`, `d_plastic.py` | `PlasticityEngine`, `WeightState`, `RewardDelivery`, `ModulationRewardProvider` | A′ (eta = 0 through the plastic path) reproduces A bit-identically; eta > 0 changes weights and only weights |
| **8.7** Condition E | `evaluation/` MLP, REINFORCE, matched observation builder | torch; same environment | E-matched trains on training seeds and evaluates on disjoint seeds; no privileged input reaches the model |
| **8.8** Campaign | `run_campaign.py` over 6 conditions × 10 seeds × 10 episodes | 8.2–8.7 | 2 seeds completed with all artifacts valid before the full run is authorised |
| **8.9** Analysis | `analyse_phase_8.py` — exact sign-flip, Holm, bootstrap, effect sizes, floor decomposition, figures | `information/` for the descriptive block only | reproduces the §7 numbers from the JSONL; no hand-entered values |
| **8.10** Report | `reports/PHASE_8_RESULTS.md` + `.json` + a freeze record | — | integrity 36/37 non-README; every limitation restated |

Ordering rationale: A first (it is the reference and it must reproduce Phase 7 bit-for-bit), the
pilot before C/F/B/D (it decides whether the campaign can run at all), C before B/D (B/D need a
second substrate to make H2 meaningful), F before B (F is cheap and diagnoses decoder-vs-network),
E last (it is the least coupled and needs no neural substrate).

---

## 11. Known limitations

**Biological model**

1. BANC v888 is an adult female brain + VNC; it lacks the lamina and ocellar ganglion.
2. The neuron model is a single-compartment leaky integrate-and-fire unit: capacitance 200 pF, leak
   10 nS, rest −65 mV, threshold −50 mV, reset −68 mV, refractory 2 ms, floor −90 mV. No
   morphology, no dendritic computation, no receptor kinetics, no short-term plasticity.
3. Weights are `min(5·count^0.75, 300) pA` from structural synapse counts. They are not
   conductances and not measurements of synaptic strength.
4. Only **683,100 of 1,535,710 edges (44.48%)** have a verified transmitter sign. **852,610 edges
   are inert.** A neuron's effective sign is a coarse two-class proxy.
5. **65,292 of 172,433 neurons** carry a verified transmitter annotation; 107,141 do not.
6. **24,320 nodes are isolated** at threshold 5.
7. Propagation delay is uniform at 1 ms; the delay-matched coincidence rule is a convention.
8. One capped edge produces at most 4.7 mV of depolarization; four coincident edges are needed to
   fire. Recruitment is therefore synchronicity-gated, not rate-gated.

**Sensory interface**

9. **7 of 14** `GameState` features have a mapped population. Player lane, player speed, jumping,
   rolling, coin presence, coin lane and coin distance are **unmapped**.
10. The feature→population assignment is the Phase 4H.4 hypothesis/convention, not a measured
    sensory pathway.
11. Distances are normalised game-world units, not metres.
12. The drive is a fixed 200 pA per active feature with zero-order hold; there is no adaptation,
    and total injected current reached 13,476.67 pA in Phase 7 while only 71 of 232 targeted
    neurons fired.

**Motor interface**

13. LEFT / RIGHT / JUMP are decoder labels derived from published effector annotations, not
    identified biological motor commands. 391 of 805 motor neurons are assigned; **414 are not**.
14. **ROLL and DUCK have no motor population** in this export. They are never inferred, never
    proxied, and execute `NO_ACTION` with an explicit reason.
15. The decoder is a fixed threshold rule (activation 0.20, release 0.10, ≥3 active ∧ ≥5 spikes,
    50 ms half-open window). These numbers were declared, not fitted.

**Task and environment**

16. The game is a synthetic 2D endless runner. It is not a fly behaviour, not a naturalistic
    stimulus, and not a measurement of anything biological.
17. Reward is synthetic: coin +1, collision −1, survival +0.01/step, obstacle reward 0.0 (inert).
18. The observation contains only currently visible, spawned objects. There is no future-obstacle
    information and none is inferred.
19. `max_steps` 900 is a truncation convention that censors survival.
20. Game time (16.67 ms) and neural time (0.5 ms) are bridged by
    `target_step = round(game_ms / 0.5)`; the residual rounding error is bounded at half a neural
    step and does not accumulate, but the two clocks are not physically coupled.

**Design**

21. The primary outcome has one degree of freedom per seed and N = 10 seeds; the smallest attainable
    two-sided p is 0.00195 and the MDE is ~53 updates against a declared SEI of 100. This design can
    detect large effects only.
22. σ_paired = 60 is an **assumption** extrapolated from a 3-seed pilot with sd 67.3.
23. The degree-preserving null preserves in/out degrees, signs, node identities and the weight
    multiset, but **not** component structure or per-neuron outgoing weight sums. C is therefore not
    a pure "wiring only" null.
24. E-matched is not a matched control for plasticity: it has direct credit assignment to its own
    parameters. Comparisons involving E are explanatory.
25. F is expected to fail if motor populations are silent. If F succeeds only through a constant
    action learned from its bias term, that is reported as an alternative explanation, not as
    "the readout learned to play".
26. Readout training is not synaptic plasticity and must never be summarised as such.
27. The floor predicted by Phase 7 means the confirmatory family may be **uninformative by
    construction**. That possibility is preregistered here, before the data.
28. Phase 6's confirmatory negative result stands unchanged; Phase 8 information measures are
    descriptive and cannot revise it.

---

## 12. Unresolved decisions requiring approval

Each item states the options and a recommendation. None is applied.

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| **U1** | What to do if the pilot confirms the floor (no non-`NO_ACTION` action in A or F) | (a) run the full campaign anyway and report a floor result; (b) stop, report the floor + pathology decomposition, and request a scope decision; (c) authorise a *separate, pre-registered* follow-up that changes drive/decoder — which would be Phase 9, not Phase 8 | **(b)** then decide with the user. Never (c) inside Phase 8 |
| **U2** | eta for B and D | (a) reuse Phase 5's declared 0.5; (b) re-derive; (c) add a second declared eta as an exploratory arm | **(a)**. It was declared before any run and tuning it on the game would be a confound. Option (c) is acceptable but doubles B/D cost |
| **U3** | Primary outcome | (a) censored survival updates; (b) total task reward; (c) survival with reward as co-primary | **(a)**. Reward is coin-dominated and coin is unmodelled in the drive, so (b) would compare conditions on an unreachable signal |
| **U4** | Random-null scope | (a) standard degree-preserving rewire only; (b) also a component-preserving variant; (c) also a degree-only (unsigned sign randomization) variant | **(a)** confirmatory, **(b)** exploratory. Report component structure for both regardless |
| **U5** | Condition E implementation | (a) direct REINFORCE against the existing 5-tuple API (no install); (b) install Gymnasium + Stable-Baselines3 and wrap the game | **(a)**. (b) adds two dependencies, a new env-contract surface and a version-pinning obligation, for no scientific gain |
| **U6** | Evaluation episode count K | (a) K = 10; (b) K = 5; (c) K = 20 | **(a)**. Primary unit is the seed; K = 10 gives a stable within-seed mean at the measured 22 s/episode |
| **U7** | Number of seeds N | (a) 10; (b) 16; (c) 20 | **(a)**, with the §7.4 escalation rule. Confirm only after the pilot measures σ_paired |
| **U8** | Whether to run E-full (14 features) | (a) yes, exploratory; (b) no | **(a)**. It is cheap and quantifies what the 7 unmapped features would be worth |
| **U9** | Whether B/D plasticity runs during evaluation episodes or only in a separate training phase | (a) during evaluation, as in Phase 5; (b) train then freeze, then evaluate | **(a)** for the primary (it measures the closed loop as specified), **(b)** as an exploratory "trained-then-frozen" arm. (b) alone would misrepresent the online mechanism |
| **U10** | Whether to add a no-action baseline condition | (a) no, use the analytically known floor; (b) add a 7th condition that always emits `NO_ACTION` | **(a)**. The floor is exactly the survival of a `NO_ACTION` agent with the same seeds and is computed from the paired episodes at zero cost |
| **U11** | Compute budget ceiling | (a) accept ~10–45 h single-process; (b) cap at ~10 h and drop K to 5; (c) parallelise across CPUs with a determinism audit | **(a)**; consider (c) only after the pilot, and only with per-process thread pinning |
| **U12** | Whether Phase 8 may write a new `learning/` implementation | The roadmap names `learning/dopamine.py`, `learning/synaptic_plasticity.py`, `learning/mutual_information.py` — all currently one-line placeholders | Keep them untouched; Phase 8 lives in `experiments/phase_8/`, `readout/`, `experiments/phase_8_random/`, `evaluation/`. Filling `learning/` would imply the Phase 5 mechanism is being replaced |

---

## Appendix A — Interface inventory (verified in source)

| Interface | Location | Signature / contract used by Phase 8 |
|---|---|---|
| `BancConnectome` | `brain/banc_graph.py` | CSR `out_indptr`, `edge_src`, `edge_dst`, `edge_weight`, `in_indptr`, `in_edge_idx`; `root_ids` strictly ascending; no self-edges; weights ≥ threshold |
| `BancSimulator` | `brain/banc_simulator.py` | per step: synapses → current → `neurons.step` → `recorder.record` → propagate; `run()` resets first; no public single-step |
| `LiveBancStepper` | `environment/live_loop.py:162` | `advance_to_step(target)` (absolute, monotonic), `reset()`, `step_index`, `time_ms`, `transmitted_spikes`, `resets`, `weight_fingerprint()` |
| `LiveSensoryDrive` | `environment/live_loop.py:297` | `set_state`, `apply(step, time_ms, current_pa)`, `stimulated_indices`, `feature_currents()`, `unmapped_features` |
| `NeuralClosedLoop` | `environment/live_loop.py:528` | `run(seed=, max_updates=)`; validates decoder/stepper neuron counts, drive bounds, clock dt match; returns records + summary + fingerprint |
| `decode_trailing_window` | `environment/live_loop.py` | decodes `[end − window, end)` from the recorder |
| `episode_fingerprint` | `environment/live_loop.py` | `spike_sha256`, `action_reward_sha256` |
| `PlasticSimulator` | `plasticity/plastic_simulator.py` | batch `run()` only; `reward_provider.step(step, time_ms, context)`; `step_callback`; **no incremental step** |
| `PlasticityConfig` | `plasticity/config.py` | enforces `fixed_mode_eta == 0.0`; validates simulation keys |
| `WeightState` | `plasticity/weights.py` | `digest()`, `describe()`, bounds, clamps, saturation |
| `GameActionDecoder` | `motor/action_decoder.py` | `decode_window`, `decode_series`, `decode_recorder`; `MotorOutput` with activation and raw scores |
| `ControlledGameEnvironment` | `environment/subway_environment.py` | `reset(seed)`, `step(action)` → 5-tuple, `save_recording`, `action_counts()`, `summary()` |
| `GameRewardFunction` | `environment/reward_function.py` | `schedule(delay_ms)`, `modulation_provider(config)`; component-sum assertion |
| `load_world` | `experiments/phase_4h/common.py` | assembles graph, nodes, policy, populations, decoder config, neuron params |
| `run_spiking_episode` | `experiments/phase_5/controlled_task.py` | single-episode driver with explicit seeds and reward shuffler |

## Appendix B — Discrepancy register

| # | Requirement | Reality | Resolution |
|---|---|---|---|
| D1 | `experiments/baseline/` | `experiments/baseline.py` is a Phase 2 runner | Phase 8 uses `experiments/phase_8/`; no file is renamed |
| D2 | `experiments/connectome/` | `experiments/phase_4h/common.py` | reuse, no new package |
| D3 | `experiments/plasticity/` | `plasticity/` + `experiments/phase_5/` | reuse; additive stepper only |
| D4 | `experiments/random_network/` | absent | new `experiments/phase_8_random/` (G3) |
| D5 | `src/fly_surfer/evaluation/` | no `src/` tree | new top-level `evaluation/` |
| D6 | Stable-Baselines3 | absent; game is not Gymnasium | U5(a): direct implementation |
| D7 | "analyse information measures" | Phase 6 result is negative and frozen | descriptive-only block; no reinterpretation |
| D8 | "compare performance across multiple episodes" | only single-episode runners exist | G5 campaign harness |
| D9 | "test randomised networks" | no full-scale generator | G3 |
| D10 | conventional baseline | Phase 5F perceptron is `privileged: true`, `matched_control: false` | G4 |

---

## Appendix C — Declared constants (all proposals, none in force)

| Constant | Proposed value | Basis |
|---|---|---|
| `MASTER_SEED` | 20261116 | declared, follows the Phase 7 convention |
| N (seeds) | 10 | §7.4 |
| K (evaluation episodes/seed) | 10 | U6 |
| training episodes/seed (F) | 20 | declared |
| training episodes (E) | 2,000 gradient updates | declared |
| truncation cap | 900 updates | game config, unchanged |
| SEI | 100 updates | declared convention |
| α | 0.05 two-sided, Holm m = 3 | §7.5 |
| sign-flip assignments | 1,024 (exact) | 2^N |
| bootstrap resamples | 10,000 | §7.7 |
| eta (B, D) | 0.5 | Phase 5 declaration, no retuning |
| weight bounds | 0.5–2.0× initial, 5 pA/update | `configs/plasticity_banc.yaml` |
| τe | 20 ms | `configs/plasticity_banc.yaml` |
| modulation | gain 1.0, τ 50 ms, clip ±5 | `configs/plasticity_banc.yaml` |
| sensory current | 200 pA per active feature | `configs/banc_sensory_mapping.yaml` |
| decoder window | 50 ms, ≥3 active, ≥5 spikes, activation 0.20, release 0.10 | `configs/motor_decoder.yaml` |

---

*End of draft. No experiment has been implemented or run. No file outside this document has been
created or modified. Awaiting approval of §12.*
