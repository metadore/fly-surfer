# Phase 4 — Implementation Report

**Date:** 2026-11-17
**Repository:** `C:\Users\Hp\fruitfly\FLY-SURFER`
**Task:** implement and complete the original Phase 4 “Motor System” requirements
against the existing repository, without rewriting valid work and without
changing scientific parameters.

---

## 1. What already existed

| Component | File | State at start |
|---|---|---|
| BANC graph loader and artifacts | `brain/banc_graph.py`, `datasets/processed/banc_v888/` | Complete, hash-verified (Phase 4D) |
| Population construction | `motor/populations.py` | Complete: LEFT 185, RIGHT 186, JUMP 20; 414 unassigned; ROLL/DUCK unsupported |
| Decoder | `motor/action_decoder.py`, `motor/motor_decoder.py` | Complete: 50 ms windows, active-fraction score, 0.20/0.10 thresholds, evidence gates, priority, arbitration, optional smoothing/hysteresis |
| Motor activity recorder | `motor/activity_recorder.py` | Complete |
| Action adapter | `environment/action_adapter.py` | Complete: maps decoder states to game actions; `UNMAPPED`/`DUCK` → `NO_ACTION` |
| Live loop | `environment/live_loop.py` | Complete: sensory drive, BANC stepper, decoder, game step, records, determinism |
| Phase 4 experiments and reports | `experiments/phase_4{e,f,g,h}`, `reports/PHASE_4*` | Complete |
| Phase 7/8 integration | `environment/`, `experiments/phase_7`, `experiments/phase_8` | Complete and frozen |

The audit also confirmed what was **not** present: there was no action-selection
module and no controller class. `environment/game_controller.py` contained only
a one-line docstring. The roadmap path `src/fly_surfer/motor/action_selection.py`
does not exist in this repository layout; the equivalent module now lives at
`motor/action_selection.py`.

---

## 2. What was missing and why it mattered

| Original requirement | Before | Consequence |
|---|---|---|
| 7. Prevent conflicting simultaneous actions | Decoder reported `active_actions` and a `primary_action`, but nothing suppressed or held conflicting channels across time | The same record could request two pools; no policy object, no suppression accounting |
| 8. Add action timing constraints | No minimum hold, no cooldown, no cross-update time validation | Rapid switching was unconstrained |
| Controller binding | No class existed | Decode → select → map → step was assembled ad hoc per experiment |
| End-to-end selection | Not part of `NeuralClosedLoop` | Phase 7 records had no selection audit trail |

---

## 3. What was implemented

### 3.1 `motor/action_selection.py` (new)

- `NO_ACTION`, `UNMAPPED`, `NEUTRAL` constants; `CONFLICT_POLICIES =
  ("decoder_primary", "priority", "suppress_all")`.
- `SelectionConfig` (frozen dataclass): `conflict_policy`, `priority`
  (permutation of LEFT/RIGHT/JUMP), `min_hold_ms`, `cooldown_ms`;
  validation of finite non-negative times and unknown keys;
  `from_config(payload)` and `describe()`.
- `ActionSelection` (frozen dataclass): requested/candidate/selected state,
  active channels, conflict flag and policy, suppressed channels, `held`,
  `cooldown_blocked`, `cooldown_remaining_ms`, `supported`, `unmapped`, `reason`;
  `as_dict()` with rounded times; `neutral` property.
- `_read_output`: accepts `MotorOutput`, mapping, object or string; validates
  windows are finite; never crashes on malformed output.
- `ActionSelector.select(output, *, window_end_ms)`:
  - invalid/unknown/unsupported (`ROLL`, `DUCK`) → `NO_ACTION` with explicit
    reason and `supported=False`;
  - `NO_ACTION`/`NEUTRAL` → immediate release (no hold, no cooldown);
  - conflict resolution by decoder primary, fixed priority, or suppress-all;
  - minimum hold delays a switch to a different non-neutral action;
  - per-action cooldown starts when an action is **left**; continuing the same
    action is never blocked;
  - time may not move backwards; equal timestamps are deterministic;
  - `reset()` clears selected state and history.

### 3.2 `environment/game_controller.py` (new)

- `ControllerCycle(output, selection, mapping)` with `as_dict()`.
- `GameController(decoder, *, selector=None, adapter=None, selection_config=None)`:
  validates the decoder and selector interfaces; rejects supplying both a
  selector and a config; exposes `n_neurons`, `reset()`, `advance(...)` (decode
  a spike window then select), `advance_output(...)` (select an existing motor
  output), and `step(environment, cycle)`; `describe()` publishes the pipeline
  `decode_window → select → map → environment.step`.
- `advance_output` maintains `_last_time_ms` as a fallback window end so outputs
  without timestamps are handled deterministically instead of raising.

### 3.3 Optional integration in `environment/live_loop.py`

- New keyword `action_selector=None` on `NeuralClosedLoop`; validated for
  `select`/`reset`; reset at episode start.
