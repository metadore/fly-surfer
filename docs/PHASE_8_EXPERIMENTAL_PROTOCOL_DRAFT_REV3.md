# Phase 8 — Training and Comparison: Experimental Protocol (DRAFT)

| field | value |
|---|---|
| status | **DESIGN / PREREGISTRATION DRAFT, REVISION 3 — NOT APPROVED, NOT EXECUTABLE** |
| date | 2026-11-17 |
| scope | design and preregistration only |
| executes anything | no — no training, no episodes, no weight change, no plasticity, no installs |
| revision | **REV3**: complete protocol resolving every finding of the independent REV2 audit (C1, M1–M9, m1–m11). Pilot split into 10.3 (A viability) and 10.8 (paired variability/control pilot); extremal sign vectors, validity assumptions, capped-score terminology, F/Fβ state-independence, C′ coverage, budget arithmetic, H3 status and N = 16 consistency corrected throughout |
| supersedes | REV2 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md` (SHA-256 `d6a8964c…ab7c0`, 1,465 lines), preserved byte-identical; V1 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` (`d9d13a6c…fc505`), preserved byte-identical |
| audit basis | `reports/PHASE_8_REV2_INDEPENDENT_AUDIT.md` (SHA-256 `dee563ef…77a12`, 866 lines), verdict **CONDITIONALLY READY — CORRECTIONS REQUIRED** |
| blocking gate | human approval of §12 before any confirmatory pilot, campaign or training is executed. Additive implementation scaffolding is authorised by the 2026-11-16 correction brief and is tracked separately in `reports/PHASE_8_IMPLEMENTATION_STATUS.md`; scaffolding is not evidence that a condition has been run |

### Revision 3 correction notice

REV3 is a **complete protocol**, not a change log. It replaces REV2 as the working specification and
addresses every finding in the independent audit. The original roadmap, the six conditions, the
Phase 6 negative result, the Phase 7 baseline and all documented limitations are preserved.

| Audit finding | Resolution in REV3 |
|---|---|
| **C1** pilot not executable in the stated order | §10 now has **10.3** (A viability, immediately after the A baseline) and **10.8** (paired pilot, after C, F/Fβ, A′/C′ and B/D exist). Every step has inputs, deliverables, acceptance criteria and dependencies |
| **M1** extremal sign vectors misdescribed | §7.3 and Appendix C state that the extremal statistic is attained by `sᵢ = sign(dᵢ)` and its negation, which are all-plus/all-minus only when every difference shares one sign |
| **M2** sign-flip validity assumption unstated | §7.3 adds the symmetry/exchangeability null, seed independence and the exact sign test as a robustness check |
| **M3** §11.23 contradicts R9b | §11.23 now matches the target-exchange parameterisation and scopes the V1 wording to endpoint re-pairing |
| **M4** missing pairs keep N and thresholds | §7.3/§7.6 recompute the enumeration and every threshold at the reduced N; no pair is dropped silently |
| **M5** "right-censored" label vs capped analysis | §5.1/§7.6 rename the primary outcome as a **capped score**, separate observed termination, cap-reaching episodes and the capped comparison, and pre-specify a censoring-aware sensitivity analysis |
| **M6** pilot cannot estimate the binding σ | §7.4 names the σ that governs N, requires B in the paired pilot, and uses the worst-case contrast; §10.8 states exactly which contrasts it estimates |
| **M7** 5× training-budget error | §9.2 recomputes every line from stated assumptions; F/Fβ training is 1.24–5.24 h at N = 10, not 6.2–26.2 h |
| **M8** floor described as two incompatible arms | §3.6.2/U10 define one substrate-free, game-side measure; it is never a neural arm, and it costs seconds |
| **M9** H3 status simultaneously resolved and open | H3 has exactly one status — **confirmatory** — in §4, §5.3, §7, §10 and Appendix C; the underlying U15 decision is marked proposed, not approved, and its contingency is recorded once in H3's entry |
| **m1–m11** | corrected in place at the cited sections; see `reports/PHASE_8_REV3_CORRECTION_REPORT.md` for the item-by-item map |

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

G1–G7 are unchanged from V1 and are the implementation gates, not design gates. Their current
implementation status is tracked separately in `reports/PHASE_8_IMPLEMENTATION_STATUS.md`; a design
section in this document is not evidence that a gate is closed.

REV3 requires four **control arms** for interpretation: **A′** (biological graph, `eta = 0` through
the live plastic path, must equal A exactly), **C′** (random graph `G_s`, `eta = 0` through the same
path, must equal C exactly on all N × K runs), **Fβ** (a genuinely state-independent readout, the
constant-policy control for F) and the **floor** (a substrate-free constant-`NO_ACTION` policy on the
paired environment seeds). A′ and Fβ are required; C′ is required for D's interpretation under the
working specification U13(a) and remains a proposed decision for human approval. The arms reuse the
B, D and F code paths, so they add runtime rather than new mechanisms. §9.2 accounts for the cost.

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
- The resource preflight immediately before REV3 recorded **≈ 1.1 GB free physical memory**
  (1,152,972 KB of 16,087,140 KB), below the 4 GB gate of §9.3. No BANC-scale randomisation,
  campaign, training or memory-intensive test suite may start while that remains true.
  Implementation may proceed only on lightweight, synthetic fixtures and must record blocked
  execution as pending, not completed.

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
**Terminology used throughout:** a *verified sign* is a **non-null predicted-transmitter
annotation in the BANC export**. It is a model input derived from a prediction, not a physiological
measurement, and the word "verified" is used only because that is the annotation column's name.

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
| R14 | Rewiring-distance plateau | recompute R5 every 10⁵ accepted swaps; require the last 20% of accepted swaps to change Jaccard by **< 1e-4 absolute** | **must plateau**; this is a *plateau diagnostic on the rewiring distance*, not a proof of Markov-chain mixing. A still-trending chain is not reported as randomized |
| R15 | Component structure | weak-component count and size distribution, before vs after | **reported, not gated** — the change is the intended effect of randomization and must be visible in the results |
| R16 | Reciprocity and degree assortativity | directed reciprocity and (optional) degree assortativity, before vs after | reported, descriptive |
| R17 | Reproducibility | two independent constructions from the same seed | `edge_src`, `edge_dst`, `edge_weight` **byte-identical**; graph digest identical |
| R18 | Graph seed derivation | `SeedSequence([MASTER_SEED, seed, "structure"])` | recorded per graph; disjoint from the environment, network and learning streams |

**Rejection protocol.** If any of R4–R14 (including R9b) or R17 fails, the graph is **rejected and not used**. The
condition does not silently fall back to a less-random graph. The campaign halts for that seed,
records which gate failed and the full report, and reports the halt. Rerunning with a different seed
is allowed; rerunning with a relaxed gate is not.

**Why R13 and R14 exist.** R4/R5 alone can be satisfied by a chain that has swapped edges only among
a small subset of nodes. R13 detects that local neighbourhoods are still almost identical; R14
detects that the scalar rewiring distance has stopped moving. Neither is a proof that the chain has
converged to its stationary distribution, and the report must not describe a Jaccard plateau as
Markov-chain mixing. Both are cheap and both must pass before the graph is called a null.

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
| 5 | Learning algorithm | REINFORCE over the readout only. Features = per-decision motor-population activity (§3.6.1). The **primary F is linear**, so that `F` and `Fβ` differ only in whether the feature pathway is trained; a one-hidden-layer readout is a declared exploratory arm, never the basis of C4 |
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

**Definition.** Fβ is condition F with **every state-dependent pathway removed**. Operationally it
is a **linear** readout over the four actions whose feature weights are fixed at exactly `0.0` and
excluded from the optimizer; only the four output biases are trainable. There is no hidden layer and
no feature weight in the trainable parameter set. The policy is therefore provably state-independent:
the same action distribution is emitted for every motor-activity vector, including the zero vector.
Same seeds, same environment, same frozen connectome, same training-episode budget and same optimizer
as F. The only difference from F is that motor activity cannot influence the decision.

**Naming rule.** The phrase "bias-only" may be used **only** for an arm with exactly this parameter
set. If any hidden-layer weight, feature weight or other state-dependent pathway is trainable, the
arm is not Fβ and the claim "constant policy" is forbidden; it must be renamed and reported as a
different control.

**The four readout claims are separate.** No one contrast supports more than its own claim.

| # | Claim | Contrast or diagnostic | What it does **not** establish |
|---|---|---|---|
| 1 | a better constant action is available than `NO_ACTION` | `Fβ − floor > 0` | says nothing about state-dependence or decoding |
| 2 | state-dependence adds value over the best constant policy | `F − Fβ > 0` (C4) | does not by itself show that the dependence is on **motor** activity rather than on any other state variable |
| 3 | the decision depends causally **in the frozen model** on motor features | frozen-parameter ablation changes the argmax (§3.6.3) **and** E4 threshold (§3.6.4) | not biological causality and not that the dependence is useful |
| 4 | F **learned** rather than merely being a non-constant policy | F beats `F-init` (same architecture, same seeded initial parameters, no training) on the paired evaluation seeds | does not show that what was learned is motor decoding |

