"""Typed detection models and validation of untrusted detector output.

A detector returns ``RawDetection`` values. Nothing downstream is allowed to
trust them until ``DetectionValidator`` has checked the class, confidence and
box geometry, and converted the box into both screen pixels and viewport
fractions. Rejections are kept with a reason; a malformed detection is never
silently repaired into a plausible one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from perception.config import (
    ClassRole,
    ClassSchema,
    GameStateRole,
    ValidationConfig,
)
from perception.geometry import BoundingBox, NormalizedBox
from perception.image import ImageFrame


class RejectionReason(str, Enum):
    """Why a raw detection was not accepted."""

    INVALID_FORMAT = "invalid_format"
    INVALID_CLASS_ID = "invalid_class_id"
    UNKNOWN_CLASS = "unknown_class"
    CLASS_NAME_MISMATCH = "class_name_mismatch"
    INVALID_CONFIDENCE = "invalid_confidence"
    LOW_CONFIDENCE = "low_confidence"
    INVALID_COORDINATES = "invalid_coordinates"
    DEGENERATE_BOX = "degenerate_box"
    BOX_TOO_SMALL = "box_too_small"
    AREA_TOO_SMALL = "area_too_small"
    OUT_OF_BOUNDS = "out_of_bounds"


@dataclass(frozen=True)
class RawDetection:
    """A detector result before class, confidence or geometry checks.

    Coordinates are interpreted as pixels of the *processed* image. The
    dataclass deliberately performs no validation so invalid values can be
    rejected with an explicit reason by ``DetectionValidator``.
    """

    class_id: Any
    confidence: Any
    x1: Any
    y1: Any
    x2: Any
    y2: Any
    class_name: Any = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RawDetection":
        """Build a raw detection from a JSON-style detector record."""
        if not isinstance(payload, Mapping):
            raise ValueError("detection must be a mapping")
        if "class_id" in payload:
            class_id = payload["class_id"]
        elif "class" in payload:
            class_id = payload["class"]
        else:
            raise ValueError("detection is missing 'class_id'")
        if "confidence" not in payload:
            raise ValueError("detection is missing 'confidence'")
        if "bbox" in payload:
            bbox = payload["bbox"]
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                raise ValueError("detection 'bbox' must contain four values")
            x1, y1, x2, y2 = bbox
        else:
            missing = [key for key in ("x1", "y1", "x2", "y2") if key not in payload]
            if missing:
                raise ValueError(
                    f"detection is missing coordinates {missing}"
                )
            x1, y1, x2, y2 = payload["x1"], payload["y1"], payload["x2"], payload["y2"]
        return cls(
            class_id=class_id,
            confidence=payload["confidence"],
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            class_name=payload.get("class_name", payload.get("name")),
        )

    def as_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": [self.x1, self.y1, self.x2, self.y2],
        }


@dataclass(frozen=True)
class Detection:
    """A validated detection with role and coordinate representations.

    ``screen_box`` is in original screenshot pixels. ``normalized_box`` is in
    fractions of the processed viewport (after crop, before resize), which is
    the coordinate system used for lane assignment. ``clamped`` is True only
    when a coordinate lay outside the processed image by no more than the
    configured bounds tolerance and was explicitly clamped.
    """

    class_id: int
    class_name: str
    confidence: float
    role: ClassRole
    game_state_role: GameStateRole
    screen_box: BoundingBox
    normalized_box: NormalizedBox
    clamped: bool = False
    raw_index: int | None = None
    source: str | None = None

    @property
    def center_screen(self) -> tuple[float, float]:
        return self.screen_box.center

    @property
    def center_normalized(self) -> tuple[float, float]:
        return self.normalized_box.center

    @property
    def size_pixels(self) -> tuple[float, float]:
        return (self.screen_box.width, self.screen_box.height)

    @property
    def size_fraction(self) -> tuple[float, float]:
        return (self.normalized_box.width, self.normalized_box.height)

    def geometry(self) -> dict:
        cx, cy = self.center_screen
        ncx, ncy = self.center_normalized
        return {
            "center_screen": [round(cx, 6), round(cy, 6)],
            "center_normalized": [round(ncx, 6), round(ncy, 6)],
            "size_pixels": [
                round(self.screen_box.width, 6),
                round(self.screen_box.height, 6),
            ],
            "size_fraction": [
                round(self.normalized_box.width, 6),
                round(self.normalized_box.height, 6),
            ],
            "bottom_fraction": round(self.normalized_box.bottom, 6),
            "clamped": self.clamped,
        }

    def as_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "role": self.role.value,
            "game_state_role": self.game_state_role.value,
            "screen_box": list(self.screen_box.as_tuple()),
            "normalized_box": list(self.normalized_box.as_tuple()),
            "geometry": self.geometry(),
            "raw_index": self.raw_index,
            "source": self.source,
        }


@dataclass(frozen=True)
class RejectedDetection:
    """A detection that failed validation, retained for auditing."""

    reason: RejectionReason
    detail: str
    raw: RawDetection | None = None
    raw_index: int | None = None

    def as_dict(self) -> dict:
        return {
            "reason": self.reason.value,
            "detail": self.detail,
            "raw_index": self.raw_index,
            "raw": self.raw.as_dict() if self.raw is not None else None,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Accepted and rejected detections from one frame."""

    accepted: tuple[Detection, ...] = ()
    rejected: tuple[RejectedDetection, ...] = ()

    @property
    def n_received(self) -> int:
        return len(self.accepted) + len(self.rejected)

    def as_dict(self) -> dict:
        return {
            "n_received": self.n_received,
            "n_accepted": len(self.accepted),
            "n_rejected": len(self.rejected),
            "accepted": [item.as_dict() for item in self.accepted],
            "rejected": [item.as_dict() for item in self.rejected],
        }


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


