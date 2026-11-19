"""Validated training configuration for Phase 8.

SCIENTIFIC STATUS
    This module checks that the declared training constants match REV4's
    Appendix C and the code constants REV4 pins. It does not choose, tune or
    fill any value. Two categories of number exist and are kept apart:

    * **declared** — written in REV4: 20 training episodes per seed for F and
      Fβ, 2,000 gradient updates for E, a linear F readout over four actions,
      and E's 7/14-feature 2×64 tanh MLP;
    * **implementation constants** — REV4 says these are "declared in config,
      not tuned per seed" without pinning a number. They are read from the
      existing modules (:class:`readout.trainer.ReinforceConfig`,
      :class:`evaluation.conventional.ConventionalConfig`,
      ``f_readout.DEFAULT_INIT_STD``), recorded verbatim, and never invented
      here.

    A mismatch in the declared category raises
    :class:`~.errors.TrainingConfigError`. A design whose
    ``n_seeds_selected`` is null is refused by :func:`..gate.assert_design_resolved`,
    not silently defaulted.

Loading or validating a configuration performs no training and authorises
nothing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from evaluation.conventional import ConventionalConfig
from readout.features import MotorFeatureSpec
from readout.linear import N_ACTIONS
from readout.trainer import ReinforceConfig

from ..campaign.protocol import PROTOCOL_ID, protocol_identity
from ..conditions import f_readout
from ..seeds import MASTER_SEED
from .errors import TrainingConfigError

#: REV4 Appendix C, row "training episodes/seed (F, Fβ)".
READOUT_EPISODES_PER_SEED = 20
#: REV4 Appendix C, row "training episodes (E)".
E_GRADIENT_UPDATES = 2000
#: REV4 §3.6 row 3: "seeded small initialization". The value is the existing
#: module default, recorded so a change cannot pass unnoticed.
READOUT_INIT_STD = 0.01
#: REV4 §3.5 row 1.
E_HIDDEN_UNITS = 64
E_HIDDEN_LAYERS = 2
#: Conditions with a training stage. F-init is derived from F and never trains.
READOUT_CONDITIONS = ("F", "F_beta")
AGENT_CONDITIONS = ("E", "E_full")
TRAINABLE_CONDITIONS = (*READOUT_CONDITIONS, *AGENT_CONDITIONS)

#: Constructor fields of :class:`evaluation.conventional.ConventionalConfig`.
AGENT_CONFIG_FIELDS = (
    "hidden_units",
    "hidden_layers",
    "learning_rate",
    "entropy_coefficient",
    "value_coefficient",
    "discount",
    "max_grad_norm",
)


def canonical_json(payload: Any) -> str:
    """Stable JSON used for every configuration and manifest hash."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check(checks: list[dict], name: str, actual: Any, expected: Any, source: str) -> None:
    ok = actual == expected
    checks.append(
        {
            "name": name,
            "actual": actual,
            "expected": expected,
            "source": source,
            "ok": bool(ok),
        }
    )
    if not ok:
        raise TrainingConfigError(
            f"{name} is {actual!r}; REV4/declaration requires {expected!r} ({source})"
        )