`F-init` is evaluated on all N × K evaluation episodes with the same protocol as F and requires no
training; it is a required diagnostic for claim 4. If F does not beat `F-init`, the report may
describe F as a non-constant policy but not as a learned one. `F-shuffled` (motor features replaced
by a time-shuffled copy of the same episode, preserving marginal statistics) is an **exploratory**
diagnostic, declared in advance and never promoted after seeing results.

**The `NO_ACTION` floor is substrate-free and must be measured, not assumed.** It is obtained by
replaying the **paired environment seeds** with a deterministic constant-`NO_ACTION` policy. The game
advances on its own fixed timestep; the policy reads no spikes, so the measure is identical whether
or not a neural substrate is present. It therefore costs seconds and is **never** budgeted or
described as a neural-substrate arm. Collision timing depends on layout, so the floor cannot be
derived analytically. It is the same quantity to which Fβ converges when `NO_ACTION` is the best
constant action.

#### 3.6.3 Motor-driven versus bias-driven decisions

For every decision in F and Fβ evaluation episodes, a **frozen-parameter ablation** is recorded.
Ablation rule, fixed in advance: set the readout's motor-feature input vector to exactly `0.0` and
recompute the logits from the **same frozen parameters**. No retraining, no gradient, no environment
step, no extra rollout. The ablation is a counterfactual on a frozen model, not a causal experiment
on the fly.

| label | operational definition |
|---|---|
| **motor-driven** | ablation **changes** the argmax action, and ≥ 1 spike occurred in the population of the chosen action within the window |
| **bias-driven** | ablation leaves the argmax action unchanged and that action is not `NO_ACTION` |
| **bias-driven (incidental)** | chosen action is `NO_ACTION` but ≥ 1 motor population spiked in the window — activity was present, but no action was chosen from any population |
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

**E4 denominator.** If there are no non-`NO_ACTION` decisions at all, E4 is **undefined**; the
decoding claim is not permitted, and the checklist records `E4: undefined (0/0)`, not a pass. E3
already fails in that case, so the two guards agree.

**If E3 fails, no claim of neural learning is permitted at all** — not "weak evidence", not "a
trend". The permitted statement is exactly: "the motor populations were silent; the readout could at
most learn a constant policy." If E1 or E2 fails, the conclusion is "no evidence that the readout
used motor information", regardless of how well F scores. Passing E1–E5 supports claim 3 of §3.6.2
(frozen-model dependence on motor activity) and, with F > `F-init`, claim 4 (learning); it never
supports a biological-causality claim.

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
| **C′** (U13(a), proposed) | randomized `G_s` | fixed, through the plastic code path at `eta = 0` | fixed threshold | nothing | exactly equals C on every campaign seed and episode, all 19 fields of §3.8.3 |
| **Fβ** | biological | fixed | state-independent readout: output biases only, feature weights fixed at 0 | output biases only | the constant-policy control for F; no hidden or feature pathway is trainable (§3.6.2) |
| **F-init** | biological | fixed | F architecture at its seeded initial parameters, no training | nothing | the "non-constant but unlearned" diagnostic for claim 4 (§3.6.2) |
| **floor** | **none** | none | constant `NO_ACTION` | nothing | substrate-free, game-side, paired-seed no-action survival; never a neural arm |

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
- C′ on **all N campaign seeds × all K evaluation episodes** — a full mirror of C, not a sample,
  not a reduced design. A trimmed C′ (for example only the seeds that reached B) would make the
  `D − C` contrast pair a full campaign against a partial one; the two arms must cover the same
  `(seed, episode)` grid.
- One **fresh-process** replay of A′ and of C′ episode 1 per seed, to confirm cross-process
  determinism.
- `eta` is exactly `0.0` — not `1e-12`, not a "learning disabled" flag that skips the rule
  entirely. The rule must execute and return an exactly zero delta, unless §3.8.4's documented
  short-circuit applies.

The paired pilot described in §10.8 must exercise A′, C′ and Fβ, not only A and F. A pilot that omits
C′ cannot certify the D path, and a pilot that omits Fβ cannot certify that the readout control is
functioning.

#### 3.8.2a Arithmetic parity of the live plastic stepper

The A′/C′ identity is only meaningful if the plastic stepper reproduces the fixed-weight stepper's
numeration exactly. The implementation requirement is therefore:

- the plastic stepper is an **additive subclass** of the fixed-weight `LiveBancStepper`;
- it replaces the synapse container with one that applies weight deltas, and installs the learning
  engine's delay line;
- it must not change the parent's current-accumulation order, accumulation dtype, threshold test,
  refractory handling or spike ordering;
- with `eta = 0` the delivered current array must be **bit-identical** to the parent's, not merely
  close.

Any implementation that reorders accumulation, accumulates in a different precision, or applies
deltas before propagation fails P1–P19 in principle and must be corrected rather than tolerated.

#### 3.8.3 Comparison fields — all must be equal to the fixed-weight arm

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
5. D shares the same plastic stepper, so an A′ mismatch is flagged against D as well. C′ is the
   corresponding control for D on the random graph and is **required** under the working
   interpretation of U13; a C′ mismatch marks **D** invalid exactly as an A′ mismatch marks B.
6. A′ and C′ are subject to the **same** strict equality: the same P1–P19 fields, the same
   zero-tolerance rule (§3.8.4) and the same hard stop (this section). There is no reduced
   comparison for C′, and no relaxed field list for the random graph.
7. There are no silent retries. If a mismatch is traced to a stale artifact, a partial write or a
   configuration drift, that is an operational fault, not a scientific retry: it is recorded in
   the run log, the affected runs are regenerated from a clean process, and the regeneration is
   disclosed. Changing a tolerance, dropping a field, or choosing a new seed to obtain a match is
   forbidden. An unresolved mismatch is a hard stop and blocks the affected arm; it is never
   resolved by weakening the comparison.

#### 3.8.6 Where the check is applied

- in the **pilot**, on all 3 pilot seeds, for A′ and C′, before the campaign is authorised;
- on **every campaign seed**, for every evaluation episode, for both A′ and C′;
- in a **final validation pass** that recomputes every comparison from the stored JSONL rather than
  from in-memory state.

---

## 4. Scientific hypotheses

Falsifiable, with the direction of the predicted effect and the observation that would refute it.
The labels are binding and match §5.3, §7 and §10: **H1, H2 and H3 are confirmatory** (they map onto
C2, C3 and C1); **H4 is an explanatory reference**; **H5 and H6 are exploratory/descriptive and
cannot be promoted after seeing data.** Each hypothesis carries exactly one status in every
register. H3's confirmatory status is contingent on U14/U15 (§7.1, §12) being resolved before any
data are generated, and the contingency is recorded once, in H3's own entry, rather than as a second
status.

> **Note (superseded contradiction, resolved in REV3).** V1 labelled H3 exploratory while `C1 =
> F − A` sat in the confirmatory family; REV2 made H3 confirmatory but did not propagate the label
> to every register. REV3 fixes the *status* as confirmatory and makes the propagation requirement
> explicit in H3's entry: if the user prefers the V1 labelling, then C1 must move out of the
> confirmatory family and H3 must be demoted in the hypothesis register, §5.3, §7 and §10 together.
> Recorded as U15. The two cannot differ.

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

*Single status.* H3 is **confirmatory**, and this is its only status in this protocol. It is
confirmatory through C1 in the m = 4 family; it is not also labelled exploratory, secondary or
"provisional" anywhere. The status is **contingent on U14 and U15 being resolved before any data are
seen**: if U14 selects m = 3 and removes C4, C1 remains confirmatory and H3 remains confirmatory but
the decoding claim is unavailable; if the user instead prefers the V1 labelling, then C1 must leave
the confirmatory family and H3 must be demoted in *every* register — the hypothesis register, the
U-item register (§12), §5.3, the analysis plan (§7) and the acceptance criteria (§10) must then be
edited together. A contradiction between those registers (H3 confirmatory in one and exploratory in
another) is a document defect and blocks authorisation. There is no reading under which H3 has two
statuses at once.

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

**Mean capped survival score per evaluation episode**, in game updates, averaged over K evaluation
episodes within a seed. The capped score is defined as

```
capped_score = min(observed_updates, 900)
```

where `observed_updates` is the number of game updates completed before the episode ended.

Three quantities must be kept distinct everywhere in the document, the analysis and the report:

| Quantity | Definition | Used for |
|---|---|---|
| **observed termination time** | updates completed before a collision; undefined for cap-reaching episodes | descriptive only |
| **cap-reaching fraction** | fraction of evaluation episodes that reached 900 updates without terminating | reported per condition; part of the floor diagnosis |
| **capped survival score** | `min(observed_updates, 900)`; a capped, bounded outcome defined for every episode | the primary comparison |

