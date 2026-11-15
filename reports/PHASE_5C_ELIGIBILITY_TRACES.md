# Phase 5C — Sparse Edge-Indexed Eligibility Traces

**Status:** complete
**Date:** 2026-11-09
**Repository:** FLY-SURFER
**Preceding phase:** 5B (reward and prediction error)
**Successful:** all declared 5C checks pass; the wall-clock comparison is a
recorded negative (Section 7.4)
**Scope:** sparse per-edge eligibility traces, coincidence selection, a sparse
delay line and a trace benchmark at synthetic sizes and at the BANC t5 edge
count. No neuron is simulated and no weight is modified.

---

## 1. Purpose

Phase 5C supplies the per-synapse tag that the three-factor rule of Phase 5D
will multiply by a reward prediction error. The tag must satisfy four
constraints from the approved 5A architecture:

- it is indexed by a CSR edge slot, never by a neuron pair;
- no `N x N` object is ever allocated;
- decay is lazy or otherwise sparse, so the cost of a step follows the number
  of active edges rather than the total edge count;
- storage, update complexity and reset behaviour are measured, not asserted.

The trace layer is independent of the reward layer and of `brain/`. It maps an
edge slot to an identity; Phase 5D decides that a slot means one verified-sign
CSR edge.

---

## 2. Scientific status and non-claims

| Element | What it is | What it is not |
|---|---|---|
| `EligibilityStore` | a short-lived scalar tag per modelled edge | not a measured synaptic eligibility trace |
| `tau_e_ms` | a declared model time constant (20 ms in the config) | not a fitted biological time constant |
| `increment` | one unit per coincident pre/post pair in the declared convention | not a quantal synaptic event count |
| `SparseDelayLine` | a queue reproducing the simulator's uniform 1 ms delay | not a model of axonal conduction |
| `coincident_edges` | a set intersection between arriving packets and postsynaptic spikes | not a plasticity mechanism by itself |
| lazy decay | an implementation of `lambda = exp(-dt / tau_e)` | not evidence that biological tags decay exponentially |

No learning curve, weight change or behavioural claim is made in this phase.
The trace is a model variable with arbitrary units.

---

## 3. Implemented interfaces

| ID | Interface | Implementation |
|---|---|---|
| M04 | eligibility store | `plasticity/traces.py`: `EligibilityStore` with `accumulate`, `value`, `decay`, `advance`, `prune`, `reset`, `memory_bytes`, `sparsity_report`, `digest` |
| M05 | trace benchmark and sparse-index contract | `experiments/phase_5/benchmark_traces.py`; measured storage, runtime, update complexity, reset and edge mapping against the CSR layout |

### 3.1 Modules

```
plasticity/traces.py                    EligibilityStore, SparseDelayLine,
                                        coincident_edges, TraceConfig,
                                        load_trace_config
plasticity/__init__.py                  exports the 5B and 5C layers
configs/plasticity.yaml                 new traces section (reward sections
                                        unchanged)
experiments/phase_5/benchmark_traces.py synthetic and BANC benchmark
tests/test_plasticity_traces.py         48 focused tests
```

`brain/`, `motor/`, `sensory/`, `perception/` and the existing tests are
untouched. The package still imports no simulator, motor or graph module.

### 3.2 Trace contract

```python
e_ij(t) = lambda * e_ij(t-1) + f(pre_i, post_j)
lambda  = exp(-dt_ms / tau_e_ms)
```

- `accumulate(edges)` applies the decayed value at the current clock and adds
  the increment; it returns the number of edges updated.
- `value(edges)` returns the value decayed to the requested step, and rejects
  reads that precede the current clock.
- `advance(steps)` only moves the clock; `decay(dt_ms)` must be an integer
  multiple of the configured step.
- Duplicate edge indices in one call are rejected; the caller passes a unique
  packet set.
- Non-finite or negative increments and float32 overflow are rejected before
  any stored value is written.
- `reset()` zeroes values, clears stamps and the touched list and resets the
  clock.

---

## 4. Storage design and lazy decay

Per edge the store keeps:

| Array | dtype | Bytes per edge |
|---|---|---|
| value | float32 | 4 |
| last-write stamp | int32 | 4 |
| active slot list | int32 | 4 per *touched* edge, appended once |

