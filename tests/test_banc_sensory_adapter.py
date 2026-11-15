"""Phase 4H.4: BANC sensory mapping and event-pulsed drive."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from brain.banc_sensory_adapter import (
    BancEventDrive,
    BancSensoryMapping,
    ConstantChargeDrive,
    shuffle_feature_identities,
    temporally_shuffle_events,
    validate_events,
)
from sensory.population_encoder import build_encoders

CONFIG_PATH = Path("configs/banc_sensory_mapping.yaml")


class FakeGraph:
    def __init__(self, n_nodes: int) -> None:
        self.n_nodes = n_nodes
        self.root_ids = np.arange(10_000, 10_000 + n_nodes, dtype=np.int64)
        self.threshold = 5


def _nodes():
    import pandas as pd

    n = 60
    super_class = np.array(
        ["visual_projection"] * 24
        + ["optic_lobe_intrinsic"] * 16
        + ["sensory"] * 10
        + ["motor"] * 10,
        dtype=object,
    )
    side = np.array([""] * n, dtype=object)
    side[0:8] = "left"
    side[8:16] = "right"
    side[16:24] = ""
    side[0:24] = side[0:24]
    cell_function = np.array([""] * n, dtype=object)
    cell_function[24:40] = "visual_achromatic"
    peripheral = np.array([""] * n, dtype=object)
    peripheral[40:50] = "photoreceptor"
    return pd.DataFrame(
        {
            "banc_888_id": np.arange(n, dtype=np.int64),
            "super_class": super_class,
            "cell_class": np.full(n, "", dtype=object),
            "cell_function": cell_function,
            "body_part_sensory": np.full(n, "", dtype=object),
            "peripheral_target_type": peripheral,
            "region": np.array(
                ["optic_lobe"] * 40 + ["ventral_nerve_cord"] * 20, dtype=object
            ),
            "flow": np.array(
                ["intrinsic"] * 40 + ["afferent"] * 10 + ["efferent"] * 10,
                dtype=object,
            ),
            "side": side,
        }
    )


NODES = _nodes()
GRAPH = FakeGraph(len(NODES))
MOTOR = np.zeros(len(NODES), dtype=bool)
MOTOR[50:60] = True
ACTIONS = {
    "LEFT": np.zeros(len(NODES), dtype=bool),
    "RIGHT": np.zeros(len(NODES), dtype=bool),
    "JUMP": np.zeros(len(NODES), dtype=bool),
}
ACTIONS["LEFT"][50:53] = True
ACTIONS["RIGHT"][53:56] = True
ACTIONS["JUMP"][56:57] = True

MAPPING = {
    "seed": 7,
    "allow_duplicates": False,
    "pools": {
        "visual_projection": {"super_class": ["visual_projection"]},
        "visual_left": {"super_class": ["visual_projection"], "side": ["left"]},
        "visual_center": {"super_class": ["visual_projection"], "side": ["unassigned"]},
        "visual_right": {"super_class": ["visual_projection"], "side": ["right"]},
        "optic": {
            "super_class": ["optic_lobe_intrinsic"],
            "cell_function": ["visual_achromatic"],
        },
        "photoreceptor": {"peripheral_target_type": ["photoreceptor"]},
    },
    "populations": {
        "train_lane": {
            "lane_pools": {
                "left": "visual_left",
                "center": "visual_center",
                "right": "visual_right",
            },
            "neurons_per_lane": 2,
            "evidence": "computational convention",
            "hypothesis": "H-test-lane",
        },
        "train_present": {
            "pool": "visual_projection",
            "n_neurons": 4,
            "evidence": "published annotation",
            "hypothesis": "H-test-present",
        },
        "train_distance": {
            "pool": "optic",
            "n_neurons": 4,
            "evidence": "connectivity hypothesis",
            "hypothesis": "H-test-distance",
        },
        "obstacle_present": {
            "pool": "photoreceptor",
            "n_neurons": 3,
            "evidence": "published annotation",
            "hypothesis": "H-test-obstacle",
        },
        "obstacle_type": {
            "lane_pools": {"low": "photoreceptor", "high": "photoreceptor"},
            "neurons_per_lane": 2,
            "evidence": "computational convention",
            "hypothesis": "H-test-type",
        },
    },
}

FEATURES = {
    "train_present": {"kind": "boolean", "n_neurons": 4, "current_pa": 200.0},
    "train_lane": {
        "kind": "lane",
        "lanes": 3,
        "neurons_per_lane": 2,
        "current_pa": 200.0,
    },
    "train_distance": {
        "kind": "gaussian",
        "n_neurons": 4,
        "minimum": 0.0,
        "maximum": 1.0,
        "sigma_fraction": 0.2,
        "current_pa": 200.0,
    },
    "obstacle_present": {"kind": "boolean", "n_neurons": 3, "current_pa": 200.0},
    "obstacle_type": {
        "kind": "lane",
        "lanes": 2,
        "neurons_per_lane": 2,
        "current_pa": 200.0,
    },
}


def make_mapping(**overrides):
    config = json.loads(json.dumps(MAPPING))
    config.update(overrides)
    return BancSensoryMapping(
        NODES,
        GRAPH,
        config,
        motor_mask=MOTOR,
        action_masks=ACTIONS,
    )


def event(kind="appeared", *, time_ms=33.3, features=None, frame=1, track=1):
    return {
        "frame_index": frame,
        "frame_id": f"frame-{frame}",
        "track_id": track,
        "event": kind,
        "class_name": "train",
        "lane": 0,
        "time_ms": time_ms,
        "confidence": 0.9,
        "distance_proxy": 0.5,
        "is_pulse": bool(features),
        "feature_values": dict(features or {}),
    }


def make_drive(events):
    encoders = build_encoders(
        {
            "train_present": FEATURES["train_present"],
            "train_lane": FEATURES["train_lane"],
            "train_distance": FEATURES["train_distance"],
        }
    )
    mapping = make_mapping()
    return BancEventDrive(
        mapping,
        encoders,
        events,
        current_pa={"train_present": 200.0, "train_lane": 200.0, "train_distance": 200.0},
        duration_ms=500.0,
        decay_ms=150.0,
        dt_ms=0.5,
    )


# -- mapping ----------------------------------------------------------------


def test_mapping_excludes_motor_and_action_neurons():
    mapping = make_mapping()
    for feature in mapping.features:
        indices = mapping.indices(feature)
        assert not MOTOR[indices].any()
        assert not ACTIONS["LEFT"][indices].any()
        assert not ACTIONS["RIGHT"][indices].any()
        assert not ACTIONS["JUMP"][indices].any()
    report = mapping.report()
    assert report["motor_overlap"] == 0
    assert report["action_overlap"] == 0
    assert report["n_stimulated_neurons"] == 4 + 3 * 2 + 4 + 3 + 2 * 2


def test_mapping_is_disjoint_and_size_matched():
    mapping = make_mapping()
    seen = set()
    for feature in mapping.features:
        indices = [int(value) for value in mapping.indices(feature)]
        assert not seen.intersection(indices)
        seen.update(indices)
    assert mapping.size("train_lane") == 6
    assert mapping.size("train_present") == 4


def test_mapping_signature_is_deterministic():
    first = make_mapping().signature()["mapping_sha256"]
    second = make_mapping().signature()["mapping_sha256"]
    assert first == second
    other = make_mapping(seed=99).signature()["mapping_sha256"]
    assert other != first


def test_mapping_rejects_unknown_label():
    config = json.loads(json.dumps(MAPPING))
    config["pools"]["photoreceptor"] = {"super_class": ["photoreceptor"]}
    with pytest.raises(ValueError, match="unknown label"):
        BancSensoryMapping(
            NODES, GRAPH, config, motor_mask=MOTOR, action_masks=ACTIONS
        )


def test_mapping_rejects_unknown_field():
    config = json.loads(json.dumps(MAPPING))
    config["pools"]["photoreceptor"] = {"not_a_field": ["x"]}
    with pytest.raises(ValueError, match="unknown fields"):
        BancSensoryMapping(
            NODES, GRAPH, config, motor_mask=MOTOR, action_masks=ACTIONS
        )


def test_mapping_requires_evidence_and_hypothesis():
    config = json.loads(json.dumps(MAPPING))
    del config["populations"]["train_present"]["hypothesis"]
    with pytest.raises(ValueError, match="evidence label"):
        BancSensoryMapping(
            NODES, GRAPH, config, motor_mask=MOTOR, action_masks=ACTIONS
        )


def test_random_matched_mapping_is_size_matched_and_excludes_motor():
    real = make_mapping()
    randomised = BancSensoryMapping(
        NODES,
        GRAPH,
        json.loads(json.dumps(MAPPING)),
        motor_mask=MOTOR,
        action_masks=ACTIONS,
        randomise_pools=True,
    )
    assert {
        feature: real.size(feature) for feature in real.features
    } == {feature: randomised.size(feature) for feature in randomised.features}
    assert randomised.report()["pool_mode"] == "random_matched_non_motor"
    for feature in randomised.features:
        indices = randomised.indices(feature)
        assert not MOTOR[indices].any()
        assert not ACTIONS["JUMP"][indices].any()


# -- event validation -------------------------------------------------------


def test_validate_events_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind"):
        validate_events([event("teleported")], features=FEATURES)


def test_validate_events_rejects_unknown_feature():
    with pytest.raises(ValueError, match="unknown features"):
        validate_events([event(features={"not_a_feature": 1.0})], features=FEATURES)


def test_validate_events_rejects_non_monotone_timestamps():
    events = [event(time_ms=100.0), event(time_ms=50.0)]
    with pytest.raises(ValueError, match="non-decreasing"):
        validate_events(events, features=FEATURES)


def test_validate_events_rejects_negative_timestamps():
    with pytest.raises(ValueError, match="non-negative"):
        validate_events([event(time_ms=-1.0)], features=FEATURES)


def test_validate_events_rejects_missing_field():
    payload = event(features={"train_present": 1.0})
    del payload["track_id"]
    with pytest.raises(ValueError, match="missing fields"):
        validate_events([payload], features=FEATURES)


def test_validate_events_preserves_identity_fields():
    payload = event(features={"train_present": 1.0})
    validated = validate_events([payload], features=FEATURES)
    assert validated[0]["track_id"] == payload["track_id"]
    assert validated[0]["lane"] == payload["lane"]
    assert validated[0]["time_ms"] == payload["time_ms"]


# -- drive ------------------------------------------------------------------


def test_drive_linear_decay_and_targets():
    payload = event(
        time_ms=100.0,
        features={"train_present": 1.0, "train_lane": 0, "train_distance": 0.5},
    )
    drive = make_drive([payload])
    indices = drive.stimulated_indices
    assert not MOTOR[indices].any()
    current = np.zeros(len(NODES), dtype=np.float64)
    drive.apply(0, 100.0, current)
    peak = current[indices]
    assert peak.max() == pytest.approx(200.0, abs=1e-9)
    current = np.zeros(len(NODES), dtype=np.float64)
    drive.apply(0, 175.0, current)
    assert current[indices].max() == pytest.approx(100.0, abs=1e-9)
    current = np.zeros(len(NODES), dtype=np.float64)
    drive.apply(0, 251.0, current)
    assert np.allclose(current, 0.0)


def test_drive_is_deterministic():
    payload = event(features={"train_present": 1.0, "train_lane": 1})
    first = make_drive([payload])
    second = make_drive([payload])
    assert first.signature_sha256() == second.signature_sha256()
    changed = make_drive([event(time_ms=200.0, features={"train_present": 1.0})])
    assert changed.signature_sha256() != first.signature_sha256()


def test_drive_ignores_events_without_feature_values():
    payload = event(features=None)
    drive = make_drive([payload])
    assert drive.describe()["n_pulses"] == 0
    assert drive.signature_sha256()


def test_temporal_shuffle_preserves_times_and_identities():
    events = validate_events(
        [
            event(features={"train_present": 1.0}, time_ms=0.0),
            event("approaching", features={"train_distance": 0.4}, time_ms=10.0, track=2),
            event("occluded", time_ms=20.0, track=3),
        ],
        features=FEATURES,
    )
    shuffled = temporally_shuffle_events(events, seed=5)
    assert len(shuffled) == len(events)
    assert sorted(item["time_ms"] for item in shuffled) == sorted(
        item["time_ms"] for item in events
    )
    assert sorted(item["track_id"] for item in shuffled) == [1, 2, 3]
    assert all(
        shuffled[position]["time_ms"] <= shuffled[position + 1]["time_ms"]
        for position in range(len(shuffled) - 1)
    )
    assert sorted(
        (item["track_id"], item["event"]) for item in shuffled
    ) == sorted((item["track_id"], item["event"]) for item in events)


def test_feature_identity_shuffle_preserves_times_and_payloads():
    events = validate_events(
        [
            event(features={"train_present": 1.0}, time_ms=0.0),
            event("approaching", features={"train_distance": 0.4}, time_ms=10.0, track=2),
            event("occluded", time_ms=20.0, track=3),
        ],
        features=FEATURES,
    )
    shuffled = shuffle_feature_identities(events, seed=3)
    assert [item["time_ms"] for item in shuffled] == [
        item["time_ms"] for item in events
    ]
    assert sorted(
        json.dumps(item["feature_values"], sort_keys=True) for item in shuffled
    ) == sorted(json.dumps(item["feature_values"], sort_keys=True) for item in events)


def test_constant_charge_drive_matches_reference_charge():
    payload = event(
        time_ms=100.0,
        features={"train_present": 1.0, "train_lane": 0, "train_distance": 0.5},
    )
    reference = make_drive([payload])
    target = reference.total_charge_pa_ms()
    assert target > 0
    constant = ConstantChargeDrive(
        reference.stimulated_indices, target, duration_ms=500.0
    )
    assert constant.injected_charge_pa_ms() == pytest.approx(target, rel=1e-12)
    current = np.zeros(len(NODES), dtype=np.float64)
    constant.apply(0, 0.0, current)
    assert current[reference.stimulated_indices].max() > 0
    current = np.zeros(len(NODES), dtype=np.float64)
    constant.apply(0, 500.0, current)
    assert np.allclose(current, 0.0)
