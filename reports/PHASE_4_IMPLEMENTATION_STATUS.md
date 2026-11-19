# Phase 4 — Implementation Status (updated)

**Date:** 2026-11-17
**Supersedes:** the Phase 4 rows in earlier status summaries. Phase 8 REV4 and
its approval status are unchanged.
**One-line status:** Phase 4 software is complete; the sensory-to-motor function
is a controlled negative pending external evidence.

---

## 1. Status by deliverable

| Deliverable | File | Status |
|---|---|---|
| Anatomical motor-pathway report | `reports/PHASE_4_MOTOR_PATHWAY_REPORT.md` | Complete |
| Motor population and mapping evidence table | `reports/PHASE_4_MOTOR_POPULATION_EVIDENCE_TABLE.md` | Complete |
| Completion matrix (nine requirements) | `reports/PHASE_4_COMPLETION_MATRIX.md` | Complete |
| Missing-resource inventory | `reports/PHASE_4_MISSING_RESOURCES.md` | Complete |
| Phase 7 motor-output failure analysis | `reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md` | Complete |
| Phase 4 implementation report | `reports/PHASE_4_IMPLEMENTATION_REPORT.md` | Complete |
| This status report | `reports/PHASE_4_IMPLEMENTATION_STATUS.md` | Complete |

---

## 2. Code status

| Module | Role | Status |
|---|---|---|
| `motor/populations.py` | Annotation-defined LEFT/RIGHT/JUMP masks, unassigned reporting | Unchanged, complete |
| `motor/action_decoder.py` | Windowed active-fraction decoding, gates, priority, arbitration | Unchanged, complete |
| `motor/motor_decoder.py` | Decoder interface and record types | Unchanged, complete |
| `motor/activity_recorder.py` | Motor-window extraction | Unchanged, complete |
| **`motor/action_selection.py`** | **Conflict policy, priority, min-hold, cooldown, invalid-state handling** | **New, complete** |
| **`environment/game_controller.py`** | **Decode → select → map → step binding** | **New, complete** |
| `environment/action_adapter.py` | Decoder state → validated game action | Unchanged, complete |
| `environment/live_loop.py` | Real sensory→BANC→decoder→game loop | One optional parameter added |
| `environment/__init__.py` | Package exports | Extended |
| `motor/__init__.py` | Package documentation | Extended |

---

## 3. Verification

| Check | Result |
|---|---|
| Phase 4 + Phase 7 focused tests | **193 passed** |
| Phase 8 focused tests | **325 passed** |
| New selection/controller tests | **42 passed** (24 + 18) |
| Phase 7 record schema for default runs | Unchanged (field-set test) |
| Decoder thresholds / weights / sensory currents / graph / simulator parameters | Unchanged |
| Frozen Phase 4 artifacts | Not modified |
| Phase 8 REV4 text and approval status | Not touched |
| Training, pilots, campaigns, experimental data collection | None run |
| Datasets, artifacts, root README | Not modified |
| Git staging / commit / push / reset / clean / stash | None performed |

Test commands are recorded in `reports/PHASE_4_IMPLEMENTATION_REPORT.md` §5.

---

## 4. Requirement status at a glance

| Requirement | Status |
|---|---|
| 1. Investigate descending pathways | Complete |
| 2. Identify neuronal populations | Complete with limitations |
| 3. Investigate motor annotations | Complete with limitations |
| 4. Design experimental motor mapping | Complete with limitations |
| 5. Implement action decoding | Complete |
| 6. Add action thresholds | Complete |
| 7. Prevent conflicting actions | Complete |
| 8. Add action timing constraints | Complete |
| 9. Test complete sensory-to-motor loop | Implemented and executed; motor recruitment not achieved |

Detailed evidence: `reports/PHASE_4_COMPLETION_MATRIX.md`.

---

## 5. Known open items

| Item | Type | Owner action |
|---|---|---|
| ROLL / DUCK channels | Missing annotation evidence | Acquire R1/R2 or leave unsupported |
| Sensory drive does not recruit motor neurons | Model/evidence gap | Acquire R3/R4 and pre-register a new experiment |
| Feature→sensory-neuron map is a hypothesis | Scientific validity gap | Acquire R5 |
| Action labels are pools, not commands | Scientific validity gap | Acquire R6 |
| 414 unassigned motor neurons, 197 missing target types | Annotation coverage | R7 |
| BANC v2 vs v3 edgelist | Version pin | R9, optional |
| Root `README.md` status table stops at Phase 2.5 | Documentation, protected file | Requires explicit approval to edit; not changed here |

---

## 6. What “complete” means here

Phase 4 is **not** declared complete. The software requirements are complete and
tested; the project goal (“convert neural activity into game actions” from the
sensory pathway) is not demonstrated. The Phase 7 evidence supports E0–E2 only
(`PHASE_4H5`). Declaring success on the basis of passing tests would contradict
the project’s scientific-integrity rules.

---

## 7. Recommended next actions

1. Decide whether to acquire R3/R4 (functional sign and physiological
   calibration) and pre-register a propagation experiment that does not tune
   parameters to a desired outcome.
2. If ROLL/DUCK are required product features, treat them as blocked rather than
   approximating them with flexor pools.
3. Keep the optional selector off for reproduction of stored Phase 7/8 results;
   turn it on only for new, labelled analyses.
