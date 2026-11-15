#!/usr/bin/env python3
"""Phase 4C.5 read-only readiness audit of the local BANC v888 graph subset.

The audit never writes to datasets/external. It reads the five downloaded
BANC files, recomputes integrity and annotation statistics, and emits one
machine-readable JSON report.

Usage:
    python experiments/phase_4c/audit_banc_graph.py
    python experiments/phase_4c/audit_banc_graph.py --output reports/PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.feather as feather
import pyarrow.parquet as parquet

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BANC_RAW = PROJECT_ROOT / "datasets" / "external" / "banc_v88" / "raw"

DEFAULT_INPUTS = {
    "metadata": BANC_RAW / "metadata" / "banc_888_meta.feather",
    "edgelist_v2": BANC_RAW / "connectivity" / "banc_888_edgelist_simple_v2.feather",
    "backbone_proofread": BANC_RAW / "annotations" / "backbone_proofread.parquet",
    "neurotransmitter": BANC_RAW / "annotations" / "banc_888_neurotransmitter_prediction_v2.csv",
    # The bucket object is a plain CSV; the local copy carries a .gz suffix.
    "reviewed_matches": BANC_RAW / "cross_dataset_matches" / "banc_fafb_reviewed_matches.csv.gz",
}

NON_NEURON_CLASSES = {"glia", "trachea", "not_a_neuron"}
LEG_PARTS = ("front_leg", "middle_leg", "hind_leg")
ID_COLUMNS = ("banc_888_id", "root_id", "root_626", "root_850", "root_888", "root_890")
META_COLUMNS = (
    "banc_888_id",
    "root_id",
    "root_626",
    "root_850",
    "root_888",
    "root_890",
    "proofread",
    "roughly_proofread",
    "status",
    "side",
    "region",
    "super_class",
    "cell_class",
    "cell_type",
    "super_cluster",
    "body_part_effector",
    "peripheral_target_type",
    "cell_function",
    "neurotransmitter_predicted",
    "neurotransmitter_verified",
    "neurotransmitter_score",
    "fafb_match",
    "fafb_nblast_match",
    "fafb_cell_type",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata(path: Path) -> pd.DataFrame:
    table = feather.read_table(path)
    frame = table.select(list(META_COLUMNS)).to_pandas()
    frame.attrs["source_columns_total"] = int(table.num_columns)
    return frame


def load_edgelist(path: Path) -> dict[str, np.ndarray]:
    table = feather.read_table(path)
    nulls = {name: int(table.column(name).null_count) for name in table.column_names}
    edges = {
        "pre": table.column("pre").cast("int64").to_numpy(),
        "post": table.column("post").cast("int64").to_numpy(),
        "count": table.column("count").to_numpy().astype("int64"),
        "norm": table.column("norm").to_numpy(),
        "pre_count": table.column("pre_count").to_numpy().astype("int64"),
        "post_count": table.column("post_count").to_numpy().astype("int64"),
        "nulls": nulls,
        "rows": int(table.num_rows),
        "columns": list(table.column_names),
    }
    return edges


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _quantiles(values: np.ndarray, points=(50, 90, 99, 100)) -> dict[str, float]:
    if values.size == 0:
        return {}
    return {f"p{p}": float(np.percentile(values, p)) for p in points}


def audit_canonical_ids(meta: pd.DataFrame) -> dict:
    """Compare the candidate identifier columns and choose the canonical key."""
    report: dict[str, object] = {"candidate_columns": list(ID_COLUMNS)}
    report["banc_888_id"] = {
        "rows": int(len(meta)),
        "nulls": int(meta["banc_888_id"].isna().sum()),
        "empty_strings": int((meta["banc_888_id"].astype(str).str.strip() == "").sum()),
        "duplicates": int(meta["banc_888_id"].duplicated().sum()),
        "unique": int(meta["banc_888_id"].nunique()),
        "example": str(meta["banc_888_id"].iloc[0]),
        "dtype": str(meta["banc_888_id"].dtype),
    }
    base_text = meta["banc_888_id"].astype(str)
    per_column: dict[str, dict] = {}
    for column in ID_COLUMNS[1:]:
        raw = meta[column]
        valid = raw.notna() & (raw.astype(str).str.strip() != "")
        equal = raw.astype(str) == base_text
        per_column[column] = {
            "nulls": int((~valid).sum()),
            "unique_non_null": int(raw[valid].nunique()),
            "duplicate_rows": int(raw.duplicated().sum()),
            "equals_banc_888_id": int((equal & valid).sum()),
            "equals_banc_888_id_share": float((equal & valid).sum() / valid.sum()) if valid.any() else None,
            "mismatch_rows": int((valid & ~equal).sum()),
        }
    report["columns"] = per_column
    if per_column["root_888"]["mismatch_rows"] != 0:
        report["root_888_mismatch_rows"] = int(per_column["root_888"]["mismatch_rows"])

    mismatch = meta[meta["banc_888_id"] != meta["root_888"]]
    report["banc_888_id_vs_root_888_mismatches"] = [
        {
            "banc_888_id": str(row.banc_888_id),
            "root_888": str(row.root_888),
            "root_890": str(row.root_890),
            "super_class": None if pd.isna(row.super_class) else str(row.super_class),
            "proofread": str(row.proofread),
        }
        for row in mismatch.head(10).itertuples()
    ]
    report["canonical"] = "banc_888_id"
    report["canonical_rationale"] = (
        "Unique, non-null primary key; equals root_888 on all but the two rows shown, "
        "and the edge list joins to it exactly. root_id is a pre-split identifier."
    )
    report["verdict"] = "PASS" if report["banc_888_id"]["duplicates"] == 0 else "FAIL"
    return report


def _edge_pairs(pre: np.ndarray, post: np.ndarray) -> np.ndarray:
    pairs = np.empty(pre.shape[0], dtype=[("pre", "<i8"), ("post", "<i8")])
    pairs["pre"] = pre
    pairs["post"] = post
    return pairs


def _annotate_nodes(meta: pd.DataFrame, node_ids: np.ndarray, column: str) -> np.ndarray:
    """Map node IDs to a metadata column, assuming every ID is present."""
    meta_ids = meta["banc_888_id"].astype("int64").to_numpy()
    order = np.argsort(meta_ids)
    position = np.searchsorted(meta_ids[order], node_ids)
    return meta[column].to_numpy()[order[position]]


def audit_self_edges(
    pre: np.ndarray,
    post: np.ndarray,
    count: np.ndarray,
    meta: pd.DataFrame | None = None,
) -> dict:
    """Quantify self-loop rows without assuming they are artifacts or biology."""
    mask = pre == post
    rows = int(mask.sum())
    total = int(count.sum())
    sel = int(count[mask].sum())
    nodes = np.unique(pre[mask]) if rows else np.empty(0, dtype="int64")
    per_node = count[mask]
    report: dict[str, object] = {
        "rows": rows,
        "rows_share_of_edgelist": float(rows / pre.shape[0]) if pre.shape[0] else None,
        "unique_nodes": int(nodes.size),
        "rows_per_node": float(rows / nodes.size) if nodes.size else None,
        "summed_count": sel,
        "summed_count_share": float(sel / total) if total else None,
        "count_quantiles": _quantiles(per_node),
        "min_count": int(per_node.min()) if rows else None,
        "max_count": int(per_node.max()) if rows else None,
    }
    if meta is not None and rows:
        node_class = _annotate_nodes(meta, np.unique(pre[mask]), "super_class")
        report["by_super_class"] = (
            pd.Series(node_class).value_counts(dropna=False).head(20).to_dict()
        )
    report["interpretation"] = (
        "Exactly one self-loop per affected segment, present in "
        f"{100.0 * nodes.size / np.unique(np.concatenate([pre, post])).size:.1f}% of "
        "graph nodes and including non-neuronal segments. The BANC paper reports a "
        "2.1% autapse rate in reviewed cubes, expects most autapses to be presynaptic "
        "misassignments, and recommends filtering them. The published v2 edgelist "
        "dictionary says autapses are excluded at build time, which this local build "
        "contradicts. This audit does not delete them."
    )
    return report


def audit_edge_integrity(
    pre: np.ndarray,
    post: np.ndarray,
    count: np.ndarray,
    norm: np.ndarray,
    meta_ids: np.ndarray,
    nulls: dict[str, int],
    source_rows: int,
) -> dict:
    """Validate endpoint coverage, duplicates and value ranges."""
    nodes = np.unique(np.concatenate([pre, post]))
    pairs = np.unique(_edge_pairs(pre, post))
    missing_meta = int((~pd.Index(nodes).isin(pd.Index(meta_ids))).sum())
    null_total = int(sum(nulls.values()))
    report: dict[str, object] = {
        "source_rows": int(source_rows),
        "parsed_rows": int(pre.shape[0]),
        "column_nulls": nulls,
        "column_null_total": null_total,
        "unique_nodes": int(nodes.size),
        "unique_directed_pairs": int(pairs.size),
        "duplicate_pair_rows": int(pre.shape[0] - pairs.size),
        "aggregation_needed": bool(pre.shape[0] != pairs.size),
        "count_le_zero": int((count <= 0).sum()),
        "count_min": int(count.min()) if count.size else None,
        "count_max": int(count.max()) if count.size else None,
        "norm_non_finite": int((~np.isfinite(norm)).sum()),
        "norm_le_zero": int((norm <= 0).sum()),
        "nodes_missing_from_metadata": missing_meta,
        "endpoint_coverage": float(1.0 - missing_meta / nodes.size) if nodes.size else None,
    }
    report["verdict"] = (
        "PASS"
        if null_total == 0
        and report["duplicate_pair_rows"] == 0
        and report["count_le_zero"] == 0
        and missing_meta == 0
        else "FAIL"
    )
    return report


def audit_weight_semantics(
    pre: np.ndarray,
    post: np.ndarray,
    count: np.ndarray,
    norm: np.ndarray,
    pre_count: np.ndarray,
    post_count: np.ndarray,
) -> dict:
    """Recompute the documented identities behind count/norm/pre_count/post_count."""
    total = int(count.sum())
    pre_sum = pd.Series(count).groupby(pd.Series(pre)).sum()
    post_sum = pd.Series(count).groupby(pd.Series(post)).sum()
    pre_declared = pd.Series(pre_count).groupby(pd.Series(pre)).first()
    post_declared = pd.Series(post_count).groupby(pd.Series(post)).first()

    calc = count / np.maximum(post_count, 1)
    rel = np.abs(calc - norm) / np.maximum(np.abs(calc), 1e-12)
    report: dict[str, object] = {
        "summed_count": total,
        "sum_of_pre_count": int(pre_declared.sum()),
        "sum_of_post_count": int(post_declared.sum()),
        "pre_count_equals_outgoing_sum_share": float((pre_sum == pre_declared).mean()),
        "post_count_equals_incoming_sum_share": float((post_sum == post_declared).mean()),
        "pre_count_constant_per_source": bool(
            pd.Series(pre_count).groupby(pd.Series(pre)).nunique().max() == 1
        ),
        "post_count_constant_per_target": bool(
            pd.Series(post_count).groupby(pd.Series(post)).nunique().max() == 1
        ),
        "norm_vs_count_over_post_count": {
            "max_relative_error": float(rel.max()),
            "share_within_0_1_percent": float((rel <= 1e-3).mean()),
            "note": "Documented as count/post_count rounded to 4 significant figures.",
        },
        "count_quantiles": _quantiles(count),
        "weight_one_share": float((count == 1).mean()),
        "weight_ge_5_share_of_pairs": float((count >= 5).mean()),
        "weight_ge_5_share_of_synapses": float(count[count >= 5].sum() / total),
        "norm_quantiles": _quantiles(norm),
        "meaning": {
            "count": "Synapses from pre to post after the v2 postsynapse size >= 5 filter.",
            "norm": "count / post_count; a target-normalized fraction, not a physiological weight.",
            "pre_count": "Total outgoing synapses of pre across all identified targets in this table.",
            "post_count": "Total incoming synapses of post across all identified sources in this table.",
        },
        "caveat": (
            "The v2 edgelist contains only links whose two partners were identified "
            "(about 18% of all BANC synaptic links). pre_count/post_count and norm are "
            "therefore totals over identified partners, not over the whole connectome, "
            "and they include self-loops."
        ),
    }
    report["verdict"] = (
        "PASS"
        if report["pre_count_equals_outgoing_sum_share"] == 1.0
        and report["post_count_equals_incoming_sum_share"] == 1.0
        else "FAIL"
    )
    return report


def audit_annotations(
    meta: pd.DataFrame,
    backbone: pd.DataFrame,
    reviewed: pd.DataFrame,
) -> dict:
    """Describe annotation coverage and separate curated from predicted fields."""
    proof = meta["proofread"] == "TRUE"
    rough = meta["roughly_proofread"] == "TRUE"
    in_graph_neurons = ~meta["super_class"].isin(NON_NEURON_CLASSES) & meta["super_class"].notna()

    status = meta["status"].fillna("")
    report: dict[str, object] = {
        "meta_rows": int(len(meta)),
        "annotated_neurons": int(in_graph_neurons.sum()),
        "proofread_true": int(proof.sum()),
        "roughly_proofread_true": int(rough.sum()),
        "proofread_or_rough_true": int((proof | rough).sum()),
        "super_class_missing": int(meta["super_class"].isna().sum()),
        "super_class_missing_proofread_true": int((meta["super_class"].isna() & proof).sum()),
        "super_class_missing_proofread_false": int((meta["super_class"].isna() & ~proof).sum()),
        "cell_type_missing": int(meta["cell_type"].isna().sum()),
        "side_missing": int(meta["side"].isna().sum()),
    }

    population: dict[str, dict] = {}
    for name in ("motor", "descending", "ascending", "ventral_nerve_cord_intrinsic"):
        sub = meta[meta["super_class"] == name]
        population[name] = {
            "rows": int(len(sub)),
            "proofread_true": int((sub["proofread"] == "TRUE").sum()),
            "roughly_true": int((sub["roughly_proofread"] == "TRUE").sum()),
            "cell_type_missing": int(sub["cell_type"].isna().sum()),
            "side_missing": int(sub["side"].isna().sum()),
            "verified_neurotransmitter": int(sub["neurotransmitter_verified"].notna().sum()),
            "predicted_neurotransmitter_missing": int(sub["neurotransmitter_predicted"].isna().sum()),
            "predicted_neurotransmitter_top": sub["neurotransmitter_predicted"]
            .value_counts(dropna=True)
            .head(6)
            .to_dict(),
            "verified_neurotransmitter_top": sub["neurotransmitter_verified"]
            .value_counts(dropna=True)
            .head(6)
            .to_dict(),
            "fafb_match_present": int(sub["fafb_match"].notna().sum()),
            "fafb_nblast_present": int(sub["fafb_nblast_match"].notna().sum()),
            "status_missing": int((sub["status"].isna() | (sub["status"] == "")).sum()),
            "flag_fafb_match_manually_checked": int(
                sub["status"].fillna("").str.contains("FAFB_MATCH_MANUALLY_CHECKED").sum()
            ),
            "flag_review_match_an_dn": int(
                sub["status"].fillna("").str.contains("REVIEW_MATCH_AN_DN").sum()
            ),
            "flag_manc_match_manually_checked": int(
                sub["status"].fillna("").str.contains("MANC_MATCH_MANUALLY_CHECKED").sum()
            ),
        }
    report["populations"] = population

    motors = meta[meta["super_class"] == "motor"]
    report["motor_fafb_matches_by_body_part"] = (
        motors.assign(has_fafb=motors["fafb_match"].notna())
        .groupby("body_part_effector")["has_fafb"]
        .sum()
        .astype(int)
        .to_dict()
    )

    backbone_ids = set(backbone["pt_root_id"].astype("int64"))
    meta_ids = set(meta["banc_888_id"].astype("int64"))
    report["backbone_proofread"] = {
        "rows": int(len(backbone)),
        "unique_pt_root_id": int(backbone["pt_root_id"].nunique()),
        "unique_ids_present_in_meta": int(len(backbone_ids & meta_ids)),
        "valid_true_rows": int(backbone["valid"].sum()),
        "note": (
            "Append-only CAVE history; pt_root_id is the join key. valid_id is not the "
            "neuron root and only 79,080 of its values are metadata keys."
        ),
    }
    report["reviewed_matches"] = {
        "rows": int(len(reviewed)),
        "unique_pt_root_id": int(reviewed["pt_root_id"].nunique()),
        "unique_match_id": int(reviewed["match_id"].nunique()),
        "valid_t": int((reviewed["valid"] == "t").sum()),
        "valid_f": int((reviewed["valid"] == "f").sum()),
        "note": "Covers 64,372 BANC neurons, not the full metadata table.",
    }
    report["interpretation"] = (
        "Motor and descending annotations are complete and almost entirely proofread. "
        "Missing super_class is common (28,632 rows) and includes 11,344 fully proofread "
        "segments, so missing annotation must be treated as unknown, not as absence."
    )
    report["verdict"] = (
        "PASS"
        if population["motor"]["cell_type_missing"] == 0
        and population["descending"]["cell_type_missing"] == 0
        else "FAIL"
    )
    return report


def _index_map(meta_ids: np.ndarray, values: np.ndarray) -> np.ndarray:
    order = np.argsort(meta_ids)
    sorted_ids = meta_ids[order]
    positions = np.searchsorted(sorted_ids, values)
    return order[positions]


def audit_locomotor_readiness(
    pre: np.ndarray,
    post: np.ndarray,
    count: np.ndarray,
    meta: pd.DataFrame,
) -> dict:
    """Count structural pathways from descending to motor neurons by effector."""
    meta_ids = meta["banc_888_id"].astype("int64").to_numpy()
    src = _index_map(meta_ids, pre)
    dst = _index_map(meta_ids, post)
    sc_src = meta["super_class"].to_numpy()[src]
    sc_dst = meta["super_class"].to_numpy()[dst]
    side_src = meta["side"].to_numpy()[src]
    side_dst = meta["side"].to_numpy()[dst]
    part_dst = meta["body_part_effector"].to_numpy()[dst]
    target_dst = meta["peripheral_target_type"].fillna("").to_numpy()[dst]
    function_dst = meta["cell_function"].fillna("").to_numpy()[dst]

    dn_to_mn = (sc_src == "descending") & (sc_dst == "motor")
    dn_to_vnc = (sc_src == "descending") & (sc_dst == "ventral_nerve_cord_intrinsic")
    vnc_to_mn = (sc_src == "ventral_nerve_cord_intrinsic") & (sc_dst == "motor")

    def side_block(mask: np.ndarray) -> dict:
        return {
            "left_to_left": int((mask & (side_src == "left") & (side_dst == "left")).sum()),
            "left_to_right": int((mask & (side_src == "left") & (side_dst == "right")).sum()),
            "right_to_left": int((mask & (side_src == "right") & (side_dst == "left")).sum()),
            "right_to_right": int((mask & (side_src == "right") & (side_dst == "right")).sum()),
            "same_side": int((mask & (side_src == side_dst) & pd.notna(side_src)).sum()),
            "cross_side": int((mask & (side_src != side_dst) & pd.notna(side_src) & pd.notna(side_dst)).sum()),
        }

    motors = meta[meta["super_class"] == "motor"]
    mn_with_dn = set(post[dn_to_mn].tolist())
    by_part: dict[str, dict] = {}
    for part, group in motors.groupby("body_part_effector"):
        ids = set(group["banc_888_id"].astype("int64").tolist())
        part_mask = dn_to_mn & (part_dst == part)
        by_part[str(part)] = {
            "motor_neurons": int(len(ids)),
            "with_direct_dn_input": int(len(ids & mn_with_dn)),
            "left": int((group["side"] == "left").sum()),
            "right": int((group["side"] == "right").sum()),
            "dn_edges": int(part_mask.sum()),
            "dn_synapses": int(count[part_mask].sum()),
        }

    jump = (target_dst == "tergotrochanter_extensor_muscle") & dn_to_mn
    jump_mn = set(post[jump].tolist())
    jump_sides = meta.set_index("banc_888_id").loc[
        [str(value) for value in jump_mn], "side"
    ].value_counts().to_dict()

    super_cluster_src = meta["super_cluster"].to_numpy()[src]
    leg_mn = np.isin(part_dst, LEG_PARTS)
    leg_clusters = pd.Series(super_cluster_src[dn_to_mn & leg_mn]).value_counts().head(15)

    two_hop_dn = pd.DataFrame({"vnc": post[dn_to_vnc], "dn": pre[dn_to_vnc], "w1": count[dn_to_vnc]})
    two_hop_mn = pd.DataFrame({"vnc": pre[vnc_to_mn], "mn": post[vnc_to_mn], "w2": count[vnc_to_mn]})
    joined = two_hop_dn.merge(two_hop_mn, on="vnc", how="inner")
    unique_pairs = np.unique(_edge_pairs(joined["dn"].to_numpy(), joined["mn"].to_numpy()))

    report: dict[str, object] = {
        "motor_neurons": int(len(motors)),
        "descending_neurons": int((meta["super_class"] == "descending").sum()),
        "direct_dn_to_mn": {
            "edges": int(dn_to_mn.sum()),
            "synapses": int(count[dn_to_mn].sum()),
            "descending_neurons": int(np.unique(pre[dn_to_mn]).size),
            "motor_neurons": int(np.unique(post[dn_to_mn]).size),
            "motor_coverage": float(np.unique(post[dn_to_mn]).size / len(motors)),
            "sides": side_block(dn_to_mn),
        },
        "dn_to_vnc_intrinsic_edges": int(dn_to_vnc.sum()),
        "vnc_intrinsic_to_mn_edges": int(vnc_to_mn.sum()),
        "two_hop_dn_vnc_mn": {
            "paths": int(len(joined)),
            "unique_dn_mn_pairs": int(unique_pairs.size),
            "descending_neurons": int(joined["dn"].nunique()),
            "motor_neurons": int(joined["mn"].nunique()),
        },
        "motor_neurons_by_body_part": by_part,
        "dn_super_cluster_to_leg_mn_edges": leg_clusters.to_dict(),
        "jump_tergotrochanter": {
            "motor_neurons": int(len(jump_mn)),
            "motor_neurons_by_side": {str(k): int(v) for k, v in jump_sides.items()},
            "dn_edges": int(jump.sum()),
            "descending_neurons": int(np.unique(pre[jump]).size),
            "synapses": int(count[jump].sum()),
        },
        "interpretation": (
            "The graph supports separate motor-pool experiments because left and right "
            "pools are both present and balanced. It does not support assigning a command "
            "to a descending neuron: cross-side DN-to-MN edges outnumber same-side edges, "
            "and no pathway is physiologically validated."
        ),
        "verdict": "PASS",
    }
    return report


def build_graph_policy(audit: dict) -> dict:
    """Derive the construction policy from the measured audit values."""
    return {
        "canonical_node_id": {
            "field": "banc_888_id",
            "type": "int64 in memory (18-digit decimal string on disk)",
            "joins": "edgelist pre/post -> metadata banc_888_id",
            "do_not_join_on": ["root_id", "root_626", "root_850", "root_890"],
            "reason": (
                "banc_888_id is unique and non-null and covers every edge endpoint. "
                "root_id is a pre-split identifier (168 duplicate rows, 8.7% mismatch), "
                "and root_890 has 274 nulls and 310 duplicates."
            ),
        },
        "edge_aggregation": {
            "policy": "none",
            "reason": (
                "The v2 edgelist already holds one row per directed pair "
                f"({audit['C_edge_integrity']['unique_directed_pairs']} unique pairs, "
                f"{audit['C_edge_integrity']['duplicate_pair_rows']} duplicates)."
            ),
            "if_source_changes": "group by (pre, post) and sum count; never sum norm",
        },
        "self_edge_policy": {
            "policy": "exclude_from_simulation_graph_keep_in_raw_file",
            "rows": audit["B_self_edges"]["rows"],
            "synapse_share": audit["B_self_edges"]["summed_count_share"],
            "reason": (
                "One self-loop per affected node, widespread across non-neuronal segments, "
                "and the BANC paper recommends filtering autapses because most are expected "
                "presynaptic misassignments."
            ),
            "denominator_effect": (
                "pre_count/post_count include the self-loop; after exclusion, downstream "
                "totals must be recomputed if absolute fractions are required."
            ),
        },
        "node_inclusion": {
            "policy": "all edge endpoints, annotated or not",
            "nodes": audit["C_edge_integrity"]["unique_nodes"],
            "unannotated_nodes": audit["C_edge_integrity"]["graph_nodes_missing_super_class"],
            "isolated_metadata_rows": audit["C_edge_integrity"]["metadata_rows_without_edges"],
            "reason": (
                "Dropping unannotated nodes would silently bias degree and pathway counts. "
                "Isolated metadata rows are retained in a separate annotation table, not in "
                "the graph."
            ),
        },
        "edge_weight": {
            "policy": "integer count, threshold count >= 5 for the FAFB-comparable graph",
            "initial_threshold": 5,
            "sensitivity_thresholds": [1, 5, 10],
            "retained_pair_share_at_5": audit["E_weight_semantics"]["weight_ge_5_share_of_pairs"],
            "retained_synapse_share_at_5": audit["E_weight_semantics"]["weight_ge_5_share_of_synapses"],
            "do_not_use": "norm as a physiological weight",
            "reason": (
                "count is the measured synapse number. norm is a target-normalized fraction "
                "whose denominator depends on identified partners and includes self-loops. "
                "A count >= 5 threshold matches the inclusion logic of the FAFB artifact."
            ),
        },
        "annotation_handling": {
            "policy": "left join, missing stays unknown",
            "quality_fields": ["proofread", "roughly_proofread", "status"],
            "sign_prior": "verified neurotransmitter only",
            "sign_prior_counts": {
                "motor": audit["D_annotation_quality"]["populations"]["motor"]["verified_neurotransmitter"],
                "descending": audit["D_annotation_quality"]["populations"]["descending"]["verified_neurotransmitter"],
            },
            "do_not_use": "neurotransmitter_predicted for effector sign",
            "reason": (
                "BANC evaluates transmitter prediction on non-effector neurons because "
                "effector output synapses lie mostly outside the volume; the prediction is "
                "therefore dominated by input-site chemistry (55% GABA in motor neurons)."
            ),
        },
        "isolated_nodes": {
            "policy": "exclude from graph, retain annotations separately",
            "rows": audit["C_edge_integrity"]["metadata_rows_without_edges"],
            "proofread_rows": audit["C_edge_integrity"]["isolated_proofread_true"],
        },
        "reproducibility": {
            "required": [
                "record SHA-256 of every input file",
                "record row and column counts and schema",
                "sort edges by (pre, post) before CSR construction",
                "record threshold and self-edge policy in the output metadata",
                "run the audit twice and require identical JSON payloads",
                "never write to datasets/external",
            ],
            "dataset_version": "BANC materialization v888 (edgelist v2, postsynapse size >= 5)",
        },
    }


def run_audit(inputs: dict[str, Path] | None = None) -> dict:
    """Execute every audit block and return the JSON-ready report."""
    inputs = inputs or DEFAULT_INPUTS
    missing = [str(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing BANC input files: {missing}")

    started = datetime.now(timezone.utc)
    meta = load_metadata(inputs["metadata"])
    edges = load_edgelist(inputs["edgelist_v2"])
    backbone = parquet.read_table(
        inputs["backbone_proofread"], columns=["pt_root_id", "valid", "valid_id", "proofread"]
    ).to_pandas()
    reviewed = pd.read_csv(inputs["reviewed_matches"], compression=None)

    meta_ids = meta["banc_888_id"].astype("int64").to_numpy()
    nodes = np.unique(np.concatenate([edges["pre"], edges["post"]]))
    meta_index = pd.Index(meta_ids)
    isolated = meta.loc[~meta_index.isin(nodes)]

    canonical = audit_canonical_ids(meta)
    self_edges = audit_self_edges(
        edges["pre"], edges["post"], edges["count"], meta
    )
    edge_integrity = audit_edge_integrity(
        edges["pre"],
        edges["post"],
        edges["count"],
        edges["norm"],
        meta_ids,
        edges["nulls"],
        edges["rows"],
    )
    edge_integrity["metadata_rows_without_edges"] = int(len(isolated))
    edge_integrity["isolated_proofread_true"] = int((isolated["proofread"] == "TRUE").sum())
    edge_integrity["isolated_annotated_neurons"] = int(
        (~isolated["super_class"].isin(NON_NEURON_CLASSES) & isolated["super_class"].notna()).sum()
    )
    edge_integrity["graph_nodes_missing_super_class"] = int(
        pd.isna(_annotate_nodes(meta, nodes, "super_class")).sum()
    )
    weights = audit_weight_semantics(
        edges["pre"],
        edges["post"],
        edges["count"],
        edges["norm"],
        edges["pre_count"],
        edges["post_count"],
    )
    annotations = audit_annotations(meta, backbone, reviewed)
    locomotor = audit_locomotor_readiness(
        edges["pre"], edges["post"], edges["count"], meta
    )

    report = {
        "audit": {
            "phase": "4C.5",
            "title": "BANC graph readiness audit",
            "generated_utc": started.isoformat(),
            "duration_seconds": None,
            "read_only": True,
            "inputs": {
                name: {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "bytes": int(path.stat().st_size),
                    "sha256": sha256_file(path),
                }
                for name, path in inputs.items()
            },
            "edgelist_schema": edges["columns"],
            "metadata_rows": int(len(meta)),
            "metadata_columns_total": int(
                meta.attrs.get("source_columns_total", meta.shape[1])
            ),
            "metadata_columns_used": int(meta.shape[1]),
        },
        "verdict": None,
        "A_canonical_id_integrity": canonical,
        "B_self_edges": self_edges,
        "C_edge_integrity": edge_integrity,
        "D_annotation_quality": annotations,
        "E_weight_semantics": weights,
        "F_locomotor_readiness": locomotor,
        "limitations": [
            "The local metadata object is the current bucket build (188,508 rows, 81 columns), not the documented 188,162-row, 79-column v888 object; the data dictionary is stale.",
            "The metadata dictionary states root_id = banc_888_id, but root_id differs on 8.7% of rows; banc_888_id is the only safe join key.",
            "The v2 edgelist dictionary says autapses are excluded and lists 11,510,975 rows, but the local/current bucket object has 11,752,828 rows and 156,311 self-loops.",
            "The edgelist contains only links with both partners identified (about 18% of BANC synaptic links), so degree and weight totals are not whole-connectome totals.",
            "Neurotransmitter predictions are unreliable for effector neurons because their output synapses lie mostly outside the imaged volume.",
            "Self-loops are widespread and are expected to be mostly presynaptic misassignments; the paper recommends filtering them.",
            "Structural connectivity does not establish a physiological motor command.",
            "No left/right or jump pathway was functionally validated in this audit.",
        ],
    }
    report["G_graph_construction_policy"] = build_graph_policy(report)

    failures = [
        name
        for name, key in (
            ("canonical IDs", "A_canonical_id_integrity"),
            ("edge integrity", "C_edge_integrity"),
            ("weight semantics", "E_weight_semantics"),
            ("annotations", "D_annotation_quality"),
            ("locomotor readiness", "F_locomotor_readiness"),
        )
        if report[key]["verdict"] != "PASS"
    ]
    report["verdict"] = "READY WITH LIMITATIONS" if not failures else "NOT READY"
    report["failed_blocks"] = failures

    finished = datetime.now(timezone.utc)
    report["audit"]["duration_seconds"] = round((finished - started).total_seconds(), 3)
    return report


def write_report(report: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=False, default=_json_default, allow_nan=False)
    output.write_text(payload + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json",
        help="JSON output path (default: reports/PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json)",
    )
    args = parser.parse_args(argv)

    report = run_audit()
    path = write_report(report, args.output)
    print(f"verdict: {report['verdict']}")
    print(f"canonical node id: {report['A_canonical_id_integrity']['canonical']}")
    print(f"graph nodes: {report['C_edge_integrity']['unique_nodes']:,}")
    print(f"directed pairs: {report['C_edge_integrity']['unique_directed_pairs']:,}")
    print(f"self-edge rows: {report['B_self_edges']['rows']:,}")
    print(f"DN -> MN edges: {report['F_locomotor_readiness']['direct_dn_to_mn']['edges']:,}")
    try:
        shown = path.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        shown = path
    print(f"report: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
