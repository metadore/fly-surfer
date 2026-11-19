# Phase 8 implementation status

**Date:** 2026-11-18 (updated after the Phase 8 readiness pass)
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines)
**REV3 (preserved byte-identical):** SHA-256 `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf` (1,848 lines)
**Correction report:** `reports/PHASE_8_REV3_TO_REV4_CORRECTION_REPORT.md`, SHA-256 `add143d127b0dfc1083a0c15c0cd0e4080c518c5d21ed61537db912ee042b24a`
**Sprint report:** `reports/PHASE_8_INTEGRATION_SPRINT_1.md`, SHA-256 `111afd306d471746a474243ba43b4c52093f9a17f068a15c38fe8b6773fec3c6`
**Random-graph report:** `reports/PHASE_8_BANC_RANDOM_GRAPH_IMPLEMENTATION.md`
**Campaign (seeds 1–16) report:** `reports/PHASE_8_BANC_RANDOM_GRAPH_CAMPAIGN.md`
**G5 report:** `reports/PHASE_8_G5_CAMPAIGN_RUNNER_IMPLEMENTATION.md`
**G4 training-artifact report:** `reports/PHASE_8_G4_TRAINING_ARTIFACT_IMPLEMENTATION.md`
**G4 remaining blockers:** `reports/PHASE_8_G4_REMAINING_BLOCKERS.md`
**Readiness report:** `reports/PHASE_8_FINAL_READINESS_REPORT.md`, SHA-256 `8f71d4e205d461db22afa1f94a5d22492fd5f77f30d4138e8afae5eb1d4648b9` — verdict **NOT READY**
**Decision register:** `reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md` — no item approved
**G3 resolution:** `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` — no option selected
**Integration audit:** `reports/PHASE_8_END_TO_END_INTEGRATION_AUDIT.md` — 352 tests, no defect found
**Execution commands:** `reports/PHASE_8_EXECUTION_COMMANDS.md` — non-executable
**Protocol approval status:** U1–U18 are all **PROPOSED — not approved** (REV4 §12). No campaign may start.

This revision adds the readiness pass of 2026-11-18. The work-package statuses for G1–G7 are
unchanged from the 2026-11-17 revision; what is new is a verified readiness assessment, five
readiness documents, and the finding that the executable stages which compose the tested
components are absent. One claim in the previous revision is corrected: the §5 table said only
campaign seed 1 was certified and seeds 2–16 were not built. That was stale even then — all
sixteen seeds are built and certified (§3), and §5 now agrees.

The earlier withdrawals remain in force: the `conditions/` and `controls/` packages exist; the
focused Phase 8 total is not 161 tests; the full Condition C graph set has been built and
independently certified at BANC scale; and G5 has a component factory and campaign driver.

The seed set was produced with **1.63 – 2.93 GB free physical memory**, below the REV4 §9.3 4 GB
gate, and §9.3 lists BANC-scale graph randomisation among the operations blocked below that gate.
The builds are certified and reproducible; they are **not protocol-compliant**, and
`campaign_seed_summary.json` records `compliance.status = "deviation_recorded"`. See §7.

---

## 1. What this report does and does not claim

A work package is marked **complete as a mechanism** only when executable code exists and
focused tests that call that code pass. A design document, an interface sketch, a config file
or the mere existence of a module is never counted as implementation.

A package is **not** marked complete in the protocol's own sense when its acceptance criterion
requires a run that has not happened — a real episode, pilot or campaign. Those parts are
recorded as blocked with the blocking condition named.

Sixteen BANC-scale computations have now been performed: the Condition C randomized graph for every
campaign seed 1–16 was constructed and certified against R1–R18 (§3, G3). No episode, training run
on a real substrate, pilot or campaign has been performed at any point in Phase 8. (Synthetic
training loops do execute inside `test_phase_8_training_engine.py` on tiny temporary fixtures; those
are loop-mechanics tests, not experimental runs.) Every other test described here uses
synthetic graphs (32 to 60,000 nodes), controlled game environments and toy agents. No parameter
was tuned on an outcome; every constant is the value declared in REV4 or `configs/phase_8/`.

---

## 2. Summary