A cap-reaching episode is **not** an ordinary right-censored observation. Right-censoring assumes
that the event time exists and would eventually be observed after the censoring horizon; here the
horizon is an administrative episode cap and the outcome is deliberately defined as bounded, so
the quantity being compared is the cap-restricted score itself. Calling it "right-censored survival"
would import a model the design does not assume, and would license methods (Kaplan–Meier curves,
log-rank tests) whose target is a different estimand.

If a time-to-event analysis is retained at all, it must be **declared separately** as a sensitivity
analysis, with an explicit censoring-aware method (for example a Cox model or a Kaplan–Meier
summary that treats cap-reaching episodes as censored at 900), and it can never replace or
contradict the capped-score primary. Ties at the cap are expected and are handled by the capped
estimand itself, not by a tie correction in a test built for uncensored data.

Definitions fixed before the run:

- *survival* = number of game updates completed before `terminated` (collision);
- an episode that reaches 900 updates enters the primary as **900** and is flagged `truncated`
  (its `observed_termination` field is null);
- an episode that raises an exception is recorded with `status: "error"` and a reason, **retained**,
  and excluded from the complete-case primary with a pre-specified sensitivity analysis (§7.6);
- an all-`NO_ACTION` episode is a **valid observation**, not a failed run. It is scored normally.

Rationale: the capped survival score is the only outcome that is (a) defined identically for all six
conditions, (b) produced by the environment rather than by a model of the environment, (c) unaffected
by the neural/ANN interface asymmetry, and (d) already measured for the Phase 7 baseline and for the
two non-neural pilot agents. It is a bounded game score, and the document does not describe it as a
duration measured without restriction.

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
| C′ vs C | **integrity check** | must be exactly equal on every seed and episode; a mismatch invalidates D. Required under the working interpretation of U13; if U13 is decided against C′, the D arm is reported without the identity certificate and no causal attribution for D is permitted |
| Fβ (state-independent readout control) | secondary + interpretation gate | the best policy whose action depends only on a fixed bias; F is never interpreted without it (§3.6.2) |
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
declared secondary (§7.7).

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

Paired, within-seed comparison. **N = 16 seeds is the primary design** (U7), K = 10 evaluation
episodes per seed per condition, six conditions plus the required control arms A′ and C′, and Fβ
(all N seeds × K episodes, §3.8.2, §3.6.2). The control arms enter no confirmatory contrast between
themselves; they gate interpretation of B, D and F.

N = 10 is available **only** as a predeclared fallback, and only if the pilot's variability estimate
supports it. The governing statistic is the **largest paired standard deviation among C1–C4**, not
the sd of whichever contrast happens to look smallest and not the sd of a single arm. With
`σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4)`, the fallback is permitted only if

```
2.8016 · σ_max / √10 ≤ SEI = 100   ⇔   σ_max ≤ 113.05
```

and the pilot must be able to establish that bound. A 3-seed pilot cannot: a 3-seed sd has `df = 2`
and its 80% upper confidence limit is ≈ 2.1× the point estimate. Consequently **N = 16 is the
default and the pilot must include B** (C2), not only A and F, because C2 is a candidate for the
largest σ. The choice between N = 16 and N = 10 is made **before the campaign**, from the pilot's
σ_max with its uncertainty reported, and is never revisited after any campaign outcome is seen.
Selecting N after observing effects is selecting on the result and is forbidden. If the pilot cannot
support N = 10 and the budget does not permit N = 16, the campaign does not start; it is not run at
N = 10 with a weakened claim.

### 7.2 Unit of analysis

The **seed**. Per seed and condition, the outcome is the mean over K episodes of the **capped
survival score** of §5.1. Episode-level values are also retained for the secondary analysis. The
episode is not the unit of the primary test: episodes within a seed share a network draw and a
training trajectory, so treating them as independent would overstate the evidence.

### 7.3 Primary test

Two-sided **exact sign-flip permutation test** on the N paired per-seed differences.
Statistic: the mean paired difference `T(s) = (1/N) Σ sᵢ dᵢ`, where `dᵢ` is the paired difference
for seed *i* and `sᵢ ∈ {−1, +1}`. Enumeration is exhaustive over all `2^N` sign vectors; the p-value
is `#{s : |T(s)| ≥ |T_obs|} / 2^N`. No normal approximation, no Monte Carlo, no asymptotics. Applied
to C1, C2, C3 and C4 (or C1–C3 if U14 selects m = 3).

**Extremal sign vectors.** The statistic `|T(s)|` is maximised when every term `sᵢ dᵢ` has the same
sign as `dᵢ`, i.e. at `sᵢ = sign(dᵢ)`, and at its negation `sᵢ = −sign(dᵢ)`. These are the two
extreme assignments, and they are **not** in general "all-plus and all-minus": those coincide with
the extremes only when all `dᵢ` share a sign. The minimum attainable two-sided p is therefore
`2/2^N` for every N, because the observed statistic itself is attained by exactly the two vectors
`sign(d)` and `−sign(d)` (with `sign(0)` resolved by the zero-difference policy below), and by no
other vector when the magnitudes are distinct. The quantity `2/2^N` is a property of the permutation
group, not of the observed data.

**Validity assumption (stated, not assumed silently).** The test's exactness rests on the paired
differences being **exchangeable under sign reversal** — i.e. under the null each `dᵢ` is symmetric
about zero, independently across seeds. This is the standard paired-permutation assumption. It is
weaker than normality but not free: it fails if the two arms differ in dispersion as well as
location, or if a seed's two arms are coupled through a shared random draw that is not paired out.
The design controls the second by pairing environment seeds (§6.2) and by using one network draw per
seed shared across conditions (§6.3); the first is a limitation of the test and is stated in §11.
Episodes are averaged within a seed before the test, so episode-level dependence does not enter the
permutation.

**Attainable p-values — primary N = 16**

| bound | value | note |
|---|---|---|
| sign vectors | 65,536 | `2^16` |
| minimum one-sided p | 1/65,536 = 0.0000152588 | not used |
| **minimum two-sided p** | **2/65,536 = 0.0000305176** | attained by `sign(d)` and its negation |
| count threshold for two-sided p ≤ 0.05 | ≤ 3,276 of 65,536 | 3,276/65,536 = 0.0499878; 3,277/65,536 = 0.0500031 > 0.05 |

