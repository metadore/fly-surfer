"""Certified random-graph selection for conditions C, D and C'.

SCIENTIFIC STATUS
    A certified graph is a degree- and sign-preserving target-exchange control
    built from the biological graph. It is not a null model fitted to data and
    not a physiological preparation. The certificate says only that this file
    passed the declared REV4 §3.3.1 gates for this original graph under this
    protocol; it is not evidence of biological validity.

There is exactly one way to obtain a structure for an arm that needs one:
:meth:`CertifiedGraphSource.load`, which delegates to
``experiments.phase_8_random.certification.load_structure``. That call verifies
the namespace marker, the certificate status, the protocol hash, every
mandatory gate, R14, R17 byte identity, the graph file hash, the graph digest,
the original-vs-output difference and the structure-seed derivation. Any
failure is a hard error; there is no fallback to the biological graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from experiments.phase_8.seeds import MASTER_SEED
from experiments.phase_8_random import certification as cert
from experiments.phase_8_random.campaign_summary import OUTPUT_ROOT, REQUIRED_SEEDS

CONSTRUCTION = "target_exchange"


class GraphSelectionError(RuntimeError):
    """A random graph may not be used for a Phase 8 campaign episode."""


@dataclass(frozen=True)
class CertifiedGraph:
    """One loaded certified graph together with the record C, D and C' need."""

    seed: int
    graph: Any
    record: dict
    certificate_path: Path
    certificate_sha256: str
    graph_path: Path
    graph_sha256: str
    graph_digest: str

    def describe(self) -> dict:
        return {
            "seed": int(self.seed),
            "structure_seed": int(self.record["seed"]),
            "campaign_seed": int(self.record["campaign_seed"]),
            "master_seed": int(self.record["master_seed"]),
            "construction": self.record["construction"],
            "u18_status": self.record["u18_status"],
            "certificate_path": self.certificate_path.as_posix(),
            "certificate_sha256": self.certificate_sha256,
            "graph_path": self.graph_path.as_posix(),
            "graph_sha256": self.graph_sha256,
            "graph_digest": self.graph_digest,
            "n_nodes": int(self.graph.n_nodes),
            "n_edges": int(self.graph.n_edges),
            "randomization_passed": bool(
                self.record["randomization_quality"]["passed"]
            ),
        }


def _check_seed(seed: Any, required: Iterable[int]) -> int:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise GraphSelectionError("the structure seed must be an integer")
    value = int(seed)
    if value not in set(int(item) for item in required):
        raise GraphSelectionError(
            f"no certified graph exists for campaign seed {value}; the "
            "certified set is "
            f"{sorted(int(item) for item in required)}"
        )
    return value


