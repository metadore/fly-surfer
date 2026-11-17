"""Phase 8 G4: condition-E observation encoding, learner and rollout.

Unit tests use a fake environment that exposes the same five-tuple contract as
``ControlledGameEnvironment``. One integration test drives the real game for
three steps, so the learner is checked against the actual API rather than only
against a stub.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from environment import ControlledGameEnvironment
from evaluation import (
    EVALUATION_ACTIONS,
    EXTRA_FEATURES,
    FULL_SPEC,
    MATCHED_FEATURES,
    MATCHED_SPEC,
    ConventionalAgent,
    ConventionalConfig,
    ObservationEncoder,
    ObservationSpec,
    discounted_returns,
    run_episode,
)
from readout.features import ACTION_SPACE
from sensory.game_state import (
    CoinState,
    GameState,
    ObstacleState,
    ObstacleType,
    PlayerState,
    Lane,
    TrainState,
)

SEED = 20261116


def obstacle_state() -> GameState:
    return GameState(
        player=PlayerState(lane=Lane.RIGHT, speed=0.25, jumping=True),
        obstacle=ObstacleState(
            present=True, lane=Lane.RIGHT, distance=0.75, obstacle_type=ObstacleType.HIGH
        ),
        time_ms=0.0,
    )


class FakeEnvironment:
    """Five-tuple contract identical in shape to ``ControlledGameEnvironment``."""

    def __init__(self, *, terminate_at: int | None = 4, reward: float = 0.5) -> None:
        self.terminate_at = terminate_at
        self.reward = reward
        self.seed: int | None = None
        self.last_step_reward = None
        self.game_state = GameState.neutral()
        self.steps = 0

    def reset(self, seed: int | None = None) -> dict:
        self.seed = 17 if seed is None else int(seed)
        self.steps = 0
        self.last_step_reward = None
        self.game_state = GameState.neutral()
        return {"step": 0}

    def step(self, action: str):
        if action not in (*EVALUATION_ACTIONS, "ROLL", "DUCK"):
            raise ValueError(f"unknown game action {action!r}")
        self.steps += 1
        self.game_state = GameState.neutral(time_ms=16.0 * self.steps)
        terminated = self.terminate_at is not None and self.steps >= self.terminate_at
        self.last_step_reward = SimpleNamespace(
            total=self.reward, termination_reason="collision" if terminated else None
        )
        return {"step": self.steps}, self.reward, terminated, False, {}


# ---------------------------------------------------------------------------
# observation interface
# ---------------------------------------------------------------------------


def test_feature_groups_cover_the_game_state():
    assert len(MATCHED_FEATURES) == 7
    assert len(EXTRA_FEATURES) == 7
    assert not set(MATCHED_FEATURES) & set(EXTRA_FEATURES)
    assert set(FULL_SPEC.features) == set(GameState.neutral().features())
    assert FULL_SPEC.n_features == 14
    assert MATCHED_SPEC.n_features == 7
    assert tuple(EVALUATION_ACTIONS) == tuple(ACTION_SPACE)


def test_matched_encoding_of_a_neutral_and_an_active_state():
    encoder = ObservationEncoder(MATCHED_SPEC)
    neutral = encoder.encode(GameState.neutral())
    assert neutral.dtype == np.float32
    assert neutral.shape == (7,)
    assert np.array_equal(neutral, np.zeros(7, dtype=np.float32))

    active = encoder.encode(obstacle_state())
    expected = np.asarray([0.0, 0.0, 0.0, 1.0, 1.0, 0.75, 1.0], dtype=np.float32)
    assert np.allclose(active, expected)
    assert encoder.describe()["privileged_information"] is False


def test_full_encoding_includes_the_seven_extra_features():
    encoder = ObservationEncoder(FULL_SPEC)
    state = GameState(
        player=PlayerState(lane=Lane.LEFT, speed=0.5, jumping=False, rolling=True),
        coin=CoinState(present=True, lane=Lane.CENTER, distance=0.3),
        time_ms=0.0,
    )
    vector = encoder.encode(state)
    assert vector.shape == (14,)
    extras = vector[7:]
    assert np.allclose(extras, [-1.0, 0.5, 0.0, 1.0, 1.0, 0.0, 0.3])


def test_observation_spec_validation():
    with pytest.raises(ValueError):
        ObservationSpec("bad", ("not_a_feature",))
    with pytest.raises(ValueError):
        ObservationSpec("dup", ("jumping", "jumping"))
    with pytest.raises(ValueError):
        ObservationSpec("empty", ())
    with pytest.raises(ValueError):
        ObservationEncoder(MATCHED_SPEC).encode_mapping({})
    with pytest.raises(ValueError):
        ObservationEncoder(MATCHED_SPEC).encode({"player": PlayerState()})


def test_discounted_returns_uses_the_terminal_value():
    returns = discounted_returns([0.0, 0.0, 2.0], 0.5)
    assert np.allclose(returns, [0.5, 1.0, 2.0])
    with_terminal = discounted_returns([1.0], 0.5, terminal_value=4.0)
    assert np.allclose(with_terminal, [3.0])
    assert discounted_returns([], 0.99).size == 0


# ---------------------------------------------------------------------------
# learner
# ---------------------------------------------------------------------------


def agent(seed: int = SEED, training: bool = True) -> ConventionalAgent:
    return ConventionalAgent(7, seed=seed, training=training)


def test_agent_initialisation_is_seeded_and_recorded():
    first = agent()
    second = agent()
    third = agent(seed=SEED + 1)
    assert first.parameter_digest() == second.parameter_digest()
    assert first.parameter_digest() != third.parameter_digest()
    description = first.describe()
    assert description["kind"] == "conventional_actor_critic"
    assert description["actions"] == list(EVALUATION_ACTIONS)
    assert description["privileged_input"] is False
    assert description["config"]["algorithm"] == "reinforce_with_value_baseline"
    assert description["seed_entropy"] == [SEED]


def test_same_seed_samples_the_same_actions():
    features = np.zeros(7, dtype=np.float32)
    first = agent()
    second = agent()
    first_actions = [first.act(features)[0] for _ in range(20)]
    second_actions = [second.act(features)[0] for _ in range(20)]
    assert first_actions == second_actions
    assert set(first_actions) <= set(range(4))


def test_training_episode_changes_parameters_and_clears_the_buffer():
    learner = agent()
    initial = learner.parameter_digest()
    features = np.linspace(-1.0, 1.0, 7).astype(np.float32)
    for reward in (1.0, 0.0, -1.0):
        learner.act(features)
        learner.record_reward(reward)
    report = learner.finish_episode()
    assert report is not None
    assert report["n_steps"] == 3
    assert report["episode_reward"] == pytest.approx(0.0)
    assert report["parameter_digest_before"] == initial
    assert report["parameter_digest_after"] == learner.parameter_digest()
    assert report["parameter_digest_after"] != initial
    assert report["config"]["learning_rate"] == learner.config.learning_rate
    assert learner.updates == 1
    with pytest.raises(ValueError):
        learner.take_transitions()


def test_eval_mode_neither_stores_nor_updates():
    learner = agent(training=False)
    initial = learner.parameter_digest()
    action, record = learner.act(np.zeros(7, dtype=np.float32))
    assert record["sampled"] is False
    assert action == int(np.argmax(record["logits"]))
    learner.record_reward(1.0)
    assert learner.finish_episode() is None
    assert learner.parameter_digest() == initial
    with pytest.raises(ValueError):
        learner.take_transitions()


def test_rewards_are_tied_to_pending_actions():
    learner = agent()
    with pytest.raises(ValueError):
        learner.record_reward(1.0)
    learner.act(np.zeros(7, dtype=np.float32))
    with pytest.raises(ValueError):
        learner.finish_episode()
    learner.record_reward(1.0)
    with pytest.raises(ValueError):
        learner.record_reward(1.0)
    report = learner.finish_episode()
    assert report["n_steps"] == 1


def test_state_roundtrip_restores_the_parameter_digest():
    learner = agent()
    saved = learner.numpy_state()
    initial = learner.parameter_digest()
    features = np.full(7, 0.5, dtype=np.float32)
    learner.act(features)
    learner.record_reward(1.0)
    learner.finish_episode()
    assert learner.parameter_digest() != initial
    learner.load_state(saved)
    assert learner.parameter_digest() == initial
    with pytest.raises(ValueError):
        learner.load_state({"missing": np.zeros(1)})


def test_configuration_validation():
    with pytest.raises(ValueError):
        ConventionalConfig(hidden_units=0)
    with pytest.raises(ValueError):
        ConventionalConfig(hidden_layers=0)
    with pytest.raises(ValueError):
        ConventionalConfig(learning_rate=0.0)
    with pytest.raises(ValueError):
        ConventionalConfig(discount=1.5)
    with pytest.raises(ValueError):
        ConventionalConfig(entropy_coefficient=-0.1)
    with pytest.raises(ValueError):
        ConventionalAgent(0)
    with pytest.raises(ValueError):
        ConventionalAgent(7, seed=True)


# ---------------------------------------------------------------------------
# rollout
# ---------------------------------------------------------------------------


def test_training_rollout_applies_one_update():
    environment = FakeEnvironment(terminate_at=4, reward=0.5)
    learner = agent()
    result = run_episode(
        environment,
        learner,
        ObservationEncoder(MATCHED_SPEC),
        seed=101,
        training=True,
    )
    assert result.seed == 101
    assert result.n_steps == 4
    assert result.terminated is True
    assert result.truncated is False
    assert result.termination_reason == "collision"
    assert result.total_reward == pytest.approx(2.0)
    assert sum(result.action_counts.values()) == 4
    assert result.update is not None
    assert result.update["n_steps"] == 4
    assert result.update["parameter_digest_after"] != result.update[
        "parameter_digest_before"
    ]
    assert result.steps[0].step == 1
    assert result.steps[0].action in EVALUATION_ACTIONS
    assert result.summary()["n_steps"] == 4


def test_eval_rollout_does_not_change_parameters():
    environment = FakeEnvironment(terminate_at=3)
    learner = agent(training=False)
    initial = learner.parameter_digest()
    result = run_episode(
        environment, learner, ObservationEncoder(MATCHED_SPEC), seed=102
    )
    assert result.update is None
    assert learner.parameter_digest() == initial
    assert all(len(step.probabilities) == 4 for step in result.steps)


def test_step_cap_truncates_without_inventing_termination():
    environment = FakeEnvironment(terminate_at=None)
    learner = agent(training=False)
    result = run_episode(
        environment,
        learner,
        ObservationEncoder(MATCHED_SPEC),
        max_steps=2,
        training=False,
    )
    assert result.n_steps == 2
    assert result.terminated is False
    assert result.truncated is True
    assert result.termination_reason == "rollout_step_cap"


def test_rollout_validation():
    environment = FakeEnvironment()
    learner = agent()
    with pytest.raises(ValueError):
        run_episode(
            environment,
            learner,
            ObservationEncoder(MATCHED_SPEC),
            max_steps=-1,
        )
    with pytest.raises(ValueError):
        run_episode(
            environment,
            learner,
            ObservationEncoder(FULL_SPEC),
            max_steps=1,
        )


def test_real_game_five_tuple_interface():
    environment = ControlledGameEnvironment(max_steps=3, render_mode=None)
    learner = agent(training=False)
    result = run_episode(
        environment,
        learner,
        ObservationEncoder(MATCHED_SPEC),
        seed=321,
        training=False,
        max_steps=3,
    )
    assert 1 <= result.n_steps <= 3
    assert result.terminated or result.truncated
    assert set(result.action_counts) <= set(EVALUATION_ACTIONS)
    assert result.update is None
    assert result.seed == 321
    environment.close()
