# Phase 8 — Integration Sprint 1

**Date:** 2026-11-17
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines, 146,643 bytes)
**REV3 (preserved, not overwritten):** SHA-256 `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf` (1,848 lines)
**Correction report:** `reports/PHASE_8_REV3_TO_REV4_CORRECTION_REPORT.md`, SHA-256 `add143d127b0dfc1083a0c15c0cd0e4080c518c5d21ed61537db912ee042b24a` (203 lines)
**Approval status:** U1–U18 remain **PROPOSED — not approved** (REV4 §12). No campaign may start.

---

## 1. Scope and authorisation

This sprint performed three things and nothing else:

1. resolved the seven residual REV3 ambiguities and published REV4 plus a correction report;
2. implemented the `conditions/` and `controls/` packages and connected them to the
   existing mechanisms (G1, G2, G4 integration);
3. connected the conditions to the G5 harness contract at the level a synthetic test can
   establish, and re-ran the focused suites.

No episode was run against the BANC substrate. No pilot, no campaign, no training
campaign, no BANC randomisation, no weight or connectivity change outside an in-memory
synthetic test stepper. U1–U18 are unapproved, so no experimental data were collected and
no confirmatory claim is made anywhere in this report.

Two of the seven REV4 changes touch declared quantities, and both are arithmetical or
definitional, not scientific: the fallback σ_max bound became **112.87** (the exact value of
the declared formula, replacing the transcription artefact 113.05, i.e. slightly
**stricter**), and the R13 denominator is now defined. SEI = 100, N = 16/10, α, K = 10, the
900-update cap, eta, bounds, Holm family and every contrast are unchanged. The full
item-by-item justification is in the correction report; nothing is repeated here except where
the sprint touched code.

---

## 2. What is new in this sprint

### 2.1 `experiments/phase_8/conditions/` — 10 files, 2,200 lines

| module | declaration |
|---|---|
| `base.py` | `Requirements`, `CONTROL_REQUIREMENTS`, component bundles (`NeuralComponents`, `ConventionalComponents`, `Components`), `validate_components`, `assert_seed_disjoint`, `describe_condition` |
| `a_fixed.py` | A — biological substrate, fixed weights, fixed decoder; refuses a plastic stepper (and therefore any plasticity hook) |
| `b_plastic.py` | B — biological substrate, three-factor plasticity at eta = 0.5 through `PlasticityUpdateHook` |
| `c_random.py` | C — target-exchange substrate, fixed weights; requires a passing structure certificate |
| `d_plastic.py` | D — target-exchange substrate, plasticity at eta = 0.5 |
| `e_conventional.py` | E / E-full — REINFORCE on the game's five-tuple API, 7 or 14 declared features |
| `f_readout.py` | F — fixed substrate, trainable motor-only readout |
| `execute.py` | `neural_episode`, `conventional_episode`, `floor_episode`, `build_row`, `error_row`, motor/decision summaries, termination |
| `plasticity_hook.py` | per-update delivery of the adapter's reward stream to `stepper.learn` |

The package adds **no biological mechanism**. It assembles components that already existed
(Phase 7 closed loop, Phase 5 three-factor rule, G1 stepper, G2 readout, G4 learner) and
refuses, before an episode starts, any bundle that contradicts the declaration: wrong
stepper kind, wrong eta, a missing hook, an overlapping training/evaluation seed set in a
condition that trains (E, F, Fβ), a random condition without a structural certificate, F
given a state-independent readout, a floor row claiming a substrate.

`execute.neural_episode` adds the runtime invariants that are cheap to check and expensive
to miss:

- refusal if the network was reset between game updates (state continuity, REV4 §3.8.2);
- refusal if the structural or initial weight layer digest changed in the episode;
- refusal if a fixed-weight condition's before/after fingerprint differs;
- an `evidence` block recording stepper kind, digests, `weights_changed`, declared trains,
  and — for plastic conditions — `plasticity_path` (`mode`, `eta`, update-report count,
  hook call count, hook modes, hook-report digest);
