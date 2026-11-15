"""Focused tests for the Phase 4C.5 BANC graph readiness audit logic.

These tests use a hand-built six-neuron graph. They do not read the BANC
files, so they run without the external dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiments.phase_4c.audit_banc_graph import (
    _json_default,
    audit_annotations,
    audit_canonical_ids,
    audit_edge_integrity,
    audit_locomotor_readiness,
    audit_self_edges,
    audit_weight_semantics,
    build_graph_policy,
)

DN1 = 1001
DN2 = 1002
MN_L = 2001
MN_R = 2002
VNC = 3001
SENSORY = 4001
ORPHAN = 5001


def make_meta() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "banc_888_id": [str(v) for v in (DN1, DN2, MN_L, MN_R, VNC, SENSORY, ORPHAN)],
            "root_id": [str(DN1), str(DN2), str(MN_L), "9999", str(VNC), str(SENSORY), str(ORPHAN)],
            "root_626": [str(v) for v in (DN1, DN2, MN_L, MN_R, VNC, SENSORY, ORPHAN)],
            "root_850": [str(v) for v in (DN1, DN2, MN_L, MN_R, VNC, SENSORY, ORPHAN)],
            "root_888": [str(v) for v in (DN1, DN2, MN_L, MN_R, VNC, SENSORY, ORPHAN)],
            "root_890": [str(v) for v in (DN1, DN2, MN_L, MN_R, VNC, SENSORY, "")],
            "proofread": ["TRUE"] * 7,
            "roughly_proofread": ["FALSE"] * 7,
            "status": [None, None, "REVIEW_MATCH_AN_DN", None, None, None, None],
            "side": ["left", "right", "left", "right", "left", "right", None],
            "region": ["central_brain", "central_brain", "ventral_nerve_cord", "ventral_nerve_cord", "ventral_nerve_cord", "central_brain", None],
            "super_class": [
                "descending",
                "descending",
                "motor",
                "motor",
                "ventral_nerve_cord_intrinsic",
                "sensory",
                None,
            ],
            "cell_class": ["DN"] * 2 + ["leg_motor"] * 2 + ["premotor"] + ["sensory"] + [None],
            "cell_type": ["DN1", "DN2", "MN_L", "MN_R", "VNC1", "S1", None],
            "super_cluster": ["walking", "walking steering", None, None, None, None, None],
            "body_part_effector": [None, None, "front_leg", "front_leg", None, None, None],
            "peripheral_target_type": [
                None,
                None,
                "tergotrochanter_extensor_muscle",
                "tibia_flexor_muscle",
                None,
                None,
                None,
            ],
            "cell_function": [None, None, "leg_motor", "leg_motor", None, None, None],
            "neurotransmitter_predicted": ["acetylcholine"] * 6 + [None],
            "neurotransmitter_verified": ["acetylcholine", None, "glutamate", None, None, None, None],
            "neurotransmitter_score": [0.9] * 7,
            "fafb_match": [str(7001), str(7002), None, None, None, None, None],
            "fafb_nblast_match": [str(7001), None, None, None, None, None, None],
            "fafb_cell_type": ["DN1", "DN2", None, None, None, None, None],
        }
    )


def make_edges() -> dict[str, np.ndarray]:
    pre = np.array([DN1, DN1, DN2, VNC, SENSORY, DN2, DN1], dtype="int64")
    post = np.array([MN_L, MN_R, MN_R, MN_L, MN_L, VNC, DN1], dtype="int64")
    count = np.array([5, 2, 7, 3, 4, 6, 1], dtype="int64")
    post_count = np.array([12, 9, 9, 6, 1, 12, 9], dtype="int64")  # indexed by node order below
    # Node order: DN1, DN2, MN_L, MN_R, VNC, SENSORY
    node_post_count = {DN1: 1, DN2: 9, MN_L: 12, MN_R: 9, VNC: 6, SENSORY: 0}
    node_pre_count = {DN1: 8, DN2: 13, MN_L: 0, MN_R: 0, VNC: 3, SENSORY: 4}
    return {
        "pre": pre,
        "post": post,
        "count": count,
        "norm": count / np.array([node_post_count[p] for p in post]),
        "pre_count": np.array([node_pre_count[p] for p in pre], dtype="int64"),
        "post_count": np.array([node_post_count[p] for p in post], dtype="int64"),
    }


def make_backbone() -> pd.DataFrame:
    return pd.DataFrame({"pt_root_id": [MN_L, MN_R], "valid": [True, True], "valid_id": [MN_L, MN_R], "proofread": [True, True]})


def make_reviewed() -> pd.DataFrame:
    return pd.DataFrame({"pt_root_id": [DN1], "match_id": [7001], "valid": ["t"]})


def test_canonical_id_prefers_banc_888_id() -> None:
    meta = make_meta()
    report = audit_canonical_ids(meta)
    assert report["canonical"] == "banc_888_id"
    assert report["banc_888_id"]["duplicates"] == 0
    assert report["columns"]["root_888"]["mismatch_rows"] == 0
    assert report["columns"]["root_id"]["mismatch_rows"] == 1
    assert report["columns"]["root_890"]["nulls"] == 1
    assert report["verdict"] == "PASS"


def test_canonical_id_flags_duplicate_primary_key() -> None:
    meta = make_meta()
    meta.loc[1, "banc_888_id"] = meta.loc[0, "banc_888_id"]
    report = audit_canonical_ids(meta)
    assert report["banc_888_id"]["duplicates"] == 1
    assert report["verdict"] == "FAIL"


def test_self_edge_audit_counts_rows_and_synapses() -> None:
    edges = make_edges()
    meta = make_meta()
    report = audit_self_edges(edges["pre"], edges["post"], edges["count"], meta)
    assert report["rows"] == 1
    assert report["unique_nodes"] == 1
    assert report["summed_count"] == 1
    assert report["summed_count_share"] == pytest.approx(1 / 28)
    assert report["by_super_class"] == {"descending": 1}


def test_edge_integrity_accepts_clean_graph() -> None:
    edges = make_edges()
    meta_ids = make_meta()["banc_888_id"].astype("int64").to_numpy()
    report = audit_edge_integrity(
        edges["pre"],
        edges["post"],
        edges["count"],
        edges["norm"],
        meta_ids,
        {name: 0 for name in ("pre", "post", "count", "norm", "pre_count", "post_count")},
        len(edges["pre"]),
    )
    assert report["unique_directed_pairs"] == 7
    assert report["duplicate_pair_rows"] == 0
    assert report["aggregation_needed"] is False
    assert report["endpoint_coverage"] == 1.0
    assert report["verdict"] == "PASS"


def test_edge_integrity_detects_duplicate_pair_and_missing_endpoint() -> None:
    pre = np.array([DN1, DN1, 8888], dtype="int64")
    post = np.array([MN_L, MN_L, MN_R], dtype="int64")
    count = np.array([2, 3, 1], dtype="int64")
    meta_ids = np.array([DN1, MN_L, MN_R], dtype="int64")
    report = audit_edge_integrity(
        pre,
        post,
        count,
        count / 10.0,
        meta_ids,
        {"pre": 0, "post": 0, "count": 0, "norm": 0, "pre_count": 0, "post_count": 0},
        3,
    )
    assert report["duplicate_pair_rows"] == 1
    assert report["aggregation_needed"] is True
    assert report["nodes_missing_from_metadata"] == 1
    assert report["verdict"] == "FAIL"


def test_weight_semantics_reproduce_norm_and_totals() -> None:
    edges = make_edges()
    report = audit_weight_semantics(
        edges["pre"], edges["post"], edges["count"], edges["norm"], edges["pre_count"], edges["post_count"]
    )
    assert report["summed_count"] == 28
    assert report["sum_of_pre_count"] == 28
    assert report["sum_of_post_count"] == 28
    assert report["pre_count_equals_outgoing_sum_share"] == 1.0
    assert report["post_count_equals_incoming_sum_share"] == 1.0
    assert report["norm_vs_count_over_post_count"]["max_relative_error"] == pytest.approx(0.0, abs=1e-12)
    assert report["verdict"] == "PASS"


def test_weight_semantics_detects_broken_total() -> None:
    edges = make_edges()
    pre_count = edges["pre_count"].copy()
    pre_count[0] += 1
    report = audit_weight_semantics(
        edges["pre"], edges["post"], edges["count"], edges["norm"], pre_count, edges["post_count"]
    )
    assert report["pre_count_equals_outgoing_sum_share"] < 1.0
    assert report["verdict"] == "FAIL"


def test_annotation_audit_keeps_missing_as_unknown() -> None:
    report = audit_annotations(make_meta(), make_backbone(), make_reviewed())
    assert report["meta_rows"] == 7
    assert report["annotated_neurons"] == 6
    assert report["super_class_missing"] == 1
    assert report["super_class_missing_proofread_true"] == 1
    assert report["populations"]["motor"]["rows"] == 2
    assert report["populations"]["motor"]["cell_type_missing"] == 0
    assert report["populations"]["descending"]["fafb_match_present"] == 2
    assert report["backbone_proofread"]["unique_pt_root_id"] == 2
    assert report["reviewed_matches"]["valid_t"] == 1
    assert report["verdict"] == "PASS"


def test_locomotor_readiness_counts_direct_and_two_hop() -> None:
    edges = make_edges()
    report = audit_locomotor_readiness(edges["pre"], edges["post"], edges["count"], make_meta())
    direct = report["direct_dn_to_mn"]
    assert direct["edges"] == 3
    assert direct["descending_neurons"] == 2
    assert direct["motor_neurons"] == 2
    assert direct["motor_coverage"] == 1.0
    assert direct["sides"]["same_side"] == 2
    assert direct["sides"]["cross_side"] == 1
    assert report["two_hop_dn_vnc_mn"]["paths"] == 1
    assert report["two_hop_dn_vnc_mn"]["unique_dn_mn_pairs"] == 1
    assert report["jump_tergotrochanter"]["motor_neurons"] == 1
    assert report["jump_tergotrochanter"]["dn_edges"] == 1
    assert report["motor_neurons_by_body_part"]["front_leg"]["motor_neurons"] == 2


def test_policy_reflects_measured_values() -> None:
    edges = make_edges()
    meta = make_meta()
    meta_ids = meta["banc_888_id"].astype("int64").to_numpy()
    audit = {
        "A_canonical_id_integrity": audit_canonical_ids(meta),
        "B_self_edges": audit_self_edges(edges["pre"], edges["post"], edges["count"], meta),
        "C_edge_integrity": audit_edge_integrity(
            edges["pre"], edges["post"], edges["count"], edges["norm"], meta_ids,
            {"pre": 0, "post": 0, "count": 0, "norm": 0, "pre_count": 0, "post_count": 0},
            len(edges["pre"]),
        ),
        "D_annotation_quality": audit_annotations(meta, make_backbone(), make_reviewed()),
        "E_weight_semantics": audit_weight_semantics(
            edges["pre"], edges["post"], edges["count"], edges["norm"], edges["pre_count"], edges["post_count"]
        ),
        "F_locomotor_readiness": audit_locomotor_readiness(edges["pre"], edges["post"], edges["count"], meta),
    }
    audit["C_edge_integrity"]["metadata_rows_without_edges"] = 1
    audit["C_edge_integrity"]["isolated_proofread_true"] = 1
    audit["C_edge_integrity"]["graph_nodes_missing_super_class"] = 2
    policy = build_graph_policy(audit)
    assert policy["canonical_node_id"]["field"] == "banc_888_id"
    assert policy["edge_aggregation"]["policy"] == "none"
    assert policy["self_edge_policy"]["policy"] == "exclude_from_simulation_graph_keep_in_raw_file"
    assert policy["edge_weight"]["initial_threshold"] == 5
    assert policy["edge_weight"]["do_not_use"] == "norm as a physiological weight"
    assert policy["annotation_handling"]["sign_prior"] == "verified neurotransmitter only"
    assert policy["node_inclusion"]["unannotated_nodes"] == 2
    assert policy["isolated_nodes"]["rows"] == 1


def test_json_default_handles_numpy_scalars() -> None:
    assert _json_default(np.int64(3)) == 3
    assert _json_default(np.float64(1.5)) == 1.5
    assert _json_default(np.bool_(True)) is True
    assert _json_default(np.array([1, 2])).__class__ is list
