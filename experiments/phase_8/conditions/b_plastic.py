"""Condition B — biological substrate with three-factor synaptic plasticity.

SCIENTIFIC STATUS
    B runs the frozen structural graph and lets the declared three-factor rule
    change the learned weight layer during evaluation. Edges and transmitter
    signs are fixed; only weights move, within the declared bounds. A nonzero
    update is a model event, not evidence of learning.

``install_hook`` attaches the per-update plasticity hook the closed loop calls
after each game update. The hook consumes the adapter's own reward deliveries;
no reward value is recomputed here.
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

CONDITION_ID = "B"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def install_hook(
    components: Components,
    *,
    modulation_config: ModulationConfig | None = None,
) -> PlasticityUpdateHook:
    """Attach one hook per episode; a hook belongs to one stepper."""
    if components.neural is None:
        raise ConditionError("B needs neural components before a hook is built")
    if components.neural.post_update is not None:
        raise ConditionError(
            "the component bundle already has a post-update hook; build one "
            "per episode rather than reusing it"
        )
    hook = PlasticityUpdateHook(
        components.neural.stepper,
        modulation_config=modulation_config,
        provenance=(
            "condition B; adapter GameRewardFunction deliveries; values not "
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
