"""Phase 3C temporal feature, lifecycle and event tests.

All sequences are synthetic observations. No detector, dataset or connectome
is used, and no output here is evidence of biological validity.
"""

from __future__ import annotations

import pytest

from perception.config import ClassRole, GameStateRole
from perception.geometry import BoundingBox, NormalizedBox
from perception.observations import FrameObservations, VisualObservation
from perception.temporal import (
    LifecycleEvent,
    Lifecycle,
    PULSE_EVENTS,
    TemporalConfig,
    TemporalFeatureConfig,
    TemporalFeatureEncoder,
    TemporalSequenceProcessor,
    build_state,
)
from perception.tracking import TrackingConfig, TrackState
from sensory.game_state import GameState, ObstacleType

TRAIN = (0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)
OBSTACLE_LOW = (1, "jump-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW)
OBSTACLE_HIGH = (2, "high-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_HIGH)
COIN = (3, "coin", ClassRole.COIN, GameStateRole.UNSUPPORTED)


def observation(index, kind, box, *, lane=1, confidence=0.9, timestamp=None):
    class_id, name, role, game_role = kind
    x1, y1, x2, y2 = box
    return VisualObservation(
        object_index=index,
        class_id=class_id,
        class_name=name,
        role=role,
        game_state_role=game_role,
        lane=lane,
        bbox_screen=BoundingBox(x1 * 300, y1 * 600, x2 * 300, y2 * 600),
        bbox_normalized=NormalizedBox(x1, y1, x2, y2),
        confidence=confidence,
        frame_id="f",
        timestamp_ms=timestamp,
        distance_proxy=round(1.0 - y2, 6),
    )


def frame(observations, index=0, timestamp=None):
    return FrameObservations(
        frame_id=f"frame-{index}",
        timestamp_ms=timestamp,
        source_path=None,
        original_size=(300, 600),
        viewport_size=(300, 600),
        observations=tuple(observations),
    )


def processor(*, tracking=None, features=None):
    tracking_values = dict(min_hits=2, max_age=2, history_limit=8)
    tracking_values.update(tracking or {})
    feature_values = dict(
        distance_change_threshold=0.02,
        confidence_floor=0.25,
        event_cooldown_frames=2,
        frame_interval_ms=1000.0 / 30.0,
        gap_threshold_ms=100.0,
    )
    feature_values.update(features or {})
    return TemporalSequenceProcessor(
        TemporalConfig(
            tracking=TrackingConfig(**tracking_values),
            features=TemporalFeatureConfig(**feature_values),
        )
    )


def events_of(result, kind):
    return [item for item in result.events if item.event is kind]


def box(y2, *, y1=0.3, x1=0.3, x2=0.7):
    return (x1, y1, x2, y2)


def test_tentative_then_appeared_and_persisting() -> None:
    sequence = processor()
    first = sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 0)
    )
    assert first.tracks[0].state is TrackState.TENTATIVE
    assert first.tracks[0].lifecycle is Lifecycle.UNCERTAIN
    assert [item.event for item in first.events] == [Lifecycle.UNCERTAIN]
    assert first.events[0].is_pulse is False

    second = sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 1)
    )
    assert second.tracks[0].state is TrackState.CONFIRMED
    assert second.tracks[0].lifecycle is Lifecycle.APPEARED
    appeared = events_of(second, Lifecycle.APPEARED)
    assert len(appeared) == 1
    assert appeared[0].is_pulse is True
    assert appeared[0].track_id == second.tracks[0].track_id
    assert appeared[0].feature_values == {
        "train_present": 1.0,
        "train_lane": 1,
        "train_distance": 0.5,
    }

    third = sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 2)
    )
    assert third.tracks[0].lifecycle is Lifecycle.PERSISTING
    assert third.events == ()


def test_approach_and_recede_transitions() -> None:
    sequence = processor()
    sequence.process(frame([observation(0, TRAIN, box(0.50))], 0))
    sequence.process(frame([observation(0, TRAIN, box(0.50))], 1))
    approaching = sequence.process(
        frame([observation(0, TRAIN, box(0.62))], 2)
    )
    assert approaching.tracks[0].lifecycle is Lifecycle.APPROACHING
    assert approaching.tracks[0].distance_delta == pytest.approx(-0.12)
    assert approaching.tracks[0].approaching is True
    assert approaching.tracks[0].receding is False
    assert [item.event for item in approaching.events] == [
        Lifecycle.APPROACHING
    ]

    continued = sequence.process(
        frame([observation(0, TRAIN, box(0.74))], 3)
    )
    assert continued.tracks[0].lifecycle is Lifecycle.APPROACHING
    assert continued.events == ()

    receding = sequence.process(
        frame([observation(0, TRAIN, box(0.62))], 4)
    )
    assert receding.tracks[0].lifecycle is Lifecycle.RECEDING
    assert receding.tracks[0].distance_delta == pytest.approx(0.12)
    assert receding.tracks[0].receding is True
    assert [item.event for item in receding.events] == [Lifecycle.RECEDING]