`advance` is O(1). Reads and updates materialise `lambda ** (clock - stamp)` for
the requested slots only. A periodic `prune` removes touched entries whose
decayed value is below the declared threshold. Storage is linear in the number
of trace slots and touched edges; there is no pairwise object anywhere, and the
benchmark asserts that all three arrays are one-dimensional.

At the BANC t5 plastic edge count (683,100 verified-sign edges) the compact
capacity is **5,464,800 bytes (5.21 MiB)**, versus 12,285,680 bytes (11.72 MiB)
if every one of the 1,535,710 CSR edges carried a trace and 2,732,400 bytes for
a float32-only dense value array over the plastic edges.

---

## 5. Edge indexing, coincidence and delay

- `coincident_edges(active_edges, post_spikes, edge_destinations)` returns the
  subset of CSR edges whose destination neuron spiked in the delivery step. It
  is a vectorised gather, not a matrix product.
- The BANC simulator applies a uniform 1 ms synaptic delay (2 steps at
  `dt = 0.5 ms`). `SparseDelayLine(2)` stores packets by step and returns them
  exactly two steps later; a missed delivery step raises instead of silently
  dropping packets.
- The configured convention is `delay_matched`: a presynaptic spike at step `t`
  forms a tag only if the postsynaptic cell spikes at the packet delivery step
  `t + 2`. The `same_step` convention exists for comparison and is not the
  default.
- The two-neuron test creates a tag at the delivery step with value `1.0` and
  then verifies closed-form decay over five further steps.

---

## 6. Configuration

`configs/plasticity.yaml`, SHA-256
`1c732d81b4f5a3a668555696ad9953c1dacae2a4a99a1a74181d9905067d40ab`
(the 5B reward sections are unchanged; this hash is the post-5C file).

| Key | Value |
|---|---|
| `traces.tau_e_ms` | 20.0 |
| `traces.dt_ms` | 0.5 |
| `traces.decay_per_step` | `exp(-0.025) = 0.975309912028` |
| `traces.prune_threshold` | 1e-4 |
| `traces.prune_interval_steps` | 50 |
| `traces.coincidence` | `delay_matched` |
| `traces.dtype` | float32 |
| `traces.benchmark.sizes` | 1,000; 10,000; 100,000; 683,100; 1,535,710 |
| `traces.benchmark.n_steps` | 600 |
| `traces.benchmark.active_fraction_per_step` | 0.01 |
| `traces.benchmark.reward_read_steps` | 150, 300, 450 |
| `traces.benchmark.seed` | 20261112 |
| `traces.banc.n_steps` | 200 |
| `traces.banc.active_fraction_per_step` | 0.001 |
| `traces.banc.seed` | 20261113 |

All values were fixed before the benchmark. The 5B sections and their hash are
recorded in `reports/PHASE_5B_REWARD_SYSTEM.md`.

---

## 7. Validation

Run: `python -m experiments.phase_5.benchmark_traces`
Result: `experiments/results/phase_5c/trace_benchmark.json`
Total wall time: 14.36 s.

### 7.1 Declared checks

| Check | Result | Evidence |
|---|---|---|
| `lazy_matches_dense_reads` | pass | sparse and dense trace reads agree within 1e-5 at every measured size |
| `no_pair_matrix` | pass | value, stamp and active arrays are one-dimensional at every size |
| `sparse_work_scales_with_active_edges` | pass | per-step updates equal `n_edges x active_fraction` within 5% in every synthetic row and both activity regimes |
| `touched_list_bounded` | pass | touched slots never exceed the slot count |
| `banc_mapping` | pass | 2,000 sampled plastic slots are sorted, signed and inside the node range; source signs and exc/inh weights match the policy arrays |
| `banc_count_matches_policy` | pass | 683,100 plastic edges equals `policy.coverage["signed_edges"]` |
| `banc_storage_bounded` | pass | compact capacity 5.21 MiB is below the 20 MiB budget |
| `banc_delay_line_complete` | pass | 136,523 packets pushed and 136,523 delivered; none pending |
| `no_simulation` | pass | `simulated_neurons: false`, `weights_modified: false` |

`all_checks_passed: true`. The quick mode (`--quick`, sizes up to 100,000 and
60 steps) passes the same checks in 3.45 s.

### 7.2 Synthetic sizes

600 steps, active fraction 1%, reward reads at steps 150/300/450, decimation:

| Edges | Sparse | Dense reference | Speedup | Store memory | Dense value only | Memory ratio | Updates |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 0.058 s | 0.013 s | 0.22x | 11,900 B | 4,000 B | 2.98x | 5,970 |
| 10,000 | 0.076 s | 0.018 s | 0.24x | 119,008 B | 40,000 B | 2.98x | 59,710 |
| 100,000 | 0.262 s | 0.080 s | 0.30x | 1,190,968 B | 400,000 B | 2.98x | 597,032 |
| 683,100 | 1.627 s | 0.677 s | 0.42x | 8,135,276 B | 2,732,400 B | 2.98x | 4,078,190 |
| 1,535,710 | 4.356 s | 1.963 s | 0.45x | 18,289,896 B | 6,142,840 B | 2.98x | 9,168,195 |

Per-step sparse cost rises from 0.097 ms at 1,000 edges to 7.26 ms at
1,535,710 edges; the per-update cost is 0.40–0.48 µs above 100,000 edges.
Trace reads agree with the dense reference at every reward step.

### 7.3 Activity regime

Same size (1,535,710 edges), 100 steps, two activity levels:

| Active fraction | Sparse | Dense | Speedup | Decay-work ratio |
|---:|---:|---:|---:|---:|
| 1.0% | 0.529 s | 0.333 s | 0.63x | 100.5x |
| 0.1% | 0.073 s | 0.062 s | 0.84x | 1,000.3x |

The sparse store performs 100–1,000 times fewer per-edge decay operations
because it never multiplies untouched edges. As activity falls, the measured
gap narrows toward parity.

### 7.4 Wall-clock result (negative, preserved)

**The lazy store was slower than the vectorised dense multiply at every
measured size and activity level in this run.** It is not presented as a
speedup. The reason is implementation dominance, not algorithmic work: the
dense baseline decays the whole array in one NumPy pass, while the sparse path
pays several Python/NumPy calls per step and per-update validation
(duplicate check, finite/negative checks, `where` chains and `lambda ** steps`)
on small arrays. The dense baseline also does 100–1,000 times more arithmetic,
which only becomes visible when the arrays are large and the activity is not
extremely low.

What the benchmark establishes:

- the trace work scales with active edges, not with total edges;
- no `N x N` object exists and all per-edge arrays are linear;
- lazy and dense reads agree exactly (within 1e-5);
- at BANC scale the trace step costs 0.37 ms per step at 0.1% activity;
- the lazy store uses about 3x the value-only dense memory.

For context only, a Phase 4G BANC t5 smoke step was measured at 3.7 ms/step
(272 steps/s). The trace layer at 0.37 ms/step is roughly 10% of that step in
this measurement; the two were measured in different runs and this is an
order-of-magnitude comparison, not a profiled decomposition.

### 7.5 BANC t5

| Measure | Value |
|---|---|
| graph | `datasets/processed/banc_v888/banc_graph_t5.npz` |
| graph SHA-256 | recorded in the JSON result |
| nodes / edges / synapses | 172,433 / 1,535,710 / 18,552,546 |
| policy | `configs/banc_synapse_policy.yaml`, SHA-256 recorded |
| verified-sign (plastic) edges | 683,100 (44.48% of edges) |
| compact capacity | 5,464,800 B (5.21 MiB) |
| all-edge capacity | 12,285,680 B (11.72 MiB) |
| dense plastic value only | 2,732,400 B (2.61 MiB) |
| sparse run, 200 steps at 0.1% | 0.074 s (0.37 ms/step) |
| dense run, same activity | 0.031 s |
| delay line | 136,523 pushed, 136,523 delivered, 0 pending, 0.022 s |
| graph load and policy build | 3.36 s |

The BANC section reads the graph and policy only; it simulates no neuron and
changes no array. The plastic slot set is derived from the policy's non-zero
excitatory/inhibitory weights, not from an independent re-derivation, and the
mapping check samples source signs and edge weights to confirm consistency.

### 7.6 Numerical behaviour

- float32 overflow in `accumulate` raises `FloatingPointError` before writing.
- Non-finite and negative increments raise `ValueError`.
- Duplicate or out-of-range edge indices raise `ValueError`.
- Reads at a step before the current clock raise `ValueError`.
- The clock is guarded against int32 timestamp overflow.

---

## 8. Tests

| Suite | Result |
|---|---|
| `tests/test_plasticity_traces.py` (new) | **48 passed in 0.30 s** |
| focused (`traces`, `reward`, `configs`) | **112 passed in 1.54 s** |
| full suite | **601 passed in 30.42 s** |

