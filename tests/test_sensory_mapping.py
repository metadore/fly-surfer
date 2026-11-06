"""Deterministic, disjoint feature-to-neuron mapping."""

from __future__ import annotations

import numpy as np
import pytest

from sensory.sensory_mapping import SensoryMapping

VOCABULARY = {
    "nt_type": ["ACH", "GABA"],
    "super_class": ["visual_projection", "sensory", "central"],
    "class": ["visual", "mechanosensory", "central"],
    "side": ["left", "center", "right"],
}


def make_sensory_graph(graph_factory):
    n_nodes = 40
    class_codes = np.full(n_nodes, 2, dtype=np.int16)
    class_codes[:24] = 0
    class_codes[24:32] = 1
    side_codes = np.full(n_nodes, 1, dtype=np.int16)
    for code, start in enumerate((0, 8, 16)):
        side_codes[start:start + 8] = code
    super_class_codes = class_codes.copy()
    nt_codes = np.zeros(n_nodes, dtype=np.int16)
    nt_codes[24:] = 1
    return graph_factory(
        n_nodes,
        [],
        nt_codes=nt_codes,
        super_class_codes=super_class_codes,
        class_codes=class_codes,
        side_codes=side_codes,
        vocabulary=VOCABULARY,
    )


def mapping_config(**overrides) -> dict:
    config = {
        "seed": 7,
        "allow_duplicates": False,
        "pools": {
            "visual_left": {"class": ["visual"], "side": ["left"]},
            "visual_center": {"class": ["visual"], "side": ["center"]},
            "visual_right": {"class": ["visual"], "side": ["right"]},
            "visual_any": {"class": ["visual"]},
            "mechanosensory": {"class": ["mechanosensory"]},
        },
        "populations": {
            "lane": {
                "lane_pools": {
                    "left": "visual_left",
                    "center": "visual_center",
                    "right": "visual_right",
                },
                "neurons_per_lane": 2,
            },
            "distance": {"pool": "visual_any", "n_neurons": 5},
            "flag": {"pool": "mechanosensory", "n_neurons": 4},
        },
    }
    config.update(overrides)
    return config


def test_sizes_and_disjoint_allocation(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    mapping = SensoryMapping(graph, mapping_config())
    assert mapping.size("lane") == 6
    assert mapping.size("distance") == 5
    assert mapping.size("flag") == 4
    chunks = [mapping.indices(feature) for feature in mapping.populations]
    union = np.unique(np.concatenate(chunks))
    assert union.size == 15
    assert mapping.stimulated_indices().tolist() == union.tolist()


def test_mapping_is_deterministic(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    first = SensoryMapping(graph, mapping_config())
    second = SensoryMapping(graph, mapping_config())
    for feature in first.populations:
        assert np.array_equal(
            first.indices(feature), second.indices(feature)
        )
    assert np.array_equal(
        first.stimulated_indices(), second.stimulated_indices()
    )


def test_root_ids_exist_in_the_graph(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    mapping = SensoryMapping(graph, mapping_config())
    known = set(int(value) for value in graph.root_ids)
    for population in mapping.populations.values():
        for ids in population.root_ids.values():
            assert set(int(value) for value in ids) <= known


def test_report_states_evidence_and_limitations(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    report = SensoryMapping(graph, mapping_config()).report()
    assert report["n_features"] == 3
    assert report["n_stimulated_neurons"] == 15
    for feature in ("lane", "distance", "flag"):
        payload = report["populations"][feature]
        assert payload["classification"].startswith("experimental input population")
        assert "not an anatomically verified sensory pathway" in payload["classification"]
        assert payload["limitations"]
        assert payload["evidence"]
        assert payload["groups"]
    lane = report["populations"]["lane"]
    assert len(lane["groups"]) == 3
    assert set(lane["groups"]) == {"left", "center", "right"}
    assert lane["plan"]["kind"] == "lane"


def test_unknown_annotation_label_is_rejected(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = mapping_config()
    config["pools"]["visual_any"] = {"class": ["motor"]}
    with pytest.raises(ValueError, match="available labels"):
        SensoryMapping(graph, config)


def test_insufficient_pool_is_rejected(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = mapping_config()
    config["populations"]["lane"]["neurons_per_lane"] = 20
    with pytest.raises(ValueError, match="unused neurons"):
        SensoryMapping(graph, config)


def test_duplicates_are_opt_in(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = mapping_config(allow_duplicates=True)
    config["populations"]["distance"] = {"pool": "visual_any", "n_neurons": 24}
    mapping = SensoryMapping(graph, config)
    assert mapping.size("distance") == 24
    assert mapping.report()["allow_duplicates"] is True


def test_validates_pool_references_and_plan_shape(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = mapping_config()
    config["populations"]["flag"]["pool"] = "missing"
    with pytest.raises(ValueError, match="unknown pool"):
        SensoryMapping(graph, config)

    config = mapping_config()
    config["populations"]["lane"]["neurons_per_lane"] = 0
    with pytest.raises(ValueError, match="neurons_per_lane"):
        SensoryMapping(graph, config)
