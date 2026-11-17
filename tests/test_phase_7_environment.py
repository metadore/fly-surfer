"""Focused tests for the Phase 7 controlled-game integration."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
import yaml

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from environment import (  # noqa: E402
    ControlledGameEnvironment,
    GameActionAdapter,
    GameEnvironmentAdapter,
    GameObservationAdapter,
    build_timeline,
)
from environment.endless_surfer import find_game_root, load_game_api  # noqa: E402
from experiments.phase_7.phase4_agent import (  # noqa: E402
    DEFAULT_ARTIFACT,
    Phase4MotorAgent,
    load_phase4_outputs,
)
from motor.action_decoder import MotorOutput  # noqa: E402
from plasticity.reward import ScriptedRewardProvider  # noqa: E402
from sensory.game_state import GameState, Lane, ObstacleType  # noqa: E402
from sensory.population_encoder import build_encoders, encode_state  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"


@pytest.fixture(scope="module")
def api():
    return load_game_api()


def make_env(api, **kwargs) -> ControlledGameEnvironment:
    kwargs.setdefault("max_steps", 40)
    return ControlledGameEnvironment(api=api, **kwargs)


def rollout(env, actions, seed=5):
    observation = env.reset(seed=seed)
    trace = []
    for action in actions:
        observation, reward, terminated, truncated, info = env.step(action)
        trace.append((observation, reward, terminated, truncated, info))
        if terminated or truncated:
            break
    return trace


def sample_observation(**overrides):
    observation = {
        "schema_version": 1,
        "player": {
            "lane": 0,
            "state": "JUMPING",
            "jump_progress": 0.5,
            "roll_progress": 0.0,
        },
        "environment": {"speed": 8.0, "distance": 10.0, "time": 1.0, "step": 60},
        "obstacles": [
            {
                "id": 1,
                "type": "BARRIER",
                "lane": 0,
                "relative_distance": 5.0,
                "width": 0.72,
                "depth": 0.65,
            },
            {
                "id": 2,
                "type": "OVERHEAD",
                "lane": 1,
                "relative_distance": 10.0,
                "width": 0.72,
                "depth": 0.65,
            },
            {
                "id": 3,
                "type": "TRAIN",
                "lane": 2,
                "relative_distance": 3.0,
                "width": 0.72,
                "depth": 0.65,
            },
            {
                "id": 4,
                "type": "BARRIER",
                "lane": 2,
                "relative_distance": 12.0,
                "width": 0.72,
                "depth": 0.65,
            },
        ],
        "coins": [
            {"id": 5, "lane": 1, "relative_distance": 2.5},
            {"id": 6, "lane": 2, "relative_distance": 7.0},
        ],
        "score": 0.0,
        "coins_collected": 0,
    }
    observation.update(overrides)
    return observation


def test_game_root_and_api(api):
    root = find_game_root()
    assert root == api.root
    assert (root / "game_env" / "environment.py").is_file()
    assert api.observation_schema_version == 1
    assert api.environment.dt == pytest.approx(1.0 / 60.0)


def test_reset_step_contract(api):
    env = make_env(api, max_steps=10)
    observation = env.reset(seed=5)
    assert observation["schema_version"] == 1
    assert env.seed == 5
    assert env.n_steps == 0
    assert isinstance(env.game_state, GameState)

    result = env.step("NO_ACTION")
    assert len(result) == 5
    observation, reward, terminated, truncated, info = result
    assert observation["environment"]["step"] == 1
    assert terminated is False and truncated is False
    assert set(info) >= {
        "events",
        "reward_components",
        "metrics",
        "termination_reason",
        "simulation_dt",
        "fly_surfer",
    }
    fly = info["fly_surfer"]
    assert fly["step"] == 1
    assert set(fly) == {
        "seed",
        "step",
        "game_state",
        "action",
        "reward",
    }
    assert fly["action"]["executed_action"] == "NO_ACTION"
    assert env.n_steps == 1
    assert len(env.conversions) == 2
    step_reward = env.last_step_reward
    assert sum(step_reward.components.values()) == pytest.approx(reward)
    assert step_reward.total == pytest.approx(reward)


def test_same_seed_reproduces_trajectory(api):
    def run():
        env = make_env(api, max_steps=200)
        trace = rollout(env, ["NO_ACTION"] * 120)
        return trace, env.recording_data

    first_trace, first_recording = run()
    second_trace, second_recording = run()
    assert first_trace == second_trace
    assert first_recording == second_recording


def test_different_seed_changes_world(api):
    env_a = make_env(api, max_steps=150)
    trace_a = rollout(env_a, ["NO_ACTION"] * 150, seed=0)
    env_b = make_env(api, max_steps=150)
    trace_b = rollout(env_b, ["NO_ACTION"] * 150, seed=1)
    assert trace_a != trace_b


def test_observation_conversion():
    adapter = GameObservationAdapter(max_speed=16.0)
    conversion = adapter.convert(sample_observation())
    state = conversion.state

    assert conversion.player_known and conversion.player_lane_known
    assert conversion.coins_available
    assert state.time_ms == pytest.approx(1000.0)
    assert state.player.lane is Lane.LEFT
    assert state.player.speed == pytest.approx(0.5)
    assert state.player.jumping and not state.player.rolling

    assert state.obstacle is not None and state.obstacle.present
    assert state.obstacle.lane is Lane.LEFT
    assert state.obstacle.obstacle_type is ObstacleType.LOW
    assert state.obstacle.distance == pytest.approx(5.0 / 25.0)

    assert state.train is not None and state.train.present
    assert state.train.lane is Lane.RIGHT
    assert state.train.distance == pytest.approx(3.0 / 25.0)

    assert state.coin is not None and state.coin.present
    assert state.coin.lane is Lane.CENTER
    assert state.coin.distance == pytest.approx(2.5 / 25.0)

    unrepresented = [item.as_dict() for item in conversion.unrepresented]
    assert {(item["kind"], item["object_id"]) for item in unrepresented} == {
        ("obstacle", 2),
        ("obstacle", 4),
        ("coin", 6),
    }
    assert "player.speed" in conversion.estimated_fields
    assert set(conversion.estimated_fields) == {
        "player.speed",
        "obstacle.distance",
        "train.distance",
        "coin.distance",
    }
    assert conversion.observation_step == 60
    assert any("normalised" in warning for warning in conversion.warnings)


def test_observation_conversion_collided_and_empty():
    adapter = GameObservationAdapter(max_speed=16.0)
    observation = sample_observation(
        player={
            "lane": 2,
            "state": "COLLIDED",
            "jump_progress": 0.0,
            "roll_progress": 0.0,
        },
        obstacles=[],
        coins=[],
    )
    conversion = adapter.convert(observation)
    assert conversion.state.obstacle is None
    assert conversion.state.train is None
    assert conversion.state.coin is None
    assert not conversion.state.player.jumping
    assert not conversion.state.player.rolling
    assert conversion.unrepresented == ()
    assert any("COLLIDED" in warning for warning in conversion.warnings)


def test_action_adapter_never_invents_actions():
    adapter = GameActionAdapter()
    assert adapter.map("left").executed_action == "LEFT"
    assert adapter.map({"state": "ROLL"}).supported
    unmapped = adapter.map({"state": "UNMAPPED"})
    assert unmapped.executed_action == "NO_ACTION"
    assert unmapped.unmapped and not unmapped.supported
    duck = adapter.map({"state": "DUCK"})
    assert duck.executed_action == "NO_ACTION" and duck.unmapped
    unknown = adapter.map({"state": "FLY"})
    assert unknown.executed_action == "NO_ACTION" and unknown.unmapped
    missing = adapter.map(None)
    assert missing.executed_action == "NO_ACTION"
    assert not missing.supported and not missing.unmapped
    invalid = adapter.map(object())
    assert invalid.executed_action == "NO_ACTION" and invalid.unmapped

    motor = MotorOutput(
        window_start_ms=0.0,
        window_end_ms=50.0,
        state="UNMAPPED",
        action="ROLL",
        supported=False,
        confidence=None,
        activation_scores={},
        raw_activation_scores={},
        active_channels=(),
        simultaneous=False,
        unresolved_channels={},
        reason="unmapped",
        evidence={},
        requested_channel="ROLL",
    )
    mapping = adapter.map(motor)
    assert mapping.requested_state == "UNMAPPED"
    assert mapping.executed_action == "NO_ACTION"
    assert mapping.channel == "ROLL"


def test_recorded_phase4_outputs_map_to_game_actions():
    records = load_phase4_outputs(DEFAULT_ARTIFACT)
    assert len(records) == 6
    adapter = GameActionAdapter()
    jump = adapter.map(records[0])
    assert jump.executed_action == "JUMP" and jump.supported
    roll_request = records[-1]
    assert roll_request["requested_channel"] == "ROLL"
    unmapped = adapter.map(roll_request)
    assert unmapped.executed_action == "NO_ACTION"
    assert unmapped.unmapped and unmapped.channel == "ROLL"


def test_environment_unmapped_and_invalid_actions(api):
    env = make_env(api, max_steps=20)
    observation = env.reset(seed=3)
    lane = observation["player"]["lane"]
    _, _, terminated, truncated, info = env.step({"state": "UNMAPPED"})
    action = info["fly_surfer"]["action"]
    assert action["requested_state"] == "UNMAPPED"
    assert action["executed_action"] == "NO_ACTION"
    assert action["unmapped"] is True
    assert env.last_mapping.unmapped
    assert not terminated and not truncated
    assert env.env.player.lane == lane

    before = env.n_steps
    with pytest.raises(api.invalid_action_error):
        env.step("FLY")
    assert env.n_steps == before

    adapter = GameEnvironmentAdapter(environment=env)
    record = adapter.step(None)
    assert record.mapping.executed_action == "NO_ACTION"
    assert record.mapping.supported is False


def test_reward_provenance_and_phase5_interfaces(api):
    config = api.difficulty(survival_reward=0.0)
    quiet = ControlledGameEnvironment(api=api, config=config, max_steps=30)
    quiet.reset(seed=5)
    for _ in range(30):
        _, reward, terminated, truncated, info = quiet.step("NO_ACTION")
        assert reward == 0.0
        assert info["reward_components"]["survival_reward"] == 0.0
        assert quiet.last_step_reward.neutral
        if terminated or truncated:
            break
    assert len(quiet.reward_function.stream) == 0
    assert quiet.reward_function.total == 0.0

    env = make_env(api, max_steps=10)
    env.reset(seed=5)
    times = []
    for _ in range(10):
        env.step("NO_ACTION")
        times.append(env.last_step_reward.time_ms)
    reward = env.reward_function
    assert reward.total == pytest.approx(0.1)
    assert len(reward.stream) == 10
    assert {item.source for item in reward.stream.deliveries} == {"gameplay"}
    assert all(
        "game_env.rewards.calculate" in item.provenance
        for item in reward.stream.deliveries
    )
    assert "not a biological dopamine" in reward.stream.classification

    provider = reward.modulation_provider()
    emitted = 0.0
    for index, time_ms in enumerate(times):
        value = provider.step(index, time_ms)
        if value is not None:
            emitted += value
    assert emitted == pytest.approx(reward.total)

    scripted = ScriptedRewardProvider(reward.schedule())
    assert scripted.step(0, times[-1]) == pytest.approx(reward.total)


def test_collision_reward_and_termination(api):
    env = ControlledGameEnvironment(api=api, max_steps=2000)
    agent = api.random_agent(seed=1000)
    adapter = GameEnvironmentAdapter(environment=env)
    run = adapter.run_episode(agent, seed=0)
    assert run.terminated and not run.truncated
    assert run.termination_reason == "collision"
    assert run.summary["collisions"] == 1
    last = run.records[-1]
    assert "collision" in last.step_reward.event_types
    assert last.step_reward.components["collision_penalty"] == pytest.approx(-1.0)
    assert last.reward == pytest.approx(-1.0)
    with pytest.raises(api.episode_ended_error):
        env.step("NO_ACTION")


def test_truncation(api):
    env = make_env(api, max_steps=5)
    env.reset(seed=1)
    for _ in range(5):
        _, _, terminated, truncated, info = env.step("NO_ACTION")
    assert not terminated and truncated
    assert info["termination_reason"] == "time_limit"
    assert env.summary()["simulation_steps"] == 5
    assert env.summary()["termination_reason"] == "time_limit"


def test_recording_and_game_replay(api, tmp_path):
    env = ControlledGameEnvironment(api=api, max_steps=150)
    agent = api.random_agent(seed=11)
    adapter = GameEnvironmentAdapter(environment=env)
    run = adapter.run_episode(agent, seed=42)
    path = env.save_recording(tmp_path / "episode.json")

    recording = api.recorder.load(path)
    assert recording["seed"] == 42
    assert recording["schema_version"] == 1
    assert len(recording["actions"]) == run.steps
    assert len(recording["observations"]) == run.steps + 1
    assert env.recording_data == recording
    assert api.replay(path) == env.summary()


def test_random_agent_reproducibility(api):
    def run():
        env = ControlledGameEnvironment(api=api, max_steps=200)
        adapter = GameEnvironmentAdapter(environment=env)
        result = adapter.run_episode(api.random_agent(seed=43), seed=42)
        return result.as_dict(), env.recording_data

    first_run, first_recording = run()
    second_run, second_recording = run()
    assert first_run == second_run
    assert first_recording == second_recording


def rule_observation(obstacles=None, coins=None, lane=1, state="RUNNING"):
    return {
        "player": {"lane": lane, "state": state},
        "obstacles": obstacles or [],
        "coins": coins or [],
    }


def test_rule_based_agent_reactions(api):
    agent = api.rule_based_agent()
    barrier = [{"type": "BARRIER", "lane": 1, "relative_distance": 0.5}]
    assert agent.act(rule_observation(barrier)).value == "JUMP"
    overhead = [{"type": "OVERHEAD", "lane": 1, "relative_distance": 0.5}]
    assert agent.act(rule_observation(overhead)).value == "ROLL"
    train = [{"type": "TRAIN", "lane": 1, "relative_distance": 1.0}]
    assert agent.act(rule_observation(train)).value == "LEFT"
    coin = [{"lane": 0, "relative_distance": 2.0}]
    assert agent.act(rule_observation(coins=coin)).value == "LEFT"
    assert agent.act(rule_observation()).value == "NO_ACTION"
    assert agent.act(rule_observation(state="JUMPING", obstacles=barrier)).value == (
        "NO_ACTION"
    )


def test_headless_and_rendered_outcomes_match(api):
    pygame = pytest.importorskip("pygame")

    def run(render: bool):
        env = ControlledGameEnvironment(api=api, max_steps=40)
        env.reset(seed=8)
        trace = []
        try:
            for _ in range(40):
                observation, reward, terminated, truncated, _ = env.step(
                    "NO_ACTION"
                )
                trace.append((observation, reward, terminated, truncated))
                if render:
                    env.render()
                if terminated or truncated:
                    break
        finally:
            env.close()
        return trace

    try:
        rendered = run(True)
    except pygame.error as exc:
        pytest.skip(f"pygame display unavailable: {exc}")
    assert rendered == run(False)


def test_timeline_and_phase3_encoders(api):
    env = make_env(api, max_steps=12)
    env.reset(seed=5)
    for _ in range(12):
        env.step("NO_ACTION")
    timeline = env.timeline()
    assert len(timeline) == 13
    times = [time_ms for time_ms, _ in timeline]
    assert times == sorted(times)
    assert len(set(times)) == len(times)
    assert all(isinstance(state, GameState) for _, state in timeline)

    config = yaml.safe_load(SENSORY_CONFIG.read_text(encoding="utf-8"))
    encoders = build_encoders(config["features"])
    responses = encode_state(timeline[-1][1].features(), encoders)
    assert set(responses) == set(encoders)
    for values in responses.values():
        assert values.ndim == 1 and values.size > 0
        assert np.all(np.isfinite(values))
        assert np.all((values >= 0.0) & (values <= 1.0))


def test_build_timeline_keeps_last_state_for_repeated_time():
    adapter = GameObservationAdapter(max_speed=16.0)
    first = adapter.convert(sample_observation())
    changed = sample_observation()
    changed["player"]["lane"] = 2
    second = adapter.convert(changed)
    timeline = build_timeline([first, second])
    assert len(timeline) == 1
    assert timeline[0][1].player.lane is Lane.RIGHT


def test_phase4_outputs_drive_an_episode(api):
    env = ControlledGameEnvironment(api=api, max_steps=30)
    agent = Phase4MotorAgent(load_phase4_outputs(DEFAULT_ARTIFACT))
    run = GameEnvironmentAdapter(environment=env).run_episode(agent, seed=42)
    assert run.steps == 30
    assert run.truncated and not run.terminated
    assert run.action_counts == {"JUMP": 20, "NO_ACTION": 10}
    unmapped = [
        record
        for record in run.records
        if record.mapping is not None and record.mapping.unmapped
    ]
    assert len(unmapped) == 5
    assert all(record.mapping.executed_action == "NO_ACTION" for record in unmapped)
    assert all(record.mapping.channel == "ROLL" for record in unmapped)
    assert json.dumps(run.as_dict(), sort_keys=True)
