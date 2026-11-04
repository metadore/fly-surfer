"""Single-size Phase 2.5 benchmark.

Run one size in its own process so peak working-set memory is isolated::

    python -m experiments.phase_2_5.benchmark --size 5000 \
        --output experiments/phase_2_5/results/benchmark_n5000.json
    python -m experiments.phase_2_5.benchmark --size full \
        --output experiments/phase_2_5/results/benchmark_full.json

The full-size mode uses the validated graph directly. Subset modes sample a
reproducible connected subgraph. No raw CSV is read.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import yaml

from brain.brain_simulator import BrainSimulator
from brain.connectome_loader import load_connectome
from brain.neuron_model import LIFParameters
from brain.subgraph import (
    extract_induced_subgraph,
    sample_connected_neurons,
    total_degrees,
    weak_component_count,
)
from brain.synapse_model import SynapseParameters
from experiments.baseline import _select_stimulus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = (
    PROJECT_ROOT / "experiments" / "phase_2_5" / "configs" / "scalability_suite.yaml"
)


class BenchmarkSkipped(RuntimeError):
    """Raised when a resource preflight says the run should not start."""


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _available_gb() -> float:
    return round(psutil.virtual_memory().available / 1024**3, 3)


def _rss_mb() -> float:
    return round(psutil.Process().memory_info().rss / 1024**2, 1)


def _peak_wset_mb() -> float:
    info = psutil.Process().memory_info()
    return round(getattr(info, "peak_wset", info.rss) / 1024**2, 1)


def _sha256_array(array: np.ndarray, dtype: str) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(array, dtype=dtype).tobytes())
    return digest.hexdigest()


def _activity_hash(recorder) -> str:
    digest = hashlib.sha256()
    digest.update(
        np.ascontiguousarray(recorder.spike_times_ms, dtype="<f4").tobytes()
    )
    digest.update(
        np.ascontiguousarray(recorder.spike_neuron_indices, dtype="<i4").tobytes()
    )
    return digest.hexdigest()


def _graph_stats(graph) -> dict:
    out_degree = np.diff(graph.out_indptr)
    in_degree = np.diff(graph.in_indptr)
    return {
        "kind": "full" if not hasattr(graph, "node_map") else "subgraph",
        "n_nodes": int(graph.n_nodes),
        "n_edges": int(graph.n_edges),
        "n_synapses": int(graph.n_synapses),
        "mean_out_degree": round(float(out_degree.mean()), 4),
        "mean_in_degree": round(float(in_degree.mean()), 4),
        "max_out_degree": int(out_degree.max()) if out_degree.size else 0,
        "max_in_degree": int(in_degree.max()) if in_degree.size else 0,
        "isolated_neurons": int(np.count_nonzero(out_degree + in_degree == 0)),
        "source_n_nodes": int(getattr(graph, "source_n_nodes", graph.n_nodes)),
        "source_n_edges": int(getattr(graph, "source_n_edges", graph.n_edges)),
    }


def _sample_stats(selection, subgraph, components, largest) -> dict:
    return {
        "strategy": (
            "connected snowball from class-stratified hub candidates; "
            "candidate chosen by composition distance to eligible neurons"
        ),
        "target_neurons": int(selection.target),
        "selected_neurons": int(subgraph.n_nodes),
        "candidate_seeds": int(selection.candidate_count),
        "minimum_degree_requested": int(selection.effective_min_degree),
        "eligible_neurons": int(selection.eligible_count),
        "sampling_seconds": float(selection.sampling_seconds),
        "weak_components": components,
        "largest_weak_component": largest,
        "weakly_connected": None if components is None else components == 1,
        "root_id_sha256": _sha256_array(subgraph.root_ids, "<i8"),
    }


def _stimulus_payload(stimulus, graph) -> dict:
    if stimulus is None:
        return {"enabled": False}
    root_ids = graph.root_ids[stimulus.indices].astype("<i8")
    return {
        "enabled": True,
        "n_neurons": int(len(stimulus.indices)),
        "current_pa": float(stimulus.current_pa),
        "start_ms": float(stimulus.start_ms),
        "end_ms": float(stimulus.end_ms),
        "root_id_sha256": _sha256_array(root_ids, "<i8"),
        "root_ids": [int(value) for value in root_ids],
    }


def _environment() -> dict:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "total_memory_gb": round(psutil.virtual_memory().total / 1024**3, 3),
    }


def _validate_run(graph, simulator, result) -> dict:
    recorder = result.recorder
    summary = result.summary
    indices = recorder.spike_neuron_indices
    times = recorder.spike_times_ms
    membrane = simulator.neurons.membrane_potential
    params = simulator.neuron_params

    finite = bool(
        np.isfinite(membrane).all()
        and np.isfinite(simulator.synapses.synaptic_current_pa).all()
        and summary["diagnostics"]["finite_state"]
    )
    finite_membrane = membrane[np.isfinite(membrane)]
    if finite_membrane.size:
        observed_min = min(
            float(finite_membrane.min()),
            float(summary["diagnostics"]["min_membrane_mv"]),
        )
        observed_max = max(
            float(finite_membrane.max()),
            float(summary["diagnostics"]["max_membrane_mv"]),
        )
        voltage_ok = bool(
            finite
            and observed_min >= params.minimum_potential_mv - 1e-4
            and observed_max <= params.threshold_mv + 1e-4
        )
    else:
        observed_min = observed_max = None
        voltage_ok = False

    min_isi = None
    refractory_ok = True
    if indices.size > 1:
        order = np.argsort(indices, kind="stable")
        sorted_indices = indices[order]
        sorted_times = times[order]
        repeated = sorted_indices[1:] == sorted_indices[:-1]
        if repeated.any():
            gaps = np.diff(sorted_times)[repeated]
            min_isi = round(float(gaps.min()), 6)
            refractory_ok = bool(
                min_isi >= simulator.neurons.effective_refractory_ms - 1e-4
            )

    expected_transmissions = (
        int(np.diff(graph.out_indptr)[indices.astype(np.int64)].sum())
        if indices.size
        else 0
    )
    recorded_transmissions = int(summary["synapses"]["spike_transmissions"])
    directional_ok = expected_transmissions == recorded_transmissions

    passed = bool(finite and voltage_ok and refractory_ok and directional_ok)
    return {
        "passed": passed,
        "finite_state": finite,
        "voltage_bounds_ok": voltage_ok,
        "observed_min_membrane_mv": (
            None if observed_min is None else round(observed_min, 4)
        ),
        "observed_max_membrane_mv": (
            None if observed_max is None else round(observed_max, 4)
        ),
        "minimum_potential_mv": float(params.minimum_potential_mv),
        "threshold_mv": float(params.threshold_mv),
        "refractory_ok": refractory_ok,
        "minimum_inter_spike_interval_ms": min_isi,
        "effective_refractory_ms": float(
            simulator.neurons.effective_refractory_ms
        ),
        "directional_consistency_ok": directional_ok,
        "expected_transmissions": expected_transmissions,
        "recorded_transmissions": recorded_transmissions,
        "n_spikes_checked": int(indices.size),
    }


def run_benchmark(suite: dict, size_request: str, label: str) -> dict:
    simulation_config = suite["simulation"]
    sampling_config = suite["sampling"]
    full_size = int(sampling_config["full_size"])
    full = size_request == "full" or int(size_request) == full_size
    requested_size = full_size if full else int(size_request)
    if requested_size < 2:
        raise ValueError("benchmark size must be at least 2 neurons")

    wall_start = time.perf_counter()
    available_before = _available_gb()
    minimum_full_gb = float(
        suite["benchmark"].get("min_available_memory_gb_full", 0.75)
    )
    if full and available_before < minimum_full_gb:
        raise BenchmarkSkipped(
            f"full connectome requires at least {minimum_full_gb} GB available; "
            f"only {available_before} GB is currently free"
        )

    timings: dict[str, float] = {}
    connectome_path = _resolve(suite["connectome"]["path"])
    marker = time.perf_counter()
    full_graph = load_connectome(connectome_path)
    timings["graph_load_s"] = round(time.perf_counter() - marker, 4)
    rss_after_load = _rss_mb()

    selection = None
    sample = None
    if full:
        graph = full_graph
    else:
        marker = time.perf_counter()
        selection = sample_connected_neurons(
            full_graph,
            n_neurons=requested_size,
            seed=int(sampling_config["seed"]),
            min_degree=int(sampling_config["min_degree"]),
            candidate_seeds_per_class=int(
                sampling_config["candidate_seeds_per_class"]
            ),
            random_candidate_seeds=int(sampling_config["random_candidate_seeds"]),
        )
        timings["sampling_s"] = round(time.perf_counter() - marker, 4)

        marker = time.perf_counter()
        graph = extract_induced_subgraph(full_graph, selection.node_indices)
        timings["subgraph_extraction_s"] = round(
            time.perf_counter() - marker, 4
        )

        marker = time.perf_counter()
        components, largest = weak_component_count(graph)
        timings["component_check_s"] = round(time.perf_counter() - marker, 4)
        if components != 1:
            raise RuntimeError(
                f"sampled subgraph has {components} weak components"
            )
        sample = _sample_stats(selection, graph, components, largest)
        marker = time.perf_counter()
        del full_graph
        gc.collect()
        timings["source_graph_release_s"] = round(
            time.perf_counter() - marker, 4
        )
    rss_before_simulation = _rss_mb()

    marker = time.perf_counter()
    stimulus = _select_stimulus(
        graph,
        suite["external_input"]["stimulus"],
        int(simulation_config["seed"]),
    )
    timings["stimulus_preparation_s"] = round(time.perf_counter() - marker, 4)
    stimulus_payload = _stimulus_payload(stimulus, graph)

    neuron_config = _load_yaml(_resolve(suite["neuron_config"]))
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(suite["synapse"])

    marker = time.perf_counter()
    simulator = BrainSimulator(
        graph,
        neuron_params,
        synapse_params,
        dt_ms=float(simulation_config["dt_ms"]),
        duration_ms=float(simulation_config["duration_ms"]),
        seed=int(simulation_config["seed"]),
        background_current_pa=float(
            suite["external_input"]["background_current_pa"]
        ),
        noise_std_pa=float(suite["external_input"]["noise_std_pa"]),
        stimulus=stimulus,
        max_recorded_spikes=int(simulation_config["max_recorded_spikes"]),
        progress_interval_ms=float(simulation_config["progress_interval_ms"]),
        diagnostics_interval_steps=int(
            simulation_config["diagnostics_interval_steps"]
        ),
        profile_timing=True,
    )
    timings["initialization_s"] = round(time.perf_counter() - marker, 4)
    rss_after_initialization = _rss_mb()

    marker = time.perf_counter()
    result = simulator.run(progress=False)
    timings["simulation_s"] = round(time.perf_counter() - marker, 4)
    rss_after_simulation = _rss_mb()
    peak_after_simulation = _peak_wset_mb()
    available_after = _available_gb()

    marker = time.perf_counter()
    validation = _validate_run(graph, simulator, result)
    timings["validation_s"] = round(time.perf_counter() - marker, 4)
    rss_after_validation = _rss_mb()
    peak_final = _peak_wset_mb()
    timings["total_s"] = round(time.perf_counter() - wall_start, 4)

    activity_hash = _activity_hash(result.recorder)
    memory = simulator.memory_breakdown()
    memory.update(
        {
            "rss_after_source_load_mb": rss_after_load,
            "rss_before_simulation_mb": rss_before_simulation,
            "rss_after_initialization_mb": rss_after_initialization,
            "rss_after_simulation_mb": rss_after_simulation,
            "rss_after_validation_mb": rss_after_validation,
            "process_peak_wset_after_simulation_mb": peak_after_simulation,
            "process_peak_wset_final_mb": peak_final,
            "tracemalloc_used": False,
        }
    )
    profile = result.summary.get("timing_s", {})
    timings.update(
        {
            key: value
            for key, value in profile.items()
            if key not in timings
        }
    )
    return {
        "status": "ok",
        "phase": "2.5",
        "label": label,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "mode": "full" if full else "subset",
        "requested_size": requested_size,
        "graph": _graph_stats(graph),
        "sample": sample,
        "stimulus": stimulus_payload,
        "configuration": {
            "simulation": simulation_config,
            "synapse": suite["synapse"],
            "external_input": suite["external_input"],
            "sampling": sampling_config,
            "neuron": neuron_config["neuron"],
        },
        "timings_s": timings,
        "performance": {
            "n_steps": int(result.n_steps),
            "steps_per_second": result.summary["simulation"]["steps_per_second"],
            "rss_after_simulation_mb": rss_after_simulation,
            "process_peak_wset_after_simulation_mb": peak_after_simulation,
            "process_peak_wset_final_mb": peak_final,
            "available_memory_gb_before": available_before,
            "available_memory_gb_after": available_after,
        },
        "activity": result.summary["activity"],
        "activity_by_stimulation": result.summary["activity_by_stimulation"],
        "synapses": result.summary["synapses"],
        "diagnostics": result.summary["diagnostics"],
        "validation": validation,
        "activity_hash": activity_hash,
        "memory": memory,
        "environment": _environment(),
    }


def _write_json(path: Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return path


def _failure_payload(
    *, status: str, label: str, size_request: str, reason: str,
    available_gb: float, suite_path: Path, exc: BaseException | None,
) -> dict:
    return {
        "status": status,
        "phase": "2.5",
        "label": label,
        "size_request": size_request,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "reason": reason,
        "available_memory_gb": available_gb,
        "total_memory_gb": round(psutil.virtual_memory().total / 1024**3, 3),
        "exception_type": None if exc is None else type(exc).__name__,
        "traceback": None if exc is None else traceback.format_exc(),
        "suite": str(suite_path),
        "environment": _environment(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one Phase 2.5 scalability benchmark in this process."
    )
    parser.add_argument(
        "--suite", default=str(DEFAULT_SUITE), help="scalability suite YAML"
    )
    parser.add_argument(
        "--size", required=True, help='neuron count, or "full" for the artifact'
    )
    parser.add_argument("--label", default=None, help="result label")
    parser.add_argument(
        "--output", default=None, help="JSON result path (default: results/)"
    )
    args = parser.parse_args(argv)

    suite_path = _resolve(args.suite)
    suite = _load_yaml(suite_path)
    size_request = args.size.strip()
    label = args.label or ("full" if size_request == "full" else f"n{size_request}")
    if args.output is None:
        output = (
            PROJECT_ROOT / "experiments" / "phase_2_5" / "results"
            / f"benchmark_{label}.json"
        )
    else:
        output = _resolve(args.output)

    available_before = _available_gb()
    try:
        payload = run_benchmark(suite, size_request, label)
    except BenchmarkSkipped as exc:
        _write_json(
            output,
            _failure_payload(
                status="skipped", label=label, size_request=size_request,
                reason=str(exc), available_gb=available_before,
                suite_path=suite_path, exc=exc,
            ),
        )
        print(f"[phase2.5] SKIPPED {label}: {exc}", flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - failure must still be recorded
        _write_json(
            output,
            _failure_payload(
                status="failed", label=label, size_request=size_request,
                reason=f"{type(exc).__name__}: {exc}",
                available_gb=available_before, suite_path=suite_path, exc=exc,
            ),
        )
        print(f"[phase2.5] FAILED {label}: {type(exc).__name__}: {exc}",
              flush=True)
        return 1

    _write_json(output, payload)
    performance = payload["performance"]
    activity = payload["activity"]
    graph = payload["graph"]
    print(
        f"[phase2.5] OK {label}: {graph['n_nodes']:,} neurons / "
        f"{graph['n_edges']:,} edges, {performance['n_steps']} steps in "
        f"{payload['timings_s']['simulation_s']:.3f} s "
        f"({performance['steps_per_second']:,.1f} steps/s), "
        f"{activity['n_spikes']:,} spikes from {activity['active_neurons']:,} "
        f"neurons, peak {performance['process_peak_wset_final_mb']:,.1f} MB",
        flush=True,
    )
    print(f"[phase2.5] wrote {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
