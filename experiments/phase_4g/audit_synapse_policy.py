"""Phase 4G.2 audit of the BANC transmitter-sign and edge-weight policy.

Loads each Phase 4D threshold graph in turn, applies the declared policy and
writes ``reports/PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.json``. Graphs are
released before the next one is loaded so only one threshold is resident.
"""

from __future__ import annotations

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
from brain.banc_synapse_policy import (  # noqa: E402
    CLASS_NAMES,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
    classify_labels,
    sign_values,
)

BANC_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
NODE_TABLE = BANC_DIR / "banc_nodes.csv.gz"
CONFIG_PATH = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
CONFIG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
OUT_JSON = PROJECT_ROOT / "reports" / "PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.json"


def _primary_policies() -> tuple[SignPolicy, WeightPolicy]:
    sign = SignPolicy.from_config(CONFIG["transmitter_sign_policy"])
    weight = WeightPolicy.from_config(CONFIG["weight_policy"]["primary"])
    return sign, weight


def _sensitivity_weights() -> dict[str, WeightPolicy]:
    return {
        entry["name"]: WeightPolicy.from_config(entry["parameters"])
        for entry in CONFIG["weight_policy"]["sensitivity"]
    }


def _summarise_weight(weights: np.ndarray, counts: np.ndarray) -> dict:
    nonzero = weights[weights > 0]
    if nonzero.size == 0:
        return {"edges": 0}
    return {
        "edges": int(nonzero.size),
        "sum_pa": round(float(nonzero.sum(dtype=np.float64)), 4),
        "min_pa": round(float(nonzero.min()), 4),
        "median_pa": round(float(np.median(nonzero)), 4),
        "p99_pa": round(float(np.percentile(nonzero, 99)), 4),
        "max_pa": round(float(nonzero.max()), 4),
        "median_count": round(float(np.median(counts)), 4),
        "p99_count": round(float(np.percentile(counts, 99)), 4),
        "max_count": int(counts.max()),
    }


def _transform_comparison(counts: np.ndarray) -> dict:
    """Shape comparison at unit scale; scale_pa is reported separately."""
    results = {}
    for name in ("linear", "log1p", "power"):
        policy = WeightPolicy(transform=name, exponent=0.75, scale_pa=1.0, cap_pa=None)
        unit = policy.apply(counts)
        results[name] = {
            "median": round(float(np.median(unit)), 4),
            "p99": round(float(np.percentile(unit, 99)), 4),
            "max": round(float(unit.max()), 4),
            "mean": round(float(unit.mean()), 4),
        }
    return results


def _sensitivity_coverage(codes: np.ndarray, signs: np.ndarray, graph) -> dict:
    edge_codes = codes[np.asarray(graph.edge_src, dtype=np.int64)]
    edge_signs = signs[np.asarray(graph.edge_src, dtype=np.int64)]
    weights = np.asarray(graph.edge_weight, dtype=np.int64)
    signed = edge_signs != 0
    by_class = {}
    for code, name in CLASS_NAMES.items():
        mask = edge_codes == code
        by_class[name] = {
            "neurons": int(np.count_nonzero(codes == code)),
            "edges": int(np.count_nonzero(mask)),
            "synapses": int(weights[mask].sum()),
        }
    return {
        "signed_edges": int(np.count_nonzero(signed)),
        "signed_synapses": int(weights[signed].sum()),
        "excluded_edges": int(signed.size - np.count_nonzero(signed)),
        "excluded_synapses": int(weights[~signed].sum()),
        "signed_edge_share": round(
            float(np.count_nonzero(signed)) / max(1, signed.size), 6
        ),
        "signed_synapse_share": round(
            float(weights[signed].sum()) / max(1, int(weights.sum())), 6
        ),
        "by_class": by_class,
    }


