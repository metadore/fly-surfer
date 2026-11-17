"""Convert a game observation into the existing Phase 3A ``GameState``.

The observation schema is the game's versioned v1 mapping. Only information
present in that mapping is used; unspawned future objects are not visible there
and are never inferred. The game exposes world-unit distances in the range
``[-1.0, 25.0]``, while ``GameState`` requires normalised distances, so each
distance is divided by a declared horizon. That normalisation is an experiment
convention, not a metric or game measurement.

The single-object schema can hold one obstacle, one train and one coin at a
time. Additional visible objects and anything the schema cannot express are
reported in ``unrepresented`` instead of being dropped silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from sensory.game_state import (
    LANE_NAMES,
    CoinState,
    GameState,
    Lane,
    ObstacleState,
    ObstacleType,
    PlayerState,
    TrainState,
)

DEFAULT_DISTANCE_HORIZON = 25.0

# BARRIER is cleared by jumping and OVERHEAD by rolling, matching the game's
# collision rule and the low/high obstacle distinction in GameState.
OBSTACLE_TYPES = {
    "BARRIER": ObstacleType.LOW,
    "OVERHEAD": ObstacleType.HIGH,
}

_SELECTABLE_OBSTACLE_TYPES = frozenset((*OBSTACLE_TYPES, "TRAIN"))


@dataclass(frozen=True)
class UnrepresentedObject:
    """A visible game object the ``GameState`` schema cannot carry."""

    kind: str
    object_id: int | None
    lane: int | None
    reason: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "object_id": self.object_id,
            "lane": self.lane,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ObservationConversion:
    """A ``GameState`` plus the assumptions made while converting."""

    state: GameState
    player_known: bool
    player_lane_known: bool
    coins_available: bool
    distance_horizon: float
    estimated_fields: tuple[str, ...] = ()
    unrepresented: tuple[UnrepresentedObject, ...] = ()
    warnings: tuple[str, ...] = ()
    observation_step: int | None = None

    def as_dict(self) -> dict:
        return {
            "state": state_as_dict(self.state),
            "player_known": self.player_known,
            "player_lane_known": self.player_lane_known,
            "coins_available": self.coins_available,
            "distance_horizon": self.distance_horizon,
            "estimated_fields": list(self.estimated_fields),
            "unrepresented": [item.as_dict() for item in self.unrepresented],
            "warnings": list(self.warnings),
            "observation_step": self.observation_step,
        }


def state_as_dict(state: GameState) -> dict:
    obstacle = state.obstacle
    train = state.train
    coin = state.coin
    return {
        "time_ms": state.time_ms,
        "player": {
            "lane": int(state.player.lane),
            "lane_name": LANE_NAMES[int(state.player.lane)],
            "speed": state.player.speed,
            "jumping": state.player.jumping,
            "rolling": state.player.rolling,
        },
        "obstacle": (
            {
                "present": True,
                "lane": int(obstacle.lane),
                "distance": obstacle.distance,
                "type": int(obstacle.obstacle_type),
                "type_name": ("low", "high")[int(obstacle.obstacle_type)],
            }
            if obstacle is not None and obstacle.present
            else None
        ),
        "train": (
            {
                "present": True,
                "lane": int(train.lane),
                "distance": train.distance,
            }
            if train is not None and train.present
            else None
        ),
        "coin": (
            {
                "present": True,
                "lane": int(coin.lane),
                "distance": coin.distance,
            }
            if coin is not None and coin.present
            else None
        ),
    }


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


class GameObservationAdapter:
    """Build one ``GameState`` from one game observation."""

    def __init__(
        self,
        *,
        max_speed: float,
        distance_horizon: float = DEFAULT_DISTANCE_HORIZON,
    ) -> None:
        speed = _finite(max_speed, "max_speed")
        if speed <= 0:
            raise ValueError("max_speed must be positive")
        horizon = _finite(distance_horizon, "distance_horizon")
        if horizon <= 0:
            raise ValueError("distance_horizon must be positive")
        self.max_speed = speed
        self.distance_horizon = horizon

    def _distance(self, z: Any, label: str) -> float:
        value = _finite(z, label)
        return min(1.0, max(0.0, value / self.distance_horizon))

    def _select(
        self,
        candidates: Sequence[tuple[float, int, Any]],
        label: str,
        unrepresented: list[UnrepresentedObject],
        estimated: list[str],
    ):
        if not candidates:
            return None
        ordered = sorted(candidates, key=lambda item: (item[0], item[1]))
        distance, object_id, obj = ordered[0]
        estimated.append(f"{label}.distance")
        for _, other_id, other in ordered[1:]:
            unrepresented.append(
                UnrepresentedObject(
                    kind=label,
                    object_id=other_id,
                    lane=other.get("lane"),
                    reason=(
                        f"only the nearest {label} is representable by the "
                        "single-object GameState"
                    ),
                )
            )
        return distance, obj

    def convert(
        self, observation: Mapping[str, Any], *, time_ms: float | None = None
    ) -> ObservationConversion:
        if not isinstance(observation, Mapping):
            raise ValueError("observation must be a mapping")
        player = observation.get("player")
        environment = observation.get("environment")
        if not isinstance(player, Mapping) or not isinstance(environment, Mapping):
            raise ValueError("observation is missing player or environment data")
        lane_value = player.get("lane")
        if isinstance(lane_value, bool) or lane_value not in (0, 1, 2):
            raise ValueError(f"invalid player lane {lane_value!r}")
        state_name = str(player.get("state", ""))
        if state_name not in ("RUNNING", "JUMPING", "ROLLING", "COLLIDED"):
            raise ValueError(f"invalid player state {state_name!r}")

        warnings: list[str] = []
        estimated: list[str] = []
        unrepresented: list[UnrepresentedObject] = []

        speed_units = _finite(environment.get("speed"), "environment.speed")
        speed = min(1.0, max(0.0, speed_units / self.max_speed))
        estimated.append("player.speed")
        jumping = state_name == "JUMPING"
        rolling = state_name == "ROLLING"
        if state_name == "COLLIDED":
            warnings.append(
                "The game reports the player as COLLIDED; the GameState "
                "schema has no collision state, so jumping and rolling are "
                "both false."
            )
        player_state = PlayerState(
            lane=Lane(int(lane_value)),
            speed=speed,
            jumping=jumping,
            rolling=rolling,
        )

        if time_ms is None:
            seconds = _finite(environment.get("time", 0.0), "environment.time")
            time_ms = seconds * 1000.0
        else:
            time_ms = _finite(time_ms, "time_ms")

        obstacles = observation.get("obstacles", [])
        if not isinstance(obstacles, Sequence) or isinstance(obstacles, (str, bytes)):
            raise ValueError("observation obstacles must be a list")
        obstacle_candidates: list[tuple[float, int, Mapping]] = []
        train_candidates: list[tuple[float, int, Mapping]] = []
        for position, raw in enumerate(obstacles):
            if not isinstance(raw, Mapping):
                raise ValueError(f"obstacle {position} is not a mapping")
            kind = str(raw.get("type", "")).upper()
            object_id = raw.get("id")
            object_id = (
                int(object_id)
                if isinstance(object_id, int) and not isinstance(object_id, bool)
                else -1
            )
            lane = raw.get("lane")
            if kind not in _SELECTABLE_OBSTACLE_TYPES:
                unrepresented.append(
                    UnrepresentedObject(
                        kind="obstacle",
                        object_id=object_id,
                        lane=lane if lane in (0, 1, 2) else None,
                        reason=f"unknown game obstacle type {kind!r}",
                    )
                )
                continue
            if lane not in (0, 1, 2) or isinstance(lane, bool):
                unrepresented.append(
                    UnrepresentedObject(
                        kind="obstacle",
                        object_id=object_id,
                        lane=None,
                        reason=f"invalid obstacle lane {lane!r}",
                    )
                )
                continue
            distance = self._distance(
                raw.get("relative_distance"),
                f"obstacles[{position}].relative_distance",
            )
            if kind == "TRAIN":
                train_candidates.append((distance, object_id, raw))
            else:
                obstacle_candidates.append((distance, object_id, raw))

        obstacle = None
        selected = self._select(
            obstacle_candidates, "obstacle", unrepresented, estimated
        )
        if selected is not None:
            distance, raw = selected
            kind = str(raw.get("type", "")).upper()
            obstacle = ObstacleState(
                present=True,
                lane=Lane(int(raw["lane"])),
                distance=distance,
                obstacle_type=OBSTACLE_TYPES[kind],
            )

        train = None
        selected = self._select(
            train_candidates, "train", unrepresented, estimated
        )
        if selected is not None:
            distance, raw = selected
            train = TrainState(
                present=True,
                lane=Lane(int(raw["lane"])),
                distance=distance,
            )

        coins = observation.get("coins", [])
        if not isinstance(coins, Sequence) or isinstance(coins, (str, bytes)):
            raise ValueError("observation coins must be a list")
        coins_available = "coins" in observation
        coin_candidates: list[tuple[float, int, Mapping]] = []
        for position, raw in enumerate(coins):
            if not isinstance(raw, Mapping):
                raise ValueError(f"coin {position} is not a mapping")
            lane = raw.get("lane")
            object_id = raw.get("id")
            object_id = (
                int(object_id)
                if isinstance(object_id, int) and not isinstance(object_id, bool)
                else -1
            )
            if lane not in (0, 1, 2) or isinstance(lane, bool):
                unrepresented.append(
                    UnrepresentedObject(
                        kind="coin",
                        object_id=object_id,
                        lane=None,
                        reason=f"invalid coin lane {lane!r}",
                    )
                )
                continue
            distance = self._distance(
                raw.get("relative_distance"),
                f"coins[{position}].relative_distance",
            )
            coin_candidates.append((distance, object_id, raw))
        coin = None
        selected = self._select(coin_candidates, "coin", unrepresented, estimated)
        if selected is not None:
            distance, raw = selected
            coin = CoinState(
                present=True,
                lane=Lane(int(raw["lane"])),
                distance=distance,
            )

        if self.distance_horizon != DEFAULT_DISTANCE_HORIZON:
            warnings.append(
                "Game distances are normalised by a declared "
                f"{self.distance_horizon:g}-unit horizon; they are not metric "
                "or game distances."
            )
        else:
            warnings.append(
                "Game distances are normalised by the declared "
                f"{DEFAULT_DISTANCE_HORIZON:g}-unit observation horizon; they "
                "are not metric or game distances."
            )
        warnings.append(
            "Player speed is normalised by the configured maximum speed "
            f"{self.max_speed:g}; jumping and rolling are read directly from "
            "the player state."
        )
        if unrepresented:
            warnings.append(
                f"{len(unrepresented)} visible game object(s) are not "
                "represented by the single-object GameState; see "
                "'unrepresented'."
            )

        state = GameState(
            player=player_state,
            obstacle=obstacle,
            train=train,
            coin=coin,
            time_ms=time_ms,
        )
        step_value = environment.get("step")
        observation_step = (
            int(step_value)
            if isinstance(step_value, int) and not isinstance(step_value, bool)
            else None
        )
        return ObservationConversion(
            state=state,
            player_known=True,
            player_lane_known=True,
            coins_available=coins_available,
            distance_horizon=self.distance_horizon,
            estimated_fields=tuple(dict.fromkeys(estimated)),
            unrepresented=tuple(unrepresented),
            warnings=tuple(dict.fromkeys(warnings)),
            observation_step=observation_step,
        )

    def describe(self) -> dict:
        return {
            "source": "endless-surfer observation schema v1",
            "distance_horizon": self.distance_horizon,
            "max_speed": self.max_speed,
            "obstacle_mapping": {
                "BARRIER": "low",
                "OVERHEAD": "high",
                "TRAIN": "train",
            },
            "selection": (
                "nearest visible object of each kind; remaining objects are "
                "reported as unrepresented"
            ),
            "player_state_mapping": {
                "JUMPING": "jumping",
                "ROLLING": "rolling",
                "COLLIDED": "neither jumping nor rolling; warning recorded",
            },
            "future_objects": (
                "the game observation only contains spawned, currently visible "
                "objects; no future obstacle position is available or inferred"
            ),
        }
