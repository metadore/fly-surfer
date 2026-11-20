# Phase 8 — Owner Decision Record D2

| field | value |
|---|---|
| record kind | owner decision record; **not** a protocol, **not** experimental evidence |
| approval id | **D2** |
| approval date | **2026-11-20** |
| recorded by | project owner |
| decision | **G3 deviation is NOT APPLICABLE to Pilot 1 only** |
| bound document | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` |
| document SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (1,915 lines) |
| depends on | D1 (REV4 §12 / U1–U18 approval) |
| machine-readable record | `reports/phase_8_owner_approvals/D2.json` |

## What D2 records

The project owner decides that the G3 §9.3 randomization-set deviation is **not applicable to
Pilot 1 only**. Pilot 1 runs:

- biological condition **A only**;
- **nine episodes** — seeds **9001, 9002, 9003**, three episodes each;
- **no randomized graph** is loaded;
- **no trained artifact** is required.

G3 remains blocking for every experiment that requires randomized graphs, including Pilot 2,
the confirmatory campaign, training and every condition built on a certified random graph.

## What D2 does not do

- It does **not** accept, resolve or downgrade the recorded G3 §9.3 deviation. The deviation
  stays `deviation_recorded`, `gate_weakened: false`.
- It does **not** weaken any graph certification requirement. No graph is recertified,
  regenerated or re-used.
- It does **not** authorise Pilot 2, the confirmatory campaign, training, or any randomized-graph
  condition.
- It does **not** bypass the 4 GiB memory gate or any other independent gate.
- It does **not** change any parameter, value or definition, and it does **not** edit REV4.

## Scope of the exemption (exact)

| field | value |
|---|---|
| stage | `pilot1` |
| arms | `["A"]` |
| seeds | `[9001, 9002, 9003]` |
| episodes per seed | `3` |
| total episodes | `9` |
| randomized graph used | **no** |
| trained artifact used | **no** |
| G3 still blocks | Pilot 2, confirmatory campaign, training, C/D/C′ and every certified-random-graph arm |

The authorisation code applies the exemption only when the requested grid matches this table
field for field and the requested condition is the biological A substrate. A forged plan, a
different arm set, a different seed set, a different episode count, or a stage other than
`pilot1` receives the unchanged B7 refusal.

## Current effect on execution

| gate | state after D2 |
|---|---|
| B1 — protocol approval (§12 / U1–U18) | satisfied by D1 |
| B2 — campaign design (`n_seeds_selected` null, U7) | still blocking campaign preparation; not required by Pilot 1 |
| B3–B6 — training-operation inputs | still blocking training and artifact generation |
| B7 — G3 §9.3 memory-gate deviation | **unchanged and unaccepted**; not applicable to the exact Pilot 1 grid only |
| B8 — §9.3 memory gate at run time | enforced per run; unchanged |

Pilot 1 may proceed past B7 only because it loads no randomized graph. Nothing else changes:
Pilot 2, the confirmatory campaign and training still refuse.
