# Phase 8 — Owner Approval Record D1

| field | value |
|---|---|
| record kind | owner approval record; **not** a protocol, **not** experimental evidence |
| approval id | **D1** |
| approval date | **2026-11-20** |
| recorded by | project owner |
| approved document | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` |
| approved document SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines) |
| approval scope | REV4 **§12** and **U1–U18** |
| scope qualifier | approved **as written**, with the existing proposed values and definitions |
| parameter modifications authorised | **no** |
| machine-readable record | `reports/phase_8_owner_approvals/D1.json` |

## What D1 records

The project owner approves `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` §12 as written,
including U1–U18 with their existing proposed values and definitions. No parameter, value or
definition is modified by this approval.

## What D1 does not authorise

- bypassing any other execution gate — the design gate (U7/B2), the training-operation gate
  (B3–B6), the memory gate (B8) and the G3 gate (B7) all remain active;
- any change to a parameter, value or definition;
- regeneration of the G3 random graphs or acceptance of the recorded §9.3 memory-gate deviation;
- use of the certified G3 graphs for experimental data collection while B7 remains open.

## Relationship to the frozen document

REV4 itself is **unchanged**. Its closing paragraph still says that the document authorises no
execution; D1 is a separate, external decision record, not an edit of the document. The
authorisation code binds the approval to the recorded SHA-256: if REV4 changes, the recorded
approval no longer matches and the approval is reported as absent until a new record is made.

## Current effect on execution

| gate | state after D1 |
|---|---|
| B1 — protocol approval (§12 / U1–U18) | **satisfied by D1** |
| B2 — campaign design (`n_seeds_selected` null, U7) | still blocking campaign preparation |
| B3–B6 — training-operation inputs | still blocking training and artifact generation |
| B7 — G3 §9.3 memory-gate deviation | still blocking experimental execution; applicability not resolved |
| B8 — §9.3 memory gate at run time | enforced per run |

Approval of §12 does not start anything. Every entry point still refuses while any independent
gate is open; with B7 unresolved, all experimental execution still refuses.
