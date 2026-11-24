# Phase 8 Owner Approval D5 — Authorised Pilot-Scoped F/Fβ Training

Record: `reports/phase_8_owner_approvals/D5.json`
Approval date: **2026-11-22**
Owner decision: **D5** (depends on D4)

## 1. Decision

The owner approves the exact D5 proposal recorded in
`reports/PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md`
(SHA-256 `f8d441a4e98bdc73ebcb7405acff02fc7221969a0aa1217ff7f88cfe2e6d3771`,
§9). D5 authorises the pilot-scoped training of **six F and Fβ readout
artifacts** on the frozen biological substrate, exactly six artifacts over the
three declared evaluation seeds, twenty episodes per artifact, using the D4
B3/B4/B5/B6 training contracts.

D5 authorises those six training runs and nothing else. It authorises **no E or
E-full**, **no confirmatory campaign**, **no Pilot 2-C episode**, **no floor
replay**, **no randomized graph**, and **no change** to a frozen parameter,
statistical constant, hypothesis or protocol document. It discharges no open
item and selects no sample size.

## 2. Hash binding

D5 is recognised only when bound to the exact documents it cites. The record
stores these values and the validator recomputes each hash from disk.

| Document | Path | SHA-256 |
| --- | --- | --- |
| REV4 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Pilot 2-C amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` |
| D3 record | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` |
| D4 record | `reports/phase_8_owner_approvals/D4.json` | `1e15138cf76c11ab8c94ffd7299d6a3657fc407fe7c32a0f8a3c9efcca51a8cf` |
| D5 proposal | `reports/PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md` | `f8d441a4e98bdc73ebcb7405acff02fc7221969a0aa1217ff7f88cfe2e6d3771` |

A changed REV4, amendment, D3 or D4 invalidates D5 rather than silently
inheriting its authorisation.

## 3. Authorised artifacts

Six independent trained artifacts, twenty episodes each, one hundred and twenty
training episodes in total. Pairings are the verified D4 B3 derivation
(record SHA-256 `bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980`),
recomputed from `master_seed = 20261116` and the declared `seeds.training` pool.

| Condition | Evaluation seed | Training seed | Pool index | Episodes |
| --- | --- | --- | --- | --- |
| F | 9001 | 1008 | 7 | 20 |
| F | 9002 | 1014 | 13 | 20 |
| F | 9003 | 1005 | 4 | 20 |
| F_beta | 9001 | 1008 | 7 | 20 |
| F_beta | 9002 | 1014 | 13 | 20 |
| F_beta | 9003 | 1005 | 4 | 20 |

F and Fβ at one evaluation seed share the derived training seed, as REV4 §3.6.2
requires, but each condition receives its own independent artifact directory,
manifest and parameter file.

## 4. Scope and substrate

- Stage: `training` (REV4 §10.5).
- Substrate: frozen **biological graph** only. No randomized graph is
  constructed, read or substituted.
- Origin `trained`, final stage `trained`, written only under
  `experiments/results/phase_8/training`.
- Training contracts: D4 B3 (pairing), B4 (training environment seeds),
  B5 (per-episode checkpoints, full retention), B6 (exact resumption).
- Every intermediate checkpoint and the final checkpoint are retained.
- Resume only from a verified checkpoint with full state restored and
  equivalence verified.

## 5. Preserved invariants

- `design.n_seeds_selected` stays `null`.
- U7 remains open; N stays 16 primary; no confirmatory sample size is selected
  and no dispersion is estimated.
- REV4, D1, D2, D3 and D4 are unchanged; every hypothesis, contrast and
  statistical constant is unchanged.

## 6. Boundary

D5 does not authorise, and the implementation must not perform:

- E or E-full;
- the confirmatory campaign;
- a Pilot 2-C episode or any floor replay;
- constructing, reading or substituting a randomized graph, or any
  graph-dependent stage;
- modifying REV4, D1, D2, D3 or D4, or any frozen parameter, hypothesis,
  contrast or statistical constant;
- discharging U7 or setting `design.n_seeds_selected`;
- lowering a resource threshold or reducing the approved workload;
- claiming equivalence without a demonstrated comparison.

D5 authorises only the six exact F/Fβ training runs above, on the frozen
biological substrate, for one hundred and twenty episodes, plus certification
and preflight of those artifacts that execute no Pilot 2-C episode.
