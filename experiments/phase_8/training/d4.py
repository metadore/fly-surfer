"""Owner decision D4: the B3-B6 training-operation declaration.

SCIENTIFIC STATUS
    D4 (2026-11-21) declares how F/Fβ training artifacts would be paired,
    seeded, checkpointed and resumed. It authorises **no execution**: no
    training run, no trained artifact, no Pilot 2-C episode and no floor
    replay. This module reads and verifies the record; it derives no number and
    starts nothing.

    The record is recognised only when all three bindings hold: the REV4 hash it
    names matches the frozen document on disk and the expected freeze, the
    Pilot 2-C amendment hash matches the document on disk, and the D3 record
    hash matches ``D3.json``. A changed source invalidates D4 instead of letting
    it inherit its decisions silently.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..campaign.protocol import (
    AMENDMENT_PATH,
    OWNER_DECISION_D3_RECORD,
    PROTOCOL_PATH,
    protocol_identity,
)
from .errors import TrainingConfigError

D4_ID = "D4"
D4_APPROVAL_DATE = "2026-11-21"
D4_RECORD_PATH = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "phase_8_owner_approvals"
    / "D4.json"
)
D4_DECISION_IDS = ("B3", "B4", "B5", "B6")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_REQUIRED_SCOPE_FALSE = (
    "authorises_training_execution",
    "generates_trained_artifacts",
    "runs_training_episodes",
    "runs_pilot2c_episodes",
    "runs_floor_replays",
    "constructs_randomized_graph",
    "reads_randomized_graph",
    "modifies_frozen_parameter",
    "modifies_statistical_constant",
    "modifies_hypothesis",
    "modifies_rev4",
    "modifies_d1",
    "modifies_d2",
    "modifies_d3",
    "changes_pilot2c_grid",
    "adds_experimental_condition",
    "discharges_u7",
    "sets_n_seeds_selected",
)


def _sha256_file(path: str | Path) -> str:
    from brain.banc_graph import sha256_file

    return sha256_file(path)


def _hex64(value) -> bool:
    return isinstance(value, str) and bool(_SHA256.match(value))


def _read_owner_decision_d4(record_path: str | Path = D4_RECORD_PATH) -> dict:
    source = Path(record_path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "valid": False,
            "payload": {},
            "failures": ["the D4 owner-decision record is missing"],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": [f"the D4 record is not valid JSON: {error}"],
        }
    if not isinstance(payload, dict):
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": ["the D4 record must be a JSON object"],
        }

    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_decision":
        failures.append("record_kind is not 'phase_8_owner_decision'")
    if payload.get("approval_id") != D4_ID:
        failures.append("approval_id is not 'D4'")
    if payload.get("approval_date") != D4_APPROVAL_DATE:
        failures.append(f"approval_date is not {D4_APPROVAL_DATE!r}")
    for name in ("decision",):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{name} must be a non-empty string")

    depends_on = payload.get("depends_on")
    if not isinstance(depends_on, dict) or depends_on.get("approval_id") != "D3":
        failures.append("depends_on.approval_id must be 'D3'")

    sources = payload.get("frozen_sources")
    if not isinstance(sources, dict):
        failures.append("frozen_sources must be an object")
        sources = {}
    for name, expected_id in (
        ("rev4", None),
        ("amendment", None),
        ("d3", "D3"),
    ):
        entry = sources.get(name)
        if not isinstance(entry, dict):
            failures.append(f"frozen_sources.{name} must be an object")
            continue
        if not _hex64(entry.get("sha256")):
            failures.append(f"frozen_sources.{name}.sha256 must be a 64-hex digest")
        if expected_id is not None and entry.get("approval_id") != expected_id:
            failures.append(
                f"frozen_sources.{name}.approval_id must be {expected_id!r}"
            )
    depends_sha = depends_on.get("record_sha256") if isinstance(depends_on, dict) else None
    if not _hex64(depends_sha):
        failures.append("depends_on.record_sha256 must be a 64-hex digest")
    elif isinstance(sources.get("d3"), dict) and depends_sha != sources["d3"].get(
        "sha256"
    ):
        failures.append(
            "depends_on.record_sha256 does not match frozen_sources.d3.sha256"
        )

    decisions = payload.get("owner_decisions")
    if not isinstance(decisions, list):
        failures.append("owner_decisions must be a list")
        decisions = []
    declared_ids = {
        str(item.get("id")) for item in decisions if isinstance(item, dict)
    }
    if declared_ids != set(D4_DECISION_IDS):
        failures.append(
            f"owner_decisions must declare exactly {list(D4_DECISION_IDS)}"
        )
    for item in decisions:
        if not isinstance(item, dict):
            failures.append("every owner decision must be an object")
            continue
        if not isinstance(item.get("text"), str) or not item["text"].strip():
            failures.append(f"owner decision {item.get('id')!r} has no text")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    for name in _REQUIRED_SCOPE_FALSE:
        if scope.get(name) is not False:
            failures.append(f"scope.{name} must be false")
    if "queries" in scope or "estimates" in scope:  # defensive: not part of D4
        failures.append("scope must not estimate or query anything")

    prohibitions = payload.get("prohibitions")
    if not isinstance(prohibitions, list) or len(prohibitions) < 10:
        failures.append("prohibitions must list at least ten entries")
    elif not all(isinstance(item, str) and item.strip() for item in prohibitions):
        failures.append("every prohibition must be a non-empty string")

    not_authorised = payload.get("does_not_authorise")
    if not isinstance(not_authorised, list):
        failures.append("does_not_authorise must be a list")
        not_authorised = []
    if "a training run" not in {str(item).strip() for item in not_authorised}:
        failures.append("does_not_authorise must include 'a training run'")

    return {
        "path": source.as_posix(),
        "present": True,
        "valid": not failures,
        "payload": payload,
        "failures": failures,
    }


def d4_applicability(
    record_path: str | Path = D4_RECORD_PATH,
    protocol_path: str | Path = PROTOCOL_PATH,
    amendment_path: str | Path = AMENDMENT_PATH,
    d3_path: str | Path = OWNER_DECISION_D3_RECORD,
) -> dict:
    """Report whether D4 is valid and bound to the three documents it cites."""
    identity = protocol_identity(protocol_path)
    record = _read_owner_decision_d4(record_path)
    payload = record["payload"]
    sources = payload.get("frozen_sources") or {}
    rev4 = sources.get("rev4") or {}
    amendment = sources.get("amendment") or {}
    d3 = sources.get("d3") or {}

    failures = list(record["failures"])
    amendment_present = Path(amendment_path).is_file()
    d3_present = Path(d3_path).is_file()
    amendment_sha = _sha256_file(amendment_path) if amendment_present else None
    d3_sha = _sha256_file(d3_path) if d3_present else None

    if record["valid"]:
        if not identity["present"]:
            failures.append("the REV4 document is missing")
        elif not identity["matches_expected"]:
            failures.append("the REV4 document hash does not match the expected freeze")
        elif rev4.get("sha256") != identity["sha256"]:
            failures.append("the recorded REV4 hash does not match the document")
        if not amendment_present:
            failures.append("the Pilot 2-C amendment is missing")
        elif amendment.get("sha256") != amendment_sha:
            failures.append("the recorded amendment hash does not match the document")
        if not d3_present:
            failures.append("the D3 record is missing")
        elif d3.get("sha256") != d3_sha:
            failures.append("the recorded D3 hash does not match the record")

    bound_to_rev4 = bool(
        record["valid"]
        and identity["present"]
        and identity["matches_expected"]
        and rev4.get("sha256") == identity["sha256"]
    )
    bound_to_amendment = bool(
        record["valid"] and amendment_present and amendment.get("sha256") == amendment_sha
    )
    bound_to_d3 = bool(record["valid"] and d3_present and d3.get("sha256") == d3_sha)
    applicable = bool(
        record["valid"] and bound_to_rev4 and bound_to_amendment and bound_to_d3
    )

    return {
        "path": record["path"],
        "present": record["present"],
        "valid": record["valid"],
        "applicable": applicable,
        "approval_id": payload.get("approval_id"),
        "approval_date": payload.get("approval_date"),
        "decisions": {
            str(item.get("id")): str(item.get("text"))
            for item in (payload.get("owner_decisions") or [])
            if isinstance(item, dict)
        },
        "frozen_sources": {
            "rev4": {
                "recorded_sha256": rev4.get("sha256"),
                "observed_sha256": identity["sha256"],
                "matches": rev4.get("sha256") == identity["sha256"],
            },
            "amendment": {
                "recorded_sha256": amendment.get("sha256"),
                "observed_sha256": amendment_sha,
                "matches": amendment.get("sha256") == amendment_sha,
            },
            "d3": {
                "recorded_sha256": d3.get("sha256"),
                "observed_sha256": d3_sha,
                "matches": d3.get("sha256") == d3_sha,
            },
        },
        "bound_to_rev4": bound_to_rev4,
        "bound_to_amendment": bound_to_amendment,
        "bound_to_d3": bound_to_d3,
        "training_execution_authorized": False,
        "failures": failures,
        "reason": (
            "D4 is valid and bound; it declares B3-B6 and authorises no "
            "training execution"
            if applicable
            else "D4 is not applicable: " + "; ".join(failures or ["unknown reason"])
        ),
    }


def assert_d4_declared(**kwargs) -> dict:
    """Raise unless D4 is valid and bound; return the applicability report."""
    report = d4_applicability(**kwargs)
    if not report["applicable"]:
        raise TrainingConfigError(report["reason"])
    return report


def describe_d4() -> dict:
    return d4_applicability()


__all__ = [
    "D4_APPROVAL_DATE",
    "D4_DECISION_IDS",
    "D4_ID",
    "D4_RECORD_PATH",
    "assert_d4_declared",
    "d4_applicability",
    "describe_d4",
]
