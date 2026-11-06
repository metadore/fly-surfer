"""Model-agnostic detector inference: letterbox, decoding, NMS, ONNX Runtime.

Everything here is model-specific and stays below the ``Detector`` protocol.
Outputs are untrusted ``RawDetection`` records in processed-image pixels; the
existing validator, lane assigner and scene builder still apply. Nothing is
clamped here, and a malformed model output raises instead of being repaired.

No model artifact is bundled or downloaded. Without an approved local weight
file, constructing the detector fails with an explicit error.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image

from perception.config import ClassSchema
from perception.detection import RawDetection
from perception.detector_config import DetectorConfig, DetectorConfigError
from perception.image import ImageFrame


class DetectorOutputError(RuntimeError):
    """Raised when a model returns an output with an unexpected shape or value."""


@dataclass(frozen=True)
class LetterboxTransform:
    """Mapping between source pixels and the model's padded input pixels."""

    source_size: tuple[int, int]
    input_size: tuple[int, int]
    scale_x: float
    scale_y: float
    pad_x: float
    pad_y: float

    def __post_init__(self) -> None:
        for name in ("scale_x", "scale_y"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("pad_x", "pad_y"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")

    def to_source(self, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float]:
        return (
            (float(x1) - self.pad_x) / self.scale_x,
            (float(y1) - self.pad_y) / self.scale_y,
            (float(x2) - self.pad_x) / self.scale_x,
            (float(y2) - self.pad_y) / self.scale_y,
        )

    def to_input(self, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float]:
        return (
            float(x1) * self.scale_x + self.pad_x,
            float(y1) * self.scale_y + self.pad_y,
            float(x2) * self.scale_x + self.pad_x,
            float(y2) * self.scale_y + self.pad_y,
        )

    def as_dict(self) -> dict:
        return {
            "source_size": list(self.source_size),
            "input_size": list(self.input_size),
            "scale": [self.scale_x, self.scale_y],
            "pad": [self.pad_x, self.pad_y],
        }


def fit_image(
    image: Image.Image,
    input_size: tuple[int, int],
    *,
    resize_mode: str = "letterbox",
    pad_value: int = 114,
) -> tuple[Image.Image, LetterboxTransform]:
    """Resize with an explicit inverse transform; never crop."""
    if not isinstance(image, Image.Image):
        raise ValueError("image must be a PIL image")
    input_width, input_height = input_size
    source_width, source_height = image.size
    if resize_mode == "stretch":
        resized = image.resize((input_width, input_height), Image.Resampling.BILINEAR)
        transform = LetterboxTransform(
            source_size=(source_width, source_height),
            input_size=(input_width, input_height),
            scale_x=input_width / source_width,
            scale_y=input_height / source_height,
            pad_x=0.0,
            pad_y=0.0,
        )
        return resized, transform

    scale = min(input_width / source_width, input_height / source_height)
    new_width = max(1, min(input_width, int(round(source_width * scale))))
    new_height = max(1, min(input_height, int(round(source_height * scale))))
    resized = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
    left = (input_width - new_width) // 2
    top = (input_height - new_height) // 2
    canvas = Image.new(image.mode, (input_width, input_height), color=pad_value)
    canvas.paste(resized, (left, top))
    return canvas, LetterboxTransform(
        source_size=(source_width, source_height),
        input_size=(input_width, input_height),
        scale_x=new_width / source_width,
        scale_y=new_height / source_height,
        pad_x=float(left),
        pad_y=float(top),
    )


def prepare_input(
    frame: ImageFrame,
    config: DetectorConfig,
) -> tuple[np.ndarray, LetterboxTransform]:
    """Build an NCHW float32 tensor in [0, 1] and its inverse transform."""
    if not isinstance(frame, ImageFrame):
        raise ValueError("frame must be an ImageFrame")
    image = frame.pixels
    if image.mode != "RGB":
        image = image.convert("RGB")
    fitted, transform = fit_image(
        image,
        config.input_size,
        resize_mode=config.resize_mode,
        pad_value=config.pad_value,
    )
    array = np.asarray(fitted, dtype=np.float32) / 255.0
    if config.color_order == "bgr":
        array = array[..., ::-1]
    tensor = np.ascontiguousarray(array.transpose(2, 0, 1)[None, ...])
    return tensor, transform


def box_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    """IoU of one xyxy box against an (N, 4) array."""
    boxes = np.asarray(boxes, dtype=np.float64)
    if boxes.size == 0:
        return np.zeros(0, dtype=np.float64)
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    intersection = np.clip(x2 - x1, 0.0, None) * np.clip(y2 - y1, 0.0, None)
    area_a = max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))
    area_b = np.clip(boxes[:, 2] - boxes[:, 0], 0.0, None) * np.clip(
        boxes[:, 3] - boxes[:, 1], 0.0, None
    )
    union = area_a + area_b - intersection
    return np.where(union > 0.0, intersection / union, 0.0)


