"""Convert a perceived scene into the existing Phase 3A ``GameState``.

The schema is not modified. Fields that perception cannot observe are filled
with schema defaults and listed in ``estimated_fields`` and ``warnings``.
Objects the single-object schema cannot represent, objects with uncertain
lanes and all but the nearest object of a kind are retained in
``unrepresented`` instead of being dropped silently.

Distance comes only from ``DistanceConfig`` and is an uncalibrated
bottom-edge proxy, not a metric or game measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from perception.config import DistanceConfig, GameStateRole
from perception.geometry import bottom_edge_distance
from perception.scene import PerceivedScene, SceneObject
from sensory.game_state import (
    LANE_NAMES,
    OBSTACLE_TYPE_NAMES,
    CoinState,
    GameState,
    Lane,
    ObstacleState,
    ObstacleType,
    PlayerState,
    TrainState,
)


@dataclass(frozen=True)
class UnrepresentedObject:
    """A scene object the ``GameState`` schema cannot carry."""

    class_name: str
    role: str
    lane: int | None
    reason: str

    def as_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "role": self.role,
            "lane": self.lane,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GameStateConversion:
    """A ``GameState`` plus everything the conversion had to assume."""

    state: GameState
    player_known: bool
    player_lane_known: bool
    coins_available: bool
    estimated_fields: tuple[str, ...] = ()
    unrepresented: tuple[UnrepresentedObject, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "state": _state_as_dict(self.state),
            "player_known": self.player_known,
            "player_lane_known": self.player_lane_known,
            "coins_available": self.coins_available,
            "estimated_fields": list(self.estimated_fields),
            "unrepresented": [item.as_dict() for item in self.unrepresented],
            "warnings": list(self.warnings),
        }


def _lane_dict(value: Lane) -> dict:
    return {"value": int(value), "name": LANE_NAMES[int(value)]}


def _state_as_dict(state: GameState) -> dict:
    obstacle = state.obstacle
    train = state.train
    coin = state.coin
    return {
        "time_ms": state.time_ms,
        "player": {
            "lane": _lane_dict(state.player.lane),
            "speed": state.player.speed,
            "jumping": state.player.jumping,
            "rolling": state.player.rolling,
        },
        "obstacle": (
            {
                "present": obstacle.present,
                "lane": _lane_dict(obstacle.lane),
                "distance": obstacle.distance,
                "obstacle_type": {
                    "value": int(obstacle.obstacle_type),
                    "name": OBSTACLE_TYPE_NAMES[int(obstacle.obstacle_type)],
                },
            }
            if obstacle is not None and obstacle.present
            else None
        ),
        "train": (
            {
                "present": train.present,
                "lane": _lane_dict(train.lane),
                "distance": train.distance,
            }
            if train is not None and train.present
            else None
        ),
        "coin": (
            {
                "present": coin.present,
                "lane": _lane_dict(coin.lane),
                "distance": coin.distance,
            }
            if coin is not None and coin.present
            else None
        ),
    }


class GameStateAdapter:
    """Build the validated Phase 3A state from one ``PerceivedScene``."""

    def __init__(self, config: DistanceConfig) -> None:
        if not isinstance(config, DistanceConfig):
            raise ValueError("config must be a DistanceConfig")
        self.config = config

    def _distance(self, obj: SceneObject) -> float | None:
        if not self.config.is_proxy:
            return None
        return round(
            bottom_edge_distance(
                obj.detection.normalized_box, self.config.horizon_fraction
            ),
            6,
        )

    def _select(
        self,
        objects: tuple[SceneObject, ...],
        label: str,
        unrepresented: list[UnrepresentedObject],
        estimated: list[str],
        *,
        allow_unsupported: bool = False,
    ) -> tuple[SceneObject | None, float | None]:
        candidates: list[tuple[float, SceneObject]] = []
        for obj in objects:
            reason = None
            if obj.lane is None:
                reason = "lane assignment is missing or uncertain"
            elif (
                obj.detection.game_state_role is GameStateRole.UNSUPPORTED
                and not allow_unsupported
            ):
                reason = (
                    f"class {obj.detection.class_name!r} has no GameState role"
                )
            else:
                distance = self._distance(obj)
                if distance is None:
                    reason = (
                        "distance mode is 'none'; the GameState requires a "
                        "distance for a present object"
                    )
                else:
                    candidates.append((distance, obj))
            if reason is not None:
                unrepresented.append(
                    UnrepresentedObject(
                        class_name=obj.detection.class_name,
                        role=obj.detection.role.value,
                        lane=obj.lane,
                        reason=reason,
                    )
                )
        if not candidates:
            return None, None
        candidates.sort(
            key=lambda item: (
                item[0],
                item[1].detection.class_id,
                item[1].detection.raw_index
                if item[1].detection.raw_index is not None
                else -1,
            )
        )
        distance, selected = candidates[0]
        estimated.append(f"{label}.distance")
        for _, other in candidates[1:]:
            unrepresented.append(
                UnrepresentedObject(
                    class_name=other.detection.class_name,
                    role=other.detection.role.value,
                    lane=other.lane,
                    reason=(
                        f"only the nearest {label} is representable by the "
                        "single-object GameState"
                    ),
                )
            )
        return selected, distance

    def convert(
        self, scene: PerceivedScene, time_ms: float | None = None
    ) -> GameStateConversion:
        if not isinstance(scene, PerceivedScene):
            raise ValueError("scene must be a PerceivedScene")
        if time_ms is None:
            time_ms = scene.timestamp_ms if scene.timestamp_ms is not None else 0.0

        warnings: list[str] = []
        estimated: list[str] = []
        unrepresented: list[UnrepresentedObject] = []

        players = scene.player_objects
        player_known = len(players) == 1
        player_lane_known = player_known and players[0].lane is not None
        if player_lane_known:
            player_lane = Lane(players[0].lane)
        else:
            player_lane = Lane.CENTER
            estimated.append("player.lane")
            if len(players) > 1:
                warnings.append(
                    f"{len(players)} player detections; no single identity was "
                    "available and the default centre lane was used."
                )
            elif player_known:
                warnings.append(
                    "The player was detected but its lane is uncertain; the "
                    "default centre lane was used."
                )
            else:
                warnings.append(
                    "No player detection is available; the schema defaults "
                    "(centre lane, speed 0.5, not jumping, not rolling) were used."
                )
        estimated.extend(("player.speed", "player.jumping", "player.rolling"))
        if player_known:
            warnings.append(
                "Player speed, jumping and rolling are not observed in a single "
                "frame; schema defaults were used."
            )
        player = PlayerState(lane=player_lane)

        obstacle_object, obstacle_distance = self._select(
            scene.obstacles, "obstacle", unrepresented, estimated
        )
        obstacle = None
        if obstacle_object is not None:
            role = obstacle_object.detection.game_state_role
            obstacle_type = (
                ObstacleType.HIGH
                if role is GameStateRole.OBSTACLE_HIGH
                else ObstacleType.LOW
            )
            obstacle = ObstacleState(
                present=True,
                lane=Lane(obstacle_object.lane),
                distance=obstacle_distance,
                obstacle_type=obstacle_type,
            )

        train_object, train_distance = self._select(
            scene.trains, "train", unrepresented, estimated
        )
        train = None
        if train_object is not None:
            train = TrainState(
                present=True,
                lane=Lane(train_object.lane),
                distance=train_distance,
            )

        coin = None
        if scene.modality.coins_available:
            coin_object, coin_distance = self._select(
                scene.coins,
                "coin",
                unrepresented,
                estimated,
                allow_unsupported=True,
            )
            if coin_object is not None:
                coin = CoinState(
                    present=True,
                    lane=Lane(coin_object.lane),
                    distance=coin_distance,
                )

        for obj in scene.other_objects:
            unrepresented.append(
                UnrepresentedObject(
                    class_name=obj.detection.class_name,
                    role=obj.detection.role.value,
                    lane=obj.lane,
                    reason=(
                        f"class role {obj.detection.role.value!r} has no "
                        "GameState representation"
                    ),
                )
            )

        if self.config.is_proxy:
            warnings.append(
                "Object distances use an uncalibrated bottom-edge image proxy "
                "with horizon fraction "
                f"{self.config.horizon_fraction:.4f}; they are not metric or "
                "game distances."
            )
        if unrepresented:
            warnings.append(
                f"{len(unrepresented)} scene object(s) are not represented by "
                "the GameState schema; see 'unrepresented'."
            )
        ambiguous_assigned = sum(
            1
            for obj in scene.objects
            if obj.lane is not None and obj.lane_assignment.ambiguous
        )
        if ambiguous_assigned:
            warnings.append(
                f"{ambiguous_assigned} object(s) touched more than one lane and "
                "were assigned by the configured majority rule."
            )
        warnings.extend(scene.modality.notes)

        state = GameState(
            player=player,
            obstacle=obstacle,
            train=train,
            coin=coin,
            time_ms=time_ms,
        )
        return GameStateConversion(
            state=state,
            player_known=player_known,
            player_lane_known=player_lane_known,
            coins_available=scene.modality.coins_available,
            estimated_fields=tuple(dict.fromkeys(estimated)),
            unrepresented=tuple(unrepresented),
            warnings=tuple(dict.fromkeys(warnings)),
        )
