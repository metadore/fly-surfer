"""Population codes and descriptive information aggregation.

One observation is a whole row of per-neuron counts or per-pool activity. The
code is built from the row, so individual spikes are never promoted to
independent trials. Ties in row ordering are resolved by lexicographic sorting
of the full vector, which makes the mapping independent of input order.

These helpers estimate nothing. They only turn matched population responses
into declared discrete codes so that the existing entropy and MI estimators can
be applied once per independent observation.
"""

from __future__ import annotations

import numpy as np

from information.discretization import MISSING, Discretized, ordinal_thresholds


def _row_matrix(values, name: str) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional array of rows")
    if arr.shape[1] < 1:
        raise ValueError(f"{name} must have at least one column")
    if arr.shape[0] == 0:
        raise ValueError(f"{name} is empty")
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"{name} must contain numeric values")
    return arr


def _usable_rows(arr: np.ndarray) -> np.ndarray:
    """A row is usable when every entry is finite and non-negative."""
    return np.all(np.isfinite(arr) & (arr >= 0), axis=1)


def pattern_codes(
    values,
    *,
    name: str = "population_pattern",
    cap: int | None = None,
    binary: bool = False,
    labels: tuple[str, ...] | list[str] | None = None,
) -> Discretized:
    """Discretise each whole population vector as one level.

    ``cap`` saturates counts before coding. ``binary`` reduces every entry to
    zero versus positive. A row with any non-finite or negative entry is
    marked missing; it is never repaired or partially used.
    """
    arr = _row_matrix(values, name)
    if cap is not None and int(cap) < 1:
        raise ValueError("cap must be at least one")
    usable = _usable_rows(arr)
    if not np.any(usable):
        raise ValueError(f"{name} has no usable observations")
    coded_values = arr[usable].astype(np.int64, copy=True)
    if binary:
        coded_values = (coded_values > 0).astype(np.int64)
    elif cap is not None:
        coded_values = np.clip(coded_values, 0, int(cap))

    unique, inverse = np.unique(coded_values, axis=0, return_inverse=True)
    generated = tuple("|".join(str(int(v)) for v in row) for row in unique)
    if labels is not None:
        declared = tuple(labels)
        if len(declared) != unique.shape[0]:
            raise ValueError(
                f"{name} declares {len(declared)} labels for "
                f"{unique.shape[0]} observed patterns"
            )
    else:
        declared = generated

    codes = np.full(arr.shape[0], MISSING, dtype=np.int64)
    codes[usable] = inverse
    spec = {
        "name": name,
        "kind": "population_pattern",
        "rows": int(arr.shape[0]),
        "columns": int(arr.shape[1]),
        "binary": bool(binary),
        "cap": None if cap is None else int(cap),
        "observed_patterns": [list(map(int, row)) for row in unique],
    }
    return Discretized(codes, declared, spec, int(np.count_nonzero(~usable)))


def level_pattern_codes(
    values,
    thresholds,
    *,
    name: str = "population_level_pattern",
) -> Discretized:
    """Code every column with the same ordinal thresholds, then code the row.

    This is the population analogue of ``ordinal_thresholds``: each pool is
    split at declared cut points and the resulting level vector is the code.
    """
    arr = _row_matrix(values, name)
    usable = _usable_rows(arr)
    if not np.any(usable):
        raise ValueError(f"{name} has no usable observations")
    levels = np.full(arr.shape, MISSING, dtype=np.int64)
    for column in range(arr.shape[1]):
        coded = ordinal_thresholds(
            np.where(usable, arr[:, column], np.nan),
            thresholds,
            f"{name}[{column}]",
        )
        levels[:, column] = coded.codes
    level_values = levels[usable]
    unique, inverse = np.unique(level_values, axis=0, return_inverse=True)
    declared = tuple("|".join(str(int(v)) for v in row) for row in unique)
    codes = np.full(arr.shape[0], MISSING, dtype=np.int64)
    codes[usable] = inverse
    spec = {
        "name": name,
        "kind": "population_level_pattern",
        "rows": int(arr.shape[0]),
        "columns": int(arr.shape[1]),
        "thresholds": [float(t) for t in thresholds],
        "observed_patterns": [list(map(int, row)) for row in unique],
    }
    return Discretized(codes, declared, spec, int(np.count_nonzero(~usable)))


def population_information(joint_mi: float, individual_mis) -> dict:
    """Descriptive split of a joint code estimate into single-column estimates.

    This is bookkeeping, not a formal redundancy or synergy decomposition.
    The plug-in estimates are biased upward, both quantities can be affected by
    that bias, and ``sum_individual`` double-counts shared information.
    """
    values = [
        float(v)
        for v in individual_mis
        if v is not None and np.isfinite(float(v))
    ]
    joint = float(joint_mi) if np.isfinite(float(joint_mi)) else None
    if not values or joint is None:
        return {
            "joint_mi_bits": joint,
            "individual_mi_bits": values,
            "max_individual_mi_bits": None,
            "sum_individual_mi_bits": None,
            "joint_minus_max_individual_bits": None,
            "sum_individual_minus_joint_bits": None,
            "interpretation": "descriptive decomposition only",
        }
    maximum = max(values)
    total = float(sum(values))
    return {
        "joint_mi_bits": round(joint, 8),
        "individual_mi_bits": [round(v, 8) for v in values],
        "max_individual_mi_bits": round(maximum, 8),
        "sum_individual_mi_bits": round(total, 8),
        "joint_minus_max_individual_bits": round(joint - maximum, 8),
        "sum_individual_minus_joint_bits": round(total - joint, 8),
        "interpretation": (
            "descriptive decomposition only: sum_individual double-counts "
            "shared information and both terms inherit estimator bias"
        ),
    }
