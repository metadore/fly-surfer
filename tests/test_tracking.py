"""Phase 3C tracking tests.

Sequences are synthetic observations. No detector, model or dataset is used.
"""

from __future__ import annotations

import pytest

from perception.config import ClassRole, GameStateRole
from perception.geometry import BoundingBox, NormalizedBox
from perception.observations import FrameObservations, VisualObservation
from perception.tracking import (
    MultiObjectTracker,
    TrackingConfig,
    TrackState,
    box_iou,
    center_distance,
)

TRAIN = (0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)
OBSTACLE = (1, "jump-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW)


def observation(index, kind, box, *, confidence=0.9, timestamp=None, frame_id="f"):
    class_id, name, role, game_role = kind
    x1, y1, x2, y2 = box
    return VisualObservation(
        object_index=index,
        class_id=class_id,
        class_name=name,
        role=role,
        game_state_role=game_role,
        lane=1,
        bbox_screen=BoundingBox(x1 * 300, y1 * 600, x2 * 300, y2 * 600),
        bbox_normalized=NormalizedBox(x1, y1, x2, y2),
        confidence=confidence,
        frame_id=frame_id,
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


def tracker(**overrides):
    defaults = dict(min_hits=2, max_age=2, history_limit=8)
    defaults.update(overrides)
    return MultiObjectTracker(TrackingConfig(**defaults))


def test_iou_and_distance_helpers() -> None:
    first = NormalizedBox(0.1, 0.1, 0.3, 0.3)
    second = NormalizedBox(0.1, 0.1, 0.3, 0.3)
    assert box_iou(first, second) == pytest.approx(1.0)
    assert center_distance(first, second) == pytest.approx(0.0)
    far = NormalizedBox(0.7, 0.7, 0.9, 0.9)
    assert box_iou(first, far) == 0.0
    assert center_distance(first, far) > 0.5


def test_stable_track_id_across_frames() -> None:
    tracker_ = tracker()
    first = tracker_.update(frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0))
    assert len(first.created) == 1
    assert first.created[0].state is TrackState.TENTATIVE
    track_id = first.created[0].track_id

    second = tracker_.update(
        frame([observation(0, TRAIN, (0.41, 0.5, 0.61, 0.7))], 1)
    )
    assert len(second.created) == 0
    assert second.tracks[0].track_id == track_id
    assert second.tracks[0].state is TrackState.CONFIRMED
    assert second.tracks[0].hits == 2
    assert second.tracks[0].history_length == 2

    third = tracker_.update(
        frame([observation(0, TRAIN, (0.42, 0.5, 0.62, 0.7))], 2)
    )
    assert third.tracks[0].track_id == track_id
    assert third.tracks[0].hits == 3


def test_temporary_miss_is_occluded_then_recovers() -> None:
    tracker_ = tracker()
    tracker_.update(frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0))
    confirmed = tracker_.update(
        frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 1)
    )
    track_id = confirmed.tracks[0].track_id

    missed = tracker_.update(frame([], 2))
    assert len(missed.occluded) == 1
    assert missed.occluded[0].track_id == track_id
    assert missed.occluded[0].state is TrackState.OCCLUDED
    assert missed.occluded[0].misses == 1
    assert missed.occluded[0].history_length == 2

    recovered = tracker_.update(
        frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 3)
    )
    assert recovered.tracks[0].track_id == track_id
    assert recovered.tracks[0].state is TrackState.CONFIRMED
    assert recovered.tracks[0].misses == 0
    assert recovered.tracks[0].hits == 3


def test_track_is_lost_after_max_age_and_retired() -> None:
    tracker_ = tracker(max_age=2)
    tracker_.update(frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0))
    tracker_.update(frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 1))
    for index in (2, 3):
        result = tracker_.update(frame([], index))
        assert result.lost == ()
        assert result.occluded[0].state is TrackState.OCCLUDED

    final = tracker_.update(frame([], 4))
    assert len(final.lost) == 1
    assert final.lost[0].state is TrackState.LOST
    assert final.tracks == ()
    assert len(tracker_.retired_tracks) == 1
    assert tracker_.retired_tracks[0]["track_id"] == final.lost[0].track_id


