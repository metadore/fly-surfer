"""Production F/Fβ pilot training on the frozen biological substrate.

SCIENTIFIC STATUS
    This is the only code path that runs a Phase 8 training episode. It drives
    the existing Phase 7 closed loop (game -> sensory encoding -> BANC LIF ->
    per-decision motor block -> readout -> game update) with a trainable
    readout, then applies exactly one declared REINFORCE update per episode to
    the readout parameters only. Every synaptic weight stays frozen; a nonzero
    readout update is not synaptic plasticity and a readout label is not an
    identified biological motor command.

    D5 authorises exactly six artifacts (F and Fβ at evaluation seeds 9001,
    9002, 9003, twenty episodes each). :func:`run_pilot_artifact` refuses
    anything else. :func:`run_pilot_plan` runs all six and never overwrites an
    existing artifact.

    Checkpoints follow D4 B5/B6: one exact checkpoint after every completed
    episode, every intermediate and the final checkpoint retained, each carrying
    parameters, optimizer state and moments, Python/NumPy/PyTorch RNG, the
    action-sampler state, and the applicable environment provenance. A
    checkpoint is the frozen B5 format (``origin = "synthetic_fixture"``,
    ``stage = "training_checkpoint"``); it is not an experimental artifact.
    Loading trains nothing until :func:`run_pilot_artifact` is called.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from brain.banc_graph import sha256_file
from environment.environment_adapter import GameEnvironmentAdapter
from environment.live_loop import ClockSync, NeuralClosedLoop
from readout.trainer import ReinforceConfig

from ..campaign.factory import CampaignFactory, FactorySettings
from ..conditions import f_readout
from ..controls import f_beta
from .artifacts import artifact_directory
from .config import TrainingConfig, canonical_json, sha256_text, validate_training_config
from .contracts import (
    B4_NAMESPACE,
    CONTRACT_VERSION,
    assert_environment_stream_disjoint,
    training_environment_seed,
)
from .d5 import (
    PILOT_TRAINING_CONDITIONS,
    PILOT_TRAINING_EPISODES,
    assert_d5_training_authorized,
)
from .errors import (
    ArtifactCompatibilityError,
    ArtifactSchemaError,
    TrainingConfigError,
    TrainingError,
    TrainingNotAuthorized,
)
from .exact_checkpoint import (
    EXACT_CHECKPOINT_NAME,
    apply_exact_restore,
    assert_resumption_equivalent,
    read_exact_checkpoint,
    restore_exact_checkpoint,
    write_exact_checkpoint,
)
from .initialization import InitializedModel, initialize
from .pilot import (
    PILOT_SUBSTRATE,
    PilotArtifactPlan,
    PilotTrainingPlan,
    build_pilot_plan,
)
from .pilot_artifact import write_trained_artifact
from .state import model_state, state_digest, trainable_digest
from .validation import MANIFEST_NAME, PARAMETERS_NAME

RUNNER_ID = "experiments.phase_8.training.pilot_training.PilotEpisodeRunner"

#: Recorded in every checkpoint. The controlled game is rebuilt and reset from
#: its B4 seed at each episode start, so no environment RNG state survives the
#: episode boundary; the B4 seed is the applicable environment provenance.
ENVIRONMENT_REASON = (
    "the controlled game is reconstructed and reset from its B4 episode seed "
    "at the start of every episode; no environment RNG state survives the "
    "episode boundary, so the applicable environment provenance is the B4 seed "
    "recorded in progress.environment_seeds_used"
)

#: The per-episode fields an uninterrupted and a resumed run must share.
PINNED_EPISODE_FIELDS = (
    "n_decisions",
    "steps",
    "updates_applied",
    "updates_after",
    "loss",
    "mean_return",
    "episode_reward",
    "policy_loss",
    "value_loss",
    "entropy",
    "grad_norm",
    "parameter_digest_after",
)


class PilotEpisodeRunner:
    """Run one training episode of F or Fβ and return JSON-safe metrics.

    ``factory`` must expose the :class:`CampaignFactory` surface
    (``world``, ``settings``, ``graph_and_policy``, ``_sensory``,
    ``_fixed_stepper``, ``environment``). The default in
    :func:`run_pilot_artifact` is the real factory; tests inject a factory over
    the 32-node fixture. Every heavy component is rebuilt per episode and the
    per-update record list is dropped after the summary is extracted.
    """

    def __init__(self, factory: Any) -> None:
        self.factory = factory

    @property
    def settings(self) -> FactorySettings:
        return self.factory.settings

    def run_episode(
        self,
        condition_id: str,
        *,
        evaluation_seed: int,
        episode: int,
        environment_seed: int,
        network_seed: int,
        controller: Any,
    ) -> dict:
        condition = str(condition_id)
        if condition not in PILOT_TRAINING_CONDITIONS:
            raise TrainingNotAuthorized(
                f"D5 authorises F and F_beta only; {condition!r} is outside its scope"
            )
        if getattr(controller, "training", False) is not True:
            raise TrainingError(
                "a training episode needs a readout controller in training mode"
            )
        settings = self.settings
        graph, policy, structure = self.factory.graph_and_policy(
            condition, int(evaluation_seed)
        )
        if structure is not None:
            raise TrainingError(
                "the pilot training substrate is the frozen biological graph; a "
                "certified randomized structure is refused"
            )
        populations = self.factory.world.populations
        _mapping, drive = self.factory._sensory()
        clock = ClockSync(
            neural_dt_ms=float(settings.neural_dt_ms),
            game_dt_s=float(settings.game_dt_s),
        )
        stepper = self.factory._fixed_stepper(
            graph, policy, drive, int(network_seed)
        )
        adapter = GameEnvironmentAdapter(environment=self.factory.environment())
        loop = NeuralClosedLoop(
            adapter,
            stepper,
            drive,
            None,
            clock=clock,
            window_ms=float(settings.window_ms),
            max_updates=int(settings.max_game_updates),
            decision_source=controller,
            record_motor_activity=True,
        )
        if int(getattr(populations, "n_neurons", -1)) != int(stepper.n_neurons):
            raise TrainingError("motor populations and the neural graph disagree")

        output = loop.run(seed=int(environment_seed))
        summary = output["summary"]
        weights_before = dict(summary["weights_before"])
        weights_after = dict(summary["weights_after"])
        metrics = {
            "episode": int(episode) + 1,
            "environment_seed": int(environment_seed),
            "network_seed": int(network_seed),
            "game_updates": int(summary["updates"]),
            "neural_steps": int(summary["neural_steps"]),
            "total_spikes": int(summary["total_spikes"]),
            "motor_spikes": int(summary["motor_spikes"]),
            "action_counts": {
                str(name): int(count)
                for name, count in dict(summary["action_counts"]).items()
            },
            "total_reward": float(summary["total_reward"]),
            "terminated": bool(summary["terminated"]),
            "truncated": bool(summary["truncated"]),
            "termination_reason": summary["termination_reason"],
            "weights_before": str(weights_before["sha256"]),
            "weights_after": str(weights_after["sha256"]),
            "weights_unchanged": bool(weights_before["sha256"] == weights_after["sha256"]),
            "unmapped_or_invalid": int(summary["unmapped_or_invalid"]),
            "substrate": "biological_graph",
            "policy_source": "biological_graph",
            "structure_record": None,
            "training": True,
        }
        metrics["behaviour_sha256"] = sha256_text(canonical_json(metrics))
        output = None
        return metrics


@dataclass(frozen=True, eq=False)
class PilotTrainingResult:
    """One artifact's completed (or interrupted) training run."""

    condition_id: str
    campaign_seed: int
    training_seed: int
    init_seed: int
    master_seed: int
    budget: dict
    episodes: tuple[dict, ...]
    environment_seeds: tuple[int, ...]
    parameter_digest: str
    state_digest: str
    initial_parameter_digest: str
    checkpoints: tuple[dict, ...]
    resume: dict
    interrupted: bool
    wall_time_s: float
    sampling_seed: int
    network_seed: int
    b3: dict
    artifact_directory: str
    origin: str
    stage: str
    training_performed_here: bool
    substrate: str
    model: Any = field(repr=False, compare=False)

    @property
    def evaluation_seed(self) -> int:
        return int(self.campaign_seed)

    @property
    def episodes_completed(self) -> int:
        return len(self.episodes)

    def describe(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "evaluation_seed": self.evaluation_seed,
            "campaign_seed": self.campaign_seed,
            "training_seed": self.training_seed,
            "init_seed": self.init_seed,
            "master_seed": self.master_seed,
            "budget": dict(self.budget),
            "episodes_completed": self.episodes_completed,
            "environment_seeds": list(self.environment_seeds),
            "parameter_digest": self.parameter_digest,
            "state_digest": self.state_digest,
            "initial_parameter_digest": self.initial_parameter_digest,
            "checkpoints": [dict(item) for item in self.checkpoints],
            "resume": dict(self.resume),
            "interrupted": bool(self.interrupted),
            "wall_time_s": round(float(self.wall_time_s), 6),
            "sampling_seed": self.sampling_seed,
            "network_seed": self.network_seed,
            "b3": dict(self.b3),
            "artifact_directory": self.artifact_directory,
            "origin": self.origin,
            "stage": self.stage,
            "substrate": self.substrate,
            "training_performed_here": True,
        }


