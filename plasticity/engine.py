"""Orchestration of traces, prediction error and the weight update.

SCIENTIFIC STATUS
    No scientific claim is made here. The engine applies the declared
    three-factor rule at the declared cadence. Traces are model tags, the
    prediction error is a model error and weights are model variables.

Per step the engine:

1. advances the trace clock once;
2. pops the spike packet delivered at this step (uniform delay);
3. accumulates tags on edges whose presynaptic packet arrives while the
   postsynaptic cell spikes (delay-matched coincidence);
4. pushes the plastic edges of the current spike packet for future delivery;
5. prunes the touched set periodically.

At a reward event the caller supplies the prediction error and the engine
applies ``delta_w = eta * delta_t * e`` to every currently touched edge.
"""

from __future__ import annotations

import numpy as np

from .rules import ThreeFactorRule, UpdateReport
from .traces import EligibilityStore, SparseDelayLine, TraceConfig, coincident_edges
from .weights import WeightState


class PlasticityEngine:
    """Couple an eligibility store, a weight state and a three-factor rule."""

    def __init__(
        self,
        graph,
        weight_state: WeightState,
        rule: ThreeFactorRule,
        trace_config: TraceConfig | None = None,
        *,
        dt_ms: float,
        delay_steps: int,
        enable_traces: bool = True,
        prune_interval_steps: int | None = None,
    ) -> None:
        if not isinstance(weight_state, WeightState):
            raise ValueError("weight_state must be a WeightState")
        if not isinstance(rule, ThreeFactorRule):
            raise ValueError("rule must be a ThreeFactorRule")
        if int(graph.n_edges) != weight_state.n_edges:
            raise ValueError("graph and weight state edge counts differ")
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if int(delay_steps) < 0:
            raise ValueError("delay_steps must be non-negative")
        self.graph = graph
        self.weight_state = weight_state
        self.rule = rule
        self.dt_ms = float(dt_ms)
        self.delay_steps = int(delay_steps)
        self.enable_traces = bool(enable_traces)

        positions = weight_state.plastic_positions
        self.plastic_positions = positions
        self.n_plastic = int(positions.size)
        self.edge_to_slot = np.full(weight_state.n_edges, -1, dtype=np.int32)
        self.edge_to_slot[positions] = np.arange(self.n_plastic, dtype=np.int32)
        self.slot_destinations = np.asarray(
            graph.edge_dst[positions], dtype=np.int64
        )

        self.trace_config = trace_config
        self.prune_interval_steps = (
            int(prune_interval_steps)
            if prune_interval_steps is not None
            else int(getattr(trace_config, "prune_interval_steps", 50))
        )
        if self.prune_interval_steps < 1:
            raise ValueError("prune_interval_steps must be positive")

        if self.enable_traces:
            if trace_config is None:
                raise ValueError("trace_config is required when traces are enabled")
            self.trace_store: EligibilityStore | None = trace_config.build(
                self.n_plastic
            )
            self.delay_line: SparseDelayLine | None = SparseDelayLine(delay_steps)
        else:
            self.trace_store = None
            self.delay_line = None
        self._last_step = -1
        self._n_coincident = 0
        self._n_delivered = 0
        self._n_pushed = 0

    # -- lifecycle ---------------------------------------------------------

    @property
    def traces_enabled(self) -> bool:
        return self.trace_store is not None

    def reset(self) -> None:
        if self.trace_store is not None:
            self.trace_store.reset()
        if self.delay_line is not None:
            self.delay_line.reset()
        self._last_step = -1
        self._n_coincident = 0
        self._n_delivered = 0
        self._n_pushed = 0

    # -- per-step coupling -------------------------------------------------

    def observe_step(self, step: int, spikes, active_csr_edges) -> int:
        """Advance traces and process one simulator step.

        ``active_csr_edges`` are the CSR edges routed into the delay buffer by
        the spike packet of this step. Only plastic edges are retained. Returns
        the number of edges that accumulated a coincident tag.
        """
        step = int(step)
        if step != self._last_step + 1:
            raise ValueError("steps must be presented consecutively from zero")
        self._last_step = step
        if self.trace_store is None or self.delay_line is None:
            return 0
        self.trace_store.advance(1)
        delivered = self.delay_line.pop_ready(step)
        coincident = np.empty(0, dtype=np.int64)
        if delivered.size:
            self._n_delivered += int(delivered.size)
            spikes_array = np.asarray(spikes, dtype=np.int64)
            mask = np.zeros(int(self.graph.n_nodes), dtype=bool)
            mask[spikes_array] = True
            coincident = coincident_edges(
                delivered, mask, self.slot_destinations
            )
            if coincident.size:
                self.trace_store.accumulate(coincident)
                self._n_coincident += int(coincident.size)
        slots = self.edge_to_slot[np.asarray(active_csr_edges, dtype=np.int64)]
        slots = slots[slots >= 0].astype(np.int64)
        if slots.size:
            self.delay_line.push(step, slots)
            self._n_pushed += int(slots.size)
        if (step + 1) % self.prune_interval_steps == 0:
            self.trace_store.prune()
        return int(coincident.size)

    # -- learning ----------------------------------------------------------

    def learn(self, step: int, delta_t: float) -> UpdateReport | None:
        """Apply the three-factor rule to every currently touched edge."""
        if self.trace_store is None:
            return None
        slots = self.trace_store.active_edges.astype(np.int64)
        eligibility = (
            self.trace_store.value(slots) if slots.size else np.empty(0)
        )
        # Trace slots are compact plastic indices; the weight layer is indexed
        # by CSR edge position.
        edges = self.plastic_positions[slots] if slots.size else slots
        return self.rule.apply(
            step, edges, eligibility, delta_t, dt_ms=self.dt_ms
        )

    # -- diagnostics and state --------------------------------------------

    @property
    def n_coincident_tags(self) -> int:
        return int(self._n_coincident)

    @property
    def n_delivered_edges(self) -> int:
        return int(self._n_delivered)

    @property
    def n_pushed_edges(self) -> int:
        return int(self._n_pushed)

    @property
    def memory_bytes(self) -> int:
        total = int(self.edge_to_slot.nbytes + self.slot_destinations.nbytes)
        if self.trace_store is not None:
            total += self.trace_store.memory_bytes
        if self.delay_line is not None:
            total += self.delay_line.memory_bytes
        return total

    def describe(self) -> dict:
        payload = {
            "model": "delay_matched_three_factor_engine",
            "n_plastic_edges": self.n_plastic,
            "dt_ms": self.dt_ms,
            "delay_steps": self.delay_steps,
            "delay_ms": round(self.delay_steps * self.dt_ms, 6),
            "traces_enabled": self.traces_enabled,
            "prune_interval_steps": self.prune_interval_steps,
            "n_pushed_edges": self.n_pushed_edges,
            "n_delivered_edges": self.n_delivered_edges,
            "n_coincident_tags": self.n_coincident_tags,
            "memory_bytes": self.memory_bytes,
        }
        if self.trace_store is not None:
            payload["traces"] = self.trace_store.describe()
        if self.delay_line is not None:
            payload["delay_line"] = self.delay_line.describe()
        return payload
