"""Focused tests for the D5/D6 authorization and the pilot training path.

Every episode here runs on the 32-node fixture from ``test_phase_8_conditions``
through the real closed loop and a real F/Fβ readout controller. The fixture is
a test network, not a biological claim: artifacts written here use
``evidence_kind = "synthetic_fixture"`` and are never experimental evidence. No
BANC-scale graph, no certified random graph, no campaign stage and no Pilot 2-C
episode is touched.

Covered, in the order the owner directive lists them: D5 and D6 hash binding,
the exact six-artifact plan, refusal of a changed seed/condition/budget/
substrate, refusal of E/E-full and of campaign execution, the separately gated
Pilot 2-C stage, the blocked graph-dependent stages, G3 preservation, distinct
artifact identities and correct seed pairing, trained origin/stage metadata,
rejection of synthetic artifacts, checkpoint completeness, provenance
completeness, and enforced resume equivalence.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from brain.banc_graph import sha256_file
from brain.neuron_model import LIFParameters
from environment import ControlledGameEnvironment
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.stages.pilot2c import pilot2c_readiness, run_pilot2c
from experiments.phase_8.stages.common import StageRefusal
from experiments.phase_8.training import gate as training_gate
from experiments.phase_8.training.config import validate_training_config
from experiments.phase_8.training.contracts import (
    assert_environment_stream_disjoint,
    training_environment_schedule,
)
from experiments.phase_8.training.d5 import (
    D5_RECORD_PATH,
    D6_RECORD_PATH,
    PILOT_TRAINING_ARTIFACTS,
    PILOT_TRAINING_EPISODES,
    assert_d5_training_authorized,
    d5_applicability,
)
from experiments.phase_8.training.errors import (
    ArtifactSchemaError,
    TrainingError,
    TrainingNotAuthorized,
)
from experiments.phase_8.training.exact_checkpoint import read_exact_checkpoint
from experiments.phase_8.training.initialization import initialize
from experiments.phase_8.training.pilot import (
    PILOT_SUBSTRATE,
    build_pilot_plan,
    validate_pilot_scope,
)
from experiments.phase_8.training.pilot_artifact import (
    read_training_run,
    verify_trained_artifact,
    write_trained_artifact,
)
from experiments.phase_8.training.pilot_training import (
    PilotEpisodeRunner,
    build_controller,
    run_pilot_artifact,
    run_pilot_plan,
    run_training_loop,
    verify_resume_equivalence,
)
from experiments.phase_8.training.validation import validate_manifest

from test_phase_8_conditions import (
    build_world,
    decoder_config,
    make_drive_clock,
    make_fixed_stepper,
    make_graph,
)

UPDATES = 3
TRAINED_UPDATES = 2
SIX_UPDATES = 1


def fake_preflight(gate_gb: float) -> dict:
    return {
        "available_gb": 999.0,
        "gate_gb": float(gate_gb),
        "passed": True,
        "reason": "synthetic preflight for the D5 pilot tests",
    }


class FixtureFactory:
    """The ``CampaignFactory`` surface over the 32-node fixture."""

    def __init__(self, world, *, max_updates: int = UPDATES, structure=None) -> None:
        self.world = world
        self.max_steps = int(max_updates)
        self.structure = structure
        self.settings = SimpleNamespace(
            neural_dt_ms=0.5,
            game_dt_s=1.0 / 60.0,
            duration_ms=60_000.0,
            background_current_pa=0.0,
            noise_std_pa=0.0,
            window_ms=50.0,
            distance_horizon=25,
            max_game_updates=self.max_steps,
        )

    def graph_and_policy(self, condition, seed):
        return self.world.graph, self.world.policy, self.structure

    def _sensory(self):
        drive, _clock = make_drive_clock(self.world)
        return self.world.mapping, drive

    def _fixed_stepper(self, graph, policy, drive, seed):
        _mapping, clock = make_drive_clock(self.world)
        return make_fixed_stepper(self.world, drive, clock, seed=seed)

    def environment(self):
        return ControlledGameEnvironment(max_steps=self.max_steps, render_mode=None)


@pytest.fixture(scope="module")
def world():
    value = build_world(make_graph())
    value.neuron_params = LIFParameters()
    value.decoder_config = decoder_config()
    return value


@pytest.fixture(scope="module")
def phase8_config():
    return load_phase8_config()


@pytest.fixture(scope="module")
def training_config(phase8_config):
    return validate_training_config(phase8_config)


@pytest.fixture(scope="module")
def plan(phase8_config, training_config):
    return build_pilot_plan(phase8_config, config=training_config)


_CONFIG_CACHE: dict = {}


def cached_training_config():
    if not _CONFIG_CACHE:
        _CONFIG_CACHE["value"] = validate_training_config(load_phase8_config())
    return _CONFIG_CACHE["value"]


def start_run(plan, world, key, *, updates, budget, root, resume_from=None, interrupt_after=None, substrate="synthetic_fixture"):
    condition, seed = key
    entry = plan.get(condition, seed)
    factory = FixtureFactory(world, max_updates=updates)
    config = cached_training_config()
    initialized = initialize(
        condition,
        campaign_seed=entry.evaluation_seed,
        training_seed=entry.training_seed,
        master_seed=plan.master_seed,
    )
    controller = build_controller(
        condition,
        initialized.model,
        world.populations,
        seed=entry.sampling_seed,
        config=config,
    )
    result = run_training_loop(
        initialized=initialized,
        model=initialized.model,
        controller=controller,
        episode_runner=PilotEpisodeRunner(factory),
        config=config,
        evaluation_seed=entry.evaluation_seed,
        training_seed=entry.training_seed,
        init_seed=entry.init_seed,
        master_seed=plan.master_seed,
        b3=entry.b3,
        environment_seeds=entry.environment_seeds,
        budget=budget,
        checkpoint_root=Path(root) / "checkpoints",
        artifact_directory_path=root,
        sampling_seed=entry.sampling_seed,
        network_seed=entry.network_seed,
        resume_from=resume_from,
        interrupt_after=interrupt_after,
        substrate=substrate,
    )
    return result, entry


# ---------------------------------------------------------------------------
# D5 and D6 binding
# ---------------------------------------------------------------------------


def test_d5_record_hash_binds_to_the_plan(plan):
    assert plan.d5_sha256 == sha256_file(D5_RECORD_PATH)
    assert len(plan.d5_sha256) == 64
    assert plan.d5_sha256 != str(D5_RECORD_PATH)
    report = d5_applicability()
    assert plan.d5_sha256 == report["d6"]["sources"]["d5"]["observed_sha256"]


def test_d6_record_hash_binds_to_the_plan(plan):
    assert plan.d6_sha256 == sha256_file(D6_RECORD_PATH)
    assert len(plan.d6_sha256) == 64
    assert plan.d6_sha256 != str(D6_RECORD_PATH)


# ---------------------------------------------------------------------------
# the exact plan
# ---------------------------------------------------------------------------


def test_exact_d5_plan_is_accepted(plan):
    described = plan.describe()
    assert described["n_artifacts"] == 6
    assert described["n_episodes"] == 120
    assert described["substrate"] == "biological_graph"
    keys = {(entry.condition_id, entry.evaluation_seed) for entry in plan.entries}
    assert keys == {
        ("F", 9001), ("F", 9002), ("F", 9003),
        ("F_beta", 9001), ("F_beta", 9002), ("F_beta", 9003),
    }
    for entry in plan.entries:
        assert entry.episodes == PILOT_TRAINING_EPISODES == 20
        assert entry.substrate == PILOT_SUBSTRATE
        assert entry.environment_seeds == training_environment_schedule(
            plan.master_seed, entry.training_seed, 20
        )
        assert_environment_stream_disjoint(
            entry.environment_seeds, master_seed=plan.master_seed
        )
    assert plan.b3["sha256"] == (
        "bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980"
    )
    recorded = {
        (item["condition_id"], item["evaluation_seed"]): item["training_seed"]
        for item in PILOT_TRAINING_ARTIFACTS
    }
    assert {
        (entry.condition_id, entry.evaluation_seed): entry.training_seed
        for entry in plan.entries
    } == recorded


def test_seed_pairing_is_correct(plan):
    by_seed = {
        9001: 1008,
        9002: 1014,
        9003: 1005,
    }
    for evaluation_seed, training_seed in by_seed.items():
        forward = plan.get("F", evaluation_seed)
        beta = plan.get("F_beta", evaluation_seed)
        assert forward.training_seed == training_seed
        assert beta.training_seed == training_seed
        # F and Fβ share a training seed but never their initial parameters.
        assert forward.init_seed != beta.init_seed
        assert forward.network_seed != beta.network_seed
        # The B4 stream is shared across conditions at one training seed.
        assert forward.environment_seeds == beta.environment_seeds
        assert evaluation_seed not in forward.environment_seeds


def test_changed_evaluation_seed_is_refused(plan):
    with pytest.raises(TrainingNotAuthorized, match="evaluation seeds"):
        validate_pilot_scope("F", 9004)
    with pytest.raises(TrainingNotAuthorized, match="six artifacts"):
        plan.get("F", 9004)
    with pytest.raises(TrainingNotAuthorized):
        assert_d5_training_authorized("F", 9000)


def test_changed_condition_is_refused(plan):
    for condition in ("A", "B", "C", "D", "E", "E_full", "F_init"):
        with pytest.raises(TrainingNotAuthorized):
            validate_pilot_scope(condition, 9001)
        with pytest.raises(TrainingNotAuthorized):
            plan.get(condition, 9001)
    with pytest.raises(TrainingNotAuthorized, match="F and F_beta only"):
        assert_d5_training_authorized("E", 9001)


def test_changed_budget_is_refused(plan):
    with pytest.raises(TrainingNotAuthorized, match="exactly 20 episodes"):
        validate_pilot_scope("F", 9001, episodes=19)
    with pytest.raises(TrainingNotAuthorized, match="exactly 20 episodes"):
        validate_pilot_scope("F", 9001, episodes=21)


def test_changed_substrate_is_refused(plan, world, tmp_path):
    entry = replace(plan.get("F", 9001), substrate="randomized_graph")
    with pytest.raises(TrainingNotAuthorized, match="frozen biological substrate"):
        run_pilot_artifact(
            load_phase8_config(), entry, root=tmp_path / "out", factory=FixtureFactory(world)
        )
    assert not (tmp_path / "out").exists()

    # The episode runner also refuses a factory that returns a structure.
    factory = FixtureFactory(world, structure={"certified": True})
    runner = PilotEpisodeRunner(factory)
    initialized = initialize(
        "F", campaign_seed=9001, training_seed=1008, master_seed=plan.master_seed
    )
    controller = build_controller(
        "F",
        initialized.model,
        world.populations,
        seed=0,
        config=validate_training_config(load_phase8_config()),
    )
    with pytest.raises(TrainingError, match="frozen biological graph"):
        runner.run_episode(
            "F",
            evaluation_seed=9001,
            episode=0,
            environment_seed=1,
            network_seed=2,
            controller=controller,
        )


def test_e_and_e_full_are_refused(world, plan):
    with pytest.raises(TrainingNotAuthorized):
        build_controller(
            "E",
            object(),
            world.populations,
            seed=0,
            config=validate_training_config(load_phase8_config()),
        )
    with pytest.raises(TrainingNotAuthorized):
        build_controller(
            "E_full",
            object(),
            world.populations,
            seed=0,
            config=validate_training_config(load_phase8_config()),
        )


def test_campaign_execution_is_still_refused(phase8_config):
    with pytest.raises(Exception) as refused:
        training_gate.assert_training_authorized()
    assert refused.type.__name__ in {"TrainingNotAuthorized", "DesignUnresolvedError"}
    design = training_gate.design_status(phase8_config.campaign)
    assert design["resolved"] is False
    assert design["value"] is None


def test_pilot2c_episodes_are_separately_gated(phase8_config, tmp_path):
    readiness = pilot2c_readiness(phase8_config, preflight=fake_preflight)
    assert readiness["executable"] is False
    assert any("pairing" in blocker for blocker in readiness["blockers"])
    base = tmp_path / "pilot2c"
    with pytest.raises(StageRefusal):
        run_pilot2c(
            phase8_config,
            run_id="must_not_run",
            base_dir=base,
            preflight=fake_preflight,
        )
    assert not base.exists()


def test_graph_dependent_stages_remain_blocked():
    report = d5_applicability()
    scope = report["d6"]["scope"]
    assert scope["graph_dependent_stages_blocked"] is True
    assert scope["graph_access_authorised"] is False
    assert scope["graph_construction_authorised"] is False
    assert scope["graph_substitution_authorised"] is False
    assert scope["rev4_section_9_3_unchanged"] is True
    assert report["authorised_scope"]["uses_randomized_graph"] is False


def test_g3_deviation_is_preserved():
    report = d5_applicability()
    g3 = report["g3"]
    assert g3["preserved"] is True
    assert g3["status"] == "deviation_recorded"
    assert g3["gate_weakened"] is False
    assert g3["rev4_section"] == "9.3"
    assert g3["gate_gb"] == 4.0
    assert g3["n_graph_seeds"] == 16
    assert report["d6"]["scope"]["g3_status_preserved"] == "deviation_recorded"
    assert report["d6"]["scope"]["graphs_unchanged"] == 16
    assert report["d6"]["scope"]["certificates_unchanged"] == 16


# ---------------------------------------------------------------------------
# the training loop and its checkpoints
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def short_run(world, plan, tmp_path_factory):
    root = tmp_path_factory.mktemp("short_run")
    result, entry = start_run(
        plan, world, ("F", 9001), updates=UPDATES, budget=4, root=root
    )
    return {"result": result, "entry": entry, "root": root}


def test_trained_run_records_origin_and_stage(short_run):
    result = short_run["result"]
    assert result.origin == "trained"
    assert result.stage == "trained"
    assert result.training_performed_here is True
    assert result.substrate == "synthetic_fixture"
    assert result.episodes_completed == 4
    assert result.parameter_digest != result.initial_parameter_digest
    assert result.sampling_seed == short_run["entry"].sampling_seed
    assert result.network_seed == short_run["entry"].network_seed


def test_checkpoints_are_complete_and_usable(short_run, training_config):
    result = short_run["result"]
    assert len(result.checkpoints) == 4
    for index, record in enumerate(result.checkpoints, start=1):
        directory = Path(record["directory"])
        assert directory.name == f"episode_{index:03d}"
        assert record["integrity_verified"] is True
        assert record["rng_checkpointed"] is True
        assert record["optimizer_state_checkpointed"] is True
        assert record["environment_present"] is False
        for name in ("checkpoint.json", "components.npz", "parameters.npz"):
            assert (directory / name).is_file()
        checkpoint = read_exact_checkpoint(
            directory, config=training_config, expected_condition="F"
        )
        assert checkpoint.manifest["origin"] == "synthetic_fixture"
        assert checkpoint.manifest["stage"] == "training_checkpoint"
        for component in ("python", "numpy", "torch", "sampler"):
            assert checkpoint.manifest["rng"][component]["present"] is True
        assert checkpoint.manifest["rng"]["environment"]["present"] is False
        assert checkpoint.manifest["rng"]["environment"]["reason"]
        assert checkpoint.manifest["optimizer"]["state_checkpointed"] is True
        assert checkpoint.manifest["progress"]["episodes_completed"] == index
        assert len(checkpoint.manifest["progress"]["episodes"]) == index
        assert checkpoint.manifest["progress"]["environment_seeds_used"] == list(
            result.environment_seeds[:index]
        )


def test_episodes_are_isolated_and_deterministic(world, plan, tmp_path_factory):
    first_root = tmp_path_factory.mktemp("iso_first")
    second_root = tmp_path_factory.mktemp("iso_second")
    first, _ = start_run(plan, world, ("F", 9002), updates=UPDATES, budget=2, root=first_root)
    second, _ = start_run(plan, world, ("F", 9002), updates=UPDATES, budget=2, root=second_root)
    assert [dict(item) for item in first.episodes] == [dict(item) for item in second.episodes]
    assert first.parameter_digest == second.parameter_digest
    assert first.episodes[0]["environment_seed"] != first.episodes[1]["environment_seed"]
    assert all(item["n_decisions"] == item["steps"] for item in first.episodes)


def test_interruption_stops_at_the_requested_episode(world, plan, tmp_path_factory):
    root = tmp_path_factory.mktemp("interrupted")
    result, _ = start_run(
        plan, world, ("F", 9003), updates=UPDATES, budget=4, root=root, interrupt_after=2
    )
    assert result.interrupted is True
    assert result.episodes_completed == 2
    assert len(result.checkpoints) == 2
    assert result.resume["resumed"] is False


def test_resume_equivalence_is_enforced(world, plan, tmp_path_factory):
    full_root = tmp_path_factory.mktemp("full_run")
    part_root = tmp_path_factory.mktemp("part_run")
    kwargs = dict(updates=UPDATES, budget=4)
    uninterrupted, _ = start_run(plan, world, ("F_beta", 9002), root=full_root, **kwargs)
    first, _ = start_run(
        plan, world, ("F_beta", 9002), root=part_root, interrupt_after=2, **kwargs
    )
    assert first.interrupted is True
    resumed, _ = start_run(
        plan,
        world,
        ("F_beta", 9002),
        root=part_root,
        resume_from=part_root / "checkpoints" / "episode_002",
        **kwargs,
    )
    assert resumed.resume["resumed"] is True
    assert resumed.resume["start_episode"] == 2
    report = verify_resume_equivalence(uninterrupted, resumed)
    assert report["equivalent"] is True
    assert report["exactness_claim"] == "demonstrated"

    # A partial run is not equivalent to a complete one, and never is silently.
    with pytest.raises(TrainingError, match="not equivalent"):
        verify_resume_equivalence(uninterrupted, first)


def test_resumed_run_ledger_retains_every_checkpoint(world, plan, tmp_path_factory):
    root = tmp_path_factory.mktemp("resume_ledger")
    kwargs = dict(updates=UPDATES, budget=4)
    start_run(
        plan, world, ("F_beta", 9003), root=root, interrupt_after=2, **kwargs
    )
    resumed, _ = start_run(
        plan,
        world,
        ("F_beta", 9003),
        root=root,
        resume_from=root / "checkpoints" / "episode_002",
        **kwargs,
    )
    assert resumed.episodes_completed == 4
    assert [record["episode"] for record in resumed.checkpoints] == [1, 2, 3, 4]
    assert all(record["integrity_verified"] for record in resumed.checkpoints)


def test_resume_refuses_a_checkpoint_from_another_seed(world, plan, tmp_path_factory):
    foreign_root = tmp_path_factory.mktemp("foreign")
    result, _ = start_run(
        plan, world, ("F", 9001), updates=UPDATES, budget=1, root=foreign_root
    )
    checkpoint = foreign_root / "checkpoints" / "episode_001"
    with pytest.raises(Exception, match="training_seed|pairing|requires"):
        start_run(
            plan,
            world,
            ("F", 9002),
            updates=UPDATES,
            budget=2,
            root=tmp_path_factory.mktemp("foreign_target"),
            resume_from=checkpoint,
        )


# ---------------------------------------------------------------------------
# the trained artifact and its provenance
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def trained_run(world, plan, tmp_path_factory):
    root = tmp_path_factory.mktemp("trained_run")
    result, entry = start_run(
        plan,
        world,
        ("F_beta", 9001),
        updates=TRAINED_UPDATES,
        budget=PILOT_TRAINING_EPISODES,
        root=root,
    )
    return {"result": result, "entry": entry, "root": root}


@pytest.fixture(scope="module")
def trained_site(phase8_config, training_config, plan, trained_run):
    root = Path(trained_run["root"]) / "artifacts"
    site = write_trained_artifact(
        phase8_config,
        trained_run["result"],
        trained_run["entry"],
        root=root,
        plan=plan,
        config=training_config,
        evidence_kind="synthetic_fixture",
    )
    return site


def test_trained_artifact_reloads_as_trained(trained_site, training_config):
    assert trained_site["origin"] == "trained"
    assert trained_site["stage"] == "trained"
    assert trained_site["evidence_kind"] == "synthetic_fixture"
    assert trained_site["experimental_evidence"] is False
    verified = verify_trained_artifact(
        trained_site["directory"], config=training_config, expected_condition="F_beta"
    )
    assert verified["verified"] is True
    assert verified["artifact"]["origin"] == "trained"
    assert verified["artifact"]["stage"] == "trained"
    assert verified["artifact"]["model_kind"] == "bias_only_readout"
    assert verified["provenance"]["episodes_completed"] == PILOT_TRAINING_EPISODES
    assert verified["provenance"]["checkpoints"] == PILOT_TRAINING_EPISODES


def test_training_artifact_metadata_is_complete(trained_site, plan, training_config):
    directory = Path(trained_site["directory"])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["origin"] == "trained"
    assert manifest["stage"] == "trained"
    assert manifest["condition_id"] == "F_beta"
    assert manifest["campaign_seed"] == 9001
    assert manifest["training_seed"] == 1008
    assert manifest["master_seed"] == plan.master_seed
    assert manifest["training_config_sha256"] == training_config.sha256()
    validate_manifest(manifest)


def test_provenance_is_complete(trained_site, plan, training_config, phase8_config):
    site = trained_site
    provenance = read_training_run(site["directory"])
    assert provenance["kind"] == "pilot_training_run"
    assert provenance["evidence_kind"] == "synthetic_fixture"
    assert provenance["experimental_evidence"] is False
    assert provenance["origin"] == "trained" and provenance["stage"] == "trained"
    assert provenance["identity"] == {
        "condition_id": "F_beta",
        "evaluation_seed": 9001,
        "training_seed": 1008,
        "pool_index": 7,
        "n_features": 3,
        "model_kind": "bias_only_readout",
    }
    authorisation = provenance["authorisation"]
    assert authorisation["owner_decision"] == "D5"
    assert authorisation["d5_sha256"] == plan.d5_sha256
    assert authorisation["d6_sha256"] == plan.d6_sha256
    assert authorisation["uses_randomized_graph"] is False
    seeds = provenance["seeds"]
    assert seeds["b3"]["derivation_sha256"] == plan.b3["sha256"]
    assert seeds["b3"]["entry"]["training_seed"] == 1008
    assert seeds["b4"]["schedule"] == list(plan.get("F_beta", 9001).environment_seeds)
    assert seeds["b4"]["initialization_environment_seed"] == plan.get(
        "F_beta", 9001
    ).initialization_environment_seed
    assert seeds["network_seed"] == plan.get("F_beta", 9001).network_seed
    assert provenance["training_config"]["sha256"] == training_config.sha256()
    assert provenance["budget"] == {"unit": "episodes", "value": 20}
    assert provenance["episodes_completed"] == 20
    assert len(provenance["episodes"]) == 20
    assert provenance["digest"]["trainable"] == site["parameter_digest"]
    assert provenance["digest"]["state"] == site["state_digest"]
    assert provenance["artifacts"]["parameters"]["sha256"] == site["parameters_sha256"]
    assert provenance["artifacts"]["manifest"]["sha256"] == site["manifest_sha256"]
    assert len(provenance["checkpoints"]) == 20
    assert all(item["retained"] and item["integrity_verified"] for item in provenance["checkpoints"])
    assert provenance["checkpoint_policy"]["cadence"].startswith("one checkpoint")
    assert provenance["rng"]["components"] == ["python", "numpy", "torch", "sampler"]
    assert provenance["rng"]["environment"]["present"] is False
    assert provenance["optimizer"]["state_checkpointed"] is True
    assert len(provenance["optimizer"]["checkpoint_digests"]) == 20
    assert provenance["frozen_inputs"] == dict(phase8_config.campaign.frozen_inputs)
    assert provenance["limitations"]
    assert any("readout parameters only" in item for item in provenance["limitations"])
    assert any("not experimental evidence" in item for item in provenance["limitations"])


def test_synthetic_fixtures_cannot_become_experimental_evidence(
    phase8_config, training_config, plan, trained_run, tmp_path
):
    result = trained_run["result"]
    entry = trained_run["entry"]

    # A fixture run cannot be written as experimental evidence.
    with pytest.raises(TrainingNotAuthorized, match="cannot become experimental evidence"):
        write_trained_artifact(
            phase8_config,
            result,
            entry,
            root=tmp_path / "experimental",
            plan=plan,
            config=training_config,
            evidence_kind="experimental",
        )
    assert not (tmp_path / "experimental").exists()

    # A result with no training performed here is refused outright.
    with pytest.raises(ArtifactSchemaError, match="no training performed"):
        write_trained_artifact(
            phase8_config,
            replace(result, training_performed_here=False),
            entry,
            root=tmp_path / "no_training",
            plan=plan,
            config=training_config,
            evidence_kind="synthetic_fixture",
        )

    # A result claiming a synthetic origin is refused outright.
    with pytest.raises(ArtifactSchemaError, match="origin"):
        write_trained_artifact(
            phase8_config,
            replace(result, origin="synthetic_fixture"),
            entry,
            root=tmp_path / "synthetic_origin",
            plan=plan,
            config=training_config,
            evidence_kind="synthetic_fixture",
        )

    # The artifact schema refuses synthetic + trained even if hand-built.
    directory = Path(trained_run["root"]) / "artifacts" / "F_beta" / "seed_9001"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest["origin"] = "synthetic_fixture"
    manifest["stage"] = "trained"
    with pytest.raises(ArtifactSchemaError, match="synthetic fixture"):
        validate_manifest(manifest)


def test_artifact_writer_never_overwrites(trained_site, phase8_config, training_config, plan, trained_run):
    with pytest.raises(ArtifactSchemaError, match="already exists"):
        write_trained_artifact(
            phase8_config,
            trained_run["result"],
            trained_run["entry"],
            root=Path(trained_site["directory"]).parent.parent,
            plan=plan,
            config=training_config,
            evidence_kind="synthetic_fixture",
        )


# ---------------------------------------------------------------------------
# the six-artifact plan end to end (fixture substrate, short episodes)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def six_artifacts(world, plan, phase8_config, tmp_path_factory):
    root = tmp_path_factory.mktemp("six")
    summary = run_pilot_plan(
        plan,
        phase8_config,
        root=root,
        factory=FixtureFactory(world, max_updates=SIX_UPDATES),
        evidence_kind="synthetic_fixture",
    )
    return {"summary": summary, "root": root}


def test_six_distinct_artifacts_are_written(six_artifacts, training_config, plan):
    summary = six_artifacts["summary"]
    assert summary["artifacts_completed"] == 6
    assert summary["episodes_completed"] == 120
    assert summary["evidence_kind"] == "synthetic_fixture"
    assert summary["training_execution_authorized_by"] == "D5"

    manifests = []
    directories = []
    for entry in plan.entries:
        directory = Path(six_artifacts["root"]) / entry.condition_id / f"seed_{entry.evaluation_seed}"
        verified = verify_trained_artifact(
            directory, config=training_config, expected_condition=entry.condition_id
        )
        assert verified["artifact"]["origin"] == "trained"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        manifests.append(manifest)
        directories.append(directory)

    # Artifact identity is the declared (condition, evaluation seed) and its own
    # files, never a parameter value: the bias-only F_beta control is
    # ``state_independent`` (its bias starts at zero regardless of the init
    # seed), so on this seed-insensitive fixture its three parameter sets can
    # legitimately coincide. The forward F artifacts, whose weights are seeded,
    # must still differ.
    assert len({(item["condition_id"], item["campaign_seed"]) for item in manifests}) == 6
    assert len({directory for directory in directories}) == 6
    assert len({sha256_file(directory / "manifest.json") for directory in directories}) == 6
    forward = [item for item in manifests if item["condition_id"] == "F"]
    assert len({item["digest"]["trainable"] for item in forward}) == 3
    assert len({item["digest"]["state"] for item in forward}) == 3
    assert len({item["parameters"]["sha256"] for item in forward}) == 3
    for evaluation_seed in (9001, 9002, 9003):
        forward = next(
            item for item in manifests
            if item["condition_id"] == "F" and item["campaign_seed"] == evaluation_seed
        )
        beta = next(
            item for item in manifests
            if item["condition_id"] == "F_beta" and item["campaign_seed"] == evaluation_seed
        )
        assert forward["training_seed"] == beta["training_seed"]
        assert forward["init_seed"] != beta["init_seed"]

    log = Path(summary["log"])
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    kinds = [event["event"] for event in events]
    assert kinds.count("plan_start") == 1
    assert kinds.count("plan_complete") == 1
    assert kinds.count("artifact_start") == 6
    assert kinds.count("artifact_complete") == 6
    assert "artifact_failed" not in kinds


def test_plan_never_overwrites_existing_artifacts(six_artifacts, world, plan, phase8_config):
    with pytest.raises(ArtifactSchemaError, match="overwrite"):
        run_pilot_plan(
            plan,
            phase8_config,
            root=six_artifacts["root"],
            factory=FixtureFactory(world, max_updates=SIX_UPDATES),
            evidence_kind="synthetic_fixture",
        )


# ---------------------------------------------------------------------------
# the authorization cannot be widened
# ---------------------------------------------------------------------------


def test_global_gate_and_pilot_scope_are_separate():
    report = d5_applicability()
    assert report["applicable"] is True
    assert report["training_execution_authorized"] is True
    # The global gate is not widened by D5: it still refuses.
    with pytest.raises(Exception):
        training_gate.assert_training_authorized()
    assert training_gate.training_authorization_status()["training_authorized"] is False
