"""Permutation nulls for discrete mutual information.

Two schemes are provided. ``block`` permutes the second variable only inside
each cluster, so any dependence that lives *between* clusters is removed and
within-cluster dependence is preserved. ``free`` permutes the second variable
globally and destroys all dependence. Clustered observations must use
``block``; treating correlated windows as independent inflates significance.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from information.entropy import _codes
from information.mutual_information import mutual_information

MAX_DRAWS = 20_000


def _p_value(observed: float, null: np.ndarray) -> float:
    null = null[np.isfinite(null)]
    if null.size == 0:
        return float("nan")
    exceed = int(np.count_nonzero(null >= observed))
    return float((exceed + 1) / (null.size + 1))


def permutation_null(
    x,
    y,
    *,
    clusters=None,
    scheme: str = "block",
    n_permutations: int = 5_000,
    seed: int = 20261110,
    exact_max_assignments: int = 0,
) -> dict:
    """Null distribution of I(X;Y) under a declared permutation scheme.

    When ``exact_max_assignments`` is positive and the full set of
    within-group permutations is no larger than that value, the null is
    enumerated exactly instead of sampled. An exact p-value can then be
    smaller than 1/(n_permutations+1), and a Monte Carlo estimate that
    falls below the exact attainable minimum is impossible by construction.
    """
    if scheme not in {"block", "free"}:
        raise ValueError("scheme must be 'block' or 'free'")
    if n_permutations < 1 or n_permutations > MAX_DRAWS:
        raise ValueError(f"n_permutations must be in 1..{MAX_DRAWS}")
    a = _codes(x)
    b = _codes(y)
    mask = (a >= 0) & (b >= 0)
    a, b = a[mask], b[mask]
    observed = mutual_information(a, b)
    if scheme == "free":
        if clusters is not None:
            c = _codes(clusters)[mask]
            n_clusters = int(np.unique(c).size)
        else:
            n_clusters = 1
        groups = [np.arange(a.size)]
    elif clusters is None:
        raise ValueError("block permutation requires clusters")
    else:
        c = _codes(clusters)[mask]
        groups = [np.flatnonzero(c == value) for value in np.unique(c)]
        n_clusters = len(groups)

    total_assignments = math.prod(math.factorial(group.size) for group in groups)
    if exact_max_assignments and total_assignments <= int(exact_max_assignments):
        per_group = [
            list(itertools.permutations(b[group].tolist())) for group in groups
        ]
        null = np.empty(int(total_assignments), dtype=np.float64)
        for position, combination in enumerate(itertools.product(*per_group)):
            shuffled = b.copy()
            for group, values in zip(groups, combination):
                shuffled[group] = values
            null[position] = mutual_information(a, shuffled)
        exceed = int(np.count_nonzero(null >= observed))
        p_value = exceed / null.size
        method = "exact enumeration"
        n_assignments = int(null.size)
    else:
        rng = np.random.default_rng(seed)
        null = np.empty(n_permutations, dtype=np.float64)
        for index in range(n_permutations):
            shuffled = b.copy()
            for group in groups:
                shuffled[group] = rng.permutation(shuffled[group])
            null[index] = mutual_information(a, shuffled)
        p_value = _p_value(observed, null)
        method = "Monte Carlo permutation"
        n_assignments = int(n_permutations)

    finite = null[np.isfinite(null)]
    return {
        "observed": round(float(observed), 8),
        "scheme": scheme,
        "method": method,
        "n_permutations": int(n_permutations),
        "n_assignments": n_assignments,
        "n_clusters": n_clusters,
        "n_permutation_groups": len(groups),
        "null_mean": round(float(finite.mean()), 8) if finite.size else None,
        "null_sd": round(float(finite.std(ddof=1)), 8) if finite.size > 1 else None,
        "null_q95": round(float(np.quantile(finite, 0.95)), 8) if finite.size else None,
        "null_max": round(float(finite.max()), 8) if finite.size else None,
        "p_value": round(p_value, 8),
        "seed": int(seed),
        "log_base": 2,
    }


def cluster_bootstrap_ci(
    x,
    y,
    clusters,
    *,
    n_resamples: int = 2_000,
    seed: int = 20261110,
    alpha: float = 0.05,
) -> dict:
    """Percentile CI of I(X;Y) resampling clusters with replacement."""
    a = _codes(x)
    b = _codes(y)
    c = _codes(clusters)
    if not (a.shape == b.shape == c.shape):
        raise ValueError("bootstrap needs equal-length variables")
    mask = (a >= 0) & (b >= 0) & (c >= 0)
    a, b, c = a[mask], b[mask], c[mask]
    unique = np.unique(c)
    rng = np.random.default_rng(seed)
    draws = np.empty(n_resamples, dtype=np.float64)
    for index in range(n_resamples):
        picked = rng.choice(unique, size=unique.size, replace=True)
        ax = np.concatenate([a[c == value] for value in picked])
        by = np.concatenate([b[c == value] for value in picked])
        draws[index] = mutual_information(ax, by)
    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        return {"low": None, "high": None, "n_resamples": n_resamples}
    return {
        "low": round(float(np.quantile(finite, alpha / 2)), 8),
        "high": round(float(np.quantile(finite, 1 - alpha / 2)), 8),
        "n_resamples": int(n_resamples),
        "n_clusters": int(unique.size),
        "seed": int(seed),
    }


def entropy_bootstrap_ci(
    codes,
    clusters,
    *,
    n_resamples: int = 2_000,
    seed: int = 20261110,
    alpha: float = 0.05,
) -> dict:
    """Percentile CI of H(X) resampling clusters with replacement."""
    from information.entropy import entropy

    a = _codes(codes)
    c = _codes(clusters)
    if a.shape != c.shape:
        raise ValueError("bootstrap needs equal-length variables")
    mask = (a >= 0) & (c >= 0)
    a, c = a[mask], c[mask]
    unique = np.unique(c)
    rng = np.random.default_rng(seed)
    draws = np.empty(n_resamples, dtype=np.float64)
    for index in range(n_resamples):
        picked = rng.choice(unique, size=unique.size, replace=True)
        draws[index] = entropy(np.concatenate([a[c == value] for value in picked]))
    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        return {"low": None, "high": None, "n_resamples": n_resamples}
    return {
        "low": round(float(np.quantile(finite, alpha / 2)), 8),
        "high": round(float(np.quantile(finite, 1 - alpha / 2)), 8),
        "n_resamples": int(n_resamples),
        "n_clusters": int(unique.size),
        "seed": int(seed),
    }
