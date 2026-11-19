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

IMPLEMENTATION NOTES
    The candidate stream is generated in fixed 4,096-candidate blocks, each
    from ``SeedSequence([seed, block_index])``. The stream is therefore a pure
    function of ``(seed, n_edges)`` and does not depend on how the caller
    chooses to batch evaluation, so ``batch_size`` changes peak memory only,
    never the produced graph. Candidates are applied sequentially in stream
    order, which is what makes that invariance hold.

    The running edge-set intersection is recomputed from the arrays at every
    R14 checkpoint instead of being maintained per swap. This removes four
    binary searches from the inner loop and is exact.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from brain.banc_graph import BancConnectome

REJECTION_REASONS = (
    "duplicate_pair",
    "self_loop",
    "no_change",
    "out_of_range",
)

#: Declared algorithm constants. Recorded in every certificate; the produced
#: graph is a function of the seed and these values (see IMPLEMENTATION NOTES).
CANDIDATE_BLOCK = 4096
DEFAULT_BATCH_SIZE = 100_000
DEFAULT_PLATEAU_INTERVAL = 100_000

_STRUCTURE_STREAM_CODE = 4


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


class MemoryTrace:
    """Coarse memory telemetry; sampling is explicit, not continuous."""

    def __init__(self) -> None:
        self.checkpoints: list[dict[str, Any]] = []
        self._psutil = None
        try:  # pragma: no cover - exercises only when psutil is present
            import psutil

            self._psutil = psutil
        except ImportError:  # pragma: no cover
            self._psutil = None

    def sample(self, label: str) -> dict[str, Any]:
        record: dict[str, Any] = {"label": str(label)}
        if self._psutil is not None:
            details = self._psutil.Process().memory_info()
            record["rss_mb"] = round(float(details.rss) / 1024.0**2, 3)
            info = self._psutil.virtual_memory()
            record["available_gb"] = round(float(info.available) / 1024.0**3, 3)
        self.checkpoints.append(record)
        return record

    @property
    def peak_rss_mb(self) -> float | None:
        values = [c["rss_mb"] for c in self.checkpoints if "rss_mb" in c]
        return max(values) if values else None

    @property
    def min_available_gb(self) -> float | None:
        values = [c["available_gb"] for c in self.checkpoints if "available_gb" in c]
        return min(values) if values else None

    def summary(self) -> dict[str, Any]:
        return {
            "sampling": "explicit checkpoints; not a continuous peak measurement",
            "peak_rss_mb": self.peak_rss_mb,
            "min_available_gb": self.min_available_gb,
            "checkpoints": list(self.checkpoints),
        }


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
    batch_size: int = DEFAULT_BATCH_SIZE
    plateau_interval: int = DEFAULT_PLATEAU_INTERVAL
    max_attempts: int = 0
    elapsed_seconds: float = 0.0
    memory: dict[str, Any] = field(default_factory=dict)

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

    @property
    def incomplete_reason(self) -> str | None:
        if self.complete:
            return None
        return "attempt_cap_reached_before_target_accepted"

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
            "incomplete_reason": self.incomplete_reason,
            "graph_digest": graph_digest(self.graph),
            "algorithm": {
                "candidate_block": CANDIDATE_BLOCK,
                "batch_size": int(self.batch_size),
                "plateau_interval": int(self.plateau_interval),
                "max_attempts": int(self.max_attempts),
            },
            "elapsed_seconds": round(float(self.elapsed_seconds), 3),
            "memory": dict(self.memory),
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


class _CandidateStream:
    """Fixed-block candidate stream, independent of evaluation batching."""

    def __init__(self, seed: int, n_edges: int) -> None:
        self._seed = int(seed)
        self._n_edges = int(n_edges)
        self._block = 0
        self._buffer = np.empty((0, 2), dtype=np.int64)

    def take(self, count: int) -> np.ndarray:
        while self._buffer.shape[0] < count:
            sequence = np.random.SeedSequence([self._seed, self._block])
            self._block += 1
            generator = np.random.default_rng(sequence)
            block = generator.integers(
                0, self._n_edges, size=(CANDIDATE_BLOCK, 2), dtype=np.int64
            )
            self._buffer = np.vstack((self._buffer, block))
        out = self._buffer[:count]
        self._buffer = self._buffer[count:]
        return out


