# Phase 5B — Reward Signal and Reward Prediction Error

**Status:** complete
**Date:** 2026-11-09
**Repository:** FLY-SURFER
**Preceding phase:** 5A (approved architecture audit, M01–M13)
**Successful:** all declared 5B checks pass
**Scope:** reward representation, delayed delivery, reward prediction and
temporal-difference prediction error. No synapse, trace, weight or simulator
state is touched.

---

## 1. Purpose

Phase 5B supplies the scalar that a three-factor plasticity rule will later
multiply. It is deliberately a standalone layer:

- a reward is an external value defined by a task, not a measurement;
- a reward prediction error is the error of a declared value model;
- nothing in this layer can change a synaptic weight.

This separation is the first requirement of the approved Phase 5A
architecture (M01–M03) and it is what allows 5C and 5D to be tested without
the reward system being entangled with the plasticity engine.

---

## 2. Scientific status and non-claims

| Element | What it is | What it is not |
|---|---|---|
| `RewardEvent`, `RewardSchedule` | a scripted external scalar in task units | not a dopamine, octopamine or serotonin measurement |
| `ScriptedRewardProvider` | deterministic delivery of scheduled reward | not a neuromodulatory release model |
| `TabularValuePredictor` | a tabular temporal-difference value model | not a recorded reward-prediction signal |
| `delta_t` | arithmetic prediction error of that model | not a biological teaching signal |
| convergence of `V` | arithmetic consistency of the model | not evidence of learning in a brain |
| `RewardLogger` | an ordered record of model variables | not a neural recording |

The reward classification string is stored in both the configuration and every
result. Values are dimensionless task units; positive means a better task
outcome, negative a worse one, zero a neutral one.

---

## 3. Implemented interfaces

| ID | Interface | Implementation |
|---|---|---|
| M01 | reward signal representation | `plasticity/reward.py`: `RewardEvent`, `RewardSchedule`, `ScriptedRewardProvider` |
| M02 | reward predictor and RPE | `TabularValuePredictor`: `value`, `next_value`, `prediction_error`, `learn` |
| M03 | reward and learning log schema | `RewardPrediction`, `RewardLogger`; per-step step, time, reward, value, next value, prediction error, state, next state |

At the end of Phase 5B, `plasticity/__init__.py` exports only these classes
and helpers. It does not import `brain`, `motor`, the simulator or any Phase 4
module. Phase 5C later adds trace exports to the same package file; the reward
module itself stays unchanged.

### 3.1 Modules

```
plasticity/__init__.py     exports of the 5B layer only
plasticity/reward.py       reward, schedule, provider, predictor, logger,
                           statistics, shuffled control, config loading
configs/plasticity.yaml    reward, predictor, convergence and demonstration
                           sections (5A module map lists this file; 5C/5D add
                           their own sections)
```

### 3.2 Reward provider contract

```python
provider.step(step: int, time_ms: float, context=None) -> float
```

- returns the total magnitude whose delayed delivery time falls in
  `(previous_time, time_ms]`;
- starts at `-inf`, so an event scheduled at time 0 is delivered on the first
  step;
- requires non-decreasing, finite time;
- emits each event exactly once;
- `emitted_reward` and `reset()` support deterministic replays.

### 3.3 Predictor contract

```python
delta_t = r_t + gamma * V(s_{t+1}) - V(s_t)
V(s_t) <- clip(V(s_t) + learning_rate * delta_t, -bound, +bound)
```

- `gamma` and `learning_rate` are constrained to `[0, 1]`;
- a `None` next state is terminal and contributes zero future value;
- states are strings, integers or tuples of those;
- non-finite rewards and non-finite updates are rejected, never stored;
- the predictor is independent of any plasticity state.

---

## 4. Reward representation and delay

- Positive, negative and zero magnitudes are all accepted; zero-magnitude
  events are still logged (they are events, not absences).
- A schedule sorts events by nominal time and reports total, sign counts and
  a SHA-256 digest of its full description.
- `delay_ms` shifts every delivery time (`due = nominal + delay`) without
  changing magnitude order, totals or event identity. The provider receives
  no knowledge of the nominal time.
- A control helper `shuffled_reward_schedule` permutes magnitudes across the
  existing delivery times with an independent `numpy.random.Generator`. It is
  the 5E/5F shuffled-reward control.

---

## 5. Logging schema

Each `RewardPrediction` record stores:

| Field | Meaning |
|---|---|
| `step` | zero-based simulation step |
| `time_ms` | `(step + 1) * dt_ms` |
| `reward` | reward delivered on this step |
| `value` | `V(state)` **before** the update |
| `next_value` | `V(next_state)` used in the error |
| `prediction_error` | `delta_t`; zero on non-transition steps |
| `state` | current stage label |
| `next_state` | next stage label, `None` at a terminal transition |

