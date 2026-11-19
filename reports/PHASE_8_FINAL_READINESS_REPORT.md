# Phase 8 final readiness report

**Date:** 2026-11-18
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines)
**Verdict:** **NOT READY**
**Approval status:** REV4 is **NOT APPROVED, NOT EXECUTABLE**. U1–U18 remain **PROPOSED — not approved**. No item was approved, applied or decided by this pass.

Companion documents, all written in this pass:

| Document | SHA-256 |
|---|---|
| `reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md` | `8d4a5b8e1a331de77b2d7c4e62fae5b0442a3555621e365eb57acea0aa951f85` |
| `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` | `001a8b1971c687e57fb09fc5e069e5866a79f969d4ea0f801bfe70a4b77b6406` |
| `reports/PHASE_8_END_TO_END_INTEGRATION_AUDIT.md` | `f8b357aae277c937961260f94dec156082e93392260856b3f35680662ca5b9a0` |
| `reports/PHASE_8_EXECUTION_COMMANDS.md` | `2f7532d16e0f018b22348186e0fdfacd4b83a5949c4b5505141ffe0d615c9250` |

---

## 1. Verdict

**NOT READY.**

This is not **READY FOR USER APPROVAL** and not **READY FOR AUTHORIZED PILOT**. Four
independent classes of blocker exist, and any one of them is sufficient:

1. **The protocol authorises nothing.** REV4's status line is "NOT APPROVED, NOT EXECUTABLE";
   U1–U18 are all proposed; `design.n_seeds_selected` is `null`. No campaign design exists.
2. **A mandatory operational gate is known unmet and unresolved.** The sixteen Condition C
   graphs were built below the REV4 §9.3 4 GiB free-memory gate; the deviation is recorded and
   unresolved. The current machine is also below the gate (2.529–2.711 GiB). No compliant
   regeneration may be attempted now, and the existing set cannot be represented as compliant.
3. **The executable stages do not exist.** Even if every decision were recorded and memory were
   sufficient, the tree has no pilot 1 runner, no pilot 2 runner, no training orchestration CLI,
   no production composition root for the campaign, no Phase 8 information adapter and no report
   generator. `run_campaign start` and `resume` are refusing stubs. Approvals alone would not make
   a campaign runnable.
4. **The scientific premise carries a pre-observed floor risk.** The Phase 7 fixed-weight
   closed loop produced 213 `NO_ACTION` outputs, zero motor-population spikes and no propagation
   past one synapse (best first-hop membrane −56.926 mV, 6.926 mV below threshold). This is not a
   Phase 8 result and says nothing about the animal, but it establishes that a floored Condition A
   is a live possibility. Pilot 1 exists to measure exactly this, and the first authorised
   execution must be pilot 1, not a campaign.

The distinctions matter. Work packages G1, G2, G4 (conventional), G6 and G7 are complete **as
mechanisms**. G3 is certified but non-compliant. G5 is assembled and synthetically tested but not
operational. G4 training artifacts and the engine exist but no trained artifact can be produced
while the gates are closed. None of these statuses is a readiness claim.

The route to a different verdict is in §11. It is finite, and most of it is user decisions and a
small number of execution stages already specified by REV4 §10.

---

## 2. What this pass did

| Activity | Result |
|---|---|
| Re-established the original design from the roadmap and REV4 §1–§12 | six conditions, four controls plus floor, four confirmatory contrasts; no condition removed or merged (§3) |
| Audited the implementation against REV4, not against status documents | interface inventory and per-arm trace (§4, §7) |
| Built the U1–U18 decision register | 18 protocol items plus 4 undeclared training inputs; none approved (§5) |
| Verified G3 artifact integrity by hash | 16/16 graph and certificate SHA-256 match; 0 markers; deviation unchanged (§6) |
| Ran the focused synthetic suites and the read-only campaign CLI | **352 passed in 24.36 s**; conformance 69/69; 16/16 certified; memory failed; `executable: false` (§7) |
| Measured free physical memory | 2.711 GiB direct `psutil`, 2.529 GiB via the campaign preflight; gate 4.0 GiB (§6) |
| Wrote the execution-command preparation | commands that are safe now, commands that always refuse, and stages that do not exist (§8) |

**Not done, by restriction:** no training run, no gradient update outside tiny synthetic test
fixtures, no game episode, no pilot, no campaign, no experimental data, no trained artifact, no
graph regeneration, no change to REV4 or any certified graph, no parameter tuning, and no Git
operation of any kind.

