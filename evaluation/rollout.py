"""One condition-E episode against the existing 5-tuple game API.

The game owns mechanics, spawning, collision, reward and termination. This
module only feeds the declared observations to a :class:`ConventionalAgent`,
executes the chosen game action and records what happened. Training and
evaluation differ only in action selection and in whether one REINFORCE
update is applied at the end; the environment, reward and cap are identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .conventional import EVALUATION_ACTIONS


@dataclass(frozen=True)
class EpisodeStep:
    """One executed game action and the learner state that chose it."""

    step: int
    features: tuple[float, ...]
    logits: tuple[float, ...]
    probabilities: tuple[float, ...]
    action: str
    action_index: int
    value: float
    reward: float
    cumulative_reward: float
    terminated: bool
    truncated: bool

    def as_dict(self) -> dict:
        return {
            "step": int(self.step),
            "features": list(self.features),
            "logits": list(self.logits),
            "probabilities": list(self.probabilities),
            "action": self.action,
            "action_index": int(self.action_index),
            "value": round(float(self.value), 9),
            "reward": round(float(self.reward), 9),
            "cumulative_reward": round(float(self.cumulative_reward), 9),
            "terminated": bool(self.terminated),
            "truncated": bool(self.truncated),
        }


@dataclass(frozen=True)
class EpisodeResult:
    seed: int | None
    steps: tuple[EpisodeStep, ...]
    total_reward: float
    terminated: bool
    truncated: bool
    termination_reason: str | None
    action_counts: dict[str, int]
    update: dict | None

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    def summary(self) -> dict:
        return {
            "seed": self.seed,
            "n_steps": self.n_steps,
            "total_reward": round(float(self.total_reward), 9),
            "terminated": bool(self.terminated),
            "truncated": bool(self.truncated),
            "termination_reason": self.termination_reason,
            "action_counts": dict(self.action_counts),
            "update": self.update,
        }


def run_episode(
    environment: Any,
    agent: Any,
    encoder: Any,
    *,
    seed: int | None = None,
    training: bool | None = None,
    max_steps: int | None = None,
) -> EpisodeResult:
    """Play one episode and, if training, apply one policy update."""
    if max_steps is not None:
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 0:
            raise ValueError("max_steps must be a non-negative integer or None")
    use_training = agent.training if training is None else bool(training)

    environment.reset(seed=seed)
    agent.reset_episode()
    observation = encoder.encode(environment.game_state)

    steps: list[EpisodeStep] = []
    total = 0.0
    terminated = False
    truncated = False
    reason: str | None = None

    while not (terminated or truncated):
        if max_steps is not None and len(steps) >= max_steps:
            truncated = True
            reason = "rollout_step_cap"
            break
        action_index, record = agent.act(observation, training=use_training)
        _, _, terminated, truncated, _ = environment.step(
            EVALUATION_ACTIONS[action_index]
        )
        step_reward = environment.last_step_reward
        if step_reward is None:
            raise RuntimeError("the environment did not record a step reward")
        reward = float(step_reward.total)
        total += reward
        if use_training:
            agent.record_reward(reward)
        observation = encoder.encode(environment.game_state)
        steps.append(
            EpisodeStep(
                step=len(steps) + 1,
                features=tuple(record["features"]),
                logits=tuple(record["logits"]),
                probabilities=tuple(record["probabilities"]),
                action=record["action"],
                action_index=int(action_index),
                value=float(record["value"]),
                reward=reward,
                cumulative_reward=total,
                terminated=bool(terminated),
                truncated=bool(truncated),
            )
        )
        reason = step_reward.termination_reason

    update = None
    if use_training:
        terminal_value = 0.0 if terminated else agent.value(observation)
        update = agent.finish_episode(terminal_value=terminal_value)

    counts: dict[str, int] = {}
    for step in steps:
        counts[step.action] = counts.get(step.action, 0) + 1
    episode_seed = getattr(environment, "seed", None)
    return EpisodeResult(
        seed=None if episode_seed is None else int(episode_seed),
        steps=tuple(steps),
        total_reward=float(total),
        terminated=bool(terminated),
        truncated=bool(truncated),
        termination_reason=reason,
        action_counts=counts,
        update=update,
    )


__all__ = ["EpisodeResult", "EpisodeStep", "run_episode"]
