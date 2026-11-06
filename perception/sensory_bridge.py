"""Bridge visual observations to the existing Phase 3A feature contract.

The 14 feature names returned here are exactly ``GameState.features()``. No
encoder, population or neuron mapping is duplicated or changed: the bridge
only records which visual observation supplied each feature group, so a
caller can inspect confidence, validity, visibility and geometry next to the
values the encoders receive.

Feature values are never repaired or invented. An unobserved object leaves the
corresponding ``*_present`` feature at 0 and its lane/distance features at
``None``, which is the existing encoder contract for an absent object.
"""

from __future__ import annotations

from dataclasses import dataclass

from perception.config import DistanceConfig
from perception.game_state_adapter import GameStateAdapter, GameStateConversion
from perception.observations import (
    FrameObservations,
    ObservationBuilder,
    VisualObservation,
)
from perception.scene import PerceivedScene
from sensory.game_state import GameState

FEATURE_NAMES = (
    "player_lane",
    "player_speed",
    "jumping",
    "rolling",
    "obstacle_present",
    "obstacle_lane",
    "obstacle_distance",
    "obstacle_type",
    "train_present",
    "train_lane",
    "train_distance",
    "coin_present",
    "coin_lane",
    "coin_distance",
)

FEATURE_GROUPS = {
    "player": ("player_lane", "player_speed", "jumping", "rolling"),
    "obstacle": (
        "obstacle_present",
        "obstacle_lane",
        "obstacle_distance",
        "obstacle_type",
    ),
    "train": ("train_present", "train_lane", "train_distance"),
    "coin": ("coin_present", "coin_lane", "coin_distance"),
}


