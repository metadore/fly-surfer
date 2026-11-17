"""Condition E — a conventional REINFORCE learner on the five-tuple API.

SCIENTIFIC STATUS
    E is a reference learner, not a matched control for synaptic plasticity
    (REV4 §3.5 row 11). It sees declared scalar game observations, never
    neural activity, spikes or weights, and it trains its own policy
    parameters directly. There is no Gymnasium or Stable-Baselines3
    dependency and no privileged access to hidden or future game state.

    E-matched consumes the seven features that the neural encoders also
    receive; E-full consumes all fourteen. The feature set is declared here,
    fixed before any run, and never fitted.

Training and evaluation seeds must be disjoint (§6.6). The check is a hard
error, not a warning, and it runs before the episode starts.
"""

from __future__ import annotations

from typing import Any

from evaluation.conventional import ConventionalAgent, ConventionalConfig
from evaluation.observations import FULL_SPEC, MATCHED_SPEC, ObservationEncoder

from .base import (
    Components,
    ConditionError,
    ConventionalComponents,
    Requirements,
    assert_seed_disjoint,
    requirements_for,
    spec_for,
    validate_components,
)
from .execute import conventional_episode

CONDITION_IDS = ("E", "E_full")


def _check_condition(condition_id: str) -> str:
    if condition_id not in CONDITION_IDS:
        raise ConditionError(
            f"{condition_id!r} is not a conventional condition; "
            f"implemented: {list(CONDITION_IDS)}"
        )
    return condition_id


def spec_for_condition(condition_id: str = "E"):
    """The declared observation spec: seven features for E, fourteen for E-full."""
    return MATCHED_SPEC if _check_condition(condition_id) == "E" else FULL_SPEC


def requirements(condition_id: str = "E") -> Requirements:
    return requirements_for(_check_condition(condition_id))


def build_encoder(condition_id: str = "E") -> ObservationEncoder:
    return ObservationEncoder(spec_for_condition(condition_id))


def build_agent(
    condition_id: str = "E",
    *,
    seed: Any = 0,
    training: bool = True,
    config: ConventionalConfig | None = None,
) -> ConventionalAgent:
    encoder = build_encoder(condition_id)
    return ConventionalAgent(
        encoder.n_features, config=config, seed=seed, training=training
    )


def build_components(
    environment: Any,
    *,
    condition_id: str = "E",
    seed: Any = 0,
    training: bool = True,
    agent: ConventionalAgent | None = None,
    encoder: ObservationEncoder | None = None,
    config: ConventionalConfig | None = None,
    metadata: dict | None = None,
) -> Components:
    """Assemble one E (or E-full) episode's component bundle."""
    _check_condition(condition_id)
    encoder = encoder or build_encoder(condition_id)
    if agent is None:
        agent = build_agent(
            condition_id, seed=seed, training=training, config=config
        )
    elif int(agent.n_features) != int(encoder.n_features):
        raise ConditionError(
            f"the agent expects {agent.n_features} features and the encoder "
            f"emits {encoder.n_features}"
        )
    return Components(
        conventional=ConventionalComponents(
            environment=environment,
            agent=agent,
            encoder=encoder,
            metadata=dict(metadata or {}),
        ),
        metadata={"condition_id": condition_id, **dict(metadata or {})},
    )


def assert_no_privileged_input(encoder: ObservationEncoder) -> None:
    """The encoder may only read ``GameState.features()``.

    This is a declaration check: the encoder is the class in
    :mod:`evaluation.observations`, whose only input is a ``GameState``, and
    the declared feature list is a subset of the fourteen public features.
    """
    if not isinstance(encoder, ObservationEncoder):
        raise ConditionError(
            "condition E must use the declared ObservationEncoder; a custom "
            "encoder could read hidden or future game state"
        )
    described = encoder.describe()
    if described.get("privileged_information"):
        raise ConditionError("the observation spec declares privileged input")


def validate(
    components: Components,
    condition_id: str = "E",
    spec: Any | None = None,
) -> Requirements:
    _check_condition(condition_id)
    requirements_for(condition_id)
    validate_components(condition_id, components, spec)
    assert_no_privileged_input(components.conventional.encoder)
    return requirements_for(condition_id)


def describe_interface(condition_id: str = "E") -> dict:
    """Declared features and capacity of the E learner."""
    encoder = build_encoder(condition_id)
    payload = encoder.describe()
    payload["condition_id"] = condition_id
    payload["agent"] = "ConventionalAgent (actor-critic REINFORCE)"
    payload["additional_capacity"] = {
        "hidden_units": ConventionalConfig().hidden_units,
        "hidden_layers": ConventionalConfig().hidden_layers,
        "heads": ["policy(4 actions)", "value(1)"],
    }
    payload["training_seed_policy"] = (
        "training and evaluation seeds must be disjoint; asserted before the "
        "episode starts"
    )
    payload["dependencies"] = "torch; no gymnasium, no stable-baselines3"
    return payload


def run(
    components: Components,
    *,
    condition_id: str = "E",
    training_seeds: Any | None = None,
    evaluation_seeds: Any | None = None,
    spec: Any | None = None,
    **kwargs: Any,
) -> dict:
    """Run one E episode.

    When seed sets are supplied both are checked for disjointness before any
    game step executes. The episode's own ``seed`` and ``environment_seed``
    remain the caller's responsibility and are validated by the row builder.
    """
    _check_condition(condition_id)
    validate(components, condition_id, spec)
    if training_seeds is not None and evaluation_seeds is not None:
        assert_seed_disjoint(
            training_seeds,
            evaluation_seeds,
            label=f"condition {condition_id}",
        )
    elif (training_seeds is None) != (evaluation_seeds is None):
        raise ConditionError(
            "supply both training and evaluation seeds, or neither"
        )
    declared = spec_for(condition_id, spec)
    return conventional_episode(
        condition_id, components, spec=spec, **kwargs
    ) | {"declared_spec": declared.as_dict()}


__all__ = [
    "CONDITION_IDS",
    "assert_no_privileged_input",
    "assert_seed_disjoint",
    "build_agent",
    "build_components",
    "build_encoder",
    "describe_interface",
    "requirements",
    "run",
    "spec_for_condition",
    "validate",
]
