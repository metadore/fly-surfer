# YOLO11n Training Authorisation Record

**Date of this record:** 2026-11-25
**Status:** record of fact. **This is not an approval, and it is not retroactive
authorisation.**
**Scope:** documents that the YOLO11n training run of 2026-11-06 happened while
`reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` still recorded its final
decision as **BLOCKED**.

---

## 1. Why this record exists

The repository contains two facts that must both remain visible:

1. The Phase 3B.2B.1 pre-training readiness audit, dated **2026-11-06**, ended
   with **"Final decision: BLOCKED — not ready to train"** (audit §16, line 742),
   and recorded several items as **BLOCKED** in §11.1 and §16, including:
   - accepted licence decision for YOLO11 training — "No record in the
     repository" (line 548);
   - official checksum for `yolo11n.pt` — not available offline (line 549);
   - game screenshot / IP rights — unresolved (line 550).
2. A YOLO11n training run was executed on **2026-11-06** in Google Colab. The
   recovered notebook (SHA-256
   `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da`) contains
   the executed `train()` call, and the exported ONNX file carries
   `date: 2026-11-06T17:01:02.116695+00:00`.

The audit was not updated after the run, and no approval record exists in the
repository. Read separately, the two documents appear to contradict each other.
Read together, they record a **governance gap**: the run happened before the
audit's BLOCKED items were cleared.

This record states that plainly. It does not close the gap by assertion.

---

## 2. What is being recorded

| Item | Recorded fact |
|---|---|
| Readiness decision on 2026-11-06 | BLOCKED — not ready to train (`PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` §16) |
| Training execution | 50 epochs, 1,188 group-held-out training images, Google Colab, 2026-11-06 |
| Approval document for that run | **None found in the repository** |
| Operator identity | **Not recorded** |
| Licence decision covering the run | **Not recorded as an approval**; the licensing analysis was produced later (`YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md`, 2026-11-20) |
| Date of this record | 2026-11-25 |

**No approval is invented here.** The absence of an approval record is itself the
recorded fact. This document must not be cited as evidence that training was
authorised at the time.

---

## 3. Readiness decision versus actual execution

The readiness audit was a **gate on starting training**. The training run was an
**execution event**. They answer different questions:

- The audit asked: *are the export, licence decision, configuration, evaluation
  plan and Git exclusions in place to start?* It answered **no** on 2026-11-06.
- The notebook records: *what was executed, with which arguments, producing
  which artifacts?* It answers with the run of 2026-11-06.

Both statements can be true at once, and here they are: the gate said no, and the
run happened anyway. Preserving both is the only accurate account. Deleting the
BLOCKED verdict, or silently implying it was lifted, would falsify the record.

Some audit findings were subsequently addressed by later work, but that does not
retroactively authorise the run:

- The dataset export that the audit recorded as missing was produced in
  Phase 3B.2B.1 (`reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md`).
- The Git-safety finding was addressed by `.gitignore` exclusions for `models/`,
  `*.onnx` and `*.pt` (see `THIRD_PARTY_NOTICES.md`).
- The licence analysis was produced on 2026-11-20, **after** the run, and it
  reaches an "insufficient evidence" verdict for publication today
  (`YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` §1, §8).
- The base-checkpoint checksum question remains open: the downloaded bytes were
  never hashed at run time, and no official upstream checksum was recorded
  (provenance report I11).

---

## 4. Consequences that remain in force

1. **The BLOCKED verdict stays in the audit as written.** It is a historical
   record and is not edited by this document.
2. **No retrospective authorisation is claimed.** Any future release must rest on
   a decision taken now, not on an inferred past one.
3. **The licence route for the resulting weights is unresolved.** Repository
   separation is a packaging choice, not a legal conclusion; the AGPL-3.0
   questions in `YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` remain open.
4. **The run date used in every document is 2026-11-06**, not the local notebook
   file's modification time (provenance report I15).
5. **Bit-exact reproduction is not claimed.** The run was non-deterministic,
   the optimiser was auto-selected, the base download was not hashed and the
   training logs were not preserved.

---

## 5. Relationship to the other records

| Record | Role |
|---|---|
| `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md` | The original gate; still says BLOCKED; unedited |
| `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md` | What actually ran, recovered from the notebook (I1–I17) |
| `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` | Licence analysis; verdicts unchanged; not superseded here |
| `docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md` | The correction proposal (I5 resolves to this record) |
| `docs/research/YOLO11N_DOCUMENTATION_RECONCILIATION_IMPLEMENTATION_REPORT.md` | What documentation was changed and verified |
| This record | States the execution/authorisation gap without resolving it by assertion |
