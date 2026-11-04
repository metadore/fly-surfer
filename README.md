# FLY-SURFER

A spiking neural simulation layer built on the validated FlyWire FAFB connectome.
The connectome supplies **measured structure**; the membrane, synapses, sign
assignments and input protocol are **explicit model assumptions**. Simulated
activity is not a recording and does not reproduce real fly neural activity.

## Status

| Layer | State |
|---|---|
| Phase 0 dataset audit | Complete; 11/11 audit checks and 8/8 round-trip checks passed |
| Phase 1 connectome artifact | Verified and treated as read-only |
| Phase 2 spiking simulation | Complete: LIF neurons, sparse synapses, activity recording, experiment, tests |
| Phase 2.5 scalability benchmark | Complete: 800 → 139,255 neurons; full connectome stable; memory and speed reports |
| Reinforcement learning / plasticity / game controls | Not started |

Verified structural facts: 139,255 neurons, 3,732,460 directed edges,
50,666,648 summed synapses, 671 isolated neurons, zero self-connections,
620,180 reciprocal directed pairs, ascending-root-ID node indices, pair-level
>=5-synapse threshold. See `datasets/README.md` and
`datasets/processed/connectome_report.json` for provenance and audit details.

## Scientific status of each layer

| Category | What it includes |
|---|---|
| Measured structure | Directed adjacency, summed synapse count per pair, root IDs, positions, predicted cell annotations |
| Predicted annotations | `nt_type`, super-class, class and side labels from FlyWire-derived predictions |
| Assumed physiology | LIF capacitance, leak, rest, threshold, reset, refractory and membrane floor; transmitter sign rules; synaptic time constants; uniform 1 ms delay |
| Computational approximations | Structural synapse counts transformed to current by `12 * count ** 0.75` pA; no receptor saturation, short-term plasticity, neuromodulation or morphology; spikes quantised to 0.5 ms |
| Controlled input | Experimenter current injection into 64 selected neurons, not sensory stimulation |
| Simulated activity | Model output only; not evidence of reproducing the living fly |

Synapse counts are **never** interpreted as measured physiological weights.
The power-law scale is a calibration choice for the model current regime.

## Quick start

Dependencies: Python 3.13, NumPy, pandas, PyYAML, matplotlib, psutil and pytest.
The validated artifact must exist at `datasets/processed/connectome.npz`.

```bash
# Reproduce the Phase 2 experiment (800 neurons, 1 s biological time)
python main.py --no-progress

# Equivalent direct entry point
python -m experiments.baseline

# Reproduce the Phase 2.5 scalability suite and reports
python -m experiments.phase_2_5.run_all

# Regenerate plots/reports from existing benchmark JSON files
python -m experiments.phase_2_5.run_all --reports-only

# Run the automated tests
python -m pytest -q
```

`pytest.ini` disables the `anyio` plugin because this environment ships an
incompatible anyio/trio pair under Python 3.13; none of the tests are async.

## Architecture

| File | Responsibility |
|---|---|
| `brain/connectome_loader.py` | Loads the validated `.npz` artifact and exposes read-only CSR adjacency plus annotations. Unmodified by Phase 2. |
| `brain/neuron_model.py` | Vectorised LIF population with exact exponential-Euler passive integration, threshold/reset, refractory period and membrane floor. |
| `brain/synapse_model.py` | Sparse CSR spike propagation, sign assignment, weight transform, exponential currents and delayed delivery. |
| `brain/subgraph.py` | Induced subgraph extraction with local indices and reproducible connected sampling. |
| `brain/neural_activity.py` | Preallocated spike recorder, firing-rate summaries, raster and rate plots. |
| `brain/brain_simulator.py` | Time-stepped loop, external stimulation, diagnostics, deterministic seeds and result saving. |
| `experiments/baseline.py` | Reproducible experiment, metadata, performance metrics, report and CLI. |
| `experiments/phase_2_5/benchmark.py` | One size per process: sampling or full graph, stage timing, validation, memory and JSON result. |
| `experiments/phase_2_5/run_all.py` | Suite orchestration, subprocess isolation, timeouts, reproducibility check, plots and reports. |
| `experiments/phase_2_5/configs/scalability_suite.yaml` | Benchmark sizes, protocol, sampling and resource preflight. |
| `configs/neuron_config.yaml` | Assumed LIF parameters. |
| `configs/simulation_config.yaml` | Connectome path, timestep, synapse transform, input protocol and experiment settings. |
| `tests/` | 68 automated tests covering dynamics, synapses, sampling, recording, simulation, configs, artifact compatibility and benchmark failure handling. |

## Model definition

Each neuron is a point LIF unit:

```text
C_m dV/dt = -g_L (V - E_L) + I_syn + I_ext
```

The passive part uses the exact exponential-Euler update

```text
V(t+dt) = E_L + (V(t)-E_L) exp(-dt/tau_m) + I (1-exp(-dt/tau_m)) / g_L
```

