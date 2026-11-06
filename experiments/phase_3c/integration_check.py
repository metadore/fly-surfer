"""Phase 3B + 3C end-to-end integration check.

The scripted chain is::

    RawDetection -> PerceptionPipeline -> FrameObservations
                 -> MultiObjectTracker -> TemporalFeatureEncoder
                 -> GameState -> TemporalActivationScheduler
                 -> BrainSimulator (connectome spikes)

Detections are scripted; no trained detector, no image understanding and no
action selection are involved. The check verifies plumbing, determinism,
protected-artifact hashes and that the connectome is the only source of the
reported neural activity.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.brain_simulator import BrainSimulator
from brain.connectome_loader import load_connectome
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_3c.temporal_calibration import (
    FEATURES,
    TRACKING,
)
from perception.config import load_perception_config
from perception.detection import RawDetection
from perception.detector import MockDetector
from perception.pipeline import PerceptionPipeline
from perception.temporal import (
    Lifecycle,
    TemporalConfig,
    TemporalFeatureConfig,
    TemporalSequenceProcessor,
)
from perception.tracking import TrackingConfig
from sensory.sensory_experiment import load_config, prepare_setup
from sensory.temporal_scheduler import (
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
PERCEPTION_CONFIG = PROJECT_ROOT / "configs" / "perception_config.yaml"
OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "phase_3c"
    / "results"
    / "integration.json"
)

WIDTH, HEIGHT = 1280, 720
FRAME_INTERVAL_MS = 1000.0 / 30.0
N_FRAMES = 10
OCCLUDED_FRAME = 5
TRAIN_CLASS = 11
OBSTACLE_CLASS = 2
TERRAIN_CLASS = 7
# The scripted sequence spans 300 ms (10 frames at 30 fps), matching the
# Phase 3A.5 calibration duration. One extra timestep is simulated so the
# current scheduled by the final frame is actually applied.
SENSITIVITY_DURATION_MS = 400.0
STABLE_SPIKE_LIMIT = 10_000

PROTECTED = {
    "README.md": (
        PROJECT_ROOT / "README.md",
        "6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10",
    ),
    "split_manifest": (
        PROJECT_ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json",
        "ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d",
    ),
    "connectome_npz": (
        PROJECT_ROOT / "datasets" / "processed" / "connectome.npz",
        "3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8",
    ),
    "v15_data_yaml": (
        PROJECT_ROOT
        / "datasets"
        / "external"
        / "subway surfers"
        / "roboflow_v15_yolov8"
        / "subway surfers object dataset.v15-added.yolov8"
        / "data.yaml",
        "f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423",
    ),
}

LIMITATIONS = [
    "Detections are scripted, not produced by a trained model.",
    "The detector placeholder ignores pixels; no visual recognition is "
    "demonstrated.",
    "Distance and lane labels are image geometry, not game measurements.",
    "The connectome mapping is an experimental input interface over predicted "
    "annotations, not an identified sensory pathway.",
    "Spikes are model output under configured assumptions, not measured "
    "biological activity.",
    "The protocol stops at the scripted sequence length (300 ms plus one "
    "timestep). A duration-sensitivity probe is recorded in the payload; "
    "extended runs are not presented as perception evidence.",
    "No action is selected anywhere in this chain.",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _signature_digest(signer) -> str:
    signature = signer.signature()
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


def _box_pixels(center_x: float, bottom: float, width: float, height: float):
    x1 = (center_x - width / 2.0) * WIDTH
    x2 = (center_x + width / 2.0) * WIDTH
    y2 = bottom * HEIGHT
    y1 = (bottom - height) * HEIGHT
    return x1, y1, x2, y2


def scripted_frames() -> list[tuple[float, list[RawDetection], dict]]:
    """Ten frames: an approaching train, a static barrier and one flicker."""
    frames = []
    for index in range(N_FRAMES):
        time_ms = index * FRAME_INTERVAL_MS
        detections: list[RawDetection] = []
        truth: dict = {}
        if index != OCCLUDED_FRAME:
            bottom = 0.30 + 0.033 * index
            x1, y1, x2, y2 = _box_pixels(0.50, bottom, 0.16, 0.18)
            detections.append(
                RawDetection(TRAIN_CLASS, 0.92, x1, y1, x2, y2, "train")
            )
            truth["train"] = {"lane": "center", "bottom": bottom}
        x1, y1, x2, y2 = _box_pixels(0.17, 0.72, 0.14, 0.16)
        detections.append(
            RawDetection(OBSTACLE_CLASS, 0.88, x1, y1, x2, y2, "jump-barrier")
        )
        truth["obstacle"] = {"lane": "left", "bottom": 0.72}
        x1, y1, x2, y2 = _box_pixels(0.84, 0.86, 0.16, 0.08)
        detections.append(
            RawDetection(TERRAIN_CLASS, 0.80, x1, y1, x2, y2, "ledge")
        )
        truth["terrain"] = {"lane": "right", "bottom": 0.86}
        if index == 3:
            x1, y1, x2, y2 = _box_pixels(0.95, 0.20, 0.10, 0.10)
            detections.append(
                RawDetection(TRAIN_CLASS, 0.55, x1, y1, x2, y2, "train")
            )
            truth["flicker"] = {"lane": "right", "bottom": 0.20}
        frames.append((time_ms, detections, truth))
    return frames


def _build_pipeline():
    config = load_perception_config(PERCEPTION_CONFIG)
    return PerceptionPipeline(config, MockDetector())


def _process_frames(pipeline, scripted):
    observations = []
    audit = []
    for index, (time_ms, detections, _truth) in enumerate(scripted):
        image = Image.new("RGB", (WIDTH, HEIGHT), (12, 12, 12))
        frame = pipeline.preprocessor.from_image(
            image,
            frame_id=f"integration-{index}",
            timestamp_ms=time_ms,
        )
        result = pipeline.run(frame, detections=detections)
        observations.append(result.spatial.observations)
        audit.append(
            {
                "frame_index": index,
                "time_ms": time_ms,
                "accepted": len(result.validation.accepted),
                "rejected": len(result.validation.rejected),
                "scene_objects": len(result.scene.objects),
                "observations": len(result.spatial.observations.observations),
                "features": dict(result.spatial.features),
            }
        )
    return observations, audit


def _temporal_config() -> TemporalConfig:
    tracking = TrackingConfig(**asdict(TRACKING))
    features = TemporalFeatureConfig(**asdict(FEATURES))
    return TemporalConfig(tracking=tracking, features=features)


def _temporal_run(observations):
    processor = TemporalSequenceProcessor(_temporal_config())
    return [processor.process(frame) for frame in observations]


def _feature_currents(scheduler, times):
    features = list(scheduler.encoders)
    rows = []
    for time_ms in times:
        currents = scheduler.feature_currents_at(float(time_ms))
        rows.append([currents[feature] for feature in features])
    return np.asarray(rows, dtype=np.float64), features


def _simulate(
    graph,
    setup,
    scheduler,
    neuron_params,
    synapse_params,
    duration_ms,
    seed,
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
        max_recorded_spikes=500_000,
        progress_interval_ms=100.0,
        diagnostics_interval_steps=200,
    )
    started = time.perf_counter()
    result = simulator.run(progress=False)
    wall = time.perf_counter() - started
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    summary = {
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
    }
    del simulator
    gc.collect()
    return counts, summary


def run(seed: int = 20261106) -> dict:
    started = time.perf_counter()
    simulation_config = _load_yaml(SIMULATION_CONFIG)
    neuron_config = _load_yaml(NEURON_CONFIG)
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(simulation_config["synapse"])
    setup = prepare_setup(
        load_connectome(
            PROJECT_ROOT / simulation_config["connectome"]["path"]
        ),
        load_config(SENSORY_CONFIG),
    )
    graph = setup.mapping.graph

    pipeline = _build_pipeline()
    scripted = scripted_frames()
    observations, audit = _process_frames(pipeline, scripted)

    temporal = _temporal_run(observations)
    events = [
        {
            "event": event.event.value,
            "track_id": event.track_id,
            "class_name": event.class_name,
            "lane": event.lane,
            "frame_index": event.frame_index,
            "time_ms": event.time_ms,
            "distance_proxy": event.distance_proxy,
            "is_pulse": event.is_pulse,
        }
        for frame in temporal
        for event in frame.events
    ]

    duration_ms = float(scripted[-1][0]) + float(setup.dt_ms)
    scheduler = TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        temporal,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
    )
    times = np.arange(0.0, duration_ms, float(setup.dt_ms))
    drive, feature_names = _feature_currents(scheduler, times)

    counts_a, summary_a = _simulate(
        graph,
        setup,
        scheduler,
        neuron_params,
        synapse_params,
        duration_ms,
        seed,
    )

    # A second scheduler and simulation with the same inputs and seed.
    scheduler_b = TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        _temporal_run(observations),
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
    )
    counts_b, summary_b = _simulate(
        graph,
        setup,
        scheduler_b,
        neuron_params,
        synapse_params,
        duration_ms,
        seed,
    )

    # Duration-sensitivity probe: identical drive held longer. Recorded as an
    # observation, not used for any reported perception result.
    probe_counts, probe_summary = _simulate(
        graph,
        setup,
        scheduler,
        neuron_params,
        synapse_params,
        SENSITIVITY_DURATION_MS,
        seed,
    )
    probe_stimulated = int(
        probe_counts[setup.mapping.stimulated_indices()].sum()
    )

    per_feature = {
        feature: int(counts_a[setup.mapping.indices(feature)].sum())
        for feature in setup.encoders
    }
    stimulated = int(counts_a[setup.mapping.stimulated_indices()].sum())
    total_spikes = int(counts_a.sum())
    statistics_payload = scheduler.input_statistics()
    final_state = temporal[-1].state
    lifecycle_counts = {
        state.value: sum(
            1 for frame in temporal for track in frame.tracks
            if track.lifecycle is state
        )
        for state in Lifecycle
    }
    track_ids = sorted(
        {track.track_id for frame in temporal for track in frame.tracks}
    )

    hashes = {}
    for name, (path, expected) in PROTECTED.items():
        actual = _sha256(path)
        hashes[name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "expected": expected,
            "actual": actual,
            "match": actual == expected,
        }

    checks = {
        "all_frames_processed": [item["frame_index"] for item in audit]
        == list(range(N_FRAMES)),
        "no_detections_rejected": all(
            item["rejected"] == 0 for item in audit
        ),
        "train_and_obstacle_tracked": len(track_ids) >= 2,
        "train_appeared": any(
            item["event"] == "appeared" and item["class_name"] == "train"
            for item in events
        ),
        "train_approaching": any(
            item["event"] == "approaching" and item["class_name"] == "train"
            for item in events
        ),
        "train_occluded": any(
            item["event"] == "occluded" for item in events
        ),
        "flicker_never_confirmed": not any(
            item["event"] == "appeared"
            and item["lane"] == 2
            and item["frame_index"] == 3
            for item in events
        ),
        "terrain_tracked_but_unrepresented": any(
            track.class_name == "ledge"
            for frame in temporal
            for track in frame.tracks
        )
        and any(frame.unrepresented_tracks > 0 for frame in temporal),
        "fourteen_features": len(final_state.features()) == 14,
        "scheduler_targets_mapped_neurons": int(
            scheduler.stimulated_indices.size
        )
        == int(setup.mapping.stimulated_indices().size),
        "pulse_events_scheduled": statistics_payload["n_pulse_events"] > 0,
        "scheduler_deterministic": _signature_digest(scheduler)
        == _signature_digest(scheduler_b),
        "simulation_spikes_deterministic": np.array_equal(counts_a, counts_b),
        "activity_matches": summary_a["activity"] == summary_b["activity"],
        "simulation_stable_at_protocol_duration": (
            total_spikes < STABLE_SPIKE_LIMIT and stimulated >= 0.5 * total_spikes
        ),
        "protected_hashes_match": all(
            item["match"] for item in hashes.values()
        ),
    }

    return {
        "seed": seed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(time.perf_counter() - started, 3),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "graph": {
            "n_neurons": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "n_stimulated_neurons": int(
                setup.mapping.stimulated_indices().size
            ),
        },
        "config": {
            "sensory": dict(setup.config["sensory"]),
            "tracking": asdict(TRACKING),
            "features": asdict(FEATURES),
            "scheduler": TemporalSchedulerConfig().as_dict(),
            "amplitudes_pa": dict(setup.amplitudes),
        },
        "frame_audit": audit,
        "temporal": {
            "n_frames": len(temporal),
            "track_ids": track_ids,
            "lifecycle_counts": lifecycle_counts,
            "n_events": len(events),
            "events": events,
            "final_game_state": {
                "time_ms": final_state.time_ms,
                "features": final_state.features(),
            },
            "unrepresented_tracks": [
                frame.unrepresented_tracks for frame in temporal
            ],
            "notes": [list(frame.notes) for frame in temporal if frame.notes],
        },
        "scheduler": {
            "n_frames": len(temporal),
            "n_stimulated_neurons": int(scheduler.stimulated_indices.size),
            "horizon_ms": scheduler.horizon_ms,
            "memory_bytes": int(scheduler.memory_bytes),
            "signature_sha256": _signature_digest(scheduler),
            "statistics": statistics_payload,
            "features": feature_names,
            "peak_current_pa": {
                feature: round(float(drive[:, index].max()), 6)
                for index, feature in enumerate(feature_names)
            },
            "mean_current_pa": {
                feature: round(float(drive[:, index].mean()), 6)
                for index, feature in enumerate(feature_names)
            },
        },
        "simulation": {
            "duration_ms": duration_ms,
            **summary_a,
            "spikes_total": total_spikes,
            "spikes_stimulated": stimulated,
            "spikes_unstimulated": total_spikes - stimulated,
            "spikes_by_feature": per_feature,
        },
        "duration_sensitivity": {
            "protocol": {
                "duration_ms": duration_ms,
                "spikes_total": total_spikes,
                "spikes_stimulated": stimulated,
                "spikes_unstimulated": total_spikes - stimulated,
                "wall_runtime_s": summary_a["wall_runtime_s"],
            },
            "probe": {
                "duration_ms": SENSITIVITY_DURATION_MS,
                "spikes_total": int(probe_counts.sum()),
                "spikes_stimulated": probe_stimulated,
                "spikes_unstimulated": int(probe_counts.sum())
                - probe_stimulated,
                "wall_runtime_s": probe_summary["wall_runtime_s"],
            },
            "note": (
                "The same scheduled drive was held past the reported protocol "
                "to expose duration sensitivity. The protocol result is taken "
                "at the scripted sequence length, matching the Phase 3A.5 "
                "calibration duration; the probe is an observation only and is "
                "not interpreted as perception performance."
            ),
        },
        "determinism": {
            "scheduler_signature_equal": _signature_digest(scheduler)
            == _signature_digest(scheduler_b),
            "spike_counts_equal": np.array_equal(counts_a, counts_b),
            "activity_equal": summary_a["activity"] == summary_b["activity"],
        },
        "protected_hashes": hashes,
        "action_selection": "none; the chain ends at sensory current injection",
        "checks": checks,
        "limitations": LIMITATIONS,
    }


def _load_yaml(path: Path) -> dict:
    import yaml

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    payload = run(seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    passed = sum(1 for value in payload["checks"].values() if value)
    print(
        f"wrote {args.output} | frames={payload['temporal']['n_frames']} "
        f"events={payload['temporal']['n_events']} "
        f"tracks={len(payload['temporal']['track_ids'])} "
        f"spikes={payload['simulation']['spikes_total']} "
        f"wall={payload['simulation']['wall_runtime_s']}s "
        f"checks={passed}/{len(payload['checks'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