The 48 focused tests cover: construction and validation; the decay constant;
accumulation and closed-form decay; rejection of reads in the past; integer
decay steps; reset; duplicate and out-of-range edges; array increments;
non-finite and negative increments; float32 overflow rejection; pruning;
lazy-versus-manual decay over a tracked clock; coincidence with no activity,
pre only, post only and both; the delay line at 0 and 2 steps and its missed
delivery guard; the two-neuron delay-matched case; linear memory; digest
determinism and decay sensitivity; configuration loading and rejection; and
the missing-section path.

No existing test was modified.

---

## 9. Resources

| Measure | Value |
|---|---|
| benchmark wall time | 14.36 s |
| largest trace capacity | 12,285,680 B (11.72 MiB) for 1,535,710 slots |
| BANC compact capacity | 5,464,800 B (5.21 MiB) |
| BANC store after 200 steps | 5,959,280 B; 123,620 touched slots |
| Python / NumPy | 3.13.14 / 2.3.4 |
| data touched | BANC t5 graph and policy, read-only |
| weights modified | false |
| neurons simulated | false |

The benchmark is single-run on a shared desktop CPU; the timings are
indicative and are not a statistical benchmark.

---

## 10. Integrity

Phase 4H protected-file integrity: **37/37 unchanged**, including root
`README.md`, Phase 4H reports and results, datasets and processed connectomes.

No file in `brain/`, `motor/`, `sensory/`, `perception/`, `experiments/phase_4*`
or the existing `tests/` was modified.

---

## 11. Files created and modified

Created:

- `plasticity/traces.py`
- `experiments/phase_5/benchmark_traces.py`
- `experiments/results/phase_5c/trace_benchmark.json`
- `tests/test_plasticity_traces.py`
- `reports/PHASE_5C_ELIGIBILITY_TRACES.md`
- `reports/PHASE_5C_ELIGIBILITY_TRACES.json`

Modified:

- `plasticity/__init__.py` (adds trace exports)
- `configs/plasticity.yaml` (adds the `traces` section)
- `tests/test_plasticity_reward.py` (renames one package-isolation test so it
  still describes the expanded export list; assertions unchanged)

No commit or push was made.

---

## 12. Limitations

1. Active edges are drawn uniformly at random. They do not come from a
   simulated spike pattern, so the benchmark measures the store, not a network.
2. The lazy store was slower in wall-clock time than the vectorised dense
   reference in this run at every measured size and activity (Section 7.4).
   The result is preserved; it is a property of this Python implementation.
3. The lazy store uses about 3x the value-only dense memory (value, timestamp
   and touched list). It is not a memory reduction over a float32 value array.
4. At 1% activity over 600 steps nearly every edge is touched, so the touched
   list approaches the full slot count. Memory stays linear, but pruning is
   effective only when activity is low or the run is short.
5. Timings are a single run on one machine. No variance, confidence interval or
   multi-machine comparison is claimed.
6. Only two activity levels were measured in the regime table; intermediate
   activities and spike-derived activities remain unmeasured.
7. The delay line models the simulator's uniform 1 ms delay only. It does not
   model distributed conduction delays.
8. `tau_e` is declared, not fitted. No claim is made that 20 ms is the
   biological time constant of any synapse in this connectome.

---

## 13. Exit criteria

| 5C requirement | Status |
|---|---|
| sparse edge-indexed trace store | implemented (`EligibilityStore`) |
| no dense `N x N` allocation | enforced and asserted in the benchmark |
| `e <- lambda*e + f`, `lambda = exp(-dt/tau_e)` | implemented and tested |
| creation, accumulation and decay | implemented and tested |
| reset | implemented and tested |
| pre-only, post-only and coincident activity | tested |
| delayed reward compatible | delay-matched convention and delay line tested |
| edge indexing consistency | tested and checked against the CSR policy |
| lazy or sparse decay | implemented (lazy) |
| memory and runtime measurement | measured at five sizes and BANC t5 |
| BANC t5 benchmark | completed read-only at 683,100 plastic edges |
| module, config, tests, runner, reports | all delivered |

Phase 5C passes its declared checks. The wall-clock comparison is a recorded
negative and is carried forward as a limitation of the implementation. The
lazy store is retained because its per-step work follows active edges, does
not materialise decay over untouched edges and allocates no pairwise object.
Proceeding to Phase 5D (three-factor plasticity).
