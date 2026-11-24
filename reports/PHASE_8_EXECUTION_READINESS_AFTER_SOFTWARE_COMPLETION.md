# Phase 8 execution readiness after software completion

**Date:** 2026-11-20
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines)
**Protocol approval status:** U1–U18 **PROPOSED — not approved** (`docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` §12, §12.1). No execution is authorised.
**Campaign configuration:** `configs/phase_8/campaign.yaml`, SHA-256 `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19` (93 lines), unchanged; `design.n_seeds_selected: null`.
**Owner decision package:** `docs/PHASE_8_OWNER_DECISION_PACKAGE.md`, SHA-256 `5d6ecca8accaf8e54bdbfea08c66e08953e485e604c1c0f8e0d3db36a246e9cb` (1,173 lines).

**Verdict: software complete, execution not authorised, not ready to execute.**

This report keeps three things apart that are easy to conflate:

1. **Software completion** — the code exists, is callable, and its focused tests pass.
2. **Experimental readiness** — the protocol, design, artifacts, seeds and environment all permit a run.
3. **Experimental evidence** — data produced by an authorised run.

Phase 8 has (1). It does not have (2), and it therefore has none of (3). No episode, training run,
pilot or campaign has been executed at any point in Phase 8. `experiments/results/phase_8/` does not
exist.

---

## 1. What this report is and is not

This is a **status record**, produced read-only by inspection and by running the stages' own
non-executing commands (`--describe`, `--status`). It reports what the code says about itself.

It does **not**:

- approve, recommend approval of, or pre-fill any U1–U18 item;
- select N, select a Holm family size, or resolve any pilot-seed or G3 question;
- alter REV4, the campaign configuration, any graph artifact, or any implementation file;
- create experimental results.

Where a source document disagrees with another, the disagreement is reported in §10, not resolved.

---

## 2. Software components completed

The previously missing executable stages are now present. `experiments/phase_8/stages/` contains:

| Module | REV4 step | Role |
|---|---|---|
| `common.py` | — | shared authorisation, readiness and JSON-emission helpers |
| `pilot1.py` | §10.3 | Pilot 1 plan, readiness and refusal gate |
| `training_stage.py` | §10.5 / §10.9 | F/Fβ and E/E-full training orchestration and status |
| `composition.py` | §10.10 | campaign composition root (`start` / `resume`) |
| `pilot2.py` | §10.8 | Pilot 2 plan, readiness and refusal gate |
| `information.py` | §10.11 | Phase 8 information-analysis adapter |
| `reporting.py` | §10.12 | report generation and freeze stage |
| `run_stage.py` | — | router over the six stages (`--list`, then per-stage argv) |

`run_stage.py:36-43` is the stage map; it adds no default, no gate and no behaviour of its own
(`run_stage.py:1-20`). Each stage keeps the first word on whether it may run.

The earlier packages are unchanged in role and remain present: the harness (`config`, `seeds`,
`runner`, `registry`, `store`, `manifest`), the `conditions/` and `controls/` packages, the G5
assembly package (`campaign/factory.py`, `campaign/dispatcher.py`, `campaign/graphs.py`,
`campaign/protocol.py`, `campaign/status.py`, `run_campaign.py`), the G4 training package
(`experiments/phase_8/training/`), the G6 analysis pipeline (`analysis.py`, `analyse_phase_8.py`)
and the G7 viability check.

### 2.1 What each stage reports about itself today

Read directly from the stages on 2026-11-20:

- **Pilot 1 (`run_stage pilot1 --describe`)** — `stage: pilot1`, `rev4_step: 10.3`, plan is arm
  **A only**, seeds `[9001, 9002, 9003]`, 3 episodes per seed, 9 total entries, `estimates_contrasts:
  false`, `hypothesis_tests: []`, `merged_into_campaign: false`. Readiness block states
  `certified_graph_needed: false`, `design_decision_needed: false`,
  `trained_artifact_needed: false`. `executable: false`, `executed: false`.
  `authorized: false`, `document_authorises_execution: false`, blockers `B1`, `B7`, `B8`.