def _checkpoint_record(episode: int, directory: Path, verified: Any) -> dict:
    manifest = verified.manifest
    return {
        "episode": int(episode),
        "directory": directory.as_posix(),
        "schema_version": int(manifest["schema_version"]),
        "manifest_sha256": sha256_file(directory / EXACT_CHECKPOINT_NAME),
        "parameters_sha256": str(manifest["parameters"]["sha256"]),
        "components_sha256": str(manifest["components"]["sha256"]),
        "digest": {
            "trainable": str(manifest["digest"]["trainable"]),
            "state": str(manifest["digest"]["state"]),
            "optimizer": str(manifest["digest"]["optimizer"]),
        },
        "rng_checkpointed": bool(manifest["rng"]["checkpointed"]),
        "optimizer_state_checkpointed": bool(
            manifest["optimizer"]["state_checkpointed"]
        ),
        "environment_present": bool(manifest["rng"]["environment"]["present"]),
        "integrity_verified": True,
    }


def run_training_loop(
    *,
    initialized: InitializedModel,
    model: Any,
    controller: Any,
    episode_runner: PilotEpisodeRunner,
    config: TrainingConfig,
    evaluation_seed: int,
    training_seed: int,
    init_seed: int,
    master_seed: int,
    b3: Mapping[str, Any],
    environment_seeds: Sequence[int],
    budget: int,
    checkpoint_root: str | Path,
    artifact_directory_path: str | Path,
    sampling_seed: int,
    network_seed: int,
    resume_from: str | Path | None = None,
    interrupt_after: int | None = None,
    substrate: str = PILOT_SUBSTRATE,
    progress_callback: Callable[[dict], None] | None = None,
) -> PilotTrainingResult:
    """Run the declared episode budget with one B5/B6 checkpoint per episode.

    This is the training machinery without an authorization decision. It is
    called by :func:`run_pilot_artifact` only after D5 has authorised the exact
    artifact; tests call it directly with a short budget on a synthetic
    substrate to demonstrate interruption, resumption and equivalence.
    """
    condition = str(initialized.condition_id)
    if condition not in PILOT_TRAINING_CONDITIONS:
        raise TrainingNotAuthorized(
            f"{condition!r} is outside the D5 training scope"
        )
    if initialized.stage != "initialized":
        raise ArtifactSchemaError(
            "the loop starts from the declared seeded initialization"
        )
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise TrainingConfigError("budget must be a positive integer")
    seeds = tuple(int(seed) for seed in environment_seeds)
    if len(seeds) < budget:
        raise TrainingConfigError(
            f"the B4 schedule has {len(seeds)} seeds for a budget of {budget}"
        )
    if int(initialized.campaign_seed) != int(evaluation_seed):
        raise ArtifactCompatibilityError(
            "the initialized campaign seed does not match the requested evaluation seed"
        )
    if int(initialized.training_seed) != int(training_seed):
        raise ArtifactCompatibilityError(
            "the initialized training seed does not match the plan"
        )
    if int(initialized.init_seed) != int(init_seed):
        raise ArtifactCompatibilityError(
            "the initialized learning seed does not match the plan"
        )
    trainer = getattr(controller, "trainer", None)
    if trainer is None or getattr(trainer, "optimizer", None) is None:
        raise TrainingError("a training loop needs the REINFORCE optimizer")

    checkpoint_directory = Path(checkpoint_root)
    if resume_from is None:
        if checkpoint_directory.exists() and any(checkpoint_directory.iterdir()):
            raise ArtifactSchemaError(
                f"{checkpoint_directory} already holds checkpoints; a fresh run "
                "is never silently merged with an interrupted one"
            )
    checkpoint_directory.mkdir(parents=True, exist_ok=True)

    episodes: list[dict] = []
    used: list[int] = []
    checkpoints: list[dict] = []
    resume_report: dict = {
        "resumed": False,
        "reason": "a fresh uninterrupted run; no resume was exercised",
        "equivalence_claimed": False,
    }
    start = 0
    if resume_from is not None:
        restored = restore_exact_checkpoint(
            resume_from,
            config=config,
            expected_condition=condition,
            model=model,
        )
        manifest = restored.manifest
        for field_name, expected in (
            ("campaign_seed", evaluation_seed),
            ("training_seed", training_seed),
            ("init_seed", init_seed),
            ("master_seed", master_seed),
        ):
            if int(manifest[field_name]) != int(expected):
                raise ArtifactCompatibilityError(
                    f"the checkpoint records {field_name}={manifest[field_name]}; "
                    f"the plan requires {expected}"
                )
        applied = apply_exact_restore(
            trainer.optimizer,
            controller.sampler,
            restored,
            restore_global_rng=True,
        )
        progress = restored.progress
        episodes = [dict(item) for item in progress["episodes"]]
        used = [int(seed) for seed in progress["environment_seeds_used"]]
        start = len(episodes)
        if start > budget:
            raise ArtifactCompatibilityError(
                f"the checkpoint is at episode {start}, beyond the budget {budget}"
            )
        if int(progress.get("budget", {}).get("value", -1)) != budget:
            raise ArtifactCompatibilityError(
                "the checkpoint was written under a different episode budget"
            )
        if used != list(seeds[:start]):
            raise ArtifactCompatibilityError(
                "the checkpoint's environment seeds are not the declared B4 prefix"
            )
        # B5 retains every intermediate checkpoint. A resumed run must carry the
        # pre-existing episode checkpoints into its ledger, or the artifact would
        # index only the episodes it ran itself and silently drop earlier ones.
        for index in range(1, start + 1):
            previous = checkpoint_directory / f"episode_{index:03d}"
            if not previous.is_dir():
                raise ArtifactSchemaError(
                    f"episode {index} checkpoint is missing from "
                    f"{checkpoint_directory}; a resumed artifact must retain "
                    "every intermediate checkpoint"
                )
            recorded = read_exact_checkpoint(
                previous, config=config, expected_condition=condition
            )
            checkpoints.append(_checkpoint_record(index, previous, recorded))
        resume_report = {
            "resumed": True,
            "checkpoint": Path(resume_from).as_posix(),
            "start_episode": start,
            "optimizer_state_restored": bool(applied["optimizer_state_restored"]),
            "sampler_state_restored": bool(applied["sampler_state_restored"]),
            "global_rng_restored": bool(applied["numpy_rng_restored"]),
            "environment_state_present": bool(applied["environment_state_present"]),
            "environment_reason": str(
                restored.manifest["rng"]["environment"]["reason"]
            ),
            "equivalence_claimed": False,
            "equivalence_note": (
                "equivalence is claimed only after verify_equivalence compares "
                "this resumed run with an uninterrupted run"
            ),
        }

    initial_digest = str(initialized.parameter_digest)
    if start == 0:
        initial_digest = trainable_digest(model)

    started = time.perf_counter()
    interrupted = False
    for episode in range(start, budget):
        if interrupt_after is not None and len(episodes) >= int(interrupt_after):
            interrupted = True
            break
        env_seed = int(seeds[episode])
        before = trainable_digest(model)
        metrics = episode_runner.run_episode(
            condition,
            evaluation_seed=evaluation_seed,
            episode=episode,
            environment_seed=env_seed,
            network_seed=network_seed,
            controller=controller,
        )
        update = controller.update()
        if not isinstance(update, Mapping):
            raise TrainingError("the readout controller returned no update record")
        after = trainable_digest(model)
        if str(update.get("parameter_digest_before")) != before:
            raise TrainingError(
                "the REINFORCE update did not start from the observed parameters"
            )
        if str(update.get("parameter_digest_after")) != after:
            raise TrainingError(
                "the REINFORCE update record disagrees with the live parameters"
            )
        if int(update.get("n_decisions", -1)) != int(metrics["game_updates"]):
            raise TrainingError(
                "not every sampled decision received a reward before the update"
            )
        state = model_state(model)
        record = {
            "episode": episode + 1,
            "n_decisions": int(update["n_decisions"]),
            "steps": int(metrics["game_updates"]),
            "updates_applied": 1,
            "updates_after": episode + 1,
            "loss": update.get("loss"),
            "mean_return": update.get("mean_return"),
            "episode_reward": float(metrics["total_reward"]),
            "policy_loss": None,
            "value_loss": None,
            "entropy": None,
            "grad_norm": update.get("grad_norm"),
            "parameter_digest_before": before,
            "parameter_digest_after": after,
            "state_digest_after": state_digest(state),
            "environment_seed": env_seed,
            "network_seed": int(network_seed),
            "action_counts": dict(metrics["action_counts"]),
            "total_spikes": int(metrics["total_spikes"]),
            "motor_spikes": int(metrics["motor_spikes"]),
            "terminated": bool(metrics["terminated"]),
            "truncated": bool(metrics["truncated"]),
            "termination_reason": metrics["termination_reason"],
            "weights_before": str(metrics["weights_before"]),
            "weights_after": str(metrics["weights_after"]),
            "behaviour_sha256": str(metrics["behaviour_sha256"]),
            "substrate": "biological_graph",
        }
        episodes.append(record)
        used.append(env_seed)
        if len(episodes) != episode + 1:
            raise TrainingError("the episode ledger did not advance by one")
        progress = {
            "episodes_completed": len(episodes),
            "updates_completed": len(episodes),
            "budget": {"unit": "episodes", "value": int(budget)},
            "environment_seeds_used": list(used),
            "sampling_seed": int(sampling_seed),
            "metrics_sha256": sha256_text(canonical_json(episodes)),
            "episodes": episodes,
            "b3": dict(b3),
            "b4": {
                "contract": "B4",
                "version": CONTRACT_VERSION,
                "namespace": B4_NAMESPACE,
                "episode": episode + 1,
                "environment_seed": env_seed,
                "schedule_size": int(budget),
            },
        }
        directory = checkpoint_directory / f"episode_{episode + 1:03d}"
        write_exact_checkpoint(
            directory,
            model,
            config=config,
            condition_id=condition,
            campaign_seed=int(evaluation_seed),
            training_seed=int(training_seed),
            init_seed=int(init_seed),
            master_seed=int(master_seed),
            progress=progress,
            optimizer=trainer.optimizer,
            sampler=controller.sampler,
            environment_state=None,
            environment_reason=ENVIRONMENT_REASON,
        )
        verified = read_exact_checkpoint(
            directory, config=config, expected_condition=condition
        )
        checkpoints.append(_checkpoint_record(episode + 1, directory, verified))
        if progress_callback is not None:
            progress_callback(
                {
                    "condition_id": condition,
                    "evaluation_seed": int(evaluation_seed),
                    "episode": episode + 1,
                    "budget": int(budget),
                    "loss": record["loss"],
                    "mean_return": record["mean_return"],
                    "episode_reward": record["episode_reward"],
                    "total_spikes": record["total_spikes"],
                    "motor_spikes": record["motor_spikes"],
                    "checkpoint": directory.as_posix(),
                }
            )
        gc.collect()

    if not interrupted and len(episodes) != budget:
        raise TrainingError(
            f"the run completed {len(episodes)} of {budget} episodes without resuming"
        )
    final_state = model_state(model)
    return PilotTrainingResult(
        condition_id=condition,
        campaign_seed=int(evaluation_seed),
        training_seed=int(training_seed),
        init_seed=int(init_seed),
        master_seed=int(master_seed),
        budget={"unit": "episodes", "value": int(budget)},
        episodes=tuple(episodes),
        environment_seeds=tuple(used),
        parameter_digest=trainable_digest(model),
        state_digest=state_digest(final_state),
        initial_parameter_digest=initial_digest,
        checkpoints=tuple(checkpoints),
        resume=resume_report,
        interrupted=bool(interrupted),
        wall_time_s=time.perf_counter() - started,
        sampling_seed=int(sampling_seed),
        network_seed=int(network_seed),
        b3=dict(b3),
        artifact_directory=Path(artifact_directory_path).as_posix(),
        origin="trained",
        stage="trained",
        training_performed_here=True,
        substrate=str(substrate),
        model=model,
    )


