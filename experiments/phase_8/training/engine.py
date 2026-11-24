"""The declared training loops for F, Fβ, E and E-full.

SCIENTIFIC STATUS
    This module implements the *mechanism* REV4 declares for the two trainable
    model families, and nothing more:

    * **F / Fβ** — the fixed biological substrate runs one training episode; the
      readout samples an action at each decision, receives the game reward, and
      one REINFORCE update is applied at the end of the episode. Twenty episodes
      per seed (REV4 Appendix C). No synaptic weight is touched: the readout is
      the only trainable object, and the substrate is the caller's fixed one.
    * **E / E-full** — the conventional actor-critic steps the five-tuple game
      API with its declared encoder, records the unshaped reward, and applies one
      :meth:`~evaluation.conventional.ConventionalAgent.finish_episode` update
      per episode until the declared 2,000 gradient updates exist (REV4
      Appendix C). No neural substrate is involved.

    B and D are **not** trained here. Their plasticity runs during evaluation
    (REV4 §3.4 row 9); implementing it as a conventional training artifact would
    misrepresent what the protocol asks for, and :func:`train_readout` and
    :func:`train_agent` refuse those conditions through their condition sets.

    **Nothing here runs unless a synthetic context is constructed.** A
    ``TrainingRunContext`` with ``mode = "authorized_protocol"`` calls
    :func:`~.gate.assert_training_authorized` in its constructor, and that
    function always raises while the design (U7) and B7 remain open. Owner
    decision D4 declares B3-B6 but authorises no execution, so the protocol
    loops remain structurally unreachable, and :func:`~.plan.run_training`
    still refuses before reaching this module. The only runnable context is
    ``synthetic_fixture``, which exists so the loop mechanics can be tested on
    tiny fake environments. Synthetic runs may use a reduced budget; that is
    recorded as ``budget.override = true``.

    D4 declares the training-episode environment-seed schedule
    (:func:`~.contracts.training_environment_seed`), the checkpoint policy and
    the exact-resumption contract. They are applied only when a caller opts in:
    ``environment_seed_for_episode=None`` uses the declared B4 schedule, and
    exact checkpoints are written only under ``exact_checkpoint_root``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from evaluation.conventional import ConventionalAgent
from readout.features import MotorFeatureSpec
from readout.trainer import ReinforceConfig

from ..conditions import e_conventional, f_readout
from ..controls import f_beta
from .checkpoint import (
    RestoredCheckpoint,
    checkpoint_directory,
    write_checkpoint,
)
from .config import (
    AGENT_CONDITIONS,
    AGENT_CONFIG_FIELDS,
    READOUT_CONDITIONS,
    TrainingConfig,
    canonical_json,
    sha256_text,
)
from .contracts import B4_DERIVATION, B4_NAMESPACE, training_environment_seed
from .errors import TrainingConfigError, TrainingError
from .exact_checkpoint import (
    RestoredExactCheckpoint,
    apply_exact_restore,
    write_exact_checkpoint,
)
from .gate import assert_training_authorized
from .initialization import InitializedModel
from .state import model_state, state_digest, trainable_digest

SYNTHETIC_MODE = "synthetic_fixture"
PROTOCOL_MODE = "authorized_protocol"
MODES = (SYNTHETIC_MODE, PROTOCOL_MODE)

RUN_SCHEMA_VERSION = 1


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrainingConfigError(f"{name} must be an integer, got {value!r}")
    if int(value) < 1:
        raise TrainingConfigError(f"{name} must be positive")
    return int(value)


def _seed(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrainingConfigError(f"{name} must be an integer seed, got {value!r}")
    if int(value) < 0:
        raise TrainingConfigError(f"{name} cannot be negative")
    return int(value)


@dataclass(frozen=True)
class TrainingRunContext:
    """The authorisation state of a training run.

    Only ``synthetic_fixture`` is constructible. ``authorized_protocol`` routes
    through the approval gate, which always raises while REV4 is unapproved;
    any other value is refused.
    """

    mode: str = SYNTHETIC_MODE
    label: str = "synthetic training-engine fixture"
    episodes: int | None = None
    updates: int | None = None

    def __post_init__(self) -> None:
        mode = str(self.mode)
        if mode == PROTOCOL_MODE:
            assert_training_authorized()
        if mode not in MODES:
            raise TrainingError(
                f"mode must be one of {list(MODES)}, got {mode!r}"
            )
        for name in ("episodes", "updates"):
            value = getattr(self, name)
            if value is not None:
                _positive_int(value, f"TrainingRunContext.{name}")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "label", str(self.label))

    @property
    def synthetic(self) -> bool:
        return self.mode == SYNTHETIC_MODE

    def describe(self) -> dict:
        return {
            "mode": self.mode,
            "label": self.label,
            "episodes_override": self.episodes,
            "updates_override": self.updates,
            "training_authorized": False,
        }


def synthetic_context(
    *,
    episodes: int | None = None,
    updates: int | None = None,
    label: str = "synthetic training-engine fixture",
) -> TrainingRunContext:
    """A context usable only for synthetic fixtures; never for a campaign."""
    return TrainingRunContext(
        mode=SYNTHETIC_MODE, label=label, episodes=episodes, updates=updates
    )


def protocol_context(
    *,
    episodes: int | None = None,
    updates: int | None = None,
    label: str = "authorized protocol training run",
) -> TrainingRunContext:
    """Refuse by construction: the approval gate is consulted, and it raises."""
    return TrainingRunContext(
        mode=PROTOCOL_MODE, label=label, episodes=episodes, updates=updates
    )


@dataclass(frozen=True, eq=False)
class TrainingRun:
    """The deterministic record of one (synthetic) training run.

    ``as_dict`` and ``sha256`` exclude the checkpoint paths, which depend on the
    caller's temporary directory, so two runs with identical inputs and
    identical fixtures have the same digest so long as the fixtures are
    deterministic. The model is trained in memory only; no artifact is written.
    """

    condition_id: str
    campaign_seed: int
    training_seed: int
    init_seed: int
    master_seed: int
    mode: str
    label: str
    model_kind: str
    n_features: int
    budget: dict
    episodes: tuple[dict, ...]
    environment_seeds: tuple[int, ...]
    max_decisions_per_episode: int
    sampling_seed: int | None
    initial_parameter_digest: str
    initial_state_digest: str
    resume: dict
    model: Any = field(repr=False)
    state: dict = field(repr=False)
    parameter_digest: str
    state_digest: str
    training_config_sha256: str
    protocol_id: str
    protocol_sha256: str
    checkpoints: tuple[str, ...] = ()
    rng_restored: bool = False
    optimizer_state_restored: bool = False
    checkpoint_kind: str = "v1"

    @property
    def n_episodes(self) -> int:
        return len(self.episodes)

    @property
    def n_updates(self) -> int:
        return int(sum(int(item.get("updates_applied", 0)) for item in self.episodes))

    def as_dict(self) -> dict:
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "kind": "training_run",
            "origin": SYNTHETIC_MODE,
            "condition_id": self.condition_id,
            "campaign_seed": int(self.campaign_seed),
            "training_seed": int(self.training_seed),
            "init_seed": int(self.init_seed),
            "master_seed": int(self.master_seed),
            "mode": self.mode,
            "label": self.label,
            "model_kind": self.model_kind,
            "n_features": int(self.n_features),
            "budget": dict(self.budget),
            "episodes": [dict(item) for item in self.episodes],
            "n_episodes": self.n_episodes,
            "n_updates": self.n_updates,
            "environment_seeds": [int(seed) for seed in self.environment_seeds],
            "max_decisions_per_episode": int(self.max_decisions_per_episode),
            "sampling_seed": (
                None if self.sampling_seed is None else int(self.sampling_seed)
            ),
            "initial_parameter_digest": self.initial_parameter_digest,
            "initial_state_digest": self.initial_state_digest,
            "resume": dict(self.resume),
            "parameter_digest": self.parameter_digest,
            "state_digest": self.state_digest,
            "training_config_sha256": self.training_config_sha256,
            "protocol": {"id": self.protocol_id, "sha256": self.protocol_sha256},
            "checkpoints_written": len(self.checkpoints),
            "checkpoint_kind": self.checkpoint_kind,
            "training_executed": True,
            "training_authorized": False,
            "trained_artifact_written": False,
            "rng_restored": bool(self.rng_restored),
            "optimizer_state_restored": bool(self.optimizer_state_restored),
            "note": (
                "synthetic training-engine fixture: the loops ran on a caller-"
                "supplied fixture, no game episode or BANC substrate was used, "
                "and the result is not a training artifact and authorises no "
                "campaign"
            ),
        }

    def sha256(self) -> str:
        return sha256_text(canonical_json(self.as_dict()))

    def describe(self) -> dict:
        return {**self.as_dict(), "checkpoint_paths": list(self.checkpoints)}


def _require_context(context: Any) -> TrainingRunContext:
    if not isinstance(context, TrainingRunContext):
        raise TrainingError("a TrainingRunContext is required")
    return context


def _resolve_budget(kind: str, requested: int | None, declared: int) -> dict:
    value = int(declared) if requested is None else int(requested)
    value = _positive_int(value, f"{kind} budget")
    return {
        "kind": kind,
        "value": value,
        "declared_value": int(declared),
        "override": value != int(declared),
    }


def _check_checkpoint_policy(
    checkpoint_every: int | None, checkpoint_root: str | Path | None
) -> int | None:
    if checkpoint_every is None and checkpoint_root is None:
        return None
    if checkpoint_every is None or checkpoint_root is None:
        raise TrainingConfigError(
            "checkpoint_every and checkpoint_root must be given together; a "
            "checkpoint is never written implicitly"
        )
    return _positive_int(checkpoint_every, "checkpoint_every")


def _check_initialized(initialized: Any, conditions: Sequence[str]) -> InitializedModel:
    if not isinstance(initialized, InitializedModel):
        raise TrainingError("training requires an InitializedModel")
    if str(initialized.stage) != "initialized":
        raise TrainingError(
            f"training requires an initialized model, got stage "
            f"{initialized.stage!r}"
        )
    if initialized.condition_id not in conditions:
        raise TrainingError(
            f"{initialized.condition_id!r} has no training loop here; the "
            f"trainable conditions are {list(conditions)} (B and D train "
            "during evaluation, not as conventional artifacts)"
        )
    return initialized


def _check_manifest_identity(
    manifest: Mapping[str, Any], initialized: InitializedModel, config: TrainingConfig
) -> None:
    if str(manifest["training_config_sha256"]) != config.sha256():
        raise TrainingConfigError(
            "the checkpoint was produced under a different training configuration"
        )
    checks = {
        "condition_id": (
            str(manifest["condition_id"]) == initialized.condition_id
        ),
        "campaign_seed": int(manifest["campaign_seed"]) == initialized.campaign_seed,
        "training_seed": int(manifest["training_seed"]) == initialized.training_seed,
        "init_seed": int(manifest["init_seed"]) == initialized.init_seed,
        "master_seed": int(manifest["master_seed"]) == initialized.master_seed,
        "model_kind": str(manifest["model_kind"]) == initialized.kind,
        "n_features": int(manifest["n_features"]) == initialized.n_features,
    }
    failures = [name for name, ok in checks.items() if not ok]
    if failures:
        raise TrainingConfigError(
            f"the checkpoint does not belong to this run: {failures}"
        )


def _check_resume(
    resume: Any, initialized: InitializedModel, config: TrainingConfig
) -> RestoredCheckpoint:
    if not isinstance(resume, RestoredCheckpoint):
        raise TrainingError("resume must be a RestoredCheckpoint")
    _check_manifest_identity(resume.manifest, initialized, config)
    return resume


def _check_exact_resume(
    resume: Any, initialized: InitializedModel, config: TrainingConfig
) -> RestoredExactCheckpoint:
    if not isinstance(resume, RestoredExactCheckpoint):
        raise TrainingError("exact resume requires a RestoredExactCheckpoint")
    if not resume.rng_restored or not resume.optimizer_state_restored:
        raise TrainingError(
            "the exact checkpoint does not carry every B6 component; exact "
            "resumption cannot be claimed from it"
        )
    _check_manifest_identity(resume.manifest, initialized, config)
    return resume


def _declared_environment_schedule(
    initialized: InitializedModel, episode: int
) -> int:
    """D4 B4: the declared training-episode environment seed."""
    return training_environment_seed(
        initialized.master_seed, initialized.training_seed, episode
    )


def _seed_from(callable_or_int: Any, episode: int, name: str) -> int:
    value = callable_or_int(episode) if callable(callable_or_int) else callable_or_int
    return _seed(value, f"{name}[{episode}]")


def _scalar_metrics(info: Any) -> dict:
    """Keep only JSON-safe scalar entries from a caller's episode report."""
    if info is None:
        return {}
    if not isinstance(info, Mapping):
        raise TrainingError("the episode runner must return a mapping or None")
    out: dict[str, Any] = {}
    for key, value in info.items():
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, bool) or value is None:
            out[str(key)] = value
        elif isinstance(value, (int, float)):
            out[str(key)] = float(value) if isinstance(value, float) else int(value)
        elif isinstance(value, str):
            out[str(key)] = value
        else:
            raise TrainingError(
                f"episode metric {key!r} is not a JSON scalar: {type(value).__name__}"
            )
    return out


