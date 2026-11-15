"""Deterministic decoder from motor-pool activity to abstract action signals.

The decoder consumes spike times and graph node indices, which is exactly what
``brain.neural_activity.SpikeRecorder`` stores, so it can read any existing
simulation result without changing the simulator.

Decision signal
    The decision score of a population is its *active neuron fraction* inside
    a fixed window: the number of population neurons that emitted at least one
    spike divided by the population size. It is bounded in [0, 1] and cannot
    grow with population size, so a larger pool does not win merely because it
    contains more neurons. Spike count and mean firing rate are reported as
    descriptive evidence, not used for arbitration.

Evidence gate
    A population can only be active if it produced at least ``min_spikes``
    spikes and at least ``min_active_neurons`` active neurons. A population
    below the gate scores zero regardless of its active fraction, which stops
    a tiny or barely recruited pool from winning.

Arbitration
    ``all_above_threshold`` reports every above-threshold action (simultaneous
    population activity is not treated as mutually exclusive commands) and
    also names one primary action for callers that need a single output.
    ``single`` reports only the primary action. NEUTRAL is the state when no
    population passes the gate and threshold.

Time window
    Every window is half-open: ``start_ms <= t < end_ms``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields
from typing import Mapping, Sequence

import numpy as np

from motor.populations import ACTION_POPULATIONS, MotorPopulations

_ARBITRATION = ("all_above_threshold", "single")
_SMOOTHING = ("none", "moving_average")
_DECISION_SIGNAL = "active_fraction"


@dataclass(frozen=True)
class DecoderConfig:
    """Decoder parameters. Thresholds are declared a priori, not fitted."""

    window_ms: float = 50.0
    step_ms: float = 50.0
    activation_threshold: float = 0.20
    release_threshold: float = 0.10
    min_active_neurons: int = 3
    min_spikes: int = 5
    tie_tolerance: float = 1e-9
    priority: tuple[str, ...] = ACTION_POPULATIONS
    arbitration: str = "all_above_threshold"
    smoothing: str = "none"
    smoothing_windows: int = 3
    hysteresis: bool = False

    def __post_init__(self) -> None:
        for name in ("window_ms", "step_ms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if not np.isfinite(float(value)) or float(value) <= 0:
                raise ValueError(f"{name} must be positive and finite")
        for name in ("activation_threshold", "release_threshold"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if not np.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.activation_threshold <= 0:
            raise ValueError("activation_threshold must be positive")
        if self.release_threshold > self.activation_threshold:
            raise ValueError(
                "release_threshold cannot exceed activation_threshold"
            )
        for name in ("min_active_neurons", "min_spikes", "smoothing_windows"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            if value < 1:
                raise ValueError(f"{name} must be at least 1")
        if not np.isfinite(float(self.tie_tolerance)):
            raise ValueError("tie_tolerance must be finite")
        if float(self.tie_tolerance) < 0:
            raise ValueError("tie_tolerance cannot be negative")
        priority = tuple(str(value) for value in self.priority)
        if len(priority) != len(ACTION_POPULATIONS) or set(priority) != set(
            ACTION_POPULATIONS
        ):
            raise ValueError(
                f"priority must be a permutation of {ACTION_POPULATIONS}"
            )
        object.__setattr__(self, "priority", priority)
        if self.arbitration not in _ARBITRATION:
            raise ValueError(f"arbitration must be one of {_ARBITRATION}")
        if self.smoothing not in _SMOOTHING:
            raise ValueError(f"smoothing must be one of {_SMOOTHING}")
        if not isinstance(self.hysteresis, (bool, np.bool_)):
            raise ValueError("hysteresis must be a boolean")
        object.__setattr__(self, "hysteresis", bool(self.hysteresis))

    @classmethod
    def from_config(cls, payload: Mapping) -> "DecoderConfig":
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise ValueError(f"unknown decoder parameters: {unknown}")
        values = dict(payload)
        if "priority" in values:
            values["priority"] = tuple(str(value) for value in values["priority"])
        for name in (
            "window_ms",
            "step_ms",
            "activation_threshold",
            "release_threshold",
            "tie_tolerance",
        ):
            if name in values:
                values[name] = float(values[name])
        for name in ("min_active_neurons", "min_spikes", "smoothing_windows"):
            if name in values:
                values[name] = int(values[name])
        if "hysteresis" in values:
            values["hysteresis"] = bool(values["hysteresis"])
        return cls(**values)


@dataclass(frozen=True)
class PopulationEvidence:
    """Descriptive activity measures for one population in one window."""

    population: str
    size: int
    spikes: int
    active_neurons: int
    active_fraction: float
    mean_rate_hz: float
    sufficient: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "population": self.population,
            "size": int(self.size),
            "spikes": int(self.spikes),
            "active_neurons": int(self.active_neurons),
            "active_fraction": round(float(self.active_fraction), 6),
            "mean_rate_hz": round(float(self.mean_rate_hz), 4),
            "sufficient": bool(self.sufficient),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ActionDecision:
    """One decoder output for one time window."""

    window_start_ms: float
    window_end_ms: float
    raw_scores: Mapping[str, float]
    scores: Mapping[str, float]
    evidence: Mapping[str, PopulationEvidence]
    active_actions: tuple[str, ...]
    primary_action: str | None
    lateralization: float | None
    reason: str

    @property
    def state(self) -> str:
        return self.primary_action or "NEUTRAL"

    @property
    def neutral(self) -> bool:
        return self.primary_action is None

    def as_dict(self) -> dict:
        return {
            "window_start_ms": round(float(self.window_start_ms), 4),
            "window_end_ms": round(float(self.window_end_ms), 4),
            "decoded_state": self.state,
            "primary_action": self.primary_action,
            "active_actions": list(self.active_actions),
            "neutral": self.neutral,
            "reason": self.reason,
            "raw_scores": {
                key: round(float(value), 6)
                for key, value in self.raw_scores.items()
            },
            "scores": {
                key: round(float(value), 6) for key, value in self.scores.items()
            },
            "lateralization": (
                None
                if self.lateralization is None
                else round(float(self.lateralization), 6)
            ),
            "evidence": {
                key: value.as_dict() for key, value in self.evidence.items()
            },
        }


def _validate_spikes(
    times_ms: np.ndarray, neuron_indices: np.ndarray, n_neurons: int
) -> tuple[np.ndarray, np.ndarray]:
    times = np.asarray(times_ms)
    indices = np.asarray(neuron_indices)
    if times.ndim != 1 or indices.ndim != 1:
        raise ValueError("spike times and neuron indices must be 1-D")
    if times.shape != indices.shape:
        raise ValueError(
            f"spike times and neuron indices differ in length: "
            f"{times.shape[0]} vs {indices.shape[0]}"
        )
    if times.size:
        times = times.astype(np.float64, copy=False)
        if not np.all(np.isfinite(times)):
            raise ValueError("spike times must be finite")
        if np.any(times < 0):
            raise ValueError("spike times cannot be negative")
    if indices.size:
        if not np.issubdtype(indices.dtype, np.integer):
            raise ValueError("neuron indices must be integers")
        indices = indices.astype(np.int64, copy=False)
        if int(indices.min()) < 0 or int(indices.max()) >= n_neurons:
            raise ValueError(
                f"neuron indices must lie in [0, {n_neurons - 1}]"
            )
    else:
        indices = indices.astype(np.int64, copy=False)
    return times, indices


class MotorDecoder:
    """Stateful, deterministic motor-population decoder."""

    def __init__(
        self,
        populations: MotorPopulations,
        config: DecoderConfig | None = None,
    ) -> None:
        self.populations = populations
        self.config = config or DecoderConfig()
        self.n_neurons = int(populations.n_neurons)
        self._masks = {
            action: np.asarray(populations.mask(action), dtype=bool)
            for action in ACTION_POPULATIONS
        }
        self._sizes = {
            action: int(mask.sum()) for action, mask in self._masks.items()
        }
        self.reset()

    def reset(self) -> None:
        """Clear smoothing history and hysteresis state."""
        self._history = {
            action: deque(maxlen=self.config.smoothing_windows)
            for action in ACTION_POPULATIONS
        }
        self._hysteresis_active = {action: False for action in ACTION_POPULATIONS}

    @property
    def decision_signal(self) -> str:
        return _DECISION_SIGNAL

    def describe(self) -> dict:
        return {
            "n_neurons": self.n_neurons,
            "populations": dict(self._sizes),
            "decision_signal": _DECISION_SIGNAL,
            "window_semantics": "[start_ms, end_ms)",
            "config": {
                "window_ms": float(self.config.window_ms),
                "step_ms": float(self.config.step_ms),
                "activation_threshold": float(self.config.activation_threshold),
                "release_threshold": float(self.config.release_threshold),
                "min_active_neurons": int(self.config.min_active_neurons),
                "min_spikes": int(self.config.min_spikes),
                "tie_tolerance": float(self.config.tie_tolerance),
                "priority": list(self.config.priority),
                "arbitration": self.config.arbitration,
                "smoothing": self.config.smoothing,
                "smoothing_windows": int(self.config.smoothing_windows),
                "hysteresis": bool(self.config.hysteresis),
            },
        }

    def decode_window(
        self,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
    ) -> ActionDecision:
        """Decode one half-open window ``[start_ms, end_ms)``."""
        start = float(start_ms)
        end = float(end_ms)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            raise ValueError("window end must be a finite time after its start")
        times, indices = _validate_spikes(
            spike_times_ms, spike_neuron_indices, self.n_neurons
        )
        return self._decode(times, indices, start, end)

    def decode_series(
        self,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
        *,
        include_partial: bool = True,
    ) -> list[ActionDecision]:
        """Decode consecutive windows of ``window_ms`` advancing by ``step_ms``."""
        start = float(start_ms)
        stop = float(end_ms)
        if not np.isfinite(start) or not np.isfinite(stop) or stop <= start:
            raise ValueError("series end must be a finite time after its start")
        times, indices = _validate_spikes(
            spike_times_ms, spike_neuron_indices, self.n_neurons
        )
        decisions: list[ActionDecision] = []
        cursor = start
        while cursor < stop:
            window_end = cursor + self.config.window_ms
            if window_end > stop:
                if not include_partial:
                    break
                window_end = stop
            decisions.append(self._decode(times, indices, cursor, window_end))
            cursor += self.config.step_ms
        return decisions

    def decode_recorder(
        self,
        recorder,
        start_ms: float,
        end_ms: float,
        *,
        include_partial: bool = True,
    ) -> list[ActionDecision]:
        """Decode a ``SpikeRecorder`` produced by the existing simulator."""
        if int(getattr(recorder, "n_neurons", -1)) != self.n_neurons:
            raise ValueError(
                "recorder neuron count does not match the decoder populations"
            )
        return self.decode_series(
            recorder.spike_times_ms,
            recorder.spike_neuron_indices,
            start_ms,
            end_ms,
            include_partial=include_partial,
        )

    def _decode(
        self,
        times: np.ndarray,
        indices: np.ndarray,
        start: float,
        end: float,
    ) -> ActionDecision:
        in_window = (times >= start) & (times < end)
        counts = np.bincount(
            indices[in_window], minlength=self.n_neurons
        ).astype(np.int64)
        seconds = (end - start) / 1000.0

        config = self.config
        evidence: dict[str, PopulationEvidence] = {}
        gated: dict[str, float] = {}
        for action in ACTION_POPULATIONS:
            mask = self._masks[action]
            size = self._sizes[action]
            spikes = int(counts[mask].sum())
            active = int(np.count_nonzero(counts[mask]))
            fraction = active / size if size else 0.0
            rate = spikes / size / seconds if size else 0.0
            reasons = []
            if size == 0:
                reasons.append("empty_population")
            else:
                if spikes < config.min_spikes:
                    reasons.append("spikes_below_minimum")
                if active < config.min_active_neurons:
                    reasons.append("active_neurons_below_minimum")
            sufficient = not reasons
            evidence[action] = PopulationEvidence(
                population=action,
                size=size,
                spikes=spikes,
                active_neurons=active,
                active_fraction=fraction,
                mean_rate_hz=rate,
                sufficient=sufficient,
                reason="ok" if sufficient else "+".join(reasons),
            )
            gated[action] = fraction if sufficient else 0.0

        if config.smoothing == "moving_average":
            scores = {}
            for action in ACTION_POPULATIONS:
                self._history[action].append(gated[action])
                scores[action] = float(np.mean(self._history[action]))
        else:
            scores = dict(gated)

        above: list[str] = []
        for action in ACTION_POPULATIONS:
            score = scores[action]
            if config.hysteresis and self._hysteresis_active[action]:
                keep = score > 0.0 and score >= config.release_threshold
            else:
                keep = score > 0.0 and score >= config.activation_threshold
            self._hysteresis_active[action] = bool(keep)
            if keep:
                above.append(action)

        priority_index = {
            action: index for index, action in enumerate(config.priority)
        }
        above.sort(key=priority_index.__getitem__)
        primary: str | None = None
        if above:
            ranked = sorted(above, key=lambda action: (-scores[action], priority_index[action]))
            best = ranked[0]
            tied = [
                action
                for action in ranked
                if abs(scores[action] - scores[best]) <= config.tie_tolerance
            ]
            primary = min(tied, key=priority_index.__getitem__)
            if len(above) > 1:
                reason = (
                    "tie_broken_by_priority"
                    if len(tied) > 1
                    else "simultaneous_actions"
                )
            elif len(tied) > 1:
                reason = "tie_broken_by_priority"
            else:
                reason = "single_action"
        else:
            reason = "neutral_no_activation"

        if config.arbitration == "single":
            active_actions = (primary,) if primary else ()
        else:
            active_actions = tuple(above)

        left = scores["LEFT"]
        right = scores["RIGHT"]
        lateralization = (
            (left - right) / (left + right) if (left + right) > 0 else None
        )
        return ActionDecision(
            window_start_ms=start,
            window_end_ms=end,
            raw_scores=gated,
            scores=scores,
            evidence=evidence,
            active_actions=active_actions,
            primary_action=primary,
            lateralization=lateralization,
            reason=reason,
        )
