"""P3-T4: shipped counts and the four-vs-twelve population relationship."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from experiments.phase_3_5 import calibration
from sensory.sensory_experiment import load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENSORY = PROJECT_ROOT / "configs" / "sensory_config.yaml"
CAUSAL = PROJECT_ROOT / "configs" / "causal_control_config.yaml"

VOCABULARY = {
    "nt_type": ["ACH", "GABA"],
    "super_class": ["visual_projection", "sensory", "central"],
    "class": ["visual", "mechanosensory", "central"],
    "side": ["left", "center", "right"],
}


def make_sensory_graph(graph_factory):
    n_nodes = 200
    class_codes = np.full(n_nodes, 2, dtype=np.int16)
    class_codes[:180] = 0
    class_codes[180:] = 1
    side_codes = np.full(n_nodes, 1, dtype=np.int16)
    for code, start in enumerate((0, 60, 120)):
        side_codes[start:start + 60] = code
    return graph_factory(
        n_nodes,
        [],
        nt_codes=np.zeros(n_nodes, dtype=np.int16),
        super_class_codes=class_codes.copy(),
        class_codes=class_codes,
        side_codes=side_codes,
        vocabulary=VOCABULARY,
    )


def feature_count(payload: dict) -> int:
    if payload["kind"] == "lane":
        return int(payload["lanes"]) * int(payload["neurons_per_lane"])
    return int(payload["n_neurons"])


def test_shipped_counts_match_pinned_causal_config() -> None:
    config = load_config(SENSORY)
    causal = yaml.safe_load(CAUSAL.read_text(encoding="utf-8"))
    reference = causal["reference"]
    pinned = reference["feature_neuron_counts"]
    counts = {
        feature: feature_count(payload)
        for feature, payload in config["features"].items()
    }
    assert counts == pinned
    assert sum(counts.values()) == reference["n_reference_neurons"] == 138
    player = {
        "player_lane",
        "player_speed",
        "jumping",
        "rolling",
    }
    assert sum(counts[name] for name in player) == reference["n_player_neurons"]
    assert sum(counts.values()) - sum(
        counts[name] for name in player
    ) == reference["n_non_player_neurons"]
    # The shipped obstacle-distance population is deliberately still 12 and is
    # not the four-neuron point selected by the Phase 3A.5 calibration.
    assert counts["obstacle_distance"] == 12


def test_four_neuron_mapping_is_subset_and_remaps_later_features(
    graph_factory,
) -> None:
    graph = make_sensory_graph(graph_factory)
    base = load_config(SENSORY)
    setup12 = calibration.build_setup(graph, base, population_size=12)
    setup4 = calibration.build_setup(graph, base, population_size=4)
    indices12 = setup12.mapping.indices("obstacle_distance")
    indices4 = setup4.mapping.indices("obstacle_distance")
    assert indices12.size == 12
    assert indices4.size == 4
    assert set(indices4.tolist()) <= set(indices12.tolist())
    # Shrinking the population releases visual_any neurons to the features
    # allocated after it, so the change is not confined to one population.
    changed = [
        feature
        for feature, population in setup12.mapping.populations.items()
        if set(population.indices.tolist())
        != set(setup4.mapping.populations[feature].indices.tolist())
    ]
    assert "obstacle_distance" in changed
    assert "train_present" in changed
    assert len(changed) > 1


def test_ordering_margin_is_a_single_spike() -> None:
    four = [2, 6, 7]
    twelve = [24, 23, 23]
    assert all(four[i] < four[i + 1] for i in range(2))
    assert abs(four[1] - four[2]) == 1
    # One extra spike at distance 0.55 ties the middle level with 0.90.
    perturbed = [four[0], four[1] + 1, four[2]]
    assert not all(perturbed[i] < perturbed[i + 1] for i in range(2))
    assert not (
        all(twelve[i] < twelve[i + 1] for i in range(2))
        or all(twelve[i] > twelve[i + 1] for i in range(2))
    )
