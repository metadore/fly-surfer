# Phase 4G.1 — Interface and Architecture Audit

**Phase:** 4G.1
**Status:** Complete
**Verdict:** **READY WITH ADAPTERS**
**Machine-readable report:** `reports/PHASE_4G1_INTERFACE_AUDIT.json`
**Audit script:** `experiments/phase_4g/audit_interfaces.py`

This audit inspects the live objects, not only their documentation. It was
completed before any Phase 4G implementation file was created.

---

## 1. Existing architecture

| Component | Role | Graph coupling |
|---|---|---|
| `brain.banc_graph.BancConnectome` | BANC CSR graph, node table and manifest | BANC-specific |
| `brain.neural_activity.SpikeRecorder` | Preallocated spike times and neuron indices | None (`n_neurons` only) |
| `brain.neuron_model.LIFPopulation` | Vectorised LIF integration, refractoriness | None (`n_neurons`, parameters, `dt_ms`) |
| `brain.synapse_model.SynapseModel` | Exponential current synapses over outgoing CSR edges | Requires `out_indptr`, `edge_dst`, `edge_weight`, `vocabulary`, `nt_code` |
| `brain.brain_simulator.BrainSimulator` | Time-stepped loop over one `SynapseModel` | Binds the synergy of the four fields above |
| `motor.populations` | Annotation-derived LEFT/RIGHT/JUMP masks | BANC node table only |
| `motor.motor_decoder` | Spike array → abstract action labels | `SpikeRecorder` fields only |

Phase 4F already established that BANC graphs cannot be passed to
`BrainSimulator`. This audit confirms the exact failure location and reproduces
it deterministically.

Graph facts (threshold 5, the Phase 4D primary graph):

| Property | Value |
|---|---:|
| Nodes | 172,433 |
| Edges | 1,535,710 |
| Structural synapses | 18,552,546 |
| Self-edges | 0 |
| Isolated nodes | 24,320 |
| `root_ids` strictly ascending | yes |
| `edge_src` / `edge_dst` | int32 |
| `edge_weight` | int32 (`count`) |
| `out_indptr` / `in_indptr` | int64 |

Indexing is the CSR position of the node in ascending `banc_888_id` order; the
Phase 4F populations use the same order and already assert equality with
`root_ids`.

---

## 2. Exact interface incompatibilities

`BrainSimulator(graph, ...)` constructs `SynapseModel(graph, ...)`. The
constructor reaches line 91 of `brain/synapse_model.py`:

```text
AttributeError: 'BancConnectome' object has no attribute 'vocabulary'
```

`SynapseModel` requires:

| Requirement | BANC provides | Consequence |
|---|---|---|
| `graph.n_nodes` | yes | none |
| `graph.out_indptr` | yes | none |
| `graph.edge_dst` | yes | none |
| `graph.edge_weight` | yes (int32 counts) | usable as a structural weight |
| `graph.vocabulary["nt_type"]` | **no** | immediate constructor failure |
| `graph.nt_code` | **no** | would fail immediately after `vocabulary` |
| per-neuron sign assignment | derived inside `SynapseModel` from the two fields above | must be replaced by a BANC policy |

Two further, non-exception differences matter:

1. `SynapseModel` interprets `edge_weight` through
   `SynapseParameters.weight_transform` with a scale in pA; the BANC graph stores
   integer synapse counts. The interpretation must be declared by Phase 4G.2,
   not inherited implicitly.
2. `BrainSimulator` reports FAFB-specific summary fields (for example
   `source_n_nodes`, `input_schedule`) that do not exist for BANC. Reusing it
   would also force BANC results into an FAFB-shaped schema.

No other incompatibility exists. The failure is confined to the transmitter
vocabulary and the FAFB-shaped loop; the CSR layout itself is compatible.

---

## 3. Reusable components

| Component | Reuse | Evidence |
|---|---|---|
| `LIFPopulation` | Reused unchanged for every BANC simulation | Constructor `(n_neurons, LIFParameters, dt_ms)` has no graph parameter; `rheobase_pa = 150 pA`, `tau_m_ms = 20` |
| `LIFParameters` | Reused unchanged | Frozen dataclass with validated defaults |
| `SpikeRecorder` | Reused unchanged | Constructor `(n_neurons, max_spikes)`; `record(step, indices, dt)`; arrays are float32 times and int32 indices |
| `BancConnectome` | Reused unchanged, loaded read-only | CSR, node order, weights and manifest already exist |
| `MotorPopulations` | Reused unchanged | `n_neurons` equals the graph node count; masks assert node order |
| `MotorDecoder.decode_recorder` | Reused unchanged | The audit fed it a probe `SpikeRecorder` and received a decision |
| `verify_manifest`, `snapshot_paths`, `sha256_file` | Reused unchanged | Integrity tooling already written and tested |