def _intersection_size(original_sorted: np.ndarray, keys: np.ndarray) -> int:
    """Exact |E_orig ∩ E_new| for duplicate-free edge sets."""
    current = np.sort(keys)
    return int(np.intersect1d(original_sorted, current, assume_unique=True).size)


def rewire_target_exchange(
    graph: BancConnectome,
    *,
    seed: int,
    swaps_per_edge: float = 10.0,
    max_attempts: int | None = None,
    plateau_interval: int = DEFAULT_PLATEAU_INTERVAL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> RandomizationResult:
    """Build one degree- and weight-preserving null graph.

    ``batch_size`` controls peak memory during the swap loop only. The
    candidate stream is block-derived from the seed, so every batch size
    produces the same graph.
    """
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    rate = float(swaps_per_edge)
    if not np.isfinite(rate) or rate < 0:
        raise ValueError("swaps_per_edge must be finite and non-negative")
    interval = int(plateau_interval)
    if interval < 1:
        raise ValueError("plateau_interval must be positive")
    batch = int(batch_size)
    if batch < 1:
        raise ValueError("batch_size must be positive")

    started = time.perf_counter()
    trace = MemoryTrace()
    trace.sample("graph_loaded")

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

    original_sorted = np.sort(_packed_keys(src, dst, n))
    keys = set(_packed_keys(src, dst, n).tolist())
    trace.sample("edge_sets_built")

    stream = _CandidateStream(int(seed), m)
    rejected = {name: 0 for name in REJECTION_REASONS}
    accepted = 0
    attempted = 0
    history: list[tuple[int, float]] = []
    n_nodes = n

    while accepted < target and attempted < attempt_cap:
        take = min(batch, attempt_cap - attempted)
        pairs = stream.take(take)

        candidates = zip(pairs[:, 0].tolist(), pairs[:, 1].tolist())
        for edge_i, edge_j in candidates:
            attempted += 1
            si = int(src[edge_i])
            sj = int(src[edge_j])
            if si == sj:
                rejected["no_change"] += 1
                continue
            di = int(dst[edge_i])
            dj = int(dst[edge_j])
            if di == dj:
                rejected["no_change"] += 1
                continue
            if dj == si or di == sj:
                rejected["self_loop"] += 1
                continue
            new_i = si * n_nodes + dj
            new_j = sj * n_nodes + di
            if new_i in keys or new_j in keys:
                rejected["duplicate_pair"] += 1
                continue
            keys.discard(si * n_nodes + di)
            keys.discard(sj * n_nodes + dj)
            keys.add(new_i)
            keys.add(new_j)
            dst[edge_i] = dj
            dst[edge_j] = di
            accepted += 1
            if accepted % interval == 0:
                intersection = _intersection_size(
                    original_sorted, _packed_keys(src, dst, n_nodes)
                )
                history.append((accepted, intersection / (2 * m - intersection)))
                del intersection
                trace.sample(f"accepted_{accepted}")
            if accepted >= target:
                break

    del keys
    trace.sample("swap_loop_finished")

    current_keys = _packed_keys(src, dst, n)
    intersection = _intersection_size(original_sorted, current_keys)
    del current_keys
    jaccard = intersection / (2 * m - intersection)

    new_graph, order = _build_graph(graph, src, dst, weight)
    del src, dst, weight
    trace.sample("graph_built")

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
        batch_size=batch,
        plateau_interval=interval,
        max_attempts=attempt_cap,
        elapsed_seconds=time.perf_counter() - started,
        memory=trace.summary(),
    )


# ---------------------------------------------------------------------------
# R1-R18 report
# ---------------------------------------------------------------------------


def _max_abs_degree_change(original: np.ndarray, new: np.ndarray) -> int:
    return int(np.max(np.abs(new.astype(np.int64) - original.astype(np.int64))))