| Package | Mechanism | Status | Reason |
|---|---|---|---|
| G1 incremental plastic stepper | implemented | **complete as a mechanism** | stepper (9 tests) plus B/D hooks, eta handling and evidence (condition tests) |
| G2 live trainable readout | implemented | **complete as a mechanism** | readout/Fβ/ablation (17 tests) plus F, Fβ, F-init conditions |
| G3 degree/sign-preserving random graph | implemented | **16/16 seeds certified; not complete** | generator + R1–R18 pipeline; seeds 1–16 built and certified; cross-seed validation and loader check pass; §9.3 deviation recorded and U18 unapproved |
| G4 conventional baseline | implemented | **complete as a mechanism** | learner (17 tests) plus E/E-full conditions and seed-disjointness enforcement |
| G5 campaign harness | implemented | **assembled and tested synthetically; campaign not authorised** | harness plus `campaign/` factory, dispatcher, certified-graph source, protocol validation, status and `run_campaign.py`; 52 new tests; campaign cannot start |
| G4 training artifacts and engine | implemented | **infrastructure and engine implemented; not complete** | schema, REV4 configuration validation, initialization, seeding, serialization, integrity, loader, factory compatibility, the F/Fβ and E/E-full training loops and resumable checkpoints; 70 new tests; no real-substrate training performed and no trained artifact exists |
| G6 analysis pipeline | implemented | **complete as a mechanism** | 28 tests; all §7 numbers reproduced from synthetic rows; no real store |
| G7 viability check | implemented | **complete** | 15 tests; read-only U1 gate against synthetic stores and the frozen Phase 7 artifact |
| `conditions/` package | implemented | **tested synthetically** | 10 modules, 2,200 lines, 22 tests |
| `controls/` package | implemented | **tested synthetically** | 8 modules, 1,236 lines, 14 tests |
| Pilot 1 stage (10.3) | **absent** | **not implemented** | no pilot plan, runner or result root |
| Pilot 2 stage (10.8) | **absent** | **not implemented** | same, plus pilot-seed graph decision |
| Training orchestration (10.5, 10.9) | engine, artifacts, checkpoints exist | **no runnable stage** | no CLI; authorisation gate always raises |
| Campaign composition root (10.10) | **absent** | **not implemented** | `start`/`resume` are refusing stubs |
| Phase 8 information analysis (10.11) | Phase 6 CLI only | **no adapter** | no Phase 8 command |
| Report / freeze (10.12) | **absent** | **manual only** | no generator |

Focused Phase 8 tests: **352 passing** (§8), of which 43 are training-artifact tests and 27 are
training-engine tests. Pre-existing `tests/test_evaluation.py`: 14 passing, unmodified.

**Readiness verdict (2026-11-18): NOT READY.** The mechanisms are largely complete, but four
classes of blocker remain: the unapproved protocol and null design; the unresolved §9.3
deviation and a machine below the memory gate; the absent executable stages listed above; and a
pre-observed floor risk for Condition A. See §9 and
`reports/PHASE_8_FINAL_READINESS_REPORT.md`.

---

## 3. Work-package detail

### G1 — Incremental plastic stepper (`plasticity/live_stepper.py`, 179 lines)

`LivePlasticStepper` is an additive subclass of `LiveBancStepper`. It reuses `PlasticityEngine`
and `WeightState`, so `dw = eta · modulation · trace` and the eta = 0 exact-zero contract are
inherited; `PlasticSimulator.run()` and its reset semantics are not on the closed-loop path.

This sprint added the condition side: `conditions/plasticity_hook.py` delivers exactly one
three-factor update per game update from the adapter's own recorded reward stream, and
`conditions/b_plastic.py` / `conditions/d_plastic.py` declare B and D at eta = 0.5. The hook
does not recompute, delay or reshape reward. `eta = 0` on the same hook executes the rule and
reports `rule_executed_zero_delta`; it does not skip work.

Verified by tests: step indexing and fingerprint stability (9 stepper tests); B and D run,
tag delay-matched coincidences, change weights and record `plasticity_path`; A refuses a plastic
stepper and holds weights fixed; reset preserves learned weights; eta = 0 is bit-identical to the
fixed path.

Frozen plasticity values are unchanged: eta = 0.5 (B/D), eta = 0.0 (A′/C′), τe = 20 ms, bounds
0.5–2.0×, 5 pA/update, delay-matched coincidence rule.

### G2 — Live trainable readout (`readout/`, 870 lines; `environment/motor_activity.py`, 150 lines)

`LinearReadout` (7/14 features) and `BiasOnlyReadout` (feature weights fixed at exactly 0.0,
four trainable biases, `state_independent = True`) exist with `assert_state_independent()`;
`readout/ablation.py` implements the §3.6.3 labels including the fifth uncovered case now
defined in REV4; `readout/controller.py` and `readout/trainer.py` provide the per-decision
controller and REINFORCE update.

