# Phase 8 protocol decision register (U1–U18 plus undeclared training inputs)

**Date:** 2026-11-18
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines)
**Register status:** **NO ITEM IS APPROVED. NO ITEM IS APPLIED.**
**What this document is:** a register of what REV4 §12 already proposes, what remains unresolved, what each
choice would change technically and scientifically, and what the implementation currently does.
**What this document is not:** an approval, an amendment to REV4, or authorisation to execute anything.

REV4 §12 states that U1–U18 are **PROPOSED — awaiting human approval** and that "nothing in this
document may be cited as an approval, and no implementation step that depends on a confirmatory choice
may run before the user records one." This register preserves that status. Where the implementation
already contains a mechanism consistent with a proposed option, that is recorded as *implementation
state*, not as approval: a mechanism built against a proposal is still gated by
`experiments/phase_8/training/gate.py::assert_training_authorized` and by
`experiments/phase_8/campaign/protocol.py::approval_status`.

Two additional facts frame every entry:

1. **REV4 itself is unapproved.** Its status line reads "NOT APPROVED, NOT EXECUTABLE", and its
   closing paragraph authorises no execution. Approving U1–U18 individually would not by itself
   approve REV4; the protocol freeze is step 10.0 and has its own approval.
2. **`design.n_seeds_selected` is `null`.** No campaign design exists until the 10.8 pilot decision
   is recorded. `training/gate.py::assert_design_resolved` and
   `campaign/registry.py::evaluation_plan` both raise on this state rather than defaulting.

---

## 1. Register summary

| ID | Subject | REV4 status | Approval required | Implementation state | Execution blocked by this item alone |
|---|---|---|---|---|---|
| U1 | Five pilot gate cases; U1-B branch | PROPOSED | **yes** | Five-case logic exists in `evaluation/viability.py`; no campaign code consumes it | no (pilot 1/2 gating is procedural) |
| U2 | B/D eta = 0.5 | PROPOSED | **yes** | `configs/phase_8/conditions.yaml` declares 0.5 | yes — sets plasticity strength |
| U3 | Primary outcome = capped survival score | PROPOSED | **yes** | `analysis.py` computes the capped score | yes — defines the confirmatory outcome |
| U4 | Confirmatory null = degree-preserving signed rewire | PROPOSED | **yes** | Target-exchange generator and certificates exist | yes — defines C and D |
| U5 | E implemented directly as REINFORCE | PROPOSED | **yes** | `evaluation/conventional.py`, `training/engine.py` | yes — E/E-full cannot run |
| U6 | K = 10 evaluation episodes | PROPOSED | **yes** | `campaign.yaml` declares `episodes_per_seed: 10` | yes — episode plan |
| U7 | N = 16 primary; N = 10 fallback | PROPOSED | **yes** | `n_seeds_selected: null`; both N declared | yes — no design exists |
| U8 | E-full exploratory, capacity-matched | PROPOSED | **yes** | `E_full` in conditions and registry | no (exploratory only) |
| U9 | B/D plasticity during evaluation | PROPOSED | **yes** | `conditions/d_plastic.py` installs the plastic hook per episode | yes — defines B/D evaluation |
| U10 | Floor = substrate-free game-side replay | PROPOSED | **yes** | `controls/floor.py`; `floor` arm in registry | yes — floor is a contrast reference |
| U11 | Compute budget ≈ 8.9–38.8 h / 13.9–61.7 h; 4 GB gate unchanged | PROPOSED | **yes** | Documented only | yes — resource authorisation |
| U12 | No new `learning/` implementation | PROPOSED | **yes** | `learning/` untouched | no, if (a) is approved |
| U13 | C′ on all N × K at eta = 0 | PROPOSED | **yes** | `controls/c_prime.py`; mirror in factory | yes — D certification |
| U14 | Holm family m = 4 including C4 | PROPOSED | **yes** | Both `[4, 3]` declared; analysis requires caller choice | yes — family size |
| U15 | H3 confirmatory, exactly one status | PROPOSED | **yes** | REV4 uses one status; no code choice | yes — interpretability of C1 |
| U16 | Fβ full N × K, genuinely state-independent | PROPOSED | **yes** | `controls/f_beta.py`; `validation.py` enforces bias-only | yes — C4 definition |
| U17 | E3/E4 thresholds 1% / half seeds, 10%, 0/0 not evaluable | PROPOSED | **yes** | `analysis.py` constants 0.01, 0.5, 0.10; 0/0 not evaluable | no (post-campaign reporting) |
| U18 | Target exchange for the null | PROPOSED | **yes** | Implemented; 16 graphs certified **before approval** | yes — C/D graph identity |
| B3 | Campaign↔training seed pairing | **not declared in REV4** | **yes** | `training/seeding.py::validate_pairing` requires a caller map | yes — F/Fβ/E artifacts |
| B4 | Training-episode environment-seed schedule | **not declared in REV4** | **yes** | `training/engine.py` takes a callable or integer | yes — F/Fβ/E training |
| B5 | Checkpoint cadence, retention, format | **not declared in REV4** | **yes** | `training/checkpoint.py` takes caller cadence/root | no (can run without checkpoints) |
| B6 | RNG and optimizer-state restoration | **not declared in REV4** | **yes** | Every checkpoint records `rng_restored=false`, `optimizer_state_restored=false` | no (resume is parameter-continuous only) |

"Execution blocked by this item alone" means: if everything else were approved, would this unresolved
item still prevent the confirmatory campaign? Items marked "no" can be resolved later without changing
a contrast, but they still require approval before their own stage runs.

---

## 2. Detailed entries, U1–U18

