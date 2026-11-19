# Phase 4 — Completion Matrix (nine original requirements)

**Date:** 2026-11-17
**Authoritative scope:** the original Phase 4 task list — “Motor System: Convert
neural activity into game actions” — with its nine tasks and four completion
criteria.
**Classification rule:** a row is `Complete` only when the code exists, is
reachable from the integration path, and is covered by a focused test. A row is
`Complete with limitations` when the software is complete but the scientific
claim it enables is not established. A row is `Blocked` when a missing external
resource prevents the requirement itself.

---

## 1. Status summary

| # | Original requirement | Status | Implementation | Evidence | Tests |
|---|---|---|---|---|---|
| 1 | Investigate descending pathways | **Complete** | analysis only (`experiments/phase_4e`, `brain/banc_graph.py`) | `reports/PHASE_4B…`, `PHASE_4E…`, `PHASE_4_MOTOR_PATHWAY_REPORT.md` | `tests/test_phase_4e_pathways.py`, `tests/test_banc_graph_*` |
| 2 | Identify relevant neuronal populations | **Complete with limitations** | `motor/populations.py` | 185 LEFT / 186 RIGHT / 20 JUMP; 414 unassigned; ROLL/DUCK unsupported | `tests/test_motor_populations.py` |
| 3 | Investigate motor annotations | **Complete with limitations** | analysis only | 805 MN, 805 proofread, 197 missing peripheral target, 30 verified NT | `tests/test_motor_populations.py`, `test_phase_4e_pathways.py` |
| 4 | Design an experimental motor mapping | **Complete with limitations** | `configs/motor_decoder.yaml`, `motor/action_decoder.py` | Declared before experiments; documented as hypothesis | `tests/test_motor_decoder.py`, `test_motor_decoder_experiment.py` |
| 5 | Implement action decoding | **Complete** | `motor/action_decoder.py`, `motor/motor_decoder.py` | Active-fraction decoder with gates; deterministic output | `tests/test_motor_decoder.py`, `test_motor_output_pipeline.py` |
| 6 | Add action thresholds | **Complete** | decoder (`activation_threshold`, `release_threshold`, `min_spikes`, `min_active_neurons`) | 0.20 / 0.10 / 5 / 3 | `tests/test_motor_decoder.py` |
| 7 | Prevent conflicting simultaneous actions | **Complete** | decoder arbitration + `motor/action_selection.py` | `decoder_primary`, `priority`, `suppress_all`; recorded suppressed channels | `tests/test_phase_4_action_selection.py`, `test_phase_4_game_controller.py` |
| 8 | Add action timing constraints | **Complete** | `motor/action_selection.py`, `environment/game_controller.py` | `min_hold_ms`, per-action `cooldown_ms`, monotone time, immediate neutral release | same |
| 9 | Test the complete sensory-to-motor loop | **Implemented and executed; functional outcome not achieved** | `environment/live_loop.py` (`NeuralClosedLoop`), Phase 7 runner | Phase 7: 213 updates, 2,852 spikes all sensory, 0 motor, 213 `NO_ACTION`; 4H5 E0–E2 only | `tests/test_phase_7_neural_closed_loop.py`, `test_phase_7_environment.py`, `test_end_to_end_pipeline.py` |

---

## 2. Requirement 9 in detail

“Test the complete sensory-to-motor loop” has two halves, and they separate
cleanly:

| Half | Result |
|---|---|
| **Software loop is complete and exercised** | Game observation → sensory encoding → BANC simulation → Phase 4 decoder → action selection → game step → next observation. Every stage is called on every update; records, rewards, timing and determinism are verified. |
| **Neural loop recruits motor neurons** | **Not achieved in this model configuration.** No non-stimulated neuron spikes; motor pools receive no current; every decode is NEUTRAL / `NO_ACTION`. |
| **Is the negative result an execution bug?** | No. Identical input hashes, hash-equal replays, and a controlled positive control (4G5 condition C: 492 motor spikes, 4 JUMP windows) show the decoder and controller work when motor activity exists. |
| **Is it a biological conclusion?** | No. It is a controlled negative result about one simulator configuration, not a statement about the fly. |

