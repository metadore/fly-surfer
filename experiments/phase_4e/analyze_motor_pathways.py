"""Phase 4E: structural analysis of BANC descending, premotor and motor pathways.

Loads the Phase 4D BANC v888 graph artifacts read-only. Every count is derived
from the existing node table and CSR graphs; this script never rebuilds,
rewrites or merges a graph. Structural connectivity is not physiology.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pyarrow import feather

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import (  # noqa: E402
    BancConnectome,
    DEFAULT_INPUTS,
    OUT_DIR,
    load_metadata,
    motor_by_body_part,
    population_mask,
    sha256_file,
    software_versions,
    verify_manifest,
    write_json,
)

THRESHOLDS = (1, 5, 10)
PRIMARY_THRESHOLD = 5
AUDIT_COMPARISON_THRESHOLD = 1
JUMP_TARGET = "tergotrochanter_extensor_muscle"
FOCUS_EFFECTORS = (
    "front_leg",
    "middle_leg",
    "hind_leg",
    "wing",
    "haltere",
    "abdomen",
    "neck",
)
EXTRA_COLUMNS = ("banc_888_id", "super_cluster", "cluster", "cell_function_detailed")
MAX_PAIR_MATERIALIZATION = 20_000_000
UNKNOWN = "unknown"

AUDIT_JSON = PROJECT_ROOT / "reports" / "PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json"
REPORT_JSON = (
    PROJECT_ROOT / "reports" / "PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.json"
)


# ---------------------------------------------------------------------------
# loading and annotation arrays
# ---------------------------------------------------------------------------


def _with_extra_annotations(nodes: pd.DataFrame, metadata_path: Path) -> pd.DataFrame:
    extra = feather.read_table(Path(metadata_path), columns=list(EXTRA_COLUMNS)).to_pandas()
    extra["_banc_key"] = extra["banc_888_id"].astype("int64")
    extra = extra.drop(columns=["banc_888_id"])
    if extra["_banc_key"].duplicated().any():
        raise ValueError("metadata contains duplicate banc_888_id values")
    frame = nodes.copy()
    frame["_banc_key"] = frame["banc_888_id"].astype("int64")
    frame = frame.merge(
        extra, on="_banc_key", how="left", validate="one_to_one", sort=False
    )
    frame = frame.drop(columns=["_banc_key"])
    if not np.array_equal(
        frame["node_index"].to_numpy(), np.arange(len(frame), dtype=np.int64)
    ):
        raise ValueError("merge changed node ordering")
    return frame


def load_inputs(
    graph_dir: Path = OUT_DIR,
    nodes_path: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[pd.DataFrame, dict[int, BancConnectome], dict, dict]:
    """Load node table, all threshold graphs and the Phase 4D manifest."""
    nodes_path = Path(nodes_path or graph_dir / "banc_nodes.csv.gz")
    manifest_path = Path(manifest_path or graph_dir / "banc_manifest.json")
    nodes = pd.read_csv(nodes_path, dtype={"banc_888_id": str})
    if not np.array_equal(
        nodes["node_index"].to_numpy(), np.arange(len(nodes), dtype=np.int64)
    ):
        raise ValueError("node_table node_index is not 0-based and contiguous")
    nodes = _with_extra_annotations(nodes, DEFAULT_INPUTS["metadata"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = verify_manifest(manifest, PROJECT_ROOT)
    if not verification["pass"]:
        raise RuntimeError(f"manifest verification failed: {verification['failures']}")
    node_ids = nodes["banc_888_id"].astype("int64").to_numpy()
    graphs: dict[int, BancConnectome] = {}
    for threshold in THRESHOLDS:
        graph = BancConnectome.load(Path(graph_dir) / f"banc_graph_t{threshold}.npz")
        if not np.array_equal(graph.root_ids, node_ids):
            raise ValueError(f"threshold {threshold} node order differs from node table")
        graphs[threshold] = graph
    return nodes, graphs, manifest, verification


def _string_array(series: pd.Series) -> np.ndarray:
    return series.fillna("").astype(str).to_numpy()


def _bool_array(series: pd.Series) -> np.ndarray:
    return series.fillna(False).astype(bool).to_numpy()


def annotation_arrays(nodes: pd.DataFrame) -> dict:
    parts = _string_array(nodes["body_part_effector"]).copy()
    parts[parts == ""] = UNKNOWN
    part_names = np.unique(parts)
    part_code = np.searchsorted(part_names, parts).astype(np.int16)
    side = _string_array(nodes["side"])
    side_code = np.where(side == "left", 1, np.where(side == "right", 2, 0)).astype(
        np.int8
    )
    return {
        "banc_ids": nodes["banc_888_id"].astype("int64").to_numpy(),
        "super_class": _string_array(nodes["super_class"]),
        "cell_class": _string_array(nodes["cell_class"]),
        "cell_sub_class": _string_array(nodes["cell_sub_class"]),
        "cell_type": _string_array(nodes["cell_type"]),
        "side": side,
        "side_code": side_code,
        "region": _string_array(nodes["region"]),
        "body_part_effector": parts,
        "part_names": [str(value) for value in part_names],
        "part_code": part_code,
        "peripheral_target_type": _string_array(nodes["peripheral_target_type"]),
        "cell_function": _string_array(nodes["cell_function"]),
        "cell_function_detailed": _string_array(nodes["cell_function_detailed"]),
        "super_cluster": _string_array(nodes["super_cluster"]),
        "cluster": _string_array(nodes["cluster"]),
        "neurotransmitter_predicted": _string_array(nodes["neurotransmitter_predicted"]),
        "neurotransmitter_verified": _string_array(nodes["neurotransmitter_verified"]),
        "proofread": _bool_array(nodes["proofread"]),
        "roughly_proofread": _bool_array(nodes["roughly_proofread"]),
        "status": _string_array(nodes["status"]),
        "is_dn": _bool_array(nodes["is_descending"]),
        "is_motor": _bool_array(nodes["is_motor"]),
        "is_vnc_intrinsic": _bool_array(nodes["is_vnc_intrinsic"]),
        "is_vnc_region": _bool_array(nodes["is_vnc"]),
        "is_jump": _bool_array(nodes["is_tergotrochanter_candidate"]),
    }


def _id_string(index: int, arrays: dict) -> str:
    return str(int(arrays["banc_ids"][index]))


def _top_counts(values: np.ndarray, limit: int = 15) -> dict:
    series = pd.Series(values)
    series = series.replace("", UNKNOWN)
    return {str(key): int(value) for key, value in series.value_counts().head(limit).items()}


def _coverage_block(frame: pd.DataFrame) -> dict:
    return {
        "rows": int(len(frame)),
        "super_class_present": int(frame["super_class"].notna().sum()),
        "cell_class_present": int(frame["cell_class"].notna().sum()),
        "cell_sub_class_present": int(frame["cell_sub_class"].notna().sum()),
        "cell_type_present": int(frame["cell_type"].notna().sum()),
        "side_present": int(frame["side"].notna().sum()),
        "region_present": int(frame["region"].notna().sum()),
        "body_part_effector_present": int(frame["body_part_effector"].notna().sum()),
        "peripheral_target_type_present": int(
            frame["peripheral_target_type"].notna().sum()
        ),
        "proofread_true": int(frame["proofread"].fillna(False).astype(bool).sum()),
        "roughly_proofread_true": int(
            frame["roughly_proofread"].fillna(False).astype(bool).sum()
        ),
        "neurotransmitter_predicted_present": int(
            frame["neurotransmitter_predicted"].notna().sum()
        ),
        "neurotransmitter_verified_present": int(
            frame["neurotransmitter_verified"].notna().sum()
        ),
    }


# ---------------------------------------------------------------------------
# shared statistics
# ---------------------------------------------------------------------------


def _stats(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.int64)
    if values.size == 0:
        return {
            "count": 0,
            "sum": 0,
            "mean": 0.0,
            "median": 0.0,
            "p90": 0.0,
            "p99": 0.0,
            "min": 0,
            "max": 0,
            "zero": 0,
        }
    return {
        "count": int(values.size),
        "sum": int(values.sum()),
        "mean": round(float(values.mean()), 4),
        "median": round(float(np.median(values)), 4),
        "p90": round(float(np.percentile(values, 90)), 4),
        "p99": round(float(np.percentile(values, 99)), 4),
        "min": int(values.min()),
        "max": int(values.max()),
        "zero": int(np.count_nonzero(values == 0)),
    }


def _share(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def _edge_sides(src_side: np.ndarray, dst_side: np.ndarray) -> dict:
    left_left = int(np.count_nonzero((src_side == 1) & (dst_side == 1)))
    left_right = int(np.count_nonzero((src_side == 1) & (dst_side == 2)))
    right_left = int(np.count_nonzero((src_side == 2) & (dst_side == 1)))
    right_right = int(np.count_nonzero((src_side == 2) & (dst_side == 2)))
    same = left_left + right_right
    cross = left_right + right_left
    known = same + cross
    return {
        "left_to_left": left_left,
        "left_to_right": left_right,
        "right_to_left": right_left,
        "right_to_right": right_right,
        "same_side": same,
        "cross_side": cross,
        "same_side_share_of_known": _share(same, known),
        "cross_side_share_of_known": _share(cross, known),
        "missing_side_edges": int(
            np.count_nonzero(
                ((src_side == 0) | (dst_side == 0))
            )
        ),
    }


def _direct_edges(graph: BancConnectome, arrays: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    src, dst, weight = graph.edge_src, graph.edge_dst, graph.edge_weight
    mask = arrays["is_dn"][src] & arrays["is_motor"][dst]
    return src[mask], dst[mask], weight[mask]


def _classify_motor_inputs(
    n_nodes: int,
    arrays: dict,
    src: np.ndarray,
    dst: np.ndarray,
    motor_mask: np.ndarray,
) -> dict:
    side_src = arrays["side_code"][src]
    side_dst = arrays["side_code"]
    left = np.bincount(dst[side_src == 1], minlength=n_nodes).astype(np.int64)
    right = np.bincount(dst[side_src == 2], minlength=n_nodes).astype(np.int64)
    missing = np.bincount(dst[side_src == 0], minlength=n_nodes).astype(np.int64)
    total = left + right + missing
    no_input = motor_mask & (total == 0)
    bilateral = motor_mask & (left > 0) & (right > 0)
    ipsilateral = motor_mask & (
        ((left > 0) & (right == 0) & (side_dst == 1))
        | ((right > 0) & (left == 0) & (side_dst == 2))
    )
    contralateral = motor_mask & (
        ((left > 0) & (right == 0) & (side_dst == 2))
        | ((right > 0) & (left == 0) & (side_dst == 1))
    )
    unknown_mn_side = motor_mask & (side_dst == 0) & ((left + right) > 0)
    unknown_input_only = motor_mask & ((left + right) == 0) & (missing > 0)
    counts = {
        "no_direct_input": int(np.count_nonzero(no_input)),
        "ipsilateral_only": int(np.count_nonzero(ipsilateral)),
        "contralateral_only": int(np.count_nonzero(contralateral)),
        "bilateral": int(np.count_nonzero(bilateral)),
        "known_input_side_unknown_mn_side": int(np.count_nonzero(unknown_mn_side)),
        "unknown_input_side_only": int(np.count_nonzero(unknown_input_only)),
    }
    population = int(np.count_nonzero(motor_mask))
    shares = {key: _share(value, population) for key, value in counts.items()}
    return {
        "counts": counts,
        "shares": shares,
        "with_unknown_side_input": int(
            np.count_nonzero(motor_mask & (missing > 0))
        ),
        "population": population,
    }


# ---------------------------------------------------------------------------
# Part A: populations and VNC discrepancy
# ---------------------------------------------------------------------------


def population_report(nodes: pd.DataFrame, audit: dict) -> dict:
    counts = {
        "total_graph_nodes": int(len(nodes)),
        "descending": int(population_mask(nodes, "descending").sum()),
        "motor": int(population_mask(nodes, "motor").sum()),
        "ascending": int(population_mask(nodes, "ascending").sum()),
        "vnc_intrinsic": int(population_mask(nodes, "vnc_intrinsic").sum()),
        "vnc_region": int(population_mask(nodes, "vnc").sum()),
        "left_motor": int(population_mask(nodes, "left_motor").sum()),
        "right_motor": int(population_mask(nodes, "right_motor").sum()),
        "tergotrochanter_motor_candidates": int(
            population_mask(nodes, "tergotrochanter_motor_candidates").sum()
        ),
    }
    by_part = motor_by_body_part(nodes)
    by_part = by_part.reset_index().to_dict("records")
    motors = nodes[population_mask(nodes, "motor")]
    completeness = {
        "motor_neurons": int(len(motors)),
        "missing_body_part_effector": int(motors["body_part_effector"].isna().sum()),
        "missing_side": int(motors["side"].isna().sum()),
        "missing_cell_type": int(motors["cell_type"].isna().sum()),
        "missing_peripheral_target_type": int(
            motors["peripheral_target_type"].isna().sum()
        ),
        "proofread_true": int(motors["proofread"].fillna(False).astype(bool).sum()),
        "verified_neurotransmitter": int(
            motors["neurotransmitter_verified"].notna().sum()
        ),
    }
    audit_populations = audit.get("D_annotation_quality", {}).get("populations", {})
    comparisons = {}
    for name, expected in (
        ("motor", audit_populations.get("motor", {}).get("rows")),
        ("descending", audit_populations.get("descending", {}).get("rows")),
        ("ascending", audit_populations.get("ascending", {}).get("rows")),
        (
            "vnc_intrinsic",
            audit_populations.get("ventral_nerve_cord_intrinsic", {}).get("rows"),
        ),
    ):
        actual = counts[name]
        comparisons[name] = {
            "phase_4c5_metadata_rows": expected,
            "phase_4e_graph_nodes": actual,
            "match": bool(expected == actual),
            "delta": None if expected is None else actual - int(expected),
        }
    return {
        "counts": counts,
        "motor_by_body_part": by_part,
        "annotation_completeness": completeness,
        "phase_4c5_comparison": comparisons,
    }


def _metadata_bool(value) -> bool:
    """BANC metadata stores proofread flags as ``"TRUE"``/``"FALSE"`` strings."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None:
        return False
    if not isinstance(value, str) and pd.isna(value):
        return False
    return str(value).strip().upper() == "TRUE"


