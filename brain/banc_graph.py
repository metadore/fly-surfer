"""Build an independent BANC v888 structural graph from the audited export.

BANC is a different specimen from the local FAFB FlyWire connectome.  This
module never merges the two graphs, never writes to ``datasets/external`` and
never changes an FAFB artifact.

Graph semantics (Phase 4C.5 policy):

* canonical node ID is ``banc_888_id`` (18-digit decimal string on disk,
  int64 in memory);
* nodes are the 172,433 unique IDs appearing in the shipped v2 edgelist,
  indexed by position in ascending ``banc_888_id`` order;
* edges are directed ``pre -> post`` rows with integer ``count`` as weight;
* self-edges are excluded from every built graph but retained in the source;
* three thresholds are built: ``count >= 1, 5, 10``; threshold 5 is primary;
* annotations are left-joined by ``banc_888_id`` and missing values stay
  unknown.

Run ``python -m brain.banc_graph`` to rebuild the artifacts under
``datasets/processed/banc_v888/``.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.feather as feather

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BANC_RAW = PROJECT_ROOT / "datasets" / "external" / "banc_v88" / "raw"
OUT_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
AUDIT_JSON = PROJECT_ROOT / "reports" / "PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json"

DEFAULT_INPUTS = {
    "metadata": BANC_RAW / "metadata" / "banc_888_meta.feather",
    "edgelist_v2": BANC_RAW / "connectivity" / "banc_888_edgelist_simple_v2.feather",
    "backbone_proofread": BANC_RAW / "annotations" / "backbone_proofread.parquet",
    "neurotransmitter": BANC_RAW / "annotations" / "banc_888_neurotransmitter_prediction_v2.csv",
    "reviewed_matches": BANC_RAW / "cross_dataset_matches" / "banc_fafb_reviewed_matches.csv.gz",
}

DEFAULT_THRESHOLDS = (1, 5, 10)
PRIMARY_THRESHOLD = 5

ANNOTATION_COLUMNS = [
    "super_class",
    "cell_class",
    "cell_sub_class",
    "cell_type",
    "side",
    "region",
    "root_region",
    "nerve",
    "tract",
    "neuromere",
    "flow",
    "body_part_effector",
    "body_part_sensory",
    "peripheral_target_type",
    "cell_function",
    "neurotransmitter_predicted",
    "neurotransmitter_verified",
    "neurotransmitter_score",
    "proofread",
    "roughly_proofread",
    "status",
]

POSITION_COLUMN = "root_position_nm"
TERGOTROCHANTER_TARGET = "tergotrochanter_extensor_muscle"

FAFB_ARTIFACTS = [
    PROJECT_ROOT / "datasets" / "processed" / "connectome.npz",
    PROJECT_ROOT / "datasets" / "processed" / "nodes.csv.gz",
    PROJECT_ROOT / "datasets" / "processed" / "connectome_report.json",
    PROJECT_ROOT / "datasets" / "manifest.json",
    PROJECT_ROOT / "README.md",
]

EDGE_COLUMNS = ["pre", "post", "count", "norm", "post_count", "pre_count"]


# ---------------------------------------------------------------------------
# integrity helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path, chunk_bytes: int = 1 << 22) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=1, allow_nan=False, default=_json_default),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def snapshot_paths(paths: list[Path]) -> dict:
    """Record size and SHA-256 for existing files; missing files are marked."""
    return {
        _relative(path): {
            "exists": Path(path).is_file(),
            "bytes": int(Path(path).stat().st_size) if Path(path).is_file() else None,
            "sha256": sha256_file(path) if Path(path).is_file() else None,
        }
        for path in paths
    }


def compare_snapshots(before: dict, after: dict) -> dict:
    checks = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name, {})
        new = after.get(name, {})
        checks.append(
            {
                "path": name,
                "before_sha256": old.get("sha256"),
                "after_sha256": new.get("sha256"),
                "unchanged": (
                    old.get("exists") == new.get("exists")
                    and old.get("sha256") == new.get("sha256")
                ),
            }
        )
    failures = [row["path"] for row in checks if not row["unchanged"]]
    return {"checks": checks, "failures": failures, "unchanged": not failures}


def software_versions() -> dict:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
        "platform": platform.platform(),
    }


# ---------------------------------------------------------------------------
# canonical IDs and metadata
# ---------------------------------------------------------------------------


def validate_canonical_ids(meta: pd.DataFrame) -> dict:
    """Validate ``banc_888_id`` as a unique, non-null, integer-representable key."""
    if "banc_888_id" not in meta.columns:
        raise ValueError("metadata has no banc_888_id column")
    raw = meta["banc_888_id"]
    text = raw.astype("string").str.strip()
    nulls = int(raw.isna().sum())
    empties = int((text == "").sum())
    duplicated = int(text.duplicated(keep=False).sum())
    numeric = pd.to_numeric(text, errors="coerce")
    non_numeric = int(numeric.isna().sum() - nulls - empties)
    problems = []
    if nulls:
        problems.append(f"{nulls} null IDs")
    if empties:
        problems.append(f"{empties} empty IDs")
    if duplicated:
        problems.append(f"{duplicated} rows participate in duplicate IDs")
    if non_numeric > 0:
        problems.append(f"{non_numeric} IDs are not integers")
    if problems:
        raise ValueError("invalid banc_888_id values: " + ", ".join(problems))
    values = numeric.astype("int64").to_numpy()
    if len(np.unique(values)) != len(values):
        raise ValueError("banc_888_id is not unique")
    return {
        "column": "banc_888_id",
        "rows": int(len(meta)),
        "nulls": nulls,
        "empty_strings": empties,
        "duplicates": duplicated,
        "unique": int(len(values)),
        "dtype": str(raw.dtype),
        "id_min": int(values.min()) if len(values) else None,
        "id_max": int(values.max()) if len(values) else None,
        "verdict": "PASS",
    }


def load_metadata(path: Path) -> pd.DataFrame:
    columns = ["banc_888_id", *ANNOTATION_COLUMNS, POSITION_COLUMN]
    table = feather.read_table(Path(path), columns=columns)
    meta = table.to_pandas()
    validate_canonical_ids(meta)
    return meta


def load_edgelist(path: Path) -> dict:
    table = feather.read_table(Path(path))
    missing = [name for name in EDGE_COLUMNS if name not in table.column_names]
    if missing:
        raise ValueError(f"edgelist is missing columns: {missing}")
    nulls = {name: int(table.column(name).null_count) for name in EDGE_COLUMNS}
    bad_nulls = {name: count for name, count in nulls.items() if count}
    if bad_nulls:
        raise ValueError(f"edgelist contains nulls: {bad_nulls}")
    edges = {
        "pre": table.column("pre").cast("int64").to_numpy(),
        "post": table.column("post").cast("int64").to_numpy(),
        "count": table.column("count").cast("int64").to_numpy(),
        "norm": table.column("norm").to_numpy().astype(np.float64, copy=False),
        "post_count": table.column("post_count").cast("int64").to_numpy(),
        "pre_count": table.column("pre_count").cast("int64").to_numpy(),
        "nulls": nulls,
        "rows": int(table.num_rows),
        "columns": list(table.column_names),
    }
    if int(edges["rows"]) != len(edges["pre"]):
        raise ValueError("edgelist row count does not match parsed columns")
    if np.any(edges["count"] <= 0):
        raise ValueError("edgelist contains a non-positive count")
    if not np.all(np.isfinite(edges["norm"])) or np.any(edges["norm"] <= 0):
        raise ValueError("edgelist contains invalid norm values")
    if np.any(edges["post_count"] <= 0) or np.any(edges["pre_count"] <= 0):
        raise ValueError("edgelist contains non-positive pre/post counts")
    return edges


# ---------------------------------------------------------------------------
# graph container
# ---------------------------------------------------------------------------


@dataclass
class BancConnectome:
    """Sparse directed CSR graph with ``banc_888_id``-ordered nodes."""

    root_ids: np.ndarray
    out_indptr: np.ndarray
    edge_src: np.ndarray
    edge_dst: np.ndarray
    edge_weight: np.ndarray
    in_indptr: np.ndarray
    in_edge_idx: np.ndarray
    threshold: int
    banc_ids: np.ndarray | None = None
    positions: np.ndarray | None = None
    position_mask: np.ndarray | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.root_ids)
        m = len(self.edge_dst)
        if n == 0:
            raise ValueError("empty graph")
        if not np.all(np.diff(self.root_ids) > 0):
            raise ValueError("root_ids must be unique and ascending")
        if self.out_indptr.shape != (n + 1,) or self.in_indptr.shape != (n + 1,):
            raise ValueError("indptr length must equal n_nodes + 1")
        if int(self.out_indptr[-1]) != m or int(self.in_indptr[-1]) != m:
            raise ValueError("indptr tails must equal the edge count")
        if not np.all(self.out_indptr[:-1] <= self.out_indptr[1:]):
            raise ValueError("out_indptr must be non-decreasing")
        if not np.all(self.in_indptr[:-1] <= self.in_indptr[1:]):
            raise ValueError("in_indptr must be non-decreasing")
        for name, arr, size in (
            ("edge_src", self.edge_src, n),
            ("edge_dst", self.edge_dst, n),
            ("in_edge_idx", self.in_edge_idx, m),
        ):
            if len(arr) and (int(arr.min()) < 0 or int(arr.max()) >= size):
                raise ValueError(f"{name} contains out-of-range indices")
        if np.any(self.edge_weight < 1):
            raise ValueError("edge weights must be positive")
        if np.any(self.edge_src == self.edge_dst):
            raise ValueError("self-edges are not allowed in a built graph")
        if np.any(self.edge_weight < int(self.threshold)):
            raise ValueError("edge weight below the configured threshold")
        if self.banc_ids is not None and len(self.banc_ids) != n:
            raise ValueError("banc_ids must have one entry per node")
        if self.positions is not None:
            if self.positions.shape != (n, 3):
                raise ValueError("positions must have shape (n, 3)")
            if self.position_mask is not None and self.position_mask.shape != (n,):
                raise ValueError("position_mask must have one entry per node")

    @property
    def n_nodes(self) -> int:
        return len(self.root_ids)

    @property
    def n_edges(self) -> int:
        return len(self.edge_dst)

    @property
    def n_synapses(self) -> int:
        return int(self.edge_weight.sum(dtype=np.int64))

    @property
    def n_isolated(self) -> int:
        return int(np.count_nonzero(np.diff(self.out_indptr) + np.diff(self.in_indptr) == 0))

    def out_edges(self, node: int) -> tuple[np.ndarray, np.ndarray]:
        start, stop = self.out_indptr[node], self.out_indptr[node + 1]
        return self.edge_dst[start:stop], self.edge_weight[start:stop]

    def in_edges(self, node: int) -> tuple[np.ndarray, np.ndarray]:
        start, stop = self.in_indptr[node], self.in_indptr[node + 1]
        rows = self.in_edge_idx[start:stop]
        return self.edge_src[rows], self.edge_weight[rows]

    def node_index(self, banc_888_id: int | str) -> int:
        value = int(banc_888_id)
        index = int(np.searchsorted(self.root_ids, value))
        if index >= self.n_nodes or int(self.root_ids[index]) != value:
            raise KeyError(f"banc_888_id {banc_888_id!r} is not a graph node")
        return index

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.stem + ".tmp.npz")
        arrays = {
            "root_ids": self.root_ids,
            "out_indptr": self.out_indptr,
            "edge_src": self.edge_src,
            "edge_dst": self.edge_dst,
            "edge_weight": self.edge_weight,
            "in_indptr": self.in_indptr,
            "in_edge_idx": self.in_edge_idx,
            "threshold": np.array(int(self.threshold), dtype=np.int16),
            "meta_json": np.array(json.dumps(self.meta)),
        }
        if self.banc_ids is not None:
            arrays["banc_ids"] = np.asarray(self.banc_ids).astype(str)
        if self.positions is not None:
            arrays["positions"] = self.positions
        if self.position_mask is not None:
            arrays["position_mask"] = self.position_mask
        np.savez_compressed(tmp, **arrays)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path) -> "BancConnectome":
        with np.load(Path(path), allow_pickle=False) as data:
            payload = {key: data[key] for key in data.files}
        meta = json.loads(str(payload.pop("meta_json")))
        threshold = int(payload.pop("threshold"))
        banc_ids = payload.pop("banc_ids", None)
        positions = payload.pop("positions", None)
        position_mask = payload.pop("position_mask", None)
        return cls(
            threshold=threshold,
            banc_ids=banc_ids,
            positions=positions,
            position_mask=position_mask,
            meta=meta,
            **payload,
        )


# ---------------------------------------------------------------------------
# edge preparation and CSR construction
# ---------------------------------------------------------------------------


def _pair_keys(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    return (src.astype(np.uint64) << np.uint64(32)) | dst.astype(np.uint64)


def resolve_node_ids(meta: pd.DataFrame, pre: np.ndarray, post: np.ndarray) -> np.ndarray:
    """Return sorted canonical IDs for all endpoints, failing on missing IDs."""
    endpoints = np.unique(np.concatenate([pre, post])).astype(np.int64)
    meta_ids = (
        meta["banc_888_id"].astype("string").str.strip().astype("int64").to_numpy()
    )
    order = np.argsort(meta_ids, kind="stable")
    sorted_ids = meta_ids[order]
    position = np.searchsorted(sorted_ids, endpoints)
    position_clipped = np.minimum(position, len(sorted_ids) - 1)
    present = (position < len(sorted_ids)) & (
        sorted_ids[position_clipped] == endpoints
    )
    if not present.all():
        missing = endpoints[~present][:10].tolist()
        raise ValueError(
            f"{int((~present).sum())} edge endpoints are absent from metadata: {missing}"
        )
    return endpoints


def prepare_edges(
    pre: np.ndarray,
    post: np.ndarray,
    count: np.ndarray,
    node_ids: np.ndarray,
) -> dict:
    """Map endpoints to indices, validate pairs and remove self-edges.

    The returned arrays are sorted by ``(src, dst)`` and contain no self-edge.
    """
    pre = np.asarray(pre, dtype=np.int64)
    post = np.asarray(post, dtype=np.int64)
    count = np.asarray(count, dtype=np.int64)
    if not (len(pre) == len(post) == len(count)):
        raise ValueError("pre, post and count must have equal length")
    if len(pre) == 0:
        raise ValueError("edgelist is empty")
    if np.any(count <= 0):
        raise ValueError("edge counts must be positive")

    src = np.searchsorted(node_ids, pre)
    dst = np.searchsorted(node_ids, post)
    src_clipped = np.minimum(src, len(node_ids) - 1)
    dst_clipped = np.minimum(dst, len(node_ids) - 1)
    src_ok = (src < len(node_ids)) & (node_ids[src_clipped] == pre)
    dst_ok = (dst < len(node_ids)) & (node_ids[dst_clipped] == post)
    if not src_ok.all() or not dst_ok.all():
        missing = pre[~src_ok][:5].tolist() + post[~dst_ok][:5].tolist()
        raise ValueError(f"edge endpoints outside the canonical node set: {missing}")

    src = src.astype(np.int32, copy=False)
    dst = dst.astype(np.int32, copy=False)
    self_mask = src == dst
    self_rows = int(self_mask.sum())
    self_synapses = int(count[self_mask].sum(dtype=np.int64))
    self_nodes = int(np.unique(src[self_mask]).size) if self_rows else 0

    keys = _pair_keys(src, dst)
    order = np.argsort(keys, kind="stable")
    sorted_keys = keys[order]
    duplicate_rows = int(np.count_nonzero(sorted_keys[1:] == sorted_keys[:-1]))
    if duplicate_rows:
        duplicate_examples = np.flatnonzero(sorted_keys[1:] == sorted_keys[:-1])[:5]
        examples = [
            (int(pre[order[i]]), int(post[order[i]])) for i in duplicate_examples
        ]
        raise ValueError(
            f"{duplicate_rows} duplicate (pre, post) pairs; examples: {examples}"
        )
    del keys, sorted_keys

    keep = ~(src[order] == dst[order])
    src_sorted = src[order][keep]
    dst_sorted = dst[order][keep]
    weight_sorted = count[order][keep].astype(np.int32)
    del order, keep
    gc.collect()

    if len(src_sorted) == 0:
        raise ValueError("no edges remain after self-edge exclusion")
    if np.any(weight_sorted < 1):
        raise ValueError("edge weight overflow or non-positive weight")
    strictly_increasing = (src_sorted[1:] > src_sorted[:-1]) | (
        (src_sorted[1:] == src_sorted[:-1]) & (dst_sorted[1:] > dst_sorted[:-1])
    )
    if not bool(np.all(strictly_increasing)):
        raise ValueError("edge ordering is not deterministic")

    return {
        "src": src_sorted,
        "dst": dst_sorted,
        "weight": weight_sorted,
        "n_original": int(len(pre)),
        "n_non_self": int(len(src_sorted)),
        "self_edge_rows": self_rows,
        "self_edge_synapses": self_synapses,
        "self_edge_nodes": self_nodes,
        "duplicate_pair_rows": duplicate_rows,
        "original_synapses": int(count.sum(dtype=np.int64)),
        "non_self_synapses": int(weight_sorted.sum(dtype=np.int64)),
    }


def _degree_summary(degrees: np.ndarray) -> dict:
    if degrees.size == 0:
        return {"total": 0, "mean": 0.0, "min": 0, "max": 0, "percentiles": {}}
    marks = (0, 25, 50, 75, 90, 95, 99, 100)
    return {
        "total": int(degrees.sum()),
        "mean": round(float(degrees.mean()), 3),
        "min": int(degrees.min()),
        "max": int(degrees.max()),
        "percentiles": {str(p): int(np.percentile(degrees, p)) for p in marks},
    }


def build_threshold_graph(
    prepared: dict,
    node_ids: np.ndarray,
    threshold: int,
    *,
    banc_ids: np.ndarray | None = None,
    positions: np.ndarray | None = None,
    position_mask: np.ndarray | None = None,
) -> tuple[BancConnectome, dict]:
    """Filter prepared edges and build one deterministic CSR graph."""
    threshold = int(threshold)
    if threshold < 1:
        raise ValueError("threshold must be at least 1")
    mask = prepared["weight"] >= threshold
    src = prepared["src"][mask]
    dst = prepared["dst"][mask]
    weight = prepared["weight"][mask]
    if len(src) == 0:
        raise ValueError(f"threshold {threshold} retains no edges")

    n = len(node_ids)
    out_counts = np.bincount(src, minlength=n).astype(np.int64)
    out_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(out_counts, out=out_indptr[1:])
    del out_counts

    in_counts = np.bincount(dst, minlength=n).astype(np.int64)
    in_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(in_counts, out=in_indptr[1:])
    del in_counts
    in_edge_idx = np.argsort(dst, kind="stable").astype(np.int32)

    graph = BancConnectome(
        root_ids=node_ids.astype(np.int64, copy=False),
        out_indptr=out_indptr,
        edge_src=src.astype(np.int32, copy=False),
        edge_dst=dst.astype(np.int32, copy=False),
        edge_weight=weight.astype(np.int32, copy=False),
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=threshold,
        banc_ids=banc_ids,
        positions=positions,
        position_mask=position_mask,
        meta={
            "artifact": "banc_v888_graph",
            "dataset": "BANC materialization v888",
            "threshold": threshold,
            "canonical_id": "banc_888_id",
            "weight": "integer synapse count",
        },
    )
    out_degree = np.diff(out_indptr)
    in_degree = np.diff(in_indptr)
    isolated = out_degree + in_degree == 0
    stats = {
        "threshold": threshold,
        "n_nodes": graph.n_nodes,
        "n_edges": graph.n_edges,
        "n_synapses": graph.n_synapses,
        "weight_min": int(graph.edge_weight.min()),
        "weight_max": int(graph.edge_weight.max()),
        "weight_mean": round(float(graph.edge_weight.mean()), 4),
        "isolated_nodes": int(isolated.sum()),
        "out_degree": _degree_summary(out_degree),
        "in_degree": _degree_summary(in_degree),
        "retained_pair_share": round(graph.n_edges / prepared["n_non_self"], 6),
        "retained_synapse_share": round(
            graph.n_synapses / prepared["non_self_synapses"], 6
        ),
    }
    return graph, stats


# ---------------------------------------------------------------------------
# node table and populations
# ---------------------------------------------------------------------------


def _ordered_metadata(meta: pd.DataFrame, root_ids: np.ndarray) -> pd.DataFrame:
    meta_ids = (
        meta["banc_888_id"].astype("string").str.strip().astype("int64").to_numpy()
    )
    index = pd.Index(meta_ids, name="banc_888_id_int")
    if index.has_duplicates:
        raise ValueError("metadata has duplicate banc_888_id values")
    ordered = meta.set_index(index)
    try:
        return ordered.loc[root_ids]
    except KeyError as error:
        raise ValueError(f"metadata missing graph node: {error}") from None


def parse_positions(meta: pd.DataFrame, root_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Parse ``root_position_nm`` as float32 nanometres; missing stays masked."""
    ordered = _ordered_metadata(meta, root_ids)
    if POSITION_COLUMN not in ordered.columns:
        return np.zeros((len(root_ids), 3), dtype=np.float32), np.zeros(
            len(root_ids), dtype=bool
        )
    text = ordered[POSITION_COLUMN].astype("string")
    parts = text.str.split(",", expand=True)
    frame = pd.DataFrame(index=parts.index)
    for column in range(3):
        if column in parts.columns:
            frame[column] = pd.to_numeric(parts[column], errors="coerce")
        else:
            frame[column] = np.nan
    values = frame.to_numpy(dtype=np.float64)
    mask = np.isfinite(values).all(axis=1)
    values[~mask] = 0.0
    return values.astype(np.float32), mask


