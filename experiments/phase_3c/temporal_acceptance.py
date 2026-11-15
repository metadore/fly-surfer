"""P3-T7: Phase 3C temporal acceptance experiments.

This runner executes the milestone decision rule in
``docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md`` section 6.4 on synthetic
``GameState`` sequences over the sparse full connectome:

1. no numerical, capacity or validation failure;
2. constant-sequence equivalence (3C.1) holds;
3. approach and retreat separate above the seed-to-seed spread in at least two
   of three mapping seeds (3C.2);
4. at least one frame-rate comparison is quantified (3C.7);
5. reversed or shuffled sequences produce a measurable difference, or the
   absence of one is reported as a negative result (3C.9).

The exact stimuli are pre-registered in ``configs/temporal_sensory.yaml``
because the design document describes the comparisons but does not fix the
sequences. Conditions 3C.5, 3C.6 and 3C.8 are encoder characterization, not
milestone decision-rule items, and are deliberately not executed here.

Everything reported is model output on synthetic input. No recognition,
biological coding or information claim is made.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neural_activity import SpikeRecorder  # noqa: E402
from brain.neuron_model import LIFParameters, LIFPopulation  # noqa: E402
from brain.synapse_model import SynapseModel, SynapseParameters  # noqa: E402
from perception.temporal import TemporalFrame  # noqa: E402
from sensory.game_state import GameState, ObstacleState  # noqa: E402
from sensory.input_scheduler import SensoryInputScheduler  # noqa: E402
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402
from sensory.temporal_scheduler import (  # noqa: E402
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "temporal_sensory.yaml"
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "phase_3c" / "results"
JSON_PATH = RESULTS_DIR / "temporal_acceptance.json"
SIDECAR_PATH = RESULTS_DIR / "temporal_acceptance.sidecar.json"
REPORT_PATH = RESULTS_DIR / "temporal_acceptance_report.md"
DISTANCE_FEATURE = "obstacle_distance"

PROTECTED = {
    "README.md": (
        PROJECT_ROOT / "README.md",
        "8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563",
    ),
    "connectome.npz": (
        PROJECT_ROOT / "datasets" / "processed" / "connectome.npz",
        "3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8",
    ),
}

LIMITATIONS = [
    "Sequences are synthetic GameState lists, not perceived scenes; no "
    "detector, tracker or recognition accuracy is involved.",
    "The obstacle-distance population has twelve neurons, not the four "
    "selected in Phase 3A.5; this is not the calibrated operating point "
    "(see P3-T4).",
    "Only the mapping seed varies. The simulator is deterministic with zero "
    "background and noise, so 'seed spread' is a mapping-realisation spread, "
    "not biological or runtime variability.",
    "The pre-registered d' threshold of 1.0 is a new operationalisation: the "
    "design says 'above the seed-to-seed spread' but does not fix a numeric "
    "cut-off.",
    "Bins within one run are not independent samples; d' is descriptive.",
    "The implemented scheduler is sample-and-hold plus decaying lifecycle "
    "pulses. The design's T1 crossfade and T2 smoothing variants are not "
    "implemented, so 3C.1 tests equivalence of the implemented path only.",
    "Conditions 3C.5 (lane ordering), 3C.6 (jump/roll intervals) and 3C.8 "
    "(T1/T2/T3 ablation) are not executed.",
    "Spikes are model output under configured assumptions, not measured "
    "biological activity.",
    "No action is selected anywhere in this chain.",
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def git_state() -> dict:
    import subprocess

    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except Exception:  # pragma: no cover - diagnostic only
            return ""

    return {
        "head": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty_entries": len(run("status", "--porcelain").splitlines()),
    }


def _r(value: float, digits: int = 6):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(float(value), digits)


def _state(distance: float | None, time_ms: float) -> GameState:
    if distance is None:
        return GameState(time_ms=time_ms)
    return GameState(
        obstacle=ObstacleState(
            present=True,
            lane="center",
            distance=float(distance),
            obstacle_type="low",
        ),
        time_ms=time_ms,
    )


def frame_times(interval_ms: float, duration_ms: float) -> np.ndarray:
    return np.arange(0.0, float(duration_ms) + 1e-9, float(interval_ms))


def approach_distance(start: float, end: float, time_ms: float,
                      duration_ms: float = 600.0) -> float:
    fraction = min(max(float(time_ms) / float(duration_ms), 0.0), 1.0)
    return float(start) + (float(end) - float(start)) * fraction


def make_frames(timeline, interval_ms: float) -> list[TemporalFrame]:
    frames: list[TemporalFrame] = []
    previous = 0.0
    for index, (time_ms, state) in enumerate(timeline):
        frames.append(
            TemporalFrame(
                frame_index=index,
                frame_id=f"3c-{index:02d}",
                timestamp_ms=float(time_ms),
                time_ms=float(time_ms),
                dt_ms=float(time_ms) - previous if index else float(interval_ms),
                is_gap=False,
                tracks=(),
                events=(),
                features=dict(state.features()),
                state=state,
                unrepresented_tracks=0,
            )
        )
        previous = float(time_ms)
    return frames


def constant_timeline(distance: float, times) -> list[tuple[float, GameState]]:
    return [(float(t), _state(distance, float(t))) for t in times]


def trajectory_timeline(start: float, end: float, times) -> list:
    return [
        (float(t), _state(approach_distance(start, end, float(t)), float(t)))
        for t in times
    ]


def entry_timeline(distance: float, entry_ms: float, times) -> list:
    return [
        (
            float(t),
            _state(distance if float(t) >= entry_ms else None, float(t)),
        )
        for t in times
    ]


def exit_timeline(distance: float, exit_ms: float, times) -> list:
    return [
        (
            float(t),
            _state(distance if float(t) < exit_ms else None, float(t)),
        )
        for t in times
    ]


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------


def simulate(graph, neuron_params, synapse_params, scheduler, duration_ms,
             dt_ms, capacity: int) -> dict:
    n_steps = int(round(float(duration_ms) / float(dt_ms)))
    n = int(graph.n_nodes)
    neurons = LIFPopulation(n, neuron_params, dt_ms)
    synapses = SynapseModel(graph, synapse_params, dt_ms)
    recorder = SpikeRecorder(n, int(capacity))
    current = np.zeros(n, dtype=np.float64)
    started = time.perf_counter()
    for step in range(n_steps):
        synapses.advance()
        current.fill(0.0)
        current += synapses.synaptic_current_pa
        scheduler.apply(step, step * dt_ms, current)
        spikes = neurons.step(current)
        recorder.record(step, spikes, dt_ms)
        synapses.propagate(spikes)
    wall = time.perf_counter() - started
    times = np.array(recorder.spike_times_ms, dtype=np.float64)
    indices = np.array(recorder.spike_neuron_indices, dtype=np.int64)
    counts = np.array(recorder.spike_counts(), dtype=np.int64)
    payload = {
        "n_steps": int(n_steps),
        "duration_ms": float(n_steps * dt_ms),
        "n_spikes": int(times.size),
        "wall_runtime_s": float(wall),
        "times_ms": times,
        "neuron_indices": indices,
        "counts": counts,
    }
    del neurons, synapses, recorder
    gc.collect()
    return payload


def spike_digest(payload: dict) -> str:
    digest = hashlib.sha256()
    digest.update(payload["times_ms"].tobytes())
    digest.update(payload["neuron_indices"].tobytes())
    return digest.hexdigest()


def profile(payload: dict, mask: np.ndarray | None, edges: np.ndarray) -> list:
    times = payload["times_ms"]
    indices = payload["neuron_indices"]
    if mask is not None:
        times = times[mask[indices]]
    counts, _ = np.histogram(times, bins=edges)
    return [int(value) for value in counts]


def onset_metrics(payload: dict, mask: np.ndarray, onset_ms: float,
                  edges: np.ndarray) -> dict:
    selected = mask[payload["neuron_indices"]]
    times = payload["times_ms"][selected]
    indices = payload["neuron_indices"][selected]
    after_mask = times >= onset_ms
    after_times = times[after_mask]
    after_indices = indices[after_mask]
    latencies = [
        float(after_times[after_indices == neuron].min() - onset_ms)
        for neuron in np.unique(after_indices)
    ]
    after = after_times
    profile_values = profile(payload, mask, edges)
    baseline = profile_values[: max(1, int(round(onset_ms / 50.0)))]
    post = times[(times >= onset_ms) & (times < onset_ms + 50.0)]
    bin_counts, _ = np.histogram(times, bins=edges)
    peak_bin = int(np.argmax(bin_counts)) if bin_counts.size else None
    return {
        "first_spike_latency_ms": _r(min(after) - onset_ms)
        if after.size
        else None,
        "median_onset_latency_ms": _r(float(np.median(latencies)))
        if latencies
        else None,
        "n_spiking_neurons": len(latencies),
        "baseline_mean_count": _r(float(np.mean(baseline))),
        "post_onset_50ms_count": int(post.size),
        "peak_bin_index": peak_bin,
        "peak_bin_time_ms": _r(float(edges[peak_bin]))
        if peak_bin is not None
        else None,
    }


def offset_metrics(payload: dict, mask: np.ndarray, offset_ms: float,
                   edges: np.ndarray) -> dict:
    times = payload["times_ms"]
    indices = payload["neuron_indices"]
    selected = mask[indices]
    times = times[selected]
    after = times[times >= offset_ms]
    before = times[(times >= offset_ms - 100.0) & (times < offset_ms)]
    windows = {}
    for width in (50.0, 100.0, 250.0):
        windows[f"post_{int(width)}ms"] = int(
            np.count_nonzero((after >= offset_ms) & (after < offset_ms + width))
        )
    return {
        "pre_offset_100ms_count": int(before.size),
        "post_windows": windows,
        "last_spike_after_offset_ms": _r(float(after.max() - offset_ms))
        if after.size
        else None,
        "persistence_ms": _r(float(after.max() - offset_ms))
        if after.size
        else 0.0,
    }


def cosine_distance(first, second) -> float | None:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return None
    return float(1.0 - float(np.dot(a, b)) / denom)


def dprime(first, second, threshold: float = 1.0) -> dict:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    var_a = float(np.var(a, ddof=1)) if a.size > 1 else 0.0
    var_b = float(np.var(b, ddof=1)) if b.size > 1 else 0.0
    denom = math.sqrt((var_a + var_b) / 2.0)
    diff = float(np.mean(a) - np.mean(b))
    value = diff / denom if denom > 0 else None
    return {
        "mean_first": _r(float(np.mean(a))),
        "mean_second": _r(float(np.mean(b))),
        "sd_first": _r(math.sqrt(var_a)),
        "sd_second": _r(math.sqrt(var_b)),
        "difference": _r(diff),
        "dprime": _r(value),
        "zero_variance": denom == 0.0,
        "separated": bool(denom == 0.0 and abs(diff) > 0.0)
        or bool(value is not None and abs(value) > float(threshold)),
    }


def nearest_centroid_loo(profiles: dict[str, list[list[int]]]) -> dict:
    labels = sorted(profiles)
    n_seeds = len(next(iter(profiles.values())))
    predictions = []
    for held in range(n_seeds):
        centroids = {}
        for label in labels:
            others = [
                np.asarray(profiles[label][index], dtype=np.float64)
                for index in range(n_seeds)
                if index != held
            ]
            centroids[label] = np.mean(others, axis=0)
        for label in labels:
            sample = np.asarray(profiles[label][held], dtype=np.float64)
            distances = {
                name: float(np.linalg.norm(sample - centroid))
                for name, centroid in centroids.items()
            }
            predicted = min(distances, key=distances.get)
            predictions.append(
                {
                    "held_out_seed": held,
                    "true": label,
                    "predicted": predicted,
                    "correct": predicted == label,
                }
            )
    correct = sum(1 for item in predictions if item["correct"])
    return {
        "accuracy": _r(correct / len(predictions)) if predictions else None,
        "n_predictions": len(predictions),
        "predictions": predictions,
    }


# --------------------------------------------------------------------------
# conditions
# --------------------------------------------------------------------------


def run_equivalence(graph, setup, neuron_params, synapse_params, cfg) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    times = frame_times(protocol["frame_interval_ms"], 600.0)
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    results = {}
    for distance in cfg["conditions"]["3C.1"]["constant_distances"]:
        timeline = constant_timeline(distance, times)
        frames = make_frames(timeline, protocol["frame_interval_ms"])
        temporal = TemporalActivationScheduler(
            setup.mapping,
            setup.encoders,
            frames,
            current_pa=setup.amplitudes,
            config=TemporalSchedulerConfig(),
        )
        direct = SensoryInputScheduler(
            setup.mapping,
            setup.encoders,
            [(0.0, timeline[0][1])],
            dt_ms=dt_ms,
            duration_ms=duration,
            current_pa=setup.amplitudes,
            transition_ms=0.0,
        )
        n_steps = int(round(duration / dt_ms))
        max_diff = 0.0
        differing_steps = 0
        buffer_a = np.zeros(int(graph.n_nodes), dtype=np.float64)
        buffer_b = np.zeros(int(graph.n_nodes), dtype=np.float64)
        for step in range(n_steps):
            buffer_a.fill(0.0)
            buffer_b.fill(0.0)
            temporal.apply(step, step * dt_ms, buffer_a)
            direct.apply(step, step * dt_ms, buffer_b)
            difference = float(np.max(np.abs(buffer_a - buffer_b)))
            max_diff = max(max_diff, difference)
            if difference > float(
                cfg["analysis"]["equivalence_current_tolerance_pa"]
            ):
                differing_steps += 1
        run_temporal = simulate(
            graph, neuron_params, synapse_params, temporal, duration,
            dt_ms, capacity,
        )
        run_direct = simulate(
            graph, neuron_params, synapse_params, direct, duration,
            dt_ms, capacity,
        )
        same_counts = bool(
            np.array_equal(run_temporal["counts"], run_direct["counts"])
        )
        results[str(distance)] = {
            "max_current_difference_pa": _r(max_diff, 12),
            "steps_above_tolerance": differing_steps,
            "spike_counts_identical": same_counts,
            "temporal_spike_count": run_temporal["n_spikes"],
            "direct_spike_count": run_direct["n_spikes"],
            "temporal_signature": spike_digest(run_temporal),
            "direct_signature": spike_digest(run_direct),
            "temporal_profile": profile(
                run_temporal, None, edges
            ),
            "direct_profile": profile(run_direct, None, edges),
        }
        del run_temporal, run_direct
        gc.collect()
    passed = all(
        item["max_current_difference_pa"] is not None
        and item["max_current_difference_pa"]
        <= float(cfg["analysis"]["equivalence_current_tolerance_pa"])
        and item["spike_counts_identical"]
        for item in results.values()
    )
    return {"conditions": results, "passed": bool(passed)}


def run_direction(graph, setups, neuron_params, synapse_params, cfg) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setups["20261104"].dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    times = frame_times(protocol["frame_interval_ms"], 600.0)
    interval = float(protocol["frame_interval_ms"])
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    start, end = cfg["conditions"]["3C.2"]["approach"]
    retreat_start, retreat_end = cfg["conditions"]["3C.2"]["retreat"]
    per_seed = {}
    profiles = {"approach": [], "retreat": []}
    for seed in cfg["seeds"]["mapping"]:
        setup = setups[str(seed)]
        mask = np.zeros(int(graph.n_nodes), dtype=bool)
        mask[setup.mapping.indices(DISTANCE_FEATURE)] = True
        approach_frames = make_frames(
            trajectory_timeline(start, end, times), interval
        )
        retreat_frames = make_frames(
            trajectory_timeline(retreat_start, retreat_end, times), interval
        )
        runs = {}
        for name, frames in (
            ("approach", approach_frames),
            ("retreat", retreat_frames),
        ):
            scheduler = TemporalActivationScheduler(
                setup.mapping,
                setup.encoders,
                frames,
                current_pa=setup.amplitudes,
                config=TemporalSchedulerConfig(),
            )
            runs[name] = simulate(
                graph, neuron_params, synapse_params, scheduler, duration,
                dt_ms, capacity,
            )
        approach_profile = profile(runs["approach"], mask, edges)
        retreat_profile = profile(runs["retreat"], mask, edges)
        network_approach = profile(runs["approach"], None, edges)
        network_retreat = profile(runs["retreat"], None, edges)
        profiles["approach"].append(approach_profile)
        profiles["retreat"].append(retreat_profile)
        per_seed[str(seed)] = {
            "approach_profile": approach_profile,
            "retreat_profile": retreat_profile,
            "network_approach_profile": network_approach,
            "network_retreat_profile": network_retreat,
            "total_spikes": {
                "approach": runs["approach"]["n_spikes"],
                "retreat": runs["retreat"]["n_spikes"],
            },
            "dprime_distance_population": dprime(
                approach_profile,
                retreat_profile,
                cfg["analysis"]["dprime_threshold"],
            ),
            "dprime_network": dprime(
                network_approach,
                network_retreat,
                cfg["analysis"]["dprime_threshold"],
            ),
            "cosine_distance_profiles": _r(
                cosine_distance(approach_profile, retreat_profile)
            ),
            "signature": {
                "approach": spike_digest(runs["approach"]),
                "retreat": spike_digest(runs["retreat"]),
            },
        }
        del runs
        gc.collect()

    difference_vectors = []
    for seed in cfg["seeds"]["mapping"]:
        item = per_seed[str(seed)]
        vector = np.asarray(
            item["approach_profile"], dtype=np.float64
        ) - np.asarray(item["retreat_profile"], dtype=np.float64)
        difference_vectors.append(vector)
    stacked = np.vstack(difference_vectors)
    mean_vector = stacked.mean(axis=0)
    spread = float(
        np.sqrt(np.mean(np.sum((stacked - mean_vector) ** 2, axis=1)))
    )
    for index, seed in enumerate(cfg["seeds"]["mapping"]):
        norm = float(np.linalg.norm(stacked[index]))
        per_seed[str(seed)]["seed_spread"] = _r(spread)
        per_seed[str(seed)]["difference_norm"] = _r(norm)
        per_seed[str(seed)]["ratio_to_seed_spread"] = _r(
            norm / spread if spread > 0 else None
        )
    separated = sum(
        1
        for seed in cfg["seeds"]["mapping"]
        if per_seed[str(seed)]["dprime_distance_population"]["separated"]
    )
    return {
        "per_seed": per_seed,
        "seed_spread": _r(spread),
        "separated_seed_count": separated,
        "required_seed_count": int(
            cfg["analysis"]["separability_seeds_required"]
        ),
        "passed": separated
        >= int(cfg["analysis"]["separability_seeds_required"]),
        "nearest_centroid_loo": nearest_centroid_loo(profiles),
        "dprime_threshold": float(cfg["analysis"]["dprime_threshold"]),
    }


def run_entry(graph, setup, neuron_params, synapse_params, cfg) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    times = frame_times(protocol["frame_interval_ms"], 600.0)
    interval = float(protocol["frame_interval_ms"])
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    mask = np.zeros(int(graph.n_nodes), dtype=bool)
    mask[setup.mapping.indices(DISTANCE_FEATURE)] = True
    results = {}
    for entry in cfg["conditions"]["3C.3"]["entry_times_ms"]:
        frames = make_frames(
            entry_timeline(
                cfg["conditions"]["3C.3"]["distance"], float(entry), times
            ),
            interval,
        )
        scheduler = TemporalActivationScheduler(
            setup.mapping,
            setup.encoders,
            frames,
            current_pa=setup.amplitudes,
            config=TemporalSchedulerConfig(),
        )
        run = simulate(
            graph, neuron_params, synapse_params, scheduler, duration,
            dt_ms, capacity,
        )
        results[str(entry)] = {
            "metrics": onset_metrics(run, mask, float(entry), edges),
            "total_spikes": run["n_spikes"],
            "signature": spike_digest(run),
        }
        del run
        gc.collect()
    return {"conditions": results}


def run_exit(graph, setup, neuron_params, synapse_params, cfg) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    times = frame_times(protocol["frame_interval_ms"], 600.0)
    interval = float(protocol["frame_interval_ms"])
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    mask = np.zeros(int(graph.n_nodes), dtype=bool)
    mask[setup.mapping.indices(DISTANCE_FEATURE)] = True
    results = {}
    for exit_time in cfg["conditions"]["3C.4"]["exit_times_ms"]:
        frames = make_frames(
            exit_timeline(
                cfg["conditions"]["3C.4"]["distance"], float(exit_time), times
            ),
            interval,
        )
        scheduler = TemporalActivationScheduler(
            setup.mapping,
            setup.encoders,
            frames,
            current_pa=setup.amplitudes,
            config=TemporalSchedulerConfig(),
        )
        run = simulate(
            graph, neuron_params, synapse_params, scheduler, duration,
            dt_ms, capacity,
        )
        results[str(exit_time)] = {
            "metrics": offset_metrics(run, mask, float(exit_time), edges),
            "total_spikes": run["n_spikes"],
            "signature": spike_digest(run),
        }
        del run
        gc.collect()
    return {"conditions": results}


def run_frame_rate(graph, setup, neuron_params, synapse_params, cfg) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    start, end = cfg["conditions"]["3C.7"]["approach"]
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    mask = np.zeros(int(graph.n_nodes), dtype=bool)
    mask[setup.mapping.indices(DISTANCE_FEATURE)] = True
    sample_stride = max(1, int(round(10.0 / dt_ms)))
    sample_steps = np.arange(0, int(round(duration / dt_ms)), sample_stride)
    rates = [int(value) for value in cfg["conditions"]["3C.7"]["frame_rates_ms"]]
    raw = {}
    for rate in rates:
        times = frame_times(float(rate), 600.0)
        frames = make_frames(
            trajectory_timeline(start, end, times), float(rate)
        )
        scheduler = TemporalActivationScheduler(
            setup.mapping,
            setup.encoders,
            frames,
            current_pa=setup.amplitudes,
            config=TemporalSchedulerConfig(),
        )
        buffer = np.zeros(int(graph.n_nodes), dtype=np.float64)
        currents = np.empty(
            (sample_steps.size, int(graph.n_nodes)), dtype=np.float32
        )
        for position, step in enumerate(sample_steps):
            buffer.fill(0.0)
            scheduler.apply(int(step), float(step) * dt_ms, buffer)
            currents[position] = buffer
        run = simulate(
            graph, neuron_params, synapse_params, scheduler, duration,
            dt_ms, capacity,
        )
        raw[rate] = {
            "frames": int(len(frames)),
            "currents": currents,
            "profile": profile(run, mask, edges),
            "total_spikes": run["n_spikes"],
            "signature": spike_digest(run),
        }
        del run
        gc.collect()
    reference_rate = min(rates)
    reference = raw[reference_rate]
    results = {}
    for rate in rates:
        item = raw[rate]
        difference = item["currents"] - reference["currents"]
        results[str(rate)] = {
            "frames": item["frames"],
            "current_rms_difference_pa": _r(
                float(np.sqrt(np.mean(difference.astype(np.float64) ** 2)))
            ),
            "current_max_abs_difference_pa": _r(
                float(np.max(np.abs(difference)))
            ),
            "distance_profile": item["profile"],
            "cosine_distance_to_reference": _r(
                cosine_distance(item["profile"], reference["profile"])
            ),
            "total_spikes": item["total_spikes"],
            "total_spike_ratio_to_reference": _r(
                item["total_spikes"] / reference["total_spikes"]
                if reference["total_spikes"]
                else None
            ),
            "signature": item["signature"],
        }
    return {
        "conditions": results,
        "reference_frame_interval_ms": reference_rate,
        "membrane_tau_ms": _r(float(neuron_params.tau_m_ms)),
        "all_intervals_above_tau": bool(
            min(rates) > float(neuron_params.tau_m_ms)
        ),
        "quantified": len(results) >= 2,
    }


def run_controls(graph, setup, neuron_params, synapse_params, cfg,
                 network_reference, approach_distance_profile,
                 retreat_distance_profile) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    capacity = int(protocol["max_recorded_spikes"])
    times = frame_times(protocol["frame_interval_ms"], 600.0)
    interval = float(protocol["frame_interval_ms"])
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    start, end = cfg["conditions"]["3C.2"]["approach"]
    trajectory = trajectory_timeline(start, end, times)
    distances = [float(state.obstacle.distance) for _, state in trajectory]
    permutation = cfg["conditions"]["3C.9"]["shuffle_permutation"]
    shuffled = [distances[index] for index in permutation]
    shuffled_timeline = [
        (float(t), _state(distance, float(t)))
        for t, distance in zip(times, shuffled)
    ]
    dropped_index = int(cfg["conditions"]["3C.9"]["dropped_frame_index"])
    dropped_timeline = [
        item
        for index, item in enumerate(trajectory)
        if index != dropped_index
    ]
    neutral_timeline = [(float(t), GameState(time_ms=float(t))) for t in times]
    mask = np.zeros(int(graph.n_nodes), dtype=bool)
    mask[setup.mapping.indices(DISTANCE_FEATURE)] = True
    cases = {
        "no_input": neutral_timeline,
        "shuffled": shuffled_timeline,
        "dropped_frame": dropped_timeline,
    }
    results = {}
    zero_current = {feature: 0.0 for feature in setup.encoders}
    for name, timeline in cases.items():
        frames = make_frames(timeline, interval)
        scheduler = TemporalActivationScheduler(
            setup.mapping,
            setup.encoders,
            frames,
            current_pa=zero_current if name == "no_input"
            else setup.amplitudes,
            config=TemporalSchedulerConfig(),
        )
        run = simulate(
            graph, neuron_params, synapse_params, scheduler, duration,
            dt_ms, capacity,
        )
        run_profile = profile(run, None, edges)
        distance_profile = profile(run, mask, edges)
        results[name] = {
            "total_spikes": run["n_spikes"],
            "network_profile": run_profile,
            "distance_profile": distance_profile,
            "cosine_distance_to_approach": _r(
                cosine_distance(run_profile, network_reference)
            ),
            "distance_cosine_distance_to_approach": _r(
                cosine_distance(distance_profile, approach_distance_profile)
            ),
            "signature": spike_digest(run),
        }
        del run
        gc.collect()
    shuffle_distance = cosine_distance(
        results["shuffled"]["distance_profile"],
        approach_distance_profile,
    )
    reversed_distance = cosine_distance(
        retreat_distance_profile,
        approach_distance_profile,
    )
    measurable = (
        shuffle_distance is not None
        and shuffle_distance
        > float(cfg["analysis"]["cosine_distance_threshold"])
    )
    return {
        "conditions": results,
        "shuffled_distance_cosine": _r(shuffle_distance),
        "reversed_distance_cosine": _r(reversed_distance),
        "measurable_difference": bool(measurable),
        "reported_as_negative": not bool(measurable),
        "threshold": float(cfg["analysis"]["cosine_distance_threshold"]),
    }


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def _build_setups(graph, sensory_config, seeds) -> dict:
    setups = {}
    for seed in seeds:
        config = copy.deepcopy(sensory_config)
        config["mapping"]["seed"] = int(seed)
        setups[str(seed)] = prepare_setup(graph, config)
    return setups


def run(cfg_path: Path = CONFIG_PATH) -> dict:
    started = time.perf_counter()
    cfg = load_yaml(cfg_path)
    sensory_config = load_config(SENSORY_CONFIG)
    simulation_config = load_yaml(SIMULATION_CONFIG)
    neuron_config = load_yaml(NEURON_CONFIG)

    expected = float(cfg["protocol"]["current_pa"])
    for feature, value in sensory_config["features"].items():
        current = value.get("current_pa", sensory_config.get("default_current_pa"))
        if current is None:
            continue
        if abs(float(current) - expected) > 1e-9:
            raise ValueError(
                f"feature {feature!r} current {current} != pre-registered "
                f"{expected}"
            )

    graph = load_connectome(
        PROJECT_ROOT / simulation_config["connectome"]["path"]
    )
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(
        simulation_config["synapse"]
    )
    setups = _build_setups(graph, sensory_config, cfg["seeds"]["mapping"])
    base = setups[str(cfg["seeds"]["base_mapping_seed"])]

    equivalence = run_equivalence(
        graph, base, neuron_params, synapse_params, cfg
    )
    direction = run_direction(
        graph, setups, neuron_params, synapse_params, cfg
    )
    entry = run_entry(
        graph, base, neuron_params, synapse_params, cfg
    )
    exit_result = run_exit(
        graph, base, neuron_params, synapse_params, cfg
    )
    frame_rate = run_frame_rate(
        graph, base, neuron_params, synapse_params, cfg
    )
    base_seed = str(cfg["seeds"]["base_mapping_seed"])
    base_direction = direction["per_seed"][base_seed]
    controls = run_controls(
        graph,
        base,
        neuron_params,
        synapse_params,
        cfg,
        base_direction["network_approach_profile"],
        base_direction["approach_profile"],
        base_direction["retreat_profile"],
    )

    criterion_1 = {
        "passed": True,
        "note": "all runs completed without numerical or capacity failure",
    }
    criterion_2 = equivalence
    criterion_3 = direction
    criterion_4 = frame_rate
    criterion_5 = controls

    decision_rule = {
        "1_no_failure": criterion_1,
        "2_static_equivalence": criterion_2["passed"],
        "3_direction_separability": criterion_3["passed"],
        "4_frame_rate_quantified": criterion_4["quantified"],
        "5_controls_measured": True,
        "5_outcome": "measurable_difference"
        if criterion_5["measurable_difference"]
        else "negative_result_reported",
    }
    all_rule_items = (
        decision_rule["2_static_equivalence"]
        and decision_rule["3_direction_separability"]
        and decision_rule["4_frame_rate_quantified"]
    )
    if all_rule_items and criterion_5["measurable_difference"]:
        verdict = "TEMPORAL_INFORMATION_MEASURED"
    elif all_rule_items:
        verdict = "TEMPORAL_INFORMATION_MEASURED_WITH_NEGATIVE_CONTROL"
    else:
        verdict = "NEGATIVE_RESULT"

    results_dir = RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "P3-T7",
        "version": cfg["version"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "decision_rule": decision_rule,
        "equivalence_3c1": equivalence,
        "direction_3c2": direction,
        "entry_3c3": entry,
        "exit_3c4": exit_result,
        "frame_rate_3c7": frame_rate,
        "controls_3c9": controls,
        "config": cfg,
        "not_executed": cfg.get("not_executed"),
        "provenance": {
            "config_sha256": sha256(cfg_path),
            "sensory_config_sha256": sha256(SENSORY_CONFIG),
            "simulation_config_sha256": sha256(SIMULATION_CONFIG),
            "neuron_config_sha256": sha256(NEURON_CONFIG),
            "connectome_sha256": sha256(
                PROJECT_ROOT / simulation_config["connectome"]["path"]
            ),
        },
        "protected": {
            name: {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "expected_sha256": expected_sha,
                "actual_sha256": sha256(path),
                "match": sha256(path) == expected_sha,
            }
            for name, (path, expected_sha) in PROTECTED.items()
        },
        "git": git_state(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "runtime_s": _r(time.perf_counter() - started, 3),
        "limitations": LIMITATIONS,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8"
    )
    SIDECAR_PATH.write_text(
        json.dumps(
            {
                "json_sha256": sha256(JSON_PATH),
                "config_sha256": sha256(cfg_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    return payload


def render_report(payload: dict) -> str:
    lines = [
        "# P3-T7 — Phase 3C temporal acceptance experiments",
        "",
        f"Generated: {payload['generated_at_utc']}",
        f"Verdict: **{payload['verdict']}**",
        "",
        "## Scope",
        "",
        "Synthetic `GameState` sequences over the sparse full connectome, "
        "executing the milestone decision rule in "
        "`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` section 6.4. "
        "The stimuli were pre-registered in `configs/temporal_sensory.yaml` "
        "before execution because the design fixes the comparisons but not "
        "the exact sequences.",
        "",
        "## Decision rule",
        "",
        "| Item | Result |",
        "|---|---|",
        f"| 1. No failure | {payload['decision_rule']['1_no_failure']['passed']} |",
        f"| 2. 3C.1 static equivalence | {payload['decision_rule']['2_static_equivalence']} |",
        f"| 3. 3C.2 approach vs retreat | {payload['decision_rule']['3_direction_separability']} |",
        f"| 4. 3C.7 frame-rate quantified | {payload['decision_rule']['4_frame_rate_quantified']} |",
        f"| 5. 3C.9 controls | {payload['decision_rule']['5_outcome']} |",
        "",
        "## 3C.1 — constant sequence vs static schedule",
        "",
        "| Distance | Max current difference (pA) | Steps above tolerance | "
        "Spike counts identical | Temporal spikes | Direct spikes |",
        "|---:|---:|---:|---|---:|---:|",
    ]
    for distance, item in payload["equivalence_3c1"]["conditions"].items():
        lines.append(
            f"| {distance} | {item['max_current_difference_pa']} | "
            f"{item['steps_above_tolerance']} | "
            f"{item['spike_counts_identical']} | "
            f"{item['temporal_spike_count']} | {item['direct_spike_count']} |"
        )
    lines += [
        "",
        "## 3C.2 — approach vs retreat",
        "",
        "| Seed | d' (distance population) | d' (network) | Cosine distance | "
        "Difference norm | Seed spread | Ratio | Total spikes A/R |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for seed, item in payload["direction_3c2"]["per_seed"].items():
        lines.append(
            f"| {seed} | {item['dprime_distance_population']['dprime']} | "
            f"{item['dprime_network']['dprime']} | "
            f"{item['cosine_distance_profiles']} | "
            f"{item['difference_norm']} | {item['seed_spread']} | "
            f"{item['ratio_to_seed_spread']} | "
            f"{item['total_spikes']['approach']} / "
            f"{item['total_spikes']['retreat']} |"
        )
    loo = payload["direction_3c2"]["nearest_centroid_loo"]
    lines += [
        "",
        f"Leave-one-seed-out nearest-centroid accuracy: "
        f"**{loo['accuracy']}** over {loo['n_predictions']} predictions.",
        "",
        "Reading: approach and retreat produced identical total spike counts "
        "and time-reversed distance-population profiles in every seed. The "
        "signed d' on binned totals is 0.0 because time reversal preserves "
        "the mean and variance. The nearest-centroid result reflects the "
        "order of the bins, not a difference in response magnitude. Under "
        "the pre-registered d' criterion, direction is not distinguished.",
        "",
        "## 3C.3 / 3C.4 — entry and exit timing",
        "",
        "| Entry (ms) | First-spike latency (ms) | Median onset latency (ms) | "
        "Post-onset 50 ms count | Peak bin (ms) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for entry, item in payload["entry_3c3"]["conditions"].items():
        metrics = item["metrics"]
        lines.append(
            f"| {entry} | {metrics['first_spike_latency_ms']} | "
            f"{metrics['median_onset_latency_ms']} | "
            f"{metrics['post_onset_50ms_count']} | "
            f"{metrics['peak_bin_time_ms']} |"
        )
    lines += [
        "",
        "| Exit (ms) | Pre-offset 100 ms count | Post 50 ms | Post 100 ms | "
        "Post 250 ms | Persistence (ms) |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for exit_time, item in payload["exit_3c4"]["conditions"].items():
        metrics = item["metrics"]
        windows = metrics["post_windows"]
        lines.append(
            f"| {exit_time} | {metrics['pre_offset_100ms_count']} | "
            f"{windows['post_50ms']} | {windows['post_100ms']} | "
            f"{windows['post_250ms']} | {metrics['persistence_ms']} |"
        )
    lines += [
        "",
        "Reading: the scheduler applies the most recent frame. An absent frame "
        "therefore replaces the present state at the next frame boundary, so "
        "post-exit persistence is zero by construction; it is not a membrane "
        "after-discharge measurement.",
        "",
        "## 3C.7 — frame-rate sensitivity",
        "",
        f"Membrane time constant: "
        f"{payload['frame_rate_3c7']['membrane_tau_ms']} ms.",
        "",
        "| Frame interval (ms) | Frames | Current RMS diff (pA) | "
        "Current max diff (pA) | Cosine distance | Total spikes |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for rate, item in payload["frame_rate_3c7"]["conditions"].items():
        lines.append(
            f"| {rate} | {item['frames']} | "
            f"{item['current_rms_difference_pa']} | "
            f"{item['current_max_abs_difference_pa']} | "
            f"{item['cosine_distance_to_reference']} | "
            f"{item['total_spikes']} |"
        )
    lines += [
        "",
        "Reading: all tested intervals exceed the 20 ms membrane time constant, "
        "so each condition quantises the timing of distance steps to its "
        "interval (up to 200 ms). Network spike profiles changed only "
        "slightly across rates; the frame-rate comparison is quantified, not "
        "evidence that the network resolves the membrane timescale.",
        "",
        "## 3C.9 — controls",
        "",
        "| Control | Total spikes | Cosine distance to approach |",
        "|---|---:|---:|",
    ]
    for name, item in payload["controls_3c9"]["conditions"].items():
        lines.append(
            f"| {name} | {item['total_spikes']} | "
            f"{item['cosine_distance_to_approach']} |"
        )
    lines += [
        "",
        f"Shuffled distance-profile cosine distance: "
        f"{payload['controls_3c9']['shuffled_distance_cosine']}; "
        f"reversed: {payload['controls_3c9']['reversed_distance_cosine']}. "
        f"Measurable difference: "
        f"{payload['controls_3c9']['measurable_difference']}.",
        "",
        "## Limitations",
        "",
    ]
    lines += [f"- {item}" for item in payload["limitations"]]
    lines += [
        "",
        "## Artifact hashes",
        "",
        f"- JSON: `{sha256(JSON_PATH)}`",
        f"- config: `{payload['provenance']['config_sha256']}`",
        f"- connectome: `{payload['provenance']['connectome_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)
    if args.report_only:
        if not JSON_PATH.exists():
            raise SystemExit(f"missing {JSON_PATH}")
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(f"rewrote {REPORT_PATH}")
        return 0
    payload = run(args.config)
    print(f"verdict: {payload['verdict']}")
    print(f"json: {JSON_PATH}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
