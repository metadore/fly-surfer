"""Condition C — degree- and sign-preserving random control, fixed weights.

SCIENTIFIC STATUS
    C replaces the biological edge targets with the target-exchange random
    control of REV4 §3.3. The random graph preserves out-degree, in-degree,
    every source's outgoing weight multiset and per-node transmitter sign. It
    is not a null model fitted to data and it is not a physiological
    preparation. C runs no plasticity.
"""

from __future__ import annotations

from typing import Any

from .base import (
    Components,
    ConditionError,
    Requirements,
    requirements_for,
    validate_components,
)
from .execute import neural_episode

CONDITION_ID = "C"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def validate(components: Components, spec: Any | None = None) -> Requirements:
    return validate_components(CONDITION_ID, components, spec)


def run(components: Components, *, spec: Any | None = None, **kwargs: Any) -> dict:
    validate(components, spec)
    result = neural_episode(CONDITION_ID, components, spec=spec, **kwargs)
    structure = result["structure"]
    if structure is None:  # pragma: no cover - validate already refuses this
        raise ConditionError("C produced a row without a structure record")
    return result


__all__ = ["CONDITION_ID", "requirements", "run", "validate"]