def build_node_table(
    meta: pd.DataFrame,
    root_ids: np.ndarray,
) -> pd.DataFrame:
    """Left-join annotations onto the exact graph node set."""
    ordered = _ordered_metadata(meta, root_ids)
    table = pd.DataFrame(
        {
            "node_index": np.arange(len(root_ids), dtype=np.int64),
            "banc_888_id": ordered["banc_888_id"].astype(str).to_numpy(),
        }
    )
    for column in ANNOTATION_COLUMNS:
        table[column] = ordered[column].to_numpy()
    super_class = table["super_class"]
    side = table["side"]
    motor = super_class.eq("motor")
    table["is_descending"] = super_class.eq("descending")
    table["is_motor"] = motor
    table["is_vnc"] = table["region"].eq("ventral_nerve_cord")
    table["is_vnc_intrinsic"] = super_class.eq("ventral_nerve_cord_intrinsic")
    table["is_left_motor"] = motor & side.eq("left")
    table["is_right_motor"] = motor & side.eq("right")
    table["is_tergotrochanter_candidate"] = motor & table[
        "peripheral_target_type"
    ].eq(TERGOTROCHANTER_TARGET)
    return table


POPULATION_RULES = {
    "descending": lambda frame: frame["super_class"].eq("descending"),
    "motor": lambda frame: frame["super_class"].eq("motor"),
    "left_motor": lambda frame: frame["super_class"].eq("motor")
    & frame["side"].eq("left"),
    "right_motor": lambda frame: frame["super_class"].eq("motor")
    & frame["side"].eq("right"),
    "vnc": lambda frame: frame["region"].eq("ventral_nerve_cord"),
    "vnc_intrinsic": lambda frame: frame["super_class"].eq(
        "ventral_nerve_cord_intrinsic"
    ),
    "ascending": lambda frame: frame["super_class"].eq("ascending"),
    "tergotrochanter_motor_candidates": lambda frame: frame[
        "is_tergotrochanter_candidate"
    ],
}


