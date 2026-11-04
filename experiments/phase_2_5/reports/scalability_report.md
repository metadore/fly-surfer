# FLY-SURFER Phase 2.5 — scalability and stability

Generated 2026-11-04T09:58:42+00:00.

**Verdict:** All requested sizes completed.

Protocol: 200 ms simulated, dt = 0.5 ms (400 steps), the same stimulus rule and parameters for every size. Subsets use reproducible connected sampling (seed 42); the full size uses the validated connectome artifact directly. No raw CSV is read.

## Environment

- Python 3.13.14, NumPy 2.3.4
- Platform: Windows-11-10.0.26200-SP0
- 12 logical CPUs, 15.342 GB total RAM
- 1.406 GB available when the report was written

## Scaling results

| Neurons | Edges | Synapses | Init (s) | Sim (s) | Steps/s | Peak WS (MB) | Retained (MB) | Spikes | Active | Mean Hz | Max Hz | Transmissions | Stable |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 800 | 7,500 | 124,693 | 0.0006 | 0.041 | 10,499 | 170.8 | 38.39 | 213 | 78 | 1.331 | 65.0 | 7,843 | yes |
| 5,000 | 121,092 | 1,931,167 | 0.0041 | 0.057 | 7,343 | 171.7 | 41.34 | 145 | 96 | 0.145 | 25.0 | 27,353 | yes |
| 20,000 | 480,107 | 7,414,940 | 0.0179 | 0.331 | 1,230 | 175.8 | 50.83 | 51,387 | 4,551 | 12.847 | 280.0 | 2,903,481 | yes |
| 50,000 | 1,620,531 | 23,785,918 | 0.0820 | 1.060 | 382 | 222.3 | 79.48 | 151,855 | 11,837 | 15.185 | 260.0 | 11,221,306 | yes |
| 139,255 | 3,732,460 | 50,666,648 | 0.1700 | 2.923 | 138 | 270.8 | 134.73 | 349,846 | 33,261 | 12.561 | 250.0 | 23,423,929 | yes |

Throughput moved from 10,499.8 steps/s at 800 neurons to 138.3 steps/s at 139,255 neurons. This reflects per-step work growing with neuron and edge counts; it is not a model-quality comparison.

## Timing decomposition

Recording is a stage inside simulation (spike copy per step), not a separate pass. Sampling and extraction apply only to subsets; graph load is the validated artifact load.

| Neurons | Graph load | Sampling | Extraction | Init | Sim | Recording | Validation | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 0.322 | 0.168 | 0.056 | 0.0006 | 0.041 | 0.0004 | 0.0002 | 0.645 |
| 5,000 | 0.354 | 0.359 | 0.097 | 0.0041 | 0.057 | 0.0004 | 0.0002 | 1.174 |
| 20,000 | 0.327 | 1.209 | 0.287 | 0.0179 | 0.331 | 0.0017 | 0.0046 | 3.206 |
| 50,000 | 0.304 | 3.253 | 1.294 | 0.0820 | 1.060 | 0.0033 | 0.0120 | 9.551 |
| 139,255 | 0.324 | 0.000 | 0.000 | 0.1700 | 2.923 | 0.0059 | 0.0316 | 3.469 |

## Stability validation

Voltage bounds check the configured floor (−90 mV) and threshold (−50 mV). Refractory checks the minimum inter-spike interval. Directional consistency checks that recorded transmissions equal the sum of out-degrees of spiking neurons.

| Neurons | Finite | Voltage bounds | Refractory | Directional | Min V (mV) | Max V (mV) | Min ISI (ms) | Reproducible |
|---:|:---:|:---:|:---:|:---:|---:|---:|---:|:---:|
| 800 | yes | yes | yes | yes | -90.00 | -50.22 | 3.500 | yes |
| 5,000 | yes | yes | yes | yes | -90.00 | -50.13 | 3.000 | — |
| 20,000 | yes | yes | yes | yes | -90.00 | -50.00 | 2.000 | — |
| 50,000 | yes | yes | yes | yes | -90.00 | -50.00 | 2.000 | — |
| 139,255 | yes | yes | yes | yes | -90.00 | -50.00 | 2.000 | — |

