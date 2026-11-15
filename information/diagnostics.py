"""Support, effective sample size and provenance diagnostics.

Every information result must state how many observations were actually
usable, how many independent clusters they came from, and whether the
estimand is even identifiable. These helpers produce that record; they never
repair or impute data.
"""

from __future__ import annotations

import numpy as np

from information.entropy import _codes

PROVENANCE = {
    "recorded": "run metadata written by an earlier experiment",
    "measured": "value derived from detector or recorded output",
    "simulated": "value produced by the model",
    "derived": "value computed from other stored quantities",
}


def effective_sample_size(clusters=None, *, n: int | None = None) -> dict:
    """Observation count, cluster count and mean cluster size."""
    if clusters is None:
        if n is None:
            raise ValueError("provide clusters or n")
        return {
            "n": int(n),
            "n_clusters": int(n),
            "mean_cluster_size": 1.0,
            "clustered": False,
        }
    codes = _codes(clusters)
    codes = codes[codes >= 0]
    unique, counts = np.unique(codes, return_counts=True)
    return {
        "n": int(codes.size),
        "n_clusters": int(unique.size),
        "mean_cluster_size": round(float(counts.mean()), 6) if counts.size else 0.0,
        "min_cluster_size": int(counts.min()) if counts.size else 0,
        "max_cluster_size": int(counts.max()) if counts.size else 0,
        "clustered": True,
    }


def degeneracy(codes, name: str = "variable") -> dict:
    """Report whether a variable carries any variation at all."""
    arr = _codes(codes)
    valid = arr[arr >= 0]
    missing = int(arr.size - valid.size)
    unique = np.unique(valid)
    if valid.size == 0:
        state, reason = "empty", "no valid observations"
    elif unique.size == 1:
        state, reason = "constant", f"single observed value {int(unique[0])}"
    else:
        state, reason = "variable", None
    return {
        "name": name,
        "state": state,
        "reason": reason,
        "n": int(arr.size),
        "n_missing": missing,
        "n_observed_levels": int(unique.size),
        "levels": [int(u) for u in unique[:20]],
    }


def support_table(kx: int, ky: int, n: int) -> dict:
    """Expected observations per cell of a kx-by-ky table at sample size n."""
    cells = max(1, kx * ky)
    expected = n / cells
    return {
        "k_declared_x": int(kx),
        "k_declared_y": int(ky),
        "cells": cells,
        "n": int(n),
        "expected_per_cell": round(expected, 4),
        "sparse": bool(expected < 5),
    }
