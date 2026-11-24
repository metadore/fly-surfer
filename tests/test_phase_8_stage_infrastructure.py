"""Focused synthetic tests for the Phase 8 stage harnesses (REV4 §10).

Every test here is construction-only. It uses synthetic episode rows, a fake
memory preflight, a temporary directory and, where a baseline is needed, a
two-file synthetic integrity baseline. No game episode is executed, no training
run is started, no certified graph is loaded, no BANC-scale work happens and
nothing is written under the Phase 8 results root. These are infrastructure
tests; they are not experimental evidence.

Covered: shared stage plumbing, Pilot 1, training orchestration, the production
composition root, Pilot 2 dispersion, the information adapter, the report and
freeze stage, and the unified stage router.
"""

from __future__ import annotations

import hashlib
import json
from statistics import stdev

import pytest

from experiments.phase_8.campaign.protocol import CampaignNotAuthorized
from experiments.phase_8.config import MemoryGateError, PROJECT_ROOT, load_phase8_config
from experiments.phase_8.stages import common, composition, information, pilot1, pilot2
from experiments.phase_8.stages import reporting, run_stage, training_stage
from experiments.phase_8.training.errors import (
    DesignUnresolvedError,
    TrainingNotAuthorized,
)

MASTER = 20261116
SHA = "a" * 64
SYNTHETIC = {"evidence_kind": "synthetic_fixture", "not_experimental": True}

ROLES = {
    "A": "reference",
    "B": "condition",
    "C": "condition",
    "D": "condition",
    "E": "condition",
    "F": "condition",
    "A_prime": "control",
    "C_prime": "control",
    "F_beta": "control",
    "F_init": "control",
    "E_full": "exploratory",
    "floor": "floor",
}


@pytest.fixture(scope="module")
def config():
    return load_phase8_config()


def fake_preflight(gate_gb: float) -> dict:
    return {
        "available_gb": 999.0,
        "gate_gb": float(gate_gb),
        "passed": True,
        "reason": "synthetic preflight for infrastructure tests",
    }


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_row(
    arm: str,
    seed: int,
    episode: int = 0,
    *,
    steps: int = 100,
    actions: dict | None = None,
    classes: dict | None = None,
    reward: float = 0.01,
    motor_spikes: int = 0,
    notes: dict | None = None,
) -> dict:
    """One schema-valid synthetic episode row."""
    counts = dict(actions) if actions is not None else {"NO_ACTION": int(steps)}
    total = sum(counts.values())
    assert total == steps
    row = {
        "schema_version": 1,
        "condition": arm,
        "role": ROLES[arm],
        "seed": int(seed),
        "episode": int(episode),
        "environment_seed": int(seed) * 10 + int(episode),
        "training": False,
        "steps": int(steps),
        "observed_updates": int(steps),
        "survival_score": float(min(int(steps), 900)),
        "max_game_updates": 900,
        "total_reward": float(reward),
        "terminated": True,
        "truncated": False,
        "termination_reason": None,
        "action_counts": counts,
        "no_action_fraction": counts.get("NO_ACTION", 0) / int(steps),
        "motor_spikes": int(motor_spikes),
        "spike_sha256": None,
        "action_sha256": SHA,
        "weights_before": SHA,
        "weights_after": SHA,
        "config_hashes": {"environment": SHA, "campaign": SHA, "conditions": SHA},
        "input_hashes": {"fixture": SHA},
        "started_at": "2026-11-17T00:00:00Z",
        "wall_time_s": 0.01,
    }
    if classes is not None:
        row["decision_classes"] = dict(classes)
    if notes is not None:
        row["notes"] = dict(notes)
    return row


def synthetic_runner(arm, seed, episode, context):
    return make_row(
        arm,
        seed,
        episode,
        notes={"evidence_kind": "synthetic_fixture"},
    )


# ---------------------------------------------------------------------------
# shared plumbing
# ---------------------------------------------------------------------------