def _metrics_digest(episodes: Sequence[Mapping]) -> str:
    return sha256_text(canonical_json([dict(item) for item in episodes]))


def _check_agent_config(agent: ConventionalAgent, config: TrainingConfig) -> None:
    observed = agent.config.as_dict()
    expected = {
        "hidden_units": config.e_hidden_units,
        "hidden_layers": config.e_hidden_layers,
        "learning_rate": config.e_learning_rate,
        "entropy_coefficient": config.e_entropy_coefficient,
        "value_coefficient": config.e_value_coefficient,
        "discount": config.e_discount,
        "max_grad_norm": config.e_max_grad_norm,
    }
    for name in AGENT_CONFIG_FIELDS:
        if observed[name] != expected[name]:
            raise TrainingConfigError(
                f"the agent's {name} is {observed[name]!r}; the validated "
                f"configuration declares {expected[name]!r}"
            )


def train_readout(
    initialized: InitializedModel,
    *,
    config: TrainingConfig,
    context: TrainingRunContext,
    populations: Any,
    episode_runner: Callable[..., Mapping | None],
    environment_seed_for_episode: Callable[[int], int] | int,
    max_decisions_per_episode: int,
    sampling_seed: int = 0,
    resume: RestoredCheckpoint | None = None,
    checkpoint_every: int | None = None,
    checkpoint_root: str | Path | None = None,
    resume_exact: RestoredExactCheckpoint | None = None,
    exact_checkpoint_root: str | Path | None = None,
    environment_state_for_episode: Callable[[int], Any] | None = None,
    b3_provenance: Mapping[str, Any] | None = None,
) -> TrainingRun:
    """Run the declared F/Fβ training loop on a caller-supplied fixture.

    ``episode_runner`` is the seam to the substrate. The engine calls it once per
    episode as ``episode_runner(controller=..., episode=..., environment_seed=...,
    max_decisions=...)``; the fixture must leave a completed reward on every
    sampled decision and must **not** call ``controller.update()`` — the engine
    applies exactly one REINFORCE update at the end of each episode, as
    :mod:`readout.trainer` defines.

    ``environment_seed_for_episode=None`` selects the declared D4 B4 schedule.
    ``exact_checkpoint_root`` writes one exact checkpoint after every completed
    episode (D4 B5); ``resume_exact`` restores parameters, optimizer moments and
    every B6 RNG component before the next episode. The two checkpoint formats
    are mutually exclusive within one run.
    """
    initialized = _check_initialized(initialized, READOUT_CONDITIONS)
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("train_readout requires a TrainingConfig")
    context = _require_context(context)
    if not callable(episode_runner):
        raise TrainingError("episode_runner must be callable")
    if resume is not None and resume_exact is not None:
        raise TrainingConfigError(
            "supply either a v1 checkpoint (resume) or an exact checkpoint "
            "(resume_exact), never both"
        )
    if exact_checkpoint_root is not None and checkpoint_every is not None:
        raise TrainingConfigError(
            "an exact run checkpoints after every episode; it does not also use "
            "the v1 checkpoint_every cadence"
        )
    if environment_state_for_episode is not None and not callable(
        environment_state_for_episode
    ):
        raise TrainingError("environment_state_for_episode must be callable or None")
    if environment_seed_for_episode is None:
        environment_seed_for_episode = lambda episode: _declared_environment_schedule(
            initialized, episode
        )
    elif not callable(environment_seed_for_episode) and not isinstance(
        environment_seed_for_episode, int
    ):
        raise TrainingError(
            "environment_seed_for_episode must be a callable, an integer or None "
            "(None selects the declared D4 B4 schedule)"
        )
    max_decisions = _positive_int(
        max_decisions_per_episode, "max_decisions_per_episode"
    )
    sampling_seed = _seed(sampling_seed, "sampling_seed")
    cadence = _check_checkpoint_policy(checkpoint_every, checkpoint_root)

    model = initialized.model
    resume_info = {
        "resumed": False,
        "rng_restored": False,
        "optimizer_state_restored": False,
    }
    start_episode = 0
    seeds_used: list[int] = []
    run_seeds: list[int] = []
    if resume is not None:
        resume = _check_resume(resume, initialized, config)
        model = resume.model
        start_episode = int(resume.progress["episodes_completed"])
        seeds_used = list(resume.progress.get("environment_seeds_used", []))
        resume_info = {
            "resumed": True,
            "start_episode": start_episode,
            "checkpoint_kind": "v1",
            "rng_restored": False,
            "optimizer_state_restored": False,
        }
    elif resume_exact is not None:
        resume_exact = _check_exact_resume(resume_exact, initialized, config)
        model = resume_exact.model
        start_episode = int(resume_exact.progress["episodes_completed"])
        seeds_used = list(resume_exact.progress.get("environment_seeds_used", []))
        run_seeds = list(seeds_used)
        if start_episode != len(seeds_used):
            raise TrainingError(
                "the exact checkpoint's completed-episode count and its recorded "
                "environment-seed history disagree"
            )
        resume_info = {
            "resumed": True,
            "start_episode": start_episode,
            "start_update": int(resume_exact.progress.get("updates_completed", 0)),
            "checkpoint_kind": "exact",
            "checkpoint": resume_exact.directory,
            "rng_restored": True,
            "optimizer_state_restored": True,
        }

    budget = _resolve_budget(
        "training_episodes",
        context.episodes,
        int(config.readout_episodes_per_seed),
    )
    if start_episode > int(budget["value"]):
        raise TrainingConfigError(
            f"the checkpoint already completed {start_episode} episodes; the "
            f"budget is {budget['value']}"
        )

    if initialized.condition_id == "F":
        if float(getattr(model, "init_std", -1.0)) != float(config.readout_init_std):
            raise TrainingConfigError(
                "the readout initialization scale differs from the validated "
                "configuration"
            )
    reinforce = ReinforceConfig(
        learning_rate=float(config.reinforce_learning_rate),
        gamma=float(config.reinforce_gamma),
    )
    if initialized.condition_id == "F":
        controller = f_readout.build_decision_source(
            populations=populations,
            training=True,
            seed=sampling_seed,
            model=model,
            reinforce=reinforce,
        )
    else:
        controller = f_beta.build_decision_source(
            populations=populations,
            training=True,
            seed=sampling_seed,
            model=model,
            reinforce=reinforce,
        )
    if int(controller.n_features) != int(initialized.n_features):
        raise TrainingConfigError(
            "the readout feature width differs from the initialized model"
        )
    if controller.trainer is None:
        raise TrainingError("a training readout needs a REINFORCE trainer")
    if resume_exact is not None:
        applied = apply_exact_restore(
            controller.trainer.optimizer,
            controller.sampler,
            resume_exact,
            restore_global_rng=True,
        )
        resume_info.update(applied)
        resume_info["resumed"] = True

    episodes: list[dict] = (
        [dict(item) for item in resume_exact.progress.get("episodes", [])]
        if resume_exact is not None
        else []
    )
    checkpoints: list[str] = []
    for episode in range(start_episode, int(budget["value"])):
        environment_seed = _seed_from(
            environment_seed_for_episode, episode, "environment_seed_for_episode"
        )
        seeds_used.append(environment_seed)
        run_seeds.append(environment_seed)
        info = episode_runner(
            controller=controller,
            episode=episode,
            environment_seed=environment_seed,
            max_decisions=max_decisions,
        )
        report = controller.update()
        if report is None:
            raise TrainingError("the readout controller returned no update report")
        if initialized.condition_id == "F":
            f_readout.assert_state_dependent(controller)
        else:
            f_beta.assert_state_independent(controller)
        n_decisions = int(report["n_decisions"])
        episodes.append(
            {
                "episode": int(episode),
                "environment_seed": int(environment_seed),
                "n_decisions": n_decisions,
                "updates_applied": 1 if n_decisions else 0,
                "loss": report["loss"],
                "mean_return": report["mean_return"],
                "grad_norm": report["grad_norm"],
                "parameter_digest_after": report["parameter_digest_after"],
                "fixture": _scalar_metrics(info),
            }
        )
        completed = episode + 1
        if exact_checkpoint_root is not None:
            environment_state = (
                environment_state_for_episode(episode)
                if environment_state_for_episode is not None
                else None
            )
            checkpoints.append(
                str(
                    write_exact_checkpoint(
                        _exact_checkpoint_directory(
                            exact_checkpoint_root,
                            initialized.condition_id,
                            initialized.campaign_seed,
                            completed,
                        ),
                        model,
                        config=config,
                        condition_id=initialized.condition_id,
                        campaign_seed=initialized.campaign_seed,
                        training_seed=initialized.training_seed,
                        init_seed=initialized.init_seed,
                        master_seed=initialized.master_seed,
                        progress={
                            "episodes_completed": completed,
                            "updates_completed": sum(
                                int(item["updates_applied"]) for item in episodes
                            ),
                            "budget": budget,
                            "environment_seeds_used": seeds_used,
                            "sampling_seed": sampling_seed,
                            "metrics_sha256": _metrics_digest(episodes),
                            "episodes": [dict(item) for item in episodes],
                            "b3": dict(b3_provenance or {}),
                            "b4": {
                                "namespace": B4_NAMESPACE,
                                "derivation": dict(B4_DERIVATION),
                                "master_seed": int(initialized.master_seed),
                                "training_seed": int(initialized.training_seed),
                                "episodes_completed": completed,
                            },
                        },
                        optimizer=controller.trainer.optimizer,
                        sampler=controller.sampler,
                        environment_state=environment_state,
                    )
                )
            )
        elif cadence is not None and completed % cadence == 0:
            checkpoints.append(
                _write_run_checkpoint(
                    checkpoint_root,
                    model,
                    config=config,
                    initialized=initialized,
                    progress={
                        "episodes_completed": completed,
                        "updates_completed": sum(
                            int(item["updates_applied"]) for item in episodes
                        ),
                        "budget": budget,
                        "environment_seeds_used": seeds_used,
                        "sampling_seed": sampling_seed,
                        "metrics_sha256": _metrics_digest(episodes),
                    },
                )
            )

    state = model_state(model)
    return TrainingRun(
        condition_id=initialized.condition_id,
        campaign_seed=initialized.campaign_seed,
        training_seed=initialized.training_seed,
        init_seed=initialized.init_seed,
        master_seed=initialized.master_seed,
        mode=context.mode,
        label=context.label,
        model_kind=initialized.kind,
        n_features=initialized.n_features,
        budget=budget,
        episodes=tuple(episodes),
        environment_seeds=tuple(run_seeds),
        max_decisions_per_episode=max_decisions,
        sampling_seed=sampling_seed,
        initial_parameter_digest=initialized.parameter_digest,
        initial_state_digest=initialized.state_digest,
        resume=resume_info,
        model=model,
        state=state,
        parameter_digest=trainable_digest(model),
        state_digest=state_digest(state),
        training_config_sha256=config.sha256(),
        protocol_id=config.protocol_id,
        protocol_sha256=config.protocol_sha256,
        checkpoints=tuple(checkpoints),
        rng_restored=bool(resume_info.get("rng_restored", False)),
        optimizer_state_restored=bool(
            resume_info.get("optimizer_state_restored", False)
        ),
        checkpoint_kind=(
            "exact"
            if exact_checkpoint_root is not None or resume_exact is not None
            else "v1"
        ),
    )


