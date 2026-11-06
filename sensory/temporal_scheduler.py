"""Phase 3C: schedule tracked visual state and lifecycle events as current.

``TemporalActivationScheduler`` is an ``input_schedule`` for
``BrainSimulator`` exactly like ``SensoryInputScheduler``: it only adds
current to a preallocated array and never overwrites unrelated input. It
consumes ``TemporalFrame`` records produced by ``TemporalSequenceProcessor``,
not screenshots or detections, so perception and connectome dynamics stay
separate.

Two drive components are added:

* a **sample-and-hold** component: the encoded ``GameState`` of the most
  recent frame at or before the simulation time. Frames are timestamped, so
  irregular intervals and dropped frames do not shift the schedule. When the
  newest frame is older than ``max_hold_ms``, holding stops; no state is
  extrapolated.
* **event pulses**: lifecycle events that carry values for existing feature
  names (appearance, approach, recede) are encoded with the same encoders and
  added with a gain and linear decay. They are extra drive for those
  populations, not a second encoder and not an action.

No action is selected here. Novel scheduler parameters are versioned in
``TemporalSchedulerConfig`` and do not alter the Phase 3A.5 baseline.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, fields

import numpy as np

from perception.temporal import LifecycleEvent, TemporalFrame
from sensory.population_encoder import encode_state


def _finite_non_negative(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


@dataclass(frozen=True)
class TemporalSchedulerConfig:
    """Versioned Phase 3C scheduler parameters; independent of Phase 3A.5."""

    version: str = "phase_3c_temporal_scheduler_v1"
    max_hold_ms: float = 250.0
    pulse_gain: float = 0.5
    pulse_decay_ms: float = 150.0

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be a non-empty string")
        hold = _finite_non_negative(self.max_hold_ms, "max_hold_ms")
        if hold <= 0:
            raise ValueError("max_hold_ms must be positive")
        gain = _finite_non_negative(self.pulse_gain, "pulse_gain")
        if gain > 1.0:
            raise ValueError("pulse_gain must be at most 1.0")
        decay = _finite_non_negative(self.pulse_decay_ms, "pulse_decay_ms")
        if decay <= 0:
            raise ValueError("pulse_decay_ms must be positive")

    def as_dict(self) -> dict:
        return {item.name: getattr(self, item.name) for item in fields(self)}


class TemporalActivationScheduler:
    """Deterministic time-varying current injection from temporal frames."""

    def __init__(
        self,
        mapping,
        encoders: dict,
        frames,
        *,
        current_pa: dict[str, float],
        config: TemporalSchedulerConfig | None = None,
        active_features=None,
    ) -> None:
        if not isinstance(frames, (list, tuple)) or not frames:
            raise ValueError("frames must be a non-empty list of TemporalFrame")
        self.config = config or TemporalSchedulerConfig()
        if not isinstance(self.config, TemporalSchedulerConfig):
            raise ValueError("config must be a TemporalSchedulerConfig")
        self.mapping = mapping
        self.encoders = encoders

        self.frames = list(frames)
        starts: list[float] = []
        for frame in self.frames:
            if not isinstance(frame, TemporalFrame):
                raise ValueError("frames must contain TemporalFrame instances")
            start = _finite_non_negative(frame.time_ms, "frame time_ms")
            if starts and start <= starts[-1]:
                raise ValueError("frame times must increase strictly")
            starts.append(start)

        if not set(encoders) <= set(mapping.populations):
            missing = sorted(set(encoders) - set(mapping.populations))
            raise ValueError(f"mapping is missing features {missing}")

        self._current_pa: dict[str, float] = {}
        for feature in encoders:
            value = current_pa.get(feature, 0.0)
            self._current_pa[feature] = _finite_non_negative(
                value, f"current_pa[{feature!r}]"
            )

        if active_features is None:
            self.active_features = list(encoders)
        else:
            unknown = set(active_features) - set(encoders)
            if unknown:
                raise ValueError(f"unknown active features {sorted(unknown)}")
            self.active_features = [
                feature for feature in encoders if feature in set(active_features)
            ]
        if not self.active_features:
            raise ValueError("at least one feature must be active")
        active = set(self.active_features)

        self._indices = np.concatenate(
            [mapping.indices(feature) for feature in encoders]
        )
        self._slices: dict[str, slice] = {}
        offset = 0
        for feature in encoders:
            size = mapping.size(feature)
            self._slices[feature] = slice(offset, offset + size)
            offset += size
        self._stimulated_indices = np.unique(
            np.concatenate(
                [mapping.indices(feature) for feature in self.active_features]
            )
        )

        self._frame_times = np.asarray(starts, dtype=np.float64)
        self._frame_values: list[np.ndarray] = []
        for frame in self.frames:
            encoded = encode_state(frame.state.features(), encoders)
            values = np.zeros(self._indices.size, dtype=np.float64)
            for feature in encoders:
                response = np.asarray(encoded[feature], dtype=np.float64)
                if response.size != mapping.size(feature):
                    raise ValueError(
                        f"encoder {feature!r} returns {response.size} values but "
                        f"the mapping has {mapping.size(feature)} neurons"
                    )
                if feature in active:
                    values[self._slices[feature]] = (
                        response * self._current_pa[feature]
                    )
            self._frame_values.append(values)

        pulse_events: list[LifecycleEvent] = []
        for frame in self.frames:
            for event in frame.events:
                if not isinstance(event, LifecycleEvent):
                    raise ValueError(
                        "frame events must be LifecycleEvent instances"
                    )
                if not event.is_pulse:
                    continue
                if not event.feature_values:
                    raise ValueError(
                        "a pulse event must carry at least one feature value"
                    )
                pulse_events.append(event)
        pulse_events.sort(
            key=lambda item: (
                item.time_ms,
                item.frame_index,
                item.track_id,
                item.event.value,
            )
        )
        self._pulse_events = tuple(pulse_events)
        self._pulse_onsets = np.asarray(
            [event.time_ms for event in pulse_events], dtype=np.float64
        )
        self._pulse_values: list[np.ndarray] = [
            self._pulse_drive(event, active) for event in pulse_events
        ]

    def _pulse_drive(self, event: LifecycleEvent, active: set[str]) -> np.ndarray:
        unknown = set(event.feature_values) - set(self.encoders)
        if unknown:
            raise ValueError(
                f"pulse event references unknown features {sorted(unknown)}"
            )
        features = {
            feature: value
            for feature, value in event.feature_values.items()
            if feature in active
        }
        values = np.zeros(self._indices.size, dtype=np.float64)
        if not features:
            return values
        encoded = encode_state(
            features, {name: self.encoders[name] for name in features}
        )
        for feature in features:
            response = np.asarray(encoded[feature], dtype=np.float64)
            values[self._slices[feature]] = (
                response
                * self._current_pa[feature]
                * self.config.pulse_gain
            )
        return values

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._stimulated_indices

    @property
    def horizon_ms(self) -> float:
        """Last scheduled frame plus the maximum hold window."""
        return float(self._frame_times[-1] + self.config.max_hold_ms)

    @property
    def memory_bytes(self) -> int:
        return int(
            self._indices.nbytes
            + self._frame_times.nbytes
            + sum(values.nbytes for values in self._frame_values)
            + self._pulse_onsets.nbytes
            + sum(values.nbytes for values in self._pulse_values)
        )

    def _add_at(self, time_ms: float, target: np.ndarray) -> None:
        index = int(np.searchsorted(self._frame_times, time_ms, side="right")) - 1
        if index < 0:
            return
        if time_ms - float(self._frame_times[index]) > self.config.max_hold_ms:
            return
        target[self._indices] += self._frame_values[index]

        decay = self.config.pulse_decay_ms
        first = bisect.bisect_left(self._pulse_onsets, time_ms - decay)
        for position in range(first, len(self._pulse_onsets)):
            onset = float(self._pulse_onsets[position])
            if onset > time_ms:
                break
            remaining = 1.0 - (time_ms - onset) / decay
            if remaining <= 0.0:
                continue
            target[self._indices] += self._pulse_values[position] * remaining

    def apply(self, step: int, time_ms: float, current_pa: np.ndarray) -> None:
        """Add this step's temporal input; never overwrite unrelated input."""
        self._add_at(float(time_ms), current_pa)

    def feature_currents_at(self, time_ms: float) -> dict[str, float]:
        """Total scheduled current per feature at a time (pA)."""
        # Indices are global neuron indices, so the temporary buffer spans
        # the whole range even though only mapped neurons receive drive.
        values = np.zeros(int(self._indices.max()) + 1, dtype=np.float64)
        self._add_at(float(time_ms), values)
        return {
            feature: float(
                values[self._indices[self._slices[feature]]].sum()
            )
            for feature in self.encoders
        }

    def input_statistics(self) -> dict:
        frame_peak = {feature: 0.0 for feature in self.encoders}
        for values in self._frame_values:
            for feature in self.encoders:
                frame_peak[feature] = max(
                    frame_peak[feature],
                    float(values[self._slices[feature]].sum()),
                )
        pulse_peak = {feature: 0.0 for feature in self.encoders}
        for event, values in zip(self._pulse_events, self._pulse_values):
            for feature in event.feature_values:
                if feature not in self.encoders:
                    continue
                pulse_peak[feature] = max(
                    pulse_peak[feature],
                    float(values[self._slices[feature]].sum()),
                )
        per_neuron_peak = max(
            (
                float(values.max())
                for values in (*self._frame_values, *self._pulse_values)
            ),
            default=0.0,
        )
        return {
            "max_frame_current_pa": round(sum(frame_peak.values()), 6),
            "max_pulse_current_pa": round(sum(pulse_peak.values()), 6),
            "max_per_neuron_current_pa": round(per_neuron_peak, 6),
            "peak_frame_feature_current_pa": {
                feature: round(value, 6)
                for feature, value in frame_peak.items()
            },
            "peak_pulse_feature_current_pa": {
                feature: round(value, 6)
                for feature, value in pulse_peak.items()
            },
            "n_frames": len(self.frames),
            "n_pulse_events": len(self._pulse_events),
            "active_features": list(self.active_features),
            "n_active_features": len(self.active_features),
        }

    def signature(self) -> dict:
        """Small deterministic representation used by reproducibility checks."""
        return {
            "indices": self._indices.astype(np.int64),
            "frame_values": np.stack(self._frame_values),
            "frame_times": self._frame_times,
            "pulse_values": (
                np.stack(self._pulse_values)
                if self._pulse_values
                else np.zeros((0, self._indices.size), dtype=np.float64)
            ),
            "pulse_onsets": self._pulse_onsets,
        }

    def describe(self) -> dict:
        populations = {}
        for feature in self.encoders:
            population = self.mapping.populations[feature]
            populations[feature] = {
                "n_neurons": int(population.size()),
                "current_pa": self._current_pa[feature],
            }
        return {
            "kind": "temporal_sensory_schedule",
            "version": self.config.version,
            "config": self.config.as_dict(),
            "n_frames": len(self.frames),
            "first_frame_ms": float(self._frame_times[0]),
            "last_frame_ms": float(self._frame_times[-1]),
            "horizon_ms": self.horizon_ms,
            "n_pulse_events": len(self._pulse_events),
            "pulse_events_by_kind": {
                kind: sum(
                    1 for event in self._pulse_events if event.event.value == kind
                )
                for kind in sorted(
                    {event.event.value for event in self._pulse_events}
                )
            },
            "n_features": len(self.encoders),
            "active_features": list(self.active_features),
            "n_stimulated_neurons": int(self.stimulated_indices.size),
            "features": populations,
            "policy": {
                "frame_holding": (
                    "sample-and-hold of the newest frame at or before the "
                    "simulation time"
                ),
                "stale_frames": (
                    "no drive after max_hold_ms without a new frame; no state "
                    "is extrapolated"
                ),
                "pulses": (
                    "pulse events add encoded feature drive with gain "
                    "pulse_gain and linear decay over pulse_decay_ms"
                ),
                "intervals": (
                    "absolute frame timestamps are used; irregular intervals "
                    "and dropped frames do not shift the schedule"
                ),
            },
            "limitations": [
                "The held state is the last observed frame, not a prediction.",
                "Pulses are extra input drive, not evidence of a biological "
                "event code.",
                "Perception frames are not validated here; upstream perception "
                "and tracking own that contract.",
                "No action is selected; BrainSimulator remains the only "
                "source of neural dynamics.",
            ],
        }