This sprint added `conditions/f_readout.py`, `controls/f_beta.py` and `controls/f_init.py`.
F trains the readout only and is refused if given a state-independent model. Fβ is refused as
F's decision source and is checked to be constant over feature vectors. F-init shares F's
architecture and trains nothing. `neural_episode` records motor activity per decision for every
neural condition, including decisions where the decoder returns null, and records the readout
description and training update in the row. The A–D decoder path is unchanged: the loop still
uses `GameActionDecoder` whenever no `decision_source` is supplied.

### G3 — Degree- and sign-preserving random graph (`experiments/phase_8_random/`)

Target exchange (sources and weights fixed, targets swapped) preserves exact in/out degrees,
the weight multiset and per-source weight profiles (R9b); CSR invariants, duplicate and
self-edge checks are enforced. R1–R18 are computed and reported; R4–R14 (including R9b) and R17
gate. R14 is a plateau diagnostic, explicitly not a mixing proof.

**All sixteen campaign seeds are built and certified.** Every seed uses its own structure seed
`SeedSequence([20261116, N, 4])` and produces 172,433 nodes, 1,535,710 edges and 15,357,100 accepted
swaps. Across the set: R4 0.997830 – 0.997944, R5 0.0010289 – 0.0010863 (residual intersection
3,157 – 3,333 pairs), R6/R7 maximum change 0, R8 683,100 signed edges and 8,426,168 signed synapses
unchanged plus 852,610 unsigned, R9 sum 18,552,546 / min 5 / max 913 and R9b exact, R10/R11 zero,
R12 true, R13 0.000297 – 0.000353 over 130,709 active nodes, R14 3.00e-05 – 6.92e-05 (31 tail
samples), R17 identical digest on both builds of every seed. Runner time 115.2 – 127.4 s per seed
(1,903 s total), construction peak RSS 525.8 – 527.3 MB. Identities, per-seed measurements and the
certificates themselves are summarised in `experiments/results/phase_8_random/campaign_seed_summary.json`
and `reports/PHASE_8_BANC_RANDOM_GRAPH_CAMPAIGN.md`.

**Set-level checks pass:** 16 distinct structure seeds, graph digests, graph files and certificates;
shared invariants single-valued; provenance complete for every seed; seed 1 byte-identical to its
frozen identities; deterministic regeneration reproduces all 16 certified digests; the Condition C
loader accepts all 16 records and refuses a failed-gate record and a record with no certificate.

**Not complete.** U18 target exchange remains PROPOSED. The whole set was built below the REV4 §9.3
4 GB free-memory gate, so it is a recorded protocol deviation (§7), not a compliant run. No mixing
claim and no anatomical claim is made, and sixteen distinct seeds are not evidence of statistical
independence. The certified graphs are accepted by `load_structure` and enforced by
`_check_structure` in Condition C/D, but no episode has been executed.

### G4 — Matched conventional baseline (`evaluation/`, 1,285 lines across five modules)

`evaluation/observations.py` defines MATCHED (7) and FULL (14) features with one encoder;
`evaluation/conventional.py` provides the policy/value network and discounted returns;
`evaluation/rollout.py` runs on the five-tuple API. No Gymnasium or Stable-Baselines3
dependency was added.

This sprint added `conditions/e_conventional.py`, which runs E and E-full directly on the game
API and enforces training/evaluation seed disjointness as a hard error before the episode. Tests
confirm feature counts, encoder parity, training, no privileged inputs and seed refusal.

### G4 training artifacts — pipeline, engine and checkpoints (`experiments/phase_8/training/`, 3,965 lines)

The brief's "G4 — training artifact pipeline" is a different work item from the conventional
baseline above. It supplies the validated route by which trained F, Fβ and E artifacts would reach
`CampaignFactory.TrainingArtifacts`, and the loops that would produce them. Thirteen modules
(including the package `__init__`) implement:

- a 22-key artifact schema (`<root>/<condition>/seed_<campaign_seed>/` with `parameters.npz` and
  `manifest.json`) that records condition, campaign/training/init/master/environment seeds, model
  kind and architecture, the full validated training configuration and its SHA-256, the REV4
  identity, parameter names/shapes/dtypes, state and trainable digests, file SHA-256/bytes and
  provenance;
- configuration validation against REV4 (19 recorded checks: 20 readout episodes, 2,000 E gradient
  updates, 0.01 init scale, 3/7/14 features, 2×64 tanh, REINFORCE with value baseline, Adam,
  4 actions, per-condition `trains`, declared training-seed sufficiency) and the certified REV4
  hash; a mismatch raises, no value is defaulted;
- deterministic initialization through the existing `f_readout`, `f_beta` and `e_conventional`
  builders, with `init_seed` derived from the training seed and recorded separately from the
  campaign seed;
