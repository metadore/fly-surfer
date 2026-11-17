"""Phase 8 statistical analysis (G6, REV3 §7 and §10.11).

The analysis is a pure function of the append-only episode store and the
declared configuration. It computes:

* the primary outcome per seed (mean capped survival score over paired
  episodes) and the **exact two-sided sign-flip permutation test** over all
  ``2^N`` sign vectors — no normal approximation, no Monte Carlo;
* the robustness two-sided exact sign test with zeros dropped for that check
  only;
* paired percentile bootstrap over seeds, paired mean and median difference,
  Cohen's dz, and win/loss/tie counts;
* Holm–Bonferroni over the declared confirmatory family, with both m = 4 and
  m = 3 supported and the family size supplied by the caller (U14 is a human
  decision, never a default here);
* the floor, F/Fβ/A and F/F-init decompositions, the E1–E5 checklist and the
  A′/C′ identity comparison from the stored rows.

Every threshold that depends on N is recomputed at the **actual number of
complete pairs**. A contrast whose complete-pair N falls below the predeclared
fallback N is not tested: the campaign is reported as a design failure and the
confirmatory family is withheld (REV3 §7.3, rule 4).

Zero differences are retained; a seed whose arms both floor contributes
``d = 0`` and can never distinguish them. All-zero differences therefore give
``p = 1.0`` and the output says "no difference detectable", never
"equivalent".

The exact test is enumerated with integer arithmetic so that the boundary
comparison ``|T(s)| >= |T_obs|`` is exact, not subject to float rounding.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from math import comb, lcm, sqrt
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .config import CampaignConfig, Phase8Config
from .registry import Registry, build_registry, confirmatory_contrasts
from .schema import validate_rows

ANALYSIS_VERSION = 1
PROTOCOL_ID = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"

# REV3 §7.4, declared constants. They are z-based coefficients, not fitted.
MDE_COEFFICIENT = 2.801585  # z_0.975 + z_0.80
HOLM_STEP1_COEFFICIENT = 3.3393  # alpha/m = 0.0125, m = 4 (REV3 §7.4)
ASSUMED_SIGMA_UPDATES = 60.0  # REV3 §7.4 assumption, not a measurement

# REV3 §3.6.4, declared thresholds.
E3_MIN_DECISION_FRACTION = 0.01
E3_MIN_SEED_FRACTION = 0.5
E4_MIN_MOTOR_DRIVEN_FRACTION = 0.10

# The protocol enumerates at N <= 16. The cap keeps the analysis from silently
# running an unplanned design and bounds memory; it is not a scientific choice.
MAX_ENUMERATED_SEEDS = 18

# REV3 §5.4. These are reported, never promoted to confirmatory.
SECONDARY_CONTRASTS = (
    {
        "id": "D_minus_C",
        "minuend": "D",
        "subtrahend": "C",
        "status": "exploratory",
        "question": "plasticity on the random substrate, completing the 2x2",
    },
    {
        "id": "E_full_minus_E",
        "minuend": "E_full",
        "subtrahend": "E",
        "status": "exploratory",
        "question": "value of the seven unmapped features",
    },
    {
        "id": "A_minus_E",
        "minuend": "A",
        "subtrahend": "E",
        "status": "explanatory reference",
        "question": "the biological substrate against the conventional learner",
    },
)

# Fields that can be compared from the stored rows. P1/P2/P5/P10 of REV3
# §3.8.3 are full sequences; the store keeps their SHA-256 digests (P3/P4) and
# the per-decision summaries, so the exact-sequence comparison belongs to the
# artifact-level replay check and is named as such in the output.
IDENTITY_FIELDS = (
    "steps",
    "observed_updates",
    "survival_score",
    "total_reward",
    "terminated",
    "truncated",
    "termination_reason",
    "action_counts",
    "no_action_fraction",
    "motor_spikes",
    "spike_sha256",
    "action_sha256",
    "weights_before",
    "weights_after",
    "decision_classes",
    "motor_summary",
)


class AnalysisError(ValueError):
    """The analysis cannot be computed as the protocol declares it."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _ratio(value: int, denominator: int) -> Fraction:
    if denominator <= 0:
        raise AnalysisError("a ratio needs a positive denominator")
    return Fraction(int(value), int(denominator))