The stop point is quantified in
`reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md`.

---

## 3. Four original completion criteria

| Criterion | Meaning | Verdict |
|---|---|---|
| 1. Valid game actions are produced | The decoder can emit LEFT/RIGHT/JUMP and the game validates them | **Met under controlled motor drive** (4F, 4G5, 4H.1–4H.3). **Not met from sensory propagation** in the Phase 7 configuration. |
| 2. Selection is reproducible | Same inputs, same output | **Met.** Hash-equal replays; deterministic tie-break, priority and time ordering; `fingerprint` in every episode. |
| 3. Controller handles timing | Windows, holds, cooldowns, invalid/unmapped outputs, neutral | **Met.** `ActionSelector` + `GameController`; 42 focused tests. |
| 4. Sensory and motor systems run together | One loop, fixed weights, no manual intervention | **Met structurally; motor recruitment not achieved.** Phase 7 executed the full loop; the neural result is the documented negative. |

---

## 4. Newly implemented in this task (closing the gap)

Before this task the repository had a decoder but **no action-selection module
and no controller**; `environment/game_controller.py` was a one-line docstring
and the roadmap path `src/fly_surfer/motor/action_selection.py` did not exist in
this repository layout.

| File | Change | What requirement it completes |
|---|---|---|
| `motor/action_selection.py` | New: `SelectionConfig`, `ActionSelection`, `ActionSelector` | 7 (conflict prevention, priority, suppression) and 8 (min-hold, cooldown, monotone time) |
| `environment/game_controller.py` | New: `GameController`, `ControllerCycle` | 7–9 (decode → select → map → step binding) |
| `environment/live_loop.py` | Optional `action_selector` in `NeuralClosedLoop` | 9 (selection inside the real sensory→BANC→game loop) |
| `environment/__init__.py`, `motor/__init__.py` | Exports and package docstrings | Integration surface |
| `tests/test_phase_4_action_selection.py` | 24 synthetic tests | 7, 8 |
| `tests/test_phase_4_game_controller.py` | 18 synthetic tests | 5–9 (controller path) |
| `tests/test_phase_7_neural_closed_loop.py` | Optional-selector integration test | 9 |

Nothing else was changed: decoder thresholds, weights, sensory currents, graph
structure and simulation parameters are untouched.

---

## 5. What is deliberately **not** complete

| Item | Why | Blocking external resource |
|---|---|---|
| ROLL channel | No roll motor population in the export | Action-specific motor annotation (R1 in the missing-resource inventory) |
| DUCK channel | No duck/crouch population | Same (R2) |
| Sensory features mapped to verified sensory pathways | Feature→population assignment is a convention/hypothesis | Sensory ground truth (R5) |
| Motor recruitment from sensory input | Activity stops at the subthreshold first hop | Physiological sign/weight calibration (R3, R4) |
| Claim that a decoded action is a fly motor command | Annotation does not identify commands | Behavioural/functional validation (R6) |
| Unassigned 414 motor neurons | Outside the declared rules | Additional annotation/physiology (R7) |

---

## 6. Overall Phase 4 verdict

**PARTIALLY COMPLETE — implementation complete, functional demonstration
blocked on external evidence.**

- All nine requirements now have an implementation, a declared rule set and
  focused tests.
- Requirement 9’s software path is complete and was executed end to end.
- The original goal — “convert neural activity into game actions” from sensory
  input — is **not demonstrated** by this model. The only positive motor output
  in the project comes from experimenter-injected current into motor pools or
  VNC intrinsics, not from the sensory pathway.
- Declaring Phase 4 complete on the strength of passing software tests would
  overstate both the biology and the integration result. The correct statement
  is: *Phase 4’s motor software is complete; its sensory-to-motor function is a
  controlled negative pending the resources listed in the inventory.*