- an explicit caller-declared `(condition, campaign_seed) → training_seed` pairing (REV4 declares
  none), enforcing F/Fβ shared training runs and per-condition uniqueness;
- pickle-free serialization that refuses overwrite and refuses to write any trained state, plus
  reload verification (file hash, key/shape/dtype table, state digest, rebuilt model, trainable
  digest, condition compatibility — including Fβ's `assert_state_independent` and zero/saturated
  logit equality);
- a loader that rejects missing, duplicate, undeclared, synthetic or cross-condition artifacts,
  checks the F/Fβ pair, builds the factory provider, and `check_factory_compatibility`, which asks
  the real factory for every key and checks widths 3/7/14;
- the declared training loops (`engine.py`): F/Fβ run one training episode and exactly one
  REINFORCE update per episode for 20 episodes; E/E-full step the five-tuple game API and apply one
  `ConventionalAgent.finish_episode` update per episode until 2,000 updates. Both reuse the
  existing condition builders, re-assert their condition invariant after every update, stop only
  at the declared budget, and never train B, D, F-init, A′ or C′;
- resumable checkpoints (`checkpoint.py`): `checkpoint.json` plus `parameters.npz`, origin
  `synthetic_fixture`, stage `training_checkpoint`, verified by file hash, shape/dtype table and
  state digest, rebuilt and re-checked on restore. Checkpoints are not artifacts and are never
  discovered by the artifact loader. RNG and optimizer moments are not stored, so resume is
  parameter-continuous, not bit-identical; every payload records that limitation;
- the unresolved-design gate: `design.n_seeds_selected` is null, so artifact generation, training
  planning and campaign preparation all refuse before reading the artifact root;
- unconditional refusal of training: `assert_training_authorized` always raises,
  `origin="trained"`/`stage="trained"` cannot be written, `plan.run_training` always raises, and a
  protocol-mode engine context raises inside its constructor through the same gate.

Verified by 70 synthetic tests (43 artifact, 27 engine), which execute the loops only on tiny
temporary fixtures. **No real-substrate training was performed, no trained artifact exists, and
`experiments/results/phase_8/training/` was never created.** G4 training artifacts is not complete
as a protocol work package: execution remains blocked by the unapproved protocol, the null design,
four undeclared inputs (campaign↔training pairing, training-episode environment seeds, checkpoint
cadence, bit-exact RNG/optimizer state) and the recorded G3 deviation.

### G5 — Campaign harness and runner assembly (`experiments/phase_8/`)

`experiments/phase_8/` contains the harness (seed derivation, frozen config loader, strict
versioned schema, append-only JSONL store with idempotent resume, manifests with environment
capture and input hashing, registry, and the runner with the §9.3 memory gate), the
`conditions/`/`controls/` contracts, and the G5 assembly package `campaign/`:

- `campaign/factory.py` (662 lines) builds one episode's BANC-scale components from the frozen
  artifacts — substrate, populations, adapter, stepper, decoder, readout or conventional agent.
  It never trains; F, Fβ and E refuse without caller-supplied `TrainingArtifacts`. It hashes the
  seven frozen inputs and rejects an environment that disagrees with the config.
- `campaign/dispatcher.py` (377 lines) is the `CampaignRunner` episode runner. It routes the twelve
  arms to their existing implementations, re-derives A/C for A′/C′ with the same paired environment
  seed, merges equivalence evidence into the row, records staged failures and never invents a row.
- `campaign/graphs.py` (283 lines) is the only route to a structure for C, D and C′: certified
  source, full certificate verification, target-exchange alignment re-check, no biological
  fallback.
- `campaign/protocol.py` (554 lines) validates the configuration against REV4's declared constants
  (69 checks) and always refuses authorisation.
- `campaign/status.py` (167 lines) reports run completeness, missing keys, drift and torn stores
  read-only.
- `run_campaign.py` (396 lines) exposes `check`, `seeds`, `graphs`, `status`, `start` and `resume`.
  `start` and `resume` always refuse with exit 2 and zero episodes/rows.

`runner.py` now passes `seed_plan=None` for the floor, which has no neural stream; this was the
only harness change needed. `conditions/base.py` re-verifies a structure record's certificate when
one is present.

Verified by 52 new synthetic tests plus the earlier 60 harness tests: REV4 conformance 69/69,
registry order and semantics, per-arm component builds, mirror wiring, floor and conventional
routes, failure staging and logging, `EquivalenceMismatch` preservation, certificate refusals,
alignment, 12-row integration, stop-on-failure, resume (3 then 21 of 24), status completeness and
drift, and CLI refusal. No game episode was executed.

