"""Decision source that replaces the fixed decoder in condition F and Fβ.

SCIENTIFIC STATUS
    Every action returned here is a readout label. It is executed because the
    controlled game accepts it, not because a biological motor command was
    identified. Training the readout changes no synaptic weight.

The controller consumes the recorded ``motor_activity`` block, builds the
declared feature vector, and returns an action plus an auditable record.
Sampling happens only while ``training`` is true; evaluation is argmax.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .ablation import classify_decision
from .features import ACTION_SPACE, MotorFeatureSpec
from .linear import action_index, parameter_digest, softmax

NO_ACTION = "NO_ACTION"


class ReadoutController:
    """Turn per-decision motor activity into an action through a readout."""

    def __init__(
        self,
        model: Any,
        spec: MotorFeatureSpec | None = None,
        *,
        populations: Any,
        training: bool = True,
        seed: int = 0,
        temperature: float = 1.0,
        trainer: Any | None = None,
    ) -> None:
        if populations is None:
            raise ValueError("populations are required for accounting")
        value = float(temperature)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("temperature must be positive and finite")
        self.model = model
        self.spec = spec or MotorFeatureSpec()
        self.populations = populations
        self.training = bool(training)
        self.seed = int(seed)
        self.temperature = value
        self.trainer = trainer
        self._rng = np.random.default_rng(self.seed)
        self._transitions: list[dict] = []

    @property
    def n_features(self) -> int:
        return self.spec.n_features

    @property
    def state_independent(self) -> bool:
        return bool(getattr(self.model, "state_independent", False))

    def reset(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._transitions = []

    def decide(self, motor_activity: dict) -> tuple[str, dict]:
        if motor_activity is None:
            raise ValueError("the readout requires the motor_activity block")
        features = self.spec.vector(motor_activity)
        logits = np.asarray(
            self.model.logits(features), dtype=np.float64
        ).ravel()
        probabilities = softmax(logits, self.temperature)
        if self.training:
            index = int(
                self._rng.choice(len(ACTION_SPACE), p=probabilities)
            )
            log_prob = float(math.log(max(probabilities[index], 1e-300)))
            self._transitions.append(
                {
                    "features": features.copy(),
                    "action_index": index,
                    "log_prob": log_prob,
                    "reward": None,
                }
            )
        else:
            index = int(np.argmax(logits))
            log_prob = None
        action = ACTION_SPACE[index]
        ablation = classify_decision(
            self.model, features, action, motor_activity
        )
        record = {
            "mode": "train" if self.training else "eval",
            "action": action,
            "action_index": index,
            "sampled_action": action,
            "log_prob": log_prob,
            "features": [round(float(value), 6) for value in features],
            "feature_names": list(self.spec.names),
            "logits": [round(float(value), 6) for value in logits],
            "probabilities": [
                round(float(value), 6) for value in probabilities
            ],
            "temperature": self.temperature,
            "state_independent": self.state_independent,
            "parameter_digest": parameter_digest(self.model),
            "ablation": ablation,
        }
        return action, record

    def record_reward(self, reward: float) -> None:
        value = float(reward)
        if not math.isfinite(value):
            raise ValueError("reward must be finite")
        if not self.training:
            return
        if not self._transitions:
            raise ValueError("no pending decision can receive a reward")
        if self._transitions[-1]["reward"] is not None:
            raise ValueError("the last decision already received a reward")
        self._transitions[-1]["reward"] = value

    def take_transitions(self) -> list[dict]:
        complete = [
            item for item in self._transitions if item["reward"] is not None
        ]
        dropped = len(self._transitions) - len(complete)
        self._transitions = []
        if dropped:
            raise ValueError(
                f"{dropped} decisions were sampled without a recorded reward"
            )
        return complete

    def update(self) -> dict | None:
        if self.trainer is None:
            return None
        transitions = self.take_transitions()
        return self.trainer.update(transitions)

    def describe(self) -> dict[str, Any]:
        payload = {
            "kind": "readout_controller",
            "training": self.training,
            "seed": self.seed,
            "temperature": self.temperature,
            "state_independent": self.state_independent,
            "feature_spec": self.spec.describe(),
            "parameter_digest": parameter_digest(self.model),
            "actions": list(ACTION_SPACE),
            "note": (
                "evaluation is argmax; training samples from the categorical "
                "distribution and updates the readout only"
            ),
        }
        describe = getattr(self.model, "describe", None)
        if callable(describe):
            payload["model"] = describe()
        return payload
