"""Signed synapses whose excitatory and inhibitory arrays are owned copies.

SCIENTIFIC STATUS
    This class changes no model. It re-binds the parent's weight arrays to the
    effective layer of a :class:`~plasticity.weights.WeightState` so that
    propagation reads the current effective weights, and it exposes the CSR
    edge indices touched by a spike packet for eligibility accumulation.

The parent arithmetic in ``brain.banc_simulator.BancSignedSynapses`` is reused
unchanged. With a zero learned delta the owned arrays are bit-identical to the
policy arrays, so propagation is bit-identical to the fixed-weight pathway.
"""

from __future__ import annotations

import numpy as np

from brain.banc_simulator import BancSignedSynapses

from .weights import WeightState, graph_signature


class PlasticSignedSynapses(BancSignedSynapses):
    """BANC synapses with owned effective weight arrays and edge attribution."""

    def __init__(self, graph, policy, weight_state: WeightState, *args, **kwargs):
        if not isinstance(weight_state, WeightState):
            raise ValueError("weight_state must be a WeightState")
        super().__init__(graph, policy, *args, **kwargs)
        if weight_state.n_edges != self.n_edges:
            raise ValueError("weight state and graph edge counts differ")
        if weight_state.graph_signature != graph_signature(graph):
            raise ValueError(
                "weight state belongs to a different structural graph"
            )
        self.weight_state = weight_state
        self.edge_exc_weight = weight_state.effective_exc
        self.edge_inh_weight = weight_state.effective_inh
        self.has_inhibition = bool(np.any(self.edge_inh_weight > 0))
        self._last_active_edges = np.empty(0, dtype=np.int64)

    @property
    def last_active_edges(self) -> np.ndarray:
        """CSR edge indices routed into the delay buffer by the last propagate."""
        return self._last_active_edges

    def active_edges_for(self, spike_indices) -> np.ndarray:
        """CSR edge indices of every outgoing edge of the spiking neurons."""
        spikes = np.asarray(spike_indices, dtype=np.int64)
        if spikes.size == 0:
            return np.empty(0, dtype=np.int64)
        if int(spikes.max()) >= self.n_neurons:
            raise ValueError("spike index outside the neuron range")
        if int(spikes.min()) < 0:
            raise ValueError("spike index cannot be negative")
        unbounded = np.unique(spikes)
        starts = self._out_indptr[unbounded]
        ends = self._out_indptr[unbounded + 1]
        counts = ends - starts
        total = int(counts.sum())
        if total == 0:
            return np.empty(0, dtype=np.int64)
        if unbounded.size == 1:
            return np.arange(starts[0], ends[0], dtype=np.int64)
        prefix = np.cumsum(counts) - counts
        return np.repeat(starts - prefix, counts) + np.arange(
            total, dtype=np.int64
        )

    def propagate(self, spike_indices: np.ndarray) -> int:
        self._last_active_edges = self.active_edges_for(spike_indices)
        return super().propagate(spike_indices)

    def reset(self) -> None:
        super().reset()
        self._last_active_edges = np.empty(0, dtype=np.int64)

    @property
    def weight_memory_bytes(self) -> int:
        return int(
            self.weight_state.effective_exc.nbytes
            + self.weight_state.effective_inh.nbytes
        )

    def describe(self) -> dict:
        return {
            "class": "PlasticSignedSynapses",
            "n_neurons": self.n_neurons,
            "n_edges": self.n_edges,
            "has_inhibition": self.has_inhibition,
            "delay_steps": int(self.delay_steps),
            "effective_delay_ms": self.effective_delay_ms,
            "weight_arrays": "owned effective layers of WeightState",
            "weights_modified": bool(self.weight_state.n_update_calls > 0),
        }
