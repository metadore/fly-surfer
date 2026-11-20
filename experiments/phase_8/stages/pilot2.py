"""Pilot 2 (REV4 §10.8): paired dispersion and control certification.

SCIENTIFIC STATUS
    Pilot 2 measures the **paired dispersion** of C1–C4 so that the
    predeclared U7 sample-size rule can be applied once, before the campaign.
    It is not a hypothesis test, it estimates no campaign effect, and it is
    never merged into the campaign dataset (REV4 §10, "What the pilots do and
    do not establish"). The U7 decision itself is a human decision: this module
    reports :math:`\\sigma_{max}` and its one-sided upper confidence limit and
    an *indication*, and never writes ``design.n_seeds_selected``.

    The grid is fixed by REV4: 3 pilot seeds × {A, B, C, F, Fβ, A′, C′} × 3
    episodes. B, C and F/Fβ are required because ``σ_C2``, ``σ_C3``, ``σ_C1``
    and ``σ_C4`` cannot be estimated without them. A′ and C′ must be certified
    on all 3 seeds before the campaign is authorised.

    ``run_pilot2`` calls the campaign authorisation gate first and therefore
    refuses today. ``describe_pilot2`` and :func:`pilot2_plan` are read-only.
    :func:`evaluate_dispersion` reads stored rows only; it writes nothing,
    rejects non-pilot rows, and labels every output descriptive.

DISPERSION DEFINITION
    For each contrast the per-seed outcome is the mean capped survival score
    over the planned episodes of that arm, exactly as
    :func:`experiments.phase_8.analysis.arm_summary` defines it. The paired
    difference is ``minuend − subtrahend`` per seed; the paired sd is the
    sample sd (``ddof = 1``) of those differences. The one-sided upper
    confidence limit for σ is the declared closed form
    ``s · sqrt(df / χ²_{α, df})`` with ``α = 1 − confidence``; for ``df = 2``
    this is ``s · sqrt(2 / (−2 ln(1 − α)))`` (factor ≈ 2.11695 at 80 %).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import stdev
from typing import Any, Callable, Iterable, Mapping, Sequence

from ..analysis import MDE_COEFFICIENT
from ..campaign.graphs import CertifiedGraphSource
from ..campaign.protocol import CampaignNotAuthorized
from ..config import (
    ConfigError,
    MemoryGateError,
    PROJECT_ROOT,
    Phase8Config,
    load_phase8_config,
    memory_preflight,
)
from ..registry import CONFIRMATORY_CONTRASTS
from ..schema import SchemaError, validate_rows
from ..training.artifacts import TRAINING_ROOT
from ..training.loader import discover_artifact_directories
from .common import (
    NO_EXECUTION_NOTE,
    PilotPlan,
    StageConfigurationError,
    StageRefusal,
    authorization_snapshot,
    collect_blockers,
    design_snapshot,
    drive_pilot,
    memory_snapshot,
    stage_envelope,
)

PILOT2_STAGE = "pilot2"
PILOT2_REV4_STEP = "10.8"
PILOT2_ARMS = ("A", "B", "C", "F", "F_beta", "A_prime", "C_prime")
PILOT2_SEED_COUNT = 3
PILOT2_EPISODE_COUNT = 3
PILOT2_CONTRASTS = tuple(str(item["id"]) for item in CONFIRMATORY_CONTRASTS)

UCL_CONFIDENCE = 0.80
UCL_CONFIDENCE_CONSERVATIVE = 0.95

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2

#: Store-level fields compared for the A′≡A and C′≡C identity. The full P1–P19
#: comparison needs in-process state and is implemented in
#: :mod:`experiments.phase_8.controls.equivalence`; this is the reduced check
#: that can be recomputed from the stored JSONL (REV4 §3.8.6 final pass).
IDENTITY_FIELDS = (
    ("P3", "spike_sha256"),
    ("P4", "action_sha256"),
    ("P6", "survival_score"),
    ("P6", "steps"),
    ("P6", "observed_updates"),
    ("P6", "terminated"),
    ("P6", "truncated"),
    ("P6", "termination_reason"),
    ("P7", "action_counts"),
    ("P7", "no_action_fraction"),
    ("P8", "total_reward"),
    ("P10", "motor_spikes"),
    ("P12", "weights_before"),
    ("P14", "weights_after"),
)

IDENTITY_REQUIRED = {"A_prime": ("A", "B"), "C_prime": ("C", "D")}
IDENTITY_NOT_STORED = (
    "P1 (spike times), P2 (spike indices), P5 (record sequence), P9 (neural "
    "timings), P11 (structural digest), P13 (delta digest and exact zero "
    "delta), P15-P17 (delta diagnostics), P18 (stepper fingerprint) and P19 "
    "(resets) need in-process state; the pilot must run the full comparison "
    "in :mod:`experiments.phase_8.controls.equivalence` as well"
)


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def pilot2_seeds(config: Phase8Config) -> tuple[int, ...]:
    seeds = tuple(int(seed) for seed in config.campaign.pilot_seeds)
    if len(seeds) < PILOT2_SEED_COUNT:
        raise StageRefusal(
            PILOT2_STAGE,
            [
                f"Pilot 2 needs {PILOT2_SEED_COUNT} declared pilot seeds; "
                f"campaign.yaml declares {len(seeds)}"
            ],
        )
    return seeds[:PILOT2_SEED_COUNT]


def pilot2_plan(config: Phase8Config) -> PilotPlan:
    return PilotPlan(
        stage=PILOT2_STAGE,
        rev4_step=PILOT2_REV4_STEP,
        arms=PILOT2_ARMS,
        seeds=pilot2_seeds(config),
        episodes=PILOT2_EPISODE_COUNT,
        establishes=(
            "the paired sd of C1-C4 (sigma_max and its one-sided upper "
            "confidence limit), the A'=A and C'=C identity on all 3 pilot "
            "seeds, and that F-beta is a functioning constant-action control"
        ),
        does_not_establish=(
            "no hypothesis is tested; no campaign effect is estimated and no "
            "campaign row is produced; the predeclared U7 N decision is "
            "reported as an indication only and is never recorded here; the "
            "pilot rows are never merged into the campaign dataset"
        ),
        estimates_contrasts=False,
    )


# ---------------------------------------------------------------------------
# readiness
# ---------------------------------------------------------------------------


def pilot2_readiness(
    config: Phase8Config,
    *,
    source: CertifiedGraphSource | None = None,
    preflight: Callable[[float], dict] = memory_preflight,
) -> dict:
    """Declare what Pilot 2 needs and what is missing today.

    Two blockers are structural, not operational: certification covers the
    campaign seeds only, and the training-artifact loader accepts only seeds
    declared in ``seeds.campaign``. Neither may be worked around by
    substituting a campaign seed or an untrained artifact.
    """
    seeds = pilot2_seeds(config)
    source = source or CertifiedGraphSource()
    certified = set(int(seed) for seed in source.required_seeds)
    graph_coverage = {seed: seed in certified for seed in seeds}

    artifact_directories = discover_artifact_directories(PROJECT_ROOT / TRAINING_ROOT)
    artifact_keys = sorted(
        f"{path.parent.name}:{path.name}" for path in artifact_directories
    )
    artifact_seeds = sorted(
        {int(path.name) for path in artifact_directories if path.name.isdigit()}
    )
    pilot_artifact_keys = sorted(
        f"{path.parent.name}:{path.name}"
        for path in artifact_directories
        if path.name.isdigit() and int(path.name) in set(seeds)
    )
    loader_accepts = sorted(set(seeds) & set(int(s) for s in config.campaign.campaign_seeds))

    memory = memory_snapshot(config, preflight=preflight)

    blockers: list[str] = []
    if not all(graph_coverage.values()):
        absent = sorted(seed for seed, present in graph_coverage.items() if not present)
        blockers.append(
            "P2-G: no certified random graph exists for pilot seed(s) "
            f"{absent}; certification covers the campaign seeds "
            f"{sorted(certified)} only, so C and C' cannot run on the pilot "
            "grid and a campaign graph may not be substituted"
        )
    if not loader_accepts:
        blockers.append(
            "P2-A: the training-artifact loader accepts only seeds declared in "
            "seeds.campaign, and no pilot seed is declared there; trained F, "
            "F-beta and E artifacts for the pilot seeds therefore cannot be "
            "loaded. Resolving this is an owner decision (a declared pilot "
            "training set or an approved change of the loader contract), never "
            "a silent substitution"
        )
    if not pilot_artifact_keys:
        blockers.append(
            "P2-A: no trained artifact directory exists for pilot seed(s) "
            f"{list(seeds)} under {TRAINING_ROOT.as_posix()}"
        )
    blockers.extend(memory["blockers"])

    return {
        "seeds": list(seeds),
        "episodes_per_seed": PILOT2_EPISODE_COUNT,
        "arms": list(PILOT2_ARMS),
        "certified_graphs": {
            "root": source.root.as_posix(),
            "certified_seeds": sorted(certified),
            "pilot_seed_coverage": graph_coverage,
        },
        "training_artifacts": {
            "root": (PROJECT_ROOT / TRAINING_ROOT).as_posix(),
            "directories": len(artifact_directories),
            "seeds": artifact_seeds,
            "pilot_seed_keys": pilot_artifact_keys,
            "loader_accepts_seeds": loader_accepts,
        },
        "memory_preflight": memory,
        "ready": not blockers,
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# dispersion
# ---------------------------------------------------------------------------


def upper_confidence_factor(df: int, confidence: float) -> float:
    """One-sided upper-limit factor ``sqrt(df / chi2_{alpha, df})``.

    ``alpha = 1 - confidence``. At ``df = 2`` the lower chi-square quantile is
    ``-2 ln(1 - alpha)`` in closed form (REV4 §7.4 / U7); other df use the
    declared SciPy quantile rather than an approximation.
    """
    if isinstance(df, bool) or not isinstance(df, int) or df <= 0:
        raise StageConfigurationError("degrees of freedom must be a positive int")
    if not 0.0 < float(confidence) < 1.0:
        raise StageConfigurationError("confidence must lie strictly inside (0, 1)")
    alpha = 1.0 - float(confidence)
    if df == 2:
        lower = -2.0 * math.log1p(-alpha)
    else:  # pragma: no cover - the declared pilot has df = 2
        try:
            from scipy.stats import chi2
        except ImportError as error:
            raise StageConfigurationError(
                "a df != 2 upper confidence limit requires SciPy"
            ) from error
        lower = float(chi2.ppf(alpha, df))
    if lower <= 0.0:
        raise StageConfigurationError("the chi-square quantile must be positive")
    return math.sqrt(df / lower)


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(text)).strip("_")


def _index_rows(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, int, int], dict]:
    index: dict[tuple[str, int, int], dict] = {}
    for row in rows:
        key = (str(row["condition"]), int(row["seed"]), int(row["episode"]))
        index[key] = dict(row)
    return index


def _pilot_rows(
    rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]
) -> list[dict]:
    try:
        validated = validate_rows(rows)
    except SchemaError as error:
        raise StageConfigurationError(f"pilot rows fail validation: {error}") from None
    allowed_seeds = {int(seed) for seed in seeds}
    foreign_seeds = sorted({int(row["seed"]) for row in validated} - allowed_seeds)
    if foreign_seeds:
        raise StageConfigurationError(
            "refusing to mix pilot rows with non-pilot seed(s) "
            f"{foreign_seeds}; pilot and campaign datasets are never merged"
        )
    foreign_arms = sorted({str(row["condition"]) for row in validated} - set(PILOT2_ARMS))
    if foreign_arms:
        raise StageConfigurationError(
            f"pilot 2 does not declare arm(s) {foreign_arms}"
        )
    return validated


def _evidence_kind(rows: Sequence[Mapping[str, Any]]) -> dict:
    labels = {
        str((row.get("notes") or {}).get("evidence_kind"))
        for row in rows
        if isinstance(row.get("notes"), Mapping)
        and (row.get("notes") or {}).get("evidence_kind")
    }
    if labels and labels != {"synthetic_fixture"}:
        raise StageConfigurationError(
            f"unexpected evidence labels on pilot rows: {sorted(labels)}"
        )
    synthetic = labels == {"synthetic_fixture"}
    return {
        "evidence_kind": "synthetic_fixture" if synthetic else "pilot",
        "experimental_evidence": not synthetic,
        "synthetic_rows": synthetic,
    }


def _seed_outcome(
    index: Mapping[tuple[str, int, int], dict],
    arm: str,
    seed: int,
    episodes: int,
) -> dict:
    missing: list[int] = []
    errors: list[int] = []
    scores: list[float] = []
    for episode in range(int(episodes)):
        row = index.get((arm, int(seed), int(episode)))
        if row is None:
            missing.append(episode)
            continue
        if row.get("status", "ok") != "ok":
            errors.append(episode)
            continue
        scores.append(float(row["survival_score"]))
    complete = not missing and not errors
    return {
        "arm": arm,
        "seed": int(seed),
        "episodes_planned": int(episodes),
        "episodes_present": len(scores) + len(errors),
        "episodes_ok": len(scores),
        "episodes_missing": missing,
        "episodes_error": errors,
        "complete": complete,
        "mean_capped_score": (
            math.fsum(scores) / len(scores) if complete and scores else None
        ),
    }


def _contrast_dispersion(
    index: Mapping[tuple[str, int, int], dict],
    contrast: Mapping[str, Any],
    seeds: Sequence[int],
    episodes: int,
    *,
    confidence: float,
) -> dict:
    minuend, subtrahend = str(contrast["minuend"]), str(contrast["subtrahend"])
    entries = []
    for seed in seeds:
        left = _seed_outcome(index, minuend, seed, episodes)
        right = _seed_outcome(index, subtrahend, seed, episodes)
        paired = (
            left["mean_capped_score"] - right["mean_capped_score"]
            if left["complete"] and right["complete"]
            else None
        )
        entries.append(
            {
                "seed": int(seed),
                "minuend": left,
                "subtrahend": right,
                "complete_pair": paired is not None,
                "paired_difference": paired,
            }
        )

    differences = [entry["paired_difference"] for entry in entries if entry["complete_pair"]]
    n_pairs = len(differences)
    evaluable = n_pairs == len(seeds) and n_pairs >= 2
    sd = stdev(differences) if evaluable else None
    df = n_pairs - 1
    ucl = (
        sd * upper_confidence_factor(df, confidence)
        if evaluable and sd is not None
        else None
    )
    ucl95 = (
        sd * upper_confidence_factor(df, UCL_CONFIDENCE_CONSERVATIVE)
        if evaluable and sd is not None
        else None
    )
    return {
        "id": str(contrast["id"]),
        "minuend": minuend,
        "subtrahend": subtrahend,
        "hypothesis": contrast.get("hypothesis"),
        "question": contrast.get("question"),
        "status": "evaluable" if evaluable else "not_evaluable",
        "reason": (
            None
            if evaluable
            else (
                f"{n_pairs} of {len(seeds)} planned pairs are complete; a paired "
                "sd needs every planned seed and at least two complete pairs"
            )
        ),
        "n_seeds": len(seeds),
        "n_complete_pairs": n_pairs,
        "df": df if evaluable else None,
        "paired_sd": sd,
        "ucl80": ucl,
        "ucl95": ucl95,
        "mean_paired_difference": (
            math.fsum(differences) / n_pairs if evaluable else None
        ),
        "per_seed": entries,
        "is_hypothesis_test": False,
    }


def _identity_check(
    index: Mapping[tuple[str, int, int], dict],
    control_arm: str,
    fixed_arm: str,
    seeds: Sequence[int],
    episodes: int,
) -> dict:
    expected = len(seeds) * int(episodes)
    compared = 0
    missing: list[dict] = []
    mismatches: list[dict] = []
    for seed in seeds:
        for episode in range(int(episodes)):
            control = index.get((control_arm, int(seed), episode))
            fixed = index.get((fixed_arm, int(seed), episode))
            if control is None or fixed is None:
                missing.append(
                    {
                        "seed": int(seed),
                        "episode": episode,
                        "control_present": control is not None,
                        "fixed_present": fixed is not None,
                    }
                )
                continue
            compared += 1
            for field_id, field in IDENTITY_FIELDS:
                left, right = control.get(field), fixed.get(field)
                if json.dumps(left, sort_keys=True) != json.dumps(right, sort_keys=True):
                    mismatches.append(
                        {
                            "field_id": field_id,
                            "field": field,
                            "seed": int(seed),
                            "episode": episode,
                            "control": control_arm,
                            "fixed": fixed_arm,
                            "control_value": left,
                            "fixed_value": right,
                        }
                    )
    evaluated = not missing
    passed = evaluated and not mismatches
    invalidates = list(IDENTITY_REQUIRED[control_arm][1:])
    return {
        "control": control_arm,
        "fixed": fixed_arm,
        "scope": (
            "store-level reduced comparison over P3, P4, P6, P7, P8, P10, P12 "
            "and P14"
        ),
        "not_stored": IDENTITY_NOT_STORED,
        "evaluated": evaluated,
        "passed": passed,
        "pairs_expected": expected,
        "pairs_compared": compared,
        "missing": missing,
        "mismatches": mismatches,
        "hard_stop": evaluated and bool(mismatches),
        "invalidates": invalidates if (not passed) else [],
        "reason": (
            None
            if passed
            else (
                "coverage is incomplete; absence is not a pass (REV4 §3.8.5)"
                if not evaluated
                else "an exact mismatch is a hard stop (REV4 §3.8.4/§3.8.5)"
            )
        ),
    }


def _constant_action_check(
    index: Mapping[tuple[str, int, int], dict],
    arm: str,
    seeds: Sequence[int],
    episodes: int,
) -> dict:
    """A state-independent control must take one action on every decision."""
    entries = []
    for seed in seeds:
        for episode in range(int(episodes)):
            row = index.get((arm, int(seed), episode))
            if row is None or row.get("status", "ok") != "ok":
                entries.append(
                    {"seed": int(seed), "episode": episode, "available": False}
                )
                continue
            counts = {
                action: int(value)
                for action, value in dict(row["action_counts"]).items()
                if int(value) > 0
            }
            entries.append(
                {
                    "seed": int(seed),
                    "episode": episode,
                    "available": True,
                    "actions_observed": sorted(counts),
                    "constant": len(counts) == 1,
                }
            )
    available = [entry for entry in entries if entry["available"]]
    return {
        "arm": arm,
        "definition": "one action on every decision (REV4 §3.6.2)",
        "episodes_available": len(available),
        "episodes_expected": len(seeds) * int(episodes),
        "constant_everywhere": bool(available) and all(
            entry["constant"] for entry in available
        ) and len(available) == len(seeds) * int(episodes),
        "entries": entries,
    }


def _u7_indication(
    sigma_max: float | None,
    ucl80_max: float | None,
    config: Phase8Config,
) -> dict:
    campaign = config.campaign
    fallback_bound = float(campaign.fallback_max_paired_sd)
    primary_bound = float(
        campaign.sei_updates * math.sqrt(campaign.n_seeds_primary) / MDE_COEFFICIENT
    )
    if ucl80_max is None:
        indication = "not_evaluable"
        reason = "no contrast has a complete three-seed paired sd"
    elif ucl80_max <= fallback_bound:
        indication = "fallback_N_may_be_defensible"
        reason = (
            f"the 80% upper limit {ucl80_max:.4f} is at or below "
            f"{fallback_bound:.2f}; U7 still requires a human decision and a "
            "3-seed pilot generally cannot defend the fallback"
        )
    elif ucl80_max <= primary_bound:
        indication = "primary_N_indicated"
        reason = (
            f"the 80% upper limit {ucl80_max:.4f} exceeds {fallback_bound:.2f}, "
            f"so the fallback is not permissible; it is within the primary "
            f"design's {primary_bound:.2f}"
        )
    else:  # pragma: no cover - a real pilot would drive this branch
        indication = "escalate_above_primary_N"
        reason = (
            f"the 80% upper limit {ucl80_max:.4f} exceeds {primary_bound:.2f}; "
            "REV4 §7.4 requires N above 16, which a larger pilot or "
            "independent variance evidence must justify before any campaign"
        )
    return {
        "decision_recorded": False,
        "recorded_n_seeds_selected": campaign.n_seeds_selected,
        "sigma_max": sigma_max,
        "ucl80_sigma_max": ucl80_max,
        "fallback_bound": fallback_bound,
        "primary_supported_bound": primary_bound,
        "indication": indication,
        "reason": reason,
        "note": (
            "the U7 decision is made by the owner before the campaign; this "
            "evaluator never sets design.n_seeds_selected and never revisits "
            "the choice after campaign outcomes are seen"
        ),
    }


def evaluate_dispersion(
    rows: Sequence[Mapping[str, Any]],
    config: Phase8Config,
    *,
    seeds: Sequence[int] | None = None,
    episodes: int = PILOT2_EPISODE_COUNT,
    confidence: float = UCL_CONFIDENCE,
) -> dict:
    """Read-only Pilot 2 evaluation of stored pilot rows.

    No hypothesis is tested, no campaign effect is estimated and nothing is
    written. Rows whose seed is not a declared pilot seed are rejected rather
    than merged.
    """
    pilot_seeds = tuple(int(seed) for seed in (seeds or pilot2_seeds(config)))
    validated = _pilot_rows(rows, pilot_seeds)
    labels = _evidence_kind(validated)
    index = _index_rows(validated)

    contrasts = [
        _contrast_dispersion(
            index, contrast, pilot_seeds, episodes, confidence=confidence
        )
        for contrast in CONFIRMATORY_CONTRASTS
    ]
    evaluable = [item for item in contrasts if item["status"] == "evaluable"]
    sigma_max = max((item["paired_sd"] for item in evaluable), default=None)
    ucl80_max = max((item["ucl80"] for item in evaluable), default=None)
    ucl95_max = max((item["ucl95"] for item in evaluable), default=None)
    sigma_max_contrast = None
    if sigma_max is not None:
        sigma_max_contrast = next(
            item["id"] for item in evaluable if item["paired_sd"] == sigma_max
        )

    identity = {
        control: _identity_check(
            index, control, fixed, pilot_seeds, episodes
        )
        for control, (fixed, _invalidates) in IDENTITY_REQUIRED.items()
    }
    f_beta = _constant_action_check(index, "F_beta", pilot_seeds, episodes)
    u7 = _u7_indication(sigma_max, ucl80_max, config)

    return {
        "record_kind": "phase_8_pilot2_dispersion",
        "stage": PILOT2_STAGE,
        "rev4_step": PILOT2_REV4_STEP,
        "evidence_kind": labels["evidence_kind"],
        "experimental_evidence": labels["experimental_evidence"],
        "rows_evaluated": len(validated),
        "seeds": list(pilot_seeds),
        "episodes_per_seed": int(episodes),
        "arms": list(PILOT2_ARMS),
        "contrasts": contrasts,
        "sigma_max": sigma_max,
        "sigma_max_contrast": sigma_max_contrast,
        "ucl80_sigma_max": ucl80_max,
        "ucl95_sigma_max": ucl95_max,
        "confidence": float(confidence),
        "identity": identity,
        "f_beta_constant_action": f_beta,
        "u7": u7,
        "estimates_contrasts": False,
        "hypothesis_tests": [],
        "campaign_effects_estimated": False,
        "merged_into_campaign": False,
        "complete": (
            all(item["status"] == "evaluable" for item in contrasts)
            and all(item["evaluated"] for item in identity.values())
        ),
        "note": (
            "descriptive dispersion for the predeclared U7 decision; no "
            "hypothesis is tested and no campaign row is produced"
        ),
    }


# ---------------------------------------------------------------------------
# read-only description and gated runner
# ---------------------------------------------------------------------------


def describe_pilot2(
    config: Phase8Config,
    *,
    preflight: Callable[[float], dict] = memory_preflight,
) -> dict:
    plan = pilot2_plan(config)
    authorization = authorization_snapshot()
    design = design_snapshot(config)
    memory = memory_snapshot(config, preflight=preflight)
    readiness = pilot2_readiness(config, preflight=preflight)

    blockers: list[str] = []
    for item in (
        list(collect_blockers(config, preflight=preflight))
        + list(readiness["blockers"])
    ):
        if item not in blockers:
            blockers.append(item)

    record = stage_envelope(PILOT2_STAGE)
    record.update(
        {
            "plan": plan.as_dict(config.campaign.master_seed),
            "authorization": authorization,
            "design": design,
            "memory_preflight": memory,
            "readiness": readiness,
            "frozen_constants": {
                "pilot_seeds": list(plan.seeds),
                "episodes_per_seed": plan.episodes,
                "max_game_updates": config.campaign.max_game_updates,
                "ucl_confidence": UCL_CONFIDENCE,
                "fallback_max_paired_sd": config.campaign.fallback_max_paired_sd,
            },
            "contrasts_estimated": [],
            "hypothesis_tests": [],
            "campaign_effects_estimated": False,
            "merged_into_campaign": False,
            "executable": False,
            "execution_blockers": blockers,
            "note": NO_EXECUTION_NOTE,
        }
    )
    return record


def run_pilot2(
    config: Phase8Config,
    *,
    base_dir: str | Path | None = None,
    run_id: str = "pilot2",
    episode_runner: Callable[..., Any] | None = None,
    preflight: Callable[[float], dict] = memory_preflight,
    synthetic_fixture: bool = False,
    **driver_kwargs: Any,
) -> dict:
    """Refuse unless the protocol authorises execution.

    ``synthetic_fixture=True`` is the labelled harness path: it refuses the
    real results root and stamps every row ``synthetic_fixture``.
    """
    plan = pilot2_plan(config)
    directory = base_dir if base_dir is not None else (
        PROJECT_ROOT / config.campaign.results_root / PILOT2_STAGE
    )
    return drive_pilot(
        plan,
        config,
        base_dir=directory,
        run_id=run_id,
        episode_runner=episode_runner,
        preflight=preflight,
        synthetic_fixture=synthetic_fixture,
        **driver_kwargs,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _emit(payload: dict, pretty: bool) -> None:
    sys.stdout.write(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n"
    )


def _load(args: argparse.Namespace) -> Phase8Config:
    return load_phase8_config(
        environment_path=args.environment,
        campaign_path=args.campaign,
        conditions_path=args.conditions,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pilot2",
        description=(
            "Pilot 2 (REV4 §10.8): describe the paired-dispersion grid, "
            "evaluate stored pilot rows, or refuse to run."
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--describe", action="store_true", help="emit the read-only plan")
    parser.add_argument("--evaluate", default=None, help="episodes.jsonl to evaluate read-only")
    parser.add_argument("--run", action="store_true", help="refused while unapproved")
    parser.add_argument("--base-dir", default=None)
    parser.add_argument("--run-id", default="pilot2")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load(args)
        if args.evaluate:
            from ..store import read_store

            try:
                rows = read_store(args.evaluate)
            except Exception as error:  # StoreError and schema failures
                sys.stderr.write(f"pilot2 cannot read rows: {error}\n")
                return EXIT_INCOMPLETE
            payload = evaluate_dispersion(rows, config)
            payload["command"] = "evaluate"
            payload["note"] = (
                "read-only evaluation; no episode was executed and no file was "
                "written"
            )
            _emit(payload, args.pretty)
            return EXIT_OK if payload["complete"] else EXIT_INCOMPLETE
        if args.run:
            payload = describe_pilot2(config)
            payload["command"] = "run"
            try:
                run_pilot2(
                    config,
                    base_dir=args.base_dir,
                    run_id=args.run_id,
                    episode_runner=None,
                )
            except (CampaignNotAuthorized, StageRefusal, MemoryGateError) as error:
                payload["refused"] = True
                payload["reason"] = str(error)
                _emit(payload, args.pretty)
                return EXIT_REFUSED
            payload["refused"] = False
            _emit(payload, args.pretty)
            return EXIT_OK
        payload = describe_pilot2(config)
        payload["command"] = "describe"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, StageConfigurationError) as error:
        sys.stderr.write(f"pilot2 configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "PILOT2_ARMS",
    "PILOT2_CONTRASTS",
    "PILOT2_EPISODE_COUNT",
    "PILOT2_REV4_STEP",
    "PILOT2_SEED_COUNT",
    "PILOT2_STAGE",
    "UCL_CONFIDENCE",
    "UCL_CONFIDENCE_CONSERVATIVE",
    "describe_pilot2",
    "evaluate_dispersion",
    "main",
    "pilot2_plan",
    "pilot2_readiness",
    "pilot2_seeds",
    "run_pilot2",
    "upper_confidence_factor",
]
