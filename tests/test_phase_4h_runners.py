"""Phase 4H.1-4H.3: analysis helpers used by the phase runners."""

from __future__ import annotations

import numpy as np
import pytest

from experiments.phase_4h import common
from experiments.phase_4h import control_draws as cd
from experiments.phase_4h import population_sensitivity as ps
from experiments.phase_4h import weight_sensitivity as ws


# -- 4H.1 -------------------------------------------------------------------


def test_endpoint_block_reports_percentile_and_binary_proportion():
    block = cd.endpoint_block(4, [0, 1, 2, 3], "binary")
    assert block["n"] == 4
    assert block["n_missing"] == 0
    assert block["p_one_sided_greater"] == pytest.approx(0.2)
    assert block["proportion_nonzero"] == pytest.approx(0.75)
    low, high = block["wilson_95"]
    assert low <= 0.75 <= high


def test_endpoint_block_handles_missing_reference_and_values():
    block = cd.endpoint_block(None, [None, None], "number")
    assert block["n"] == 0
    assert block["n_missing"] == 2
    assert "note" in block


def test_matching_summary_recurses_into_nested_dicts():
    values = [
        {"a": {"jaccard": 0.5, "size": 2}, "b": 1.0},
        {"a": {"jaccard": 0.7, "size": 2}, "b": 3.0},
    ]
    summary = cd._matching_summary(values)
    assert summary["a"]["jaccard"]["mean"] == pytest.approx(0.6)
    assert summary["a"]["size"]["sd"] == 0.0
    assert summary["b"]["max"] == pytest.approx(3.0)


def test_confirmatory_holm_across_families():
    def family(p1, p2):
        return {
            "endpoints": {
                "P1_motor_spikes": {
                    "p_one_sided_greater": p1,
                    "cliffs_delta": 1.0,
                    "cliffs_delta_ci": [1.0, 1.0],
                    "hedges_g": 2.0,
                    "empirical_percentile": 1.0,
                },
                "P2_jump_windows": {
                    "p_one_sided_greater": p2,
                    "cliffs_delta": 0.0,
                    "cliffs_delta_ci": [0.0, 0.0],
                    "hedges_g": 0.0,
                    "empirical_percentile": 0.5,
                },
            }
        }

    families = {
        "A": family(0.01, 0.5),
        "B": family(0.20, 0.5),
        "C": family(0.40, 0.5),
        "D": family(0.60, 0.5),
        "E": family(0.90, 0.5),
    }
    reference = {"P1_motor_spikes": 10, "P2_jump_windows": 4}
    result = cd.confirmatory(families, reference)
    assert result["alpha"] == 0.05
    assert result["P1_motor_spikes"]["holm"]["rejected"]["A"] is True
    assert result["P1_motor_spikes"]["holm"]["rejected"]["B"] is False
    assert result["any_confirmatory_difference"] is True


def test_family_statistics_pools_decisions_and_matching():
    def draw(seed, motor, state):
        return {
            "seed": seed,
            "pool": "C_all_verified_excitatory_random",
            "pool_size": 10,
            "matching": {"size_overlap": {"jaccard": 0.1}},
            "flat": {
                "P1_motor_spikes": motor,
                "P2_jump_windows": 0,
                "total_spikes": 10 * motor,
                "non_neutral_windows": 0,
                "time_to_first_motor_spike_ms": 100.0 if motor else None,
            },
            "metrics": {"decoded_state_counts": state},
            "wall_time_s": 1.0,
            "memory": {"retained_arrays_mb": 5.0},
        }

    draws = [
        draw(1, 0, {"NEUTRAL": 6}),
        draw(2, 2, {"NEUTRAL": 5, "JUMP": 1}),
    ]
    result = cd.family_statistics(
        draws,
        {
            "P1_motor_spikes": 4,
            "P2_jump_windows": 4,
            "non_neutral_windows": 1,
        },
    )
    assert result["n_draws"] == 2
    assert result["seeds"] == [1, 2]
    assert result["decision_state_totals"] == {"NEUTRAL": 11, "JUMP": 1}
    assert result["endpoints"]["P1_motor_spikes"]["n"] == 2
    assert result["endpoints"]["any_motor_spike"]["proportion_nonzero"] == 0.5
    assert result["matching_diagnostics"]["size_overlap"]["jaccard"]["mean"] == 0.1


