"""Focused tests for owner decision D4 and the B3-B6 training contracts.

Every test here is a mechanism test on synthetic fixtures or arithmetic on
declared seeds. No game episode runs, no BANC graph is built or read, no
training is authorised and no trained artifact is produced. Exact checkpoints
are written to ``tmp_path`` only and are always labelled
``origin = "synthetic_fixture"``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from experiments.phase_8.campaign.protocol import (
    AMENDMENT_PATH,
    OWNER_DECISION_D3_RECORD,
    PROTOCOL_PATH,
)
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.seeds import environment_seed
from experiments.phase_8.training import (
    B3_NAMESPACE,
    B4_NAMESPACE,
    D4_APPROVAL_DATE,
    D4_RECORD_PATH,
    ArtifactIntegrityError,
    ArtifactSchemaError,
    TrainingNotAuthorized,
    apply_exact_restore,
    assert_environment_stream_disjoint,
    assert_resumption_equivalent,
    capture_optimizer_state,
    d4_applicability,
    derive_b3_pairing,
    initialize,
    namespace_digest,
    namespace_seed,
    pairing_map,
    pilot2c_evaluation_environment_seeds,
    restore_exact_checkpoint,
    synthetic_context,
    train_readout,
    training_authorization_status,
    training_environment_schedule,
    training_environment_seed,
    validate_b3_pairing,
    validate_exact_checkpoint,
    validate_training_config,
    verify_equivalence,
)
from experiments.phase_8.training.exact_checkpoint import EXACT_COMPONENTS_NAME
from experiments.phase_8.training.gate import assert_training_authorized
from motor.populations import ACTION_POPULATIONS
from readout.controller import ReadoutController

MASTER = 20261116
EVALUATIONS = (9001, 9002, 9003)
POOL = tuple(range(1001, 1021))
ACTION_SPACE = ("LEFT", "RIGHT", "JUMP", "NO_ACTION")


@pytest.fixture(scope="session")
def training_config():
    return validate_training_config(load_phase8_config())


def fixture_episode(*, controller, episode, environment_seed, max_decisions):
    rng = np.random.default_rng(int(environment_seed))
    total = 0.0
    for _ in range(int(max_decisions)):
        block = {
            action: {
                "spikes": int(rng.integers(0, 3)),
                "active_neurons": 1,
                "active_fraction": float(rng.random()),
                "mean_rate_hz": float(rng.random() * 10.0),
            }
            for action in ACTION_POPULATIONS
        }
        block["any_motor_spike"] = any(
            block[action]["spikes"] > 0 for action in ACTION_POPULATIONS
        )
        controller.decide(block)
        controller.record_reward(float(rng.normal()))
        total += float(rng.normal())
    return {"fixture_reward": round(total, 9)}


def exact_run(
    training_config,
    *,
    condition="F",
    episodes=3,
    campaign_seed=9001,
    training_seed=1008,
    root=None,
    resume_exact=None,
):
    return train_readout(
        initialize(
            condition,
            campaign_seed=campaign_seed,
            training_seed=training_seed,
            master_seed=training_config.master_seed,
        ),
        config=training_config,
        context=synthetic_context(episodes=episodes, label="d4 contract fixture"),
        populations=SimpleNamespace(),
        episode_runner=fixture_episode,
        environment_seed_for_episode=None,
        max_decisions_per_episode=2,
        sampling_seed=0,
        resume_exact=resume_exact,
        exact_checkpoint_root=root,
    )


# ---------------------------------------------------------------------------
# 1. deterministic seed derivation
# ---------------------------------------------------------------------------


def test_b3_derivation_is_deterministic():
    first = derive_b3_pairing(EVALUATIONS, POOL, master_seed=MASTER)
    second = derive_b3_pairing(EVALUATIONS, POOL, master_seed=MASTER)
    assert first["sha256"] == second["sha256"]
    assert first["pairing"] == second["pairing"]
    for entry in first["entries"].values():
        expected = namespace_digest(B3_NAMESPACE, [MASTER, entry["evaluation_seed"]])
        assert entry["sha256"] == expected


def test_b4_derivation_is_deterministic():
    first = training_environment_schedule(MASTER, 1008, 20)
    second = training_environment_schedule(MASTER, 1008, 20)
    assert first == second
    assert len(set(first)) == len(first)
    assert first[0] == training_environment_seed(MASTER, 1008, 0)
    assert first[0] == namespace_seed(B4_NAMESPACE, [MASTER, 1008, 0])


# ---------------------------------------------------------------------------
# 2. namespace separation
# ---------------------------------------------------------------------------


def test_namespaces_never_collide():
    b3 = namespace_digest(B3_NAMESPACE, [MASTER, 9001])
    b4 = namespace_digest(B4_NAMESPACE, [MASTER, 9001, 0])
    assert b3 != b4
    # The frozen evaluation stream is a SeedSequence, not the B4 namespace.
    assert training_environment_seed(MASTER, 9001, 0) != environment_seed(
        MASTER, 9001, 0
    )
    # Changing the version string changes the derived value.
    assert namespace_seed("phase_8/training/B4/v2", [MASTER, 1008, 0]) != (
        namespace_seed(B4_NAMESPACE, [MASTER, 1008, 0])
    )


# ---------------------------------------------------------------------------
# 3. stable B3 pairing
# ---------------------------------------------------------------------------


def test_b3_pairing_is_stable_independent_of_input_order():
    straight = derive_b3_pairing(EVALUATIONS, POOL, master_seed=MASTER)
    shuffled = derive_b3_pairing((9003, 9001, 9002), POOL, master_seed=MASTER)
    assert straight["pairing"] == shuffled["pairing"]
    assert straight["sha256"] == shuffled["sha256"]
    chosen = [straight["entries"][str(seed)]["training_seed"] for seed in EVALUATIONS]
    assert len(set(chosen)) == len(chosen)
    assert set(chosen) <= set(POOL)
    # F and F_beta share the training seed and keep separate condition keys.
    for seed in EVALUATIONS:
        assert straight["pairing"][f"F:{seed}"] == straight["pairing"][f"F_beta:{seed}"]
    assert len(pairing_map(straight)) == 2 * len(EVALUATIONS)
    assert validate_b3_pairing(
        straight, evaluation_seeds=EVALUATIONS, training_seeds=POOL, master_seed=MASTER
    )["sha256"] == straight["sha256"]


def test_altered_b3_pairing_is_rejected():
    record = derive_b3_pairing(EVALUATIONS, POOL, master_seed=MASTER)
    record["entries"]["9001"]["training_seed"] = 1020
    with pytest.raises(Exception, match="does not match the declared derivation"):
        validate_b3_pairing(
            record,
            evaluation_seeds=EVALUATIONS,
            training_seeds=POOL,
            master_seed=MASTER,
        )


# ---------------------------------------------------------------------------
# 4. training / evaluation seed separation
# ---------------------------------------------------------------------------


def test_training_environment_stream_is_disjoint_from_pilot2c():
    schedule = training_environment_schedule(MASTER, 1008, 20)
    report = assert_environment_stream_disjoint(schedule, master_seed=MASTER)
    assert report["disjoint"] is True
    evaluation = set(
        pilot2c_evaluation_environment_seeds(MASTER, evaluation_seeds=EVALUATIONS)
    )
    assert evaluation & set(schedule) == set()
    assert set(schedule) & set(EVALUATIONS) == set()


def test_evaluation_seed_may_not_be_a_training_seed():
    with pytest.raises(Exception, match="never be reused as a training seed"):
        derive_b3_pairing((9001, 9002), (9001, 1001), master_seed=MASTER)


# ---------------------------------------------------------------------------
# 5. F / Fb artifact separation
# ---------------------------------------------------------------------------


def test_f_and_f_beta_are_separate_exact_artifacts(training_config, tmp_path):
    f_run = exact_run(training_config, condition="F", episodes=1, root=tmp_path / "f")
    beta_run = exact_run(
        training_config, condition="F_beta", episodes=1, root=tmp_path / "beta"
    )
    f_dir = Path(f_run.checkpoints[0])
    beta_dir = Path(beta_run.checkpoints[0])
    assert f_dir != beta_dir
    f_manifest = json.loads((f_dir / "checkpoint.json").read_text(encoding="utf-8"))
    beta_manifest = json.loads((beta_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert f_manifest["condition_id"] == "F"
    assert beta_manifest["condition_id"] == "F_beta"
    assert f_manifest["model_kind"] != beta_manifest["model_kind"]
    assert f_manifest["training_seed"] == beta_manifest["training_seed"] == 1008
    assert f_manifest["digest"]["trainable"] != beta_manifest["digest"]["trainable"]


# ---------------------------------------------------------------------------
# 6. per-episode checkpoint creation
# ---------------------------------------------------------------------------


def test_one_exact_checkpoint_per_completed_episode(training_config, tmp_path):
    run = exact_run(training_config, episodes=3, root=tmp_path / "ckpt")
    assert run.checkpoint_kind == "exact"
    assert len(run.checkpoints) == 3
    for index, directory in enumerate(run.checkpoints, start=1):
        manifest = json.loads(
            (Path(directory) / "checkpoint.json").read_text(encoding="utf-8")
        )
        assert manifest["progress"]["episodes_completed"] == index
        assert len(manifest["progress"]["episodes"]) == index
        assert manifest["b5"]["cadence"] == 1
        assert Path(directory).name == f"exact_step_{index}"


# ---------------------------------------------------------------------------
# 7. optimizer and RNG state persistence
# ---------------------------------------------------------------------------


def test_checkpoint_stores_optimizer_state_and_every_rng(training_config, tmp_path):
    run = exact_run(training_config, episodes=1, root=tmp_path / "ckpt")
    directory = Path(run.checkpoints[0])
    manifest = json.loads((directory / "checkpoint.json").read_text(encoding="utf-8"))
    assert manifest["rng"]["checkpointed"] is True
    for name in ("python", "numpy", "torch", "sampler"):
        assert manifest["rng"][name]["present"] is True
        assert len(manifest["rng"][name]["sha256"]) == 64
    assert manifest["optimizer"]["state_checkpointed"] is True
    assert manifest["optimizer"]["param_groups"][0]["lr"] > 0
    assert manifest["components"]["file"] == EXACT_COMPONENTS_NAME


def test_optimizer_moments_round_trip():
    parameter = torch.nn.Parameter(torch.tensor([1.0, 2.0]))
    optimizer = torch.optim.SGD([parameter], lr=0.1, momentum=0.9)
    (parameter.sum()).backward()
    optimizer.step()
    arrays, scalars = capture_optimizer_state(optimizer)
    assert arrays
    assert set(scalars["param_groups"][0]) >= {"lr", "momentum"}


def test_restored_optimizer_state_matches_the_checkpoint(training_config, tmp_path):
    run = exact_run(training_config, episodes=1, root=tmp_path / "ckpt")
    restored = restore_exact_checkpoint(
        run.checkpoints[0], config=training_config, expected_condition="F"
    )
    assert restored.optimizer_state_restored is True
    assert restored.rng_restored is True
    group = restored.optimizer_state["param_groups"][0]
    manifest = restored.manifest
    assert float(group["lr"]) == float(
        manifest["optimizer"]["param_groups"][0]["lr"]
    )


# ---------------------------------------------------------------------------
# 8. sampler restoration
# ---------------------------------------------------------------------------


def test_apply_exact_restore_restores_sampler_and_globals():
    controller = ReadoutController(
        model=None,
        populations=SimpleNamespace(),
        training=True,
        seed=7,
    )
    source = np.random.default_rng(123)
    expected = [int(source.choice(4)) for _ in range(5)]

    restored_rng = np.random.default_rng(0)
    restored_rng.bit_generator.state = np.random.default_rng(123).bit_generator.state

    from experiments.phase_8.training.exact_checkpoint import (
        RestoredExactCheckpoint,
        ExactCheckpoint,
    )

    target = torch.optim.SGD([torch.nn.Parameter(torch.zeros(2))], lr=1.0)
    optimizer_state = target.state_dict()
    optimizer_state["param_groups"][0]["lr"] = 0.01
    probe = RestoredExactCheckpoint(
        checkpoint=ExactCheckpoint(
            directory="<memory>",
            manifest={"rng": {"environment_present": False}},
            state={},
            optimizer_arrays={},
            optimizer_scalars={"param_groups": [{"lr": 0.01}], "state": {}},
            rng={"environment_present": False},
        ),
        model=object(),
        state={},
        optimizer_state=optimizer_state,
        python_rng=None,
        numpy_rng=None,
        torch_rng=None,
        sampler_state=restored_rng.bit_generator.state,
        environment_state=None,
        parameter_digest="0" * 64,
        state_digest="0" * 64,
    )
    applied = apply_exact_restore(target, controller.sampler, probe)
    assert applied["sampler_state_restored"] is True
    assert applied["environment_state_present"] is False
    assert controller.sampler.bit_generator.state == restored_rng.bit_generator.state
    draw = np.random.default_rng(123)
    starts_aligned = [
        int(controller.sampler.choice(4)) for _ in range(5)
    ] == [int(draw.choice(4)) for _ in range(5)]
    assert starts_aligned
    assert float(target.param_groups[0]["lr"]) == 0.01
    assert expected  # the source stream itself is deterministic


# ---------------------------------------------------------------------------
# 9. checkpoint corruption detection
# ---------------------------------------------------------------------------


def test_corrupted_parameter_bytes_are_refused(training_config, tmp_path):
    run = exact_run(training_config, episodes=1, root=tmp_path / "ckpt")
    directory = Path(run.checkpoints[0])
    parameters = directory / "parameters.npz"
    payload = bytearray(parameters.read_bytes())
    payload[-8] ^= 0xFF
    parameters.write_bytes(bytes(payload))
    with pytest.raises(ArtifactIntegrityError, match="parameter file"):
        restore_exact_checkpoint(directory, config=training_config)


def test_missing_component_file_is_refused(training_config, tmp_path):
    run = exact_run(training_config, episodes=1, root=tmp_path / "ckpt")
    directory = Path(run.checkpoints[0])
    (directory / EXACT_COMPONENTS_NAME).unlink()
    with pytest.raises(ArtifactIntegrityError, match="component file is missing"):
        restore_exact_checkpoint(directory, config=training_config)


# ---------------------------------------------------------------------------
# 10. uninterrupted versus resumed equivalence
# ---------------------------------------------------------------------------


def test_exact_resume_matches_an_uninterrupted_run(training_config, tmp_path):
    uninterrupted = exact_run(training_config, episodes=3, root=tmp_path / "full")
    partial = exact_run(training_config, episodes=2, root=tmp_path / "part")
    restored = restore_exact_checkpoint(
        partial.checkpoints[-1], config=training_config, expected_condition="F"
    )
    resumed = exact_run(training_config, episodes=3, resume_exact=restored)
    report = verify_equivalence(uninterrupted, resumed)
    assert report["equivalent"] is True
    assert report["differences"] == []
    assert report["compared_episodes"] == 3
    assert report["exactness_claim"] == "demonstrated"
    assert assert_resumption_equivalent(uninterrupted, resumed)["equivalent"] is True
    assert resumed.rng_restored is True
    assert resumed.optimizer_state_restored is True
    assert resumed.parameter_digest == uninterrupted.parameter_digest


def test_a_divergent_resume_is_not_claimed_equivalent(training_config, tmp_path):
    uninterrupted = exact_run(training_config, episodes=2, root=tmp_path / "full")
    partial = exact_run(training_config, episodes=1, root=tmp_path / "part")
    restored = restore_exact_checkpoint(
        partial.checkpoints[-1], config=training_config, expected_condition="F"
    )
    # The restored state is complete, but resuming under a different environment
    # seed for the remaining episode produces a different trajectory; the
    # verifier must refuse the exactness claim rather than assume it.
    resumed = train_readout(
        initialize(
            "F",
            campaign_seed=9001,
            training_seed=1008,
            master_seed=training_config.master_seed,
        ),
        config=training_config,
        context=synthetic_context(episodes=2),
        populations=SimpleNamespace(),
        episode_runner=fixture_episode,
        environment_seed_for_episode=lambda episode: (
            training_environment_seed(MASTER, 1008, episode) + 1
        ),
        max_decisions_per_episode=2,
        sampling_seed=0,
        resume_exact=restored,
    )
    report = verify_equivalence(uninterrupted, resumed)
    assert report["equivalent"] is False
    assert any("environment seeds used differ" in item for item in report["differences"])
    assert report["exactness_claim"] == "refused"
    with pytest.raises(Exception, match="not equivalent"):
        assert_resumption_equivalent(uninterrupted, resumed)


# ---------------------------------------------------------------------------
# 11. rejection of incomplete artifacts
# ---------------------------------------------------------------------------


def _manifest(training_config, tmp_path) -> dict:
    run = exact_run(training_config, episodes=1, root=tmp_path / "ckpt")
    source = Path(run.checkpoints[0]) / "checkpoint.json"
    return json.loads(source.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda m: m["rng"].update({"checkpointed": False}), "B6 requires every RNG"),
        (lambda m: m["rng"]["python"].update({"present": False}), "python RNG"),
        (lambda m: m["rng"]["sampler"].update({"present": False}), "sampler RNG"),
        (
            lambda m: m["optimizer"].update({"state_checkpointed": False}),
            "optimizer state",
        ),
        (
            lambda m: m["rng"].update(
                {
                    "environment": {
                        "present": False,
                        "sha256": None,
                        "reason": "",
                    }
                }
            ),
            "absent environment",
        ),
        (lambda m: m["progress"].update({"episodes": []}), "episodes disagrees"),
        (
            lambda m: m["digest"].update({"optimizer": "not-a-digest"}),
            "64-hex digest",
        ),
    ],
)
def test_incomplete_exact_manifests_are_refused(
    training_config, tmp_path, mutation, message
):
    manifest = _manifest(training_config, tmp_path)
    mutation(manifest)
    with pytest.raises(ArtifactSchemaError, match=message):
        validate_exact_checkpoint(manifest)


# ---------------------------------------------------------------------------
# 12. D4 record binding and approval validation
# ---------------------------------------------------------------------------


def test_d4_is_valid_and_bound_to_the_frozen_sources():
    report = d4_applicability()
    assert report["valid"] is True
    assert report["applicable"] is True
    assert report["approval_id"] == "D4"
    assert report["approval_date"] == D4_APPROVAL_DATE == "2026-11-21"
    assert set(report["decisions"]) == {"B3", "B4", "B5", "B6"}
    assert report["bound_to_rev4"] is True
    assert report["bound_to_amendment"] is True
    assert report["bound_to_d3"] is True
    assert report["training_execution_authorized"] is False


def test_d4_declares_but_does_not_authorise_training():
    status = training_authorization_status()
    assert status["training_authorized"] is False
    assert set(status["declared_decisions"]) == {"B3", "B4", "B5", "B6"}
    assert all(not item.startswith("B3:") for item in status["blockers"])
    assert any(item[:2] in {"B2", "B7"} for item in status["blockers"])
    with pytest.raises(TrainingNotAuthorized):
        assert_training_authorized()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"approval_date": "2026-11-20"}),
        lambda payload: payload.update({"approval_id": "D5"}),
        lambda payload: payload["frozen_sources"]["rev4"].update(
            {"sha256": "0" * 64}
        ),
        lambda payload: payload["scope"].update(
            {"authorises_training_execution": True}
        ),
        lambda payload: payload["owner_decisions"].pop(),
        lambda payload: payload["does_not_authorise"].remove("a training run"),
    ],
)
def test_altered_d4_records_are_refused(tmp_path, mutation):
    payload = json.loads(Path(D4_RECORD_PATH).read_text(encoding="utf-8"))
    mutation(payload)
    altered = tmp_path / "D4.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    report = d4_applicability(record_path=altered)
    assert report["applicable"] is False
    assert report["failures"]


def test_changed_frozen_source_unbinds_d4(tmp_path):
    altered = tmp_path / "REV4.md"
    altered.write_text(PROTOCOL_PATH.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = d4_applicability(protocol_path=altered)
    assert report["bound_to_rev4"] is False
    assert report["applicable"] is False


def test_missing_d4_record_is_refused(tmp_path):
    report = d4_applicability(record_path=tmp_path / "absent.json")
    assert report["present"] is False
    assert report["applicable"] is False


def test_d4_binds_the_amendment_and_d3_it_records():
    from brain.banc_graph import sha256_file

    payload = json.loads(Path(D4_RECORD_PATH).read_text(encoding="utf-8"))
    assert payload["frozen_sources"]["amendment"]["sha256"] == sha256_file(
        AMENDMENT_PATH
    )
    assert payload["frozen_sources"]["d3"]["sha256"] == sha256_file(
        OWNER_DECISION_D3_RECORD
    )
    assert payload["depends_on"]["record_sha256"] == payload["frozen_sources"]["d3"][
        "sha256"
    ]


def test_exact_manifest_is_never_a_training_artifact(training_config, tmp_path):
    manifest = _manifest(training_config, tmp_path)
    assert manifest["origin"] == "synthetic_fixture"
    assert manifest["stage"] == "training_checkpoint"
    assert manifest["b6"]["exactness_claimed"] is False
    assert "training_authorized" not in manifest
    assert copy.deepcopy(manifest)["owner_decision"] == "D4"
