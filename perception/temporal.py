"""Causal temporal features, lifecycle states and lifecycle events.

This module consumes the per-frame output of ``MultiObjectTracker`` and
produces, for each frame:

* per-track motion features (frame-to-frame displacement, velocity, change in
  the uncalibrated distance proxy, approach/recede classification),
* one lifecycle state per track, following explicit transition rules,
* lifecycle events with timestamps, thresholds, cooldown-based duplicate
  suppression and an optional pulse encoded through the existing 14 feature
  names,
* a ``GameState`` built from the nearest confirmed track of each kind so the
  existing encoders keep their contract.

No action is selected here and the connectome is not bypassed. Units are
normalized over the image viewport; "velocity" is viewport fractions per
frame, or per second when explicit timestamps are available. Nothing is a
metric distance, and occlusion is not observed directly, only inferred from
missed associations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from perception.config import ClassRole, GameStateRole
from perception.observations import VisualObservation
from perception.tracking import (
    FrameTracks,
    MultiObjectTracker,
    TrackMatch,
    TrackRecord,
    TrackState,
    TrackingConfig,
)
from sensory.game_state import (
    CoinState,
    GameState,
    Lane,
    ObstacleState,
    ObstacleType,
    PlayerState,
    TrainState,
)


class Lifecycle(str, Enum):
    APPEARED = "appeared"
    PERSISTING = "persisting"
    APPROACHING = "approaching"
    RECEDING = "receding"
    DISAPPEARED = "disappeared"
    OCCLUDED = "occluded"
    UNCERTAIN = "uncertain"


EVENT_PRIORITY = {
    Lifecycle.APPEARED: 0,
    Lifecycle.APPROACHING: 1,
    Lifecycle.RECEDING: 2,
    Lifecycle.UNCERTAIN: 3,
    Lifecycle.OCCLUDED: 4,
    Lifecycle.DISAPPEARED: 5,
    Lifecycle.PERSISTING: 6,
}

PULSE_EVENTS = frozenset(
    {Lifecycle.APPEARED, Lifecycle.APPROACHING, Lifecycle.RECEDING}
)


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class TemporalFeatureConfig:
    """Thresholds for motion classification and event emission."""

    distance_change_threshold: float = 0.02
    confidence_floor: float = 0.25
    event_cooldown_frames: int = 2
    frame_interval_ms: float = 1000.0 / 30.0
    gap_threshold_ms: float = 100.0
    velocity_epsilon: float = 1e-9

    def __post_init__(self) -> None:
        threshold = _finite(
            self.distance_change_threshold, "distance_change_threshold"
        )
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("distance_change_threshold must be in [0, 1]")
        floor = _finite(self.confidence_floor, "confidence_floor")
        if not 0.0 <= floor <= 1.0:
            raise ValueError("confidence_floor must be in [0, 1]")
        for name in ("frame_interval_ms", "gap_threshold_ms"):
            value = _finite(getattr(self, name), name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        epsilon = _finite(self.velocity_epsilon, "velocity_epsilon")
        if epsilon < 0:
            raise ValueError("velocity_epsilon must be non-negative")
        if (
            isinstance(self.event_cooldown_frames, bool)
            or not isinstance(self.event_cooldown_frames, int)
            or self.event_cooldown_frames < 0
        ):
            raise ValueError("event_cooldown_frames must be a non-negative integer")


@dataclass(frozen=True)
class TemporalConfig:
    """Tracking plus temporal-feature configuration for the processor."""

    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    features: TemporalFeatureConfig = field(default_factory=TemporalFeatureConfig)

    def __post_init__(self) -> None:
        if not isinstance(self.tracking, TrackingConfig):
            raise ValueError("tracking must be a TrackingConfig")
        if not isinstance(self.features, TemporalFeatureConfig):
            raise ValueError("features must be a TemporalFeatureConfig")


@dataclass(frozen=True)
class TrackTemporalFeatures:
    """Motion and lifecycle features for one track in one frame."""

    track_id: int
    frame_index: int
    timestamp_ms: float | None
    time_ms: float
    dt_ms: float
    class_id: int
    class_name: str
    role: ClassRole
    game_state_role: GameStateRole
    lane: int | None
    confidence: float
    state: TrackState
    lifecycle: Lifecycle
    event: Lifecycle | None
    center: tuple[float, float]
    previous_center: tuple[float, float] | None
    delta_x: float | None
    delta_y: float | None
    velocity_x: float | None
    velocity_y: float | None
    velocity_unit: str
    distance_proxy: float | None
    previous_distance_proxy: float | None
    distance_delta: float | None
    approaching: bool | None
    receding: bool | None
    visibility: str
    valid: bool
    hits: int
    misses: int
    confirmed: bool
    is_new: bool

    def as_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "frame_index": self.frame_index,
            "timestamp_ms": self.timestamp_ms,
            "time_ms": self.time_ms,
            "dt_ms": self.dt_ms,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "role": self.role.value,
            "game_state_role": self.game_state_role.value,
            "lane": self.lane,
            "confidence": self.confidence,
            "state": self.state.value,
            "lifecycle": self.lifecycle.value,
            "event": self.event.value if self.event is not None else None,
            "center": [self.center[0], self.center[1]],
            "previous_center": (
                [self.previous_center[0], self.previous_center[1]]
                if self.previous_center is not None
                else None
            ),
            "delta_x": self.delta_x,
            "delta_y": self.delta_y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "velocity_unit": self.velocity_unit,
            "distance_proxy": self.distance_proxy,
            "previous_distance_proxy": self.previous_distance_proxy,
            "distance_delta": self.distance_delta,
            "approaching": self.approaching,
            "receding": self.receding,
            "visibility": self.visibility,
            "valid": self.valid,
            "hits": self.hits,
            "misses": self.misses,
            "confirmed": self.confirmed,
            "is_new": self.is_new,
        }


@dataclass(frozen=True)
class LifecycleEvent:
    """One lifecycle transition at a definite time."""

    track_id: int
    frame_index: int
    timestamp_ms: float | None
    time_ms: float
    event: Lifecycle
    class_id: int
    class_name: str
    role: ClassRole
    lane: int | None
    confidence: float
    distance_proxy: float | None
    feature_values: dict
    is_pulse: bool
    detail: str

    def as_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "frame_index": self.frame_index,
            "timestamp_ms": self.timestamp_ms,
            "time_ms": self.time_ms,
            "event": self.event.value,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "role": self.role.value,
            "lane": self.lane,
            "confidence": self.confidence,
            "distance_proxy": self.distance_proxy,
            "feature_values": dict(self.feature_values),
            "is_pulse": self.is_pulse,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class TemporalFrame:
    """Temporal output for one frame, suitable for scheduling."""

    frame_index: int
    frame_id: str | None
    timestamp_ms: float | None
    time_ms: float
    dt_ms: float
    is_gap: bool
    tracks: tuple[TrackTemporalFeatures, ...]
    events: tuple[LifecycleEvent, ...]
    features: dict
    state: GameState
    unrepresented_tracks: int
    notes: tuple[str, ...] = ()
    matches: tuple[TrackMatch, ...] = ()

    def as_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "time_ms": self.time_ms,
            "dt_ms": self.dt_ms,
            "is_gap": self.is_gap,
            "tracks": [item.as_dict() for item in self.tracks],
            "events": [item.as_dict() for item in self.events],
            "matches": [item.as_dict() for item in self.matches],
            "features": dict(self.features),
            "game_state": {
                "time_ms": self.state.time_ms,
                "features": dict(self.state.features()),
            },
            "unrepresented_tracks": self.unrepresented_tracks,
            "notes": list(self.notes),
        }


@dataclass
class _TrackMotion:
    appeared_emitted: bool = False
    occluded_emitted: bool = False
    uncertain_emitted: bool = False
    disappeared_emitted: bool = False
    last_lifecycle: Lifecycle | None = None
    persisting_run: int = 0
    last_event_frame: dict[str, int] = field(default_factory=dict)


class TemporalFeatureEncoder:
    """Turn tracker updates into per-track features, lifecycle and events."""

    def __init__(
        self,
        config: TemporalFeatureConfig | None = None,
        *,
        min_hits: int = 2,
    ) -> None:
        self.config = config or TemporalFeatureConfig()
        if not isinstance(self.config, TemporalFeatureConfig):
            raise ValueError("config must be a TemporalFeatureConfig")
        if isinstance(min_hits, bool) or not isinstance(min_hits, int) or min_hits < 1:
            raise ValueError("min_hits must be a positive integer")
        self.min_hits = min_hits
        self._states: dict[int, _TrackMotion] = {}
        self._last_time_ms: float | None = None
        self._frame_index = -1

    def reset(self) -> None:
        self._states.clear()
        self._last_time_ms = None
        self._frame_index = -1

    def _state(self, track_id: int) -> _TrackMotion:
        state = self._states.get(track_id)
        if state is None:
            state = _TrackMotion()
            self._states[track_id] = state
        return state

    def _resolve_time(self, timestamp_ms: float | None, frame_index: int) -> float:
        if timestamp_ms is None:
            if self._last_time_ms is None:
                return frame_index * self.config.frame_interval_ms
            return self._last_time_ms + self.config.frame_interval_ms
        value = _finite(timestamp_ms, "timestamp_ms")
        if value < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if self._last_time_ms is not None and value <= self._last_time_ms:
            raise ValueError(
                "timestamps must increase strictly for causal temporal features"
            )
        return value

    def _classify(
        self,
        record: TrackRecord,
        *,
        confirmed_before: bool,
        distance_delta: float | None,
    ) -> Lifecycle:
        if record.state is TrackState.OCCLUDED:
            # A never-confirmed track that misses a frame is noise, not an
            # object known to be occluded.
            return (
                Lifecycle.OCCLUDED
                if record.hits >= self._min_hits
                else Lifecycle.UNCERTAIN
            )
        if record.state is TrackState.LOST:
            return Lifecycle.DISAPPEARED
        if (
            record.state is TrackState.TENTATIVE
            or record.confidence < self.config.confidence_floor
        ):
            return Lifecycle.UNCERTAIN
        if not confirmed_before:
            return Lifecycle.APPEARED
        if distance_delta is None:
            return Lifecycle.PERSISTING
        if distance_delta <= -self.config.distance_change_threshold:
            return Lifecycle.APPROACHING
        if distance_delta >= self.config.distance_change_threshold:
            return Lifecycle.RECEDING
        return Lifecycle.PERSISTING

    def _feature_values(self, record: TrackRecord) -> dict:
        observation = record.observation
        if observation.lane is None or observation.distance_proxy is None:
            return {}
        kind = int(observation.lane)
        distance = float(observation.distance_proxy)
        role = observation.game_state_role
        if role in (GameStateRole.OBSTACLE_LOW, GameStateRole.OBSTACLE_HIGH):
            return {
                "obstacle_present": 1.0,
                "obstacle_lane": kind,
                "obstacle_distance": distance,
                "obstacle_type": (
                    1 if role is GameStateRole.OBSTACLE_HIGH else 0
                ),
            }
        if role is GameStateRole.TRAIN:
            return {
                "train_present": 1.0,
                "train_lane": kind,
                "train_distance": distance,
            }
        if observation.role is ClassRole.COIN:
            return {
                "coin_present": 1.0,
                "coin_lane": kind,
                "coin_distance": distance,
            }
        return {}

    def _emit(
        self,
        events: list[LifecycleEvent],
        record: TrackRecord,
        *,
        event: Lifecycle,
        frame_index: int,
        time_ms: float,
        detail: str,
        allow_repeat: bool = False,
    ) -> None:
        motion = self._state(record.track_id)
        key = event.value
        last = motion.last_event_frame.get(key)
        if not allow_repeat and last is not None:
            if frame_index - last < self.config.event_cooldown_frames:
                return
        motion.last_event_frame[key] = frame_index
        values = self._feature_values(record) if event in PULSE_EVENTS else {}
        events.append(
            LifecycleEvent(
                track_id=record.track_id,
                frame_index=frame_index,
                timestamp_ms=record.observation.timestamp_ms,
                time_ms=time_ms,
                event=event,
                class_id=record.class_id,
                class_name=record.class_name,
                role=record.observation.role,
                lane=record.lane,
                confidence=record.confidence,
                distance_proxy=record.distance_proxy,
                feature_values=values,
                is_pulse=bool(values),
                detail=detail,
            )
        )

    def _features_for(
        self,
        record: TrackRecord,
        *,
        frame_index: int,
        timestamp_ms: float | None,
        time_ms: float,
        dt_ms: float,
        velocity_unit: str,
        lifecycle: Lifecycle,
        event: Lifecycle | None,
    ) -> TrackTemporalFeatures:
        observation = record.observation
        previous = record.previous
        center = observation.center_normalized
        previous_center = previous.center_normalized if previous is not None else None
        # An occluded/lost track carries its last observation, not a current
        # one. Motion over that stale pair is not a measurement, so it is
        # suppressed rather than repeated every frame.
        has_current_measurement = record.state not in (
            TrackState.OCCLUDED,
            TrackState.LOST,
        )
        delta_x = delta_y = None
        velocity_x = velocity_y = None
        if has_current_measurement and previous_center is not None:
            delta_x = center[0] - previous_center[0]
            delta_y = center[1] - previous_center[1]
            if velocity_unit == "normalized_per_second":
                seconds = dt_ms / 1000.0
                if seconds > 0:
                    velocity_x = delta_x / seconds
                    velocity_y = delta_y / seconds
            else:
                velocity_x = delta_x
                velocity_y = delta_y
            if (
                velocity_x is not None
                and abs(velocity_x) < self.config.velocity_epsilon
            ):
                velocity_x = 0.0
            if (
                velocity_y is not None
                and abs(velocity_y) < self.config.velocity_epsilon
            ):
                velocity_y = 0.0
        previous_distance = (
            previous.distance_proxy if previous is not None else None
        )
        distance_delta = None
        if (
            has_current_measurement
            and observation.distance_proxy is not None
            and previous_distance is not None
        ):
            distance_delta = observation.distance_proxy - previous_distance
        approaching = (
            None
            if distance_delta is None
            else distance_delta <= -self.config.distance_change_threshold
        )
        receding = (
            None
            if distance_delta is None
            else distance_delta >= self.config.distance_change_threshold
        )
        return TrackTemporalFeatures(
            track_id=record.track_id,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            time_ms=time_ms,
            dt_ms=dt_ms,
            class_id=record.class_id,
            class_name=record.class_name,
            role=observation.role,
            game_state_role=observation.game_state_role,
            lane=record.lane,
            confidence=record.confidence,
            state=record.state,
            lifecycle=lifecycle,
            event=event,
            center=center,
            previous_center=previous_center,
            delta_x=delta_x,
            delta_y=delta_y,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
            velocity_unit=velocity_unit,
            distance_proxy=observation.distance_proxy,
            previous_distance_proxy=previous_distance,
            distance_delta=distance_delta,
            approaching=approaching,
            receding=receding,
            visibility=observation.visibility.value,
            valid=observation.valid,
            hits=record.hits,
            misses=record.misses,
            confirmed=record.confirmed,
            is_new=record.is_new,
        )

    def update(self, tracks: FrameTracks) -> tuple[tuple[TrackTemporalFeatures, ...], tuple[LifecycleEvent, ...]]:
        if not isinstance(tracks, FrameTracks):
            raise ValueError("tracks must be a FrameTracks")
        frame_index = tracks.frame_index
        time_ms = self._resolve_time(tracks.timestamp_ms, frame_index)
        dt_ms = (
            self.config.frame_interval_ms
            if self._last_time_ms is None
            else time_ms - self._last_time_ms
        )
        self._last_time_ms = time_ms
        if self._frame_index >= 0 and frame_index <= self._frame_index:
            raise ValueError("tracker frame indices must increase strictly")
        self._frame_index = frame_index
        velocity_unit = (
            "normalized_per_second"
            if tracks.timestamp_ms is not None
            else "normalized_per_frame"
        )

        features: list[TrackTemporalFeatures] = []
        events: list[LifecycleEvent] = []
        seen: set[int] = set()

        for record in tracks.tracks:
            seen.add(record.track_id)
            motion = self._state(record.track_id)
            previous = record.previous
            distance_delta = None
            if (
                record.observation.distance_proxy is not None
                and previous is not None
                and previous.distance_proxy is not None
            ):
                distance_delta = (
                    record.observation.distance_proxy - previous.distance_proxy
                )
            confirmed_before = motion.appeared_emitted
            lifecycle = self._classify(
                record,
                confirmed_before=confirmed_before,
                distance_delta=distance_delta,
            )
            event: Lifecycle | None = None

            if record.state is TrackState.OCCLUDED:
                if (
                    record.hits >= self._min_hits
                    and not motion.occluded_emitted
                ):
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.OCCLUDED,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail=(
                            "missed association; last observation retained within "
                            "max_age"
                        ),
                    )
                    motion.occluded_emitted = True
                    event = Lifecycle.OCCLUDED
                elif record.hits < self._min_hits and not motion.uncertain_emitted:
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.UNCERTAIN,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail="tentative track missed; treated as detector noise",
                    )
                    motion.uncertain_emitted = True
                    event = Lifecycle.UNCERTAIN
            elif (
                not motion.appeared_emitted
                and lifecycle is not Lifecycle.UNCERTAIN
            ):
                self._emit(
                    events,
                    record,
                    event=Lifecycle.APPEARED,
                    frame_index=frame_index,
                    time_ms=time_ms,
                    detail=(
                        f"confirmed after {record.hits} matched frame(s)"
                    ),
                    allow_repeat=True,
                )
                motion.appeared_emitted = True
                motion.uncertain_emitted = False
                motion.occluded_emitted = False
                lifecycle = Lifecycle.APPEARED
                event = Lifecycle.APPEARED
            elif lifecycle is Lifecycle.UNCERTAIN:
                if not motion.uncertain_emitted:
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.UNCERTAIN,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail=(
                            "track is tentative or below the confidence floor"
                        ),
                    )
                    motion.uncertain_emitted = True
                    event = Lifecycle.UNCERTAIN
            else:
                motion.uncertain_emitted = False
                motion.occluded_emitted = False
                if (
                    lifecycle is Lifecycle.APPROACHING
                    and motion.last_lifecycle is not Lifecycle.APPROACHING
                ):
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.APPROACHING,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail=(
                            "distance proxy decreased by at least "
                            f"{self.config.distance_change_threshold:.4f}"
                        ),
                    )
                    event = Lifecycle.APPROACHING
                elif (
                    lifecycle is Lifecycle.RECEDING
                    and motion.last_lifecycle is not Lifecycle.RECEDING
                ):
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.RECEDING,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail=(
                            "distance proxy increased by at least "
                            f"{self.config.distance_change_threshold:.4f}"
                        ),
                    )
                    event = Lifecycle.RECEDING

            # A PERSISTING frame inside an ongoing approach/recede is usually a
            # threshold dip, not a new episode: retain the previous direction
            # until the quiet run exceeds the cooldown window.
            if lifecycle is Lifecycle.PERSISTING:
                motion.persisting_run += 1
                if motion.persisting_run > self.config.event_cooldown_frames:
                    motion.last_lifecycle = Lifecycle.PERSISTING
            else:
                motion.persisting_run = 0
                motion.last_lifecycle = lifecycle
            features.append(
                self._features_for(
                    record,
                    frame_index=frame_index,
                    timestamp_ms=tracks.timestamp_ms,
                    time_ms=time_ms,
                    dt_ms=dt_ms,
                    velocity_unit=velocity_unit,
                    lifecycle=lifecycle,
                    event=event,
                )
            )

        for record in tracks.lost:
            if record.track_id in seen:
                continue
            seen.add(record.track_id)
            motion = self._state(record.track_id)
            if record.hits >= self._min_hits:
                if not motion.disappeared_emitted:
                    self._emit(
                        events,
                        record,
                        event=Lifecycle.DISAPPEARED,
                        frame_index=frame_index,
                        time_ms=time_ms,
                        detail="track exceeded max_age without an association",
                        allow_repeat=True,
                    )
                    motion.disappeared_emitted = True
                lifecycle = Lifecycle.DISAPPEARED
                event = Lifecycle.DISAPPEARED
            else:
                lifecycle = Lifecycle.UNCERTAIN
                event = None
            features.append(
                self._features_for(
                    record,
                    frame_index=frame_index,
                    timestamp_ms=tracks.timestamp_ms,
                    time_ms=time_ms,
                    dt_ms=dt_ms,
                    velocity_unit=velocity_unit,
                    lifecycle=lifecycle,
                    event=event,
                )
            )

        events.sort(
            key=lambda item: (
                item.time_ms,
                item.track_id,
                EVENT_PRIORITY[item.event],
            )
        )
        features.sort(key=lambda item: item.track_id)
        self._prune()
        return tuple(features), tuple(events)

    @property
    def _min_hits(self) -> int:
        return self.min_hits

    def _prune(self) -> None:
        if len(self._states) <= 256:
            return
        for track_id in sorted(self._states)[: len(self._states) - 128]:
            del self._states[track_id]

    def describe(self) -> dict:
        return {
            "encoder": "causal_track_motion_lifecycle",
            "config": {
                "min_hits": self.min_hits,
                "distance_change_threshold": self.config.distance_change_threshold,
                "confidence_floor": self.config.confidence_floor,
                "event_cooldown_frames": self.config.event_cooldown_frames,
                "frame_interval_ms": self.config.frame_interval_ms,
                "gap_threshold_ms": self.config.gap_threshold_ms,
                "velocity_epsilon": self.config.velocity_epsilon,
            },
            "lifecycle_states": [item.value for item in Lifecycle],
            "pulse_events": sorted(item.value for item in PULSE_EVENTS),
            "transition_rules": [
                "tentative or below-floor track -> UNCERTAIN",
                "new confirmed track -> APPEARED once",
                "distance proxy decrease >= threshold -> APPROACHING",
                "distance proxy increase >= threshold -> RECEDING",
                "confirmed track without a significant change -> PERSISTING; "
                "a run no longer than the cooldown keeps the previous direction",
                "missed association within max_age -> OCCLUDED on first miss",
                "missed association beyond max_age -> DISAPPEARED once",
            ],
            "limitations": [
                "Velocity is image-space, not physical.",
                "Approach/recede uses the uncalibrated distance proxy.",
                "Occlusion is inferred from missed associations, not observed.",
            ],
        }


def _state_eligible(item: TrackTemporalFeatures, min_hits: int) -> bool:
    """Confirmed tracks, plus occluded tracks that were confirmed before.

    An occluded track carries its last observation (``max_age`` frames old at
    most); representing it keeps a one-frame detector miss from looking like
    an object disappearance. Tentative noise never becomes state.
    """
    if item.state is TrackState.CONFIRMED:
        return True
    return item.state is TrackState.OCCLUDED and item.hits >= min_hits


def _nearest(records: tuple[TrackTemporalFeatures, ...], min_hits: int):
    candidates = [
        item
        for item in records
        if _state_eligible(item, min_hits)
        and item.lane is not None
        and item.distance_proxy is not None
    ]
    candidates.sort(
        key=lambda item: (item.distance_proxy, item.track_id)
    )
    return candidates[0] if candidates else None


def build_state(
    tracks: tuple[TrackTemporalFeatures, ...],
    *,
    time_ms: float,
    min_hits: int = 2,
) -> tuple[GameState, int, tuple[str, ...]]:
    """Build the existing single-object ``GameState`` from tracked objects.

    The nearest eligible track of each kind is represented. Other eligible
    tracks are counted in ``unrepresented_tracks`` rather than dropped
    silently. Tentative tracks never drive the state. An occluded track may
    drive it only with the last observation it actually had, never with
    extrapolated geometry.
    """
    if isinstance(min_hits, bool) or not isinstance(min_hits, int) or min_hits < 1:
        raise ValueError("min_hits must be a positive integer")
    eligible = [item for item in tracks if _state_eligible(item, min_hits)]
    obstacles = [item for item in eligible if item.role is ClassRole.OBSTACLE]
    trains = [item for item in eligible if item.role is ClassRole.TRAIN]
    coins = [item for item in eligible if item.role is ClassRole.COIN]
    players = [item for item in eligible if item.role is ClassRole.PLAYER]

    notes: list[str] = []
    player = PlayerState()
    if len(players) == 1 and players[0].lane is not None:
        player = PlayerState(lane=Lane(players[0].lane))
    elif len(players) > 1:
        notes.append(
            f"{len(players)} player tracks; no single identity was selected."
        )

    obstacle = None
    representative = _nearest(tuple(obstacles), min_hits)
    if representative is not None:
        obstacle_type = (
            ObstacleType.HIGH
            if representative.game_state_role is GameStateRole.OBSTACLE_HIGH
            else ObstacleType.LOW
        )
        obstacle = ObstacleState(
            present=True,
            lane=Lane(representative.lane),
            distance=representative.distance_proxy,
            obstacle_type=obstacle_type,
        )
        if representative.state is TrackState.OCCLUDED:
            notes.append(
                f"Obstacle state uses track {representative.track_id}'s last "
                f"observation ({representative.misses} missed frame(s))."
            )

    train = None
    representative = _nearest(tuple(trains), min_hits)
    if representative is not None:
        train = TrainState(
            present=True,
            lane=Lane(representative.lane),
            distance=representative.distance_proxy,
        )
        if representative.state is TrackState.OCCLUDED:
            notes.append(
                f"Train state uses track {representative.track_id}'s last "
                f"observation ({representative.misses} missed frame(s))."
            )

    coin = None
    representative = _nearest(tuple(coins), min_hits)
    if representative is not None:
        coin = CoinState(
            present=True,
            lane=Lane(representative.lane),
            distance=representative.distance_proxy,
        )
        if representative.state is TrackState.OCCLUDED:
            notes.append(
                f"Coin state uses track {representative.track_id}'s last "
                f"observation ({representative.misses} missed frame(s))."
            )

    represented = 1 if obstacle is not None else 0
    represented += 1 if train is not None else 0
    represented += 1 if coin is not None else 0
    represented += 1 if len(players) == 1 and players[0].lane is not None else 0
    unrepresented = max(0, len(eligible) - represented)
    if unrepresented:
        notes.append(
            f"{unrepresented} tracked object(s) are not representable by the "
            "single-object GameState."
        )
    state = GameState(
        player=player,
        obstacle=obstacle,
        train=train,
        coin=coin,
        time_ms=time_ms,
    )
    return state, unrepresented, tuple(notes)


class TemporalSequenceProcessor:
    """Frame-to-frame tracker plus temporal feature/lifecycle encoder."""

    def __init__(self, config: TemporalConfig | None = None) -> None:
        self.config = config or TemporalConfig()
        if not isinstance(self.config, TemporalConfig):
            raise ValueError("config must be a TemporalConfig")
        self.tracker = MultiObjectTracker(self.config.tracking)
        self.feature_encoder = TemporalFeatureEncoder(
            self.config.features, min_hits=self.config.tracking.min_hits
        )
        self._last_time_ms: float | None = None

    def reset(self) -> None:
        self.tracker.reset()
        self.feature_encoder.reset()
        self._last_time_ms = None

    def process(self, frame) -> TemporalFrame:
        from perception.observations import FrameObservations

        if not isinstance(frame, FrameObservations):
            raise ValueError("frame must be a FrameObservations")
        tracks = self.tracker.update(frame)
        features, events = self.feature_encoder.update(tracks)

        if frame.timestamp_ms is None:
            if self._last_time_ms is None:
                time_ms = tracks.frame_index * self.config.features.frame_interval_ms
            else:
                time_ms = (
                    self._last_time_ms + self.config.features.frame_interval_ms
                )
        else:
            time_ms = float(frame.timestamp_ms)
        dt_ms = (
            self.config.features.frame_interval_ms
            if self._last_time_ms is None
            else time_ms - self._last_time_ms
        )
        self._last_time_ms = time_ms
        is_gap = dt_ms > self.config.features.gap_threshold_ms

        state, unrepresented, notes = build_state(
            features,
            time_ms=time_ms,
            min_hits=self.config.tracking.min_hits,
        )
        if is_gap:
            notes = notes + (
                f"frame interval {dt_ms:.3f} ms exceeds the gap threshold "
                f"{self.config.features.gap_threshold_ms:.3f} ms; features are "
                "computed over the full interval.",
            )
        if not notes:
            notes = ()
        return TemporalFrame(
            frame_index=tracks.frame_index,
            frame_id=tracks.frame_id,
            timestamp_ms=frame.timestamp_ms,
            time_ms=time_ms,
            dt_ms=dt_ms,
            is_gap=is_gap,
            tracks=features,
            events=events,
            features=dict(state.features()),
            state=state,
            unrepresented_tracks=unrepresented,
            notes=notes,
            matches=tracks.matches,
        )

    def describe(self) -> dict:
        return {
            "processor": "phase_3c_temporal_sequence",
            "tracking": self.tracker.describe(),
            "features": self.feature_encoder.describe(),
            "state_policy": (
                "nearest confirmed track per kind; the GameState schema is not "
                "modified"
            ),
        }
