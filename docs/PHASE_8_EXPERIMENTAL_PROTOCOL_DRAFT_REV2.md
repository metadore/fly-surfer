# Phase 8 — Training and Comparison: Experimental Protocol (DRAFT)

| field | value |
|---|---|
| status | **DESIGN / PREREGISTRATION DRAFT, REVISION 2 — NOT APPROVED, NOT EXECUTABLE** |
| date | 2026-11-16 |
| scope | design and preregistration only |
| executes anything | no — no training, no episodes, no weight change, no plasticity, no installs |
| revision | **REV2**: corrected exact sign-flip p-values and Holm minima; condition F constant-action control (Fβ), per-decision motor record, ablation classification and evidence bar E1–E5; condition C randomization validation R1–R18; A′/C′ exactness specification P1–P19 with hard stop; U1–U12 ambiguity review plus new decisions U13–U18 |
| supersedes | V1, preserved byte-identical at `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` (SHA-256 `d9d13a6c…fc505`) |
| blocking gate | human approval of §12 before any code is written |

### Revision 2 correction notice

REV2 changes **eight** things and nothing else. Sections not listed below are V1 unchanged.

1. §7.3/§7.5/§11: the minimum attainable **two-sided** exact sign-flip p at N = 10 was stated as
   0.000977. That is the *one-sided* minimum. The two-sided minimum is **2/1024 = 0.001953125**.
   All derived thresholds, the Holm minimum, the confirmatory family size and the power statements
   are corrected.
2. §3.6/§3.8/§5.4: condition F now has a defined constant-action control (Fβ), a per-decision
   motor-activity record, an operational motor-driven vs bias-driven distinction, and an explicit
   evidence bar that forbids any neural-learning claim while the motor populations are silent.
3. §3.3: condition C randomization now has a full validation report — accepted/rejected swaps,
   rewired fraction, in/out degree preservation, sign preservation, weight-multiset preservation,
   duplicates and self-edges, plus randomization-quality and reproducibility gates. Attempted swap
   count is explicitly rejected as sufficient evidence.
4. §3.8/§10: A′ (eta = 0) exactness is now specified field by field, required on **all** campaign
   seeds and evaluation episodes, and defined as a hard stop for B on any mismatch. A companion C′
   (eta = 0 on the random graph) is proposed for D and raised as decision U13.
5. §4/§5.3: V1 labelled H3 exploratory while C1 = F − A appeared in the confirmatory family. This
   contradiction is resolved: H1, H2 and H3 are confirmatory and map onto C2, C3 and C1.
6. §6.7/§12: train/eval separation was written as if all conditions train. Only E and F train; A–D
   have no training phase at all. Corrected. The U1–U12 review findings are in §12.1.
7. §9.2/§11/U7/U10/U11: the compute budget, the power statement and the no-action-floor statement
   are re-derived for the new control arms and the corrected p-value floor. Declared budget is
   now ≈ 19 h measured / ≈ 78 h worst case; N = 16 is the recommended default with N = 10 the
   declared floor.