- per-decision motor activity recorded in every neural condition regardless of whether the
  decoder returned an action, which is the REV4 §3.6.1 requirement;
- one `build_row` path that calls `validate_episode_row` before any row can reach a store.

Condition E is a separate path: it uses the game API only, never the neural loop, and holds
the encoder fed by declared scalar features.

### 2.2 `experiments/phase_8/controls/` — 8 files, 1,236 lines

| module | control |
|---|---|
| `a_prime.py` | A′ — A through the plastic code path at exactly eta = 0.0 |
| `c_prime.py` | C′ — C through the plastic code path on the same per-seed random graph |
| `zero_hook.py` | the zero-learning-rate hook both A′ and C′ must use |
| `equivalence.py` | P1–P19 exact comparison, first-mismatch hard stop, control invariants |
| `f_beta.py` | Fβ — bias-only, provably state-independent readout |
| `f_init.py` | F-init — the F architecture at seeded initial parameters, untrained |
| `floor.py` | substrate-free constant-`NO_ACTION` floor |

The A′/C′ contract is implemented as an identity, not a similarity. `COMPARISON_FIELDS`
contains all 19 fields: spike arrays and indices, spike/action-reward hashes, the full
record sequence, the survival/termination summary, action and decoder counts, reward
components, neural/game time, per-decision motor activity, the structural/initial/delta/
effective weight digests, `max |Δw| = 0.0`, zero changed edges, zero clamp hits, equal
weight fingerprint before and after, and zero mid-episode resets. The first unequal field
raises `EquivalenceMismatch` carrying `kind`, `control_id`, `field_id`,
`fields_checked_before_stop`, `tolerance = "none (REV4 §3.8.4)"` and the hard-stop action;
A′ invalidates B, C′ invalidates D. C′ additionally refuses a run whose graph digest differs
from the C run it is compared against.

Skipping the optimisation is **not** the control: the zero hook executes the rule once per
game update at eta = 0.0 and must return an exactly zero delta (`rule_executed_zero_delta`).

Fβ is built from `BiasOnlyReadout`: feature weights are fixed at exactly 0.0, excluded from
the optimizer, and `assert_state_independent` checks that the logits are constant over
feature vectors. A state-dependent readout is refused, so no network with a trainable
hidden-state pathway can be labelled bias-only. F-init shares F's architecture and trains
nothing. The floor owns no network, reads no spikes, changes no weight, replays the paired
environment seed with constant `NO_ACTION`, and its row states that it is not a
neural-substrate arm.

---

## 3. G1 — plastic stepper connected to B and D

B and D now run through `PlasticityUpdateHook`, which takes the deliveries the adapter's own
reward function already recorded, passes them to the Phase 5 `ModulationRewardProvider`, and
calls `LivePlasticStepper.learn(delta_t)` exactly once per game update. The stepper is an
additive subclass of `LiveBancStepper` and reuses `PlasticityEngine`; `PlasticSimulator.run`
is never called, so its batch reset cannot break continuity.

Verified in this sprint's synthetic tests:

- B runs and changes weights (`weights_changed is True`), records
  `plasticity_path.mode == "rule_executed"`, and the recorded structural digest matches the
  stepper's;
- D does the same on a target-exchanged graph and records the graph digest and
  `randomization_passed` in `evidence.structure`;
- A refuses a plastic stepper; A's fingerprint is identical before and after and it records
  `delta_digest is None`;
- the stepper suite independently proves eta = 0 is bit-identical to the fixed path, eta > 0
  produces reproducible weight changes, and a reset preserves learned weights.

Eta remains 0.5 for B/D and 0.0 for A′/C′. No plasticity parameter was changed.

## 4. G2 — readout connected to F, Fβ and F-init

F builds a `LinearReadout` over the declared 7-feature motor block and trains only readout
parameters; the encoder cannot receive sensory features, game state or earlier actions.
Fβ builds `BiasOnlyReadout` and is refused if supplied to F. F-init reuses the F
architecture with no updates. `neural_episode` records the decision-source description and
the training update into the row.

