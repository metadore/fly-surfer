"""Phase 8 G5 campaign assembly: factory, dispatcher, graph source, status.

SCIENTIFIC STATUS
    This package assembles existing components into the campaign runner. It
    adds no mechanism and no scientific claim. It does not authorise a
    campaign: the protocol is not approved (REV4 §10.0, §12), and the only
    entry point that could start one refuses until that changes.

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
    protocol_identity,
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
    "assert_target_exchange_alignment",
    "protocol_identity",
    "run_status",
    "validate_campaign",
]
