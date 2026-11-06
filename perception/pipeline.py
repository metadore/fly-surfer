"""End-to-end perception pipeline: image -> detections -> scene -> GameState.

The pipeline never imports the neural simulator. It can be run on synthetic
frames and scripted detections, which is what Phase 3B.2A tests do. Until a
trained detector is integrated, no output of this module is visual recognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from perception.config import PerceptionConfig, load_perception_config
from perception.detection import (
    DetectionValidator,
    RejectedDetection,
    ValidationResult,
    coerce_raw_detections,
)
from perception.detector import describe_detector
from perception.game_state_adapter import GameStateAdapter, GameStateConversion
from perception.image import ImageFrame, ImagePreprocessor
from perception.lanes import LaneAssigner
from perception.scene import PerceivedScene, SceneBuilder
from perception.sensory_bridge import SpatialFeatureBridge, SpatialFeatureBundle


@dataclass(frozen=True)
class PerceptionResult:
    """Everything produced for one frame, including audit information."""

    frame: ImageFrame
    validation: ValidationResult
    scene: PerceivedScene
    conversion: GameStateConversion
    spatial: SpatialFeatureBundle
    detector: dict
    config: dict

    def frame_info(self) -> dict:
        return {
            "frame_id": self.frame.frame_id,
            "source_path": (
                str(self.frame.source_path) if self.frame.source_path else None
            ),
            "timestamp_ms": self.frame.timestamp_ms,
            "original_size": list(self.frame.original_size),
            "crop_box": list(self.frame.crop_box),
            "viewport_size": list(self.frame.viewport_size),
            "processed_size": list(self.frame.processed_size),
            "scale": [self.frame.scale_x, self.frame.scale_y],
        }

    def as_dict(self) -> dict:
        return {
            "frame": self.frame_info(),
            "detector": self.detector,
            "config": self.config,
            "validation": self.validation.as_dict(),
            "scene": self.scene.as_dict(),
            "game_state": self.conversion.as_dict(),
            "observations": self.spatial.observations.as_dict(),
            "features": dict(self.spatial.features),
            "feature_groups": [item.as_dict() for item in self.spatial.groups],
        }


class PerceptionPipeline:
    """Run preprocessing, validation, scene building and GameState conversion."""

    def __init__(self, config: PerceptionConfig, detector: Any) -> None:
        if not isinstance(config, PerceptionConfig):
            raise ValueError("config must be a PerceptionConfig")
        if not hasattr(detector, "detect") or not callable(detector.detect):
            raise ValueError("detector must provide a callable detect(frame) method")
        self.config = config
        self.detector = detector
        self.preprocessor = ImagePreprocessor(config.preprocess)
        self.assigner = LaneAssigner(config.lanes)
        self.scene_builder = SceneBuilder(self.assigner, config.schema)
        self.adapter = GameStateAdapter(config.distance)
        self.bridge = SpatialFeatureBridge(config.distance)

    @classmethod
    def from_config(cls, path: str | Path, detector: Any) -> "PerceptionPipeline":
        return cls(load_perception_config(path), detector)

    @property
    def detector_info(self) -> dict:
        return describe_detector(self.detector)

    def run(
        self,
        frame: ImageFrame,
        detections: Any | None = None,
    ) -> PerceptionResult:
        """Process one frame.

        ``detections`` overrides the detector for this call. When omitted the
        configured detector is invoked. Overrides are still validated as
        untrusted input.
        """
        if not isinstance(frame, ImageFrame):
            raise ValueError("frame must be an ImageFrame")
        description = self.detector_info
        detector_name = str(description.get("name", type(self.detector).__name__))
        if detections is None:
            detections = self.detector.detect(frame)
        raws, rejected = coerce_raw_detections(detections)
        validator = DetectionValidator(
            self.config.validation,
            self.config.schema,
            frame,
            source=detector_name,
        )
        accepted = []
        for index, raw in raws:
            outcome = validator.validate_one(raw, index)
            if isinstance(outcome, RejectedDetection):
                rejected.append(outcome)
            else:
                accepted.append(outcome)
        rejected.sort(
            key=lambda item: (
                item.raw_index if item.raw_index is not None else 1_000_000_000
            )
        )
        validation = ValidationResult(
            accepted=tuple(accepted), rejected=tuple(rejected)
        )
        scene = self.scene_builder.build(frame, validation)
        conversion = self.adapter.convert(scene)
        spatial = self.bridge.from_conversion(scene, conversion)
        return PerceptionResult(
            frame=frame,
            validation=validation,
            scene=scene,
            conversion=conversion,
            spatial=spatial,
            detector=description,
            config=self.config.as_dict(),
        )

    def run_path(
        self,
        path: str | Path,
        *,
        frame_id: str | None = None,
        timestamp_ms: float | None = None,
        detections: Any | None = None,
    ) -> PerceptionResult:
        frame = self.preprocessor.load(
            path, frame_id=frame_id, timestamp_ms=timestamp_ms
        )
        return self.run(frame, detections=detections)

    def describe(self) -> dict:
        return {
            "pipeline": "phase_3b2a_visual_perception",
            "detector": self.detector_info,
            "config": self.config.as_dict(),
            "integrated_with_simulator": False,
            "visual_recognition_available": False,
            "limitations": [
                "No trained detector is part of this package.",
                "Distance is an uncalibrated bottom-edge proxy.",
                "Lane assignment is geometric and does not model perspective.",
            ],
        }