so the integration is stable for any positive timestep. Threshold crossing is
checked at the end of a step, spikes reset the membrane, and the refractory
period is rounded up to whole timesteps. A configurable floor (`-90 mV`)
represents unmodelled leak and voltage-gated currents; without it, sustained
inhibition can drive a purely passive membrane to non-physiological values.

Synaptic propagation is sparse. A presynaptic spike indexes its outgoing CSR
rows; destination currents are accumulated with `numpy.bincount`. No dense
N x N matrix is built. Each edge inherits the assumed sign of its presynaptic
neuron:

- ACH and GLUT: excitatory
- GABA: inhibitory
- DA, SER, OCT: configurable, excitatory in this run
- unlabeled or unknown: configurable, excitatory in this run

Currents decay exponentially (`tau_exc = 5 ms`, `tau_inh = 8 ms`). A uniform
1 ms delay is implemented with separate excitatory and inhibitory ring buffers.
The net synaptic current is `I_exc - I_inh`. The structural synapse count `w`
becomes `12 * w ** 0.75` pA for this calibrated run; this is an approximation,
not a measured conductance or reversal potential.

## Reproducible experiment

Settings in `configs/simulation_config.yaml`: 800 neurons sampled with seed 42,
1,000 ms at 0.5 ms timesteps (2,000 steps), simulation seed 20261104, no
background current or noise. Sixty-four highest-degree neurons receive 180 pA
from 100 to 800 ms. The sample is grown as a connected snowball from
class-stratified candidate hubs; the candidate whose super-class and
neurotransmitter composition is closest to the eligible population is kept.
It is not the first N neurons.

Measured run summary (`experiments/results/initial/`):

| Quantity | Result |
|---|---|
| Sampled neurons | 800 |
| Internal directed edges | 7,500 |
| Internal summed synapses | 124,693 |
| Weakly connected components | 1 |
| Structural synapses per edge: median / 95th / max | 9 / 47 / 2,633 |
| Excitatory / inhibitory edges | 5,149 / 2,351 |
| Excitatory / inhibitory neurons | 685 / 115 |
| Effective synaptic delay | 1.0 ms |
| Spike-to-edge transmissions | 55,319 (35.37 per spike) |
| Spikes | 1,564 |
| Active / silent neurons | 79 / 721 (9.88% active) |
| Mean firing rate | 1.96 Hz |
| Per-neuron rate: 95th / 99th / max | 12 / 60 / 111 Hz |
| Peak 10 ms population rate | 8.25 Hz |
| Stimulated neurons active | 64 / 64 (1,193 spikes) |
| Non-stimulated neurons active | 15 (371 spikes; 23.7% of all spikes) |

The 15 active non-stimulated neurons show that recurrent synaptic transmission
recruits activity beyond the directly injected cells in this seeded run. This
is a property of the model, not a measurement of the fly.

## Performance

| Metric | Result |
|---|---|
| Connectome load | 0.325 s |
| Connected sampling | 0.319 s |
| Simulation | 0.508 s for 2,000 steps (3,936 steps/s) |
| End-to-end experiment wall time | 7.66 s (includes imports, plots and report) |
| Resident memory before simulation | 162.5 MB |
| Peak process working set | 230.4 MB |
| Peak traced Python allocations | 106.2 MB |

The simulation keeps only CSR adjacency, per-edge weights, ring buffers of size
`n_neurons`, membrane state and a preallocated spike recorder. Phase 2.5
measures how those arrays and the per-step loop scale.

## Phase 2.5 scalability and stability

The suite runs 800, 5,000, 20,000 and 50,000 neurons through the same
reproducible connected sampling used in Phase 2 (seed 42), plus the full
139,255-neuron connectome directly from the validated artifact. Each size runs
in a fresh process. The protocol is 200 ms at 0.5 ms timesteps (400 steps),
with 64 highest-degree neurons in each graph receiving 180 pA from 50 to
150 ms and no background current or noise. The full run performs no sampling and no
subgraph extraction; no raw CSV is read and no dense adjacency matrix exists.

Measured results (`experiments/phase_2_5/reports/scalability_report.json`):

| Neurons | Edges | Synapses | Init (s) | Sim (s) | Steps/s | Peak WS (MB) | Retained (MB) | Spikes | Active | Non-stim spike share | Stable |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 800 | 7,500 | 124,693 | 0.0006 | 0.041 | 10,500 | 170.8 | 38.39 | 213 | 78 | 19.25% | yes |
| 5,000 | 121,092 | 1,931,167 | 0.0041 | 0.057 | 7,343 | 171.7 | 41.34 | 145 | 96 | 26.21% | yes |
| 20,000 | 480,107 | 7,414,940 | 0.0179 | 0.331 | 1,231 | 175.8 | 50.83 | 51,387 | 4,551 | 97.82% | yes |
| 50,000 | 1,620,531 | 23,785,918 | 0.0820 | 1.060 | 382 | 222.3 | 79.48 | 151,855 | 11,837 | 99.07% | yes |
| 139,255 | 3,732,460 | 50,666,648 | 0.1700 | 2.923 | 138 | 270.8 | 134.73 | 349,846 | 33,261 | 99.58% | yes |