8. §3.3/§3.3.1: the swap parameterisation was unstated and one §3.3 row ("per-neuron sum of outgoing
   weight is not preserved") contradicted the exact-preservation gates. Made explicit, R9b added,
   and the choice raised as U18.

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

G1–G7 are unchanged from V1. REV2 adds three **control arms** that also do not exist yet and are now
required for interpretation: **A′** (biological graph, `eta = 0`, must equal A exactly), **C′**
(random graph, `eta = 0`, must equal C exactly — proposed, see U13) and **Fβ** (bias-only readout,
the constant-action control for F). They reuse the same code paths as B, D and F respectively, so
they add runtime rather than new mechanisms. §9.2 accounts for the extra cost.

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
| — | Internal validity arm **A′** | A executed through the **same plastic code path** with `eta = 0`. Required to reproduce A **exactly** — spike stream, every record field, action/reward trace, termination, and weights — on **every campaign seed and every evaluation episode**. Comparison fields, hashes and the failure protocol are specified in §3.8. Any mismatch makes B uninterpretable and stops the B campaign |
| 12 | Scientific question | Does reward-modulated structural plasticity change behaviour, holding connectivity, drive and decoder constant? |

### 3.3 Condition C — Random network, fixed weights

Rows 1, 4–7, 10 identical to A except topology.

| # | Aspect | Specification |
|---|---|---|
| 2 | Connectivity source | **Declared null**: a signed, degree-preserving directed randomization of the BANC t5 edge list |
| 3 | Weight initialization | The original weight multiset is preserved and permuted with the edges; node identities, annotations and signs are **unchanged** |
| — | Null construction | Directed double-edge swaps on `(source, target)` with rejection of duplicates and self-loops; seeded from the dedicated `structure` RNG stream; **one graph per seed**, generated once and shared by C, D and C′ so that C−D and A−C are paired on the same topology. **Parameterisation** (recommended, U18): each edge keeps its source neuron and its weight, and a swap exchanges the **targets** of two edges drawn from distinct sources with distinct targets — so out-degree, in-degree and every source's outgoing weight profile are preserved by construction |
| — | Preserved exactly | Per-node out-degree; per-node in-degree; the global weight multiset; every source's outgoing weight multiset; per-node transmitter sign and every annotation column; therefore the LEFT 185 / RIGHT 186 / JUMP 20 populations and every motor neuron's in-degree |
| — | Not preserved (declared) | Weak-component sizes; which source talks to which target; per-target **incoming** weight sums (targets receive different sources' weights) |
| — | Validation gate | Not a single check but a report: §3.3.1. The graph is rejected, and the campaign does not proceed, if any gate in §3.3.1 fails |
| 11 | Potential confounds | A rewire changes global connectivity as well as local wiring; the null therefore conflates "which neurons connect" with "how the graph fragments". A component-preserving variant is listed as exploratory (U4) |
| 12 | Scientific question | Does the specific biological wiring matter, or would any graph with the same degrees and signs do as well? |

### 3.3.1 Condition C — randomization validation

**A swap count is not evidence of randomization.** An attempted-swap target (previously "≥ 10·E")
is a minimum-effort floor, not a mixing guarantee: a chain can attempt 15 million swaps and reject
most of them, or accept them while leaving almost every original pair intact. The gates below are
the actual evidence. Every gate is evaluated per generated graph and its full report is written into
the run manifest and into every C, D and C′ episode record (`randomization_quality`).

**Required report**

| # | Quantity | How measured | Gate |
|---|---|---|---|
| R1 | Swaps attempted | counter | reported only |
| R2 | Swaps accepted | counter | reported only |
| R3 | Swaps rejected, by reason | counters for `duplicate_pair`, `self_loop`, `no_change`, `out_of_range` | reported only; acceptance rate = accepted / attempted is reported and must exceed 0 to make progress |
| R4 | Fraction of original edges rewired | `1 − |E_orig ∩ E_new| / |E_orig|` on directed `(src, dst)` pairs | **≥ 0.99** |
| R5 | Edge-set Jaccard | `|∩| / |∪|` vs the original | **≤ 0.01** |
| R6 | Out-degree preservation | `max_i |out_new[i] − out_orig[i]|` | **exactly 0**, and `sum(out_new) = 1,535,710` |
| R7 | In-degree preservation | `max_i |in_new[i] − in_orig[i]|` | **exactly 0**, and `sum(in_new) = 1,535,710` |
| R8 | Transmitter sign preservation | per-node sign vector unchanged (identities are not permuted) | **exactly equal**; signed edge count stays 683,100. Signed synapse sum (8,426,168) is exactly preserved **only** under the recommended target-exchange parameterisation of U18; under endpoint re-pairing it is reported, not gated |
| R9 | Weight multiset preservation | `np.sort(weight_new)` compared elementwise with `np.sort(weight_orig)` | **exactly equal**; sum 18,552,546; min 5; max 913 (these are the stored synapse counts, which the simulator transforms to pA at load) |
| R9b | Per-source outgoing weight preservation | for every node, the sorted multiset of its outgoing weights, before vs after | **exactly equal** under the U18 recommendation; this is what makes R8's signed-synapse gate meaningful |
| R10 | Duplicate pairs | count of repeated `(src, dst)` | **0** |
| R11 | Self-edges | count of `src == dst` | **0** |
| R12 | CSR invariants | `BancConnectome.__post_init__` plus the Phase 4D construction checks | **all pass** |
| R13 | Neighbourhood overlap | mean over nodes of Jaccard(out-neighbours_orig, out-neighbours_new), unweighted | **≤ 0.01** — catches a chain that preserves degrees while barely moving edges |
| R14 | Mixing plateau | recompute R5 every 10⁵ accepted swaps; require the last 20% of accepted swaps to change Jaccard by **< 1e-4 absolute** | **must plateau**; a still-trending chain is not reported as randomized |
| R15 | Component structure | weak-component count and size distribution, before vs after | **reported, not gated** — the change is the intended effect of randomization and must be visible in the results |
| R16 | Reciprocity and degree assortativity | directed reciprocity and (optional) degree assortativity, before vs after | reported, descriptive |
| R17 | Reproducibility | two independent constructions from the same seed | `edge_src`, `edge_dst`, `edge_weight` **byte-identical**; graph digest identical |
| R18 | Graph seed derivation | `SeedSequence([MASTER_SEED, seed, "structure"])` | recorded per graph; disjoint from the environment, network and learning streams |

**Rejection protocol.** If any of R4–R14 (including R9b) or R17 fails, the graph is **rejected and not used**. The
condition does not silently fall back to a less-random graph. The campaign halts for that seed,
records which gate failed and the full report, and reports the halt. Rerunning with a different seed
is allowed; rerunning with a relaxed gate is not.

**Why R13 and R14 exist.** R4/R5 alone can be satisfied by a chain that has swapped edges only among
a small subset of nodes. R13 detects that the local neighbourhoods are still almost identical; R14
detects that the chain has not mixed. Both are cheap and both must pass before the graph is called
a null.

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
| 4 | Weights fixed or changing | **Connectome fixed, readout changes.** Asserted five ways per episode: connectome `weight_fingerprint` identical before and after; `WeightState` absent; the set of trainable tensors equals the readout parameter list exactly; the connectome arrays are never written in place; and a `connectome_unchanged` boolean accompanies every episode. Readout parameters are checkpointed, never applied to the graph |
| 5 | Learning algorithm | REINFORCE over the readout only. Features = per-decision motor-population activity (§3.6.1). Linear or one-hidden-layer readout; declared in config, not tuned per seed |
| 6 | Inputs / observations | Same 7-feature sensory drive as A. The readout does **not** receive the sensory features directly — only the motor-population activity they evoke. This keeps it a *decoder of neural output*, not a second controller |
| 7 | Action selection | Readout over {LEFT, RIGHT, JUMP, NO_ACTION}. **ROLL and DUCK are excluded**: no motor population exists for them in this export, so a readout "learning" them would be ungrounded. Categorical sampling at training, argmax at evaluation |
| 8 | Reward handling | Same task reward; used only as the readout's learning signal, never as a synaptic modulator |
| 9 | Training / evaluation | Train readout on training seeds; evaluate on disjoint seeds. Connectome never resets between updates within an episode; readout frozen at evaluation |
| 10 | Required recordings | Everything in A, plus the per-decision motor block (§3.6.1), readout inputs and logits, sampled action, readout parameters per checkpoint, `connectome_unchanged` with both fingerprints, and the per-decision ablation record (§3.6.3) |
| 11 | Potential confounds | The decisive one: a readout with a bias term can learn a **constant action** with no motor information at all. F must therefore be interpreted against Fβ (§3.6.2), not against A alone. Secondary: the readout sees only motor-population output; if those populations are silent (Phase 7: 0 motor spikes in 213 updates) the readout has no state signal and its best policy is a constant action. Readout training is **not** synaptic plasticity |
| 12 | Scientific question | Is the failure of the fixed loop a **decoder** problem or a **network** problem? F is the cleanest test in this phase — but only if the motor-dependence bar in §3.6.4 is met |

#### 3.6.1 Per-decision motor recording

Every decision in A, B, C, D, F and Fβ records, in the **same half-open window**
`[end − window_ms, end)` that the decoder uses:

```
"motor_activity": {
  "window_start_ms": float, "window_end_ms": float, "window_rule": "[start, end)",
  "source": "recorder",
  "total_spikes": int, "any_motor_spike": bool,
  "populations_with_spikes": [str, ...],
  "LEFT": {"spikes": int, "active_neurons": int, "active_fraction": float,
           "mean_rate_hz": float, "sufficient": bool},
  "RIGHT": {...}, "JUMP": {...}
}
```

This is **additive**. It changes no Phase 7 artifact and no Phase 7 record field. It is required at
top level because `record["decoder"]` is `null` whenever the decoder returns `None`, and because the
readout must consume the block without depending on the fixed-threshold decoder being present.
(The Phase 7 `record["decoder"]["evidence"][<action>]` block already carries per-population `spikes`,
`active_neurons`, `active_fraction`, `mean_rate_hz` and `sufficient`; REV2 requires the same
quantities to exist independently of it, and requires the record to exist for every decision in
every condition, including those that never call the fixed decoder.)

Float fields in the block are rounded at the producer to the same precision as the existing record
(6 dp for times, rates and fractions; counts remain integers), so equal motor activity serializes to
identical JSON in A and A′ — which is what comparison field P10 in §3.8.3 relies on.

#### 3.6.2 Constant-action control Fβ

**Definition.** Fβ is condition F with the readout's feature path removed: the input to the trainable
layer is the zero vector, so only the bias term trains. Its policy is therefore state-independent —
the best constant (possibly stochastic) action distribution for the training reward. Same seeds,
same environment, same frozen connectome, same readout architecture and optimizer. The only
difference from F is that motor activity cannot influence the decision.

**Interpretation of the three readout contrasts.**

| Contrast | What it measures |
|---|---|
| `F − Fβ` | the value of **motor-driven state-dependence** over the best constant policy — the only contrast that can support a decoding claim |
| `Fβ − floor` | the value of choosing a better constant action than `NO_ACTION` |
| `F − A` | the value of replacing a fixed threshold rule with a learned one, which may be entirely bias-driven |

**The `NO_ACTION` floor must be measured, not assumed.** It is obtained by replaying the paired
environment seeds with a deterministic constant-`NO_ACTION` policy on the neural substrate; it costs
seconds and it is the same quantity that Fβ converges to when `NO_ACTION` is the best constant
action. Collision timing depends on layout, so the floor cannot be derived analytically.

**Optional stronger control, exploratory only.** `F-shuffled` replaces the motor features with a
time-shuffled copy of the same episode's features, destroying the temporal correspondence while
preserving marginal statistics. It is listed as exploratory so it cannot be promoted after seeing
results.

#### 3.6.3 Motor-driven versus bias-driven decisions

For every decision in F and Fβ evaluation episodes, a counterfactual is recorded. Ablation rule,
fixed in advance: set the readout's motor-feature input vector to exactly `0.0` and recompute the
logits from the **same frozen parameters**. No retraining, no gradient, no environment step, no
extra rollout.

| label | operational definition |
|---|---|
| **motor-driven** | ablation **changes** the argmax action, and ≥ 1 spike occurred in the population of the chosen action within the window |
| **bias-driven** | ablation leaves the argmax action unchanged |
| **undefined** | chosen action is `NO_ACTION` and no motor population spiked in the window — no motor evidence either way |

Reported per condition per episode: counts and fractions of each label; the ablation-change rate;
and the agreement between the ablated and unablated policy. All three are written to the episode
row, so the classification is auditable without rerunning anything.

#### 3.6.4 Evidence required before claiming useful motor decoding

All five must hold before any sentence of the form "the readout learned to decode motor activity"
may appear in a report, abstract or figure caption.

| E# | Evidence | Threshold |
|---|---|---|
| E1 | `F − Fβ > 0` on paired seeds | confirmatory contrast C4, exact sign-flip, survives Holm |
| E2 | `F − A > 0` on paired seeds | confirmatory contrast C1, exact sign-flip, survives Holm |
| E3 | motor populations not silent | ≥ 1 LEFT/RIGHT/JUMP spike on ≥ 1% of decisions, in ≥ half of seeds |
| E4 | a non-trivial fraction of decisions are motor-driven | ≥ 10% of non-`NO_ACTION` decisions classified motor-driven (§3.6.3), declared in advance |
| E5 | the ablation effect is not a numerical artefact | a fresh-process rerun reproduces the motor-driven count exactly |

**If E3 fails, no claim of neural learning is permitted at all** — not "weak evidence", not "a
trend". The permitted statement is exactly: "the motor populations were silent; the readout could at
most learn a constant policy." If E1 or E2 fails, the conclusion is "no evidence that the readout
used motor information", regardless of how well F scores.

#### 3.6.5 Statements forbidden in every Phase 8 report

- "the connectome learned" — the connectome is frozen; only the readout changed;
- "plasticity improved performance" in condition F — F contains no plasticity;
- "the readout succeeded" when Fβ scores the same — that is a constant action, not a decoder;
- "F beat the baseline" without naming which baseline, because `A` (fixed decoder) and `Fβ` (best
  constant policy) support different claims.

### 3.7 Condition summary

| | topology | weights | decoder | learns |
|---|---|---|---|---|
| A | biological | fixed | fixed threshold | nothing |
| B | biological | plastic | fixed threshold | synapses (3-factor) |
| C | randomized, degree+sign preserved | fixed | fixed threshold | nothing |
| D | randomized, degree+sign preserved | plastic | fixed threshold | synapses (3-factor) |
| E | none (MLP) | trained | argmax over 4 logits | all parameters (policy gradient) |
| F | biological | **fixed** | **trained readout** | readout only |

**Control arms** (not conditions; they produce no new scientific claim of their own):

| arm | topology | weights | decoder | learns | must satisfy |
|---|---|---|---|---|---|
| **A′** | biological | fixed, through the plastic code path at `eta = 0` | fixed threshold | nothing | exactly equals A on every seed and episode (§3.8) |
| **C′** (proposed, U13) | randomized `G_s` | fixed, through the plastic code path at `eta = 0` | fixed threshold | nothing | exactly equals C on every seed and episode |
| **Fβ** | biological | fixed | bias-only readout | bias term only | the constant-action control for F (§3.6.2) |
| **floor** | biological | fixed | constant `NO_ACTION` | nothing | the measured no-action survival on the paired seeds |

### 3.8 Internal validity controls A′ and C′

#### 3.8.1 Purpose

A′ runs the biological fixed-weight condition through the **same code path used by B**. It exists to
prove that the plasticity implementation is an exact identity when `eta = 0`, so that any `B − A`
difference is attributable to the learning rule and not to the mere act of routing the episode
through the plastic pipeline — different data structures, different arithmetic order, different
float32/float64 casts, different clamp bookkeeping. Without A′ a `B − A` difference cannot be
attributed to plasticity at all.

C′ is the same control on the random graph `G_s`, and is the corresponding safeguard for D. It is
proposed rather than assumed because it doubles C's evaluation cost; see U13.

#### 3.8.2 Required coverage

- A′ on **all N campaign seeds × all K evaluation episodes** — a full mirror of A, not a sample.
- One **fresh-process** replay of A′ episode 1 per seed, to confirm cross-process determinism.
- `eta` is exactly `0.0` — not `1e-12`, not a "learning disabled" flag that skips the rule
  entirely. The rule must execute and return an exactly zero delta, unless §3.8.4's documented
  short-circuit applies.

#### 3.8.3 Comparison fields — all must be equal to A

| # | Field | Source | Comparison |
|---|---|---|---|
| P1 | spike times | `recorder.spike_times_ms` | exact array equality |
| P2 | spike neuron indices | `recorder.spike_neuron_indices` | exact array equality |
| P3 | `spike_sha256` | `episode_fingerprint` | string equality |
| P4 | `action_reward_sha256` | `episode_fingerprint` | string equality |
| P5 | full record sequence | `records[]` | equality of the serialized JSON (sort keys, separators `(",", ":")`); all float fields are already rounded by the record producer |
| P6 | survival and termination | `summary`: `updates`, `terminated`, `truncated`, `termination_reason` | equal |
| P7 | action and decoder-state counts | `summary` | equal |
| P8 | reward total and every component | `summary` | equal |
| P9 | `neural_steps`, `neural_time_ms`, `game_time_ms` | `summary` | equal |
| P10 | `motor_activity` per decision | each record | equal (§3.6.1) |
| P11 | structural weight digest | `WeightState.digest()` | equal |
| P12 | initial weight digest | `WeightState.digest()` | equal |
| P13 | learned-delta digest | `WeightState.digest()` | equal **and** the delta array is exactly all zeros |
| P14 | effective weight digest | `WeightState.digest()` | equal, and equal to A′'s own initial digest |
| P15 | `max |Δw|` | `WeightState.describe()` | exactly `0.0` |
| P16 | changed edges | `WeightState.describe()` | `0` |
| P17 | clamp hits and saturation count | `WeightState.describe()` | `0` |
| P18 | stepper weight fingerprint | `weight_fingerprint()["sha256"]` | equal before and after, and equal to A's |
| P19 | resets during the episode | `stepper.resets` | equal |

#### 3.8.4 Tolerance: none

**Every comparison in §3.8.3 is exact.** No numeric tolerance is permitted. The claim under test is
that `eta = 0` is an *identity*, and "almost identical" does not establish identity. A tolerance
would convert a correctness property into a similarity heuristic.

One documented nuance: eligibility traces are expected to be **non-zero**, because the trace
machinery still runs and traces are a property of activity, not of the learning rate. What must be
exactly zero is every **weight delta**. Either implementation choice is acceptable — the rule may
compute traces and multiply by `eta = 0`, or it may short-circuit `learn()` — provided the episode
record states which behaviour occurred (`plasticity_path.mode ∈ {"rule_executed_zero_delta",
"short_circuited"}`).

#### 3.8.5 Failure protocol — a hard stop

1. On the first mismatch, stop the A′ run and write an `a_prime_mismatch` record containing the
   field ID, seed, episode, both values and both hashes.
2. **B is immediately marked INVALID for interpretation.** Any B result already produced is
   **retained** in the artifact store, labelled INVALID, and excluded from every aggregate, table
   and figure. It is not deleted.
3. The campaign does **not** retry with a different seed until a match is obtained. Selecting a
   passing seed is selecting on the outcome and is forbidden.
4. The report must state which of two conclusions applies:
   - **(a) the plastic path is not an identity at `eta = 0`** → B is uninterpretable; the
     implementation must be corrected before any B claim can be made;
   - **(b) the mismatch is confined to a named non-scientific field** (for example rounding inside a
     diagnostic string) → that field is quarantined and disclosed, and B may proceed **only with the
     user's explicit approval**. This is not a default.
5. D shares the same plastic stepper, so an A′ mismatch is flagged against D as well. C′ (U13) is the
   corresponding control for D on the random graph.

#### 3.8.6 Where the check is applied

- in the **pilot**, on all 3 pilot seeds, before the campaign is authorised;
- on **every campaign seed**, for every evaluation episode;
- in a **final validation pass** that recomputes every comparison from the stored JSONL rather than
  from in-memory state.

---

## 4. Scientific hypotheses

Falsifiable, with the direction of the predicted effect and the observation that would refute it.
The labels are binding and match §5.3: **H1, H2 and H3 are confirmatory** (they map onto C2, C3 and
C1); **H4 is an explanatory reference**; **H5 and H6 are exploratory/descriptive and cannot be
promoted after seeing data.**

> **Revision-2 correction.** V1 labelled H3 exploratory while `C1 = F − A` sat in the confirmatory
> family. That was a contradiction inside the same document. REV2 makes H3 confirmatory, because the
> readout contrast is one of the three questions this phase exists to answer. If the user prefers the
> V1 labelling, then C1 must move out of the confirmatory family — the two cannot differ. Recorded
> as U15.

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
*Prediction:* F − A > 0 (C1).
*Refuted if:* F − A ≤ 0.
*Prior expectation:* low. If the motor populations are silent, the readout cannot exceed a constant
policy.
*Necessary condition:* H3 alone is **not** evidence of motor decoding, because a bias-only readout
can satisfy it. A decoding claim additionally requires F − Fβ > 0 (C4) and the §3.6.4 evidence bar.
H3 and the decoding claim are therefore two different statements and the report must keep them
separate.

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

### 5.3 Confirmatory family (Holm-corrected)

| ID | Contrast | Interpretation |
|---|---|---|
| C1 | **F − A** | contribution of a trainable readout on the biological substrate (H3) |
| C2 | **B − A** | contribution of three-factor synaptic plasticity on the biological substrate (H1) |
| C3 | **A − C** | contribution of biological over degree+sign-matched random connectivity (H2) |
| C4 | **F − Fβ** | whether the readout uses motor information at all, over the best constant policy (§3.6.2) |

C1–C3 are V1's family, unchanged. **C4 is added by REV2** because without it the readout claim is
not identifiable: a bias term alone can produce C1 > 0 with silent motor populations. Family size is
therefore **m = 4**, α = 0.05 family-wise. Nothing else is confirmatory; the remaining conditions are
reported but cannot be promoted after seeing data.

Because the family size changed, both variants are stated openly in §7.5 and the choice is decision
**U14**. If U14 selects m = 3, then C4 is not a confirmatory contrast and **no decoding claim may be
made at all** — C4 would be demoted to exploratory and could not support the §3.6.4 evidence bar,
which requires a Holm-surviving test.

### 5.4 Secondary and exploratory outcomes

| Outcome | Status | Notes |
|---|---|---|
| D − C (plasticity on random substrate) | exploratory | completes the 2×2 |
| A vs E-matched | explanatory reference | E is not a matched control |
| E-full vs E-matched | exploratory | value of the 7 unmapped features |
| A′ vs A | **integrity check** | must be exactly equal on every seed and episode; any mismatch invalidates B (§3.8) |
| C′ vs C | **integrity check** (proposed, U13) | must be exactly equal; a mismatch invalidates D |
| Fβ (constant-action control) | secondary + interpretation gate | the best state-independent policy; F is never interpreted without it (§3.6.2) |
| F − Fβ | confirmatory (C4) | the only contrast that supports a motor-decoding claim |
| Motor-driven / bias-driven / undefined decision fractions | secondary, mechanism-level | per §3.6.3; reported per condition and per episode |
| Motor-population spikes per decision | secondary | recorded for **every** decision in every condition (§3.6.1); expected 0 for A–D |
| Total task reward per episode | secondary | reward is coin-dominated: coin +1, collision −1, survival +0.01/step, obstacle 0.0 (the obstacle component is configured to zero and is therefore inert) |
| Coins collected per episode | secondary | unmodelled in the sensory drive — no coin population exists |
| Collisions per episode | secondary | survival and collision count are near-redundant at this cap; reported but not tested separately |
| Obstacles avoided | **not available** | the reward component is configured to 0.0 and no per-obstacle outcome is recorded; must not be invented |
| Action distribution per condition | secondary | primary diagnostic of the floor |
| Fraction of updates with `NO_ACTION` | secondary | expected ≈ 1.0 for A–D |
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
`stream ∈ {"environment", "network", "learning", "structure"}`:

| stream | used by | examples |
|---|---|---|
| environment | `ControlledGameEnvironment.reset(seed)` | obstacle/coin placement, speed |
| network | `BancSimulator` noise (`noise_std_pa = 0` at present) | membrane noise, any synaptic stochasticity |
| learning | readout init, action sampling, training batch order | E, F |
| structure | random-graph construction | C, D, C′; one graph `G_s` per seed, shared by all three (§3.3.1, R18) |

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

This applies to **E and F (and Fβ) only**. A–D have **no training phase at all**: their weights are
either fixed (A, C) or change online under the mechanism under test (B, D), and that online change
*is* the measurement, not a training step.

- **E**: training seeds and evaluation seeds are disjoint ranges; disjointness is asserted at run
  start. Evaluation uses a frozen policy, argmax action selection and no gradient step.
- **F / Fβ**: readout trained on training seeds, frozen at evaluation. Connectome frozen throughout.
- **A–D**: every episode is an evaluation episode. Nothing is fitted anywhere.
- For every condition, no evaluation episode may update any parameter other than those the
  condition declares as changing: synapses in B/D, readout parameters in F/Fβ, nothing in A/C/E at
  evaluation.

> **Revision-2 correction.** V1 wrote "No evaluation episode may update anything", which is false for
> B and D by construction — their whole purpose is to change weights during the episode. The sentence
> is replaced by the per-condition statement above.

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

Paired, within-seed comparison. N seeds (10 declared floor, 16 recommended — U7), K = 10 evaluation
episodes per seed per condition, 6 conditions plus the **control arms** A′ and C′ (all N seeds × K
episodes, §3.8.2) and Fβ (all N seeds × K episodes, §3.6.2). The control arms enter no confirmatory
contrast between themselves; they gate interpretation of B, D and F.

### 7.2 Unit of analysis

The **seed**. Per seed and condition, the outcome is the mean over K episodes of the censored
survival. Episode-level values are also retained for the secondary analysis.

### 7.3 Primary test

Two-sided **exact sign-flip permutation test** on the 10 paired per-seed differences. Statistic: the
mean paired difference. Enumeration is exhaustive over all `2^10 = 1024` sign vectors; the p-value is
`#{s : |T(s)| ≥ |T_obs|} / 1024`. No normal approximation, no Monte Carlo, no asymptotics. Applied to
C1, C2, C3 and C4 (or C1–C3 if U14 selects m = 3). The N = 10 constants below are the declared
floor; if U7 selects N = 16 the same enumeration applies with `2^16 = 65,536` sign vectors and
minimum two-sided p = `2/65,536 = 0.0000305176`.

**Attainable p-values at N = 10 — corrected**

| bound | value | note |
|---|---|---|
| sign vectors | 1,024 | `2^10` |
| minimum **one-sided** p | 1/1024 = 0.0009765625 | V1 quoted this value and mislabelled it two-sided |
| **minimum two-sided p** | **2/1024 = 0.001953125** | the extreme statistic `|T| = Σ|dᵢ|` is attained by two sign vectors, all-plus and all-minus |
| count threshold for two-sided p ≤ 0.05 | ≤ 51 of 1,024 | 51/1024 = 0.049805; 52/1024 = 0.050781 > 0.05 |

**Tie and degeneracy policy (declared).** If every paired difference is exactly zero — the expected
case when both conditions floor — then `T(s) = 0` for all 1,024 sign vectors and `|T(s)| ≥ |T_obs|`
holds everywhere, so **p = 1.0 by definition**. The test is then uninformative by construction and
this is reported as "no difference detectable; the design has no power against a difference between
two floored conditions", never as evidence that the conditions are equivalent.

**Robustness check.** A two-sided exact sign test (binomial on the count of positive differences,
ties dropped) is reported alongside every sign-flip p. The two agree exactly when all magnitudes
are equal, which is the case that makes the sign-flip test most permissive.

### 7.4 Sample size and power

| Quantity | Value |
|---|---|
| design | N = 10 (declared floor) or N = 16 (recommended default — U7) paired seeds |
| α (two-sided, per contrast) | 0.05 |
| power | 0.80 |
| MDE formula | `MDE = (z₀.₉₇₅ + z₀.₈) · σ_paired / √N = 2.8016 · σ_paired / √N` |
| declared SEI | 100 updates |
| assumed σ_paired | 60 updates |
| MDE at N = 10, σ = 60 | **≈ 53 updates** |
| σ_paired supported at N = 10 for MDE = 100 | **≈ 113 updates** |
| escalation rule | if the pilot paired sd exceeds 113, set N = ⌈(2.8016·σ/100)²⌉ and re-run the pilot analysis before the campaign |
| **recommended default (U7)** | **N = 16** — the pilot sd from 3 seeds has `df = 2`, and its 80% upper confidence limit is ≈ 2.1× the point estimate; N = 16 keeps the MDE at SEI even if the true σ is that large |
| MDE at N = 16, σ = 60 | ≈ 42 updates |
| σ_paired supported at N = 16 for MDE = 100 | ≈ 143 updates |

**Where σ_paired = 60 comes from.** It is an **assumption**, not a measurement. The only available
dispersion evidence is the 3-seed Phase 7 pilot: random agent sd 67.3, rule-based agent sd 57.2
across seeds. These are between-seed sd of a *single* episode, not the sd of a *paired difference*.
A paired difference removes the shared environment layout, so the true σ_paired is expected to be
**smaller**; 60 is deliberately the conservative end. The pilot (§10, step 8.3) measures the real
value on 3 seeds and the escalation rule applies.

### 7.5 Multiplicity

Holm–Bonferroni, α = 0.05 family-wise, contrasts ordered by raw p. **Corrected values** — V1 wrote
`3 × 0.000977 = 0.00293`, which used the one-sided minimum. The correct minimum two-sided raw p is
`2/1024 = 0.001953125`.

**Primary variant — m = 4 (C1, C2, C3, C4), pending U14**

| Holm step | threshold | admissible count of the 1,024 sign vectors | minimum adjusted p |
|---|---|---|---|
| 1 | α/4 = 0.0125 | ≤ 12 (12/1024 = 0.011719) | 4 × 0.001953125 = **0.0078125** |
| 2 | α/3 = 0.016667 | ≤ 17 (17/1024 = 0.016602) | — |
| 3 | α/2 = 0.025 | ≤ 25 (25/1024 = 0.024414) | — |
| 4 | α = 0.05 | ≤ 51 (51/1024 = 0.049805) | — |

**Alternative variant — m = 3 (C1, C2, C3), if U14 selects it**

| Holm step | threshold | admissible count | minimum adjusted p |
|---|---|---|---|
| 1 | α/3 = 0.016667 | ≤ 17 | 3 × 0.001953125 = **0.005859375** |
| 2 | α/2 = 0.025 | ≤ 25 | — |
| 3 | α = 0.05 | ≤ 51 | — |

Holm is feasible in both variants: the minimum attainable adjusted p is below 0.05. It is also
**demanding**: with equal-magnitude differences, a 9-versus-1 split gives raw
`p = 22/1024 = 0.0215`, which fails step 1 in both variants, and an 8-versus-2 split gives
`p = 112/1024 = 0.109`, which fails outright. **Under equal magnitudes only a unanimous 10-of-10
separation can survive.** This is stated so that the design is not later described as more powerful
than it is. The real differences will not have equal magnitudes, so the binding constraint is the
count table above, not the unanimity rule.

Exploratory outcomes receive no correction and are labelled exploratory in every table, caption and
sentence.

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

This is a **post-campaign reporting rule**, not a stopping rule. The stop rule is U1 (zero
non-`NO_ACTION` in A and F at pilot time). If the primary outcome is at floor in ≥ 4 of 6 conditions:

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
| one condition × 10 seeds, eval only | 10 × 3.7 min | 0.62 h |
| one condition × 10 seeds, eval only | 10 × 15.7 min | 2.62 h |
| 5 conditions (A, B, C, D, F) eval | both ends | 3.1 h – 13.1 h |
| **A′ mirror** of A (all seeds, all episodes) | one condition | +0.62 h – +2.62 h |
| **C′ mirror** of C, if U13 approves | one condition | +0.62 h – +2.62 h |
| **Fβ** eval (all seeds, all episodes) | one condition | +0.62 h – +2.62 h |
| **F training rollouts** (20 episodes/seed) | measured rate | +6.2 h – +26.2 h |
| **Fβ training rollouts** (20 episodes/seed) | measured rate | +6.2 h – +26.2 h |
| B/D plasticity overhead | assumed +20–40% (trace update on ≤683,100 edges) | +0.25 h – +2.1 h |
| random-graph construction (one per seed, 10 graphs) | assumed 2–15 min per graph | 0.3 h – 2.5 h |
| E training and evaluation | torch CPU, 7 or 14 inputs, 4 outputs | < 10 min total |
| analysis, figures, replay checks | | < 30 min |

**Declared budget, single process: ≈ 19 h at the measured rate, ≈ 78 h at the 900-update worst
case, for N = 10.** N = 16 scales every per-seed line by 1.6, giving ≈ 30 h and ≈ 125 h. V1 quoted
10–45 h because it omitted the control arms; the mirrors and Fβ now dominate the
lower bound. Every non-measured figure is an assumption and is labelled as such. Halving K from 10 to
5 roughly halves the evaluation half of the budget. Parallelism across 12 CPUs could reduce wall time
by up to ~8× but introduces determinism risk (BLAS thread counts, per-process memory) and is **not**
part of the primary plan.

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
| **8.3** Pilot | 3 seeds × {A, C, F, A′, Fβ} × 3 episodes | 8.1–8.2 | measures the true σ_paired; applies the §7.4 escalation rule; applies the §0 viability gate; **A′ must match A exactly on all 3 pilot seeds before the campaign is authorised** |
| **8.4** Condition C | `experiments/phase_8_random/` degree-preserving signed rewire + validator | `brain/banc_graph.py` invariants | **all of R1–R18 (§3.3.1) pass**, specifically rewired fraction ≥ 0.99, neighbourhood overlap ≤ 0.01, mixing plateau reached, zero duplicates, zero self-edges, exact degree, weight-multiset and per-source weight-profile equality (R9b); ≤ 15 min per graph |
| **8.5** Condition F and control Fβ | `readout/` module, `conditions/f_readout.py`, `controls/f_beta.py` (bias-only), the per-decision `motor_activity` block (§3.6.1) and the ablation counterfactual (§3.6.3) | torch; `GameActionDecoder` retained as the reference decoder for A–D | connectome fingerprint identical before and after; trainable-parameter set == readout parameters only; `motor_activity` present on 100% of decisions in every condition; Fβ input vector identically zero |
| **8.6** Conditions B and D + control A′ | `plasticity/live_stepper.py` (additive subclass; **no edit to `PlasticSimulator`**) + `conditions/b_plastic.py`, `d_plastic.py`, `controls/a_prime.py`, and `controls/c_prime.py` if U13 approves | `PlasticityEngine`, `WeightState`, `RewardDelivery`, `ModulationRewardProvider` | **A′ reproduces A exactly on every campaign seed and every episode across all 19 fields of §3.8.3, with zero tolerance**; `eta > 0` changes weights and only weights; on any mismatch the B campaign stops and B is marked INVALID |
| **8.7** Condition E | `evaluation/` MLP, REINFORCE, matched observation builder | torch; same environment | E-matched trains on training seeds and evaluates on disjoint seeds; no privileged input reaches the model |
| **8.8** Campaign | `run_campaign.py` over 6 conditions + the A′/C′/Fβ control arms, N seeds (10 declared floor, 16 recommended — U7) × K episodes | 8.2–8.7 | 2 seeds completed with all artifacts valid before the full run is authorised; A′/C′ exact-equality reports present for every completed seed |
| **8.9** Analysis | `analyse_phase_8.py` — exact sign-flip (two-sided, count-thresholded), Holm for m = 4 and m = 3, bootstrap, effect sizes, floor decomposition, the F/Fβ/A readout decomposition, the motor-driven versus bias-driven breakdown, figures | `information/` for the descriptive block only | reproduces every §7 number from the JSONL; no hand-entered values; the §3.6.4 evidence checklist is emitted as a pass/fail table |
| **8.10** Report | `reports/PHASE_8_RESULTS.md` + `.json` + a freeze record | — | integrity 36/37 non-README; every limitation restated; the §3.6.5 forbidden statements absent; the readout claim present only if E1–E5 all pass |

Ordering rationale: A first (the reference; must reproduce Phase 7 bit-for-bit), then the pilot
before C/F/B/D (it decides whether the campaign can run at all, and it must prove A′ ≡ A), then C
before B/D (B/D need a second substrate for H2 to mean anything), then F together with Fβ (F alone
is uninterpretable), then B with its A′ mirror, then E last (least coupled, no neural substrate).

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

21. The primary outcome has one degree of freedom per seed and N = 10 seeds. The smallest attainable
    **two-sided** p is `2/1024 = 0.001953125`; reaching raw p ≤ 0.05 requires at most 51 of the 1,024
    sign vectors to be at least as extreme as the observed one, and surviving Holm step 1 requires at
    most 12 (m = 4) or 17 (m = 3). Under equal-magnitude differences only a unanimous 10-of-10
    separation survives. The MDE is ~53 updates against a declared SEI of 100. **This design can
    detect large effects only.**
22. σ_paired = 60 is an **assumption**, extrapolated from a 3-seed pilot whose observed sd was 67.3.
    A standard deviation estimated from 3 points has 2 degrees of freedom and is extremely unstable.
    The 80% one-sided upper confidence limit for σ at df = 2 is ≈ **2.1×** the point estimate, i.e.
    ≈ 142 updates, which would imply N ≈ 16 for an MDE of 100. N = 10 is adequate only if the true
    σ_paired is ≤ 113, and a 3-seed pilot **cannot establish that**. This is a direct argument for
    N = 16 and is folded into U7.
23. The degree-preserving null preserves in/out degrees, signs, node identities and the weight
    multiset, but **not** component structure or per-neuron outgoing weight sums. C is therefore not
    a pure "wiring only" null: it differs from A in global fragmentation as well as local wiring. The
    §3.3.1 diagnostics detect the common failure modes of a rewire (insufficient movement, poor
    mixing, degree corruption) but are not a proof that the null is well mixed.
24. E-matched is not a matched control for plasticity: it has direct credit assignment to its own
    parameters. Comparisons involving E are explanatory.
25. F is expected to fail if the motor populations are silent. If F succeeds only through a constant
    action learned from its bias term, **Fβ is designed to detect exactly that**, and the result is
    reported as a constant policy, not as "the readout learned to play". While the motor populations
    are silent, **no neural-learning claim of any strength is permitted** (§3.6.4, E3).
26. Readout training is not synaptic plasticity and must never be summarised as such.
27. The floor predicted by Phase 7 means the confirmatory family may be **uninformative by
    construction**. That possibility is preregistered here, before the data.
28. Phase 6's confirmatory negative result stands unchanged; Phase 8 information measures are
    descriptive and cannot revise it.
29. **The attainable-p floor is a property of N = 10, not of the data.** No contrast can be reported
    below an adjusted p of 0.0078 (m = 4) or 0.0059 (m = 3), however large the true effect. A
    "significant" Phase 8 result will always carry that floor in its footnote.
30. A′, C′ and Fβ are **control arms, not conditions**: they produce no scientific claim of their
    own, and a failure in any of them consumes budget and ends in a methodological conclusion rather
    than a behavioural one. That expenditure is deliberate.
31. The motor-driven/bias-driven classification (§3.6.3) is a **counterfactual on a frozen model**.
    It establishes whether the recorded decision depended on motor features; it does not establish
    that the dependence is biologically meaningful, and it says nothing about causality in the fly.

---

## 12. Unresolved decisions requiring approval

Each item states the options and a recommendation. **None is applied.** Recommendations are
advisory; every alternative stays visible.

### U1 — action if the pilot confirms the floor

*Decision.* What to do when the pilot shows zero non-`NO_ACTION` executions across all pilot seeds
and episodes in A and F.
*Options.* (a) run the full campaign anyway and report a floor result; (b) stop, report the floor
plus a pathology decomposition (no motor spikes / no sustained activity / decoder gate never met),
and request a scope decision; (c) authorise a **separate, pre-registered** follow-up that changes
drive or decoder; (d) if A and F floor but E-matched does not, run only E and report the environment
as solvable-but-not-from-this-interface.
*Recommendation.* **(b)**, then decide with the user; (d) is a legitimate refinement of (b) once E
results exist. **Never (c) inside Phase 8** — (c) is Phase 9 and requires its own preregistration.

### U2 — eta for B and D

*Options.* (a) reuse Phase 5's declared `0.5`; (b) re-derive on the game; (c) add a second declared
eta as an exploratory arm.
*Recommendation.* **(a)**. It was declared before any run; tuning it on the game would be a confound.
If (c), declare the value **in advance** from `{0.1, 1.0}` and accept that it roughly doubles B/D
cost. Phase 5 found 0.1–2.0 indistinguishable, so an eta axis is unlikely to inform anything and is
mostly a cost.

### U3 — primary outcome

*Options.* (a) censored survival in updates; (b) total task reward; (c) survival with reward as
co-primary.
*Recommendation.* **(a)**. Reward is coin-dominated (coin +1, collision −1, survival +0.01/step) and
coins are entirely unmodelled in the sensory drive, so (b) would compare conditions on a signal no
neural condition can reach. (c) breaks the single-primary discipline and makes the family size
depend on an outcome choice; not recommended.

### U4 — random-null scope

*Options.* (a) degree-preserving signed rewire only; (b) also a **component-preserving** variant
(swaps restricted to within an original weak component); (c) also a **sign-randomized** variant
(node signs re-drawn at the observed verified fraction).
*Recommendation.* **(a)** confirmatory, **(b)** exploratory, **(c)** exploratory and clearly labelled
as answering a different question — *"does sign assignment matter?"*, not *"does wiring matter?"*.
Component structure is reported for every graph regardless (§3.3.1, R15).

### U5 — condition E implementation

*Options.* (a) direct REINFORCE against the existing 5-tuple API, no installs; (b) install Gymnasium
+ Stable-Baselines3 and wrap the game.
*Recommendation.* **(a)**. (b) adds two dependencies, a version-pinning obligation, a new
environment-contract surface, and a wrapper that must be re-validated against the same 5-tuple
semantics — for no scientific gain, since E only needs to be a competent reference learner on the
same observations.

### U6 — evaluation episode count K

*Options.* (a) K = 10; (b) K = 5; (c) K = 20.
*Recommendation.* **(a)**. The primary unit is the seed, so K affects only the precision of the
within-seed mean, not the degrees of freedom; at the measured 22 s per episode, K = 10 costs 3.7 min
per seed per condition and K = 20 doubles that. (b) is the fallback if U11 caps the budget.

### U7 — number of seeds N

*Options.* (a) N = 10; (b) N = 16; (c) N = 20.
*Recommendation.* **(b) as the default, (a) only if justified.** This is a **change from V1**. V1
recommended 10 with an escalation rule, but that rule applied to a 3-seed σ estimate with 2 degrees
of freedom; its 80% upper limit is ≈ 2.1× the point estimate (§11.22), which implies N ≈ 16 for an
MDE of 100. Applying V1's own escalation rule honestly therefore selects 16. Choose (a) only if the
pilot is enlarged to ≥ 5 seeds so that σ is estimated well enough to justify 10.

### U8 — E-full (14 features)

*Options.* (a) yes, exploratory; (b) no.
*Recommendation.* **(a)**. It costs minutes and quantifies what the 7 unmapped features would be
worth. It must use the same architecture and training budget as E-matched, or the comparison is
confounded by capacity.

### U9 — B/D plasticity during evaluation versus train-then-freeze

*Options.* (a) plasticity runs during evaluation, as in Phase 5; (b) train, freeze, then evaluate;
(c) both.
*Recommendation.* **(a)** for the primary — it measures the closed loop as specified. **(c)** if
budget allows, with (b) labelled exploratory; (b) alone would misrepresent an online mechanism as an
offline one. If (b) or (c), the frozen evaluation must use **held-out seeds** for both the training
and the freeze point, or the reported result is a training-set score.

### U10 — no-action baseline

*Options.* (a) derive the floor from the game configuration without replay; (b) add a seventh
condition that always emits `NO_ACTION`.
*Recommendation.* **(b), implemented as a control arm rather than a condition.** This is a
**correction from V1**, which called the floor "analytically known" and "computed at zero cost".
Collision timing depends on obstacle layout, so the floor **must be measured** by replaying the
paired environment seeds with a constant-`NO_ACTION` policy; it costs seconds and requires no neural
substrate. It is not a seventh condition because it makes no scientific claim.

### U11 — compute budget ceiling

*Options.* (a) accept the §9.2 estimate, now **≈ 19–78 h** single-process; (b) cap at ≈ 10 h by
dropping K to 5 and Fβ's training rollouts; (c) parallelise across CPUs with a determinism audit.
*Recommendation.* **(a)** as the planning figure. Consider (c) only after the pilot, and only with
per-process thread pinning and a byte-identical determinism check. (b) reduces cost but also reduces
the precision of every within-seed mean.

### U12 — whether Phase 8 may write a new `learning/` implementation

*Options.* (a) keep `learning/dopamine.py`, `learning/synaptic_plasticity.py` and
`learning/mutual_information.py` untouched; (b) fill them with Phase 8 code.
*Recommendation.* **(a)**. All three are one-line placeholders. Phase 8 code lives in
`experiments/phase_8/`, `readout/`, `experiments/phase_8_random/` and `evaluation/`. Filling
`learning/` would create a second plasticity implementation alongside Phase 5's, which the project
constraints forbid (no duplicate modules), and would imply the Phase 5 mechanism is being replaced.

### U13 — C′ mirror for condition D *(new in REV2)*

*Decision.* A′ protects B. D uses the **same** plastic stepper on a different graph, so an
implementation defect would corrupt D identically. Does D get its own `eta = 0` mirror?
*Options.* (a) require C′ on all N seeds × K episodes, exactly like A′; (b) require C′ on the pilot
seeds plus episode 1 of every campaign seed; (c) omit C′, rely on A′, and disclose that D shares the
stepper.
*Recommendation.* **(a)**. It is one extra condition's runtime (§9.2) and it converts "D shares
validated code" into "D shares code that was validated on its own graph". (b) is a defensible
compromise; (c) leaves the only remaining unvalidated path in the campaign.

### U14 — confirmatory family size *(new in REV2)*

*Decision.* Does C4 (`F − Fβ`) join the confirmatory family?
*Options.* (a) **m = 4** with C4; (b) **m = 3** without C4, C4 demoted to exploratory.
*Recommendation.* **(a)**. Without C4 the readout claim is not identifiable — a bias term alone can
produce `F − A > 0` with silent motor populations. Choosing (b) is coherent, but it means **no
decoding claim may be made at all**, because §3.6.4 requires a Holm-surviving test and an
exploratory contrast cannot supply one. Both variants' Holm numbers are tabulated in §7.5.

### U15 — confirmatory status of H3 *(new in REV2)*

*Decision.* V1 labelled H3 exploratory while placing `C1 = F − A` in the confirmatory family.
*Options.* (a) H3 confirmatory (consistent with C1); (b) H3 exploratory (then C1 must leave the
family, which changes m and therefore every Holm threshold).
*Recommendation.* **(a)**. The readout question is one of the three the phase exists to answer, and
(a) is the only labelling consistent with V1's own contrast table.

### U16 — scope of Fβ *(new in REV2)*

*Decision.* Fβ is a full rollout arm (its own training + evaluation on the neural substrate). How
much of it is mandatory?
*Options.* (a) all N seeds × K episodes, full training, exactly mirroring F; (b) pilot seeds only,
plus the ablation counterfactual (§3.6.3) on every F decision; (c) no Fβ rollouts at all — rely only
on the ablation counterfactual.
*Recommendation.* **(a)** if U14 selects m = 4, because C4 needs a paired per-seed difference and
that cannot come from a 3-seed pilot. (b) is acceptable only if C4 is dropped, and then no decoding
claim is possible. (c) answers the mechanism question but not the behavioural one.

### U17 — declared thresholds in the readout evidence bar *(new in REV2)*

*Decision.* E3 and E4 in §3.6.4 are conventions introduced by this revision: "≥ 1 motor spike on
≥ 1% of decisions, in ≥ half of seeds" and "≥ 10% of non-`NO_ACTION` decisions motor-driven".
*Options.* (a) accept both as stated; (b) tighten to 5% and 25%; (c) loosen to any single motor spike
and 1%.
*Recommendation.* **(a)**. They are deliberately low because the expected regime has zero motor
spikes; (c) would let one spike anywhere license a decoding claim, and (b) risks being unreachable
even if a real effect exists.

### U18 — swap parameterisation for the degree-preserving null *(new in REV2, found during the consistency pass)*

*Decision.* How the double-edge swap rewires an edge. This was implicit in V1, and it determines
which preservation gates are provable, so it must be declared before C is implemented.
*Options.* (a) **target exchange** — each edge keeps its source and its weight; a swap exchanges
the targets of two edges from distinct sources with distinct targets; (b) **endpoint re-pairing** —
both source and target are re-paired across the two edges, with the weight carried by the edge.
*Recommendation.* **(a)**. It preserves out-degree, in-degree, the weight multiset **and** each
source's outgoing weight profile, so R8's signed-synapse gate and R9b are exact by construction. (b)
is a valid null but does not preserve per-source weight sums: the signed-synapse total becomes a
reported quantity, not a gate, and R9b drops to descriptive. Either choice must be written into the
config and into every `randomization_quality` block.

### 12.1 Review findings for U1–U12

Ambiguities and inconsistencies found while reviewing V1, and how REV2 addressed them. **No item was
decided on the user's behalf**; each remains open above.

| ID | Finding in V1 | Addressed in REV2 by |
|---|---|---|
| U1 | Gate referenced only "A or F" while §0 predicted A,B,C,D,F also floor; §7.8 used a *different* floor definition ("≥ 4 of 6 conditions") for a different purpose | gate definition made precise (zero non-`NO_ACTION` in A and F at pilot time); the 4-of-6 rule is now explicitly a post-campaign **reporting** rule, not a stop rule; option (d) added |
| U2 | Option (c) named no eta value and did not mention that Phase 5 found 0.1–2.0 indistinguishable | value set declared in advance; Phase 5 saturation noted; cost stated |
| U3 | Option (c) "co-primary" silently violates the single-primary discipline and did not say how censoring would apply to reward | contradiction stated; censoring applies to survival only |
| U4 | "component-preserving" was undefined operationally; the sign-randomized variant was not distinguished from a wiring null | operational definition added for (b); (c) labelled as answering a sign question, not a wiring question |
| U5 | Option (b) did not state its cost | dependency, pinning and wrapper-validation costs listed |
| U6 | K's interaction with cost and with the seed-level df was unstated | clarified: K affects within-seed precision only |
| U7 | "Confirm only after the pilot measures σ_paired" implied a 3-seed estimate was sufficient to confirm; it has 2 df | UCB argument added; recommendation changed to N = 16 by default |
| U8 | No capacity-matching requirement for E-full | same architecture and training budget required |
| U9 | "(b) exploratory trained-then-frozen" did not say the frozen evaluation needs held-out seeds | added |
| U10 | **Error**: floor called "analytically known" and "computed at zero cost" — collision timing depends on layout | floor must be measured by replaying paired seeds; reclassified as a control arm, not a condition |
| U11 | Budget figure stale once control arms were added | updated to ≈ 19–78 h (§9.2) |
| U12 | Did not state that filling `learning/` would duplicate the Phase 5 mechanism | duplicate-module constraint cited |

Two further inconsistencies were found **outside** U1–U12 and are corrected in place, with the choice
still open: the H3 confirmatory/exploratory contradiction (§4, now U15) and the claim
"No evaluation episode may update anything", which is false for B and D (§6.7).

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
| N (seeds) | 10 in V1; **16 recommended default** | §7.4, U7 — 10 is the declared floor, 16 the recommendation after the `df = 2` uncertainty check |
| K (evaluation episodes/seed) | 10 | U6 |
| training episodes/seed (F, Fβ) | 20 | declared |
| training episodes (E) | 2,000 gradient updates | declared |
| truncation cap | 900 updates | game config, unchanged |
| SEI | 100 updates | declared convention |
| α | 0.05, two-sided, Holm over **m = 4** (C1–C4) pending U14; m = 3 if U14 selects it | §5.3, §7.5 |
| exact sign-flip assignments (N = 10) | 1,024 | 2^N |
| minimum attainable one-sided p (N = 10) | 1/1,024 = 0.0009765625 | **not** the two-sided value (V1 error) |
| minimum attainable two-sided p (N = 10) | 2/1,024 = 0.001953125 | attained by all-plus and all-minus |
| count threshold, two-sided raw p ≤ 0.05 (N = 10) | ≤ 51 of 1,024 extreme statistics | 51/1,024 = 0.049805; 52/1,024 = 0.050781 |
| Holm-adjusted minimum, m = 4 | 4 × 0.001953125 = 0.0078125 | §7.5 |
| Holm-adjusted minimum, m = 3 | 3 × 0.001953125 = 0.005859375 | §7.5 |
| MDE at N = 10, σ = 60 | 53.155 | §7.4, 2.801585·σ/√N |
| bootstrap resamples | 10,000 | §7.7 |
| eta (B, D) | 0.5 | Phase 5 declaration, no retuning |
| eta (A′) | exactly 0.0 | §3.8 — must reproduce A bit-for-bit |
| Fβ readout | bias-only: motor-feature path fixed at 0.0, bias trainable | §3.6.2 |
| graph randomisation seed stream | `SeedSequence([MASTER_SEED, seed, "structure"])` | §3.3.1 R18 |
| weight bounds | 0.5–2.0× initial, 5 pA/update | `configs/plasticity_banc.yaml` |
| τe | 20 ms | `configs/plasticity_banc.yaml` |
| modulation | gain 1.0, τ 50 ms, clip ±5 | `configs/plasticity_banc.yaml` |
| sensory current | 200 pA per active feature | `configs/banc_sensory_mapping.yaml` |
| decoder window | 50 ms, ≥3 active, ≥5 spikes, activation 0.20, release 0.10 | `configs/motor_decoder.yaml` |

---

*End of draft. No experiment has been implemented or run. No file outside this document has been
created or modified. Awaiting approval of §12.*