`RewardLogger.to_dict()` adds totals, positive/negative/zero step counts,
mean and maximum absolute prediction error, and the record list. A SHA-256
digest over the ordered records makes replay equality checkable without
comparing every field.

---

## 6. Configuration

`configs/plasticity.yaml`, SHA-256
`1acaee386ba62653b6f604b63f2898b0a15a8c9c136958e3825925b5aae57fe5`.

| Block | Declared values |
|---|---|
| `reward.delay_ms_default` | 0.0 |
| `reward.schedules` | `positive_single`, `negative_single`, `zero_reward`, `mixed`, `delayed_mixed` |
| `delayed_mixed.delay_ms` | 50.0 |
| `predictor.defaults` | gamma 0.9, learning rate 0.2, initial value 0.0, bound 100.0 |
| `predictor.gamma_grid` | 0.0, 0.5, 0.9, 0.99 |
| `convergence` | schedule `mixed`, 400 episodes, tolerance 1e-3 |
| `demonstration` | dt 0.5 ms, 300 ms episodes, shuffle seed 20261111 |

The `mixed` schedule is `+1.0` at 80 ms, `-1.0` at 160 ms and `+0.5` at
240 ms (total 0.5). `delayed_mixed` uses the same magnitudes and nominal times
with a 50 ms delay.

All values were fixed before the run. The 5C and 5D sections will be appended
to the same file.

---

## 7. Validation

Run: `python -m experiments.phase_5.run_reward`
Result: `experiments/results/phase_5b/reward_system.json` (20,425 bytes)

### 7.1 Declared checks

| Check | Result | Evidence |
|---|---|---|
| reward signs | pass | +1.0 total positive; −1.0 total negative; 0.0 total zero |
| reward timing | pass | deliveries at 80.0, 160.0, 240.0 ms |
| single emission | pass | 3 nonzero-reward steps for 3 events |
| delayed reward | pass | deliveries at 130.0, 210.0, 290.0 ms |
| predictor convergence | pass | max error 0.0 for all four gamma values |
| numerical stability | pass | bounded, zero, negative, non-finite and overflow probes |
| determinism | pass | value and log digests reproduce exactly |
| logging | pass | 600 records for 600 steps; logged total equals episode total |
| shuffled control | pass | times, magnitudes and total preserved; digest changed |

`all_checks_passed: true`.

### 7.2 Convergence

The deterministic chain has three deliveries. For discount `gamma` the
analytic stage values are:

```
V(stage_2) = 0.5
V(stage_1) = -1.0 + gamma * 0.5
V(stage_0) =  1.0 + gamma * (-1.0 + gamma * 0.5)
```

After 400 episodes with learning rate 0.2:

| gamma | V(stage 0) | V(stage 1) | V(stage 2) | max abs error |
|---|---|---|---|---|
| 0.0 | 1.0 | −1.0 | 0.5 | 0.0 |
| 0.5 | 0.625 | −0.75 | 0.5 | 0.0 |
| 0.9 | 0.505 | −0.55 | 0.5 | 0.0 |
| 0.99 | 0.50005 | −0.505 | 0.5 | 0.0 |

The sampled curve for gamma 0.9 rises from (0.2, −0.2, 0.1) after episode 1
to the analytic values by episode 200 and is unchanged at episode 400.
Convergence is arithmetic convergence of the declared model, not learning in
a network.

### 7.3 Delay

With the same magnitudes delivered 50 ms later:

- the first delivery moves from step 159 to step 259, exactly 100 steps at
  0.5 ms per step;
- delivery times become 130.0, 210.0 and 290.0 ms;
- total reward is unchanged at 0.5;
- converged values equal the immediate-reward values exactly
  (`stage_0 = 0.505`, `stage_1 = -0.55`, `stage_2 = 0.5`).

The delay therefore changes when the error is computed, not what the chain
converges to. This is the property 5C will need when pairing delayed reward
with decaying traces.

### 7.4 Numerical stability

| Probe | Result |
|---|---|
| reward 1e6 with unit learning rate, bound 10 | value clipped to 10.0, finite |
| repeated tiny reward 1e-9, 10,000 updates | converges to 1e-9, finite |
| zero reward | values remain exactly 0.0 |
| negative reward | value −2.0, sign preserved |
| NaN / +inf reward | rejected with `ValueError` |
| update that would overflow float64 | rejected with `FloatingPointError`; stored value stays finite |
| value bound | enforced by clipping in `learn`, `load_state_dict` refuses out-of-bound values |

### 7.5 Determinism

| Digest | Value |
|---|---|
| learned values, gamma 0.9, run 1 | `7a42e5642e10febae13738b5c7c1d2e8b170a23ce974fa19decaa72dee237402` |
| learned values, gamma 0.9, run 2 | identical |
| 600-step episode log | `8bea469f4b79990eb12f519345536c4b53e34b259a96c529de68e5769e997862` |
| episode log replay | identical |