**Attainable p-values — fallback N = 10 (only if §7.1's predeclared condition is met)**

| bound | value | note |
|---|---|---|
| sign vectors | 1,024 | `2^10` |
| minimum one-sided p | 1/1,024 = 0.0009765625 | V1 quoted this and mislabelled it two-sided |
| **minimum two-sided p** | **2/1,024 = 0.001953125** | attained by `sign(d)` and its negation |
| count threshold for two-sided p ≤ 0.05 | ≤ 51 of 1,024 | 51/1,024 = 0.049805; 52/1,024 = 0.050781 > 0.05 |

**Zero-difference policy (declared).** A paired difference of exactly `0.0` is a legitimate
observation and is **not** dropped: it is kept as `dᵢ = 0`, it contributes `0` to every `T(s)`, and
it cannot distinguish the arms. If every `dᵢ` is exactly zero — the expected case when both
conditions floor — then `T(s) = 0` for all `2^N` sign vectors, `|T(s)| ≥ |T_obs|` holds everywhere
and **p = 1.0 by definition**. The test is then uninformative by construction; this is reported as
"no difference detectable; the design has no power against a difference between two floored
conditions", never as evidence that the conditions are equivalent. `sign(0)` in the extremal
construction is therefore only a bookkeeping device for the two vectors that attain `|T_obs| = 0`;
it creates no additional attainable p-value below 1.0.

**Missing and invalid pairs (declared).** A pair is **missing** when one or both arms have no valid
value for that seed×episode cell (an `error` row, a truncated write, a failed integrity check). The
rules are:

1. Missingness is **reported**, per arm and per condition, in the analysis output — counts and
   reasons, never silently skipped.
2. A pair is dropped from the primary **only** when it is structurally undefined or invalid, and
   the drop is disclosed with the reason. It is never dropped because it is inconvenient, extreme,
   or because dropping it changes a result.
3. **N is recomputed at the actual number of complete pairs** and every threshold is recalculated
   at that N. The attainability tables and Holm thresholds are never quoted for a nominal N that
   differs from the number of analysed pairs.
4. If the actual N is below the predeclared minimum, the primary is **not** computed; the campaign
   reports the design failure and stops. Lowering the N floor to salvage a result is forbidden.
5. If missingness is **asymmetric between the two arms** of a contrast (for example B errors more
   often than A), the complete-case primary is labelled potentially biased, and the
   pre-specified sensitivity analysis of §7.6 (errors scored at their last completed update) is
   reported alongside it. Asymmetric missingness is never hidden behind a complete-case result.

**Robustness check.** A two-sided exact sign test (binomial on the count of positive differences,
zero differences dropped for this check only) is reported alongside every sign-flip p. The two agree
in ranking, but the sign-flip test is **not** uniformly more powerful. With equal magnitudes, the
sign-flip p is determined by the split count alone; the sign test is the same count with a different
denominator. Equal magnitudes are the **least** permissive configuration, not the most permissive:
for example eight differences of `+10` and two of `−0.1` give `|T_obs| = 79.8`, and only 8 of the
1,024 sign vectors are at least as extreme, i.e. `p = 0.0078125`, which passes Holm step 1 at m = 4
(`0.0125`) — whereas the same 8-versus-2 split with equal magnitudes gives `p = 112/1024 = 0.109`
and fails outright. Any statement that the test is "most permissive" when magnitudes are equal is
withdrawn.

### 7.4 Sample size and power

| Quantity | Value |
|---|---|
| primary design | **N = 16** paired seeds (U7), K = 10 episodes per seed per condition |
| predeclared fallback | N = 10 only if the pilot shows `σ_max ≤ 113.05` with enough precision to defend it (§7.1); otherwise N = 16 or no campaign |
| σ that governs N | `σ_max = max(σ_paired,C1, σ_paired,C2, σ_paired,C3, σ_paired,C4)` — the **largest** of the four confirmatory paired sds, not an average and not the smallest |
| pilot requirement for σ | the pilot must include **B** (to estimate `σ_C2`), **C** (for `σ_C3`) and **F/Fβ** (for `σ_C1`, `σ_C4`), not only A and F |
| α (two-sided, per contrast) | 0.05 |
| nominal power | 0.80 |
| normal-theory MDE formula | `MDE = (z₀.₉₇₅ + z₀.₈) · σ_max / √N = 2.8016 · σ_max / √N` |
| declared SEI | 100 updates |
| assumed `σ_max` | 60 updates |
| MDE at N = 16, σ = 60 | **≈ 42.0 updates** |
| σ supported at N = 16 for MDE = 100 | **≈ 142.8 updates** |
| MDE at N = 10, σ = 60 (fallback) | ≈ 53.2 updates |
| σ supported at N = 10 for MDE = 100 | ≈ 113.1 updates |
| **Holm step-1 normal-theory MDE** (α/m = 0.0125, m = 4) | `(2.4977 + 0.8416) · σ / √N = 3.3393 · σ / √N`; ≈ **50.1 updates at N = 16, σ = 60**, ≈ 63.4 at N = 10 |

**The MDE table is a normal-theory approximation, not exact power.** The actual test is an exact
sign-flip permutation with a discrete (attainable-p) distribution, followed by Holm. A normal-theory
`z`-based MDE does not describe the power of that combination exactly, and it does not describe the
Holm step-1 threshold either. The unadjusted MDE (2.8016·σ/√N) is therefore a **lower bound on the
effort required** relative to the Holm-controlled family; the step-1 MDE above is the more honest
number for a contrast that must survive the first Holm comparison. Both are reported, both are
labelled approximations, and neither is used to claim a guaranteed detectable effect.

**Where σ = 60 comes from.** It is an **assumption**, not a measurement. The only available
dispersion evidence is the 3-seed Phase 7 pilot: random agent sd 67.3, rule-based agent sd 57.2
across seeds. These are between-seed sds of a *single* episode, not the sd of a *paired difference*.
A paired difference removes the shared environment layout, so the true `σ_paired` is expected to be
**smaller**; 60 is deliberately the conservative end for the *point* value. It is not a defensible
upper bound: at `df = 2` the 80% upper confidence limit is ≈ 2.1× the point estimate.
**That is why N = 16 is primary**: it keeps the MDE near the SEI even if the true `σ_max` is close to
the upper confidence limit of a 3-seed estimate. The paired pilot (§10.8) measures the real value and its
uncertainty, `σ_max` is taken across C1–C4, and the escalation rule is applied **once, before the
campaign**: if the pilot's 80% upper limit for `σ_max` exceeds 142.8, N must be raised above 16; if
it exceeds 113.1, N = 10 is not permissible. No decision about N is made after campaign outcomes
are seen.

### 7.5 Multiplicity

Holm–Bonferroni, α = 0.05 family-wise, contrasts ordered by raw p. Thresholds are stated at the
**primary N = 16**, with the N = 10 fallback below. Minimum two-sided raw p at N = 16 is
`2/65,536 = 0.0000305176`; at N = 10 it is `2/1,024 = 0.001953125` (V1's `3 × 0.000977 = 0.00293`
used the one-sided minimum and is withdrawn).

**Primary variant — m = 4 (C1, C2, C3, C4), N = 16, pending U14**

| Holm step | threshold | admissible count of the 65,536 sign vectors | minimum adjusted p |
|---|---|---|---|
| 1 | α/4 = 0.0125 | ≤ 819 (819/65,536 = 0.0124969) | 4 × 2/65,536 = **0.0001220703** |
| 2 | α/3 = 0.016667 | ≤ 1,092 (1,092/65,536 = 0.0166626) | — |
| 3 | α/2 = 0.025 | ≤ 1,638 (1,638/65,536 = 0.0249939) | — |
| 4 | α = 0.05 | ≤ 3,276 (3,276/65,536 = 0.0499878) | — |

**Alternative variant — m = 3 (C1, C2, C3), N = 16, if U14 selects it**

| Holm step | threshold | admissible count | minimum adjusted p |
|---|---|---|---|
| 1 | α/3 = 0.016667 | ≤ 1,092 | 3 × 2/65,536 = **0.0000915527** |
| 2 | α/2 = 0.025 | ≤ 1,638 | — |
| 3 | α = 0.05 | ≤ 3,276 | — |

**Fallback variant — N = 10 if §7.1 permits it**

| Holm step | m = 4 threshold (count of 1,024) | m = 3 threshold (count of 1,024) | minimum adjusted p (m = 4) |
|---|---|---|---|
| 1 | α/4 = 0.0125, ≤ 12 (0.011719) | α/3 = 0.016667, ≤ 17 (0.016602) | 4 × 2/1,024 = **0.0078125** |
| 2 | α/3 = 0.016667, ≤ 17 | α/2 = 0.025, ≤ 25 | — |
| 3 | α/2 = 0.025, ≤ 25 | α = 0.05, ≤ 51 | — |
| 4 | α = 0.05, ≤ 51 | — | — |

Holm is feasible in every variant: the minimum attainable adjusted p is below 0.05. It is also
**demanding**. With equal-magnitude differences at N = 16, a 13-versus-3 split gives raw
`p = 2 × 697 / 65,536 = 0.02127`, which fails step 1 at m = 4 (`0.0125`); a 14-versus-2 split gives
`p = 2 × 137 / 65,536 = 0.004181`, which passes step 1. So under equal magnitudes at least 14 of 16
seeds must favour the same direction to survive the first Holm comparison. This is stated so the
design is not later described as more powerful than it is. Real differences rarely have equal
magnitudes, so the binding constraint is the count table above, not the unanimity rule. Under the
N = 10 fallback only a unanimous 10-of-10 separation survives equal-magnitude step 1.

Exploratory outcomes receive no correction and are labelled exploratory in every table, caption and
sentence.

### 7.6 Missing, failed and capped runs

| Situation | Handling |
|---|---|
| episode raises an exception | record `status: "error"`, keep the partial trace and the traceback, include the row in the dataset |
| episode hits the 900-update cap | `truncated: true`, `observed_termination: null`, **capped score = 900**, included; this is a capped observation, not an ordinary right-censored survival time (§5.1) |
| episode collides on update 1 | valid, capped score = 1, included |
| a whole seed×condition cell errors | primary analysis uses complete pairs only; sensitivity analysis re-runs with errors scored at their last completed update; the lost pairs are counted and reported (§7.3) |
| a condition is structurally impossible to run | the campaign halts and the report says so; the condition is not silently replaced |

**No unsuccessful episode is discarded at any stage.** The dataset is append-only JSONL; the
analysis reads it and reports counts of every status. If a time-to-event analysis is retained, it is
declared separately as a sensitivity analysis with an explicit censoring-aware method (cap-reaching
episodes censored at 900); it never replaces the capped-score primary and is labelled as a different
estimand.

### 7.7 Uncertainty

- Paired percentile bootstrap over seeds (10,000 resamples) for the difference, reported as
  *approximate* at N = 16; the exact attainable interval is also printed.
- Secondary: two-level cluster bootstrap (episodes within seed) for the episode-level estimate.
- Effect sizes: paired mean difference, median difference, Cohen's dz, and the win/loss/tie count.
  A unanimous 16–0 split has raw two-sided `p = 2/65,536 = 0.0000305`; a 14–2 split has
  `p = 0.004181`, which passes Holm step 1 at m = 4 but not a stricter unadjusted α of 0.001. These
  numbers are stated rather than hidden.

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

Rates from §2.2. Neural conditions = A, B, C, D, F. **Every line is labelled measured or
estimated.** All numbers are single-process wall time. The floor is a game-side control and costs
essentially zero (it is not a neural arm); the substrate-free floor is never added as a simulation
line.

| Scope | Assumption | Wall time |
|---|---|---|
| one 213-update episode | **measured** (22.345 s) | 22.3 s |
| one 900-update episode | measured rate × cap | 94.4 s |
| one seed, 10 eval episodes | measured rate | 3.73 min |
| one seed, 10 eval episodes | worst case (every episode caps) | 15.74 min |
| one condition × 10 seeds (N = 10 basis), eval only | 10 × 3.73 min | 0.62 h |
| one condition × 10 seeds (N = 10 basis), eval only | 10 × 15.74 min | 2.62 h |
| 5 conditions (A, B, C, D, F) eval, N = 10 | both ends | 3.10 h – 13.11 h |
| 5 conditions eval, N = 16 | ×1.6 | 4.97 h – 20.98 h |
| **A′ mirror** of A (all seeds, all episodes, +20–40% plastic overhead), N = 10 | estimated | 0.75 h – 3.67 h |
| A′ mirror, N = 16 | estimated | 1.19 h – 5.87 h |
| **C′ mirror** of C, same coverage and overhead, N = 10 | estimated | 0.75 h – 3.67 h |
| C′ mirror, N = 16 | estimated | 1.19 h – 5.87 h |
| **Fβ** eval (all seeds, all episodes), N = 10 | measured rate | 0.62 h – 2.62 h |
| Fβ eval, N = 16 | measured rate | 0.99 h – 4.20 h |
| **F training rollouts** (20 episodes/seed), N = 10 | measured rate | 1.24 h – 5.25 h |
| F training rollouts, N = 16 | measured rate | 1.99 h – 8.39 h |
| **Fβ training rollouts** (20 episodes/seed), N = 10 | measured rate | 1.24 h – 5.25 h |
| Fβ training rollouts, N = 16 | measured rate | 1.99 h – 8.39 h |
| B/D plasticity overhead (2 conditions, +20–40%), N = 10 | estimated (trace update on ≤683,100 edges) | 0.25 h – 2.10 h |
| B/D plastic overhead, N = 16 | estimated | 0.40 h – 3.36 h |
| random-graph construction (one per seed), N = 10 | estimated 2–15 min per graph | 0.33 h – 2.50 h |
| random-graph construction, N = 16 | estimated | 0.53 h – 4.00 h |
| E training and evaluation | torch CPU, 7 or 14 inputs, 4 outputs | < 0.17 h |
| floor (game-side, substrate-free) | no simulation | ≈ 0 h |
| analysis, figures, replay checks | | < 0.5 h |

**Declared budget, single process, including A′/C′/Fβ and their training:**

| design | estimated total |
|---|---|
| **N = 10** | **≈ 8.9 h – 38.8 h** |
| **N = 16** | **≈ 13.9 h – 61.7 h** |

**This corrects REV2's 19 h – 78 h (N = 10) and 30 h – 125 h (N = 16).** Those figures over-counted
F/Fβ training by about a factor of five: with a measured 22.345 s per 213-update episode, 20
training episodes per seed is 7.45 min per seed at the measured rate and 31.5 min at the capped
worst case, so F training at N = 10 is 1.24 h – 5.25 h, **not** 6.2 h – 26.2 h. The corrected total
also states explicitly what REV2 left implicit: the substrate-free floor costs no simulation; the
20–40% plastic overhead applies to A′, C′ and B/D but not to the fixed arms; and the N = 16 scaling
is per-seed on every per-seed line.

**Why this differs from the audit's provisional ≈ 10 h – 42 h (N = 10) and ≈ 16 h – 67 h
(N = 16).** The audit included the floor as if it consumed evaluation time and rounded some
per-condition lines differently. This recalculation is independent: it derives every line from the
measured rate, applies overhead only where the plastic path is actually used, and treats the floor
as game-side. The two are close, and neither is copied from the other. All non-measured figures are
assumptions and are labelled as such; the dominant uncertainty is the worst case, which assumes all
600 (N = 10) or 960 (N = 16) evaluation episodes run to the cap.

Halving K from 10 to 5 roughly halves the evaluation half of the budget. Parallelism across 12 CPUs
could reduce wall time by up to ~8× but introduces determinism risk (BLAS thread counts, per-process
memory) and is **not** part of the primary plan.

### 9.3 Blocking operational constraint

At original audit time only **0.5 GB of 15.34 GB RAM was available**; the most recent preflight
before this revision measured **≈ 1.1 GB free** (1,152,972 KB of 16,087,140 KB), still below the
4 GB gate. The t5 substrate plus traces is on the order of a few hundred MB, so the substrate is not
the problem, but the machine is. The gate is **4 GB of free physical memory**, and it is not
weakened, rounded down or waived.

The campaign must **re-check free memory immediately before starting** and record it. If < 4 GB is
free, the campaign does not start and reports the reason rather than failing mid-run (this is the
Phase 2.5 "never silently skip" rule applied here). While the machine is below the gate:

- no BANC-scale graph randomisation;
- no full campaign simulation;
- no training run;
- no memory-intensive test suite.

Safe implementation, static inspection, unit-level tests on synthetic graphs and document work may
proceed. Any execution work that is skipped for this reason is recorded as **pending resource
availability**, never as completed.

---

## 10. Implementation sequence

The implementation is split into explicitly gated stages. **No stage may consume the output of a
stage that has not passed its acceptance criteria**, and the pilot is split in two because the two
pilots answer different questions. Nothing below is implemented at the time of writing.

| Step | Inputs | Deliverable | Acceptance criteria | Depends on |
|---|---|---|---|---|
| **10.0** Protocol approval | this document | frozen REV3 with SHA-256 and freeze record | user approval of §12 recorded; no code may implement a *confirmatory* decision before approval | — |
| **10.1** Campaign skeleton (G5) | `experiments/phase_4h/common.py`, Phase 7 runner structure | `experiments/phase_8/`: seed derivation, config loader, append-only JSONL writer with resume, run manifest, versioned schema + validator | validator rejects a malformed row; a 1-update dummy episode round-trips; resume is idempotent on (condition, seed, episode); no result directory is overwritten | 10.0 |
| **10.2** Condition A baseline (part of G5/G1 input) | `LiveBancStepper`, `LiveSensoryDrive`, `GameActionDecoder`, `NeuralClosedLoop` | `conditions/a_fixed.py`, a callable episode with an explicit seed | reproduces the Phase 7 fingerprint `cca811f3…b2fb` on seed 42 at 213 updates; weight fingerprint unchanged | 10.1 |
| **10.3** Pilot 1 — A viability | 10.2 only | `experiments/results/phase_8/pilot1/`, 3 seeds × A × 3 episodes | reports survival, action counts, motor spikes, floor status; **does not estimate any C1–C4 contrast and must not be described as doing so**; establishes the A row of the §0/U1 gate only — the full three-case U1 decision needs F and is made at 10.8 | 10.2 |
| **10.4** Condition C + randomisation validation (G3) | `brain/banc_graph.py` invariants, 10.1 | `experiments/phase_8_random/` target-exchange rewire, R1–R18 reporter, per-graph certificates | **all R1–R18 pass**, including rewired fraction ≥ 0.99, neighbourhood overlap ≤ 0.01, rewiring-distance plateau reached, zero duplicates, zero self-edges, exact degree, exact weight multiset and **per-source weight profile (R9b)**; ≤ 15 min per graph at BANC scale; **BANC-scale construction is blocked while below the memory gate** | 10.1 |
| **10.5** Condition F and control Fβ (G2) | torch (present), `GameActionDecoder` retained for A–D | `readout/` linear readout, genuinely state-independent Fβ (feature weights fixed 0, only biases trainable), frozen-parameter ablation, `conditions/f_readout.py`, `controls/f_beta.py`, per-decision `motor_activity` | connectome fingerprint unchanged before/after; trainable-parameter set == readout parameters only; `motor_activity` present on 100% of decisions; Fβ feature vector identically zero; E4 undefined (0/0) reported as **not evaluable**, never pass | 10.2 |
| **10.6** A′ and C′ identity controls (G1) | `plasticity/live_stepper.py` additive subclass; `PlasticityEngine`, `WeightState` | `controls/a_prime.py`, `controls/c_prime.py` with the 19-field P1–P19 comparison | **A′ ≡ A and C′ ≡ C exactly, every seed and episode, zero tolerance**; `eta = 0` through the actual rule; weight delta array exactly zero; a mismatch is a hard stop and marks B/D INVALID | 10.4, 10.2 |
| **10.7** Conditions B and D (G1) | 10.6 | `conditions/b_plastic.py`, `d_plastic.py` | `eta > 0` changes weights and only weights; A′/C′ still exact with the same stepper; no silent retry; any mismatch stops the campaign | 10.6 |
| **10.8** Pilot 2 — variability and control certification | 10.2, 10.4, 10.5, 10.6, 10.7 | 3 seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes | computes paired sd for C1–C4 and reports `σ_max` with its upper confidence limit; **A′ ≡ A and C′ ≡ C on all 3 seeds**; **B is included** so `σ_C2` is estimated; applies the **predeclared** N decision (N = 16 primary; N = 10 only if `σ_max ≤ 113.05` is defensible); does **not** test hypotheses or estimate campaign effects | 10.3, 10.4, 10.5, 10.6, 10.7 |
| **10.9** Condition E (G4) | `evaluation/`, torch, shared environment | E-matched and E-full REINFORCE learner on the 7/14-feature interface | training seeds disjoint from evaluation seeds and asserted; no privileged input; E-matched beats the substrate-free floor on its own training distribution before the campaign (otherwise §0 gate) | 10.1 |
| **10.10** Campaign (G5) | 10.2, 10.4–10.7, 10.9 | `run_campaign.py` over 6 conditions + A′/C′/Fβ, N from 10.8 × K = 10 | 2 seeds complete with all artifacts valid; A′/C′ exact-equality reports present for every completed seed; memory preflight ≥ 4 GB; **below the gate the campaign does not start** | 10.8, 10.9 |
| **10.11** Analysis (G6) | campaign JSONL | `analyse_phase_8.py`: exact sign-flip at the actual N, Holm m = 4/3, bootstrap, effect sizes, floor decomposition, F/Fβ/A decomposition, E1–E5 checklist | reproduces every §7 number from the JSONL; no hand-entered values; thresholds recomputed at the actual complete-pair N; zero/missing-pair rules applied as declared | 10.10 |
| **10.12** Report and freeze | analysis outputs | `reports/PHASE_8_RESULTS.md` + `.json` + freeze record | integrity 36/37 non-README; every limitation restated; §3.6.5 forbidden statements absent; readout claim present only if E1–E5 all pass; Phase 6 result unchanged | 10.11 |
| **10.13** Viability check (G7) | Phase 7 artifact, Phase 8 JSONL | `evaluation/viability.py`, read-only report | implements U1's three gate cases without tuning; never marks blocked work as complete | 10.12 |

**Ordering rationale.** The protocol is approved first. The skeleton is then built so every later
stage writes through one validated path. A comes before anything else because it is the reference and
must reproduce Phase 7 bit-for-bit. **Pilot 1 is deliberately narrow**: it measures whether A can
act at all and never touches a contrast, so it cannot be misread as a preliminary estimate of C1–C4.
C must precede B and D, because without a second substrate H2 and the 2×2 are undefined. F and Fβ
are built together because F alone is uninterpretable. A′ and C′ must exist before B and D are
certified. **Pilot 2 comes after every condition it measures exists**, which is why it cannot be
placed at 10.3: a pilot that includes B, C, F, A′ and C′ cannot run before those conditions are
implemented, and a pilot that omits them cannot estimate the σ that governs N. E is last among the
conditions because it is least coupled and requires no neural substrate.

**What the pilots do and do not establish.** Pilot 1 establishes only whether the A pipeline runs and
whether the floor is present. Pilot 2 establishes the paired dispersion for C1–C4, the identity of
A′ and C′, and the fact that Fβ is functioning. **Neither pilot is a hypothesis test, neither may be
reported as evidence for or against H1–H6, and neither may be merged into the campaign dataset.**
The pilot seeds are recorded separately and are not reused as campaign seeds unless the protocol
explicitly declares them to be part of the campaign (it does not).

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
19. `max_steps` 900 is an administrative cap. The primary outcome is the **capped survival score**
    `min(observed_updates, 900)`, not an unrestricted duration and not an ordinary right-censored
    survival time (§5.1). Cap-reaching episodes are recorded as 900 with `truncated: true`; their
    true termination time is unknown and is not estimated.
20. Game time (16.67 ms) and neural time (0.5 ms) are bridged by
    `target_step = round(game_ms / 0.5)`; the residual rounding error is bounded at half a neural
    step and does not accumulate, but the two clocks are not physically coupled.

**Design**

21. The primary outcome has one degree of freedom per seed and **N = 16 seeds** (N = 10 only as the
    predeclared fallback of §7.1). At N = 16 the smallest attainable **two-sided** p is
    `2/65,536 = 0.0000305176`; reaching raw p ≤ 0.05 requires at most 3,276 of the 65,536 sign
    vectors, and surviving Holm step 1 (m = 4) requires at most 819. Under equal-magnitude
    differences at least 14 of 16 seeds must favour the same direction to pass step 1. The
    normal-theory MDE is ≈ 42 updates at σ = 60 against a declared SEI of 100 (≈ 50 at the Holm
    step-1 threshold). These are approximations to, not exact powers of, the sign-flip/Holm
    combination. **This design can detect large effects only.**
22. σ = 60 is an **assumption**, extrapolated from a 3-seed pilot whose observed sd was 67.3. A
    standard deviation estimated from 3 points has `df = 2` and is extremely unstable. The 80%
    upper confidence limit for σ at `df = 2` is ≈ **2.1×** the point estimate, i.e. ≈ 143 updates,
    which is why **N = 16 is primary**: it keeps the MDE at the SEI even if the true σ is that
    large. N = 10 is permissible only if the pilot's **largest** paired sd across C1–C4 (including
    C2, hence B in the pilot) is ≤ 113.1 with a defensible upper limit; a 3-seed pilot alone cannot
    establish that, so N = 16 is the default and is folded into U7.
