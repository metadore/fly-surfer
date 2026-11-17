"""Phase 8 random-graph controls (conditions C, D and C′).

The null graph is a signed, degree-preserving directed randomization of the
BANC t5 edge list built by **target exchange**: each edge keeps its source and
its weight, and a swap exchanges the targets of two edges whose sources and
targets are all distinct. This preserves out-degree, in-degree and every
source's outgoing weight profile by construction (Phase 8 §3.3, U18).
"""

from __future__ import annotations

from .target_exchange import (
    RandomizationResult,
    graph_digest,
    rewire_target_exchange,
    validate_randomization,
)

__all__ = [
    "RandomizationResult",
    "graph_digest",
    "rewire_target_exchange",
    "validate_randomization",
]