def test_stage_envelope_is_construction_only():
    record = common.stage_envelope("pilot1")
    assert record["record_kind"] == "phase_8_stage_record"
    assert record["executed"] is False
    assert record["experimental_evidence"] is False
    assert "not experimental evidence" in record["note"]
    executed = common.stage_envelope("pilot1", executed=True, evidence_kind="pilot")
    assert executed["experimental_evidence"] is True


def test_stage_envelope_rejects_unknown_stage():
    with pytest.raises(common.StageConfigurationError):
        common.stage_envelope("nonsense")


def test_write_json_is_write_once(tmp_path):
    target = tmp_path / "record.json"
    common.write_json(target, {"a": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    with pytest.raises(FileExistsError):
        common.write_json(target, {"a": 2})


def test_canonical_json_is_sorted_and_compact():
    assert common.canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


# ---------------------------------------------------------------------------
# pilot 1
# ---------------------------------------------------------------------------


def test_pilot1_plan_is_arm_a_only(config):
    plan = pilot1.pilot1_plan(config)
    payload = plan.as_dict(MASTER)
    assert payload["n_entries"] == 9
    assert payload["arms"] == ["A"]
    assert payload["seeds"] == [9001, 9002, 9003]
    assert {entry["arm"] for entry in payload["entries"]} == {"A"}
    assert payload["estimates_contrasts"] is False
    assert payload["hypothesis_tests"] == []


def test_pilot1_description_is_executable_after_d2(config):
    record = pilot1.describe_pilot1(config, preflight=fake_preflight)
    assert record["executable"] is True
    assert record["contrasts_estimated"] == []
    assert record["frozen_constants"]["episodes_per_seed"] == 3
    assert not any(item.startswith("B7") for item in record["execution_blockers"])
    exemption = record["authorization"]["exemption"]
    assert exemption["applied"] is True
    assert exemption["scope"]["arms"] == ["A"]
    assert exemption["scope"]["seeds"] == [9001, 9002, 9003]


def test_run_pilot1_stops_at_the_memory_gate_and_creates_nothing(config, tmp_path):
    def below_gate(gate_gb: float) -> dict:
        return {
            "available_gb": 1.0,
            "gate_gb": float(gate_gb),
            "passed": False,
            "reason": "synthetic low-memory fixture",
        }

    base = tmp_path / "pilot1"
    with pytest.raises(MemoryGateError):
        pilot1.run_pilot1(
            config,
            base_dir=base,
            episode_runner=synthetic_runner,
            preflight=below_gate,
            input_hashes={"fixture": {"path": "fixture.bin", "sha256": SHA}},
        )
    assert not base.exists()


def test_synthetic_driver_refuses_the_real_results_root(config):
    real_root = PROJECT_ROOT / config.campaign.results_root
    with pytest.raises(common.StageRefusal):
        pilot1.run_pilot1(
            config,
            base_dir=real_root,
            run_id="must_not_exist",
            episode_runner=synthetic_runner,
            preflight=fake_preflight,
            synthetic_fixture=True,
            input_hashes={"fixture": {"path": "fixture.bin", "sha256": SHA}},
        )
    assert not (real_root / "must_not_exist").exists()


def test_synthetic_driver_stamps_rows_and_labels_the_run(config, tmp_path):
    summary = pilot1.run_pilot1(
        config,
        base_dir=tmp_path / "runs",
        run_id="pilot1_synthetic",
        episode_runner=synthetic_runner,
        preflight=fake_preflight,
        synthetic_fixture=True,
        input_hashes={"fixture": {"path": "fixture.bin", "sha256": SHA}},
    )
    assert summary["evidence_kind"] == "synthetic_fixture"
    assert summary["experimental_evidence"] is False
    assert summary["rows_stored"] == 9
    assert summary["planned"] == 9
    assert summary["complete"] is True
    assert summary["estimates_contrasts"] is False
    run_dir = tmp_path / "runs" / "pilot1_synthetic"
    rows = [
        json.loads(line)
        for line in (run_dir / config.campaign.episode_store_name)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(rows) == 9
    assert all(row["notes"]["evidence_kind"] == "synthetic_fixture" for row in rows)


# ---------------------------------------------------------------------------
# training orchestration
# ---------------------------------------------------------------------------


def test_training_status_declares_b3_to_b6(config):
    record = training_stage.describe_training_stage(config)
    assert record["training_performed"] is False
    assert record["artifacts_written"] == 0
    # D4 declares B3-B6; the remaining execution blockers are the unresolved
    # design (B2) and the recorded G3 deviation (B7).
    assert [item[:2] for item in record["execution_blockers"]] == ["B2", "B7"]
    assert record["authorization"]["training_authorized"] is False
    declarations = record["declarations"]
    assert declarations["applicable"] is True
    assert set(declarations["declared"]) == {"B3", "B4", "B5", "B6"}
    pairing = declarations["seed_pairing"]["pairing"]
    assert pairing["F:9001"] == pairing["F_beta:9001"]
    assert len({pairing[f"F:{seed}"] for seed in (9001, 9002, 9003)}) == 3
    assert declarations["environment_seed_schedule"]["namespace"] == (
        "phase_8/training/B4/v1"
    )
    assert declarations["checkpoint_policy"]["cadence"].startswith("one checkpoint")
    assert declarations["bit_identical_resume"]["claimed"] is False


def test_training_plan_refuses_unresolved_design(config):
    with pytest.raises(DesignUnresolvedError):
        training_stage.plan_training_stage(config, pairing={("F", 1): 1001})


def test_training_execution_refuses_authorization_first(config):
    with pytest.raises(TrainingNotAuthorized):
        training_stage.execute_training_stage(
            config,
            pairing={("F", 1): 1001},
            environment_seed_for_episode=None,
        )


def test_load_pairing_accepts_flat_and_nested(tmp_path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"F:1": 1001, "F_beta:2": 1002}), encoding="utf-8")
    assert training_stage.load_pairing(flat) == {("F", 1): 1001, ("F_beta", 2): 1002}

    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"E": {"3": 1003}}), encoding="utf-8")
    assert training_stage.load_pairing(nested) == {("E", 3): 1003}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"Z:1": 1001},
        {"F": 1001},
        {"F:notanint": 1001},
    ],
)
def test_load_pairing_rejects_bad_input(tmp_path, payload):
    source = tmp_path / "pairing.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(common.StageConfigurationError):
        training_stage.load_pairing(source)


