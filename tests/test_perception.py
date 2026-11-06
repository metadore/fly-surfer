"""Phase 3B.2A perception tests.

All images are synthetic and generated in memory. No Roboflow image or label
is read. The ``MockDetector`` is a scripted test component, not a model.
"""

from __future__ import annotations

import json

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
    load_perception_config,
)
from perception.detection import (
    Detection,
    DetectionValidator,
    RawDetection,
    RejectionReason,
    coerce_raw_detections,
)
from perception.detector import MockDetector
from perception.game_state_adapter import GameStateAdapter
from perception.geometry import NormalizedBox, bottom_edge_distance
from perception.image import ImageLoadError, ImagePreprocessor
from perception.lanes import LaneAssigner, LaneReason
from perception.manifest import ManifestError, SplitManifest
from perception.pipeline import PerceptionPipeline
from sensory.game_state import Lane, ObstacleType

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent

TRAIN = ClassDefinition(0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)
JUMP = ClassDefinition(
    1, "jump-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW
)
ROLL = ClassDefinition(
    2, "roll-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_HIGH
)
WALL = ClassDefinition(3, "wall", ClassRole.BOUNDARY, GameStateRole.UNSUPPORTED)
PLAYER = ClassDefinition(
    10, "player", ClassRole.PLAYER, GameStateRole.UNSUPPORTED
)
COIN = ClassDefinition(11, "coin", ClassRole.COIN, GameStateRole.UNSUPPORTED)

BASE_CLASSES = (TRAIN, JUMP, ROLL, WALL)


def make_config(
    classes=BASE_CLASSES,
    *,
    player_class_ids=(),
    coin_class_ids=(),
    preprocess=None,
    validation=None,
    lanes=None,
    distance=None,
) -> PerceptionConfig:
    return PerceptionConfig(
        preprocess=preprocess or PreprocessConfig(),
        validation=validation or ValidationConfig(),
        lanes=lanes or LaneConfig(),
        distance=distance or DistanceConfig(),
        schema=ClassSchema(
            classes=tuple(classes),
            player_class_ids=tuple(player_class_ids),
            coin_class_ids=tuple(coin_class_ids),
        ),
    )


def make_frame(width=300, height=600, preprocess=None, frame_id="synthetic"):
    image = Image.new("RGB", (width, height), (16, 24, 40))
    return ImagePreprocessor(preprocess or PreprocessConfig()).from_image(
        image, frame_id=frame_id
    )


def validate(raws, config=None, frame=None):
    config = config or make_config()
    frame = frame or make_frame()
    validator = DetectionValidator(config.validation, config.schema, frame)
    return validator.validate_many(raws)


def run(raws, config=None, frame=None):
    config = config or make_config()
    frame = frame or make_frame()
    pipeline = PerceptionPipeline(config, MockDetector(raws))
    return pipeline.run(frame)


# ---------------------------------------------------------------------------
# Image loading and preprocessing
# ---------------------------------------------------------------------------


def test_preprocess_crop_resize_and_coordinate_mapping() -> None:
    preprocess = PreprocessConfig(
        crop_left_fraction=0.1,
        crop_right_fraction=0.1,
        crop_top_fraction=0.2,
        resize=(100, 200),
    )
    frame = make_frame(200, 400, preprocess=preprocess)
    assert frame.original_size == (200, 400)
    assert frame.crop_box == (20, 80, 180, 400)
    assert frame.viewport_size == (160, 320)
    assert frame.processed_size == (100, 200)
    assert frame.scale_x == pytest.approx(0.625)
    assert frame.scale_y == pytest.approx(0.625)

    screen = frame.processed_box_to_screen(0, 0, 100, 200)
    assert screen.as_tuple() == pytest.approx((20, 80, 180, 400))
    normalized = frame.screen_box_to_normalized(screen)
    assert normalized.as_tuple() == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_preprocess_without_resize_keeps_viewport_pixels() -> None:
    frame = make_frame(320, 640, preprocess=PreprocessConfig())
    assert frame.processed_size == (320, 640)
    assert frame.scale_x == 1.0 and frame.scale_y == 1.0