The fixed decoder path is unchanged: when `decision_source` is absent, `NeuralClosedLoop`
uses the same `GameActionDecoder` as before (A–D), and when it is present the readout decides
and the `readout` record is stored. In both cases `motor_activity` is recorded per decision,
including decisions where the decoder's output is null.

## 5. G4 — E baseline connected

E and E-full run directly on the five-tuple `reset`/`step` API with the declared 7/14-feature
encoder, no Gymnasium or Stable-Baselines3 dependency, and a hard pre-episode error when
training and evaluation seed sets overlap. Tests confirm the feature counts, that the
learner trains its own policy, that no privileged input channel exists, and that the seed
check refuses overlap.

## 6. G5 connection — what the synthetic tests do and do not show

Synthetic tests demonstrate:

- `configs/phase_8/` loads through the strict loader and every arm resolves through the
  registry;
- seed derivation is condition-independent for the environment and structure streams and
  condition-dependent for the network and learning streams;
- condition rows pass `validate_episode_row` with the expected condition, version and
  counters;
- the store round-trips rows, resumes idempotently on `(condition, seed, episode)`, refuses
  to overwrite a result directory and refuses config drift;
- the memory gate refuses a run below 4.00 GB;
- the analysis CLI consumes a synthetic store and refuses to overwrite an existing output.

They do **not** show that a campaign can be assembled. There is still no production
component factory that builds the BANC-scale substrate, populations, adapter, stepper and
decoder from the frozen artifacts, and there is no campaign CLI driver in the repository
(`experiments/phase_8/` contains the harness, schema, store, manifest and
`analyse_phase_8.py`; `CampaignRunner` is a library class taking an injected
`episode_runner`). The condition modules accept injected components precisely because that
factory does not exist yet. This gap is the concrete remaining distance between "the
contracts are implemented" and "the campaign runs".

---

## 7. Finding: the feed-forward fixture cannot produce delay-matched coincidences

While connecting B, the first synthetic fixture produced no weight changes. The cause is
fixture dynamics, not an engine defect:

- each fixture edge is capped at 300 pA by the declared weight policy (12 edges → 3,600 pA);
- one neural step at the declared drive is 0.0025 mV/pA → ≈ 9 mV per delivered packet;
- the LIF threshold gap is 15 mV (−50 mV from −65 mV), so the postsynaptic cell cannot
  cross threshold on the injection step;
- the delay-matched convention only tags a coincidence when the postsynaptic spike and the
  delivery share the scheduled step, so a one-step-late spike never tags.

The timing was checked directly: a spike at step k is delivered by the delay line at step
k+2, and the engine pops exactly that step — there is no off-by-one. Raising the fixture
weight does not help because the policy caps it; the frozen cap, neuron parameters and
engine were left untouched.

B and D therefore use a recurrent **target-exchanged synthetic** fixture
(`synthetic_graph(32, 224, seed=5)` rewired with `rewire_target_exchange(seed=11,
swaps_per_edge=3.0)`). It carries the same structure/weight/sign contract, yields
non-zero coincidence tags in the test, and produces weight changes. The test asserts
`n_coincident_tags > 0` and `weights_changed is True`; it does not assert a scientific
effect. This is a property of a 32-node fixture under a 300 pA cap and says nothing about
BANC-scale dynamics.

---

## 8. Tests executed

All runs on Windows, Python 3.13.14, numpy 2.3.4, torch 2.10.0+cpu; no GPU, no dataset load,
no BANC graph, no campaign.

| command | result |
|---|---|
| `pytest tests/test_phase_8_conditions.py tests/test_phase_8_controls.py -q` | **36 passed** (6.78 s) — 22 conditions, 14 controls |
| `pytest tests/test_phase_8_live_plastic_stepper.py tests/test_phase_8_readout.py tests/test_phase_8_random_target_exchange.py tests/test_phase_8_conventional_learner.py tests/test_phase_8_campaign_skeleton.py tests/test_phase_8_analysis.py tests/test_phase_8_viability.py -q` | **161 passed** (5.77 s) |
| `pytest tests/test_evaluation.py -q` | **14 passed** (0.37 s), pre-existing and unmodified |

