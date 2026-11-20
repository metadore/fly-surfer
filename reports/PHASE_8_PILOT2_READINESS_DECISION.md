# Phase 8 — Pilot 2 Scientific Applicability and Operational Readiness Decision

**Date:** 2026-11-20
**Scope:** REV4 §10.8 Pilot 2 (3 pilot seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes)
**Mode:** read-only assessment. No source, configuration, protocol, dataset or result was
modified. No parameter was tuned, no graph regenerated, no training run and no Pilot 2
episode executed, and no Git operation was performed.
**Deliverable:** this file only.

---

## 0. Decision

> **Pilot 2 is NOT READY.**

Three independent classes of finding support this:

1. **No execution path exists on the present state.** The stage gate refuses
   (`B7`, the G3 §9.3 deviation, is open for every stage except the exact Pilot 1
   grid), two declared input classes do not exist (`P2-G`, `P2-A`), there is no
   training-artifact root at all, and there is no Pilot 2 episode runner: the CLI
   `--run` path passes `episode_runner=None`.
2. **The stage cannot meet its own stated objective on the present substrate.** REV4
   §10.8 measures the paired dispersion of C1–C4 so that the predeclared U7 N rule can
   be applied. Pilot 1 and Phase 4H.4/Phase 7 show the motor layer is silent and the
   action is constant `NO_ACTION`. On that substrate C1, C3 and C4 are algebraically
   degenerate (two of them exactly zero, the third an artefact of bias-only policies),
   C2 is a real but almost certainly null test, and a measured `σ_max = 0` would
   *appear* to justify the N = 10 fallback while carrying no information about the
   campaign's contrast dispersion.
3. **Every route out of (1) is a formal change.** The owner decision package records
   that each resolution of `P2-G`/`P2-A` requires a formal amendment; `P2-G` and
   `P2-A` cannot be resolved by regeneration either, because graph regeneration is
   blocked by B7 and training is blocked by B2–B7.

The confirmatory hypotheses (H1–H6) and the contrast definitions (C1–C4) are **not**
invalidated by running Pilot 2, and this report proposes no change to either. The
problem is that Pilot 2 as written cannot supply the number it exists to supply.

The shortest scientifically defensible path is given in §5.3. It begins with a
recorded owner decision on the motor-null scope (the U1-B condition), not with code.

---

## 1. Evidence base and method

Read in full or in the cited parts:

