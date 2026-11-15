"""Multiple-comparison and paired-test helpers.

Phase 5 already defines ``holm`` (family-wise step-down correction) and
``sign_flip_test`` (exact enumeration up to a declared size, seeded Monte
Carlo beyond it). They are re-exported here so information analysis and the
plasticity comparison share one implementation instead of drifting apart.
"""

from __future__ import annotations

from experiments.phase_5.comparative import holm, sign_flip_test

__all__ = ["holm", "sign_flip_test", "summarise"]


def summarise(values) -> dict:
    """Mean, sd, standard error and count of a small sample of numbers."""
    import numpy as np

    numbers = np.asarray([v for v in values if v is not None], dtype=np.float64)
    if numbers.size == 0:
        return {"n": 0, "mean": None, "sd": None, "se": None}
    sd = float(numbers.std(ddof=1)) if numbers.size > 1 else None
    return {
        "n": int(numbers.size),
        "mean": round(float(numbers.mean()), 8),
        "sd": None if sd is None else round(sd, 8),
        "se": None if sd is None else round(float(sd / numbers.size**0.5), 8),
    }