- **Training (`run_stage training --status`)** — `training_performed: false`,
  `artifacts_written: 0`. Four undeclared inputs reported: `B3` seed pairing, `B4` training-episode
  environment-seed schedule, `B5` checkpoint cadence/retention/format, `B6` RNG/optimizer state.
  The checkpoint declaration is explicit: `rng_restored: false`, `optimizer_state_restored: false`,
  `bit_identical_resume: false`, with the note that resume is "parameter-continuous and not
  bit-identical to an uninterrupted run". Trainable conditions are `F`, `F_beta`, `E`, `E_full`;
  budgets are 20 readout episodes per seed and 2,000 gradient updates.
- **Campaign composition (`run_stage campaign --describe`)** — `start` and `resume` refuse;
  `n_seeds_selected` is null so no evaluation plan resolves.
- **Pilot 2 (`run_stage pilot2 --describe`)** — emits `P2-G` (no certified random graph exists for
  pilot seeds 9001–9003; certification covers campaign seeds 1–16 only) and two `P2-A` blockers
  (the artifact loader accepts only `seeds.campaign`; no trained artifact directory exists for the
  pilot seeds), plus the memory blocker.

---

## 3. Test results

Measured 2026-11-20.

| Suite | Result |
|---|---|
| Phase 8 focused (`pytest tests -q -k phase_8`) | **402 collected / 402 passing** |
| of which `tests/test_phase_8_stage_infrastructure.py` | **50 passing** (the new stages) |
| Full suite (`pytest tests -q`) | **1,481 collected: 1,472 passed, 3 skipped, 6 failed** |

The 402 = 352 previously recorded plus 50 new stage tests. The full-suite total 1,481 agrees with
the focused count (402 Phase 8 + 1,079 other).

### 3.1 The six failures are pre-existing and unrelated to Phase 8

These six were failing before the Phase 8 work and are not caused by it:

1. `tests/test_causal_control.py::test_smoke_100ms_runs_every_condition`
2. `tests/test_causal_control.py::test_c0_only_full_mode_requires_no_cache`
3. `tests/test_feature_ablation.py::test_smoke_window_never_invokes_the_archive_gate`
4. `tests/test_integration_3b_3c.py::test_protected_artifacts_unchanged`
5. `tests/test_p3_3c5_lane_encoding.py::test_source_and_protected_hashes_are_recorded`
6. `tests/test_p3_3c5_lane_encoding.py::test_static_gates_cover_groups_reversal_pools_and_hashes`

They are recorded here so that "software complete" is never read as "the whole repository is
green". The Phase 8 statement is narrower and exact: **every Phase 8 test passes.**

### 3.2 What the tests do and do not prove

The 402 tests exercise real code on synthetic graphs (32 to 60,000 nodes), controlled game
environments and toy agents. The training loops are executed only on tiny temporary fixtures; those
are loop-mechanics tests, not experimental runs. No test executes a BANC-scale episode, generates a
trained artifact on the real substrate, or produces a campaign row.

**Test success establishes mechanism, not evidence.**

---

## 4. Remaining scientific blockers

| # | Blocker | Source | Consequence |
|---|---|---|---|
| B1 | REV4 §12 is unapproved; U1–U18 remain PROPOSED and the document's final paragraph authorises no execution | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` §12, §12.1 | every execution path refuses; exit 2 |
| B2 | `design.n_seeds_selected` is null | `configs/phase_8/campaign.yaml`; `experiments/phase_8/registry.py` `evaluation_plan` | no campaign design resolves, no artifact may be generated, no campaign prepared (U7) |
| B3 | No `(condition, campaign_seed) → training_seed` pairing is declared | REV4 declares none | training cannot plan |
| B4 | No training-episode environment-seed schedule is declared | REV4 declares none | training cannot be made reproducible |
| B5 | No checkpoint cadence, retention or format is declared | REV4 declares none | resume policy undefined |
| B6 | Sampler RNG and optimizer moments are not checkpointed | `experiments/phase_8/training/checkpoint.py` | bit-identical resume **cannot be claimed** |
| B7 | G3 certified graphs carry a recorded §9.3 memory-gate deviation (`status: deviation_recorded`) | `experiments/results/phase_8_random/campaign_seed_summary.json` | graphs may not be used for data collection until amendment or compliant rerun |
| B8 | Free physical memory below the declared 4.0 GiB gate | `psutil.virtual_memory().available`; REV4 §9.3 | no BANC-scale randomisation, campaign simulation or training may start |
| B9 | Pilot seeds have no certified graph and no loadable artifact | `experiments/phase_8/stages/pilot2.py` `P2-G`, `P2-A` | Pilot 2 cannot run as declared |
| B10 | Pre-observed floor risk for Condition A | REV4 §3.6.2; Phase 7 result (0 motor spikes, 213 `NO_ACTION`) | A may be at floor before the campaign; this is a design risk, not a defect |