| Source | Use |
|---|---|
| `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` (SHA-256 `e4aa9e0f…1547c`) | §3.6.2–3.6.5, §3.7, §4, §5.1–5.3, §6.9, §7.4–7.8, §10.3, §10.5–10.8, §12 U1/U7/U10 |
| `configs/phase_8/campaign.yaml` | design constants, seed sets, memory gate |
| `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl` | nine stored Pilot 1 rows |
| `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` | totals line, protected-baseline drift, zero motor output |
| `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` | first-hop mechanism, structural query, decoder, eligibility, arm analysis |
| `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | first-hop current/membrane, motor first-hop = 0, repeat pairs |
| `reports/PHASE_4G5_MOTOR_DECODER_INTEGRATION.md` | decoder positive control |
| `experiments/results/phase_7/neural_closed_loop.json` | 2,852 spikes, 0 motor, 0 non-stimulated |
| `experiments/phase_8/stages/pilot2.py` | plan, readiness, dispersion evaluator, CLI, gated runner |
| `experiments/phase_8/stages/common.py` | stage gate, memory gate, `drive_pilot` |
| `experiments/phase_8/campaign/protocol.py` | `stage_authorization`, Pilot 1-only exemption |
| `experiments/phase_8/campaign/graphs.py`, `experiments/phase_8_random/campaign_summary.py` | certified seed set, refusal path |
| `experiments/phase_8/training/{loader,artifacts,gate,seeding,checkpoint,config,validation}.py` | P2-A loader contract, artifact requirements, seed pairing, checkpoint status |
| `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` Part E | amendment options and independence trade-offs |

I also ran the stage's own **read-only** `describe` path
(`experiments.phase_8.stages.pilot2.main(["--describe"])`). It executes no episode,
writes no file, and is the authoritative statement of current readiness. Its output is
quoted in §3.

Evidence grades used below:

- **[M]** measured and stored;
- **[A]** analytically certain from the declared model, not separately measured;
- **[I]** inference from converging measured facts;
- **[U]** unknown / not measured.

---

## 2. Scientific applicability

### 2.1 What Pilot 2 is for, in REV4's own terms

REV4 §10.8 (line 1415) defines the stage as:

> "3 seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes … computes paired sd for C1–C4 and
> reports `σ_max` with its upper confidence limit; **A′ ≡ A and C′ ≡ C on all 3 seeds**;
> **B is included** so `σ_C2` is estimated; applies the **predeclared** N decision
> (N = 16 primary; N = 10 only if `σ_max ≤ 112.87` is defensible); does **not** test
> hypotheses or estimate campaign effects."

REV4 §10 (line 1435) adds:

> "Neither pilot is a hypothesis test, neither may be reported as evidence for or
> against H1–H6, and neither may be merged into the campaign dataset."

The implementation matches this exactly. `pilot2_plan` declares
`estimates_contrasts=False`; `evaluate_dispersion` returns `hypothesis_tests: []`,
`campaign_effects_estimated: False`, `merged_into_campaign: False` and rejects any row
whose seed is not a declared pilot seed (`stages/pilot2.py:286–330, 599–674`).

So Pilot 2 has exactly three deliverables: (i) `σ_max` and its 80 % upper limit for
C1–C4, (ii) A′≡A and C′≡C identity on all three seeds, (iii) certification that Fβ is a
functioning constant-action control. Nothing else.

### 2.2 The substrate Pilot 2 would run on

Measured facts, unchanged from the Pilot 1 investigation:

- **[M]** Nine Pilot 1 rows, 73,880 total spikes, 3,784 updates, **0 motor spikes**,
  `NO_ACTION` on every decision, weights `4923f0cd…45d5` unchanged
  (`pilot1/episodes.jsonl`).
- **[M]** The first-hop current→spike conversion fails: 473 of 607 non-stimulated
  first-hop receivers carry current, peak **164.443 pA**, peak membrane
  **−56.926064 mV** against a −50 mV threshold — **6.926 mV short**, **0 threshold
  crossings** (`PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json`).
- **[M]** Because no first-hop neuron spikes, no second-hop neuron receives current
  (0 of 3,576), and **0 of 805 motor neurons receive current**.
- **[M]** No motor neuron is a first-hop target of the 232-neuron sensory set
  (0/608); the route requires at least two hops to reach any motor pool.
- **[M]** Phase 4G.5 condition C (direct 300 pA into 64 VNC-intrinsic neurons) gave
  1,296 spikes / 492 motor spikes / 82 motor neurons / JUMP×4 + NEUTRAL×1. The
  decoder and motor populations are functional; the failure is upstream drive.
- **[M]** Phase 7: 2,852 spikes, **all** stimulated sensory, `non_stimulated_spikes=0`,
  `motor_spikes=0`, 213/213 `NO_ACTION`, `decoded_action_supported=false`.
- **[A]** Eligibility (`plasticity/traces.py:326–345`) requires a postsynaptic spike.
  With zero first-hop spikes, **no eligibility forms on sensory→first-hop edges**, so
  plasticity has nothing to reinforce at the blocked hop.
- **[A]** The readout consumes motor features (`readout/features.py`, default
  `active_fraction`). With zero motor spikes the feature vector is **exactly 0** on
  every decision.

### 2.3 Arm-by-arm applicability

REV4 §3.7 (line 855 region) defines the arms: A = biological/fixed/fixed decoder;
B = biological/plastic/fixed decoder; C = randomised/fixed/fixed decoder;
F = biological/fixed/**trained readout**; Fβ = bias-only control; A′, C′ = η = 0
identity controls. E is **not** in the Pilot 2 grid.

| Arm | What it would measure | Status on the present substrate | Grade |
|---|---|---|---|
| **A** | viability reference; the measured floor side | Runs, but is a **constant-`NO_ACTION` policy**. Established by Pilot 1. No dispersion information: every episode is the same policy. | [M] |
| **B** | whether three-factor plasticity changes survival | **The only arm whose behaviour could in principle change**, because plasticity can still form eligibility at first-hop receivers that *do* spike (473/607) and could potentiate ascending edges over 900 updates. But it can only change behaviour by eventually recruiting a motor population, which requires crossing the 6.926 mV deficit; unmeasured. If B stays motor-silent, it is also constant `NO_ACTION` and C2 is **exactly 0** per seed. | [A] conditional |
| **C** | random-connectivity control | Target exchange preserves per-neuron in-degree and sign but **changes which sources** feed each neuron, so a motor neuron *could* gain input from an active first-hop cell. If it does not, C is also constant `NO_ACTION` and C3 is exactly 0. **Cannot run at all**: no certified graph exists for pilot seeds (§3.1). | [U] |
| **F** | trained readout on motor features | Trains, but with `x ≡ 0` the logits are the biases. The REINFORCE gradient w.r.t. feature weights is `(onehot − p)·xᵀ = 0`, so the **feature weights never move**; only biases train. Behaviourally F is a **constant-action policy**, exactly the class Fβ is built to represent. | [A] |
| **Fβ** | best constant policy | Already state-independent by construction (feature weights fixed 0, only biases trainable). It is therefore the *correct* control — but in a silent-substrate run it is indistinguishable in kind from F, not merely in score. | [A] |
| **A′** | η = 0 through the live plastic path must equal A | Still meaningful: an exact structural/stepper identity check, independent of behaviour. Cheap and unaffected by motor silence. | [M]-capable |
| **C′** | random graph + η = 0 must equal C | Same identity value, but **requires a pilot random graph**, which does not exist (§3.1). | blocked |

Two terminology points matter and are easy to get wrong:

- **F is not "bias-only".** REV4 §3.6.2 (lines 461–468) restricts the phrase to an arm
  with **exactly** Fβ's parameter set. F keeps trainable feature weights; they simply
  receive zero gradient. The correct statement is *"F is behaviourally equivalent to a
  constant policy"*, not *"F is bias-only"*. Using the Fβ term for F is forbidden by
  the naming rule and would produce a mislabelled record.
- **The `NO_ACTION` floor is substrate-free and must be measured by replay**
  (§3.6.2, §12 U10). Pilot 2 does **not** include a floor arm. On this substrate the
  floor and arms A–C coincide, so the floor comparison is available for free from the
  same environment seeds — but it is not part of the Pilot 2 grid and must not be
  reported as if it were.

### 2.4 Contrast-by-contrast applicability

| Contrast | Definition | On the present substrate | Verdict |
|---|---|---|---|
| **C1** = F − A | contribution of a trainable readout (H3) | F can still learn a **non-`NO_ACTION` constant** action if any action beats `NO_ACTION` on reward (the bias gradient is nonzero). So C1 can be **nonzero and even "significant"** while carrying no motor information. REV4 §3.6.3 labels such decisions **bias-driven**; §3.6.4 E3 fails, so no decoding claim is permitted. | **Degenerate as evidence for H3**, possibly numerically nonzero |
| **C2** = B − A | contribution of synaptic plasticity (H1) | Real in principle. Exact zero if B remains motor-silent (same actions ⇒ same game trajectory on the paired env seed). Plasticity at the 473 spiking first-hop receivers is possible, so a small real effect cannot be excluded analytically. | **Genuine but expected null**; unmeasured for B |
| **C3** = A − C | biological vs degree+sign-matched random (H2) | If C is motor-silent, both arms are constant `NO_ACTION` and the paired difference is **exactly 0** on every seed, because the environment sees identical actions on identical seeds. If target exchange accidentally routes an active first-hop cell into a motor neuron, C3 becomes a real incidental difference. | **Exactly zero or incidental**; cannot run today |
| **C4** = F − Fβ | does the readout use motor information (over the best constant policy) | With `x ≡ 0`, both arms emit bias-only logits. Any difference is **initialisation, bias-training and optimizer noise between two constant policies**, not state-dependence — let alone motor-state dependence. | **Degenerate by construction** |

Consequences for the U7 number:

- **[A]** If all arms stay motor-silent, `σ_C1 = σ_C2 = σ_C3 = 0` exactly (three
  identical paired differences of 0), and `σ_C4` is the sd of noise between two
  constant policies. `σ_max` is then either 0 or that noise.
- **[A]** `evaluate_dispersion` would report `sigma_max ≈ 0`, `ucl80 ≈ 0`, and
  `_u7_indication` would return **`fallback_N_may_be_defensible`** because
  `0 ≤ 112.87` (`stages/pilot2.py:548–596`). That indication would be **an artefact of
  a floored design**, not evidence that N = 10 is adequate. REV4 §7.4 intends `σ_max`
  to be the dispersion of contrasts that exist; a zero from four degenerate contrasts
  estimates nothing about the campaign.
- **[A]** Even if C1 or C4 is nonzero, the dispersion measured is that of **constant
  policies on a floored platform**. The campaign's contrasts will include plasticity
  (B, D), a random substrate (C, D, C′), trained readouts and E. Pilot 2's pilot-arm
  dispersion is not a proxy for those, and REV4 forbids using pilot rows as campaign
  rows.

Therefore the **original objective — "measure the paired dispersion that governs N" —
cannot be met** on the present substrate, and if it is run and reported naively it
would produce a **misleading `σ_max ≈ 0`** favourable to the smallest design.

### 2.5 What remains meaningful

Not everything degenerates. The following retain value and are unaffected by motor
silence:

| Deliverable | Meaning | Condition |
|---|---|---|
| A′ ≡ A exact identity (P1–P19) | certifies the η = 0 path through the real stepper | none beyond a runner |
| C′ ≡ C exact identity | certifies the random-substrate path | requires pilot random graphs |
| Weight invariance in A/F/Fβ/A′ | structural invariant, already measured in Pilot 1 for A | reproducible today |
| Floor measurement on pilot environment seeds | the substrate-free `NO_ACTION` floor, required for §7.8 and U1 | free; already implied by A |
| Motor-silence *measurement* | REV4 §6.9 treats zero motor activity as a measurement, not a failure to hide | reproducible today |
| Fβ constant-action certification | that the control took one action everywhere | trivially true; weak evidence beyond construction |

What is lost is precisely the part Pilot 2 exists for: a **positive, informative**
estimate of `σ_max` across contrasts that can actually differ.

### 2.6 The evidence bar it would satisfy

REV4 §3.6.4:

| Evidence | Status under the measured substrate |
|---|---|
| E1 `F − Fβ > 0`, C4 survives Holm | may pass numerically on bias noise — and would be **uninterpretable** |
| E2 `F − A > 0`, C1 survives Holm | may pass numerically as a bias-driven constant policy |
| E3 ≥ 1 LEFT/RIGHT/JUMP spike on ≥ 1 % of decisions in ≥ half of seeds | **fails** (0 motor spikes in every measured run) |
| E4 ≥ 10 % of non-`NO_ACTION` decisions motor-driven | **undefined (0/0)**, to be recorded as not evaluable, never as pass |
| E5 fresh-process reproduction of the motor-driven count | vacuous |

The only permitted statement is REV4's own (lines 533–535):

> "the motor populations were silent; the readout could at most learn a constant
> policy."

Pilot 2 cannot move this. It is a property of the substrate, not of the pilot.

---

## 3. Protocol implications

### 3.1 Is proceeding already permitted under REV4?

**No.** Three separate refusals apply, in order of encounter.

**(a) Authorization.** `drive_pilot` calls
`assert_stage_authorized(plan.stage, config=config, plan=plan)`
(`stages/common.py:411`). For `stage="pilot2"` that produces, verbatim from
`campaign/protocol.py:597–604`:

> "B7: stage 'pilot2' does not inherit the D2 Pilot 1 exemption; the G3 randomization
> set has a recorded §9.3 deviation (status 'deviation_recorded', gate weakened:
> False) and remains blocking"

The D2 exemption is scoped field-for-field to Pilot 1: `stage == "pilot1"`, arms
`("A",)`, seeds `[9001, 9002, 9003]`, 3 episodes each, **no randomized graph, no
trained artifact** (`protocol.py:560–640`). Pilot 2 uses a randomized graph (C, C′)
and trained artifacts (F, Fβ), so it is excluded by construction, not by accident.

**(b) Design gate.** `campaign.yaml:25` has `design.n_seeds_selected: null`. The
campaign-wide `describe` path therefore also lists `B2`
(`stages/common.py:207–213`). Note the asymmetry, which is real and should not be
smoothed over: `describe_pilot2` uses the **campaign-wide** snapshot (B2 + B7), while
the **execution** path only calls `assert_stage_authorized` (B7). B2 is checked at
training and campaign preparation, not at Pilot 2 execution.

**(c) Missing inputs.** `pilot2_readiness` declares `P2-G` and `P2-A`; and, not
declared anywhere, the CLI `--run` passes `episode_runner=None`
(`stages/pilot2.py:821–826`), so even with B7 resolved `drive_pilot` would raise
`StageConfigurationError("drive_pilot requires an episode_runner")`
(`stages/common.py:414–415`).

Exact current `describe` output (abridged to the decision fields):

```
executable: false
execution_blockers:
  - B7: the G3 certified graphs carry a recorded §9.3 memory-gate deviation
        (status 'deviation_recorded')
  - B2: design.n_seeds_selected is null until the 10.8 pilot decision (U7)
  - P2-G: no certified random graph exists for pilot seed(s) [9001, 9002, 9003];
          certification covers the campaign seeds [1..16] only, so C and C'
          cannot run on the pilot grid and a campaign graph may not be substituted
  - P2-A: the training-artifact loader accepts only seeds declared in seeds.campaign,
          and no pilot seed is declared there; trained F, F-beta and E artifacts for
          the pilot seeds therefore cannot be loaded. Resolving this is an owner
          decision (a declared pilot training set or an approved change of the loader
          contract), never a silent substitution
  - P2-A: no trained artifact directory exists for pilot seed(s) [9001, 9002, 9003]
          under experiments/results/phase_8/training