Evidence in this report is labelled as one of:

- **executed** — a test or read-only command run in this pass;
- **verified** — an artifact re-hashed or re-read in this pass;
- **static** — a code path or document read without execution because the gate refuses.

---

## 3. Design preservation

The original Phase 8 design is intact in code and configuration. REV4 conformance validates 69
declared constants, including the arm set, seed derivations, budgets and the confirmatory family.

### 3.1 Conditions

| Arm | Role | Substrate | Plasticity | Decision source |
|---|---|---|---|---|
| A | biological, fixed | BANC | none | fixed decoder |
| B | biological, plastic | BANC | three-factor, eta = 0.5 | fixed decoder |
| C | randomized, fixed | target-exchanged BANC | none | fixed decoder |
| D | randomized, plastic | target-exchanged BANC | three-factor, eta = 0.5 | fixed decoder |
| E | conventional baseline | none | none | MLP policy (7 features) |
| E-full | exploratory conventional, capacity-matched | none | none | MLP policy (14 features) |
| F | biological + trainable readout | BANC | none | linear readout |

### 3.2 Controls

| Arm | Role |
|---|---|
| A′ | A through the plastic path at exactly eta = 0; P1–P19 must equal A |
| C′ | C through the plastic path at eta = 0 on the same per-seed graph; must equal C |
| Fβ | bias-only readout, feature weights exactly zero, provably state-independent |
| F-init | F architecture at its seeded initial parameters, trains nothing |
| floor | substrate-free constant `NO_ACTION` game-side replay, no neural stream |

### 3.3 Confirmatory family

C1 = F − A, C2 = B − A, C3 = A − C, C4 = F − Fβ. Holm at α = 0.05 with family size m = 4
(U14) or m = 3. Everything else is a control, an exploratory variant or the floor. C and D are
reported and never gate any decision (U1). The primary outcome is the capped survival score
`min(updates, 900)`, with SEI = 100.

**No condition was removed, merged or redefined in this pass.** No scientific parameter was
altered. The only changes made were the five readiness reports and this status update.

---

## 4. Readiness by work package

"Mechanism" means executable code exists and focused tests that call it pass. "Operational"
means the protocol's own acceptance criterion has been met by a real authorised run. Only the
second is a readiness claim.

| Package | Mechanism | Operational | Principal blocker |
|---|---|---|---|
| G1 plastic stepper | complete | no | no Phase 8 episode |
| G2 trainable readout | complete | no | no trained artifact, no Phase 8 episode |
| G3 random graphs | 16/16 certified, integrity verified | **no — non-compliant** | §9.3 memory deviation; U18 unapproved |
| G4 conventional baseline | complete | no | no Phase 8 game episode |
| G4 training artifacts and engine | infrastructure and loops complete | **no** | authorisation gate; null design; B3–B6 undeclared |
| G5 campaign harness | assembled, 52 tests, CLI present | **no** | no composition root; `start` refuses |
| G6 analysis | complete as a mechanism | **no** | no campaign store |
| G7 viability | complete | no | no pilot or campaign store |
| `conditions/` | 10 modules, 22 tests | no | no Phase 8 episode |
| `controls/` | 8 modules, 14 tests | no | no Phase 8 episode |
| Pilot 1 / pilot 2 stages | **absent** | **no** | not implemented |
| Training orchestration stage | **absent** | **no** | not implemented |
| Campaign execution stage | **refusing stub** | **no** | not implemented |
| Information analysis for Phase 8 | **absent** | **no** | no adapter |
| Report / freeze stage | **absent** | **no** | manual, no generator |

The boundary between "component" and "stage" is the central readiness finding: the components
exist and are tested, but the stages that compose them into an executable Phase 8 do not. A
campaign cannot be produced by recording approvals while those stages are missing.

---

## 5. Protocol decisions

`reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md` records all 18 protocol decisions and four
undeclared training inputs. **No item is approved, applied or decided.**

### 5.1 Items that independently block the confirmatory campaign

U2 (eta = 0.5), U3 (primary outcome), U4 (null model), U5 (E as REINFORCE), U6 (K = 10), U7
(N), U9 (plasticity during evaluation), U10 (floor), U11 (compute budget and the 4 GB gate),
U13 (C′ at all N × K), U14 (Holm family size), U15 (H3 confirmatory), U16 (Fβ definition), U18
(target exchange), and B3–B6 (pairing, training environment seeds, checkpoint policy, RNG and
optimizer restoration).

### 5.2 Items whose choices are recorded later

