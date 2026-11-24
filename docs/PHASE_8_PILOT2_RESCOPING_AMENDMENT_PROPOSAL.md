# Phase 8 — Pilot 2 Re-Scoping Amendment Proposal

## Floor and identity certification in place of paired-dispersion estimation

| Field | Value |
|---|---|
| Document status | **PROPOSAL ONLY — NOT AN AMENDMENT, NOT AN AUTHORISATION** |
| Date | 2026-11-20 |
| Target | REV4 §10.8 (Pilot 2 — variability and control certification) |
| Proposed stage name | `pilot2` — *floor and identity certification* (working label "Pilot 2-C") |
| Governed by | REV4 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`, SHA-256 `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`, 1,915 lines |
| Existing approvals | D1 `reports/phase_8_owner_approvals/D1.json` (`5c183c99…4d489`); D2 `reports/phase_8_owner_approvals/D2.json` (`b5b0c229…0c17327`) |
| Evidence basis | `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md`; `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`; `reports/PHASE_8_PILOT2_READINESS_DECISION.md`; `experiments/phase_8/stages/pilot2.py`; `experiments/phase_8/campaign/protocol.py` |
| Modifies | **Nothing.** No protocol, configuration, source file, parameter, approval record or result is changed by this document |
| Executes | **Nothing.** No training run, no episode, no Pilot 2 |

---

## 0. Status, reading rules and evidence grades

### 0.1 What this document is

This is a **proposal** to change the scope of the REV4 §10.8 pilot. Adopting it
would require (a) an owner decision recorded as a new approval record, and
(b) a protocol amendment or a new revision, neither of which this document
performs. Every statement below is therefore conditional: *"if the owner adopts
this proposal, then …"*. Until an owner record exists, the operative
specification remains REV4 §10.8 exactly as written, and Pilot 2 remains blocked.

REV4 is unchanged by this document. Its last line still reads: *"This document
authorises no execution."* D1 and D2 are unchanged. `configs/phase_8/*.yaml` is
unchanged, including `design.n_seeds_selected: null`. The four confirmatory
contrasts C1–C4 are unchanged and are quoted verbatim in §3.6 so that no reader
can read a re-scoping as a re-definition.

### 0.2 Evidence grades

Every factual statement carries one of four grades. They are used exactly as in
the two Pilot 1 reports so a reader can compare documents without re-learning
the convention.

| Grade | Meaning |
|---|---|
| **[M]** | **Measured** — recorded in a stored artifact from a real run |
| **[A]** | **Analytically certain** — follows from declared constants, frozen structure or code, without a new run |
| **[I]** | **Inference** — reasoned from [M] and [A] but not itself measured; may be wrong |
| **[U]** | **Unknown / unmeasured** — not recorded, and not derivable |

A statement with no grade is a definition or a proposal, not a claim about the
world.

### 0.3 Reading rules

1. **No number in this document is a new measurement.** Every [M] figure is
   quoted from an existing report and is cited to its section.
2. **Certification is not inference.** A certification result may *gate* an
   interpretation; it may never *support* a hypothesis. §2.6 makes this rule
   operational.
3. **Absence of an effect under a floor is not evidence of absence.** REV4 §7.8
   already states this for the campaign; it applies with full force here.
4. Where this document proposes something REV4 does not contain, it says so in
   §8 and again in §9, and it names the owner decision in §10.

---

## 1. Why a re-scope is necessary

The re-scope is not a preference. Four facts, taken together, make the REV4
§10.8 acceptance criteria unreachable as written.

### 1.1 Fact 1 — condition A does not produce motor output

Pilot 1 executed the authorised nine-episode A grid on the frozen BANC
substrate **[M]** (`reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` §6):

| Quantity | Value |
|---|---|
| Episodes executed | 9 / 9 (seeds 9001–9003 × 3) |
| Game updates | 3,784 |
| Neural steps | 126,135 |
| Total spikes | 73,880 (the report's totals line prints 72,880 — a totals-line arithmetic error; per-row values sum to 73,880; `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` §12.1) |
| Motor-population spikes | **0** |
| Decisions | `NO_ACTION` on all 3,784 |
| Decoder fallbacks / unmapped / invalid | 0 / 0 / 0 |
| Termination | collision in all nine; none reached the 900-update cap |
| Weight fingerprint | `4923f0cd…b06d945d5`, identical before and after every episode |

The simulation was not silent or dead: 73,880 spikes occurred. The motor
population was silent **[M]**.

### 1.2 Fact 2 — the activity stops at the first hop, at a measurable margin

The bottleneck investigation **[M]** (`reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`
§10–§11, from Phase 7 and 4H.4 under the same frozen inputs):

- 232 stimulated sensory neurons → 662 signed outgoing edges → 608 first-hop
  targets (607 non-stimulated); 473 of 607 receive current, peak **164.443 pA**;
- peak first-hop membrane potential **−56.926 mV** against a −50 mV threshold, a
  **6.926 mV deficit**; **0** threshold crossings;
- second hop: **0 / 3,576** receivers; motor neurons: **0 / 805**; motor spikes
  **0**;
- **no** motor neuron is a first-hop target of the sensory set; only **4** are
  reachable at two hops (2 JUMP, 0 LEFT/RIGHT);
- 25,332 transmissions occurred (9,499 signed), so synaptic transmission is not
  the failure;
- 0.0 pA of signed inhibitory weight leaves the stimulated set, so sign coverage
  is not the failure for this subset.

The investigation is explicit that these are facts *about this model
configuration*, not about a fly (§11). The 6.926 mV margin depends on the
declared weight scale, LIF parameters and synaptic time constants, and would move
if any of them changed.

### 1.3 Fact 3 — with a silent motor population, F, Fβ, C1 and C4 cannot carry their declared claims

Every decision's motor-feature vector is a function of motor-population activity.
With zero motor spikes it is the zero vector on 100 % of decisions **[A]** from
Fact 1 and §3.6.1's recording rule. The consequences are analytic, not empirical:

- **F** computes `logits = W·0 + b = b`. Its policy is constant, determined by
  its bias. The REINFORCE gradient with respect to the feature weights is
  `(e_a − p)·xᵀ = 0`; `readout/trainer.py:97–138` uses plain
  `torch.optim.SGD` with no weight decay and no entropy bonus, so `W` does not
  move at all during training **[A]**.
- **Fβ** computes `logits = b` by construction; `readout/linear.py:144–171`
  never reads the feature tensor **[A]**.
- Therefore **C4 = F − Fβ** compares two constant-action policies whose only
  difference is their trained bias vector. The contrast remains *computable*, but
  it cannot test REV4 §3.6.2 claim 2 ("state-dependence adds value over the best
  constant policy"), because neither arm is state-dependent **[A]**.
- Likewise **C1 = F − A**: A's fixed decoder never meets its own gate (0 motor
  spikes, §1.1), so A is also a constant-`NO_ACTION` policy. C1 is a difference
  of two constant policies and cannot test H3 ("a trainable readout rescues the
  platform") **[A]**.
- **E3** fails outright (0 motor spikes), and REV4 §3.6.4 then permits exactly
  one sentence: *"the motor populations were silent; the readout could at most
  learn a constant policy."* **E4** is undefined (0/0).

### 1.4 Fact 4 — the C and C′ arms of the §10.8 grid cannot be run

The Pilot 2 readiness decision **[M]** (`reports/PHASE_8_PILOT2_READINESS_DECISION.md`
§3.2, §4) records three independent operational blockers:

- **P2-G** — `CertifiedGraphSource.required_seeds` is `range(1, 17)`
  (`experiments/phase_8_random/campaign_summary.py:35`); no certified random
  graph exists for pilot seeds 9001–9003. C and C′ cannot run, and a campaign
  graph may not be substituted for an independent pilot graph.
- **P2-A (loader)** — `load_training_artifacts` rejects any seed not declared in
  `seeds.campaign` (`experiments/phase_8/training/loader.py:101–104`), and
  `seeds.campaign` is `[1…16]`; the pilot seeds are not declared there.
- **P2-A (artifacts)** — no trained F/Fβ artifact directory exists for the pilot
  seeds under `experiments/results/phase_8/training`.

### 1.5 The consequence for REV4 §10.8

REV4 §10.8 requires the stage to compute the paired standard deviation of C1–C4
and report `σ_max` with its upper confidence limit, so that U7 can choose N. Of
the four contrasts that enter `σ_max`:

- one (C3) is **not runnable** for an operational reason (P2-G) — Fact 4;
- one (C2) is **structurally zero** under the declared eligibility rule (no
  postsynaptic spike at the blocked hop ⇒ no trace; §1.5.1) — Fact 2;
- two (C1, C4) are **computable but void as evidence** for their declared claims
  — Fact 3.

A maximum over a set containing an undefined member is undefined. That is the
precise, non-rhetorical ground for the declaration in §3.5: **`σ_max` is not
evaluable for U7.** It is not a claim that the variance is small; it is a claim
that the quantity U7 names does not exist in this configuration.

#### 1.5.1 Why C2 is structurally zero rather than merely small

Under the declared eligibility convention, a trace is created only on edges whose
presynaptic packet arrives **while the postsynaptic cell spikes**
(`plasticity/traces.py:326–345`, `coincident_edges`, used at
`plasticity/engine.py:134`) **[A]**. With zero first-hop spikes, no eligibility is
created on sensory→first-hop edges, so condition B has nothing to strengthen on
the path whose failure causes the block. B is therefore expected to be
bit-identical to A **[I]**, and `d_i = 0` for every seed.

This is a code-level deduction about the model, not a hypothesis about biology.
Two cautions belong with it:

1. It predicts identity **on the blocked paths**. It does not exclude weight
   changes on edges inside the stimulated set or elsewhere where a postsynaptic
   spike can coincide with an arrival. If B ≠ A is observed, that is a **finding
   about where eligibility can form**, not a failure to be suppressed.
2. A structural zero is not a small variance. Reporting `s_C2 = 0` as a
   "standard deviation" invites the reader to believe the pilot measured low
   variability. It measured a degenerate construction.

---

## 2. Proposed experimental scope

### 2.1 One-sentence scope

Pilot 2-C certifies, on the three pilot seeds, that (i) the platform is at or
below the measured substrate-free floor in every neural arm, (ii) A′ reproduces A
exactly, (iii) Fβ is a genuine constant-action control, (iv) F behaves as a
constant policy whose feature weights provably did not move, and (v) the motor
population is silent at the per-decision level — and it estimates **no** contrast
and discharges **no** U7 decision.

### 2.2 Proposed grid

| Arm | Role in Pilot 2-C | Seeds | Evaluation episodes | Training |
|---|---|---|---|---|
| `A` | reference; also the substrate-driven arm whose floor is certified | 9001–9003 | 3 each = 9 | none |
| `B` | plastic path; certifies the C2 structural zero | 9001–9003 | 3 each = 9 | none (plasticity runs online, per REV4 U9(a)) |
| `F` | readout; certifies bias-only **behaviour** | 9001–9003 | 3 each = 9 | readout only, declared schedule |
| `F_beta` | constant-action control; certifies state-independence **by parameter set** | 9001–9003 | 3 each = 9 | biases only, same schedule as F |
| `A_prime` | internal-validity control; exact identity with A | 9001–9003 | 3 each = 9 | none |
| `floor` | substrate-free constant-`NO_ACTION` control policy (REV4 §3.6.2, U10(b)) | paired environment seeds | 9 replays | none |
| `C`, `C_prime` | **excluded** under the recommended scope (§4.4, §10 OD-2) | — | — | — |
| `D` | **not part of** the REV4 §10.8 grid; not added | — | — | — |

45 neural evaluation episodes, 9 substrate-free replays, one declared readout
training schedule for F and Fβ. No graph is constructed, so the resource that
produced the B7 deviation (§9.3, 1.628 GB during graph construction) is not
consumed.

### 2.3 What Pilot 2-C establishes

Each claim below is a **certification claim**: a statement about whether the
machinery behaves as specified. None is a statement about a fly, and none is a
statement about a contrast between conditions.

| ID | Certification claim | Basis |
|---|---|---|
| **P2C-1 Floor** | For each of A, B, F, Fβ, the paired mean capped-score difference from the measured floor is reported per condition with its per-seed values, and the "at floor" predicate of REV4 §7.8 is evaluated and reported with its value | [M] rows + [M] floor replays |
| **P2C-2 A′ identity** | A′ reproduces A exactly on every seed and episode, on the full P1–P19 comparison, with zero tolerance | [M] rows + in-process comparison |
| **P2C-3 Fβ constancy** | Fβ's trainable parameter set is exactly the four output biases, its policy is identical for `x = 0` and `x = 10⁶`, and every evaluation episode takes exactly one action | [M] rows + [M] controller assertion |
| **P2C-4 F behaviour** | F's feature-weight tensor is bit-identical before and after training; every F evaluation episode takes exactly one action; therefore F is **behaviourally equivalent to a constant policy** under this substrate | [M] digests + [M] action counts, with the [A] gradient argument of §1.3 |
| **P2C-5 Motor silence** | Every decision in every neural arm records `motor_activity.total_spikes == 0`, and the per-population counts are zero for LEFT, RIGHT and JUMP | [M] rows |
| **P2C-6 Plasticity inertness** | B's weight fingerprint equals A's before and after every episode, or a bounded, reported set of edges changed and is attributed to eligible intra-set coincidences | [M] fingerprints + [I] deduction of §1.5.1 |
| **P2C-7 Provenance** | All seven frozen-input hashes and three config hashes match the declared values; no decoder fallback, unmapped action or neural reset occurs | [M] manifest and rows |
| **P2C-8 Operational viability** | 45 episodes execute through the production runner with no manual intervention, no silent retry and no skipped episode | [M] summary |

### 2.4 What Pilot 2-C explicitly does **not** establish

The following list is normative. Any report produced from Pilot 2-C must contain
it, and any sentence that contradicts it is forbidden.

1. It does **not** estimate C1, C2, C3 or C4. No effect size, no difference, no
   direction of effect is reported for any of them.
2. It does **not** test H1, H2 or H3, and it is not evidence for or against any
   of them.
3. It does **not** report `σ_max`, any paired standard deviation as a variance
   estimate, or any upper confidence limit for U7.
4. It does **not** discharge U7 and does **not** write
   `design.n_seeds_selected`.
5. It does **not** compare distributions across arms beyond the floor predicate
   of P2C-1, which is a descriptive categorisation, not a test.
6. It does **not** establish that the readout "learned", "decoded",
   "interpreted", "rescued" or "improved" anything.
7. It does **not** establish that plasticity "does not work": it establishes
   that under the declared eligibility rule no eligibility is created on the
   blocked path.
8. It does **not** revise Phase 4, 5, 6 or 7 findings.
9. It does **not** unblock the confirmatory campaign, training or the G3/B7
   question.
10. It does **not** transfer to the campaign seeds. Pilot seeds are never
    campaign seeds, and pilot rows are never merged into the campaign dataset
    (REV4 §10).

### 2.5 Scope variants

Three variants are possible. They differ only in which blockers must be resolved
first.

| Variant | Arms | Requires | Discharges | Cost |
|---|---|---|---|---|
| **S1 — recommended** | A, B, F, Fβ, A′ (+floor) | P2-A resolution (§7.2) | P2C-1…P2C-8 | 45 episodes + readout training |
| **S2 — full REV4 grid** | S1 + C, C′ | S1 **and** P2-G resolution (new certified graphs for 9001–9003) | P2C-1…P2C-8 plus C′ identity and a C floor certificate | +18 episodes, +3 graph certifications, reopens B7 |
| **S0 — minimal** | A, A′ (+floor) | nothing beyond D2-style authorisation | P2C-1 (A only), P2C-2, P2C-5, P2C-7, P2C-8 | 18 episodes |

S2 is the only variant that could compute `σ_C3`. It still could not produce an
eligible `σ_max`, because C1 and C4 remain degenerate as evidence (Fact 3) and
C2 remains a structural zero (Fact 4). S2 therefore buys an extra dispersion
estimate for a contrast the protocol itself treats as floored and powerless, at
the price of three graph certifications and a reopened B7.

S0 is the fallback if the owner declines to resolve P2-A. Under S0, objective 4
(F/Fβ behaviour) can only be discharged **analytically** — by the code-level
argument of §1.3 and §5.2 — and must be labelled as such: *derived, not
measured*. That is a materially weaker certification and should be accompanied by
a statement that no empirical readout evidence exists.

### 2.6 Separation of certification evidence from confirmatory evidence

This is the rule that keeps a certification stage from contaminating the
confirmatory family.

| | Certification evidence (Pilot 2-C) | Confirmatory evidence (REV4 campaign) |
|---|---|---|
| Question | Did the machinery behave as specified? | Did condition X differ from condition Y on the primary outcome? |
| Unit | episode and arm-within-seed | seed, paired |
| Permitted statistics | counts, digests, exact equality, the §7.8 floor predicate, descriptive per-seed means | exact sign-flip, Holm m = 4, effect sizes |
| Permitted outputs | pass / fail / not-evaluable per certification claim | p-value, CI, effect size per contrast |
| May invalidate a campaign arm? | **yes** — e.g. A′ ≠ A invalidates B (REV4 §3.8.4) | n/a |
| May support a hypothesis? | **no, never** | **yes, that is its only purpose** |
| May enter the confirmatory family? | **no** | n/a |
| Storage | its own run directory, its own manifest | `episodes.jsonl`, append-only |

Operational rules that follow:

1. No Pilot 2-C output is imported into any campaign analysis.
2. `merged_into_campaign` is `false` on every output record, and the record kind
   is distinguishable from the campaign's.
3. A certification failure is a **methodological** result. It ends in a
   methodological conclusion (e.g. "the F arm is INVALID") and never in a
   behavioural one.
4. A certification **pass** licenses only the statement "the machinery behaved as
   specified on the pilot seeds". It licenses no claim about the campaign's
   outcome.

---

## 3. Mathematical and statistical definitions

### 3.1 Outcome

For seed `i`, condition `c`, episode `k`, let `U` be the observed update count.
The **capped survival score** (REV4 §5.1) is

```
U*_{i,c,k} = min(U_{i,c,k}, 900)
y_{i,c}    = (1/K) · Σ_{k=1..K} U*_{i,c,k}          K = 3
```

The seed is the unit (REV4 §7.2). `y` is never called a survival time and is not
right-censored; cap reaches are recorded as 900 with `truncated: true`.

### 3.2 The floor

The floor is a **measured** control, not an analytic quantity (REV4 §3.6.2, U10).
For the paired environment seed of seed `i`,

```
f_i = y_{i,floor}     (constant-NO_ACTION policy, substrate-free replay)
```

The **floor gap** of condition `c` on seed `i` is `g_{i,c} = y_{i,c} − f_i`, and
the condition is **at floor** when

```
(1/N) · Σ_i g_{i,c}  ≤  0            (REV4 §7.8, correction 6; tie = at floor)
```

A missing floor makes the predicate **not evaluable**, never satisfied. The
predicate is used only to select descriptive wording; it is not a test and never
excludes a condition from the confirmatory family.

### 3.3 Paired difference and dispersion (defined, not used in Pilot 2-C)

For a contrast `c = (m, s)` (minuend, subtrahend),

```
d_i      = y_{i,m} − y_{i,s}
d̄        = (1/N) Σ_i d_i
s_c      = sqrt( (1/(N−1)) · Σ_i (d_i − d̄)² )        df = N − 1
```

The one-sided upper confidence limit for `σ` at confidence `1 − α` is

```
UCL_{1−α}(σ) = s · sqrt( df / χ²_{α, df} )
```

At `df = 2` the lower chi-square quantile is `χ²_{α,2} = −2 ln(1 − α)` in closed
form, so

```
UCL_{1−α}(σ) = s · sqrt( 2 / (−2 ln(1 − α)) )
```

which is ≈ **2.11695 · s** at 80 %. These definitions are retained verbatim from
REV4 §7.1/§7.4 and `experiments/phase_8/stages/pilot2.py:upper_confidence_factor`
so that no reader has to reconcile a new formula with the old one. **Pilot 2-C
computes none of them for the purpose of sizing a campaign.**

### 3.4 Contrast status lattice

Each contrast in the §10.8 grid is assigned exactly one status. The lattice is
the operative definition of "degenerate comparison" for this proposal.

| Status | Meaning | May be reported as a contrast? |
|---|---|---|
| `estimable_and_interpretable` | every cell present, and the difference can move for the reason the contrast names | yes |
| `estimable_but_degenerate` | every cell present, the number exists, but the difference cannot test the named claim because the arms do not differ in the relevant mechanism | **no** — report the reason, not the number |
| `structurally_zero` | the difference is identically zero by construction of the model | **no** — report the construction, not an sd |
| `not_evaluable` | a required cell cannot be produced | **no** — report the blocker |

Applied to the REV4 §10.8 grid under current facts:

| Contrast | Definition | Estimable? | Interpretable? | Status | Reason |
|---|---|---|---|---|---|
| **C1 = F − A** | H3 | yes | **no** | `estimable_but_degenerate` | A and F are both constant policies under a silent motor population (§1.3); any difference is a bias-trajectory difference, not a decoding difference |
| **C2 = B − A** | H1 | yes | yes as a *measurement*, void as evidence under a floor | `structurally_zero` | no eligibility on the blocked path (`plasticity/traces.py:326–345`); expected `d_i = 0` ∀ i |
| **C3 = A − C** | H2 | **no** | **no** | `not_evaluable` | no certified pilot graph (P2-G); and A and C would both be floored, so REV4 §7.8 attaches no power |
| **C4 = F − Fβ** | §3.6.2 claim 2 | yes | **no** | `estimable_but_degenerate` | neither arm is state-dependent when `x ≡ 0`; the claim tested is "state-dependence adds value", which the construction cannot express |

### 3.5 Declaration: `σ_max` is not evaluable for U7

**Proposed declaration.** For the Pilot 2-C grid, `σ_max` is declared
**not evaluable** and is not reported. U7 is therefore **not discharged** by this
stage, `design.n_seeds_selected` remains `null`, and the predeclared default
N = 16 governs if a campaign is ever authorised.

Four independent justifications; any one of them alone would be sufficient.

**(a) Definitional.** `σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4)` (REV4 §7.1). `σ_C3`
is undefined because C is not run. A maximum over a set containing an undefined
element is undefined. There is no defensible convention under which the
undefined element is replaced (with zero, with the previous value, or by
dropping it) that REV4 predeclares; inventing one after seeing the grid would be
a post-hoc definition.

**(b) Structural zero is not a variance.** `σ_C2 = 0` exactly, because `B ≡ A`
by the eligibility rule. The estimator `s` is not a noisy measurement of a
positive quantity here; it is the constant 0 of a degenerate construction. Its
upper confidence limit is 0 by the same construction, and the confidence
statement attached to that 0 is vacuous. Treating it as evidence of low
dispersion is a category error, and it is exactly the failure mode the readiness
decision forbids ("do not let `σ_max ≈ 0` select N = 10").

**(c) Interpretive.** `σ_C1` and `σ_C4` are dispersions of differences between
constant policies. They are computable, but they are not the dispersions of the
confirmatory contrasts they are named for, because the *scientific content* of
those contrasts is void while E3 fails (REV4 §3.6.4). Sizing the confirmatory
family from them would size a test whose estimand is degenerate — a power
calculation for a null by construction.

**(d) Decision-theoretic redundancy.** With N = 3, `df = 2`, and the 80 % upper
limit is ≈ 2.11695 · s. REV4 §7.1 states in terms that a 3-seed pilot *cannot*
establish the 112.87 bound. Therefore the only decision a 3-seed pilot can
produce under U7 is "N = 10 is not supported", i.e. the predeclared default
N = 16. Declaring `σ_max` not evaluable changes no predeclared decision; it only
prevents a misleading number from entering a report.

**What the declaration does not do.** It does not weaken the 4 GiB memory gate,
the B1/B2/B3–B6/B7 gates, or the campaign's requirement that U7 be decided
before any campaign. It does not select N = 16 *as a U7 decision*; it leaves U7
open and the campaign blocked.

### 3.6 The confirmatory contrasts are preserved unchanged

Quoted from `experiments/phase_8/registry.py::CONFIRMATORY_CONTRASTS`, unchanged
by this proposal:

| ID | Contrast | Hypothesis | Family role |
|---|---|---|---|
| C1 | `F − A` | H3 | confirmatory, m = 4 |
| C2 | `B − A` | H1 | confirmatory, m = 4 |
| C3 | `A − C` | H2 | confirmatory, m = 4 |
| C4 | `F − F_beta` | REV4 §3.6.2 claim 2 | confirmatory, m = 4 |

Nothing in this proposal changes a minuend, a subtrahend, a hypothesis, a family
size, α = 0.05 two-sided, Holm m = 4, SEI = 100 updates, N = 16/10, K = 10, the
exact sign-flip test or the zero-difference policy. Pilot 2-C produces no input
to any of them.

### 3.7 Why no p-value is computed in Pilot 2-C

Three reasons, each independently sufficient:

1. REV4 §10 states that neither pilot is a hypothesis test; computing one would
   contradict the protocol even if the number existed.
2. At N = 3 the attainable two-sided exact p is `2/2³ = 0.25 > 0.05`: no
   outcome could reach significance under any assignment of the data.
3. The four contrasts are, per §3.4, degenerate or not evaluable, so there is no
   estimand to test.

---

## 4. Conditions and controls

### 4.1 Retained, with the property each certifies

| Arm | Retained? | Property certified | Why it remains meaningful |
|---|---|---|---|
| `A` | yes | floor gap; reference for A′; motor silence | It is the reference arm and the only arm whose behaviour is known end-to-end from Pilot 1 [M] |
| `B` | yes | C2 structural zero; plasticity inertness | Its expected identity with A is a *prediction of a code-level deduction*; confirming it distinguishes "inert by construction" from "silently broken" |
| `F` | yes | behavioural constant-policy status; feature-weight invariance | The one arm where a plausible-but-wrong inference ("the readout learned to act") is most available; certification forecloses it |
| `F_beta` | yes | parameter-level state-independence; constant action | The control that makes F's status interpretable; REV4 §3.6.2 makes it mandatory wherever F is reported |
| `A_prime` | yes | exact identity with A | REV4 §3.8.4 hard stop; a failure invalidates B and is a methodological result |
| `floor` | yes (control, not an arm) | measured substrate-free baseline | Required by REV4 §3.6.2/U10 and by the §7.8 floor predicate |
| `C` | **no** (S1) | — | Not runnable on pilot seeds; remains a campaign prerequisite |
| `C_prime` | **no** (S1) | — | Depends on C |
| `F_init` | optional | REV4 §3.6.2 claim 4 diagnostic | Cheap (no training); include only if F and Fβ are run — it costs 9 evaluation episodes per arm in REV4 §10.8 terms, but here it is one extra constant-policy arm |

### 4.2 Controls that are *not* meaningful in this configuration

- **The frozen-parameter ablation (REV4 §3.6.3) as evidence of state
  dependence.** Ablation sets `x := 0`. When `x ≡ 0` already, the ablation is a
  no-op and the ablated argmax equals the unablated argmax on every decision
  trivially. The resulting label distribution is an artefact of the input being
  zero, not a measurement. It must be recorded — REV4 requires the field — but it
  must be labelled *uninformative in the zero-input regime* and may not be cited
  as evidence that a decision was bias-driven.
- **E4 (motor-driven fraction).** Denominator 0 → undefined (REV4 §3.6.4).
  Recorded as `E4: undefined (0/0)`, never as a pass.
- **C4 as a test of state-dependence.** See §3.4.
- **C1 as a test of readout rescue.** See §3.4.

### 4.3 What is still meaningful about B

B is retained for one reason: it converts a prediction into a checked statement.
The prediction is that the plastic path is *inert* on the blocked pathway. If B's
weight fingerprint is identical to A's in every episode, the report may state:
"under the declared eligibility convention, no eligibility was created on
sensory→first-hop edges, so condition B produced no weight change on the blocked
path." If B differs, the report must locate the differing edges and attribute
them to eligible postsynaptic coincidences, and it must state that the
deduction was incomplete. In neither case may the report say "plasticity has no
effect" (REV4 §7.8, §3.6.4).

### 4.4 Why C and C′ are excluded under the recommended scope

Exclusion is a **scope** decision, not a scientific verdict:

1. **Operationally impossible today.** No certified graph exists for the pilot
   seeds, and the readiness decision forbids substituting a campaign graph
   (P2-G).
2. **Inferentially void even if run.** A and C would both be at floor; REV4 §7.8
   states the design has no power against a difference between two floored
   conditions. C3 would be a difference of two constant `NO_ACTION` policies.
3. **C′ has no mirror without C.** `IDENTITY_REQUIRED["C_prime"] = ("C", "D")`;
   with C absent there is nothing for C′ to reproduce.
4. **Cost.** Three BANC-scale graph certifications reopen B7, the constraint that
   produced the recorded §9.3 deviation. Excluding C/C′ means Pilot 2-C
   constructs no graph at all.

C remains **required for the campaign** (H2) and remains blocked by B7. Dropping
it from the pilot does not drop it from the protocol.

---

## 5. How F and Fβ bias-only behaviour is evaluated

This section discharges objective 4. It separates three things that are easy to
conflate: the *parameter set*, the *behaviour*, and the *claim*.

### 5.1 Two distinct predicates — never interchange them

| Predicate | Definition | Holds for F? | Holds for Fβ? |
|---|---|---|---|
| `parameter_bias_only(arm)` | the set of trainable parameters is exactly the four output biases; no feature weight is trainable | **no** — F's feature weights are trainable (REV4 §3.6 row 3–4) | **yes** — `BiasOnlyReadout`; optimizer names are `["bias"]` (`controls/f_beta.py:56–82`) |
| `behaviourally_state_independent(arm, rows)` | the emitted action distribution does not depend on the motor-feature vector, on the evidence at hand | **yes in this configuration** (§5.2) | **yes by construction** (§5.3) |

**Naming rule (REV4 §3.6.2, restated because it is the most likely violation).**
"Bias-only" may be used **only** for an arm satisfying `parameter_bias_only`.
F must be described as *"behaviourally equivalent to a constant policy"*, never as
"bias-only" — even though, in this configuration, its behaviour is exactly that.
The distinction matters because the two statements are established by different
evidence and would diverge the moment the motor population became active.

### 5.2 Certifying F's behaviour

The certification has four parts, three measured and one analytic.

**(i) Zero-input premise.** For every decision in every F and Fβ episode,
`motor_activity.total_spikes == 0`, and `LEFT`, `RIGHT`, `JUMP` each report
`spikes == 0`. This is a stored field (REV4 §3.6.1) **[M]**.

**(ii) Feature-weight invariance.** The readout's feature-weight tensor digest is
recorded at initialisation, after every training update, and at the end of
training. All digests must be equal. Backing derivation **[A]**: for a linear
softmax readout, `∂/∂W [ −log π(a|x) · G ] = −(e_a − p) xᵀ`; at `x = 0` this is
exactly zero; `readout/trainer.py:80–82, 126–138` uses
`torch.optim.SGD` with no weight decay and no entropy term, so a zero gradient
produces an exactly zero parameter delta. The digest check is therefore an
empirical confirmation of a derivation, not a search for an effect.

**(iii) Decision constancy.** In each F evaluation episode, `action_counts` has
exactly one non-zero entry. (REV4 §3.6.2's `Fβ` definition uses the same test;
`stages/pilot2.py::_constant_action_check` already implements it for Fβ and is
extended to F here.)

**(iv) Initial-parameter comparison (optional).** Where an `F_init` arm is run,
report the paired descriptive difference `y_{i,F} − y_{i,F_init}`. Under a
constant policy this is a bias-trajectory comparison. It may be reported
descriptively; it may **not** be reported as claim 4 ("F learned"), because
claim 4 requires that what was learned is motor decoding, and E3 fails.

**Certification verdict.** F is certified `behaviourally_constant` if (i)–(iii)
hold. If (ii) fails — feature weights moved — the zero-input premise or the
gradient derivation is wrong, and the run is INVALID pending investigation. If
(iii) fails — F emits more than one action within an episode — F is *not*
behaviourally constant, and the §1.3 reasoning must be re-examined before any
other use of F's rows.

### 5.3 Certifying Fβ

**(i) Parameter set.** `trainable_parameter_names == ["bias"]`
(`controls/f_beta.py:67–74`). The optimizer must contain no other tensor.

**(ii) State-independence.** `logits(0) == logits(1e6)` elementwise, and
`BiasOnlyReadout.forward` does not read the feature tensor
(`readout/linear.py:144–171`). `controls/f_beta.py:75–81` asserts this at build
time; the certification re-asserts it at evaluation time and records the result.

**(iii) Decision constancy.** Exactly one action per episode, as for F.

**(iv) Training actually occurred.** `Fβ` is not the floor: it trains, and its
action distribution is data-independent but not forced to one action
(`controls/f_beta.py` module docstring). The certification records the bias
vector before and after training and requires it to have changed if the arm is
to be described as trained. If the biases did not move, Fβ is indistinguishable
from `F_init` and must be reported as such.

### 5.4 What F − Fβ means here, and what it does not

If both arms are behaviourally constant, `y_{i,F} − y_{i,Fβ}` is a difference
between two constant policies selected by two bias trajectories under the same
seed, environment and training schedule.

- **Permitted statement:** "F and Fβ both selected constant actions; their scores
  differed by X on the pilot seeds."
- **Forbidden statement:** "F beat Fβ, therefore state-dependence adds value"
  (REV4 §3.6.2 claim 2) — the requirement is not met.
- **Forbidden statement:** "F and Fβ tied, therefore motor activity is
  unnecessary" — they tied because there was no motor activity to use.

### 5.5 Pre-declared expectations (to be checked, not assumed)

| Expectation | Reason | If violated |
|---|---|---|
| `motor_activity.total_spikes == 0` on 100 % of decisions in A, B, F, Fβ, A′ | Pilot 1 [M]; anatomy [A] | Investigate before any certification claim; a nonzero count contradicts Fact 1 |
| The §3.6.3 ablation changes no argmax | `x ≡ 0` makes ablation a no-op | Investigate; a change would imply the ablation path is not what §3.6.3 declares |
| Every decision is labelled `bias-driven` (if the chosen action is not `NO_ACTION`) or `undefined` (if it is) | follows from the ablation being a no-op | Any `motor-driven` label is a contradiction and stops the certification |
| F's feature-weight digest is unchanged after training | §5.2(ii) | INVALID run pending investigation |
| Fβ's bias vector changes during training | §5.3(iv) | Fβ is effectively `F_init`; report it as such and do not call it a trained control |

---

## 6. Acceptance criteria

Two classes: **certification pass criteria** (what must hold for the stage to
report a pass) and **stop criteria** (what ends the stage or invalidates an arm).
A criterion that is not evaluated is `not_evaluable`, never `pass`.

### 6.1 Per-claim acceptance

| Claim | Pass predicate | On failure |
|---|---|---|
| P2C-1 floor | floor measured for all 9 paired environment seeds; per-condition floor gap reported with its value; §7.8 predicate evaluated with its value | If any floor replay is missing: `not_evaluable`, and no floor statement is made |
| P2C-2 A′ identity | full P1–P19 comparison equal for every seed and episode, zero mismatches, zero missing pairs | **hard stop** (REV4 §3.8.4): A′ stops, B is marked INVALID, artifacts retained, no retry with a different seed |
| P2C-3 Fβ constancy | parameter set == `{bias}`; state-independence assertion holds at evaluation; exactly one action per episode; biases changed during training | Any failure: Fβ is not the declared control; it may not be used to interpret F; report the failure |
| P2C-4 F behaviour | zero-input premise holds; feature-weight digests all equal; exactly one action per episode | Feature-weight drift ⇒ INVALID; non-constant decisions ⇒ re-examine §1.3 before further use |
| P2C-5 motor silence | `total_spikes == 0` and per-population zeros on 100 % of decisions in every neural arm | Any nonzero count contradicts Fact 1 and stops the certification pending investigation |
| P2C-6 plasticity inertness | B's weight fingerprint equals A's before and after each episode, **or** every differing edge is enumerated and attributed to an eligible postsynaptic coincidence | Unattributed differences ⇒ the §1.5.1 deduction is incomplete; report, do not suppress |
| P2C-7 provenance | 7 input hashes and 3 config hashes match; `decoder_fallbacks == {}`; `unmapped_actions == 0`; `invalid_actions == 0`; no neural reset | Any mismatch: the run is not certifiable; it is retained and labelled |
| P2C-8 viability | 45 planned episodes executed and stored; `complete == true`; no episode `status != ok`; no silent retry | An incomplete grid is `not_evaluable`, never partially passed |

### 6.2 Global stop criteria

1. **Authorization.** No stage run without a validated owner record covering
   this exact grid (§7.4). The D2 exemption does **not** cover Pilot 2 and cannot
   be widened.
2. **Memory.** The 4.0 GiB gate is checked before any directory is created and,
   per the Pilot 1 practice, sampled passively during the run. Below the gate the
   stage does not start and records the reason (REV4 §9.3, Phase 2.5 rule).
3. **Integrity.** The 37-file protected baseline is checked. The pre-existing
   `motor/__init__.py` drift (introduced by `3c74ae8`, 2026-11-19) still makes
   `check_integrity()` return `pass = false`. Pilot 2-C is therefore **not
   publishable as a freeze report** unless the drift is resolved by an authorised
   amendment or a compliant restoration (§10 OD-6).
4. **No parameter change.** No drive scale, decoder threshold, LIF constant,
   weight transform, time constant, random seed derivation or episode cap may be
   altered to obtain an outcome. A certification stage that tunes the thing it
   certifies certifies nothing.
5. **No seed substitution.** Campaign seeds may not stand in for pilot seeds, and
   an untrained artifact may not stand in for a trained one.

### 6.3 What a pass licenses

A fully passing Pilot 2-C licenses exactly this report headline:

> On the three pilot seeds, A, B, F and Fβ were at or below the measured
> substrate-free floor; A′ reproduced A exactly; Fβ was a constant-action
> control; F behaved as a constant policy with unchanged feature weights; the
> motor populations were silent on every decision. No contrast was estimated, no
> dispersion was estimated, and U7 remains open. The confirmatory campaign
> remains blocked.

Nothing stronger.

---

## 7. Execution requirements

Everything in this section is **work that does not exist**, listed so the owner
can price it. None of it is performed by this document.

### 7.1 P2-R — production episode runner (required)

`experiments/phase_8/stages/pilot1_runner.py` is the template: a class holding
the configuration, an injectable factory, lazy BANC load, `input_hashes()`
covering the seven frozen inputs, and provenance recorded before the episode. A
`pilot2_runner.py` must additionally:

1. construct per-arm components through the campaign factory rather than
   hand-assembling them;
2. for `A_prime`, obtain the paired A result for the same `(seed, episode)` and
   call `controls.a_prime.run(fixed_result=...)`, which performs the comparison
   in `controls/equivalence.compare_runs` — the store-level reduced check in
   `pilot2.py::_identity_check` is explicitly **not** sufficient for P1–P19;
3. for `F` and `Fβ`, run the declared training schedule on training seeds
   disjoint from 9001–9003, then evaluate with a frozen controller
   (`conditions/f_readout.py` and `controls/f_beta.py` both raise
   `ConditionError` on a mismatch between role and controller mode);
4. for `floor`, call `conditions.execute.floor_episode` on the paired environment
   seeds;
5. write rows through the existing validated store only.

The CLI currently passes `episode_runner=None`
(`experiments/phase_8/stages/pilot2.py:817–826`), so `--run` cannot execute even
if authorization were granted. That wiring is part of this requirement.

### 7.2 P2-A — training artifacts and the loader contract (owner decision)

Two distinct things are needed.

**(a) A decision on how F and Fβ obtain their trained parameters.** Two models
exist and they are not equivalent:

| Model | Mechanism | Status today |
|---|---|---|
| **Artifact model** | Pre-trained readout artifacts under `experiments/results/phase_8/training`, loaded by `training/loader.py`, fully re-verified, F/Fβ pair sharing one training run | This is what `pilot2_readiness` checks and what the campaign factory consumes. **No artifacts exist for pilot seeds, and the loader rejects undeclared seeds** |
| **In-arm training model** | The pilot trains the readout during its own training episodes using `conditions/f_readout.py` with `training=True` and a `ReinforceTrainer` | Technically supported by the condition code, but the pilot rows would then depend on a training run that the artifact contract never certifies, and the campaign would use a different provisioning path — a contract divergence |

**Recommendation.** Use the artifact model. It keeps one provisioning path for
pilot and campaign, which is the only way a pilot certification can say anything
about the campaign's machinery. The cheaper alternative (in-arm) is defensible
only if the report states that the pilot's F arm is *not* the campaign's F arm.

**(b) The loader contract must change or the pilot seeds must be declared.**
`load_training_artifacts` rejects any seed outside `seeds.campaign`
(`training/loader.py:101–104`). Documented options
(`reports/PHASE_8_PILOT2_READINESS_DECISION.md` §4):

| Option | Change | Independence | Verdict |
|---|---|---|---|
| **A-1** | declare an explicit pilot training-seed set in config, with the loader accepting it | preserved — pilot stays a separate set | **recommended** |
| **A-2** | amend the loader contract to key artifacts by evaluation seed without requiring campaign membership | preserved, but a contract change with campaign-wide effect | acceptable, heavier |
| **A-3** | add 9001–9003 to `seeds.campaign` | destroyed — pilot seeds become campaign seeds | **rejected**; it would also make pilot rows mergeable and violate REV4 §10 |

### 7.3 P2-G — graph certification (not required under S1)

Under S1 no graph is built and P2-G is not on the critical path. Under S2 the
owner must certify three new graphs for 9001–9003, which:

- reopens the §9.3 memory constraint that produced the recorded B7 deviation;
- costs 2–15 min per graph [I] plus certification;
- must still satisfy R1–R18 including the rewired-fraction and
  neighbourhood-overlap gates.

The recorded deviation is unchanged by any Pilot 2-C outcome
(`status = deviation_recorded`, `gate_weakened = false`,
`min_observed_free_gb = 1.628`, 16 certified seeds).

### 7.4 Authorization and gates

| Gate | Current status | What Pilot 2-C needs |
|---|---|---|
| B1 — REV4 approval | D1 recorded | unchanged; D1 already applies |
| B2 — `design.n_seeds_selected` non-null | null | **not required** for a certification stage, which sets no N; but the existing campaign authorizer treats it as blocking. A stage-specific exemption is needed |
| B3–B6 — training declarations | blocked; `assert_training_authorized()` **always raises** (`training/gate.py`) | **required** under either provisioning model, because readout training must be authorised; under the artifact model the training run is a prerequisite stage. This is the single largest authorization gap |
| B7 — G3 deviation | `deviation_recorded` | D2 does not extend to Pilot 2 (D2's own scope says so). A **new** owner decision is needed, scoped field-for-field like D2 |
| B8 — 4.0 GiB memory | gate exists | re-checked before start; unchanged |

`stage_authorization()` has no Pilot 2 branch and `assert_campaign_authorized()`
is deliberately not stage-aware. Implementing a Pilot 2 exemption is a **source
change** (`campaign/protocol.py`), analogous to `PILOT1_G3_SCOPE` but hard-coded
to the Pilot 2-C grid so that a changed configuration cannot widen it. This
document proposes the scope; it does not write the code.

### 7.5 Budget and memory (estimates)

Anchors **[M]**: Pilot 1 measured 357.0 s wall for 9 episodes (17.79–72.81 s per
episode at 213–620 updates), i.e. ≈ 0.083–0.117 s per update; REV4 §9.2 records
22.345 s per 213-update episode and 94.4 s at the 900-update cap.

| Component | Episodes | Estimate [I] |
|---|---|---|
| A, B, A′ evaluation | 27 | 8–33 min (+20–40 % for B's plastic path) |
| F, Fβ evaluation | 18 | 5–22 min |
| F, Fβ training (20 episodes/seed × 3 seeds, twice) | 120 | 36–146 min |
| floor replays | 9 | seconds |
| BANC load and overheads | — | 1–3 min |
| **Total (S1)** | 165 + 9 replays | **≈ 0.8–3.4 h** |

Memory: Pilot 1 sampled 177 times, process RSS max 0.3725 GiB and system
available min 4.1997 GiB against a 4.0 GiB gate **[M]**. Pilot 2-C holds no more
than one substrate at a time and stores no graph, so the binding risk is the same
as Pilot 1's: a machine already near the gate. The gate is checked, never waived.

### 7.6 Evidence labelling

Rows must be distinguishable from campaign rows without a schema change. Proposal:
keep the row schema exactly as it is (so no validator change), set
`notes.evidence_kind = "pilot"` as Pilot 1 did, and record the certification
purpose in the **manifest** and in every summary record, e.g.
`stage_purpose = "floor_and_identity_certification"`. If the owner prefers a
row-level label, that is a schema change and a separate decision.

---

## 8. Exact differences from REV4

Everything below is a difference from the frozen REV4 text. Nothing else in REV4
is changed, and no difference takes effect without §10 OD-1.

| # | REV4 §10.8 as written | Proposed Pilot 2-C | Class |
|---|---|---|---|
| 1 | Grid: 3 seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes | 3 seeds × {A, B, F, Fβ, A′} × 3 episodes (+ floor control) | scope reduction |
| 2 | Acceptance: "computes paired sd for C1–C4 and reports `σ_max` with its upper confidence limit" | No paired sd is computed for U7; `σ_max` is declared **not evaluable** under §3.5; per-contrast status is reported from the §3.4 lattice | criterion replaced |
| 3 | Acceptance: "applies the predeclared N decision (N = 16 primary; N = 10 only if `σ_max ≤ 112.87` is defensible)" | U7 is **not** discharged; `design.n_seeds_selected` stays null; N = 16 remains the predeclared default for any future campaign | decision deferred (not re-made) |
| 4 | "B is included so `σ_C2` is estimated" | B is included so the structural zero of C2 is **certified**, not estimated | rationale replaced |
| 5 | Acceptance: "A′ ≡ A and C′ ≡ C on all 3 seeds" | A′ ≡ A retained in full; C′ ≡ C dropped with C | scope reduction |
| 6 | No explicit floor acceptance criterion at §10.8 | Floor certification added as an explicit acceptance claim (P2C-1) | criterion added |
| 7 | No explicit Fβ certification criterion at §10.8 | Fβ constant-action / state-independence certification added (P2C-3) | criterion added |
| 8 | No explicit F bias-only-behaviour criterion | F behavioural certification added (P2C-4), with the §5.1 naming rule | criterion added |
| 9 | No explicit motor-silence acceptance criterion at §10.8 | Motor-silence certification added (P2C-5) | criterion added |
| 10 | Evidence is implicitly "pilot" | Certification evidence is separated from confirmatory evidence by an explicit rule (§2.6) | interpretation rule added |
| 11 | `σ_max` reported with 80 % and 95 % limits | Neither is reported | output removed |
| 12 | Authorization: no Pilot 2 exemption exists | A new owner record and a hard-coded stage scope are required (§7.4) | authorization prerequisite added |
| 13 | Training provisioning: not specified for pilots | Artifact model recommended; loader contract change or pilot seed declaration required (§7.2) | implementation prerequisite specified |
| 14 | Integrity: freeze requires 36/37 | Pilot 2-C is not a freeze report while the `motor/__init__.py` drift persists (§6.2) | status qualification |
| 15 | Wall-time budget in §9.2 covers the campaign | §7.5 adds a Pilot 2-C estimate of ≈ 0.8–3.4 h | estimate added |

**Not changed by this proposal:** §0 expectations, §3.6.2 Fβ definition and the
four readout claims, §3.6.3 ablation labels, §3.6.4 E1–E5, §3.7, §3.8 A′/C′
semantics, §4 H1–H6, §5.1 outcome, §5.3 C1–C4, §6 seeds, §7.1–§7.8, §9.3 gate,
§10.0–10.7 and §10.9–10.13, §11 limitations, §12 U1–U18, Appendix C constants.

---

## 9. Scientific limitations

The re-scoping removes a failed measurement; it does not remove the reason the
measurement failed.

1. **Certification is not inference.** Every result is a statement about the
   machinery on three pilot seeds. None is a statement about behaviour, the fly,
   or an effect.
2. **The floor finding is model-specific.** "At floor" means at or below the
   substrate-free constant-`NO_ACTION` replay under this game, this reward
   function and these environment seeds. It says nothing about whether the
   environment is solvable, and U1-E cannot be decided without E.
3. **Three seeds.** Any per-seed quantity is a sample of one network draw per
   seed with K = 3 episodes. No dispersion statement is supportable, which is
   precisely why `σ_max` is withdrawn rather than reported as small.
4. **F's certification is conditional on silence.** If the motor population
   became active — by a declared, separately pre-registered change to drive or
   decoder, which is Phase 9 and not this proposal — F's feature weights would
   move and its policy would stop being constant. The certification is a
   statement about the frozen configuration only.
5. **Dropping C/C′ leaves H2 un-certified and un-sized.** No pilot evidence
   about wiring will exist. C remains a campaign prerequisite and remains blocked
   by B7. This is a real loss of coverage, accepted for a real operational reason.
6. **B's inertness is a property of the declared eligibility convention**, not of
   biological plasticity. The permitted statement is about this model.
7. **The ablation and E4 are uninformative in the zero-input regime** (§4.2).
   This is a limitation of the measurement instrument, not of the substrate.
8. **U7 remains open, so the campaign cannot be sized.** Declaring `σ_max` not
   evaluable does not supply an N; it records that the pilot cannot supply one.
   A future σ estimate requires either a larger pilot (≥ 5 seeds, per REV4 §7.1)
   or independent variance evidence, both out of scope here.
9. **The confirmatory family may still be uninformative by construction**
   (REV4 limitation 27). Nothing here changes that; it is the reason a scope
   decision is needed rather than a campaign.
10. **Re-running pilot seeds does not create independent evidence** about the
    campaign, and pilot rows are never merged (REV4 §10).
11. **Integrity is not certified.** The protected-baseline drift means Pilot 2-C
    can be a valid measurement and still fail the publication gate. That outcome
    must be stated, not worked around.
12. **Naming.** "Bias-only" is reserved for Fβ's parameter set; F is
    "behaviourally equivalent to a constant policy". This is a limitation of the
    vocabulary as much as of the experiment, and it is the phrase most likely to
    be eroded in a summary.

---

## 10. Owner decisions required

Seven decisions. Each is stated so that the owner can accept, reject or modify it
independently; none implies another, except where a dependency is named.

| ID | Decision | Depends on | What it does **not** authorise |
|---|---|---|---|
| **OD-1** | **Adopt the re-scope.** Pilot 2 becomes a floor-and-identity certification stage with the §2.2 grid and the §2.4 prohibitions | — | Any execution, any REV4 change (REV4 needs a separate amendment or a REV5), any campaign |
| **OD-2** | **G3/B7 applicability for this stage.** Either (a) exclude C and C′ from the pilot (recommended), or (b) authorise certification of three new pilot graphs and accept the reopened memory risk | OD-1 | Waiving B7 for the campaign, training or C/D in any other stage; D2 remains exactly as recorded |
| **OD-3** | **Readout provisioning.** Choose the artifact model (recommended) and a resolution of the loader contract: A-1 declare a pilot training-seed set, or A-2 amend the loader. A-3 (pilot seeds into `seeds.campaign`) is rejected | OD-1 | Training any model that is not declared; reusing a campaign seed; bypassing B3–B6 |
| **OD-4** | **U7 disposition.** Record formally that Pilot 2-C does not discharge U7, that `σ_max` is not evaluable (§3.5), and that N = 16 remains the predeclared default for any future campaign | OD-1 | Selecting N for a campaign; running a campaign; weakening §7.1 for any later stage |
| **OD-5** | **Floor decomposition and U1-B.** REV4 U1-B requires "run the predeclared floor decomposition and stop for a scope decision" when A and F are floored. Record U1-B as the applicable case, with Pilot 1 plus Pilot 2-C as its evidence | OD-1 | Changing drive or decoder inside Phase 8; treating U1-B as a result about neural conditions |
| **OD-6** | **Integrity / publication status.** Either authorise an amendment or compliant restoration for the `motor/__init__.py` drift, or accept that Pilot 2-C is a valid but non-freeze report | — | Deleting, reverting or editing protected files without an explicit instruction |
| **OD-7** | **Evidence labelling.** Accept manifest-level `stage_purpose` labelling (no schema change), or request a row-level label (schema change) | OD-1 | Changing the campaign schema |

### 10.1 What a new approval record must contain

For OD-1/OD-2/OD-3/OD-4 to be executable, a record analogous to D2 is required,
with these properties (a template, not a record):

- `record_kind` = `phase_8_owner_decision`; `approval_id` = a new identifier
  (e.g. `D3`);
- `depends_on` = D1 and D2, both validated;
- `approved_document.sha256` = the hash of the amended protocol **or** of REV4
  plus a hash-bound amendment document — the D2 pattern binds to one document
  hash and this must be decided explicitly;
- `scope.stage` = `pilot2`; `arms` = `["A","B","F","F_beta","A_prime"]`;
  `seeds` = `[9001,9002,9003]`; `episodes_per_seed` = 3; `n_episodes` = 45;
  `uses_randomized_graph` = false; `uses_trained_artifact` = true or false
  matching OD-3; `estimates_contrasts` = false;
  `declares_sigma_max_not_evaluable` = true;
  `sets_n_seeds_selected` = false;
- explicit negative flags: `accepts_g3_deviation: false`,
  `weakens_graph_certification: false`, `parameter_modifications_authorised:
  false`, `authorises_campaign: false`, `authorises_training_outside_declared_
  seeds: false`.

The code that would read such a record does not exist. Writing it is a source
change and is itself subject to owner authorisation. Until both the record and the
code exist, `stage_authorization("pilot2", …)` continues to refuse, and that
refusal is correct.

### 10.2 What the owner can do instead

If OD-1 is rejected, the operative path is the readiness decision's Path 1:
record U1-B, defer Pilot 2, and resolve the blockers (G3/B7 and the training
contract) before returning to the pilot. That path requires no new pilot design
and no scope reduction; it simply keeps the stage closed.

---

## 11. Proposed implementation sequence (for pricing only)

Listed so the owner can see the dependency order. None of it is performed here.

| Step | Deliverable | Acceptance test | Depends on |
|---|---|---|---|
| **P2C.1** | Owner record and protocol amendment | record validates structurally; scope matches the §2.2 grid field-for-field | OD-1, OD-2, OD-3, OD-4 |
| **P2C.2** | Stage scope in `campaign/protocol.py` | a changed grid cannot widen the exemption; non-pilot2 stages still refuse | P2C.1 |
| **P2C.3** | `stages/pilot2_runner.py` | one synthetic 32-node episode per arm round-trips through the store; A′ comparison runs in-process | P2C.2 |
| **P2C.4** | Readout provisioning | a loaded artifact re-verifies (manifest, SHA-256, shapes, digests, F/Fβ pair) for pilot seeds | OD-3 |
| **P2C.5** | Certification evaluator | implements §5 and §6 predicates over stored rows; emits `pass` / `fail` / `not_evaluable` per claim | P2C.3 |
| **P2C.6** | Preflight | memory ≥ 4.0 GiB; 7 input hashes; 3 config hashes; results path free; no graph construction | P2C.4 |
| **P2C.7** | Run and report | 45 episodes + 9 floor replays stored; every §6.1 claim evaluated; §2.4 prohibitions present verbatim | P2C.6 |

---

## 12. Statement of what remains true regardless

1. REV4 is unmodified and still authorises no execution.
2. D1 and D2 are unmodified. D2's scope still excludes Pilot 2, training and the
   campaign.
3. C1–C4, H1–H3, α, Holm m = 4, SEI = 100, N = 16/10, K = 10 and the exact
   sign-flip test are unchanged.
4. `design.n_seeds_selected` remains `null`.
5. The G3 deviation remains `deviation_recorded` with `gate_weakened = false`.
6. The 4.0 GiB memory gate remains in force and unwaived.
7. The campaign, training and C/D/C′ remain blocked.
8. No frozen parameter, configuration value, source file or result has been
   changed by this proposal, and none may be changed by adopting it without a
   further explicit authorisation.

---

## Appendix A — Source register

| Source | Role | Hash / locator |
|---|---|---|
| `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | protocol | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`, 1,915 lines |
| `reports/phase_8_owner_approvals/D1.json` | approval | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| `reports/phase_8_owner_approvals/D2.json` | decision | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |
| `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` | Pilot 1 results; §6, §7, §8 | — |
| `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` | bottleneck chain; §10–§13 | — |
| `reports/PHASE_8_PILOT2_READINESS_DECISION.md` | readiness; §2.4, §3.2, §4, §6.3 | — |
| `experiments/phase_8/stages/pilot2.py` | current implementation | `PILOT2_ARMS`, `pilot2_readiness`, `_identity_check`, `_constant_action_check`, `_u7_indication`, `evaluate_dispersion` |
| `experiments/phase_8/campaign/protocol.py` | authorization | `PILOT1_G3_SCOPE`, `g3_applicability`, `stage_authorization` |
| `experiments/phase_8/registry.py` | contrasts | `CONFIRMATORY_CONTRASTS` |
| `experiments/phase_8/training/loader.py` | artifact contract | loader rejects undeclared seeds at lines 101–104 |
| `experiments/phase_8/training/gate.py` | training gate | `assert_training_authorized` always raises |
| `readout/trainer.py` | REINFORCE | plain SGD, no weight decay (lines 80–82, 126–138) |
| `readout/linear.py` | `BiasOnlyReadout` | forward does not read features (lines 144–171) |
| `controls/f_beta.py` | Fβ | `assert_state_independent`, trainable names `["bias"]` |
| `conditions/f_readout.py` | F | training/evaluation role separation |
| `conditions/execute.py` | episodes | `neural_episode`, `floor_episode` |
| `configs/phase_8/campaign.yaml` | design constants | `n_seeds_selected: null`, `fallback_max_paired_sd: 112.87`, seeds |

## Appendix B — Glossary

| Term | Meaning in this document |
|---|---|
| certification | evidence that the machinery behaves as specified; never evidence for a hypothesis |
| structural zero | a difference that is exactly zero by the construction of the model |
| degenerate comparison | an estimable difference that cannot test the claim its name asserts |
| not evaluable | a required quantity or predicate cannot be produced; never `pass` |
| floor | the measured substrate-free constant-`NO_ACTION` baseline |
| behavioural constancy | one action per episode with feature weights that did not move |
| parameter bias-only | trainable set is exactly the four output biases (Fβ only) |

## Appendix C — Objective coverage

| Requested objective | Section |
|---|---|
| 1. Define exactly what the revised Pilot 2 establishes | §2.1, §2.3 (and §2.4 for what it does not) |
| 2. Identify which conditions and controls remain meaningful | §4.1, §4.2, §4.3 |
| 3. Identify degenerate comparisons and exclude them | §1.5, §3.4, §3.7 |
| 4. Define how F and Fβ bias-only behaviour is evaluated | §1.3, §5.1–§5.5 |
| 5. Declare `σ_max` not evaluable for U7 | §3.5 |
| 6. Preserve the original C1–C4 hypotheses unchanged | §3.6, §12.3 |
| 7. Separate certification evidence from confirmatory evidence | §2.6 |
| 8. Identify required operational work | §7 (P2-G, P2-A, artifacts, runner, gates), §11 |
| Required section: proposed experimental scope | §2 |
| Required section: mathematical/statistical definitions | §3 |
| Required section: conditions and controls | §4 |
| Required section: acceptance criteria | §6 |
| Required section: execution requirements | §7 |
| Required section: scientific limitations | §9 |
| Required section: exact differences from REV4 | §8 |
| Required section: owner decisions required | §10 |
