"""Campaign-level verification for the Phase 8 Condition C seed set.

One certificate guarantees one graph. This module checks the *set*: that every
required seed has its own certified namespace, that the identities are distinct,
that a rebuild of each seed reproduces the certified digest, that seed 1 is
unchanged, and that the Condition C loader accepts each record and refuses an
uncertified one. It never certifies a graph itself and never modifies artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from experiments.phase_8.seeds import seed_plan
from experiments.phase_8_random import certification as cert
from experiments.phase_8_random.target_exchange import (
    graph_digest,
    rewire_target_exchange,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_GRAPH = PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_graph_t5.npz"
OUTPUT_ROOT = PROJECT_ROOT / "datasets" / "processed" / "banc_v888_random"
RESULTS_ROOT = PROJECT_ROOT / "experiments" / "results" / "phase_8_random"
CAMPAIGN_CONFIG = PROJECT_ROOT / "configs" / "phase_8" / "campaign.yaml"
SUMMARY_NAME = "campaign_seed_summary.json"

REQUIRED_SEEDS = tuple(range(1, 17))

#: Seed 1 identities recorded when that graph was certified. They are the
#: anchor for "seed 1 remains unchanged"; every other seed is compared to its
#: own certificate instead.
SEED_1_FROZEN = {
    "graph_sha256": "d3644a70f36f3f962ed8a2a9b3157915320f1107ff511b431ed3a3dda4d8f768",
    "certificate_sha256": "9873f4f17b6c7d18cc1ff25cb4f56e62550047cde88b5c7be11b3b77c60b7da3",
    "manifest_sha256": "d85572a41d0343751234788aad9e815a449174cc9e6eda21514c6da80c0daea4",
    "results_sha256": "956580dc28430e3f2d476c322088de01b0abebd1303987b82e75bc39c4ae53e2",
    "graph_digest": "e75c6ad78e5e55daa34fa7a58dc016d1aba3c9b017237ba03ab3ec8e66d5aa24",
}


def master_seed() -> int:
    payload = yaml.safe_load(CAMPAIGN_CONFIG.read_text(encoding="utf-8"))
    return int(payload["master_seed"])


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _paths(seed: int) -> dict[str, Path]:
    directory = OUTPUT_ROOT / f"seed_{seed}"
    return {
        "directory": directory,
        "graph": directory / "banc_graph_random_t5_seed_1.npz"
        if seed == 1
        else directory / f"banc_graph_random_t5_seed_{seed}.npz",
        "certificate": directory / cert.CERTIFICATE_NAME,
        "manifest": directory / cert.MANIFEST_NAME,
        "results": RESULTS_ROOT / f"certification_seed_{seed}.json",
        "marker": directory / cert.MARKER_NAME,
    }


def _gates(record: Mapping[str, Any]) -> Mapping[str, Any]:
    return record["randomization_quality"]["gates"]


def _gate(record: Mapping[str, Any], name: str) -> Any:
    return _gates(record)[name]


def _invariant_fields(record: Mapping[str, Any], gates: Mapping[str, Any], graph) -> dict:
    return {
        "nodes": int(graph.n_nodes),
        "edges": int(graph.n_edges),
        "attempted": int(gates["R1"]["swaps_attempted"]),
        "accepted": int(gates["R2"]["swaps_accepted"]),
        "target_accepted": int(gates["R2"]["target_accepted"]),
        "rejected": dict(gates["R3"]["swaps_rejected"]),
        "acceptance_rate": float(gates["R3"]["acceptance_rate"]),
        "fraction_rewired": float(gates["R4"]["fraction_rewired"]),
        "jaccard": float(gates["R5"]["jaccard"]),
        "intersection": int(gates["R5"]["intersection"]),
        "out_degree_max_change": int(gates["R6"]["max_abs_out_degree_change"]),
        "in_degree_max_change": int(gates["R7"]["max_abs_in_degree_change"]),
        "signed_edges": int(gates["R8"]["signed_edges_new"]),
        "signed_synapses": int(gates["R8"]["signed_synapses_new"]),
        "unsigned_edges": int(gates["R8"]["unsigned_edges_new"]),
        "sign_per_node_equal": bool(gates["R8"]["per_node_signs_equal"]),
        "sign_codes_per_node_equal": bool(gates["R8"]["per_node_codes_equal"]),
        "sign_per_edge_reordering_equal": bool(
            gates["R8"]["per_edge_sign_reordering_equal"]
        ),
        "weight_multiset_equal": bool(gates["R9"]["multiset_equal"]),
        "weight_sum": int(gates["R9"]["synapse_sum"]),
        "weight_min": int(gates["R9"]["min"]),
        "weight_max": int(gates["R9"]["max"]),
        "r9b_source_weight_multiset_equal": bool(
            gates["R9b"]["per_source_weight_multiset_equal"]
        ),
        "r9b_out_degree_profile_equal": bool(gates["R9b"]["out_degree_profile_equal"]),
        "duplicate_pairs": int(gates["R10"]["duplicate_pairs"]),
        "self_edges": int(gates["R11"]["self_edges"]),
        "csr_invariants": bool(gates["R12"]["csr_invariants_pass"]),
        "r13_active_mean": float(gates["R13"]["mean_out_neighbour_jaccard"]),
        "r13_all_nodes": float(gates["R13"]["mean_out_neighbour_jaccard_all_nodes"]),
        "r13_active_nodes": int(gates["R13"]["active_nodes"]),
        "r13_isolated_both": int(gates["R13"]["isolated_in_both"]),
        "r14_tail_samples": int(gates["R14"]["tail_samples"]),
        "r14_max_abs_change": float(gates["R14"]["max_abs_change"]),
        "r14_final_jaccard": float(gates["R14"]["final_jaccard"]),
        "components_before": int(gates["R15"]["before"]["n_components"]),
        "components_after": int(gates["R15"]["after"]["n_components"]),
        "largest_component_before": int(gates["R15"]["before"]["largest_component"]),
        "largest_component_after": int(gates["R15"]["after"]["largest_component"]),
        "reciprocity_before": float(gates["R16"]["reciprocity_before"]),
        "reciprocity_after": float(gates["R16"]["reciprocity_after"]),
        "assortativity_before": float(gates["R16"]["degree_assortativity_before"]),
        "assortativity_after": float(gates["R16"]["degree_assortativity_after"]),
        "r17_byte_identical": gates["R17"]["graph_digest"]
        == gates["R17"]["reference_digest"],
        "r18_derivation_verified": bool(gates["R18"]["derivation_verified"]),
        "r18_derived_seed": gates["R18"]["derived_structure_seed"],
        "r18_seed_used": gates["R18"]["seed_used"],
        "r18_entropy": gates["R18"]["entropy"],
        "structure_seed": int(record["seed"]),
        "graph_digest": record["graph_digest"],
        "graph_sha256": record["graph_sha256"],
        "certificate_sha256": record["certificate_sha256"],
        "protocol_sha256": record["protocol_sha256"],
        "construction": record["construction"],
        "u18_status": record["u18_status"],
    }


def load_seed(
    seed: int,
    *,
    original=None,
    regenerate: bool = False,
    previous: Mapping[str, Any] | None = None,
) -> dict:
    paths = _paths(seed)
    entry: dict[str, Any] = {
        "seed": int(seed),
        "paths": {name: path.as_posix() for name, path in paths.items()},
    }
    missing = [
        name
        for name in ("certificate", "manifest", "results")
        if not paths[name].is_file()
    ]
    if missing:
        entry["status"] = "missing"
        entry["missing"] = missing
        return entry
    entry["marker_present"] = paths["marker"].exists()
    try:
        graph, record = cert.load_structure(paths["certificate"])
    except cert.CertificationError as error:
        entry["status"] = "refused"
        entry["reason"] = str(error)
        return entry

    entry.update(
        _invariant_fields(
            record, _read_json(paths["certificate"])["report"]["gates"], graph
        )
    )
    entry["mandatory_gates"] = {
        name: bool(_gate(record, name).get("pass")) for name in cert.MANDATORY_GATES
    }
    results = _read_json(paths["results"])
    entry["results_status"] = results.get("status")
    entry["runtime_seconds"] = results.get("runtime_seconds")
    memory_raw = results.get("memory") or {}

    def _trim(name: str) -> dict:
        payload = memory_raw.get(name) or {}
        return {
            key: payload[key]
            for key in (
                "peak_rss_mb",
                "min_available_gb",
                "available_gb",
                "floor_gb",
                "allowed",
            )
            if key in payload
        }

    entry["memory"] = {
        name: _trim(name) for name in ("construction", "runner", "preflight")
    }
    entry["reproducibility"] = results.get("reproducibility")
    manifest = _read_json(paths["manifest"])
    entry["provenance"] = {
        "manifest_sha256": cert.sha256_file(paths["manifest"]),
        "results_sha256": cert.sha256_file(paths["results"]),
        "created_at": manifest.get("created_at"),
        "source_check_passed": bool(
            (manifest.get("source_check") or {}).get("pass", False)
        ),
        "protocol_sha256": (manifest.get("protocol") or {}).get("sha256"),
        "declared_structure_seed": (manifest.get("seed") or {}).get("structure_seed"),
        "declared_campaign_seed": (manifest.get("seed") or {}).get("campaign_seed"),
    }
    certified_now = (
        entry["results_status"] == "certified"
        and all(entry["mandatory_gates"].values())
        and not entry["marker_present"]
    )
    entry["status"] = "certified" if certified_now else "failed"
    if entry["status"] != "certified":
        entry["failures"] = [
            name for name, ok in entry["mandatory_gates"].items() if not ok
        ]
    del graph

    if regenerate and entry["status"] == "certified":
        if original is None:
            from brain.banc_graph import BancConnectome

            original = BancConnectome.load(ORIGINAL_GRAPH)
        rebuilt = rewire_target_exchange(
            original,
            seed=int(entry["structure_seed"]),
            swaps_per_edge=10.0,
        )
        entry["regenerated_digest"] = graph_digest(rebuilt.graph)
        entry["regenerated_matches"] = (
            entry["regenerated_digest"] == entry["graph_digest"]
        )
        del rebuilt
    elif previous and entry["status"] == "certified":
        # A rebuild is expensive. A result already produced for the same
        # immutable certificate may be carried forward, but only after the
        # graph and certificate hashes are shown to be the ones it was
        # computed against.
        if (
            previous.get("graph_sha256") == entry["graph_sha256"]
            and previous.get("certificate_sha256") == entry["certificate_sha256"]
            and "regenerated_matches" in previous
        ):
            entry["regenerated_digest"] = previous.get("regenerated_digest")
            entry["regenerated_matches"] = previous["regenerated_matches"]
            entry["regenerated_from_previous_summary"] = True
    return entry


def _unique(entries: Iterable[dict], field: str) -> int:
    return len({entry[field] for entry in entries})


def cross_seed_checks(entries: list[dict]) -> dict:
    certified = [entry for entry in entries if entry["status"] == "certified"]
    by_seed = {entry["seed"]: entry for entry in entries}
    seed_1 = by_seed.get(1)
    seed_1_unchanged = bool(
        seed_1
        and seed_1.get("status") == "certified"
        and seed_1["graph_sha256"] == SEED_1_FROZEN["graph_sha256"]
        and seed_1["certificate_sha256"] == SEED_1_FROZEN["certificate_sha256"]
        and seed_1["graph_digest"] == SEED_1_FROZEN["graph_digest"]
        and seed_1["provenance"]["manifest_sha256"] == SEED_1_FROZEN["manifest_sha256"]
        and seed_1["provenance"]["results_sha256"] == SEED_1_FROZEN["results_sha256"]
    )

    def distinct(field: str) -> bool:
        return _unique(certified, field) == len(certified)

    invariants = {
        "node_counts": sorted({entry["nodes"] for entry in certified}),
        "edge_counts": sorted({entry["edges"] for entry in certified}),
        "accepted_targets": sorted({entry["accepted"] for entry in certified}),
        "signed_edges_counts": sorted({entry["signed_edges"] for entry in certified}),
        "signed_synapse_sums": sorted(
            {entry["signed_synapses"] for entry in certified}
        ),
        "weight_sums": sorted({entry["weight_sum"] for entry in certified}),
        "out_degree_changes": sorted(
            {entry["out_degree_max_change"] for entry in certified}
        ),
        "in_degree_changes": sorted(
            {entry["in_degree_max_change"] for entry in certified}
        ),
        "duplicate_counts": sorted(
            {entry["duplicate_pairs"] for entry in certified}
        ),
        "self_edge_counts": sorted({entry["self_edges"] for entry in certified}),
        "csr_invariants": sorted({entry["csr_invariants"] for entry in certified}),
        "unsigned_edge_counts": sorted(
            {entry["unsigned_edges"] for entry in certified}
        ),
        "weight_multiset_equality": sorted(
            {entry["weight_multiset_equal"] for entry in certified}
        ),
        "sign_preservation": sorted(
            {
                entry["sign_per_node_equal"]
                and entry["sign_codes_per_node_equal"]
                and entry["sign_per_edge_reordering_equal"]
                for entry in certified
            }
        ),
        "r9b_equality": sorted(
            {
                entry["r9b_source_weight_multiset_equal"]
                and entry["r9b_out_degree_profile_equal"]
                for entry in certified
            }
        ),
        "r17_byte_identity": sorted(
            {entry["r17_byte_identical"] for entry in certified}
        ),
    }
    single_valued = {
        name: len(values) == 1 for name, values in invariants.items()
    }
    provenance_complete = all(
        entry["provenance"]["source_check_passed"]
        and entry["provenance"]["protocol_sha256"] == cert.EXPECTED_PROTOCOL_SHA256
        and entry["provenance"]["declared_structure_seed"] == entry["structure_seed"]
        and entry["provenance"]["declared_campaign_seed"] == entry["seed"]
        and entry["provenance"]["created_at"]
        for entry in certified
    )
    regeneration = {
        entry["seed"]: entry.get("regenerated_matches")
        for entry in certified
        if "regenerated_matches" in entry
    }
    return {
        "required_seeds": list(REQUIRED_SEEDS),
        "certified_seeds": sorted(entry["seed"] for entry in certified),
        "entries": len(entries),
        "unique_structure_seeds": distinct("structure_seed"),
        "unique_graph_digests": distinct("graph_digest"),
        "unique_graph_sha256": distinct("graph_sha256"),
        "unique_certificate_sha256": distinct("certificate_sha256"),
        "no_duplicate_artifacts": distinct("graph_sha256")
        and distinct("certificate_sha256")
        and distinct("graph_digest"),
        "seed_1_unchanged": seed_1_unchanged,
        "single_valued_invariants": single_valued,
        "all_invariants_shared": all(single_valued.values()),
        "r18_derivation_verified_all": all(
            entry["r18_derivation_verified"] for entry in certified
        ),
        "provenance_complete": provenance_complete,
        "deterministic_regeneration": regeneration,
        "deterministic_regeneration_all": bool(regeneration)
        and all(regeneration.values()),
        "regeneration_attempted": bool(regeneration),
        "original_graph_distinct_from_all": all(
            entry["graph_sha256"] != cert.sha256_file(ORIGINAL_GRAPH)
            for entry in certified
        ),
    }


def condition_c_loader_checks(entries: list[dict]) -> dict:
    from experiments.phase_8.conditions.base import ConditionError, _check_structure

    per_seed: dict[int, bool] = {}
    sample: dict | None = None
    for entry in entries:
        if entry["status"] != "certified":
            continue
        path = Path(entry["paths"]["certificate"])
        certificate = cert.load_certificate(path)
        record = cert.structure_record(
            certificate,
            certificate_path=path,
            certificate_sha256=cert.sha256_file(path),
        )
        cert.verify_structure_record(record)
        _check_structure(record)
        per_seed[entry["seed"]] = (
            record["campaign_seed"] == entry["seed"]
            and record["seed"] == entry["structure_seed"]
            and record["graph_sha256"] == entry["graph_sha256"]
        )
        sample = record

    failed_gate_refused = False
    missing_certificate_refused = False
    if sample is not None:
        bad = json.loads(json.dumps(sample))
        bad["randomization_quality"]["passed"] = False
        try:
            _check_structure(bad)
        except ConditionError:
            failed_gate_refused = True
        without = {key: value for key, value in sample.items() if key != "certificate_path"}
        try:
            cert.verify_structure_record(without)
        except cert.CertificationError:
            missing_certificate_refused = True
    return {
        "per_seed": per_seed,
        "all_seeds_accepted": bool(per_seed) and all(per_seed.values()),
        "failed_gate_record_refused": failed_gate_refused,
        "record_without_certificate_refused": missing_certificate_refused,
        "note": (
            "C and D consume the same structure record; D would need an episode run "
            "to exercise the readout path, which this task does not perform. The "
            "graph file is opened through load_structure and is never modified."
        ),
    }


def compliance(entries: list[dict]) -> dict:
    """Report the REV4 §9.3 memory gate honestly.

    §9.3 lists "BANC-scale graph randomisation" among the operations that may
    not start below 4 GB of free physical memory. Every build in this set ran
    below that figure. The recorded measurement is therefore reported as a
    deviation, not converted into a pass.
    """
    observed: list[float] = []
    preflight_allowed = True
    for entry in entries:
        memory = entry.get("memory") or {}
        for name in ("construction", "runner"):
            value = (memory.get(name) or {}).get("min_available_gb")
            if value is not None:
                observed.append(float(value))
        preflight = memory.get("preflight") or {}
        if preflight.get("allowed") is not True:
            preflight_allowed = False
    lowest = round(min(observed), 3) if observed else None
    highest = round(max(observed), 3) if observed else None
    return {
        "rev4_section": "9.3",
        "gate_gb": 4.0,
        "gate_weakened": False,
        "operations_blocked_below_gate": [
            "BANC-scale graph randomisation",
            "full campaign simulation",
            "training run",
            "memory-intensive test suite",
        ],
        "min_observed_free_gb": lowest,
        "max_observed_free_gb": highest,
        "construction_runs_below_gate": bool(observed) and highest < 4.0,
        "construction_preflight_floor_gb": 0.75,
        "construction_preflight_allowed_all": preflight_allowed,
        "status": "deviation_recorded",
        "note": (
            "Every BANC-scale randomisation in this set started below the REV4 "
            "§9.3 4.00 GB free-memory gate and therefore is a recorded deviation "
            "from the protocol's operational constraint, not a compliant run. The "
            "documented 0.75 GB construction preflight passed for every seed and "
            "no build exhausted memory (peak RSS about 527 MB, lowest observed "
            "free memory 1.63 GB), so the safety rationale held in practice; the "
            "rule itself was not met and is not reported as met."
        ),
    }


def build_summary(
    seeds: Iterable[int] = REQUIRED_SEEDS,
    *,
    regenerate: bool = False,
    previous_summary: Path | None = None,
) -> dict:
    seeds = [int(seed) for seed in seeds]
    original_sha_before = cert.sha256_file(ORIGINAL_GRAPH)
    original = None
    if regenerate:
        from brain.banc_graph import BancConnectome

        original = BancConnectome.load(ORIGINAL_GRAPH)
    previous: dict[int, dict] = {}
    previous_sha = None
    if previous_summary is not None and previous_summary.is_file():
        previous_sha = cert.sha256_file(previous_summary)
        for entry in _read_json(previous_summary).get("seeds", []):
            previous[int(entry["seed"])] = entry
    entries = [
        load_seed(
            seed,
            original=original,
            regenerate=regenerate,
            previous=previous.get(seed),
        )
        for seed in seeds
    ]
    del original
    carried = [
        entry["seed"] for entry in entries if entry.get("regenerated_from_previous_summary")
    ]
    summary = {
        "schema_version": 1,
        "phase": "8",
        "work_package": "G3",
        "artifact": "campaign_seed_set",
        "generated_at": cert.utc_now(),
        "protocol": cert.file_identity(
            PROJECT_ROOT / cert.PROTOCOL_PATH, root=PROJECT_ROOT
        ),
        "original_graph": cert.file_identity(ORIGINAL_GRAPH, root=PROJECT_ROOT),
        "master_seed": master_seed(),
        "required_seeds": list(REQUIRED_SEEDS),
        "seeds": entries,
        "cross_seed": cross_seed_checks(entries),
        "condition_c_loader": condition_c_loader_checks(entries),
        "compliance": compliance(entries),
        "regeneration_provenance": {
            "rebuilt_in_this_run": regenerate,
            "carried_forward_from": previous_summary.as_posix()
            if carried and previous_summary is not None
            else None,
            "carried_forward_summary_sha256": previous_sha if carried else None,
            "seeds_carried_forward": carried,
            "identity_checked": True,
            "note": (
                "A carried-forward result was computed by an earlier run of this "
                "command against the same certificate; it is reused only when the "
                "graph and certificate SHA-256 still match."
            ),
        },
        "original_graph_unchanged_during_summary": (
            cert.sha256_file(ORIGINAL_GRAPH) == original_sha_before
        ),
    }
    return summary


def write_summary(summary: Mapping[str, Any], path: Path = RESULTS_ROOT / SUMMARY_NAME) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _parse_seeds(text: str) -> list[int]:
    if "-" in text:
        start, end = text.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(item) for item in text.split(",") if item]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the Phase 8 Condition C seed set and write the campaign summary."
    )
    parser.add_argument("--seeds", default="1-16")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rebuild every certified seed from the original graph and compare digests",
    )
    parser.add_argument("--output", type=Path, default=RESULTS_ROOT / SUMMARY_NAME)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    summary = build_summary(
        _parse_seeds(args.seeds),
        regenerate=bool(args.regenerate),
        previous_summary=output,
    )
    path = write_summary(summary, output)
    cross = summary["cross_seed"]
    print(
        f"certified={len(cross['certified_seeds'])}/{len(summary['required_seeds'])} "
        f"unique_digests={cross['unique_graph_digests']} "
        f"seed1_unchanged={cross['seed_1_unchanged']} "
        f"loader={summary['condition_c_loader']['all_seeds_accepted']} "
        f"-> {path}"
    )
    failed = [entry["seed"] for entry in summary["seeds"] if entry["status"] != "certified"]
    if failed:
        print(f"not certified: {failed}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


