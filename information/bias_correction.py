"""Finite-sample bias quantities for entropy and mutual information.

Plug-in mutual information is biased upward by approximately
``(k_x - 1)(k_y - 1) / (2 N ln 2)`` bits. These helpers expose that floor so
that every estimate can be reported raw and corrected, and so that sample
sizes can be planned against a declared tolerance.
"""

from __future__ import annotations

import math

LN2 = math.log(2.0)


def entropy_bias_correction(k_observed: int, n: int) -> float:
    """Miller-Madow first-order entropy bias in bits."""
    if k_observed <= 1 or n <= 0:
        return 0.0
    return (k_observed - 1) / (2.0 * n * LN2)


def mi_bias_floor(kx: int, ky: int, n: int) -> float:
    """Analytic upward bias floor of plug-in MI for a kx-by-ky table."""
    if n <= 0 or kx <= 1 or ky <= 1:
        return 0.0
    return (kx - 1) * (ky - 1) / (2.0 * n * LN2)


def required_sample_size(kx: int, ky: int, tolerance_bits: float) -> int:
    """Smallest N whose bias floor does not exceed ``tolerance_bits``."""
    if tolerance_bits <= 0:
        raise ValueError("tolerance must be positive")
    if kx <= 1 or ky <= 1:
        return 1
    return int(math.ceil((kx - 1) * (ky - 1) / (2.0 * LN2 * tolerance_bits)))


def bias_table(sample_sizes, kx: int, ky: int) -> list[dict]:
    return [
        {"n": int(n), "bias_floor_bits": round(mi_bias_floor(kx, ky, int(n)), 6)}
        for n in sample_sizes
    ]
