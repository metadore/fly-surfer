# Phase 7 — Controlled game environment integration

Status: implemented and demonstrated. No Phase 8 training, no real Subway
Surfers integration and no changes to frozen Phase 3–6 artifacts.

## What was integrated

The standalone `metadore/endless-surfer` game is used as-is. FLY-SURFER adds a
thin wrapper and three adapters:

| File | Role |
| --- | --- |
| `environment/endless_surfer.py` | finds the game (`FLY_SURFER_GAME_ROOT` or `external/` candidates) and imports its public API once |
| `environment/game_state.py` | game observation (schema v1) → existing Phase 3 `GameState` |
| `environment/action_adapter.py` | Phase 4 motor state → documented game action |
| `environment/reward_function.py` | game `reward_components` → Phase 5 `RewardDelivery` / `RewardEvent` / `RewardStream` |
| `environment/subway_environment.py` | stable `reset(seed)` / `step(action)` interface |
| `environment/environment_adapter.py` | end-to-end adapter, episode runner and `SensoryInputScheduler` timeline |

The game still owns mechanics, spawning, collision and reward rules. FLY-SURFER
does not recompute the reward; `GameRewardFunction.for_step` verifies that the
game's components sum to its returned scalar and records provenance.

## Interfaces

```python
observation = environment.reset(seed=42)
observation, reward, terminated, truncated, info = environment.step(action)
```

`info["fly_surfer"]` adds the converted `GameState`, the requested/executed
action, the step reward components/provenance and the seed. The game's original
`info` keys are preserved.

Mapping rules:

- `LEFT`, `RIGHT`, `JUMP`, `ROLL`, `NO_ACTION` pass through unchanged.
- `UNMAPPED` and `DUCK` execute `NO_ACTION`; no unsupported state becomes a
  different action. Unknown or invalid motor outputs also execute `NO_ACTION`
  with a recorded reason.
- `BARRIER → LOW`, `OVERHEAD → HIGH`, `TRAIN → train`; the nearest visible
  object of each kind is represented, extras are reported as unrepresented.
- Distances are world units divided by the declared 25.0-unit observation
  horizon; they are not metric distances. Only currently visible objects are
  used; no future obstacle position exists in the observation.

## Demonstrated episodes

All runs are fixed-seed, headless, recorded and replayed with the game's own
strict `replay()`. Results are in
`experiments/results/phase_7/game_integration_demo.json`
(sha256 `be27dda6…22ebed2`; the digest includes the run's `generated_at_utc`
timestamp, so re-running the demo changes only that field and the digest).

| Agent | Seed | Steps | End | Score | Coins | Collisions | Total reward |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| random | 42 | 213 | collision | 5.55 | 2 | 1 | 3.12 |
| random | 7 | 332 | collision | 7.53 | 2 | 1 | 4.31 |
| random | 123 | 218 | collision | 4.63 | 1 | 1 | 2.17 |
| rule_based | 42 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| rule_based | 7 | 531 | collision | 16.85 | 8 | 1 | 12.30 |
| rule_based | 123 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| phase4 replay | 42 | 300 | time limit | 8.00 | 3 | 0 | 6.00 |
| phase4 replay | 7 | 300 | time limit | 5.00 | 0 | 0 | 3.00 |

Phase 4 action distribution (300-step replay): `JUMP=200`, `NO_ACTION=100`.
`ROLL` requests from the recorded decoder output are `UNMAPPED` and execute
`NO_ACTION`.

Concrete events:

- Coin: rule-based seed 42, step 111, 1850 ms, +1.01
  (`coin_collection=1.0`, `survival_reward=0.01`).
- Collision: rule-based seed 42, step 432, 7200 ms, −1.0
  (`collision_penalty=-1.0`, no survival reward on the terminal step).
- Truncation: rule-based seed 42 with `max_steps=100`, `time_limit`.
- Phase 5 check: the recorded `RewardStream` replayed through the existing
  `ModulationRewardProvider` and `ScriptedRewardProvider` reproduces the game
  reward total exactly for every condition.

All demo checks true: `all_replays_ok`, `all_reproducible`, `all_headless`,
`all_rewards_match_phase5`.

## Tests

Focused Phase 7 tests (`tests/test_phase_7_environment.py`): 19 passed.

Game repository tests: 19 passed (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`).

Full FLY-SURFER suite: **1012 passed, 3 skipped, 6 failed**. All six failures
are the pre-existing README integrity pins, unrelated to Phase 7:

- `test_causal_control.py::test_smoke_100ms_runs_every_condition`
- `test_causal_control.py::test_c0_only_full_mode_requires_no_cache`
- `test_feature_ablation.py::test_smoke_window_never_invokes_the_archive_gate`
- `test_integration_3b_3c.py::test_protected_artifacts_unchanged`
- `test_p3_3c5_lane_encoding.py::test_source_and_protected_hashes_are_recorded`
- `test_p3_3c5_lane_encoding.py::test_static_gates_cover_groups_reversal_pools_and_hashes`

Cause: commit `efd3a3e` (“Merge remote README title update…”) changed
`README.md`; the repository pins the previous README hash
`8ab6a8cc…` in `configs/causal_control_config.yaml` and the Phase 3C freeze
records. Current hash is `8a79d44d…`. The working tree README equals `HEAD`.
No frozen artifact, protocol pin or test was modified to hide this.

## Commands

```bash
python experiments/phase_7/run_game_episode.py --agent random --seed 42 --max-steps 900
python experiments/phase_7/run_game_episode.py --agent rule_based --seed 42 --max-steps 900 --record episode.json
python experiments/phase_7/run_game_episode.py --agent phase4 --seed 42 --max-steps 300
python experiments/phase_7/run_game_episode.py --agent rule_based --visual
python experiments/phase_7/run_integration_demo.py
python -m pytest tests/test_phase_7_environment.py -q
```

Declared assumptions are in `configs/phase_7_environment.yaml`.

## Limitations

- The reward is a synthetic task reward defined by the game rules; it is not a
  biological dopamine, octopamine or serotonin measurement. The game's survival
  component is reported exactly as configured.
- Phase 4 records are replayed open loop; no BANC simulation runs during the
  Phase 7 episodes.
- Distance normalisation is an experiment convention, not a calibration.
- Visual mode was smoke-tested with the SDL dummy driver; equal outcomes with
  and without rendering are covered by a test. A human-observed interactive
  window was not available in this environment.
- No learning, Phase 8 training or real Subway Surfers integration was started.
