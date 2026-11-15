"""Sparse, edge-indexed eligibility traces and a sparse synaptic delay line.

SCIENTIFIC STATUS
    An eligibility trace here is a short-lived scalar tag attached to one
    plastic edge. It is a model of synaptic tagging, not a measurement of a
    biological eligibility trace. ``tau_e_ms`` is a declared modelling
    parameter, not an experimentally fitted time constant.

The store is indexed by a caller-defined edge slot (0..n_traces-1). The caller
decides what a slot means: in Phase 5D a slot maps to one verified-sign CSR
edge. No N x N matrix is ever allocated; per-edge state is two linear arrays
and a list of currently touched edges.

Decay is lazy by default: advancing the clock performs no per-edge work and
each value is materialised as ``stored * lambda**dt_steps`` when it is read or
updated. A periodic ``prune`` removes entries below a declared threshold so the
touched set stays bounded.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml

INCREMENT_UNIT = "one per coincident pre/post spike pair in the declared convention"

COINCIDENCE_CONVENTIONS = ("delay_matched", "same_step")


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _positive(value, name: str) -> float:
    number = _finite(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


class EligibilityStore:
    """Per-edge eligibility traces with lazy exponential decay."""

    def __init__(
        self,
        n_traces: int,
        *,
        tau_e_ms: float,
        dt_ms: float,
        prune_threshold: float = 1e-4,
        dtype=np.float32,
    ) -> None:
        if isinstance(n_traces, bool) or not isinstance(n_traces, (int, np.integer)):
            raise ValueError("n_traces must be an integer")
        if int(n_traces) < 1:
            raise ValueError("n_traces must be positive")
        self.n_traces = int(n_traces)
        self.tau_e_ms = _positive(tau_e_ms, "tau_e_ms")
        self.dt_ms = _positive(dt_ms, "dt_ms")
        self.prune_threshold = _finite(prune_threshold, "prune_threshold")
        if self.prune_threshold < 0:
            raise ValueError("prune_threshold must be non-negative")
        self.dtype = np.dtype(dtype)
        if self.dtype.kind != "f":
            raise ValueError("dtype must be a floating type")
        self.decay_per_step = math.exp(-self.dt_ms / self.tau_e_ms)
        if not 0.0 < self.decay_per_step <= 1.0:
            raise ValueError("decay_per_step must lie in (0, 1]")
        self._value = np.zeros(self.n_traces, dtype=self.dtype)
        self._stamp = np.full(self.n_traces, -1, dtype=np.int32)
        self._active = np.empty(0, dtype=np.int32)
        self._clock = 0

    @property
    def clock(self) -> int:
        return self._clock

    @property
    def active_edges(self) -> np.ndarray:
        """Edge slots that currently hold, or held, a trace."""
        return self._active

    @property
    def n_touched(self) -> int:
        return int(self._active.size)

    @property
    def memory_bytes(self) -> int:
        return int(self._value.nbytes + self._stamp.nbytes + self._active.nbytes)

    @staticmethod
    def capacity_bytes(n_traces: int, dtype=np.float32) -> int:
        """Bytes for the value and timestamp arrays, excluding the touched list."""
        dtype = np.dtype(dtype)
        return int(n_traces) * (dtype.itemsize + np.dtype(np.int32).itemsize)

    def _check_edges(self, edge_index, name: str = "edge_index") -> np.ndarray:
        edges = np.asarray(edge_index, dtype=np.int64).ravel()
        if edges.size and (edges.min() < 0 or edges.max() >= self.n_traces):
            raise ValueError(f"{name} contains edges outside 0..{self.n_traces - 1}")
        if edges.size > 1:
            ordered = np.sort(edges)
            if np.any(ordered[1:] == ordered[:-1]):
                raise ValueError(f"{name} must not contain duplicate edges")
        return edges

    def value(self, edge_index, step: int | None = None):
        """Decayed trace value at ``step`` (default: the current clock)."""
        edges = self._check_edges(edge_index)
        target = self._clock if step is None else int(step)
        if target < self._clock:
            raise ValueError("step must not precede the current clock")
        stamps = self._stamp[edges]
        stored = self._value[edges].astype(np.float64)
        valid = stamps >= 0
        steps = np.where(valid, target - stamps, 0)
        factors = np.where(valid, self.decay_per_step**steps, 0.0)
        values = np.where(valid, stored * factors, 0.0)
        if np.isscalar(edge_index):
            return float(values[0])
        return values

    def accumulate(self, edge_index, increment: float | Iterable[float] = 1.0) -> int:
        """Add ``increment`` to the decayed trace of each edge at the clock."""
        edges = self._check_edges(edge_index)
        if edges.size == 0:
            return 0
        increments = np.asarray(increment, dtype=np.float64)
        if increments.ndim == 0:
            increments = np.full(edges.size, float(increments), dtype=np.float64)
        else:
            increments = increments.ravel()
            if increments.size != edges.size:
                raise ValueError("increment must be scalar or match edge_index")
        if not np.all(np.isfinite(increments)):
            raise ValueError("increment must be finite")
        if np.any(increments < 0):
            raise ValueError("increment must be non-negative")

        stamps = self._stamp[edges]
        valid = stamps >= 0
        steps = np.where(valid, self._clock - stamps, 0)
        factors = np.where(valid, self.decay_per_step**steps, 0.0)
        stored = self._value[edges].astype(np.float64)
        updated = np.where(valid, stored * factors, 0.0) + increments
        limit = float(np.finfo(self.dtype).max)
        if not np.all(np.isfinite(updated)) or float(updated.max()) > limit:
            raise FloatingPointError("trace update produced a non-finite value")
        self._value[edges] = updated.astype(self.dtype)
        self._stamp[edges] = self._clock
        new = stamps < 0
        if new.any():
            self._active = np.concatenate(
                [self._active, edges[new].astype(np.int32)]
            )
        return int(edges.size)

    def advance(self, steps: int = 1) -> None:
        if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)):
            raise ValueError("steps must be an integer")
        if int(steps) < 0:
            raise ValueError("steps must be non-negative")
        if self._clock + int(steps) > np.iinfo(np.int32).max:
            raise OverflowError("trace clock exceeds the int32 timestamp range")
        self._clock += int(steps)

    def decay(self, dt_ms: float) -> None:
        """Advance the clock by ``dt_ms``; per-edge decay is applied lazily."""
        dt_ms = _finite(dt_ms, "dt_ms")
        if dt_ms < 0:
            raise ValueError("dt_ms must be non-negative")
        steps = dt_ms / self.dt_ms
        if abs(steps - round(steps)) > 1e-9:
            raise ValueError("dt_ms must be an integer multiple of dt_ms")
        self.advance(int(round(steps)))

    def prune(self, threshold: float | None = None) -> int:
        """Drop touched entries whose decayed value is below the threshold."""
        limit = self.prune_threshold if threshold is None else _finite(
            threshold, "threshold"
        )
        if limit < 0:
            raise ValueError("threshold must be non-negative")
        if self._active.size == 0:
            return 0
        stamps = self._stamp[self._active]
        steps = self._clock - stamps
        values = self._value[self._active].astype(np.float64) * (
            self.decay_per_step**steps
        )
        keep = values >= limit
        dropped = self._active[~keep]
        if dropped.size:
            self._value[dropped] = 0
            self._stamp[dropped] = -1
            self._active = self._active[keep]
        return int(dropped.size)

    def reset(self) -> None:
        self._value.fill(0)
        self._stamp.fill(-1)
        self._active = np.empty(0, dtype=np.int32)
        self._clock = 0

    def sparsity_report(self) -> dict:
        if self._active.size:
            values = self.value(self._active)
            magnitudes = np.abs(np.asarray(values, dtype=np.float64))
            nonzero = int(np.count_nonzero(magnitudes >= self.prune_threshold))
            l1 = float(magnitudes.sum())
            peak = float(magnitudes.max())
        else:
            nonzero = 0
            l1 = 0.0
            peak = 0.0
        return {
            "n_traces": self.n_traces,
            "n_touched": self.n_touched,
            "n_nonzero": nonzero,
            "touched_fraction": round(self.n_touched / self.n_traces, 9),
            "nonzero_fraction": round(nonzero / self.n_traces, 9),
            "l1": round(l1, 9),
            "max": round(peak, 9),
            "decay_per_step": round(self.decay_per_step, 12),
            "tau_e_ms": self.tau_e_ms,
            "prune_threshold": self.prune_threshold,
            "clock": self._clock,
            "storage": "lazy edge-indexed float arrays",
            "memory_bytes": self.memory_bytes,
            "capacity_bytes": self.capacity_bytes(self.n_traces, self.dtype),
        }

    def digest(self) -> str:
        if self._active.size:
            order = np.argsort(self._active)
            edges = self._active[order]
            values = np.round(self.value(edges), 9)
            payload = json.dumps(
                {"edges": edges.tolist(), "values": values.tolist()},
                sort_keys=True,
            )
        else:
            payload = json.dumps({"edges": [], "values": []})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def state_dict(self) -> dict:
        """Exact lazy state: stored values, stamps, active slots and clock."""
        if self._active.size:
            order = np.argsort(self._active)
            edges = self._active[order].astype(np.int32)
            values = self._value[edges].copy()
            stamps = self._stamp[edges].copy()
        else:
            edges = np.empty(0, dtype=np.int32)
            values = np.empty(0, dtype=self.dtype)
            stamps = np.empty(0, dtype=np.int32)
        return {
            "n_traces": self.n_traces,
            "edges": edges,
            "values": values,
            "stamps": stamps,
            "clock": int(self._clock),
            "digest": self.digest(),
        }

    def load_state_dict(self, payload: dict) -> None:
        """Restore a state produced by :meth:`state_dict`."""
        if not isinstance(payload, dict):
            raise ValueError("trace state must be a mapping")
        if int(payload.get("n_traces", -1)) != self.n_traces:
            raise ValueError("trace state was saved for a different slot count")
        edges = np.asarray(payload["edges"], dtype=np.int64).ravel()
        values = np.asarray(payload["values"], dtype=self.dtype).ravel()
        stamps = np.asarray(payload["stamps"], dtype=np.int64).ravel()
        clock = int(payload["clock"])
        if not 0 <= clock <= np.iinfo(np.int32).max:
            raise ValueError("trace clock is outside the int32 range")
        if not (edges.size == values.size == stamps.size):
            raise ValueError("trace state arrays must have equal length")
        if edges.size and (edges.min() < 0 or edges.max() >= self.n_traces):
            raise ValueError("trace state contains an invalid slot")
        if edges.size > 1:
            ordered = np.sort(edges)
            if np.any(ordered[1:] == ordered[:-1]):
                raise ValueError("trace state contains duplicate slots")
        if not np.all(np.isfinite(values)):
            raise ValueError("trace values must be finite")
        if np.any(stamps < 0) or np.any(stamps > clock):
            raise ValueError("trace stamps must lie between zero and the clock")
        prior = (
            self._value.copy(),
            self._stamp.copy(),
            self._active.copy(),
            self._clock,
        )
        self._value.fill(0)
        self._stamp.fill(-1)
        self._value[edges] = values
        self._stamp[edges] = stamps.astype(np.int32)
        self._active = edges.astype(np.int32)
        self._clock = clock
        expected = payload.get("digest")
        if expected is not None and self.digest() != expected:
            self._value, self._stamp, self._active, self._clock = prior
            raise ValueError("restored trace state does not match its digest")

    def describe(self) -> dict:
        payload = self.sparsity_report()
        payload["digest"] = self.digest()
        payload["increment_unit"] = INCREMENT_UNIT
        return payload


def coincident_edges(
    active_edges, post_spikes, edge_destinations
) -> np.ndarray:
    """Edges whose presynaptic packet arrives while the postsynaptic cell spikes.

    ``active_edges`` are CSR edge indices carrying a presynaptic spike in the
    delivery step; ``edge_destinations[i]`` is the postsynaptic node of CSR
    edge ``i``. The result is a subset of ``active_edges`` in ascending order and
    never an N x N object.
    """
    edges = np.asarray(active_edges, dtype=np.int64).ravel()
    if edges.size == 0:
        return np.empty(0, dtype=np.int64)
    destinations = np.asarray(edge_destinations)
    spikes = np.asarray(post_spikes)
    if edges.max() >= destinations.size:
        raise ValueError("active_edges contains an index outside the edge table")
    if destinations.size and spikes.size <= int(destinations.max()):
        raise ValueError("post_spikes is shorter than the edge destination table")
    return edges[spikes[destinations[edges]]]


class SparseDelayLine:
    """Fixed-delay queue of edge-index packets.

    One entry is pushed per simulation step that carried presynaptic packets.
    ``pop_ready(step)`` returns the packets pushed exactly ``delay_steps``
    earlier, matching the simulator's uniform synaptic delay.
    """

    def __init__(self, delay_steps: int) -> None:
        if isinstance(delay_steps, bool) or not isinstance(
            delay_steps, (int, np.integer)
        ):
            raise ValueError("delay_steps must be an integer")
        if int(delay_steps) < 0:
            raise ValueError("delay_steps must be non-negative")
        self.delay_steps = int(delay_steps)
        self._queue: deque[tuple[int, np.ndarray]] = deque()
        self._last_push_step = -1
        self._n_pushed = 0

    @property
    def pending_packets(self) -> int:
        return len(self._queue)

    @property
    def pending_edges(self) -> int:
        return int(sum(edges.size for _, edges in self._queue))

    @property
    def memory_bytes(self) -> int:
        return int(sum(edges.nbytes for _, edges in self._queue))

    def push(self, step: int, edge_index) -> int:
        step = int(step)
        if step < 0:
            raise ValueError("step must be non-negative")
        if step < self._last_push_step:
            raise ValueError("step must be non-decreasing")
        edges = np.asarray(edge_index, dtype=np.int64).ravel()
        if edges.size == 0:
            return 0
        if edges.min() < 0:
            raise ValueError("edge_index must be non-negative")
        self._queue.append((step, edges))
        self._last_push_step = step
        self._n_pushed += int(edges.size)
        return int(edges.size)

    def pop_ready(self, step: int) -> np.ndarray:
        step = int(step)
        ready: list[np.ndarray] = []
        while self._queue and self._queue[0][0] + self.delay_steps <= step:
            entry_step, edges = self._queue.popleft()
            if entry_step + self.delay_steps != step:
                raise ValueError(
                    f"delay line missed the delivery step for entry at {entry_step}"
                )
            ready.append(edges)
        if not ready:
            return np.empty(0, dtype=np.int64)
        if len(ready) == 1:
            return ready[0]
        return np.concatenate(ready)

    def reset(self) -> None:
        self._queue.clear()
        self._last_push_step = -1
        self._n_pushed = 0

    def describe(self) -> dict:
        return {
            "delay_steps": self.delay_steps,
            "pending_packets": self.pending_packets,
            "pending_edges": self.pending_edges,
            "memory_bytes": self.memory_bytes,
            "edges_pushed": self._n_pushed,
        }


class TraceConfig:
    """The declared ``traces`` section of ``configs/plasticity.yaml``."""

    def __init__(self, payload: dict) -> None:
        body = payload.get("traces")
        if not isinstance(body, dict):
            raise ValueError("traces must be a mapping")
        self.section = body
        self.tau_e_ms = _positive(body.get("tau_e_ms"), "traces.tau_e_ms")
        self.dt_ms = _positive(body.get("dt_ms"), "traces.dt_ms")
        self.prune_threshold = _finite(
            body.get("prune_threshold", 1e-4), "traces.prune_threshold"
        )
        if self.prune_threshold < 0:
            raise ValueError("traces.prune_threshold must be non-negative")
        self.prune_interval_steps = int(body.get("prune_interval_steps", 50))
        if self.prune_interval_steps < 1:
            raise ValueError("traces.prune_interval_steps must be positive")
        self.coincidence = str(body.get("coincidence", "delay_matched"))
        if self.coincidence not in COINCIDENCE_CONVENTIONS:
            raise ValueError(
                f"traces.coincidence must be one of {COINCIDENCE_CONVENTIONS}"
            )
        self.dtype = str(body.get("dtype", "float32"))
        if np.dtype(self.dtype).kind != "f":
            raise ValueError("traces.dtype must be a floating type")
        benchmark = body.get("benchmark", {})
        if not isinstance(benchmark, dict):
            raise ValueError("traces.benchmark must be a mapping")
        self.benchmark = benchmark
        banc = body.get("banc", {})
        if not isinstance(banc, dict):
            raise ValueError("traces.banc must be a mapping")
        self.banc = banc

    def build(self, n_traces: int) -> EligibilityStore:
        return EligibilityStore(
            n_traces,
            tau_e_ms=self.tau_e_ms,
            dt_ms=self.dt_ms,
            prune_threshold=self.prune_threshold,
            dtype=self.dtype,
        )

    def describe(self) -> dict:
        return {
            "tau_e_ms": self.tau_e_ms,
            "dt_ms": self.dt_ms,
            "decay_per_step": round(math.exp(-self.dt_ms / self.tau_e_ms), 12),
            "prune_threshold": self.prune_threshold,
            "prune_interval_steps": self.prune_interval_steps,
            "coincidence": self.coincidence,
            "dtype": self.dtype,
        }


def load_trace_config(path: str | Path) -> TraceConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("plasticity config must be a mapping")
    return TraceConfig(raw)
