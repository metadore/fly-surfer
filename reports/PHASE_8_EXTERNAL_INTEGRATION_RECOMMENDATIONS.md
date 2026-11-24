# Phase 8 external-integration recommendations

Status: research recommendation, written 2026-11-20. **Reference-only.** This
document changes no gate definition, no condition, no control, no frozen
parameter, no learning rule, no threshold, and no graph. It adds no code to the
repository.

Companion documents:

- `docs/research/EXTERNAL_REPOSITORY_COMPARISON.md`
- `docs/research/FLYVERSE_CORE_COMPATIBILITY_AUDIT.md`
- `docs/research/EXTERNAL_NEURAL_MODEL_EQUATION_COMPARISON.md`

## Constraints in force (verbatim, unchanged)

- Do not modify REV4.
- Do not change frozen parameters, learning rules or thresholds.
- Do not replace FAFB/BANC with MaleCNS.
- Do not copy external code into the main repository yet.
- Do not install large dependencies or download large datasets.
- Do not run training or experimental campaigns.
- Do not perform Git operations.

REV4 remains SHA-256
`e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`,
1,915 lines, **NOT APPROVED, NOT EXECUTABLE**, with U1–U18 all PROPOSED. The
current gate status is tracked in `reports/PHASE_8_IMPLEMENTATION_STATUS.md`; a
recommendation here is not evidence that a gate is closed.

## Executive verdict

**No external repository should be merged, installed, vendored, or copied into
FLY-SURFER under these constraints.** None of the four implements FLY-SURFER's
neuron, weight law, sign policy, or Phase 5 learning rule, and every one of them
targets MaleCNS except flyverse (which also targets MaleCNS and merely *loads*
FAFB/BANC with a different downstream law). Adopting any of their equations
would change frozen dynamics and therefore the meaning of conditions A–F.

What *is* usable, without touching any frozen quantity, is **discipline and
framing**: flyverse's transmitter-coverage accounting, doomfly's provenance
hashing, and neurocraft's separation of neural decisions from scripted behaviour
plus its evidence-kind and exclusion rules. Those are **reporting patterns**
(class **A as a pattern**), adoptable in Phase 8 reports and analyses without a
code import.

The **one genuinely independent solver** among the four — the Brian2
implementation — solves the *Shiu* equations, not FLY-SURFER's, and cannot
currently validate FLY-SURFER's numbers (see the equation comparison, §5).

---

## PART E — per-gate recommendations (G1–G7)

Each subsection states: what the gate is; whether any external repository is a
usable reference; the exact external source file, if any; and the confound that
makes adoption unsafe.

### G1 — Incremental plastic stepper

*Gate:* provide `advance_to_step` / `step_index` / `weight_fingerprint`
semantics so B and D can run one step at a time through the **actual** plastic
pathway (`plasticity/live_stepper.py`, `plastic_simulator.py`).

*External references:*

- **doomfly** `doom_learning/brain.py` — `MemoryBrain` keeps explicit per-step
  `eligibility`, `eligibility_last`, `modulation`, `modulation_last`,
  per-edge `baseline_plastic`, and checkpoint provenance hashes, and exposes
  `configuration_signature()`. This is a clean example of **per-step state plus
  provenance**, which is exactly the shape G1 needs (`weight_fingerprint` is the
  analogue of `configuration_signature()`).
- **neurocraft** `neurocraft_neural/model.py` — `NeuralState` / `NeuralStepRecord`
  hash chains are an example of **per-step identity chaining**.

*Recommendation:* adopt **the pattern only** — a per-step state record plus a
weight fingerprint that is hashed into the episode identity. Do **not** import
doomfly's learning rule: its own parameter string declares it
`"LTD-only; no consolidation, recovery, extinction or prediction-error
circuit"`, and it is per-neuron eligibility, not FLY-SURFER's per-edge
three-factor rule. Importing it would replace the Phase 5 rule, which is frozen.

*Required tests (only if a future revision adopts anything):* the REV4 §10.6
tests already governing G1 remain authoritative — A′ ≡ A and C′ ≡ C with **zero
tolerance**, `eta = 0` executed through the real rule, weight-delta array exactly
zero, and a mismatch is a hard stop that marks B/D INVALID. Any borrowed state
record must not alter those outcomes.

*Confound:* a foreign stepper that changes float dtype, accumulation order, or
clamp bookkeeping would break the `eta = 0` bit-identity contract, which is the
entire point of A′/C′. Under the freeze, the correct action is **none**.