U1 (pilot gate cases and the U1-B branch) is procedural at 10.8; U8 (E-full) is exploratory; U12
(no new `learning/` implementation) preserves the current state if option (a) is approved; U17
(E3/E4 thresholds) applies at reporting.

### 5.3 The null design and the N rule

`design.n_seeds_selected` remains `null`. The register documents, but does not apply, the
following recommendation:

- default **N = 16**;
- **N = 10** only if the pilot's 80% upper confidence limit on `σ_max` is ≤ 112.87, the bound
  derived from `2.8016 · σ_max / √10 ≤ 100`;
- with three pilot seeds (df = 2) the 80% upper limit is about 2.1× the point estimate, so N = 10
  requires a point estimate of roughly ≤ 53.7;
- the decision must be recorded before any campaign outcome is observed; N = 10 must never be
  selected from the point estimate alone;
- if neither N = 10 nor N = 16 is defensible, there is no campaign.

If the value is later recorded, the change is `design.n_seeds_selected` in
`configs/phase_8/campaign.yaml`, the null-only conformance check in
`experiments/phase_8/campaign/protocol.py`, and the tests that assert the null. The analysis
already accepts either N and recomputes at the actual complete-pair N.

### 5.4 Inputs REV4 does not declare

- **B3 campaign↔training pairing.** `training/seeding.py::validate_pairing` requires an exact,
  complete `(condition, campaign_seed) → training_seed` map with per-condition uniqueness and a
  shared F/Fβ training run. It supplies no default. REV4 declares no mapping.
- **B4 training-episode environment seeds.** The engine accepts a callable or an integer and
  records it per episode. The schedule is a caller decision.
- **B5 checkpoint cadence, retention and format.** The checkpoint module takes the cadence and
  root as caller inputs. REV4 declares none.
- **B6 RNG and optimizer restoration.** Every checkpoint records `rng_restored: false` and
  `optimizer_state_restored: false`. Resume is parameter-continuous, not bit-identical. That
  limitation must be accepted or the checkpoint format extended before resume is used as
  evidence.

None of these may be invented by the implementation. Each requires a recorded decision.

---

## 6. G3 memory deviation

### 6.1 What is established

- All sixteen Condition C graphs for campaign seeds 1–16 exist, are certified against the
  mandatory gates R4–R14 (including R9b) and R17, and were re-hashed in this pass: 16/16 graph
  SHA-256 and certificate SHA-256 match their records; zero markers remain.
- The graphs are structurally what their certificates say: exact per-node in/out degree, exact
  weight multiset, exact per-source weight profile, exact per-node transmitter signs, no
  duplicate pairs or self-edges, valid CSR, rewired fraction ≥ 0.99, neighbourhood Jaccard ≤
  0.01, R17 byte identity across two builds.
- The 16 digests are distinct from each other and from the original graph; the deterministic
  regeneration reproduces all 16; the loader accepts all 16 and refuses an uncertified or
  missing-certificate record; the biological graph is unchanged.

### 6.2 What is not established

- That the builds were performed under §9.3. They were not. Free physical memory during the
  builds was **1.628–2.747 GiB** against a 4.0 GiB gate, and
  `campaign_seed_summary.json` records `compliance.status = "deviation_recorded"` with
  `gate_weakened: false`.
- That U18 is approved. It is not.
- That the set is campaign-ready. Compliance is one open gate among several.

**Conclusion:** the graphs and certificates are intact and usable as objects. The deviation is a
**compliance** defect, not a **corruption** defect. The integrity evidence does not cure it.

### 6.3 Is regeneration necessary?

Only if the campaign must claim §9.3 compliance without a recorded deviation or protocol
amendment. Regeneration is **not** necessary for the graphs' integrity. The options are:

| Option | Effect |
|---|---|
| A. Accept the recorded deviation | no execution; requires a user record and a written rationale; the campaign carries the deviation |
| B. Regenerate all 16 on a machine with ≥ 4 GiB free | produces a compliant build record; deterministic digests should match, and equality must be observed; new namespaces only |
| C. Regenerate a subset | insufficient; a compliant subset does not make the set compliant |
| D. Defer until the machine sustains the gate, then regenerate | same as B, later |

The 0.75 GB construction preflight is a separate safety check and does **not** satisfy §9.3. The
4 GB requirement is not weakened, rounded down or waived by this report.

### 6.4 Can the current machine regenerate?