def _neighbour_overlap(original: BancConnectome, new: BancConnectome) -> dict:
    """R13's mean out-neighbour Jaccard, computed exactly without per-node sets.

    ``E = src * n + dst`` is sorted by ``(src, dst)`` inside each source because
    both graphs store their edges in that order and hold no duplicate pair.
    A global intersection therefore yields a per-source intersection count by
    ``bincount(common // n)``.

    A node whose out-neighbourhood is empty in both graphs has an undefined
    Jaccard, not a perfect one. Counting it as 1.0 would put BANC's 24,320
    isolated nodes at >= 0.14 before any swap and make the gate unsatisfiable.
    The gated value averages over nodes with an out-neighbour in at least one
    graph; the literal all-node value is reported next to it (REV4 §3.3.1).
    """
    n = int(original.n_nodes)
    if int(new.n_nodes) != n:
        raise ValueError("graphs have different node counts")
    old_keys = _packed_keys(original.edge_src, original.edge_dst, n)
    new_keys = _packed_keys(new.edge_src, new.edge_dst, n)
    if np.unique(old_keys).size != old_keys.size or np.unique(new_keys).size != new_keys.size:
        raise ValueError("R13 requires duplicate-free edge sets")
    common = np.intersect1d(
        np.sort(old_keys), np.sort(new_keys), assume_unique=True
    )
    intersection_per_source = np.bincount(common // np.int64(n), minlength=n)
    out_original = np.diff(original.out_indptr)
    out_new = np.diff(new.out_indptr)
    union = out_original + out_new - intersection_per_source
    active = union > 0
    per_node = intersection_per_source[active] / union[active]
    active_count = int(np.count_nonzero(active))
    total_active = float(per_node.sum()) if active_count else 0.0
    literal_total = total_active + float(n - active_count)
    return {
        "mean_over_active_nodes": total_active / active_count if active_count else 0.0,
        "mean_over_all_nodes": literal_total / n if n else 0.0,
        "active_nodes": active_count,
        "isolated_in_both": n - active_count,
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
    keys = np.sort(_packed_keys(graph.edge_src, graph.edge_dst, n))
    reverse = _packed_keys(graph.edge_dst, graph.edge_src, n)
    positions = np.searchsorted(keys, reverse)
    np.clip(positions, 0, keys.size - 1, out=positions)
    reciprocal = int(np.count_nonzero(keys[positions] == reverse))
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


def _signed_edge_summary(graph: BancConnectome, policy: Any) -> dict[str, int]:
    signs = np.asarray(policy.neuron_signs)[np.asarray(graph.edge_src, dtype=np.int64)]
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    signed = signs != 0
    return {
        "signed_edges": int(np.count_nonzero(signed)),
        "signed_synapses": int(weight[signed].sum()),
        "unsigned_edges": int(np.count_nonzero(~signed)),
        "unsigned_synapses": int(weight[~signed].sum()),
    }


def _derive_structure_seed(master_seed: int, campaign_seed: int) -> int:
    """Match ``experiments.phase_8.seeds`` exactly (uint32 draw, code 4)."""
    from experiments.phase_8.seeds import structure_sequence

    sequence = structure_sequence(int(master_seed), int(campaign_seed))
    return int(sequence.generate_state(1, np.uint32)[0])


def validate_randomization(
    original: BancConnectome,
    result: RandomizationResult,
    *,
    policy_original: Any | None = None,
    policy_new: Any | None = None,
    reference_digest: str | None = None,
    include_components: bool = True,
    master_seed: int | None = None,
    campaign_seed: int | None = None,
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

    # Independent recomputation of the rewiring distance; the construction
    # counter is never trusted on its own.
    original_keys = _packed_keys(original.edge_src, original.edge_dst, n)
    new_keys = _packed_keys(new.edge_src, new.edge_dst, n)
    intersection = int(
        np.intersect1d(
            np.sort(original_keys), np.sort(new_keys), assume_unique=True
        ).size
    )
    jaccard = intersection / (2 * m - intersection)
    fraction_rewired = 1.0 - intersection / m
    intersection_matches = intersection == int(result.intersection)

    report: dict[str, Any] = {}
    report["R1"] = {
        "swaps_attempted": int(result.attempted),
        "gate": "reported only",
    }
    report["R2"] = {
        "swaps_accepted": int(result.accepted),
        "target_accepted": int(result.target_accepted),
        "complete": bool(result.complete),
        "gate": "reported only",
    }
    report["R3"] = {
        "swaps_rejected": {
            name: int(result.rejected.get(name, 0)) for name in REJECTION_REASONS
        },
        "acceptance_rate": round(float(result.acceptance_rate), 9),
        "progress": bool(result.accepted > 0),
        "gate": "reported only; the acceptance rate must exceed 0 to make progress",
        "pass": bool(result.accepted > 0),
    }
    report["R4"] = {
        "fraction_rewired": round(float(fraction_rewired), 9),
        "gate": 0.99,
        "pass": bool(fraction_rewired >= 0.99),
    }
    report["R5"] = {
        "jaccard": round(float(jaccard), 9),
        "intersection": int(intersection),
        "gate": 0.01,
        "pass": bool(jaccard <= 0.01),
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
        if order.size != m:
            raise ValueError("edge_order does not cover every edge")
        exc_equal = np.array_equal(
            np.asarray(policy_new.edge_exc_weight),
            np.asarray(policy_original.edge_exc_weight)[order],
        )
        inh_equal = np.array_equal(
            np.asarray(policy_new.edge_inh_weight),
            np.asarray(policy_original.edge_inh_weight)[order],
        )
        codes_equal = np.array_equal(
            np.asarray(policy_new.neuron_codes),
            np.asarray(policy_original.neuron_codes),
        )
        signs_equal = np.array_equal(
            np.asarray(policy_new.neuron_signs),
            np.asarray(policy_original.neuron_signs),
        )
        before = _signed_edge_summary(original, policy_original)
        after = _signed_edge_summary(new, policy_new)
        report["R8"] = {
            "evaluated": True,
            "parameterisation": "target_exchange (U18 option a, PROPOSED)",
            "per_edge_sign_reordering_equal": bool(exc_equal and inh_equal),
            "per_node_codes_equal": bool(codes_equal),
            "per_node_signs_equal": bool(signs_equal),
            "signed_edges_original": int(before["signed_edges"]),
            "signed_edges_new": int(after["signed_edges"]),
            "signed_synapses_original": int(before["signed_synapses"]),
            "signed_synapses_new": int(after["signed_synapses"]),
            "unsigned_edges_original": int(before["unsigned_edges"]),
            "unsigned_edges_new": int(after["unsigned_edges"]),
            "pass": bool(
                exc_equal
                and inh_equal
                and codes_equal
                and signs_equal
                and before == after
            ),
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
        "out_degree_profile_equal": bool(np.array_equal(out_original, out_new)),
        "pass": per_source_equal,
    }

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
    csr_ok = csr_ok and bool(np.all(np.asarray(new.edge_weight) >= int(new.threshold)))
    csr_ok = csr_ok and bool(not np.any(new.edge_src == new.edge_dst))
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
            "final_jaccard": round(float(tail[-1]), 12),
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

    if master_seed is not None and campaign_seed is not None:
        derived = _derive_structure_seed(master_seed, campaign_seed)
        report["R18"] = {
            "master_seed": int(master_seed),
            "campaign_seed": int(campaign_seed),
            "structure_stream_code": _STRUCTURE_STREAM_CODE,
            "entropy": [int(master_seed), int(campaign_seed), _STRUCTURE_STREAM_CODE],
            "derived_structure_seed": int(derived),
            "seed_used": int(result.seed),
            "derivation_verified": bool(derived == int(result.seed)),
            "recorded": True,
            "note": "the seed is the structure-stream value; R18 is not gated",
        }
    else:
        report["R18"] = {
            "seed": int(result.seed),
            "stream": "structure",
            "derivation_verified": False,
            "recorded": True,
            "note": (
                "the seed is recorded; supply master_seed and campaign_seed to "
                "verify SeedSequence([master, seed, 4]); R18 is not gated"
            ),
        }

    failures = [
        name
        for name in ("R4", "R5", "R6", "R7", "R8", "R9", "R9b", "R10",
                     "R11", "R12", "R13", "R14", "R17")
        if not report[name]["pass"]
    ]
    if not intersection_matches:
        failures.append("intersection_integrity")
    return {
        "construction": "target_exchange",
        "graph_digest": digest,
        "gates": report,
        "failures": failures,
        "passed": not failures,
        "integrity": {
            "intersection_recomputed": int(intersection),
            "intersection_reported": int(result.intersection),
            "match": bool(intersection_matches),
        },
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
        "algorithm": {
            "candidate_block": CANDIDATE_BLOCK,
            "default_batch_size": DEFAULT_BATCH_SIZE,
            "default_plateau_interval": DEFAULT_PLATEAU_INTERVAL,
            "candidate_stream": "SeedSequence([seed, block]) per candidate block",
        },
        "plateau_note": (
            "R14 is a diagnostic on the rewiring distance; a Jaccard plateau "
            "is not a proof of Markov-chain mixing"
        ),
    }