def test_image_loading_rejects_missing_and_corrupt_files(tmp_path) -> None:
    preprocessor = ImagePreprocessor(PreprocessConfig())
    with pytest.raises(ImageLoadError):
        preprocessor.load(tmp_path / "missing.png")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(ImageLoadError):
        preprocessor.load(corrupt)


# ---------------------------------------------------------------------------
# Detection validation: boxes, confidence, classes
# ---------------------------------------------------------------------------


def test_valid_detection_gets_roles_and_both_coordinates() -> None:
    frame = make_frame()
    raw = RawDetection(0, 0.9, 100, 100, 200, 300, class_name="train")
    result = validate([raw], frame=frame)
    assert len(result.accepted) == 1 and not result.rejected
    detection = result.accepted[0]
    assert isinstance(detection, Detection)
    assert detection.class_name == "train"
    assert detection.role is ClassRole.TRAIN
    assert detection.game_state_role is GameStateRole.TRAIN
    assert detection.screen_box.as_tuple() == pytest.approx((100, 100, 200, 300))
    assert detection.normalized_box.as_tuple() == pytest.approx(
        (1 / 3, 1 / 6, 2 / 3, 0.5)
    )
    assert detection.center_screen == pytest.approx((150, 200))
    assert detection.size_pixels == pytest.approx((100, 200))


@pytest.mark.parametrize(
    "raw, reason",
    [
        (RawDetection(0, 0.9, 200, 100, 100, 300), RejectionReason.DEGENERATE_BOX),
        (RawDetection(0, 0.9, 100, 300, 200, 100), RejectionReason.DEGENERATE_BOX),
        (RawDetection(0, 0.9, float("nan"), 0, 10, 10), RejectionReason.INVALID_COORDINATES),
        (RawDetection(0, 0.9, 290, 0, 310, 20), RejectionReason.OUT_OF_BOUNDS),
        (RawDetection(0, 0.9, 0, 0, 0.5, 10), RejectionReason.BOX_TOO_SMALL),
        (RawDetection(0, 0.9, 0, 0, 1, 1), RejectionReason.BOX_TOO_SMALL),
    ],
)
def test_invalid_boxes_are_rejected_with_reasons(raw, reason) -> None:
    result = validate([raw])
    assert not result.accepted
    assert result.rejected[0].reason is reason


def test_confidence_threshold_is_inclusive() -> None:
    config = make_config(validation=ValidationConfig(confidence_threshold=0.25))
    result = validate(
        [
            RawDetection(0, 0.25, 10, 10, 60, 60),
            RawDetection(0, 0.2499, 10, 10, 60, 60),
        ],
        config=config,
    )
    assert len(result.accepted) == 1
    assert result.accepted[0].confidence == pytest.approx(0.25)
    assert result.rejected[0].reason is RejectionReason.LOW_CONFIDENCE


def test_confidence_outside_unit_interval_is_rejected() -> None:
    result = validate([RawDetection(0, 1.2, 10, 10, 60, 60)])
    assert result.rejected[0].reason is RejectionReason.INVALID_CONFIDENCE


def test_class_id_zero_is_valid_and_unknown_or_mismatched_classes_rejected() -> None:
    result = validate(
        [
            RawDetection(0, 0.9, 10, 10, 60, 60),
            RawDetection(99, 0.9, 10, 10, 60, 60),
            RawDetection(0, 0.9, 10, 10, 60, 60, class_name="jump-barrier"),
            RawDetection(True, 0.9, 10, 10, 60, 60),
        ]
    )
    assert len(result.accepted) == 1
    assert [item.reason for item in result.rejected] == [
        RejectionReason.UNKNOWN_CLASS,
        RejectionReason.CLASS_NAME_MISMATCH,
        RejectionReason.INVALID_CLASS_ID,
    ]


def test_malformed_record_is_rejected_not_ignored() -> None:
    raws, rejected = coerce_raw_detections(
        [
            {"class_id": 0, "confidence": 0.9, "bbox": [10, 10, 60, 60]},
            {"confidence": 0.9, "bbox": [10, 10, 60, 60]},
            "not a detection",
        ]
    )
    assert len(raws) == 1
    assert len(rejected) == 2
    assert all(item.reason is RejectionReason.INVALID_FORMAT for item in rejected)


