"""Tests for detector configuration, transforms, decoding and serialisation."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from experiments.phase_3b.evaluate_detector import _validate_detections
from perception.config import (
    ClassDefinition,
    ClassRole,
    ClassSchema,
    GameStateRole,
    PreprocessConfig,
    ValidationConfig,
    load_perception_config,
)
from perception.detection import (
    Detection,
    DetectionValidator,
    RawDetection,
    RejectionReason,
)
from perception.detector import MockDetector
from perception.detector_config import (
    DetectorConfig,
    DetectorConfigError,
    load_detector_config,
)
from perception.image import ImageFrame, ImagePreprocessor
from perception.inference import (
    DetectorOutputError,
    OnnxRuntimeDetector,
    batched_nms,
    box_iou,
    decode_boxes_scores,
    decode_nanodet_plus,
    decode_yolo_raw,
    fit_image,
    nms,
    prepare_input,
)
from perception.pipeline import PerceptionPipeline
from perception.serialization import detection_to_record

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOYED_MODEL = (
    PROJECT_ROOT
    / "models"
    / "YOLO11"
    / "deployment"
    / "yolo11n_v1_deployment"
    / "best.onnx"
)
DEPLOYED_SHA256 = "e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77"

SCHEMA = ClassSchema(
    classes=(
        ClassDefinition(0, "alpha", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW),
        ClassDefinition(1, "beta", ClassRole.TRAIN, GameStateRole.TRAIN),
    )
)


def _v15_config():
    return load_perception_config(PROJECT_ROOT / "configs" / "perception_config.yaml")


def _v15_schema() -> ClassSchema:
    return _v15_config().schema


def _frame(size: tuple[int, int] = (64, 64)) -> ImageFrame:
    return ImagePreprocessor(PreprocessConfig()).from_image(
        Image.new("RGB", size), frame_id="frame"
    )


class _FakeSession:
    def __init__(self, outputs):
        self.outputs = outputs
        self.feed = None

    def get_inputs(self):
        return [SimpleNamespace(name="images")]

    def run(self, names, feed):
        self.feed = feed
        return self.outputs


def _model_file(tmp_path: Path) -> Path:
    path = tmp_path / "model.onnx"
    path.write_bytes(b"not a real model")
    return path


def _yolo11_output(
    class_index: int,
    *,
    box: tuple[float, float, float, float] = (32.0, 32.0, 16.0, 8.0),
    score: float = 0.9,
    anchors: int = 8400,
) -> np.ndarray:
    """A [1, 18, 8400] tensor with one detection at anchor 0."""
    output = np.zeros((1, 4 + 14, anchors), dtype=np.float64)
    output[0, :4, 0] = box
    output[0, 4 + class_index, 0] = score
    return output


# ---------------------------------------------------------------------------
# Configuration contract
# ---------------------------------------------------------------------------


def test_deployed_config_matches_onnx_contract() -> None:
    config = load_detector_config(PROJECT_ROOT / "configs" / "detector_config.yaml")
    assert config.model_path == DEPLOYED_MODEL.resolve()
    assert config.model_sha256 == DEPLOYED_SHA256
    assert config.input_size == (640, 640)
    assert config.output_layout == "yolo_raw"
    assert config.has_objectness is False
    assert config.class_activation == "none"
    assert config.class_id_map == tuple(range(14))
    assert config.providers == ("CPUExecutionProvider",)
    assert 0.0 < config.confidence_threshold <= 1.0
    assert 0.0 < config.nms_iou_threshold <= 1.0


def test_relative_model_path_uses_repository_root() -> None:
    config = DetectorConfig(
        model_path="models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx"
    )
    assert config.model_path.is_absolute()
    assert config.model_path == DEPLOYED_MODEL.resolve()


def test_detector_requires_model_path() -> None:
    with pytest.raises(DetectorConfigError, match="no detector weights"):
        OnnxRuntimeDetector(DetectorConfig(), SCHEMA)


def test_detector_reports_missing_model_file(tmp_path: Path) -> None:
    config = DetectorConfig(model_path=tmp_path / "missing.onnx")
    with pytest.raises(DetectorConfigError, match="not found"):
        OnnxRuntimeDetector(config, SCHEMA)


def test_model_sha256_is_verified(tmp_path: Path) -> None:
    path = _model_file(tmp_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    session = _FakeSession(
        [np.array([[[32, 32, 16, 8, 0.9, 0.9, 0.1]]], dtype=np.float64)]
    )
    config = DetectorConfig(model_path=path, model_sha256=digest, has_objectness=True)
    detector = OnnxRuntimeDetector(
        config, SCHEMA, session_factory=lambda *_: session
    )
    assert detector.model_sha256 == digest

    wrong = DetectorConfig(
        model_path=path, model_sha256="0" * 64, has_objectness=True
    )
    with pytest.raises(DetectorConfigError, match="SHA-256 mismatch"):
        OnnxRuntimeDetector(wrong, SCHEMA, session_factory=lambda *_: session)


def test_missing_onnxruntime_is_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    config = DetectorConfig(model_path=_model_file(tmp_path))
    with pytest.raises(DetectorConfigError, match="onnxruntime is not installed"):
        OnnxRuntimeDetector(config, SCHEMA)


def test_invalid_config_rejected() -> None:
    with pytest.raises(DetectorConfigError, match="output_layout"):
        DetectorConfig(output_layout="magic")
    with pytest.raises(DetectorConfigError, match="model_sha256"):
        DetectorConfig(model_sha256="abc")


# ---------------------------------------------------------------------------
# Preprocessing and transforms
# ---------------------------------------------------------------------------


def test_letterbox_round_trip() -> None:
    image = Image.new("RGB", (606, 1050))
    fitted, transform = fit_image(image, (640, 640))
    assert fitted.size == (640, 640)
    box = (10.0, 20.0, 110.0, 220.0)
    back = transform.to_source(*transform.to_input(*box))
    assert back == pytest.approx(box)
    assert transform.pad_x > 0
    assert transform.pad_y == pytest.approx(0)


def test_prepare_input_shape_and_range() -> None:
    config = DetectorConfig(input_size=(32, 32))
    tensor, transform = prepare_input(_frame(), config)
    assert tensor.shape == (1, 3, 32, 32)
    assert tensor.dtype == np.float32
    assert 0.0 <= float(tensor.min()) and float(tensor.max()) <= 1.0
    assert transform.source_size == (64, 64)


# ---------------------------------------------------------------------------
# Decoding and NMS
# ---------------------------------------------------------------------------


def test_iou_and_nms() -> None:
    boxes = np.array(
        [[0, 0, 10, 10], [1, 1, 11, 11], [20, 20, 30, 30]], dtype=np.float64
    )
    scores = np.array([0.9, 0.8, 0.7])
    assert box_iou(boxes[0], boxes[1:])[0] == pytest.approx(81 / 119)
    assert nms(boxes, scores, 0.5).tolist() == [0, 2]
    assert batched_nms(boxes, scores, np.array([0, 0, 1]), 0.5).tolist() == [0, 2]
    # Class-aware: the overlapping boxes belong to different classes.
    assert batched_nms(
        boxes, scores, np.array([0, 1, 0]), 0.5
    ).tolist() == [0, 1, 2]


def test_decode_yolo11_transposed_no_objectness() -> None:
    config = DetectorConfig(
        input_size=(640, 640), has_objectness=False, class_activation="none"
    )
    output = _yolo11_output(13, box=(320.0, 320.0, 64.0, 32.0), score=0.9)
    assert output.shape == (1, 18, 8400)
    decoded = decode_yolo_raw(output, config, num_model_classes=14)
    assert decoded.boxes.shape == (8400, 4)
    assert decoded.class_indices[0] == 13
    assert decoded.scores[0] == pytest.approx(0.9)
    assert decoded.boxes[0].tolist() == pytest.approx([288, 304, 352, 336])
    assert int(np.argmax(decoded.scores)) == 0


def test_decode_yolo11_wrong_column_count_rejected() -> None:
    config = DetectorConfig(input_size=(640, 640), has_objectness=False)
    with pytest.raises(DetectorOutputError, match="columns"):
        decode_yolo_raw(np.zeros((1, 17, 8400)), config, num_model_classes=14)
    with pytest.raises(DetectorOutputError, match="columns"):
        decode_yolo_raw(np.zeros((1, 19, 8400)), config, num_model_classes=14)


def test_decode_yolo_raw_pixels_and_normalized() -> None:
    config = DetectorConfig(input_size=(64, 64), has_objectness=True)
    output = np.array([[32, 32, 16, 8, 0.9, 0.9, 0.1]], dtype=np.float64)
    decoded = decode_yolo_raw(output[None], config, num_model_classes=2)
    assert decoded.class_indices.tolist() == [0]
    assert decoded.scores[0] == pytest.approx(0.81)
    assert decoded.boxes[0].tolist() == pytest.approx([24, 28, 40, 36])

    normalized = DetectorConfig(
        input_size=(64, 64), has_objectness=False, box_format="normalized"
    )
    output = np.array([[0.5, 0.5, 0.25, 0.125, 0.1, 0.8]], dtype=np.float64)
    decoded = decode_yolo_raw(output, normalized, num_model_classes=2)
    assert decoded.class_indices.tolist() == [1]
    assert decoded.boxes[0].tolist() == pytest.approx([24, 28, 40, 36])


def test_decode_boxes_scores() -> None:
    output = np.array([[10, 20, 30, 40, 0.75, 3]], dtype=np.float64)
    decoded = decode_boxes_scores(output, input_size=(64, 64), box_format="pixels")
    assert decoded.boxes.tolist() == [[10, 20, 30, 40]]
    assert decoded.scores.tolist() == [0.75]
    assert decoded.class_indices.tolist() == [3]


def test_decode_nanodet_plus_synthetic() -> None:
    config = DetectorConfig(
        input_size=(32, 32),
        output_layout="nanodet_plus",
        nanodet_strides=(8, 16, 32),
        nanodet_reg_max=7,
        nanodet_num_priors=1,
    )
    outputs = []
    for stride in config.nanodet_strides:
        anchors = (32 // stride) ** 2
        class_logits = np.full((anchors, 2), -10.0)
        regression = np.zeros((anchors, 4 * 8))
        if stride == 8:
            class_logits[5, 1] = 10.0
            regression[5].reshape(4, 8)[:, 1] = 20.0
        outputs.extend([class_logits, regression])
    decoded = decode_nanodet_plus(outputs, config, num_model_classes=2)
    best = int(np.argmax(decoded.scores))
    assert decoded.class_indices[best] == 1
    assert decoded.scores[best] > 0.99
    assert decoded.boxes[best] == pytest.approx([-0.007, -0.007, 16.007, 16.007], abs=0.05)


def test_decode_rejects_bad_shapes() -> None:
    config = DetectorConfig(input_size=(32, 32), has_objectness=True)
    with pytest.raises(DetectorOutputError, match="columns"):
        decode_yolo_raw(np.zeros((5, 4)), config, num_model_classes=2)
    with pytest.raises(DetectorOutputError, match="non-finite"):
        decode_yolo_raw(np.full((1, 7), np.nan), config, num_model_classes=2)


# ---------------------------------------------------------------------------
# ONNX detector behaviour with a fake session
# ---------------------------------------------------------------------------


def test_detector_end_to_end_with_fake_session(tmp_path: Path) -> None:
    session = _FakeSession(
        [np.array([[[32, 32, 16, 8, 0.9, 0.9, 0.1]]], dtype=np.float64)]
    )
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        has_objectness=True,
        confidence_threshold=0.25,
        class_id_map=(0, 1),
    )
    detector = OnnxRuntimeDetector(config, SCHEMA, session_factory=lambda *_: session)
    detections = detector.detect(_frame())
    assert len(detections) == 1
    raw = detections[0]
    assert raw.class_id == 0
    assert (raw.x1, raw.y1, raw.x2, raw.y2) == pytest.approx((24, 28, 40, 36))
    assert session.feed["images"].shape == (1, 3, 64, 64)
    assert detector.last_detector_call_ms is not None
    assert detector.last_session_run_ms is not None
    assert detector.last_preprocess_ms is not None
    assert detector.last_postprocess_ms is not None
    assert detector.last_detector_call_ms >= detector.last_session_run_ms
    assert detector.last_detector_call_ms == detector.last_inference_ms
    description = detector.describe()
    assert description["weights_loaded"] is True
    assert description["trained_accuracy_reported"] is None
    assert "not pure ONNX inference time" in description["timing_scope"]


def test_detector_yolo11_contract_with_fake_session(tmp_path: Path) -> None:
    session = _FakeSession([_yolo11_output(11)])
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        has_objectness=False,
        class_activation="none",
        class_id_map=tuple(range(14)),
        confidence_threshold=0.25,
    )
    detector = OnnxRuntimeDetector(
        config, _v15_schema(), session_factory=lambda *_: session
    )
    detections = detector.detect(_frame())
    assert len(detections) == 1
    assert detections[0].class_id == 11
    assert detections[0].confidence == pytest.approx(0.9)
    assert (
        detections[0].x1,
        detections[0].y1,
        detections[0].x2,
        detections[0].y2,
    ) == pytest.approx((24, 28, 40, 36))
    description = detector.describe()
    assert description["num_model_classes"] == 14
    assert description["has_objectness"] is False
    assert description["class_id_map"] == list(range(14))


def test_detector_inverts_letterbox_on_non_square_frame(tmp_path: Path) -> None:
    session = _FakeSession([_yolo11_output(11)])
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        has_objectness=False,
        class_id_map=tuple(range(14)),
        confidence_threshold=0.25,
    )
    detector = OnnxRuntimeDetector(
        config, _v15_schema(), session_factory=lambda *_: session
    )
    detections = detector.detect(_frame((128, 64)))
    assert session.feed["images"].shape == (1, 3, 64, 64)
    assert len(detections) == 1
    assert (
        detections[0].x1,
        detections[0].y1,
        detections[0].x2,
        detections[0].y2,
    ) == pytest.approx((48, 24, 80, 40))


def test_detector_ignores_mapped_negative_class(tmp_path: Path) -> None:
    session = _FakeSession(
        [np.array([[[32, 32, 16, 8, 0.9, 0.1, 0.9]]], dtype=np.float64)]
    )
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        has_objectness=True,
        class_id_map=(0, -1),
    )
    detector = OnnxRuntimeDetector(config, SCHEMA, session_factory=lambda *_: session)
    assert detector.detect(_frame()) == []


# ---------------------------------------------------------------------------
# Pipeline injection and reporting
# ---------------------------------------------------------------------------


def test_pipeline_injects_onnx_detector(tmp_path: Path) -> None:
    session = _FakeSession([_yolo11_output(11)])
    detector_config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        has_objectness=False,
        class_id_map=tuple(range(14)),
        confidence_threshold=0.25,
    )
    detector = OnnxRuntimeDetector(
        detector_config, _v15_schema(), session_factory=lambda *_: session
    )
    pipeline = PerceptionPipeline(_v15_config(), detector)
    result = pipeline.run(_frame())
    assert len(result.validation.accepted) == 1
    assert result.validation.accepted[0].class_name == "train"
    assert result.validation.accepted[0].class_id == 11
    assert result.detector["weights_loaded"] is True
    assert result.detector["last_detector_call_ms"] is not None

    description = pipeline.describe()
    assert description["visual_recognition_available"] is True
    assert description["detector_test_only"] is False
    assert description["detector_name"] == "onnx-runtime-detector"


def test_pipeline_reports_mock_detector_unavailable() -> None:
    pipeline = PerceptionPipeline(_v15_config(), MockDetector([]))
    description = pipeline.describe()
    assert description["visual_recognition_available"] is False
    assert description["detector_test_only"] is True
    assert any(
        "No trained detector is active" in item
        for item in description["limitations"]
    )


# ---------------------------------------------------------------------------
# Evaluation consistency
# ---------------------------------------------------------------------------


def test_evaluation_validation_matches_pipeline() -> None:
    config = _v15_config()
    frame = _frame()
    raws = [
        RawDetection(11, 0.9, 24, 28, 40, 36),
        RawDetection(11, 0.9, -5, 28, 10, 36),
        RawDetection(11, 0.9, 24, 28, 24.5, 36),
        RawDetection(99, 0.9, 24, 28, 40, 36),
    ]
    accepted, rejected = _validate_detections(
        frame, raws, config.validation, config.schema, "test"
    )
    assert len(accepted) == 1
    assert {item.reason for item in rejected} == {
        RejectionReason.OUT_OF_BOUNDS,
        RejectionReason.BOX_TOO_SMALL,
        RejectionReason.UNKNOWN_CLASS,
    }

    pipeline = PerceptionPipeline(config, MockDetector(raws))
    result = pipeline.run(frame)

    def summary(items):
        return [
            (
                item.class_id,
                item.confidence,
                item.screen_box.as_tuple(),
                item.normalized_box.as_tuple(),
            )
            for item in items
        ]

    assert summary(accepted) == summary(result.validation.accepted)
    assert [item.reason for item in rejected] == [
        item.reason for item in result.validation.rejected
    ]


# ---------------------------------------------------------------------------
# Real-model smoke test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not DEPLOYED_MODEL.is_file(), reason="deployed ONNX artifact is not present"
)
def test_real_onnx_model_smoke() -> None:
    pytest.importorskip("onnxruntime")
    config = load_detector_config(PROJECT_ROOT / "configs" / "detector_config.yaml")
    detector = OnnxRuntimeDetector(config, _v15_schema())
    raws = detector.detect(_frame((320, 240)))
    assert isinstance(raws, list)
    for raw in raws:
        assert isinstance(raw, RawDetection)
        assert 0 <= raw.class_id < 14
        assert 0.0 <= raw.confidence <= 1.0
    assert detector.model_sha256 == DEPLOYED_SHA256
    assert detector.last_session_run_ms is not None
    assert detector.last_detector_call_ms is not None
    assert detector.last_detector_call_ms >= detector.last_session_run_ms


# ---------------------------------------------------------------------------
# Detection serialisation
# ---------------------------------------------------------------------------


def test_detection_serialisation_has_bbox_and_center() -> None:
    frame = _frame()
    validator = DetectionValidator(
        ValidationConfig(),
        SCHEMA,
        frame,
    )
    detection = validator.validate_one(
        RawDetection(class_id=1, confidence=0.8, x1=8, y1=8, x2=40, y2=48)
    )
    assert isinstance(detection, Detection)
    record = detection_to_record(detection)
    assert record["class_name"] == "beta"
    assert record["bbox"] == {"x1": 8.0, "y1": 8.0, "x2": 40.0, "y2": 48.0}
    assert record["center"] == {"x": 24.0, "y": 28.0}
