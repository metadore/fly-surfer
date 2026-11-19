# Phase 8 G3 memory-gate deviation: resolution assessment

**Date:** 2026-11-18
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256 (verified this pass):** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`
**Scope:** the sixteen degree- and sign-preserving randomized BANC graphs certified for Condition C (and
used by D and C′), and the §9.3 free-memory gate they were built under.
**Status of this document:** assessment and recommendation. **It does not waive, amend or weaken
§9.3, and it does not regenerate anything.** The protocol remains as frozen; the graphs remain as
certified.

---

## 1. The requirement

REV4 §9.3 states:

> At original audit time only **0.5 GB of 15.34 GB RAM was available**; the most recent preflight
> before this revision measured **≈ 1.1 GB free** (1,152,972 KB of 16,087,140 KB), still below the
> 4 GB gate. […] The gate is **4 GB of free physical memory**, and it is not weakened, rounded down or
> waived.
>
> The campaign must **re-check free memory immediately before starting** and record it. If < 4 GB is
> free, the campaign does not start and reports the reason rather than failing mid-run […]. While the
> machine is below the gate:
>
> - no BANC-scale graph randomisation;
> - no full campaign simulation;
> - no training run;
> - no memory-intensive test suite.
>
> Safe implementation, static inspection, unit-level tests on synthetic graphs and document work may
> proceed. Any execution work that is skipped for this reason is recorded as **pending resource
> availability**, never as completed.

The gate is an **operational constraint**, not a threshold on a result. Its purpose is that work the
machine cannot carry does not start, rather than failing mid-run and leaving an incomplete artifact.

The implementation measures with `psutil.virtual_memory().available / 1024³`, i.e. the 4 GB gate as
implemented is 4 GiB (4.295 × 10⁹ bytes). The gate value is declared as
`configs/phase_8/campaign.yaml::budget.memory_gate_gb: 4.0` and is read by
`experiments/phase_8/config.py::memory_preflight` / `require_memory_gate`. It is not rounded down,
not scaled by a fraction, and an unmeasurable reading counts as **not passed**.

---

## 2. What actually happened

Source: `experiments/results/phase_8_random/campaign_seed_summary.json`, `compliance` block, and
`reports/PHASE_8_BANC_RANDOM_GRAPH_CAMPAIGN.md` §2, §4, §10.

| Fact | Value |
|---|---|
| Seeds built | 16 (campaign seeds 1–16) |
| Seeds individually certified against R1–R18 | 16 |
| Mandatory-gate failures | 0 |
| Runs started with ≥ 4 GiB free | **0** |
| Free physical memory, observed range | **1.628 – 2.747 GiB** |
| Construction preflight floor | 0.75 GB, `allowed: true` for all 16 |
| Construction peak RSS | 525.8 – 527.3 MB |
| Runner peak RSS | 431.5 – 433.3 MB |
| Lowest free memory during construction | 1.628 GiB (seed 4) |
| Lowest free memory during the runner | 1.936 GiB (seed 2) |
| Runner wall time | 115.2 – 127.4 s per seed; 1,903.0 s for 16 |
| Concurrent builds | none |
| Recorded status | `deviation_recorded` |
| Recorded `gate_weakened` | `false` |

The `compliance` block states, verbatim:

```json
{
  "rev4_section": "9.3",
  "gate_gb": 4.0,
  "gate_weakened": false,
  "operations_blocked_below_gate": [
    "BANC-scale graph randomisation",
    "full campaign simulation",
    "training run",
    "memory-intensive test suite"
  ],
  "min_observed_free_gb": 1.628,
  "max_observed_free_gb": 2.747,
  "construction_runs_below_gate": true,
  "construction_preflight_floor_gb": 0.75,
  "construction_preflight_allowed_all": true,
  "status": "deviation_recorded"
}
```

The 0.75 GB construction floor is the generator's own safety preflight. It is **not** the §9.3 gate
and cannot substitute for it. Passing it means the build was expected to fit; it does not mean the
protocol's 4 GiB condition was met. Both statements are true at once and are kept apart.

The distinction this section preserves:

- The **safety rationale** behind §9.3 held in practice: every build fit (peak RSS ≈ 0.53 GB) with at
  least 1.628 GiB free, and no build exhausted memory.
- The **rule as written** was not met: graph randomisation is explicitly in the blocked list, and it
  ran sixteen times below the gate.

Reporting the set as "§9.3-compliant" would be false. Reporting it as "certified with a recorded
§9.3 deviation" is accurate and is what the artifact store and the campaign report already say.

---

## 3. Affected requirements

| Requirement | Affected? | How |
|---|---|---|
| REV4 §9.3 free-memory gate | **yes** | Not met at any preflight; recorded as deviation |
| REV4 §10.4 acceptance ("BANC-scale construction is blocked while below the memory gate") | **yes** | The stage ran below the gate, so its acceptance criterion is not satisfied as written |
| REV4 §10.0 protocol approval | no | Independent of the build; still unapproved |
| REV4 §12 U18 (target exchange) | **separate issue** | The generator implements option (a) but U18 is unapproved; this is not caused by the memory deviation |
| R1–R18 certificate gates | no | Each graph was certified on its own content; the gates do not depend on the machine's memory |
| R17 two-build determinism | no | Checked per seed at build time; byte-identical |
| R18 seed derivation | no | Independent of memory |
| Original-graph integrity | no | Original graph opened read-only; hash unchanged (verified again below) |
| Condition C/D/C′ loader | no | `load_structure` accepted 16/16 records; loader does not read memory state |
| Campaign execution | **yes, indirectly** | The campaign cannot claim §9.3-compliant provenance while the deviation stands |
| Scientific validity of C/D contrasts | no, on integrity grounds | The null graphs satisfy every declared structural gate; the deviation is about *when/how* they were built, not *what* they are |

---

## 4. Integrity assessment

### 4.1 Evidence collected in this pass (read-only)

Every graph and certificate was hashed from disk and compared with the SHA-256 recorded in the
certified summary. No file was opened for writing; no graph was regenerated; no array was modified.

| Check | Result |
|---|---|
| Graph files hashed and compared with `graph_sha256` | **16 / 16 identical** |
| Certificates hashed and compared with `certificate_sha256` | **16 / 16 identical** |
| `RUN_INCOMPLETE` markers present | **0 / 16** |
| REV4 protocol hash recomputed | `e4aa9e0f…1547c` — matches the certificate expectation |
| Original BANC graph hash recomputed | `6d47f259…e2192` — matches the recorded original |
| Summary's recorded original hash | same `6d47f259…e2192` |
| Distinct graph digests recorded at certification | 16 / 16 distinct |
| Deterministic regeneration recorded at certification | 16 / 16 identical digests |
| Cross-seed artifact duplication | none |
| Loader acceptance per seed | 16 / 16 |

Because a file's SHA-256 is unchanged, its bytes are unchanged, and therefore every array and the
`graph_digest` derived from those arrays are unchanged. Recomputing the digest is not required to
establish integrity; the file hash is sufficient and is cheaper and safer under the memory gate.

### 4.2 What remains valid

- Each graph is **structurally what its certificate says**: exact per-node in/out degree, exact weight
  multiset, exact per-source weight profile (R9b), exact per-node transmitter signs, zero duplicate
  pairs, zero self-edges, valid CSR, rewired fraction ≥ 0.99, neighbourhood Jaccard ≤ 0.01, R14
  plateau, R17 byte identity.
- Each certificate is **bound to its graph file** by SHA-256 and to the manifest and results files by
  recorded hashes; the loader re-checks the binding.
- The 16 graphs are **distinct** from each other and from the original, and the derivation from
  `SeedSequence([20261116, N, 4])` is recorded and was independently re-checked.
- The **original graph is unchanged**, so the comparison baseline is intact.
- The **Condition C/D/C′ code path** consumes the certified record and refuses anything else.

### 4.3 What is not established

- That the builds were **performed under §9.3**. They were not.
- That the null model is **statistically valid** for this connectome. R14 is a plateau diagnostic,
  not a mixing proof; this is a separate limitation stated in the campaign report.
- That **U18 is approved**. It is not; the generator implements the proposed option (a).
- That the set is **campaign-ready**. Compliance is one of several open gates.

**Conclusion of the integrity assessment:** the graphs and certificates are intact and usable as
objects; the deviation is a **compliance** defect, not a **corruption** defect. No evidence was found
that any graph or certificate is wrong for what it claims to be.

---

## 5. Is compliant regeneration necessary?

This is a user decision. The technical facts that bound it:

| Option | What it would establish | Cost / risk | Effect on existing artifacts |
|---|---|---|---|
| **A. Accept the recorded deviation** (no regeneration) | Nothing about §9.3 compliance. The set stays "certified with a recorded deviation". A campaign run under it cannot claim compliant execution unless the protocol is amended or a waiver is recorded. | Zero execution. Requires a user decision and a written rationale. | None. Existing certificates remain valid. |
| **B. Regenerate all 16 on a machine with ≥ 4 GiB free** | A compliant build record for the same 16 seeds. Because the generator is deterministic, the resulting digests **should** equal the published ones; equality is a check, not an assumption. | ~31 min runner for 16 seeds plus 16 × ~2 min certification, sequential; peak RSS ≈ 0.53 GB; must use **new namespaces** and must not overwrite the certified directories. | Existing artifacts must not be modified. New artifacts are compared with the old; if digests match, the structural result is unchanged. |
| **C. Regenerate a subset** | Nothing sufficient: §9.3 applies to each build, and a compliant subset does not make the set compliant. | Partial cost. | Could create a mixed-provenance set, which is worse than a uniformly recorded deviation. Not recommended. |
| **D. Defer until the machine is above the gate, then regenerate** | The same as B, later. | No execution now. The delay is unbounded. | None now. |

**Is regeneration necessary for integrity?** No. Section 4 shows the files are intact and certified.

**Is regeneration necessary for a compliant campaign?** Only if the campaign must claim §9.3
compliance **without** a protocol amendment or recorded waiver. REV4 says the gate is "not weakened,
rounded down or waived" — so a waiver is not something this document can grant. The honest paths are
(A) a user-recorded deviation with an explicit statement that the campaign carries it, or (B/D) a
compliant rebuild.

**Recommendation (advisory):** **do not regenerate now** — the machine is below the gate, and
regeneration below the gate would repeat the same violation. Preserve the certified set as-is. Record
the deviation as a known, bounded compliance defect. If the campaign must be §9.3-compliant, plan a
sequential rebuild (B) on a machine that sustains ≥ 4 GiB free, into new namespaces, with the existing
set retained for digest comparison. This is a user decision, not a harness decision.

**Do not** describe the existing set as compliant, and **do not** treat the 0.75 GB construction
preflight as satisfying §9.3.

---

## 6. Exact preflight requirements for any future regeneration

If option B or D is authorised, these are the requirements the run must satisfy. They restate §9.3
and the existing generator's own checks; they add nothing and weaken nothing.

1. **Measurement.** Use `psutil.virtual_memory().available` in bytes, divided by 1024³ (the same unit
   as `memory_preflight`). Record both GiB and bytes. The gate is **≥ 4.0 GiB**.
2. **Timing.** Measure **immediately before each seed starts**, not only once at the beginning of the
   batch. A batch that starts above the gate and later drops below it must stop before the next seed.
3. **No substitute floors.** The 0.75 GB construction preflight is a separate safety check. Passing it
   does not satisfy §9.3, and failing §9.3 is not cured by passing it.
4. **Abort behaviour.** If the reading is below 4.0 GiB, do not start the seed. Record
   `pending resource availability` with the measured value and the time; never mark the seed complete.
   If the reading is unavailable, treat the gate as **not passed**.
5. **Sequential execution only.** One `certify_banc` process at a time; no concurrent seeds; no
   parallel builds. Parallelism would change the memory profile and is outside the declared plan.
6. **Namespaces.** Write to new, empty namespaces. `certify_banc` refuses an occupied namespace
   (exit 5). Never overwrite, move or delete the currently certified directories.
7. **Frozen inputs.** Recompute and record the SHA-256 of the REV4 protocol, the original graph, the
   node table and the synapse policy **before** the first build and **after** the last. Any drift is a
   hard stop. The original graph is opened read-only.
8. **Per-seed certification.** Each seed must pass R4, R5, R6, R7, R8, R9, R9b, R10, R11, R12, R13,
   R14 and R17, build the graph twice and show byte identity (R17), and record R18 derivation. A
   marker must be removed only after the graph, certificate, manifest and results are written and
   hash-verified.
9. **Comparison with the existing set.** For every seed, compare the new `graph_digest` with the
   published digest. Equality is expected from determinism but must be observed. A mismatch is a
   finding, not a reason to overwrite; it must be investigated and reported.
10. **Record.** Write the observed free-memory range, the number of seeds attempted, the exit codes,
    the preflight values and the `compliance.status` into the new summary. `gate_weakened` must remain
    `false`.
11. **Budget.** Expect ~115–127 s per seed for the runner and ~1,900 s for 16 seeds, plus certification
    time; peak RSS ≈ 0.53 GB. These are measured figures, not guarantees.
12. **Approval.** Regeneration is execution. It requires the protocol approval (10.0) and U18 to be
    resolved, or an explicit user instruction that the rebuild is a compliance exercise independent of
    U18. It cannot start merely because memory is available.

---

## 7. Can the current machine safely regenerate?

**No.**

| Measurement | Value |
|---|---|
| Total physical memory | 16.47 × 10⁹ B (15.34 GiB) |
| Available physical memory, direct `psutil` reading | 2.911 × 10⁹ B (**2.711 GiB**) |
| Available physical memory, read-only campaign CLI (`memory_preflight`) | **2.529 GiB** |
| Gate | 4.0 GiB |
| Margin at the lower reading | **−1.47 GiB** |

The reading is below the gate even though it is above the 1.628–2.747 GiB range observed during the
original builds. A single higher reading does not satisfy the rule, which is a threshold, not an
average. The read-only campaign CLI reports the same state and refuses execution.

**Therefore:**

- no BANC-scale graph randomisation is authorised now;
- no regeneration is attempted by this pass;
- no campaign simulation, training run or memory-intensive suite is authorised now;
- the existing certified graphs are left untouched.

This assessment itself was performed with read-only operations: file hashing, JSON reading and a
memory measurement. No numpy array was loaded for randomisation, no graph was rebuilt, and no
namespace was written.

---

## 8. Consequences for Phase 8 readiness

1. **G3 cannot be marked §9.3-compliant.** It remains "16/16 certified, with a recorded deviation".
2. **The deviation does not invalidate the graphs or certificates.** Conditions C, D and C′ can consume
   them; the loader does, and the structural gates hold.
3. **A campaign that runs under this set inherits the deviation.** The run manifest and the final
   report must carry it; it cannot be reported as a compliant execution.
4. **The deviation is independent of the design gates.** Resolving U7 or U18 would not cure it; curing
   it requires either a user-recorded deviation/amendment or a compliant rebuild.
5. **The machine remains below the gate**, so the campaign and all training are also blocked by
   resources independently of the protocol approvals.

This is one of the reasons the final verdict in `PHASE_8_FINAL_READINESS_REPORT.md` is **NOT READY**,
not "ready for approval". A protocol decision cannot be requested while a mandatory operational gate
is known to be unmet and unresolved.

---

## 9. Decision record (blank)

| Field | Value |
|---|---|
| G3 deviation decision | ☐ accept recorded deviation (no regeneration)  ☐ authorise compliant rebuild  ☐ defer |
| If rebuild: machine / date | |
| If accepted: rationale and scope of the deviation | |
| U18 decision (separate) | |
| Date | |
| Protocol SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |

Until this record exists, the status is: **certified, deviation recorded, not compliant, not
regenerated.**

---

## 10. What this document does not do

1. It does not regenerate, repair or replace any graph or certificate.
2. It does not mark the set compliant, and it does not weaken the 4 GB gate.
3. It does not approve U18 or any other U-item.
4. It does not delete, move or rename any artifact.
5. It does not run a campaign, pilot, training job or game episode.