def test_bounds_tolerance_clamps_explicitly() -> None:
    frame = make_frame()
    config = make_config(
        validation=ValidationConfig(bounds_tolerance_pixels=1.0)
    )
    result = validate(
        [RawDetection(0, 0.9, -0.5, 0, 50, 50)], config=config, frame=frame
    )
    detection = result.accepted[0]
    assert detection.clamped is True
    assert detection.normalized_box.x1 == 0.0


# ---------------------------------------------------------------------------
# Lane assignment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "box, lane",
    [
        (NormalizedBox(0.02, 0.2, 0.30, 0.8), 0),
        (NormalizedBox(0.40, 0.2, 0.60, 0.8), 1),
        (NormalizedBox(0.72, 0.2, 0.98, 0.8), 2),
    ],
)
def test_single_lane_assignment(box, lane) -> None:
    assignment = LaneAssigner(LaneConfig()).assign(box)
    assert assignment.lane == lane
    assert assignment.confident is True
    assert assignment.ambiguous is False
    assert assignment.reason is LaneReason.SINGLE_LANE


def test_majority_overlap_assigns_but_stays_ambiguous() -> None:
    assignment = LaneAssigner(LaneConfig()).assign(
        NormalizedBox(0.0, 0.2, 0.40, 0.8)
    )
    assert assignment.lane == 0
    assert assignment.confident is True
    assert assignment.ambiguous is True
    assert assignment.reason is LaneReason.MAJORITY_OVERLAP
    assert assignment.touched_lanes == (0, 1)


def test_straddling_box_is_left_unassigned() -> None:
    assignment = LaneAssigner(LaneConfig()).assign(
        NormalizedBox(0.55, 0.2, 0.80, 0.8)
    )
    assert assignment.lane is None
    assert assignment.confident is False
    assert assignment.ambiguous is True
    assert assignment.reason is LaneReason.STRADDLES_LANES


def test_narrow_boundary_box_is_not_forced_into_a_lane() -> None:
    assignment = LaneAssigner(LaneConfig()).assign(
        NormalizedBox(0.32, 0.2, 0.34, 0.8)
    )
    assert assignment.lane is None
    assert assignment.touched_lanes == (0, 1)
    assert assignment.reason is LaneReason.STRADDLES_LANES


def test_overlapping_objects_keep_separate_lane_assignments() -> None:
    result = run(
        [
            RawDetection(0, 0.9, 10, 100, 90, 400),
            RawDetection(1, 0.9, 20, 200, 80, 450),
        ]
    )
    scene = result.scene
    assert [obj.lane for obj in scene.objects] == [0, 0]
    assert scene.lane_occupancy[0].obstacle_count == 1
    assert scene.lane_occupancy[0].train_count == 1
    assert scene.lane_occupancy[0].occupied
    assert scene.uncertainty.unassigned_objects == 0


def test_ambiguous_object_is_counted_in_occupancy_and_uncertainty() -> None:
    result = run([RawDetection(0, 0.9, 0, 100, 120, 400)])
    scene = result.scene
    assert scene.objects[0].lane == 0
    assert scene.objects[0].lane_assignment.ambiguous is True
    assert scene.uncertainty.ambiguous_objects == 1
    assert scene.lane_occupancy[0].train_count == 1


# ---------------------------------------------------------------------------
# Missing modalities and empty results
# ---------------------------------------------------------------------------


def test_player_and_coin_modalities_unavailable_in_v15_schema() -> None:
    config = load_perception_config(PROJECT_ROOT / "configs" / "perception_config.yaml")
    result = run([RawDetection(11, 0.9, 100, 100, 200, 300)], config=config)
    scene = result.scene
    assert scene.modality.player_available is False
    assert scene.modality.player_status == "unavailable_in_schema"
    assert scene.modality.coins_available is False
    assert scene.modality.coin_status == "unavailable_in_schema"
    conversion = result.conversion
    assert conversion.player_known is False
    assert conversion.player_lane_known is False
    assert conversion.coins_available is False
    assert "player.lane" in conversion.estimated_fields
    assert conversion.state.coin is None


