"""Phase 4F population extraction from published BANC annotations."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import OUT_DIR as BANC_OUT_DIR
from motor.populations import (
    ACTION_POPULATIONS,
    UNSUPPORTED_ACTIONS,
    MotorPopulations,
    PopulationOptions,
    build_populations,
    load_banc_populations,
)

ARTIFACTS_PRESENT = all(
    (BANC_OUT_DIR / name).is_file()
    for name in (
        "banc_nodes.csv.gz",
        "banc_graph_t1.npz",
        "banc_graph_t5.npz",
        "banc_graph_t10.npz",
    )
)

COLUMNS = (
    "super_class",
    "side",
    "body_part_effector",
    "peripheral_target_type",
    "proofread",
)


def node(super_class, side, effector, target=None, proofread="TRUE") -> dict:
    return {
        "super_class": super_class,
        "side": side,
        "body_part_effector": effector,
        "peripheral_target_type": target,
        "proofread": proofread,
    }


def synthetic_nodes() -> pd.DataFrame:
    rows = [
        node("motor", "left", "front_leg", "tergotrochanter_extensor_muscle"),
        node("motor", "left", "middle_leg"),
        node("motor", "right", "hind_leg", "tergotrochanter_extensor_muscle"),
        node("motor", "right", "front_leg"),
        node("motor", "left", "wing", "wing_steering_muscle"),
        node("motor", None, "front_leg"),
        node("motor", "left", None),
        node("descending", "left", "front_leg"),
        node("motor", "right", "hind_leg", "tergotrochanter_extensor_muscle"),
        node("central", "left", "front_leg"),
    ]
    frame = pd.DataFrame(rows, columns=list(COLUMNS))
    frame.insert(0, "node_index", np.arange(len(frame), dtype=np.int64))
    frame.insert(1, "banc_888_id", [str(1000 + index) for index in range(len(frame))])
    return frame


def test_default_populations_are_disjoint_and_skip_tergotrochanter() -> None:
    populations = build_populations(synthetic_nodes())
    assert populations.sizes == {"LEFT": 1, "RIGHT": 1, "JUMP": 3}
    assert int(populations.assigned_union.sum()) == 5
    assert int(populations.motor_mask.sum()) == 8
    assert int(populations.unassigned_mask.sum()) == 3
    masks = [populations.mask(action) for action in ACTION_POPULATIONS]
    assert not np.any(masks[0] & masks[1])
    assert not np.any(masks[0] & masks[2])
    assert not np.any(masks[1] & masks[2])


def test_inclusion_policy_keeps_tergotrochanter_in_leg_pools() -> None:
    options = PopulationOptions(jump_membership_in_leg_pools=True)
    populations = build_populations(synthetic_nodes(), options=options)
    assert populations.sizes == {"LEFT": 2, "RIGHT": 3, "JUMP": 3}
    assert int(populations.assigned_union.sum()) == 5
    assert int(populations.unassigned_mask.sum()) == 3
    assert populations.composition["jump_candidates_in_leg_pools"] == 3
    assert "overlap by construction" in populations.provenance["overlap_policy"]


def test_composition_preserves_jump_side_and_effector_structure() -> None:
    populations = build_populations(synthetic_nodes())
    jump = populations.composition["JUMP"]
    assert jump["size"] == 3
    assert jump["left"] == 1
    assert jump["right"] == 2
    assert jump["effectors"] == {"front_leg": 1, "hind_leg": 2}
    assert jump["proofread_true"] == 3


def test_unassigned_preserves_unknown_annotations() -> None:
    populations = build_populations(synthetic_nodes())
    unassigned = populations.unassigned_mask
    assert bool(unassigned[4])  # non-leg motor neuron
    assert bool(unassigned[5])  # motor neuron with no side
    assert bool(unassigned[6])  # motor neuron with no effector
    assert populations.composition["motor_missing_side"] == 1
    assert populations.composition["motor_missing_effector"] == 1


def test_non_motor_neurons_are_never_assigned() -> None:
    populations = build_populations(synthetic_nodes())
    for index in (7, 9):
        assert not populations.motor_mask[index]
        for action in ACTION_POPULATIONS:
            assert not populations.mask(action)[index]


def test_unsupported_actions_are_reported_not_implemented() -> None:
    populations = build_populations(synthetic_nodes())
    assert set(UNSUPPORTED_ACTIONS) == {"ROLL", "DUCK"}
    assert "ROLL" not in populations.masks
    assert "DUCK" not in populations.masks
    definitions = populations.provenance["definitions"]
    assert definitions["ROLL"].startswith("unsupported")
    assert definitions["DUCK"].startswith("unsupported")
    assert populations.provenance["unsupported_actions"] == UNSUPPORTED_ACTIONS


def test_threshold_is_recorded_in_provenance() -> None:
    populations = build_populations(synthetic_nodes(), threshold=10)
    assert populations.threshold == 10
    assert populations.provenance["graph_threshold"] == 10
    assert populations.report()["graph_threshold"] == 10


def test_node_index_must_be_contiguous() -> None:
    frame = synthetic_nodes()
    frame["node_index"] = frame["node_index"][::-1].to_numpy()
    with pytest.raises(ValueError, match="node_index"):
        build_populations(frame)


def test_n_neurons_must_match_rows() -> None:
    with pytest.raises(ValueError, match="does not match"):
        build_populations(synthetic_nodes(), n_neurons=5)


def test_required_columns_are_validated() -> None:
    frame = synthetic_nodes().drop(columns=["side"])
    with pytest.raises(ValueError, match="missing columns"):
        build_populations(frame)


def test_motor_populations_validates_mask_shape() -> None:
    frame = synthetic_nodes()
    populations = build_populations(frame)
    with pytest.raises(ValueError, match="shape"):
        MotorPopulations(
            n_neurons=populations.n_neurons,
            threshold=5,
            masks={**populations.masks, "LEFT": np.zeros(3, dtype=bool)},
            motor_mask=populations.motor_mask,
            unassigned_mask=populations.unassigned_mask,
            composition={},
            provenance={},
        )


def test_motor_populations_validates_mask_names() -> None:
    populations = build_populations(synthetic_nodes())
    with pytest.raises(ValueError, match="cover exactly"):
        MotorPopulations(
            n_neurons=populations.n_neurons,
            threshold=5,
            masks={"LEFT": populations.mask("LEFT")},
            motor_mask=populations.motor_mask,
            unassigned_mask=populations.unassigned_mask,
            composition={},
            provenance={},
        )
    with pytest.raises(KeyError, match="unknown action"):
        populations.mask("ROLL")


def test_empty_population_is_allowed() -> None:
    frame = synthetic_nodes()
    frame["peripheral_target_type"] = None
    frame["body_part_effector"] = "wing"
    populations = build_populations(frame)
    assert populations.sizes == {"LEFT": 0, "RIGHT": 0, "JUMP": 0}
    assert int(populations.unassigned_mask.sum()) == 8


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="BANC artifacts are absent")
def test_real_banc_populations_match_phase_4e_counts() -> None:
    populations = load_banc_populations()
    assert populations.n_neurons == 172_433
    assert populations.threshold == 5
    assert populations.provenance["graph_edges"] == 1_535_710
    assert populations.sizes == {"LEFT": 185, "RIGHT": 186, "JUMP": 20}
    assert int(populations.motor_mask.sum()) == 805
    assert int(populations.assigned_union.sum()) == 391
    assert int(populations.unassigned_mask.sum()) == 414
    jump = populations.composition["JUMP"]
    assert jump["left"] == 10 and jump["right"] == 10
    assert jump["effectors"] == {"front_leg": 8, "hind_leg": 6, "middle_leg": 6}


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="BANC artifacts are absent")
def test_real_inclusion_policy_matches_annotation_counts() -> None:
    populations = load_banc_populations(
        options=PopulationOptions(jump_membership_in_leg_pools=True)
    )
    assert populations.sizes == {"LEFT": 195, "RIGHT": 196, "JUMP": 20}
    assert populations.composition["jump_candidates_in_leg_pools"] == 20


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="BANC artifacts are absent")
def test_real_population_membership_is_threshold_invariant() -> None:
    reference = load_banc_populations(threshold=5)
    for threshold in (1, 10):
        other = load_banc_populations(threshold=threshold)
        assert other.threshold == threshold
        assert other.sizes == reference.sizes
        for action in ACTION_POPULATIONS:
            assert np.array_equal(other.mask(action), reference.mask(action))
