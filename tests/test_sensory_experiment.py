"""Phase 3A protocol expansion, integration with the simulator, and reporting."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_3.run_all import digest_run
from sensory.game_state import ObstacleType
from sensory.sensory_experiment import (
    condition_specs,
    environment_info,
    load_config,
    prepare_setup,
    run_condition,
    write_report,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "sensory_config.yaml"

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


def neuron_params() -> LIFParameters:
    return LIFParameters.from_config(
        {
            "capacitance_pf": 200.0,
            "leak_conductance_ns": 10.0,
            "resting_potential_mv": -65.0,
            "threshold_mv": -50.0,
            "reset_potential_mv": -68.0,
            "refractory_ms": 2.0,
            "initial_potential_mv": -65.0,
        }
    )


def synapse_params() -> SynapseParameters:
    return SynapseParameters(
        weight_transform="linear",
        weight_scale_pa_per_synapse=1.0,
        weight_exponent=0.75,
        tau_exc_ms=5.0,
        tau_inh_ms=8.0,
        delay_ms=1.0,
    )


def short_config() -> dict:
    config = load_config(CONFIG_PATH)
    config["sensory"]["max_recorded_spikes"] = 20000
    return config


def test_protocol_expansion() -> None:
    config = load_config(CONFIG_PATH)
    specs = condition_specs(config)
    names = [spec["name"] for spec in specs]
    assert len(specs) == 23
    assert len(names) == len(set(names))
    assert "single_obstacle_distance_0p90" in names
    assert "combined_train_and_player_center" in names
    assert "sequence_obstacle_approach" in names
    assert "sequence_coin_approach" in names

    sequence = next(
        spec for spec in specs if spec["name"] == "sequence_obstacle_approach"
    )
    assert sequence["duration_ms"] == pytest.approx(800.0)
    assert [start for start, _ in sequence["timeline"]] == [0.0, 200.0, 400.0, 600.0]
    first = sequence["timeline"][0][1].obstacle
    assert first.present and first.obstacle_type is ObstacleType.LOW
    last = sequence["timeline"][-1][1].obstacle
    assert not last.present

    combined = next(
        spec
        for spec in specs
        if spec["name"] == "combined_jumping_train_approach"
    )
    assert "jumping" in combined["active_features"]
    assert "train_present" in combined["active_features"]


def test_setup_sizes_match_mapping(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = short_config()
    setup = prepare_setup(graph, config)
    assert len(setup.encoders) == 14
    for feature, encoder in setup.encoders.items():
        assert encoder.spec.output_size == setup.mapping.size(feature)
    info = setup.info()
    assert info["n_stimulated_neurons"] == setup.mapping.stimulated_indices().size
    assert info["amplitudes_pa"]["player_lane"] == pytest.approx(200.0)


def test_condition_runs_through_the_existing_simulator(graph_factory, tmp_path) -> None:
    graph = make_sensory_graph(graph_factory)
    config = short_config()
    setup = prepare_setup(graph, config)
    spec = dict(condition_specs(config)[0])
    spec["duration_ms"] = 60.0

    run = run_condition(
        setup,
        graph,
        neuron_params(),
        synapse_params(),
        spec,
        seed=11,
    )
    metrics = run["metrics"]
    assert metrics["condition"] == spec["name"]
    assert metrics["duration_ms"] == pytest.approx(60.0)
    assert metrics["n_stimulated_neurons"] == 42
    assert metrics["activity"]["n_spikes"] > 0
    assert metrics["stimulated_spikes_by_feature"]["obstacle_present"] > 0
    assert metrics["simulation"]["wall_runtime_s"] > 0
    assert metrics["memory"]["sensory_arrays_bytes"] > 0
    assert metrics["input"]["max_total_current_pa"] > 0

    digest = digest_run(run)
    assert digest["n_spikes"] == metrics["activity"]["n_spikes"]
    assert len(digest["input_hash"]) == 64
    assert len(digest["spike_hash"]) == 64


def test_condition_is_reproducible(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    config = short_config()
    setup = prepare_setup(graph, config)
    spec = dict(condition_specs(config)[0])
    spec["duration_ms"] = 60.0
    first = run_condition(
        setup, graph, neuron_params(), synapse_params(), spec, seed=5
    )
    second = run_condition(
        setup, graph, neuron_params(), synapse_params(), spec, seed=5
    )
    assert digest_run(first) == digest_run(second)
    assert np.array_equal(
        first["result"].recorder.spike_times_ms,
        second["result"].recorder.spike_times_ms,
    )


def test_report_is_written_from_measured_results(
    graph_factory, tmp_path
) -> None:
    graph = make_sensory_graph(graph_factory)
    config = short_config()
    setup = prepare_setup(graph, config)
    spec = dict(condition_specs(config)[0])
    spec["duration_ms"] = 10.0
    run = run_condition(
        setup, graph, neuron_params(), synapse_params(), spec, seed=3
    )
    summary = {
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "config_path": "configs/sensory_config.yaml",
        "graph": {
            "n_nodes": graph.n_nodes,
            "n_edges": graph.n_edges,
            "n_synapses": graph.n_synapses,
        },
        "setup": setup.info(),
        "seed": 3,
        "mapping": setup.mapping.report(),
        "conditions": [{"metrics": run["metrics"]}],
        "performance": {
            "baseline_runtime_s": 0.1,
            "baseline_steps_per_second": 200.0,
            "sensory_mean_runtime_s": 0.2,
            "sensory_mean_steps_per_second": 100.0,
            "added_runtime_s": 0.1,
            "added_runtime_fraction": 1.0,
            "retained_arrays_mb": 1.0,
            "mean_rss_delta_mb": 0.5,
        },
        "reproducibility": {
            "condition": spec["name"],
            "processes": 2,
            "input_equal": True,
            "spikes_equal": True,
            "spike_count": 10,
        },
    }
    path = write_report(summary, tmp_path / "PHASE_3_REPORT.md")
    text = path.read_text(encoding="utf-8")
    assert "simulated activity only" in text
    assert "No pathway here is anatomically verified" in text
    assert spec["name"] in text
    assert "Reproducibility" in text


def test_environment_info() -> None:
    info = environment_info()
    assert set(info) == {"python", "platform", "numpy", "executable"}
    assert info["numpy"]


def test_summary_json_is_serialisable(graph_factory, tmp_path) -> None:
    graph = make_sensory_graph(graph_factory)
    config = short_config()
    setup = prepare_setup(graph, config)
    spec = dict(condition_specs(config)[0])
    spec["duration_ms"] = 5.0
    run = run_condition(
        setup, graph, neuron_params(), synapse_params(), spec, seed=1
    )
    payload = {
        "metrics": run["metrics"],
        "schedule": run["scheduler"].describe(),
    }
    path = tmp_path / "condition.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["metrics"]["condition"] == spec["name"]
    assert loaded["schedule"]["n_stimulated_neurons"] == 42
