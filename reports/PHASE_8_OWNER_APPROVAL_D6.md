# Phase 8 Owner Approval D6 — B7 Has No Subject in the D5 Plan

Record: `reports/phase_8_owner_approvals/D6.json`
Approval date: **2026-11-22**
Owner decision: **D6** (depends on D5)

## 1. Decision

The owner records that the REV4 §9.3 memory-gate deviation tracked as blocker
**B7** has **no subject in the exact D5 training plan**. D5 trains on the frozen
biological substrate only; it constructs, reads without authorisation, or
substitutes no randomized graph, so the deviation from the §9.3 gate cannot be
triggered, accepted, resolved or weakened by it.

D6 follows the exact D6 proposal recorded in
`reports/PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md`
(SHA-256 `f8d441a4e98bdc73ebcb7405acff02fc7221969a0aa1217ff7f88cfe2e6d3771`,
§10).

D6 authorises **no training**, **no graph construction**, **no graph access**
and **no graph-dependent stage**.

## 2. Hash binding

D6 is recognised only when bound to the exact documents it cites. The record
stores these values and the validator recomputes each hash from disk.

| Document | Path | SHA-256 |
| --- | --- | --- |
| REV4 (§9.3) | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Pilot 2-C amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` |
| D3 record | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` |
| D4 record | `reports/phase_8_owner_approvals/D4.json` | `1e15138cf76c11ab8c94ffd7299d6a3657fc407fe7c32a0f8a3c9efcca51a8cf` |
| D5 record | `reports/phase_8_owner_approvals/D5.json` | `015598e82217b0655b0c4e851948b5c2fc08c16967023238f04c1389ca8bfe3f` |
| G3 compliance summary | `experiments/results/phase_8_random/campaign_seed_summary.json` | `d4e85db7787fea487a0e793ad9c87ca189f4332c34d6063165bd6c435f2ea0ef` |

A changed D5 invalidates D6: the "no subject" finding holds only for the exact
D5 plan.

## 3. Decisions, verbatim in substance

- **OD-1.** B7 has no subject in the D5 plan: the six authorised F/Fβ training
  runs use the frozen biological substrate and construct, read or substitute no
  randomized graph. The §9.3 memory gate governs BANC-scale graph
  randomisation, not a constant biological-substrate training run.
- **OD-2.** The G3 compliance record is preserved exactly: status
  `deviation_recorded`, `gate_weakened = false`, REV4 §9.3 unchanged. D6 neither
  accepts nor resolves the deviation and does not re-run the randomised
  construction.
- **OD-3.** All sixteen randomized graph files and all sixteen certificates are
  preserved unchanged; their recorded SHA-256 digests remain the authority. D6
  does not regenerate, read, compare against or replace any graph.
- **OD-4.** Every graph-dependent stage remains blocked. D6 grants no exemption
  to any graph-dependent stage and is **non-inheritable**: it is scoped only to
  the exact D5 plan and does not carry to Pilot 2-C, the confirmatory campaign,
  or any other stage beyond the one already covered by D3.

## 4. Preserved state

- G3 status: `deviation_recorded`.
- `gate_weakened`: `false`.
- Gate: 4.0 GB free physical memory, unchanged.
- Randomized graphs unchanged: 16; certificates unchanged: 16; all certified.
- REV4 §9.3 unchanged.
- Graph-dependent stages: blocked.
- Graph access / construction / substitution: not authorised.

## 5. Boundary

D6 does not authorise, and the implementation must not perform:

- constructing, reading or substituting a randomized graph;
- accepting, resolving or weakening the G3 §9.3 deviation;
- altering REV4 §9.3 or the G3 compliance record;
- regenerating or replacing any randomized graph file or certificate;
- unblocking any graph-dependent stage;
- inheriting D6 beyond the exact D5 plan;
- treating D6 as authorising any training run;
- modifying REV4, D1, D2, D3, D4 or D5;
- discharging U7 or setting `design.n_seeds_selected`.

D6 authorises only the recording that B7 has no subject in the exact D5 plan,
and the confirmation that the D5 biological-substrate training lies outside the
§9.3 graph-randomisation gate.