class CertifiedGraphSource:
    """Read-only access to the per-seed certified graph namespaces."""

    def __init__(
        self,
        root: str | Path = OUTPUT_ROOT,
        *,
        required_seeds: Iterable[int] = REQUIRED_SEEDS,
    ) -> None:
        self.root = Path(root)
        self.required_seeds = tuple(int(item) for item in required_seeds)

    # -- locations -------------------------------------------------------
    def namespace(self, seed: int) -> Path:
        return self.root / f"seed_{_check_seed(seed, self.required_seeds)}"

    def certificate_path(self, seed: int) -> Path:
        return self.namespace(seed) / cert.CERTIFICATE_NAME

    def manifest_path(self, seed: int) -> Path:
        return self.namespace(seed) / cert.MANIFEST_NAME

    # -- inspection (no graph load) --------------------------------------
    def inspect(self, seed: int) -> dict:
        """Certificate-level facts for one seed; never loads the graph."""
        value = _check_seed(seed, self.required_seeds)
        path = self.certificate_path(value)
        entry: dict = {
            "seed": value,
            "namespace": self.namespace(value).as_posix(),
            "certificate_path": path.as_posix(),
            "present": path.is_file(),
            "marker_present": (path.parent / cert.MARKER_NAME).exists(),
            "status": "missing",
        }
        if not path.is_file():
            return entry
        if entry["marker_present"]:
            entry["status"] = "incomplete_namespace"
            return entry
        try:
            certificate = cert.load_certificate(path)
        except cert.CertificationError as error:
            entry["status"] = "unreadable"
            entry["reason"] = str(error)
            return entry
        reason = cert.certificate_refusal_reason(certificate)
        entry.update(
            {
                "certificate_sha256": cert.sha256_file(path),
                "protocol_sha256": certificate["protocol"]["sha256"],
                "structure_seed": certificate["seed"]["structure_seed"],
                "campaign_seed": certificate["seed"]["campaign_seed"],
                "master_seed": certificate["seed"]["master_seed"],
                "graph_digest": certificate["output_graph"]["graph_digest"],
                "graph_sha256": certificate["output_graph"]["sha256"],
                "construction": certificate["construction"]["method"],
                "status": "refused" if reason else "certified",
            }
        )
        if reason:
            entry["reason"] = reason
        return entry

    def inspect_all(self) -> list[dict]:
        return [self.inspect(seed) for seed in self.required_seeds]

    # -- loading ---------------------------------------------------------
    def load(self, seed: int) -> CertifiedGraph:
        """Load and verify one certified graph; any failure is fatal."""
        value = _check_seed(seed, self.required_seeds)
        path = self.certificate_path(value)
        try:
            graph, record = cert.load_structure(path)
        except cert.CertificationError as error:
            raise GraphSelectionError(
                f"certified graph refused for seed {value}: {error}"
            ) from error
        except FileNotFoundError as error:
            raise GraphSelectionError(
                f"certified graph is missing for seed {value}: {error}"
            ) from error

        if record.get("construction") != CONSTRUCTION:
            raise GraphSelectionError(
                f"seed {value} was built by {record.get('construction')!r}; "
                f"Phase 8 requires {CONSTRUCTION!r}"
            )
        if int(record["master_seed"]) != int(MASTER_SEED):
            raise GraphSelectionError(
                f"seed {value} was derived from master seed "
                f"{record['master_seed']}, not {MASTER_SEED}"
            )
        if int(record["seed"]) != value or int(record["campaign_seed"]) != value:
            raise GraphSelectionError(
                f"certificate seed fields do not describe campaign seed {value}: "
                f"structure {record['seed']}, campaign {record['campaign_seed']}"
            )
        quality = record.get("randomization_quality")
        if not isinstance(quality, Mapping) or quality.get("passed") is not True:
            raise GraphSelectionError(
                f"seed {value} failed the randomization gates; the structure "
                "may not enter a campaign"
            )
        if record.get("protocol_sha256") != cert.EXPECTED_PROTOCOL_SHA256:
            raise GraphSelectionError(
                f"seed {value} was certified against another protocol document"
            )

        graph_path = Path(record["graph_path"])
        if not graph_path.is_file():
            graph_path = self.namespace(value) / graph_path.name
        if not graph_path.is_file():
            raise GraphSelectionError(
                f"certified graph file for seed {value} is missing: {graph_path}"
            )
        return CertifiedGraph(
            seed=value,
            graph=graph,
            record=dict(record),
            certificate_path=path,
            certificate_sha256=cert.sha256_file(path),
            graph_path=graph_path,
            graph_sha256=str(record["graph_sha256"]),
            graph_digest=str(record["graph_digest"]),
        )

    def require(self, seed: int) -> CertifiedGraph:
        return self.load(seed)

    def describe(self) -> dict:
        return {
            "root": self.root.as_posix(),
            "required_seeds": list(self.required_seeds),
            "construction": CONSTRUCTION,
            "protocol_sha256": cert.EXPECTED_PROTOCOL_SHA256,
            "fallback_to_biological_graph": False,
            "mandatory_gates": list(cert.MANDATORY_GATES),
        }


# ---------------------------------------------------------------------------
# structural alignment
# ---------------------------------------------------------------------------


def assert_target_exchange_alignment(biological: Any, randomized: Any) -> dict:
    """Prove the random graph is a re-pairing of the biological edge set.

    Target exchange preserves the source column, the weight column, the node
    identities, the threshold and both degree sequences; only the destination
    column moves. This function re-checks that contract directly on the arrays
    instead of trusting the certificate's gate report.
    """
    checks = {
        "threshold": int(biological.threshold) == int(randomized.threshold),
        "n_nodes": int(biological.n_nodes) == int(randomized.n_nodes),
        "n_edges": int(biological.n_edges) == int(randomized.n_edges),
        "root_ids": np.array_equal(
            np.asarray(biological.root_ids), np.asarray(randomized.root_ids)
        ),
        "edge_src": np.array_equal(
            np.asarray(biological.edge_src), np.asarray(randomized.edge_src)
        ),
        "edge_weight": np.array_equal(
            np.asarray(biological.edge_weight), np.asarray(randomized.edge_weight)
        ),
        "out_degree": np.array_equal(
            np.diff(np.asarray(biological.out_indptr)),
            np.diff(np.asarray(randomized.out_indptr)),
        ),
        "in_degree": np.array_equal(
            np.diff(np.asarray(biological.in_indptr)),
            np.diff(np.asarray(randomized.in_indptr)),
        ),
    }
    failed = sorted(name for name, ok in checks.items() if not ok)
    if failed:
        raise GraphSelectionError(
            "the certified graph is not a target-exchange re-pairing of the "
            f"biological graph; failed invariants: {failed}"
        )
    return {
        "passed": True,
        "checks": checks,
        "note": (
            "edge targets changed; sources, weights, node identities and both "
            "degree sequences are unchanged"
        ),
    }


__all__ = [
    "CONSTRUCTION",
    "CertifiedGraph",
    "CertifiedGraphSource",
    "GraphSelectionError",
    "assert_target_exchange_alignment",
]