# -- 4H.2 -------------------------------------------------------------------


def test_population_rule_seeds_are_unique_and_pre_registered():
    seeds = {
        ps.rule_seed(rule, size, draw)
        for rule in ps.RULES
        for size in ps.SIZES
        for draw in range(ps.DRAWS_PER_CELL)
    }
    assert len(seeds) == len(ps.RULES) * len(ps.SIZES) * ps.DRAWS_PER_CELL
    assert ps.rule_seed(ps.RULES[0], 8, 0) == (
        common.SEED_ROOT
        + 200_000
        + 8_000
        + 10 * ps.RULE_ORDINAL[ps.RULES[0]]
    )


def test_null_summary_reports_empirical_p_and_percentile():
    null = np.linspace(0.0, 1.0, 101)
    summary = ps._null_summary(0.6, null)
    assert summary["n_subsets"] == 101
    assert summary["p_greater"] == pytest.approx(
        (1 + np.count_nonzero(null >= 0.6)) / 102
    )
    assert 0.0 <= summary["percentile"] <= 1.0


def test_contrast_reports_direction_and_p_value():
    block = ps.contrast([10, 12, 11], [0, 0, 0], "test")
    assert block["difference"] == pytest.approx(11.0)
    assert block["p_one_sided_greater"] == pytest.approx(0.25)
    assert block["empirical_percentile"] == 1.0


# -- 4H.3 -------------------------------------------------------------------


def test_weight_grid_matches_preregistration():
    ids = [config["id"] for config in ws.CONFIGS]
    assert len(ids) == 22
    assert len(set(ids)) == 22
    assert ids[0] == "D0_W0_S0"
    assert [config["ordinal"] for config in ws.CONFIGS] == list(range(22))
    assert sum(config["drive"] == "D1" for config in ws.CONFIGS) == 8
    assert ws.REFERENCE_ID == "D0_W0_S0"
    assert ws.config_seed(0, 0) == common.SEED_ROOT + 300_000
    assert ws.config_seed(3, 7) == common.SEED_ROOT + 300_000 + 307


def test_weight_policies_declare_w4_equals_w1():
    class FakeGraph:
        n_nodes = 1
        edge_dst = np.zeros(0, dtype=np.int64)
        edge_weight = np.zeros(0, dtype=np.int64)

    class FakeWorld:
        graph = FakeGraph()

    weights = ws.weight_policies(FakeWorld())
    assert weights["W4"].describe() == weights["W1"].describe()
    assert weights["W2"].cap_pa is None
    assert weights["W5"].cap_pa is None


def test_weight_config_summary_flags_silent_and_neutral():
    def flat(**overrides):
        payload = {
            "P1_motor_spikes": 0,
            "P2_jump_windows": 0,
            "total_spikes": 10,
            "non_stimulated_spikes": 10,
            "active_neurons": 3,
            "motor_active_neurons": 0,
            "neutral_windows": 6,
            "left_windows": 0,
            "right_windows": 0,
            "time_to_first_motor_spike_ms": None,
            "post_stimulation_spikes": 1,
            "left_active_fraction": 0.0,
            "right_active_fraction": 0.0,
            "jump_active_fraction": 0.0,
            "left_peak_window_active_fraction": 0.0,
            "right_peak_window_active_fraction": 0.0,
            "jump_peak_window_active_fraction": 0.0,
            "non_neutral_windows": 0,
        }
        payload.update(overrides)
        return payload

    runs = [
        {
            "seed": 1,
            "current_pa": 300.0,
            "aggregate_out_weight_pa": 1000.0,
            "spike_hash": "a",
            "decision_hash": "b",
            "policy": {"weight": "w"},
            "flat": flat(),
        },
        {
            "seed": 2,
            "current_pa": 300.0,
            "aggregate_out_weight_pa": 1000.0,
            "spike_hash": "a",
            "decision_hash": "b",
            "policy": {"weight": "w"},
            "flat": flat(),
        },
    ]
    summary = ws.config_summary(runs)
    assert summary["silent"] is True
    assert summary["neutral_only"] is True
    assert summary["all_spike_hashes_equal"] is True
    assert summary["endpoints"]["P1_motor_spikes"]["n"] == 2
