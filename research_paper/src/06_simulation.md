# Chapter 6. Neural Simulation

## 6.1 The neuron model

Every simulated cell is a leaky integrate-and-fire (LIF) neuron with current-based exponential synapses. The membrane equation is

C_m dV/dt = −g_L (V − E_L) + I(t),

where C_m = 200 pF, g_L = 10 nS, E_L = −65 mV, and I(t) is the total synaptic and external current arriving in the step. The membrane time constant is therefore τ_m = C_m / g_L = 20 ms. The neuron emits a spike when V crosses V_th = −50 mV, resets to V_reset = −68 mV, and is held at the reset value for a 2 ms refractory period. Membrane potential is floored at −90 mV to keep the state finite under large conductance bursts. The gap from rest to threshold is 15 mV, so the steady-state rheobase is 15 mV × 10 nS = 150 pA. A neuron at rest needs at least 150 pA of sustained current to fire; a transient pulse needs more.

The update is the exact exponential-Euler solution of the linear membrane equation over one step, evaluated at dt = 0.5 ms:

V(t + dt) = E_L + (V(t) − E_L + I/g_L) e^{−dt/τ_m} − I/g_L,

followed by the threshold, reset, and refractory rules. Figure 6 shows the step response computed directly from these declared parameters at two current amplitudes.

![Figure 6. LIF membrane dynamics computed from the declared model parameters. Traces show the response to a 300 ms current step at 150 pA (rheobase) and 300 pA, starting from rest at −65 mV, with threshold −50 mV and reset −68 mV, τ_m = 20 ms, dt = 0.5 ms. These curves are a numerical illustration of the frozen equations, not recorded biological data and not an experiment. Data source: configs/neuron_config.yaml.](figures/F06_lif_dynamics.png)

The figure is an illustration, not a measurement. Its purpose is to make the rheobase arithmetic visible: a 150 pA step reaches threshold only after roughly one time constant, while a 300 pA step reaches it sooner. The sensory pulses of Chapter 5 peak at 200 pA and decay with a 150 ms time constant, so a stimulated neuron sits between these two regimes. Whether it fires depends on its recent history and on the synaptic current it is already receiving.

## 6.2 The synapse model

A spike at neuron j at time t contributes a current to each postsynaptic neuron i with weight w_ij. Each contribution is a current impulse that decays exponentially with a time constant of 5 ms for excitatory and 8 ms for inhibitory synapses. All synapses carry a uniform 1 ms delay, which at dt = 0.5 ms is an effective two-step delay. The total synaptic current into neuron i is the sum over all presynaptic spikes within the delay and decay window.

Weights are derived from the structural synapse count c of a connected pair. For FAFB the transform is w = 12 · c^0.75 pA; for BANC it is w = min(5.0 · c^0.75, 300) pA. Both transforms are calibrations, not measurements of quantal amplitude. They were chosen so that a typical edge delivers current on the order of tens of pA, which is below the 150 pA rheobase for a single spike but can sum across a population. The cap on BANC weights prevents a few high-count edges from dominating the current balance.

Synaptic sign follows the transmitter policy. In the verified-only BANC policy, an edge is excitatory only when both endpoints carry a predicted transmitter with an excitatory sign (acetylcholine or glutamate) and inhibitory only when both carry an inhibitory sign (GABA or glycine). Edges involving dopamine, serotonin, octopamine, a conflict, or an unannotated endpoint are excluded from sign-dependent computation; they remain in the graph but contribute no signed current. This is why only 44.48% of BANC t5 edges (683,100 of 1,535,710) enter the sign-dependent simulation. The FAFB replay used an earlier predicted-transmitter policy and classified 2,955,795 edges as excitatory and 776,665 as inhibitory. The two policies are not interchangeable, and results from the FAFB replay and the BANC executions are not pooled.

The exclusion is conservative in both directions. It discards genuine neuromodulatory effects, but it avoids assigning an arbitrary sign to an edge whose transmitter is unknown. In a preparation where predicted transmitters cover 89.27% of BANC nodes but only 37.87% are verified, assigning signs to the remainder would be a modelling choice presented as data. The project chose to lose edges rather than invent signs.

## 6.3 The simulation engine

The engine stores the network as a compressed sparse row (CSR) adjacency matrix over edge indices, with parallel arrays for destination, weight, sign, and delay bin. A step proceeds in a fixed order: advance synaptic state, apply external current, integrate membranes, detect threshold crossings, schedule delayed propagation, and record spikes. Propagation from a spike visits the outgoing edge list of that neuron; the hub structure of the connectome means one spike can touch thousands of synapses.

