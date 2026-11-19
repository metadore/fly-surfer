"""Phase 8 random-graph controls (conditions C, D and C′).

The null graph is a signed, degree-preserving directed randomization of the
BANC t5 edge list built by **target exchange**: each edge keeps its source and
its weight, and a swap exchanges the targets of two edges whose sources and
targets are all distinct. This preserves out-degree, in-degree and every
source's outgoing weight profile by construction (Phase 8 §3.3, U18).

``certification`` turns the R1–R18 report into a loadable certificate and
refuses to hand a graph to condition C unless every mandatory gate passed on
that exact file.
"""

from __future__ import annotations

from .certification import (
    CertificationError,
    OutputNamespace,
    certificate_refusal_reason,
    describe_certification,
    load_certificate,
    load_certified_graph,
    load_structure,
    structure_record,
    verify_structure_record,
)
from .target_exchange import (
    CANDIDATE_BLOCK,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PLATEAU_INTERVAL,
    MemoryTrace,
    RandomizationResult,
    describe_randomization,
    graph_digest,
    rewire_target_exchange,
    validate_randomization,
)

__all__ = [
    "CANDIDATE_BLOCK",
    "CertificationError",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_PLATEAU_INTERVAL",
    "MemoryTrace",
    "OutputNamespace",
    "RandomizationResult",
    "certificate_refusal_reason",
    "describe_certification",
    "describe_randomization",
    "graph_digest",
    "load_certificate",
    "load_certified_graph",
    "load_structure",
    "rewire_target_exchange",
    "structure_record",
    "validate_randomization",
    "verify_structure_record",
]
