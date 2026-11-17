"""Frozen-parameter motor-feature ablation and decision labels.

SCIENTIFIC STATUS
    The ablation is a counterfactual on a frozen model: the feature vector is
    set to zero and the logits are recomputed with the same parameters. It is
    not an intervention on the animal, the connectome or the game.

The four labels are those fixed in Phase 8 §3.6.3. They classify one recorded
decision each; the counts and fractions are written to the episode row so the
classification is auditable without rerunning anything.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .features import ACTION_SPACE, MOTOR_ACTIONS
from .linear import argmax_action

ABLATION_LABELS = (
    "motor-driven",
    "bias-driven",
    "bias-driven (incidental)",
    "undefined",
)


def ablated_logits(readout: Any, features: np.ndarray) -> np.ndarray:
    """Recompute logits with the motor-feature vector set to exactly zero."""
    values = np.asarray(features, dtype=np.float32).ravel()
    if values.size != int(getattr(readout, "n_features", -1)):
        raise ValueError("feature vector width does not match the readout")
    zeros = np.zeros_like(values)
    return np.asarray(readout.logits(zeros), dtype=np.float64).ravel()


def classify_decision(
    readout: Any,
    features: np.ndarray,
    chosen_action: str,
    motor_activity: dict,
) -> dict:
    """Label one decision as motor-driven, bias-driven or undefined."""
    values = np.asarray(features, dtype=np.float32).ravel()
    chosen = str(chosen_action).strip().upper()
    if chosen not in ACTION_SPACE:
        raise ValueError(f"chosen action must be one of {ACTION_SPACE}")
    unablated = np.asarray(readout.logits(values), dtype=np.float64).ravel()
    ablated = ablated_logits(readout, values)
    unablated_action = argmax_action(unablated)
    ablated_action = argmax_action(ablated)
    changed = ablated_action != unablated_action
    if chosen in MOTOR_ACTIONS:
        population_spikes = int(motor_activity[chosen]["spikes"])
    else:
        population_spikes = 0
    any_motor_spike = bool(motor_activity.get("any_motor_spike", False))

    if changed and population_spikes >= 1:
        label = "motor-driven"
        reason = "ablation changed the argmax and the chosen population spiked"
    elif not changed and chosen != "NO_ACTION":
        label = "bias-driven"
        reason = "ablation left the argmax unchanged for a non-NO_ACTION choice"
    elif chosen == "NO_ACTION" and any_motor_spike:
        label = "bias-driven (incidental)"
        reason = "NO_ACTION was chosen although a motor population spiked"
    elif changed:
        # Uncovered cell in the §3.6.3 table: the ablation changed the argmax
        # but the chosen population had no spike. It cannot be motor-driven,
        # and it is not the NO_ACTION case the table calls undefined. The
        # label stays in the declared four-way set; the reason makes the gap
        # auditable and the episode row records it without changing E4's
        # denominator (non-NO_ACTION decisions).
        label = "undefined"
        reason = (
            "ablation changed the argmax but the chosen population had no "
            "spike; not defined by the §3.6.3 table"
        )
    else:
        label = "undefined"
        reason = "NO_ACTION was chosen and no motor population spiked"

    return {
        "ablation_rule": "motor-feature vector set to exactly 0.0",
        "unablated_argmax": unablated_action,
        "ablated_argmax": ablated_action,
        "chosen_action": chosen,
        "ablation_changed_argmax": bool(changed),
        "chosen_population_spikes": population_spikes,
        "any_motor_spike": any_motor_spike,
        "label": label,
        "label_reason": reason,
    }


def summarise_labels(decisions: list[dict]) -> dict:
    """Counts and fractions of the four labels for one episode."""
    total = len(decisions)
    counts = {name: 0 for name in ABLATION_LABELS}
    for decision in decisions:
        name = decision["label"]
        if name not in counts:
            raise ValueError(f"unknown ablation label {name!r}")
        counts[name] += 1
    non_no_action = sum(
        1 for decision in decisions if decision["chosen_action"] != "NO_ACTION"
    )
    return {
        "n_decisions": total,
        "counts": counts,
        "fractions": {
            name: round(value / total, 6) if total else 0.0
            for name, value in counts.items()
        },
        "ablation_change_rate": (
            round(
                sum(
                    1
                    for decision in decisions
                    if decision["ablation_changed_argmax"]
                )
                / total,
                6,
            )
            if total
            else 0.0
        ),
        "motor_driven_fraction_of_non_no_action": (
            round(counts["motor-driven"] / non_no_action, 6)
            if non_no_action
            else None
        ),
        "motor_driven_denominator": int(non_no_action),
    }