Each entry reproduces the REV4 wording (quoted), states the unresolved issue, lists every option that
REV4 leaves open, and records technical consequences, scientific consequences, the advisory
recommendation, and the approval requirement. **The recommendation is advisory and is not applied.**

### U1 — action if the pilot confirms the floor

*Protocol reference:* REV4 §0, §3.6.2, §6.9, §10.3, §12 "U1"; REV4 §12 table row U1.

*Existing wording (REV4 §12):* "five gate cases for the pilot floor (U1-A … U1-E: both above / both
floored / A floored only / F floored only / both floored with E above); C and D reported, never gated;
floor is a substrate-free game-side control".

| case | A | F | E-matched | declared action |
|---|---|---|---|---|
| U1-A | above floor | above floor | — | proceed; gate passed |
| U1-B | floored | floored | any | platform floor: run the predeclared floor decomposition and stop for a scope decision; no effect may be claimed for any neural condition |
| U1-C | floored | above floor | — | readout rescues the platform: proceed, report A's floor and F's success as readout-specific, not as substrate evidence |
| U1-D | above floor | floored | — | readout harms: proceed with the readout contrast, report F's failure, Fβ is not the floor |
| U1-E | floored | floored | above floor | environment solvable but not from this interface; report A–D as an interface limitation |

*Unresolved issue:* the gate cases themselves are proposed, not approved; and the branch to take when
U1-B occurs is unresolved. REV4 offers four branches: (a) run the campaign anyway and report a floor
result; (b) stop, report the floor plus a pathology decomposition, request a scope decision;
(c) authorise a separate pre-registered follow-up that changes drive or decoder; (d) if A and F floor
but E-matched does not, run only E and report the environment solvable-but-not-from-this-interface.

*Technical consequences:*
- (a) produces a complete dataset whose primary contrasts are guaranteed to be degenerate on the
  floored arms and consumes the full budget.
- (b) requires only the pilot artifacts and the floor replay; no further execution; the stop is
  recorded as a protocol outcome, not a failure.
- (c) is a new experiment with a new pre-registration; it is explicitly Phase 9 and cannot be executed
  inside Phase 8.
- (d) requires E-matched training and evaluation, which U5/U9 gate anyway.
- In all branches, C and D remain reported-only; no C/D outcome can authorise or block the campaign.
- The current `evaluation/viability.py` implements the five-case classification as a read-only report;
  no campaign code consults it, so the stop is a stage-level procedural decision at 10.8, not an
  automatic runner refusal.

*Scientific consequences:* (b) prevents a campaign that would produce only null, floored contrasts
being reported as evidence about the connectome. (a) risks exactly that misinterpretation. (d) is the
only branch that separates "the substrate cannot act" from "the interface cannot act" using a
competent learner, but it reports no neural-substrate result. (c) is the only branch that could repair
the interface, and it cannot be part of this phase without invalidating the pre-registration.

*Recommendation (advisory, from REV4 §12):* **(b), then decide with the user; (d) is a legitimate
refinement of (b) once E results exist. Never (c) inside Phase 8.**

*Approval required:* **yes.** The five cases, the reporting-only status of C/D, and the U1-B branch
must be recorded by the user before pilot 2 is interpreted or any stop decision is taken.

### U2 — eta for B and D

*Protocol reference:* REV4 §3.4, §6.7, §12 "U2"; `configs/phase_8/conditions.yaml` (`plasticity.eta: 0.5`).

*Existing wording:* "B/D eta = 0.5 (Phase 5 declared value); no tuning on the game".

*Unresolved issue:* whether to accept Phase 5's declared 0.5, re-derive eta on the game, or add a
second declared eta as an exploratory arm.

*Options:* (a) reuse 0.5; (b) re-derive on the game; (c) add a second declared value from `{0.1, 1.0}`
as an exploratory arm.

*Technical consequences:* (a) uses the existing Phase 5 mechanism unchanged; (b) requires a search
procedure that is itself a design choice and would consume episodes before the campaign; (c) roughly
doubles B/D cost and adds two arms to every seed.

*Scientific consequences:* (a) is pre-declared and cannot be accused of tuning. (b) is tuning on the
game and confounds plasticity strength with selection. (c) is unlikely to inform, because Phase 5 found
0.1–2.0 indistinguishable.

*Recommendation (advisory):* **(a) 0.5.**

*Approval required:* **yes.** The value is declared in config but remains unapproved.

### U3 — primary outcome

*Protocol reference:* REV4 §5.1, §7.2, §12 "U3".

*Existing wording:* "primary outcome is the **capped survival score** `min(updates, 900)`, not
right-censored survival".

*Unresolved issue:* whether the primary is the capped score, total task reward, or capped survival
with reward as co-primary.

*Options:* (a) capped survival score in updates, `min(observed_updates, 900)`; (b) total task reward;
(c) capped survival with reward as co-primary.

*Technical consequences:* (a) is bounded, uses an existing game quantity, and needs no censoring
machinery; the 900 cap is the game update ceiling. (b) changes the analysis to a different scalar and
requires reward provenance to be complete per episode. (c) requires two primary outcomes and changes
the family definition.

*Scientific consequences:* (a) is not right-censored survival and must never be described as such; a
time-to-event analysis, if retained, is a separate declared sensitivity analysis. (b) compares
conditions on a signal dominated by coins, which are entirely unmodelled in the sensory drive, so no
neural condition can reach it. (c) breaks the single-primary discipline and makes the Holm family
depend on an outcome choice.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes.** The primary outcome defines every confirmatory number.

### U4 — random-null scope

*Protocol reference:* REV4 §3.3, §12 "U4"; `experiments/phase_8_random/target_exchange.py`.

*Existing wording:* "confirmatory null is the degree-preserving signed rewire; component- and
sign-randomised variants exploratory".

