"""Phase 4F deterministic motor decoder."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.neural_activity import SpikeRecorder
from motor.motor_decoder import ActionDecision, DecoderConfig, MotorDecoder
from motor.populations import ACTION_POPULATIONS, MotorPopulations


def make_populations(
    sizes: dict[str, int], n_neurons: int | None = None
) -> MotorPopulations:
    total = int(n_neurons if n_neurons is not None else sum(sizes.values()))
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
    unassigned = np.zeros(total, dtype=bool)
    return MotorPopulations(
        n_neurons=total,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=unassigned,
        composition={},
        provenance={},
    )


def spikes(
    populations: MotorPopulations,
    active: dict[str, int],
    *,
    time_ms: float = 25.0,
    repeats: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    times: list[np.ndarray] = []
    indices: list[np.ndarray] = []
    for action, count in active.items():
        members = np.flatnonzero(populations.mask(action))[: int(count)]
        for repeat in range(repeats):
            times.append(np.full(members.size, time_ms + repeat, dtype=float))
            indices.append(members)
    if not times:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
    return np.concatenate(times), np.concatenate(indices).astype(np.int64)


def default_decoder(**overrides) -> tuple[MotorDecoder, MotorPopulations]:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    return MotorDecoder(populations, DecoderConfig(**overrides)), populations


def test_no_spikes_is_neutral() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {}), 0.0, 50.0)
    assert decision.state == "NEUTRAL"
    assert decision.neutral
    assert decision.active_actions == ()
    assert decision.reason == "neutral_no_activation"
    assert all(value == 0.0 for value in decision.scores.values())


def test_left_only_selects_left() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {"LEFT": 7}), 0.0, 50.0)
    assert decision.state == "LEFT"
    assert decision.active_actions == ("LEFT",)
    assert decision.scores["LEFT"] == pytest.approx(0.7)
    assert decision.scores["RIGHT"] == 0.0


def test_right_only_selects_right() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {"RIGHT": 6}), 0.0, 50.0)
    assert decision.state == "RIGHT"
    assert decision.active_actions == ("RIGHT",)


def test_jump_only_selects_jump() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {"JUMP": 5}), 0.0, 50.0)
    assert decision.state == "JUMP"
    assert decision.active_actions == ("JUMP",)


def test_bilateral_reports_both_and_priority_primary() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 6, "RIGHT": 6}), 0.0, 50.0
    )
    assert decision.active_actions == ("LEFT", "RIGHT")
    assert decision.primary_action == "LEFT"
    assert decision.reason == "tie_broken_by_priority"


def test_left_jump_reports_both_populations() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 6, "JUMP": 6}), 0.0, 50.0
    )
    assert decision.active_actions == ("LEFT", "JUMP")
    assert decision.primary_action == "LEFT"


def test_right_jump_reports_both_populations() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(
        *spikes(populations, {"RIGHT": 6, "JUMP": 6}), 0.0, 50.0
    )
    assert decision.active_actions == ("RIGHT", "JUMP")
    assert decision.primary_action == "RIGHT"


def test_weak_activity_below_threshold_is_neutral() -> None:
    populations = make_populations({"LEFT": 100, "RIGHT": 100, "JUMP": 100})
    decoder = MotorDecoder(populations)
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 10}), 0.0, 50.0
    )
    assert decision.evidence["LEFT"].sufficient
    assert decision.evidence["LEFT"].active_fraction == pytest.approx(0.1)
    assert decision.state == "NEUTRAL"


def test_minimum_active_neurons_gate_blocks_small_evidence() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {"LEFT": 2}), 0.0, 50.0)
    evidence = decision.evidence["LEFT"]
    assert evidence.active_neurons == 2
    assert not evidence.sufficient
    assert "active_neurons_below_minimum" in evidence.reason
    assert decision.scores["LEFT"] == 0.0
    assert decision.state == "NEUTRAL"


def test_minimum_spikes_gate_blocks_sparse_evidence() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(*spikes(populations, {"LEFT": 3}), 0.0, 50.0)
    evidence = decision.evidence["LEFT"]
    assert evidence.spikes == 3
    assert not evidence.sufficient
    assert "spikes_below_minimum" in evidence.reason
    assert decision.state == "NEUTRAL"


def test_uniform_background_activates_all_populations() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 5, "RIGHT": 5, "JUMP": 5}), 0.0, 50.0
    )
    assert decision.active_actions == ("LEFT", "RIGHT", "JUMP")
    assert decision.primary_action == "LEFT"
    assert decision.lateralization == pytest.approx(0.0)


def test_ambiguous_competition_is_resolved_by_priority() -> None:
    decoder, populations = default_decoder()
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 5, "RIGHT": 5}), 0.0, 50.0
    )
    assert decision.scores["LEFT"] == pytest.approx(decision.scores["RIGHT"])
    assert decision.primary_action == "LEFT"

    reverse = MotorDecoder(
        populations, DecoderConfig(priority=("RIGHT", "JUMP", "LEFT"))
    )
    other = reverse.decode_window(
        *spikes(populations, {"LEFT": 5, "RIGHT": 5}), 0.0, 50.0
    )
    assert other.primary_action == "RIGHT"


def test_sparse_noisy_activity_is_neutral() -> None:
    decoder, _ = default_decoder()
    times = np.array([5.0, 10.0, 20.0, 30.0, 40.0])
    indices = np.array([0, 0, 10, 11, 29], dtype=np.int64)
    decision = decoder.decode_window(times, indices, 0.0, 50.0)
    assert decision.state == "NEUTRAL"
    assert decision.evidence["LEFT"].spikes == 2
    assert decision.evidence["RIGHT"].spikes == 2
    assert decision.evidence["JUMP"].spikes == 1


def test_unequal_population_sizes_are_normalised_by_size() -> None:
    populations = make_populations({"LEFT": 3, "RIGHT": 30, "JUMP": 10})
    decoder = MotorDecoder(populations)
    times, indices = spikes(
        populations, {"LEFT": 3, "RIGHT": 6}, repeats=5
    )
    decision = decoder.decode_window(times, indices, 0.0, 50.0)
    assert decision.evidence["LEFT"].spikes == 15
    assert decision.evidence["RIGHT"].spikes == 30
    assert decision.scores["LEFT"] == pytest.approx(1.0)
    assert decision.scores["RIGHT"] == pytest.approx(0.2)
    assert decision.primary_action == "LEFT"


def test_window_is_half_open() -> None:
    decoder, populations = default_decoder()
    members = np.flatnonzero(populations.mask("LEFT"))
    at_start = decoder.decode_window(
        np.zeros(members.size), members, 0.0, 50.0
    )
    assert at_start.state == "LEFT"
    decoder.reset()
    at_end = decoder.decode_window(
        np.full(members.size, 50.0), members, 0.0, 50.0
    )
    assert at_end.state == "NEUTRAL"
    next_window = decoder.decode_window(
        np.full(members.size, 50.0), members, 50.0, 100.0
    )
    assert next_window.state == "LEFT"


def test_repeated_decoding_is_deterministic() -> None:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    times, indices = spikes(
        populations, {"LEFT": 6, "RIGHT": 6, "JUMP": 4}
    )
    first = MotorDecoder(populations).decode_window(times, indices, 0.0, 50.0)
    second = MotorDecoder(populations).decode_window(times, indices, 0.0, 50.0)
    assert isinstance(first, ActionDecision)
    assert first.as_dict() == second.as_dict()


def test_moving_average_smoothing_carries_activity() -> None:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    decoder = MotorDecoder(
        populations,
        DecoderConfig(smoothing="moving_average", smoothing_windows=2),
    )
    times, indices = spikes(populations, {"LEFT": 6}, time_ms=10.0)
    decisions = decoder.decode_series(times, indices, 0.0, 150.0)
    assert [decision.state for decision in decisions] == [
        "LEFT",
        "LEFT",
        "NEUTRAL",
    ]
    assert [round(decision.scores["LEFT"], 6) for decision in decisions] == [
        0.6,
        0.3,
        0.0,
    ]


def test_hysteresis_holds_action_between_release_and_activation() -> None:
    populations = make_populations({"LEFT": 25, "RIGHT": 10, "JUMP": 10})
    decoder = MotorDecoder(populations, DecoderConfig(hysteresis=True))
    decisions = [
        decoder.decode_window(*spikes(populations, {"LEFT": 10}), 0.0, 50.0),
        decoder.decode_window(
            *spikes(populations, {"LEFT": 4}, time_ms=75.0, repeats=2),
            50.0,
            100.0,
        ),
        decoder.decode_window(
            *spikes(populations, {"LEFT": 2}, time_ms=125.0, repeats=3),
            100.0,
            150.0,
        ),
    ]
    assert decisions[0].scores["LEFT"] == pytest.approx(0.4)
    assert decisions[1].scores["LEFT"] == pytest.approx(0.16)
    assert [decision.state for decision in decisions] == [
        "LEFT",
        "LEFT",
        "NEUTRAL",
    ]


def test_hysteresis_without_state_would_release_immediately() -> None:
    populations = make_populations({"LEFT": 25, "RIGHT": 10, "JUMP": 10})
    decoder = MotorDecoder(populations)
    decoder.decode_window(*spikes(populations, {"LEFT": 10}), 0.0, 50.0)
    second = decoder.decode_window(
        *spikes(populations, {"LEFT": 4}, time_ms=75.0, repeats=2), 50.0, 100.0
    )
    assert second.scores["LEFT"] == pytest.approx(0.16)
    assert second.state == "NEUTRAL"


def test_reset_clears_hysteresis_state() -> None:
    populations = make_populations({"LEFT": 25, "RIGHT": 10, "JUMP": 10})
    decoder = MotorDecoder(populations, DecoderConfig(hysteresis=True))
    decoder.decode_window(*spikes(populations, {"LEFT": 10}), 0.0, 50.0)
    decoder.reset()
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 4}, time_ms=75.0, repeats=2), 50.0, 100.0
    )
    assert decision.state == "NEUTRAL"


def test_single_arbitration_reports_only_the_primary_action() -> None:
    decoder, populations = default_decoder(arbitration="single")
    decision = decoder.decode_window(
        *spikes(populations, {"LEFT": 6, "RIGHT": 6}), 0.0, 50.0
    )
    assert decision.active_actions == ("LEFT",)
    assert decision.primary_action == "LEFT"


def test_empty_population_never_activates() -> None:
    populations = make_populations({"LEFT": 0, "RIGHT": 10, "JUMP": 10})
    decoder = MotorDecoder(populations)
    decision = decoder.decode_window(
        *spikes(populations, {"RIGHT": 6}), 0.0, 50.0
    )
    assert decision.evidence["LEFT"].size == 0
    assert decision.evidence["LEFT"].reason == "empty_population"
    assert decision.scores["LEFT"] == 0.0
    assert decision.state == "RIGHT"


def test_lateralization_reports_left_right_balance() -> None:
    decoder, populations = default_decoder()
    left = decoder.decode_window(*spikes(populations, {"LEFT": 10}), 0.0, 50.0)
    assert left.lateralization == pytest.approx(1.0)
    decoder.reset()
    balanced = decoder.decode_window(
        *spikes(populations, {"LEFT": 6, "RIGHT": 6}), 0.0, 50.0
    )
    assert balanced.lateralization == pytest.approx(0.0)
    decoder.reset()
    silent = decoder.decode_window(*spikes(populations, {}), 0.0, 50.0)
    assert silent.lateralization is None


def test_decode_series_handles_partial_windows() -> None:
    decoder, populations = default_decoder()
    times, indices = spikes(populations, {"LEFT": 6}, time_ms=10.0)
    full = decoder.decode_series(times, indices, 0.0, 120.0)
    assert [(item.window_start_ms, item.window_end_ms) for item in full] == [
        (0.0, 50.0),
        (50.0, 100.0),
        (100.0, 120.0),
    ]
    decoder.reset()
    clipped = decoder.decode_series(
        times, indices, 0.0, 120.0, include_partial=False
    )
    assert len(clipped) == 2


def test_decode_recorder_matches_array_input() -> None:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    recorder = SpikeRecorder(populations.n_neurons, max_spikes=100)
    members = np.flatnonzero(populations.mask("LEFT"))[:6]
    recorder.record(9, members, dt_ms=1.0)
    decoder = MotorDecoder(populations)
    from_recorder = decoder.decode_series(
        recorder.spike_times_ms, recorder.spike_neuron_indices, 0.0, 50.0
    )
    decoder.reset()
    direct = decoder.decode_series(
        recorder.spike_times_ms, recorder.spike_neuron_indices, 0.0, 50.0
    )
    assert [item.as_dict() for item in from_recorder] == [
        item.as_dict() for item in direct
    ]
    recorder_decoder = MotorDecoder(populations)
    assert (
        recorder_decoder.decode_recorder(recorder, 0.0, 50.0)[0].state == "LEFT"
    )


def test_decode_recorder_rejects_mismatched_size() -> None:
    populations = make_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    recorder = SpikeRecorder(populations.n_neurons + 1, max_spikes=10)
    with pytest.raises(ValueError, match="neuron count"):
        MotorDecoder(populations).decode_recorder(recorder, 0.0, 50.0)


def test_invalid_spike_arrays_raise() -> None:
    decoder, _ = default_decoder()
    with pytest.raises(ValueError, match="1-D"):
        decoder.decode_window(np.zeros((2, 2)), np.zeros(4, dtype=int), 0, 1)
    with pytest.raises(ValueError, match="differ in length"):
        decoder.decode_window(np.zeros(2), np.zeros(3, dtype=int), 0, 1)
    with pytest.raises(ValueError, match="finite"):
        decoder.decode_window(np.array([np.nan]), np.array([0]), 0, 1)
    with pytest.raises(ValueError, match="negative"):
        decoder.decode_window(np.array([-1.0]), np.array([0]), 0, 1)
    with pytest.raises(ValueError, match="integers"):
        decoder.decode_window(np.array([1.0]), np.array([0.5]), 0, 1)
    with pytest.raises(ValueError, match=r"lie in \[0"):
        decoder.decode_window(np.array([1.0]), np.array([30]), 0, 1)
    with pytest.raises(ValueError, match="window end"):
        decoder.decode_window(np.empty(0), np.empty(0, dtype=int), 5, 5)


def test_invalid_configuration_raises() -> None:
    with pytest.raises(ValueError, match="activation_threshold"):
        DecoderConfig(activation_threshold=0.0)
    with pytest.raises(ValueError, match="release_threshold"):
        DecoderConfig(activation_threshold=0.2, release_threshold=0.5)
    with pytest.raises(ValueError, match="permutation"):
        DecoderConfig(priority=("LEFT", "RIGHT"))
    with pytest.raises(ValueError, match="min_spikes"):
        DecoderConfig(min_spikes=0)
    with pytest.raises(ValueError, match="arbitration"):
        DecoderConfig(arbitration="first")
    with pytest.raises(ValueError, match="smoothing"):
        DecoderConfig(smoothing="median")
    with pytest.raises(ValueError, match="unknown decoder parameters"):
        DecoderConfig.from_config({"window_ms": 50.0, "mystery": 1})


def test_from_config_converts_types() -> None:
    config = DecoderConfig.from_config(
        {
            "window_ms": 25,
            "priority": ["JUMP", "RIGHT", "LEFT"],
            "min_spikes": 2,
            "hysteresis": 1,
        }
    )
    assert config.window_ms == 25.0
    assert config.priority == ("JUMP", "RIGHT", "LEFT")
    assert config.min_spikes == 2
    assert config.hysteresis is True


def test_describe_reports_signal_and_sizes() -> None:
    decoder, populations = default_decoder()
    description = decoder.describe()
    assert description["decision_signal"] == "active_fraction"
    assert description["window_semantics"] == "[start_ms, end_ms)"
    assert description["populations"] == populations.sizes
    assert description["config"]["priority"] == ["LEFT", "RIGHT", "JUMP"]