class DetectionValidator:
    """Apply configuration rules and coordinate conversion to raw results."""

    def __init__(
        self,
        config: ValidationConfig,
        schema: ClassSchema,
        frame: ImageFrame,
        source: str | None = None,
    ) -> None:
        if not isinstance(config, ValidationConfig):
            raise ValueError("config must be a ValidationConfig")
        if not isinstance(schema, ClassSchema):
            raise ValueError("schema must be a ClassSchema")
        if not isinstance(frame, ImageFrame):
            raise ValueError("frame must be an ImageFrame")
        self.config = config
        self.schema = schema
        self.frame = frame
        self.source = source
        self._by_id = schema.by_id

    def _reject(
        self, reason: RejectionReason, detail: str, raw: RawDetection | None, index: int | None
    ) -> RejectedDetection:
        return RejectedDetection(
            reason=reason, detail=detail, raw=raw, raw_index=index
        )

    def validate_one(
        self, raw: Any, index: int | None = None
    ) -> Detection | RejectedDetection:
        if not isinstance(raw, RawDetection):
            return self._reject(
                RejectionReason.INVALID_FORMAT,
                f"expected RawDetection, got {type(raw).__name__}",
                None,
                index,
            )

        class_id = raw.class_id
        if isinstance(class_id, bool) or not isinstance(class_id, int):
            return self._reject(
                RejectionReason.INVALID_CLASS_ID,
                f"class_id must be an integer, got {class_id!r}",
                raw,
                index,
            )
        definition = self._by_id.get(class_id)
        if definition is None:
            return self._reject(
                RejectionReason.UNKNOWN_CLASS,
                f"class_id {class_id} is not in the configured schema",
                raw,
                index,
            )

        if raw.class_name is not None:
            if not isinstance(raw.class_name, str):
                return self._reject(
                    RejectionReason.CLASS_NAME_MISMATCH,
                    "class_name must be a string when provided",
                    raw,
                    index,
                )
            if raw.class_name != definition.name:
                return self._reject(
                    RejectionReason.CLASS_NAME_MISMATCH,
                    f"class_id {class_id} maps to {definition.name!r}, "
                    f"detector reported {raw.class_name!r}",
                    raw,
                    index,
                )

        try:
            confidence = _number(raw.confidence, "confidence")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be in [0, 1]")
        except ValueError as exc:
            return self._reject(
                RejectionReason.INVALID_CONFIDENCE, str(exc), raw, index
            )
        if confidence < self.config.confidence_threshold:
            return self._reject(
                RejectionReason.LOW_CONFIDENCE,
                f"confidence {confidence:.4f} is below "
                f"{self.config.confidence_threshold:.4f}",
                raw,
                index,
            )

        try:
            x1 = _number(raw.x1, "x1")
            y1 = _number(raw.y1, "y1")
            x2 = _number(raw.x2, "x2")
            y2 = _number(raw.y2, "y2")
        except ValueError as exc:
            return self._reject(
                RejectionReason.INVALID_COORDINATES, str(exc), raw, index
            )
        if x2 <= x1 or y2 <= y1:
            return self._reject(
                RejectionReason.DEGENERATE_BOX,
                f"box must have positive width and height, got "
                f"({x1}, {y1}, {x2}, {y2})",
                raw,
                index,
            )

        width = x2 - x1
        height = y2 - y1
        if width < self.config.min_box_pixels or height < self.config.min_box_pixels:
            return self._reject(
                RejectionReason.BOX_TOO_SMALL,
                f"box is {width:.3f}x{height:.3f} px; minimum side is "
                f"{self.config.min_box_pixels:.3f} px",
                raw,
                index,
            )

        processed_width, processed_height = self.frame.processed_size
        tolerance = self.config.bounds_tolerance_pixels
        overflow = max(
            -x1,
            -y1,
            x2 - processed_width,
            y2 - processed_height,
        )
        if overflow > tolerance:
            return self._reject(
                RejectionReason.OUT_OF_BOUNDS,
                f"box lies {overflow:.3f} px outside the "
                f"{processed_width}x{processed_height} processed image; "
                f"tolerance is {tolerance:.3f} px",
                raw,
                index,
            )
        clamped = overflow > 0.0
        if clamped:
            x1 = min(max(x1, 0.0), processed_width)
            y1 = min(max(y1, 0.0), processed_height)
            x2 = min(max(x2, 0.0), processed_width)
            y2 = min(max(y2, 0.0), processed_height)
            if x2 <= x1 or y2 <= y1:
                return self._reject(
                    RejectionReason.DEGENERATE_BOX,
                    "box collapsed after clamping to the processed image",
                    raw,
                    index,
                )

        area_fraction = (x2 - x1) * (y2 - y1) / (processed_width * processed_height)
        if area_fraction < self.config.min_area_fraction:
            return self._reject(
                RejectionReason.AREA_TOO_SMALL,
                f"box area fraction {area_fraction:.6f} is below "
                f"{self.config.min_area_fraction:.6f}",
                raw,
                index,
            )

        try:
            screen_box = self.frame.processed_box_to_screen(x1, y1, x2, y2)
            normalized_box = self.frame.screen_box_to_normalized(screen_box)
        except ValueError as exc:
            return self._reject(
                RejectionReason.INVALID_COORDINATES, str(exc), raw, index
            )

        return Detection(
            class_id=class_id,
            class_name=definition.name,
            confidence=confidence,
            role=definition.role,
            game_state_role=definition.game_state_role,
            screen_box=screen_box,
            normalized_box=normalized_box,
            clamped=clamped,
            raw_index=index,
            source=self.source,
        )

    def validate_many(self, raw_detections: Any) -> ValidationResult:
        if isinstance(raw_detections, (str, bytes, Mapping)):
            raise ValueError("detections must be a sequence, not a single record")
        if not isinstance(raw_detections, Sequence):
            raise ValueError("detections must be a sequence")
        accepted: list[Detection] = []
        rejected: list[RejectedDetection] = []
        for index, raw in enumerate(raw_detections):
            outcome = self.validate_one(raw, index)
            if isinstance(outcome, Detection):
                accepted.append(outcome)
            else:
                rejected.append(outcome)
        return ValidationResult(
            accepted=tuple(accepted), rejected=tuple(rejected)
        )


def coerce_raw_detections(
    detections: Any,
) -> tuple[list[tuple[int, RawDetection]], list[RejectedDetection]]:
    """Convert detector output records; malformed records become rejections.

    ``RawDetection`` instances are passed through with their original index.
    Mappings are parsed with ``RawDetection.from_mapping``. Any other value is
    rejected rather than ignored.
    """
    if detections is None:
        return [], []
    if isinstance(detections, (str, bytes, Mapping)) or not isinstance(
        detections, Sequence
    ):
        raise ValueError("detector output must be a sequence of detections")
    raws: list[tuple[int, RawDetection]] = []
    rejected: list[RejectedDetection] = []
    for index, item in enumerate(detections):
        if isinstance(item, RawDetection):
            raws.append((index, item))
            continue
        try:
            raws.append((index, RawDetection.from_mapping(item)))
        except ValueError as exc:
            rejected.append(
                RejectedDetection(
                    reason=RejectionReason.INVALID_FORMAT,
                    detail=str(exc),
                    raw=None,
                    raw_index=index,
                )
            )
    return raws, rejected