def test_load_pairing_rejects_invalid_json(tmp_path):
    source = tmp_path / "broken.json"
    source.write_text("{not json", encoding="utf-8")
    with pytest.raises(common.StageConfigurationError):
        training_stage.load_pairing(source)


# ---------------------------------------------------------------------------
# production composition root
# ---------------------------------------------------------------------------


def test_composition_partitions_all_twelve_arms(config):
    verification = composition.verify_arm_routes(config)
    assert verification["passed"] is True
    assert verification["n_arms"] == 12
    assert len(set(verification["arms"])) == 12
    assert all(item["pass"] for item in verification["checks"])


def test_composition_control_semantics(config):
    routes = {route.arm: route for route in composition.arm_routes(config)}
    for arm in ("A_prime", "C_prime"):
        assert routes[arm].stepper_kind == "plastic"
        assert routes[arm].eta == 0.0
        assert routes[arm].mirror is not None
    assert {arm for arm, route in routes.items() if route.requires_structure} == {
        "C",
        "D",
        "C_prime",
    }
    for arm in ("F", "F_beta", "F_init"):
        assert routes[arm].needs_readout is True
    for arm in ("E", "E_full"):
        assert routes[arm].kind == "conventional"
        assert routes[arm].needs_agent is True
    for arm in ("B", "D"):
        assert routes[arm].eta == 0.5
    assert routes["floor"].kind == "floor"


