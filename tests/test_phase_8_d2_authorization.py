"""Synthetic tests for D2: G3 is not applicable to Pilot 1 only.

No episode runs here. The tests exercise the authorization layer with the
recorded D1/D2 files, temporary altered copies, and a fake memory preflight.
They prove that the Pilot 1 exemption is exact: every other stage and every
other grid still receives the unchanged B7 refusal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.phase_8.campaign.protocol import (
    OWNER_APPROVAL_RECORD,
    OWNER_DECISION_D2_RECORD,
    PROTOCOL_PATH,
    CampaignNotAuthorized,
    approval_status,
    assert_campaign_authorized,
    assert_stage_authorized,
    g3_applicability,
    stage_authorization,
)
from experiments.phase_8.conditions.base import requirements_for
from experiments.phase_8.config import MemoryGateError, load_phase8_config
from experiments.phase_8.stages import composition, pilot1, pilot2
from experiments.phase_8.stages.common import PilotPlan, authorization_snapshot
from experiments.phase_8.training.gate import training_authorization_status

REV4_SHA = "e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c"
PILOT_SEEDS = (9001, 9002, 9003)
SHA = "a" * 64
FIXTURE_HASHES = {"fixture": {"path": "fixture.bin", "sha256": SHA}}


@pytest.fixture(scope="module")
def config():
    return load_phase8_config()


def fake_preflight(gate_gb: float) -> dict:
    return {
        "available_gb": 999.0,
        "gate_gb": float(gate_gb),
        "passed": True,
        "reason": "synthetic preflight for authorization tests",
    }


def low_memory(gate_gb: float) -> dict:
    return {
        "available_gb": 1.0,
        "gate_gb": float(gate_gb),
        "passed": False,
        "reason": "synthetic low-memory fixture",
    }


def must_not_run(*args, **kwargs):
    raise AssertionError("no episode may run in an authorization test")


def read_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_record(directory: Path, name: str, payload: dict) -> Path:
    target = directory / name
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def forged_plan(arms: tuple[str, ...], seeds: tuple[int, ...] = PILOT_SEEDS) -> PilotPlan:
    return PilotPlan(
        stage="pilot1",
        rev4_step="10.3",
        arms=arms,
        seeds=seeds,
        episodes=3,
        establishes="nothing: forged plan for an authorization test",
        does_not_establish="nothing",
    )


# ---------------------------------------------------------------------------
# recognised decisions
# ---------------------------------------------------------------------------


def test_d1_approval_is_recognised():
    status = approval_status()
    assert status["approved"] is True
    assert status["decision_status"] == "APPROVED - recorded owner decision D1"
    assert status["approval_record"]["approval_id"] == "D1"
    assert status["protocol_sha256"] == REV4_SHA
    assert status["protocol_matches_expected"] is True
    assert status["document_authorises_execution"] is False


def test_d2_decision_is_recognised():
    decision = g3_applicability()
    assert decision["present"] is True
    assert decision["valid"] is True
    assert decision["bound_to_rev4"] is True
    assert decision["pilot1_exempt"] is True
    assert decision["approval_id"] == "D2"
    assert decision["approval_date"] == "2026-11-20"
    assert decision["document_matches_rev4"] is True
    scope = decision["scope"]
    assert scope["arms"] == ["A"]
    assert scope["seeds"] == list(PILOT_SEEDS)
    assert scope["episodes_per_seed"] == 3
    assert scope["n_episodes"] == 9
    assert scope["accepts_g3_deviation"] is False
    assert scope["weakens_graph_certification"] is False
    assert scope["parameter_modifications_authorised"] is False


# ---------------------------------------------------------------------------
# exact Pilot 1 passage, every other stage refused
# ---------------------------------------------------------------------------


def test_pilot1_passes_the_g3_applicability_check(config):
    plan = pilot1.pilot1_plan(config)
    report = stage_authorization("pilot1", config=config, plan=plan)
    assert report["authorized"] is True
    assert report["blockers"] == []
    assert report["exemption"]["applied"] is True
    assert report["exemption"]["approval_id"] == "D2"
    assert report["randomization_deviation"]["status"] == "deviation_recorded"
    assert report["randomization_deviation"]["gate_weakened"] is False
    assert_stage_authorized("pilot1", config=config, plan=plan)


def test_pilot1_still_fails_below_the_memory_gate(config, tmp_path):
    base = tmp_path / "low_memory"
    with pytest.raises(MemoryGateError):
        pilot1.run_pilot1(
            config,
            base_dir=base,
            episode_runner=must_not_run,
            preflight=low_memory,
            input_hashes=FIXTURE_HASHES,
        )
    assert not base.exists()


def test_conditions_c_and_d_remain_blocked(config):
    assert requirements_for("C").requires_structure is True
    assert requirements_for("D").requires_structure is True
    for arms in (("C",), ("D",), ("A", "C"), ("C_prime",)):
        report = stage_authorization("pilot1", config=config, plan=forged_plan(arms))
        assert report["authorized"] is False
        assert report["exemption"]["applied"] is False
        assert any("D2 Pilot 1 scope" in item for item in report["blockers"])

    campaign_report = stage_authorization("campaign", config=config)
    assert campaign_report["authorized"] is False
    assert campaign_report["exemption"]["applied"] is False


def test_pilot2_remains_blocked(config, tmp_path):
    plan = pilot2.pilot2_plan(config)
    report = stage_authorization("pilot2", config=config, plan=plan)
    assert report["authorized"] is False
    assert report["exemption"]["applied"] is False
    assert any(item.startswith("B7") for item in report["blockers"])

    base = tmp_path / "pilot2"
    with pytest.raises(CampaignNotAuthorized, match="does not inherit"):
        pilot2.run_pilot2(
            config,
            base_dir=base,
            episode_runner=must_not_run,
            preflight=fake_preflight,
        )
    assert not base.exists()


def test_confirmatory_campaign_remains_blocked(config, tmp_path):
    with pytest.raises(CampaignNotAuthorized, match="G3"):
        assert_campaign_authorized()
    base = tmp_path / "campaign"
    with pytest.raises(CampaignNotAuthorized, match="G3"):
        composition.start_campaign(config, base, "c1")
    assert not base.exists()
    assert training_authorization_status()["training_authorized"] is False


# ---------------------------------------------------------------------------
# altered or invalid records
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"approval_id": "D3"}),
        lambda payload: payload["scope"].update({"accepts_g3_deviation": True}),
        lambda payload: payload["scope"].update({"weakens_graph_certification": True}),
        lambda payload: payload["scope"].update({"seeds": [9001, 9002, 9004]}),
        lambda payload: payload["scope"].update({"uses_randomized_graph": True}),
        lambda payload: payload["approved_document"].update({"sha256": "0" * 64}),
        lambda payload: payload.update({"record_kind": "owner_approval"}),
    ],
)
def test_altered_d2_records_are_rejected(config, tmp_path, mutation):
    payload = read_record(OWNER_DECISION_D2_RECORD)
    mutation(payload)
    altered = write_record(tmp_path, "D2.json", payload)
    report = stage_authorization(
        "pilot1",
        config=config,
        plan=pilot1.pilot1_plan(config),
        decision_record_path=altered,
    )
    assert report["authorized"] is False
    assert report["exemption"]["applied"] is False
    assert report["g3_applicability"]["pilot1_exempt"] is False
    assert any(item.startswith("B7") for item in report["blockers"])


def test_missing_d2_record_is_rejected(config, tmp_path):
    report = stage_authorization(
        "pilot1",
        config=config,
        plan=pilot1.pilot1_plan(config),
        decision_record_path=tmp_path / "absent.json",
    )
    assert report["authorized"] is False
    assert report["g3_applicability"]["present"] is False


def test_altered_or_missing_d1_is_rejected(config, tmp_path):
    payload = read_record(OWNER_APPROVAL_RECORD)
    payload["approved_document"]["sha256"] = "0" * 64
    altered = write_record(tmp_path, "D1.json", payload)
    for record in (altered, tmp_path / "absent.json"):
        report = stage_authorization(
            "pilot1",
            config=config,
            plan=pilot1.pilot1_plan(config),
            approval_record_path=record,
        )
        assert report["authorized"] is False
        assert report["approval"]["approved"] is False
        assert any(item.startswith("B1") for item in report["blockers"])


def test_changed_protocol_invalidates_both_decisions(config, tmp_path):
    altered = tmp_path / "REV4.md"
    altered.write_text(
        PROTOCOL_PATH.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    status = approval_status(protocol_path=altered)
    assert status["approved"] is False
    decision = g3_applicability(protocol_path=altered)
    assert decision["pilot1_exempt"] is False
    report = stage_authorization(
        "pilot1",
        config=config,
        plan=pilot1.pilot1_plan(config),
        protocol_path=altered,
    )
    assert report["authorized"] is False


# ---------------------------------------------------------------------------
# unrelated gates stay active
# ---------------------------------------------------------------------------


def test_no_unrelated_authorization_gate_is_bypassed(config):
    plan = pilot1.pilot1_plan(config)
    campaign_snapshot = authorization_snapshot()
    assert campaign_snapshot["authorized"] is False
    assert any(item.startswith("B7") for item in campaign_snapshot["blockers"])

    preflight = composition.preflight_report(config, preflight=fake_preflight)
    assert preflight["execution_ready"] is False
    assert any(item.startswith("B7") for item in preflight["execution_blockers"])

    for stage in ("pilot2", "campaign", "training", "information", "report"):
        report = stage_authorization(stage, config=config, plan=plan)
        assert report["authorized"] is False
        assert report["exemption"]["applied"] is False

    training = training_authorization_status()
    assert training["training_authorized"] is False
    assert any(item.startswith("B7") for item in training["blockers"])
