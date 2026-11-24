"""REV4 conformance checks and the execution-authorisation gate.

SCIENTIFIC STATUS
    Validating a configuration against REV4 says that the declared constants
    match the protocol text. It says nothing about scientific validity and it
    does not authorise execution.

    Approval now comes from a separate, auditable owner-decision record rather
    than from the document text. Record **D1** (2026-11-20) approves REV4 §12
    and U1-U18 as written, bound to the document's SHA-256. The REV4 file
    itself is unchanged and its closing paragraph still says it "authorises no
    execution"; D1 is external to the frozen document and is recognised here
    only when the recorded hash matches the protocol on disk. D1 authorises no
    parameter change and bypasses no other gate.

    Record **D2** (2026-11-20) decides that the G3 §9.3 deviation is *not
    applicable to Pilot 1 only*: condition A, seeds 9001-9003, three episodes
    each, no randomized graph and no trained artifact. D2 accepts no deviation
    and weakens no certification. :func:`assert_stage_authorized` applies it
    only to a grid that matches that scope field for field; every other stage
    and every other grid still receives the unchanged B7 refusal.

    Record **D3** (2026-11-20) adopts the Pilot 2-C amendment
    (``docs/PHASE_8_PILOT2C_AMENDMENT.md``), bound by hash. It decides that the
    recorded §9.3 deviation is likewise not applicable to the exact Pilot 2-C
    grid — A, B, F, F_beta, A_prime and the substrate-free floor, seeds
    9001-9003, three episodes each — because that grid constructs and uses no
    randomized graph. D3 accepts no deviation, weakens no certification and
    amends only REV4 §10.8; the amendment and D3 are external to the frozen
    document. :func:`pilot2c_applicability` requires both the amendment hash and
    the REV4 hash to match before the exemption can apply.

    :func:`assert_campaign_authorized` is deliberately *not* stage-aware and
    therefore still raises while any independent gate is open, in particular
    the G3 §9.3 deviation (B7). Campaign, Pilot 2 and training entry points
    call it and cannot inherit the Pilot 1 or Pilot 2-C exemption.

The G3 §9.3 deviation is reported here as a fact, not resolved:
``experiments/results/phase_8_random/campaign_seed_summary.json`` records
``compliance.status = "deviation_recorded"`` and ``gate_weakened: false``. The
16 graphs are certified, but G3 is not complete and the graphs may not be used
for experimental data collection until the owner resolves B7 or an approved
amendment / compliant rerun exists (G5 brief §4-§5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from experiments.phase_8_random.certification import EXPECTED_PROTOCOL_SHA256

from ..config import PROJECT_ROOT, ConfigError, Phase8Config, load_yaml
from ..registry import build_registry, confirmatory_contrasts
from ..seeds import MASTER_SEED

PROTOCOL_PATH = PROJECT_ROOT / "docs" / "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md"
PROTOCOL_ID = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"
#: Registry declaration order: conditions.yaml groups, then the floor.
ARMS_ACTIVE = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "A_prime",
    "C_prime",
    "F_beta",
    "F_init",
    "E_full",
    "floor",
)
CAMPAIGN_SUMMARY = (
    PROJECT_ROOT / "experiments" / "results" / "phase_8_random" / "campaign_seed_summary.json"
)
#: Separate, auditable owner-decision record; not part of the frozen protocol.
OWNER_APPROVAL_RECORD = (
    PROJECT_ROOT / "reports" / "phase_8_owner_approvals" / "D1.json"
)
#: Owner decision that the G3 deviation does not apply to this exact Pilot 1 grid.
OWNER_DECISION_D2_RECORD = (
    PROJECT_ROOT / "reports" / "phase_8_owner_approvals" / "D2.json"
)
#: Hash-bound owner decision adopting the Pilot 2-C amendment.
OWNER_DECISION_D3_RECORD = (
    PROJECT_ROOT / "reports" / "phase_8_owner_approvals" / "D3.json"
)
#: The formal amendment D3 approves. It is not part of the frozen REV4 file.
AMENDMENT_PATH = PROJECT_ROOT / "docs" / "PHASE_8_PILOT2C_AMENDMENT.md"
AMENDMENT_ID = "PHASE_8_PILOT2C_AMENDMENT"
DECISION_ITEM_IDS = tuple(f"U{index}" for index in range(1, 19))

#: The only grid D2 exempts from B7. Anything else receives the unchanged B7
#: refusal; the values are fixed here rather than read from configuration so a
#: changed configuration cannot widen the exemption.
PILOT1_G3_SCOPE = {
    "stage": "pilot1",
    "arms": ("A",),
    "seeds": (9001, 9002, 9003),
    "episodes_per_seed": 3,
    "n_episodes": 9,
}

#: The only grid D3 exempts from B7, and only because it constructs and uses
#: no randomized graph. As with the D2 scope the values are fixed here rather
#: than read from configuration, so a changed configuration cannot widen it.
PILOT2C_G3_SCOPE = {
    "stage": "pilot2c",
    "rev4_step": "10.8",
    "arms": ("A", "B", "F", "F_beta", "A_prime", "floor"),
    "neural_arms": ("A", "B", "F", "F_beta", "A_prime"),
    "floor_arm": "floor",
    "seeds": (9001, 9002, 9003),
    "episodes_per_seed": 3,
    "n_episodes": 54,
    "neural_episodes": 45,
    "floor_replays": 9,
    "stage_purpose": "floor_and_identity_certification",
    "uses_randomized_graph": False,
    "constructs_randomized_graph": False,
    "uses_trained_artifact": True,
    "trained_artifact_conditions": ("F", "F_beta"),
    "g3_applicability": "not_applicable_no_randomized_graph",
    # The registry facts the exemption depends on: every neural arm rides the
    # biological graph, so no arm can silently pull in a randomized graph.
    "substrates": {
        "A": "biological",
        "B": "biological",
        "F": "biological",
        "F_beta": "biological",
        "A_prime": "biological",
    },
    "trains": {
        "A": ("none",),
        "B": ("synapses",),
        "F": ("readout",),
        "F_beta": ("readout",),
        "A_prime": ("none",),
    },
    "eta": {"A": None, "B": 0.5, "F": None, "F_beta": None, "A_prime": 0.0},
}

#: Appendix C and §6.3 declared constants, in the order the protocol lists them.
DECLARED = {
    "master_seed": 20261116,
    "n_seeds_primary": 16,
    "n_seeds_fallback": 10,
    "episodes_per_seed": 10,
    "max_game_updates": 900,
    "sei_updates": 100,
    "alpha": 0.05,
    "holm_family_sizes": (4, 3),
    "bootstrap_resamples": 10_000,
    "bootstrap_seed": 20261116,
    "memory_gate_gb": 4.0,
    "readout_episodes_per_seed": 20,
    "e_gradient_updates": 2000,
    "eta_plastic": 0.5,
    "eta_identity": 0.0,
    "weight_bounds": (0.5, 2.0),
    "max_abs_update_pa": 5.0,
    "tau_e_ms": 20.0,
    "modulation_gain": 1.0,
    "modulation_tau_ms": 50.0,
    "modulation_clip": (-5.0, 5.0),
    "sensory_current_pa": 200.0,
    "decoder_window_ms": 50.0,
    "decoder_min_active_neurons": 3,
    "decoder_min_spikes": 5,
    "decoder_activation": 0.20,
    "decoder_release": 0.10,
}

EXPECTED_CONDITIONS = ("A", "B", "C", "D", "E", "F")
EXPECTED_CONTROLS = ("A_prime", "C_prime", "F_beta", "F_init")
EXPECTED_EXPLORATORY = ("E_full",)
EXPECTED_ETA = {
    "A": None,
    "B": 0.5,
    "C": None,
    "D": 0.5,
    "E": None,
    "F": None,
    "A_prime": 0.0,
    "C_prime": 0.0,
    "F_beta": None,
    "F_init": None,
    "E_full": None,
}
EXPECTED_TRAINS = {
    "A": ("none",),
    "B": ("synapses",),
    "C": ("none",),
    "D": ("synapses",),
    "E": ("policy",),
    "F": ("readout",),
    "A_prime": ("none",),
    "C_prime": ("none",),
    "F_beta": ("readout",),
    "F_init": ("none",),
    "E_full": ("policy",),
}


class CampaignProtocolError(ConfigError):
    """The configuration disagrees with a constant declared in REV4."""


class CampaignNotAuthorized(RuntimeError):
    """No code path may start a Phase 8 campaign on the present approval state."""


def protocol_identity(path: str | Path = PROTOCOL_PATH) -> dict:
    """Hash and approval statement of the frozen REV4 document."""
    from brain.banc_graph import sha256_file

    source = Path(path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "sha256": None,
            "expected_sha256": EXPECTED_PROTOCOL_SHA256,
            "matches_expected": False,
            "authorises_execution": False,
        }
    digest = sha256_file(source)
    text = source.read_text(encoding="utf-8")
    return {
        "path": source.as_posix(),
        "present": True,
        "sha256": digest,
        "expected_sha256": EXPECTED_PROTOCOL_SHA256,
        "matches_expected": digest == EXPECTED_PROTOCOL_SHA256,
        "authorises_execution": "authorises no execution" not in text,
    }


def _read_approval_record(record_path: str | Path) -> dict:
    """Read the separate owner-decision record and check its own structure."""
    source = Path(record_path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "valid": False,
            "payload": {},
            "failures": ["the owner-approval record is missing"],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": [f"the owner-approval record is not valid JSON: {error}"],
        }
    if not isinstance(payload, dict):
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": ["the owner-approval record must be a JSON object"],
        }

    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_approval":
        failures.append("record_kind is not 'phase_8_owner_approval'")
    for name in ("approval_id", "approval_date"):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{name} must be a non-empty string")

    document = payload.get("approved_document")
    if not isinstance(document, dict):
        failures.append("approved_document must be an object")
        document = {}
    if not isinstance(document.get("sha256"), str) or not (
        len(document.get("sha256", "")) == 64
        and all(character in "0123456789abcdef" for character in document.get("sha256", ""))
    ):
        failures.append("approved_document.sha256 must be a 64-hex digest")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    sections = [str(item).strip() for item in (scope.get("sections") or [])]
    if not ({"§12", "12", "section 12", "Section 12"} & set(sections)):
        failures.append("scope.sections must include §12")
    items = {str(item) for item in (scope.get("decision_items") or [])}
    missing = sorted(set(DECISION_ITEM_IDS) - items)
    if missing:
        failures.append(f"scope.decision_items is missing {missing}")
    if scope.get("parameter_modifications_authorised") is not False:
        failures.append("scope.parameter_modifications_authorised must be false")

    return {
        "path": source.as_posix(),
        "present": True,
        "valid": not failures,
        "payload": payload,
        "failures": failures,
    }


def approval_status(
    protocol_path: str | Path = PROTOCOL_PATH,
    record_path: str | Path = OWNER_APPROVAL_RECORD,
) -> dict:
    """The recorded owner decision, recognised only when bound to this REV4.

    Approval is *recorded* rather than inferred from the document text: the
    separate D1 record must exist, be structurally valid, and carry the same
    SHA-256 as the REV4 file on disk. A changed protocol invalidates the
    recorded approval instead of silently inheriting it.
    """
    identity = protocol_identity(protocol_path)
    record = _read_approval_record(record_path)
    payload = record["payload"]
    document = payload.get("approved_document") or {}
    scope = payload.get("scope") or {}
    recorded_sha = document.get("sha256")
    bound = (
        record["valid"]
        and identity["present"]
        and identity["matches_expected"]
        and recorded_sha == identity["sha256"]
    )
    approved = bool(bound)

    if approved:
        reason = (
            "REV4 §12 and U1-U18 are approved as written by recorded owner "
            f"decision {payload.get('approval_id')} "
            f"({payload.get('approval_date')}), bound to REV4 SHA-256 "
            f"{recorded_sha}. The approval authorises no parameter change and "
            "does not bypass any other gate: every independent gate remains "
            "active."
        )
    else:
        failures = list(record["failures"])
        if record["present"] and record["valid"]:
            if not identity["present"]:
                failures.append("the REV4 document is missing")
            elif not identity["matches_expected"]:
                failures.append("the REV4 document hash does not match the expected freeze")
            elif recorded_sha != identity["sha256"]:
                failures.append(
                    "the recorded approval hash does not match the REV4 document"
                )
        reason = (
            "no valid owner approval is recorded: "
            + ("; ".join(failures) if failures else "unknown reason")
            + ". No campaign, training run, pilot or confirmatory data "
            "collection may start."
        )

    return {
        "protocol_id": PROTOCOL_ID,
        "approved": approved,
        "decision_status": (
            "APPROVED - recorded owner decision D1" if approved else "PROPOSED - not approved"
        ),
        "decision_items": list(DECISION_ITEM_IDS),
        "protocol_sha256": identity["sha256"],
        "protocol_matches_expected": identity["matches_expected"],
        "document_authorises_execution": identity["authorises_execution"],
        "approval_basis": "recorded owner decision (external to the frozen document)",
        "approval_record": {
            "path": record["path"],
            "present": record["present"],
            "valid": record["valid"],
            "approval_id": payload.get("approval_id"),
            "approval_date": payload.get("approval_date"),
            "approved_document_sha256": recorded_sha,
            "document_matches_rev4": recorded_sha == identity["sha256"],
            "scope_sections": list(scope.get("sections") or []),
            "decision_items": list(scope.get("decision_items") or []),
            "parameter_modifications_authorised": scope.get(
                "parameter_modifications_authorised"
            ),
            "failures": record["failures"],
        },
        "reason": reason,
    }


def randomization_deviation(path: str | Path = CAMPAIGN_SUMMARY) -> dict:
    """The recorded G3 §9.3 deviation, carried unchanged."""
    source = Path(path)
    if not source.is_file():
        return {
            "summary_path": source.as_posix(),
            "present": False,
            "status": "summary_missing",
            "gate_weakened": False,
            "note": "the G3 campaign summary could not be read; the deviation is unresolved",
        }
    payload = json.loads(source.read_text(encoding="utf-8"))
    compliance = dict(payload.get("compliance") or {})
    seeds = list(payload.get("seeds") or [])
    return {
        "summary_path": source.as_posix(),
        "present": True,
        "status": compliance.get("status"),
        "gate_gb": compliance.get("gate_gb"),
        "gate_weakened": bool(compliance.get("gate_weakened")),
        "min_observed_free_gb": compliance.get("min_observed_free_gb"),
        "construction_runs_below_gate": compliance.get("construction_runs_below_gate"),
        "certified_seeds": [entry.get("seed") for entry in seeds if entry.get("status") == "certified"],
        "note": (
            "the certified graphs were built below the §9.3 4.00 GB gate; G3 is "
            "not complete and the graphs may not be used for experimental data "
            "collection until an approved amendment or a compliant rerun exists"
        ),
    }


def _read_owner_decision(record_path: str | Path) -> dict:
    """Read the D2 record and check its own structure and declared scope."""
    source = Path(record_path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "valid": False,
            "payload": {},
            "failures": ["the D2 owner-decision record is missing"],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": [f"the D2 record is not valid JSON: {error}"],
        }
    if not isinstance(payload, dict):
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": ["the D2 record must be a JSON object"],
        }

    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_decision":
        failures.append("record_kind is not 'phase_8_owner_decision'")
    if payload.get("approval_id") != "D2":
        failures.append("approval_id is not 'D2'")
    for name in ("approval_date", "decision"):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{name} must be a non-empty string")

    document = payload.get("approved_document")
    if not isinstance(document, dict):
        failures.append("approved_document must be an object")
        document = {}
    digest = document.get("sha256")
    if not (
        isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest)
    ):
        failures.append("approved_document.sha256 must be a 64-hex digest")

    depends_on = payload.get("depends_on")
    if not isinstance(depends_on, dict) or depends_on.get("approval_id") != "D1":
        failures.append("depends_on.approval_id must be 'D1'")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    if scope.get("stage") != PILOT1_G3_SCOPE["stage"]:
        failures.append("scope.stage must be 'pilot1'")
    if list(scope.get("arms") or []) != list(PILOT1_G3_SCOPE["arms"]):
        failures.append("scope.arms must be ['A']")
    if [int(item) for item in (scope.get("seeds") or [])] != list(
        PILOT1_G3_SCOPE["seeds"]
    ):
        failures.append("scope.seeds must be [9001, 9002, 9003]")
    if scope.get("episodes_per_seed") != PILOT1_G3_SCOPE["episodes_per_seed"]:
        failures.append("scope.episodes_per_seed must be 3")
    if scope.get("n_episodes") != PILOT1_G3_SCOPE["n_episodes"]:
        failures.append("scope.n_episodes must be 9")
    if scope.get("uses_randomized_graph") is not False:
        failures.append("scope.uses_randomized_graph must be false")
    if scope.get("uses_trained_artifact") is not False:
        failures.append("scope.uses_trained_artifact must be false")
    if scope.get("g3_applicability") != "not_applicable_to_pilot1_only":
        failures.append("scope.g3_applicability must be 'not_applicable_to_pilot1_only'")
    if scope.get("accepts_g3_deviation") is not False:
        failures.append("scope.accepts_g3_deviation must be false")
    if scope.get("weakens_graph_certification") is not False:
        failures.append("scope.weakens_graph_certification must be false")
    if scope.get("parameter_modifications_authorised") is not False:
        failures.append("scope.parameter_modifications_authorised must be false")

    return {
        "path": source.as_posix(),
        "present": True,
        "valid": not failures,
        "payload": payload,
        "failures": failures,
    }


def g3_applicability(
    record_path: str | Path = OWNER_DECISION_D2_RECORD,
    protocol_path: str | Path = PROTOCOL_PATH,
) -> dict:
    """D2, recognised only when it is valid and bound to this REV4.

    ``pilot1_exempt`` is true only for a structurally valid D2 whose recorded
    document hash matches the REV4 file on disk. It never changes the recorded
    deviation; it only reports that the deviation does not apply to the exact
    Pilot 1 grid.
    """
    identity = protocol_identity(protocol_path)
    record = _read_owner_decision(record_path)
    payload = record["payload"]
    document = payload.get("approved_document") or {}
    scope = payload.get("scope") or {}
    recorded_sha = document.get("sha256")
    bound = (
        record["valid"]
        and identity["present"]
        and identity["matches_expected"]
        and recorded_sha == identity["sha256"]
    )
    failures = list(record["failures"])
    if record["valid"] and not bound:
        if not identity["present"]:
            failures.append("the REV4 document is missing")
        elif not identity["matches_expected"]:
            failures.append("the REV4 document hash does not match the expected freeze")
        else:
            failures.append(
                "the recorded D2 document hash does not match the REV4 document"
            )
    return {
        "path": record["path"],
        "present": record["present"],
        "valid": record["valid"],
        "bound_to_rev4": bool(bound),
        "pilot1_exempt": bool(bound),
        "approval_id": payload.get("approval_id"),
        "approval_date": payload.get("approval_date"),
        "scope": dict(scope),
        "recorded_document_sha256": recorded_sha,
        "document_matches_rev4": recorded_sha == identity["sha256"],
        "accepts_g3_deviation": scope.get("accepts_g3_deviation"),
        "weakens_graph_certification": scope.get("weakens_graph_certification"),
        "failures": failures,
    }


def _pilot1_scope_failures(config: Phase8Config | None, plan: Any) -> list[str]:
    """Every way a requested grid differs from the exact D2 scope."""
    failures: list[str] = []
    if plan is None:
        return ["no Pilot 1 plan was supplied, so the D2 scope cannot be checked"]
    if getattr(plan, "stage", None) != PILOT1_G3_SCOPE["stage"]:
        failures.append(f"stage is {getattr(plan, 'stage', None)!r}, not 'pilot1'")
    arms = tuple(str(item) for item in (getattr(plan, "arms", ()) or ()))
    if arms != PILOT1_G3_SCOPE["arms"]:
        failures.append(f"arms are {list(arms)!r}, not ['A']")
    try:
        seeds = tuple(int(item) for item in (getattr(plan, "seeds", ()) or ()))
    except (TypeError, ValueError):
        failures.append("seeds are not integers")
        seeds = ()
    if seeds != PILOT1_G3_SCOPE["seeds"]:
        failures.append(f"seeds are {list(seeds)!r}, not [9001, 9002, 9003]")
    if int(getattr(plan, "episodes", -1)) != PILOT1_G3_SCOPE["episodes_per_seed"]:
        failures.append("episodes_per_seed is not 3")
    if bool(getattr(plan, "estimates_contrasts", True)):
        failures.append("the plan estimates contrasts; Pilot 1 may not")
    try:
        n_entries = len(plan.entries())
    except Exception:  # noqa: BLE001 - a malformed plan is a scope failure
        failures.append("the plan exposes no entry grid")
        n_entries = -1
    if n_entries != PILOT1_G3_SCOPE["n_episodes"]:
        failures.append(f"the plan has {n_entries} entries, not 9")

    if config is None:
        failures.append("no configuration was supplied, so the substrate cannot be checked")
        return failures

    try:
        spec = build_registry(config.conditions).spec("A")
    except ConfigError as error:
        failures.append(f"condition A is not registered: {error}")
        return failures
    if spec.substrate != "biological":
        failures.append(f"condition A substrate is {spec.substrate!r}, not 'biological'")
    if spec.requires_structure:
        failures.append("condition A requires a certified structure record")
    if tuple(spec.trains) != ("none",):
        failures.append(f"condition A trains {list(spec.trains)!r}, so it needs an artifact")
    if spec.eta is not None:
        failures.append("condition A declares a plasticity rate")
    declared = tuple(int(item) for item in config.campaign.pilot_seeds[:3])
    if declared != PILOT1_G3_SCOPE["seeds"]:
        failures.append(
            f"the configured pilot seeds are {list(declared)!r}, not [9001, 9002, 9003]"
        )
    return failures


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _amendment_identity(path: str | Path = AMENDMENT_PATH) -> dict:
    """Hash the amendment document D3 approves, or report that it is absent."""
    from brain.banc_graph import sha256_file

    source = Path(path)
    if not source.is_file():
        return {"path": source.as_posix(), "present": False, "sha256": None}
    return {"path": source.as_posix(), "present": True, "sha256": sha256_file(source)}


def _read_owner_decision_d3(record_path: str | Path) -> dict:
    """Read the D3 record and check its structure and declared scope."""
    source = Path(record_path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "valid": False,
            "payload": {},
            "failures": ["the D3 owner-decision record is missing"],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": [f"the D3 record is not valid JSON: {error}"],
        }
    if not isinstance(payload, dict):
        return {
            "path": source.as_posix(),
            "present": True,
            "valid": False,
            "payload": {},
            "failures": ["the D3 record must be a JSON object"],
        }

    failures: list[str] = []
    if payload.get("record_kind") != "phase_8_owner_decision":
        failures.append("record_kind is not 'phase_8_owner_decision'")
    if payload.get("approval_id") != "D3":
        failures.append("approval_id is not 'D3'")
    for name in ("approval_date", "decision"):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{name} must be a non-empty string")

    depends_on = payload.get("depends_on")
    if not isinstance(depends_on, dict) or depends_on.get("approval_id") != "D1":
        failures.append("depends_on.approval_id must be 'D1'")

    document = payload.get("approved_document")
    if not isinstance(document, dict):
        failures.append("approved_document must be an object")
        document = {}
    if document.get("id") != AMENDMENT_ID:
        failures.append(f"approved_document.id must be {AMENDMENT_ID!r}")
    if not _is_hex64(document.get("sha256")):
        failures.append("approved_document.sha256 must be a 64-hex digest")

    amended = payload.get("amends_document")
    if not isinstance(amended, dict):
        failures.append("amends_document must be an object")
        amended = {}
    if amended.get("id") != PROTOCOL_ID:
        failures.append(f"amends_document.id must be {PROTOCOL_ID!r}")
    if not _is_hex64(amended.get("sha256")):
        failures.append("amends_document.sha256 must be a 64-hex digest")
    clauses = {str(item) for item in (amended.get("clauses_amended") or [])}
    if "10.8" not in clauses:
        failures.append("amends_document.clauses_amended must include '10.8'")

    decisions = payload.get("owner_decisions")
    if not isinstance(decisions, list):
        failures.append("owner_decisions must be a list")
        decisions = []
    declared_ids = {
        str(item.get("id")) for item in decisions if isinstance(item, dict)
    }
    expected_ids = {f"OD-{index}" for index in range(1, 8)}
    if declared_ids != expected_ids:
        failures.append("owner_decisions must declare OD-1 through OD-7")

    prohibitions = payload.get("prohibitions")
    if not isinstance(prohibitions, list) or len(prohibitions) < 10:
        failures.append("prohibitions must list at least ten entries")
    elif not all(isinstance(item, str) and item.strip() for item in prohibitions):
        failures.append("every prohibition must be a non-empty string")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append("scope must be an object")
        scope = {}
    expected = PILOT2C_G3_SCOPE

    def expect(name: str, value: Any, label: str) -> None:
        if scope.get(name) != value:
            failures.append(f"scope.{name} must be {label}")

    expect("stage", expected["stage"], "'pilot2c'")
    expect("rev4_step", expected["rev4_step"], "'10.8'")
    expect("arms", list(expected["arms"]), str(list(expected["arms"])))
    expect("neural_arms", list(expected["neural_arms"]), str(list(expected["neural_arms"])))
    expect("floor_arm", expected["floor_arm"], "'floor'")
    try:
        seeds_ok = [int(item) for item in (scope.get("seeds") or [])] == list(
            expected["seeds"]
        )
    except (TypeError, ValueError):
        seeds_ok = False
    if not seeds_ok:
        failures.append("scope.seeds must be [9001, 9002, 9003]")
    expect("episodes_per_seed", expected["episodes_per_seed"], "3")
    expect("n_episodes", expected["n_episodes"], "54")
    expect("neural_episodes", expected["neural_episodes"], "45")
    expect("floor_replays", expected["floor_replays"], "9")
    expect("uses_randomized_graph", False, "false")
    expect("constructs_randomized_graph", False, "false")
    expect("uses_trained_artifact", True, "true")
    expect(
        "trained_artifact_conditions",
        list(expected["trained_artifact_conditions"]),
        "['F', 'F_beta']",
    )
    expect("trains_anything_here", False, "false")
    expect("g3_applicability", expected["g3_applicability"], repr(expected["g3_applicability"]))
    expect("accepts_g3_deviation", False, "false")
    expect("weakens_graph_certification", False, "false")
    expect("estimates_contrasts", False, "false")
    expect("hypothesis_tests", [], "[]")
    expect("selects_n_seeds", False, "false")
    expect("discharges_u7", False, "false")
    expect("parameter_modifications_authorised", False, "false")
    expect("results_root", "experiments/results/phase_8/pilot2c", "the Pilot 2-C root")
    expect(
        "stage_purpose",
        expected["stage_purpose"],
        repr(expected["stage_purpose"]),
    )

    return {
        "path": source.as_posix(),
        "present": True,
        "valid": not failures,
        "payload": payload,
        "failures": failures,
    }


def pilot2c_applicability(
    record_path: str | Path = OWNER_DECISION_D3_RECORD,
    protocol_path: str | Path = PROTOCOL_PATH,
    amendment_path: str | Path = AMENDMENT_PATH,
) -> dict:
    """D3, recognised only when valid and bound to this REV4 and amendment.

    ``applicable`` is true only for a structurally valid D3 whose recorded
    amendment hash matches the file on disk and whose recorded REV4 hash matches
    the frozen protocol. It never accepts or weakens the recorded deviation; it
    reports only that the deviation does not apply to a grid that builds no
    randomized graph.
    """
    identity = protocol_identity(protocol_path)
    amendment = _amendment_identity(amendment_path)
    record = _read_owner_decision_d3(record_path)
    payload = record["payload"]
    document = payload.get("approved_document") or {}
    amended = payload.get("amends_document") or {}
    scope = payload.get("scope") or {}
    recorded_amend_sha = document.get("sha256")
    recorded_rev4_sha = amended.get("sha256")

    failures = list(record["failures"])
    if record["valid"]:
        if not amendment["present"]:
            failures.append("the approved amendment document is missing")
        elif recorded_amend_sha != amendment["sha256"]:
            failures.append(
                "the recorded amendment hash does not match the document on disk"
            )
        if not identity["present"]:
            failures.append("the REV4 document is missing")
        elif not identity["matches_expected"]:
            failures.append("the REV4 document hash does not match the expected freeze")
        elif recorded_rev4_sha != identity["sha256"]:
            failures.append(
                "the recorded amends_document hash does not match the REV4 document"
            )

    bound = not failures
    return {
        "path": record["path"],
        "present": record["present"],
        "valid": record["valid"],
        "amendment_path": amendment["path"],
        "amendment_present": amendment["present"],
        "amendment_sha256": amendment["sha256"],
        "recorded_amendment_sha256": recorded_amend_sha,
        "amendment_matches_disk": recorded_amend_sha == amendment["sha256"],
        "bound_to_rev4": bool(
            record["valid"]
            and identity["present"]
            and identity["matches_expected"]
            and recorded_rev4_sha == identity["sha256"]
        ),
        "applicable": bool(bound),
        "approval_id": payload.get("approval_id"),
        "approval_date": payload.get("approval_date"),
        "scope": dict(scope),
        "accepts_g3_deviation": scope.get("accepts_g3_deviation"),
        "weakens_graph_certification": scope.get("weakens_graph_certification"),
        "failures": failures,
    }


def _pilot2c_scope_failures(config: Phase8Config | None, plan: Any) -> list[str]:
    """Every way a requested grid differs from the exact D3 Pilot 2-C scope."""
    failures: list[str] = []
    if plan is None:
        return ["no Pilot 2-C plan was supplied, so the D3 scope cannot be checked"]
    if getattr(plan, "stage", None) != PILOT2C_G3_SCOPE["stage"]:
        failures.append(f"stage is {getattr(plan, 'stage', None)!r}, not 'pilot2c'")
    arms = tuple(str(item) for item in (getattr(plan, "arms", ()) or ()))
    if arms != PILOT2C_G3_SCOPE["arms"]:
        failures.append(
            f"arms are {list(arms)!r}, not {list(PILOT2C_G3_SCOPE['arms'])!r}"
        )
    try:
        seeds = tuple(int(item) for item in (getattr(plan, "seeds", ()) or ()))
    except (TypeError, ValueError):
        failures.append("seeds are not integers")
        seeds = ()
    if seeds != PILOT2C_G3_SCOPE["seeds"]:
        failures.append(f"seeds are {list(seeds)!r}, not [9001, 9002, 9003]")
    if int(getattr(plan, "episodes", -1)) != PILOT2C_G3_SCOPE["episodes_per_seed"]:
        failures.append("episodes_per_seed is not 3")
    if bool(getattr(plan, "estimates_contrasts", True)):
        failures.append("the plan estimates contrasts; Pilot 2-C may not")
    if getattr(plan, "stage_purpose", None) != PILOT2C_G3_SCOPE["stage_purpose"]:
        failures.append(
            f"stage_purpose is {getattr(plan, 'stage_purpose', None)!r}, not "
            f"{PILOT2C_G3_SCOPE['stage_purpose']!r}"
        )
    try:
        entries = tuple(plan.entries())
    except Exception:  # noqa: BLE001 - a malformed plan is a scope failure
        failures.append("the plan exposes no entry grid")
        entries = ()
    if len(entries) != PILOT2C_G3_SCOPE["n_episodes"]:
        failures.append(
            f"the plan has {len(entries)} entries, not "
            f"{PILOT2C_G3_SCOPE['n_episodes']}"
        )
    if arms:
        counts = {arm: sum(1 for entry in entries if entry[0] == arm) for arm in arms}
        neural = {
            arm: counts.get(arm, 0) for arm in PILOT2C_G3_SCOPE["neural_arms"]
        }
        if sum(neural.values()) != PILOT2C_G3_SCOPE["neural_episodes"]:
            failures.append(
                f"the plan has {sum(neural.values())} neural episodes, not "
                f"{PILOT2C_G3_SCOPE['neural_episodes']}"
            )
        if counts.get(PILOT2C_G3_SCOPE["floor_arm"], 0) != PILOT2C_G3_SCOPE["floor_replays"]:
            failures.append(
                f"the plan has {counts.get(PILOT2C_G3_SCOPE['floor_arm'], 0)} floor "
                f"replays, not {PILOT2C_G3_SCOPE['floor_replays']}"
            )

    if config is None:
        failures.append("no configuration was supplied, so the substrate cannot be checked")
        return failures

    try:
        registry = build_registry(config.conditions)
    except ConfigError as error:
        failures.append(f"the condition registry cannot be built: {error}")
        return failures

    for arm in PILOT2C_G3_SCOPE["neural_arms"]:
        try:
            spec = registry.spec(arm)
        except ConfigError as error:
            failures.append(f"condition {arm} is not registered: {error}")
            continue
        if spec.requires_structure:
            failures.append(
                f"condition {arm} requires a certified structure record, so the grid "
                "is not free of randomized graphs"
            )
        substrate = PILOT2C_G3_SCOPE["substrates"][arm]
        if spec.substrate != substrate:
            failures.append(
                f"condition {arm} substrate is {spec.substrate!r}, not {substrate!r}"
            )
        trains = PILOT2C_G3_SCOPE["trains"][arm]
        if tuple(spec.trains) != trains:
            failures.append(
                f"condition {arm} trains {list(spec.trains)!r}, not {list(trains)!r}"
            )
        eta = PILOT2C_G3_SCOPE["eta"][arm]
        if spec.eta != eta:
            failures.append(f"condition {arm} eta is {spec.eta!r}, not {eta!r}")

    try:
        floor_spec = registry.spec(PILOT2C_G3_SCOPE["floor_arm"])
    except ConfigError as error:
        failures.append(f"the floor arm is not registered: {error}")
    else:
        if floor_spec.substrate != "none":
            failures.append(
                f"the floor substrate is {floor_spec.substrate!r}, not 'none'"
            )
        if tuple(floor_spec.trains) != ("none",):
            failures.append("the floor arm must not train anything")
        if floor_spec.requires_structure:
            failures.append("the floor arm must not require a structure record")
    if config.campaign.floor_arm != PILOT2C_G3_SCOPE["floor_arm"]:
        failures.append(
            f"the configured floor arm is {config.campaign.floor_arm!r}, not 'floor'"
        )
    declared = tuple(int(item) for item in config.campaign.pilot_seeds[:3])
    if declared != PILOT2C_G3_SCOPE["seeds"]:
        failures.append(
            f"the configured pilot seeds are {list(declared)!r}, not [9001, 9002, 9003]"
        )
    return failures


def stage_authorization(
    stage: str,
    *,
    config: Phase8Config | None = None,
    plan: Any = None,
    protocol_path: str | Path = PROTOCOL_PATH,
    approval_record_path: str | Path = OWNER_APPROVAL_RECORD,
    decision_record_path: str | Path = OWNER_DECISION_D2_RECORD,
    decision3_record_path: str | Path = OWNER_DECISION_D3_RECORD,
    amendment_path: str | Path = AMENDMENT_PATH,
    deviation_path: str | Path = CAMPAIGN_SUMMARY,
) -> dict:
    """Authorisation for one named stage.

    The recorded approval (B1) must hold for every stage. B7 is waived only
    when the supplied plan matches the exact scope field for field *and* the
    matching owner decision is valid and bound: D2 for ``pilot1`` and D3 (with
    its amendment) for ``pilot2c``. No other stage inherits either exemption,
    and neither exemption accepts or weakens the recorded deviation.
    """
    approval = approval_status(protocol_path, approval_record_path)
    deviation = randomization_deviation(deviation_path)
    decision = g3_applicability(decision_record_path, protocol_path)
    decision3 = pilot2c_applicability(
        decision3_record_path, protocol_path, amendment_path
    )
    blockers: list[str] = []
    exemption = {
        "applied": False,
        "record": decision["path"],
        "reason": (
            "the G3 exemption is available to the exact Pilot 1 grid (D2) and "
            "the exact Pilot 2-C grid (D3) only"
        ),
    }

    if not approval["approved"]:
        blockers.append("B1: " + approval["reason"])

    if deviation.get("status") != "compliant":
        if stage == PILOT1_G3_SCOPE["stage"]:
            if not decision["pilot1_exempt"]:
                blockers.append(
                    "B7: the G3 deviation remains blocking because the D2 record is "
                    "not valid and bound to this REV4: "
                    + "; ".join(decision["failures"] or ["unknown reason"])
                )
            else:
                scope_failures = _pilot1_scope_failures(config, plan)
                if scope_failures:
                    blockers.append(
                        "B7: the requested grid is not the D2 Pilot 1 scope: "
                        + "; ".join(scope_failures)
                    )
                else:
                    exemption = {
                        "applied": True,
                        "record": decision["path"],
                        "approval_id": decision["approval_id"],
                        "approval_date": decision["approval_date"],
                        "reason": (
                            "D2 records that the G3 deviation is not applicable to "
                            "this exact Pilot 1 grid (condition A, seeds 9001-9003, "
                            "three episodes each, no randomized graph, no trained "
                            "artifact). The deviation itself remains recorded and "
                            "unaccepted."
                        ),
                        "scope": {
                            "stage": PILOT1_G3_SCOPE["stage"],
                            "arms": list(PILOT1_G3_SCOPE["arms"]),
                            "seeds": list(PILOT1_G3_SCOPE["seeds"]),
                            "episodes_per_seed": PILOT1_G3_SCOPE["episodes_per_seed"],
                            "n_episodes": PILOT1_G3_SCOPE["n_episodes"],
                            "uses_randomized_graph": False,
                            "uses_trained_artifact": False,
                        },
                    }
        elif stage == PILOT2C_G3_SCOPE["stage"]:
            if not decision3["applicable"]:
                blockers.append(
                    "B7: the requested Pilot 2-C grid has no valid, hash-bound D3 "
                    "decision: "
                    + "; ".join(decision3["failures"] or ["unknown reason"])
                )
            else:
                scope_failures = _pilot2c_scope_failures(config, plan)
                if scope_failures:
                    blockers.append(
                        "B7: the requested grid is not the D3 Pilot 2-C scope: "
                        + "; ".join(scope_failures)
                    )
                else:
                    exemption = {
                        "applied": True,
                        "record": decision3["path"],
                        "approval_id": decision3["approval_id"],
                        "approval_date": decision3["approval_date"],
                        "reason": (
                            "D3 adopts the Pilot 2-C amendment for this exact grid "
                            "(A, B, F, F_beta, A_prime and the floor; seeds "
                            "9001-9003; three episodes per seed; no randomized "
                            "graph). The grid constructs and reads no randomized "
                            "graph, so the recorded §9.3 deviation does not apply "
                            "to it; the deviation remains recorded and unaccepted "
                            "and B7 stays open for every other stage."
                        ),
                        "scope": {
                            "stage": PILOT2C_G3_SCOPE["stage"],
                            "arms": list(PILOT2C_G3_SCOPE["arms"]),
                            "seeds": list(PILOT2C_G3_SCOPE["seeds"]),
                            "episodes_per_seed": PILOT2C_G3_SCOPE["episodes_per_seed"],
                            "n_episodes": PILOT2C_G3_SCOPE["n_episodes"],
                            "neural_episodes": PILOT2C_G3_SCOPE["neural_episodes"],
                            "floor_replays": PILOT2C_G3_SCOPE["floor_replays"],
                            "uses_randomized_graph": False,
                            "uses_trained_artifact": True,
                            "stage_purpose": PILOT2C_G3_SCOPE["stage_purpose"],
                        },
                    }
        else:
            blockers.append(
                f"B7: stage {stage!r} does not inherit the D2 Pilot 1 or D3 "
                "Pilot 2-C exemption; the G3 randomization set has a recorded "
                f"§9.3 deviation (status {deviation.get('status')!r}, gate "
                f"weakened: {deviation.get('gate_weakened')}) and remains "
                "blocking"
            )

    return {
        "stage": str(stage),
        "authorized": not blockers,
        "blockers": blockers,
        "exemption": exemption,
        "approval": approval,
        "g3_applicability": decision,
        "pilot2c_applicability": decision3,
        "randomization_deviation": deviation,
    }


def assert_stage_authorized(stage: str, **kwargs: Any) -> dict:
    """Raise unless :func:`stage_authorization` authorises this stage."""
    report = stage_authorization(stage, **kwargs)
    if not report["authorized"]:
        raise CampaignNotAuthorized(
            " ".join(report["blockers"]) + " This entry point does not start the stage."
        )
    return report


def assert_campaign_authorized(*_args: Any, **_kwargs: Any) -> None:
    """Refuse unless a recorded approval exists and no other gate is open.

    This is the campaign-wide gate: it is deliberately not stage-aware, so
    neither the D2 Pilot 1 exemption nor the D3 Pilot 2-C exemption can be
    inherited by a campaign, another pilot or a training run. With D1 recorded
    and B7 open it still raises.
    """
    status = approval_status()
    deviation = randomization_deviation()
    reasons: list[str] = []
    if not status["approved"]:
        reasons.append(status["reason"])
    if deviation.get("status") != "compliant":
        reasons.append(
            "the G3 randomization set has a recorded §9.3 deviation "
            f"(status {deviation['status']!r}, gate weakened: "
            f"{deviation['gate_weakened']}); B7 remains open and the certified "
            "graphs may not be used for experimental data collection until the "
            "owner resolves its applicability or an approved amendment / "
            "compliant rerun exists"
        )
    if reasons:
        raise CampaignNotAuthorized(
            " ".join(reasons) + " This entry point does not start campaigns."
        )


# ---------------------------------------------------------------------------
# static conformance
# ---------------------------------------------------------------------------


def _resolve(relative: str) -> Path:
    source = Path(relative)
    return source if source.is_absolute() else PROJECT_ROOT / source


def _check(checks: list[dict], name: str, actual: Any, expected: Any, source: str) -> None:
    passed = actual == expected
    checks.append(
        {
            "name": name,
            "actual": actual,
            "expected": expected,
            "source": source,
            "pass": bool(passed),
        }
    )


def validate_campaign(
    config: Phase8Config,
    *,
    strict: bool = True,
    protocol_path: str | Path = PROTOCOL_PATH,
) -> dict:
    """Compare the loaded configuration with the constants REV4 declares.

    ``n_seeds_selected`` is reported, not failed: null is a legitimate
    pre-pilot state, but the evaluation plan refuses to resolve while it is
    null. Every other mismatch is a hard error in strict mode.
    """
    checks: list[dict] = []

    identity = protocol_identity(protocol_path)
    _check(checks, "protocol.present", identity["present"], True, "REV4")
    _check(
        checks,
        "protocol.sha256",
        identity["matches_expected"],
        True,
        "REV4 / Phase 8 protocol freeze",
    )

    campaign = config.campaign
    for name in (
        "master_seed",
        "n_seeds_primary",
        "n_seeds_fallback",
        "episodes_per_seed",
        "max_game_updates",
        "sei_updates",
        "alpha",
        "bootstrap_resamples",
        "bootstrap_seed",
        "memory_gate_gb",
        "readout_episodes_per_seed",
        "e_gradient_updates",
    ):
        _check(
            checks,
            f"campaign.{name}",
            getattr(campaign, name),
            DECLARED[name],
            "REV4 Appendix C / §6.3 / §9.3",
        )
    _check(
        checks,
        "campaign.holm_family_sizes",
        tuple(campaign.holm_family_sizes),
        DECLARED["holm_family_sizes"],
        "REV4 §7.5 / U14",
    )
    _check(
        checks,
        "campaign.n_seeds_selected",
        campaign.n_seeds_selected,
        None,
        "pre-pilot state (null until U7 is resolved)",
    )
    _check(
        checks,
        "campaign.conditions",
        tuple(campaign.conditions),
        EXPECTED_CONDITIONS,
        "REV4 §3",
    )
    _check(
        checks,
        "campaign.control_arms",
        tuple(campaign.control_arms),
        EXPECTED_CONTROLS,
        "REV4 §3.6 / §3.8",
    )
    _check(
        checks,
        "campaign.exploratory_arms",
        tuple(campaign.exploratory_arms),
        EXPECTED_EXPLORATORY,
        "REV4 §3.5 / U8",
    )
    _check(
        checks,
        "campaign.floor_arm",
        campaign.floor_arm,
        "floor",
        "REV4 §3.6.2 / U10",
    )

    registry = build_registry(config.conditions)
    _check(
        checks,
        "registry.evaluation_arms",
        tuple(registry.evaluation_arms),
        ARMS_ACTIVE,
        "REV4 §3 arms plus the substrate-free floor",
    )
    for arm, eta in EXPECTED_ETA.items():
        _check(
            checks,
            f"eta.{arm}",
            registry.spec(arm).eta,
            eta,
            "REV4 Appendix C",
        )
        _check(
            checks,
            f"trains.{arm}",
            tuple(registry.spec(arm).trains),
            EXPECTED_TRAINS[arm],
            "REV4 §6.7",
        )
    for contrast in confirmatory_contrasts(4):
        for member in (contrast["minuend"], contrast["subtrahend"]):
            # C4 compares F with its control arm F beta, so a contrast member
            # may be a registered control rather than a condition.
            _check(
                checks,
                f"confirmatory.{contrast['id']}.{member}",
                member in registry.arms,
                True,
                "REV4 §5.3",
            )

    # frozen input files carry the declared plasticity, sensory and decoder
    # constants; a changed file is a changed protocol constant.
    inputs = {name: _resolve(path) for name, path in campaign.frozen_inputs.items()}
    plasticity = load_yaml(inputs["plasticity"])
    body = dict(plasticity["plasticity"])
    _check(
        checks,
        "plasticity.eta",
        float(body["eta"]),
        DECLARED["eta_plastic"],
        "configs/plasticity_banc.yaml / REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.control_eta",
        float(body["control_eta"]),
        DECLARED["eta_identity"],
        "REV4 §3.8",
    )
    bounds = dict(body["bounds"])
    _check(
        checks,
        "plasticity.bounds",
        (float(bounds["lower_factor"]), float(bounds["upper_factor"])),
        DECLARED["weight_bounds"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.max_abs_update_pa",
        float(bounds["max_abs_update_pa"]),
        DECLARED["max_abs_update_pa"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.traces.tau_e_ms",
        float(body["traces"]["tau_e_ms"]),
        DECLARED["tau_e_ms"],
        "REV4 Appendix C",
    )
    modulation = dict(plasticity["modulation"])
    _check(
        checks,
        "modulation.gain",
        float(modulation["gain"]),
        DECLARED["modulation_gain"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "modulation.decay_tau_ms",
        float(modulation["decay_tau_ms"]),
        DECLARED["modulation_tau_ms"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "modulation.clip_abs",
        (
            -float(modulation["clip_abs"]),
            float(modulation["clip_abs"]),
        ),
        DECLARED["modulation_clip"],
        "REV4 Appendix C",
    )

    mapping = load_yaml(inputs["sensory_mapping"])
    feature_currents = {
        float(payload.get("current_pa", 0.0))
        for payload in mapping["features"].values()
    }
    _check(
        checks,
        "sensory.current_pa",
        feature_currents,
        {DECLARED["sensory_current_pa"]},
        "REV4 Appendix C",
    )
    _check(
        checks,
        "sensory.n_features",
        len(mapping["features"]),
        7,
        "REV4 §6.6",
    )

    decoder = dict(load_yaml(inputs["motor_decoder"])["decoder"])
    _check(checks, "decoder.window_ms", float(decoder["window_ms"]), DECLARED["decoder_window_ms"], "REV4 Appendix C")
    _check(
        checks,
        "decoder.min_active_neurons",
        int(decoder["min_active_neurons"]),
        DECLARED["decoder_min_active_neurons"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.min_spikes",
        int(decoder["min_spikes"]),
        DECLARED["decoder_min_spikes"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.activation_threshold",
        float(decoder["activation_threshold"]),
        DECLARED["decoder_activation"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.release_threshold",
        float(decoder["release_threshold"]),
        DECLARED["decoder_release"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.priority",
        tuple(decoder["priority"]),
        ("LEFT", "RIGHT", "JUMP"),
        "REV4 Appendix C",
    )

    # seed ranges must remain disjoint and cover the primary design (the
    # loader already enforces this; the report restates it for the record).
    _check(
        checks,
        "seeds.disjoint",
        not (
            set(campaign.campaign_seeds) & set(campaign.training_seeds)
        )
        and not (set(campaign.campaign_seeds) & set(campaign.pilot_seeds))
        and not (set(campaign.training_seeds) & set(campaign.pilot_seeds)),
        True,
        "REV4 §6.3 / §6.7",
    )
    _check(
        checks,
        "seeds.campaign_count",
        len(campaign.campaign_seeds) >= campaign.n_seeds_primary,
        True,
        "REV4 §7.1",
    )

    failed = [entry for entry in checks if not entry["pass"]]
    report = {
        "protocol": identity,
        "approval": approval_status(protocol_path),
        "randomization_deviation": randomization_deviation(),
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failures": failed,
        "conforms": not failed,
        "n_seeds_selected": campaign.n_seeds_selected,
        "design_resolved": campaign.n_seeds_selected is not None,
        "note": (
            "conformance to declared constants is not scientific validity and "
            "is not an authorisation to execute"
        ),
    }
    if strict and failed:
        names = ", ".join(entry["name"] for entry in failed)
        raise CampaignProtocolError(
            "the campaign configuration disagrees with REV4 at: " + names
        )
    return report


def describe() -> dict:
    return {
        "protocol": protocol_identity(),
        "approval": approval_status(),
        "declared": dict(DECLARED),
        "expected_arms": list(ARMS_ACTIVE),
        "master_seed": MASTER_SEED,
    }


__all__ = [
    "AMENDMENT_ID",
    "AMENDMENT_PATH",
    "CAMPAIGN_SUMMARY",
    "CampaignNotAuthorized",
    "CampaignProtocolError",
    "DECISION_ITEM_IDS",
    "DECLARED",
    "EXPECTED_CONDITIONS",
    "EXPECTED_CONTROLS",
    "EXPECTED_EXPLORATORY",
    "OWNER_APPROVAL_RECORD",
    "OWNER_DECISION_D2_RECORD",
    "OWNER_DECISION_D3_RECORD",
    "PILOT1_G3_SCOPE",
    "PILOT2C_G3_SCOPE",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "approval_status",
    "assert_campaign_authorized",
    "assert_stage_authorized",
    "describe",
    "g3_applicability",
    "pilot2c_applicability",
    "protocol_identity",
    "randomization_deviation",
    "stage_authorization",
    "validate_campaign",
]