def population_mask(nodes: pd.DataFrame, name: str) -> np.ndarray:
    try:
        rule = POPULATION_RULES[name]
    except KeyError:
        raise KeyError(f"unknown population {name!r}") from None
    return rule(nodes).fillna(False).to_numpy(dtype=bool)


def select_population(nodes: pd.DataFrame, name: str) -> pd.DataFrame:
    return nodes.loc[population_mask(nodes, name)].reset_index(drop=True)


def motor_by_body_part(nodes: pd.DataFrame) -> pd.DataFrame:
    motor = nodes.loc[population_mask(nodes, "motor")].copy()
    motor["body_part_effector"] = motor["body_part_effector"].fillna("unknown")
    grouped = motor.groupby("body_part_effector", dropna=False)
    summary = pd.DataFrame(
        {
            "motor_neurons": grouped.size(),
            "left": grouped["side"].apply(lambda values: int((values == "left").sum())),
            "right": grouped["side"].apply(
                lambda values: int((values == "right").sum())
            ),
        }
    )
    summary = summary.sort_values(
        ["motor_neurons", "body_part_effector"], ascending=[False, True]
    ).reset_index()
    return summary


# ---------------------------------------------------------------------------
# construction pipeline
# ---------------------------------------------------------------------------


def construct_graphs(
    meta: pd.DataFrame,
    edges: dict,
    thresholds: tuple[int, ...] = DEFAULT_THRESHOLDS,
) -> tuple[dict[int, BancConnectome], pd.DataFrame, dict]:
    """Build every threshold graph from a single edge load."""
    validate_canonical_ids(meta)
    node_ids = resolve_node_ids(meta, edges["pre"], edges["post"])
    prepared = prepare_edges(edges["pre"], edges["post"], edges["count"], node_ids)
    node_table = build_node_table(meta, node_ids)
    positions, position_mask = parse_positions(meta, node_ids)
    banc_ids = node_table["banc_888_id"].to_numpy().astype(str)
    graphs: dict[int, BancConnectome] = {}
    stats: dict[str, dict] = {}
    for threshold in thresholds:
        graph, graph_stats = build_threshold_graph(
            prepared,
            node_ids,
            threshold,
            banc_ids=banc_ids,
            positions=positions,
            position_mask=position_mask,
        )
        graphs[int(threshold)] = graph
        stats[f"threshold_{int(threshold)}"] = graph_stats
    summary = {
        "node_count": int(len(node_ids)),
        "metadata_rows": int(len(meta)),
        "metadata_only_rows": int(len(meta) - len(node_ids)),
        "canonical_ids": validate_canonical_ids(meta),
        "edge_preparation": {
            key: int(value)
            for key, value in prepared.items()
            if isinstance(value, (int, np.integer))
        },
        "duplicate_pair_rows": int(prepared["duplicate_pair_rows"]),
        "thresholds": [int(value) for value in thresholds],
    }
    return graphs, node_table, {"summary": summary, "stats": stats, "prepared": prepared}


