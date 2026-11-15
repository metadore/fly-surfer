"""Reward representation, delayed scheduling and temporal-difference prediction.

SCIENTIFIC STATUS
    reward        an external computational scalar, not dopamine
    predictor     a configurable value model, not a measured neural signal
    delta_t       reward prediction error of that model

The predictor is deliberately independent of the plasticity engine. It can be
used, inspected and tested without any synapse, trace or weight state.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import yaml

REWARD_CLASSIFICATION = (
    "computational task reward; not a biological dopamine, octopamine or "
    "serotonin measurement"
)


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _non_negative(value, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


@dataclass(frozen=True)
class RewardEvent:
    """One scheduled reward delivery, before the optional delay is applied."""

    time_ms: float
    magnitude: float
    label: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "time_ms", _non_negative(self.time_ms, "time_ms"))
        object.__setattr__(
            self, "magnitude", _finite(self.magnitude, "magnitude")
        )
        if not isinstance(self.label, str):
            raise ValueError("label must be a string")

    def as_dict(self) -> dict:
        return {
            "time_ms": self.time_ms,
            "magnitude": self.magnitude,
            "label": self.label,
        }


class RewardSchedule:
    """An ordered reward schedule with an optional delivery delay."""

    def __init__(
        self, events: Iterable[RewardEvent | Sequence], *, delay_ms: float = 0.0
    ) -> None:
        self.delay_ms = _non_negative(delay_ms, "delay_ms")
        parsed: list[RewardEvent] = []
        for position, event in enumerate(events):
            if isinstance(event, RewardEvent):
                parsed.append(event)
            elif isinstance(event, (tuple, list)) and len(event) >= 2:
                label = str(event[2]) if len(event) > 2 else ""
                parsed.append(RewardEvent(float(event[0]), float(event[1]), label))
            else:
                raise ValueError(f"reward event {position} is not valid")
        self.events = tuple(sorted(parsed, key=lambda item: item.time_ms))

    def due_time(self, event: RewardEvent) -> float:
        return event.time_ms + self.delay_ms

    def due_between(self, start_ms: float, end_ms: float) -> float:
        """Sum magnitudes whose delayed delivery falls in (start, end]."""
        total = 0.0
        for event in self.events:
            due = self.due_time(event)
            if start_ms < due <= end_ms:
                total += event.magnitude
        return total

    def total(self) -> float:
        return float(sum(event.magnitude for event in self.events))

    def counts(self) -> dict:
        positive = sum(1 for event in self.events if event.magnitude > 0)
        negative = sum(1 for event in self.events if event.magnitude < 0)
        zero = sum(1 for event in self.events if event.magnitude == 0)
        return {"positive": positive, "negative": negative, "zero": zero}

    def describe(self) -> dict:
        return {
            "classification": REWARD_CLASSIFICATION,
            "delay_ms": self.delay_ms,
            "n_events": len(self.events),
            "total_reward": round(self.total(), 9),
            "counts": self.counts(),
            "events": [event.as_dict() for event in self.events],
        }

    def digest(self) -> str:
        payload = json.dumps(self.describe(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ScriptedRewardProvider:
    """Emit due reward exactly once per delivery time.

    ``step(step, time_ms, context)`` returns the total reward whose delayed
    delivery time falls in ``(previous_time, time_ms]``. The first call starts
    at negative infinity so an event at time zero is delivered at the first
    step.
    """

    def __init__(self, schedule: RewardSchedule) -> None:
        if not isinstance(schedule, RewardSchedule):
            raise ValueError("schedule must be a RewardSchedule")
        self.schedule = schedule
        self._last_time = -math.inf
        self._emitted = 0

    @property
    def emitted_reward(self) -> float:
        return float(self._emitted)

    def reset(self) -> None:
        self._last_time = -math.inf
        self._emitted = 0

    def step(self, step: int, time_ms: float, context=None) -> float:
        del step, context
        now = _finite(time_ms, "time_ms")
        if now < self._last_time:
            raise ValueError("time_ms must be non-decreasing")
        reward = self.schedule.due_between(self._last_time, now)
        self._last_time = now
        self._emitted += reward
        return float(reward)

    def describe(self) -> dict:
        payload = self.schedule.describe()
        payload["provider"] = "scripted"
        return payload


class TabularValuePredictor:
    """A tabular value model with a configurable discount and learning rate.

    ``delta = reward + gamma * V(next_state) - V(state)``. A ``None`` next
    state is a terminal transition and contributes zero future value. This is
    one model of reward prediction, not the only biologically plausible one.
    """

    def __init__(
        self,
        *,
        gamma: float = 0.0,
        learning_rate: float = 0.2,
        initial_value: float = 0.0,
        value_bound: float = 100.0,
    ) -> None:
        self.gamma = _finite(gamma, "gamma")
        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError("gamma must lie in [0, 1]")
        self.learning_rate = _finite(learning_rate, "learning_rate")
        if not 0.0 <= self.learning_rate <= 1.0:
            raise ValueError("learning_rate must lie in [0, 1]")
        self.initial_value = _finite(initial_value, "initial_value")
        self.value_bound = _non_negative(value_bound, "value_bound")
        if self.value_bound == 0:
            raise ValueError("value_bound must be positive")
        self._values: dict[str, float] = {}

    @staticmethod
    def _key(state) -> str:
        if isinstance(state, (str, int)) and not isinstance(state, bool):
            return str(state)
        if isinstance(state, tuple) and all(
            isinstance(item, (str, int)) and not isinstance(item, bool)
            for item in state
        ):
            return "|".join(str(item) for item in state)
        raise ValueError("state must be a string, integer or tuple of those")

    def value(self, state) -> float:
        return float(self._values.get(self._key(state), self.initial_value))

    def next_value(self, next_state) -> float:
        if next_state is None:
            return 0.0
        return self.value(next_state)

    def prediction_error(self, state, next_state, reward: float) -> float:
        observed = _finite(reward, "reward")
        delta = (
            observed
            + self.gamma * self.next_value(next_state)
            - self.value(state)
        )
        return float(delta)

    def learn(self, state, next_state, reward: float) -> float:
        delta = self.prediction_error(state, next_state, reward)
        key = self._key(state)
        updated = self.value(state) + self.learning_rate * delta
        if not math.isfinite(updated):
            raise FloatingPointError("value update produced a non-finite value")
        self._values[key] = float(
            np.clip(updated, -self.value_bound, self.value_bound)
        )
        return delta

    @property
    def n_states(self) -> int:
        return len(self._values)

    def state_dict(self) -> dict[str, float]:
        return {key: round(float(value), 9) for key, value in sorted(self._values.items())}

    def load_state_dict(self, values: Mapping[str, float]) -> None:
        loaded: dict[str, float] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not key:
                raise ValueError("predictor state keys must be non-empty strings")
            number = _finite(value, f"value[{key}]")
            if abs(number) > self.value_bound:
                raise ValueError(f"value[{key}] exceeds the declared bound")
            loaded[key] = float(number)
        self._values = loaded

    def digest(self) -> str:
        payload = json.dumps(self.state_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def describe(self) -> dict:
        return {
            "model": "tabular_temporal_difference",
            "gamma": self.gamma,
            "learning_rate": self.learning_rate,
            "initial_value": self.initial_value,
            "value_bound": self.value_bound,
            "n_states": self.n_states,
            "classification": (
                "computational value model; not a measured reward prediction "
                "signal"
            ),
        }


@dataclass(frozen=True)
class RewardPrediction:
    """One logged reward step."""

    step: int
    time_ms: float
    reward: float
    value: float
    next_value: float
    prediction_error: float
    state: str
    next_state: str | None

    def as_dict(self) -> dict:
        return {
            "step": int(self.step),
            "time_ms": float(self.time_ms),
            "reward": round(float(self.reward), 9),
            "value": round(float(self.value), 9),
            "next_value": round(float(self.next_value), 9),
            "prediction_error": round(float(self.prediction_error), 9),
            "state": self.state,
            "next_state": self.next_state,
        }


class RewardLogger:
    """Ordered reward log with a deterministic digest."""

    def __init__(self) -> None:
        self._records: list[RewardPrediction] = []

    def append(self, record: RewardPrediction) -> None:
        if not isinstance(record, RewardPrediction):
            raise ValueError("record must be a RewardPrediction")
        self._records.append(record)

    @property
    def records(self) -> tuple[RewardPrediction, ...]:
        return tuple(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def to_dict(self) -> dict:
        rewards = np.asarray([item.reward for item in self._records], dtype=np.float64)
        deltas = np.asarray(
            [item.prediction_error for item in self._records], dtype=np.float64
        )
        return {
            "n_steps": len(self._records),
            "total_reward": round(float(rewards.sum()), 9) if rewards.size else 0.0,
            "positive_steps": int(np.count_nonzero(rewards > 0)),
            "negative_steps": int(np.count_nonzero(rewards < 0)),
            "zero_steps": int(np.count_nonzero(rewards == 0)),
            "mean_prediction_error": (
                round(float(deltas.mean()), 9) if deltas.size else 0.0
            ),
            "max_abs_prediction_error": (
                round(float(np.abs(deltas).max()), 9) if deltas.size else 0.0
            ),
            "records": [item.as_dict() for item in self._records],
        }

    def digest(self) -> str:
        payload = json.dumps(
            [item.as_dict() for item in self._records], sort_keys=True
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RewardStatistics:
    n_events: int
    total: float
    positive: int
    negative: int
    zero: int
    first_time_ms: float | None
    last_time_ms: float | None

    def as_dict(self) -> dict:
        return {
            "n_events": self.n_events,
            "total": round(self.total, 9),
            "positive": self.positive,
            "negative": self.negative,
            "zero": self.zero,
            "first_time_ms": self.first_time_ms,
            "last_time_ms": self.last_time_ms,
        }


def reward_statistics(events: Iterable[RewardEvent]) -> RewardStatistics:
    items = list(events)
    times = [event.time_ms for event in items]
    return RewardStatistics(
        n_events=len(items),
        total=float(sum(event.magnitude for event in items)),
        positive=sum(1 for event in items if event.magnitude > 0),
        negative=sum(1 for event in items if event.magnitude < 0),
        zero=sum(1 for event in items if event.magnitude == 0),
        first_time_ms=min(times) if times else None,
        last_time_ms=max(times) if times else None,
    )


def shuffled_reward_schedule(
    schedule: RewardSchedule, *, seed: int
) -> RewardSchedule:
    """Permute magnitudes across the existing event times (control condition)."""
    if not isinstance(schedule, RewardSchedule):
        raise ValueError("schedule must be a RewardSchedule")
    magnitudes = [event.magnitude for event in schedule.events]
    rng = np.random.default_rng(int(seed))
    order = rng.permutation(len(magnitudes))
    shuffled = [
        RewardEvent(
            event.time_ms,
            magnitudes[int(order[index])],
            f"shuffled:{event.label}" if event.label else "shuffled",
        )
        for index, event in enumerate(schedule.events)
    ]
    return RewardSchedule(shuffled, delay_ms=schedule.delay_ms)


@dataclass(frozen=True)
class RewardConfig:
    """The declared reward section of ``configs/plasticity.yaml``."""

    classification: str
    delay_ms: float
    schedules: dict[str, RewardSchedule]

    def schedule(self, name: str) -> RewardSchedule:
        if name not in self.schedules:
            raise KeyError(f"unknown reward schedule {name!r}")
        return self.schedules[name]

    def describe(self) -> dict:
        return {
            "classification": self.classification,
            "delay_ms": self.delay_ms,
            "schedule_names": sorted(self.schedules),
            "schedules": {
                name: schedule.describe() for name, schedule in self.schedules.items()
            },
            "digests": {
                name: schedule.digest() for name, schedule in self.schedules.items()
            },
        }


@dataclass(frozen=True)
class PredictorConfig:
    """The declared predictor section of ``configs/plasticity.yaml``."""

    gamma: float
    learning_rate: float
    initial_value: float
    value_bound: float

    def build(self) -> "TabularValuePredictor":
        return TabularValuePredictor(
            gamma=self.gamma,
            learning_rate=self.learning_rate,
            initial_value=self.initial_value,
            value_bound=self.value_bound,
        )

    def describe(self) -> dict:
        return {
            "gamma": self.gamma,
            "learning_rate": self.learning_rate,
            "initial_value": self.initial_value,
            "value_bound": self.value_bound,
        }


@dataclass(frozen=True)
class RewardSystemConfig:
    reward: RewardConfig
    predictor: PredictorConfig
    raw: dict

    def describe(self) -> dict:
        return {
            "reward": self.reward.describe(),
            "predictor": self.predictor.describe(),
        }


def _mapping(value, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def load_reward_system_config(path: str | Path) -> RewardSystemConfig:
    """Load and validate the reward and predictor sections of the config."""
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    root = _mapping(raw, "plasticity config")

    reward_section = _mapping(root.get("reward"), "reward")
    classification = str(
        reward_section.get("classification", REWARD_CLASSIFICATION)
    ).strip()
    default_delay = _non_negative(
        reward_section.get("delay_ms_default", 0.0), "reward.delay_ms_default"
    )
    schedule_section = _mapping(
        reward_section.get("schedules", {}), "reward.schedules"
    )
    if not schedule_section:
        raise ValueError("reward.schedules must declare at least one schedule")
    schedules: dict[str, RewardSchedule] = {}
    for name, entry in schedule_section.items():
        if not isinstance(name, str) or not name:
            raise ValueError("reward schedule names must be non-empty strings")
        body = _mapping(entry, f"reward.schedules.{name}")
        events = body.get("events")
        if not isinstance(events, list) or not events:
            raise ValueError(f"reward.schedules.{name}.events must be non-empty")
        delay = _non_negative(
            body.get("delay_ms", default_delay),
            f"reward.schedules.{name}.delay_ms",
        )
        schedules[name] = RewardSchedule(events, delay_ms=delay)

    predictor_section = _mapping(root.get("predictor"), "predictor")
    defaults = _mapping(predictor_section.get("defaults", predictor_section), "predictor.defaults")
    predictor = PredictorConfig(
        gamma=_finite(
            defaults.get("gamma", 0.0),
            "predictor.gamma",
        ),
        learning_rate=_finite(
            defaults.get("learning_rate", 0.2),
            "predictor.learning_rate",
        ),
        initial_value=_finite(
            defaults.get("initial_value", 0.0),
            "predictor.initial_value",
        ),
        value_bound=_non_negative(
            defaults.get("value_bound", 100.0),
            "predictor.value_bound",
        ),
    )
    predictor.build()

    reward = RewardConfig(
        classification=classification,
        delay_ms=default_delay,
        schedules=schedules,
    )
    return RewardSystemConfig(reward=reward, predictor=predictor, raw=raw)
