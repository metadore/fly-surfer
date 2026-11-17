# Phase 8 Protocol — Revision 2 Change Log, Open Decisions and Readiness

| field | value |
|---|---|
| date | 2026-11-16 |
| scope | review correction of `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` |
| original (V1) | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md`, 888 lines, SHA-256 `d9d13a6c312b1c536a0d9266ade4ad81c47bdc99192d6f8d53816d81813fc505` — **preserved byte-identical** |
| corrected (REV2) | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md`, 1,465 lines, SHA-256 `d6a8964c753984736fcdcf315ca0e8e6af61415afcb79cd5db9cbae45bdab7c0` |
| executed | nothing — no experiment, no training, no campaign, no install, no weight or connectivity change, no Git operation |
| status | **NOT APPROVED, NOT EXECUTABLE** |

---

## 1. Change log

### 1.1 Requested correction 1 — statistics

| Where | V1 | REV2 |
|---|---|---|
| §7.3 | minimum attainable p quoted as `1/1024 = 0.000977` and labelled **two-sided** | split into minimum **one-sided** `1/1024 = 0.0009765625` and minimum **two-sided** `2/1024 = 0.001953125`. The two-sided statistic `|T| = Σ|dᵢ|` is attained by two sign vectors (all-plus, all-minus), which is why the factor is 2 |
| §7.3 | count threshold for p ≤ 0.05 unstated | `≤ 51 of 1,024` (51/1,024 = 0.049805; 52/1,024 = 0.050781) |
| §7.3 | no degeneracy rule | all-zero differences ⇒ p = 1.0 **by definition**, reported as uninformative, never as equivalence; sign-test robustness check added |
| §7.5 | Holm m = 3; minimum adjusted p implied `3 × 0.000977 = 0.00293` | m = 4 (primary, pending U14): step 1 threshold 0.0125 ⇒ ≤ 12 sign vectors, minimum adjusted **0.0078125**. m = 3 alternative: step 1 0.016667 ⇒ ≤ 17, minimum adjusted **0.005859375** |
| §7.5 | power framing implied reasonable sensitivity | equal-magnitude consequence stated: 9-vs-1 gives p = 22/1024 = 0.0215, 8-vs-2 gives 112/1024 = 0.109, so **only a unanimous 10-of-10** survives under equal magnitudes |
| §7.4 | N = 10, escalation rule | N = 10 kept as the declared floor; N = 16 stated as the recommended default, because a 3-point σ estimate has `df = 2` and a 80% upper limit ≈ 2.1× the point estimate (≈ 142 updates ⇒ N ≈ 16) |
| §11.21/22/29, Appendix C, §12 | some constants stale or absent | all restated consistently; Appendix C now carries both variants and both minima |

Every constant was re-derived independently from `2^10 = 1024` and checked across §7.3, §7.4, §7.5, §11, Appendix C.

### 1.2 Requested correction 2 — condition F (trainable readout)

New §3.6.1–§3.6.5:

- **§3.6.1 per-decision motor record.** A `motor_activity` block at record top level for every decision in A, B, C, D, F and Fβ: window bounds and rule, total spikes, `any_motor_spike`, populations with spikes, and per-population `spikes`, `active_neurons`, `active_fraction`, `mean_rate_hz`, `sufficient`. Top-level because `record["decoder"]` is `null` whenever the fixed decoder returns `None`. Additive only; no Phase 7 field changes; floats rounded at the producer so P10 comparisons are exact.
- **§3.6.2 Fβ constant-action control.** F with the readout's feature path zeroed, so only the bias trains. Declared contrasts: `F − Fβ` = value of motor-driven state-dependence; `Fβ − floor` = value of a better constant action; `F − A` = value of a learned vs fixed decoder, possibly bias-driven. The floor must be **measured** by replaying paired seeds with constant `NO_ACTION` — V1's "analytically known, zero cost" was wrong because collision timing depends on layout.
- **§3.6.3 motor-driven vs bias-driven.** Frozen-parameter input ablation (motor features set to exactly 0.0, logits recomputed, no retraining and no extra rollout). Motor-driven = argmax changes and ≥ 1 spike in the chosen population; bias-driven = argmax unchanged; undefined = `NO_ACTION` with no motor spike.
- **§3.6.4 evidence bar E1–E5.** E1 `F − Fβ > 0` survives Holm; E2 `F − A > 0` survives Holm; E3 motor activity present on ≥ 1% of decisions in ≥ half of seeds; E4 ≥ 10% of non-`NO_ACTION` decisions motor-driven; E5 fresh-process rerun reproduces the motor-driven count. **If E3 fails, no neural-learning claim of any strength is permitted.**
- **§3.6.5 forbidden statements.** "the connectome learned", "plasticity improved performance" in F, "the readout succeeded" when Fβ matches, and "F beat the baseline" without naming the baseline.