- After the decoder produces its decision, the selector runs with the neural
  window end; the selected state (or the original requested state when
  unmapped) is passed to the action adapter.
- A `"selection"` field is added to a record **only when a selector is
  supplied**. Default Phase 7/8 records therefore keep their exact frozen field
  set.
- When a selector is present, the summary gains a compact `selection` block
  (updates, conflicts, held updates, cooldown-blocked updates, unmapped updates,
  suppressed-channel counts).

### 3.4 Package surface

- `motor/__init__.py` documents the package split: populations, decoder,
  selection in `motor/`; game binding in `environment.game_controller`.
- `environment/__init__.py` exports `ControllerCycle` and `GameController`.

---

## 4. Backward compatibility

| Consumer | Effect |
|---|---|
| Phase 7 closed loop | No selector → identical records, summary and fingerprint; 16 tests pass |
| Phase 8 conditions (A–F) | No selector → identical record schema; 325 focused tests pass |
| Existing decoder API | Unchanged; `ActionSelector` consumes its output |
| Existing adapter | Unchanged |
| Frozen artifacts | Not read or written by the new code |

No decoder threshold, weight, sensory current, graph edge, neuron parameter or
game rule was modified.

---

## 5. Tests

| File | Tests | What it covers |
|---|---:|---|
| `tests/test_phase_4_action_selection.py` | 24 | Config validation, neutral, single/continuing action, all three conflict policies, hold and expiry, immediate neutral release, cooldown block/expiry, continuing-action exemption, ROLL/DUCK, UNMAPPED, unknown state, malformed outputs, time monotonicity, deterministic replay, reset |
| `tests/test_phase_4_game_controller.py` | 18 | Decoder → selector → adapter → game: subthreshold, LEFT, conflict, suppress-all, ROLL, DUCK, malformed output, hold across real decoder windows, neutral release, identical replay, reset, component validation, pipeline description |
| `tests/test_phase_7_neural_closed_loop.py` | +1 (16 total) | Optional selector inside the real loop; per-record `selection`; field-set equality with `RECORD_FIELDS`; weights unchanged |

All tests are **synthetic** where they inject activity. They demonstrate
mechanics and determinism, not BANC motor function.

Commands and results:

```
python -m pytest tests/test_motor_decoder.py tests/test_motor_populations.py \
  tests/test_motor_output_pipeline.py tests/test_motor_decoder_experiment.py \
  tests/test_phase_4_action_selection.py tests/test_phase_4_game_controller.py \
  tests/test_phase_4e_pathways.py tests/test_phase_4h4_analysis.py \
  tests/test_phase_4h5_assessment.py tests/test_phase_4h_runners.py \
  tests/test_phase_7_environment.py tests/test_phase_7_neural_closed_loop.py -q
# 193 passed

python -m pytest tests/test_phase_8_conditions.py tests/test_phase_8_controls.py \
  tests/test_phase_8_readout.py tests/test_phase_8_live_plastic_stepper.py \
  tests/test_phase_8_viability.py tests/test_phase_8_campaign_skeleton.py \
  tests/test_phase_8_analysis.py tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_random_campaign.py tests/test_phase_8_random_certification.py \
  tests/test_phase_8_random_target_exchange.py tests/test_phase_8_training_artifacts.py \
  tests/test_phase_8_conventional_learner.py -q
# 325 passed
```

---

## 6. Usage

```python
from motor.action_selection import ActionSelector, SelectionConfig
from environment.game_controller import GameController
from environment.action_adapter import GameActionAdapter

selector = ActionSelector(SelectionConfig(
    conflict_policy="priority",
    min_hold_ms=100.0,
    cooldown_ms=200.0,
))
controller = GameController(
    decoder,
    selector=selector,
    adapter=GameActionAdapter(),
)
cycle = controller.advance(times, indices, start_ms, end_ms)
step = controller.step(environment, cycle)
```

Inside the real loop:

```python
loop = NeuralClosedLoop(..., action_selector=selector)
result = loop.run(seed=42)
```

---

## 7. Limitations introduced by this work

1. The selector is a **computational policy**. `min_hold_ms` and `cooldown_ms`
   are declared constants, not measured fly timing.
2. `decoder_primary` assumes the decoder’s `primary_action` is meaningful; when
   the decoder returns simultaneous actions, the choice is still a convention.
3. The integration is opt-in; existing Phase 7/8 results were produced without
   it and remain valid only as fixed-weight baselines.
4. Selection cannot create motor activity. In the Phase 7 configuration the
   input to the selector is `NO_ACTION` on every update.

---

## 8. Verdict

The missing **software** requirements (7, 8 and the controller binding for 9)
are implemented, integrated optionally, and covered by focused tests. The
**scientific** goal of converting sensory-driven neural activity into game
actions is not achieved; that is a model/evidence limitation documented in
`reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md` and
`reports/PHASE_4_MISSING_RESOURCES.md`.

Phase 4 overall: **partially complete** — implementation complete, functional
demonstration blocked on external evidence.
