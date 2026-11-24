# Phase 8 — Pilot 2-C Execution Report

**Stage:** `pilot2c`, REV4 step 10.8 as amended by D3
**Stage purpose:** `floor_and_identity_certification`
**Run id:** `pilot2c_d3_20261123`
**Run directory:** `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123`
**Executed:** 2026-11-23, first row `03:37:44Z`, last row `04:35:36Z`; total episode wall time 3,458.8 s
**Owner execution authorization:** explicit owner message of 2026-11-23, authorising exactly this grid and nothing else
**Evidence kind:** `pilot` (not campaign evidence; never merged into the campaign dataset)

This report records the executed grid and its certification, states the eight
P2C claims with their evidence, states which quantities were *not* evaluated and
why, and separates observation from conclusion. A certification PASS is a
statement about the experiment's machinery. It is **not** evidence of biological
learning, behavioural competence or motor decoding, and it is not treated as such
below.

---

## 1. Preflight and authorization verification

### 1.1 Authorization chain

| Gate | State at execution | Evidence |
|---|---|---|
| REV4 protocol | present, SHA-256 `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` | `records.D1` in the execution preflight |
| D1 — protocol approval | APPROVED, bound to the REV4 hash; does not itself authorise execution | `reports/phase_8_owner_approvals/D1.json` |
| D2 — G3 applicability (Pilot 1 only) | valid, `accepts_g3_deviation: false`, `weakens_graph_certification: false` | `reports/phase_8_owner_approvals/D2.json` |
| D3 — Pilot 2-C amendment | applicable, bound to REV4, amendment matches disk, no failures | `reports/phase_8_owner_approvals/D3.json`; `docs/PHASE_8_PILOT2C_AMENDMENT.md` (`832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad`) |
| D4 — training contracts B3–B6 | applicable, no failures | `reports/phase_8_owner_approvals/D4.json` |
| D5 — six pilot training artifacts | applicable, valid, D6 valid, all six artifacts bound | `reports/phase_8_owner_approvals/D5.json`, `D6.json` |
| D6 — B7 has no subject in this plan | present, valid, bound | `reports/phase_8_owner_approvals/D6.json` |
| Stage authorization | `authorized: true`, `blockers: []`, D3 exemption applied for exactly this grid | execution preflight `authorization` |
| Global training gate | **still refuses** (`training_authorization_status()["training_authorized"] is False`) | preflight `training_authorization.global_training_gate_authorized: false` |
| Campaign gate | **still refuses** | `assert_campaign_authorized` unchanged |

The B3 pairing used is the D5 derivation with global digest
`bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980`:

| Condition | Evaluation seed | Training seed | Pool index |
|---|---|---|---|
| F | 9001 | 1008 | 7 |
| F | 9002 | 1014 | 13 |
| F | 9003 | 1005 | 4 |
| F_beta | 9001 | 1008 | 7 |
| F_beta | 9002 | 1014 | 13 |
| F_beta | 9003 | 1005 | 4 |

### 1.2 Preflight result

`reports/PHASE_8_PILOT2C_EXECUTION_PREFLIGHT.json` records
`readiness.executable: true` with `blockers: []`, `uses_randomized_graph: false`,
`constructs_randomized_graph: false`, and a free destination. The six trained
artifacts load with `origins: ["trained"]`, `complete: true`, `missing: []`,
`require_trained: true`, `synthetic_allowed: false`.

Run-time memory gate: **6.115 GB available ≥ 4.00 GB** (`passed: true`,
60.1 % used). The gate is the frozen §9.3 gate and was not waived.

The one preflight blocker resolved before execution is documented in
`reports/PHASE_8_PILOT2C_EXECUTION_PREFLIGHT.md`: a *training-stage* refusal had
been folded into the pilot's stage `blockers`. Pilot 2-C trains nothing (amendment
C-7), so the refusal was moved to `training_blockers` (still reported), D5/D6
applicability was made the real precondition, and the runner now injects the six
loaded artifacts. Regression tests cover both the reporting and the refusal when
D5 is not applicable. The global training gate and the campaign gate were not
altered. The full Phase 8 suite passed after the change (531 passed).