def build_controller(condition_id: str, model: Any, populations: Any, *, seed: int, config: TrainingConfig) -> Any:
    """The declared F or Fβ training controller over the declared motor spec."""
    reinforce = ReinforceConfig(
        learning_rate=float(config.reinforce_learning_rate),
        gamma=float(config.reinforce_gamma),
    )
    if condition_id == "F":
        controller = f_readout.build_decision_source(
            populations=populations,
            training=True,
            seed=int(seed),
            model=model,
            reinforce=reinforce,
        )
        f_readout.assert_state_dependent(controller)
        f_readout.assert_motor_only_interface(controller)
        return controller
    if condition_id == "F_beta":
        controller = f_beta.build_decision_source(
            populations=populations,
            training=True,
            seed=int(seed),
            model=model,
            reinforce=reinforce,
        )
        f_beta.assert_state_independent(controller)
        return controller
    raise TrainingNotAuthorized(
        f"D5 authorises F and F_beta only; {condition_id!r} is outside its scope"
    )


def run_pilot_artifact(
    phase8_config: Any,
    entry: PilotArtifactPlan,
    *,
    root: str | Path,
    config: TrainingConfig | None = None,
    factory: Any | None = None,
    episode_runner: PilotEpisodeRunner | None = None,
    resume_from: str | Path | None = None,
    interrupt_after: int | None = None,
    substrate: str | None = None,
    progress_callback: Callable[[dict], None] | None = None,
) -> PilotTrainingResult:
    """Authorise, then run, one of the six D5 artifacts end to end."""
    if not isinstance(entry, PilotArtifactPlan):
        raise TrainingConfigError("run_pilot_artifact requires a plan entry")
    if entry.substrate != PILOT_SUBSTRATE:
        raise TrainingNotAuthorized(
            "D5 authorises the frozen biological substrate only"
        )
    assert_d5_training_authorized(
        entry.condition_id, entry.evaluation_seed, episodes=entry.episodes
    )
    if int(entry.episodes) != PILOT_TRAINING_EPISODES:
        raise TrainingNotAuthorized(
            f"D5 authorises exactly {PILOT_TRAINING_EPISODES} episodes; "
            f"{entry.episodes} is outside its scope"
        )
    if config is None:
        config = validate_training_config(phase8_config)
    if len(str(entry.b3.get("sha256", ""))) != 64:
        raise TrainingConfigError("the plan entry carries no B3 provenance")

    if factory is None:
        factory = CampaignFactory(
            frozen_inputs=phase8_config.campaign.frozen_inputs,
            settings=FactorySettings(
                max_game_updates=int(phase8_config.campaign.max_game_updates)
            ),
        )
    directory = artifact_directory(root, entry.condition_id, entry.evaluation_seed)
    for name in (MANIFEST_NAME, PARAMETERS_NAME, "training_run.json"):
        if (directory / name).exists():
            raise ArtifactSchemaError(
                f"{directory / name} already exists; a trained artifact is never "
                "silently replaced"
            )
    checkpoint_directory = directory / "checkpoints"
    if resume_from is None and checkpoint_directory.exists() and any(
        checkpoint_directory.iterdir()
    ):
        raise ArtifactSchemaError(
            f"{checkpoint_directory} already holds checkpoints; pass resume_from "
            "to continue an interrupted artifact"
        )

    initialized = initialize(
        entry.condition_id,
        campaign_seed=entry.evaluation_seed,
        training_seed=entry.training_seed,
        master_seed=int(config.master_seed),
    )
    if initialized.init_seed != entry.init_seed:
        raise ArtifactCompatibilityError(
            "the plan's initialization seed does not match the declared derivation"
        )
    if initialized.environment_seed != entry.initialization_environment_seed:
        raise ArtifactCompatibilityError(
            "the plan's initialization environment seed does not match the derivation"
        )
    if training_environment_seed(
        int(config.master_seed), entry.training_seed, 0
    ) != int(entry.environment_seeds[0]):
        raise ArtifactCompatibilityError(
            "the plan's first B4 seed does not match the declared derivation"
        )
    assert_environment_stream_disjoint(
        entry.environment_seeds, master_seed=int(config.master_seed)
    )

    model = initialized.model
    runner = episode_runner or PilotEpisodeRunner(factory)
    controller = build_controller(
        entry.condition_id,
        model,
        factory.world.populations,
        seed=entry.sampling_seed,
        config=config,
    )
    return run_training_loop(
        initialized=initialized,
        model=model,
        controller=controller,
        episode_runner=runner,
        config=config,
        evaluation_seed=entry.evaluation_seed,
        training_seed=entry.training_seed,
        init_seed=entry.init_seed,
        master_seed=int(config.master_seed),
        b3=entry.b3,
        environment_seeds=entry.environment_seeds,
        budget=entry.episodes,
        checkpoint_root=checkpoint_directory,
        artifact_directory_path=directory,
        sampling_seed=entry.sampling_seed,
        network_seed=entry.network_seed,
        resume_from=resume_from,
        interrupt_after=interrupt_after,
        substrate=substrate or entry.substrate,
        progress_callback=progress_callback,
    )