def test_brief_threshold_dip_does_not_repeat_direction_event() -> None:
    sequence = processor(features={"event_cooldown_frames": 2})
    sequence.process(frame([observation(0, TRAIN, box(0.50))], 0))
    sequence.process(frame([observation(0, TRAIN, box(0.50))], 1))
    first = sequence.process(frame([observation(0, TRAIN, box(0.62))], 2))
    assert [item.event for item in first.events] == [Lifecycle.APPROACHING]

    dip = sequence.process(frame([observation(0, TRAIN, box(0.61))], 3))
    assert dip.tracks[0].lifecycle is Lifecycle.PERSISTING
    assert dip.events == ()

    resumed = sequence.process(
        frame([observation(0, TRAIN, box(0.73))], 4)
    )
    assert resumed.tracks[0].lifecycle is Lifecycle.APPROACHING
    assert events_of(resumed, Lifecycle.APPROACHING) == []

    for index, y2 in enumerate((0.72, 0.71, 0.70), start=5):
        quiet = sequence.process(frame([observation(0, TRAIN, box(y2))], index))
        assert quiet.tracks[0].lifecycle is Lifecycle.PERSISTING

    renewed = sequence.process(
        frame([observation(0, TRAIN, box(0.82))], 8)
    )
    assert [item.event for item in renewed.events] == [Lifecycle.APPROACHING]


def test_occlusion_is_reported_and_motion_is_suppressed() -> None:
    sequence = processor(tracking={"max_age": 2})
    sequence.process(frame([observation(0, TRAIN, box(0.5))], 0))
    sequence.process(frame([observation(0, TRAIN, box(0.5))], 1))

    occluded = sequence.process(frame([], 2))
    assert occluded.tracks[0].state is TrackState.OCCLUDED
    assert occluded.tracks[0].lifecycle is Lifecycle.OCCLUDED
    assert occluded.tracks[0].misses == 1
    assert occluded.tracks[0].delta_x is None
    assert occluded.tracks[0].velocity_x is None
    assert occluded.tracks[0].distance_delta is None
    assert occluded.tracks[0].approaching is None
    assert [item.event for item in occluded.events] == [Lifecycle.OCCLUDED]
    assert occluded.state.train is not None
    assert any("last observation" in note for note in occluded.notes)

    repeated = sequence.process(frame([], 3))
    assert repeated.tracks[0].lifecycle is Lifecycle.OCCLUDED
    assert repeated.events == ()

    lost = sequence.process(frame([], 4))
    assert lost.tracks[0].state is TrackState.LOST
    assert lost.tracks[0].lifecycle is Lifecycle.DISAPPEARED
    assert lost.tracks[0].delta_x is None
    assert [item.event for item in lost.events] == [Lifecycle.DISAPPEARED]
    assert lost.state.train is None
    assert lost.unrepresented_tracks == 0


def test_tentative_noise_never_emits_appearance_or_disappearance() -> None:
    sequence = processor(tracking={"max_age": 1})
    first = sequence.process(frame([observation(0, TRAIN, box(0.5))], 0))
    second = sequence.process(frame([], 1))
    third = sequence.process(frame([], 2))

    emitted = [item.event for item in first.events + second.events + third.events]
    assert emitted == [Lifecycle.UNCERTAIN]
    assert second.tracks[0].lifecycle is Lifecycle.UNCERTAIN
    assert third.tracks[0].lifecycle is Lifecycle.UNCERTAIN
    assert third.state.train is None
    assert all(
        frame_result.state.player.lane == GameState.neutral().player.lane
        for frame_result in (first, second, third)
    )


def test_confirmed_track_below_confidence_floor_is_uncertain() -> None:
    sequence = processor()
    sequence.process(
        frame([observation(0, TRAIN, box(0.5), confidence=0.9)], 0)
    )
    low = sequence.process(
        frame([observation(0, TRAIN, box(0.5), confidence=0.1)], 1)
    )
    assert low.tracks[0].state is TrackState.CONFIRMED
    assert low.tracks[0].lifecycle is Lifecycle.UNCERTAIN
    assert low.events == ()

    recovered = sequence.process(
        frame([observation(0, TRAIN, box(0.5), confidence=0.9)], 2)
    )
    assert recovered.tracks[0].lifecycle is Lifecycle.APPEARED
    assert [item.event for item in recovered.events] == [Lifecycle.APPEARED]