def test_composition_preflight_is_not_executable(config):
    record = composition.preflight_report(config, preflight=fake_preflight)
    assert record["execution_ready"] is False
    assert record["execution_blockers"]
    assert any(item.startswith("B7") for item in record["execution_blockers"])
    assert any(item.startswith("B2") for item in record["execution_blockers"])
    assert record["certified_graphs"]["fallback_to_biological_graph"] is False
    assert all(
        covered is False for covered in record["pilot_seed_graphs"]["covered"].values()
    )


def test_campaign_start_and_resume_refuse(config, tmp_path):
    with pytest.raises(CampaignNotAuthorized):
        composition.start_campaign(config, tmp_path / "campaign", "c1")
    with pytest.raises(CampaignNotAuthorized):
        composition.resume_campaign(config, tmp_path / "campaign")
    assert not (tmp_path / "campaign").exists()


# ---------------------------------------------------------------------------
# pilot 2
# ---------------------------------------------------------------------------


PILOT2_SCORES = {
    "A": {9001: 100, 9002: 200, 9003: 300},
    "B": {9001: 100, 9002: 200, 9003: 300},
    "C": {9001: 50, 9002: 100, 9003: 150},
    "F": {9001: 400, 9002: 600, 9003: 500},
    "F_beta": {9001: 200, 9002: 200, 9003: 200},
}


def pilot2_rows(scores: dict | None = None) -> list[dict]:
    scores = scores or PILOT2_SCORES
    rows: list[dict] = []
    for seed in (9001, 9002, 9003):
        for episode in range(3):
            for arm, values in scores.items():
                rows.append(
                    make_row(
                        arm,
                        seed,
                        episode,
                        steps=values[seed],
                        notes=dict(SYNTHETIC),
                    )
                )
            rows.append(
                make_row(
                    "A_prime",
                    seed,
                    episode,
                    steps=scores["A"][seed],
                    notes=dict(SYNTHETIC),
                )
            )
            rows.append(
                make_row(
                    "C_prime",
                    seed,
                    episode,
                    steps=scores["C"][seed],
                    notes=dict(SYNTHETIC),
                )
            )
    return rows


def test_pilot2_plan_is_63_entries(config):
    plan = pilot2.pilot2_plan(config)
    payload = plan.as_dict(MASTER)
    assert payload["n_entries"] == 63
    assert payload["arms"] == list(pilot2.PILOT2_ARMS)
    assert payload["seeds"] == [9001, 9002, 9003]
    assert payload["estimates_contrasts"] is False


def test_upper_confidence_factor_closed_form():
    assert pilot2.upper_confidence_factor(2, 0.80) == pytest.approx(
        2.1169364935501847
    )
    assert pilot2.upper_confidence_factor(2, 0.95) == pytest.approx(
        4.4153964427017955
    )
    with pytest.raises(common.StageConfigurationError):
        pilot2.upper_confidence_factor(0, 0.80)
    with pytest.raises(common.StageConfigurationError):
        pilot2.upper_confidence_factor(2, 1.5)


def test_pilot2_readiness_reports_structural_blockers(config):
    readiness = pilot2.pilot2_readiness(config, preflight=fake_preflight)
    assert readiness["ready"] is False
    joined = " ".join(readiness["blockers"])
    assert "P2-G" in joined
    assert "P2-A" in joined
    assert readiness["training_artifacts"]["loader_accepts_seeds"] == []
    assert all(covered is False for covered in readiness["certified_graphs"]["pilot_seed_coverage"].values())


def test_pilot2_description_is_not_executable(config):
    record = pilot2.describe_pilot2(config, preflight=fake_preflight)
    assert record["executable"] is False
    assert record["plan"]["n_entries"] == 63
    assert record["contrasts_estimated"] == []
    assert record["hypothesis_tests"] == []