Figure 7 shows the engine structure and the measured throughput at two scales.

![Figure 7. Spiking simulation engine structure and measured throughput. The left panel is a schematic of the step loop (synaptic update, input injection, integration, threshold detection, delayed propagation, recording). The right panel reports measured steps per second for the full FAFB graph benchmark (139,255 neurons, 138.3 steps/s) and for the full-graph Phase 3B.2C replay of 100 real frames (81.9 steps/s, including current injection and spike recording). Throughput values are measurements; box structure is schematic. Data source: experiments/phase_2_5/reports/scalability_report.json and experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json.](figures/F07_simulation_engine.png)

The engine is pure NumPy and runs on the CPU. It does not use a GPU, a neuromorphic device, or a compiled kernel. On the execution host (12 logical CPUs, 15.342 GB RAM), the full FAFB graph advances at 138.3 steps per second for a 200 ms benchmark, which is about 69 ms of biological time per wall second at dt = 0.5 ms. The 100-frame replay is slower, at 81.93 steps per second, because it includes current injection, spike recording to a 30-million-event buffer, and per-feature bookkeeping. Neither rate is fast enough for real-time closed-loop control of a 30 fps game; the pilot executions are necessarily slower than the game clock, and the paper does not claim real-time performance.

The propagation cost is dominated by spikes. The full-graph replay produced 15,654,631 spikes and 996,524,829 synaptic transmissions, or 63.657 transmissions per spike. The maximum out-degree is 6,523, and the engine reserves a 48.1 MB worst-case temporary buffer for a single hub's propagation. This is the concrete reason the design cannot simply scale the network up: cost grows with spike count times out-degree, and the connectome's degree distribution puts a long tail on that product.

## 6.4 Scalability measurements

Phase 2.5 benchmarked the same engine on connected subgraphs of 800, 5,000, 20,000, and 50,000 neurons, and on the full 139,255-neuron graph. Every run used a 200 ms simulation, dt = 0.5 ms, and a stimulus of 180 pA to the 64 highest-degree neurons from 50 to 150 ms. Each graph was a connected snowball sample from class-stratified hub candidates, so the subgraphs are not random induced subgraphs; they are dense, connected neighbourhoods and therefore favour propagation relative to a random sample of the same size.

Table 6 reports the measurements.

**Table 6.** Phase 2.5 scalability measurements. The 800-neuron configuration was run twice to check reproducibility. "Retained" is the memory held by the simulation arrays after the run; "peak" is the process working set. "Non-stimulated share" is the fraction of spikes from neurons outside the 64-neuron stimulus. Data source: `experiments/phase_2_5/reports/scalability_report.json`; full machine-readable table in `tables/T19_scalability.csv`.

| Run | Neurons | Edges | Synapses | Init (s) | Sim (s) | Steps/s | Peak WS (MB) | Retained (MB) | Spikes | Active | Non-stim. share |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| first | 800 | 7,500 | 124,693 | 0.0006 | 0.0406 | 10,499.8 | 170.8 | 38.3866 | 213 | 78 | 0.1925 |
| repeat | 800 | 7,500 | 124,693 | 0.0006 | 0.0499 | 8,342.0 | 170.4 | 38.3866 | 213 | 78 | 0.1925 |
| first | 5,000 | 121,092 | 1,931,167 | 0.0041 | 0.0568 | 7,343.1 | 171.7 | 41.3429 | 145 | 96 | 0.2621 |
| first | 20,000 | 480,107 | 7,414,940 | 0.0179 | 0.3310 | 1,230.6 | 175.8 | 50.8333 | 51,387 | 4,551 | 0.9782 |
| first | 50,000 | 1,620,531 | 23,785,918 | 0.0820 | 1.0601 | 382.2 | 222.3 | 79.4818 | 151,855 | 11,837 | 0.9907 |
| first | 139,255 | 3,732,460 | 50,666,648 | 0.1700 | 2.9227 | 138.3 | 270.8 | 134.7317 | 349,846 | 33,261 | 0.9958 |

Four features of the table matter for the paper.

First, the 800-neuron run is reproducible in its spike output (213 spikes, 78 active neurons in both runs) but not in its speed (10,499.8 versus 8,342.0 steps/s). The activity result is deterministic; the timing is not. All reported activity numbers are from the deterministic path, and no inference depends on wall-clock rates.

Second, the subgraphs are not representative of sparse sampling. At 5,000 neurons, only 145 spikes occur, fewer than at 800, even though the subgraph has more edges per neuron; the benchmark records the observation without attributing a mechanism, and the paper does not interpret it. At 20,000 neurons, activity jumps to 51,387 spikes, and non-stimulated spikes become 97.8% of the total. The transition from stimulus-dominated to background-dominated activity happens between 5,000 and 20,000 neurons. The full graph is 99.58% non-stimulated.

