"""Target-exchange randomization with the Phase 8 §3.3.1 R1–R18 report.

SCIENTIFIC STATUS
    A randomized graph is a null model, not a biological network. Preserving
    degrees, signs and per-source weights makes it a constrained null; it is
    not evidence that the biological wiring is or is not special.

The construction is **target exchange** (U18): an edge keeps its source and
its weight, and a swap exchanges the targets of two edges whose sources and
targets are all distinct. Therefore out-degree, in-degree, the global weight
multiset and every source's outgoing weight multiset are preserved by
construction; which source talks to which target is not.

A Jaccard plateau in R14 is a diagnostic on the rewiring distance. It is not a
proof that the swap chain has mixed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from brain.banc_graph import BancConnectome

REJECTION_REASONS = (
    "duplicate_pair",
    "self_loop",
    "no_change",
    "out_of_range",
)


def graph_digest(graph: BancConnectome) -> str:
    digest = hashlib.sha256()
    for name in (
        "root_ids",
        "out_indptr",
        "edge_src",
        "edge_dst",
        "edge_weight",
    ):
        array = np.ascontiguousarray(getattr(graph, name))
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("utf-8"))
        digest.update(str(array.shape).encode("utf-8"))
        digest.update(array.tobytes())
    digest.update(str(int(graph.threshold)).encode("utf-8"))
    return digest.hexdigest()


@dataclass
class RandomizationResult:
    graph: BancConnectome
    seed: int
    swaps_per_edge: float
    target_accepted: int
    attempted: int
    accepted: int
    rejected: dict[str, int] = field(default_factory=dict)
    intersection: int = 0
    jaccard: float = 1.0
    jaccard_history: list[tuple[int, float]] = field(default_factory=list)
    edge_order: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))

    @property
    def complete(self) -> bool:
        return self.accepted >= self.target_accepted

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.attempted if self.attempted else 0.0

    @property
    def fraction_rewired(self) -> float:
        total = int(self.graph.n_edges)
        return 1.0 - self.intersection / total if total else 0.0

    def summary(self) -> dict:
        return {
            "construction": "target_exchange",
            "seed": int(self.seed),
            "swaps_per_edge": float(self.swaps_per_edge),
            "target_accepted": int(self.target_accepted),
            "attempted": int(self.attempted),
            "accepted": int(self.accepted),
            "rejected": {name: int(self.rejected.get(name, 0)) for name in REJECTION_REASONS},
            "acceptance_rate": round(self.acceptance_rate, 9),
            "fraction_of_original_edges_rewired": round(self.fraction_rewired, 9),
            "jaccard_vs_original": round(float(self.jaccard), 9),
            "complete": bool(self.complete),
            "graph_digest": graph_digest(self.graph),
        }


def _packed_keys(src: np.ndarray, dst: np.ndarray, n_nodes: int) -> np.ndarray:
    return src.astype(np.int64) * np.int64(n_nodes) + dst.astype(np.int64)


def _build_graph(
    original: BancConnectome,
    src: np.ndarray,
    dst: np.ndarray,
    weight: np.ndarray,
) -> tuple[BancConnectome, np.ndarray]:
    order = np.lexsort((dst, src)).astype(np.int64)
    new_src = src[order]
    new_dst = dst[order]
    new_weight = weight[order]
    n = int(original.n_nodes)
    out_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(np.bincount(new_src, minlength=n), out=out_indptr[1:])
    in_indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(np.bincount(new_dst, minlength=n), out=in_indptr[1:])
    graph = BancConnectome(
        root_ids=original.root_ids,
        out_indptr=out_indptr,
        edge_src=new_src.astype(np.int32, copy=False),
        edge_dst=new_dst.astype(np.int32, copy=False),
        edge_weight=new_weight.astype(np.int32, copy=False),
        in_indptr=in_indptr,
        in_edge_idx=np.argsort(new_dst, kind="stable").astype(np.int32),
        threshold=original.threshold,
        banc_ids=original.banc_ids,
        positions=original.positions,
        position_mask=original.position_mask,
        meta=dict(original.meta or {}),
    )
    return graph, order


def rewire_target_exchange(
    graph: BancConnectome,
    *,
    seed: int,
    swaps_per_edge: float = 10.0,
    max_attempts: int | None = None,
    plateau_interval: int = 100_000,
) -> RandomizationResult:
    """Build one degree- and weight-preserving null graph."""
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    rate = float(swaps_per_edge)
    if not np.isfinite(rate) or rate < 0:
        raise ValueError("swaps_per_edge must be finite and non-negative")
    interval = int(plateau_interval)
    if interval < 1:
        raise ValueError("plateau_interval must be positive")

    n = int(graph.n_nodes)
    src = np.asarray(graph.edge_src, dtype=np.int64).copy()
    dst = np.asarray(graph.edge_dst, dtype=np.int64).copy()
    weight = np.asarray(graph.edge_weight, dtype=np.int64).copy()
    m = int(src.size)
    if m == 0:
        raise ValueError("graph has no edges to randomize")

    target = int(round(rate * m))
    attempt_cap = (
        int(max_attempts)
        if max_attempts is not None
        else max(20 * target, 1)
    )
    if attempt_cap < 0:
        raise ValueError("max_attempts cannot be negative")

    rng = np.random.default_rng(int(seed))
    keys = set(_packed_keys(src, dst, n).tolist())
    original_sorted = np.sort(_packed_keys(src, dst, n))
    intersection = m

    def in_original(values: np.ndarray) -> int:
        positions = np.searchsorted(original_sorted, values)
        positions = np.clip(positions, 0, original_sorted.size - 1)
        return int(np.count_nonzero(original_sorted[positions] == values))

    rejected = {name: 0 for name in REJECTION_REASONS}
    accepted = 0
    attempted = 0
    history: list[tuple[int, float]] = []
    while accepted < target and attempted < attempt_cap:
        attempted += 1
        i, j = (int(value) for value in rng.integers(0, m, size=2))
        si, sj = int(src[i]), int(src[j])
        di, dj = int(dst[i]), int(dst[j])
        if si == sj or di == dj:
            rejected["no_change"] += 1
            continue
        if dj == si or di == sj:
            rejected["self_loop"] += 1
            continue
        old_i = np.array([si * n + di], dtype=np.int64)
        old_j = np.array([sj * n + dj], dtype=np.int64)
        new_i = np.array([si * n + dj], dtype=np.int64)
        new_j = np.array([sj * n + di], dtype=np.int64)
        if int(new_i[0]) in keys or int(new_j[0]) in keys:
            rejected["duplicate_pair"] += 1
            continue

        keys.discard(int(old_i[0]))
        keys.discard(int(old_j[0]))
        keys.add(int(new_i[0]))
        keys.add(int(new_j[0]))
        intersection -= in_original(old_i) + in_original(old_j)
        intersection += in_original(new_i) + in_original(new_j)
        dst[i] = dj
        dst[j] = di
        accepted += 1
        if accepted % interval == 0:
            jaccard = intersection / (2 * m - intersection)
            history.append((accepted, float(jaccard)))

    jaccard = intersection / (2 * m - intersection)
    new_graph, order = _build_graph(graph, src, dst, weight)
    return RandomizationResult(
        graph=new_graph,
        seed=int(seed),
        swaps_per_edge=rate,
        target_accepted=target,
        attempted=attempted,
        accepted=accepted,
        rejected=rejected,
        intersection=intersection,
        jaccard=float(jaccard),
        jaccard_history=history,
        edge_order=order,
    )


# ---------------------------------------------------------------------------
# R1-R18 report
# ---------------------------------------------------------------------------


def _max_abs_degree_change(original: np.ndarray, new: np.ndarray) -> int:
    return int(np.max(np.abs(new.astype(np.int64) - original.astype(np.int64))))


def _neighbour_overlap(original: BancConnectome, new: BancConnectome) -> dict:
    """Return R13's mean neighbourhood Jaccard under both denominators.

    REV3 §3.3.1 R13 says "mean over nodes ... unweighted". A node whose
    out-neighbourhood is empty in both graphs has an undefined Jaccard, not a
    perfect one. Counting it as 1.0 would put the BANC graph's 24,320 isolated
    nodes at >= 0.14 before any swap and make the gate unsatisfiable. The gated
    value therefore averages over nodes that have an out-neighbour in at least
    one graph; the literal all-node value is reported next to it.
    """
    n = int(original.n_nodes)
    if int(new.n_nodes) != n:
        raise ValueError("graphs have different node counts")
    old_sets = [
        set(original.edge_dst[original.out_indptr[i] : original.out_indptr[i + 1]].tolist())
        for i in range(n)
    ]
    new_sets = [
        set(new.edge_dst[new.out_indptr[i] : new.out_indptr[i + 1]].tolist())
        for i in range(n)
    ]
    total = 0.0
    literal_total = 0.0
    active = 0
    for left, right in zip(old_sets, new_sets):
        union = left | right
        if not union:
            literal_total += 1.0
            continue
        value = len(left & right) / len(union)
        total += value
        literal_total += value
        active += 1
    return {
        "mean_over_active_nodes": total / active if active else 0.0,
        "mean_over_all_nodes": literal_total / n if n else 0.0,
        "active_nodes": active,
        "isolated_in_both": n - active,
        "statistic": "mean_over_active_nodes",
    }


def _weak_components(graph: BancConnectome) -> dict[str, Any]:
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components

    n = int(graph.n_nodes)
    matrix = csr_matrix(
        (
            np.ones(graph.n_edges, dtype=np.int8),
            (graph.edge_src, graph.edge_dst),
        ),
        shape=(n, n),
    )
    count, labels = connected_components(matrix, directed=True, connection="weak")
    sizes = np.bincount(labels, minlength=count)
    order = np.sort(sizes)[::-1]
    return {
        "n_components": int(count),
        "largest_component": int(order[0]) if order.size else 0,
        "size_histogram": {
            str(int(size)): int(np.count_nonzero(sizes == size))
            for size in np.unique(sizes)
        },
    }


def _reciprocity(graph: BancConnectome) -> float:
    n = int(graph.n_nodes)
    keys = set(_packed_keys(
        np.asarray(graph.edge_src, dtype=np.int64),
        np.asarray(graph.edge_dst, dtype=np.int64),
        n,
    ).tolist())
    reverse = _packed_keys(
        np.asarray(graph.edge_dst, dtype=np.int64),
        np.asarray(graph.edge_src, dtype=np.int64),
        n,
    )
    reciprocal = sum(1 for value in reverse.tolist() if value in keys)
    return reciprocal / int(graph.n_edges) if graph.n_edges else 0.0


def _degree_assortativity(graph: BancConnectome) -> float | None:
    src = np.asarray(graph.edge_src, dtype=np.int64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    out_degree = np.diff(graph.out_indptr)
    in_degree = np.diff(graph.in_indptr)
    left = (out_degree + in_degree)[src].astype(np.float64)
    right = (out_degree + in_degree)[dst].astype(np.float64)
    if left.size < 2 or left.std() == 0 or right.std() == 0:
        return None
    return round(float(np.corrcoef(left, right)[0, 1]), 9)


def validate_randomization(
    original: BancConnectome,
    result: RandomizationResult,
    *,
    policy_original: Any | None = None,
    policy_new: Any | None = None,
    reference_digest: str | None = None,
    include_components: bool = True,
) -> dict:
    """Evaluate the §3.3.1 gates and return the full report."""
    new = result.graph
    n = int(original.n_nodes)
    m = int(original.n_edges)
    if int(new.n_edges) != m:
        raise ValueError("randomized graph changed the edge count")

    out_original = np.diff(original.out_indptr)
    out_new = np.diff(new.out_indptr)
    in_original = np.diff(original.in_indptr)
    in_new = np.diff(new.in_indptr)

    report: dict[str, Any] = {}
    report["R1"] = {"swaps_attempted": int(result.attempted)}
    report["R2"] = {"swaps_accepted": int(result.accepted)}
    report["R3"] = {
        "swaps_rejected": {
            name: int(result.rejected.get(name, 0)) for name in REJECTION_REASONS
        },
        "acceptance_rate": round(float(result.acceptance_rate), 9),
        "progress": bool(result.accepted > 0),
    }
    report["R4"] = {
        "fraction_rewired": round(float(result.fraction_rewired), 9),
        "gate": 0.99,
        "pass": bool(result.fraction_rewired >= 0.99),
    }
    report["R5"] = {
        "jaccard": round(float(result.jaccard), 9),
        "gate": 0.01,
        "pass": bool(result.jaccard <= 0.01),
    }
    out_change = _max_abs_degree_change(out_original, out_new)
    report["R6"] = {
        "max_abs_out_degree_change": out_change,
        "out_degree_sum": int(out_new.sum()),
        "expected_sum": m,
        "pass": bool(out_change == 0 and int(out_new.sum()) == m),
    }
    in_change = _max_abs_degree_change(in_original, in_new)
    report["R7"] = {
        "max_abs_in_degree_change": in_change,
        "in_degree_sum": int(in_new.sum()),
        "expected_sum": m,
        "pass": bool(in_change == 0 and int(in_new.sum()) == m),
    }

    if policy_original is not None and policy_new is not None:
        order = np.asarray(result.edge_order, dtype=np.int64)
        exc_equal = np.array_equal(
            np.asarray(policy_new.edge_exc_weight),
            np.asarray(policy_original.edge_exc_weight)[order],
        )
        inh_equal = np.array_equal(
            np.asarray(policy_new.edge_inh_weight),
            np.asarray(policy_original.edge_inh_weight)[order],
        )
        signed_original = int(
            np.count_nonzero(policy_original.edge_exc_weight)
            + np.count_nonzero(policy_original.edge_inh_weight)
        )
        signed_new = int(
            np.count_nonzero(policy_new.edge_exc_weight)
            + np.count_nonzero(policy_new.edge_inh_weight)
        )
        report["R8"] = {
            "evaluated": True,
            "per_edge_sign_reordering_equal": bool(exc_equal and inh_equal),
            "signed_edges_original": signed_original,
            "signed_edges_new": signed_new,
            "pass": bool(exc_equal and inh_equal and signed_original == signed_new),
        }
    else:
        report["R8"] = {
            "evaluated": False,
            "reason": "policies were not supplied; per-edge sign was not checked",
            "pass": False,
        }

    weight_original = np.sort(np.asarray(original.edge_weight, dtype=np.int64))
    weight_new = np.sort(np.asarray(new.edge_weight, dtype=np.int64))
    report["R9"] = {
        "multiset_equal": bool(np.array_equal(weight_original, weight_new)),
        "synapse_sum": int(weight_new.sum()),
        "min": int(weight_new.min()) if weight_new.size else None,
        "max": int(weight_new.max()) if weight_new.size else None,
        "pass": bool(np.array_equal(weight_original, weight_new)),
    }

    def source_weight_order(graph):
        source = np.asarray(graph.edge_src, dtype=np.int64)
        weight = np.asarray(graph.edge_weight, dtype=np.int64)
        rank = np.lexsort((weight, source))
        return source[rank], weight[rank]

    src_o, w_o = source_weight_order(original)
    src_n, w_n = source_weight_order(new)
    per_source_equal = bool(
        np.array_equal(src_o, src_n) and np.array_equal(w_o, w_n)
    )
    report["R9b"] = {
        "per_source_weight_multiset_equal": per_source_equal,
        "pass": per_source_equal,
    }

    new_keys = _packed_keys(
        np.asarray(new.edge_src, dtype=np.int64),
        np.asarray(new.edge_dst, dtype=np.int64),
        n,
    )
    report["R10"] = {
        "duplicate_pairs": int(m - np.unique(new_keys).size),
        "pass": bool(np.unique(new_keys).size == m),
    }
    self_edges = int(np.count_nonzero(np.asarray(new.edge_src) == np.asarray(new.edge_dst)))
    report["R11"] = {"self_edges": self_edges, "pass": self_edges == 0}

    csr_ok = bool(
        np.array_equal(
            new.out_indptr,
            np.concatenate(
                (
                    np.zeros(1, dtype=np.int64),
                    np.cumsum(np.bincount(new.edge_src, minlength=n)),
                )
            ),
        )
        and np.array_equal(
            new.in_indptr,
            np.concatenate(
                (
                    np.zeros(1, dtype=np.int64),
                    np.cumsum(np.bincount(new.edge_dst, minlength=n)),
                )
            ),
        )
    )
    destinations = np.asarray(new.edge_dst)[new.in_edge_idx]
    csr_ok = csr_ok and bool(np.all(np.diff(destinations) >= 0))
    report["R12"] = {"csr_invariants_pass": csr_ok, "pass": csr_ok}

    overlap = _neighbour_overlap(original, new)
    report["R13"] = {
        "mean_out_neighbour_jaccard": round(
            float(overlap["mean_over_active_nodes"]), 9
        ),
        "mean_out_neighbour_jaccard_all_nodes": round(
            float(overlap["mean_over_all_nodes"]), 9
        ),
        "active_nodes": int(overlap["active_nodes"]),
        "isolated_in_both": int(overlap["isolated_in_both"]),
        "statistic": overlap["statistic"],
        "gate": 0.01,
        "pass": bool(overlap["mean_over_active_nodes"] <= 0.01),
        "note": (
            "gated value averages over nodes with an out-neighbour in at "
            "least one graph; Jaccard(empty, empty) is undefined, not 1.0"
        ),
    }

    history = result.jaccard_history
    final_accepted = max(int(result.accepted), 1)
    tail = [value for accepted, value in history if accepted >= 0.8 * final_accepted]
    if len(tail) >= 2:
        change = max(tail) - min(tail)
        report["R14"] = {
            "evaluated": True,
            "tail_samples": len(tail),
            "max_abs_change": round(float(change), 12),
            "gate": 1.0e-4,
            "pass": bool(change < 1.0e-4),
            "note": "plateau diagnostic on the rewiring distance, not mixing",
        }
    else:
        report["R14"] = {
            "evaluated": False,
            "tail_samples": len(tail),
            "pass": False,
            "note": (
                "too few accepted-swap checkpoints for a plateau; the chain "
                "cannot be reported as randomized"
            ),
        }

    if include_components:
        before = _weak_components(original)
        after = _weak_components(new)
        report["R15"] = {
            "before": before,
            "after": after,
            "changed": before != after,
            "gated": False,
        }
    else:
        report["R15"] = {"evaluated": False, "gated": False}

    report["R16"] = {
        "reciprocity_before": round(_reciprocity(original), 9),
        "reciprocity_after": round(_reciprocity(new), 9),
        "degree_assortativity_before": _degree_assortativity(original),
        "degree_assortativity_after": _degree_assortativity(new),
        "gated": False,
    }

    digest = graph_digest(new)
    if reference_digest is None:
        report["R17"] = {
            "evaluated": False,
            "graph_digest": digest,
            "pass": False,
            "note": "a second same-seed build must be supplied for R17",
        }
    else:
        report["R17"] = {
            "evaluated": True,
            "graph_digest": digest,
            "reference_digest": str(reference_digest),
            "pass": bool(digest == reference_digest),
        }

    report["R18"] = {
        "seed": int(result.seed),
        "stream": "structure",
        "recorded": True,
        "note": "the seed is the already-derived structure-stream value",
    }

    failures = [
        name
        for name in ("R4", "R5", "R6", "R7", "R8", "R9", "R9b", "R10",
                     "R11", "R12", "R13", "R14", "R17")
        if not report[name]["pass"]
    ]
    return {
        "construction": "target_exchange",
        "graph_digest": digest,
        "gates": report,
        "failures": failures,
        "passed": not failures,
        "summary": result.summary(),
    }


def describe_randomization() -> dict:
    return {
        "construction": "target_exchange",
        "edge_identity": "source and weight are fixed; only targets swap",
        "preserved": [
            "per-node out-degree",
            "per-node in-degree",
            "global weight multiset",
            "every source's outgoing weight multiset",
            "per-node transmitter sign (identities are not permuted)",
        ],
        "not_preserved": [
            "weak-component sizes",
            "which source talks to which target",
            "per-target incoming weight sums",
        ],
        "gates": [f"R{index}" for index in range(1, 19)],
        "plateau_note": (
            "R14 is a diagnostic on the rewiring distance; a Jaccard plateau "
            "is not a proof of Markov-chain mixing"
        ),
    }