23. The degree-preserving null is implemented by **target exchange**: each selected edge keeps its
    source and its weight, and two edges swap targets. It therefore preserves in/out degrees, signs,
    node identities, the weight multiset **and the per-source outgoing weight profile (R9b)**. It
    does **not** preserve component structure. C is therefore not a pure "wiring only" null: it
    differs from A in global fragmentation as well as local wiring. By contrast, endpoint
    re-pairing would have changed the per-source weight sums; that parameterisation is rejected for
    this protocol (U18). The §3.3.1 diagnostics detect the common failure modes of a rewire
    (insufficient movement, poor mixing, degree corruption) but are **not** a proof that the null
    is well mixed; R14 is a rewiring-distance plateau diagnostic only.
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
29. **The attainable-p floor is a property of the design and N, not of the data.** At N = 16 the
    smallest raw two-sided p is `2/65,536 = 0.0000305`, and no contrast can be reported below an
    adjusted p of `8/65,536 = 0.000122` (m = 4) or `6/65,536 = 0.0000916` (m = 3), however large the
    true effect. At the N = 10 fallback the corresponding floor is raw 0.00195 and adjusted 0.0078
    (m = 4). A "significant" Phase 8 result will always carry that floor in its footnote.
30. A′, C′ and Fβ are **control arms, not conditions**: they produce no scientific claim of their
    own, and a failure in any of them consumes budget and ends in a methodological conclusion rather
    than a behavioural one. That expenditure is deliberate. The no-action floor is a **substrate-free
    game-side control** and is never counted as a neural-substrate arm or given a simulation budget.
