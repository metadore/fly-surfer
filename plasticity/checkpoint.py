"""Checkpoints and provenance for learned model state.

SCIENTIFIC STATUS
    A checkpoint stores model outputs: learned weight deltas, optional traces
    and the reward predictor state. It is not a biological measurement.

Loading verifies the graph checksum, the policy digest and the invariant
digests of the weight layers. Any mismatch is refused; there is no silent
partial load.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .weights import WeightState, _digest_arrays

FORMAT_VERSION = 1
PHASE = "5D"
MODEL_OUTPUT_LABEL = (
    "learned weights are model outputs of a computational rule, not biological "
    "measurements"
)


def _digest_json(payload: Mapping) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def graph_checksum(graph) -> str:
    """SHA-256 over the structural arrays that define the substrate."""
    arrays = {
        "root_ids": np.asarray(graph.root_ids),
        "out_indptr": np.asarray(graph.out_indptr),
        "edge_src": np.asarray(graph.edge_src),
        "edge_dst": np.asarray(graph.edge_dst),
        "edge_weight": np.asarray(graph.edge_weight),
        "threshold": np.asarray(int(graph.threshold), dtype=np.int64),
    }
    return _digest_arrays(arrays)


def policy_digest(policy) -> str:
    arrays = {
        "neuron_codes": np.asarray(policy.neuron_codes),
        "neuron_signs": np.asarray(policy.neuron_signs),
        "edge_exc_weight": np.asarray(policy.edge_exc_weight),
        "edge_inh_weight": np.asarray(policy.edge_inh_weight),
        "threshold": np.asarray(int(policy.threshold), dtype=np.int64),
    }
    return _digest_arrays(arrays)


def config_digest(config: Mapping) -> str:
    return _digest_json(config)


def save_checkpoint(
    path: str | Path,
    *,
    weight_state: WeightState,
    graph,
    policy,
    config: Mapping,
    trace_store=None,
    predictor=None,
    step: int = 0,
    seed: int | None = None,
    metadata: Mapping | None = None,
) -> dict:
    """Write a checkpoint and return its metadata."""
    if not isinstance(weight_state, WeightState):
        raise ValueError("weight_state must be a WeightState")
    weight_state.assert_invariants()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    trace_state = None
    if trace_store is not None:
        trace_state = trace_store.state_dict()
    predictor_state = None
    if predictor is not None:
        predictor_state = predictor.state_dict()
    payload = {
        "format_version": FORMAT_VERSION,
        "phase": PHASE,
        "label": MODEL_OUTPUT_LABEL,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "step": int(step),
        "seed": None if seed is None else int(seed),
        "graph_checksum": graph_checksum(graph),
        "policy_digest": policy_digest(policy),
        "structural_digest": weight_state.structural_digest(),
        "initial_digest": weight_state.initial_digest(),
        "delta_digest": weight_state.delta_digest(),
        "config": dict(config),
        "config_digest": config_digest(dict(config)),
        "has_traces": trace_state is not None,
        "trace_digest": None if trace_state is None else trace_state["digest"],
        "has_predictor": predictor_state is not None,
        "metadata": dict(metadata or {}),
    }
    arrays = {
        "metadata_json": np.array(json.dumps(payload, sort_keys=True)),
        "delta_exc": weight_state.delta_exc,
        "delta_inh": weight_state.delta_inh,
    }
    if trace_state is not None:
        arrays["trace_edges"] = trace_state["edges"]
        arrays["trace_values"] = trace_state["values"]
        arrays["trace_stamps"] = trace_state["stamps"]
        arrays["trace_clock"] = np.array(trace_state["clock"], dtype=np.int64)
        arrays["trace_n_traces"] = np.array(
            trace_state["n_traces"], dtype=np.int64
        )
    if predictor_state is not None:
        arrays["predictor_json"] = np.array(
            json.dumps(predictor_state, sort_keys=True)
        )
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.replace(path)
    return payload


def load_checkpoint(
    path: str | Path,
    *,
    weight_state: WeightState,
    graph,
    policy,
    trace_store=None,
    predictor=None,
) -> dict:
    """Verify and restore a checkpoint; refuse any identity mismatch."""
    if not isinstance(weight_state, WeightState):
        raise ValueError("weight_state must be a WeightState")
    with np.load(Path(path), allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    payload = json.loads(str(arrays["metadata_json"]))
    if int(payload.get("format_version", -1)) != FORMAT_VERSION:
        raise ValueError("unsupported checkpoint format version")
    if int(payload["step"]) < 0:
        raise ValueError("checkpoint step cannot be negative")
    expected_graph = graph_checksum(graph)
    if payload["graph_checksum"] != expected_graph:
        raise ValueError("checkpoint belongs to a different structural graph")
    expected_policy = policy_digest(policy)
    if payload["policy_digest"] != expected_policy:
        raise ValueError("checkpoint belongs to a different synapse policy")
    if payload["structural_digest"] != weight_state.structural_digest():
        raise ValueError("checkpoint structural counts do not match the graph")
    if payload["initial_digest"] != weight_state.initial_digest():
        raise ValueError("checkpoint initial weights do not match this state")
    incoming = _digest_arrays(
        {
            "delta_exc": np.asarray(arrays["delta_exc"], dtype=np.float32),
            "delta_inh": np.asarray(arrays["delta_inh"], dtype=np.float32),
        }
    )
    if incoming != payload["delta_digest"]:
        raise ValueError("checkpoint learned deltas do not match their digest")
    weight_state.restore_deltas(arrays["delta_exc"], arrays["delta_inh"])
    if weight_state.delta_digest() != payload["delta_digest"]:
        raise ValueError("restored learned deltas do not match their digest")

    restored_traces = False
    if payload.get("has_traces"):
        if trace_store is None:
            raise ValueError("checkpoint contains traces but no trace store was given")
        trace_state = {
            "n_traces": int(arrays["trace_n_traces"]),
            "edges": arrays["trace_edges"],
            "values": arrays["trace_values"],
            "stamps": arrays["trace_stamps"],
            "clock": int(arrays["trace_clock"]),
            "digest": payload.get("trace_digest"),
        }
        trace_store.load_state_dict(trace_state)
        restored_traces = True
    restored_predictor = False
    if payload.get("has_predictor"):
        if predictor is None:
            raise ValueError(
                "checkpoint contains a predictor state but no predictor was given"
            )
        predictor.load_state_dict(json.loads(str(arrays["predictor_json"])))
        restored_predictor = True
    return {
        "metadata": payload,
        "restored_traces": restored_traces,
        "restored_predictor": restored_predictor,
        "weight_digest": weight_state.delta_digest(),
        "effective_digest": weight_state.effective_digest(),
    }