**No.** Total physical memory is 16.47 × 10⁹ B (15.34 GiB); available is 2.711 GiB by direct
`psutil` reading and 2.529 GiB through the campaign preflight, a margin of −1.47 GiB. No graph
was regenerated in this pass and none may be while the reading is below the gate.

**A user decision is required:** accept the recorded deviation, authorise a compliant rebuild on
a qualifying machine, or defer. The blank decision record is in
`PHASE_8_G3_DEVIATION_RESOLUTION.md` §9. No option is selected by this report.

---

## 7. Integration verification

### 7.1 Executed evidence

| Check | Result |
|---|---|
| 14 focused synthetic suites | **352 passed in 24.36 s** |
| Read-only `run_campaign check` | conformance **69/69**; certified graphs **16/16**; memory **2.529 / 4.0 GiB (failed)**; `design_resolved: false`; `executable: false` |
| G3 integrity | 16/16 graph and certificate hashes match; zero markers |
| Static trace | registry → factory → dispatcher → runner → store → analysis |

### 7.2 Per-dimension result

| Dimension | Result | Basis |
|---|---|---|
| Construction and dispatch | pass | 12/12 arms routed |
| Certified-graph selection for C/D/C′ | pass | certified-only source; no biological fallback; refusal paths tested |
| Trained-artifact loading | pass (refused while unauthorised) | origin, width, state, trainable checks; trained origin refused |
| Seed pairing | pass | environment paired; network per condition; structure shared by C/D/C′ |
| Environment pairing | pass | identical environment seed across paired arms; A′/C′ mirror |
| Reward handling | pass | one three-factor update per game update; non-finite refused |
| Result schema | pass | closed key set; episode-key uniqueness; torn-tail detection |
| Provenance | pass | protocol/config/input hashes, seeds, manifests, row evidence |
| Deterministic replay | pass within declared scope | deterministic loops and sign-flip; resume is parameter-continuous only |
| Failure handling and resume | pass | failures recorded without fabricated rows; drift refused |
| **Uninterrupted six-condition campaign** | **not executed** | prohibited in this pass |

No implementation defect was found in the audited path. The integration is mechanically complete
and deliberately blocked. The six open inputs are **designed refusals**, not bugs.

### 7.3 Boundaries of that evidence

- Verification is at real interface boundaries with synthetic fixtures, not an uninterrupted
  campaign. A boundary-level pass does not prove that 1,920 sequential episodes would complete.
- No BANC-scale episode, no real game episode and no training run was executed.
- The 32-node condition fixtures are test networks, not biological claims.
- The Phase 7 fingerprint `cca811f3…b2fb` at 213 updates has **not** been reproduced from
  `conditions/a_fixed.py`. That remains an open integration item (REV4 §10.2).
- The Phase 4 action selector and game controller (`environment/game_controller.py`) are
  **optional** and are not wired into the Phase 8 A–D path; the default path preserves the
  Phase 7 record schema. This is not a defect, but it means the Phase 4 additions do not change
  the floor risk described in §9. Action selection acts after decoding; with zero motor spikes it
  has nothing to select.

Two stale documentation labels were observed and are recorded, not silently corrected:
`analysis.py:1414` and `registry.py:196` still say "REV3 U14" where REV4 is the governing
document, and the CLI blocker text says "10.7/10.8" where the design decision is at 10.8. They
change no behaviour.

---

## 8. Execution readiness

### 8.1 Stages that can and cannot be commanded

| Stage | State |
|---|---|
| `run_campaign check`, `seeds`, `graphs`, `status` | available and read-only |
| Focused synthetic tests | available |
| `run_campaign start`, `resume` | refusing stubs, exit 2, zero rows |
| Pilot 1 (10.3) | **absent** |
| Pilot 2 (10.8) | **absent** |
| Training artifacts (10.5, 10.9) | engine exists, **no CLI**; gate always raises |
| Production composition root (10.10) | **absent** |
| Statistical analysis | CLI exists; no store to analyse |
| Information analysis (10.11) | Phase 6 CLI only; **no Phase 8 adapter** |
| Final report and freeze (10.12) | **absent**; manual |

### 8.2 Preconditions

P1 REV4 approval; P2 U1–U18 recorded; P3 `n_seeds_selected`; P4 B3 pairing; P5 B4 environment
schedule; P6 B5 checkpoint policy; P7 B6 restore policy; P8 G3 resolution; P9 ≥ 4.0 GiB at the
immediate preflight; P10 composition root and pilot runners. **All ten are currently unmet.**

### 8.3 Intended scale, once executable

