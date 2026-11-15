"""Focused tests for the Phase 4G.3 decoder-activity adapter."""

from __future__ import annotations

import numpy as np
import pytest

from brain.banc_simulation_adapter import BancActivityAdapter, SpikeWindow
from brain.neural_activity import SpikeRecorder
from motor.motor_decoder import DecoderConfig, MotorDecoder
from motor.populations import ACTION_POPULATIONS, MotorPopulations


def make_populations(n_neurons: int, masks: dict[str, list[int]]) -> MotorPopulations:
    arrays = {}
    for action in ACTION_POPULATIONS:
        mask = np.zeros(n_neurons, dtype=bool)
        mask[masks.get(action, [])] = True
        arrays[action] = mask
    motor = np.zeros(n_neurons, dtype=bool)
    for mask in arrays.values():
        motor |= mask
    return MotorPopulations(
        n_neurons=n_neurons,
        threshold=5,
        masks=arrays,
        motor_mask=motor,
        unassigned_mask=np.zeros(n_neurons, dtype=bool),
        composition={},
        provenance={},
    )


def make_recorder() -> SpikeRecorder:
    recorder = SpikeRecorder(n_neurons=4, max_spikes=100)
    recorder.record(0, np.array([0], dtype=np.int32), dt_ms=0.5)
    recorder.record(1, np.array([1, 2], dtype=np.int32), dt_ms=0.5)
    recorder.record(5, np.array([3], dtype=np.int32), dt_ms=0.5)
    return recorder


def test_adapter_requires_matching_neuron_counts():
    recorder = make_recorder()
    with pytest.raises(ValueError):
        BancActivityAdapter(recorder, make_populations(5, {}))
    with pytest.raises(ValueError):
        BancActivityAdapter(None, make_populations(4, {}))


def test_adapter_exposes_the_unchanged_spike_arrays():
    recorder = make_recorder()
    adapter = BancActivityAdapter(
        recorder, make_populations(4, {"LEFT": [0, 1]}), graph_threshold=5
    )
    assert np.shares_memory(adapter.spike_times_ms, recorder.spike_times_ms)
    assert np.shares_memory(
        adapter.spike_neuron_indices, recorder.spike_neuron_indices
    )
    assert np.array_equal(adapter.spike_times_ms, recorder.spike_times_ms)
    assert adapter.n_neurons == 4
    assert adapter.n_spikes == 4
    assert adapter.graph_threshold == 5
    assert adapter.population_threshold == 5


def test_window_is_half_open_and_matches_spikes():
    adapter = BancActivityAdapter(make_recorder(), make_populations(4, {}))
    window = adapter.window(0.5, 3.0)
    assert isinstance(window, SpikeWindow)
    assert list(window.times_ms) == [0.5, 1.0, 1.0]
    assert list(window.neuron_indices) == [0, 1, 2]
    assert window.duration_ms == pytest.approx(2.5)
    with pytest.raises(ValueError):
        adapter.window(3.0, 3.0)


def test_adapter_decode_matches_direct_decoder_call():
    recorder = make_recorder()
    populations = make_populations(4, {"LEFT": [0, 1], "RIGHT": [2], "JUMP": [3]})
    adapter = BancActivityAdapter(recorder, populations)
    config = DecoderConfig(min_active_neurons=1, min_spikes=1)
    decoder = MotorDecoder(populations, config)
    direct = decoder.decode_recorder(recorder, 0.0, 2.0)
    through_adapter = adapter.decode(MotorDecoder(populations, config), 0.0, 2.0)
    assert [item.as_dict() for item in direct] == [
        item.as_dict() for item in through_adapter
    ]
    assert through_adapter[0].primary_action == "LEFT"


def test_population_activity_matches_recorded_spikes():
    recorder = make_recorder()
    populations = make_populations(
        4, {"LEFT": [0, 1], "RIGHT": [2], "JUMP": [3]}
    )
    adapter = BancActivityAdapter(recorder, populations)
    activity = adapter.population_activity(0.0, 2.0)
    assert activity["n_spikes"] == 3
    left = activity["populations"]["LEFT"]
    assert left["size"] == 2
    assert left["spikes"] == 2
    assert left["active_neurons"] == 2
    assert left["active_fraction"] == 1.0
    assert left["mean_rate_hz"] == pytest.approx(500.0)
    assert activity["populations"]["RIGHT"]["active_fraction"] == 1.0
    assert activity["populations"]["JUMP"]["spikes"] == 0
    assert activity["network"]["spikes"] == 3
    assert activity["motor"]["spikes"] == 3


def test_empty_populations_produce_neutral_decisions():
    recorder = make_recorder()
    populations = make_populations(4, {})
    adapter = BancActivityAdapter(recorder, populations)
    activity = adapter.population_activity(0.0, 10.0)
    for action in ACTION_POPULATIONS:
        assert activity["populations"][action]["size"] == 0
        assert activity["populations"][action]["active_fraction"] == 0.0
        assert activity["populations"][action]["mean_rate_hz"] == 0.0
    decisions = adapter.decode(
        MotorDecoder(populations, DecoderConfig(min_active_neurons=1, min_spikes=1)),
        0.0,
        10.0,
    )
    assert decisions
    assert all(decision.neutral for decision in decisions)


def test_adapter_rejects_a_decoder_for_another_population_size():
    adapter = BancActivityAdapter(make_recorder(), make_populations(4, {}))
    other = MotorDecoder(make_populations(6, {}))
    with pytest.raises(ValueError):
        adapter.decode(other, 0.0, 1.0)


def test_empty_recording_decodes_to_neutral():
    recorder = SpikeRecorder(n_neurons=4, max_spikes=10)
    populations = make_populations(4, {"LEFT": [0]})
    adapter = BancActivityAdapter(recorder, populations)
    decisions = adapter.decode(
        MotorDecoder(populations, DecoderConfig(min_active_neurons=1, min_spikes=1)),
        0.0,
        5.0,
    )
    assert decisions
    assert all(decision.neutral for decision in decisions)
    assert adapter.population_activity(0.0, 5.0)["n_spikes"] == 0
