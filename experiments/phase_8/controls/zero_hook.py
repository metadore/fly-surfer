"""Zero-learning-rate hook shared by A′ and C′.

SCIENTIFIC STATUS
    A′/C′ must route the episode through the plastic code path, so the hook
    exists and executes one three-factor update per game update. ``eta`` is
    exactly ``0.0``; the rule computes traces and returns an exactly zero
    delta (REV4 §3.8.2). Skipping the hook entirely is not the control.
"""

from __future__ import annotations

from typing import Any

from ..conditions.base import ConditionError, Components, is_plastic_stepper
from ..conditions.plasticity_hook import PlasticityUpdateHook


def install_hook(components: Components, *, control_id: str) -> PlasticityUpdateHook:
    if components.neural is None:
        raise ConditionError(f"{control_id} needs neural components")
    if components.neural.post_update is not None:
        raise ConditionError(
            "the component bundle already has a post-update hook; build one "
            "per episode rather than reusing it"
        )
    stepper = components.neural.stepper
    if not is_plastic_stepper(stepper):
        raise ConditionError(
            f"{control_id} must run the plastic stepper, not the fixed pathway"
        )
    eta = float(getattr(stepper, "eta", float("nan")))
    if eta != 0.0:
        raise ConditionError(
            f"{control_id} requires eta = 0.0 exactly, stepper has {eta}"
        )
    hook = PlasticityUpdateHook(
        stepper,
        provenance=(
            f"{control_id}; adapter GameRewardFunction deliveries; eta = 0.0; "
            "the rule executes and must return an exactly zero delta"
        ),
    )
    components.neural.post_update = hook
    return hook


def require_zero_hook(components: Components, *, control_id: str) -> Any:
    hook = None if components.neural is None else components.neural.post_update
    if not isinstance(hook, PlasticityUpdateHook):
        raise ConditionError(
            f"{control_id} requires the zero-rate plasticity hook; got "
            f"{type(hook).__name__ if hook is not None else None}"
        )
    if float(hook.eta) != 0.0:
        raise ConditionError(f"{control_id} requires eta = 0.0 exactly")
    return hook


__all__ = ["install_hook", "require_zero_hook"]
