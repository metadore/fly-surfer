"""Induced subgraphs and reproducible connected neuron sampling.

Sampling grows a connected snowball from candidate hubs chosen across cell
classes and neurotransmitter groups, then keeps the candidate whose class
composition is closest to the eligible population. The result is deterministic
for a given seed and is a single weakly connected component.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class GraphView:
    """Read-only local-index view of a subgraph of the connectome."""

    root_ids: np.ndarray
    node_map: np.ndarray
    out_indptr: np.ndarray
    edge_src: np.ndarray
    edge_dst: np.ndarray
    edge_weight: np.ndarray
    in_indptr: np.ndarray
    in_edge_idx: np.ndarray
    nt_code: np.ndarray
    super_class_code: np.ndarray
    class_code: np.ndarray
    side_code: np.ndarray
    positions: np.ndarray
    vocabulary: dict = field(default_factory=dict)
    source_n_nodes: int = 0
    source_n_edges: int = 0

    def __post_init__(self) -> None:
        n = len(self.root_ids)
        m = len(self.edge_dst)
        if n == 0:
            raise ValueError("subgraph must contain at least one neuron")
        if not np.all(np.diff(self.root_ids) > 0):
            raise ValueError("root_ids must be ascending and unique")
        if len(self.node_map) != n:
            raise ValueError("node_map must have one entry per node")
        if self.out_indptr.shape != (n + 1,) or self.in_indptr.shape != (n + 1,):
            raise ValueError("indptr length must equal n_nodes + 1")
        if self.out_indptr[-1] != m or self.in_indptr[-1] != m:
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
                raise ValueError(f"{name} has out-of-range indices")
        if np.any(self.edge_weight < 1):
            raise ValueError("edge weights must be positive")
        for name in ("nt_code", "super_class_code", "class_code", "side_code"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"{name} must have one entry per node")
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
        index = int(np.searchsorted(self.root_ids, root_id))
        if index >= self.n_nodes or int(self.root_ids[index]) != int(root_id):
            raise KeyError(f"root ID {root_id} is not in this subgraph")
        return index


@dataclass(frozen=True)
class SampleSelection:
    node_indices: np.ndarray
    target: int
    seed_node_index: int
    candidate_count: int
    effective_min_degree: int
    eligible_count: int
    sampling_seconds: float


def total_degrees(graph: GraphView) -> np.ndarray:
    return (np.diff(graph.out_indptr) + np.diff(graph.in_indptr)).astype(np.int64)


def extract_induced_subgraph(graph, node_indices: np.ndarray) -> GraphView:
    """Build a local CSR graph containing every edge among ``node_indices``."""
    selected = np.unique(np.asarray(node_indices, dtype=np.int64))
    n_full = len(graph.root_ids)
    if selected.size == 0:
        raise ValueError("cannot build an empty subgraph")
    if int(selected[0]) < 0 or int(selected[-1]) >= n_full:
        raise ValueError("node index outside the source graph")

    local_of_full = np.full(n_full, -1, dtype=np.int32)
    local_of_full[selected] = np.arange(selected.size, dtype=np.int32)

    mask = (local_of_full[graph.edge_src] >= 0) & (
        local_of_full[graph.edge_dst] >= 0
    )
    edge_index = np.flatnonzero(mask)
    local_src = local_of_full[graph.edge_src[edge_index]]
    local_dst = local_of_full[graph.edge_dst[edge_index]]
    weights = graph.edge_weight[edge_index].astype(np.int32, copy=False)

    order = np.lexsort((local_dst, local_src))
    local_src = local_src[order]
    local_dst = local_dst[order]
    weights = weights[order]

    n = selected.size
    out_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(np.bincount(local_src, minlength=n), out=out_indptr[1:])
    in_order = np.argsort(local_dst, kind="stable").astype(np.int32)
    in_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(np.bincount(local_dst, minlength=n), out=in_indptr[1:])

    return GraphView(
        root_ids=graph.root_ids[selected].astype(np.int64, copy=False),
        node_map=selected.astype(np.int64, copy=False),
        out_indptr=out_indptr,
        edge_src=local_src.astype(np.int32, copy=False),
        edge_dst=local_dst.astype(np.int32, copy=False),
        edge_weight=weights,
        in_indptr=in_indptr,
        in_edge_idx=in_order,
        nt_code=graph.nt_code[selected].astype(np.int16, copy=False),
        super_class_code=graph.super_class_code[selected].astype(
            np.int16, copy=False
        ),
        class_code=graph.class_code[selected].astype(np.int16, copy=False),
        side_code=graph.side_code[selected].astype(np.int16, copy=False),
        positions=graph.positions[selected].astype(np.float32, copy=False),
        vocabulary=graph.vocabulary,
        source_n_nodes=n_full,
        source_n_edges=graph.n_edges,
    )


def weak_component_count(graph: GraphView) -> tuple[int, int]:
    """Return (component count, largest component size) ignoring direction."""
    n = graph.n_nodes
    parent = np.arange(n, dtype=np.int64)
    rank = np.zeros(n, dtype=np.int8)

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = int(parent[root])
        while parent[node] != node:
            parent[node], node = root, int(parent[node])
        return root

    for src, dst in zip(graph.edge_src, graph.edge_dst):
        root_src, root_dst = find(int(src)), find(int(dst))
        if root_src == root_dst:
            continue
        if rank[root_src] < rank[root_dst]:
            root_src, root_dst = root_dst, root_src
        parent[root_dst] = root_src
        if rank[root_src] == rank[root_dst]:
            rank[root_src] += 1

    roots = np.array([find(node) for node in range(n)], dtype=np.int64)
    counts = np.bincount(roots)
    return int(np.count_nonzero(counts)), int(counts.max())


def _class_codes(graph: GraphView) -> np.ndarray:
    return graph.super_class_code.astype(np.int32) + 1


def _distribution(codes: np.ndarray, selected: np.ndarray) -> np.ndarray:
    counts = np.bincount(codes[selected], minlength=int(codes.max()) + 1)
    total = counts.sum()
    if total == 0:
        return counts.astype(np.float64)
    return counts.astype(np.float64) / total


def _composition_distance(
    graph: GraphView, selected: np.ndarray, eligible: np.ndarray
) -> tuple[float, float]:
    class_dist = 0.5 * np.abs(
        _distribution(_class_codes(graph), selected)
        - _distribution(_class_codes(graph), np.flatnonzero(eligible))
    ).sum()
    nt_codes = graph.nt_code.astype(np.int32) + 1
    nt_dist = 0.5 * np.abs(
        _distribution(nt_codes, selected)
        - _distribution(nt_codes, np.flatnonzero(eligible))
    ).sum()
    return float(class_dist), float(nt_dist)


def _eligible_mask(graph: GraphView, min_degree: int) -> np.ndarray:
    return total_degrees(graph) >= max(1, int(min_degree))


def _candidate_seeds(
    graph: GraphView,
    eligible: np.ndarray,
    rng: np.random.Generator,
    per_class: int,
    n_random: int,
) -> np.ndarray:
    nodes = np.flatnonzero(eligible)
    degrees = total_degrees(graph)
    seeds: list[int] = []
    classes = graph.super_class_code
    for code in np.unique(classes[nodes]):
        class_nodes = nodes[classes[nodes] == code]
        order = np.lexsort((class_nodes, -degrees[class_nodes]))
        seeds.extend(int(value) for value in class_nodes[order[:per_class]])
    if n_random > 0 and len(nodes):
        random_nodes = rng.choice(
            nodes, size=min(n_random, len(nodes)), replace=False
        )
        seeds.extend(int(value) for value in random_nodes)
    return np.unique(np.asarray(seeds, dtype=np.int64))


def _bfs_sample(
    graph: GraphView,
    start: int,
    target: int,
    eligible: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    n = graph.n_nodes
    visited = np.zeros(n, dtype=bool)
    visited[start] = True
    selected = [start]
    frontier = [start]

    while frontier and len(selected) < target:
        pick = int(rng.integers(len(frontier)))
        node = frontier[pick]
        frontier[pick] = frontier[-1]
        frontier.pop()

        out_start, out_stop = graph.out_indptr[node], graph.out_indptr[node + 1]
        in_start, in_stop = graph.in_indptr[node], graph.in_indptr[node + 1]
        neighbours = np.concatenate(
            (
                graph.edge_dst[out_start:out_stop],
                graph.edge_src[graph.in_edge_idx[in_start:in_stop]],
            )
        )
        neighbours = neighbours[eligible[neighbours] & ~visited[neighbours]]
        if neighbours.size == 0:
            continue
        neighbours = np.unique(neighbours)
        rng.shuffle(neighbours)
        for neighbour in neighbours:
            value = int(neighbour)
            visited[value] = True
            selected.append(value)
            frontier.append(value)
            if len(selected) >= target:
                break

    return np.sort(np.asarray(selected, dtype=np.int64))


def sample_connected_neurons(
    graph: GraphView,
    n_neurons: int,
    seed: int,
    min_degree: int = 5,
    candidate_seeds_per_class: int = 3,
    random_candidate_seeds: int = 10,
) -> SampleSelection:
    """Sample a reproducible, weakly connected, class-aware neuron subset."""
    if n_neurons < 2:
        raise ValueError("n_neurons must be at least 2")
    if n_neurons > graph.n_nodes:
        raise ValueError("n_neurons exceeds the graph size")

    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    effective_min_degree = int(min_degree)
    eligible = _eligible_mask(graph, effective_min_degree)
    if int(eligible.sum()) < n_neurons:
        effective_min_degree = 0
        eligible = np.ones(graph.n_nodes, dtype=bool)

    candidates = _candidate_seeds(
        graph,
        eligible,
        rng,
        max(1, candidate_seeds_per_class),
        random_candidate_seeds,
    )
    best_nodes: np.ndarray | None = None
    best_seed = -1
    best_score = np.inf

    for candidate in candidates:
        candidate_rng = np.random.default_rng([int(seed), int(candidate)])
        nodes = _bfs_sample(
            graph, int(candidate), int(n_neurons), eligible, candidate_rng
        )
        if len(nodes) < n_neurons:
            continue
        class_distance, nt_distance = _composition_distance(graph, nodes, eligible)
        score = class_distance + nt_distance
        if score < best_score - 1e-12:
            best_score = score
            best_nodes = nodes
            best_seed = int(candidate)

    if best_nodes is None:
        fallback = int(np.argmax(total_degrees(graph)))
        fallback_rng = np.random.default_rng([int(seed), fallback])
        best_nodes = _bfs_sample(
            graph,
            fallback,
            int(n_neurons),
            np.ones(graph.n_nodes, dtype=bool),
            fallback_rng,
        )
        if len(best_nodes) < n_neurons:
            raise RuntimeError(
                "could not grow a connected sample of the requested size; "
                "reduce n_neurons or min_degree"
            )
        best_seed = fallback
        effective_min_degree = 0

    return SampleSelection(
        node_indices=best_nodes,
        target=int(n_neurons),
        seed_node_index=best_seed,
        candidate_count=int(len(candidates)),
        effective_min_degree=effective_min_degree,
        eligible_count=int(eligible.sum()),
        sampling_seconds=round(time.perf_counter() - started, 3),
    )