def test_pilot2_dispersion_known_values(config):
    record = pilot2.evaluate_dispersion(pilot2_rows(), config)
    assert record["evidence_kind"] == "synthetic_fixture"
    assert record["experimental_evidence"] is False
    assert record["complete"] is True
    assert record["estimates_contrasts"] is False
    assert record["hypothesis_tests"] == []

    by_id = {item["id"]: item for item in record["contrasts"]}
    assert all(item["status"] == "evaluable" for item in by_id.values())
    assert by_id["C1"]["paired_sd"] == pytest.approx(stdev([300, 400, 200]))
    assert by_id["C2"]["paired_sd"] == pytest.approx(0.0)
    assert by_id["C3"]["paired_sd"] == pytest.approx(stdev([50, 100, 150]))
    assert by_id["C4"]["paired_sd"] == pytest.approx(stdev([200, 400, 300]))
    assert by_id["C1"]["is_hypothesis_test"] is False

    assert record["sigma_max"] == pytest.approx(100.0)
    assert record["sigma_max_contrast"] == "C1"
    assert record["ucl80_sigma_max"] == pytest.approx(
        100.0 * pilot2.upper_confidence_factor(2, 0.80)
    )

    assert record["identity"]["A_prime"]["passed"] is True
    assert record["identity"]["C_prime"]["passed"] is True
    assert record["f_beta_constant_action"]["constant_everywhere"] is True

    u7 = record["u7"]
    assert u7["decision_recorded"] is False
    assert u7["recorded_n_seeds_selected"] is None
    assert u7["indication"] == "escalate_above_primary_N"


def test_pilot2_small_sigma_indicates_fallback(config):
    scores = {
        "A": {9001: 100, 9002: 200, 9003: 300},
        "B": {9001: 100, 9002: 200, 9003: 300},
        "C": {9001: 100, 9002: 200, 9003: 300},
        "F": {9001: 101, 9002: 202, 9003: 303},
        "F_beta": {9001: 100, 9002: 200, 9003: 300},
    }
    record = pilot2.evaluate_dispersion(pilot2_rows(scores), config)
    assert record["sigma_max"] == pytest.approx(stdev([1, 2, 3]))
    assert record["u7"]["indication"] == "fallback_N_may_be_defensible"


def test_pilot2_missing_rows_are_not_a_pass(config):
    rows = pilot2_rows()
    rows = [row for row in rows if not (row["condition"] == "F" and row["seed"] == 9002 and row["episode"] == 1)]
    record = pilot2.evaluate_dispersion(rows, config)
    c1 = next(item for item in record["contrasts"] if item["id"] == "C1")
    assert c1["status"] == "not_evaluable"
    assert c1["paired_sd"] is None
    assert record["complete"] is False


def test_pilot2_rejects_campaign_seed_rows(config):
    rows = pilot2_rows()
    rows.append(make_row("A", 1, 0, steps=100, notes=dict(SYNTHETIC)))
    with pytest.raises(common.StageConfigurationError):
        pilot2.evaluate_dispersion(rows, config)


def test_pilot2_rejects_undeclared_arm(config):
    rows = pilot2_rows()
    rows.append(make_row("D", 9001, 0, steps=100, notes=dict(SYNTHETIC)))
    with pytest.raises(common.StageConfigurationError):
        pilot2.evaluate_dispersion(rows, config)


def test_run_pilot2_refuses(config, tmp_path):
    with pytest.raises(CampaignNotAuthorized):
        pilot2.run_pilot2(
            config,
            base_dir=tmp_path / "pilot2",
            episode_runner=synthetic_runner,
            preflight=fake_preflight,
        )
    assert not (tmp_path / "pilot2").exists()


# ---------------------------------------------------------------------------
# information adapter
# ---------------------------------------------------------------------------


def information_rows() -> list[dict]:
    rows = []
    for seed in (1, 2):
        rows.append(
            make_row(
                "A",
                seed,
                0,
                steps=4,
                actions={"LEFT": 2, "RIGHT": 2},
                classes={"motor-driven": 2, "bias-driven": 2},
                notes=dict(SYNTHETIC),
            )
        )
    rows.append(
        make_row(
            "F",
            1,
            0,
            steps=4,
            actions={"JUMP": 4},
            classes={"bias-driven (incidental)": 4},
            notes=dict(SYNTHETIC),
        )
    )
    return rows