def nms(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float,
    *,
    max_detections: int | None = None,
) -> np.ndarray:
    """Greedy non-maximum suppression with deterministic tie-breaking."""
    boxes = np.asarray(boxes, dtype=np.float64)
    scores = np.asarray(scores, dtype=np.float64)
    if boxes.ndim != 2 or boxes.shape[1] != 4:
        raise ValueError("boxes must have shape (N, 4)")
    if scores.shape != (boxes.shape[0],):
        raise ValueError("scores must have shape (N,)")
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be in [0, 1]")
    if boxes.shape[0] == 0:
        return np.zeros(0, dtype=np.int64)
    order = np.lexsort((np.arange(scores.size), -scores))
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if max_detections is not None and len(keep) >= max_detections:
            break
        rest = order[1:]
        overlaps = box_iou(boxes[current], boxes[rest])
        order = rest[overlaps <= iou_threshold]
    return np.asarray(keep, dtype=np.int64)


def batched_nms(
    boxes: np.ndarray,
    scores: np.ndarray,
    class_ids: np.ndarray,
    iou_threshold: float,
    *,
    max_detections: int | None = None,
) -> np.ndarray:
    """Per-class NMS, then a global score cap."""
    boxes = np.asarray(boxes, dtype=np.float64)
    scores = np.asarray(scores, dtype=np.float64)
    class_ids = np.asarray(class_ids, dtype=np.int64)
    if boxes.shape[0] != scores.shape[0] or scores.shape != class_ids.shape:
        raise ValueError("boxes, scores and class_ids must share their length")
    kept: list[int] = []
    for class_id in sorted(set(int(value) for value in class_ids)):
        indices = np.flatnonzero(class_ids == class_id)
        local = nms(boxes[indices], scores[indices], iou_threshold)
        kept.extend(int(indices[index]) for index in local)
    if not kept:
        return np.zeros(0, dtype=np.int64)
    kept_array = np.asarray(kept, dtype=np.int64)
    order = np.lexsort((kept_array, -scores[kept_array]))
    kept_array = kept_array[order]
    if max_detections is not None:
        kept_array = kept_array[:max_detections]
    return kept_array


