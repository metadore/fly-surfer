"""Controlled endless-runner environment the fly brain can drive.

This is a thin, stable wrapper around the standalone ``endless-surfer`` game.
The game owns mechanics, physics, spawning, collision and reward rules; this
module owns only the FLY-SURFER-facing integration:

``reset(seed)`` returns the game observation;
``step(action)`` returns ``(observation, reward, terminated, truncated, info)``
and extends ``info`` with the converted Phase 3 ``GameState``, the Phase 4
action mapping and the Phase 5 reward provenance.

Rendering is opt-in through :meth:`render` and never changes the simulation:
the game advances on its fixed ``1/60`` s timestep regardless of frame rate.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from environment.action_adapter import ActionMapping, GameActionAdapter, GAME_ACTIONS
from environment.endless_surfer import GameAPI, load_game_api
from environment.game_state import (
    DEFAULT_DISTANCE_HORIZON,
    GameObservationAdapter,
    ObservationConversion,
)
from environment.reward_function import (
    GameRewardFunction,
    REWARD_CLASSIFICATION,
    StepReward,
)
from motor.action_decoder import MotorOutput
from sensory.game_state import GameState


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


class ControlledGameEnvironment:
    """Game observation/action interface with FLY-SURFER adapters attached."""

    def __init__(
        self,
        config: Any = None,
        *,
        game_root: str | Path | None = None,
        max_steps: int | None = None,
        render_mode: str | None = None,
        distance_horizon: float = DEFAULT_DISTANCE_HORIZON,
        api: GameAPI | None = None,
    ) -> None:
        self.api = api or load_game_api(game_root)
        if config is None:
            config = self.api.default_config()
        elif isinstance(config, (str, Path)):
            config = self.api.load_config(config)
        elif not isinstance(config, self.api.difficulty):
            raise ValueError(
                "config must be a Difficulty, a configuration path or None"
            )
        if max_steps is not None:
            config = replace(config, max_steps=_positive_int(max_steps, "max_steps"))

        self.config = config
        self.render_mode = render_mode
        self.env = self.api.environment(config, render_mode=render_mode)
        self.observation_adapter = GameObservationAdapter(
            max_speed=config.max_speed, distance_horizon=distance_horizon
        )
        self.action_adapter = GameActionAdapter()
        self.reward_function = GameRewardFunction()

        self._renderer = None
        self._seed: int | None = None
        self._step_index = 0
        self._recorder = None
        self._conversions: list[ObservationConversion] = []
        self._last_mapping: ActionMapping | None = None
        self._last_step_reward: StepReward | None = None
        self._last_info: dict | None = None

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------

    @property
    def seed(self) -> int | None:
        return self._seed

    @property
    def n_steps(self) -> int:
        return self._step_index

    @property
    def conversions(self) -> tuple[ObservationConversion, ...]:
        return tuple(self._conversions)

    @property
    def game_state(self) -> GameState:
        if not self._conversions:
            raise RuntimeError("call reset() before reading the game state")
        return self._conversions[-1].state

    @property
    def last_mapping(self) -> ActionMapping | None:
        return self._last_mapping

    @property
    def last_step_reward(self) -> StepReward | None:
        return self._last_step_reward

    @property
    def last_info(self) -> Mapping[str, Any] | None:
        return self._last_info

    @property
    def recording_data(self) -> dict | None:
        return None if self._recorder is None else self._recorder.data

    # ------------------------------------------------------------------
    # interface
    # ------------------------------------------------------------------

    def reset(self, seed: int | None = None) -> Mapping[str, Any]:
        observation = self.env.reset(seed)
        self._seed = int(self.env.seed)
        self._step_index = 0
        self._conversions = [self.observation_adapter.convert(observation)]
        self.reward_function.reset()
        self._recorder = self.api.recorder(self.env)
        self._last_mapping = None
        self._last_step_reward = None
        self._last_info = None
        return observation

    def _map_action(self, action: Any) -> tuple[ActionMapping, Any]:
        if isinstance(action, ActionMapping):
            return action, action.executed_action
        if isinstance(action, (MotorOutput, Mapping)):
            mapping = self.action_adapter.map(action)
            return mapping, mapping.executed_action
        text = action.value if isinstance(getattr(action, "value", None), str) else action
        text = text if isinstance(text, str) else str(action)
        mapping = ActionMapping(
            requested_state=text,
            executed_action=text,
            supported=text.upper() in GAME_ACTIONS,
            unmapped=False,
            reason="caller-supplied game action; passed through unchanged",
        )
        return mapping, action

    def step(self, action: Any):
        if self._recorder is None:
            raise RuntimeError("call reset() before step()")
        mapping, game_action = self._map_action(action)
        observation, reward, terminated, truncated, info = self.env.step(game_action)
        self._step_index += 1
        conversion = self.observation_adapter.convert(observation)
        self._conversions.append(conversion)
        seconds = float(observation["environment"]["time"])
        step_reward = self.reward_function.for_step(
            reward,
            info,
            step=self._step_index,
            time_ms=seconds * 1000.0,
        )
        self._recorder.append(game_action, observation, reward, info)
        self._last_mapping = mapping
        self._last_step_reward = step_reward
        extended_info = dict(info)
        extended_info["fly_surfer"] = {
            "seed": self._seed,
            "step": self._step_index,
            "game_state": conversion.as_dict(),
            "action": mapping.as_dict(),
            "reward": step_reward.as_dict(),
        }
        self._last_info = extended_info
        return observation, reward, terminated, truncated, extended_info

    # ------------------------------------------------------------------
    # integration helpers
    # ------------------------------------------------------------------

    def timeline(self):
        """``(time_ms, GameState)`` pairs for ``SensoryInputScheduler``."""
        from environment.environment_adapter import build_timeline

        return build_timeline(self._conversions)

    def summary(self) -> dict:
        return self.env.summary()

    def action_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        if self._recorder is not None:
            for action in self._recorder.data["actions"]:
                counts[action] = counts.get(action, 0) + 1
        return counts

    def save_recording(self, path: str | Path) -> Path:
        if self._recorder is None:
            raise RuntimeError("no episode is active; call reset() first")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._recorder.save(target)
        return target

    def render(self, status: str | None = None, *, debug: bool = False) -> None:
        if self._renderer is None:
            self._renderer = self.api.renderer()()
        label = status or ("GAME OVER" if self.env.done else "RUNNING")
        self._renderer.draw(self.env, label, debug=debug, fps=0.0)

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    def describe(self) -> dict:
        return {
            "interface": "controlled_endless_runner_v1",
            "game": {
                "root": str(self.api.root),
                "observation_schema_version": self.api.observation_schema_version,
                "simulation_dt_s": float(self.env.dt),
            },
            "config": {
                "max_steps": int(self.config.max_steps),
                "initial_speed": float(self.config.initial_speed),
                "max_speed": float(self.config.max_speed),
                "coin_reward": float(self.config.coin_reward),
                "collision_penalty": float(self.config.collision_penalty),
                "survival_reward": float(self.config.survival_reward),
                "obstacle_reward": float(self.config.obstacle_reward),
            },
            "observation_adapter": self.observation_adapter.describe(),
            "action_adapter": self.action_adapter.describe(),
            "reward": {
                "classification": REWARD_CLASSIFICATION,
                "provenance": self.reward_function.provenance,
            },
            "rendering": {
                "mode": self.render_mode,
                "note": (
                    "render() draws the current frame; the simulation advances "
                    "on the fixed game timestep and never depends on frame rate"
                ),
            },
        }

    def __enter__(self) -> "ControlledGameEnvironment":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
