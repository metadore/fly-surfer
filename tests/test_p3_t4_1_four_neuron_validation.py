"""Focused tests for the P3-T4.1 four-neuron validation experiment."""

from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from brain.connectome_loader import load_connectome
from experiments.phase_3c import p3_t4_1_four_neuron_validation as module
from sensory.sensory_experiment import load_config


@pytest.fixture(scope="module")
def graph():
    settings = module.load_yaml(module.SIMULATION_CONFIG)
    return load_connectome(module.PROJECT_ROOT / settings["connectome"]["path"])


@pytest.fixture(scope="module")
def base_config():
    return load_config(module.SENSORY_CONFIG)


@pytest.fixture(scope="module")
def protocol():
    return module.load_protocol()


def test_protocol_matches_frozen_constants(protocol):
    assert protocol["phase"] == "P3-T4.1"
    assert protocol["seeds"]["mapping"] == module.EXPECTED["seeds"]
    assert protocol["protocol"]["active_features"] == [module.FEATURE]
    assert protocol["analysis"]["dprime_threshold"] == 1.0


def test_protocol_rejects_changed_threshold(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["analysis"]["dprime_threshold"] = 0.5
    path = tmp_path / "changed.yaml"
    module.yaml.safe_dump(changed, path.open("w", encoding="utf-8"))
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_configs_differ_only_in_population_size(graph, base_config, protocol):
    for seed in protocol["seeds"]["mapping"]:
        block = module.equivalence(graph, base_config, protocol, seed)
        assert block["only_intended_fields_differ"], block["differing_paths"]
        assert block["differing_paths"] == [
            ["features", "obstacle_distance", "n_neurons"],
            ["mapping", "populations", "obstacle_distance", "n_neurons"],
        ]


def test_four_is_prefix_of_twelve_for_every_seed(graph, base_config, protocol):
    for seed in protocol["seeds"]["mapping"]:
        four, _ = module.build_setup(graph, base_config, 4, seed)
        twelve, _ = module.build_setup(graph, base_config, 12, seed)
        four_indices = module.population_indices(four)
        twelve_indices = module.population_indices(twelve)
        assert four_indices.tolist() == twelve_indices[:4].tolist()
        assert four.encoders[module.FEATURE].preferred.tolist() == pytest.approx(
            [0.0, 1 / 3, 2 / 3, 1.0]
        )
        assert twelve.encoders[module.FEATURE].preferred.size == 12


def test_preflight_matches_p3_t4_sorted_indices(graph, base_config, protocol):
    block = module.population_evidence(graph, base_config, protocol, 20261104)
    recorded = json.loads(
        (
            module.RESULTS_DIR / "p3_t4_calibration_discrepancy.json"
        ).read_text(encoding="utf-8")
    )["mapping"]["comparison"]
    assert block["P4"]["sorted_indices"] == recorded["indices_4"]
    assert block["P12"]["sorted_indices"] == recorded["indices_12"]


def test_only_distance_feature_receives_current(graph, base_config, protocol):
    setup, _ = module.build_setup(graph, base_config, 4, 20261104)
    times = module.frame_times(protocol["protocol"]["frame_interval_ms"])
    frames = module.make_frames(module.constant_timeline(0.55, times), 50.0)
    scheduler = module.build_scheduler(setup, frames)
    values = scheduler._frame_values[0]
    distance_slice = scheduler._slices[module.FEATURE]
    assert float(values[distance_slice].sum()) > 0.0
    for feature, slc in scheduler._slices.items():
        if feature == module.FEATURE:
            continue
        assert float(values[slc].sum()) == 0.0


def test_restricted_scheduler_drives_only_the_four_cells(graph, base_config, protocol):
    twelve, _ = module.build_setup(graph, base_config, 12, 20261104)
    four, _ = module.build_setup(graph, base_config, 4, 20261104)
    subset = module.population_indices(four)
    times = module.frame_times(protocol["protocol"]["frame_interval_ms"])
    frames = module.make_frames(module.constant_timeline(0.55, times), 50.0)
    scheduler = module.build_scheduler(twelve, frames, subset)
    assert sorted(scheduler.stimulated_indices.tolist()) == sorted(subset.tolist())
    values = scheduler._frame_values[0]
    unrestricted = module.build_scheduler(twelve, frames)._frame_values[0]
    outside = np.ones(values.size, dtype=bool)
    outside[scheduler._keep] = False
    assert float(values[outside].sum()) == 0.0
    assert float(unrestricted[outside].sum()) > 0.0


def test_condition_matrix(protocol):
    specs = module.condition_specs(protocol)
    names = [spec["name"] for spec in specs]
    assert names == [
        "constant_0.15",
        "constant_0.55",
        "constant_0.90",
        "approach",
        "retreat",
        "frame_rate_200",
        "frame_rate_100",
        "control_no_input",
    ]
    by_name = {spec["name"]: spec for spec in specs}
    assert by_name["approach"]["interval_ms"] == 50.0
    assert by_name["frame_rate_100"]["interval_ms"] == 100.0
    assert len(by_name["frame_rate_100"]["timeline"]) == 7
    assert len(by_name["frame_rate_200"]["timeline"]) == 4
    assert len(by_name["approach"]["timeline"]) == 13
    control_state = by_name["control_no_input"]["timeline"][0][1]
    assert control_state.obstacle is None


def test_dprime_and_cosine_helpers():
    identical = [1, 2, 3, 4]
    result = module.dprime(identical, identical, 1.0)
    assert result["difference"] == 0.0
    assert result["separated"] is False
    separated = module.dprime([0, 0, 0, 0], [5, 5, 5, 5], 1.0)
    assert separated["separated"] is True
    assert separated["zero_variance"] is True
    assert module.cosine_distance([1, 2, 3], [1, 2, 3]) == pytest.approx(0.0)


def _synthetic_runs(stim_counts, network_counts, approach_profile, retreat_profile):
    names = [
        "constant_0.15",
        "constant_0.55",
        "constant_0.90",
        "approach",
        "retreat",
        "frame_rate_200",
        "frame_rate_100",
        "control_no_input",
    ]
    runs = {}
    for index, name in enumerate(names):
        runs[name] = {
            "n_spikes_total": network_counts[index],
            "n_spikes_stimulated": stim_counts[index],
            "n_spikes_outside": network_counts[index] - stim_counts[index],
            "profile_stimulated": (
                approach_profile if name == "approach" else retreat_profile
            ),
            "profile_network": (
                approach_profile if name == "approach" else retreat_profile
            ),
            "first_stimulated_spike_latency_ms": 1.0,
            "median_stimulated_first_latency_ms": 2.0,
            "voltage": [],
            "n_frames": 13,
            "current_trace_stimulated": [[0.0], [1.0]],
            "current_trace_network_rms": [0.0, 1.0],
            "digest": name,
        }
    return runs


def test_analysis_detects_ordering_and_separation(protocol):
    rising = [2, 6, 7, 5, 5, 5, 5, 0]
    network = [10, 20, 30, 15, 15, 15, 15, 0]
    separated = [0, 0, 10, 0] * 3
    flat = [10, 10, 10, 10] * 3
    runs = _synthetic_runs(rising, network, separated, flat)
    analysis = module.analyse_seed(protocol, runs)
    assert analysis["ordering_stimulated"]["ordered"] is True
    assert analysis["ordering_stimulated"]["strictly_increasing"] is True
    assert analysis["direction"]["stimulated"]["separated"] is True


def test_assess_verdict_mapping(protocol):
    ordering = [2, 6, 7, 5, 5, 5, 5, 0]
    network = [10, 20, 30, 15, 15, 15, 15, 0]
    approach = [0, 1, 1, 0] * 3
    retreat = [0, 0, 1, 1] * 3
    seeds = [str(seed) for seed in protocol["seeds"]["mapping"]]
    results = {
        name: {
            seed: {
                "conditions": _synthetic_runs(
                    ordering, network, approach, retreat
                )
            }
            for seed in seeds
        }
        for name in ("P4", "P12", "P12S")
    }
    analysis = {
        name: {
            seed: module.analyse_seed(
                protocol, results[name][seed]["conditions"]
            )
            for seed in seeds
        }
        for name in results
    }
    determinism = {
        name: {"identical": True} for name in ("P4", "P12", "P12S")
    }
    protected = {"README.md": {"expected": "x", "actual": "x"}}
    comparisons_block = module.comparisons(protocol, results)
    hypotheses_block = module.hypotheses(protocol, analysis)
    assessment = module.assess(
        protocol, results, analysis, determinism,
        [{"only_intended_fields_differ": True}], protected,
        comparisons_block, hypotheses_block,
    )
    assert assessment["verdict"] == "PASS"
    assert assessment["execution_checks"]["determinism"] is True
    broken = module.assess(
        protocol, results, analysis,
        {"P4": {"identical": False}, "P12": {"identical": True},
         "P12S": {"identical": True}},
        [{"only_intended_fields_differ": True}], protected,
        comparisons_block, hypotheses_block,
    )
    assert broken["verdict"] == "BLOCKED"


def test_preregistration_and_protocol_hashes_recorded():
    assert module.CONFIG_PATH.exists()
    assert module.PREREG_PATH.exists()
    assert len(module.sha256(module.CONFIG_PATH)) == 64
    assert len(module.sha256(module.PREREG_PATH)) == 64
