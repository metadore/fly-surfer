"""Run one BANC simulation condition and save activity, metadata and hashes.

Examples::

    python experiments/phase_4g/run_banc_simulation.py \\
        --threshold 5 --duration-ms 100 --stimulus-count 64 \\
        --output experiments/results/phase_4g/smoke_t5_seed20261108

The output directory must be new (or empty). No earlier result is overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import BancConnectome, sha256_file  # noqa: E402
from brain.banc_simulator import BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)

BANC_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
CONFIG_PATH = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"


def _process_memory_mb() -> dict:
    try:
        import psutil

        info = psutil.Process().memory_info()
        peak = getattr(info, "peak_wset", None)
        return {
            "rss_mb": round(info.rss / 1024**2, 2),
            "peak_working_set_mb": None if peak is None else round(peak / 1024**2, 2),
        }
    except Exception:  # pragma: no cover - psutil is a declared dependency
        return {"rss_mb": None, "peak_working_set_mb": None}


def select_stimulus_indices(
    graph, count: int, selection: str, seed: int
) -> np.ndarray:
    n = int(graph.n_nodes)
    if count < 1 or count > n:
        raise ValueError(f"stimulus count must be in [1, {n}]")
    if selection == "highest_out_degree":
        degrees = np.diff(graph.out_indptr)
        order = np.lexsort((np.arange(n), -degrees))
        selected = order[:count]
    elif selection == "lowest_index":
        selected = np.arange(count)
    elif selection == "random":
        selected = np.random.default_rng(seed).choice(n, size=count, replace=False)
    else:
        raise ValueError(
            "selection must be highest_out_degree, lowest_index or random"
        )
    return np.sort(np.asarray(selected, dtype=np.int64))


def activity_hash(recorder) -> str:
    digest = hashlib.sha256()
    digest.update(
        np.ascontiguousarray(recorder.spike_times_ms).tobytes()
    )
    digest.update(
        np.ascontiguousarray(recorder.spike_neuron_indices).tobytes()
    )
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=int, choices=(1, 5, 10), default=5)
    parser.add_argument("--duration-ms", type=float, default=100.0)
    parser.add_argument("--dt-ms", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--stimulus-count", type=int, default=64)
    parser.add_argument(
        "--selection",
        choices=("highest_out_degree", "lowest_index", "random"),
        default="highest_out_degree",
    )
    parser.add_argument("--stimulus-current-pa", type=float, default=300.0)
    parser.add_argument("--stimulus-start-ms", type=float, default=10.0)
    parser.add_argument("--stimulus-end-ms", type=float, default=40.0)
    parser.add_argument("--background-current-pa", type=float, default=0.0)
    parser.add_argument("--noise-std-pa", type=float, default=0.0)
    parser.add_argument("--max-recorded-spikes", type=int, default=2_000_000)
    parser.add_argument("--no-stimulus", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists() and any(args.output.iterdir()):
        print(
            f"refusing to overwrite existing output directory {args.output}",
            file=sys.stderr,
        )
        return 2

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    started = time.perf_counter()
    graph_path = BANC_DIR / f"banc_graph_t{args.threshold}.npz"
    nodes_path = BANC_DIR / "banc_nodes.csv.gz"
    load_started = time.perf_counter()
    graph = BancConnectome.load(graph_path)
    nodes = pd.read_csv(nodes_path)
    load_s = time.perf_counter() - load_started
    policy_started = time.perf_counter()
    policy = build_synapse_policy(
        graph,
        nodes,
        SignPolicy.from_config(config["transmitter_sign_policy"]),
        WeightPolicy.from_config(config["weight_policy"]["primary"]),
    )
    policy_s = time.perf_counter() - policy_started

    stimulation = None
    selected = np.empty(0, dtype=np.int64)
    if not args.no_stimulus:
        selected = select_stimulus_indices(
            graph, args.stimulus_count, args.selection, args.seed
        )
        stimulation = BancStimulation(
            selected,
            args.stimulus_current_pa,
            args.stimulus_start_ms,
            args.stimulus_end_ms,
            label=(
                f"{args.selection}:{args.stimulus_count}@"
                f"{args.stimulus_current_pa:g}pA"
            ),
        )

    before = _process_memory_mb()
    build_started = time.perf_counter()
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=args.dt_ms,
        duration_ms=args.duration_ms,
        seed=args.seed,
        background_current_pa=args.background_current_pa,
        noise_std_pa=args.noise_std_pa,
        stimulation=stimulation,
        max_recorded_spikes=args.max_recorded_spikes,
    )
    build_s = time.perf_counter() - build_started
    result = simulator.run(duration_ms=args.duration_ms, progress=args.progress)
    after = _process_memory_mb()
    paths = result.save(args.output)

    payload = {
        "phase": "4G.3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "inputs": {
            "graph": str(graph_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "graph_sha256": sha256_file(graph_path),
            "node_table_sha256": sha256_file(nodes_path),
            "policy_config_sha256": sha256_file(CONFIG_PATH),
        },
        "setup": {
            "graph_load_s": round(load_s, 3),
            "policy_build_s": round(policy_s, 3),
            "simulator_init_s": round(build_s, 3),
            "total_setup_s": round(time.perf_counter() - started, 3),
            "memory_before": before,
            "memory_after": after,
        },
        "stimulus_indices": [int(value) for value in selected],
        "stimulus_root_ids": [
            int(value) for value in graph.root_ids[selected]
        ],
        "summary": result.summary,
        "activity_sha256": activity_hash(result.recorder),
        "outputs": paths,
        "no_stimulus": bool(args.no_stimulus),
        "not_a_biological_claim": (
            "This is a seeded simulation under declared modelling priors; it "
            "does not establish physiological connectivity or motor control."
        ),
    }
    if args.evidence:
        payload["evidence"] = {
            "policy": policy.describe(),
            "stimulation_label": None
            if stimulation is None
            else stimulation.label,
        }
    metadata_path = args.output / "run_metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    summary = result.summary
    print(
        json.dumps(
            {
                "threshold": args.threshold,
                "nodes": summary["graph"]["n_nodes"],
                "edges": summary["graph"]["n_edges"],
                "stimulated_neurons": len(selected),
                "spikes": summary["activity"]["n_spikes"],
                "active_neurons": summary["activity"]["active_neurons"],
                "active_fraction": summary["activity"]["active_fraction"],
                "mean_rate_hz": summary["activity"]["mean_rate_hz"],
                "runtime_s": summary["simulation"]["runtime_s"],
                "steps_per_second": summary["simulation"]["steps_per_second"],
                "memory_after": after,
                "activity_sha256": payload["activity_sha256"],
                "output": str(args.output),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
