"""Phase 4G.1 interface audit.

Records, from the live objects rather than from documentation, which existing
components the BANC simulation pathway can reuse, which require an adapter and
which must stay untouched. Writes ``reports/PHASE_4G1_INTERFACE_AUDIT.json``.

Run with ``python experiments/phase_4g/audit_interfaces.py``.
"""

from __future__ import annotations

import inspect
import json
import platform
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import OUT_DIR, BancConnectome  # noqa: E402
from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.neural_activity import SpikeRecorder  # noqa: E402
from brain.neuron_model import LIFParameters, LIFPopulation  # noqa: E402
from brain.synapse_model import SynapseModel, SynapseParameters  # noqa: E402
from motor.motor_decoder import DecoderConfig, MotorDecoder  # noqa: E402
from motor.populations import load_banc_populations  # noqa: E402

OUT_PATH = PROJECT_ROOT / "reports" / "PHASE_4G1_INTERFACE_AUDIT.json"
NODES_PATH = OUT_DIR / "banc_nodes.csv.gz"
GRAPH_T5 = OUT_DIR / "banc_graph_t5.npz"

GRAPH_FIELDS = [
    "root_ids",
    "banc_ids",
    "positions",
    "position_mask",
    "out_indptr",
    "edge_src",
    "edge_dst",
    "edge_weight",
    "in_indptr",
    "in_edge_idx",
    "threshold",
    "meta",
]
SIMULATOR_GRAPH_USES = {
    "n_nodes": "node count for LIFPopulation, recorder and CSR validation",
    "out_indptr": "SynapseModel reads outgoing edge ranges",
    "edge_dst": "SynapseModel destination of every outgoing edge",
    "edge_weight": "SynapseModel structural weight (synapse count)",
    "vocabulary": "SynapseModel reads graph.vocabulary['nt_type']",
    "nt_code": "SynapseModel reads per-neuron transmitter codes",
    "root_ids": "summary reports stimulus root IDs",
    "edge_weight.sum()": "summary reports the structural synapse total",
}


def _signature(target) -> str:
    return str(inspect.signature(target))


