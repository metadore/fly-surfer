#!/usr/bin/env python3
"""Run real gameplay frames through the full sensory-to-neural chain.

    python -m experiments.phase_3b.run_pipeline                  # 10 recorded frames
    python -m experiments.phase_3b.run_pipeline --recording 100 149
    python -m experiments.phase_3b.run_pipeline --image frame.jpg

Chain: image -> YOLO11n ONNX -> PerceptionPipeline -> GameState -> Phase 3A
encoders -> SensoryMapping -> SensoryInputScheduler -> BrainSimulator ->
SpikeRecorder summary.

The detector is the deployed 14-class YOLO11n ONNX artifact. Distance is an
uncalibrated bottom-edge proxy, lane assignment is geometric, and spikes are
model output under configured assumptions, not measured biological activity.
Player, jump, roll and coin observations are unavailable in the v15 schema and
stay at their schema defaults; they are not inferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from perception.config import load_perception_config  # noqa: E402
from perception.detector_config import load_detector_config  # noqa: E402
from perception.inference import OnnxRuntimeDetector  # noqa: E402
from perception.pipeline import PerceptionPipeline  # noqa: E402
from sensory.input_scheduler import SensoryInputScheduler  # noqa: E402
from sensory.population_encoder import encode_state  # noqa: E402
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402

DETECTOR_CONFIG = PROJECT_ROOT / "configs" / "detector_config.yaml"
PERCEPTION_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "phase_3b"
    / "results"
    / "end_to_end_pipeline_demo.json"
)
FRAME_INTERVAL_MS = 1000.0 / 30.0
DEFAULT_RECORDING = (100, 109)

LIMITATIONS = [
    "The detector was trained on the same recording groups; no independent "
    "test split exists, so detections are not an accuracy estimate.",
    "The v15 schema has no player class, so player lane, jumping and rolling "
    "are unavailable and remain at schema defaults.",
    "No coin class is available; coin features remain absent.",
    "Lane and distance are image geometry; distance is an uncalibrated "
    "bottom-edge proxy, not metres.",
    "Spikes are model output from a fixed connectome with no plasticity. "
    "They are not measured biological activity and no action is selected.",
    "One mapping realization and one seed are used.",
]


@dataclass(frozen=True)
class FrameInput:
    """One image and the timestamp assigned to it."""

    path: Path
    frame_id: str
    timestamp_ms: float
    source: str


@dataclass(frozen=True)
class InputSelection:
    """Resolved frames plus a description of where they came from."""

    frames: list[FrameInput]
    info: dict


def _load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_inputs(
    images: list[str] | None = None,
    recording: tuple[int, int] | None = None,
) -> InputSelection:
    """Resolve image paths or an existing recording into ordered frames."""
    if images and recording:
        raise ValueError("provide either images or a recording, not both")
    if images:
        frames = []
        for index, raw in enumerate(images):
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = (Path.cwd() / path).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"image not found: {path}")
            frames.append(
                FrameInput(
                    path=path,
                    frame_id=path.stem,
                    timestamp_ms=index * FRAME_INTERVAL_MS,
                    source="image",
                )
            )
        return InputSelection(
            frames=frames,
            info={
                "kind": "image",
                "n_frames": len(frames),
                "frame_interval_ms": FRAME_INTERVAL_MS,
                "paths": [str(item.path) for item in frames],
                "sha256": [_sha256(item.path) for item in frames],
            },
        )

    from experiments.phase_3b.real_sequence_replay import discover_frames

    start, end = recording if recording is not None else DEFAULT_RECORDING
    payload = discover_frames(start, end)
    frames = [
        FrameInput(
            path=PROJECT_ROOT / item["image_path"],
            frame_id=f"{payload['group']}-{item['frame_number']:04d}",
            timestamp_ms=index * FRAME_INTERVAL_MS,
            source=f"recording:{payload['group']}",
        )
        for index, item in enumerate(payload["frames"])
    ]
    return InputSelection(
        frames=frames,
        info={
            "kind": "recording",
            "group": payload["group"],
            "start": start,
            "end": end,
            "n_frames": len(frames),
            "frame_interval_ms": FRAME_INTERVAL_MS,
            "paths": [item["image_path"] for item in payload["frames"]],
            "sha256": [item["image_sha256"] for item in payload["frames"]],
        },
    )


def build_detector() -> tuple[OnnxRuntimeDetector, object]:
    detector_config = load_detector_config(DETECTOR_CONFIG)
    schema = load_perception_config(PERCEPTION_CONFIG).schema
    detector = OnnxRuntimeDetector(detector_config, schema)
    if detector_config.model_sha256 is not None:
        if detector.model_sha256 != detector_config.model_sha256:
            raise RuntimeError("detector SHA-256 was not verified at load time")
    return detector, detector_config


def build_pipeline(
    detector, bounds_tolerance_px: float = 1.0
) -> PerceptionPipeline:
    """Build the existing perception pipeline with an in-memory tolerance.

    The production config keeps a zero-tolerance bounds rule. The 1 px
    experiment override is the same one used by the Phase 3B.2C replay and is
    recorded in the output; it changes no file.
    """
    base = load_perception_config(PERCEPTION_CONFIG)
    if base.validation.bounds_tolerance_pixels != 0.0:
        raise ValueError("production bounds tolerance is not 0.0")
    tolerance = float(bounds_tolerance_px)
    if tolerance < 0.0:
        raise ValueError("bounds tolerance must be non-negative")
    config = base
    if tolerance > 0.0:
        config = replace(
            base,
            validation=replace(
                base.validation, bounds_tolerance_pixels=tolerance
            ),
        )
    return PerceptionPipeline(config, detector)


def process_frame(pipeline: PerceptionPipeline, item: FrameInput):
    frame = pipeline.preprocessor.load(
        item.path, frame_id=item.frame_id, timestamp_ms=item.timestamp_ms
    )
    return pipeline.run(frame)


def build_schedule(
    setup,
    timeline: list[tuple[float, object]],
    *,
    duration_ms: float,
    transition_ms: float | None = None,
) -> SensoryInputScheduler:
    return SensoryInputScheduler(
        setup.mapping,
        setup.encoders,
        timeline,
        dt_ms=setup.dt_ms,
        duration_ms=duration_ms,
        current_pa=setup.amplitudes,
        transition_ms=(
            setup.transition_ms if transition_ms is None else float(transition_ms)
        ),
    )


def run_simulation(
    graph,
    setup,
    scheduler,
    *,
    duration_ms: float,
    seed: int,
    neuron_params: LIFParameters,
    synapse_params: SynapseParameters,
    max_recorded_spikes: int,
    progress_interval_ms: float = 100.0,
    diagnostics_interval_steps: int = 200,
):
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
        max_recorded_spikes=int(max_recorded_spikes),
        progress_interval_ms=progress_interval_ms,
        diagnostics_interval_steps=diagnostics_interval_steps,
    )
    started = time.perf_counter()
    result = simulator.run(progress=False)
    wall = time.perf_counter() - started
    return result, wall


def summarize_activity(result, stimulated_indices) -> dict:
    """Partition recorded spikes into stimulated and non-stimulated neurons."""
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    times = result.recorder.spike_times_ms
    neurons = result.recorder.spike_neuron_indices
    stimulated_mask = np.zeros(counts.size, dtype=bool)
    stimulated_mask[np.asarray(stimulated_indices, dtype=np.int64)] = True

    stimulated_spike = stimulated_mask[neurons]
    total = int(counts.sum())
    stimulated = int(counts[stimulated_mask].sum())
    downstream_times = times[~stimulated_spike]
    activity = dict(result.summary["activity"])

    return {
        "duration_ms": float(result.duration_ms),
        "dt_ms": float(result.dt_ms),
        "n_steps": int(result.n_steps),
        "seed": int(result.seed),
        "spikes_total": total,
        "spikes_stimulated": stimulated,
        "spikes_non_stimulated": total - stimulated,
        "stimulated_neuron_count": int(stimulated_mask.sum()),
        "stimulated_neuron_fraction": round(
            int(stimulated_mask.sum()) / max(1, counts.size), 6
        ),
        "spiking_neurons_stimulated": int(
            np.count_nonzero(counts[stimulated_mask])
        ),
        "spiking_neurons_non_stimulated": int(
            np.count_nonzero(counts[~stimulated_mask])
        ),
        "first_spike_ms": (
            round(float(times.min()), 3) if times.size else None
        ),
        "first_non_stimulated_spike_ms": (
            round(float(downstream_times.min()), 3)
            if downstream_times.size
            else None
        ),
        "active_neurons": int(activity.get("active_neurons", 0)),
        "silent_neurons": int(activity.get("silent_neurons", 0)),
        "active_fraction": float(activity.get("active_fraction", 0.0)),
        "mean_rate_hz": float(activity.get("mean_rate_hz", 0.0)),
        "population_rate_hz": float(activity.get("population_rate_hz", 0.0)),
        "population_rate_peak_hz": float(
            activity.get("population_rate_peak_hz", 0.0)
        ),
        "activity_by_stimulation": dict(
            result.summary["activity_by_stimulation"]
        ),
        "spike_capacity": int(result.recorder.capacity),
    }


def schedule_summary(setup, scheduler, times: np.ndarray) -> dict:
    """Describe the mapped populations and the current actually scheduled."""
    features = {}
    for feature in setup.encoders:
        indices = np.asarray(setup.mapping.indices(feature), dtype=np.int64)
        population = setup.mapping.populations[feature]
        root_ids = {
            name: [int(value) for value in population.root_ids[name]]
            for name, _pool, _count in population.plan.groups
        }
        series = [
            float(scheduler.feature_currents_at(float(value))[feature])
            for value in times
        ]
        peak = max(series, default=0.0)
        features[feature] = {
            "n_neurons": int(indices.size),
            "neuron_indices": [int(value) for value in indices],
            "root_ids": root_ids,
            "peak_total_current_pa": round(peak, 6),
            "mean_total_current_pa": round(
                float(np.mean(series)) if series else 0.0, 6
            ),
            "injected_pa_ms": round(float(np.sum(series)) * setup.dt_ms, 6),
        }
    return {
        "kind": "sensory_population_schedule",
        "dt_ms": setup.dt_ms,
        "duration_ms": scheduler.duration_ms,
        "transition_ms": scheduler.transition_ms,
        "n_segments": len(scheduler.states),
        "n_stimulated_neurons": int(scheduler.stimulated_indices.size),
        "stimulated_neuron_indices": [
            int(value) for value in scheduler.stimulated_indices
        ],
        "peak_total_current_pa": round(
            float(
                max(
                    sum(
                        scheduler.feature_currents_at(float(value)).values()
                    )
                    for value in times
                )
            ),
            6,
        ),
        "features": features,
        "describe": scheduler.describe(),
    }


def encoding_summary(results, inputs, encoders) -> dict:
    per_frame = []
    aggregate = {
        name: {
            "max_activation": 0.0,
            "mean_activation_across_frames": 0.0,
            "max_active_units": 0,
        }
        for name in encoders
    }
    for item, result in zip(inputs, results):
        encoded = encode_state(result.conversion.state.features(), encoders)
        active = {}
        for name, encoder in encoders.items():
            values = np.asarray(encoded[name], dtype=np.float64)
            entry = aggregate[name]
            entry["max_activation"] = max(
                entry["max_activation"], float(values.max(initial=0.0))
            )
            entry["mean_activation_across_frames"] += float(values.mean())
            entry["max_active_units"] = max(
                entry["max_active_units"], int(np.count_nonzero(values > 0.0))
            )
            if float(values.max(initial=0.0)) > 0.0:
                active[name] = {
                    "n_units": int(values.size),
                    "max_activation": round(float(values.max()), 6),
                    "active_units": int(np.count_nonzero(values > 0.0)),
                }
        per_frame.append(
            {
                "frame_id": item.frame_id,
                "timestamp_ms": round(item.timestamp_ms, 3),
                "active_features": active,
            }
        )
    n_frames = max(1, len(per_frame))
    for entry in aggregate.values():
        entry["max_activation"] = round(entry["max_activation"], 6)
        entry["mean_activation_across_frames"] = round(
            entry["mean_activation_across_frames"] / n_frames, 6
        )
    return {"per_frame": per_frame, "aggregate": aggregate}


def detector_record(pipeline, result, item: FrameInput) -> dict:
    accepted = [
        {
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "role": detection.role.value,
            "confidence": round(float(detection.confidence), 6),
            "screen_box": [
                round(float(value), 4)
                for value in detection.screen_box.as_tuple()
            ],
            "normalized_box": [
                round(float(value), 6)
                for value in detection.normalized_box.as_tuple()
            ],
            "clamped": bool(detection.clamped),
        }
        for detection in result.validation.accepted
    ]
    rejected = [
        {"reason": item_.reason.value, "detail": item_.detail}
        for item_ in result.validation.rejected
    ]
    return {
        "frame_id": item.frame_id,
        "timestamp_ms": round(item.timestamp_ms, 3),
        "image_path": str(item.path),
        "n_decoded_above_threshold": int(
            getattr(pipeline.detector, "last_decoded_count", 0) or 0
        ),
        "detections": accepted,
        "rejected": rejected,
        "observations": [
            observation.as_dict()
            for observation in result.spatial.observations.observations
        ],
        "game_state": result.conversion.as_dict(),
        "features": {
            name: (None if value is None else float(value))
            for name, value in result.spatial.features.items()
        },
        "feature_groups": [group.as_dict() for group in result.spatial.groups],
    }


def run(
    *,
    images: list[str] | None = None,
    recording: tuple[int, int] | None = None,
    seed: int | None = None,
    duration_ms: float | None = None,
    transition_ms: float | None = None,
    bounds_tolerance_px: float = 1.0,
    max_recorded_spikes: int | None = None,
    output: str | Path | None = None,
    write: bool = True,
) -> dict:
    started = time.perf_counter()
    selection = resolve_inputs(images=images, recording=recording)

    sensory_config = load_config(SENSORY_CONFIG)
    simulation_config = _load_yaml(SIMULATION_CONFIG)
    neuron_config = _load_yaml(NEURON_CONFIG)
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(simulation_config["synapse"])
    graph = load_connectome(
        PROJECT_ROOT / simulation_config["connectome"]["path"]
    )
    setup = prepare_setup(graph, sensory_config)

    detector, detector_config = build_detector()
    pipeline = build_pipeline(
        detector, bounds_tolerance_px=bounds_tolerance_px
    )
    results = [process_frame(pipeline, item) for item in selection.frames]

    timeline = [
        (item.timestamp_ms, result.conversion.state)
        for item, result in zip(selection.frames, results)
    ]
    last_start = timeline[-1][0]
    resolved_duration = (
        setup.duration_ms if len(timeline) == 1 else last_start + FRAME_INTERVAL_MS
    )
    if duration_ms is not None:
        resolved_duration = float(duration_ms)
    if resolved_duration <= last_start:
        raise ValueError("duration_ms must be later than the last frame")
    if max_recorded_spikes is None:
        max_recorded_spikes = int(
            sensory_config["sensory"].get("max_recorded_spikes", 5_000_000)
        )
    resolved_seed = int(
        sensory_config["sensory"]["seed"] if seed is None else seed
    )

    scheduler = build_schedule(
        setup,
        timeline,
        duration_ms=resolved_duration,
        transition_ms=transition_ms,
    )
    times = np.arange(
        0.0, resolved_duration, float(setup.dt_ms), dtype=np.float64
    )
    simulation, wall = run_simulation(
        graph,
        setup,
        scheduler,
        duration_ms=resolved_duration,
        seed=resolved_seed,
        neuron_params=neuron_params,
        synapse_params=synapse_params,
        max_recorded_spikes=max_recorded_spikes,
        progress_interval_ms=float(
            sensory_config["sensory"].get("progress_interval_ms", 100.0)
        ),
        diagnostics_interval_steps=int(
            sensory_config["sensory"].get("diagnostics_interval_steps", 200)
        ),
    )
    activity = summarize_activity(simulation, scheduler.stimulated_indices)

    frames = [
        detector_record(pipeline, result, item)
        for item, result in zip(selection.frames, results)
    ]
    payload = {
        "pipeline": "phase_3b_end_to_end_sensory_to_neural",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "input": {
            **selection.info,
            "frame_ids": [item.frame_id for item in selection.frames],
            "timestamps_ms": [
                round(item.timestamp_ms, 3) for item in selection.frames
            ],
        },
        "detector": {
            "description": detector.describe(),
            "config": {
                "model_path": str(detector_config.model_path),
                "model_sha256": detector_config.model_sha256,
                "input_size": list(detector_config.input_size),
                "confidence_threshold": detector_config.confidence_threshold,
                "nms_iou_threshold": detector_config.nms_iou_threshold,
                "providers": list(detector_config.providers),
            },
            "bounds_tolerance_pixels": float(bounds_tolerance_px),
        },
        "frames": frames,
        "encoding": encoding_summary(
            results, selection.frames, setup.encoders
        ),
        "schedule": schedule_summary(setup, scheduler, times),
        "simulation": {
            **activity,
            "wall_runtime_s": round(wall, 4),
            "steps_per_second_wall": round(
                simulation.n_steps / wall if wall > 0 else 0.0, 2
            ),
            "synapses": dict(simulation.summary["synapses"]),
            "diagnostics": dict(simulation.summary["diagnostics"]),
            "max_recorded_spikes": int(max_recorded_spikes),
        },
        "limitations": list(LIMITATIONS),
    }
    payload["total_wall_runtime_s"] = round(time.perf_counter() - started, 3)

    if write:
        destination = Path(output) if output is not None else DEFAULT_OUTPUT
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8"
        )
        payload["output_path"] = str(destination)
    return payload


def _print_summary(payload: dict) -> None:
    input_info = payload["input"]
    simulation = payload["simulation"]
    accepted = sum(
        len(frame["detections"]) for frame in payload["frames"]
    )
    rejected = sum(len(frame["rejected"]) for frame in payload["frames"])
    stimulating = payload["schedule"]["n_stimulated_neurons"]
    source = input_info.get("group", "images")
    if input_info["kind"] == "recording":
        source = f"{source} {input_info['start']}-{input_info['end']}"
    print(f"input: {input_info['n_frames']} frame(s) ({source})")
    print(
        f"detector: {payload['detector']['description'].get('name')} "
        f"sha256={str(payload['detector']['config']['model_sha256'])[:16]}..."
    )
    print(f"detections: {accepted} accepted, {rejected} rejected")
    print(f"stimulated neurons: {stimulating}")
    print(
        f"simulation: {simulation['duration_ms']:.1f} ms | "
        f"{simulation['n_steps']} steps | "
        f"{simulation['wall_runtime_s']:.2f} s"
    )
    print(
        f"spikes: {simulation['spikes_total']} total "
        f"({simulation['spikes_stimulated']} stimulated, "
        f"{simulation['spikes_non_stimulated']} non-stimulated)"
    )
    if simulation["first_non_stimulated_spike_ms"] is not None:
        print(
            "downstream: first non-stimulated spike at "
            f"{simulation['first_non_stimulated_spike_ms']:.1f} ms "
            f"({simulation['spiking_neurons_non_stimulated']} neurons)"
        )
    else:
        print("downstream: no non-stimulated neuron spiked")
    if payload.get("output_path"):
        print(f"wrote {payload['output_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        action="append",
        metavar="PATH",
        help="gameplay image; repeat for a sequence (overrides --recording)",
    )
    parser.add_argument(
        "--recording",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help=(
            "frame range from the existing datasetfootage recording "
            f"(default {DEFAULT_RECORDING[0]} {DEFAULT_RECORDING[1]})"
        ),
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--duration-ms", type=float, default=None)
    parser.add_argument("--transition-ms", type=float, default=None)
    parser.add_argument(
        "--bounds-tolerance-px",
        type=float,
        default=1.0,
        help="in-memory validation tolerance; production config stays at 0.0",
    )
    parser.add_argument("--max-spikes", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    payload = run(
        images=args.image,
        recording=tuple(args.recording) if args.recording else None,
        seed=args.seed,
        duration_ms=args.duration_ms,
        transition_ms=args.transition_ms,
        bounds_tolerance_px=args.bounds_tolerance_px,
        max_recorded_spikes=args.max_spikes,
        output=args.output,
    )
    _print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
