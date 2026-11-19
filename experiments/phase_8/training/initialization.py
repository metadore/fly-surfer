"""Deterministic model and readout initialization.

Initialization is a separate stage from training, validation and loading. This
module only builds a fresh model at its declared seeded initialization; it
moves no parameter, consumes no episode and writes no artifact. A caller that
wants an artifact must pass the result to
:func:`~.artifacts.write_artifact`, and that function refuses any request to
label initialized state as trained.

Seeds follow :mod:`experiments.phase_8.seeds`: the learning stream of the
declared *training* seed initializes the trainable parameters. F and Fβ use
their own condition codes, so their initial parameter values differ even when
they share a training seed; the shared training run, not identical initial
weights, is what §3.6.2 requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from readout.features import MotorFeatureSpec

from ..conditions import e_conventional, f_readout
from ..controls import f_beta
from .config import AGENT_CONDITIONS, READOUT_CONDITIONS, TRAINABLE_CONDITIONS
from .errors import TrainingConfigError
from .seeding import artifact_seeds
from .state import (
    model_architecture,
    model_kind,
    model_state,
    state_digest,
    trainable_digest,
)


@dataclass(frozen=True, eq=False)
class InitializedModel:
    """One freshly initialized model plus the seeds that produced it."""

    condition_id: str
    campaign_seed: int
    training_seed: int
    init_seed: int
    master_seed: int
    environment_seed: int
    model: Any = field(repr=False)
    kind: str
    architecture: dict
    state: dict[str, np.ndarray] = field(repr=False)
    parameter_digest: str
    state_digest: str
    stage: str = "initialized"

    @property
    def n_features(self) -> int:
        return int(self.architecture["n_features"])

    def describe(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "campaign_seed": self.campaign_seed,
            "training_seed": self.training_seed,
            "init_seed": self.init_seed,
            "master_seed": self.master_seed,
            "environment_seed": self.environment_seed,
            "model_kind": self.kind,
            "n_features": self.n_features,
            "architecture": dict(self.architecture),
            "parameter_names": sorted(self.state),
            "parameter_digest": self.parameter_digest,
            "state_digest": self.state_digest,
            "stage": self.stage,
            "training_performed": False,
        }


def initialize(
    condition_id: str,
    *,
    campaign_seed: int,
    training_seed: int,
    master_seed: int,
) -> InitializedModel:
    """Build the declared model at its seeded initialization.

    No optimizer step, episode or gradient is executed. E's optimizer object is
    constructed by :class:`evaluation.conventional.ConventionalAgent` as part
    of the model definition, but remains unused.
    """
    if condition_id not in TRAINABLE_CONDITIONS:
        raise TrainingConfigError(
            f"{condition_id!r} has no training stage; trainable conditions are "
            f"{list(TRAINABLE_CONDITIONS)}"
        )
    seeds = artifact_seeds(
        master_seed,
        condition_id,
        campaign_seed=campaign_seed,
        training_seed=training_seed,
    )
    spec = MotorFeatureSpec()
    if condition_id in READOUT_CONDITIONS:
        if condition_id == "F":
            model = f_readout.build_readout(
                n_features=spec.n_features, seed=seeds["init_seed"]
            )
        else:
            model = f_beta.build_readout(
                n_features=spec.n_features, seed=seeds["init_seed"]
            )
    elif condition_id in AGENT_CONDITIONS:
        model = e_conventional.build_agent(
            condition_id, seed=seeds["init_seed"], training=False
        )
    else:  # pragma: no cover - guarded above
        raise TrainingConfigError(f"{condition_id!r} has no initializer")

    state = model_state(model)
    architecture = model_architecture(model)
    return InitializedModel(
        condition_id=condition_id,
        campaign_seed=seeds["campaign_seed"],
        training_seed=seeds["training_seed"],
        init_seed=seeds["init_seed"],
        master_seed=seeds["master_seed"],
        environment_seed=seeds["environment_seed"],
        model=model,
        kind=model_kind(model),
        architecture=architecture,
        state=state,
        parameter_digest=trainable_digest(model),
        state_digest=state_digest(state),
    )


def initialize_all(
    *, campaign_seed: int, training_seed: int, master_seed: int
) -> dict[str, InitializedModel]:
    """Initialization only; F, Fβ and E share a campaign seed by request.

    This helper exists so a caller can compare initial states. It does not
    train, and E-full is excluded because its role is exploratory.
    """
    return {
        condition_id: initialize(
            condition_id,
            campaign_seed=campaign_seed,
            training_seed=training_seed,
            master_seed=master_seed,
        )
        for condition_id in (*READOUT_CONDITIONS, "E")
    }


__all__ = [
    "InitializedModel",
    "initialize",
    "initialize_all",
]