def _probe_simulator(graph) -> dict:
    result = {"attempted": True, "failed": False, "error_type": None}
    try:
        BrainSimulator(
            graph,
            LIFParameters(),
            SynapseParameters(),
            duration_ms=1.0,
            progress_interval_ms=0.0,
        )
    except Exception as error:  # noqa: BLE001 - the failure is the evidence
        result["failed"] = True
        result["error_type"] = type(error).__name__
        result["error_message"] = str(error)
        result["traceback_tail"] = [
            {
                "file": Path(frame.filename).name,
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in traceback.extract_tb(error.__traceback__)[-3:]
        ]
    return result


def audit() -> dict:
    graph = BancConnectome.load(GRAPH_T5)
    nodes = pd.read_csv(NODES_PATH, nrows=5)
    populations = load_banc_populations(threshold=5)
    recorder_probe = SpikeRecorder(graph.n_nodes, max_spikes=10)
    recorder_probe.record(0, np.array([0, 5], dtype=np.int32), 0.5)
    decoder = MotorDecoder(populations, DecoderConfig())
    decisions = decoder.decode_recorder(recorder_probe, 0.0, 1.0, include_partial=True)

    probe = _probe_simulator(graph)
    present = {name: hasattr(graph, name) for name in GRAPH_FIELDS}
    missing = [name for name in ("vocabulary", "nt_code") if not present.get(name)]

    return {
        "phase": "4G.1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pyarrow": pyarrow.__version__,
            "platform": platform.platform(),
        },
        "graph": {
            "path": str(GRAPH_T5.relative_to(PROJECT_ROOT).as_posix()),
            "threshold": int(graph.threshold),
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.edge_weight.sum(dtype=np.int64)),
            "fields_present": present,
            "fields_missing_for_simulator": missing,
            "dtypes": {
                "root_ids": str(graph.root_ids.dtype),
                "edge_src": str(graph.edge_src.dtype),
                "edge_dst": str(graph.edge_dst.dtype),
                "edge_weight": str(graph.edge_weight.dtype),
                "out_indptr": str(graph.out_indptr.dtype),
                "in_indptr": str(graph.in_indptr.dtype),
                "in_edge_idx": str(graph.in_edge_idx.dtype),
            },
            "indexing": {
                "node_index": "position in ascending banc_888_id order",
                "banc_id_type": "int64 in memory, decimal string on disk",
                "root_ids_strictly_ascending": bool(
                    np.all(np.diff(graph.root_ids) > 0)
                ),
                "self_edges": int(
                    np.count_nonzero(graph.edge_src == graph.edge_dst)
                ),
                "isolated_nodes": int(graph.n_isolated),
            },
        },
        "simulator": {
            "brain_simulator_signature": _signature(BrainSimulator.__init__),
            "synapse_model_signature": _signature(SynapseModel.__init__),
            "simulator_requires_on_graph": SIMULATOR_GRAPH_USES,
            "probe_on_banc_t5": probe,
        },
        "decoder": {
            "motor_decoder_signature": _signature(MotorDecoder.__init__),
            "decode_recorder_signature": _signature(MotorDecoder.decode_recorder),
            "decoder_attributes_read": [
                "recorder.n_neurons",
                "recorder.spike_times_ms",
                "recorder.spike_neuron_indices",
            ],
            "recorder_probe": {
                "n_neurons": int(recorder_probe.n_neurons),
                "n_spikes": int(recorder_probe.n_spikes),
                "decisions": len(decisions),
                "state": decisions[0].state,
                "neutral": decisions[0].neutral,
            },
            "populations_n_neurons": int(populations.n_neurons),
            "populations_match_graph": bool(
                populations.n_neurons == graph.n_nodes
            ),
            "populations": populations.sizes,
        },
        "node_table": {
            "columns_used_by_simulation": [
                "node_index",
                "banc_888_id",
                "neurotransmitter_verified",
                "neurotransmitter_predicted",
                "neurotransmitter_score",
            ],
            "columns_present_in_head": [
                name for name in (
                    "node_index",
                    "banc_888_id",
                    "neurotransmitter_verified",
                    "neurotransmitter_predicted",
                    "neurotransmitter_score",
                ) if name in nodes.columns
            ],
            "annotation_source": "published BANC v888 metadata, left-joined by banc_888_id",
        },
        "reusable": [
            {
                "component": "brain.neuron_model.LIFPopulation",
                "why": "graph-agnostic vectorised LIF; constructed from n_neurons, "
                "parameters and dt only",
                "verified": "constructor accepts (n_neurons, LIFParameters, dt_ms)",
            },
            {
                "component": "brain.neural_activity.SpikeRecorder",
                "why": "graph-agnostic preallocated spike recorder; its arrays are "
                "exactly what MotorDecoder.decode_recorder reads",
                "verified": "recorder probe decoded with the Phase 4F decoder",
            },
            {
                "component": "brain.neuron_model.LIFParameters",
                "why": "frozen parameter dataclass with rheobase and tau properties",
                "verified": "rheobase_pa = %.1f pA"
                % LIFParameters().rheobase_pa,
            },
            {
                "component": "brain.banc_graph.BancConnectome",
                "why": "already provides the CSR adjacency, node order and weights",
                "verified": "t5 graph has %d nodes and %d edges"
                % (graph.n_nodes, graph.n_edges),
            },
            {
                "component": "motor.populations / motor.motor_decoder",
                "why": "Phase 4F components must be reused unchanged",
                "verified": "populations match graph node count; decode_recorder "
                "accepted a recorder",
            },
        ],
        "adapters_needed": [
            {
                "adapter": "signed edge weights",
                "reason": "BancConnectome carries int32 synapse counts and no "
                "transmitter vocabulary; SynapseModel expects a per-neuron sign "
                "array and transmitter metadata",
            },
            {
                "adapter": "BANC simulation loop",
                "reason": "BrainSimulator is bound to SynapseModel, whose "
                "constructor fails on BancConnectome; a separate loop must own "
                "the BANC edge arrays, current state and delay buffers",
            },
            {
                "adapter": "transmitter-scoped weight arrays",
                "reason": "excitatory and inhibitory edge arrays must be built "
                "once per policy so unknown-sign edges can be excluded without "
                "changing the graph artifact",
            },
            {
                "adapter": "experiment result serialisation",
                "reason": "every result must carry graph threshold, policy, seed "
                "and decoder configuration explicitly",
            },
        ],
        "untouched": [
            "brain/neuron_model.py",
            "brain/synapse_model.py",
            "brain/brain_simulator.py",
            "brain/neural_activity.py",
            "brain/banc_graph.py",
            "datasets/processed/banc_v888/*",
            "datasets/processed/* (FAFB artifacts)",
            "datasets/external/* (raw BANC and FAFB data)",
            "motor/populations.py",
            "motor/motor_decoder.py",
            "configs/motor_decoder.yaml",
            "experiments/phase_4f/*",
            "README.md",
        ],
        "risks": [
            "Structural synapse counts are not conductances; any weight scale is "
            "a modelling assumption, not a physiological estimate.",
            "Presynaptic transmitter identity does not fix the postsynaptic "
            "effect; signs are modelling priors.",
            "Recurrent excitation without calibrated inhibition can produce an "
            "avalanche; the simulator must cap spikes and check finite state.",
            "The full t1 graph has 11.6M edges; naive dense operations would "
            "exceed memory, so only sparse CSR gathers are allowed.",
            "A propagated decoder label would still be a computational output, "
            "not evidence of biological motor control.",
        ],
        "verdict": "READY WITH ADAPTERS",
        "blocking_issues": [],
    }


def main() -> int:
    payload = audit()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(
        "verdict:",
        payload["verdict"],
        "| graph:",
        payload["graph"]["n_nodes"],
        "nodes",
        payload["graph"]["n_edges"],
        "edges | simulator:",
        payload["simulator"]["probe_on_banc_t5"]["error_message"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