31. The motor-driven/bias-driven classification (§3.6.3) is a **counterfactual on a frozen model**.
    It establishes whether the recorded decision depended on motor features; it does not establish
    that the dependence is biologically meaningful, and it says nothing about causality in the fly.
32. The exact sign-flip test assumes the paired differences are **exchangeable under sign reversal**
    (symmetric about zero under the null, independent across seeds). That assumption can fail if the
    two arms differ in dispersion or if any coupling between arms is not removed by pairing. The
    design pairs environment seeds and network draws, but the assumption is a limitation of the
    inference, not a guarantee.
33. A pilot with 3 seeds can only produce a very unstable σ and cannot certify N = 10. The N
    decision is therefore made from an upper confidence limit, not from the point estimate, and is
    made before the campaign; a larger N than 16 may be required if the upper limit exceeds 142.8.

---

## 12. Unresolved decisions requiring approval

Each item states the options and a recommendation. **None is applied and none is approved.**
Recommendations are advisory; every alternative stays visible. The table below is the complete
proposed-decision register: it records what this revision would do if approved, and its status is
**PROPOSED — awaiting human approval**. Nothing in this document may be cited as an approval, and
no implementation step that depends on a confirmatory choice may run before the user records one.

| ID | Proposed decision | Status |
|---|---|---|
| U1 | three gate cases for the pilot floor (both floor / A floors only / F floors only); C and D reported, never gated; floor is a substrate-free game-side control | **PROPOSED — not approved** |
| U2 | B/D eta = 0.5 (Phase 5 declared value); no tuning on the game | **PROPOSED — not approved** |
| U3 | primary outcome is the **capped survival score** `min(updates, 900)`, not right-censored survival | **PROPOSED — not approved** |
| U4 | confirmatory null is the degree-preserving signed rewire; component- and sign-randomised variants exploratory | **PROPOSED — not approved** |
| U5 | E implemented directly as REINFORCE against the 5-tuple API; no Gymnasium/SB3 install | **PROPOSED — not approved** |
| U6 | K = 10 evaluation episodes per seed | **PROPOSED — not approved** |
| U7 | **N = 16 primary**; N = 10 only as the predeclared fallback of §7.1, with the pilot including B and `σ_max` governing the decision | **PROPOSED — not approved** |
| U8 | E-full (14 features) included as exploratory, capacity-matched to E-matched | **PROPOSED — not approved** |
| U9 | B/D plasticity runs during evaluation (primary); train-then-freeze exploratory only | **PROPOSED — not approved** |
| U10 | no-action floor is a **substrate-free game-side control policy**, measured by replay, never a neural arm | **PROPOSED — not approved** |
| U11 | planning budget ≈ 8.9–38.8 h (N = 10) / ≈ 13.9–61.7 h (N = 16), single process; no weakening of the 4 GB memory gate | **PROPOSED — not approved** |
| U12 | Phase 8 does not write a new `learning/` implementation | **PROPOSED — not approved** |
| U13 | C′ on **all N × K** at eta = 0 through the actual plasticity pathway, same P1–P19 and hard stop as A′; pilot and campaign coverage consistent | **PROPOSED — not approved** |
| U14 | confirmatory family m = 4, including C4 = F − Fβ | **PROPOSED — not approved** |
| U15 | H3 **confirmatory**, exactly one status in every register, contingent on U14/U15 being resolved before data | **PROPOSED — not approved** |
| U16 | Fβ full N × K rollout, **genuinely state-independent** (feature weights fixed 0, only output biases trainable); no hidden or state pathway | **PROPOSED — not approved** |
| U17 | readout evidence bar E3/E4 at the declared low thresholds (≥ 1% of decisions, ≥ half of seeds; ≥ 10% motor-driven), with 0/0 reported as not evaluable | **PROPOSED — not approved** |
| U18 | degree-preserving null uses **target exchange** (sources and weights fixed, targets swapped), preserving R9b; endpoint re-pairing rejected | **PROPOSED — not approved** |

