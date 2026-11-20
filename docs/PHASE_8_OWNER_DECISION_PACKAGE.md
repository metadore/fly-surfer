# Phase 8 — Owner Decision Package

| field | value |
|---|---|
| document kind | owner-facing decision package; **not** a protocol, **not** an approval, **not** evidence |
| date | 2026-11-20 |
| governing protocol | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` |
| protocol SHA-256 (verified this pass) | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines) |
| protocol status | **NOT APPROVED, NOT EXECUTABLE**; U1–U18 are **PROPOSED — not approved** |
| campaign configuration (verified this pass) | `configs/phase_8/campaign.yaml` SHA-256 `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19` |
| other configs (verified this pass) | `conditions.yaml` `9a93f047…d42f671`; `environment.yaml` `b391ecf7…3281dc` |
| what this document does | it collects, in one place, every unresolved scientific and experimental decision, verified against the protocol, the code and the artifacts |
| what this document does not do | it approves nothing, changes no status, sets no sample size, chooses no correction, alters no graph, runs nothing |

**Evidence labels used throughout.**

- **verified** — re-read or re-hashed in this preparation pass (2026-11-20).
- **executed** — a read-only command or a synthetic test suite run in this pass; never an experiment.
- **static** — read from a source file, config or certificate without executing the path.
- **reported** — a figure taken from an existing committed report, cited with its section, and not re-measured here.

No experiment, pilot, training run, simulation or campaign was executed to produce this document. No
file other than this document and its companion readiness report was created or modified.

---

## How to read this package

- **Part A** explains the experiment as a whole: what it is for, what the six conditions and four
  controls establish, what the four confirmatory comparisons mean, and what would count as success,
  failure or an inconclusive result.
- **Part B** is the full register of U1–U18: for each decision, the exact protocol wording, the
  options the protocol actually supports, and the scientific, statistical and implementation
  consequences.
- **Part C** treats the two decisions that determine the statistical size of the experiment (U7
  sample size, U14 correction family) in depth.
- **Part D** treats the four training-operations decisions that the protocol does not declare
  (B3–B6).
- **Part E** documents the pilot seed/graph/artifact mismatch and the legitimate ways out.
- **Part F** documents the G3 memory-gate deviation.
- **Part G** states the remaining environmental requirements.
- **Part H** is the dependency map and the shortest valid sequence.
- **Part I** is the one-page owner decision sheet.

Three vocabularies are kept strictly apart, because conflating them is the main way this project
could mislead itself:

| term | meaning | current state |
|---|---|---|
| **software readiness** | executable code exists and focused tests that call it pass | mechanisms largely complete; six stage harnesses added; 402 Phase 8 tests pass |
| **experimental readiness** | every protocol, design, compliance, resource and authorisation gate is met | **not met**; ten preconditions, all open (see Part G, Part H) |
| **experimental evidence** | rows produced by an authorised run on the real substrate and game | **none exists**; `experiments/results/phase_8/` does not exist |

---

# PART A — The experiment as a whole

## A.1 What Phase 8 establishes, if it runs and the gates pass

Phase 8 is the first phase whose stated purpose is to *compare conditions* rather than to build a
pipeline (`docs/PROJECT_VISION.md`, Phase 8, quoted in REV4 §1.1). It asks four questions, each
attached to one confirmatory contrast (REV4 §4, §5.3):

| # | Question | Contrast | Hypothesis |
|---|---|---|---|
| 1 | does reward-modulated three-factor plasticity change behaviour on the biological graph? | C2 = B − A | H1 |
| 2 | does the biological graph outperform a degree- and sign-matched random graph? | C3 = A − C | H2 |
| 3 | does a trainable readout on the same frozen substrate beat the fixed threshold decoder? | C1 = F − A | H3 |
| 4 | does the readout use motor information at all, over the best constant policy? | C4 = F − Fβ | §3.6.2 claim 2 |

The primary outcome for all four is the **capped survival score** `min(observed_updates, 900)`,
averaged over K = 10 episodes within a seed, with the **seed** as the independent unit (REV4 §5.1,
§7.2). The test is a two-sided exact sign-flip permutation over `2^N` sign vectors, followed by Holm
at α = 0.05 family-wise (REV4 §7.3, §7.5).

Phase 8 does **not** establish any biological fact about the fly. It measures the behaviour of a
model built from structural connectome counts, driven by a synthetic game, decoded by declared
thresholds (Part A.6).

## A.2 Why six conditions

The six conditions form a 2 × 3 design over *substrate* and *what changes*, so that each contrast
removes one explanation (REV4 §3.7):

| Condition | Topology | Weights | Decision source | What it isolates |
|---|---|---|---|---|
| **A** | biological | fixed | fixed threshold decoder | the reference: no learning anywhere |
| **B** | biological | plastic (η = 0.5) | fixed threshold decoder | synaptic plasticity on the real graph |
| **C** | target-exchanged random, degree- and sign-preserved | fixed | fixed threshold decoder | biological *wiring* versus a matched null |
| **D** | target-exchanged random | plastic | fixed threshold decoder | plasticity on a random substrate (completes the 2 × 2) |
| **E** | none (MLP) | trained | argmax over 4 logits | whether the *task* is learnable from the 7 shared features |
| **F** | biological | **fixed** | trained linear readout | whether a trained decoder can extract more than the fixed rule |

B is only interpretable against A; D only against C; F only against both A (readout vs fixed rule)
and Fβ (state-dependence vs best constant policy). That is why the controls in A.3 are not optional.

## A.3 What the four control arms establish

Control arms produce no scientific claim of their own; they gate the interpretation of B, D and F
(REV4 §3.7, §3.8).

| Arm | What it is | What it establishes | What failure means |
|---|---|---|---|
| **A′** | A routed through the plastic code path at exactly η = 0 | that the plastic pipeline is an *identity* when η = 0, field by field (P1–P19, zero tolerance) | any mismatch marks **B INVALID** for interpretation and is a hard stop (REV4 §3.8.5) |
| **C′** | C routed through the same plastic path at η = 0 on the same per-seed graph | the same identity for D's actual code path and graph | a mismatch marks **D INVALID**; without C′ no causal attribution for D is permitted (REV4 §5.4, U13) |
| **Fβ** | bias-only readout: feature weights fixed at exactly 0.0, only output biases trainable | the best policy whose action cannot depend on any observation | if F does not beat Fβ, the readout may be described as non-constant but **not** as using motor information (C4) |
| **F-init** | F's architecture at its seeded initial parameters, no training | the "non-constant but unlearned" diagnostic | if F does not beat F-init, F may not be described as *learned* (§3.6.2 claim 4) |
| **floor** | substrate-free constant `NO_ACTION` policy replayed on the paired environment seeds | the game-side no-action baseline | it is a measurement, never a neural arm; a missing floor makes the at-floor rule **not evaluable** (§7.8) |

The "fifth column" is the **floor**: it consumes seconds, has no neural substrate, and is never
budgeted as a condition (U10). The distinction matters because Phase 7 already observed that the
neural conditions may be *at* that floor.

## A.4 What the four confirmatory comparisons mean

| ID | Comparison | Positive result means | Positive result does **not** mean |
|---|---|---|---|
| **C1** | F − A > 0 | a trained readout extracts more survival than the fixed rule on the same spikes | that the readout used motor information — a bias term alone can produce C1 (REV4 §5.3) |
| **C2** | B − A > 0 | the three-factor rule changed behaviour under the game reward | that the change is adaptive, or that the fly learns |
| **C3** | A − C > 0 | biological wiring beats a degree- and sign-matched null at this operating point | that the effect is due to any specific biological feature; the null does not preserve component structure (§11.23) |
| **C4** | F − Fβ > 0 | the readout's action depends on state, not only on a constant bias | that the dependence is on **motor** activity rather than another state variable (§3.6.2 claim 2) |

A claim that "the readout learned to decode motor activity" requires **all five** of E1–E5
(REV4 §3.6.4): C4 survives Holm, C1 survives Holm, motor populations are not silent (≥ 1 spike on
≥ 1% of decisions in ≥ half of seeds), ≥ 10% of non-`NO_ACTION` decisions are classified
motor-driven by the frozen-parameter ablation, and a fresh-process rerun reproduces the motor-driven
count exactly. If the motor populations are silent, **no neural-learning claim of any strength is
permitted** — not "weak evidence", not "a trend" (§3.6.4).

## A.5 What counts as success, unsuccess, and inconclusive

REV4 states a refutation condition for each hypothesis (§4). None of these is a pass/fail on the
whole phase; each is a statement about one contrast.

| Hypothesis | Success (predicted direction, survives Holm) | Unsuccess (refuted) | Inconclusive |
|---|---|---|---|
| H1 (C2) | B − A > 0 | difference indistinguishable from zero, or negative | non-zero point estimate that does not survive Holm |
| H2 (C3) | A − C > 0 | A − C ≤ 0 or indistinguishable | same |
| H3 (C1) | F − A > 0 | F − A ≤ 0 | same |
| H4 (E reference) | E-matched above the measured floor | E-matched ≤ floor (environment not solvable from this interface) | n/a — reference, not confirmatory |

Four rules govern the interpretation and must not be relaxed after the data are seen:

1. **Non-rejection is not equivalence.** With all paired differences exactly zero the sign-flip
   p-value is **1.0 by definition**; the report must say "no difference detectable; the design has no
   power against a difference between two floored conditions", never "the conditions are equivalent"
   (REV4 §7.3).
2. **A floored design is uninformative by construction.** If the outcome is at floor in ≥ 4 of 6
   conditions (§7.8, with "at floor" defined numerically as a paired mean difference from the
   measured floor ≤ 0), the confirmatory tests are still reported, but no confirmatory claim of
   "plasticity does not work" may be made.
3. **A floor result is a legitimate outcome.** REV4 §0 preregisters the expectation that A, B, C, D
   and probably F will execute `NO_ACTION` on every update. The response to a floor is a floor report
   plus a scope decision (U1), never a tuning of drive, decoder or mapping (§6.9).
4. **The minimum attainable p is a property of N.** At N = 16 no contrast can be reported below an
   adjusted p of 0.000122 (m = 4), however large the true effect (§11.29).

**Pre-observed floor risk (context, not a Phase 8 result).** The Phase 7 fixed-weight loop produced
2,852 spikes, all in the 232 stimulated sensory neurons, **zero** in any non-stimulated neuron,
**zero** delivered to motor neurons, and `NO_ACTION` on all 213 updates, with bit-identical weights
(REV4 §0). Propagation stopped one synapse downstream: 473 of 607 first-hop targets received
current, the strongest reaching −56.926 mV, 6.926 mV below the −50 mV threshold (reported in
`reports/PHASE_8_FINAL_READINESS_REPORT.md` §9). This is why pilot 1 exists and why it must precede
any campaign.

## A.6 What Phase 8 cannot establish biologically

The following are declared limitations (REV4 §11, selected items) and forbidden statements (§3.6.5).
They are not caveats to be softened in a summary.

| Area | What the model is | What it therefore cannot show |
|---|---|---|
| Connectome | BANC v888 adult female brain + VNC, no lamina or ocellar ganglion; 172,433 nodes, 1,535,710 edges | anything about a whole animal, or about the missing neuropils |
| Synapses | weights are `min(5·count^0.75, 300) pA` from structural counts; only 683,100 edges (44.48%) have a predicted transmitter sign, 852,610 are inert | synaptic strength, conductance, or the effect of the unsigned 55.5% |
| Neurons | single-compartment LIF, 200 pF, 10 nS leak, −50 mV threshold, 2 ms refractory; uniform 1 ms delay | morphology, dendritic computation, receptor kinetics, short-term plasticity |
| Recruitment | one capped edge produces at most 4.7 mV; four coincident edges are needed to fire | rate-coded behaviour; recruitment is synchronicity-gated |
| Sensory interface | 7 of 14 features mapped onto 232 neurons at a fixed 200 pA with zero-order hold | a measured sensory pathway; 7 features including player lane are unmapped |
| Motor interface | LEFT/RIGHT/JUMP are decoder labels from published effector annotations; 391 of 805 motor neurons assigned; ROLL and DUCK have no population | identified biological motor commands; the 414 unassigned neurons |
| Task | synthetic 2-D endless runner; coin +1, collision −1, survival +0.01/step, obstacle reward 0.0 | fly behaviour, naturalistic stimulus, ecological validity |
| Plasticity | three-factor Hebbian rule with a scalar modulation term; "dopamine-inspired" | a dopamine measurement |
| Readout | readout training is not synaptic plasticity and must never be summarised as such (§11.26) | that the connectome learned anything — the connectome is frozen in F |
| Null model | target exchange preserves degree, sign, weight multiset and per-source weight profile (R9b) but **not** component structure (§11.23) | a pure "wiring only" null; C differs from A in global fragmentation too |
| Inference | exact sign-flip assumes paired differences are exchangeable under sign reversal (§11.32) | robustness to dispersion differences between arms |

Forbidden phrasings in every Phase 8 report, abstract and figure caption (REV4 §3.6.5): "the
connectome learned"; "plasticity improved performance" in F; "the readout succeeded" when Fβ scores
the same; "F beat the baseline" without naming which baseline (A vs Fβ support different claims).

## A.7 The three readiness statements, kept apart

| Statement | What would justify it | Current status |
|---|---|---|
| "the software is implemented" | every mechanism exists and its focused tests pass | **true for mechanisms**: 402 Phase 8 tests pass (`executed`); six stage harnesses exist (`verified`) but the package is **untracked in Git** |
| "the experiment is ready to run" | protocol approved, U1–U18 recorded, design recorded, B3–B6 recorded, G3 resolved, memory ≥ 4 GiB, pilot 1 and 2 passed | **false**: ten preconditions, all open |
| "the experiment has produced evidence" | authorised rows in `experiments/results/phase_8/` | **false**: that directory does not exist |

A mechanism being complete never upgrades a scientific status. The campaign CLI reports
`executable: false`, `design_resolved: false`, 69/69 conformance, 16/16 certified graphs and a
**failed** memory gate (2.141 GB of 4.0 GB, `executed` this pass).

---

# PART B — Decision register U1–U18

## B.0 Status vocabulary

REV4 §12 states: "None is applied and none is approved… its status is **PROPOSED — awaiting human
approval**." That is the **protocol status** of every item below. It is not changed here.

Part I adds a separate, owner-facing **action status** drawn from the five permitted labels. The two
must not be confused: an item with "RECOMMENDATION AVAILABLE" is still PROPOSED, and nothing in this
package applies it.

Every recommendation quoted below is the one REV4 itself gives in its §12 entry. Where REV4 gives no
recommendation, this package says so rather than inventing one.

## B.1 U1 — action if the pilot confirms the floor

| field | value |
|---|---|
| **REV4 reference** | §0 (preregistered floor expectation), §3.6.2 (floor definition), §6.9 (degeneracy rules), §10.3 and §10.8 (pilots), §12 "U1", §12.1 row U1 |
| **Proposed decision (exact)** | "five gate cases for the pilot floor (U1-A … U1-E: both above / both floored / A floored only / F floored only / both floored with E above); C and D reported, never gated; floor is a substrate-free game-side control" |
| **Current status** | PROPOSED — not approved. No branch selected. |
| **Plain language** | If the pilot shows no non-`NO_ACTION` action at all, the protocol does not leave the decision open-ended: it defines five situations (A above/at floor × F above/at floor, plus the case where E is above) and prescribes what each licenses. It also names four possible responses if A and F are both floored. |
| **Choices the protocol supports** | the five gate cases as written; and, for the U1-B (both floored) branch: (a) run the full campaign anyway and report a floor; (b) stop, report the floor plus a pathology decomposition, request a scope decision; (c) authorise a separate pre-registered follow-up that changes drive or decoder; (d) if A and F floor but E-matched does not, run only E and report the environment as solvable-but-not-from-this-interface. No other option is offered. |
| **Scientific consequences** | (b) prevents a null, floored campaign from being reported as evidence about the connectome. (d) is the only branch that separates "the substrate cannot act" from "the interface cannot act", and it reports no neural-substrate result. (c) repairs the interface and therefore cannot live inside Phase 8 — it is Phase 9 and needs its own preregistration. (a) risks exactly the misinterpretation the protocol was written to avoid. |
| **Statistical consequences** | No test is attached to U1. If U1-B occurs, §7.8 already declares the confirmatory family uninformative by construction: tests are reported, but no "plasticity does not work" claim is permitted. The stop rule is U1; the ≥ 4-of-6 at-floor rule is a post-campaign **reporting** rule only. |
| **Implementation consequences** | `evaluation/viability.py` implements U1-A … U1-E as a read-only report with C and D reported and never gated (`verified`). No campaign or runner code consults it, so the stop is a stage-level procedural decision at 10.8, not an automatic refusal. Pilot 1 (10.3) establishes only the A row; the full gate needs F and is made at 10.8 (REV4 §10.3). |
| **Recommendation** | REV4 §12: "**(b), then decide with the user; (d) is a legitimate refinement of (b) once E results exist. Never (c) inside Phase 8.**" |
| **Owner approval required** | **Yes.** The five cases, the reporting-only status of C and D, and the U1-B branch must be recorded before pilot 2 is interpreted or any stop is taken. |
| **Dependency** | pilot 1 and pilot 2 (hence memory, REV4 authorisation, pilot graph/artifact contract); U5/U8 for the E-matched leg of case U1-E and branch (d). |

## B.2 U2 — eta for B and D

| field | value |
|---|---|
| **REV4 reference** | §3.4 (B/D specification), §6.7 (what may change during evaluation), §12 "U2" |
| **Proposed decision (exact)** | "B/D eta = 0.5 (Phase 5 declared value); no tuning on the game" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | How strongly the three-factor rule changes weights in B and D. |
| **Choices the protocol supports** | (a) reuse Phase 5's declared 0.5; (b) re-derive η on the game; (c) add a second declared value from `{0.1, 1.0}` as an exploratory arm |
| **Scientific consequences** | (a) is pre-declared and cannot be accused of tuning. (b) is tuning on the game and confounds plasticity strength with selection. (c) is unlikely to inform: Phase 5 found 0.1–2.0 indistinguishable. |
| **Statistical consequences** | η scales the size of any C2 effect. Choosing it after seeing B − A would be selecting on the result; the protocol forbids that. No multiplicity change. |
| **Implementation consequences** | `configs/phase_8/conditions.yaml` declares `plasticity.eta: 0.5`; `conditions/b_plastic.py` and `d_plastic.py` consume it; A′/C′ run the same hook at exactly 0.0 (`verified`). Option (c) would roughly double B/D runtime and add two declared arms. |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U9 (when plasticity runs); U13 (D's identity control). |

## B.3 U3 — primary outcome

| field | value |
|---|---|
| **REV4 reference** | §5.1 (primary outcome), §7.2 (unit of analysis), §12 "U3" |
| **Proposed decision (exact)** | "primary outcome is the **capped survival score** `min(updates, 900)`, not right-censored survival" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether the experiment scores "how long the agent survived, capped at 900 updates", total reward, or both. |
| **Choices the protocol supports** | (a) capped survival score in updates; (b) total task reward; (c) capped survival with reward as co-primary |
| **Scientific consequences** | (a) is bounded, game-defined and identical for all six conditions; it is **not** right-censored survival and must not be described as such. (b) compares conditions on a signal dominated by coins, which are entirely unmodelled in the sensory drive, so no neural condition can reach it. (c) breaks the single-primary discipline and makes the Holm family depend on an outcome choice. |
| **Statistical consequences** | Defines the estimand of every confirmatory contrast and therefore every p-value. A time-to-event analysis, if retained, must be declared separately as a sensitivity analysis with an explicit censoring-aware method; it can never replace the capped-score primary (§5.1, §7.6). |
| **Implementation consequences** | `experiments/phase_8/analysis.py` computes the capped score (`verified`); no change needed if (a) is approved. (c) would require schema and family changes. |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U14 (family), U17 (reporting thresholds), §7.8 at-floor rule. |

## B.4 U4 — random-null scope

| field | value |
|---|---|
| **REV4 reference** | §3.3 (condition C), §3.3.1 (gates R1–R18), §12 "U4" |
| **Proposed decision (exact)** | "confirmatory null is the degree-preserving signed rewire; component- and sign-randomised variants exploratory" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Which randomised comparison counts as the scientific null for "does biological wiring matter?". |
| **Choices the protocol supports** | (a) degree-preserving signed rewire only (confirmatory); (b) also a component-preserving variant (swaps restricted to within an original weak component), exploratory; (c) also a sign-randomised variant (node signs re-drawn at the observed verified fraction), exploratory, answering "does sign assignment matter?" rather than "does wiring matter?" |
| **Scientific consequences** | (a) is a wiring null that holds degree, sign and weights fixed. (b) would separate wiring from fragmentation but needs a second generator and its own gates. (c) answers a different question and must never be pooled with (a). Component structure is reported for every graph regardless (R15). |
| **Statistical consequences** | Only (a) defines C3. Adding (b) or (c) adds no confirmatory test and no multiplicity cost, because they are exploratory. |
| **Implementation consequences** | The target-exchange generator, the R1–R18 reporter and 16 certified certificates exist for (a) (`verified` via the campaign CLI). (b) and (c) would require new generators, new certificates and a different preservation argument; (c) cannot reuse R8 unchanged. |
| **Recommendation** | REV4 §12: "**(a)** confirmatory, **(b)** exploratory, **(c)** exploratory and clearly labelled as answering a different question." |
| **Owner approval required** | **Yes.** |
| **Dependency** | **U18** (swap parameterisation) is coupled to this item; G3 compliance (Part F). |

## B.5 U5 — condition E implementation

| field | value |
|---|---|
| **REV4 reference** | §3.5 (E specification), §9.1 (dependencies), §12 "U5" |
| **Proposed decision (exact)** | "E implemented directly as REINFORCE against the 5-tuple API; no Gymnasium/SB3 install" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether the conventional baseline is written against the project's own environment API or wrapped for a reinforcement-learning library. |
| **Choices the protocol supports** | (a) direct REINFORCE against the existing 5-tuple API, no installs; (b) install Gymnasium + Stable-Baselines3 and wrap the game |
| **Scientific consequences** | (a) gives a competent reference learner on exactly the same 7 observations, which is all E needs. (b) imports a library's internal choices (GAE, clipping, vectorisation) as an unexamined confound and adds a wrapper that would need re-validation against the same five-tuple semantics. |
| **Statistical consequences** | None for the confirmatory family; E is a reference. H4 is refuted if E-matched is at or below the measured floor, which would mean no neural condition's poor performance can be attributed to the connectome alone. |
| **Implementation consequences** | `evaluation/conventional.py` and `training/engine.py` implement (a); gymnasium and Stable-Baselines3 are absent and not required (`verified` by report and by the environment inventory in REV4 §2.3). Training is gated and refuses (`executed`). |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U8 (E-full); U1-E branch; H4. |

## B.6 U6 — evaluation episode count K

| field | value |
|---|---|
| **REV4 reference** | §6.8 (independent evaluation episodes), §7.2 (unit of analysis), §12 "U6" |
| **Proposed decision (exact)** | "K = 10 evaluation episodes per seed" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | How many evaluation episodes each seed contributes to its own average. |
| **Choices the protocol supports** | (a) K = 10; (b) K = 5; (c) K = 20 |
| **Scientific consequences** | K affects the precision of each seed's mean only; the seed remains the independent unit, so it does not change the degrees of freedom of the primary test. Choosing K after seeing data would be selecting on the result. |
| **Statistical consequences** | A smaller K inflates the variance of each seed's mean, which propagates into the paired differences, into σ_max, and hence into whether N = 10 is admissible at all (§7.1). With the three-seed pilot, K also controls how well σ can be estimated. |
| **Implementation consequences** | `campaign.yaml` declares `episodes_per_seed: 10`; the evaluation grid is 12 arms × N × K (1,920 episodes at N = 16, 1,200 at N = 10). At the measured 22.345 s per 213-update episode, K = 10 is ≈ 3.73 min per seed per condition and ≈ 15.7 min if every episode caps. |
| **Recommendation** | REV4 §12: "**(a)**. … (b) is the fallback if U11 caps the budget." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U11 (budget), U7 (σ_max and N), U16 (Fβ full rollout). |

## B.7 U7 — number of seeds N

Detailed treatment in **Part C.1**. Summary: N = 16 primary; N = 10 only as a predeclared fallback
requiring `σ_max ≤ 112.87` defended from pilot 2's upper confidence limit; `design.n_seeds_selected`
is `null`; the value cannot be fixed now.

| field | value |
|---|---|
| **REV4 reference** | §7.1, §7.4, §10.8, §11.22, §12 "U7" |
| **Proposed decision (exact)** | "**N = 16 primary**; N = 10 only as the predeclared fallback of §7.1, with the pilot including B and `σ_max` governing the decision" |
| **Current status** | PROPOSED — not approved; `design.n_seeds_selected` is `null` |
| **Owner approval required** | **Yes**, at 10.8, before any campaign outcome is seen. Approving "N = 16" now would not be the same act as recording it after the pilot. |
| **Dependency** | pilot 2 (all of B, C, F, Fβ, A′, C′ on the pilot grid), which needs the pilot graph/artifact contract (Part E); U11; U6. |

## B.8 U8 — E-full (14 features)

| field | value |
|---|---|
| **REV4 reference** | §3.5, §12 "U8" |
| **Proposed decision (exact)** | "E-full (14 features) included as exploratory, capacity-matched to E-matched" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether to also train a reference learner on all 14 game features, to price the 7 features the neural conditions cannot see. |
| **Choices the protocol supports** | (a) yes, exploratory; (b) no |
| **Scientific consequences** | (a) quantifies what the unmapped features would be worth; it cannot support a confirmatory claim and must not be merged into E. Capacity must match E exactly or the comparison is confounded. |
| **Statistical consequences** | None confirmatory; exploratory outcomes receive no correction and are labelled exploratory everywhere. |
| **Implementation consequences** | `E_full` is a declared separate arm in `conditions.yaml` and the registry, so rows can never be merged into E; the same 2,000-update budget applies. Training is gated (`verified`). |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes** (exploratory arms still require approval before training). |
| **Dependency** | U5; U11 (cost, minutes). |

## B.9 U9 — B/D plasticity during evaluation versus train-then-freeze

| field | value |
|---|---|
| **REV4 reference** | §3.4, §6.7 (per-condition statement of what may change), §12 "U9" |
| **Proposed decision (exact)** | "B/D plasticity runs during evaluation (primary); train-then-freeze exploratory only" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether the plastic conditions keep learning during the measured episodes, or learn first and are then frozen. |
| **Choices the protocol supports** | (a) plasticity runs during evaluation (Phase 5 behaviour); (b) train, freeze, then evaluate; (c) both |
| **Scientific consequences** | (a) measures the closed loop as specified and is the only option that does not misrepresent an online mechanism as an offline one. (b) alone is a different experiment. If (b) or (c), the frozen evaluation must use held-out seeds for both training and the freeze point, or the reported result is a training-set score. |
| **Statistical consequences** | Changes what C2 and D − C estimate. Under (b)/(c), B/D gain a training phase and the train/evaluation separation of §6.7 must be demonstrated. |
| **Implementation consequences** | `conditions/d_plastic.py` installs the plastic hook per episode; A′/C′ certify the same stepper at η = 0 (`verified`). (b)/(c) would require an additional training stage, a freeze point and held-out-seed bookkeeping. |
| **Recommendation** | REV4 §12: "**(a)** for the primary … **(c)** if budget allows, with (b) labelled exploratory." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U2 (η), U13 (C′), A′ control, U11 (budget if (c)). |

## B.10 U10 — no-action baseline

| field | value |
|---|---|
| **REV4 reference** | §3.6.2 (floor definition), §6.9, §7.8 (at-floor rule), §12 "U10" |
| **Proposed decision (exact)** | "no-action floor is a **substrate-free game-side control policy**, measured by replay, never a neural arm" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | How the "do nothing" baseline is obtained. |
| **Choices the protocol supports** | (a) derive the floor from the game configuration without replay; (b) replay the paired environment seeds with a constant `NO_ACTION` policy |
| **Scientific consequences** | (a) is invalid: collision timing depends on obstacle layout, so an analytic floor would be a guess. (b) yields an empirical floor on exactly the seeds each arm faces. |
| **Statistical consequences** | The floor feeds the §7.8 at-floor definition and the U1 gate. A missing floor makes the at-floor rule **not evaluable**, never satisfied. The floor is never a confirmatory contrast. |
| **Implementation consequences** | `controls/floor.py` implements the control policy; the `floor` arm is registered with no neural stream and `seed_plan=None` (`verified`). It costs seconds and produces no simulation rows. |
| **Recommendation** | REV4 §12: "**(b), implemented as a control policy, not a condition and not a neural arm.**" |
| **Owner approval required** | **Yes.** |
| **Dependency** | U1, §7.8 reporting rule. |

## B.11 U11 — compute budget ceiling

| field | value |
|---|---|
| **REV4 reference** | §9.2 (budget table), §9.3 (memory gate), §12 "U11" |
| **Proposed decision (exact)** | "planning budget ≈ 8.9–38.8 h (N = 10) / ≈ 13.9–61.7 h (N = 16), single process; no weakening of the 4 GB memory gate" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | What compute envelope the owner is authorising, and whether cost is reduced by design changes or by parallelism. |
| **Choices the protocol supports** | (a) accept the §9.2 estimate; (b) cap the budget by dropping K to 5 and Fβ's training rollouts; (c) parallelise across CPUs with a determinism audit |
| **Scientific consequences** | (b) is a design change, not a cost saving: it changes K and, for Fβ, removes C4's feasibility. (c) changes no design but introduces a determinism failure mode if the byte-identical check fails. |
| **Statistical consequences** | (b) inflates within-seed variance and weakens the σ estimate that governs U7. (a) and (c) leave the statistics unchanged. |
| **Implementation consequences** | The budget is documented only; no code enforces a wall-clock ceiling. Parallelism is not part of the primary plan and would require per-process thread pinning and a byte-identical determinism check. |
| **Recommendation** | REV4 §12: "**(a)** as the planning figure … Consider (c) only after the pilot." |
| **Owner approval required** | **Yes.** The budget is not an authorisation to run; §9.3 still applies. |
| **Dependency** | U6, U7, U16; the memory gate (Part G). |

## B.12 U12 — whether Phase 8 may write a new `learning/` implementation

| field | value |
|---|---|
| **REV4 reference** | §12 "U12", §12.1 row U12 (the decision register's citation to "§2.3" points at the environment section and is a miscitation — Part B.19) |
| **Proposed decision (exact)** | "Phase 8 does not write a new `learning/` implementation" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether the three placeholder modules in `learning/` stay untouched or are filled with Phase 8 code. |
| **Choices the protocol supports** | (a) leave `learning/dopamine.py`, `learning/synaptic_plasticity.py` and `learning/mutual_information.py` untouched; (b) fill them |
| **Scientific consequences** | (b) creates a second plasticity implementation alongside Phase 5's, makes provenance ambiguous, and implies the Phase 5 mechanism is being replaced — which the project's no-duplicate-modules constraint forbids. (a) preserves one mechanism. |
| **Statistical consequences** | None. |
| **Implementation consequences** | `learning/` is untouched and all Phase 8 code lives in `experiments/phase_8/`, `readout/`, `experiments/phase_8_random/` and `evaluation/` (`verified`). |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes**, although approving (a) preserves the current state. |
| **Dependency** | none. |

## B.13 U13 — C′ mirror for condition D

| field | value |
|---|---|
| **REV4 reference** | §3.8 (A′/C′ controls), §3.8.5 (failure protocol), §10.6, §12 "U13" |
| **Proposed decision (exact)** | "C′ on **all N × K** at eta = 0 through the actual plasticity pathway, same P1–P19 and hard stop as A′; pilot and campaign coverage consistent" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether D gets its own identity control on its own graph, or relies on A′'s validation of shared code. |
| **Choices the protocol supports** | (a) C′ on all N × K, η = 0 through the actual pathway, same P1–P19 and hard stop; (b) C′ on pilot seeds plus episode 1 of every campaign seed; (c) omit C′ and disclose that D shares the stepper |
| **Scientific consequences** | (a) converts "D shares validated code" into "D shares code validated on its own graph". (b) is defensible only if D is reported without causal attribution. (c) leaves the only unvalidated path in the campaign. |
| **Statistical consequences** | None on the family; it gates whether D − C can be interpreted at all. |
| **Implementation consequences** | `controls/c_prime.py` and the factory mirror exist; the comparison is P1–P19 with no tolerance and the first mismatch raises `EquivalenceMismatch` (`verified`). (a) costs about one condition's runtime (≈ 1.19–5.87 h at N = 16 per §9.2). |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U18 and G3 (C′ needs the same per-seed graph), Part E (pilot C′ needs pilot graphs), U9. |

## B.14 U14 — confirmatory family size

Detailed treatment in **Part C.2**. Summary: m = 4 including C4, or m = 3 without it; the choice
changes every Holm threshold and whether a decoding claim is possible at all.

| field | value |
|---|---|
| **REV4 reference** | §5.3, §7.5, §12 "U14" |
| **Proposed decision (exact)** | "confirmatory family m = 4, including C4 = F − Fβ" |
| **Current status** | PROPOSED — not approved; `campaign.yaml` declares `holm_family_sizes: [4, 3]` and the analysis requires the caller to state which was used |
| **Owner approval required** | **Yes**, before data. |
| **Dependency** | **U15** (H3's status must move with it), **U16** (C4 needs Fβ's full rollout), U17. |

## B.15 U15 — confirmatory status of H3

| field | value |
|---|---|
| **REV4 reference** | §4 (hypotheses), §5.3, §5.4, §7, §10, §12 "U15" |
| **Proposed decision (exact)** | "H3 **confirmatory**, exactly one status in every register, contingent on U14/U15 being resolved before data" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | Whether "a trainable readout beats the fixed decoder" is one of the questions the phase is allowed to answer confirmatorily. |
| **Choices the protocol supports** | (a) H3 confirmatory, one status in every register; (b) H3 exploratory, in which case C1 must leave the confirmatory family, m changes, and every Holm threshold and the analysis plan must be edited together |
| **Scientific consequences** | (a) makes the readout question one of the three the phase exists to answer. (b) removes it from the confirmatory set. |
| **Statistical consequences** | Under (b) the family becomes C2, C3 only (or must be redefined); every threshold and the attainable-p table change. A document that says confirmatory in one place and exploratory in another is defective and blocks authorisation (§4, §12.1). |
| **Implementation consequences** | REV4 uses one status; `registry.confirmatory_contrasts(3 or 4)` and `analysis.py` accept either family but require the caller to declare it (`verified`). No code choice exists. |
| **Recommendation** | REV4 §12: "**(a)**. … **Exactly one status is permitted.**" |
| **Owner approval required** | **Yes.** |
| **Dependency** | U14 (must be resolved together), U16, U17. |

## B.16 U16 — scope of Fβ

| field | value |
|---|---|
| **REV4 reference** | §3.6.2 (Fβ definition), §3.6.3, §3.6.4, §12 "U16" |
| **Proposed decision (exact)** | "Fβ full N × K rollout, **genuinely state-independent** (feature weights fixed 0, only output biases trainable); no hidden or state pathway" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | How much of the constant-policy control is run, and how strictly "bias-only" is enforced. |
| **Choices the protocol supports** | (a) all N × K, full training, genuinely state-independent, mirroring F; (b) pilot seeds only, plus the ablation counterfactual on every F decision; (c) no Fβ rollouts |
| **Scientific consequences** | (a) supports C4. (b) cannot supply a paired per-seed difference at N and is acceptable only if C4 is dropped — and then no decoding claim is possible. (c) answers the mechanism question but not the behavioural one. A "bias-only" label is valid only when nothing but the output biases trains. |
| **Statistical consequences** | C4 requires a paired per-seed difference; a pilot-only Fβ cannot provide it. Dropping C4 changes m (U14) and therefore every threshold. |
| **Implementation consequences** | `controls/f_beta.py` and `training/validation.py` enforce feature weights fixed at exactly 0.0 and `assert_state_independent()` (`verified`). (a) costs 0.99–4.20 h evaluation plus 1.99–8.39 h training at N = 16 (§9.2). |
| **Recommendation** | REV4 §12: "**(a)** if U14 selects m = 4." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U14 (must be resolved together), U6, U11. |

## B.17 U17 — declared thresholds in the readout evidence bar

| field | value |
|---|---|
| **REV4 reference** | §3.6.4 (E1–E5), §12 "U17" |
| **Proposed decision (exact)** | "readout evidence bar E3/E4 at the declared low thresholds (≥ 1% of decisions, ≥ half of seeds; ≥ 10% motor-driven), with 0/0 reported as not evaluable" |
| **Current status** | PROPOSED — not approved |
| **Plain language** | How much motor activity is required before the words "the readout learned to decode motor activity" may appear. |
| **Choices the protocol supports** | (a) accept 1% of decisions in at least half the seeds and 10% motor-driven; (b) tighten to 5% and 25%; (c) loosen to any single motor spike and 1% |
| **Scientific consequences** | (a) is deliberately low because the expected regime has zero motor spikes. (c) would let one spike anywhere license a decoding claim. (b) risks being unreachable even if a real effect exists. |
| **Statistical consequences** | E4's denominator is non-`NO_ACTION` decisions; with none, E4 is **undefined (0/0)**, never a pass. E3 already fails in that case, so the two guards agree. |
| **Implementation consequences** | `analysis.py` constants `E3_MIN_DECISION_FRACTION = 0.01`, `E3_MIN_SEED_FRACTION = 0.5`, `E4_MIN_MOTOR_DRIVEN_FRACTION = 0.10` (`verified`). |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes** (a reporting convention, but it gates the readout claim). |
| **Dependency** | U14/U15/U16 (the claim it qualifies), §3.6.3 classification. |

## B.18 U18 — swap parameterisation for the degree-preserving null

| field | value |
|---|---|
| **REV4 reference** | §3.3.1 (R1–R18), §11.23 (limitation), §12 "U18" |
| **Proposed decision (exact)** | "degree-preserving null uses **target exchange** (sources and weights fixed, targets swapped), preserving R9b; endpoint re-pairing rejected" |
| **Current status** | PROPOSED — not approved. **The 16 certified graphs were generated under this option before approval** (recorded deviation, Part F). |
| **Plain language** | How the rewire moves an edge: swap only the targets of two edges (option a), or re-pair both endpoints and carry the weight (option b). |
| **Choices the protocol supports** | (a) target exchange; (b) endpoint re-pairing |
| **Scientific consequences** | (a) preserves out-degree, in-degree, weight multiset, per-source weight profile (R9b) and per-node signs exactly, so the null isolates wiring while holding the rest fixed; it does not preserve component structure. (b) is a valid null but does not preserve per-source weight sums; R9b becomes descriptive and §11.23 must be rewritten. |
| **Statistical consequences** | Under (b), R8's signed-synapse total becomes a reported quantity rather than an exact gate; the existing certificates would be invalid for the confirmatory null. |
| **Implementation consequences** | `experiments/phase_8_random/target_exchange.py` implements (a); 16 certificates record `construction: "target_exchange"` (`verified` via the campaign CLI). (b) would require a new generator, new certificates and a new preservation argument. |
| **Recommendation** | REV4 §12: "**(a)**." |
| **Owner approval required** | **Yes.** |
| **Dependency** | U4; G3 deviation (Part F); Part E if pilot graphs are ever built. |

## B.19 Document defects observed while verifying this register

These are reported, not corrected. They change no decision and no number.

| # | Defect | Where | Effect |
|---|---|---|---|
| 1 | `reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md` cites "REV4 §2.3" for U12; §2.3 is "Verified environment" | register §2 U12 | wrong citation only |
| 2 | `reports/PHASE_8_G4_REMAINING_BLOCKERS.md` calls the N decision the "U7 pilot-1 decision"; REV4 §7.1/§10.8 place it at pilot 2 (10.8), and pilot 1 explicitly estimates no contrast | blockers §1 B2 | wrong stage reference only; resolved in favour of REV4 |
| 3 | `experiments/phase_8/campaign/protocol.py::validate_campaign` docstring says `n_seeds_selected` "is reported, not failed", but the operative check compares it to `None` and `strict=True` raises on any failed check | `protocol.py:242–245, 287–293, 520` | once U7 is recorded, conformance fails and the campaign is refused until the check is edited (see Part C.1.6) |
| 4 | Campaign CLI blocker text says "10.7/10.8"; REV4 places the design decision at 10.8 | `run_campaign check` output | label only |
| 5 | `configs/phase_8/campaign.yaml` comments describe values as "REV3 …"; every value matches REV4 | `campaign.yaml` header and several comments | label drift only; values verified against REV4 Appendix C |
| 6 | `pilot2_readiness` blocker text names "trained F, F-beta and **E** artifacts", but pilot 2's arm set is A, B, C, F, Fβ, A′, C′ — no E | `experiments/phase_8/stages/pilot2.py:204–212` | over-broad blocker text; does not change the requirement that F/Fβ artifacts are missing |
| 7 | `reports/PHASE_8_FINAL_READINESS_REPORT.md` and `reports/PHASE_8_IMPLEMENTATION_STATUS.md` (both 2026-11-18) record the pilot/training/campaign/information/report stages as absent; the tree now contains `experiments/phase_8/stages/` with all six harnesses (untracked) | both reports, §4/§8 and §2/§9 | stale status; the newer state is reported in the companion readiness document, and neither older report is edited |

---

# PART C — The two decisions that set the statistical size

## C.1 U7 — sample size

### C.1.1 What `design.n_seeds_selected` actually controls

It is not a cosmetic field. Reading the code (`verified`):

| Consumer | Effect |
|---|---|
| `experiments/phase_8/config.py::CampaignConfig.active_seeds` | returns `campaign_seeds[:n_seeds_active]`, i.e. the first N declared campaign seeds (1…N) |
| `experiments/phase_8/registry.py::evaluation_plan` | builds the full `(arm, seed, episode)` grid; **raises** while the value is null |
| `experiments/phase_8/training/loader.py::prepare_campaign_artifacts` | loads training artifacts for the *active* seeds only, so the set of required trained artifacts changes with N |
| `experiments/phase_8/campaign/protocol.py::validate_campaign` | includes `campaign.n_seeds_selected` in the 69 conformance checks, compared against `None` today |
| `experiments/phase_8/analysis.py` | requires the actual number of complete pairs to equal the selected N; every threshold is recomputed at the actual N (§7.3 rule 3) |
| `campaign/status.py`, run manifest, every episode row | carry N so that a partial or drifted store is detectable |

Because the value is `null`, the campaign CLI reports `design_resolved: false` and
`executable: false`, and `training/gate.py::assert_design_resolved` raises before any artifact path
is touched (`executed`).

### C.1.2 Why it is null

REV4 §7.1 makes the choice depend on a measurement that does not exist yet: the largest paired
standard deviation among C1–C4, estimated by pilot 2, with its uncertainty. The pilot must include B,
C, F and Fβ so that all four σ values are estimable. The value is fixed **before** the campaign and
never revisited after outcomes are seen. The code refuses to invent a design rather than defaulting,
which is the correct behaviour but means the field cannot be filled by an implementation decision
(`reports/PHASE_8_PROTOCOL_DECISION_REGISTER.md` §3.1).

### C.1.3 The existing recommendation

REV4 §7.1/§7.4/§12 U7: **N = 16 is the primary design**. N = 10 is available **only** as a
predeclared fallback, and only if

```
σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4)
2.801585 · σ_max / √10 ≤ 100   ⇔   σ_max ≤ 112.8718…  (declared 112.87)
```

can be defended from the pilot's upper confidence limit. A three-seed pilot has df = 2 and an 80%
upper confidence limit ≈ 2.12× its point estimate (factor 2.1169364935501847), so N = 10 would
require a point estimate of roughly `112.87 / 2.12 ≈ 53.2` — a much stronger condition than
"point estimate ≤ 112.87". REV4 §7.1 says a 3-seed pilot "generally cannot" establish the bound and
that N = 10 needs a larger pilot (≥ 5 seeds) or independent variance evidence.

### C.1.4 Statistical consequences

| Quantity | N = 16 | N = 10 (fallback) |
|---|---|---|
| sign vectors | 65,536 | 1,024 |
| minimum two-sided p | 0.0000305176 | 0.001953125 |
| raw p ≤ 0.05 requires | ≤ 3,276 vectors | ≤ 51 vectors |
| Holm step 1, m = 4 | α/4 = 0.0125; ≤ 819 vectors | ≤ 12 vectors |
| minimum adjusted p, m = 4 | 0.0001220703 | 0.0078125 |
| MDE at σ = 60 (normal approximation) | ≈ 42.0 | ≈ 53.2 |
| Holm step-1 MDE at σ = 60 | ≈ 50.1 | ≈ 63.4 |
| σ supported for MDE = SEI = 100 | ≈ 142.8 | 112.87 |
| equal-magnitude split needed for step 1 | 14 of 16 | 10 of 10 |

These are REV4 §7.3–§7.5 numbers. The row that matters most for planning is the last: at N = 16 a
14–2 split passes Holm step 1; at N = 10 only unanimity does.

### C.1.5 Is the recommendation supported by a power analysis?

**Partly, and the distinction matters.** REV4 §7.4 states explicitly that the MDE table is a
**normal-theory approximation, not exact power**: the actual test is an exact sign-flip permutation
with a discrete attainable-p distribution, followed by Holm, and a z-based MDE does not describe
that combination. σ = 60 is an **assumption** extrapolated from a 3-seed Phase 7 pilot (random agent
sd 67.3, rule-based 57.2), not a measurement of the paired difference. What justifies N = 16 is
therefore a **design argument with approximate power arithmetic**: it keeps the MDE near the SEI even
if the true σ is close to the upper confidence limit of a 3-seed estimate. It is not a formal power
analysis, and this package does not describe it as one.

### C.1.6 Interaction with seeds, pairing, episodes and cost

- **Independent seeds.** The seed is the unit of analysis (§7.2); N is the number of independent
  units. Episodes within a seed are averaged before the test, so K does not buy degrees of freedom.
- **Paired contrasts.** All four contrasts are within-seed differences on the same seed grid; A′ and
  C′ must mirror A and C on **all** N × K cells, so a larger N also enlarges the control cost.
- **Episode count.** K = 10 (U6) sets the precision of each seed's mean; a noisier mean inflates
  σ_max and pushes the N decision upward.
- **Cost.** §9.2: N = 10 ≈ 8.9–38.8 h, N = 16 ≈ 13.9–61.7 h, single process. At N = 16 the 12-arm
  grid is 1,920 episodes.
- **Recording it is not free.** Setting the value makes the current conformance check fail
  (`protocol.py:287–293`, `strict` raise at line 520) and makes several tests that assert
  "design unresolved" fail, until those are updated. That edit is mandatory and must be made
  **with** the record, not before it (register §3.4, §5.2).

### C.1.7 What this package does not do

It does not set N. It does not recommend N = 10. It records that N = 16 is REV4's primary design and
that the field must stay `null` until pilot 2 produces `σ_max` with an upper confidence limit.

## C.2 U14 — Holm family size

### C.2.1 Why family size matters

Holm–Bonferroni compares each ordered p-value against α/(m − i + 1). m therefore sets every
threshold, the minimum attainable adjusted p, and the number of seeds that must agree in direction.
It also decides **which scientific claims are available**: C4 is the only contrast that can support a
motor-decoding claim, and §3.6.4 requires that claim to rest on a Holm-surviving test.

### C.2.2 The two variants

| item | m = 4 (C1, C2, C3, C4) | m = 3 (C1, C2, C3) |
|---|---|---|
| which contrasts | F−A, B−A, A−C, F−Fβ | F−A, B−A, A−C |
| step 1 threshold at N = 16 | 0.0125 (≤ 819 vectors) | 0.016667 (≤ 1,092) |
| step 2 | 0.016667 | 0.025 |
| step 3 | 0.025 | 0.05 |
| step 4 | 0.05 | — |
| minimum adjusted p at N = 16 | 0.0001220703 | 0.0000915527 |
| at N = 10, step 1 | 0.0125 (≤ 12 of 1,024) | 0.016667 (≤ 17) |
| decoding claim | possible, if E1–E5 hold | **unavailable** |

A detail worth stating because it is easy to get wrong: at N = 16 with equal-magnitude differences,
m = 3 does **not** lower the evidential bar in practice. A 13–3 split gives raw p = 0.02127, which
still fails m = 3 step 1 (0.016667); a 14–2 split gives 0.004181 and passes under either family. So
the "cost" of C4 at N = 16 is small in the equal-magnitude case and larger only when the split is
moderate and the magnitudes are unequal (REV4 §7.5).

### C.2.3 Statistical consequences of removing C4

- C1 remains confirmatory and H3 can remain confirmatory (U15), but the readout claim is reduced to
  "F beats the fixed rule", which a bias term alone can produce with silent motor populations.
- Fβ loses its confirmatory role; U16 option (a) is no longer needed for C4, though Fβ is still the
  interpretation gate for F (§5.4).
- The evidence bar E1 (C4 survives Holm) can never be met, so the §3.6.4 decoding claim is
  unavailable regardless of how well F scores.
- Every Holm threshold in §7.5, Appendix C and `analysis.py` changes; the achievable minimum adjusted
  p changes.

### C.2.4 Does removing a contrast change the scientific question?

Yes, and not merely statistically. C4 asks whether the readout's action depends on the state rather
than on a constant bias. Without it, Phase 8 can say "a trainable readout scores better than a fixed
threshold" but cannot distinguish that from "the best constant action is better than the fixed rule".
The protocol states this as the reason C4 was added in REV2 (§5.3): without C4 the readout claim is
not identifiable.

### C.2.5 Implementation consequences

`campaign.yaml` declares `holm_family_sizes: [4, 3]`; `registry.confirmatory_contrasts(4|3)` returns
the corresponding tuple; `analysis.holm_adjust` requires `len(p_values) == family_size` and
`analysis` records `family_size` in its output (`verified`). The code does not choose; the caller must
state which family was used, and the report must repeat it.

### C.2.6 What this package does not do

It does not select m = 3 or m = 4. It records that REV4 recommends m = 4 and that choosing m = 3
makes any decoding claim unavailable.

---

# PART D — Training decisions B3–B6

REV4 fixes the training **budgets** (20 readout episodes per seed; 2,000 gradient updates for E) and
declares that training and evaluation seeds are disjoint, that F and Fβ share a training run, and
that the readout is trained on training seeds and frozen at evaluation (§3.6.2, §6.7, Appendix C).
It does **not** declare four operational inputs. The implementation deliberately refuses to invent
them: `python -m experiments.phase_8.stages.run_stage training --status` reports, verbatim
(`executed` this pass):

```
B3: no campaign-to-training seed pairing is declared; supply an explicit (condition, campaign_seed) -> training_seed map
B4: no training-episode environment-seed schedule is declared; supply an explicit per-episode schedule
B5: no checkpoint cadence, retention or format is declared; a resumable run needs an explicit policy
B6: sampler RNG and optimizer moments are not checkpointed; resume is parameter-continuous and not bit-identical
```

and `declarations = {bit_identical_resume: false, checkpoint_policy: null,
environment_seed_schedule: null, seed_pairing: null}`.

For each item below, the "declared contract" is what the code enforces today, and the "unresolved
choice" is what only the owner can supply.

## D.1 B3 — campaign-to-training seed pairing

| field | value |
|---|---|
| **Problem it resolves** | Which training seed serves which `(condition, campaign_seed)`, so that trained F, Fβ and E artifacts can be produced and later matched to evaluation seeds. |
| **Declared contract** | `training/seeding.py::validate_pairing` requires a **complete** map covering every `(condition, campaign_seed)` pair, every value inside `seeds.training` (1001–1020), per-condition uniqueness, and an identical training seed for F and Fβ. A partial map is an error; no default exists. The map is written into each artifact manifest. |
| **Unresolved choice** | the mapping itself, e.g. one-to-one (`campaign i → 1000+i`), a declared permutation, or independent draws recorded after the fact. |
| **Reproducibility** | any complete, recorded map is reproducible; an unrecorded or partial one is not representable, because the code rejects it. |
| **Scientific validity** | affects validity only if it creates leakage. The code rejects `campaign_seed == training_seed`, and the config rejects overlapping campaign/training/pilot seed lists (`configs/phase_8/config.py:525–533`). Index alignment (i → 1000+i) is simple but invites a reader to confuse the two; a declared permutation removes that ambiguity. |
| **REV4-supported recommendation** | REV4 declares disjointness and the F/Fβ shared run, so those are requirements, not choices. It gives **no** mapping, so no protocol-grounded recommendation can be made. The register's "one-to-one with a 1000+i offset" is advisory and not derived from the protocol. |
| **Owner approval required** | **Yes.** |

## D.2 B4 — training-episode environment-seed schedule

| field | value |
|---|---|
| **Problem it resolves** | Which environment seed each training episode uses. |
| **Declared contract** | `training/engine.py::train_readout` / `train_agent` accept `environment_seed_for_episode` as a callable or an integer, refuse a callable returning a non-integer, and record every seed used in `environment_seeds` and in the checkpoint. No derivation is imposed. |
| **Unresolved choice** | a separate training-environment stream derived from the training seed and episode index; the evaluation seeds; or a constant seed. |
| **Reproducibility** | a derived stream is reproducible and auditable; a constant seed is reproducible but degenerate; reuse of evaluation seeds is reproducible but not held-out. |
| **Scientific validity** | **yes, directly.** Reusing evaluation environment seeds would train and evaluate on the same layouts, which is not held-out evaluation and would inflate F and Fβ. A constant seed removes environment variability and biases the readout toward one layout. The protocol's train/evaluation separation (§6.7) supports a disjoint schedule but does not derive one. |
| **REV4-supported recommendation** | REV4 supports only the constraint "training must not use the evaluation environment seed for the same paired episode". It declares no derivation, so a specific schedule is an owner decision; the register's "distinct stream code" suggestion is advisory. |
| **Owner approval required** | **Yes.** |

## D.3 B5 — checkpoint cadence, retention and format

| field | value |
|---|---|
| **Problem it resolves** | When checkpoints are written, how many are kept, and in what format — only needed if a run must be resumable. |
| **Declared contract** | `training/engine.py` requires `checkpoint_every` and `checkpoint_root` together or neither; `training/checkpoint.py::_check_checkpoint_policy` enforces that. The format is `checkpoint.json` plus `parameters.npz`, versioned, refusing overwrite, with state digest, trainable digest, config hash, progress and environment seeds. Checkpoints are **not** artifacts and the artifact loader never discovers them. |
| **Unresolved choice** | cadence (every episode, every n, or only at the end), retention (all, last, declared subset) and whether to keep the existing format. |
| **Reproducibility** | more frequent checkpoints make mid-run failure recoverable and replay possible from any point; keeping only the last makes a failure unrecoverable without rerunning the whole budget. |
| **Scientific validity** | no, provided the declared stopping condition remains the fixed budget. A checkpoint must never be selected by performance: REV4 has no validation-based model selection and no early stopping (register §4.5). |
| **REV4-supported recommendation** | **None.** REV4 declares nothing about checkpoints. The register's "every episode, retain all" is an operational advisory; this package does not present it as protocol-derived. |
| **Owner approval required** | **Yes.** |

## D.4 B6 — RNG and optimizer-state restoration

| field | value |
|---|---|
| **Problem it resolves** | Whether a resumed training run must be bit-identical to an uninterrupted one. |
| **Declared contract** | Every checkpoint payload records `rng_restored: false` and `optimizer_state_restored: false`; `restore_checkpoint` restores parameters and counters only. The training-stage status prints the limitation verbatim: "resume restores parameters and counters only, so a resumed run is parameter-continuous and not bit-identical to an uninterrupted run" (`executed`). |
| **Unresolved choice** | (a) accept parameter-continuous resume with the limitation recorded on the artifact and in the run manifest; (b) extend the checkpoint payload to persist sampler RNG state and Adam moments (`exp_avg`, `exp_avg_sq`, step), then assert equality against a non-interrupted reference. |
| **Reproducibility** | **this is the crux.** Under (a) a resumed run is **not** the same run as an uninterrupted one: the artifact is valid but its provenance must say it was resumed, and no claim of bit-identical reproduction across the resume boundary may be made. Under (b) the campaign could treat a resumed run as equivalent, at the cost of a larger checkpoint and stricter tests. |
| **Scientific validity** | no effect on the evaluation design; it affects what a completed artifact may **claim**. If a run is interrupted and resumed and the limitation is not disclosed, the provenance is misleading. |
| **REV4-supported recommendation** | REV4 requires deterministic replay of one seed × one episode per condition in a fresh process (§8.4) and an append-only store with resume by key (§8.3). It does **not** require bit-identical *training* resume, so (a) is not a protocol violation provided the resume is recorded. Choosing (b) is a code and schema change, not an amendment. If any training run may be interrupted and the artifact must claim an uninterrupted sequence, (b) is the only honest choice. |
| **Owner approval required** | **Yes.** |

## D.5 What B3–B6 do **not** block

Per the register §4.5 and the code: the declared budgets, the fixed stopping rule, F-init (no
training), and the refusal paths are all already correct. There is no validation-based selection and
no early stopping anywhere. B5 alone does not block a run that is never interrupted; B3, B4 and B6
block any run whose artifacts must later be loaded into the campaign or whose provenance must be
honest.

---

# PART E — The pilot seed and artifact problem

## E.1 The mismatch, verified

Three declared sets exist in `configs/phase_8/campaign.yaml` (`verified`):

| set | values | count |
|---|---|---|
| `seeds.campaign` | 1–16 | 16 |
| `seeds.training` | 1001–1020 | 20 |
| `seeds.pilot` | 9001, 9002, 9003 | 3 |

They are pairwise disjoint, and `config.py:525–533` raises on any overlap. The certified random graphs
cover **campaign seeds 1–16 only**. The training-artifact loader accepts **only** seeds declared in
`seeds.campaign`. Pilot 2 is declared to run on the **pilot** seeds 9001–9003, and its arms include C,
C′, F and Fβ, which need a per-seed random graph and trained readout artifacts respectively.

`python -m experiments.phase_8.stages.run_stage pilot2 --describe` reports, verbatim (`executed`):

```
P2-G: no certified random graph exists for pilot seed(s) [9001, 9002, 9003]; certification covers
      the campaign seeds [1..16] only, so C and C' cannot run on the pilot grid and a campaign graph
      may not be substituted