def _squeeze_predictions(values: Any, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2:
        raise DetectorOutputError(
            f"{name} must be a 2-D tensor after removing the batch axis, "
            f"got shape {array.shape}"
        )
    if not np.isfinite(array).all():
        raise DetectorOutputError(f"{name} contains non-finite values")
    return array


def _columns(array: np.ndarray, expected: int, name: str) -> np.ndarray:
    """Return an (N, expected) view, transposing a single batch output."""
    if array.shape[1] == expected:
        return array
    if array.shape[0] == expected:
        return array.T
    raise DetectorOutputError(
        f"{name} has shape {array.shape}; expected {expected} columns"
    )


@dataclass(frozen=True)
class DecodedBoxes:
    """Decoded boxes in input-image pixels with class indices and scores."""

    boxes: np.ndarray
    scores: np.ndarray
    class_indices: np.ndarray

    def __post_init__(self) -> None:
        if self.boxes.ndim != 2 or self.boxes.shape[1] != 4:
            raise ValueError("boxes must have shape (N, 4)")
        if self.scores.shape != (self.boxes.shape[0],):
            raise ValueError("scores must have shape (N,)")
        if self.class_indices.shape != (self.boxes.shape[0],):
            raise ValueError("class_indices must have shape (N,)")


def _empty_decoded() -> DecodedBoxes:
    return DecodedBoxes(
        boxes=np.zeros((0, 4), dtype=np.float64),
        scores=np.zeros(0, dtype=np.float64),
        class_indices=np.zeros(0, dtype=np.int64),
    )


def decode_yolo_raw(
    output: Any,
    config: DetectorConfig,
    *,
    num_model_classes: int,
) -> DecodedBoxes:
    """Decode a single anchor tensor of ``[cx, cy, w, h, obj?, classes...]``."""
    array = _squeeze_predictions(output, name="yolo_raw output")
    class_offset = 5 if config.has_objectness else 4
    expected = class_offset + num_model_classes
    array = _columns(array, expected, "yolo_raw output")
    if array.shape[0] == 0:
        return _empty_decoded()
    boxes = array[:, :4]
    if config.box_format == "normalized":
        boxes = boxes * np.asarray(
            [config.input_size[0], config.input_size[1]] * 2, dtype=np.float64
        )
    objectness = array[:, 4] if config.has_objectness else np.ones(array.shape[0])
    class_scores = array[:, class_offset:]
    class_indices = np.argmax(class_scores, axis=1)
    best_scores = class_scores[np.arange(class_scores.shape[0]), class_indices]
    scores = objectness * best_scores
    center_x, center_y, width, height = (
        boxes[:, 0],
        boxes[:, 1],
        boxes[:, 2],
        boxes[:, 3],
    )
    xyxy = np.stack(
        [
            center_x - width / 2.0,
            center_y - height / 2.0,
            center_x + width / 2.0,
            center_y + height / 2.0,
        ],
        axis=1,
    )
    return DecodedBoxes(
        boxes=xyxy.astype(np.float64),
        scores=scores.astype(np.float64),
        class_indices=class_indices.astype(np.int64),
    )


def decode_boxes_scores(
    output: Any,
    *,
    input_size: tuple[int, int],
    box_format: str,
) -> DecodedBoxes:
    """Decode ``[x1, y1, x2, y2, score, class_id]`` predictions."""
    array = _squeeze_predictions(output, name="boxes_scores output")
    array = _columns(array, 6, "boxes_scores output")
    if array.shape[0] == 0:
        return _empty_decoded()
    boxes = array[:, :4]
    if box_format == "normalized":
        boxes = boxes * np.asarray(
            [input_size[0], input_size[1]] * 2, dtype=np.float64
        )
    class_values = array[:, 5]
    rounded = np.rint(class_values)
    if not np.allclose(class_values, rounded, atol=1e-6):
        raise DetectorOutputError("boxes_scores class ids must be integers")
    return DecodedBoxes(
        boxes=boxes.astype(np.float64),
        scores=array[:, 4].astype(np.float64),
        class_indices=rounded.astype(np.int64),
    )


def _softmax(values: np.ndarray, axis: int) -> np.ndarray:
    shifted = values - values.max(axis=axis, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=axis, keepdims=True)


def decode_nanodet_plus(
    outputs: Sequence[Any],
    config: DetectorConfig,
    *,
    num_model_classes: int,
) -> DecodedBoxes:
    """Decode per-stride NanoDet-Plus class and regression tensors.

    The regression head is assumed to use distribution focal loss with
    ``reg_max`` bins and distances ordered left, top, right, bottom, in stride
    units. The output order and tensor orientation are configurable. This
    decoder is unit tested on synthetic tensors; it has not been verified
    against real NanoDet-Plus weights in this environment.
    """
    strides = config.nanodet_strides
    if not isinstance(outputs, (list, tuple)) or len(outputs) != 2 * len(strides):
        length = len(outputs) if isinstance(outputs, (list, tuple)) else "non-sequence"
        raise DetectorOutputError(
            f"nanodet_plus expects {2 * len(strides)} outputs, got {length}"
        )
    input_width, input_height = config.input_size
    bins = config.nanodet_reg_max + 1
    all_boxes: list[np.ndarray] = []
    all_scores: list[np.ndarray] = []
    all_classes: list[np.ndarray] = []
    for stride_index, stride in enumerate(strides):
        first = _squeeze_predictions(
            outputs[2 * stride_index], name=f"stride {stride} first output"
        )
        second = _squeeze_predictions(
            outputs[2 * stride_index + 1], name=f"stride {stride} second output"
        )
        reg_columns = 4 * bins
        if config.nanodet_output_order == "cls_reg":
            class_array, regression = first, second
        else:
            regression, class_array = first, second
        if regression.shape[1] != reg_columns and regression.shape[0] == reg_columns:
            regression = regression.T
        if regression.shape[1] != reg_columns:
            raise DetectorOutputError(
                f"stride {stride} regression output has shape {regression.shape}; "
                f"expected {reg_columns} columns"
            )
        if class_array.shape[1] != num_model_classes and class_array.shape[0] == num_model_classes:
            class_array = class_array.T
        if class_array.shape[1] != num_model_classes:
            raise DetectorOutputError(
                f"stride {stride} class output has shape {class_array.shape}; "
                f"expected {num_model_classes} columns"
            )
        expected_anchors = (
            (input_width // stride) * (input_height // stride) * config.nanodet_num_priors
        )
        if class_array.shape[0] != expected_anchors or regression.shape[0] != expected_anchors:
            raise DetectorOutputError(
                f"stride {stride} produces {class_array.shape[0]} class rows and "
                f"{regression.shape[0]} regression rows; expected {expected_anchors}"
            )
        if config.class_activation == "sigmoid":
            probabilities = 1.0 / (1.0 + np.exp(-class_array))
        elif config.class_activation == "softmax":
            probabilities = _softmax(class_array, axis=1)
        else:
            probabilities = class_array
        if not np.isfinite(probabilities).all() or (
            probabilities < 0.0
        ).any() or (probabilities > 1.0).any():
            raise DetectorOutputError(
                "class probabilities must be finite and in [0, 1]"
            )
        distances = _softmax(
            regression.reshape(expected_anchors, 4, bins), axis=2
        ) @ np.arange(bins, dtype=np.float64)
        grid_width = input_width // stride
        grid_height = input_height // stride
        grid_y, grid_x = np.meshgrid(
            np.arange(grid_height), np.arange(grid_width), indexing="ij"
        )
        centers_x = np.repeat(grid_x.reshape(-1), config.nanodet_num_priors)
        centers_y = np.repeat(grid_y.reshape(-1), config.nanodet_num_priors)
        left, top, right, bottom = (distances[:, index] for index in range(4))
        boxes = np.stack(
            [
                (centers_x - left) * stride,
                (centers_y - top) * stride,
                (centers_x + right) * stride,
                (centers_y + bottom) * stride,
            ],
            axis=1,
        )
        class_indices = np.argmax(probabilities, axis=1)
        scores = probabilities[np.arange(probabilities.shape[0]), class_indices]
        all_boxes.append(boxes)
        all_scores.append(scores)
        all_classes.append(class_indices)
    if not all_boxes:
        return _empty_decoded()
    return DecodedBoxes(
        boxes=np.concatenate(all_boxes, axis=0),
        scores=np.concatenate(all_scores, axis=0),
        class_indices=np.concatenate(all_classes, axis=0).astype(np.int64),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


SessionFactory = Callable[[Path, DetectorConfig], Any]


class OnnxRuntimeDetector:
    """Local ONNX Runtime detector implementing the ``Detector`` protocol."""

    def __init__(
        self,
        config: DetectorConfig,
        schema: ClassSchema,
        *,
        session_factory: SessionFactory | None = None,
    ) -> None:
        if not isinstance(config, DetectorConfig):
            raise ValueError("config must be a DetectorConfig")
        if not isinstance(schema, ClassSchema):
            raise ValueError("schema must be a ClassSchema")
        if config.model_path is None:
            raise DetectorConfigError(
                "no detector weights are configured; set detector.model_path to "
                "an approved local artifact (nothing is downloaded automatically)"
            )
        path = Path(config.model_path)
        if not path.is_file():
            raise DetectorConfigError(f"detector model not found: {path}")
        actual_digest = _sha256(path)
        if config.model_sha256 is not None and actual_digest != config.model_sha256:
            raise DetectorConfigError(
                f"model SHA-256 mismatch: expected {config.model_sha256}, "
                f"got {actual_digest}"
            )
        if session_factory is None:
            try:
                import onnxruntime
            except ImportError as exc:
                raise DetectorConfigError(
                    "onnxruntime is not installed; no package was installed by "
                    "this phase"
                ) from exc
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = config.intra_op_threads
            session = onnxruntime.InferenceSession(
                str(path),
                sess_options=options,
                providers=list(config.providers),
            )
        else:
            session = session_factory(path, config)
        inputs = session.get_inputs()
        if not inputs:
            raise DetectorConfigError("the ONNX model declares no inputs")
        self.config = config
        self.schema = schema
        self.model_path = path
        self.model_sha256 = actual_digest
        self.session = session
        self._input_name = inputs[0].name
        self.last_inference_ms: float | None = None
        self.last_decoded_count = 0
        self.model_classes = (
            len(config.class_id_map) if config.class_id_map else len(schema.classes)
        )

    def _decode(self, outputs: Sequence[Any]) -> DecodedBoxes:
        if self.config.output_layout == "yolo_raw":
            if len(outputs) != 1:
                raise DetectorOutputError(
                    f"yolo_raw expects one output, got {len(outputs)}"
                )
            return decode_yolo_raw(
                outputs[0],
                self.config,
                num_model_classes=self.model_classes,
            )
        if self.config.output_layout == "boxes_scores":
            if len(outputs) != 1:
                raise DetectorOutputError(
                    f"boxes_scores expects one output, got {len(outputs)}"
                )
            return decode_boxes_scores(
                outputs[0],
                input_size=self.config.input_size,
                box_format=self.config.box_format,
            )
        return decode_nanodet_plus(
            outputs, self.config, num_model_classes=self.model_classes
        )

    def detect(self, frame: ImageFrame) -> list[RawDetection]:
        started = time.perf_counter()
        tensor, transform = prepare_input(frame, self.config)
        outputs = self.session.run(None, {self._input_name: tensor})
        if not isinstance(outputs, (list, tuple)):
            outputs = [outputs]
        decoded = self._decode(outputs)
        threshold = self.config.confidence_threshold
        mask = decoded.scores >= threshold
        boxes = decoded.boxes[mask]
        scores = decoded.scores[mask]
        class_indices = decoded.class_indices[mask]
        keep = batched_nms(
            boxes,
            scores,
            class_indices,
            self.config.nms_iou_threshold,
            max_detections=self.config.max_detections,
        )
        detections: list[RawDetection] = []
        for index in keep:
            mapped = self.config.mapped_class_id(int(class_indices[index]))
            if mapped is None:
                continue
            x1, y1, x2, y2 = transform.to_source(*boxes[index])
            detections.append(
                RawDetection(
                    class_id=mapped,
                    confidence=float(scores[index]),
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                )
            )
        self.last_inference_ms = (time.perf_counter() - started) * 1000.0
        self.last_decoded_count = int(boxes.shape[0])
        return detections

    def describe(self) -> dict:
        return {
            "name": "onnx-runtime-detector",
            "kind": "local_onnx_detector",
            "test_only": False,
            "produces": "untrusted RawDetection records in processed-image pixels",
            "model_path": str(self.model_path),
            "model_sha256": self.model_sha256,
            "weights_loaded": True,
            "weights_trained_in_repository": False,
            "trained_accuracy_reported": None,
            "input_size": list(self.config.input_size),
            "resize_mode": self.config.resize_mode,
            "output_layout": self.config.output_layout,
            "providers": list(self.config.providers),
            "class_names": [definition.name for definition in self.schema.classes],
            "class_id_map": list(self.config.class_id_map) or "identity",
            "confidence_threshold": self.config.confidence_threshold,
            "nms_iou_threshold": self.config.nms_iou_threshold,
            "last_inference_ms": self.last_inference_ms,
            "notes": [
                "No model weights are part of this repository.",
                "Predictions are visual estimates and are validated downstream.",
                "The detector is not connected to the connectome or plasticity.",
            ],
        }