def test_duplicate_detections_are_suppressed_per_frame() -> None:
    tracker_ = tracker(min_hits=1)
    result = tracker_.update(
        frame(
            [
                observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7), confidence=0.9),
                observation(1, TRAIN, (0.405, 0.5, 0.605, 0.7), confidence=0.6),
            ],
            0,
        )
    )
    assert len(result.created) == 1
    assert result.created[0].observation.object_index == 0
    assert len(result.duplicates) == 1
    assert result.duplicates[0].object_index == 1
    assert result.duplicates[0].kept_index == 0


def test_multiple_objects_keep_distinct_ids() -> None:
    tracker_ = tracker(min_hits=1)
    for index in range(4):
        result = tracker_.update(
            frame(
                [
                    observation(0, TRAIN, (0.1 + 0.01 * index, 0.5, 0.3, 0.7)),
                    observation(1, OBSTACLE, (0.6, 0.4, 0.8, 0.6)),
                ],
                index,
            )
        )
        assert len(result.tracks) == 2
        by_class = {item.class_name: item.track_id for item in result.tracks}
        assert by_class["train"] != by_class["jump-barrier"]
    assert result.tracks[0].track_id == 1
    assert result.tracks[1].track_id == 2


def test_class_aware_association_does_not_reuse_track() -> None:
    tracker_ = tracker(min_hits=1)
    first = tracker_.update(
        frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0)
    )
    second = tracker_.update(
        frame([observation(0, OBSTACLE, (0.4, 0.5, 0.6, 0.7))], 1)
    )
    assert len(first.tracks) == 1
    assert len(second.tracks) == 2
    ids = {item.track_id for item in second.tracks}
    assert len(ids) == 2
    assert first.tracks[0].track_id in ids


def test_class_switch_when_class_aware_is_off() -> None:
    tracker_ = tracker(min_hits=1, class_aware=False)
    tracker_.update(frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0))
    result = tracker_.update(
        frame([observation(0, OBSTACLE, (0.4, 0.5, 0.6, 0.7))], 1)
    )
    assert len(result.tracks) == 1
    assert result.tracks[0].class_name == "jump-barrier"
    assert any("switched class" in note for note in result.notes)


def test_history_is_bounded() -> None:
    tracker_ = tracker(min_hits=1, history_limit=3)
    for index in range(8):
        result = tracker_.update(
            frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], index)
        )
    assert result.tracks[0].history_length == 3
    assert result.tracks[0].hits == 8


def test_identical_sequences_are_deterministic() -> None:
    sequence = [
        [observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))],
        [observation(1, OBSTACLE, (0.1, 0.4, 0.3, 0.6))],
        [],
        [
            observation(0, TRAIN, (0.42, 0.5, 0.62, 0.7)),
            observation(1, OBSTACLE, (0.1, 0.4, 0.3, 0.6)),
        ],
    ]
    outputs = []
    for _ in range(2):
        tracker_ = tracker()
        frame_outputs = [
            tracker_.update(frame(items, index)).as_dict()
            for index, items in enumerate(sequence)
        ]
        outputs.append(frame_outputs)
    assert outputs[0] == outputs[1]


def test_timestamp_and_retirement_are_recorded() -> None:
    tracker_ = tracker(min_hits=1, max_age=1)
    tracker_.update(
        frame([observation(0, TRAIN, (0.4, 0.5, 0.6, 0.7))], 0, timestamp=100.0)
    )
    missed = tracker_.update(frame([], 1, timestamp=200.0))
    assert missed.occluded[0].last_timestamp_ms == pytest.approx(100.0)
    lost = tracker_.update(frame([], 2, timestamp=300.0))
    assert lost.lost[0].state is TrackState.LOST
    assert lost.lost[0].first_timestamp_ms == pytest.approx(100.0)
    assert lost.lost[0].last_timestamp_ms == pytest.approx(100.0)


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="min_hits"):
        TrackingConfig(min_hits=0)
    with pytest.raises(ValueError, match="gate_distance"):
        TrackingConfig(gate_distance=0.0)
    with pytest.raises(ValueError, match="iou_threshold"):
        TrackingConfig(iou_threshold=1.5)
    with pytest.raises(ValueError, match="frame must be"):
        tracker().update(object())
