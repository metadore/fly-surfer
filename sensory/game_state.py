"""Validated environment snapshots for Phase 3A sensory encoding.

The representation is independent of the neural simulation. It describes a
simplified endless-runner scene with normalised conventions chosen for the
experiment: ``distance`` is 0 at the player and 1 far away, ``speed`` is 0..1
of a nominal maximum. These are game-design conventions, not measurements of
a real game or of the fly.

Validation is deliberately strict. A state that contradicts itself (an object
marked absent but given a lane, a player both jumping and rolling, a distance
outside its range) raises ``ValueError`` instead of being silently repaired.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Mapping

LANE_NAMES = ("left", "center", "right")
OBSTACLE_TYPE_NAMES = ("low", "high")


class Lane(IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2


class ObstacleType(IntEnum):
    LOW = 0
    HIGH = 1


def parse_lane(value: Any) -> Lane:
    if isinstance(value, Lane):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        if key in LANE_NAMES:
            return Lane(LANE_NAMES.index(key))
        raise ValueError(f"unknown lane {value!r}; expected one of {LANE_NAMES}")
    if isinstance(value, bool):
        raise ValueError(f"invalid lane {value!r}")
    if isinstance(value, int) and 0 <= value < len(LANE_NAMES):
        return Lane(value)
    raise ValueError(f"invalid lane {value!r}")


def parse_obstacle_type(value: Any) -> ObstacleType:
    if isinstance(value, ObstacleType):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        if key in OBSTACLE_TYPE_NAMES:
            return ObstacleType(OBSTACLE_TYPE_NAMES.index(key))
        raise ValueError(
            f"unknown obstacle type {value!r}; expected one of {OBSTACLE_TYPE_NAMES}"
        )
    if isinstance(value, bool):
        raise ValueError(f"invalid obstacle type {value!r}")
    if isinstance(value, int) and 0 <= value < len(OBSTACLE_TYPE_NAMES):
        return ObstacleType(value)
    raise ValueError(f"invalid obstacle type {value!r}")


def _unit_interval(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1], got {value!r}")
    return number


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool, got {value!r}")
    return value


@dataclass(frozen=True)
class PlayerState:
    """Player pose and normalised forward speed."""

    lane: Lane = Lane.CENTER
    speed: float = 0.5
    jumping: bool = False
    rolling: bool = False

    def __post_init__(self) -> None:
        lane = parse_lane(self.lane)
        speed = _unit_interval(self.speed, "speed")
        jumping = _boolean(self.jumping, "jumping")
        rolling = _boolean(self.rolling, "rolling")
        if jumping and rolling:
            raise ValueError("player cannot jump and roll in the same state")
        object.__setattr__(self, "lane", lane)
        object.__setattr__(self, "speed", speed)


@dataclass(frozen=True)
class ObstacleState:
    """A track obstacle. Absent obstacles must not carry object data."""

    present: bool = False
    lane: Lane | None = None
    distance: float | None = None
    obstacle_type: ObstacleType | None = None

    def __post_init__(self) -> None:
        present = _boolean(self.present, "obstacle.present")
        if present:
            if self.lane is None or self.distance is None:
                raise ValueError(
                    "a present obstacle requires both lane and distance"
                )
            lane = parse_lane(self.lane)
            distance = _unit_interval(self.distance, "obstacle.distance")
            obstacle_type = (
                ObstacleType.LOW
                if self.obstacle_type is None
                else parse_obstacle_type(self.obstacle_type)
            )
            object.__setattr__(self, "lane", lane)
            object.__setattr__(self, "distance", distance)
            object.__setattr__(self, "obstacle_type", obstacle_type)
        else:
            if any(
                value is not None
                for value in (self.lane, self.distance, self.obstacle_type)
            ):
                raise ValueError(
                    "an absent obstacle must not specify lane, distance or type"
                )


@dataclass(frozen=True)
class TrainState:
    """An approaching train. Absent trains must not carry object data."""

    present: bool = False
    lane: Lane | None = None
    distance: float | None = None

    def __post_init__(self) -> None:
        present = _boolean(self.present, "train.present")
        if present:
            if self.lane is None or self.distance is None:
                raise ValueError("a present train requires both lane and distance")
            object.__setattr__(self, "lane", parse_lane(self.lane))
            object.__setattr__(
                self, "distance", _unit_interval(self.distance, "train.distance")
            )
        elif self.lane is not None or self.distance is not None:
            raise ValueError("an absent train must not specify lane or distance")


@dataclass(frozen=True)
class CoinState:
    """A collectable coin. Absent coins must not carry object data."""

    present: bool = False
    lane: Lane | None = None
    distance: float | None = None

    def __post_init__(self) -> None:
        present = _boolean(self.present, "coin.present")
        if present:
            if self.lane is None or self.distance is None:
                raise ValueError("a present coin requires both lane and distance")
            object.__setattr__(self, "lane", parse_lane(self.lane))
            object.__setattr__(
                self, "distance", _unit_interval(self.distance, "coin.distance")
            )
        elif self.lane is not None or self.distance is not None:
            raise ValueError("an absent coin must not specify lane or distance")


@dataclass(frozen=True)
class GameState:
    """One validated snapshot of the simplified environment."""

    player: PlayerState = PlayerState()
    obstacle: ObstacleState | None = None
    train: TrainState | None = None
    coin: CoinState | None = None
    time_ms: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.player, PlayerState):
            raise ValueError("player must be a PlayerState")
        for name, value, expected in (
            ("obstacle", self.obstacle, ObstacleState),
            ("train", self.train, TrainState),
            ("coin", self.coin, CoinState),
        ):
            if value is not None and not isinstance(value, expected):
                raise ValueError(f"{name} must be a {expected.__name__} or None")
        if isinstance(self.time_ms, bool) or not isinstance(
            self.time_ms, (int, float)
        ):
            raise ValueError("time_ms must be a number")
        time_ms = float(self.time_ms)
        if not math.isfinite(time_ms) or time_ms < 0:
            raise ValueError("time_ms must be finite and non-negative")
        object.__setattr__(self, "time_ms", time_ms)

    @classmethod
    def neutral(cls, time_ms: float = 0.0) -> "GameState":
        """An empty track with the player centred at half speed."""
        return cls(player=PlayerState(), time_ms=time_ms)

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any], time_ms: float = 0.0
    ) -> "GameState":
        """Build a state from configuration-style dictionaries."""
        if not isinstance(payload, Mapping):
            raise ValueError("state payload must be a mapping")
        player_payload = payload.get("player") or {}
        player = PlayerState(
            lane=player_payload.get("lane", Lane.CENTER),
            speed=player_payload.get("speed", 0.5),
            jumping=player_payload.get("jumping", False),
            rolling=player_payload.get("rolling", False),
        )

        def object_state(name, factory):
            value = payload.get(name)
            if value is None:
                return factory()
            if not isinstance(value, Mapping):
                raise ValueError(f"{name} must be a mapping or null")
            return factory(**value)

        obstacle = object_state("obstacle", ObstacleState)
        train = object_state("train", TrainState)
        coin = object_state("coin", CoinState)
        return cls(
            player=player,
            obstacle=obstacle,
            train=train,
            coin=coin,
            time_ms=payload.get("time_ms", time_ms),
        )

    def features(self) -> dict[str, float | int | None]:
        """Flatten the state to the features the encoders consume.

        Booleans are 0/1 floats. Values that only exist when an object is
        present are ``None``; encoders emit their baseline response for them
        instead of inventing a lane or distance.
        """
        obstacle = self.obstacle
        train = self.train
        coin = self.coin
        return {
            "player_lane": int(self.player.lane),
            "player_speed": self.player.speed,
            "jumping": float(self.player.jumping),
            "rolling": float(self.player.rolling),
            "obstacle_present": float(bool(obstacle and obstacle.present)),
            "obstacle_lane": (
                int(obstacle.lane) if obstacle and obstacle.present else None
            ),
            "obstacle_distance": (
                obstacle.distance if obstacle and obstacle.present else None
            ),
            "obstacle_type": (
                int(obstacle.obstacle_type)
                if obstacle and obstacle.present
                else None
            ),
            "train_present": float(bool(train and train.present)),
            "train_lane": int(train.lane) if train and train.present else None,
            "train_distance": (
                train.distance if train and train.present else None
            ),
            "coin_present": float(bool(coin and coin.present)),
            "coin_lane": int(coin.lane) if coin and coin.present else None,
            "coin_distance": coin.distance if coin and coin.present else None,
        }
