"""REINFORCE update over readout parameters only.

SCIENTIFIC STATUS
    The loss and its gradients belong to a computational classifier. The task
    reward is an external game scalar, not a dopamine measurement, and this
    update is not synaptic plasticity.

Only parameters with ``requires_grad`` are optimized. For the primary linear
readout that is every parameter; for control Fβ it is exactly the four output
biases, because the feature weights are a constant zero buffer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch

from .linear import parameter_digest


@dataclass(frozen=True)
class ReinforceConfig:
    """Declared REINFORCE parameters. Not fitted per seed."""

    learning_rate: float = 0.01
    gamma: float = 0.99

    def __post_init__(self) -> None:
        rate = float(self.learning_rate)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("learning_rate must be positive and finite")
        gamma = float(self.gamma)
        if not math.isfinite(gamma) or not 0.0 <= gamma <= 1.0:
            raise ValueError("gamma must lie in [0, 1]")
        object.__setattr__(self, "learning_rate", rate)
        object.__setattr__(self, "gamma", gamma)

    def describe(self) -> dict:
        return {
            "rule": "REINFORCE: -sum(log pi(a|s) * G_t)",
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "optimizer": "torch.optim.SGD",
            "baseline": "none",
            "trainable": "parameters with requires_grad only",
        }


def discounted_returns(rewards, gamma: float) -> np.ndarray:
    values = np.asarray(rewards, dtype=np.float64).ravel()
    step = float(gamma)
    if not math.isfinite(step) or not 0.0 <= step <= 1.0:
        raise ValueError("gamma must lie in [0, 1]")
    returns = np.zeros(values.size, dtype=np.float64)
    running = 0.0
    for index in range(values.size - 1, -1, -1):
        running = float(values[index]) + step * running
        returns[index] = running
    return returns


class ReinforceTrainer:
    """Apply one REINFORCE update to a readout's trainable parameters."""

    def __init__(
        self, model: torch.nn.Module, config: ReinforceConfig | None = None
    ) -> None:
        self.model = model
        self.config = config or ReinforceConfig()
        trainable = [
            parameter
            for parameter in model.parameters()
            if parameter.requires_grad
        ]
        if not trainable:
            raise ValueError("the readout has no trainable parameters")
        self.optimizer = torch.optim.SGD(
            trainable, lr=self.config.learning_rate
        )

    @property
    def trainable_parameter_names(self) -> list[str]:
        names = {
            id(parameter)
            for parameter in self.model.parameters()
            if parameter.requires_grad
        }
        return [
            name
            for name, parameter in self.model.named_parameters()
            if id(parameter) in names
        ]

    def update(self, transitions: list[dict]) -> dict:
        if not transitions:
            return {
                "model": "reinforce",
                "n_decisions": 0,
                "loss": None,
                "mean_return": None,
                "grad_norm": None,
                "parameter_digest_before": parameter_digest(self.model),
                "parameter_digest_after": parameter_digest(self.model),
                "trainable_parameters": self.trainable_parameter_names,
                "config": self.config.describe(),
            }
        for item in transitions:
            if item.get("reward") is None:
                raise ValueError("every transition must carry a reward")
        returns = discounted_returns(
            [item["reward"] for item in transitions], self.config.gamma
        )
        features = torch.as_tensor(
            np.stack([item["features"] for item in transitions]),
            dtype=torch.float32,
        )
        indices = torch.as_tensor(
            [item["action_index"] for item in transitions], dtype=torch.long
        )
        target = torch.as_tensor(returns, dtype=torch.float32)
        before = parameter_digest(self.model)

        logits = self.model(features)
        log_probs = torch.log_softmax(logits, dim=-1)
        chosen = log_probs[torch.arange(logits.shape[0]), indices]
        loss = -(chosen * target).mean()

        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = 0.0
        for parameter in self.model.parameters():
            if parameter.grad is not None:
                grad_norm += float(parameter.grad.detach().pow(2).sum())
        grad_norm = math.sqrt(grad_norm)
        self.optimizer.step()

        return {
            "model": "reinforce",
            "n_decisions": len(transitions),
            "loss": round(float(loss.detach()), 9),
            "mean_return": round(float(np.mean(returns)), 9),
            "grad_norm": round(grad_norm, 9),
            "parameter_digest_before": before,
            "parameter_digest_after": parameter_digest(self.model),
            "trainable_parameters": self.trainable_parameter_names,
            "config": self.config.describe(),
        }


__all__ = [
    "ReinforceConfig",
    "ReinforceTrainer",
    "discounted_returns",
]
