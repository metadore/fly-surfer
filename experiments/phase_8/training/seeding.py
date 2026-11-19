"""Seed handling for training and artifact initialization.

Three values are deliberately kept apart and recorded separately:

* ``campaign_seed`` — the evaluation seed the artifact is later loaded under;
* ``training_seed`` — the declared index into ``seeds.training`` used for the
  training run; it must be disjoint from campaign and pilot seeds;
* ``init_seed`` — the derived learning-stream value that initializes the
  trainable parameters. It is derived from the *training* seed, not the
  evaluation seed, so an artifact can never share a stream with the episode
  that evaluates it.

REV4 declares that training and evaluation seeds are disjoint but does not
declare which training seed pairs with which campaign seed. That mapping is
therefore an explicit caller input (:func:`validate_pairing`); this module
never invents one. F and Fβ must share a training seed for the same campaign
seed (REV4 §3.6.2, "same seeds ... as F"), and that is the only pairing
constraint imposed here.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..seeds import seed_plan
from .config import TRAINABLE_CONDITIONS
from .errors import TrainingConfigError


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int,)):
        raise TrainingConfigError(f"{name} must be an integer, got {value!r}")
    if int(value) < 0:
        raise TrainingConfigError(f"{name} cannot be negative")
    return int(value)


def artifact_seeds(
    master_seed: int,
    condition_id: str,
    *,
    campaign_seed: int,
    training_seed: int,
) -> dict:
    """All seeds one artifact records, derived from the declared streams.

    Only the learning stream initializes trainable parameters; the network and
    environment values are recorded because the derivation produces them and
    so the record can be audited against :mod:`experiments.phase_8.seeds`.
    """
    if condition_id not in TRAINABLE_CONDITIONS:
        raise TrainingConfigError(
            f"{condition_id!r} has no training stage; trainable conditions are "
            f"{list(TRAINABLE_CONDITIONS)}"
        )
    master = _int(master_seed, "master_seed")
    campaign = _int(campaign_seed, "campaign_seed")
    training = _int(training_seed, "training_seed")
    if campaign == training:
        raise TrainingConfigError(
            "training and evaluation seeds must be disjoint (REV4 §3.5 row 9, "
            "§3.6 row 9)"
        )
    plan = seed_plan(master, condition_id, training)
    return {
        "master_seed": master,
        "campaign_seed": campaign,
        "training_seed": training,
        "init_seed": int(plan["learning"]),
        "network_seed": int(plan["network"]),
        "environment_seed": int(plan["environment"]),
        "init_source": "learning stream of the declared training seed",
    }


def validate_pairing(
    pairing: Mapping[tuple[str, int], int],
    *,
    conditions: Sequence[str] = TRAINABLE_CONDITIONS,
    campaign_seeds: Sequence[int],
    training_seeds: Sequence[int],
) -> dict:
    """Validate an explicit ``(condition, campaign_seed) -> training_seed`` map.

    No default pairing exists because REV4 does not declare one. A partial or
    extra map is an error, not something to fill in.
    """
    if not isinstance(pairing, Mapping):
        raise TrainingConfigError("pairing must be a mapping")
    conditions = tuple(str(condition) for condition in conditions)
    unknown = sorted(set(conditions) - set(TRAINABLE_CONDITIONS))
    if unknown:
        raise TrainingConfigError(f"pairing declares untrainable conditions: {unknown}")
    seeds = tuple(_int(seed, "campaign_seed") for seed in campaign_seeds)
    allowed_training = {_int(seed, "training_seed") for seed in training_seeds}
    declared = tuple(_int(seed, "campaign_seed") for seed in campaign_seeds)

    expected = {(condition, seed) for condition in conditions for seed in seeds}
    actual = set(pairing)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise TrainingConfigError(
            "the pairing does not cover every (condition, campaign seed): "
            f"missing {missing}"
        )
    if extra:
        raise TrainingConfigError(
            f"the pairing declares entries outside the design: {extra}"
        )

    normalised: dict[tuple[str, int], int] = {}
    for key, value in pairing.items():
        condition = str(key[0])
        seed = _int(key[1], "campaign_seed")
        training = _int(value, f"pairing[{condition},{seed}]")
        if training not in allowed_training:
            raise TrainingConfigError(
                f"pairing[{condition},{seed}] = {training} is not one of the "
                "declared training seeds"
            )
        normalised[(condition, seed)] = training

    per_condition: dict[str, list[int]] = {condition: [] for condition in conditions}
    for (condition, _seed), training in sorted(normalised.items()):
        per_condition[condition].append(training)
    for condition, values in per_condition.items():
        if len(set(values)) != len(values):
            raise TrainingConfigError(
                f"condition {condition} reuses a training seed across campaign "
                "seeds; each artifact needs its own training run"
            )

    if "F" in per_condition and "F_beta" in per_condition:
        for seed in seeds:
            if normalised[("F", seed)] != normalised[("F_beta", seed)]:
                raise TrainingConfigError(
                    "F and Fβ must share the same training seed at campaign "
                    f"seed {seed} (REV4 §3.6.2)"
                )

    return {
        "conditions": list(conditions),
        "campaign_seeds": list(declared),
        "entries": {
            f"{condition}:{seed}": normalised[(condition, seed)]
            for condition, seed in sorted(normalised)
        },
        "shared_readout_training_seed": "F and F_beta match by declaration",
        "source": "caller-declared; REV4 declares no campaign-to-training mapping",
    }


__all__ = [
    "artifact_seeds",
    "validate_pairing",
]