### 1.3 Requested correction 3 — condition C (random graph validation)

New §3.3.1 with gates R1–R18: swaps attempted / accepted / rejected by reason; rewired fraction ≥ 0.99; edge-set Jaccard ≤ 0.01; out- and in-degree exact preservation with sums 1,535,710; sign vector exactly equal, signed edges 683,100; weight multiset elementwise equal, sum 18,552,546, min 5, max 913; per-source outgoing weight profile (R9b); duplicates 0; self-edges 0; `BancConnectome.__post_init__` invariants; neighbourhood overlap ≤ 0.01; mixing plateau (< 1e-4 change over the last 20% of accepted swaps); component structure reported not gated; reciprocity/assortativity descriptive; byte-identical reproducibility from the same seed; graph seed stream `SeedSequence([MASTER_SEED, seed, "structure"])`.

Explicit statement that **an attempted swap count is not evidence of adequate randomization**, plus a rejection protocol (halt, no relaxed gate) and a new decision U18 on the swap parameterisation, which the gates depend on.

### 1.4 Requested correction 4 — A′ internal validity control

New §3.8:

- §3.8.2 coverage: A′ on **all N seeds × all K episodes**, one fresh-process replay per seed, `eta` exactly `0.0` (not `1e-12`, not a skip flag).
- §3.8.3 comparison fields P1–P19: spike arrays, `spike_sha256`, `action_reward_sha256`, full record JSON, survival/termination, action and state counts, reward total and components, neural steps and times, per-decision `motor_activity`, structural/initial/learned-delta/effective weight digests, `max|Δw| = 0.0`, changed edges 0, clamp hits 0, stepper `weight_fingerprint`, resets.
- §3.8.4 **zero tolerance**; documented nuance that eligibility traces may be non-zero while all weight deltas are exactly zero, with `plasticity_path.mode ∈ {"rule_executed_zero_delta","short_circuited"}` recorded.
- §3.8.5 hard-stop failure protocol: B marked INVALID, artifacts retained and labelled, no retry-until-match, only two permissible conclusions.
- §3.8.6 applied at pilot, every campaign seed, and a final validation pass that recomputes from the stored JSONL.

### 1.5 Requested correction 5 — U1–U12 review

§12 rewritten: U1–U12 each now state *Decision / Options / Recommendation* with every alternative preserved, plus new §12.1 tabulating, per item, the ambiguity found in V1 and how REV2 addressed it **without deciding**:

| ID | V1 ambiguity found | Status |
|---|---|---|
| U1 | "A or F" gate vs §0 prediction vs §7.8's different 4-of-6 rule | stop rule vs reporting rule separated; option (d) added |
| U2 | option (c) unnamed eta; Phase 5 insensitivity unmentioned | value set moved to the decision, cost stated |
| U3 | "co-primary" conflicts with single-primary; censoring scope unstated | contradiction stated; censoring applies to survival only |
| U4 | "component-preserving" undefined; sign null conflated with wiring null | operational definition added; questions separated |
| U5 | option (b) cost unstated | dependency, pinning and wrapper-validation costs listed |
| U6 | K's effect on cost and df unstated | K affects within-seed precision only |
| U7 | 3-seed σ treated as confirmatory | `df = 2` argument added; **recommendation changed 10 → 16** |
| U8 | no capacity matching for E-full | same architecture and budget required |
| U9 | frozen evaluation did not require held-out seeds | added |
| U10 | floor called analytically known and zero-cost | **error corrected**: floor must be measured; reclassified as a control arm |
| U11 | budget omitted the control arms | updated to ≈ 19–78 h at N = 10 (≈ 30–125 h at N = 16) |
| U12 | duplicate `learning/` implementation risk unstated | duplicate-module constraint cited |

Two further inconsistencies outside U1–U12 were found and corrected with the choice left open: H3 was labelled exploratory while `C1 = F − A` was confirmatory (now U15), and "No evaluation episode may update anything" is false for B and D (§6.7).

### 1.6 Corrections found during the consistency pass (not in the original five)

