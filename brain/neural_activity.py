"""Spike recording, firing-rate summaries and activity plots.

Only spike times and neuron indices are stored. Membrane traces are not
retained, which keeps memory bounded by the configured spike capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


class SpikeCapacityExceeded(RuntimeError):
    """Raised instead of silently dropping spikes when the buffer is full."""


class SpikeRecorder:
    """Preallocated spike-time recorder."""

    def __init__(self, n_neurons: int, max_spikes: int = 2_000_000) -> None:
        if n_neurons < 1:
            raise ValueError("n_neurons must be positive")
        if max_spikes < 1:
            raise ValueError("max_spikes must be positive")
        self.n_neurons = int(n_neurons)
        self.capacity = int(max_spikes)
        self._times = np.empty(self.capacity, dtype=np.float32)
        self._neurons = np.empty(self.capacity, dtype=np.int32)
        self._count = 0

    @property
    def n_spikes(self) -> int:
        return self._count

    @property
    def memory_bytes(self) -> int:
        """Bytes held by the preallocated spike buffers."""
        return int(self._times.nbytes + self._neurons.nbytes)

    @staticmethod
    def capacity_bytes(max_spikes: int) -> int:
        """Bytes needed by a recorder with ``max_spikes`` capacity."""
        return int(max_spikes) * (np.dtype(np.float32).itemsize
                                  + np.dtype(np.int32).itemsize)

    @property
    def spike_times_ms(self) -> np.ndarray:
        return self._times[: self._count]

    @property
    def spike_neuron_indices(self) -> np.ndarray:
        return self._neurons[: self._count]

    def reset(self) -> None:
        self._count = 0

    def record(
        self, step_index: int, spike_indices: np.ndarray, dt_ms: float
    ) -> None:
        count = len(spike_indices)
        if count == 0:
            return
        if self._count + count > self.capacity:
            raise SpikeCapacityExceeded(
                f"spike capacity {self.capacity:,} exceeded at step "
                f"{step_index}; increase max_recorded_spikes"
            )
        stop = self._count + count
        self._times[self._count : stop] = (step_index + 1) * dt_ms
        self._neurons[self._count : stop] = spike_indices
        self._count = stop

    def spike_counts(self) -> np.ndarray:
        return np.bincount(
            self._neurons[: self._count], minlength=self.n_neurons
        ).astype(np.int64)

    def firing_rates(self, duration_ms: float) -> np.ndarray:
        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        return self.spike_counts() / (duration_ms / 1000.0)

    def population_rate(
        self, duration_ms: float, bin_ms: float = 10.0
    ) -> tuple[np.ndarray, np.ndarray]:
        if duration_ms <= 0 or bin_ms <= 0:
            raise ValueError("duration_ms and bin_ms must be positive")
        edges = np.arange(0.0, duration_ms + bin_ms, bin_ms, dtype=np.float64)
        if edges[-1] < duration_ms:
            edges = np.append(edges, duration_ms)
        counts, _ = np.histogram(
            self._times[: self._count], bins=edges
        )
        widths_s = np.diff(edges) / 1000.0
        rates = counts / (self.n_neurons * widths_s)
        return edges, rates

    def summary(self, duration_ms: float, bin_ms: float = 10.0) -> dict:
        counts = self.spike_counts()
        rates = counts / (duration_ms / 1000.0)
        active = int(np.count_nonzero(counts))
        _, population = self.population_rate(duration_ms, bin_ms)
        if self._count:
            percentiles = {
                str(p): round(float(np.percentile(rates, p)), 4)
                for p in (50, 90, 95, 99, 100)
            }
        else:
            percentiles = {str(p): 0.0 for p in (50, 90, 95, 99, 100)}
        return {
            "duration_ms": float(duration_ms),
            "n_neurons": self.n_neurons,
            "n_spikes": int(self._count),
            "active_neurons": active,
            "silent_neurons": int(self.n_neurons - active),
            "active_fraction": round(active / self.n_neurons, 6),
            "mean_rate_hz": round(float(rates.mean()), 4),
            "rate_percentiles_hz": percentiles,
            "population_rate_hz": round(float(population.mean()), 4),
            "population_rate_peak_hz": round(float(population.max()), 4),
            "spike_capacity": self.capacity,
        }

    def raster_data(
        self, max_points: int | None = None
    ) -> tuple[np.ndarray, np.ndarray, int]:
        total = self._count
        if max_points is not None and total > max_points > 0:
            index = np.linspace(0, total - 1, max_points).astype(np.int64)
            return self._times[index], self._neurons[index], total
        return self.spike_times_ms, self.spike_neuron_indices, total

    def save(self, path: Path, duration_ms: float) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            spike_times_ms=self.spike_times_ms,
            spike_neuron_indices=self.spike_neuron_indices,
            n_neurons=np.int64(self.n_neurons),
            duration_ms=np.float64(duration_ms),
            capacity=np.int64(self.capacity),
        )

def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_raster(
    recorder: SpikeRecorder,
    path: Path,
    duration_ms: float,
    max_points: int = 300_000,
    dpi: int = 150,
    title: str | None = None,
) -> Path:
    """Write a raster plot; deterministic subsampling keeps the figure small."""
    plt = _pyplot()
    times, neurons, total = recorder.raster_data(max_points)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(12, 5.5))
    if total:
        axis.scatter(
            times,
            neurons,
            s=1,
            marker=".",
            alpha=0.55,
            linewidths=0,
            color="#1f4e79",
            rasterized=True,
        )
        shown = "all" if len(times) == total else f"{len(times):,} sampled"
        axis.set_title(
            f"{title or 'FAFB spiking simulation'} — {total:,} spikes ({shown})"
        )
    else:
        axis.text(
            0.5, 0.5, "No spikes in this run", ha="center", va="center",
            transform=axis.transAxes, fontsize=14,
        )
        axis.set_title(title or "FAFB spiking simulation")
    axis.set_xlim(0, duration_ms)
    axis.set_xlabel("Time (ms)")
    axis.set_ylabel("Neuron index (subgraph)")
    axis.grid(alpha=0.2, linewidth=0.4)
    figure.tight_layout()
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return path


def plot_firing_rates(
    recorder: SpikeRecorder,
    path: Path,
    duration_ms: float,
    bin_ms: float = 10.0,
    dpi: int = 150,
    title: str | None = None,
) -> Path:
    """Write a firing-rate distribution and population-rate time series."""
    plt = _pyplot()
    rates = recorder.firing_rates(duration_ms)
    edges, population = recorder.population_rate(duration_ms, bin_ms)
    centers = edges[:-1] + np.diff(edges) / 2.0
    mean_rate = float(rates.mean())

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, (distribution, timeline) = plt.subplots(
        2, 1, figsize=(12, 7.5), gridspec_kw={"height_ratios": [1.1, 1.0]}
    )

    upper = float(rates.max()) if rates.max() > 0 else 1.0
    bins = np.linspace(0.0, upper, 50) if rates.max() > 0 else 10
    distribution.hist(
        rates, bins=bins, color="#2e75b6", edgecolor="white", linewidth=0.3
    )
    distribution.axvline(
        mean_rate, color="#c00000", linewidth=1.2,
        label=f"population mean {mean_rate:.2f} Hz",
    )
    distribution.set_xlabel("Firing rate (Hz)")
    distribution.set_ylabel("Neuron count")
    distribution.set_title("Per-neuron firing-rate distribution")
    distribution.legend(frameon=False)
    if recorder.n_spikes:
        distribution.set_yscale("log")
    distribution.grid(alpha=0.2, linewidth=0.4)

    timeline.plot(centers, population, color="#1f4e79", linewidth=1.2)
    timeline.set_xlim(0, duration_ms)
    timeline.set_xlabel("Time (ms)")
    timeline.set_ylabel("Population rate (Hz)")
    timeline.set_title(f"Population rate, {bin_ms:g} ms bins")
    timeline.grid(alpha=0.2, linewidth=0.4)

    figure.suptitle(title or "FAFB spiking simulation activity", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return path
