"""Phase 2.5 scalability suite orchestrator.

Each benchmark size runs in a fresh subprocess so peak working-set memory is
not contaminated by earlier sizes. Subset sizes use reproducible connected
sampling; the full size uses the validated connectome artifact directly. No
raw CSV is read.

Usage::

    python -m experiments.phase_2_5.run_all
    python -m experiments.phase_2_5.run_all --sizes 800 5000 --skip-full
    python -m experiments.phase_2_5.run_all --reports-only
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
HERE = Path(__file__).resolve().parent
DEFAULT_SUITE = HERE / "configs" / "scalability_suite.yaml"
RESULTS_DIR = HERE / "results"
PLOTS_DIR = HERE / "plots"
REPORTS_DIR = HERE / "reports"

TERMINAL_STATUSES = {"ok", "failed", "skipped", "timeout"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _available_gb() -> float:
    return round(psutil.virtual_memory().available / 1024**3, 3)


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _tail(path: Path, lines: int = 40) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:])


def _write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _run_one(
    *,
    size_request: str,
    label: str,
    role: str,
    suite_path: Path,
    result_path: Path,
    log_path: Path,
    timeout_s: float,
) -> dict:
    """Run one benchmark in a child process and load its result."""
    result_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if result_path.exists():
        result_path.unlink()

    command = [
        sys.executable,
        "-m",
        "experiments.phase_2_5.benchmark",
        "--suite",
        str(suite_path),
        "--size",
        str(size_request),
        "--label",
        label,
        "--output",
        str(result_path),
    ]
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"

    started = time.perf_counter()
    timed_out = False
    returncode: int | None = None
    with log_path.open("w", encoding="utf-8") as log:
        try:
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                env=environment,
                check=False,
            )
            returncode = int(completed.returncode)
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = round(time.perf_counter() - started, 3)

    record: dict | None = None
    if result_path.exists():
        try:
            record = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            record = None

    if record is None:
        record = {
            "status": "timeout" if timed_out else "failed",
            "phase": "2.5",
            "label": label,
            "size_request": str(size_request),
            "generated_at_utc": _utc_now(),
            "reason": (
                f"benchmark exceeded the {timeout_s:g} s timeout"
                if timed_out
                else f"benchmark exited with code {returncode} "
                "without writing a result"
            ),
            "available_memory_gb": _available_gb(),
            "returncode": returncode,
            "log_tail": _tail(log_path),
        }

    record.setdefault("status", "failed")
    record["orchestrator"] = {
        "role": role,
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": float(timeout_s),
        "wall_seconds": elapsed,
        "log": _relative(log_path),
        "result": _relative(result_path),
    }
    if record["status"] not in TERMINAL_STATUSES:
        record["status"] = "failed"
        record["reason"] = f"unexpected status {record['status']!r}"
    return record


def _last_success(records: list[dict]) -> dict | None:
    successes = [record for record in records if record.get("status") == "ok"]
    if not successes:
        return None
    latest = successes[-1]
    graph = latest.get("graph", {})
    performance = latest.get("performance", {})
    return {
        "label": latest.get("label"),
        "n_neurons": graph.get("n_nodes"),
        "n_edges": graph.get("n_edges"),
        "steps_per_second": performance.get("steps_per_second"),
        "process_peak_wset_final_mb": performance.get(
            "process_peak_wset_final_mb"
        ),
        "activity_hash": latest.get("activity_hash"),
    }


# ---------------------------------------------------------------------------
# plots
# ---------------------------------------------------------------------------

COLORS = {
    "graph": "#1f4e79",
    "neuron": "#2e75b6",
    "synapse": "#c55a11",
    "delay": "#8c564b",
    "recorder": "#7f7f7f",
    "total": "#548235",
    "rss": "#2e75b6",
    "peak": "#c00000",
    "source": "#a6a6a6",
    "simulation": "#1f4e79",
    "recording": "#c55a11",
    "initialization": "#548235",
    "load": "#7f7f7f",
    "stimulated": "#c55a11",
    "non_stimulated": "#548235",
}


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _series(records: list[dict]) -> list[dict]:
    rows = [
        record
        for record in records
        if record.get("status") == "ok"
        and record.get("orchestrator", {}).get("role") == "series"
    ]
    return sorted(rows, key=lambda record: record["graph"]["n_nodes"])


def _sizes(rows: list[dict]) -> np.ndarray:
    return np.array([row["graph"]["n_nodes"] for row in rows], dtype=float)


def _lookup(rows: list[dict], path: tuple[str, ...], default=0.0):
    values = []
    for row in rows:
        current = row
        for key in path:
            current = current.get(key, {}) if isinstance(current, dict) else {}
        values.append(default if current in ({}, None) else current)
    return np.asarray(values, dtype=float)


def _style_axis(axis, sizes: np.ndarray, title: str, xlabel: str, ylabel: str):
    axis.set_xscale("log")
    axis.set_xticks(sizes)
    axis.set_xticklabels([f"{int(size):,}" for size in sizes])
    axis.minorticks_off()
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25, linewidth=0.5, which="major")
    axis.legend(frameon=False, fontsize=8)


def make_memory_plot(rows: list[dict], path: Path) -> Path | None:
    if not rows:
        return None
    plt = _pyplot()
    sizes = _sizes(rows)
    graph = _lookup(rows, ("memory", "components_mb", "graph_arrays"))
    neuron = _lookup(rows, ("memory", "components_mb", "neuron_state"))
    delays = _lookup(rows, ("memory", "components_mb", "delay_buffers"))
    synapse = (
        _lookup(rows, ("memory", "components_mb", "synapse_state")) - delays
    )
    recorder = _lookup(rows, ("memory", "components_mb", "spike_recorder"))
    retained = _lookup(rows, ("memory", "retained_arrays_mb"))
    source = _lookup(rows, ("memory", "rss_after_source_load_mb"))
    rss = _lookup(rows, ("memory", "rss_after_simulation_mb"))
    peak = _lookup(rows, ("memory", "process_peak_wset_final_mb"))

    figure, (arrays, process) = plt.subplots(1, 2, figsize=(13, 5.6))
    arrays.plot(sizes, graph, marker="o", color=COLORS["graph"],
                label="graph arrays")
    arrays.plot(sizes, synapse, marker="s", color=COLORS["synapse"],
                label="synapse weights/currents")
    arrays.plot(sizes, delays, marker="v", color=COLORS["delay"],
                label="delay buffers")
    arrays.plot(sizes, neuron, marker="^", color=COLORS["neuron"],
                label="neuron membrane/refractory state")
    arrays.plot(sizes, recorder, marker="D", linestyle="--",
                color=COLORS["recorder"], label="spike recorder capacity")
    arrays.plot(sizes, retained, marker="*", linewidth=2,
                color=COLORS["total"], label="retained arrays total")
    arrays.set_yscale("log")
    _style_axis(arrays, sizes, "Retained simulation arrays",
                "Neurons", "Memory (MB)")

    process.plot(sizes, source, marker="D", linestyle=":",
                 color=COLORS["source"], label="RSS after source graph load")
    process.plot(sizes, rss, marker="o", color=COLORS["rss"],
                 label="RSS after simulation")
    process.plot(sizes, peak, marker="s", color=COLORS["peak"],
                 label="process peak working set")
    process.plot(sizes, retained, marker="*", linestyle="--",
                 color=COLORS["total"], label="retained arrays (numpy nbytes)")
    process.set_yscale("log")
    _style_axis(process, sizes, "Process memory", "Neurons", "Memory (MB)")

    figure.suptitle(
        "Phase 2.5 memory scaling — subsets load the full graph before sampling, "
        "so process peaks overstate subset-only memory",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    return path


def make_speed_plot(rows: list[dict], path: Path) -> Path | None:
    if not rows:
        return None
    plt = _pyplot()
    sizes = _sizes(rows)
    steps_per_second = _lookup(rows, ("performance", "steps_per_second"))
    graph_load = _lookup(rows, ("timings_s", "graph_load_s"))
    initialization = _lookup(rows, ("timings_s", "initialization_s"))
    simulation = _lookup(rows, ("timings_s", "simulation_s"))
    recording = _lookup(rows, ("timings_s", "recording_s"))

    figure, (throughput, stages) = plt.subplots(1, 2, figsize=(13, 5.6))
    throughput.plot(sizes, steps_per_second, marker="o", linewidth=2,
                    color=COLORS["simulation"], label="simulation throughput")
    for size, value in zip(sizes, steps_per_second):
        throughput.annotate(
            f"{value:,.0f}", (size, value), textcoords="offset points",
            xytext=(0, 8), ha="center", fontsize=8,
        )
    throughput.set_yscale("log")
    _style_axis(throughput, sizes, "Simulation throughput",
                "Neurons", "Steps per second")
    lower, upper = throughput.get_ylim()
    throughput.set_ylim(lower, upper * 1.18)

    stages.plot(sizes, graph_load, marker="D", linestyle=":",
                color=COLORS["load"], label="graph load")
    stages.plot(sizes, initialization, marker="s", color=COLORS["initialization"],
                label="simulator initialization")
    stages.plot(sizes, simulation, marker="o", linewidth=2,
                color=COLORS["simulation"], label="simulation (400 steps)")
    stages.plot(sizes, recording, marker="^", color=COLORS["recording"],
                label="spike recording (inside simulation)")
    stages.set_yscale("log")
    _style_axis(stages, sizes, "Stage timing", "Neurons", "Seconds (log)")

    figure.suptitle(
        "Phase 2.5 speed scaling — 200 ms simulated with dt = 0.5 ms "
        "(400 steps) for every size",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    return path


def make_active_plot(rows: list[dict], path: Path) -> Path | None:
    if not rows:
        return None
    plt = _pyplot()
    sizes = _sizes(rows)
    active = _lookup(rows, ("activity", "active_neurons"))
    neurons = _lookup(rows, ("graph", "n_nodes"))
    stimulated_n = _lookup(rows, ("activity_by_stimulation", "stimulated_neurons"))
    stimulated_active = _lookup(
        rows, ("activity_by_stimulation", "stimulated_active_neurons")
    )
    non_stimulated_active = _lookup(
        rows, ("activity_by_stimulation", "non_stimulated_active_neurons")
    )
    active_fraction = _lookup(rows, ("activity", "active_fraction"))
    unstimulated_total = np.maximum(neurons - stimulated_n, 1.0)
    stimulated_fraction = stimulated_active / np.maximum(stimulated_n, 1.0)
    non_stimulated_fraction = non_stimulated_active / unstimulated_total

    figure, (counts, fractions) = plt.subplots(1, 2, figsize=(13, 5.6))
    counts.plot(sizes, active, marker="o", linewidth=2,
                color=COLORS["simulation"], label="active neurons")
    counts.plot(sizes, stimulated_active, marker="s", linestyle="--",
                color=COLORS["stimulated"], label="stimulated active")
    counts.plot(sizes, non_stimulated_active, marker="^",
                color=COLORS["non_stimulated"], label="non-stimulated active")
    counts.set_yscale("log")
    _style_axis(counts, sizes, "Active neurons", "Neurons", "Count (log)")

    fractions.plot(sizes, active_fraction, marker="o",
                   color=COLORS["simulation"], label="active fraction")
    fractions.plot(sizes, stimulated_fraction, marker="s", linestyle="--",
                   color=COLORS["stimulated"], label="stimulated active fraction")
    fractions.plot(sizes, non_stimulated_fraction, marker="^",
                   color=COLORS["non_stimulated"],
                   label="non-stimulated active fraction")
    fractions.set_ylim(0, 1.05)
    fractions.set_xscale("log")
    fractions.set_xticks(sizes)
    fractions.set_xticklabels([f"{int(size):,}" for size in sizes])
    fractions.minorticks_off()
    fractions.set_title("Active fractions")
    fractions.set_xlabel("Neurons")
    fractions.set_ylabel("Fraction of group")
    fractions.grid(alpha=0.25, linewidth=0.5)
    fractions.legend(frameon=False, fontsize=8)

    figure.suptitle(
        "Phase 2.5 active-neuron scaling — equal activity is not implied by "
        "equal stimulation",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    return path


def make_spike_plot(rows: list[dict], path: Path) -> Path | None:
    if not rows:
        return None
    plt = _pyplot()
    sizes = _sizes(rows)
    spikes = _lookup(rows, ("activity", "n_spikes"))
    neurons = _lookup(rows, ("graph", "n_nodes"))
    stimulated_spikes = _lookup(
        rows, ("activity_by_stimulation", "stimulated_spikes")
    )
    non_stimulated_spikes = _lookup(
        rows, ("activity_by_stimulation", "non_stimulated_spikes")
    )
    max_rate = _lookup(rows, ("activity", "rate_percentiles_hz", "100"))
    spikes_per_neuron = spikes / np.maximum(neurons, 1.0)

    figure, (counts, intensity) = plt.subplots(1, 2, figsize=(13, 5.6))
    counts.plot(sizes, spikes, marker="o", linewidth=2,
                color=COLORS["simulation"], label="total spikes")
    counts.plot(sizes, stimulated_spikes, marker="s", linestyle="--",
                color=COLORS["stimulated"], label="stimulated spikes")
    counts.plot(sizes, non_stimulated_spikes, marker="^",
                color=COLORS["non_stimulated"], label="non-stimulated spikes")
    counts.set_xscale("log")
    counts.set_xticks(sizes)
    counts.set_xticklabels([f"{int(size):,}" for size in sizes])
    counts.minorticks_off()
    counts.set_yscale("log")
    counts.set_title("Spike counts")
    counts.set_xlabel("Neurons")
    counts.set_ylabel("Spikes (log)")
    counts.grid(alpha=0.25, linewidth=0.5)
    counts.legend(frameon=False, fontsize=8)

    intensity.plot(sizes, spikes_per_neuron, marker="o",
                   color=COLORS["simulation"], label="spikes per neuron")
    intensity.set_xscale("log")
    intensity.set_xticks(sizes)
    intensity.set_xticklabels([f"{int(size):,}" for size in sizes])
    intensity.minorticks_off()
    intensity.set_title("Spike intensity")
    intensity.set_xlabel("Neurons")
    intensity.set_ylabel("Spikes per neuron (200 ms)")
    intensity.grid(alpha=0.25, linewidth=0.5)
    rate_axis = intensity.twinx()
    rate_axis.plot(sizes, max_rate, marker="s", linestyle="--",
                   color=COLORS["peak"], label="max neuron rate")
    rate_axis.set_ylabel("Max firing rate (Hz)")
    rate_axis.grid(False)
    handles, labels = intensity.get_legend_handles_labels()
    extra_handles, extra_labels = rate_axis.get_legend_handles_labels()
    intensity.legend(handles + extra_handles, labels + extra_labels,
                     frameon=False, fontsize=8, loc="upper left")

    figure.suptitle(
        "Phase 2.5 spike-count scaling — counts are simulated, not measured, "
        "and larger counts do not indicate a better model",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    return path


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def _fmt_int(value) -> str:
    return "—" if value is None else f"{int(value):,}"


def _fmt_num(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.{digits}f}"


def _yes(value) -> str:
    return "yes" if value else "no"


def _series_expected(
    sizes: list[int], include_full: bool, full_size: int
) -> list[int]:
    expected = list(sizes)
    if include_full:
        expected.append(int(full_size))
    return expected


def _environment(records: list[dict]) -> dict:
    for record in records:
        if record.get("environment"):
            return record["environment"]
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "platform": sys.platform,
        "cpu_count": os.cpu_count(),
        "total_memory_gb": round(psutil.virtual_memory().total / 1024**3, 3),
    }


def _compact_failure(record: dict) -> dict:
    return {
        "label": record.get("label"),
        "status": record.get("status"),
        "size_request": record.get("size_request"),
        "reason": record.get("reason"),
        "available_memory_gb": record.get("available_memory_gb"),
        "last_successful_benchmark": record.get("last_successful_benchmark"),
        "timed_out": record.get("orchestrator", {}).get("timed_out"),
        "returncode": record.get("orchestrator", {}).get("returncode"),
        "log": record.get("orchestrator", {}).get("log"),
        "log_tail": record.get("log_tail"),
    }


def build_report(
    *,
    suite_path: Path,
    suite: dict,
    records: list[dict],
    reproducibility: dict,
    plots: list[Path | None],
    expected_sizes: list[int],
    include_full: bool,
    started_at: str,
    finished_at: str,
) -> dict:
    series = [
        record
        for record in records
        if record.get("orchestrator", {}).get("role") == "series"
    ]
    successes = [record for record in series if record.get("status") == "ok"]
    failures = [record for record in records if record.get("status") != "ok"]
    full = next((record for record in series if record.get("label") == "full"), None)
    full_index = records.index(full) if full is not None else len(records)
    prior_success = _last_success(records[:full_index])
    expected_ok = all(
        any(
            record.get("status") == "ok"
            and int(record.get("graph", {}).get("n_nodes", -1)) == size
            for record in series
        )
        for size in expected_sizes
    )
    if not successes:
        status = "failed"
    elif expected_ok:
        status = "complete"
    else:
        status = "partial"

    notes = [
        "Subset benchmarks load the validated full graph before sampling; "
        "process peak working set therefore includes the source graph and "
        "overstates subset-only process memory.",
        "Retained array bytes are exact NumPy nbytes for graph and simulation "
        "state; they exclude interpreter, allocator and shared-library "
        "overhead, and temporary propagation buffers.",
        "Simulated activity is model output, not measured neural activity. "
        "Higher firing rates or spike counts do not indicate better "
        "scientific or computational performance.",
        "The connectome structure is measured (FAFB); membrane, synapse and "
        "input parameters remain explicit model assumptions.",
    ]

    return {
        "phase": "2.5",
        "generated_at_utc": _utc_now(),
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "status": status,
        "suite_path": _relative(suite_path),
        "suite": suite,
        "environment": _environment(records),
        "expected_sizes": expected_sizes,
        "full_connectome_requested": include_full,
        "successful_sizes": [
            int(record["graph"]["n_nodes"]) for record in successes
        ],
        "benchmarks": records,
        "failures": [_compact_failure(record) for record in failures],
        "full_connectome": (
            {
                "attempted": full is not None,
                "status": full.get("status") if full else "not_requested",
                "reason": full.get("reason") if full else None,
                "available_memory_gb": (
                    full.get("available_memory_gb")
                    if full and full.get("available_memory_gb") is not None
                    else full.get("performance", {}).get(
                        "available_memory_gb_before"
                    )
                    if full
                    else None
                ),
                "last_successful_benchmark": prior_success,
            }
            if include_full
            else {
                "attempted": False,
                "status": "not_requested",
                "reason": "full-connectome run disabled with --skip-full",
                "available_memory_gb": _available_gb(),
                "last_successful_benchmark": _last_success(records),
            }
        ),
        "reproducibility": reproducibility,
        "last_successful_benchmark": _last_success(records),
        "plots": [_relative(path) for path in plots if path is not None],
        "notes": notes,
    }


def _md_scaling_table(series: list[dict]) -> list[str]:
    lines = [
        "| Neurons | Edges | Synapses | Init (s) | Sim (s) | Steps/s | "
        "Peak WS (MB) | Retained (MB) | Spikes | Active | Mean Hz | Max Hz | "
        "Transmissions | Stable |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for record in series:
        graph = record.get("graph", {})
        timings = record.get("timings_s", {})
        performance = record.get("performance", {})
        activity = record.get("activity", {})
        memory = record.get("memory", {})
        validation = record.get("validation", {})
        synapses = record.get("synapses", {})
        rates = activity.get("rate_percentiles_hz", {})
        lines.append(
            "| {n} | {e} | {s} | {init} | {sim} | {sps} | {peak} | {ret} | "
            "{spikes} | {active} | {mean} | {maxr} | {tx} | {stable} |".format(
                n=_fmt_int(graph.get("n_nodes")),
                e=_fmt_int(graph.get("n_edges")),
                s=_fmt_int(graph.get("n_synapses")),
                init=_fmt_num(timings.get("initialization_s"), 4),
                sim=_fmt_num(timings.get("simulation_s"), 3),
                sps=_fmt_int(performance.get("steps_per_second")),
                peak=_fmt_num(
                    performance.get("process_peak_wset_final_mb"), 1
                ),
                ret=_fmt_num(memory.get("retained_arrays_mb"), 2),
                spikes=_fmt_int(activity.get("n_spikes")),
                active=_fmt_int(activity.get("active_neurons")),
                mean=_fmt_num(activity.get("mean_rate_hz"), 3),
                maxr=_fmt_num(rates.get("100"), 1),
                tx=_fmt_int(synapses.get("spike_transmissions")),
                stable=_yes(validation.get("passed")),
            )
        )
    return lines


def _md_timing_table(series: list[dict]) -> list[str]:
    lines = [
        "| Neurons | Graph load | Sampling | Extraction | Init | Sim | "
        "Recording | Validation | Total |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in series:
        size = record.get("graph", {}).get("n_nodes")
        timing = record.get("timings_s", {})
        lines.append(
            "| {n} | {load} | {sample} | {extract} | {init} | {sim} | "
            "{record} | {validate} | {total} |".format(
                n=_fmt_int(size),
                load=_fmt_num(timing.get("graph_load_s"), 3),
                sample=_fmt_num(timing.get("sampling_s", 0.0), 3),
                extract=_fmt_num(timing.get("subgraph_extraction_s", 0.0), 3),
                init=_fmt_num(timing.get("initialization_s"), 4),
                sim=_fmt_num(timing.get("simulation_s"), 3),
                record=_fmt_num(timing.get("recording_s"), 4),
                validate=_fmt_num(timing.get("validation_s"), 4),
                total=_fmt_num(timing.get("total_s"), 3),
            )
        )
    return lines


def _md_stability_table(series: list[dict], reproducibility: dict) -> list[str]:
    lines = [
        "| Neurons | Finite | Voltage bounds | Refractory | Directional | "
        "Min V (mV) | Max V (mV) | Min ISI (ms) | Reproducible |",
        "|---:|:---:|:---:|:---:|:---:|---:|---:|---:|:---:|",
    ]
    repeat_size = reproducibility.get("size")
    for record in series:
        validation = record.get("validation", {})
        size = record.get("graph", {}).get("n_nodes")
        repro = "—"
        if repeat_size is not None and size == repeat_size:
            repro = _yes(reproducibility.get("passed"))
        lines.append(
            "| {n} | {finite} | {volt} | {refr} | {dir} | {minv} | {maxv} | "
            "{isi} | {repro} |".format(
                n=_fmt_int(size),
                finite=_yes(validation.get("finite_state")),
                volt=_yes(validation.get("voltage_bounds_ok")),
                refr=_yes(validation.get("refractory_ok")),
                dir=_yes(validation.get("directional_consistency_ok")),
                minv=_fmt_num(validation.get("observed_min_membrane_mv"), 2),
                maxv=_fmt_num(validation.get("observed_max_membrane_mv"), 2),
                isi=(
                    _fmt_num(validation.get("minimum_inter_spike_interval_ms"), 3)
                    if validation.get("minimum_inter_spike_interval_ms")
                    is not None
                    else "—"
                ),
                repro=repro,
            )
        )
    return lines


def _md_activity_table(series: list[dict]) -> list[str]:
    lines = [
        "| Neurons | Stimulated | Stim active | Non-stim active | "
        "Non-stim spikes | Non-stim share | Stim spikes |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in series:
        graph = record.get("graph", {})
        stim = record.get("activity_by_stimulation", {})
        lines.append(
            "| {n} | {sn} | {sa} | {na} | {ns} | {share} | {ss} |".format(
                n=_fmt_int(graph.get("n_nodes")),
                sn=_fmt_int(stim.get("stimulated_neurons")),
                sa=_fmt_int(stim.get("stimulated_active_neurons")),
                na=_fmt_int(stim.get("non_stimulated_active_neurons")),
                ns=_fmt_int(stim.get("non_stimulated_spikes")),
                share=_fmt_num(
                    100.0 * float(stim.get("non_stimulated_spike_fraction", 0.0)),
                    2,
                ) + "%",
                ss=_fmt_int(stim.get("stimulated_spikes")),
            )
        )
    return lines


def _md_memory_table(series: list[dict]) -> list[str]:
    lines = [
        "| Neurons | Graph | Neuron state | Synapse (excl. delay) | "
        "Delay buffers | Recorder | Retained | RSS after sim | Peak WS |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in series:
        graph = record.get("graph", {})
        memory = record.get("memory", {})
        components = memory.get("components_mb", {})
        synapse_total = float(components.get("synapse_state", 0.0))
        delays = float(components.get("delay_buffers", 0.0))
        synapse_arrays = max(synapse_total - delays, 0.0)
        lines.append(
            "| {n} | {g} | {ns} | {s} | {d} | {r} | {t} | {rss} | {peak} |".format(
                n=_fmt_int(graph.get("n_nodes")),
                g=_fmt_num(components.get("graph_arrays"), 2),
                ns=_fmt_num(components.get("neuron_state"), 4),
                s=_fmt_num(synapse_arrays, 3),
                d=_fmt_num(delays, 4),
                r=_fmt_num(components.get("spike_recorder"), 2),
                t=_fmt_num(memory.get("retained_arrays_mb"), 2),
                rss=_fmt_num(memory.get("rss_after_simulation_mb"), 1),
                peak=_fmt_num(
                    memory.get("process_peak_wset_final_mb"), 1
                ),
            )
        )
    return lines


def _md_failures(failures: list[dict]) -> list[str]:
    if not failures:
        return ["No failed or skipped runs."]
    lines = [
        "| Label | Status | Reason | Available GB | Last successful | Log |",
        "|---|---|---|---:|---|---|",
    ]
    for failure in failures:
        last = failure.get("last_successful_benchmark") or {}
        last_text = (
            f"{last.get('label')} ({_fmt_int(last.get('n_neurons'))} neurons)"
            if last
            else "none"
        )
        lines.append(
            "| {label} | {status} | {reason} | {mem} | {last} | {log} |".format(
                label=failure.get("label"),
                status=failure.get("status"),
                reason=str(failure.get("reason")).replace("|", "/"),
                mem=_fmt_num(failure.get("available_memory_gb"), 3),
                last=last_text,
                log=failure.get("log") or "—",
            )
        )
    return lines


def render_scalability_markdown(report: dict, series: list[dict]) -> str:
    environment = report["environment"]
    reproducibility = report["reproducibility"]
    full = report["full_connectome"]
    lines: list[str] = []
    lines.append("# FLY-SURFER Phase 2.5 — scalability and stability")
    lines.append("")
    lines.append(f"Generated {report['generated_at_utc']}.")
    lines.append("")
    verdict = {
        "complete": "All requested sizes completed.",
        "partial": "Some requested sizes did not complete; see failures.",
        "failed": "No requested size completed.",
    }[report["status"]]
    lines.append(f"**Verdict:** {verdict}")
    if full["status"] != "ok":
        lines.append(
            f"Full-connectome status: **{full['status']}** — "
            f"{full.get('reason') or 'no reason recorded'}"
        )
    lines.append("")
    lines.append(
        "Protocol: 200 ms simulated, dt = 0.5 ms (400 steps), the same "
        "stimulus rule and parameters for every size. Subsets use reproducible "
        "connected sampling (seed 42); the full size uses the validated "
        "connectome artifact directly. No raw CSV is read."
    )
    lines.append("")
    lines.append("## Environment")
    lines.append("")
    lines.append(
        f"- Python {environment.get('python')}, NumPy {environment.get('numpy')}"
    )
    lines.append(f"- Platform: {environment.get('platform')}")
    lines.append(
        f"- {environment.get('cpu_count')} logical CPUs, "
        f"{environment.get('total_memory_gb')} GB total RAM"
    )
    lines.append(
        f"- {_available_gb()} GB available when the report was written"
    )
    lines.append("")
    lines.append("## Scaling results")
    lines.append("")
    lines.extend(_md_scaling_table(series))
    lines.append("")
    if len(series) >= 2:
        first, last = series[0], series[-1]
        first_rate = first["performance"]["steps_per_second"]
        last_rate = last["performance"]["steps_per_second"]
        lines.append(
            f"Throughput moved from {first_rate:,.1f} steps/s at "
            f"{first['graph']['n_nodes']:,} neurons to {last_rate:,.1f} "
            f"steps/s at {last['graph']['n_nodes']:,} neurons. This reflects "
            "per-step work growing with neuron and edge counts; it is not a "
            "model-quality comparison."
        )
        lines.append("")
    lines.append("## Timing decomposition")
    lines.append("")
    lines.append(
        "Recording is a stage inside simulation (spike copy per step), not a "
        "separate pass. Sampling and extraction apply only to subsets; graph "
        "load is the validated artifact load."
    )
    lines.append("")
    lines.extend(_md_timing_table(series))
    lines.append("")
    lines.append("## Stability validation")
    lines.append("")
    lines.append(
        "Voltage bounds check the configured floor (−90 mV) and threshold "
        "(−50 mV). Refractory checks the minimum inter-spike interval. "
        "Directional consistency checks that recorded transmissions equal the "
        "sum of out-degrees of spiking neurons."
    )
    lines.append("")
    lines.extend(_md_stability_table(series, reproducibility))
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    if reproducibility.get("passed") is not None:
        lines.append(
            f"Size {_fmt_int(reproducibility.get('size'))} was run twice in "
            f"separate processes. Activity hash match: "
            f"**{_yes(reproducibility.get('activity_hash_match'))}**; root-ID "
            f"set match: **{_yes(reproducibility.get('root_id_hash_match'))}**; "
            f"spike-count match: "
            f"**{_yes(reproducibility.get('spike_count_match'))}**; "
            f"transmission match: "
            f"**{_yes(reproducibility.get('transmissions_match'))}**."
        )
        if reproducibility.get("reason"):
            lines.append("")
            lines.append(f"Reason: {reproducibility['reason']}")
    else:
        lines.append("Reproducibility comparison was not available.")
    lines.append("")
    lines.append("## Activity by stimulation")
    lines.append("")
    lines.extend(_md_activity_table(series))
    lines.append("")
    lines.append(
        "Non-stimulated share is the fraction of all spikes emitted by neurons "
        "that never received the external stimulus. Equal firing does not mean "
        "equal health or correctness."
    )
    lines.append("")
    lines.append("## Memory")
    lines.append("")
    lines.extend(_md_memory_table(series))
    lines.append("")
    lines.append(
        "See `memory_report.md` for the component model, temporary-buffer "
        "estimates and measurement caveats."
    )
    lines.append("")
    lines.append("## Full-connectome attempt")
    lines.append("")
    lines.append(
        f"- Status: **{full['status']}**\n"
        f"- Reason: {full.get('reason') or 'completed within resources'}\n"
        f"- Available memory at attempt: "
        f"{_fmt_num(full.get('available_memory_gb'), 3)} GB"
    )
    last = full.get("last_successful_benchmark") or {}
    if last:
        lines.append(
            f"- Last successful benchmark before the full attempt: "
            f"{last.get('label')} ({_fmt_int(last.get('n_neurons'))} neurons)"
        )
    else:
        lines.append("- Last successful benchmark before the full attempt: none")
    lines.append("")
    lines.append("## Failures and skips")
    lines.append("")
    lines.extend(_md_failures(report["failures"]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if series:
        retained = [record["memory"]["retained_arrays_mb"] for record in series]
        peaks = [
            record["performance"]["process_peak_wset_final_mb"]
            for record in series
        ]
        lines.append(
            f"- Retained simulation arrays ranged from {min(retained):,.2f} MB "
            f"to {max(retained):,.2f} MB; process peaks ranged from "
            f"{min(peaks):,.1f} MB to {max(peaks):,.1f} MB."
        )
        stable = all(
            record.get("validation", {}).get("passed") for record in series
        )
        lines.append(
            f"- Numerical and structural checks passed for every completed "
            f"size: **{_yes(stable)}**."
        )
        spike_share = [
            record["activity_by_stimulation"]["non_stimulated_spike_fraction"]
            for record in series
        ]
        lines.append(
            f"- Non-stimulated spikes were {min(spike_share):.2%}–"
            f"{max(spike_share):.2%} of all spikes across completed sizes. "
            "They confirm propagation through the sampled graph rather than "
            "isolated stimulus-driven firing, but the very high shares at "
            "large sizes may also reflect strong excitatory coupling under "
            "the model's weight and transmitter assumptions. This is not "
            "evidence of biological correctness."
        )
        least_active = min(
            series, key=lambda record: record["activity"]["mean_rate_hz"]
        )
        if least_active["graph"]["n_nodes"] != series[0]["graph"]["n_nodes"]:
            lines.append(
                f"- Activity was not monotonic in size: the "
                f"{least_active['graph']['n_nodes']:,}-neuron sample had the "
                f"lowest mean rate "
                f"({least_active['activity']['mean_rate_hz']:.3f} Hz; "
                f"{least_active['activity']['n_spikes']:,} spikes). That rate "
                f"was no higher than the "
                f"{series[0]['graph']['n_nodes']:,}-neuron sample's, so "
                "sampled composition can dominate size effects."
            )
    lines.append(
        "- The suite varies size only. It does not establish that any size is "
        "biologically correct, and throughput is not a scientific metric."
    )
    lines.append("")
    lines.append("## Scientific limitations")
    lines.append("")
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append(
        "- FAFB covers the adult female brain only; motor output and the "
        "ventral nerve cord are out of scope in Phase 2.5."
    )
    lines.append(
        "- A single 200 ms protocol and seed cannot characterise all network "
        "regimes or long-run stability."
    )
    lines.append("")
    lines.append("## Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("python -m experiments.phase_2_5.run_all")
    lines.append("python -m experiments.phase_2_5.benchmark --size 5000 \\")
    lines.append(
        "    --output experiments/phase_2_5/results/benchmark_n5000.json"
    )
    lines.append("pytest")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_memory_markdown(report: dict, series: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# FLY-SURFER Phase 2.5 — memory report")
    lines.append("")
    lines.append(f"Generated {report['generated_at_utc']}.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "- Retained component bytes are exact NumPy `nbytes` sums: connectome "
        "CSR arrays, LIF membrane/refractory state, synapse weights/signs/"
        "currents, delay ring buffers and preallocated spike recorder."
    )
    lines.append(
        "- Process RSS and peak working set come from `psutil`. Each benchmark "
        "runs in a fresh subprocess, so peaks are not shared across sizes."
    )
    lines.append(
        "- `tracemalloc` is not used: it does not track NumPy data buffers. "
        "Retained bytes are therefore the authoritative simulation-state "
        "measure."
    )
    lines.append(
        "- No membrane traces or dense adjacency matrices are stored. Only "
        "spike times and neuron indices are recorded."
    )
    lines.append("")
    lines.append("## Components by size")
    lines.append("")
    lines.extend(_md_memory_table(series))
    lines.append("")
    lines.append("All values in MB. Peak WS is process peak working set.")
    lines.append("")
    lines.append("## Scaling")
    lines.append("")
    for record in series:
        graph = record.get("graph", {})
        memory = record.get("memory", {})
        n = max(int(graph.get("n_nodes", 0)), 1)
        m = max(int(graph.get("n_edges", 0)), 1)
        delay_bytes = int(memory.get("delay_buffer_bytes", 0))
        synapse_arrays = int(
            memory.get(
                "synapse_arrays_bytes",
                int(memory.get("synapse_state_bytes", 0)) - delay_bytes,
            )
        )
        structural = (
            int(memory.get("graph_arrays_bytes", 0))
            + int(memory.get("neuron_state_bytes", 0))
            + synapse_arrays
            + delay_bytes
        )
        lines.append(
            f"- **{int(graph.get('n_nodes', 0)):,} neurons / "
            f"{int(graph.get('n_edges', 0)):,} edges:** "
            f"{memory.get('graph_arrays_bytes', 0) / m:,.2f} bytes of graph "
            f"arrays per edge; "
            f"{synapse_arrays / m:,.2f} bytes of synapse weights/currents "
            f"per edge; "
            f"{delay_bytes / n:,.2f} bytes of delay buffers per neuron; "
            f"{structural / n:,.2f} bytes of structural arrays per neuron; "
            f"{memory.get('retained_arrays_bytes', 0) / n:,.2f} bytes retained "
            f"per neuron including the fixed recorder."
        )
    lines.append("")
    lines.append("## Spike recording bound")
    lines.append("")
    first = series[0] if series else {}
    memory = first.get("memory", {})
    lines.append(
        f"The recorder is preallocated at "
        f"{_fmt_int(memory.get('recorder_capacity'))} spikes "
        f"({_fmt_num(memory.get('components_mb', {}).get('spike_recorder'), 2)}"
        " MB) for every "
        "size. This is deliberate: recording is bounded and overflow raises "
        "`SpikeCapacityExceeded` instead of silently dropping spikes. Because "
        "the capacity is fixed, it dominates retained-array memory at small "
        "network sizes and is shown separately in the memory plot."
    )
    lines.append("")
    lines.append(
        "The recorder stores one float32 time and one int32 neuron index per "
        "spike. A size-specific capacity can be supplied through "
        "`simulation.max_recorded_spikes` when the expected spike count is "
        "known; the suite uses one capacity so runs are directly comparable."
    )
    lines.append("")
    lines.append("## Temporary propagation arrays")
    lines.append("")
    lines.append(
        "Temporary arrays are allocated per step and released: the input "
        "current vector, the spike index array, and `np.bincount` outputs for "
        "inhibitory and excitatory transmission. The simulator reports bounds:"
    )
    lines.append("")
    lines.append(
        "- `single_hub_propagation_temporary_bytes = 12 * max_out_degree + "
        "24 * n_neurons`"
    )
    lines.append(
        "- `worst_case_propagation_temporary_bytes = 12 * n_edges + "
        "24 * n_neurons`"
    )
    lines.append("")
    lines.append(
        "| Neurons | Max out-degree | Single-hub temp (MB) | "
        "Worst-case temp (MB) |"
    )
    lines.append("|---:|---:|---:|---:|")
    for record in series:
        graph = record.get("graph", {})
        memory = record.get("memory", {})
        lines.append(
            f"| {_fmt_int(graph.get('n_nodes'))} | "
            f"{_fmt_int(memory.get('max_out_degree'))} | "
            f"{_fmt_num(memory.get('single_hub_propagation_temporary_mb'), 3)} | "
            f"{_fmt_num(memory.get('worst_case_propagation_temporary_mb'), 2)} |"
        )
    lines.append("")
    lines.append("## Why process peak overstates subset memory")
    lines.append("")
    lines.append(
        "Every subset run loads the validated full graph to perform sampling "
        "and extraction. The source graph is then deleted and garbage "
        "collected, but the operating system is not required to return the "
        "freed pages immediately. Both the peak working set and the RSS after "
        "simulation can therefore include memory attributable to the source "
        "graph. The exact `retained_arrays_bytes` is the subset-only figure; "
        "process RSS is an upper bound."
    )
    lines.append("")
    if series:
        first, last = series[0], series[-1]
        lines.append(
            f"For example, at {_fmt_int(first['graph']['n_nodes'])} neurons the "
            f"source graph load reached "
            f"{_fmt_num(first['memory'].get('rss_after_source_load_mb'), 1)} MB "
            f"RSS while retained arrays were "
            f"{_fmt_num(first['memory'].get('retained_arrays_mb'), 2)} MB; at "
            f"{_fmt_int(last['graph']['n_nodes'])} neurons the corresponding "
            f"values were "
            f"{_fmt_num(last['memory'].get('rss_after_source_load_mb'), 1)} MB "
            f"and {_fmt_num(last['memory'].get('retained_arrays_mb'), 2)} MB. "
            "The full run uses the source graph directly and does not delete "
            "it, so its retained arrays legitimately include the graph."
        )
        lines.append("")
    lines.append("## Full-connectome feasibility")
    lines.append("")
    full = report["full_connectome"]
    if full["status"] == "ok":
        full_record = next(
            (record for record in series if record.get("label") == "full"), {}
        )
        lines.append(
            f"The full graph completed. Retained arrays were "
            f"{_fmt_num(full_record.get('memory', {}).get('retained_arrays_mb'), 2)} MB "
            f"and process peak working set was "
            f"{_fmt_num(full_record.get('performance', {}).get('process_peak_wset_final_mb'), 1)} MB."
        )
    else:
        last = full.get("last_successful_benchmark") or {}
        lines.append(
            f"The full graph did not complete: **{full['status']}**. "
            f"Reason: {full.get('reason') or 'not recorded'}. Available "
            f"memory: {_fmt_num(full.get('available_memory_gb'), 3)} GB. "
            f"Last successful size: {last.get('label', 'none')}."
        )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- RSS includes the Python interpreter, imported libraries and "
        "allocator overhead; it is not a pure simulation-state measure."
    )
    lines.append(
        "- NumPy `nbytes` counts logical array sizes, not page-rounded or "
        "allocator-retained memory."
    )
    lines.append(
        "- Peak working set is a Windows process metric; values are not "
        "directly comparable across operating systems."
    )
    lines.append(
        "- The suite uses one graph artifact and one protocol, so memory "
        "scaling is measured for this model, not for spiking simulation in "
        "general."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def _print_record(record: dict) -> None:
    status = record.get("status", "failed").upper()
    label = record.get("label")
    if record.get("status") == "ok":
        graph = record.get("graph", {})
        performance = record.get("performance", {})
        activity = record.get("activity", {})
        print(
            f"[{status}] {label}: {graph.get('n_nodes', 0):,} neurons, "
            f"{performance.get('steps_per_second', 0):,.1f} steps/s, "
            f"{activity.get('n_spikes', 0):,} spikes, "
            f"peak {performance.get('process_peak_wset_final_mb', 0):,.1f} MB",
            flush=True,
        )
    else:
        print(
            f"[{status}] {label}: {record.get('reason', 'no reason recorded')}",
            flush=True,
        )


def _reproducibility(
    records: list[dict], repeat_size: int | None
) -> dict:
    if repeat_size is None:
        return {
            "size": None,
            "passed": None,
            "reason": "no repeat size configured",
        }
    base_label = f"n{repeat_size}"
    repeat_label = f"n{repeat_size}_repeat"
    base = next(
        (record for record in records if record.get("label") == base_label),
        None,
    )
    repeat = next(
        (record for record in records if record.get("label") == repeat_label),
        None,
    )
    if base is None or repeat is None:
        return {
            "size": repeat_size,
            "base_label": base_label,
            "repeat_label": repeat_label,
            "passed": None,
            "reason": "repeat run was not performed in this invocation",
        }
    if base.get("status") != "ok" or repeat.get("status") != "ok":
        return {
            "size": repeat_size,
            "base_label": base_label,
            "repeat_label": repeat_label,
            "passed": False,
            "reason": (
                f"base status {base.get('status')}, "
                f"repeat status {repeat.get('status')}"
            ),
        }

    activity_hash_match = base.get("activity_hash") == repeat.get("activity_hash")
    root_id_hash_match = base.get("sample", {}).get(
        "root_id_sha256"
    ) == repeat.get("sample", {}).get("root_id_sha256")
    spike_count_match = base.get("activity", {}).get("n_spikes") == repeat.get(
        "activity", {}
    ).get("n_spikes")
    transmissions_match = base.get("synapses", {}).get(
        "spike_transmissions"
    ) == repeat.get("synapses", {}).get("spike_transmissions")
    passed = bool(
        activity_hash_match
        and root_id_hash_match
        and spike_count_match
        and transmissions_match
    )
    return {
        "size": repeat_size,
        "base_label": base_label,
        "repeat_label": repeat_label,
        "base_activity_hash": base.get("activity_hash"),
        "repeat_activity_hash": repeat.get("activity_hash"),
        "activity_hash_match": activity_hash_match,
        "root_id_hash_match": root_id_hash_match,
        "spike_count_match": spike_count_match,
        "transmissions_match": transmissions_match,
        "passed": passed,
        "reason": None if passed else "one or more deterministic outputs differ",
    }


def _parse_sizes(values: list[str]) -> list[int]:
    sizes: list[int] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                continue
            size = int(part)
            if size < 2:
                raise ValueError("benchmark sizes must be at least 2 neurons")
            sizes.append(size)
    return sizes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 2.5 scalability suite and write reports."
    )
    parser.add_argument(
        "--suite", default=str(DEFAULT_SUITE), help="scalability suite YAML"
    )
    parser.add_argument(
        "--sizes", nargs="+", default=None,
        help="override subset sizes (space or comma separated)",
    )
    parser.add_argument(
        "--skip-full", action="store_true",
        help="do not attempt the full connectome (recorded as not_requested)",
    )
    parser.add_argument(
        "--reports-only", action="store_true",
        help="regenerate plots and reports from existing benchmark JSON files",
    )
    args = parser.parse_args(argv)

    suite_path = _resolve(args.suite)
    suite = _load_yaml(suite_path)
    if args.sizes:
        sizes = _parse_sizes(args.sizes)
    else:
        sizes = [int(value) for value in suite["sampling"]["sizes"]]
    include_full = not args.skip_full
    full_size = int(suite["sampling"]["full_size"])
    if full_size in sizes:
        raise SystemExit(
            "the full size must be run through the dedicated full mode, "
            "not the subset list"
        )
    repeat_size = suite["benchmark"].get("repeat_reproducibility_size")
    repeat_size = None if repeat_size is None else int(repeat_size)
    subset_timeout = float(suite["benchmark"]["subset_timeout_seconds"])
    full_timeout = float(suite["benchmark"]["full_timeout_seconds"])

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = RESULTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    started_clock = time.perf_counter()
    records: list[dict] = []

    def run(size_request, label: str, role: str, timeout: float) -> None:
        result_path = RESULTS_DIR / f"benchmark_{label}.json"
        log_path = log_dir / f"benchmark_{label}.log"
        record = _run_one(
            size_request=size_request,
            label=label,
            role=role,
            suite_path=suite_path,
            result_path=result_path,
            log_path=log_path,
            timeout_s=timeout,
        )
        if record.get("status") != "ok":
            record["last_successful_benchmark"] = _last_success(records)
        records.append(record)
        _write_json(result_path, record)
        _print_record(record)

    if args.reports_only:
        labels: list[tuple[str, str]] = []
        for size in sizes:
            labels.append((f"n{size}", "series"))
            if repeat_size is not None and size == repeat_size:
                labels.append((f"n{size}_repeat", "reproducibility"))
        if include_full:
            labels.append(("full", "series"))
        for label, role in labels:
            result_path = RESULTS_DIR / f"benchmark_{label}.json"
            if not result_path.exists():
                raise SystemExit(
                    f"missing {result_path}; run the suite without "
                    "--reports-only first"
                )
            record = json.loads(result_path.read_text(encoding="utf-8"))
            record.setdefault("orchestrator", {})["role"] = role
            records.append(record)
            _print_record(record)
        if records:
            started_at = records[0].get("generated_at_utc", started_at)
    else:
        for size in sizes:
            run(size, f"n{size}", "series", subset_timeout)
            if repeat_size is not None and size == repeat_size:
                run(
                    size, f"n{size}_repeat", "reproducibility", subset_timeout
                )
        if include_full:
            run(full_size, "full", "series", full_timeout)

    reproducibility = _reproducibility(records, repeat_size)
    series = [
        record
        for record in records
        if record.get("orchestrator", {}).get("role") == "series"
    ]
    series = sorted(series, key=lambda record: record["graph"]["n_nodes"])

    plots = [
        make_memory_plot(series, PLOTS_DIR / "memory_vs_size.png"),
        make_speed_plot(series, PLOTS_DIR / "speed_vs_size.png"),
        make_active_plot(series, PLOTS_DIR / "active_neurons_vs_size.png"),
        make_spike_plot(series, PLOTS_DIR / "spike_count_vs_size.png"),
    ]

    finished_at = _utc_now()
    expected_sizes = _series_expected(sizes, include_full, full_size)
    report = build_report(
        suite_path=suite_path,
        suite=suite,
        records=records,
        reproducibility=reproducibility,
        plots=plots,
        expected_sizes=expected_sizes,
        include_full=include_full,
        started_at=started_at,
        finished_at=finished_at,
    )
    if args.reports_only:
        report["wall_seconds"] = round(
            sum(
                float(record.get("orchestrator", {}).get("wall_seconds", 0.0))
                for record in records
            ),
            3,
        )
    else:
        report["wall_seconds"] = round(time.perf_counter() - started_clock, 3)

    _write_json(REPORTS_DIR / "scalability_report.json", report)
    (REPORTS_DIR / "scalability_report.md").write_text(
        render_scalability_markdown(report, series), encoding="utf-8"
    )
    (REPORTS_DIR / "memory_report.md").write_text(
        render_memory_markdown(report, series), encoding="utf-8"
    )

    print("", flush=True)
    print(f"Status: {report['status']} ({len(series)} completed series runs)",
          flush=True)
    print(f"Full connectome: {report['full_connectome']['status']}", flush=True)
    for plot in plots:
        if plot is not None:
            print(f"  plot: {_relative(plot)}", flush=True)
    print(f"  report: {_relative(REPORTS_DIR / 'scalability_report.json')}",
          flush=True)
    print(f"  report: {_relative(REPORTS_DIR / 'scalability_report.md')}",
          flush=True)
    print(f"  report: {_relative(REPORTS_DIR / 'memory_report.md')}",
          flush=True)
    if report["status"] == "complete":
        return 0
    if report["status"] == "partial":
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
