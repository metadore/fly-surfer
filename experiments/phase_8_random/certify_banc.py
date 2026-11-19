"""Build and certify one Condition C null graph at BANC scale.

SCIENTIFIC STATUS
    This runner produces a randomized structural control. It does not run an
    episode, train anything, or touch the original BANC artifacts. A passing
    certificate is evidence about the *construction*, not about biology.

MEMORY POLICY
    The Phase 8 campaign gate (§9.3, 4 GB free) applies to campaign execution
    and is not touched here. This read-only construction instead uses its own
    measured preflight: the required free memory is estimated from the graph
    size with a declared safety factor, and the run aborts before allocating
    if that estimate is not met. Aborting records a `blocked` result; it never
    produces a certificate.

USAGE
    python -m experiments.phase_8_random.certify_banc --campaign-seed 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from brain.banc_graph import PROJECT_ROOT, BancConnectome
from brain.banc_synapse_policy import SignPolicy, WeightPolicy, build_synapse_policy

from . import certification as cert
from .target_exchange import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_PLATEAU_INTERVAL,
    MemoryTrace,
    graph_digest,
    rewire_target_exchange,
    validate_randomization,
)

BANC_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
GRAPH_PATH = BANC_DIR / "banc_graph_t5.npz"
NODE_TABLE = BANC_DIR / "banc_nodes.csv.gz"
SOURCE_MANIFEST = BANC_DIR / "banc_manifest.json"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
PROTOCOL_PATH = PROJECT_ROOT / cert.PROTOCOL_PATH
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "datasets" / "processed" / "banc_v888_random"
DEFAULT_RESULTS_ROOT = PROJECT_ROOT / "experiments" / "results" / "phase_8_random"
POLICY_COLUMNS = (
    "banc_888_id",
    "neurotransmitter_verified",
    "neurotransmitter_predicted",
)


def estimate_requirement_mb(n_nodes: int, n_edges: int) -> dict[str, float]:
    """Declared estimate of this construction's peak working set.

    Deliberately crude and documented: integer arrays for the graph and swap
    copies, a Python int set for duplicate rejection (~96 B/edge), transient
    sorted keys at each checkpoint and in validation, and two signed policies.
    """
    m = float(n_edges)
    n = float(n_nodes)
    parts = {
        "graph_arrays_mb": (m * 16.0 + n * 16.0) / 2**20,
        "swap_copies_mb": (m * 24.0) / 2**20,
        "duplicate_key_set_mb": (m * 96.0) / 2**20,
        "checkpoint_transient_mb": (m * 24.0) / 2**20,
        "validation_transient_mb": (m * 48.0 + n * 24.0) / 2**20,
        "signed_policies_mb": (m * 8.0 + n * 24.0) / 2**20,
    }
    total = float(sum(parts.values()))
    parts["total_mb"] = total
    return parts


def memory_preflight(
    n_nodes: int,
    n_edges: int,
    *,
    safety_factor: float = 1.5,
    floor_gb: float = 0.75,
) -> dict[str, Any]:
    estimate = estimate_requirement_mb(n_nodes, n_edges)
    required_gb = max(float(floor_gb), estimate["total_mb"] * float(safety_factor) / 1024.0)
    available_gb = None
    try:
        import psutil

        available_gb = round(float(psutil.virtual_memory().available) / 1024.0**3, 3)
    except ImportError:  # pragma: no cover
        pass
    allowed = (
        available_gb is not None
        and float(available_gb) >= required_gb
        and float(safety_factor) > 0
    )
    return {
        "estimate": {key: round(value, 3) for key, value in estimate.items()},
        "safety_factor": float(safety_factor),
        "floor_gb": float(floor_gb),
        "available_gb": available_gb,
        "required_gb": round(required_gb, 3),
        "allowed": bool(allowed),
        "note": (
            "construction-specific preflight; the 4 GB campaign gate of REV4 "
            "§9.3 is unchanged and no campaign step is run"
        ),
    }


def _load_policies():
    import yaml

    payload = yaml.safe_load(POLICY_CONFIG.read_text(encoding="utf-8"))
    sign = SignPolicy.from_config(payload["transmitter_sign_policy"])
    weight = WeightPolicy.from_config(payload["weight_policy"]["primary"])
    return sign, weight


def _load_node_table():
    import pandas as pd

    return pd.read_csv(NODE_TABLE, usecols=list(POLICY_COLUMNS))


def _verify_source_identities(graph_sha: str, nodes_sha: str) -> dict:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    graph_entry = manifest["outputs"]["graph_threshold_5"]
    nodes_entry = manifest["outputs"]["nodes"]
    report = {
        "graph": {
            "expected_sha256": graph_entry["sha256"],
            "actual_sha256": graph_sha,
            "match": graph_entry["sha256"] == graph_sha,
        },
        "nodes": {
            "expected_sha256": nodes_entry["sha256"],
            "actual_sha256": nodes_sha,
            "match": nodes_entry["sha256"] == nodes_sha,
        },
        "manifest_path": SOURCE_MANIFEST.relative_to(PROJECT_ROOT).as_posix(),
    }
    report["pass"] = bool(report["graph"]["match"] and report["nodes"]["match"])
    return report


def _policy_summary(policy) -> dict:
    coverage = dict(policy.coverage)
    return {
        "sign_policy": {
            "source": "neurotransmitter_verified",
            "predicted_fallback": bool(policy.sign_policy.predicted_fallback),
            "unknown_edge_policy": policy.sign_policy.unknown_edge_policy,
        },
        "weight_policy": {
            "transform": policy.weight_policy.transform,
            "exponent": float(policy.weight_policy.exponent),
            "scale_pa": float(policy.weight_policy.scale_pa),
            "cap_pa": policy.weight_policy.cap_pa,
        },
        "coverage": {
            key: coverage.get(key)
            for key in (
                "total_neurons",
                "total_edges",
                "total_synapses",
                "signed_edges",
                "signed_synapses",
                "excluded_edges",
            )
        },
        "config_path": POLICY_CONFIG.relative_to(PROJECT_ROOT).as_posix(),
        "config_sha256": cert.sha256_file(POLICY_CONFIG),
    }


def _compare_builds(first, second) -> dict:
    fields = ("edge_src", "edge_dst", "edge_weight", "out_indptr", "in_indptr")
    equal = {
        name: bool(
            np.array_equal(
                np.asarray(getattr(first, name)), np.asarray(getattr(second, name))
            )
            and np.asarray(getattr(first, name)).dtype
            == np.asarray(getattr(second, name)).dtype
        )
        for name in fields
    }
    digest_first = graph_digest(first)
    digest_second = graph_digest(second)
    return {
        "fields_compared": list(fields),
        "fields_equal": equal,
        "first_build_digest": digest_first,
        "second_build_digest": digest_second,
        "byte_identical": bool(all(equal.values()) and digest_first == digest_second),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and certify the Phase 8 Condition C null graph."
    )
    parser.add_argument("--campaign-seed", type=int, required=True)
    parser.add_argument(
        "--master-seed",
        type=int,
        default=None,
        help="defaults to master_seed from configs/phase_8/campaign.yaml",
    )
    parser.add_argument("--swaps-per-edge", type=float, default=10.0)
    parser.add_argument(
        "--plateau-interval", type=int, default=DEFAULT_PLATEAU_INTERVAL
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--safety-factor", type=float, default=1.5)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    return parser


def _default_master_seed() -> int:
    import yaml

    payload = yaml.safe_load(
        (PROJECT_ROOT / "configs" / "phase_8" / "campaign.yaml").read_text(
            encoding="utf-8"
        )
    )
    return int(payload["master_seed"])


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    master_seed = (
        int(args.master_seed) if args.master_seed is not None else _default_master_seed()
    )

    from experiments.phase_8.seeds import seed_plan

    structure_seed = int(seed_plan(master_seed, "C", int(args.campaign_seed))["structure"])
    results_root = Path(args.results_root)
    results_root.mkdir(parents=True, exist_ok=True)
    result_path = results_root / f"certification_seed_{int(args.campaign_seed)}.json"

    for required in (GRAPH_PATH, NODE_TABLE, SOURCE_MANIFEST, POLICY_CONFIG, PROTOCOL_PATH):
        if not required.is_file():
            payload = {
                "status": "input_missing",
                "missing": required.as_posix(),
                "certificate_written": False,
            }
            cert.write_json_atomic(result_path, payload)
            print(f"input missing: {required}")
            return 4

    original_identity = cert.file_identity(GRAPH_PATH, root=PROJECT_ROOT)
    protocol_identity = cert.file_identity(PROTOCOL_PATH, root=PROJECT_ROOT)
    nodes_identity = cert.file_identity(NODE_TABLE, root=PROJECT_ROOT)
    source_check = _verify_source_identities(
        original_identity["sha256"], nodes_identity["sha256"]
    )
    if not source_check["pass"]:
        cert.write_json_atomic(
            result_path,
            {
                "status": "source_hash_mismatch",
                "source_check": source_check,
                "certificate_written": False,
            },
        )
        print("source hash mismatch against datasets/processed/banc_v888/banc_manifest.json")
        return 4
    if protocol_identity["sha256"] != cert.EXPECTED_PROTOCOL_SHA256:
        cert.write_json_atomic(
            result_path,
            {
                "status": "protocol_hash_mismatch",
                "protocol": protocol_identity,
                "expected": cert.EXPECTED_PROTOCOL_SHA256,
                "certificate_written": False,
            },
        )
        print("REV4 protocol hash does not match the frozen value")
        return 4

    graph = BancConnectome.load(GRAPH_PATH)
    preflight = memory_preflight(
        graph.n_nodes, graph.n_edges, safety_factor=float(args.safety_factor)
    )
    if not preflight["allowed"]:
        cert.write_json_atomic(
            result_path,
            {
                "status": "blocked_insufficient_memory",
                "campaign_seed": int(args.campaign_seed),
                "structure_seed": structure_seed,
                "preflight": preflight,
                "certificate_written": False,
            },
        )
        print(
            "blocked: free memory "
            f"{preflight['available_gb']} GB < required {preflight['required_gb']} GB"
        )
        return 2

    target_dir = Path(args.output_root) / f"seed_{int(args.campaign_seed)}"
    if target_dir.exists() and any(target_dir.iterdir()):
        cert.write_json_atomic(
            result_path,
            {
                "status": "refused_existing_output",
                "namespace": target_dir.as_posix(),
                "certificate_written": False,
            },
        )
        print(f"refusing to overwrite existing output: {target_dir}")
        return 5
    namespace = cert.OutputNamespace(target_dir)

    trace = MemoryTrace()
    trace.sample("start")

    try:
        first = rewire_target_exchange(
            graph,
            seed=structure_seed,
            swaps_per_edge=float(args.swaps_per_edge),
            max_attempts=args.max_attempts,
            plateau_interval=int(args.plateau_interval),
            batch_size=int(args.batch_size),
        )
        trace.sample("first_construction")
        second = rewire_target_exchange(
            graph,
            seed=structure_seed,
            swaps_per_edge=float(args.swaps_per_edge),
            max_attempts=args.max_attempts,
            plateau_interval=int(args.plateau_interval),
            batch_size=int(args.batch_size),
        )
        trace.sample("second_construction")
        reproducibility = _compare_builds(first.graph, second.graph)
        del second
        trace.sample("second_build_released")

        sign_policy, weight_policy = _load_policies()
        node_table = _load_node_table()
        policy_original = build_synapse_policy(
            graph, node_table, sign_policy, weight_policy
        )
        policy_new = build_synapse_policy(
            first.graph, node_table, sign_policy, weight_policy
        )
        del node_table
        trace.sample("policies_built")

        report = validate_randomization(
            graph,
            first,
            policy_original=policy_original,
            policy_new=policy_new,
            reference_digest=reproducibility["second_build_digest"],
            master_seed=master_seed,
            campaign_seed=int(args.campaign_seed),
        )
        trace.sample("validation_finished")
    except Exception as error:  # pragma: no cover - defensive, evidence preserved
        namespace.fail(
            "exception",
            {
                "error": repr(error),
                "campaign_seed": int(args.campaign_seed),
                "structure_seed": structure_seed,
                "report": locals().get("report"),
            },
        )
        cert.write_json_atomic(
            result_path,
            {
                "status": "exception",
                "error": repr(error),
                "certificate_written": False,
                "namespace": namespace.root.as_posix(),
            },
        )
        raise

    if not report["passed"]:
        namespace.fail(
            "certification_gates_failed",
            {
                "failures": report["failures"],
                "gates": report["gates"],
                "summary": report["summary"],
            },
        )
        cert.write_json_atomic(
            result_path,
            {
                "status": "certification_failed",
                "campaign_seed": int(args.campaign_seed),
                "structure_seed": structure_seed,
                "failures": report["failures"],
                "gates": report["gates"],
                "summary": report["summary"],
                "certificate_written": False,
            },
        )
        print(f"certification failed: {report['failures']}")
        return 3

    graph_name = f"banc_graph_random_t5_seed_{int(args.campaign_seed)}.npz"
    output_path = namespace.path(graph_name)
    first.graph.save(output_path)
    output_identity = cert.file_identity(output_path, root=PROJECT_ROOT)
    trace.sample("graph_written")

    runtime = time.perf_counter() - started
    memory = {
        "construction": first.memory,
        "runner": trace.summary(),
        "preflight": preflight,
    }
    certificate = cert.build_certificate(
        original_identity=original_identity,
        output_identity=output_identity,
        protocol_identity=protocol_identity,
        report=report,
        master_seed=master_seed,
        campaign_seed=int(args.campaign_seed),
        structure_seed=structure_seed,
        swaps_per_edge=float(args.swaps_per_edge),
        construction={
            "candidate_block": first.summary()["algorithm"]["candidate_block"],
            "batch_size": int(args.batch_size),
            "plateau_interval": int(args.plateau_interval),
            "max_attempts": int(first.max_attempts),
            "graph_npz_name": graph_name,
        },
        reproducibility=reproducibility,
        memory=memory,
        runtime_seconds=runtime,
        policy_summary=_policy_summary(policy_original),
    )
    certificate_path, certificate_sha = cert.write_certificate(namespace, certificate)
    manifest_path, manifest_sha = cert.write_manifest(
        namespace,
        certificate=certificate,
        certificate_identity={
            "path": certificate_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": certificate_sha,
        },
        graph_identity=output_identity,
        extra={
            "source_check": source_check,
            "preflight": preflight,
            "cache_policy": "graph artifacts are reproducible from the seed; never edit",
        },
    )
    namespace.complete(
        required=(output_path, certificate_path, manifest_path)
    )

    # Prove the certification path accepts what was just written.
    loaded_graph, loaded_certificate = cert.load_certified_graph(certificate_path)
    if graph_digest(loaded_graph) != certificate["output_graph"]["graph_digest"]:
        raise cert.CertificationError("post-write verification failed")
    structure = cert.structure_record(
        loaded_certificate,
        certificate_path=certificate_path,
        certificate_sha256=certificate_sha,
    )

    summary_payload = {
        "status": "certified",
        "campaign_seed": int(args.campaign_seed),
        "master_seed": master_seed,
        "structure_seed": structure_seed,
        "protocol": protocol_identity,
        "original_graph": original_identity,
        "output_graph": output_identity,
        "certificate": {
            "path": certificate_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": certificate_sha,
        },
        "manifest": {
            "path": manifest_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": manifest_sha,
        },
        "gates": report["gates"],
        "failures": report["failures"],
        "reproducibility": reproducibility,
        "integrity": report["integrity"],
        "summary": report["summary"],
        "memory": memory,
        "runtime_seconds": round(runtime, 3),
        "structure_record": structure,
        "certificate_written": True,
    }
    cert.write_json_atomic(result_path, summary_payload)
    print(
        "certified: "
        f"seed={int(args.campaign_seed)} accepted={first.accepted} "
        f"jaccard={report['gates']['R5']['jaccard']} "
        f"fraction_rewired={report['gates']['R4']['fraction_rewired']} "
        f"peak_rss_mb={memory['runner']['peak_rss_mb']} "
        f"runtime_s={runtime:.1f}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
