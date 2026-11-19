"""Deterministic action selection, conflict handling and timing constraints.

The Phase 4F decoder already decides which annotated populations are active and
which one is primary. This module adds the controller-level rules a game needs
and that the decoder deliberately does not implement:

``conflict_policy``
    ``decoder_primary`` keeps the decoder's primary action (the behaviour of
    the Phase 7 bridge); ``priority`` chooses the first active channel in the
    declared priority order; ``suppress_all`` emits ``NO_ACTION`` whenever more
    than one population is above threshold.
``min_hold_ms``
    A selected action cannot be replaced by a *different* non-neutral action
    before it has been held for this long. ``NO_ACTION`` always releases
    immediately, so a decoded absence of activity is never fabricated into a
    continued movement.
``cooldown_ms``
    After an action is left, it cannot be selected again until this much
    controller time has elapsed. Continuing the same action is not a
    re-selection and is never blocked.

SCIENTIFIC STATUS
    The selected state is a game command produced by the Phase 4 decoder from
    model activity. It is not a measured biological motor command, and the
    timing rules are game-controller conventions, not measured neural dynamics.
    The decoder scores, thresholds and populations are consumed unchanged; this
    module never alters them.

Times are the decoder window end (``[start_ms, end_ms)``) and are compared in
milliseconds. Selection is a pure function of the decoder output, the
controller time and the selector's own history; it uses no random numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

import numpy as np

from motor.populations import ACTION_POPULATIONS, UNSUPPORTED_ACTIONS

NO_ACTION = "NO_ACTION"
UNMAPPED = "UNMAPPED"
NEUTRAL = "NEUTRAL"

CONFLICT_POLICIES = ("decoder_primary", "priority", "suppress_all")
_NEUTRAL_STATES = (NO_ACTION, NEUTRAL)
_UNSUPPORTED_STATES = ("ROLL", "DUCK")


@dataclass(frozen=True)
class SelectionConfig:
    """Declared selection rules. Values are conventions, not fitted parameters."""

    conflict_policy: str = "decoder_primary"
    priority: tuple[str, ...] = ACTION_POPULATIONS
    min_hold_ms: float = 0.0
    cooldown_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.conflict_policy not in CONFLICT_POLICIES:
            raise ValueError(
                f"conflict_policy must be one of {CONFLICT_POLICIES}"
            )
        priority = tuple(str(value) for value in self.priority)
        if len(priority) != len(ACTION_POPULATIONS) or set(priority) != set(
            ACTION_POPULATIONS
        ):
            raise ValueError(
                f"priority must be a permutation of {ACTION_POPULATIONS}"
            )
        object.__setattr__(self, "priority", priority)
        for name in ("min_hold_ms", "cooldown_ms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            number = float(value)
            if not np.isfinite(number) or number < 0:
                raise ValueError(f"{name} must be finite and non-negative")
            object.__setattr__(self, name, number)

    @classmethod
    def from_config(cls, payload: Mapping) -> "SelectionConfig":
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise ValueError(f"unknown selection parameters: {unknown}")
        values = dict(payload)
        if "priority" in values:
            values["priority"] = tuple(str(value) for value in values["priority"])
        for name in ("min_hold_ms", "cooldown_ms"):
            if name in values:
                values[name] = float(values[name])
        return cls(**values)

    def describe(self) -> dict:
        return {
            "conflict_policy": self.conflict_policy,
            "priority": list(self.priority),
            "min_hold_ms": float(self.min_hold_ms),
            "cooldown_ms": float(self.cooldown_ms),
        }


@dataclass(frozen=True)
class ActionSelection:
    """One executable action plus the rule that produced it."""

    window_start_ms: float | None
    window_end_ms: float
    requested_state: str | None
    candidate_state: str | None
    selected_state: str
    active_channels: tuple[str, ...]
    conflict: bool
    conflict_policy: str
    suppressed_channels: tuple[str, ...]
    held: bool
    cooldown_blocked: bool
    cooldown_remaining_ms: float
    supported: bool
    unmapped: bool
    reason: str

    @property
    def neutral(self) -> bool:
        return self.selected_state == NO_ACTION

    def as_dict(self) -> dict:
        return {
            "window_start_ms": (
                None
                if self.window_start_ms is None
                else round(float(self.window_start_ms), 6)
            ),
            "window_end_ms": round(float(self.window_end_ms), 6),
            "requested_state": self.requested_state,
            "candidate_state": self.candidate_state,
            "selected_state": self.selected_state,
            "active_channels": list(self.active_channels),
            "conflict": bool(self.conflict),
            "conflict_policy": self.conflict_policy,
            "suppressed_channels": list(self.suppressed_channels),
            "held": bool(self.held),
            "cooldown_blocked": bool(self.cooldown_blocked),
            "cooldown_remaining_ms": round(
                float(self.cooldown_remaining_ms), 6
            ),
            "supported": bool(self.supported),
            "unmapped": bool(self.unmapped),
            "reason": self.reason,
            "neutral": self.neutral,
        }


def _read_output(
    output: Any, window_end_ms: float | None
) -> tuple[str | None, tuple[str, ...], float | None, float | None, str | None]:
    """Return ``(state, active_channels, start, end, error)``."""
    active: tuple[str, ...] = ()
    start: float | None = None
    output_end: float | None = None
    if output is None:
        return None, active, start, window_end_ms, "no motor state was supplied"
    if isinstance(output, Mapping):
        if "state" in output:
            state = output.get("state")
        elif "action" in output:
            state = output.get("action")
        else:
            return (
                None,
                active,
                start,
                window_end_ms,
                "mapping has neither 'state' nor 'action'",
            )
        raw_active = output.get("active_channels") or ()
        if isinstance(raw_active, (list, tuple)):
            active = tuple(str(item) for item in raw_active)
        start = output.get("window_start_ms")
        output_end = output.get("window_end_ms")
    elif isinstance(output, str):
        state = output
    else:
        state = getattr(output, "state", None)
        if state is None:
            value = getattr(output, "value", None)
            state = value if isinstance(value, str) else None
        raw_active = getattr(output, "active_channels", ()) or ()
        if isinstance(raw_active, (list, tuple)):
            active = tuple(str(item) for item in raw_active)
        start = getattr(output, "window_start_ms", None)
        output_end = getattr(output, "window_end_ms", None)
    end = output_end if output_end is not None else window_end_ms
    if state is None:
        return None, active, start, end, "motor output has no state"
    if not isinstance(state, str):
        return None, active, start, end, f"motor state {state!r} is not a string"
    for name, value in (("window_start_ms", start), ("window_end_ms", end)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, active, start, end, f"{name} must be a number"
        if not np.isfinite(float(value)):
            return None, active, start, end, f"{name} must be finite"
    return state, active, start, end, None


class ActionSelector:
    """Choose at most one executable action and apply the timing rules."""

    def __init__(self, config: SelectionConfig | None = None) -> None:
        self.config = config or SelectionConfig()
        self.reset()

    def reset(self) -> None:
        self._selected: str = NO_ACTION
        self._selected_since_ms: float | None = None
        self._exit_ms: dict[str, float] = {}
        self._last_time_ms: float | None = None

    @property
    def selected_state(self) -> str:
        return self._selected

    def describe(self) -> dict:
        return {
            "interface": "action_selection_v1",
            "states": [*ACTION_POPULATIONS, "ROLL", "DUCK", NO_ACTION, UNMAPPED],
            "config": self.config.describe(),
            "neutral_rule": (
                "NO_ACTION releases immediately; minimum hold only delays "
                "switches between two non-neutral actions"
            ),
            "cooldown_rule": (
                "an action cannot be re-selected for cooldown_ms after it was "
                "left; continuing it is not a re-selection"
            ),
            "unsupported_rule": (
                "ROLL, DUCK, UNMAPPED and unknown states select NO_ACTION and "
                "are reported as unsupported/unmapped"
            ),
            "timing_basis": "decoder window_end_ms",
            "determinism": "no random numbers; state is reset explicitly",
        }

    # ------------------------------------------------------------------

    def _selection(
        self,
        *,
        start: float | None,
        end: float,
        requested: str | None,
        candidate: str | None,
        selected: str,
        active: tuple[str, ...],
        conflict: bool,
        suppressed: tuple[str, ...],
        held: bool,
        cooldown_blocked: bool,
        cooldown_remaining_ms: float,
        supported: bool,
        unmapped: bool,
        reason: str,
    ) -> ActionSelection:
        return ActionSelection(
            window_start_ms=start,
            window_end_ms=end,
            requested_state=requested,
            candidate_state=candidate,
            selected_state=selected,
            active_channels=active,
            conflict=conflict,
            conflict_policy=self.config.conflict_policy,
            suppressed_channels=suppressed,
            held=held,
            cooldown_blocked=cooldown_blocked,
            cooldown_remaining_ms=cooldown_remaining_ms,
            supported=supported,
            unmapped=unmapped,
            reason=reason,
        )

    def _release(self, time_ms: float) -> None:
        if self._selected != NO_ACTION:
            self._exit_ms[self._selected] = float(time_ms)
            self._selected = NO_ACTION
            self._selected_since_ms = None

    def select(
        self, output: Any, *, window_end_ms: float | None = None
    ) -> ActionSelection:
        """Select one action for a decoder output.

        ``window_end_ms`` is required when the output itself does not carry a
        window end (for example when a caller passes a bare state string).
        """
        state, active, start, end, error = _read_output(output, window_end_ms)
        if end is None:
            raise ValueError(
                "window_end_ms is required when the motor output has no "
                "window_end_ms"
            )
        end = float(end)
        if start is not None:
            start = float(start)
        if self._last_time_ms is not None and end < self._last_time_ms:
            raise ValueError(
                "selection time cannot move backwards: "
                f"{end} < {self._last_time_ms}"
            )
        self._last_time_ms = end
        requested = None if state is None else state.strip().upper()
        active_named = tuple(
            dict.fromkeys(
                item.strip().upper()
                for item in active
                if isinstance(item, str) and item.strip()
            )
        )

        if error is not None:
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=active_named,
                conflict=False,
                suppressed=(),
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=False,
                unmapped=True,
                reason=f"{error}; NO_ACTION selected",
            )

        if requested in _UNSUPPORTED_STATES:
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=active_named,
                conflict=False,
                suppressed=(),
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=False,
                unmapped=True,
                reason=UNSUPPORTED_ACTIONS[requested],
            )

        if requested == UNMAPPED:
            self._release(end)
            reported = (
                output.get("reason")
                if isinstance(output, Mapping)
                else getattr(output, "reason", None)
            )
            if not isinstance(reported, str) or not reported:
                reported = "the decoder reported UNMAPPED"
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=active_named,
                conflict=False,
                suppressed=(),
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=False,
                unmapped=True,
                reason=reported,
            )

        if requested in _NEUTRAL_STATES:
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=(),
                conflict=False,
                suppressed=(),
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=True,
                unmapped=False,
                reason="decoder_reports_no_action",
            )

        if requested not in ACTION_POPULATIONS:
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=active_named,
                conflict=False,
                suppressed=(),
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=False,
                unmapped=True,
                reason=f"unknown motor state {requested!r}; NO_ACTION selected",
            )

        population_channels = tuple(
            name for name in active_named if name in ACTION_POPULATIONS
        )
        if requested in population_channels:
            channels = population_channels
        elif population_channels:
            channels = tuple(dict.fromkeys((requested, *population_channels)))
        else:
            channels = (requested,)
        conflict = len(channels) > 1

        if conflict and self.config.conflict_policy == "suppress_all":
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=None,
                selected=NO_ACTION,
                active=channels,
                conflict=True,
                suppressed=channels,
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=True,
                unmapped=False,
                reason="simultaneous_conflict_suppressed",
            )

        priority_index = {
            action: index for index, action in enumerate(self.config.priority)
        }
        if (
            self.config.conflict_policy == "decoder_primary"
            and requested in channels
        ):
            candidate = requested
        else:
            candidate = min(channels, key=priority_index.__getitem__)
        suppressed = tuple(name for name in channels if name != candidate)

        if self._selected == candidate:
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=candidate,
                selected=candidate,
                active=channels,
                conflict=conflict,
                suppressed=suppressed,
                held=False,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=True,
                unmapped=False,
                reason=(
                    "conflict_resolved_by_decoder_primary"
                    if conflict
                    else "continuing_action"
                ),
            )

        if (
            self._selected != NO_ACTION
            and self._selected_since_ms is not None
            and end - self._selected_since_ms < self.config.min_hold_ms
        ):
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=candidate,
                selected=self._selected,
                active=channels,
                conflict=conflict,
                suppressed=tuple(dict.fromkeys((candidate, *suppressed))),
                held=True,
                cooldown_blocked=False,
                cooldown_remaining_ms=0.0,
                supported=True,
                unmapped=False,
                reason="minimum_hold_active",
            )

        exit_time = self._exit_ms.get(candidate)
        remaining = 0.0
        if exit_time is not None:
            remaining = float(self.config.cooldown_ms) - (end - exit_time)
        if remaining > 0.0:
            self._release(end)
            return self._selection(
                start=start,
                end=end,
                requested=requested,
                candidate=candidate,
                selected=NO_ACTION,
                active=channels,
                conflict=conflict,
                suppressed=suppressed,
                held=False,
                cooldown_blocked=True,
                cooldown_remaining_ms=remaining,
                supported=True,
                unmapped=False,
                reason="cooldown_active",
            )

        if self._selected != NO_ACTION:
            self._exit_ms[self._selected] = end
        self._selected = candidate
        self._selected_since_ms = end
        return self._selection(
            start=start,
            end=end,
            requested=requested,
            candidate=candidate,
            selected=candidate,
            active=channels,
            conflict=conflict,
            suppressed=suppressed,
            held=False,
            cooldown_blocked=False,
            cooldown_remaining_ms=0.0,
            supported=True,
            unmapped=False,
            reason=(
                "conflict_resolved_by_decoder_primary"
                if conflict
                and self.config.conflict_policy == "decoder_primary"
                else "conflict_resolved_by_priority"
                if conflict
                else "selected_action"
            ),
        )


__all__ = [
    "ActionSelection",
    "ActionSelector",
    "CONFLICT_POLICIES",
    "SelectionConfig",
]
