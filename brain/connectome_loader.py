"""Reconstruct the FAFB connectome from the audited FlyWire tables.

Graph semantics (fixed by the Phase 0 audit):

* nodes are all 139,255 root IDs in ``neurons.csv.gz``, indexed by their
  position in ascending root-ID order;
* edges are directed ``pre -> post`` pairs;
* an edge weight is the sum of ``syn_count`` across neuropils;
* the shipped filtered table already contains every row of every pair whose
  summed strength is >= 5, so pair weights are recovered by summing rows.
  The loader never applies ``syn_count >= 5`` per row.

Run ``python -m brain.connectome_loader`` to rebuild
``datasets/processed/connectome.npz``, ``nodes.csv.gz`` and the report.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "datasets" / "raw"
OUT_DIR = PROJECT_ROOT / "datasets" / "processed"
MANIFEST_PATH = PROJECT_ROOT / "datasets" / "manifest.json"

NEURONS_CSV = RAW_DIR / "neurons" / "neurons.csv.gz"
NAMES_CSV = RAW_DIR / "neurons" / "names.csv.gz"
COORDS_CSV = RAW_DIR / "neurons" / "coordinates.csv.gz"
CELL_STATS_CSV = RAW_DIR / "neurons" / "cell_stats.csv.gz"
CLASSIFICATION_CSV = RAW_DIR / "annotations" / "classification.csv.gz"
CELL_TYPES_CSV = RAW_DIR / "annotations" / "consolidated_cell_types.csv.gz"
LABELS_CSV = RAW_DIR / "annotations" / "labels.csv.gz"
CONNECTIVITY_TAGS_CSV = RAW_DIR / "connections" / "connectivity_tags.csv.gz"
FILTERED_CSV = RAW_DIR / "connections" / "connections_princeton.csv.gz"

DEFAULT_OUT = OUT_DIR / "connectome.npz"
DEFAULT_NODES_OUT = OUT_DIR / "nodes.csv.gz"
DEFAULT_REPORT = OUT_DIR / "connectome_report.json"
DEFAULT_THRESHOLD = 5
CHUNK_ROWS = 1_000_000

AUDIT_EXPECTED = {
    "n_nodes": 139_255,
    "n_edges": 3_732_460,
    "n_synapses": 50_666_648,
    "rows": 5_342_446,
    "reciprocal_directed": 620_180,
    "reciprocal_unordered": 310_090,
    "used_nodes": 138_584,
}

POSITION_RE = r"^\s*\[\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\]\s*$"


# ---------------------------------------------------------------------------
# graph container
# ---------------------------------------------------------------------------


@dataclass
class Connectome:
    root_ids: np.ndarray
    out_indptr: np.ndarray
    edge_src: np.ndarray
    edge_dst: np.ndarray
    edge_weight: np.ndarray
    in_indptr: np.ndarray
    in_edge_idx: np.ndarray
    positions: np.ndarray
    position_mask: np.ndarray
    nt_code: np.ndarray
    super_class_code: np.ndarray
    class_code: np.ndarray
    side_code: np.ndarray
    flow_code: np.ndarray
    vocabulary: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.root_ids)
        m = len(self.edge_dst)
        if n == 0:
            raise ValueError("empty connectome")
        if not np.all(np.diff(self.root_ids) > 0):
            raise ValueError("root_ids must be unique and ascending")
        if self.out_indptr.shape != (n + 1,) or self.in_indptr.shape != (n + 1,):
            raise ValueError("indptr length must equal n_nodes + 1")
        if not np.all(self.out_indptr[:-1] <= self.out_indptr[1:]):
            raise ValueError("out_indptr must be non-decreasing")
        if not np.all(self.in_indptr[:-1] <= self.in_indptr[1:]):
            raise ValueError("in_indptr must be non-decreasing")
        if self.out_indptr[-1] != m or self.in_indptr[-1] != m:
            raise ValueError("indptr tails must equal the edge count")
        for name, arr, size in (
            ("edge_src", self.edge_src, n),
            ("edge_dst", self.edge_dst, n),
            ("in_edge_idx", self.in_edge_idx, m),
        ):
            if len(arr) and (int(arr.min()) < 0 or int(arr.max()) >= size):
                raise ValueError(f"{name} contains out-of-range indices")
        if np.any(self.edge_weight < 1):
            raise ValueError("edge weights must be positive")
        if self.positions.shape != (n, 3):
            raise ValueError("positions must have shape (n, 3)")

    @property
    def n_nodes(self) -> int:
        return len(self.root_ids)

    @property
    def n_edges(self) -> int:
        return len(self.edge_dst)

    @property
    def n_synapses(self) -> int:
        return int(self.edge_weight.sum(dtype=np.int64))

    def out_edges(self, node: int) -> tuple[np.ndarray, np.ndarray]:
        start, stop = self.out_indptr[node], self.out_indptr[node + 1]
        return self.edge_dst[start:stop], self.edge_weight[start:stop]

    def in_edges(self, node: int) -> tuple[np.ndarray, np.ndarray]:
        start, stop = self.in_indptr[node], self.in_indptr[node + 1]
        rows = self.in_edge_idx[start:stop]
        return self.edge_src[rows], self.edge_weight[rows]

    def node_index(self, root_id: int) -> int:
        idx = int(np.searchsorted(self.root_ids, root_id))
        if idx >= self.n_nodes or int(self.root_ids[idx]) != int(root_id):
            raise KeyError(f"root ID {root_id} is not part of the reference set")
        return idx

    def save(self, path: Path) -> None:
        path = Path(path)
        tmp = path.with_name(path.stem + ".tmp.npz")
        arrays = {
            "root_ids": self.root_ids,
            "out_indptr": self.out_indptr,
            "edge_src": self.edge_src,
            "edge_dst": self.edge_dst,
            "edge_weight": self.edge_weight,
            "in_indptr": self.in_indptr,
            "in_edge_idx": self.in_edge_idx,
            "positions": self.positions,
            "position_mask": self.position_mask,
            "nt_code": self.nt_code,
            "super_class_code": self.super_class_code,
            "class_code": self.class_code,
            "side_code": self.side_code,
            "flow_code": self.flow_code,
            "vocabulary_json": np.array(json.dumps(self.vocabulary)),
            "meta_json": np.array(json.dumps(self.meta)),
        }
        np.savez_compressed(tmp, **arrays)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path) -> "Connectome":
        with np.load(Path(path), allow_pickle=False) as data:
            payload = {key: data[key] for key in data.files}
        vocabulary = json.loads(str(payload.pop("vocabulary_json")))
        meta = json.loads(str(payload.pop("meta_json")))
        return cls(vocabulary=vocabulary, meta=meta, **payload)


def load_connectome(path: Path = DEFAULT_OUT) -> Connectome:
    """Load a previously built connectome artifact."""
    return Connectome.load(path)


# ---------------------------------------------------------------------------
# node table
# ---------------------------------------------------------------------------


def _encode(series: pd.Series) -> tuple[np.ndarray, list[str]]:
    clean = series.dropna().astype(str)
    vocab = sorted(clean.unique().tolist())
    mapping = {value: index for index, value in enumerate(vocab)}
    codes = series.map(mapping).fillna(-1).astype(np.int16).to_numpy()
    return codes, vocab


def _merge_unique(
    nodes: pd.DataFrame, path: Path, columns: list[str]
) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=columns)
    if frame["root_id"].duplicated().any():
        raise ValueError(f"{path.name} has duplicate root IDs")
    return nodes.merge(
        frame, on="root_id", how="left", validate="one_to_one", sort=False
    )


def _load_positions(root_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """Centroid of unique coordinate rows per neuron, in root_id order.

    Exact duplicate rows are removed first; a neuron's position is the mean of
    its remaining distinct sampled coordinates.  Coordinates are soma-region
    samples, not synapse positions.
    """
    frame = pd.read_csv(COORDS_CSV, usecols=["root_id", "position"])
    coordinate_rows = len(frame)
    parsed = frame["position"].str.extract(POSITION_RE).astype(np.float64)
    parsed.columns = ["x", "y", "z"]
    frame = pd.concat([frame[["root_id"]], parsed], axis=1).dropna()
    parsed_rows = len(frame)
    frame = frame.drop_duplicates()
    positions = frame.groupby("root_id")[["x", "y", "z"]].mean()
    aligned = positions.reindex(root_ids).to_numpy(dtype=np.float32)
    mask = ~np.isnan(aligned).any(axis=1)
    stats = {
        "coordinate_rows": int(coordinate_rows),
        "parsed_rows": int(parsed_rows),
        "unparsed_rows": int(coordinate_rows - parsed_rows),
        "unique_rows_used": int(len(frame)),
        "exact_duplicate_rows_removed": int(parsed_rows - len(frame)),
        "neurons_with_position": int(mask.sum()),
        "neurons_without_position": int((~mask).sum()),
    }
    return aligned, mask, stats


def load_node_table() -> tuple[pd.DataFrame, dict]:
    """Build the 139,255-node annotation table and numeric code arrays."""
    neurons = pd.read_csv(NEURONS_CSV)
    if neurons["root_id"].duplicated().any():
        raise ValueError("neurons.csv.gz has duplicate root IDs")
    root_ids = np.sort(neurons["root_id"].to_numpy(dtype=np.int64))
    nodes = pd.DataFrame({"root_id": root_ids})
    nodes = nodes.merge(
        neurons, on="root_id", how="left", validate="one_to_one", sort=False
    )
    nodes = _merge_unique(nodes, NAMES_CSV, ["root_id", "name"])
    nodes = _merge_unique(
        nodes,
        CLASSIFICATION_CSV,
        ["root_id", "flow", "super_class", "class", "sub_class", "hemilineage", "side", "nerve"],
    )
    nodes = _merge_unique(
        nodes, CELL_TYPES_CSV, ["root_id", "primary_type", "additional_type(s)"]
    ).rename(columns={"additional_type(s)": "additional_types"})
    nodes = _merge_unique(
        nodes, CELL_STATS_CSV, ["root_id", "length_nm", "area_nm", "size_nm"]
    )
    nodes = _merge_unique(
        nodes, CONNECTIVITY_TAGS_CSV, ["root_id", "connectivity_tag"]
    )

    labels = pd.read_csv(LABELS_CSV, usecols=["root_id", "label"]).dropna()
    labels = labels.drop_duplicates().sort_values(["root_id", "label"])
    label_counts = labels.groupby("root_id").size().rename("label_count")
    label_text = labels.groupby("root_id")["label"].agg("; ".join).rename("labels")
    nodes = nodes.merge(
        pd.concat([label_counts, label_text], axis=1),
        left_on="root_id",
        right_index=True,
        how="left",
        validate="one_to_one",
    )
    nodes["label_count"] = nodes["label_count"].fillna(0).astype(np.int32)
    nodes["labels"] = nodes["labels"].fillna("")

    positions, position_mask, position_stats = _load_positions(root_ids)
    nodes["x"], nodes["y"], nodes["z"] = (
        positions[:, 0],
        positions[:, 1],
        positions[:, 2],
    )
    nodes.insert(1, "node_index", np.arange(len(nodes), dtype=np.int64))

    columns = [
        "node_index", "root_id", "name", "group", "nt_type", "nt_type_score",
        "da_avg", "ser_avg", "gaba_avg", "glut_avg", "ach_avg", "oct_avg",
        "flow", "super_class", "class", "sub_class", "hemilineage", "side",
        "nerve", "primary_type", "additional_types", "length_nm", "area_nm",
        "size_nm", "connectivity_tag", "label_count", "labels", "x", "y", "z",
    ]
    nodes = nodes[columns]

    missing = nodes[["root_id", "node_index"]].isna().sum().sum()
    if missing:
        raise ValueError("node identity columns contain nulls")

    nt_code, nt_vocab = _encode(nodes["nt_type"])
    super_code, super_vocab = _encode(nodes["super_class"])
    class_code, class_vocab = _encode(nodes["class"])
    side_code, side_vocab = _encode(nodes["side"])
    flow_code, flow_vocab = _encode(nodes["flow"])

    arrays = {
        "positions": positions,
        "position_mask": position_mask,
        "nt_code": nt_code,
        "super_class_code": super_code,
        "class_code": class_code,
        "side_code": side_code,
        "flow_code": flow_code,
        "vocabulary": {
            "nt_type": nt_vocab,
            "super_class": super_vocab,
            "class": class_vocab,
            "side": side_vocab,
            "flow": flow_vocab,
        },
        "position_stats": position_stats,
        "nt_missing": int((nodes["nt_type"].isna()).sum()),
    }
    return nodes, arrays


# ---------------------------------------------------------------------------
# edge reconstruction
# ---------------------------------------------------------------------------


def _read_edges(
    root_ids: np.ndarray, csv_path: Path, chunksize: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(root_ids)
    src_parts: list[np.ndarray] = []
    dst_parts: list[np.ndarray] = []
    syn_parts: list[np.ndarray] = []
    rows = 0
    for chunk in pd.read_csv(
        csv_path,
        usecols=["pre_root_id", "post_root_id", "syn_count"],
        dtype={
            "pre_root_id": np.int64,
            "post_root_id": np.int64,
            "syn_count": np.int32,
        },
        chunksize=chunksize,
    ):
        pre = chunk["pre_root_id"].to_numpy()
        post = chunk["post_root_id"].to_numpy()
        syn = chunk["syn_count"].to_numpy()
        if len(pre) == 0:
            continue
        if np.any(syn <= 0):
            raise ValueError(f"{csv_path.name} contains non-positive syn_count")
        pre_idx = np.searchsorted(root_ids, pre)
        post_idx = np.searchsorted(root_ids, post)
        pre_ok = (pre_idx < n) & (root_ids[np.minimum(pre_idx, n - 1)] == pre)
        post_ok = (post_idx < n) & (root_ids[np.minimum(post_idx, n - 1)] == post)
        if not pre_ok.all() or not post_ok.all():
            bad = pre[~pre_ok][:5].tolist() + post[~post_ok][:5].tolist()
            raise ValueError(f"{csv_path.name} has root IDs outside the reference: {bad}")
        src_parts.append(pre_idx.astype(np.int32))
        dst_parts.append(post_idx.astype(np.int32))
        syn_parts.append(syn)
        rows += len(pre)
    if not src_parts:
        raise ValueError(f"{csv_path.name} contains no rows")
    return (
        np.concatenate(src_parts),
        np.concatenate(dst_parts),
        np.concatenate(syn_parts),
    )


def aggregate_pairs(
    src: np.ndarray, dst: np.ndarray, syn: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Sum syn_count per directed pair and return sorted unique pairs."""
    keys = (src.astype(np.uint64) << np.uint64(32)) | dst.astype(np.uint64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    src = src[order]
    dst = dst[order]
    syn = syn[order]
    del order

    is_new = np.empty(len(keys), dtype=bool)
    is_new[0] = True
    is_new[1:] = keys[1:] != keys[:-1]
    starts = np.flatnonzero(is_new)
    del is_new

    n_rows = len(syn)
    weights = np.add.reduceat(syn, starts, dtype=np.int64)
    pair_src = src[starts]
    pair_dst = dst[starts]
    unique_keys = keys[starts]
    del keys, src, dst, syn
    gc.collect()

    if np.any(pair_src == pair_dst):
        raise ValueError("self-connections are present")
    if weights.max() > np.iinfo(np.int32).max:
        raise ValueError("pair weight exceeds int32 range")
    weights = weights.astype(np.int32)
    stats = {
        "unique_keys": unique_keys,
        "rows_per_pair_max": int(np.diff(np.append(starts, n_rows)).max()),
    }
    return pair_src, pair_dst, weights, stats


def build_edges(
    root_ids: np.ndarray, csv_path: Path, threshold: int, chunksize: int
) -> tuple[dict, dict]:
    n = len(root_ids)
    start = time.perf_counter()
    src, dst, syn = _read_edges(root_ids, csv_path, chunksize)
    rows = len(src)
    pair_src, pair_dst, weights, pair_stats = aggregate_pairs(src, dst, syn)
    del src, dst, syn
    gc.collect()
    n_edges = len(weights)

    weight_min = int(weights.min())
    if weight_min < threshold:
        raise ValueError(
            f"filtered table produced a pair weight of {weight_min} < {threshold}; "
            "the source is not the audited pair-level filtered table"
        )

    key = pair_stats["unique_keys"]
    rev = (key << np.uint64(32)) | (key >> np.uint64(32))
    pos = np.searchsorted(key, rev)
    pos_clipped = np.minimum(pos, n_edges - 1)
    reciprocal_mask = (pos < n_edges) & (key[pos_clipped] == rev)
    reciprocal_directed = int(reciprocal_mask.sum())
    if reciprocal_directed % 2:
        raise ValueError("reciprocal count is odd; reverse pairs are inconsistent")
    del rev, pos, pos_clipped, reciprocal_mask

    out_counts = np.bincount(pair_src, minlength=n).astype(np.int64)
    out_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(out_counts, out=out_indptr[1:])
    del out_counts

    in_order = np.argsort(pair_dst, kind="stable").astype(np.int32)
    in_counts = np.bincount(pair_dst, minlength=n).astype(np.int64)
    in_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(in_counts, out=in_indptr[1:])
    del in_counts

    edge_stats = {
        "source_rows": int(rows),
        "n_edges": int(n_edges),
        "n_synapses": int(weights.sum(dtype=np.int64)),
        "weight_min": weight_min,
        "weight_max": int(weights.max()),
        "weight_mean": float(weights.mean()),
        "rows_per_pair_max": pair_stats["rows_per_pair_max"],
        "reciprocal_directed": reciprocal_directed,
        "reciprocal_unordered": reciprocal_directed // 2,
        "self_connections": 0,
        "edge_build_seconds": round(time.perf_counter() - start, 2),
    }
    arrays = {
        "pair_src": pair_src,
        "pair_dst": pair_dst,
        "weights": weights,
        "out_indptr": out_indptr,
        "in_indptr": in_indptr,
        "in_order": in_order,
    }
    return arrays, edge_stats


# ---------------------------------------------------------------------------
# report and artifact verification
# ---------------------------------------------------------------------------


def _degree_summary(degrees: np.ndarray) -> dict:
    marks = (0, 25, 50, 75, 90, 95, 99, 100)
    return {
        "total": int(degrees.sum()),
        "mean": round(float(degrees.mean()), 3),
        "min": int(degrees.min()),
        "max": int(degrees.max()),
        "percentiles": {
            str(p): int(np.percentile(degrees, p)) for p in marks
        },
    }


def _audit_expectations() -> tuple[dict, dict]:
    expected = {
        "n_nodes": AUDIT_EXPECTED["n_nodes"],
        "n_edges": AUDIT_EXPECTED["n_edges"],
        "n_synapses": AUDIT_EXPECTED["n_synapses"],
        "source_rows": AUDIT_EXPECTED["rows"],
        "weight_min": 5,
        "weight_max": 2633,
        "reciprocal_directed": AUDIT_EXPECTED["reciprocal_directed"],
        "reciprocal_unordered": AUDIT_EXPECTED["reciprocal_unordered"],
        "used_nodes": AUDIT_EXPECTED["used_nodes"],
    }
    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        filtered = manifest.get("connections", {}).get("filtered", {})
        per_dataset = {
            item["name"]: item
            for item in manifest.get("cross_dataset", {}).get("per_dataset", [])
        }
        expected.update(
            {
                "n_nodes": manifest.get("cross_dataset", {}).get(
                    "reference_unique_ids", expected["n_nodes"]
                ),
                "n_edges": filtered.get("unique_pairs", expected["n_edges"]),
                "n_synapses": filtered.get(
                    "pair_synapse_total", expected["n_synapses"]
                ),
                "source_rows": filtered.get("rows", expected["source_rows"]),
                "weight_min": filtered.get(
                    "pair_synapse_min", expected["weight_min"]
                ),
                "weight_max": filtered.get(
                    "pair_synapse_max", expected["weight_max"]
                ),
                "reciprocal_directed": filtered.get(
                    "reciprocal_edges", expected["reciprocal_directed"]
                ),
                "reciprocal_unordered": filtered.get(
                    "unordered_reciprocal_pairs", expected["reciprocal_unordered"]
                ),
                "used_nodes": per_dataset.get(
                    "connections_princeton.csv.gz", {}
                ).get("unique_ids", expected["used_nodes"]),
            }
        )
    return expected, manifest


def verify_artifact(path: Path, edge_stats: dict, n_nodes: int) -> dict:
    graph = load_connectome(path)
    n = graph.n_nodes
    out_degree = np.bincount(graph.edge_src, minlength=n)
    in_degree = np.bincount(graph.edge_dst, minlength=n)
    in_dst_sorted = graph.edge_dst[graph.in_edge_idx]
    checks = {
        "n_nodes": graph.n_nodes == n_nodes,
        "n_edges": graph.n_edges == edge_stats["n_edges"],
        "n_synapses": graph.n_synapses == edge_stats["n_synapses"],
        "no_self_loops": bool(np.all(graph.edge_src != graph.edge_dst)),
        "weights_positive": bool(np.all(graph.edge_weight >= 1)),
        "out_csr_consistent": bool(
            np.array_equal(out_degree, np.diff(graph.out_indptr))
        ),
        "in_csr_consistent": bool(
            np.array_equal(in_degree, np.diff(graph.in_indptr))
        ),
        "in_order_sorted": bool(
            np.all(in_dst_sorted[:-1] <= in_dst_sorted[1:])
        ),
    }
    return {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "loaded": True,
        "checks": checks,
        "failures": [name for name, ok in checks.items() if not ok],
    }


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def build_report(
    node_df: pd.DataFrame,
    node_arrays: dict,
    edge_stats: dict,
    graph: Connectome,
    audit_expected: dict,
    roundtrip: dict | None,
    outputs: dict,
) -> dict:
    n = graph.n_nodes
    out_degree = np.diff(graph.out_indptr)
    in_degree = np.diff(graph.in_indptr)
    used = (out_degree > 0) | (in_degree > 0)
    isolated = ~used

    checks = [
        ("n_nodes", audit_expected["n_nodes"], graph.n_nodes),
        ("n_edges", audit_expected["n_edges"], graph.n_edges),
        ("n_synapses", audit_expected["n_synapses"], graph.n_synapses),
        ("source_rows", audit_expected["source_rows"], edge_stats["source_rows"]),
        ("weight_min", audit_expected["weight_min"], edge_stats["weight_min"]),
        ("weight_max", audit_expected["weight_max"], edge_stats["weight_max"]),
        (
            "reciprocal_directed",
            audit_expected["reciprocal_directed"],
            edge_stats["reciprocal_directed"],
        ),
        (
            "reciprocal_unordered",
            audit_expected["reciprocal_unordered"],
            edge_stats["reciprocal_unordered"],
        ),
        ("used_nodes", audit_expected["used_nodes"], int(used.sum())),
        ("self_connections", 0, edge_stats["self_connections"]),
        ("nodes_accounted_for", n, int(used.sum()) + int(isolated.sum())),
    ]
    check_rows = [
        {"name": name, "expected": expected, "actual": actual, "pass": expected == actual}
        for name, expected, actual in checks
    ]

    weight_counts = np.bincount(graph.edge_weight)
    top_weights = sorted(
        (
            {"synapses": int(weight), "edges": int(count)}
            for weight, count in enumerate(weight_counts)
            if count and weight > 0
        ),
        key=lambda item: item["edges"],
        reverse=True,
    )[:10]

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "connection_table": "datasets/raw/connections/connections_princeton.csv.gz",
            "reference_nodes": "datasets/raw/neurons/neurons.csv.gz",
            "audit_manifest": "datasets/manifest.json",
            "threshold": DEFAULT_THRESHOLD,
            "threshold_rule": (
                "keep every row of every directed pair whose summed syn_count "
                "across neuropils is >= 5; never filter individual rows"
            ),
            "edge_weight": "sum of syn_count across neuropils for one directed pair",
        },
        "node_index": {
            "n_nodes": graph.n_nodes,
            "rule": "0-based position in ascending root_id order",
            "annotated": int(node_df["nt_type"].notna().sum()),
            "nt_type_missing": node_arrays["nt_missing"],
            "with_position": int(graph.position_mask.sum()),
            "without_position": int((~graph.position_mask).sum()),
            "position_rule": (
                "mean of distinct sampled coordinate rows per neuron "
                "(not synapse positions)"
            ),
            "position_stats": node_arrays["position_stats"],
        },
        "edges": {
            "n_edges": graph.n_edges,
            "n_synapses": graph.n_synapses,
            "weight_min": edge_stats["weight_min"],
            "weight_max": edge_stats["weight_max"],
            "weight_mean": round(edge_stats["weight_mean"], 3),
            "source_rows": edge_stats["source_rows"],
            "rows_per_pair_max": edge_stats["rows_per_pair_max"],
            "self_connections": edge_stats["self_connections"],
            "most_common_weights": top_weights,
        },
        "degree": {
            "out": _degree_summary(out_degree),
            "in": _degree_summary(in_degree),
            "isolated_nodes": int(isolated.sum()),
            "isolated_root_id_samples": [
                int(value) for value in graph.root_ids[isolated][:10]
            ],
        },
        "reciprocity": {
            "directed_pairs_with_reverse": edge_stats["reciprocal_directed"],
            "fraction": round(
                edge_stats["reciprocal_directed"] / graph.n_edges, 6
            ),
            "unordered_reciprocal_pairs": edge_stats["reciprocal_unordered"],
        },
        "audit_cross_check": {
            "status": "PASS" if all(row["pass"] for row in check_rows) else "FAIL",
            "checks": check_rows,
        },
        "artifact_roundtrip": roundtrip,
        "outputs": outputs,
    }
    return report


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def run(
    out: Path,
    nodes_out: Path,
    report_path: Path,
    threshold: int,
    chunksize: int,
    verify: bool,
) -> dict:
    if threshold != DEFAULT_THRESHOLD:
        raise ValueError(
            "only the audited pair-level filtered table is supported; it encodes "
            f"exactly the >= {DEFAULT_THRESHOLD} synapse threshold. Reconstruct "
            "from the unfiltered table first to support another threshold."
        )
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading node annotations ...", flush=True)
    node_df, node_arrays = load_node_table()
    root_ids = node_df["root_id"].to_numpy(dtype=np.int64)
    print(f"  {len(root_ids):,} nodes, {node_arrays['nt_missing']:,} without nt_type")

    print("Aggregating directed pairs across neuropils ...", flush=True)
    edge_arrays, edge_stats = build_edges(root_ids, FILTERED_CSV, threshold, chunksize)
    print(
        f"  {edge_stats['n_edges']:,} edges, "
        f"{edge_stats['n_synapses']:,} synapses "
        f"({edge_stats['edge_build_seconds']:.1f}s build)"
    )

    n_nodes = len(root_ids)
    n_edges = edge_stats["n_edges"]
    n_synapses = edge_stats["n_synapses"]
    graph = Connectome(
        root_ids=root_ids,
        out_indptr=edge_arrays["out_indptr"],
        edge_src=edge_arrays["pair_src"],
        edge_dst=edge_arrays["pair_dst"],
        edge_weight=edge_arrays["weights"],
        in_indptr=edge_arrays["in_indptr"],
        in_edge_idx=edge_arrays["in_order"],
        positions=node_arrays["positions"],
        position_mask=node_arrays["position_mask"],
        nt_code=node_arrays["nt_code"],
        super_class_code=node_arrays["super_class_code"],
        class_code=node_arrays["class_code"],
        side_code=node_arrays["side_code"],
        flow_code=node_arrays["flow_code"],
        vocabulary=node_arrays["vocabulary"],
        meta={
            "artifact": "fafb_connectome",
            "schema_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "node_index_rule": "0-based position in ascending root_id order",
            "edge_rule": "directed pre->post; weight = summed syn_count across neuropils",
            "threshold": threshold,
            "source_table": "datasets/raw/connections/connections_princeton.csv.gz",
            "reference_nodes": "datasets/raw/neurons/neurons.csv.gz",
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "n_synapses": n_synapses,
        },
    )

    print(f"Writing {out} ...", flush=True)
    graph.save(out)
    node_df.to_csv(nodes_out, index=False, compression="gzip")

    roundtrip = verify_artifact(out, edge_stats, graph.n_nodes) if verify else None
    if roundtrip and roundtrip["failures"]:
        raise RuntimeError(f"artifact round-trip failed: {roundtrip['failures']}")

    audit_expected, _ = _audit_expectations()
    outputs = {
        "connectome": {
            "path": out.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": out.stat().st_size,
        },
        "nodes": {
            "path": nodes_out.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": nodes_out.stat().st_size,
            "rows": len(node_df),
            "columns": list(node_df.columns),
        },
    }
    report = build_report(
        node_df, node_arrays, edge_stats, graph, audit_expected, roundtrip, outputs
    )
    report["duration_seconds"] = round(time.perf_counter() - started, 2)
    _write_json(report_path, report)

    print(f"  audit cross-check: {report['audit_cross_check']['status']}")
    failures = [
        row for row in report["audit_cross_check"]["checks"] if not row["pass"]
    ]
    for row in failures:
        print(
            f"  FAIL {row['name']}: expected {row['expected']:,}, "
            f"got {row['actual']:,}"
        )
    print(
        f"  isolated nodes: {report['degree']['isolated_nodes']:,}; "
        f"reciprocal directed pairs: {report['reciprocity']['directed_pairs_with_reverse']:,}"
    )
    print(f"Wrote {report_path}")
    if failures:
        raise SystemExit(1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruct the FAFB connectome from audited FlyWire tables"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--nodes-out", type=Path, default=DEFAULT_NODES_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--chunksize", type=int, default=CHUNK_ROWS)
    parser.add_argument(
        "--no-verify", action="store_true", help="skip the artifact round-trip check"
    )
    args = parser.parse_args(argv)
    run(
        out=args.out,
        nodes_out=args.nodes_out,
        report_path=args.report,
        threshold=args.threshold,
        chunksize=args.chunksize,
        verify=not args.no_verify,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