*Unresolved issue:* whether the confirmatory null is the degree-preserving signed rewire only, or also
a component-preserving variant and/or a sign-randomised variant.

*Options:* (a) degree-preserving signed rewire only; (b) also component-preserving (swaps restricted
within original weak components), exploratory; (c) also sign-randomised (node signs re-drawn at the
observed verified fraction), exploratory and labelled as a sign question.

*Technical consequences:* (a) is what is built and certified (16 graphs). (b) requires a second
generator with a component constraint and its own R-gates. (c) requires a sign re-draw generator and a
different preservation certificate; it cannot reuse the R8 gate unchanged.

*Scientific consequences:* (a) answers "does wiring matter?" with wiring only. (b) separates wiring
from fragmentation. (c) answers "does sign assignment matter?", a different question, and must not be
pooled with (a). Component structure (R15) is reported for every graph regardless.

*Recommendation (advisory):* **(a) confirmatory; (b) and (c) exploratory only.**

*Approval required:* **yes.** U18 (the swap parameterisation) is coupled to this item.

### U5 — condition E implementation

*Protocol reference:* REV4 §3.5, §9.1, §12 "U5"; `evaluation/conventional.py`, `training/engine.py`.

*Existing wording:* "E implemented directly as REINFORCE against the 5-tuple API; no Gymnasium/SB3
install".

*Unresolved issue:* direct REINFORCE versus wrapping the game for Stable-Baselines3.

*Options:* (a) direct REINFORCE against the existing 5-tuple API, no installs; (b) install Gymnasium +
Stable-Baselines3 and wrap the game.

*Technical consequences:* (a) uses the present numpy/torch stack and the existing environment
contract; no new dependency, no version pinning, no wrapper surface. (b) adds two dependencies and a
wrapper that must be re-validated against the same five-tuple semantics; the campaign's determinism
and provenance checks would have to cover the wrapper.

*Scientific consequences:* (a) gives a competent reference learner on the same observations, which is
all E needs. (b) adds a library's internal choices (GAE, clipping, vectorisation) as an unexamined
confound and does not improve the comparison.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes.** Until approved, `training/engine.py` and `training/gate.py` refuse every
training call.

### U6 — evaluation episode count K

*Protocol reference:* REV4 §7.1, §7.2, §12 "U6"; `campaign.yaml` (`episodes_per_seed: 10`).

*Existing wording:* "K = 10 evaluation episodes per seed".

*Unresolved issue:* K = 10, 5 or 20.

*Options:* (a) 10; (b) 5; (c) 20.

*Technical consequences:* K affects only within-seed precision, not the degrees of freedom, because the
seed is the unit of analysis. At the measured ~22 s per episode, K = 10 is ≈ 3.7 min per seed per
condition; K = 20 doubles that; K = 5 halves it. K changes the runtime of every arm and the pilot.

*Scientific consequences:* a smaller K increases the variance of each seed's mean, which propagates
into the paired differences and hence into σ_max and the N decision. It does not change the primary
test's validity. Choosing K after seeing data would be selecting on the result.

*Recommendation (advisory):* **(a) K = 10; (b) only if U11 caps the budget, declared in advance.**

*Approval required:* **yes.**

### U7 — number of seeds N

*Protocol reference:* REV4 §7.1, §7.4, §10.8, §11.33, §12 "U7"; `campaign.yaml`
(`n_seeds_primary: 16`, `n_seeds_fallback: 10`, `n_seeds_selected: null`, `fallback_max_paired_sd: 112.87`).

*Existing wording:* "**N = 16 primary**; N = 10 only as the predeclared fallback of §7.1, with the
pilot including B and `σ_max` governing the decision".

*Unresolved issue:* which N the campaign uses. This is the item that leaves `n_seeds_selected` null.

*Options:* (a) N = 16 primary; (b) N = 10 predeclared fallback; (c) N = 20.

*Technical consequences:* (a) doubles the sign-flip vector count to 65,536, gives a minimum two-sided
p of 3.05e-5, and costs the N = 16 budget line. (b) gives 1,024 vectors and a minimum p of 1.95e-3;
it is admissible only if `σ_max ≤ 112.87` can be defended. (c) exceeds the declared design and the
declared budget.

*Scientific consequences:* the N decision governs the attainable p-values, the Holm thresholds at the
actual N, and the power against the 100-update SEI. Choosing N after seeing campaign outcomes is
forbidden. A 3-seed pilot has df = 2 and an 80% upper confidence limit ≈ 2.1× its point estimate, so
it generally cannot defend N = 10; REV4 requires a larger pilot (≥ 5 seeds) or independent variance
evidence for that branch.

*Recommendation (advisory):* **(a) N = 16, unless the 10.8 pilot's upper confidence limit supports the
112.87 bound; section 3 below records the exact resolution procedure and does not apply it).**

*Approval required:* **yes**, at 10.8, before any campaign outcome is seen.

### U8 — E-full (14 features)

*Protocol reference:* REV4 §3.5, §12 "U8"; `conditions.yaml` (`exploratory.E_full`), `registry.py`.

*Existing wording:* "E-full (14 features) included as exploratory, capacity-matched to E-matched".

*Unresolved issue:* include E-full or not.

*Options:* (a) yes, exploratory; (b) no.

*Technical consequences:* (a) adds an arm with the same architecture and training budget as E; it uses
the 14-feature encoder instead of the 7-feature matched encoder. It is recorded as `E_full`, never
merged into `E`. (b) removes it and its cost.

*Scientific consequences:* (a) quantifies what the 7 unmapped features would be worth; it cannot
support a confirmatory claim. Capacity must match E exactly or the comparison is confounded.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes** (exploratory arms still require approval before training).