def vnc_intrinsic_discrepancy(meta: pd.DataFrame, nodes: pd.DataFrame) -> dict:
    graph_ids = set(nodes["banc_888_id"].astype("int64").tolist())
    intrinsic = meta[meta["super_class"].eq("ventral_nerve_cord_intrinsic")]
    missing = intrinsic[~intrinsic["banc_888_id"].astype("int64").isin(graph_ids)]
    columns = [
        "banc_888_id",
        "cell_class",
        "cell_sub_class",
        "cell_type",
        "side",
        "region",
        "proofread",
        "roughly_proofread",
        "status",
        "neurotransmitter_predicted",
        "neurotransmitter_verified",
    ]
    records = []
    for row in missing[columns].itertuples(index=False):
        record = {column: getattr(row, column) for column in columns}
        record["banc_888_id"] = str(record["banc_888_id"])
        for value in list(record):
            if record[value] is None:
                continue
            if isinstance(record[value], str):
                continue
            if pd.isna(record[value]):
                record[value] = None
        record["proofread"] = _metadata_bool(row.proofread)
        record["roughly_proofread"] = _metadata_bool(row.roughly_proofread)
        records.append(record)
    proofread_true = sum(1 for record in records if record["proofread"])
    roughly_true = sum(1 for record in records if record["roughly_proofread"])
    return {
        "metadata_rows": int(len(meta)),
        "graph_nodes": int(len(nodes)),
        "metadata_only_rows_total": int(len(meta) - len(nodes)),
        "phase_4c5_vnc_intrinsic": int(len(intrinsic)),
        "phase_4d_graph_vnc_intrinsic": int(
            np.count_nonzero(nodes["is_vnc_intrinsic"].to_numpy(dtype=bool))
        ),
        "missing_count": int(len(missing)),
        "missing_ids": records,
        "missing_proofread_true": int(proofread_true),
        "missing_roughly_proofread_true": int(roughly_true),
        "explanation": (
            "These 16 metadata rows have no endpoint in the exported v2 edgelist "
            "in either direction, so they are not graph nodes. Their annotations "
            "are preserved in the source metadata and were not changed."
        ),
    }


