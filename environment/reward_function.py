"""Bridge game-derived rewards to the Phase 5 reward interfaces.

The game computes the reward from the events of each step and returns both the
scalar and its ``reward_components`` in ``info``. This module does not recompute
that reward: it verifies that the components sum to the returned scalar and
then expresses each nonzero component as a Phase 5 ``RewardDelivery`` and
``RewardEvent`` with ``source='gameplay'`` and explicit provenance.

The scalar is a synthetic task reward defined by the configured game rules. It
is not a biological dopamine, octopamine or serotonin measurement, and the
game's survival component is reported as the game defines it, not as an
independent objective invented here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from plasticity.modulation import (
    REWARD_SOURCE_GAMEPLAY,
    ModulationConfig,
    ModulationRewardProvider,
    RewardDelivery,
    RewardModulation,
    RewardStream,
)
from plasticity.reward import RewardEvent, RewardSchedule

REWARD_COMPONENTS = (
    "coin_collection",
    "collision_penalty",
    "survival_reward",
    "obstacle_avoided",
)

REWARD_CLASSIFICATION = (
    "synthetic task reward derived from controlled-game events; not a "
    "biological dopamine, octopamine or serotonin measurement"
)

DEFAULT_PROVENANCE = (
    "endless-surfer info['reward_components'] produced by "
    "game_env.rewards.calculate; the value was not recomputed by FLY-SURFER"
)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class StepReward:
    """One step's reward with its game components and provenance."""

    step: int
    time_ms: float
    total: float
    components: Mapping[str, float]
    event_types: tuple[str, ...]
    events: tuple[RewardEvent, ...]
    deliveries: tuple[RewardDelivery, ...]
    termination_reason: str | None
    provenance: str

    @property
    def neutral(self) -> bool:
        return all(value == 0.0 for value in self.components.values())

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "time_ms": round(float(self.time_ms), 6),
            "total": round(float(self.total), 9),
            "components": {
                key: round(float(value), 9)
                for key, value in self.components.items()
            },
            "neutral": self.neutral,
            "event_types": list(self.event_types),
            "events": [event.as_dict() for event in self.events],
            "deliveries": [delivery.as_dict() for delivery in self.deliveries],
            "termination_reason": self.termination_reason,
            "provenance": self.provenance,
            "classification": REWARD_CLASSIFICATION,
        }