def _payload(value: Fraction | None) -> dict | None:
    """A p-value both as a float and as the exact rational."""
    if value is None:
        return None
    if value < 0 or value > 1:
        raise AnalysisError(f"a p-value left [0, 1]: {value}")
    return {
        "value": float(value),
        "exact": f"{value.numerator}/{value.denominator}",
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _mean(values: Sequence[Fraction]) -> Fraction:
    if not values:
        raise AnalysisError("cannot average an empty sequence")
    return sum(values, Fraction(0)) / len(values)


def _is_usable(row: Mapping[str, Any], include_errors: bool) -> bool:
    status = row.get("status", "ok")
    return status == "ok" or include_errors


def _index_arm(
    rows: Iterable[Mapping[str, Any]],
    arm: str,
) -> dict[int, dict[int, Mapping[str, Any]]]:
    index: dict[int, dict[int, Mapping[str, Any]]] = {}
    for row in rows:
        if str(row["condition"]) != arm:
            continue
        index.setdefault(int(row["seed"]), {})[int(row["episode"])] = row
    return index


# ---------------------------------------------------------------------------
# paired per-seed series
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeedPair:
    """One seed's paired difference, exact as a rational."""

    seed: int
    cells: tuple[int, ...]
    sum_minuend: int
    sum_subtrahend: int

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    @property
    def difference(self) -> Fraction:
        return Fraction(self.sum_minuend - self.sum_subtrahend, self.n_cells)


def pair_series(
    rows: Iterable[Mapping[str, Any]],
    minuend: str,
    subtrahend: str,
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    include_errors: bool = False,
) -> tuple[list[SeedPair], list[dict], int, int]:
    """Pair the two arms cell by cell and average within a seed.

    Returns ``(pairs, excluded_seeds, unpaired_minuend, unpaired_subtrahend)``.
    Only cells valid in *both* arms enter a seed's mean; each excluded seed and
    each unpaired cell is reported by the caller. Errors are usable only when
    ``include_errors`` is set, which is the §7.6 sensitivity analysis (errors
    scored at their last completed update).
    """
    left = _index_arm(rows, minuend)
    right = _index_arm(rows, subtrahend)
    pairs: list[SeedPair] = []
    excluded: list[dict] = []
    unpaired_left = 0
    unpaired_right = 0
    planned = set(range(int(episodes_per_seed)))

    for seed in seeds:
        got_left = {
            episode: row
            for episode, row in left.get(int(seed), {}).items()
            if _is_usable(row, include_errors)
        }
        got_right = {
            episode: row
            for episode, row in right.get(int(seed), {}).items()
            if _is_usable(row, include_errors)
        }
        for episode in sorted(planned):
            in_left = episode in got_left
            in_right = episode in got_right
            if in_left and not in_right:
                unpaired_left += 1
            elif in_right and not in_left:
                unpaired_right += 1
        common = tuple(sorted(set(got_left) & set(got_right)))
        if not common:
            absent_left = sorted(planned - set(left.get(int(seed), {})))
            absent_right = sorted(planned - set(right.get(int(seed), {})))
            if not got_left and not got_right:
                reason = "no valid episode in either arm"
            elif not got_left:
                reason = "no valid episode in the minuend arm"
            elif not got_right:
                reason = "no valid episode in the subtrahend arm"
            else:
                reason = "no common valid episode"
            excluded.append(
                {
                    "seed": int(seed),
                    "reason": reason,
                    "minuend_valid": len(got_left),
                    "subtrahend_valid": len(got_right),
                    "minuend_absent_episodes": absent_left,
                    "subtrahend_absent_episodes": absent_right,
                    "minuend_error_episodes": sorted(
                        episode
                        for episode, row in left.get(int(seed), {}).items()
                        if not _is_usable(row, include_errors)
                    ),
                    "subtrahend_error_episodes": sorted(
                        episode
                        for episode, row in right.get(int(seed), {}).items()
                        if not _is_usable(row, include_errors)
                    ),
                }
            )
            continue
        pairs.append(
            SeedPair(
                seed=int(seed),
                cells=common,
                sum_minuend=sum(
                    int(round(got_left[episode]["survival_score"]))
                    for episode in common
                ),
                sum_subtrahend=sum(
                    int(round(got_right[episode]["survival_score"]))
                    for episode in common
                ),
            )
        )
    return pairs, excluded, unpaired_left, unpaired_right


def _missingness_label(unpaired_left: int, unpaired_right: int) -> str:
    if unpaired_left == 0 and unpaired_right == 0:
        return "complete"
    if unpaired_left == unpaired_right:
        return "symmetric"
    return "asymmetric"


# ---------------------------------------------------------------------------
# exact tests
# ---------------------------------------------------------------------------


def exact_sign_flip(
    values: Sequence[Fraction],
) -> dict:
    """Exact two-sided sign-flip test over every one of the ``2^N`` vectors.

    ``T(s) = (1/N) sum s_i d_i`` and ``p = #{s : |T(s)| >= |T_obs|} / 2^N``.
    Integer scaling makes the boundary comparison exact.
    """
    n = len(values)
    if n < 2:
        raise AnalysisError("the sign-flip test needs at least two paired seeds")
    if n > MAX_ENUMERATED_SEEDS:
        raise AnalysisError(
            f"{n} paired seeds exceed the enumerated maximum {MAX_ENUMERATED_SEEDS}; "
            "the protocol enumerates at N <= 16 and does not authorise this design"
        )
    scale = 1
    for value in values:
        scale = lcm(scale, value.denominator)
    ints = [value.numerator * (scale // value.denominator) for value in values]
    max_abs = max(abs(item) for item in ints) or 0
    if max_abs * n >= 2**62:
        raise AnalysisError("scaled differences are too large for exact enumeration")
    observed = abs(sum(ints))
    total = 1 << n
    vector = np.asarray(ints, dtype=np.int64)
    masks = (1 << np.arange(n, dtype=np.int64)).astype(np.int64)
    count = 0
    chunk = 4096
    for start in range(0, total, chunk):
        index = np.arange(start, min(start + chunk, total), dtype=np.int64)
        bits = (index[:, None] & masks) != 0
        signs = np.where(bits, -1, 1).astype(np.int64)
        sums = signs @ vector
        count += int(np.count_nonzero(np.abs(sums) >= observed))

    p_value = Fraction(count, total)
    mean = _mean(values)
    all_zero = all(value == 0 for value in values)
    spread = sum((abs(value) for value in values), Fraction(0)) / n
    return {
        "n": n,
        "n_sign_vectors": total,
        "observed_mean_difference": float(mean),
        "count_at_least_as_extreme": count,
        "p_value": _payload(p_value),
        "minimum_two_sided_p": {"value": 2.0 / total, "exact": f"2/{total}"},
        "attainable_mean_difference_min": float(-spread),
        "attainable_mean_difference_max": float(spread),
        "exact_integer_scale": scale,
        "degenerate_all_zero": all_zero,
        **(
            {
                "note": (
                    "every paired difference is exactly zero: the design has no "
                    "power against a difference between two floored conditions; "
                    "this is not evidence that the conditions are equivalent"
                )
            }
            if all_zero
            else {}
        ),
    }


def exact_sign_test(values: Sequence[Fraction]) -> dict:
    """Two-sided exact sign test; zero differences are dropped for this check."""
    positive = sum(1 for value in values if value > 0)
    negative = sum(1 for value in values if value < 0)
    zero = len(values) - positive - negative
    n = positive + negative
    if n == 0:
        return {
            "n_nonzero": 0,
            "positive": 0,
            "negative": 0,
            "zeros_dropped": zero,
            "p_value": _payload(Fraction(1, 1)),
            "note": "all differences are zero; the sign test carries no information",
        }
    tail = min(positive, negative)
    favourable = sum(comb(n, i) for i in range(tail + 1))
    p_value = min(Fraction(1, 1), Fraction(2 * favourable, 1 << n))
    return {
        "n_nonzero": n,
        "positive": positive,
        "negative": negative,
        "zeros_dropped": zero,
        "p_value": _payload(p_value),
    }


def effect_sizes(values: Sequence[Fraction]) -> dict:
    floats = [float(value) for value in values]
    n = len(floats)
    mean = math.fsum(floats) / n
    sd = statistics.stdev(floats) if n > 1 else None
    dz = mean / sd if sd else None
    return {
        "n": n,
        "mean_difference": mean,
        "median_difference": statistics.median(floats),
        "sd_difference": sd,
        "cohens_dz": dz,
        "cohens_dz_note": (
            None
            if dz is not None
            else "undefined: the paired differences have zero standard deviation"
        ),
        "wins": sum(1 for value in floats if value > 0),
        "losses": sum(1 for value in floats if value < 0),
        "ties": sum(1 for value in floats if value == 0),
    }


def paired_bootstrap(values: Sequence[Fraction], *, resamples: int, seed: int) -> dict:
    """Paired percentile bootstrap over seeds (approximate at small N)."""
    if resamples < 1:
        raise AnalysisError("bootstrap resamples must be positive")
    array = np.asarray([float(value) for value in values], dtype=np.float64)
    rng = np.random.default_rng(int(seed))
    draws = rng.integers(0, len(array), size=(int(resamples), len(array)))
    means = array[draws].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return {
        "method": "paired percentile bootstrap over seeds",
        "resamples": int(resamples),
        "seed": int(seed),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "resampled_mean": float(means.mean()),
        "approximate": True,
        "note": (
            "approximate at this N; the exact attainable interval of the sign-flip "
            "statistic is reported alongside"
        ),
    }


# ---------------------------------------------------------------------------
# Holm
# ---------------------------------------------------------------------------


def holm_adjust(
    p_values: Mapping[str, Fraction],
    *,
    alpha: float,
    family_size: int,
) -> dict:
    """Holm–Bonferroni over the declared family, ordered by raw p."""
    if family_size < 1:
        raise AnalysisError("the Holm family size must be positive")
    if len(p_values) != family_size:
        raise AnalysisError(
            f"Holm was given {len(p_values)} tests for a declared family of "
            f"{family_size}"
        )
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    running = Fraction(0)
    still_rejecting = True
    steps = []
    rejected: list[str] = []
    for position, (contrast_id, raw) in enumerate(ordered, start=1):
        divisor = family_size - position + 1
        threshold = Fraction(alpha).limit_denominator(10**9) / divisor
        adjusted = min(Fraction(1), raw * divisor)
        running = max(running, adjusted)
        survives = still_rejecting and raw <= threshold
        if survives:
            rejected.append(contrast_id)
        else:
            still_rejecting = False
        steps.append(
            {
                "step": position,
                "id": contrast_id,
                "p_raw": _payload(raw),
                "threshold": float(threshold),
                "threshold_fraction": f"{threshold.numerator}/{threshold.denominator}",
                "p_adjusted": _payload(running),
                "rejected": bool(survives),
            }
        )
    return {
        "method": "Holm-Bonferroni",
        "alpha": float(alpha),
        "family_size": family_size,
        "steps": steps,
        "rejected": rejected,
        "not_rejected": [cid for cid in p_values if cid not in rejected],
    }


# ---------------------------------------------------------------------------
# design constants reproduced from config (REV3 §7.1, §7.4, §7.5)
# ---------------------------------------------------------------------------


def design_summary(
    campaign: CampaignConfig,
    *,
    family_size: int,
    sigma: float = ASSUMED_SIGMA_UPDATES,
) -> dict:
    """Recompute every N-dependent §7 number from the declared configuration."""
    alpha = float(campaign.alpha)
    sei = int(campaign.sei_updates)
    variants = {}
    for label, n in (
        ("fallback", int(campaign.n_seeds_fallback)),
        ("primary", int(campaign.n_seeds_primary)),
    ):
        vectors = 1 << n
        thresholds = []
        for step in range(1, family_size + 1):
            divisor = family_size - step + 1
            threshold = alpha / divisor
            admissible = int(math.floor(threshold * vectors + 1e-9))
            thresholds.append(
                {
                    "step": step,
                    "divisor": divisor,
                    "threshold": threshold,
                    "admissible_sign_vectors": admissible,
                    "admissible_fraction": admissible / vectors,
                }
            )
        variants[label] = {
            "n": n,
            "sign_vectors": vectors,
            "minimum_two_sided_p": 2.0 / vectors,
            "minimum_two_sided_count": 2,
            "raw_two_sided_0_05_count_threshold": int(
                math.floor(alpha * vectors + 1e-9)
            ),
            "holm_steps": thresholds,
            "minimum_adjusted_p": family_size * 2.0 / vectors,
            "mde_sigma_coefficient": MDE_COEFFICIENT / sqrt(n),
            "mde_at_assumed_sigma": MDE_COEFFICIENT * sigma / sqrt(n),
            "sigma_supported_for_sei": sei * sqrt(n) / MDE_COEFFICIENT,
            "holm_step1_mde_coefficient": HOLM_STEP1_COEFFICIENT / sqrt(n),
            "holm_step1_mde_at_assumed_sigma": HOLM_STEP1_COEFFICIENT * sigma / sqrt(n),
        }

    declared = float(campaign.fallback_max_paired_sd)
    computed = sei * sqrt(campaign.n_seeds_fallback) / MDE_COEFFICIENT
    relative = abs(computed - declared) / declared
    return {
        "alpha": alpha,
        "family_size": family_size,
        "sei_updates": sei,
        "assumed_sigma_updates": float(sigma),
        "variants": variants,
        "fallback_threshold_check": {
            "declared_max_paired_sd": declared,
            "computed_from_mde_formula": computed,
            "relative_difference": relative,
            "consistent": relative <= 0.001,
            "note": (
                "the declared fallback bound and the §7.4 formula agree"
                if relative <= 0.001
                else (
                    "the declared fallback bound is "
                    f"{100 * relative:.2f}% above the value implied by the §7.4 "
                    "formula; the declared constant governs the pilot decision "
                    "and the discrepancy is reported, not reconciled"
                )
            ),
        },
    }


# ---------------------------------------------------------------------------
# arm summaries and missingness
# ---------------------------------------------------------------------------


def arm_summary(
    rows: Iterable[Mapping[str, Any]],
    arm: str,
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
) -> dict:
    index = _index_arm(rows, arm)
    ok_rows = [
        row
        for seed in seeds
        for episode, row in sorted(index.get(int(seed), {}).items())
        if episode < episodes_per_seed and row.get("status", "ok") == "ok"
    ]
    stored = sum(
        1
        for seed in seeds
        for episode in index.get(int(seed), {})
        if episode < episodes_per_seed
    )
    errors = sum(
        1
        for seed in seeds
        for episode, row in index.get(int(seed), {}).items()
        if episode < episodes_per_seed and row.get("status") == "error"
    )
    expected = len(seeds) * episodes_per_seed
    scores = [float(row["survival_score"]) for row in ok_rows]
    per_seed = []
    for seed in seeds:
        seed_rows = [
            row
            for episode, row in sorted(index.get(int(seed), {}).items())
            if episode < episodes_per_seed and row.get("status", "ok") == "ok"
        ]
        per_seed.append(
            {
                "seed": int(seed),
                "episodes": len(seed_rows),
                "mean_capped_score": (
                    math.fsum(float(row["survival_score"]) for row in seed_rows)
                    / len(seed_rows)
                    if seed_rows
                    else None
                ),
            }
        )
    steps = sum(int(row["steps"]) for row in ok_rows)
    motor = sum(int(row["motor_spikes"]) for row in ok_rows)
    return {
        "arm": arm,
        "episodes_expected": expected,
        "episodes_stored": stored,
        "episodes_ok": len(ok_rows),
        "episodes_error": errors,
        "episodes_missing": expected - stored,
        "seeds_with_data": sum(1 for entry in per_seed if entry["episodes"]),
        "mean_capped_score": (math.fsum(scores) / len(scores)) if scores else None,
        "median_capped_score": statistics.median(scores) if scores else None,
        "cap_reaching_fraction": (
            sum(1 for row in ok_rows if bool(row["truncated"])) / len(ok_rows)
            if ok_rows
            else None
        ),
        "no_action_fraction": (
            math.fsum(float(row["no_action_fraction"]) for row in ok_rows)
            / len(ok_rows)
            if ok_rows
            else None
        ),
        "non_no_action_decisions": (
            steps - sum(int(row["action_counts"].get("NO_ACTION", 0)) for row in ok_rows)
        ),
        "total_steps": steps,
        "total_motor_spikes": motor,
        "mean_motor_spikes": (motor / len(ok_rows)) if ok_rows else None,
        "seeds_with_motor_spikes": sum(
            1
            for seed in seeds
            if any(
                int(row["motor_spikes"]) > 0
                for episode, row in sorted(index.get(int(seed), {}).items())
                if episode < episodes_per_seed and row.get("status", "ok") == "ok"
            )
        ),
        "mean_total_reward": (
            math.fsum(float(row["total_reward"]) for row in ok_rows) / len(ok_rows)
            if ok_rows
            else None
        ),
        "per_seed": per_seed,
    }


def missingness_report(
    rows: Sequence[Mapping[str, Any]],
    *,
    arms: Sequence[str],
    seeds: Sequence[int],
    episodes_per_seed: int,
) -> dict:
    counts = {}
    for arm in arms:
        index = _index_arm(rows, arm)
        stored = sum(
            1
            for seed in seeds
            for episode in index.get(int(seed), {})
            if episode < episodes_per_seed
        )
        errors = sum(
            1
            for seed in seeds
            for episode, row in index.get(int(seed), {}).items()
            if episode < episodes_per_seed and row.get("status") == "error"
        )
        expected = len(seeds) * episodes_per_seed
        counts[arm] = {
            "expected": expected,
            "stored": stored,
            "ok": stored - errors,
            "error": errors,
            "missing": expected - stored,
        }
    planned = {
        (arm, int(seed), int(episode))
        for arm in arms
        for seed in seeds
        for episode in range(episodes_per_seed)
    }
    outside = []
    for row in rows:
        key = (str(row["condition"]), int(row["seed"]), int(row["episode"]))
        if key not in planned:
            outside.append(
                {
                    "condition": key[0],
                    "seed": key[1],
                    "episode": key[2],
                    "status": row.get("status", "ok"),
                }
            )
    return {
        "arms": counts,
        "outside_plan_count": len(outside),
        "outside_plan": outside,
        "seeds": [int(seed) for seed in seeds],
        "episodes_per_seed": int(episodes_per_seed),
        "note": (
            "counts are per arm; a pair is dropped only when a cell is structurally "
            "undefined or invalid, and every dropped cell is reported here"
        ),
    }


# ---------------------------------------------------------------------------
# one contrast
# ---------------------------------------------------------------------------


def _contrast_series(
    rows: Sequence[Mapping[str, Any]],
    contrast: Mapping[str, str],
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    include_errors: bool = False,
) -> dict:
    pairs, excluded, unpaired_left, unpaired_right = pair_series(
        rows,
        contrast["minuend"],
        contrast["subtrahend"],
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        include_errors=include_errors,
    )
    label = _missingness_label(unpaired_left, unpaired_right)
    return {
        "id": contrast["id"],
        "minuend": contrast["minuend"],
        "subtrahend": contrast["subtrahend"],
        "seeds_planned": len(seeds),
        "seeds_paired": len(pairs),
        "cells_paired": sum(pair.n_cells for pair in pairs),
        "unpaired_minuend_cells": unpaired_left,
        "unpaired_subtrahend_cells": unpaired_right,
        "missingness": label,
        "potentially_biased": label == "asymmetric",
        "excluded_seeds": excluded,
        "values": [
            {
                "seed": pair.seed,
                "cells": list(pair.cells),
                "n_cells": pair.n_cells,
                "difference": float(pair.difference),
                "difference_exact": (
                    f"{pair.difference.numerator}/{pair.difference.denominator}"
                ),
            }
            for pair in pairs
        ],
        "_fractions": [pair.difference for pair in pairs],
    }


def _contrast_block(
    rows: Sequence[Mapping[str, Any]],
    contrast: Mapping[str, str],
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    bootstrap_resamples: int,
    bootstrap_seed: int | None,
    include_errors: bool = False,
) -> dict:
    block = _contrast_series(
        rows,
        contrast,
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        include_errors=include_errors,
    )
    values: list[Fraction] = block.pop("_fractions")
    block["direction"] = (
        "positive" if values and _mean(values) > 0 else
        "negative" if values and _mean(values) < 0 else
        "zero"
    )
    if len(values) >= 2:
        block["sign_flip"] = exact_sign_flip(values)
        block["sign_test"] = exact_sign_test(values)
        block["effect_sizes"] = effect_sizes(values)
        block["bootstrap"] = paired_bootstrap(
            values,
            resamples=bootstrap_resamples,
            seed=(
                int(bootstrap_seed)
                if bootstrap_seed is not None
                else int(contrast["id"].encode("utf-8")[0])
            ),
        )
    else:
        block["sign_flip"] = {
            "status": "not computed",
            "reason": "fewer than two complete pairs",
        }
    return block


def _withhold_inference(block: dict, reason: str) -> dict:
    for key in ("sign_flip", "sign_test", "effect_sizes", "bootstrap"):
        if key in block:
            block[key] = {"status": "not computed", "reason": reason}
    block["status"] = "design_failure"
    block["reason"] = reason
    return block


# ---------------------------------------------------------------------------
# identity controls
# ---------------------------------------------------------------------------


def identity_check(
    rows: Sequence[Mapping[str, Any]],
    *,
    control: str,
    target: str,
    seeds: Sequence[int],
    episodes_per_seed: int,
) -> dict:
    """Compare a control arm with its target, from the stored rows only."""
    left = _index_arm(rows, control)
    right = _index_arm(rows, target)
    mismatches: list[dict] = []
    compared = 0
    missing: list[tuple[int, int]] = []
    unavailable: list[str] = []
    required_non_null = {
        "spike_sha256",
        "action_sha256",
        "weights_before",
        "weights_after",
    }
    fields_compared: list[str] = []
    for seed in seeds:
        for episode in range(int(episodes_per_seed)):
            control_row = left.get(int(seed), {}).get(episode)
            target_row = right.get(int(seed), {}).get(episode)
            if control_row is None or target_row is None:
                missing.append((int(seed), episode))
                continue
            compared += 1
            for field in IDENTITY_FIELDS:
                a = control_row.get(field)
                b = target_row.get(field)
                if field not in fields_compared and (field in control_row or field in target_row):
                    fields_compared.append(field)
                if field in required_non_null and a is None and b is None:
                    if field not in unavailable:
                        unavailable.append(field)
                    continue
                if a != b:
                    mismatches.append(
                        {
                            "seed": int(seed),
                            "episode": episode,
                            "field": field,
                            "control": a,
                            "target": b,
                        }
                    )
    planned = len(seeds) * int(episodes_per_seed)
    if mismatches:
        status = "fail"
    elif missing or unavailable or not fields_compared:
        status = "incomplete"
    else:
        status = "pass"
    return {
        "control": control,
        "target": target,
        "status": status,
        "pairs_planned": planned,
        "pairs_compared": compared,
        "pairs_missing": len(missing),
        "missing_keys": [
            {"seed": seed, "episode": episode} for seed, episode in missing[:50]
        ],
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:50],
        "fields_compared": fields_compared,
        "unavailable_fields": unavailable,
        "fields_unavailable_from_rows": [
            "P1 spike times (covered here by spike_sha256)",
            "P2 spike neuron indices (covered here by spike_sha256)",
            "P5 full record sequence (requires the episode artifact)",
            "P10 per-decision motor_activity (requires the episode artifact)",
        ],
        "invalidated_arm": (
            "B" if control == "A_prime" else "D" if control == "C_prime" else None
        ),
        "note": (
            "exact equality only (REV3 §3.8.4); a mismatch is a hard stop and the "
            "invalidated arm is excluded from every aggregate"
        ),
    }


# ---------------------------------------------------------------------------
# decisions and the E1-E5 checklist
# ---------------------------------------------------------------------------


def decision_summary(
    rows: Iterable[Mapping[str, Any]],
    arm: str,
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
) -> dict:
    index = _index_arm(rows, arm)
    classes: Counter[str] = Counter()
    has_classes = True
    decisions = 0
    with_motor_spike = 0
    has_motor = True
    non_no_action = 0
    per_seed = {}
    for seed in seeds:
        seed_classes: Counter[str] = Counter()
        seed_decisions = 0
        seed_with_spike = 0
        seed_non_no_action = 0
        seed_has_classes = True
        seed_has_motor = True
        for episode, row in sorted(index.get(int(seed), {}).items()):
            if episode >= episodes_per_seed or row.get("status", "ok") != "ok":
                continue
            seed_non_no_action += int(row["steps"]) - int(
                row["action_counts"].get("NO_ACTION", 0)
            )
            record = row.get("decision_classes")
            if isinstance(record, Mapping):
                seed_classes.update({str(k): int(v) for k, v in record.items()})
            else:
                seed_has_classes = False
            motor = row.get("motor_summary")
            if isinstance(motor, Mapping):
                seed_decisions += int(motor.get("decisions", row["steps"]))
                seed_with_spike += int(motor.get("decisions_with_motor_spike", 0))
            else:
                seed_has_motor = False
        has_classes = has_classes and seed_has_classes
        has_motor = has_motor and seed_has_motor
        classes.update(seed_classes)
        decisions += seed_decisions
        with_motor_spike += seed_with_spike
        non_no_action += seed_non_no_action
        per_seed[int(seed)] = {
            "decisions": seed_decisions,
            "decisions_with_motor_spike": seed_with_spike,
            "decision_fraction_with_motor_spike": (
                seed_with_spike / seed_decisions if seed_decisions else None
            ),
            "non_no_action_decisions": seed_non_no_action,
            "motor_driven": int(seed_classes.get("motor-driven", 0)),
            "decision_classes_present": seed_has_classes,
            "motor_summary_present": seed_has_motor,
        }
    return {
        "arm": arm,
        "decision_classes_present": has_classes and decisions > 0,
        "motor_summary_present": has_motor and decisions > 0,
        "decision_classes": dict(classes),
        "decisions": decisions,
        "decisions_with_motor_spike": with_motor_spike,
        "motor_driven": int(classes.get("motor-driven", 0)),
        "non_no_action_decisions": non_no_action,
        "per_seed": per_seed,
    }


def _check(status: str, **details: Any) -> dict:
    return {"status": status, **details}


def evidence_checklist(
    rows: Sequence[Mapping[str, Any]],
    *,
    confirmatory: Mapping[str, dict],
    family_size: int,
    seeds: Sequence[int],
    episodes_per_seed: int,
    replay_rows: Sequence[Mapping[str, Any]] | None = None,
    arm: str = "F",
) -> dict:
    """E1-E5 of REV3 §3.6.4. A missing input is "not evaluable", never a pass."""
    summary = decision_summary(
        rows, arm, seeds=seeds, episodes_per_seed=episodes_per_seed
    )

    checks: dict[str, dict] = {}

    c1 = confirmatory.get("C1", {})
    c4 = confirmatory.get("C4", {})
    if family_size == 3:
        e1 = _check(
            "not evaluable",
            reason=(
                "C4 is exploratory when U14 selects m = 3; no decoding claim may be "
                "made at all (REV3 §5.3)"
            ),
        )
    elif c4.get("holm_rejected") is None:
        e1 = _check("not evaluable", reason="the confirmatory family was withheld")
    else:
        positive = c4.get("direction") == "positive"
        e1 = _check(
            "pass" if c4["holm_rejected"] and positive else "fail",
            contrast="C4",
            direction=c4.get("direction"),
            p_adjusted=(
                c4.get("holm", {}).get("p_adjusted") if isinstance(c4.get("holm"), Mapping) else None
            ),
        )
    checks["E1"] = e1

    if c1.get("holm_rejected") is None:
        e2 = _check("not evaluable", reason="the confirmatory family was withheld")
    else:
        e2 = _check(
            "pass" if c1["holm_rejected"] and c1.get("direction") == "positive" else "fail",
            contrast="C1",
            direction=c1.get("direction"),
            p_adjusted=(
                c1.get("holm", {}).get("p_adjusted") if isinstance(c1.get("holm"), Mapping) else None
            ),
        )
    checks["E2"] = e2

    if not summary["motor_summary_present"]:
        checks["E3"] = _check(
            "not evaluable",
            reason="per-decision motor summaries are absent from the stored rows",
        )
    else:
        passing = []
        for seed in seeds:
            entry = summary["per_seed"][int(seed)]
            fraction = entry["decision_fraction_with_motor_spike"]
            if (
                fraction is not None
                and fraction >= E3_MIN_DECISION_FRACTION
            ):
                passing.append(int(seed))
        required = max(1, math.ceil(E3_MIN_SEED_FRACTION * len(seeds)))
        checks["E3"] = _check(
            "pass" if len(passing) >= required else "fail",
            passing_seeds=len(passing),
            seeds_required=required,
            seeds_total=len(seeds),
            threshold_fraction=E3_MIN_DECISION_FRACTION,
        )

    if not summary["decision_classes_present"]:
        checks["E4"] = _check(
            "not evaluable",
            reason="the frozen-parameter ablation classes are absent from the rows",
        )
    elif summary["non_no_action_decisions"] == 0:
        checks["E4"] = _check(
            "undefined",
            numerator=0,
            denominator=0,
            threshold_fraction=E4_MIN_MOTOR_DRIVEN_FRACTION,
            reason=(
                "no non-NO_ACTION decisions: E4 is undefined (0/0), never a pass "
                "(REV3 §3.6.4)"
            ),
        )
    else:
        fraction = (
            summary["motor_driven"] / summary["non_no_action_decisions"]
        )
        checks["E4"] = _check(
            "pass" if fraction >= E4_MIN_MOTOR_DRIVEN_FRACTION else "fail",
            motor_driven=summary["motor_driven"],
            non_no_action_decisions=summary["non_no_action_decisions"],
            fraction=fraction,
            threshold_fraction=E4_MIN_MOTOR_DRIVEN_FRACTION,
        )

    if replay_rows is None:
        checks["E5"] = _check(
            "not run",
            reason="no fresh-process replay store was supplied",
        )
    else:
        current = {
            (int(row["seed"]), int(row["episode"])): int(
                (row.get("decision_classes") or {}).get("motor-driven", 0)
            )
            for row in rows
            if str(row["condition"]) == arm and row.get("status", "ok") == "ok"
        }
        replay = {
            (int(row["seed"]), int(row["episode"])): int(
                (row.get("decision_classes") or {}).get("motor-driven", 0)
            )
            for row in replay_rows
            if str(row["condition"]) == arm and row.get("status", "ok") == "ok"
        }
        differing = sorted(
            key for key, value in current.items() if replay.get(key) != value
        )
        checks["E5"] = _check(
            "pass" if not differing and bool(current) else "fail",
            compared=len(current),
            differing=[{"seed": s, "episode": e} for s, e in differing],
        )

    all_pass = all(
        entry["status"] == "pass" for entry in checks.values()
    )
    return {
        "arm": arm,
        "checks": checks,
        "decoding_claim_permitted": all_pass,
        "decision_summary": summary,
    }


# ---------------------------------------------------------------------------
# floor and readout decompositions
# ---------------------------------------------------------------------------


def floor_decomposition(
    rows: Sequence[Mapping[str, Any]],
    *,
    arms: Sequence[str],
    conditions: Sequence[str],
    seeds: Sequence[int],
    episodes_per_seed: int,
    bootstrap_resamples: int,
    bootstrap_seed: int,
    exclude_arms: Sequence[str] = (),
) -> dict:
    floor = "floor"
    floor_present = any(str(row["condition"]) == floor for row in rows)
    if not floor_present:
        return {
            "status": "not measured",
            "note": (
                "the substrate-free floor must be measured by replaying the paired "
                "environment seeds; it is never assumed"
            ),
        }

    floor_mean = arm_summary(
        rows, floor, seeds=seeds, episodes_per_seed=episodes_per_seed
    )["mean_capped_score"]
    contrasts = []
    per_arm = []
    at_floor_conditions = []
    for arm in arms:
        if arm == floor or arm in exclude_arms:
            continue
        summary = arm_summary(
            rows, arm, seeds=seeds, episodes_per_seed=episodes_per_seed
        )
        entry = {
            "arm": arm,
            "mean_capped_score": summary["mean_capped_score"],
            "cap_reaching_fraction": summary["cap_reaching_fraction"],
            "no_action_fraction": summary["no_action_fraction"],
            "total_motor_spikes": summary["total_motor_spikes"],
            "seeds_with_motor_spikes": summary["seeds_with_motor_spikes"],
        }
        block = _contrast_block(
            rows,
            {"id": f"{arm}_minus_floor", "minuend": arm, "subtrahend": floor},
            seeds=seeds,
            episodes_per_seed=episodes_per_seed,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        entry["mean_difference_from_floor"] = (
            block["effect_sizes"]["mean_difference"]
            if isinstance(block.get("effect_sizes"), Mapping)
            else None
        )
        entry["sign_flip_p"] = (
            block["sign_flip"].get("p_value")
            if isinstance(block.get("sign_flip"), Mapping)
            else None
        )
        if arm in conditions and isinstance(block.get("effect_sizes"), Mapping):
            at_floor = block["effect_sizes"]["mean_difference"] <= 0
            entry["at_floor"] = at_floor
            if at_floor:
                at_floor_conditions.append(arm)
        entry["status"] = "descriptive, uncorrected"
        entry["claim"] = (
            "the substrate-free no-action floor; not a neural arm and not a "
            "confirmatory contrast"
        )
        per_arm.append(entry)
        contrasts.append(block)

    diagnosis = {}
    for arm in arms:
        if arm == floor or arm in exclude_arms:
            continue
        summary = arm_summary(
            rows, arm, seeds=seeds, episodes_per_seed=episodes_per_seed
        )
        decisions = decision_summary(
            rows, arm, seeds=seeds, episodes_per_seed=episodes_per_seed
        )
        reason = None
        if summary["total_motor_spikes"] == 0:
            reason = "no motor spikes"
        elif summary["non_no_action_decisions"] == 0:
            reason = "decoder gate never met"
        elif decisions["motor_summary_present"]:
            passing = sum(
                1
                for entry in decisions["per_seed"].values()
                if (entry["decision_fraction_with_motor_spike"] or 0.0)
                >= E3_MIN_DECISION_FRACTION
            )
            if passing < math.ceil(E3_MIN_SEED_FRACTION * len(seeds)):
                reason = "no sustained activity"
        if reason is None:
            reason = (
                "not decomposed by the three declared reasons; inspect the action "
                "distribution"
            )
        diagnosis[arm] = {
            "reason": reason,
            "motor_spikes": summary["total_motor_spikes"],
            "non_no_action_decisions": summary["non_no_action_decisions"],
            "per_decision_summary_present": decisions["motor_summary_present"],
        }

    return {
        "status": "measured",
        "floor_mean_capped_score": floor_mean,
        "per_arm": per_arm,
        "contrasts": contrasts,
        "diagnosis": diagnosis,
        "conditions_at_floor": at_floor_conditions,
        "conditions_considered": list(conditions),
        "no_power_warning": len(at_floor_conditions) >= 4,
        "note": (
            "a condition is declared at floor here when its paired mean difference "
            "from the measured floor is <= 0; the protocol names the floor finding "
            "but does not define the comparison numerically, so this definition is "
            "reported rather than assumed silently"
        ),
    }


def readout_decomposition(
    rows: Sequence[Mapping[str, Any]],
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    family_size: int,
    confirmatory: Mapping[str, dict],
    bootstrap_resamples: int,
    bootstrap_seed: int,
    replay_rows: Sequence[Mapping[str, Any]] | None,
) -> dict:
    claims: dict[str, dict] = {}

    claim_1 = _contrast_block(
        rows,
        {"id": "F_beta_minus_floor", "minuend": "F_beta", "subtrahend": "floor"},
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    claims["1"] = {
        "claim": "a better constant action is available than NO_ACTION",
        "contrast": "F_beta - floor",
        "result": claim_1,
        "does_not_establish": "state-dependence or decoding",
    }

    c4 = confirmatory.get("C4")
    claims["2"] = {
        "claim": "state-dependence adds value over the best constant policy",
        "contrast": "F - F_beta (C4)",
        "result": c4 if c4 is not None else {"status": "not available (m = 3)"},
        "does_not_establish": (
            "that the dependence is on motor activity rather than another state variable"
        ),
    }

    claim_4 = _contrast_block(
        rows,
        {"id": "F_minus_F_init", "minuend": "F", "subtrahend": "F_init"},
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    claims["4"] = {
        "claim": "F learned rather than being merely a non-constant policy",
        "contrast": "F - F_init (diagnostic, uncorrected)",
        "result": claim_4,
        "does_not_establish": "that what was learned is motor decoding",
    }

    checklist = evidence_checklist(
        rows,
        confirmatory=confirmatory,
        family_size=family_size,
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        replay_rows=replay_rows,
    )
    claims["3"] = {
        "claim": "the decision depends causally in the frozen model on motor features",
        "evidence": checklist,
        "does_not_establish": "biological causality or usefulness",
    }

    statements = []
    e3 = checklist["checks"]["E3"]["status"]
    e1 = checklist["checks"]["E1"]["status"]
    e2 = checklist["checks"]["E2"]["status"]
    if e3 == "fail":
        statements.append(
            "the motor populations were silent; the readout could at most learn a "
            "constant policy"
        )
    elif e3 == "pass" and not (e1 == "pass" and e2 == "pass"):
        statements.append(
            "no evidence that the readout used motor information"
        )
    if checklist["decoding_claim_permitted"]:
        statements.append(
            "the readout's decisions depend on motor activity in the frozen model; "
            "this is not a biological-causality claim"
        )
    claim_4_result = claims["4"]["result"]
    if isinstance(claim_4_result.get("effect_sizes"), Mapping) and isinstance(
        claim_4_result.get("sign_flip"), Mapping
    ):
        learned = (
            claim_4_result["effect_sizes"]["mean_difference"] > 0
            and claim_4_result["sign_flip"].get("p_value") is not None
            and claim_4_result["sign_flip"]["p_value"]["value"] < 0.05
        )
        statements.append(
            "F learned rather than being merely a non-constant policy"
            if learned
            else "F may be described as a non-constant policy, not as a learned one"
        )

    return {
        "claims": claims,
        "checklist": checklist,
        "permitted_statements": statements,
        "forbidden_statements": [
            "the connectome learned",
            "plasticity improved performance in condition F",
            "the readout succeeded when F_beta scores the same",
            "F beat the baseline (without naming which baseline)",
        ],
    }


# ---------------------------------------------------------------------------
# top-level analysis
# ---------------------------------------------------------------------------


def analyse_campaign(
    rows: Sequence[Mapping[str, Any]],
    config: Phase8Config,
    *,
    family_size: int,
    n_seeds: int,
    sigma: float = ASSUMED_SIGMA_UPDATES,
    include_sensitivity: bool = True,
    replay_rows: Sequence[Mapping[str, Any]] | None = None,
    registry: Registry | None = None,
) -> dict:
    """Analyse a campaign store as REV3 §7 declares.

    ``family_size`` and ``n_seeds`` are explicit because both are recorded
    decisions (U14, U7), not analysis defaults.
    """
    if family_size not in (3, 4):
        raise AnalysisError("the Holm family size must be 4 or 3 (REV3 U14)")
    campaign = config.campaign
    if n_seeds not in (campaign.n_seeds_fallback, campaign.n_seeds_primary):
        raise AnalysisError(
            f"n_seeds must be one of the declared designs "
            f"({campaign.n_seeds_fallback}, {campaign.n_seeds_primary})"
        )
    if len(campaign.campaign_seeds) < n_seeds:
        raise AnalysisError("the campaign declares fewer seeds than requested")

    checked = validate_rows(rows)
    active = tuple(int(seed) for seed in campaign.campaign_seeds[:n_seeds])
    episodes_per_seed = int(campaign.episodes_per_seed)
    registry = registry or build_registry(config.conditions)
    arms = registry.evaluation_arms
    conditions = registry.conditions
    n_floor = int(campaign.n_seeds_fallback)

    missingness = missingness_report(
        checked,
        arms=arms,
        seeds=active,
        episodes_per_seed=episodes_per_seed,
    )
    arms_report = {
        arm: arm_summary(
            checked, arm, seeds=active, episodes_per_seed=episodes_per_seed
        )
        for arm in arms
    }

    warnings: list[str] = []

    identity = {
        "A_prime": identity_check(
            checked,
            control="A_prime",
            target="A",
            seeds=active,
            episodes_per_seed=episodes_per_seed,
        ),
        "C_prime": identity_check(
            checked,
            control="C_prime",
            target="C",
            seeds=active,
            episodes_per_seed=episodes_per_seed,
        ),
    }
    invalid_arms: set[str] = set()
    for name, report in identity.items():
        if report["status"] == "fail":
            invalid_arms.add(str(report["invalidated_arm"]))
            if name == "A_prime":
                # The same stepper serves D (REV3 §3.8.5, point 5).
                invalid_arms.add("D")
            warnings.append(
                f"{name} is not identical to {report['target']}: hard stop; "
                f"{sorted(invalid_arms)} INVALID for interpretation"
            )
        elif report["status"] == "incomplete":
            warnings.append(
                f"{name} identity check is incomplete: "
                f"{report['pairs_missing']} pairs missing, "
                f"{len(report['unavailable_fields'])} required fields unavailable; "
                "it is not a pass"
            )
    for arm in invalid_arms:
        if arm in arms_report:
            arms_report[arm]["invalid"] = True

    confirmatory_results: dict[str, dict] = {}
    p_values: dict[str, Fraction] = {}
    withheld = False
    for contrast in confirmatory_contrasts(family_size):
        involved = {contrast["minuend"], contrast["subtrahend"]}
        block = _contrast_block(
            checked,
            contrast,
            seeds=active,
            episodes_per_seed=episodes_per_seed,
            bootstrap_resamples=int(campaign.bootstrap_resamples),
            bootstrap_seed=int(campaign.bootstrap_seed),
        )
        block["hypothesis"] = contrast["hypothesis"]
        block["question"] = contrast["question"]
        block["confirmatory"] = True
        if involved & invalid_arms:
            block = _withhold_inference(
                block,
                (
                    "an identity control failed; "
                    f"{sorted(involved & invalid_arms)} is INVALID and excluded from "
                    "every aggregate (REV3 §3.8.5)"
                ),
            )
            block["invalid"] = True
            withheld = True
        elif block["seeds_paired"] < n_floor:
            block = _withhold_inference(
                block,
                (
                    f"actual complete-pair N = {block['seeds_paired']} is below the "
                    f"predeclared minimum {n_floor}; the primary is not computed "
                    "(REV3 §7.3 rule 4)"
                ),
            )
            withheld = True
            warnings.append(
                f"{contrast['id']}: complete-pair N {block['seeds_paired']} < "
                f"predeclared minimum {n_floor}; confirmatory family withheld"
            )
        elif "sign_flip" in block and "p_value" in block["sign_flip"]:
            p_values[contrast["id"]] = Fraction(
                block["sign_flip"]["p_value"]["numerator"],
                block["sign_flip"]["p_value"]["denominator"],
            )
        if block.get("potentially_biased"):
            warnings.append(
                f"{contrast['id']}: missingness is {block['missingness']}; the "
                "complete-case primary is labelled potentially biased"
            )
        if isinstance(block.get("sign_flip"), Mapping) and block["sign_flip"].get(
            "degenerate_all_zero"
        ):
            warnings.append(
                f"{contrast['id']}: every paired difference is zero; no difference "
                "is detectable and the design has no power between the two floored "
                "conditions"
            )

        if include_sensitivity and not block.get("invalid"):
            errors_present = any(
                int(missingness["arms"][arm]["error"]) > 0
                for arm in (contrast["minuend"], contrast["subtrahend"])
                if arm in missingness["arms"]
            )
            if errors_present:
                sensitivity = _contrast_block(
                    checked,
                    contrast,
                    seeds=active,
                    episodes_per_seed=episodes_per_seed,
                    bootstrap_resamples=int(campaign.bootstrap_resamples),
                    bootstrap_seed=int(campaign.bootstrap_seed),
                    include_errors=True,
                )
                sensitivity["scored_at"] = "last completed update (REV3 §7.6)"
                sensitivity["trigger"] = (
                    "asymmetric missingness"
                    if block.get("missingness") == "asymmetric"
                    else "error rows present"
                )
                block["sensitivity"] = sensitivity
        confirmatory_results[contrast["id"]] = block

    holm = None
    if not withheld and len(p_values) == family_size:
        holm = holm_adjust(
            p_values,
            alpha=float(campaign.alpha),
            family_size=family_size,
        )
        by_id = {step["id"]: step for step in holm["steps"]}
        for contrast_id, block in confirmatory_results.items():
            step = by_id.get(contrast_id)
            if step is None:
                continue
            block["holm_rejected"] = bool(step["rejected"])
            block["holm"] = {
                "step": step["step"],
                "threshold": step["threshold"],
                "p_adjusted": step["p_adjusted"],
            }
    else:
        if not withheld:
            warnings.append(
                "the confirmatory family could not be assembled; Holm is not computed"
            )
        for block in confirmatory_results.values():
            block.setdefault("holm_rejected", None)
            block.setdefault("holm", {"status": "withheld"})

    secondary = []
    for contrast in SECONDARY_CONTRASTS:
        involved = {contrast["minuend"], contrast["subtrahend"]}
        block = _contrast_block(
            checked,
            contrast,
            seeds=active,
            episodes_per_seed=episodes_per_seed,
            bootstrap_resamples=int(campaign.bootstrap_resamples),
            bootstrap_seed=int(campaign.bootstrap_seed),
        )
        block["status_label"] = contrast["status"]
        block["question"] = contrast["question"]
        block["exploratory"] = True
        if involved & invalid_arms:
            block = _withhold_inference(
                block,
                (
                    "an identity control failed; "
                    f"{sorted(involved & invalid_arms)} is INVALID (REV3 §3.8.5)"
                ),
            )
            block["invalid"] = True
        if block["seeds_paired"] < 2 and not block.get("invalid"):
            block["sign_flip"] = {
                "status": "not computed",
                "reason": "fewer than two complete pairs",
            }
        secondary.append(block)

    floor = floor_decomposition(
        checked,
        arms=arms,
        conditions=conditions,
        seeds=active,
        episodes_per_seed=episodes_per_seed,
        bootstrap_resamples=int(campaign.bootstrap_resamples),
        bootstrap_seed=int(campaign.bootstrap_seed),
        exclude_arms=tuple(sorted(invalid_arms)),
    )
    if floor["status"] != "measured":
        warnings.append(
            "the substrate-free floor is not present in the store; the floor "
            "decomposition and U1 are not evaluable"
        )
    elif floor.get("no_power_warning"):
        warnings.append(
            f"{len(floor['conditions_at_floor'])} of {len(conditions)} conditions "
            "are at the measured floor; the design has no power against a "
            "difference between floored conditions (REV3 §7.8)"
        )

    readout = readout_decomposition(
        checked,
        seeds=active,
        episodes_per_seed=episodes_per_seed,
        family_size=family_size,
        confirmatory=confirmatory_results,
        bootstrap_resamples=int(campaign.bootstrap_resamples),
        bootstrap_seed=int(campaign.bootstrap_seed),
        replay_rows=replay_rows,
    )

    design = design_summary(campaign, family_size=family_size, sigma=sigma)
    if not design["fallback_threshold_check"]["consistent"]:
        warnings.append(
            "the declared fallback sigma bound differs from the MDE formula: "
            f"{design['fallback_threshold_check']['declared_max_paired_sd']} vs "
            f"{design['fallback_threshold_check']['computed_from_mde_formula']:.3f}"
        )
    if campaign.n_seeds_selected is not None and n_seeds != campaign.n_seeds_selected:
        warnings.append(
            f"analysed at N = {n_seeds} although the recorded selection is "
            f"N = {campaign.n_seeds_selected}"
        )
    if campaign.n_seeds_selected is None:
        warnings.append(
            "n_seeds_selected is null in the configuration; the N recorded for "
            "this analysis was supplied explicitly and U7 remains unresolved"
        )
    warnings.append(
        "U14 is supplied by the caller (m = "
        f"{family_size}); the protocol decision is still pending approval"
    )

    paired_counts = {
        contrast_id: block["seeds_paired"]
        for contrast_id, block in confirmatory_results.items()
    }
    return {
        "analysis_version": ANALYSIS_VERSION,
        "protocol": PROTOCOL_ID,
        "family_size": family_size,
        "n_seeds_planned": n_seeds,
        "n_seeds_by_contrast": paired_counts,
        "n_seeds_analysed": min(paired_counts.values()) if paired_counts else 0,
        "n_floor": n_floor,
        "primary_status": "design_failure" if withheld else "computed",
        "rows": len(checked),
        "design": design,
        "missingness": missingness,
        "arms": arms_report,
        "confirmatory": {
            "family_size": family_size,
            "contrasts": confirmatory_results,
            "holm": holm,
            "status": "withheld" if withheld else "computed",
        },
        "floor": floor,
        "identity": identity,
        "readout": readout,
        "secondary": secondary,
        "warnings": warnings,
        "notes": [
            "no number in this output is typed by hand; every value is computed "
            "from the stored rows and the declared configuration",
            "zero differences are retained; ties cannot distinguish the arms",
            "the sign-flip test is exact and enumerated, not Monte Carlo",
        ],
    }


def analyse_store(
    store_path,
    config: Phase8Config,
    *,
    family_size: int,
    n_seeds: int,
    sigma: float = ASSUMED_SIGMA_UPDATES,
    replay_store_path=None,
) -> dict:
    """Convenience wrapper: read the append-only store and analyse it."""
    from .store import read_store

    rows = read_store(store_path)
    replay_rows = read_store(replay_store_path) if replay_store_path else None
    return analyse_campaign(
        rows,
        config,
        family_size=family_size,
        n_seeds=n_seeds,
        sigma=sigma,
        replay_rows=replay_rows,
    )


__all__ = [
    "ANALYSIS_VERSION",
    "ASSUMED_SIGMA_UPDATES",
    "AnalysisError",
    "E3_MIN_DECISION_FRACTION",
    "E3_MIN_SEED_FRACTION",
    "E4_MIN_MOTOR_DRIVEN_FRACTION",
    "HOLM_STEP1_COEFFICIENT",
    "IDENTITY_FIELDS",
    "MAX_ENUMERATED_SEEDS",
    "MDE_COEFFICIENT",
    "PROTOCOL_ID",
    "SECONDARY_CONTRASTS",
    "SeedPair",
    "analyse_campaign",
    "analyse_store",
    "arm_summary",
    "decision_summary",
    "design_summary",
    "effect_sizes",
    "evidence_checklist",
    "exact_sign_flip",
    "exact_sign_test",
    "floor_decomposition",
    "holm_adjust",
    "identity_check",
    "missingness_report",
    "pair_series",
    "paired_bootstrap",
    "readout_decomposition",
]
