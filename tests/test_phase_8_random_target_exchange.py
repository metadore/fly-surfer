"""Phase 8 G3: target-exchange randomization and the §3.3.1 R1-R18 report.

These tests use a synthetic graph. They do not load BANC, do not randomize the
172,433-node graph and do not substitute for the BANC-scale R1-R18 run, which
is blocked by the memory gate.

R14's gate is an absolute change of 1e-4 in the edge-set Jaccard on a graph
with 683,100 signed edges. On a 600-edge fixture one edge of fluctuation is
1.7e-3, so the tests verify that R14 is evaluated and reported and do not
require a 600-edge chain to meet a BANC-scale tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from experiments.phase_8_random import (
    RandomizationResult,
    graph_digest,
    rewire_target_exchange,
    validate_randomization,
)
from experiments.phase_8_random.target_exchange import (
    REJECTION_REASONS,
    describe_randomization,
)
from plasticity.synthetic import synthetic_graph, synthetic_policy

N_NODES = 600
N_EDGES = 600
SWAPS_PER_EDGE = 10.0
PLATEAU_INTERVAL = 20
SEED = 12345


def _per_source_weights(graph) -> tuple[np.ndarray, np.ndarray]:
    source = np.asarray(graph.edge_src, dtype=np.int64)
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    order = np.lexsort((weight, source))
    return source[order], weight[order]


@pytest.fixture(scope="module")
def world():
    original = synthetic_graph(N_NODES, N_EDGES, seed=11)
    original_policy = synthetic_policy(original)
    result = rewire_target_exchange(
        original,
        seed=SEED,
        swaps_per_edge=SWAPS_PER_EDGE,
        plateau_interval=PLATEAU_INTERVAL,
    )
    twin = rewire_target_exchange(
        original,
        seed=SEED,
        swaps_per_edge=SWAPS_PER_EDGE,
        plateau_interval=PLATEAU_INTERVAL,
    )
    other = rewire_target_exchange(
        original,
        seed=SEED + 1,
        swaps_per_edge=SWAPS_PER_EDGE,
        plateau_interval=PLATEAU_INTERVAL,
    )
    new_policy = synthetic_policy(result.graph)
    report = validate_randomization(
        original,
        result,
        policy_original=original_policy,
        policy_new=new_policy,
        reference_digest=graph_digest(twin.graph),
    )
    return {
        "original": original,
        "original_policy": original_policy,
        "result": result,
        "twin": twin,
        "other": other,
        "new_policy": new_policy,
        "report": report,
    }


# ---------------------------------------------------------------------------
# construction contract
# ---------------------------------------------------------------------------


def test_target_exchange_completes_and_accounts_for_every_attempt(world):
    result: RandomizationResult = world["result"]
    assert isinstance(result, RandomizationResult)
    assert result.complete
    assert result.accepted == result.target_accepted == int(
        round(SWAPS_PER_EDGE * N_EDGES)
    )
    assert result.attempted >= result.accepted
    assert set(result.rejected) == set(REJECTION_REASONS)
    assert sum(result.rejected.values()) + result.accepted == result.attempted
    assert result.acceptance_rate == pytest.approx(
        result.accepted / result.attempted
    )
    assert 0.0 < result.acceptance_rate <= 1.0


def test_randomization_preserves_degrees_weights_and_sources(world):
    original = world["original"]
    result = world["result"]
    new = result.graph

    assert new.n_nodes == original.n_nodes
    assert new.n_edges == original.n_edges
    assert np.array_equal(new.root_ids, original.root_ids)
    assert new.threshold == original.threshold

    assert np.array_equal(np.diff(new.out_indptr), np.diff(original.out_indptr))
    assert np.array_equal(np.diff(new.in_indptr), np.diff(original.in_indptr))
    assert np.array_equal(
        np.sort(np.asarray(new.edge_weight, dtype=np.int64)),
        np.sort(np.asarray(original.edge_weight, dtype=np.int64)),
    )
    src_old, weight_old = _per_source_weights(original)
    src_new, weight_new = _per_source_weights(new)
    assert np.array_equal(src_old, src_new)
    assert np.array_equal(weight_old, weight_new)
    assert np.array_equal(np.sort(new.edge_src), np.sort(original.edge_src))

    # target exchange keeps the source; only destinations move
    changed = np.flatnonzero(
        np.asarray(new.edge_dst) != np.asarray(original.edge_dst)
    )
    assert changed.size > 0


def test_randomized_graph_satisfies_connectome_invariants(world):
    new = world["result"].graph
    n = new.n_nodes
    m = new.n_edges

    assert np.array_equal(
        new.out_indptr,
        np.concatenate(([0], np.cumsum(np.bincount(new.edge_src, minlength=n)))),
    )
    assert np.array_equal(
        new.in_indptr,
        np.concatenate(([0], np.cumsum(np.bincount(new.edge_dst, minlength=n)))),
    )
    assert int(new.out_indptr[-1]) == m == int(new.in_indptr[-1])
    destinations = np.asarray(new.edge_dst)[new.in_edge_idx]
    assert np.all(destinations[:-1] <= destinations[1:])
    assert not np.any(new.edge_src == new.edge_dst)
    assert np.all(new.edge_weight >= new.threshold)
    # edges are stored in deterministic (src, dst) order
    order = np.lexsort((new.edge_dst, new.edge_src))
    assert np.array_equal(order, np.arange(m))


# ---------------------------------------------------------------------------
# R-gates
# ---------------------------------------------------------------------------


def test_structural_gates_pass(world):
    report = world["report"]["gates"]
    for name in ("R6", "R7", "R8", "R9", "R9b", "R10", "R11", "R12"):
        assert report[name]["pass"] is True, (name, report[name])

    assert report["R6"]["out_degree_sum"] == N_EDGES
    assert report["R7"]["in_degree_sum"] == N_EDGES
    assert report["R8"]["signed_edges_original"] == report["R8"]["signed_edges_new"]
    assert report["R10"]["duplicate_pairs"] == 0
    assert report["R11"]["self_edges"] == 0
    assert report["R9"]["synapse_sum"] == int(
        np.asarray(world["original"].edge_weight, dtype=np.int64).sum()
    )


def test_rewiring_distance_gates_catch_real_movement(world):
    report = world["report"]["gates"]
    assert report["R4"]["fraction_rewired"] >= 0.99
    assert report["R4"]["pass"] is True
    assert report["R5"]["jaccard"] <= 0.01
    assert report["R5"]["pass"] is True
    assert world["result"].fraction_rewired == pytest.approx(
        report["R4"]["fraction_rewired"], abs=1e-9
    )


def test_r13_gate_uses_nodes_with_a_neighbourhood(world):
    report = world["report"]["gates"]
    r13 = report["R13"]
    assert r13["pass"] is True
    assert r13["statistic"] == "mean_over_active_nodes"
    assert r13["mean_out_neighbour_jaccard"] <= 0.01
    assert r13["active_nodes"] + r13["isolated_in_both"] == N_NODES
    expected_all_node_mean = (
        r13["mean_out_neighbour_jaccard"] * r13["active_nodes"]
        + r13["isolated_in_both"]
    ) / N_NODES
    assert r13["mean_out_neighbour_jaccard_all_nodes"] == pytest.approx(
        expected_all_node_mean, abs=1e-9
    )
    assert r13["mean_out_neighbour_jaccard_all_nodes"] > r13[
        "mean_out_neighbour_jaccard"
    ]


def test_r14_is_reported_as_a_plateau_diagnostic(world):
    report = world["report"]
    r14 = report["gates"]["R14"]
    assert r14["evaluated"] is True
    assert r14["tail_samples"] >= 2
    assert r14["gate"] == 1.0e-4
    assert "plateau diagnostic" in r14["note"]
    # Only R14 may fail at this graph size; every other gated check passes.
    assert set(report["failures"]) <= {"R14"}


def test_r15_and_r16_are_reported_but_not_gated(world):
    report = world["report"]["gates"]
    assert report["R15"]["gated"] is False
    assert "n_components" in report["R15"]["before"]
    assert "n_components" in report["R15"]["after"]
    assert report["R16"]["gated"] is False
    assert 0.0 <= report["R16"]["reciprocity_before"] <= 1.0
    assert 0.0 <= report["R16"]["reciprocity_after"] <= 1.0


def test_same_seed_is_byte_identical_and_different_seed_differs(world):
    result = world["result"]
    twin = world["twin"]
    other = world["other"]

    for name in ("edge_src", "edge_dst", "edge_weight", "out_indptr", "in_indptr"):
        assert np.array_equal(
            getattr(result.graph, name), getattr(twin.graph, name)
        ), name
    assert graph_digest(result.graph) == graph_digest(twin.graph)
    assert world["report"]["gates"]["R17"]["pass"] is True
    assert world["report"]["passed"] is True or set(
        world["report"]["failures"]
    ) <= {"R14"}

    assert graph_digest(other.graph) != graph_digest(result.graph)
    assert np.array_equal(np.diff(other.graph.in_indptr), np.diff(world["original"].in_indptr))


# ---------------------------------------------------------------------------
# edge cases and reporting
# ---------------------------------------------------------------------------


def test_zero_budget_is_the_identity_map(world):
    original = world["original"]
    result = rewire_target_exchange(original, seed=1, swaps_per_edge=0.0)
    assert result.target_accepted == 0
    assert result.accepted == 0
    assert result.attempted == 0
    assert result.complete
    assert result.fraction_rewired == 0.0
    assert graph_digest(result.graph) == graph_digest(original)


def test_attempt_cap_reports_incomplete_without_pretending(world):
    original = world["original"]
    result = rewire_target_exchange(
        original, seed=2, swaps_per_edge=10.0, max_attempts=0
    )
    assert result.attempted == 0
    assert result.accepted == 0
    assert result.complete is False
    assert result.fraction_rewired == 0.0
    report = validate_randomization(
        original,
        result,
        policy_original=world["original_policy"],
        policy_new=world["original_policy"],
        include_components=False,
    )
    assert report["passed"] is False
    assert "R4" in report["failures"]
    assert "R5" in report["failures"]
    assert report["gates"]["R6"]["pass"] is True
    assert report["gates"]["R15"]["evaluated"] is False


def test_r8_requires_both_policies(world):
    report = validate_randomization(
        world["original"],
        world["result"],
        include_components=False,
    )
    assert report["gates"]["R8"]["evaluated"] is False
    assert report["gates"]["R8"]["pass"] is False
    assert "R8" in report["failures"]
    assert "policies were not supplied" in report["gates"]["R8"]["reason"]


def test_summary_records_construction_and_digest(world):
    summary = world["result"].summary()
    assert summary["construction"] == "target_exchange"
    assert summary["seed"] == SEED
    assert summary["complete"] is True
    assert summary["graph_digest"] == graph_digest(world["result"].graph)
    assert set(summary["rejected"]) == set(REJECTION_REASONS)
    assert 0.0 <= summary["jaccard_vs_original"] <= 1.0
    assert world["report"]["summary"] == summary


def test_invalid_parameters_are_rejected(world):
    graph = world["original"]
    with pytest.raises(ValueError):
        rewire_target_exchange(graph, seed=True)
    with pytest.raises(ValueError):
        rewire_target_exchange(graph, seed=1, swaps_per_edge=-1.0)
    with pytest.raises(ValueError):
        rewire_target_exchange(graph, seed=1, swaps_per_edge=float("nan"))
    with pytest.raises(ValueError):
        rewire_target_exchange(graph, seed=1, plateau_interval=0)


def test_describe_documents_the_contract():
    description = describe_randomization()
    assert description["construction"] == "target_exchange"
    assert "fixed" in description["edge_identity"]
    assert "per-node out-degree" in description["preserved"]
    assert "per-node in-degree" in description["preserved"]
    assert "which source talks to which target" in description["not_preserved"]
    assert description["gates"] == [f"R{index}" for index in range(1, 19)]
    assert "not a proof" in description["plateau_note"]
