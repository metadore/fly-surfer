"""Control F-init — the F readout at its seeded initial parameters, untrained.

SCIENTIFIC STATUS
    F-init is a diagnostic: it separates "the readout learned nothing useful"
    from "the readout cannot learn" (REV4 §3.6 row 12, claim 4). It has the F
    architecture and therefore a state-dependent policy, but no parameter
    moves. A difference between F and F-init is not by itself evidence of
    learning; the confirmatory comparison for claim 4 is F against Fβ.
"""

from __future__ import annotations

from typing import Any

from readout.features import MotorFeatureSpec
from readout.linear import LinearReadout

from ..conditions.base import (
    Components,
    ConditionError,
    NeuralComponents,
    Requirements,
    requirements_for,
    spec_for,
    validate_components,
)
from ..conditions.execute import neural_episode
from ..conditions.f_readout import DEFAULT_INIT_STD, build_decision_source

CONDITION_ID = "F_init"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def build_readout(
    *, n_features: int | None = None, seed: int = 0
) -> LinearReadout:
    width = (
        MotorFeatureSpec().n_features if n_features is None else int(n_features)
    )
    return LinearReadout(width, seed=int(seed), init_std=DEFAULT_INIT_STD)


def build_components(
    *,
    adapter: Any,
    stepper: Any,
    drive: Any,
    clock: Any,
    populations: Any,
    window_ms: float,
    seed: int = 0,
    sufficiency: Any | None = None,
    structure: dict | None = None,
    spec: MotorFeatureSpec | None = None,
    model: Any | None = None,
    metadata: dict | None = None,
) -> Components:
    spec = spec or MotorFeatureSpec()
    model = model or build_readout(n_features=spec.n_features, seed=seed)
    controller = build_decision_source(
        populations=populations,
        training=False,
        seed=seed,
        model=model,
        spec=spec,
    )
    controller.training = False
    controller.trainer = None
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
    validate_components(CONDITION_ID, components, spec)
    controller = components.neural.decision_source
    if getattr(controller, "state_independent", False):
        raise ConditionError(
            "F-init is the state-dependent F architecture at initial "
            "parameters, not the bias-only control"
        )
    if bool(getattr(controller, "training", False)):
        raise ConditionError("F-init must not train; the readout is frozen")
    if getattr(controller, "trainer", None) is not None:
        raise ConditionError("F-init must not own a trainer")
    return requirements()


def describe_interface() -> dict:
    return {
        "condition_id": CONDITION_ID,
        "readout": "LinearReadout(state_independent=False) at its seeded init",
        "parameter_change": "none by construction",
        "purpose": (
            "the non-constant but unlearned diagnostic for claim 4; not the "
            "constant-policy control (that is Fβ)"
        ),
    }


def run(components: Components, *, spec: Any | None = None, **kwargs: Any) -> dict:
    validate(components, spec)
    if bool(kwargs.get("training", False)):
        raise ConditionError("F-init has no training episode")
    declared = spec_for(CONDITION_ID, spec)
    return neural_episode(CONDITION_ID, components, spec=spec, **kwargs) | {
        "declared_spec": declared.as_dict()
    }


__all__ = [
    "CONDITION_ID",
    "build_components",
    "build_readout",
    "describe_interface",
    "requirements",
    "run",
    "validate",
]