### U9 — B/D plasticity during evaluation versus train-then-freeze

*Protocol reference:* REV4 §3.4, §6.7, §12 "U9"; `conditions/d_plastic.py`, `conditions/plasticity_hook.py`.

*Existing wording:* "B/D plasticity runs during evaluation (primary); train-then-freeze exploratory
only".

*Unresolved issue:* whether plasticity is online during evaluation, frozen after training, or both.

*Options:* (a) plasticity runs during evaluation (Phase 5 behaviour); (b) train, freeze, evaluate;
(c) both.

*Technical consequences:* (a) uses the existing plastic stepper and hook for the whole episode; the
weight state changes within evaluation, so the readout fingerprint is not constant across an episode.
(b) requires a separate training phase, a freeze point, and held-out seeds. (c) doubles B/D runtime
and requires both paths to be certified.

*Scientific consequences:* (a) measures the closed loop as specified and is the only option that does
not misrepresent an online mechanism as an offline one. (b) alone is a different experiment. If (b)
or (c), the frozen evaluation must use held-out seeds for both training and freeze point, or the
reported result is a training-set score.

*Recommendation (advisory):* **(a) primary; (c) only if budget allows, with (b) labelled
exploratory.**

*Approval required:* **yes.**

### U10 — no-action baseline

*Protocol reference:* REV4 §3.6.2, §6.9, §12 "U10"; `controls/floor.py`, `campaign/registry.py`.

*Existing wording:* "no-action floor is a **substrate-free game-side control policy**, measured by
replay, never a neural arm".

*Unresolved issue:* derive the floor analytically or measure it by replay.

*Options:* (a) derive from the game configuration without replay; (b) replay the paired environment
seeds with a constant `NO_ACTION` policy.

*Technical consequences:* (a) costs nothing but is not valid, because collision timing depends on
obstacle layout. (b) costs seconds, produces no simulation rows, and must use the same paired
environment seeds as the neural arms; it is never budgeted as a condition and never counted as a
neural arm.

*Scientific consequences:* (a) is the V1 error REV4 corrects; an analytic floor would be a guess.
(b) yields an empirical floor that can be compared with each arm on the same seeds.

*Recommendation (advisory):* **(b), as a control policy.**

*Approval required:* **yes.**

### U11 — compute budget ceiling

*Protocol reference:* REV4 §9.2, §9.3, §12 "U11".

*Existing wording:* "planning budget ≈ 8.9–38.8 h (N = 10) / ≈ 13.9–61.7 h (N = 16), single process; no
weakening of the 4 GB memory gate".

*Unresolved issue:* accept the estimate, cap it by K = 5 and dropping Fβ training, or parallelise.

*Options:* (a) accept §9.2; (b) cap by K = 5 and no Fβ training rollouts; (c) parallelise with a
determinism audit.

*Technical consequences:* (a) requires the machine to be above the 4 GB gate for the duration and to
tolerate a multi-tens-of-hours single process. (b) reduces precision and, for Fβ, removes C4's
feasibility. (c) requires per-process thread pinning, per-process memory checks, and a byte-identical
determinism check; not part of the primary plan.

*Scientific consequences:* (b) changes K and the confirmatory family, so it is a design change, not
merely a cost saving. (c) does not change the design but introduces a new failure mode if determinism
is not exact.

*Recommendation (advisory):* **(a) as the planning figure; consider (c) only after the pilot, with
thread pinning and a byte-identical check.**

*Approval required:* **yes.** The budget is not an authorisation to run; §9.3 still applies.

### U12 — whether Phase 8 may write a new `learning/` implementation

*Protocol reference:* REV4 §2.3, §12 "U12"; repository `learning/` package.

*Existing wording:* "Phase 8 does not write a new `learning/` implementation".

*Unresolved issue:* keep `learning/dopamine.py`, `learning/synaptic_plasticity.py` and
`learning/mutual_information.py` untouched, or fill them with Phase 8 code.

*Options:* (a) leave them untouched; (b) fill them.

*Technical consequences:* (a) keeps all Phase 8 code in `experiments/phase_8/`, `readout/`,
`experiments/phase_8_random/` and `evaluation/`. (b) creates a second plasticity implementation
alongside Phase 5's.

*Scientific consequences:* (b) violates the project's no-duplicate-modules constraint and implies the
Phase 5 mechanism is being replaced; it would make provenance ambiguous. (a) preserves one mechanism.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes** (confirmatory choice only in the sense that it fixes where Phase 8 code
lives; no execution depends on it beyond U12 itself).

### U13 — C′ mirror for condition D

*Protocol reference:* REV4 §3.8, §3.8.5, §10.6, §12 "U13"; `controls/c_prime.py`,
`campaign/factory.py`.

*Existing wording:* "C′ on **all N × K** at eta = 0 through the actual plasticity pathway, same P1–P19
and hard stop as A′; pilot and campaign coverage consistent".

*Unresolved issue:* full C′ coverage, sampled coverage, or no C′.

*Options:* (a) C′ on all N seeds × K episodes, eta = 0 through the actual pathway, same P1–P19 and
hard stop; (b) C′ on pilot seeds plus episode 1 of every campaign seed; (c) omit C′, rely on A′.

*Technical consequences:* (a) costs about one condition's runtime and requires the plastic path to run
with zero delta, not a bypass. (b) halves the evidence. (c) leaves D's own code path unvalidated.

*Scientific consequences:* (a) converts "D shares validated code" into "D shares code validated on
its own graph". (b) is defensible only if D is reported without causal attribution. (c) leaves the
only unvalidated path in the campaign.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes.**

