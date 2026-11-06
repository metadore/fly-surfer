"""Phase 3A.5 calibration conditions, metrics and selection rules."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_3_5 import calibration
from sensory.sensory_experiment import load_config, run_condition

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


def short_base_config() -> dict:
    config = load_config(CONFIG_PATH)
    config["sensory"]["max_recorded_spikes"] = 20000
    return config


def test_stage_expansion_and_unique_names() -> None:
    cal = calibration.load_calibration_config()
    assert cal["feature"] == "obstacle_distance"
    assert cal["distances"] == [0.15, 0.55, 0.90]
    assert len(cal["mapping_seeds"]) == 3

    amplitude = calibration.amplitude_groups(cal)
    tuning = calibration.tuning_groups(cal, [175.0, 200.0])
    population = calibration.population_groups(cal, 175.0, 0.20)
    seeds = calibration.seed_groups(cal, 175.0, 0.20, 12)
    additivity = calibration.additivity_groups(cal, 175.0, 0.20, 12, 7)
    transition = calibration.transition_groups(cal, 175.0, 0.20, 12, 7)
    baseline = calibration.baseline_groups(cal, 175.0, 0.20, 12)
    controls = calibration.control_groups(cal)

    assert len(amplitude) == 8
    assert sum(len(group["specs"]) for group in amplitude) == 24
    assert len(tuning) == 10
    assert sum(len(group["specs"]) for group in tuning) == 30
    assert len(population) == 5
    assert sum(len(group["specs"]) for group in population) == 15
    assert len(seeds) == 3
    assert sum(len(group["specs"]) for group in seeds) == 9
    assert sum(len(group["specs"]) for group in additivity) == 3
    assert sum(len(group["specs"]) for group in transition) == 5
    assert sum(len(group["specs"]) for group in baseline) == 9
    assert sum(len(group["specs"]) for group in controls) == 4

    names = [
        spec["name"]
        for groups in (
            amplitude,
            tuning,
            population,
            seeds,
            additivity,
            transition,
            baseline,
            controls,
        )
        for group in groups
        for spec in group["specs"]
    ]
    assert len(names) == len(set(names))
    assert "a5_1_amp200_dist0p15" in names
    assert "a5_7_transition0p00" in names


def test_build_setup_changes_only_requested_factors(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    base = short_base_config()
    setup = calibration.build_setup(
        graph,
        base,
        amplitude_pa=250.0,
        sigma_fraction=0.10,
        population_size=8,
        baseline=0.10,
        mapping_seed=11,
        transition_ms=25.0,
    )
    encoder = setup.encoders["obstacle_distance"]
    assert encoder.spec.sigma_fraction == pytest.approx(0.10)
    assert encoder.spec.n_neurons == 8
    assert setup.mapping.size("obstacle_distance") == 8
    assert setup.amplitudes["obstacle_distance"] == pytest.approx(250.0)
    assert setup.mapping.seed == 11
    assert setup.transition_ms == pytest.approx(25.0)
    assert setup.config["features"]["obstacle_distance"]["baseline"] == pytest.approx(
        0.10
    )
    assert base["features"]["obstacle_distance"]["current_pa"] == pytest.approx(
        200.0
    )


def test_group_analysis_marks_flat_and_ordered_responses() -> None:
    def row(distance: float, spikes: int) -> dict:
        return {
            "factors": {"distance": distance},
            "calibration": {
                "by_feature": {
                    "obstacle_distance": {
                        "spikes": spikes,
                        "spikes_per_neuron": spikes / 12,
                        "recruitment_fraction": min(1.0, spikes / 12),
                    }
                }
            },
        }

    ordered = calibration.group_analysis(
        [row(0.15, 12), row(0.55, 8), row(0.90, 3)],
        "obstacle_distance",
    )
    assert ordered["ordered"] is True
    assert ordered["weakly_ordered"] is True
    assert ordered["direction"] == "decreasing_with_distance"
    assert ordered["d_prime_proxy"] > 0
    assert ordered["dynamic_range"] == 9

    flat = calibration.group_analysis(
        [row(0.15, 5), row(0.55, 5), row(0.90, 5)],
        "obstacle_distance",
    )
    assert flat["ordered"] is False
    assert flat["weakly_ordered"] is True
    assert flat["direction"] == "flat"
    assert flat["d_prime_proxy"] == 0.0


def test_selection_prefers_ordered_group_and_falls_back() -> None:
    def group(amplitude: float, counts: list[int]) -> dict:
        analysis = calibration.group_analysis(
            [
                {
                    "factors": {"distance": distance},
                    "calibration": {
                        "by_feature": {
                            "obstacle_distance": {
                                "spikes": count,
                                "spikes_per_neuron": count / 12,
                                "recruitment_fraction": min(1.0, count / 12),
                            }
                        }
                    },
                }
                for distance, count in zip((0.15, 0.55, 0.90), counts)
            ],
            "obstacle_distance",
        )
        return {
            "parameters": {"amplitude_pa": amplitude},
            "analysis": analysis,
            "conditions": [],
        }

    stage = {
        "groups": [
            group(175.0, [12, 12, 12]),
            group(200.0, [12, 8, 3]),
        ]
    }
    selected, ranked, reason = calibration.select_amplitude(stage, 200.0)
    assert selected == 200.0
    assert reason == "ordered"
    assert len(ranked) == 1

    flat_stage = {"groups": [group(200.0, [5, 5, 5])]}
    selected, ranked, reason = calibration.select_amplitude(flat_stage, 200.0)
    assert selected == 200.0
    assert ranked == []
    assert reason.startswith("fallback")


def test_poisson_d_prime_and_spearman() -> None:
    assert calibration.poisson_d_prime(0, 0) == 0.0
    assert calibration.poisson_d_prime(0, 4) == pytest.approx(2.828427, rel=1e-5)
    assert calibration.spearman([0.15, 0.55, 0.90], [12, 8, 3]) < -0.99
    assert calibration.spearman([0.15, 0.55, 0.90], [1, 1, 1]) == 0.0


def test_seed_and_additivity_summaries() -> None:
    def seed_group(seed: int, counts: list[int]) -> dict:
        analysis = calibration.group_analysis(
            [
                {
                    "factors": {"distance": distance},
                    "calibration": {
                        "by_feature": {
                            "obstacle_distance": {
                                "spikes": count,
                                "spikes_per_neuron": count / 12,
                                "recruitment_fraction": min(1.0, count / 12),
                            }
                        }
                    },
                }
                for distance, count in zip((0.15, 0.55, 0.90), counts)
            ],
            "obstacle_distance",
        )
        return {"parameters": {"mapping_seed": seed}, "analysis": analysis, "conditions": []}

    seed_stage = {
        "groups": [
            seed_group(1, [12, 8, 3]),
            seed_group(2, [12, 9, 4]),
            seed_group(3, [1, 1, 1]),
        ]
    }
    summary = calibration.seed_summary(seed_stage, "obstacle_distance")
    assert summary["n_ordered_seeds"] == 2
    assert summary["passed"] is True

    def add_row(kind: str, obstacle: int, coin: int) -> dict:
        return {
            "factors": {"kind": kind},
            "calibration": {
                "total_feature_spikes": obstacle + coin,
                "by_feature": {
                    "obstacle_distance": {"spikes": obstacle},
                    "coin_distance": {"spikes": coin},
                },
            },
        }

    additivity = calibration.additivity_summary(
        {
            "groups": [
                {
                    "conditions": [
                        add_row("obstacle", 10, 0),
                        add_row("coin", 0, 6),
                        add_row("both", 8, 4),
                    ]
                }
            ]
        }
    )
    assert additivity["expected_additive"] == 16
    assert additivity["additivity_index"] == pytest.approx(-4 / 16)


def test_condition_overrides_reach_the_scheduler(graph_factory) -> None:
    graph = make_sensory_graph(graph_factory)
    base = short_base_config()
    setup = calibration.build_setup(
        graph,
        base,
        amplitude_pa=250.0,
        sigma_fraction=0.10,
        population_size=6,
        transition_ms=25.0,
    )
    spec = calibration.amplitude_groups(calibration.load_calibration_config())[0][
        "specs"
    ][0]
    spec = dict(spec)
    spec["duration_ms"] = 10.0
    run = run_condition(
        setup,
        graph,
        neuron_params(),
        synapse_params(),
        spec,
        seed=3,
    )
    assert run["scheduler"].transition_ms == pytest.approx(25.0)
    assert run["scheduler"].describe()["features"]["obstacle_distance"][
        "current_pa"
    ] == pytest.approx(250.0)
    metrics = calibration.extract_calibration_metrics(
        run, setup, spec["active_features"]
    )
    assert metrics["by_feature"]["obstacle_distance"]["n_neurons"] == 6
    assert (
        metrics["by_feature"]["obstacle_distance"]["spikes"]
        <= run["metrics"]["activity"]["n_spikes"]
    )


def test_distance_analysis_requires_the_calibrated_feature() -> None:
    from experiments.phase_3_5 import run_all

    coin_row = {
        "factors": {"kind": "coin_control", "distance": 0.30},
        "calibration": {"by_feature": {"coin_distance": {"spikes": 4}}},
    }
    obstacle_row = {
        "factors": {"distance": 0.55},
        "calibration": {"by_feature": {"obstacle_distance": {"spikes": 6}}},
    }
    assert run_all._analysable([obstacle_row], "obstacle_distance")
    assert not run_all._analysable([coin_row], "obstacle_distance")
    assert not run_all._analysable([], "obstacle_distance")