def test_player_class_supported_but_not_detected() -> None:
    config = make_config(
        classes=BASE_CLASSES + (PLAYER, COIN),
        player_class_ids=(PLAYER.class_id,),
        coin_class_ids=(COIN.class_id,),
    )
    result = run([RawDetection(0, 0.9, 100, 100, 200, 300)], config=config)
    assert result.scene.modality.player_status == "not_detected"
    assert result.scene.modality.coin_status == "not_detected"
    assert result.conversion.player_known is False
    assert result.conversion.state.coin is None


def test_detected_player_and_coin_are_converted() -> None:
    config = make_config(
        classes=BASE_CLASSES + (PLAYER, COIN),
        player_class_ids=(PLAYER.class_id,),
        coin_class_ids=(COIN.class_id,),
    )
    result = run(
        [
            RawDetection(10, 0.9, 120, 400, 180, 550),
            RawDetection(11, 0.9, 120, 300, 180, 350),
        ],
        config=config,
    )
    conversion = result.conversion
    assert conversion.player_known is True
    assert conversion.player_lane_known is True
    assert conversion.state.player.lane is Lane.CENTER
    assert conversion.coins_available is True
    assert conversion.state.coin is not None
    assert conversion.state.coin.lane is Lane.CENTER
    assert "player.speed" in conversion.estimated_fields


def test_multiple_players_do_not_produce_a_fabricated_identity() -> None:
    config = make_config(
        classes=BASE_CLASSES + (PLAYER,),
        player_class_ids=(PLAYER.class_id,),
    )
    result = run(
        [
            RawDetection(10, 0.9, 20, 400, 80, 550),
            RawDetection(10, 0.8, 220, 400, 280, 550),
        ],
        config=config,
    )
    assert result.scene.modality.player_status == "multiple_detections"
    assert result.scene.player is None
    assert result.conversion.player_known is False
    assert result.conversion.player_lane_known is False


def test_empty_detections_produce_an_empty_scene() -> None:
    result = run([])
    scene = result.scene
    assert scene.objects == ()
    assert scene.player is None
    assert scene.obstacles == () and scene.trains == () and scene.coins == ()
    assert all(not lane.occupied for lane in scene.lane_occupancy)
    assert scene.uncertainty.rejected_detections == 0
    assert result.conversion.state.obstacle is None
    assert result.conversion.state.train is None
    assert result.validation.n_received == 0


# ---------------------------------------------------------------------------
# GameState conversion
# ---------------------------------------------------------------------------


def test_nearest_obstacle_is_selected_and_others_are_recorded() -> None:
    result = run(
        [
            RawDetection(1, 0.9, 20, 100, 90, 200),   # left, far
            RawDetection(2, 0.9, 20, 400, 90, 500),   # left, near
            RawDetection(0, 0.9, 210, 100, 290, 300), # right, train
        ]
    )
    state = result.conversion.state
    assert state.obstacle is not None
    assert state.obstacle.present is True
    assert state.obstacle.lane is Lane.LEFT
    assert state.obstacle.obstacle_type is ObstacleType.HIGH
    assert state.obstacle.distance == pytest.approx(
        bottom_edge_distance(
            result.scene.obstacles[1].detection.normalized_box, 0.15
        ),
        abs=1e-6,
    )
    assert state.train is not None and state.train.lane is Lane.RIGHT
    reasons = {item.class_name: item.reason for item in result.conversion.unrepresented}
    assert "jump-barrier" in reasons
    assert "nearest" in reasons["jump-barrier"]
    assert "obstacle.distance" in result.conversion.estimated_fields


def test_unsupported_and_uncertain_objects_are_unrepresented() -> None:
    result = run(
        [
            RawDetection(3, 0.9, 10, 100, 90, 500),    # wall: unsupported
            RawDetection(0, 0.9, 110, 100, 250, 300),  # straddles lanes
        ]
    )
    state = result.conversion.state
    assert state.train is None
    reasons = [item.reason for item in result.conversion.unrepresented]
    assert any("no GameState representation" in reason for reason in reasons)
    assert any("lane assignment" in reason for reason in reasons)
    assert result.conversion.player_known is False
    assert result.conversion.state.player.speed == pytest.approx(0.5)
    assert "player.speed" in result.conversion.estimated_fields


