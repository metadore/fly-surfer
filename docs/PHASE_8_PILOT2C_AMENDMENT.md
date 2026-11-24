# Phase 8 — Formal Protocol Amendment: Pilot 2-C

**Document id:** `PHASE_8_PILOT2C_AMENDMENT`
**Adopted by:** owner decision record **D3** (2026-11-20)
**Amends:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`, §10.8 only
**REV4 status:** unmodified. Its SHA-256 remains
`e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` and its
closing sentence still reads "This document authorises no execution."

---

## A0. Scope of this amendment

This amendment changes **one** thing in REV4: the content of the Pilot 2 stage
defined in §10.8. It replaces the paired-dispersion pilot with a **floor and
identity certification experiment**, designated **Pilot 2-C**.

It changes no condition, no parameter, no contrast, no statistical constant, no
campaign requirement and no confirmatory analysis. Section A2 lists, item by
item, everything that is retained verbatim. Section A3 lists, item by item,
everything that changes.

This amendment is recognised by the implementation **only** when all of the
following hold at once:

1. REV4 is present and its SHA-256 equals the certified freeze above;
2. owner approval record D1 is present, valid and bound to that same hash;
3. owner decision record D3 is present, valid, bound to the SHA-256 of **this
   file**, and declares exactly the scope in §A4;
4. the requested grid matches §A4 field for field.

If any of the four fails, the Pilot 2-C stage refuses. Nothing in this
amendment is inherited by the training stage, the confirmatory campaign or any
other pilot.

---

## A1. Why the pilot changes

Three recorded facts drive the change. None of them is new evidence about the
fly; all three are facts about the experiment as built.

**F1 — Pilot 1 is operationally complete and motor-null.** The authorised Pilot
1 run executed 9 of 9 planned A episodes and persisted 9 valid rows. Every
episode recorded 0 motor spikes, executed `NO_ACTION` on every decision and
terminated by collision. This is an observation about the frozen substrate and
the fixed decoder as built; it is not evidence that the animal cannot act, and
it is not a defect to be repaired by changing a parameter.

**F2 — the original Pilot 2 grid cannot be run at the required standard.**
REV4 §10.8 requires C and C′ on the pilot seeds. C and C′ run only on a
certified random graph (R18), and certification covers campaign seeds 1–16
only (P2-G). A campaign graph may not be substituted for a pilot graph, and no
new randomisation may be built while the G3 §9.3 deviation (B7) is unresolved.
The C and C′ legs of §10.8 are therefore unavailable, not merely inconvenient.

**F3 — the original Pilot 2 output is not evaluable.** REV4's Pilot 2 exists to
estimate the paired dispersion of C1–C4 so that U7 can select N. With C absent,
C3 (`A − C`) has no definition; with C and D absent, C2 (`B − A`) is a
structural zero; with C and D absent, C1 (`F − A`) and C4 (`F − Fβ`) can be
computed but are degenerate on a motor-silent substrate. A three-seed pilot
cannot in any case distinguish the predeclared N = 16 from values above it.
`sigma_max` is therefore **not evaluable**, and U7 remains open.

A pilot that promises a dispersion estimate it cannot produce would be worse
than no pilot. Pilot 2-C instead certifies the properties the campaign will
depend on, and states plainly which quantities it does not estimate.

---

## A2. Retained unchanged from REV4

Everything in this section is unchanged and is asserted by the implementation
that this amendment authorises.

| Item | REV4 location | Retained value |
|---|---|---|
| Confirmatory hypotheses | §5.3 | H1, H2, H3 unchanged in wording and direction |
| Contrasts | §5.3, §3.6.2 | C1 = F − A, C2 = B − A, C3 = A − C, C4 = F − Fβ |
| Family-wise error | §7.5, U14 | Holm over m = 4 (C1–C4) and, as the declared variant, m = 3 (C1–C3) |
| Significance level | Appendix C | α = 0.05, two-sided |
| Smallest effect of interest | §5.2 | SEI = 100 updates |
| Primary sample size | §7.1, U7 | N = 16, predeclared |
| Predeclared fallback | §7.1 | N = 10, with the declared bound `fallback_max_paired_sd = 112.87` |
| Episodes per seed | Appendix C, U6 | K = 10 |
| Master seed | §6.3 | 20261116 |
| Seed derivation | §6.3, R18 | environment/network/learning/structure streams unchanged |
| Conditions A–F, E-full | §3 | declarations unchanged, including A′/C′ at η = 0 |
| Randomisation | §3.7, §9.3 | unchanged; no rule is relaxed |
| Memory gate | §9.3 | free physical memory ≥ 4.00 GB, not rounded down |
| Frozen neural, sensory, decoder and plasticity constants | Appendix C | unchanged |
| Frozen inputs | §8.5 | the seven declared files, unchanged |
| Campaign statistics family | §7.6–§7.8 | bootstrap 10,000, seed 20261116, SEI 100 |
| Episode-row and manifest schemas | §8.7 | unchanged; Pilot 2-C writes no new row field |
| Campaign requirements | §10.10 | unchanged; the campaign is not started by this amendment |

Pilot 2-C produces **no** campaign row, estimates **no** contrast, tests **no**
hypothesis, and contributes **no** data to the campaign dataset.

---

## A3. Complete list of changes from REV4

Each row is a distinct change. "REV4" gives the current clause; "Amended"
gives the behaviour that replaces it for Pilot 2 only.

| # | REV4 | Amended |
|---|---|---|
| **C-1** | §10.8 grid: 3 pilot seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes = 63 episodes | Grid: 3 pilot seeds × {A, B, F, Fβ, A′} × 3 episodes = **45 neural episodes**, plus **9 substrate-free floor replays** paired to the same environment seeds. C, C′ and D are absent. |
| **C-2** | §10.8 purpose: estimate paired dispersion of C1–C4 for the U7 sample-size decision | Purpose: certify the floor, the A′ identity, the Fβ control, the F readout, motor-silence recording, plasticity attribution, provenance and arm viability. `sigma_max` is declared not evaluable (§A6). |
| **C-3** | §10.8 stage identity: `pilot2`, step 10.8 | Stage identity `pilot2c`, step `10.8 (amended by D3)`. The original `pilot2` stage code path is left intact and remains refused. |
| **C-4** | §10.8 requires C for contrast C3 and for the C′ identity check | C and C′ are **excluded** from Pilot 2-C. No randomized graph is constructed, read or substituted. |
| **C-5** | §10.8 and §7.4 compute `sigma_max` and its one-sided upper confidence limit | Pilot 2-C computes neither. No dispersion estimate, no upper confidence limit and no U7 indication appear in its output. |
| **C-6** | §7.1/U7: the pilot informs the choice of N | U7 remains open. Pilot 2-C does **not** discharge U7, does **not** select N, and never writes `design.n_seeds_selected`. |
| **C-7** | §6.7: F and Fβ are trained for the campaign on campaign seeds | Pilot 2-C **never trains**. F and Fβ evaluation read pre-existing trained artifacts through the campaign factory's `TrainingArtifacts` provider. In-arm training, synthetic state and initialized state are refused in a campaign grid. |
| **C-8** | Implied: artifacts are keyed by campaign seed only | **A-2 loader contract amendment.** Trained artifacts may be keyed by the declared *pilot evaluation seeds* 9001–9003 without adding them to `seeds.campaign`. The training seed recorded inside each manifest must still be a declared `seeds.training` value, and the pilot-evaluation key must be disjoint from campaign and training seeds. |
| **C-9** | §3.6.2 floor exists as an analysis reference only | Nine floor replays are materialised as stored rows: for each pilot seed and each of its 3 paired environment seeds, one constant-`NO_ACTION` replay on the substrate-free game path. |
| **C-10** | §3.8.6: A′ identity is checked on stored fields where in-process state is unavailable | The A′ ≡ A identity is checked **in process** on all P1–P19 for all 9 pairs, and the comparison report is stored with each A′ row. The store-level reduced comparison is retained as a secondary check, never as a substitute. |
| **C-11** | §3.6.1: the per-decision motor block is recorded | Unchanged in substance; Pilot 2-C additionally requires that motor silence be *counted and reported* for all five neural arms so that F1 is measured rather than assumed. |
| **C-12** | §6.10: all Phase 8 writes stay under the results root | Pilot 2-C writes under `experiments/results/phase_8/pilot2c/` only, and its manifest records `design.stage_purpose = "floor_and_identity_certification"`. No episode-row field is added. |
| **C-13** | §10.8 outputs: dispersion estimates and an indication | Outputs: certification findings **P2C-1 … P2C-8** (§A5). Any quantity outside those claims is reported as not evaluated. |
| **C-14** | §10.8 inherits the campaign-wide gate, under which B7 blocks every stage | Pilot 2-C is authorised by D3 for the exact grid in §A4 only. Because that grid constructs and uses no randomized graph, the G3 §9.3 deviation does not apply to it. The deviation is **not accepted and not weakened**; the graph certification is unchanged; every other stage still refuses. |
| **C-15** | §10.5/§10.9 training declarations B3–B6 are owner decisions | Unchanged. Pilot 2-C may not invent a campaign-to-training pairing, a training-episode environment-seed schedule, a checkpoint cadence/retention/format, or an RNG/optimizer restoration policy. With no artifacts present, Pilot 2-C **refuses** (§A7). |
| **C-16** | §7 statistical analysis plan applies to pilot output | No part of the confirmatory analysis plan is applied to Pilot 2-C. α, Holm, bootstrap and SEI are retained unchanged for the campaign and are **unused** here. |
| **C-17** | The document text is the only authorisation artefact | A new hash-bound owner decision record, **D3**, is required. It is external to REV4 and is recognised only when bound to this amendment's SHA-256. D1 and D2 stay unchanged and keep their current meanings. |
| **C-18** | Stage authorisation is campaign-wide | A stage-specific authorisation branch is added for `pilot2c`, matching the existing `pilot1` pattern. `assert_campaign_authorized` is unchanged and still refuses, and `assert_training_authorized` is unchanged and still refuses. |

---

## A4. Pilot 2-C scope (exact)

```
stage                     pilot2c
step                      10.8 (amended)
neural arms               A, B, F, F_beta, A_prime
floor arm                 floor
seeds                     9001, 9002, 9003
episodes per seed per arm 3
neural episodes           5 arms x 3 seeds x 3 episodes = 45
floor replays             1 floor x 3 seeds x 3 episodes = 9
total stored rows         54
randomized graph          none constructed, none read, none substituted
trained artifacts         F and F_beta only; read-only; never created here
contrast estimates        none
hypothesis tests          none
N selected                none
campaign rows produced    none
results root              experiments/results/phase_8/pilot2c
stage purpose             floor_and_identity_certification
```

The environment seed of every row is `environment_seed(master_seed, seed,
episode)` from the unchanged §6.3 derivation, so each floor replay is paired
with the five neural episodes that share its `(seed, episode)`.

### A4.1 Prohibitions

Pilot 2-C may not, under any configuration:

1. add C, C′ or D;
2. construct, read or substitute a randomized graph;
3. accept, resolve or weaken the G3 §9.3 deviation;
4. estimate C1–C4, H1–H3, paired dispersion or `sigma_max`;
5. discharge U7 or set `design.n_seeds_selected`;
6. create, train, retrain or substitute a model artifact;
7. persist synthetic or initialized state in a pilot row;
8. write a row under the campaign results root;
9. merge a pilot row into the campaign dataset;
10. change an episode-row field, a frozen parameter or a statistical constant;
11. modify REV4, D1 or D2;
12. derive its own authorisation from its own output.

---

## A5. Certification claims

Pilot 2-C supports exactly eight claims. A claim that is not satisfied is
reported as failed, with the evidence that failed; it is never softened into a
partial pass.

**P2C-1 — floor execution.** The nine substrate-free replays execute, each
produces a schema-valid row, each executes `NO_ACTION` on every decision, and
none reads a spike or owns a weight fingerprint.

**P2C-2 — A′ identity.** For all nine `(seed, episode)` pairs, A′ reproduces A
in process on P1–P19 with no tolerance, at η = 0, with a zero weight delta and
no reset inside the episode.

**P2C-3 — Fβ constancy.** Fβ's feature weights are exactly zero, its trainable
parameter set is exactly `["bias"]`, its logits are identical for the zero and
saturated feature vectors, and every Fβ episode selects one action on every
decision.

**P2C-4 — F behaviour.** F's readout is state-dependent (its feature weights
are not all zero), evaluation leaves its weights unchanged from episode start
to episode end, and F is *not* required to be constant.

**P2C-5 — motor silence.** Every neural arm records a per-decision motor block
and a motor-spike count for every episode. The count is reported as measured;
zero is reported as zero and is not interpreted biologically.

**P2C-6 — plasticity attribution.** A′ reports a weight delta of exactly zero
with zero changed edges. B reports its eligibility-trace updates, the number of
eligible edges, the number of changed edges, and the maximum absolute applied
update, so a nonzero change can be attributed to the declared rule.

**P2C-7 — provenance.** Every row records the seven frozen-input hashes, the
three configuration hashes, the seed plan, the evidence kind and the manifest
stage purpose. Each F/Fβ row records its artifact's condition, evaluation seed,
training seed, parameter digest and parameter-file SHA-256.

**P2C-8 — viability.** Every arm completes its nine planned episodes with
schema-valid rows and a recorded survival score. A missing or failed episode is
reported, never skipped and never retried with a different seed.

---

## A6. σ_max and U7

For the record, and so that no future reader mistakes absence for oversight:

- C3 = A − C is **undefined** because C is not in the grid;
- C2 = B − A is a **structural zero** on any substrate that produces no motor
  output, and F1 shows the recorded substrate does;
- C1 = F − A and C4 = F − Fβ are **estimable but degenerate** for the same
  reason;
- three seeds cannot distinguish N = 16 from any larger N; N = 16 is the
  predeclared default, so the decision rule has no remaining degree of freedom
  that this pilot could inform.

Pilot 2-C therefore reports the contrast statuses above and no dispersion
number. U7 is untouched.

---

## A7. Training dependency and the present blocker

F and Fβ are trained conditions (§3.6). Pilot 2-C evaluates **trained**
artifacts; it does not train them and will not run an untrained readout in
their place.

The artifact interface, the loader and its A-2 amendment are implemented. The
present repository state is:

- `experiments/results/phase_8/training/` **does not exist**;
- no `origin = "trained"` artifact exists for any condition or seed;
- the training stage refuses (`assert_training_authorized`), because
  `design.n_seeds_selected` is null (U7 open) and the training-operation
  decisions **B3–B6** are undeclared:

  - **B3** — the campaign-to-training seed pairing;
  - **B4** — the training-episode environment-seed schedule;
  - **B5** — the checkpoint cadence, retention and format;
  - **B6** — the sampler RNG and optimizer-moment checkpoint policy.

These are owner decisions. They are not inferred, defaulted or chosen here.
Until D3's scope is satisfied *and* valid F/Fβ artifacts exist *and* B3–B6 are
recorded, Pilot 2-C is **not executable**, and the implementation refuses with
the exact missing keys.

---

## A8. G3 / B7

`experiments/results/phase_8_random/campaign_seed_summary.json` still records
`compliance.status = "deviation_recorded"` and `gate_weakened: false`, with a
minimum observed free memory of 1.628 GB against the 4.00 GB gate.

Pilot 2-C changes none of that. Its grid contains no condition that requires a
random graph, and the implementation asserts that property before an episode is
built. D3 records only that, for this exact grid, the §9.3 gate has no subject:
there is no randomisation to certify and no certified graph to use. D3 sets
`accepts_g3_deviation: false` and `weakens_graph_certification: false`.

The G3 deviation remains open for every use of the certified graphs, and the
confirmatory campaign remains refused.

---

## A9. Authorisation model

| Gate | Pilot 2-C |
|---|---|
| B1 — REV4 §12 / U1–U18 approval | Satisfied by D1 (unchanged) |
| B2 — `n_seeds_selected` null | **Still open**; Pilot 2-C does not read or write it |
| B3–B6 — training declarations | **Still open**; Pilot 2-C does not invent them |
| B7 — G3 §9.3 deviation | Not applicable to this exact grid under D3; **still open everywhere else** |
| B8 — 4.00 GiB free memory | Enforced at run time; not waived |
| D3 — Pilot 2-C scope | Required, hash-bound to this file |
| Artifacts | Required, trained, verified, paired |

`assert_campaign_authorized` and `assert_training_authorized` are unchanged and
both still refuse. Only `assert_stage_authorized("pilot2c", plan=...)` can pass,
and only for the exact grid in §A4.

---

## A10. Invariants

1. REV4, D1 and D2 are byte-identical to their recorded hashes.
2. No frozen parameter, statistical constant or campaign configuration changes.
3. No historical result is modified.
4. No protected README or motor-baseline file is altered.
5. No randomized graph is generated.
6. No confirmatory campaign is run.
7. Pilot rows are never merged into the campaign dataset.
8. Every refusal is recorded with its exact blocker string.

---

## A11. What this amendment does not do

It does not authorise a campaign, a training run, a graph randomisation or any
Pilot 2-C episode. It does not discharge U7. It does not certify the G3 graphs.
It does not make the substrate motor-active. It does not claim that any model
learned anything. It defines what Pilot 2-C would establish, and the conditions
under which it may run.
