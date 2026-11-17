"""Condition A — biological substrate, fixed weights, fixed decoder.

SCIENTIFIC STATUS
    A is the reference condition. It runs the frozen structural graph at its
    policy weights with the Phase 4 fixed-threshold decoder. It performs no
    learning and changes no weight. Its rows are not evidence of biological
    motor coding: a decoder label is not an identified motor command.
"""

from __future__ import annotations

from typing import Any

from .base import Components, Requirements, requirements_for, validate_components
from .execute import neural_episode

CONDITION_ID = "A"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def validate(components: Components, spec: Any | None = None) -> Requirements:
    return validate_components(CONDITION_ID, components, spec)


def run(components: Components, *, spec: Any | None = None, **kwargs: Any) -> dict:
    validate(components, spec)
    return neural_episode(CONDITION_ID, components, spec=spec, **kwargs)


__all__ = ["CONDITION_ID", "requirements", "run", "validate"]