B1, B2 and B8 gate **everything**. B7 gates C, D, C′ (and is listed by the gate for every stage).
B3–B6 gate training only. B9 gates Pilot 2 only.

---

## 5. Remaining owner decisions

The complete register, with options, consequences and REV4 citations, is
`docs/PHASE_8_OWNER_DECISION_PACKAGE.md` Parts B–F. Summary of what remains open:

- **U1–U18** — eighteen protocol items, each **PROPOSED — not approved** (`docs/PHASE_8_PROTOCOL_DECISION_REGISTER.md`). No item has been approved.
- **U7** — sample size / `design.n_seeds_selected` (Part C.1). Not selected. No power analysis is
  available behind the N=16 recommendation; it is a design recommendation, not a power-derived value.
- **U14** — Holm family size m = 4 or m = 3 (Part C.2). Not selected; the two choices change which
  contrasts exist and therefore what the study claims.
- **B3–B6** — four execution-contract inputs REV4 leaves undeclared (Part D). No value may be invented.
- **Pilot seed / artifact disposition** (Part E). Three legitimate routes; none selected.
- **G3 deviation disposition** (Part F). Amendment, compliant regeneration, or deferral; none selected.
- **Environmental gate** (Part G). The machine is below the gate now.

Every one of these is on the owner sheet in `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` Part I with an
explicit "Approved — owner signature/date: ______" column left blank.

---

## 6. G3 status

| Property | Value |
|---|---|
| Campaign seeds built and certified | **16 / 16** (seeds 1–16) |
| Builds that independently reproduce the certified digest (R17) | 16 / 16 |
| Certificate verification at load | passes for all 16; refuses failed-gate and certificate-less records |
| Integrity markers missing | 0 |
| Minimum free physical memory during builds | **1.628 GB** |
| Gate required by REV4 §9.3 | **4.0 GiB** |
| Recorded compliance status | `deviation_recorded` |
| Graphs modified or regenerated since certification | **none** |

**Certification is not compliance.** The graphs are cryptographically and structurally
reproducible — R4 0.997830–0.997944, R5 0.0010289–0.0010863, R6/R7 change 0, R9b exact, R10/R11 zero,
R12 true, R13 0.000297–0.000353 over 130,709 active nodes, R14 3.00e-05–6.92e-05, 15,357,100 accepted
swaps per seed — but every one was built below the §9.3 free-memory gate, and §9.3 names BANC-scale
graph randomisation among the operations blocked below that gate. That is a recorded protocol
deviation, and the graphs may not be used for experimental data collection until the owner disposes
of it. Details: `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md`.

No graph artifact was touched while preparing this report.

---

## 7. Current memory status

The gate is free **physical** memory via `psutil.virtual_memory().available`, compared against
4.0 GiB, not rounded down (REV4 §9.3).

| Reading | Free | Total | Used |
|---|---|---|---|
| 2026-11-20, this report (independent readings) | **2.805 GB** / **2.973 GB** | 15.342 GB | 81.7% / 80.6% |
| 2026-11-18 readiness record | 2.529 – 2.711 GiB | — | — |
| During the 16 G3 builds | 1.628 – 2.747 GB | — | — |
| REV4 preflight | ≈ 1.1 GB | — | — |
| Original Phase 8 audit | ≈ 0.5 GB | — | — |

**No reading recorded in repository history reaches 4.0 GiB.** The machine is below the gate at
every measurement on record. Available memory is also volatile: it moved by ~0.17 GB between two
readings minutes apart during this report.

Consequence: the gate is environmental, not something code can satisfy. Until it is genuinely met,
`B8` blocks BANC-scale work regardless of how many owner decisions are approved.

---

## 8. Pilot seed incompatibility

