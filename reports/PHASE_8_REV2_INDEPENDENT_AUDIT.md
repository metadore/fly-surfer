# Phase 8 — Independent Audit of Protocol Revision 2

| field | value |
|---|---|
| audited document | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md` |
| audited identity | 1,465 lines; SHA-256 `d6a8964c753984736fcdcf315ca0e8e6af61415afcb79cd5db9cbae45bdab7c0` — **matches the declared identity exactly** |
| audit type | document audit only — no implementation, no execution, no training, no graph randomization, no installs |
| repository | `C:/Users/Hp/fruitfly/FLY-SURFER`, branch `main`, HEAD `efd3a3e5fb8c5c2b241eb988371a6170ae70b4c4` (working tree dirty — preserved, untouched) |
| audit date | 2026-11-16 |
| verdict | **CONDITIONALLY READY — CORRECTIONS REQUIRED** |
| issue counts | 1 critical, 9 major, 10 minor, 12 resolved/verified |

---

## 1. Executive verdict

**CONDITIONALLY READY — CORRECTIONS REQUIRED.**

The scientific design is sound and unusually well disciplined. The six conditions A–F are preserved
without exception; the primary outcome is singular and pre-declared; the control arms A′/C′/Fβ and the
measured floor are the right controls for the three ways this phase could fool itself; the negative
Phase 6 result and the Phase 7 motor floor are represented honestly; every interface used by the
protocol exists and was re-read from source during this audit. Almost every numeric claim
reproduces.

The document is nevertheless **not ready for sign-off**, for one reason of execution planning and
nine of specification:

1. **(Critical)** §10's step 8.3 pilot is impossible in the stated order: it requires conditions C, F,
   Fβ and the A′ control before steps 8.4–8.6 that implement them, and the ordering rationale places
   the pilot *before* those steps. The plan as written cannot be executed.
2. **(Major ×9)** A core statistical explanation is wrong (§7.3 "all-plus and all-minus"), the
   sign-flip validity assumption is never stated, the censored-survival label does not match the
   analysis, the missing-pair rule silently changes N without changing the thresholds, the pilot
   cannot estimate σ for the two contrasts most likely to bind (C2, D−C), the §9.2 training budget is
   5× its own stated assumption, the floor arm is described two incompatible ways, §11.23 contradicts
   the revised §3.3/R9b, and H3's confirmatory status is simultaneously "resolved" and "open".

None of these invalidates the scientific design. All are correctable in a REV3 without new evidence.
The verdict separates four readiness questions, which are **not** the same:

| Question | Answer |
|---|---|
| Is the document correct? | Almost — 1 critical, 9 major, 10 minor corrections required |
| Is the scientific design ready? | Yes, conditionally: the design is coherent once the specification corrections are made |
| Is the technical implementation ready? | **No** — G1–G7 are all real gaps, none implemented (as §0 states) |
| Is execution ready? | **No** — sequencing contradiction; memory pre-flight currently fails; no code exists |
| Is human approval ready? | **No** — REV3 corrections plus explicit decisions on all 18 U-items are required |

---

## 2. Document identity verification

| Document | Expected | Measured | Match |
|---|---|---|---|
| REV2 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md` | 1,465 lines; `d6a8964c753984736fcdcf315ca0e8e6af61415afcb79cd5db9cbae45bdab7c0` | 1,465 lines; `d6a8964c…bdab7c0` | **exact** |
| V1 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` | preserved byte-identical (claim) | 888 lines; `d9d13a6c312b1c536a0d9266ade4ad81c47bdc99192d6f8d53816d81813fc505` | consistent with REV2's own citation `d9d13a6c…fc505` |
| Change log `docs/PHASE_8_PROTOCOL_REV2_CHANGELOG.md` | not cited with a hash in REV2 | 125 lines; `b4a5dba7874b8b1371843b7d76bb66254bd8ab156d9241abc979d107896192e9` | n/a — not used as evidence |

The audited document is authoritative. The change log was **not** used to establish any fact; every
claim below was checked against REV2 itself and, where it concerns the repository, against source.

Repository metadata read (read-only, explicitly required by §1 of the audit brief):

- `git rev-parse --show-toplevel` → `C:/Users/Hp/fruitfly/FLY-SURFER`
- `git rev-parse --abbrev-ref HEAD` → `main`
- `git rev-parse HEAD` → `efd3a3e5fb8c5c2b241eb988371a6170ae70b4c4`
- working tree dirty (modified `environment/subway_environment.py`; untracked `environment/`,
  `experiments/phase_7/`, `experiments/results/phase_7/`, `configs/phase_7_*.yaml`,
  `datasets/processed/banc_v888/`, `datasets/external/`, the Phase 8 documents) — matches §2.4.

No Git operation beyond these read-only queries was performed. The target report
`reports/PHASE_8_REV2_INDEPENDENT_AUDIT.md` did not exist (the `reports/` directory did not exist);
no prior report was overwritten.

---

## 3. Original-roadmap alignment

Source read: `docs/PROJECT_VISION.md` lines 1443–1477 (Phase 8) and 1478–1485 (Phase 9), plus the
dependency list at line 2184.

**Objective preserved.** The roadmap's Phase 8 goal is "Conduct the main scientific experiments",
with ten tasks: train the plastic network, test the fixed network, test randomised networks, test a
conventional AI baseline, compare performance across episodes, analyse firing patterns, analyse
weight changes, analyse information measures, record configurations, generate graphs and reports.
REV2 §1.1 reproduces this list; §3, §5, §7 and §10 map onto all ten.

**All six conditions preserved.** A (biological, fixed), B (biological, plastic), C (random, fixed),
D (random, plastic), E (conventional ANN), F (biological + trainable readout) all appear with the
intended contrasts. No condition was removed, merged, or replaced by a demonstration. Phase 8 is
still training-and-comparison; Phase 9 is still the browser-game deployment, and REV2 §12 U1
explicitly forbids folding a Phase 9 scope change into Phase 8.

**No unsupported biological claim.** The scientific status declaration (§56–68) states that no
measured claim is made about fly learning, motor control, gameplay competence, or biological
dopamine. §11.1–15 restate the model's limits. The forbidden-statement list (§3.6.5) is binding.

Documented deviations (all disclosed, none silent):

| # | Roadmap | REV2 | Assessment |
|---|---|---|---|
| D1 | `experiments/baseline/` | `experiments/phase_8/` to avoid the existing 526-line `experiments/baseline.py` (Phase 2) | justified; verified the collision is real |
| D2/D3 | `experiments/connectome/`, `experiments/plasticity/` | reuse `experiments/phase_4h/common.py`, `plasticity/` + `experiments/phase_5/` | justified |
| D4 | `experiments/random_network/` | absent; new `experiments/phase_8_random/` | a real gap (G3), not cosmetic |
| D5 | `src/fly_surfer/evaluation/` | no `src/` tree; new top-level `evaluation/` | forced by repository reality |
| D6 | Stable-Baselines3 dependency | not installed; U5 recommends direct REINFORCE | **deviation from the roadmap's stated dependency**; disclosed and justified |
| D7 | "analyse information measures" | descriptive only, because Phase 6 is negative and frozen | **scope reduction**, disclosed; defensible |
| D8/D9 | multi-episode comparison; randomised networks | single-episode runners only; 32-node fixture only | gaps G5/G3, disclosed |
| D10 | conventional baseline | Phase 5F perceptron is `privileged: true`, `matched_control: false`; E must be rebuilt | gap G4, disclosed |

**One role change worth naming explicitly.** The roadmap treats E as a comparison condition; REV2
demotes its interpretation to "explanatory reference" because E-matched is not a matched control
(§11.24) and because 7 of 14 features are unmapped. E is still run as the roadmap requires; only its
inferential role is narrowed. This is disclosed in §3.5, §5.4 and §11.24 and is scientifically
correct — a supervised/privileged baseline cannot license a like-for-like comparison. It is listed
here as a deviation so it is not mistaken for a silent change.

No deviation changes the scientific objective. Phase 8 remains the training-and-comparison phase.

---

## 4. Statistical recalculation

Every quantity below was recomputed independently from the definitions, not copied from REV2.
`C(n,k)` denotes a binomial coefficient.

### 4.1 Exact sign-flip constants

| # | Quantity | REV2 | Independent value | Verdict |
|---|---|---|---|---|
| S1 | sign vectors at N = 10 | 1,024 | 2^10 = 1,024 | match |
| S2 | minimum one-sided p | 1/1,024 = 0.0009765625 | 0.0009765625 | match |
| S3 | minimum two-sided p | 2/1,024 = 0.001953125 | 0.001953125 | match |
| S4 | which vectors attain the extreme \|T\| | "all-plus and all-minus" (§7.3, Appendix C) | `s_i = sign(d_i)` and its negation | **MISMATCH — Major M1** |
| S5 | raw-p count threshold at α = 0.05 | ≤ 51 of 1,024 | 51/1,024 = 0.0498047; 52/1,024 = 0.0507813 | match |
| S6 | N = 16 assignments | 65,536 | 2^16 = 65,536 | match |
| S7 | N = 16 minimum two-sided p | 2/65,536 = 0.0000305176 | 0.000030517578125 | match |

On S4: the statistic is `T(s) = Σ sᵢdᵢ`. Its maximum is `Σ|dᵢ|`, attained exactly when
`sᵢ = sign(dᵢ)`; its minimum is `−Σ|dᵢ|`, attained at `sᵢ = −sign(dᵢ)`. "All-plus" is
`sᵢ = +1` for every i, which yields `T = Σdᵢ = T_obs`, not the maximum, unless every observed
difference already has the same sign. The **count is still 2** (the pair ±sign(d) is always two
distinct vectors when not all `dᵢ = 0`; the all-zero case is handled by the declared tie policy,
§7.3), so **S3, S5, S7 and every derived Holm number are unaffected**. The error is one of
explanation, not arithmetic — but the brief is right that it must be corrected, because it teaches
the wrong mechanics of the test.

### 4.2 Holm–Bonferroni

| # | Quantity | REV2 | Independent value | Verdict |
|---|---|---|---|---|
| H1 | m = 4 step 1 threshold | 0.0125 | 0.05/4 = 0.0125 | match |
| H2 | m = 4 step 1 count | ≤ 12 | 12/1,024 = 0.011719 ≤ 0.0125 < 13/1,024 = 0.012695 | match |
| H3 | m = 4 step 2 | 0.016667, ≤ 17 | 0.05/3 = 0.0166667; 17/1,024 = 0.016602 < 18/1,024 = 0.017578 | match |
| H4 | m = 4 step 3 | 0.025, ≤ 25 | 0.025; 25/1,024 = 0.024414 < 26/1,024 = 0.025391 | match |
| H5 | m = 4 step 4 | 0.05, ≤ 51 | 0.05; 51/1,024 = 0.049805 | match |
| H6 | m = 4 minimum adjusted p | 0.0078125 | 4 × 0.001953125 = 0.0078125 | match |
| H7 | m = 3 step 1 | 0.016667, ≤ 17 | same as H3 | match |
| H8 | m = 3 minimum adjusted p | 0.005859375 | 3 × 0.001953125 = 0.005859375 | match |

### 4.3 Equal-magnitude examples (N = 10, all |dᵢ| = 1)

For a sign split k:1−k, `|T| ≥ |T_obs|` requires at most |1−k| sign mismatches (or their complements),
so the count is `2 · Σ_{j=0}^{min(k,10−k)} C(10,j)`.

| Split | Count | p | REV2 | Verdict |
|---|---|---|---|---|
| 10/0 | 2 | 0.001953 | 2/1,024; survives even Holm step 1 | match |
| 9/1 | 2·(1+10) = 22 | 22/1,024 = 0.021484 | 0.0215; fails step 1 (0.0125 and 0.016667) | match |
| 8/2 | 2·(1+10+45) = 112 | 112/1,024 = 0.109375 | 0.109; fails outright | match |

"Only a unanimous 10-of-10 separation survives under equal magnitudes" is correct.

### 4.4 Power, sample size, and the pilot

Formula check: `z₀.₉₇₅ + z₀.₈₀ = 1.959964 + 0.841621 = 2.801585`.

| # | Quantity | REV2 | Independent value | Verdict |
|---|---|---|---|---|
| P1 | MDE at N = 10, σ = 60 | ≈53 (53.155) | 2.801585 × 60/√10 = 53.1545 | match |
| P2 | σ supported at N = 10 for MDE = 100 | ≈113 | 100√10/2.801585 = 112.87 | match |
| P3 | MDE at N = 16, σ = 60 | ≈42 | 2.801585 × 60/4 = 42.024 | match |
| P4 | σ supported at N = 16 for MDE = 100 | ≈143 | 400/2.801585 = 142.78 | match |
| P5 | 80% one-sided UCL factor for σ at df = 2 | ≈2.1× | `P(χ²₂ ≥ q) = 0.8 ⇒ q = −2ln0.8 = 0.44629`; `U = s√(2/q) = 2.11694 s` | match |
| P6 | implied σ and N | ≈142 updates; N ≈ 16 | 2.11694 × 67.3 = 142.5; `(2.801585 × 142.5/100)² = 15.93 ⇒ 16` | match |
| P7 | escalation `N = ⌈(2.8016σ/100)²⌉` | — | at σ = 113.0 → 10.02 → 11 (rule fires only above 113) | internally consistent |
| P8 | power/MDE adjusted for Holm | not stated | MDE is the *unadjusted* per-contrast value; the step-1 threshold 0.0125 corresponds to z ≈ 2.50, giving an effective step-1 MDE ≈ 68 | **GAP — Minor m10** |

On P8: at N = 10 the test is discrete and Holm orders contrasts by raw p, so the *family-adjusted*
power for the first step is lower than 80% at the stated MDE. §11.21 already says "this design can
detect large effects only", so this is a labelling gap rather than a false claim. The MDE row should
say "unadjusted" and give the step-1 value.

### 4.5 Sign-flip assumptions

The mechanics in §7.3 are correct, but the **validity assumptions are not stated anywhere**:

- **Symmetry / exchangeability.** The sign-flip test is exact under the null that each paired
  difference `dᵢ = X_{B,i} − X_{A,i}` is symmetric about zero (equivalently, that the condition
  labels are exchangeable within seed). Conditions A and B are deterministic procedures, not randomly
  assigned treatments, so this is an assumption about the difference distribution, not a design
  guarantee. It should be declared, with the two-sided exact sign test (§7.3) as the robustness check.
- **Independence of seeds.** §6.3's separate seed streams make seeds independent by construction;
  §7.2 correctly makes the seed the unit. This is implied but never stated as a test assumption.
- **No within-seed dependence in the primary test.** K = 10 episodes are averaged before the test
  (§6.8, §7.2), which is correct; the episode-level bootstrap is properly labelled secondary.

**Recommendation:** add one paragraph to §7.3. This is Major M2.

### 4.6 Censoring and the survival cap

The outcome is defined as "right-censored at the 900-update truncation cap" (§5.1), but the
confirmatory analysis is a sign-flip test on the per-seed **mean of capped values** (§7.2), with no
censoring-aware estimator (Kaplan–Meier, log-rank, Cox, or a censoring-sensitive permutation). A
capped value treated as fully observed is a bounded score, not a censored observation. With the
Phase 7 baseline at 213 updates censoring is rare, but censoring becomes common precisely if a
condition improves — the case the experiment exists to detect — and conditions with different
censoring rates are then compared on an unequal footing.

This is a **label–analysis mismatch** (Major M5), correctable either way:

- (a) rename the outcome "updates survived, capped at 900" (a bounded score) and keep the exact test
  as the primary, adding the censoring rate per condition as a mandatory secondary; or
- (b) keep the survival language and pre-specify a censoring-aware sensitivity analysis (KM medians
  and a permutation log-rank-type statistic at the seed level).

Either is defensible; the document currently does neither.

### 4.7 Missing pairs and the multiplicity thresholds

§7.6 allows a whole seed×condition cell to error and says the primary uses "complete pairs only".
Dropping one pair changes the enumeration from 2^10 = 1,024 to 2^9 = 512, which changes **every**
threshold in §7.3 and §7.5:

| N (complete pairs) | assignments | min two-sided p | raw ≤ 0.05 count | Holm m=4 min adjusted p |
|---|---|---|---|---|
| 10 | 1,024 | 0.001953 | ≤ 51 | 0.0078125 |
| 9 | 512 | 0.003906 | ≤ 25 | 0.015625 |
| 8 | 256 | 0.007813 | ≤ 12 | 0.03125 |

REV2 does not state that the analysis must recompute the thresholds at the reduced N, nor that the
attainable floor degrades. It should. This is Major M4 (and it is not hypothetical: §7.6 explicitly
anticipates a cell error).

### 4.8 Independent units and confidence intervals

- Unit of analysis = seed; K-averaged within seed; episode-level as secondary (§7.2, §6.8) — correct.
- Paired seeds via `derive(master, s, j, "env")`, independent of condition (§6.2) — correct.
- Paired percentile bootstrap over seeds, labelled approximate at N = 10, with the exact attainable
  interval printed (§7.7) — correct and unusually honest.
- Two-level cluster bootstrap for the episode-level estimate (§7.7) — correct.
- Cohen's dz and win/loss/tie counts — correct.

No correction required in this subsection beyond M4/M5.

---

## 5. Six-condition and control audit

### 5.1 A and A′

| Requirement | Finding |
|---|---|
| A′ implemented through the real plasticity pathway with eta exactly 0 | **Specified correctly.** §3.8.2 requires `eta` exactly `0.0` (not `1e-12`, not a skip flag), the rule to execute and return an exact zero delta, with a documented alternative short-circuit recorded as `plasticity_path.mode`. Supported by `plasticity/config.py`'s `fixed_mode_eta == 0.0` contract. |
| Comparison fields observable | **Yes, all 19.** P1–P2 come from `recorder.spike_times_ms` / `spike_neuron_indices`; P3–P4 from `episode_fingerprint`; P5 from `records[]`; P6–P9 from `summary`; P10 from the new `motor_activity` block; P11–P17 from `WeightState.digest()` / `describe()`; P18 from `LiveBancStepper.weight_fingerprint()`; P19 from `stepper.resets`. Every one exists in current source (App. A). |
| Hashes and exact equality technically meaningful | **Yes, with one condition not stated.** P3/P4/P18 are SHA-256 over arrays; exact equality is meaningful. P1/P2/P5 are bit-level comparisons of float-producing code. Exact identity across the *same* kernel is achievable; exact identity across a re-implemented kernel is not guaranteed. The document does not require the live plastic stepper to reuse `LiveBancStepper`'s accumulation order and dtype. Since §10 8.6 already specifies an "additive subclass", the fix is one sentence: **the subclass must apply weight deltas only and must not alter the parent's current-accumulation order or precision.** Minor m11. |
| Fresh-process comparisons | **Specified** for A′ episode 1 per seed (§3.8.2) and for the E5 ablation (fresh-process rerun). Adequate. |
| Hard-stop rule unambiguous | **Yes.** §3.8.5: first mismatch stops A′, B is marked INVALID and retained, no seed shopping, two named conclusions, (b) requires explicit user approval. This is a model of how to write a stop rule. |

### 5.2 B and D

| Requirement | Finding |
|---|---|
| Online plasticity during evaluation consistently specified | **Yes.** §3.2 row 9 and §6.7 say plasticity runs *during* evaluation for B/D, and §6.7's correction explicitly replaces V1's false "no evaluation episode may update anything". |
| Update timing | Neural step matching the game update; `delta_w = eta · M(t) · e(t)`; 5 pA/update cap; bounds 0.5–2.0× initial; clamps recorded. Reproducible. |
| Reward timing | `GameRewardFunction.schedule(delay_ms)` → `ModulationRewardProvider`; gain 1.0, τ 50 ms, clip ±5; delivered at the matching neural step; delay recorded per delivery. Reproducible. |
| Eligibility traces | τe = 20 ms, delay-matched coincidence, prune 1e-4 every 50 steps, signed edges only. Reproducible. |
| Training/evaluation distinction | **Correct.** A–D have no training phase; the online change *is* the measurement (U9). |
| Residual issue | The pilot does not include B or D (§10 8.3), so σ for C2 (B−A) and D−C cannot be estimated before N is fixed (Major M6). |

### 5.3 C and C′

| Requirement | Finding |
|---|---|
| Random graph construction fully specified | **Yes after REV2.** Directed double-edge swaps; duplicates and self-loops rejected; `structure` stream; one graph `G_s` per seed shared by C, D, C′; target-exchange parameterisation recommended (U18), with endpoint re-pairing as the alternative. |
| Degree and transmitter-sign properties preserved | In/out degree exact; signs exact (identities not permuted); weight multiset exact; per-source outgoing weight multiset exact under U18(a) (R9b). |
| Edge weights and source-associated properties | Weight travels with the edge; per-source profile preserved under U18(a). |
| R1–R18 measurable | **Yes.** Every gate is an explicit, computable quantity with a stated threshold. R1–R3, R15, R16 are report-only by design; R4–R14 and R17 gate; R18 is a derivation record. |
| Swap parameterisation / target-exchange internal consistency | **Consistent within §3.3/§3.3.1/U18** — but **§11.23 still says per-neuron outgoing weight sums are *not* preserved**, contradicting §3.3 and R9b (Major M3). |
| Strict rewiring, Jaccard, neighbourhood overlap, mixing gates feasible | **Yes.** With 99% rewiring, mean out-neighbourhood Jaccard ≈ 0.0006 (≪ 0.01) and edge-set Jaccard ≈ 0.01; degree preservation holds by construction. R14's plateau test is cheap (O(E) per checkpoint). The 2–15 min/graph figure is an **assumption** (§9.2) and remains unverified. |
| Failure handled without relaxing thresholds | **Yes.** §3.3.1 rejection protocol: reject the graph, halt the seed, allow a new seed, forbid a relaxed gate. |
| C′ genuinely bias-free | C′ is C through the plastic path at eta = 0 and must equal C exactly. Conditional on U13. §0 calls all three arms "now required" while C′ is still proposed (Minor m9). |

### 5.4 E

| Requirement | Finding |
|---|---|
| Genuinely matched baseline | **Only partially, and disclosed.** E-matched receives the same 7 features, the same environment and the same action vocabulary, but it is not matched to the neural conditions in credit assignment, sample budget or architecture. REV2 labels it an explanatory reference, not a matched control (§11.24), which is the honest resolution. |
| Capacity matching for E-full | Required by U8 ("same architecture and training budget") — correct. |
| E's role | H4 ("E-matched > no-action floor") is an explanatory reference, not confirmatory. Consistent with §4/§5.4. |

### 5.5 F and Fβ

| Requirement | Finding |
|---|---|
| Can F learn through motor activity? | **Yes, in principle.** The readout's only input is per-decision motor-population activity (§3.6 row 6), so any state-dependence is motor-driven by construction. The Phase 7 measurement (0 motor spikes) predicts the input will be identically zero, in which case F collapses to Fβ — exactly what the control is for. |
| Can its bias learn constant actions? | **Yes** — and this is now explicitly the failure mode the protocol guards against (§3.6 row 11, §3.6.2, U16). This was the central V1 gap and REV2 closes it. |
| Is Fβ genuinely bias-only? | **Yes.** Zero input vector, only the bias trains, same architecture/optimizer/seeds; the gate in §10 8.5 checks "Fβ input vector identically zero". |
| Are the two training procedures comparable? | **Yes** — identical except the feature path. |
| Is the motor-feature ablation correctly defined? | **Mostly.** Zero the motor features, recompute logits from frozen parameters, no retraining/rollout. One undefined case: a `NO_ACTION` decision with spikes present is neither "motor-driven" (no chosen-action population) nor "undefined" as defined (Minor m4). |
| Can the evidence distinguish (1) beating a constant policy, (2) causal dependence on motor activity, (3) actual learning benefit? | **Yes, as three separate statements:** C1/E2 (`F − A`) answers (1)-adjacent "learned decoder beats fixed rule"; C4/E1 (`F − Fβ`) answers (2); E3–E5 add the mechanism requirements; the report is forbidden from merging them (§3.6.5). The three-level separation is explicit and correct. |
| E1–E5 thresholds | E1/E2 are Holm-surviving contrasts (coherent). E3 (≥1 spike on ≥1% of decisions, in ≥ half of seeds) is deliberately low and appropriate for a zero-spike regime. E4 (≥10% of non-`NO_ACTION` decisions motor-driven) has an undefined 0/0 case (Minor m5). E5 (fresh-process reproduction) is meaningful. |
| Positive F result auto-interpreted as neural learning? | **No.** §3.6.4 forbids any neural-learning claim if E3 fails, and §3.6.5 forbids "the connectome learned", "the readout succeeded" when Fβ matches, and "F beat the baseline" without naming the baseline. This is the correct standard. |

---

## 6. Decision register U1–U18

Status legend: **R** = recommendation only (none approved); every item still requires explicit human
approval. "Consistent?" refers to REV2 as a whole, not to §12 alone.

| ID | Decision (exact) | Answer given in REV2 | Unambiguous? | Consistent? | R/approved | Dependency / note |
|---|---|---|---|---|---|---|
| U1 | What to do if the pilot confirms the floor | (b) stop, report floor + pathology decomposition, request scope decision; (d) a refinement of (b) once E exists; (c) is Phase 9 | Partly — gate is "zero non-`NO_ACTION` in A **and** F"; the asymmetric case (A floors, F acts) is unstated; C is piloted but not gated | Yes | R | Blocks 8.3/8.8; Minor m7 |
| U2 | eta for B and D | (a) reuse Phase 5's 0.5 | Yes | Yes (§3.2, Appendix C) | R | Blocks 8.6 |
| U3 | Primary outcome | (a) censored survival in updates | Yes as a choice; the label/analysis mismatch is M5 | Yes (§5.1) | R | Blocks 8.9; M5 |
| U4 | Random-null scope | (a) degree-preserving confirmatory; (b) component-preserving exploratory; (c) sign-randomized exploratory | Yes | Yes (§3.3) | R | Blocks 8.4 |
| U5 | Condition E implementation | (a) direct REINFORCE against the 5-tuple API; no installs | Yes | Yes (D6) | R | Blocks 8.7 |
| U6 | Evaluation episodes per seed K | (a) K = 10 | Yes | Yes (§6.8, §7.1 — except the wrong cross-ref, m3) | R | Blocks 8.8 |
| U7 | Number of seeds N | (b) N = 16 default; (a) N = 10 only if justified | Yes | Yes (§7.1, §7.4, §10, Appendix C) | R | Depends on 8.3 pilot σ; M6 |
| U8 | E-full (14 features) | (a) yes, exploratory, capacity-matched | Yes | Yes (§3.5, §11.24) | R | Blocks 8.7 |
| U9 | B/D online vs train-then-freeze | (a) online primary; (c) if budget allows, with (b) exploratory and held-out seeds | Yes | Yes (§3.2, §6.7) | R | Blocks 8.6 |
| U10 | No-action baseline | (b) as a control arm, **measured** by replay | Yes as a decision; the substrate wording conflicts with §3.6.2 (M8) | Partly — M8 | R | Blocks 8.3; M8 |
| U11 | Compute budget ceiling | (a) accept §9.2 ≈19–78 h; (c) parallelise only after the pilot | Yes | Yes, but §9.2 arithmetic is wrong (M7) | R | Blocks 8.8; M7 |
| U12 | May Phase 8 write a new `learning/` implementation | (a) keep the three placeholders untouched | Yes | Yes (verified: each is a 1-line file) | R | Blocks 8.6/8.7 |
| U13 | C′ mirror for D | (a) full C′ on all N×K | Yes | Yes (§3.7, §7.1, §9.2) — but §0 overstates it as "required" (m9) | R | Depends on U11; blocks 8.6 |
| U14 | Confirmatory family size | (a) m = 4 with C4 | Yes | Yes (§5.3, §7.3, §7.5, §11.29, Appendix C) | R | Interacts with U15, U16; M9 |
| U15 | Confirmatory status of H3 | (a) H3 confirmatory | Yes as a decision, but §4/notice item 5 present it as resolved (M9) | Substantively yes (H3↔C1 everywhere) | R | Determines m via U14 |
| U16 | Scope of Fβ | (a) all N×K, full training, if m = 4 | Yes | Yes (§7.1, §9.2) | R | Depends on U14 |
| U17 | E3/E4 thresholds | (a) 1% of decisions / 10% motor-driven | Yes | Yes (§3.6.4) | R | Blocks 8.5; m5 |
| U18 | Swap parameterisation | (a) target exchange | Yes | Yes in §3.3/§3.3.1/U18; contradicted by §11.23 (M3) | R | Blocks 8.4; M3 |

**No item is approved.** Wording such as "recommendation" was not read as approval. Every U-item
still requires an explicit human decision, and the §12 heading "Unresolved decisions requiring
approval" is accurate.

**Approval ordering implied by the dependencies (for the human reviewer):** freeze U18, U4, U1, U10
before 8.3/8.4; U2, U9, U12, U13, U17 before 8.5–8.6; U5, U8 before 8.7; U6, U7, U11 before 8.8;
U14, U15, U16 together (they are coupled); U3 before 8.9.

---

## 7. Four-contrast and Holm family audit

| ID | Contrast | Hypothesis | Outcome | Control | Belongs in the family? |
|---|---|---|---|---|---|
| C1 | F − A | H3 readout sufficiency | mean capped survival (per seed) | A: same substrate, fixed decoder | Yes — one of the phase's three questions; pre-declared; paired |
| C2 | B − A | H1 plasticity on the biological substrate | same | A, made code-path-matched by A′ ≡ A | Yes — the phase's central plasticity question |
| C3 | A − C | H2 biological vs degree+sign-matched random wiring | same | C, same `G_s` per seed | Yes — the connectivity-specificity question |
| C4 | F − Fβ | whether F's readout uses motor information at all | same | Fβ: best constant policy | Yes, *given* U14(a) and U16(a); without it C1 is not identifiable |

**Family coherence.** All four are two-sided, paired at the seed level, on the identical primary
outcome, under one family-wise α = 0.05 with Holm. Holm controls FWER under arbitrary dependence, so
the fact that C1 and C4 both involve F does not violate the family. Each contrast has a distinct
hypothesis, a defined outcome and an appropriate control. The family matches the project's scientific
objective (plasticity, biological specificity, readout sufficiency, readout state-dependence).

**Internal consistency of the family size.** §5.3, §7.3, §7.5, §11.29, §12.1/U14, §10 8.9 and
Appendix C all state m = 4 as primary with m = 3 as the alternative. **No section retains m = 3 as
the sole family.** The stale "Holm m = 3" in Appendix C was corrected before this audit; the current
Appendix C says "m = 4 (C1–C4) pending U14; m = 3 if U14 selects it". ✔

**H3 status.** Substantively consistent (§4 maps H3→C1, §5.3 labels C1 as H3, §7.3 tests C1). But
the *status* is stated three ways: the revision notice item 5 says the contradiction "is resolved";
§4 says "the labels are binding" and H3 "is confirmatory"; U15 says it is an open decision. The
document's own rule ("None is applied", §12) makes U15 authoritative, so §4 and the notice are
premature. This is Major M9 — it matters because H3's status sets m, which sets every Holm threshold.

**Interpretation guard.** §5.3 correctly states that if U14 selects m = 3, C4 is demoted and **no
decoding claim may be made at all**, because §3.6.4 requires a Holm-surviving test. That is the
correct coupling and removes the temptation to "look at C4 anyway".

---

## 8. Technical feasibility G1–G7

All source was read, not assumed. No test was executed in this audit (see §15).

| Gate | Required capability | Existing implementation (verified) | Missing work | Verifiable acceptance test | Verdict |
|---|---|---|---|---|---|
| G1 | Incremental plastic stepping with `advance_to_step` / `step_index` / `weight_fingerprint` | `PlasticSimulator` is batch-only: `reset()` at `plasticity/plastic_simulator.py:221`; `run()` at `:243` calls `self.reset()` at `:253`; no `advance_to_step`, no `step_index`, no fingerprint. `PlasticityEngine.observe_step` (`plasticity/engine.py:113`) and `learn` (`:151`) do expose per-step hooks. | Additive `plasticity/live_stepper.py` subclassing `LiveBancStepper`, applying `WeightState` deltas per neural step in the parent's order; must not edit `PlasticSimulator`. | `eta = 0` reproduces the `LiveBancStepper` spike stream bit-for-bit on a 5-update episode; `eta > 0` changes only weights; `weight_fingerprint()` differs iff eta > 0; `resets` semantics match. | **REAL GAP — feasible (medium)** |
| G2 | Live trainable readout replacing the fixed decoder | `NeuralClosedLoop.run` calls `decode_trailing_window(self.action_decoder, …)` unconditionally at `environment/live_loop.py:600`; `record["decoder"]` is `None` when the decoder returns `None`. No readout module exists (`readout/` absent). | Readout module, motor-feature builder independent of the decoder, REINFORCE training loop, per-decision `motor_activity` block, ablation counterfactual. | Connectome fingerprint equal before/after; trainable parameter set == readout parameters; `motor_activity` present on 100% of decisions in every condition; Fβ input vector identically zero. | **REAL GAP — feasible (medium)** |
| G3 | Degree- and sign-preserving random null at t5 scale, with valid CSR invariants | Only `plasticity/synthetic.py::synthetic_graph` (n_nodes = 32 test fixture, `:35`). No BANC-scale generator. | `experiments/phase_8_random/`: directed double-edge swap (target exchange, U18), duplicate/self-loop rejection, CSR rebuild, R1–R18 reporter. | All R1–R18 pass on a generated graph; R17 gives byte-identical `edge_src`/`edge_dst`/`edge_weight` for two constructions from one seed; ≤ 15 min/graph (assumption to be measured). | **REAL GAP — feasible, runtime unverified** |
| G4 | Matched conventional baseline | Phase 5F perceptron is `privileged: true` (`experiments/phase_5/comparative.py:978`), `matched_control: false` (`:718`); no Gymnasium/SB3 (`§2.3`). | `evaluation/` MLP (2×64 tanh, 4 logits), REINFORCE against the existing 5-tuple, 7-feature builder. | Trains on training seeds, evaluates on disjoint seeds; no privileged input reaches the model; E-full uses the same architecture and budget. | **REAL GAP — feasible (medium)** |
| G5 | Multi-episode, multi-seed campaign harness | Only `experiments/phase_5/controlled_task.py::run_spiking_episode` at `:300` — one episode per call. | `experiments/phase_8/`: config loader, JSONL writer, manifest, resume, error capture, seed derivation. | A 1-update dummy episode round-trips through the schema validator; a 2-seed dry run produces a valid artifact set. | **REAL GAP — feasible (medium)** |
| G6 | Phase 8 analysis layer | None (`experiments/phase_8*`, `evaluation/` absent). `information/` exists for descriptives. | `analyse_phase_8.py`: exact sign-flip (two-sided, count-thresholded), Holm m = 4/3, bootstrap, effect sizes, floor decomposition, F/Fβ/A decomposition, E1–E5 checklist. | Reproduces every §7 number from the JSONL, no hand-entered values; E1–E5 emitted as pass/fail. | **REAL GAP — feasible (small)** |
| G7 | Viability check that a neural condition can act | None. Phase 7 measured 2,852 spikes, 0 motor spikes, 213/213 `NO_ACTION` (`experiments/results/phase_7/neural_closed_loop.json`). | A pilot gate that counts non-`NO_ACTION` actions in A and F on the paired seeds. | Detects the Phase 7 floor from the stored artifact without tuning any parameter. | **REAL GAP — feasible (small)** |

**Specific determinations requested by the brief:**

- **B/D incremental plasticity in the live loop:** not present; feasible via the additive subclass
  (G1). `PlasticityEngine` already exposes the per-step hooks; the missing piece is orchestration.
- **F trainable readout:** not present; feasible (torch is installed and already used by the Phase 3B
  detector path; A–D do not require torch).
- **C/D random graph generation and validation:** not present at scale; feasible with a seeded
  swap chain; the 2–15 min/graph figure is **UNVERIFIED**.
- **E genuinely matched:** no; it is matched on observations only, and REV2 correctly refuses to call
  it a matched control.
- **Campaign harness reproducibility:** not present; the seed-stream design (§6.3) is sound and the
  harness is straightforward, but nothing can be executed today.
- **Phase 8 analysis metrics:** not present; all are computable from the proposed JSONL.
- **Viability check:** not present; it is the cheapest and most decisive of the seven gaps, and the
  Phase 7 artifact already demonstrates why it is needed.

**A′ exactness feasibility.** P1–P19 are meaningful *provided* A′ and A run the same numerical
kernel. §3.8.1 explicitly anticipates "different data structures, different arithmetic order,
different float32/float64 casts" — but exact bit-identity is not generally preserved across
different accumulation orders. The protocol should require the live plastic stepper to be a
delta-applying subclass of `LiveBancStepper` that does not change the parent's current accumulation
order or precision. Without that sentence, P1/P2/P5/P9 can fail on a benign rounding difference and
trigger the hard stop (Minor m11).

---

## 9. Experimental sequence and budget audit

### 9.1 Sequence 8.0–8.10

| Step | Deliverable | Gate | Audit finding |
|---|---|---|---|
| 8.0 | Protocol approval + freeze | user approval of §12 | Correct; nothing downstream is authorised today |
| 8.1 | Campaign skeleton | schema validator; dummy round-trip | Sound |
| 8.2 | Condition A | reproduces Phase 7 fingerprint `cca811f3…b2fb` on seed 42 | Sound; Phase 7 fingerprint verified in the artifact |
| 8.3 | Pilot: 3 seeds × {A, C, F, A′, Fβ} × 3 episodes; "reuses 8.1–8.2" | measures σ_paired; A′ ≡ A on all 3 seeds | **CRITICAL C1** — C is implemented in 8.4, F/Fβ in 8.5, A′ in 8.6. The pilot cannot run where it is placed, and the ordering rationale explicitly says "the pilot before C/F/B/D" |
| 8.4 | Condition C + validator | all R1–R18 pass | Depends on U18; 8.3's A′ gate also expects C to exist (C1) |
| 8.5 | F + Fβ | fingerprint unchanged; 100% motor_activity; Fβ input zero | Depends on U17 |
| 8.6 | B, D, A′ (+C′ if U13) | A′ ≡ A on every seed/episode, 19 fields, zero tolerance | A′ is built here but is required by 8.3 (C1) |
| 8.7 | E | disjoint train/eval seeds; no privileged input | Sound; depends on U5/U8 |
| 8.8 | Campaign | 2 seeds valid before full run; A′/C′ reports per seed | Sound; depends on U6/U7/U11 |
| 8.9 | Analysis | reproduces every §7 number from JSONL | Sound; depends on M4/M5 |
| 8.10 | Report | integrity 36/37; forbidden statements absent; readout claim only if E1–E5 | Sound |

**Can the pilot invalidate later work?** Yes: a floored A triggers U1(b) and stops the campaign. That
is the point. But placing the pilot *after* the expensive implementations maximises the wasted
effort. The fix is to split it:

- **8.3a (after 8.2):** A viability + A's between-seed dispersion, on 3 seeds. Cheap; decides whether
  U1(b) applies before any C/F/B/D investment.
- **8.3b (after 8.7):** the paired pilot that measures σ_paired, checks A′ ≡ A, Fβ and F's ability to
  act, and applies the escalation rule before 8.8.

**Are A′/C′ applied at the required stages?** A′ is required at 8.3 (impossible as placed), 8.6 and
8.8; C′ at 8.6 (after C exists) and 8.8. Once the pilot is moved, the control stages are coherent.

**Stop condition when viability fails.** Present and unambiguous at the level of principle (U1(b)):
stop, report the floor with a pathology decomposition, request a scope decision; never tune the
drive, the decoder gate or the mapping. The only gap is the AND/OR asymmetry of "A and F" (Minor m7).

### 9.2 Budget

Measured rate: 0.1049 s per game update, 22.345 s for the 213-update Phase 7 episode
(`neural_closed_loop.json`). A 900-update episode at that rate is 94.4 s.

Every line of §9.2 was recomputed:

| Scope | REV2 | Independent | Verdict |
|---|---|---|---|
| 1 seed × 10 episodes | 3.7 min | 10 × 22.3 s = 3.72 min | match |
| 1 condition × 10 seeds (measured) | 0.62 h | 100 × 22.3 s = 0.620 h | match |
| 1 condition × 10 seeds (worst) | 2.62 h | 100 × 94.4 s = 2.62 h | match |
| 5 conditions eval | 3.1–13.1 h | 3.10–13.11 h | match |
| A′ / C′ / Fβ eval | 0.62–2.62 h each | match | match |
| **F training rollouts (20 episodes/seed)** | **6.2–26.2 h** | **200 episodes × 22.3–94.4 s = 1.24–5.24 h** | **MISMATCH — Major M7 (5×)** |
| **Fβ training rollouts** | **6.2–26.2 h** | **1.24–5.24 h** | **MISMATCH — M7** |
| B/D plasticity overhead | +0.25–2.1 h | 20–40% of 2/5 of eval = 0.25–2.10 h | match |
| Random graphs | 0.3–2.5 h | 10 × 2–15 min = 0.33–2.50 h | match |
| E | <10 min | not measurable without code; plausible | **UNVERIFIED** |
| Analysis | <30 min | plausible | **UNVERIFIED** |

The training lines are exactly 5× the product of their stated assumption (20 episodes/seed × 10
seeds) and the measured per-episode time. Either the wall time is wrong or the assumption should read
"100 episodes/seed"; Appendix C says 20. The error is conservative (it overstates cost), but it
propagates into U11's ceiling and into the N = 16 projection.

**Recomputed total at N = 10**, using the stated assumptions:

- lower: 3.10 + 3×0.62 + 2×1.24 + 0.25 + 0.33 + 0.17 (E) + 0.5 (analysis) ≈ **8.7 h**
- upper: 13.11 + 3×2.62 + 2×5.24 + 2.10 + 2.50 + 0.17 + 0.50 ≈ **36.7 h**

Adding the two lines §9.2 omits — plastic-path overhead for A′ and C′ (0.25–2.1 h) and the floor arm
if replayed on the neural substrate (0.62–2.62 h) — gives **≈ 10–42 h at N = 10** and **≈ 16–67 h at
N = 16**, versus REV2's 19–78 h and 30–125 h. The headline is conservative by roughly 2×, not
optimistic. That is the right direction of error, but the table should be arithmetically self-
consistent.

**Memory.** §9.3 states 0.5 GB available at design time. At this audit, `Win32_OperatingSystem.
FreePhysicalMemory` = 1,889,320 KB ≈ 1.80 GB. The figure is a time-dependent snapshot; the operative
rule (re-check immediately before the campaign; do not start below 4 GB) is correct and currently
**would block the campaign**. Memory is not a protocol defect; it is an execution precondition.

**N = 16 and K = 10 fit the budget?** At the recomputed rates, yes: ≈16–67 h single-process for
N = 16, K = 10, with E and analysis negligible. Even REV2's inflated 30–125 h is a planning figure,
not a hard limit, and U11 leaves parallelism (c) for after the pilot. No contradiction.

**Disk.** 17.93 GB free at design time; the JSONL volume is small. No issue.

### 9.3 Other sequence observations

- 8.2's gate ("reproduce the Phase 7 fingerprint") is a determinism check, not a robustness claim —
  correctly framed.
- 8.10's "integrity 36/37" is consistent with §2.4's README-pin drift description.
- 8.9 says it "reproduces every §7 number", but the §7 numbers are design constants, not
  data-derived quantities; the intended meaning (all computed statistics) is clear from context.

---

## 10. Scientific-integrity audit

| Required distinction | Where REV2 keeps it | Finding |
|---|---|---|
| Structural connectivity ≠ physiological connectivity | Scientific status declaration; §11.1–8; §11.13 | Kept |
| Structural synapse counts ≠ measured synaptic strengths | §11.3 ("not conductances and not measurements of synaptic strength"); §3.1 row 3 | Kept |
| Predicted transmitter signs ≠ experimentally verified physiology | §11.4 ("coarse two-class proxy"); but the document repeatedly says "verified transmitter sign" (§2.1, §3.1 row 3, §3.3 R8, §11.4) | **Terminology risk** — "verified" can read as experimental verification. Minor m8: define it once as "non-null predicted-transmitter annotation" |
| Deterministic replay ≠ evidence of robustness | §2.2 reports determinism as a measurement; §6.10/§8 use it as a control | Kept; no robustness claim is made |
| Decoder output ≠ proof of neural motor control | §11.13 (labels are derived, not identified commands); §3.6.5 forbids "the connectome learned" | Kept |
| Mutual information ≠ biological representation or learning | §5.4 (exploratory, non-confirmatory); §11.28; §4 frozen-prior note | Kept; explicitly cannot revise Phase 6 |
| Trainable readout ≠ connectome learning | §3.6.5; §11.26; E1–E5 | Kept — the strongest part of the revision |
| Synthetic task performance ≠ biological learning | Status declaration; §11.16–20 | Kept |
| `NO_ACTION` outcomes not hidden or discarded | §6.9(1); §7.6 ("No unsuccessful episode is discarded at any stage"); §5.1 ("an all-`NO_ACTION` episode is a valid observation") | Kept |
| Floor reported honestly | §0 predicts five of six conditions will floor; §7.3 tie policy gives p = 1.0 and says it is uninformative; §7.8 forbids "plasticity does not work" | Kept — exemplary |
| Phase 6 negative result honest and frozen | §4 frozen-prior paragraph reproduces −0.0863 bits, p = 0.125, Holm 0.25, not rejected; "Nothing in Phase 8 may be described as confirming, repairing, or overturning Phase 6" | Kept; I verified these are the published values |
| Phase 7 motor floor honest | §0: 2,852 spikes, all stimulated, 0 motor, 213/213 `NO_ACTION`, weights unchanged | Kept; I verified every number against the artifact |
| E's inferential status not inflated | §11.24; §5.4 ("A vs E-matched | explanatory reference") | Kept |
| H3 not inflated into a decoding claim | §4 "Necessary condition"; §5.3; §3.6.4 | Kept (status-label issue M9 is administrative, not a claim inflation) |

No unsupported biological claim was found. No frozen result was reinterpreted. The document's
integrity posture is unusually strong; the only integrity-related correction is the word "verified".

---

## 11. Issues, classified

### 11.1 Critical blocker (1)

**C1 — §10 step 8.3 is not executable in the stated order.**
Step 8.3 requires 3 seeds × {A, C, F, A′, Fβ} × 3 episodes and claims to "reuse 8.1–8.2", but C is
delivered in 8.4, F/Fβ in 8.5 and A′ in 8.6. The ordering rationale says "then the pilot before
C/F/B/D". The gate "A′ must match A exactly on all 3 pilot seeds before the campaign is authorised"
cannot be satisfied before A′ exists. Consequences: the plan cannot be executed, and the σ estimate
arrives after the expensive builds rather than before them.
**Fix:** split the pilot into 8.3a (after 8.2: A viability + A dispersion, 3 seeds) and 8.3b (after
8.7: paired σ, A′ ≡ A, Fβ, F viability), and update the ordering rationale and every cross-reference
(§0, §7.4, §10 8.4–8.8, §12 U7/U13).

### 11.2 Major issues (9)

**M1 — §7.3 table and Appendix C misdescribe the extremal sign vectors.**
"attained by two sign vectors, all-plus and all-minus" is true only when every observed difference
has the same sign. The correct statement is the pair `sᵢ = sign(dᵢ)` and its negation. The count 2 and
every derived number are correct; the explanation is not. (Also Appendix C line "attained by all-plus
and all-minus".)

**M2 — The sign-flip validity assumption is never stated.**
§7.3 gives the mechanics but not the null (paired differences symmetric about zero / condition labels
exchangeable within seed) nor the independence of seeds as a test assumption. Add one paragraph.

**M3 — §11.23 contradicts the revised §3.3 and R9b.**
§11.23 says the null does not preserve "per-neuron outgoing weight sums"; §3.3 and R9b say every
source's outgoing weight multiset is preserved exactly under the recommended U18(a). The limitation
text is V1's and was not updated. It is true only under U18(b).

**M4 — Missing pairs change N without changing the thresholds.**
§7.6 drops pairs; §7.3/§7.5 hard-code 1,024 assignments. At N = 9 the floor is 2/512, the α = 0.05
count is ≤ 25 and the Holm m=4 minimum is 0.015625. The analysis must recompute at the reduced N and
report the degraded floor.

**M5 — "Right-censored survival" is analysed as capped values.**
Rename the outcome as a bounded score, or pre-specify a censoring-aware sensitivity analysis, and
report the censoring rate per condition. As written, the label promises an analysis the plan does not
perform.

**M6 — The pilot cannot estimate σ for the binding contrasts, and §7.4 does not say which σ governs N.**
The pilot covers A, C, F, A′, Fβ; it cannot estimate σ(B−A) or σ(D−C). Power for the family should be
set by the least-powered contrast, which is plausibly C2. Either add B (and D, or justify C as a
proxy) to 8.3b, or state that N is chosen from the worst-case contrast and use a conservative bound.

**M7 — §9.2 training lines are 5× their stated assumption.**
20 episodes/seed × 10 seeds × 22.3–94.4 s = 1.24–5.24 h, not 6.2–26.2 h. The totals are therefore
inflated: ≈10–42 h (N = 10) and ≈16–67 h (N = 16) after adding the omitted A′/C′ overhead and floor
arm. Correct the table or change the assumption to 100 training episodes/seed and update Appendix C.

**M8 — The floor arm is described two incompatible ways and has no budget line.**
§3.6.2: "replaying the paired environment seeds … **on the neural substrate**; it costs seconds".
U10: "replaying … **requires no neural substrate**". Only the game-only replay costs seconds; a neural
replay costs 0.62–2.62 h at N = 10. Pick one, add it to §9.2 if neural, and state the quantity is
identical either way (a `NO_ACTION` policy is spike-independent).

**M9 — H3's status is simultaneously "resolved" and "open".**
Notice item 5 and §4 say the contradiction is resolved and H3 "is confirmatory"; §12 U15 says it is an
open decision and the document says "None is applied". One status must be authoritative: mark §4 and
the notice as *proposals contingent on U15*, and state that m = 4 is in force only after U14/U15.

### 11.3 Minor corrections (10)

- **m1 — §7.5 "most permissive" is inverted.** Equal magnitudes reduce the sign-flip test to the sign
  test, which discards magnitude information and is the *least* permissive magnitude configuration
  for a given split. Counterexample: 8 differences of +10 and 2 of −0.1 give `|T_obs| = 79.8` and only
  8 of 1,024 sign vectors reach it (p = 0.0078), versus 112/1,024 (p = 0.109) under equal magnitudes.
  Reword as "the case that reduces the sign-flip test to the sign test, which is the least efficient
  use of the magnitudes".
- **m2 — §5.1 "within a seed in which the agent is random".** Contradicts trained B, D, E and F.
  Probably a leftover; replace with "within a seed, over K paired evaluation episodes".
- **m3 — §6.8 cross-reference.** "the episode-level analysis is a declared secondary (§7.5)" should be
  §7.7 (Uncertainty) / §5.4; §7.5 is Multiplicity.
- **m4 — §3.6.3 classification gap.** A `NO_ACTION` decision with spikes present is neither
  "motor-driven" (no chosen-action population) nor "undefined" (which requires no spikes). Define it
  (e.g. "bias-driven with incidental activity") or add a fourth label.
- **m5 — §3.6.4 E4 0/0.** If there are no non-`NO_ACTION` decisions the denominator is zero. State
  that E4 is then undefined and the decoding claim is not permitted (E3 already fails, but the
  checklist should say so).
- **m6 — §11.29 is N = 10-specific.** With U7 recommending N = 16, add the N = 16 floor
  (2/65,536 raw; 4 × that adjusted) or scope the limitation explicitly to the N = 10 variant.
- **m7 — U1 gate asymmetry.** "zero non-`NO_ACTION` in A and F" does not say whether this is AND or OR,
  and C is piloted but not gated. Define the three cases (A floors / F floors / both floor) and say
  what happens to C and D.
- **m8 — "verified transmitter sign".** Define once as "non-null predicted-transmitter annotation"
  and avoid "verified" where it could be read as experimental verification.
- **m9 — §0 overstates C′.** C′ is called "now required for interpretation" while U13 is open. Say
  "proposed; required only if U13(a)". §7.1's design enumeration also omits the floor arm that §3.7
  lists.
- **m10 — MDE is unadjusted for Holm.** §7.4/§11.21 should label 53 (N = 10) and 42 (N = 16) as
  unadjusted and give the step-1 values (z ≈ 2.50 gives ≈68 at N = 10), or state that Holm power is
  reported separately in 8.9.
- **m11 — A′ exact identity needs an arithmetic-parity sentence.** Require the live plastic stepper to
  apply deltas only, without changing `LiveBancStepper`'s accumulation order or dtype, so P1/P2/P5/P9
  cannot fail on a benign rounding difference. (This is a feasibility safeguard, not a weakening of
  the zero-tolerance rule.)

### 11.4 Resolved / verified (12)

| # | Item | Status |
|---|---|---|
| R1 | V1's two-sided p error | corrected to 2/1,024; verified |
| R2 | Holm minima (m = 4, m = 3) | corrected; verified |
| R3 | H3 ↔ C1 substantive contradiction | resolved in substance (status wording M9) |
| R4 | "No evaluation episode may update anything" | replaced with the per-condition rule (§6.7); verified |
| R5 | Floor "analytically known / zero cost" | corrected to a measured arm (cost wording M8) |
| R6 | §3.3 outgoing-weight contradiction | corrected; R9b added; U18 added (§11.23 stale — M3) |
| R7 | Budget omitted the control arms | arms added; a new arithmetic error remains (M7) |
| R8 | N = 16 recommendation with UCB argument | verified: 2.117× → 142 → N = 16 |
| R9 | Appendix C constants | updated; all checked (except M1's wording) |
| R10 | U1 stop rule vs §7.8 reporting rule | separated correctly |
| R11 | U12 duplicate-module constraint | verified: the three `learning/` files are 1-line placeholders |
| R12 | D1–D10 repository discrepancies | verified against source (`experiments/baseline.py` 526 lines; no `src/`; no SB3; 32-node fixture only) |

---

## 12. Exact corrections required

Each item names the section and, where useful, proposed wording. No correction was applied to REV2
during this audit.

1. **§10 8.3 (Critical C1).** Replace the pilot row with two rows:
   - 8.3a "A viability pilot — 3 seeds × A × 3 episodes; reuses 8.1–8.2; gate: records the non-
     `NO_ACTION` count and A's between-seed dispersion; applies U1(b) if the floor is confirmed."
   - 8.3b "Paired pilot — 3 seeds × {A, B, C, F, A′, Fβ} × 3 episodes, after 8.7; gate: measures
     σ_paired for C1–C4, proves A′ ≡ A on all 3 seeds, applies the §7.4 escalation rule."
   Update the ordering rationale ("after the pilot before C/F/B/D" → "8.3a before C/F/B/D; 8.3b after
   8.7 and before 8.8") and the cross-references in §0, §7.4, §12 U7/U13.

2. **§7.3 table, extreme-statistic note (M1).** Replace "the extreme statistic `|T| = Σ|dᵢ|` is
   attained by two sign vectors, all-plus and all-minus" with: "the extreme statistic `|T| = Σ|dᵢ|`
   is attained by the sign vector `sᵢ = sign(dᵢ)` and by its negation; these are the all-plus and
   all-minus vectors only when every observed difference has the same sign." Apply the same fix to
   Appendix C.

3. **§7.3, new paragraph after the table (M2).** "Validity assumption. The test is exact under the
   null that the paired differences `dᵢ` are symmetric about zero, i.e. that the two condition labels
   are exchangeable within a seed. Conditions are deterministic procedures, not randomly assigned
   treatments, so this is an assumption about the difference distribution, not a design guarantee;
   the two-sided exact sign test is reported alongside as the robustness check. Seeds are independent
   by construction (§6.3) and are the only independent units; episodes within a seed are averaged
   before the test (§6.8)."

4. **§7.5, final paragraph (m1).** Replace "which is the case that makes the sign-flip test most
   permissive" with "which reduces the sign-flip test to the sign test and is the least efficient use
   of the magnitudes; with unequal magnitudes a split that fails here can still reach significance."

5. **§7.6, cell-error row (M4).** Append: "If a pair is dropped, the enumeration and every threshold
   in §7.3/§7.5 are recomputed at the reduced N (N = 9: 512 assignments, minimum two-sided p =
   0.003906, α = 0.05 count ≤ 25, Holm m=4 minimum 0.015625). The report states the reduced N and its
   degraded floor."

6. **§5.1 primary-outcome definition (M5, m2).** Replace with: "Mean number of game updates survived
   per evaluation episode, capped at the 900-update truncation cap, averaged over K paired evaluation
   episodes within a seed. The capped value is a bounded score; the censoring rate per condition is a
   mandatory secondary, and a Kaplan–Meier/log-rank-type sensitivity analysis is pre-specified."
   (Or keep "censored survival" and add the sensitivity analysis; either wording is acceptable, but
   the label and the analysis must agree.)

7. **§7.4 (M6, m10).** Add a row: "σ that governs N: the largest σ_paired among C1–C4; the pilot must
   include B (and D, or state why C is an acceptable proxy for D−C)." Label the MDE rows "unadjusted"
   and add "Holm step-1 MDE at N = 10 ≈ 68".

8. **§9.2 (M7, M8).** Change the two training lines to "1.24–5.24 h" (or change the assumption to
   100 episodes/seed and update Appendix C), recompute the totals (≈10–42 h at N = 10; ≈16–67 h at
   N = 16), and add two lines: "A′/C′ plastic-path overhead +0.25–2.1 h" and "floor replay (neural
   substrate) +0.62–2.62 h". In §3.6.2, replace "on the neural substrate" with "on the paired
   environment seeds (game-side; the floor is spike-independent)" or budget the neural replay.

9. **§11.23 (M3).** Replace "but **not** component structure or per-neuron outgoing weight sums" with
   "but **not** component structure; per-source outgoing weight sums are preserved exactly under the
   recommended target-exchange parameterisation (R9b) and not under endpoint re-pairing (U18)". If
   U18(b) is chosen, restore the current wording and drop R9b to descriptive.

10. **§4 opening paragraph and notice item 5 (M9).** Replace "the labels are binding" with "the
    labels proposed by REV2 are binding **once U15 is approved**; until then m = 4 is a proposal and
    every Holm threshold in §7.5 is contingent". Notice item 5 should say "proposed resolution",
    not "resolved".

11. **§6.8 (m3).** "(§7.5)" → "(§7.7)".

12. **§3.6.3 (m4).** Add a row: "| **bias-driven (incidental)** | chosen action is `NO_ACTION` but
    ≥ 1 motor spike occurred — no action was chosen from any population |".

13. **§3.6.4 E4 (m5).** Append: "If there are no non-`NO_ACTION` decisions, E4 is undefined and the
    decoding claim is not permitted."

14. **§11.29 (m6).** Add: "At N = 16 the same floor is 2/65,536 raw and 4 × 2/65,536 adjusted."

15. **U1 (m7).** Add: "The gate is evaluated separately for A and for F: (i) both floor → option (b);
    (ii) A floors but F does not → the campaign may proceed only if the user accepts that C2/C3 are
    uninformative at the floor; (iii) F floors but A does not → F is uninformative and C1/C4 are
    reported as floor-limited. C and D are reported, not gated."

16. **§2.1, §3.1 row 3, §3.3 R8, §11.4 (m8).** Define once: "verified sign = non-null predicted-
    transmitter annotation in the BANC export; it is a prediction, not a physiological measurement."

17. **§0 and §7.1 (m9).** "A′, C′ and Fβ are now required" → "A′ and Fβ are required; C′ is proposed
    (U13) and becomes required only under U13(a)". Add the floor arm to §7.1's design enumeration.

18. **§3.8 (m11).** Add: "The live plastic stepper must be an additive subclass of `LiveBancStepper`
    that applies weight deltas without changing the parent's current-accumulation order or precision;
    otherwise P1/P2/P5/P9 are not a test of eta = 0 but of kernel equivalence."

---

## 13. Human decisions still required

All 18 U-items remain open; none is approved, and no wording such as "recommended" or "proposed"
was treated as approval.

**Decisions that change the statistics (must be settled together):**

- **U14** confirmatory family size (m = 4 with C4, or m = 3 without) and **U15** H3's status — these
  two are coupled; m = 3 forbids any decoding claim.
- **U7** N (10 floor vs 16 default) and **U6** K (10 vs 5 vs 20) — both feed the budget and the
  attainable floor.
- **U16** Fβ scope (full N×K training vs pilot-only) — required for C4.
- **U13** C′ scope — required for D's code-path validation.
- **U3** primary outcome — chooses between the bounded-score and censored-survival framings (M5).
- **U18** swap parameterisation — decides which gates (R8/R9b) are exact.
- **U4** random-null scope — confirmatory vs exploratory variants.
- **U11** budget ceiling — now informed by the corrected ≈10–42 h / ≈16–67 h figures.
- **U1** floor response — the stop decision, including the three gate cases (m7).
- **U9** B/D online vs train-then-freeze; **U2** eta; **U10** floor arm; **U12** `learning/`
  namespace; **U5** E implementation; **U8** E-full; **U17** E3/E4 thresholds.

**Not a decision, but a precondition:** the memory pre-flight (≥ 4 GB free) currently fails (≈1.8 GB
at this audit). No campaign can start until that is resolved.

---

## 14. Final readiness verdict

| Dimension | Verdict | Reason |
|---|---|---|
| **Document correctness** | **CONDITIONALLY READY — CORRECTIONS REQUIRED** | 1 critical, 9 major, 10 minor; all correctable in REV3 without new evidence |
| **Scientific design readiness** | **CONDITIONALLY READY** | Design is coherent, controls are right, claims are bounded; the corrections are specification, not design |
| **Technical implementation readiness** | **NOT READY** | G1–G7 are all real gaps; none is implemented; the acceptance tests are stated and feasible |
| **Execution readiness** | **NOT READY** | §10 sequence is contradictory (C1); memory pre-flight fails; no code exists |
| **Human approval readiness** | **NOT READY** | REV3 corrections plus explicit decisions on U1–U18 are required |

**Final verdict: CONDITIONALLY READY — CORRECTIONS REQUIRED.**

REV2 is materially better than V1: it corrects the two-sided p floor, adds the Fβ constant-action
control and the E1–E5 bar, makes graph randomization evidence-based (R1–R18), and specifies A′/C′
with a zero-tolerance hard stop. It is not yet approvable, because one sequencing contradiction makes
the plan unexecutable as written and nine specification defects must be fixed before the design is
frozen. None of the nine changes the scientific conclusions the phase is designed to reach.

---

## 15. Evidence

**Documents inspected (read-only):**

- `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV2.md` — 1,465 lines, SHA-256
  `d6a8964c753984736fcdcf315ca0e8e6af61415afcb79cd5db9cbae45bdab7c0`
  (sections re-read for this audit: lines 1–120, 161–255, 256–515, 516–600, 602–742, 743–851,
  852–991, 1037–1135, 1135–1195, 1195–1392, 1395–1465)
- `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT.md` — 888 lines, SHA-256
  `d9d13a6c312b1c536a0d9266ade4ad81c47bdc99192d6f8d53816d81813fc505`
- `docs/PHASE_8_PROTOCOL_REV2_CHANGELOG.md` — 125 lines, SHA-256
  `b4a5dba7874b8b1371843b7d76bb66254bd8ab156d9241abc979d107896192e9` (not used as evidence)
- `docs/PROJECT_VISION.md` lines 1443–1485 and 2184 (Phase 8/9 definitions and dependencies)

**Source inspected (read-only):**

| File | Lines / symbols used |
|---|---|
| `plasticity/plastic_simulator.py` | `reset` 221, `run` 243, internal `self.reset()` 253 (G1) |
| `plasticity/engine.py` | `observe_step` 113, `learn` 151 (G1 feasibility) |
| `plasticity/weights.py` | `WeightState` 151, `digest` 507, `describe` 511 (P11–P17) |
| `plasticity/config.py` | `fixed_mode_eta` 43, exact-zero validation 92–97 (A′/C′) |
| `plasticity/synthetic.py` | `synthetic_graph` 35, default `n_nodes = 32` (G3) |
| `environment/live_loop.py` | `LiveBancStepper` 162, `advance_to_step` 204, `weight_fingerprint` 253; `LiveSensoryDrive` 297; `decode_trailing_window` 472; `NeuralClosedLoop` 528, `run` 568, unconditional decoder call 600 (G2) |
| `environment/subway_environment.py` | `ControlledGameEnvironment` 44, `reset` 129, `step` 158, `summary` 197, `action_counts` 200, `save_recording` 207 |
| `environment/reward_function.py` | `GameRewardFunction` 95, `schedule` 130, `modulation_provider` 133 |
| `motor/action_decoder.py` | decoder interface (`decode_window`, `decode_series`, `decode_recorder`) |
| `brain/banc_graph.py` | `BancConnectome` CSR invariants (R12) |
| `brain/banc_simulator.py` | `BancSimulator` step order |
| `experiments/phase_4h/common.py` | `load_world` 255 |
| `experiments/phase_5/controlled_task.py` | `run_spiking_episode` 300 (G5) |
| `experiments/phase_5/comparative.py` | `privileged: true` 978, `matched_control: False` 718 (G4) |
| `learning/dopamine.py`, `learning/synaptic_plasticity.py`, `learning/mutual_information.py` | each one line (U12) |
| `experiments/baseline.py` | 526 lines (D1) |

**Measured artifacts inspected:**

- `experiments/results/phase_7/neural_closed_loop.json` — 213 updates, 7,100 neural steps, 2,852
  spikes (all stimulated), 0 motor spikes, 213 `NO_ACTION`, 22.345 s wall, weights
  `4923f0cd…d945d5` identical before/after, spike fingerprint `cca811f3…b2fb`.
- `experiments/results/phase_7/game_integration_demo.json` — random-agent survival 213/332/218
  (mean 254.3, sd 67.3); rule-based 432/531/432 (mean 465.0, sd 57.2).
- `datasets/processed/banc_v888/banc_manifest.json`, `banc_graph_t5.npz` — 172,433 nodes,
  1,535,710 edges, 18,552,546 synapses, `edge_weight` int32 min 5 max 913, 24,320 isolated.
- `experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108/simulation_metadata.json` —
  683,100 signed edges, 852,610 excluded, 502,727 excitatory, 180,373 inhibitory.
- `experiments/results/phase_4g/phase_4g_summary.json` — 8,426,168 signed synapses.
- `README.md` — current SHA-256 `8a79d44d4d5679333a99d475c419f790d3ad14d00c145645c55f6a45dac64164`,
  14,938 bytes; pinned in the integrity baseline as `8ab6a8cc…f90563`, 14,921 bytes (pre-existing
  drift, as §2.4 states).

**Tests inspected but NOT executed:**

- `tests/test_phase_7_neural_closed_loop.py` (16 tests, including "synaptic weights unchanged" and
  "deterministic episode").
- `tests/test_phase_7_environment.py` (19 tests, including reset/step contract and same-seed
  reproducibility).

REV2's claim that "6 of the full test suite fail on one cause only (the README pin)" and that
"all 36 other pinned files match" is **UNVERIFIED in this audit** — no test was run, by rule. The
README drift itself is confirmed by direct hashing.

**Computed independently (no code executed against project modules):** every constant in §4,
including 2^10, 1/1,024, 2/1,024, the 51/1,024 threshold, all Holm thresholds and minima, the 22/1,024
and 112/1,024 equal-magnitude counts, 2^16, 2/65,536, MDE 53.155/42.024, σ supports 112.87/142.78,
the 2.11694 UCL factor and the implied N = 16, the corrected budget totals, and the 8/1,024
unequal-magnitude counterexample in m1.

**What this audit did not do:** it did not modify REV2, V1, the change log, any source file, any
configuration, any weight, any graph, or any frozen artifact; it did not implement Phase 8; it did not
run tests, episodes, training, or graph randomization; it did not install anything; it did not stage,
commit, push, pull, reset, checkout, clean, stash, or delete anything. The only write was this report.