### U14 — confirmatory family size

*Protocol reference:* REV4 §5.3, §7.5, §12 "U14"; `campaign.yaml` (`holm_family_sizes: [4, 3]`),
`analysis.py`.

*Existing wording:* "confirmatory family m = 4, including C4 = F − Fβ".

*Unresolved issue:* m = 4 or m = 3.

*Options:* (a) m = 4 with C4; (b) m = 3 without C4, C4 demoted to exploratory.

*Technical consequences:* (a) requires Fβ to have full N × K rollouts and a paired difference
(U16). (b) removes Fβ's confirmatory role and changes every Holm threshold; the analysis accepts either
but requires the caller to state which was used.

*Scientific consequences:* (a) makes the readout claim identifiable; without C4, a bias term alone
could produce F − A > 0 with silent motor populations. (b) is coherent but means no decoding claim may
be made at all, because §3.6.4 requires a Holm-surviving test and an exploratory contrast cannot supply
one.

*Recommendation (advisory):* **(a) m = 4.**

*Approval required:* **yes**, before data.

### U15 — confirmatory status of H3

*Protocol reference:* REV4 §4, §5.3, §5.4, §7, §10, §12 "U15".

*Existing wording:* "H3 **confirmatory**, exactly one status in every register, contingent on U14/U15
being resolved before data".

*Unresolved issue:* H3 confirmatory or exploratory.

*Options:* (a) H3 confirmatory, one status everywhere; (b) H3 exploratory, in which case C1 must leave
the confirmatory family, m changes, and every Holm threshold and the analysis plan must be edited
together.

*Technical consequences:* (a) is consistent with C1 being confirmatory. (b) requires edits to §4,
§5.3, §5.4, §7, §10 and this register; a document that says confirmatory in one place and exploratory
in another is defective and blocks authorisation.

*Scientific consequences:* (a) makes the readout question one of the three the phase exists to answer.
(b) removes it from the confirmatory set.

*Recommendation (advisory):* **(a), exactly one status.**

*Approval required:* **yes.**

### U16 — scope of Fβ

*Protocol reference:* REV4 §3.6.2, §3.6.3, §3.6.4, §12 "U16"; `controls/f_beta.py`,
`training/validation.py`.

*Existing wording:* "Fβ full N × K rollout, **genuinely state-independent** (feature weights fixed 0,
only output biases trainable); no hidden or state pathway".

*Unresolved issue:* full Fβ rollouts, pilot-only plus counterfactual, or no Fβ rollouts.

*Options:* (a) all N × K, full training, genuinely state-independent, mirroring F; (b) pilot seeds plus
the ablation counterfactual on every F decision; (c) no Fβ rollouts.

*Technical consequences:* (a) requires a bias-only readout whose fixed feature weights are exactly 0,
with `validation.py` enforcing that any feature pathway training disqualifies the arm. (b) cannot
supply a paired per-seed difference at N. (c) answers neither the mechanism nor the behavioural
question.

*Scientific consequences:* (a) supports C4. (b) is acceptable only if C4 is dropped, and then no
decoding claim is possible. (c) answers the mechanism question but not the behavioural one. A
"bias-only" label is valid only when only output biases train.

*Recommendation (advisory):* **(a) if U14 selects m = 4.**

*Approval required:* **yes.**

### U17 — declared thresholds in the readout evidence bar

*Protocol reference:* REV4 §3.6.4, §12 "U17"; `analysis.py`
(`E3_MIN_DECISION_FRACTION = 0.01`, `E3_MIN_SEED_FRACTION = 0.5`,
`E4_MIN_MOTOR_DRIVEN_FRACTION = 0.10`).

*Existing wording:* "readout evidence bar E3/E4 at the declared low thresholds (≥ 1% of decisions,
≥ half of seeds; ≥ 10% motor-driven), with 0/0 reported as not evaluable".

*Unresolved issue:* accept as stated, tighten, or loosen.

*Options:* (a) accept 1% / half of seeds and 10%; (b) tighten to 5% and 25%; (c) loosen to any single
motor spike and 1%.

*Technical consequences:* the thresholds are constants in `analysis.py` and are applied per seed for
E3 and per non-`NO_ACTION` decision for E4. E4 with zero non-`NO_ACTION` decisions is reported as
"not evaluable (0/0)", never a pass.

*Scientific consequences:* (a) is deliberately low because the expected regime has zero motor spikes;
(c) would let one spike license a decoding claim; (b) risks being unreachable even if a real effect
exists.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes** (reporting convention, but it gates the readout claim).

### U18 — swap parameterisation for the degree-preserving null

*Protocol reference:* REV4 §3.3.1, §11.23, §12 "U18"; `experiments/phase_8_random/target_exchange.py`,
`certification.py`.

*Existing wording:* "degree-preserving null uses **target exchange** (sources and weights fixed,
targets swapped), preserving R9b; endpoint re-pairing rejected".

*Unresolved issue:* target exchange versus endpoint re-pairing.

*Options:* (a) target exchange — each edge keeps its source and weight; a swap exchanges targets of
two edges from distinct sources with distinct targets; (b) endpoint re-pairing — both source and target
re-paired, weight carried by the edge.

*Technical consequences:* (a) preserves out-degree, in-degree, weight multiset, per-source weight
profile (R9b) and per-node sign vectors exactly by construction; the 16 certified graphs implement (a).
(b) does not preserve per-source weight sums, so R9b becomes descriptive and R8's signed-synapse total
becomes a reported quantity; it would require a new generator and new certificates.

*Scientific consequences:* (a) makes the null "wiring only" with degree and weight structure fixed.
(b) is a valid null but answers a different question and would invalidate the current certificates.
Either choice must be written into the config and every `randomization_quality` block. R14 remains a
diagnostic, not a mixing proof.

