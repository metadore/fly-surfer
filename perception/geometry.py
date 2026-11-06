"""Bounding-box geometry in screen and normalised viewport coordinates.

Screen coordinates are pixels relative to the original screenshot. Normalised
coordinates are fractions of the processed viewport (after optional crop and
before optional resize), which is the frame used for lane assignment. The two
representations are separate types so they cannot be mixed accidentally.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned box in original screen pixels."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        x1 = _finite(self.x1, "x1")
        y1 = _finite(self.y1, "y1")
        x2 = _finite(self.x2, "x2")
        y2 = _finite(self.y2, "y2")
        if x2 <= x1:
            raise ValueError("x2 must be greater than x1")
        if y2 <= y1:
            raise ValueError("y2 must be greater than y1")
        object.__setattr__(self, "x1", x1)
        object.__setattr__(self, "y1", y1)
        object.__setattr__(self, "x2", x2)
        object.__setattr__(self, "y2", y2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass(frozen=True)
class NormalizedBox:
    """Axis-aligned box in viewport fractions, both axes in [0, 1]."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        values = {
            "x1": _finite(self.x1, "x1"),
            "y1": _finite(self.y1, "y1"),
            "x2": _finite(self.x2, "x2"),
            "y2": _finite(self.y2, "y2"),
        }
        if any(not 0.0 <= value <= 1.0 for value in values.values()):
            raise ValueError("normalised coordinates must be in [0, 1]")
        if values["x2"] <= values["x1"]:
            raise ValueError("x2 must be greater than x1")
        if values["y2"] <= values["y1"]:
            raise ValueError("y2 must be greater than y1")
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def bottom(self) -> float:
        return self.y2

    def horizontal_overlap(self, left: float, right: float) -> float:
        """Width of the intersection with a vertical band, in box fractions."""
        overlap = max(0.0, min(self.x2, right) - max(self.x1, left))
        return overlap / self.width

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


def bottom_edge_distance(box: NormalizedBox, horizon_fraction: float) -> float:
    """Uncalibrated near/far proxy: 0 near the bottom, 1 at the horizon.

    This is the convention already used by ``GameState`` (0 near, 1 far). It
    is image geometry, not a metric distance and not a game measurement.
    """
    horizon = _finite(horizon_fraction, "horizon_fraction")
    if not 0.0 <= horizon < 1.0:
        raise ValueError("horizon_fraction must be in [0, 1)")
    return min(1.0, max(0.0, (1.0 - box.bottom) / (1.0 - horizon)))
