"""Phase 8 controls: A′, C′, Fβ, F-init and the substrate-free floor.

* ``a_prime`` — A through the plastic code path at eta = 0; must equal A
  exactly, field by field (P1–P19);
* ``c_prime`` — C through the plastic code path on the same per-seed random
  graph; must equal C exactly;
* ``f_beta`` — state-independent, bias-only readout; the constant-policy
  control for F;
* ``f_init`` — the F architecture at its seeded initial parameters, untrained;
* ``floor`` — constant NO_ACTION with no substrate; not a neural arm.

``equivalence`` implements the zero-tolerance comparison and the hard-stop
payload of REV4 §3.8.3–§3.8.5.
"""

from __future__ import annotations

from . import a_prime, c_prime, equivalence, f_beta, f_init, floor, zero_hook
from .equivalence import (
    CHECKS,
    COMPARISON_FIELDS,
    FIELD_ORDER,
    EquivalenceMismatch,
    check_control_invariants,
    compare_runs,
)

MODULES = {
    "A_prime": a_prime,
    "C_prime": c_prime,
    "F_beta": f_beta,
    "F_init": f_init,
    "floor": floor,
}

__all__ = [
    "CHECKS",
    "COMPARISON_FIELDS",
    "EquivalenceMismatch",
    "FIELD_ORDER",
    "MODULES",
    "a_prime",
    "c_prime",
    "check_control_invariants",
    "compare_runs",
    "equivalence",
    "f_beta",
    "f_init",
    "floor",
    "zero_hook",
]
