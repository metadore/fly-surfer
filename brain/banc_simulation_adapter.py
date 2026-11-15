"""Adapter between BANC simulation output and the Phase 4F motor decoder.

The BANC simulator records spikes into the same
:class:`brain.neural_activity.SpikeRecorder` used by the FAFB pathway, with one
entry per graph node. The Phase 4F decoder reads exactly ``n_neurons``,
``spike_times_ms`` and ``spike_neuron_indices``, so no spike event or timestamp
is transformed here.

The adapter adds three things:

* a check that the recording and the population masks cover the same nodes;
* a window view for descriptive per-population metrics (explicitly a filtered
  copy, never fed to the decoder);
* a ``decode`` method that hands the unchanged recorder to the existing
  :class:`motor.motor_decoder.MotorDecoder`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from motor.populations import ACTION_POPULATIONS, MotorPopulations


@dataclass(frozen=True)
class SpikeWindow:
    """Spikes inside ``[start_ms, end_ms)`` for descriptive analysis."""

    times_ms: np.ndarray
    neuron_indices: np.ndarray
    n_neurons: int
    start_ms: float
    end_ms: float

    @property
    def n_spikes(self) -> int:
        return int(len(self.times_ms))

    @property
    def duration_ms(self) -> float:
        return float(self.end_ms - self.start_ms)


class BancActivityAdapter:
    """Read-only view over BANC spikes sized for the Phase 4F decoder."""

    def __init__(
        self,
        recorder,
        populations: MotorPopulations,
        graph_threshold: int | None = None,
    ) -> None:
        if recorder is None:
            raise ValueError("recorder is required")
        if int(getattr(recorder, "n_neurons", -1)) != int(populations.n_neurons):
            raise ValueError(
                "recorder neuron count does not match the motor populations"
            )
        self.recorder = recorder
        self.populations = populations
        self.graph_threshold = (
            None if graph_threshold is None else int(graph_threshold)
        )
        self.population_threshold = int(populations.threshold)

    @property
    def n_neurons(self) -> int:
        return int(self.recorder.n_neurons)

    @property
    def n_spikes(self) -> int:
        return int(len(self.recorder.spike_times_ms))

    @property
    def spike_times_ms(self) -> np.ndarray:
        """Exact array stored by the simulator; no copy or shift."""
        return self.recorder.spike_times_ms

    @property
    def spike_neuron_indices(self) -> np.ndarray:
        """Exact array stored by the simulator; no copy or shift."""
        return self.recorder.spike_neuron_indices

    def window(self, start_ms: float, end_ms: float) -> SpikeWindow:
        start = float(start_ms)
        end = float(end_ms)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            raise ValueError("window end must be a finite time after its start")
        times = self.recorder.spike_times_ms
        indices = self.recorder.spike_neuron_indices
        mask = (times >= start) & (times < end)
        return SpikeWindow(
            times_ms=times[mask],
            neuron_indices=indices[mask],
            n_neurons=self.n_neurons,
            start_ms=start,
            end_ms=end,
        )

    def decode(self, decoder, start_ms: float, end_ms: float, **kwargs):
        """Decode with the existing decoder on the unchanged recorder."""
        if int(getattr(decoder, "n_neurons", -1)) != self.n_neurons:
            raise ValueError(
                "decoder neuron count does not match the BANC recording"
            )
        return decoder.decode_recorder(
            self.recorder, start_ms, end_ms, **kwargs
        )

    def population_activity(
        self, start_ms: float, end_ms: float
    ) -> dict:
        """Descriptive activity per action population and for the network.

        Uses the same half-open window as the decoder. These values are
        descriptive only; the decoder computes its own evidence internally.
        """
        window = self.window(start_ms, end_ms)
        duration_s = window.duration_ms / 1000.0
        indices = window.neuron_indices
        counts = np.bincount(indices, minlength=self.n_neurons)

        def block(mask: np.ndarray, size: int) -> dict:
            spikes = int(counts[mask].sum())
            active = int(np.count_nonzero(counts[mask]))
            return {
                "size": int(size),
                "spikes": spikes,
                "active_neurons": active,
                "active_fraction": round(
                    active / size, 6) if size else 0.0,
                "mean_rate_hz": round(
                    spikes / size / duration_s, 4) if size else 0.0,
                "spike_share": round(
                    spikes / max(1, window.n_spikes), 6),
            }

        populations = {
            action: block(
                np.asarray(self.populations.mask(action), dtype=bool),
                self.populations.sizes[action],
            )
            for action in ACTION_POPULATIONS
        }
        motor_mask = np.asarray(self.populations.motor_mask, dtype=bool)
        unassigned_mask = np.asarray(
            self.populations.unassigned_mask, dtype=bool
        )
        return {
            "window_start_ms": window.start_ms,
            "window_end_ms": window.end_ms,
            "n_spikes": window.n_spikes,
            "populations": populations,
            "motor": block(motor_mask, int(motor_mask.sum())),
            "unassigned_motor": block(
                unassigned_mask, int(unassigned_mask.sum())
            ),
            "network": block(
                np.ones(self.n_neurons, dtype=bool), self.n_neurons
            ),
        }