| N | Arms | K | Episodes |
|---|---|---|---|
| 16 | 12 | 10 | 1,920 |
| 10 | 12 | 10 | 1,200 |

The 12 arms include the four controls, E-full and the floor. The six conditions and the
confirmatory family are unchanged. Exact prepared commands, acceptance checks and refusal
behaviour are in `reports/PHASE_8_EXECUTION_COMMANDS.md`.

### 8.4 Memory

The campaign preflight requires ≥ 4.0 GiB free physical memory measured with
`psutil.virtual_memory().available / 1024³`. The current machine reads 2.529–2.711 GiB. Nothing
may start until the gate passes at the immediate preflight, regardless of protocol approval.
This is the same gate that blocks graph randomisation and BANC-scale simulation.

---

## 9. Scientific premise: a pre-observed floor risk

This section is context, not a Phase 8 result. It was already established before this readiness
pass and is reported here because it changes what the first authorised execution should be.

The Phase 7 fixed-weight closed loop ran 213 game updates and produced:

- 2,852 spikes, **all** inside the 232 stimulated sensory neurons;
- **zero** spikes in any non-stimulated neuron;
- **zero** current delivered to motor neurons;
- **213 `NO_ACTION`** outputs.

The propagation stops one synapse downstream: 473 of 607 first-hop targets receive current, and
the strongest reaches −56.926 mV, which is 6.926 mV below the −50 mV threshold. Because no
first-hop neuron spikes, no second-hop current exists, and motor neurons receive zero current.
The decoder's evidence gate (≥ 5 spikes, ≥ 3 active neurons) therefore never passes. This is a
controlled negative result about one model configuration, not a bug in the decoder, selector,
controller or adapter, and not evidence about the living fly.

The Phase 4 status records the goal as **not demonstrated**: "the sensory drive does not recruit
motor neurons" is an open model/evidence gap requiring R3/R4 and a pre-registered new
experiment. No threshold was changed to force recruitment, and none may be changed inside
Phase 8.

**Consequence for readiness:** Condition A is at material risk of being at the platform floor.
Pilot 1 (REV4 §10.3) is the instrument designed to measure this before any campaign. If A and F
floor, U1-B applies; the register's advisory recommendation is to stop, report the floor and the
pathology decomposition, and request a scope decision — never to run the campaign anyway and
never to repair the interface inside Phase 8 (that is Phase 9). The first authorised execution
must therefore be pilot 1, not a campaign.

---

## 10. Mandatory gates

| # | Gate | Requirement | Current state | Owner |
|---|---|---|---|---|
| 1 | Protocol | REV4 approved at 10.0 | **not approved** | user |
| 2 | Decisions | U1–U18 recorded | **none** | user |
| 3 | Design | `n_seeds_selected` recorded | **null** | user, after pilot 2 |
| 4 | Training inputs | B3–B6 recorded | **none** | user |
| 5 | G3 | deviation accepted by record or compliant rebuild; U18 approved | **deviation recorded, unresolved** | user |
| 6 | Memory | ≥ 4.0 GiB at the immediate preflight | **2.529–2.711 GiB** | environment |
| 7 | Training | authorised training producing F/Fβ/E artifacts | **impossible while gated** | user + implementation |
| 8 | Execution stages | pilot 1/2, training CLI, composition root, information adapter | **absent** | implementation |
| 9 | A fingerprint | reproduce `cca811f3…b2fb` at 213 updates (10.2) | **not attempted** | implementation + execution |
| 10 | Pilot 1 | A viability and measured floor | **not started** | execution |
| 11 | Pilot 2 | `σ_max` with UCL; N recorded | **not started** | execution |
| 12 | Campaign start | first two seeds complete and valid (10.10) | **not started** | execution |

A refusal at any one of these is the correct outcome. None may be bypassed to "see what
happens".

---

## 11. Shortest path to a different verdict

The original objective is the experiment, not more infrastructure. This path adds only the
stages REV4 §10 already requires.

**User decisions (no execution):**

1. Record REV4 approval (10.0) and the U1–U18 decisions, including the U7 N rule, the U1-B
   branch, U14 and U18. Approving U-items individually does not itself approve REV4.
2. Record B3–B6: the campaign↔training pairing, the training-episode environment-seed schedule,
   the checkpoint cadence/retention/format, and the restore policy (or accept
   parameter-continuous resume).
3. Decide G3: accept the recorded deviation with a written rationale, authorise a compliant
   rebuild on a machine that sustains ≥ 4 GiB, or defer. Do not regenerate on the current
   machine.
