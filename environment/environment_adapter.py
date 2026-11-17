"""End-to-end adapter between Phase 3/4 records and the controlled game.

The game environment already exposes the stable ``reset``/``step`` interface.
This module adds the FLY-SURFER-facing layer: it accepts a Phase 4 motor
output, records the Phase 4 action mapping, the Phase 3 ``GameState`` and the
Phase 5 reward provenance that belong to the resulting step, and exposes the
episode as a ``SensoryInputScheduler`` timeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from environment.action_adapter import ActionMapping
from environment.game_state import ObservationConversion
from environment.reward_function import StepReward
from environment.subway_environment import ControlledGameEnvironment
from motor.action_decoder import MotorOutput
from sensory.game_state import GameState


def build_timeline(
    conversions: Iterable[ObservationConversion],
) -> list[tuple[float, GameState]]:
    """Convert recorded observations into scheduler segments.

    Times must be non-decreasing. A repeated time keeps the later state, since
    the scheduler requires strictly increasing segment starts.
    """
    pairs: list[tuple[float, GameState]] = []
    for conversion in conversions:
        time_ms = float(conversion.state.time_ms)
        if pairs and time_ms < pairs[-1][0]:
            raise ValueError(
                "game-state times must be non-decreasing; got "
                f"{time_ms} after {pairs[-1][0]}"
            )
        if pairs and time_ms == pairs[-1][0]:
            pairs[-1] = (time_ms, conversion.state)
        else:
            pairs.append((time_ms, conversion.state))
    return pairs


@dataclass(frozen=True)
class AdapterStep:
    """One game step with the FLY-SURFER records attached."""

    step: int
    seed: int | None
    time_ms: float
    game_state: GameState
    conversion: ObservationConversion
    mapping: ActionMapping | None
    reward: float
    step_reward: StepReward
    terminated: bool
    truncated: bool
    observation: Mapping[str, Any]
    info: Mapping[str, Any]

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "seed": self.seed,
            "time_ms": round(float(self.time_ms), 6),
            "game_state": self.conversion.as_dict(),
            "action": None if self.mapping is None else self.mapping.as_dict(),
            "reward": round(float(self.reward), 9),
            "step_reward": self.step_reward.as_dict(),
            "terminated": bool(self.terminated),
            "truncated": bool(self.truncated),
            "termination_reason": self.step_reward.termination_reason,
        }


@dataclass(frozen=True)
class EpisodeRun:
    """Summary of one adapter-driven episode."""

    agent: str
    seed: int | None
    steps: int
    terminated: bool
    truncated: bool
    termination_reason: str | None
    total_reward: float
    action_counts: Mapping[str, int]
    reward_summary: Mapping[str, Any]
    summary: Mapping[str, Any]
    records: tuple[AdapterStep, ...]

    def as_dict(self) -> dict:
        return {
            "agent": self.agent,
            "seed": self.seed,
            "steps": self.steps,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "termination_reason": self.termination_reason,
            "total_reward": round(float(self.total_reward), 9),
            "action_counts": dict(self.action_counts),
            "reward": dict(self.reward_summary),
            "summary": dict(self.summary),
        }


class GameEnvironmentAdapter:
    """Drive a controlled game episode with motor outputs or game actions."""

    def __init__(
        self,
        environment: ControlledGameEnvironment | None = None,
        **environment_kwargs: Any,
    ) -> None:
        self.environment = environment or ControlledGameEnvironment(
            **environment_kwargs
        )

    @property
    def game(self) -> ControlledGameEnvironment:
        return self.environment

    def reset(self, seed: int | None = None) -> Mapping[str, Any]:
        return self.environment.reset(seed)

    def step(self, motor_output: MotorOutput | Mapping | None = None) -> AdapterStep:
        if motor_output is None:
            mapping = self.environment.action_adapter.map(None)
            observation, reward, terminated, truncated, info = (
                self.environment.step(mapping)
            )
        elif isinstance(motor_output, (MotorOutput, Mapping)):
            observation, reward, terminated, truncated, info = (
                self.environment.step(motor_output)
            )
            mapping = self.environment.last_mapping
        else:
            observation, reward, terminated, truncated, info = (
                self.environment.step(motor_output)
            )
            mapping = self.environment.last_mapping
        conversion = self.environment.conversions[-1]
        step_reward = self.environment.last_step_reward
        return AdapterStep(
            step=self.environment.n_steps,
            seed=self.environment.seed,
            time_ms=float(observation["environment"]["time"]) * 1000.0,
            game_state=conversion.state,
            conversion=conversion,
            mapping=mapping,
            reward=float(reward),
            step_reward=step_reward,
            terminated=bool(terminated),
            truncated=bool(truncated),
            observation=observation,
            info=info,
        )

    def run_episode(
        self,
        agent,
        *,
        seed: int | None = None,
        max_steps: int | None = None,
        on_step: Callable[[AdapterStep], None] | None = None,
    ) -> EpisodeRun:
        """Run until the game ends or ``max_steps`` records are collected."""
        if max_steps is not None and (
            isinstance(max_steps, bool)
            or not isinstance(max_steps, int)
            or max_steps <= 0
        ):
            raise ValueError("max_steps must be a positive integer or None")
        act = agent.act if hasattr(agent, "act") else agent
        observation = self.reset(seed)
        records: list[AdapterStep] = []
        terminated = truncated = False
        while not (terminated or truncated):
            if max_steps is not None and len(records) >= max_steps:
                break
            output = act(observation)
            record = self.step(output)
            records.append(record)
            if on_step is not None:
                on_step(record)
            observation = record.observation
            terminated = record.terminated
            truncated = record.truncated
        reason = records[-1].step_reward.termination_reason if records else None
        return EpisodeRun(
            agent=type(agent).__name__ if hasattr(agent, "act") else "callable",
            seed=self.environment.seed,
            steps=len(records),
            terminated=terminated,
            truncated=truncated,
            termination_reason=reason,
            total_reward=float(sum(record.reward for record in records)),
            action_counts=self.environment.action_counts(),
            reward_summary=self.environment.reward_function.describe(),
            summary=self.environment.summary(),
            records=tuple(records),
        )

    def timeline(self) -> list[tuple[float, GameState]]:
        return self.environment.timeline()

    def close(self) -> None:
        self.environment.close()

    def describe(self) -> dict:
        payload = self.environment.describe()
        payload["interface"] = "game_environment_adapter_v1"
        payload["adapter_step_fields"] = [
            "step",
            "seed",
            "time_ms",
            "game_state",
            "conversion",
            "mapping",
            "reward",
            "step_reward",
            "terminated",
            "truncated",
            "observation",
            "info",
        ]
        return payload

    def __enter__(self) -> "GameEnvironmentAdapter":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
