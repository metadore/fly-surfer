#!/usr/bin/env python3
"""Phase 3B.2C: replay one contiguous real Subway Surfers sequence.

The chain is the existing one, with no duplicated implementations::

    datasetframe -> ImagePreprocessor -> OnnxRuntimeDetector
                 -> DetectionValidator -> PerceivedScene -> FrameObservations
                 -> MultiObjectTracker -> TemporalFeatureEncoder
                 -> TemporalActivationScheduler -> BrainSimulator

The sequence is frames 100-199 of the single ``datasetfootage`` recording.
Every frame is assigned to the fixed split's validation set (grouped split)
and to LOGO fold 1. Frames are ordered by their numeric frame id.

Boundary policy for this experiment: a box may lie at most 1.0 processed
pixel outside the viewport, is then clipped, and both the original and clipped
boxes plus the clip distance are recorded. Anything farther out is rejected.
Production ``configs/perception_config.yaml`` keeps its tolerance at 0.0; the
override exists only in this experiment's in-memory configuration.

This is an integration experiment. It does not measure gameplay success,
annotated identity tracking or biological perception.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import yaml
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from experiments.phase_3c.temporal_calibration import (  # noqa: E402
    FEATURES,
    TRACKING,
)
from perception.config import load_perception_config  # noqa: E402
from perception.detector_config import load_detector_config  # noqa: E402
from perception.inference import OnnxRuntimeDetector  # noqa: E402
from perception.pipeline import PerceptionPipeline  # noqa: E402
from perception.temporal import (  # noqa: E402
    Lifecycle,
    TemporalConfig,
    TemporalFeatureConfig,
    TemporalSequenceProcessor,
)
from perception.tracking import TrackState, TrackingConfig  # noqa: E402
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402
from sensory.temporal_scheduler import (  # noqa: E402
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

GROUP = "datasetfootage"
FRAME_START = 100
FRAME_END = 199
SMOKE_FRAMES = 10
FPS = 30.0
FRAME_INTERVAL_MS = 1000.0 / FPS
BOUNDS_TOLERANCE_PIXELS = 1.0
SEED = 20261106
MAX_RECORDED_SPIKES = 30_000_000

DATASET_ROOT = (
    PROJECT_ROOT
    / "datasets"
    / "external"
    / "subway surfers"
    / "roboflow_v15_yolov8"
    / "subway surfers object dataset.v15-added.yolov8"
)
MANIFEST = PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"
DETECTOR_CONFIG = PROJECT_ROOT / "configs" / "detector_config.yaml"
PERCEPTION_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
CONNECTOME = PROJECT_ROOT / "datasets" / "processed" / "connectome.npz"
OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "phase_3b"
    / "results"
    / "phase_3b2c_real_sequence_replay.json"
)
FRAME_PATTERN = re.compile(
    rf"^{GROUP}_mp4-(?P<n>\d+)_jpg\.rf\.(?P<hash>[0-9a-f]+)\.jpg$", re.I
)

LIMITATIONS = [
    "This is an engineering integration experiment, not evidence of gameplay "
    "success or biological perception.",
    "Frames carry no source timestamps; 30 fps is assumed and timestamps are "
    "synthesized as (local_index) * 1000/30 ms.",
    "The detector was trained on the same recording groups; the sequence is "
    "held out by recording in the fixed split and LOGO fold 1, but there is "
    "no independent test set.",
    "No annotated object identities exist, so tracker-ID switches cannot be "
    "distinguished from real object changes. Reported track ids are tracker "
    "ids, not object identities.",
    "The v15 schema has no player and no coin class. Player movement, jumping, "
    "rolling and coin observations are therefore unavailable, not inferred.",
    "Lane, distance and velocity are image geometry. Distance is an "
    "uncalibrated bottom-edge proxy, not metres.",
    "Occlusion is inferred from missed associations, not observed directly.",
    "Spikes are model output under configured assumptions, not measured "
    "biological activity. The connectome is fixed and no plasticity is used.",
    "No action is selected anywhere in this chain.",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_json(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_array(value: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(value).tobytes()
    ).hexdigest()


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _summary(values) -> dict:
    numbers = [float(value) for value in values]
    if not numbers:
        return {"n": 0}
    ordered = sorted(numbers)
    return {
        "n": len(numbers),
        "mean": round(statistics.fmean(numbers), 4),
        "median": round(statistics.median(numbers), 4),
        "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 4),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
    }


def discover_frames(start: int = FRAME_START, end: int = FRAME_END) -> list[dict]:
    """Find the requested frames, verify order, labels and split assignment."""
    if start > end:
        raise ValueError("start must not exceed end")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assignments = manifest["fixed_split"]["assignments"]
    group_info = manifest["groups"][GROUP]
    fold = next(
        item for item in manifest["logo_folds"] if item["valid_group"] == GROUP
    )

    found: dict[int, dict] = {}
    for split in ("train", "valid"):
        image_dir = DATASET_ROOT / split / "images"
        label_dir = DATASET_ROOT / split / "labels"
        for path in sorted(image_dir.iterdir()):
            match = FRAME_PATTERN.match(path.name)
            if match is None:
                continue
            number = int(match.group("n"))
            if not start <= number <= end:
                continue
            if number in found:
                raise ValueError(f"frame {number} appears in more than one folder")
            label_path = label_dir / f"{path.stem}.txt"
            if not label_path.is_file():
                raise ValueError(f"frame {number} has no label file")
            key = f"{split}/images/{path.name}"
            assigned = assignments.get(key)
            if assigned != "valid":
                raise ValueError(
                    f"frame {number} ({key}) is assigned to {assigned!r}, not "
                    "the validation split"
                )
            with Image.open(path) as image:
                size = image.size
            found[number] = {
                "frame_number": number,
                "split_folder": split,
                "split_assignment": assigned,
                "image_name": path.name,
                "image_path": str(path.relative_to(PROJECT_ROOT)),
                "label_path": str(label_path.relative_to(PROJECT_ROOT)),
                "image_size": list(size),
                "image_sha256": _sha256(path),
                "label_sha256": _sha256(label_path),
            }

    expected = list(range(start, end + 1))
    if sorted(found) != expected:
        missing = sorted(set(expected) - set(found))
        extra = sorted(set(found) - set(expected))
        raise ValueError(f"sequence is not contiguous; missing={missing} extra={extra}")

    sequence = [found[number] for number in expected]
    for item in sequence:
        boxes = 0
        classes = Counter()
        label_path = PROJECT_ROOT / item["label_path"]
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            boxes += 1
            classes[int(parts[0])] += 1
        item["label_boxes"] = boxes
        item["label_classes"] = dict(sorted(classes.items()))

    sizes = {tuple(item["image_size"]) for item in sequence}
    if len(sizes) != 1:
        raise ValueError(f"sequence mixes image sizes: {sorted(sizes)}")

    sequence_digest = hashlib.sha256()
    for item in sequence:
        sequence_digest.update(bytes.fromhex(item["image_sha256"]))
        sequence_digest.update(bytes.fromhex(item["label_sha256"]))
    return {
        "frames": sequence,
        "group": GROUP,
        "group_info": group_info,
        "logo_fold": {
            "fold": fold["fold"],
            "valid_group": fold["valid_group"],
            "valid_images": fold["valid_images"],
            "valid_boxes": fold["valid_boxes"],
        },
        "sequence_sha256": sequence_digest.hexdigest(),
        "image_size": list(next(iter(sizes))),
        "split_folder_counts": dict(
            Counter(item["split_folder"] for item in sequence)
        ),
    }


def _experiment_perception_config(tolerance: float):
    base = load_perception_config(PERCEPTION_CONFIG)
    if base.validation.bounds_tolerance_pixels != 0.0:
        raise ValueError(
            "production bounds tolerance changed; this experiment expects 0.0 "
            "and applies its override in memory"
        )
    if tolerance == 0.0:
        return base
    return replace(
        base,
        validation=replace(
            base.validation, bounds_tolerance_pixels=float(tolerance)
        ),
    )


def _temporal_config() -> TemporalConfig:
    return TemporalConfig(
        tracking=TrackingConfig(**asdict(TRACKING)),
        features=TemporalFeatureConfig(**asdict(FEATURES)),
    )


def _build_detector():
    detector_config = load_detector_config(DETECTOR_CONFIG)
    schema = load_perception_config(PERCEPTION_CONFIG).schema
    detector = OnnxRuntimeDetector(detector_config, schema)
    if detector_config.model_sha256 is not None:
        if detector.model_sha256 != detector_config.model_sha256:
            raise RuntimeError("detector SHA-256 was not verified at load time")
    return detector, detector_config


def _process_frames(pipeline, frames: list[dict], tolerance: float) -> tuple[list, list[dict]]:
    observations = []
    records = []
    for index, item in enumerate(frames):
        timestamp_ms = index * FRAME_INTERVAL_MS
        frame = pipeline.preprocessor.load(
            PROJECT_ROOT / item["image_path"],
            frame_id=f"{GROUP}-{item['frame_number']:04d}",
            timestamp_ms=timestamp_ms,
        )
        result = pipeline.run(frame)
        observation = result.spatial.observations
        observations.append(observation)

        accepted = result.validation.accepted
        rejected = result.validation.rejected
        by_raw = {
            obs.raw_index: obs for obs in observation.observations
            if obs.raw_index is not None
        }
        accepted_records = []
        for detection in accepted:
            obs = by_raw.get(detection.raw_index)
            accepted_records.append(
                {
                    "class_id": detection.class_id,
                    "class_name": detection.class_name,
                    "role": detection.role.value,
                    "confidence": round(detection.confidence, 6),
                    "screen_box": [
                        round(value, 4)
                        for value in detection.screen_box.as_tuple()
                    ],
                    "normalized_box": [
                        round(value, 6)
                        for value in detection.normalized_box.as_tuple()
                    ],
                    "lane": obs.lane if obs is not None else None,
                    "distance_proxy": (
                        round(obs.distance_proxy, 6)
                        if obs is not None and obs.distance_proxy is not None
                        else None
                    ),
                    "visibility": (
                        obs.visibility.value if obs is not None else None
                    ),
                    "clamped": detection.clamped,
                    "clip_distance_pixels": round(
                        detection.clip_distance_pixels, 6
                    ),
                    "raw_box_pixels": (
                        [round(value, 6) for value in detection.raw_box_pixels]
                        if detection.raw_box_pixels is not None
                        else None
                    ),
                    "clipped_box_pixels": (
                        [round(value, 6) for value in detection.clipped_box_pixels]
                        if detection.clipped_box_pixels is not None
                        else None
                    ),
                }
            )
        rejected_records = [
            {
                "reason": item.reason.value,
                "detail": item.detail,
                "raw_index": item.raw_index,
                "raw": item.raw.as_dict() if item.raw is not None else None,
            }
            for item in rejected
        ]
        records.append(
            {
                "frame_index": index,
                "frame_number": item["frame_number"],
                "frame_id": frame.frame_id,
                "timestamp_ms": round(timestamp_ms, 6),
                "image_size": list(frame.original_size),
                "processed_size": list(frame.processed_size),
                "n_candidates": len(accepted) + len(rejected),
                "n_decoded_above_threshold": int(
                    pipeline.detector.last_decoded_count
                ),
                "n_accepted": len(accepted),
                "n_rejected": len(rejected),
                "n_clipped": sum(
                    1 for detection in accepted if detection.clamped
                ),
                "max_clip_distance_pixels": max(
                    (
                        detection.clip_distance_pixels
                        for detection in accepted
                    ),
                    default=0.0,
                ),
                "bounds_tolerance_pixels": tolerance,
                "accepted": accepted_records,
                "rejected": rejected_records,
                "detector_call_ms": round(
                    float(pipeline.detector.last_detector_call_ms or 0.0), 3
                ),
                "preprocess_ms": round(
                    float(pipeline.detector.last_preprocess_ms or 0.0), 3
                ),
                "session_run_ms": round(
                    float(pipeline.detector.last_session_run_ms or 0.0), 3
                ),
                "postprocess_ms": round(
                    float(pipeline.detector.last_postprocess_ms or 0.0), 3
                ),
            }
        )
    return observations, records


def _temporal_run(observations) -> list:
    processor = TemporalSequenceProcessor(_temporal_config())
    return [processor.process(observation) for observation in observations]


def _events(temporal) -> list[dict]:
    return [
        {
            "frame_index": event.frame_index,
            "frame_id": frame.frame_id,
            "track_id": event.track_id,
            "event": event.event.value,
            "class_name": event.class_name,
            "lane": event.lane,
            "time_ms": round(event.time_ms, 4),
            "confidence": round(event.confidence, 6),
            "distance_proxy": (
                round(event.distance_proxy, 6)
                if event.distance_proxy is not None
                else None
            ),
            "is_pulse": event.is_pulse,
            "feature_values": dict(event.feature_values),
            "detail": event.detail,
        }
        for frame in temporal
        for event in frame.events
    ]


def _tracking_records(temporal) -> list[dict]:
    records = []
    for frame in temporal:
        states = Counter(track.state.value for track in frame.tracks)
        lifecycles = Counter(track.lifecycle.value for track in frame.tracks)
        records.append(
            {
                "frame_index": frame.frame_index,
                "frame_id": frame.frame_id,
                "time_ms": round(frame.time_ms, 4),
                "dt_ms": round(frame.dt_ms, 4),
                "is_gap": frame.is_gap,
                "track_ids": sorted(track.track_id for track in frame.tracks),
                "states": dict(sorted(states.items())),
                "lifecycles": dict(sorted(lifecycles.items())),
                "n_events": len(frame.events),
                "n_matches": len(frame.matches),
                "created_track_ids": sorted(
                    item.track_id for item in frame.created
                ),
                "occluded_track_ids": sorted(
                    item.track_id for item in frame.occluded
                ),
                "lost_track_ids": sorted(item.track_id for item in frame.lost),
                "n_duplicates": len(frame.duplicates),
                "unrepresented_tracks": frame.unrepresented_tracks,
                "notes": list(frame.notes),
            }
        )
    return records


def _track_summaries(temporal) -> list[dict]:
    by_track: dict[int, list] = defaultdict(list)
    for frame in temporal:
        for track in frame.tracks:
            by_track[track.track_id].append(track)

    summaries = []
    for track_id in sorted(by_track):
        items = by_track[track_id]
        items.sort(key=lambda item: item.frame_index)
        lane_sequence = [item.lane for item in items]
        lane_changes = []
        for previous, current in zip(items, items[1:]):
            if (
                previous.lane is not None
                and current.lane is not None
                and previous.lane != current.lane
            ):
                lane_changes.append(
                    {
                        "from_frame": previous.frame_index,
                        "to_frame": current.frame_index,
                        "from_lane": previous.lane,
                        "to_lane": current.lane,
                    }
                )
        distance_deltas = [
            item.distance_delta
            for item in items
            if item.distance_delta is not None
        ]
        deltas_x = [item.delta_x for item in items if item.delta_x is not None]
        deltas_y = [item.delta_y for item in items if item.delta_y is not None]
        summaries.append(
            {
                "track_id": track_id,
                "class_id": items[0].class_id,
                "class_name": items[0].class_name,
                "role": items[0].role.value,
                "first_frame": items[0].frame_index,
                "last_frame": items[-1].frame_index,
                "n_frames": len(items),
                "max_hits": max(item.hits for item in items),
                "ever_confirmed": any(item.confirmed for item in items),
                "lifecycles": dict(
                    sorted(
                        Counter(
                            item.lifecycle.value for item in items
                        ).items()
                    )
                ),
                "lanes_observed": sorted(
                    {value for value in lane_sequence if value is not None}
                ),
                "lane_sequence": lane_sequence,
                "observable_lane_changes": lane_changes,
                "distance_delta": _summary(distance_deltas),
                "approaching_frames": sum(
                    1 for item in items if item.approaching is True
                ),
                "receding_frames": sum(
                    1 for item in items if item.receding is True
                ),
                "delta_x": _summary(deltas_x),
                "delta_y": _summary(deltas_y),
                "distance_proxy_range": [
                    round(
                        min(
                            item.distance_proxy
                            for item in items
                            if item.distance_proxy is not None
                        ),
                        6,
                    ),
                    round(
                        max(
                            item.distance_proxy
                            for item in items
                            if item.distance_proxy is not None
                        ),
                        6,
                    ),
                ]
                if any(item.distance_proxy is not None for item in items)
                else None,
            }
        )
    return summaries


def _scheduler_digest(scheduler) -> str:
    signature = scheduler.signature()
    digest = hashlib.sha256()
    for key in (
        "indices",
        "values",
        "starts",
        "frame_values",
        "frame_times",
        "pulse_values",
        "pulse_onsets",
    ):
        if key in signature:
            digest.update(np.ascontiguousarray(signature[key]).tobytes())
            digest.update(b"|")
    return digest.hexdigest()


def _feature_currents(scheduler, times) -> tuple[np.ndarray, list[str]]:
    features = list(scheduler.encoders)
    rows = []
    for time_ms in times:
        currents = scheduler.feature_currents_at(float(time_ms))
        rows.append([currents[feature] for feature in features])
    return np.asarray(rows, dtype=np.float64), features


def _simulate(graph, setup, scheduler, neuron_params, synapse_params, duration_ms, seed):
    process = psutil.Process()
    rss_before = process.memory_info().rss
    simulator = BrainSimulator(
        graph,
        neuron_params,
        synapse_params,
        dt_ms=setup.dt_ms,
        duration_ms=duration_ms,
        seed=int(seed),
        background_current_pa=0.0,
        noise_std_pa=0.0,
        stimulus=None,
        input_schedule=scheduler,
        max_recorded_spikes=MAX_RECORDED_SPIKES,
        progress_interval_ms=100.0,
        diagnostics_interval_steps=200,
    )
    started = time.perf_counter()
    result = simulator.run(progress=False)
    wall = time.perf_counter() - started
    rss_after = process.memory_info().rss
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    summary = {
        "duration_ms": duration_ms,
        "n_steps": int(result.n_steps),
        "wall_runtime_s": round(wall, 4),
        "steps_per_second_wall": round(result.n_steps / wall, 2),
        "activity": dict(result.summary["activity"]),
        "activity_by_stimulation": dict(
            result.summary["activity_by_stimulation"]
        ),
        "synapses": dict(result.summary["synapses"]),
        "diagnostics": dict(result.summary["diagnostics"]),
        "memory": simulator.memory_breakdown(),
        "rss_before_mb": round(rss_before / 1024**2, 3),
        "rss_after_mb": round(rss_after / 1024**2, 3),
        "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
        "max_recorded_spikes": MAX_RECORDED_SPIKES,
    }
    print(
        f"  simulation {duration_ms:.1f} ms | steps={result.n_steps} "
        f"spikes={int(counts.sum())} wall={wall:.2f}s",
        flush=True,
    )
    del simulator
    gc.collect()
    return counts, summary


def _execute_chain(frames, tolerance, seed, setup, neuron_params, synapse_params):
    detector, detector_config = _build_detector()
    perception_config = _experiment_perception_config(tolerance)
    pipeline = PerceptionPipeline(perception_config, detector)
    print(
        f"  detector loaded | sha={detector.model_sha256[:16]}... "
        f"| tolerance={tolerance:.3f}px",
        flush=True,
    )
    observations, detection_records = _process_frames(
        pipeline, frames, tolerance
    )
    temporal = _temporal_run(observations)
    events = _events(temporal)
    tracking = _tracking_records(temporal)
    track_summaries = _track_summaries(temporal)

    duration_ms = float(temporal[-1].time_ms) + float(setup.dt_ms)
    scheduler = TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        temporal,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
    )
    times = (
        np.arange(int(round(duration_ms / float(setup.dt_ms))))
        * float(setup.dt_ms)
    )
    drive, feature_names = _feature_currents(scheduler, times)
    counts, simulation = _simulate(
        graph=setup.mapping.graph,
        setup=setup,
        scheduler=scheduler,
        neuron_params=neuron_params,
        synapse_params=synapse_params,
        duration_ms=duration_ms,
        seed=seed,
    )

    stimulated_indices = setup.mapping.stimulated_indices()
    stimulated = int(counts[stimulated_indices].sum())
    total = int(counts.sum())
    spiking_stimulated = int(np.count_nonzero(counts[stimulated_indices]))
    unstimulated_mask = np.ones(counts.size, dtype=bool)
    unstimulated_mask[stimulated_indices] = False
    spiking_unstimulated = int(np.count_nonzero(counts[unstimulated_mask]))

    detection_digest = _digest_json(
        [
            {
                "frame_id": record["frame_id"],
                "accepted": record["accepted"],
                "rejected": record["rejected"],
            }
            for record in detection_records
        ]
    )
    temporal_digest = _digest_json([frame.as_dict() for frame in temporal])
    scheduler_digest = _scheduler_digest(scheduler)
    spike_digest = _digest_array(counts)

    payload = {
        "detector": detector.describe(),
        "detector_config": {
            "model_path": str(detector_config.model_path),
            "model_sha256": detector_config.model_sha256,
            "input_size": list(detector_config.input_size),
            "resize_mode": detector_config.resize_mode,
            "has_objectness": detector_config.has_objectness,
            "class_activation": detector_config.class_activation,
            "confidence_threshold": detector_config.confidence_threshold,
            "nms_iou_threshold": detector_config.nms_iou_threshold,
            "providers": list(detector_config.providers),
            "intra_op_threads": detector_config.intra_op_threads,
        },
        "digests": {
            "detections_sha256": detection_digest,
            "temporal_sha256": temporal_digest,
            "scheduler_sha256": scheduler_digest,
            "spike_counts_sha256": spike_digest,
        },
        "temporal": temporal,
        "detection_records": detection_records,
        "tracking_records": tracking,
        "track_summaries": track_summaries,
        "events": events,
        "scheduler": {
            "n_frames": len(temporal),
            "n_stimulated_neurons": int(scheduler.stimulated_indices.size),
            "horizon_ms": scheduler.horizon_ms,
            "memory_bytes": int(scheduler.memory_bytes),
            "signature_sha256": scheduler_digest,
            "statistics": scheduler.input_statistics(),
            "features": feature_names,
            "peak_current_pa": {
                feature: round(float(drive[:, index].max()), 6)
                for index, feature in enumerate(feature_names)
            },
            "mean_current_pa": {
                feature: round(float(drive[:, index].mean()), 6)
                for index, feature in enumerate(feature_names)
            },
            "n_samples": int(drive.shape[0]),
        },
        "simulation": {
            **simulation,
            "spikes_total": total,
            "spikes_stimulated": stimulated,
            "spikes_unstimulated": total - stimulated,
            "spiking_neurons_stimulated": spiking_stimulated,
            "spiking_neurons_unstimulated": spiking_unstimulated,
            "stimulated_neuron_count": int(stimulated_indices.size),
            "stimulated_active_fraction": round(
                spiking_stimulated / max(1, int(stimulated_indices.size)), 6
            ),
            "stimulated_neuron_fraction": round(
                stimulated / max(1, total), 6
            ),
        },
    }
    return payload


def _oob_overflow(detail: str) -> float | None:
    match = re.search(r"box lies ([0-9.]+) px outside", detail)
    return float(match.group(1)) if match is not None else None


def _aggregate_detection(records: list[dict]) -> dict:
    reasons = Counter()
    classes = Counter()
    for record in records:
        for rejection in record["rejected"]:
            reasons[rejection["reason"]] += 1
        for detection in record["accepted"]:
            classes[detection["class_name"]] += 1
    clipped = [
        detection
        for record in records
        for detection in record["accepted"]
        if detection["clamped"]
    ]
    return {
        "n_frames": len(records),
        "n_candidates": sum(record["n_candidates"] for record in records),
        "n_decoded_above_threshold": sum(
            record["n_decoded_above_threshold"] for record in records
        ),
        "n_accepted": sum(record["n_accepted"] for record in records),
        "n_rejected": sum(record["n_rejected"] for record in records),
        "n_clipped": len(clipped),
        "rejection_reasons": dict(sorted(reasons.items())),
        "accepted_by_class": dict(sorted(classes.items())),
        "clip_distances_pixels": sorted(
            detection["clip_distance_pixels"] for detection in clipped
        ),
        "max_clip_distance_pixels": max(
            (record["max_clip_distance_pixels"] for record in records),
            default=0.0,
        ),
        "detector_call_ms": _summary(
            record["detector_call_ms"] for record in records
        ),
        "preprocess_ms": _summary(
            record["preprocess_ms"] for record in records
        ),
        "session_run_ms": _summary(
            record["session_run_ms"] for record in records
        ),
        "postprocess_ms": _summary(
            record["postprocess_ms"] for record in records
        ),
        "frames_with_no_accepted": [
            record["frame_id"]
            for record in records
            if record["n_accepted"] == 0
        ],
    }


def _aggregate_tracking(temporal) -> dict:
    all_ids = sorted(
        {track.track_id for frame in temporal for track in frame.tracks}
    )
    created = [item.track_id for frame in temporal for item in frame.created]
    occluded = [item.track_id for frame in temporal for item in frame.occluded]
    lost = [item.track_id for frame in temporal for item in frame.lost]
    duplicates = [
        duplicate.as_dict()
        for frame in temporal
        for duplicate in frame.duplicates
    ]
    states = Counter(
        track.state.value for frame in temporal for track in frame.tracks
    )
    lifecycles = Counter(
        track.lifecycle.value for frame in temporal for track in frame.tracks
    )
    return {
        "n_frames": len(temporal),
        "n_track_ids": len(all_ids),
        "track_ids": all_ids,
        "track_observations": sum(len(frame.tracks) for frame in temporal),
        "created_events": len(created),
        "created_track_ids": sorted(set(created)),
        "occluded_observations": len(occluded),
        "lost_events": len(lost),
        "lost_track_ids": sorted(set(lost)),
        "duplicates_suppressed": len(duplicates),
        "duplicate_records": duplicates,
        "state_observations": dict(sorted(states.items())),
        "lifecycle_observations": dict(sorted(lifecycles.items())),
        "frames_with_no_tracks": [
            frame.frame_id for frame in temporal if not frame.tracks
        ],
        "id_switch_measurement": (
            "not measurable: no annotated object identities exist, and "
            "class-aware association prevents cross-class track switching by "
            "construction. Tracker ids are not object identities."
        ),
    }


def _aggregate_temporal(temporal, events: list[dict], track_summaries) -> dict:
    event_counts = Counter(event["event"] for event in events)
    event_classes = Counter(event["class_name"] for event in events)
    lane_changes = sum(
        len(item["observable_lane_changes"]) for item in track_summaries
    )
    unavailable = {
        "player": "the v15 schema declares no player class",
        "coins": "the v15 schema declares no coin class",
        "jumping": "not observable; no action or jump state is inferred",
        "rolling": "not observable; no action or roll state is inferred",
        "player_movement": "no player detections; no movement is invented",
        "metric_distance": "distance is an uncalibrated bottom-edge proxy",
        "occlusion": "inferred from missed associations, not observed",
    }
    return {
        "n_frames": len(temporal),
        "n_events": len(events),
        "events_by_type": dict(sorted(event_counts.items())),
        "events_by_class": dict(sorted(event_classes.items())),
        "n_pulse_events": sum(1 for event in events if event["is_pulse"]),
        "observable_lane_changes": lane_changes,
        "n_gap_frames": sum(1 for frame in temporal if frame.is_gap),
        "final_game_state": {
            "time_ms": round(temporal[-1].time_ms, 4),
            "features": dict(temporal[-1].state.features()),
        },
        "unrepresented_tracks": [
            frame.unrepresented_tracks for frame in temporal
        ],
        "track_summaries": track_summaries,
        "unavailable_modalities": unavailable,
    }


def _compare_runs(first: dict, second: dict) -> dict:
    differences = []
    for key in (
        "detections_sha256",
        "temporal_sha256",
        "scheduler_sha256",
        "spike_counts_sha256",
    ):
        if first["digests"][key] != second["digests"][key]:
            differences.append(key)
    return {
        "identical": not differences,
        "differences": differences,
        "detections_sha256": [
            first["digests"]["detections_sha256"],
            second["digests"]["detections_sha256"],
        ],
        "temporal_sha256": [
            first["digests"]["temporal_sha256"],
            second["digests"]["temporal_sha256"],
        ],
        "scheduler_sha256": [
            first["digests"]["scheduler_sha256"],
            second["digests"]["scheduler_sha256"],
        ],
        "spike_counts_sha256": [
            first["digests"]["spike_counts_sha256"],
            second["digests"]["spike_counts_sha256"],
        ],
        "spikes_total": [
            first["simulation"]["spikes_total"],
            second["simulation"]["spikes_total"],
        ],
        "metadata_sha256": {
            "model": first["detector"]["model_sha256"],
            "model_repeated": second["detector"]["model_sha256"],
            "model_match": (
                first["detector"]["model_sha256"]
                == second["detector"]["model_sha256"]
            ),
        },
    }


def _input_hashes(sequence: dict) -> dict:
    files = {
        "README.md": PROJECT_ROOT / "README.md",
        "split_manifest": MANIFEST,
        "connectome_npz": CONNECTOME,
        "detector_config": DETECTOR_CONFIG,
        "perception_config": PERCEPTION_CONFIG,
        "sensory_config": SENSORY_CONFIG,
        "simulation_config": SIMULATION_CONFIG,
        "neuron_config": NEURON_CONFIG,
        "model": (
            PROJECT_ROOT / "models" / "YOLO11" / "deployment"
            / "yolo11n_v1_deployment" / "best.onnx"
        ),
    }
    return {
        name: {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(path),
        }
        for name, path in files.items()
    }


def run(seed: int = SEED, smoke_only: bool = False) -> dict:
    started = time.perf_counter()
    sequence = discover_frames()
    frames = sequence["frames"]
    print(
        f"sequence {GROUP} frames {FRAME_START}-{FRAME_END} "
        f"({len(frames)} frames, {sequence['split_folder_counts']})",
        flush=True,
    )

    base_config = load_perception_config(PERCEPTION_CONFIG)
    if base_config.validation.bounds_tolerance_pixels != 0.0:
        raise RuntimeError("production bounds tolerance is not 0.0")

    detector, detector_config = _build_detector()
    detector_description = detector.describe()

    # Smoke: production tolerance versus the experiment tolerance.
    smoke_frames = frames[:SMOKE_FRAMES]
    smoke = {}
    for tolerance in (0.0, BOUNDS_TOLERANCE_PIXELS):
        config = _experiment_perception_config(tolerance)
        pipeline = PerceptionPipeline(config, detector)
        observations, records = _process_frames(
            pipeline, smoke_frames, tolerance
        )
        smoke[f"tolerance_{tolerance:.1f}"] = {
            "bounds_tolerance_pixels": tolerance,
            "frames": [record["frame_id"] for record in records],
            "aggregate": _aggregate_detection(records),
            "per_frame": [
                {
                    "frame_id": record["frame_id"],
                    "n_candidates": record["n_candidates"],
                    "n_accepted": record["n_accepted"],
                    "n_rejected": record["n_rejected"],
                    "n_clipped": record["n_clipped"],
                    "rejection_reasons": sorted(
                        {item["reason"] for item in record["rejected"]}
                    ),
                }
                for record in records
            ],
        }
        del observations
        gc.collect()
    smoke["production_tolerance"] = 0.0
    smoke["experiment_tolerance"] = BOUNDS_TOLERANCE_PIXELS

    if smoke_only:
        return {
            "phase": "3B.2C",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "verdict": "SMOKE ONLY",
            "runtime_s": round(time.perf_counter() - started, 3),
            "sequence": {
                "group": sequence["group"],
                "frame_start": FRAME_START,
                "frame_end": FRAME_END,
                "n_frames": len(frames),
                "image_size": sequence["image_size"],
                "split_folder_counts": sequence["split_folder_counts"],
                "split_assignment": "valid (fixed grouped split)",
                "logo_fold": sequence["logo_fold"],
                "sequence_sha256": sequence["sequence_sha256"],
            },
            "model": {
                **detector_description,
                "config": {
                    "model_path": str(detector_config.model_path),
                    "model_sha256": detector_config.model_sha256,
                    "input_size": list(detector_config.input_size),
                    "confidence_threshold": detector_config.confidence_threshold,
                    "nms_iou_threshold": detector_config.nms_iou_threshold,
                },
            },
            "smoke": smoke,
            "limitations": LIMITATIONS,
        }

    # Fixed connectome and simulator parameters for both repeated runs.
    simulation_config = _load_yaml(SIMULATION_CONFIG)
    neuron_config = _load_yaml(NEURON_CONFIG)
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(simulation_config["synapse"])
    setup = prepare_setup(
        load_connectome(PROJECT_ROOT / simulation_config["connectome"]["path"]),
        load_config(SENSORY_CONFIG),
    )
    graph = setup.mapping.graph
    print(
        f"connectome nodes={graph.n_nodes} edges={graph.n_edges} "
        f"stimulated={setup.mapping.stimulated_indices().size}",
        flush=True,
    )

    print("run A", flush=True)
    first = _execute_chain(
        frames,
        BOUNDS_TOLERANCE_PIXELS,
        seed,
        setup,
        neuron_params,
        synapse_params,
    )
    print("run B", flush=True)
    second = _execute_chain(
        frames,
        BOUNDS_TOLERANCE_PIXELS,
        seed,
        setup,
        neuron_params,
        synapse_params,
    )

    reproducibility = _compare_runs(first, second)
    reproducibility["seed"] = seed
    reproducibility["config"] = {
        "bounds_tolerance_pixels": BOUNDS_TOLERANCE_PIXELS,
        "temporal_tracking": asdict(TRACKING),
        "temporal_features": asdict(FEATURES),
        "scheduler": TemporalSchedulerConfig().as_dict(),
        "dt_ms": setup.dt_ms,
        "duration_ms": first["simulation"]["duration_ms"],
    }
    reproducibility["note"] = (
        "Both runs created a new ONNX session, perception pipeline, tracker, "
        "temporal encoder, scheduler and simulator from the same inputs, "
        "configuration and seed."
    )

    detection = _aggregate_detection(first["detection_records"])
    tracking = _aggregate_tracking(first["temporal"])
    temporal = _aggregate_temporal(
        first["temporal"], first["events"], first["track_summaries"]
    )

    checks = {
        "sequence_contiguous": [item["frame_number"] for item in frames]
        == list(range(FRAME_START, FRAME_END + 1)),
        "all_frames_in_validation_split": all(
            item["split_assignment"] == "valid" for item in frames
        ),
        "single_recording": len({item["image_name"].split("_mp4-")[0] for item in frames})
        == 1,
        "model_sha_verified": (
            detector_description["model_sha256"]
            == detector_config.model_sha256
        ),
        "production_tolerance_unchanged": (
            base_config.validation.bounds_tolerance_pixels == 0.0
        ),
        "no_box_beyond_tolerance_accepted": all(
            record["max_clip_distance_pixels"] <= BOUNDS_TOLERANCE_PIXELS
            for record in first["detection_records"]
        ),
        "rejected_boxes_exceed_tolerance": all(
            _oob_overflow(rejection["detail"]) is not None
            and _oob_overflow(rejection["detail"]) > BOUNDS_TOLERANCE_PIXELS
            for record in first["detection_records"]
            for rejection in record["rejected"]
            if rejection["reason"] == "out_of_bounds"
        ),
        "all_frames_processed": len(first["detection_records"]) == len(frames),
        "scheduler_targets_mapped_neurons": (
            first["scheduler"]["n_stimulated_neurons"]
            == int(setup.mapping.stimulated_indices().size)
        ),
        "simulation_finite": bool(
            first["simulation"]["diagnostics"].get("finite_state", False)
        ),
        "simulation_within_spike_capacity": (
            first["simulation"]["spikes_total"] < MAX_RECORDED_SPIKES
        ),
        "runs_identical": reproducibility["identical"],
    }
    critical = (
        "sequence_contiguous",
        "all_frames_in_validation_split",
        "single_recording",
        "model_sha_verified",
        "no_box_beyond_tolerance_accepted",
        "all_frames_processed",
        "scheduler_targets_mapped_neurons",
        "simulation_finite",
    )
    if not all(checks[name] for name in critical):
        verdict = "BLOCKED"
    else:
        verdict = "PASS WITH LIMITATIONS"

    protected = _input_hashes(sequence)
    payload = {
        "phase": "3B.2C",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "runtime_s": round(time.perf_counter() - started, 3),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pid_rss_mb": round(
                psutil.Process().memory_info().rss / 1024**2, 3
            ),
        },
        "sequence": {
            "group": sequence["group"],
            "frame_start": FRAME_START,
            "frame_end": FRAME_END,
            "n_frames": len(frames),
            "image_size": sequence["image_size"],
            "split_folder_counts": sequence["split_folder_counts"],
            "split_assignment": "valid (fixed grouped split)",
            "logo_fold": sequence["logo_fold"],
            "group_info": sequence["group_info"],
            "timestamp_policy": (
                "30 fps assumed; timestamps synthesized as local frame index "
                "* 1000/30 ms because images carry no timestamps"
            ),
            "frames": frames,
            "sequence_sha256": sequence["sequence_sha256"],
            "input_hashes": protected,
        },
        "model": {
            **first["detector"],
            "model_sha256_verified": (
                first["detector"]["model_sha256"]
                == detector_config.model_sha256
            ),
            "config": first["detector_config"],
        },
        "boundary_policy": {
            "production_tolerance_pixels": 0.0,
            "experiment_tolerance_pixels": BOUNDS_TOLERANCE_PIXELS,
            "rules": {
                "inside_or_exact_boundary": "accepted without clipping",
                "outside_by_at_most_1px": "accepted and clipped",
                "outside_by_more_than_1px": "rejected as out_of_bounds",
                "negative_coordinates": (
                    "rejected when the overflow exceeds the tolerance"
                ),
                "degenerate_before_clipping": "rejected",
                "degenerate_after_clipping": "rejected",
            },
            "recorded_fields": [
                "raw_box_pixels",
                "clipped_box_pixels",
                "clip_distance_pixels",
            ],
            "justification": (
                "Letterbox inversion and floating-point rounding can place a "
                "true edge a fraction of a pixel outside the processed image. "
                "A 1 px tolerance absorbs that numerical artifact while any "
                "larger overflow still fails closed. Both boxes are retained "
                "so clipping is auditable rather than silent."
            ),
            "production_unchanged": True,
        },
        "smoke": smoke,
        "detection": detection,
        "detection_frames": first["detection_records"],
        "tracking": tracking,
        "tracking_frames": first["tracking_records"],
        "temporal": temporal,
        "events": first["events"],
        "scheduler": first["scheduler"],
        "simulation": first["simulation"],
        "reproducibility": reproducibility,
        "checks": checks,
        "limitations": LIMITATIONS,
        "action_selection": "none; the chain ends at sensory current injection",
        "claims": {
            "gameplay_success": False,
            "biological_perception": False,
            "annotated_identity_tracking": False,
            "independent_test_set": False,
            "plasticity": False,
            "detector_retrained": False,
        },
    }
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="run the 10-frame tolerance smoke without the neural simulation",
    )
    args = parser.parse_args(argv)

    payload = run(seed=args.seed, smoke_only=args.smoke_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8"
    )
    if args.smoke_only:
        print(
            f"wrote {args.output} | smoke only | "
            f"frames={payload['sequence']['n_frames']} | "
            f"0.0px accepted="
            f"{payload['smoke']['tolerance_0.0']['aggregate']['n_accepted']} "
            f"1.0px accepted="
            f"{payload['smoke']['tolerance_1.0']['aggregate']['n_accepted']}"
        )
        return 0
    passed = sum(1 for value in payload["checks"].values() if value)
    print(
        f"wrote {args.output} | verdict={payload['verdict']} "
        f"frames={payload['sequence']['n_frames']} "
        f"accepted={payload['detection']['n_accepted']} "
        f"tracks={payload['tracking']['n_track_ids']} "
        f"events={payload['temporal']['n_events']} "
        f"spikes={payload['simulation']['spikes_total']} "
        f"checks={passed}/{len(payload['checks'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
