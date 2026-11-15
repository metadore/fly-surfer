"""Reward provenance and decaying reward modulation for Phase 5.

SCIENTIFIC STATUS
    A reward delivery is an external computational scalar. Its ``source``
    records where the scalar came from; it does not make the scalar a
    biological measurement.
    Modulation is a computational decaying scalar, not a dopamine,
    octopamine or serotonin measurement.
    A missing reward is represented explicitly and is never treated as a
    zero-magnitude reward: no modulation is emitted and no weight update is
    triggered.

The provider is compatible with ``PlasticSimulator``'s reward interface:
``step(step, time_ms, context)`` returns a modulation value only when a
reward is due, and ``None`` when no reward information is available.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

REWARD_SOURCE_EXPERIMENTAL = "experimental_input"
REWARD_SOURCE_GAMEPLAY = "gameplay"
REWARD_SOURCE_EXTERNAL = "external"
REWARD_SOURCE_UNAVAILABLE = "unavailable"
REWARD_SOURCES = (
    REWARD_SOURCE_EXPERIMENTAL,
    REWARD_SOURCE_GAMEPLAY,
    REWARD_SOURCE_EXTERNAL,
    REWARD_SOURCE_UNAVAILABLE,
)

REWARD_CLASSIFICATION = (
    "external computational reward; not a biological dopamine, octopamine or "
    "serotonin measurement"
)
MODULATION_CLASSIFICATION = (
    "computational decaying reward modulation; not a biological dopamine model"
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


def _text(value, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


@dataclass(frozen=True)
class RewardDelivery:
    """One reward delivery with explicit provenance.

    ``magnitude=None`` means reward information was unavailable; it is a
    distinct state from ``magnitude=0.0`` (a delivered neutral reward).
    """

    time_ms: float
    magnitude: float | None
    source: str = REWARD_SOURCE_EXPERIMENTAL
    label: str = ""
    provenance: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "time_ms", _non_negative(self.time_ms, "time_ms")
        )
        if not isinstance(self.source, str) or self.source not in REWARD_SOURCES:
            raise ValueError(f"source must be one of {REWARD_SOURCES}")
        object.__setattr__(self, "label", _text(self.label, "label"))
        object.__setattr__(
            self, "provenance", _text(self.provenance, "provenance")
        )
        missing = self.magnitude is None
        if missing != (self.source == REWARD_SOURCE_UNAVAILABLE):
            raise ValueError(
                "magnitude=None requires source 'unavailable', and source "
                "'unavailable' requires magnitude=None"
            )
        if not missing:
            object.__setattr__(
                self, "magnitude", _finite(self.magnitude, "magnitude")
            )

    @property
    def available(self) -> bool:
        return self.magnitude is not None

    def as_dict(self) -> dict:
        return {
            "time_ms": float(self.time_ms),
            "magnitude": None if self.magnitude is None else float(self.magnitude),
            "source": self.source,
            "label": self.label,
            "provenance": self.provenance,
            "available": self.available,
        }


class RewardStream:
    """Ordered reward deliveries with source-level provenance."""

    def __init__(
        self,
        deliveries: Iterable[RewardDelivery | Sequence],
        *,
        provenance: str = "",
        classification: str = REWARD_CLASSIFICATION,
    ) -> None:
        parsed: list[RewardDelivery] = []
        for position, item in enumerate(deliveries):
            if isinstance(item, RewardDelivery):
                parsed.append(item)
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                time_ms, magnitude = item[0], item[1]
                source = (
                    item[2]
                    if len(item) > 2
                    else (
                        REWARD_SOURCE_UNAVAILABLE
                        if magnitude is None
                        else REWARD_SOURCE_EXPERIMENTAL
                    )
                )
                label = str(item[3]) if len(item) > 3 else ""
                detail = str(item[4]) if len(item) > 4 else ""
                parsed.append(
                    RewardDelivery(
                        float(time_ms),
                        None if magnitude is None else float(magnitude),
                        source=str(source),
                        label=label,
                        provenance=detail,
                    )
                )
            else:
                raise ValueError(f"reward delivery {position} is not valid")
        self.deliveries = tuple(sorted(parsed, key=lambda item: item.time_ms))
        self.provenance = _text(provenance, "provenance")
        self.classification = _text(classification, "classification")

    def __len__(self) -> int:
        return len(self.deliveries)

    def due_between(self, start_ms: float, end_ms: float) -> tuple[RewardDelivery, ...]:
        """Deliveries whose time falls in ``(start_ms, end_ms]``."""
        return tuple(
            item
            for item in self.deliveries
            if start_ms < item.time_ms <= end_ms
        )

    def total(self) -> float:
        return float(
            sum(item.magnitude for item in self.deliveries if item.available)
        )

    def counts(self) -> dict:
        return {
            "positive": sum(
                1
                for item in self.deliveries
                if item.available and item.magnitude > 0
            ),
            "negative": sum(
                1
                for item in self.deliveries
                if item.available and item.magnitude < 0
            ),
            "neutral": sum(
                1
                for item in self.deliveries
                if item.available and item.magnitude == 0
            ),
            "missing": sum(1 for item in self.deliveries if not item.available),
        }

    def describe(self) -> dict:
        return {
            "classification": self.classification,
            "provenance": self.provenance,
            "n_events": len(self.deliveries),
            "counts": self.counts(),
            "total_available_reward": round(self.total(), 9),
            "events": [item.as_dict() for item in self.deliveries],
            "digest": self.digest(),
        }

    def digest(self) -> str:
        payload = {
            "provenance": self.provenance,
            "events": [item.as_dict() for item in self.deliveries],
        }
        text = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModulationConfig:
    """Declared parameters of the decaying modulation signal."""

    gain: float = 1.0
    decay_tau_ms: float = 50.0
    baseline: float = 0.0
    clip_abs: float | None = 5.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "gain", _non_negative(self.gain, "gain"))
        object.__setattr__(
            self,
            "decay_tau_ms",
            _finite(self.decay_tau_ms, "decay_tau_ms"),
        )
        if self.decay_tau_ms <= 0:
            raise ValueError("decay_tau_ms must be positive")
        object.__setattr__(
            self, "baseline", _finite(self.baseline, "baseline")
        )
        if self.clip_abs is not None:
            clip = _finite(self.clip_abs, "clip_abs")
            if clip <= 0:
                raise ValueError("clip_abs must be positive")
            object.__setattr__(self, "clip_abs", clip)

    @classmethod
    def from_config(cls, payload) -> "ModulationConfig":
        if not isinstance(payload, dict):
            raise ValueError("modulation config must be a mapping")
        known = {"gain", "decay_tau_ms", "baseline", "clip_abs"}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise ValueError(f"unknown modulation parameters: {unknown}")
        return cls(**{key: payload[key] for key in payload})

    @property
    def decay_per_ms(self) -> float:
        return math.exp(-1.0 / self.decay_tau_ms)

    def clip(self, value: float) -> float:
        if self.clip_abs is None:
            return float(value)
        return float(np.clip(value, -self.clip_abs, self.clip_abs))

    def describe(self) -> dict:
        return {
            "gain": float(self.gain),
            "decay_tau_ms": float(self.decay_tau_ms),
            "decay_per_ms": round(self.decay_per_ms, 12),
            "baseline": float(self.baseline),
            "clip_abs": None if self.clip_abs is None else float(self.clip_abs),
            "classification": MODULATION_CLASSIFICATION,
            "interpretation": (
                "phasic modulation is gain * reward for one delivery; the "
                "state is a decaying envelope kept for inspection"
            ),
        }


@dataclass(frozen=True)
class ModulationRecord:
    """One delivered (or unavailable) reward and the resulting modulation."""

    step: int
    time_ms: float
    magnitude: float | None
    source: str
    label: str
    available: bool
    phasic_modulation: float | None
    modulation_state: float

    def as_dict(self) -> dict:
        return {
            "step": int(self.step),
            "time_ms": round(float(self.time_ms), 9),
            "magnitude": None if self.magnitude is None else round(float(self.magnitude), 9),
            "source": self.source,
            "label": self.label,
            "available": self.available,
            "phasic_modulation": (
                None
                if self.phasic_modulation is None
                else round(float(self.phasic_modulation), 9)
            ),
            "modulation_state": round(float(self.modulation_state), 9),
        }


class RewardModulation:
    """Exponential decay envelope driven by timestamped reward deliveries."""

    def __init__(self, config: ModulationConfig | None = None) -> None:
        self.config = config or ModulationConfig()
        self._state = float(self.config.baseline)
        self._last_time: float | None = None
        self._records: list[ModulationRecord] = []
        self._step = 0

    @property
    def records(self) -> tuple[ModulationRecord, ...]:
        return tuple(self._records)

    @property
    def n_events(self) -> int:
        return len(self._records)

    @property
    def n_available(self) -> int:
        return sum(1 for record in self._records if record.available)

    @property
    def n_missing(self) -> int:
        return sum(1 for record in self._records if not record.available)

    @property
    def value(self) -> float:
        return float(self._state)

    def _decay_to(self, time_ms: float) -> float:
        if self._last_time is None:
            return float(self.config.baseline)
        elapsed = float(time_ms) - self._last_time
        if elapsed < 0:
            raise ValueError("reward deliveries must be time ordered")
        decayed = self.config.baseline + (
            self._state - self.config.baseline
        ) * math.exp(-elapsed / self.config.decay_tau_ms)
        return float(decayed)

    def deliver(
        self, delivery: RewardDelivery, *, step: int | None = None
    ) -> ModulationRecord:
        if not isinstance(delivery, RewardDelivery):
            raise ValueError("delivery must be a RewardDelivery")
        decayed = self._decay_to(delivery.time_ms)
        phasic = (
            None
            if not delivery.available
            else self.config.clip(self.config.gain * float(delivery.magnitude))
        )
        state = decayed if phasic is None else self.config.clip(decayed + phasic)
        record = ModulationRecord(
            step=int(self._step if step is None else step),
            time_ms=float(delivery.time_ms),
            magnitude=delivery.magnitude,
            source=delivery.source,
            label=delivery.label,
            available=delivery.available,
            phasic_modulation=phasic,
            modulation_state=float(state),
        )
        self._state = float(state)
        self._last_time = float(delivery.time_ms)
        self._step += 1
        self._records.append(record)
        return record

    def value_at(self, time_ms: float) -> float:
        """Project the current state to ``time_ms`` without mutating it."""
        return float(self._decay_to(_non_negative(time_ms, "time_ms")))

    def series(self, times_ms: Iterable[float]) -> list[float]:
        """Reconstructed modulation at arbitrary times from the event log."""
        if not self._records:
            return [float(self.config.baseline) for _ in times_ms]
        times = np.asarray(list(times_ms), dtype=np.float64)
        event_times = np.asarray(
            [record.time_ms for record in self._records], dtype=np.float64
        )
        states = np.asarray(
            [record.modulation_state for record in self._records], dtype=np.float64
        )
        index = np.searchsorted(event_times, times, side="right") - 1
        values = np.full(times.shape, self.config.baseline, dtype=np.float64)
        valid = index >= 0
        if valid.any():
            elapsed = times[valid] - event_times[index[valid]]
            values[valid] = self.config.baseline + (
                states[index[valid]] - self.config.baseline
            ) * np.exp(-elapsed / self.config.decay_tau_ms)
        return [round(float(value), 9) for value in values]

    def reset(self) -> None:
        self._state = float(self.config.baseline)
        self._last_time = None
        self._records = []
        self._step = 0

    def digest(self) -> str:
        payload = [record.as_dict() for record in self._records]
        text = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def describe(self) -> dict:
        return {
            "config": self.config.describe(),
            "n_events": self.n_events,
            "n_available": self.n_available,
            "n_missing": self.n_missing,
            "records": [record.as_dict() for record in self._records],
            "digest": self.digest(),
            "classification": MODULATION_CLASSIFICATION,
        }


class ModulationRewardProvider:
    """Reward provider returning phasic modulation at due events only.

    The returned value is the sum of the phasic modulations due at that step.
    It is ``None`` when no available reward is due, so the simulator performs
    no weight update. Unavailable deliveries are logged and never emitted as
    zeros.
    """

    def __init__(self, stream: RewardStream, modulation: RewardModulation) -> None:
        if not isinstance(stream, RewardStream):
            raise ValueError("stream must be a RewardStream")
        if not isinstance(modulation, RewardModulation):
            raise ValueError("modulation must be a RewardModulation")
        self.stream = stream
        self.modulation = modulation
        self._last_time = -math.inf
        self.n_steps = 0
        self.n_update_steps = 0
        self.n_steps_without_reward = 0
        self.n_missing_events = 0
        self.emitted_modulation = 0.0

    @property
    def emitted_reward(self) -> float:
        return float(self.emitted_modulation)

    def reset(self) -> None:
        self._last_time = -math.inf
        self.n_steps = 0
        self.n_update_steps = 0
        self.n_steps_without_reward = 0
        self.n_missing_events = 0
        self.emitted_modulation = 0.0
        self.modulation.reset()

    def step(self, step: int, time_ms: float, context=None):
        del context
        now = _finite(time_ms, "time_ms")
        if now < self._last_time:
            raise ValueError("time_ms must be non-decreasing")
        due = self.stream.due_between(self._last_time, now)
        self._last_time = now
        self.n_steps += 1
        phasic_values: list[float] = []
        for delivery in due:
            record = self.modulation.deliver(delivery, step=step)
            if record.available:
                phasic_values.append(float(record.phasic_modulation))
            else:
                self.n_missing_events += 1
        if not phasic_values:
            self.n_steps_without_reward += 1
            return None
        value = float(sum(phasic_values))
        self.n_update_steps += 1
        self.emitted_modulation += value
        return value

    def modulation_series(self, duration_ms: float, dt_ms: float) -> list[float]:
        n_steps = int(round(float(duration_ms) / float(dt_ms)))
        times = [step * float(dt_ms) for step in range(n_steps + 1)]
        return self.modulation.series(times)

    def describe(self) -> dict:
        return {
            "provider": "modulation_reward_provider",
            "stream": self.stream.describe(),
            "modulation": self.modulation.describe(),
            "n_steps": int(self.n_steps),
            "n_update_steps": int(self.n_update_steps),
            "n_steps_without_reward": int(self.n_steps_without_reward),
            "n_missing_events": int(self.n_missing_events),
            "emitted_modulation": round(float(self.emitted_modulation), 9),
            "missing_reward_policy": (
                "no reward information -> step returns None -> no weight update"
            ),
            "classification": MODULATION_CLASSIFICATION,
        }