def _artifact_paths(out_dir: Path) -> dict:
    return {
        "graph_threshold_1": out_dir / "banc_graph_t1.npz",
        "graph_threshold_5": out_dir / "banc_graph_t5.npz",
        "graph_threshold_10": out_dir / "banc_graph_t10.npz",
        "nodes": out_dir / "banc_nodes.csv.gz",
        "id_map": out_dir / "banc_id_map.csv.gz",
        "manifest": out_dir / "banc_manifest.json",
        "construction_report": out_dir / "banc_construction_report.json",
    }


def _output_descriptor(path: Path) -> dict:
    return {
        "path": _relative(path),
        "bytes": int(Path(path).stat().st_size),
        "sha256": sha256_file(path),
    }


def build_manifest(
    *,
    inputs: dict[str, Path],
    input_hashes: dict[str, dict],
    graphs: dict[int, BancConnectome],
    stats: dict,
    summary: dict,
    nodes: pd.DataFrame,
    outputs: dict[str, Path],
    audit: dict,
    fafb_before: dict,
    fafb_after: dict,
    generated_at: str,
    duration_seconds: float,
    peak_memory_mb: float | None,
    thresholds: tuple[int, ...],
) -> dict:
    audit_inputs = audit["audit"]["inputs"]
    audit_checks = {
        name: {
            "expected_sha256": audit_inputs.get(name, {}).get("sha256"),
            "actual_sha256": input_hashes[name]["sha256"],
            "match": audit_inputs.get(name, {}).get("sha256")
            == input_hashes[name]["sha256"],
        }
        for name in inputs
    }
    expected = {
        "node_count": int(audit["C_edge_integrity"]["unique_nodes"]),
        "original_edge_count": int(audit["C_edge_integrity"]["source_rows"]),
        "self_edge_rows": int(audit["B_self_edges"]["rows"]),
        "self_edge_synapses": int(audit["B_self_edges"]["summed_count"]),
    }
    actual = {
        "node_count": int(summary["node_count"]),
        "original_edge_count": int(summary["edge_preparation"]["n_original"]),
        "self_edge_rows": int(summary["edge_preparation"]["self_edge_rows"]),
        "self_edge_synapses": int(summary["edge_preparation"]["self_edge_synapses"]),
    }
    audit_count_checks = {
        name: {
            "expected": expected[name],
            "actual": actual[name],
            "match": expected[name] == actual[name],
        }
        for name in expected
    }
    fafb_isolation = compare_snapshots(fafb_before, fafb_after)
    retained = {
        name: {
            "threshold": value["threshold"],
            "n_edges": value["n_edges"],
            "n_synapses": value["n_synapses"],
            "weight_min": value["weight_min"],
            "weight_max": value["weight_max"],
            "isolated_nodes": value["isolated_nodes"],
        }
        for name, value in stats.items()
    }
    return {
        "schema_version": 1,
        "phase": "4D",
        "generated_at_utc": generated_at,
        "dataset_version": "BANC materialization v888 (edgelist v2, size >= 5)",
        "dataset_separation": (
            "Independent BANC graph. No node, edge or index is shared with the "
            "FAFB FlyWire artifact."
        ),
        "canonical_id_field": "banc_888_id",
        "canonical_id_representation": (
            "18-digit decimal string in the node table; exact int64 in memory"
        ),
        "node_index_rule": (
            "0-based position in ascending numeric banc_888_id order over the "
            "unique endpoints of the source edgelist"
        ),
        "deterministic_ordering_policy": (
            "edges sorted by (pre_index, post_index) before CSR construction; "
            "in_edge_idx from a stable argsort of post_index"
        ),
        "node_count": int(summary["node_count"]),
        "metadata_rows": int(summary["metadata_rows"]),
        "metadata_only_rows_excluded": int(summary["metadata_only_rows"]),
        "original_edge_count": int(summary["edge_preparation"]["n_original"]),
        "original_synapse_sum": int(summary["edge_preparation"]["original_synapses"]),
        "excluded_self_edge_count": int(summary["edge_preparation"]["self_edge_rows"]),
        "excluded_self_edge_synapse_sum": int(
            summary["edge_preparation"]["self_edge_synapses"]
        ),
        "non_self_edge_count": int(summary["edge_preparation"]["n_non_self"]),
        "non_self_synapse_sum": int(summary["edge_preparation"]["non_self_synapses"]),
        "retained": retained,
        "configuration": {
            "thresholds": [int(value) for value in thresholds],
            "primary_threshold": PRIMARY_THRESHOLD,
            "self_edge_policy": "exclude_from_graph_keep_in_source",
            "duplicate_policy": "fail_on_unexpected_duplicates",
            "annotation_join": "left_join_on_banc_888_id",
        },
        "edge_weight_policy": {
            "field": "count",
            "type": "integer synapse count",
            "physiology": (
                "Structural synapse count, not conductance. norm is never used "
                "as a weight."
            ),
        },
        "inputs": input_hashes,
        "audit_cross_check": {
            "path": _relative(AUDIT_JSON),
            "inputs": audit_checks,
            "counts": audit_count_checks,
            "pass": all(row["match"] for row in audit_checks.values())
            and all(row["match"] for row in audit_count_checks.values()),
        },
        "fafb_isolation": fafb_isolation,
        "outputs": {
            name: _output_descriptor(path)
            for name, path in outputs.items()
            if path.exists()
        },
        "software": software_versions(),
        "runtime_seconds": round(float(duration_seconds), 3),
        "peak_memory_mb": peak_memory_mb,
        "nodes_columns": list(nodes.columns),
    }