**Assembled, not run.** G5 is complete as a mechanism, not in the protocol's operational sense.
`check` reports 16/16 certified graphs, 69/69 conformance, `executable: false`, and a live memory
gate of 2.529 GiB of 4.0 GiB at the 2026-11-18 readiness measurement (2.711 GiB by direct
`psutil` reading). `start`/`resume` return exit 2 with `authorized: false`. The
authorisation refusal and the unresolved G3 deviation are what keep this from being a campaign.

### G6 — Analysis pipeline (`experiments/phase_8/analysis.py`, 1,773 lines; `analyse_phase_8.py`, 179 lines)

Exact sign-flip over the full 2^N enumeration, exact sign test, Holm at the declared family
size, paired bootstrap, effect sizes, missing-pair accounting, identity-first invalidation,
predeclared fallback withholding, error-row sensitivity, floor decomposition, F/Fβ/A
decomposition and E1–E5. The CLI refuses to overwrite and writes no hand-entered numbers.

Verified by 28 tests including the §7.5 enumeration counts, brute-force cross-check at n = 6,
refusal at n = 19, the §7.4 MDE constants with 112.87 now consistent, invalidation propagation,
E4 0/0 as undefined, and CLI overwrite refusal with the store byte-identical.

**Not verified on real data:** there is no campaign store. The §10.11 acceptance criterion is
not satisfied.

### G7 — Viability check (`evaluation/viability.py`, 521 lines)

Read-only U1 report implementing U1-A … U1-E, with C and D reported and never gated, the floor
measured by replay, per-arm gate states, missing-floor blocking, and a read-only Phase 7 summary
that does not reinterpret the frozen artifact. Verified by 15 tests.

---

## 4. Conditions and controls

| arm | module | declaration |
|---|---|---|
| A | `conditions/a_fixed.py` | biological substrate, fixed weights, fixed decoder |
| B | `conditions/b_plastic.py` | biological substrate, eta = 0.5 through the live stepper |
| C | `conditions/c_random.py` | target-exchange substrate, fixed weights, structural certificate required |
| D | `conditions/d_plastic.py` | target-exchanged substrate, eta = 0.5 |
| E / E-full | `conditions/e_conventional.py` | REINFORCE on the five-tuple API, 7/14 features |
| F | `conditions/f_readout.py` | fixed substrate, motor-only trainable readout |
| A′ | `controls/a_prime.py` | A through the plastic path at exactly eta = 0.0 |
| C′ | `controls/c_prime.py` | C through the plastic path on the same per-seed graph |
| Fβ | `controls/f_beta.py` | bias-only, provably state-independent |
| F-init | `controls/f_init.py` | F architecture at seeded initial parameters |
| floor | `controls/floor.py` | constant `NO_ACTION`, no substrate, not a neural arm |

A′/C′ use the zero hook that must execute; the comparison is P1–P19 with **no tolerance**, and
the first mismatch raises `EquivalenceMismatch` with the hard-stop payload. A′ invalidates B;
C′ invalidates D. C′ refuses a different graph. Tests tamper with a record and a reward to show
the stop occurs at P5 with P1–P4 already checked.

---

## 5. Condition wiring against REV4 §10

| §10 item | artifact | status |
|---|---|---|
| 10.1 campaign skeleton (G5) | `experiments/phase_8/` | implemented and tested |
| 10.2 condition A | `conditions/a_fixed.py` | **implemented and tested synthetically**; Phase 7 fingerprint reproduction at 213 updates not attempted (needs BANC substrate) |
| 10.3 pilot 1 capacity | — | **not started** — blocked by memory |
| 10.4 condition C + randomisation | `experiments/phase_8_random/`, `conditions/c_random.py` | mechanism, runner and certification implemented; **all 16 campaign seeds built and certified at BANC scale**; §9.3 deviation recorded, so not compliant |
| 10.5 condition F and Fβ | `conditions/f_readout.py`, `controls/f_beta.py`, `training/engine.py` | conditions implemented and tested synthetically; the declared readout training loop exists but no real-substrate episode or update was run |
| 10.6 A′ and C′ | `controls/a_prime.py`, `controls/c_prime.py`, `controls/zero_hook.py` | implemented and tested synthetically |
| 10.7 conditions B and D | `conditions/b_plastic.py`, `conditions/d_plastic.py` | implemented and tested synthetically |
| 10.8 pilot 2 | — | **not started** — needs real episodes |
| 10.9 condition E | `conditions/e_conventional.py`, `training/engine.py` | condition implemented and tested synthetically, including seed disjointness; the declared 2,000-update loop exists but no real game episode or update was run |
| 10.10 campaign | `campaign/`, `run_campaign.py` | **assembled and tested synthetically; not authorised and not run** — factory, dispatcher, certificate enforcement and CLI exist; `start`/`resume` always refuse |
| 10.11 analysis | `analyse_phase_8.py` | mechanism implemented; no real store to analyse |
| 10.12 base rate / floor | `controls/floor.py` | floor implemented; base-rate measurement not run |
| 10.13 viability | `evaluation/viability.py` | implemented and tested |

