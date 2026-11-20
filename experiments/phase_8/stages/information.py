"""Information analyses for Phase 8 (REV4 §5.4 and §10.11) — descriptive only.

SCIENTIFIC STATUS
    Every quantity here is a **descriptive** summary of stored episode rows.
    REV4 §5.4 labels event-class entropy, decoder-state entropy and the
    feature→action mutual information *exploratory*, and the mutual information
    is explicitly **non-confirmatory**: it cannot alter the Phase 6 conclusion
    and every such value must be labelled "in a new substrate".

    The adapter therefore:

    * computes action-count entropy and the optional decision-class entropy
      with the frozen Phase 6 estimator
      (:func:`information.entropy.entropy_from_counts`), per seed and pooled
      for description only;
    * keeps the seed as the independent unit (REV4 §7.2) and never treats a
      decision as an independent replicate for inference;
    * reports the feature→action mutual information as **not available** from
      the episode store, because the store has no per-decision feature vector;
    * records no hypothesis test, no p-value and no confirmatory label;
    * never writes anything and never touches Phase 6 artefacts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from information.entropy import entropy_from_counts
from readout.ablation import ABLATION_LABELS
from readout.features import ACTION_SPACE

from ..config import ConfigError, Phase8Config, load_phase8_config
from ..schema import SchemaError, validate_rows
from .common import (
    NO_EXECUTION_NOTE,
    StageConfigurationError,
    stage_envelope,
)

INFORMATION_STAGE = "information"
INFORMATION_REV4_STEP = "10.11 / §5.4"
INFORMATION_VERSION = 1

EXIT_OK = 0
EXIT_INCOMPLETE = 1

FEATURE_ACTION_LABEL = (
    "exploratory, non-confirmatory; in a new substrate; cannot alter the "
    "Phase 6 conclusion"
)


def describe_information_analyses() -> dict:
    """The §5.4 catalogue, with what the episode store can and cannot support."""
    outcomes = [
        {
            "outcome": "Action distribution per condition",
            "status": "secondary",
            "source": "action_counts",
            "available_from_store": True,
        },
        {
            "outcome": "Fraction of updates with NO_ACTION",
            "status": "secondary",
            "source": "no_action_fraction",
            "available_from_store": True,
        },
        {
            "outcome": "Total task reward per episode",
            "status": "secondary",
            "source": "total_reward",
            "available_from_store": True,
        },
        {
            "outcome": "Motor-population spikes per decision",
            "status": "secondary",
            "source": "motor_spikes (episode total)",
            "available_from_store": True,
            "note": (
                "the store keeps the episode total, not one value per decision; "
                "a per-decision series is not reconstructed here"
            ),
        },
        {
            "outcome": "Event-class entropy",
            "status": "exploratory",
            "source": "action_counts via the Phase 6 plug-in estimator",
            "available_from_store": True,
            "estimator": "information.entropy.entropy_from_counts",
        },
        {
            "outcome": "Decoder-state entropy",
            "status": "exploratory",
            "source": "decision_classes (the four §3.6.3 ablation labels)",
            "available_from_store": True,
            "note": (
                "the stored ablation labels are the decoder-state proxy; rows "
                "without decision_classes leave this outcome missing, not zero"
            ),
        },
        {
            "outcome": "Cue/feature -> action mutual information",
            "status": "exploratory, non-confirmatory",
            "source": "per-decision feature and action records",
            "available_from_store": False,
            "label": FEATURE_ACTION_LABEL,
            "reason": (
                "the episode store records action_counts and optional "
                "decision_classes, not the per-decision sensory feature vector, "
                "so the estimate cannot be computed from stored rows and must "
                "not be invented"
            ),
        },
        {
            "outcome": "Mean firing rate, sensory-population recruitment",
            "status": "descriptive",
            "source": "per-decision neural recordings",
            "available_from_store": False,
            "reason": "no per-decision neural summary is stored in the row",
        },
        {
            "outcome": "Coins collected, collisions, obstacles avoided",
            "status": "not available",
            "source": "-",
            "available_from_store": False,
            "reason": (
                "no coin population exists, no per-obstacle outcome is stored "
                "and the obstacle reward component is configured to zero; "
                "these must not be invented (REV4 §5.4)"
            ),
        },
    ]
    return {
        "record_kind": "phase_8_information_catalogue",
        "stage": INFORMATION_STAGE,
        "rev4_step": INFORMATION_REV4_STEP,
        "version": INFORMATION_VERSION,
        "outcomes": outcomes,
        "labels": {
            "confirmatory": False,
            "exploratory": True,
            "feature_action_mutual_information": FEATURE_ACTION_LABEL,
        },
        "phase_6": {
            "artefacts_untouched": True,
            "conclusion_can_change": False,
        },
        "note": NO_EXECUTION_NOTE,
    }


def _labels(rows: Sequence[Mapping[str, Any]]) -> dict:
    labels = {
        str((row.get("notes") or {}).get("evidence_kind"))
        for row in rows
        if isinstance(row.get("notes"), Mapping)
        and (row.get("notes") or {}).get("evidence_kind")
    }
    if labels and labels != {"synthetic_fixture"}:
        raise StageConfigurationError(
            f"unexpected evidence labels: {sorted(labels)}"
        )
    synthetic = labels == {"synthetic_fixture"}
    return {
        "evidence_kind": "synthetic_fixture" if synthetic else "campaign",
        "experimental_evidence": not synthetic,
    }


def _index_rows(
    rows: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, int, int], dict]:
    index: dict[tuple[str, int, int], dict] = {}
    for row in rows:
        index[(str(row["condition"]), int(row["seed"]), int(row["episode"]))] = dict(row)
    return index


def _counts(mapping: Mapping[str, Any], space: Sequence[str]) -> np.ndarray:
    return np.asarray([int(mapping.get(name, 0)) for name in space], dtype=np.int64)


def _mean(values: Sequence[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def _seed_summary(
    index: Mapping[tuple[str, int, int], dict],
    arm: str,
    seed: int,
    *,
    episodes: int | None,
) -> dict:
    stored = sorted(
        (episode, row)
        for (condition, row_seed, episode), row in index.items()
        if condition == arm and row_seed == int(seed)
    )
    selected = [
        (episode, row)
        for episode, row in stored
        if episodes is None or episode < int(episodes)
    ]
    ok = [(episode, row) for episode, row in selected if row.get("status", "ok") == "ok"]
    errors = [episode for episode, row in selected if row.get("status") != "ok"]

    action_counts = {name: 0 for name in ACTION_SPACE}
    class_counts = {name: 0 for name in ABLATION_LABELS}
    steps = 0
    motor_spikes = 0
    total_reward = 0.0
    rows_with_classes = 0
    for _episode, row in ok:
        for name in ACTION_SPACE:
            action_counts[name] += int(dict(row["action_counts"]).get(name, 0))
        steps += int(row["steps"])
        motor_spikes += int(row["motor_spikes"])
        total_reward += float(row["total_reward"])
        classes = row.get("decision_classes")
        if isinstance(classes, Mapping):
            rows_with_classes += 1
            for name in ABLATION_LABELS:
                class_counts[name] += int(classes.get(name, 0))

    action_entropy = (
        entropy_from_counts(_counts(action_counts, ACTION_SPACE))
        if steps > 0
        else None
    )
    class_total = sum(class_counts.values())
    class_entropy = (
        entropy_from_counts(_counts(class_counts, ABLATION_LABELS))
        if class_total > 0
        else None
    )
    missing = (
        [episode for episode in range(int(episodes)) if episode not in dict(stored)]
        if episodes is not None
        else []
    )
    return {
        "arm": arm,
        "seed": int(seed),
        "episodes_stored": len(stored),
        "episodes_selected": len(selected),
        "episodes_ok": len(ok),
        "episodes_error": errors,
        "episodes_missing": missing,
        "updates": steps,
        "action_counts": action_counts,
        "action_entropy_bits": action_entropy,
        "no_action_fraction": (
            action_counts["NO_ACTION"] / steps if steps else None
        ),
        "decision_classes_present": rows_with_classes > 0 and rows_with_classes == len(ok),
        "decision_classes": class_counts,
        "decoder_state_entropy_bits": class_entropy,
        "motor_spikes": motor_spikes,
        "total_reward": total_reward,
        "mean_total_reward": (total_reward / len(ok)) if ok else None,
    }


def analyse_information(
    rows: Sequence[Mapping[str, Any]],
    config: Phase8Config,
    *,
    episodes: int | None = None,
    arms: Sequence[str] | None = None,
) -> dict:
    """Read-only descriptive summaries. Nothing is inferred or tested.

    ``episodes`` is the declared per-seed episode count; when it is given, a
    short seed reports its missing episodes explicitly and is not treated as a
    complete unit. When it is ``None`` only what is stored is summarised.
    """
    try:
        validated = validate_rows(rows)
    except SchemaError as error:
        raise StageConfigurationError(f"rows fail validation: {error}") from None
    if not validated:
        raise StageConfigurationError("no rows to summarise")
    labels = _labels(validated)
    index = _index_rows(validated)

    declared_arms = tuple(
        arms
        or (
            config.campaign.conditions
            + config.campaign.control_arms
            + config.campaign.exploratory_arms
            + (config.campaign.floor_arm,)
        )
    )
    observed_arms = sorted({str(row["condition"]) for row in validated})
    arms = tuple(arm for arm in declared_arms if arm in observed_arms)
    seeds = sorted({int(row["seed"]) for row in validated})

    per_arm: dict[str, dict] = {}
    for arm in arms:
        arm_seeds = sorted({key[1] for key in index if key[0] == arm})
        seed_entries = [
            _seed_summary(index, arm, seed, episodes=episodes)
            for seed in arm_seeds
        ]
        action_entropies = [
            entry["action_entropy_bits"]
            for entry in seed_entries
            if entry["action_entropy_bits"] is not None
        ]
        class_entropies = [
            entry["decoder_state_entropy_bits"]
            for entry in seed_entries
            if entry["decoder_state_entropy_bits"] is not None
        ]
        pooled_actions = {
            name: sum(entry["action_counts"][name] for entry in seed_entries)
            for name in ACTION_SPACE
        }
        pooled_classes = {
            name: sum(entry["decision_classes"][name] for entry in seed_entries)
            for name in ABLATION_LABELS
        }
        pooled_steps = sum(entry["updates"] for entry in seed_entries)
        pooled_class_total = sum(pooled_classes.values())
        per_arm[arm] = {
            "arm": arm,
            "seeds": [entry["seed"] for entry in seed_entries],
            "per_seed": seed_entries,
            "action_distribution_pooled": {
                name: (value / pooled_steps if pooled_steps else None)
                for name, value in pooled_actions.items()
            },
            "no_action_fraction_pooled": (
                pooled_actions["NO_ACTION"] / pooled_steps
                if pooled_steps
                else None
            ),
            "event_class_entropy_bits": {
                "meaning": "action-count entropy, pooled and per seed",
                "per_seed_mean": _mean(action_entropies),
                "per_seed_median": median(action_entropies) if action_entropies else None,
                "pooled": (
                    entropy_from_counts(_counts(pooled_actions, ACTION_SPACE))
                    if pooled_steps
                    else None
                ),
                "seeds_with_data": len(action_entropies),
            },
            "decoder_state_entropy_bits": {
                "meaning": (
                    "entropy of the four §3.6.3 decision labels, the stored "
                    "decoder-state proxy"
                ),
                "per_seed_mean": _mean(class_entropies),
                "per_seed_median": median(class_entropies) if class_entropies else None,
                "pooled": (
                    entropy_from_counts(_counts(pooled_classes, ABLATION_LABELS))
                    if pooled_class_total
                    else None
                ),
                "seeds_with_data": len(class_entropies),
                "missing": [
                    entry["seed"]
                    for entry in seed_entries
                    if entry["decoder_state_entropy_bits"] is None
                ],
            },
            "motor_spikes_total": sum(entry["motor_spikes"] for entry in seed_entries),
            "total_reward": math.fsum(
                entry["total_reward"] for entry in seed_entries
            ),
        }

    record = stage_envelope(
        INFORMATION_STAGE,
        executed=False,
        evidence_kind=(
            "synthetic_fixture"
            if labels["evidence_kind"] == "synthetic_fixture"
            else "analysis"
        ),
    )
    record.update(
        {
            "version": INFORMATION_VERSION,
            "evidence_kind": labels["evidence_kind"],
            "experimental_evidence": labels["experimental_evidence"],
            "analysis_kind": "descriptive",
            "descriptive": True,
            "exploratory": True,
            "confirmatory": False,
            "unit_of_analysis": (
                "seed; pooled per-decision and per-episode aggregates are "
                "descriptive only and never treated as independent replicates"
            ),
            "rows_evaluated": len(validated),
            "arms": list(arms),
            "seeds": list(seeds),
            "declared_episodes_per_seed": episodes,
            "per_arm": per_arm,
            "feature_action_mutual_information": {
                "available": False,
                "status": "not_available",
                "label": FEATURE_ACTION_LABEL,
                "reason": (
                    "stored rows carry action_counts and optional "
                    "decision_classes, not the per-decision feature vector; "
                    "the estimate is not reconstructed and not invented"
                ),
                "estimator": "information.entropy would be the Phase 6 "
                "estimator once per-decision features exist",
            },
            "not_available": [
                "cue/feature -> action mutual information",
                "mean firing rate and sensory-population recruitment",
                "coins collected, collisions and obstacles avoided",
            ],
            "hypothesis_tests": [],
            "p_values": None,
            "phase_6": {
                "artefacts_untouched": True,
                "conclusion_can_change": False,
                "note": (
                    "any information value from this substrate is new-substrate "
                    "exploratory evidence and cannot alter the Phase 6 result"
                ),
            },
            "note": (
                "descriptive information summary of stored rows; no episode "
                "was executed and no file was written"
            ),
        }
    )
    return record


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
        prog="information",
        description=(
            "Phase 8 §5.4 information analyses: describe the catalogue, or "
            "summarise stored rows descriptively. No hypothesis is tested."
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--describe", action="store_true", help="emit the §5.4 catalogue")
    parser.add_argument("--analyse", default=None, help="episodes.jsonl to summarise")
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="declared episodes per seed; enables the missingness report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.analyse:
            from ..store import read_store

            config = _load(args)
            try:
                rows = read_store(args.analyse)
            except Exception as error:  # StoreError and schema failures
                sys.stderr.write(f"information cannot read rows: {error}\n")
                return EXIT_INCOMPLETE
            payload = analyse_information(rows, config, episodes=args.episodes)
            payload["command"] = "analyse"
            _emit(payload, args.pretty)
            return EXIT_OK
        payload = describe_information_analyses()
        payload["command"] = "describe"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, StageConfigurationError) as error:
        sys.stderr.write(f"information configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "FEATURE_ACTION_LABEL",
    "INFORMATION_REV4_STEP",
    "INFORMATION_STAGE",
    "INFORMATION_VERSION",
    "analyse_information",
    "describe_information_analyses",
    "main",
]
