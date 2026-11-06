"""Deterministic lightweight tracking of visual observations.

Tracks are associated frame to frame by class-compatible IoU, with a
centre-distance gate as a fallback. Each track has a stable integer id, a
bounded observation history and an explicit state:

``TENTATIVE``
    Seen fewer than ``min_hits`` times. A tentative track can absorb a
    one-frame false positive without becoming an event source.
``CONFIRMED``
    Seen at least ``min_hits`` times.
``OCCLUDED``
    Missed at least one frame but not more than ``max_age`` frames. The last
    observation is retained; no new geometry is invented.
``LOST``
    Missed more than ``max_age`` frames. Reported once and then retired.

Association is greedy, confidence ordered and tie-broken by track id and
object index, so identical input sequences produce identical outputs.
Detector noise can still create short-lived tracks; these remain
``TENTATIVE`` and are excluded from event emitters unless a caller chooses
otherwise.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from perception.geometry import NormalizedBox
from perception.observations import FrameObservations, VisualObservation


class TrackState(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    OCCLUDED = "occluded"
    LOST = "lost"


@dataclass(frozen=True)
class TrackingConfig:
    """Association and lifetime parameters."""

    iou_threshold: float = 0.3
    gate_distance: float = 0.35
    duplicate_iou: float = 0.75
    max_age: int = 3
    min_hits: int = 2
    history_limit: int = 32
    class_aware: bool = True
    max_tracks: int = 128
    retired_limit: int = 64

    def __post_init__(self) -> None:
        for name in ("iou_threshold", "gate_distance", "duplicate_iou"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            number = float(value)
            if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if self.gate_distance == 0.0:
            raise ValueError("gate_distance must be greater than zero")
        for name in (
            "max_age",
            "min_hits",
            "history_limit",
            "max_tracks",
            "retired_limit",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.class_aware, bool):
            raise ValueError("class_aware must be a bool")


def box_iou(first: NormalizedBox, second: NormalizedBox) -> float:
    left = max(first.x1, second.x1)
    top = max(first.y1, second.y1)
    right = min(first.x2, second.x2)
    bottom = min(first.y2, second.y2)
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = first.area + second.area - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


def center_distance(first: NormalizedBox, second: NormalizedBox) -> float:
    first_x, first_y = first.center
    second_x, second_y = second.center
    return math.hypot(first_x - second_x, first_y - second_y)


@dataclass
class _Track:
    track_id: int
    class_id: int
    class_name: str
    role: object
    state: TrackState
    hits: int
    misses: int
    age: int
    first_frame_index: int
    last_frame_index: int
    first_timestamp_ms: float | None
    last_timestamp_ms: float | None
    observation: VisualObservation
    previous: VisualObservation | None
    history: deque[VisualObservation] = field(default_factory=deque)

    def record(self, *, is_new: bool) -> "TrackRecord":
        return TrackRecord(
            track_id=self.track_id,
            class_id=self.class_id,
            class_name=self.class_name,
            role=self.role,
            state=self.state,
            observation=self.observation,
            previous=self.previous,
            hits=self.hits,
            misses=self.misses,
            age=self.age,
            first_frame_index=self.first_frame_index,
            last_frame_index=self.last_frame_index,
            first_timestamp_ms=self.first_timestamp_ms,
            last_timestamp_ms=self.last_timestamp_ms,
            history_length=len(self.history),
            is_new=is_new,
            confirmed=self.state is TrackState.CONFIRMED,
        )


@dataclass(frozen=True)
class TrackRecord:
    """Immutable view of one track after a frame update."""

    track_id: int
    class_id: int
    class_name: str
    role: object
    state: TrackState
    observation: VisualObservation
    previous: VisualObservation | None
    hits: int
    misses: int
    age: int
    first_frame_index: int
    last_frame_index: int
    first_timestamp_ms: float | None
    last_timestamp_ms: float | None
    history_length: int
    is_new: bool
    confirmed: bool

    @property
    def lane(self) -> int | None:
        return self.observation.lane

    @property
    def confidence(self) -> float:
        return self.observation.confidence

    @property
    def bbox_normalized(self) -> NormalizedBox:
        return self.observation.bbox_normalized

    @property
    def distance_proxy(self) -> float | None:
        return self.observation.distance_proxy

    def as_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "role": getattr(self.role, "value", str(self.role)),
            "state": self.state.value,
            "observation": self.observation.as_dict(),
            "previous": (
                self.previous.as_dict() if self.previous is not None else None
            ),
            "hits": self.hits,
            "misses": self.misses,
            "age": self.age,
            "first_frame_index": self.first_frame_index,
            "last_frame_index": self.last_frame_index,
            "first_timestamp_ms": self.first_timestamp_ms,
            "last_timestamp_ms": self.last_timestamp_ms,
            "history_length": self.history_length,
            "is_new": self.is_new,
            "confirmed": self.confirmed,
        }


@dataclass(frozen=True)
class TrackMatch:
    track_id: int
    object_index: int
    iou: float
    center_distance: float

    def as_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "object_index": self.object_index,
            "iou": self.iou,
            "center_distance": self.center_distance,
        }


@dataclass(frozen=True)
class DuplicateRecord:
    object_index: int
    kept_index: int
    class_name: str
    iou: float

    def as_dict(self) -> dict:
        return {
            "object_index": self.object_index,
            "kept_index": self.kept_index,
            "class_name": self.class_name,
            "iou": self.iou,
        }


@dataclass(frozen=True)
class FrameTracks:
    """Tracking output for one frame."""

    frame_index: int
    frame_id: str | None
    timestamp_ms: float | None
    tracks: tuple[TrackRecord, ...]
    matches: tuple[TrackMatch, ...]
    created: tuple[TrackRecord, ...]
    updated: tuple[TrackRecord, ...]
    occluded: tuple[TrackRecord, ...]
    lost: tuple[TrackRecord, ...]
    duplicates: tuple[DuplicateRecord, ...]
    notes: tuple[str, ...] = ()

    def get(self, track_id: int) -> TrackRecord | None:
        for item in self.tracks:
            if item.track_id == track_id:
                return item
        return None

    @property
    def confirmed(self) -> tuple[TrackRecord, ...]:
        return tuple(
            item for item in self.tracks if item.state is TrackState.CONFIRMED
        )

    def as_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "tracks": [item.as_dict() for item in self.tracks],
            "matches": [item.as_dict() for item in self.matches],
            "created": [item.as_dict() for item in self.created],
            "updated": [item.as_dict() for item in self.updated],
            "occluded": [item.as_dict() for item in self.occluded],
            "lost": [item.as_dict() for item in self.lost],
            "duplicates": [item.as_dict() for item in self.duplicates],
            "notes": list(self.notes),
        }


class MultiObjectTracker:
    """Greedy IoU tracker with a centre-distance fallback."""

    def __init__(self, config: TrackingConfig | None = None) -> None:
        self.config = config or TrackingConfig()
        if not isinstance(self.config, TrackingConfig):
            raise ValueError("config must be a TrackingConfig")
        self._next_id = 1
        self._frame_index = -1
        self._tracks: dict[int, _Track] = {}
        self._retired: deque[dict] = deque(maxlen=self.config.retired_limit)

    @property
    def active_tracks(self) -> tuple[TrackRecord, ...]:
        return tuple(
            track.record(is_new=False)
            for track in sorted(self._tracks.values(), key=lambda item: item.track_id)
        )

    @property
    def retired_tracks(self) -> tuple[dict, ...]:
        return tuple(self._retired)

    def reset(self) -> None:
        self._next_id = 1
        self._frame_index = -1
        self._tracks.clear()
        self._retired.clear()

    def _duplicates(
        self, observations: tuple[VisualObservation, ...]
    ) -> tuple[list[VisualObservation], list[DuplicateRecord]]:
        kept: list[VisualObservation] = []
        duplicates: list[DuplicateRecord] = []
        ordered = sorted(
            observations,
            key=lambda item: (
                -item.confidence,
                item.class_id,
                item.object_index,
            ),
        )
        for item in ordered:
            duplicate = None
            for existing in kept:
                if existing.class_id != item.class_id:
                    continue
                value = box_iou(existing.bbox_normalized, item.bbox_normalized)
                if value >= self.config.duplicate_iou:
                    duplicate = (existing, value)
                    break
            if duplicate is None:
                kept.append(item)
            else:
                duplicates.append(
                    DuplicateRecord(
                        object_index=item.object_index,
                        kept_index=duplicate[0].object_index,
                        class_name=item.class_name,
                        iou=duplicate[1],
                    )
                )
        kept.sort(key=lambda item: item.object_index)
        duplicates.sort(key=lambda item: item.object_index)
        return kept, duplicates

    def _cost(
        self, track: _Track, observation: VisualObservation
    ) -> tuple[float, float, float] | None:
        if self.config.class_aware and track.class_id != observation.class_id:
            return None
        value = box_iou(track.observation.bbox_normalized, observation.bbox_normalized)
        if value >= self.config.iou_threshold:
            return (1.0 - value, 0.0, value)
        distance = center_distance(
            track.observation.bbox_normalized, observation.bbox_normalized
        )
        if distance <= self.config.gate_distance:
            return (1.0 + distance, distance, value)
        return None

    def _new_track(
        self,
        observation: VisualObservation,
        frame_index: int,
        timestamp_ms: float | None,
    ) -> _Track:
        state = (
            TrackState.CONFIRMED
            if self.config.min_hits <= 1
            else TrackState.TENTATIVE
        )
        track = _Track(
            track_id=self._next_id,
            class_id=observation.class_id,
            class_name=observation.class_name,
            role=observation.role,
            state=state,
            hits=1,
            misses=0,
            age=1,
            first_frame_index=frame_index,
            last_frame_index=frame_index,
            first_timestamp_ms=timestamp_ms,
            last_timestamp_ms=timestamp_ms,
            observation=observation,
            previous=None,
            history=deque([observation], maxlen=self.config.history_limit),
        )
        self._next_id += 1
        return track

    def update(self, frame: FrameObservations) -> FrameTracks:
        if not isinstance(frame, FrameObservations):
            raise ValueError("frame must be a FrameObservations")
        self._frame_index += 1
        frame_index = self._frame_index
        observations, duplicates = self._duplicates(frame.observations)
        notes: list[str] = []
        if duplicates:
            notes.append(
                f"{len(duplicates)} same-class detection(s) overlapped another "
                f"at IoU >= {self.config.duplicate_iou:.2f} and were suppressed."
            )

        candidates: list[tuple[float, int, int, float, float]] = []
        tracks = sorted(self._tracks.values(), key=lambda item: item.track_id)
        for track in tracks:
            for observation in observations:
                cost = self._cost(track, observation)
                if cost is None:
                    continue
                primary, secondary, overlap = cost
                candidates.append(
                    (
                        primary,
                        track.track_id,
                        observation.object_index,
                        secondary,
                        overlap,
                    )
                )
        candidates.sort(key=lambda item: item[:4])

        assigned_tracks: set[int] = set()
        assigned_objects: set[int] = set()
        matches: list[TrackMatch] = []
        updated: list[TrackRecord] = []
        for _primary, track_id, object_index, distance, overlap in candidates:
            if track_id in assigned_tracks or object_index in assigned_objects:
                continue
            observation = next(
                item for item in observations if item.object_index == object_index
            )
            track = self._tracks[track_id]
            if not self.config.class_aware and track.class_id != observation.class_id:
                track.class_id = observation.class_id
                track.class_name = observation.class_name
                track.role = observation.role
                notes.append(
                    f"track {track.track_id} switched class to "
                    f"{observation.class_name!r}; class-aware association is off."
                )
            track.previous = track.observation
            track.observation = observation
            track.hits += 1
            track.misses = 0
            track.age += 1
            track.last_frame_index = frame_index
            track.last_timestamp_ms = frame.timestamp_ms
            track.history.append(observation)
            if track.state is TrackState.TENTATIVE and (
                track.hits >= self.config.min_hits
            ):
                track.state = TrackState.CONFIRMED
            elif track.state is TrackState.OCCLUDED:
                track.state = (
                    TrackState.CONFIRMED
                    if track.hits >= self.config.min_hits
                    else TrackState.TENTATIVE
                )
            assigned_tracks.add(track_id)
            assigned_objects.add(object_index)
            matches.append(
                TrackMatch(
                    track_id=track_id,
                    object_index=object_index,
                    iou=overlap,
                    center_distance=distance,
                )
            )
            updated.append(track.record(is_new=False))

        created: list[TrackRecord] = []
        for observation in observations:
            if observation.object_index in assigned_objects:
                continue
            if len(self._tracks) >= self.config.max_tracks:
                notes.append(
                    "max_tracks reached; a new observation was not tracked."
                )
                continue
            track = self._new_track(observation, frame_index, frame.timestamp_ms)
            self._tracks[track.track_id] = track
            assigned_tracks.add(track.track_id)
            record = track.record(is_new=True)
            created.append(record)
            updated.append(record)

        occluded: list[TrackRecord] = []
        lost: list[TrackRecord] = []
        for track in sorted(self._tracks.values(), key=lambda item: item.track_id):
            if track.track_id in assigned_tracks:
                continue
            track.misses += 1
            track.age += 1
            if track.misses > self.config.max_age:
                track.state = TrackState.LOST
                record = track.record(is_new=False)
                lost.append(record)
                self._retired.append(record.as_dict())
                del self._tracks[track.track_id]
            else:
                track.state = TrackState.OCCLUDED
                occluded.append(track.record(is_new=False))

        if lost:
            notes.append(
                f"{len(lost)} track(s) exceeded max_age={self.config.max_age} "
                "and were retired."
            )
        if occluded:
            notes.append(
                f"{len(occluded)} track(s) were missed this frame and remain "
                "within max_age; their last observation is retained."
            )

        active = tuple(
            track.record(is_new=False)
            for track in sorted(self._tracks.values(), key=lambda item: item.track_id)
        )
        return FrameTracks(
            frame_index=frame_index,
            frame_id=frame.frame_id,
            timestamp_ms=frame.timestamp_ms,
            tracks=active,
            matches=tuple(matches),
            created=tuple(created),
            updated=tuple(updated),
            occluded=tuple(occluded),
            lost=tuple(lost),
            duplicates=tuple(duplicates),
            notes=tuple(notes),
        )

    def describe(self) -> dict:
        return {
            "tracker": "greedy_iou_with_center_gate",
            "config": {
                "iou_threshold": self.config.iou_threshold,
                "gate_distance": self.config.gate_distance,
                "duplicate_iou": self.config.duplicate_iou,
                "max_age": self.config.max_age,
                "min_hits": self.config.min_hits,
                "history_limit": self.config.history_limit,
                "class_aware": self.config.class_aware,
                "max_tracks": self.config.max_tracks,
                "retired_limit": self.config.retired_limit,
            },
            "frame_index": self._frame_index,
            "active_tracks": len(self._tracks),
            "retired_tracks": len(self._retired),
            "limitations": [
                "Association uses normalized image boxes; no depth or motion "
                "model is applied.",
                "Occluded tracks retain their last observation and do not "
                "invent a current position.",
                "Tentative tracks may be detector noise and are marked as such.",
            ],
        }