*Classification:* **B** (doomfly state record), **B** (neurocraft hash chain),
both as patterns; the doomfly *rule* is **E**.

### G2 — Live readout

*Gate:* route condition F's motor features through a trained readout instead of
the fixed-threshold `GameActionDecoder`, and keep Fβ genuinely state-independent.

*External references:*

- **neurocraft** `controller-runtime/src/neurocraft_controller/program_policy.py`
  — the clearest published statement of the boundary Phase 8 must keep:
  "Everything in this module is a hand-chosen engineering mapping. It is not the
  fly deciding, it is not anatomy, and no constant here is derived from any
  measurement of fly behaviour." It also distinguishes a **declaration hash**
  from a behaviour hash: "`policy_hash` is a DECLARATION hash … nothing
  machine-checks that `DNA01_TURN_FORMULA` describes what
  `readout_values_from_step` computes."

*Recommendation:* adopt **the framing and the check** — Phase 8's readout
identity should be described as a *declaration* hash, and any claim that the
readout uses motor information must rest on the E1–E4 tests, not on the hash.
Do **not** import neurocraft's policy: it is a set of hand-chosen scripted body
programs (CRUISE / ESCAPE_JUMP) selecting movements, which is structurally the
opposite of Phase 8's F, a **trained linear readout over motor-population
features**.

*Required tests:* REV4 §10.5 already fixes them — connectome fingerprint
unchanged before/after; trainable-parameter set == readout parameters only;
`motor_activity` present on 100% of decisions; Fβ feature vector identically
zero; E4 with a 0/0 denominator reported **not evaluable**, never pass.

*Confound:* importing a scripted-program policy would convert F from "a learner
over motor features" into "a hand-chosen controller", which would invalidate
C4 (`F − Fβ`) as a test of state-dependence. Under the freeze, the only safe
adoption is the **wording and the declaration-vs-behaviour caveat**.

*Classification:* **A as a framing pattern** (neurocraft), no code.

### G3 — Degree-preserving random graph null

*Gate:* a degree-and-sign-preserving random graph at BANC t5 scale with valid
CSR invariants, rewired fraction ≥ 0.99, neighbourhood overlap ≤ 0.01, exact
degree, exact weight multiset and **per-source weight profile (R9b)**.

*External references:*

- **neurocraft** `neural-runtime/model.py` — `TopologyOverlay` is a
  **directed-degree-preserving pairwise swap that preserves the self-edge
  count**. This is the same *family* as G3 and is a useful independent statement
  that degree-preserving nulls are standard.
- **flyverse** has **no** degree-preserving null; it documents sign ablations
  only.
- **neurocraft** `docs/SCIENTIFIC_CLAIMS.md` also states the caution Phase 8
  already honours: "Weight shuffling … is not rewiring. One shuffle is not a null
  distribution."

*Recommendation:* **G3 as implemented is already stricter than any external
null** — it preserves the per-source outgoing weight multiset (R9b), which
neurocraft's overlay does not state. Use neurocraft only as a **B-class
cross-check** that the null family is standard, and keep the existing 16-seed
certified construction (`experiments/phase_8_random/target_exchange.py`,
`certification.py`).

*Required tests:* unchanged — the R1–R18 reporter and per-graph certificates
already required by REV4 §10.4. The recorded memory deviation (16/16 seeds
certified at 1.63–2.93 GB, below the 4 GB gate, logged as `deviation_recorded`)
stands as-is.

*Confound:* a weaker external null (degree-only, or single-shuffle) would make
condition C easier to distinguish from A and would inflate the apparent
biological contribution (C3). Adopting it would weaken the experiment.

*Classification:* **B** (neurocraft `TopologyOverlay`, conceptual only).

### G4 — Matched conventional-learner baseline

*Gate:* a matched conventional learner for condition E, matched to the neural
arms' sensors, actuators and feature interface, with E-matched and E-full
variants and training/evaluation seed separation.

*External references:*

- **doomfly** — its learning is a declared **LTD-only heuristic**, not a
  conventional baseline, and its own review states the base run makes no
  learning claim. **E** for this purpose.
