"""Validated game-state representation and feature flattening."""

from __future__ import annotations

import pytest

from sensory.game_state import (
    CoinState,
    GameState,
    Lane,
    ObstacleState,
    ObstacleType,
    PlayerState,
    TrainState,
    parse_lane,
    parse_obstacle_type,
)


def test_defaults_and_neutral_state() -> None:
    player = PlayerState()
    assert player.lane is Lane.CENTER
    assert player.speed == pytest.approx(0.5)
    assert not player.jumping and not player.rolling

    state = GameState.neutral()
    assert state.player == player
    assert state.obstacle is None
    assert state.time_ms == 0.0


def test_lane_and_obstacle_type_parsing() -> None:
    assert parse_lane("left") is Lane.LEFT
    assert parse_lane(" CENTER ") is Lane.CENTER
    assert parse_lane(2) is Lane.RIGHT
    assert parse_obstacle_type("high") is ObstacleType.HIGH
    assert parse_obstacle_type(0) is ObstacleType.LOW
    for value in ("up", 3, True):
        with pytest.raises(ValueError):
            parse_lane(value)
    for value in ("medium", 2, False):
        with pytest.raises(ValueError):
            parse_obstacle_type(value)


def test_player_validation() -> None:
    with pytest.raises(ValueError):
        PlayerState(jumping=True, rolling=True)
    for speed in (-0.1, 1.1, True, "fast"):
        with pytest.raises(ValueError):
            PlayerState(speed=speed)


def test_absent_objects_must_not_carry_data() -> None:
    with pytest.raises(ValueError):
        ObstacleState(present=False, lane=Lane.LEFT)
    with pytest.raises(ValueError):
        TrainState(present=False, distance=0.5)
    with pytest.raises(ValueError):
        CoinState(present=False, lane=Lane.RIGHT)


def test_present_objects_require_position() -> None:
    with pytest.raises(ValueError):
        ObstacleState(present=True, lane=Lane.LEFT)
    with pytest.raises(ValueError):
        TrainState(present=True, distance=0.5)
    with pytest.raises(ValueError):
        CoinState(present=True, lane=Lane.CENTER)


def test_present_obstacle_defaults_to_low_type() -> None:
    obstacle = ObstacleState(
        present=True, lane="right", distance=0.4, obstacle_type="high"
    )
    assert obstacle.lane is Lane.RIGHT
    assert obstacle.obstacle_type is ObstacleType.HIGH
    default = ObstacleState(present=True, lane="left", distance=0.2)
    assert default.obstacle_type is ObstacleType.LOW


def test_game_state_from_dict_and_features() -> None:
    state = GameState.from_dict(
        {
            "player": {"lane": "left", "speed": 0.9, "jumping": True},
            "obstacle": {
                "present": True,
                "lane": "center",
                "distance": 0.3,
                "obstacle_type": "high",
            },
            "coin": {"present": True, "lane": "right", "distance": 0.6},
        },
        time_ms=12.5,
    )
    assert state.time_ms == 12.5
    features = state.features()
    assert features["player_lane"] == int(Lane.LEFT)
    assert features["player_speed"] == pytest.approx(0.9)
    assert features["jumping"] == 1.0
    assert features["obstacle_present"] == 1.0
    assert features["obstacle_lane"] == int(Lane.CENTER)
    assert features["obstacle_type"] == int(ObstacleType.HIGH)
    assert features["train_present"] == 0.0
    assert features["train_lane"] is None
    assert features["train_distance"] is None
    assert features["coin_lane"] == int(Lane.RIGHT)


def test_game_state_validates_component_types() -> None:
    with pytest.raises(ValueError):
        GameState(player={"lane": "left"})
    with pytest.raises(ValueError):
        GameState(obstacle=CoinState())
    with pytest.raises(ValueError):
        GameState(time_ms=-1.0)
    with pytest.raises(ValueError):
        GameState.from_dict({"obstacle": "near"})
