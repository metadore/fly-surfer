"""The Phase 8 arm registry and the confirmatory family.

Every arm is declared once, from ``configs/phase_8/conditions.yaml`` plus the
substrate-free floor, so the campaign, the analysis and the report cannot
disagree about what ran or which contrast means what. The confirmatory family
C1–C4 is REV3 §5.3; nothing outside it may be promoted after seeing data.

`floor` is an arm, not a condition: it reads no spikes, owns no substrate and
is measured by replaying the paired environment seeds with a constant
``NO_ACTION`` policy (REV3 §3.6.2). It is still recorded as rows, because the
analysis compares every condition against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .config import (
    CampaignConfig,
    ConditionsConfig,
    ConfigError,
    Phase8Config,
    load_conditions_config,
)
from .seeds import FLOOR_ID


@dataclass(frozen=True)
class ConditionSpec:
    condition_id: str
    group: str
    role: str
    substrate: str
    plasticity: str
    controller: str
    trains: tuple[str, ...]
    eta: float | None
    requires_structure: bool = False
    exact_match_of: str | None = None
    state_independent: bool = False
    init_only: bool = False
    feature_set: str | None = None

    @property
    def has_neural_substrate(self) -> bool:
        return self.substrate != "none"

    @property
    def changes_during_evaluation(self) -> bool:
        return self.trains != ("none",)

    def as_dict(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "group": self.group,
            "role": self.role,
            "substrate": self.substrate,
            "plasticity": self.plasticity,
            "controller": self.controller,
            "trains": list(self.trains),
            "eta": self.eta,
            "requires_structure": self.requires_structure,
            "exact_match_of": self.exact_match_of,
            "state_independent": self.state_independent,
            "init_only": self.init_only,
            "feature_set": self.feature_set,
        }


def _spec(condition_id: str, payload: dict, group: str) -> ConditionSpec:
    return ConditionSpec(
        condition_id=condition_id,
        group=group,
        role=payload["role"],
        substrate=payload["substrate"],
        plasticity=payload["plasticity"],
        controller=payload["controller"],
        trains=tuple(payload["trains"]),
        eta=payload["eta"],
        requires_structure=bool(payload.get("requires_structure", False)),
        exact_match_of=payload.get("requires_exact_match_of"),
        state_independent=bool(payload.get("state_independent", False)),
        init_only=bool(payload.get("init_only", False)),
        feature_set=payload.get("feature_set"),
    )


FLOOR_SPEC = ConditionSpec(
    condition_id=FLOOR_ID,
    group="floor",
    role="floor",
    substrate="none",
    plasticity="none",
    controller="constant_no_action",
    trains=("none",),
    eta=None,
)


@dataclass(frozen=True)
class Registry:
    arms: dict[str, ConditionSpec]

    def spec(self, condition_id: str) -> ConditionSpec:
        try:
            return self.arms[condition_id]
        except KeyError:
            raise ConfigError(f"arm {condition_id!r} is not registered") from None

    @property
    def conditions(self) -> tuple[str, ...]:
        return tuple(
            key for key, spec in self.arms.items() if spec.group == "condition"
        )

    @property
    def controls(self) -> tuple[str, ...]:
        return tuple(
            key for key, spec in self.arms.items() if spec.group == "control"
        )

    @property
    def exploratory(self) -> tuple[str, ...]:
        return tuple(
            key for key, spec in self.arms.items() if spec.group == "exploratory"
        )

    @property
    def evaluation_arms(self) -> tuple[str, ...]:
        """Every arm that produces evaluation rows, in declaration order."""
        return tuple(self.arms)

    def as_dict(self) -> dict:
        return {key: spec.as_dict() for key, spec in self.arms.items()}


def build_registry(conditions: ConditionsConfig) -> Registry:
    arms: dict[str, ConditionSpec] = {}
    for group_name, group in (
        ("condition", conditions.conditions),
        ("control", conditions.controls),
        ("exploratory", conditions.exploratory),
    ):
        for condition_id, payload in group.items():
            arms[condition_id] = _spec(condition_id, payload, group_name)
    arms[FLOOR_ID] = FLOOR_SPEC
    return Registry(arms=arms)


@lru_cache(maxsize=1)
def default_registry() -> Registry:
    return build_registry(load_conditions_config())


CONFIRMATORY_CONTRASTS = (
    {
        "id": "C1",
        "minuend": "F",
        "subtrahend": "A",
        "hypothesis": "H3",
        "question": "contribution of a trainable readout on the biological substrate",
    },
    {
        "id": "C2",
        "minuend": "B",
        "subtrahend": "A",
        "hypothesis": "H1",
        "question": "contribution of three-factor synaptic plasticity",
    },
    {
        "id": "C3",
        "minuend": "A",
        "subtrahend": "C",
        "hypothesis": "H2",
        "question": "contribution of biological over degree+sign-matched connectivity",
    },
    {
        "id": "C4",
        "minuend": "F",
        "subtrahend": "F_beta",
        "hypothesis": "§3.6.2 claim 2",
        "question": "whether the readout uses motor information at all",
    },
)


def confirmatory_contrasts(family_size: int | None = None) -> tuple[dict, ...]:
    """C1–C4, or C1–C3 when U14 selects m = 3."""
    if family_size is None:
        return tuple(dict(item) for item in CONFIRMATORY_CONTRASTS)
    if family_size == 4:
        return tuple(dict(item) for item in CONFIRMATORY_CONTRASTS)
    if family_size == 3:
        return tuple(dict(item) for item in CONFIRMATORY_CONTRASTS[:3])
    raise ConfigError("the Holm family size must be 4 or 3 (REV3 U14)")


def assert_confirmatory_family(registry: Registry, family_size: int = 4) -> None:
    """Every contrast member must be a registered condition."""
    registered = set(registry.conditions)
    for contrast in confirmatory_contrasts(family_size):
        for name in (contrast["minuend"], contrast["subtrahend"]):
            if name not in registered:
                raise ConfigError(
                    f"{contrast['id']} uses {name!r}, which is not a registered condition"
                )


def evaluation_plan(config: Phase8Config) -> tuple[tuple[str, int, int], ...]:
    """The full ``(arm, seed, episode)`` grid for a selected design.

    Raises when ``n_seeds_selected`` is still null: the 10.8 pilot decision is
    part of the design, not something the harness may assume (REV3 U7).
    """
    campaign: CampaignConfig = config.campaign
    seeds = campaign.active_seeds()
    registry = build_registry(config.conditions)
    plan: list[tuple[str, int, int]] = []
    for arm in registry.evaluation_arms:
        for seed in seeds:
            for episode in range(campaign.episodes_per_seed):
                plan.append((arm, int(seed), int(episode)))
    return tuple(plan)


def describe(config: Phase8Config | None = None) -> dict:
    registry = build_registry(config.conditions) if config else default_registry()
    payload = {
        "arms": registry.as_dict(),
        "confirmatory_family_m4": list(confirmatory_contrasts(4)),
        "confirmatory_family_m3": list(confirmatory_contrasts(3)),
        "note": (
            "only C1–C4 are confirmatory; every other arm is a control, an "
            "exploratory variant or the substrate-free floor"
        ),
    }
    if config is not None:
        payload["declared_conditions"] = list(config.campaign.conditions)
        payload["declared_controls"] = list(config.campaign.control_arms)
        payload["declared_exploratory"] = list(config.campaign.exploratory_arms)
        payload["floor"] = config.campaign.floor_arm
    return payload


__all__ = [
    "CONFIRMATORY_CONTRASTS",
    "ConditionSpec",
    "FLOOR_SPEC",
    "Registry",
    "assert_confirmatory_family",
    "build_registry",
    "confirmatory_contrasts",
    "default_registry",
    "describe",
    "evaluation_plan",
]