def test_event_cooldown_suppresses_repeated_approach_events() -> None:
    sequence = [
        box(0.50),
        box(0.50),
        box(0.62),
        box(0.62),
        box(0.74),
    ]

    def run(cooldown):
        pipeline = processor(features={"event_cooldown_frames": cooldown})
        outputs = [
            pipeline.process(frame([observation(0, TRAIN, item)], index))
            for index, item in enumerate(sequence)
        ]
        return [
            item.event
            for result in outputs
            for item in result.events
            if item.event is Lifecycle.APPROACHING
        ]

    assert run(0) == [Lifecycle.APPROACHING, Lifecycle.APPROACHING]
    assert run(4) == [Lifecycle.APPROACHING]


def test_motion_features_use_timestamp_velocity_units() -> None:
    sequence = processor()
    sequence.process(
        frame(
            [observation(0, TRAIN, (0.30, 0.40, 0.50, 0.60))],
            0,
            timestamp=0.0,
        )
    )
    second = sequence.process(
        frame(
            [observation(0, TRAIN, (0.35, 0.40, 0.55, 0.60))],
            1,
            timestamp=100.0,
        )
    )
    track = second.tracks[0]
    assert second.dt_ms == pytest.approx(100.0)
    assert track.velocity_unit == "normalized_per_second"
    assert track.delta_x == pytest.approx(0.05)
    assert track.delta_y == pytest.approx(0.0)
    assert track.velocity_x == pytest.approx(0.5)
    assert track.velocity_y == 0.0
    assert track.distance_delta == pytest.approx(0.0)
    assert track.approaching is False
    assert track.receding is False


def test_motion_features_without_timestamps_are_per_frame() -> None:
    sequence = processor()
    sequence.process(
        frame([observation(0, TRAIN, (0.30, 0.40, 0.50, 0.60))], 0)
    )
    second = sequence.process(
        frame([observation(0, TRAIN, (0.35, 0.40, 0.55, 0.60))], 1)
    )
    track = second.tracks[0]
    assert track.velocity_unit == "normalized_per_frame"
    assert track.velocity_x == pytest.approx(0.05)
    assert track.velocity_y == pytest.approx(0.0)


def test_irregular_intervals_and_gaps_are_flagged() -> None:
    sequence = processor(features={"gap_threshold_ms": 100.0})
    sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 0, timestamp=0.0)
    )
    long_gap = sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 1, timestamp=500.0)
    )
    assert long_gap.dt_ms == pytest.approx(500.0)
    assert long_gap.is_gap is True
    assert any("gap threshold" in note for note in long_gap.notes)

    short_gap = sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 2, timestamp=530.0)
    )
    assert short_gap.dt_ms == pytest.approx(30.0)
    assert short_gap.is_gap is False


def test_non_increasing_timestamps_are_rejected() -> None:
    sequence = processor()
    sequence.process(
        frame([observation(0, TRAIN, box(0.5))], 0, timestamp=100.0)
    )
    with pytest.raises(ValueError, match="strictly"):
        sequence.process(
            frame([observation(0, TRAIN, box(0.5))], 1, timestamp=100.0)
        )


def test_state_selects_nearest_and_counts_unrepresented() -> None:
    sequence = processor(tracking={"min_hits": 1})
    result = sequence.process(
        frame(
            [
                observation(
                    0, OBSTACLE_HIGH, (0.10, 0.30, 0.30, 0.50), lane=0
                ),
                observation(
                    1, OBSTACLE_LOW, (0.40, 0.40, 0.60, 0.70), lane=1
                ),
                observation(2, TRAIN, (0.70, 0.30, 0.90, 0.50), lane=2),
            ],
            0,
        )
    )
    assert result.state.obstacle is not None
    assert result.state.obstacle.lane.name == "CENTER"
    assert result.state.obstacle.distance == pytest.approx(0.30)
    assert result.state.obstacle.obstacle_type is ObstacleType.LOW
    assert result.state.train is not None
    assert result.state.train.lane.name == "RIGHT"
    assert result.unrepresented_tracks == 1
    assert any("not representable" in note for note in result.notes)


