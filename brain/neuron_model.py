"""Vectorised leaky integrate-and-fire neuron population.

Membrane dynamics per neuron::

    C_m dV/dt = -g_L (V - E_L) + I_syn + I_ext

The passive part is integrated exactly over each timestep:

    V(t+dt) = E_L + (V(t) - E_L) exp(-dt/tau_m) + I (1 - exp(-dt/tau_m)) / g_L

so the update is stable for any positive timestep. Threshold crossing is
detected at the end of a timestep, which makes spike times quantised to dt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

DEFAULT_N_NEURONS = 1


@dataclass(frozen=True)
class LIFParameters:
    """Assumed LIF parameters in pF, nS, mV, ms and pA."""

    capacitance_pf: float = 200.0
    leak_conductance_ns: float = 10.0
    resting_potential_mv: float = -65.0
    threshold_mv: float = -50.0
    reset_potential_mv: float = -68.0
    refractory_ms: float = 2.0
    initial_potential_mv: float = -65.0
    minimum_potential_mv: float = -90.0

    def __post_init__(self) -> None:
        if self.capacitance_pf <= 0 or self.leak_conductance_ns <= 0:
            raise ValueError("capacitance and leak conductance must be positive")
        if self.threshold_mv <= self.reset_potential_mv:
            raise ValueError("threshold must be above the reset potential")
        if self.refractory_ms < 0:
            raise ValueError("refractory_ms cannot be negative")
        if self.minimum_potential_mv > self.reset_potential_mv:
            raise ValueError(
                "minimum_potential_mv must not exceed the reset potential"
            )

    @property
    def tau_m_ms(self) -> float:
        return self.capacitance_pf / self.leak_conductance_ns

    @property
    def rheobase_pa(self) -> float:
        """Constant current that holds the membrane exactly at threshold."""
        return (self.threshold_mv - self.resting_potential_mv) * self.leak_conductance_ns

    @classmethod
    def from_config(cls, config: Mapping[str, float]) -> "LIFParameters":
        return cls(**{key: float(value) for key, value in config.items()})


class LIFPopulation:
    """A vectorised population of independent LIF neurons."""

    def __init__(
        self, n_neurons: int, params: LIFParameters, dt_ms: float
    ) -> None:
        if n_neurons < 1:
            raise ValueError("n_neurons must be positive")
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        self.n_neurons = int(n_neurons)
        self.params = params
        self.dt_ms = float(dt_ms)
        self._decay = float(np.exp(-self.dt_ms / params.tau_m_ms))
        self._drive = (1.0 - self._decay) / params.leak_conductance_ns
        rounded = int(np.ceil(params.refractory_ms / self.dt_ms))
        self._refractory_steps_blocked = max(0, rounded - 1)
        self._V = np.full(
            self.n_neurons, params.initial_potential_mv, dtype=np.float64
        )
        self._refractory_steps = np.zeros(self.n_neurons, dtype=np.int32)
        self._spike_count = 0

    @property
    def membrane_potential(self) -> np.ndarray:
        """Current membrane potential in mV (read-only use)."""
        return self._V

    @property
    def refractory_steps(self) -> np.ndarray:
        return self._refractory_steps

    @property
    def effective_refractory_ms(self) -> float:
        return (self._refractory_steps_blocked + 1) * self.dt_ms

    @property
    def spike_count(self) -> int:
        return self._spike_count

    @property
    def memory_bytes(self) -> int:
        """Bytes held by persistent membrane and refractory state."""
        return int(self._V.nbytes + self._refractory_steps.nbytes)

    def steady_state_potential(self, current_pa: float) -> float:
        return self.params.resting_potential_mv + current_pa / self.params.leak_conductance_ns

    def reset(self, initial_potential_mv: float | None = None) -> None:
        value = (
            self.params.initial_potential_mv
            if initial_potential_mv is None
            else float(initial_potential_mv)
        )
        self._V.fill(value)
        self._refractory_steps.fill(0)
        self._spike_count = 0

    def step(self, current_pa: np.ndarray | float) -> np.ndarray:
        """Advance one timestep and return the indices of spiking neurons."""
        current = np.asarray(current_pa, dtype=np.float64)
        if current.ndim == 0:
            current = np.broadcast_to(current, (self.n_neurons,))
        elif current.shape != (self.n_neurons,):
            raise ValueError(
                f"current must be scalar or shape ({self.n_neurons},), "
                f"got {current.shape}"
            )

        blocked = self._refractory_steps > 0
        if blocked.any():
            self._V[blocked] = self.params.reset_potential_mv
        active = ~blocked

        params = self.params
        self._V[active] = (
            params.resting_potential_mv
            + (self._V[active] - params.resting_potential_mv) * self._decay
            + current[active] * self._drive
        )
        # Unmodelled leak/voltage-gated currents keep real neurons from being
        # driven to arbitrarily negative potentials by sustained inhibition.
        np.maximum(self._V, params.minimum_potential_mv, out=self._V)

        spikes = active & (self._V >= params.threshold_mv)
        if self._refractory_steps_blocked:
            self._refractory_steps[blocked] = np.maximum(
                self._refractory_steps[blocked] - 1, 0
            )
        if spikes.any():
            self._V[spikes] = params.reset_potential_mv
            self._refractory_steps[spikes] = self._refractory_steps_blocked
            self._spike_count += int(spikes.sum())
            return np.flatnonzero(spikes).astype(np.int32)
        return np.empty(0, dtype=np.int32)