## Reproducibility

Size 800 was run twice in separate processes. Activity hash match: **yes**; root-ID set match: **yes**; spike-count match: **yes**; transmission match: **yes**.

## Activity by stimulation

| Neurons | Stimulated | Stim active | Non-stim active | Non-stim spikes | Non-stim share | Stim spikes |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 64 | 64 | 14 | 41 | 19.25% | 172 |
| 5,000 | 64 | 64 | 32 | 38 | 26.21% | 107 |
| 20,000 | 64 | 64 | 4,487 | 50,269 | 97.82% | 1,118 |
| 50,000 | 64 | 64 | 11,773 | 150,439 | 99.07% | 1,416 |
| 139,255 | 64 | 64 | 33,197 | 348,377 | 99.58% | 1,469 |

Non-stimulated share is the fraction of all spikes emitted by neurons that never received the external stimulus. Equal firing does not mean equal health or correctness.

## Memory

| Neurons | Graph | Neuron state | Synapse (excl. delay) | Delay buffers | Recorder | Retained | RSS after sim | Peak WS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 0.15 | 0.0092 | 0.064 | 0.0122 | 38.15 | 38.39 | 88.0 | 170.8 |
| 5,000 | 2.10 | 0.0572 | 0.967 | 0.0763 | 38.15 | 41.34 | 93.7 | 171.7 |
| 20,000 | 8.32 | 0.2289 | 3.835 | 0.3052 | 38.15 | 50.83 | 105.9 | 175.8 |
| 50,000 | 27.21 | 0.5722 | 12.793 | 0.7629 | 38.15 | 79.48 | 133.4 | 222.3 |
| 139,255 | 63.19 | 1.5936 | 29.672 | 2.1249 | 38.15 | 134.73 | 192.5 | 270.8 |

See `memory_report.md` for the component model, temporary-buffer estimates and measurement caveats.

## Full-connectome attempt

- Status: **ok**
- Reason: completed within resources
- Available memory at attempt: 1.997 GB
- Last successful benchmark before the full attempt: n50000 (50,000 neurons)

## Failures and skips

No failed or skipped runs.

## Interpretation

- Retained simulation arrays ranged from 38.39 MB to 134.73 MB; process peaks ranged from 170.8 MB to 270.8 MB.
- Numerical and structural checks passed for every completed size: **yes**.
- Non-stimulated spikes were 19.25%–99.58% of all spikes across completed sizes. They confirm propagation through the sampled graph rather than isolated stimulus-driven firing, but the very high shares at large sizes may also reflect strong excitatory coupling under the model's weight and transmitter assumptions. This is not evidence of biological correctness.
- Activity was not monotonic in size: the 5,000-neuron sample had the lowest mean rate (0.145 Hz; 145 spikes). That rate was no higher than the 800-neuron sample's, so sampled composition can dominate size effects.
- The suite varies size only. It does not establish that any size is biologically correct, and throughput is not a scientific metric.

## Scientific limitations

- Subset benchmarks load the validated full graph before sampling; process peak working set therefore includes the source graph and overstates subset-only process memory.
- Retained array bytes are exact NumPy nbytes for graph and simulation state; they exclude interpreter, allocator and shared-library overhead, and temporary propagation buffers.
- Simulated activity is model output, not measured neural activity. Higher firing rates or spike counts do not indicate better scientific or computational performance.
- The connectome structure is measured (FAFB); membrane, synapse and input parameters remain explicit model assumptions.
- FAFB covers the adult female brain only; motor output and the ventral nerve cord are out of scope in Phase 2.5.
- A single 200 ms protocol and seed cannot characterise all network regimes or long-run stability.

## Reproduce

```bash
python -m experiments.phase_2_5.run_all
python -m experiments.phase_2_5.benchmark --size 5000 \
    --output experiments/phase_2_5/results/benchmark_n5000.json
pytest
```
