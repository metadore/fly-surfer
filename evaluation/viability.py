"""Read-only U1 viability report (REV3 §12 U1, implementation step 10.13).

The U1 decision is the pre-campaign stop rule: if the pilot shows zero
non-``NO_ACTION`` executions in the neural conditions, Phase 8 must stop and
request a scope decision instead of claiming an effect. This module implements
the U1 table **as proposed**. U1 is not approved (REV3 §12), so nothing here
authorises a campaign, a tune, or a reclassification of a floored arm.

The report has three moving parts:

* :func:`arm_gate` — one arm's distance from the **measured** substrate-free
  floor. The floor is never assumed; if the floor rows are absent the arm's
  status is ``indeterminate`` or ``not run``, never ``above floor``.
* :func:`evaluate_viability` — the five rows of the U1 table (the document
  calls them "three gate cases"; U1-B/U1-E are the two halves of the
  both-floored case). An incomplete input yields ``complete: False`` and a
  ``blocked_by`` list; blocked work is never reported as complete.
* :func:`phase7_summary` — the frozen Phase 7 baseline, read from its artifact
  and explicitly labelled as not a campaign arm.

Everything is read-only: no store, manifest, configuration or artifact is
written, and no game or simulator is started.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from experiments.phase_8.analysis import arm_summary, pair_series
from experiments.phase_8.schema import validate_rows
from experiments.phase_8.seeds import FLOOR_ID
from experiments.phase_8.store import read_store

REPORT_VERSION = 1
PROTOCOL_ID = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV3"
PROTOCOL_STATUS = "PROPOSED — not approved (REV3 §12 U1)"

#: The arms the U1 table needs. ``E`` is the matched conventional learner
#: (condition id ``E``); its only role here is to separate U1-B from U1-E.
GATE_ARMS = ("A", "F", "E")


class ViabilityError(ValueError):
    """The supplied rows or artifact cannot support a U1 report."""


# ---------------------------------------------------------------------------
# the U1 table
# ---------------------------------------------------------------------------

U1_CASES: tuple[dict, ...] = (
    {
        "id": "U1-A",
        "a": "above floor",
        "f": "above floor",
        "e_matched": "—",
        "label": "gate passed",
        "action": "proceed; the gate is passed",
    },
    {
        "id": "U1-B",
        "a": "floored",
        "f": "floored",
        "e_matched": "any",
        "label": "platform floor",
        "action": (
            "run the predeclared floor decomposition and stop for a scope "
            "decision; do not claim an effect for any neural condition"
        ),
    },
    {
        "id": "U1-C",
        "a": "floored",
        "f": "above floor",
        "e_matched": "—",
        "label": "readout rescues the platform",
        "action": (
            "proceed, but report A's floor and F's success as a "
            "readout-specific finding, not as evidence about the substrate"
        ),
    },
    {
        "id": "U1-D",
        "a": "above floor",
        "f": "floored",
        "e_matched": "—",
        "label": "readout harms",
        "action": (
            "proceed with the readout contrast, report F's failure, and do "
            "not treat Fβ as the floor"
        ),
    },
    {
        "id": "U1-E",
        "a": "floored",
        "f": "floored",
        "e_matched": "above floor",
        "label": "environment solvable but not from this interface",
        "action": (
            "report A–D as an interface limitation; the environment is "
            "solvable but not from this interface"
        ),
    },
)

U1_B_OPTIONS: tuple[str, ...] = (
    "run the full campaign anyway and report a floor result",
    "stop, report the floor plus a pathology decomposition (no motor spikes / "
    "no sustained activity / decoder gate never met), and request a scope decision",
    "authorise a separate, pre-registered follow-up that changes drive or decoder "
    "(Phase 9, never inside Phase 8)",
    "if A and F floor but E-matched does not, run only E and report the "
    "environment as solvable-but-not-from-this-interface",
)
U1_B_RECOMMENDATION = "option 2, then decide with the user; option 4 is a refinement of option 2 once E exists"


def case_table() -> list[dict]:
    """The U1 table as declared, plus U1-B's options, ready for a report."""
    rows = [dict(entry) for entry in U1_CASES]
    for row in rows:
        if row["id"] == "U1-B":
            row["options"] = list(U1_B_OPTIONS)
            row["recommendation"] = U1_B_RECOMMENDATION
    return rows


# ---------------------------------------------------------------------------
# one arm against the measured floor
# ---------------------------------------------------------------------------


