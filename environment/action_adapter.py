"""Translate Phase 4 motor output into an action the game can execute.

The Phase 4 decoder reports a motor state, not a game command. This adapter
keeps that distinction: it records the requested state and the action that is
actually executed. ``UNMAPPED`` never becomes an arbitrary game action; it and
every unsupported or invalid state execute ``NO_ACTION`` with a recorded
reason. The game itself still validates the five documented actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from motor.action_decoder import MotorOutput

GAME_ACTIONS = ("LEFT", "RIGHT", "JUMP", "ROLL", "NO_ACTION")
NO_ACTION = "NO_ACTION"

_DIRECT_STATES = frozenset(GAME_ACTIONS)
_UNSUPPORTED_STATES = {
    "UNMAPPED": (
        "the Phase 4 decoder reported UNMAPPED; NO_ACTION is executed rather "
        "than an arbitrary game action"
    ),
    "DUCK": (
        "the controlled game has no duck action; DUCK is executed as "
        "NO_ACTION"
    ),
}


@dataclass(frozen=True)
class ActionMapping:
    """One motor state and the action the game received."""

    requested_state: str | None
    executed_action: str
    supported: bool
    unmapped: bool
    reason: str
    channel: str | None = None

    def as_dict(self) -> dict:
        return {
            "requested_state": self.requested_state,
            "executed_action": self.executed_action,
            "supported": self.supported,
            "unmapped": self.unmapped,
            "reason": self.reason,
            "channel": self.channel,
        }


def _state_from(output: Any) -> tuple[str | None, str | None, str | None]:
    """Return ``(state, channel, error)`` for a motor output or mapping."""
    channel = None
    if output is None:
        return None, channel, None
    if isinstance(output, MotorOutput):
        return output.state, output.requested_channel, None
    if isinstance(output, Mapping):
        channel = output.get("requested_channel")
        if "state" in output:
            state = output.get("state")
        elif "action" in output:
            state = output.get("action")
        else:
            return None, channel, "mapping has neither 'state' nor 'action'"
    elif isinstance(output, str):
        state = output
    else:
        value = getattr(output, "value", None)
        if isinstance(value, str):
            state = value
        else:
            return None, channel, f"unsupported motor output type {type(output).__name__}"
    if not isinstance(state, str):
        return None, channel, f"motor state {state!r} is not a string"
    return state, channel, None


class GameActionAdapter:
    """Map a motor state to a documented game action without inventing one."""

    def map(self, output: Any) -> ActionMapping:
        state, channel, error = _state_from(output)
        if error is not None:
            return ActionMapping(
                requested_state=None,
                executed_action=NO_ACTION,
                supported=False,
                unmapped=True,
                reason=f"{error}; NO_ACTION executed",
                channel=channel,
            )
        if state is None:
            return ActionMapping(
                requested_state=None,
                executed_action=NO_ACTION,
                supported=False,
                unmapped=False,
                reason="no motor state was supplied; NO_ACTION executed",
                channel=channel,
            )
        name = state.strip().upper()
        if name in _DIRECT_STATES:
            return ActionMapping(
                requested_state=name,
                executed_action=name,
                supported=True,
                unmapped=False,
                reason="motor state maps directly to the game action",
                channel=channel,
            )
        if name in _UNSUPPORTED_STATES:
            return ActionMapping(
                requested_state=name,
                executed_action=NO_ACTION,
                supported=False,
                unmapped=True,
                reason=_UNSUPPORTED_STATES[name],
                channel=channel,
            )
        return ActionMapping(
            requested_state=name,
            executed_action=NO_ACTION,
            supported=False,
            unmapped=True,
            reason=f"unknown motor state {name!r}; NO_ACTION executed",
            channel=channel,
        )

    def describe(self) -> dict:
        return {
            "interface": "motor_output_to_game_action_v1",
            "direct_states": list(GAME_ACTIONS),
            "unsupported_states": dict(_UNSUPPORTED_STATES),
            "unknown_state_policy": "NO_ACTION with an explicit reason",
            "invalid_output_policy": "NO_ACTION with an explicit reason",
            "note": (
                "the requested motor state and the executed game action are "
                "recorded separately; no unsupported state becomes a "
                "different action"
            ),
        }
