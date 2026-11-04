"""Reproducible initial experiment: spontaneous activity in a sampled subgraph.

The sample is grown as a connected snowball from candidate hub neurons chosen
across cell classes and transmitter groups; the candidate whose composition is
closest to the eligible population is kept. This is deliberately not a
"first N neurons" slice.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from brain.brain_simulator import BrainSimulator, Stimulus
from brain.connectome_loader import load_connectome
from brain.neural_activity import plot_firing_rates, plot_raster
from brain.neuron_model import LIFParameters
from brain.subgraph import (
    extract_induced_subgraph,
    sample_connected_neurons,
    total_degrees,
    weak_component_count,
)
from brain.synapse_model import SynapseParameters

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
DEFAULT_NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def _labels(codes: np.ndarray, vocabulary: list[str]) -> list[str]:
    return [
        vocabulary[int(code)] if 0 <= int(code) < len(vocabulary) else "unlabeled"
        for code in codes
    ]


def _composition(
    codes: np.ndarray, vocabulary: list[str], mask: np.ndarray | None = None
) -> dict:
    values = codes if mask is None else codes[mask]
    counts = np.bincount(
        values.astype(np.int64) + 1, minlength=len(vocabulary) + 1
    )
    total = int(counts.sum())
    if total == 0:
        return {}
    labels = ["unlabeled"] + list(vocabulary)
    return {
        label: round(int(count) / total, 6)
        for label, count in zip(labels, counts)
        if count
    }


def _tv_distance(left: dict, right: dict) -> float:
    keys = set(left) | set(right)
    return round(
        0.5 * sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys),
        6,
    )


def _select_stimulus(graph, config: dict, seed: int) -> Stimulus | None:
    if not config.get("enabled", False):
        return None
    count = min(int(config["n_neurons"]), graph.n_nodes)
    degrees = total_degrees(graph)
    selection = config.get("selection", "highest_degree")
    if selection == "highest_degree":
        order = np.lexsort((np.arange(graph.n_nodes), -degrees))
        indices = np.sort(order[:count].astype(np.int64))
    elif selection == "random":
        rng = np.random.default_rng(seed + 1)
        indices = np.sort(
            rng.choice(graph.n_nodes, size=count, replace=False).astype(np.int64)
        )
    else:
        raise ValueError(f"unknown stimulus selection: {selection}")
    return Stimulus(
        indices=indices,
        current_pa=float(config["current_pa"]),
        start_ms=float(config["start_ms"]),
        end_ms=float(config["end_ms"]),
    )


def _sample_report(
    full_graph, selection, subgraph, sampling_seed: int
) -> dict:
    weights = subgraph.edge_weight
    components, largest = weak_component_count(subgraph)
    eligible = (
        np.ones(full_graph.n_nodes, dtype=bool)
        if selection.effective_min_degree <= 0
        else total_degrees(full_graph) >= selection.effective_min_degree
    )
    class_vocab = subgraph.vocabulary.get("super_class", [])
    nt_vocab = subgraph.vocabulary.get("nt_type", [])
    classes_selected = _composition(subgraph.super_class_code, class_vocab)
    classes_eligible = _composition(
        full_graph.super_class_code, class_vocab, eligible
    )
    nt_selected = _composition(subgraph.nt_code, nt_vocab)
    nt_eligible = _composition(full_graph.nt_code, nt_vocab, eligible)
    out_degree = np.diff(subgraph.out_indptr)
    in_degree = np.diff(subgraph.in_indptr)
    percentiles = {
        str(p): round(float(np.percentile(weights, p)), 4)
        for p in (0, 5, 25, 50, 75, 95, 99, 100)
    }
    return {
        "strategy": (
            "connected snowball from class-stratified hub candidates; "
            "candidate chosen by composition distance to eligible neurons"
        ),
        "sampling_seed": int(sampling_seed),
        "target_neurons": selection.target,
        "selected_neurons": subgraph.n_nodes,
        "candidate_seeds": selection.candidate_count,
        "chosen_seed_node_index": int(selection.seed_node_index),
        "chosen_seed_root_id": int(full_graph.root_ids[selection.seed_node_index]),
        "minimum_degree_requested": int(selection.effective_min_degree),
        "eligible_neurons": selection.eligible_count,
        "sampling_seconds": selection.sampling_seconds,
        "internal_connections": subgraph.n_edges,
        "internal_synapses": subgraph.n_synapses,
        "connection_weight_percentiles": percentiles,
        "mean_weight": round(float(weights.mean()), 4),
        "mean_out_degree": round(float(out_degree.mean()), 3),
        "mean_in_degree": round(float(in_degree.mean()), 3),
        "weak_components": components,
        "largest_weak_component": largest,
        "weakly_connected": components == 1,
        "composition": {
            "super_class": {
                "selected": classes_selected,
                "eligible": classes_eligible,
                "total_variation_distance": _tv_distance(
                    classes_selected, classes_eligible
                ),
            },
            "nt_type": {
                "selected": nt_selected,
                "eligible": nt_eligible,
                "total_variation_distance": _tv_distance(
                    nt_selected, nt_eligible
                ),
            },
        },
        "selected_root_ids": [int(value) for value in subgraph.root_ids],
    }


def _write_selected_csv(subgraph, stimulus: Stimulus | None, path: Path) -> None:
    stimulated = np.zeros(subgraph.n_nodes, dtype=bool)
    if stimulus is not None:
        stimulated[stimulus.indices] = True
    frame = pd.DataFrame(
        {
            "local_index": np.arange(subgraph.n_nodes),
            "root_id": subgraph.root_ids.astype(np.int64),
            "nt_type": _labels(
                subgraph.nt_code, subgraph.vocabulary.get("nt_type", [])
            ),
            "super_class": _labels(
                subgraph.super_class_code,
                subgraph.vocabulary.get("super_class", []),
            ),
            "class": _labels(
                subgraph.class_code, subgraph.vocabulary.get("class", [])
            ),
            "side": _labels(
                subgraph.side_code, subgraph.vocabulary.get("side", [])
            ),
            "out_degree": np.diff(subgraph.out_indptr),
            "in_degree": np.diff(subgraph.in_indptr),
            "stimulated": stimulated,
            "x": subgraph.positions[:, 0],
            "y": subgraph.positions[:, 1],
            "z": subgraph.positions[:, 2],
        }
    )
    frame.to_csv(path, index=False)


def _memory_mb() -> tuple[float | None, float | None]:
    try:
        import psutil

        info = psutil.Process().memory_info()
        peak = getattr(info, "peak_wset", info.rss)
        return round(info.rss / 1024**2, 1), round(peak / 1024**2, 1)
    except Exception:
        return None, None


def _system_info() -> dict:
    total_gb = None
    try:
        import psutil

        total_gb = round(psutil.virtual_memory().total / 1024**3, 2)
    except Exception:
        pass
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "total_memory_gb": total_gb,
    }


def _integrity() -> dict:
    return {
        "measured_structure": [
            "directed FAFB adjacency and summed synapse counts per pair",
            "139,255 neuron root IDs and per-neuron annotations",
        ],
        "predicted_annotations": [
            "neurotransmitter class (nt_type) and its confidence score",
            "cell type and super-class labels",
        ],
        "assumed_physiology": [
            "LIF membrane parameters, refractory period and membrane floor",
            "excitatory/inhibitory sign of each transmitter class",
            "synaptic time constants and uniform propagation delay",
        ],
        "computational_approximations": [
            "structural synapse counts mapped through a power law to current",
            "no receptor saturation, short-term plasticity or neuromodulation",
            "spike times quantised to the simulation timestep",
        ],
        "simulated_activity": (
            "This run generates model activity. It is not a recording and is "
            "not evidence that the model reproduces real fly neural dynamics."
        ),
        "limitations": [
            "FAFB is an adult female brain without a complete ventral nerve cord",
            "the sample is a connected 800-neuron subset, not the whole brain",
            "neurotransmitter-based sign assignment is a coarse assumption",
            "no synapse-level physiology, conduction delays or morphology",
            "external stimulation is experimenter-controlled current injection",
        ],
    }


def _prepare_experiment(args) -> dict:
    config_path = _resolve(args.config)
    neuron_config_path = _resolve(args.neuron_config)
    config = _load_yaml(config_path)
    neuron_config = _load_yaml(neuron_config_path)
    experiment = config["experiment"]
    simulation = config["simulation"]

    n_neurons = args.n_neurons or int(experiment["n_neurons"])
    sampling_seed = (
        args.sampling_seed
        if args.sampling_seed is not None
        else int(experiment["sampling_seed"])
    )
    if args.duration_ms is not None:
        simulation["duration_ms"] = float(args.duration_ms)
    if args.dt_ms is not None:
        simulation["dt_ms"] = float(args.dt_ms)
    if args.seed is not None:
        simulation["seed"] = int(args.seed)

    connectome_path = _resolve(config["connectome"]["path"])
    print(f"Loading connectome {connectome_path} ...", flush=True)
    started = time.perf_counter()
    full_graph = load_connectome(connectome_path)
    load_seconds = time.perf_counter() - started

    print(f"Sampling {n_neurons} connected neurons ...", flush=True)
    selection = sample_connected_neurons(
        full_graph,
        n_neurons=n_neurons,
        seed=sampling_seed,
        min_degree=int(experiment["min_degree"]),
        candidate_seeds_per_class=int(experiment["candidate_seeds_per_class"]),
        random_candidate_seeds=int(experiment["random_candidate_seeds"]),
    )
    subgraph = extract_induced_subgraph(full_graph, selection.node_indices)
    components, _ = weak_component_count(subgraph)
    if components != 1:
        raise RuntimeError(
            f"sampled subgraph has {components} weak components; "
            "the sampler failed to produce a connected sample"
        )

    stimulus = _select_stimulus(
        subgraph,
        config["external_input"]["stimulus"],
        int(simulation["seed"]),
    )
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(config["synapse"])
    simulator = BrainSimulator(
        subgraph,
        neuron_params,
        synapse_params,
        dt_ms=float(simulation["dt_ms"]),
        duration_ms=float(simulation["duration_ms"]),
        seed=int(simulation["seed"]),
        background_current_pa=float(
            config["external_input"]["background_current_pa"]
        ),
        noise_std_pa=float(config["external_input"]["noise_std_pa"]),
        stimulus=stimulus,
        max_recorded_spikes=int(simulation["max_recorded_spikes"]),
        progress_interval_ms=float(simulation["progress_interval_ms"]),
        diagnostics_interval_steps=int(simulation["diagnostics_interval_steps"]),
    )
    return {
        "config": config,
        "neuron_config": neuron_config,
        "config_path": str(config_path),
        "neuron_config_path": str(neuron_config_path),
        "full_graph": full_graph,
        "subgraph": subgraph,
        "selection": selection,
        "stimulus": stimulus,
        "simulator": simulator,
        "sampling_seed": sampling_seed,
        "load_seconds": round(load_seconds, 3),
        "connectome_path": str(connectome_path),
    }


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _assemble_report(
    ctx: dict,
    result,
    sample: dict,
    performance: dict,
    outputs: dict,
) -> dict:
    full = ctx["full_graph"]
    summary = result.summary
    return {
        "phase": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "connectome": {
            "path": _relative(Path(ctx["connectome_path"])),
            "full_nodes": full.n_nodes,
            "full_edges": full.n_edges,
            "full_synapses": full.n_synapses,
            "threshold": full.meta.get("threshold"),
            "node_index_rule": full.meta.get("node_index_rule"),
        },
        "configuration": {
            "simulation_config": ctx["config"],
            "neuron_config": ctx["neuron_config"],
        },
        "sample": sample,
        "simulation": summary,
        "performance": performance,
        "environment": _system_info(),
        "scientific_integrity": _integrity(),
        "outputs": outputs,
    }


def run_experiment(args) -> dict:
    wall_start = time.perf_counter()
    tracemalloc.start()
    ctx = _prepare_experiment(args)
    out_dir = _resolve(
        args.output or ctx["config"]["experiment"]["output_dir"]
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    rss_before, _ = _memory_mb()
    print("Running simulation ...", flush=True)
    result = ctx["simulator"].run(progress=not args.no_progress)
    rss_after_sim, _ = _memory_mb()
    result.save(out_dir)

    sample = _sample_report(
        ctx["full_graph"], ctx["selection"], ctx["subgraph"], ctx["sampling_seed"]
    )
    selected_csv = out_dir / "selected_neurons.csv"
    _write_selected_csv(ctx["subgraph"], ctx["stimulus"], selected_csv)
    experiment_config = ctx["config"]["experiment"]
    raster_path = out_dir / "raster.png"
    plot_raster(
        result.recorder,
        raster_path,
        result.duration_ms,
        max_points=int(experiment_config["raster_max_points"]),
        dpi=int(experiment_config["raster_dpi"]),
        title="FLY-SURFER initial experiment",
    )
    rates_path = out_dir / "firing_rates.png"
    plot_firing_rates(
        result.recorder,
        rates_path,
        result.duration_ms,
        dpi=int(experiment_config["raster_dpi"]),
        title="FLY-SURFER initial experiment",
    )

    activity_path = out_dir / "activity.npz"
    metadata_path = out_dir / "simulation_metadata.json"
    outputs = {
        "selected_neurons": _relative(selected_csv),
        "activity": _relative(activity_path),
        "simulation_metadata": _relative(metadata_path),
        "raster": _relative(raster_path),
        "firing_rates": _relative(rates_path),
        "bytes": {
            "selected_neurons": selected_csv.stat().st_size,
            "activity": activity_path.stat().st_size,
            "simulation_metadata": metadata_path.stat().st_size,
            "raster": raster_path.stat().st_size,
            "firing_rates": rates_path.stat().st_size,
        },
    }

    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    final_rss, peak_wset = _memory_mb()
    performance = {
        "wall_seconds": round(time.perf_counter() - wall_start, 3),
        "connectome_load_seconds": ctx["load_seconds"],
        "sampling_seconds": ctx["selection"].sampling_seconds,
        "simulation_seconds": result.summary["simulation"]["runtime_s"],
        "steps_per_second": result.summary["simulation"]["steps_per_second"],
        "rss_before_simulation_mb": rss_before,
        "rss_after_simulation_mb": rss_after_sim,
        "final_rss_mb": final_rss,
        "process_peak_working_set_mb": peak_wset,
        "tracemalloc_peak_mb": round(traced_peak / 1024**2, 1),
        "spike_transmissions": result.summary["synapses"]["spike_transmissions"],
    }
    report = _assemble_report(ctx, result, sample, performance, outputs)
    report_path = out_dir / "experiment_report.json"
    report["outputs"]["report"] = _relative(report_path)
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")

    activity = result.summary["activity"]
    print("\nExperiment complete")
    print(
        f"  sample: {sample['selected_neurons']:,} neurons, "
        f"{sample['internal_connections']:,} internal edges, "
        f"{sample['internal_synapses']:,} synapses"
    )
    print(
        f"  stimulation: {result.summary['stimulus']['n_neurons'] if result.summary['stimulus'] else 0}"
        f" neurons at {ctx['stimulus'].current_pa if ctx['stimulus'] else 0:g} pA"
    )
    print(
        f"  activity: {activity['n_spikes']:,} spikes, "
        f"{activity['active_neurons']:,}/{activity['n_neurons']:,} active, "
        f"mean {activity['mean_rate_hz']:.2f} Hz"
    )
    breakdown = result.summary["activity_by_stimulation"]
    print(
        f"  propagation: {breakdown['non_stimulated_active_neurons']:,} "
        f"non-stimulated neurons active, "
        f"{breakdown['non_stimulated_spikes']:,} spikes "
        f"({breakdown['non_stimulated_spike_fraction']:.1%})"
    )
    print(
        f"  performance: {performance['wall_seconds']:.2f} s wall, "
        f"{performance['steps_per_second']:.0f} steps/s, "
        f"peak working set {performance['process_peak_working_set_mb']} MB"
    )
    if activity["n_spikes"] == 0:
        print("  note: no spikes were emitted; check stimulus amplitude")
    print(f"  wrote {_relative(out_dir)}/")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible FLY-SURFER Phase 2 experiment"
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--neuron-config", default=str(DEFAULT_NEURON_CONFIG))
    parser.add_argument("--output", default=None)
    parser.add_argument("--n-neurons", type=int, default=None)
    parser.add_argument("--duration-ms", type=float, default=None)
    parser.add_argument("--dt-ms", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--sampling-seed", type=int, default=None)
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args(argv)
    run_experiment(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

