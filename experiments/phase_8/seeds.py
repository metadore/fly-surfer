"""Deterministic seed derivation for the Phase 8 campaign.

REV3 §6.2 requires paired evaluation episodes: episode ``j`` of campaign seed
``s`` faces the same initial layout in every condition. REV3 §6.3 lists four
streams, and R18 requires one random graph per seed shared by C, D and C′.

Two consequences follow and are implemented here:

* the **environment** stream is derived without a condition id, otherwise the
  pairing of §6.2 would be broken;
* the **structure** stream is derived without a condition id, otherwise C, D
  and C′ would receive different random graphs.

Network and learning streams include the condition id, as §6.3 specifies.
Strings cannot enter a ``SeedSequence``, so stream and condition names map to
fixed integer codes. This is a naming convention, not a scientific parameter.
"""

from __future__ import annotations

import numpy as np

MASTER_SEED = 20261116

STREAM_CODES = {
    "environment": 1,
    "network": 2,
    "learning": 3,
    "structure": 4,
}
STREAMS = tuple(STREAM_CODES)

CONDITION_CODES = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "E_full": 6,
    "F": 7,
    "F_beta": 8,
    "F_init": 9,
    "A_prime": 10,
    "C_prime": 11,
}
CONDITION_IDS = tuple(CONDITION_CODES)

# The substrate-free floor is measured by replaying the paired environment
# seeds with a constant NO_ACTION policy (REV3 §3.6.2). It has no network, so
# it has no seed stream and no entry in ``CONDITION_CODES``, but its episodes
# are recorded like every other arm's.
FLOOR_ID = "floor"
ARM_IDS = (*CONDITION_IDS, FLOOR_ID)


def _non_negative_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    if int(value) < 0:
        raise ValueError(f"{name} cannot be negative")
    return int(value)


def _stream_code(stream: str) -> int:
    try:
        return STREAM_CODES[str(stream).strip().lower()]
    except KeyError:
        raise ValueError(f"stream must be one of {STREAMS}") from None


def condition_code(condition_id: str) -> int:
    try:
        return CONDITION_CODES[str(condition_id)]
    except KeyError:
        raise ValueError(f"condition must be one of {CONDITION_IDS}") from None


def _sequence(entropy: list[int]) -> np.random.SeedSequence:
    return np.random.SeedSequence([int(value) for value in entropy])


def _draw(sequence: np.random.SeedSequence) -> int:
    return int(sequence.generate_state(1, np.uint32)[0])


def environment_seed(master_seed: int, seed: int, episode: int) -> int:
    """Condition-independent environment seed for one paired episode."""
    master = _non_negative_int(master_seed, "master_seed")
    campaign_seed = _non_negative_int(seed, "seed")
    index = _non_negative_int(episode, "episode")
    return _draw(
        _sequence([master, campaign_seed, index, STREAM_CODES["environment"]])
    )


def condition_sequence(
    master_seed: int,
    condition_id: str,
    seed: int,
    stream: str,
) -> np.random.SeedSequence:
    """Network or learning stream for one condition and campaign seed."""
    master = _non_negative_int(master_seed, "master_seed")
    campaign_seed = _non_negative_int(seed, "seed")
    code = _stream_code(stream)
    if code not in (STREAM_CODES["network"], STREAM_CODES["learning"]):
        raise ValueError(
            "condition_sequence covers the network and learning streams; "
            "environment and structure are condition-independent"
        )
    return _sequence([master, condition_code(condition_id), campaign_seed, code])


def structure_sequence(master_seed: int, seed: int) -> np.random.SeedSequence:
    """One random-graph stream per campaign seed, shared by C, D and C′."""
    master = _non_negative_int(master_seed, "master_seed")
    campaign_seed = _non_negative_int(seed, "seed")
    return _sequence([master, campaign_seed, STREAM_CODES["structure"]])


def seed_plan(
    master_seed: int,
    condition_id: str,
    seed: int,
    *,
    episode: int = 0,
) -> dict[str, int]:
    """Every derived integer the manifest records for one (condition, seed).

    ``environment`` is the paired seed of ``episode``; the remaining episodes
    follow from :func:`environment_seed` unchanged across conditions.
    """
    plan = {
        "environment": environment_seed(master_seed, seed, episode),
        "structure": _draw(structure_sequence(master_seed, seed)),
    }
    for stream in ("network", "learning"):
        plan[stream] = _draw(
            condition_sequence(master_seed, condition_id, seed, stream)
        )
    return plan


def describe_derivation(master_seed: int = MASTER_SEED) -> dict:
    """Human- and manifest-readable statement of the derivation."""
    master = _non_negative_int(master_seed, "master_seed")
    return {
        "master_seed": master,
        "environment": "[master, campaign_seed, episode, 1] (condition-independent)",
        "network": "[master, condition_code, campaign_seed, 2]",
        "learning": "[master, condition_code, campaign_seed, 3]",
        "structure": "[master, campaign_seed, 4] (one graph per seed)",
        "stream_codes": dict(STREAM_CODES),
        "condition_codes": dict(CONDITION_CODES),
        "note": (
            "environment and structure omit the condition so that paired "
            "episodes and the C/D/C′ graph are shared"
        ),
    }


__all__ = [
    "ARM_IDS",
    "CONDITION_CODES",
    "CONDITION_IDS",
    "FLOOR_ID",
    "MASTER_SEED",
    "STREAM_CODES",
    "STREAMS",
    "condition_code",
    "condition_sequence",
    "describe_derivation",
    "environment_seed",
    "seed_plan",
    "structure_sequence",
]