def train_agent(
    initialized: InitializedModel,
    *,
    config: TrainingConfig,
    context: TrainingRunContext,
    environment: Any,
    environment_seed_for_episode: Callable[[int], int] | int,
    max_decisions_per_episode: int,
    max_episodes: int,
    encoder: Any | None = None,
    resume: RestoredCheckpoint | None = None,
    checkpoint_every: int | None = None,
    checkpoint_root: str | Path | None = None,
) -> TrainingRun:
    """Run the declared E/E-full loop until the declared gradient-update budget.

    ``max_episodes`` is a loop-safety bound, not a scientific stopping rule: the
    declared stopping condition is the gradient-update budget, and the engine
    refuses if the bound is exhausted first. ``environment`` must implement the
    game's declared ``reset(seed=...)``/``step(action)`` five-tuple API;
    ``encoder`` defaults to the declared :class:`evaluation.observations.
    ObservationEncoder` for the condition.
    """
    initialized = _check_initialized(initialized, AGENT_CONDITIONS)
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("train_agent requires a TrainingConfig")
    context = _require_context(context)
    if not callable(getattr(environment, "reset", None)) or not callable(
        getattr(environment, "step", None)
    ):
        raise TrainingError(
            "the environment must implement reset(seed=...) and step(action)"
        )
    if not callable(environment_seed_for_episode) and not isinstance(
        environment_seed_for_episode, int
    ):
        raise TrainingError(
            "environment_seed_for_episode must be a callable or an integer"
        )
    max_decisions = _positive_int(
        max_decisions_per_episode, "max_decisions_per_episode"
    )
    max_episodes = _positive_int(max_episodes, "max_episodes")
    cadence = _check_checkpoint_policy(checkpoint_every, checkpoint_root)

    model = initialized.model
    if not isinstance(model, ConventionalAgent):
        raise TrainingError(
            f"{initialized.condition_id} must train a ConventionalAgent, got "
            f"{type(model).__name__}"
        )
    _check_agent_config(model, config)

    resume_info = {
        "resumed": False,
        "rng_restored": False,
        "optimizer_state_restored": False,
    }
    seeds_used: list[int] = []
    run_seeds: list[int] = []
    if resume is not None:
        resume = _check_resume(resume, initialized, config)
        model = resume.model
        if not isinstance(model, ConventionalAgent):
            raise TrainingError("the checkpoint does not hold a ConventionalAgent")
        progress = resume.progress
        model.updates = int(progress["updates_completed"])
        model.episodes = int(progress["episodes_completed"])
        seeds_used = list(progress.get("environment_seeds_used", []))
        resume_info = {
            "resumed": True,
            "start_episode": int(progress["episodes_completed"]),
            "start_update": int(progress["updates_completed"]),
            "rng_restored": False,
            "optimizer_state_restored": False,
        }

    budget = _resolve_budget(
        "gradient_updates",
        context.updates,
        int(config.e_gradient_updates),
    )
    if model.updates > int(budget["value"]):
        raise TrainingConfigError(
            f"the checkpoint already completed {model.updates} updates; the "
            f"budget is {budget['value']}"
        )

    if encoder is None:
        encoder = e_conventional.build_encoder(initialized.condition_id)
    if int(getattr(encoder, "n_features", -1)) != int(model.n_features):
        raise TrainingConfigError(
            "the encoder width differs from the trained agent"
        )

    model.train()
    episodes: list[dict] = []
    checkpoints: list[str] = []
    episodes_run = 0
    while model.updates < int(budget["value"]):
        if episodes_run >= max_episodes:
            raise TrainingError(
                f"the loop-safety bound of {max_episodes} episodes was reached "
                f"after {model.updates} of {budget['value']} declared gradient "
                "updates; the declared stopping condition is the update budget, "
                "so this run is refused rather than silently truncated"
            )
        episode = int(model.episodes)
        environment_seed = _seed_from(
            environment_seed_for_episode, episode, "environment_seed_for_episode"
        )
        seeds_used.append(environment_seed)
        run_seeds.append(environment_seed)
        environment.reset(seed=int(environment_seed))
        model.reset_episode()
        steps = 0
        total_reward = 0.0
        terminated = truncated = False
        while not (terminated or truncated) and steps < max_decisions:
            features = encoder.encode(environment.game_state)
            _, decision = model.act(features, training=True)
            _, reward, terminated, truncated, _ = environment.step(
                str(decision["action"])
            )
            number = float(reward)
            if not np.isfinite(number):
                raise TrainingError("the environment returned a non-finite reward")
            model.record_reward(number)
            total_reward += number
            steps += 1
        report = model.finish_episode()
        if report is None:
            raise TrainingError(
                "an episode recorded no transition and applied no update; the "
                "declared gradient budget cannot be reached this way"
            )
        model.episodes += 1
        episodes_run += 1
        episodes.append(
            {
                "episode": episode,
                "environment_seed": int(environment_seed),
                "steps": int(steps),
                "episode_reward": round(float(total_reward), 9),
                "updates_applied": 1,
                "updates_after": int(model.updates),
                "loss": round(float(report["loss"]), 9),
                "policy_loss": round(float(report["policy_loss"]), 9),
                "value_loss": round(float(report["value_loss"]), 9),
                "entropy": round(float(report["entropy"]), 9),
                "grad_norm": round(float(report["grad_norm"]), 9),
                "parameter_digest_after": report["parameter_digest_after"],
            }
        )
        if cadence is not None and model.updates % cadence == 0:
            checkpoints.append(
                _write_run_checkpoint(
                    checkpoint_root,
                    model,
                    config=config,
                    initialized=initialized,
                    progress={
                        "episodes_completed": int(model.episodes),
                        "updates_completed": int(model.updates),
                        "budget": budget,
                        "environment_seeds_used": seeds_used,
                        "sampling_seed": None,
                        "metrics_sha256": _metrics_digest(episodes),
                    },
                )
            )

    if model.updates != int(budget["value"]):
        raise TrainingError(
            f"the run stopped at {model.updates} updates; the declared budget "
            f"is {budget['value']}"
        )
    model.eval()
    model.reset_episode()
    state = model_state(model)
    return TrainingRun(
        condition_id=initialized.condition_id,
        campaign_seed=initialized.campaign_seed,
        training_seed=initialized.training_seed,
        init_seed=initialized.init_seed,
        master_seed=initialized.master_seed,
        mode=context.mode,
        label=context.label,
        model_kind=initialized.kind,
        n_features=initialized.n_features,
        budget=budget,
        episodes=tuple(episodes),
        environment_seeds=tuple(run_seeds),
        max_decisions_per_episode=max_decisions,
        sampling_seed=None,
        initial_parameter_digest=initialized.parameter_digest,
        initial_state_digest=initialized.state_digest,
        resume=resume_info,
        model=model,
        state=state,
        parameter_digest=trainable_digest(model),
        state_digest=state_digest(state),
        training_config_sha256=config.sha256(),
        protocol_id=config.protocol_id,
        protocol_sha256=config.protocol_sha256,
        checkpoints=tuple(checkpoints),
    )