---

## 6. REV3 ambiguities: all seven resolved in REV4

| # | ambiguity | resolution in REV4 |
|---|---|---|
| 1 | R13 denominator for isolated nodes | gate over nodes with a non-empty out-neighbourhood in at least one graph; literal all-node value reported, not gated |
| 2 | §6.3 seed formula vs §6.2/R18 | four per-stream entropy vectors; environment and structure omit the condition; structure code 4 |
| 3 | uncovered §3.6.3 ablation cell | fifth row defined; label stays `undefined` with a distinct audit reason; E4 unchanged |
| 4 | 113.05 vs 112.87 | formula governs; bound is 112.87 (tightened by 0.16 %); config and test updated |
| 5 | U1 "three" vs five gate cases | five cases; prose corrected; rows unchanged |
| 6 | numeric "at floor" | paired capped-score mean difference from the measured floor ≤ 0; descriptive only, never a stopping rule |
| 7 | error before the first update | sensitivity contribution `min(observed_updates, 900)` = 0.0; counted and reported separately |

No scientific parameter changed. The item-by-item evidence is in the correction report.

---

## 7. Resource gate

| Measure | Value |
|---|---|
| Total physical memory | 16.47 GB (reported by `psutil`) |
| Free physical memory during the seed 1–16 builds | **1.63 – 2.93 GB** at preflight; low-water marks 1.628 GB (construction) and 1.936 GB (runner) |
| Gate (REV4 §9.3, which names BANC-scale graph randomisation among the blocked operations) | 4.00 GB |
| Gate result | **below the gate at every seed — deviation recorded** |
| Construction-specific preflight (0.75 GB floor) | `allowed: true` for all 16 seeds |

The gate was not weakened, redefined or reported as met. `campaign_seed_summary.json` carries
`compliance = {status: "deviation_recorded", gate_weakened: false, min_observed_free_gb: 1.628,
max_observed_free_gb: 2.747}`. The builds are real, certified and reproducible, and no build
exhausted memory (peak RSS 527 MB) — but the rule as written was not satisfied, and the honest
reading is that this work needs either an approved protocol amendment covering construction-time
memory or a rerun on a machine with ≥ 4 GB free.

Work still blocked by resources regardless of code state:

- pilot 1 (§10.3), pilot 2 (§10.8), any condition episode or training run (§10.2, 10.5–10.7,
  10.9), and the campaign (§10.10);
- memory-intensive test suites.

None of the remaining work is authorised yet either: U1–U18 are proposed, and implementation
gates have not been demonstrated for a campaign at BANC scale.

---

## 8. Tests executed

```
python -m pytest tests/test_phase_8_training_artifacts.py \
  tests/test_phase_8_training_engine.py tests/test_phase_8_readout.py \
  tests/test_phase_8_conventional_learner.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py -q
    -> 252 passed (13.48 s)

python -m pytest tests -q -k "phase_8"
    -> 352 passed, 1079 deselected (25.74 s)

python -m pytest tests/test_phase_8_live_plastic_stepper.py \
  tests/test_phase_8_random_target_exchange.py tests/test_phase_8_random_certification.py \
  tests/test_phase_8_random_campaign.py tests/test_phase_8_analysis.py \
  tests/test_phase_8_viability.py -q
    -> 100 passed

python -m pytest tests/test_evaluation.py tests/test_motor_populations.py \
  tests/test_phase_7_environment.py -q
    -> 49 passed (7.52 s)   # regression; test_evaluation.py is pre-existing and unmodified

python -m pytest tests -q
    -> 1422 passed, 3 skipped, 6 failed
```

Readiness pass (2026-11-18), 14 focused suites:

```
python -m pytest tests/test_phase_8_analysis.py tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py tests/test_phase_8_conventional_learner.py \
  tests/test_phase_8_live_plastic_stepper.py tests/test_phase_8_readout.py \
  tests/test_phase_8_training_artifacts.py tests/test_phase_8_training_engine.py \
  tests/test_phase_8_viability.py tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py tests/test_phase_8_random_campaign.py -q
    -> 352 passed (24.36 s)
```

