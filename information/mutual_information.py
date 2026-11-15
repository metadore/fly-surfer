"""Mutual information between discrete variables, in bits.

``I(X;Y) = H(X) + H(Y) - H(X,Y)`` is estimated with the plug-in estimator and
reported next to its analytic bias floor ``(k_x-1)(k_y-1)/(2 N ln 2)``. The
corrected value is the plug-in estimate minus that floor, clipped at zero; it
is a first-order correction, never a substitute for adequate sample size.

``I(X;Y|Z)`` is the sample-weighted mean of the within-stratum estimates. A
stratum whose sample count cannot support its table contributes a warning, not
a silently pooled guess.
"""

from __future__ import annotations

import numpy as np

from information.bias_correction import mi_bias_floor
from information.entropy import (
    _codes,
    _k_declared,
    entropy,
    entropy_from_counts,
    joint_codes,
    joint_entropy,
    observed_counts,
)


def mutual_information(x, y) -> float:
    """Plug-in mutual information I(X;Y) in bits."""
    a = _codes(x)
    b = _codes(y)
    if a.shape != b.shape:
        raise ValueError("mutual information needs equal-length variables")
    mask = (a >= 0) & (b >= 0)
    if not np.any(mask):
        return float("nan")
    hx = entropy(a[mask])
    hy = entropy(b[mask])
    hxy = joint_entropy(a[mask], b[mask])
    return float(max(0.0, hx + hy - hxy))


def _normalised(mi: float, hx: float, hy: float, floor_bits: float) -> float | None:
    denominator = min(hx, hy)
    if not np.isfinite(denominator) or denominator <= floor_bits:
        return None
    return float(mi / denominator)


def mutual_information_report(x, y, *, min_entropy_bits: float = 0.05) -> dict:
    """Full MI report: raw, bias floor, corrected, normalised, warnings."""
    a = _codes(x)
    b = _codes(y)
    if a.shape != b.shape:
        raise ValueError("mutual information needs equal-length variables")
    mask = (a >= 0) & (b >= 0)
    n = int(np.count_nonzero(mask))
    kx = max(1, int(_k_declared(x, a)))
    ky = max(1, int(_k_declared(y, b)))
    warnings: list[str] = []

    if n == 0:
        return {
            "n": 0,
            "n_missing": int(a.size),
            "k_declared_x": kx,
            "k_declared_y": ky,
            "I_plugin": float("nan"),
            "bias_floor": float("nan"),
            "I_corrected": float("nan"),
            "normalised_mi": None,
            "uncertainty_coefficient": None,
            "log_base": 2,
            "estimator": "plug-in",
            "warnings": ["no complete observations"],
        }

    ax = a[mask]
    by = b[mask]
    counts_x = observed_counts(ax, kx)
    counts_y = observed_counts(by, ky)
    counts_xy = observed_counts(joint_codes(ax, by))
    hx = entropy_from_counts(counts_x)
    hy = entropy_from_counts(counts_y)
    hxy = entropy_from_counts(counts_xy)
    mi = float(max(0.0, hx + hy - hxy))
    floor = float(mi_bias_floor(kx, ky, n))
    corrected = float(max(0.0, mi - floor))

    if min(hx, hy) < min_entropy_bits:
        warnings.append(
            "marginal entropy below floor; normalised MI withheld"
        )
    if floor > 0.5 * mi and mi > 0:
        warnings.append(
            "bias floor exceeds half the plug-in estimate; treat as exploratory"
        )
    if n < 5 * kx * ky:
        warnings.append(
            "fewer than 5 observations per table cell; sample size unsupported"
        )

    norm = _normalised(mi, hx, hy, min_entropy_bits)
    return {
        "n": n,
        "n_missing": int(a.size) - n,
        "k_declared_x": kx,
        "k_declared_y": ky,
        "k_observed_x": int(np.count_nonzero(counts_x)),
        "k_observed_y": int(np.count_nonzero(counts_y)),
        "k_observed_joint": int(np.count_nonzero(counts_xy)),
        "H_x": round(hx, 8),
        "H_y": round(hy, 8),
        "H_joint": round(hxy, 8),
        "I_plugin": round(mi, 8),
        "bias_floor": round(floor, 8),
        "I_corrected": round(corrected, 8),
        "normalised_mi": None if norm is None else round(norm, 8),
        "uncertainty_coefficient": (
            None if min(hx, hy) <= min_entropy_bits else round(mi / hy, 8)
        ),
        "log_base": 2,
        "estimator": "plug-in + analytic bias floor",
        "warnings": warnings,
    }


def conditional_mutual_information(x, y, z, *, min_stratum_n: int = 20) -> float:
    """I(X;Y|Z) as the sample-weighted mean of within-stratum I(X;Y)."""
    return conditional_mutual_information_report(x, y, z, min_stratum_n=min_stratum_n)[
        "I_conditional"
    ]


def conditional_mutual_information_report(
    x, y, z, *, min_stratum_n: int = 20
) -> dict:
    """Per-stratum MI, sample weights, support warnings and weighted total."""
    a = _codes(x)
    b = _codes(y)
    c = _codes(z)
    if not (a.shape == b.shape == c.shape):
        raise ValueError("conditional mutual information needs equal-length variables")
    mask = (a >= 0) & (b >= 0) & (c >= 0)
    n_total = int(np.count_nonzero(mask))
    if n_total == 0:
        return {
            "I_conditional": float("nan"),
            "n": 0,
            "strata": [],
            "warnings": ["no complete observations"],
            "log_base": 2,
        }
    a, b, c = a[mask], b[mask], c[mask]
    strata = []
    warnings: list[str] = []
    total = 0.0
    supported_weight = 0.0
    for stratum in np.unique(c):
        sel = c == stratum
        n_s = int(np.count_nonzero(sel))
        report = mutual_information_report(a[sel], b[sel])
        support_ok = n_s >= min_stratum_n
        if not support_ok:
            warnings.append(
                f"stratum {int(stratum)} has n={n_s} below minimum {min_stratum_n}"
            )
        if not np.isfinite(report["I_plugin"]):
            warnings.append(f"stratum {int(stratum)} has no estimable MI")
            continue
        weight = n_s / n_total
        total += weight * report["I_plugin"]
        if support_ok:
            supported_weight += weight
        strata.append(
            {
                "stratum": int(stratum),
                "n": n_s,
                "weight": round(weight, 6),
                "I_plugin": report["I_plugin"],
                "bias_floor": report["bias_floor"],
                "support_ok": support_ok,
            }
        )
    return {
        "I_conditional": round(total, 8),
        "n": n_total,
        "stratified_support_fraction": round(supported_weight, 6),
        "strata": strata,
        "warnings": warnings,
        "log_base": 2,
        "estimator": "sample-weighted mean of plug-in stratum MI",
    }
