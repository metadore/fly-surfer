"""Per-object visual observations for one frame.

``PerceivedScene`` already carries every validated detection, but its objects
are organised for the single-object ``GameState`` conversion. Phase 3B.4 and
Phase 3C need a stable, JSON-safe per-object record with explicit geometry,
confidence, validity, visibility and timestamp, including objects the
``GameState`` schema cannot represent.

Nothing here measures metric depth. ``distance_proxy`` is the same
uncalibrated bottom-edge image proxy used by ``GameState``, and
``relative_horizontal_position`` / ``relative_vertical_position`` are
viewport fractions, not world coordinates. Visibility is inferred from box
geometry only: occlusion cannot be observed by a single detector frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from perception.config import ClassRole, DistanceConfig, GameStateRole
from perception.detection import Detection, RejectedDetection
from perception.geometry import BoundingBox, NormalizedBox, bottom_edge_distance
from perception.scene import PerceivedScene, SceneObject

_EDGE_EPSILON = 1e-6


class Visibility(str, Enum):
    """What can be said about visibility from one detector frame."""

    IN_FRAME = "in_frame"
    TOUCHES_EDGE = "touches_edge"
    UNKNOWN = "unknown"


def _finite_unit(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return number


@dataclass(frozen=True)
class VisualObservation:
    """One validated detection described in frame-independent coordinates.

    ``object_index`` is only stable within its frame. Stable identities across
    frames are assigned later by the temporal tracker; this layer deliberately
    does not invent one.
    """

    object_index: int
    class_id: int
    class_name: str
    role: ClassRole
    game_state_role: GameStateRole
    lane: int | None
    bbox_screen: BoundingBox
    bbox_normalized: NormalizedBox
    confidence: float
    frame_id: str | None
    timestamp_ms: float | None
    distance_proxy: float | None = None
    visibility: Visibility = Visibility.UNKNOWN
    valid: bool = True
    invalid_reason: str | None = None
    clamped: bool = False
    raw_index: int | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.object_index, bool) or not isinstance(
            self.object_index, int
        ):
            raise ValueError("object_index must be an integer")
        if self.object_index < 0:
            raise ValueError("object_index must be non-negative")
        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise ValueError("class_id must be an integer")
        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")
        if not isinstance(self.class_name, str) or not self.class_name:
            raise ValueError("class_name must be a non-empty string")
        if not isinstance(self.role, ClassRole):
            raise ValueError("role must be a ClassRole")
        if not isinstance(self.game_state_role, GameStateRole):
            raise ValueError("game_state_role must be a GameStateRole")
        if self.lane is not None:
            if isinstance(self.lane, bool) or not isinstance(self.lane, int):
                raise ValueError("lane must be an integer or None")
            if self.lane < 0:
                raise ValueError("lane must be non-negative")
        if not isinstance(self.bbox_screen, BoundingBox):
            raise ValueError("bbox_screen must be a BoundingBox")
        if not isinstance(self.bbox_normalized, NormalizedBox):
            raise ValueError("bbox_normalized must be a NormalizedBox")
        object.__setattr__(
            self, "confidence", _finite_unit(self.confidence, "confidence")
        )
        if self.timestamp_ms is not None:
            if isinstance(self.timestamp_ms, bool) or not isinstance(
                self.timestamp_ms, (int, float)
            ):
                raise ValueError("timestamp_ms must be a number or None")
            timestamp = float(self.timestamp_ms)
            if not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError("timestamp_ms must be finite and non-negative")
            object.__setattr__(self, "timestamp_ms", timestamp)
        if self.distance_proxy is not None:
            object.__setattr__(
                self,
                "distance_proxy",
                _finite_unit(self.distance_proxy, "distance_proxy"),
            )
        if not isinstance(self.visibility, Visibility):
            raise ValueError("visibility must be a Visibility")
        if not isinstance(self.valid, bool):
            raise ValueError("valid must be a bool")
        if self.valid and self.invalid_reason is not None:
            raise ValueError("a valid observation must not have invalid_reason")
        if not self.valid and (
            not isinstance(self.invalid_reason, str) or not self.invalid_reason
        ):
            raise ValueError("an invalid observation requires invalid_reason")
        if not isinstance(self.clamped, bool):
            raise ValueError("clamped must be a bool")
        if self.raw_index is not None and (
            isinstance(self.raw_index, bool) or not isinstance(self.raw_index, int)
        ):
            raise ValueError("raw_index must be an integer or None")
        if self.source is not None and not isinstance(self.source, str):
            raise ValueError("source must be a string or None")

    @property
    def center_normalized(self) -> tuple[float, float]:
        return self.bbox_normalized.center

    @property
    def center_screen(self) -> tuple[float, float]:
        return self.bbox_screen.center

    @property
    def relative_horizontal_position(self) -> float:
        """Box-centre offset from the viewport centre in [-1, 1].

        ``-1`` is the left viewport edge, ``0`` the centre and ``1`` the right
        edge. This is a normalised image coordinate, not a world position.
        """
        return 2.0 * self.center_normalized[0] - 1.0

    @property
    def relative_vertical_position(self) -> float:
        """Box-centre offset from the viewport centre in [-1, 1].

        Image ``y`` grows downwards, so negative values are above the centre.
        This is a normalised image coordinate, not an elevation.
        """
        return 2.0 * self.center_normalized[1] - 1.0

    @property
    def normalized_proximity(self) -> float | None:
        """Inverse distance proxy: 0 far, 1 near; ``None`` without a proxy.

        This is not a metric distance and must not be reported as metres.
        """
        if self.distance_proxy is None:
            return None
        return 1.0 - self.distance_proxy

    @property
    def box_area_fraction(self) -> float:
        return self.bbox_normalized.area

    def as_dict(self) -> dict:
        return {
            "object_index": self.object_index,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "role": self.role.value,
            "game_state_role": self.game_state_role.value,
            "lane": self.lane,
            "bbox_screen": {
                "x1": self.bbox_screen.x1,
                "y1": self.bbox_screen.y1,
                "x2": self.bbox_screen.x2,
                "y2": self.bbox_screen.y2,
            },
            "bbox_normalized": list(self.bbox_normalized.as_tuple()),
            "center": {
                "x": self.center_normalized[0],
                "y": self.center_normalized[1],
            },
            "relative_horizontal_position": self.relative_horizontal_position,
            "relative_vertical_position": self.relative_vertical_position,
            "distance_proxy": self.distance_proxy,
            "normalized_proximity": self.normalized_proximity,
            "box_area_fraction": self.box_area_fraction,
            "confidence": self.confidence,
            "valid": self.valid,
            "invalid_reason": self.invalid_reason,
            "visibility": self.visibility.value,
            "clamped": self.clamped,
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "raw_index": self.raw_index,
            "source": self.source,
        }


@dataclass(frozen=True)
class FrameObservations:
    """All objects of one frame plus the detections that were rejected."""

    frame_id: str | None
    timestamp_ms: float | None
    source_path: str | None
    original_size: tuple[int, int]
    viewport_size: tuple[int, int]
    observations: tuple[VisualObservation, ...]
    rejected: tuple[RejectedDetection, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.frame_id is not None and not isinstance(self.frame_id, str):
            raise ValueError("frame_id must be a string or None")
        if self.timestamp_ms is not None:
            if isinstance(self.timestamp_ms, bool) or not isinstance(
                self.timestamp_ms, (int, float)
            ):
                raise ValueError("timestamp_ms must be a number or None")
            timestamp = float(self.timestamp_ms)
            if not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError("timestamp_ms must be finite and non-negative")
            object.__setattr__(self, "timestamp_ms", timestamp)
        for name, size in (
            ("original_size", self.original_size),
            ("viewport_size", self.viewport_size),
        ):
            if (
                not isinstance(size, tuple)
                or len(size) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 1
                    for value in size
                )
            ):
                raise ValueError(f"{name} must be a (width, height) pair")
        if not isinstance(self.observations, tuple) or any(
            not isinstance(item, VisualObservation) for item in self.observations
        ):
            raise ValueError("observations must be a tuple of VisualObservation")
        if not isinstance(self.rejected, tuple) or any(
            not isinstance(item, RejectedDetection) for item in self.rejected
        ):
            raise ValueError("rejected must be a tuple of RejectedDetection")
        if not isinstance(self.notes, tuple) or any(
            not isinstance(item, str) for item in self.notes
        ):
            raise ValueError("notes must be a tuple of strings")

    @property
    def n_observations(self) -> int:
        return len(self.observations)

    @property
    def valid_observations(self) -> tuple[VisualObservation, ...]:
        return tuple(item for item in self.observations if item.valid)

    @property
    def invalid_observations(self) -> tuple[VisualObservation, ...]:
        return tuple(item for item in self.observations if not item.valid)

    def with_role(self, *roles: ClassRole) -> tuple[VisualObservation, ...]:
        wanted = set(roles)
        return tuple(item for item in self.observations if item.role in wanted)

    @property
    def obstacles(self) -> tuple[VisualObservation, ...]:
        return self.with_role(ClassRole.OBSTACLE)

    @property
    def trains(self) -> tuple[VisualObservation, ...]:
        return self.with_role(ClassRole.TRAIN)

    @property
    def coins(self) -> tuple[VisualObservation, ...]:
        return self.with_role(ClassRole.COIN)

    @property
    def player_objects(self) -> tuple[VisualObservation, ...]:
        return self.with_role(ClassRole.PLAYER)

    @property
    def other_objects(self) -> tuple[VisualObservation, ...]:
        return self.with_role(
            ClassRole.TERRAIN,
            ClassRole.BOUNDARY,
            ClassRole.POWERUP,
            ClassRole.OTHER,
        )

    def as_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "source_path": self.source_path,
            "original_size": list(self.original_size),
            "viewport_size": list(self.viewport_size),
            "n_observations": self.n_observations,
            "n_rejected": len(self.rejected),
            "observations": [item.as_dict() for item in self.observations],
            "rejected": [item.as_dict() for item in self.rejected],
            "notes": list(self.notes),
        }


def classify_visibility(box: NormalizedBox) -> Visibility:
    """Classify visibility from geometry alone.

    A box touching the viewport boundary may be clipped or may simply end at
    the edge; the two cannot be distinguished from one frame, so the result is
    ``TOUCHES_EDGE`` rather than a claim of occlusion.
    """
    if (
        box.x1 <= _EDGE_EPSILON
        or box.y1 <= _EDGE_EPSILON
        or box.x2 >= 1.0 - _EDGE_EPSILON
        or box.y2 >= 1.0 - _EDGE_EPSILON
    ):
        return Visibility.TOUCHES_EDGE
    return Visibility.IN_FRAME


class ObservationBuilder:
    """Turn a ``PerceivedScene`` into explicit per-object observations."""

    def __init__(self, config: DistanceConfig) -> None:
        if not isinstance(config, DistanceConfig):
            raise ValueError("config must be a DistanceConfig")
        self.config = config

    def _distance(self, detection: Detection) -> float | None:
        if not self.config.is_proxy:
            return None
        return round(
            bottom_edge_distance(
                detection.normalized_box, self.config.horizon_fraction
            ),
            6,
        )

    def _observation(
        self, index: int, obj: SceneObject, scene: PerceivedScene
    ) -> VisualObservation:
        detection = obj.detection
        return VisualObservation(
            object_index=index,
            class_id=detection.class_id,
            class_name=detection.class_name,
            role=detection.role,
            game_state_role=detection.game_state_role,
            lane=obj.lane,
            bbox_screen=detection.screen_box,
            bbox_normalized=detection.normalized_box,
            confidence=detection.confidence,
            frame_id=scene.frame_id,
            timestamp_ms=scene.timestamp_ms,
            distance_proxy=self._distance(detection),
            visibility=classify_visibility(detection.normalized_box),
            valid=True,
            clamped=detection.clamped,
            raw_index=detection.raw_index,
            source=detection.source,
        )

    def from_scene(self, scene: PerceivedScene) -> FrameObservations:
        if not isinstance(scene, PerceivedScene):
            raise ValueError("scene must be a PerceivedScene")
        observations = tuple(
            self._observation(index, obj, scene)
            for index, obj in enumerate(scene.objects)
        )
        notes: list[str] = []
        if self.config.is_proxy:
            notes.append(
                "distance_proxy is an uncalibrated bottom-edge image proxy "
                f"(horizon fraction {self.config.horizon_fraction:.4f}); it is "
                "not a metric distance."
            )
        else:
            notes.append(
                "distance mode is 'none'; distance_proxy and "
                "normalized_proximity are unavailable for this frame."
            )
        touching = sum(
            1
            for item in observations
            if item.visibility is Visibility.TOUCHES_EDGE
        )
        if touching:
            notes.append(
                f"{touching} object(s) touch the viewport boundary; clipping "
                "cannot be distinguished from a box that ends at the edge."
            )
        notes.append(
            "Visibility is inferred from box geometry only; occlusion is not "
            "observable from a single frame."
        )
        return FrameObservations(
            frame_id=scene.frame_id,
            timestamp_ms=scene.timestamp_ms,
            source_path=scene.source_path,
            original_size=scene.original_size,
            viewport_size=scene.viewport_size,
            observations=observations,
            rejected=scene.rejected,
            notes=tuple(notes),
        )
