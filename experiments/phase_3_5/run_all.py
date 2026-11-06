"""Phase 3A.5 calibration suite.

Runs the calibration factors through the unchanged Phase 3A encoders,
mapping, scheduler and simulator. Every reported spike is simulated activity.

Usage::

    python -m experiments.phase_3_5.run_all
    python -m experiments.phase_3_5.run_all --stage amplitude
    python -m experiments.phase_3_5.run_all --skip-reproducibility
"""

from __future__ import annotations

import argparse
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
SIM_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from experiments.phase_3.run_all import digest_run  # noqa: E402
from experiments.phase_3_5 import calibration  # noqa: E402
from sensory.sensory_experiment import (  # noqa: E402
    environment_info,
    run_condition,
    write_json,
)

STAGES = (
    "amplitude",
    "tuning",
    "population",
    "seeds",
    "additivity",
    "transition",
    "baseline",
    "controls",
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


def _baseline_run(graph, neuron_params, synapse_params, base_config: dict) -> dict:
    sensory = base_config["sensory"]
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
    return {
        "duration_ms": duration_ms,
        "n_steps": result.n_steps,
        "wall_runtime_s": round(wall, 4),
        "steps_per_second": round(result.n_steps / wall, 2),
        "n_spikes": int(result.recorder.n_spikes),
        "active_neurons": int(
            np.count_nonzero(result.recorder.spike_counts())
        ),
        "retained_arrays_mb": simulator.memory_breakdown()["retained_arrays_mb"],
        "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
    }


def _compact_row(row: dict) -> dict:
    metrics = row["metrics"]
    return {
        "name": row["name"],
        "stage": row["stage"],
        "factors": row["factors"],
        "calibration": row["calibration"],
        "activity": metrics["activity"],
        "input": metrics["input"],
        "simulation": metrics["simulation"],
        "memory": metrics["memory"],
        "digest": row["digest"],
    }


def _compact_stage(stage: dict) -> dict:
    return {
        "stage": stage["stage"],
        "errors": list(stage.get("errors", [])),
        "groups": [
            {
                "parameters": group["parameters"],
                "analysis": group["analysis"],
                "conditions": [
                    _compact_row(row) for row in group["conditions"]
                ],
            }
            for group in stage["groups"]
        ],
    }


def _analysable(rows: list[dict], feature: str) -> bool:
    """True when every row varies distance and carries the calibrated feature."""
    return bool(rows) and all(
        "distance" in row["factors"]
        and feature in row["calibration"]["by_feature"]
        for row in rows
    )


def _run_stage(
    name: str,
    groups: list[dict],
    *,
    graph,
    base_config: dict,
    neuron_params,
    synapse_params,
    results_dir: Path,
    feature: str,
) -> dict:
    stage = {"stage": name, "errors": [], "groups": []}
    condition_dir = results_dir / "conditions" / name
    condition_dir.mkdir(parents=True, exist_ok=True)
    total = sum(len(group["specs"]) for group in groups)
    done = 0
    for group in groups:
        try:
            setup = calibration.build_setup(
                graph, base_config, **group["setup"]
            )
        except Exception as exc:  # noqa: BLE001 - failure is recorded
            stage["errors"].append(
                {
                    "stage": name,
                    "parameters": group["parameters"],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            done += len(group["specs"])
            continue
        rows = []
        for spec in group["specs"]:
            done += 1
            try:
                run = run_condition(
                    setup,
                    graph,
                    neuron_params,
                    synapse_params,
                    spec,
                    seed=None,
                )
            except Exception as exc:  # noqa: BLE001 - failure is recorded
                stage["errors"].append(
                    {
                        "stage": name,
                        "condition": spec["name"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            row = {
                "name": spec["name"],
                "stage": name,
                "factors": spec["factors"],
                "metrics": run["metrics"],
                "calibration": calibration.extract_calibration_metrics(
                    run, setup, spec["active_features"]
                ),
                "digest": digest_run(run),
            }
            write_json(
                condition_dir / f"{spec['name']}.json",
                {
                    "phase": "3A.5",
                    "generated_at_utc": _utc_now(),
                    "condition": spec["name"],
                    "stage": name,
                    "factors": spec["factors"],
                    "timeline": [
                        {"start_ms": float(start), "state": state.features()}
                        for start, state in spec["timeline"]
                    ],
                    "active_features": list(spec["active_features"]),
                    "metrics": run["metrics"],
                    "calibration": row["calibration"],
                    "digest": row["digest"],
                },
            )
            rows.append(row)
            print(
                f"  [{done}/{total}] {spec['name']} "
                f"{row['calibration']['total_feature_spikes']} feature spikes "
                f"{row['metrics']['simulation']['wall_runtime_s']:.3f} s",
                flush=True,
            )
        analysis = (
            calibration.group_analysis(rows, feature)
            if _analysable(rows, feature)
            else {}
        )
        stage["groups"].append(
            {
                "parameters": group["parameters"],
                "conditions": rows,
                "analysis": analysis,
            }
        )
    return stage


def _flatten_rows(stages: list[dict]) -> list[dict]:
    return [
        row
        for stage in stages
        for group in stage["groups"]
        for row in group["conditions"]
    ]


def _performance(baseline: dict, rows: list[dict]) -> dict:
    if not rows:
        return {
            "baseline_runtime_s": float(baseline["wall_runtime_s"]),
            "baseline_steps_per_second": float(baseline["steps_per_second"]),
            "sensory_mean_runtime_s": 0.0,
            "sensory_mean_steps_per_second": 0.0,
            "added_runtime_s": 0.0,
            "added_runtime_fraction": 0.0,
            "retained_arrays_mb": 0.0,
            "mean_rss_delta_mb": 0.0,
            "n_conditions_compared": 0,
        }
    runtimes = [float(row["metrics"]["simulation"]["wall_runtime_s"]) for row in rows]
    steps = [
        float(row["metrics"]["simulation"]["steps_per_second_wall"])
        for row in rows
    ]
    mean_wall = float(np.mean(runtimes))
    added = mean_wall - float(baseline["wall_runtime_s"])
    return {
        "baseline_runtime_s": float(baseline["wall_runtime_s"]),
        "baseline_steps_per_second": float(baseline["steps_per_second"]),
        "sensory_mean_runtime_s": round(mean_wall, 4),
        "sensory_mean_steps_per_second": round(float(np.mean(steps)), 2),
        "added_runtime_s": round(added, 4),
        "added_runtime_fraction": round(
            added / float(baseline["wall_runtime_s"]), 6
        ),
        "retained_arrays_mb": round(
            float(
                np.mean(
                    [row["metrics"]["memory"]["retained_arrays_mb"] for row in rows]
                )
            ),
            4,
        ),
        "mean_rss_delta_mb": round(
            float(
                np.mean([row["metrics"]["memory"]["rss_delta_mb"] for row in rows])
            ),
            3,
        ),
        "n_conditions_compared": len(rows),
    }


def _run_hash_subprocess(
    config_path: Path, condition: str, output_path: Path, timeout_s: float
) -> dict | None:
    if output_path.exists():
        output_path.unlink()
    command = [
        sys.executable,
        "-m",
        "experiments.phase_3_5.run_all",
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


def _find_condition(groups: list[dict], name: str) -> tuple[dict, dict] | None:
    for group in groups:
        for spec in group["specs"]:
            if spec["name"] == name:
                return group, spec
    return None


def _condition_mode(args, cal: dict, graph, neuron_params, synapse_params) -> int:
    groups = calibration.amplitude_groups(cal)
    found = _find_condition(groups, args.condition)
    if found is None:
        raise SystemExit(
            f"unknown reproducibility condition {args.condition!r}; "
            "only amplitude-stage conditions are supported"
        )
    group, spec = found
    setup = calibration.build_setup(
        graph, cal["base_config"], **group["setup"]
    )
    run = run_condition(
        setup, graph, neuron_params, synapse_params, spec, seed=None
    )
    digest = digest_run(run)
    digest["condition"] = spec["name"]
    if args.hash_out:
        write_json(_resolve(args.hash_out), digest)
    print(json.dumps(digest, indent=1), flush=True)
    return 0


def _plot_amplitude(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [group for group in stage["groups"] if group["conditions"]]
    amplitudes = [float(group["parameters"]["amplitude_pa"]) for group in groups]
    distances = groups[0]["analysis"]["distances"]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for index, distance in enumerate(distances):
        values = [
            group["analysis"]["spike_counts"][index] for group in groups
        ]
        axes[0].plot(amplitudes, values, marker="o", label=f"distance {distance}")
        fractions = [
            group["analysis"]["recruitment_fractions"][index]
            for group in groups
        ]
        axes[1].plot(
            amplitudes, fractions, marker="o", label=f"distance {distance}"
        )
    axes[0].set_xlabel("Current amplitude (pA)")
    axes[0].set_ylabel("Feature spikes")
    axes[0].set_title("Obstacle-distance response")
    axes[1].set_xlabel("Current amplitude (pA)")
    axes[1].set_ylabel("Recruited fraction")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("Stimulated population recruitment")
    for axis in axes:
        axis.grid(alpha=0.25, linewidth=0.4)
        axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_discriminability(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [group for group in stage["groups"] if group["conditions"]]
    amplitudes = [float(group["parameters"]["amplitude_pa"]) for group in groups]
    d_prime = [group["analysis"]["d_prime_proxy"] for group in groups]
    rho = [group["analysis"]["spearman_rho"] for group in groups]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    axes[0].plot(amplitudes, d_prime, marker="o", color="#2e75b6")
    axes[0].set_xlabel("Current amplitude (pA)")
    axes[0].set_ylabel("Poisson d' proxy (near vs far)")
    axes[0].set_title("Separation proxy")
    axes[1].plot(amplitudes, rho, marker="o", color="#c55a11")
    axes[1].set_xlabel("Current amplitude (pA)")
    axes[1].set_ylabel("Spearman rho (distance vs spikes)")
    axes[1].set_title("Ordering")
    axes[1].set_ylim(-1.05, 1.05)
    for axis in axes:
        axis.grid(alpha=0.25, linewidth=0.4)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_tuning(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8, 4.8))
    for group in stage["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        sigma = float(group["parameters"]["sigma_fraction"])
        amplitude = float(group["parameters"]["amplitude_pa"])
        axis.plot(
            analysis["distances"],
            analysis["spike_counts"],
            marker="o",
            label=f"sigma {sigma:.2f}, {amplitude:.0f} pA",
        )
    axis.set_xlabel("Obstacle distance (normalised)")
    axis.set_ylabel("Feature spikes")
    axis.set_title("Tuning-width sweep")
    axis.grid(alpha=0.25, linewidth=0.4)
    axis.legend(frameon=False, fontsize=7, ncol=2)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_population(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8, 4.8))
    for group in stage["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        size = int(group["parameters"]["population_size"])
        axis.plot(
            analysis["distances"],
            analysis["spikes_per_neuron"],
            marker="o",
            label=f"{size} neurons",
        )
    axis.set_xlabel("Obstacle distance (normalised)")
    axis.set_ylabel("Feature spikes per neuron")
    axis.set_title("Population-size sweep")
    axis.grid(alpha=0.25, linewidth=0.4)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_seeds(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8, 4.8))
    for group in stage["groups"]:
        if not group["conditions"]:
            continue
        seed = int(group["parameters"]["mapping_seed"])
        axis.plot(
            group["analysis"]["distances"],
            group["analysis"]["spike_counts"],
            marker="o",
            label=f"seed {seed}",
        )
    axis.set_xlabel("Obstacle distance (normalised)")
    axis.set_ylabel("Feature spikes")
    axis.set_title("Mapping-seed sensitivity")
    axis.grid(alpha=0.25, linewidth=0.4)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_additivity(additivity: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["obstacle", "coin", "both"]
    values = [
        additivity["obstacle_spikes"],
        additivity["coin_spikes"],
        additivity["combined_spikes"],
    ]
    figure, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.bar(labels, values, color=["#2e75b6", "#70ad47", "#c55a11"])
    axis.set_ylabel("Feature spikes (sum of active features)")
    axis.set_title("Additivity of obstacle and coin distance")
    axis.grid(axis="y", alpha=0.25, linewidth=0.4)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_transition(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    transitions = [
        float(group["parameters"]["transition_ms"])
        for group in stage["groups"]
        if group["conditions"]
    ]
    spikes = [
        group["conditions"][0]["calibration"]["total_feature_spikes"]
        for group in stage["groups"]
        if group["conditions"]
    ]
    figure, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.bar(range(len(transitions)), spikes, color="#8faadc")
    axis.set_xticks(range(len(transitions)), [f"{value:g}" for value in transitions])
    axis.set_xlabel("Crossfade duration (ms)")
    axis.set_ylabel("Feature spikes")
    axis.set_title("Two-state distance transition")
    axis.grid(axis="y", alpha=0.25, linewidth=0.4)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_baseline(stage: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    baselines = [
        float(group["parameters"]["baseline"])
        for group in stage["groups"]
        if group["conditions"]
    ]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for group in stage["groups"]:
        if not group["conditions"]:
            continue
        baseline = float(group["parameters"]["baseline"])
        axes[0].plot(
            group["analysis"]["distances"],
            group["analysis"]["spike_counts"],
            marker="o",
            label=f"baseline {baseline:g}",
        )
        axes[1].bar(
            str(baseline), group["analysis"]["max_recruitment_fraction"],
            color="#8faadc",
        )
    axes[0].set_xlabel("Obstacle distance (normalised)")
    axes[0].set_ylabel("Feature spikes")
    axes[0].set_title("Activation baseline")
    axes[0].grid(alpha=0.25, linewidth=0.4)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].set_xlabel("Baseline activation")
    axes[1].set_ylabel("Maximum recruited fraction")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("Recruitment by baseline")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _stage_tables(stage: dict) -> list[str]:
    lines = []
    for group in stage["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        parameters = group["parameters"]
        label = ", ".join(f"{key}={value}" for key, value in parameters.items())
        counts = ", ".join(
            f"{distance:g}: {count}"
            for distance, count in zip(
                analysis["distances"], analysis["spike_counts"]
            )
        )
        lines.append(
            f"- `{label}`: {counts}; ordered={analysis['ordered']}, "
            f"d'={analysis['d_prime_proxy']}, "
            f"max recruited={analysis['max_recruitment_fraction']:.2f}."
        )
    return lines


def write_report(summary: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    selection = summary["selection"]
    criteria = summary["criteria"]
    stages = summary["stages"]
    additivity = summary["additivity"]
    seeds = summary["seeds"]
    repro = summary["reproducibility"]
    performance = summary["performance"]
    lines = [
        "# Phase 3A.5 — sensory-calibration report",
        "",
        f"Generated {summary['generated_at_utc']} from "
        f"`{summary['config_path']}`.",
        "",
        "## Scientific status",
        "",
        "This report contains simulated activity only. The game states are "
        "experimenter-defined, the encoders are configured assumptions, and "
        "the mapped neurons come from predicted FlyWire annotations. No value "
        "here is a biological recording or a validated sensory pathway. "
        "Calibration selects a model operating point; it does not identify "
        "the fly's coding scheme.",
        "",
        "## Setup",
        "",
        f"- Graph: {summary['graph']['n_nodes']:,} neurons, "
        f"{summary['graph']['n_edges']:,} directed edges, "
        f"{summary['graph']['n_synapses']:,} summed synapses.",
        f"- Duration: {summary['duration_ms']:.0f} ms at "
        f"{summary['dt_ms']} ms timesteps; zero background current and noise.",
        f"- Calibrated feature: `{summary['feature']}`.",
        f"- Distances: {', '.join(f'{value:g}' for value in summary['distances'])}.",
        f"- Conditions run: {summary['n_conditions']}.",
        "",
        "## Pre-registered selection rule",
        "",
        "A factor group is eligible only if it produced at least one spike and "
        "did not recruit the entire stimulated population at every tested "
        "level. It is *ordered* only if the three distance levels produced a "
        "strictly monotone spike-count sequence; ties are not ordered. Among "
        "ordered eligible groups, the largest Poisson signal-to-noise proxy "
        "is selected. If no group is ordered, the Phase 3A reference values "
        "are retained (200 pA, sigma_fraction 0.20, 12 neurons) and the "
        "outcome is reported as a negative result.",
        "",
        "## Selected operating point",
        "",
        f"- Current amplitude: **{selection['amplitude_pa']:.0f} pA**.",
        f"- Gaussian sigma_fraction: **{selection['sigma_fraction']:.2f}**.",
        f"- Population size: **{selection['population_size']} neurons**.",
        f"- Mapping seed: **{selection['mapping_seed']}**.",
        f"- Baseline activation: **{selection['baseline']:g}**.",
        f"- Selection sources: {json.dumps(selection['sources'])}.",
        f"- Fallbacks: {json.dumps(selection['fallbacks'])}.",
        "",
        "## Decision rule",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for name, value in criteria["checks"].items():
        lines.append(f"| `{name}` | {value} |")
    lines += [
        "",
        f"**Overall: {'PASS' if criteria['passed'] else 'NEGATIVE / NOT MET'}**",
        "",
    ]
    if criteria["passed"]:
        lines += [
            "An operating point met every pre-registered check. It is the "
            "recommended Phase 3B input setting, within the model's "
            "assumptions.",
            "",
        ]
    else:
        lines += [
            "No operating point met every pre-registered check. This is a "
            "negative result, not a failure to be hidden. Phase 3B must either "
            "use the Phase 3A reference point and report the limitation, or "
            "treat the graded-coding question as unresolved.",
            "",
        ]

    lines += [
        "## Amplitude and recruitment",
        "",
        "| Amplitude (pA) | Spikes at distances | Ordered | d' proxy | "
        "Max recruited |",
        "|---:|---|---|---:|---:|",
    ]
    for group in stages["amplitude"]["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        counts = " / ".join(str(value) for value in analysis["spike_counts"])
        lines.append(
            f"| {float(group['parameters']['amplitude_pa']):.0f} | {counts} | "
            f"{analysis['ordered']} | {analysis['d_prime_proxy']} | "
            f"{analysis['max_recruitment_fraction']:.2f} |"
        )

    lines += [
        "",
        "## Tuning width",
        "",
        "| Amplitude (pA) | Sigma | Spikes at distances | Ordered | d' proxy |",
        "|---:|---:|---|---:|---:|",
    ]
    for group in stages["tuning"]["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        counts = " / ".join(str(value) for value in analysis["spike_counts"])
        lines.append(
            f"| {float(group['parameters']['amplitude_pa']):.0f} | "
            f"{float(group['parameters']['sigma_fraction']):.2f} | {counts} | "
            f"{analysis['ordered']} | {analysis['d_prime_proxy']} |"
        )

    lines += [
        "",
        "## Population size",
        "",
        "| Neurons | Spikes at distances | Spikes/neuron at distances | Ordered | "
        "d' proxy |",
        "|---:|---|---|---|---:|",
    ]
    for group in stages["population"]["groups"]:
        if not group["conditions"]:
            continue
        analysis = group["analysis"]
        counts = " / ".join(str(value) for value in analysis["spike_counts"])
        rates = " / ".join(
            f"{value:.2f}" for value in analysis["spikes_per_neuron"]
        )
        lines.append(
            f"| {int(group['parameters']['population_size'])} | {counts} | "
            f"{rates} | {analysis['ordered']} | {analysis['d_prime_proxy']} |"
        )

    lines += [
        "",
        "## Mapping seeds",
        "",
        f"- Seeds: {seeds['seeds']}.",
        f"- Ordered seeds: {seeds['ordered_seeds']} "
        f"({seeds['n_ordered_seeds']}/3).",
        f"- Criterion (at least two ordered seeds): {seeds['passed']}.",
        "",
        "| Distance | Counts across seeds | Mean | SD |",
        "|---|---:|---:|---:|",
    ]
    for distance, payload in seeds["counts_by_distance"].items():
        lines.append(
            f"| {float(distance):g} | {payload['values']} | "
            f"{payload['mean']} | {payload['std']} |"
        )

    lines += [
        "",
        "## Additivity",
        "",
        f"- Obstacle alone: {additivity['obstacle_spikes']} spikes.",
        f"- Coin alone: {additivity['coin_spikes']} spikes.",
        f"- Both: {additivity['combined_spikes']} spikes.",
        f"- Expected additive excess: {additivity['expected_additive']}.",
        f"- Additivity index: {additivity['additivity_index']}.",
        "",
        additivity["interpretation"],
        "",
        "## Transitions",
        "",
        "| Crossfade (ms) | Spikes | Active neurons | First latency (ms) | "
        "Peak feature current (pA) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in summary["transition"]["rows"]:
        lines.append(
            f"| {row['transition_ms']:g} | {row['spikes']} | "
            f"{row['active_neurons']} | {row['first_latency_ms']} | "
            f"{row['max_total_current_pa']} |"
        )

    lines += [
        "",
        "## Activation baseline",
        "",
        "| Baseline | Spikes at distances | Ordered | d' proxy | Max recruited |",
        "|---:|---|---|---:|---:|",
    ]
    for row in summary["baseline_activation"]["rows"]:
        counts = " / ".join(str(value) for value in row["spike_counts"])
        lines.append(
            f"| {row['baseline']:g} | {counts} | {row['ordered']} | "
            f"{row['d_prime_proxy']} | {row['max_recruitment_fraction']:.2f} |"
        )

    lines += [
        "",
        "## Controls",
        "",
        "| Condition | Feature | Amplitude (pA) | Spikes | Active | Recruited |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary["controls"]["rows"]:
        lines.append(
            f"| `{row['condition']}` | `{row['feature']}` | "
            f"{row['amplitude_pa']:.0f} | {row['spikes']} | "
            f"{row['active_neurons']} | {row['recruitment_fraction']:.2f} |"
        )
    lines += [
        "",
        "The 100 pA and 300 pA obstacle-distance controls are the first and "
        "last rows of the amplitude table.",
        "",
        "## Performance",
        "",
        f"- Baseline (no schedule): {performance['baseline_runtime_s']:.3f} s, "
        f"{performance['baseline_steps_per_second']:.1f} steps/s.",
        f"- Calibration mean: {performance['sensory_mean_runtime_s']:.3f} s, "
        f"{performance['sensory_mean_steps_per_second']:.1f} steps/s.",
        f"- Added runtime: {performance['added_runtime_s']:.3f} s "
        f"({performance['added_runtime_fraction'] * 100:.2f}% of baseline).",
        f"- Retained arrays: {performance['retained_arrays_mb']:.2f} MB; "
        f"mean RSS change {performance['mean_rss_delta_mb']:.2f} MB.",
        "",
        "A negative added runtime means the single no-input baseline ran "
        "slower than the calibrated conditions in this process; it is "
        "measurement noise, not a speedup.",
        "",
        "## Reproducibility",
        "",
    ]
    if repro:
        lines += [
            f"- Condition: `{repro['condition']}`.",
            f"- Separate processes: {repro['processes']}.",
            f"- Input hash equal: {repro.get('input_equal')}.",
            f"- Spike hash equal: {repro.get('spikes_equal')}.",
            f"- Transmissions equal: {repro.get('transmissions_equal')}.",
            f"- Passed: {repro.get('passed')}.",
        ]
    else:
        lines.append("- Reproducibility check was not run.")

    lines += [
        "",
        "## Failures",
        "",
    ]
    if summary["failures"]:
        for failure in summary["failures"]:
            lines.append(f"- `{failure}`")
    else:
        lines.append("- No condition or setup failures were recorded.")

    lines += [
        "",
        "## Limitations",
        "",
        "- A calibrated operating point is a model choice, not a biological "
        "finding.",
        "- The strict monotonicity rule is deliberately conservative; a flat "
        "response is reported as flat.",
        "- The Poisson d' proxy is a descriptive signal-to-noise ratio of "
        "simulated spike counts, not a behavioural discrimination measure.",
        "- Additivity is affected by recurrent network activity and by shared "
        "downstream targets; it is not a property of the encoders alone.",
        "- Only one feature, one duration, one game-state family and one "
        "connectome artifact were tested.",
        "- No motor readout, reward, plasticity or perception is present.",
        "",
        "## Next milestone",
        "",
        "Phase 3B should use the selected operating point (or the documented "
        "reference fallback) when it integrates perceived scenes with the "
        "Phase 3A encoder. Perception errors must be reported separately from "
        "neural calibration.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _default_selection(cal: dict) -> dict:
    return {
        "amplitude_pa": float(cal["default_amplitude_pa"]),
        "sigma_fraction": float(cal["default_sigma_fraction"]),
        "population_size": int(cal["default_population_size"]),
        "mapping_seed": int(cal["mapping_seeds"][0]),
        "baseline": float(cal["default_baseline"]),
        "amplitudes_considered": [float(cal["default_amplitude_pa"])],
        "sources": {},
        "fallbacks": [],
    }


def _load_selection(results_dir: Path, cal: dict) -> dict:
    path = results_dir / "selection.json"
    if not path.exists():
        return _default_selection(cal)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_selection(cal)
    selection = _default_selection(cal)
    selection.update(payload)
    selection["fallbacks"] = list(dict.fromkeys(selection.get("fallbacks", [])))
    return selection


def _save_selection(results_dir: Path, selection: dict) -> Path:
    return write_json(results_dir / "selection.json", selection)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 3A.5 sensory calibration."
    )
    parser.add_argument(
        "--config", default=str(calibration.DEFAULT_CALIBRATION_CONFIG)
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--stage", choices=("all",) + STAGES, default="all")
    parser.add_argument("--condition", default=None)
    parser.add_argument("--hash-out", default=None)
    parser.add_argument("--skip-reproducibility", action="store_true")
    parser.add_argument("--repro-timeout", type=float, default=1800.0)
    args = parser.parse_args(argv)

    config_path = _resolve(args.config)
    cal = calibration.load_calibration_config(config_path)
    base_config = cal["base_config"]
    output_root = _resolve(args.output or cal["output_dir"])
    results_dir = output_root / "results"
    plots_dir = output_root / "plots"
    results_dir.mkdir(parents=True, exist_ok=True)

    simulation_config = _load_yaml(SIM_CONFIG)
    neuron_params = LIFParameters.from_config(_load_yaml(NEURON_CONFIG)["neuron"])
    synapse_params = SynapseParameters.from_config(
        simulation_config["synapse"]
    )

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

    if args.condition is not None:
        return _condition_mode(
            args, cal, graph, neuron_params, synapse_params
        )

    started_at = _utc_now()
    print("Running no-input baseline ...", flush=True)
    baseline = _baseline_run(
        graph, neuron_params, synapse_params, base_config
    )
    write_json(results_dir / "baseline.json", baseline)
    print(
        f"  {baseline['wall_runtime_s']:.3f} s, "
        f"{baseline['n_spikes']:,} spikes",
        flush=True,
    )

    selection = (
        _default_selection(cal)
        if args.stage == "all"
        else _load_selection(results_dir, cal)
    )
    stages: dict[str, dict] = {}
    requested = STAGES if args.stage == "all" else (args.stage,)

    if "amplitude" in requested:
        print("Stage 3A.5.1: amplitude x distance ...", flush=True)
        stages["amplitude"] = _run_stage(
            "amplitude",
            calibration.amplitude_groups(cal),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        amplitude, ranked, reason = calibration.select_amplitude(
            stages["amplitude"], cal["default_amplitude_pa"]
        )
        selection["amplitude_pa"] = amplitude
        selection["sources"]["amplitude"] = reason
        if reason != "ordered":
            selection["fallbacks"].append("amplitude")
        considered = [
            float(group["parameters"]["amplitude_pa"]) for group in ranked[:2]
        ] or [amplitude]
        selection["amplitudes_considered"] = considered
        _save_selection(results_dir, selection)
        write_json(
            results_dir / "stage_amplitude.json",
            _compact_stage(stages["amplitude"]),
        )

    if "tuning" in requested:
        print("Stage 3A.5.3: tuning width ...", flush=True)
        amplitudes = [
            float(value)
            for value in selection.get(
                "amplitudes_considered", [selection["amplitude_pa"]]
            )
        ]
        stages["tuning"] = _run_stage(
            "tuning",
            calibration.tuning_groups(cal, amplitudes),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        amplitude, sigma, ranked, reason = calibration.select_tuning(
            stages["tuning"],
            selection["amplitude_pa"],
            selection["sigma_fraction"],
        )
        selection["amplitude_pa"] = amplitude
        selection["sigma_fraction"] = sigma
        selection["sources"]["tuning"] = reason
        if reason != "ordered":
            selection["fallbacks"].append("tuning")
        _save_selection(results_dir, selection)
        write_json(
            results_dir / "stage_tuning.json",
            _compact_stage(stages["tuning"]),
        )

    if "population" in requested:
        print("Stage 3A.5.4: population size ...", flush=True)
        stages["population"] = _run_stage(
            "population",
            calibration.population_groups(
                cal,
                selection["amplitude_pa"],
                selection["sigma_fraction"],
            ),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        size, ranked, reason = calibration.select_population(
            stages["population"], selection["population_size"]
        )
        selection["population_size"] = size
        selection["sources"]["population"] = reason
        if reason != "ordered":
            selection["fallbacks"].append("population")
        _save_selection(results_dir, selection)
        write_json(
            results_dir / "stage_population.json",
            _compact_stage(stages["population"]),
        )

    if "seeds" in requested:
        print("Stage 3A.5.5: mapping seeds ...", flush=True)
        stages["seeds"] = _run_stage(
            "seeds",
            calibration.seed_groups(
                cal,
                selection["amplitude_pa"],
                selection["sigma_fraction"],
                selection["population_size"],
            ),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        write_json(
            results_dir / "stage_seeds.json",
            _compact_stage(stages["seeds"]),
        )

    if "additivity" in requested:
        print("Stage 3A.5.6: additivity ...", flush=True)
        stages["additivity"] = _run_stage(
            "additivity",
            calibration.additivity_groups(
                cal,
                selection["amplitude_pa"],
                selection["sigma_fraction"],
                selection["population_size"],
                selection["mapping_seed"],
            ),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        additivity = calibration.additivity_summary(
            stages["additivity"], baseline_spikes=int(baseline["n_spikes"])
        )
        write_json(results_dir / "additivity.json", additivity)
        write_json(
            results_dir / "stage_additivity.json",
            _compact_stage(stages["additivity"]),
        )

    if "transition" in requested:
        print("Stage 3A.5.7: transition ...", flush=True)
        stages["transition"] = _run_stage(
            "transition",
            calibration.transition_groups(
                cal,
                selection["amplitude_pa"],
                selection["sigma_fraction"],
                selection["population_size"],
                selection["mapping_seed"],
            ),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        transition = calibration.transition_summary(
            stages["transition"], cal["feature"]
        )
        write_json(results_dir / "transition.json", transition)
        write_json(
            results_dir / "stage_transition.json",
            _compact_stage(stages["transition"]),
        )

    if "baseline" in requested:
        print("Stage 3A.5.8: activation baseline ...", flush=True)
        stages["baseline"] = _run_stage(
            "baseline",
            calibration.baseline_groups(
                cal,
                selection["amplitude_pa"],
                selection["sigma_fraction"],
                selection["population_size"],
            ),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        baseline_values = calibration.baseline_summary(
            stages["baseline"], cal["feature"]
        )
        write_json(results_dir / "baseline_activation.json", baseline_values)
        write_json(
            results_dir / "stage_baseline.json",
            _compact_stage(stages["baseline"]),
        )

    if "controls" in requested:
        print("Stage 3A.5 controls: coin and speed ...", flush=True)
        stages["controls"] = _run_stage(
            "controls",
            calibration.control_groups(cal),
            graph=graph,
            base_config=base_config,
            neuron_params=neuron_params,
            synapse_params=synapse_params,
            results_dir=results_dir,
            feature=cal["feature"],
        )
        controls = calibration.controls_summary(stages["controls"])
        write_json(results_dir / "controls.json", controls)
        write_json(
            results_dir / "stage_controls.json",
            _compact_stage(stages["controls"]),
        )

    if args.stage != "all":
        print(
            f"Completed stage {args.stage}; results in {_relative(results_dir)}",
            flush=True,
        )
        return 0

    rows = _flatten_rows(list(stages.values()))
    performance = _performance(baseline, rows)
    failures = [
        failure
        for stage in stages.values()
        for failure in stage.get("errors", [])
    ]
    seed_values = calibration.seed_summary(stages["seeds"], cal["feature"])
    additivity = calibration.additivity_summary(
        stages["additivity"], baseline_spikes=int(baseline["n_spikes"])
    )
    transition = calibration.transition_summary(
        stages["transition"], cal["feature"]
    )
    baseline_values = calibration.baseline_summary(
        stages["baseline"], cal["feature"]
    )
    controls = calibration.controls_summary(stages["controls"])

    reproducibility = None
    if not args.skip_reproducibility:
        anchor = "a5_1_amp200_dist0p15"
        anchor_row = next(
            (
                row
                for group in stages["amplitude"]["groups"]
                for row in group["conditions"]
                if row["name"] == anchor
            ),
            None,
        )
        if anchor_row is not None:
            print(
                f"Reproducibility: running {anchor!r} in two subprocesses ...",
                flush=True,
            )
            reproducibility = _reproducibility(
                config_path,
                anchor,
                anchor_row["digest"],
                results_dir,
                args.repro_timeout,
            )
            write_json(
                results_dir / "reproducibility.json", reproducibility
            )
            print(
                f"  passed={reproducibility['passed']}",
                flush=True,
            )

    criteria = calibration.decision_criteria(
        seed_stage=stages["seeds"],
        amplitude_stage=stages["amplitude"],
        population_stage=stages["population"],
        selection=selection,
        additivity=additivity,
        reproducibility=reproducibility,
        failures=failures,
        performance=performance,
    )

    print("Writing plots ...", flush=True)
    plots = [
        _plot_amplitude(
            stages["amplitude"], plots_dir / "recruitment_vs_current.png"
        ),
        _plot_discriminability(
            stages["amplitude"], plots_dir / "discriminability.png"
        ),
        _plot_tuning(stages["tuning"], plots_dir / "tuning_width.png"),
        _plot_population(
            stages["population"], plots_dir / "population_size.png"
        ),
        _plot_seeds(stages["seeds"], plots_dir / "seed_variability.png"),
        _plot_additivity(additivity, plots_dir / "additivity.png"),
        _plot_transition(
            stages["transition"], plots_dir / "transition_response.png"
        ),
        _plot_baseline(
            stages["baseline"], plots_dir / "baseline_activation.png"
        ),
    ]

    summary = {
        "phase": "3A.5",
        "generated_at_utc": _utc_now(),
        "started_at_utc": started_at,
        "config_path": _relative(config_path),
        "output_dir": _relative(output_root),
        "feature": cal["feature"],
        "distances": cal["distances"],
        "duration_ms": cal["duration_ms"],
        "dt_ms": float(base_config["sensory"]["dt_ms"]),
        "environment": environment_info(),
        "graph": {
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "load_s": round(load_seconds, 4),
        },
        "selection": selection,
        "criteria": criteria,
        "seeds": seed_values,
        "additivity": additivity,
        "transition": transition,
        "baseline_activation": baseline_values,
        "controls": controls,
        "baseline": baseline,
        "performance": performance,
        "reproducibility": reproducibility,
        "failures": failures,
        "n_conditions": len(rows),
        "stages": {
            name: _compact_stage(stage) for name, stage in stages.items()
        },
        "plots": [_relative(path) for path in plots],
    }
    write_json(results_dir / "summary.json", summary)
    write_json(results_dir / "calibration_summary.json", {
        "selection": selection,
        "criteria": criteria,
        "seeds": seed_values,
        "additivity": additivity,
        "baseline_activation": baseline_values,
        "performance": performance,
    })
    report_path = write_report(summary, output_root / "PHASE_3_5_REPORT.md")
    print("", flush=True)
    print(
        f"Completed {len(rows)} conditions; report written to "
        f"{_relative(report_path)}",
        flush=True,
    )
    print(
        f"Selected amplitude={selection['amplitude_pa']:.0f} pA, "
        f"sigma={selection['sigma_fraction']:.2f}, "
        f"population={selection['population_size']}, "
        f"criteria={criteria['passed']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
