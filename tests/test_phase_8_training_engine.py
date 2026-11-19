"""Focused synthetic tests for the Phase 8 G4 training engine.

Every test runs on a tiny caller-supplied fixture: a fake motor block for the
readout loop and a fake five-tuple game for the conventional loop. No BANC
graph is loaded, no game episode runs, no real training is authorised and no
trained artifact is generated. Checkpoints go to ``tmp_path`` only.

These are mechanism tests (G4 brief §6), not experimental evidence.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from evaluation.conventional import ConventionalAgent
from experiments.phase_8.campaign.factory import (
    CampaignFactory,
    FactoryError,
    TrainingArtifacts,
)
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.training import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    ArtifactSchemaError,
    RestoredCheckpoint,
    TrainingConfigError,
    TrainingError,
    TrainingNotAuthorized,
    TrainingRunContext,
    build_training_plan,
    checkpoint_directory,
    describe_checkpoint_interface,
    describe_engine,
    initialize,
    protocol_context,
    read_checkpoint,
    restore_checkpoint,
    run_training,
    synthetic_context,
    train_agent,
    train_readout,
    validate_training_config,
    write_checkpoint,
)
from motor.populations import ACTION_POPULATIONS
from readout.linear import BiasOnlyReadout, LinearReadout

ACTION_SPACE = ("LEFT", "RIGHT", "JUMP", "NO_ACTION")


@pytest.fixture(scope="session")
def phase8():
    return load_phase8_config()


@pytest.fixture(scope="session")
def training_config(phase8):
    return validate_training_config(phase8)


@pytest.fixture
def populations():
    return SimpleNamespace(n_neurons=1, note="accounting-only fixture")


def fixture_episode(*, controller, episode, environment_seed, max_decisions):
    """A deterministic fake training episode: motor blocks plus a reward."""
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
        reward = float(rng.normal())
        controller.record_reward(reward)
        total += reward
    return {"fixture_reward": round(total, 9), "fixture_decisions": int(max_decisions)}


def seed_at(base: int):
    return lambda episode: base + int(episode)


class TinyGame:
    """Deterministic five-tuple game stand-in with a fixed horizon."""

    def __init__(self, *, horizon: int = 2, width: int = 7):
        self.horizon = int(horizon)
        self.width = int(width)
        self.game_state = np.zeros(self.width, dtype=np.float32)
        self.reset_seeds: list[int] = []
        self.actions: list[str] = []
        self._rng = np.random.default_rng(0)
        self._steps = 0

    def reset(self, *, seed=None):
        self.reset_seeds.append(int(seed))
        self._rng = np.random.default_rng(int(seed))
        self._steps = 0
        self.game_state = self._rng.random(self.width).astype(np.float32)
        return self.game_state, {}

    def step(self, action):
        assert action in ACTION_SPACE, action
        self.actions.append(action)
        self._steps += 1
        terminated = self._steps >= self.horizon
        reward = float(self._rng.normal())
        self.game_state = self._rng.random(self.width).astype(np.float32)
        return self.game_state, reward, terminated, False, {
            "termination_reason": "horizon" if terminated else None
        }


class FakeEncoder:
    def __init__(self, n_features: int = 7):
        self.n_features = int(n_features)

    def encode(self, state):
        return np.asarray(state, dtype=np.float32).reshape(-1)[: self.n_features]


def readout_run(
    training_config,
    condition="F",
    *,
    episodes=3,
    decisions=2,
    campaign_seed=1,
    training_seed=1001,
    sampling_seed=0,
    base_seed=500,
    populations=None,
    checkpoint_every=None,
    checkpoint_root=None,
    resume=None,
):
    initialized = initialize(
        condition,
        campaign_seed=campaign_seed,
        training_seed=training_seed,
        master_seed=training_config.master_seed,
    )
    return train_readout(
        initialized,
        config=training_config,
        context=synthetic_context(episodes=episodes, label="readout fixture"),
        populations=populations or SimpleNamespace(),
        episode_runner=fixture_episode,
        environment_seed_for_episode=seed_at(base_seed),
        max_decisions_per_episode=decisions,
        sampling_seed=sampling_seed,
        resume=resume,
        checkpoint_every=checkpoint_every,
        checkpoint_root=checkpoint_root,
    )


def agent_run(
    training_config,
    *,
    updates=4,
    decisions=3,
    horizon=2,
    campaign_seed=1,
    training_seed=1002,
    base_seed=700,
    max_episodes=20,
    checkpoint_every=None,
    checkpoint_root=None,
    resume=None,
):
    initialized = initialize(
        "E",
        campaign_seed=campaign_seed,
        training_seed=training_seed,
        master_seed=training_config.master_seed,
    )
    environment = TinyGame(horizon=horizon, width=training_config.e_n_features)
    return train_agent(
        initialized,
        config=training_config,
        context=synthetic_context(updates=updates, label="agent fixture"),
        environment=environment,
        encoder=FakeEncoder(training_config.e_n_features),
        environment_seed_for_episode=seed_at(base_seed),
        max_decisions_per_episode=decisions,
        max_episodes=max_episodes,
        resume=resume,
        checkpoint_every=checkpoint_every,
        checkpoint_root=checkpoint_root,
    )


# ---------------------------------------------------------------------------
# context and refusal
# ---------------------------------------------------------------------------


def test_synthetic_context_is_the_only_constructible_context():
    context = synthetic_context(episodes=2)
    assert context.synthetic is True
    assert context.episodes == 2
    with pytest.raises(TrainingNotAuthorized):
        protocol_context(episodes=20)
    with pytest.raises(TrainingError, match="mode must be"):
        TrainingRunContext(mode="whatever")


def test_protocol_context_consults_the_same_gate():
    from experiments.phase_8.training import gate

    with pytest.raises(TrainingNotAuthorized, match="protocol sha256"):
        protocol_context()
    assert gate.training_authorization_status()["training_authorized"] is False


def test_plan_entry_point_still_refuses(phase8, training_config):
    campaign = replace(phase8.campaign, n_seeds_selected=1)
    pairing = {
        ("F", 1): 1001,
        ("F_beta", 1): 1001,
        ("E", 1): 1002,
        ("E_full", 1): 1003,
    }
    plan = build_training_plan(training_config, campaign, pairing)
    with pytest.raises(TrainingNotAuthorized):
        run_training(plan)


# ---------------------------------------------------------------------------
# readout loop (F / Fβ)
# ---------------------------------------------------------------------------


def test_readout_loop_mechanics_and_budget_override(training_config):
    run = readout_run(training_config, "F", episodes=3, decisions=2)
    assert run.n_episodes == 3
    assert run.n_updates == 3
    assert run.budget == {
        "kind": "training_episodes",
        "value": 3,
        "declared_value": 20,
        "override": True,
    }
    assert [item["n_decisions"] for item in run.episodes] == [2, 2, 2]
    assert run.environment_seeds == (500, 501, 502)
    assert run.model is not None
    assert run.parameter_digest != run.initial_parameter_digest
    record = run.as_dict()
    assert record["training_executed"] is True
    assert record["training_authorized"] is False
    assert record["trained_artifact_written"] is False
    assert record["origin"] == "synthetic_fixture"
    assert record["checkpoints_written"] == 0


def test_readout_declared_budget_needs_no_override(training_config):
    run = readout_run(training_config, "F", episodes=None, decisions=1)
    assert run.n_episodes == 20
    assert run.budget["value"] == 20
    assert run.budget["override"] is False


def test_readout_run_is_deterministic(training_config):
    first = readout_run(training_config, "F", episodes=3)
    second = readout_run(training_config, "F", episodes=3)
    assert first.sha256() == second.sha256()
    assert first.parameter_digest == second.parameter_digest
    assert first.state_digest == second.state_digest


def test_fbeta_stays_state_independent_through_training(training_config):
    run = readout_run(training_config, "F_beta", episodes=2)
    model = run.model
    assert isinstance(model, BiasOnlyReadout)
    model.assert_state_independent()
    assert int(np.count_nonzero(model.fixed_feature_weights.detach().numpy())) == 0
    zero = np.zeros((1, 3), dtype=np.float32)
    saturated = np.full((1, 3), 1e6, dtype=np.float32)
    assert np.array_equal(model.logits(zero), model.logits(saturated))
    assert run.parameter_digest != run.initial_parameter_digest


def test_f_readout_remains_state_dependent(training_config):
    run = readout_run(training_config, "F", episodes=2)
    model = run.model
    assert isinstance(model, LinearReadout)
    assert model.state_independent is False
    left = model.logits(np.array([[1.0, 0.0, 0.0]], dtype=np.float32))
    right = model.logits(np.array([[0.0, 1.0, 0.0]], dtype=np.float32))
    assert not np.array_equal(left, right)


def test_readout_refuses_the_wrong_condition(training_config):
    initialized = initialize(
        "E",
        campaign_seed=1,
        training_seed=1002,
        master_seed=training_config.master_seed,
    )
    with pytest.raises(TrainingError, match="no training loop"):
        train_readout(
            initialized,
            config=training_config,
            context=synthetic_context(episodes=1),
            populations=SimpleNamespace(),
            episode_runner=fixture_episode,
            environment_seed_for_episode=seed_at(1),
            max_decisions_per_episode=1,
        )


def test_b_and_d_are_not_readout_training_conditions(training_config):
    for condition in ("B", "D"):
        with pytest.raises(TrainingConfigError):
            initialize(
                condition,
                campaign_seed=1,
                training_seed=1001,
                master_seed=training_config.master_seed,
            )


def test_readout_rejects_invalid_parameters(training_config):
    with pytest.raises(TrainingConfigError):
        synthetic_context(episodes=0)
    with pytest.raises(TrainingConfigError):
        readout_run(training_config, "F", episodes=1, decisions=0)
    with pytest.raises(TrainingConfigError, match="environment_seed"):
        readout_run(training_config, "F", episodes=2, base_seed=-5)
    with pytest.raises(TrainingConfigError, match="must be given together"):
        readout_run(training_config, "F", episodes=1, checkpoint_every=1)


# ---------------------------------------------------------------------------
# conventional loop (E / E-full)
# ---------------------------------------------------------------------------


def test_agent_loop_mechanics_and_update_budget(training_config):
    run = agent_run(training_config, updates=4, decisions=3, horizon=2)
    assert isinstance(run.model, ConventionalAgent)
    assert run.model.updates == 4
    assert run.model.episodes == 4
    assert run.n_updates == 4
    assert run.budget == {
        "kind": "gradient_updates",
        "value": 4,
        "declared_value": 2000,
        "override": True,
    }
    assert [item["steps"] for item in run.episodes] == [2, 2, 2, 2]
    assert [item["updates_after"] for item in run.episodes] == [1, 2, 3, 4]
    assert run.parameter_digest != run.initial_parameter_digest
    assert run.sampling_seed is None
    assert run.as_dict()["training_authorized"] is False


def test_agent_loop_is_deterministic(training_config):
    first = agent_run(training_config, updates=3)
    second = agent_run(training_config, updates=3)
    assert first.sha256() == second.sha256()
    assert first.parameter_digest == second.parameter_digest


def test_agent_loop_refuses_the_safety_bound(training_config):
    with pytest.raises(TrainingError, match="loop-safety bound"):
        agent_run(training_config, updates=5, max_episodes=2)


def test_agent_loop_stops_exactly_at_the_requested_budget(training_config):
    run = agent_run(training_config, updates=2)
    assert run.model.updates == 2
    assert run.n_updates == 2
    assert run.budget["value"] == 2


def test_agent_refuses_the_wrong_condition(training_config):
    initialized = initialize(
        "F",
        campaign_seed=1,
        training_seed=1001,
        master_seed=training_config.master_seed,
    )
    with pytest.raises(TrainingError, match="no training loop"):
        train_agent(
            initialized,
            config=training_config,
            context=synthetic_context(updates=1),
            environment=TinyGame(width=7),
            encoder=FakeEncoder(7),
            environment_seed_for_episode=seed_at(1),
            max_decisions_per_episode=1,
            max_episodes=3,
        )


def test_agent_refuses_the_wrong_encoder_width(training_config):
    initialized = initialize(
        "E",
        campaign_seed=1,
        training_seed=1002,
        master_seed=training_config.master_seed,
    )
    with pytest.raises(TrainingConfigError, match="encoder width"):
        train_agent(
            initialized,
            config=training_config,
            context=synthetic_context(updates=1),
            environment=TinyGame(width=3),
            encoder=FakeEncoder(3),
            environment_seed_for_episode=seed_at(1),
            max_decisions_per_episode=1,
            max_episodes=3,
        )


# ---------------------------------------------------------------------------
# checkpoints and resume
# ---------------------------------------------------------------------------


def test_readout_checkpoints_and_resume(training_config, tmp_path):
    root = tmp_path / "ckpt"
    run = readout_run(
        training_config,
        "F",
        episodes=2,
        checkpoint_every=1,
        checkpoint_root=root,
    )
    assert len(run.checkpoints) == 2
    first = read_checkpoint(run.checkpoints[0], config=training_config)
    assert first.progress["episodes_completed"] == 1
    assert first.manifest["rng"]["checkpointed"] is False
    assert first.manifest["optimizer"]["state_checkpointed"] is False
    restored = restore_checkpoint(
        run.checkpoints[-1], config=training_config, expected_condition="F"
    )
    assert isinstance(restored, RestoredCheckpoint)
    assert restored.progress["episodes_completed"] == 2
    assert restored.rng_restored is False
    assert restored.optimizer_state_restored is False

    resumed = readout_run(
        training_config,
        "F",
        episodes=4,
        sampling_seed=1,
        resume=restored,
    )
    assert resumed.resume["resumed"] is True
    assert resumed.resume["start_episode"] == 2
    assert resumed.n_episodes == 2
    assert resumed.environment_seeds == (502, 503)
    assert resumed.as_dict()["rng_restored"] is False
    assert resumed.parameter_digest != run.parameter_digest


def test_resumed_readout_is_reproducible(training_config, tmp_path):
    def once(root: Path):
        run = readout_run(
            training_config,
            "F",
            episodes=2,
            checkpoint_every=2,
            checkpoint_root=root,
        )
        restored = restore_checkpoint(
            run.checkpoints[-1], config=training_config, expected_condition="F"
        )
        return readout_run(
            training_config, "F", episodes=4, sampling_seed=7, resume=restored
        )

    first = once(tmp_path / "a")
    second = once(tmp_path / "b")
    assert first.sha256() == second.sha256()


def test_resume_seed_mismatch_is_refused(training_config, tmp_path):
    run = readout_run(
        training_config,
        "F",
        episodes=1,
        checkpoint_every=1,
        checkpoint_root=tmp_path / "ckpt",
    )
    restored = restore_checkpoint(
        run.checkpoints[-1], config=training_config, expected_condition="F"
    )
    with pytest.raises(TrainingConfigError, match="does not belong"):
        readout_run(
            training_config,
            "F",
            episodes=2,
            campaign_seed=2,
            resume=restored,
        )


def test_agent_checkpoints_and_resume(training_config, tmp_path):
    root = tmp_path / "ckpt"
    run = agent_run(
        training_config, updates=4, checkpoint_every=2, checkpoint_root=root
    )
    assert len(run.checkpoints) == 2
    restored = restore_checkpoint(
        run.checkpoints[-1], config=training_config, expected_condition="E"
    )
    assert restored.progress["updates_completed"] == 4
    resumed = agent_run(training_config, updates=6, resume=restored)
    assert resumed.resume["resumed"] is True
    assert resumed.resume["start_update"] == 4
    assert resumed.model.updates == 6
    assert resumed.n_updates == 2


def test_checkpoint_integrity_and_refusals(training_config, tmp_path):
    run = readout_run(
        training_config,
        "F",
        episodes=1,
        checkpoint_every=1,
        checkpoint_root=tmp_path / "ckpt",
    )
    directory = Path(run.checkpoints[0])
    parameters = directory / "parameters.npz"
    payload = np.load(parameters, allow_pickle=False)
    arrays = {name: payload[name] for name in payload.files}
    payload.close()
    arrays["bias"] = arrays["bias"] + 1.0
    np.savez_compressed(parameters, **arrays)
    with pytest.raises(ArtifactIntegrityError):
        read_checkpoint(directory, config=training_config)

    with pytest.raises(ArtifactCompatibilityError):
        read_checkpoint(
            run.checkpoints[0], config=training_config, expected_condition="E"
        )
    with pytest.raises(ArtifactSchemaError, match="already exists"):
        write_checkpoint(
            directory,
            run.model,
            config=training_config,
            condition_id="F",
            campaign_seed=1,
            training_seed=1001,
            init_seed=run.init_seed,
            master_seed=run.master_seed,
            progress={
                "episodes_completed": 1,
                "updates_completed": 1,
                "budget": run.budget,
                "environment_seeds_used": [500],
                "sampling_seed": run.sampling_seed,
                "metrics_sha256": run.sha256(),
            },
        )
    with pytest.raises(TrainingNotAuthorized):
        write_checkpoint(
            tmp_path / "trained",
            run.model,
            config=training_config,
            condition_id="F",
            campaign_seed=1,
            training_seed=1001,
            init_seed=run.init_seed,
            master_seed=run.master_seed,
            progress={
                "episodes_completed": 1,
                "updates_completed": 1,
                "budget": run.budget,
                "environment_seeds_used": [500],
                "sampling_seed": run.sampling_seed,
                "metrics_sha256": run.sha256(),
            },
            origin="trained",
        )


def test_no_checkpoint_is_written_without_a_policy(training_config, tmp_path):
    run = readout_run(training_config, "F", episodes=1)
    assert run.checkpoints == ()
    assert list(tmp_path.iterdir()) == []


def test_checkpoint_layout_is_declared(tmp_path):
    directory = checkpoint_directory(tmp_path, "F_beta", 3, 5)
    assert directory == tmp_path / "F_beta" / "seed_3" / "step_5"
    described = describe_checkpoint_interface()
    assert described["not_a_training_artifact"] is True
    assert described["loaded_by_campaign_loader"] is False
    assert described["rng_restored"] is False


# ---------------------------------------------------------------------------
# factory compatibility and declared interfaces
# ---------------------------------------------------------------------------


def test_run_models_are_accepted_by_the_factory_provider(training_config):
    readout = readout_run(training_config, "F", episodes=1)
    agent = agent_run(training_config, updates=1)
    training = TrainingArtifacts(
        readouts={("F", 1): readout.model},
        agents={("E", 1): agent.model},
        provenance="synthetic-fixture-run",
    )
    factory = CampaignFactory(training=training)
    assert factory.training.readout("F", 1) is readout.model
    assert factory.training.agent("E", 1) is agent.model
    with pytest.raises(FactoryError, match="training stage is implemented"):
        factory.neural_components(
            "F", seed=1, episode=0, environment_seed=1, training=True
        )
    with pytest.raises(FactoryError):
        factory.training.readout("E", 1)


def test_run_state_matches_the_model(training_config):
    from experiments.phase_8.training.state import model_state, state_digest

    run = readout_run(training_config, "F", episodes=1)
    assert run.state_digest == state_digest(model_state(run.model))
    assert run.parameter_digest == run.describe()["parameter_digest"]
    assert set(run.state) == {"feature_weights", "bias"}


def test_describe_engine_names_every_open_decision():
    described = describe_engine()
    names = {item["name"] for item in described["unresolved_inputs"]}
    assert names == {
        "campaign-to-training seed pairing",
        "training-episode environment seed schedule",
        "checkpoint cadence and retention",
        "sampler RNG and optimizer-state checkpointing",
    }
    assert described["training_authorized"] is False
    assert described["trained_artifacts_written_by_this_task"] == 0
    assert "B" in described["not_trained_here"]
    assert "D" in described["not_trained_here"]
    assert described["contexts"]["authorized_protocol"].startswith("refused")
