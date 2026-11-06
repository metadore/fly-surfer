"""Configuration for the model-specific detector backend.

The model is never downloaded automatically. ``model_path`` may be null, in
which case constructing the detector raises an explicit error; the rest of the
perception layer remains usable with scripted detections.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class DetectorConfigError(ValueError):
    """Raised when detector configuration or a model artifact is unusable."""


def _fraction(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectorConfigError(f"{name} must be a number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise DetectorConfigError(f"{name} must be finite and in [0, 1]")
    return number


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DetectorConfigError(f"{name} must be a positive integer")
    return int(value)


def _pair(value: Any, name: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise DetectorConfigError(f"{name} must be a pair")
    return (
        _positive_int(value[0], f"{name}[0]"),
        _positive_int(value[1], f"{name}[1]"),
    )


@dataclass(frozen=True)
class DetectorConfig:
    """Validated settings for one local detector artifact."""

    model_path: Path | None = None
    model_sha256: str | None = None
    input_size: tuple[int, int] = (416, 416)
    resize_mode: str = "letterbox"
    pad_value: int = 114
    color_order: str = "rgb"
    output_layout: str = "yolo_raw"
    has_objectness: bool = True
    box_format: str = "pixels"
    class_activation: str = "sigmoid"
    nanodet_strides: tuple[int, ...] = (8, 16, 32)
    nanodet_reg_max: int = 7
    nanodet_num_priors: int = 1
    nanodet_output_order: str = "cls_reg"
    confidence_threshold: float = 0.25
    nms_iou_threshold: float = 0.45
    max_detections: int = 300
    class_id_map: tuple[int, ...] = ()
    providers: tuple[str, ...] = ("CPUExecutionProvider",)
    intra_op_threads: int = 1

    def __post_init__(self) -> None:
        if self.model_path is not None:
            object.__setattr__(self, "model_path", Path(self.model_path))
        if self.model_sha256 is not None:
            digest = str(self.model_sha256).lower()
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise DetectorConfigError("model_sha256 must be 64 hex characters")
            object.__setattr__(self, "model_sha256", digest)
        object.__setattr__(self, "input_size", _pair(self.input_size, "input_size"))
        if self.resize_mode not in ("letterbox", "stretch"):
            raise DetectorConfigError("resize_mode must be 'letterbox' or 'stretch'")
        if isinstance(self.pad_value, bool) or not isinstance(self.pad_value, int):
            raise DetectorConfigError("pad_value must be an integer")
        if not 0 <= self.pad_value <= 255:
            raise DetectorConfigError("pad_value must be in [0, 255]")
        if self.color_order not in ("rgb", "bgr"):
            raise DetectorConfigError("color_order must be 'rgb' or 'bgr'")
        if self.output_layout not in ("yolo_raw", "boxes_scores", "nanodet_plus"):
            raise DetectorConfigError(
                "output_layout must be 'yolo_raw', 'boxes_scores' or "
                "'nanodet_plus'"
            )
        if self.box_format not in ("pixels", "normalized"):
            raise DetectorConfigError("box_format must be 'pixels' or 'normalized'")
        if self.class_activation not in ("sigmoid", "softmax", "none"):
            raise DetectorConfigError(
                "class_activation must be 'sigmoid', 'softmax' or 'none'"
            )
        strides = tuple(
            _positive_int(value, "nanodet stride") for value in self.nanodet_strides
        )
        if not strides:
            raise DetectorConfigError("nanodet_strides must not be empty")
        object.__setattr__(self, "nanodet_strides", strides)
        object.__setattr__(
            self, "nanodet_reg_max", _positive_int(self.nanodet_reg_max, "reg_max")
        )
        object.__setattr__(
            self,
            "nanodet_num_priors",
            _positive_int(self.nanodet_num_priors, "num_priors"),
        )
        if self.nanodet_output_order not in ("cls_reg", "reg_cls"):
            raise DetectorConfigError(
                "nanodet_output_order must be 'cls_reg' or 'reg_cls'"
            )
        object.__setattr__(
            self,
            "confidence_threshold",
            _fraction(self.confidence_threshold, "confidence_threshold"),
        )
        object.__setattr__(
            self,
            "nms_iou_threshold",
            _fraction(self.nms_iou_threshold, "nms_iou_threshold"),
        )
        object.__setattr__(
            self,
            "max_detections",
            _positive_int(self.max_detections, "max_detections"),
        )
        class_map = tuple(int(value) for value in self.class_id_map)
        if any(value < -1 for value in class_map):
            raise DetectorConfigError(
                "class_id_map entries must be class ids or -1 to ignore"
            )
        object.__setattr__(self, "class_id_map", class_map)
        providers = tuple(str(value) for value in self.providers)
        if not providers:
            raise DetectorConfigError("providers must not be empty")
        object.__setattr__(self, "providers", providers)
        object.__setattr__(
            self,
            "intra_op_threads",
            _positive_int(self.intra_op_threads, "intra_op_threads"),
        )

    def mapped_class_id(self, model_index: int) -> int | None:
        """Map a model output index to a schema class id; None means ignore."""
        if not self.class_id_map:
            return int(model_index)
        if not 0 <= model_index < len(self.class_id_map):
            raise DetectorConfigError(
                f"model class index {model_index} is outside class_id_map "
                f"(length {len(self.class_id_map)})"
            )
        value = self.class_id_map[model_index]
        return None if value < 0 else value

    def as_dict(self) -> dict:
        return {
            "model_path": str(self.model_path) if self.model_path else None,
            "model_sha256": self.model_sha256,
            "input_size": list(self.input_size),
            "resize_mode": self.resize_mode,
            "pad_value": self.pad_value,
            "color_order": self.color_order,
            "output_layout": self.output_layout,
            "has_objectness": self.has_objectness,
            "box_format": self.box_format,
            "class_activation": self.class_activation,
            "nanodet_strides": list(self.nanodet_strides),
            "nanodet_reg_max": self.nanodet_reg_max,
            "nanodet_num_priors": self.nanodet_num_priors,
            "nanodet_output_order": self.nanodet_output_order,
            "confidence_threshold": self.confidence_threshold,
            "nms_iou_threshold": self.nms_iou_threshold,
            "max_detections": self.max_detections,
            "class_id_map": list(self.class_id_map),
            "providers": list(self.providers),
            "intra_op_threads": self.intra_op_threads,
        }


def _require_mapping(payload: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise DetectorConfigError(f"{name} must be a mapping")
    return payload


def load_detector_config(path: str | Path) -> DetectorConfig:
    path = Path(path)
    if not path.is_file():
        raise DetectorConfigError(f"detector config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload = _require_mapping(payload, "detector config")
    detector = _require_mapping(payload.get("detector"), "detector")
    output = _require_mapping(detector.get("output", {}), "detector.output")
    nanodet = _require_mapping(output.get("nanodet", {}), "output.nanodet")
    decoding = _require_mapping(detector.get("decoding", {}), "detector.decoding")
    runtime = _require_mapping(detector.get("runtime", {}), "detector.runtime")
    model_path = detector.get("model_path")
    return DetectorConfig(
        model_path=Path(model_path) if model_path else None,
        model_sha256=detector.get("model_sha256"),
        input_size=detector.get("input_size", (416, 416)),
        resize_mode=str(detector.get("resize_mode", "letterbox")),
        pad_value=int(detector.get("pad_value", 114)),
        color_order=str(detector.get("color_order", "rgb")),
        output_layout=str(output.get("layout", "yolo_raw")),
        has_objectness=bool(output.get("has_objectness", True)),
        box_format=str(output.get("box_format", "pixels")),
        class_activation=str(output.get("class_activation", "sigmoid")),
        nanodet_strides=tuple(nanodet.get("strides", (8, 16, 32))),
        nanodet_reg_max=int(nanodet.get("reg_max", 7)),
        nanodet_num_priors=int(nanodet.get("num_priors", 1)),
        nanodet_output_order=str(nanodet.get("output_order", "cls_reg")),
        confidence_threshold=float(decoding.get("confidence_threshold", 0.25)),
        nms_iou_threshold=float(decoding.get("nms_iou_threshold", 0.45)),
        max_detections=int(decoding.get("max_detections", 300)),
        class_id_map=tuple(decoding.get("class_id_map", ())),
        providers=tuple(runtime.get("providers", ("CPUExecutionProvider",))),
        intra_op_threads=int(runtime.get("intra_op_threads", 1)),
    )
