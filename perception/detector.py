"""Detector abstraction and a test-only scripted detector.

``Detector`` is a protocol: any object with a compatible ``detect`` method can
be supplied to the pipeline. There is no trained model in this phase. The
``MockDetector`` returns experimenter-supplied detections without looking at
the image; it exists so the rest of the pipeline can be tested deterministically
and must never be presented as visual recognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from perception.detection import RawDetection
from perception.image import ImageFrame


@runtime_checkable
class Detector(Protocol):
    """Structural interface for a future YOLO or other object detector."""

    def detect(self, frame: ImageFrame) -> Sequence[Any]:
        """Return detections in pixels of the processed image."""
        ...

    def describe(self) -> dict:
        """Return a JSON-safe description of the detector and its origin."""
        ...


@dataclass(frozen=True)
class DetectorInfo:
    """Description of a detector implementation."""

    name: str
    kind: str
    test_only: bool
    produces: str
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "test_only": self.test_only,
            "produces": self.produces,
            "notes": list(self.notes),
        }


class MockDetector:
    """Deterministic scripted detector for tests and pipeline plumbing.

    This is **not** a perception model. It ignores image content and returns
    the records it was constructed with, either for every frame or per
    ``frame_id``. No randomness is used.
    """

    INFO = DetectorInfo(
        name="mock-scripted",
        kind="scripted_test_detector",
        test_only=True,
        produces="untrusted RawDetection records in processed-image pixels",
        notes=(
            "Does not inspect pixels and performs no visual recognition.",
            "Used only to exercise validation, lane assignment and conversion.",
            "Never report outputs from this detector as model accuracy.",
        ),
    )

    def __init__(
        self,
        detections: Sequence[Any] | None = None,
        *,
        frame_detections: Mapping[str, Sequence[Any]] | None = None,
        default_detections: Sequence[Any] | None = None,
    ) -> None:
        if detections is not None and not isinstance(detections, Sequence):
            raise ValueError("detections must be a sequence")
        self._detections = tuple(detections or ())
        self._frame_detections = {
            str(key): tuple(value)
            for key, value in (frame_detections or {}).items()
        }
        self._default = tuple(
            default_detections if default_detections is not None else self._detections
        )

    @property
    def test_only(self) -> bool:
        return True

    def detect(self, frame: ImageFrame) -> list[Any]:
        if frame.frame_id is not None and frame.frame_id in self._frame_detections:
            return list(self._frame_detections[frame.frame_id])
        return list(self._default)

    def describe(self) -> dict:
        payload = self.INFO.as_dict()
        payload.update(
            {
                "n_default_detections": len(self._default),
                "frame_ids": sorted(self._frame_detections),
                "test_only": True,
            }
        )
        return payload


def describe_detector(detector: Any) -> dict:
    """Describe a detector without assuming it implements ``describe``."""
    if hasattr(detector, "describe") and callable(detector.describe):
        description = detector.describe()
        if isinstance(description, Mapping):
            payload = dict(description)
            payload.setdefault("test_only", bool(getattr(detector, "test_only", False)))
            return payload
    return {
        "name": type(detector).__name__,
        "kind": "custom_detector",
        "test_only": bool(getattr(detector, "test_only", False)),
        "produces": "unspecified",
        "notes": [],
    }