Third, memory is modest. The full graph retains 134.7 MB of simulation arrays and peaks at 270.8 MB of working set, well within the host's 15.3 GB. The later replay retained 341.3 MB (325.47 MB) because it kept a 30-million-event spike buffer and per-step records; the process RSS increased by 163.8 MB during that run. Neither execution approached the host limit, but the Phase 8 training preflight recorded a tighter budget (7.118/15.342 GB available), which is why the training artifacts run in sequence rather than in parallel.

Fourth, the scaling is not linear in neuron count. From 20,000 to 139,255 neurons, the step rate falls from 1,230.6 to 138.3 steps/s while the edge count grows by a factor of 7.77. The cost tracks edges and spikes, not neurons, and the spike count grows faster than the graph because the full network contains densely connected hub regions.

Figure 19 plots the throughput and retained-memory columns of Table 6.

![Figure 19. Phase 2.5 scalability on the FAFB substrate. Panel (a): simulated steps per second on a logarithmic ordinate for connected subgraphs of 800, 5,000, 20,000, 50,000, and 139,255 neurons. Panel (b): retained simulation-array memory in MB. Every point is a 200 ms simulation (400 steps at dt = 0.5 ms) with 180 pA delivered to the 64 highest-degree neurons from 50 to 150 ms. The two 800-neuron runs share one point because their spike output is identical; their speed difference is described in the text. Data source: experiments/phase_2_5/reports/scalability_report.json.](figures/F13_phase25_scaling.png)

The Phase 2.5 benchmark predates the verified-only sign policy: its configuration treats unknown and unlabeled transmitter classes as excitatory. The benchmark is a throughput measurement and makes no biological claim, but the difference is recorded here so that a reader does not assume the benchmarked network and the BANC execution share a sign policy.

## 6.5 Determinism and numerical stability

Simulation is deterministic: spikes are processed in index order, the integration is closed-form per step, and the only state carried between steps is the membrane vector, the synaptic current vector, and the delay buffers. A repeat of the 800-neuron configuration produced identical spike counts and active-neuron counts (213 and 78). The full-graph replay repeated with identical detections, temporal events, scheduler signature, and spike count (15,654,631), and an empty difference list, as reported in Chapter 5.

Numerical stability is checked by diagnostics. In the full-graph replay the membrane stayed within [−90, −50] mV, the state was finite at every diagnostic step, and the maximum absolute total current was 178,691 pA in a single step. That current is far above rheobase but is distributed across a neuron's many incoming synapses; the per-synapse contributions are much smaller. The 48.1 MB worst-case propagation buffer and the 30-million-event spike buffer are sized for the observed maxima, and the replay recorded 15.65 million spikes against that 30-million capacity.

## 6.6 What the simulator is and is not

The simulator is a structural spiking model. Its connectivity is a measured reconstruction; its neurons are point LIF units with declared parameters; its synapses are calibrated current injections; its signs are predicted transmitters; its stimulation is a declared encoding. It is not a biophysical model of the fly brain, it does not reproduce measured firing rates, and it was not fitted to any neural recording. The absence of fitting is deliberate: the project asks what a connectome can do under a fixed, simple model, not what parameters best reproduce a recording.

Two consequences follow. First, a negative result from this simulator does not show that the biological circuit cannot produce the behaviour; it shows that this model, with these parameters, did not. Second, a positive result would not show that the biological circuit does produce the behaviour; it would show that the structure supports it under the model. Every claim in later chapters is phrased within this scope.

The simulator's cost profile also shapes the experimental design. A full-graph run at about 138 steps/s means a 3.3 s replay takes about 80 s of wall time, and a Pilot 1 episode of 20,667 neural steps takes minutes. The Phase 8 campaigns are sized around this budget, not around statistical optimality, and Chapter 12 shows how the sample size was derived from the projected variance rather than from what the machine could conveniently run.

## 6.7 Summary

The simulation layer is a deterministic, sparse, current-based LIF network over the FAFB or BANC graph. Its parameters are declared and listed in Table 4; its weights are calibrated transforms; its signs are predicted transmitters under either an early default or the later verified-only policy. It runs the full 139,255-neuron FAFB graph at 138.3 steps/s and the BANC execution at 81.9 steps/s, retains 135–341 MB depending on recording, and produces reproducible spike output. It is a structural model, not a physiological replica, and the results it produces are interpreted only within that scope.
