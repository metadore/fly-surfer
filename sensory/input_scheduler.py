"""Schedule encoded sensory responses as external current for the simulator.

The scheduler is an ``input_schedule`` for ``BrainSimulator``: each step it
adds ``activation * current_pa`` to a preallocated current array. It never
overwrites the array, so background, noise and a Phase 2 stimulus can coexist.

States change at configured times. With ``transition_ms > 0`` the encoded
activations are blended linearly between the outgoing and incoming state over
that window; with the default 0 the change is instantaneous. The blend is on
the encoded activations, not on the game state.
"""

from __future__ import annotations

import bisect
import math

import numpy as np

from sensory.game_state import GameState
from sensory.population_encoder import encode_state


def _finite_non_negative(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


class SensoryInputScheduler:
    """Deterministic, time-varying current injection for mapped populations."""

    def __init__(
        self,
        mapping,
        encoders: dict,
        timeline,
        *,
        dt_ms: float,
        duration_ms: float,
        current_pa: dict[str, float],
        transition_ms: float = 0.0,
        onset_ms: float = 0.0,
        offset_ms: float | None = None,
        active_features=None,
    ) -> None:
        if not isinstance(timeline, (list, tuple)) or not timeline:
            raise ValueError("timeline must be a non-empty list of states")
        self.mapping = mapping
        self.encoders = encoders
        self.dt_ms = _finite_non_negative(dt_ms, "dt_ms")
        if self.dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        self.duration_ms = _finite_non_negative(duration_ms, "duration_ms")
        if self.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        self.transition_ms = _finite_non_negative(transition_ms, "transition_ms")
        self.onset_ms = _finite_non_negative(onset_ms, "onset_ms")
        self.offset_ms = (
            self.duration_ms
            if offset_ms is None
            else _finite_non_negative(offset_ms, "offset_ms")
        )
        if self.onset_ms >= self.offset_ms:
            raise ValueError("onset_ms must be earlier than offset_ms")
        if self.offset_ms > self.duration_ms:
            raise ValueError("offset_ms must not exceed duration_ms")

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

        self.states: list[GameState] = []
        starts: list[float] = []
        for entry in timeline:
            if isinstance(entry, GameState):
                state, start = entry, entry.time_ms
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                start, state = entry
            else:
                raise ValueError(
                    "each timeline entry must be a GameState or (time_ms, state)"
                )
            if not isinstance(state, GameState):
                raise ValueError("timeline states must be GameState instances")
            start = _finite_non_negative(start, "segment start")
            if starts and start <= starts[-1]:
                raise ValueError("timeline start times must increase strictly")
            starts.append(start)
            self.states.append(state)
        if starts[0] >= self.duration_ms:
            raise ValueError("the first state must start before duration_ms")

        self.starts = np.asarray(starts, dtype=np.float64)
        if not set(encoders) <= set(mapping.populations):
            missing = sorted(set(encoders) - set(mapping.populations))
            raise ValueError(f"mapping is missing features {missing}")

        self._current_pa: dict[str, float] = {}
        for feature in encoders:
            value = current_pa.get(feature, 0.0)
            self._current_pa[feature] = _finite_non_negative(
                value, f"current_pa[{feature!r}]"
            )
        self._indices = np.concatenate(
            [mapping.indices(feature) for feature in encoders]
        )
        self._slices: dict[str, slice] = {}
        offset = 0
        for feature in encoders:
            size = mapping.size(feature)
            self._slices[feature] = slice(offset, offset + size)
            offset += size

        active = set(self.active_features)
        self._stimulated_indices = np.unique(
            np.concatenate(
                [mapping.indices(feature) for feature in self.active_features]
            )
        )
        self._values: list[np.ndarray] = []
        for state in self.states:
            encoded = encode_state(state.features(), encoders)
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
            self._values.append(values)

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._stimulated_indices

    @property
    def memory_bytes(self) -> int:
        """Bytes held by the scheduled index and per-segment value arrays."""
        return int(
            self._indices.nbytes
            + self.starts.nbytes
            + sum(values.nbytes for values in self._values)
        )

    def _values_at(self, time_ms: float) -> np.ndarray | None:
        index = int(np.searchsorted(self.starts, time_ms, side="right")) - 1
        if index < 0:
            return None
        values = self._values[index]
        if (
            self.transition_ms > 0
            and index > 0
            and time_ms < self.starts[index] + self.transition_ms
        ):
            alpha = (time_ms - self.starts[index]) / self.transition_ms
            values = (1.0 - alpha) * self._values[index - 1] + alpha * values
        return values

    def apply(self, step: int, time_ms: float, current_pa: np.ndarray) -> None:
        """Add this step's sensory current; never overwrite unrelated input."""
        if time_ms < self.onset_ms or time_ms >= self.offset_ms:
            return
        values = self._values_at(time_ms)
        if values is None:
            return
        current_pa[self._indices] += values

    def feature_currents_at(self, time_ms: float) -> dict[str, float]:
        """Total scheduled current per feature at a time (pA)."""
        if time_ms < self.onset_ms or time_ms >= self.offset_ms:
            return {feature: 0.0 for feature in self.encoders}
        values = self._values_at(time_ms)
        if values is None:
            return {feature: 0.0 for feature in self.encoders}
        return {
            feature: float(values[self._slices[feature]].sum())
            for feature in self.encoders
        }

    def input_statistics(self) -> dict:
        active = set(self.active_features)
        peak = {feature: 0.0 for feature in self.encoders}
        for values in self._values:
            for feature in self.encoders:
                peak[feature] = max(
                    peak[feature], float(values[self._slices[feature]].sum())
                )
        return {
            "max_total_current_pa": round(float(sum(peak.values())), 6),
            "max_per_neuron_current_pa": round(
                max(
                    (float(values.max()) for values in self._values),
                    default=0.0,
                ),
                6,
            ),
            "peak_feature_current_pa": {
                feature: round(peak[feature], 6) for feature in self.encoders
            },
            "active_features": list(self.active_features),
            "n_active_features": len(active),
        }

    def signature(self) -> dict:
        """Small deterministic representation used by reproducibility checks."""
        return {
            "indices": self._indices.astype(np.int64),
            "values": np.stack(self._values),
            "starts": self.starts,
        }

    def describe(self) -> dict:
        populations = {}
        for feature in self.encoders:
            population = self.mapping.populations[feature]
            populations[feature] = {
                "n_neurons": int(population.size()),
                "current_pa": self._current_pa[feature],
                "root_ids": [
                    int(value)
                    for group in population.plan.groups
                    for value in population.root_ids[group[0]]
                ],
            }
        return {
            "kind": "sensory_population_schedule",
            "dt_ms": self.dt_ms,
            "duration_ms": self.duration_ms,
            "transition_ms": self.transition_ms,
            "onset_ms": self.onset_ms,
            "offset_ms": self.offset_ms,
            "n_features": len(self.encoders),
            "active_features": list(self.active_features),
            "n_stimulated_neurons": int(self.stimulated_indices.size),
            "features": populations,
            "segments": [
                {"start_ms": float(start), "state_time_ms": state.time_ms}
                for start, state in zip(self.starts, self.states)
            ],
        }
