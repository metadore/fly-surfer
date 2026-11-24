"""Synthetic tests for Pilot 2-C (REV4 §10.8 as amended by D3).

Every episode here runs on the 32-node test network from
``test_phase_8_conditions`` through the existing controlled game. No BANC-scale
graph, no certified random graph and no trained artifact is loaded; the readouts
and artifact manifests are fixtures, not experimental artefacts. Rows produced
directly through :class:`Pilot2CEpisodeRunner` are labelled ``pilot`` exactly as
the production runner labels them; the only driver run in this file is the
``synthetic_fixture`` path, whose rows must be refused as experimental evidence.

Covered: the 54-entry grid and its certification, exact A/A' identity with the
P1-P19 report, the A' hard stop and the resumed-process refusal, F's frozen and
state-dependent readout, Fβ's provable state independence, motor silence,
plasticity attribution, provenance and manifest stage purpose, schema-valid
failure rows, the no-overwrite rule, pilot/campaign separation, the D3 gate's
exact scope and the A-2 pilot-scope loader refusals.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from environment import ControlledGameEnvironment, GameEnvironmentAdapter
from experiments.phase_8.campaign.protocol import stage_authorization
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.conditions import b_plastic, f_readout
from experiments.phase_8.controls import a_prime, f_beta
from experiments.phase_8.schema import validate_episode_row
from experiments.phase_8.seeds import environment_seed, seed_plan
from experiments.phase_8.stages import pilot2c
from experiments.phase_8.stages.common import (
    PilotPlan,
    StageConfigurationError,
    StageRefusal,
    drive_pilot,
    stage_root,
)
from experiments.phase_8.stages.pilot2c_runner import (
    PILOT2C_ARMS,
    PILOT2C_SEEDS,
    PILOT2C_STAGE_PURPOSE,
    Pilot2CEpisodeRunner,
)
from experiments.phase_8.store import ExistingResultError
from experiments.phase_8.training import (
    ArtifactCompatibilityError,
    TrainingConfigError,
    load_pilot_evaluation_artifacts,
    load_training_artifacts,
    validate_training_config,
)

from test_phase_8_conditions import (
    build_world,
    make_bundle,
    make_drive_clock,
    make_fixed_stepper,
    make_graph,
    make_plastic_stepper,
)
from test_phase_8_training_artifacts import write_fixture

MASTER = 20261116
UPDATES = 6
EPISODES = (0, 1, 2)
SHA = "a" * 64
MANIFEST_INPUT_HASHES = {
    "fixture_graph": {"path": "fixture_graph.npz", "sha256": SHA}
}


def small_config():
    config = load_phase8_config()
    campaign = replace(config.campaign, max_game_updates=UPDATES)
    return replace(config, campaign=campaign)


def fake_preflight(gate_gb: float) -> dict:
    return {
        "available_gb": 999.0,
        "gate_gb": float(gate_gb),
        "passed": True,
        "reason": "synthetic preflight for the Pilot 2-C tests",
    }


class ExplodingAdapter:
    """A real adapter whose first game update fails, to exercise error rows."""

    def __init__(self, inner):
        self._inner = inner
        self.game = inner.game

    def reset(self, seed=None):
        return self._inner.reset(seed)

    def step(self, decision):
        raise RuntimeError("synthetic adapter failure")


class SynthFactory:
    """Build a fresh 32-node bundle per arm; records every request.

    It mirrors the real factory's per-arm routing (fixed vs plastic stepper,
    readout decision source, zero hook) but never trains and never reads a
    certified graph.
    """

    def __init__(self, world, config, *, max_steps: int = UPDATES, fail_arm=None):
        self.world = world
        self.config = config
        self.max_steps = int(max_steps)
        self.fail_arm = fail_arm
        self.calls: list[dict] = []

    def input_hashes(self) -> dict[str, str]:
        return {
            name: hashlib.sha256(name.encode("utf-8")).hexdigest()
            for name in self.config.campaign.frozen_inputs
        }

    def floor_adapter(self) -> GameEnvironmentAdapter:
        return GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(
                max_steps=self.max_steps, render_mode=None
            )
        )

    def neural_components(
        self,
        arm,
        *,
        seed,
        episode,
        environment_seed,
        master_seed,
        training=False,
    ):
        assert not training, "Pilot 2-C never requests a training episode"
        self.calls.append(
            {
                "arm": arm,
                "seed": int(seed),
                "episode": int(episode),
                "environment_seed": int(environment_seed),
                "master_seed": int(master_seed),
            }
        )
        plan = seed_plan(int(master_seed), arm, int(seed), episode=int(episode))
        drive, clock = make_drive_clock(self.world)
        decision_source = None
        with_decoder = True
        if arm == "B":
            stepper, _ = make_plastic_stepper(
                self.world, drive, clock, eta=0.5, seed=int(plan["network"])
            )
        elif arm == "A_prime":
            stepper, _ = make_plastic_stepper(
                self.world, drive, clock, eta=0.0, seed=int(plan["network"])
            )
        else:
            stepper = make_fixed_stepper(
                self.world, drive, clock, seed=int(plan["network"])
            )
        if arm == "F":
            model = f_readout.build_readout(seed=int(plan["learning"]))
            decision_source = f_readout.build_decision_source(
                populations=self.world.populations,
                training=False,
                seed=int(plan["learning"]),
                model=model,
            )
            with_decoder = False
        elif arm == "F_beta":
            model = f_beta.build_readout(seed=int(plan["learning"]))
            decision_source = f_beta.build_decision_source(
                populations=self.world.populations,
                training=False,
                seed=int(plan["learning"]),
                model=model,
            )
            with_decoder = False

        components = make_bundle(
            self.world,
            drive=drive,
            clock=clock,
            stepper=stepper,
            condition_id=arm,
            decision_source=decision_source,
            with_decoder=with_decoder,
            max_steps=self.max_steps,
        )
        if arm == "B":
            b_plastic.install_hook(components)
        elif arm == "A_prime":
            a_prime.install_hook(components)
        if self.fail_arm == arm:
            components.neural.adapter = ExplodingAdapter(components.neural.adapter)
        components.metadata = {
            "condition_id": arm,
            "seed": int(seed),
            "episode": int(episode),
            "environment_seed": int(environment_seed),
            "master_seed": int(master_seed),
            "network_seed": int(plan["network"]),
            "learning_seed": int(plan["learning"]),
            "structure_seed": int(plan["structure"]),
            "policy_source": "biological_graph",
            "training": False,
        }
        return components


def artifact_manifests() -> dict:
    manifests = {}
    for seed in PILOT2C_SEEDS:
        for arm in ("F", "F_beta"):
            manifests[(arm, seed)] = {
                "condition_id": arm,
                "campaign_seed": seed,
                "training_seed": 1001,
                "origin": "trained",
                "stage": "trained",
                "parameters": {"path": f"{arm}/{seed}/parameters.pt", "sha256": SHA},
                "digest": "d" * 64,
            }
    return manifests


class FakeArtifacts:
    """The subset of :class:`LoadedArtifacts` the runner reads.

    The manifests are fixtures that describe loaded *trained* artifacts; no
    artifact file exists and nothing is trained here.
    """

    def __init__(self, manifests: dict) -> None:
        self.manifests = dict(manifests)


def make_context(config, seed: int, episode: int) -> dict:
    return {
        "master_seed": config.campaign.master_seed,
        "environment_seed": environment_seed(
            config.campaign.master_seed, seed, episode
        ),
        "seed_plan": None,
        "config_hashes": {
            name: entry["sha256"] for name, entry in config.hashes.items()
        },
        "max_game_updates": config.campaign.max_game_updates,
        "episodes_per_seed": 3,
    }


@pytest.fixture(scope="module")
def world():
    return build_world(make_graph())


@pytest.fixture(scope="module")
def certified(world):
    """Run the exact 54-entry grid through the production runner, in memory."""
    config = small_config()
    factory = SynthFactory(world, config)
    artifacts = FakeArtifacts(artifact_manifests())
    runner = Pilot2CEpisodeRunner(config, factory=factory, artifacts=artifacts)
    rows = [
        runner(arm, seed, episode, make_context(config, seed, episode))
        for arm, seed, episode in pilot2c.pilot2c_plan(config).entries()
    ]
    report = pilot2c.evaluate_certification(rows, config=config)
    return SimpleNamespace(
        config=config,
        world=world,
        factory=factory,
        artifacts=artifacts,
        runner=runner,
        rows=rows,
        report=report,
    )


def rows_for(certified, arm: str) -> list[dict]:
    return [row for row in certified.rows if row["condition"] == arm]


def claims(certified) -> dict:
    return {claim["id"]: claim for claim in certified.report["claims"]}


# ---------------------------------------------------------------------------
# the exact grid and the eight certification claims
# ---------------------------------------------------------------------------


def test_the_grid_has_forty_five_neural_episodes_and_nine_floor_replays(certified):
    plan = pilot2c.pilot2c_plan(certified.config)
    expected = {
        (arm, seed, episode)
        for arm in PILOT2C_ARMS
        for seed in PILOT2C_SEEDS
        for episode in EPISODES
    }
    keys = {
        (row["condition"], row["seed"], row["episode"]) for row in certified.rows
    }
    assert keys == expected
    assert len(certified.rows) == len(plan.entries()) == 54
    assert sum(1 for row in certified.rows if row["condition"] == "floor") == 9
    assert sum(1 for row in certified.rows if row["condition"] != "floor") == 45


def test_all_eight_claims_pass(certified):
    report = certified.report
    assert report["stage"] == "pilot2c"
    assert report["stage_purpose"] == PILOT2C_STAGE_PURPOSE
    assert report["descriptive_only"] is True
    assert report["is_hypothesis_test"] is False
    assert report["estimates_contrasts"] is False
    assert report["merged_into_campaign"] is False
    assert report["n_seeds_selected_written"] is False
    assert report["rows"] == 54

    found = claims(certified)
    assert sorted(found) == [f"P2C-{index}" for index in range(1, 9)]
    for claim in report["claims"]:
        assert claim["passed"] is True, claim["id"]
        assert claim["descriptive_only"] is True
        assert claim["is_hypothesis_test"] is False
    assert report["all_passed"] is True


# ---------------------------------------------------------------------------
# A' identity (P2C-2, P2C-6)
# ---------------------------------------------------------------------------


def test_a_prime_reports_exact_identity_on_all_nineteen_fields(certified):
    a_by_key = {
        (row["seed"], row["episode"]): row for row in rows_for(certified, "A")
    }
    for row in rows_for(certified, "A_prime"):
        block = row["notes"]["a_prime"]
        assert block["mirror"] == "A"
        assert block["fixed_result_present"] is True
        assert block["hard_stop"] is False
        assert block["equivalence"]["all_equal"] is True
        assert block["equivalence"]["field_count"] == 19
        assert block["equivalence"]["tolerance"] == "none"
        assert block["zero_pathway"]["eta"] == 0.0
        assert block["zero_pathway"]["mode"] == "rule_executed_zero_delta"
        assert block["zero_pathway"]["zero_delta"] is True
        fixed = a_by_key[(row["seed"], row["episode"])]
        assert row["weights_before"] == fixed["weights_before"]
        assert row["weights_after"] == fixed["weights_after"]


def test_a_prime_reports_an_exactly_zero_delta(certified):
    for row in rows_for(certified, "A_prime"):
        plasticity = row["notes"]["plasticity"]
        assert plasticity["changed_edges"] == 0
        assert plasticity["max_abs_delta_pa"] == 0.0
        assert plasticity["summary_plasticity"]["eta"] == 0.0
        assert row["notes"]["game_loop"]["weights_unchanged"] is True
        assert row["weights_before"] == row["weights_after"]


def test_b_reports_its_eligible_and_changed_edges(certified):
    for row in rows_for(certified, "B"):
        plasticity = row["notes"]["plasticity"]
        assert plasticity["condition"] == "B"
        assert plasticity["eligible_edges"] > 0
        assert plasticity["n_update_reports"] == row["steps"]
        assert plasticity["n_hook_calls"] == row["steps"]
        assert plasticity["summary_plasticity"]["eta"] == 0.5
        assert isinstance(plasticity["changed_edges"], int)
        assert isinstance(plasticity["max_abs_delta_pa"], float)
        if plasticity["changed_edges"] == 0:
            assert plasticity["max_abs_delta_pa"] == 0.0


def test_a_prime_mismatch_is_a_hard_stop_with_no_retry(world):
    config = small_config()
    factory = SynthFactory(world, config)
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    context = make_context(config, 9001, 0)
    runner("A", 9001, 0, context)
    # Corrupt only the cached A artefact; the A' episode itself is untouched.
    runner._a_results[(9001, 0)]["summary"]["total_reward"] += 1.0

    control = runner("A_prime", 9001, 0, context)
    checked = validate_episode_row(control, expected_condition="A_prime")
    block = checked["notes"]["a_prime"]
    assert block["hard_stop"] is True
    assert block["equivalence"]["all_equal"] is False
    assert block["equivalence"]["tolerance"] == "none"
    assert block["equivalence"]["mismatch"]["field_id"] == "P8"
    assert block["invalidates_on_mismatch"] == ["B"]

    with pytest.raises(StageConfigurationError, match="no retry"):
        runner("A_prime", 9002, 0, make_context(config, 9002, 0))


def test_a_prime_refuses_a_resumed_process_without_an_a_artefact(world):
    config = small_config()
    factory = SynthFactory(world, config)
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    with pytest.raises(StageConfigurationError, match="resumed run has no such artefact"):
        runner("A_prime", 9001, 0, make_context(config, 9001, 0))
    # The runner built A' components (that is the expected call), but it never
    # silently re-ran A to manufacture the missing mirror.
    assert {call["arm"] for call in factory.calls} == {"A_prime"}


# ---------------------------------------------------------------------------
# F and Fbeta readouts (P2C-3, P2C-4)
# ---------------------------------------------------------------------------


def test_f_readout_is_state_dependent_and_frozen(certified):
    for row in rows_for(certified, "F"):
        block = row["notes"]["readout_certification"]
        assert block["state_dependent"] is True
        assert block["feature_weights_all_zero"] is False
        assert block["weights_frozen"] is True
        assert (
            block["before"]["parameter_digest"]
            == block["after"]["parameter_digest"]
        )
        assert (
            block["before"]["feature_weight_sha256"]
            == block["after"]["feature_weight_sha256"]
        )
        assert block["after"]["feature_weight_nonzero"] > 0
        assert row["weights_before"] == row["weights_after"]


def test_f_rows_record_their_trained_artifact(certified):
    for row in rows_for(certified, "F"):
        entries = row["notes"]["readout_certification"]["artifact"]["entries"]
        match = [e for e in entries if e["evaluation_seed"] == row["seed"]]
        assert len(match) == 1
        entry = match[0]
        assert entry["condition_id"] == "F"
        assert entry["origin"] == "trained"
        assert entry["stage"] == "trained"
        assert entry["training_seed"] == 1001
        assert len(entry["parameter_file_sha256"]) == 64
        assert len(entry["parameter_digest"]) == 64


def test_f_beta_is_provably_state_independent(certified):
    for row in rows_for(certified, "F_beta"):
        block = row["notes"]["readout_certification"]
        checks = block["invariant_checks"]
        assert block["state_independent"] is True
        assert block["feature_weights_all_zero"] is True
        assert block["weights_frozen"] is True
        assert block["logits_identical"] is True
        assert checks["single_trainable_tensor"] is True
        assert checks["trainable_is_bias"] is True
        assert checks["feature_weights_exactly_zero"] is True
        assert checks["feature_weights_not_trainable"] is True
        assert block["after"]["trainable_parameters"] == ["bias"]
        # A state-independent policy selects one action for the whole episode.
        assert len([v for v in row["action_counts"].values() if v]) == 1


# ---------------------------------------------------------------------------
# motor silence (P2C-5) and provenance (P2C-7)
# ---------------------------------------------------------------------------


def test_motor_blocks_record_zero_as_zero(certified):
    for row in certified.rows:
        if row["condition"] == "floor":
            continue
        summary = row["motor_summary"]
        assert isinstance(summary, dict)
        assert summary["decisions"] == row["steps"]
        assert summary["total_motor_spikes"] == row["motor_spikes"]
        assert summary["windows_with_motor_spikes"] == (
            summary["decisions_with_motor_spike"]
        )
    claim = claims(certified)["P2C-5"]
    assert claim["passed"] is True
    assert claim["failures"] == []
    for arm, item in claim["per_arm"].items():
        assert item["episodes"] == 9
        # The per-arm block counts zeros explicitly rather than omitting them.
        assert (
            item["episodes_with_zero_motor_spikes"]
            == sum(
                1
                for row in rows_for(certified, arm)
                if int(row["motor_spikes"]) == 0
            )
        )


def test_rows_carry_full_provenance(certified):
    config = certified.config
    expected_inputs = set(config.campaign.frozen_inputs)
    expected_configs = {
        name: entry["sha256"] for name, entry in config.hashes.items()
    }
    assert len(expected_inputs) == 7
    for row in certified.rows:
        assert set(row["input_hashes"]) == expected_inputs
        assert row["config_hashes"] == expected_configs
        notes = row["notes"]
        assert notes["evidence_kind"] == "pilot"
        assert notes["stage_purpose"] == PILOT2C_STAGE_PURPOSE
        assert notes["runner"].endswith("Pilot2CEpisodeRunner")
        assert notes["does_not_establish"].startswith("Pilot 2-C certifies")
        binding = notes["provenance_binding"]
        assert binding["owner_decision"] == "D3"
        assert len(binding["owner_decision_sha256"]) == 64
        assert binding["amendment_id"] == "PHASE_8_PILOT2C_AMENDMENT"
        assert len(binding["amendment_sha256"]) == 64
        if row["condition"] == "floor":
            assert notes["substrate"] == "none"
            assert notes["seed_plan"]["seed_streams"].startswith("none")
            assert notes["floor"]["substrate_free"] is True
        else:
            plan = seed_plan(
                config.campaign.master_seed, row["condition"], row["seed"]
            )
            assert notes["substrate"] == "biological_graph"
            assert notes["seed_plan"]["network_seed"] == plan["network"]
            assert notes["seed_plan"]["learning_seed"] == plan["learning"]
            assert notes["seed_plan"]["structure_seed"] == plan["structure"]
            assert notes["seed_plan"]["environment_seed"] == row["environment_seed"]


def test_evaluator_requires_the_manifest_stage_purpose(certified):
    manifest = {"design": {"stage_purpose": "something_else"}}
    report = pilot2c.evaluate_certification(
        certified.rows, config=certified.config, manifest=manifest
    )
    provenance = {c["id"]: c for c in report["claims"]}["P2C-7"]
    assert provenance["passed"] is False
    assert any(
        failure["row"] == "manifest" for failure in provenance["failures"]
    )


# ---------------------------------------------------------------------------
# floor (P2C-1)
# ---------------------------------------------------------------------------


def test_floor_replays_are_substrate_free_and_constant(certified):
    for row in rows_for(certified, "floor"):
        assert row.get("status", "ok") == "ok"
        assert row["action_counts"] == {"NO_ACTION": row["steps"]}
        assert row["motor_spikes"] == 0
        assert row["weights_before"] is None and row["weights_after"] is None
        evidence = row["evidence"]
        assert evidence["neural_substrate"] == "none"
        assert evidence["is_neural_arm"] is False
        assert evidence["spikes_read"] is False
        assert row["notes"]["floor"]["policy"] == "constant NO_ACTION"


# ---------------------------------------------------------------------------
# pilot / campaign separation and evaluator refusals
# ---------------------------------------------------------------------------


def test_evaluator_refuses_a_campaign_seed(certified):
    row = copy.deepcopy(rows_for(certified, "A")[0])
    row["seed"] = certified.config.campaign.campaign_seeds[0]
    with pytest.raises(StageConfigurationError, match="non-pilot seed"):
        pilot2c.evaluate_certification([row], config=certified.config)


def test_evaluator_refuses_an_undeclared_arm(certified):
    row = copy.deepcopy(rows_for(certified, "A")[0])
    row["condition"] = "C"
    with pytest.raises(StageConfigurationError, match="does not declare arm"):
        pilot2c.evaluate_certification([row], config=certified.config)


def test_synthetic_driver_stamps_rows_and_refuses_them_as_evidence(
    world, tmp_path
):
    config = small_config()
    runner = Pilot2CEpisodeRunner(config, factory=SynthFactory(world, config))
    plan = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=("A",),
        seeds=(9001,),
        episodes=1,
        establishes="synthetic fixture only",
        does_not_establish="nothing",
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )
    base = tmp_path / "runs"
    summary = drive_pilot(
        plan,
        config,
        base_dir=base,
        run_id="p2c_synthetic",
        episode_runner=runner,
        preflight=fake_preflight,
        input_hashes=MANIFEST_INPUT_HASHES,
        synthetic_fixture=True,
    )
    assert summary["evidence_kind"] == "synthetic_fixture"
    assert summary["experimental_evidence"] is False

    run_dir = base / "p2c_synthetic"
    rows = [
        json.loads(line)
        for line in (run_dir / config.campaign.episode_store_name)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["notes"]["evidence_kind"] == "synthetic_fixture"
    assert rows[0]["notes"]["experimental_evidence"] is False
    assert rows[0]["notes"]["not_experimental"] is True

    manifest = json.loads(
        (run_dir / config.campaign.run_manifest_name).read_text(encoding="utf-8")
    )
    assert manifest["design"]["stage_purpose"] == PILOT2C_STAGE_PURPOSE

    report = pilot2c.evaluate_certification(
        rows, config=config, manifest=manifest
    )
    provenance = {c["id"]: c for c in report["claims"]}["P2C-7"]
    assert provenance["passed"] is False
    assert any(
        failure["reason"] == "evidence kind" for failure in provenance["failures"]
    )


def test_synthetic_driver_refuses_the_campaign_results_root():
    config = small_config()
    plan = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=("A",),
        seeds=(9001,),
        episodes=1,
        establishes="nothing",
        does_not_establish="nothing",
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )
    with pytest.raises(StageRefusal, match="may not write under"):
        drive_pilot(
            plan,
            config,
            base_dir=stage_root(config, "pilot2c"),
            run_id="must_not_exist",
            episode_runner=lambda *args: None,
            preflight=fake_preflight,
            synthetic_fixture=True,
        )


def test_driver_never_overwrites_an_existing_run(world, tmp_path):
    config = small_config()
    plan = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=("A",),
        seeds=(9001,),
        episodes=1,
        establishes="nothing",
        does_not_establish="nothing",
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )
    base = tmp_path / "runs"
    run_dir = base / "same_run"
    first = Pilot2CEpisodeRunner(config, factory=SynthFactory(world, config))
    drive_pilot(
        plan,
        config,
        base_dir=base,
        run_id="same_run",
        episode_runner=first,
        preflight=fake_preflight,
        input_hashes=MANIFEST_INPUT_HASHES,
        synthetic_fixture=True,
    )
    before = (run_dir / config.campaign.episode_store_name).read_text(
        encoding="utf-8"
    )
    second_factory = SynthFactory(world, config)
    second = Pilot2CEpisodeRunner(config, factory=second_factory)
    with pytest.raises(ExistingResultError, match="already exists"):
        drive_pilot(
            plan,
            config,
            base_dir=base,
            run_id="same_run",
            episode_runner=second,
            preflight=fake_preflight,
            input_hashes=MANIFEST_INPUT_HASHES,
            synthetic_fixture=True,
        )
    after = (run_dir / config.campaign.episode_store_name).read_text(
        encoding="utf-8"
    )
    assert before == after
    assert second_factory.calls == []


# ---------------------------------------------------------------------------
# runner refusals
# ---------------------------------------------------------------------------


def test_runner_refuses_a_foreign_seed_before_building_components(world):
    config = small_config()
    factory = SynthFactory(world, config)
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    with pytest.raises(StageConfigurationError, match="D3 Pilot 2-C scope"):
        runner("A", 9004, 0, make_context(config, 9004, 0))
    assert factory.calls == []


def test_runner_refuses_a_changed_environment_seed(world):
    config = small_config()
    factory = SynthFactory(world, config)
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    context = make_context(config, 9001, 0)
    context["environment_seed"] += 1
    with pytest.raises(StageConfigurationError, match="declared stream value"):
        runner("A", 9001, 0, context)
    assert factory.calls == []


def test_runner_refuses_changed_configuration_hashes(world):
    config = small_config()
    factory = SynthFactory(world, config)
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    context = make_context(config, 9001, 0)
    context["config_hashes"]["campaign"] = "0" * 64
    with pytest.raises(StageConfigurationError, match="do not match the loaded"):
        runner("A", 9001, 0, context)
    assert factory.calls == []


def test_runner_refuses_an_undeclared_arm(world):
    config = small_config()
    runner = Pilot2CEpisodeRunner(config, factory=SynthFactory(world, config))
    with pytest.raises(StageConfigurationError, match="does not declare arm"):
        runner("C", 9001, 0, make_context(config, 9001, 0))


# ---------------------------------------------------------------------------
# failure rows
# ---------------------------------------------------------------------------


def test_episode_failure_is_a_schema_valid_error_row(world):
    config = small_config()
    factory = SynthFactory(world, config, fail_arm="A")
    runner = Pilot2CEpisodeRunner(config, factory=factory)
    row = runner("A", 9001, 0, make_context(config, 9001, 0))
    checked = validate_episode_row(row, expected_condition="A")
    assert checked["status"] == "error"
    assert "RuntimeError" in checked["error"]
    assert checked["steps"] == 0
    assert checked["observed_updates"] == 0
    assert checked["survival_score"] == 0.0
    assert checked["action_counts"] == {"NO_ACTION": 0}
    assert checked["terminated"] is False and checked["truncated"] is False
    assert checked["notes"]["failure"]["error_type"] == "RuntimeError"
    assert checked["notes"]["evidence_kind"] == "pilot"
    assert (9001, 0) not in runner._a_results


# ---------------------------------------------------------------------------
# D3 authorization scope
# ---------------------------------------------------------------------------


def test_d3_gate_accepts_the_exact_grid_and_rejects_forgeries():
    config = small_config()
    exact = stage_authorization(
        "pilot2c", config=config, plan=pilot2c.pilot2c_plan(config)
    )
    assert exact["authorized"] is True
    assert exact["exemption"]["applied"] is True
    assert exact["exemption"]["scope"]["n_episodes"] == 54
    assert exact["exemption"]["scope"]["uses_randomized_graph"] is False

    forged_arms = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=("A", "B", "C", "F", "F_beta", "A_prime", "floor"),
        seeds=PILOT2C_SEEDS,
        episodes=3,
        establishes="nothing",
        does_not_establish="nothing",
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )
    rejected = stage_authorization("pilot2c", config=config, plan=forged_arms)
    assert rejected["authorized"] is False
    assert any(
        "not the D3 Pilot 2-C scope" in blocker
        for blocker in rejected["blockers"]
    )

    forged_seeds = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=PILOT2C_ARMS,
        seeds=(9001, 9002),
        episodes=3,
        establishes="nothing",
        does_not_establish="nothing",
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )
    rejected = stage_authorization("pilot2c", config=config, plan=forged_seeds)
    assert rejected["authorized"] is False
    assert any("seeds are [9001, 9002]" in b for b in rejected["blockers"])

    no_purpose = PilotPlan(
        stage="pilot2c",
        rev4_step="10.8 (amended by D3)",
        arms=PILOT2C_ARMS,
        seeds=PILOT2C_SEEDS,
        episodes=3,
        establishes="nothing",
        does_not_establish="nothing",
        stage_purpose=None,
    )
    rejected = stage_authorization("pilot2c", config=config, plan=no_purpose)
    assert rejected["authorized"] is False
    assert any("stage_purpose" in b for b in rejected["blockers"])


def test_other_stages_do_not_inherit_the_d3_exemption():
    config = small_config()
    report = stage_authorization("pilot2", config=config, plan=None)
    assert report["authorized"] is False
    assert any(
        blocker.startswith("B7: stage 'pilot2'") for blocker in report["blockers"]
    )


def test_readiness_reports_the_training_refusal_without_blocking_evaluation():
    config = small_config()
    report = pilot2c.pilot2c_readiness(config, preflight=fake_preflight)
    assert report["executable"] is False
    assert report["uses_randomized_graph"] is False
    assert report["constructs_randomized_graph"] is False
    assert report["authorization"]["authorized"] is True
    blockers = report["blockers"]
    assert any(b.startswith("artifacts:") for b in blockers)
    # The global training gate still refuses further training. Pilot 2-C trains
    # nothing, so that refusal is reported but is never a stage blocker.
    assert any("D4 declares B3-B6" in b for b in report["training_blockers"])
    assert not any(b.startswith("training: ") for b in blockers)
    assert report["training_authorization"]["d5_d6_applicable"] is True
    assert (
        report["training_authorization"]["global_training_gate_authorized"] is False
    )

    # The authorised 54-entry run has been executed, so the destination is no
    # longer free and the no-overwrite gate must keep refusing a second run.
    # The readiness report must describe that run, not deny that it exists.
    assert report["results_destination_free"] is False
    assert any(
        "is not free" in blocker and "never overwritten" in blocker
        for blocker in blockers
    )
    destination = stage_root(config, "pilot2c")
    runs = sorted(
        path
        for path in destination.iterdir()
        if path.is_dir() and (path / "manifest.json").is_file()
    )
    assert len(runs) == 1
    run = runs[0]
    for name in (
        "manifest.json",
        "pilot_plan.json",
        "pilot_summary.json",
        "episodes.jsonl",
    ):
        assert (run / name).is_file(), name

    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == run.name
    assert manifest["schema_version"] == 1
    assert manifest["design"]["conditions"] == ["A", "B", "C", "D", "E", "F"]
    assert manifest["design"]["episodes_per_seed"] == 10
    assert manifest["design"]["seed_indices"]["pilot"] == [9001, 9002, 9003]
    assert manifest["integrity"]["non_readme_failures"] == []

    summary = json.loads((run / "pilot_summary.json").read_text(encoding="utf-8"))
    assert summary["stage"] == "pilot2c"
    assert summary["complete"] is True
    assert summary["executed"] is True
    assert summary["planned"] == 54
    assert summary["rows_executed"] == 54
    assert summary["rows_stored"] == 54
    assert Path(summary["run_dir"]).resolve() == run.resolve()

    rows = [
        validate_episode_row(json.loads(line))
        for line in (run / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 54
    assert {row["condition"] for row in rows} == {
        "A",
        "A_prime",
        "B",
        "F",
        "F_beta",
        "floor",
    }
    assert report["training_artifacts"]["loaded"] is False


def test_readiness_refuses_without_a_live_d5_authority(monkeypatch):
    config = small_config()
    stub = {
        "applicable": False,
        "path": "D5.json",
        "valid": False,
        "d6": {"path": "D6.json", "valid": False},
        "training_execution_authorized": False,
        "authorised_scope": {},
        "frozen_sources": {},
        "g3": {},
        "does_not_authorise": [],
        "failures": ["fixture: D5 is not applicable"],
        "reason": "fixture: D5 is not applicable",
    }
    monkeypatch.setattr(pilot2c, "d5_applicability", lambda: stub)
    report = pilot2c.pilot2c_readiness(config, preflight=fake_preflight)
    assert report["executable"] is False
    assert any(
        b.startswith("training artifacts:") for b in report["blockers"]
    )


# ---------------------------------------------------------------------------
# A-2 loader: pilot scope only
# ---------------------------------------------------------------------------


def test_pilot_loader_requires_an_explicit_pairing(tmp_path):
    config = load_phase8_config()
    training = validate_training_config(config)
    root = tmp_path / "artifacts"
    write_fixture(root, training, "F", campaign_seed=9001, training_seed=1001)
    write_fixture(root, training, "F_beta", campaign_seed=9001, training_seed=1001)
    with pytest.raises(TrainingConfigError, match="explicit pairing"):
        load_pilot_evaluation_artifacts(
            config,
            root,
            pairing=None,
            evaluation_seeds=(9001,),
            require_trained=False,
            allow_synthetic_fixtures=True,
        )


def test_pilot_loader_requires_the_pairing_to_declare_every_key(tmp_path):
    config = load_phase8_config()
    training = validate_training_config(config)
    root = tmp_path / "artifacts"
    write_fixture(root, training, "F", campaign_seed=9001, training_seed=1001)
    write_fixture(root, training, "F_beta", campaign_seed=9001, training_seed=1001)
    with pytest.raises(TrainingConfigError, match="does not declare"):
        load_pilot_evaluation_artifacts(
            config,
            root,
            pairing={("F", 9001): 1001},
            evaluation_seeds=(9001,),
            require_trained=False,
            allow_synthetic_fixtures=True,
        )


def test_pilot_loader_refuses_an_initialized_fixture_as_trained(tmp_path):
    config = load_phase8_config()
    training = validate_training_config(config)
    root = tmp_path / "artifacts"
    write_fixture(root, training, "F", campaign_seed=9001, training_seed=1001)
    write_fixture(root, training, "F_beta", campaign_seed=9001, training_seed=1001)
    pairing = {("F", 9001): 1001, ("F_beta", 9001): 1001}
    with pytest.raises(ArtifactCompatibilityError, match="origin="):
        load_pilot_evaluation_artifacts(
            config,
            root,
            pairing=pairing,
            evaluation_seeds=(9001,),
            require_trained=True,
        )


def test_pilot_scope_refuses_a_campaign_seed(tmp_path):
    config = load_phase8_config()
    training = validate_training_config(config)
    root = tmp_path / "artifacts"
    write_fixture(root, training, "F", campaign_seed=2, training_seed=1001)
    write_fixture(root, training, "F_beta", campaign_seed=2, training_seed=1001)
    with pytest.raises(TrainingConfigError, match="not declared in seeds.pilot"):
        load_training_artifacts(
            root,
            config=training,
            campaign_seeds=(2,),
            pairing={("F", 2): 1001, ("F_beta", 2): 1001},
            require_trained=False,
            allow_synthetic_fixtures=True,
            seed_scope="pilot",
        )


def test_pilot_loader_loads_declared_pilot_seeds_in_the_pilot_scope(tmp_path):
    config = load_phase8_config()
    training = validate_training_config(config)
    root = tmp_path / "artifacts"
    write_fixture(root, training, "F", campaign_seed=9001, training_seed=1001)
    write_fixture(root, training, "F_beta", campaign_seed=9001, training_seed=1001)
    loaded = load_pilot_evaluation_artifacts(
        config,
        root,
        pairing={("F", 9001): 1001, ("F_beta", 9001): 1001},
        evaluation_seeds=(9001,),
        require_trained=False,
        allow_synthetic_fixtures=True,
    )
    report = loaded.describe()
    assert report["seed_scope"] == "pilot"
    assert report["campaign_seeds"] == [9001]
    assert report["loaded"] == ["F:9001", "F_beta:9001"]
    assert report["pairing_source"] == "explicit"
    assert report["provenance"] == "synthetic-fixture-artifacts"
    assert report["training_performed_here"] is False
    assert report["execution_authorized"] is False
    assert report["readout_pairs"]["9001"]["training_seed"] == 1001
    assert report["readout_pairs"]["9001"]["paired"] is True


def test_plan_stage_purpose_is_recorded_on_the_plan():
    config = small_config()
    described = pilot2c.pilot2c_plan(config).as_dict(config.campaign.master_seed)
    assert described["stage_purpose"] == PILOT2C_STAGE_PURPOSE
    assert described["n_entries"] == 54
    floor_entry = next(
        entry for entry in described["entries"] if entry["arm"] == "floor"
    )
    assert floor_entry["substrate"] == "none"
    assert floor_entry["network_seed"] is None