### U1 — action if the pilot confirms the floor

*Decision.* What to do when the pilot shows **zero non-`NO_ACTION` executions across all pilot seeds
and episodes**, evaluated against the substrate-free no-action floor. Three gate cases must be
distinguished, because they license different conclusions:

| case | A | F | E-matched | action |
|---|---|---|---|---|
| **U1-A** | above floor | above floor | — | proceed; the gate is passed |
| **U1-B** | floored | floored | any | **platform floor**: run the predeclared floor decomposition and stop for a scope decision; do not claim an effect for any neural condition |
| **U1-C** | floored | above floor | — | **readout rescues the platform**: proceed, but report A's floor and F's success as a readout-specific finding, not as evidence about the substrate |
| **U1-D** | above floor | floored | — | **readout harms**: proceed with the readout contrast, report F's failure, and do not treat Fβ as the floor |
| **U1-E** | floored | floored | above floor | environment is solvable but not from this interface; report A–D as an interface limitation |

C and D are **reported, never gated**: no pre-campaign stop rule is attached to them, and no
outcome in C or D can authorise or block the campaign. The floor is a **substrate-free game-side
control** measured by replaying the paired environment seeds with a constant-`NO_ACTION` policy; it
is not a neural arm and is never compared as if it were one.

*Options for U1-B.* (a) run the full campaign anyway and report a floor result; (b) stop, report the
floor plus a pathology decomposition (no motor spikes / no sustained activity / decoder gate never
met), and request a scope decision; (c) authorise a **separate, pre-registered** follow-up that
changes drive or decoder; (d) if A and F floor but E-matched does not, run only E and report the
environment as solvable-but-not-from-this-interface.
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

*Options.* (a) **capped survival score** in updates, `min(observed_updates, 900)`; (b) total task
reward; (c) capped survival with reward as co-primary.
*Recommendation.* **(a)**. The capped score is a bounded, game-defined outcome and is **not** called
right-censored survival; a time-to-event analysis, if retained, is a separately declared sensitivity
analysis (§5.1, §7.6). Reward is coin-dominated (coin +1, collision −1, survival +0.01/step) and
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

*Options.* (a) **N = 16 as the primary design**; (b) N = 10 as a predeclared fallback; (c) N = 20.
*Recommendation.* **(a), with (b) available only on the predeclared condition of §7.1.** This is a
**change from V1**, which recommended 10 with an escalation rule. That rule applied to a 3-seed σ
estimate with 2 degrees of freedom; its 80% upper confidence limit is ≈ 2.1× the point estimate
(§11.22), which implies N ≈ 16 for an MDE of 100. Applying V1's own escalation rule honestly
therefore selects 16. The σ that governs the decision is the **largest** paired sd among C1–C4, and
the pilot must include **B** so that `σ_C2` is estimable. N = 10 is permitted only if the pilot's
`σ_max ≤ 113.05` can be defended from its upper confidence limit; a 3-seed pilot generally cannot,
so (b) requires a larger pilot (≥ 5 seeds) or independent variance evidence. The choice is made
before the campaign and is never revisited after outcomes are seen.

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

*Options.* (a) derive the floor from the game configuration without replay; (b) add a **substrate-free
game-side control policy** that always emits `NO_ACTION` and is replayed on the paired evaluation
seeds.
*Recommendation.* **(b), implemented as a control policy, not a condition and not a neural arm.**
This is a **correction from V1**, which called the floor "analytically known" and "computed at zero
cost". Collision timing depends on obstacle layout, so the floor **must be measured** by replaying
the paired environment seeds with a constant-`NO_ACTION` policy; it costs seconds, requires no neural
substrate, and produces no simulation rows. It is never counted among the neural-substrate arms, is
never budgeted as a condition, and cannot be used simultaneously as the "floor" and as a neural
condition.

### U11 — compute budget ceiling

*Options.* (a) accept the recalculated §9.2 estimate, **≈ 8.9 h – 38.8 h (N = 10)** or
**≈ 13.9 h – 61.7 h (N = 16)** single-process, including A′/C′/Fβ and their training; (b) cap the
budget by dropping K to 5 and Fβ's training rollouts; (c) parallelise across CPUs with a determinism
audit.
*Recommendation.* **(a)** as the planning figure. REV2's 19–78 h is withdrawn: it over-counted F/Fβ
training by about 5× (§9.2). Consider (c) only after the pilot, and only with per-process thread
pinning and a byte-identical determinism check. (b) reduces cost but also reduces the precision of
every within-seed mean. The budget estimate is **not** an authorisation to run: the memory gate of
§9.3 still applies, and below 4 GB free no campaign or training starts.

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
*Options.* (a) require C′ on **all N seeds × K episodes**, exactly like A′, with the same 19-field
P1–P19 comparison and the same hard stop; (b) require C′ on the pilot seeds plus episode 1 of every
campaign seed; (c) omit C′, rely on A′, and disclose that D shares the stepper.
*Recommendation.* **(a)**. C′ runs at `eta = 0.0` through the **actual plasticity pathway** (the
same rule and stepper used by D, not a bypass), so the identity certificate covers D's real code
path. It is one extra condition's runtime (§9.2) and it converts "D shares validated code" into "D
shares code that was validated on its own graph". The pilot and the campaign use the **same**
coverage: the pilot's C′ is a full 3 seeds × 3 episodes mirror, and the campaign's C′ is a full
N × K mirror. (b) is a defensible compromise only if D is then reported without a causal
attribution; (c) leaves the only remaining unvalidated path in the campaign and is not recommended.
An A′/C′ mismatch is a hard stop: no silent retry, no tolerance change, no seed substitution
(§3.8.5).

### U14 — confirmatory family size *(new in REV2)*

*Decision.* Does C4 (`F − Fβ`) join the confirmatory family?
*Options.* (a) **m = 4** with C4; (b) **m = 3** without C4, C4 demoted to exploratory.
*Recommendation.* **(a)**. Without C4 the readout claim is not identifiable — a bias term alone can
produce `F − A > 0` with silent motor populations. Choosing (b) is coherent, but it means **no
decoding claim may be made at all**, because §3.6.4 requires a Holm-surviving test and an
exploratory contrast cannot supply one. Both variants' Holm numbers are tabulated in §7.5.

### U15 — confirmatory status of H3 *(new in REV2)*