def verify_resume_equivalence(uninterrupted: Any, resumed: Any) -> dict:
    """B6: an interrupted-and-resumed run must equal the uninterrupted run."""
    return assert_resumption_equivalent(uninterrupted, resumed)


def run_pilot_plan(
    plan: PilotTrainingPlan,
    phase8_config: Any,
    *,
    root: str | Path,
    config: TrainingConfig | None = None,
    factory: Any | None = None,
    log_path: str | Path | None = None,
    evidence_kind: str = "experimental",
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """Run all six D5 artifacts sequentially on one shared factory.

    The event log is append-only JSON Lines. An existing trained artifact is
    refused before the first episode; a failure stops the plan with its
    checkpoints intact rather than restarting anything. ``evidence_kind`` is
    ``"experimental"`` for the production run and may be
    ``"synthetic_fixture"`` only for tests on the fixture substrate.
    """
    if not isinstance(plan, PilotTrainingPlan):
        raise TrainingConfigError("run_pilot_plan requires a PilotTrainingPlan")
    if config is None:
        config = validate_training_config(phase8_config)
    if factory is None:
        factory = CampaignFactory(
            frozen_inputs=phase8_config.campaign.frozen_inputs,
            settings=FactorySettings(
                max_game_updates=int(phase8_config.campaign.max_game_updates)
            ),
        )
    substrate = PILOT_SUBSTRATE if evidence_kind == "experimental" else evidence_kind
    base = Path(root)
    for entry in plan.entries:
        directory = artifact_directory(base, entry.condition_id, entry.evaluation_seed)
        for name in (MANIFEST_NAME, PARAMETERS_NAME, "training_run.json"):
            if (directory / name).exists():
                raise ArtifactSchemaError(
                    f"{directory / name} already exists; the plan refuses to "
                    "overwrite evidence"
                )
    base.mkdir(parents=True, exist_ok=True)
    log = Path(log_path) if log_path is not None else base / "pilot_training_log.jsonl"

    def emit(payload: dict) -> None:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(payload) + "\n")

    emit(
        {
            "event": "plan_start",
            "runner": RUNNER_ID,
            "n_artifacts": len(plan.entries),
            "n_episodes": sum(entry.episodes for entry in plan.entries),
            "master_seed": plan.master_seed,
            "substrate": plan.substrate,
            "b3_sha256": plan.b3.get("sha256"),
        }
    )
    results: list[PilotTrainingResult] = []
    for entry in plan.entries:
        emit(
            {
                "event": "artifact_start",
                "condition_id": entry.condition_id,
                "evaluation_seed": entry.evaluation_seed,
                "training_seed": entry.training_seed,
                "episodes": entry.episodes,
            }
        )
        try:
            result = run_pilot_artifact(
                phase8_config,
                entry,
                root=base,
                config=config,
                factory=factory,
                substrate=substrate,
                progress_callback=progress_callback,
            )
            written = write_trained_artifact(
                phase8_config,
                result,
                entry,
                root=base,
                plan=plan,
                config=config,
                evidence_kind=evidence_kind,
            )
        except BaseException as error:  # noqa: BLE001 - evidence is preserved
            emit(
                {
                    "event": "artifact_failed",
                    "condition_id": entry.condition_id,
                    "evaluation_seed": entry.evaluation_seed,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "note": (
                        "checkpoints already written are retained; no episode is "
                        "restarted under a different seed"
                    ),
                }
            )
            raise
        results.append(result)
        emit(
            {
                "event": "artifact_complete",
                "condition_id": entry.condition_id,
                "evaluation_seed": entry.evaluation_seed,
                "training_seed": entry.training_seed,
                "episodes_completed": result.episodes_completed,
                "parameter_digest": result.parameter_digest,
                "state_digest": result.state_digest,
                "manifest_sha256": written["manifest_sha256"],
                "training_run_sha256": written["training_run_sha256"],
                "evidence_kind": written["evidence_kind"],
                "wall_time_s": round(float(result.wall_time_s), 6),
            }
        )
    emit(
        {
            "event": "plan_complete",
            "artifacts_completed": len(results),
            "episodes_completed": sum(result.episodes_completed for result in results),
            "evidence_kind": evidence_kind,
        }
    )
    return {
        "plan": plan.describe(),
        "results": [result.describe() for result in results],
        "artifacts_completed": len(results),
        "episodes_completed": sum(result.episodes_completed for result in results),
        "log": log.as_posix(),
        "evidence_kind": evidence_kind,
        "training_execution_authorized_by": "D5",
    }


__all__ = [
    "ENVIRONMENT_REASON",
    "PINNED_EPISODE_FIELDS",
    "PilotEpisodeRunner",
    "PilotTrainingResult",
    "RUNNER_ID",
    "build_controller",
    "run_pilot_artifact",
    "run_pilot_plan",
    "run_training_loop",
    "verify_resume_equivalence",
]