def main() -> int:
    started = time.perf_counter()
    nodes = pd.read_csv(NODE_TABLE)
    sign_policy, weight_policy = _primary_policies()
    sensitivity_policies = _sensitivity_weights()
    fallback_policy = SignPolicy(
        verified_excitatory=sign_policy.verified_excitatory,
        verified_inhibitory=sign_policy.verified_inhibitory,
        modulators=sign_policy.modulators,
        conflict_policy=sign_policy.conflict_policy,
        modulator_only_policy=sign_policy.modulator_only_policy,
        predicted_fallback=True,
        unknown_edge_policy=sign_policy.unknown_edge_policy,
    )

    thresholds = {}
    for threshold in CONFIG["graphs"]["thresholds"]:
        path = BANC_DIR / f"banc_graph_t{threshold}.npz"
        load_started = time.perf_counter()
        graph = BancConnectome.load(path)
        load_s = time.perf_counter() - load_started
        policy_started = time.perf_counter()
        policy = build_synapse_policy(graph, nodes, sign_policy, weight_policy)
        build_s = time.perf_counter() - policy_started
        counts = np.asarray(graph.edge_weight)
        uncapped = WeightPolicy(
            transform=weight_policy.transform,
            exponent=weight_policy.exponent,
            scale_pa=weight_policy.scale_pa,
            cap_pa=None,
        )
        signed_mask = (
            (policy.edge_exc_weight > 0) | (policy.edge_inh_weight > 0)
        )

        primary = policy.describe()
        summary = {
            "artifact": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "artifact_sha256": sha256_file(path),
            "threshold": int(graph.threshold),
            "nodes": int(graph.n_nodes),
            "edges": int(graph.n_edges),
            "synapses": int(graph.n_synapses),
            "isolated_nodes": int(graph.n_isolated),
            "load_seconds": round(load_s, 3),
            "policy_build_seconds": round(build_s, 3),
            "memory_bytes": {
                "policy_arrays": int(policy.memory_bytes),
                "graph_edge_arrays": int(
                    counts.nbytes
                    + graph.edge_src.nbytes
                    + graph.edge_dst.nbytes
                    + graph.in_edge_idx.nbytes
                ),
            },
            "primary_policy": primary,
            "class_partition_check": {
                "edges": int(
                    sum(
                        entry["edges"]
                        for entry in primary["coverage"]["by_class"].values()
                    )
                ),
                "synapses": int(
                    sum(
                        entry["synapses"]
                        for entry in primary["coverage"]["by_class"].values()
                    )
                ),
                "matches_graph": bool(
                    sum(
                        entry["edges"]
                        for entry in primary["coverage"]["by_class"].values()
                    )
                    == graph.n_edges
                    and sum(
                        entry["synapses"]
                        for entry in primary["coverage"]["by_class"].values()
                    )
                    == graph.n_synapses
                ),
            },
            "signed_weight_summary": {
                "excitatory": _summarise_weight(policy.edge_exc_weight, counts),
                "inhibitory": _summarise_weight(policy.edge_inh_weight, counts),
            },
            "cap_saturation": {
                "edges_at_cap": (
                    int(
                        np.count_nonzero(
                            policy.edge_exc_weight
                            == np.float32(weight_policy.cap_pa)
                        )
                        + np.count_nonzero(
                            policy.edge_inh_weight
                            == np.float32(weight_policy.cap_pa)
                        )
                    )
                    if weight_policy.cap_pa is not None
                    else 0
                ),
                "uncapped_policy_max_pa": round(
                    float(uncapped.apply(counts[signed_mask]).max(initial=0.0)),
                    4,
                ),
            },
            "transform_comparison_unit_scale": _transform_comparison(counts),
            "weight_sensitivity": {
                name: {
                    "parameters": wp.describe(),
                    "excitatory_edges": int(np.count_nonzero(policy.edge_exc_weight > 0)),
                    "excitatory_sum_pa": round(
                        float(
                            wp.apply(counts[policy.edge_exc_weight > 0]).sum(
                                dtype=np.float64
                            )
                        ),
                        4,
                    ),
                    "uncapped_max_pa": round(
                        float(
                            wp.apply(counts[policy.edge_exc_weight > 0]).max(
                                initial=0.0
                            )
                        ),
                        4,
                    ),
                }
                for name, wp in sensitivity_policies.items()
            },
        }

        fallback_codes = classify_labels(
            nodes["neurotransmitter_verified"],
            nodes["neurotransmitter_predicted"],
            fallback_policy,
        )
        fallback_signs = sign_values(fallback_codes, fallback_policy)
        summary["predicted_fallback_sensitivity"] = _sensitivity_coverage(
            fallback_codes, fallback_signs, graph
        )
        summary["predicted_fallback_sensitivity"]["policy"] = fallback_policy.describe()

        thresholds[f"t{threshold}"] = summary
        print(
            f"t{threshold}: {graph.n_nodes:,} nodes, {graph.n_edges:,} edges, "
            f"{graph.n_synapses:,} synapses, signed "
            f"{policy.coverage['signed_edges']:,} edges "
            f"({policy.coverage['signed_edge_share']:.4%}), "
            f"loaded in {load_s:.1f}s, policy in {build_s:.1f}s",
            flush=True,
        )
        del policy, graph, counts

    payload = {
        "phase": "4G.2",
        "title": "BANC transmitter-sign and edge-weight policy audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "inputs": {
            "node_table": str(NODE_TABLE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "node_table_sha256": sha256_file(NODE_TABLE),
            "config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "config_sha256": sha256_file(CONFIG_PATH),
            "annotation_columns": [
                "neurotransmitter_verified",
                "neurotransmitter_predicted",
                "neurotransmitter_score",
            ],
        },
        "sign_policy": sign_policy.describe(),
        "weight_policy": weight_policy.describe(),
        "weight_sensitivity_policies": {
            name: wp.describe() for name, wp in sensitivity_policies.items()
        },
        "unknown_edge_strategies": CONFIG["unknown_edge_strategies"],
        "thresholds": thresholds,
        "total_audit_seconds": round(time.perf_counter() - started, 3),
        "interpretation": (
            "Signed edges are modelling priors derived from verified presynaptic "
            "transmitter labels. Synapse counts are structural measurements, not "
            "conductances, and excluded edges are structural connections the "
            "declared policy cannot sign."
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {OUT_JSON} in {payload['total_audit_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
