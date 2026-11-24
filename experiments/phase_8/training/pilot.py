"""The pilot-scoped training plan D5 authorises.

SCIENTIFIC STATUS
    D5 authorises exactly six F/Fβ training runs at evaluation seeds 9001,
    9002 and 9003, twenty episodes each, on the frozen biological substrate.
    This module turns that authorisation into an explicit plan: which
    condition, which evaluation seed, which B3 training seed, which B4
    environment stream, which initialization and network seeds, and which
    sampling seed.

    The plan is deliberately narrow. It refuses a different condition, a
    different seed, a different episode budget or a subscriber graph, and it
    never expands into the campaign seed grid. It is not gated by
    ``design.n_seeds_selected``: Pilot 2-C certifies a floor and an identity and
    selects no campaign N. Building a plan trains nothing, runs no episode and
    writes no artifact.

    The B3 pairing is re-derived here and compared with the pairing D5 records;
    the B4 schedule is derived per artifact and checked against the Pilot 2-C
    evaluation environment stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import TrainingConfig, validate_training_config
from .contracts import (
    assert_environment_stream_disjoint,
    derive_b3_pairing,
    training_environment_schedule,
)
from .d5 import (
    PILOT_TRAINING_ARTIFACTS,
    PILOT_TRAINING_ARTIFACT_COUNT,
    PILOT_TRAINING_CONDITIONS,
    PILOT_TRAINING_EPISODE_COUNT,
    PILOT_TRAINING_EPISODES,
    PILOT_TRAINING_EVALUATION_SEEDS,
    assert_d5_training_authorized,
    d5_applicability,
)
from .errors import TrainingConfigError, TrainingNotAuthorized
from .seeding import artifact_seeds

#: The only substrate D5 authorises. A plan never carries another one.
PILOT_SUBSTRATE = "biological_graph"
#: Implementation constant, matching the declared engine's default. It seeds
#: the action sampler only; it is not a B3/B4 value.
DEFAULT_SAMPLING_SEED = 0


@dataclass(frozen=True, eq=False)
class PilotArtifactPlan:
    """One authorised training artifact and every seed it will use."""

    condition_id: str
    evaluation_seed: int
    training_seed: int
    pool_index: int
    episodes: int
    init_seed: int
    network_seed: int
    initialization_environment_seed: int
    environment_seeds: tuple[int, ...]
    sampling_seed: int
    b3: dict
    substrate: str = PILOT_SUBSTRATE

    @property
    def key(self) -> str:
        return f"{self.condition_id}:{self.evaluation_seed}"

    def describe(self) -> dict:
        return {
            "key": self.key,
            "condition_id": self.condition_id,
            "evaluation_seed": self.evaluation_seed,
            "campaign_seed": self.evaluation_seed,
            "training_seed": self.training_seed,
            "pool_index": self.pool_index,
            "episodes": self.episodes,
            "init_seed": self.init_seed,
            "network_seed": self.network_seed,
            "initialization_environment_seed": self.initialization_environment_seed,
            "environment_seeds": list(self.environment_seeds),
            "sampling_seed": self.sampling_seed,
            "substrate": self.substrate,
            "b3": dict(self.b3),
            "trains_nothing_here": True,
        }


@dataclass(frozen=True, eq=False)
class PilotTrainingPlan:
    """The six authorised artifacts and the records they are bound to."""

    master_seed: int
    config_sha256: str
    d5_sha256: str
    d6_sha256: str
    b3: dict
    entries: tuple[PilotArtifactPlan, ...]
    substrate: str
    authorisation: dict

    def get(self, condition_id: str, evaluation_seed: int) -> PilotArtifactPlan:
        condition = str(condition_id)
        seed = int(evaluation_seed)
        for entry in self.entries:
            if entry.condition_id == condition and entry.evaluation_seed == seed:
                return entry
        raise TrainingNotAuthorized(
            f"{condition}:{seed} is not one of the six artifacts D5 authorises"
        )

    def describe(self) -> dict:
        return {
            "master_seed": self.master_seed,
            "config_sha256": self.config_sha256,
            "d5_sha256": self.d5_sha256,
            "d6_sha256": self.d6_sha256,
            "substrate": self.substrate,
            "n_artifacts": len(self.entries),
            "n_episodes": sum(entry.episodes for entry in self.entries),
            "b3_sha256": self.b3.get("sha256"),
            "entries": [entry.describe() for entry in self.entries],
            "training_execution_authorized": True,
            "authorisation": dict(self.authorisation),
            "trains_nothing_here": True,
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TrainingNotAuthorized(message)


def _record_sha256(path: Any, label: str) -> str:
    """The hash of the owner-decision record the report points at."""
    if not isinstance(path, str) or not path.strip():
        raise TrainingConfigError(f"{label} record path is missing from the report")
    candidate = Path(path)
    if not candidate.is_file():
        raise TrainingConfigError(f"the {label} record is not on disk: {path}")
    from brain.banc_graph import sha256_file

    digest = sha256_file(candidate)
    if len(str(digest)) != 64:
        raise TrainingConfigError(f"the {label} record hash is not a 64-hex digest")
    return str(digest)


def build_pilot_plan(
    phase8_config: Any,
    *,
    config: TrainingConfig | None = None,
    report: dict | None = None,
) -> PilotTrainingPlan:
    """Build the exact six-artifact D5 plan; refuse anything else."""
    if report is None:
        report = d5_applicability()
    _require(
        bool(report.get("applicable")), str(report.get("reason", "D5 is not applicable"))
    )
    if config is None:
        config = validate_training_config(phase8_config)
    master = int(config.master_seed)

    derived = derive_b3_pairing(
        PILOT_TRAINING_EVALUATION_SEEDS,
        config.training_seeds,
        master_seed=master,
    )
    recorded_pairing = {
        f"{entry['condition_id']}:{entry['evaluation_seed']}": int(
            entry["training_seed"]
        )
        for entry in report["authorised_artifacts"]
    }
    _require(
        derived["pairing"] == recorded_pairing,
        "the re-derived B3 pairing does not match the pairing D5 records",
    )
    recorded_sha = (report.get("b3") or {}).get("derived_sha256")
    _require(
        recorded_sha == derived["sha256"],
        "the re-derived B3 digest does not match the digest D5 records",
    )

    entries: list[PilotArtifactPlan] = []
    for item in PILOT_TRAINING_ARTIFACTS:
        condition = str(item["condition_id"])
        evaluation = int(item["evaluation_seed"])
        training = int(item["training_seed"])
        episodes = int(item["episodes"])
        _require(
            condition in PILOT_TRAINING_CONDITIONS,
            f"D5 authorises F and F_beta only; {condition!r} is outside its scope",
        )
        _require(
            evaluation in PILOT_TRAINING_EVALUATION_SEEDS,
            f"D5 authorises evaluation seeds "
            f"{list(PILOT_TRAINING_EVALUATION_SEEDS)}; {evaluation} is outside "
            "its scope",
        )
        _require(
            episodes == PILOT_TRAINING_EPISODES,
            f"D5 authorises exactly {PILOT_TRAINING_EPISODES} episodes per "
            f"artifact; {episodes} is outside its scope",
        )
        entry = derived["entries"][str(evaluation)]
        _require(
            int(entry["training_seed"]) == training,
            f"the B3 derivation pairs {evaluation} with "
            f"{entry['training_seed']}, not the recorded {training}",
        )
        seeds = artifact_seeds(
            master,
            condition,
            campaign_seed=evaluation,
            training_seed=training,
        )
        schedule = training_environment_schedule(master, training, episodes)
        assert_environment_stream_disjoint(schedule, master_seed=master)
        entries.append(
            PilotArtifactPlan(
                condition_id=condition,
                evaluation_seed=evaluation,
                training_seed=training,
                pool_index=int(item["pool_index"]),
                episodes=episodes,
                init_seed=int(seeds["init_seed"]),
                network_seed=int(seeds["network_seed"]),
                initialization_environment_seed=int(seeds["environment_seed"]),
                environment_seeds=schedule,
                sampling_seed=DEFAULT_SAMPLING_SEED,
                b3=dict(entry),
            )
        )

    if len(entries) != PILOT_TRAINING_ARTIFACT_COUNT:
        raise TrainingConfigError(
            f"the plan must carry exactly {PILOT_TRAINING_ARTIFACT_COUNT} "
            f"artifacts, built {len(entries)}"
        )
    if sum(entry.episodes for entry in entries) != PILOT_TRAINING_EPISODE_COUNT:
        raise TrainingConfigError(
            "the plan's episode total does not match the authorised 120"
        )

    return PilotTrainingPlan(
        master_seed=master,
        config_sha256=config.sha256(),
        d5_sha256=_record_sha256(report.get("path"), "D5"),
        d6_sha256=_record_sha256((report.get("d6") or {}).get("path"), "D6"),
        b3=derived,
        entries=tuple(entries),
        substrate=PILOT_SUBSTRATE,
        authorisation={
            "owner_decision": "D5",
            "applicable": True,
            "approval_date": report.get("approval_date"),
            "d5_path": report.get("path"),
            "d6_path": (report.get("d6") or {}).get("path"),
            "d6": dict(report.get("d6") or {}),
            "does_not_authorise": list(report.get("does_not_authorise") or []),
            "substrate": PILOT_SUBSTRATE,
            "uses_randomized_graph": False,
        },
    )


def validate_pilot_scope(
    condition_id: str,
    evaluation_seed: int,
    *,
    episodes: int | None = None,
    plan: PilotTrainingPlan | None = None,
    report: dict | None = None,
) -> dict:
    """Refuse a condition, seed or budget outside the exact D5 plan.

    Returns the planned entry when a plan is supplied, else the D5 record's
    authorised-artifact entry. Any other request raises
    :class:`~.errors.TrainingNotAuthorized`.
    """
    entry = assert_d5_training_authorized(
        condition_id, evaluation_seed, episodes=episodes, report=report
    )
    if episodes is not None and int(episodes) != PILOT_TRAINING_EPISODES:
        raise TrainingNotAuthorized(
            f"D5 authorises exactly {PILOT_TRAINING_EPISODES} episodes for "
            f"{condition_id}:{evaluation_seed}; {episodes} is outside its scope"
        )
    if plan is not None:
        planned = plan.get(condition_id, evaluation_seed)
        if episodes is not None and planned.episodes != int(episodes):
            raise TrainingNotAuthorized(
                f"the plan declares {planned.episodes} episodes for "
                f"{planned.key}; {episodes} is outside its scope"
            )
        return planned.describe()
    return entry


def describe_pilot_plan(plan: PilotTrainingPlan) -> dict:
    return plan.describe()


__all__ = [
    "DEFAULT_SAMPLING_SEED",
    "PILOT_SUBSTRATE",
    "PilotArtifactPlan",
    "PilotTrainingPlan",
    "build_pilot_plan",
    "describe_pilot_plan",
    "validate_pilot_scope",
]
