# Chapter 4. Overall System Architecture

## 4.1 Design constraints

FLY-SURFER is organised around one constraint that shapes every component: the two connectomes are treated as separate sources of structure, and no information is allowed to flow between them by identity. FAFB supplies the brain graph used for perception, simulation, plasticity, and information analysis. BANC supplies the brain–ventral-nerve-cord graph used for motor decoding and for every Phase 8 execution. The FAFB volume has no leg motor neurons; the BANC reconstruction has them but comes from a different specimen and a different annotation pipeline. Merging the graphs would require asserting neuron correspondences that no available evidence supports. The architecture therefore exposes a single explicit boundary — the stimulated sensory pool — and never lets the rest of the pipeline assume that an FAFB neuron and a BANC neuron are the same cell.

Five further constraints follow from the project's scientific-integrity rules and are visible in the code structure.

- **Predicted annotation is not physiology.** Every population used as an input or an output is selected from published annotation columns. The code records the annotation field that produced each selection and marks the assignment as a computational convention where no measurement exists.
- **Verified-only synaptic signs.** An edge is excitatory or inhibitory only if both endpoints carry a predicted transmitter with a known sign (acetylcholine and glutamate excitatory; GABA and glycine inhibitory). Dopaminergic, serotonergic, octopaminergic, and unannotated edges are excluded from sign-dependent computation. This removes 55.52% of BANC t5 edges from sign-dependent paths; 44.48% remain signed.
- **Decoding is a declared rule, not a learned policy.** The motor decoder is a deterministic window-and-threshold rule with fixed priorities. It is not trained, and its output is not a motor command in any physiological sense.
- **All stochasticity is seeded.** Detector inference is deterministic for a fixed input; sampling, graph randomisation, and episode construction draw from explicit seeds recorded with every artifact.
- **Failed and null results are stored, not repaired.** The repository keeps negative outcomes (motor silence, a positive plasticity contrast that did not survive correction, a behaviourally null training set) as first-class artifacts, and the paper reports them unchanged.

## 4.2 Component inventory

The system has seven functional components, each with a narrow interface.

1. **Controlled game environment.** A standalone endless-runner derived from the open `endless-surfer` code base. It exposes a fixed three-lane geometry, four event classes used by the detector (train, ramp, wall, barrier components), coin and score bookkeeping, and a programmatic API for stepping, reading state, and injecting actions. It is not the commercial game Subway Surfers, and no commercial binary was instrumented at any point.
2. **Visual perception.** A YOLO11n detector exported to ONNX, run on 640×640 frames, followed by per-class non-maximum suppression. The detector emits boxes with class labels and confidence; a tracking layer associates boxes across frames and a temporal layer converts tracks into events.
3. **Event encoder and sensory scheduler.** Converts game events into feature activations on a 14-feature schema, maps activations onto named neuron populations, and delivers current pulses with per-neuron caps.
4. **Spiking simulator.** A sparse LIF network with exponential current synapses, implemented over compressed sparse row adjacency. It advances the network at 0.5 ms resolution and records spikes and per-neuron state.
5. **Motor decoder.** Aggregates spikes in 50 ms half-open windows and emits LEFT, RIGHT, JUMP, or NO_ACTION according to fixed thresholds and priority.
6. **Plasticity and reward.** Computes a reward-prediction-error-like modulation signal from game events, maintains eligibility traces, and applies a three-factor weight update within declared bounds.
7. **Analysis and experiment harness.** Performs mutual-information estimation, permutation and bootstrap inference, campaign execution, checkpointing, and artifact certification.

Figure 1 (Chapter 1) shows how these components connect. The pipeline is feed-forward at the level of data flow — frame to detector to event to current to spike to decoded action to game state — but two feedback paths exist. The closed-loop path returns decoded actions to the environment, and the plasticity path returns reward and modulation to the synapse update. Neither feedback path was shown to carry motor activity in any executed experiment, which is the central empirical result of the project.

## 4.3 Interfaces and data contracts

Each boundary in the pipeline is a typed structure rather than an implicit convention.

