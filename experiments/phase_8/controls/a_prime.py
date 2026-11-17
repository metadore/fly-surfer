"""Control A′ — condition A through the plastic code path at eta = 0.

SCIENTIFIC STATUS
    A′ is an internal-validity control, not an experimental arm. It must
    reproduce A exactly on spike times, indices, fingerprints, every record
    field, action and reward counts, termination, motor activity and weights
    (REV4 §3.8.3). Any mismatch is a hard stop: A′ stops, B is marked INVALID,
    artefacts are retained, and no retry with a different seed is permitted.
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
CONDITION_ID = "A_prime"
MIRROR = "A"


def requirements() -> Requirements:
    return requirements_for(CONDITION_ID)


def install_hook(components: Components):
    return zero_hook.install_hook(components, control_id=CONDITION_ID)


def validate(components: Components, spec: Any | None = None) -> Requirements:
    validate_components(CONDITION_ID, components, spec)
    zero_hook.require_zero_hook(components, control_id=CONDITION_ID)
    if components.neural.structure is not None:
        raise ConditionError(
            "A′ runs on the biological graph; a random-graph structure record "
            "belongs to C′"
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
    """Run one A′ episode and compare it with the paired A result.

    ``fixed_result`` is the artefact returned by
    ``conditions.a_fixed.run`` for the same ``(seed, episode)``. A mismatch
    raises :class:`EquivalenceMismatch` after the control episode has been
    produced; the caller retains both artefacts.
    """
    validate(components, spec)
    result = neural_episode(
        CONDITION_ID, components, seed=seed, episode=episode, spec=spec, **kwargs
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
