"""Focused tests for the Phase 4G.2 transmitter-sign and weight policy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from brain.banc_graph import BancConnectome
from brain.banc_synapse_policy import (
    PREDICTED_EXCITATORY,
    PREDICTED_INHIBITORY,
    PREDICTED_MODULATOR_ONLY,
    UNANNOTATED,
    VERIFIED_CONFLICT,
    VERIFIED_EXCITATORY,
    VERIFIED_INHIBITORY,
    VERIFIED_MODULATOR_ONLY,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
    classify_labels,
    sign_values,
)


def make_graph(n_nodes: int, edges: list[tuple[int, int, int]], threshold: int = 5) -> BancConnectome:
    order = sorted((int(s), int(d), int(w)) for s, d, w in edges)
    edge_src = np.array([edge[0] for edge in order], dtype=np.int32)
    edge_dst = np.array([edge[1] for edge in order], dtype=np.int32)
    edge_weight = np.array([edge[2] for edge in order], dtype=np.int32)
    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)
    return BancConnectome(
        root_ids=np.arange(1000, 1000 + n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=threshold,
    )


def make_nodes(labels: list[str | None], predicted: list[str | None] | None = None) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "banc_888_id": [str(1000 + index) for index in range(len(labels))],
            "node_index": np.arange(len(labels)),
            "neurotransmitter_verified": labels,
            "neurotransmitter_predicted": predicted or [None] * len(labels),
        }
    )


def test_verified_labels_are_classified_by_transmitter_set():
    nodes = make_nodes(
        [
            "acetylcholine",
            "glutamate",
            "gaba",
            "gaba,nitric_oxide",
            "acetylcholine,nitric_oxide,dopamine",
            "dopamine",
            "acetylcholine,gaba",
            None,
        ]
    )
    codes = classify_labels(
        nodes["neurotransmitter_verified"],
        nodes["neurotransmitter_predicted"],
        SignPolicy(),
    )
    assert list(codes) == [
        VERIFIED_EXCITATORY,
        VERIFIED_EXCITATORY,
        VERIFIED_INHIBITORY,
        VERIFIED_INHIBITORY,
        VERIFIED_EXCITATORY,
        VERIFIED_MODULATOR_ONLY,
        VERIFIED_CONFLICT,
        UNANNOTATED,
    ]


def test_missing_and_unknown_values_are_unannotated():
    nodes = make_nodes([None, np.nan, "unknown", "<NA>", "", " "])
    codes = classify_labels(
        nodes["neurotransmitter_verified"],
        nodes["neurotransmitter_predicted"],
        SignPolicy(),
    )
    assert list(codes) == [UNANNOTATED] * 6


def test_predicted_labels_never_carry_a_sign_in_the_primary_policy():
    nodes = make_nodes([None, None], ["gaba", "acetylcholine"])
    codes = classify_labels(
        nodes["neurotransmitter_verified"],
        nodes["neurotransmitter_predicted"],
        SignPolicy(),
    )
    assert list(codes) == [UNANNOTATED, UNANNOTATED]
    assert list(sign_values(codes, SignPolicy())) == [0, 0]


def test_predicted_fallback_classifies_without_touching_verified_labels():
    policy = SignPolicy(predicted_fallback=True)
    nodes = make_nodes(
        [None, None, None, None, "gaba"],
        ["acetylcholine", "gaba", "dopamine", None, "acetylcholine"],
    )
    codes = classify_labels(
        nodes["neurotransmitter_verified"],
        nodes["neurotransmitter_predicted"],
        policy,
    )
    assert list(codes) == [
        PREDICTED_EXCITATORY,
        PREDICTED_INHIBITORY,
        PREDICTED_MODULATOR_ONLY,
        UNANNOTATED,
        VERIFIED_INHIBITORY,
    ]
    assert list(sign_values(codes, policy)) == [1, -1, 0, 0, -1]


def test_sign_policy_rejects_conflicting_or_invalid_configuration():
    with pytest.raises(ValueError):
        SignPolicy(verified_excitatory=("gaba",))
    with pytest.raises(ValueError):
        SignPolicy(conflict_policy="excitatory")
    with pytest.raises(ValueError):
        SignPolicy(modulator_only_policy="inhibitory")
    with pytest.raises(ValueError):
        SignPolicy(unknown_edge_policy="sqrt")
    with pytest.raises(ValueError):
        SignPolicy(predicted_fallback="yes")


def test_sign_policy_from_config_ignores_documentation_keys():
    policy = SignPolicy.from_config(
        {
            "primary_source": "neurotransmitter_verified",
            "verified_excitatory": ["acetylcholine"],
            "verified_inhibitory": ["gaba"],
            "unknown_edge_policy": "exclude",
        }
    )
    assert policy.verified_excitatory == ("acetylcholine",)
    assert policy.verified_inhibitory == ("gaba",)


def test_weight_policy_transforms_and_cap():
    counts = np.array([1, 4, 16, 1000], dtype=np.int32)
    linear = WeightPolicy(transform="linear", scale_pa=2.0, cap_pa=None)
    assert np.allclose(linear.apply(counts), [2.0, 8.0, 32.0, 2000.0])
    powered = WeightPolicy(transform="power", exponent=0.5, scale_pa=3.0, cap_pa=None)
    assert np.allclose(powered.apply(counts), 3.0 * np.sqrt(counts))
    logged = WeightPolicy(transform="log1p", scale_pa=1.0, cap_pa=None)
    assert np.allclose(logged.apply(counts), np.log1p(counts))
    capped = WeightPolicy(transform="linear", scale_pa=2.0, cap_pa=10.0)
    assert np.allclose(capped.apply(counts), [2.0, 8.0, 10.0, 10.0])


def test_weight_policy_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        WeightPolicy(transform="sqrt")
    with pytest.raises(ValueError):
        WeightPolicy(exponent=0.0)
    with pytest.raises(ValueError):
        WeightPolicy(exponent=float("inf"))
    with pytest.raises(ValueError):
        WeightPolicy(scale_pa=-1.0)
    with pytest.raises(ValueError):
        WeightPolicy(cap_pa=0.0)


def test_edge_weights_follow_the_presynaptic_sign_only():
    graph = make_graph(
        4,
        [
            (0, 3, 10),  # acetylcholine source
            (1, 3, 20),  # gaba source
            (2, 3, 30),  # unannotated source
        ],
    )
    nodes = make_nodes(["acetylcholine", "gaba", None, "glutamate"])
    policy = build_synapse_policy(graph, nodes, SignPolicy(), WeightPolicy())
    exc = policy.edge_exc_weight
    inh = policy.edge_inh_weight
    assert exc[graph.edge_src == 0].sum() > 0
    assert inh[graph.edge_src == 1].sum() > 0
    assert exc[graph.edge_src == 2].sum() == 0
    assert inh[graph.edge_src == 2].sum() == 0
    assert policy.coverage["excluded_edges"] == 1
    assert policy.coverage["signed_edges"] == 2


def test_policy_is_independent_of_the_postsynaptic_label():
    graph = make_graph(2, [(0, 1, 12)])
    first = build_synapse_policy(
        graph,
        make_nodes(["acetylcholine", "gaba"]),
        SignPolicy(),
        WeightPolicy(),
    )
    second = build_synapse_policy(
        graph,
        make_nodes(["acetylcholine", "acetylcholine"]),
        SignPolicy(),
        WeightPolicy(),
    )
    assert np.array_equal(first.edge_exc_weight, second.edge_exc_weight)


def test_build_policy_validates_node_order_and_annotations():
    graph = make_graph(2, [(0, 1, 10)])
    shuffled = make_nodes(["acetylcholine", "gaba"]).iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError):
        build_synapse_policy(graph, shuffled, SignPolicy(), WeightPolicy())
    with pytest.raises(ValueError):
        build_synapse_policy(graph, make_nodes(["gaba"]), SignPolicy(), WeightPolicy())
    missing = make_nodes(["acetylcholine", "gaba"]).drop(
        columns=["neurotransmitter_predicted"]
    )
    with pytest.raises(ValueError):
        build_synapse_policy(graph, missing, SignPolicy(), WeightPolicy())


def test_coverage_partition_has_no_double_counting():
    graph = make_graph(
        6,
        [
            (0, 3, 10),
            (0, 4, 12),
            (1, 4, 20),
            (2, 5, 7),
            (3, 5, 30),
            (4, 0, 9),
        ],
    )
    nodes = make_nodes(
        ["acetylcholine", "gaba", "dopamine", "acetylcholine,gaba", None, "glutamate"]
    )
    policy = build_synapse_policy(graph, nodes, SignPolicy(), WeightPolicy())
    coverage = policy.coverage
    by_class = coverage["by_class"]
    assert sum(entry["edges"] for entry in by_class.values()) == graph.n_edges
    assert (
        sum(entry["synapses"] for entry in by_class.values())
        == graph.n_synapses
    )
    assert (
        coverage["signed_edges"] + coverage["excluded_edges"] == graph.n_edges
    )
    assert (
        coverage["signed_synapses"] + coverage["excluded_synapses"]
        == graph.n_synapses
    )


def test_weight_cap_bounds_large_structural_counts():
    graph = make_graph(2, [(0, 1, 10_000_000)], threshold=1)
    nodes = make_nodes(["acetylcholine", "gaba"])
    policy = build_synapse_policy(
        graph,
        nodes,
        SignPolicy(),
        WeightPolicy(transform="power", exponent=0.75, scale_pa=5.0, cap_pa=300.0),
    )
    assert float(policy.edge_exc_weight.max()) == pytest.approx(300.0)
    assert np.all(np.isfinite(policy.edge_exc_weight))


def test_policy_records_the_graph_threshold():
    graph = make_graph(3, [(0, 1, 10), (1, 2, 10)], threshold=10)
    nodes = make_nodes(["acetylcholine", "gaba", "glutamate"])
    policy = build_synapse_policy(graph, nodes, SignPolicy(), WeightPolicy())
    assert policy.threshold == 10
    assert policy.describe()["graph_threshold"] == 10