- **neurocraft** — **forbids** learning entirely (ADR 0002 "Forbidden
  learning"). **D** for this purpose.
- **flyverse** / **male-cns-fly-brain** — no matched conventional learner.

*Recommendation:* **no external repository provides a usable matched
conventional learner for this interface.** The reason G4 is hard is specific to
FLY-SURFER: the Phase 5F perceptron was `privileged: true`,
`matched_control: false`, and Gymnasium / Stable-Baselines3 are absent by
design. Keep the REV4 design (E-matched 7-feature vs E-full 14-feature
REINFORCE, `readout/linear.py`, `experiments/phase_8/training/`). Do not
substitute doomfly's LTD rule or neurocraft's forbidden-learning stance.

*Required tests:* REV4 §10.9 — training seeds disjoint from evaluation seeds and
asserted; no privileged input; E-matched beats the substrate-free floor on its
own training distribution **before** the campaign (otherwise the §0 gate).

*Confound:* importing a different learner would make E a test of *that learner*
against A–D, not of "a matched conventional learner on the same interface", and
would break C1/E2 interpretation.

*Classification:* **D/E** — no usable reference.

### G5 — Multi-episode, multi-seed campaign harness

*Gate:* per-episode JSONL, error capture, artifact manifest, resume, versioned
schema + validator, over N × K.

*External references:*

- **flyverse** `backends/common.py` — `finish()` writes a manifest with SHA-256
  of the source files. Directly analogous to the campaign manifest discipline.
- **doomfly** `doom_learning/brain.py` — checkpoint provenance hashes plus
  `configuration_signature()`.
- **neurocraft** `NeuralState` / `NeuralStepRecord` hash chains.

*Recommendation:* adopt **the manifest/provenance pattern** in
`experiments/phase_8/campaign/manifest.py` and `store.py` reporting. No code
import; these files already implement the required behaviour (append-only JSONL,
resume, schema validator).

*Required tests:* REV4 §10.1 — validator rejects a malformed row; a 1-update
dummy episode round-trips; resume is idempotent on
`(condition, seed, episode)`; no result directory is overwritten.

*Confound:* none scientific. The only risk is that a borrowed manifest format
could omit a field the analyser expects; the schema validator already guards
this.

*Classification:* **A as a pattern** (flyverse manifest, doomfly provenance).

### G6 — Phase 8 artifact reader / analysis layer

*Gate:* `analyse_phase_8.py` reproducing every §7 number from the JSONL, exact
sign-flip at the actual N, Holm m = 4/3, bootstrap, effect sizes, floor
decomposition, F/Fβ/A decomposition, E1–E5 checklist.

*External references:*

- **neurocraft** `docs/SCIENTIFIC_CLAIMS.md` — five separate evidence kinds and
  the rules "a failed or missed stimulus is an exclusion, not a zero neural
  response" and "no-input activity can remain zero while scripted baseline
  CRUISE moves the body". These are the same integrity rules Phase 8's analysis
  must obey.
- **flyverse** `docs/NT_INTEGRATION.md` — the **coverage accounting** pattern:
  report how many rows and how much |weight| each choice changes (e.g. "2.2% of
  synapses … 1.7% of presynaptic neurons"; "29.7% of edges / 25.7% of |W|").

*Recommendation:* adopt **both patterns**: structure the G6 report by
neurocraft's five evidence kinds, and add a flyverse-style coverage line to the
G3/G4 documentation (how much of the BANC graph and weight mass each sign and
null choice excludes). No code import; no external threshold enters the
analysis.

*Required tests:* REV4 §10.11 — reproduce every §7 number from the JSONL; no
hand-entered values; thresholds recomputed at the actual complete-pair N;
zero/missing-pair rules applied as declared.

*Confound:* importing an external significance threshold or estimator would
change the analysis; the analysis must use FLY-SURFER's own
`information/` estimators and the REV4-declared statistics only.

*Classification:* **A as a reporting pattern** (neurocraft evidence kinds,
flyverse coverage accounting).

### G7 — Viability check

*Gate:* verify that any neural condition can emit a non-`NO_ACTION` action, per
U1's five gate cases (U1-A … U1-E), without tuning, and never mark blocked work
as complete.

*External references:* **none of the four** implements a viability gate.
doomfly's `NeuralControls` (`attack = any(MN9 spike)`) is a trivial
"does-a-motor-spike-happen" analogue, not a gate, and its action mapping is
Doom-specific.

*Recommendation:* **no external reference.** Keep `evaluation/viability.py`
read-only against the Phase 7 artifact and the Phase 8 JSONL, implementing the
five U1 cases exactly. Note, consistent with E3, that **a non-`NO_ACTION` action
is necessary but not sufficient** for a neural-learning claim (E3/E4/E5 still
govern).

*Required tests:* REV4 §10.13 — implements U1's five gate cases without tuning;
never marks blocked work as complete.

*Confound:* none external; the risk is internal (treating a single action as a
learning result), which the E1–E5 bar already blocks.

*Classification:* **D** — no external reference exists.

---

## Integration classification of every identified component

Classes: **A** directly reusable (compatible licence and validated semantics);
**B** useful independent reference; **C** requires substantial adaptation;
**D** incompatible with architecture/datasets; **E** not scientifically
justified. "A (pattern)" means adoptable as a **reporting practice**, not as
code.

| Component | Repo | Exact source file(s) | Class | Phase 8 gate | Adoptable under freeze? |
|---|---|---|---|---|---|
| FAFB v783 pair/threshold adapter | flyverse | `flyverse/backends/fafb.py`, `backends/common.py` | B | G6 (cross-check) | No code; reference only |
| BANC v888 adapter + motor subclasses | flyverse | `flyverse/backends/banc.py` | B | G3/G4 (pool cross-check) | No code; reference only |
| Cross-release synapse-yield ratio | flyverse | `docs/NT_INTEGRATION.md` | C | G6 (corroboration) | Record only |
| Anti-runaway normalisation (cap/fan-in/path/same-type) | flyverse | `flyverse/brain.py` (`_shaped_weights`) | B/C | — (diagnosis only) | No — changes frozen dynamics |
| Transmitter-coverage accounting | flyverse | `docs/NT_INTEGRATION.md` | **A (pattern)** | G6 | Yes, in reports |
| Manifest with source SHA-256 | flyverse | `backends/common.py` (`finish()`) | **A (pattern)** | G5 | Yes, in reports |
| Receptor tier/gain table | flyverse | `connectome.py` (`ReceptorSigns`) | C | — | No — changes sign matrix |
| numba all-edge LIF kernel | doomfly | `doom/engine.py` | D | — | No — MaleCNS + different constants |
| Joystick readout interface | doomfly | `doom/engine.py` (`NeuralControls`) | B | G7 (analogue) | No code |
| Per-step state + checkpoint provenance | doomfly | `doom_learning/brain.py` | **A (pattern)** | G1, G5 | Yes, as pattern |
| LTD-only eligibility rule | doomfly | `doom_learning/brain.py` | E | — | No — not the Phase 5 rule |
| Neural/scripted-body separation + declaration-hash caveat | neurocraft | `controller-runtime/.../program_policy.py` | **A (pattern)** | G2, G6 | Yes, as framing |
| Five evidence kinds + exclusion rules | neurocraft | `docs/SCIENTIFIC_CLAIMS.md` | **A (pattern)** | G6 | Yes, in reports |
| Degree-preserving `TopologyOverlay` | neurocraft | `neural-runtime/.../model.py` | B | G3 (family cross-check) | No code; G3 is stricter |
| Leaky-rate `tanh` dynamics | neurocraft | `neural-runtime/.../model.py`, ADR 0002 | D | — | No — different neuron |
| Brian2 LIF solver | male-cns-fly-brain | `shiu_model/model.py`, `brian_escape.py` | B | — (verification only) | No — Shiu equations |
| Shiu numpy LIF + escape probe | male-cns-fly-brain | `lif_model.py` | B | — | No — different constants |
| Root licence for wrapper scripts | male-cns-fly-brain | (none) | D | — | No — unlicensed |

## Required tests for any *future* adoption

These apply only if a later, separately authorised task decides to adopt a
component. Under the present constraints they are **not** executed.

1. **Identity preservation.** Any adopted state record, manifest field, or
   stepper must leave A′ ≡ A and C′ ≡ C bit-identical (`eta = 0` through the
   real rule; weight-delta array exactly zero; zero tolerance). A mismatch is a
   hard stop marking B/D INVALID.
2. **Frozen-fingerprint invariance.** The Phase 7 fingerprint `cca811f3…b2fb`
   (condition A, seed 42, 213 updates) and the fixed-weight hash
   `4923f0cd…d945d5` must be reproduced unchanged by any adopted code path.
3. **Schema conformance.** Any adopted manifest or JSONL field must pass the
   `experiments/phase_8/schema.py` validator, and a 1-update dummy episode must
   round-trip.
4. **Readout isolation.** Any adopted readout framing must keep the trainable
   parameter set == readout parameters only; Fβ feature vector identically zero;
   `motor_activity` present on 100% of decisions.
5. **No new thresholds.** Any adopted report structure must read only REV4's
   declared thresholds and FLY-SURFER's own `information/` estimators; no
   external significance level, estimator, or normalisation may enter the
   analysis.
6. **Licence gate.** No component from `male-cns-fly-brain` may be reused except
   `shiu_model/` (MIT); the wrapper scripts have no root licence. Any flyverse,
   doomfly, or neurocraft reuse must carry their MIT notice.

## Scientific confounds of adoption

| Candidate | Confound | Effect on conditions A–F |
|---|---|---|
| flyverse weight law / normalisation | Changes absolute and relative edge strengths | Changes A, B, C, D inputs; invalidates the frozen REV4 parameters |
| flyverse sign table | Glutamate −1, monoamines 0 | Changes which edges propagate at all; changes C3 |
| flyverse receptor/slow model | Adds a second timescale and per-type signs | Changes dynamics A–F; not in FLY-SURFER's model |
| neurocraft scripted-program policy | Replaces a learner with a hand-chosen controller | Invalidates C4 (`F − Fβ`) as a state-dependence test |
| neurocraft leaky-rate dynamics | Different neuron (no spike, tanh) | Replaces the Phase 2–8 substrate entirely |
| doomfly LTD eligibility | Different learning rule (per-neuron, LTD-only) | Invalidates C2 (`B − A`) and A′/C′ identity |
| doomfly numba kernel | MaleCNS all-edge, Shiu constants | Not the FAFB/BANC substrate; changes everything |
| any "one shuffle / one graph" null | Weaker than G3's R1–R18 | Inflates C3 (biological vs random) |
| external significance threshold | Different test than the exact sign-flip | Changes E1/E2/C4 decisions |

## FINAL REQUIREMENT — per-component reference recommendation

| Phase 8 component | Recommended reference | Repository | Class | Why |
|---|---|---|---|---|
| **G1** incremental plastic stepper | Per-step state + provenance **pattern** | doomfly `doom_learning/brain.py`; neurocraft `NeuralStepRecord` | B (pattern) | Clean per-step state and identity chaining; adopt pattern, not rule |
| **G2** live readout | Declaration-vs-behaviour framing | neurocraft `program_policy.py` | A (pattern) | Best statement of the neural/scripted boundary; framing only |
| **G3** degree-preserving null | None needed; neurocraft as family cross-check | neurocraft `TopologyOverlay` | B | G3 already stricter (R9b); neurocraft only confirms the family |
| **G4** matched conventional learner | **None** | — | D/E | No external repo provides a matched learner on this interface |
| **G5** campaign harness | Manifest/provenance **pattern** | flyverse `backends/common.py`; doomfly `brain.py` | A (pattern) | Same SHA-256 manifest discipline already required |
| **G6** analysis layer | Evidence kinds + coverage accounting **pattern** | neurocraft `SCIENTIFIC_CLAIMS.md`; flyverse `NT_INTEGRATION.md` | A (pattern) | Matches FLY-SURFER's integrity rules; coverage accounting improves G3/G4 reporting |
| **G7** viability check | **None** | — | D | No external viability gate exists |

**Single-sentence answer:** *Use `flyverse-core` as the reference for dataset
loading and transmitter-coverage accounting, `neurocraft-fly-public` as the
reference for separating neural decisions from scripted behaviour and for
evidence-kind reporting, `doomfly` as the reference for per-step provenance
discipline, and `male-cns-fly-brain` only as a future, separately authorised
numerical-verification reference — and adopt none of their code or equations
while REV4 is frozen.*

## Reflection against the project's scientific-integrity rules

- **No overclaiming.** Every external benefit is labelled a **reporting
  pattern** or a **reference**, never a validated improvement. Nothing was run.
- **Limitations stated.** The Brian2 solver validates the Shiu equations, not
  FLY-SURFER's; `male-cns-fly-brain` has no root licence; test trees were not
  inspected; one doomfly file was missing.
- **Observation vs interpretation separated.** Quoted constants and counts are
  observations; classifications and recommendations are interpretation and are
  marked as such.
- **Failures recorded, not hidden.** The Phase 7 zero-motor-spike failure, the
  G3 memory deviation, and the Phase 6 frozen negative result remain as they
  were; no external recommendation softens them.
- **Existing decisions preserved.** No file inside the repository is changed
  except the four research deliverables themselves; REV4, the frozen parameters,
  the graphs, the learning rule, the thresholds, and the Git state are
  untouched.