def test_information_catalogue_marks_mi_unavailable():
    catalogue = information.describe_information_analyses()
    mi = next(
        item
        for item in catalogue["outcomes"]
        if "mutual information" in item["outcome"]
    )
    assert mi["available_from_store"] is False
    assert "in a new substrate" in mi["label"]
    assert catalogue["labels"]["confirmatory"] is False
    assert catalogue["phase_6"]["artefacts_untouched"] is True


def test_information_is_descriptive_only(config):
    record = information.analyse_information(information_rows(), config, episodes=3)
    assert record["descriptive"] is True
    assert record["exploratory"] is True
    assert record["confirmatory"] is False
    assert record["hypothesis_tests"] == []
    assert record["p_values"] is None
    assert record["phase_6"]["artefacts_untouched"] is True
    assert record["phase_6"]["conclusion_can_change"] is False
    assert record["feature_action_mutual_information"]["available"] is False
    assert record["evidence_kind"] == "synthetic_fixture"
    assert record["experimental_evidence"] is False


def test_information_entropy_values(config):
    record = information.analyse_information(information_rows(), config)
    arm_a = record["per_arm"]["A"]
    assert arm_a["event_class_entropy_bits"]["pooled"] == pytest.approx(1.0)
    assert arm_a["decoder_state_entropy_bits"]["pooled"] == pytest.approx(1.0)
    assert arm_a["no_action_fraction_pooled"] == pytest.approx(0.0)
    arm_f = record["per_arm"]["F"]
    assert arm_f["event_class_entropy_bits"]["pooled"] == pytest.approx(0.0)
    assert arm_f["decoder_state_entropy_bits"]["pooled"] == pytest.approx(0.0)


def test_information_reports_missing_episodes(config):
    record = information.analyse_information(information_rows(), config, episodes=3)
    seed_entry = record["per_arm"]["A"]["per_seed"][0]
    assert seed_entry["episodes_stored"] == 1
    assert seed_entry["episodes_missing"] == [1, 2]


def test_information_rejects_unexpected_evidence_label(config):
    rows = information_rows()
    rows[0] = dict(rows[0])
    rows[0]["notes"] = {"evidence_kind": "pilot"}
    with pytest.raises(common.StageConfigurationError):
        information.analyse_information(rows, config)


def test_information_rejects_empty_rows(config):
    with pytest.raises(common.StageConfigurationError):
        information.analyse_information([], config)


# ---------------------------------------------------------------------------
# report and freeze
# ---------------------------------------------------------------------------


def test_forbidden_scanner_finds_each_statement():
    clean = reporting.scan_for_forbidden_statements("A neutral report body.")
    assert clean["clean"] is True
    assert clean["hits"] == []

    body = "The connectome learned the task.\nplasticity improved performance."
    scan = reporting.scan_for_forbidden_statements(body)
    assert scan["clean"] is False
    assert {hit["id"] for hit in scan["hits"]} == {"FS1", "FS2"}
    assert all(hit["line"] in (1, 2) for hit in scan["hits"])

    with pytest.raises(common.StageConfigurationError):
        reporting.scan_for_forbidden_statements(None)


def write_baseline(tmp_path, entries: dict[str, str]) -> tuple:
    root = tmp_path / "repo"
    root.mkdir()
    for relative, text in entries.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                relative: {"sha256": sha_of(text)}
                for relative, text in entries.items()
            }
        ),
        encoding="utf-8",
    )
    return root, baseline


def test_integrity_passes_with_matching_non_readme(tmp_path):
    root, baseline = write_baseline(
        tmp_path, {"README.md": "readme", "configs/a.yaml": "alpha"}
    )
    report = reporting.check_integrity(baseline, root=root)
    assert report["checked"] is True
    assert report["protected_total"] == 2
    assert report["matching"] == 2
    assert report["pass"] is True
    assert report["non_readme_failures"] == []


