"""Spike recording, firing-rate summaries, raster data and plots."""

from __future__ import annotations

import numpy as np
import pytest

from brain.neural_activity import (
    SpikeCapacityExceeded,
    SpikeRecorder,
    plot_firing_rates,
    plot_raster,
)


def test_recording_stores_time_and_neuron_index() -> None:
    recorder = SpikeRecorder(3, max_spikes=10)
    recorder.record(0, np.array([0, 2], dtype=np.int32), dt_ms=0.5)
    recorder.record(2, np.array([1], dtype=np.int32), dt_ms=0.5)
    assert recorder.n_spikes == 3
    assert recorder.spike_times_ms.tolist() == [0.5, 0.5, 1.5]
    assert recorder.spike_neuron_indices.tolist() == [0, 2, 1]
    assert recorder.spike_counts().tolist() == [1, 1, 1]
    assert recorder.firing_rates(1000.0).tolist() == pytest.approx([1.0, 1.0, 1.0])


def test_capacity_is_enforced_without_partial_write() -> None:
    recorder = SpikeRecorder(2, max_spikes=2)
    recorder.record(0, np.array([0, 1], dtype=np.int32), 0.5)
    with pytest.raises(SpikeCapacityExceeded):
        recorder.record(1, np.array([0], dtype=np.int32), 0.5)
    assert recorder.n_spikes == 2


def test_raster_subsampling_is_deterministic() -> None:
    recorder = SpikeRecorder(4, max_spikes=100)
    spikes = np.arange(10, dtype=np.int32) % 4
    recorder.record(0, spikes, 1.0)
    first = recorder.raster_data(max_points=5)
    second = recorder.raster_data(max_points=5)
    assert len(first[0]) == 5
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    assert first[2] == 10


def test_summary_counts_active_and_silent_neurons() -> None:
    recorder = SpikeRecorder(3, max_spikes=10)
    recorder.record(0, np.array([0], dtype=np.int32), 0.5)
    recorder.record(1, np.array([0], dtype=np.int32), 0.5)
    recorder.record(2, np.array([2], dtype=np.int32), 0.5)
    summary = recorder.summary(1000.0)
    assert summary["n_neurons"] == 3
    assert summary["n_spikes"] == 3
    assert summary["active_neurons"] == 2
    assert summary["silent_neurons"] == 1
    assert summary["active_fraction"] == pytest.approx(2 / 3, abs=1e-6)
    assert summary["mean_rate_hz"] == pytest.approx(1.0)
    assert summary["rate_percentiles_hz"]["100"] == pytest.approx(2.0)


def test_empty_summary_is_well_defined() -> None:
    summary = SpikeRecorder(4, max_spikes=10).summary(500.0)
    assert summary["n_spikes"] == 0
    assert summary["active_neurons"] == 0
    assert summary["active_fraction"] == 0.0
    assert summary["mean_rate_hz"] == 0.0
    assert summary["population_rate_peak_hz"] == 0.0


def test_population_rate_preserves_spike_total() -> None:
    recorder = SpikeRecorder(2, max_spikes=20)
    recorder.record(0, np.array([0, 1], dtype=np.int32), 1.0)
    recorder.record(9, np.array([0], dtype=np.int32), 1.0)
    edges, rates = recorder.population_rate(10.0, bin_ms=1.0)
    assert edges[0] == 0.0
    assert edges[-1] == pytest.approx(10.0)
    assert rates.size == edges.size - 1
    assert np.count_nonzero(rates) == 2
    # Two neurons in a 1 ms bin is 1000 Hz across the population.
    assert rates.max() == pytest.approx(1000.0)


def test_memory_accounting_is_capacity_based() -> None:
    recorder = SpikeRecorder(20, max_spikes=100)
    recorder.record(0, np.array([1, 2], dtype=np.int32), 0.5)
    assert recorder.memory_bytes == 100 * (4 + 4)
    assert recorder.memory_bytes == SpikeRecorder.capacity_bytes(100)
    assert SpikeRecorder.capacity_bytes(10) == 80


def test_save_round_trip(tmp_path) -> None:
    recorder = SpikeRecorder(3, max_spikes=10)
    recorder.record(0, np.array([0, 2], dtype=np.int32), 0.5)
    path = tmp_path / "activity.npz"
    recorder.save(path, duration_ms=1000.0)
    with np.load(path) as data:
        assert data["spike_times_ms"].tolist() == [0.5, 0.5]
        assert data["spike_neuron_indices"].tolist() == [0, 2]
        assert int(data["n_neurons"]) == 3
        assert float(data["duration_ms"]) == pytest.approx(1000.0)
        assert int(data["capacity"]) == 10


def test_plots_are_written_for_spiking_and_silent_runs(tmp_path) -> None:
    recorder = SpikeRecorder(5, max_spikes=100)
    times = np.arange(5, dtype=np.int32)
    for step in range(5):
        recorder.record(step, times, 1.0)
    raster = plot_raster(recorder, tmp_path / "raster.png", 10.0, max_points=5)
    rates = plot_firing_rates(
        recorder, tmp_path / "rates.png", 10.0, bin_ms=1.0
    )
    assert raster.stat().st_size > 0
    assert rates.stat().st_size > 0

    silent = SpikeRecorder(5, max_spikes=10)
    silent_raster = plot_raster(silent, tmp_path / "silent_raster.png", 10.0)
    assert silent_raster.stat().st_size > 0