No randomized graph was constructed, read or substituted. No C, C′ or D arm was
run. No training occurred. No `n_seeds_selected` write occurred.

---

## 2. Planned versus executed

| Quantity | Planned (D3 §A4) | Stored | Missing | Error rows | Retries | Substitutions |
|---|---|---|---|---|---|---|
| Neural episodes (A, B, F, F_beta, A_prime × 3 seeds × 3 episodes) | 45 | 45 | 0 | 0 | 0 | 0 |
| Floor replays (substrate-free, paired environment seeds) | 9 | 9 | 0 | 0 | 0 | 0 |
| **Total rows** | **54** | **54** | **0** | **0** | **0** | **0** |

`pilot_summary.json` records `planned: 54`, `rows_executed: 54`,
`rows_stored: 54`, `complete: true`, `evidence_kind: "pilot"`,
`experimental_evidence: true`, `merged_into_campaign: false`. No row carries an
error status (the schema omits the `status` field on success); all 54 rows pass
schema validation. Episode rows were appended once, in arm-major plan order; the
store's no-overwrite rule was never triggered.

---

## 3. Per-arm, per-seed, per-episode results

Environment seeds are `environment_seed(master 20261116, seed, episode)`; floor
replays share the environment seed of the five neural arms in the same
`(seed, episode)`.

| Seed | Episode | Environment seed | Steps = survival score | Reward | Termination | Motor spikes | NO_ACTION fraction |
|---|---|---|---|---|---|---|---|
| 9001 | 0 | 563774599 | 323 | 5.22 | collision | 0 | 1.0 |
| 9001 | 1 | 2911696168 | 620 | 10.19 | collision | 0 | 1.0 |
| 9001 | 2 | 4240939637 | 323 | 4.22 | collision | 0 | 1.0 |
| 9002 | 0 | 2632356062 | 620 | 7.19 | collision | 0 | 1.0 |
| 9002 | 1 | 307060235 | 426 | 3.25 | collision | 0 | 1.0 |
| 9002 | 2 | 4241804999 | 620 | 8.19 | collision | 0 | 1.0 |
| 9003 | 0 | 2839813884 | 213 | 3.12 | collision | 0 | 1.0 |
| 9003 | 1 | 756850162 | 426 | 4.25 | collision | 0 | 1.0 |
| 9003 | 2 | 2981106662 | 213 | 2.12 | collision | 0 | 1.0 |

These nine `(seed, episode)` outcomes are **identical for all six arms**,
including the floor: every decision in every arm was `NO_ACTION`, so the game
trajectory is determined by the environment seed alone. The 54 stored rows are
therefore the 9 pairs above, repeated per arm, each with a recorded survival
score.

Per-arm totals (9 episodes each):

| Arm | Rows | Mean survival | Total motor spikes | Episodes with any motor spike | Error rows |
|---|---|---|---|---|---|
| A | 9 | 420.44 | 0 | 0 | 0 |
| B | 9 | 420.44 | 0 | 0 | 0 |
| F | 9 | 420.44 | 0 | 0 | 0 |
| F_beta | 9 | 420.44 | 0 | 0 | 0 |
| A_prime | 9 | 420.44 | 0 | 0 | 0 |
| floor | 9 | 420.44 | 0 | 0 | 0 |

Per-arm, per-seed means (identical across arms):

| Seed | Episodes | Mean survival | Total reward |
|---|---|---|---|
| 9001 | 3 | 422.00 | 19.63 |
| 9002 | 3 | 555.33 | 18.63 |
| 9003 | 3 | 284.00 | 9.49 |

**Observation (not interpretation):** every one of the 54 rows has
`motor_spikes = 0`, `no_action_fraction = 1.0`, and terminated by collision.
This reproduces Pilot 1's F1 record and is the substrate property the amendment
declared, not a new biological finding.

---

## 4. A′ identity

All nine A′ episodes compare equal to the in-process A episode of the same
`(seed, episode)`:

| Evidence | Value |
|---|---|
| Pairs compared | 9 of 9 |
| Fields compared | 19 of 19 (P1–P19: spike times, spike indices, spike digest, action/reward digest, full record sequence, survival/termination summary, action and decoder counts, reward components, neural/game timing, per-decision motor activity, structural/initial/learned-delta/effective weight digests, max abs delta, changed edges, clamp and saturation counts, weight fingerprint, resets) |
| Tolerance | none (exact equality) |
| Mismatches | 0 |
| η | 0.0 in all nine episodes |
| Zero weight delta | true; `changed_edges = 0`; `max_abs_delta_pa = 0.0` in all nine |
| Pathway execution | `rule_executed_zero_delta` in all nine (the rule executes; applied updates are zero because η = 0) |
| Resets | exactly one opening stepper reset per episode (`stepper_resets_this_episode = 1`); zero resets inside the episode (`neural_resets_during_episode = 0`, P19 equal) |
| Store-level reduced comparison | no mismatches |
| Hard stop | never triggered (`hard_stop: false` in all nine) |
| B status | not invalidated |

Because the identity never failed, no A′ episode was refused and no later row
was lost to the hard stop.

---

## 5. Certification claims P2C-1 … P2C-8

Recomputed from the stored rows by
`python -m experiments.phase_8.stages.pilot2c evaluate`; full evidence in
`reports/PHASE_8_PILOT2C_CERTIFICATION.json` (page `all_passed: true`, 54 rows).
The evaluator recomputes from the rows and the manifest only; it writes nothing
else.

| Claim | Result | Evidence summary |
|---|---|---|
| **P2C-1 — floor execution** | **PASS** | 9/9 replays present; each takes `NO_ACTION` on every decision (`{NO_ACTION: steps}`); `motor_spikes = 0`; `weights_before = weights_after = null`; `neural_substrate: "none"`, `is_neural_arm: false`, `spikes_read: false`. |
| **P2C-2 — A′ identity** | **PASS** | 9/9 exact on P1–P19, tolerance none, η = 0, zero delta, one opening reset, no in-episode reset, store-level match. |
| **P2C-3 — Fβ constancy** | **PASS** | All 9 episodes: state-independent; 0 non-zero feature weights; only trainable parameter `["bias"]`; logits for zero and saturated feature vectors identical; exactly one action (NO_ACTION) on every decision; weights frozen. |
| **P2C-4 — F behaviour** | **PASS** | All 9 episodes: state-dependent (`feature_weight_nonzero = 12`); `weights_frozen: true`; parameter digest and feature-weight digest identical before/after every episode. F is not required to be constant and is not treated as constant evidence. |
| **P2C-5 — motor silence** | **PASS** | Every neural episode records a per-decision motor block (`decisions`, `decisions_with_motor_spike`, `per_population_spikes` for LEFT/RIGHT/JUMP, `window_ms = 50.0`) and a motor-spike count consistent with the row. 3,784 decisions per arm; 0 with a motor spike. Zero is reported as zero. |
| **P2C-6 — plasticity attribution** | **PASS** | A′: `changed_edges = 0`, `max_abs_delta_pa = 0.0`, η = 0, all nine. B: per-episode records of `eligible_edges = 683,100`, `changed_edges`, `max_abs_delta_pa`, `n_update_reports`, `n_hook_calls`; 4 of 9 episodes changed 1 edge (applied updates 42, 45, 24, 12 in the four episodes); maximum absolute delta 0.03265 pA; maximum applied update 0.01022 pA; 0 clamp hits; 0 sign violations. |
| **P2C-7 — provenance** | **PASS** | Every row: the seven frozen-input hashes, the three config hashes, the seed plan, `evidence_kind: "pilot"`, `stage_purpose: "floor_and_identity_certification"`, owner/amendment binding; manifest stage purpose matches. Every F/Fβ row records its artifact's condition, evaluation seed, training seed, parameter digest and parameter-file SHA-256. |
| **P2C-8 — viability** | **PASS** | 54 planned, 54 stored, 0 missing, 0 error rows, every row schema-valid with a survival score; nothing skipped, retried or substituted. |

---

## 6. C1–C4 and H1–H3: status, including unevaluable claims

