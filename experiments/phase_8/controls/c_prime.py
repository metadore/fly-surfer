"""Control C′ — condition C through the plastic code path at eta = 0.

SCIENTIFIC STATUS
    C′ is the random-graph mirror of A′ and the internal-validity control for
    D. It runs the same per-seed target-exchange graph ``G_s`` as C and D and
    must reproduce C exactly on all nineteen comparison fields of REV4
    §3.8.3, with the same zero tolerance and the same hard stop. A C′
    mismatch marks D INVALID exactly as an A′ mismatch marks B.
"""

from __future__ import annotations

from typing import Any

from ..conditions.base import (
    Components,
    ConditionError,
    Requirements,
    requirements_for,
    validate_components,
)
from ..conditions.execute import neural_episode
from . import zero_hook
from .equivalence import check_control_invariants, compare_runs

CONDITION_ID = "C_prime"
MIRROR = "C"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def install_hook(components: Components):
    return zero_hook.install_hook(components, control_id=CONDITION_ID)


def validate(components: Components, spec: Any | None = None) -> Requirements:
    validate_components(CONDITION_ID, components, spec)
    zero_hook.require_zero_hook(components, control_id=CONDITION_ID)
    structure = None if components.neural is None else components.neural.structure
    if structure is None:
        raise ConditionError(
            "C′ requires the per-seed structure record it shares with C and D"
        )
    return requirements()


def run(
    components: Components,
    *,
    fixed_result: dict,
    seed: int,
    episode: int,
    spec: Any | None = None,
    **kwargs: Any,
) -> dict:
    validate(components, spec)
    result = neural_episode(
        CONDITION_ID, components, seed=seed, episode=episode, spec=spec, **kwargs
    )
    fixed_structure = fixed_result.get("structure")
    if not isinstance(fixed_structure, dict):
        raise ConditionError(
            "the fixed-weight mirror C has no structure record; C′ cannot be "
            "certified against a different graph"
        )
    if fixed_structure["graph_digest"] != result["structure"]["graph_digest"]:
        raise ConditionError(
            "C′ and C ran on different random graphs; the paired structure "
            "requirement (R18) is broken"
        )
    invariants = check_control_invariants(result, control_id=CONDITION_ID)
    report = compare_runs(fixed_result, result, control_id=CONDITION_ID)
    result["equivalence"] = report
    result["zero_pathway"] = invariants
    return result


__all__ = [
    "CONDITION_ID",
    "MIRROR",
    "install_hook",
    "requirements",
    "run",
    "validate",
]
