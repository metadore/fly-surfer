"""Phase 8 G5 campaign assembly: factory, dispatcher, graph source, status.

SCIENTIFIC STATUS
    This package assembles existing components into the campaign runner. It
    adds no mechanism and no scientific claim. It does not authorise a
    campaign: recorded owner decision D1 approves REV4 §12 and U1-U18 as
    written, and D2 makes the G3 deviation not applicable to the exact Pilot 1
    grid only. Pilot 2, the campaign, training and the randomized arms remain
    refused by the unchanged campaign-wide gate.

Nothing in this package runs an episode by itself. The factory builds
components, the dispatcher routes one plan entry to the arm implementation
declared in ``experiments/phase_8/conditions`` or ``controls``, and the status
module reads a run directory without modifying it.
"""

from __future__ import annotations

from .dispatcher import CampaignDispatcher, EpisodeFailure
from .factory import CampaignFactory, FactoryError, TrainingArtifacts
from .graphs import (
    CertifiedGraph,
    CertifiedGraphSource,
    GraphSelectionError,
    assert_target_exchange_alignment,
)
from .protocol import (
    CampaignNotAuthorized,
    CampaignProtocolError,
    approval_status,
    assert_campaign_authorized,
    assert_stage_authorized,
    g3_applicability,
    protocol_identity,
    stage_authorization,
    validate_campaign,
)
from .status import run_status

__all__ = [
    "CampaignDispatcher",
    "CampaignFactory",
    "CampaignNotAuthorized",
    "CampaignProtocolError",
    "CertifiedGraph",
    "CertifiedGraphSource",
    "EpisodeFailure",
    "FactoryError",
    "GraphSelectionError",
    "TrainingArtifacts",
    "approval_status",
    "assert_campaign_authorized",
    "assert_stage_authorized",
    "assert_target_exchange_alignment",
    "g3_applicability",
    "protocol_identity",
    "run_status",
    "stage_authorization",
    "validate_campaign",
]
