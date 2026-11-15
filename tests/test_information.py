"""Focused tests for the Phase 6B/6C information package.

Every observation in this file is synthetic and exists only to check the
mathematics against hand-computable answers. No value here enters a research
result.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from information.bias_correction import (
    bias_table,
    entropy_bias_correction,
    mi_bias_floor,
    required_sample_size,
)
from information.diagnostics import (
    PROVENANCE,
    degeneracy,
    effective_sample_size,
    support_table,
)
from information.discretization import (
    MISSING,
    categorical,
    count_capped,
    equal_width,
    ordinal_thresholds,
    quantile,
)
from information.entropy import (
    conditional_entropy,
    entropy,
    entropy_from_counts,
    entropy_report,
    joint_entropy,
    joint_entropy_report,
    observed_counts,
)
from information.mutual_information import (
    conditional_mutual_information,
    conditional_mutual_information_report,
    mutual_information,
    mutual_information_report,
)
from information.permutation import (
    cluster_bootstrap_ci,
    entropy_bootstrap_ci,
    permutation_null,
)

LN2 = math.log(2.0)


def test_constant_variable_zero_entropy():
    assert entropy([2, 2, 2, 2, 2]) == pytest.approx(0.0, abs=1e-12)


def test_fair_coin_one_bit():
    assert entropy([0, 1, 0, 1]) == pytest.approx(1.0, abs=1e-12)


def test_uniform_four_two_bits():
    assert entropy([0, 1, 2, 3]) == pytest.approx(2.0, abs=1e-12)


def test_uniform_eight_three_bits():
    assert entropy(list(range(8))) == pytest.approx(3.0, abs=1e-12)


def test_skewed_binary_matches_hand_value():
    p = 0.75
    expected = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
    codes = [0] * 75 + [1] * 25
    assert entropy(codes) == pytest.approx(expected, abs=1e-12)


def test_maximum_entropy_for_declared_support():
    coded = categorical([0, 1, 2, 3], "x")
    report = entropy_report(coded)
    assert report["H_plugin"] == pytest.approx(2.0, abs=1e-12)
    assert report["H_max_declared"] == pytest.approx(2.0, abs=1e-12)
    assert report["coverage"] == pytest.approx(1.0)


def test_joint_entropy_of_independent_variables_is_sum():
    x = [0, 0, 1, 1]
    y = [0, 1, 0, 1]
    assert joint_entropy(x, y) == pytest.approx(2.0, abs=1e-12)
    assert entropy(x) + entropy(y) == pytest.approx(2.0, abs=1e-12)


def test_joint_entropy_of_identical_variable_equals_marginal():
    x = [0, 1, 2, 3] * 2
    assert joint_entropy(x, x) == pytest.approx(entropy(x), abs=1e-12)


def test_conditional_entropy_of_identical_is_zero():
    x = [0, 1, 2, 3] * 3
    assert conditional_entropy(x, x) == pytest.approx(0.0, abs=1e-12)


def test_conditional_entropy_of_independent_equals_marginal():
    x = [0, 0, 1, 1] * 4
    y = [0, 1, 0, 1] * 4
    assert conditional_entropy(x, y) == pytest.approx(1.0, abs=1e-12)


def test_mutual_information_perfect_dependence():
    x = [0, 1, 2, 3] * 5
    assert mutual_information(x, x) == pytest.approx(2.0, abs=1e-12)


def test_mutual_information_independent_is_zero():
    x = [0, 0, 1, 1] * 10
    y = [0, 1, 0, 1] * 10
    assert mutual_information(x, y) == pytest.approx(0.0, abs=1e-12)


def test_mutual_information_is_symmetric():
    rng = np.random.default_rng(7)
    x = rng.integers(0, 3, 400)
    y = rng.integers(0, 4, 400)
    assert mutual_information(x, y) == pytest.approx(mutual_information(y, x), abs=1e-12)


def test_mutual_information_is_non_negative():
    rng = np.random.default_rng(11)
    for _ in range(20):
        x = rng.integers(0, 5, 50)
        y = rng.integers(0, 5, 50)
        assert mutual_information(x, y) >= 0.0


def test_mutual_information_hand_checked_two_by_two():
    # Cell counts [[30, 10], [10, 30]] of n=80.
    x = [0] * 40 + [1] * 40
    y = [0] * 30 + [1] * 10 + [0] * 10 + [1] * 30
    hx = 1.0
    hy = 1.0
    cells = np.array([30, 10, 10, 30]) / 80.0
    hxy = float(-np.sum(cells * np.log2(cells)))
    assert mutual_information(x, y) == pytest.approx(hx + hy - hxy, abs=1e-12)


def test_equal_width_bins_are_deterministic_and_ordered():
    first = equal_width([0.0, 0.5, 1.0, 2.0], 2, "v")
    second = equal_width([0.0, 0.5, 1.0, 2.0], 2, "v")
    assert first.codes.tolist() == second.codes.tolist() == [0, 0, 1, 1]
    assert first.n_bins == 2
    assert first.summary()["spec"]["kind"] == "equal_width"


def test_equal_width_boundary_belongs_to_upper_bin():
    coded = equal_width([0.0, 0.5, 1.0], 2, "v")
    assert coded.codes.tolist() == [0, 1, 1]


def test_ordinal_thresholds_partition_exactly():
    coded = ordinal_thresholds([0.1, 0.4, 0.9], [0.5, 0.8], "d")
    assert coded.codes.tolist() == [0, 0, 2]


def test_quantile_bins_balance_counts():
    values = list(np.linspace(0, 1, 100))
    coded = quantile(values, 4, "v")
    counts = np.bincount(coded.codes, minlength=4)
    assert counts.tolist() == [25, 25, 25, 25]


def test_count_capped_saturates():
    coded = count_capped([0, 1, 2, 3, 9], cap=3, name="c")
    assert coded.codes.tolist() == [0, 1, 2, 3, 3]
    assert coded.n_bins == 4


def test_missing_values_are_excluded_not_imputed():
    coded = categorical(["a", None, "b", "a"], "x")
    assert coded.n_missing == 1
    assert set(coded.codes.tolist()) <= {0, 1, MISSING}
    report = entropy_report(coded)
    assert report["n"] == 3
    assert report["n_missing"] == 1


def test_all_missing_variable_is_rejected_by_discretisation():
    with pytest.raises(ValueError, match="no usable observations"):
        categorical([None, None], "x")


def test_all_missing_codes_report_empty_support():
    report = entropy_report(np.array([MISSING, MISSING]))
    assert report["n"] == 0
    assert math.isnan(report["H_plugin"])


def test_observed_counts_ignore_missing_sentinel():
    counts = observed_counts([0, 0, MISSING, 1])
    assert counts.tolist() == [2, 1]


def test_entropy_from_counts_hand_value():
    assert entropy_from_counts(np.array([1, 1, 1, 1])) == pytest.approx(2.0)


def test_miller_madow_correction_hand_value():
    expected = (2 - 1) / (2 * 4 * LN2)
    report = entropy_report(categorical([0, 1, 0, 1], "x"))
    assert report["H_miller_madow"] - report["H_plugin"] == pytest.approx(expected, abs=1e-7)


def test_bias_correction_helpers_hand_values():
    assert entropy_bias_correction(2, 4) == pytest.approx(1 / (8 * LN2), abs=1e-12)
    assert mi_bias_floor(2, 2, 100) == pytest.approx(1 / (200 * LN2), abs=1e-12)
    assert mi_bias_floor(1, 5, 100) == 0.0
    assert required_sample_size(4, 4, 0.01) == 650
    assert required_sample_size(4, 4, 0.10) == 65


def test_bias_table_is_monotone_decreasing():
    table = bias_table([10, 100, 1000], 4, 4)
    values = [row["bias_floor_bits"] for row in table]
    assert values == sorted(values, reverse=True)


def test_joint_entropy_report_matches_manual_product():
    x = [0, 1] * 10
    y = [0, 1] * 10
    report = joint_entropy_report(x, y)
    assert report["k_declared_product"] == 4
    assert report["H_joint_plugin"] == pytest.approx(1.0, abs=1e-12)


def test_mutual_information_report_flags_small_samples():
    report = mutual_information_report([0, 1] * 5, [0, 1] * 5)
    assert report["I_plugin"] == pytest.approx(1.0, abs=1e-12)
    assert report["bias_floor"] == pytest.approx(mi_bias_floor(2, 2, 10))
    assert report["I_corrected"] < report["I_plugin"]
    assert any("sample size" in warning for warning in report["warnings"])


def test_mutual_information_report_withholds_normalised_mi_for_constant():
    report = mutual_information_report([0, 0, 0, 0], [0, 1, 0, 1])
    assert report["I_plugin"] == pytest.approx(0.0)
    assert report["normalised_mi"] is None


def _dependent_pair(n=400, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 4, n)
    return x, np.where(rng.random(n) < 0.9, x, rng.integers(0, 4, n))


def test_permutation_is_reproducible_for_a_fixed_seed():
    x, y = _dependent_pair()
    first = permutation_null(x, y, scheme="free", n_permutations=200, seed=99)
    second = permutation_null(x, y, scheme="free", n_permutations=200, seed=99)
    assert first == second
    assert first["observed"] == pytest.approx(mutual_information(x, y))


def test_permutation_null_has_small_p_for_strong_dependence():
    x, y = _dependent_pair()
    result = permutation_null(x, y, scheme="free", n_permutations=500, seed=5)
    assert result["p_value"] < 0.01
    assert result["observed"] > result["null_max"]


def test_permutation_null_has_large_p_for_independence():
    rng = np.random.default_rng(21)
    x = rng.integers(0, 4, 400)
    y = rng.integers(0, 4, 400)
    result = permutation_null(x, y, scheme="free", n_permutations=500, seed=5)
    assert result["p_value"] > 0.05


def test_block_permutation_requires_clusters():
    with pytest.raises(ValueError, match="cluster"):
        permutation_null([0, 1], [0, 1], scheme="block", n_permutations=10)


def test_permutation_rejects_unknown_scheme_and_bad_sizes():
    with pytest.raises(ValueError, match="scheme"):
        permutation_null([0, 1], [0, 1], scheme="shuffle", n_permutations=10)
    with pytest.raises(ValueError, match="n_permutations"):
        permutation_null([0, 1], [0, 1], scheme="free", n_permutations=0)


def test_block_permutation_preserves_within_cluster_pairs():
    # Each cluster is internally dependent; the block null keeps that pairing.
    clusters = np.repeat(np.arange(20), 10)
    base = np.tile(np.arange(10) % 2, 20)
    result = permutation_null(base, base, clusters=clusters, n_permutations=50, seed=2)
    assert result["observed"] == pytest.approx(1.0, abs=1e-9)
    assert result["p_value"] < 0.05
    assert result["n_clusters"] == 20


def test_bootstrap_ci_is_reproducible_and_brackets_the_estimate():
    x, y = _dependent_pair()
    clusters = np.repeat(np.arange(20), 20)
    first = cluster_bootstrap_ci(x, y, clusters, n_resamples=200, seed=7)
    second = cluster_bootstrap_ci(x, y, clusters, n_resamples=200, seed=7)
    assert first == second
    assert first["low"] <= mutual_information(x, y) <= first["high"]


def test_bootstrap_ci_collapses_for_a_constant_variable():
    x = np.zeros(40, dtype=np.int64)
    y = np.tile([0, 1, 2, 3], 10)
    result = cluster_bootstrap_ci(x, y, np.repeat(np.arange(4), 10), n_resamples=100)
    assert result["low"] == pytest.approx(0.0)
    assert result["high"] == pytest.approx(0.0)


def test_conditional_mi_removes_an_entirely_confounding_stratum():
    # x and y are independent inside each stratum; the marginal association
    # comes from the stratum alone.
    x = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    y = np.array([0, 1, 0, 1, 2, 3, 2, 3])
    z = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    assert mutual_information(x, y) == pytest.approx(1.0, abs=1e-12)
    assert conditional_mutual_information(x, y, z, min_stratum_n=4) == pytest.approx(0.0, abs=1e-12)
    report = conditional_mutual_information_report(x, y, z, min_stratum_n=4)
    assert len(report["strata"]) == 2
    assert report["stratified_support_fraction"] == pytest.approx(1.0)


def test_conditional_mi_report_marks_unsupported_strata():
    x = [0, 1] * 30
    y = [0, 1] * 30
    z = [0] * 58 + [1, 1]
    report = conditional_mutual_information_report(x, y, z, min_stratum_n=20)
    assert report["stratified_support_fraction"] < 1.0
    assert any("below minimum" in warning for warning in report["warnings"])


def test_conditional_mi_can_exceed_the_marginal():
    # The pooled table is independent, but x and y are perfectly related
    # inside each stratum. Conditioning therefore adds information.
    x = np.array([0, 1, 0, 1])
    y = np.array([0, 1, 1, 0])
    z = np.array([0, 0, 1, 1])
    assert mutual_information(x, y) == pytest.approx(0.0, abs=1e-12)
    assert conditional_mutual_information(x, y, z, min_stratum_n=2) == pytest.approx(1.0)


def test_conditional_mi_is_never_negative():
    rng = np.random.default_rng(31)
    x = rng.integers(0, 3, 600)
    z = rng.integers(0, 2, 600)
    y = np.where(rng.random(600) < 0.5, x, z)
    conditional = conditional_mutual_information(x, y, z, min_stratum_n=50)
    assert conditional >= 0.0


def test_effective_sample_size_counts_clusters():
    stats = effective_sample_size(np.repeat(np.arange(4), 5))
    assert stats["n"] == 20
    assert stats["n_clusters"] == 4
    assert stats["mean_cluster_size"] == pytest.approx(5.0)
    assert stats["clustered"] is True


def test_degeneracy_identifies_constant_and_empty_variables():
    assert degeneracy([1, 1, 1])["state"] == "constant"
    assert degeneracy([MISSING, MISSING])["state"] == "empty"
    assert degeneracy([0, 1])["state"] == "variable"


def test_support_table_flags_sparse_cells():
    assert support_table(4, 4, 400)["sparse"] is False
    assert support_table(4, 4, 40)["sparse"] is True


def test_statistics_helpers_are_reused_from_phase_5():
    from information.statistics import holm, sign_flip_test, summarise

    result = holm({"a": 0.01, "b": 0.04}, 0.05)
    assert result["adjusted"]["a"] == pytest.approx(0.02)
    flipped = sign_flip_test([1.0] * 8, exact_max_n=12, draws=100, seed=1)
    assert flipped["p_value"] < 0.05
    assert summarise([1, 2, 3])["mean"] == pytest.approx(2.0)


def test_provenance_labels_are_declared():
    assert set(PROVENANCE) == {"recorded", "measured", "simulated", "derived"}


def test_entropy_bootstrap_ci_is_degenerate_for_a_balanced_binary():
    result = entropy_bootstrap_ci([0, 1] * 20, np.repeat(np.arange(5), 8), n_resamples=100)
    assert result["low"] == pytest.approx(1.0)
    assert result["high"] == pytest.approx(1.0)
    assert result["n_clusters"] == 5
