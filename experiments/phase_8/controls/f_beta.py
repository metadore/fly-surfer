"""Control Fβ — the constant-policy, state-independent readout control.

SCIENTIFIC STATUS
    Fβ is condition F with every state-dependent pathway removed. It is a
    linear readout whose feature weights are fixed at exactly 0.0 and
    excluded from the optimizer; only the four output biases train. Its
    policy is provably identical for every motor-activity vector, including
    the zero vector (REV4 §3.6.2). Only a parameter set of exactly that shape
    may be called "bias-only".

    Fβ is not the NO_ACTION floor: it trains, and its action distribution is
    data-independent but not forced to one action.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from readout.controller import ReadoutController
from readout.features import ACTION_SPACE, MotorFeatureSpec
from readout.linear import BiasOnlyReadout
from readout.trainer import ReinforceConfig, ReinforceTrainer

from ..conditions.base import (
    Components,
    ConditionError,
    NeuralComponents,
    Requirements,
    assert_seed_disjoint,
    requirements_for,
    spec_for,
    validate_components,
)
from ..conditions.execute import neural_episode

CONDITION_ID = "F_beta"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def build_readout(
    *, n_features: int | None = None, seed: int = 0
) -> BiasOnlyReadout:
    width = (
        MotorFeatureSpec().n_features if n_features is None else int(n_features)
    )
    model = BiasOnlyReadout(width, seed=int(seed))
    model.assert_state_independent()
    return model


def assert_state_independent(controller: ReadoutController) -> dict:
    """Prove that no observation-dependent pathway is trainable or active."""
    model = getattr(controller, "model", None)
    if not isinstance(model, BiasOnlyReadout):
        raise ConditionError(
            "Fβ must use BiasOnlyReadout; another architecture may contain a "
            "state-dependent pathway and may not be called bias-only"
        )
    checks = model.assert_state_independent()
    if int(model.n_features) != int(controller.n_features):
        raise ConditionError("the bias-only readout and the motor spec disagree")
    trainer = getattr(controller, "trainer", None)
    if trainer is not None:
        names = list(trainer.trainable_parameter_names)
        if names != ["bias"]:
            raise ConditionError(
                "Fβ's optimizer must contain exactly the output bias, got "
                f"{names}"
            )
    zero = np.zeros((1, controller.n_features), dtype=np.float32)
    saturated = np.full((1, controller.n_features), 1e6, dtype=np.float32)
    if not np.array_equal(model.logits(zero), model.logits(saturated)):
        raise ConditionError(
            "the bias-only readout emitted different logits for different "
            "motor activity; its policy is not state independent"
        )
    return {**checks, "constant_over_feature_vectors": True}


def build_decision_source(
    *,
    populations: Any,
    training: bool,
    seed: int = 0,
    model: Any | None = None,
    spec: MotorFeatureSpec | None = None,
    temperature: float = 1.0,
    reinforce: ReinforceConfig | None = None,
) -> ReadoutController:
    spec = spec or MotorFeatureSpec()
    model = model or build_readout(n_features=spec.n_features, seed=seed)
    trainer = ReinforceTrainer(model, reinforce) if training else None
    controller = ReadoutController(
        model,
        spec,
        populations=populations,
        training=training,
        seed=seed,
        temperature=temperature,
        trainer=trainer,
    )
    assert_state_independent(controller)
    return controller


def build_components(
    *,
    adapter: Any,
    stepper: Any,
    drive: Any,
    clock: Any,
    populations: Any,
    window_ms: float,
    training: bool,
    seed: int = 0,
    sufficiency: Any | None = None,
    structure: dict | None = None,
    spec: MotorFeatureSpec | None = None,
    model: Any | None = None,
    reinforce: ReinforceConfig | None = None,
    metadata: dict | None = None,
) -> Components:
    controller = build_decision_source(
        populations=populations,
        training=training,
        seed=seed,
        model=model,
        spec=spec,
        reinforce=reinforce,
    )
    return Components(
        neural=NeuralComponents(
            adapter=adapter,
            stepper=stepper,
            drive=drive,
            clock=clock,
            action_decoder=None,
            decision_source=controller,
            window_ms=window_ms,
            populations=populations,
            sufficiency=sufficiency,
            structure=structure,
            metadata=dict(metadata or {}),
        ),
        metadata={"condition_id": CONDITION_ID, **dict(metadata or {})},
    )


def validate(components: Components, spec: Any | None = None) -> Requirements:
    requirements_for(CONDITION_ID)
    validate_components(CONDITION_ID, components, spec)
    controller = components.neural.decision_source
    assert_state_independent(controller)
    return requirements()


def describe_interface() -> dict:
    spec = MotorFeatureSpec()
    return {
        "condition_id": CONDITION_ID,
        "readout": "BiasOnlyReadout(state_independent=True)",
        "feature_spec": spec.describe(),
        "actions": list(ACTION_SPACE),
        "trainable_parameters": ["bias"],
        "feature_weights": "fixed at exactly 0.0, excluded from the optimizer",
        "policy": "the same categorical distribution for every motor vector",
        "not_the_floor": (
            "Fβ trains its action distribution; the floor is constant "
            "NO_ACTION with no substrate"
        ),
    }


def run(
    components: Components,
    *,
    training_seeds: Any | None = None,
    evaluation_seeds: Any | None = None,
    spec: Any | None = None,
    **kwargs: Any,
) -> dict:
    validate(components, spec)
    controller = components.neural.decision_source
    training = bool(kwargs.get("training", False))
    if training and not bool(getattr(controller, "training", False)):
        raise ConditionError("a training episode needs a training controller")
    if training and getattr(controller, "trainer", None) is None:
        raise ConditionError("a training episode needs a REINFORCE trainer")
    if not training and bool(getattr(controller, "training", True)):
        raise ConditionError(
            "an evaluation episode must freeze the readout: build the "
            "controller with training=False"
        )
    if training_seeds is not None and evaluation_seeds is not None:
        assert_seed_disjoint(
            training_seeds, evaluation_seeds, label="condition Fβ"
        )
    elif (training_seeds is None) != (evaluation_seeds is None):
        raise ConditionError(
            "supply both training and evaluation seeds, or neither"
        )
    declared = spec_for(CONDITION_ID, spec)
    return neural_episode(CONDITION_ID, components, spec=spec, **kwargs) | {
        "declared_spec": declared.as_dict()
    }


__all__ = [
    "CONDITION_ID",
    "assert_state_independent",
    "assert_seed_disjoint",
    "build_components",
    "build_decision_source",
    "build_readout",
    "describe_interface",
    "requirements",
    "run",
    "validate",
]
