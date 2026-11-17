"""Condition E: a conventional actor-critic MLP trained with REINFORCE.

SCIENTIFIC STATUS
    This is a reference learner, not a matched control for synaptic
    plasticity. It assigns credit directly to its own parameters and sees no
    neural activity. REV3 §3.5 row 11 states that asymmetry and does not
    correct it.

The learner is deliberately small: a fully connected tanh MLP with a
four-way action head over ``{LEFT, RIGHT, JUMP, NO_ACTION}`` and a scalar
value head used as the REINFORCE baseline. It trains on the identical
unshaped game reward and the same 5-tuple environment API as every other
condition. There is no Gymnasium or Stable-Baselines3 dependency (REV3 U5).

The only imports from :mod:`readout` are two model-independent numeric
helpers (``softmax`` and ``parameter_digest``). No readout, controller or
neural feature is involved.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from readout.linear import parameter_digest, softmax

EVALUATION_ACTIONS = ("LEFT", "RIGHT", "JUMP", "NO_ACTION")
N_ACTIONS = len(EVALUATION_ACTIONS)


def discounted_returns(
    rewards: list[float] | np.ndarray,
    discount: float,
    terminal_value: float = 0.0,
) -> np.ndarray:
    """Discounted return from each step to the end of the episode."""
    values = np.asarray(rewards, dtype=np.float64).reshape(-1)
    if values.size and not np.all(np.isfinite(values)):
        raise ValueError("rewards must be finite")
    out = np.zeros(values.size, dtype=np.float64)
    running = float(terminal_value)
    for index in range(values.size - 1, -1, -1):
        running = float(values[index]) + float(discount) * running
        out[index] = running
    return out


class _Model(nn.Module):
    """Tanh trunk with a policy head and a value head."""

    def __init__(self, n_inputs: int, hidden_units: int, hidden_layers: int, seed: int):
        super().__init__()
        self.n_inputs = int(n_inputs)
        # Reproduce torch's default Linear initialisation under a private
        # generator, without disturbing the process-global RNG.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(int(seed))
            layers: list[nn.Module] = []
            width = int(n_inputs)
            for _ in range(int(hidden_layers)):
                layers.append(nn.Linear(width, int(hidden_units)))
                layers.append(nn.Tanh())
                width = int(hidden_units)
            self.trunk = nn.Sequential(*layers)
            self.actor = nn.Linear(width, N_ACTIONS)
            self.critic = nn.Linear(width, 1)

    def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.trunk(features)
        return self.actor(hidden), self.critic(hidden).squeeze(-1)


class ConventionalConfig:
    """Declared learner hyperparameters. Change only before a campaign."""

    def __init__(
        self,
        *,
        hidden_units: int = 64,
        hidden_layers: int = 2,
        learning_rate: float = 3.0e-4,
        entropy_coefficient: float = 0.01,
        value_coefficient: float = 0.5,
        discount: float = 0.99,
        max_grad_norm: float = 1.0,
    ) -> None:
        for name, value in (
            ("hidden_units", hidden_units),
            ("hidden_layers", hidden_layers),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name, value in (
            ("learning_rate", learning_rate),
            ("max_grad_norm", max_grad_norm),
        ):
            number = float(value)
            if not np.isfinite(number) or number <= 0:
                raise ValueError(f"{name} must be positive and finite")
        for name, value in (
            ("entropy_coefficient", entropy_coefficient),
            ("value_coefficient", value_coefficient),
        ):
            number = float(value)
            if not np.isfinite(number) or number < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        rate = float(discount)
        if not np.isfinite(rate) or not 0.0 <= rate <= 1.0:
            raise ValueError("discount must be in [0, 1]")
        self.hidden_units = int(hidden_units)
        self.hidden_layers = int(hidden_layers)
        self.learning_rate = float(learning_rate)
        self.entropy_coefficient = float(entropy_coefficient)
        self.value_coefficient = float(value_coefficient)
        self.discount = rate
        self.max_grad_norm = float(max_grad_norm)

    def as_dict(self) -> dict:
        return {
            "hidden_units": self.hidden_units,
            "hidden_layers": self.hidden_layers,
            "learning_rate": self.learning_rate,
            "entropy_coefficient": self.entropy_coefficient,
            "value_coefficient": self.value_coefficient,
            "discount": self.discount,
            "max_grad_norm": self.max_grad_norm,
            "algorithm": "reinforce_with_value_baseline",
            "optimizer": "adam",
            "action_selection": "categorical sample while training; argmax otherwise",
            "reward": "the unshaped game reward scalar; no shaping, no normalisation",
        }


class ConventionalAgent:
    """Categorical-policy REINFORCE with a learned value baseline."""

    def __init__(
        self,
        n_features: int,
        *,
        config: ConventionalConfig | None = None,
        seed: int | np.random.SeedSequence = 0,
        training: bool = True,
    ) -> None:
        if isinstance(n_features, bool) or not isinstance(n_features, int):
            raise ValueError("n_features must be an integer")
        if n_features < 1:
            raise ValueError("n_features must be positive")
        if isinstance(seed, bool):
            raise ValueError("seed must be an integer or a SeedSequence")
        if isinstance(seed, np.random.SeedSequence):
            sequence = seed
        else:
            sequence = np.random.SeedSequence(int(seed))
        init_sequence, sampling_sequence = sequence.spawn(2)
        init_seed = int(init_sequence.generate_state(1, np.uint32)[0])

        self.n_features = int(n_features)
        self.config = config or ConventionalConfig()
        entropy = sequence.entropy
        self.seed_entropy = (
            (int(entropy),)
            if isinstance(entropy, (int, np.integer))
            else tuple(int(value) for value in entropy)
        )
        self.network = _Model(
            self.n_features,
            self.config.hidden_units,
            self.config.hidden_layers,
            init_seed,
        )
        self.optimizer = torch.optim.Adam(
            self.network.parameters(), lr=self.config.learning_rate
        )
        self._rng = np.random.default_rng(sampling_sequence)
        self.training = bool(training)
        self.updates = 0
        self.episodes = 0
        self.reset_episode()

    # ------------------------------------------------------------------
    # episode state
    # ------------------------------------------------------------------

    def train(self) -> None:
        self.training = True

    def eval(self) -> None:
        self.training = False

    def reset_episode(self) -> None:
        self._features: list[np.ndarray] = []
        self._actions: list[int] = []
        self._rewards: list[float] = []

    def value(self, features: np.ndarray) -> float:
        vector = self._vector(features)
        with torch.no_grad():
            _, value = self.network(torch.as_tensor(vector).unsqueeze(0))
        return float(value[0])

    def _vector(self, features: np.ndarray) -> np.ndarray:
        vector = np.asarray(features, dtype=np.float32).reshape(-1)
        if vector.size != self.n_features:
            raise ValueError(
                f"observation has {vector.size} features; expected {self.n_features}"
            )
        return vector

    # ------------------------------------------------------------------
    # interaction
    # ------------------------------------------------------------------

    def act(
        self,
        features: np.ndarray,
        *,
        training: bool | None = None,
    ) -> tuple[int, dict]:
        vector = self._vector(features)
        use_training = self.training if training is None else bool(training)
        with torch.no_grad():
            logits, value = self.network(torch.as_tensor(vector).unsqueeze(0))
        logits_np = logits[0].detach().cpu().numpy().astype(np.float64)
        probabilities = softmax(logits_np)
        if use_training:
            action = int(self._rng.choice(N_ACTIONS, p=probabilities))
        else:
            action = int(np.argmax(logits_np))
        record = {
            "features": [float(entry) for entry in vector],
            "logits": [float(entry) for entry in logits_np],
            "probabilities": [float(entry) for entry in probabilities],
            "action": EVALUATION_ACTIONS[action],
            "action_index": action,
            "value": float(value[0]),
            "sampled": use_training,
        }
        if use_training:
            self._features.append(vector.copy())
            self._actions.append(action)
        return action, record

    def record_reward(self, reward: float) -> None:
        if not self.training:
            return
        number = float(reward)
        if not np.isfinite(number):
            raise ValueError("reward must be finite")
        if len(self._rewards) >= len(self._actions):
            raise ValueError("no pending action can receive a reward")
        self._rewards.append(number)

    def take_transitions(self) -> tuple[np.ndarray, np.ndarray]:
        if not self._actions:
            raise ValueError("the episode has no stored transitions")
        return np.stack(self._features), np.asarray(self._actions, dtype=np.int64)

    # ------------------------------------------------------------------
    # learning
    # ------------------------------------------------------------------

    def finish_episode(self, *, terminal_value: float = 0.0) -> dict | None:
        """Apply one REINFORCE update and clear the episode buffer."""
        if not self.training:
            return None
        if len(self._rewards) != len(self._actions):
            raise ValueError(
                "every stored action must have exactly one reward: "
                f"{len(self._actions)} actions, {len(self._rewards)} rewards"
            )
        if not self._actions:
            self.reset_episode()
            return None
        features = np.stack(self._features)
        actions = np.asarray(self._actions, dtype=np.int64)
        targets = discounted_returns(
            self._rewards, self.config.discount, float(terminal_value)
        )
        before = parameter_digest(self.network)

        logits, values = self.network(torch.as_tensor(features))
        log_probs = torch.log_softmax(logits, dim=1)
        probabilities = log_probs.exp()
        chosen = log_probs.gather(1, torch.as_tensor(actions).unsqueeze(1)).squeeze(1)
        entropy = -(probabilities * log_probs).sum(dim=1)
        target_tensor = torch.as_tensor(targets, dtype=torch.float32)
        advantage = (target_tensor - values).detach()
        policy_loss = -(chosen * advantage).mean()
        value_loss = ((values - target_tensor) ** 2).mean()
        entropy_mean = entropy.mean()
        loss = (
            policy_loss
            + self.config.value_coefficient * value_loss
            - self.config.entropy_coefficient * entropy_mean
        )

        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            self.network.parameters(), self.config.max_grad_norm
        )
        self.optimizer.step()
        self.updates += 1

        report = {
            "n_steps": int(len(self._actions)),
            "episode_reward": float(sum(self._rewards)),
            "mean_return": float(np.mean(targets)),
            "loss": float(loss.detach()),
            "policy_loss": float(policy_loss.detach()),
            "value_loss": float(value_loss.detach()),
            "entropy": float(entropy_mean.detach()),
            "grad_norm": float(grad_norm),
            "parameter_digest_before": before,
            "parameter_digest_after": parameter_digest(self.network),
            "config": self.config.as_dict(),
        }
        self.reset_episode()
        return report

    # ------------------------------------------------------------------
    # parameters and reporting
    # ------------------------------------------------------------------

    def numpy_state(self) -> dict[str, np.ndarray]:
        return {
            name: np.array(value.detach().cpu().numpy(), copy=True)
            for name, value in self.network.named_parameters()
        }

    def load_state(self, state: dict[str, np.ndarray]) -> None:
        with torch.no_grad():
            for name, value in self.network.named_parameters():
                if name not in state:
                    raise ValueError(f"state is missing parameter {name!r}")
                array = np.asarray(state[name], dtype=np.float32)
                if array.shape != tuple(value.shape):
                    raise ValueError(f"parameter {name!r} has the wrong shape")
                value.copy_(torch.as_tensor(array))

    def parameter_digest(self) -> str:
        return parameter_digest(self.network)

    def describe(self) -> dict:
        return {
            "kind": "conventional_actor_critic",
            "actions": list(EVALUATION_ACTIONS),
            "n_features": self.n_features,
            "seed_entropy": list(self.seed_entropy),
            "training": self.training,
            "updates": self.updates,
            "config": self.config.as_dict(),
            "parameter_digest": self.parameter_digest(),
            "privileged_input": False,
            "note": (
                "reference learner with direct credit assignment; not a "
                "matched control for synaptic plasticity"
            ),
        }


__all__ = [
    "ConventionalAgent",
    "ConventionalConfig",
    "EVALUATION_ACTIONS",
    "N_ACTIONS",
    "discounted_returns",
]
