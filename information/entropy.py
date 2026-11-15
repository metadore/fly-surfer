"""Shannon entropy of discrete variables, in bits.

All estimates use base-2 logarithms. The plug-in (maximum likelihood)
estimator is reported alongside the Miller-Madow correction, which adds
``(K_obs - 1) / (2 N ln 2)`` bits to compensate first-order bias.
"""

from __future__ import annotations

import numpy as np

LN2 = float(np.log(2.0))


def _codes(value) -> np.ndarray:
    codes = value.codes if hasattr(value, "codes") else value
    return np.asarray(codes, dtype=np.int64)


def _k_declared(value, codes: np.ndarray) -> int:
    if hasattr(value, "labels"):
        return len(value.labels)
    if codes.size and codes.max() >= 0:
        return int(codes.max()) + 1
    return 0


def _valid_mask(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones(arrays[0].shape, dtype=bool)
    for arr in arrays:
        mask &= arr >= 0
    return mask


def observed_counts(codes, k: int | None = None) -> np.ndarray:
    arr = _codes(codes)
    arr = arr[arr >= 0]
    if arr.size == 0:
        return np.zeros(0, dtype=np.int64)
    width = int(arr.max()) + 1 if k is None else max(int(k), int(arr.max()) + 1)
    return np.bincount(arr, minlength=width)


def entropy_from_counts(counts: np.ndarray) -> float:
    total = float(counts.sum())
    if total <= 0:
        return float("nan")
    p = counts[counts > 0] / total
    return float(-np.sum(p * np.log2(p)))


def entropy(codes) -> float:
    """Plug-in Shannon entropy H(X) in bits."""
    return entropy_from_counts(observed_counts(codes))


def miller_madow_correction(counts: np.ndarray) -> float:
    observed = int(np.count_nonzero(counts))
    total = float(counts.sum())
    if total <= 0 or observed <= 1:
        return 0.0
    return float((observed - 1) / (2.0 * total * LN2))


def entropy_report(value) -> dict:
    """Entropy estimate with support, correction and coverage diagnostics."""
    codes = _codes(value)
    k_declared = _k_declared(value, codes)
    counts = observed_counts(codes, k_declared or None)
    total = int(counts.sum())
    k_obs = int(np.count_nonzero(counts))
    if total == 0:
        return {
            "n": 0,
            "k_observed": 0,
            "k_declared": k_declared,
            "H_plugin": float("nan"),
            "H_miller_madow": float("nan"),
            "H_max_declared": float("nan"),
            "coverage": 0.0,
            "estimator": "plug-in",
            "log_base": 2,
        }
    h = entropy_from_counts(counts)
    mm = miller_madow_correction(counts)
    h_max = float(np.log2(k_declared)) if k_declared > 1 else 0.0
    return {
        "n": total,
        "n_missing": int(np.count_nonzero(codes < 0)),
        "k_observed": k_obs,
        "k_declared": k_declared,
        "H_plugin": round(h, 8),
        "H_miller_madow": round(h + mm, 8),
        "H_max_declared": round(h_max, 8),
        "coverage": round(k_obs / k_declared, 6) if k_declared else 0.0,
        "estimator": "plug-in + Miller-Madow",
        "log_base": 2,
    }


def joint_codes(x, y) -> np.ndarray:
    """Flatten a pair into one code, preserving the MISSING sentinel."""
    a = _codes(x)
    b = _codes(y)
    if a.shape != b.shape:
        raise ValueError("joint entropy needs equal-length variables")
    ky = int(b[b >= 0].max()) + 1 if np.any(b >= 0) else 1
    out = np.full(a.shape, -1, dtype=np.int64)
    mask = _valid_mask(a, b)
    out[mask] = a[mask] * ky + b[mask]
    return out


def joint_entropy(x, y) -> float:
    """Plug-in joint entropy H(X, Y) in bits."""
    return entropy(joint_codes(x, y))


def joint_entropy_report(x, y) -> dict:
    a = _codes(x)
    b = _codes(y)
    kx = _k_declared(x, a)
    ky = _k_declared(y, b)
    counts = observed_counts(joint_codes(x, y))
    total = int(counts.sum())
    h = entropy_from_counts(counts)
    mm = miller_madow_correction(counts)
    return {
        "n": total,
        "k_declared_product": kx * ky,
        "k_observed": int(np.count_nonzero(counts)),
        "H_joint_plugin": round(h, 8),
        "H_joint_miller_madow": round(h + mm, 8),
        "estimator": "plug-in + Miller-Madow",
    }


def conditional_entropy(x, y) -> float:
    """H(X | Y) = H(X, Y) - H(Y), clipped at zero."""
    joint = joint_entropy(x, y)
    marginal = entropy(y)
    if not np.isfinite(joint) or not np.isfinite(marginal):
        return float("nan")
    return float(max(0.0, joint - marginal))


def entropy_sensitivity(values, transforms) -> list[dict]:
    """Entropy under several declared discretisations of the same values."""
    out = []
    for transform, kwargs in transforms:
        coded = transform(values, **kwargs)
        report = entropy_report(coded)
        report["discretization"] = coded.summary()["spec"]
        out.append(report)
    return out
