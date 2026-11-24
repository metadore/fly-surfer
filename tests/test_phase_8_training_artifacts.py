"""Focused synthetic tests for the Phase 8 G4 training-artifact pipeline.

Every test uses tiny freshly initialized models and a temporary directory. No
training update is executed, no game episode runs and no BANC graph is loaded.
These are infrastructure tests, not experimental evidence (G4 brief §5–§7).

Covered: manifest schema, REV4 configuration validation, deterministic
initialization, separate seed recording, F/Fβ/E separation, Fβ state
independence, serialization and reload, hash and digest mismatches, missing
artifacts, factory compatibility, the null ``n_seeds_selected`` refusal and the
unconditional refusal to train.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from evaluation.conventional import ConventionalAgent
from experiments.phase_8.campaign.factory import (
    CampaignFactory,
    FactoryError,
    TrainingArtifacts,
)
from experiments.phase_8.campaign.protocol import protocol_identity
from experiments.phase_8.config import PROJECT_ROOT, load_phase8_config
from experiments.phase_8.seeds import seed_plan
from experiments.phase_8.training import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    ArtifactSchemaError,
    DesignUnresolvedError,
    LoadedArtifacts,
    TrainingConfigError,
    TrainingNotAuthorized,
    assert_training_authorized,
    build_training_plan,
    check_factory_compatibility,
    check_readout_pair,
    design_status,
    initialize,
    load_training_artifacts,
    prepare_campaign_artifacts,
    read_artifact,
    read_manifest,
    run_training,
    validate_manifest,
    validate_pairing,
    validate_training_config,
    write_artifact,
)
from experiments.phase_8.training.artifacts import TRAINING_ROOT
from readout.features import MotorFeatureSpec
from readout.linear import BiasOnlyReadout, LinearReadout


@pytest.fixture(scope="session")
def phase8():
    return load_phase8_config()


@pytest.fixture(scope="session")
def training_config(phase8):
    return validate_training_config(phase8)


@pytest.fixture
def root(tmp_path):
    return tmp_path / "artifacts"


def write_fixture(
    root: Path,
    config,
    condition_id: str,
    *,
    campaign_seed: int = 1,
    training_seed: int = 1001,
):
    initialized = initialize(
        condition_id,
        campaign_seed=campaign_seed,
        training_seed=training_seed,
        master_seed=config.master_seed,
    )
    directory = write_artifact(root, initialized, config=config)
    return initialized, directory


def write_three(root: Path, config, *, campaign_seed: int = 1):
    return {
        condition: write_fixture(
            root, config, condition, campaign_seed=campaign_seed
        )
        for condition in ("F", "F_beta", "E")
    }


def pairing_for(*campaign_seeds: int) -> dict:
    pairing = {}
    next_training = 1001
    for seed in campaign_seeds:
        shared = next_training
        pairing[("F", seed)] = shared
        pairing[("F_beta", seed)] = shared
        next_training += 1
        pairing[("E", seed)] = next_training
        next_training += 1
        pairing[("E_full", seed)] = next_training
        next_training += 1
    return pairing


def load_fixture(root: Path, config, *, seeds=(1,), pairing=None):
    return load_training_artifacts(
        root,
        config=config,
        campaign_seeds=list(seeds),
        pairing=pairing,
        require_trained=False,
        allow_synthetic_fixtures=True,
    )


def resolved(phase8, n: int = 1):
    return replace(phase8.campaign, n_seeds_selected=n)


# ---------------------------------------------------------------------------
# configuration validation
# ---------------------------------------------------------------------------


def test_training_config_matches_rev4(training_config):
    config = training_config
    assert config.readout_episodes_per_seed == 20
    assert config.e_gradient_updates == 2000
    assert config.readout_init_std == 0.01
    assert (config.e_hidden_units, config.e_hidden_layers) == (64, 2)
    assert config.motor_n_features == MotorFeatureSpec().n_features == 3
    assert (config.e_n_features, config.e_full_n_features) == (7, 14)
    assert config.master_seed == 20261116
    assert all(entry["ok"] for entry in config.checks)
    assert config.sha256() == config.sha256()
    assert len(config.sha256()) == 64


def test_training_config_records_the_certified_protocol(training_config):
    identity = protocol_identity()
    assert training_config.protocol_sha256 == identity["sha256"]
    assert identity["matches_expected"] is True
    assert training_config.protocol_id == "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"


@pytest.mark.parametrize(
    "field,value",
    [
        ("readout_episodes_per_seed", 19),
        ("e_gradient_updates", 1999),
        ("master_seed", 1),
    ],
)
def test_training_config_rejects_declared_mismatch(phase8, field, value):
    campaign = replace(phase8.campaign, **{field: value})
    with pytest.raises(TrainingConfigError):
        validate_training_config(replace(phase8, campaign=campaign))


def test_training_config_is_deterministic(phase8):
    first = validate_training_config(phase8)
    second = validate_training_config(phase8)
    assert first.sha256() == second.sha256()


def test_training_config_rejects_a_different_protocol(phase8, monkeypatch):
    identity = protocol_identity()
    monkeypatch.setattr(
        "experiments.phase_8.training.config.protocol_identity",
        lambda: {**identity, "sha256": "0" * 64, "matches_expected": False},
    )
    with pytest.raises(TrainingConfigError):
        validate_training_config(phase8)


def test_training_config_rejects_a_changed_init_scale(phase8, monkeypatch):
    from experiments.phase_8.conditions import f_readout

    monkeypatch.setattr(f_readout, "DEFAULT_INIT_STD", 0.02)
    with pytest.raises(TrainingConfigError):
        validate_training_config(phase8)


# ---------------------------------------------------------------------------
# deterministic initialization and seed recording
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("condition_id", ["F", "F_beta", "E"])
def test_initialization_is_deterministic(training_config, condition_id):
    first = initialize(
        condition_id,
        campaign_seed=1,
        training_seed=1001,
        master_seed=training_config.master_seed,
    )
    second = initialize(
        condition_id,
        campaign_seed=1,
        training_seed=1001,
        master_seed=training_config.master_seed,
    )
    assert first.parameter_digest == second.parameter_digest
    assert first.state_digest == second.state_digest
    assert first.state.keys() == second.state.keys()
    for name in first.state:
        np.testing.assert_array_equal(first.state[name], second.state[name])


def test_initialization_changes_with_training_seed(training_config):
    first = initialize(
        "F", campaign_seed=1, training_seed=1001, master_seed=training_config.master_seed
    )
    second = initialize(
        "F", campaign_seed=1, training_seed=1002, master_seed=training_config.master_seed
    )
    assert first.state_digest != second.state_digest


def test_initialization_refuses_a_shared_training_seed(training_config):
    with pytest.raises(TrainingConfigError):
        initialize(
            "F",
            campaign_seed=7,
            training_seed=7,
            master_seed=training_config.master_seed,
        )


def test_seeds_are_recorded_separately(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    plan = seed_plan(manifest["master_seed"], "F", manifest["training_seed"])
    assert manifest["campaign_seed"] == 1
    assert manifest["training_seed"] == 1001
    assert manifest["init_seed"] == plan["learning"]
    assert manifest["init_seed"] != manifest["training_seed"]
    assert manifest["training_environment_seed"] == plan["environment"]
    assert manifest["training_config_sha256"] == training_config.sha256()


# ---------------------------------------------------------------------------
# condition separation and Fβ state independence
# ---------------------------------------------------------------------------


def test_f_and_fbeta_are_distinct_kinds(training_config, root):
    pairs = write_three(root, training_config)
    forward = read_artifact(pairs["F"][1], config=training_config)
    beta = read_artifact(pairs["F_beta"][1], config=training_config)
    assert isinstance(forward.model, LinearReadout)
    assert not isinstance(forward.model, BiasOnlyReadout)
    assert forward.model.state_independent is False
    assert isinstance(beta.model, BiasOnlyReadout)
    assert beta.model.state_independent is True
    assert [name for name, _ in beta.model.named_parameters()] == ["bias"]


def test_fbeta_state_independence_survives_reload(training_config, root):
    _, directory = write_fixture(root, training_config, "F_beta")
    artifact = read_artifact(directory, config=training_config)
    model = artifact.model
    model.assert_state_independent()
    width = int(artifact.manifest["n_features"])
    zero = np.zeros((1, width), dtype=np.float32)
    saturated = np.full((1, width), 1e6, dtype=np.float32)
    np.testing.assert_array_equal(model.logits(zero), model.logits(saturated))
    assert np.count_nonzero(artifact.state["fixed_feature_weights"]) == 0


def test_condition_substitution_is_rejected(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    with pytest.raises(ArtifactCompatibilityError):
        read_artifact(directory, config=training_config, expected_condition="F_beta")


def test_misplaced_artifact_directory_is_rejected(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    wrong = root / "F_beta" / "seed_1"
    wrong.parent.mkdir(parents=True)
    shutil.copytree(directory, wrong)
    with pytest.raises(ArtifactCompatibilityError):
        read_artifact(wrong, config=training_config)


def test_f_init_never_has_a_training_artifact(training_config):
    with pytest.raises(TrainingConfigError):
        initialize(
            "F_init",
            campaign_seed=1,
            training_seed=1001,
            master_seed=training_config.master_seed,
        )


def test_manifest_for_f_init_is_schema_rejected(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    payload = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    payload["condition_id"] = "F_init"
    (directory / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactSchemaError):
        read_manifest(directory)


# ---------------------------------------------------------------------------
# serialization and reload
# ---------------------------------------------------------------------------


def test_serialization_round_trip_preserves_models(training_config, root):
    features = np.linspace(-0.5, 0.5, MotorFeatureSpec().n_features, dtype=np.float32)
    for condition_id in ("F", "F_beta", "E"):
        initialized, directory = write_fixture(root, training_config, condition_id)
        artifact = read_artifact(directory, config=training_config)
        if condition_id in ("F", "F_beta"):
            before = initialized.model.logits(features)
            after = artifact.model.logits(features)
            np.testing.assert_array_equal(before, after)
        else:
            assert isinstance(artifact.model, ConventionalAgent)
            assert artifact.model.parameter_digest() == initialized.parameter_digest


def test_manifest_records_provenance_and_digests(training_config, root):
    initialized, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    assert manifest["origin"] == "synthetic_fixture"
    assert manifest["stage"] == "initialized"
    assert manifest["digest"]["trainable"] == initialized.parameter_digest
    assert manifest["digest"]["state"] == initialized.state_digest
    assert manifest["protocol"]["matches_expected"] is True
    assert manifest["created"]["tool"].startswith("experiments.phase_8.training")
    assert manifest["parameters"]["bytes"] == (
        directory / manifest["parameters"]["file"]
    ).stat().st_size


# ---------------------------------------------------------------------------
# schema and integrity refusals
# ---------------------------------------------------------------------------


def test_schema_rejects_missing_and_unknown_keys(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    missing = dict(manifest)
    missing.pop("digest")
    with pytest.raises(ArtifactSchemaError):
        validate_manifest(missing)
    extra = dict(manifest)
    extra["unexpected"] = 1
    with pytest.raises(ArtifactSchemaError):
        validate_manifest(extra)


def test_schema_rejects_wrong_width(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    manifest["n_features"] = 7
    with pytest.raises(ArtifactSchemaError):
        validate_manifest(manifest)


def test_schema_rejects_training_config_hash_mismatch(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    manifest["training_config"]["declared"]["e_gradient_updates"] = 1
    with pytest.raises(ArtifactSchemaError):
        validate_manifest(manifest)


def test_schema_rejects_synthetic_trained_stage(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    manifest = read_manifest(directory)
    manifest["stage"] = "trained"
    with pytest.raises(ArtifactSchemaError):
        validate_manifest(manifest)


def test_parameter_file_hash_mismatch_is_rejected(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    parameters = directory / "parameters.npz"
    with parameters.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        read_artifact(directory, config=training_config)


def test_state_digest_mismatch_is_rejected(training_config, root):
    _, directory = write_fixture(root, training_config, "F")
    payload = read_manifest(directory)
    parameters = directory / payload["parameters"]["file"]
    with np.load(parameters, allow_pickle=False) as data:
        state = {
            name: np.array(data[name], copy=True)
            for name in payload["parameter_names"]
        }
    state["bias"] = state["bias"] + 1.0
    parameters.unlink()
    np.savez_compressed(parameters, **{name: state[name] for name in sorted(state)})
    payload["parameters"]["sha256"] = hashlib.sha256(
        parameters.read_bytes()
    ).hexdigest()
    payload["parameters"]["bytes"] = parameters.stat().st_size
    (directory / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        read_artifact(directory, config=training_config)


def test_missing_manifest_is_rejected(training_config, tmp_path):
    empty = tmp_path / "no-artifact"
    empty.mkdir()
    with pytest.raises(ArtifactCompatibilityError):
        read_artifact(empty, config=training_config)


# ---------------------------------------------------------------------------
# loader and factory compatibility
# ---------------------------------------------------------------------------


def test_loader_requires_trained_origin(training_config, root):
    write_three(root, training_config)
    with pytest.raises(ArtifactCompatibilityError):
        load_training_artifacts(
            root, config=training_config, campaign_seeds=[1]
        )


def test_loader_requires_explicit_fixture_permission(training_config, root):
    write_three(root, training_config)
    with pytest.raises(ArtifactCompatibilityError):
        load_training_artifacts(
            root,
            config=training_config,
            campaign_seeds=[1],
            require_trained=False,
            allow_synthetic_fixtures=False,
        )


def test_loader_rejects_missing_required_artifact(training_config, root):
    write_fixture(root, training_config, "F")
    write_fixture(root, training_config, "F_beta")
    with pytest.raises(ArtifactCompatibilityError):
        load_fixture(root, training_config)


def test_loader_can_validate_a_partial_seed(training_config, root):
    write_fixture(root, training_config, "F")
    loaded = load_training_artifacts(
        root,
        config=training_config,
        campaign_seeds=[1],
        conditions=("F",),
        require_trained=False,
        allow_synthetic_fixtures=True,
        require_complete=False,
    )
    assert set(loaded.artifacts) == {("F", 1)}
    assert loaded.report["required_conditions"] == ["F"]
    assert loaded.report["complete"] is True
    assert loaded.report["missing"] == []


def test_f_and_fbeta_must_share_their_training_run(training_config, root):
    write_fixture(root, training_config, "F", training_seed=1001)
    write_fixture(root, training_config, "F_beta", training_seed=1002)
    write_fixture(root, training_config, "E", training_seed=1003)
    with pytest.raises(ArtifactCompatibilityError):
        load_training_artifacts(
            root,
            config=training_config,
            campaign_seeds=[1],
            require_trained=False,
            allow_synthetic_fixtures=True,
        )


def test_loaded_fixtures_are_factory_compatible(training_config, root):
    write_three(root, training_config)
    loaded = load_fixture(root, training_config)
    assert set(loaded.training.describe()["readouts"]) == {"F:1", "F_beta:1"}
    assert loaded.training.describe()["agents"] == ["E:1"]
    factory = CampaignFactory(training=loaded.training)
    report = check_factory_compatibility(loaded, factory)
    assert all(entry["same_object"] for entry in report["checked"])
    assert {entry["condition_id"] for entry in report["checked"]} == {
        "F",
        "F_beta",
        "E",
    }
    with pytest.raises(FactoryError):
        factory.training.readout("F", 2)


def test_factory_width_mismatch_is_rejected(training_config, root):
    write_fixture(root, training_config, "F")
    loaded = load_training_artifacts(
        root,
        config=training_config,
        campaign_seeds=[1],
        conditions=("F",),
        require_trained=False,
        allow_synthetic_fixtures=True,
        require_complete=False,
    )
    wrong_model = LinearReadout(5, seed=0)
    wrong = LoadedArtifacts(
        training=TrainingArtifacts(readouts={("F", 1): wrong_model}),
        artifacts={("F", 1): replace(loaded.artifacts[("F", 1)], model=wrong_model)},
        manifests=loaded.manifests,
        report=loaded.report,
    )
    factory = CampaignFactory(training=wrong.training)
    with pytest.raises(ArtifactCompatibilityError):
        check_factory_compatibility(wrong, factory)


def test_readout_pair_check_requires_f_and_fbeta(training_config, root):
    _, forward_dir = write_fixture(root, training_config, "F")
    _, beta_dir = write_fixture(root, training_config, "F_beta")
    forward = read_manifest(forward_dir)
    beta = read_manifest(beta_dir)
    assert check_readout_pair(forward, beta)["paired"] is True
    with pytest.raises(ArtifactCompatibilityError):
        check_readout_pair(beta, forward)


# ---------------------------------------------------------------------------
# design gate, pairing and unauthorized training
# ---------------------------------------------------------------------------


def test_null_design_is_identified_and_blocks_preparation(phase8, training_config, root):
    status = design_status(phase8.campaign)
    assert status["field"] == "design.n_seeds_selected"
    assert status["value"] is None
    assert status["resolved"] is False
    assert status["active_seeds"] == []
    write_three(root, training_config)
    with pytest.raises(DesignUnresolvedError):
        prepare_campaign_artifacts(phase8, root, pairing=pairing_for(1))
    with pytest.raises(DesignUnresolvedError):
        build_training_plan(training_config, phase8.campaign, pairing_for(1))


def test_plan_expands_the_declared_budgets(phase8, training_config):
    campaign = resolved(phase8, n=2)
    pairing = pairing_for(1, 2)
    plan = build_training_plan(training_config, campaign, pairing)
    assert plan.execution_authorized is False
    assert plan.describe()["n_entries"] == 8
    assert plan.sha256() == build_training_plan(
        training_config, campaign, pairing
    ).sha256()
    entries = {(entry.condition_id, entry.campaign_seed): entry for entry in plan.entries}
    for condition in ("F", "F_beta"):
        assert entries[(condition, 1)].budget == {
            "kind": "training_episodes",
            "value": 20,
        }
        assert entries[(condition, 1)].substrate == "biological"
    for condition in ("E", "E_full"):
        assert entries[(condition, 1)].budget == {
            "kind": "gradient_updates",
            "value": 2000,
        }
        assert entries[(condition, 1)].substrate == "none"
    assert entries[("E_full", 1)].role == "exploratory"
    assert entries[("E", 1)].role == "confirmatory"
    for seed in (1, 2):
        assert entries[("F", seed)].training_seed == entries[("F_beta", seed)].training_seed


def test_pairing_must_be_explicit_and_complete(training_config):
    complete = pairing_for(1)
    missing = dict(complete)
    missing.pop(("E", 1))
    with pytest.raises(TrainingConfigError):
        validate_pairing(
            missing,
            campaign_seeds=[1],
            training_seeds=training_config.training_seeds,
        )
    mismatch = dict(complete)
    mismatch[("F_beta", 1)] = 1002
    with pytest.raises(TrainingConfigError):
        validate_pairing(
            mismatch,
            campaign_seeds=[1],
            training_seeds=training_config.training_seeds,
        )
    undeclared = dict(complete)
    undeclared[("F", 1)] = 9999
    with pytest.raises(TrainingConfigError):
        validate_pairing(
            undeclared,
            campaign_seeds=[1],
            training_seeds=training_config.training_seeds,
        )


def test_training_is_never_authorized(phase8, training_config, root):
    with pytest.raises(TrainingNotAuthorized):
        assert_training_authorized()
    plan = build_training_plan(training_config, resolved(phase8, n=1), pairing_for(1))
    with pytest.raises(TrainingNotAuthorized):
        run_training(plan, root=root)
    assert not root.exists()


def test_trained_artifact_writes_are_refused(training_config, root):
    initialized = initialize(
        "F",
        campaign_seed=1,
        training_seed=1001,
        master_seed=training_config.master_seed,
    )
    with pytest.raises(TrainingNotAuthorized):
        write_artifact(root, initialized, config=training_config, origin="trained")
    assert not (root / "F").exists()
    with pytest.raises(ArtifactSchemaError):
        write_artifact(
            root, initialized, config=training_config, stage="trained"
        )
    assert not (root / "F").exists()


def test_real_training_storage_holds_only_authorized_trained_artifacts():
    """Real storage may exist only from an owner-authorized training run.

    Synthetic fixtures are infrastructure evidence, never experimental
    evidence, so a fixture must never leak into the real training root.
    """
    root = PROJECT_ROOT / TRAINING_ROOT
    if not root.exists():
        return
    manifests = sorted(root.glob("*/seed_*/manifest.json"))
    assert manifests, "the real training root must hold authorized artifacts"
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["origin"] == "trained", path
        assert manifest["stage"] == "trained", path
        provenance = json.loads(
            (path.parent / "training_run.json").read_text(encoding="utf-8")
        )
        assert provenance["evidence_kind"] == "experimental", path