def test_time_and_distance_mode_none_are_explicit() -> None:
    from dataclasses import replace

    frame = replace(make_frame(), frame_id="timed", timestamp_ms=1234.0)
    config = make_config(distance=DistanceConfig(mode="none"))
    result = run(
        [RawDetection(0, 0.9, 100, 100, 200, 300)], config=config, frame=frame
    )
    assert result.conversion.state.time_ms == pytest.approx(1234.0)
    assert result.conversion.state.train is None
    assert any(
        "distance mode is 'none'" in item.reason
        for item in result.conversion.unrepresented
    )


def test_bottom_edge_distance_convention() -> None:
    assert bottom_edge_distance(NormalizedBox(0, 0.5, 1, 1.0), 0.15) == 0.0
    assert bottom_edge_distance(NormalizedBox(0, 0.0, 1, 0.15), 0.15) == 1.0
    assert bottom_edge_distance(NormalizedBox(0, 0.0, 1, 0.05), 0.15) == 1.0


# ---------------------------------------------------------------------------
# Deterministic mock detector
# ---------------------------------------------------------------------------


def test_mock_detector_is_deterministic_and_pixel_independent() -> None:
    raws = [RawDetection(0, 0.9, 10, 10, 60, 60)]
    detector = MockDetector(raws)
    first = detector.detect(make_frame())
    second = detector.detect(make_frame(640, 480))
    assert first == second == raws
    description = detector.describe()
    assert description["test_only"] is True
    assert description["kind"] == "scripted_test_detector"
    assert "visual recognition" in json.dumps(description).lower()


def test_mock_detector_supports_frame_specific_records() -> None:
    detector = MockDetector(
        frame_detections={
            "a": [RawDetection(0, 0.9, 10, 10, 60, 60)],
            "b": [],
        }
    )
    assert len(detector.detect(make_frame(frame_id="a"))) == 1
    assert detector.detect(make_frame(frame_id="b")) == []
    assert detector.detect(make_frame(frame_id="unknown")) == []


# ---------------------------------------------------------------------------
# Curation manifest
# ---------------------------------------------------------------------------


def test_manifest_split_comes_from_group_not_folder() -> None:
    manifest = SplitManifest.load(PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json")
    path = (
        "datasets/external/subway surfers/roboflow_v15_yolov8/"
        "subway surfers object dataset.v15-added.yolov8/"
        "valid/images/subwayavitomp4_mp4-34_jpg.rf.abc.jpg"
    )
    assignment = manifest.resolve(path)
    assert assignment.group == "subwayavitomp4"
    assert assignment.split == "train"
    assert assignment.excluded is False


def test_manifest_reports_exclusions_and_refuses_unknown_groups() -> None:
    manifest = SplitManifest.load(PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json")
    excluded = manifest.resolve(
        "subwayedtied_mp4-293_jpg.rf.e8b37a118b7921ba1b7e4b6625a8b4ef.jpg"
    )
    assert excluded.excluded is True
    assert excluded.exclusion_reason == "probable_gap"
    with pytest.raises(ManifestError):
        manifest.resolve("not-a-curated-group_mp4-1_jpg.rf.abc.jpg")
    with pytest.raises(ManifestError):
        manifest.resolve("elsewhere/image.jpg")


def test_config_class_ids_and_names_match_v15_order() -> None:
    config = load_perception_config(PROJECT_ROOT / "configs" / "perception_config.yaml")
    expected = [
        "boots-powerup",
        "boxtrain",
        "jump-barrier",
        "jump-electric",
        "jump-hedge",
        "jump-roll-barrier",
        "jump-trash",
        "ledge",
        "pogstick-powerup",
        "ramp",
        "roll-barrier",
        "train",
        "undercover-barrier",
        "wall",
    ]
    assert [definition.name for definition in config.schema.classes] == expected
    assert [definition.class_id for definition in config.schema.classes] == list(
        range(14)
    )
    assert config.schema.supports_player is False
    assert config.schema.supports_coins is False


def test_pipeline_is_not_integrated_with_the_simulator() -> None:
    import perception

    source = (PROJECT_ROOT / "perception").glob("*.py")
    for path in source:
        text = path.read_text(encoding="utf-8")
        assert "brain.brain_simulator" not in text
        assert "brain_simulator" not in text
    assert perception is not None