Pilot 2 is planned on seeds **9001, 9002, 9003** (`configs/phase_8/campaign.yaml`, `seeds.pilot`).
Two independent contracts exclude them:

1. **Graphs.** `pilot2.py` takes the certified set to be `CertifiedGraphSource().required_seeds`,
   which is campaign seeds 1–16. `graph_coverage` is therefore false for all three pilot seeds,
   producing `P2-G`.
2. **Artifacts.** The training-artifact loader accepts only seeds declared in `seeds.campaign`
   (`experiments/phase_8/training/loader.py`: "campaign seeds … are not declared in
   `seeds.campaign`"), and `loader_accepts = pilot_seeds ∩ campaign_seeds = ∅`. No trained
   artifact directory exists for the pilot seeds either. This produces the two `P2-A` blockers.

Pilot 1 is **not** affected: it uses arm A only, needs no graph and no artifact
(`pilot1 --describe`: `certified_graph_needed: false`, `trained_artifact_needed: false`).

The three legitimate resolutions — a separate certified pilot seed set with its own artifacts; a
formal seed/loader amendment; or selection from the eligible certified set where scientifically
permissible — are analysed in `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` Part E. **None has been
selected. No seed or graph has been substituted.**

---

## 9. Execution authorisation status

Every stage and `run_campaign.py` reports the same state, read today:

```
authorization.approved           : false
authorization.decision_status    : "PROPOSED - not approved"
document_authorises_execution    : false
protocol_matches_expected        : true
protocol_sha256                  : e4aa9e0f2f8f…1547c
authorized                       : false
executable                       : false
executed                         : false
```

`run_campaign.py start` and `resume` return exit 2 with zero episodes and zero rows. The training
stage reports `training_performed: false`, `artifacts_written: 0`. No CLI argument opens the gate.

**The authorisation gate is the binding constraint, and it is working as designed.**

---

## 10. Conflicts between sources (reported, not resolved)

These were found during preparation. Each is a documentation or internal-consistency defect; none
was corrected, because this task may not modify existing files.

1. **Stale "stages absent" claim.** `reports/PHASE_8_IMPLEMENTATION_STATUS.md` (dated 2026-11-18,
   §2 table) and `reports/PHASE_8_FINAL_READINESS_REPORT.md` record Pilot 1, Pilot 2, the training
   CLI, the composition root, the information adapter and the report generator as **absent**.
   The tree now contains `experiments/phase_8/stages/` (8 modules) with 50 passing tests. The
   2026-11-18 documents are superseded on this point by this report; they were not edited.
2. **U7 stage mislabel.** `reports/PHASE_8_G4_REMAINING_BLOCKERS.md` calls U7 the "pilot-1
   decision". REV4 assigns the N decision to **10.8 (Pilot 2)**; Pilot 1's own output says
   `design_decision_needed: false`.
3. **`campaign/protocol.py` docstring vs operative check.** The docstring says `n_seeds_selected`
   "is reported, not failed", but `_check(..., campaign.n_seeds_selected, None, …)` combined with
   `if strict and failed:` (`campaign/protocol.py:520`) makes conformance **fail** once U7 is
   recorded. Recording N therefore requires a code change, not just a config edit.
4. **Pilot 2 blocker names E.** Pilot 2's grid is A, B, C, F, Fβ, A′, C′ and contains no E, yet the
   `P2-A` text names "trained F, F-beta and E artifacts". Cosmetic; the blocker is real regardless.
5. **REV3 references in a REV4-era config.** `configs/phase_8/campaign.yaml` comments cite "REV3"
   throughout while the governing protocol is REV4. Values are unchanged and validated; only the
   citations are stale.
6. **U12 miscitation.** The decision register's U12 entry cites §2.3; the register summary and
   other entries differ. Reported, not fixed.
7. **"10.7/10.8" label.** At least one record refers to the pilot-2 decision as "10.7/10.8"; REV4
   numbers the step 10.8.

A conflict list is part of the evidence. None of these changes any blocker's substance.

---

## 11. Requirements before the first pilot (Pilot 1, §10.3)

Pilot 1 is the cheapest executable step and needs the least: arm A only, biological substrate, no
randomised graph, no trained artifact, no design value. What it still requires:

1. **Owner authorisation of REV4 §12.** Every U item the gate inspects is currently PROPOSED.
   Approval must be recorded in the protocol's approval record, not merely stated in conversation.
2. **Free physical memory ≥ 4.0 GiB at run time**, measured the way §9.3 measures it.
3. **A disposition of B7.** The authorisation gate lists the G3 deviation as an execution blocker
   for Pilot 1 even though Pilot 1 uses no randomised graph. Until either the gate's coupling is
   formally addressed or the deviation is disposed of, the stage will refuse. This coupling is a
   finding of this report; it is not resolved here.
4. **A write root.** A run would create `experiments/results/phase_8/…`; no such directory exists
   today. Creating it is part of execution, not preparation.

Pilot 1 does **not** require: a certified graph, a training artifact, `n_seeds_selected`, U14, or
Pilot 2's seed disposition.

## 12. Requirements before confirmatory execution

All of §11, plus:

1. **U7 resolved** — `design.n_seeds_selected` set to a declared value, and the `protocol.py` null
   check (defect 3 above) reconciled with that declaration.
2. **U14 resolved** — Holm family size chosen; this fixes whether C4 exists and therefore what the
   study claims.
3. **B3–B6 declared** — seed pairing, environment-seed schedule, checkpoint policy, and an explicit
   acceptance that resume is parameter-continuous rather than bit-identical (or a mechanism that
   restores RNG/optimizer state).
4. **Pilot seed disposition (§8)** — resolved by one of the three legitimate routes.
5. **G3 disposition (§6)** — an approved amendment **or** a compliant regeneration above 4.0 GiB.
6. **Training artifacts generated on the real substrate** — F, Fβ and E or E-full; none exists today.
7. **Both pilots executed and recorded** — Pilot 1 (§10.3) and Pilot 2 (§10.8), with the U7 decision
   recorded from the pilot outcome as REV4 requires.
8. **Memory gate passed during every BANC-scale stage**, not just at preflight.
9. **Evaluation plan resolves** — `experiments/phase_8/registry.py` `evaluation_plan` must return a
   plan; it currently raises while the design is null.

Only after all nine does the confirmatory campaign become possible. None is a software defect; each
is an owner decision or an environmental condition.

---

## 13. Separation statement

| Layer | State |
|---|---|
| Software implementation | **complete as mechanisms**; 402/402 Phase 8 tests pass |
| Protocol | **unapproved**; U1–U18 PROPOSED |
| Design | **null**; N not selected |
| Statistics family | **undecided**; m = 4 or m = 3 |
| Graphs | **16/16 certified, non-compliant**; deviation recorded |
| Training artifacts | **none**; infrastructure only |
| Pilots | **not run**; Pilot 2 additionally blocked on seeds |
| Environment | **below the 4.0 GiB gate** |
| Experimental evidence | **none** |

Software completion is real and can be stated plainly. It does not move any scientific blocker, and
it does not authorise a single episode.

---

## 14. What was untouched while preparing this report

- `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` — SHA-256 unchanged
  `e4aa9e0f…1547c`, still 1,915 lines, still unapproved.
- `configs/phase_8/campaign.yaml` — SHA-256 unchanged
  `b9a2d3d5…7e19`, `n_seeds_selected` still null.
- `experiments/results/phase_8_random/` — no graph or certificate modified.
- `experiments/results/phase_8/` — still absent; no experiment was run.
- No implementation file, test, graph, weight, threshold or learning rule was modified.
- No Git operation was performed.
- No external model equation was imported.

Only two documents were created by this work: this report and
`docs/PHASE_8_OWNER_DECISION_PACKAGE.md`.

---

## 15. Provenance

| Artifact | SHA-256 |
|---|---|
| REV4 protocol | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| `configs/phase_8/campaign.yaml` | `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19` |
| `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` | `5d6ecca8accaf8e54bdbfea08c66e08953e485e604c1c0f8e0d3db36a246e9cb` |

Read-only commands used: `run_stage --list`, `run_stage pilot1 --describe`,
`run_stage training --status`, `run_stage campaign --describe`, `run_stage pilot2 --describe`,
`run_campaign check`, `pytest --collect-only`, `psutil.virtual_memory()`. None executes experimental
work.
