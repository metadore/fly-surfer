"""Tests for detector configuration, transforms, decoding and serialisation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from perception.config import (
    ClassDefinition,
    ClassRole,
    ClassSchema,
    GameStateRole,
    PreprocessConfig,
    ValidationConfig,
)
from perception.detection import Detection, DetectionValidator, RawDetection
from perception.detector_config import DetectorConfig, DetectorConfigError, load_detector_config
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
from perception.serialization import detection_to_record

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA = ClassSchema(
    classes=(
        ClassDefinition(0, "alpha", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW),
        ClassDefinition(1, "beta", ClassRole.TRAIN, GameStateRole.TRAIN),
    )
)


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


def test_default_config_loads_without_weights() -> None:
    config = load_detector_config(PROJECT_ROOT / "configs" / "detector_config.yaml")
    assert config.model_path is None
    assert config.input_size == (416, 416)
    assert config.output_layout == "yolo_raw"
    assert config.providers == ("CPUExecutionProvider",)
    with pytest.raises(DetectorConfigError, match="no detector weights"):
        OnnxRuntimeDetector(config, SCHEMA)


def test_invalid_config_rejected() -> None:
    with pytest.raises(DetectorConfigError, match="output_layout"):
        DetectorConfig(output_layout="magic")
    with pytest.raises(DetectorConfigError, match="model_sha256"):
        DetectorConfig(model_sha256="abc")


def test_letterbox_round_trip() -> None:
    image = Image.new("RGB", (606, 1050))
    fitted, transform = fit_image(image, (416, 416))
    assert fitted.size == (416, 416)
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


def test_iou_and_nms() -> None:
    boxes = np.array(
        [[0, 0, 10, 10], [1, 1, 11, 11], [20, 20, 30, 30]], dtype=np.float64
    )
    scores = np.array([0.9, 0.8, 0.7])
    assert box_iou(boxes[0], boxes[1:])[0] == pytest.approx(81 / 119)
    assert nms(boxes, scores, 0.5).tolist() == [0, 2]
    assert batched_nms(boxes, scores, np.array([0, 0, 1]), 0.5).tolist() == [0, 2]


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


def test_detector_end_to_end_with_fake_session(tmp_path: Path) -> None:
    session = _FakeSession(
        [np.array([[[32, 32, 16, 8, 0.9, 0.9, 0.1]]], dtype=np.float64)]
    )
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
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
    assert detector.last_inference_ms is not None
    description = detector.describe()
    assert description["weights_loaded"] is True
    assert description["trained_accuracy_reported"] is None


def test_detector_ignores_mapped_negative_class(tmp_path: Path) -> None:
    session = _FakeSession(
        [np.array([[[32, 32, 16, 8, 0.9, 0.1, 0.9]]], dtype=np.float64)]
    )
    config = DetectorConfig(
        model_path=_model_file(tmp_path),
        input_size=(64, 64),
        class_id_map=(0, -1),
    )
    detector = OnnxRuntimeDetector(config, SCHEMA, session_factory=lambda *_: session)
    assert detector.detect(_frame()) == []


def test_detection_serialisation_has_bbox_and_center() -> None:
    from perception.detection import Detection, DetectionValidator, RawDetection

    frame = _frame()
    validator = DetectionValidator(
        __import__("perception.config", fromlist=["ValidationConfig"]).ValidationConfig(),
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