def _exact_checkpoint_directory(
    root: str | Path, condition_id: str, campaign_seed: int, step: int
) -> Path:
    """``<root>/<condition>/seed_<n>/exact_step_<k>``; never shares a v1 path."""
    return (
        Path(root)
        / str(condition_id)
        / f"seed_{int(campaign_seed)}"
        / f"exact_step_{int(step)}"
    )


def _write_run_checkpoint(
    root: str | Path | None,
    model: Any,
    *,
    config: TrainingConfig,
    initialized: InitializedModel,
    progress: Mapping[str, Any],
) -> str:
    step = int(progress["episodes_completed"])
    directory = checkpoint_directory(
        root, initialized.condition_id, initialized.campaign_seed, step
    )
    written = write_checkpoint(
        directory,
        model,
        config=config,
        condition_id=initialized.condition_id,
        campaign_seed=initialized.campaign_seed,
        training_seed=initialized.training_seed,
        init_seed=initialized.init_seed,
        master_seed=initialized.master_seed,
        progress=progress,
    )
    return str(written)


def describe_engine() -> dict:
    """The engine's declared loops, gates and deliberately unresolved inputs."""
    return {
        "module": "experiments.phase_8.training.engine",
        "loops": {
            "F/F_beta": {
                "update": "one REINFORCE update per training episode",
                "budget": "20 training episodes per seed (REV4 Appendix C)",
                "features": list(MotorFeatureSpec().names),
                "substrate": "caller-supplied fixed substrate fixture",
            },
            "E/E_full": {
                "update": "one ConventionalAgent.finish_episode per episode",
                "budget": "2,000 gradient updates (REV4 Appendix C)",
                "features": "7 matched / 14 full (REV4 §3.5 row 1)",
                "substrate": "none; five-tuple game API",
            },
        },
        "not_trained_here": {
            "B": "plasticity runs during evaluation (REV4 §3.4 row 9)",
            "D": "plasticity runs during evaluation (REV4 §3.4 row 9)",
            "F_init": "derived from F's learning stream; never its own artifact",
            "A_prime": "an eta = 0 equivalence mirror, not a trained arm",
            "C_prime": "an eta = 0 equivalence mirror, not a trained arm",
        },
        "contexts": {
            SYNTHETIC_MODE: "constructible; fixtures only, never a campaign",
            PROTOCOL_MODE: (
                "refused by construction: gate.assert_training_authorized always "
                "raises while the design (U7) and B7 remain open and D4 "
                "authorises no execution"
            ),
        },
        "declarations": {
            "owner_decision": "D4 (2026-11-21)",
            "B3": "declared: SHA-256 namespace phase_8/training/B3/v1 over the "
            "declared training pool",
            "B4": "declared: SHA-256 namespace phase_8/training/B4/v1 per "
            "training seed and episode",
            "B5": "declared: exact checkpoint after every completed episode; "
            "all intermediates and the final checkpoint retained",
            "B6": "declared: parameters, optimizer moments, python/numpy/torch "
            "RNG and sampler state; exactness requires verify_equivalence",
        },
        "unresolved_inputs": [
            {
                "name": "campaign-to-training seed pairing",
                "status": "declared by D4 (B3); derived from the declared pool",
                "interface": "training.contracts.derive_b3_pairing",
            },
            {
                "name": "training-episode environment seed schedule",
                "status": "declared by D4 (B4); used when the caller passes None",
                "interface": "environment_seed_for_episode / training.contracts",
            },
            {
                "name": "checkpoint cadence and retention",
                "status": (
                    "declared by D4 (B5): every completed episode, retain all; "
                    "still an explicit opt-in through exact_checkpoint_root"
                ),
                "interface": "exact_checkpoint_root",
            },
            {
                "name": "sampler RNG and optimizer-state checkpointing",
                "status": (
                    "implemented by D4 (B6) in training.exact_checkpoint; "
                    "exactness is claimed only after verify_equivalence"
                ),
                "interface": "training.exact_checkpoint.describe_exact_checkpoint_interface",
            },
        ],
        "gates": {
            "design": "gate.assert_design_resolved (n_seeds_selected is null)",
            "authorization": "gate.assert_training_authorized (always refuses)",
            "plan_entry": "plan.run_training (refuses before this module)",
        },
        "training_authorized": False,
        "trained_artifacts_written_by_this_task": 0,
    }


__all__ = [
    "MODES",
    "PROTOCOL_MODE",
    "RUN_SCHEMA_VERSION",
    "SYNTHETIC_MODE",
    "TrainingRun",
    "TrainingRunContext",
    "describe_engine",
    "protocol_context",
    "synthetic_context",
    "train_agent",
    "train_readout",
]