# ---------------------------------------------------------------------------
# Part B: direct descending-to-motor pathways
# ---------------------------------------------------------------------------


def direct_pathway(graph: BancConnectome, arrays: dict) -> dict:
    n = graph.n_nodes
    src, dst, weight = _direct_edges(graph, arrays)
    n_dn = int(np.count_nonzero(arrays["is_dn"]))
    n_motor = int(np.count_nonzero(arrays["is_motor"]))
    out_degree = np.bincount(src, minlength=n).astype(np.int64)
    in_degree = np.bincount(dst, minlength=n).astype(np.int64)
    unique_sources = np.unique(src)
    unique_targets = np.unique(dst)
    target_side = arrays["side_code"][unique_targets]
    side_counts = {
        "left": int(np.count_nonzero(target_side == 1)),
        "right": int(np.count_nonzero(target_side == 2)),
        "missing": int(np.count_nonzero(target_side == 0)),
    }
    source_side = arrays["side_code"][unique_sources]
    source_sides = {
        "left": int(np.count_nonzero(source_side == 1)),
        "right": int(np.count_nonzero(source_side == 2)),
        "missing": int(np.count_nonzero(source_side == 0)),
    }
    edge_sides = _edge_sides(arrays["side_code"][src], arrays["side_code"][dst])

    by_part = []
    for part_code, part_name in enumerate(arrays["part_names"]):
        motor_mask = arrays["is_motor"] & (arrays["part_code"] == part_code)
        population = int(np.count_nonzero(motor_mask))
        if population == 0:
            continue
        edge_mask = arrays["part_code"][dst] == part_code
        part_dst = dst[edge_mask]
        with_input = int(np.unique(part_dst).size)
        part_src = src[edge_mask]
        part_weight = weight[edge_mask]
        categories = _classify_motor_inputs(n, arrays, src, dst, motor_mask)
        by_part.append(
            {
                "body_part_effector": str(part_name),
                "motor_neurons": population,
                "left": int(np.count_nonzero(motor_mask & (arrays["side_code"] == 1))),
                "right": int(np.count_nonzero(motor_mask & (arrays["side_code"] == 2))),
                "missing_side": int(
                    np.count_nonzero(motor_mask & (arrays["side_code"] == 0))
                ),
                "with_direct_dn_input": with_input,
                "dn_edges": int(edge_mask.sum()),
                "dn_synapses": int(part_weight.sum()),
                "dn_sources": int(np.unique(part_src).size),
                "edge_sides": _edge_sides(
                    arrays["side_code"][part_src],
                    arrays["side_code"][part_dst],
                ),
                "input_pattern": categories["counts"],
            }
        )
    by_part.sort(key=lambda row: (-row["motor_neurons"], row["body_part_effector"]))

    by_annotation = {}
    for field in ("cell_class", "super_cluster", "cell_function_detailed"):
        frame = pd.DataFrame(
            {"src": src, "dst": dst, "weight": weight, "annotation": arrays[field][src]}
        )
        frame["annotation"] = frame["annotation"].replace("", UNKNOWN)
        grouped = (
            frame.groupby("annotation")
            .agg(
                edges=("weight", "size"),
                synapses=("weight", "sum"),
                descending_neurons=("src", "nunique"),
                motor_neurons=("dst", "nunique"),
            )
            .reset_index()
            .sort_values(["synapses", "edges"], ascending=False)
            .head(15)
        )
        by_annotation[field] = grouped.to_dict("records")

    return {
        "descending_population": n_dn,
        "motor_population": n_motor,
        "edges": int(src.size),
        "synapses": int(weight.sum(dtype=np.int64)),
        "unique_descending_sources": int(unique_sources.size),
        "unique_motor_targets": int(unique_targets.size),
        "motor_neurons_without_direct_input": n_motor - int(unique_targets.size),
        "descending_without_motor_target": n_dn - int(unique_sources.size),
        "source_out_degree_all_descending": _stats(out_degree[arrays["is_dn"]]),
        "source_out_degree_connected": _stats(out_degree[out_degree > 0]),
        "target_in_degree_all_motor": _stats(in_degree[arrays["is_motor"]]),
        "target_in_degree_connected": _stats(in_degree[in_degree > 0]),
        "unique_target_sides": side_counts,
        "unique_source_sides": source_sides,
        "input_synapses_to_left_targets": int(weight[arrays["side_code"][dst] == 1].sum()),
        "input_synapses_to_right_targets": int(weight[arrays["side_code"][dst] == 2].sum()),
        "edge_sides": edge_sides,
        "motor_by_effector": by_part,
        "descending_by_annotation": by_annotation,
    }


# ---------------------------------------------------------------------------
# Part C: two-hop pathways
# ---------------------------------------------------------------------------


