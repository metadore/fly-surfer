"""Focused tests for the Phase 4E motor population and pathway analysis."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from brain.banc_graph import OUT_DIR, BancConnectome

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "phase_4e"
    / "analyze_motor_pathways.py"
)
REPORT_JSON = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.json"
)
ARTIFACTS = (
    OUT_DIR / "banc_nodes.csv.gz",
    OUT_DIR / "banc_graph_t1.npz",
    OUT_DIR / "banc_graph_t5.npz",
    OUT_DIR / "banc_graph_t10.npz",
    OUT_DIR / "banc_manifest.json",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("phase_4e_analysis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PHASE_4E = _load_module()

D1, D2 = 1001, 1002
V1, V2 = 3001, 3002
M1, M2, M3, M4 = 2001, 2002, 2003, 2004
S1 = 4001

NODE_FIELDS = (
    "banc_888_id",
    "super_class",
    "cell_class",
    "cell_sub_class",
    "cell_type",
    "side",
    "region",
    "body_part_effector",
    "peripheral_target_type",
    "cell_function",
    "cell_function_detailed",
    "super_cluster",
    "cluster",
    "neurotransmitter_predicted",
    "neurotransmitter_verified",
    "proofread",
    "roughly_proofread",
    "status",
    "nerve",
    "is_descending",
    "is_motor",
    "is_vnc_intrinsic",
    "is_vnc",
    "is_tergotrochanter_candidate",
)


def _node(
    banc_id: int,
    super_class: str,
    side: str,
    *,
    region: str = "brain",
    body_part: str | None = None,
    peripheral_target: str | None = None,
    cell_type: str | None = None,
    proofread: bool = False,
    roughly_proofread: bool = False,
    status: str | None = None,
) -> dict:
    return {
        "banc_888_id": str(banc_id),
        "super_class": super_class,
        "cell_class": super_class,
        "cell_sub_class": None,
        "cell_type": cell_type,
        "side": side,
        "region": region,
        "body_part_effector": body_part,
        "peripheral_target_type": peripheral_target,
        "cell_function": None,
        "cell_function_detailed": None,
        "super_cluster": None,
        "cluster": None,
        "neurotransmitter_predicted": None,
        "neurotransmitter_verified": None,
        "proofread": proofread,
        "roughly_proofread": roughly_proofread,
        "status": status,
        "nerve": None,
        "is_descending": super_class == "descending",
        "is_motor": super_class == "motor",
        "is_vnc_intrinsic": super_class == "ventral_nerve_cord_intrinsic",
        "is_vnc": region == "ventral_nerve_cord",
        "is_tergotrochanter_candidate": (
            super_class == "motor"
            and peripheral_target == "tergotrochanter_extensor_muscle"
        ),
    }


def make_nodes() -> pd.DataFrame:
    rows = [
        _node(D1, "descending", "left", cell_type="d1"),
        _node(D2, "descending", "right", cell_type="d2"),
        _node(
            V1,
            "ventral_nerve_cord_intrinsic",
            "left",
            region="ventral_nerve_cord",
            cell_type="v1",
        ),
        _node(
            V2,
            "ventral_nerve_cord_intrinsic",
            "right",
            region="ventral_nerve_cord",
            cell_type="v2",
        ),
        _node(
            M1,
            "motor",
            "left",
            region="ventral_nerve_cord",
            body_part="front_leg",
            peripheral_target="tergotrochanter_extensor_muscle",
            cell_type="m1",
            proofread=True,
        ),
        _node(
            M2,
            "motor",
            "right",
            region="ventral_nerve_cord",
            body_part="front_leg",
            peripheral_target="tergotrochanter_extensor_muscle",
            cell_type="m2",
        ),
        _node(M3, "motor", "left", region="ventral_nerve_cord", body_part="wing"),
        _node(M4, "motor", "right", region="ventral_nerve_cord", body_part="wing"),
        _node(S1, "sensory", "left"),
    ]
    frame = pd.DataFrame(rows)
    return frame.loc[:, list(NODE_FIELDS)]


# (src, dst, weight) in node-index space. The direct-only edge from S1 to M3
# must never appear in a descending-to-motor count.
EDGES = (
    (0, 4, 3),  # D1 -> M1
    (0, 5, 5),  # D1 -> M2
    (1, 5, 9),  # D2 -> M2
    (1, 4, 12),  # D2 -> M1
    (0, 2, 8),  # D1 -> V1
    (2, 4, 7),  # V1 -> M1
    (0, 3, 2),  # D1 -> V2
    (3, 4, 4),  # V2 -> M1
    (1, 3, 9),  # D2 -> V2
    (3, 5, 6),  # V2 -> M2
    (8, 6, 7),  # S1 -> M3
)


def make_graph(edges, threshold: int, n_nodes: int = 9) -> BancConnectome:
    kept = sorted((s, d, w) for s, d, w in edges if w >= threshold)
    src = np.array([row[0] for row in kept], dtype=np.int64)
    dst = np.array([row[1] for row in kept], dtype=np.int64)
    weight = np.array([row[2] for row in kept], dtype=np.int64)
    out_counts = np.bincount(src, minlength=n_nodes)
    in_counts = np.bincount(dst, minlength=n_nodes)
    return BancConnectome(
        root_ids=np.arange(1, n_nodes + 1, dtype=np.int64),
        out_indptr=np.concatenate(([0], np.cumsum(out_counts))).astype(np.int64),
        edge_src=src,
        edge_dst=dst,
        edge_weight=weight,
        in_indptr=np.concatenate(([0], np.cumsum(in_counts))).astype(np.int64),
        in_edge_idx=np.argsort(dst, kind="stable").astype(np.int64),
        threshold=threshold,
        banc_ids=np.array([str(1000 + index) for index in range(n_nodes)]),
    )


def make_frames():
    nodes = make_nodes()
    arrays = PHASE_4E.annotation_arrays(nodes)
    graphs = {threshold: make_graph(EDGES, threshold) for threshold in (1, 5, 10)}
    return nodes, arrays, graphs


# ---------------------------------------------------------------------------
# helper semantics
# ---------------------------------------------------------------------------


def test_encode_pairs_roundtrip_and_unique_count():
    src = np.array([1, 1, 2, 2], dtype=np.int64)
    dst = np.array([10, 20, 10, 10], dtype=np.int64)
    codes = PHASE_4E._encode_pairs(src, dst)
    assert np.unique(codes).size == 3
    assert sorted(set(codes.tolist())) == sorted(
        ((1 << 32) | 10, (1 << 32) | 20, (2 << 32) | 10)
    )


def test_unique_pair_count_does_not_count_independent_routes():
    # D1 reaches M1 through two different intermediates: two paths, one pair.
    mid_in = np.array([2, 3], dtype=np.int64)
    mid_out = np.array([2, 3], dtype=np.int64)
    used = np.array([2, 3], dtype=np.int64)
    incoming_dn = np.array([0, 0], dtype=np.int64)
    outgoing_mn = np.array([4, 4], dtype=np.int64)
    assert PHASE_4E._unique_pair_count(mid_in, mid_out, used, incoming_dn, outgoing_mn, 2) == 1


def test_metadata_bool_parses_strings_and_nulls():
    assert PHASE_4E._metadata_bool("TRUE") is True
    assert PHASE_4E._metadata_bool("true") is True
    assert PHASE_4E._metadata_bool("FALSE") is False
    assert PHASE_4E._metadata_bool(True) is True
    assert PHASE_4E._metadata_bool(None) is False
    assert PHASE_4E._metadata_bool(np.nan) is False


def test_edge_sides_counts_and_missing_side():
    src_side = np.array([1, 1, 2, 0, 2], dtype=np.int8)
    dst_side = np.array([1, 2, 1, 2, 2], dtype=np.int8)
    sides = PHASE_4E._edge_sides(src_side, dst_side)
    assert sides["left_to_left"] == 1
    assert sides["left_to_right"] == 1
    assert sides["right_to_left"] == 1
    assert sides["right_to_right"] == 1
    assert sides["same_side"] == 2
    assert sides["cross_side"] == 2
    assert sides["same_side_share_of_known"] == 0.5
    assert sides["missing_side_edges"] == 1


def test_classify_motor_inputs_categories():
    _, arrays, _ = make_frames()
    motor_mask = arrays["is_motor"]
    # M1 ipsilateral, M2 contralateral, M3 bilateral, M4 no input.
    src = np.array([0, 0, 0, 1], dtype=np.int64)
    dst = np.array([4, 5, 6, 6], dtype=np.int64)
    result = PHASE_4E._classify_motor_inputs(9, arrays, src, dst, motor_mask)
    assert result["counts"] == {
        "no_direct_input": 1,
        "ipsilateral_only": 1,
        "contralateral_only": 1,
        "bilateral": 1,
        "known_input_side_unknown_mn_side": 0,
        "unknown_input_side_only": 0,
    }
    assert result["population"] == 4


def test_intermediate_masks_exclude_non_neurons_and_effectors():
    nodes = make_nodes()
    rows = [
        _node(5001, "glia", "left", region="ventral_nerve_cord"),
        _node(5002, "motor", "left", region="ventral_nerve_cord"),
        _node(5003, "central", "left", region="ventral_nerve_cord"),
    ]
    frame = pd.concat([nodes, pd.DataFrame(rows)], ignore_index=True)
    arrays = PHASE_4E.annotation_arrays(frame)
    masks = PHASE_4E.intermediate_masks(arrays)
    assert int(masks["strict_vnc_intrinsic"][:9].sum()) == 2
    assert not masks["strict_vnc_intrinsic"][9]
    # Broad includes the central VNC neuron but excludes glia and motor.
    assert masks["broad_vnc_region"][11]
    assert not masks["broad_vnc_region"][9]
    assert not masks["broad_vnc_region"][10]


# ---------------------------------------------------------------------------
# Part B: direct pathways
# ---------------------------------------------------------------------------


def test_direct_pathway_thresholds_and_sides():
    _, arrays, graphs = make_frames()
    t1 = PHASE_4E.direct_pathway(graphs[1], arrays)
    assert t1["descending_population"] == 2
    assert t1["motor_population"] == 4
    assert t1["edges"] == 4
    assert t1["synapses"] == 29
    assert t1["unique_descending_sources"] == 2
    assert t1["unique_motor_targets"] == 2
    assert t1["motor_neurons_without_direct_input"] == 2
    assert t1["descending_without_motor_target"] == 0
    assert t1["edge_sides"]["same_side"] == 2
    assert t1["edge_sides"]["cross_side"] == 2
    assert t1["input_synapses_to_left_targets"] == 15
    assert t1["input_synapses_to_right_targets"] == 14

    t5 = PHASE_4E.direct_pathway(graphs[5], arrays)
    assert (t5["edges"], t5["synapses"]) == (3, 26)
    t10 = PHASE_4E.direct_pathway(graphs[10], arrays)
    assert (t10["edges"], t10["synapses"]) == (1, 12)

    front_leg = next(
        row for row in t1["motor_by_effector"] if row["body_part_effector"] == "front_leg"
    )
    wing = next(
        row for row in t1["motor_by_effector"] if row["body_part_effector"] == "wing"
    )
    assert (front_leg["motor_neurons"], front_leg["dn_edges"]) == (2, 4)
    assert (front_leg["left"], front_leg["right"]) == (1, 1)
    assert (wing["motor_neurons"], wing["dn_edges"]) == (2, 0)


# ---------------------------------------------------------------------------
# Part C: two-hop pathways
# ---------------------------------------------------------------------------


def test_two_hop_paths_unique_pairs_and_thresholds():
    _, arrays, graphs = make_frames()
    masks = PHASE_4E.intermediate_masks(arrays)
    t1 = PHASE_4E.two_hop_pathway(graphs[1], arrays, masks["strict_vnc_intrinsic"])
    assert t1["intermediate_population"] == 2
    assert t1["dn_to_intermediate_edges"] == 3
    assert t1["dn_to_intermediate_synapses"] == 19
    assert t1["intermediate_to_target_edges"] == 3
    assert t1["intermediate_to_target_synapses"] == 17
    assert t1["paths"] == 5
    assert t1["unique_dn_target_pairs"] == 4
    assert t1["unique_descending_sources"] == 2
    assert t1["unique_intermediates"] == 2
    assert t1["unique_targets"] == 2
    assert t1["path_sides"]["same_side_paths"] == 3
    assert t1["path_sides"]["cross_side_paths"] == 2
    assert t1["paths_per_target"]["sum"] == 5

    t5 = PHASE_4E.two_hop_pathway(graphs[5], arrays, masks["strict_vnc_intrinsic"])
    assert (t5["paths"], t5["unique_dn_target_pairs"]) == (2, 2)
    t10 = PHASE_4E.two_hop_pathway(graphs[10], arrays, masks["strict_vnc_intrinsic"])
    assert (t10["paths"], t10["unique_dn_target_pairs"]) == (0, 0)
    assert t10["unique_targets"] == 0


def test_two_hop_broad_mask_adds_central_vnc_neuron():
    nodes = make_nodes()
    frame = pd.concat(
        [nodes, pd.DataFrame([_node(5001, "central", "left", region="ventral_nerve_cord")])],
        ignore_index=True,
    )
    arrays = PHASE_4E.annotation_arrays(frame)
    graph = make_graph(EDGES + ((0, 9, 9), (9, 4, 9)), 1, n_nodes=10)
    masks = PHASE_4E.intermediate_masks(arrays)
    strict = PHASE_4E.two_hop_pathway(graph, arrays, masks["strict_vnc_intrinsic"])
    broad = PHASE_4E.two_hop_pathway(graph, arrays, masks["broad_vnc_region"])
    assert strict["paths"] == 5
    assert broad["paths"] == 6
    assert broad["unique_dn_target_pairs"] == 4


# ---------------------------------------------------------------------------
# Part E: tergotrochanter candidates
# ---------------------------------------------------------------------------


def test_jump_report_direct_two_hop_and_stability():
    nodes, arrays, graphs = make_frames()
    annotations = PHASE_4E._jump_annotations(nodes)
    masks = PHASE_4E.intermediate_masks(arrays)
    report = PHASE_4E.jump_report(graphs, arrays, masks["strict_vnc_intrinsic"], annotations)

    assert annotations["candidates"] == 2
    assert annotations["by_side"] == {"left": 1, "right": 1}
    assert annotations["all_peripheral_target_exact"] is True

    t1 = report["thresholds"]["threshold_1"]
    assert t1["direct_dn_edges"] == 4
    assert t1["direct_dn_synapses"] == 29
    assert t1["direct_descending_sources"] == 2
    assert t1["candidates_with_direct_input"] == 2
    assert t1["candidates_with_two_hop_input"] == 2
    assert t1["two_hop"]["paths"] == 5
    assert t1["direct_edge_sides"]["same_side"] == 2
    assert t1["direct_edge_sides"]["cross_side"] == 2
    assert t1["direct_synapses_to_left_targets"] == 15
    assert t1["direct_synapses_to_right_targets"] == 14
    assert t1["descending_sources_direct_only"] == 0
    assert t1["descending_sources_two_hop_only"] == 0
    assert t1["descending_sources_both"] == 2

    t10 = report["thresholds"]["threshold_10"]
    assert t10["direct_dn_edges"] == 1
    assert t10["direct_dn_synapses"] == 12
    assert t10["candidates_with_two_hop_input"] == 0
    assert t10["descending_sources_direct_only"] == 1


# ---------------------------------------------------------------------------
# Part F: threshold sensitivity
# ---------------------------------------------------------------------------


def _sensitivity_inputs():
    _, arrays, graphs = make_frames()
    direct = {
        f"threshold_{threshold}": PHASE_4E.direct_pathway(graphs[threshold], arrays)
        for threshold in (1, 5, 10)
    }
    masks = PHASE_4E.intermediate_masks(arrays)
    two_hop = {
        f"threshold_{threshold}": {
            "strict_vnc_intrinsic": PHASE_4E.two_hop_pathway(
                graphs[threshold], arrays, masks["strict_vnc_intrinsic"]
            ),
            "broad_vnc_region": PHASE_4E.two_hop_pathway(
                graphs[threshold], arrays, masks["broad_vnc_region"]
            ),
        }
        for threshold in (1, 5, 10)
    }
    nodes = make_nodes()
    jump = PHASE_4E.jump_report(
        graphs,
        arrays,
        masks["strict_vnc_intrinsic"],
        PHASE_4E._jump_annotations(nodes),
    )
    return graphs, arrays, direct, two_hop, jump


def test_threshold_sensitivity_pair_persistence_and_retention():
    graphs, arrays, direct, two_hop, jump = _sensitivity_inputs()
    result = PHASE_4E.threshold_sensitivity(graphs, arrays, direct, two_hop, jump)
    assert result["direct_pairs_present_all_thresholds"] == 1
    assert result["direct_pairs_present_all_thresholds_share_of_t1"] == 0.25
    assert result["direct_pairs_t1_t5"] == 3
    assert result["direct_pairs_t1_t10"] == 1
    assert result["motor_neurons_with_input_all_thresholds"] == 1
    assert result["motor_neurons_without_input"] == {
        "threshold_1": 2,
        "threshold_5": 2,
        "threshold_10": 3,
    }
    front_leg = next(
        row
        for row in result["effector_retention"]
        if row["body_part_effector"] == "front_leg"
    )
    assert front_leg["t1_synapses"] == 29
    assert front_leg["t5_synapses"] == 26
    assert front_leg["t10_synapses"] == 12
    assert front_leg["retention_t5"] == round(26 / 29, 6)
    assert result["top_motor_neurons_by_synapse_loss_t1_to_t5"][0]["banc_888_id"] == str(M1)
    assert result["jump_stability"]["threshold_5"]["direct_dn_edges"] == 3
    assert result["jump_stability"]["threshold_10"]["direct_dn_edges"] == 1
    assert "None" in result["null_model"]


# ---------------------------------------------------------------------------
# Part A: populations and the VNC discrepancy
# ---------------------------------------------------------------------------


def test_population_report_counts():
    nodes = make_nodes()
    audit = {
        "D_annotation_quality": {
            "populations": {
                "motor": {"rows": 4},
                "descending": {"rows": 2},
                "ascending": {"rows": 0},
                "ventral_nerve_cord_intrinsic": {"rows": 3},
            }
        }
    }
    result = PHASE_4E.population_report(nodes, audit)
    counts = result["counts"]
    assert counts["total_graph_nodes"] == 9
    assert counts["descending"] == 2
    assert counts["motor"] == 4
    assert counts["vnc_intrinsic"] == 2
    assert counts["vnc_region"] == 6
    assert counts["left_motor"] == 2
    assert counts["right_motor"] == 2
    assert counts["tergotrochanter_motor_candidates"] == 2
    assert result["phase_4c5_comparison"]["vnc_intrinsic"]["delta"] == -1
    assert result["annotation_completeness"]["motor_neurons"] == 4


def test_vnc_intrinsic_discrepancy_lists_exact_missing_ids():
    nodes = make_nodes()
    meta = pd.DataFrame(
        {
            "banc_888_id": [V1, V2, 9999],
            "super_class": ["ventral_nerve_cord_intrinsic"] * 3,
            "cell_class": ["intrinsic"] * 3,
            "cell_sub_class": [None] * 3,
            "cell_type": ["v1", "v2", "v3"],
            "side": ["left", "right", "left"],
            "region": ["ventral_nerve_cord"] * 3,
            "proofread": ["TRUE", "FALSE", "TRUE"],
            "roughly_proofread": ["FALSE", "FALSE", "FALSE"],
            "status": ["DONE", "DONE", "MANC_MATCH_WRONG_SIDE"],
            "neurotransmitter_predicted": [None] * 3,
            "neurotransmitter_verified": ["acetylcholine", None, None],
        }
    )
    result = PHASE_4E.vnc_intrinsic_discrepancy(meta, nodes)
    assert result["missing_count"] == 1
    assert result["missing_ids"][0]["banc_888_id"] == "9999"
    assert result["missing_ids"][0]["proofread"] is True
    assert result["missing_ids"][0]["status"] == "MANC_MATCH_WRONG_SIDE"
    assert result["missing_proofread_true"] == 1
    assert result["missing_roughly_proofread_true"] == 0


# ---------------------------------------------------------------------------
# real-artifact integration checks
# ---------------------------------------------------------------------------

ARTIFACTS_PRESENT = all(path.exists() for path in ARTIFACTS)


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="Phase 4D artifacts not built")
def test_phase_4e_report_matches_phase_4d_artifacts():
    assert REPORT_JSON.exists()
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    nodes = pd.read_csv(OUT_DIR / "banc_nodes.csv.gz", dtype={"banc_888_id": str})
    assert len(nodes) == report["populations"]["counts"]["total_graph_nodes"] == 172_433
    assert np.array_equal(
        nodes["node_index"].to_numpy(), np.arange(len(nodes), dtype=np.int64)
    )

    node_ids = nodes["banc_888_id"].astype("int64").to_numpy()
    for threshold in (1, 5, 10):
        graph = BancConnectome.load(OUT_DIR / f"banc_graph_t{threshold}.npz")
        assert graph.threshold == threshold
        assert np.array_equal(graph.root_ids, node_ids)
        assert int(graph.edge_weight.min()) >= threshold
        assert not np.any(graph.edge_src == graph.edge_dst)

    assert report["verdict"] == "PASS WITH LIMITATIONS"
    assert report["phase_4c5_reproduction"]["pass"] is True
    assert report["vnc_intrinsic_discrepancy"]["missing_count"] == 16
    assert report["vnc_intrinsic_discrepancy"]["missing_proofread_true"] == 1
    assert report["integrity"]["manifest_verification_pass"] is True
    assert report["integrity"]["fafb_isolation_unchanged"] is True
