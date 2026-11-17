# Phase 8 implementation status

**Date:** 2026-11-17 (updated after Integration Sprint 1)
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines)
**REV3 (preserved byte-identical):** SHA-256 `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf` (1,848 lines)
**Correction report:** `reports/PHASE_8_REV3_TO_REV4_CORRECTION_REPORT.md`, SHA-256 `add143d127b0dfc1083a0c15c0cd0e4080c518c5d21ed61537db912ee042b24a`
**Sprint report:** `reports/PHASE_8_INTEGRATION_SPRINT_1.md`, SHA-256 `111afd306d471746a474243ba43b4c52093f9a17f068a15c38fe8b6773fec3c6`
**Protocol approval status:** U1–U18 are all **PROPOSED — not approved** (REV4 §12). No campaign may start.

This revision replaces the pre-sprint status of the same date. Two claims in that version are
now obsolete and are withdrawn: that the `conditions/` and `controls/` packages do not exist,
and that the focused Phase 8 total is 161 tests.

---

## 1. What this report does and does not claim

A work package is marked **complete as a mechanism** only when executable code exists and
focused tests that call that code pass. A design document, an interface sketch, a config file
or the mere existence of a module is never counted as implementation.

A package is **not** marked complete in the protocol's own sense when its acceptance criterion
requires a run that has not happened — BANC-scale graph construction, a real episode, pilot or
campaign. Those parts are recorded as blocked with the blocking condition named.

No experiment, training run or BANC-scale computation has been performed at any point in Phase 8
implementation. Every test described here uses synthetic 32-node graphs, controlled game
environments and toy agents. No parameter was tuned on an outcome; every constant is the value
declared in REV4 or `configs/phase_8/`.

---

## 2. Summary

| Package | Mechanism | Status | Reason |
|---|---|---|---|
| G1 incremental plastic stepper | implemented | **complete as a mechanism** | stepper (9 tests) plus B/D hooks, eta handling and evidence (condition tests) |
| G2 live trainable readout | implemented | **complete as a mechanism** | readout/Fβ/ablation (17 tests) plus F, Fβ, F-init conditions |
| G3 degree/sign-preserving random graph | implemented | **blocked at BANC scale** | generator + R1–R18 reporter tested on synthetic graphs; no BANC-scale graph built |
| G4 conventional baseline | implemented | **complete as a mechanism** | learner (17 tests) plus E/E-full conditions and seed-disjointness enforcement |
| G5 campaign harness | implemented | **contract complete; campaign not assembled** | harness (60 tests) + validated condition rows; no production component factory, no campaign run |
| G6 analysis pipeline | implemented | **complete as a mechanism** | 28 tests; all §7 numbers reproduced from synthetic rows; no real store |
| G7 viability check | implemented | **complete** | 15 tests; read-only U1 gate against synthetic stores and the frozen Phase 7 artifact |
| `conditions/` package | implemented | **tested synthetically** | 10 modules, 2,200 lines, 22 tests |
| `controls/` package | implemented | **tested synthetically** | 8 modules, 1,236 lines, 14 tests |

Focused Phase 8 tests: **197 passing** (§8). Pre-existing `tests/test_evaluation.py`: 14 passing,
unmodified.

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

### G3 — Degree- and sign-preserving random graph (`experiments/phase_8_random/`, 633 lines)

Target exchange (sources and weights fixed, targets swapped) preserves exact in/out degrees,
the weight multiset and per-source weight profiles (R9b); CSR invariants, duplicate and
self-edge checks are enforced, and R1–R18 are computed and reported with R4–R10 plus R9b
gating and R14 as a diagnostic.

Verified on synthetic graphs by 15 tests, including deterministic rebuild (R17) and the shared
graph identity (R18).

