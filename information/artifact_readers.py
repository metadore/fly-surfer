"""Read-only access to archived FLY-SURFER experiment artifacts.

Every reader returns plain numpy arrays plus the source path and SHA-256 so a
result can be traced to bytes on disk. Nothing here writes, repairs or
imputes. A reader that cannot find the variation a phase needs raises
``UnavailableEndpoint`` with the reason, which callers record verbatim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EVENT_SOURCES = {
    "replay_0101": "experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json",
    "segment_0_99": "experiments/phase_4h/sequences/events_0_99.json",
    "segment_200_299": "experiments/phase_4h/sequences/events_200_299.json",
}
DECODER_SOURCE = "experiments/results/phase_4f/motor_decoder_experiment.json"
PHASE_5E_SOURCE = "experiments/results/phase_5e/controlled_learning_raw.json"
PHASE_5F_SOURCE = "experiments/results/phase_5f/comparison_raw.json"
PHASE_3A5_SEEDS_SOURCE = "experiments/phase_3_5/results/stage_seeds.json"
PHASE_3A5_POPULATION_SOURCE = "experiments/phase_3_5/results/stage_population.json"
PHASE_3A5_TUNING_SOURCE = "experiments/phase_3_5/results/stage_tuning.json"
PHASE_5_BANC_SOURCE = "experiments/results/phase_5/banc_reward_plasticity.json"
PHASE_3B2C_SOURCE = "experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json"

EVENT_CLASSES = [
    "appeared",
    "occluded",
    "disappeared",
    "approaching",
    "receding",
    "uncertain",
]
DECODED_STATES = ["NEUTRAL", "LEFT", "RIGHT", "JUMP"]


class UnavailableEndpoint(RuntimeError):
    """An endpoint the archived data cannot support, with the reason."""


def sha256_of(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(PROJECT_ROOT / path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: str) -> dict:
    with open(PROJECT_ROOT / path, encoding="utf-8") as handle:
        return json.load(handle)


def load_events() -> dict:
    """All archived event records, tagged with segment and frame cluster."""
    classes: list[int] = []
    clusters: list[int] = []
    segments: list[int] = []
    segment_names: list[str] = []
    per_segment: dict[str, dict] = {}
    for index, (name, path) in enumerate(EVENT_SOURCES.items()):
        payload = _load(path)
        events = payload["events"]
        counts = {cls: 0 for cls in EVENT_CLASSES}
        for event in events:
            code = EVENT_CLASSES.index(event["event"])
            classes.append(code)
            segments.append(index)
            clusters.append(index * 1000 + int(event["frame_index"]))
            counts[event["event"]] += 1
        per_segment[name] = {
            "n": len(events),
            "path": path,
            "sha256": sha256_of(path),
            "class_counts": counts,
            "n_frame_clusters": len(
                {int(event["frame_index"]) for event in events}
            ),
        }
        segment_names.append(name)
    return {
        "class_codes": np.asarray(classes, dtype=np.int64),
        "class_names": EVENT_CLASSES,
        "frame_clusters": np.asarray(clusters, dtype=np.int64),
        "segment_codes": np.asarray(segments, dtype=np.int64),
        "segment_names": segment_names,
        "per_segment": per_segment,
        "provenance": "measured",
        "source_hashes": {name: block["sha256"] for name, block in per_segment.items()},
    }


def load_frame_event_counts(block_frames: int = 10) -> dict:
    """Distinct event classes per frame, capped, with temporal blocks.

    Frames that carry no event stay coded 0 rather than being dropped: the
    archived extractor emits one record per detected event, so an absent
    record means no event was raised for that frame.
    """
    counts: list[int] = []
    blocks: list[int] = []
    segments: list[int] = []
    for index, name in enumerate(EVENT_SOURCES):
        payload = _load(EVENT_SOURCES[name])
        events = payload["events"]
        n_frames = 100
        per_frame: dict[int, set[str]] = {}
        for event in events:
            per_frame.setdefault(int(event["frame_index"]), set()).add(event["event"])
        for frame in range(n_frames):
            counts.append(min(3, len(per_frame.get(frame, ()))))
            blocks.append(index * 100 + frame // block_frames)
            segments.append(index)
    return {
        "counts": np.asarray(counts, dtype=np.int64),
        "block_clusters": np.asarray(blocks, dtype=np.int64),
        "segment_codes": np.asarray(segments, dtype=np.int64),
        "n_frames_per_segment": 100,
        "block_frames": block_frames,
        "provenance": "derived",
    }


def load_decoder_windows() -> dict:
    """Per-window decoder state, scores and pool evidence from Phase 4F."""
    payload = _load(DECODER_SOURCE)
    states: list[int] = []
    max_scores: list[float] = []
    run_clusters: list[int] = []
    scenarios: list[str] = []
    amplitudes: list[float] = []
    left_active: list[int] = []
    right_active: list[int] = []
    jump_active: list[int] = []
    for run_index, run in enumerate(payload["runs"]):
        scenarios.append(run["scenario"])
        amplitudes.append(float(run["amplitude_pa"]))
        for window in run["windows"]:
            states.append(DECODED_STATES.index(window["decoded_state"]))
            max_scores.append(max(window["raw_scores"].values()))
            run_clusters.append(run_index)
            evidence = window["evidence"]
            left_active.append(int(evidence["LEFT"]["active_neurons"] > 0))
            right_active.append(int(evidence["RIGHT"]["active_neurons"] > 0))
            jump_active.append(int(evidence["JUMP"]["active_neurons"] > 0))
    return {
        "state_codes": np.asarray(states, dtype=np.int64),
        "state_names": DECODED_STATES,
        "max_score": np.asarray(max_scores, dtype=np.float64),
        "run_clusters": np.asarray(run_clusters, dtype=np.int64),
        "scenarios": np.asarray(scenarios, dtype=object),
        "amplitude_pa": np.asarray(amplitudes, dtype=np.float64),
        "left_active": np.asarray(left_active, dtype=np.int64),
        "right_active": np.asarray(right_active, dtype=np.int64),
        "jump_active": np.asarray(jump_active, dtype=np.int64),
        "n_runs": len(payload["runs"]),
        "provenance": "simulated",
        "source_sha256": sha256_of(DECODER_SOURCE),
    }


REWARD_LEVELS = [-1.0, 0.0, 1.0]


def load_phase5e() -> dict:
    """Training episodes per condition, with cue, action, reward, spike counts."""
    payload = _load(PHASE_5E_SOURCE)
    out: dict[str, dict] = {}
    for condition, block in payload["conditions"].items():
        cues: list[int] = []
        actions: list[int] = []
        rewards: list[int] = []
        spikes: list[int] = []
        cue_spikes: list[int] = []
        replicates: list[int] = []
        episodes: list[int] = []
        for replicate in block["replicates"]:
            index = int(replicate["replicate"])
            for record in replicate["train"]:
                cues.append(int(record["cue"]))
                action = record.get("chosen_action")
                actions.append(-1 if action is None else int(action))
                rewards.append(REWARD_LEVELS.index(round(float(record["reward"]), 6)))
                spikes.append(int(record.get("n_spikes", -1)))
                cue_count = record.get("n_cue_spikes")
                cue_spikes.append(-1 if cue_count is None else int(cue_count))
                replicates.append(index)
                episodes.append(int(record["episode"]))
        out[condition] = {
            "label": block["label"],
            "spec": block["spec"],
            "cue": np.asarray(cues, dtype=np.int64),
            "action": np.asarray(actions, dtype=np.int64),
            "reward": np.asarray(rewards, dtype=np.int64),
            "n_spikes": np.asarray(spikes, dtype=np.int64),
            "n_cue_spikes": np.asarray(cue_spikes, dtype=np.int64),
            "replicate_clusters": np.asarray(replicates, dtype=np.int64),
            "episode": np.asarray(episodes, dtype=np.int64),
        }
    return {
        "conditions": out,
        "reward_levels": REWARD_LEVELS,
        "n_replicates": len({int(r["replicate"]) for r in payload["conditions"]["A"]["replicates"]}),
        "provenance": "simulated",
        "source_sha256": sha256_of(PHASE_5E_SOURCE),
    }


def load_phase5f() -> dict:
    """Evaluation episodes per condition, checkpoint and seed from Phase 5F."""
    payload = _load(PHASE_5F_SOURCE)
    out: dict[str, dict] = {}
    for condition, block in payload["core"]["conditions"].items():
        per_checkpoint: dict[str, dict] = {}
        for checkpoint in block["eval_checkpoints"]:
            key = str(int(checkpoint))
            cues: list[int] = []
            actions: list[int] = []
            rewards: list[int] = []
            seeds: list[int] = []
            for cell in block["cells"]:
                seed_index = int(cell["seed_index"])
                records = cell["eval"][key]["records"]
                for record in records:
                    cues.append(int(record["cue"]))
                    action = record.get("chosen_action")
                    actions.append(-1 if action is None else int(action))
                    rewards.append(REWARD_LEVELS.index(round(float(record["reward"]), 6)))
                    seeds.append(seed_index)
            per_checkpoint[key] = {
                "cue": np.asarray(cues, dtype=np.int64),
                "action": np.asarray(actions, dtype=np.int64),
                "reward": np.asarray(rewards, dtype=np.int64),
                "seed_clusters": np.asarray(seeds, dtype=np.int64),
            }
        out[condition] = {
            "label": block["label"],
            "eta": float(block["eta"]),
            "connectivity": block["connectivity"],
            "per_checkpoint": per_checkpoint,
        }
    return {
        "conditions": out,
        "checkpoints": [str(int(c)) for c in payload["core"]["conditions"]["fixed_complete"]["eval_checkpoints"]],
        "n_seeds": len(payload["core"]["conditions"]["fixed_complete"]["cells"]),
        "provenance": "simulated",
        "source_sha256": sha256_of(PHASE_5F_SOURCE),
    }


def load_sensory_population_stage(path: str = PHASE_3A5_SEEDS_SOURCE) -> dict:
    """Matched distance -> population-vector runs from a Phase 3A.5 stage.

    Each condition is one simulation run. The reader keeps the full response
    vector per run; it never expands a run into per-spike observations.
    """
    payload = _load(path)
    groups = payload.get("groups", [])
    if not groups:
        raise UnavailableEndpoint(f"{path} has no stage groups")
    distances: list[float] = []
    group_index: list[int] = []
    mapping_seeds: list[int | None] = []
    population_sizes: list[int | None] = []
    vectors: list[list[int]] = []
    spikes: list[int] = []
    group_meta: list[dict] = []
    for index, group in enumerate(groups):
        parameters = group.get("parameters", {})
        seed = parameters.get("mapping_seed")
        conditions = group.get("conditions", [])
        if not conditions:
            raise UnavailableEndpoint(f"{path} group {index} has no conditions")
        group_distances: list[float] = []
        for condition in conditions:
            factors = condition.get("factors", {})
            distance = factors.get("distance")
            calibration = (
                condition.get("calibration", {})
                .get("by_feature", {})
                .get("obstacle_distance")
            )
            if distance is None or not calibration:
                raise UnavailableEndpoint(
                    f"{path} group {index} lacks an obstacle_distance calibration"
                )
            vector = calibration.get("population_vector")
            if not vector:
                raise UnavailableEndpoint(
                    f"{path} group {index} has no population_vector"
                )
            distances.append(float(distance))
            group_distances.append(float(distance))
            group_index.append(index)
            mapping_seeds.append(None if seed is None else int(seed))
            size = parameters.get("population_size", factors.get("population_size"))
            population_sizes.append(None if size is None else int(size))
            vectors.append([int(value) for value in vector])
            spikes.append(int(calibration.get("spikes", sum(vector))))
        if len(set(group_distances)) != len(group_distances):
            raise UnavailableEndpoint(
                f"{path} group {index} repeats a distance"
            )
        group_meta.append(
            {
                "group": index,
                "parameters": parameters,
                "distances": group_distances,
                "analysis": group.get("analysis", {}),
            }
        )
    width = len(vectors[0])
    if any(len(vector) != width for vector in vectors):
        raise UnavailableEndpoint(f"{path} mixes population-vector widths")
    return {
        "stage": payload.get("stage"),
        "distances": np.asarray(distances, dtype=np.float64),
        "group_index": np.asarray(group_index, dtype=np.int64),
        "mapping_seeds": np.asarray(
            [-1 if seed is None else seed for seed in mapping_seeds], dtype=np.int64
        ),
        "mapping_seed_recorded": [seed is not None for seed in mapping_seeds],
        "population_sizes": np.asarray(
            [-1 if size is None else size for size in population_sizes], dtype=np.int64
        ),
        "vectors": np.asarray(vectors, dtype=np.int64),
        "spikes": np.asarray(spikes, dtype=np.int64),
        "groups": group_meta,
        "n_groups": len(groups),
        "n_runs": len(vectors),
        "provenance": "simulated",
        "source": path,
        "source_sha256": sha256_of(path),
    }


def load_population_sweep(path: str = PHASE_3A5_POPULATION_SOURCE) -> dict:
    """Population-size sweep from Phase 3A.5, kept grouped by vector width.

    Every group is a separate run with its own width, so the groups are
    returned side by side instead of being forced into one matrix. All groups
    share one mapping seed; the sweep is a sensitivity analysis, not an
    independent replication.
    """
    payload = _load(path)
    groups = payload.get("groups", [])
    if not groups:
        raise UnavailableEndpoint(f"{path} has no stage groups")
    out: list[dict] = []
    seen_sizes: set[int] = set()
    seed_values: set[int] = set()
    for index, group in enumerate(groups):
        parameters = group.get("parameters", {})
        size = parameters.get("population_size")
        if size is None:
            raise UnavailableEndpoint(f"{path} group {index} lacks population_size")
        size = int(size)
        if size in seen_sizes:
            raise UnavailableEndpoint(f"{path} repeats population_size {size}")
        seen_sizes.add(size)
        seed = parameters.get("mapping_seed")
        if seed is not None:
            seed_values.add(int(seed))
        distances: list[float] = []
        vectors: list[list[int]] = []
        spikes: list[int] = []
        for condition in group.get("conditions", []):
            factors = condition.get("factors", {})
            distance = factors.get("distance")
            calibration = (
                condition.get("calibration", {})
                .get("by_feature", {})
                .get("obstacle_distance")
            )
            if distance is None or not calibration:
                raise UnavailableEndpoint(
                    f"{path} group {index} lacks an obstacle_distance calibration"
                )
            vector = calibration.get("population_vector")
            if not vector:
                raise UnavailableEndpoint(
                    f"{path} group {index} has no population_vector"
                )
            if len(vector) != size:
                raise UnavailableEndpoint(
                    f"{path} group {index} vector width does not match {size}"
                )
            distances.append(float(distance))
            vectors.append([int(value) for value in vector])
            spikes.append(int(calibration.get("spikes", sum(vector))))
        if len(set(distances)) != len(distances):
            raise UnavailableEndpoint(f"{path} group {index} repeats a distance")
        out.append(
            {
                "population_size": size,
                "mapping_seed": None if seed is None else int(seed),
                "distances": np.asarray(distances, dtype=np.float64),
                "vectors": np.asarray(vectors, dtype=np.int64),
                "spikes": np.asarray(spikes, dtype=np.int64),
            }
        )
    out.sort(key=lambda group: group["population_size"])
    return {
        "stage": payload.get("stage"),
        "groups": out,
        "sizes": np.asarray([group["population_size"] for group in out], dtype=np.int64),
        "mapping_seeds": sorted(seed_values),
        "n_groups": len(out),
        "provenance": "simulated",
        "source": path,
        "source_sha256": sha256_of(path),
        "note": (
            "all groups share one mapping seed; this sweep is a descriptive "
            "sensitivity analysis, not an independent replication"
        ),
    }


def load_decoder_window_details() -> dict:
    """Per-window pool activity and decoded state from Phase 4F."""
    payload = _load(DECODER_SOURCE)
    pools = ["LEFT", "RIGHT", "JUMP"]
    state_codes: list[int] = []
    run_clusters: list[int] = []
    window_indices: list[int] = []
    starts: list[float] = []
    ends: list[float] = []
    scenarios: list[str] = []
    amplitudes: list[float] = []
    fractions: list[list[float]] = []
    spikes: list[list[int]] = []
    active: list[list[int]] = []
    sizes: list[list[int]] = []
    for run_index, run in enumerate(payload["runs"]):
        for window_index, window in enumerate(run["windows"]):
            evidence = window["evidence"]
            state_codes.append(DECODED_STATES.index(window["decoded_state"]))
            run_clusters.append(run_index)
            window_indices.append(window_index)
            starts.append(float(window["window_start_ms"]))
            ends.append(float(window["window_end_ms"]))
            scenarios.append(run["scenario"])
            amplitudes.append(float(run["amplitude_pa"]))
            fractions.append(
                [float(evidence[pool]["active_fraction"]) for pool in pools]
            )
            spikes.append([int(evidence[pool]["spikes"]) for pool in pools])
            active.append(
                [int(evidence[pool]["active_neurons"] > 0) for pool in pools]
            )
            sizes.append([int(evidence[pool]["size"]) for pool in pools])
    return {
        "state_codes": np.asarray(state_codes, dtype=np.int64),
        "state_names": DECODED_STATES,
        "run_clusters": np.asarray(run_clusters, dtype=np.int64),
        "window_index": np.asarray(window_indices, dtype=np.int64),
        "window_start_ms": np.asarray(starts, dtype=np.float64),
        "window_end_ms": np.asarray(ends, dtype=np.float64),
        "scenario": np.asarray(scenarios, dtype=object),
        "amplitude_pa": np.asarray(amplitudes, dtype=np.float64),
        "pool_names": pools,
        "active_fraction": np.asarray(fractions, dtype=np.float64),
        "pool_spikes": np.asarray(spikes, dtype=np.int64),
        "pool_active": np.asarray(active, dtype=np.int64),
        "pool_sizes": np.asarray(sizes, dtype=np.int64),
        "n_runs": len(payload["runs"]),
        "n_windows": len(state_codes),
        "provenance": "simulated",
        "source": DECODER_SOURCE,
        "source_sha256": sha256_of(DECODER_SOURCE),
    }


def load_phase5_banc_conditions() -> dict:
    """Window-level summaries of the Phase 5 real-BANC plasticity demonstration."""
    payload = _load(PHASE_5_BANC_SOURCE)
    out: dict[str, dict] = {}
    for name, block in payload["conditions"].items():
        windows = []
        for record in block.get("decoder_outputs", []):
            evidence = record.get("evidence", {})
            windows.append(
                {
                    "window_start_ms": record.get("window_start_ms"),
                    "window_end_ms": record.get("window_end_ms"),
                    "state": record.get("state"),
                    "active_spikes": {
                        pool: int(evidence[pool]["spikes"])
                        for pool in ("LEFT", "RIGHT", "JUMP")
                        if pool in evidence
                    },
                    "active_neurons": {
                        pool: int(evidence[pool]["active_neurons"])
                        for pool in ("LEFT", "RIGHT", "JUMP")
                        if pool in evidence
                    },
                }
            )
        out[name] = {
            "label": block.get("label"),
            "eta": block.get("eta"),
            "spike_hash": block.get("spike_hash"),
            "n_windows": len(windows),
            "windows": windows,
            "reward_provider": block.get("reward_provider"),
        }
    hashes = {block["spike_hash"] for block in out.values() if block["spike_hash"]}
    return {
        "conditions": out,
        "n_conditions": len(out),
        "windows_per_condition": sorted({block["n_windows"] for block in out.values()}),
        "n_distinct_spike_hashes": len(hashes),
        "provenance": "simulated",
        "source": PHASE_5_BANC_SOURCE,
        "source_sha256": sha256_of(PHASE_5_BANC_SOURCE),
    }


def load_replay_neural_availability() -> dict:
    """Evidence about what the Phase 3B2C replay persisted for neural activity."""
    payload = _load(PHASE_3B2C_SOURCE)
    simulation = payload.get("simulation", {})
    raw_markers = [
        key
        for key in simulation
        if any(
            token in key.lower()
            for token in ("spike_time", "spike_neuron", "raw_spike", "spikes_per_neuron")
        )
    ]
    return {
        "source": PHASE_3B2C_SOURCE,
        "source_sha256": sha256_of(PHASE_3B2C_SOURCE),
        "n_frames": int(payload.get("sequence", {}).get("n_frames", 0)),
        "n_events": len(payload.get("events", [])),
        "spikes_total": int(simulation.get("spikes_total", 0)),
        "stimulated_neuron_count": int(
            simulation.get("stimulated_neuron_count", 0)
        ),
        "activity": simulation.get("activity"),
        "activity_by_stimulation": simulation.get("activity_by_stimulation"),
        "simulation_keys": sorted(simulation.keys()),
        "raw_spike_markers": raw_markers,
        "per_neuron_spikes_persisted": bool(raw_markers),
        "provenance": "simulated",
    }
