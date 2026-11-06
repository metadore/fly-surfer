"""Structured scene representation between detection and GameState.

The scene keeps every validated detection, its lane decision and the modality
availability explicit. Missing player or coin detections are recorded as
unavailable/not-detected; they are never replaced by assumed objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from perception.config import ClassRole, ClassSchema
from perception.detection import Detection, RejectedDetection, ValidationResult
from perception.image import ImageFrame
from perception.lanes import LaneAssigner, LaneAssignment


@dataclass(frozen=True)
class SceneObject:
    """One validated detection together with its lane decision."""

    detection: Detection
    lane_assignment: LaneAssignment

    @property
    def lane(self) -> int | None:
        return self.lane_assignment.lane

    def as_dict(self) -> dict:
        return {
            "detection": self.detection.as_dict(),
            "lane": self.lane_assignment.as_dict(),
        }


@dataclass(frozen=True)
class LaneOccupancy:
    """Counts of assigned objects in one lane."""

    lane: int
    obstacle_count: int = 0
    train_count: int = 0
    coin_count: int = 0
    other_count: int = 0

    @property
    def occupied(self) -> bool:
        return (
            self.obstacle_count + self.train_count + self.coin_count + self.other_count
        ) > 0

    def as_dict(self) -> dict:
        return {
            "lane": self.lane,
            "obstacle_count": self.obstacle_count,
            "train_count": self.train_count,
            "coin_count": self.coin_count,
            "other_count": self.other_count,
            "occupied": self.occupied,
        }


@dataclass(frozen=True)
class ModalityAvailability:
    """Whether player and coin information exists in this frame/schema."""

    player_available: bool
    player_status: str
    coins_available: bool
    coin_status: str
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "player_available": self.player_available,
            "player_status": self.player_status,
            "coins_available": self.coins_available,
            "coin_status": self.coin_status,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class SceneUncertainty:
    """Explicit uncertainty counts and notes for one frame."""

    rejected_detections: int
    unassigned_objects: int
    ambiguous_objects: int
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "rejected_detections": self.rejected_detections,
            "unassigned_objects": self.unassigned_objects,
            "ambiguous_objects": self.ambiguous_objects,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PerceivedScene:
    """Detections, lanes and availability for a single frame."""

    frame_id: str | None
    timestamp_ms: float | None
    source_path: str | None
    original_size: tuple[int, int]
    viewport_size: tuple[int, int]
    objects: tuple[SceneObject, ...]
    lane_occupancy: tuple[LaneOccupancy, ...]
    modality: ModalityAvailability
    uncertainty: SceneUncertainty
    rejected: tuple[RejectedDetection, ...] = ()

    def objects_with_role(self, *roles: ClassRole) -> tuple[SceneObject, ...]:
        wanted = set(roles)
        return tuple(obj for obj in self.objects if obj.detection.role in wanted)

    @property
    def obstacles(self) -> tuple[SceneObject, ...]:
        return self.objects_with_role(ClassRole.OBSTACLE)

    @property
    def trains(self) -> tuple[SceneObject, ...]:
        return self.objects_with_role(ClassRole.TRAIN)

    @property
    def coins(self) -> tuple[SceneObject, ...]:
        return self.objects_with_role(ClassRole.COIN)

    @property
    def other_objects(self) -> tuple[SceneObject, ...]:
        return self.objects_with_role(
            ClassRole.TERRAIN,
            ClassRole.BOUNDARY,
            ClassRole.POWERUP,
            ClassRole.OTHER,
        )

    @property
    def player_objects(self) -> tuple[SceneObject, ...]:
        return self.objects_with_role(ClassRole.PLAYER)

    @property
    def player(self) -> SceneObject | None:
        """The player only when exactly one player detection exists."""
        players = self.player_objects
        return players[0] if len(players) == 1 else None

    def as_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "source_path": self.source_path,
            "original_size": list(self.original_size),
            "viewport_size": list(self.viewport_size),
            "objects": [obj.as_dict() for obj in self.objects],
            "lane_occupancy": [lane.as_dict() for lane in self.lane_occupancy],
            "modality": self.modality.as_dict(),
            "uncertainty": self.uncertainty.as_dict(),
            "rejected": [item.as_dict() for item in self.rejected],
        }


class SceneBuilder:
    """Assign lanes and assemble a ``PerceivedScene`` from validated output."""

    def __init__(
        self,
        assigner: LaneAssigner,
        schema: ClassSchema,
    ) -> None:
        if not isinstance(assigner, LaneAssigner):
            raise ValueError("assigner must be a LaneAssigner")
        if not isinstance(schema, ClassSchema):
            raise ValueError("schema must be a ClassSchema")
        self.assigner = assigner
        self.schema = schema
        self.n_lanes = assigner.config.n_lanes

    def build(
        self, frame: ImageFrame, validation: ValidationResult
    ) -> PerceivedScene:
        if not isinstance(frame, ImageFrame):
            raise ValueError("frame must be an ImageFrame")
        if not isinstance(validation, ValidationResult):
            raise ValueError("validation must be a ValidationResult")

        objects = tuple(
            SceneObject(
                detection=detection,
                lane_assignment=self.assigner.assign(detection.normalized_box),
            )
            for detection in validation.accepted
        )

        counts = [
            {
                "obstacle": 0,
                "train": 0,
                "coin": 0,
                "other": 0,
            }
            for _ in range(self.n_lanes)
        ]
        for obj in objects:
            if obj.lane is None:
                continue
            bucket = counts[obj.lane]
            role = obj.detection.role
            if role is ClassRole.OBSTACLE:
                bucket["obstacle"] += 1
            elif role is ClassRole.TRAIN:
                bucket["train"] += 1
            elif role is ClassRole.COIN:
                bucket["coin"] += 1
            else:
                bucket["other"] += 1

        lane_occupancy = tuple(
            LaneOccupancy(
                lane=lane,
                obstacle_count=bucket["obstacle"],
                train_count=bucket["train"],
                coin_count=bucket["coin"],
                other_count=bucket["other"],
            )
            for lane, bucket in enumerate(counts)
        )

        player_objects = [
            obj for obj in objects if obj.detection.role is ClassRole.PLAYER
        ]
        notes: list[str] = []
        if not self.schema.supports_player:
            player_available = False
            player_status = "unavailable_in_schema"
            notes.append(
                "The configured detector schema declares no player class; "
                "player state is not observed."
            )
        elif not player_objects:
            player_available = False
            player_status = "not_detected"
        elif len(player_objects) > 1:
            player_available = True
            player_status = "multiple_detections"
            notes.append(
                f"{len(player_objects)} player detections; no single player "
                "identity was selected."
            )
        elif player_objects[0].lane is None:
            player_available = True
            player_status = "lane_unknown"
        else:
            player_available = True
            player_status = "available"

        coin_objects = [obj for obj in objects if obj.detection.role is ClassRole.COIN]
        if not self.schema.supports_coins:
            coins_available = False
            coin_status = "unavailable_in_schema"
            notes.append(
                "The configured detector schema declares no coin class; "
                "coin presence is not observed."
            )
        elif not coin_objects:
            coins_available = False
            coin_status = "not_detected"
        elif any(obj.lane is None for obj in coin_objects):
            coins_available = True
            coin_status = "lane_unknown"
        else:
            coins_available = True
            coin_status = "available"

        unassigned = sum(1 for obj in objects if obj.lane is None)
        ambiguous = sum(
            1 for obj in objects if obj.lane_assignment.ambiguous
        )
        uncertainty_notes = []
        if unassigned:
            uncertainty_notes.append(
                f"{unassigned} object(s) were not assigned to any lane."
            )
        if ambiguous:
            uncertainty_notes.append(
                f"{ambiguous} object(s) touched more than one lane."
            )
        if validation.rejected:
            uncertainty_notes.append(
                f"{len(validation.rejected)} detection(s) were rejected and "
                "are excluded from the scene."
            )
        uncertainty_notes.append(
            "Lane assignment uses horizontal overlap only; perspective, "
            "occlusion and 3D track geometry are not modelled."
        )

        return PerceivedScene(
            frame_id=frame.frame_id,
            timestamp_ms=frame.timestamp_ms,
            source_path=str(frame.source_path) if frame.source_path else None,
            original_size=frame.original_size,
            viewport_size=frame.viewport_size,
            objects=objects,
            lane_occupancy=lane_occupancy,
            modality=ModalityAvailability(
                player_available=player_available,
                player_status=player_status,
                coins_available=coins_available,
                coin_status=coin_status,
                notes=tuple(notes),
            ),
            uncertainty=SceneUncertainty(
                rejected_detections=len(validation.rejected),
                unassigned_objects=unassigned,
                ambiguous_objects=ambiguous,
                notes=tuple(uncertainty_notes),
            ),
            rejected=validation.rejected,
        )