*Recommendation (advisory):* **(a).**

*Approval required:* **yes.** **Recorded deviation:** the 16 graphs were generated and certified under
option (a) **before approval**. They are not withdrawn, but they are not evidence of an approved
decision. See `PHASE_8_G3_DEVIATION_RESOLUTION.md`.

---

## 3. `n_seeds_selected`: documented recommendation, not applied

### 3.1 Current state

| Item | Value |
|---|---|
| `configs/phase_8/campaign.yaml` → `design.n_seeds_selected` | `null` |
| `design.n_seeds_primary` | 16 |
| `design.n_seeds_fallback` | 10 |
| `design.fallback_max_paired_sd` | 112.87 (= 100·√10 / 2.801585) |
| `design.episodes_per_seed` | 10 |
| `campaign/protocol.py::validate_campaign` | asserts `n_seeds_selected` **is null** ("pre-pilot state") |
| `training/gate.py::assert_design_resolved` | raises `DesignUnresolvedError` while null |
| `campaign/registry.py::evaluation_plan` | raises while null |
| `analysis.py` | accepts either value; requires the actual paired N to equal the selected N |

This is not an accident: the code is written to refuse to invent a design. Any change to
`n_seeds_selected` is therefore a **design-resolution act**, not a configuration tweak, and it
requires the user's record.

### 3.2 The decision rule REV4 declares

REV4 §7.1 and §7.4 define the fallback precisely:

```
σ_max = max(σ_paired,C1, σ_paired,C2, σ_paired,C3, σ_paired,C4)
N = 10 permitted only if 2.8016 · σ_max / √10 ≤ 100, i.e. σ_max ≤ 112.87,
and only if that bound can be defended from the pilot's uncertainty.
```

The pilot's σ must come from a design that includes **B** (for C2), **C** (for C3) and **F/Fβ**
(for C1 and C4). A 3-seed pilot has df = 2; its 80% upper confidence limit is ≈ 2.1× the point
estimate. Consequently, with the declared 3-seed pilot at 10.8, N = 10 would require a point estimate
of roughly

```
σ̂_max ≤ 112.87 / 2.1 ≈ 53.7
```

which is a much stronger condition than "point estimate ≤ 112.87". If the upper limit exceeds 112.87,
N = 10 is not permitted. REV4 also says that a 3-seed pilot "generally cannot" establish the bound and
that N = 10 requires a larger pilot (≥ 5 seeds) or independent variance evidence.

### 3.3 Recommendation (advisory; NOT applied)

1. **Default to N = 16.** This is the primary design and the only choice that needs no pilot
   certification. It must be recorded before the campaign and is then fixed.
2. **Permit N = 10 only** if all of the following hold and are recorded in the pilot report:
   - the pilot includes B, C, F and Fβ (so all four paired sds are estimable);
   - the pilot reports `σ_max`, its point estimate, its 80% upper confidence limit and the method used;
   - the upper confidence limit is ≤ 112.87;
   - the report states that the bound was computed **before** any campaign outcome was seen.
3. **Do not select N = 10 from a 3-seed pilot on the point estimate alone.** If the 3-seed upper limit
   is above 112.87, the only admissible outcomes are N = 16 or no campaign. If N = 10 is genuinely
   wanted, enlarge pilot 2 to at least 5 seeds (a design change requiring approval) or supply
   independent variance evidence.
4. **Never revisit N after campaign outcomes.** REV4 §7.1 forbids selecting N on the result.
5. **Record the actual N in the run manifest and in every episode row.** If the number of complete
   pairs later differs from the selected N, §7.3 rule 3 recomputes every threshold at the actual N;
   the selected N is not silently reduced.

### 3.4 What changes when the value is recorded

When the user records a value, the following are required **at that time**, none of which is done now:

- `configs/phase_8/campaign.yaml`: set `design.n_seeds_selected` to 16 (recommended) or 10.
- `experiments/phase_8/campaign/protocol.py`: replace the null-only conformance check
  (`"campaign.n_seeds_selected"` expects `None`) with a check that the value is one of the declared
  design sizes and is consistent with the pilot record. The current check is deliberately built to
  fail once the design resolves, so this edit is mandatory rather than optional.
- `experiments/phase_8/config.py`: the loader already accepts a non-null value and enforces
  `selected ∈ {n_seeds_primary, n_seeds_fallback}`; no change expected, but the test suite must be
  re-run.
- Tests that assert `design_resolved is False` for the shipped configuration must be updated to assert
  the recorded value. They currently document the null state; they must not be edited to make a real
  design pass without the user's record.
- The run manifest and episode schema already carry `n_seeds`; no schema change is expected.

The recommendation is **not applied** in this readiness pass. `n_seeds_selected` remains `null`.

---

## 4. Undeclared training inputs (B3–B6) and declared budgets

REV4 fixes the training budgets but does not declare four operational inputs. The code deliberately
requires them as caller inputs rather than inventing them. Each is a decision the user must record
before training artifacts exist.

### 4.1 B3 — campaign↔training seed pairing

*What REV4 declares:* training and evaluation seeds are disjoint; F and Fβ share a training seed for
the same campaign seed (REV4 §3.6.2); `seeds.training` contains 20 indices, `seeds.campaign` 16.

*What it does not declare:* which training seed serves which `(condition, campaign_seed)` pair.

*Unresolved issue:* the mapping. No default exists, and a partial map is an error.

*Options:*
- (a) one-to-one: campaign seed *i* → training seed 1000+*i* for every trainable condition
  (F/Fβ share; E and E_full may share or not);