class GameRewardFunction:
    """Accumulate per-step game rewards as Phase 5 deliveries and events."""

    def __init__(self, *, provenance: str = DEFAULT_PROVENANCE) -> None:
        if not isinstance(provenance, str) or not provenance:
            raise ValueError("provenance must be a non-empty string")
        self.provenance = provenance
        self.reset()

    def reset(self) -> None:
        self._steps: list[StepReward] = []
        self._deliveries: list[RewardDelivery] = []
        self._events: list[RewardEvent] = []

    @property
    def steps(self) -> tuple[StepReward, ...]:
        return tuple(self._steps)

    @property
    def events(self) -> tuple[RewardEvent, ...]:
        return tuple(self._events)

    @property
    def deliveries(self) -> tuple[RewardDelivery, ...]:
        return tuple(self._deliveries)

    @property
    def stream(self) -> RewardStream:
        """The recorded deliveries as an immutable Phase 5 stream snapshot."""
        return RewardStream(
            self._deliveries,
            provenance=self.provenance,
            classification=REWARD_CLASSIFICATION,
        )

    def schedule(self, delay_ms: float = 0.0) -> RewardSchedule:
        return RewardSchedule(self._events, delay_ms=delay_ms)

    def modulation_provider(
        self, config: ModulationConfig | None = None
    ) -> ModulationRewardProvider:
        """Phase 5 provider over the deliveries recorded so far."""
        return ModulationRewardProvider(
            self.stream, RewardModulation(config or ModulationConfig())
        )

    @property
    def total(self) -> float:
        return float(sum(step.total for step in self._steps))

    @property
    def n_steps(self) -> int:
        return len(self._steps)

    @property
    def n_reward_steps(self) -> int:
        return sum(1 for step in self._steps if not step.neutral)

    @property
    def n_neutral_steps(self) -> int:
        return sum(1 for step in self._steps if step.neutral)

    def component_totals(self) -> dict[str, float]:
        totals = {name: 0.0 for name in REWARD_COMPONENTS}
        for step in self._steps:
            for name, value in step.components.items():
                totals[name] += value
        return {name: round(value, 9) for name, value in totals.items()}

    def for_step(
        self,
        reward: Any,
        info: Mapping[str, Any],
        *,
        step: int,
        time_ms: float,
    ) -> StepReward:
        value = _finite(reward, "reward")
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise ValueError("step must be a non-negative integer")
        time_value = _finite(time_ms, "time_ms")
        if time_value < 0:
            raise ValueError("time_ms must be non-negative")
        if not isinstance(info, Mapping):
            raise ValueError("info must be a mapping")

        raw_components = info.get("reward_components")
        if not isinstance(raw_components, Mapping):
            raise ValueError("info is missing reward_components")
        if set(raw_components) != set(REWARD_COMPONENTS):
            raise ValueError(
                "reward_components do not match the documented game "
                f"components: {sorted(raw_components)}"
            )
        components = {
            name: _finite(raw_components[name], f"reward_components[{name!r}]")
            for name in REWARD_COMPONENTS
        }
        component_sum = float(sum(components.values()))
        if not math.isclose(component_sum, value, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "the game reward does not equal the sum of its components: "
                f"{value!r} != {component_sum!r}"
            )

        raw_events = info.get("events", [])
        if not isinstance(raw_events, Sequence) or isinstance(raw_events, (str, bytes)):
            raise ValueError("info events must be a list")
        event_types: list[str] = []
        for position, event in enumerate(raw_events):
            if not isinstance(event, Mapping) or not isinstance(
                event.get("type"), str
            ):
                raise ValueError(f"game event {position} has no type")
            event_types.append(str(event["type"]))

        deliveries: list[RewardDelivery] = []
        events: list[RewardEvent] = []
        for name in REWARD_COMPONENTS:
            magnitude = components[name]
            if magnitude == 0.0:
                continue
            detail = (
                f"{self.provenance}; step {step}, time {time_value:.6f} ms, "
                f"component {name!r}"
            )
            deliveries.append(
                RewardDelivery(
                    time_ms=time_value,
                    magnitude=magnitude,
                    source=REWARD_SOURCE_GAMEPLAY,
                    label=name,
                    provenance=detail,
                )
            )
            events.append(
                RewardEvent(time_ms=time_value, magnitude=magnitude, label=name)
            )

        termination_reason = info.get("termination_reason")
        if termination_reason is not None and not isinstance(termination_reason, str):
            raise ValueError("termination_reason must be a string or None")

        step_reward = StepReward(
            step=step,
            time_ms=time_value,
            total=value,
            components=components,
            event_types=tuple(event_types),
            events=tuple(events),
            deliveries=tuple(deliveries),
            termination_reason=termination_reason,
            provenance=self.provenance,
        )
        self._steps.append(step_reward)
        self._deliveries.extend(deliveries)
        self._events.extend(events)
        return step_reward

    def describe(self) -> dict:
        return {
            "classification": REWARD_CLASSIFICATION,
            "provenance": self.provenance,
            "components": list(REWARD_COMPONENTS),
            "n_steps": self.n_steps,
            "n_reward_steps": self.n_reward_steps,
            "n_neutral_steps": self.n_neutral_steps,
            "total_reward": round(self.total, 9),
            "component_totals": self.component_totals(),
            "stream": self.stream.describe(),
            "events": [event.as_dict() for event in self._events],
            "note": (
                "the game's survival component is reported exactly as the "
                "configured game rules define it; FLY-SURFER does not add "
                "extra survival reward"
            ),
        }