def test_integrity_only_readme_drift_does_not_block(tmp_path):
    root, baseline = write_baseline(
        tmp_path, {"README.md": "readme", "configs/a.yaml": "alpha"}
    )
    (root / "README.md").write_text("changed readme", encoding="utf-8")
    report = reporting.check_integrity(baseline, root=root)
    assert report["pass"] is True
    assert report["readme_failure"]["path"] == "README.md"
    assert report["non_readme_failures"] == []


def test_integrity_non_readme_failure_blocks(tmp_path):
    root, baseline = write_baseline(
        tmp_path, {"README.md": "readme", "configs/a.yaml": "alpha"}
    )
    (root / "configs/a.yaml").write_text("tampered", encoding="utf-8")
    report = reporting.check_integrity(baseline, root=root)
    assert report["pass"] is False
    assert [item["path"] for item in report["non_readme_failures"]] == ["configs/a.yaml"]


def test_report_record_is_not_publishable_without_evidence(config, tmp_path):
    record = reporting.build_final_report(tmp_path / "run", config)
    assert record["publishable"] is False
    assert record["publish_blockers"]
    assert record["integrity"]["checked"] is False
    assert record["forbidden_scan"]["clean"] is None
    assert len(record["limitations"]) == 33
    assert record["readout_claim"]["claim_allowed"] is False
    assert record["phase_6"]["result_unchanged"] is True


def test_limitations_are_complete_and_unique():
    ids = [item["id"] for item in reporting.LIMITATIONS]
    assert ids == [f"L{index}" for index in range(1, 34)]
    assert len(set(ids)) == 33


def test_report_writer_refuses_unpublishable(config, tmp_path):
    record = reporting.build_final_report(tmp_path / "run", config)
    with pytest.raises(common.StageRefusal):
        reporting.write_final_report(tmp_path / "report.json", record)
    assert not (tmp_path / "report.json").exists()


def test_freeze_record_uses_report_integrity(config, tmp_path):
    empty = reporting.build_final_report(tmp_path / "run", config)
    record = reporting.freeze_record(tmp_path / "run", config, report=empty)
    assert record["eligible_to_freeze"] is False
    assert record["frozen"] is False
    assert record["blockers"]
    with pytest.raises(common.StageRefusal):
        reporting.write_freeze_record(tmp_path / "freeze.json", record)
    assert not (tmp_path / "freeze.json").exists()

    eligible_report = {
        "publishable": True,
        "publish_blockers": [],
        "integrity": {"checked": True, "pass": True},
    }
    eligible = reporting.freeze_record(
        tmp_path / "run", config, report=eligible_report
    )
    assert eligible["eligible_to_freeze"] is True
    assert eligible["frozen"] is False
    written = reporting.write_freeze_record(tmp_path / "freeze.json", eligible)
    assert written.is_file()


# ---------------------------------------------------------------------------
# unified stage router
# ---------------------------------------------------------------------------


def test_run_stage_lists_known_stages(capsys):
    assert run_stage.main(["--list"]) == 0
    output = capsys.readouterr().out
    for name in run_stage.STAGES:
        assert name in output


def test_run_stage_rejects_unknown_and_empty():
    assert run_stage.main(["unknown"]) == run_stage.EXIT_USAGE
    assert run_stage.main([]) == run_stage.EXIT_USAGE


def test_run_stage_dispatches_pilot1_describe(capsys):
    assert run_stage.main(["pilot1", "--describe"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stage"] == "pilot1"
    assert payload["authorization"]["exemption"]["applied"] is True
    assert payload["contrasts_estimated"] == []


def test_run_stage_dispatches_report_describe(capsys):
    assert run_stage.main(["report", "--describe"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stage"] == "report"
    assert payload["publishable"] is False