- (b) a declared permutation (e.g. a fixed offset) so training seeds are not index-aligned with
  campaign seeds;
- (c) independent draws within `seeds.training`, with the realised map recorded.

*Technical consequences:* `training/seeding.py::validate_pairing` requires
`{(condition, campaign_seed)}` to be covered exactly, every value to be in `seeds.training`, every
condition to use each training seed at most once, and F/Fβ to match. It does not require training
seeds to be unique across conditions, so (a) and (b) are both expressible. The pairing is written into
each artifact manifest, so it is auditable.

*Scientific consequences:* index alignment (a) is simple but couples the training and evaluation
indices; any accidental reuse would be visible because `artifact_seeds` rejects
`campaign_seed == training_seed`, but the pairing is still a design choice. A permutation (b) reduces
the chance that a reader mistakes training seed *i* for evaluation seed *i*. Cross-condition sharing
of a training seed ties the initialization streams of E and E_full and should be declared if used.

*Recommendation (advisory):* **one-to-one, but with training seeds not numerically equal to campaign
seeds (e.g. campaign seed *i* → `1000 + i`), F/Fβ sharing, recorded in a dedicated pairing artifact.**
The exact scheme is a user decision; the code will accept any complete map.

*Enforcement point:* `experiments/phase_8/training/seeding.py::validate_pairing` (lines 76–151);
`build_training_plan` calls it before any artifact path is touched.

*Approval required:* **yes.**

### 4.2 B4 — training-episode environment-seed schedule

*What REV4 declares:* F/Fβ train for 20 episodes per seed; E/E-full train for 2,000 gradient updates.
It does not declare which environment seeds those training episodes use.

*What it does not declare:* the training-episode environment-seed schedule.

*Unresolved issue:* whether training episodes reuse the evaluation environment seeds, use a separate
declared stream, or use a fixed literal seed.

*Options:*
- (a) a separate training-environment stream derived from the training seed and the episode index;
- (b) the same environment seeds as the evaluation episodes (strong leakage risk);
- (c) a constant seed for every training episode (no environment diversity).

*Technical consequences:* `training/engine.py::train_readout` and `train_agent` accept
`environment_seed_for_episode` as a callable or an integer and record every seed used in
`environment_seeds`. The engine refuses a callable that returns a non-integer. The checkpoint stores
`environment_seeds_used`. No derivation is imposed.

*Scientific consequences:* (b) would train and evaluate on the same environment instances, which is
not held-out evaluation and would inflate F/Fβ. (a) keeps training environments disjoint and
reproducible but requires a declared derivation. (c) removes environment variability and biases the
readout toward one layout.

*Recommendation (advisory):* **(a), with a declared derivation that cannot collide with the
evaluation environment stream (for example a distinct stream code for training episodes), recorded in
the training manifest.**

*Enforcement point:* `training/engine.py::_seed_from` and the `environment_seed_for_episode`
parameter (lines 330–334, 489–498, 681–686); `TrainingRun.environment_seeds` records the schedule.

*Approval required:* **yes.**

### 4.3 B5 — checkpoint cadence, retention and format

*What REV4 declares:* nothing about checkpoints. The engine needs a cadence only if the run is to be
resumable.

*Unresolved issue:* how often to checkpoint, how many to keep, and what format.

*Options for cadence:* (a) every episode (20 checkpoints for F/Fβ; up to the episode bound for E);
(b) every *n* episodes; (c) only at the end.
*Options for retention:* keep all, keep the last, keep a declared subset.
*Options for format:* the existing NPZ + JSON-manifest scheme, or a new format.

*Technical consequences:* `training/checkpoint.py::_check_checkpoint_policy` requires cadence and root
to be either both supplied or both absent; `write_checkpoint` refuses overwrite; the payload is a
manifest of state digest, trainable digest, config hash, progress and environment seeds, with the
parameters in an NPZ. The format is already versioned and validated; changing it is a schema change.
Every checkpoint records `rng_restored=false` and `optimizer_state_restored=false` (see B6).

*Scientific consequences:* checkpoints are operational, not scientific, but retention affects
reproducibility and disk footprint. Keeping all checkpoints allows a replay from any episode; keeping
only the last makes a mid-run failure unrecoverable without rerunning. The cadence must not be
confused with a stopping rule: the declared stopping condition is the fixed budget.

*Recommendation (advisory):* **checkpoint at every episode, retain all for the declared training
seeds, keep the existing NPZ+manifest format.** This is the most conservative choice and adds no new
format surface. The decision remains the user's.

*Enforcement point:* `training/checkpoint.py` (lines 8–9, 527–531); `training/engine.py`
`checkpoint_every` / `checkpoint_root`.

*Approval required:* **yes.**

### 4.4 B6 — RNG and optimizer-state restoration

*What REV4 declares:* nothing. The engine's resume is parameter-continuous, not bit-identical.

*Unresolved issue:* whether a resumed training run must reproduce the uninterrupted run bit for bit.

*Options:*
- (a) parameter-continuous resume (current behaviour): parameters and progress are restored; torch's
  RNG state and the Adam moment estimates are **not**; the run is reproducible only up to the
  checkpoint, not across the resume boundary;
- (b) bit-identical resume: persist torch RNG state and optimizer state (Adam exp_avg, exp_avg_sq,
  step), and assert equality against a non-interrupted reference.

*Technical consequences:* (a) is implemented and honestly labelled in every checkpoint
(`rng_restored: false`, `optimizer_state_restored: false`) and in the engine's returned
`resume_info`. (b) requires extending the checkpoint payload and the state-digest schema, plus new
tests; it is a code change, not a config change.

