"""Phase 5E: controlled task, deterministic seeds and the eta = 0 contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from brain.banc_simulator import BancSimulator
from experiments.phase_5 import controlled_task as runner
from plasticity.config import load_plasticity_config
from plasticity.diagnostics import spike_hash
from plasticity.plastic_simulator import PlasticSimulator
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.tasks import (
    CueActionSchedule,
    TargetResponseController,
    TaskConfig,
    build_task_substrate,
    derive_seed,
    load_task_config,
)
from plasticity.weights import WeightState

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity_task.yaml"
PLASTICITY_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"


# ---------------------------------------------------------------------------
# configuration and substrate
# ---------------------------------------------------------------------------


def test_task_config_defaults():
    config = TaskConfig()
    assert config.n_nodes == 36
    assert config.n_steps == 48
    assert config.deadline_step == 27
    described = config.describe()
    assert described["n_cues"] == 4
    assert described["n_nodes"] == 36
    assert described["success_rule"].startswith("the designated action")


@pytest.mark.parametrize(
    "overrides",
    [
        {"response_deadline_ms": 25.0},
        {"response_deadline_ms": 0.0},
        {"connectivity": "sparse"},
        {"pulse_onset_max_ms": 19.0},
        {"action_prime_end_ms": 14.0},
        {"min_count": 6, "max_count": 5},
        {"n_cues": 1},
    ],
)
def test_task_config_rejects_invalid_values(overrides):
    with pytest.raises(ValueError):
        TaskConfig(**overrides)


def test_task_config_from_mapping():
    config = TaskConfig.from_config({"n_cues": 3, "cue_neurons": 4})
    assert config.n_cues == 3
    assert config.cue_neurons == 4
    assert config.action_neurons == 1


def test_complete_substrate_is_deterministic_and_fully_connected():
    config = TaskConfig()
    first = build_task_substrate(config, seed=7)
    second = build_task_substrate(config, seed=7)
    assert first.graph.n_nodes == 36
    assert first.graph.n_edges == 128
    assert int(first.graph.edge_weight.sum()) >= 128
    assert int(first.graph.edge_weight.max()) <= config.max_count
    assert np.array_equal(first.graph.edge_src, second.graph.edge_src)
    assert np.array_equal(first.graph.edge_dst, second.graph.edge_dst)
    assert np.array_equal(first.graph.edge_weight, second.graph.edge_weight)
    assert np.array_equal(
        first.policy.edge_exc_weight, second.policy.edge_exc_weight
    )
    assert np.all(first.policy.edge_exc_weight > 0)
    assert not np.any(first.policy.edge_inh_weight)
    assert sum(index.size for index in first.cue_indices) == 32
    assert sum(index.size for index in first.action_indices) == 4
    descriptor = first.describe()
    assert descriptor["graph"]["n_edges"] == 128
    assert descriptor["populations"]["mapping"] == "cue i -> action i"


def test_random_substrate_is_reproducible_and_sparser():
    complete = build_task_substrate(TaskConfig(), seed=11)
    config = TaskConfig(connectivity="random", edge_probability=0.5)
    first = build_task_substrate(config, seed=11)
    second = build_task_substrate(config, seed=11)
    assert first.graph.n_edges < complete.graph.n_edges
    assert np.array_equal(first.graph.edge_src, second.graph.edge_src)
    assert np.array_equal(first.graph.edge_dst, second.graph.edge_dst)
    assert np.array_equal(first.graph.edge_weight, second.graph.edge_weight)
    assert np.all(first.graph.edge_weight >= 1)


def test_derive_seed_separates_streams():
    assert derive_seed(5, 1, 2, 3) == derive_seed(5, 1, 2, 3)
    assert derive_seed(5, 1, 2, 3) != derive_seed(5, 1, 3, 3)
    assert derive_seed(5, 1, 2, 3) != derive_seed(5, 1, 2, 4)
    assert derive_seed(6, 1, 2, 3) != derive_seed(5, 1, 2, 3)
    assert derive_seed(5, 1, 2, 3) != derive_seed(5, 2, 2, 3)


def test_seed_pools_are_disjoint():
    settings = {
        "train_episodes": 8,
        "eval_episodes": 4,
        "replicates": 2,
        "master_seed": 20261114,
    }
    pools = runner.seed_pools(settings)
    assert pools["disjoint_train_eval"]
    assert pools["unique_train"] and pools["unique_eval"]
    assert pools["train_overlap_count"] == 0


def test_load_task_config():
    config, settings = load_task_config(TASK_CONFIG_PATH)
    assert config.n_cues == 4
    assert settings["train_episodes"] == 160
    assert settings["eval_episodes"] == 40
    assert settings["replicates"] == 3
    assert settings["eta"] == 1.0
    assert settings["eval_checkpoints"] == [0, 40, 80, 120, 160]
    assert settings["checkpoint_condition"] == "B"


def test_load_task_config_rejects_bad_checkpoints(tmp_path):
    raw = yaml.safe_load(TASK_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["experiment"]["eval_checkpoints"] = [10, 40, 160]
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_task_config(path)


# ---------------------------------------------------------------------------
# stimulus schedule and outcome controller
# ---------------------------------------------------------------------------


def test_schedule_applies_cue_prime_and_hold_currents():
    schedule = CueActionSchedule(
        cue_indices=[0, 1],
        action_indices=[4, 5],
        onsets_ms=[1.0, 3.0],
        pulse_duration_ms=2.0,
        cue_current_pa=100.0,
        action_prime_current_pa=50.0,
        action_prime_end_ms=2.0,
        action_background_pa=10.0,
        duration_ms=10.0,
    )
    current = np.zeros(6)
    schedule.apply(0, 0.5, current)
    assert current.tolist() == [0.0, 0.0, 0.0, 0.0, 50.0, 50.0]
    current = np.zeros(6)
    schedule.apply(3, 1.5, current)
    assert current[0] == 100.0 and current[1] == 0.0
    assert current[4] == 50.0 and current[5] == 50.0
    current = np.zeros(6)
    schedule.apply(7, 3.5, current)
    assert current[0] == 0.0 and current[1] == 100.0
    assert current[4] == 10.0 and current[5] == 10.0
    current = np.zeros(6)
    schedule.apply(11, 5.5, current)
    assert current[:4].sum() == 0.0
    assert current[4] == 10.0 and current[5] == 10.0
    described = schedule.describe()
    assert described["n_cue_neurons"] == 2
    assert described["onsets_ms"] == [1.0, 3.0]


def test_controller_rewards_only_the_designated_action_before_deadline():
    controller = TargetResponseController(
        [[0], [1]],
        target_action=1,
        deadline_step=10,
        reward_correct=1.0,
        reward_incorrect=0.0,
    )
    assert controller(2, 1.0, np.array([0, 3])) is None
    assert controller.first_action == 0
    assert controller(4, 2.0, np.array([1])) == pytest.approx(1.0)
    outcome = controller.outcome()
    assert outcome["hit"] and not outcome["timed_out"]
    assert outcome["correct_action"] == 1
    assert outcome["chosen_action"] == 0
    assert outcome["response_step"] == 4
    assert outcome["response_ms"] == pytest.approx(2.0)
    assert outcome["reward"] == pytest.approx(1.0)
    # A second target spike must not produce a second reward.
    assert controller(5, 2.5, np.array([1])) is None


def test_controller_times_out_with_the_declared_miss_reward():
    controller = TargetResponseController(
        [[0], [1]],
        target_action=1,
        deadline_step=10,
        reward_correct=1.0,
        reward_incorrect=-0.5,
    )
    for step in range(10):
        assert controller(step, step * 0.5, np.empty(0, dtype=np.int64)) is None
    assert controller(10, 5.0, np.empty(0, dtype=np.int64)) == pytest.approx(-0.5)
    outcome = controller.outcome()
    assert outcome["timed_out"] and not outcome["hit"]
    assert outcome["response_step"] is None
    # A late target spike cannot turn the miss into a hit.
    assert controller(11, 5.5, np.array([1])) is None
    assert not controller.outcome()["hit"]


def test_controller_shuffled_reward_keeps_the_spike_timing():
    rewards = iter([-1.0, -1.0])
    controller = TargetResponseController(
        [[0], [1]],
        target_action=0,
        deadline_step=10,
        reward_correct=1.0,
        reward_incorrect=0.0,
        reward_shuffler=lambda: next(rewards),
    )
    assert controller(3, 1.5, np.array([0])) == pytest.approx(-1.0)
    assert controller.response_step == 3
    assert controller.outcome()["hit"]


# ---------------------------------------------------------------------------
# simulator contracts on the task substrate
# ---------------------------------------------------------------------------


def _task_schedule(substrate, config, cue=0, onsets=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 1.5, 2.5)):
    return runner.make_schedule(substrate, config, cue, np.asarray(onsets))


def test_eta_zero_matches_the_fixed_weight_simulator_on_the_task():
    config = TaskConfig()
    substrate = build_task_substrate(config, seed=13)
    schedule = _task_schedule(substrate, config)
    common = {
        "dt_ms": config.dt_ms,
        "duration_ms": config.duration_ms,
        "seed": 99,
        "noise_std_pa": config.noise_std_pa,
        "input_schedule": schedule,
        "tau_exc_ms": config.tau_exc_ms,
        "tau_inh_ms": config.tau_inh_ms,
        "delay_ms": config.delay_ms,
        "max_recorded_spikes": 5_000,
    }
    fixed = BancSimulator(substrate.graph, substrate.policy, **common).run()
    state = WeightState(substrate.graph, substrate.policy)
    plastic_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)
    plastic = PlasticSimulator(
        substrate.graph,
        substrate.policy,
        weight_state=state,
        rule=ThreeFactorRule(RuleConfig(eta=0.0), state),
        trace_config=plastic_config.traces,
        enable_traces=True,
        **common,
    ).run()
    assert fixed.recorder.n_spikes > 0
    assert spike_hash(fixed.recorder) == plastic.spike_hash
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)


def test_plastic_condition_changes_weights_while_controls_do_not():
    config = TaskConfig()
    substrate = build_task_substrate(config, seed=20261114)
    plastic_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)
    settings = {
        "train_episodes": 8,
        "eval_episodes": 4,
        "replicates": 1,
        "master_seed": 20261114,
        "eta": 1.0,
        "criterion_window": 4,
        "criterion_success": 0.75,
        "eval_checkpoints": [0, 4, 8],
        "checkpoint_condition": "B",
    }
    pools = runner.seed_pools(settings)
    plastic = runner.run_spiking_condition(
        "B",
        substrate,
        plastic_config,
        config,
        settings,
        pools,
        0,
        save_condition_checkpoint=False,
    )
    zero_reward = runner.run_spiking_condition(
        "C",
        substrate,
        plastic_config,
        config,
        settings,
        pools,
        0,
        save_condition_checkpoint=False,
    )
    no_traces = runner.run_spiking_condition(
        "F",
        substrate,
        plastic_config,
        config,
        settings,
        pools,
        0,
        save_condition_checkpoint=False,
    )
    assert plastic["tags_total"] > 0
    assert plastic["changed_edges"] > 0
    assert plastic["final_weights"]["delta_l1_pa"] > 0
    assert plastic["weights_unchanged"] is False
    assert plastic["structural_counts_immutable"]
    assert all(bool(value) for value in plastic["invariants"].values())
    assert zero_reward["weights_unchanged"] is True
    assert zero_reward["final_weights"]["delta_l1_pa"] == 0.0
    assert no_traces["weights_unchanged"] is True
    assert no_traces["tags_total"] == 0
    assert no_traces["slots_total"] == 0
    record = plastic["train"][1]
    for key in (
        "episode",
        "cue",
        "hit",
        "response_ms",
        "n_coincident_tags",
        "n_slots",
        "n_updates",
        "weight_l1_pa",
        "spike_hash",
    ):
        assert key in record
    assert set(plastic["eval"]) == {"0", "4", "8"}
