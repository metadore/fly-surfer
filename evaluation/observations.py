"""The 7/14 observation interface used by condition E.

SCIENTIFIC STATUS
    These are declared scalar encodings of ``GameState.features()``. They are
    not measured neural responses and not a claim about how a fly represents
    the game.

Condition E receives no pixels, no hidden game state and no future objects
(REV3 §3.5 row 6, §6.6). ``GameState.features()`` exposes 14 values; the seven
that ``BancSensoryMapping`` gives a population to are ``MATCHED_FEATURES`` and
the other seven are ``EXTRA_FEATURES``. E-matched consumes the first group and
E-full consumes both, in the declared order below.

Missing object values (``None``) encode to the same baseline the neural
encoders emit for an absent object, ``0.0``:

* lanes are encoded as ``lane_index - 1`` in ``{-1, 0, +1}`` for the three-lane
  game and as the raw ``0/1`` index for the two obstacle types;
* distances and speed are already normalised to ``[0, 1]`` by ``GameState``;
* presence/jump/roll are ``0.0/1.0``.

A present centre-lane object and an absent object therefore both carry ``0.0``
on the lane dimension; the presence feature is what distinguishes them. This
convention is fixed before any run and is not tuned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from sensory.game_state import GameState

MATCHED_FEATURES = (
    "train_present",
    "train_lane",
    "train_distance",
    "obstacle_present",
    "obstacle_lane",
    "obstacle_distance",
    "obstacle_type",
)
EXTRA_FEATURES = (
    "player_lane",
    "player_speed",
    "jumping",
    "rolling",
    "coin_present",
    "coin_lane",
    "coin_distance",
)
FULL_FEATURES = MATCHED_FEATURES + EXTRA_FEATURES

FEATURE_ENCODINGS = {
    "train_present": "boolean",
    "train_lane": "lane3",
    "train_distance": "unit",
    "obstacle_present": "boolean",
    "obstacle_lane": "lane3",
    "obstacle_distance": "unit",
    "obstacle_type": "lane2",
    "player_lane": "lane3",
    "player_speed": "unit",
    "jumping": "boolean",
    "rolling": "boolean",
    "coin_present": "boolean",
    "coin_lane": "lane3",
    "coin_distance": "unit",
}


def encode_feature(name: str, value: Any) -> float:
    """Encode one ``GameState.features()`` value under its declared kind."""
    try:
        kind = FEATURE_ENCODINGS[name]
    except KeyError:
        raise ValueError(f"unknown observation feature {name!r}") from None
    if value is None:
        return 0.0
    if kind == "boolean":
        return 1.0 if float(value) else 0.0
    if kind == "lane3":
        return float(int(value) - 1)
    if kind == "lane2":
        return float(int(value))
    return float(value)


def encode_features(features: Mapping, names: tuple[str, ...]) -> np.ndarray:
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"observation is missing features: {missing}")
    return np.asarray(
        [encode_feature(name, features[name]) for name in names],
        dtype=np.float32,
    )


@dataclass(frozen=True)
class ObservationSpec:
    """A named, ordered subset of the 14 game features."""

    name: str
    features: tuple[str, ...]

    def __post_init__(self) -> None:
        label = str(self.name).strip()
        if not label:
            raise ValueError("observation spec name cannot be empty")
        names = tuple(str(value) for value in self.features)
        if not names:
            raise ValueError("observation spec must contain at least one feature")
        if len(set(names)) != len(names):
            raise ValueError("observation spec has duplicate features")
        unknown = [name for name in names if name not in FULL_FEATURES]
        if unknown:
            raise ValueError(f"unknown observation features: {unknown}")
        object.__setattr__(self, "name", label)
        object.__setattr__(self, "features", names)

    @property
    def n_features(self) -> int:
        return len(self.features)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "n_features": self.n_features,
            "features": list(self.features),
            "encodings": {
                name: FEATURE_ENCODINGS[name] for name in self.features
            },
            "missing_value_policy": "encode as 0.0 (the neural encoder baseline)",
            "privileged_information": False,
        }


MATCHED_SPEC = ObservationSpec("E-matched", MATCHED_FEATURES)
FULL_SPEC = ObservationSpec("E-full", FULL_FEATURES)


class ObservationEncoder:
    """Turn a ``GameState`` into the declared float32 feature vector."""

    def __init__(self, spec: ObservationSpec = MATCHED_SPEC) -> None:
        if not isinstance(spec, ObservationSpec):
            raise ValueError("spec must be an ObservationSpec")
        self.spec = spec

    @property
    def n_features(self) -> int:
        return self.spec.n_features

    def encode(self, state: GameState) -> np.ndarray:
        if not isinstance(state, GameState):
            raise ValueError("state must be a GameState")
        return encode_features(state.features(), self.spec.features)

    def encode_mapping(self, features: Mapping) -> np.ndarray:
        return encode_features(features, self.spec.features)

    def describe(self) -> dict:
        return {"interface": "e_observation_v1", **self.spec.describe()}


__all__ = [
    "EXTRA_FEATURES",
    "FEATURE_ENCODINGS",
    "FULL_FEATURES",
    "FULL_SPEC",
    "MATCHED_FEATURES",
    "MATCHED_SPEC",
    "ObservationEncoder",
    "ObservationSpec",
    "encode_feature",
    "encode_features",
]
