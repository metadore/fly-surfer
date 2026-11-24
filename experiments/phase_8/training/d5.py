"""Owner decisions D5 and D6: the pilot-scoped training authorisation.

SCIENTIFIC STATUS
    D5 (2026-11-22) authorises exactly six training runs: F and Fβ on the
    frozen biological substrate at evaluation seeds 9001, 9002 and 9003, twenty
    episodes per artifact, 120 training episodes in total. It authorises
    nothing else: no E or E-full, no campaign, no Pilot 2-C episode, no floor
    replay, no randomized graph and no change to a frozen parameter.

    D6 (2026-11-22) records that B7 (the G3 §9.3 memory-gate deviation) has no
    subject in that exact D5 plan. It preserves ``status =
    deviation_recorded`` and ``gate_weakened = false``, keeps all sixteen graph
    files and certificates unchanged, and remains non-inheritable. It
    authorises no training by itself.

    This module reads and verifies both records against hashes recomputed from
    disk. It derives no scientific quantity. The global
    :func:`~.gate.assert_training_authorized` keeps refusing: D5 authority is
    narrow, per-artifact and explicit, and is granted only through
    :func:`assert_d5_training_authorized`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import load_phase8_config
from ..campaign.protocol import (
    AMENDMENT_PATH,
    CAMPAIGN_SUMMARY,
    OWNER_DECISION_D3_RECORD,
    PROTOCOL_PATH,
    protocol_identity,
)
from .contracts import (
    CONTRACT_VERSION,
    derive_b3_pairing,
    validate_b3_pairing,
)
from .errors import TrainingConfigError, TrainingNotAuthorized

D5_ID = "D5"
D5_APPROVAL_DATE = "2026-11-22"
D6_ID = "D6"
D6_APPROVAL_DATE = "2026-11-22"

_RECORDS_ROOT = Path(__file__).resolve().parents[3] / "reports"
D5_RECORD_PATH = _RECORDS_ROOT / "phase_8_owner_approvals" / "D5.json"
D6_RECORD_PATH = _RECORDS_ROOT / "phase_8_owner_approvals" / "D6.json"
D4_RECORD_PATH = _RECORDS_ROOT / "phase_8_owner_approvals" / "D4.json"
APPROVED_PROPOSAL_PATH = _RECORDS_ROOT / "PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md"

#: The exact six artifacts D5 authorises, in declaration order.
PILOT_TRAINING_ARTIFACTS = (
    {"condition_id": "F", "evaluation_seed": 9001, "training_seed": 1008, "pool_index": 7, "episodes": 20},
    {"condition_id": "F", "evaluation_seed": 9002, "training_seed": 1014, "pool_index": 13, "episodes": 20},
    {"condition_id": "F", "evaluation_seed": 9003, "training_seed": 1005, "pool_index": 4, "episodes": 20},
    {"condition_id": "F_beta", "evaluation_seed": 9001, "training_seed": 1008, "pool_index": 7, "episodes": 20},
    {"condition_id": "F_beta", "evaluation_seed": 9002, "training_seed": 1014, "pool_index": 13, "episodes": 20},
    {"condition_id": "F_beta", "evaluation_seed": 9003, "training_seed": 1005, "pool_index": 4, "episodes": 20},
)
PILOT_TRAINING_CONDITIONS = ("F", "F_beta")
PILOT_TRAINING_EVALUATION_SEEDS = (9001, 9002, 9003)
PILOT_TRAINING_EPISODES = 20
PILOT_TRAINING_ARTIFACT_COUNT = 6
PILOT_TRAINING_EPISODE_COUNT = 120

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_IDS = {
    "rev4": None,
    "amendment": None,
    "d3": "D3",
    "d4": "D4",
}
_D5_SCOPE_TRUE = (
    "independent_artifacts_per_condition_and_seed",
    "shared_training_seed_within_evaluation_seed",
    "authorises_training_execution",
    "generates_trained_artifacts",
    "runs_training_episodes",
)
_D5_SCOPE_FALSE = (
    "uses_randomized_graph",
    "constructs_randomized_graph",
    "reads_randomized_graph",
    "runs_pilot2c_episodes",
    "runs_floor_replays",
    "runs_confirmatory_campaign",
    "runs_e_or_e_full",
    "discharges_u7",
    "sets_n_seeds_selected",
    "modifies_frozen_parameter",
    "modifies_statistical_constant",
    "modifies_hypothesis",
    "modifies_rev4",
    "modifies_d1",
    "modifies_d2",
    "modifies_d3",
    "modifies_d4",
    "changes_pilot2c_grid",
    "adds_experimental_condition",
)
_D6_SCOPE_FALSE = (
    "b7_subject_in_d5_plan",
    "gate_weakened",
    "graph_access_authorised",
    "graph_construction_authorised",
    "graph_substitution_authorised",
    "authorises_training_execution",
    "grants_b7_exemption",
    "accepts_g3_deviation",
    "resolves_g3_deviation",
    "weakens_graph_certification",
    "modifies_rev4",
    "modifies_g3_summary",
    "regenerates_graph",
    "reads_graph",
    "discharges_u7",
    "sets_n_seeds_selected",
)
_D6_SCOPE_TRUE = (
    "rev4_section_9_3_unchanged",
    "all_graphs_certified",
    "graph_dependent_stages_blocked",
    "non_inheritable",
)


def _sha256_file(path: str | Path) -> str:
    from brain.banc_graph import sha256_file

    return sha256_file(path)


def _hex64(value) -> bool:
    return isinstance(value, str) and bool(_SHA256.match(value))


def _read_json(source: Path, label: str) -> dict:
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "payload": {},
            "failures": [f"the {label} record is missing"],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {
            "path": source.as_posix(),
            "present": True,
            "payload": {},
            "failures": [f"the {label} record is not valid JSON: {error}"],
        }
    if not isinstance(payload, dict):
        return {
            "path": source.as_posix(),
            "present": True,
            "payload": {},
            "failures": [f"the {label} record must be a JSON object"],
        }
    return {"path": source.as_posix(), "present": True, "payload": payload, "failures": []}


def _decision_table(payload: dict, ids: tuple[str, ...], failures: list[str]) -> None:
    decisions = payload.get("owner_decisions")
    if not isinstance(decisions, list):
        failures.append("owner_decisions must be a list")
        return
    declared = {str(item.get("id")) for item in decisions if isinstance(item, dict)}
    if declared != set(ids):
        failures.append(f"owner_decisions must declare exactly {list(ids)}")
    for item in decisions:
        if not isinstance(item, dict):
            failures.append("every owner decision must be an object")
        elif not isinstance(item.get("text"), str) or not item["text"].strip():
            failures.append(f"owner decision {item.get('id')!r} has no text")


def _artefact_table(payload: dict, failures: list[str]) -> None:
    entries = payload.get("authorised_artifacts")
    if not isinstance(entries, list):
        failures.append("authorised_artifacts must be a list")
        return
    expected = [
        (item["condition_id"], item["evaluation_seed"], item["training_seed"],
         item["pool_index"], item["episodes"])
        for item in PILOT_TRAINING_ARTIFACTS
    ]
    observed = []
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append("every authorised artifact must be an object")
            continue
        observed.append(
            (
                entry.get("condition_id"),
                entry.get("evaluation_seed"),
                entry.get("training_seed"),
                entry.get("pool_index"),
                entry.get("episodes"),
            )
        )
    if observed != expected:
        failures.append(
            "authorised_artifacts is not the exact six-artifact D5 table"
        )


def _check_d5_payload(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_decision":
        failures.append("record_kind is not 'phase_8_owner_decision'")
    if payload.get("approval_id") != D5_ID:
        failures.append("approval_id is not 'D5'")
    if payload.get("approval_date") != D5_APPROVAL_DATE:
        failures.append(f"approval_date is not {D5_APPROVAL_DATE!r}")
    if not isinstance(payload.get("decision"), str) or not payload["decision"].strip():
        failures.append("decision must be a non-empty string")

    depends = payload.get("depends_on")
    if not isinstance(depends, dict) or depends.get("approval_id") != "D4":
        failures.append("depends_on.approval_id must be 'D4'")
    elif not _hex64(depends.get("record_sha256")):
        failures.append("depends_on.record_sha256 must be a 64-hex digest")

    proposal = payload.get("approved_proposal")
    if not isinstance(proposal, dict):
        failures.append("approved_proposal must be an object")
    else:
        if proposal.get("id") != "PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW":
            failures.append("approved_proposal.id is not the decision review")
        if proposal.get("path") != "reports/PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md":
            failures.append("approved_proposal.path is not the decision review")
        if not _hex64(proposal.get("sha256")):
            failures.append("approved_proposal.sha256 must be a 64-hex digest")

    sources = payload.get("frozen_sources")
    if not isinstance(sources, dict):
        failures.append("frozen_sources must be an object")
        sources = {}
    for name, approval_id in _SOURCE_IDS.items():
        entry = sources.get(name)
        if not isinstance(entry, dict):
            failures.append(f"frozen_sources.{name} must be an object")
            continue
        if not _hex64(entry.get("sha256")):
            failures.append(f"frozen_sources.{name}.sha256 must be a 64-hex digest")
        if approval_id is not None and entry.get("approval_id") != approval_id:
            failures.append(
                f"frozen_sources.{name}.approval_id must be {approval_id!r}"
            )
    if isinstance(depends, dict) and isinstance(sources.get("d4"), dict):
        if depends.get("record_sha256") != sources["d4"].get("sha256"):
            failures.append("depends_on.record_sha256 does not match frozen_sources.d4")

    _decision_table(payload, ("OD-1", "OD-2", "OD-3", "OD-4", "OD-5", "OD-6"), failures)
    _artefact_table(payload, failures)

    b3 = payload.get("b3_pairing_record")
    expected_pairing = {
        f"{item['condition_id']}:{item['evaluation_seed']}": item["training_seed"]
        for item in PILOT_TRAINING_ARTIFACTS
    }
    if not isinstance(b3, dict):
        failures.append("b3_pairing_record must be an object")
    else:
        if b3.get("contract") != "B3" or b3.get("version") != CONTRACT_VERSION:
            failures.append("b3_pairing_record must declare B3 / D4-v1")
        if b3.get("master_seed") != 20261116:
            failures.append("b3_pairing_record.master_seed must be 20261116")
        if not _hex64(b3.get("derivation_sha256")):
            failures.append("b3_pairing_record.derivation_sha256 must be a 64-hex digest")
        if b3.get("pairing") != expected_pairing:
            failures.append("b3_pairing_record.pairing is not the D5 six-artifact pairing")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    for name in _D5_SCOPE_TRUE:
        if scope.get(name) is not True:
            failures.append(f"scope.{name} must be true")
    for name in _D5_SCOPE_FALSE:
        if scope.get(name) is not False:
            failures.append(f"scope.{name} must be false")
    expected = {
        "stage": "training",
        "rev4_step": "10.5",
        "substrate": "biological_graph",
        "origin": "trained",
        "final_stage": "trained",
        "results_root": "experiments/results/phase_8/training",
        "conditions": ["F", "F_beta"],
        "evaluation_seeds": [9001, 9002, 9003],
        "training_seeds": [1008, 1014, 1005],
        "episodes_per_artifact": PILOT_TRAINING_EPISODES,
        "n_artifacts": PILOT_TRAINING_ARTIFACT_COUNT,
        "n_training_episodes": PILOT_TRAINING_EPISODE_COUNT,
        "training_contracts": ["B3", "B4", "B5", "B6"],
        "checkpoint_history": "every intermediate and the final checkpoint retained",
    }
    for name, value in expected.items():
        if scope.get(name) != value:
            failures.append(f"scope.{name} is not {value!r}")
    for name in ("resume_policy",):
        if not isinstance(scope.get(name), str) or not scope[name].strip():
            failures.append(f"scope.{name} must be a non-empty string")

    prohibitions = payload.get("prohibitions")
    if not isinstance(prohibitions, list) or len(prohibitions) < 10:
        failures.append("prohibitions must list at least ten entries")
    elif not all(isinstance(item, str) and item.strip() for item in prohibitions):
        failures.append("every prohibition must be a non-empty string")
    else:
        text = " ".join(prohibitions)
        for phrase in (
            "randomized graph",
            "Pilot 2-C",
            "E-full",
            "equivalence",
            "twenty episodes",
        ):
            if phrase not in text:
                failures.append(f"prohibitions must mention {phrase!r}")

    not_authorised = payload.get("does_not_authorise")
    if not isinstance(not_authorised, list):
        failures.append("does_not_authorise must be a list")
    else:
        declared = {str(item).strip() for item in not_authorised}
        for phrase in (
            "E or E-full",
            "a confirmatory campaign",
            "a Pilot 2-C episode",
            "a floor replay",
            "a randomized-graph construction or access",
            "U7 discharge or design.n_seeds_selected selection",
        ):
            if phrase not in declared:
                failures.append(f"does_not_authorise must include {phrase!r}")

    authorises = payload.get("authorises")
    if not isinstance(authorises, list):
        failures.append("authorises must be a list")
    else:
        text = " ".join(str(item) for item in authorises)
        for phrase in ("six exact F and Fbeta training runs", "one hundred and twenty", "six trained artifacts"):
            if phrase not in text:
                failures.append(f"authorises must mention {phrase!r}")
    return failures


def _check_d6_payload(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_decision":
        failures.append("record_kind is not 'phase_8_owner_decision'")
    if payload.get("approval_id") != D6_ID:
        failures.append("approval_id is not 'D6'")
    if payload.get("approval_date") != D6_APPROVAL_DATE:
        failures.append(f"approval_date is not {D6_APPROVAL_DATE!r}")
    if not isinstance(payload.get("decision"), str) or not payload["decision"].strip():
        failures.append("decision must be a non-empty string")

    depends = payload.get("depends_on")
    if not isinstance(depends, dict) or depends.get("approval_id") != "D5":
        failures.append("depends_on.approval_id must be 'D5'")
    elif not _hex64(depends.get("record_sha256")):
        failures.append("depends_on.record_sha256 must be a 64-hex digest")

    proposal = payload.get("approved_proposal")
    if not isinstance(proposal, dict):
        failures.append("approved_proposal must be an object")
    elif not _hex64(proposal.get("sha256")):
        failures.append("approved_proposal.sha256 must be a 64-hex digest")

    sources = payload.get("frozen_sources")
    if not isinstance(sources, dict):
        failures.append("frozen_sources must be an object")
        sources = {}
    for name in ("rev4", "amendment", "d3", "d4", "d5", "g3_summary"):
        entry = sources.get(name)
        if not isinstance(entry, dict):
            failures.append(f"frozen_sources.{name} must be an object")
            continue
        if not _hex64(entry.get("sha256")):
            failures.append(f"frozen_sources.{name}.sha256 must be a 64-hex digest")
        if name in ("rev4", "amendment", "d3", "d4", "d5") and not isinstance(
            entry.get("path"), str
        ):
            failures.append(f"frozen_sources.{name}.path must be a string")
    if isinstance(depends, dict) and isinstance(sources.get("d5"), dict):
        if depends.get("record_sha256") != sources["d5"].get("sha256"):
            failures.append("depends_on.record_sha256 does not match frozen_sources.d5")

    _decision_table(payload, ("OD-1", "OD-2", "OD-3", "OD-4"), failures)

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    for name in _D6_SCOPE_FALSE:
        if scope.get(name) is not False:
            failures.append(f"scope.{name} must be false")
    for name in _D6_SCOPE_TRUE:
        if scope.get(name) is not True:
            failures.append(f"scope.{name} must be true")
    exact = {
        "stage": "training",
        "rev4_step": "10.5",
        "g3_status_preserved": "deviation_recorded",
        "gate_gb": 4.0,
        "graphs_unchanged": 16,
        "certificates_unchanged": 16,
    }
    for name, value in exact.items():
        if scope.get(name) != value:
            failures.append(f"scope.{name} is not {value!r}")
    if not isinstance(scope.get("reason"), str) or not scope["reason"].strip():
        failures.append("scope.reason must be a non-empty string")

    blocked = payload.get("blocked_graph_dependent_stages")
    if not isinstance(blocked, list) or len(blocked) < 5:
        failures.append("blocked_graph_dependent_stages must list at least five entries")

    prohibitions = payload.get("prohibitions")
    if not isinstance(prohibitions, list) or len(prohibitions) < 9:
        failures.append("prohibitions must list at least nine entries")
    elif not all(isinstance(item, str) and item.strip() for item in prohibitions):
        failures.append("every prohibition must be a non-empty string")

    not_authorised = payload.get("does_not_authorise")
    if not isinstance(not_authorised, list):
        failures.append("does_not_authorise must be a list")
    else:
        text = " ".join(str(item) for item in not_authorised)
        for phrase in ("graph-dependent", "beyond the exact D5 plan", "Pilot 2-C", "confirmatory campaign"):
            if phrase not in text:
                failures.append(f"does_not_authorise must mention {phrase!r}")
    return failures


def _source_report(record: dict, observed: dict, failures: list[str]) -> dict:
    report: dict[str, dict] = {}
    sources = (record["payload"].get("frozen_sources") or {})
    for name, observed_sha in observed.items():
        entry = sources.get(name) or {}
        recorded = entry.get("sha256")
        report[name] = {
            "recorded_sha256": recorded,
            "observed_sha256": observed_sha,
            "matches": recorded == observed_sha,
        }
    return report


def d5_applicability(
    record_path: str | Path = D5_RECORD_PATH,
    d6_path: str | Path = D6_RECORD_PATH,
    protocol_path: str | Path = PROTOCOL_PATH,
    amendment_path: str | Path = AMENDMENT_PATH,
    d3_path: str | Path = OWNER_DECISION_D3_RECORD,
    d4_path: str | Path = D4_RECORD_PATH,
    proposal_path: str | Path = APPROVED_PROPOSAL_PATH,
    g3_path: str | Path = CAMPAIGN_SUMMARY,
) -> dict:
    """Report whether D5 and D6 are valid and bound to the documents they cite."""
    identity = protocol_identity(protocol_path)
    d5_record = _read_json(Path(record_path), "D5 owner-decision")
    d6_record = _read_json(Path(d6_path), "D6 owner-decision")
    payload = d5_record["payload"]
    d6_payload = d6_record["payload"]
    failures = list(d5_record["failures"]) + list(d6_record["failures"])
    if d5_record["present"]:
        failures.extend(_check_d5_payload(payload))
    if d6_record["present"]:
        failures.extend(_check_d6_payload(d6_payload))

    observed = {
        "rev4": identity.get("sha256"),
        "amendment": _sha256_file(amendment_path) if Path(amendment_path).is_file() else None,
        "d3": _sha256_file(d3_path) if Path(d3_path).is_file() else None,
        "d4": _sha256_file(d4_path) if Path(d4_path).is_file() else None,
        "proposal": _sha256_file(proposal_path) if Path(proposal_path).is_file() else None,
        "g3_summary": _sha256_file(g3_path) if Path(g3_path).is_file() else None,
        "d5_record": _sha256_file(record_path) if Path(record_path).is_file() else None,
    }
    if not identity.get("present"):
        failures.append("the REV4 document is missing")
    elif not identity.get("matches_expected"):
        failures.append("the REV4 document hash does not match the expected freeze")
    for name in ("amendment", "d3", "d4", "proposal", "g3_summary"):
        if observed[name] is None:
            failures.append(f"the {name} source is missing")

    sources = _source_report(d5_record, {
        key: observed[key] for key in ("rev4", "amendment", "d3", "d4")
    }, failures)
    for name, entry in sources.items():
        if not entry["matches"]:
            failures.append(f"the recorded {name} hash does not match the document")
    if isinstance(payload.get("approved_proposal"), dict):
        if payload["approved_proposal"].get("sha256") != observed["proposal"]:
            failures.append("the recorded approved-proposal hash does not match")

    d6_sources = _source_report(d6_record, {
        "rev4": observed["rev4"],
        "amendment": observed["amendment"],
        "d3": observed["d3"],
        "d4": observed["d4"],
        "d5": observed["d5_record"],
        "g3_summary": observed["g3_summary"],
    }, failures)
    for name, entry in d6_sources.items():
        if not entry["matches"]:
            failures.append(f"D6 records a different {name} hash")
    if isinstance(d6_payload.get("depends_on"), dict):
        if d6_payload["depends_on"].get("record_sha256") != observed["d5_record"]:
            failures.append("D6 does not depend on the present D5 record")

    b3 = payload.get("b3_pairing_record") or {}
    b3_report: dict = {"checked": False}
    try:
        config = load_phase8_config()
        pool = tuple(int(seed) for seed in config.campaign.training_seeds)
        derived = derive_b3_pairing(
            PILOT_TRAINING_EVALUATION_SEEDS, pool, master_seed=int(config.campaign.master_seed)
        )
        validate_b3_pairing(
            {"entries": derived["entries"], "training_pool": list(pool),
             "master_seed": derived["master_seed"]},
            evaluation_seeds=PILOT_TRAINING_EVALUATION_SEEDS,
            training_seeds=pool,
            master_seed=int(config.campaign.master_seed),
        )
        pairing_matches = derived["pairing"] == b3.get("pairing")
        sha_matches = derived["sha256"] == b3.get("derivation_sha256")
        if not pairing_matches:
            failures.append("the D5 B3 pairing does not match the declared derivation")
        if not sha_matches:
            failures.append("the D5 B3 derivation digest does not match the declared derivation")
        b3_report = {
            "checked": True,
            "master_seed": int(config.campaign.master_seed),
            "training_pool": list(pool),
            "recorded_sha256": b3.get("derivation_sha256"),
            "derived_sha256": derived["sha256"],
            "pairing_matches": pairing_matches,
            "sha256_matches": sha_matches,
            "entries": derived["entries"],
        }
    except TrainingConfigError as error:
        failures.append(f"the B3 derivation could not be checked: {error}")

    g3_report: dict = {}
    if Path(g3_path).is_file():
        try:
            summary = json.loads(Path(g3_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:  # pragma: no cover - defensive
            failures.append(f"the G3 summary is not valid JSON: {error}")
            summary = {}
        compliance = summary.get("compliance") or {}
        seeds = summary.get("seeds") or []
        g3_report = {
            "path": Path(g3_path).as_posix(),
            "sha256": observed["g3_summary"],
            "status": compliance.get("status"),
            "gate_weakened": compliance.get("gate_weakened"),
            "rev4_section": compliance.get("rev4_section"),
            "gate_gb": compliance.get("gate_gb"),
            "n_graph_seeds": len(seeds),
            "preserved": (
                compliance.get("status") == "deviation_recorded"
                and compliance.get("gate_weakened") is False
                and compliance.get("rev4_section") == "9.3"
                and compliance.get("gate_gb") == 4.0
                and len(seeds) == 16
            ),
        }
        if not g3_report["preserved"]:
            failures.append(
                "the G3 record no longer reports the preserved §9.3 deviation "
                "state (status deviation_recorded, gate_weakened false, 16 graphs)"
            )

    applicable = not failures
    return {
        "path": d5_record["path"],
        "present": d5_record["present"],
        "valid": not _check_d5_payload(payload) if d5_record["present"] else False,
        "applicable": applicable,
        "approval_id": payload.get("approval_id"),
        "approval_date": payload.get("approval_date"),
        "d6": {
            "path": d6_record["path"],
            "present": d6_record["present"],
            "valid": not _check_d6_payload(d6_payload) if d6_record["present"] else False,
            "approval_id": d6_payload.get("approval_id"),
            "sources": d6_sources,
            "scope": dict(d6_payload.get("scope") or {}),
        },
        "authorised_artifacts": [dict(item) for item in (payload.get("authorised_artifacts") or [])],
        "authorised_scope": dict(payload.get("scope") or {}),
        "b3": b3_report,
        "g3": g3_report,
        "frozen_sources": sources,
        "training_execution_authorized": applicable,
        "training_scope": (
            "exactly the six F/F_beta artifacts at evaluation seeds 9001-9003, "
            "twenty episodes each, on the frozen biological substrate"
            if applicable
            else None
        ),
        "does_not_authorise": list(payload.get("does_not_authorise") or []),
        "failures": failures,
        "reason": (
            "D5 is valid and bound; it authorises exactly the six declared "
            "F/F_beta pilot training artifacts, and D6 records that B7 has no "
            "subject in that plan without changing the G3 record"
            if applicable
            else "D5 is not applicable: " + "; ".join(failures[:6])
        ),
    }


def assert_d5_training_authorized(
    condition_id: str,
    evaluation_seed: int,
    *,
    episodes: int | None = None,
    report: dict | None = None,
) -> dict:
    """Return the one authorised artifact entry, or refuse.

    This is the only execution authority in the training package. The global
    :func:`~.gate.assert_training_authorized` continues to refuse: it is not
    widened by D5.
    """
    if report is None:
        report = d5_applicability()
    if not report.get("applicable"):
        raise TrainingNotAuthorized(report["reason"])
    condition = str(condition_id)
    seed = int(evaluation_seed)
    if condition not in PILOT_TRAINING_CONDITIONS:
        raise TrainingNotAuthorized(
            f"D5 authorises F and F_beta only; {condition!r} is outside its scope"
        )
    if seed not in PILOT_TRAINING_EVALUATION_SEEDS:
        raise TrainingNotAuthorized(
            f"D5 authorises evaluation seeds {list(PILOT_TRAINING_EVALUATION_SEEDS)}; "
            f"{seed} is outside its scope"
        )
    for entry in report["authorised_artifacts"]:
        if (
            str(entry.get("condition_id")) == condition
            and int(entry.get("evaluation_seed", -1)) == seed
        ):
            if episodes is not None and int(episodes) != int(entry.get("episodes", -1)):
                raise TrainingNotAuthorized(
                    f"D5 authorises exactly {entry['episodes']} episodes for "
                    f"{condition}:{seed}; {episodes} is outside its scope"
                )
            return dict(entry)
    raise TrainingNotAuthorized(
        f"{condition}:{seed} is not one of the six artifacts D5 authorises"
    )


def describe_d5() -> dict:
    return d5_applicability()


__all__ = [
    "APPROVED_PROPOSAL_PATH",
    "D5_ID",
    "D5_APPROVAL_DATE",
    "D5_RECORD_PATH",
    "D6_ID",
    "D6_APPROVAL_DATE",
    "D6_RECORD_PATH",
    "PILOT_TRAINING_ARTIFACTS",
    "PILOT_TRAINING_ARTIFACT_COUNT",
    "PILOT_TRAINING_CONDITIONS",
    "PILOT_TRAINING_EPISODE_COUNT",
    "PILOT_TRAINING_EPISODES",
    "PILOT_TRAINING_EVALUATION_SEEDS",
    "assert_d5_training_authorized",
    "d5_applicability",
    "describe_d5",
]
