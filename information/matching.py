"""Validation of matched observations before any information estimate.

Matched comparisons are only meaningful when both sides describe the same
observational units. These helpers fail loudly on unequal lengths, duplicate
keys, missing keys or incomplete clusters instead of silently dropping rows.
They never reorder or impute data.
"""

from __future__ import annotations

import numpy as np


def validate_equal_lengths(**arrays) -> dict:
    """Require every supplied array to have the same first-axis length."""
    if not arrays:
        raise ValueError("provide at least one array")
    lengths = {name: int(len(value)) for name, value in arrays.items()}
    distinct = set(lengths.values())
    if len(distinct) != 1:
        detail = ", ".join(f"{name}={size}" for name, size in lengths.items())
        raise ValueError(f"matched arrays have unequal lengths: {detail}")
    return lengths


def match_keys(left_keys, right_keys, *, label: str = "observations") -> list:
    """Return the sorted keys present exactly once on both sides.

    A duplicate key is ambiguous and therefore rejected. A key present on one
    side only is a missing observation and also rejected.
    """
    left = list(left_keys)
    right = list(right_keys)
    if not left or not right:
        raise ValueError(f"{label} keys are empty")
    if len(set(left)) != len(left):
        raise ValueError(f"{label} left keys contain duplicates")
    if len(set(right)) != len(right):
        raise ValueError(f"{label} right keys contain duplicates")
    left_set = set(left)
    right_set = set(right)
    only_left = sorted(left_set - right_set, key=repr)
    only_right = sorted(right_set - left_set, key=repr)
    if only_left or only_right:
        raise ValueError(
            f"{label} keys do not match: only left={only_left}, "
            f"only right={only_right}"
        )
    return sorted(left_set, key=repr)


def validate_cluster_coverage(clusters, expected_clusters, *, label: str = "clusters") -> dict:
    """Check that every expected cluster is present at least once."""
    codes = np.asarray(clusters)
    if codes.ndim != 1:
        raise ValueError(f"{label} must be one-dimensional")
    present = {str(value) for value in np.unique(codes).tolist()}
    expected = {str(value) for value in expected_clusters}
    missing = sorted(expected - present)
    unexpected = sorted(present - expected)
    if missing or unexpected:
        raise ValueError(
            f"{label} coverage mismatch: missing={missing}, unexpected={unexpected}"
        )
    return {
        "n_observations": int(codes.size),
        "n_clusters": len(present),
        "clusters": sorted(present),
    }
