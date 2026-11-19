# Phase 4 — Motor Population and Mapping Evidence Table

**Date:** 2026-11-17
**Purpose:** One table that states, for every Phase 4 action channel, exactly what
the mapping is derived from, how strong that evidence is, and where the mapping
stops. This report consolidates `reports/PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.md`,
`reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md`, `configs/motor_decoder.yaml` and
the code in `motor/populations.py` and `motor/action_decoder.py`.
**Status:** descriptive only; nothing was tuned or re-run to produce it.

---

## 1. The five channels and their evidence

| Channel | Pop. size | Rule (published annotation columns only) | Evidence class | Decoder meaning | Mapping status |
|---|---:|---|---|---|---|
| **LEFT** | 185 | `super_class == motor` ∧ `side == left` ∧ `body_part_effector ∈ {front_leg, middle_leg, hind_leg}` ∧ `peripheral_target_type ≠ tergotrochanter_extensor_muscle` | Anatomically identified neurons grouped by expert annotation | Left leg motor pool active | Implemented; **label, not verified command** |
| **RIGHT** | 186 | Mirror of LEFT with `side == right` | Same | Right leg motor pool active | Implemented; **label, not verified command** |
| **JUMP** | 20 | `super_class == motor` ∧ `peripheral_target_type == tergotrochanter_extensor_muscle` | Anatomically identified jump-extending motor neurons | Tergotrochanter extensor pool active | Implemented; **candidate pool, not a jump command** |
| **ROLL** | 0 | No published annotation in this export defines a roll motor population | — | — | **Unsupported; no proxy invented** |
| **DUCK** | 0 | No published annotation defines a duck/crouch population | — | — | **Unsupported; no proxy invented** |
| **NO_ACTION** | — | Decoder neutral state | Computational | No pool above threshold | Implemented |
| **UNMAPPED** | — | Decoder error/unknown state | Computational | Adapter executes `NO_ACTION` and records why | Implemented |

Population total: **391 assigned** of 805 motor neurons; **414 remain
UNASSIGNED**. The decoder never reports UNASSIGNED as an action and never
promotes an unassigned motor neuron into a pool.

The 20 tergotrochanter neurons are also leg motor neurons. They are removed from
LEFT/RIGHT by the `jump_membership_in_leg_pools: false` default so the three
populations are disjoint and JUMP spikes are not double counted. Setting it to
true is supported by the code but is not the project configuration.

---

## 2. Why the three labels are disjoint and reproducible

| Property | Implementation | Test |
|---|---|---|
| Membership depends only on node-table annotations | `motor/populations.py` reads only `super_class`, `side`, `body_part_effector`, `peripheral_target_type` | `tests/test_motor_populations.py` |
| No edge, simulator state or predicted transmitter changes membership | `PopulationOptions` has no connectivity input | same |
| Deterministic order | Masks are boolean arrays in graph node-index order | same |
| Unassigned neurons are reported, not forced | `unassigned_mask`, `composition`, `provenance` | same |
| Config matches code | `configs/motor_decoder.yaml` | `tests/test_motor_decoder_experiment.py` |

---

## 3. Decoder mapping: annotation pool → score → action

| Stage | Definition | Where |
|---|---|---|
| Window | Half-open `[start_ms, end_ms)`, default 50 ms, stride 50 ms | `configs/motor_decoder.yaml`, `motor/action_decoder.py` |
| Score | `active_neurons_in_window / population_size`, in [0, 1] | `motor/action_decoder.py` |
| Evidence gate | ≥ 5 spikes and ≥ 3 active neurons in the window | same |
| Activation | `score ≥ 0.20` (or `≥ 0.10` when hysteresis holds a previously active pool) | same |
| Arbitration | `all_above_threshold` (default) or `single`; priority `LEFT, RIGHT, JUMP` | same |
| Tie-break | Score first, then fixed priority; tolerance 1e-9 | same |
| Neutral | No pool passes → `NO_ACTION` | same |
| Conflict handling | `ActionSelector` (`decoder_primary`, `priority`, `suppress_all`) | `motor/action_selection.py` |
| Timing | `min_hold_ms`, per-action `cooldown_ms` | `motor/action_selection.py` |
| Game binding | `ActionSelector` → `ActionMapping` → environment step | `environment/game_controller.py`, `environment/action_adapter.py` |

The activation and release thresholds were declared **before** any experiment
(`PHASE_4F` §6) and are not fitted to a successful example. No Phase 4 run
changed them.

---

## 4. Evidence strength by claim

| Claim | Supported? | Basis |
|---|---|---|
| Leg motor neurons exist, sided, annotated by effector | **Yes** | Published annotation, 805/805 proofread |
| A tergotrochanter extensor motor pool exists | **Yes** | 20 annotated candidates, all with direct and two-hop DN input |
| LEFT/RIGHT/JUMP pools can be scored deterministically | **Yes** | 4F controlled experiment, 4G5, 4H |
| Pool activity is caused by the descending pathway | **Only under controlled drive** | 4G5 condition C is direct VNC-intrinsic stimulation, not sensory propagation |
| Pool activity encodes a left/right/jump *command* | **No** | No command annotation exists; lateral input is predominantly bilateral and cross-side |
| ROLL/DUCK can be decoded | **No** | No annotation; not implemented |
| The 414 unassigned motor neurons have no role | **Unknown, not “no role”** | Unannotated by the rules used; the decoder is silent about them |
| Predicted transmitter equals functional sign | **No** | 30/805 verified; unknown edges excluded |
| Decoded action is a biological motor command | **No** | Decoder labels are computational constructs |

---

## 5. Annotation completeness relevant to the mapping

| Field / group | Value | Consequence |
|---|---:|---|
| Motor neurons | 805 | All proofread |
| `body_part_effector` populated | 805/805 | Effector grouping is complete |
| `side` populated | 805/805 | Sided pools are complete |
| `peripheral_target_type` populated | 608/805 | **197 missing**; JUMP rule depends on this field, so a missing value cannot be a JUMP member |
| Verified neurotransmitter | 30/805 | Sign is a prior for the other 775 |
| `LR_TYPE_CONFLICT` in tergotrochanter pool | 8/20 | Jump pool is not a clean type set |
| Motor neurons without direct DN input | 167/805 | Some pools cannot be driven monosynaptically at t5 |
| Descending neurons without motor target | 563/1,316 | A large DN set has no direct motor output |

---

## 6. Explicit statements

1. **LEFT, RIGHT and JUMP are decoder labels.** They name annotation-defined
   motor pools. They are not identified biological commands for lane change,
   jump or any other behaviour.
2. **The mapping is a hypothesis with declared rules**, not a measured
   sensorimotor transformation.
3. **No neuron was assigned to an action by hand.** Every member follows from a
   published annotation predicate.
4. **No ROLL or DUCK population was invented.** Unsupported states are recorded
   as unsupported and execute `NO_ACTION`.
5. **Synthetic decoder tests demonstrate mechanics, not biology.** They drive
   the pools with injected current (`tests/test_motor_*.py`); they are not
   evidence that BANC produces these actions.
6. **The 414 unassigned motor neurons are outside the decoder’s scope.** Any
   statement about them would require additional annotation or physiology.
