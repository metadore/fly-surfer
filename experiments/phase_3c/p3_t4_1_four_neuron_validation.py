"""P3-T4.1 four-neuron calibration-point validation.

Compares the four-neuron obstacle-distance population selected in Phase 3A.5
against the frozen twelve-neuron population of ``configs/sensory_config.yaml``
under the Phase 3C temporal stimulus framework.

The experiment is deterministic: the simulator has zero background and zero
noise, so paired 4-vs-12 runs at the same mapping seed differ only through the
configuration under test. ``seeds`` here are mapping permutations, not
biological replicates, and no inferential statistic is computed.

This module only adds current to the simulator through the existing
``TemporalActivationScheduler``. It does not change the neuron model, synapse
model, connectome or global simulation parameters.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import gc
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
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
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402
from sensory.temporal_scheduler import (  # noqa: E402
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "p3_t4_1_four_neuron_validation.yaml"
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
TEMPORAL_CONFIG = PROJECT_ROOT / "configs" / "temporal_sensory.yaml"
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
PREREG_PATH = (
    PROJECT_ROOT / "docs" / "P3_T4_1_FOUR_NEURON_VALIDATION_PREREGISTRATION.md"
)
RESULTS_DIR = PROJECT_ROOT / "experiments" / "phase_3c" / "results"
PREFLIGHT_JSON = RESULTS_DIR / "p3_t4_1_preflight.json"
JSON_PATH = RESULTS_DIR / "p3_t4_1_four_neuron_validation.json"
SIDECAR_PATH = RESULTS_DIR / "p3_t4_1_four_neuron_validation.sidecar.json"
REPORT_PATH = RESULTS_DIR / "p3_t4_1_four_neuron_validation_report.md"

FEATURE = "obstacle_distance"

PROTECTED = {
    "README.md": (
        PROJECT_ROOT / "README.md",
        "9dab9dc47281261c6c60996764adaf951276c173e5c40acce91b6e2e9914ef54",
    ),
    "connectome.npz": (
        PROJECT_ROOT / "datasets" / "processed" / "connectome.npz",
        "3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8",
    ),
}

# Values frozen before execution. The runner asserts the configuration
# matches these, so a silent config edit cannot change the experiment.
EXPECTED = {
    "duration_ms": 600.5,
    "frame_interval_ms": 50.0,
    "bin_ms": 50.0,
    "current_pa": 200.0,
    "sigma_fraction": 0.20,
    "baseline_pa": 0.0,
    "background_current_pa": 0.0,
    "noise_std_pa": 0.0,
    "max_recorded_spikes": 6_000_000,
    "seeds": [20261104, 20261105, 20261106],
    "constant_distances": [0.15, 0.55, 0.90],
    "approach": [0.90, 0.15],
    "retreat": [0.15, 0.90],
    "frame_rates": [200, 100, 50],
    "ordering_seeds_required": 2,
    "dprime_threshold": 1.0,
    "separability_seeds_required": 2,
    "cosine_distance_threshold": 0.01,
    "determinism_condition": "approach",
    "determinism_seed": 20261104,
}

DEVIATIONS = [
    {
        "id": "attempt1_report_render_defect",
        "stage": (
            "after all 75 simulations of attempt 1 and after the result JSON "
            "was written; report and sidecar were not written"
        ),
        "detail": (
            "render_report read payload['populations'] instead of "
            "payload['protocol']['populations'] and raised KeyError after the "
            "campaign finished."
        ),
        "protocol_effect": (
            "none: stimuli, seeds, metrics, thresholds and decision rules were "
            "unchanged; only report serialisation was affected"
        ),
        "resolution": (
            "render_report corrected and the full campaign rerun from scratch; "
            "attempt 1 JSON preserved as "
            "p3_t4_1_four_neuron_validation_attempt1_report_defect.json"
        ),
        "attempt1_output_sha256": (
            "337c9a6e9d7cd7936d66b630118ba757ebe1558fed509c6974bc5efe23edca35"
        ),
        "runner_sha256_at_registration": (
            "f3e5dc1ec2afdd957869079c7654a832ede8e088da472a16d9e7d1f218b8a163"
        ),
    }
]

LIMITATIONS = [
    "The four-neuron point is a different encoder bank as well as a smaller "
    "population: the frozen Phase 3A gaussian encoder places n_neurons "
    "preferred stimuli on a linspace, so its four units are not a subset of "
    "the twelve units. The primary contrast is therefore configuration-level.",
    "The twelve-neuron configuration stimulates about three times the number "
    "of obstacle-distance cells and injects about three times the total "
    "current (per-neuron amplitude is held at 200 pA in both). No amplitude "
    "normalisation is applied.",
    "The P12S control keeps the twelve-neuron encoder and mapping but zeroes "
    "current in all but the four cells of the four-neuron mapping; it "
    "separates 'more driven cells' from 'four-cell retuning' descriptively.",
    "Sequences are synthetic GameState lists, not perceived scenes; no "
    "detector, tracker or recognition stage is involved.",
    "Only the mapping seed varies. The simulator is deterministic with zero "
    "background and zero noise, so seed spread is mapping-realisation spread.",
    "Distances are dimensionless image-geometry proxies used by the Phase 3A "
    "encoder, not metres.",
    "Bins within one run are not independent samples; d' is descriptive and "
    "the 1.0 threshold is copied from the Phase 3C pre-registration.",
    "Spikes are model output under configured assumptions, not measured "
    "biological activity; no biological superiority is implied by any count.",
    "No action is selected anywhere in this chain.",
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def git_state() -> dict:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PROJECT_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    status = [
        line
        for line in subprocess.run(
            ["git", "status", "--porcelain"], cwd=PROJECT_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    ]
    return {
        "head": head,
        "branch": branch,
        "working_tree_dirty": bool(status),
        "n_status_entries": len(status),
        "staged_changes": any(
            line[0] not in " ?" for line in status
        ),
    }


def _r(value: float | None, digits: int = 6):
    if value is None:
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _diff_paths(left, right, prefix=()) -> list[list[str]]:
    """Configuration paths whose values differ between two dicts."""
    if isinstance(left, dict) and isinstance(right, dict):
        paths = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                paths.append(list(prefix) + [str(key)])
                continue
            paths.extend(_diff_paths(left[key], right[key], prefix + (str(key),)))
        return paths
    if left != right:
        return [list(prefix)]
    return []


def load_protocol(path: Path = CONFIG_PATH) -> dict:
    cfg = load_yaml(path)
    if not isinstance(cfg, dict) or cfg.get("phase") != "P3-T4.1":
        raise ValueError("protocol must declare phase P3-T4.1")
    protocol = cfg["protocol"]
    analysis = cfg["analysis"]
    checks = {
        "duration_ms": protocol["duration_ms"],
        "frame_interval_ms": protocol["frame_interval_ms"],
        "bin_ms": protocol["bin_ms"],
        "current_pa": protocol["current_pa"],
        "sigma_fraction": protocol["sigma_fraction"],
        "baseline_pa": protocol["baseline_pa"],
        "background_current_pa": protocol["background_current_pa"],
        "noise_std_pa": protocol["noise_std_pa"],
        "max_recorded_spikes": protocol["max_recorded_spikes"],
        "seeds": cfg["seeds"]["mapping"],
        "constant_distances": cfg["conditions"]["constant_distances"],
        "approach": cfg["conditions"]["approach"],
        "retreat": cfg["conditions"]["retreat"],
        "frame_rates": cfg["conditions"]["frame_rates_ms"],
        "ordering_seeds_required": analysis["ordering_seeds_required"],
        "dprime_threshold": analysis["dprime_threshold"],
        "separability_seeds_required": analysis["separability_seeds_required"],
        "cosine_distance_threshold": analysis["cosine_distance_threshold"],
        "determinism_condition": analysis["determinism_condition"],
        "determinism_seed": analysis["determinism_seed"],
    }
    for key, expected in EXPECTED.items():
        actual = checks[key]
        if isinstance(expected, list):
            if len(expected) != len(actual) or any(
                abs(float(item) - float(reference)) > 1e-9
                for item, reference in zip(actual, expected)
            ):
                raise ValueError(
                    f"protocol {key}={actual!r} != pre-registered {expected!r}"
                )
        elif isinstance(expected, float):
            if abs(float(actual) - expected) > 1e-9:
                raise ValueError(
                    f"protocol {key}={actual!r} != pre-registered {expected!r}"
                )
        elif isinstance(expected, str):
            if str(actual) != expected:
                raise ValueError(
                    f"protocol {key}={actual!r} != pre-registered {expected!r}"
                )
        elif int(actual) != int(expected):
            raise ValueError(
                f"protocol {key}={actual!r} != pre-registered {expected!r}"
            )
    if cfg["protocol"]["active_features"] != [FEATURE]:
        raise ValueError("only obstacle_distance may be an active feature")
    return cfg


def assert_sources(protocol: dict) -> None:
    """Protocol constants must match the frozen sensory and temporal configs."""
    sensory = load_config(SENSORY_CONFIG)
    temporal = load_yaml(TEMPORAL_CONFIG)["protocol"]
    feature = sensory["features"][FEATURE]
    if abs(float(feature["current_pa"]) - EXPECTED["current_pa"]) > 1e-9:
        raise ValueError("sensory obstacle_distance current differs from protocol")
    if abs(float(feature["sigma_fraction"]) - EXPECTED["sigma_fraction"]) > 1e-9:
        raise ValueError("sensory sigma_fraction differs from protocol")
    if abs(float(feature["baseline"]) - EXPECTED["baseline_pa"]) > 1e-9:
        raise ValueError("sensory baseline differs from protocol")
    for key in ("duration_ms", "frame_interval_ms", "bin_ms"):
        if abs(float(temporal[key]) - EXPECTED[key]) > 1e-9:
            raise ValueError(f"temporal {key} differs from protocol")
    if float(protocol["protocol"]["duration_ms"]) != EXPECTED["duration_ms"]:
        raise ValueError("protocol duration differs from expectation")
    settings = load_yaml(SIMULATION_CONFIG)
    external = settings.get("external_input", {})
    if float(external.get("background_current_pa", 0.0)) != 0.0:
        raise ValueError("simulation config has non-zero background current")
    if float(external.get("noise_std_pa", 0.0)) != 0.0:
        raise ValueError("simulation config has non-zero noise")


def build_setup(graph, base_config: dict, n_neurons: int, seed: int):
    config = copy.deepcopy(base_config)
    config["mapping"]["seed"] = int(seed)
    config["features"][FEATURE]["n_neurons"] = int(n_neurons)
    config["mapping"]["populations"][FEATURE]["n_neurons"] = int(n_neurons)
    setup = prepare_setup(graph, config)
    if int(setup.mapping.size(FEATURE)) != int(n_neurons):
        raise ValueError("mapping size does not match the requested population")
    return setup, config


def population_indices(setup) -> np.ndarray:
    return np.asarray(
        [int(value) for value in setup.mapping.indices(FEATURE)], dtype=np.int64
    )


def state_at(distance: float | None, time_ms: float) -> GameState:
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


def frame_times(interval_ms: float, duration_ms: float = 600.0) -> np.ndarray:
    return np.arange(0.0, float(duration_ms) + 1e-9, float(interval_ms))


def make_frames(timeline, interval_ms: float) -> list[TemporalFrame]:
    frames: list[TemporalFrame] = []
    previous = 0.0
    for index, (time_ms, state) in enumerate(timeline):
        frames.append(
            TemporalFrame(
                frame_index=index,
                frame_id=f"p3t41-{index:02d}",
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


def constant_timeline(distance: float, times) -> list:
    return [(float(t), state_at(distance, float(t))) for t in times]


def trajectory_distance(start: float, end: float, time_ms: float,
                        duration_ms: float = 600.0) -> float:
    fraction = min(max(float(time_ms) / float(duration_ms), 0.0), 1.0)
    return float(start) + (float(end) - float(start)) * fraction


def trajectory_timeline(start: float, end: float, times) -> list:
    return [
        (
            float(t),
            state_at(trajectory_distance(start, end, float(t)), float(t)),
        )
        for t in times
    ]


class RestrictedScheduler(TemporalActivationScheduler):
    """Temporal scheduler that drives only a subset of the active population."""

    def __init__(self, *args, stimulated_indices, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        subset = np.asarray(sorted(int(v) for v in stimulated_indices), np.int64)
        if not set(subset.tolist()).issubset(set(self._indices.tolist())):
            raise ValueError("stimulated subset is not inside the mapped neurons")
        keep = np.isin(self._indices, subset)
        for values in self._frame_values:
            values[~keep] = 0.0
        for values in self._pulse_values:
            values[~keep] = 0.0
        self._keep = keep

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._indices[self._keep]


def build_scheduler(setup, frames, stimulated_subset=None):
    scheduler_cls = (
        TemporalActivationScheduler if stimulated_subset is None
        else RestrictedScheduler
    )
    kwargs = {}
    if stimulated_subset is not None:
        kwargs["stimulated_indices"] = stimulated_subset
    return scheduler_cls(
        setup.mapping,
        setup.encoders,
        frames,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
        active_features=[FEATURE],
        **kwargs,
    )


def spike_digest(payload: dict) -> str:
    digest = hashlib.sha256()
    digest.update(payload["times_ms"].tobytes())
    digest.update(payload["neuron_indices"].tobytes())
    return digest.hexdigest()


def voltage_stats(values: np.ndarray) -> dict:
    if values.size == 0:
        return {
            "n": 0, "mean_mv": None, "sd_mv": None, "min_mv": None,
            "p10_mv": None, "median_mv": None, "p90_mv": None, "max_mv": None,
        }
    return {
        "n": int(values.size),
        "mean_mv": _r(float(np.mean(values))),
        "sd_mv": _r(float(np.std(values))),
        "min_mv": _r(float(np.min(values))),
        "p10_mv": _r(float(np.percentile(values, 10))),
        "median_mv": _r(float(np.percentile(values, 50))),
        "p90_mv": _r(float(np.percentile(values, 90))),
        "max_mv": _r(float(np.max(values))),
    }


def profile(payload: dict, mask: np.ndarray | None, edges: np.ndarray) -> list:
    times = payload["times_ms"]
    indices = payload["neuron_indices"]
    if mask is not None:
        times = times[mask[indices]]
    counts, _ = np.histogram(times, bins=edges)
    return [int(value) for value in counts]


def cosine_distance(first, second) -> float | None:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return None
    return float(1.0 - float(np.dot(a, b)) / denom)


def dprime(first, second, threshold: float) -> dict:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    var_a = float(np.var(a, ddof=1)) if a.size > 1 else 0.0
    var_b = float(np.var(b, ddof=1)) if b.size > 1 else 0.0
    denom = math.sqrt((var_a + var_b) / 2.0)
    diff = float(np.mean(a) - np.mean(b))
    value = diff / denom if denom > 0 else None
    separated = (denom == 0.0 and abs(diff) > 0.0) or (
        value is not None and abs(value) > float(threshold)
    )
    return {
        "mean_approach": _r(float(np.mean(a))),
        "mean_retreat": _r(float(np.mean(b))),
        "sd_approach": _r(math.sqrt(var_a)),
        "sd_retreat": _r(math.sqrt(var_b)),
        "difference": _r(diff),
        "dprime": _r(value),
        "zero_variance": denom == 0.0,
        "separated": bool(separated),
    }


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------


def simulate(graph, neuron_params, synapse_params, scheduler, duration_ms,
             dt_ms, capacity: int, stimulated_indices: np.ndarray,
             voltage_samples_ms) -> dict:
    n_steps = int(round(float(duration_ms) / float(dt_ms)))
    n = int(graph.n_nodes)
    neurons = LIFPopulation(n, neuron_params, dt_ms)
    synapses = SynapseModel(graph, synapse_params, dt_ms)
    recorder = SpikeRecorder(n, int(capacity))
    current = np.zeros(n, dtype=np.float64)
    stimulated_mask = np.zeros(n, dtype=bool)
    stimulated_mask[stimulated_indices] = True
    samples = {
        int(round(float(t) / float(dt_ms))): float(t) for t in voltage_samples_ms
    }
    voltage = []
    started = time.perf_counter()
    for step in range(n_steps):
        synapses.advance()
        current.fill(0.0)
        current += synapses.synaptic_current_pa
        scheduler.apply(step, step * float(dt_ms), current)
        spikes = neurons.step(current)
        recorder.record(step, spikes, float(dt_ms))
        if step in samples:
            potential = neurons.membrane_potential
            voltage.append(
                {
                    "time_ms": samples[step],
                    "step": int(step),
                    "stimulated": voltage_stats(potential[stimulated_mask]),
                    "outside": voltage_stats(potential[~stimulated_mask]),
                }
            )
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
        "voltage": voltage,
    }
    del neurons, synapses, recorder
    gc.collect()
    return payload


def current_trace(scheduler, n_nodes: int, stimulated_indices: np.ndarray,
                  duration_ms: float, dt_ms: float,
                  stride_ms: float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    stride = max(1, int(round(float(stride_ms) / float(dt_ms))))
    steps = np.arange(0, int(round(float(duration_ms) / float(dt_ms))), stride)
    stimulated = np.empty((steps.size, stimulated_indices.size), dtype=np.float64)
    network_rms = np.empty(steps.size, dtype=np.float64)
    buffer = np.zeros(int(n_nodes), dtype=np.float64)
    for position, step in enumerate(steps):
        buffer.fill(0.0)
        scheduler.apply(int(step), float(step) * float(dt_ms), buffer)
        stimulated[position] = buffer[stimulated_indices]
        network_rms[position] = float(np.sqrt(np.mean(buffer * buffer)))
    return stimulated, network_rms


def run_condition(graph, setup, neuron_params, synapse_params, cfg,
                  name: str, timeline, interval_ms: float,
                  stimulated_indices: np.ndarray,
                  stimulated_subset=None) -> dict:
    protocol = cfg["protocol"]
    dt_ms = float(setup.dt_ms)
    duration = float(protocol["duration_ms"])
    edges = np.arange(0.0, 601.0, float(protocol["bin_ms"]))
    frames = make_frames(timeline, interval_ms)
    scheduler = build_scheduler(setup, frames, stimulated_subset)
    if not np.array_equal(np.sort(scheduler.stimulated_indices), np.sort(stimulated_indices)):
        raise ValueError("scheduler stimulated set does not match the request")
    stim_trace, net_trace = current_trace(
        scheduler, int(graph.n_nodes), stimulated_indices, duration, dt_ms
    )
    run = simulate(
        graph, neuron_params, synapse_params, scheduler, duration, dt_ms,
        int(protocol["max_recorded_spikes"]), stimulated_indices,
        protocol["voltage_sample_times_ms"],
    )
    mask = np.zeros(int(graph.n_nodes), dtype=bool)
    mask[stimulated_indices] = True
    counts = run["counts"]
    stimulated_counts = counts[stimulated_indices]
    outside_counts = counts[~mask]
    times = run["times_ms"]
    indices = run["neuron_indices"]
    selected = mask[indices]
    stim_times = times[selected]
    stim_indices = indices[selected]
    latencies = [
        float(stim_times[stim_indices == neuron].min())
        for neuron in np.unique(stim_indices)
    ]
    payload = {
        "condition": name,
        "n_frames": len(frames),
        "n_spikes_total": int(run["n_spikes"]),
        "n_spikes_stimulated": int(stimulated_counts.sum()),
        "n_spikes_outside": int(outside_counts.sum()),
        "n_active_stimulated": int(np.count_nonzero(stimulated_counts)),
        "n_active_outside": int(np.count_nonzero(outside_counts)),
        "stimulated_firing_rate_hz": _r(
            float(stimulated_counts.sum())
            / (stimulated_indices.size * (run["duration_ms"] / 1000.0))
        ),
        "stimulated_population_rate_hz": _r(
            float(stimulated_counts.sum()) / (run["duration_ms"] / 1000.0)
        ),
        "per_neuron_stimulated": {
            str(int(index)): int(value)
            for index, value in zip(stimulated_indices, stimulated_counts)
        },
        "first_stimulated_spike_latency_ms": _r(min(latencies))
        if latencies
        else None,
        "median_stimulated_first_latency_ms": _r(float(np.median(latencies)))
        if latencies
        else None,
        "profile_stimulated": profile(run, mask, edges),
        "profile_network": profile(run, None, edges),
        "profile_outside": profile(run, ~mask, edges),
        "voltage": run["voltage"],
        "mean_stimulated_current_pa": _r(float(np.mean(stim_trace))),
        "max_per_neuron_current_pa": _r(float(np.max(stim_trace))),
        "mean_network_current_rms_pa": _r(float(np.mean(net_trace))),
        "current_trace_stimulated": np.round(stim_trace, 6).tolist(),
        "current_trace_network_rms": np.round(net_trace, 6).tolist(),
        "digest": spike_digest(run),
        "wall_runtime_s": _r(run["wall_runtime_s"]),
    }
    del run
    gc.collect()
    return payload


# --------------------------------------------------------------------------
# preflight (no simulation)
# --------------------------------------------------------------------------


def population_evidence(graph, base_config, cfg, seed: int) -> dict:
    """Exact indices, root IDs, encoder bank and input currents for one seed."""
    evidence = {}
    for name, spec in cfg["populations"].items():
        setup, config = build_setup(
            graph, base_config, int(spec["mapping_n_neurons"]), seed
        )
        indices = population_indices(setup)
        encoder = setup.encoders[FEATURE]
        population = setup.mapping.populations[FEATURE]
        currents = {}
        for distance in EXPECTED["constant_distances"]:
            frames = make_frames(
                constant_timeline(distance, frame_times(EXPECTED["frame_interval_ms"])),
                EXPECTED["frame_interval_ms"],
            )
            scheduler = build_scheduler(setup, frames)
            values = scheduler._frame_values[0][scheduler._slices[FEATURE]]
            currents[str(distance)] = {
                "per_neuron_pa": [_r(float(value)) for value in values],
                "total_pa": _r(float(values.sum())),
                "max_pa": _r(float(values.max())),
            }
        evidence[name] = {
            "mapping_n_neurons": int(spec["mapping_n_neurons"]),
            "encoder_n_neurons": int(spec["encoder_n_neurons"]),
            "stimulated_cells": spec["stimulated_cells"],
            "indices_in_mapping_order": [int(value) for value in indices],
            "sorted_indices": sorted(int(value) for value in indices),
            "root_ids": {
                key: [int(value) for value in values]
                for key, values in population.root_ids.items()
            },
            "encoder_preferred": [_r(float(value)) for value in encoder.preferred],
            "encoder_sigma": _r(float(encoder.sigma)),
            "injected_current_at_constants": currents,
            "other_feature_sizes": {
                feature: int(setup.mapping.size(feature))
                for feature in setup.encoders
                if feature != FEATURE
            },
            "amplitude_pa": _r(float(setup.amplitudes[FEATURE])),
        }
        del setup
    four = evidence["P4"]["indices_in_mapping_order"]
    twelve = evidence["P12"]["indices_in_mapping_order"]
    evidence["properties"] = {
        "four_is_subset_of_twelve": set(four).issubset(set(twelve)),
        "four_is_prefix_of_twelve": four == twelve[: len(four)],
        "shared_cells": sorted(set(four) & set(twelve)),
    }
    return evidence


def equivalence(graph, base_config, cfg, seed: int) -> dict:
    _, config4 = build_setup(graph, base_config, 4, seed)
    _, config12 = build_setup(graph, base_config, 12, seed)
    paths = _diff_paths(config4, config12)
    expected = [
        ["features", FEATURE, "n_neurons"],
        ["mapping", "populations", FEATURE, "n_neurons"],
    ]
    return {
        "seed": int(seed),
        "differing_paths": paths,
        "expected_paths": expected,
        "only_intended_fields_differ": sorted(paths) == sorted(expected),
    }


def preflight(cfg: dict) -> dict:
    base = load_config(SENSORY_CONFIG)
    graph = load_connectome(PROJECT_ROOT / load_yaml(SIMULATION_CONFIG)["connectome"]["path"])
    seeds = cfg["seeds"]["mapping"]
    evidence = {
        str(seed): {
            "populations": population_evidence(graph, base, cfg, int(seed)),
            "config_equivalence": equivalence(graph, base, cfg, int(seed)),
        }
        for seed in seeds
    }
    for seed, block in evidence.items():
        props = block["populations"]["properties"]
        if not props["four_is_subset_of_twelve"]:
            raise ValueError(f"four cells are not a subset of twelve at {seed}")
        if not props["four_is_prefix_of_twelve"]:
            raise ValueError(f"four cells are not a prefix of twelve at {seed}")
        if not block["config_equivalence"]["only_intended_fields_differ"]:
            raise ValueError(f"configs differ outside the intended fields at {seed}")
    temporal = load_yaml(TEMPORAL_CONFIG)
    acceptance = json.loads(
        (RESULTS_DIR / "temporal_acceptance.json").read_text(encoding="utf-8")
    )
    direction = acceptance.get("conditions", {}).get("3C.2", {})
    selection = json.loads(
        (PROJECT_ROOT / "experiments" / "phase_3_5" / "results" / "selection.json")
        .read_text(encoding="utf-8")
    )
    discrepancy = json.loads(
        (RESULTS_DIR / "p3_t4_calibration_discrepancy.json").read_text(
            encoding="utf-8"
        )
    )
    payload = {
        "phase": "P3-T4.1",
        "version": cfg["version"],
        "mode": "preflight",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": sha256(CONFIG_PATH),
        "sensory_config_sha256": sha256(SENSORY_CONFIG),
        "temporal_config_sha256": sha256(TEMPORAL_CONFIG),
        "seeds": [int(seed) for seed in seeds],
        "population_definitions": cfg["populations"],
        "per_seed": evidence,
        "prior_evidence": {
            "phase_3_5_selection": selection,
            "phase_3_5_selection_has_no_neuron_ids": "neuron_ids" not in selection,
            "phase_3_t4_recorded_indices_4": discrepancy["mapping"]["comparison"][
                "indices_4"
            ],
            "phase_3_t4_recorded_indices_12": discrepancy["mapping"]["comparison"][
                "indices_12"
            ],
            "phase_3_t7_3C2": {
                "dprime_threshold": temporal["analysis"]["dprime_threshold"],
                "direction": direction,
            },
        },
        "protected_hashes": {
            name: {"expected": expected, "actual": sha256(path)}
            for name, (path, expected) in PROTECTED.items()
        },
        "git": git_state(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    return payload


# --------------------------------------------------------------------------
# execution and analysis
# --------------------------------------------------------------------------


def condition_specs(cfg: dict) -> list[dict]:
    conditions = cfg["conditions"]
    interval = float(cfg["protocol"]["frame_interval_ms"])
    times = frame_times(interval)
    specs = [
        {
            "name": f"constant_{distance:.2f}",
            "kind": "constant",
            "distance": float(distance),
            "timeline": constant_timeline(float(distance), times),
            "interval_ms": interval,
        }
        for distance in conditions["constant_distances"]
    ]
    approach = conditions["approach"]
    retreat = conditions["retreat"]
    specs.append(
        {
            "name": "approach",
            "kind": "approach",
            "start": float(approach[0]),
            "end": float(approach[1]),
            "timeline": trajectory_timeline(
                float(approach[0]), float(approach[1]), times
            ),
            "interval_ms": interval,
        }
    )
    specs.append(
        {
            "name": "retreat",
            "kind": "retreat",
            "start": float(retreat[0]),
            "end": float(retreat[1]),
            "timeline": trajectory_timeline(
                float(retreat[0]), float(retreat[1]), times
            ),
            "interval_ms": interval,
        }
    )
    for rate in conditions["frame_rates_ms"]:
        rate = float(rate)
        if abs(rate - interval) < 1e-9:
            continue
        rate_times = frame_times(rate)
        specs.append(
            {
                "name": f"frame_rate_{int(rate)}",
                "kind": "frame_rate",
                "start": float(approach[0]),
                "end": float(approach[1]),
                "timeline": trajectory_timeline(
                    float(approach[0]), float(approach[1]), rate_times
                ),
                "interval_ms": rate,
            }
        )
    if conditions.get("control_no_input"):
        specs.append(
            {
                "name": "control_no_input",
                "kind": "control",
                "distance": None,
                "timeline": constant_timeline(None, times),
                "interval_ms": interval,
            }
        )
    return specs


def run_population(graph, base_config, cfg, name: str, spec: dict,
                   neuron_params, synapse_params) -> dict:
    seed_results = {}
    for seed in cfg["seeds"]["mapping"]:
        setup, _ = build_setup(graph, base_config, int(spec["mapping_n_neurons"]), int(seed))
        stimulated = population_indices(setup)
        subset = None
        if spec["stimulated_cells"] == "four_neuron_mapping":
            four_setup, _ = build_setup(graph, base_config, 4, int(seed))
            subset = population_indices(four_setup)
            stimulated = subset
            del four_setup
        runs = {}
        for condition in condition_specs(cfg):
            runs[condition["name"]] = run_condition(
                graph, setup, neuron_params, synapse_params, cfg,
                condition["name"], condition["timeline"], condition["interval_ms"],
                stimulated, subset,
            )
        seed_results[str(seed)] = {
            "stimulated_indices": [int(value) for value in stimulated],
            "conditions": runs,
        }
        del setup
        gc.collect()
    return seed_results


def analyse_seed(cfg: dict, runs: dict) -> dict:
    constants = [f"constant_{distance:.2f}" for distance in EXPECTED["constant_distances"]]
    stim_counts = [runs[name]["n_spikes_stimulated"] for name in constants]
    network_counts = [runs[name]["n_spikes_total"] for name in constants]
    edges = np.arange(0.0, 601.0, float(cfg["protocol"]["bin_ms"]))

    def ordering(counts):
        strict_up = all(b > a for a, b in zip(counts, counts[1:]))
        strict_down = all(b < a for a, b in zip(counts, counts[1:]))
        strict = strict_up or strict_down
        return {
            "counts": [int(value) for value in counts],
            "distinct_levels": len(set(int(value) for value in counts)),
            "strictly_increasing": strict_up,
            "strictly_decreasing": strict_down,
            "ordered": strict,
            "direction": "increasing_with_distance" if strict_up else (
                "decreasing_with_distance" if strict_down else None
            ),
        }

    approach = runs["approach"]
    retreat = runs["retreat"]
    direction = {
        "stimulated": dprime(
            approach["profile_stimulated"], retreat["profile_stimulated"],
            float(cfg["analysis"]["dprime_threshold"]),
        ),
        "network": dprime(
            approach["profile_network"], retreat["profile_network"],
            float(cfg["analysis"]["dprime_threshold"]),
        ),
        "cosine_stimulated": _r(
            cosine_distance(
                approach["profile_stimulated"], retreat["profile_stimulated"]
            )
        ),
        "cosine_network": _r(
            cosine_distance(approach["profile_network"], retreat["profile_network"])
        ),
        "total_spikes": {
            "approach": approach["n_spikes_total"],
            "retreat": retreat["n_spikes_total"],
        },
        "stimulated_spikes": {
            "approach": approach["n_spikes_stimulated"],
            "retreat": retreat["n_spikes_stimulated"],
        },
    }

    reference = approach
    frame_rate = {}
    for rate in EXPECTED["frame_rates"]:
        if abs(float(rate) - EXPECTED["frame_interval_ms"]) < 1e-9:
            continue
        candidate = runs[f"frame_rate_{int(rate)}"]
        stim_diff = np.asarray(candidate["current_trace_stimulated"]) - np.asarray(
            reference["current_trace_stimulated"]
        )
        net_diff = np.asarray(candidate["current_trace_network_rms"]) - np.asarray(
            reference["current_trace_network_rms"]
        )
        frame_rate[str(rate)] = {
            "n_frames": candidate["n_frames"],
            "current_rms_difference_pa_stimulated": _r(
                float(np.sqrt(np.mean(stim_diff ** 2)))
            ),
            "current_max_abs_difference_pa_stimulated": _r(
                float(np.max(np.abs(stim_diff)))
            ),
            "network_current_rms_difference_pa": _r(
                float(np.sqrt(np.mean(net_diff ** 2)))
            ),
            "profile_cosine_distance_stimulated": _r(
                cosine_distance(
                    candidate["profile_stimulated"],
                    reference["profile_stimulated"],
                )
            ),
            "profile_cosine_distance_network": _r(
                cosine_distance(
                    candidate["profile_network"], reference["profile_network"]
                )
            ),
            "total_spike_ratio_to_reference": _r(
                candidate["n_spikes_total"] / reference["n_spikes_total"]
                if reference["n_spikes_total"]
                else None
            ),
            "stimulated_spike_ratio_to_reference": _r(
                candidate["n_spikes_stimulated"] / reference["n_spikes_stimulated"]
                if reference["n_spikes_stimulated"]
                else None
            ),
        }

    latency = {
        condition: {
            "first_stimulated_spike_latency_ms": item[
                "first_stimulated_spike_latency_ms"
            ],
            "median_stimulated_first_latency_ms": item[
                "median_stimulated_first_latency_ms"
            ],
        }
        for condition, item in runs.items()
    }

    return {
        "ordering_stimulated": ordering(stim_counts),
        "ordering_network": ordering(network_counts),
        "direction": direction,
        "frame_rate": frame_rate,
        "latency": latency,
        "control_no_input": {
            "total_spikes": runs["control_no_input"]["n_spikes_total"],
            "stimulated_spikes": runs["control_no_input"]["n_spikes_stimulated"],
            "outside_spikes": runs["control_no_input"]["n_spikes_outside"],
        },
        "voltage_summary": {
            condition: {
                sample["time_ms"]: {
                    "stimulated": sample["stimulated"],
                    "outside": sample["outside"],
                }
                for sample in item["voltage"]
            }
            for condition, item in runs.items()
        },
    }


def detect_determinism(cfg, graph, base_config, results, neuron_params,
                       synapse_params) -> dict:
    output = {}
    condition_name = cfg["analysis"]["determinism_condition"]
    seed = int(cfg["analysis"]["determinism_seed"])
    spec = next(
        item for item in condition_specs(cfg) if item["name"] == condition_name
    )
    for name, population_spec in cfg["populations"].items():
        setup, _ = build_setup(
            graph, base_config, int(population_spec["mapping_n_neurons"]), seed
        )
        stimulated = population_indices(setup)
        subset = None
        if population_spec["stimulated_cells"] == "four_neuron_mapping":
            four_setup, _ = build_setup(graph, base_config, 4, seed)
            subset = population_indices(four_setup)
            stimulated = subset
            del four_setup
        rerun = run_condition(
            graph, setup, neuron_params, synapse_params, cfg, condition_name,
            spec["timeline"], spec["interval_ms"], stimulated, subset,
        )
        original = results[name][str(seed)]["conditions"][condition_name]["digest"]
        output[name] = {
            "condition": condition_name,
            "seed": seed,
            "original_digest": original,
            "rerun_digest": rerun["digest"],
            "identical": original == rerun["digest"],
            "original_total_spikes": results[name][str(seed)]["conditions"][
                condition_name
            ]["n_spikes_total"],
            "rerun_total_spikes": rerun["n_spikes_total"],
        }
        del setup, rerun
        gc.collect()
    return output


def comparisons(cfg: dict, results: dict) -> dict:
    conditions = [spec["name"] for spec in condition_specs(cfg)]
    seeds = [str(seed) for seed in cfg["seeds"]["mapping"]]
    metrics = ("n_spikes_total", "n_spikes_stimulated", "n_spikes_outside")
    output = {}
    for metric in metrics:
        per_condition = {}
        for condition in conditions:
            values = {
                name: {
                    seed: results[name][seed]["conditions"][condition][metric]
                    for seed in seeds
                }
                for name in ("P4", "P12", "P12S")
            }
            deltas = {
                "P12_minus_P4": {
                    seed: values["P12"][seed] - values["P4"][seed] for seed in seeds
                },
                "P12S_minus_P4": {
                    seed: values["P12S"][seed] - values["P4"][seed] for seed in seeds
                },
                "P12_minus_P12S": {
                    seed: values["P12"][seed] - values["P12S"][seed] for seed in seeds
                },
            }
            consistent = {
                key: (
                    all(value > 0 for value in items.values())
                    or all(value < 0 for value in items.values())
                    or all(value == 0 for value in items.values())
                )
                for key, items in deltas.items()
            }
            per_condition[condition] = {
                "values": values,
                "deltas": deltas,
                "consistent_direction_across_seeds": consistent,
            }
        output[metric] = per_condition
    return output


def hypotheses(cfg: dict, analysis: dict) -> dict:
    seeds = [str(seed) for seed in cfg["seeds"]["mapping"]]
    required = int(cfg["analysis"]["ordering_seeds_required"])
    separable_required = int(cfg["analysis"]["separability_seeds_required"])
    threshold = float(cfg["analysis"]["cosine_distance_threshold"])

    ordering = {}
    for name in ("P4", "P12", "P12S"):
        ordered_seeds = [
            seed
            for seed in seeds
            if analysis[name][seed]["ordering_stimulated"]["ordered"]
        ]
        ordering[name] = {
            "ordered_seeds": ordered_seeds,
            "n_ordered_seeds": len(ordered_seeds),
            "replicates": len(ordered_seeds) >= required,
            "counts_by_seed": {
                seed: analysis[name][seed]["ordering_stimulated"]["counts"]
                for seed in seeds
            },
        }

    separation = {}
    for name in ("P4", "P12", "P12S"):
        separated_seeds = [
            seed
            for seed in seeds
            if analysis[name][seed]["direction"]["stimulated"]["separated"]
        ]
        values = {
            seed: analysis[name][seed]["direction"]["stimulated"]["dprime"]
            for seed in seeds
        }
        separation[name] = {
            "separated_seeds": separated_seeds,
            "n_separated_seeds": len(separated_seeds),
            "separates": len(separated_seeds) >= separable_required,
            "dprime_by_seed": values,
        }

    frame_rate = {}
    for name in ("P4", "P12", "P12S"):
        sensitive = []
        for rate in ("100", "200"):
            values = [
                analysis[name][seed]["frame_rate"][rate][
                    "profile_cosine_distance_stimulated"
                ]
                for seed in seeds
            ]
            if any(
                value is not None and abs(value) > threshold for value in values
            ):
                sensitive.append(rate)
        frame_rate[name] = {
            "rates_above_cosine_threshold": sensitive,
            "cosine_by_rate_seed": {
                rate: {
                    seed: analysis[name][seed]["frame_rate"][rate][
                        "profile_cosine_distance_stimulated"
                    ]
                    for seed in seeds
                }
                for rate in ("100", "200")
            },
        }

    return {
        "H1_ordering_replication": {
            "rule": (
                "strictly increasing stimulated spikes across 0.15/0.55/0.90 "
                f"in >= {required} of 3 mapping seeds"
            ),
            "by_population": ordering,
            "claim_p4_and_not_p12": bool(
                ordering["P4"]["replicates"] and not ordering["P12"]["replicates"]
            ),
        },
        "H2_approach_retreat_separation": {
            "rule": (
                "|d'| > 1.0 on stimulated 50 ms profiles in >= "
                f"{separable_required} of 3 mapping seeds"
            ),
            "by_population": separation,
            "claim_p4_and_not_p12": bool(
                separation["P4"]["separates"] and not separation["P12"]["separates"]
            ),
        },
        "H4_frame_rate_sensitivity": {
            "rule": (
                "stimulated spike-profile cosine distance to the 50 ms "
                f"reference exceeds {threshold} in any seed"
            ),
            "by_population": frame_rate,
        },
    }


def assess(cfg: dict, results: dict, analysis: dict, determinism: dict,
           equivalence_checks: list[dict], protected: dict,
           comparisons_block: dict, hypotheses_block: dict) -> dict:
    checks = {
        "config_equivalence": all(
            item["only_intended_fields_differ"] for item in equivalence_checks
        ),
        "runs_complete": all(
            len(results[name]) == len(cfg["seeds"]["mapping"])
            for name in cfg["populations"]
        ),
        "determinism": all(item["identical"] for item in determinism.values()),
        "protected_hashes_unchanged": all(
            item["expected"] == item["actual"] for item in protected.values()
        ),
    }
    primary_conditions = [
        item for item in comparisons_block["n_spikes_total"].values()
    ]
    any_activity = any(
        value != 0
        for condition in primary_conditions
        for population in condition["values"].values()
        for value in population.values()
    )
    dprime_values = [
        hypotheses_block["H2_approach_retreat_separation"]["by_population"][name][
            "dprime_by_seed"
        ][seed]
        for name in ("P4", "P12", "P12S")
        for seed in [str(item) for item in cfg["seeds"]["mapping"]]
    ]
    dprime_defined = any(value is not None for value in dprime_values)
    if not all(checks.values()):
        verdict = "BLOCKED"
        reason = "an execution check failed"
    elif not any_activity:
        verdict = "INCONCLUSIVE"
        reason = "no spikes in any primary condition"
    elif not dprime_defined:
        verdict = "INCONCLUSIVE"
        reason = "approach/retreat d' undefined in every population and seed"
    else:
        verdict = "PASS"
        reason = "execution checks passed and primary metrics are defined"
    return {
        "verdict": verdict,
        "reason": reason,
        "execution_checks": checks,
        "any_primary_activity": bool(any_activity),
        "dprime_defined": bool(dprime_defined),
        "hypotheses_do_not_change_verdict": True,
    }


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def render_report(payload: dict) -> str:
    lines = []
    add = lines.append
    add("# P3-T4.1 four-neuron calibration-point validation")
    add("")
    add(f"Generated: {payload['generated_at_utc']}")
    add(f"Repository HEAD: `{payload['git']['head']}` (branch `{payload['git']['branch']}`)")
    add(f"Protocol: `{payload['version']}` — `configs/p3_t4_1_four_neuron_validation.yaml`")
    add(f"Verdict: **{payload['assessment']['verdict']}** — {payload['assessment']['reason']}")
    add("")
    add("## 1. Question and design")
    add("")
    add(
        "Does the four-neuron obstacle-distance population selected in Phase "
        "3A.5 produce a measurably different or better response than the frozen "
        "twelve-neuron population under the Phase 3C temporal stimulus "
        "framework? Only the obstacle-distance feature is active; all other "
        "features receive no current. The simulator, neuron model, synapse "
        "model and stimulus schedules are identical across populations."
    )
    add("")
    add("| Population | Mapping | Encoder bank | Driven cells |")
    add("|---|---|---|---|")
    for name, spec in payload["protocol"]["populations"].items():
        add(
            f"| {name} | {spec['mapping_n_neurons']} neurons | "
            f"{spec['encoder_n_neurons']} units | {spec['stimulated_cells']} |"
        )
    add("")
    add("## 2. Exact populations (seed 20261104)")
    add("")
    by_seed = payload["preflight"]["per_seed"]
    for seed in payload["preflight"]["seeds"]:
        block = by_seed[str(seed)]["populations"]
        add(f"### Mapping seed {seed}")
        add("")
        add("| Population | Indices | Root IDs |")
        add("|---|---|---|")
        for name in ("P4", "P12", "P12S"):
            item = block[name]
            roots = item["root_ids"].get("default", [])
            add(
                f"| {name} | {item['indices_in_mapping_order']} | {roots} |"
            )
        add("")
    add("## 3. Conditions and seeds")
    add("")
    add(
        f"Seeds: {payload['preflight']['seeds']}. Duration "
        f"{EXPECTED['duration_ms']} ms, frame interval "
        f"{EXPECTED['frame_interval_ms']} ms, 200 pA per neuron, zero "
        "background and noise. Conditions: three constant distances, "
        "approach, retreat, 100 ms and 200 ms frame rates, no-input control."
    )
    add("")
    add("## 4. Results")
    add("")
    add("### 4.1 Static distance ordering (stimulated spikes)")
    add("")
    add("| Population | Seed 20261104 | Seed 20261105 | Seed 20261106 | Ordered seeds |")
    add("|---|---|---|---|---|")
    h1 = payload["hypotheses"]["H1_ordering_replication"]["by_population"]
    for name in ("P4", "P12", "P12S"):
        item = h1[name]
        counts = item["counts_by_seed"]
        add(
            f"| {name} | {counts[str(20261104)]} | {counts[str(20261105)]} | "
            f"{counts[str(20261106)]} | {item['n_ordered_seeds']}/3 |"
        )
    add("")
    add(
        f"Replication rule (str >= 2 of 3 seeds): "
        f"P4 {h1['P4']['replicates']}, P12 {h1['P12']['replicates']}, "
        f"P12S {h1['P12S']['replicates']}."
    )
    add("")
    add("### 4.2 Approach vs retreat")
    add("")
    add("| Population | d' (20261104) | d' (20261105) | d' (20261106) | Separated seeds |")
    add("|---|---|---|---|---|")
    h2 = payload["hypotheses"]["H2_approach_retreat_separation"]["by_population"]
    for name in ("P4", "P12", "P12S"):
        item = h2[name]
        values = item["dprime_by_seed"]
        add(
            f"| {name} | {values[str(20261104)]} | {values[str(20261105)]} | "
            f"{values[str(20261106)]} | {item['n_separated_seeds']}/3 |"
        )
    add("")
    add("### 4.3 Total spikes by condition and seed")
    add("")
    add("| Condition | P4 | P12 | P12S | P12-P4 consistent |")
    add("|---|---|---|---|---|")
    for condition, block in payload["comparisons"]["n_spikes_total"].items():
        values = block["values"]
        p4 = [values["P4"][seed] for seed in sorted(values["P4"])]
        p12 = [values["P12"][seed] for seed in sorted(values["P12"])]
        p12s = [values["P12S"][seed] for seed in sorted(values["P12S"])]
        consistent = block["consistent_direction_across_seeds"]["P12_minus_P4"]
        add(f"| {condition} | {p4} | {p12} | {p12s} | {consistent} |")
    add("")
    add("### 4.4 Frame-rate comparison (stimulated profile cosine to 50 ms)")
    add("")
    add("| Population | 100 ms | 200 ms | Rate above 0.01 in any seed |")
    add("|---|---|---|---|")
    h4 = payload["hypotheses"]["H4_frame_rate_sensitivity"]["by_population"]
    for name in ("P4", "P12", "P12S"):
        values = h4[name]["cosine_by_rate_seed"]
        add(
            f"| {name} | {values['100']} | {values['200']} | "
            f"{h4[name]['rates_above_cosine_threshold']} |"
        )
    add("")
    add("## 5. Hypothesis assessment")
    add("")
    add(
        f"- H1 ordering replicates in P4 and not in P12: "
        f"**{payload['hypotheses']['H1_ordering_replication']['claim_p4_and_not_p12']}**"
    )
    add(
        f"- H2 approach/retreat separation in P4 and not in P12: "
        f"**{payload['hypotheses']['H2_approach_retreat_separation']['claim_p4_and_not_p12']}**"
    )
    add(
        "- H3 measurable difference: see the consistent-direction column in "
        "4.3; a nonzero paired difference is exact, not statistical."
    )
    add(
        "- H4 frame-rate sensitivity: descriptive; a cosine above 0.01 is the "
        "Phase 3C threshold, not evidence of a biological code."
    )
    add("")
    add("## 6. Limitations")
    add("")
    for item in payload["limitations"]:
        add(f"- {item}")
    add("")
    add("## 7. Deviations")
    add("")
    for item in payload["deviations"]:
        add(f"- **{item['id']}** — {item['detail']} Protocol effect: {item['protocol_effect']} Resolution: {item['resolution']}")
    if not payload["deviations"]:
        add("- None.")
    add("")
    add("## 8. Artifacts")
    add("")
    for name, path in payload["artifacts"].items():
        add(f"- `{path}`")
    add("")
    return "\n".join(lines)


def run(cfg_path: Path = CONFIG_PATH, write: bool = True) -> dict:
    started = time.perf_counter()
    cfg = load_protocol(cfg_path)
    assert_sources(cfg)
    preflight_payload = preflight(cfg)
    base = load_config(SENSORY_CONFIG)
    settings = load_yaml(SIMULATION_CONFIG)
    neuron_params = LIFParameters.from_config(load_yaml(NEURON_CONFIG)["neuron"])
    synapse_params = SynapseParameters.from_config(settings["synapse"])
    graph = load_connectome(PROJECT_ROOT / settings["connectome"]["path"])

    results = {}
    for name, spec in cfg["populations"].items():
        results[name] = run_population(
            graph, base, cfg, name, spec, neuron_params, synapse_params
        )
    analysis = {
        name: {
            seed: analyse_seed(cfg, block["conditions"])
            for seed, block in results[name].items()
        }
        for name in results
    }
    determinism = detect_determinism(
        cfg, graph, base, results, neuron_params, synapse_params
    )
    comparisons_block = comparisons(cfg, results)
    hypotheses_block = hypotheses(cfg, analysis)
    equivalence_checks = [
        item["config_equivalence"]
        for item in preflight_payload["per_seed"].values()
    ]
    protected = preflight_payload["protected_hashes"]
    assessment = assess(
        cfg, results, analysis, determinism, equivalence_checks, protected,
        comparisons_block, hypotheses_block,
    )
    payload = {
        "phase": "P3-T4.1",
        "version": cfg["version"],
        "description": (
            "Four-neuron versus twelve-neuron obstacle-distance population "
            "validation under the Phase 3C temporal stimulus framework."
        ),
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_s": _r(time.perf_counter() - started),
        "verdict": assessment["verdict"],
        "assessment": assessment,
        "git": git_state(),
        "environment": preflight_payload["environment"],
        "protocol": cfg,
        "preregistration_sha256": sha256(PREREG_PATH)
        if PREREG_PATH.exists()
        else None,
        "config_sha256": sha256(cfg_path),
        "sensory_config_sha256": sha256(SENSORY_CONFIG),
        "temporal_config_sha256": sha256(TEMPORAL_CONFIG),
        "simulation_config_sha256": sha256(SIMULATION_CONFIG),
        "neuron_config_sha256": sha256(NEURON_CONFIG),
        "preflight": preflight_payload,
        "results": results,
        "analysis": analysis,
        "determinism": determinism,
        "comparisons": comparisons_block,
        "hypotheses": hypotheses_block,
        "protected_hashes": protected,
        "deviations": DEVIATIONS,
        "runner_sha256": sha256(Path(__file__)),
        "limitations": LIMITATIONS,
        "artifacts": {
            "config": "configs/p3_t4_1_four_neuron_validation.yaml",
            "preflight": "experiments/phase_3c/results/p3_t4_1_preflight.json",
            "result": "experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json",
            "attempt1": "experiments/phase_3c/results/p3_t4_1_four_neuron_validation_attempt1_report_defect.json",
            "sidecar": "experiments/phase_3c/results/p3_t4_1_four_neuron_validation.sidecar.json",
            "report": "experiments/phase_3c/results/p3_t4_1_four_neuron_validation_report.md",
            "runner": "experiments/phase_3c/p3_t4_1_four_neuron_validation.py",
            "preregistration": str(PREREG_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "tests": "tests/test_p3_t4_1_four_neuron_validation.py",
        },
    }
    if write:
        PREFLIGHT_JSON.write_text(
            json.dumps(preflight_payload, indent=1), encoding="utf-8"
        )
        JSON_PATH.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        sidecar = {
            "output": JSON_PATH.name,
            "output_sha256": sha256(JSON_PATH),
            "phase": "P3-T4.1",
            "version": cfg["version"],
            "verdict": payload["verdict"],
            "generated_at_utc": payload["generated_at_utc"],
            "config_sha256": sha256(cfg_path),
            "preregistration_sha256": payload["preregistration_sha256"],
            "runner_sha256": payload["runner_sha256"],
            "preflight_sha256": sha256(PREFLIGHT_JSON),
            "report_sha256": sha256(REPORT_PATH),
            "git": payload["git"],
        }
        SIDECAR_PATH.write_text(json.dumps(sidecar, indent=1), encoding="utf-8")
    del graph
    gc.collect()
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight", action="store_true",
        help="write the preflight artifact and exit without simulating",
    )
    args = parser.parse_args(argv)
    if args.preflight:
        cfg = load_protocol()
        payload = preflight(cfg)
        PREFLIGHT_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(json.dumps({"preflight": str(PREFLIGHT_JSON)}, indent=1))
        return 0
    payload = run()
    print(
        json.dumps(
            {
                "verdict": payload["verdict"],
                "runtime_s": payload["runtime_s"],
                "result": str(JSON_PATH),
                "report": str(REPORT_PATH),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