- §3.3 contradicted itself: it declared per-neuron outgoing weight sums *not* preserved, while §3.3.1 gates require exact weight-multiset (and, after this revision, per-source profile) preservation. The swap parameterisation was implicit. Made explicit and raised as **U18**; R9b added; R8 made conditional on the choice.
- §7.1 and §10 step 8.8 said "N = 10" and "6 conditions" without the control arms; updated.
- §7.8 restated as a reporting rule, not a stop rule.
- §9.2 arithmetic re-added: 3.1 + 0.62·3 + 6.2·2 + 0.25 + 0.3 + E + analysis = ≈ 19 h; upper 13.1 + 2.62·3 + 26.2·2 + 2.1 + 2.5 ≈ 78 h (V1/earlier REV2 rounded to 18/76).
- Appendix C said "Holm m = 3" and lacked the corrected minima; rewritten.
- A structural edit had deleted the `### 3.4 Condition D` heading; restored.

---

## 2. Remaining unresolved decisions (all open — none applied)

Recommendations are advisory; every alternative is preserved in §12 of the protocol.

| ID | Decision | Recommendation (not applied) |
|---|---|---|
| U1 | action if the pilot shows the `NO_ACTION` floor in A and F | (b) stop, report floor + pathology decomposition, request scope decision; (d) legitimate once E exists; **never** change drive/decoder inside Phase 8 |
| U2 | eta for B and D | (a) Phase 5's declared 0.5; a second eta arm only if declared in advance |
| U3 | primary outcome | (a) censored survival in updates |
| U4 | random-null scope | (a) degree+sign-preserving rewire confirmatory; (b) component-preserving exploratory; (c) sign-randomised exploratory |
| U5 | condition E implementation | (a) direct REINFORCE, no installs |
| U6 | evaluation episodes per seed K | (a) K = 10; K = 5 fallback if budget-capped |
| U7 | number of seeds N | **(b) N = 16** (changed from V1's 10) |
| U8 | E-full (14 features) | exploratory only; capacity-matched |
| U9 | B/D plasticity during evaluation vs train-then-freeze | (a) online; (c) both if budget allows; (b) exploratory with held-out seeds |
| U10 | no-action floor | measure it by replaying paired seeds with constant `NO_ACTION`; control arm, not a condition |
| U11 | compute ceiling | (a) accept ≈ 19–78 h at N = 10 (≈ 30–125 h at N = 16) |
| U12 | new `learning/` implementation | (a) no — keep placeholders untouched, no duplicate plasticity module |
| U13 | C′ (`eta = 0` on the random graph) for D | (a) all N seeds × K episodes |
| U14 | confirmatory family size | (a) m = 4 with C4; m = 3 forbids any decoding claim |
| U15 | H3 confirmatory vs exploratory | (a) confirmatory, consistent with C1 |
| U16 | scope of Fβ | (a) full campaign if m = 4 |
| U17 | E3/E4 declared thresholds | (a) accept ≥ 1% of decisions in ≥ half of seeds and ≥ 10% motor-driven |
| U18 | swap parameterisation for the null | (a) target exchange (source and weight stay with the edge), making R8/R9b exact |

---

## 3. Updated readiness verdict

**Design-ready; NOT execution-ready. Unchanged from V1 in substance.**

- The six conditions are fully specifiable against verified interfaces, and REV2 closes the interpretability gaps in F, C and A′.
- Implementation gaps **G1–G7 are unchanged**: no incremental plastic stepper (B, D), no live readout (F), no BANC-scale degree-preserving null (C, D), no matched conventional baseline (E), no campaign harness, no Phase 8 analysis layer, no verified viability check.
- Three **control arms** are now mandatory for interpretation and none exists: **A′** (must equal A exactly), **C′** (proposed, U13), **Fβ** (bias-only). They reuse B/D/F code paths, so they add runtime rather than new mechanisms: ≈ 19–78 h single-process at N = 10, ≈ 30–125 h at N = 16.
- The pre-registered expectation remains that A, B, C, D and probably F execute `NO_ACTION` everywhere, exactly as the Phase 7 baseline did (2,852 spikes, 0 motor spikes, 213/213 `NO_ACTION`, weights unchanged). A floor result is a reportable outcome and is not grounds for tuning.
- Phase 6's negative confirmatory result remains frozen and is not reinterpreted.
- The statistics are now correct but **only detect large effects**: at N = 10 no contrast can reach an adjusted p below 0.0078 (m = 4) or 0.0059 (m = 3); N = 16 is recommended.
- Approval is required for §12 (U1–U18) **before** any code, install or campaign. Until then no implementation step in §10 may begin.
