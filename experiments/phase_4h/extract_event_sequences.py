"""Phase 4H.4 input extraction: archive sensory event streams for three segments.

The Phase 3B.2C replay archived events for frames 100-199 only. Phase 4H.4
needs more than one temporal stream, so this runner reuses the unchanged
Phase 3B perception functions to produce compact event archives for frames
0-99 and 200-299 of the same held-out recording group.

Nothing in the Phase 3B pipeline is modified: :func:`discover_frames`,
:func:`_build_detector`, :func:`_experiment_perception_config`,
:func:`_process_frames`, :func:`_temporal_run` and :func:`_events` are imported
and called as they are. The detector is not retrained and its thresholds are
not changed. No neural simulation is run here.

All 504 frames of the ``datasetfootage`` group are assigned to the validation
split in the fixed split manifest (LOGO fold 1), so both extra segments are
held out by recording.

Outputs: ``experiments/phase_4h/sequences/events_<start>_<end>.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_3b.real_sequence_replay import (  # noqa: E402
    _build_detector,
    _events,
    _experiment_perception_config,
    _process_frames,
    _temporal_run,
    discover_frames,
)

TOLERANCE = 1.0
OUT_DIR = PROJECT_ROOT / "experiments" / "phase_4h" / "sequences"

LIMITATIONS = [
    "Segments come from one recording group; they are not independent "
    "recordings.",
    "Frames carry no source timestamps; 30 fps is assumed and timestamps are "
    "synthesized as (local frame index) * 1000/30 ms.",
    "The detector was trained on this recording group; the group is held out "
    "by the fixed split, but detections on it are not an independent estimate "
    "of detector accuracy.",
    "Event timestamps and feature values are perception output, not ground "
    "truth about the scene.",
]


def extract(start: int, end: int) -> dict:
    sequence = discover_frames(start, end)
    detector, detector_config = _build_detector()
    perception_config = _experiment_perception_config(TOLERANCE)
    from perception.pipeline import PerceptionPipeline

    pipeline = PerceptionPipeline(perception_config, detector)
    observations, detection_records = _process_frames(
        pipeline, sequence["frames"], TOLERANCE
    )
    temporal = _temporal_run(observations)
    events = _events(temporal)

    event_kinds: dict[str, int] = {}
    event_classes: dict[str, int] = {}
    for event in events:
        event_kinds[event["event"]] = event_kinds.get(event["event"], 0) + 1
        event_classes[event["class_name"]] = (
            event_classes.get(event["class_name"], 0) + 1
        )

    accepted = sum(1 for record in detection_records if record["n_accepted"] > 0)
    return {
        "phase": "4H.4-input",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "segment": {
            "group": sequence["group"],
            "frame_start": start,
            "frame_end": end,
            "n_frames": len(sequence["frames"]),
            "image_size": sequence["image_size"],
            "sequence_sha256": sequence["sequence_sha256"],
            "split_folder_counts": sequence["split_folder_counts"],
            "split_assignment": "valid (fixed grouped split, all frames)",
            "logo_fold": sequence["logo_fold"],
            "timestamp_policy": (
                "30 fps assumed; timestamps synthesized as (local frame index)"
                " * 1000/30 ms because images carry no timestamps"
            ),
        },
        "detector": detector.describe(),
        "detector_config": {
            "model_path": str(detector_config.model_path),
            "model_sha256": detector_config.model_sha256,
            "confidence_threshold": detector_config.confidence_threshold,
            "nms_iou_threshold": detector_config.nms_iou_threshold,
        },
        "perception": {
            "bounds_tolerance_pixels": TOLERANCE,
            "n_detection_records": len(detection_records),
            "n_frames_with_accepts": accepted,
            "n_accepted_total": sum(
                record["n_accepted"] for record in detection_records
            ),
        },
        "temporal": {
            "n_frames": len(temporal),
            "final_time_ms": float(temporal[-1].time_ms),
            "frame_times_ms": [round(float(frame.time_ms), 4) for frame in temporal],
        },
        "events": events,
        "event_counts": {
            "n_events": len(events),
            "by_kind": dict(sorted(event_kinds.items())),
            "by_class": dict(sorted(event_classes.items())),
            "n_pulse_events": sum(1 for event in events if event["is_pulse"]),
        },
        "spike_events": int(
            sum(len(frame.events) for frame in temporal)
        ),
        "limitations": LIMITATIONS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or OUT_DIR / f"events_{args.start}_{args.end}.json"
    payload = extract(args.start, args.end)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8"
    )
    print(
        f"wrote {output} | frames={payload['segment']['n_frames']} "
        f"events={payload['event_counts']['n_events']} "
        f"detections={payload['perception']['n_accepted_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
