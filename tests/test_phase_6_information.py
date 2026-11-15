"""Focused tests for the Phase 6 analysis runner, population codes and matching.

All synthetic observations here exist only to check algebra, coding rules and
error policy. The three artifact-backed tests read archived Phase 5 files and
assert only that declared matched conditions really are matched; they compute
no research estimate.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.phase_6.run_information_analysis import (  # noqa: E402
    _distance_codes,
    contingency,
    json_safe,
    load_config,
    mi_endpoint,
    paired_bootstrap_mean,
    per_seed_mi,
)
from information.artifact_readers import UnavailableEndpoint, load_phase5e, load_phase5f  # noqa: E402
from information.discretization import MISSING, ordinal_thresholds  # noqa: E402
from information.matching import (  # noqa: E402
    match_keys,
    validate_cluster_coverage,
    validate_equal_lengths,
)
from information.population import (  # noqa: E402
    level_pattern_codes,
    pattern_codes,
    population_information,
)


# ---------------------------------------------------------------------------
# population coding
# ---------------------------------------------------------------------------


def test_pattern_codes_map_whole_rows_and_are_order_independent():
    rows = np.array([[0, 1], [2, 0], [0, 1], [1, 1]])
    coded = pattern_codes(rows, name="p")
    assert coded.codes.tolist() == [0, 2, 0, 1]
    shuffled = rows[[2, 0, 3, 1]]
    recoded = pattern_codes(shuffled, name="p").codes.tolist()
    assert recoded == [0, 0, 1, 2]


def test_pattern_codes_binary_and_cap_collapse_magnitude_only():
    binary = pattern_codes([[0, 9], [1, 0]], binary=True, name="b")
    assert binary.codes.tolist() == [0, 1]
    capped = pattern_codes([[2, 0], [5, 0], [1, 0]], cap=2, name="c")
    assert capped.codes.tolist()[0] == capped.codes.tolist()[1]
    assert capped.codes.tolist()[2] != capped.codes.tolist()[0]


def test_pattern_codes_mark_a_row_with_any_bad_entry_missing():
    coded = pattern_codes([[1.0, -1.0], [0.0, 1.0]], name="p")
    assert coded.codes.tolist() == [MISSING, 0]
    assert coded.n_missing == 1


def test_pattern_codes_reject_empty_ragged_and_fully_missing_rows():
    with pytest.raises(ValueError, match="two-dimensional"):
        pattern_codes([0, 1], name="p")
    with pytest.raises(ValueError, match="empty"):
        pattern_codes(np.zeros((0, 2)), name="p")
    with pytest.raises(ValueError, match="no usable observations"):
        pattern_codes([[np.nan, 0.0]], name="p")


def test_level_pattern_codes_equal_independent_column_thresholding():
    values = np.array([[0.02, 0.35], [0.18, 0.05], [0.5, 0.4]])
    population = level_pattern_codes(values, [0.1, 0.2], name="lvl")
    columns = [
        ordinal_thresholds(values[:, i], [0.1, 0.2], f"c{i}").codes for i in range(2)
    ]
    for row, code in enumerate(population.codes):
        assert population.labels[code] == f"{columns[0][row]}|{columns[1][row]}"


def test_population_information_is_descriptive_bookkeeping():
    result = population_information(1.0, [0.25, 0.5, None])
    assert result["joint_mi_bits"] == pytest.approx(1.0)
    assert result["individual_mi_bits"] == [0.25, 0.5]
    assert result["max_individual_mi_bits"] == pytest.approx(0.5)
    assert result["sum_individual_mi_bits"] == pytest.approx(0.75)
    assert result["joint_minus_max_individual_bits"] == pytest.approx(0.5)
    assert result["sum_individual_minus_joint_bits"] == pytest.approx(-0.25)
    assert "double-counts" in result["interpretation"]


def test_population_information_without_individual_estimates():
    result = population_information(1.0, [None, float("nan")])
    assert result["joint_mi_bits"] == pytest.approx(1.0)
    assert result["sum_individual_mi_bits"] is None


# ---------------------------------------------------------------------------
# matching validation
# ---------------------------------------------------------------------------


def test_validate_equal_lengths_accepts_equal_and_reports_unequal():
    assert validate_equal_lengths(x=[0, 1], y=[0, 1]) == {"x": 2, "y": 2}
    with pytest.raises(ValueError, match="x=2, y=3"):
        validate_equal_lengths(x=[0, 1], y=[0, 1, 2])


def test_match_keys_returns_sorted_shared_keys():
    assert match_keys([3, 1, 2], [2, 3, 1], label="seeds") == [1, 2, 3]


def test_match_keys_rejects_duplicates_and_unmatched_keys():
    with pytest.raises(ValueError, match="duplicates"):
        match_keys([1, 1], [1, 2])
    with pytest.raises(ValueError, match="only left=\\[2\\]"):
        match_keys([1, 2], [1, 3])
    with pytest.raises(ValueError, match="empty"):
        match_keys([], [1])


def test_cluster_coverage_requires_exactly_the_expected_clusters():
    result = validate_cluster_coverage([0, 1, 0], [0, 1])
    assert result == {"n_observations": 3, "n_clusters": 2, "clusters": ["0", "1"]}
    with pytest.raises(ValueError, match="missing=\\['2'\\]"):
        validate_cluster_coverage([0, 1], [0, 1, 2])
    with pytest.raises(ValueError, match="unexpected=\\['3'\\]"):
        validate_cluster_coverage([0, 1, 3], [0, 1])


# ---------------------------------------------------------------------------
# one MI endpoint: reproducibility, scheme choice, support policy
# ---------------------------------------------------------------------------


def _config(**overrides) -> dict:
    config = load_config()
    config = json.loads(json.dumps(config))  # independent copy
    config["permutation"]["n_permutations_confirmatory"] = 200
    config["permutation"]["n_permutations_exploratory"] = 200
    config["bootstrap"]["n_resamples"] = 200
    for key, value in overrides.items():
        config[key].update(value)
    return config


def _dependent_pair(n: int = 40, seed: int = 4):
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 4, n)
    return x, np.where(rng.random(n) < 0.9, x, rng.integers(0, 4, n))


def test_mi_endpoint_is_reproducible_and_uses_block_clusters():
    x, y = _dependent_pair()
    clusters = np.repeat(np.arange(10), 4)
    kwargs = dict(
        label="synthetic",
        provenance="simulated",
        clusters=clusters,
        levels=(4, 4),
        config=_config(),
        seed=77,
        status="exploratory",
    )
    first = mi_endpoint(x, y, **kwargs)
    second = mi_endpoint(x, y, **kwargs)
    assert first == second
    assert first["null"]["scheme"] == "block"
    assert first["null"]["n_clusters"] == 10
    assert first["effective_sample"]["n_clusters"] == 10
    assert 0.5 < first["raw_mi_bits"] < 2.0


def test_mi_endpoint_withholds_inference_for_a_constant_variable():
    x = np.zeros(20, dtype=np.int64)
    y = np.tile([0, 1, 2, 3], 5)
    block = mi_endpoint(
        x,
        y,
        label="constant",
        provenance="simulated",
        clusters=np.repeat(np.arange(10), 2),
        levels=(1, 4),
        config=_config(),
        seed=1,
        status="exploratory",
    )
    assert block["estimable"] is False
    assert block["raw_mi_bits"] == pytest.approx(0.0)
    assert block["null"]["status"] == "not_estimable"
    assert block["bootstrap_ci"]["low"] is None
    assert any("not estimable" in warning for warning in block["warnings"])


def test_mi_endpoint_reports_zero_complete_observations_for_all_missing():
    x = np.full(20, MISSING, dtype=np.int64)
    y = np.tile([0, 1, 2, 3], 5)
    block = mi_endpoint(
        x,
        y,
        label="empty",
        provenance="simulated",
        clusters=np.repeat(np.arange(10), 2),
        levels=(1, 4),
        config=_config(),
        seed=2,
        status="exploratory",
    )
    assert block["n"] == 0
    assert block["estimable"] is False
    assert block["contingency"] == []
    assert any("no complete observations" in warning for warning in block["warnings"])


def test_mi_endpoint_warns_when_below_confirmatory_support():
    x, y = _dependent_pair()
    block = mi_endpoint(
        x,
        y,
        label="small",
        provenance="simulated",
        clusters=np.repeat(np.arange(10), 4),
        levels=(4, 4),
        config=_config(),
        seed=3,
        status="confirmatory",
    )
    assert block["support"]["n"] == 40
    assert any("below the confirmatory minimum" in warning for warning in block["warnings"])


def test_mi_endpoint_rejects_unmatched_lengths():
    with pytest.raises(ValueError, match="unequal lengths"):
        mi_endpoint(
            [0, 1],
            [0, 1, 0],
            label="bad",
            provenance="simulated",
            clusters=[0, 1],
            levels=(2, 2),
            config=_config(),
            seed=1,
            status="exploratory",
        )


def test_free_permutation_is_global_even_when_clusters_are_singletons():
    from information.permutation import permutation_null

    rng = np.random.default_rng(5)
    x = rng.integers(0, 4, 60)
    result = permutation_null(
        x,
        x.copy(),
        clusters=np.arange(60),
        scheme="free",
        n_permutations=200,
        seed=3,
    )
    assert result["n_permutation_groups"] == 1
    assert result["n_clusters"] == 60
    assert result["null_sd"] > 0.0
    assert result["p_value"] < 0.05


def test_exact_permutation_enumeration_matches_hand_count():
    from information.permutation import permutation_null

    x = np.array([0, 1, 0, 1])
    y = np.array([0, 1, 0, 1])
    result = permutation_null(
        x,
        y,
        clusters=np.array([0, 0, 1, 1]),
        scheme="block",
        n_permutations=100,
        seed=1,
        exact_max_assignments=10,
    )
    # Two clusters of two values give 2 * 2 = 4 assignments. The identity and
    # the same swap applied in both clusters both reproduce the bijection.
    assert result["method"] == "exact enumeration"
    assert result["n_assignments"] == 4
    assert result["p_value"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# small runner helpers
# ---------------------------------------------------------------------------


def test_distance_codes_follow_the_declared_order():
    assert _distance_codes([0.9, 0.15, 0.55], [0.15, 0.55, 0.9]).tolist() == [2, 0, 1]
    with pytest.raises(UnavailableEndpoint, match="not in the declared order"):
        _distance_codes([0.3], [0.15, 0.55, 0.9])


def test_contingency_sums_to_n_and_matches_hand_table():
    table = contingency(np.array([0, 0, 1, 1, 1]), np.array([0, 1, 0, 1, 1]), 2, 2)
    assert table == [[1, 1], [1, 2]]
    assert sum(map(sum, table)) == 5


def test_paired_bootstrap_mean_is_reproducible_and_brackets_mean():
    values = [0.1, -0.2, 0.3, -0.05, 0.15]
    first = paired_bootstrap_mean(values, n_resamples=500, seed=9, alpha=0.05)
    second = paired_bootstrap_mean(values, n_resamples=500, seed=9, alpha=0.05)
    assert first == second
    assert first["low"] <= first["mean"] <= first["high"]
    assert first["mean"] == pytest.approx(float(np.mean(values)))


def test_json_safe_makes_strict_json_payloads():
    payload = {
        "int": np.int64(3),
        "bool": np.bool_(True),
        "nan": float("nan"),
        "arr": np.array([1.0, np.inf]),
    }
    cleaned = json_safe(payload)
    assert cleaned == {"int": 3, "bool": True, "nan": None, "arr": [1.0, None]}
    json.dumps(cleaned, allow_nan=False)


# ---------------------------------------------------------------------------
# archived matched conditions satisfy the declared pairing
# ---------------------------------------------------------------------------


def test_phase5f_seed_keys_match_across_conditions_and_checkpoints():
    data = load_phase5f()
    conditions = list(data["conditions"])
    for checkpoint in data["checkpoints"]:
        reference = np.unique(
            data["conditions"][conditions[0]]["per_checkpoint"][checkpoint][
                "seed_clusters"
            ]
        ).tolist()
        for condition in conditions[1:]:
            other = np.unique(
                data["conditions"][condition]["per_checkpoint"][checkpoint][
                    "seed_clusters"
                ]
            ).tolist()
            assert match_keys(reference, other, label="seeds") == sorted(reference)


def test_phase5f_checkpoint_zero_is_exactly_matched_between_arms():
    data = load_phase5f()
    fixed = per_seed_mi(
        data["conditions"]["fixed_complete"]["per_checkpoint"]["0"]
    )
    plastic = per_seed_mi(
        data["conditions"]["plastic_complete"]["per_checkpoint"]["0"]
    )
    assert fixed == plastic


def test_phase5e_shared_cue_streams_and_missing_actions_are_declared():
    data = load_phase5e()
    reference = data["conditions"]["A"]["cue"]
    for condition in "BCDF":
        assert np.array_equal(reference, data["conditions"][condition]["cue"])
    assert np.all(data["conditions"]["G"]["action"] < 0)
    assert math.isfinite(data["conditions"]["A"]["action"].max())
