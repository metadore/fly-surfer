"""Approval and design gates for the training stage.

Three independent gates guard artifact generation:

1. **Design gate.** ``configs/phase_8/campaign.yaml`` leaves
   ``design.n_seeds_selected`` null until the 10.8 pilot decision (U7) is
   recorded. Without it there is no campaign design, so no per-seed training
   artifact can be generated and no campaign can be prepared. The value is
   never defaulted or guessed here.
2. **Training-operation gate.** Owner decision D4 (2026-11-21) declares B3-B6:
   the campaign-to-training seed pairing, the training-episode environment-seed
   schedule, the checkpoint policy and the exact-resumption contract. The
   declaration removes those four items from the blocker list only while D4 is
   present, valid and bound to the frozen REV4, the Pilot 2-C amendment and the
   D3 record. D4 authorises **no execution**, so this gate reports the
   contracts as declared and still refuses training.
3. **Authorization gate.** Recorded owner decision D1 (2026-11-20) approves
   REV4 §12 and U1-U18 as written, so the protocol-approval check passes. That
   approval authorises no parameter change and bypasses no other gate: training
   is still refused because the design (U7, B2) and the G3 deviation (B7)
   remain open, and D4 itself authorises no training run.
   :func:`assert_training_authorized` therefore still raises. Synthetic
   fixtures written under ``origin = "synthetic_fixture"`` are not training runs
   and do not pass through this gate; the campaign loader refuses them by
   origin.

These functions add no scientific mechanism. They are the same refusals the
campaign stage already enforces (``experiments.phase_8.campaign.protocol``),
applied to training and artifact generation.
"""

from __future__ import annotations

from typing import Any

from ..campaign.protocol import approval_status, randomization_deviation
from .d4 import d4_applicability
from .errors import DesignUnresolvedError, TrainingNotAuthorized

UNRESOLVED_REASON = (
    "design.n_seeds_selected is null: the 10.8 pilot decision (U7) is not "
    "recorded, so no campaign design exists, no training artifact may be "
    "generated and no campaign may be prepared from these artifacts"
)


def design_status(campaign: Any) -> dict:
    """Report the unresolved design field without inventing a value."""
    selected = campaign.n_seeds_selected
    resolved = selected is not None
    seeds = list(campaign.campaign_seeds) if resolved else []
    return {
        "field": "design.n_seeds_selected",
        "path": getattr(campaign, "path", None),
        "value": selected,
        "resolved": resolved,
        "active_seeds": seeds[: int(selected)] if resolved else [],
        "reason": (
            "the 10.8 pilot decision is recorded"
            if resolved
            else UNRESOLVED_REASON
        ),
    }


def assert_design_resolved(campaign: Any) -> int:
    """Return ``n_seeds_selected`` or raise :class:`DesignUnresolvedError`."""
    status = design_status(campaign)
    if not status["resolved"]:
        raise DesignUnresolvedError(UNRESOLVED_REASON)
    return int(status["value"])


TRAINING_DECLARATION_BLOCKERS = (
    "B2: design.n_seeds_selected is null until the 10.8 pilot decision (U7) is recorded",
    "B3: no campaign-to-training seed pairing is declared",
    "B4: no training-episode environment-seed schedule is declared",
    "B5: no checkpoint cadence, retention or format is declared",
    "B6: sampler RNG and optimizer moments are not checkpointed, so resume is "
    "parameter-continuous and not bit-identical",
)

TRAINING_OPERATION_DECISIONS = ("B3", "B4", "B5", "B6")


def training_declarations() -> dict:
    """The B3-B6 contracts as declared by D4, or the reasons they are not.

    ``declared`` is populated only when the D4 record is present, valid and
    bound to the frozen documents it cites. Nothing here is execution
    authority: ``training_execution_authorized`` is always false.
    """
    report = d4_applicability()
    applicable = bool(report["applicable"])
    undischarged = (
        {}
        if applicable
        else {
            decision: blocker
            for decision, blocker in zip(
                TRAINING_OPERATION_DECISIONS, TRAINING_DECLARATION_BLOCKERS[1:]
            )
        }
    )
    return {
        "owner_decision": "D4",
        "approval_date": report["approval_date"],
        "record": report["path"],
        "applicable": applicable,
        "declared": dict(report["decisions"]) if applicable else {},
        "undischarged": undischarged,
        "failures": list(report["failures"]),
        "training_execution_authorized": False,
    }


def training_authorization_status() -> dict:
    """The recorded approval plus every gate that still refuses training."""
    approval = approval_status()
    deviation = randomization_deviation()
    declarations = training_declarations()
    blockers: list[str] = []
    if not approval["approved"]:
        blockers.append("B1: " + approval["reason"])
    blockers.append(TRAINING_DECLARATION_BLOCKERS[0])
    if not declarations["applicable"]:
        blockers.extend(TRAINING_DECLARATION_BLOCKERS[1:])
    if deviation.get("status") != "compliant":
        blockers.append(
            "B7: the G3 certified graphs carry a recorded §9.3 memory-gate "
            f"deviation (status {deviation.get('status')!r})"
        )
    return {
        "training_authorized": False,
        "blockers": blockers,
        "declared_decisions": declarations["declared"],
        "training_declarations": declarations,
        "protocol_id": approval["protocol_id"],
        "approved": approval["approved"],
        "decision_status": approval["decision_status"],
        "decision_items": list(approval["decision_items"]),
        "protocol_sha256": approval["protocol_sha256"],
        "document_authorises_execution": approval["document_authorises_execution"],
        "approval_record": approval["approval_record"],
        "reason": (
            "training remains unauthorised: the design decision (U7, B2) is "
            "unrecorded, B7 (the G3 §9.3 deviation) is open, and owner decision "
            "D4 declares B3-B6 without authorising any training run"
            if declarations["applicable"]
            else "training remains unauthorised: the design decision (U7, B2) is "
            "unrecorded, the training-operation inputs B3-B6 are undeclared, "
            "and B7 (the G3 §9.3 deviation) is open. The recorded D1 approval "
            "of §12/U1-U18 authorises no parameter change and does not by "
            "itself authorise a training run"
        ),
    }


def assert_training_authorized(*_args: Any, **_kwargs: Any) -> None:
    """Always refuse: no training run is authorised on the present state."""
    status = training_authorization_status()
    raise TrainingNotAuthorized(
        f"{status['reason']} (protocol sha256 {status['protocol_sha256']})"
    )


__all__ = [
    "TRAINING_DECLARATION_BLOCKERS",
    "TRAINING_OPERATION_DECISIONS",
    "UNRESOLVED_REASON",
    "assert_design_resolved",
    "assert_training_authorized",
    "design_status",
    "training_authorization_status",
    "training_declarations",
]
