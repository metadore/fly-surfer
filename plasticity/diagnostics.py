"""JSON-serialisable diagnostics for plastic runs.

Every value here is a measurement of the model, not of a brain. The module
does not import the simulator; callers pass a recorder, a weight state and the
engine.
"""

from __future__ import annotations

import hashlib

import numpy as np


def spike_hash(recorder) -> str:
    """SHA-256 over the exact recorded spike times and neuron indices."""
    times = np.ascontiguousarray(recorder.spike_times_ms)
    neurons = np.ascontiguousarray(recorder.spike_neuron_indices)
    digest = hashlib.sha256()
    digest.update(str(times.dtype).encode("utf-8"))
    digest.update(str(times.shape).encode("utf-8"))
    digest.update(times.tobytes())
    digest.update(str(neurons.dtype).encode("utf-8"))
    digest.update(str(neurons.shape).encode("utf-8"))
    digest.update(neurons.tobytes())
    return digest.hexdigest()


def summarize_updates(reports) -> dict:
    """Aggregate a sequence of per-update reports."""
    items = list(reports)
    if not items:
        return {
            "n_update_events": 0,
            "n_changed_events": 0,
            "sum_abs_applied_pa": 0.0,
            "max_abs_applied_pa": 0.0,
            "clamp_hits": 0,
            "update_clip_hits": 0,
            "sign_violations": 0,
            "decayed_edges": 0,
            "mean_abs_delta_t": 0.0,
            "max_abs_delta_t": 0.0,
        }
    deltas = np.asarray([item.delta_t for item in items], dtype=np.float64)
    applied = np.asarray(
        [item.sum_abs_applied_pa for item in items], dtype=np.float64
    )
    return {
        "n_update_events": len(items),
        "n_changed_events": int(sum(1 for item in items if item.n_updates)),
        "sum_abs_applied_pa": round(float(applied.sum()), 12),
        "max_abs_applied_pa": round(
            float(max(item.max_abs_applied_pa for item in items)), 12
        ),
        "clamp_hits": int(sum(item.clamp_hits for item in items)),
        "update_clip_hits": int(sum(item.update_clip_hits for item in items)),
        "sign_violations": int(sum(item.sign_violations for item in items)),
        "decayed_edges": int(sum(item.decayed_edges for item in items)),
        "mean_abs_delta_t": round(float(np.abs(deltas).mean()), 9),
        "max_abs_delta_t": round(float(np.abs(deltas).max()), 9),
        "records": [item.as_dict() for item in items],
    }


def weight_diagnostics(weight_state, reports=(), *, invariants=None) -> dict:
    payload = weight_state.describe()
    payload["updates"] = summarize_updates(reports)
    if invariants is not None:
        payload["invariants"] = invariants
    return payload


def trace_diagnostics(engine) -> dict:
    if engine is None or not engine.traces_enabled:
        return {
            "enabled": False,
            "reason": "traces disabled by the experiment condition",
        }
    payload = {
        "enabled": True,
        "n_coincident_tags": engine.n_coincident_tags,
        "n_pushed_edges": engine.n_pushed_edges,
        "n_delivered_edges": engine.n_delivered_edges,
        "memory_bytes": engine.memory_bytes,
    }
    payload.update(engine.trace_store.describe())
    return payload


def memory_breakdown(simulator) -> dict:
    """Bytes retained by the plastic simulation components."""
    weights = simulator.weight_state.memory_bytes
    engine = simulator.engine.memory_bytes
    neurons = simulator.neurons.memory_bytes
    synapses = simulator.synapses.memory_bytes
    recorder = simulator.recorder.memory_bytes
    delay = simulator.synapses.delay_buffer_bytes
    # The synapses read the effective weight arrays owned by the weight state;
    # counting them in both components would overstate retained memory.
    shared_effective = int(
        simulator.weight_state.effective_exc.nbytes
        + simulator.weight_state.effective_inh.nbytes
    )
    total = weights + engine + neurons + synapses - shared_effective + recorder

    def mb(value: int) -> float:
        return round(value / 1024**2, 4)

    return {
        "weight_state_bytes": int(weights),
        "engine_bytes": int(engine),
        "neuron_state_bytes": int(neurons),
        "synapse_state_bytes": int(synapses),
        "synapse_arrays_bytes": int(synapses - delay - shared_effective),
        "shared_effective_weight_bytes": shared_effective,
        "delay_buffer_bytes": int(delay),
        "spike_recorder_bytes": int(recorder),
        "retained_arrays_bytes": int(total),
        "components_mb": {
            "weight_state": mb(weights),
            "engine": mb(engine),
            "neuron_state": mb(neurons),
            "synapse_state": mb(synapses),
            "spike_recorder": mb(recorder),
        },
        "retained_arrays_mb": mb(total),
    }
