"""Condition D — random control substrate with three-factor plasticity.

SCIENTIFIC STATUS
    D is B's plasticity on C's random substrate. The random graph is the same
    per-seed graph C and C′ receive (R18). Only the learned weight layer moves;
    the edge set and transmitter signs are fixed.
"""

from __future__ import annotations

from typing import Any

from plasticity.modulation import ModulationConfig

from .base import (
    Components,
    ConditionError,
    Requirements,
    requirements_for,
    validate_components,
)
from .execute import neural_episode
from .plasticity_hook import PlasticityUpdateHook

CONDITION_ID = "D"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def install_hook(
    components: Components,
    *,
    modulation_config: ModulationConfig | None = None,
) -> PlasticityUpdateHook:
    if components.neural is None:
        raise ConditionError("D needs neural components before a hook is built")
    if components.neural.post_update is not None:
        raise ConditionError(
            "the component bundle already has a post-update hook; build one "
            "per episode rather than reusing it"
        )
    hook = PlasticityUpdateHook(
        components.neural.stepper,
        modulation_config=modulation_config,
        provenance=(
            "condition D; adapter GameRewardFunction deliveries; values not "
            "recomputed"
        ),
    )
    components.neural.post_update = hook
    return hook


def validate(components: Components, spec: Any | None = None) -> Requirements:
    return validate_components(CONDITION_ID, components, spec)


def run(components: Components, *, spec: Any | None = None, **kwargs: Any) -> dict:
    validate(components, spec)
    return neural_episode(CONDITION_ID, components, spec=spec, **kwargs)


__all__ = [
    "CONDITION_ID",
    "install_hook",
    "requirements",
    "run",
    "validate",
]
