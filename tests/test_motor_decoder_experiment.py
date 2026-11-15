"""Phase 4F experiment helpers: pool targeting, spike generation, config."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from motor.motor_decoder import DecoderConfig
from motor.populations import PopulationOptions
from tests.test_motor_decoder import make_populations

SCRIPT = PROJECT_ROOT / "experiments" / "phase_4f" / "run_decoder_experiment.py"
SPEC = importlib.util.spec_from_file_location("phase_4f_experiment", SCRIPT)
EXPERIMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPERIMENT)

CONFIG_PATH = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
ARTIFACTS_PRESENT = (PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_graph_t5.npz").is_file()


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_configuration_sections_are_valid() -> None:
    config = load_config()
    assert set(config) == {"populations", "decoder", "experiment"}
    decoder = DecoderConfig.from_config(config["decoder"])
    assert decoder.window_ms == pytest.approx(50.0)
    assert decoder.priority == ("LEFT", "RIGHT", "JUMP")
    assert decoder.activation_threshold > decoder.release_threshold
    options = PopulationOptions(
        leg_effectors=tuple(config["populations"]["leg_effectors"]),
        jump_target=config["populations"]["jump_target"],
        jump_membership_in_leg_pools=config["populations"][
            "jump_membership_in_leg_pools"
        ],
    )
    assert options.leg_effectors == ("front_leg", "middle_leg", "hind_leg")
    experiment = config["experiment"]
    assert experiment["drive_jitter_pa"] == 0.0
    assert experiment["jitter_sensitivity_pa"] > 0.0
    assert experiment["decode_end_ms"] > experiment["decode_start_ms"]
    assert experiment["drive_end_ms"] > experiment["drive_start_ms"]
    assert all(value > 0 for value in experiment["current_amplitudes_pa"])


def test_scenario_targets_select_by_ascending_node_index() -> None:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    targets = EXPERIMENT.scenario_targets(populations, {"LEFT": 0.3})
    assert targets["LEFT"].tolist() == [0, 1, 2]
    weak = EXPERIMENT.scenario_targets(populations, {"LEFT": 0.01})
    assert weak["LEFT"].tolist() == [0]
    with pytest.raises(ValueError, match="unknown scenario population"):
        EXPERIMENT.scenario_targets(populations, {"ROLL": 0.5})
    with pytest.raises(ValueError, match="must be in"):
        EXPERIMENT.scenario_targets(populations, {"LEFT": 0.0})


def test_generate_spikes_respects_rheobase() -> None:
    driven = np.array([0, 1, 2, 3], dtype=np.int64)
    silent = EXPERIMENT.generate_spikes(
        driven,
        current_pa=100.0,
        dt_ms=0.5,
        duration_ms=100.0,
        drive_start_ms=10.0,
        drive_end_ms=80.0,
        jitter_pa=0.0,
        seed=1,
    )
    assert silent[0].size == 0
    firing = EXPERIMENT.generate_spikes(
        driven,
        current_pa=200.0,
        dt_ms=0.5,
        duration_ms=100.0,
        drive_start_ms=10.0,
        drive_end_ms=80.0,
        jitter_pa=0.0,
        seed=1,
    )
    assert firing[0].size > 0
    assert set(np.unique(firing[1]).tolist()) == {0, 1, 2, 3}
    assert firing[0].min() > 10.0


def test_generate_spikes_is_deterministic_with_seeded_jitter() -> None:
    driven = np.arange(12, dtype=np.int64)
    kwargs = dict(
        current_pa=180.0,
        dt_ms=0.5,
        duration_ms=120.0,
        drive_start_ms=20.0,
        drive_end_ms=100.0,
        jitter_pa=25.0,
        seed=20261108,
    )
    first = EXPERIMENT.generate_spikes(driven, **kwargs)
    second = EXPERIMENT.generate_spikes(driven, **kwargs)
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])


def test_generate_spikes_with_no_driven_neurons_is_empty() -> None:
    times, indices = EXPERIMENT.generate_spikes(
        np.empty(0, dtype=np.int64),
        current_pa=200.0,
        dt_ms=0.5,
        duration_ms=50.0,
        drive_start_ms=10.0,
        drive_end_ms=40.0,
        jitter_pa=0.0,
        seed=0,
    )
    assert times.size == 0 and indices.size == 0


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="BANC graph is absent")
def test_simulator_probe_records_the_interface_limitation() -> None:
    probe = EXPERIMENT.probe_simulator(EXPERIMENT.GRAPH_PATHS[5])
    assert probe["attempted"] is True
    assert probe["failed"] is True
    assert probe["error_type"] == "AttributeError"
    assert probe["missing_graph_fields"] == ["vocabulary", "nt_code"]
    assert "transmitter" in probe["conclusion"]
    assert "sign policy" in probe["conclusion"]
