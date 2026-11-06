"""Phase 3B.4 observation-layer and spatial-bridge tests.

All images and detections are synthetic. ``MockDetector`` is a scripted test
component, so nothing here is visual recognition or detector accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from perception.config import (
    ClassDefinition,
    ClassRole,
    ClassSchema,
    DistanceConfig,
    GameStateRole,
    LaneConfig,
    PerceptionConfig,
    PreprocessConfig,
    ValidationConfig,
)
from perception.detection import RawDetection
from perception.detector import MockDetector
from perception.geometry import BoundingBox, NormalizedBox
from perception.image import ImagePreprocessor
from perception.observations import (
    FrameObservations,
    ObservationBuilder,
    Visibility,
    VisualObservation,
    classify_visibility,
)
from perception.pipeline import PerceptionPipeline
from perception.sensory_bridge import (
    FEATURE_GROUPS,
    FEATURE_NAMES,
    SpatialFeatureBridge,
)
from sensory.game_state import Lane

TRAIN = ClassDefinition(0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)
JUMP = ClassDefinition(
    1, "jump-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW
)
ROLL = ClassDefinition(
    2, "roll-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_HIGH
)
PLAYER = ClassDefinition(
    10, "player", ClassRole.PLAYER, GameStateRole.UNSUPPORTED
)
COIN = ClassDefinition(11, "coin", ClassRole.COIN, GameStateRole.UNSUPPORTED)

CLASSES = (TRAIN, JUMP, ROLL)


def make_config(
    *,
    classes=CLASSES,
    player_class_ids=(),
    coin_class_ids=(),
    distance=None,
):
    return PerceptionConfig(
        preprocess=PreprocessConfig(),
        validation=ValidationConfig(),
        lanes=LaneConfig(),
        distance=distance or DistanceConfig(),
        schema=ClassSchema(
            classes=tuple(classes),
            player_class_ids=tuple(player_class_ids),
            coin_class_ids=tuple(coin_class_ids),
        ),
    )


def make_frame(width=300, height=600, frame_id="synthetic", timestamp_ms=None):
    image = Image.new("RGB", (width, height), (16, 24, 40))
    return ImagePreprocessor(PreprocessConfig()).from_image(
        image,
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
    )


def make_raw(class_id, x1, y1, x2, y2, confidence=0.9):
    return RawDetection(
        class_id=class_id,
        confidence=confidence,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
    )


def run(raws, config=None, frame=None):
    config = config or make_config()
    frame = frame or make_frame()
    pipeline = PerceptionPipeline(config, MockDetector(raws))
    return pipeline.run(frame)


# ---------------------------------------------------------------------------
# Observation fields
# ---------------------------------------------------------------------------


def test_single_object_observation_fields() -> None:
    raw = make_raw(0, 120, 450, 180, 570, confidence=0.9)
    frame = make_frame(timestamp_ms=1234.0)
    result = run([raw], frame=frame)
    observations = result.spatial.observations

    assert observations.n_observations == 1
    item = observations.observations[0]
    assert item.object_index == 0
    assert item.class_id == 0
    assert item.class_name == "train"
    assert item.role is ClassRole.TRAIN
    assert item.game_state_role is GameStateRole.TRAIN
    assert item.lane == int(Lane.CENTER)
    assert item.bbox_screen == BoundingBox(120.0, 450.0, 180.0, 570.0)
    assert item.bbox_normalized.as_tuple() == pytest.approx((0.4, 0.75, 0.6, 0.95))
    assert item.center_normalized == pytest.approx((0.5, 0.85))
    assert item.center_screen == pytest.approx((150.0, 510.0))
    assert item.relative_horizontal_position == pytest.approx(0.0)
    assert item.relative_vertical_position == pytest.approx(0.7)
    # bottom 0.95, horizon 0.15 -> (1 - 0.95) / 0.85
    assert item.distance_proxy == pytest.approx(0.058824, abs=1e-6)
    assert item.normalized_proximity == pytest.approx(0.941176, abs=1e-6)
    assert item.box_area_fraction == pytest.approx(0.2 * 0.2)
    assert item.confidence == pytest.approx(0.9)
    assert item.valid is True
    assert item.invalid_reason is None
    assert item.visibility is Visibility.IN_FRAME
    assert item.clamped is False
    assert item.frame_id == "synthetic"
    assert item.timestamp_ms == pytest.approx(1234.0)
    assert item.raw_index == 0
    assert observations.frame_id == "synthetic"
    assert observations.timestamp_ms == pytest.approx(1234.0)

    payload = observations.as_dict()
    assert json.loads(json.dumps(payload)) == payload
    assert payload["observations"][0]["distance_proxy"] == pytest.approx(
        0.058824, abs=1e-6
    )
    assert payload["observations"][0]["visibility"] == "in_frame"


def test_relative_positions_follow_viewport_centre() -> None:
    left = make_raw(1, 10, 300, 60, 400)
    right = make_raw(1, 240, 300, 290, 400)
    result = run([left, right])
    observations = result.spatial.observations.observations
    assert observations[0].relative_horizontal_position < -0.5
    assert observations[1].relative_horizontal_position > 0.5
    # Boxes are at y=300..400 in a 600 px frame, so their centres are below
    # the vertical midpoint (image y grows downwards).
    assert observations[0].relative_vertical_position > 0.0
    assert observations[1].relative_vertical_position > 0.0


def test_visibility_edge_and_disabled_distance() -> None:
    config = make_config(distance=DistanceConfig(mode="none"))
    raw = make_raw(1, 0, 450, 60, 570)
    result = run([raw], config=config)
    item = result.spatial.observations.observations[0]

    assert item.visibility is Visibility.TOUCHES_EDGE
    assert item.distance_proxy is None
    assert item.normalized_proximity is None
    assert result.conversion.state.obstacle is None
    assert result.spatial.features["obstacle_present"] == 0.0
    assert result.spatial.features["obstacle_distance"] is None
    assert any(
        "distance mode is 'none'" in note
        for note in result.spatial.observations.notes
    )
    assert any(
        "no obstacle observation" in (group.reason or "")
        or "represented" in (group.reason or "")
        for group in result.spatial.groups
        if group.group == "obstacle"
    )


def test_classify_visibility_edges() -> None:
    assert classify_visibility(NormalizedBox(0.1, 0.1, 0.9, 0.9)) is Visibility.IN_FRAME
    assert (
        classify_visibility(NormalizedBox(0.0, 0.1, 0.9, 0.9))
        is Visibility.TOUCHES_EDGE
    )
    assert (
        classify_visibility(NormalizedBox(0.1, 0.1, 1.0, 0.9))
        is Visibility.TOUCHES_EDGE
    )


def test_observation_rejects_inconsistent_values() -> None:
    box = BoundingBox(10.0, 10.0, 20.0, 20.0)
    normalized = NormalizedBox(0.1, 0.1, 0.2, 0.2)
    common = dict(
        object_index=0,
        class_id=0,
        class_name="train",
        role=ClassRole.TRAIN,
        game_state_role=GameStateRole.TRAIN,
        lane=1,
        bbox_screen=box,
        bbox_normalized=normalized,
        confidence=0.9,
        frame_id=None,
        timestamp_ms=None,
    )
    with pytest.raises(ValueError, match="invalid_reason"):
        VisualObservation(**common, valid=False)
    with pytest.raises(ValueError, match="valid observation"):
        VisualObservation(**common, valid=True, invalid_reason="stale")
    with pytest.raises(ValueError, match="distance_proxy"):
        VisualObservation(**common, distance_proxy=1.5)
    with pytest.raises(ValueError, match="timestamp_ms"):
        VisualObservation(**{**common, "timestamp_ms": -1.0})
    with pytest.raises(ValueError, match="confidence"):
        VisualObservation(**{**common, "confidence": 1.2})
    with pytest.raises(ValueError, match="observations must be a tuple"):
        FrameObservations(
            frame_id=None,
            timestamp_ms=None,
            source_path=None,
            original_size=(10, 10),
            viewport_size=(10, 10),
            observations=[],
        )


def test_rejected_detections_are_retained() -> None:
    raw = make_raw(0, 120, 450, 180, 570)
    bad = make_raw(7, 120, 450, 180, 570)
    result = run([raw, bad])
    observations = result.spatial.observations
    assert observations.n_observations == 1
    assert len(observations.rejected) == 1
    assert observations.rejected[0].raw_index == 1
    assert observations.as_dict()["n_rejected"] == 1


# ---------------------------------------------------------------------------
# Spatial feature bridge
# ---------------------------------------------------------------------------


def test_bridge_features_are_the_game_state_contract() -> None:
    raw = make_raw(0, 120, 450, 180, 570)
    result = run([raw])

    assert set(result.spatial.features) == set(FEATURE_NAMES)
    assert tuple(result.spatial.features) == FEATURE_NAMES
    assert result.spatial.ordered_features == tuple(
        result.spatial.features[name] for name in FEATURE_NAMES
    )
    assert result.spatial.features == result.conversion.state.features()
    assert result.spatial.state is result.conversion.state

    train_group = next(
        group for group in result.spatial.groups if group.group == "train"
    )
    assert train_group.present is True
    assert train_group.object_index == 0
    assert train_group.class_name == "train"
    assert train_group.confidence == pytest.approx(0.9)
    assert train_group.lane == int(Lane.CENTER)
    assert train_group.feature_names == FEATURE_GROUPS["train"]

    player_group = next(
        group for group in result.spatial.groups if group.group == "player"
    )
    assert player_group.present is False
    assert player_group.object_index is None
    assert "player" in (player_group.reason or "")


def test_bridge_selects_nearest_object_and_keeps_all_observations() -> None:
    # Far obstacle at the left, near obstacle at the right.
    far = make_raw(1, 20, 300, 70, 360, confidence=0.6)
    near = make_raw(2, 230, 480, 280, 590, confidence=0.8)
    result = run([far, near])

    state = result.conversion.state
    assert state.obstacle is not None
    assert state.obstacle.lane is Lane.RIGHT
    assert state.obstacle.obstacle_type is not None
    assert int(state.obstacle.obstacle_type) == 1  # high (roll-barrier)

    observations = result.spatial.observations
    assert observations.n_observations == 2
    obstacle_group = next(
        group for group in result.spatial.groups if group.group == "obstacle"
    )
    assert obstacle_group.present is True
    assert obstacle_group.object_index == 1
    assert obstacle_group.n_candidates == 2
    assert obstacle_group.confidence == pytest.approx(0.8)
    assert obstacle_group.distance_proxy == pytest.approx(state.obstacle.distance)
    reasons = [item.reason for item in result.conversion.unrepresented]
    assert any("nearest obstacle" in reason for reason in reasons)


def test_bridge_player_and_coin_availability() -> None:
    config = make_config(
        classes=CLASSES + (PLAYER, COIN),
        player_class_ids=(10,),
        coin_class_ids=(11,),
    )
    player = make_raw(10, 120, 500, 180, 590)
    coin = make_raw(11, 130, 400, 170, 440)
    result = run([player, coin], config=config)

    groups = {group.group: group for group in result.spatial.groups}
    assert groups["player"].present is True
    assert groups["player"].object_index == 0
    assert groups["coin"].present is True
    assert groups["coin"].object_index == 1
    assert result.conversion.state.coin is not None
    assert result.conversion.state.coin.lane is Lane.CENTER


def test_bridge_without_objects_uses_baseline_features() -> None:
    result = run([])
    bundle = result.spatial
    assert bundle.observations.n_observations == 0
    assert bundle.features["player_lane"] == int(Lane.CENTER)
    assert bundle.features["obstacle_present"] == 0.0
    assert bundle.features["obstacle_lane"] is None
    assert bundle.features["train_present"] == 0.0
    for group in bundle.groups:
        if group.group == "player":
            assert group.present is False
        else:
            assert group.present is False
            assert group.object_index is None
            assert group.reason


def test_observation_builder_is_the_pipeline_layer() -> None:
    raw = make_raw(0, 120, 450, 180, 570)
    config = make_config()
    result = run([raw], config=config)
    builder = ObservationBuilder(config.distance)
    rebuilt = builder.from_scene(result.scene)
    assert rebuilt.as_dict() == result.spatial.observations.as_dict()

    bridge = SpatialFeatureBridge(config.distance)
    again = bridge.from_scene(result.scene)
    assert again.features == result.spatial.features
    assert again.groups == result.spatial.groups


def test_pipeline_result_serializes_new_fields() -> None:
    result = run([make_raw(0, 120, 450, 180, 570)])
    payload = result.as_dict()
    assert "observations" in payload
    assert set(payload["features"]) == set(FEATURE_NAMES)
    assert [group["group"] for group in payload["feature_groups"]] == [
        "player",
        "obstacle",
        "train",
        "coin",
    ]
    assert json.loads(json.dumps(payload)) == payload
