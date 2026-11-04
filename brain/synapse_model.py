"""Sparse synaptic transmission over a connectome CSR graph.

Synaptic weights are a computational transformation of structural synapse
counts, not measured conductances::

    weight_pa = scale * syn_count ** exponent

Each edge inherits the assumed sign of its presynaptic neuron. Predicted
neurotransmitters provide only a coarse sign assumption; cotransmission,
receptor kinetics and neuromodulation are not modelled.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

DEFAULT_NT_SIGNS = {
    "ACH": "excitatory",
    "GLUT": "excitatory",
    "GABA": "inhibitory",
    "DA": "unknown",
    "SER": "unknown",
    "OCT": "unknown",
}
_SIGN_VALUES = {"excitatory": 1, "inhibitory": -1, "silent": 0}


@dataclass(frozen=True)
class SynapseParameters:
    weight_transform: str = "power"
    weight_scale_pa_per_synapse: float = 0.55
    weight_exponent: float = 0.75
    tau_exc_ms: float = 5.0
    tau_inh_ms: float = 8.0
    delay_ms: float = 1.0
    nt_signs: Mapping[str, str] = field(
        default_factory=lambda: dict(DEFAULT_NT_SIGNS)
    )
    unknown_nt_sign: str = "excitatory"
    unlabeled_sign: str = "excitatory"

    def __post_init__(self) -> None:
        if self.weight_transform not in {"linear", "power"}:
            raise ValueError("weight_transform must be 'linear' or 'power'")
        if self.weight_scale_pa_per_synapse < 0:
            raise ValueError("weight_scale_pa_per_synapse cannot be negative")
        if self.weight_exponent <= 0:
            raise ValueError("weight_exponent must be positive")
        if self.tau_exc_ms <= 0 or self.tau_inh_ms <= 0:
            raise ValueError("synaptic time constants must be positive")
        if self.delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        for value in (self.unknown_nt_sign, self.unlabeled_sign):
            if value not in _SIGN_VALUES:
                raise ValueError(f"invalid sign policy: {value}")
        for value in self.nt_signs.values():
            if value not in _SIGN_VALUES and value != "unknown":
                raise ValueError(f"invalid nt_signs value: {value}")

    @classmethod
    def from_config(cls, config: Mapping) -> "SynapseParameters":
        values = dict(config)
        signs = values.pop("nt_signs", None)
        merged = dict(DEFAULT_NT_SIGNS)
        if signs:
            merged.update(
                {str(key).upper(): str(value) for key, value in signs.items()}
            )
        return cls(nt_signs=merged, **values)

class SynapseModel:
    """Exponential current synapses driven by presynaptic spikes."""

    def __init__(self, graph, params: SynapseParameters, dt_ms: float) -> None:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        n = graph.n_nodes
        if len(graph.out_indptr) != n + 1:
            raise ValueError("graph out_indptr is incompatible with n_nodes")
        self.n_neurons = n
        self.params = params
        self.dt_ms = float(dt_ms)
        self._out_indptr = graph.out_indptr
        self._edge_dst = graph.edge_dst
        self._exc_decay = float(np.exp(-self.dt_ms / params.tau_exc_ms))
        self._inh_decay = float(np.exp(-self.dt_ms / params.tau_inh_ms))
        vocabulary = graph.vocabulary.get("nt_type", [])
        self.signs = self._assign_signs(graph.nt_code, vocabulary)
        counts = graph.edge_weight.astype(np.float64)
        if params.weight_transform == "power":
            weights = params.weight_scale_pa_per_synapse * np.power(
                counts, params.weight_exponent
            )
        else:
            weights = params.weight_scale_pa_per_synapse * counts
        edge_signs = self.signs[graph.edge_src]
        self.edge_exc_weight = np.where(
            edge_signs > 0, weights, 0.0
        ).astype(np.float32)
        self.edge_inh_weight = np.where(
            edge_signs < 0, weights, 0.0
        ).astype(np.float32)
        self.has_inhibition = bool(np.any(self.edge_inh_weight > 0))
        rounded_delay = int(round(params.delay_ms / self.dt_ms))
        extra_steps = max(0, rounded_delay - 1)
        self.effective_delay_ms = (extra_steps + 1) * self.dt_ms
        self._pending_exc = deque(
            (np.zeros(n, dtype=np.float32) for _ in range(extra_steps + 1)),
            maxlen=extra_steps + 1,
        )
        self._pending_inh = deque(
            (np.zeros(n, dtype=np.float32) for _ in range(extra_steps + 1)),
            maxlen=extra_steps + 1,
        )
        self._exc = np.zeros(n, dtype=np.float32)
        self._inh = np.zeros(n, dtype=np.float32)
        self.total_transmissions = 0

    def _assign_signs(
        self, nt_code: np.ndarray, vocabulary: list[str]
    ) -> np.ndarray:
        params = self.params
        signs = np.full(
            self.n_neurons, _SIGN_VALUES[params.unlabeled_sign], dtype=np.int8
        )
        for index, label in enumerate(vocabulary):
            decision = params.nt_signs.get(str(label).upper(), "unknown")
            if decision == "unknown":
                decision = params.unknown_nt_sign
            signs[nt_code == index] = _SIGN_VALUES[decision]
        return signs

    @property
    def excitatory_current_pa(self) -> np.ndarray:
        return self._exc

    @property
    def inhibitory_current_pa(self) -> np.ndarray:
        return self._inh

    @property
    def synaptic_current_pa(self) -> np.ndarray:
        return self._exc - self._inh

    @property
    def delay_buffer_bytes(self) -> int:
        return int(
            sum(buffer.nbytes for buffer in self._pending_exc)
            + sum(buffer.nbytes for buffer in self._pending_inh)
        )

    @property
    def memory_bytes(self) -> int:
        """Bytes held by edge weights, signs, currents and delay buffers."""
        return int(
            self.edge_exc_weight.nbytes
            + self.edge_inh_weight.nbytes
            + self.signs.nbytes
            + self._exc.nbytes
            + self._inh.nbytes
            + self.delay_buffer_bytes
        )

    def reset(self) -> None:
        self._exc.fill(0.0)
        self._inh.fill(0.0)
        for buffer in self._pending_exc:
            buffer.fill(0.0)
        for buffer in self._pending_inh:
            buffer.fill(0.0)
        self.total_transmissions = 0

    def advance(self) -> None:
        """Decay currents and deliver the next delayed spike packet."""
        self._exc *= self._exc_decay
        self._inh *= self._inh_decay
        incoming_exc = self._pending_exc.popleft()
        incoming_inh = self._pending_inh.popleft()
        if incoming_exc.any():
            self._exc += incoming_exc
        if incoming_inh.any():
            self._inh += incoming_inh
        incoming_exc.fill(0.0)
        incoming_inh.fill(0.0)
        self._pending_exc.append(incoming_exc)
        self._pending_inh.append(incoming_inh)

    def propagate(self, spike_indices: np.ndarray) -> int:
        """Route spikes through outgoing edges into the delay buffer.

        Returns the number of spike-to-edge transmissions. No dense adjacency
        matrix is constructed.
        """
        spikes = np.asarray(spike_indices, dtype=np.int64)
        if spikes.size == 0:
            return 0
        starts = self._out_indptr[spikes]
        ends = self._out_indptr[spikes + 1]
        counts = ends - starts
        total = int(counts.sum())
        if total == 0:
            return 0
        if spikes.size == 1:
            edge_index = np.arange(starts[0], ends[0], dtype=np.int64)
        else:
            prefix = np.cumsum(counts) - counts
            edge_index = np.repeat(starts - prefix, counts) + np.arange(
                total, dtype=np.int64
            )
        destinations = self._edge_dst[edge_index]
        exc = np.bincount(
            destinations,
            weights=self.edge_exc_weight[edge_index],
            minlength=self.n_neurons,
        )
        self._pending_exc[-1] += exc.astype(np.float32)
        if self.has_inhibition:
            inh = np.bincount(
                destinations,
                weights=self.edge_inh_weight[edge_index],
                minlength=self.n_neurons,
            )
            self._pending_inh[-1] += inh.astype(np.float32)
        self.total_transmissions += total
        return total
