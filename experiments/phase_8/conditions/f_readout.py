"""Condition F — fixed neural substrate with a trainable linear readout.

SCIENTIFIC STATUS
    F keeps the connectome and every synaptic weight exactly as in A and
    trains only the readout that maps motor-population activity to an action.
    The readout sees the declared per-decision motor block and nothing else:
    not the seven sensory features, not the game state, not earlier actions
    (REV4 §3.6 row 6). An action from F is a readout label executed because
    the controlled game accepts it, not an identified motor command.

    Training episodes sample from the categorical readout and apply one
    REINFORCE update at the episode end. Evaluation episodes are argmax and
    the readout is frozen. Training and evaluation seeds must be disjoint.

    Fβ (the state-independent control) is not built here; it lives in
    ``experiments.phase_8.controls.f_beta`` and is refused by ``F``'s
    validator if it is supplied as F's decision source.
"""

from __future__ import annotations

from typing import Any

from readout.controller import ReadoutController
from readout.features import ACTION_SPACE, MotorFeatureSpec
from readout.linear import LinearReadout
from readout.trainer import ReinforceConfig, ReinforceTrainer

from .base import (
    Components,
    ConditionError,
    NeuralComponents,
    Requirements,
    assert_seed_disjoint,
    requirements_for,
    spec_for,
    validate_components,
)
from .execute import neural_episode

CONDITION_ID = "F"
DEFAULT_INIT_STD = 0.01


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def build_readout(
    *,
    n_features: int | None = None,
    seed: int = 0,
    init_std: float = DEFAULT_INIT_STD,
) -> LinearReadout:
    """The primary state-dependent readout over the motor feature vector."""
    width = (
        MotorFeatureSpec().n_features if n_features is None else int(n_features)
    )
    return LinearReadout(width, seed=int(seed), init_std=float(init_std))


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
    """One readout controller per episode, over the declared motor features."""
    spec = spec or MotorFeatureSpec()
    model = model or build_readout(n_features=spec.n_features, seed=seed)
    if int(getattr(model, "n_features", -1)) != int(spec.n_features):
        raise ConditionError(
            f"the readout expects {getattr(model, 'n_features', None)} features "
            f"but the motor spec emits {spec.n_features}"
        )
    if getattr(model, "state_independent", False):
        raise ConditionError(
            "F must not use a state-independent readout; that is Fβ"
        )
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
    if training and controller.trainer is None:  # pragma: no cover
        raise ConditionError("a training episode needs a REINFORCE trainer")
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
    """Assemble one F episode's neural components with a readout controller."""
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


def assert_state_dependent(controller: ReadoutController) -> None:
    if bool(getattr(controller, "state_independent", True)):
        raise ConditionError(
            "F's readout declares state independence; F requires the output to "
            "depend on motor-population activity"
        )


def assert_motor_only_interface(controller: ReadoutController) -> None:
    """The readout may consume only the declared motor block (REV4 §3.6)."""
    spec = getattr(controller, "spec", None)
    if not isinstance(spec, MotorFeatureSpec):
        raise ConditionError(
            "F's readout must use the declared MotorFeatureSpec; another spec "
            "could admit sensory or game-state features"
        )
    described = spec.describe()
    if described.get("excluded_inputs") != [
        "the seven sensory features",
        "game state",
        "previous actions",
    ]:
        raise ConditionError("the motor feature spec no longer excludes sensory input")


def validate(components: Components, spec: Any | None = None) -> Requirements:
    requirements_for(CONDITION_ID)
    validate_components(CONDITION_ID, components, spec)
    controller = components.neural.decision_source
    assert_state_dependent(controller)
    assert_motor_only_interface(controller)
    model = getattr(controller, "model", None)
    if model is not None and int(getattr(model, "n_features", -1)) != int(
        controller.n_features
    ):
        raise ConditionError("the readout input width does not match the motor spec")
    return requirements_for(CONDITION_ID)


def describe_interface() -> dict:
    spec = MotorFeatureSpec()
    return {
        "condition_id": CONDITION_ID,
        "readout": "LinearReadout(state_independent=False)",
        "feature_spec": spec.describe(),
        "actions": list(ACTION_SPACE),
        "init_std": DEFAULT_INIT_STD,
        "trainer": ReinforceConfig().describe(),
        "training_protocol": (
            "sample during training episodes; one REINFORCE update at the "
            "episode end; argmax and frozen at evaluation"
        ),
        "seed_policy": (
            "training and evaluation seeds must be disjoint; asserted before "
            "the episode starts"
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
    if training:
        if not bool(getattr(controller, "training", False)):
            raise ConditionError(
                "a training episode needs a controller in training mode"
            )
        if getattr(controller, "trainer", None) is None:
            raise ConditionError("a training episode needs a REINFORCE trainer")
    else:
        if bool(getattr(controller, "training", True)):
            raise ConditionError(
                "an evaluation episode must freeze the readout: build the "
                "controller with training=False"
            )
    if training_seeds is not None and evaluation_seeds is not None:
        assert_seed_disjoint(
            training_seeds, evaluation_seeds, label="condition F"
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
    "DEFAULT_INIT_STD",
    "assert_motor_only_interface",
    "assert_seed_disjoint",
    "assert_state_dependent",
    "build_components",
    "build_decision_source",
    "build_readout",
    "describe_interface",
    "requirements",
    "run",
    "validate",
]