def verify_manifest(manifest: dict, root: Path = PROJECT_ROOT) -> dict:
    """Recompute hashes for every manifest input and output."""
    checks = []
    for section in ("inputs", "outputs"):
        for name, entry in manifest.get(section, {}).items():
            path = Path(root) / entry["path"]
            exists = path.is_file()
            actual = sha256_file(path) if exists else None
            checks.append(
                {
                    "section": section,
                    "name": name,
                    "path": entry["path"],
                    "expected_sha256": entry.get("sha256"),
                    "actual_sha256": actual,
                    "exists": exists,
                    "match": bool(exists and actual == entry.get("sha256")),
                }
            )
    failures = [
        f"{row['section']}:{row['name']}" for row in checks if not row["match"]
    ]
    return {"checks": checks, "failures": failures, "pass": not failures}


def verify_graph(graph: BancConnectome, stats: dict) -> dict:
    n = graph.n_nodes
    degrees_out = np.bincount(graph.edge_src, minlength=n)
    degrees_in = np.bincount(graph.edge_dst, minlength=n)
    in_dst_sorted = graph.edge_dst[graph.in_edge_idx]
    checks = {
        "n_nodes": graph.n_nodes == stats["n_nodes"],
        "n_edges": graph.n_edges == stats["n_edges"],
        "n_synapses": graph.n_synapses == stats["n_synapses"],
        "no_self_loops": bool(np.all(graph.edge_src != graph.edge_dst)),
        "threshold_respected": bool(np.all(graph.edge_weight >= graph.threshold)),
        "weights_positive": bool(np.all(graph.edge_weight >= 1)),
        "out_csr_consistent": bool(
            np.array_equal(degrees_out, np.diff(graph.out_indptr))
        ),
        "in_csr_consistent": bool(
            np.array_equal(degrees_in, np.diff(graph.in_indptr))
        ),
        "in_order_sorted": bool(np.all(in_dst_sorted[:-1] <= in_dst_sorted[1:])),
        "root_ids_sorted": bool(np.all(np.diff(graph.root_ids) > 0)),
        "isolated_nodes": graph.n_isolated == stats["isolated_nodes"],
    }
    failures = [name for name, ok in checks.items() if not ok]
    return {"checks": checks, "failures": failures, "pass": not failures}