*Decision.* V1 labelled H3 exploratory while placing `C1 = F − A` in the confirmatory family.
*Options.* (a) H3 **confirmatory**, identical in every register, contingent on U14/U15 being
resolved before data; (b) H3 **exploratory**, in which case C1 must leave the confirmatory family,
m changes, and every Holm threshold and the analysis plan must be edited together.
*Recommendation.* **(a)**. The readout question is one of the three the phase exists to answer, and
(a) is the only labelling consistent with V1's own contrast table. **Exactly one status is
permitted.** If (b) is chosen, the hypothesis register (§4), §5.3, §5.4, §7, §10 and this register
must all say exploratory; a document that says confirmatory in one place and exploratory in another
is defective and blocks authorisation.

### U16 — scope of Fβ *(new in REV2)*

*Decision.* Fβ is a full rollout arm (its own training + evaluation on the neural substrate). How
much of it is mandatory?
*Options.* (a) all N seeds × K episodes, full training, exactly mirroring F, with Fβ **genuinely
state-independent** — feature weights fixed at exactly 0.0, only the output biases trainable, so its
action cannot depend on any observation; (b) pilot seeds only, plus the ablation counterfactual
(§3.6.3) on every F decision; (c) no Fβ rollouts at all — rely only on the ablation counterfactual.
*Recommendation.* **(a)** if U14 selects m = 4, because C4 needs a paired per-seed difference and
that cannot come from a 3-seed pilot. A "bias-only" label is used **only** when no hidden-layer or
state-independent pathway other than the output biases is trained; if any feature pathway trains,
the arm is not Fβ and cannot support C4. (b) is acceptable only if C4 is dropped, and then no
decoding claim is possible. (c) answers the mechanism question but not the behavioural one.

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

**Consistency with §11.23.** Under (a) the per-source outgoing weight profile **is** preserved, so
the limitation must not claim otherwise. The limitation that remains is component structure: target
exchange preserves local degree, sign and per-source weights but not global fragmentation. If (b)
were selected, §11.23 would have to be rewritten to say that per-source weight sums are **not**
preserved and that R9b is descriptive. The document must not contain both statements at once. The
rewiring-distance plateau (R14) remains a diagnostic only; it is **not** evidence that the null is
well mixed.

### 12.1 Review findings for U1–U18

Ambiguities and inconsistencies found while reviewing V1 and REV2, and how REV3 addressed them.
**No item was decided on the user's behalf**; each remains open above.

| ID | Finding | Addressed in REV3 by |
|---|---|---|
| U1 | Gate referenced only "A or F" while §0 predicted A,B,C,D,F also floor; §7.8 used a *different* floor definition ("≥ 4 of 6 conditions") for a different purpose | three gate cases (U1-A to U1-E) with C/D explicitly reported, never gated; the 4-of-6 rule remains a post-campaign **reporting** rule; floor is substrate-free |
| U2 | Option (c) named no eta value and did not mention that Phase 5 found 0.1–2.0 indistinguishable | value set declared in advance; Phase 5 saturation noted; cost stated |
| U3 | Option (c) "co-primary" silently violates the single-primary discipline and did not say how censoring would apply to reward | primary renamed **capped survival score**; right-censoring language removed from the primary; any time-to-event analysis is a separate declared sensitivity analysis |
| U4 | "component-preserving" was undefined operationally; the sign-randomized variant was not distinguished from a wiring null | operational definition added for (b); (c) labelled as answering a sign question, not a wiring question |
| U5 | Option (b) did not state its cost | dependency, pinning and wrapper-validation costs listed |
| U6 | K's interaction with cost and with the seed-level df was unstated | clarified: K affects within-seed precision only |
| U7 | "Confirm only after the pilot measures σ_paired" implied a 3-seed estimate was sufficient; it has 2 df | N = 16 primary; N = 10 fallback only on §7.1's predeclared σ_max condition; pilot must include B |
| U8 | No capacity-matching requirement for E-full | same architecture and training budget required |
| U9 | "(b) exploratory trained-then-frozen" did not say the frozen evaluation needs held-out seeds | added |
| U10 | **Error**: floor called "analytically known" and "computed at zero cost" — collision timing depends on layout | floor measured by replay with a substrate-free `NO_ACTION` policy; never counted as a neural arm |
| U11 | Budget was stale and then over-corrected | recalculated to ≈ 8.9–38.8 h (N = 10) and ≈ 13.9–61.7 h (N = 16), with the 5× F/Fβ training error corrected; memory gate unchanged |
| U12 | Did not state that filling `learning/` would duplicate the Phase 5 mechanism | duplicate-module constraint cited |
| U13 | C′ coverage was ambiguous (full vs sample) | full N × K at eta = 0 through the actual pathway; same P1–P19 and hard stop; pilot and campaign consistent |
| U14 | m = 4 vs m = 3 was stated but C4's role was not tied to the decoding claim | §5.3 and §7.5 state both variants; (b) makes any decoding claim unavailable |
| U15 | H3 had two statuses in different registers | exactly one status; propagation rule across §4, §5.3, §5.4, §7, §10 and this register |
| U16 | Fβ could be trained through a hidden or state-dependent pathway while called "bias-only" | Fβ is genuinely state-independent: feature weights fixed at 0, only output biases trainable |
| U17 | Thresholds were conventions with no failure treatment | low thresholds retained; E4 0/0 is **undefined / not evaluable**, never a pass |
| U18 | Swap parameterisation was implicit and conflicted with §11.23 | target exchange declared; R9b preserved; §11.23 restated consistently; plateau is a diagnostic only |

Two further inconsistencies were found **outside** U1–U12 in V1 and are corrected in place, with the
choice still open: the H3 confirmatory/exploratory contradiction (§4, now U15) and the claim
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
| N (seeds) | **16 primary**; 10 only as the §7.1 predeclared fallback | §7.4, U7 — 16 keeps the MDE at the SEI under the `df = 2` upper confidence limit; 10 requires `σ_max ≤ 113.05` |
| K (evaluation episodes/seed) | 10 | U6 |
| training episodes/seed (F, Fβ) | 20 | declared |
| training episodes (E) | 2,000 gradient updates | declared |
| truncation cap | 900 updates | game config, unchanged |
| SEI | 100 updates | declared convention |
| α | 0.05, two-sided, Holm over **m = 4** (C1–C4) pending U14; m = 3 if U14 selects it | §5.3, §7.5 |
| exact sign-flip assignments (N = 16) | 65,536 | 2^N |
| minimum attainable one-sided p (N = 16) | 1/65,536 = 0.0000152588 | **not** the two-sided value |
| minimum attainable two-sided p (N = 16) | 2/65,536 = 0.0000305176 | attained by `sign(d)` and its negation |
| count threshold, two-sided raw p ≤ 0.05 (N = 16) | ≤ 3,276 of 65,536 | 3,276/65,536 = 0.0499878; 3,277/65,536 = 0.0500031 |
| Holm-adjusted minimum, m = 4 (N = 16) | 4 × 2/65,536 = 0.0001220703 | §7.5 |
| Holm-adjusted minimum, m = 3 (N = 16) | 3 × 2/65,536 = 0.0000915527 | §7.5 |
| MDE at N = 16, σ = 60 | 42.024 | §7.4, 2.801585·σ/√N |
| **Fallback N = 10** | | |
| exact sign-flip assignments (N = 10) | 1,024 | 2^N |
| minimum attainable two-sided p (N = 10) | 2/1,024 = 0.001953125 | attained by `sign(d)` and its negation |
| count threshold, two-sided raw p ≤ 0.05 (N = 10) | ≤ 51 of 1,024 | 51/1,024 = 0.049805; 52/1,024 = 0.050781 |
| Holm-adjusted minimum, m = 4 (N = 10) | 4 × 2/1,024 = 0.0078125 | §7.5 |
| MDE at N = 10, σ = 60 | 53.155 | §7.4 |
| bootstrap resamples | 10,000 | §7.7 |
| eta (B, D) | 0.5 | Phase 5 declaration, no retuning |
| eta (A′) | exactly 0.0 | §3.8 — must reproduce A bit-for-bit |
| eta (C′) | exactly 0.0 | §3.8 — must reproduce C bit-for-bit |
| Fβ readout | **state-independent**: all feature weights fixed at exactly 0.0, only output biases trainable | §3.6.2, U16 |
| graph randomisation seed stream | `SeedSequence([MASTER_SEED, seed, "structure"])` | §3.3.1 R18 |
| weight bounds | 0.5–2.0× initial, 5 pA/update | `configs/plasticity_banc.yaml` |
| τe | 20 ms | `configs/plasticity_banc.yaml` |
| modulation | gain 1.0, τ 50 ms, clip ±5 | `configs/plasticity_banc.yaml` |
| sensory current | 200 pA per active feature | `configs/banc_sensory_mapping.yaml` |
| decoder window | 50 ms, ≥3 active, ≥5 spikes, activation 0.20, release 0.10 | `configs/motor_decoder.yaml` |

---

*End of draft. This document authorises no execution. No BANC-scale randomisation, campaign
simulation or training may start until §12 is approved, the relevant implementation gates of §10
pass, and the memory preflight of §9.3 records ≥ 4 GB free. Awaiting approval of §12.*