"Stable" means finite state, membrane potentials within the configured
`[-90, -50]` mV bounds, refractory intervals respected, and recorded
transmissions exactly equal to the out-degree sum of spiking neurons. The
800-neuron run repeated in a separate process produced the same activity hash,
root-ID set, spike count and transmission count.

Memory at full size is 134.73 MB of retained arrays: 63.19 MB graph CSR,
29.67 MB synapse weights/currents, 2.12 MB delay buffers, 1.59 MB neuron state
and a 38.15 MB preallocated recorder. Process peak working set was 270.8 MB. The
recorder holds 5,000,000 spikes (40 MB); overflow raises rather than silently
dropping spikes. Subset peaks include the full source graph loaded for
sampling, so they overstate subset-only memory. Full details and caveats are in
`experiments/phase_2_5/reports/memory_report.md`.

Activity is **not monotonic in size**: the 5,000-neuron sample fired less than
the 800-neuron sample, consistent with sampled composition differences. At 20,000 neurons
and above, more than 97% of spikes came from neurons that never received the
external stimulus. That demonstrates propagation through the sampled graph,
but it may also reflect strong excitatory coupling under the model's weight
and transmitter assumptions. It is not evidence of biological correctness.
Throughput is a performance measurement, not a scientific score.

All sizes passed every stability check, but the suite covers one seed and one
200 ms protocol. Longer runs and other stimulation regimes remain untested.
Phase 2.5 does not implement sensory encoding, motor decoding, reinforcement
learning or game integration.

## Outputs

`python main.py --no-progress` writes into `experiments/results/initial/`:

- `selected_neurons.csv` - local and root IDs, annotations, degrees, positions,
  and whether each neuron was stimulated.
- `activity.npz` - spike times, neuron indices, neuron count, duration, capacity.
- `simulation_metadata.json` - model parameters, graph and synapse counts,
  activity summaries, diagnostics and stimulus root IDs.
- `raster.png` - spike raster.
- `firing_rates.png` - per-neuron rate distribution and 10 ms population rate.
- `experiment_report.json` - full configuration, composition comparison, weight
  percentiles, performance, environment and scientific-integrity statement.

Phase 2.5 writes `experiments/phase_2_5/results/` (one JSON and log per size),
`experiments/phase_2_5/plots/` (memory, speed, active-neuron and spike-count
plots) and `experiments/phase_2_5/reports/` (the JSON report, scalability
report and memory report).

## Tests

`python -m pytest -q` currently reports **68 passed**. Coverage includes:

- analytic passive decay, steady state, threshold timing, reset, refractory,
  membrane floor and vectorised populations;
- linear and power weight transforms, sign policies, sparse destination sums,
  delay delivery, exponential decay and validation;
- induced-subgraph CSR consistency, reproducible connected sampling and
  component counts;
- spike capacity, counts, rates, raster subsampling, saving and plotting;
- simulator equivalence to a standalone LIF loop, no-input quiescence,
  synaptic recruitment, seeded reproducibility, result saving and summaries;
- YAML config construction and compatibility with the verified 139,255-neuron
  artifact and its exact edge/synapse counts;
- Phase 2.5 benchmark statistics, activity hashing, directional and finite-state
  validation, low-memory skip recording, size parsing and reproducibility
  comparison.

## Known limitations

- Phase 2's 1 s experiment uses an 800-neuron connected subset. Phase 2.5 runs
  the full 139,255-neuron graph for 200 ms, but neither establishes whole-brain
  dynamics over behaviourally relevant timescales.
- All neurons share one LIF parameter set; cell-type-specific physiology is absent.
- Transmitter classes are predictions used only as coarse sign assumptions;
  cotransmission, receptor types and neuromodulation are not modelled.
- Synaptic weights are an arbitrary calibrated transform of structural counts.
- Delay is uniform; conduction distance, morphology and dendritic filtering are absent.
- Inhibition is a hyperpolarising current, not a conductance with a reversal potential;
  shunting inhibition is not represented.
- Membrane floor and 0.5 ms spike-time quantisation are modelling choices.
- No short-term plasticity, adaptation, bursting, gap junctions or learning.
- The FAFB dataset is an adult female brain without a complete ventral nerve cord.
- Results have not been compared against electrophysiological recordings.
- The Phase 2.5 suite uses one seed and one 200 ms protocol; long-run stability,
  other stimulation regimes and parameter sensitivity are untested.
- The high non-stimulated spike share at large sizes may indicate excessive
  excitatory coupling under the current assumptions; it is not a biological result.

## Recommended next milestone

The full-connectome performance envelope is now measured: 400 steps in 2.92 s
at 139,255 neurons with a 270.8 MB process peak. Phase 3 should add explicit
sensory input encoding and a motor/readout interface, then study parameter
sensitivity and longer simulations. Plasticity and reinforcement learning
should come only after those layers are validated. They are not implemented
here.

