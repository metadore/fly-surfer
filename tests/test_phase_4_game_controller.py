"""Focused tests for the Phase 4 game controller (decoder -> selection -> game).

All spikes and populations here are synthetic. The tests verify the controller
contract and fallback behaviour; they are not evidence of BANC motor activity.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from environment.game_controller import GameController
from motor.action_decoder import GameActionDecoder
from motor.action_selection import ActionSelector, SelectionConfig
from motor.motor_decoder import DecoderConfig
from motor.populations import ACTION_POPULATIONS, MotorPopulations


def synthetic_populations(sizes=None) -> MotorPopulations:
    sizes = sizes or {"LEFT": 10, "RIGHT": 10, "JUMP": 10}
    total = sum(sizes.values())
    masks = {}
    cursor = 0
    for action in ACTION_POPULATIONS:
        size = int(sizes.get(action, 0))
        mask = np.zeros(total, dtype=bool)
        mask[cursor : cursor + size] = True
        cursor += size
        masks[action] = mask
    motor = np.zeros(total, dtype=bool)
    for mask in masks.values():
        motor |= mask
    return MotorPopulations(
        n_neurons=total,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=np.zeros(total, dtype=bool),
        composition={},
        provenance={},
    )


def synthetic_spikes(
    populations: MotorPopulations,
    active: dict[str, int],
    *,
    time_ms: float = 25.0,
) -> tuple[np.ndarray, np.ndarray]:
    times: list[np.ndarray] = []
    indices: list[np.ndarray] = []
    for action, count in active.items():
        members = np.flatnonzero(populations.mask(action))[: int(count)]
        times.append(np.full(members.size, time_ms, dtype=float))
        indices.append(members)
    if not times:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
    return np.concatenate(times), np.concatenate(indices).astype(np.int64)


def make_controller(*, selection=None, populations=None) -> GameController:
    populations = populations or synthetic_populations()
    decoder = GameActionDecoder(populations, DecoderConfig())
    return GameController(decoder, selection_config=selection)


class FakeEnvironment:
    def __init__(self) -> None:
        self.actions: list[str] = []
        self.mappings: list[dict] = []

    def step(self, action):
        self.actions.append(action.executed_action)
        self.mappings.append(action.as_dict())
        return {"executed_action": action.executed_action}


# ---------------------------------------------------------------------------
# thresholds and supported actions
# ---------------------------------------------------------------------------


def test_subthreshold_activity_executes_no_action() -> None:
    controller = make_controller()
    populations = controller.decoder.populations
    cycle = controller.advance(*synthetic_spikes(populations, {"LEFT": 1}), 0.0, 50.0)
    assert cycle.selection.selected_state == "NO_ACTION"
    assert cycle.mapping.executed_action == "NO_ACTION"
    assert cycle.mapping.supported is True


def test_supported_synthetic_activity_reaches_the_game() -> None:
    """Synthetic end to end: spikes -> decoder -> selector -> game action."""
    controller = make_controller()
    populations = controller.decoder.populations
    environment = FakeEnvironment()
    cycle = controller.advance(
        *synthetic_spikes(populations, {"LEFT": 5}), 0.0, 50.0
    )
    result = controller.step(environment, cycle)
    assert cycle.output.state == "LEFT"
    assert cycle.selection.selected_state == "LEFT"
    assert cycle.mapping.requested_state == "LEFT"
    assert cycle.mapping.executed_action == "LEFT"
    assert result["executed_action"] == "LEFT"
    assert environment.actions == ["LEFT"]
    assert environment.mappings[0]["supported"] is True


# ---------------------------------------------------------------------------
# conflicting populations
# ---------------------------------------------------------------------------


def test_conflict_is_resolved_before_the_game_action() -> None:
    controller = make_controller()
    populations = controller.decoder.populations
    times, indices = synthetic_spikes(populations, {"LEFT": 5, "RIGHT": 5})
    cycle = controller.advance(times, indices, 0.0, 50.0)
    assert cycle.output.active_channels == ("LEFT", "RIGHT")
    assert cycle.selection.conflict is True
    assert cycle.selection.selected_state == "LEFT"
    assert cycle.selection.suppressed_channels == ("RIGHT",)
    assert cycle.mapping.executed_action == "LEFT"


def test_suppress_all_policy_prevents_a_conflicting_command() -> None:
    controller = make_controller(
        selection=SelectionConfig(conflict_policy="suppress_all")
    )
    populations = controller.decoder.populations
    times, indices = synthetic_spikes(populations, {"LEFT": 5, "JUMP": 5})
    cycle = controller.advance(times, indices, 0.0, 50.0)
    assert cycle.selection.conflict is True
    assert cycle.mapping.executed_action == "NO_ACTION"
    assert cycle.mapping.supported is True
    assert cycle.selection.reason == "simultaneous_conflict_suppressed"


# ---------------------------------------------------------------------------
# unsupported, unmapped and invalid outputs
# ---------------------------------------------------------------------------


def test_roll_request_never_becomes_a_game_action() -> None:
    controller = make_controller()
    empty = np.empty(0)
    output = controller.decoder.decode_requested(
        "ROLL", empty, empty.astype(int), 0.0, 50.0
    )
    cycle = controller.advance_output(output)
    assert output.state == "UNMAPPED"
    assert cycle.selection.unmapped
    assert cycle.mapping.requested_state == "UNMAPPED"
    assert cycle.mapping.executed_action == "NO_ACTION"
    assert cycle.mapping.supported is False and cycle.mapping.unmapped is True
    assert "UNMAPPED" in cycle.mapping.reason


def test_duck_request_is_recorded_and_not_executed() -> None:
    cycle = make_controller().advance_output("DUCK")
    assert cycle.selection.requested_state == "DUCK"
    assert cycle.selection.unmapped
    assert cycle.mapping.requested_state == "DUCK"
    assert cycle.mapping.executed_action == "NO_ACTION"
    assert cycle.mapping.supported is False
    assert "duck" in cycle.mapping.reason.lower()


@pytest.mark.parametrize("value", [None, {"window_end_ms": 50.0}, 17, {"state": 5}])
def test_invalid_outputs_are_safe(value) -> None:
    cycle = make_controller().advance_output(value)
    assert cycle.selection.selected_state == "NO_ACTION"
    assert cycle.mapping.executed_action == "NO_ACTION"
    assert cycle.mapping.supported is False


# ---------------------------------------------------------------------------
# timing through the real decoder
# ---------------------------------------------------------------------------


def test_minimum_hold_is_applied_to_decoder_windows() -> None:
    controller = make_controller(selection=SelectionConfig(min_hold_ms=100.0))
    populations = controller.decoder.populations
    left_times, left_indices = synthetic_spikes(
        populations, {"LEFT": 5}, time_ms=25.0
    )
    right_times, right_indices = synthetic_spikes(
        populations, {"RIGHT": 5}, time_ms=75.0
    )
    later_times, later_indices = synthetic_spikes(
        populations, {"RIGHT": 5}, time_ms=125.0
    )
    times = np.concatenate([left_times, right_times, later_times])
    indices = np.concatenate([left_indices, right_indices, later_indices])

    first = controller.advance(times, indices, 0.0, 50.0)
    held = controller.advance(times, indices, 50.0, 100.0)
    switched = controller.advance(times, indices, 100.0, 150.0)

    assert first.mapping.executed_action == "LEFT"
    assert held.mapping.executed_action == "LEFT"
    assert held.selection.held is True
    assert held.selection.candidate_state == "RIGHT"
    assert switched.mapping.executed_action == "RIGHT"


def test_neutral_window_releases_the_held_action() -> None:
    controller = make_controller(selection=SelectionConfig(min_hold_ms=1000.0))
    populations = controller.decoder.populations
    times, indices = synthetic_spikes(populations, {"LEFT": 5}, time_ms=25.0)
    controller.advance(times, indices, 0.0, 50.0)
    released = controller.advance(times, indices, 50.0, 100.0)
    assert released.selection.requested_state == "NO_ACTION"
    assert released.mapping.executed_action == "NO_ACTION"
    assert released.selection.held is False


# ---------------------------------------------------------------------------
# determinism, reset and validation
# ---------------------------------------------------------------------------


def test_controllers_replay_identically() -> None:
    cycles = []
    for _ in range(2):
        controller = make_controller(
            selection=SelectionConfig(
                conflict_policy="priority",
                priority=("RIGHT", "LEFT", "JUMP"),
                min_hold_ms=50.0,
                cooldown_ms=100.0,
            )
        )
        populations = controller.decoder.populations
        times, indices = synthetic_spikes(
            populations, {"LEFT": 5, "RIGHT": 5}, time_ms=25.0
        )
        cycles.append(
            [
                controller.advance(times, indices, 0.0, 50.0).as_dict(),
                controller.advance(times, indices, 50.0, 100.0).as_dict(),
            ]
        )
    assert cycles[0] == cycles[1]


def test_reset_restores_the_initial_controller_state() -> None:
    controller = make_controller()
    populations = controller.decoder.populations
    times, indices = synthetic_spikes(populations, {"LEFT": 5})
    first = controller.advance(times, indices, 0.0, 50.0)
    controller.reset()
    again = controller.advance(times, indices, 0.0, 50.0)
    assert first.as_dict() == again.as_dict()


def test_controller_rejects_incomplete_components() -> None:
    populations = synthetic_populations()
    decoder = GameActionDecoder(populations, DecoderConfig())
    with pytest.raises(TypeError):
        GameController(object())
    with pytest.raises(ValueError):
        GameController(decoder, selector=ActionSelector(), selection_config=SelectionConfig())
    with pytest.raises(TypeError):
        GameController(decoder, selector=object())
    with pytest.raises(TypeError):
        make_controller().step(object(), None)


def test_describe_reports_the_complete_pipeline() -> None:
    described = make_controller().describe()
    assert described["interface"] == "phase_4_game_controller_v1"
    assert described["pipeline"] == [
        "GameActionDecoder.decode_window",
        "ActionSelector.select",
        "GameActionAdapter.map",
        "environment.step",
    ]
    assert described["selection"]["interface"] == "action_selection_v1"
    assert described["decoder"]["interface"] == "game_action_v1"
