"""Configurable lane assignment from normalised box geometry.

Only horizontal overlap with the configured lane bands is used. A box that
touches several lanes keeps the per-lane fractions and is either assigned by a
majority rule (flagged ambiguous) or left unassigned. It is never forced into
a lane.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from perception.config import LaneConfig
from perception.geometry import NormalizedBox

_EPSILON = 1e-9


class LaneReason(str, Enum):
    """How a lane decision was reached."""

    SINGLE_LANE = "single_lane_overlap"
    MAJORITY_OVERLAP = "majority_overlap"
    STRADDLES_LANES = "straddles_lanes"
    NO_LANE_OVERLAP = "no_lane_overlap"


@dataclass(frozen=True)
class LaneAssignment:
    """Lane decision for one box.

    ``overlap_fractions`` has one entry per configured lane. A lane is
    "touched" when its overlap reaches ``min_overlap_fraction``. ``lane`` is
    ``None`` when the box does not touch any lane or when no lane reaches the
    majority fraction. ``ambiguous`` is True when more than one lane is
    touched, whether or not a lane was assigned.
    """

    lane: int | None
    touched_lanes: tuple[int, ...]
    overlap_fractions: tuple[float, ...]
    confident: bool
    ambiguous: bool
    reason: LaneReason

    @property
    def assigned(self) -> bool:
        return self.lane is not None

    def as_dict(self) -> dict:
        return {
            "lane": self.lane,
            "touched_lanes": list(self.touched_lanes),
            "overlap_fractions": [round(value, 6) for value in self.overlap_fractions],
            "confident": self.confident,
            "ambiguous": self.ambiguous,
            "reason": self.reason.value,
        }


class LaneAssigner:
    """Map a normalized box to zero or one lane using configured bands."""

    def __init__(self, config: LaneConfig) -> None:
        if not isinstance(config, LaneConfig):
            raise ValueError("config must be a LaneConfig")
        self.config = config
        self.boundaries = tuple(config.boundaries)

    def overlap_fractions(self, box: NormalizedBox) -> tuple[float, ...]:
        return tuple(
            box.horizontal_overlap(left, right)
            for left, right in zip(self.boundaries, self.boundaries[1:])
        )

    def assign(self, box: NormalizedBox) -> LaneAssignment:
        if not isinstance(box, NormalizedBox):
            raise ValueError("box must be a NormalizedBox")
        fractions = self.overlap_fractions(box)
        touched = tuple(
            lane
            for lane, fraction in enumerate(fractions)
            if fraction + _EPSILON >= self.config.min_overlap_fraction
        )
        if not touched:
            return LaneAssignment(
                lane=None,
                touched_lanes=(),
                overlap_fractions=fractions,
                confident=False,
                ambiguous=False,
                reason=LaneReason.NO_LANE_OVERLAP,
            )
        if len(touched) == 1:
            return LaneAssignment(
                lane=touched[0],
                touched_lanes=touched,
                overlap_fractions=fractions,
                confident=True,
                ambiguous=False,
                reason=LaneReason.SINGLE_LANE,
            )

        ranked = sorted(
            touched, key=lambda lane: fractions[lane], reverse=True
        )
        best = ranked[0]
        runner_up = fractions[ranked[1]]
        if fractions[best] >= self.config.majority_fraction and fractions[best] > runner_up + _EPSILON:
            return LaneAssignment(
                lane=best,
                touched_lanes=touched,
                overlap_fractions=fractions,
                confident=True,
                ambiguous=True,
                reason=LaneReason.MAJORITY_OVERLAP,
            )
        return LaneAssignment(
            lane=None,
            touched_lanes=touched,
            overlap_fractions=fractions,
            confident=False,
            ambiguous=True,
            reason=LaneReason.STRADDLES_LANES,
        )