Total focused Phase 8 tests now **197** (36 new + 161 existing). The two new suites are
synthetic contract tests: 32-node graphs, controlled game environments, injected toy agents.
A passing suite means the declarations, refusals, evidence blocks and row validation behave
as specified; it does not mean an episode ran on the BANC substrate.

## 9. Resource preflight

| time | free physical memory | gate | result |
|---|---|---|---|
| start of report work | 3.22 GB | 4.00 GB | **below gate** |
| during the 161-test suite | 3.21 GB | 4.00 GB | below gate |
| after all suites | 3.33 GB | 4.00 GB | below gate |

The gate was not weakened. Because the reading stayed below 4.00 GB, no BANC-scale graph
construction, no randomisation certification, no pilot and no campaign was attempted, and no
memory-intensive suite was run. Only 32-node synthetic focused tests ran.

## 10. Status by work package

| package | status after this sprint | basis | remaining |
|---|---|---|---|
| G1 stepper | **complete as a mechanism** | stepper suite (9) + B/D condition tests | real-substrate run blocked by memory and approval |
| G2 readout | **complete as a mechanism** | readout suite (17) + F/Fβ/F-init tests | real-substrate run blocked |
| G3 random graph | **mechanism complete, BANC certification blocked** | 15 tests on synthetic graphs | BANC-scale construction (memory) |
| G4 conventional baseline | **complete as a mechanism** | 17 learner tests + E/E-full condition and seed-disjointness tests | real campaign run |
| G5 harness | **complete as a contract; campaign not assembled** | 60 harness tests + condition row validation | production component factory; memory; approval |
| G6 analysis | **complete as a mechanism** | 28 tests; synthetic store via CLI | real campaign store |
| G7 viability | **complete** | 15 tests; frozen Phase 7 artifact | none for the mechanism |
| conditions package | **implemented and tested synthetically** | 22 tests | real-substrate episodes |
| controls package | **implemented and tested synthetically** | 14 tests | real-substrate episodes |

"Complete as a mechanism" means executable code exists and focused tests exercise it with
synthetic inputs. It does not mean the package's real-scale acceptance criterion is met. The
requirements that remain unmet are itemised next.

## 11. What remains before a campaign

1. U1–U18 approval, in particular U1, U14 and U15.
2. A production component factory that builds the BANC-scale substrate, motor populations,
   adapter, stepper, decoder and readout from the frozen artifacts, with the E-family
   counterparts.
3. Reproduce the Phase 7 fingerprint (`cca811f3…b2fb`, 213 updates) through
   `conditions/a_fixed.py`, which requires a BANC-scale episode.
4. Pass the §9.3 memory preflight with margin; run BANC-scale randomisation certification
   (§10.4) and pilot 1 (§10.3).
5. Run pilot 2 (§10.8) to fix N; then the campaign (§10.10); then the analysis (§10.11).

None of items 2–5 was attempted.

## 12. Integrity

- No Git mutation: no stage, commit, push, reset, clean, stash or checkout. `git status` was
  read only. The two tracked diffs are `tests/conftest.py` (a Phase 8 row fixture added
  additively in earlier Phase 8 work) and `environment/subway_environment.py` (earlier Phase 7
  work); neither was touched in this sprint, and every file created this sprint is untracked.
- REV1, REV2 and REV3 documents, frozen Phase 6/7 artifacts, BANC data, connectome and
  weights were not modified. Weight changes occurred only in memory inside synthetic test
  steppers.
- No protocol parameter was tuned on an outcome. The only constant change is the arithmetic
  correction 113.05 → 112.87, which tightens the fallback and is documented in the REV4
  correction report.
- No experimental data were collected and no confirmatory statement is made.
