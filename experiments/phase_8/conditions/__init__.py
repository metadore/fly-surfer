"""Declared Phase 8 conditions A–F and their shared components.

Each module in this package is one declared condition:

* ``a_fixed`` — A: biological substrate, fixed weights, fixed decoder;
* ``b_plastic`` — B: biological substrate with three-factor plasticity;
* ``c_random`` — C: target-exchange random substrate, fixed weights;
* ``d_plastic`` — D: random substrate with three-factor plasticity;
* ``e_conventional`` — E / E-full: conventional REINFORCE on the game API;
* ``f_readout`` — F: fixed substrate with a trainable motor readout.

Controls live in :mod:`experiments.phase_8.controls` (A′, C′, Fβ, floor).

Nothing here loads a dataset or builds a graph. The caller injects the heavy
components and these modules prove the bundle matches the declaration before
an episode starts. A condition's presence is not evidence that it ran; the
episode row and its artefacts are.
"""

from __future__ import annotations

from . import a_fixed, b_plastic, c_random, d_plastic, e_conventional, f_readout
from .base import (
    CONVENTIONAL_CONDITIONS,
    CONTROL_MODES,
    CONTROL_REQUIREMENTS,
    IMPLEMENTED_CONDITIONS,
    NEURAL_CONDITIONS,
    REQUIREMENTS,
    Components,
    ConditionError,
    ConventionalComponents,
    NeuralComponents,
    Requirements,
    assert_seed_disjoint,
    describe_condition,
    is_plastic_stepper,
    requirements_for,
    spec_for,
    validate_components,
)
from .execute import (
    NO_ACTION,
    build_row,
    conventional_episode,
    decision_classes,
    error_row,
    floor_episode,
    motor_summary,
    neural_episode,
    trace_digest,
    utc_timestamp,
)
from .plasticity_hook import (
    PLASTICITY_MODES,
    AppendedRewardStream,
    PlasticityUpdateHook,
    zero_delta_arrays,
)

#: Condition id -> module, for the campaign and the G5 connection tests.
MODULES = {
    "A": a_fixed,
    "B": b_plastic,
    "C": c_random,
    "D": d_plastic,
    "E": e_conventional,
    "E_full": e_conventional,
    "F": f_readout,
}

__all__ = [
    "AppendedRewardStream",
    "CONVENTIONAL_CONDITIONS",
    "CONTROL_MODES",
    "CONTROL_REQUIREMENTS",
    "Components",
    "ConditionError",
    "ConventionalComponents",
    "IMPLEMENTED_CONDITIONS",
    "MODULES",
    "NEURAL_CONDITIONS",
    "NO_ACTION",
    "PLASTICITY_MODES",
    "PlasticityUpdateHook",
    "REQUIREMENTS",
    "Requirements",
    "a_fixed",
    "assert_seed_disjoint",
    "b_plastic",
    "build_row",
    "c_random",
    "conventional_episode",
    "d_plastic",
    "decision_classes",
    "describe_condition",
    "e_conventional",
    "error_row",
    "f_readout",
    "floor_episode",
    "is_plastic_stepper",
    "motor_summary",
    "neural_episode",
    "requirements_for",
    "spec_for",
    "trace_digest",
    "utc_timestamp",
    "validate_components",
    "zero_delta_arrays",
]
