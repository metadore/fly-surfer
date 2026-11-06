"""Phase 3A sensory-encoding suite.

Runs the configured game-state protocols through the population encoders,
sensory mapping and the existing ``BrainSimulator``. Every reported spike is
simulated activity; nothing here is a biological measurement.

Usage::

    python -m experiments.phase_3.run_all
    python -m experiments.phase_3.run_all --conditions combined_obstacle_and_coin_other_lane
    python -m experiments.phase_3.run_all --condition sequence_obstacle_approach \
        --hash-out experiments/phase_3/results/hashes.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
SIM_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from sensory.sensory_experiment import (  # noqa: E402
    condition_specs,
    environment_info,
    load_config,
    plot_condition_comparison,
    plot_input_activity,
    plot_representative_activity,
    plot_tuning_curves,
    prepare_setup,
    run_condition,
    write_json,
    write_report,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _hash_arrays(arrays) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.dtype).encode("ascii"))
        digest.update(str(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def digest_run(run: dict) -> dict:
    """Deterministic hashes of the scheduler input and recorded spikes."""
    signature = run["scheduler"].signature()
    recorder = run["result"].recorder
    return {
        "input_hash": _hash_arrays(
            [signature["indices"], signature["values"], signature["starts"]]
        ),
        "spike_hash": _hash_arrays(
            [recorder.spike_times_ms, recorder.spike_neuron_indices]
        ),
        "n_spikes": int(recorder.n_spikes),
        "spike_transmissions": int(
            run["result"].summary["synapses"]["spike_transmissions"]
        ),
    }


def _run_one_condition(
    graph,
    setup,
    neuron_params,
    synapse_params,
    spec: dict,
    *,
    seed: int | None,
    results_dir: Path | None,
    progress: bool = False,
) -> dict:
    run = run_condition(
        setup,
        graph,
        neuron_params,
        synapse_params,
        spec,
        seed=seed,
        progress=progress,
    )
    if results_dir is not None:
        write_json(
            results_dir / "conditions" / f"{spec['name']}.json",
            {
                "phase": "3A",
                "generated_at_utc": _utc_now(),
                "condition": spec["name"],
                "protocol": spec["protocol"],
                "description": spec["description"],
                "timeline": [
                    {"start_ms": float(start), "state": state.features()}
                    for start, state in spec["timeline"]
                ],
                "active_features": list(spec["active_features"]),
                "metrics": run["metrics"],
                "schedule": run["scheduler"].describe(),
                "digest": digest_run(run),
            },
        )
    return run


def _run_hash_subprocess(
    config_path: Path, condition: str, output_path: Path, timeout_s: float
) -> dict | None:
    if output_path.exists():
        output_path.unlink()
    command = [
        sys.executable,
        "-m",
        "experiments.phase_3.run_all",
        "--config",
        str(config_path),
        "--condition",
        condition,
        "--hash-out",
        str(output_path),
    ]
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    try:
        subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            timeout=timeout_s,
            env=environment,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None
    if not output_path.exists():
        return None
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _reproducibility(
    config_path: Path,
    condition: str,
    parent: dict,
    results_dir: Path,
    timeout_s: float,
) -> dict:
    first = _run_hash_subprocess(
        config_path, condition, results_dir / "repro_hash_a.json", timeout_s
    )
    second = _run_hash_subprocess(
        config_path, condition, results_dir / "repro_hash_b.json", timeout_s
    )
    if first is None or second is None:
        return {
            "condition": condition,
            "processes": 2,
            "passed": False,
            "reason": "one or both reproducibility subprocesses did not finish",
        }
    input_equal = bool(
        first["input_hash"] == second["input_hash"] == parent["input_hash"]
    )
    spikes_equal = bool(
        first["spike_hash"] == second["spike_hash"] == parent["spike_hash"]
    )
    transmissions_equal = bool(
        first["spike_transmissions"]
        == second["spike_transmissions"]
        == parent["spike_transmissions"]
    )
    return {
        "condition": condition,
        "processes": 2,
        "parent": parent,
        "process_a": first,
        "process_b": second,
        "input_equal": input_equal,
        "spikes_equal": spikes_equal,
        "transmissions_equal": transmissions_equal,
        "passed": bool(input_equal and spikes_equal and transmissions_equal),
        "spike_count": first["n_spikes"] if spikes_equal else None,
        "reason": None
        if (input_equal and spikes_equal and transmissions_equal)
        else "one or more deterministic outputs differ",
    }


def _baseline_run(
    graph, neuron_params, synapse_params, config: dict
) -> dict:
    sensory = config["sensory"]
    duration_ms = float(sensory["duration_ms"])
    simulator = BrainSimulator(
        graph,
        neuron_params,
        synapse_params,
        dt_ms=float(sensory["dt_ms"]),
        duration_ms=duration_ms,
        seed=int(sensory["seed"]),
        background_current_pa=0.0,
        noise_std_pa=0.0,
        stimulus=None,
        input_schedule=None,
        max_recorded_spikes=int(sensory["max_recorded_spikes"]),
        progress_interval_ms=float(sensory["progress_interval_ms"]),
        diagnostics_interval_steps=int(sensory["diagnostics_interval_steps"]),
    )
    rss_before = psutil.Process().memory_info().rss
    started = time.perf_counter()
    result = simulator.run(progress=False)
    wall = time.perf_counter() - started
    rss_after = psutil.Process().memory_info().rss
    memory = simulator.memory_breakdown()
    return {
        "duration_ms": duration_ms,
        "n_steps": result.n_steps,
        "wall_runtime_s": round(wall, 4),
        "steps_per_second": round(result.n_steps / wall, 2),
        "n_spikes": int(result.recorder.n_spikes),
        "active_neurons": int(np.count_nonzero(result.recorder.spike_counts())),
        "retained_arrays_mb": memory["retained_arrays_mb"],
        "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
    }


def _performance(baseline: dict, runs: list[dict]) -> dict:
    short = [
        run["metrics"]
        for run in runs
        if abs(float(run["metrics"]["duration_ms"]) - baseline["duration_ms"])
        < 1e-9
    ]
    pool = short or [run["metrics"] for run in runs]
    mean_wall = float(np.mean([metrics["simulation"]["wall_runtime_s"] for metrics in pool]))
    mean_sps = float(
        np.mean([metrics["simulation"]["steps_per_second_wall"] for metrics in pool])
    )
    added = mean_wall - float(baseline["wall_runtime_s"])
    return {
        "baseline_runtime_s": float(baseline["wall_runtime_s"]),
        "baseline_steps_per_second": float(baseline["steps_per_second"]),
        "sensory_mean_runtime_s": round(mean_wall, 4),
        "sensory_mean_steps_per_second": round(mean_sps, 2),
        "added_runtime_s": round(added, 4),
        "added_runtime_fraction": round(
            added / float(baseline["wall_runtime_s"]), 6
        ),
        "retained_arrays_mb": float(
            np.mean([metrics["memory"]["retained_arrays_mb"] for metrics in pool])
        ),
        "mean_rss_delta_mb": round(
            float(np.mean([metrics["memory"]["rss_delta_mb"] for metrics in pool])),
            3,
        ),
        "n_conditions_compared": len(pool),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 3A sensory-encoding protocols."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        help="optional condition names or prefixes to run",
    )
    parser.add_argument(
        "--condition",
        default=None,
        help="run exactly one condition and optionally write its hashes",
    )
    parser.add_argument("--hash-out", default=None)
    parser.add_argument("--skip-reproducibility", action="store_true")
    parser.add_argument(
        "--repro-timeout", type=float, default=1800.0,
        help="timeout for each reproducibility subprocess (seconds)",
    )
    args = parser.parse_args(argv)

    config_path = _resolve(args.config)
    config = load_config(config_path)
    output_root = _resolve(args.output or config["sensory"]["output_dir"])
    results_dir = output_root / "results"
    plots_dir = output_root / "plots"
    output_root.mkdir(parents=True, exist_ok=True)

    simulation_config = _load_yaml(SIM_CONFIG)
    neuron_config = _load_yaml(NEURON_CONFIG)
    neuron_params = LIFParameters.from_config(neuron_config["neuron"])
    synapse_params = SynapseParameters.from_config(simulation_config["synapse"])

    print("Loading validated connectome artifact ...", flush=True)
    started = time.perf_counter()
    graph = load_connectome(
        _resolve(simulation_config["connectome"]["path"])
    )
    load_seconds = time.perf_counter() - started
    print(
        f"  {graph.n_nodes:,} neurons, {graph.n_edges:,} edges, "
        f"{graph.n_synapses:,} summed synapses in {load_seconds:.3f} s",
        flush=True,
    )

    print("Building sensory encoders and neuron mapping ...", flush=True)
    mapping_started = time.perf_counter()
    setup = prepare_setup(graph, config)
    print(
        f"  {len(setup.encoders)} features, "
        f"{setup.mapping.stimulated_indices().size} mapped neurons "
        f"in {time.perf_counter() - mapping_started:.3f} s",
        flush=True,
    )
    specs = condition_specs(config)

    if args.condition is not None:
        spec = next(
            (item for item in specs if item["name"] == args.condition), None
        )
        if spec is None:
            available = ", ".join(item["name"] for item in specs)
            raise SystemExit(
                f"unknown condition {args.condition!r}; available: {available}"
            )
        run = _run_one_condition(
            graph,
            setup,
            neuron_params,
            synapse_params,
            spec,
            seed=None,
            results_dir=None,
        )
        digest = digest_run(run)
        digest["condition"] = spec["name"]
        if args.hash_out:
            write_json(_resolve(args.hash_out), digest)
        print(json.dumps(digest, indent=1), flush=True)
        return 0

    if args.conditions:
        wanted = set(args.conditions)
        specs = [
            spec
            for spec in specs
            if spec["name"] in wanted
            or any(spec["name"].startswith(prefix) for prefix in wanted)
        ]
        if not specs:
            raise SystemExit("no conditions matched --conditions")

    started_at = _utc_now()
    (results_dir / "conditions").mkdir(parents=True, exist_ok=True)

    print("Running baseline (no sensory schedule) ...", flush=True)
    baseline = _baseline_run(
        graph, neuron_params, synapse_params, config
    )
    print(
        f"  {baseline['wall_runtime_s']:.3f} s, "
        f"{baseline['steps_per_second']:.1f} steps/s, "
        f"{baseline['n_spikes']:,} spikes",
        flush=True,
    )
    write_json(results_dir / "baseline.json", baseline)

    runs: list[dict] = []
    for index, spec in enumerate(specs, start=1):
        print(
            f"[{index}/{len(specs)}] {spec['name']} "
            f"({spec['duration_ms']:.0f} ms, "
            f"{len(spec['active_features'])} active features) ...",
            flush=True,
        )
        run = _run_one_condition(
            graph,
            setup,
            neuron_params,
            synapse_params,
            spec,
            seed=None,
            results_dir=results_dir,
        )
        runs.append(run)
        metrics = run["metrics"]
        print(
            f"  {metrics['activity']['n_spikes']:,} spikes, "
            f"{metrics['activity']['active_neurons']:,} active, "
            f"{metrics['simulation']['wall_runtime_s']:.3f} s",
            flush=True,
        )

    mapping_report = setup.mapping.report()
    write_json(results_dir / "mapping_report.json", mapping_report)

    print("Writing plots ...", flush=True)
    plots = [
        plot_tuning_curves(
            setup.encoders, plots_dir / "tuning_curves.png"
        )
    ]
    representative = next(
        (
            run
            for run in runs
            if run["metrics"]["condition"]
            == "combined_obstacle_and_coin_other_lane"
        ),
        next(
            (
                run
                for run in runs
                if run["metrics"]["protocol"] == "combined"
            ),
            runs[0],
        ),
    )
    plots.append(
        plot_input_activity(
            representative["scheduler"],
            plots_dir / "input_activity_representative.png",
            "Scheduled sensory current — combined obstacle and coin",
        )
    )
    for key, filename, title, ylabel in (
        ("n_spikes", "spikes_by_condition.png", "Spikes per condition",
         "Recorded spikes"),
        ("active_neurons", "active_by_condition.png", "Active neurons per condition",
         "Active neurons"),
        ("mean_rate_hz", "mean_rate_by_condition.png",
         "Mean simulated rate per condition", "Mean rate (Hz)"),
    ):
        plots.append(
            plot_condition_comparison(
                runs, key, plots_dir / filename, title, ylabel
            )
        )
    representative_plots = plot_representative_activity(
        representative,
        plots_dir,
        "Representative sensory condition (simulated activity)",
    )
    plots.extend(Path(value) for value in representative_plots.values())

    reproducibility = None
    if not args.skip_reproducibility:
        condition = representative["metrics"]["condition"]
        print(
            f"Reproducibility: running {condition!r} in two subprocesses ...",
            flush=True,
        )
        reproducibility = _reproducibility(
            config_path,
            condition,
            digest_run(representative),
            results_dir,
            args.repro_timeout,
        )
        write_json(results_dir / "reproducibility.json", reproducibility)
        print(
            f"  passed={reproducibility['passed']} "
            f"input={reproducibility.get('input_equal')} "
            f"spikes={reproducibility.get('spikes_equal')}",
            flush=True,
        )

    performance = _performance(baseline, runs)
    summary = {
        "phase": "3A",
        "generated_at_utc": _utc_now(),
        "started_at_utc": started_at,
        "config_path": _relative(config_path),
        "output_dir": _relative(output_root),
        "seed": int(config["sensory"]["seed"]),
        "environment": environment_info(),
        "graph": {
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "load_s": round(load_seconds, 4),
        },
        "setup": setup.info(),
        "mapping": mapping_report,
        "baseline": baseline,
        "conditions": [
            {"metrics": run["metrics"]} for run in runs
        ],
        "performance": performance,
        "reproducibility": reproducibility,
        "plots": [_relative(path) for path in plots],
    }
    write_json(results_dir / "summary.json", summary)
    report_path = write_report(summary, output_root / "PHASE_3_REPORT.md")

    print("", flush=True)
    print(
        f"Completed {len(runs)} conditions; report written to "
        f"{_relative(report_path)}",
        flush=True,
    )
    print(
        f"Mean sensory runtime {performance['sensory_mean_runtime_s']:.3f} s "
        f"vs baseline {performance['baseline_runtime_s']:.3f} s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