The read-only `python -m experiments.phase_8.run_campaign check` reported 69/69 conformance,
16/16 certified graphs, `design_resolved: false`, `executable: false`, and a failed memory gate.

The six full-suite failures are pre-existing and outside Phase 8: the `README.md` protected-hash
check in `test_integration_3b_3c.py`, the amended P3-3C.5 record in
`test_p3_3c5_lane_encoding.py`, and the Phase 4 motor-substrate smoke verdict
("SMOKE INVALID") in `test_causal_control.py` and `test_feature_ablation.py`. None imports the
training package.

Windows, Python 3.13.14, numpy 2.3.4, torch 2.10.0+cpu. No GPU work, no real game episode, no
real-substrate training. The BANC random-graph work described in §3 used the real graph but no
model, dataset or episode; the training-engine tests use tiny temporary fixtures only.

| Suite | Package | Tests |
|---|---|---|
| `test_phase_8_conditions.py` | conditions, G1/G2/G4 wiring | 22 |
| `test_phase_8_controls.py` | controls, A′/C′/Fβ/F-init | 14 |
| `test_phase_8_live_plastic_stepper.py` | G1 | 9 |
| `test_phase_8_readout.py` | G2 | 17 |
| `test_phase_8_random_target_exchange.py` | G3 exchange | 15 |
| `test_phase_8_random_certification.py` | G3 certification | 22 |
| `test_phase_8_random_campaign.py` | G3 seed set | 11 |
| `test_phase_8_conventional_learner.py` | G4 baseline | 17 |
| `test_phase_8_training_artifacts.py` | G4 training artifacts | 43 |
| `test_phase_8_training_engine.py` | G4 training engine, checkpoints | 27 |
| `test_phase_8_campaign_skeleton.py` | G5 harness | 60 |
| `test_phase_8_campaign_runner.py` | G5 assembly | 52 |
| `test_phase_8_analysis.py` | G6 | 28 |
| `test_phase_8_viability.py` | G7 | 15 |
| **Total** | | **352** |

These tests establish that the declarations, refusals, evidence blocks, row validation,
analysis arithmetic, certificate hand-off, component routing, resume and CLI refusal behave as
specified on synthetic inputs. They do not establish that a Phase 8 episode runs on the BANC
substrate — no episode was ever executed. The separate BANC runs establish that all sixteen
Condition C graphs are certified and reproduce byte-identically; they say nothing about
confirmatory numbers, and — as §7 records — the runs themselves are outside the protocol's
memory gate.

---

## 9. Readiness pass (2026-11-18) and verdict

Five reports were produced by a readiness pass that audited the implementation against REV4,
built the decision register, verified G3 integrity, exercised the campaign interfaces with
synthetic fixtures and prepared the execution commands. The pass ran no episode, training job,
pilot or campaign and changed no scientific parameter.

| Report | Finding |
|---|---|
| `PHASE_8_FINAL_READINESS_REPORT.md` | **verdict NOT READY** |
| `PHASE_8_PROTOCOL_DECISION_REGISTER.md` | U1–U18 and B3–B6: none approved; `n_seeds_selected` remains null; N = 16 default documented but not applied |
| `PHASE_8_G3_DEVIATION_RESOLUTION.md` | graphs and certificates intact; compliance not met; machine 2.529–2.711 GiB below the 4.0 GiB gate; no option selected |
| `PHASE_8_END_TO_END_INTEGRATION_AUDIT.md` | 352 tests pass; 12/12 arms route; no implementation defect found at the audited boundaries; no uninterrupted campaign was run |
| `PHASE_8_EXECUTION_COMMANDS.md` | pilot 1/2, training CLI, composition root, Phase 8 information adapter and report generator are absent or refusing stubs |

The pass found that the tested components are **not composed into executable stages**. The
missing stages are pilot 1 (10.3), pilot 2 (10.8), training orchestration (10.5/10.9), the
production composition root (10.10), the Phase 8 information adapter (10.11) and the report
generator (10.12). `run_campaign start` and `resume` remain refusing stubs. Recording approvals
would not make a campaign runnable.

It also recorded a pre-observed scientific risk that is independent of the protocol: the Phase 7
fixed-weight loop produced 213/213 `NO_ACTION`, zero motor spikes and propagation stopping at
the first hop (best −56.926 mV, 6.926 mV below threshold). That is prior evidence about one model
configuration, not Phase 8 data, but it means Condition A may be at the platform floor. Pilot 1
is the intended instrument and must precede any campaign.

Verdict: **NOT READY** — not "ready for user approval" and not "ready for authorised pilot". The
blockers are the unapproved protocol and null design, the unresolved G3 deviation, the failed
memory gate, the absent execution stages, and the floor risk. The ordered route to a different
verdict is in `PHASE_8_FINAL_READINESS_REPORT.md` §11.

