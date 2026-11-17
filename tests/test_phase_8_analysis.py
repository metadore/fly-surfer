"""Focused tests for the Phase 8 analysis layer (G6, REV3 §7).

Everything here is synthetic and lightweight: no game, simulator, connectome or
training is started. The tests pin the exact attainable-p arithmetic of §7.5,
the Holm tables, the missing-pair rules of §7.3/§7.6, the identity hard stop of
§3.8.4 and the E1-E5 rules of §3.6.4.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from itertools import product
from pathlib import Path

import pytest

from experiments.phase_8 import load_phase8_config
from experiments.phase_8.analysis import (
    AnalysisError,
    analyse_campaign,
    design_summary,
    evidence_checklist,
    exact_sign_flip,
    exact_sign_test,
    floor_decomposition,
    holm_adjust,
    identity_check,
    pair_series,
)
from experiments.phase_8.analyse_phase_8 import main as cli_main

ARMS = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "A_prime",
    "C_prime",
    "F_beta",
    "F_init",
    "E_full",
    "floor",
)

OFFSETS = {
    "A": 0,
    "B": 3,
    "C": -2,
    "D": 1,
    "E": 6,
    "F": 5,
    "A_prime": 0,
    "C_prime": -2,
    "F_beta": 2,
    "F_init": -1,
    "E_full": 7,
    "floor": None,
}

SEEDS = (1, 2, 3, 4, 5)
EPISODES = 2


@pytest.fixture(scope="module")
def real_config():
    return load_phase8_config()


@pytest.fixture(scope="module")
def small_config(real_config):
    """A 5-seed fixture design, not the declared 10/16 campaign design."""
    campaign = replace(
        real_config.campaign,
        n_seeds_primary=5,
        n_seeds_fallback=3,
        n_seeds_selected=None,
        episodes_per_seed=EPISODES,
        campaign_seeds=SEEDS,
        bootstrap_resamples=200,
        bootstrap_seed=7,
    )
    return replace(real_config, campaign=campaign)


def build_rows(
    make_row,
    *,
    offsets=None,
    omit=(),
    errors=(),
    rewards=None,
):
    offsets = OFFSETS if offsets is None else offsets
    rewards = rewards or {}
    rows = []
    for arm in ARMS:
        for seed in SEEDS:
            for episode in range(EPISODES):
                key = (arm, seed, episode)
                if key in omit:
                    continue
                if key in errors:
                    rows.append(make_row(arm, seed, episode, status="error"))
                    continue
                score = 2 if arm == "floor" else 10 + seed + offsets[arm]
                rows.append(
                    make_row(
                        arm,
                        seed,
                        episode,
                        steps=score,
                        total_reward=rewards.get(key, 0.0),
                    )
                )
    return rows


def brute_force_sign_flip(values):
    n = len(values)
    observed = abs(sum(values, Fraction(0)))
    count = 0
    for signs in product((1, -1), repeat=n):
        total = sum(sign * value for sign, value in zip(signs, values))
        if abs(total) >= observed:
            count += 1
    return Fraction(count, 1 << n), count


# ---------------------------------------------------------------------------
# exact sign-flip
# ---------------------------------------------------------------------------


def test_sign_flip_14_2_at_n16_matches_rev3_section_7_5():
    values = [Fraction(1)] * 14 + [Fraction(-1)] * 2
    result = exact_sign_flip(values)
    assert result["n"] == 16
    assert result["n_sign_vectors"] == 65_536
    assert result["count_at_least_as_extreme"] == 274
    p = result["p_value"]
    assert Fraction(p["numerator"], p["denominator"]) == Fraction(274, 65_536)
    assert p["value"] == pytest.approx(0.004180908203125)
    assert result["degenerate_all_zero"] is False


def test_sign_flip_13_3_fails_holm_step1_at_m4():
    values = [Fraction(1)] * 13 + [Fraction(-1)] * 3
    result = exact_sign_flip(values)
    assert result["count_at_least_as_extreme"] == 1394
    p = Fraction(
        result["p_value"]["numerator"], result["p_value"]["denominator"]
    )
    assert p == Fraction(1394, 65_536)
    assert float(p) > 0.0125
    assert result["minimum_two_sided_p"]["exact"] == "2/65536"


def test_sign_flip_all_zero_is_degenerate_and_never_significant():
    result = exact_sign_flip([Fraction(0)] * 10)
    assert result["degenerate_all_zero"] is True
    assert result["p_value"]["numerator"] == result["p_value"]["denominator"] == 1
    assert result["p_value"]["value"] == 1.0
    assert "no power" in result["note"]
    assert "not evidence" in result["note"]


def test_sign_flip_mixed_sign_is_not_degenerate():
    result = exact_sign_flip([Fraction(10), Fraction(-10)])
    assert result["degenerate_all_zero"] is False
    assert "note" not in result


def test_sign_flip_matches_brute_force_enumeration():
    values = [
        Fraction(3),
        Fraction(-1),
        Fraction(1, 2),
        Fraction(7, 10),
        Fraction(-2),
        Fraction(1, 3),
    ]
    expected_p, expected_count = brute_force_sign_flip(values)
    result = exact_sign_flip(values)
    assert result["count_at_least_as_extreme"] == expected_count
    assert (
        Fraction(
            result["p_value"]["numerator"], result["p_value"]["denominator"]
        )
        == expected_p
    )


def test_sign_flip_refuses_more_than_the_enumerated_maximum():
    with pytest.raises(AnalysisError):
        exact_sign_flip([Fraction(1)] * 19)


def test_sign_test_8_2_at_n10():
    values = [Fraction(1)] * 8 + [Fraction(-1)] * 2
    result = exact_sign_test(values)
    assert result["n_nonzero"] == 10
    assert result["zeros_dropped"] == 0
    assert Fraction(result["p_value"]["numerator"], result["p_value"]["denominator"]) == Fraction(
        112, 1024
    )
    assert result["p_value"]["value"] == pytest.approx(0.109375)


def test_sign_test_drops_zeros_for_that_check_only():
    values = [Fraction(1)] * 8 + [Fraction(0)] * 2
    result = exact_sign_test(values)
    assert result["n_nonzero"] == 8
    assert result["zeros_dropped"] == 2
    assert Fraction(result["p_value"]["numerator"], result["p_value"]["denominator"]) == Fraction(
        2, 256
    )


# ---------------------------------------------------------------------------
# Holm
# ---------------------------------------------------------------------------

N16_THRESHOLDS = {
    "C1": Fraction(819, 65_536),
    "C2": Fraction(1092, 65_536),
    "C3": Fraction(1638, 65_536),
    "C4": Fraction(3276, 65_536),
}


def test_holm_admissible_counts_at_n16_m4_are_all_rejected():
    result = holm_adjust(N16_THRESHOLDS, alpha=0.05, family_size=4)
    assert [step["rejected"] for step in result["steps"]] == [True] * 4
    assert result["rejected"] == ["C1", "C2", "C3", "C4"]
    adjusted = [
        Fraction(step["p_adjusted"]["numerator"], step["p_adjusted"]["denominator"])
        for step in result["steps"]
    ]
    assert adjusted == [Fraction(3276, 65_536)] * 4


def test_holm_step1_failure_stops_the_family():
    values = dict(N16_THRESHOLDS)
    values["C1"] = Fraction(820, 65_536)
    result = holm_adjust(values, alpha=0.05, family_size=4)
    assert [step["rejected"] for step in result["steps"]] == [False] * 4
    assert result["rejected"] == []


def test_holm_m3_thresholds_at_n16():
    result = holm_adjust(
        {
            "C1": Fraction(1092, 65_536),
            "C2": Fraction(1638, 65_536),
            "C3": Fraction(3276, 65_536),
        },
        alpha=0.05,
        family_size=3,
    )
    assert result["steps"][0]["threshold"] == pytest.approx(1 / 60)
    assert result["steps"][0]["rejected"] is True
    assert Fraction(
        result["steps"][0]["p_adjusted"]["numerator"],
        result["steps"][0]["p_adjusted"]["denominator"],
    ) == Fraction(3276, 65_536)


def test_holm_requires_the_declared_family_size():
    with pytest.raises(AnalysisError):
        holm_adjust(N16_THRESHOLDS, alpha=0.05, family_size=3)


# ---------------------------------------------------------------------------
# design constants (§7.1, §7.4, §7.5)
# ---------------------------------------------------------------------------


def test_design_summary_reproduces_primary_n16_numbers(real_config):
    design = design_summary(real_config.campaign, family_size=4)
    primary = design["variants"]["primary"]
    assert primary["n"] == 16
    assert primary["sign_vectors"] == 65_536
    assert primary["minimum_two_sided_p"] == pytest.approx(2 / 65_536)
    assert primary["raw_two_sided_0_05_count_threshold"] == 3276
    assert [
        step["admissible_sign_vectors"] for step in primary["holm_steps"]
    ] == [819, 1092, 1638, 3276]
    assert primary["minimum_adjusted_p"] == pytest.approx(4 * 2 / 65_536)
    assert primary["mde_at_assumed_sigma"] == pytest.approx(42.024, abs=0.01)
    assert primary["sigma_supported_for_sei"] == pytest.approx(142.8, abs=0.1)
    assert primary["holm_step1_mde_at_assumed_sigma"] == pytest.approx(50.1, abs=0.1)


def test_design_summary_reproduces_fallback_n10_numbers_and_flags_discrepancy(real_config):
    design = design_summary(real_config.campaign, family_size=4)
    fallback = design["variants"]["fallback"]
    assert fallback["sign_vectors"] == 1024
    assert fallback["minimum_two_sided_p"] == pytest.approx(2 / 1024)
    assert fallback["raw_two_sided_0_05_count_threshold"] == 51
    assert [
        step["admissible_sign_vectors"] for step in fallback["holm_steps"]
    ] == [12, 17, 25, 51]
    assert fallback["minimum_adjusted_p"] == pytest.approx(4 * 2 / 1024)
    assert fallback["mde_at_assumed_sigma"] == pytest.approx(53.155, abs=0.01)
    assert fallback["sigma_supported_for_sei"] == pytest.approx(112.87, abs=0.05)

    check = design["fallback_threshold_check"]
    assert check["declared_max_paired_sd"] == pytest.approx(112.87, abs=0.05)
    assert check["computed_from_mde_formula"] == pytest.approx(112.87, abs=0.05)
    assert check["consistent"] is True
    assert "agree" in check["note"]


# ---------------------------------------------------------------------------
# pairing and missing cells
# ---------------------------------------------------------------------------


def test_pair_series_excludes_only_invalid_cells(phase_8_row):
    make_row = phase_8_row
    rows = [
        make_row("A", 1, 0, steps=10),
        make_row("A", 1, 1, steps=11),
        make_row("F", 1, 0, steps=20),
        # episode 1 of F is missing: the seed keeps episode 0 only
        make_row("A", 2, 0, steps=10),
        make_row("F", 2, 0, steps=21),
        make_row("F", 2, 1, steps=22),
        make_row("A", 3, 0, steps=0, status="error"),
        make_row("A", 3, 1, steps=10),
        make_row("F", 3, 0, steps=20),
        make_row("F", 3, 1, steps=21),
    ]
    pairs, excluded, left, right = pair_series(
        rows, "F", "A", seeds=(1, 2, 3), episodes_per_seed=2
    )
    assert [pair.seed for pair in pairs] == [1, 2, 3]
    assert pairs[0].cells == (0,)
    assert pairs[1].cells == (0,)
    assert pairs[2].cells == (1,)
    # seed 1 loses F episode 1 (right side actually: A is the subtrahend and
    # has an extra cell), seed 2 loses A episode 1, and seed 3 loses the F and
    # A episode-0 cells because the A cell is an error and is not entered.
    assert left == 2 and right == 1
    assert excluded == []


def test_pair_series_reports_a_seed_with_no_common_cell(phase_8_row):
    rows = [
        phase_8_row("A", 1, 0, steps=10),
        phase_8_row("F", 1, 0, status="error"),
        phase_8_row("A", 1, 1, steps=12),
        phase_8_row("F", 1, 1, status="error"),
    ]
    pairs, excluded, left, right = pair_series(
        rows, "F", "A", seeds=(1,), episodes_per_seed=2
    )
    assert pairs == []
    assert left == 0 and right == 2
    assert excluded[0]["seed"] == 1
    assert excluded[0]["reason"] == "no valid episode in the minuend arm"


# ---------------------------------------------------------------------------
# identity control
# ---------------------------------------------------------------------------


def test_identity_pass_requires_every_row_and_field(phase_8_row):
    rows = [
        phase_8_row("A", seed, episode, steps=10 + seed)
        for seed in SEEDS
        for episode in range(EPISODES)
    ] + [
        phase_8_row("A_prime", seed, episode, steps=10 + seed)
        for seed in SEEDS
        for episode in range(EPISODES)
    ]
    report = identity_check(
        rows,
        control="A_prime",
        target="A",
        seeds=SEEDS,
        episodes_per_seed=EPISODES,
    )
    assert report["status"] == "pass"
    assert report["pairs_compared"] == len(SEEDS) * EPISODES
    assert report["invalidated_arm"] == "B"


def test_identity_mismatch_is_a_fail(phase_8_row):
    rows = [
        phase_8_row("A", 1, 0, steps=10, total_reward=0.0),
        phase_8_row("A_prime", 1, 0, steps=10, total_reward=0.5),
    ]
    report = identity_check(
        rows,
        control="A_prime",
        target="A",
        seeds=(1,),
        episodes_per_seed=1,
    )
    assert report["status"] == "fail"
    assert report["mismatch_count"] == 1
    assert report["mismatches"][0]["field"] == "total_reward"


def test_identity_missing_row_is_incomplete_not_a_pass(phase_8_row):
    rows = [
        phase_8_row("C", 1, 0, steps=10),
        phase_8_row("C", 1, 1, steps=11),
        phase_8_row("C_prime", 1, 0, steps=10),
    ]
    report = identity_check(
        rows,
        control="C_prime",
        target="C",
        seeds=(1,),
        episodes_per_seed=2,
    )
    assert report["status"] == "incomplete"
    assert report["pairs_missing"] == 1


# ---------------------------------------------------------------------------
# campaign analysis
# ---------------------------------------------------------------------------


def test_analyse_campaign_computes_the_family_and_identity(
    phase_8_row, small_config
):
    rows = build_rows(phase_8_row)
    result = analyse_campaign(
        rows,
        small_config,
        family_size=4,
        n_seeds=5,
        include_sensitivity=False,
    )
    assert result["primary_status"] == "computed"
    assert result["n_seeds_planned"] == 5
    assert result["n_seeds_analysed"] == 5
    assert result["n_floor"] == 3
    assert result["identity"]["A_prime"]["status"] == "pass"
    assert result["identity"]["C_prime"]["status"] == "pass"
    for contrast in result["confirmatory"]["contrasts"].values():
        assert contrast["seeds_paired"] == 5
        assert "sign_flip" in contrast
        assert contrast["holm_rejected"] is False
    assert result["confirmatory"]["holm"]["family_size"] == 4
    assert result["floor"]["status"] == "measured"
    assert result["readout"]["checklist"]["decoding_claim_permitted"] is False


def test_analyse_campaign_withholds_below_the_predeclared_floor(
    phase_8_row, small_config
):
    omit = {
        ("A", seed, episode)
        for seed in (3, 4, 5)
        for episode in range(EPISODES)
    }
    result = analyse_campaign(
        build_rows(phase_8_row, omit=omit),
        small_config,
        family_size=4,
        n_seeds=5,
        include_sensitivity=False,
    )
    assert result["primary_status"] == "design_failure"
    assert result["confirmatory"]["status"] == "withheld"
    assert result["confirmatory"]["holm"] is None
    for contrast_id in ("C1", "C2", "C3"):
        block = result["confirmatory"]["contrasts"][contrast_id]
        assert block["status"] == "design_failure"
        assert block["seeds_paired"] == 2
    assert (
        result["confirmatory"]["contrasts"]["C4"].get("status")
        != "design_failure"
    )
    assert any("predeclared minimum" in warning for warning in result["warnings"])
    assert any("asymmetric" in warning for warning in result["warnings"])


def test_analyse_campaign_flags_an_all_zero_contrast(phase_8_row, small_config):
    offsets = dict(OFFSETS)
    offsets["F"] = 0  # F - A is exactly zero on every seed
    result = analyse_campaign(
        build_rows(phase_8_row, offsets=offsets),
        small_config,
        family_size=4,
        n_seeds=5,
        include_sensitivity=False,
    )
    c1 = result["confirmatory"]["contrasts"]["C1"]
    assert c1["sign_flip"]["degenerate_all_zero"] is True
    assert c1["sign_flip"]["p_value"]["value"] == 1.0
    assert c1["sign_test"]["p_value"]["value"] == 1.0
    assert any("every paired difference is zero" in warning for warning in result["warnings"])


def test_identity_failure_invalidates_b_and_d(phase_8_row, small_config):
    rewards = {("A_prime", 1, 0): 1.0}
    result = analyse_campaign(
        build_rows(phase_8_row, rewards=rewards),
        small_config,
        family_size=4,
        n_seeds=5,
        include_sensitivity=False,
    )
    assert result["identity"]["A_prime"]["status"] == "fail"
    assert result["arms"]["B"]["invalid"] is True
    assert result["arms"]["D"]["invalid"] is True
    assert result["primary_status"] == "design_failure"
    c2 = result["confirmatory"]["contrasts"]["C2"]
    assert c2.get("invalid") is True
    assert c2["status"] == "design_failure"
    # C3 = A - C involves neither invalidated arm and remains computable.
    assert (
        result["confirmatory"]["contrasts"]["C3"].get("invalid") is None
    )
    d_minus_c = next(
        block for block in result["secondary"] if block["id"] == "D_minus_C"
    )
    assert d_minus_c.get("invalid") is True
    assert result["floor"]["status"] == "measured"


def test_sensitivity_block_appears_for_error_rows(phase_8_row, small_config):
    errors = {("B", 1, 0)}
    result = analyse_campaign(
        build_rows(phase_8_row, errors=errors),
        small_config,
        family_size=4,
        n_seeds=5,
        include_sensitivity=True,
    )
    c2 = result["confirmatory"]["contrasts"]["C2"]
    assert "sensitivity" in c2
    assert c2["sensitivity"]["scored_at"] == "last completed update (REV3 §7.6)"
    assert result["missingness"]["arms"]["B"]["error"] == 1


def test_floor_decomposition_requires_a_measured_floor(phase_8_row, small_config):
    rows = [row for row in build_rows(phase_8_row) if row["condition"] != "floor"]
    report = floor_decomposition(
        rows,
        arms=("A", "B", "C", "D", "E", "F"),
        conditions=("A", "B", "C", "D", "E", "F"),
        seeds=SEEDS,
        episodes_per_seed=EPISODES,
        bootstrap_resamples=100,
        bootstrap_seed=1,
    )
    assert report["status"] == "not measured"
    assert "never assumed" in report["note"]


# ---------------------------------------------------------------------------
# E1-E5
# ---------------------------------------------------------------------------


def test_e4_zero_over_zero_is_undefined_never_a_pass(phase_8_row):
    rows = [
        phase_8_row(
            "F",
            seed,
            episode,
            steps=10,
            non_no_action=0,
            decision_classes={"motor-driven": 0, "bias-driven": 0},
            motor_summary={"decisions": 10, "decisions_with_motor_spike": 0},
        )
        for seed in SEEDS
        for episode in range(EPISODES)
    ]
    checklist = evidence_checklist(
        rows,
        confirmatory={"C1": {"holm_rejected": False}, "C4": {"holm_rejected": False}},
        family_size=4,
        seeds=SEEDS,
        episodes_per_seed=EPISODES,
    )
    assert checklist["checks"]["E4"]["status"] == "undefined"
    assert checklist["checks"]["E4"]["numerator"] == 0
    assert checklist["checks"]["E4"]["denominator"] == 0
    assert checklist["decoding_claim_permitted"] is False


def test_e3_fails_when_the_motor_populations_are_silent(phase_8_row):
    rows = [
        phase_8_row(
            "F",
            seed,
            episode,
            steps=10,
            non_no_action=2,
            decision_classes={"motor-driven": 0, "bias-driven": 2},
            motor_summary={"decisions": 10, "decisions_with_motor_spike": 0},
        )
        for seed in SEEDS
        for episode in range(EPISODES)
    ]
    checklist = evidence_checklist(
        rows,
        confirmatory={"C1": {"holm_rejected": False}, "C4": {"holm_rejected": False}},
        family_size=4,
        seeds=SEEDS,
        episodes_per_seed=EPISODES,
    )
    assert checklist["checks"]["E3"]["status"] == "fail"
    assert checklist["checks"]["E4"]["status"] == "fail"
    assert checklist["checks"]["E5"]["status"] == "not run"
    assert checklist["decoding_claim_permitted"] is False


# ---------------------------------------------------------------------------
# CLI (store in, analysis JSON out)
# ---------------------------------------------------------------------------


def test_cli_writes_once_and_refuses_to_overwrite(tmp_path, real_config, phase_8_row):
    seeds = real_config.campaign.campaign_seeds[:10]
    rows = []
    for arm in ("A", "F"):
        for seed in seeds:
            steps = 10 + (10 if arm == "F" else 0) + (seed % 3)
            rows.append(phase_8_row(arm, seed, 0, steps=steps))
    store = tmp_path / "episodes.jsonl"
    store.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    before = store.read_text(encoding="utf-8")
    output = tmp_path / "analysis.json"

    assert cli_main(
        [
            "--store",
            str(store),
            "--output",
            str(output),
            "--family-size",
            "4",
            "--n-seeds",
            "10",
        ]
    ) == 0
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["rows"] == len(rows)
    assert payload["n_seeds_planned"] == 10
    assert store.read_text(encoding="utf-8") == before

    assert cli_main(
        [
            "--store",
            str(store),
            "--output",
            str(output),
            "--family-size",
            "4",
            "--n-seeds",
            "10",
        ]
    ) == 2
    assert cli_main(
        [
            "--store",
            str(store),
            "--output",
            str(output),
            "--family-size",
            "4",
            "--n-seeds",
            "10",
            "--overwrite",
        ]
    ) == 0