No randomness is used by the reward path. The only RNG is the explicitly
seeded shuffle control.

### 7.6 Logging correctness

- 600 records for a 600-step episode; first time 0.5 ms, last 300.0 ms.
- Total logged reward 0.5 equals the episode total.
- Sign accounting: 2 positive steps (`+1.0`, `+0.5`), 1 negative step
  (`−1.0`), 597 zero-reward steps.
- Mean absolute prediction error 0.000833333; maximum 1.0 (the first
  transition into the positive outcome).
- Every record carries all eight required fields; `next_state` is `None`
  exactly at the terminal transition.

### 7.7 Shuffled control

Seed 20261111 permutes `(+1.0, −1.0, +0.5)` to `(+0.5, −1.0, +1.0)` at the
same delivery times. Times, magnitude multiset and total are preserved and
the description digest changes. This helper is the control required by 5E
condition D; it has not yet been applied to a network.

---

## 8. Tests

| Suite | Result |
|---|---|
| `tests/test_plasticity_reward.py` (new) | **61 passed in 1.14 s** |
| focused regression (`test_plasticity_reward`, `test_configs`, `test_banc_simulator`) | **85 passed in 2.62 s** |
| full suite | **553 passed in 55.05 s** |

The 61 focused tests cover: field validation; sorting and sign counts; the
half-open delivery interval; delay application; event-at-zero delivery;
single emission; reset; monotonic time; hand-computed `delta_t`; terminal
value; learning-rate behaviour; sign preservation; clipping; parameter
validation; non-finite rewards; state keys; state round trip and digests;
analytic chain values; episode timing; convergence for gamma 0 and 0.9;
delay-invariant convergence; episode determinism; logger completeness and
order sensitivity; statistics; shuffle preservation; numerical probes;
configuration loading and rejection paths; and absence of imports from
`brain`, `motor`, `banc` or the simulator.

There was no change to any existing test.

---

## 9. Resources

| Measure | Value |
|---|---|
| runner wall time | 26.04 s |
| peak `tracemalloc` | 811,962 bytes (0.774 MB) |
| Python / NumPy | 3.13.14 / 2.3.4 |
| data touched | none — no graph, no simulation, no dataset |

The 26 s is dominated by 2,800 simulated episodes of 600 Python-level steps
(seven convergence runs). It is a validation cost, not a runtime model. The
reward layer itself is O(1) per step plus O(events) per delivery check.

---

## 10. Integrity

Phase 4H protected-file integrity: **37/37 unchanged** (including root
`README.md`, Phase 4H reports and results, datasets and processed
connectomes).

No file in `brain/`, `motor/`, `sensory/`, `perception/`, `experiments/phase_4*`
or the existing `tests/` was modified.

---

## 11. Files created and modified

Created:

- `plasticity/__init__.py`
- `plasticity/reward.py`
- `configs/plasticity.yaml`
- `experiments/phase_5/run_reward.py`
- `experiments/results/phase_5b/reward_system.json`
- `tests/test_plasticity_reward.py`
- `reports/PHASE_5B_REWARD_SYSTEM.md`
- `reports/PHASE_5B_REWARD_SYSTEM.json`

Modified: none.

No commit or push was made.

---

## 12. Limitations

1. Reward is a scripted computational scalar. It is not a neuromodulator
   measurement and carries no biological units.
2. The predictor is one tabular model with hand-declared parameters. Other
   value models would produce different errors.
3. Convergence proves arithmetic consistency and temporal credit assignment
   in this model. It does not demonstrate learning by any network.
4. The schedule is finite and deterministic; arbitrary reward distributions,
   partial observability and stochastic outcomes are not modelled here.
5. The delayed-reward result shows timing invariance of the *model*; whether
   a biological system can bridge a 50 ms delay is not addressed.
6. The shuffled control has only been validated as a schedule operation, not
   yet applied to a learning run.

---

## 13. Exit criteria

| 5B requirement | Status |
|---|---|
| reward signal representation | implemented (`RewardEvent`, `RewardSchedule`) |
| positive, negative and zero reward | implemented and tested |
| delayed reward with configurable timing | implemented and tested |
| configurable magnitude | implemented (per-event magnitudes) |
| reward predictor | implemented (`TabularValuePredictor`) |
| temporal-difference RPE | implemented and hand-verified |
| configurable discount | gamma grid 0.0–0.99 verified |
| reward logging | implemented with deterministic digest |
| deterministic behaviour | verified by repeated digests |
| predictor separate from plasticity | enforced by module imports and tests |
| module, config, tests, runner, reports | all delivered |

Phase 5B passes. Proceeding to Phase 5C (eligibility traces).