@dataclass(frozen=True)
class FeatureGroupLink:
    """Which observation, if any, supplied one GameState feature group."""

    group: str
    feature_names: tuple[str, ...]
    present: bool
    object_index: int | None = None
    class_name: str | None = None
    confidence: float | None = None
    valid: bool | None = None
    visibility: str | None = None
    lane: int | None = None
    distance_proxy: float | None = None
    n_candidates: int = 0
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.group not in FEATURE_GROUPS:
            raise ValueError(f"unknown feature group {self.group!r}")
        if self.feature_names != FEATURE_GROUPS[self.group]:
            raise ValueError(f"feature names do not match group {self.group!r}")
        if self.present and self.object_index is None and self.reason is None:
            raise ValueError("a present group must name an object or explain why not")

    def as_dict(self) -> dict:
        return {
            "group": self.group,
            "feature_names": list(self.feature_names),
            "present": self.present,
            "object_index": self.object_index,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "valid": self.valid,
            "visibility": self.visibility,
            "lane": self.lane,
            "distance_proxy": self.distance_proxy,
            "n_candidates": self.n_candidates,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SpatialFeatureBundle:
    """The GameState feature vector plus its visual provenance."""

    state: GameState
    features: dict
    conversion: GameStateConversion
    observations: FrameObservations
    groups: tuple[FeatureGroupLink, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.state, GameState):
            raise ValueError("state must be a GameState")
        expected = dict(self.state.features())
        if set(self.features) != set(expected):
            raise ValueError("features do not match the GameState feature contract")
        if any(
            self.features[name] != expected[name] for name in FEATURE_NAMES
        ):
            raise ValueError("features differ from GameState.features()")
        if not isinstance(self.conversion, GameStateConversion):
            raise ValueError("conversion must be a GameStateConversion")
        if not isinstance(self.observations, FrameObservations):
            raise ValueError("observations must be FrameObservations")
        if tuple(item.group for item in self.groups) != tuple(FEATURE_GROUPS):
            raise ValueError("groups must cover player, obstacle, train and coin")

    @property
    def ordered_features(self) -> tuple:
        return tuple(self.features[name] for name in FEATURE_NAMES)

    def as_dict(self) -> dict:
        return {
            "features": {name: self.features[name] for name in FEATURE_NAMES},
            "groups": [item.as_dict() for item in self.groups],
            "observations": self.observations.as_dict(),
            "game_state": self.conversion.as_dict(),
            "notes": list(self.notes),
        }


def _match_primary(
    candidates: tuple[VisualObservation, ...],
    *,
    lane: int,
    distance: float,
) -> VisualObservation | None:
    """Find the observation the GameState adapter selected.

    The adapter selects the nearest object and breaks ties by class id and raw
    index. Matching on lane and the rounded distance proxy recovers that same
    record without duplicating the selection rule.
    """
    matches = [
        item
        for item in candidates
        if item.lane == lane
        and item.distance_proxy is not None
        and abs(item.distance_proxy - distance) <= 1e-6
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda item: (
            item.distance_proxy,
            item.class_id,
            item.raw_index if item.raw_index is not None else -1,
        )
    )
    return matches[0]


def _link(
    group: str,
    present: bool,
    candidates: tuple[VisualObservation, ...],
    primary: VisualObservation | None,
    reason: str | None = None,
) -> FeatureGroupLink:
    return FeatureGroupLink(
        group=group,
        feature_names=FEATURE_GROUPS[group],
        present=present,
        object_index=primary.object_index if primary is not None else None,
        class_name=primary.class_name if primary is not None else None,
        confidence=primary.confidence if primary is not None else None,
        valid=primary.valid if primary is not None else None,
        visibility=(
            primary.visibility.value if primary is not None else None
        ),
        lane=primary.lane if primary is not None else None,
        distance_proxy=(
            primary.distance_proxy if primary is not None else None
        ),
        n_candidates=len(candidates),
        reason=reason,
    )


class SpatialFeatureBridge:
    """Build ``GameState`` features from a scene and keep visual provenance."""

    def __init__(self, config: DistanceConfig) -> None:
        if not isinstance(config, DistanceConfig):
            raise ValueError("config must be a DistanceConfig")
        self.config = config
        self.adapter = GameStateAdapter(config)
        self.observation_builder = ObservationBuilder(config)

    def from_scene(
        self, scene: PerceivedScene, time_ms: float | None = None
    ) -> SpatialFeatureBundle:
        if not isinstance(scene, PerceivedScene):
            raise ValueError("scene must be a PerceivedScene")
        return self.from_conversion(
            scene, self.adapter.convert(scene, time_ms=time_ms)
        )

    def from_conversion(
        self, scene: PerceivedScene, conversion: GameStateConversion
    ) -> SpatialFeatureBundle:
        if not isinstance(scene, PerceivedScene):
            raise ValueError("scene must be a PerceivedScene")
        if not isinstance(conversion, GameStateConversion):
            raise ValueError("conversion must be a GameStateConversion")
        observations = self.observation_builder.from_scene(scene)
        state = conversion.state

        notes: list[str] = [
            "Feature values are exactly GameState.features(); the bridge does "
            "not alter encoders or neuron mappings."
        ]

        players = observations.player_objects
        if conversion.player_known:
            player_primary = players[0]
            player_reason = None
        else:
            player_primary = None
            if not scene.modality.player_available:
                player_reason = (
                    "the configured detector schema declares no player class"
                )
            elif len(players) > 1:
                player_reason = (
                    "multiple player detections; no single identity was selected"
                )
            else:
                player_reason = "no player detection in this frame"
        player_link = _link(
            "player",
            conversion.player_known,
            players,
            player_primary,
            player_reason,
        )

        obstacle_candidates = observations.obstacles
        obstacle_state = state.obstacle
        if obstacle_state is not None and obstacle_state.present:
            obstacle_primary = _match_primary(
                obstacle_candidates,
                lane=int(obstacle_state.lane),
                distance=float(obstacle_state.distance),
            )
            if obstacle_primary is None:
                notes.append(
                    "The GameState contains an obstacle that could not be "
                    "matched to an observation; provenance is incomplete."
                )
            obstacle_link = _link(
                "obstacle",
                True,
                obstacle_candidates,
                obstacle_primary,
                None if obstacle_primary is not None else "unmatched GameState obstacle",
            )
        else:
            obstacle_link = _link(
                "obstacle",
                False,
                obstacle_candidates,
                None,
                (
                    "candidate obstacle observations exist but none could be "
                    "represented by the GameState"
                    if obstacle_candidates
                    else "no obstacle detection in this frame"
                ),
            )

        train_candidates = observations.trains
        train_state = state.train
        if train_state is not None and train_state.present:
            train_primary = _match_primary(
                train_candidates,
                lane=int(train_state.lane),
                distance=float(train_state.distance),
            )
            if train_primary is None:
                notes.append(
                    "The GameState contains a train that could not be matched "
                    "to an observation; provenance is incomplete."
                )
            train_link = _link(
                "train",
                True,
                train_candidates,
                train_primary,
                None if train_primary is not None else "unmatched GameState train",
            )
        else:
            train_link = _link(
                "train",
                False,
                train_candidates,
                None,
                (
                    "candidate train observations exist but none could be "
                    "represented by the GameState"
                    if train_candidates
                    else "no train detection in this frame"
                ),
            )

        coin_candidates = observations.coins
        coin_state = state.coin
        if coin_state is not None and coin_state.present:
            coin_primary = _match_primary(
                coin_candidates,
                lane=int(coin_state.lane),
                distance=float(coin_state.distance),
            )
            if coin_primary is None:
                notes.append(
                    "The GameState contains a coin that could not be matched "
                    "to an observation; provenance is incomplete."
                )
            coin_link = _link(
                "coin",
                True,
                coin_candidates,
                coin_primary,
                None if coin_primary is not None else "unmatched GameState coin",
            )
        else:
            if not scene.modality.coins_available:
                coin_reason = (
                    "coins are unavailable in the configured detector schema"
                )
            elif coin_candidates:
                coin_reason = (
                    "candidate coin observations exist but none could be "
                    "represented by the GameState"
                )
            else:
                coin_reason = "no coin detection in this frame"
            coin_link = _link(
                "coin", False, coin_candidates, None, coin_reason
            )

        notes.extend(conversion.warnings)
        return SpatialFeatureBundle(
            state=state,
            features=dict(state.features()),
            conversion=conversion,
            observations=observations,
            groups=(
                player_link,
                obstacle_link,
                train_link,
                coin_link,
            ),
            notes=tuple(dict.fromkeys(notes)),
        )