@dataclass(frozen=True)
class TrainingConfig:
    """The validated, fully recorded training declaration.

    ``sha256`` is written into every artifact manifest so an artifact can never
    be silently reused under a different training configuration.
    """

    master_seed: int
    protocol_id: str
    protocol_sha256: str
    protocol_path: str
    campaign_path: str
    campaign_sha256: str
    readout_episodes_per_seed: int
    e_gradient_updates: int
    readout_init_std: float
    reinforce_learning_rate: float
    reinforce_gamma: float
    motor_fields: tuple[str, ...]
    motor_n_features: int
    e_n_features: int
    e_full_n_features: int
    e_hidden_units: int
    e_hidden_layers: int
    e_learning_rate: float
    e_entropy_coefficient: float
    e_value_coefficient: float
    e_discount: float
    e_max_grad_norm: float
    n_seeds_primary: int
    n_seeds_fallback: int
    campaign_seeds: tuple[int, ...]
    training_seeds: tuple[int, ...]
    pilot_seeds: tuple[int, ...]
    checks: tuple[dict, ...]

    def as_dict(self) -> dict:
        return {
            "schema_version": 1,
            "master_seed": self.master_seed,
            "protocol": {
                "id": self.protocol_id,
                "sha256": self.protocol_sha256,
                "path": self.protocol_path,
            },
            "campaign_config": {
                "path": self.campaign_path,
                "sha256": self.campaign_sha256,
            },
            "declared": {
                "readout_episodes_per_seed": self.readout_episodes_per_seed,
                "e_gradient_updates": self.e_gradient_updates,
            },
            "implementation_constants": {
                "readout_init_std": self.readout_init_std,
                "reinforce": {
                    "learning_rate": self.reinforce_learning_rate,
                    "gamma": self.reinforce_gamma,
                },
                "e_learner": self.e_learner_dict(),
                "motor_feature_spec": {
                    "fields": list(self.motor_fields),
                    "n_features": self.motor_n_features,
                },
                "features": {
                    "e": self.e_n_features,
                    "e_full": self.e_full_n_features,
                },
            },
            "conditions": list(TRAINABLE_CONDITIONS),
            "seeds": {
                "declared": {
                    "n_seeds_primary": self.n_seeds_primary,
                    "n_seeds_fallback": self.n_seeds_fallback,
                },
                "campaign": list(self.campaign_seeds),
                "training": list(self.training_seeds),
                "pilot": list(self.pilot_seeds),
            },
            "checks": [dict(entry) for entry in self.checks],
        }

    def e_learner_dict(self) -> dict:
        return {
            "hidden_units": self.e_hidden_units,
            "hidden_layers": self.e_hidden_layers,
            "learning_rate": self.e_learning_rate,
            "entropy_coefficient": self.e_entropy_coefficient,
            "value_coefficient": self.e_value_coefficient,
            "discount": self.e_discount,
            "max_grad_norm": self.e_max_grad_norm,
            "algorithm": "reinforce_with_value_baseline",
            "optimizer": "adam",
            "action_selection": (
                "categorical sample while training; argmax otherwise"
            ),
        }

    def sha256(self) -> str:
        return sha256_text(canonical_json(self.as_dict()))


