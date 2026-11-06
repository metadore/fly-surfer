"""Phase 3B.2A visual-perception configuration models.

The configuration is deliberately explicit about what the detector schema
contains. v15 has no player or coin class, so those modalities are declared
empty rather than inferred. Class roles are hypotheses copied from the Phase
3B.1 curation policy, not verified game mechanics.

Nothing in this module imports the connectome simulator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


class ConfigurationError(ValueError):
    """Raised when a perception configuration is missing or inconsistent."""


class ClassRole(str, Enum):
    """What a detected class represents in the visual scene."""

    TRAIN = "train"
    OBSTACLE = "obstacle"
    COIN = "coin"
    PLAYER = "player"
    TERRAIN = "terrain"
    BOUNDARY = "boundary"
    POWERUP = "powerup"
    OTHER = "other"


class GameStateRole(str, Enum):
    """How a class can be represented by the existing Phase 3A schema."""

    TRAIN = "train"
    OBSTACLE_LOW = "obstacle_low"
    OBSTACLE_HIGH = "obstacle_high"
    UNSUPPORTED = "unsupported"


def _fraction(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ConfigurationError(f"{name} must be finite and in [0, 1]")
    return number


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigurationError(f"{name} must be a positive integer")
    return int(value)


def _class_id(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{name} must be a non-negative integer")
    return int(value)


@dataclass(frozen=True)
class PreprocessConfig:
    """Optional crop and resize applied before detection.

    Crop fractions are relative to the original screenshot. Lane geometry is
    expressed relative to the resulting viewport, so a cropped HUD or toolbar
    does not shift lane boundaries.
    """

    crop_left_fraction: float = 0.0
    crop_right_fraction: float = 0.0
    crop_top_fraction: float = 0.0
    crop_bottom_fraction: float = 0.0
    resize: tuple[int, int] | None = None
    mode: str = "RGB"

    def __post_init__(self) -> None:
        fractions = {
            "crop_left_fraction": self.crop_left_fraction,
            "crop_right_fraction": self.crop_right_fraction,
            "crop_top_fraction": self.crop_top_fraction,
            "crop_bottom_fraction": self.crop_bottom_fraction,
        }
        values = {
            name: _fraction(value, name) for name, value in fractions.items()
        }
        if sum(values.values()) >= 1.0:
            raise ConfigurationError(
                "crop fractions must leave at least one pixel in both dimensions"
            )
        if self.resize is not None:
            if not isinstance(self.resize, (tuple, list)) or len(self.resize) != 2:
                raise ConfigurationError("resize must be a (width, height) pair")
            object.__setattr__(
                self,
                "resize",
                (
                    _positive_int(self.resize[0], "resize width"),
                    _positive_int(self.resize[1], "resize height"),
                ),
            )
        if not isinstance(self.mode, str) or not self.mode:
            raise ConfigurationError("mode must be a non-empty Pillow mode string")

    def as_dict(self) -> dict:
        return {
            "crop_left_fraction": self.crop_left_fraction,
            "crop_right_fraction": self.crop_right_fraction,
            "crop_top_fraction": self.crop_top_fraction,
            "crop_bottom_fraction": self.crop_bottom_fraction,
            "resize": list(self.resize) if self.resize else None,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class ValidationConfig:
    """Rules applied to untrusted detector output."""

    confidence_threshold: float = 0.25
    min_box_pixels: float = 2.0
    min_area_fraction: float = 0.0
    bounds_tolerance_pixels: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "confidence_threshold",
            _fraction(self.confidence_threshold, "confidence_threshold"),
        )
        object.__setattr__(
            self,
            "min_area_fraction",
            _fraction(self.min_area_fraction, "min_area_fraction"),
        )
        for name in ("min_box_pixels", "bounds_tolerance_pixels"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigurationError(f"{name} must be a number")
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ConfigurationError(f"{name} must be finite and non-negative")
            object.__setattr__(self, name, number)
        if self.min_box_pixels <= 0:
            raise ConfigurationError("min_box_pixels must be positive")


@dataclass(frozen=True)
class LaneConfig:
    """Three-lane geometry in normalised viewport coordinates."""

    n_lanes: int = 3
    boundaries: tuple[float, ...] = (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)
    min_overlap_fraction: float = 0.15
    majority_fraction: float = 0.75

    def __post_init__(self) -> None:
        if self.n_lanes != 3:
            raise ConfigurationError(
                "the existing GameState supports exactly three lanes"
            )
        if not isinstance(self.boundaries, (tuple, list)):
            raise ConfigurationError("lane boundaries must be a sequence")
        boundaries = tuple(
            _fraction(value, f"lane boundary {index}")
            for index, value in enumerate(self.boundaries)
        )
        if len(boundaries) != self.n_lanes + 1:
            raise ConfigurationError(
                "lane boundaries must contain n_lanes + 1 values"
            )
        if boundaries[0] != 0.0 or boundaries[-1] != 1.0:
            raise ConfigurationError("lane boundaries must start at 0 and end at 1")
        if any(
            right <= left
            for left, right in zip(boundaries, boundaries[1:])
        ):
            raise ConfigurationError("lane boundaries must increase strictly")
        minimum = _fraction(self.min_overlap_fraction, "min_overlap_fraction")
        majority = _fraction(self.majority_fraction, "majority_fraction")
        if minimum == 0.0 or majority == 0.0:
            raise ConfigurationError("overlap fractions must be greater than zero")
        object.__setattr__(self, "boundaries", boundaries)

    def as_dict(self) -> dict:
        return {
            "n_lanes": self.n_lanes,
            "boundaries": list(self.boundaries),
            "min_overlap_fraction": self.min_overlap_fraction,
            "majority_fraction": self.majority_fraction,
        }


@dataclass(frozen=True)
class DistanceConfig:
    """How to derive the GameState distance field.

    ``bottom_edge_proxy`` is geometric and uncalibrated: 0 means the box
    bottom is at the viewport bottom (near), 1 means it is at the horizon
    fraction (far). It is not a metric distance.
    """

    mode: str = "bottom_edge_proxy"
    horizon_fraction: float = 0.15

    def __post_init__(self) -> None:
        if self.mode not in ("bottom_edge_proxy", "none"):
            raise ConfigurationError(
                "distance mode must be 'bottom_edge_proxy' or 'none'"
            )
        horizon = _fraction(self.horizon_fraction, "horizon_fraction")
        if horizon >= 1.0:
            raise ConfigurationError("horizon_fraction must be below 1")

    @property
    def is_proxy(self) -> bool:
        return self.mode == "bottom_edge_proxy"


@dataclass(frozen=True)
class ClassDefinition:
    class_id: int
    name: str
    role: ClassRole
    game_state_role: GameStateRole

    def __post_init__(self) -> None:
        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise ConfigurationError("class id must be an integer")
        if self.class_id < 0:
            raise ConfigurationError("class id must be non-negative")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigurationError("class name must be a non-empty string")
        if not isinstance(self.role, ClassRole):
            raise ConfigurationError(f"class {self.name!r} has an invalid role")
        if not isinstance(self.game_state_role, GameStateRole):
            raise ConfigurationError(
                f"class {self.name!r} has an invalid GameState role"
            )

    def as_dict(self) -> dict:
        return {
            "id": self.class_id,
            "name": self.name,
            "role": self.role.value,
            "game_state_role": self.game_state_role.value,
        }


@dataclass(frozen=True)
class ClassSchema:
    """Detector class IDs and the modalities the schema can represent."""

    classes: tuple[ClassDefinition, ...]
    player_class_ids: tuple[int, ...] = ()
    coin_class_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.classes:
            raise ConfigurationError("at least one class definition is required")
        ids = [definition.class_id for definition in self.classes]
        names = [definition.name for definition in self.classes]
        if len(set(ids)) != len(ids):
            raise ConfigurationError("class ids must be unique")
        if len(set(names)) != len(names):
            raise ConfigurationError("class names must be unique")
        object.__setattr__(
            self,
            "player_class_ids",
            tuple(_class_id(value, "player class id") for value in self.player_class_ids),
        )
        object.__setattr__(
            self,
            "coin_class_ids",
            tuple(_class_id(value, "coin class id") for value in self.coin_class_ids),
        )
        by_id = self.by_id
        for class_id in self.player_class_ids:
            if class_id not in by_id:
                raise ConfigurationError(f"unknown player class id {class_id}")
            if by_id[class_id].role is not ClassRole.PLAYER:
                raise ConfigurationError(
                    f"player class id {class_id} does not have role 'player'"
                )
        for class_id in self.coin_class_ids:
            if class_id not in by_id:
                raise ConfigurationError(f"unknown coin class id {class_id}")
            if by_id[class_id].role is not ClassRole.COIN:
                raise ConfigurationError(
                    f"coin class id {class_id} does not have role 'coin'"
                )

    @property
    def by_id(self) -> dict[int, ClassDefinition]:
        return {definition.class_id: definition for definition in self.classes}

    @property
    def by_name(self) -> dict[str, ClassDefinition]:
        return {definition.name: definition for definition in self.classes}

    @property
    def supports_player(self) -> bool:
        return bool(self.player_class_ids)

    @property
    def supports_coins(self) -> bool:
        return bool(self.coin_class_ids)

    def as_dict(self) -> dict:
        return {
            "classes": [definition.as_dict() for definition in self.classes],
            "player_class_ids": list(self.player_class_ids),
            "coin_class_ids": list(self.coin_class_ids),
        }


@dataclass(frozen=True)
class PerceptionConfig:
    preprocess: PreprocessConfig
    validation: ValidationConfig
    lanes: LaneConfig
    distance: DistanceConfig
    schema: ClassSchema
    source_path: Path | None = None

    def __post_init__(self) -> None:
        for name, value, expected in (
            ("preprocess", self.preprocess, PreprocessConfig),
            ("validation", self.validation, ValidationConfig),
            ("lanes", self.lanes, LaneConfig),
            ("distance", self.distance, DistanceConfig),
            ("schema", self.schema, ClassSchema),
        ):
            if not isinstance(value, expected):
                raise ConfigurationError(f"{name} must be a {expected.__name__}")

    def as_dict(self) -> dict:
        return {
            "source_path": str(self.source_path) if self.source_path else None,
            "preprocess": self.preprocess.as_dict(),
            "validation": {
                "confidence_threshold": self.validation.confidence_threshold,
                "min_box_pixels": self.validation.min_box_pixels,
                "min_area_fraction": self.validation.min_area_fraction,
                "bounds_tolerance_pixels": self.validation.bounds_tolerance_pixels,
            },
            "lanes": self.lanes.as_dict(),
            "distance": {
                "mode": self.distance.mode,
                "horizon_fraction": self.distance.horizon_fraction,
            },
            "schema": self.schema.as_dict(),
        }


def _require_mapping(payload: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ConfigurationError(f"{name} must be a mapping")
    return payload


def _enum(value: Any, enum_type, name: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ConfigurationError(
            f"{name} must be one of: {allowed}"
        ) from exc


def load_perception_config(path: str | Path) -> PerceptionConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigurationError(f"perception config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload = _require_mapping(payload, "perception config")
    for key in ("preprocessing", "validation", "lanes", "distance", "classes"):
        if key not in payload:
            raise ConfigurationError(f"perception config is missing {key!r}")

    preprocessing = _require_mapping(payload["preprocessing"], "preprocessing")
    resize = preprocessing.get("resize")
    if resize is not None and not isinstance(resize, (list, tuple)):
        raise ConfigurationError("preprocessing.resize must be a pair or null")
    preprocess = PreprocessConfig(
        crop_left_fraction=float(preprocessing.get("crop_left_fraction", 0.0)),
        crop_right_fraction=float(preprocessing.get("crop_right_fraction", 0.0)),
        crop_top_fraction=float(preprocessing.get("crop_top_fraction", 0.0)),
        crop_bottom_fraction=float(preprocessing.get("crop_bottom_fraction", 0.0)),
        resize=tuple(resize) if resize is not None else None,
        mode=str(preprocessing.get("mode", "RGB")),
    )

    validation = _require_mapping(payload["validation"], "validation")
    validation_config = ValidationConfig(
        confidence_threshold=float(validation.get("confidence_threshold", 0.25)),
        min_box_pixels=float(validation.get("min_box_pixels", 2.0)),
        min_area_fraction=float(validation.get("min_area_fraction", 0.0)),
        bounds_tolerance_pixels=float(
            validation.get("bounds_tolerance_pixels", 0.0)
        ),
    )

    lanes = _require_mapping(payload["lanes"], "lanes")
    lane_config = LaneConfig(
        n_lanes=int(lanes.get("n_lanes", 3)),
        boundaries=tuple(float(value) for value in lanes["boundaries"]),
        min_overlap_fraction=float(lanes.get("min_overlap_fraction", 0.15)),
        majority_fraction=float(lanes.get("majority_fraction", 0.75)),
    )

    distance = _require_mapping(payload["distance"], "distance")
    distance_config = DistanceConfig(
        mode=str(distance.get("mode", "bottom_edge_proxy")),
        horizon_fraction=float(distance.get("horizon_fraction", 0.15)),
    )

    class_payload = payload["classes"]
    if not isinstance(class_payload, Sequence) or isinstance(class_payload, str):
        raise ConfigurationError("classes must be a sequence")
    definitions = []
    for entry in class_payload:
        entry = _require_mapping(entry, "class entry")
        definitions.append(
            ClassDefinition(
                class_id=entry.get("id"),
                name=str(entry.get("name", "")),
                role=_enum(entry.get("role"), ClassRole, "class role"),
                game_state_role=_enum(
                    entry.get("game_state_role"),
                    GameStateRole,
                    "class game_state_role",
                ),
            )
        )
    schema = ClassSchema(
        classes=tuple(definitions),
        player_class_ids=tuple(payload.get("player_class_ids", ())),
        coin_class_ids=tuple(payload.get("coin_class_ids", ())),
    )

    return PerceptionConfig(
        preprocess=preprocess,
        validation=validation_config,
        lanes=lane_config,
        distance=distance_config,
        schema=schema,
        source_path=path,
    )
