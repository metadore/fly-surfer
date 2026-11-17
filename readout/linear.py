"""Linear readouts over {LEFT, RIGHT, JUMP, NO_ACTION}.

SCIENTIFIC STATUS
    Logits and probabilities are outputs of a computational classifier. They
    are not action potentials of identified neurons and not a biological action
    selection mechanism.

``LinearReadout``
    the primary condition-F readout: a linear map from motor features to four
    logits. Every parameter is trainable.

``BiasOnlyReadout``
    control Fβ: the forward pass never reads the feature vector, the feature
    weights are a constant zero buffer, and the only trainable parameter is the
    four-way output bias. The action distribution is therefore provably
    independent of motor activity.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

import numpy as np
import torch
from torch import nn

from .features import ACTION_SPACE, MOTOR_ACTIONS

N_ACTIONS = len(ACTION_SPACE)
NO_ACTION_INDEX = ACTION_SPACE.index("NO_ACTION")


def argmax_action(logits: np.ndarray) -> str:
    values = np.asarray(logits, dtype=np.float64).ravel()
    if values.size != N_ACTIONS:
        raise ValueError(f"logits must have {N_ACTIONS} entries")
    return ACTION_SPACE[int(np.argmax(values))]


def action_index(action: str) -> int:
    name = str(action).strip().upper()
    if name not in ACTION_SPACE:
        raise ValueError(f"action must be one of {ACTION_SPACE}")
    return ACTION_SPACE.index(name)


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    value = float(temperature)
    if not np.isfinite(value) or value <= 0:
        raise ValueError("temperature must be positive and finite")
    scaled = np.asarray(logits, dtype=np.float64).ravel() / value
    shifted = scaled - scaled.max()
    weights = np.exp(shifted)
    return weights / weights.sum()


def _digest_state(named: Iterable[tuple[str, torch.Tensor]]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(named, key=lambda item: item[0]):
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("utf-8"))
        digest.update(str(array.shape).encode("utf-8"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def parameter_digest(model: nn.Module) -> str:
    return _digest_state(model.named_parameters())


class LinearReadout(nn.Module):
    """Primary readout: ``logits = features @ W.T + b``."""

    state_independent = False

    def __init__(
        self,
        n_features: int,
        *,
        seed: int = 0,
        init_std: float = 0.01,
    ) -> None:
        super().__init__()
        if isinstance(n_features, bool) or not isinstance(n_features, int):
            raise ValueError("n_features must be an integer")
        if n_features < 1:
            raise ValueError("n_features must be positive")
        std = float(init_std)
        if not np.isfinite(std) or std < 0:
            raise ValueError("init_std must be finite and non-negative")
        generator = torch.Generator().manual_seed(int(seed))
        weights = torch.randn(
            N_ACTIONS, n_features, generator=generator
        ) * std
        self.feature_weights = nn.Parameter(weights)
        self.bias = nn.Parameter(torch.zeros(N_ACTIONS))
        self.n_features = int(n_features)
        self.init_std = std
        self.seed = int(seed)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        values = torch.as_tensor(features, dtype=self.feature_weights.dtype)
        if values.ndim == 1:
            values = values.unsqueeze(0)
        if int(values.shape[-1]) != self.n_features:
            raise ValueError("feature width does not match the readout")
        return values @ self.feature_weights.t() + self.bias

    # -- numpy surface used by the controller and the analysis -----------
    def logits(self, features: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            return self.forward(
                torch.as_tensor(np.atleast_2d(features), dtype=torch.float32)
            ).numpy()

    def numpy_state(self) -> dict[str, np.ndarray]:
        return {
            name: np.array(value.detach().cpu().numpy(), copy=True)
            for name, value in self.named_parameters()
        }

    def trainable_parameters(self) -> list[nn.Parameter]:
        return [value for value in self.parameters() if value.requires_grad]

    def parameter_names(self) -> list[str]:
        return [name for name, _ in self.named_parameters()]

    def describe(self) -> dict[str, Any]:
        return {
            "kind": "linear_readout",
            "actions": list(ACTION_SPACE),
            "n_features": self.n_features,
            "init_std": self.init_std,
            "seed": self.seed,
            "trainable_parameters": self.parameter_names(),
            "parameter_digest": parameter_digest(self),
            "state_independent": False,
            "logit_rule": "logits = features @ W.T + bias",
        }


class BiasOnlyReadout(nn.Module):
    """Control Fβ: only four output biases are trainable.

    The forward pass does not read ``features``. The zero feature-weight buffer
    exists only so the record can show the parameter is fixed at exactly 0.
    """

    state_independent = True

    def __init__(self, n_features: int, *, seed: int = 0) -> None:
        super().__init__()
        if isinstance(n_features, bool) or not isinstance(n_features, int):
            raise ValueError("n_features must be an integer")
        if n_features < 1:
            raise ValueError("n_features must be positive")
        self.n_features = int(n_features)
        self.seed = int(seed)
        self.register_buffer(
            "fixed_feature_weights", torch.zeros(N_ACTIONS, n_features)
        )
        self.bias = nn.Parameter(torch.zeros(N_ACTIONS))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        values = torch.as_tensor(features, dtype=self.bias.dtype)
        batch = 1 if values.ndim == 1 else int(values.shape[0])
        if int(values.shape[-1]) != self.n_features:
            raise ValueError("feature width does not match the readout")
        return self.bias.unsqueeze(0).expand(batch, N_ACTIONS).clone()

    def logits(self, features: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            return self.forward(
                torch.as_tensor(np.atleast_2d(features), dtype=torch.float32)
            ).numpy()

    @property
    def feature_weights(self) -> torch.Tensor:
        return self.fixed_feature_weights

    def numpy_state(self) -> dict[str, np.ndarray]:
        state = {
            name: np.array(value.detach().cpu().numpy(), copy=True)
            for name, value in self.named_parameters()
        }
        state["fixed_feature_weights"] = np.array(
            self.fixed_feature_weights.cpu().numpy(), copy=True
        )
        return state

    def trainable_parameters(self) -> list[nn.Parameter]:
        return [value for value in self.parameters() if value.requires_grad]

    def parameter_names(self) -> list[str]:
        return [name for name, _ in self.named_parameters()]

    def assert_state_independent(self) -> dict[str, Any]:
        trainable = self.trainable_parameters()
        fixed = torch.count_nonzero(self.fixed_feature_weights).item()
        checks = {
            "single_trainable_tensor": len(trainable) == 1,
            "trainable_is_bias": trainable[0] is self.bias,
            "feature_weights_exactly_zero": int(fixed) == 0,
            "feature_weights_not_trainable": (
                not self.fixed_feature_weights.requires_grad
            ),
        }
        failures = [name for name, ok in checks.items() if not ok]
        if failures:
            raise ValueError(f"bias-only readout invariant failures: {failures}")
        return checks

    def describe(self) -> dict[str, Any]:
        return {
            "kind": "bias_only_readout",
            "actions": list(ACTION_SPACE),
            "n_features": self.n_features,
            "trainable_parameters": self.parameter_names(),
            "feature_weights": "fixed at exactly 0.0, excluded from optimizer",
            "parameter_digest": parameter_digest(self),
            "state_independent": True,
            "logit_rule": "logits = bias for every feature vector, including 0",
        }


def make_readout(
    kind: str,
    n_features: int,
    *,
    seed: int = 0,
    init_std: float = 0.01,
) -> nn.Module:
    name = str(kind).strip().lower()
    if name in ("linear", "f"):
        return LinearReadout(n_features, seed=seed, init_std=init_std)
    if name in ("bias_only", "bias-only", "fbeta", "f_beta"):
        return BiasOnlyReadout(n_features, seed=seed)
    raise ValueError(f"unknown readout kind {kind!r}")


__all__ = [
    "ACTION_SPACE",
    "BiasOnlyReadout",
    "LinearReadout",
    "MOTOR_ACTIONS",
    "N_ACTIONS",
    "NO_ACTION_INDEX",
    "action_index",
    "argmax_action",
    "make_readout",
    "parameter_digest",
    "softmax",
]
