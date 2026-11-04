# FLY-SURFER Phase 2.5 — memory report

Generated 2026-11-04T09:58:42+00:00.

## Method

- Retained component bytes are exact NumPy `nbytes` sums: connectome CSR arrays, LIF membrane/refractory state, synapse weights/signs/currents, delay ring buffers and preallocated spike recorder.
- Process RSS and peak working set come from `psutil`. Each benchmark runs in a fresh subprocess, so peaks are not shared across sizes.
- `tracemalloc` is not used: it does not track NumPy data buffers. Retained bytes are therefore the authoritative simulation-state measure.
- No membrane traces or dense adjacency matrices are stored. Only spike times and neuron indices are recorded.

## Components by size

| Neurons | Graph | Neuron state | Synapse (excl. delay) | Delay buffers | Recorder | Retained | RSS after sim | Peak WS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 0.15 | 0.0092 | 0.064 | 0.0122 | 38.15 | 38.39 | 88.0 | 170.8 |
| 5,000 | 2.10 | 0.0572 | 0.967 | 0.0763 | 38.15 | 41.34 | 93.7 | 171.7 |
| 20,000 | 8.32 | 0.2289 | 3.835 | 0.3052 | 38.15 | 50.83 | 105.9 | 175.8 |
| 50,000 | 27.21 | 0.5722 | 12.793 | 0.7629 | 38.15 | 79.48 | 133.4 | 222.3 |
| 139,255 | 63.19 | 1.5936 | 29.672 | 2.1249 | 38.15 | 134.73 | 192.5 | 270.8 |

All values in MB. Peak WS is process peak working set.

## Scaling

- **800 neurons / 7,500 edges:** 21.55 bytes of graph arrays per edge; 8.96 bytes of synapse weights/currents per edge; 16.00 bytes of delay buffers per neuron; 314.02 bytes of structural arrays per neuron; 50,314.02 bytes retained per neuron including the fixed recorder.
- **5,000 neurons / 121,092 edges:** 18.15 bytes of graph arrays per edge; 8.37 bytes of synapse weights/currents per edge; 16.00 bytes of delay buffers per neuron; 670.24 bytes of structural arrays per neuron; 8,670.24 bytes retained per neuron including the fixed recorder.
- **20,000 neurons / 480,107 edges:** 18.17 bytes of graph arrays per edge; 8.37 bytes of synapse weights/currents per edge; 16.00 bytes of delay buffers per neuron; 665.13 bytes of structural arrays per neuron; 2,665.13 bytes retained per neuron including the fixed recorder.
- **50,000 neurons / 1,620,531 edges:** 17.60 bytes of graph arrays per edge; 8.28 bytes of synapse weights/currents per edge; 16.00 bytes of delay buffers per neuron; 866.86 bytes of structural arrays per neuron; 1,666.86 bytes retained per neuron including the fixed recorder.
- **139,255 neurons / 3,732,460 edges:** 17.75 bytes of graph arrays per edge; 8.34 bytes of synapse weights/currents per edge; 16.00 bytes of delay buffers per neuron; 727.27 bytes of structural arrays per neuron; 1,014.52 bytes retained per neuron including the fixed recorder.

## Spike recording bound

The recorder is preallocated at 5,000,000 spikes (38.15 MB) for every size. This is deliberate: recording is bounded and overflow raises `SpikeCapacityExceeded` instead of silently dropping spikes. Because the capacity is fixed, it dominates retained-array memory at small network sizes and is shown separately in the memory plot.

The recorder stores one float32 time and one int32 neuron index per spike. A size-specific capacity can be supplied through `simulation.max_recorded_spikes` when the expected spike count is known; the suite uses one capacity so runs are directly comparable.

## Temporary propagation arrays

Temporary arrays are allocated per step and released: the input current vector, the spike index array, and `np.bincount` outputs for inhibitory and excitatory transmission. The simulator reports bounds:

- `single_hub_propagation_temporary_bytes = 12 * max_out_degree + 24 * n_neurons`
- `worst_case_propagation_temporary_bytes = 12 * n_edges + 24 * n_neurons`

| Neurons | Max out-degree | Single-hub temp (MB) | Worst-case temp (MB) |
|---:|---:|---:|---:|
| 800 | 203 | 0.021 | 0.10 |
| 5,000 | 871 | 0.124 | 1.50 |
| 20,000 | 1,534 | 0.475 | 5.95 |
| 50,000 | 3,147 | 1.180 | 19.69 |
| 139,255 | 6,523 | 3.262 | 45.90 |

## Why process peak overstates subset memory

Every subset run loads the validated full graph to perform sampling and extraction. The source graph is then deleted and garbage collected, but the operating system is not required to return the freed pages immediately. Both the peak working set and the RSS after simulation can therefore include memory attributable to the source graph. The exact `retained_arrays_bytes` is the subset-only figure; process RSS is an upper bound.

For example, at 800 neurons the source graph load reached 152.2 MB RSS while retained arrays were 38.39 MB; at 139,255 neurons the corresponding values were 152.1 MB and 134.73 MB. The full run uses the source graph directly and does not delete it, so its retained arrays legitimately include the graph.

## Full-connectome feasibility

The full graph completed. Retained arrays were 134.73 MB and process peak working set was 270.8 MB.

## Limitations

- RSS includes the Python interpreter, imported libraries and allocator overhead; it is not a pure simulation-state measure.
- NumPy `nbytes` counts logical array sizes, not page-rounded or allocator-retained memory.
- Peak working set is a Windows process metric; values are not directly comparable across operating systems.
- The suite uses one graph artifact and one protocol, so memory scaling is measured for this model, not for spiking simulation in general.
