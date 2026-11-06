#!/usr/bin/env python3
"""Phase 3C temporal calibration on ten synthetic sequence families.

This is a measurement harness for the temporal layer only: synthetic
detections go through the real tracker, temporal feature encoder and
scheduler, and the resulting features/events are compared against the
synthetic ground truth. No detector, dataset, image or connectome is used.

The report is machine-readable JSON. It is calibration evidence, not a
biological result and not an independent test-set estimate.

Usage::

    python experiments/phase_3c/temporal_calibration.py --seed 20261106
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from perception.config import ClassRole, GameStateRole  # noqa: E402
from perception.geometry import BoundingBox, NormalizedBox  # noqa: E402
from perception.observations import (  # noqa: E402
    FrameObservations,
    VisualObservation,
)
from perception.temporal import (  # noqa: E402
    Lifecycle,
    TemporalConfig,
    TemporalFeatureConfig,
    TemporalSequenceProcessor,
)
from perception.tracking import TrackState, TrackingConfig  # noqa: E402
from sensory.population_encoder import build_encoders  # noqa: E402
from sensory.temporal_scheduler import (  # noqa: E402
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

DEFAULT_SEED = 20261106
DEFAULT_TRIALS = 5
DT_MS = 1000.0 / 30.0

TRACKING = TrackingConfig(
    min_hits=2,
    max_age=2,
    iou_threshold=0.3,
    gate_distance=0.35,
    duplicate_iou=0.75,
    history_limit=32,
)
FEATURES = TemporalFeatureConfig(
    distance_change_threshold=0.02,
    confidence_floor=0.25,
    event_cooldown_frames=2,
    frame_interval_ms=DT_MS,
    gap_threshold_ms=100.0,
)
SCHEDULER_CONFIG = TemporalSchedulerConfig(
    max_hold_ms=250.0,
    pulse_gain=0.5,
    pulse_decay_ms=150.0,
)

EVENT_TYPES = (
    Lifecycle.APPEARED,
    Lifecycle.APPROACHING,
    Lifecycle.RECEDING,
    Lifecycle.OCCLUDED,
    Lifecycle.DISAPPEARED,
)

TRAIN = (0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)
OBSTACLE_LOW = (1, "jump-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_LOW)
OBSTACLE_HIGH = (2, "high-barrier", ClassRole.OBSTACLE, GameStateRole.OBSTACLE_HIGH)
COIN = (3, "coin", ClassRole.COIN, GameStateRole.UNSUPPORTED)

ENCODER_CONFIG = {
    "player_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "player_speed": {"kind": "gaussian", "n_neurons": 3},
    "jumping": {"kind": "boolean", "n_neurons": 1},
    "rolling": {"kind": "boolean", "n_neurons": 1},
    "obstacle_present": {"kind": "boolean", "n_neurons": 1},
    "obstacle_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "obstacle_distance": {"kind": "gaussian", "n_neurons": 4},
    "obstacle_type": {"kind": "boolean", "n_neurons": 1},
    "train_present": {"kind": "boolean", "n_neurons": 1},
    "train_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "train_distance": {"kind": "gaussian", "n_neurons": 4},
    "coin_present": {"kind": "boolean", "n_neurons": 1},
    "coin_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "coin_distance": {"kind": "gaussian", "n_neurons": 4},
}
ENCODERS = build_encoders(ENCODER_CONFIG)
CURRENTS = {feature: 200.0 for feature in ENCODERS}


class _Population:
    def __init__(self, indices) -> None:
        self._indices = np.asarray(indices, dtype=np.int64)
        self.plan = SimpleNamespace(
            groups=[("default", "pool", self._indices.size)]
        )
        self.root_ids = {"default": self._indices + 10_000}

    def size(self) -> int:
        return int(self._indices.size)


class _Mapping:
    def __init__(self) -> None:
        self.populations = {}
        offset = 0
        for name in ENCODERS:
            size = ENCODERS[name].spec.output_size
            self.populations[name] = _Population(range(offset, offset + size))
            offset += size

    def indices(self, feature):
        return self.populations[feature]._indices

    def size(self, feature):
        return self.populations[feature].size()

    def stimulated_indices(self):
        return np.unique(
            np.concatenate(
                [population._indices for population in self.populations.values()]
            )
        )


MAPPING = _Mapping()


@dataclass(frozen=True)
class DetectionSpec:
    object_index: int
    kind: tuple
    lane: int
    box: tuple[float, float, float, float]
    confidence: float = 0.9


@dataclass(frozen=True)
class FrameSpec:
    time_ms: float
    detections: tuple[DetectionSpec, ...] = ()
    truth_boxes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ExpectedEvent:
    event: Lifecycle
    frame_index: int
    time_ms: float
    origin_frame: int
    origin_time_ms: float
    object_key: int


@dataclass
class SequenceResult:
    outputs: list
    expected: dict
    emitted: list
    matched: dict
    emitted_counts: dict
    direction_correct: int
    direction_total: int
    direction_by_label: dict
    visible_frames: int
    matched_visible_frames: int
    id_switches: int


def _box(y2: float, center_x: float = 0.5, width: float = 0.2, height: float = 0.2):
    y2 = float(min(0.98, max(0.21, y2)))
    return (
        center_x - width / 2.0,
        y2 - height,
        center_x + width / 2.0,
        y2,
    )


def _grid_box(index: int):
    center_x = 0.1 + (index % 3) * 0.4
    center_y = 0.1 + ((index // 3) % 3) * 0.4
    return (
        center_x - 0.05,
        center_y - 0.05,
        center_x + 0.05,
        center_y + 0.05,
    )


def _times(count: int, dt_ms: float = DT_MS):
    return [index * dt_ms for index in range(count)]


def _frame(time_ms, truth_objects, detected=None, false_positives=()):
    detections = []
    for key, (kind, lane, box) in truth_objects.items():
        if detected is None or key in detected:
            detections.append(DetectionSpec(key, kind, lane, box, 0.9))
    detections.extend(false_positives)
    return FrameSpec(
        time_ms=float(time_ms),
        detections=tuple(detections),
        truth_boxes={key: value[2] for key, value in truth_objects.items()},
    )


# --------------------------------------------------------------------------
# Ten synthetic families
# --------------------------------------------------------------------------


def _static(rng, trial):
    lane = trial % 3
    center_x = (lane + 0.5) / 3.0
    box = _box(0.45 + 0.01 * (trial % 3), center_x)
    return [
        _frame(time_ms, {0: (TRAIN, lane, box)})
        for time_ms in _times(20)
    ]


def _approaching(rng, trial):
    y_start = 0.25 + 0.02 * (trial % 3)
    rate = 0.035 + 0.004 * trial
    frames = []
    for i, time_ms in enumerate(_times(22)):
        box = _box(min(0.95, y_start + rate * i))
        frames.append(_frame(time_ms, {0: (TRAIN, 1, box)}))
    return frames


def _receding(rng, trial):
    y_start = 0.85 - 0.02 * (trial % 3)
    rate = 0.035 + 0.004 * trial
    frames = []
    for i, time_ms in enumerate(_times(22)):
        box = _box(max(0.25, y_start - rate * i))
        frames.append(_frame(time_ms, {0: (TRAIN, 1, box)}))
    return frames


def _sudden_appearance(rng, trial):
    start = 3 + (trial % 3)
    box = _box(0.45 + 0.02 * trial)
    frames = []
    for i, time_ms in enumerate(_times(22)):
        truth = {} if i < start else {0: (TRAIN, 1, box)}
        frames.append(_frame(time_ms, truth))
    return frames


def _disappearance(rng, trial):
    visible_until = 9 + (trial % 3)
    box = _box(0.45)
    frames = []
    for i, time_ms in enumerate(_times(24)):
        truth = {0: (TRAIN, 1, box)} if i <= visible_until else {}
        frames.append(_frame(time_ms, truth))
    return frames


def _two_objects(rng, trial):
    frames = []
    for i, time_ms in enumerate(_times(20)):
        train_box = _box(0.80 - 0.03 * i, 5.0 / 6.0)
        obstacle_box = _box(0.25 + 0.03 * i, 1.0 / 6.0)
        frames.append(
            _frame(
                time_ms,
                {
                    0: (TRAIN, 2, train_box),
                    1: (OBSTACLE_LOW, 0, obstacle_box),
                },
            )
        )
    return frames


def _temporary_occlusion(rng, trial):
    gap_start = 8 + (trial % 3)
    frames = []
    for i, time_ms in enumerate(_times(24)):
        box = _box(0.30 + 0.035 * i)
        detected = None
        if gap_start <= i < gap_start + 2:
            detected = set()
        frames.append(
            _frame(time_ms, {0: (OBSTACLE_LOW, 1, box)}, detected)
        )
    return frames


def _noisy_detections(rng, trial):
    frames = []
    for i, time_ms in enumerate(_times(20)):
        y2 = min(0.95, 0.30 + 0.028 * i)
        truth_box = _box(y2)
        jitter_x = rng.uniform(-0.006, 0.006)
        jitter_y = rng.uniform(-0.006, 0.006)
        noisy = (
            truth_box[0] + jitter_x,
            truth_box[1] + jitter_y,
            truth_box[2] + jitter_x,
            truth_box[3] + jitter_y,
        )
        detection = DetectionSpec(
            0, TRAIN, 1, noisy, rng.uniform(0.55, 0.95)
        )
        false_positives = []
        if i % 3 == 0:
            false_positives.append(
                DetectionSpec(1000 + i, TRAIN, 0, _grid_box(i), 0.6)
            )
        frames.append(
            FrameSpec(
                time_ms=float(time_ms),
                detections=(detection, *false_positives),
                truth_boxes={0: truth_box},
            )
        )
    return frames


def _irregular_intervals(rng, trial):
    intervals = (30.0, 60.0, 90.0, 120.0, 150.0)
    times = [0.0]
    for index in range(19):
        times.append(times[-1] + intervals[(index + trial) % len(intervals)])
    frames = []
    for time_ms in times:
        box = _box(0.28 + 0.00035 * time_ms)
        frames.append(_frame(time_ms, {0: (TRAIN, 1, box)}))
    return frames


def _missing_frames(rng, trial):
    frames = []
    for i, time_ms in enumerate(_times(30)):
        box = _box(0.30 + 0.025 * i)
        missing = (i % 7 in (3, 4)) or (i % 13 == 6)
        frames.append(
            _frame(
                time_ms,
                {0: (TRAIN, 1, box)},
                set() if missing else None,
            )
        )
    return frames


FAMILIES = {
    "static": ("A single stationary train; no motion events are expected.", _static),
    "approaching": ("A train whose distance proxy decreases each frame.", _approaching),
    "receding": ("A train whose distance proxy increases each frame.", _receding),
    "sudden_appearance": ("Empty frames followed by a persistent train.", _sudden_appearance),
    "disappearance": ("A confirmed train stops being detected.", _disappearance),
    "two_objects": ("A train and an obstacle moving in opposite directions.", _two_objects),
    "temporary_occlusion": ("A confirmed obstacle missed for two frames, then recovered.", _temporary_occlusion),
    "noisy_detections": ("Jittered boxes, variable confidence and distant false positives.", _noisy_detections),
    "irregular_intervals": ("Uneven timestamps including intervals above the gap threshold.", _irregular_intervals),
    "missing_frames": ("Periodic one- and two-frame detector dropouts.", _missing_frames),
}


# --------------------------------------------------------------------------
# Conversion and execution
# --------------------------------------------------------------------------


def _observations(spec: FrameSpec, index: int) -> FrameObservations:
    observations = []
    for detection in spec.detections:
        x1, y1, x2, y2 = detection.box
        observations.append(
            VisualObservation(
                object_index=detection.object_index,
                class_id=detection.kind[0],
                class_name=detection.kind[1],
                role=detection.kind[2],
                game_state_role=detection.kind[3],
                lane=detection.lane,
                bbox_screen=BoundingBox(
                    x1 * 300.0, y1 * 600.0, x2 * 300.0, y2 * 600.0
                ),
                bbox_normalized=NormalizedBox(x1, y1, x2, y2),
                confidence=float(detection.confidence),
                frame_id=f"frame-{index}",
                timestamp_ms=float(spec.time_ms),
                distance_proxy=round(1.0 - y2, 6),
            )
        )
    return FrameObservations(
        frame_id=f"frame-{index}",
        timestamp_ms=float(spec.time_ms),
        source_path=None,
        original_size=(300, 600),
        viewport_size=(300, 600),
        observations=tuple(observations),
    )


def run_sequence(frames: list[FrameSpec]):
    processor = TemporalSequenceProcessor(
        TemporalConfig(tracking=TRACKING, features=FEATURES)
    )
    return [
        processor.process(_observations(spec, index))
        for index, spec in enumerate(frames)
    ]


def _visible(spec: FrameSpec, key: int) -> bool:
    if key not in spec.truth_boxes:
        return False
    return any(item.object_index == key for item in spec.detections)


def _direction_by_frame(frames: list[FrameSpec], key: int) -> dict[int, str]:
    directions: dict[int, str] = {}
    previous = None
    threshold = FEATURES.distance_change_threshold
    for index, spec in enumerate(frames):
        if not _visible(spec, key):
            continue
        box = spec.truth_boxes[key]
        if previous is not None:
            delta = (1.0 - box[3]) - (1.0 - previous[3])
            if delta <= -threshold:
                directions[index] = "approach"
            elif delta >= threshold:
                directions[index] = "recede"
            else:
                directions[index] = "persist"
        previous = box
    return directions


def _expected_event(frames, kind, index, origin, key) -> ExpectedEvent:
    return ExpectedEvent(
        event=kind,
        frame_index=index,
        time_ms=float(frames[index].time_ms),
        origin_frame=origin,
        origin_time_ms=float(frames[origin].time_ms),
        object_key=key,
    )


def expected_events(frames: list[FrameSpec], truth_keys) -> dict:
    expected = {kind: [] for kind in EVENT_TYPES}
    directions = {key: _direction_by_frame(frames, key) for key in truth_keys}
    for key in truth_keys:
        visible = [_visible(spec, key) for spec in frames]

        confirmed = False
        run = 0
        run_start = 0
        misses = 0
        for index, seen in enumerate(visible):
            if seen:
                if run == 0:
                    run_start = index
                run += 1
                misses = 0
                if not confirmed and run >= TRACKING.min_hits:
                    confirmed = True
                    expected[Lifecycle.APPEARED].append(
                        _expected_event(
                            frames, Lifecycle.APPEARED, index, run_start, key
                        )
                    )
            else:
                run = 0
                if confirmed:
                    misses += 1
                    if misses == 1:
                        expected[Lifecycle.OCCLUDED].append(
                            _expected_event(
                                frames, Lifecycle.OCCLUDED, index, index, key
                            )
                        )
                    if misses == TRACKING.max_age + 1:
                        expected[Lifecycle.DISAPPEARED].append(
                            _expected_event(
                                frames,
                                Lifecycle.DISAPPEARED,
                                index,
                                index - TRACKING.max_age,
                                key,
                            )
                        )
                        confirmed = False
                else:
                    misses = 0

        confirmed = False
        run = 0
        misses = 0
        quiet = 0
        last_direction = None
        last_event_frame = None
        for index, seen in enumerate(visible):
            if seen:
                run += 1
                misses = 0
                newly_confirmed = False
                if not confirmed and run >= TRACKING.min_hits:
                    confirmed = True
                    newly_confirmed = True
                if not confirmed or newly_confirmed:
                    last_direction = None
                    quiet = 0
                    continue
                direction = directions[key].get(index)
                if direction in ("approach", "recede"):
                    quiet = 0
                    kind = (
                        Lifecycle.APPROACHING
                        if direction == "approach"
                        else Lifecycle.RECEDING
                    )
                    if last_direction != direction:
                        cooldown_ok = (
                            last_event_frame is None
                            or index - last_event_frame >= FEATURES.event_cooldown_frames
                        )
                        if cooldown_ok:
                            expected[kind].append(
                                _expected_event(
                                    frames, kind, index, index, key
                                )
                            )
                            last_event_frame = index
                    last_direction = direction
                else:
                    # A short quiet step is a threshold dip inside an ongoing
                    # approach/recede, not the end of the episode.
                    quiet += 1
                    if quiet > FEATURES.event_cooldown_frames:
                        last_direction = None
            else:
                run = 0
                quiet = 0
                last_direction = None
                if confirmed:
                    misses += 1
                    if misses == TRACKING.max_age + 1:
                        confirmed = False
                else:
                    misses = 0
    return expected


def _match_events(expected, emitted, tolerance_frames: int = 2):
    matched = {kind: [] for kind in EVENT_TYPES}
    used: set[int] = set()
    for kind in EVENT_TYPES:
        candidates: dict[int, list] = {}
        for index, (event, object_key) in enumerate(emitted):
            if event.event is kind and object_key is not None:
                candidates.setdefault(object_key, []).append((index, event))
        for item in sorted(expected[kind], key=lambda value: value.frame_index):
            best = None
            for index, event in candidates.get(item.object_key, []):
                if index in used:
                    continue
                difference = abs(event.frame_index - item.frame_index)
                if difference > tolerance_frames:
                    continue
                rank = (difference, event.frame_index, index)
                if best is None or rank < best[0]:
                    best = (rank, index, event)
            if best is not None:
                used.add(best[1])
                matched[kind].append((item, best[2]))
    return matched, used


def evaluate_sequence(frames: list[FrameSpec]) -> SequenceResult:
    outputs = run_sequence(frames)
    truth_keys = sorted(
        {key for spec in frames for key in spec.truth_boxes}
    )
    expected = expected_events(frames, truth_keys)
    directions = {key: _direction_by_frame(frames, key) for key in truth_keys}

    track_object: dict[int, int] = {}
    object_last_track: dict[int, int] = {}
    emitted = []
    visible_frames = 0
    matched_visible_frames = 0
    id_switches = 0
    direction_correct = 0
    direction_total = 0
    direction_by_label = {
        label: {"correct": 0, "total": 0}
        for label in ("approach", "recede", "persist")
    }

    for output, spec in zip(outputs, frames):
        matches = {item.object_index: item.track_id for item in output.matches}
        for object_index, track_id in matches.items():
            track_object[track_id] = object_index

        for key in truth_keys:
            if not _visible(spec, key):
                continue
            visible_frames += 1
            if key in matches:
                matched_visible_frames += 1
                previous = object_last_track.get(key)
                if previous is not None and previous != matches[key]:
                    id_switches += 1
                object_last_track[key] = matches[key]

        for feature in output.tracks:
            if feature.state is not TrackState.CONFIRMED:
                continue
            if feature.distance_delta is None:
                continue
            key = track_object.get(feature.track_id)
            truth = directions.get(key, {}).get(output.frame_index)
            if truth is None:
                continue
            predicted = (
                "approach"
                if feature.approaching
                else "recede" if feature.receding else "persist"
            )
            direction_total += 1
            direction_by_label[truth]["total"] += 1
            if predicted == truth:
                direction_correct += 1
                direction_by_label[truth]["correct"] += 1

        for event in output.events:
            emitted.append((event, track_object.get(event.track_id)))

    matched, _used = _match_events(expected, emitted)
    emitted_counts = {kind: 0 for kind in Lifecycle}
    for event, _object in emitted:
        emitted_counts[event.event] += 1

    return SequenceResult(
        outputs=outputs,
        expected=expected,
        emitted=emitted,
        matched=matched,
        emitted_counts=emitted_counts,
        direction_correct=direction_correct,
        direction_total=direction_total,
        direction_by_label=direction_by_label,
        visible_frames=visible_frames,
        matched_visible_frames=matched_visible_frames,
        id_switches=id_switches,
    )


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _event_metrics(tp: int, fp: int, fn: int) -> dict:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and precision + recall > 0:
        f1 = round(
            2.0 * precision * recall / (precision + recall), 6
        )
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _percentiles(values) -> dict:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "mean": round(float(array.mean()), 6),
        "p50": round(float(np.percentile(array, 50)), 6),
        "p95": round(float(np.percentile(array, 95)), 6),
        "p99": round(float(np.percentile(array, 99)), 6),
        "max": round(float(array.max()), 6),
    }


def _scheduler_measurement(outputs, latency_sink: list | None = None) -> dict:
    started = time.perf_counter()
    schedule = TemporalActivationScheduler(
        MAPPING,
        ENCODERS,
        outputs,
        current_pa=CURRENTS,
        config=SCHEDULER_CONFIG,
    )
    construction_ms = (time.perf_counter() - started) * 1000.0
    last_time = float(outputs[-1].time_ms)
    times = np.arange(0.0, last_time + 1.0, 1.0)
    current = np.zeros(len(MAPPING.stimulated_indices()), dtype=np.float64)
    latencies_us = []
    for step, value in enumerate(times):
        start = time.perf_counter_ns()
        schedule.apply(step, float(value), current)
        latencies_us.append((time.perf_counter_ns() - start) / 1000.0)
    statistics_ = schedule.input_statistics()
    if latency_sink is not None:
        latency_sink.extend(latencies_us)
    return {
        "construction_ms": round(construction_ms, 6),
        "apply_us": _percentiles(latencies_us),
        "n_steps": int(times.size),
        "n_pulse_events": statistics_["n_pulse_events"],
        "max_frame_current_pa": statistics_["max_frame_current_pa"],
        "max_pulse_current_pa": statistics_["max_pulse_current_pa"],
        "memory_bytes": int(schedule.memory_bytes),
    }


def evaluate_family(
    name: str,
    generator,
    trials: int,
    seed: int,
    family_index: int,
    scheduler_samples: list | None = None,
):
    totals = {
        kind: {"expected": 0, "emitted": 0, "tp": 0, "latencies": []}
        for kind in EVENT_TYPES
    }
    direction_correct = 0
    direction_total = 0
    by_label = {
        label: {"correct": 0, "total": 0}
        for label in ("approach", "recede", "persist")
    }
    visible_frames = 0
    matched_visible_frames = 0
    id_switches = 0
    latencies_us = []
    constructions = []
    n_pulse_events = 0
    n_steps = 0
    uncertain_events = 0

    for trial in range(trials):
        rng = random.Random(seed + family_index * 1000 + trial)
        frames = generator(rng, trial)
        result = evaluate_sequence(frames)
        uncertain_events += result.emitted_counts[Lifecycle.UNCERTAIN]
        for kind in EVENT_TYPES:
            totals[kind]["expected"] += len(result.expected[kind])
            totals[kind]["emitted"] += result.emitted_counts[kind]
            pairs = result.matched[kind]
            totals[kind]["tp"] += len(pairs)
            for expected, event in pairs:
                totals[kind]["latencies"].append(
                    event.time_ms - expected.origin_time_ms
                )
        direction_correct += result.direction_correct
        direction_total += result.direction_total
        for label in by_label:
            by_label[label]["correct"] += result.direction_by_label[label]["correct"]
            by_label[label]["total"] += result.direction_by_label[label]["total"]
        visible_frames += result.visible_frames
        matched_visible_frames += result.matched_visible_frames
        id_switches += result.id_switches

        scheduler = _scheduler_measurement(result.outputs, latencies_us)
        constructions.append(scheduler["construction_ms"])
        n_pulse_events += scheduler["n_pulse_events"]
        n_steps += scheduler["n_steps"]

    if scheduler_samples is not None:
        scheduler_samples.extend(latencies_us)

    event_metrics = {}
    micro_tp = micro_fp = micro_fn = 0
    for kind in EVENT_TYPES:
        counts = totals[kind]
        tp = counts["tp"]
        fp = counts["emitted"] - tp
        fn = counts["expected"] - tp
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        event_metrics[kind.value] = _event_metrics(tp, fp, fn)

    return {
        "description": FAMILIES[name][0],
        "n_sequences": trials,
        "event_counts": {
            "expected": {
                kind.value: totals[kind]["expected"] for kind in EVENT_TYPES
            },
            "emitted": {
                kind.value: totals[kind]["emitted"] for kind in EVENT_TYPES
            },
        },
        "event_metrics": event_metrics,
        "uncertainty_events": uncertain_events,
        "micro": _event_metrics(micro_tp, micro_fp, micro_fn),
        "event_latency_ms": {
            kind.value: _percentiles(totals[kind]["latencies"])
            for kind in EVENT_TYPES
        },
        "direction_accuracy": {
            "correct": direction_correct,
            "total": direction_total,
            "accuracy": _ratio(direction_correct, direction_total),
            "by_label": {
                label: {
                    "correct": value["correct"],
                    "total": value["total"],
                    "accuracy": _ratio(value["correct"], value["total"]),
                }
                for label, value in by_label.items()
            },
        },
        "tracking": {
            "visible_frames": visible_frames,
            "matched_visible_frames": matched_visible_frames,
            "continuity": _ratio(matched_visible_frames, visible_frames),
            "id_switches": id_switches,
        },
        "scheduler": {
            "construction_ms_mean": (
                round(statistics.fmean(constructions), 6) if constructions else None
            ),
            "construction_ms_max": (
                round(max(constructions), 6) if constructions else None
            ),
            "apply_us": _percentiles(latencies_us),
            "n_pulse_events": n_pulse_events,
            "n_steps": n_steps,
        },
    }


# --------------------------------------------------------------------------
# Adversarial checks
# --------------------------------------------------------------------------


def _adversarial_noise(seed: int) -> dict:
    frames = []
    for i, time_ms in enumerate(_times(40)):
        detection = DetectionSpec(1000 + i, TRAIN, 0, _grid_box(i), 0.8)
        frames.append(
            FrameSpec(time_ms=time_ms, detections=(detection,), truth_boxes={})
        )
    outputs = run_sequence(frames)
    emitted = [event.event for output in outputs for event in output.events]
    forbidden = [
        kind.value
        for kind in EVENT_TYPES
        if kind in emitted and kind is not Lifecycle.UNCERTAIN
    ]
    return {
        "expectation": "single-frame false positives never confirm or emit object events",
        "pass": not forbidden,
        "observed": {
            "event_counts": {
                kind.value: sum(1 for item in emitted if item is kind)
                for kind in Lifecycle
            },
            "forbidden_events": forbidden,
        },
    }


def _adversarial_duplicates(seed: int) -> dict:
    frames = []
    for index, time_ms in enumerate(_times(12)):
        box = _box(0.5)
        frames.append(
            FrameSpec(
                time_ms=time_ms,
                detections=(
                    DetectionSpec(0, TRAIN, 1, box, 0.9),
                    DetectionSpec(1, TRAIN, 1, box, 0.6),
                ),
                truth_boxes={0: box},
            )
        )
    result = evaluate_sequence(frames)
    appeared = [
        event
        for event, _object in result.emitted
        if event.event is Lifecycle.APPEARED
    ]
    track_ids = {event.track_id for event, _object in result.emitted}
    return {
        "expectation": "same-class duplicates are suppressed and create one track",
        "pass": len(appeared) == 1 and len(track_ids) == 1,
        "observed": {
            "appeared_events": len(appeared),
            "distinct_track_ids": sorted(track_ids),
            "matched_visible_frames": result.matched_visible_frames,
            "visible_frames": result.visible_frames,
        },
    }


def _adversarial_dropout(seed: int) -> dict:
    frames = []
    for i, time_ms in enumerate(_times(12)):
        box = _box(0.5)
        detected = None if i != 5 else set()
        frames.append(_frame(time_ms, {0: (TRAIN, 1, box)}, detected))
    result = evaluate_sequence(frames)
    counts = {
        kind.value: result.emitted_counts[kind] for kind in EVENT_TYPES
    }
    return {
        "expectation": "one miss is OCCLUDED, not DISAPPEARED, and the track id is stable",
        "pass": (
            counts["appeared"] == 1
            and counts["occluded"] == 1
            and counts["disappeared"] == 0
            and result.id_switches == 0
        ),
        "observed": {
            "event_counts": counts,
            "id_switches": result.id_switches,
        },
    }


def _adversarial_boundary_noise(seed: int) -> dict:
    frames = []
    for i, time_ms in enumerate(_times(20)):
        offset = 0.004 if i % 2 == 0 else -0.004
        frames.append(_frame(time_ms, {0: (TRAIN, 1, _box(0.5 + offset))}))
    result = evaluate_sequence(frames)
    counts = {
        "approaching": result.emitted_counts[Lifecycle.APPROACHING],
        "receding": result.emitted_counts[Lifecycle.RECEDING],
    }
    return {
        "expectation": "sub-threshold jitter does not emit direction events",
        "pass": counts["approaching"] == 0 and counts["receding"] == 0,
        "observed": counts,
    }


def _adversarial_timestamp_regression(seed: int) -> dict:
    processor = TemporalSequenceProcessor(
        TemporalConfig(tracking=TRACKING, features=FEATURES)
    )
    box = _box(0.5)
    spec = FrameSpec(
        time_ms=0.0,
        detections=(DetectionSpec(0, TRAIN, 1, box, 0.9),),
        truth_boxes={0: box},
    )
    processor.process(_observations(spec, 0))
    raised = False
    try:
        processor.process(_observations(spec, 1))
    except ValueError:
        raised = True
    return {
        "expectation": "non-increasing timestamps are rejected",
        "pass": raised,
        "observed": {"raised": raised},
    }


def _adversarial_stale_hold(seed: int) -> dict:
    box = _box(0.5)
    outputs = run_sequence(
        [
            FrameSpec(
                time_ms=0.0,
                detections=(DetectionSpec(0, TRAIN, 1, box, 0.9),),
                truth_boxes={0: box},
            ),
            FrameSpec(
                time_ms=DT_MS,
                detections=(DetectionSpec(0, TRAIN, 1, box, 0.9),),
                truth_boxes={0: box},
            ),
        ]
    )
    schedule = TemporalActivationScheduler(
        MAPPING,
        ENCODERS,
        outputs,
        current_pa=CURRENTS,
        config=TemporalSchedulerConfig(max_hold_ms=100.0),
    )
    last = float(outputs[-1].time_ms)
    held = schedule.feature_currents_at(last)["train_present"]
    stale = schedule.feature_currents_at(last + 150.0)["train_present"]
    return {
        "expectation": "drive is held up to max_hold_ms, then stops without new frames",
        "pass": held > 0.0 and stale == 0.0,
        "observed": {
            "at_last_frame_ms": held,
            "at_last_plus_150ms": stale,
            "max_hold_ms": 100.0,
        },
    }


ADVERSARIAL = {
    "noise_only": _adversarial_noise,
    "duplicate_detections": _adversarial_duplicates,
    "single_frame_dropout": _adversarial_dropout,
    "threshold_boundary_noise": _adversarial_boundary_noise,
    "timestamp_regression": _adversarial_timestamp_regression,
    "stale_frame_hold": _adversarial_stale_hold,
}


# --------------------------------------------------------------------------
# Calibration driver
# --------------------------------------------------------------------------


def _aggregate(families: dict, scheduler_samples: list | None = None) -> dict:
    micro_tp = micro_fp = micro_fn = 0
    per_type = {
        kind.value: {"tp": 0, "fp": 0, "fn": 0} for kind in EVENT_TYPES
    }
    direction_correct = direction_total = 0
    visible = matched = switches = 0
    for result in families.values():
        for kind in EVENT_TYPES:
            metrics = result["event_metrics"][kind.value]
            per_type[kind.value]["tp"] += metrics["tp"]
            per_type[kind.value]["fp"] += metrics["fp"]
            per_type[kind.value]["fn"] += metrics["fn"]
            micro_tp += metrics["tp"]
            micro_fp += metrics["fp"]
            micro_fn += metrics["fn"]
        direction_correct += result["direction_accuracy"]["correct"]
        direction_total += result["direction_accuracy"]["total"]
        visible += result["tracking"]["visible_frames"]
        matched += result["tracking"]["matched_visible_frames"]
        switches += result["tracking"]["id_switches"]
    return {
        "n_families": len(families),
        "n_sequences": sum(item["n_sequences"] for item in families.values()),
        "event_metrics": {
            kind: _event_metrics(values["tp"], values["fp"], values["fn"])
            for kind, values in per_type.items()
        },
        "micro": _event_metrics(micro_tp, micro_fp, micro_fn),
        "direction_accuracy": {
            "correct": direction_correct,
            "total": direction_total,
            "accuracy": _ratio(direction_correct, direction_total),
        },
        "tracking": {
            "visible_frames": visible,
            "matched_visible_frames": matched,
            "continuity": _ratio(matched, visible),
            "id_switches": switches,
        },
        "scheduler_apply_us": _percentiles(scheduler_samples or []),
    }


def calibrate(seed: int = DEFAULT_SEED, trials: int = DEFAULT_TRIALS) -> dict:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError("trials must be a positive integer")
    families = {}
    scheduler_samples: list = []
    for index, (name, (description, generator)) in enumerate(FAMILIES.items()):
        families[name] = evaluate_family(
            name, generator, trials, seed, index, scheduler_samples
        )
    adversarial = {
        name: check(seed + 5000 + index)
        for index, (name, check) in enumerate(ADVERSARIAL.items())
    }
    return {
        "seed": seed,
        "trials_per_family": trials,
        "config": {
            "tracking": asdict(TRACKING),
            "features": asdict(FEATURES),
            "scheduler": SCHEDULER_CONFIG.as_dict(),
            "currents_pa": dict(CURRENTS),
        },
        "families": families,
        "aggregate": _aggregate(families, scheduler_samples),
        "adversarial": adversarial,
    }


def _canonical(payload: dict) -> dict:
    """Remove wall-clock measurements so two runs can be compared exactly."""
    if isinstance(payload, dict):
        return {
            key: _canonical(value)
            for key, value in payload.items()
            if key
            not in {
                "construction_ms",
                "construction_ms_mean",
                "construction_ms_max",
                "apply_us",
                "scheduler_apply_us",
            }
        }
    if isinstance(payload, list):
        return [_canonical(value) for value in payload]
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT
        / "experiments"
        / "phase_3c"
        / "results"
        / "temporal_calibration.json",
    )
    args = parser.parse_args(argv)

    payload = calibrate(args.seed, args.trials)
    repeated = calibrate(args.seed, args.trials)
    payload["determinism"] = {
        "repeated": True,
        "identical": _canonical(payload) == _canonical(repeated),
    }
    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
    }
    payload["limitations"] = [
        "Sequences are synthetic and use idealized boxes; they are not "
        "detector output.",
        "Expected events implement the documented lifecycle and direction "
        "rules from ground-truth boxes. Agreement therefore checks rule "
        "consistency, not independently recorded game events.",
        "The direction hold suppresses re-emission after a quiet run no "
        "longer than the event cooldown; this is a configured debounce, not "
        "evidence about fly motion processing.",
        "Direction labels use the uncalibrated bottom-edge distance proxy.",
        "Tracking continuity counts the first tentative frame as unmatched "
        "and every frame of a gap as unmatched, so it cannot reach 1.0.",
        "A track that is lost for longer than max_age is re-created with a "
        "new identifier; those re-identifications are reported as ID "
        "switches rather than hidden.",
        "Scheduler latency measures Python scheduling overhead only; no "
        "connectome is simulated in this calibration.",
        "The ten families are a design probe, not a representative sample of "
        "the game.",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=1), encoding="utf-8"
    )
    aggregate = payload["aggregate"]
    print(
        f"wrote {args.output} | sequences={aggregate['n_sequences']} "
        f"micro_f1={aggregate['micro']['f1']} "
        f"direction_accuracy={aggregate['direction_accuracy']['accuracy']} "
        f"continuity={aggregate['tracking']['continuity']} "
        f"deterministic={payload['determinism']['identical']} "
        f"adversarial_passed="
        f"{sum(1 for item in payload['adversarial'].values() if item['pass'])}"
        f"/{len(payload['adversarial'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
