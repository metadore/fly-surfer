"""Phase 5C benchmark: sparse edge-indexed eligibility traces.

Compares the lazy decay store with a dense per-edge decay baseline at sizes up
to the BANC t5 edge tables. The dense baseline is a benchmark reference only;
it is never used by the plasticity stack.

The BANC section loads the published graph artifact and builds the declared
sign policy read-only. It simulates no neuron and changes no weight: it measures
trace storage, mapping and update cost at the real edge count.

Writes:
  experiments/results/phase_5c/trace_benchmark.json

Usage:
  python -m experiments.phase_5.benchmark_traces
  python -m experiments.phase_5.benchmark_traces --quick
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plasticity.traces import (  # noqa: E402
    EligibilityStore,
    SparseDelayLine,
    load_trace_config,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase_5c"
RESULT_PATH = RESULTS_DIR / "trace_benchmark.json"
GRAPH_T5 = PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_graph_t5.npz"
NODES_PATH = PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_nodes.csv.gz"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def step_edges(rng: np.random.Generator, n_edges: int, k: int) -> np.ndarray:
    """Independent draws, deduplicated and sorted (unique CSR edge slots)."""
    return np.unique(rng.integers(0, n_edges, size=k, dtype=np.int64))


def sparse_run(
    n_edges: int,
    *,
    n_steps: int,
    active_fraction: float,
    prune_interval: int,
    reward_read_steps: tuple[int, ...],
    seed: int,
    tau_e_ms: float,
    dt_ms: float,
    prune_threshold: float,
) -> dict:
    store = EligibilityStore(
        n_edges,
        tau_e_ms=tau_e_ms,
        dt_ms=dt_ms,
        prune_threshold=prune_threshold,
    )
    rng = np.random.default_rng(seed)
    k = max(1, int(round(n_edges * active_fraction)))
    reads: list[float] = []
    pruned = 0
    updates = 0
    started = time.perf_counter()
    for step in range(n_steps):
        edges = step_edges(rng, n_edges, k)
        updates += store.accumulate(edges)
        if step in reward_read_steps:
            reads.append(float(np.mean(store.value(edges))))
        store.advance(1)
        if (step + 1) % prune_interval == 0:
            pruned += store.prune()
    runtime = time.perf_counter() - started
    touched_bytes = int(store.active_edges.nbytes)
    dense_equivalent_bytes = int(n_edges * np.dtype(np.float32).itemsize)
    return {
        "strategy": "lazy_edge_indexed",
        "n_edges": int(n_edges),
        "n_steps": int(n_steps),
        "edges_per_step": int(k),
        "total_edge_updates": int(updates),
        "runtime_s": round(runtime, 6),
        "per_step_ms": round(1000.0 * runtime / n_steps, 6),
        "per_update_us": round(1e6 * runtime / max(1, updates), 6),
        "pruned_total": int(pruned),
        "reward_read_means": [round(value, 9) for value in reads],
        "n_touched": int(store.n_touched),
        "capacity_bytes": store.capacity_bytes(n_edges),
        "touched_list_bytes": touched_bytes,
        "store_memory_bytes": store.memory_bytes,
        "dense_value_only_bytes": dense_equivalent_bytes,
        "trace_l1": store.sparsity_report()["l1"],
        "final_nonzero": store.sparsity_report()["n_nonzero"],
        "arrays_are_one_dimensional": bool(
            store._value.ndim == 1
            and store._stamp.ndim == 1
            and store.active_edges.ndim == 1
        ),
    }


def dense_run(
    n_edges: int,
    *,
    n_steps: int,
    active_fraction: float,
    reward_read_steps: tuple[int, ...],
    seed: int,
    tau_e_ms: float,
    dt_ms: float,
    prune_threshold: float,
) -> dict:
    """Reference baseline: materialise decay on every edge every step."""
    values = np.zeros(n_edges, dtype=np.float32)
    decay = np.float32(np.exp(-dt_ms / tau_e_ms))
    rng = np.random.default_rng(seed)
    k = max(1, int(round(n_edges * active_fraction)))
    reads: list[float] = []
    started = time.perf_counter()
    for step in range(n_steps):
        edges = step_edges(rng, n_edges, k)
        values *= decay
        values[edges] += 1.0
        if step in reward_read_steps:
            reads.append(float(np.mean(values[edges])))
    runtime = time.perf_counter() - started
    return {
        "strategy": "dense_full_decay",
        "n_edges": int(n_edges),
        "n_steps": int(n_steps),
        "edges_per_step": int(k),
        "runtime_s": round(runtime, 6),
        "per_step_ms": round(1000.0 * runtime / n_steps, 6),
        "full_array_updates": int(n_edges * n_steps),
        "reward_read_means": [round(value, 9) for value in reads],
        "memory_bytes": int(values.nbytes),
        "final_nonzero": int(np.count_nonzero(values >= prune_threshold)),
    }


def activity_regime(
    n_edges: int,
    *,
    fractions: tuple[float, ...],
    n_steps: int,
    tau_e_ms: float,
    dt_ms: float,
    prune_threshold: float,
    prune_interval: int,
    seed: int,
) -> list[dict]:
    """Compare the two strategies at the same size and different activity.

    Trace work should follow the number of active edges, so the sparse/dense
    ratio is reported as a function of activity rather than asserted as a
    wall-clock win on one machine.
    """
    rows = []
    for fraction in fractions:
        options = {
            "n_steps": n_steps,
            "active_fraction": fraction,
            "reward_read_steps": (n_steps // 2,),
            "seed": seed,
            "tau_e_ms": tau_e_ms,
            "dt_ms": dt_ms,
            "prune_threshold": prune_threshold,
        }
        sparse = sparse_run(n_edges, prune_interval=prune_interval, **options)
        dense = dense_run(n_edges, **options)
        rows.append(
            {
                "n_edges": int(n_edges),
                "n_steps": int(n_steps),
                "active_fraction": fraction,
                "sparse": sparse,
                "dense": dense,
                "speedup": round(
                    dense["runtime_s"] / max(1e-12, sparse["runtime_s"]), 4
                ),
                "decay_work_ratio": round(
                    dense["full_array_updates"]
                    / max(1, sparse["total_edge_updates"]),
                    4,
                ),
            }
        )
    return rows


def banc_benchmark(trace_config, *, quick: bool) -> dict:
    if not GRAPH_T5.is_file() or not NODES_PATH.is_file():
        return {
            "available": False,
            "reason": "BANC t5 graph artifact is not present",
        }
    from brain.banc_graph import BancConnectome
    from brain.banc_synapse_policy import (
        SignPolicy,
        WeightPolicy,
        build_synapse_policy,
    )
    import yaml

    started = time.perf_counter()
    graph = BancConnectome.load(GRAPH_T5)
    nodes = pd.read_csv(NODES_PATH)
    with POLICY_CONFIG.open("r", encoding="utf-8") as handle:
        policy_payload = yaml.safe_load(handle)
    sign_policy = SignPolicy.from_config(policy_payload["transmitter_sign_policy"])
    weight_policy = WeightPolicy.from_config(policy_payload["weight_policy"]["primary"])
    policy = build_synapse_policy(graph, nodes, sign_policy, weight_policy)
    load_s = time.perf_counter() - started

    plastic = (policy.edge_exc_weight > 0) | (policy.edge_inh_weight > 0)
    positions = np.flatnonzero(plastic).astype(np.int64)
    n_plastic = int(positions.size)
    if n_plastic == 0:
        raise RuntimeError("the declared policy signed no edge")

    sample_count = min(2000, n_plastic)
    sample_slots = np.linspace(0, n_plastic - 1, sample_count, dtype=np.int64)
    sample_edges = positions[sample_slots]
    source_signs = policy.neuron_signs[np.asarray(graph.edge_src[sample_edges], dtype=np.int64)]
    mapping_ok = bool(
        np.all(np.diff(positions) > 0)
        and np.all(plastic[positions])
        and np.all(source_signs != 0)
        and np.all(
            (policy.edge_exc_weight[sample_edges] > 0)
            | (policy.edge_inh_weight[sample_edges] > 0)
        )
    )
    sample_destinations = np.asarray(graph.edge_dst[sample_edges], dtype=np.int64)
    destinations_in_range = bool(
        sample_destinations.size == 0
        or (sample_destinations.min() >= 0 and sample_destinations.max() < graph.n_nodes)
    )

    banc = trace_config.banc
    n_steps = int(banc.get("n_steps", 200))
    fraction = float(banc.get("active_fraction_per_step", 0.001))
    prune_interval = int(banc.get("prune_interval_steps", 50))
    seed = int(banc.get("seed", 20261113))
    if quick:
        n_steps = min(n_steps, 20)

    sparse = sparse_run(
        n_plastic,
        n_steps=n_steps,
        active_fraction=fraction,
        prune_interval=prune_interval,
        reward_read_steps=(n_steps // 3, 2 * n_steps // 3),
        seed=seed,
        tau_e_ms=trace_config.tau_e_ms,
        dt_ms=trace_config.dt_ms,
        prune_threshold=trace_config.prune_threshold,
    )
    dense = dense_run(
        n_plastic,
        n_steps=n_steps,
        active_fraction=fraction,
        reward_read_steps=(n_steps // 3, 2 * n_steps // 3),
        seed=seed,
        tau_e_ms=trace_config.tau_e_ms,
        dt_ms=trace_config.dt_ms,
        prune_threshold=trace_config.prune_threshold,
    )

    delay = SparseDelayLine(2)
    delay_started = time.perf_counter()
    rng = np.random.default_rng(seed + 1)
    k = max(1, int(round(n_plastic * fraction)))
    pushed = 0
    delivered = 0
    for step in range(n_steps):
        edges = step_edges(rng, n_plastic, k)
        pushed += delay.push(step, edges)
        delivered += int(delay.pop_ready(step - 2).size) if step >= 2 else 0
    for step in range(max(0, n_steps - 2), n_steps + 2):
        delivered += int(delay.pop_ready(step).size)
    delay_runtime = time.perf_counter() - delay_started

    return {
        "available": True,
        "graph": {
            "path": str(GRAPH_T5.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(GRAPH_T5),
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "threshold": int(graph.threshold),
        },
        "policy": {
            "path": str(POLICY_CONFIG.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(POLICY_CONFIG),
            "n_plastic_edges": n_plastic,
            "signed_edges_reported": int(policy.coverage["signed_edges"]),
            "plastic_edge_share": round(n_plastic / graph.n_edges, 9),
            "counts_match": bool(n_plastic == int(policy.coverage["signed_edges"])),
        },
        "mapping": {
            "sample_size": int(sample_count),
            "positions_are_sorted_and_plastic": mapping_ok,
            "destinations_in_range": destinations_in_range,
            "first_edge": int(sample_edges[0]),
            "last_edge": int(sample_edges[-1]),
        },
        "storage": {
            "compact_capacity_bytes": EligibilityStore.capacity_bytes(n_plastic),
            "all_edge_capacity_bytes": EligibilityStore.capacity_bytes(graph.n_edges),
            "dense_plastic_value_bytes": int(
                n_plastic * np.dtype(np.float32).itemsize
            ),
            "compact_under_20mb": bool(
                EligibilityStore.capacity_bytes(n_plastic) < 20 * 1024 * 1024
            ),
        },
        "sparse": sparse,
        "dense": dense,
        "speedup": round(dense["runtime_s"] / max(1e-12, sparse["runtime_s"]), 4),
        "delay_line": {
            "delay_steps": 2,
            "edges_pushed": int(pushed),
            "edges_delivered": int(delivered),
            "pending_at_end": int(delay.pending_packets),
            "runtime_s": round(delay_runtime, 6),
            "all_packets_delivered": bool(
                delay.pending_packets == 0 and delivered == pushed
            ),
        },
        "load_and_policy_s": round(load_s, 4),
        "simulated_neurons": False,
        "weights_modified": False,
    }


def build_result(*, quick: bool = False) -> dict:
    started = time.perf_counter()
    config = load_trace_config(CONFIG_PATH)
    benchmark = config.benchmark
    sizes = [int(value) for value in benchmark.get("sizes", [])]
    if not sizes:
        raise ValueError("traces.benchmark.sizes must not be empty")
    n_steps = int(benchmark.get("n_steps", 600))
    fraction = float(benchmark.get("active_fraction_per_step", 0.01))
    prune_interval = int(benchmark.get("prune_interval_steps", 50))
    read_steps = tuple(int(value) for value in benchmark.get("reward_read_steps", []))
    seed = int(benchmark.get("seed", 20261112))
    if quick:
        sizes = [value for value in sizes if value <= 100_000]
        n_steps = min(n_steps, 60)

    rows = []
    for size in sizes:
        options = {
            "n_steps": n_steps,
            "active_fraction": fraction,
            "reward_read_steps": read_steps,
            "seed": seed,
            "tau_e_ms": config.tau_e_ms,
            "dt_ms": config.dt_ms,
            "prune_threshold": config.prune_threshold,
        }
        sparse = sparse_run(size, prune_interval=prune_interval, **options)
        dense = dense_run(size, **options)
        rows.append(
            {
                "n_edges": size,
                "n_steps": n_steps,
                "sparse": sparse,
                "dense": dense,
                "speedup": round(
                    dense["runtime_s"] / max(1e-12, sparse["runtime_s"]), 4
                ),
                "memory_ratio": round(
                    sparse["store_memory_bytes"] / max(1, dense["memory_bytes"]), 4
                ),
            }
        )

    banc = banc_benchmark(config, quick=quick)

    regime_size = max(sizes)
    regime_rows = activity_regime(
        regime_size,
        fractions=(fraction, 0.001),
        n_steps=min(n_steps, 100),
        tau_e_ms=config.tau_e_ms,
        dt_ms=config.dt_ms,
        prune_threshold=config.prune_threshold,
        prune_interval=prune_interval,
        seed=seed,
    )

    checks = {
        "lazy_matches_dense_reads": all(
            len(row["sparse"]["reward_read_means"]) == len(row["dense"]["reward_read_means"])
            and all(
                abs(a - b) <= 1e-5 * max(1.0, abs(a))
                for a, b in zip(
                    row["sparse"]["reward_read_means"],
                    row["dense"]["reward_read_means"],
                )
            )
            for row in rows
        ),
        "no_pair_matrix": all(
            row["sparse"]["arrays_are_one_dimensional"] for row in rows
        ),
        "sparse_work_scales_with_active_edges": bool(
            all(
                row["sparse"]["total_edge_updates"]
                <= row["n_edges"] * row["n_steps"] * fraction * 1.05
                for row in rows
            )
            and all(
                regime["sparse"]["total_edge_updates"]
                <= regime["n_edges"]
                * regime["n_steps"]
                * regime["active_fraction"]
                * 1.05
                for regime in regime_rows
            )
        ),
        "touched_list_bounded": all(
            row["sparse"]["n_touched"] <= row["n_edges"] for row in rows
        ),
        "banc_mapping": bool(
            banc.get("available")
            and banc["mapping"]["positions_are_sorted_and_plastic"]
            and banc["mapping"]["destinations_in_range"]
        ),
        "banc_count_matches_policy": bool(
            banc.get("available") and banc["policy"]["counts_match"]
        ),
        "banc_storage_bounded": bool(
            banc.get("available") and banc["storage"]["compact_under_20mb"]
        ),
        "banc_delay_line_complete": bool(
            banc.get("available") and banc["delay_line"]["all_packets_delivered"]
        ),
        "no_simulation": bool(
            not banc.get("simulated_neurons", False)
            and not banc.get("weights_modified", False)
        ),
    }
    runtime = time.perf_counter() - started
    return {
        "phase": "5C",
        "title": "Sparse edge-indexed eligibility traces",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": "FLY-SURFER",
        "config": {
            "path": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(CONFIG_PATH),
            "traces": config.describe(),
            "benchmark": {
                "sizes": sizes,
                "n_steps": n_steps,
                "active_fraction_per_step": fraction,
                "prune_interval_steps": prune_interval,
                "reward_read_steps": list(read_steps),
                "seed": seed,
                "quick": quick,
            },
        },
        "strategies": {
            "lazy": "value and timestamp arrays per edge; clock advance is O(1); reads and updates materialise lambda**age",
            "dense_reference": "float32 value per edge multiplied by lambda every step",
            "selection": "lazy by default; the dense strategy exists only for this benchmark",
        },
        "synthetic": rows,
        "activity_regime": regime_rows,
        "banc": banc,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "resources": {
            "runtime_s": round(runtime, 4),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "data_touched": "BANC t5 graph and policy read-only" if banc.get("available") else "synthetic only",
            "weights_modified": False,
            "neurons_simulated": False,
        },
        "limitations": [
            "Active edges are drawn uniformly at random, not from a simulated spike pattern.",
            "The dense baseline is a reference implementation, not part of the plasticity stack.",
            "The BANC section measures trace storage and updates at the real edge count; it does not simulate the network.",
            "Timings are a single machine run on a shared desktop CPU and are indicative, not a benchmark suite.",
            "The lazy store does O(active) trace work per step but pays per-element Python/NumPy validation overhead; at 1% activity it was slower in wall-clock time than the dense float32 multiply in this run.",
            "The lazy store trades about 3x the value-array memory of a float32-only dense trace (value plus int32 timestamp plus touched list) for bounded per-step work.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="small sizes and few steps")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = build_result(quick=args.quick)
    print(
        json.dumps(
            {
                "checks": result["checks"],
                "all_checks_passed": result["all_checks_passed"],
                "runtime_s": result["resources"]["runtime_s"],
                "banc_available": result["banc"].get("available"),
            },
            indent=1,
        )
    )
    for row in result["synthetic"]:
        print(
            f"{row['n_edges']:>9,} edges  sparse {row['sparse']['runtime_s']:.3f}s  "
            f"dense {row['dense']['runtime_s']:.3f}s  speedup {row['speedup']:.2f}x  "
            f"mem ratio {row['memory_ratio']:.2f}x"
        )
    for row in result["activity_regime"]:
        print(
            f"{row['n_edges']:>9,} edges @ {row['active_fraction']:.1%} active  "
            f"sparse {row['sparse']['runtime_s']:.3f}s  dense "
            f"{row['dense']['runtime_s']:.3f}s  speedup {row['speedup']:.2f}x  "
            f"decay-work ratio {row['decay_work_ratio']:.1f}x"
        )
    if result["banc"].get("available"):
        banc = result["banc"]
        print(
            f"BANC plastic edges {banc['policy']['n_plastic_edges']:,}  "
            f"compact {banc['storage']['compact_capacity_bytes'] / 1024 / 1024:.2f} MiB  "
            f"sparse {banc['sparse']['runtime_s']:.3f}s"
        )
    if not args.no_write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {RESULT_PATH}")
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
