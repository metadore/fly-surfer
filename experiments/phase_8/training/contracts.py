"""The D4 training contracts B3 and B4: seed pairing and environment streams.

SCIENTIFIC STATUS
    These functions *derive* numbers; they do not train, build a model, run an
    episode or write an artifact. Owner decision D4 (2026-11-21) declares the
    derivations, and the declarations are reproduced here so a derived value can
    always be recomputed and audited against its recorded provenance.

    Two namespaces keep training away from evaluation:

    * ``phase_8/training/B3/v1`` maps an evaluation seed onto one declared
      ``seeds.training`` value. The derivation is condition-independent, so F
      and Fβ at one evaluation seed share the training seed that REV4 §3.6.2
      requires, while each condition still writes its own artifact.
    * ``phase_8/training/B4/v1`` derives the training-episode environment seed
      from ``(master_seed, training_seed, episode)``. It is a different
      namespace from the evaluation stream in :mod:`experiments.phase_8.seeds`,
      and every value is checked against the Pilot 2-C evaluation episode
      seeds.

    A derived training seed is drawn from the declared training pool by index;
    it is never an arbitrary offset and never a value the caller supplies
    implicitly. No function here authorises a training run.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from ..seeds import environment_seed
from .config import TRAINABLE_CONDITIONS, canonical_json, sha256_text
from .errors import TrainingConfigError

B3_NAMESPACE = "phase_8/training/B3/v1"
B4_NAMESPACE = "phase_8/training/B4/v1"
CONTRACT_VERSION = "D4-v1"

#: The exact Pilot 2-C evaluation grid D4 names (D3 scope).
PILOT2C_EVALUATION_SEEDS = (9001, 9002, 9003)
PILOT2C_EPISODES_PER_SEED = 3
D4_READOUT_CONDITIONS = ("F", "F_beta")

#: Declared in D4 B3. Kept as data so a record and the code cannot drift apart.
B3_DERIVATION = {
    "namespace": B3_NAMESPACE,
    "hash": "sha256",
    "payload": "namespace|master_seed|evaluation_seed",
    "index_rule": (
        "first four digest bytes as a big-endian uint32, modulo the declared "
        "training-pool length"
    ),
    "collision_rule": (
        "linear forward probe over the pool in declaration order; the first "
        "unused index wins"
    ),
    "condition_scope": (
        "derived once per evaluation seed and independent of condition, so F "
        "and F_beta share the training seed"
    ),
}
B4_DERIVATION = {
    "namespace": B4_NAMESPACE,
    "hash": "sha256",
    "payload": "namespace|master_seed|training_seed|episode",
    "seed_width": "first four digest bytes as a big-endian uint32",
    "separation": (
        "never equal to a Pilot 2-C evaluation episode environment seed and "
        "never equal to a declared evaluation seed"
    ),
}


def _non_negative(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrainingConfigError(f"{name} must be an integer, got {value!r}")
    if int(value) < 0:
        raise TrainingConfigError(f"{name} cannot be negative")
    return int(value)


def _payload(namespace: str, parts: Sequence[int]) -> str:
    return namespace + "|" + "|".join(str(int(part)) for part in parts)


def namespace_digest(namespace: str, parts: Sequence[int]) -> str:
    """The full SHA-256 of one namespaced derivation payload."""
    return hashlib.sha256(_payload(namespace, parts).encode("ascii")).hexdigest()


def namespace_seed(namespace: str, parts: Sequence[int]) -> int:
    """The first four digest bytes as a big-endian uint32."""
    digest = bytes.fromhex(namespace_digest(namespace, parts))
    return int.from_bytes(digest[:4], "big")


def _seed_list(values: Sequence[int], name: str) -> tuple[int, ...]:
    seeds = tuple(_non_negative(value, name) for value in values)
    if not seeds:
        raise TrainingConfigError(f"{name} cannot be empty")
    if len(set(seeds)) != len(seeds):
        raise TrainingConfigError(f"{name} contains duplicates")
    return seeds


def derive_b3_pairing(
    evaluation_seeds: Sequence[int],
    training_seeds: Sequence[int],
    *,
    master_seed: int,
) -> dict:
    """Derive the D4 B3 pairing from the declared pools, with provenance.

    Evaluation seeds are processed in ascending order so the result is stable
    regardless of how the caller lists them. Each evaluation seed maps to a
    distinct declared training seed; the mapping does not depend on the
    condition, so F and Fβ share it.
    """
    master = _non_negative(master_seed, "master_seed")
    evaluations = _seed_list(evaluation_seeds, "evaluation_seeds")
    pool = _seed_list(training_seeds, "training_seeds")
    if len(pool) < len(evaluations):
        raise TrainingConfigError(
            f"the declared training pool has {len(pool)} seeds for "
            f"{len(evaluations)} evaluation seeds; B3 needs at least one "
            "distinct training seed per evaluation seed"
        )
    overlap = sorted(set(evaluations) & set(pool))
    if overlap:
        raise TrainingConfigError(
            f"evaluation seeds {overlap} are also declared training seeds; an "
            "evaluation seed may never be reused as a training seed (REV4 "
            "§3.5 row 9, §3.6 row 9)"
        )

    used: set[int] = set()
    entries: dict[str, dict] = {}
    for evaluation in sorted(evaluations):
        digest = namespace_digest(B3_NAMESPACE, [master, evaluation])
        offset = int(digest[:8], 16) % len(pool)
        index = None
        for step in range(len(pool)):
            candidate = (offset + step) % len(pool)
            if pool[candidate] not in used:
                index = candidate
                break
        if index is None:  # pragma: no cover - guarded by the length check
            raise TrainingConfigError(
                "the declared training pool cannot accommodate every "
                "evaluation seed"
            )
        training = pool[index]
        used.add(training)
        entries[str(evaluation)] = {
            "evaluation_seed": int(evaluation),
            "training_seed": int(training),
            "namespace": B3_NAMESPACE,
            "payload": _payload(B3_NAMESPACE, [master, evaluation]),
            "sha256": digest,
            "pool_index": int(index),
            "pool_size": int(len(pool)),
            "probe_steps": int(step),
        }

    result = {
        "contract": "B3",
        "version": CONTRACT_VERSION,
        "derivation": dict(B3_DERIVATION),
        "master_seed": master,
        "training_pool": list(pool),
        "entries": entries,
        "conditions": list(D4_READOUT_CONDITIONS),
        "pairing": {
            f"{condition}:{entry['evaluation_seed']}": int(entry["training_seed"])
            for condition in D4_READOUT_CONDITIONS
            for entry in entries.values()
        },
        "training_execution_authorized": False,
    }
    result["sha256"] = sha256_text(canonical_json(result))
    return result


def pairing_map(pairing: Mapping[str, Any], *, conditions: Sequence[str] = D4_READOUT_CONDITIONS) -> dict:
    """``(condition, evaluation_seed) -> training_seed`` for the loader."""
    declared = tuple(str(condition) for condition in conditions)
    unknown = sorted(set(declared) - set(TRAINABLE_CONDITIONS))
    if unknown:
        raise TrainingConfigError(f"unknown pairing conditions: {unknown}")
    entries = pairing.get("entries")
    if not isinstance(entries, Mapping) or not entries:
        raise TrainingConfigError("the pairing record has no entries")
    mapping: dict[tuple[str, int], int] = {}
    for key, entry in entries.items():
        evaluation = _non_negative(entry.get("evaluation_seed"), "evaluation_seed")
        training = _non_negative(entry.get("training_seed"), "training_seed")
        for condition in declared:
            mapping[(condition, evaluation)] = training
    return mapping


def validate_b3_pairing(
    pairing: Mapping[str, Any],
    *,
    evaluation_seeds: Sequence[int],
    training_seeds: Sequence[int],
    master_seed: int,
) -> dict:
    """Re-derive B3 and require the supplied record to match exactly."""
    expected = derive_b3_pairing(
        evaluation_seeds, training_seeds, master_seed=master_seed
    )
    if not isinstance(pairing, Mapping):
        raise TrainingConfigError("the B3 pairing must be a mapping")
    differences: list[str] = []
    if int(pairing.get("master_seed", -1)) != int(expected["master_seed"]):
        differences.append("master_seed")
    if list(pairing.get("training_pool") or []) != list(expected["training_pool"]):
        differences.append("training_pool")
    supplied = pairing.get("entries") or {}
    if set(supplied) != set(expected["entries"]):
        differences.append("entry set")
    else:
        for key, entry in expected["entries"].items():
            observed = supplied[key]
            for field in ("evaluation_seed", "training_seed", "sha256", "pool_index"):
                if observed.get(field) != entry[field]:
                    differences.append(f"{key}.{field}")
    if supplied and isinstance(supplied, Mapping):
        for condition in D4_READOUT_CONDITIONS:
            for key, entry in expected["entries"].items():
                expected_training = expected["pairing"][
                    f"{condition}:{entry['evaluation_seed']}"
                ]
                if int(entry["training_seed"]) != int(expected_training):
                    differences.append(f"{condition}:{key}")

    if differences:
        raise TrainingConfigError(
            "the supplied B3 pairing does not match the declared derivation: "
            f"{sorted(set(differences))}"
        )
    return expected


def training_environment_seed(master_seed: int, training_seed: int, episode: int) -> int:
    """The D4 B4 environment seed for one training episode."""
    master = _non_negative(master_seed, "master_seed")
    training = _non_negative(training_seed, "training_seed")
    index = _non_negative(episode, "episode")
    return namespace_seed(B4_NAMESPACE, [master, training, index])


def training_environment_schedule(
    master_seed: int, training_seed: int, episodes: int
) -> tuple[int, ...]:
    """One deterministic environment seed per training episode."""
    count = _non_negative(episodes, "episodes")
    if count < 1:
        raise TrainingConfigError("episodes must be positive")
    schedule = tuple(
        training_environment_seed(master_seed, training_seed, episode)
        for episode in range(count)
    )
    if len(set(schedule)) != len(schedule):
        raise TrainingConfigError(
            "the B4 stream repeated an environment seed; the derivation is not "
            "usable for this budget"
        )
    return schedule


def pilot2c_evaluation_environment_seeds(
    master_seed: int,
    *,
    evaluation_seeds: Sequence[int] = PILOT2C_EVALUATION_SEEDS,
    episodes: int = PILOT2C_EPISODES_PER_SEED,
) -> tuple[int, ...]:
    """The evaluation environment seeds Pilot 2-C uses, unchanged.

    This calls the frozen evaluation derivation in
    :mod:`experiments.phase_8.seeds`; it does not modify it.
    """
    seeds = tuple(_non_negative(seed, "evaluation_seed") for seed in evaluation_seeds)
    count = _non_negative(episodes, "episodes")
    if count < 1:
        raise TrainingConfigError("episodes must be positive")
    return tuple(
        environment_seed(master_seed, seed, episode)
        for seed in seeds
        for episode in range(count)
    )


def assert_environment_stream_disjoint(
    schedule: Sequence[int],
    *,
    master_seed: int,
    evaluation_seeds: Sequence[int] = PILOT2C_EVALUATION_SEEDS,
    evaluation_episodes: int = PILOT2C_EPISODES_PER_SEED,
) -> dict:
    """Refuse a B4 schedule that reuses a Pilot 2-C evaluation environment seed."""
    values = tuple(_non_negative(value, "training_environment_seed") for value in schedule)
    if len(set(values)) != len(values):
        raise TrainingConfigError("the B4 schedule contains duplicate environment seeds")
    evaluations = tuple(
        _non_negative(seed, "evaluation_seed") for seed in evaluation_seeds
    )
    pilot_seeds = set(
        pilot2c_evaluation_environment_seeds(
            master_seed,
            evaluation_seeds=evaluations,
            episodes=int(evaluation_episodes),
        )
    )
    reused = sorted(set(values) & pilot_seeds)
    if reused:
        raise TrainingConfigError(
            f"the training environment stream reuses Pilot 2-C evaluation "
            f"episode seeds {reused}; B4 requires a separate stream"
        )
    as_evaluation_seed = sorted(set(values) & set(evaluations))
    if as_evaluation_seed:
        raise TrainingConfigError(
            f"training environment seeds {as_evaluation_seed} equal declared "
            "evaluation seeds; B4 forbids that reuse"
        )
    return {
        "contract": "B4",
        "version": CONTRACT_VERSION,
        "n_training_seeds": len(values),
        "n_pilot2c_evaluation_seeds": len(pilot_seeds),
        "disjoint": True,
        "evaluation_seeds": list(evaluations),
        "master_seed": int(master_seed),
    }


def describe_training_contracts() -> dict:
    """The D4 declarations as data, with no execution authority attached."""
    return {
        "version": CONTRACT_VERSION,
        "owner_decision": "D4 (2026-11-21)",
        "B3": {
            "title": "campaign-to-training seed pairing",
            "derivation": dict(B3_DERIVATION),
            "conditions": list(D4_READOUT_CONDITIONS),
            "shared_training_seed_per_evaluation_seed": True,
            "separate_artifacts_per_condition": True,
        },
        "B4": {
            "title": "training environment seeds",
            "derivation": dict(B4_DERIVATION),
        },
        "B5": {
            "title": "checkpoint policy",
            "cadence": "after every completed training episode",
            "retention": "all intermediate checkpoints plus the final checkpoint",
            "format": "exact-checkpoint schema 2",
            "not_a_training_artifact": True,
        },
        "B6": {
            "title": "exact resumption",
            "components": [
                "model parameters",
                "optimizer state and moments",
                "python_rng",
                "numpy_rng",
                "torch_rng",
                "sampler",
                "environment_rng (caller-supplied or explicitly absent)",
            ],
            "verification": (
                "compare an uninterrupted run with an interrupted-and-resumed "
                "run; equality is required before exactness is claimed"
            ),
        },
        "training_execution_authorized": False,
        "note": (
            "D4 declares these contracts only. It authorises no training run, "
            "no trained artifact and no Pilot 2-C episode."
        ),
    }


__all__ = [
    "B3_DERIVATION",
    "B3_NAMESPACE",
    "B4_DERIVATION",
    "B4_NAMESPACE",
    "CONTRACT_VERSION",
    "D4_READOUT_CONDITIONS",
    "PILOT2C_EPISODES_PER_SEED",
    "PILOT2C_EVALUATION_SEEDS",
    "assert_environment_stream_disjoint",
    "derive_b3_pairing",
    "describe_training_contracts",
    "namespace_digest",
    "namespace_seed",
    "pairing_map",
    "pilot2c_evaluation_environment_seeds",
    "training_environment_schedule",
    "training_environment_seed",
    "validate_b3_pairing",
]