def _encode_pairs(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    return (np.asarray(src, dtype=np.uint64) << np.uint64(32)) | np.asarray(
        dst, dtype=np.uint64
    )


def _unique_pair_count(
    mid_in: np.ndarray,
    mid_out: np.ndarray,
    used_ids: np.ndarray,
    incoming_dn: np.ndarray,
    outgoing_mn: np.ndarray,
    total_paths: int,
) -> int | None:
    if total_paths > MAX_PAIR_MATERIALIZATION:
        return None
    in_order = np.argsort(mid_in, kind="stable")
    in_sorted = mid_in[in_order]
    dn_sorted = incoming_dn[in_order]
    out_order = np.argsort(mid_out, kind="stable")
    out_sorted = mid_out[out_order]
    mn_sorted = outgoing_mn[out_order]
    chunks = []
    for vertex in used_ids:
        left = int(np.searchsorted(in_sorted, vertex, side="left"))
        right = int(np.searchsorted(in_sorted, vertex, side="right"))
        low = int(np.searchsorted(out_sorted, vertex, side="left"))
        high = int(np.searchsorted(out_sorted, vertex, side="right"))
        dn_list = dn_sorted[left:right]
        mn_list = mn_sorted[low:high]
        if dn_list.size == 0 or mn_list.size == 0:
            continue
        chunks.append(
            _encode_pairs(
                np.repeat(dn_list, mn_list.size),
                np.tile(mn_list, dn_list.size),
            )
        )
    if not chunks:
        return 0
    return int(np.unique(np.concatenate(chunks)).size)


def two_hop_pathway(
    graph: BancConnectome,
    arrays: dict,
    intermediate_mask: np.ndarray,
    target_mask: np.ndarray | None = None,
    include_source_ids: bool = False,
) -> dict:
    n = graph.n_nodes
    target_mask = arrays["is_motor"] if target_mask is None else target_mask
    src, dst, weight = graph.edge_src, graph.edge_dst, graph.edge_weight
    first = arrays["is_dn"][src] & intermediate_mask[dst]
    second = intermediate_mask[src] & target_mask[dst]
    incoming_dn = src[first]
    mids_in = dst[first]
    mids_out = src[second]
    outgoing_target = dst[second]
    incoming = np.bincount(mids_in, minlength=n).astype(np.int64)
    outgoing = np.bincount(mids_out, minlength=n).astype(np.int64)
    used = (incoming > 0) & (outgoing > 0)
    used_ids = np.flatnonzero(used)
    contrib = incoming[mids_out].astype(np.int64)
    total_paths = int(contrib.sum())
    paths_per_target = np.bincount(
        outgoing_target, weights=contrib, minlength=n
    ).astype(np.int64)
    reached = (paths_per_target > 0) & target_mask
    unique_pairs = _unique_pair_count(
        mids_in, mids_out, used_ids, incoming_dn, outgoing_target, total_paths
    )

    dn_side = arrays["side_code"][incoming_dn]
    target_side = arrays["side_code"][outgoing_target]
    dn_left = np.bincount(mids_in[dn_side == 1], minlength=n).astype(np.int64)
    dn_right = np.bincount(mids_in[dn_side == 2], minlength=n).astype(np.int64)
    dn_missing = np.bincount(mids_in[dn_side == 0], minlength=n).astype(np.int64)
    out_left = np.bincount(mids_out[target_side == 1], minlength=n).astype(np.int64)
    out_right = np.bincount(mids_out[target_side == 2], minlength=n).astype(np.int64)
    same_paths = int((dn_left * out_left + dn_right * out_right)[used].sum())
    cross_paths = int((dn_left * out_right + dn_right * out_left)[used].sum())
    missing_side_paths = total_paths - same_paths - cross_paths

    target_parts = arrays["part_code"][outgoing_target]
    paths_by_part = np.bincount(
        target_parts, weights=contrib, minlength=len(arrays["part_names"])
    ).astype(np.int64)
    by_part = []
    for part_code, part_name in enumerate(arrays["part_names"]):
        count = int(paths_by_part[part_code])
        if count == 0:
            continue
        part_edge_mask = target_parts == part_code
        part_out_left = np.bincount(
            mids_out[part_edge_mask & (target_side == 1)], minlength=n
        ).astype(np.int64)
        part_out_right = np.bincount(
            mids_out[part_edge_mask & (target_side == 2)], minlength=n
        ).astype(np.int64)
        same = int((dn_left * part_out_left + dn_right * part_out_right)[used].sum())
        cross = int((dn_left * part_out_right + dn_right * part_out_left)[used].sum())
        by_part.append(
            {
                "body_part_effector": str(part_name),
                "paths": count,
                "unique_motor_targets": int(
                    np.unique(outgoing_target[part_edge_mask]).size
                ),
                "same_side_paths": same,
                "cross_side_paths": cross,
                "same_side_share_of_known": _share(same, same + cross),
            }
        )
    by_part.sort(key=lambda row: (-row["paths"], row["body_part_effector"]))

    top_targets = []
    for index in np.argsort(-paths_per_target)[:10]:
        if not reached[index]:
            continue
        top_targets.append(
            {
                "banc_888_id": _id_string(int(index), arrays),
                "paths": int(paths_per_target[index]),
                "cell_type": arrays["cell_type"][index] or None,
                "super_class": arrays["super_class"][index] or None,
                "side": arrays["side"][index] or None,
                "body_part_effector": arrays["body_part_effector"][index] or None,
            }
        )

    used_annotation = {
        "intermediates_with_paths": int(used_ids.size),
        "super_class_present": int(
            np.count_nonzero(arrays["super_class"][used_ids] != "")
        ),
        "cell_class_present": int(
            np.count_nonzero(arrays["cell_class"][used_ids] != "")
        ),
        "cell_type_present": int(
            np.count_nonzero(arrays["cell_type"][used_ids] != "")
        ),
        "side_present": int(np.count_nonzero(arrays["side"][used_ids] != "")),
        "region_present": int(
            np.count_nonzero(arrays["region"][used_ids] != "")
        ),
        "proofread_true": int(
            np.count_nonzero(arrays["proofread"][used_ids])
        ),
        "super_class_composition": _top_counts(arrays["super_class"][used_ids], 10),
        "cell_class_composition": _top_counts(arrays["cell_class"][used_ids], 10),
        "cell_type_composition": _top_counts(arrays["cell_type"][used_ids], 10),
    }

    result = {
        "intermediate_population": int(np.count_nonzero(intermediate_mask)),
        "target_population": int(np.count_nonzero(target_mask)),
        "dn_to_intermediate_edges": int(first.sum()),
        "dn_to_intermediate_synapses": int(weight[first].sum(dtype=np.int64)),
        "intermediate_to_target_edges": int(second.sum()),
        "intermediate_to_target_synapses": int(weight[second].sum(dtype=np.int64)),
        "paths": total_paths,
        "unique_dn_target_pairs": unique_pairs,
        "unique_descending_sources": int(np.unique(incoming_dn).size),
        "unique_intermediates": int(used_ids.size),
        "unique_targets": int(np.count_nonzero(reached)),
        "targets_without_two_hop_input": int(
            np.count_nonzero(target_mask) - np.count_nonzero(reached)
        ),
        "paths_per_target": _stats(paths_per_target[reached]),
        "top_targets_by_paths": top_targets,
        "path_sides": {
            "same_side_paths": same_paths,
            "cross_side_paths": cross_paths,
            "missing_side_paths": missing_side_paths,
            "same_side_share_of_known": _share(same_paths, same_paths + cross_paths),
            "cross_side_share_of_known": _share(cross_paths, same_paths + cross_paths),
            "paths_with_missing_input_side": int(
                np.sum((dn_missing * outgoing)[used])
            ),
        },
        "paths_by_effector": by_part,
        "intermediate_annotation": used_annotation,
        "path_count_semantics": (
            "A path is one (descending neuron, intermediate, motor target) triple. "
            "Multiple intermediates reaching the same motor target do not prove "
            "independent physiological routes."
        ),
    }
    if include_source_ids:
        source_mask = used[mids_in]
        result["descending_source_ids"] = sorted(
            {_id_string(int(index), arrays) for index in incoming_dn[source_mask]}
        )
        result["intermediate_ids"] = sorted(
            {_id_string(int(index), arrays) for index in used_ids}
        )
        result["target_ids"] = sorted(
            {_id_string(int(index), arrays) for index in outgoing_target[reached[outgoing_target]]}
        )
    return result


def intermediate_masks(arrays: dict) -> dict[str, np.ndarray]:
    excluded = np.isin(
        arrays["super_class"],
        ["descending", "motor", "glia", "trachea", "not_a_neuron"],
    )
    return {
        "strict_vnc_intrinsic": arrays["is_vnc_intrinsic"],
        "broad_vnc_region": arrays["is_vnc_region"] & ~excluded,
    }


# ---------------------------------------------------------------------------
# Part D: left/right organisation
# ---------------------------------------------------------------------------


def _input_pattern_verdict(categories: dict) -> str:
    counts = categories["counts"]
    known = {
        key: value
        for key, value in counts.items()
        if key != "no_direct_input"
    }
    if not known or max(known.values()) == 0:
        return "no_known_side_input"
    return max(known, key=known.get)


def left_right_report(graphs: dict[int, BancConnectome], arrays: dict) -> dict:
    report = {}
    n = len(arrays["banc_ids"])
    motor_mask = arrays["is_motor"]
    for threshold, graph in graphs.items():
        src, dst, _ = _direct_edges(graph, arrays)
        entry = {
            "edge_sides_all_motor": _edge_sides(
                arrays["side_code"][src], arrays["side_code"][dst]
            ),
            "input_pattern_all_motor": _classify_motor_inputs(
                n, arrays, src, dst, motor_mask
            ),
            "by_effector": {},
        }
        entry["dominant_input_pattern"] = _input_pattern_verdict(
            entry["input_pattern_all_motor"]
        )
        for part_name in FOCUS_EFFECTORS:
            part_index = int(np.searchsorted(arrays["part_names"], part_name))
            if part_index >= len(arrays["part_names"]) or arrays["part_names"][part_index] != part_name:
                continue
            part_mask = motor_mask & (arrays["part_code"] == part_index)
            population = int(np.count_nonzero(part_mask))
            if population == 0:
                continue
            edge_mask = arrays["part_code"][dst] == part_index
            entry["by_effector"][part_name] = {
                "motor_neurons": population,
                "left": int(np.count_nonzero(part_mask & (arrays["side_code"] == 1))),
                "right": int(np.count_nonzero(part_mask & (arrays["side_code"] == 2))),
                "missing_side": int(
                    np.count_nonzero(part_mask & (arrays["side_code"] == 0))
                ),
                "direct_edges": int(edge_mask.sum()),
                "edge_sides": _edge_sides(
                    arrays["side_code"][src[edge_mask]],
                    arrays["side_code"][dst[edge_mask]],
                ),
                "input_pattern": _classify_motor_inputs(
                    n, arrays, src, dst, part_mask
                ),
            }
            entry["by_effector"][part_name]["dominant_input_pattern"] = (
                _input_pattern_verdict(entry["by_effector"][part_name]["input_pattern"])
            )
        report[f"threshold_{threshold}"] = entry
    return report


# ---------------------------------------------------------------------------
# Part E: tergotrochanter-associated candidates
# ---------------------------------------------------------------------------


def _jump_annotations(nodes: pd.DataFrame) -> dict:
    candidates = nodes[nodes["is_tergotrochanter_candidate"].fillna(False).astype(bool)]
    columns = [
        "banc_888_id",
        "cell_class",
        "cell_sub_class",
        "cell_type",
        "side",
        "body_part_effector",
        "peripheral_target_type",
        "cell_function",
        "nerve",
        "proofread",
        "roughly_proofread",
        "status",
        "neurotransmitter_verified",
    ]
    records = []
    for row in candidates[columns].itertuples(index=False):
        record = {column: getattr(row, column) for column in columns}
        record["banc_888_id"] = str(record["banc_888_id"])
        for value in list(record):
            if not isinstance(record[value], str) and pd.isna(record[value]):
                record[value] = None
        records.append(record)
    records.sort(key=lambda row: (row["side"] or "", row["banc_888_id"]))
    return {
        "candidates": int(len(candidates)),
        "by_side": {
            str(key): int(value)
            for key, value in candidates["side"].value_counts(dropna=False).items()
        },
        "all_peripheral_target_exact": bool(
            candidates["peripheral_target_type"].eq(JUMP_TARGET).all()
        ),
        "peripheral_target_values": {
            str(key): int(value)
            for key, value in candidates["peripheral_target_type"].value_counts(
                dropna=False
            ).items()
        },
        "by_body_part_effector": {
            str(key): int(value)
            for key, value in candidates["body_part_effector"].value_counts(
                dropna=False
            ).items()
        },
        "cell_types": sorted(
            {str(value) for value in candidates["cell_type"].dropna().unique()}
        ),
        "proofread_true": int(
            candidates["proofread"].fillna(False).astype(bool).sum()
        ),
        "roughly_proofread_true": int(
            candidates["roughly_proofread"].fillna(False).astype(bool).sum()
        ),
        "status_counts": {
            str(key): int(value)
            for key, value in candidates["status"].value_counts(dropna=False).items()
        },
        "candidate_records": records,
    }


def _per_source_table(
    src: np.ndarray, dst: np.ndarray, weight: np.ndarray, arrays: dict
) -> list[dict]:
    frame = pd.DataFrame({"src": src, "dst": dst, "weight": weight})
    grouped = (
        frame.groupby("src")
        .agg(edges=("weight", "size"), synapses=("weight", "sum"), targets=("dst", "nunique"))
        .reset_index()
        .sort_values(["synapses", "edges"], ascending=False)
    )
    records = []
    for row in grouped.itertuples(index=False):
        index = int(row.src)
        records.append(
            {
                "banc_888_id": _id_string(index, arrays),
                "edges": int(row.edges),
                "synapses": int(row.synapses),
                "targets": int(row.targets),
                "cell_class": arrays["cell_class"][index] or None,
                "cell_type": arrays["cell_type"][index] or None,
                "super_cluster": arrays["super_cluster"][index] or None,
                "side": arrays["side"][index] or None,
            }
        )
    return records


def _per_target_table(
    src: np.ndarray, dst: np.ndarray, weight: np.ndarray, arrays: dict
) -> list[dict]:
    frame = pd.DataFrame({"src": src, "dst": dst, "weight": weight})
    grouped = (
        frame.groupby("dst")
        .agg(edges=("weight", "size"), synapses=("weight", "sum"), sources=("src", "nunique"))
        .reset_index()
        .sort_values(["synapses", "edges"], ascending=False)
    )
    records = []
    for row in grouped.itertuples(index=False):
        index = int(row.dst)
        records.append(
            {
                "banc_888_id": _id_string(index, arrays),
                "edges": int(row.edges),
                "synapses": int(row.synapses),
                "sources": int(row.sources),
                "cell_type": arrays["cell_type"][index] or None,
                "side": arrays["side"][index] or None,
            }
        )
    return records


def jump_report(
    graphs: dict[int, BancConnectome],
    arrays: dict,
    intermediate_mask: np.ndarray,
    annotations: dict,
) -> dict:
    jump_mask = arrays["is_jump"]
    jump_ids = set(arrays["banc_ids"][jump_mask].tolist())
    report = {"annotations": annotations, "thresholds": {}}
    for threshold, graph in graphs.items():
        src, dst, weight = _direct_edges(graph, arrays)
        edge_mask = jump_mask[dst]
        direct_src = src[edge_mask]
        direct_dst = dst[edge_mask]
        direct_weight = weight[edge_mask]
        direct_sources = set(arrays["banc_ids"][np.unique(direct_src)].tolist())
        two_hop = two_hop_pathway(
            graph,
            arrays,
            intermediate_mask,
            target_mask=jump_mask,
            include_source_ids=True,
        )
        two_sources = {
            int(value) for value in two_hop.get("descending_source_ids", [])
        }
        per_dn = _per_source_table(direct_src, direct_dst, direct_weight, arrays)
        per_target = _per_target_table(direct_src, direct_dst, direct_weight, arrays)
        target_synapses_left = int(
            direct_weight[arrays["side_code"][direct_dst] == 1].sum()
        )
        target_synapses_right = int(
            direct_weight[arrays["side_code"][direct_dst] == 2].sum()
        )
        report["thresholds"][f"threshold_{threshold}"] = {
            "graph_candidates": int(np.count_nonzero(jump_mask)),
            "candidates_with_direct_input": int(
                np.unique(direct_dst).size
            ),
            "candidates_with_two_hop_input": int(two_hop["unique_targets"]),
            "direct_dn_edges": int(edge_mask.sum()),
            "direct_dn_synapses": int(direct_weight.sum(dtype=np.int64)),
            "direct_descending_sources": int(len(direct_sources)),
            "direct_by_source": per_dn,
            "direct_by_target": per_target,
            "direct_edge_sides": _edge_sides(
                arrays["side_code"][direct_src],
                arrays["side_code"][direct_dst],
            ),
            "direct_synapses_to_left_targets": target_synapses_left,
            "direct_synapses_to_right_targets": target_synapses_right,
            "left_right_synapse_ratio": (
                None
                if target_synapses_right == 0
                else round(target_synapses_left / target_synapses_right, 6)
            ),
            "two_hop": two_hop,
            "descending_sources_direct_only": len(direct_sources - two_sources),
            "descending_sources_two_hop_only": len(two_sources - direct_sources),
            "descending_sources_both": len(direct_sources & two_sources),
            "all_candidates_retained_as_nodes": bool(
                jump_ids.issubset(set(arrays["banc_ids"].tolist()))
            ),
        }
    return report


# ---------------------------------------------------------------------------
# Part F: threshold sensitivity
# ---------------------------------------------------------------------------


def _direct_pair_codes(graph: BancConnectome, arrays: dict) -> np.ndarray:
    src, dst, _ = _direct_edges(graph, arrays)
    return np.unique(_encode_pairs(src, dst))


def threshold_sensitivity(
    graphs: dict[int, BancConnectome],
    arrays: dict,
    direct: dict[str, dict],
    two_hop: dict[str, dict],
    jump: dict,
) -> dict:
    n = len(arrays["banc_ids"])
    pair_codes = {
        threshold: _direct_pair_codes(graph, arrays)
        for threshold, graph in graphs.items()
    }
    common = pair_codes[1]
    for threshold in THRESHOLDS[1:]:
        common = np.intersect1d(common, pair_codes[threshold], assume_unique=True)

    input_synapses = {}
    for threshold, graph in graphs.items():
        src, dst, weight = _direct_edges(graph, arrays)
        input_synapses[threshold] = np.bincount(
            dst, weights=weight, minlength=n
        ).astype(np.int64)

    base = input_synapses[1]
    motor_indices = np.flatnonzero(arrays["is_motor"])
    losses = []
    for index in motor_indices:
        if base[index] == 0:
            continue
        losses.append(
            (
                int(base[index] - input_synapses[PRIMARY_THRESHOLD][index]),
                int(base[index]),
                int(input_synapses[PRIMARY_THRESHOLD][index]),
                int(input_synapses[10][index]),
                int(index),
            )
        )
    losses.sort(reverse=True)
    top_losses = []
    for loss, original, primary, strict, index in losses[:15]:
        top_losses.append(
            {
                "banc_888_id": _id_string(index, arrays),
                "cell_type": arrays["cell_type"][index] or None,
                "side": arrays["side"][index] or None,
                "body_part_effector": arrays["body_part_effector"][index] or None,
                "t1_synapses": original,
                "t5_synapses": primary,
                "t10_synapses": strict,
                "synapse_loss_t1_to_t5": loss,
                "retention_t5": _share(primary, original),
            }
        )

    effector_retention = []
    for part_code, part_name in enumerate(arrays["part_names"]):
        part_mask = arrays["is_motor"] & (arrays["part_code"] == part_code)
        population = int(np.count_nonzero(part_mask))
        if population == 0:
            continue
        row = {
            "body_part_effector": str(part_name),
            "motor_neurons": population,
            "t1_synapses": 0,
            "t5_synapses": 0,
            "t10_synapses": 0,
            "t1_motor_neurons_with_input": 0,
            "t5_motor_neurons_with_input": 0,
            "t10_motor_neurons_with_input": 0,
        }
        for threshold in THRESHOLDS:
            graph = graphs[threshold]
            src, dst, weight = _direct_edges(graph, arrays)
            mask = arrays["part_code"][dst] == part_code
            row[f"t{threshold}_synapses"] = int(weight[mask].sum(dtype=np.int64))
            row[f"t{threshold}_motor_neurons_with_input"] = int(
                np.unique(dst[mask]).size
            )
        row["retention_t5"] = _share(row["t5_synapses"], row["t1_synapses"])
        row["retention_t10"] = _share(row["t10_synapses"], row["t1_synapses"])
        effector_retention.append(row)
    effector_retention.sort(
        key=lambda row: (-row["motor_neurons"], row["body_part_effector"])
    )

    intermediates = {}
    for name in ("strict_vnc_intrinsic", "broad_vnc_region"):
        intermediates[name] = {}
        for threshold in THRESHOLDS:
            data = two_hop[f"threshold_{threshold}"][name]
            intermediates[name][f"threshold_{threshold}"] = {
                "population": data["intermediate_population"],
                "with_paths": data["unique_intermediates"],
                "dn_to_intermediate_edges": data["dn_to_intermediate_edges"],
                "intermediate_to_target_edges": data["intermediate_to_target_edges"],
                "paths": data["paths"],
                "unique_dn_target_pairs": data["unique_dn_target_pairs"],
                "descending_sources": data["unique_descending_sources"],
                "motor_targets": data["unique_targets"],
            }

    jump_stability = {}
    for threshold in THRESHOLDS:
        entry = jump["thresholds"][f"threshold_{threshold}"]
        jump_stability[f"threshold_{threshold}"] = {
            "direct_dn_edges": entry["direct_dn_edges"],
            "direct_dn_synapses": entry["direct_dn_synapses"],
            "direct_descending_sources": entry["direct_descending_sources"],
            "candidates_with_direct_input": entry["candidates_with_direct_input"],
            "candidates_with_two_hop_input": entry["candidates_with_two_hop_input"],
            "two_hop_paths": entry["two_hop"]["paths"],
            "same_side_share_of_known": entry["direct_edge_sides"][
                "same_side_share_of_known"
            ],
        }

    retained_by_effector = [
        row
        for row in effector_retention
        if row["t5_synapses"] > 0 and row["t10_synapses"] > 0
    ]
    return {
        "direct_edge_retention": {
            f"threshold_{threshold}": {
                "edges": direct[f"threshold_{threshold}"]["edges"],
                "synapses": direct[f"threshold_{threshold}"]["synapses"],
                "edge_share_of_t1": _share(
                    direct[f"threshold_{threshold}"]["edges"],
                    direct["threshold_1"]["edges"],
                ),
                "synapse_share_of_t1": _share(
                    direct[f"threshold_{threshold}"]["synapses"],
                    direct["threshold_1"]["synapses"]
                ),
                "motor_targets": direct[f"threshold_{threshold}"][
                    "unique_motor_targets"
                ],
                "motor_target_share_of_t1": _share(
                    direct[f"threshold_{threshold}"]["unique_motor_targets"],
                    direct["threshold_1"]["unique_motor_targets"],
                ),
            }
            for threshold in THRESHOLDS
        },
        "direct_pairs_present_all_thresholds": int(common.size),
        "direct_pairs_present_all_thresholds_share_of_t1": _share(
            common.size, pair_codes[1].size
        ),
        "direct_pairs_t1_t5": int(
            np.intersect1d(pair_codes[1], pair_codes[5], assume_unique=True).size
        ),
        "direct_pairs_t1_t10": int(
            np.intersect1d(pair_codes[1], pair_codes[10], assume_unique=True).size
        ),
        "motor_neurons_with_input_all_thresholds": int(
            np.count_nonzero(
                (input_synapses[1] > 0)
                & (input_synapses[5] > 0)
                & (input_synapses[10] > 0)
            )
        ),
        "motor_neurons_without_input": {
            f"threshold_{threshold}": int(
                np.count_nonzero(
                    arrays["is_motor"] & (input_synapses[threshold] == 0)
                )
            )
            for threshold in THRESHOLDS
        },
        "top_motor_neurons_by_synapse_loss_t1_to_t5": top_losses,
        "effector_retention": effector_retention,
        "persisting_effectors": [
            row["body_part_effector"] for row in retained_by_effector
        ],
        "intermediate_populations": intermediates,
        "jump_stability": jump_stability,
        "null_model": (
            "None. No random-graph control or significance test was performed; "
            "threshold differences are descriptive."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 4C.5 reproduction
# ---------------------------------------------------------------------------


def reproduce_audit(audit: dict, direct: dict, two_hop: dict, jump: dict) -> dict:
    reference = audit["F_locomotor_readiness"]
    direct_t1 = direct["threshold_1"]
    two_t1 = two_hop["threshold_1"]["strict_vnc_intrinsic"]
    jump_t1 = jump["thresholds"]["threshold_1"]

    def compare(name: str, expected, actual) -> dict:
        return {
            "name": name,
            "phase_4c5": expected,
            "phase_4e_threshold_1": actual,
            "delta": None if expected is None else actual - expected,
            "match": bool(expected == actual),
        }

    checks = [
        compare(
            "direct_dn_to_mn_edges",
            reference["direct_dn_to_mn"]["edges"],
            direct_t1["edges"],
        ),
        compare(
            "direct_dn_to_mn_synapses",
            reference["direct_dn_to_mn"]["synapses"],
            direct_t1["synapses"],
        ),
        compare(
            "direct_descending_neurons",
            reference["direct_dn_to_mn"]["descending_neurons"],
            direct_t1["unique_descending_sources"],
        ),
        compare(
            "direct_motor_neurons",
            reference["direct_dn_to_mn"]["motor_neurons"],
            direct_t1["unique_motor_targets"],
        ),
        compare(
            "dn_to_vnc_intrinsic_edges",
            reference["dn_to_vnc_intrinsic_edges"],
            two_t1["dn_to_intermediate_edges"],
        ),
        compare(
            "vnc_intrinsic_to_mn_edges",
            reference["vnc_intrinsic_to_mn_edges"],
            two_t1["intermediate_to_target_edges"],
        ),
        compare(
            "two_hop_paths",
            reference["two_hop_dn_vnc_mn"]["paths"],
            two_t1["paths"],
        ),
        compare(
            "two_hop_unique_dn_mn_pairs",
            reference["two_hop_dn_vnc_mn"]["unique_dn_mn_pairs"],
            two_t1["unique_dn_target_pairs"],
        ),
        compare(
            "two_hop_descending_neurons",
            reference["two_hop_dn_vnc_mn"]["descending_neurons"],
            two_t1["unique_descending_sources"],
        ),
        compare(
            "two_hop_motor_neurons",
            reference["two_hop_dn_vnc_mn"]["motor_neurons"],
            two_t1["unique_targets"],
        ),
        compare(
            "jump_motor_neurons",
            reference["jump_tergotrochanter"]["motor_neurons"],
            jump_t1["graph_candidates"],
        ),
        compare(
            "jump_dn_edges",
            reference["jump_tergotrochanter"]["dn_edges"],
            jump_t1["direct_dn_edges"],
        ),
        compare(
            "jump_descending_neurons",
            reference["jump_tergotrochanter"]["descending_neurons"],
            jump_t1["direct_descending_sources"],
        ),
        compare(
            "jump_synapses",
            reference["jump_tergotrochanter"]["synapses"],
            jump_t1["direct_dn_synapses"],
        ),
    ]
    side_expected = reference["jump_tergotrochanter"]["motor_neurons_by_side"]
    side_actual = jump["annotations"]["by_side"]
    checks.append(
        {
            "name": "jump_motor_neurons_by_side",
            "phase_4c5": side_expected,
            "phase_4e_threshold_1": side_actual,
            "delta": {
                key: side_actual.get(key, 0) - side_expected.get(key, 0)
                for key in set(side_actual) | set(side_expected)
            },
            "match": side_actual == side_expected,
        }
    )

    body_part_mismatches = []
    ours = {
        row["body_part_effector"]: row for row in direct_t1["motor_by_effector"]
    }
    for part, expected in reference["motor_neurons_by_body_part"].items():
        actual = ours.get(part)
        if actual is None:
            body_part_mismatches.append({"body_part_effector": part, "missing": True})
            continue
        for field in (
            "motor_neurons",
            "with_direct_dn_input",
            "left",
            "right",
            "dn_edges",
            "dn_synapses",
        ):
            if actual[field] != expected[field]:
                body_part_mismatches.append(
                    {
                        "body_part_effector": part,
                        "field": field,
                        "phase_4c5": expected[field],
                        "phase_4e_threshold_1": actual[field],
                    }
                )
    return {
        "comparison_threshold": AUDIT_COMPARISON_THRESHOLD,
        "note": (
            "Phase 4C.5 read the unfiltered edgelist, which is equivalent to the "
            "threshold-1 graph here after self-edge removal. Its figures are "
            "therefore compared to threshold 1, not the primary threshold 5."
        ),
        "checks": checks,
        "all_match": all(check["match"] for check in checks),
        "motor_neurons_by_body_part_mismatches": body_part_mismatches,
        "motor_neurons_by_body_part_match": not body_part_mismatches,
        "pass": all(check["match"] for check in checks) and not body_part_mismatches,
    }


# ---------------------------------------------------------------------------
# report assembly
# ---------------------------------------------------------------------------


def _integrity_block(
    manifest: dict,
    verification: dict,
    nodes_path: Path,
    audit_path: Path,
    graphs: dict[int, BancConnectome],
    nodes: pd.DataFrame,
) -> dict:
    node_ids = nodes["banc_888_id"].astype("int64").to_numpy()
    return {
        "manifest_inputs": manifest.get("inputs", {}),
        "manifest_outputs": manifest.get("outputs", {}),
        "manifest_verification_pass": bool(verification["pass"]),
        "manifest_verification_failures": verification["failures"],
        "nodes_sha256": sha256_file(nodes_path),
        "audit_sha256": sha256_file(audit_path),
        "graph_node_ids_match_nodes": {
            str(threshold): bool(np.array_equal(graph.root_ids, node_ids))
            for threshold, graph in graphs.items()
        },
        "graph_hashes_verified_by_manifest": verification["pass"],
        "fafb_isolation_unchanged": bool(
            manifest.get("fafb_isolation", {}).get("unchanged", False)
        ),
    }


def analyze(
    graph_dir: Path = OUT_DIR,
    nodes_path: Path | None = None,
    manifest_path: Path | None = None,
    audit_path: Path = AUDIT_JSON,
) -> dict:
    started = time.perf_counter()
    graph_dir = Path(graph_dir)
    nodes_path = Path(nodes_path or graph_dir / "banc_nodes.csv.gz")
    manifest_path = Path(manifest_path or graph_dir / "banc_manifest.json")
    audit_path = Path(audit_path)

    nodes, graphs, manifest, verification = load_inputs(
        graph_dir, nodes_path, manifest_path
    )
    arrays = annotation_arrays(nodes)
    meta = load_metadata(DEFAULT_INPUTS["metadata"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    direct = {
        f"threshold_{threshold}": direct_pathway(graphs[threshold], arrays)
        for threshold in THRESHOLDS
    }
    masks = intermediate_masks(arrays)
    two_hop = {
        f"threshold_{threshold}": {
            name: two_hop_pathway(graphs[threshold], arrays, mask)
            for name, mask in masks.items()
        }
        for threshold in THRESHOLDS
    }
    jump = jump_report(graphs, arrays, masks["strict_vnc_intrinsic"], _jump_annotations(nodes))
    sensitivity = threshold_sensitivity(graphs, arrays, direct, two_hop, jump)
    reproduction = reproduce_audit(audit, direct, two_hop, jump)

    populations = population_report(nodes, audit)
    discrepancy = vnc_intrinsic_discrepancy(meta, nodes)
    coverage = {
        "graph_nodes": _coverage_block(nodes),
        "descending": _coverage_block(nodes[nodes["is_descending"].astype(bool)]),
        "motor": _coverage_block(nodes[nodes["is_motor"].astype(bool)]),
        "vnc_intrinsic": _coverage_block(nodes[nodes["is_vnc_intrinsic"].astype(bool)]),
        "tergotrochanter_candidates": _coverage_block(
            nodes[nodes["is_tergotrochanter_candidate"].astype(bool)]
        ),
    }

    integrity = _integrity_block(
        manifest, verification, nodes_path, audit_path, graphs, nodes
    )
    integrity["manifest_path"] = str(manifest_path)
    limitations = [
        "BANC is a separate specimen from FAFB; this analysis does not merge them.",
        "The graph contains only exported v2 pairs with both partners identified.",
        "Edge weight is synapse count, not conductance or release probability.",
        "Structural adjacency does not establish synaptic sign or physiological function.",
        "Every intermediate is a connectivity-derived premotor candidate, not a validated premotor neuron.",
        "Two-hop paths are triples, not independent physiological routes.",
        "Motor-effector annotations do not establish a specific game command.",
        "The 20 tergotrochanter candidates are jump-associated, not confirmed jump commands.",
        "No biological Subway Surfers action has been identified.",
        "No random-graph null model or significance test was used.",
    ]
    core_checks = {
        "manifest_verified": bool(verification["pass"]),
        "graph_ids_match_node_table": all(
            integrity["graph_node_ids_match_nodes"].values()
        ),
        "phase_4c5_reproduced_at_threshold_1": bool(reproduction["pass"]),
        "vnc_intrinsic_discrepancy_is_16": discrepancy["missing_count"] == 16,
        "fafb_artifacts_unchanged": bool(integrity["fafb_isolation_unchanged"]),
    }
    verdict = "PASS WITH LIMITATIONS" if all(core_checks.values()) else "FAIL"

    report = {
        "phase": "4E",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdict": verdict,
        "canonical_id_field": "banc_888_id",
        "parameters": {
            "thresholds": list(THRESHOLDS),
            "primary_threshold": PRIMARY_THRESHOLD,
            "phase_4c5_comparison_threshold": AUDIT_COMPARISON_THRESHOLD,
            "jump_target": JUMP_TARGET,
            "focus_effectors": list(FOCUS_EFFECTORS),
            "intermediate_definitions": {
                "strict_vnc_intrinsic": "super_class == 'ventral_nerve_cord_intrinsic'",
                "broad_vnc_region": (
                    "region == 'ventral_nerve_cord' and super_class not in "
                    "{descending, motor, glia, trachea, not_a_neuron}"
                ),
            },
            "path_counting": (
                "one path = one (descending neuron, intermediate, motor target) triple; "
                "unique DN->MN pairs are counted separately"
            ),
            "weight_policy": "integer count; norm is never used",
            "deterministic": True,
        },
        "populations": populations,
        "vnc_intrinsic_discrepancy": discrepancy,
        "annotation_coverage": coverage,
        "direct_pathways": direct,
        "two_hop_pathways": two_hop,
        "left_right_organisation": left_right_report(graphs, arrays),
        "jump_candidates": jump,
        "threshold_sensitivity": sensitivity,
        "phase_4c5_reproduction": reproduction,
        "integrity": integrity,
        "software": software_versions(),
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "core_checks": core_checks,
        "limitations": limitations,
    }
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--nodes", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--audit", type=Path, default=AUDIT_JSON)
    parser.add_argument("--output", type=Path, default=REPORT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = analyze(args.graph_dir, args.nodes, args.manifest, args.audit)
    write_json(args.output, report)
    jump = report["jump_candidates"]["thresholds"]["threshold_1"]
    print(
        "verdict: {verdict}; nodes: {nodes}; direct DN->MN t1: {edges}; "
        "jump t1: {jump_edges} edges / {jump_sources} DNs / {jump_synapses} synapses".format(
            verdict=report["verdict"],
            nodes=report["populations"]["counts"]["total_graph_nodes"],
            edges=report["direct_pathways"]["threshold_1"]["edges"],
            jump_edges=jump["direct_dn_edges"],
            jump_sources=jump["direct_descending_sources"],
            jump_synapses=jump["direct_dn_synapses"],
        )
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