- **Frame to perception.** Frames are RGB arrays at the environment's native resolution. The detector wrapper accepts a frame and returns a list of `(class_id, confidence, x1, y1, x2, y2)` boxes after non-maximum suppression at IoU 0.7 and confidence 0.426. The wrapper records the model hash so that a stored perception output can be tied to a specific weight file.
- **Perception to events.** Boxes are associated into tracks; tracks are converted into typed events (appearance, lane membership, distance band, obstacle class, train class). Events carry timestamps in milliseconds of game time, not wall time.
- **Events to current.** The scheduler maps each active feature to a neuron population and emits a current pulse. Pulses decay over 150 ms and are clipped per neuron at 200 pA. The scheduler records the peak and mean current per feature, the number of pulses, and the number of stimulated neurons.
- **Current to spikes.** The simulator receives a sparse current vector and an adjacency matrix in CSR form, advances the network, and returns spike records and, where requested, membrane traces. Spike records are `(neuron_index, time_step)` pairs.
- **Spikes to action.** The decoder receives spike records, counts spikes per motor pool in the current 50 ms window, computes the active fraction of each pool, applies the gate (at least five spikes and at least three active neurons), and selects an action by priority LEFT, then RIGHT, then JUMP. If no pool passes, the action is NO_ACTION.
- **Action to reward.** The environment scores the action against the current state and returns a reward decomposed into coin, collision, and survival terms. The decomposition is preserved in the artifacts so that a reward total can be audited against its parts.

## 4.4 Configuration and provenance

Every experiment is described by a configuration file plus a set of recorded hashes. The Phase 8 protocol, REV4, has digest `e4aa9e0f…1547c`; its amendment has digest `832ef485…667ad`; the owner decision records D3, D4, D5, and D6 have digests `74f11d2c…948df8`, `1e15138c…51a8cf`, `015598e8…ca8bfe3f`, and `6a342504…61d8325`; the B3 record has digest `bc231c79…92a75a143a1f980`. These digests bind an execution to the protocol text that authorised it. A run whose configuration hash does not match the authorised record is rejected by the execution gate.

The model parameters themselves are declared in configuration files and are listed in Table 4. The table is a complete inventory of the neuron, synapse, decoder, plasticity, and sensory-drive parameters, with a status column distinguishing assumptions, calibrations, and derived values. No parameter in this table was tuned on an outcome that the paper reports.

**Table 4.** Complete model-parameter inventory. "Assumed" means a declared value with no fitting; "calibration" means a transform chosen to place synaptic currents on a workable scale; "derived" means computed from other declared values. Data source: `configs/neuron_config.yaml`, `configs/synapse_config.yaml`, `configs/motor_decoder.yaml`, `configs/plasticity*.yaml`, `configs/banc_sensory_mapping.yaml`; full machine-readable table in `tables/T03_model_parameters.csv`.

| Component | Parameter | Value | Unit | Status |
|---|---|---|---|---|
| neuron | membrane capacitance C_m | 200 | pF | assumed |
| neuron | leak conductance g_L | 10 | nS | assumed (tau_m = 20 ms) |
| neuron | resting potential E_L | −65 | mV | assumed |
| neuron | threshold V_th | −50 | mV | assumed |
| neuron | reset V_reset | −68 | mV | assumed |
| neuron | refractory period | 2 | ms | assumed |
| neuron | membrane floor | −90 | mV | assumed |
| neuron | rheobase (steady state) | 150 | pA | derived: 15 mV × 10 nS |
| simulation | timestep dt | 0.5 | ms | assumed |
| synapse (FAFB) | weight transform | 12 × count^0.75 | pA | calibration |
| synapse (BANC) | weight transform | min(5.0 × count^0.75, 300) | pA | calibration |
| synapse | excitatory time constant | 5 | ms | assumed |
| synapse | inhibitory time constant | 8 | ms | assumed |
| synapse | uniform delay | 1 | ms | assumed (effective 1.0 ms at dt 0.5 ms) |
| sign | ACh / glutamate | excitatory | – | predicted transmitter |
| sign | GABA / glycine | inhibitory | – | predicted transmitter |
| sign | DA / SER / OCT | unknown | – | excluded under verified-only policy |
| sign | unannotated edge | excluded | – | 44.48% of BANC t5 edges carry a sign |
| decoder | window | 50 | ms | half-open |
| decoder | activation threshold | 0.2 | active fraction | declared |
| decoder | release threshold | 0.1 | active fraction | declared |
| decoder | gate | ≥5 spikes and ≥3 active neurons | – | declared |
| decoder | priority | LEFT → RIGHT → JUMP | – | declared |
| plasticity (BANC) | learning rate eta | 0.5 | declared units | declared, not tuned |
| plasticity (BANC) | eligibility time constant | 20 | ms | assumed |
| plasticity (BANC) | weight bounds | 0.5–2.0 × initial | – | assumed |
| plasticity (BANC) | max \|delta w\| per update | 5 | pA | assumed |
| sensory drive | current per active feature | 200 | pA | declared |
| sensory drive | pulse decay | 150 | ms | declared |
| sensory mapping | mapped neurons | 232 | neurons | 7 features |

