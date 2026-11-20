"""Approval and design gates for the training stage.

Three independent gates guard artifact generation:

1. **Design gate.** ``configs/phase_8/campaign.yaml`` leaves
   ``design.n_seeds_selected`` null until the 10.8 pilot decision (U7) is
   recorded. Without it there is no campaign design, so no per-seed training
   artifact can be generated and no campaign can be prepared. The value is
   never defaulted or guessed here.
2. **Training-operation gate.** B3-B6 are undeclared: no campaign-to-training
   seed pairing, no training-episode environment-seed schedule, no checkpoint
   cadence/retention/format, and no checkpointed sampler RNG or optimizer
   moments.
3. **Authorization gate.** Recorded owner decision D1 (2026-11-20) approves
   REV4 §12 and U1-U18 as written, so the protocol-approval check passes. That
   approval authorises no parameter change and bypasses no other gate: training
   is still refused because the design (U7), B3-B6 and the G3 deviation (B7)
   remain open. :func:`assert_training_authorized` therefore still raises.
   Synthetic fixtures written under ``origin = "synthetic_fixture"`` are not
   training runs and do not pass through this gate; the campaign loader refuses
   them by origin.

These functions add no scientific mechanism. They are the same refusals the
campaign stage already enforces (``experiments.phase_8.campaign.protocol``),
applied to training and artifact generation.
"""

from __future__ import annotations

from typing import Any

from ..campaign.protocol import approval_status, randomization_deviation
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


def training_authorization_status() -> dict:
    """The recorded approval plus every gate that still refuses training."""
    approval = approval_status()
    deviation = randomization_deviation()
    blockers = list(TRAINING_DECLARATION_BLOCKERS)
    if not approval["approved"]:
        blockers.insert(0, "B1: " + approval["reason"])
    if deviation.get("status") != "compliant":
        blockers.append(
            "B7: the G3 certified graphs carry a recorded §9.3 memory-gate "
            f"deviation (status {deviation.get('status')!r})"
        )
    return {
        "training_authorized": False,
        "blockers": blockers,
        "protocol_id": approval["protocol_id"],
        "approved": approval["approved"],
        "decision_status": approval["decision_status"],
        "decision_items": list(approval["decision_items"]),
        "protocol_sha256": approval["protocol_sha256"],
        "document_authorises_execution": approval["document_authorises_execution"],
        "approval_record": approval["approval_record"],
        "reason": (
            "training remains unauthorised: the design decision (U7) is "
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
    "UNRESOLVED_REASON",
    "assert_design_resolved",
    "assert_training_authorized",
    "design_status",
    "training_authorization_status",
]
