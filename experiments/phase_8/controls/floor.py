"""The substrate-free floor — constant NO_ACTION on the paired game seeds.

SCIENTIFIC STATUS
    The floor owns no network, reads no spikes, trains nothing and changes no
    weight. It replays the environment seed of a paired episode with a
    constant ``NO_ACTION`` policy (REV4 §3.6.2). It is recorded as rows
    because the analysis compares every arm against it, but it is **not** a
    neural-substrate experimental arm, and its row says so.
"""

from __future__ import annotations

from typing import Any

from ..conditions.base import ConditionError
from ..conditions.execute import NO_ACTION, floor_episode

CONDITION_ID = "floor"


def requirements() -> dict:
    return {
        "substrate": "none",
        "policy": "constant NO_ACTION",
        "trains": ("none",),
        "is_neural_arm": False,
        "neural_loop": False,
    }


def validate_adapter(adapter: Any) -> None:
    for name in ("reset", "step"):
        if not callable(getattr(adapter, name, None)):
            raise ConditionError(
                f"the floor needs the environment adapter's {name}()"
            )
    if getattr(adapter, "game", None) is None:
        raise ConditionError("the floor needs the controlled game adapter")


def assert_substrate_free(result: dict) -> dict:
    """Re-check the row evidence; a neural field here is a hard error."""
    evidence = dict(result["row"].get("evidence") or {})
    if evidence.get("neural_substrate") != "none":
        raise ConditionError(
            "the floor row claims a neural substrate; it must be substrate-free"
        )
    if evidence.get("is_neural_arm") is not False:
        raise ConditionError("the floor row must declare is_neural_arm = false")
    if result["row"]["condition"] != CONDITION_ID:
        raise ConditionError("the floor row has the wrong condition id")
    if result["row"]["role"] != "floor":
        raise ConditionError("the floor row has the wrong role")
    if result["row"]["weights_before"] is not None or (
        result["row"]["weights_after"] is not None
    ):
        raise ConditionError("the floor row must not carry weight fingerprints")
    actions = {record["action"] for record in result["records"]}
    if actions - {NO_ACTION}:
        raise ConditionError(
            f"the floor executed {sorted(actions)}; it must be constant NO_ACTION"
        )
    return evidence


def run(
    adapter: Any,
    *,
    seed: int,
    episode: int,
    environment_seed: int,
    config_hashes: Any,
    input_hashes: Any,
    max_game_updates: int,
) -> dict:
    validate_adapter(adapter)
    result = floor_episode(
        adapter,
        seed=seed,
        episode=episode,
        environment_seed=environment_seed,
        config_hashes=config_hashes,
        input_hashes=input_hashes,
        max_game_updates=max_game_updates,
    )
    result["floor_evidence"] = assert_substrate_free(result)
    return result


__all__ = [
    "CONDITION_ID",
    "assert_substrate_free",
    "requirements",
    "run",
    "validate_adapter",
]
