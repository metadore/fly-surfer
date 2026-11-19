"""Certificate and certified-graph gate for the Phase 8 Condition C null.

SCIENTIFIC STATUS
    A certificate says one thing only: *this file* passed every mandatory
    REV4 §3.3.1 gate for *this* original graph, under *this* protocol hash and
    *these* declared parameters. It is not evidence of biological validity and
    it is not evidence that the chain has mixed. R14 is a plateau diagnostic.

A certificate is written only after `validate_randomization` reports no
failures. An output directory carries a `RUN_INCOMPLETE` marker from creation
until every artifact has been written and hash-verified; a graph whose marker
is still present, whose certificate fails a gate, whose file hash differs from
the certificate, or whose protocol hash differs from the frozen protocol is
refused by `load_certified_graph`. Nothing is silently repaired.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np

SCHEMA_VERSION = 1
MARKER_NAME = "RUN_INCOMPLETE"
CERTIFICATE_NAME = "randomization_certificate.json"
MANIFEST_NAME = "manifest.json"
FAILURE_NAME = "failure_report.json"

#: Frozen Phase 8 protocol. A graph certified against another document is not
#: a Phase 8 artifact.
EXPECTED_PROTOCOL_SHA256 = (
    "e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c"
)
PROTOCOL_PATH = "docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md"

#: REV4 §3.3.1 rejection protocol: R4-R14 (including R9b) and R17 are gates.
MANDATORY_GATES = (
    "R4",
    "R5",
    "R6",
    "R7",
    "R8",
    "R9",
    "R9b",
    "R10",
    "R11",
    "R12",
    "R13",
    "R14",
    "R17",
)
REPORTED_GATES = tuple(f"R{index}" for index in range(1, 19))


class CertificationError(ValueError):
    """A graph may not enter a Phase 8 campaign."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: str | Path, chunk_bytes: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with open(Path(path), "rb") as handle:
        while True:
            block = handle.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def file_identity(path: str | Path, *, root: str | Path | None = None) -> dict:
    """Path (project-relative when possible), byte size and SHA-256."""
    source = Path(path)
    stats = source.stat()
    if root is not None:
        try:
            display = source.resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            display = source.resolve().as_posix()
    else:
        display = source.as_posix()
    return {
        "path": display,
        "bytes": int(stats.st_size),
        "sha256": sha256_file(source),
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write_json_atomic(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    text = json.dumps(_jsonable(dict(payload)), indent=1, sort_keys=False)
    temporary.write_text(text + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return target


@dataclass
class OutputNamespace:
    """A directory that cannot be mistaken for a finished result."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.marker = self.root / MARKER_NAME
        payload = {
            "status": "incomplete",
            "started_at": utc_now(),
            "note": (
                "this marker is removed only after the graph, certificate and "
                "manifest are written and hash-verified"
            ),
        }
        self.marker.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    def path(self, name: str) -> Path:
        return self.root / name

    def fail(self, reason: str, evidence: Mapping[str, Any]) -> Path:
        payload = {
            "status": "failed",
            "failed_at": utc_now(),
            "reason": str(reason),
            "evidence": dict(evidence),
            "namespace": self.root.as_posix(),
        }
        return write_json_atomic(self.path(FAILURE_NAME), payload)

    def complete(self, required: tuple[Path, ...]) -> None:
        missing = [path.name for path in required if not Path(path).is_file()]
        if missing:
            raise CertificationError(f"cannot complete: missing artifacts {missing}")
        self.marker.unlink()

    @property
    def incomplete(self) -> bool:
        return self.marker.exists()


def build_certificate(
    *,
    original_identity: Mapping[str, Any],
    output_identity: Mapping[str, Any],
    protocol_identity: Mapping[str, Any],
    report: Mapping[str, Any],
    master_seed: int,
    campaign_seed: int,
    structure_seed: int,
    swaps_per_edge: float,
    construction: Mapping[str, Any],
    reproducibility: Mapping[str, Any],
    memory: Mapping[str, Any],
    runtime_seconds: float,
    policy_summary: Mapping[str, Any] | None = None,
) -> dict:
    """Assemble the certificate payload from a completed report."""
    if not report.get("passed"):
        raise CertificationError(
            "refusing to write a certificate for a report with failures: "
            f"{report.get('failures')}"
        )
    gates = report["gates"]
    missing = [name for name in MANDATORY_GATES if name not in gates]
    if missing:
        raise CertificationError(f"report is missing mandatory gates {missing}")
    failed = [name for name in MANDATORY_GATES if not gates[name].get("pass")]
    if failed:
        raise CertificationError(f"mandatory gates failed: {failed}")
    if not gates["R14"].get("evaluated"):
        raise CertificationError("R14 was not evaluated; the graph is not certifiable")
    if not reproducibility.get("byte_identical"):
        raise CertificationError("R17 byte-identity was not established")
    if original_identity["sha256"] == output_identity["sha256"]:
        raise CertificationError(
            "original and randomized graph files are identical; a null graph "
            "must differ from the biological graph"
        )
    if protocol_identity["sha256"] != EXPECTED_PROTOCOL_SHA256:
        raise CertificationError(
            "protocol hash does not match the frozen REV4 document: "
            f"{protocol_identity['sha256']}"
        )

    quality = {
        "construction": "target_exchange",
        "u18": "PROPOSED — not approved",
        "protocol_sha256": protocol_identity["sha256"],
        "graph_digest": report["graph_digest"],
        "passed": True,
        "failures": [],
        "gates": {name: gates[name] for name in MANDATORY_GATES},
        "not_a_mixing_proof": (
            "R14 is a plateau diagnostic on the rewiring distance; neither it "
            "nor degree preservation proves that the chain has mixed"
        ),
    }
    summary = report.get("summary") or {}
    if summary.get("graph_digest") not in (None, report["graph_digest"]):
        raise CertificationError(
            "the report summary and the gate report disagree on the graph digest"
        )
    certified_output = dict(output_identity)
    certified_output["graph_digest"] = report["graph_digest"]

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "8",
        "work_package": "G3",
        "artifact": "condition_c_random_graph",
        "created_at": utc_now(),
        "status": "certified",
        "protocol": dict(protocol_identity),
        "original_graph": dict(original_identity),
        "output_graph": certified_output,
        "seed": {
            "master_seed": int(master_seed),
            "campaign_seed": int(campaign_seed),
            "structure_seed": int(structure_seed),
            "entropy": [int(master_seed), int(campaign_seed), 4],
            "derivation_verified": bool(
                gates.get("R18", {}).get("derivation_verified", False)
            ),
        },
        "construction": {
            "method": "target_exchange",
            "parameterisation": "U18 option (a), PROPOSED — not approved",
            "swaps_per_edge": float(swaps_per_edge),
            **dict(construction),
        },
        "reproducibility": dict(reproducibility),
        "report": {
            "passed": True,
            "failures": [],
            "gates": gates,
            "integrity": report.get("integrity"),
            "summary": report.get("summary"),
        },
        "randomization_quality": quality,
        "policy": dict(policy_summary or {}),
        "memory": dict(memory),
        "runtime_seconds": round(float(runtime_seconds), 3),
    }


def write_certificate(
    namespace: OutputNamespace,
    certificate: Mapping[str, Any],
) -> tuple[Path, str]:
    path = write_json_atomic(namespace.path(CERTIFICATE_NAME), certificate)
    return path, sha256_file(path)


def write_manifest(
    namespace: OutputNamespace,
    *,
    certificate: Mapping[str, Any],
    certificate_identity: Mapping[str, Any],
    graph_identity: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> tuple[Path, str]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "phase": "8",
        "work_package": "G3",
        "artifact": "condition_c_random_graph",
        "created_at": utc_now(),
        "status": "complete",
        "protocol": dict(certificate["protocol"]),
        "original_graph": dict(certificate["original_graph"]),
        "output_graph": dict(graph_identity),
        "certificate": dict(certificate_identity),
        "seed": dict(certificate["seed"]),
        "gates_passed": list(MANDATORY_GATES),
        "randomization_quality": dict(certificate["randomization_quality"]),
        "memory": dict(certificate["memory"]),
        "runtime_seconds": certificate["runtime_seconds"],
        **dict(extra or {}),
    }
    path = write_json_atomic(namespace.path(MANIFEST_NAME), payload)
    return path, sha256_file(path)


def load_certificate(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise CertificationError(f"certificate is missing: {source}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CertificationError(
            f"unsupported certificate schema_version {payload.get('schema_version')}"
        )
    return payload


def certificate_refusal_reason(
    certificate: Mapping[str, Any],
    *,
    expected_protocol_sha256: str = EXPECTED_PROTOCOL_SHA256,
) -> str | None:
    """Return the first reason this certificate cannot be used, or None."""
    if certificate.get("status") != "certified":
        return f"certificate status is {certificate.get('status')!r}"
    if certificate.get("protocol", {}).get("sha256") != expected_protocol_sha256:
        return "certificate was produced against a different protocol document"
    if certificate.get("report", {}).get("failures"):
        return f"certificate reports failures {certificate['report']['failures']}"
    gates = certificate.get("report", {}).get("gates", {})
    missing = [name for name in MANDATORY_GATES if name not in gates]
    if missing:
        return f"certificate is missing gates {missing}"
    failed = [name for name in MANDATORY_GATES if not gates[name].get("pass")]
    if failed:
        return f"mandatory gates failed {failed}"
    if not gates["R14"].get("evaluated"):
        return "R14 plateau was not evaluated"
    if not certificate.get("reproducibility", {}).get("byte_identical"):
        return "R17 byte-identical replay was not established"
    if certificate["original_graph"]["sha256"] == certificate["output_graph"]["sha256"]:
        return "original and randomized graph files are identical"
    if not certificate.get("seed", {}).get("derivation_verified"):
        return "structure-seed derivation was not verified against R18"
    return None


def load_certified_graph(
    certificate_path: str | Path,
    *,
    expected_protocol_sha256: str = EXPECTED_PROTOCOL_SHA256,
    verify_file_hash: bool = True,
):
    """Load a graph that is certified, finished and byte-identical to its record.

    Refuses a namespace whose marker is still present, a certificate that
    fails any mandatory gate, a graph file whose SHA-256 differs from the
    certificate, and a graph whose in-memory digest differs from the recorded
    one.
    """
    from brain.banc_graph import BancConnectome
    from experiments.phase_8_random.target_exchange import graph_digest

    path = Path(certificate_path)
    namespace = path.parent
    if (namespace / MARKER_NAME).exists():
        raise CertificationError(
            f"output namespace is marked incomplete: {namespace / MARKER_NAME}"
        )
    certificate = load_certificate(path)
    reason = certificate_refusal_reason(
        certificate, expected_protocol_sha256=expected_protocol_sha256
    )
    if reason is not None:
        raise CertificationError(f"certified graph refused: {reason}")

    graph_path = namespace / Path(certificate["output_graph"]["path"]).name
    if not graph_path.is_file():
        raise CertificationError(f"certified graph file is missing: {graph_path}")
    if verify_file_hash:
        digest = sha256_file(graph_path)
        if digest != certificate["output_graph"]["sha256"]:
            raise CertificationError(
                "graph file SHA-256 does not match the certificate "
                f"({digest} != {certificate['output_graph']['sha256']})"
            )
    graph = BancConnectome.load(graph_path)
    recomputed = graph_digest(graph)
    if recomputed != certificate["output_graph"]["graph_digest"]:
        raise CertificationError(
            "loaded graph digest does not match the certificate "
            f"({recomputed} != {certificate['output_graph']['graph_digest']})"
        )
    return graph, certificate


def structure_record(
    certificate: Mapping[str, Any],
    *,
    certificate_path: str | Path,
    certificate_sha256: str,
) -> dict:
    """The per-seed structure record Conditions C, D and C' require."""
    reason = certificate_refusal_reason(certificate)
    if reason is not None:
        raise CertificationError(f"no structure record for an uncertified graph: {reason}")
    return {
        "graph_digest": certificate["output_graph"]["graph_digest"],
        "graph_path": certificate["output_graph"]["path"],
        "graph_sha256": certificate["output_graph"]["sha256"],
        "construction": "target_exchange",
        "u18_status": "PROPOSED — not approved",
        "certificate_path": str(certificate_path),
        "certificate_sha256": str(certificate_sha256),
        "protocol_sha256": certificate["protocol"]["sha256"],
        "master_seed": certificate["seed"]["master_seed"],
        "campaign_seed": certificate["seed"]["campaign_seed"],
        "seed": certificate["seed"]["structure_seed"],
        "randomization_quality": certificate["randomization_quality"],
    }


def verify_structure_record(
    structure: Mapping[str, Any],
    *,
    expected_protocol_sha256: str = EXPECTED_PROTOCOL_SHA256,
) -> dict:
    """Re-check a structure record against the certificate on disk.

    Conditions C, D and C' receive a structure record. Without this check the
    record is an assertion the caller could write by hand; with it the record
    must match a finished, gate-passing certificate whose file hash still
    holds. A record without a certificate is refused.
    """
    from brain.banc_graph import PROJECT_ROOT

    if not isinstance(structure, Mapping):
        raise CertificationError("structure record must be a mapping")
    declared = structure.get("certificate_path")
    if not isinstance(declared, str) or not declared:
        raise CertificationError(
            "structure record has no certificate_path; an uncertified graph "
            "may not enter a campaign"
        )
    source = Path(declared)
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    if (source.parent / MARKER_NAME).exists():
        raise CertificationError(
            f"certificate namespace is marked incomplete: {source.parent}"
        )
    if not source.is_file():
        raise CertificationError(f"certificate is missing: {source}")
    actual = sha256_file(source)
    if actual != structure.get("certificate_sha256"):
        raise CertificationError(
            "structure record certificate hash does not match the file on disk"
        )
    certificate = load_certificate(source)
    reason = certificate_refusal_reason(
        certificate, expected_protocol_sha256=expected_protocol_sha256
    )
    if reason is not None:
        raise CertificationError(f"structure record refused: {reason}")
    if certificate["output_graph"]["graph_digest"] != structure.get("graph_digest"):
        raise CertificationError("structure record graph digest is not the certified one")
    if certificate["output_graph"]["sha256"] != structure.get("graph_sha256"):
        raise CertificationError("structure record graph hash is not the certified one")
    if certificate["seed"]["structure_seed"] != structure.get("seed"):
        raise CertificationError("structure record seed is not the certified seed")
    return certificate


def load_structure(
    certificate_path: str | Path,
    *,
    expected_protocol_sha256: str = EXPECTED_PROTOCOL_SHA256,
):
    """Load the certified graph together with the record the conditions need.

    One call so that a campaign cannot pair a graph with a hand-written
    structure record: the record is derived from the same certificate and then
    re-verified against the file on disk.
    """
    path = Path(certificate_path)
    graph, certificate = load_certified_graph(
        path, expected_protocol_sha256=expected_protocol_sha256
    )
    record = structure_record(
        certificate,
        certificate_path=path,
        certificate_sha256=sha256_file(path),
    )
    verify_structure_record(record, expected_protocol_sha256=expected_protocol_sha256)
    return graph, record


def describe_certification() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "mandatory_gates": list(MANDATORY_GATES),
        "reported_gates": list(REPORTED_GATES),
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "marker": MARKER_NAME,
        "refusals": [
            "namespace marker present",
            "certificate status not certified",
            "protocol hash mismatch",
            "any mandatory gate failed or missing",
            "R14 not evaluated",
            "R17 byte-identical replay not established",
            "graph file or graph digest differs from the certificate",
            "original and randomized graph files identical",
            "structure-seed derivation not verified",
        ],
    }