Pilot 2-C tests no hypothesis and estimates no contrast (amendment C-2, C-5,
C-13, C-16). The status of each campaign quantity after this pilot:

| Quantity | Status | Reason |
|---|---|---|
| C1 = F − A | **Not estimated**; rows show a zero descriptive difference | The grid is motor-silent: both arms execute NO_ACTION on every decision, so the paired row difference is exactly 0. The amendment declares C1 estimable but degenerate; three pilot seeds with K = 3 are not the campaign design. No inferential statement is made. |
| C2 = B − A | **Structural zero; not estimated** | On a substrate producing no motor output, the B/A difference has no behavioural channel. Observed row equality is expected and carries no information about plasticity. |
| C3 = A − C | **Undefined; not estimated** | C is excluded from Pilot 2-C (C-4); no randomized graph was constructed, read or substituted. |
| C4 = F − Fβ | **Not estimated**; rows show a zero descriptive difference | Both trained readouts selected NO_ACTION on every decision (F's features are all zero on a motor-silent substrate, so its logits reduce to its bias; Fβ is bias-only). The pilot cannot support a decoding claim, and none is made. |
| H1 (B − A ≠ 0) | **Unevaluable** | C2 is a structural zero here; no test is performed. |
| H2 (A − C > 0) | **Unevaluable** | C3 is undefined; C is absent. |
| H3 (F − A > 0) | **Unevaluable** | C1 is degenerate on this substrate; absence of a difference is not a refutation of H3 at the campaign operating point. |
| H4 (E-matched > floor) | **Not evaluated** | E is not in the Pilot 2-C grid. |
| H5 ((B−A) − (D−C) ≈ 0) | **Not evaluated** | C and D are not in the grid. |
| H6 (motor substrate for non-NO_ACTION) | **No subject** | No non-NO_ACTION update exists in the grid; the descriptive antecedent never occurs. |
| σ_max, paired dispersion, upper confidence limit | **Not estimated** | Amendment C-5. |
| U7, N selection, `design.n_seeds_selected` | **Open / not written** | Amendment C-6. N = 16 remains the predeclared default; no value was selected or written. |
| Bootstrap, Holm, α, SEI | **Unused here** | Retained unchanged for the campaign (C-16). |

Any reading of this pilot as evidence for or against H1–H3 would contradict the
amendment and the data's information content.

---

## 7. Control and floor-replay results

**Floor (P2C-1).** Nine substrate-free constant-`NO_ACTION` replays on the same
nine environment seeds. Each row is schema-valid, takes `NO_ACTION` on every
decision (323 / 620 / 323 / 620 / 426 / 620 / 213 / 426 / 213 decisions), reads
no spike (`spikes_read: false`, `neural_substrate: "none"`), owns no weights
(`weights_before = weights_after = null`), and matches the neural arms' game
trajectories for the same environment seed.

**A′ (P2C-2, P2C-6).** η = 0 identity with the A episode, exact on all P1–P19,
zero weight delta, zero changed edges, zero clamp hits, one opening reset. In
episodes where eligibility slots were touched (12–45 slots), nothing was applied
because η = 0 — the rule executes and the delta is exactly zero.

**Fβ (P2C-3).** Bias-only readout: zero feature weights, trainable set exactly
`["bias"]`, logits identical for zero and 10⁶-saturated feature vectors,
state-independent, weights frozen during evaluation, one action on every
decision.

**F (P2C-4).** State-dependent readout (12 non-zero feature-weight entries),
weights frozen from episode start to end.

**B (P2C-6).** Plasticity executes on the biological substrate: 683,100 eligible
edges at η = 0.5; four of nine episodes applied updates (42, 45, 24 and 12 applied
updates) and changed exactly one edge each; maximum absolute delta 0.03265 pA;
zero clamp hits and zero sign violations. These changes are weight-level only:
they produced no motor spikes and no behavioural difference in this grid, which
is precisely the distinction P2C-6 exists to make attributable.

---

## 8. Deviations, failures and stop conditions

| Item | Record |
|---|---|
| Stop conditions triggered | **None.** No identity mismatch, no memory-gate failure, no refusal during execution, no schema error. |
| Failed or missing entries | **None.** 54/54 stored. |
| Retries or substitutions | **None.** |
| Pre-execution deviation (resolved) | The preflight blocker described in §1.2 (mis-scoped training refusal) was corrected in `experiments/phase_8/stages/pilot2c.py` with two regression tests before execution. The earlier `PHASE_8_PILOT2C_FINAL_PREFLIGHT.*` files are preserved unmodified; the execution preflight supersedes them with that resolution recorded. |
| Run-time anomaly (recorded, no effect on rows) | `F_beta:9001:0` took 1,653.9 s wall time (47.8 % of total run wall time); the next longest episode was 304.8 s. All row fields of that episode are consistent (323 steps, NO_ACTION, collision, 0 motor spikes). This is a host-scheduling observation about the run, not a behavioural or simulation deviation. |
| Historical evidence | Untouched. No original artifact, row, manifest, record, report or README was modified or deleted. |

No parameter, threshold, learning rate, statistical constant, N, U7 value or
frozen protocol was changed.

---

## 9. Artifacts, hashes and provenance

### 9.1 Run artifacts

| File | SHA-256 |
|---|---|
| `episodes.jsonl` (54 rows) | `a14fd3bba0141113ec5f1755927fca9422ee0b46fc310356a0c48fe747778991` |
| `manifest.json` | `43710d3833a7504e5b077fe6bcd0298fdfd237046fb9132afbc4cfa6ae020534` |
| `pilot_plan.json` | `63d51f618f6bebe4024b33db6f1b7cb65fdcb8f948a5cc87c3386b0a80addcab` |
| `pilot_summary.json` | `44dc5c05d78beaae823d515be090b24c656304a31d8ba0ea7102860692a520c5` |
| `reports/PHASE_8_PILOT2C_CERTIFICATION.json` | `bc5effaa28a33f09489c167001f1347ade78464844a021a09cf6d2b894faa357` |

### 9.2 Per-row provenance

Every row records:

- **Seven frozen input hashes:** `graph` `6d47f259…e2192`, `nodes` `144a2eb0…53e5f`,
  `neuron_config` `9b652bde…8b77`, `synapse_policy` `88f64492…dc399e`,
  `plasticity` `616288a4…9e5f70`, `sensory_mapping` `64c716a4…cdfc4ff`,
  `motor_decoder` `525f25e9…0d9fae`.
- **Three config hashes:** `campaign` `b9a2d3d5…477e19`, `conditions`
  `9a93f047…42f671`, `environment` `b391ecf7…3281dc`.
- **Seed plan:** network, learning, structure and environment streams (floor:
  environment only, no streams), derived from master seed 20261116.
- **Binding:** D3 owner decision `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8`,
  amendment `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad`.
- **Evidence kind** `pilot`; **stage purpose** `floor_and_identity_certification`.

### 9.3 Trained artifacts (F, Fβ)

All six are `origin: "trained"`, `stage: "trained"`, read-only, and were not
created, retrained or substituted during this run.

| Condition | Evaluation seed | Training seed | Parameter digest (state/trainable) | Parameter file SHA-256 |
|---|---|---|---|---|
| F | 9001 | 1008 | `bd50cc7343616dd3768b25291d2f3a25f2ae6d56b1c8825de2029ef7889a8883` | `35918eb7bf8d9f2f8b631f1612519484dc845fca71d5c08e61918044ba42efb6` |
| F | 9002 | 1014 | `e1c25034b0e6896f9548fddabd41e4ca9df6d2bf732e816b02e71d25b33dadce` | `a71b47a30f4992bb1cad1d35241dfdbcfb5521fac72347654abcf213fd3d5d95` |
| F | 9003 | 1005 | `2e188b78643612cbdc07570d829fe988c09f5ef29162edb7c419d438c08d9961` | `3ad5e6be64cf7cb7cf912dece30c91fa51bc028950436534e7dea1ec982d0e17` |
| F_beta | 9001 | 1008 | state `b9e5b6e370ad26fa6edcb427a997a88a764fdfe27eac5c6d3773b3145887d712` / trainable `0975693e51a610ab9cc2524d08f3f461eed0d097eb18ae20db8aefbb5191f76e` | `1030fe141f15f34d9cc4e9f8b1b2140f0dbc7fc13f6759a6ccdd1574d14215a5` |
| F_beta | 9002 | 1014 | state `5842826f11dfa058d979237fda5d4d8793cad55ffa981f9d01121f115aaa5b4e` / trainable `5f03c88b093e079ef2a1d87e20efb72b7cdc3566af78e74f2d5a4da4062ff5b9` | `41abbe4d215fda77d29aa7904659f70219e2f570668c17cc463c7a3bae80e6a8` |
| F_beta | 9003 | 1005 | state `409410cc2e87cad2b0d880d6470129b7f7fbeeaaaf6e86bacbf4ea3dd3103f84` / trainable `b157ae1e60912134f0132843f9036fa1ee2a653752aaad0c89eb36a98a6ca120` | `b1cd7e70f3e1d5189e8e0d5708345f0ef588ea5eae4b6fddfbdcbe08d2f86e85` |

Each artifact was loaded through the campaign factory's `TrainingArtifacts`
provider after the A-2 pilot-scope loader verified: explicit pairing, pilot
evaluation seed disjoint from campaign and training seeds, `origin = "trained"`,
complete manifests, and readout width equal to the motor interface (3 features).

---

## 10. Scientific interpretation

### 10.1 What is established (observation)

1. The authorised 54-entry grid executed exactly as declared: 45 neural episodes
   and 9 floor replays, 54 schema-valid rows, no failures, no retries, no
   substitutions, inside the frozen protocol and the D3 scope.
2. The machinery the campaign will depend on behaved as specified: the
   substrate-free floor takes `NO_ACTION` and owns no spike or weight; A′ at η = 0
   is an exact in-process identity on P1–P19 including the reset count; Fβ is a
   provable bias-only readout whose logits ignore the features; F is
   state-dependent and frozen during evaluation; plasticity is attributable to
   its declared rule (A′ exactly zero; B reports eligible edges, changed edges
   and maximum applied update, with 1 changed edge in 4 of 9 episodes and a
   maximum |Δw| of 0.033 pA); provenance is complete on every row; every arm
   completed its planned episodes.
3. The motor substrate is silent in this grid: 3,784 decisions per arm, zero
   motor spikes, `NO_ACTION` on every decision, collision termination in every
   episode. This is measured, not assumed (P2C-5 / C-11), and it reproduces
   Pilot 1's F1 record.
4. Consequently every arm — including the two trained readouts and the floor —
   produced the same game trajectory per environment seed. The zero differences
   between arms are a property of a motor-silent grid, not a result about
   learning, decoding or connectivity.

### 10.2 What is not established (conclusion)

- **No biological claim.** Nothing here shows that the connectome learned,
  adapted, or is capable of behaviour. The readouts' biases chose `NO_ACTION`;
  the substrate produced no motor spikes.
- **No decoding claim.** C4 is not estimated and no evidence bar is met; F and
  Fβ are behaviourally indistinguishable in this grid. H3's necessary condition
  (C4 > 0) is untested, and H3 is not refuted either.
- **No contrast or hypothesis conclusion.** C1–C4 and H1–H3 are not estimated;
  C2 is a structural zero and C3 is undefined. α, Holm, bootstrap and SEI were
  not used.
- **No sample-size decision.** σ_max and paired dispersion were not computed;
  U7 remains open and N remains the predeclared 16 with `n_seeds_selected`
  unset.
- **No campaign authorization.** The confirmatory campaign, E/E-full, graph
  randomisation and the G3 deviation remain exactly as before: refused, open and
  unaccepted. D5's training scope is exhausted by the six existing artifacts;
  the global training gate still refuses further training.

### 10.3 Standing interpretation

Pilot 2-C certifies a floor and an identity. It is infrastructure evidence: the
experiment that will test H1–H3 can be built, paired, stored and audited as
declared. It is not behavioural evidence about the fly, and a PASS on P2C-1 …
P2C-8 must never be described as proof of biological learning or behavioural
competence.

---

*End of Pilot 2-C. No further phase was started.*