P2-A: the training-artifact loader accepts only seeds declared in seeds.campaign, and no pilot seed
      is declared there; trained F, F-beta and E artifacts for the pilot seeds therefore cannot be
      loaded. Resolving this is an owner decision (a declared pilot training set or an approved
      change of the loader contract), never a silent substitution
P2-A: no trained artifact directory exists for pilot seed(s) [9001, 9002, 9003] under
      experiments/results/phase_8/training
```

The readiness record also reports `loader_accepts_seeds: []`, `training_artifacts.directories: 0`,
`certified_graphs.pilot_seed_coverage: {9001: false, 9002: false, 9003: false}`, `ready: false`.

**Pilot 1 is not affected.** Its plan is arm A only, three seeds × three episodes, and it declares
`certified_graph_needed: false`, `trained_artifact_needed: false` (`verified` in
`experiments/phase_8/stages/pilot1.py`, `describe_pilot1`). It needs only authorisation and memory.

## E.2 Why this is structural, not a bug

REV4 requires pilot 2 to estimate σ_C3 and σ_C4, which requires C and Fβ on the pilot grid; and
§3.8.6 requires A′ and C′ coverage on all three pilot seeds, which requires a pilot C graph. But
REV4 §10 never declares *which* graphs the pilot uses, and it explicitly states that pilot seeds are
"not reused as campaign seeds unless the protocol explicitly declares them to be part of the
campaign (it does not)" (§10, "What the pilots do and do not establish"). The result is a gap between
a requirement (pilot C needs a graph) and a declaration (only campaign graphs exist). Certification
for seeds 9001–9003 was never performed, and no protocol text authorises substituting a campaign
graph.

## E.3 The three legitimate resolutions

No fourth route exists that preserves both the protocol and the independence of the pilot.

### Option 1 — declare a separate pilot seed set with its own graphs and artifacts

Build and certify random graphs for seeds 9001–9003, and train F/Fβ artifacts for those seeds under a
declared pilot training set.

| aspect | assessment |
|---|---|
| What must be added | a protocol declaration that pilot graphs and pilot training artifacts exist for seeds 9001–9003; three new certified graphs produced under §9.3; trained F/Fβ artifacts produced under B3/B4/B6 |
| Reproducibility | good: each pilot graph gets its own certificate bound to `SeedSequence([20261116, 9001…9003, 4])`; each artifact records its training seed and schedule |
| Data leakage | none, provided the pilot training seeds are disjoint from campaign, evaluation and pilot evaluation sets — the config already rejects overlap, and a new `seeds.pilot_training` list would need the same check |
| Independence from confirmatory seeds | **complete**: pilot seeds 9001–9003 are disjoint from campaign seeds 1–16 |
| Implementation consequences | loader must accept the declared pilot training set (otherwise P2-A remains); `pilot2_readiness` must be extended; new tests; three BANC-scale graph builds (~2 min each) and their certification |
| Formal amendment required | **yes** — REV4 declares neither pilot graphs nor pilot training artifacts, and §9.3 currently blocks BANC-scale randomisation on this machine |
| Blocking gates today | memory (Part G), U18 approval (the generator implements an unapproved option), authorisation |

### Option 2 — formally amend the loader and seed contract

Two sub-variants exist, and they are not equivalent.

**(2a) Amend the loader to accept an explicitly declared pilot training set** (while keeping pilot
evaluation seeds 9001–9003). This is Option 1 without new graphs only if the pilot evaluation seeds
are changed to certified ones — which they are not. On its own, (2a) fixes P2-A but leaves P2-G
(pilot C has no graph) unresolved. It is therefore not sufficient by itself.

**(2b) Amend the protocol so that the pilot runs on three already-certified campaign seeds** (for
example 1, 2, 3), reusing their graphs and their trained artifacts.

| aspect | assessment |
|---|---|
| What must be added | an explicit protocol declaration that these seeds are part of both the pilot and the campaign |
| Reproducibility | good: graphs and artifacts already exist for these seeds and are hash-bound |
| Data leakage | no outcome leakage into training (the artifacts are trained on `seeds.training`, which stays disjoint), but the pilot and the campaign would **share evaluation units** |
| Independence from confirmatory seeds | **lost for the shared seeds**: σ would be estimated on cells that later enter the confirmatory test. A variance estimate is not an effect estimate, so this does not bias C1–C4 directly, but it means the pilot is no longer independent evidence, and the §10 statement that pilot seeds are not reused would have to be rewritten |
| Implementation consequences | smallest of all options: `pilot2_seeds` would read a declared list; P2-G and P2-A disappear; no new graph, no new artifact |
| Formal amendment required | **yes**, and it is the more consequential amendment because it changes the independence statement, not just a loader rule |
| Additional risk | three seeds is already the minimum; making them campaign seeds reduces the campaign's usable seed count if N = 16 is fixed and seeds 1–3 are "used twice" — the protocol would have to say whether they still count as campaign seeds |

### Option 3 — select pilot seeds from the eligible certified set "if scientifically permissible"

This is Option 2b stated as a selection rather than a contract change: choose three of seeds 1–16 as
the pilot seeds. It is only "scientifically permissible" if the protocol declares the reuse, because
REV4 §10 says the pilot seeds are not campaign seeds unless explicitly declared. Consequences are the
same as 2b: no leakage into training, reduced independence, full reproducibility, smallest
implementation change, formal amendment required. It is **not** permissible as a silent substitution.

## E.4 Comparison

| criterion | 1 (separate pilot set) | 2b / 3 (pilot on certified campaign seeds) |
|---|---|---|
| new graphs needed | 3, under §9.3 | none |
| new trained artifacts needed | F and Fβ for 3 pilot seeds | none |
| independence from confirmatory seeds | full | partial (shared evaluation units) |
| data leakage into training | none | none |
| reproducibility | full, if declared | full, already hash-bound |
| protocol amendment | yes | yes |
| blocked today by memory | yes | no (no new graph build) |
| blocked today by U18 | yes | only for new graphs; existing graphs already exist but U18 is still unapproved |
| earliest possible | after a compliant machine and U18 approval | after amendment only |
| cost | ~6 min graph builds plus certification, plus artifact training | near zero |

## E.5 What must not happen

- **No silent substitution** of a campaign seed for a pilot seed, or of a campaign graph for a pilot
  graph. Both are forbidden by the blocker text and by REV4 §10.
- **No untrained artifact** may stand in for F or Fβ: the loader refuses `origin != "trained"` unless
  `allow_synthetic_fixtures=True`, which exists only for tests and is refused in campaign mode
  (`training/loader.py:97–99, 141–149`).
- **No merge** of pilot rows into the campaign store; the pilots are recorded separately (REV4 §10).

## E.6 What the owner must record

Whichever option is chosen, the record must state: the pilot seed list; whether it overlaps
`seeds.campaign` and why that is acceptable; the pilot graph namespace and certificate hashes (Option
1) or the reused certificate hashes (2b/3); the pilot training seed list and its disjointness
(Option 1); the loader contract change, if any; and the exact protocol text amended.

---

# PART F — The G3 memory-gate deviation

## F.1 The requirement

REV4 §9.3 fixes a **4 GB free physical memory** gate and lists BANC-scale graph randomisation among
the operations blocked below it: "The gate is **4 GB of free physical memory**, and it is not
weakened, rounded down or waived." The campaign must re-check the reading immediately before starting
and record it; below the gate it does not start. The implementation measures
`psutil.virtual_memory().available / 1024³`, i.e. 4 GiB, and an unmeasurable reading counts as not
passed (`reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` §1).

## F.2 What exists, and what was observed

| fact | value | source |
|---|---|---|
| Condition C graphs built and certified | 16, campaign seeds 1–16 | `verified` by the campaign CLI this pass |
| graph SHA-256 and certificate SHA-256 matching their records | 16/16 | `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` §4.1; campaign CLI |
| `RUN_INCOMPLETE` markers | 0 | same |
| construction method recorded | `target_exchange` | certificates |
| structure seed derivation | `SeedSequence([20261116, seed, 4])`, one graph per seed shared by C, D, C′ | R18, certificates |
| structural gates | R4 0.997830–0.997944; R5 0.0010289–0.0010863; R6/R7 exact; R8 683,100 signed edges and 8,426,168 signed synapses; R9 sum 18,552,546, min 5, max 913; R9b exact; R10/R11 zero; R12 valid; R13 0.000297–0.000353 over 130,709 active nodes; R14 3.00e-05–6.92e-05; R17 byte-identical | `reports/PHASE_8_BANC_RANDOM_GRAPH_CAMPAIGN.md` §3–§6 |
| free memory during construction | **1.628–2.747 GiB**; low-water 1.628 (construction), 1.936 (runner) | `campaign_seed_summary.json` compliance block |
| construction preflight (separate safety check) | 0.75 GB floor, `allowed: true` for all 16 | same |
| peak RSS | 525.8–527.3 MB construction; 431.5–433.3 MB runner | same |
| recorded compliance status | `deviation_recorded`, `gate_weakened: false`, `construction_runs_below_gate: true` | same |
| runner wall time | 115.2–127.4 s per seed; 1,903.0 s for 16 | same |

## F.3 Why certification and memory compliance are separate

Certification asks: **is this graph the object its certificate claims?** Memory compliance asks:
**was the build performed under the rule the protocol set?** The first is a property of the artifact;
the second is a property of the run that produced it.

- A hash match proves the bytes have not changed since certification. It says nothing about how much
  memory was free at the time. The deviation is therefore a **compliance** defect, not a
  **corruption** defect (`reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` §4.3).
- The 0.75 GB construction preflight is the generator's own safety floor. Passing it does **not**
  satisfy §9.3, and failing §9.3 is not cured by passing it (§2 of the same report).
- Structurally, the null graphs satisfy every declared gate; scientifically, the deviation is about
  *when and how* they were built, not *what* they are. The report says this explicitly (§3).

## F.4 The three options and their consequences

### Option A — owner-approved amendment accepting the deviation

| aspect | assessment |
|---|---|
| What it establishes | nothing about compliance; it records that the set is certified with a bounded, disclosed deviation |
| Effect on artifacts | none; certificates remain valid |
| Science | unchanged: the graphs are the same objects; the limitation (component structure not preserved, R14 is a diagnostic not a mixing proof) stands independently |
| Reporting | the campaign and its final report must carry the deviation; the campaign cannot be described as §9.3-compliant |
| Risk | a reviewer may treat "accepted deviation" as a weakened gate. The record must state that the gate was not waived and that the builds' peak RSS (≈ 0.53 GB) is the safety evidence, not the rule |
| Cost | zero execution; one written record |

### Option B — full compliant regeneration on a compliant machine

| aspect | assessment |
|---|---|
| What it establishes | a build record with every seed started above 4.0 GiB |
| Effect on artifacts | the existing set must be preserved untouched; new namespaces only; `certify_banc` refuses an occupied namespace (exit 5) |
| Determinism | the generator is deterministic, so the new digests **should** equal the published ones; equality must be **observed**, and a mismatch is a finding to investigate, not a reason to overwrite |
| Requirements | measure before **each** seed; abort below the gate; sequential builds; recompute frozen-input hashes before and after; record the free-memory range and exit codes (report §6) |
| Cost | ≈ 31 min runner for 16 seeds plus certification; peak RSS ≈ 0.53 GB |
| Blocking gates | the machine must sustain ≥ 4 GiB; U18 approval or an explicit instruction that the rebuild is a compliance exercise independent of U18; protocol approval |

### Option C — deferral

Deferral is Option B later. It costs nothing now, leaves the deviation standing, and keeps the
campaign blocked. It is the only option compatible with the current machine, because a rebuild below
the gate would repeat the same violation.

**A fourth option — regenerate a subset — is not sufficient**: §9.3 applies to each build, and a
compliant subset does not make the set compliant (report §5, option C).

## F.5 What must not happen

No graph, certificate or namespace may be altered, moved, renamed or deleted; no subset regeneration
may be presented as compliance; the 0.75 GB preflight may not be described as satisfying §9.3; and
the deviation may not be described as resolved until a record exists. Nothing in this package
regenerates anything.

---

# PART G — Remaining environmental requirements

## G.1 Memory, measured now

| measurement | value | source |
|---|---|---|
| total physical memory | 15.342 GB | `psutil`, campaign CLI |
| available at the campaign preflight, 2026-11-20 | **2.141 GB** (86.0% used) | `python -m experiments.phase_8.run_campaign check` (`executed`) |
| available at the pilot 2 describe, 2026-11-20 | 2.188 GB (85.7% used) | `run_stage pilot2 --describe` (`executed`) |
| gate | 4.0 GiB | `campaign.yaml::budget.memory_gate_gb` |
| result | **failed**, margin ≈ −1.86 GB | same |
| historically recorded readings | 2.529–2.711 GiB (2026-11-18 readiness pass); 1.628–2.747 GiB during the G3 builds; ≈ 1.1 GB at the REV4 preflight; 0.5 GB at the original audit | readiness and G3 reports; REV4 §9.3 |

Every recorded reading, including the highest (2.747 GiB), is below 4.0 GiB. No measurement in the
repository's record has ever reached the gate.

## G.2 Can the current laptop satisfy it?

Only arithmetically, and only if a substantial amount of memory is released.

- The machine has 15.342 GB total, so 4 GiB free is physically possible: it requires total use to
  fall to roughly 73% or less. The current reading is 86%.
- The gate is a **threshold at an instantaneous preflight**, not an average over a run. A single
  higher reading satisfies it; a single lower reading at start blocks the run.
- No source in this repository states how much memory the machine can free, what processes hold the
  remaining ~13.2 GB, or whether a reboot, a closed application set or an added DIMM would reach the
  gate. **This package does not infer any of that.** The only defensible statement is: the gate is
  mathematically attainable on this hardware, and no recorded attempt has attained it.
- The §9.2 budget (13.9–61.7 h at N = 16, single process) also means the machine must sustain the
  gate for the **duration** of a multi-tens-of-hours campaign, not merely at start; the protocol
  requires a re-check immediately before starting, and the G3 rebuild requirements go further
  (measure before each seed).

## G.3 What must close before the preflight

From REV4 §9.3 and the G3 resolution report §6, the operational preflight is:

1. measure `psutil.virtual_memory().available` in bytes, divide by 1024³, record both GiB and bytes;
2. require **≥ 4.0 GiB**; an unavailable reading counts as not passed;
3. measure immediately before the operation starts (and, for graph builds, before each seed);
4. below the gate: do not start; record `pending resource availability` with the value and time;
   never mark the work complete;
5. sequential execution only for graph builds; no concurrent builds;
6. no substitute floor: the 0.75 GB construction preflight does not satisfy §9.3;
7. frozen-input hashes recomputed before and after any build;
8. the gate is not weakened, rounded down or waived.

## G.4 Other execution requirements named by the authoritative documents

| requirement | source | state |
|---|---|---|
| protocol approval at 10.0 before any confirmatory implementation is exercised | REV4 §10.0 | not approved |
| U1–U18 recorded | REV4 §12 | none |
| `design.n_seeds_selected` recorded | REV4 §7.1, §10.8 | null |
| B3–B6 recorded | REV4 (undeclared); code gate | none |
| G3 deviation resolved (record or compliant rebuild) | REV4 §9.3, §10.4 | unresolved |
| Python 3.13.14, numpy 2.3.4, pandas 2.3.3, matplotlib 3.10.7, PyYAML 6.0.3, psutil 7.1.2, torch 2.10.0+cpu | REV4 §2.3, §9.1 | present |
| gymnasium and Stable-Baselines3 | REV4 §9.1 | absent and **not required** under U5(a) |
| no GPU work | REV4 §2.3 | not required |
| append-only JSONL store, resume by `(condition, seed, episode)` | REV4 §8.3 | implemented |
| deterministic replay of one seed × episode per condition in a fresh process | REV4 §8.4 | implemented, not exercised on the substrate |
| 37-file protected hash baseline, 36 non-README files must match | REV4 §8.10, §6.10 | implemented; README pin drift is pre-existing |
| no result directory overwrite unless `--new-run-id` | REV4 §8.8 | implemented |
| pilot 1 before pilot 2 before campaign | REV4 §10 | not started |
| Phase 7 fingerprint `cca811f3…b2fb` reproduced from `conditions/a_fixed.py` at 213 updates | REV4 §10.2 | not attempted |
| the Phase 8 stage harnesses committed to the repository | repository state | **untracked** (`git status` read-only) |

---

# PART H — Decision dependency map

## H.1 Direct dependencies

```
REV4 approval (10.0)
├── every execution step (nothing may run before it)
├── U1–U18 recording ──┬── U14 ⇄ U15 ⇄ U16 (one family decision, three registers)
│                      ├── U4 ⇄ U18 ──► G3 deviation decision
│                      ├── U7 ◄── pilot 2 ◄── pilot graph/artifact contract (Part E)
│                      ├── U11 ⇄ U6 ⇄ U7 (budget, K, N)
│                      ├── U9 ⇄ U13 ⇄ A′ (plastic path certification)
│                      └── U3 ⇄ U17 (outcome and reporting thresholds)
├── B3 ⇄ B6 ⇄ B4 ⇄ B5 (training artifacts; B5 optional if never resumed)
└── memory gate (environment)
```

## H.2 Grouping

| group | items | why together |
|---|---|---|
| **must be resolved together** | U14 + U15 (+ U16) | family size, H3's single status, and Fβ's rollout are one decision chain; splitting them produces a document that is confirmatory in one register and exploratory in another, which REV4 §4 calls a defect that blocks authorisation |
| | U4 + U18 (+ G3 deviation) | the null model, its swap parameterisation and the compliance status of the existing graphs are the same object |
| | U7 + U11 + U6 | N's cost and statistical effect depend on K and the budget ceiling |
| | U9 + U13 + A′ | whether D's code path needs its own identity control depends on when plasticity runs |
| | B3 + B4 + B6 (+ B5) | training artifacts cannot be produced honestly without a pairing, an environment schedule and a resume policy |
| **independent** | U2 (η) | one value; no interaction with the family |
| | U5 (E implementation) | affects only E and E-full |
| | U8 (E-full inclusion) | exploratory only |
| | U10 (floor) | a control-policy decision; required by U1 but not dependent on it |
| | U12 (no `learning/` code) | repository hygiene; no statistical effect |
| | U17 (E3/E4 thresholds) | reporting convention; independent of U14 except that it qualifies the claim |
| **implementation-only** | U12 option (a) | preserves the current tree |
| | B5 values, B4 schedule values, B3 map values | config/call-site values once the owner records them |
| | the `protocol.py` conformance check and the tests that assert a null design | must be edited when U7 is recorded |
| **requires formal amendment** | G3 deviation acceptance (unless a compliant rebuild is done) | REV4 §9.3 says the gate is not waived; an acceptance must be recorded as an amendment or a bounded deviation |
| | the pilot seed/graph/artifact contract (Part E, any option) | REV4 §10 does not declare pilot graphs or pilot training artifacts, and forbids reusing campaign seeds without an explicit declaration |
| | enlarging pilot 2 beyond 3 seeds (needed for an N = 10 decision) | REV4 §7.1 says so explicitly; the declared pilot is 3 seeds |
| | U15 option (b), if chosen | edits §4, §5.3, §5.4, §7, §10 and the register together |
| **blocking pilot 1** | REV4 approval/authorisation; memory ≥ 4 GiB | pilot 1 needs no graph, no artifact and no design value |
| **blocking pilot 2** | Part E contract; U13 and U16 (C′ and Fβ on the pilot grid); U18 (pilot graphs, if built); B3/B4/B6 (F/Fβ artifacts); memory | plus everything that blocks pilot 1 |
| **blocking confirmatory execution** | U2, U3, U4, U5, U6, U7, U9, U10, U13, U14, U15, U16, U18; B3–B6; G3; memory; U11 budget | plus the campaign design itself |

## H.3 The shortest scientifically valid sequence

1. **Owner records REV4 approval (10.0) and authorises pilot 1 explicitly.** Pilot 1 estimates no
   contrast, so it does not need U7, U14, U18, G3 or B3–B6. It does need the protocol to authorise
   execution.
2. **Reach the memory gate (≥ 4.0 GiB) and record the reading.** Nothing at BANC scale starts before.
3. **Run pilot 1** (3 pilot seeds × A × 3 episodes), measure the substrate-free floor, and classify
   A against it. If A is floored, the U1-A … U1-E gate applies; under the REV4 recommendation, stop,
   report the floor plus the pathology decomposition, and request a scope decision (U1-B(b)). Do not
   proceed to a campaign.
4. **If A is above the floor**, resolve the pilot-2 inputs in this order:
   a. U18 (the null's swap parameterisation) and the G3 deviation decision, because both concern the
      graphs;
   b. the Part E contract — either certify pilot graphs and train pilot artifacts (Option 1) or
      amend the protocol to run the pilot on certified campaign seeds (Option 2b/3);
   c. B3, B4 and B6, so F/Fβ artifacts can be produced;
   d. U13 and U16, so C′ and Fβ are on the pilot grid.
5. **Produce the F/Fβ artifacts** for the pilot and campaign seeds under the recorded pairing,
   environment schedule and resume policy.
6. **Run pilot 2** (3 seeds × 7 arms × 3 episodes), verify A′ ≡ A and C′ ≡ C exactly, and report
   `σ_max` with its upper confidence limit. If the upper limit exceeds 112.87, N = 10 is not
   admissible; if it exceeds 142.8, N must be raised above 16.
7. **Record U7**, then edit `campaign.yaml`, the `protocol.py` conformance check and the tests that
   assert a null design, all in one act.
8. **Record the remaining decisions** (U1 branch, U2, U3, U5, U6, U8–U12, U14, U15, U17) and the
   U11 budget.
9. **Resolve the training artifacts for the campaign seeds** (F, Fβ, E, E-full), which is the first
   step that produces real trained artifacts.
10. **Start the campaign**; verify the first two seeds, A′ ≡ A and C′ ≡ C on every completed seed,
    then continue. Below the gate it does not start.
11. **Analyse** from the JSONL at the actual complete-pair N, then run the information analysis, then
    the report and freeze.

Steps 1–3 are the only path that can produce the first new experimental row, and they require exactly
two things that do not exist: an authorisation and 4 GiB of free memory.

---

# PART I — Owner decision sheet

Statuses are restricted to the five permitted labels. **No approval is pre-filled.** "Recommendation"
records what REV4 itself advises; it is not applied.

| ID | Subject | Action status | Recommendation on record (REV4) | Blocks |
|---|---|---|---|---|
| — | REV4 approval at 10.0 | PENDING OWNER DECISION | none — approval is the owner's act | everything |
| U1 | pilot floor gate cases and U1-B branch | RECOMMENDATION AVAILABLE | (b), then (d) once E exists; never (c) in Phase 8 | pilot 2 interpretation; campaign start after a floor |
| U2 | B/D η = 0.5 | RECOMMENDATION AVAILABLE | (a) | B/D execution |
| U3 | primary outcome = capped survival score | RECOMMENDATION AVAILABLE | (a) | every confirmatory number |
| U4 | confirmatory null = degree-preserving signed rewire | RECOMMENDATION AVAILABLE | (a) confirmatory; (b), (c) exploratory | C/D execution |
| U5 | E as direct REINFORCE | RECOMMENDATION AVAILABLE | (a) | E execution; H4; U1-E |
| U6 | K = 10 | RECOMMENDATION AVAILABLE | (a); (b) only if U11 caps the budget | episode plan; σ estimation |
| U7 | number of seeds N | PENDING OWNER DECISION | N = 16 primary; N = 10 only if pilot 2's UCL ≤ 112.87 | the campaign design |
| U8 | E-full exploratory | RECOMMENDATION AVAILABLE | (a) | E-full execution |
| U9 | plasticity during evaluation | RECOMMENDATION AVAILABLE | (a); (c) if budget allows | B/D execution |
| U10 | floor measured by replay | RECOMMENDATION AVAILABLE | (b) | U1 gate; §7.8 rule |
| U11 | compute budget ceiling | RECOMMENDATION AVAILABLE | (a) | duration authorisation |
| U12 | no new `learning/` implementation | RECOMMENDATION AVAILABLE | (a) | repository scope |
| U13 | C′ on all N × K | RECOMMENDATION AVAILABLE | (a) | D interpretability |
| U14 | Holm family m = 4 (with C4) | PENDING OWNER DECISION | m = 4 | family size; decoding claim |
| U15 | H3 confirmatory, one status | RECOMMENDATION AVAILABLE | (a) | C1's status in every register |
| U16 | Fβ full N × K, genuinely state-independent | RECOMMENDATION AVAILABLE | (a) if U14 = m = 4 | C4 feasibility |
| U17 | E3/E4 thresholds | RECOMMENDATION AVAILABLE | (a) | readout claim wording |
| U18 | target exchange for the null | RECOMMENDATION AVAILABLE | (a) | C/D graph identity; G3 |
| B3 | campaign↔training seed pairing | IMPLEMENTATION CONTRACT UNRESOLVED | none — REV4 declares no map | F/Fβ/E artifacts |
| B4 | training-episode environment-seed schedule | IMPLEMENTATION CONTRACT UNRESOLVED | none — REV4 declares no schedule | training runs |
| B5 | checkpoint cadence, retention, format | IMPLEMENTATION CONTRACT UNRESOLVED | none — REV4 declares nothing | resumability only |
| B6 | RNG and optimizer-state restoration | IMPLEMENTATION CONTRACT UNRESOLVED | none — REV4 declares nothing; (a) is permitted if disclosed | what a resumed artifact may claim |
| E-P1 | pilot graphs and pilot artifacts (Part E, Option 1) | REQUIRES FORMAL AMENDMENT | none | pilot 2 |
| E-P2 | loader/seed contract or pilot-on-campaign-seeds (Part E, Option 2b/3) | REQUIRES FORMAL AMENDMENT | none | pilot 2 |
| G3 | accept deviation, compliant rebuild, or defer | REQUIRES FORMAL AMENDMENT | defer now; rebuild only above the gate | campaign compliance; C/D use |
| MEM | free memory ≥ 4.0 GiB at the immediate preflight | ENVIRONMENTAL BLOCKER | n/a | everything at BANC scale |

All 22 protocol and training items above are, today, in protocol status **PROPOSED — not approved**.
The action status column describes what the owner must do, not what the protocol says.

---

## Appendix — Verification performed for this package

| check | result |
|---|---|
| REV4 SHA-256 | `e4aa9e0f…1547c`, unchanged (`verified`, `sha256sum`) |
| REV3 SHA-256 preserved | `ad907827…b82b9cf` (`reported`) |
| campaign config SHA-256 | `b9a2d3d5…3477e19`, unchanged; values match REV4 Appendix C (`verified`) |
| conditions / environment config hashes | `9a93f047…d42f671` / `b391ecf7…3281dc` (`verified`) |
| U1–U18 wording | compared line by line with REV4 §12 and §12.1 (`verified` by reading lines 1555–1833) |
| B3–B6 | compared with `training_stage.py` declaration blockers and `training/gate.py`; CLI output reproduced verbatim (`executed`) |
| G3 graphs | 16/16 certified, 0 markers, `target_exchange`, campaign seeds 1–16 (`executed`) |
| pilot 2 readiness | P2-G and P2-A reproduced verbatim; `ready: false` (`executed`) |
| campaign conformance | 69/69; `design_resolved: false`; `executable: false` (`executed`) |
| memory | 2.141 GB and 2.188 GB in two independent read-only calls (`executed`) |
| Phase 8 tests | 402 passed (`executed`) |
| full suite | 1,472 passed, 3 skipped, 6 pre-existing failures (`executed`) |
| experiments run | none; `experiments/results/phase_8/` does not exist (`verified`) |
| files modified | none except this document and its companion report (`verified`) |
| Git operations | none; `git status` read only (`verified`) |