readiness.ready: false
memory_preflight: passed, available 5.823 GB of 4.0 GB gate
plan: 63 entries (7 arms × 3 seeds × 3 episodes)
```

### 3.2 Does proceeding require an explicit owner decision?

**Yes, several, and they are distinct:**

| Decision | Why it is the owner's | What it unlocks |
|---|---|---|
| **G3/B7 applicability** | the deviation is recorded against a completed, certified graph set; only the owner can accept it, order a compliant rerun, or declare it inapplicable to a defined pilot scope | any stage beyond Pilot 1 |
| **P2-G resolution** | choosing among "certify pilot graphs", "declare a pilot↔certified-seed mapping", or "remove C/C′ from the pilot" changes what the pilot certifies | C and C′ can run |
| **P2-A resolution** | choosing a pilot training-seed set, or changing the loader contract, changes the seed-independence declaration | F and Fβ can be loaded |
| **U1-B scope** | a floored A (and predictably floored F) is §12's platform-floor case; the protocol stops for a scope decision rather than letting a campaign proceed | whether any neural condition may be interpreted |
| **U7/N** | explicitly a human decision; the evaluator never writes `n_seeds_selected` | campaign N |

The owner decision package Part E records that **all three** P2-G/P2-A resolutions
require a formal amendment, and that the smallest implementation change (Option 2b/3:
run the pilot on certified campaign seeds) **sacrifices pilot–campaign independence**
and must be declared, not assumed.

### 3.3 Does proceeding require a formal protocol amendment?

**Yes for the operational path; no for the science of §10.8 as written.**

- **Needs amendment:** graph certification scope (`P2-G`), pilot training-seed set and
  loader contract (`P2-A`), and any relaxation of B7 for a pilot other than 10.3.
- **Does not need amendment:** the Pilot 2 design itself — arms, seeds, episodes,
  contrasts, UCL, U7 rule. None of those numbers is the problem.
- **Cannot be fixed by amendment alone:** "Pilot 2 measures σ for N" cannot be made
  true by changing a document. Either the substrate changes (Phase 9 scope) or the
  stage's stated objective must be re-scoped to floor/identity certification.

A useful distinction for the amendment text: an amendment may **redefine what the
stage certifies**; it may not **relabel a floored measurement as a dispersion
estimate**. REV4 §7.8 already forbids the latter ("no power against a difference
between two floored conditions", "absence of an effect under a floor is not evidence
of absence").

### 3.4 Would proceeding invalidate or change any confirmatory hypothesis?

**No confirmatory definition changes, and Pilot 2 itself cannot invalidate H1–H6** —
it tests none of them (§10, line 1435). But four constraints on interpretation follow
directly from the measured substrate and should be recorded before any run:

| Hypothesis | Constraint |
|---|---|
| **H1** (B − A; expected to fail, §4) | unchanged; if B stays motor-silent, C2 is exactly 0 and the expected failure is confirmed trivially |
| **H2** (A − C) | C3 measures two constant policies unless C accidentally drives a motor pool; a null is not evidence about connectivity |
| **H3** (F − A, confirmatory) | REV4 §4 states H3 "cannot exceed a constant policy if motor populations are silent"; C1 may still be positive as a bias-driven constant |
| **H4** (E vs floor) | unaffected by Pilot 2; E is not in the grid |
| **H5, H6** (exploratory/descriptive) | unaffected |
| **U1** | If F is also floored, the case is **U1-B** ("platform floor: run the predeclared floor decomposition and stop for a scope decision; do not claim an effect for any neural condition"). U1 is a stop rule, not a hypothesis |
| **§7.8** | if ≥ 4 of 6 conditions are at floor, the design has **no power against differences among floored conditions** and no "plasticity does not work" claim may be made |

So the risk is not corrupted hypotheses; it is a **stage that appears to succeed while
producing a number (`σ_max ≈ 0`) that would shrink the campaign on no evidence**.

### 3.5 Ordering

REV4 §10.8 depends on 10.4 (C + randomisation), 10.5 (F/Fβ), 10.6 (A′/C′), 10.7
(B/D) and 10.3. Today:

- 10.4's certified set carries a recorded §9.3 deviation and covers seeds 1–16 only;
- 10.5's training gate refuses unconditionally (`training/gate.py:111–116`);
- 10.6's C′ needs 10.4; A′ is implementable;
- 10.7's D needs 10.4 and B needs 10.6.

Pilot 2 therefore also fails on **dependency order**, not only on its own gates.

---

## 4. Operational readiness and exact resolution steps

### 4.1 P2-G — certified pilot graphs

**Facts.**

- `REQUIRED_SEEDS = tuple(range(1, 17))`
  (`experiments/phase_8_random/campaign_summary.py:35`).
- `CertifiedGraphSource._check_seed` raises for any seed outside that tuple:
  *"no certified graph exists for campaign seed {value}; the certified set is [1…16]"*
  (`campaign/graphs.py:72–82`).
- Pilot 2 seeds are 9001–9003 (`campaign.yaml:64`); coverage is `false` for all three.
- This assessment cannot change that: the certified set is an artifact of a completed
  BANC-scale randomisation run, and regeneration is blocked by B7 and by the read-only
  constraint on this task.

**Exact resolution options** (each requires a recorded owner decision; none may be
done by substitution):

| Option | Exact steps | Cost / loss |
|---|---|---|
| **G-1: certify pilot graphs** | (1) owner resolves B7 for graph construction *and* for pilot data collection, or orders a compliant ≥ 4 GB rerun; (2) run the target-exchange construction for structure seeds derived from 9001–9003; (3) run R1–R18 and write per-seed certificates; (4) extend `REQUIRED_SEEDS` (a code change) or pass `required_seeds` explicitly at the pilot call site | restores full design; new BANC-scale work; requires B7 resolution **before** it can be authorised |
| **G-2: declared pilot↔certified mapping** | (1) formal amendment declaring, e.g., pilot seed 9001 uses certified seed 1; (2) record the mapping in a new config key consulted by the pilot runner; (3) declare in the report that pilot and campaign share graph seeds; (4) `CertifiedGraphSource` must still validate the certificate | smallest implementation change; **loses pilot–campaign independence**; C/C′ at pilot are the same graphs as at campaign |
| **G-3: drop C and C′** | (1) formal amendment removing two arms; (2) re-declare what the stage establishes; (3) accept that C3/C4-with-C′ certification and the C′≡C identity are unavailable | cheapest; **changes the stage**, contradicts §10.8, and removes the identity certification the campaign requires |

Recommendation on evidence: **G-1** is the only option that preserves the protocol's
intent. **G-2** is defensible only if the loss of independence is stated in the same
sentence as every pilot-derived claim.

### 4.2 P2-A — loader contract

**Facts.**

- `load_training_artifacts` rejects any seed not in `config.campaign_seeds`:
  *"campaign seeds {…} are not declared in seeds.campaign"* (`training/loader.py:104–108`).
- `seeds.campaign = [1..16]` (`campaign.yaml:57`); pilot seeds are 9001–9003 and are
  **not** declared there.
- The loader discovers artifacts **only** by directory
  `<root>/<condition_id>/seed_<campaign_seed>/manifest.json`
  (`training/loader.py:64–72`), and never substitutes a condition for another.
- `DEFAULT_REQUIRED = ("F", "F_beta", "E")` (`loader.py:50`). Note: **E is not a
  Pilot 2 arm**; a pilot-scoped load can legitimately pass
  `conditions=("F", "F_beta")`. The readiness message's mention of E is the default,
  not a Pilot 2 requirement. This distinction matters for the amendment text.

**Exact resolution options:**

| Option | Exact steps | Consequence |
|---|---|---|
| **A-1: declare a pilot training-seed set** | (1) owner decision adding e.g. `seeds.pilot_training` disjoint from `campaign`, `training`, `pilot`; (2) extend the training config validator and `TrainingConfig.campaign_seeds` handling; (3) declare a pairing `(condition, pilot_seed) → pilot_training_seed`; (4) produce trained artifacts under that set; (5) pass the pilot seed set to `load_training_artifacts` | new formal declarations; preserves independence; most work |
| **A-2: approve a loader-contract change** | (1) amendment permitting an explicit `declared_pilot_seeds` argument; (2) enforce the same integrity checks; (3) reject any overlap with campaign seeds | code change to a **frozen contract**; must not create a silent substitution path |
| **A-3: add pilot seeds to `seeds.campaign`** | one-line config change | **not acceptable**: it makes pilot rows campaign-declared and invites exactly the merge §10 forbids. Listed only to be rejected explicitly |

### 4.3 P2-A — trained artifact requirements

**Facts.** There is **no training root at all**:
`experiments/results/phase_8/training` does not exist, so
`discover_artifact_directories(...)` returns `[]` and `pilot_seed_keys` is empty.

An artifact is accepted only if (`training/artifacts.py`, `loader.py`,
`validation.py`):

| Requirement | Where enforced |
|---|---|
| directory `<root>/<condition_id>/seed_<campaign_seed>/` with `manifest.json` + `parameters.npz` | `artifacts.py:3–10, 96–97` |
| `condition_id ∈ {F, F_beta, E, E_full}` | `config.py:55–57` |
| `origin == "trained"` **and** `stage == "trained"` | `loader.py:139–145` |
| `training_seed ∈ seeds.training` | `loader.py:151–156` |
| file SHA-256, byte length, shapes, dtypes, full-state digest and trainable digest all re-verified | `artifacts.py:272–304` |
| F loads as `LinearReadout` and is **not** state-independent; Fβ loads as `BiasOnlyReadout` with `trainable == ["bias"]` and fixed feature weights exactly 0 | `validation.py:296–331` |
| F/Fβ pair shares `campaign_seed`, `training_seed`, `master_seed` | `validation.py:346–358` |
| F/Fβ width = `MotorFeatureSpec().n_features`; E = 7; E_full = 14 | `validation.py:49–54` |

**Writing a trained artifact is impossible today**, by design:

- `_check_origin_stage` routes `origin == "trained"` straight into
  `assert_training_authorized()`, which **always raises**
  (`artifacts.py:105–107`; `gate.py:111–116`).
- `stage == "trained"` is refused independently (`artifacts.py:108–111`).
- The refusal reason is explicit: U7 (B2), B3–B6 and B7 (G3) remain open
  (`gate.py:69–116`).

**Exact resolution steps (in dependency order):**

1. Record the B7/G3 resolution (see §4.1) — it blocks the training stage itself, not
   only graph construction.
2. Record U7 (`design.n_seeds_selected`) **or** a pilot-scoped design that does not
   require it. Note that Pilot 2 comes *before* the U7 decision in §10.8; the current
   gate makes U7 a prerequisite for any training run, which is an ordering wart that an
   amendment must address explicitly rather than silently flip.
3. Declare B3 (campaign→training pairing), B4 (training-episode environment-seed
   schedule), B5 (checkpoint cadence/retention/format), B6 (RNG and optimizer-state
   policy).
4. Implement or authorise the training orchestration for F/Fβ (and E if the default
   required set is used) and run it for the pilot seed set.
5. Write artifacts with `origin="trained"`, `stage="trained"` and full manifests;
   verify with `read_artifact` before any pilot episode.

### 4.4 Seed pairing and checkpoint requirements

**Seed pairing** (`training/seeding.py`):

- REV4 declares training and evaluation seeds disjoint but **does not declare which
  training seed pairs with which campaign seed**. `validate_pairing` therefore needs an
  explicit mapping and never invents one (`seeding.py:82–90`; B3).
- `artifact_seeds` derives `init_seed` from the **training** seed's learning stream, not
  from the evaluation seed, so an artifact never shares a stream with the episode that
  evaluates it (`seeding.py:38–73`).
- Constraints: campaign ≠ training seed per entry; no training-seed reuse across
  campaign seeds within a condition; **F and Fβ must share the same training seed** for
  a given campaign seed (`seeding.py:124–140`).
- For Pilot 2 there is no declared pilot training seed set at all, so **every pairing
  entry for 9001–9003 is currently undefined**.

**Checkpoints** (`training/checkpoint.py:1–25`):

- A checkpoint is **not** a training artifact; it is never loaded by the campaign
  loader and cannot be passed to `write_artifact`.
- REV4 declares **no cadence, retention or format** (B5), so these are caller inputs
  with no default.
- Sampler RNG state and optimizer state are **not** restored; B6 records that a
  resumed run is *parameter-continuous, not bit-identical*. Any claim of bit-exact
  resume would be false.
- Checkpoints with `origin="trained"` are refused through the same
  `assert_training_authorized` path.

**Exact steps:** record B5/B6 answers (cadence, retained checkpoints, format, and an
explicit statement that resume is not bit-identical); declare the pilot training-seed
pairing; assert disjointness in the runner **before** the first episode.

### 4.5 Authorization and memory gates

| Gate | Current state | Resolution |
|---|---|---|
| **B1** REV4 §12 approval | **passes**: D1 recorded 2026-11-20, bound to `e4aa9e0f…1547c`; `document_authorises_execution` is **false** | none for B1 |
| **B2** design (`n_seeds_selected`) | open (`null`) | U7 decision, or a pilot-scoped design by amendment |
| **B7** G3 §9.3 deviation | **open for pilot2** | owner applicability decision, or compliant rerun, or B7-scoped amendment |
| **B8** memory | **passes at describe time**: 5.823 GB available vs 4.0 GB gate | re-checked at run (`_gate_report`); must pass at that moment |
| **P2-R** episode runner | **missing**: no `pilot2_runner.py`; CLI passes `episode_runner=None` | implement a 7-arm runner using `conditions/execute.py` (`neural_episode`, `conventional_episode`, `floor_episode`) and the arm modules; wire it into `main --run` exactly as `pilot1.py:213` wires `Pilot1EpisodeRunner` |

`P2-R` is not in the readiness list, and it should be. It means that even a fully
authorised, fully provisioned Pilot 2 would **still not execute**.

### 4.6 Blocker summary

| ID | Blocker | Class | Blocks | Resolvable read-only? |
|---|---|---|---|---|
| B7 | G3 §9.3 deviation; no Pilot 1 exemption for pilot2 | authorization | everything after Pilot 1 | no — owner/compliant rerun |
| B2 | `n_seeds_selected` null | design/authorization | training, campaign preparation | no — U7 |
| P2-G | no certified graphs for 9001–9003 | missing input | C, C′ (hence C3 and C′≡C) | no — regeneration or amendment |
| P2-A(loader) | loader accepts `seeds.campaign` only | contract | F, Fβ | no — declared pilot set or contract change |
| P2-A(artifacts) | no training root, no trained artifacts | missing input | F, Fβ | no — authorized training |
| P2-R | no episode runner; `--run` passes `None` | implementation | all 7 arms | no — code |
| B3–B6 | pairing, env schedule, checkpoint policy | declaration | training, artifacts | no — declarations |
| B8 | memory | operational | BANC-scale work | environmental; passes now |

---

## 5. Spike-total correction

### 5.1 Recalculation

Recalculated directly from the nine stored rows
(`experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`), reading
`notes.game_loop.total_spikes`:

| seed | episode | updates | neural steps | total spikes | motor spikes |
|---|---|---|---|---|---|
| 9001 | 0 | 323 | 10,767 | 4,764 | 0 |
| 9001 | 1 | 620 | 20,667 | 14,348 | 0 |
| 9001 | 2 | 323 | 10,767 | 4,764 | 0 |
| 9002 | 0 | 620 | 20,667 | 14,911 | 0 |
| 9002 | 1 | 426 | 14,200 | 8,396 | 0 |
| 9002 | 2 | 620 | 20,667 | 13,139 | 0 |
| 9003 | 0 | 213 | 7,100 | 2,850 | 0 |
| 9003 | 1 | 426 | 14,200 | 7,856 | 0 |
| 9003 | 2 | 213 | 7,100 | 2,852 | 0 |
| **total** | | **3,784** | **126,135** | **73,880** | **0** |

### 5.2 Confirmation

> **The correct Pilot 1 aggregate is 73,880.**

Independent checks: 3,784 updates and 126,135 neural steps sum correctly from the
same rows; the nine per-row values sum to 73,880; the row-level
`weights_unchanged`, `neural_resets_during_episode = 0` and
`unmapped_or_invalid = 0` invariants hold in every row.

### 5.3 The 1,000-spike discrepancy

- `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` states **72,880** in its totals line
  (lines 194 and 236 of the current file).
- The per-episode table in that report's §6 is correct and sums to **73,880**.
- Difference: **1,000**, i.e. **1.35 %** of the true total.

Interpretation: this is a **totals-line arithmetic error in the narrative report only**.
No stored episode record, manifest or hash is affected. The error is the same class as
the one corrected in `PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` §3.

**This assessment did not alter the execution report or any episode row.** Correcting
the narrative is a separate, owner-authorised task; doing it here would violate the
read-only constraint.

### 5.4 Why it does not change any conclusion

Every scientific conclusion rests on `motor_spikes = 0` and `NO_ACTION` on all
decisions, neither of which depends on the total. The 1,000-spike difference is
1.35 % of a quantity used only as a headline scale.

---

## 6. Final recommendation

### 6.1 Classification

> **NOT READY.**

### 6.2 Evidence for the decision

**Operational (any one of these is sufficient):**

1. `assert_stage_authorized("pilot2")` raises B7; the D2 exemption is field-scoped to
   Pilot 1 and cannot be inherited.
2. `P2-G`: certified graphs exist for seeds 1–16 only; `_check_seed` raises for
   9001–9003.
3. `P2-A` (contract): the loader rejects seeds outside `seeds.campaign`.
4. `P2-A` (artifacts): no training root exists; trained writes always raise.
5. `P2-R`: no Pilot 2 episode runner; the CLI's `--run` passes `episode_runner=None`.
6. `B3–B6`: pairing, environment-seed schedule and checkpoint policy are undeclared.

**Scientific (independent of operations):**

7. On the measured substrate, A, C, F and Fβ are constant-`NO_ACTION` policies. C1 is
   at best a bias-driven constant; C3 is exactly 0 or incidental; C4 compares two
   constant policies; only C2 is a genuine (expected-null) test.
8. `σ_max` from such a pilot is 0 or bias noise. `_u7_indication` would then return
   `fallback_N_may_be_defensible` — a **misleading** support for N = 10 that REV4 §7.4
   and §7.8 do not sanction.
9. E3 fails and E4 is undefined, so Pilot 2 cannot support any readout claim even if
   C1/C4 are numerically positive.
10. The stage's declared objective (paired dispersion governing N) is therefore
    unattainable on the present substrate, and the likely outcome is a floored design
    with a spurious precision signal.

**What is *not* wrong:** the Pilot 2 design, its arms, its contrasts, its UCL and its
U7 rule; and no confirmatory hypothesis is invalidated.

### 6.3 Shortest scientifically defensible path to readiness

There are two honest paths. They differ in what "ready" means, and the owner must pick
one **before** any code is written.

#### Path 1 — restore meaning (recommended)

| # | Step | Type | Why it is first |
|---|---|---|---|
| 1 | Record the **U1-B / motor-null scope decision**: the measured platform is floored (A) and F is predictably floored, so Phase 8 cannot produce a neural competence claim on this substrate | owner decision, no code | everything below is wasted if this is unresolved |
| 2 | Decide whether the substrate fix belongs to Phase 9 (REV4 forbids drive/decoder changes inside Phase 8) or whether Phase 8 proceeds as a **floor finding** | owner decision | determines whether Pilot 2 is deferred or re-scoped |
| 3 | If deferred: produce the floor finding from existing records (§7.8 decomposition, U1-B) and stop. Pilot 2 is then unnecessary rather than blocked | analysis of existing rows | zero new execution |
| 4 | If the substrate is fixed later: run Pilot 2 **after** the fix, with the original design unchanged | new Phase 9+ work | restores the original σ objective |

This path is short because it requires **no new execution** and no amendment to the
Pilot 2 design. It is scientifically defensible because it does not attempt to estimate
contrast dispersion from four degenerate arms.

#### Path 2 — run Pilot 2 anyway, as floor/identity certification

Accept that Pilot 2 no longer estimates σ for N, and make that explicit. Required
changes, all formal:

| # | Change | Kind |
|---|---|---|
| 1 | B7/G3 resolution for pilot scope (or compliant rerun) | owner decision / amendment |
| 2 | P2-G resolution: G-1 (certify 9001–9003) or G-2 (declared mapping, independence loss stated) | amendment + possibly new BANC-scale work |
| 3 | P2-A: declare a pilot training-seed set and reader contract | amendment + config/code |
| 4 | B3–B6 declarations and an authorised F/Fβ (and optionally E) training run | declarations + training |
| 5 | Predeclare that **`σ_max` is not evaluable for U7** on a floored design, and that the U7 decision will not be taken from it | amendment text; **required** to avoid the `σ_max = 0` trap |
| 6 | Implement the 7-arm runner (`P2-R`) and wire it into `main --run` | code |
| 7 | Re-scope the stage's stated deliverable to: floor measurement, A′≡A and C′≡C identity, Fβ constant-action certification, motor-silence measurement | amendment |

Path 2 is **not** short: it is at least five formal changes plus a training run plus a
new runner, and it still does not deliver the number Pilot 2 exists for. It is
defensible **only** if the owner explicitly wants control certification and a floor
measurement on the pilot seeds, and records that N will not be chosen from it.

#### What must not be done

- Do not run the pilot on certified campaign seeds and describe the result as
  independent pilot evidence.
- Do not let `σ_max ≈ 0` select N = 10.
- Do not call F "bias-only".
- Do not report C1 > 0 as evidence for H3 while E3 fails.
- Do not treat a floored null (C2/C3) as evidence that plasticity or biological
  connectivity "does not work" (§7.8).
- Do not resolve any blocker by silent substitution of a seed, a graph or an untrained
  artifact.

---

## 7. Limitations of this assessment

- No Pilot 2 episode was run, so every statement about what the seven arms *would*
  produce is derived from the frozen model, the stored Pilot 1 rows, the 4H.4
  diagnostic and the Phase 7 record — not from a measured Pilot 2 run.
- B's 900-update weight evolution is **unmeasured**. The claim that C2 is exactly zero
  is conditional on B remaining motor-silent; the claim that it is a genuine test is
  conditional on plasticity being unable to recruit a motor pool. Both are stated as
  conditionals, not as results.
- C's behaviour is **unmeasured** and cannot be measured without a pilot random graph.
- The `σ_max = 0` outcome is an analytical prediction for the all-silent case. If any
  arm produced a motor spike, the arithmetic changes; the interpretive problem does not
  (a handful of incidental spikes cannot estimate campaign dispersion).
- The memory figure (5.823 GB) is a snapshot at describe time and is re-checked at run.
- This report changes no protocol text, no configuration and no record. It is the only
  file created by this assessment.

---

## 8. Owner summary

1. **Pilot 2 is NOT READY** — on authorization, missing inputs, missing artifacts,
   missing runner, and on its own scientific objective.
2. **Proceeding is not permitted today**; B7 applies to every stage except the exact
   Pilot 1 grid, and even that exemption explicitly excludes randomized graphs and
   trained artifacts.
3. **No hypothesis is invalidated**, but H3 cannot exceed a constant policy, H2's
   contrast is floored, and U1-B is the likely gate case.
4. **The 1,000-spike discrepancy is a totals-line error only**; the true Pilot 1
   aggregate is **73,880**, and no stored record was altered.
5. **Shortest defensible path:** record the U1-B scope decision first; then either
   report the floor finding and defer Pilot 2 (recommended, no new execution), or
   authorise a re-scoped Pilot 2 as floor/identity certification with `σ_max` declared
   not evaluable for U7, resolving B7, P2-G, P2-A, B3–B6 and P2-R through one declared
   amendment.
