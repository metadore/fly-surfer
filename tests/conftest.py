"""Shared fixtures: small in-memory graphs matching the loader's GraphView."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.subgraph import GraphView

DEFAULT_VOCABULARY = {
    "nt_type": ["ACH", "GABA", "DA", "GLUT"],
    "super_class": ["central", "sensory", "motor"],
    "class": ["class_a", "class_b"],
    "side": ["left", "right"],
}


def make_graph(
    n_nodes: int,
    edges: list[tuple[int, int, int]],
    *,
    nt_codes: np.ndarray | None = None,
    super_class_codes: np.ndarray | None = None,
    class_codes: np.ndarray | None = None,
    side_codes: np.ndarray | None = None,
    root_ids: np.ndarray | None = None,
    vocabulary: dict | None = None,
) -> GraphView:
    """Build a validated GraphView from an explicit edge list."""
    root_ids = (
        np.arange(1000, 1000 + n_nodes, dtype=np.int64)
        if root_ids is None
        else np.asarray(root_ids, dtype=np.int64)
    )
    order = sorted((int(s), int(d), int(w)) for s, d, w in edges)
    edge_src = np.array([e[0] for e in order], dtype=np.int32)
    edge_dst = np.array([e[1] for e in order], dtype=np.int32)
    edge_weight = np.array([e[2] for e in order], dtype=np.int32)

    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)

    def codes(values, default):
        if values is None:
            return np.full(n_nodes, default, dtype=np.int16)
        return np.asarray(values, dtype=np.int16)

    return GraphView(
        root_ids=root_ids,
        node_map=np.arange(n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        nt_code=codes(nt_codes, 0),
        super_class_code=codes(super_class_codes, 0),
        class_code=codes(class_codes, 0),
        side_code=codes(side_codes, 0),
        positions=np.zeros((n_nodes, 3), dtype=np.float32),
        vocabulary=dict(vocabulary or DEFAULT_VOCABULARY),
        source_n_nodes=n_nodes,
        source_n_edges=len(order),
    )


@pytest.fixture
def graph_factory():
    return make_graph
