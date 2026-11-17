"""Declared motor-population feature vector for the readout.

SCIENTIFIC STATUS
    The features are counts and rates of model spikes on annotated
    motor populations. They are not a measured motor command.

The readout may only see motor-population activity, never the seven sensory
features directly (Phase 8 §3.6, row 6). The default field is
``active_fraction`` because it is scale-free across populations of different
size; every other choice must be declared in config and is reported with the
episode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from motor.populations import ACTION_POPULATIONS

MOTOR_ACTIONS = tuple(ACTION_POPULATIONS)
ACTION_SPACE = (*MOTOR_ACTIONS, "NO_ACTION")

FEATURE_FIELDS = ("spikes", "active_neurons", "active_fraction", "mean_rate_hz")


@dataclass(frozen=True)
class MotorFeatureSpec:
    """Declared mapping from the motor block to the readout input vector."""

    fields: tuple[str, ...] = ("active_fraction",)

    def __post_init__(self) -> None:
        fields = tuple(str(value) for value in self.fields)
        if not fields:
            raise ValueError("at least one feature field is required")
        unknown = sorted(set(fields) - set(FEATURE_FIELDS))
        if unknown:
            raise ValueError(f"unknown motor feature fields: {unknown}")
        if len(set(fields)) != len(fields):
            raise ValueError("motor feature fields must not repeat")
        object.__setattr__(self, "fields", fields)

    @property
    def n_features(self) -> int:
        return len(MOTOR_ACTIONS) * len(self.fields)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(
            f"{action}.{field}"
            for action in MOTOR_ACTIONS
            for field in self.fields
        )

    def vector(self, motor_activity: dict) -> np.ndarray:
        if not isinstance(motor_activity, dict):
            raise ValueError("motor_activity must be the recorded block")
        values: list[float] = []
        for action in MOTOR_ACTIONS:
            if action not in motor_activity:
                raise ValueError(f"motor_activity is missing {action}")
            block = motor_activity[action]
            for field in self.fields:
                if field not in block:
                    raise ValueError(
                        f"motor_activity[{action!r}] is missing {field}"
                    )
                value = block[field]
                if isinstance(value, bool) or not isinstance(
                    value, (int, float, np.integer, np.floating)
                ):
                    raise ValueError(
                        f"motor_activity[{action!r}][{field!r}] is not numeric"
                    )
                values.append(float(value))
        return np.asarray(values, dtype=np.float32)

    def describe(self) -> dict[str, Any]:
        return {
            "model": "motor_population_feature_spec",
            "actions": list(MOTOR_ACTIONS),
            "fields": list(self.fields),
            "feature_names": list(self.names),
            "n_features": self.n_features,
            "source": "per-decision motor_activity block (§3.6.1)",
            "excluded_inputs": [
                "the seven sensory features",
                "game state",
                "previous actions",
            ],
            "classification": (
                "model motor-population activity; not a measured motor command"
            ),
        }
