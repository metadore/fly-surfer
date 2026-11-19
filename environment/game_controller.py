"""Phase 4 game controller: decoder -> selection -> executable game action.

This is the binding the original Phase 4 scope calls ``game_controller``. The
roadmap sketch names it ``motor/game_controller.py``; in this repository the
game-facing modules live under ``environment/`` and only this package touches
the game, so the controller is implemented here. It composes three existing
components without changing any of them:

``GameActionDecoder`` (``motor.action_decoder``)
    turns motor-population activity into a structured ``MotorOutput``;
``ActionSelector`` (``motor.action_selection``)
    applies conflict handling, minimum hold and cooldown to that output;
``GameActionAdapter`` (``environment.action_adapter``)
    records the requested state and the game action actually executed.

The controller never owns the episode loop. ``step`` hands the produced
mapping to whatever object provides the game's ``step`` (normally
``ControlledGameEnvironment``), so the same controller can be used by the live
closed loop, by a replay script or by a test double.

SCIENTIFIC STATUS
    A selected state is a game command decoded from simulated model activity.
    It is not a measured biological motor command, and the timing rules are
    controller conventions rather than measured neural dynamics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from environment.action_adapter import ActionMapping, GameActionAdapter
from motor.action_selection import ActionSelection, ActionSelector, SelectionConfig


@dataclass(frozen=True)
class ControllerCycle:
    """One decoded window, the selected action and the executed game action."""

    output: Any | None
    selection: ActionSelection
    mapping: ActionMapping

    def as_dict(self) -> dict:
        if self.output is None:
            output = None
        elif callable(getattr(self.output, "as_dict", None)):
            output = self.output.as_dict()
        elif isinstance(self.output, Mapping):
            output = dict(self.output)
        elif isinstance(self.output, str):
            output = self.output
        else:
            output = str(self.output)
        return {
            "output": output,
            "selection": self.selection.as_dict(),
            "mapping": self.mapping.as_dict(),
        }


class GameController:
    """Deterministic decoder -> selector -> adapter binding."""

    def __init__(
        self,
        decoder: Any,
        *,
        selector: ActionSelector | None = None,
        adapter: GameActionAdapter | None = None,
        selection_config: SelectionConfig | None = None,
    ) -> None:
        for name in ("decode_window", "reset"):
            if not callable(getattr(decoder, name, None)):
                raise TypeError(f"decoder must provide {name}()")
        if int(getattr(decoder, "n_neurons", 0)) < 1:
            raise ValueError("decoder must expose a positive n_neurons")
        if selector is not None and selection_config is not None:
            raise ValueError(
                "pass either a configured selector or a selection_config, "
                "not both"
            )
        if selector is not None:
            for name in ("select", "reset"):
                if not callable(getattr(selector, name, None)):
                    raise TypeError(f"selector must provide {name}()")
        self.decoder = decoder
        self.selector = selector or ActionSelector(selection_config)
        self.adapter = adapter or GameActionAdapter()
        self._last_time_ms: float = 0.0

    @property
    def n_neurons(self) -> int:
        return int(self.decoder.n_neurons)

    def reset(self) -> None:
        self.decoder.reset()
        self.selector.reset()
        self._last_time_ms = 0.0

    # ------------------------------------------------------------------

    def advance(
        self,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
    ) -> ControllerCycle:
        """Decode one window and produce the executable action."""
        output = self.decoder.decode_window(
            spike_times_ms, spike_neuron_indices, start_ms, end_ms
        )
        return self.advance_output(output)

    def advance_output(self, output: Any) -> ControllerCycle:
        """Select and map an already-decoded output."""
        selection = self.selector.select(
            output, window_end_ms=self._last_time_ms
        )
        self._last_time_ms = max(
            self._last_time_ms, float(selection.window_end_ms)
        )
        state = (
            selection.requested_state
            if selection.unmapped
            else selection.selected_state
        )
        mapping = self.adapter.map(state)
        return ControllerCycle(
            output=output,
            selection=selection,
            mapping=mapping,
        )

    def step(self, environment: Any, cycle: ControllerCycle) -> Any:
        """Execute one controller cycle in a game environment."""
        if not callable(getattr(environment, "step", None)):
            raise TypeError("environment must provide step()")
        return environment.step(cycle.mapping)

    def describe(self) -> dict:
        return {
            "interface": "phase_4_game_controller_v1",
            "pipeline": [
                "GameActionDecoder.decode_window",
                "ActionSelector.select",
                "GameActionAdapter.map",
                "environment.step",
            ],
            "selection": self.selector.describe(),
            "action_adapter": self.adapter.describe(),
            "decoder": (
                self.decoder.describe()
                if callable(getattr(self.decoder, "describe", None))
                else None
            ),
            "note": (
                "the controller produces one game action per decoder window; "
                "it never changes decoder thresholds, populations or scores"
            ),
        }


__all__ = ["ControllerCycle", "GameController"]
