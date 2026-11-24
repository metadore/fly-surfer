"""The training interface: an explicit plan and an unconditional refusal to run.

SCIENTIFIC STATUS
    REV4 §12 is unapproved, U1–U18 remain ``PROPOSED``, the document
    authorises no execution, and the campaign design is unresolved
    (``n_seeds_selected`` is null). Training is therefore not permitted. This
    module implements the *interface* the future stage must use:

    * :func:`build_training_plan` expands the declared budgets into one entry
      per condition, campaign seed and paired training seed. It performs no
      training and writes nothing; it refuses while the design is unresolved
      and while an explicit seed pairing is missing;
    * :func:`run_training` accepts such a plan, validates its type, and then
      raises :class:`~.errors.TrainingNotAuthorized` before touching a file.

    The plan separates the four stages explicitly: initialization
    (:mod:`~.initialization`), training (here), validation
    (:mod:`~.validation`) and loading (:mod:`~.loader`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from readout.trainer import ReinforceConfig

from .config import (
    READOUT_CONDITIONS,
    TRAINABLE_CONDITIONS,
    TrainingConfig,
    canonical_json,
    sha256_text,
)
from .errors import TrainingError
from .gate import assert_design_resolved, assert_training_authorized
from .seeding import artifact_seeds, validate_pairing

CONFIRMATORY_CONDITIONS = ("F", "F_beta", "E")
EXPLORATORY_CONDITIONS = ("E_full",)


@dataclass(frozen=True)
class TrainingEntry:
    condition_id: str
    role: str
    campaign_seed: int
    training_seed: int
    init_seed: int
    environment_seed: int
    model_kind: str
    n_features: int
    substrate: str
    budget: dict
    optimizer: dict

    def as_dict(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "role": self.role,
            "campaign_seed": self.campaign_seed,
            "training_seed": self.training_seed,
            "init_seed": self.init_seed,
            "training_environment_seed": self.environment_seed,
            "model_kind": self.model_kind,
            "n_features": self.n_features,
            "substrate": self.substrate,
            "budget": dict(self.budget),
            "optimizer": dict(self.optimizer),
        }


@dataclass(frozen=True)
class TrainingPlan:
    config_sha256: str
    master_seed: int
    entries: tuple[TrainingEntry, ...]
    pairing: dict
    execution_authorized: bool = False

    def as_dict(self) -> dict:
        return {
            "training_config_sha256": self.config_sha256,
            "master_seed": self.master_seed,
            "execution_authorized": self.execution_authorized,
            "pairing": dict(self.pairing),
            "entries": [entry.as_dict() for entry in self.entries],
        }

    def sha256(self) -> str:
        return sha256_text(canonical_json(self.as_dict()))

    def describe(self) -> dict:
        return {
            "n_entries": len(self.entries),
            "conditions": sorted({entry.condition_id for entry in self.entries}),
            "campaign_seeds": sorted({entry.campaign_seed for entry in self.entries}),
            "training_seeds": sorted({entry.training_seed for entry in self.entries}),
            "plan_sha256": self.sha256(),
            "execution_authorized": False,
            "training_performed": False,
        }


def _budget(condition_id: str, config: TrainingConfig) -> dict:
    if condition_id in READOUT_CONDITIONS:
        return {
            "kind": "training_episodes",
            "value": int(config.readout_episodes_per_seed),
        }
    return {
        "kind": "gradient_updates",
        "value": int(config.e_gradient_updates),
    }


def _optimizer(condition_id: str, config: TrainingConfig) -> dict:
    if condition_id in READOUT_CONDITIONS:
        return ReinforceConfig(
            learning_rate=float(config.reinforce_learning_rate),
            gamma=float(config.reinforce_gamma),
        ).describe()
    return dict(config.e_learner_dict())


def build_training_plan(
    config: TrainingConfig,
    campaign: Any,
    pairing: Mapping[tuple[str, int], int],
) -> TrainingPlan:
    """Expand the declared budgets into a plan; never trains.

    ``pairing`` is the explicit ``(condition, campaign_seed) -> training_seed``
    map. REV4 declares no default mapping, so none is supplied here.
    """
    assert_design_resolved(campaign)
    active = list(campaign.active_seeds())
    normalised = validate_pairing(
        pairing,
        conditions=TRAINABLE_CONDITIONS,
        campaign_seeds=active,
        training_seeds=config.training_seeds,
    )
    kind_by_condition = {
        "F": "linear_readout",
        "F_beta": "bias_only_readout",
        "E": "conventional_actor_critic",
        "E_full": "conventional_actor_critic",
    }
    width_by_condition = {
        "F": int(config.motor_n_features),
        "F_beta": int(config.motor_n_features),
        "E": int(config.e_n_features),
        "E_full": int(config.e_full_n_features),
    }
    entries: list[TrainingEntry] = []
    for condition_id in TRAINABLE_CONDITIONS:
        role = (
            "confirmatory"
            if condition_id in CONFIRMATORY_CONDITIONS
            else "exploratory"
        )
        for campaign_seed in active:
            training_seed = int(pairing[(condition_id, campaign_seed)])
            seeds = artifact_seeds(
                config.master_seed,
                condition_id,
                campaign_seed=campaign_seed,
                training_seed=training_seed,
            )
            entries.append(
                TrainingEntry(
                    condition_id=condition_id,
                    role=role,
                    campaign_seed=int(campaign_seed),
                    training_seed=int(seeds["training_seed"]),
                    init_seed=int(seeds["init_seed"]),
                    environment_seed=int(seeds["environment_seed"]),
                    model_kind=kind_by_condition[condition_id],
                    n_features=int(width_by_condition[condition_id]),
                    substrate=(
                        "biological" if condition_id in READOUT_CONDITIONS else "none"
                    ),
                    budget=_budget(condition_id, config),
                    optimizer=_optimizer(condition_id, config),
                )
            )
    return TrainingPlan(
        config_sha256=config.sha256(),
        master_seed=int(config.master_seed),
        entries=tuple(entries),
        pairing=normalised,
        execution_authorized=False,
    )


def run_training(plan: TrainingPlan, *, root: Any | None = None) -> None:
    """Refuse to train. No file, model or episode is touched.

    The signature exists so the future authorized stage has one entry point.
    Until REV4 is approved and the design is resolved, that point always
    raises. The engine
    (:mod:`experiments.phase_8.training.engine`) implements the declared loops,
    but its protocol context consults the same gate in its constructor, so
    there is no path around this refusal.
    """
    if not isinstance(plan, TrainingPlan):
        raise TrainingError("run_training expects a TrainingPlan")
    assert_training_authorized()


def describe_interface() -> dict:
    return {
        "stages": {
            "initialization": "experiments.phase_8.training.initialization",
            "training": "experiments.phase_8.training.plan.run_training",
            "engine": "experiments.phase_8.training.engine (synthetic fixtures only)",
            "checkpoint": "experiments.phase_8.training.checkpoint",
            "validation": "experiments.phase_8.training.validation",
            "loading": "experiments.phase_8.training.loader",
        },
        "trainable_conditions": list(TRAINABLE_CONDITIONS),
        "readout_budget": "20 training episodes per seed (REV4 Appendix C)",
        "agent_budget": "2,000 gradient updates (REV4 Appendix C)",
        "training_authorized": False,
        "reason": (
            "D1 approved REV4 §12 and U1-U18, and D4 declares the B3-B6 "
            "training-operation contracts, but training is still refused: "
            "design.n_seeds_selected is null (U7), B7 is open, and neither "
            "decision authorises a training run"
        ),
        "artifacts_written_by_this_task": 0,
    }


__all__ = [
    "CONFIRMATORY_CONDITIONS",
    "EXPLORATORY_CONDITIONS",
    "TrainingEntry",
    "TrainingPlan",
    "build_training_plan",
    "describe_interface",
    "run_training",
]