4. Decide how pilot 2 obtains a C graph: use campaign-certified seeds (not fully disjoint) or
   build pilot certificates under the §9.3 gate. No certificate exists for pilot seeds
   9001–9003.

**Implementation (no scientific choices):**

5. Implement the pilot 1 runner and pilot plan (10.3): an explicit `(arm, pilot_seed, episode)`
   plan, a separate pilot root, `pilot: true`, schema-valid rows, measured floor replay, no
   campaign-store writes. Add focused tests.
6. Implement the training orchestration CLI (10.5, 10.9) over the existing engine, artifacts and
   checkpoints: explicit pairing, declared budgets, declared checkpoint policy, refusal of
   overwrite and of untrained artifacts. Add focused tests.
7. Implement the pilot 2 runner (10.8), including A′/C′ exact mirrors and the `σ`/UCL report.
8. Implement the production composition root (10.10): real factory, dispatcher, per-arm runners,
   input hashes, environment capture, integrity baseline and memory preflight passed to
   `CampaignRunner.start`; replace the refusing stub. Add focused tests.
9. Implement the Phase 8 information-analysis adapter (10.11) as a read-only stage over
   `information/`, writing under the Phase 8 results root and leaving Phase 6 outputs untouched.
10. Add the report/freeze stage (10.12) or run it manually to produce `PHASE_8_RESULTS.md` and
    `.json` with the analysis hash, protocol hash, limitations and the G3 deviation.

**Execution (only after the gates):**

11. On a machine with ≥ 4 GiB free, and with approvals recorded, run pilot 1; classify A against
    the measured floor. If U1-B occurs, stop and request a scope decision.
12. Run training for F/Fβ/E; verify artifacts reload and pass condition compatibility.
13. Run pilot 2; compute `σ_max` and its upper confidence limit; record N according to the
    predeclared rule.
14. Start the campaign; verify the first two seeds, A′≡A and C′≡C, then continue.
15. Run the statistical analysis on the store, then the information analysis, then the final
    report and freeze.

Steps 5–10 may be implemented before decisions 1–4 are recorded because they change no scientific
parameter and execute nothing; they must remain gated and tested synthetically. Steps 11–15
cannot begin until every gate in §10 is satisfied.

---

## 12. What this pass did not do

- No training run, no gradient update on a real substrate, no game episode, no pilot, no
  campaign and no experimental data collection.
- No trained artifact generated and no `experiments/results/phase_8/training/` directory
  created.
- No graph regenerated, moved, renamed or deleted; no certified namespace written.
- No change to REV4, REV3, the configs, the scientific parameters, the thresholds or the
  datasets.
- No parameter tuned on any outcome; every constant is the value declared in REV4 or
  `configs/phase_8/`.
- No Git staging, commit, push, reset, clean, stash, checkout or delete.
- No item approved on the user's behalf, and no decision recorded in the blank records.

---

## 13. Provenance and integrity

| Item | Value |
|---|---|
| REV4 SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (unchanged) |
| REV3 SHA-256 | `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf` (preserved) |
| Certified graphs | 16/16 graph and certificate hashes match their records; 0 markers |
| Original BANC graph | unchanged; hash matches the recorded value |
| Focused Phase 8 tests | 352 passed in 24.36 s (synthetic fixtures only) |
| Conformance | 69/69 checks pass |
| Memory | 2.711 GiB direct `psutil`; 2.529 GiB campaign preflight; gate 4.0 GiB |
| Environment | Windows, Python 3.13.14, numpy 2.3.4, torch 2.10.0+cpu; no GPU work |

No experimental observation was produced and no biological claim is made anywhere in this
report. The Phase 7 figures in §9 are prior controlled-negative evidence, not Phase 8 data.

---

## 14. Limitations of this report

1. It is a readiness audit, not an execution report. It cannot establish that a BANC-scale
   episode runs; only an authorised episode can.
2. The integration evidence is boundary-level, with synthetic fixtures. A passing boundary suite
   does not prove an uninterrupted 1,920-episode campaign.
3. The G3 certification is internally consistent but was produced below the required memory
   gate; compliance is unresolved regardless of integrity.
4. The N recommendation is advisory and unapplied; no campaign design exists.
5. Statuses in this report are true of the tree at 2026-11-18. Any later execution must re-run
   the preflight and record its own evidence; this report must not be cited as authorisation.
6. Nothing here approves U1–U18, REV4, U18, the G3 deviation or any training or campaign.