Two values in this table deserve emphasis because they recur in the results. The rheobase of 150 pA is a derived quantity: with a 15 mV gap between rest and threshold and a 10 nS leak conductance, a steady current of 150 pA is the minimum that can drive a neuron from rest to threshold. The sensory pulse of 200 pA is therefore only 1.33 times rheobase at the peak of a pulse, and it decays over 150 ms. A neuron that is not at rest, or whose pulse arrives late in the decay, may never reach threshold. This arithmetic is the reason the sensory pool itself fires sparsely and the reason downstream propagation is weak.

## 4.5 Determinism and reproducibility

Three mechanisms support reproduction.

First, the simulator is deterministic given a seed, a current schedule, and an adjacency matrix. There is no thread-level nondeterminism in the integration path: spikes are processed in index order, and the exponential-Euler update is applied in a fixed sequence. Repeated runs with identical inputs were verified to produce identical spike counts and action sequences in Phase 3B.2C, Phase 7, Pilot 1, and the Pilot 2-C grid.

Second, every artifact records the inputs that produced it. The Phase 3B.2C report stores the model SHA-256, the sequence identifier, the boundary policy, and the scheduler signature. The Pilot 2-C rows store seven input hashes and three configuration hashes. The D5 training artifacts store per-checkpoint parameter digests.

Third, analyses are separated from executions. The mutual-information analyses read stored spike and action records; they do not re-run the simulator. The bottleneck investigation reads Pilot 1 records; it does not stimulate anything. This separation means an analysis cannot silently change the data it analyses, and a discrepancy between an analysis and a source record is detectable.

The implementation is written in Python and uses NumPy [26], pandas [27], Matplotlib [28], PyTorch [30], and the SciPy stack [31] for numerical work, tabular records, figures, the linear readout, and statistical utilities. Package versions are pinned in the repository, and the figures in this paper were generated from the stored tables by a single script.

Determinism does not imply correctness. A deterministic pipeline can be deterministically silent, and in this project it was: the closed-loop and pilot executions produced identical outcomes across arms because no motor population ever fired. The architecture makes that failure visible rather than hiding it behind run-to-run variation.

## 4.6 What the architecture deliberately omits

The system does not contain a learned policy network, a gradient-based training loop over the connectome, a reinforcement-learning agent operating on the full graph, or any interface to the commercial game. The trainable component is a linear readout on neural activity in the D5/F conditions, and even that readout is trained on a synthetic objective rather than on game reward. There is no backpropagation through the spiking simulation. These omissions are scope decisions: the project asks whether a connectome-derived spiking network, with local plasticity and a fixed decoder, can transform visual game information into motor commands, not whether a large learned model can play the game.

The architecture also omits a limb model. BANC motor neurons are grouped into LEFT, RIGHT, and JUMP pools by annotation, but no muscle, joint, or body model converts pool activity into movement. A decoded action is a categorical symbol passed to the game; it is not a simulated limb trajectory. This is why the paper can report decoded actions but cannot report motor behaviour in the sense of a movement.

## 4.7 Summary

The architecture separates structure (two connectomes), function (declared encoders, simulator, decoder), learning (three-factor plasticity and a linear readout), and evaluation (seeded campaigns with pre-registered contrasts). Each boundary is typed and hash-bound. The design makes the motor stage the single point where the pipeline can fail to produce behaviour, and the empirical chapters show that it did fail there, reproducibly, for reasons that the architecture itself helps to localise.