*Scientific consequences:* with (a), a run that is resumed after a failure is not the same run as an
uninterrupted one; the artifact is still a valid trained artifact but its provenance must state the
resume. With (b), the campaign can treat a resumed run as equivalent, at the cost of a larger
checkpoint and stricter tests. Neither option changes the evaluation design.

*Recommendation (advisory):* **(b) for the campaign** if any training run may be interrupted; **(a) is
acceptable only if resumes are recorded and no run is silently restarted.** The choice must be made
before training, because it affects what a completed artifact claims.

*Enforcement point:* `training/checkpoint.py::build_checkpoint_payload` and `validate_checkpoint`;
`training/engine.py::resume_info`; `training/artifacts.py::read_artifact` re-verifies state and
trainable digests.

*Approval required:* **yes.**

### 4.5 Declared budgets and stopping conditions (review)

These are declared in REV4 Appendix C and implemented as constants, so they are **not** unresolved;
they are restated here because the brief asks that they be reviewed.

| Stage | Declared budget | Stopping rule | Early stopping | Implementation |
|---|---|---|---|---|
| F (linear readout) | 20 training episodes per seed | fixed episode budget | none | `training/config.py::READOUT_EPISODES_PER_SEED = 20`; `engine.train_readout` |
| Fβ (bias-only readout) | 20 training episodes per seed, same as F | fixed episode budget | none | same constant; `controls/f_beta.py` |
| F-init | none — seeded initialization only | n/a | n/a | `controls/f_init.py`; no training stage |
| E-matched | 2,000 gradient updates | update budget | none; a loop-safety episode bound refuses rather than truncates | `training/config.py::E_GRADIENT_UPDATES = 2000`; `engine.train_agent` |
| E-full | 2,000 gradient updates, same as E | update budget | none | same constant and path |
| Evaluation episode | game cap 900 updates | game termination or cap | none | `campaign.yaml::max_game_updates: 900` |
| A/B/C/D/F/Fβ evaluation | K = 10 episodes per seed | fixed episode count | none | `campaign.yaml::episodes_per_seed` |

There is **no validation-based model selection, no early stopping, and no checkpoint chosen by
performance**. The declared stopping condition is always a fixed budget; `train_agent` explicitly
raises if the loop-safety episode bound is reached before the update budget, rather than silently
truncating. This is consistent with REV4 and requires no new decision.

One residual point is not a new decision but a consequence of U9: for B and D, plasticity runs during
evaluation, so the evaluation episode itself changes weights. The evaluation budget is still fixed
(900 updates / K = 10), and no training-style stopping rule applies.

---

## 5. Cross-cutting consequences of resolving the register

### 5.1 Documentation edits required after approval

- REV4 §12 status column: each approved item becomes `APPROVED — <date> — <record>`; unapproved items
  stay `PROPOSED`. REV4 is frozen and must not be edited in place; approval is recorded in a separate
  freeze/approval record with the protocol SHA-256, and the register points to it.
- If U14 = m = 3, REV4 §5.3, §5.4, §7, §10 and this register must all say exploratory for H3 and C4
  (U15 propagation).
- If U9 = (b) or (c), the frozen-evaluation held-out-seed requirement must be added to the execution
  plan.
- If U18 = (b), the current 16 certificates are invalid for the confirmatory null and would have to be
  regenerated under a new generator; §11.23 must be rewritten. This is not recommended.

### 5.2 Code edits required after approval

| Trigger | Edit | Why it cannot be done before approval |
|---|---|---|
| U7 resolved | `campaign/protocol.py` null-only conformance check; tests asserting the null design | The check is deliberately built to fail when the design resolves; editing it early would make a real design pass without a record |
| B3 recorded | a pairing artifact + loader call | No default pairing exists; inventing one would be the decision itself |
| B4 recorded | a declared training-environment seed derivation | The engine deliberately takes the schedule as a caller input |
| B5 recorded | cadence/retention values at the call site | No scientific default exists |
| B6 = (b) | checkpoint payload extension + tests | Changes the state schema; must not be slipped in as a fix |
| U14/U15 | analysis call-site family size and register wording | The analysis already accepts 4 or 3; the caller must declare which |
| U1-B branch | none in code; the viability report is read-only | The stop is procedural |

### 5.3 What is executable before approval

Nothing in the confirmatory path. The following are permitted because they are static or synthetic and
do not collect experimental data:

- reading code, configs, certificates and reports;
- running the synthetic test suites;
- running the read-only CLI `python -m experiments.phase_8.run_campaign check`, which reports
  conformance, memory and certificate status and exits non-zero without executing.

Everything else — training, game episodes, pilots, campaign, analysis of campaign data — remains
blocked by `assert_training_authorized`, `assert_design_resolved`, the campaign gate, or the memory
gate.

---

## 6. Approval record (blank)

No signature is implied by this document. To record a decision, the user supplies, per item:

| Field | Value |
|---|---|
| Item | e.g. U7 |
| Decision | e.g. N = 16 |
| Date | |
| Protocol SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Record location | |
| Notes | |

Until such a record exists, the register status is unchanged: **PROPOSED — not approved**.

---

## 7. What this register does not do

1. It does not approve, reject or amend any U-item.
2. It does not set `n_seeds_selected`; the recommendation in §3 is advisory and explicitly not
   applied.
3. It does not declare a campaign↔training pairing, a training environment-seed schedule, a checkpoint
   cadence or a resume policy; §4 records the options and the code's refusal to invent them.
4. It does not run, authorise or schedule any training, episode, pilot or campaign.
5. It does not modify REV4, any certificate, any graph, any frozen input, or any scientific parameter.
6. It does not claim that any implementation mechanism is scientifically validated. Synthetic tests
   establish that the machinery behaves as specified; they say nothing about biological performance.