def _peak_memory_mb() -> float | None:
    try:
        import psutil

        process = psutil.Process()
        info = process.memory_info()
        peak = getattr(info, "peak_wset", None)
        value = peak if peak is not None else info.rss
        return round(float(value) / (1024 * 1024), 1)
    except Exception:
        return None


def run(
    *,
    out_dir: Path = OUT_DIR,
    inputs: dict[str, Path] | None = None,
    thresholds: tuple[int, ...] = DEFAULT_THRESHOLDS,
    verify: bool = True,
) -> dict:
    started = time.perf_counter()
    inputs = dict(inputs or DEFAULT_INPUTS)
    missing = [str(path) for path in inputs.values() if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing BANC inputs: {missing}")
    thresholds = tuple(int(value) for value in thresholds)
    if PRIMARY_THRESHOLD not in thresholds:
        raise ValueError(f"primary threshold {PRIMARY_THRESHOLD} must be built")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fafb_before = snapshot_paths(FAFB_ARTIFACTS)
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    input_hashes = {
        name: {
            "path": _relative(path),
            "bytes": int(Path(path).stat().st_size),
            "sha256": sha256_file(path),
        }
        for name, path in inputs.items()
    }
    software = software_versions()

    timings: dict[str, float] = {}
    stage = time.perf_counter()
    print("Loading BANC metadata and edgelist ...", flush=True)
    meta = load_metadata(inputs["metadata"])
    edges = load_edgelist(inputs["edgelist_v2"])
    timings["load_seconds"] = round(time.perf_counter() - stage, 3)
    print(
        f"  metadata: {len(meta):,} rows; edgelist: {edges['rows']:,} rows",
        flush=True,
    )

    stage = time.perf_counter()
    graphs, nodes, result = construct_graphs(meta, edges, thresholds)
    timings["construct_seconds"] = round(time.perf_counter() - stage, 3)
    summary = result["summary"]
    stats = result["stats"]
    prepared = result["prepared"]
    print(
        f"  nodes: {summary['node_count']:,}; self-edges excluded: "
        f"{prepared['self_edge_rows']:,} ({prepared['self_edge_synapses']:,} synapses)",
        flush=True,
    )
    print(
        f"  edges retained: "
        + ", ".join(
            f">={threshold}: {stats[f'threshold_{threshold}']['n_edges']:,}"
            for threshold in thresholds
        ),
        flush=True,
    )

    paths = _artifact_paths(out_dir)
    stage = time.perf_counter()
    for threshold in thresholds:
        target = paths[f"graph_threshold_{threshold}"]
        print(f"Writing {target} ...", flush=True)
        graphs[threshold].save(target)
    nodes.to_csv(paths["nodes"], index=False, compression="gzip")
    nodes[["banc_888_id", "node_index"]].to_csv(
        paths["id_map"], index=False, compression="gzip"
    )
    if verify:
        artifact_checks = {
            str(threshold): verify_graph(graphs[threshold], stats[f"threshold_{threshold}"])
            for threshold in thresholds
        }
        artifact_failures = {
            threshold: row["failures"]
            for threshold, row in artifact_checks.items()
            if row["failures"]
        }
        if artifact_failures:
            raise RuntimeError(f"graph self-verification failed: {artifact_failures}")
    else:
        artifact_checks = {}
    timings["write_seconds"] = round(time.perf_counter() - stage, 3)

    stage = time.perf_counter()
    fafb_after = snapshot_paths(FAFB_ARTIFACTS)
    duration = time.perf_counter() - started
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    outputs = {name: path for name, path in paths.items() if name != "manifest" and name != "construction_report"}
    manifest = build_manifest(
        inputs=inputs,
        input_hashes=input_hashes,
        graphs=graphs,
        stats=stats,
        summary=summary,
        nodes=nodes,
        outputs=outputs,
        audit=audit,
        fafb_before=fafb_before,
        fafb_after=fafb_after,
        generated_at=generated_at,
        duration_seconds=duration,
        peak_memory_mb=_peak_memory_mb(),
        thresholds=thresholds,
    )
    write_json(paths["manifest"], manifest)
    manifest_check = verify_manifest(manifest)
    if not manifest_check["pass"]:
        raise RuntimeError(f"manifest checksum validation failed: {manifest_check['failures']}")

    populations = {
        "metadata": {
            "motor": int(meta["super_class"].eq("motor").sum()),
            "descending": int(meta["super_class"].eq("descending").sum()),
            "ascending": int(meta["super_class"].eq("ascending").sum()),
            "vnc_region": int(meta["region"].eq("ventral_nerve_cord").sum()),
            "vnc_intrinsic": int(
                meta["super_class"].eq("ventral_nerve_cord_intrinsic").sum()
            ),
            "tergotrochanter_candidates": int(
                (
                    meta["super_class"].eq("motor")
                    & meta["peripheral_target_type"].eq(TERGOTROCHANTER_TARGET)
                ).sum()
            ),
        },
        "graph": {
            name: int(population_mask(nodes, name).sum())
            for name in POPULATION_RULES
        },
    }
    audit_populations = {
        "motor": int(audit["D_annotation_quality"]["populations"]["motor"]["rows"]),
        "descending": int(
            audit["D_annotation_quality"]["populations"]["descending"]["rows"]
        ),
        "ascending": int(
            audit["D_annotation_quality"]["populations"]["ascending"]["rows"]
        ),
        "vnc_intrinsic": int(
            audit["D_annotation_quality"]["populations"]["ventral_nerve_cord_intrinsic"][
                "rows"
            ]
        ),
    }
    population_checks = {
        name: {
            "expected": value,
            "metadata_actual": populations["metadata"].get(name),
            "match": populations["metadata"].get(name) == value,
        }
        for name, value in audit_populations.items()
    }
    graph_counts = {
        "motor": int(population_mask(nodes, "motor").sum()),
        "descending": int(population_mask(nodes, "descending").sum()),
        "ascending": int(population_mask(nodes, "ascending").sum()),
        "vnc_intrinsic": int(population_mask(nodes, "vnc_intrinsic").sum()),
        "vnc_region": int(population_mask(nodes, "vnc").sum()),
        "tergotrochanter_motor_candidates": int(
            population_mask(nodes, "tergotrochanter_motor_candidates").sum()
        ),
    }
    motor_parts = motor_by_body_part(nodes)
    population_report = {
        "definitions": {
            "descending": "super_class == 'descending'",
            "motor": "super_class == 'motor'",
            "vnc": "region == 'ventral_nerve_cord'",
            "vnc_intrinsic": "super_class == 'ventral_nerve_cord_intrinsic'",
            "tergotrochanter_motor_candidates": (
                "super_class == 'motor' and peripheral_target_type == "
                "'tergotrochanter_extensor_muscle'"
            ),
        },
        "metadata_counts": populations["metadata"],
        "graph_counts": graph_counts,
        "audit_checks": population_checks,
        "motor_by_body_part": motor_parts.to_dict(orient="records"),
        "discrepancies": [
            {
                "population": name,
                "audit": value,
                "metadata": populations["metadata"].get(name),
                "delta": (
                    None
                    if populations["metadata"].get(name) is None
                    else int(populations["metadata"][name]) - int(value)
                ),
            }
            for name, value in audit_populations.items()
            if populations["metadata"].get(name) != value
        ],
        "audit_vs_graph_discrepancies": [
            {
                "population": name,
                "audit": value,
                "graph": graph_counts.get(name),
                "delta": (
                    None
                    if graph_counts.get(name) is None
                    else int(graph_counts[name]) - int(value)
                ),
                "reason": (
                    "metadata rows absent from the source edgelist are not graph nodes"
                ),
            }
            for name, value in audit_populations.items()
            if graph_counts.get(name) != value
        ],
    }

    annotation_coverage = {
        column: {
            "present": int(nodes[column].notna().sum()),
            "missing": int(nodes[column].isna().sum()),
            "present_share": round(float(nodes[column].notna().mean()), 6),
        }
        for column in ("super_class", "cell_type", "side", "body_part_effector", "proofread")
    }

    construction_report = {
        "phase": "4D",
        "generated_at_utc": generated_at,
        "verdict": "PASS WITH LIMITATIONS",
        "canonical_id_field": "banc_888_id",
        "node_count": int(summary["node_count"]),
        "metadata_rows": int(summary["metadata_rows"]),
        "metadata_only_rows_excluded": int(summary["metadata_only_rows"]),
        "original_edge_count": int(prepared["n_original"]),
        "excluded_self_edge_count": int(prepared["self_edge_rows"]),
        "excluded_self_edge_synapse_sum": int(prepared["self_edge_synapses"]),
        "non_self_edge_count": int(prepared["n_non_self"]),
        "thresholds": stats,
        "populations": population_report,
        "annotation_coverage": annotation_coverage,
        "validation": {
            "canonical_ids": summary["canonical_ids"],
            "duplicate_pair_rows": int(summary["duplicate_pair_rows"]),
            "artifact_checks": artifact_checks,
            "manifest_check": manifest_check,
            "audit_cross_check": manifest["audit_cross_check"],
            "fafb_isolation": manifest["fafb_isolation"],
        },
        "software": software,
        "timings": timings,
        "runtime_seconds": round(float(duration), 3),
        "peak_memory_mb": manifest["peak_memory_mb"],
        "outputs": manifest["outputs"],
        "limitations": [
            "BANC is a different specimen from FAFB; the graphs are not merged.",
            "The graph contains only the exported v2 pairs with both partners identified.",
            "Edge weight is synapse count, not conductance.",
            "Structural adjacency does not establish excitation, inhibition or a motor command.",
            "Self-edges are excluded from the graph as a simulation policy; the source file is unchanged.",
            "Missing annotations remain unknown and are never inferred.",
            "Tergotrochanter candidates are annotation-defined, not functionally validated jump commands.",
        ],
    }
    write_json(paths["construction_report"], construction_report)
    print(f"Wrote {paths['manifest']}")
    print(f"Wrote {paths['construction_report']}")
    return construction_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the independent BANC v888 graph")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_INPUTS["metadata"])
    parser.add_argument("--edgelist", type=Path, default=DEFAULT_INPUTS["edgelist_v2"])
    parser.add_argument("--thresholds", type=int, nargs="+", default=list(DEFAULT_THRESHOLDS))
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args(argv)
    inputs = dict(DEFAULT_INPUTS)
    inputs["metadata"] = args.metadata
    inputs["edgelist_v2"] = args.edgelist
    report = run(
        out_dir=args.out_dir,
        inputs=inputs,
        thresholds=tuple(args.thresholds),
        verify=not args.no_verify,
    )
    print(
        f"verdict: {report['verdict']}; nodes: {report['node_count']:,}; "
        f"edges >=5: {report['thresholds']['threshold_5']['n_edges']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
