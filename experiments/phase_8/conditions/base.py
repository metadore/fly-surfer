"""Declared components and validation for Phase 8 conditions A–F.

SCIENTIFIC STATUS
    This package assembles existing components. It adds no biological
    mechanism. A condition is a declared combination of substrate, plasticity,
    controller and trainable parameters (REV4 §3); the substrate is either the
    frozen connectome or a degree-and-sign-preserving random control, never a
    measured physiological preparation. Structural connectivity is not a
    physiological measurement.

Every condition is described by the same record:

* ``requirements`` — which components the condition must be given;
* ``initialisation`` — what is built and how it is seeded;
* ``reset`` — what returns to its initial state at an episode boundary;
* ``state`` — what is allowed to change during an episode;
* ``outputs`` — the validated episode row and the per-decision records.

The heavy objects (a BANC-scale graph, a simulator, a game environment) are
injected by the caller. Tests build small synthetic graphs and environments;
the campaign builds the frozen artifacts. Nothing here loads a dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..registry import ConditionSpec, default_registry

#: Conditions implemented in this package. ``E_full`` is exploratory.
NEURAL_CONDITIONS = ("A", "B", "C", "D", "F")
CONVENTIONAL_CONDITIONS = ("E", "E_full")
IMPLEMENTED_CONDITIONS = (*NEURAL_CONDITIONS, *CONVENTIONAL_CONDITIONS)


class ConditionError(RuntimeError):
    """A condition was given components that contradict its declaration."""


@dataclass(frozen=True)
class Requirements:
    """What a condition must receive before an episode may start."""

    uses_neural_loop: bool = True
    stepper_kind: str | None = None  # "fixed" | "plastic" | None
    needs_adapter: bool = True
    needs_drive: bool = True
    needs_clock: bool = True
    needs_decoder: bool = False
    needs_decision_source: bool = False
    needs_post_update: bool = False
    needs_game_environment: bool = False
    needs_agent: bool = False
    needs_encoder: bool = False
    needs_motor_populations: bool = False
    requires_structure: bool = False
    trains: tuple[str, ...] = ("none",)
    eta: float | None = None

    def as_dict(self) -> dict:
        return {
            "uses_neural_loop": self.uses_neural_loop,
            "stepper_kind": self.stepper_kind,
            "needs_adapter": self.needs_adapter,
            "needs_drive": self.needs_drive,
            "needs_clock": self.needs_clock,
            "needs_decoder": self.needs_decoder,
            "needs_decision_source": self.needs_decision_source,
            "needs_post_update": self.needs_post_update,
            "needs_game_environment": self.needs_game_environment,
            "needs_agent": self.needs_agent,
            "needs_encoder": self.needs_encoder,
            "needs_motor_populations": self.needs_motor_populations,
            "requires_structure": self.requires_structure,
            "trains": list(self.trains),
            "eta": self.eta,
        }


#: The declaration that G1–G4 must satisfy. Frozen plasticity values are
#: repeated from ``configs/phase_8/conditions.yaml``; they are not tuned here.
REQUIREMENTS: dict[str, Requirements] = {
    "A": Requirements(
        stepper_kind="fixed", needs_decoder=True, needs_motor_populations=True
    ),
    "B": Requirements(
        stepper_kind="plastic",
        needs_decoder=True,
        needs_post_update=True,
        needs_motor_populations=True,
        trains=("synapses",),
        eta=0.5,
    ),
    "C": Requirements(
        stepper_kind="fixed",
        needs_decoder=True,
        needs_motor_populations=True,
        requires_structure=True,
    ),
    "D": Requirements(
        stepper_kind="plastic",
        needs_decoder=True,
        needs_post_update=True,
        needs_motor_populations=True,
        requires_structure=True,
        trains=("synapses",),
        eta=0.5,
    ),
    "E": Requirements(
        uses_neural_loop=False,
        stepper_kind=None,
        needs_adapter=False,
        needs_drive=False,
        needs_clock=False,
        needs_game_environment=True,
        needs_agent=True,
        needs_encoder=True,
        trains=("policy",),
    ),
    "E_full": Requirements(
        uses_neural_loop=False,
        stepper_kind=None,
        needs_adapter=False,
        needs_drive=False,
        needs_clock=False,
        needs_game_environment=True,
        needs_agent=True,
        needs_encoder=True,
        trains=("policy",),
    ),
    "F": Requirements(
        stepper_kind="fixed",
        needs_decision_source=True,
        needs_motor_populations=True,
        trains=("readout",),
    ),
}

CONTROL_MODES: dict[str, dict] = {
    "A_prime": {"eta": 0.0, "exact_match_of": "A", "uses_neural_loop": True},
    "C_prime": {
        "eta": 0.0,
        "exact_match_of": "C",
        "uses_neural_loop": True,
        "requires_structure": True,
    },
    "F_beta": {"eta": None, "exact_match_of": "F", "state_independent": True},
    "F_init": {"eta": None, "exact_match_of": "F", "init_only": True},
    "floor": {"eta": None, "substrate": "none", "policy": "constant_no_action"},
}

#: Control arms run the same components under a restricted declaration. A′ and
#: C′ route the episode through the plastic stepper at exactly eta = 0.0 so the
#: rule executes and must return an exactly zero delta (REV4 §3.8.2).
CONTROL_REQUIREMENTS: dict[str, Requirements] = {
    "A_prime": Requirements(
        stepper_kind="plastic",
        needs_decoder=True,
        needs_motor_populations=True,
        needs_post_update=True,
        trains=("none",),
        eta=0.0,
    ),
    "C_prime": Requirements(
        stepper_kind="plastic",
        needs_decoder=True,
        needs_motor_populations=True,
        needs_post_update=True,
        requires_structure=True,
        trains=("none",),
        eta=0.0,
    ),
    "F_beta": Requirements(
        stepper_kind="fixed",
        needs_decision_source=True,
        needs_motor_populations=True,
        trains=("readout",),
    ),
    "F_init": Requirements(
        stepper_kind="fixed",
        needs_decision_source=True,
        needs_motor_populations=True,
        trains=("none",),
    ),
}


@dataclass
class NeuralComponents:
    """Everything a neural condition needs; built by the caller per episode.

    ``structure`` carries the graph certificate for C, D and C′ (R18: one
    random graph per seed shared by all three). It is ``None`` for conditions
    on the biological graph.
    """

    adapter: Any
    stepper: Any
    drive: Any
    clock: Any
    action_decoder: Any | None = None
    decision_source: Any | None = None
    post_update: Any | None = None
    window_ms: float | None = None
    populations: Any | None = None
    sufficiency: Any | None = None
    structure: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ConventionalComponents:
    """Condition E: a game environment, an observation encoder and an agent."""

    environment: Any
    agent: Any
    encoder: Any
    metadata: dict = field(default_factory=dict)


@dataclass
class Components:
    """The per-episode component bundle handed to one condition."""

    neural: NeuralComponents | None = None
    conventional: ConventionalComponents | None = None
    metadata: dict = field(default_factory=dict)


def is_plastic_stepper(stepper: Any) -> bool:
    """A plastic stepper owns an engine, a weight state and ``learn``."""
    return all(
        hasattr(stepper, name) for name in ("engine", "weight_state", "learn")
    )


def assert_seed_disjoint(
    training_seeds: Any, evaluation_seeds: Any, *, label: str = "seeds"
) -> tuple[int, ...]:
    """Refuse overlapping training and evaluation seeds (REV4 §6.6).

    Returns the sorted evaluation seeds. Overlap is a hard error: a leak
    would let an evaluation episode be scored on data the learner trained on.
    """
    training = {int(value) for value in training_seeds}
    evaluation = {int(value) for value in evaluation_seeds}
    if not training or not evaluation:
        raise ConditionError(f"{label}: both seed sets must be non-empty")
    overlap = sorted(training & evaluation)
    if overlap:
        raise ConditionError(
            f"{label}: training and evaluation seeds overlap at {overlap}; "
            "the learner would be evaluated on its training distribution"
        )
    return tuple(sorted(evaluation))


def spec_for(
    condition_id: str, spec: ConditionSpec | None = None
) -> ConditionSpec:
    if spec is not None:
        return spec
    return default_registry().spec(condition_id)


def requirements_for(condition_id: str) -> Requirements:
    if condition_id in REQUIREMENTS:
        return REQUIREMENTS[condition_id]
    if condition_id in CONTROL_REQUIREMENTS:
        return CONTROL_REQUIREMENTS[condition_id]
    raise ConditionError(
        f"{condition_id!r} is not an implemented condition or control; "
        f"implemented: {list(REQUIREMENTS) + list(CONTROL_REQUIREMENTS)}"
    )


def _require(components: Components, name: str) -> Any:
    value = getattr(components.neural, name, None)
    if value is None:
        raise ConditionError(f"the condition requires {name}")
    return value


def _check_structure(structure: dict | None) -> dict:
    if not isinstance(structure, dict):
        raise ConditionError(
            "conditions C, D and C′ require the per-seed structure record"
        )
    digest = structure.get("graph_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ConditionError(
            "the structure record needs a 64-hex graph_digest"
        )
    quality = structure.get("randomization_quality")
    if not isinstance(quality, dict) or "passed" not in quality:
        raise ConditionError(
            "the structure record needs the randomization quality report"
        )
    if not quality["passed"]:
        raise ConditionError(
            "the randomization gates did not pass; C/D/C′ may not run on this "
            f"graph (failures: {quality.get('failures')})"
        )
    return structure


def validate_components(
    condition_id: str,
    components: Components,
    spec: ConditionSpec | None = None,
) -> Requirements:
    """Refuse a component bundle that contradicts the declaration.

    This is a structural check, not a scientific one: it proves the episode
    will run the declared pathway, not that the pathway is adequate.
    """
    requirements = requirements_for(condition_id)
    declared = spec_for(condition_id, spec)
    if components.neural is not None and components.conventional is not None:
        raise ConditionError("a condition receives either neural or conventional components")
    if requirements.uses_neural_loop:
        if components.neural is None:
            raise ConditionError(
                f"{condition_id} runs the neural closed loop and needs neural components"
            )
        for name, required in (
            ("adapter", requirements.needs_adapter),
            ("drive", requirements.needs_drive),
            ("clock", requirements.needs_clock),
            ("action_decoder", requirements.needs_decoder),
            ("decision_source", requirements.needs_decision_source),
            ("post_update", requirements.needs_post_update),
            ("populations", requirements.needs_motor_populations),
        ):
            if required:
                _require(components, name)
        stepper = _require(components, "stepper")
        plastic = is_plastic_stepper(stepper)
        if requirements.stepper_kind == "fixed" and plastic:
            raise ConditionError(
                f"{condition_id} must run the fixed-weight stepper, but the "
                "supplied stepper owns a plasticity engine"
            )
        if requirements.stepper_kind == "plastic" and not plastic:
            raise ConditionError(
                f"{condition_id} must run the plastic pathway, but the "
                "supplied stepper has no engine/weight_state/learn"
            )
        if requirements.stepper_kind == "plastic":
            eta = float(getattr(stepper, "eta", np.nan))
            expected = declared.eta if declared.eta is not None else requirements.eta
            if expected is None or eta != float(expected):
                raise ConditionError(
                    f"{condition_id} requires eta = {expected}, stepper has {eta}"
                )
            for name in ("reset", "learn"):
                if not callable(getattr(stepper, name, None)):
                    raise ConditionError(
                        f"the plastic stepper must provide {name}()"
                    )
        if requirements.requires_structure:
            _check_structure(components.neural.structure)
        if condition_id == "F":
            source = components.neural.decision_source
            if getattr(source, "state_independent", False):
                raise ConditionError(
                    "F needs a state-dependent readout; the supplied decision "
                    "source declares itself state-independent (that is Fβ)"
                )
            if not callable(getattr(source, "decide", None)):
                raise ConditionError("the F decision source must provide decide()")
        if condition_id == "F_beta":
            source = components.neural.decision_source
            if not bool(getattr(source, "state_independent", False)):
                raise ConditionError(
                    "Fβ needs a state-independent readout; the supplied "
                    "decision source depends on the motor features (that is F)"
                )
            if not callable(getattr(source, "decide", None)):
                raise ConditionError("the Fβ decision source must provide decide()")
        if condition_id == "F_init":
            source = components.neural.decision_source
            if bool(getattr(source, "state_independent", False)):
                raise ConditionError(
                    "F-init is the F architecture at its initial parameters, "
                    "not the bias-only control"
                )
            if bool(getattr(source, "training", False)):
                raise ConditionError("F-init must not train; the readout is frozen")
            if getattr(source, "trainer", None) is not None:
                raise ConditionError("F-init must not own a trainer")
        if condition_id in ("A", "C") and declared.trains != ("none",):
            raise ConditionError(f"{condition_id} must not train anything")
        if condition_id in ("A_prime", "C_prime", "F_init"):
            if declared.trains != ("none",):
                raise ConditionError(f"{condition_id} must not train anything")
            if condition_id != "F_init":
                if float(getattr(stepper, "eta", np.nan)) != 0.0:
                    raise ConditionError(
                        f"{condition_id} must run the plastic pathway at exactly "
                        f"eta = 0.0, stepper has {getattr(stepper, 'eta', None)}"
                    )
    else:
        if components.conventional is None:
            raise ConditionError(
                f"{condition_id} runs on the game API and needs conventional components"
            )
        for name in ("environment", "agent", "encoder"):
            if getattr(components.conventional, name, None) is None:
                raise ConditionError(f"{condition_id} requires {name}")
        if declared.trains != ("policy",) and condition_id != "E_full":
            raise ConditionError(f"{condition_id} must train its policy")
        encoder_features = int(getattr(components.conventional.encoder, "n_features", -1))
        agent_features = int(getattr(components.conventional.agent, "n_features", -2))
        if encoder_features != agent_features:
            raise ConditionError(
                f"the encoder emits {encoder_features} features and the agent "
                f"expects {agent_features}"
            )
        expected = 7 if condition_id == "E" else 14
        if encoder_features != expected:
            raise ConditionError(
                f"{condition_id} declares the {expected}-feature set, the "
                f"encoder emits {encoder_features}"
            )
    if components.metadata.get("condition_id") not in (None, condition_id):
        raise ConditionError(
            "the component metadata names a different condition"
        )
    return requirements


def describe_condition(condition_id: str) -> dict:
    """The declared record for one condition or control."""
    requirements = requirements_for(condition_id)
    spec = spec_for(condition_id)
    return {
        "condition_id": condition_id,
        "requirements": requirements.as_dict(),
        "declared_spec": spec.as_dict(),
        "initialisation": (
            "the caller builds every component per episode; seeds come from "
            "the declared streams (REV4 §6.3)"
        ),
        "reset": (
            "adapter, stepper, drive, decoder/readout, and (plastic) traces "
            "return to the episode start; learned deltas are part of the "
            "stepper, not of the episode reset"
            if requirements.uses_neural_loop
            else "environment and agent episode buffers reset; network "
            "parameters persist across episodes"
        ),
        "state_that_may_change": list(requirements.trains),
        "scientific_limitations": [
            "structural connectivity is not a physiological measurement",
            "a decoder label is not an identified biological motor command",
            "a nonzero weight update is not evidence of learning",
        ],
    }


__all__ = [
    "CONVENTIONAL_CONDITIONS",
    "CONTROL_MODES",
    "CONTROL_REQUIREMENTS",
    "assert_seed_disjoint",
    "Components",
    "ConditionError",
    "ConventionalComponents",
    "IMPLEMENTED_CONDITIONS",
    "NEURAL_CONDITIONS",
    "NeuralComponents",
    "REQUIREMENTS",
    "Requirements",
    "describe_condition",
    "is_plastic_stepper",
    "requirements_for",
    "spec_for",
    "validate_components",
]
