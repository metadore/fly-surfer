# Phase 8 REV3 — Correction Report

**Date:** 2026-11-17
**Scope:** correction of the Phase 8 REV2 protocol against the independent audit, and production of
a complete REV3 protocol. Implementation status is reported separately in
`reports/PHASE_8_IMPLEMENTATION_STATUS.md`.
**Status of REV3:** complete protocol, **NOT APPROVED, NOT EXECUTABLE**. Every U-item remains a
proposal awaiting human approval.

---

## 1. Source and output identity

| Document | SHA-256 | Lines | State |
|---|---|---|---|
| REV2 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md` | `d6a8964c753984736fcdcf315ca0e8e6af61415afcb79cd5db9cbae45bdab7c0` | 1,465 | **unchanged, byte-identical** |
| REV1 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` | `d9d13a6c312b1c536a0d9266ade4ad81c47bdc99192d6f8d53816d81813fc505` | — | **unchanged, byte-identical** |
| Audit `reports/PHASE_8_REV2_INDEPENDENT_AUDIT.md` | `dee563ef22a94b093a5e61b16303ac23890024efddcad16ff27d3f9d6fb77a12` | 866 | **unchanged** |
| REV3 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV3.md` | `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf` | **1,848** | new complete protocol |

The REV2 and audit hashes match the values declared in the correction brief. REV1 and REV2 were
preserved in place. REV3 was created as a copy of REV2 and then edited; it is a complete protocol,
not a change log.

---

## 2. Audit findings → REV3 sections

### 2.1 Critical and major findings

| Audit ID | Finding | REV3 resolution | REV3 location |
|---|---|---|---|
| **C1** | Pilot could not run because it referenced conditions not yet implemented; sequencing was circular | Pilot split into **10.3** (A viability: 3 seeds × A × 3 episodes) and **10.8** (paired pilot: 3 seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes, after all those builds exist). The sequence is 10.0 approval → 10.1 skeleton → 10.2 A → 10.3 pilot 1 → 10.4 C → 10.5 F/Fβ → 10.6 A′/C′ → 10.7 B/D → 10.8 pilot 2 → 10.9 E → 10.10 campaign → 10.11 analysis → 10.12 report → 10.13 viability. Every step has inputs, deliverables, acceptance criteria and dependencies. The two pilots are explicitly not hypothesis tests and pilot 1 does not estimate any contrast | §10, §3.8.2, §7.1 |
| **M1** | Extremal sign assignments were called all-plus/all-minus | REV3 states the extremes are `sᵢ = sign(dᵢ)` and its negation; these coincide with all-plus/all-minus only when all differences share a sign. The minimum two-sided p is `2/2^N` by the permutation group, not by unanimity | §7.3, Appendix C, revision notice |
| **M2** | Validity assumption of the sign-flip test was unstated | REV3 adds the null of sign-reversal exchangeability, seed independence, the role of pairing, and the exact sign test as a robustness check; the assumption's failure mode is a limitation | §7.3, §11.32 |
| **M3** | §11.23 said per-neuron outgoing weight sums are not preserved, contradicting R9b | Parameterisation is target exchange (U18): sources and weights stay fixed, targets swap. R9b (per-source outgoing weight profile) is exact under the recommendation. §11.23 now says so and scopes the V1 wording to endpoint re-pairing | §11.23, §3.3.1 R9b, §12 U18 |
| **M4** | Missing pairs silently kept N and thresholds | REV3 defines missingness, forbids silent drops, recomputes the enumeration and every threshold at the actual complete-pair N, halts if N is below the predeclared minimum, and requires a sensitivity analysis for asymmetric missingness | §7.3, §7.6, §7.1 |
| **M5** | Primary outcome was called right-censored survival while analysed as capped | REV3 distinguishes observed termination, cap-reaching fraction and capped survival score; the primary is the capped score, not ordinary right-censored survival. A censoring-aware time-to-event analysis is a separately declared sensitivity analysis only | §5.1, §7.6, U3, §11.19 |
| **M6** | The pilot could not estimate the σ that governs N | The governing σ is `σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4)`; the pilot must include B so C2 is estimable; the N decision uses the upper confidence limit and is made before the campaign | §7.1, §7.4, §10.8, U7 |
| **M7** | F/Fβ training budget was 5× too high | Recalculated from 22.345 s/213 updates: F/Fβ training at N = 10 is 1.24–5.25 h, not 6.2–26.2 h. Totals are ≈ 8.9–38.8 h (N = 10) and ≈ 13.9–61.7 h (N = 16) | §9.2, U11 |
| **M8** | The floor was described as two incompatible things (substrate-free and a neural arm) | One substrate-free game-side constant-`NO_ACTION` control policy, measured by replay, costs ≈ 0 simulation; it is never a neural arm, never a condition, never budgeted as a simulation line | §3.6.2, §3.7, §9.2, U10, §11.30 |
| **M9** | H3 was both resolved and open | H3 has exactly one status — **confirmatory** — in the hypothesis register, §5.3, §7, §10 and Appendix C. The underlying U15 decision is marked proposed, not approved; its contingency is stated once in H3's entry | §4, §5.3, §7, §10, §12, Appendix C |

### 2.2 Minor findings

| Audit ID | Finding | REV3 resolution | REV3 location |
|---|---|---|---|
| **m1** | Equal magnitudes described as "most permissive" | Corrected: equal magnitudes are the **least** permissive. Counterexample retained: eight `+10` and two `−0.1` give `|T| = 79.8`, `p = 8/1,024 = 0.0078125`, which passes Holm step 1 at m = 4; equal magnitudes at 8-vs-2 give `p = 112/1,024 = 0.109` | §7.3 |
| **m2** | §5.1 said the primary was averaged "in which the agent is random" | Removed | §5.1 |
| **m3** | §6.8 cross-referenced §7.5 for the episode-level secondary | Corrected to §7.7 | §6.8 |
| **m4** | `NO_ACTION` with motor spikes had no label | Added `bias-driven (incidental)` and `undefined` labels | §3.6.3 |
| **m5** | E4 was undefined at 0/0 but could be read as a pass | E4 is explicitly **undefined (0/0)** and never a pass; E3 fails in the same case | §3.6.4 |
| **m6** | §11.29 quoted only the N = 10 p-floor | Updated to N = 16 (`2/65,536` raw; `8/65,536 = 0.000122` adjusted at m = 4) with the N = 10 fallback stated separately | §11.29, Appendix C |
| **m7** | U1 did not distinguish gate cases | U1 now has five cases: both above floor; both floored; A floored/F above; A above/F floored; both floored with E above. C and D are reported, never gated | U1 |
| **m8** | "Verified sign" undefined | Defined as a non-null predicted-transmitter annotation in the BANC export, not a physiological measurement | §2.1 |
| **m9** | §0 overstated C′ as required; floor absent from §7.1 | C′ is required for D under the working U13(a) but remains proposed; the floor is named in §7.1 and all control-arm tables | §0, §7.1, §3.7 |
| **m10** | Normal-theory MDE presented without the Holm adjustment | Both the unadjusted and Holm step-1 MDE are stated and labelled approximations; the exact power of the sign-flip/Holm combination is not claimed | §7.4, §7.5 |
| **m11** | No arithmetic-parity requirement for the live plastic stepper | §3.8.2a requires an additive `LiveBancStepper` subclass with unchanged accumulation order and dtype, bit-identical current at `eta = 0` | §3.8.2a |

---

## 3. Proposed-decision register U1–U18

All 18 decisions are recorded as **PROPOSED — not approved**. No approval is claimed anywhere, and
the protocol states that no confirmatory implementation step may run before the user records one.

| ID | Proposed decision | Status |
|---|---|---|
| U1 | three gate cases (both floor / A-only floor / F-only floor); C/D reported, never gated; floor substrate-free | PROPOSED — not approved |
| U2 | eta = 0.5 for B/D; no tuning | PROPOSED — not approved |
| U3 | capped survival score `min(updates, 900)` as primary | PROPOSED — not approved |
| U4 | degree-preserving signed rewire as the confirmatory null | PROPOSED — not approved |
| U5 | direct REINFORCE for E; no new dependencies | PROPOSED — not approved |
| U6 | K = 10 | PROPOSED — not approved |
| U7 | N = 16 primary; N = 10 only as the predeclared fallback | PROPOSED — not approved |
| U8 | E-full exploratory and capacity-matched | PROPOSED — not approved |
| U9 | B/D plasticity runs during evaluation | PROPOSED — not approved |
| U10 | floor is a substrate-free game-side control, never a neural arm | PROPOSED — not approved |
| U11 | ≈ 8.9–38.8 h (N = 10) / ≈ 13.9–61.7 h (N = 16); memory gate unchanged | PROPOSED — not approved |
| U12 | no new `learning/` implementation | PROPOSED — not approved |
| U13 | C′ on all N × K at eta = 0 through the actual pathway, same P1–P19 | PROPOSED — not approved |
| U14 | m = 4 including C4 = F − Fβ | PROPOSED — not approved |
| U15 | H3 confirmatory, exactly one status | PROPOSED — not approved |
| U16 | Fβ genuinely state-independent, full N × K | PROPOSED — not approved |
| U17 | evidence thresholds as stated, with 0/0 not evaluable | PROPOSED — not approved |
| U18 | target exchange for the degree-preserving null | PROPOSED — not approved |

The four confirmatory contrasts remain **C1 = F − A**, **C2 = B − A**, **C3 = A − C**,
**C4 = F − Fβ**.

---

## 4. Updated implementation sequence

| Step | Purpose | Inputs | Key acceptance criterion | Depends on |
|---|---|---|---|---|
| 10.0 | protocol approval | REV3 | user approval of §12 recorded | — |
| 10.1 | campaign skeleton (G5) | phase 4H/7 structure | schema validator; idempotent resume; no overwrite | 10.0 |
| 10.2 | condition A | live stepper, drive, decoder, loop | reproduces Phase 7 fingerprint `cca811f3…b2fb` | 10.1 |
| 10.3 | pilot 1 — A viability | 10.2 only | floor status only; **no contrast estimate** | 10.2 |
| 10.4 | condition C + randomisation (G3) | graph invariants | R1–R18 pass, including R9b; BANC scale blocked below memory gate | 10.1 |
| 10.5 | F and Fβ (G2) | torch, decoder | state-independent Fβ; `motor_activity` on 100% of decisions; E4 0/0 not evaluable | 10.2 |
| 10.6 | A′ and C′ (G1) | plastic stepper | exact P1–P19 equality, zero tolerance, hard stop | 10.4, 10.2 |
| 10.7 | B and D (G1) | 10.6 | `eta > 0` changes weights and only weights | 10.6 |
| 10.8 | pilot 2 — variability and controls | all condition builds | `σ_max` with upper limit; A′ ≡ A, C′ ≡ C; B included; predeclared N decision | 10.3–10.7 |
| 10.9 | condition E (G4) | torch, environment | disjoint train/eval seeds; no privileged input | 10.1 |
| 10.10 | campaign (G5) | all conditions | 2 valid seeds; A′/C′ certificates; memory ≥ 4 GB | 10.8, 10.9 |
| 10.11 | analysis (G6) | JSONL | recomputes every §7 number at actual N | 10.10 |
| 10.12 | report and freeze | analysis | forbidden statements absent; E1–E5 gate | 10.11 |
| 10.13 | viability check (G7) | Phase 7 artifact, JSONL | U1 three cases, read-only | 10.12 |

This removes the original circularity: pilot 2 cannot precede the conditions it measures, and
pilot 1 is deliberately limited to A so that it does not claim to estimate a contrast.

---

## 5. Runtime arithmetic (independent recalculation)

Measured base: 22.345 s per 213-update episode ⇒ 94.415 s per capped 900-update episode;
3.724 min per seed for K = 10 at the measured rate, 15.736 min at the worst case.

| Line | N = 10 | N = 16 |
|---|---|---|
| 5 conditions eval | 3.10–13.11 h | 4.97–20.98 h |
| A′ eval (+20–40% plastic overhead) | 0.75–3.67 h | 1.19–5.87 h |
| C′ eval (same) | 0.75–3.67 h | 1.19–5.87 h |
| Fβ eval | 0.62–2.62 h | 0.99–4.20 h |
| F training (20 episodes/seed) | 1.24–5.25 h | 1.99–8.39 h |
| Fβ training (20 episodes/seed) | 1.24–5.25 h | 1.99–8.39 h |
| B/D plastic overhead | 0.25–2.10 h | 0.40–3.36 h |
| random-graph construction | 0.33–2.50 h | 0.53–4.00 h |
| E | < 0.17 h | < 0.17 h |
| floor (game-side) | ≈ 0 | ≈ 0 |
| analysis | < 0.5 h | < 0.5 h |
| **total, single process** | **≈ 8.9–38.8 h** | **≈ 13.9–61.7 h** |

The previous 6.2–26.2 h F/Fβ training figure was exactly 5× the stated assumption: 20 episodes ×
10 seeds × 22.345 s = 4,469 s = 1.24 h at the measured rate, and 20 × 10 × 94.415 s = 18,883 s =
5.25 h at the worst case.

These totals differ slightly from the audit's provisional ≈ 10–42 h (N = 10) and ≈ 16–67 h
(N = 16) because the audit included the floor as if it consumed evaluation time and rounded
per-condition lines differently. The recalculation was performed independently from the measured
rate; neither set was copied from the other. The difference is disclosed rather than suppressed.

---

## 6. Statistical constants and formula verification

| Quantity | N = 16 (primary) | N = 10 (fallback) |
|---|---|---|
| sign vectors | 65,536 | 1,024 |
| minimum one-sided p | 1/65,536 = 0.0000152588 | 1/1,024 = 0.0009765625 |
| minimum two-sided p | 2/65,536 = **0.0000305176** | 2/1,024 = **0.001953125** |
| count threshold for raw p ≤ 0.05 | ≤ 3,276 (0.0499878; 3,277 = 0.0500031) | ≤ 51 (0.049805; 52 = 0.050781) |
| Holm step 1, m = 4 | α/4 = 0.0125; ≤ 819 (0.0124969) | ≤ 12 (0.011719) |
| Holm step 2, m = 4 | α/3 = 0.016667; ≤ 1,092 (0.0166626) | ≤ 17 (0.016602) |
| Holm step 3, m = 4 | α/2 = 0.025; ≤ 1,638 (0.0249939) | ≤ 25 (0.024414) |
| Holm step 4, m = 4 | α = 0.05; ≤ 3,276 | ≤ 51 |
| minimum adjusted p, m = 4 | 4 × 2/65,536 = **0.0001220703** | 4 × 2/1,024 = **0.0078125** |
| minimum adjusted p, m = 3 | 3 × 2/65,536 = **0.0000915527** | 3 × 2/1,024 = **0.005859375** |
| MDE at σ = 60 | 2.801585 × 60 / 4 = **42.024** | 2.801585 × 60 / √10 = **53.155** |
| σ supported for MDE = 100 | 100 × 4 / 2.801585 = **142.78** | 100 × √10 / 2.801585 = **113.05** |
| Holm step-1 normal-theory factor | 2.4977 + 0.8416 = 3.3393 | same |
| Holm step-1 MDE, σ = 60 | 3.3393 × 60 / 4 = **50.09** | 3.3393 × 60 / √10 = **63.36** |

`z₀.₉₇₅ + z₀.₈ = 1.959964 + 0.841621 = 2.801585`. `z` for Holm step 1 is
`z(1 − 0.0125/2) = z(0.99375) = 2.4977`.

Equal-magnitude splits at N = 16: a 13-vs-3 split gives `2 × C(16,≤3) = 2 × 697 = 1,394` of 65,536,
`p = 0.021271` (fails step 1); a 14-vs-2 split gives `2 × 137 = 274`, `p = 0.004181` (passes).
At N = 10, an 8-vs-2 equal-magnitude split gives `p = 112/1,024 = 0.109`.

The MDE table is explicitly labelled a **normal-theory approximation**, not exact power for the
exact sign-flip/Holm combination. Both the unadjusted and step-1 values are shown.

---

## 7. Document-level consistency searches

Searches were run over REV3 after all edits.

| Search target | Result |
|---|---|
| Contradictory N = 10 vs N = 16 | No contradiction. N = 16 is primary; every N = 10 appearance is explicitly the predeclared fallback or a labelled N = 10 basis line in §9.2. |
| "all-plus/all-minus" as the extremal vectors | No stale use. The only occurrences explain that the extremes are `sign(d)` and its negation and that all-plus/all-minus coincide only when all differences share a sign. |
| "right-censored" as the primary outcome | No stale use. Occurrences are explanatory (why the label is rejected) or specify a separately declared sensitivity analysis. |
| "bias-only" vs state-independent | The naming rule permits "bias-only" only for the exact parameter set (feature weights fixed 0, only output biases trainable). U16 says a hidden or state pathway disqualifies the label. |
| Substrate-free floor vs neural-substrate arm | The floor is consistently a substrate-free game-side control; it is never a neural arm, condition or simulation budget line. |
| R9b vs per-source weight sums | Consistent with target exchange: per-source outgoing weight profile preserved; component structure not preserved. |
| H3 status | Confirmatory in §4, §5.3, §7, §10 and Appendix C; U15 remains proposed. No second status. |
| C′ pilot coverage | Pilot 2 and the campaign both use full coverage; C′ is N × K in both. |
| 8.3 ordering | No 8.3 remains. The sequence is 10.3 (A viability) and 10.8 (paired pilot). |
| Four contrasts / Holm m = 4 | C1–C4 are stated consistently; m = 3 is available only as the U14 alternative and removes the decoding claim. |

No unresolved contradiction was found in the searched categories. This is a statement about the
searches listed above, not a claim that REV3 is approved or that implementation gates are closed.

---

## 8. Remaining issues and gates

1. **REV3 is not approved.** All U1–U18 items are proposals. The blocking gate is human approval of
   §12.
2. **REV3 is not execution-ready.** G1–G7 implementation gates remain; see
   `reports/PHASE_8_IMPLEMENTATION_STATUS.md`.
3. **Memory gate.** The latest preflight measured 1,152,972 KB free (≈ 1.1 GB) of 16,087,140 KB,
   below the 4 GB gate. No BANC-scale randomisation, campaign, training or memory-intensive test
   suite may start.
4. **Statistical approximation.** The MDE is normal-theory; the exact sign-flip/Holm power has not
   been computed and is not claimed. The design can detect large effects only.
5. **Scientific scope.** The Phase 6 negative result (−0.0863 bits, p = 0.125, Holm 0.25) is frozen
   and unrevised. The anticipated Phase 8 result is a floor; a floor is reportable and is not
   evidence that plasticity or the connectome "does not work".
6. **Unchanged unknowns.** ROLL and DUCK have no motor population; 414 of 805 motor neurons are
   unassigned; 852,610 of 1,535,710 edges are unsigned and inert; 7 of 14 game features are
   unmapped. These are documented limitations, not defects introduced by REV3.

**Readiness verdict for this correction:** protocol correction complete, all audit findings
addressed in the mapped sections, no searched contradiction outstanding. **REV3 remains NOT
APPROVED and NOT EXECUTABLE** pending human decisions and implementation gates.