The audit's recorder probe recorded two spikes and the Phase 4F decoder returned
a NEUTRAL decision without modification, confirming the recorder contract.

---

## 4. Components requiring adapters

| Adapter | Why it is required | Planned owner |
|---|---|---|
| Transmitter sign policy | BANC has verified and predicted transmitters but no per-edge sign and no `nt_code` | `brain/banc_synapse_policy.py` |
| Signed edge arrays | Excitatory and inhibitory float32 edge arrays must be built once per policy and threshold | `banc_synapse_policy.py` |
| BANC simulation loop | Must own the CSR gathers, current state, delay buffers, spike cap and finite-state checks without touching `BrainSimulator` | `brain/banc_simulator.py` |
| Activity adapter | Must expose the recorded spikes to the Phase 4F decoder without altering timestamps or indices | `brain/banc_simulation_adapter.py` (thin layer, mostly validation) |
| Result serialisation | Must record threshold, policy, transformations, seed and decoder configuration in every result | `banc_simulator.py` |

The adapters live beside the existing modules and import them; the existing
modules import nothing from Phase 4G.

---

## 5. Components that must remain untouched

- `brain/neuron_model.py`, `brain/synapse_model.py`, `brain/brain_simulator.py`,
  `brain/neural_activity.py`, `brain/banc_graph.py`
- Phase 4D artifacts under `datasets/processed/banc_v888/`
- Phase 4E reports and analysis outputs
- `motor/populations.py`, `motor/motor_decoder.py`, `configs/motor_decoder.yaml`
- `experiments/phase_4f/` and its results
- FAFB artifacts, raw BANC and FAFB datasets, manifests and checksums
- Root `README.md`

Byte-for-byte hashes for all of these were recorded before implementation in
`experiments/phase_4g/baseline_integrity.json`.

---

## 6. Proposed BANC simulation architecture

```text
BancConnectome (t1 | t5 | t10, read-only)
        │
        ├── node table (annotations, verified / predicted transmitter)
        │        │
        │        v
        │   BancSynapsePolicy  ──> per-neuron sign class
        │        │                 (verified-excitatory / verified-inhibitory /
        │        │                  conflict / verified-modulator-only /
        │        │                  predicted-only / unannotated)
        │        v
        │   signed edge weights  exc_weight[], inh_weight[]  (float32)
        │
        v
   BancSimulator (separate loop)
        ├── LIFPopulation (reused, unmodified)
        ├── SpikeRecorder (reused, unmodified)
        ├── sparse CSR gather + bincount per timestep
        ├── delay buffers (deque of float32 arrays)
        ├── external current injection / seeded noise
        └── finite-state and spike-cap checks
        │
        v
   BancActivityAdapter ──> same recorder object (no copy, no retiming)
        │
        v
   MotorDecoder (Phase 4F, unchanged) ──> LEFT / RIGHT / JUMP / NEUTRAL
```

Design constraints carried into implementation:

1. Only sparse CSR gathers and `bincount` are used; no dense adjacency is ever
   allocated.
2. Only one threshold graph is resident at a time.
3. Every result records `graph_threshold`, `sign_policy`, `weight_transform`,
   `weight_scale`, `dt_ms`, `duration_ms` and `seed`.
4. Unknown-sign edges are excluded from the primary signed simulation and
   counted, never assigned an arbitrary sign.
5. The simulation loop raises on non-finite state or recorder overflow rather
   than truncating silently.

---

## 7. Scientific risks

1. **Synapse count is not conductance.** The edge weight is a structural count;
   the pA scale is an assumption declared in Phase 4G.2 and tested for
   sensitivity.
2. **Transmitter identity is not effect.** Excitatory and inhibitory labels are
   modelling priors. Cotransmission, receptor kinetics and neuromodulation are
   not modelled.
3. **Predicted transmitters are not verified transmitters.** They are kept as a
   separate sensitivity condition and never silently merged into the primary
   policy.
4. **Recurrent avalanche.** A large recurrent network with compressed weights can
   either die immediately or saturate. The simulator must measure both failure
   modes and report them rather than tune them away.
5. **Structural propagation is not behaviour.** A decoded label after
   propagation remains a computational output.
6. **Threshold mixing.** t1, t5 and t10 must remain separate conditions with the
   threshold recorded in every result.

---

## 8. Implementation readiness verdict

**READY WITH ADAPTERS.**

The only blocking incompatibility is the transmitter vocabulary, and it is fully
explained: `SynapseModel` needs `graph.vocabulary` and `graph.nt_code`, which
`BancConnectome` does not have. The neuron model and the spike recorder are
graph-agnostic and reusable without modification. The CSR layout, node ordering
and motor-population indices are aligned with the Phase 4F decoder.

Phase 4G.2 (transmitter-sign and edge-weight policy) can proceed. No existing
file needs to change to unblock it.
