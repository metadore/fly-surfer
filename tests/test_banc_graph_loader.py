"""Focused tests for the Phase 4D BANC graph pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from brain.banc_graph import (
    FAFB_ARTIFACTS,
    OUT_DIR,
    TERGOTROCHANTER_TARGET,
    BancConnectome,
    _artifact_paths,
    compare_snapshots,
    construct_graphs,
    motor_by_body_part,
    parse_positions,
    population_mask,
    sha256_file,
    snapshot_paths,
    validate_canonical_ids,
    verify_manifest,
)

D1, D2 = 1001, 1002
M1, M2, M3 = 2001, 2002, 2003
V1, S1, X1, META_ONLY = 3001, 4001, 5001, 6001


def make_meta() -> pd.DataFrame:
    rows = {
        "banc_888_id": [str(value) for value in (D1, D2, M1, M2, M3, V1, S1, X1, META_ONLY)],
        "super_class": ["descending", "descending", "motor", "motor", "motor", "ventral_nerve_cord_intrinsic", "sensory", None, "motor"],
        "cell_class": ["descending", "descending", "motor", "motor", "motor", "intrinsic", "sensory", None, "motor"],
        "cell_sub_class": [None] * 9,
        "cell_type": ["d1", "d2", "m1", "m2", "m3", "v1", "s1", None, "m4"],
        "side": ["left", "right", "left", "right", "left", "left", "left", None, "left"],
        "region": ["central_brain", "central_brain", "ventral_nerve_cord", "ventral_nerve_cord", "ventral_nerve_cord", "ventral_nerve_cord", "ventral_nerve_cord", None, "ventral_nerve_cord"],
        "root_region": ["CB", "CB", "VNC", "VNC", "VNC", "VNC", "VNC", None, "VNC"],
        "nerve": [None] * 9,
        "tract": [None] * 9,
        "neuromere": [None] * 9,
        "flow": ["efferent", "efferent", "efferent", "efferent", "efferent", "intrinsic", "afferent", None, "efferent"],
        "body_part_effector": [None, None, "front_leg", "front_leg", "front_leg", None, None, None, "front_leg"],
        "body_part_sensory": [None] * 9,
        "peripheral_target_type": [None, None, "femur_reductor_muscle", "femur_reductor_muscle", TERGOTROCHANTER_TARGET, None, None, None, "femur_reductor_muscle"],
        "cell_function": [None, None, "leg_motor", "leg_motor", "leg_motor", None, None, None, "leg_motor"],
        "neurotransmitter_predicted": ["acetylcholine", "acetylcholine", "gaba", "gaba", "gaba", "gaba", "acetylcholine", None, "gaba"],
        "neurotransmitter_verified": ["acetylcholine", None, None, None, None, None, None, None, None],
        "neurotransmitter_score": [0.9, 0.8, 0.7, 0.7, 0.7, 0.6, 0.8, None, 0.7],
        "proofread": ["TRUE"] * 9,
        "roughly_proofread": ["FALSE"] * 9,
        "status": ["done"] * 9,
        "root_position_nm": ["1, 2, 3", "4, 5, 6", "7, 8, 9", "10, 11, 12", "13, 14, 15", "16, 17, 18", "19, 20, 21", None, "22, 23, 24"],
    }
    return pd.DataFrame(rows)


def make_edges() -> dict:
    pre = np.array([D1, D1, D2, D1, V1, S1, M1, X1], dtype=np.int64)
    post = np.array([M1, M2, M2, D1, M1, V1, X1, M3], dtype=np.int64)
    count = np.array([5, 2, 7, 4, 10, 3, 1, 1], dtype=np.int64)
    return {
        "pre": pre,
        "post": post,
        "count": count,
        "norm": np.ones(len(pre), dtype=np.float64),
        "pre_count": np.ones(len(pre), dtype=np.int64),
        "post_count": np.ones(len(pre), dtype=np.int64),
        "nulls": {},
        "rows": len(pre),
        "columns": ["pre", "post", "count", "norm", "post_count", "pre_count"],
    }


@pytest.fixture
def built():
    meta = make_meta()
    edges = make_edges()
    graphs, nodes, result = construct_graphs(meta, edges, (1, 5, 10))
    return meta, edges, graphs, nodes, result


def test_canonical_id_uniqueness() -> None:
    meta = make_meta()
    report = validate_canonical_ids(meta)
    assert report["verdict"] == "PASS"
    assert report["unique"] == len(meta)
    assert report["duplicates"] == 0
    with pytest.raises(ValueError, match="duplicate"):
        validate_canonical_ids(pd.concat([meta, meta.iloc[[0]]], ignore_index=True))
    broken = meta.copy()
    broken.loc[0, "banc_888_id"] = None
    with pytest.raises(ValueError, match="null"):
        validate_canonical_ids(broken)


def test_canonical_id_index_round_trip(built) -> None:
    _, _, graphs, nodes, _ = built
    graph = graphs[5]
    for value in (D1, M1, V1, X1):
        index = graph.node_index(value)
        assert int(graph.root_ids[index]) == value
        assert str(graph.banc_ids[index]) == str(value)
        assert str(nodes.loc[nodes["node_index"] == index, "banc_888_id"].iloc[0]) == str(value)
    with pytest.raises(KeyError):
        graph.node_index(9999)


def test_missing_endpoint_detection() -> None:
    meta = make_meta()
    edges = make_edges()
    edges["post"] = edges["post"].copy()
    edges["post"][0] = 9999
    with pytest.raises(ValueError, match="absent from metadata"):
        construct_graphs(meta, edges, (5,))


def test_duplicate_edge_detection() -> None:
    meta = make_meta()
    edges = make_edges()
    edges["pre"] = np.append(edges["pre"], D1).astype(np.int64)
    edges["post"] = np.append(edges["post"], M1).astype(np.int64)
    edges["count"] = np.append(edges["count"], 3).astype(np.int64)
    with pytest.raises(ValueError, match="duplicate"):
        construct_graphs(meta, edges, (5,))


def test_self_edge_exclusion(built) -> None:
    _, _, graphs, _, result = built
    prepared = result["summary"]["edge_preparation"]
    assert prepared["self_edge_rows"] == 1
    assert prepared["self_edge_synapses"] == 4
    assert prepared["n_original"] == 8
    assert prepared["n_non_self"] == 7
    for graph in graphs.values():
        assert not np.any(graph.edge_src == graph.edge_dst)


def test_edge_thresholds(built) -> None:
    _, _, graphs, _, result = built
    assert graphs[1].n_edges == 7
    assert graphs[5].n_edges == 3
    assert graphs[10].n_edges == 1
    assert graphs[1].n_synapses == 29
    assert graphs[5].n_synapses == 22
    assert graphs[10].n_synapses == 10
    assert result["stats"]["threshold_5"]["weight_min"] == 5
    assert result["stats"]["threshold_10"]["weight_min"] == 10


def test_structural_weights_match_counts(built) -> None:
    meta, edges, graphs, _, _ = built
    graph = graphs[1]
    expected = {
        (graph.node_index(pre), graph.node_index(post)): int(count)
        for pre, post, count in zip(edges["pre"], edges["post"], edges["count"])
        if pre != post
    }
    actual = {
        (int(src), int(dst)): int(weight)
        for src, dst, weight in zip(graph.edge_src, graph.edge_dst, graph.edge_weight)
    }
    assert actual == expected


def test_csr_directionality(built) -> None:
    _, _, graphs, _, _ = built
    graph = graphs[5]
    targets, weights = graph.out_edges(graph.node_index(D1))
    assert [int(graph.root_ids[value]) for value in targets] == [M1]
    assert [int(value) for value in weights] == [5]
    sources, in_weights = graph.in_edges(graph.node_index(M1))
    assert sorted(int(graph.root_ids[value]) for value in sources) == [D1, V1]
    assert sorted(int(value) for value in in_weights) == [5, 10]


def test_in_and_out_degrees(built) -> None:
    _, _, graphs, _, _ = built
    graph = graphs[1]
    out_degree = np.bincount(graph.edge_src, minlength=graph.n_nodes)
    in_degree = np.bincount(graph.edge_dst, minlength=graph.n_nodes)
    assert int(out_degree[graph.node_index(D1)]) == 2
    assert int(in_degree[graph.node_index(D1)]) == 0
    assert int(out_degree[graph.node_index(V1)]) == 1
    assert int(in_degree[graph.node_index(V1)]) == 1
    assert np.array_equal(out_degree, np.diff(graph.out_indptr))
    assert np.array_equal(in_degree, np.diff(graph.in_indptr))


def test_isolated_nodes_are_retained(built) -> None:
    _, _, graphs, _, result = built
    for graph in graphs.values():
        assert graph.n_nodes == 8
        assert graph.node_index(M3) >= 0
    assert graphs[5].n_isolated == 3
    assert graphs[10].n_isolated == 6
    assert result["stats"]["threshold_5"]["isolated_nodes"] == 3


def test_annotation_left_join_and_metadata_only_exclusion(built) -> None:
    meta, _, _, nodes, _ = built
    assert len(nodes) == 8
    assert META_ONLY not in set(nodes["banc_888_id"].astype(int))
    row = nodes.loc[nodes["banc_888_id"].astype(int) == M1].iloc[0]
    assert row["super_class"] == "motor"
    assert row["body_part_effector"] == "front_leg"
    assert row["cell_type"] == "m1"
    assert pd.isna(row["neurotransmitter_verified"])
    descending = nodes.loc[nodes["banc_888_id"].astype(int) == D1].iloc[0]
    assert descending["neurotransmitter_verified"] == "acetylcholine"
    assert list(nodes["node_index"]) == list(range(8))


def test_missing_annotations_stay_unknown(built) -> None:
    _, _, _, nodes, _ = built
    row = nodes.loc[nodes["banc_888_id"].astype(int) == X1].iloc[0]
    assert pd.isna(row["super_class"])
    assert pd.isna(row["cell_type"])
    assert pd.isna(row["side"])
    assert pd.isna(row["body_part_effector"])
    assert not bool(row["is_motor"])
    assert bool(row["is_tergotrochanter_candidate"]) is False


def test_positions_parse_and_missing_stays_masked() -> None:
    meta = make_meta()
    graphs, _, _ = construct_graphs(meta, make_edges(), (5,))
    graph = graphs[5]
    positions, mask = parse_positions(meta, graph.root_ids)
    assert positions.shape == (graph.n_nodes, 3)
    assert int(mask.sum()) == 7
    assert not bool(mask[graph.node_index(X1)])
    assert positions[graph.node_index(D1)].tolist() == [1.0, 2.0, 3.0]
    assert np.array_equal(graph.positions, positions)
    assert np.array_equal(graph.position_mask, mask)


def test_motor_and_descending_populations(built) -> None:
    _, _, _, nodes, _ = built
    assert int(population_mask(nodes, "descending").sum()) == 2
    assert int(population_mask(nodes, "motor").sum()) == 3
    assert int(population_mask(nodes, "left_motor").sum()) == 2
    assert int(population_mask(nodes, "right_motor").sum()) == 1
    assert int(population_mask(nodes, "vnc").sum()) == 5
    assert int(population_mask(nodes, "vnc_intrinsic").sum()) == 1
    assert int(population_mask(nodes, "tergotrochanter_motor_candidates").sum()) == 1
    parts = motor_by_body_part(nodes)
    assert parts.loc[parts["body_part_effector"] == "front_leg", "motor_neurons"].iloc[0] == 3
    assert parts.loc[parts["body_part_effector"] == "front_leg", "left"].iloc[0] == 2
    assert parts.loc[parts["body_part_effector"] == "front_leg", "right"].iloc[0] == 1


def test_deterministic_construction() -> None:
    meta = make_meta()
    edges = make_edges()
    first, _, _ = construct_graphs(meta, edges, (1, 5, 10))
    second, _, _ = construct_graphs(meta, edges, (1, 5, 10))
    for threshold in (1, 5, 10):
        left, right = first[threshold], second[threshold]
        assert np.array_equal(left.root_ids, right.root_ids)
        assert np.array_equal(left.out_indptr, right.out_indptr)
        assert np.array_equal(left.in_indptr, right.in_indptr)
        assert np.array_equal(left.edge_src, right.edge_src)
        assert np.array_equal(left.edge_dst, right.edge_dst)
        assert np.array_equal(left.edge_weight, right.edge_weight)
        assert np.array_equal(left.in_edge_idx, right.in_edge_idx)


def test_graph_artifact_round_trip(built, tmp_path: Path) -> None:
    _, _, graphs, nodes, result = built
    graph = graphs[5]
    path = tmp_path / "banc_graph_t5.npz"
    graph.save(path)
    loaded = BancConnectome.load(path)
    assert loaded.threshold == 5
    assert loaded.n_nodes == graph.n_nodes
    assert loaded.n_edges == graph.n_edges
    assert loaded.n_synapses == graph.n_synapses
    assert np.array_equal(loaded.edge_weight, graph.edge_weight)
    assert np.array_equal(loaded.banc_ids, graph.banc_ids)
    assert loaded.node_index(D1) == graph.node_index(D1)
    assert loaded.meta["artifact"] == "banc_v888_graph"


def test_manifest_checksum_validation(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.bin"
    first.write_text("alpha", encoding="utf-8")
    second.write_bytes(b"beta")
    manifest = {
        "inputs": {
            "first": {
                "path": "first.txt",
                "sha256": sha256_file(first),
            }
        },
        "outputs": {
            "second": {
                "path": "second.bin",
                "sha256": sha256_file(second),
            }
        },
    }
    assert verify_manifest(manifest, root=tmp_path)["pass"] is True
    second.write_bytes(b"tampered")
    result = verify_manifest(manifest, root=tmp_path)
    assert result["pass"] is False
    assert result["failures"] == ["outputs:second"]


def test_fafb_artifact_isolation(tmp_path: Path) -> None:
    artifact = tmp_path / "connectome.npz"
    artifact.write_bytes(b"fafb")
    before = snapshot_paths([artifact])
    after = snapshot_paths([artifact])
    assert compare_snapshots(before, after)["unchanged"] is True
    artifact.write_bytes(b"changed")
    assert compare_snapshots(before, snapshot_paths([artifact]))["unchanged"] is False
    assert OUT_DIR not in {path.parent for path in FAFB_ARTIFACTS}
    paths = _artifact_paths(OUT_DIR)
    assert paths["graph_threshold_5"].parent == OUT_DIR
    assert paths["graph_threshold_5"].name == "banc_graph_t5.npz"


def test_banc_and_fafb_node_sets_are_disjoint() -> None:
    from brain.connectome_loader import load_connectome

    graph_path = _artifact_paths(OUT_DIR)["graph_threshold_5"]
    fafb_path = FAFB_ARTIFACTS[0]
    if not graph_path.exists() or not fafb_path.exists():
        pytest.skip("built BANC or FAFB artifact not available")
    banc = BancConnectome.load(graph_path)
    fafb = load_connectome(fafb_path)
    assert banc.n_nodes != fafb.n_nodes
    assert np.intersect1d(banc.root_ids, fafb.root_ids).size == 0


def test_built_artifacts_match_manifest() -> None:
    import json

    manifest_path = _artifact_paths(OUT_DIR)["manifest"]
    if not manifest_path.exists():
        pytest.skip("BANC manifest not built")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert verify_manifest(manifest)["pass"] is True
    assert manifest["audit_cross_check"]["pass"] is True
    assert manifest["fafb_isolation"]["unchanged"] is True
    graph = BancConnectome.load(_artifact_paths(OUT_DIR)["graph_threshold_5"])
    assert graph.n_nodes == manifest["node_count"]
    assert graph.n_edges == manifest["retained"]["threshold_5"]["n_edges"]
    assert graph.n_synapses == manifest["retained"]["threshold_5"]["n_synapses"]
