"""Deterministic synthetic substrate for Phase 5D validation.

SCIENTIFIC STATUS
    This is a validation fixture, not a dataset and not a model of any
    biological circuit. It exists so weight updates, trace wiring and the
    eta = 0 equivalence contract can be tested cheaply and reproducibly before
    any full-graph experiment. It never reads or writes ``datasets/``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from brain.banc_graph import BancConnectome
from brain.banc_synapse_policy import (
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)

# Verified labels covering the three sign outcomes of the primary policy.
LABEL_CYCLE = (
    "acetylcholine",
    "gaba",
    "acetylcholine",
    "glutamate",
    None,
    "gaba",
    "dopamine",
    None,
)


def synthetic_graph(
    n_nodes: int = 32,
    n_edges: int = 192,
    *,
    threshold: int = 1,
    seed: int = 11,
    max_count: int = 20,
) -> BancConnectome:
    """A connected, sorted, duplicate-free random directed graph."""
    if n_nodes < 4:
        raise ValueError("n_nodes must be at least 4")
    if n_edges < n_nodes or n_edges > n_nodes * (n_nodes - 1):
        raise ValueError("n_edges must be between n_nodes and n*(n-1)")
    rng = np.random.default_rng(int(seed))
    pairs: set[tuple[int, int]] = set()
    while len(pairs) < n_edges:
        src = int(rng.integers(0, n_nodes))
        dst = int(rng.integers(0, n_nodes))
        if src != dst:
            pairs.add((src, dst))
    ordered = np.array(sorted(pairs), dtype=np.int32)
    edge_src = ordered[:, 0]
    edge_dst = ordered[:, 1]
    edge_weight = rng.integers(1, max_count + 1, size=n_edges).astype(np.int32)
    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)
    return BancConnectome(
        root_ids=np.arange(900_000, 900_000 + n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=threshold,
    )


def synthetic_node_table(graph: BancConnectome) -> pd.DataFrame:
    labels = [
        LABEL_CYCLE[index % len(LABEL_CYCLE)] for index in range(graph.n_nodes)
    ]
    return pd.DataFrame(
        {
            "banc_888_id": [str(value) for value in graph.root_ids],
            "node_index": np.arange(graph.n_nodes),
            "neurotransmitter_verified": labels,
            "neurotransmitter_predicted": [None] * graph.n_nodes,
        }
    )


def synthetic_policy(
    graph: BancConnectome,
    *,
    weight_policy: WeightPolicy | None = None,
    sign_policy: SignPolicy | None = None,
):
    return build_synapse_policy(
        graph,
        synthetic_node_table(graph),
        sign_policy or SignPolicy(),
        weight_policy or WeightPolicy(),
    )


def synthetic_substrate(
    n_nodes: int = 32,
    n_edges: int = 192,
    *,
    threshold: int = 1,
    seed: int = 11,
):
    graph = synthetic_graph(n_nodes, n_edges, threshold=threshold, seed=seed)
    return graph, synthetic_policy(graph)
