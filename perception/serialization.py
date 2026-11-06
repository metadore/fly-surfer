"""Stable JSON representation of validated detections and scenes.

Screen boxes are original screenshot pixels; normalised boxes are viewport
fractions. Both are emitted so a consumer cannot confuse the two.
"""

from __future__ import annotations

from typing import Iterable

from perception.detection import Detection, RejectedDetection
from perception.scene import PerceivedScene


def detection_to_record(detection: Detection) -> dict:
    if not isinstance(detection, Detection):
        raise ValueError("detection must be a Detection")
    screen = detection.screen_box
    normalized = detection.normalized_box
    center_x, center_y = detection.center_screen
    return {
        "class_id": detection.class_id,
        "class_name": detection.class_name,
        "role": detection.role.value,
        "game_state_role": detection.game_state_role.value,
        "confidence": round(detection.confidence, 6),
        "bbox": {
            "x1": round(screen.x1, 3),
            "y1": round(screen.y1, 3),
            "x2": round(screen.x2, 3),
            "y2": round(screen.y2, 3),
        },
        "center": {"x": round(center_x, 3), "y": round(center_y, 3)},
        "normalized_bbox": {
            "x1": round(normalized.x1, 6),
            "y1": round(normalized.y1, 6),
            "x2": round(normalized.x2, 6),
            "y2": round(normalized.y2, 6),
        },
        "size_fraction": {
            "width": round(normalized.width, 6),
            "height": round(normalized.height, 6),
        },
        "clamped": bool(detection.clamped),
        "raw_index": detection.raw_index,
        "source": detection.source,
    }


def detections_to_records(detections: Iterable[Detection]) -> list[dict]:
    return [detection_to_record(detection) for detection in detections]


def rejection_to_record(rejection: RejectedDetection) -> dict:
    if not isinstance(rejection, RejectedDetection):
        raise ValueError("rejection must be a RejectedDetection")
    return rejection.as_dict()


def scene_to_records(scene: PerceivedScene) -> dict:
    """Serialise a scene with lane decisions and rejection reasons."""
    if not isinstance(scene, PerceivedScene):
        raise ValueError("scene must be a PerceivedScene")
    return {
        "frame_id": scene.frame_id,
        "timestamp_ms": scene.timestamp_ms,
        "source_path": scene.source_path,
        "original_size": list(scene.original_size),
        "viewport_size": list(scene.viewport_size),
        "detections": [detection_to_record(obj.detection) for obj in scene.objects],
        "lanes": [
            {"detection_index": index, **obj.lane_assignment.as_dict()}
            for index, obj in enumerate(scene.objects)
        ],
        "lane_occupancy": [lane.as_dict() for lane in scene.lane_occupancy],
        "uncertainty": scene.uncertainty.as_dict(),
        "modality": scene.modality.as_dict(),
        "rejected": [item.as_dict() for item in scene.rejected],
    }