---

## 10. What remains before a campaign can be authorised

1. Decide U1–U18; U1, U14 and U15 change what the campaign computes. U18 decides whether the
   target-exchange graphs already built remain valid.
2. Supply trained artifacts for F, Fβ and E. The artifact schema, REV4 configuration validation,
   initialization, serialization, integrity checks, loader and factory compatibility now exist
   (`experiments/phase_8/training/`), and so do the declared training loops and checkpoints. The
   loops are unreachable by construction while REV4 is unapproved and `design.n_seeds_selected` is
   null (U7 unresolved), and they require caller-declared inputs that REV4 does not supply
   (campaign↔training pairing, training-episode environment seeds, checkpoint cadence). The factory
   still refuses to evaluate an untrained model.
3. Reproduce the Phase 7 fingerprint (`cca811f3…b2fb`, 213 updates) from
   `conditions/a_fixed.py`.
4. Settle the §9.3 deviation for the Condition C graphs: approve an amendment covering
   construction-time memory, or rebuild the set with ≥ 4 GB free. All sixteen graphs exist and are
   certified, so this is a compliance decision, not a build task. Pilot 1 (§10.3) stays blocked by
   the 4.00 GB campaign gate regardless.
5. Run pilot 2 (§10.8) to fix N, then the campaign (§10.10), then the analysis (§10.11).
6. Execute one authorised end-to-end episode through `CampaignDispatcher` on the BANC substrate,
   to replace stub verification with real integration evidence.

Step 4's build half is done; its compliance half is open, and it is the user's call. Step 2's
execution half (an authorised run), steps 3, 5 and 6 have not been started.

---

## 11. Integrity

- No Git state was changed: no staging, commit, push, reset, clean, stash or checkout.
  `git status` was read only.
- The tracked diffs visible in `git status` are `experiments/phase_8_random/target_exchange.py`,
  `experiments/phase_8_random/__init__.py`, `experiments/phase_8/conditions/base.py` (earlier
  certification task, plus the G5 certificate re-check), `experiments/phase_8/runner.py` (floor
  seed plan) and this report. Files created since are untracked: `certification.py`,
  `certify_banc.py`, `campaign_summary.py`, `tests/test_phase_8_random_certification.py`,
  `tests/test_phase_8_random_campaign.py`, `datasets/processed/banc_v888_random/` (seed 1–16),
  `experiments/results/phase_8_random/`, the `experiments/phase_8/campaign/` package,
  `experiments/phase_8/run_campaign.py`, `tests/test_phase_8_campaign_runner.py`,
  `reports/PHASE_8_G5_CAMPAIGN_RUNNER_IMPLEMENTATION.md`, the
  `experiments/phase_8/training/` package, `tests/test_phase_8_training_artifacts.py`,
  `tests/test_phase_8_training_engine.py`,
  `reports/PHASE_8_G4_TRAINING_ARTIFACT_IMPLEMENTATION.md` and
  `reports/PHASE_8_G4_REMAINING_BLOCKERS.md`.
- The training tasks modified no existing source file outside
  `experiments/phase_8/training/__init__.py` and `experiments/phase_8/training/plan.py`, and wrote
  nothing under `experiments/results/phase_8/training/`, which does not exist. The engine's
  synthetic checkpoints live only in pytest temporary directories.
- REV1, REV2, REV3, the independent audit, frozen Phase 4–7 artifacts, BANC data, connectome
  files and weights were not modified. REV3's SHA-256 is unchanged. The original BANC graph,
  node table and policy config were opened read-only, and their hashes still match the values in
  §3.
- Weight changes occurred only in memory inside synthetic test steppers. The randomized graph
  copies every edge weight unchanged; no BANC weight was altered.
- No experimental data were collected; no episode, pilot or campaign was run; no confirmatory
  claim is made.
- The readiness pass (2026-11-18) performed only read-only inspection: file reads, SHA-256
  verification of the 16 graph/certificate pairs, a memory measurement, the read-only campaign
  CLI, and the synthetic test suites. It wrote the five readiness reports and this status update;
  it did not write under `experiments/results/`, `datasets/` or any certified namespace, and it
  performed no Git operation. The new reports are untracked:
  `reports/PHASE_8_FINAL_READINESS_REPORT.md`, `reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md`,
  `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md`,
  `reports/PHASE_8_END_TO_END_INTEGRATION_AUDIT.md` and
  `reports/PHASE_8_EXECUTION_COMMANDS.md`.
