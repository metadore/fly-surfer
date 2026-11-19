"""Focused tests for Phase 4 action selection, conflict and timing rules.

All activity used here is synthetic. These tests exercise the controller rules,
not BANC motor activity and not fly behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from motor.action_selection import (
    ActionSelector,
    SelectionConfig,
)


def output(
    state,
    active=None,
    *,
    start=0.0,
    end=50.0,
    reason="",
):
    return {
        "state": state,
        "active_channels": list(active or []),
        "window_start_ms": start,
        "window_end_ms": end,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def test_default_config_is_neutral_and_declared() -> None:
    config = SelectionConfig()
    assert config.conflict_policy == "decoder_primary"
    assert config.priority == ("LEFT", "RIGHT", "JUMP")
    assert config.min_hold_ms == 0.0
    assert config.cooldown_ms == 0.0


def test_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        SelectionConfig(conflict_policy="first")
    with pytest.raises(ValueError):
        SelectionConfig(priority=("LEFT", "RIGHT"))
    with pytest.raises(ValueError):
        SelectionConfig(priority=("LEFT", "LEFT", "JUMP"))
    with pytest.raises(ValueError):
        SelectionConfig(min_hold_ms=-1.0)
    with pytest.raises(ValueError):
        SelectionConfig(cooldown_ms=float("nan"))
    with pytest.raises(ValueError):
        SelectionConfig(min_hold_ms="50")


def test_config_from_config_converts_and_rejects_unknown() -> None:
    config = SelectionConfig.from_config(
        {
            "conflict_policy": "priority",
            "priority": ["JUMP", "LEFT", "RIGHT"],
            "min_hold_ms": "100",
            "cooldown_ms": 200,
        }
    )
    assert config.priority == ("JUMP", "LEFT", "RIGHT")
    assert config.min_hold_ms == 100.0
    assert config.cooldown_ms == 200.0
    with pytest.raises(ValueError):
        SelectionConfig.from_config({"unknown": 1})


def test_describe_states_the_rules() -> None:
    described = ActionSelector().describe()
    assert described["interface"] == "action_selection_v1"
    assert "NO_ACTION" in described["states"]
    assert described["determinism"].startswith("no random numbers")


# ---------------------------------------------------------------------------
# neutral, single and continued states
# ---------------------------------------------------------------------------


def test_no_action_is_neutral_and_supported() -> None:
    selection = ActionSelector().select(output("NO_ACTION"))
    assert selection.selected_state == "NO_ACTION"
    assert selection.neutral
    assert selection.supported and not selection.unmapped
    assert selection.reason == "decoder_reports_no_action"


def test_single_active_population_is_selected() -> None:
    selection = ActionSelector().select(output("LEFT", ["LEFT"]))
    assert selection.selected_state == "LEFT"
    assert selection.requested_state == "LEFT"
    assert selection.candidate_state == "LEFT"
    assert selection.active_channels == ("LEFT",)
    assert not selection.conflict
    assert selection.reason == "selected_action"


def test_repeating_the_same_action_continues_without_a_switch() -> None:
    selector = ActionSelector(SelectionConfig(min_hold_ms=500, cooldown_ms=500))
    first = selector.select(output("LEFT", ["LEFT"], end=50.0))
    second = selector.select(output("LEFT", ["LEFT"], end=100.0))
    assert first.selected_state == "LEFT"
    assert second.selected_state == "LEFT"
    assert second.reason == "continuing_action"
    assert not second.held and not second.cooldown_blocked


# ---------------------------------------------------------------------------
# conflicting populations
# ---------------------------------------------------------------------------


def test_conflict_uses_the_decoder_primary_by_default() -> None:
    selection = ActionSelector().select(
        output("RIGHT", ["LEFT", "RIGHT"])
    )
    assert selection.conflict
    assert selection.selected_state == "RIGHT"
    assert selection.suppressed_channels == ("LEFT",)
    assert selection.reason == "conflict_resolved_by_decoder_primary"


def test_conflict_priority_overrides_the_decoder_primary() -> None:
    selector = ActionSelector(
        SelectionConfig(
            conflict_policy="priority",
            priority=("RIGHT", "LEFT", "JUMP"),
        )
    )
    selection = selector.select(output("LEFT", ["LEFT", "RIGHT"]))
    assert selection.requested_state == "LEFT"
    assert selection.selected_state == "RIGHT"
    assert selection.suppressed_channels == ("LEFT",)
    assert selection.reason == "conflict_resolved_by_priority"


def test_conflict_suppress_all_emits_no_action() -> None:
    selector = ActionSelector(
        SelectionConfig(conflict_policy="suppress_all")
    )
    selection = selector.select(output("LEFT", ["LEFT", "JUMP"]))
    assert selection.selected_state == "NO_ACTION"
    assert selection.conflict
    assert set(selection.suppressed_channels) == {"LEFT", "JUMP"}
    assert selection.supported and not selection.unmapped
    assert selection.reason == "simultaneous_conflict_suppressed"


# ---------------------------------------------------------------------------
# minimum hold
# ---------------------------------------------------------------------------


def test_minimum_hold_delays_but_does_not_block_a_switch() -> None:
    selector = ActionSelector(SelectionConfig(min_hold_ms=100.0))
    selector.select(output("LEFT", ["LEFT"], end=50.0))
    held = selector.select(output("RIGHT", ["RIGHT"], end=100.0))
    assert held.selected_state == "LEFT"
    assert held.held
    assert held.candidate_state == "RIGHT"
    assert held.suppressed_channels == ("RIGHT",)
    assert held.reason == "minimum_hold_active"

    switched = selector.select(output("RIGHT", ["RIGHT"], end=150.0))
    assert switched.selected_state == "RIGHT"
    assert not switched.held
    assert switched.reason == "selected_action"


def test_no_action_releases_immediately_despite_minimum_hold() -> None:
    selector = ActionSelector(SelectionConfig(min_hold_ms=1000.0))
    selector.select(output("LEFT", ["LEFT"], end=50.0))
    released = selector.select(output("NO_ACTION", end=60.0))
    assert released.selected_state == "NO_ACTION"
    assert not released.held
    assert released.reason == "decoder_reports_no_action"


# ---------------------------------------------------------------------------
# cooldown
# ---------------------------------------------------------------------------


def test_cooldown_blocks_re_selection_after_the_action_is_left() -> None:
    selector = ActionSelector(SelectionConfig(cooldown_ms=200.0))
    selector.select(output("LEFT", ["LEFT"], end=0.0))
    selector.select(output("NO_ACTION", end=50.0))

    blocked = selector.select(output("LEFT", ["LEFT"], end=100.0))
    assert blocked.selected_state == "NO_ACTION"
    assert blocked.cooldown_blocked
    assert blocked.cooldown_remaining_ms == pytest.approx(150.0)
    assert blocked.reason == "cooldown_active"

    allowed = selector.select(output("LEFT", ["LEFT"], end=300.0))
    assert allowed.selected_state == "LEFT"
    assert not allowed.cooldown_blocked


def test_cooldown_does_not_block_a_continuing_action() -> None:
    selector = ActionSelector(SelectionConfig(cooldown_ms=1000.0))
    selector.select(output("LEFT", ["LEFT"], end=0.0))
    continuing = selector.select(output("LEFT", ["LEFT"], end=50.0))
    assert continuing.selected_state == "LEFT"
    assert not continuing.cooldown_blocked


# ---------------------------------------------------------------------------
# unsupported and invalid outputs
# ---------------------------------------------------------------------------


def test_duck_and_roll_select_no_action_with_their_reasons() -> None:
    selector = ActionSelector()
    duck = selector.select(output("DUCK"))
    assert duck.selected_state == "NO_ACTION"
    assert duck.supported is False and duck.unmapped is True
    assert duck.requested_state == "DUCK"
    assert "duck" in duck.reason.lower()

    roll = selector.select(output("ROLL"), window_end_ms=100.0)
    assert roll.selected_state == "NO_ACTION"
    assert roll.unmapped is True
    assert "roll" in roll.reason.lower()


def test_unmapped_preserves_the_decoder_reason() -> None:
    selection = ActionSelector().select(
        output("UNMAPPED", reason="no annotated population maps to ROLL")
    )
    assert selection.selected_state == "NO_ACTION"
    assert selection.unmapped
    assert selection.reason == "no annotated population maps to ROLL"


def test_unknown_state_selects_no_action() -> None:
    selection = ActionSelector().select(output("FLY"))
    assert selection.selected_state == "NO_ACTION"
    assert selection.unmapped
    assert "unknown motor state" in selection.reason


@pytest.mark.parametrize(
    "value",
    [None, {"action": None}, {"window_end_ms": 50.0}, 17, {"state": 5}],
)
def test_invalid_outputs_select_no_action(value) -> None:
    selection = ActionSelector().select(
        value, window_end_ms=50.0
    )
    assert selection.selected_state == "NO_ACTION"
    assert selection.unmapped and not selection.supported
    assert selection.reason


def test_missing_window_end_is_rejected() -> None:
    with pytest.raises(ValueError):
        ActionSelector().select("LEFT")


def test_selection_time_cannot_move_backwards() -> None:
    selector = ActionSelector()
    selector.select(output("LEFT", ["LEFT"], end=100.0))
    with pytest.raises(ValueError):
        selector.select(output("LEFT", ["LEFT"], end=50.0))


# ---------------------------------------------------------------------------
# determinism and reset
# ---------------------------------------------------------------------------


def test_identical_sequences_produce_identical_selections() -> None:
    sequence = [
        output("LEFT", ["LEFT"], end=0.0),
        output("RIGHT", ["LEFT", "RIGHT"], end=50.0),
        output("NO_ACTION", end=100.0),
        output("RIGHT", ["RIGHT"], end=150.0),
    ]
    config = SelectionConfig(
        conflict_policy="priority",
        priority=("RIGHT", "LEFT", "JUMP"),
        min_hold_ms=50.0,
        cooldown_ms=100.0,
    )
    first = ActionSelector(config)
    second = ActionSelector(config)
    records_a = [first.select(item).as_dict() for item in sequence]
    records_b = [second.select(item).as_dict() for item in sequence]
    assert records_a == records_b


def test_reset_clears_hold_and_cooldown_history() -> None:
    selector = ActionSelector(
        SelectionConfig(min_hold_ms=100.0, cooldown_ms=200.0)
    )
    selector.select(output("LEFT", ["LEFT"], end=0.0))
    selector.select(output("NO_ACTION", end=50.0))
    selector.reset()
    selected = selector.select(output("RIGHT", ["RIGHT"], end=0.0))
    assert selected.selected_state == "RIGHT"
    assert not selected.cooldown_blocked