def validate_training_config(config: Any) -> TrainingConfig:
    """Validate a loaded :class:`..config.Phase8Config` against REV4.

    Every check is recorded, whether it passes or fails; the first failure
    raises. No value is substituted for a missing or differing one.
    """
    campaign = config.campaign
    conditions = config.conditions
    identity = protocol_identity()
    if not identity["present"]:
        raise TrainingConfigError(
            f"the frozen REV4 document is missing: {identity['path']}"
        )
    if not identity["matches_expected"]:
        raise TrainingConfigError(
            "the REV4 document does not match the certified hash "
            f"{identity['expected_sha256']} (observed {identity['sha256']})"
        )

    checks: list[dict] = []
    _check(checks, "campaign.master_seed", campaign.master_seed, MASTER_SEED,
           "REV4 Appendix C")
    _check(checks, "campaign.readout_episodes_per_seed",
           campaign.readout_episodes_per_seed, READOUT_EPISODES_PER_SEED,
           "REV4 Appendix C: training episodes/seed (F, Fβ)")
    _check(checks, "campaign.e_gradient_updates", campaign.e_gradient_updates,
           E_GRADIENT_UPDATES, "REV4 Appendix C: training episodes (E)")
    _check(checks, "f_readout.DEFAULT_INIT_STD", float(f_readout.DEFAULT_INIT_STD),
           READOUT_INIT_STD, "REV4 §3.6 row 3: seeded small initialization")

    spec = MotorFeatureSpec()
    _check(checks, "MotorFeatureSpec.fields", tuple(spec.fields),
           ("active_fraction",), "REV4 §3.6.1")
    _check(checks, "MotorFeatureSpec.n_features", spec.n_features, 3,
           "REV4 §3.6.1: three motor populations feed the four-way readout")

    _check(checks, "conditions.sensory.n_features",
           int(conditions.sensory.get("n_features", 0)), 7,
           "REV4 §3.5 row 1 / row 6")
    _check(checks, "conditions.sensory.n_features_full",
           int(conditions.sensory.get("n_features_full", 0)), 14,
           "REV4 §3.5 row 1 (E-full exploratory)")

    learner = ConventionalConfig()
    _check(checks, "ConventionalAgent.hidden_units", learner.hidden_units,
           E_HIDDEN_UNITS, "REV4 §3.5 row 1: 2×64 tanh hidden units")
    _check(checks, "ConventionalAgent.hidden_layers", learner.hidden_layers,
           E_HIDDEN_LAYERS, "REV4 §3.5 row 1: 2×64 tanh hidden units")
    _check(checks, "ConventionalAgent.algorithm", learner.as_dict()["algorithm"],
           "reinforce_with_value_baseline", "REV4 §3.5 row 5")
    _check(checks, "ConventionalAgent.optimizer", learner.as_dict()["optimizer"],
           "adam", "REV4 §3.5 row 5")
    _check(checks, "readout.N_ACTIONS", N_ACTIONS, 4,
           "REV4 §3.5 row 1 / §3.6 row 7")

    expected_trains = {
        "F": ("readout",),
        "F_beta": ("readout",),
        "E": ("policy",),
        "E_full": ("policy",),
        "F_init": ("none",),
    }
    for condition_id, expected in expected_trains.items():
        declared = tuple(conditions.spec(condition_id)["trains"])
        _check(checks, f"conditions.{condition_id}.trains", declared, expected,
               "REV4 §3.5 / §3.6 / §3.7")

    _check(checks, "len(seeds.training) >= n_seeds_primary",
           len(campaign.training_seeds) >= campaign.n_seeds_primary, True,
           "REV4 §6.3: training seeds are reserved and disjoint")

    reinforce = ReinforceConfig()
    return TrainingConfig(
        master_seed=int(campaign.master_seed),
        protocol_id=PROTOCOL_ID,
        protocol_sha256=str(identity["sha256"]),
        protocol_path=str(identity["path"]),
        campaign_path=str(campaign.path),
        campaign_sha256=str(campaign.sha256),
        readout_episodes_per_seed=int(campaign.readout_episodes_per_seed),
        e_gradient_updates=int(campaign.e_gradient_updates),
        readout_init_std=float(f_readout.DEFAULT_INIT_STD),
        reinforce_learning_rate=float(reinforce.learning_rate),
        reinforce_gamma=float(reinforce.gamma),
        motor_fields=tuple(spec.fields),
        motor_n_features=int(spec.n_features),
        e_n_features=int(conditions.sensory["n_features"]),
        e_full_n_features=int(conditions.sensory["n_features_full"]),
        e_hidden_units=int(learner.hidden_units),
        e_hidden_layers=int(learner.hidden_layers),
        e_learning_rate=float(learner.learning_rate),
        e_entropy_coefficient=float(learner.entropy_coefficient),
        e_value_coefficient=float(learner.value_coefficient),
        e_discount=float(learner.discount),
        e_max_grad_norm=float(learner.max_grad_norm),
        n_seeds_primary=int(campaign.n_seeds_primary),
        n_seeds_fallback=int(campaign.n_seeds_fallback),
        campaign_seeds=tuple(campaign.campaign_seeds),
        training_seeds=tuple(campaign.training_seeds),
        pilot_seeds=tuple(campaign.pilot_seeds),
        checks=tuple(checks),
    )


__all__ = [
    "AGENT_CONDITIONS",
    "AGENT_CONFIG_FIELDS",
    "E_GRADIENT_UPDATES",
    "E_HIDDEN_LAYERS",
    "E_HIDDEN_UNITS",
    "READOUT_CONDITIONS",
    "READOUT_EPISODES_PER_SEED",
    "READOUT_INIT_STD",
    "TRAINABLE_CONDITIONS",
    "TrainingConfig",
    "canonical_json",
    "sha256_text",
    "validate_training_config",
]