def _mean_fraction(values: Sequence[Fraction]) -> Fraction:
    return sum(values, Fraction(0)) / len(values)


def arm_gate(
    rows: Sequence[Mapping[str, Any]],
    arm: str,
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    floor_arm: str = FLOOR_ID,
) -> dict:
    """Describe one arm relative to the substrate-free no-action floor.

    ``status`` is one of:

    ``not run``
        no completed episode for this arm in the planned cells.
    ``floored``
        zero non-``NO_ACTION`` decisions. This is the literal U1 stop signal
        and does not depend on the floor being measured.
    ``above floor``
        at least one non-``NO_ACTION`` decision **and** a positive paired mean
        capped-score difference from the measured floor.
    ``acts but not above floor``
        actions exist, but the paired mean difference from the floor is
        ``<= 0``. The arm is treated as floored for the gate and the
        discrepancy is reported.
    ``indeterminate``
        actions exist but the floor is absent (or has no complete pair), so
        "above floor" cannot be asserted.

    The function never writes and never reclassifies an arm from an assumption.
    """
    if isinstance(seeds, (str, bytes)) or not seeds:
        raise ViabilityError("seeds must be a non-empty sequence of integers")
    seed_tuple = tuple(int(seed) for seed in seeds)
    if episodes_per_seed < 1:
        raise ViabilityError("episodes_per_seed must be at least 1")

    summary = arm_summary(
        rows, arm, seeds=seed_tuple, episodes_per_seed=episodes_per_seed
    )
    floor_summary = arm_summary(
        rows, floor_arm, seeds=seed_tuple, episodes_per_seed=episodes_per_seed
    )
    floor_measured = floor_summary["episodes_ok"] > 0
    expected = len(seed_tuple) * int(episodes_per_seed)
    floor_complete = floor_summary["episodes_ok"] == expected

    pairs: list = []
    if floor_measured and arm != floor_arm:
        pairs, _excluded, _left, _right = pair_series(
            rows,
            arm,
            floor_arm,
            seeds=seed_tuple,
            episodes_per_seed=episodes_per_seed,
        )
    differences = [pair.difference for pair in pairs]
    mean_difference = _mean_fraction(differences) if differences else None

    if summary["episodes_ok"] == 0:
        status = "not run"
    elif summary["non_no_action_decisions"] == 0:
        status = "floored"
    elif mean_difference is None:
        status = "indeterminate"
    elif mean_difference > 0:
        status = "above floor"
    else:
        status = "acts but not above floor"

    notes = []
    if status == "floored" and summary["episodes_ok"] < expected:
        notes.append(
            f"only {summary['episodes_ok']} of {expected} planned episodes are "
            "complete; the floor signal is based on those rows"
        )
    if status == "floored" and floor_measured:
        notes.append(
            "zero non-NO_ACTION decisions; the measured floor is reported for "
            "context, not used to upgrade the arm"
        )
    if status == "acts but not above floor":
        notes.append(
            "the arm acts but its paired mean capped score does not exceed the "
            "floor; it is treated as floored for the U1 gate (REV3 §7.8)"
        )
    if status == "indeterminate":
        notes.append(
            "the floor is not measured on the paired seeds, so 'above floor' "
            "cannot be asserted; the floor is never assumed"
        )
    if status == "not run":
        notes.append("no completed episode for this arm in the planned cells")

    return {
        "arm": arm,
        "episodes_expected": expected,
        "episodes_ok": summary["episodes_ok"],
        "episodes_error": summary["episodes_error"],
        "episodes_missing": summary["episodes_missing"],
        "total_steps": summary["total_steps"],
        "non_no_action_decisions": summary["non_no_action_decisions"],
        "mean_capped_score": summary["mean_capped_score"],
        "mean_no_action_fraction": summary["no_action_fraction"],
        "total_motor_spikes": summary["total_motor_spikes"],
        "seeds_with_motor_spikes": summary["seeds_with_motor_spikes"],
        "floor_measured": floor_measured,
        "floor_complete": floor_complete,
        "floor_mean_capped_score": floor_summary["mean_capped_score"],
        "seeds_paired_with_floor": len(pairs),
        "mean_difference_from_floor": (
            float(mean_difference) if mean_difference is not None else None
        ),
        "mean_difference_from_floor_exact": (
            f"{mean_difference.numerator}/{mean_difference.denominator}"
            if mean_difference is not None
            else None
        ),
        "status": status,
        "above_floor": status == "above floor",
        "floored": status in ("floored", "acts but not above floor"),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# the U1 decision
# ---------------------------------------------------------------------------


def _floor_status(rows: Sequence[Mapping[str, Any]], *, seeds, episodes_per_seed) -> dict:
    summary = arm_summary(
        rows, FLOOR_ID, seeds=seeds, episodes_per_seed=episodes_per_seed
    )
    expected = len(tuple(seeds)) * int(episodes_per_seed)
    return {
        "measured": summary["episodes_ok"] > 0,
        "complete": summary["episodes_ok"] == expected,
        "episodes_ok": summary["episodes_ok"],
        "episodes_expected": expected,
        "mean_capped_score": summary["mean_capped_score"],
        "note": (
            "the substrate-free floor is a game-side replay of the paired "
            "environment seeds with a constant NO_ACTION policy; it is never "
            "assumed and never treated as a neural arm"
        ),
    }


def evaluate_viability(
    rows: Sequence[Mapping[str, Any]],
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    floor_arm: str = FLOOR_ID,
) -> dict:
    """Apply the U1 table to the supplied rows and report, never authorize.

    ``complete`` is ``True`` only when every required arm is classifiable and
    the floor is measured. A missing ``F`` row, an unmeasured floor, or an arm
    that acts without a floor keeps the report blocked and says which input is
    missing. ``provisional`` is ``True`` for U1-B when E-matched is absent,
    because U1-E cannot then be excluded.
    """
    checked = validate_rows(rows)
    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple:
        raise ViabilityError("seeds must be a non-empty sequence")

    gates = {
        arm: arm_gate(
            checked,
            arm,
            seeds=seed_tuple,
            episodes_per_seed=episodes_per_seed,
            floor_arm=floor_arm,
        )
        for arm in GATE_ARMS
    }
    floor = _floor_status(
        checked, seeds=seed_tuple, episodes_per_seed=episodes_per_seed
    )

    a, f, e = gates["A"], gates["F"], gates["E"]
    blocked_by: list[str] = []
    provisional = False
    case_id: str | None = None

    if a["status"] in ("not run", "indeterminate"):
        blocked_by.append(f"A is {a['status']}")
    if f["status"] in ("not run", "indeterminate"):
        blocked_by.append(f"F is {f['status']}")
    if not floor["measured"] and (a["status"] != "not run" or f["status"] != "not run"):
        blocked_by.append("the substrate-free floor is not measured on the paired seeds")

    if a["above_floor"] and f["above_floor"]:
        case_id = "U1-A"
    elif a["floored"] and f["above_floor"]:
        case_id = "U1-C"
    elif a["above_floor"] and f["floored"]:
        case_id = "U1-D"
    elif a["floored"] and f["floored"]:
        if e["above_floor"]:
            case_id = "U1-E"
        elif e["floored"]:
            case_id = "U1-B"
        else:
            case_id = "U1-B"
            provisional = True
            blocked_by.append(
                f"E-matched is {e['status']}; U1-E cannot be excluded until E is measured"
            )

    case = next((entry for entry in U1_CASES if entry["id"] == case_id), None)
    complete = bool(case_id) and not blocked_by and not provisional

    notes = []
    if not floor["measured"]:
        notes.append(
            "without a measured floor no arm can be declared above floor; the "
            "report is descriptive only"
        )
    if not floor["complete"] and floor["measured"]:
        notes.append(
            f"the floor covers {floor['episodes_ok']} of "
            f"{floor['episodes_expected']} planned cells; paired differences use "
            "complete pairs only"
        )
    if case_id == "U1-B":
        notes.append(
            "U1-B recommends stopping and requesting a scope decision; no drive "
            "or decoder change is authorised inside Phase 8"
        )
    if case_id == "U1-A":
        notes.append(
            "U1-A passes only the viability gate; it is not evidence for any "
            "confirmatory contrast"
        )
    notes.append(
        "the U1 rule is proposed, not approved; this report records what the "
        "supplied rows imply under REV3 §12 and authorises nothing"
    )

    return {
        "report_version": REPORT_VERSION,
        "protocol": PROTOCOL_ID,
        "protocol_status": PROTOCOL_STATUS,
        "read_only": True,
        "scope": {
            "seeds": list(seed_tuple),
            "episodes_per_seed": int(episodes_per_seed),
            "rows": len(checked),
            "note": (
                "U1 is decided at step 10.8 on the 3-seed pilot; this report "
                "describes exactly the rows supplied and nothing else"
            ),
        },
        "floor": floor,
        "gates": gates,
        "case": case_id,
        "case_label": case["label"] if case else None,
        "action": case["action"] if case else None,
        "provisional": provisional,
        "complete": complete,
        "blocked": bool(blocked_by) or provisional,
        "blocked_by": blocked_by,
        "evidence": {
            "A": a["status"],
            "F": f["status"],
            "E_matched": e["status"],
        },
        "notes": notes,
    }


def evaluate_store(
    store_path: str | Path,
    *,
    seeds: Sequence[int],
    episodes_per_seed: int,
    floor_arm: str = FLOOR_ID,
) -> dict:
    """Read a JSONL store and apply :func:`evaluate_viability` to it."""
    rows = read_store(store_path)
    report = evaluate_viability(
        rows,
        seeds=seeds,
        episodes_per_seed=episodes_per_seed,
        floor_arm=floor_arm,
    )
    report["store"] = str(Path(store_path))
    return report


# ---------------------------------------------------------------------------
# the frozen Phase 7 baseline
# ---------------------------------------------------------------------------


def phase7_summary(payload: Mapping[str, Any]) -> dict:
    """Summarise the frozen Phase 7 closed-loop artifact.

    This is historical evidence, **not** a campaign arm: it has no floor, no
    paired seeds and no control. It is reported only so the implementation
    status can cite the same frozen numbers the protocol cites.
    """
    run = payload.get("run")
    if not isinstance(run, Mapping) or not isinstance(run.get("summary"), Mapping):
        raise ViabilityError("Phase 7 artifact has no run.summary mapping")
    summary = run["summary"]
    required = ("seed", "updates", "action_counts", "motor_spikes")
    missing = [name for name in required if name not in summary]
    if missing:
        raise ViabilityError(f"Phase 7 run.summary is missing {missing}")

    action_counts = summary["action_counts"]
    if not isinstance(action_counts, Mapping):
        raise ViabilityError("Phase 7 action_counts must be a mapping")
    updates = int(summary["updates"])
    no_action = int(action_counts.get("NO_ACTION", 0))

    def _fingerprint(key: str) -> str | None:
        block = summary.get(key)
        if isinstance(block, Mapping):
            return block.get("sha256")
        return None

    return {
        "source": "experiments/results/phase_7/neural_closed_loop.json",
        "phase": payload.get("phase", "phase_7"),
        "is_campaign_arm": False,
        "arm": None,
        "seed": int(summary["seed"]),
        "updates": updates,
        "observed_updates": updates,
        "action_counts": {str(k): int(v) for k, v in action_counts.items()},
        "non_no_action_decisions": updates - no_action,
        "motor_spikes": int(summary["motor_spikes"]),
        "total_spikes": summary.get("total_spikes"),
        "non_stimulated_spikes": summary.get("non_stimulated_spikes"),
        "terminated": summary.get("terminated"),
        "truncated": summary.get("truncated"),
        "termination_reason": summary.get("termination_reason"),
        "weights_before_sha256": _fingerprint("weights_before"),
        "weights_after_sha256": _fingerprint("weights_after"),
        "floored_by_actions": updates - no_action == 0,
        "note": (
            "frozen Phase 7 fixed-weight baseline: 2,852 spikes, all sensory, "
            "0 motor spikes, 213/213 NO_ACTION, weights bit-identical before "
            "and after. It is not a Phase 8 arm and has no measured floor"
        ),
    }


def phase7_summary_from_path(path: str | Path) -> dict:
    """Load a Phase 7 JSON artifact and return :func:`phase7_summary`."""
    import json

    source = Path(path)
    if not source.is_file():
        raise ViabilityError(f"Phase 7 artifact not found: {source}")
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ViabilityError(f"{source} must contain a JSON object")
    return phase7_summary(payload)


__all__ = [
    "GATE_ARMS",
    "PROTOCOL_ID",
    "PROTOCOL_STATUS",
    "REPORT_VERSION",
    "U1_B_OPTIONS",
    "U1_B_RECOMMENDATION",
    "U1_CASES",
    "ViabilityError",
    "arm_gate",
    "case_table",
    "evaluate_store",
    "evaluate_viability",
    "phase7_summary",
    "phase7_summary_from_path",
]
