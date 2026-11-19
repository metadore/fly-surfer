"""Approval and design gates for the training stage.

Two independent gates guard artifact generation:

1. **Design gate.** ``configs/phase_8/campaign.yaml`` leaves
   ``design.n_seeds_selected`` null until the 10.8 pilot decision (U7) is
   recorded. Without it there is no campaign design, so no per-seed training
   artifact can be generated and no campaign can be prepared. The value is
   never defaulted or guessed here.
2. **Authorization gate.** REV4 §12 is unapproved and U1–U18 remain
   ``PROPOSED — not approved``. The document's final paragraph states that it
   authorises no execution, so :func:`assert_training_authorized` always
   raises. Synthetic fixtures written under ``origin = "synthetic_fixture"``
   are not training runs and do not pass through this gate; the campaign
   loader refuses them by origin.

These functions add no scientific mechanism. They are the same refusals the
campaign stage already enforces (``experiments.phase_8.campaign.protocol``),
applied to training and artifact generation.
"""

from __future__ import annotations

from typing import Any

from ..campaign.protocol import approval_status
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


def training_authorization_status() -> dict:
    """The approval facts, unchanged from the campaign gate."""
    approval = approval_status()
    return {
        "training_authorized": False,
        "protocol_id": approval["protocol_id"],
        "approved": approval["approved"],
        "decision_status": approval["decision_status"],
        "decision_items": list(approval["decision_items"]),
        "protocol_sha256": approval["protocol_sha256"],
        "document_authorises_execution": approval["document_authorises_execution"],
        "reason": (
            "training is an execution step: REV4 §12 is unapproved, U1-U18 "
            "remain PROPOSED, and the document authorises no execution"
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