def test_high_obstacle_type_is_preserved() -> None:
    sequence = processor(tracking={"min_hits": 1})
    result = sequence.process(
        frame(
            [observation(0, OBSTACLE_HIGH, (0.10, 0.30, 0.30, 0.50), lane=0)],
            0,
        )
    )
    assert result.state.obstacle is not None
    assert result.state.obstacle.obstacle_type is ObstacleType.HIGH


def test_coin_role_is_represented_without_inventing_labels() -> None:
    sequence = processor(tracking={"min_hits": 1})
    result = sequence.process(
        frame([observation(0, COIN, (0.40, 0.40, 0.60, 0.70))], 0)
    )
    assert result.state.coin is not None
    assert result.state.coin.distance == pytest.approx(0.30)
    coin_events = [
        item
        for item in result.events
        if item.feature_values.get("coin_present") == 1.0
    ]
    assert len(coin_events) == 1


def test_features_match_the_existing_game_state_contract() -> None:
    sequence = processor()
    sequence.process(frame([observation(0, TRAIN, box(0.5))], 0))
    result = sequence.process(frame([observation(0, TRAIN, box(0.5))], 1))

    expected = GameState.neutral().features()
    assert set(result.features) == set(expected)
    assert result.features == result.state.features()

    for event in result.events:
        assert set(event.feature_values) <= set(expected)
    for event in result.events:
        if event.event in PULSE_EVENTS:
            assert event.is_pulse is True
        else:
            assert event.is_pulse is False


def test_temporal_output_serializes_game_state_role() -> None:
    sequence = processor()
    sequence.process(frame([observation(0, TRAIN, box(0.5))], 0))
    result = sequence.process(frame([observation(0, TRAIN, box(0.5))], 1))
    payload = result.as_dict()
    assert payload["tracks"][0]["game_state_role"] == "train"
    assert payload["game_state"]["features"] == result.state.features()
    assert payload["events"][0]["event"] == "appeared"
    assert payload["matches"][0]["track_id"] == payload["tracks"][0]["track_id"]
    assert payload["matches"][0]["object_index"] == 0


def test_identical_sequences_are_deterministic() -> None:
    steps = [
        [observation(0, TRAIN, box(0.40)), observation(1, OBSTACLE_LOW, (0.1, 0.4, 0.3, 0.6))],
        [observation(0, TRAIN, box(0.46)), observation(1, OBSTACLE_LOW, (0.1, 0.4, 0.3, 0.6))],
        [observation(0, TRAIN, box(0.52))],
        [],
        [observation(0, TRAIN, box(0.52))],
    ]

    def run():
        sequence = processor()
        return [
            sequence.process(frame(items, index)).as_dict()
            for index, items in enumerate(steps)
        ]

    assert run() == run()


def test_invalid_configuration_and_arguments_are_rejected() -> None:
    with pytest.raises(ValueError, match="distance_change_threshold"):
        TemporalFeatureConfig(distance_change_threshold=1.5)
    with pytest.raises(ValueError, match="event_cooldown_frames"):
        TemporalFeatureConfig(event_cooldown_frames=-1)
    with pytest.raises(ValueError, match="min_hits"):
        TemporalFeatureEncoder(min_hits=0)
    with pytest.raises(ValueError, match="frame must be"):
        processor().process(object())
    with pytest.raises(ValueError, match="tracks must be"):
        TemporalFeatureEncoder().update(object())
    with pytest.raises(ValueError, match="min_hits"):
        build_state((), time_ms=0.0, min_hits=0)


def test_describe_lists_lifecycle_states_and_transition_rules() -> None:
    description = processor().describe()
    states = description["features"]["lifecycle_states"]
    assert states == [item.value for item in Lifecycle]
    assert len(description["features"]["transition_rules"]) == len(Lifecycle)
    assert description["features"]["config"]["min_hits"] == 2
    assert description["processor"] == "phase_3c_temporal_sequence"


def test_event_records_are_immutable_and_ordered() -> None:
    sequence = processor(tracking={"min_hits": 1})
    result = sequence.process(
        frame(
            [
                observation(0, TRAIN, (0.70, 0.30, 0.90, 0.50), lane=2),
                observation(1, OBSTACLE_LOW, (0.10, 0.40, 0.30, 0.60), lane=0),
            ],
            0,
        )
    )
    assert all(isinstance(item, LifecycleEvent) for item in result.events)
    assert [item.track_id for item in result.events] == sorted(
        item.track_id for item in result.events
    )
    assert [item.track_id for item in result.tracks] == sorted(
        item.track_id for item in result.tracks
    )
