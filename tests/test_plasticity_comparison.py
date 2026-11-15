"""Phase 5F: comparison design, statistics and delay contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experiments.phase_5 import comparative as runner
from experiments.phase_5 import controlled_task
from plasticity.config import load_plasticity_config
from plasticity.tasks import DelayedReward, TaskConfig, build_task_substrate, load_task_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity_task.yaml"
PLASTICITY_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"


def test_comparison_config_declares_core_family_and_axes():
    settings = runner.load_comparison_config(runner.CONFIG_PATH)
    assert settings["core"]["conditions"] == [
        "fixed_complete",
        "plastic_complete",
        "fixed_random",
        "plastic_random",
    ]
    assert len(settings["core"]["contrasts"]) == 4
    assert settings["core"]["eval_checkpoints"][0] == 0
    assert settings["core"]["n_seeds"] >= 2
    assert set(settings["robustness"]["axes"]) == {
        "eta",
        "tau_e_ms",
        "reward_magnitude",
        "weight_bounds",
        "initial_weights",
        "network_size",
        "structural_threshold",
        "reward_delay_ms",
    }
    for axis, body in settings["robustness"]["axes"].items():
        assert body["reference"] in [str(item["label"]) for item in body["values"]]


def test_threshold_is_declared_and_bounded():
    config = TaskConfig(threshold=2, min_count=2)
    substrate = build_task_substrate(config, seed=3)
    assert substrate.graph.threshold == 2
    assert int(substrate.graph.edge_weight.min()) >= 2
    with pytest.raises(ValueError):
        TaskConfig(threshold=0)


class _RewardAtStep:
    def __init__(self, step: int, value: float) -> None:
        self.step = int(step)
        self.value = float(value)
        self.done = False

    def reset(self) -> None:
        self.done = False

    def __call__(self, step, time_ms, spikes, simulator=None):
        del time_ms, spikes, simulator
        if step == self.step and not self.done:
            self.done = True
            return self.value
        return None


def test_delayed_reward_is_released_after_declared_steps():
    wrapper = DelayedReward(_RewardAtStep(5, 1.0), delay_steps=4)
    assert wrapper(5, 2.5, np.array([], dtype=np.int64)) is None
    assert wrapper(6, 3.0, np.array([], dtype=np.int64)) is None
    assert wrapper(8, 4.0, np.array([], dtype=np.int64)) is None
    assert wrapper(9, 4.5, np.array([], dtype=np.int64)) == 1.0
    assert wrapper(10, 5.0, np.array([], dtype=np.int64)) is None
    assert wrapper.n_delivered == 1
    assert wrapper.n_dropped == 0


def test_delayed_reward_reports_a_dropped_reward():
    wrapper = DelayedReward(_RewardAtStep(5, 1.0), delay_steps=4)
    assert wrapper(5, 2.5, np.array([], dtype=np.int64)) is None
    wrapper.finalize()
    assert wrapper.n_delivered == 0
    assert wrapper.n_dropped == 1


def test_zero_delay_returns_the_reward_immediately():
    wrapper = DelayedReward(_RewardAtStep(5, -1.0), delay_steps=0)
    assert wrapper(5, 2.5, np.array([], dtype=np.int64)) == -1.0
    assert wrapper.n_delivered == 1


def test_sign_flip_is_exact_and_two_sided():
    all_positive = [0.1, 0.1, 0.1]
    result = runner.sign_flip_test(
        all_positive, exact_max_n=16, draws=1000, seed=0
    )
    assert result["p_value"] == pytest.approx(2 / 8)
    symmetric = [0.1, -0.1, 0.1, -0.1, 0.1, -0.1]
    result = runner.sign_flip_test(
        symmetric, exact_max_n=16, draws=1000, seed=0
    )
    assert result["p_value"] == pytest.approx(1.0)
    ten = [0.05] * 10
    result = runner.sign_flip_test(ten, exact_max_n=16, draws=1000, seed=0)
    assert result["p_value"] == pytest.approx(round(2 / 1024, 8), abs=1e-8)


def test_holm_adjusts_and_keeps_order():
    result = runner.holm({"a": 0.01, "b": 0.04, "c": 0.03}, alpha=0.05)
    assert result["adjusted"]["a"] == pytest.approx(0.03)
    assert result["adjusted"]["c"] == pytest.approx(0.06)
    assert result["adjusted"]["b"] == pytest.approx(0.06)
    assert result["rejected"] == {"a": True, "b": False, "c": False}


def test_run_cell_plastic_changes_weights_and_fixed_does_not():
    task_cfg, _ = load_task_config(TASK_CONFIG_PATH)
    plasticity_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)
    pools = controlled_task.seed_pools(
        {
            "master_seed": 314,
            "train_episodes": 8,
            "eval_episodes": 4,
            "replicates": 1,
        }
    )
    common = {
        "task_cfg": task_cfg,
        "bounds": plasticity_config.bounds,
        "trace_config": plasticity_config.traces,
        "reward_magnitude": 1.0,
        "reward_delay_ms": 0.0,
        "train_episodes": 8,
        "checkpoints": [0, 8],
        "pools": pools,
        "seed_index": 0,
        "substrate_seed": 20261114,
    }
    plastic = runner.run_cell("plastic_complete", eta=1.0, **common)
    fixed = runner.run_cell("fixed_complete", eta=0.0, **common)
    assert plastic["weights_unchanged"] is False
    assert plastic["changed_edges"] > 0
    assert fixed["weights_unchanged"] is True
    assert fixed["changed_edges"] == 0
    assert plastic["structural_counts_immutable"] is True
    assert plastic["invariant_error"] is None
    assert plastic["all_finite"] is True
    assert plastic["rewards_dropped"] == 0
    assert set(plastic["eval"]) == {"0", "8"}
    assert 0.0 <= plastic["final_success"] <= 1.0