**Blocked at BANC scale.** The §10.4 criterion ("all R1–R18 pass … ≤ 15 min per graph at BANC
scale") cannot be evaluated because no BANC-scale graph was constructed; the machine is below
the memory gate and the protocol marks that construction as blocked below it.

### G4 — Matched conventional baseline (`evaluation/`, 1,285 lines across five modules)

`evaluation/observations.py` defines MATCHED (7) and FULL (14) features with one encoder;
`evaluation/conventional.py` provides the policy/value network and discounted returns;
`evaluation/rollout.py` runs on the five-tuple API. No Gymnasium or Stable-Baselines3
dependency was added.

This sprint added `conditions/e_conventional.py`, which runs E and E-full directly on the game
API and enforces training/evaluation seed disjointness as a hard error before the episode. Tests
confirm feature counts, encoder parity, training, no privileged inputs and seed refusal.

### G5 — Campaign harness (`experiments/phase_8/`)

`experiments/phase_8/` now contains **8,055 lines**: ten top-level modules (4,619 lines), the
`conditions/` subpackage (2,200) and the `controls/` subpackage (1,236), plus
`configs/phase_8/` (283 lines across three YAMLs).

Implemented: seed derivation, frozen config loader, strict versioned schema, append-only JSONL
store with idempotent resume, manifests with environment capture and input hashing, registry,
the runner with the §9.3 memory gate, and the condition/control contracts above.

Verified by 60 harness tests plus the condition row tests: malformed rows rejected, 1-update
row round-trip, resume idempotence on `(condition, seed, episode)`, refusal to overwrite,
manifest round-trip, seed-plan properties, memory-gate refusal, recorded-N enforcement,
config-drift refusal, and every condition row passing `validate_episode_row`.

**Not assembled. Not run.** There is no production component factory that builds the BANC-scale
substrate, populations, adapter, stepper and decoder from the frozen artifacts, and there is no
campaign CLI driver in the repository — `CampaignRunner` is a library class taking an injected
`episode_runner`, and `experiments/phase_8/` contains `analyse_phase_8.py` but no
`run_campaign.py`. The harness has never executed a real episode.

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
| 10.4 condition C + randomisation | `experiments/phase_8_random/`, `conditions/c_random.py` | mechanism and module implemented; **BANC-scale certification blocked by memory** |
| 10.5 condition F and Fβ | `conditions/f_readout.py`, `controls/f_beta.py` | implemented and tested synthetically |
| 10.6 A′ and C′ | `controls/a_prime.py`, `controls/c_prime.py`, `controls/zero_hook.py` | implemented and tested synthetically |
| 10.7 conditions B and D | `conditions/b_plastic.py`, `conditions/d_plastic.py` | implemented and tested synthetically |
| 10.8 pilot 2 | — | **not started** — needs real episodes |
| 10.9 condition E | `conditions/e_conventional.py` | implemented and tested synthetically, including seed disjointness |
| 10.10 campaign | `CampaignRunner` | **not assembled and not run** — no component factory, memory gate, protocol unapproved |
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
| Free physical memory, 2026-11-17 at report time | **3.33 GB** (range during this sprint 2.91–3.33 GB) |
| Gate (REV4 §9.3) | 4.00 GB |
| Gate result | **below the gate** |

The gate was not weakened. Work still blocked by resources regardless of code state:

- BANC-scale random-graph construction and R1–R18 certification (§10.4);
- pilot 1 (§10.3), pilot 2 (§10.8), any condition episode or training run (§10.2, 10.5–10.7,
  10.9), and the campaign (§10.10);
- memory-intensive test suites.

None of that work is authorised yet either: U1–U18 are proposed, and implementation gates have
not been demonstrated at BANC scale.

---

## 8. Tests executed

```
python -m pytest tests/test_phase_8_conditions.py tests/test_phase_8_controls.py -q
    -> 36 passed (6.78 s)

python -m pytest tests/test_phase_8_live_plastic_stepper.py \
  tests/test_phase_8_readout.py \
  tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_conventional_learner.py \
  tests/test_phase_8_campaign_skeleton.py \
  tests/test_phase_8_analysis.py \
  tests/test_phase_8_viability.py -q
    -> 161 passed (5.77 s)

python -m pytest tests/test_evaluation.py -q
    -> 14 passed (0.37 s), pre-existing, unmodified
```

Windows, Python 3.13.14, numpy 2.3.4, torch 2.10.0+cpu. No GPU work, no dataset load, no BANC
graph, no training campaign.

| Suite | Package | Tests |
|---|---|---|
| `test_phase_8_conditions.py` | conditions, G1/G2/G4 wiring | 22 |
| `test_phase_8_controls.py` | controls, A′/C′/Fβ/F-init | 14 |
| `test_phase_8_live_plastic_stepper.py` | G1 | 9 |
| `test_phase_8_readout.py` | G2 | 17 |
| `test_phase_8_random_target_exchange.py` | G3 | 15 |
| `test_phase_8_conventional_learner.py` | G4 | 17 |
| `test_phase_8_campaign_skeleton.py` | G5 | 60 |
| `test_phase_8_analysis.py` | G6 | 28 |
| `test_phase_8_viability.py` | G7 | 15 |
| **Total** | | **197** |

These tests establish that the declarations, refusals, evidence blocks, row validation and
analysis arithmetic behave as specified on synthetic inputs. They do not establish that a Phase 8
episode runs on the BANC substrate, that BANC-scale randomisation completes, or that any
confirmatory number is correct on real data.

---

## 9. What remains before a campaign can be authorised

1. Decide U1–U18; U1, U14 and U15 change what the campaign computes.
2. Build the production component factory from the frozen artifacts (BANC substrate, motor
   populations, adapter, stepper, decoder, readout) and connect `CampaignRunner` with a
   campaign driver.
3. Reproduce the Phase 7 fingerprint (`cca811f3…b2fb`, 213 updates) from
   `conditions/a_fixed.py`.
4. Pass the §9.3 memory preflight with margin, then run BANC-scale randomisation certification
   (§10.4) and pilot 1 (§10.3).
5. Run pilot 2 (§10.8) to fix N, then the campaign (§10.10), then the analysis (§10.11).

None of steps 2–5 was attempted.

---

## 10. Integrity

- No Git state was changed: no staging, commit, push, reset, clean, stash or checkout.
  `git status` was read only.
- The two tracked diffs visible in `git status` are `tests/conftest.py` (a Phase 8 row fixture
  added additively in earlier Phase 8 work) and `environment/subway_environment.py` (earlier
  Phase 7 work). Neither was touched in this sprint; every file created this sprint is untracked.
- REV1, REV2, REV3, the independent audit, frozen Phase 4–7 artifacts, BANC data, connectome
  files and weights were not modified. REV3's SHA-256 is unchanged.
- Weight changes occurred only in memory inside synthetic test steppers. No BANC graph was
  randomised.
- No experimental data were collected; no confirmatory claim is made.
