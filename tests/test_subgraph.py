"""Induced-subgraph extraction and reproducible connected sampling."""

from __future__ import annotations

import numpy as np
import pytest

from brain.subgraph import (
    GraphView,
    extract_induced_subgraph,
    sample_connected_neurons,
    total_degrees,
    weak_component_count,
)


def chain_graph(graph_factory, n_nodes: int = 40) -> GraphView:
    edges = []
    for node in range(n_nodes - 1):
        edges.append((node, node + 1, 1))
        edges.append((node + 1, node, 1))
    return graph_factory(n_nodes, edges)


def test_extract_keeps_only_internal_edges(graph_factory) -> None:
    full = graph_factory(
        5, [(0, 1, 3), (1, 2, 2), (2, 3, 5), (3, 0, 1), (4, 0, 7)]
    )
    sub = extract_induced_subgraph(full, np.array([0, 1, 2]))
    assert sub.n_nodes == 3
    assert sub.root_ids.tolist() == [1000, 1001, 1002]
    assert sub.node_map.tolist() == [0, 1, 2]
    assert sub.edge_src.tolist() == [0, 1]
    assert sub.edge_dst.tolist() == [1, 2]
    assert sub.edge_weight.tolist() == [3, 2]
    assert sub.out_indptr.tolist() == [0, 1, 2, 2]
    assert sub.in_indptr.tolist() == [0, 0, 1, 2]
    assert sub.out_edges(0)[0].tolist() == [1]
    assert sub.in_edges(2)[0].tolist() == [1]


def test_extract_disconnected_selection_has_no_edges(graph_factory) -> None:
    full = graph_factory(
        5, [(0, 1, 3), (1, 2, 2), (2, 3, 5), (3, 0, 1), (4, 0, 7)]
    )
    sub = extract_induced_subgraph(full, np.array([1, 4]))
    assert sub.n_edges == 0
    assert weak_component_count(sub) == (2, 1)


def test_extract_rejects_invalid_selection(graph_factory) -> None:
    full = graph_factory(3, [(0, 1, 1)])
    with pytest.raises(ValueError):
        extract_induced_subgraph(full, np.array([], dtype=np.int64))
    with pytest.raises(ValueError):
        extract_induced_subgraph(full, np.array([0, 3]))


def test_graph_view_rejects_inconsistent_root_ids(graph_factory) -> None:
    full = graph_factory(3, [(0, 1, 1)])
    with pytest.raises(ValueError):
        GraphView(
            root_ids=np.array([1001, 1000, 1002]),
            node_map=full.node_map,
            out_indptr=full.out_indptr,
            edge_src=full.edge_src,
            edge_dst=full.edge_dst,
            edge_weight=full.edge_weight,
            in_indptr=full.in_indptr,
            in_edge_idx=full.in_edge_idx,
            nt_code=full.nt_code,
            super_class_code=full.super_class_code,
            class_code=full.class_code,
            side_code=full.side_code,
            positions=full.positions,
            vocabulary=full.vocabulary,
        )


def test_total_degrees_counts_both_directions(graph_factory) -> None:
    full = graph_factory(
        5, [(0, 1, 3), (1, 2, 2), (2, 3, 5), (3, 0, 1), (4, 0, 7)]
    )
    assert total_degrees(full).tolist() == [3, 2, 2, 2, 1]


def test_sampling_is_reproducible_and_connected(graph_factory) -> None:
    full = chain_graph(graph_factory, 60)
    first = sample_connected_neurons(
        full, n_neurons=20, seed=7, min_degree=2, random_candidate_seeds=5
    )
    second = sample_connected_neurons(
        full, n_neurons=20, seed=7, min_degree=2, random_candidate_seeds=5
    )
    assert np.array_equal(first.node_indices, second.node_indices)
    assert first.node_indices.size == 20
    assert np.all(np.diff(first.node_indices) > 0)
    sub = extract_induced_subgraph(full, first.node_indices)
    assert weak_component_count(sub) == (1, 20)


def test_sampling_falls_back_when_min_degree_is_too_strict(graph_factory) -> None:
    full = chain_graph(graph_factory, 30)
    selection = sample_connected_neurons(
        full, n_neurons=10, seed=3, min_degree=99
    )
    assert selection.effective_min_degree == 0
    assert selection.node_indices.size == 10
    assert selection.eligible_count == 30


def test_sampling_validates_request(graph_factory) -> None:
    full = chain_graph(graph_factory, 10)
    with pytest.raises(ValueError):
        sample_connected_neurons(full, n_neurons=1, seed=0)
    with pytest.raises(ValueError):
        sample_connected_neurons(full, n_neurons=11, seed=0)


def test_node_lookup_round_trips(graph_factory) -> None:
    full = graph_factory(3, [(0, 1, 1)])
    assert full.node_index(1002) == 2
    with pytest.raises(KeyError):
        full.node_index(9999)
