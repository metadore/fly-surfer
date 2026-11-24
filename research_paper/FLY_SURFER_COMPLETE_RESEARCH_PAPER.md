# Teaching a Fruit Fly Brain to Play Subway Surfers Through Connectome-Based Neural Simulation: Architecture, Learning Mechanisms, Experimental Evaluation, and Motor-Output Limitations

**FLY-SURFER Project**

Author: metadore

Document version 1.1 — 24 November 2026

**Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0), © 2026 metadore — <https://creativecommons.org/licenses/by/4.0/>. You may share and adapt the original paper text, tables and figures for any purpose, including commercially, provided you give appropriate credit to metadore, cite this paper (title, author, version 1.1, 24 November 2026), link to the licence, and indicate if changes were made. No additional restrictions may be applied. Third-party datasets and assets (FlyWire, BANC, Subway Surfers, third-party software, model weights and figures) retain their own licences and attribution and are not relicensed by CC BY 4.0; see `LICENSE` and `THIRD_PARTY_NOTICES.md`.

Research paper prepared from the completed FLY-SURFER repository. This document reports existing experiments; it introduces no new experiment, model change, protocol change, or project phase. All quantitative statements are traceable to a file in the repository through the companion `SOURCE_AND_EVIDENCE_REGISTER.md`.

<!-- pagebreak -->

## Abstract

Can a connectome-derived fruit-fly neural network, implemented as a spiking neural simulation with learning mechanisms, transform visual game information into functional motor commands in a controlled game environment? FLY-SURFER addressed this question through a staged program that began with the FlyWire FAFB v783 brain connectome (139,255 neurons; 3,732,460 directed pairs at a five-synapse threshold; 50,666,648 summed synapses), constructed a leaky integrate-and-fire simulation over sparse synaptic matrices, mapped game-derived visual features onto identified sensory populations, decoded activity in annotation-defined motor pools, and added reward-modulated three-factor plasticity and trainable linear readouts. Because the FAFB volume contains no limb motor neurons, the motor stage was rebuilt on the BANC v888 brain–ventral-nerve-cord connectome (172,433 endpoints; 1,535,710 edges at a five-synapse threshold), which supplies 805 annotated motor neurons, 1,316 descending neurons, and 1,849 ascending neurons.

The program produced a functioning, reproducible software chain: perception and replay, full-scale simulation, a fixed motor decoder, a plasticity rule, an information-theoretic evaluation, a closed-loop game bridge, a pre-registered Phase 8 protocol, and two executed pilots. It did not produce functional game-playing. In the Phase 7 closed-loop demonstration the network emitted 2,852 spikes, all from directly stimulated sensory neurons, and zero motor-population spikes, so the decoder returned NO_ACTION on all 213 decisions. The nine-episode Pilot 1 reproduced the same outcome (3,784 decisions, 126,135 neural steps, 73,880 recorded spikes, zero motor spikes) and added a mechanistic explanation: of 662 signed first-hop edges from stimulated sensory neurons, 473 targets received current, but the peak somatic depolarisation reached −56.926 mV against a −50 mV threshold, a shortfall of 6.926 mV, and no second-hop current was generated. The Phase 6 information analysis found no confirmatory gain in cue-to-action mutual information from plasticity (mean difference −0.0863 bits; exact two-sided sign-flip p = 0.125; Holm-adjusted 0.25), and a synthetic positive control confirmed that the decoder can fire when motor populations are driven directly. Six trained F/Fβ readout artifacts (120 episodes) were certified technically but were behaviourally null: zero motor spikes, zero weight change, and identical F/Fβ outcomes. Pilot 2-C then executed 54/54 planned rows, certified all eight descriptive claims, and confirmed exact A′ identity and a degenerate all-arm equality of survival, but could not estimate any of the four pre-registered contrasts C1–C4 or test H1–H3. The central question therefore receives a qualified negative answer at the current operating point: the structural connectome, the sensory convention, and the LIF parameterisation jointly fail to drive the first post-sensory stage above threshold, and no learning mechanism downstream of a silent motor channel can be evaluated behaviourally. The paper documents this boundary in full, including negative results, protocol deviations, unavailable analyses, and the distinction between structural connectivity and physiological connectivity.

**Keywords:** connectome; Drosophila melanogaster; spiking neural network; leaky integrate-and-fire; FlyWire; BANC; sensory encoding; motor decoding; three-factor plasticity; mutual information; closed-loop simulation; negative results; reproducibility.

<!-- pagebreak -->

## Abbreviations and terminology

| Abbreviation | Expansion | Meaning in this paper |
|---|---|---|
| ACh | acetylcholine | Predicted excitatory transmitter in the sign policy |
| A′ | A-prime | Plasticity control arm with learning rate η = 0 |
| BANC | Brain And Nerve Cord | Female *Drosophila* brain + ventral nerve cord connectome, v888 |
| C1–C4 | Confirmatory contrasts 1–4 | Pre-registered Phase 8 differences (F−A, B−A, A−C, F−Fβ) |
| CSR | compressed sparse row | Storage format for the synaptic matrices |
| DA | dopamine | Predicted modulator; excluded from sign assignment |
| DN | descending neuron | Brain-to-ventral-cord projection neuron |
| FAFB | Full Adult Fly Brain | Electron-microscopy volume of an adult female brain |
| F | readout condition | Fixed substrate plus trained linear feature readout |
| Fβ | F-beta | Bias-only readout control |
| GABA | γ-aminobutyric acid | Predicted inhibitory transmitter |
| GLUT | glutamate | Predicted excitatory transmitter in the sign policy |
| H1–H6 | Hypotheses 1–6 | Phase 8 hypotheses; H1–H3 map to C2, C3, C1 |
| LIF | leaky integrate-and-fire | Neuron model used throughout |
| MI | mutual information | Information-theoretic dependence measure, in bits |
| MN | motor neuron | Neuron with motor effector annotation |
| OCT | octopamine | Predicted modulator; excluded from sign assignment |
| ONNX | Open Neural Network Exchange | Portable detector model format |
| RPE | reward prediction error | Scalar modulation signal |
| SEI | smallest effect of interest | 100 game updates in Phase 8 |
| SER | serotonin | Predicted modulator; excluded from sign assignment |
| SNN | spiking neural network | The simulated network |
| VNC | ventral nerve cord | Thoracic/abdominal ganglion containing limb motor neurons |
| YOLO | You Only Look Once | Object-detection architecture family |

**Evidence vocabulary.** Throughout the paper, an *implementation test* checks that software behaves as specified on fixtures or synthetic inputs; it is not biological evidence. A *pilot* is an authorized, small, pre-specified execution used to check viability and variance; it is not a confirmatory campaign. A *campaign* is the full pre-registered design with the declared seed count; no Phase 8 campaign was executed. An *observation* is a recorded value; an *interpretation* is an inference drawn from observations; an *assumption* is a modelling choice not measured in this project; a *hypothesis* is a statement awaiting test. These labels are used consistently and are not interchangeable.

**Scope statement.** The controlled environment is the standalone `endless-surfer` implementation, a Subway-Surfers-style runner. The commercial Subway Surfers game was never instrumented, controlled, or played by the network. The detector was trained outside this repository, and its published validation metrics are reported as provenance, not re-measured here.

<!-- pagebreak -->

## Table of contents

    - Abstract
    - Abbreviations and terminology
- **Chapter 1. Introduction**
    - 1.1 Motivation
    - 1.2 Central research question
    - 1.3 Secondary questions
    - 1.4 What the project built
    - 1.5 What the programme found
    - 1.6 What this paper does not claim
    - 1.7 Organisation
- **Chapter 2. Background and Related Work**
    - 2.1 From wiring diagrams to simulated circuits
    - 2.2 Insect visual guidance and motor control
    - 2.3 Spiking models and large-scale simulation
    - 2.4 Neuromodulated plasticity and credit assignment
    - 2.5 Information-theoretic evaluation
    - 2.6 Object detection and controlled game environments
    - 2.7 Positioning and gaps
- **Chapter 3. Biological Data and Connectome Construction**
    - 3.1 Data sources and governance
    - 3.2 The FAFB graph artifact
    - 3.3 FAFB annotations and population inventory
    - 3.4 The BANC graph and threshold sensitivity
    - 3.5 BANC annotations and coverage
    - 3.6 Why the motor stage uses BANC
    - 3.7 Dataset inventory and detector provenance
    - 3.8 Summary
- **Chapter 4. Overall System Architecture**
    - 4.1 Design constraints
    - 4.2 Component inventory
    - 4.3 Interfaces and data contracts
    - 4.4 Configuration and provenance
    - 4.5 Determinism and reproducibility
    - 4.6 What the architecture deliberately omits
    - 4.7 Summary
- **Chapter 5. Visual Perception and Sensory Encoding**
    - 5.1 What the perception stage must deliver
    - 5.2 The detector
    - 5.3 The annotated dataset and its split structure
    - 5.4 From boxes to events
    - 5.5 Sensory encoding
    - 5.6 What the replay established about propagation
    - 5.7 Summary
- **Chapter 6. Neural Simulation**
    - 6.1 The neuron model
    - 6.2 The synapse model
    - 6.3 The simulation engine
    - 6.4 Scalability measurements
    - 6.5 Determinism and numerical stability
    - 6.6 What the simulator is and is not
    - 6.7 Summary
- **Chapter 7. Motor Decoding and Game Control**
    - 7.1 The motor interface
    - 7.2 The decoding rule
    - 7.3 Characterising the rule on controlled drive
    - 7.4 Driving the decoder from BANC structure
    - 7.5 The sensory-to-motor round trip
    - 7.6 The controlled game
    - 7.7 What the motor stage established
    - 7.8 Summary
- **Chapter 8. Reward, Plasticity and Information Theory**
    - 8.1 The learning problem as stated
    - 8.2 The reward signal
    - 8.3 Eligibility traces
    - 8.4 The three-factor rule and its constraints
    - 8.5 The controlled task on which the rule was tested
    - 8.6 The Phase 5F comparative evaluation
    - 8.7 What the rule did and did not establish
    - 8.8 Information theory: what would count as evidence
    - 8.9 Summary
- **Chapter 9. Project Development and Experimental Chronology**
    - 9.1 Why the chronology is part of the evidence
    - 9.2 Phase map
    - 9.3 The first arc: connectome and simulator (Phases 0–2.5)
    - 9.4 Perception and dataset work (Phases 3A–3C)
    - 9.5 The dataset switch (Phases 4A–4H)
    - 9.6 Plasticity and information (Phases 5 and 6)
    - 9.7 Closed loop (Phase 7)
    - 9.8 Phase 8 design and authorization (REV3 → REV4 → D1–D6)
    - 9.9 The execution arc (2026-11-20 to 2026-11-23)
    - 9.10 Validation history
    - 9.11 What the chronology shows
- **Chapter 10. Phase 6: Mutual Information in the Archived Record**
    - 10.1 The question Phase 6 could answer
    - 10.2 The declared analysis
    - 10.3 The confirmatory result: no information gain
    - 10.4 Exploratory endpoints: sensory coding
    - 10.5 Exploratory endpoint: neural pools to decoded action
    - 10.6 Exploratory endpoints: reward ablation and conditional information
    - 10.7 Endpoints that were not estimable
    - 10.8 What Phase 6 established
- **Chapter 11. Phase 7: Closed-Loop Integration**
    - 11.1 What Phase 7 had to demonstrate
    - 11.3 The controlled environment and the adapter contract
    - 11.4 Open-loop demonstrations: validating the harness
    - 11.5 The live closed-loop bridge
    - 11.6 One update end to end
    - 11.7 The result: activity without motor recruitment
    - 11.8 Determinism, integrity, and the README baseline
    - 11.9 An unexplained numerical equality
    - 11.10 What integration established and what it did not
    - 11.11 Summary
- **Chapter 12. Phase 8: Experimental Design and Pre-registration**
    - 12.1 Why a pre-registered campaign was written
    - 12.2 The six conditions
    - 12.3 The control arms and what they certify
    - 12.4 Hypotheses and the confirmatory family
    - 12.5 Primary outcome and smallest effect of interest
    - 12.6 Pairing, replication, and the sample-size rule
    - 12.7 The exact sign-flip test
    - 12.8 Integrity gates and the authorization chain
    - 12.9 What the design could and could not establish
    - 12.10 Summary
- **Chapter 13. Pilot 1: A Viability and the Motor Floor**
    - 13.1 What Pilot 1 was authorised to do
    - 13.2 Execution and provenance
    - 13.3 Nine episode results
    - 13.4 The spike total: 72,880 and 73,880
    - 13.5 Zero motor output
    - 13.6 Integrity, freeze status, and documentation nuances
    - 13.7 What Pilot 1 established and what it did not
    - 13.8 Summary
- **Chapter 14. The Motor Bottleneck**
    - 14.1 The question and the method
    - 14.2 The sensory layer is not the failure
    - 14.3 The first hop
    - 14.4 Why a current above rheobase does not produce a spike
    - 14.5 The second hop and the motor layer
    - 14.6 What is not the cause, and what remains ambiguous
    - 14.7 The convergence argument and its limits
    - 14.8 What would be required to move the bottleneck
    - 14.9 Summary
- **Chapter 15. D5/D6: Training and Artifact Certification**
    - 15.1 Authorisation for exactly six artifacts
    - 15.2 What was trained, and what was not
    - 15.3 The six-artifact grid and its execution
    - 15.4 Interruption, recovery, and equivalence
    - 15.5 Provenance correction for F/9001
    - 15.6 Certification of the six artifacts
    - 15.7 The training outcome is behaviourally null
    - 15.8 Preflight and the execution boundary
    - 15.9 What the stage established and what it did not
    - 15.10 Summary
- **Chapter 16. Pilot 2-C: Floor and Identity Certification**
    - 16.1 Authorisation and the resolved preflight blocker
    - 16.2 The 54-entry grid and its execution
    - 16.3 The nine distinct game trajectories
    - 16.4 A′ identity
    - 16.5 The eight certification claims
    - 16.6 C1–C4 and H1–H3: what Pilot 2-C could not evaluate
    - 16.7 Deviations, failures, and the one run-time anomaly
    - 16.8 What Pilot 2-C established and what it did not
    - 16.9 Summary
- **Chapter 17. Consolidated Results**
    - 17.1 How the consolidated results are stated
    - 17.2 The central question
    - 17.3 The nine secondary questions
    - 17.4 The cross-phase evidence ladder
    - 17.5 Status of the pre-registered contrasts and hypotheses
    - 17.6 What the negative results jointly imply
    - 17.7 What is solid and what remains provisional
    - 17.8 Summary
- **Chapter 18. Discussion**
    - 18.1 The result in one paragraph
    - 18.2 Why the motor silence is the central finding
    - 18.3 Success without information: reading Phase 5F and Phase 6 together
    - 18.4 What a structural connectome can and cannot be
    - 18.5 The readout null and the logic of controls
    - 18.6 Pre-registration, provenance, and the discipline of negative results
    - 18.7 Relation to alternative approaches
    - 18.8 Implications for the central question
    - 18.9 Summary
- **Chapter 19. Limitations and Threats to Validity**
    - 19.1 What this chapter covers
    - 19.2 Construct validity: what the model measures
    - 19.3 Internal validity: whether the comparisons support their claims
    - 19.4 External validity: whether the findings generalise
    - 19.5 Statistical validity
    - 19.6 Documentation and evidence-status limitations
    - 19.7 Deviations register
    - 19.8 Consolidated limitations register
    - 19.9 Unresolved documentation issues
    - 19.10 Summary
- **Chapter 20. Conclusion**
    - 20.1 The question and the answer
    - 20.2 Why the negative is qualified
    - 20.3 What the programme established
    - 20.4 What the programme did not establish
    - 20.5 Contributions
    - 20.6 Closing statement
    - 20.7 Summary
- **Chapter 21. Future Research**
    - 21.1 How future work should be framed
    - 21.2 The first-hop drive question
    - 21.3 Physiological validation
    - 21.4 Readout, motor activity, and the logic of controls
    - 21.5 Topology and null models
    - 21.6 Parameter sensitivity and cell-type physiology
    - 21.7 Conventional learners and observation sufficiency
    - 21.8 Receptive-field mapping
    - 21.9 What would count as a positive result
    - 21.10 The open-question register
    - 21.11 Summary
- **Appendix A. Repository Map and Artifact Inventory**
    - A.1 Scope and the read-only rule
    - A.2 Executed-evidence directories
    - A.3 What the repository does not contain
- **Appendix B. Data Provenance and Inventory**
    - B.1 FlyWire FAFB v783
    - B.2 BANC v888
    - B.3 Detector dataset and model
    - B.4 Controlled game
    - B.5 Dataset separation
- **Appendix C. Model and Simulation Parameters**
    - C.1 Neuron model
    - C.2 Synapses, signs, and weights
    - C.3 Motor decoder
    - C.4 Plasticity and sensory drive
- **Appendix D. Phase-by-Phase Implementation and Validation Evidence**
    - D.1 Recorded outcomes
    - D.2 Test-suite record
    - D.3 Interpretation rule
- **Appendix E. Phase 6 Estimator Definitions and Declared Analysis**
    - E.1 Estimators
    - E.2 Declared inference and support rules
    - E.3 Confirmatory and exploratory values
    - E.4 Endpoints declared unavailable
- **Appendix F. Phase 8 Statistical Design Details**
    - F.1 Contrasts and hypotheses
    - F.2 Primary outcome and smallest effect of interest
    - F.3 Pairing and random streams
    - F.4 Sample-size rule
    - F.5 Exact sign-flip test
    - F.6 Identity and integrity gates
- **Appendix G. Pilot 1 Checks and the 72,880 / 73,880 Disclosure**
    - G.1 Arithmetic from the stored rows
    - G.2 The discrepancy
    - G.3 Execution and integrity checks
- **Appendix H. Motor-Bottleneck Measurements and Controls**
    - H.1 Structural funnel
    - H.2 Current and membrane at the first hop
    - H.3 Negative controls
    - H.4 Positive controls on the decoder and motor tissue
    - H.5 What the bottleneck analysis does not establish
- **Appendix I. D5/D6 Training and Checkpoint Record Schema**
    - I.1 Artifact layout
    - I.2 Episode record fields
    - I.3 Checkpoint ledger
    - I.4 Six artifacts and their pairing
    - I.5 Recovery and equivalence
    - I.6 Why the training was behaviourally null
- **Appendix J. Pilot 2-C Claim Definitions and Identity Fields**
    - J.1 Authorisation binding
    - J.2 Operational definition of each claim
    - J.3 The nineteen identity fields
    - J.4 Recorded attribution values
    - J.5 What the certification does not license
- **Appendix K. Reproduction, Environment, and Frozen Hashes**
    - K.1 Software environment
    - K.2 Read-only verification commands
    - K.3 Frozen input and configuration hashes
    - K.4 Protocol and authorisation hashes
    - K.5 Resource and timing record
    - K.6 Closing note on reproducibility

<!-- pagebreak -->

## List of figures

| Figure | Caption (short) | Image file |
|---|---|---|
| Figure 1 | End-to-end FLY-SURFER architecture. | `figures/F01_system_architecture.png` |
| Figure 2 | FlyWire FAFB v783 connectome construction summary. | `figures/F02_flywire_construction.png` |
| Figure 3 | FlyWire FAFB v783 edge-weight and degree distributions computed from the stored edge arrays. | `figures/F03_fafb_distributions.png` |
| Figure 4 | BANC v888 graph construction and threshold sensitivity. | `figures/F04_banc_construction.png` |
| Figure 5 | BANC v888 annotation coverage and neuronal composition. | `figures/F05_banc_annotation.png` |
| Figure 6 | LIF membrane dynamics computed from the declared model parameters. | `figures/F06_lif_dynamics.png` |
| Figure 7 | Spiking simulation engine structure and measured throughput. | `figures/F07_simulation_engine.png` |
| Figure 8 | Subway Surfers v15 annotation inventory by class and official split. | `figures/F08_dataset_inventory.png` |
| Figure 9 | Six unmodified curated training images, one for each of six high-frequency classes, with no annotation … | `figures/yolo11_visuals/Y01_training_samples.png` |
| Figure 10 | Ground-truth annotations for the six curated training images of Figure 9, drawn from the original YOLO label … | `figures/yolo11_visuals/Y02_ground_truth.png` |
| Figure 11 | One labelled instance for each of the 14 detector classes from the curated training split, with the number of … | `figures/yolo11_visuals/Y03_class_diversity.png` |
| Figure 12 | Actual predictions of the deployed YOLO11n ONNX model on six curated validation images at the deployment … | `figures/yolo11_visuals/Y04_predictions.png` |
| Figure 13 | Paired ground-truth and detection panels for four curated validation images at identical scale, with … | `figures/yolo11_visuals/Y05_gt_vs_prediction.png` |
| Figure 14 | Detection examples and limitations: correct detections, missed ground-truth objects, extra detections and … | `figures/yolo11_visuals/Y06_detection_examples.png` |
| Figure 15 | Perception and tracking counts in the Phase 3B.2C real-sequence replay (datasetfootage frames 100–199). | `figures/F09_3b2c_perception.png` |
| Figure 16 | Spike attribution in the Phase 3B.2C full-FAFB replay. | `figures/F10_3b2c_attribution.png` |
| Figure 17 | Sensory schedule in the Phase 3B.2C replay: current delivered per game feature. | `figures/F11_sensory_currents.png` |
| Figure 18 | Motor populations and decoder rule. | `figures/F12_motor_decoder.png` |
| Figure 19 | Phase 2.5 scalability on the FAFB substrate. | `figures/F13_phase25_scaling.png` |
| Figure 20 | Phase 5F paired seed-level mutual information between cue and chosen action at checkpoint 160. | `figures/F14_phase5f_paired.png` |
| Figure 21 | Phase 5F final success rates on the synthetic task (mean ± sd over ten seeds). | `figures/F15_phase5f_success.png` |
| Figure 22 | Phase 6 paired mutual-information differences for the two confirmatory contrasts. | `figures/F16_phase6_paired.png` |
| Figure 23 | Phase 6 population-size sweep for the Phase 3A.5 distance code. | `figures/F17_phase6_population.png` |
| Figure 24 | Phase 4F neural-pool to decoded-action mutual information for the declared code and sensitivity variants. | `figures/F18_phase6_decoder_mi.png` |
| Figure 25 | Phase 7 closed-loop activity and sensory drive at environment seed 42. | `figures/F19_phase7_timeseries.png` |
| Figure 26 | Phase 7 controlled-game runs for the random agent (three seeds), the rule-based agent (three seeds), and the … | `figures/F20_phase7_demo.png` |
| Figure 27 | Pilot 1 nine-episode outcomes on the frozen BANC substrate. | `figures/F21_pilot1_episodes.png` |
| Figure 28 | Pilot 1 first-hop signal funnel from the 232 stimulated sensory neurons. | `figures/F22_pilot1_firsthop.png` |
| Figure 29 | Peak membrane depolarisation at the first hop versus rest and spike threshold. | `figures/F23_membrane_threshold.png` |
| Figure 30 | Phase 4G condition outcomes on the BANC graph, including the positive control. | `figures/F24_phase4g_positive_control.png` |
| Figure 31 | D5 training reward trajectories for F and F_beta across the three evaluation seeds. | `figures/F25_d5_trajectories.png` |
| Figure 32 | D5 artifact and checkpoint matrix. | `figures/F26_d5_checkpoint_matrix.png` |
| Figure 33 | Pilot 2-C design grid as executed. | `figures/F27_pilot2c_design.png` |
| Figure 34 | Pilot 2-C survival by arm and cell. | `figures/F28_pilot2c_outcomes.png` |
| Figure 35 | Pilot 2-C A_prime identity check. | `figures/F29_pilot2c_a_prime.png` |
| Figure 36 | Pilot 2-C certification claims P2C-1 through P2C-8. | `figures/F30_certification_matrix.png` |
| Figure 37 | Consolidated cross-phase evidence ladder. | `figures/F31_evidence_ladder.png` |
| Figure 38 | Three-factor plasticity rule. | `figures/F32_three_factor.png` |
| Figure 39 | Minimum attainable two-sided p-value of the exact sign-flip test as a function of the number of paired seeds … | `figures/F33_statistical_design.png` |

<!-- pagebreak -->

## List of tables

| Table | Caption (short) |
|---|---|
| Table 1. | Dataset inventory. |
| Table 2. | Graph statistics for the FAFB v783 graph and the three BANC v888 thresholds. |
| Table 3. | Neural population inventory for FAFB v783, BANC v888, and the decoder-defined motor pools. |
| Table 4. | Complete model-parameter inventory. |
| Table 5. | Sensory feature mapping for BANC executions. |
| Table 6. | Phase 2.5 scalability measurements. |
| Table 7. | Decoder-defined motor populations on BANC v888. |
| Table 8. | Phase 4G condition outcomes on the BANC t5 graph. |
| Table 9. | Phase 7 controlled-game demonstration runs. |
| Table 10. | Phase 5F core conditions on the synthetic 36-node cued-response task. |
| Table 11. | Phase-by-phase implementation and validation summary. |
| Table 12. | Cumulative test-suite counts at major gates. |
| Table 13. | Phase 6 confirmatory mutual-information contrasts on Phase 5F artifacts at checkpoint 160. |
| Table 14. | Phase 8 conditions and control arms. |
| Table 15. | Phase 8 confirmatory contrasts and their mapped hypotheses. |
| Table 16. | Pilot 1 nine-episode A-viability grid. |
| Table 17. | D5 trained artifacts. |
| Table 18. | Pilot 2-C design grid. |
| Table 19. | Pilot 2-C per-episode outcomes. |
| Table 20. | Pilot 2-C certification claims P2C-1 through P2C-8. |
| Table 21. | Status of the Phase 8 contrasts and hypotheses and the Phase 6 confirmatory contrast. |
| Table 22. | Deviations register. |
| Table 23. | Consolidated limitations register. |
| Table 24. | Open questions for future research. |
| Table A1. | Repository components and their roles. |
| Table A2. | Executed-evidence directories and their authoritative records. |
| Table B1. | FAFB node composition by `super_class`, in neurons. |
| Table B2. | BANC v888 threshold sensitivity. |
| Table B3. | BANC `super_class` composition, in nodes. |
| Table C1. | Leaky integrate-and-fire parameters. |
| Table C2. | Synapse and sign-policy parameters. |
| Table C3. | Motor pools and decoder constants. |
| Table C4. | Plasticity and sensory-drive parameters. |
| Table D1. | Phase-by-phase outcomes. |
| Table D2. | Cumulative test-suite counts recorded at each phase boundary. |
| Table E1. | Phase 6 declared analysis constants. |
| Table E2. | Phase 6 recorded estimates. |
| Table E3. | Phase 6 endpoints that could not be estimated from the archive, with the recorded reason. |
| Table F1. | Confirmatory contrasts, mapped hypotheses, and the interpretation each would license. |
| Table G1. | Pilot 1 row sums. |
| Table G2. | Pilot 1 recorded checks. |
| Table H1. | Signed structural reachability from the 232 stimulated sensory neurons under the verified-only sign policy. |
| Table H2. | Recorded first-hop current and membrane values from the instrumented Phase 4H.4 run, which used the same … |
| Table H3. | Phase 4H.4 control conditions. |
| Table H4. | Positive controls showing that the decoder and motor populations can produce actions when driven directly. |
| Table I1. | Top-level sections of `training_run.json`. |
| Table I2. | Fields recorded for each training episode. |
| Table I3. | Fields recorded for each checkpoint entry. |
| Table I4. | The six D5/D6 artifacts. |
| Table J1. | Pilot 2-C claims and the observation that would falsify each. |
| Table J2. | The P1–P19 exact-comparison fields used by the A′ and C′ controls. |
| Table K1. | Recorded software versions. |
| Table K2. | Frozen input and configuration hashes recorded in every Pilot 2-C row. |
| Table K3. | Protocol and authorisation hashes. |
| Table K4. | Recorded resource and timing facts for the executed stages. |

# Chapter 1. Introduction

## 1.1 Motivation

A connectome is a map of physical connections. It states which neurons are joined by synapses and how many synapses join them. It does not state what any connection does, how strong it is electrically, which transmitter sign it carries in a given behavioural context, or how a population of such connections behaves when it is driven. The gap between a wiring diagram and a functioning sensorimotor system is therefore not a data-processing problem alone; it is a modelling and validation problem. FLY-SURFER was built to make that gap explicit and measurable in a small, fully specified setting: an adult fruit-fly connectome, a spiking simulation, a controlled endless-runner game, and a fixed action interface.

The fruit fly is an attractive subject for this purpose. Its brain and ventral nerve cord have been reconstructed at synapse resolution, its visual system and locomotor circuitry are extensively annotated, and its behavioural repertoire includes visually guided locomotion. The FlyWire FAFB v783 reconstruction of an adult female brain contains 139,255 neurons and 50,666,648 synapses in 3,732,460 directed pairs at a five-synapse threshold. The BANC v888 reconstruction of a female brain and ventral nerve cord contains 172,433 endpoint nodes and 1,535,710 edges at the same threshold, and — unlike the brain-only FAFB volume — it includes 805 annotated motor neurons. These datasets make it possible to ask a concrete question about structure and function without pretending that the map is the mechanism.

## 1.2 Central research question

The paper addresses one central question:

> **Can a connectome-derived fruit-fly neural network, implemented through spiking neural simulation and learning mechanisms, transform visual game information into functional motor commands in a controlled game environment?**

The question has three parts and each must be answered separately: whether visual information can be injected into the network in a defensible way; whether activity propagates from the injection site to motor populations; and whether learning mechanisms improve the mapping from network state to game action. A positive answer requires all three. A negative answer at any stage bounds what the later stages can show.

## 1.3 Secondary questions

Nine secondary questions structure the investigation. Each is answered in the chapter indicated.

1. **Connectome to computational network.** How can a connectome be converted into a computable network without confusing structural adjacency with physiological connectivity? (Chapters 3 and 6.)
2. **Visual information to sensory stimulation.** How can game-derived visual information be mapped onto sensory populations, and what is the epistemic status of that mapping? (Chapter 5.)
3. **Activity propagation.** Does injected activity propagate through the network, and how far? (Chapters 6, 10, 13, and 14.)
4. **Motor-population activity.** Do annotation-defined motor populations spike under sensory drive? (Chapters 7, 11, 13, and 14.)
5. **Fixed decoder to game actions.** Can a fixed decoder translate motor-population activity into game actions, and under what conditions? (Chapter 7.)
6. **Dopamine-inspired plasticity to cue-to-action information.** Does three-factor plasticity increase information about the cue in the action, measured without circularity? (Chapters 8 and 10.)
7. **Trainable readout to state-dependent decisions.** Does a trainable linear readout produce state-dependent decisions on the biological substrate? (Chapters 12, 15, and 16.)
8. **Comparison with alternative architectures.** Can the biological substrate be compared with degree- and sign-matched null graphs, random wiring, and non-biological learners? (Chapters 9, 12, and 16.)
9. **Limitations of structural connectome models.** What does the programme establish about the limits of structural connectome models for sensorimotor control? (Chapters 14, 18, and 19.)

## 1.4 What the project built

FLY-SURFER is a staged programme. Its components are:

- a reproducible connectome artifact built from FlyWire FAFB v783, with 139,255 indexed neurons, 3,732,460 directed pairs, and 50,666,648 summed synapses;
- a sparse leaky integrate-and-fire simulator with a 0.5 ms timestep, exponential synapses, a 1 ms delay, and a 139,255-neuron full-scale benchmark;
- a perception path from a YOLO11n ONNX detector through tracking and temporal event encoding to 14 game features, and a sensory scheduler that injects current into identified neurons;
- a second graph built from BANC v888, with 805 motor neurons, 1,316 descending neurons, 1,849 ascending neurons, and 683,100 signed edges at the five-synapse threshold;
- a fixed motor decoder that reads 50 ms windows over LEFT, RIGHT, and JUMP pools and emits LEFT, RIGHT, JUMP, or NO_ACTION;
- a reward-modulated three-factor plasticity rule and a trainable linear readout, both implemented and unit-tested;
- an information-theoretic evaluation of cue, neural, and action variables;
- a closed-loop game bridge and a controlled endless-runner environment;
- a pre-registered Phase 8 protocol (REV4) with six conditions and four controls, explicit estimands, an exact sign-flip test, and a Holm correction;
- two executed pilots (Pilot 1 and Pilot 2-C) and six certified training artifacts.

The architecture is summarised in Figure 1. The paper reports the programme as executed, including the parts that failed.

![Figure 1. End-to-end FLY-SURFER architecture. The frozen biological path (green) runs from the controlled game through perception, sensory scheduling, the connectome simulation, the motor decoder, and back to the game. Purple components (trainable readout, three-factor plasticity) were added in Phases 5 and 8. The MLP baseline E was specified but never run. Counts are frozen configuration values. Data source: none in the measured sense — this is a schematic drawn for this paper from the frozen configuration values listed in Tables 3 and 4, and it plots no recorded data.](figures/F01_system_architecture.png)

## 1.5 What the programme found

The headline result is a motor-output bottleneck. The network can be driven; it produces spikes; but the first post-sensory stage does not cross threshold. In the Phase 7 closed-loop demonstration, the network produced 2,852 spikes in 7,100 steps, all of them from directly stimulated sensory neurons, and zero motor-population spikes; the decoder therefore returned NO_ACTION on all 213 decisions. Pilot 1 repeated the result over nine episodes: 3,784 decisions, 126,135 neural steps, 73,880 recorded spikes, zero motor spikes. The dedicated bottleneck investigation traced this to the first hop: 662 signed first-hop edges reached 608 distinct targets, 473 of which received current, but the peak somatic depolarisation was −56.926 mV against a −50 mV threshold. The shortfall was 6.926 mV, and no second-hop current was generated.

This is not a software failure. A positive control in Phase 4G drove the ventral-nerve-cord intrinsic population directly and produced 1,296 spikes, 492 motor spikes across 82 motor neurons, and four JUMP decisions, showing that the decoder and the motor readout can fire when their inputs are active. The failure is therefore localised to the propagation from the sensory injection site into the motor network under the frozen parameterisation.

The learning components were evaluated as far as the silent motor channel permitted. The synthetic Phase 5F task showed that the implemented three-factor rule can learn a conditioned response (plastic success 0.945 versus fixed 0.795), but the Phase 6 information analysis found no confirmatory gain in cue-to-action mutual information on the biological substrate: the plastic-minus-fixed difference was −0.0863 bits (95% interval [−0.1751, 0.0052]), with exact sign-flip p = 0.125 and Holm-adjusted p = 0.25. The Phase 8 design was frozen and pre-registered, but only its pilots were executed. Six F/Fβ training artifacts were certified after 120 episodes, yet training was behaviourally null: zero motor spikes, zero weight change, and identical F/Fβ outcomes. Pilot 2-C then executed all 54 planned rows and passed all eight descriptive certification claims, but every arm — including the substrate-free floor — produced the same survival scores, so C1–C4 and H1–H3 are unevaluable rather than null.

## 1.6 What this paper does not claim

The paper does not claim that the network played Subway Surfers. It did not. The controlled environment is a separate endless-runner implementation, and the commercial game was never instrumented. The paper does not claim that structural edges are physiological connections, that predicted transmitters are measured signs, that synthetic decoder tests are biological motor activity, that implementation tests are experimental evidence, that Phase 6 found an information gain, that Pilot 1 or Pilot 2-C demonstrated functional game-playing, that Pilot 2-C certification proves biological learning, that C1–C4 or H1–H3 were evaluated, or that the N = 16 confirmatory campaign was executed. It does not hide the motor-silence finding, omit negative results, or silently correct historical records. Where a source record contains an error, the paper reports the error and the correct value side by side without editing the record.

## 1.7 Organisation

Chapter 2 places the work in the context of connectome simulation, insect motor control, spiking models, plasticity, information theory, and game environments. Chapter 3 describes the two biological datasets and their construction. Chapter 4 describes the overall architecture. Chapter 5 covers perception and sensory encoding. Chapter 6 covers the neuron and synapse model and simulation performance. Chapter 7 covers motor decoding and game control. Chapter 8 covers reward, plasticity, and information theory. Chapter 9 gives the development chronology and validation history. Chapters 10 and 11 report the Phase 6 information study and the Phase 7 closed-loop integration. Chapter 12 describes the Phase 8 experimental design. Chapters 13 and 14 report Pilot 1 and the motor-bottleneck investigation. Chapter 15 reports D5/D6 training and artifact certification. Chapter 16 reports Pilot 2-C. Chapter 17 consolidates results across phases. Chapters 18–21 give the discussion, limitations, conclusion, and future research. The references and eleven appendices follow.

# Chapter 2. Background and Related Work

## 2.1 From wiring diagrams to simulated circuits

Connectomics has moved from partial reconstructions of small circuits to whole-brain wiring diagrams at synapse resolution. The FAFB volume established that an entire adult *Drosophila* brain could be imaged and segmented [1], and the FlyWire project produced a proofread neuronal wiring diagram with cell-type annotations and predicted transmitters [2]–[4]. The BANC reconstruction extends the same approach to the brain and ventral nerve cord, which is where limb motor neurons reside [5]. These resources are structural: they report synapse counts between identified neurons, not conductance, reversal potential, short-term dynamics, or the sign of a connection in a particular behavioural state.

A structural graph can be turned into a dynamical model in many ways, and the choice is consequential. One may treat edges as directed weights and run a point-neuron network; one may fit a conductance-based model per cell type; one may use the graph only as a topology prior and learn the weights. Each choice answers a different question. FLY-SURFER adopted the simplest defensible option — a leaky integrate-and-fire (LIF) neuron with exponential synapses, a single uniform parameter set, predicted transmitter signs, and a calibrated weight transform — because the project's purpose was to test whether the structural graph, the sensory convention, and a minimal physiology could carry information from a game observation to a motor decision. A negative result under this option does not prove that the biological network cannot do so; it bounds what this particular mapping achieves.

## 2.2 Insect visual guidance and motor control

Flies guide locomotion with vision, mechanosensation, and descending commands. Motion vision has been characterised in detail [19], and walking modulates visual processing [17]. Collision detection and looming responses provide a well-studied sensorimotor pathway [18]. Haltere feedback and visual feedback jointly control body saccades [25]. Walking direction is controlled by identifiable descending neurons [16], and mechanosensory feedback is integrated with motor commands throughout the ventral nerve cord [20]. Central-complex circuits implement navigation and action selection [21], and the mushroom body provides a substrate for associative learning [22]. These findings motivate the use of a connectome as a control substrate, but they also show why a generic LIF model is a crude approximation: identified neurons have cell-type-specific physiology, adaptation, and neuromodulatory context that a single parameter set does not capture.

## 2.3 Spiking models and large-scale simulation

The LIF model is the standard reduced model of spike generation [6]. Large-scale reconstructions have been simulated with detailed compartmental models [23], and the case for brain simulation as a scientific method has been argued carefully [24]. The engineering problem in FLY-SURFER was different from those efforts: the graph is sparse but large (139,255 neurons and up to 50.7 million synapses), the timestep is small (0.5 ms), and the simulation must run inside a closed game loop on a single machine. This led to a sparse compressed-sparse-row (CSR) representation, a vectorised exponential-Euler update, and a benchmark programme that measured throughput and memory from 800 to 139,255 neurons.

## 2.4 Neuromodulated plasticity and credit assignment

Three-factor learning rules multiply a Hebbian or eligibility trace by a neuromodulatory signal [7]. The rule used here is a reward-modulated eligibility trace: Δw = η · M(t) · e(t), where e(t) is a decaying eligibility trace and M(t) is a scalar modulation derived from reward. This family of rules is biologically motivated and computationally simple, but it is not a full credit-assignment algorithm. It cannot route a scalar reward to the specific synapses responsible for an action unless eligibility traces and modulation are appropriately aligned. The synthetic Phase 5F task was designed to test that alignment in a setting where the correct response is known; the biological application was designed to test whether the rule changes cue-to-action information on the connectome substrate.

Reinforcement learning provides the formal language for the readout experiments [8]. The F condition is a linear policy trained with a score-function estimator; the Fβ condition is a bias-only policy. The comparison between them is a test of whether feature information is used, not a test of whether the biological network learns.

## 2.5 Information-theoretic evaluation

Mutual information I(X;Y) measures dependence in bits [9]. It is attractive for connectome work because it makes no linearity assumption and can be estimated for discrete variables. It is also treacherous at small sample sizes: plug-in estimators are biased upward, and the bias floor for two discrete variables with k_x and k_y levels is approximately (k_x−1)(k_y−1)/(2N ln 2). FLY-SURFER used plug-in estimates with a declared bias floor, block permutation tests, cluster bootstrap intervals, and Holm correction for multiple contrasts [10]–[12]. The Phase 6 analysis was pre-specified as descriptive where the design could not support causation, and the paper preserves that distinction.

## 2.6 Object detection and controlled game environments

The perception stage uses a YOLO-family detector [13], exported to ONNX and executed with a local runtime [14]. Detection quality is reported with COCO-style precision, recall, mAP50, and mAP50-95 [15]. The detector was trained outside this repository on a 14-class dataset derived from gameplay footage; its published validation metrics are provenance, not a result of this paper. The game environment is a standalone endless-runner implementation inspired by Subway Surfers [29]; the commercial game was never modified or controlled.

## 2.7 Positioning and gaps

Three gaps motivate the programme. First, whole-brain connectomes are increasingly available, but demonstrations that they can support closed-loop sensorimotor behaviour remain rare, and negative results are rarely reported in comparable detail. Second, connectome simulations often report activity statistics without a motor readout, or a motor readout without a structural pathway analysis. Third, learning claims on biological graphs are often made without a null model, without an information-theoretic estimand, or without distinguishing implementation tests from experiments. FLY-SURFER addresses all three by combining a structural pathway audit, a fixed decoder, a pre-registered information analysis, a certified null-graph construction, and an explicit evidence taxonomy. Its contribution is less a positive demonstration than a carefully bounded negative one: it shows where a structural connectome model, driven by a conventional sensory mapping and a uniform LIF physiology, stops propagating.

# Chapter 3. Biological Data and Connectome Construction

## 3.1 Data sources and governance

FLY-SURFER uses two published connectomes and one externally trained detector. The FlyWire FAFB v783 reconstruction of an adult female brain supplies the brain-only graph used for the simulation, perception, plasticity, and information analyses. The BANC v888 reconstruction of an adult female brain and ventral nerve cord supplies the graph used for motor decoding and all Phase 8 executions, because the FAFB volume does not contain the limb motor neurons that innervate the legs. The two graphs are kept separate. No FAFB root identifier is transferred to BANC, no BANC neuron is selected by FAFB connectivity, and no attempt is made to merge them into a single network. This separation is a design decision, not an implementation shortcut: the datasets come from different specimens, different reconstruction pipelines, and different annotation versions, and merging them would create unverifiable identities.

All datasets and processed artifacts are treated as read-only. The project did not download new data during this paper's preparation, did not regenerate graphs, and did not modify any stored artifact. The processed connectome file has SHA-256 `3f568f24…5f33d8` and is 28,013,212 bytes. The BANC artifacts are bound to five source hashes recorded in the Phase 4D report.

Table 1 summarises the datasets and artifacts used in the paper.

**Table 1.** Dataset inventory. Scale figures are the values recorded in the source artifacts. Data source: `datasets/processed/connectome_report.json`, `datasets/processed/banc_v888/banc_construction_report.json`, `reports/PHASE_3B02_V15_DATASET_AUDIT.json`, `models/YOLO11/deployment/yolo11n_v1_deployment/`; full machine-readable table in `tables/T01_dataset_inventory.csv`.

| Dataset | Version | Scale | Role | Provenance |
|---|---|---|---|---|
| FAFB (FlyWire) | v783 | 139,255 neurons; 3,732,460 directed pairs; 50,666,648 synapses | structural brain connectome | `datasets/processed/connectome.npz` |
| FAFB annotations | v783 | 119,597 annotated; 19,658 without transmitter | cell class, transmitter, side, position | `datasets/processed/nodes.csv.gz` |
| BANC | v888 | 172,433 endpoints; 1,535,710 edges at t5 | brain + VNC connectome; motor interface | `datasets/processed/banc_v888/` |
| BANC nulls | seeds 1–16 | 16 certified graphs, same edge count | degree/sign-preserving nulls | `datasets/processed/banc_v888_random/` |
| Detector dataset | v15 | 2,328 images; 8,666 boxes; 14 classes | detector supervision | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` |
| YOLO11n weights | v1 deployment | 10,636,871 bytes; 1×3×640×640 input | visual perception | `models/YOLO11/deployment/…/best.onnx` |
| endless-surfer | standalone | 200/900-step episodes; 25-unit horizon | controlled game environment | `external/endless-surfer-main` (third-party clone, not distributed) |

## 3.2 The FAFB graph artifact

The FAFB artifact (`datasets/processed/connectome.npz`) stores the graph as flat arrays: `root_ids`, `out_indptr`, `edge_src`, `edge_dst`, `edge_weight`, `in_indptr`, `in_edge_idx`, `positions`, `position_mask`, `nt_code`, `super_class_code`, `class_code`, `side_code`, `flow_code`, a vocabulary object, and a metadata object. The graph retains directed pairs with at least five summed synapses. Applying that threshold yields 139,255 indexed neurons, 3,732,460 directed pairs, and 50,666,648 summed synapses. Figure 2 summarises the construction and Figure 3 shows the resulting weight and degree distributions.

![Figure 2. FlyWire FAFB v783 connectome construction summary. Bars show indexed neurons, annotated neurons, neurons without a predicted transmitter, retained directed pairs at the five-synapse threshold, summed synapses in retained pairs, and isolated neurons. Data source: datasets/processed/connectome_report.json.](figures/F02_flywire_construction.png)

![Figure 3. FlyWire FAFB v783 edge-weight and degree distributions computed from the stored edge arrays. (a) Summed synapses per retained directed pair on a log scale; the minimum is the threshold of 5. (b) Complementary cumulative distribution of out-degree. (c) Complementary cumulative distribution of in-degree. Data source: datasets/processed/connectome.npz.](figures/F03_fafb_distributions.png)

The weight distribution is heavy-tailed: the mean summed synapse count is 13.575, the minimum is 5 by construction, and the maximum is 2,633. Out-degree is also heavy-tailed, with a mean of 26.803 and a maximum of 6,523; in-degree reaches 6,261. There are 620,180 directed reciprocal pairs, corresponding to 310,090 unordered reciprocal connections. These statistics matter for simulation: the sparse matrix has 50.7 million non-zeros, but the degree distribution means that a small number of hub neurons can generate very large propagation bursts. The simulator's worst-case temporary allocation is sized for this, and the full-graph benchmark is discussed in Chapter 6.

**Table 2.** Graph statistics for the FAFB v783 graph and the three BANC v888 thresholds. Synapse counts are sums over retained directed pairs. Data source: `datasets/processed/connectome_report.json` and `datasets/processed/banc_v888/banc_construction_report.json`; full machine-readable table in `tables/T02_connectome_statistics.csv`.

| Graph | Threshold | Nodes | Directed edges | Summed synapses | Isolated | Mean weight | Max weight |
|---|---:|---:|---:|---:|---:|---:|---:|
| FAFB v783 | 5 | 139,255 | 3,732,460 | 50,666,648 | 671 | 13.575 | 2,633 |
| BANC v888 | 1 | 172,433 | 11,596,517 | 34,310,230 | 6,232 | 2.9587 | 913 |
| BANC v888 | 5 | 172,433 | 1,535,710 | 18,552,546 | 24,320 | 12.0808 | 913 |
| BANC v888 | 10 | 172,433 | 570,721 | 12,397,230 | 62,551 | 21.722 | 913 |

## 3.3 FAFB annotations and population inventory

Annotations are predictions [3]. The node table provides a super-class label for most neurons, a predicted transmitter for most, a side label, positions, and a mask indicating whether a position is valid. Of 139,255 neurons, 119,597 carry at least one annotation and 19,658 have no predicted transmitter. The transmitter composition at the five-synapse graph is 82,298 cholinergic, 19,605 glutamatergic, 16,017 GABAergic, 1,021 serotonergic, 584 dopaminergic, and 72 octopaminergic neurons. The super-class composition is dominated by optic-lobe neurons (77,873), followed by central neurons (32,381), sensory neurons (16,938), visual-projection neurons (7,684), ascending neurons (1,750), descending neurons (1,305), sensory-ascending neurons (612), visual-centrifugal neurons (522), motor-superclass neurons (110), and endocrine neurons (80). Side labels are available for 69,959 left, 69,093 right, and 173 centre neurons.

The FAFB motor super-class contains 110 neurons, none of which are the leg motor neurons required for a walking or jumping readout. This is the decisive compatibility finding of Phase 4A: the FAFB volume is brain-only, and the ventral nerve cord — where limb motor neurons reside — is absent. Table 3 lists the population inventory for both datasets and for the decoder-defined motor pools. The table is descriptive; a super-class label is not a functional identification, and a motor label does not establish that a neuron drives a particular leg movement.

**Table 3.** Neural population inventory for FAFB v783, BANC v888, and the decoder-defined motor pools. Counts are annotation-derived, not measured physiological populations. Data source: `datasets/processed/connectome_report.json`, `datasets/processed/banc_v888/banc_nodes.csv.gz`, and `configs/motor_decoder.yaml`; full machine-readable table in `tables/T04_population_inventory.csv`.

| Dataset | Population | Count | Basis |
|---|---|---:|---|
| FAFB v783 | optic | 77,873 | super_class |
| FAFB v783 | central | 32,381 | super_class |
| FAFB v783 | sensory | 16,938 | super_class |
| FAFB v783 | visual_projection | 7,684 | super_class |
| FAFB v783 | ascending | 1,750 | super_class |
| FAFB v783 | descending | 1,305 | super_class |
| FAFB v783 | sensory_ascending | 612 | super_class |
| FAFB v783 | visual_centrifugal | 522 | super_class |
| FAFB v783 | motor | 110 | super_class |
| FAFB v783 | endocrine | 80 | super_class |
| BANC v888 | optic_lobe_intrinsic | 72,826 | super_class |
| BANC v888 | central_brain_intrinsic | 31,347 | super_class |
| BANC v888 | unannotated | 20,573 | super_class |
| BANC v888 | sensory | 15,956 | super_class |
| BANC v888 | ventral_nerve_cord_intrinsic | 12,850 | super_class |
| BANC v888 | visual_projection | 7,284 | super_class |
| BANC v888 | glia | 6,281 | super_class |
| BANC v888 | ascending | 1,849 | super_class |
| BANC v888 | descending | 1,316 | super_class |
| BANC v888 | motor | 805 | super_class |
| BANC v888 | sensory_ascending | 514 | super_class |
| BANC v888 | visual_centrifugal | 470 | super_class |
| BANC v888 | visceral_circulatory | 221 | super_class |
| BANC v888 | trachea | 83 | super_class |
| BANC v888 | not_a_neuron | 40 | super_class |
| BANC v888 | sensory_descending | 13 | super_class |
| BANC v888 | ascending_visceral_circulatory | 5 | super_class |
| BANC v888 | LEFT pool | 185 | decoder annotation |
| BANC v888 | RIGHT pool | 186 | decoder annotation |
| BANC v888 | JUMP pool | 20 | decoder annotation |
| BANC v888 | motor unassigned | 414 | decoder annotation |
| BANC v888 | tergotrochanter candidates | 20 | annotation |
| BANC v888 | VNC intrinsic (graph) | 12,850 | is_vnc_intrinsic |
| BANC v888 | stimulated sensory neurons | 232 | experimental mapping |

## 3.4 The BANC graph and threshold sensitivity

The BANC source table contains 188,508 metadata rows, of which 16,075 are metadata-only rows that do not correspond to an endpoint node. Excluding them leaves 172,433 endpoint nodes. The original edge list contains 11,752,828 edges and 156,311 self-edges, which are excluded along with 1,422,866 self-loop synapses, leaving 11,596,517 non-self edges. Thresholding at one, five, and ten summed synapses produces the graphs in Figure 4. At threshold 1 the graph has 11,596,517 edges and 34,310,230 synapses with 6,232 isolated nodes; at threshold 5 it has 1,535,710 edges and 18,552,546 synapses with 24,320 isolated nodes; at threshold 10 it has 570,721 edges and 12,397,230 synapses with 62,551 isolated nodes. The five-synapse graph therefore retains 13.24% of pairs but 54.07% of synapses, a direct consequence of the heavy-tailed weight distribution; the mean weight rises from 2.959 at t1 to 12.081 at t5 and 21.722 at t10.

![Figure 4. BANC v888 graph construction and threshold sensitivity. (a) Directed edges and summed synapses retained at thresholds 1, 5, and 10. (b) Construction stages: metadata rows, endpoint nodes, original edges, and retained t5 edges. Data source: datasets/processed/banc_v888/banc_construction_report.json.](figures/F04_banc_construction.png)

The five-synapse threshold is used throughout because it matches the FAFB threshold and removes pairs supported by a single or very few synapses, which are the most likely to reflect segmentation or annotation error. This is a modelling convention, not a claim that five synapses is a biological criterion for a functional connection.

## 3.5 BANC annotations and coverage

BANC annotation coverage is uneven (Figure 5). A super-class label is present for 88.07% of endpoint nodes, a cell-type label for 68.20%, a side label for 91.74%, and a body-part-effector label for only 0.60%. A predicted neurotransmitter is present for 89.27% of nodes, and 37.87% carry a verified label. The composition is dominated by optic-lobe intrinsic neurons (72,826), central-brain intrinsic neurons (31,347), unannotated nodes (20,573), sensory neurons (15,956), VNC intrinsic neurons (12,850), visual-projection neurons (7,284), and glia (6,281), with 1,849 ascending, 1,316 descending, and 805 motor neurons. The low effector coverage is the key limitation for the decoder: the LEFT, RIGHT, and JUMP pools are built from whatever side and effector annotations exist, and 414 of the 805 motor neurons cannot be assigned to any of the three pools.

![Figure 5. BANC v888 annotation coverage and neuronal composition. (a) Coverage of super-class, cell-type, side, and body-part-effector annotations. (b) Super-class composition for the twelve largest populations. Data source: datasets/processed/banc_v888/banc_nodes.csv.gz.](figures/F05_banc_annotation.png)

Transmitter predictions are also incomplete. Under the verified-only sign policy, an edge is excitatory if its presynaptic transmitter is acetylcholine or glutamate, inhibitory if GABA or glycine, and excluded if the transmitter is a modulator or missing. At the five-synapse threshold only 44.48% of edges carry a usable sign (683,100 edges, 8,426,168 synapses). The rest are structurally present but electrically undefined in the model. Chapter 7 explains how the decoder and the simulation handle this.

## 3.6 Why the motor stage uses BANC

The FAFB and BANC datasets overlap in the brain but differ in coverage. Phase 4A compared them and found 139,241 shared root identifiers, 14 FAFB-only identifiers, and 7 annotation-only identifiers. The high overlap is expected because both reconstruct the same brain region, but the overlap does not make the graphs interchangeable: the annotation versions differ, the IDs are dataset-specific, and the BANC adds the VNC. The decisive difference is the presence of 805 motor neurons and 1,316 descending neurons in BANC versus 110 motor-superclass neurons and 1,305 descending neurons in FAFB. The FAFB descending count is similar, but the FAFB motor neurons do not include leg effectors. Using FAFB for the motor readout would therefore have required assuming that a brain motor neuron stands in for a leg motor neuron, which the project declined to do. BANC is used for every motor-relevant result; FAFB is used only where the question concerns the brain graph itself.

## 3.7 Dataset inventory and detector provenance

Table 1 (Section 3.1) lists the datasets, their versions, scales, roles, and provenance. The detector dataset is not duplicated in the repository; it is referenced by its audit reports. The YOLO11n weights are 10,636,871 bytes with SHA-256 `e6ad18f9…6aa77`, and the published validation metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, and mAP50-95 0.687726 on 1,128 validation images — are recorded as provenance. They were not re-measured in this paper, and the repository does not contain an independent test split.

## 3.8 Summary

The programme has a large, well-annotated brain graph and a large brain–VNC graph with a usable motor interface, but the interfaces are not free. The FAFB graph lacks limb motor neurons; the BANC graph has sparse effector annotations and only 44.48% signed edges; both are structural. These constraints propagate into every later result and are therefore stated before any simulation result is reported.

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

# Chapter 5. Visual Perception and Sensory Encoding

## 5.1 What the perception stage must deliver

The perception stage has one job: convert a game frame into a small set of typed events that the sensory encoder can turn into current. It does not need to understand the scene, identify objects persistently, or estimate the player's posture. It needs to detect the object classes that the game's collision logic uses — trains, ramps, walls, and three barrier variants — assign each detection to one of three lanes and a distance band, and emit events with timestamps. Everything downstream is driven by those events.

The stage is deliberately thin. The detector is used as a fixed, externally trained component and was not retrained, fine-tuned, or calibrated during this project. The detector's reported performance is therefore a property of the supplied deployment, not a result of the work reported here. This distinction matters because a reader might otherwise attribute the detector's accuracy to the connectome pipeline.

## 5.2 The detector

The detector is a YOLO11n model exported to ONNX. Its input is a single float32 tensor of shape 1×3×640×640 in NCHW layout; its output before post-processing is a 1×18×8,400 tensor, decoded into 14 class scores and four box coordinates per anchor. The deployed weight file is 10,636,871 bytes with SHA-256 `e6ad18f9…6aa77`. Inference uses a per-class confidence threshold of 0.426 and non-maximum suppression at IoU 0.7, as recorded in the deployment configuration.

The deployment manifest reports precision 0.937310, recall 0.810829, mAP@0.5 0.897776, and mAP@0.5:0.95 0.687726 on the 1,128-image validation split. These values were produced in the training environment; they were not re-measured on this host, and the integration audit explicitly labels them grouped-validation results rather than independent test-set results. The paper reports them with that scope. No claim in later chapters depends on the detector reaching these values.

The 14 detector classes are `boots-powerup`, `boxtrain`, `jump-barrier`, `jump-electric`, `jump-hedge`, `jump-roll-barrier`, `jump-trash`, `ledge`, `pogstick-powerup`, `ramp`, `roll-barrier`, `train`, `undercover-barrier`, and `wall`. There is no player class and no coin class. This is the single most consequential fact about the perception stage: the dataset cannot tell the pipeline where the player is, whether the player is jumping or rolling, or where a coin is. Those features are reported as unmapped rather than inferred.

## 5.3 The annotated dataset and its split structure

The detector dataset is Roboflow "subway surfers object dataset" version 15, licensed CC BY 4.0. It contains 2,328 images and 2,328 label files with 8,666 boxes across the 14 classes. Twelve label files are empty; they were inspected individually and excluded from the curated splits, because an empty label in this dataset is not evidence of an empty scene — nine of the twelve sit inside a contiguous run bracketed by frames with four and five boxes, and previews show trains, wagons, and barriers.

The official split is 1,825 training images and 503 validation images, with no test split. Figure 8 shows the class inventory and the official split.

![Figure 8. Subway Surfers v15 annotation inventory by class and official split. Bars show labelled boxes per class in the official training and validation sets. This is the dataset inventory, not a test set: the release has no test split, and the deployed detector uses a group-held-out curation described in the text. Data source: reports/PHASE_3B02_V15_DATASET_AUDIT.json.](figures/F08_dataset_inventory.png)

The official split is not usable as an evaluation split without qualification. Adjacent-frame analysis found that 554 of 1,724 consecutive-frame pairs (32.1%) cross the train/validation boundary, and a perceptual near-duplicate audit at 64-bit dHash Hamming distance ≤4 found 224 near-duplicate pairs, 58 of which cross the split. The dataset also contains five source recording groups, and the official split cuts every group across both sides. One group, `subwayy1_1`, contains two recordings that collide on 296 frame identifiers; those pairs are genuinely different images (dHash distance 9–39, all label pairs differ), so they cannot be deduplicated by filename.

Curation therefore re-split the data by recording group rather than by frame. Three groups (`subwayavitomp4`, `subwayedited2`, `subwayedtied`) form the 1,188-image training side; two groups (`datasetfootage`, `subwayy1_1`) form the 1,128-image validation side; the 12 empty-label files are excluded. No group appears on both sides. This is a grouped development split, not an independent test set: all five groups come from the same game and the same capture pipeline, and there is no sixth recording to hold out. The report is explicit that the design supports development and variance estimation, not an unbiased estimate of performance on unseen game footage. Chapter 19 treats this as a threat to validity.

The figures in this section document the actual data and the actual deployed weight; they are evidence about the detector, not about the connectome. Every image is a project file from the curated split described above. No image is synthetic, none comes from outside the dataset, and no box is invented: each ground-truth box is one row of a label file, and each prediction is the output of the deployment ONNX model at the deployment thresholds. The model was not retrained, fine-tuned, or calibrated to produce any of these panels, and none of them re-estimates an accuracy metric.

### 5.3.1 Visual dataset samples and annotation examples

Figure 9 shows one unmodified training image for each of six high-frequency classes: `train`, `boxtrain`, `ramp`, `wall`, `jump-roll-barrier`, and `jump-barrier`. The selection is deterministic: for each class the largest labelled instance is chosen, with 64-bit dHash distance at least 12 and at least 40 frames of separation within a recording, so the six images are not near-duplicates of one another. The images are displayed as stored, without stretching or cropping, and deliberately carry no annotation overlay so that the raw scene can be inspected before the boxes are added.

![Figure 9. Six unmodified curated training images, one for each of six high-frequency classes, with no annotation overlay. Split: curated training (1,188 images, 4,704 boxes; groups subwayavitomp4, subwayedited2, subwayedtied), group-held-out development data and not an independent test set. Data source: datasets/exports/phase_3b2b1_yolo11n/train/images (original files from the Roboflow "subway surfers object dataset" v15 release). Images: subwayedited2_mp4-126_jpg.rf.048ee9c2e9c53dbe1a5cc70aea1fbb00.jpg; subwayedited2_mp4-226_jpg.rf.06e5611632b20f0221ea1400b4267f59.jpg; subwayedtied_mp4-59_jpg.rf.23133e519a4ca7a9adf6a2dfc8fcec7c.jpg; subwayedtied_mp4-163_jpg.rf.ecc60997dfab88d97acfb9ec5dddaa7e.jpg; subwayavitomp4_mp4-907_jpg.rf.30cf28613c091e5ca32a7b53991df15e.jpg; subwayavitomp4_mp4-449_jpg.rf.6409b26145a57f4adffe35e9b0c318b7.jpg. Their label-file ground truth is drawn in Figure 10.](figures/yolo11_visuals/Y01_training_samples.png)

Figure 10 draws the ground truth for the same six images. Each YOLO label row (class, centre x, centre y, width, height) is converted to pixel coordinates with the original 606×1050 image size; every box on screen corresponds to exactly one label row. Colours identify classes and the legend beneath each image gives the class names and counts. The labels are the dataset's own annotations, not a relabelling produced for this paper, and their occasional looseness — a large box for a distant train, a box that includes surrounding track — is visible rather than corrected.

![Figure 10. Ground-truth annotations for the six curated training images of Figure 9, drawn from the original YOLO label files at the original image scale. Split: curated training. Data source: datasets/exports/phase_3b2b1_yolo11n/train/labels, converted from normalised coordinates to pixels with the 606×1050 image size; box colour identifies the class. Images: the six files listed in the Figure 9 caption. There is no player class and no coin class in the label schema.](figures/yolo11_visuals/Y02_ground_truth.png)

Figure 11 covers all 14 classes rather than the six high-frequency ones. For each class it shows a square crop centred on the largest labelled instance in the curated training split and reports how many training images and boxes contain that class. Four classes are marked as low support (fewer than 40 training images): `boots-powerup` (24), `jump-electric` (14), `jump-hedge` (17), and `jump-trash` (33). The same disclosure is what the validation split implies: it contains no `boots-powerup` and no `jump-electric` annotation at all, so those two classes cannot be evaluated there. The figure shows the least-sampled instance available rather than inventing an example, and the low-support marker is a warning, not a decoration.

![Figure 11. One labelled instance for each of the 14 detector classes from the curated training split, with the number of images and boxes containing that class and low-support classes marked. Split: curated training. Data source: datasets/exports/phase_3b2b1_yolo11n/train images and label files. Source images in class order, boots-powerup to wall: subwayedtied_mp4-242, subwayedited2_mp4-133, subwayavitomp4_mp4-449, subwayedited2_mp4-331, subwayedited2_mp4-247, subwayavitomp4_mp4-907, subwayavitomp4_mp4-1030, subwayedited2_mp4-335, subwayedtied_mp4-185, subwayedtied_mp4-59, subwayedited2_mp4-112, subwayedited2_mp4-126, subwayavitomp4_mp4-465, subwayedited2_mp4-187; full filenames are listed in figures/yolo11_visuals/FIGURE_INDEX.md. The curated validation split contains no boots-powerup and no jump-electric annotations.](figures/yolo11_visuals/Y03_class_diversity.png)

### 5.3.2 Deployed YOLO11n prediction examples

The panels in this section are genuine forward passes of the deployment weight, executed locally through the repository `OnnxRuntimeDetector` on CPU with one thread. The model file is the same 10,636,871-byte ONNX file whose SHA-256 is verified at load. Preprocessing is the deployment letterbox to 640×640 with RGB order and pad value 114; the raw 1×18×8,400 output is decoded with the identity 14-class map, a per-class confidence threshold of 0.426, and class-aware non-maximum suppression at IoU 0.70 with at most 300 detections. Nothing about the model, weights, thresholds, or class map was changed to make these panels, and no aggregate precision, recall, or mAP is computed from them.

To keep the example set reproducible without fishing for successes or failures, the selection pool is fixed in advance: every ninth curated-validation image in sorted filename order (125 of 1,128 images). Over that pool the detector produced 73 images with no unmatched box and no miss, 25 with a miss and no extra detection, 7 with an extra detection and no miss, and 20 with both; the panels below are drawn from these categories with near-duplicate and same-recording frame separation enforced. The pool exists only to choose illustrative examples. It is not an evaluation sample, and its category counts are not a performance estimate.

![Figure 12. Actual predictions of the deployed YOLO11n ONNX model on six curated validation images at the deployment confidence and NMS settings, with predicted class and confidence. Split: curated validation (1,128 images; groups datasetfootage, subwayy1_1), group-held-out development data and not an independent test set. Model: models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx, SHA-256 e6ad18f9…6aa77, confidence 0.426, NMS IoU 0.70, 640×640 letterbox, identity 14-class map; not retrained, fine-tuned, or calibrated for this figure, and no accuracy metric is re-estimated. Images: datasetfootage_mp4-111_jpg.rf.9c94c489144333ad643331ec11166aa8.jpg; datasetfootage_mp4-11_jpg.rf.b9a41c0c0af4f913b7542d9bc25283ac.jpg; datasetfootage_mp4-160_jpg.rf.e08632470fabc8383d3e4f0b79ead5c4.jpg; datasetfootage_mp4-200_jpg.rf.ba24aac5f964e1c2d40e2a294ae55ab9.jpg; datasetfootage_mp4-266_jpg.rf.150650a46b175c1a983765d32f4231a2.jpg; datasetfootage_mp4-306_jpg.rf.a4dedacfee7bb4698d43edabf8f32cf0.jpg.](figures/yolo11_visuals/Y04_predictions.png)

Figure 13 places ground truth and prediction side by side at identical scale so that a box difference is a model difference rather than a display difference. Matching is greedy one-to-one among same-class boxes at IoU ≥ 0.5; a ground-truth box with no partner counts as missed and a prediction with no partner counts as extra. Two of the four pairs are exact (three of three and one of one), one has a miss and an extra, and one has a miss with no extra. The pairs were chosen to include imperfect outcomes.

![Figure 13. Paired ground-truth and detection panels for four curated validation images at identical scale, with unmatched boxes counted under the stated matching rule. Split: curated validation. Data source: curated validation label files plus the deployment ONNX model (SHA-256 e6ad18f9…6aa77). Matching: greedy one-to-one same-class matching at IoU ≥ 0.5; "missed" counts unmatched ground-truth boxes and "extra" counts unmatched detections. Images: datasetfootage_mp4-111_jpg.rf.9c94c489144333ad643331ec11166aa8.jpg; datasetfootage_mp4-11_jpg.rf.b9a41c0c0af4f913b7542d9bc25283ac.jpg; datasetfootage_mp4-128_jpg.rf.13ca4d313d3eb2863888fde6ab4133b7.jpg; datasetfootage_mp4-144_jpg.rf.96feccc148883a09a538cbf58078efb3.jpg.](figures/yolo11_visuals/Y05_gt_vs_prediction.png)

Figure 14 assembles the error categories deliberately. It includes two exact panels, one panel with a missed ground-truth object, one with an extra detection, one with both, and one whose match sits in the low-confidence band above the deployment threshold (0.426–0.526). The panel legend names the class of each missed object and lists prediction confidences. The footer states which categories occur in this particular selection, and it states explicitly that absence in this sample is not evidence that the model never makes that error. Categories that do not appear here, such as a miss of a class absent from the validation split, are not represented because the data cannot represent them.

![Figure 14. Detection examples and limitations: correct detections, missed ground-truth objects, extra detections and low-confidence matches, with explicit disclosure of which error categories were observed in the selected panels. Split: curated validation. Data source: curated validation label files plus the deployment ONNX model (SHA-256 e6ad18f9…6aa77), at confidence 0.426 and NMS IoU 0.70; matching by greedy one-to-one same-class IoU ≥ 0.5. Images: datasetfootage_mp4-193_jpg.rf.55e7d98f04df72dcf517ea956290b813.jpg; datasetfootage_mp4-225_jpg.rf.cc9bafabe3faa41e7bb6f0ffb4fa94b0.jpg; datasetfootage_mp4-258_jpg.rf.43b143cb0c29b76eb109581633f230bd.jpg; datasetfootage_mp4-299_jpg.rf.a3e50a68f7f8e68c7d2ab14489c891e6.jpg; datasetfootage_mp4-330_jpg.rf.02041097f7d23f09b2e7f3c8cfe2c314.jpg; subwayy1_1_mp4-175_jpg.rf.02828cfd3f8f906ee3fc01bdd5c32725.jpg.](figures/yolo11_visuals/Y06_detection_examples.png)

## 5.4 From boxes to events

Boxes are associated across frames by a class-aware tracker. A track becomes confirmed after two matched frames, and confirmed tracks generate typed temporal events: appearance, approach, recession, occlusion, disappearance, and an `uncertain` state for tentative or low-confidence tracks. Lane assignment is geometric, using the horizontal position of the box in the frame; distance is an uncalibrated bottom-edge proxy, not metres. The schema is explicitly image-geometric.

The tracking and temporal layers were exercised on synthetic sequences before being applied to real footage. The Phase 3C calibration generated 50 sequences across adversarial and ordinary families. On those synthetic sequences the pipeline recovered 175 true-positive events with 0 false positives and 0 false negatives, achieved a direction accuracy of 0.996 and a tracking continuity of 0.944, produced 5 identifier switches, and emitted 130 pulse events. These numbers measure whether the implementation realises its declared rules on controlled inputs. They are not perception performance on real video, and this paper does not present them as such.

The real-sequence replay, Phase 3B.2C, ran the detector on 100 consecutive frames of the `datasetfootage` group (frames 100–199) and passed the resulting events through tracking, encoding, and a full FAFB simulation. The perception counts from that replay are shown in Figure 15.

![Figure 15. Perception and tracking counts in the Phase 3B.2C real-sequence replay (datasetfootage frames 100–199). Stages from left to right: detector candidates, candidates above threshold, accepted detections, track identifiers, track observations, temporal events, and pulse events. The class breakdown of the 327 accepted detections is shown in the inset. Data source: experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json.](figures/F09_3b2c_perception.png)

The detector produced 334 candidates over the 100 frames, of which 2,769 anchor-level decodings passed the confidence threshold; after per-class suppression and lane/role acceptance, 327 detections were accepted, 7 were rejected for falling outside the frame bounds, and 18 were clipped to the boundary. The accepted detections were 120 `train`, 63 `boxtrain`, 60 `ramp`, 41 `wall`, 37 `jump-roll-barrier`, and 6 `jump-barrier`. The tracker created 46 track identifiers, accumulated 475 observations, marked 106 observations as occluded, and emitted 42 lost-track events. The temporal layer produced 215 events and 43 pulse events, with 5 observable lane changes and 0 gap frames.

These counts must be read with the replay's own limitations. There are no annotated object identities in the footage, so a tracker identifier is not an object identity and an identifier switch cannot be distinguished from a real object change. Occlusion is inferred from missed associations rather than observed. Most importantly, the replay's action-selection field reads "none; the chain ends at sensory current injection", and its claim flags mark gameplay success, biological perception, annotated identity tracking, independent test-set use, plasticity, and detector retraining all false. The replay demonstrates that the perception-to-event chain executes end to end; it does not demonstrate that the fly brain perceived the game, and it never reaches a motor decision.

## 5.5 Sensory encoding

Sensory encoding exists in two versions with different scopes, and the paper keeps them separate.

The first is the Phase 3A encoder on FAFB. It defines 14 features: player lane, player speed, jumping, rolling, obstacle presence, obstacle lane, obstacle distance, obstacle type, train presence, train lane, train distance, coin presence, coin lane, and coin distance. Feature activations are dimensionless in [0, 1]. Boolean features drive a fixed group of neurons; lane features drive one of three disjoint groups; Gaussian features drive a population with a tuning curve

r_i(x) = baseline + (amplitude − baseline) · exp(−(x − μ_i)² / (2σ²)),

where μ_i are evenly spaced preferred values, σ = σ_fraction · (x_max − x_min), and σ_fraction = 0.2. The scheduler converts activations to current pulses of at most 200 pA per neuron, decaying over 150 ms, with the game state updated every 50 ms. The Phase 3A mapping allocates 138 FAFB neurons across the 14 features. Phase 3A.5 calibrated this encoder on a small sweep: it retained 200 pA and σ_fraction 0.20 (the amplitude and tuning searches fell back to the declared defaults because no ordered alternative was available) and selected a population of four neurons, recording spike counts of 2, 6, and 7 at distances 0.15, 0.55, and 0.90 across three seeds, with an ordered response in all three seeds and a d′ proxy of 2.357. Additivity of the combined condition was 0.0. These are calibration observations on declared inputs, not a sensory code discovered in the connectome.

The second version is the Phase 4H.4 BANC mapping used by every BANC execution, including Phase 7 and all Phase 8 runs. It defines seven features — the subset the v15 event stream can actually emit — and allocates 232 BANC neurons to them: 48 to `train_lane`, 48 to `obstacle_lane`, 24 to `obstacle_type`, 24 to `train_present`, 24 to `obstacle_present`, 32 to `train_distance`, and 32 to `obstacle_distance`. Each feature carries 200 pA and a 150 ms decay. The mapping excludes every motor neuron and every LEFT/RIGHT/JUMP pool neuron before selection, and the adapter asserts zero overlap. Table 5 lists the mapping and, critically, the evidence tier for each feature.

**Table 5.** Sensory feature mapping for BANC executions. "Evidence" records what the published annotation supports; "hypothesis" is the untested assignment identifier. All seven assignments are computational hypotheses, including those whose pools come from published annotations. Data source: `configs/banc_sensory_mapping.yaml`; full machine-readable table in `tables/T05_sensory_features.csv`.

| Feature | Neurons | Current (pA) | Decay (ms) | Evidence | Hypothesis |
|---|---:|---:|---:|---|---|
| train_lane | 48 | 200 | 150 | computational convention | H4H4-B |
| obstacle_lane | 48 | 200 | 150 | computational convention | H4H4-E |
| obstacle_type | 24 | 200 | 150 | computational convention | H4H4-G |
| train_present | 24 | 200 | 150 | published annotation | H4H4-A |
| obstacle_present | 24 | 200 | 150 | published annotation | H4H4-D |
| train_distance | 32 | 200 | 150 | connectivity hypothesis | H4H4-C |
| obstacle_distance | 32 | 200 | 150 | connectivity hypothesis | H4H4-F |
| **Total** | **232** | | | | |

The distinction between the two mappings is not cosmetic. In the FAFB replay, 138 neurons were stimulated and 14 features were schedulable, including player pose and coin features that the replay's event schema reports as zero because the detector cannot emit them. In the BANC executions, 232 neurons were stimulated and only seven features were schedulable; player lane, player speed, jumping, rolling, coin presence, coin lane, and coin distance are listed as unmapped, not as zero-valued observations. Any comparison between the two must therefore name its scope. This paper does not pool the 138-neuron and 232-neuron stimulation results.

Figure 17 shows the scheduler's per-feature current record from the FAFB replay.

![Figure 17. Sensory schedule in the Phase 3B.2C replay: current delivered per game feature. Bars show peak frame-level feature current; the per-neuron cap is 200 pA and the maximum frame current is 9,288.797 pA. Coin and player-pose features carry zero current because the v15 detector schema has no coin or player class. Data source: experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json (scheduler block).](figures/F11_sensory_currents.png)

The scheduler's own summary records a maximum frame current of 9,288.797 pA, a maximum single-pulse current of 3,696.218 pA, and a per-neuron maximum of exactly 200.0 pA. It also records 14 "active" features, but three of them — coin presence, coin lane, and coin distance — contribute zero current, and jumping and rolling are zero throughout this footage. The count of active features is therefore a schema count, not a count of features that carried drive.

## 5.6 What the replay established about propagation

The FAFB replay ran 6,601 simulation steps over 3,300.5 ms of game time on the full 139,255-neuron graph. It produced 15,654,631 spikes from 35,979 active neurons, a 25.84% active fraction, at a mean per-neuron rate of 34.0606 Hz and a population rate of 33.9628 Hz. Of those spikes, 3,710 came from the 138 stimulated neurons and 15,650,921 came from the other 139,117 neurons. The non-stimulated share is 0.999763.

![Figure 16. Spike attribution in the Phase 3B.2C full-FAFB replay. The 138 stimulated neurons produced 3,710 spikes (0.0237% of 15,654,631); the remaining 139,117 neurons produced 15,650,921. Of the stimulated neurons, 72 fired at least once (52.17%). Data source: experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json (activity_by_stimulation).](figures/F10_3b2c_attribution.png)

The ratio is the first indication of the project's central problem. Almost all spiking in this network is spontaneous or recurrent, not sensory-driven. The stimulated pool fired on 52.17% of its neurons, but its spikes are a rounding error against the background. A decoder that reads population rates will therefore see mostly background, and a downstream neuron's firing cannot be attributed to the stimulus without an explicit causal analysis. That analysis was performed later, on the Pilot 1 run, and is reported in Chapter 14.

The replay's execution record is unambiguous about what it is not: the claim flags mark gameplay success, biological perception, annotated identity tracking, independent test-set use, plasticity, and detector retraining all false. The report's limitations state that spikes are model output under configured assumptions, that the connectome is fixed and no plasticity is used, that lane and distance are image geometry, and that no action is selected anywhere in the chain. The replay is an engineering integration test of perception and simulation, and the paper treats it as such.

## 5.7 Summary

The perception stage can turn game footage into typed events, and the encoder can turn those events into current on a declared neuron population. The detector is externally trained and its reported accuracy is not a result of this project. The dataset has no independent test set, no player class, and no coin class; the official split leaks adjacent frames, and the curated split is group-held-out but still development data. The FAFB replay shows that stimulation produces spikes and that the network is dominated by non-stimulated activity, while the BANC mapping shows that seven features can be delivered to 232 annotation-selected neurons. Neither result establishes that the fly brain perceived the game, and the paper does not claim that it did.

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

# Chapter 7. Motor Decoding and Game Control

## 7.1 The motor interface

The motor stage exists because the FAFB graph cannot supply it. FAFB contains 110 neurons in a motor super-class, none of which are the leg motor neurons that would drive walking or jumping; the ventral nerve cord is outside the volume. BANC contains 805 neurons annotated as motor, including leg efferents, and the decoder is defined on the BANC graph. This is the one place where the project must switch datasets, and the switch is explicit: no FAFB root identifier appears in a BANC run, and no BANC neuron is selected by FAFB connectivity.

The 805 BANC motor neurons are divided by annotation into three decoded pools and one remainder. LEFT contains 185 neurons, RIGHT 186, and JUMP 20 (ten left and ten right tergotrochanter candidates). The remaining 414 motor neurons carry no LEFT, RIGHT, or JUMP label and are never decoded. There is no ROLL pool and no DUCK pool; the published annotation in this export does not define one, and the project reports them as unsupported rather than inventing a population.

Table 7 lists the pools.

**Table 7.** Decoder-defined motor populations on BANC v888. Pool membership is annotation-derived and is not a functional assignment; an unassigned motor neuron is not evidence that it does nothing. Data source: `configs/motor_decoder.yaml` and `motor/populations.py`; full machine-readable table in `tables/T06_motor_populations.csv`.

| Population | Size | Basis | Role |
|---|---:|---|---|
| LEFT | 185 | annotation: left leg effectors | decoded action |
| RIGHT | 186 | annotation: right leg effectors | decoded action |
| JUMP | 20 | annotation: tergotrochanter candidates (10 L / 10 R) | decoded action |
| unassigned | 414 | motor neurons without LEFT/RIGHT/JUMP label | never decoded |
| **Total** | **805** | annotation-defined motor neurons | |
| ROLL | 0 | unsupported | reported, not invented |
| DUCK | 0 | unsupported | reported, not invented |

The pool definitions are the weakest link in the motor chain. A neuron annotated as innervating a left leg is not thereby a "turn left" command; it may participate in many movements, and the annotation itself is a prediction. The decoder's LEFT, RIGHT, and JUMP labels are therefore labels on populations, not identified commands. This is stated in every Phase 4 and Phase 7 report and is repeated here because it bounds what a decoded action can mean.

## 7.2 The decoding rule

The decoder is a stateless, windowed threshold rule. It divides time into 50 ms half-open windows `[t, t+50)`. For each window it counts spikes in each pool and computes the active fraction — the number of pool neurons that spiked at least once divided by pool size. A pool is eligible for decoding when the window contains at least 5 spikes and at least 3 active neurons, and its active fraction reaches the activation threshold of 0.20. Among eligible pools, the decoder selects the one with the highest active fraction; exact ties are broken by the declared order LEFT, then RIGHT, then JUMP. If no pool is eligible, the action is NO_ACTION. The configuration also declares a release threshold of 0.10 for an optional hysteresis mode, but the characterised and executed decoder runs with smoothing and hysteresis disabled. Every window is therefore decided independently, and the post-drive window is always NO_ACTION.

Two properties follow. First, the decoder cannot invent an action: if no pool crosses threshold, the output is NO_ACTION. Second, the decoder cannot express a graded movement: it emits one of three categorical symbols. The categorical output is what the game consumes, and it is also the reason the decoder is easy to audit.

Figure 18 shows the pools and the decision rule.

![Figure 18. Motor populations and decoder rule. The upper panel shows the three decoded pools (LEFT 185, RIGHT 186, JUMP 20) and the 414 unassigned motor neurons, with ROLL and DUCK marked unsupported. The lower panel is a schematic of the 50 ms window rule: spike count and active fraction per pool, activation threshold 0.20, gate of at least five spikes and three active neurons, highest-fraction arbitration with LEFT/RIGHT/JUMP tie order, and NO_ACTION when no pool is eligible. Pool sizes are annotation counts, not functional assignments. Data source: configs/motor_decoder.yaml; reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md.](figures/F12_motor_decoder.png)

## 7.3 Characterising the rule on controlled drive

Before the decoder was connected to the connectome, Phase 4F characterised it on synthetic population drive. Eleven scenarios were defined: no drive; left; right; jump; left plus jump; right plus jump; bilateral; an ambiguous competition at half of each pool; a uniform drive at 0.3 of every pool; a weak left drive at 2% of the pool; and a weak jump drive at 5%. Each scenario was run at six current amplitudes from 120 to 220 pA, with and without a seeded ±25 pA per-neuron jitter, for 66 declared runs and 66 jitter runs. The drive was applied to neurons chosen by ascending node index, so the characterisation isolates the rule from graph structure.

The response matrix is clean at and above 180 pA. At 120 and 140 pA no driven neuron reaches the 150 pA rheobase, and every scenario returns NEUTRAL. At 160 pA the first window is still empty because the membrane needs time to charge, and the first non-neutral window appears at `[100,150)`; this is charging latency, not decoder delay. At 180, 200, and 220 pA every driven scenario returns its declared active set. The two weak scenarios remain NEUTRAL at every amplitude because their active fractions (0.02 and 0.05) are below the 0.20 activation threshold.

Two edge cases are instructive and are reported as arithmetic, not biology. The ambiguous competition requests half of each pool, but 185 is odd: `round(0.5 × 185) = 92` and `round(0.5 × 186) = 93`, giving active fractions 0.4973 and 0.5000. RIGHT therefore wins because its fraction is strictly higher, not because the decoder prefers RIGHT. The uniform scenario activates all three pools, and LEFT wins because 56/185 = 0.3027 is the highest fraction; the reason field records `simultaneous_actions`, flagging that this is arbitration. Every post-drive window is NEUTRAL in every run, confirming the stateless behaviour.

Jitter changes 24 of 66 primary sequences and leaves 42 of 66 fully identical. The changes are onset shifts and near-tie flips at fractions differing by a few percent; no run produces an action whose pool produced no spikes. This is the expected sensitivity of a threshold rule with categorical output, and it is a reason to treat single-window decoder outputs as noisy.

The synthetic characterisation shows that the decoder implements its declared rule. It does not show that the rule is a good motor decoder, and it says nothing about whether the connectome can drive the pools.

## 7.4 Driving the decoder from BANC structure

Phase 4G connected the decoder to the BANC graph and asked which structural routes can recruit the pools. Six conditions were run for 300 ms on the BANC t5 graph with signed edges, 300 pA stimulation from 50 to 250 ms, and the unchanged decoder. No motor neuron was stimulated. The candidates were 64-neuron groups chosen by structure, not by output: descending neurons ranked by direct motor synapses, VNC intrinsic neurons ranked by direct motor synapses, a random matched group, and a shuffled descending group.

The outcomes are shown in Figure 30 and summarised in Table 8.

![Figure 30. Phase 4G condition outcomes on the BANC graph, including the positive control. Bars show total, motor, and decoded-state counts for conditions A–F. Only condition C (VNC intrinsic candidate) recruited the decoder pools, producing 492 motor spikes across 82 motor neurons and four JUMP windows; condition B produced 18 motor spikes, all in unassigned motor neurons; A, D, E, and F produced no decoder-pool activity. This establishes that the decoder fires when motor tissue is driven directly; it does not establish a sensory-to-motor pathway. Data source: experiments/results/phase_4g/phase_4g_experiment.json (signal_overview).](figures/F24_phase4g_positive_control.png)

**Table 8.** Phase 4G condition outcomes on the BANC t5 graph. Six conditions of 300 ms with 300 pA stimulation of 64 selected neurons, each scored by the unchanged decoder over five 50 ms windows. "Active motor neurons" counts motor cells that spiked at least once. Data source: `experiments/results/phase_4g/phase_4g_experiment.json` (signal_overview).

| Condition | Input | Total spikes | Motor spikes | Active motor neurons | Decoded states |
|---|---|---:|---:|---:|---|
| A | none | 0 | 0 | 0 | NEUTRAL ×5 |
| B | 64 descending candidates | 781 | 18 | 3 | NEUTRAL ×5 |
| C | 64 VNC intrinsic candidates | 1,296 | 492 | 82 | JUMP ×4, NEUTRAL ×1 |
| D | 64 random matched | 704 | 0 | 0 | NEUTRAL ×5 |
| E | 64 shuffled descending | 728 | 0 | 0 | NEUTRAL ×5 |
| F | background/noise only | 0 | 0 | 0 | NEUTRAL ×5 |

Only condition C recruited the decoder. Its 492 motor spikes came from 71 neurons in LEFT (27), RIGHT (32), and JUMP (12) plus 11 unassigned motor neurons, and the decoder produced JUMP in four of five windows. Condition B, despite being selected for direct descending-to-motor synapses, produced 18 motor spikes all in unassigned neurons and no decoder action. Conditions D and E produced no motor spikes at all. The silent baseline conditions A and F show that the model has no spontaneous motor activity under this policy, even with 50 pA background and 50 pA noise.

The correct reading of condition C is narrow. It is a positive control for the decoder and for BANC propagation: when 64 VNC intrinsic neurons are driven strongly, current reaches motor tissue and the decoder fires. It is not a sensory pathway, because the 64 neurons were selected by their motor synapses, not by their response to game events. Chapter 14 shows that when the sensory mapping is used instead, the current dies before the motor pools.

The result also localises the problem. BANC has 17,745 direct descending-to-motor edges at t1, and the motor population is reachable from many directions. The failure in the sensory-to-motor direction is not a lack of anatomical routes; it is a failure to deliver enough current through the routes that the sensory mapping happens to engage. That distinction is developed in Chapter 14.

## 7.5 The sensory-to-motor round trip

Phase 4H.4 ran the actual sensory mapping on the BANC graph. It stimulated the 232 mapped neurons with the seven supported features across two 100-frame segments and compared the actual mapping against five controls: no events, temporal shuffle, feature-identity shuffle, random matched mapping, and constant matched charge. The stimulated population was 232 neurons, of which 171 fired on the full stream; total spikes were 3,562, all in stimulated neurons. No motor neuron fired in any condition. The first-hop targets received current, but the maximum first-hop current was below what the earlier synthetic studies delivered, and the second hop received none. Chapter 14 quantifies the funnel on the Pilot 1 run, where the same pattern appears with a peak somatic depolarisation of −56.926 mV against a −50 mV threshold.

Phase 4H.4 is therefore the bridge between the positive control and the pilots. It shows that the mapping can drive its own neurons, that those neurons can drive first-hop targets weakly, and that the signal does not reach motor populations. The paper treats this as an execution-level result about this mapping and this model, not as a statement about the fly.

## 7.6 The controlled game

The game environment is a standalone endless runner in the Subway Surfers [29] genre, built on the open `endless-surfer` code base. It has three lanes, a fixed timestep of 1/60 s, a player who runs automatically, and obstacles of type barrier, overhead, and train. Coins are collected by lane; collisions end the episode; survival contributes a small per-step reward. The reward is synthetic and defined by the game rules: +1.0 for a coin, −1.0 for a collision, +0.01 per surviving step. It is not a biological dopamine signal, and the paper never treats it as one.

The environment exposes actions LEFT, RIGHT, JUMP, ROLL, and NO_ACTION. The motor adapter passes LEFT, RIGHT, JUMP, and NO_ACTION through unchanged; ROLL is a supported game action but has no BANC population, so a decoded ROLL cannot arise. UNMAPPED and DUCK execute NO_ACTION with a recorded reason, and unknown or invalid outputs also execute NO_ACTION. The adapter records the requested state and the executed action separately, so no unsupported state can silently become a different action.

The observation adapter reports the nearest visible object of each kind, its lane, and a distance proxy normalised by a 25-unit horizon. It does not know future obstacle positions, and it cannot report player pose from the detector. In the game-integration demonstrations the observation came from the game state directly; in the perception replay it came from the detector. The two paths are separate and are not mixed in any single result.

Phase 7 ran fixed-seed demonstrations with four agent types: a random agent, a rule-based agent, a replay of recorded Phase 4 decoder outputs, and a live neural closed loop. Table 9 reports the outcomes.

**Table 9.** Phase 7 controlled-game demonstration runs. All runs are headless, fixed-seed, recorded, and replayable with the game's own replay function. The neural closed loop used the BANC graph with fixed weights and no plasticity. Data source: `experiments/results/phase_7/game_integration_demo.json` and `experiments/results/phase_7/neural_closed_loop.json`; full machine-readable table in `tables/T09_phase7_demonstration.csv`.

| Agent | Seed | Steps | End | Score | Coins | Collisions | Reward |
|---|---:|---:|---|---:|---:|---:|---:|
| random | 42 | 213 | collision | 5.55 | 2 | 1 | 3.12 |
| random | 7 | 332 | collision | 7.53 | 2 | 1 | 4.31 |
| random | 123 | 218 | collision | 4.63 | 1 | 1 | 2.17 |
| rule-based | 42 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| rule-based | 7 | 531 | collision | 16.85 | 8 | 1 | 12.30 |
| rule-based | 123 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| Phase 4 replay | 42 | 300 | time limit | 8.00 | 3 | 0 | 6.00 |
| Phase 4 replay | 7 | 300 | time limit | 5.00 | 0 | 0 | 3.00 |
| neural loop | 42 | 213 | collision | 5.55 | 2 | 1 | 3.12 |

The rule-based agent is the strongest, reaching 432–531 steps and 14.20–16.85 score. The random agent reaches 213–332 steps. The Phase 4 replay is open loop and is truncated at 300 steps; its recorded action stream is 200 JUMP and 100 NO_ACTION, with ROLL requests mapped to NO_ACTION because no ROLL pool exists.

The neural closed loop is the critical row. It advanced 213 game updates, which required 7,100 neural steps over 3,550 ms of game time. It recorded 2,852 spikes, all in stimulated neurons, 71 active neurons out of 232 stimulated, 10,215 transmitted spikes, and zero motor spikes. Every one of the 213 decoder states was NO_ACTION. The weights were unchanged from start to end (identical SHA-256), the run repeated deterministically, and the checks `decoder_received_motor_activity` and `decoded_action_supported` were both false while the execution checks were true. The episode ended by collision with reward 3.12, decomposed into 2.0 coin, −1.0 collision, and 2.12 survival.

The neural row coincides numerically with the random-baseline row at seed 42. The source records do not explain the equality, and this paper does not interpret it; it is noted as a documentation issue rather than used as evidence. What the row establishes on its own is simpler and more important: the closed loop executed, the game advanced, and the decoder received no motor activity, so every action was NO_ACTION. A pipeline that always outputs NO_ACTION cannot play the game, regardless of how its score compares to a baseline.

## 7.7 What the motor stage established

Three conclusions follow from this chapter.

First, the decoder works as specified. On synthetic drive it returns the declared action sets at and above 180 pA, remains neutral below rheobase, and behaves statelessly across windows. On BANC structure it fires when motor tissue is driven strongly through VNC intrinsic neurons. The rule is not the bottleneck.

Second, the structural route from the sensory mapping to the motor pools does not deliver enough current. Phase 4H.4 drove 232 neurons, produced 3,562 spikes, and recruited no motor neuron. Phase 7 repeated the result in closed loop with 2,852 spikes and no motor activity. The failure is at the sensory-to-motor stage, not at the decoder.

Third, a decoded action is not a motor command. LEFT, RIGHT, and JUMP are labels on annotation-defined populations, the game consumes categorical symbols, and no limb model exists. Even if a pool had fired, the paper could claim a decoded action, not a movement. The next chapter turns to the learning mechanisms that were supposed to bridge this gap, and shows that they did not.

## 7.8 Summary

The motor interface is an annotation-defined, three-pool decoder on the BANC graph. It is characterised, positive-controlled, and connected to a controlled game. It fires when driven directly and is silent when driven through the sensory mapping or in closed loop. The game demonstrations show a functioning environment and a functioning adapter chain, with a neural agent that always chose NO_ACTION. The chapter's result is a localisation: the decoder is not the failure point; the sensory-to-motor current is.

# Chapter 8. Reward, Plasticity and Information Theory

## 8.1 The learning problem as stated

Chapters 5–7 describe a forward chain: game events become sensory currents, sensory currents evoke spikes, and spikes are decoded into categorical actions. Nothing in that chain changes with experience. A fixed structural network can only express the transformations its weights already encode, and the weights are a power-law transform of synapse counts. If the project was to test whether a connectome-derived network can *learn* to turn visual information into actions, it needed a mechanism that alters synaptic efficacy as a function of outcome.

The project chose a three-factor rule rather than backpropagation or a trained policy network. The choice follows from the data: a biologically motivated, local update can be applied to the sparse connectome without a dense backward pass, and it keeps the fixed-weight simulator available as an oracle. The rule has three declared factors — a reward prediction error, a short-lived eligibility trace, and a learning rate with bounds. Each factor is a computational construct. None is a measurement of dopamine, octopamine, serotonin, a biological synaptic tag, or a biological learning law, and every Phase 5 report says so explicitly.

This chapter describes the reward signal, the trace, the update rule, and the controlled task on which the rule was evaluated. It then reports the Phase 5F comparison, where plastic weights improved reward-conditioned success on that task, and closes with the information-theoretic machinery that Phase 6 later used to ask whether the improvement carried more information about the cue. The chapter's central caution is stated once here and repeated where it matters: a successful conditioned response on a synthetic task is not competitive action selection, and it is not learning in a fly.

## 8.2 The reward signal

Two reward definitions exist in the project and they must not be conflated. The controlled task of Phase 5 uses task rewards: +1.0 for a correct response, 0.0 for a miss, and no negative outcome in the primary protocol. The game of Phase 7 and Phase 8 uses game rewards: +1.0 for a coin, −1.0 for a collision, and +0.01 per surviving step. Both are dimensionless task scalars. Neither is a biological reward, and the project never treats a reward value as a dopamine measurement.

Phase 5B implemented a reward scheduler with four fixed schedules: a single positive event at 100 ms, a single negative event at 100 ms, a zero-reward event, and a mixed schedule with +1.0 at 80 ms, −1.0 at 160 ms, and +0.5 at 240 ms. A delayed variant delivers the same mixed magnitudes 50 ms later. Delivery time, sign, and one-event-per-outcome were checked and passed. The scheduler is a software component, and those checks are software checks.

The third factor is not the reward itself but a prediction error from a declared value model:

δ_t = r_t + γ V(s_{t+1}) − V(s_t),  (8.1)

with a default discount γ = 0.9, a value learning rate of 0.2, an initial value of 0.0, and a value bound of ±100. The Phase 5B convergence test ran 400 deterministic episodes over the mixed schedule and compared learned stage values with the analytic discounted sum at a tolerance of 0.001; it passed. The discount grid {0.0, 0.5, 0.9, 0.99} was probed, with γ = 0 the myopic case. Equation (8.1) is a model equation. No neural signal was recorded that could be compared with δ_t.

## 8.3 Eligibility traces

The second factor is a per-edge tag that records recent pre-before-post coincidence. Phase 5C implemented it as

e_ij(t) = λ e_ij(t−1) + f(pre_i, post_j),  (8.2)

with λ = exp(−dt/τ_e), a declared τ_e of 20 ms, and dt = 0.5 ms, so the per-step decay is exp(−0.025) = 0.97531. The trace is float32 and is pruned when its absolute value falls below 1.0 × 10⁻⁴, checked every 50 steps. Coincidence is delay-matched: a presynaptic spike is paired with postsynaptic spikes at the step where the uniformly delayed packet is delivered, not at the emission step. With the declared 1 ms delay at 0.5 ms resolution, that is two steps. There is no coincidence window; a tag exists only for exact delivery-step coincidence.

The storage design is sparse. Traces live on compact plastic-slot arrays, and the slot-to-edge mapping is materialised only when the rule learns. At the BANC t5 verified-sign edge count of 683,100, the compact capacity is 5,464,800 bytes (5.21 MiB), against 12,285,680 bytes (11.72 MiB) for all 1,535,710 edges. No dense pair matrix is allocated.

The Phase 5C benchmark also produced a negative engineering result that is preserved rather than hidden. The lazy sparse store was slower than a vectorised dense multiply at every measured size and activity level, with speed ratios from 0.22× at 1,000 edges to 0.45× at 1,535,710 edges, because the dense baseline performs one NumPy pass while the sparse path pays per-step Python and validation overhead. The sparse design nevertheless performs 100–1,000 times fewer per-edge decay operations and scales with active edges rather than total edges. At BANC scale, 0.1% activity, and a 600-step benchmark, the trace step costs 0.37 ms; a separate Phase 4G smoke step was measured at 3.7 ms. The two measurements come from different runs, so the roughly 10% ratio is an order-of-magnitude comparison, not a profiled decomposition. The trace layer is a storage and scaling success and a wall-clock regression; both statements are true and both are reported.

## 8.4 The three-factor rule and its constraints

Phase 5D coupled the two factors into a bounded update:

Δw_ij = η δ_t e_ij.  (8.3)

The implemented constraints are as important as the equation. Weight state is split into five layers with declared write permissions: an integer structural synapse count (read-only), initial excitatory and inhibitory weights (read-only), learned deltas (writable), effective weights (writable), and a sign class (read-only). Only edges with a verified sign are plastic. On BANC t5 that is 683,100 of 1,535,710 edges, or 44.48%; an update on an unknown-sign edge raises rather than silently guessing a sign. Updates are split by sign channel, so an excitatory update touches only the excitatory delta and effective weight. Effective weights are bounded to 0.5×–2.0× the initial weight, and the raw increment is clipped at 5 pA before the bound clamp; both events are counted separately. Weight decay is disabled (0.0 per ms), normalization is a declared exclusion, and a detected sign flip aborts when the abort flag is set. The update cadence is reward-event driven, not every step.

The load-bearing software contract is the η = 0 identity. At η = 0 the rule returns an all-zero update report before decay and before any array write, and the plastic pathway must reproduce the fixed-weight simulator's spike hashes exactly. That equality was verified synthetically and on the BANC t5 graph, and it is what licenses the plastic simulator as a strict extension of the fixed oracle rather than a replacement. Phase 5D's BANC trace capacity was 5.21 MiB with a peak process working set of 286.31 MB. The Phase 5 validation ran 186 focused plasticity tests and 683 tests in the full suite, all passing.

Figure 38 illustrates the arithmetic of the rule. It is computed from the declared equations with an illustrative rectangular modulation and η = 0.5; it is not a recorded weight change from any experiment.

![Figure 38. Three-factor plasticity rule. The eligibility trace decays with τ_e = 20 ms after a presynaptic event at 60 ms; the modulation M(t) is a rectangular illustrative signal, not a measured reward or dopamine trace; the resulting absolute weight increment is computed with η = 0.5 and is clipped in the implementation at 5 pA with effective-weight bounds of 0.5×–2.0× the initial value. The panel demonstrates the declared arithmetic only. Data source: configs/plasticity*.yaml and reports/PHASE_5D_THREE_FACTOR_PLASTICITY.md.](figures/F32_three_factor.png)

The rule is not fitted. η, τ_e, the bounds, and the clip are declared modelling choices fixed before the learning experiments. Later robustness runs vary them, but no value was selected by looking at an outcome that this paper reports.

## 8.5 The controlled task on which the rule was tested

Phase 5E built a synthetic cued-response task with 36 nodes. Four cue populations of eight neurons project to four single-neuron action populations. Complete wiring gives 4 × 8 × 4 = 128 directed cue-to-action edges; a Bernoulli(0.5) control gives 67 edges. Each episode lasts 24 ms at dt = 0.5 ms. A cue receives a 600 pA pulse for 6 ms with onset jittered between 1 and 7 ms; action neurons carry a 145 pA background; the response deadline is 13.5 ms; noise is 8 pA; the task's excitatory decay is 20 ms. Success is defined as the designated action population spiking at or before the deadline. The cue-to-action assignment is arbitrary and was declared before the run.

Seven conditions were run: A, fixed weights with outcome reward; B, plastic weights with outcome reward; C, plastic with zero reward; D, plastic with shuffled reward; E, plastic with random connectivity; F, plastic with traces disabled; G, a conventional supervised perceptron. Each condition used 160 training episodes and 40 held-out episodes at five checkpoints, with three replicates. Evaluation used η = 0 on the current learned state, traces disabled, and the same held-out episodes at every checkpoint. Training and evaluation seeds came from separate streams and were verified disjoint. The perceptron receives the correct action label. It is information-privileged and is not a matched control; it bounds what a supervised method can achieve on the task, nothing more.

Condition B moved held-out success from 0.792 at checkpoint 0 to 0.942 at checkpoint 160, while the fixed control A stayed at 0.792. B exceeded A in 3 of 3 replicates. The zero-reward condition C and the traces-disabled condition F never moved from 0.792 and changed no weight. The shuffled-reward condition D ended at 0.792 after a transient rise to 0.817, so it did not improve. The random-connectivity condition E started at 0.158 and stayed there; because it also has fewer edges and less total cue input (67 versus 128), its impairment cannot be attributed to topology alone. The perceptron G moved from 0.250 to 1.000.

Two negative results matter more than the headline improvement. First, the selective metric — whether the first action population to spike is the designated one — reached only 0.192 for condition B, below the 0.250 chance rate for four actions. The network increased the designated population's response without selecting it over alternatives. Second, the predeclared training criterion (0.75 success over a 20-episode window) was reached by the fixed-weight control A in 3 of 3 replicates without any weight change, so the criterion alone does not discriminate learning. The held-out comparison is the evidence; the criterion is not.

The Phase 5E result is therefore a conditioned-response result: a designated population spikes more reliably after reward-modulated training, on a task with one rewarded response and no requirement to choose among competing actions. It is not a demonstration of competitive action selection.

## 8.6 The Phase 5F comparative evaluation

Phase 5F repeated the comparison with ten independent seeds, 160 training episodes, 40 held-out episodes, and η = 1.0, and added paired contrasts with an exact two-sided sign-flip test over 1,024 assignments and Holm correction across four declared contrasts. Table 10 reports the core conditions.

**Table 10.** Phase 5F core conditions on the synthetic 36-node cued-response task. Success is the designated action population spiking before the deadline on held-out episodes; selective is the first-spiking population matching the designated one (four-action chance 0.25); changed edges is a mean over ten seeds. The perceptron is privileged and is not a matched control. Data source: `experiments/results/phase_5f/comparison_analysis.json`; full machine-readable table in `tables/T21_phase5f_core.csv`.

| Condition | Wiring | η | Seeds | Final success (sd) | 95% CI | Start | Selective | Changed edges |
|---|---|---:|---:|---|---:|---:|---:|---:|
| fixed complete | complete | 0.0 | 10 | 0.795 (0.084) | 0.743–0.843 | 0.795 | 0.120 | 0.0 |
| plastic complete | complete | 1.0 | 10 | 0.945 (0.023) | 0.930–0.958 | 0.795 | 0.200 | 96.7 |
| fixed random | Bernoulli(0.5) | 0.0 | 10 | 0.102 (0.043) | 0.078–0.128 | 0.102 | 0.218 | 0.0 |
| plastic random | Bernoulli(0.5) | 1.0 | 10 | 0.113 (0.052) | 0.085–0.145 | 0.102 | 0.220 | 2.4 |
| perceptron | dense | n/a | 10 | 1.000 (0.000) | 1.000–1.000 | 0.250 | 1.000 | 6 weights |

Figure 21 shows the same success rates. The plastic advantage over fixed weights is visible only on complete wiring.

![Figure 21. Phase 5F final success rates on the synthetic task (mean ± sd over ten seeds). Complete wiring reaches 0.795 fixed and 0.945 plastic; random wiring reaches 0.102 and 0.113. The selective accuracy of the plastic complete condition is 0.200 against a four-action chance rate of 0.250, so the success increase is not competitive action selection. The conventional perceptron, which receives the correct label, reaches 1.000 and is shown for context only. Data source: experiments/results/phase_5f/comparison_analysis.json (core.conditions).](figures/F15_phase5f_success.png)

The paired contrasts are:

- plastic complete − fixed complete: +0.150, 95% bootstrap CI [0.110, 0.198], Cohen's d_z = 2.012, 10/10 seeds positive, exact p = 0.00195, Holm p = 0.00781, rejected.
- plastic random − fixed random: +0.010, CI [0.000, 0.020], d_z = 0.572, 3/10 positive and 7 exact zeros, exact p = 0.250, Holm p = 0.250, not rejected.
- plastic complete − plastic random: +0.833, CI [0.800, 0.863], d_z = 15.776, 10/10 positive, exact p = 0.00195, Holm p = 0.00781, rejected.
- fixed complete − fixed random: +0.693, CI [0.647, 0.735], d_z = 9.285, 10/10 positive, exact p = 0.00195, Holm p = 0.00781, rejected.

The second contrast is the one that limits the learning claim. Plasticity on random wiring did not improve success; the 0.010 point estimate rests on three nonzero pairs. The largest contrast, fixed complete versus fixed random, is structural rather than learned: complete cue-to-action wiring is far better than sparse random wiring before any weight changes. The learning effect is the additional +0.150 that plasticity contributes on top of an already favourable structure.

The robustness sweep is descriptive and was not corrected for multiple comparisons. Two axes failed to discriminate: η from 0.1 to 2.0 produced identical final success (0.948), and τ_e from 10 to 40 ms also produced identical success, consistent with saturation at the declared weight bounds. Reward magnitude did matter (0.25 → 0.854, 1.0 → 0.948, 4.0 → 1.000), initial weights mattered (0.740 to 0.969 across three seeds), network size barely mattered (0.938 to 0.958 for 2, 4, and 8 cues), a higher structural threshold helped (t3 → 0.990), and a 10 ms reward delay reduced success to 0.906. One plastic-random seed produced no weight change at all; it is retained in the analysis and reported as a negative result rather than dropped.

Two scoping cautions apply. Phase 5F used η = 1.0; the Phase 8 protocol later declared η = 0.5. The two settings belong to different designs and are never pooled. And every Phase 5 number is a model output on a synthetic graph; no BANC edge was read, modified, or simulated.

## 8.7 What the rule did and did not establish

The Phase 5 programme established four things. The three-factor rule is implemented as declared, with sign preservation, structural immutability, bounded effective weights, and an exact η = 0 identity against the fixed simulator. On a synthetic task with one rewarded response, reward-modulated plasticity improves held-out success relative to fixed weights, and the improvement depends on the reward signal: zero reward, shuffled reward, and disabled traces do not improve. The improvement requires complete cue-to-action structure; random wiring shows no supported gain. And the effect is robust in direction across the declared descriptive axes, though two axes saturate and do not discriminate.

It did not establish competitive action selection. The selective rate stayed near or below the four-action chance level in every condition, which means the trained network increased a designated response without choosing it over the alternatives. It did not establish an information gain: Chapter 10 reports that the paired cue-to-action mutual-information contrast between plastic and fixed complete wiring is negative and not rejected. And it did not establish anything about the connectome or about biological plasticity. The task graph has 36 nodes, the reward is an external scalar, and the weight change is the output of a declared equation.

These limits are not incidental. They define what the later Phase 8 experiments could possibly show, and they explain why the paper treats a high conditioned-response success rate as insufficient evidence of learning to play a game.

## 8.8 Information theory: what would count as evidence

To ask whether a manipulation carries more information about a variable, the project used discrete information theory on archived artifacts. For discrete variables X and Y with empirical distribution p,

H(X) = −Σ_x p(x) log₂ p(x),  (8.4)

I(X;Y) = Σ_{x,y} p(x,y) log₂ [p(x,y) / (p(x)p(y))].  (8.5)

Estimates are plug-in values in bits. The plug-in estimator is biased upward, so the analysis reports the first-order bias floor (k_x − 1)(k_y − 1) / (2N ln 2) rather than correcting it away; for the Phase 5F tables the floor is 0.1623 bits per seed. Because both arms of a paired contrast have the same episode count, the floor is common and cancels in the difference. Guard rails were declared before any endpoint was computed: at least 100 observations for a reported estimate, at least 5 expected observations per cell, a marginal entropy floor of 0.05 bits below which normalized MI is withheld, and at least 50 observations per conditioning stratum.

Inference is cluster-preserving in the sense of cluster-based permutation testing [11]. Confirmatory endpoints use 5,000 block permutations and 2,000 bootstrap resamples; exploratory endpoints use 2,000 permutations. When the design has ten paired seeds, the confirmatory test is the exact two-sided sign-flip over 2¹⁰ = 1,024 assignments, with Holm correction inside the declared family. The observational unit is the seed. Episodes and timesteps are never treated as independent samples.

Three endpoints were declared unavailable rather than approximated. Spike-train entropy was not estimable because the only archived recording with individual spike times is a single replay run of 74 spikes. Population-response entropy for the 138-neuron sensory population was not estimable at any available sample size because the nominal support is 2¹³⁸ with no repeat structure. Membrane-potential entropy was unavailable because membrane potentials were never recorded. One endpoint, the decoder-mediated neural-to-motor MI, is circular by construction — the decoder maps pool activity to a state by definition — and is reported only as an internal-consistency check.

The confirmatory family was two paired contrasts on the Phase 5F artifacts: plastic minus fixed on complete wiring, and plastic minus fixed on random wiring. Chapter 10 reports the outcome. The design question here is what such a test could mean. A positive contrast would say that plasticity increased the statistical dependence between cue and chosen action on held-out episodes. A null contrast would say that any success improvement was not accompanied by more cue information, which is exactly the dissociation the project later had to report.

## 8.9 Summary

The learning machinery is a declared three-factor rule with a task reward, a delay-matched eligibility trace, a bounded update, and an exact zero-learning-rate identity against the fixed simulator. On a synthetic 36-node conditioned-response task it produces a reward-dependent improvement in designated-response success, and on random wiring it does not. It does not produce competitive action selection, and the information analysis in Chapter 10 finds no supported increase in cue-to-action mutual information. Nothing in this chapter is evidence of biological synaptic plasticity, dopamine function, or learning in a fly. The next chapter places these experiments in the project's chronological record and identifies the deviations and documentation issues that the record preserves.

# Chapter 9. Project Development and Experimental Chronology

## 9.1 Why the chronology is part of the evidence

The FLY-SURFER record is a sequence of gated phases, each with its own protocol, implementation, validation, and report. The sequence matters for two reasons. First, later phases were designed in response to earlier failures: the dataset switch to BANC, the motor decoder, the sensory-to-motor round trip, and the Phase 8 protocol all exist because an earlier attempt did not work. Second, the record preserves several deviations and one freeze-readiness failure that cannot be understood from a results table alone. This chapter reconstructs the sequence from the stored reports and execution records. It adds no experiment and changes no conclusion.

The chronology is also the place to state what was *not* done. The Phase 8 confirmatory campaign with N = 16 seed pairs was never executed. The paper reports a design, two pilots, and six trained artifacts, not a completed campaign. No commercial Subway Surfers process was controlled at any point; the game is a standalone open-source endless runner. No fly was recorded, stimulated, or observed.

## 9.2 Phase map

Table 11 is the phase-by-phase backbone, reproduced from the project's validation summary. It lists the objective, implementation, validation, status, key result, and test count for every phase that appears in this paper.

**Table 11.** Phase-by-phase implementation and validation summary. Statuses are the values recorded in the phase reports; "PASS WITH LIMITATIONS" is a recorded status, not an editorial softening. Test counts are cumulative full-suite counts at the time of the phase and are not independent samples. Data source: `reports/` phase reports and execution records; full machine-readable table in `tables/T07_phase_validation_summary.csv`.

| Phase | Objective | Implementation | Validation | Status | Key result | Tests |
|---|---|---|---|---|---|---|
| 0 | Audit the raw FAFB export | dataset audit | 11/11 audit, 8/8 round-trip | PASS | artifact trusted as read-only | — |
| 1 | Build the connectome artifact | `connectome.npz` | 139,255 nodes; 3,732,460 edges; 50,666,648 synapses | PASS | exact counts reproduced | — |
| 2 | LIF simulation over 800 neurons | LIF, sparse CSR synapses, recorder | 1,564 spikes; 79/800 active | PASS | recruitment inside the sample | 68 |
| 2.5 | Scalability to the full graph | benchmark suite | 800–139,255 neurons; stability checks pass | PASS WITH LIMITATIONS | 349,846 spikes at full size | — |
| 3A | Map game features to sensory populations | 14 features, 138 neurons | scripted scene protocols | PASS WITH LIMITATIONS | driven neurons spike; mapping is a convention | — |
| 3A.5 | Calibrate the sensory operating point | amplitude/sigma/population sweep | 200 pA, σ 0.20, 4 neurons; 2/6/7 spikes | PASS WITH LIMITATIONS | small threshold-sensitive code | — |
| 3B.1 | Curate the detector dataset | sequence-grouped split | 2,328 images; 8,666 boxes; 14 classes | PASS WITH LIMITATIONS | no independent test split | 6 |
| 3B.2A | Perception inference architecture | perception package + mock detector | screenshot → GameState contract | PASS | no accuracy claim | 38 |
| 3B.2B.3 | Integrate YOLO11n ONNX | ONNX runtime decoder | one image + five-image smoke slice | PASS WITH LIMITATIONS | 2/13 detections rejected by bounds | 13 new |
| 3B.2C | Replay 100 real frames | end-to-end replay | 15,654,631 spikes; 99.976% non-stimulated | PASS WITH LIMITATIONS | not a gameplay result | 12 checks |
| 3C | Temporal features and scheduler | tracker, lifecycle, scheduler | 50 synthetic sequences; 175/0/0 events | PASS (synthetic) | direction 0.996; continuity 0.944 | — |
| 4A | Check dataset compatibility | read-only audit | 139,241 shared IDs; 14 FAFB-only; 7 annotation-only | PARTIALLY COMPATIBLE | FAFB is brain-only | — |
| 4B | Investigate locomotor pathways | read-only pathway analysis | BANC motor/descending inventory | COMPLETE | no local VNC motor neurons in FAFB | — |
| 4C.5 | Audit BANC integrity | ID/edge/annotation audit | 172,433 endpoints | PASS WITH LIMITATIONS | read-ready with limits | — |
| 4D | Construct BANC graphs | `banc_graph.py` | t1/t5/t10; t5 1,535,710 edges | PASS WITH LIMITATIONS | 5 source hashes match | 20 focused / 331 total |
| 4E | Analyse motor populations | Phase 4E analysis | 805 motor; 1,316 descending; 1,849 ascending | PASS WITH LIMITATIONS | 17,745 direct DN→MN edges at t1 | 14 focused / 345 total |
| 4F | Build a fixed motor decoder | populations + `motor_decoder` | 11 scenarios × 6 amplitudes = 66 runs | PASS WITH LIMITATIONS | correct sets from 180 pA | 52 focused / 397 total |
| 4G | Propagate spikes and decode | BANC simulator + adapter | condition C: 1,296 spikes, 492 motor, JUMP ×4 | PASS WITH LIMITATIONS | positive control works; descending route does not | 140 focused / 440 total |
| 4H.4 | Sensory-to-motor round trip | archived event pulses → BANC | 3,562 spikes, all stimulated; 0 motor | PASS WITH LIMITATIONS | first hop does not spike | 47/47 config checks |
| 5 | Reward, eligibility, three-factor plasticity | plastic simulator; synthetic task | 10 seeds; plastic 0.945 vs fixed 0.795 | PASS (software); INCONCLUSIVE (biology) | conditioned response, not action selection | 186 focused / 683 total |
| 6 | Information-theoretic evaluation | entropy and MI estimators | plastic − fixed cue→action MI = −0.0863 bits; p = 0.125 | NOT SUPPORTED | no information gain from plasticity | 65 focused / 748 total |
| 7 | Closed-loop game integration | environment adapters + live loop | seed 42: 213 updates, 2,852 spikes, 0 motor | INTEGRATION PASS | NO_ACTION ×213; reward 3.12 | 19 focused; 1,012 passed / 6 pre-existing failures |
| 8 Pilot 1 | A-condition viability grid | production episode runner | 9 episodes; 73,880 spikes; 0 motor | EXECUTED; NOT FREEZE-READY | viability only; baseline drift | — |
| 8 D5/D6 | Train F and F-beta readouts | training engine + checkpointing | 6 artifacts; 120/120 episodes | CERTIFIED | behaviourally null training | 71 focused / 530 total |
| 8 Pilot 2-C | Floor and identity certification | Pilot 2-C runner | 54/54 rows; A′ exact ×9; all arms motor-null | EXECUTED AND CERTIFIED | C1–C4 and H1–H3 unevaluable | 531 total |

## 9.3 The first arc: connectome and simulator (Phases 0–2.5)

Phase 0 audited the raw FAFB export and its round-trip integrity. Phase 1 built the read-only connectome artifact used by every FAFB run: 139,255 neurons, 3,732,460 directed pairs after the ≥5 summed-synapse threshold, and 50,666,648 synapses. The artifact hash is `3f568f24…5f33d8`, and the arrays are described in Chapter 3. Phase 1's claim is narrow — exact counts were reproduced from the source export — and it does not claim that the thresholded graph is a physiological wiring diagram.

Phase 2 implemented the LIF neuron, sparse current-based synapses, a recorder, a simulator, and configuration validation, and ran an 800-neuron subset. It produced 1,564 spikes with 79 of 800 neurons active and passed 68 tests. Phase 2.5 scaled the same engine from 800 to the full 139,255 neurons. The full graph ran at 138.3 steps/s, retained 134.7 MB of simulation arrays, produced 349,846 spikes with 33,261 active neurons, and passed its stability checks. The phase also recorded the nonlinear scaling and the very high non-stimulated spike share at large subgraphs; Chapter 6 reports those measurements without attributing a mechanism.

The chronology of these two phases matters because they set the simulator's scope. The model was always a current-based LIF network over a structural graph, never a conductance-based or physiologically calibrated model. Later phases inherited that scope.

## 9.4 Perception and dataset work (Phases 3A–3C)

Phase 3A mapped 14 game features to 138 FAFB neurons and showed that scripted feature drive evokes spikes. Phase 3A.5 swept amplitude, input noise, and population size to pick a workable operating point: 200 pA, σ = 0.20, four neurons, producing spike counts of 2, 6, and 7 at three distances across three seeds. The counts were ordered at every seed, with a reported d′ of 2.357, but the amplitude and tuning searches fell back to declared defaults. The calibration therefore established a small, threshold-sensitive code, not an optimised encoder.

The perception side began with Phase 3B.1, which curated a 2,328-image detector dataset with 8,666 boxes and 14 classes, and produced a group-aware split. Phase 3B.2A defined the screenshot-to-`GameState` contract with a mock detector and made no accuracy claim. Phase 3B.2B.3 integrated a trained YOLO11n ONNX model and ran a one-image plus five-image smoke slice; two of 13 detections were rejected by bounds. Phase 3B.2C then replayed 100 real frames through perception, tracking, the sensory mapping, and the full FAFB graph. The replay produced 15,654,631 spikes, 99.976% of them from non-stimulated neurons, and ended at the sensory-injection stage with no action selection. Chapter 5 explains why that share is expected and why it is not evidence of network computation.

Phase 3C built and calibrated the tracker, the object lifecycle, and the temporal activation scheduler on 50 synthetic sequences, with 175 true positives, zero false positives, and zero false negatives. Those numbers are an implementation calibration on synthetic sequences. They are not detector performance on real video, and the paper labels them accordingly.

A parallel Phase 3 follow-up programme produced a frozen lane-encoding preregistration (P3-3C.5), a 42-instance pilot, and a recorded finding that one acceptance criterion in the earlier protocol revision was unsatisfiable. That work is documented in the repository. It is not part of the causal chain reported here, and this paper neither relies on it nor reinterprets it.

## 9.5 The dataset switch (Phases 4A–4H)

Phase 4A audited compatibility between FAFB and BANC. The decisive finding was that FAFB is a brain-only volume: it contains 110 motor-super-class neurons, none of them the limb motor neurons required for a walking or jumping readout, because the ventral nerve cord is absent. BANC contains 805 motor neurons, including leg effectors. Phase 4B confirmed the absence of local VNC motor neurons in FAFB and mapped the descending and ascending populations. Phase 4C.5 audited BANC identifiers, edges, and annotations and found the resource read-ready with limitations: 172,433 endpoint nodes after excluding metadata-only rows and self-edges.

Phase 4D constructed the BANC graph at three thresholds. At t5 the graph has 1,535,710 edges and 18,552,546 synapses; 683,100 edges (44.48%) carry a verified sign. Phase 4E analysed motor populations and pathways and found 805 motor neurons, 1,316 descending, and 1,849 ascending neurons, with 17,745 direct descending-to-motor edges at t1. Phase 4F built the three-pool decoder and characterised it on 11 scenarios at six amplitudes, with and without jitter. Phase 4G connected the decoder to the BANC graph and produced the positive control: driving 64 VNC intrinsic neurons recruited motor tissue and produced four JUMP windows, while descending candidates, random groups, and shuffled groups did not.

Phase 4H.4 then ran the actual seven-feature sensory mapping on BANC. It stimulated 232 neurons, obtained 3,562 spikes all in stimulated neurons, and recorded zero motor spikes. The first hop received weak current and the second hop received none. This is the pivot of the project: the decoder works when driven directly, but the sensory mapping does not deliver enough current to the motor pools. Chapters 7 and 14 treat the positive control and the null round trip as separate results and never merge them.

## 9.6 Plasticity and information (Phases 5 and 6)

Phase 5 built the reward scheduler, the eligibility traces, the three-factor rule, the synthetic cued-response task, and the comparative evaluation. Chapter 8 reports the results. The chronology point is that the entire Phase 5 programme ran on synthetic graphs of tens of nodes; no BANC edge was read, modified, or simulated. The 0.945 versus 0.795 success comparison is a result about the rule and the task, not about the connectome.

Phase 6 then analysed archived Phase 3, 4, 5 artifacts for entropy and mutual information. The only confirmatory family was two paired plastic-versus-fixed contrasts. Both were null: the complete-wiring contrast was −0.0863 bits (p = 0.125, Holm 0.25), and the random-wiring contrast was −0.0025 bits with nine exact zeros (p = 1.0). The analysis also declared three endpoints unavailable rather than approximating them. Chapter 10 reports the full result, including the dissociation between the Phase 5 success increase and the absence of an information increase.

## 9.7 Closed loop (Phase 7)

Phase 7 integrated the standalone game with the Phase 3 observation schema, the Phase 4 motor adapter, and the Phase 5 reward interface. It ran fixed-seed demonstrations with a random agent, a rule-based agent, a recorded Phase 4 replay, and a live neural loop. The live loop advanced 213 game updates over 7,100 neural steps, recorded 2,852 spikes all in stimulated neurons, and produced zero motor spikes. All 213 decoded states were NO_ACTION. The weights were unchanged by SHA-256.

The Phase 7 report also records a pre-existing repository condition: the full suite had six failures on README hash pins. Those failures are disclosed in the deviations register and are unrelated to the game integration. The paper uses them as a fact about the repository state, not as a result.

## 9.8 Phase 8 design and authorization (REV3 → REV4 → D1–D6)

Phase 8 was designed as a confirmatory campaign with controls, a pre-registered contrast family, and a fixed analysis plan. The protocol went through REV3 and a REV4 revision that resolved seven residual ambiguities without changing any hypothesis, contrast, outcome, seed count, α, SEI, K, cap, or coefficient. REV4's hash is `e4aa9e0f…1547c`; a later amendment, `832ef485…667ad`, defines Pilot 2-C.

The campaign design declares six conditions A–F, three controls A′, C′, Fβ, an F-init refinement, and a floor condition; four contrasts C1–C4; three hypotheses H1–H3 with Holm correction over m = 4; a primary outcome of min(updates, 900); N = 16 seed pairs (N = 10 if the pilot variance is low enough); K = 10 episodes; a master seed of 20261116; and an exact sign-flip test whose minimum attainable p is 2/65,536 at N = 16 and 2/1,024 at N = 10. Chapter 12 describes the design.

Execution was gated by six owner decisions, D1 through D6, each recorded with an approval identifier and date. D1 and D2 authorized specific stages; D3 amended Pilot 2-C; D4 bound the training contracts; D5 and D6 authorized the six training artifacts and the Pilot 2-C grid. The gates were not bypassed: when the Pilot 2-C preflight refused because the global training gate was unsatisfied, the refusal was recorded and resolved through a recorded decision rather than by weakening the gate.

## 9.9 The execution arc (2026-11-20 to 2026-11-23)

Pilot 1 executed nine episodes on 20 November 2026. It produced 3,784 updates, 126,135 neural steps, and 73,880 spikes, with zero motor spikes, and ended at the reward-conditioned A arm. Its execution report is explicitly not freeze-ready: two of 37 protected files drifted from their recorded pins, and the run manifest could not check the baseline at run time. The drift predates the pilot and was not caused by it. The motor-bottleneck investigation of the same date analysed the saved run without simulating anything and found that the first-hop current peaked at 164.443 pA, delivering a peak membrane potential of −56.926 mV against a −50 mV threshold, 6.926 mV short, with zero second-hop current and zero of 473 current-receiving targets firing.

On 23 November the six D5/D6 training artifacts were executed: F and F-beta readouts for seeds 9001, 9002, and 9003, each for 20 episodes and 20 checkpoints. All 120 episodes ended in collision with zero motor spikes and no weight change. The F/9001 artifact's resume ledger required a provenance correction; the original record was preserved and a regression test was added. Pilot 2-C then executed all 54 rows of the amended grid: six arms (A, B, F, Fβ, A′, floor) × three seeds × three episodes. Survival scores were identical across arms, A′ reproduced the fixed-weight reference exactly on the declared 19 fields, and all eight P2C claims passed certification. Certification is a statement about the machinery; it is not evidence of learning.

The chronology ends before the N = 16 confirmatory campaign. That campaign was not executed, and the paper does not report its contrasts as results.

## 9.10 Validation history

Table 12 lists the cumulative test-suite counts at each major gate. The counts are not independent evidence: each later suite contains the earlier tests, and the same test can appear at several gates. They are useful as a record of when the software was checked and what was known at the time.

**Table 12.** Cumulative test-suite counts at major gates. Counts include tests inherited from earlier phases. The Phase 7 row includes six pre-existing README-hash failures that are unrelated to the integration. Data source: phase reports and `reports/PHASE_5_FINAL_ASSESSMENT.md`; full machine-readable table in `tables/T20_test_suite_summary.csv`.

| Phase | Tests | Status | Note |
|---|---:|---|---|
| Phase 2 | 68 | passed | LIF, synapses, sampling, recorder, simulator, configs |
| Phase 4D | 331 | passed | full suite at BANC graph construction |
| Phase 4E | 345 | passed | full suite at pathway analysis |
| Phase 4F | 397 | passed | full suite at decoder development |
| Phase 4G | 440 | passed | full suite at BANC propagation |
| Phase 5G | 683 | passed | full suite at plasticity validation |
| Phase 6C | 748 | passed | full suite at MI analysis |
| Phase 6 final | 999 | passed, 3 skipped | information analysis and integration |
| Phase 7 | 1,012 | passed, 3 skipped, 6 failed | six pre-existing README-hash failures |
| Phase 8 D5/D6 | 530 | passed | after pilot training path |
| Phase 8 Pilot 2-C | 531 | passed | after preflight blocker resolution |

The drop from 1,012 at Phase 7 to 530 at Phase 8 D5/D6 is not a regression in coverage. The Phase 7 count includes a different collection and the six README failures; the Phase 8 counts come from the suites run for the training path. The paper reports the values as recorded and does not reconstruct a single monotone series.

## 9.11 What the chronology shows

Three patterns run through the record. First, the project repeatedly narrowed its claims rather than widening them: from a connectome simulation to a structural simulation, from a 14-feature FAFB encoder to a 7-feature BANC mapping, from a conditioning task to a pilot, and from a campaign to a design. Second, every failure is preserved: the negative Phase 5C wall-clock benchmark, the Phase 4H.4 null round trip, the Phase 6 null information contrasts, the Phase 7 zero-motor loop, the Pilot 1 freeze-readiness failure, and the behaviourally null training. Third, the machinery was tested far more thoroughly than the science was confirmed. That asymmetry is the project's actual state, and the remaining chapters report it without repairing it.

# Chapter 10. Phase 6: Mutual Information in the Archived Record

## 10.1 The question Phase 6 could answer

Phase 5 showed that reward-modulated plasticity raised conditioned-response success on a synthetic task. It did not show that the trained network carried more information about the cue. Those are different claims. A network can increase a designated response by becoming more excitable, by shifting a threshold, or by repeating a stereotyped action without representing the cue any better. To distinguish an information gain from a response bias, Phase 6 estimated mutual information between archived variables and tested the paired plastic-versus-fixed contrasts that had been declared before the analysis.

The analysis could only use artifacts that already existed. It did not run a simulation, train a model, or generate a new observation. Every endpoint is therefore bounded by what earlier phases chose to persist. That constraint is the main lesson of the chapter: several questions that would have been natural to ask could not be answered from the archive, and the analysis declares them unavailable instead of substituting a proxy.

Eight guardrails were fixed with the analysis and apply to every result below: mutual information does not establish causation; information about a label does not establish biological perception; neural decoding does not prove that the brain uses the information; structural connectivity does not establish physiological information flow; direct stimulation responses are not downstream activity; a Phase 5 weight change is not evidence of learning without behavioural evidence; deterministic repeats are never independent replicates; and no gameplay label or ground truth was fabricated.

## 10.2 The declared analysis

The estimators and guard rails are those of Chapter 8: plug-in entropy and mutual information in bits, an analytic bias floor reported rather than removed, a minimum of 100 observations and 5 expected observations per cell for a reported estimate, cluster-preserving block permutation, a cluster bootstrap, and an exact sign-flip test for the ten-pair contrasts. The observational unit is the seed or the simulation run, never the timestep or the episode. The only confirmatory family is the pair of paired plastic-versus-fixed task-information contrasts from Phase 5F; everything else is exploratory or descriptive, and is labelled as such in the results.

The confirmatory contrasts use the checkpoint-160 evaluation tables. Each seed contributes 40 held-out episodes to each arm, discretised into a 4 × 4 cue-by-action table. With equal episode counts, the first-order bias floor of 0.1623 bits is common to both arms and cancels in the paired difference. At checkpoint 0 the two arms have identical weights, so the paired difference must be exactly zero; the analysis checks this and obtains 0.0.

## 10.3 The confirmatory result: no information gain

Table 13 reports the two confirmatory contrasts.

**Table 13.** Phase 6 confirmatory mutual-information contrasts on Phase 5F artifacts at checkpoint 160. The estimate is the mean paired difference in bits over ten seeds; the interval is a descriptive percentile bootstrap; the decision is the exact two-sided sign-flip test with Holm correction over the declared family of two. Data source: `experiments/results/phase_6/information_analysis.json`; full machine-readable table in `tables/T08_phase6_information.csv`.

| Wiring | Contrast | Pairs | Mean difference (bits) | 95% CI | Exact p | Holm p | Decision |
|---|---|---:|---:|---|---:|---:|---|
| complete | plastic − fixed | 10 | −0.0863 | [−0.1751, 0.0052] | 0.125 | 0.250 | not rejected |
| random | plastic − fixed | 10 | −0.0025 | [−0.0075, 0.0000] | 1.000 | 1.000 | not rejected |

Neither contrast is rejected. On complete wiring the point estimate is negative: plasticity was associated with 0.086 fewer bits of cue-to-action information per seed, with four of ten paired differences positive and six negative. On random wiring the estimate is essentially zero, with nine exact zeros and one small negative difference. The checkpoint-0 matched control is exactly zero for both contrasts.

The per-condition means put the contrast in context. Fixed complete wiring had a mean MI of 0.6126 bits at both checkpoints. Plastic complete wiring started at the same 0.6126 bits and ended at 0.5262 bits. Fixed random wiring was 1.3547 bits at both checkpoints, and plastic random wiring was 1.3522 bits at the end. The random graph therefore carries more measured cue-to-action information than the complete graph in this task, and plastic training reduced the complete-wiring value. Both observations are descriptive. The analysis makes no causal claim about why the random graph differs, and it does not treat the higher random MI as a virtue: the random condition also has much lower success, so measured information and task performance are not monotonically related.

Figure 20 shows the paired seed-level values. Figure 22 shows the paired differences.

![Figure 20. Phase 5F paired seed-level mutual information between cue and chosen action at checkpoint 160. Each line connects the fixed-wiring and plastic-wiring value for one seed on complete wiring; green marks a seed whose plastic value is higher. The mean difference is −0.0863 bits, the exact sign-flip p is 0.125, and the Holm-adjusted p is 0.250. This is a synthetic 36-node conditioned-response task, not the BANC connectome. Data source: experiments/results/phase_6/information_analysis.json (B_plasticity.conditions).](figures/F14_phase5f_paired.png)

![Figure 22. Phase 6 paired mutual-information differences for the two confirmatory contrasts. Panel (a), complete wiring: six of ten seed differences are negative; mean −0.0863 bits; exact p = 0.125; Holm p = 0.250; not rejected. Panel (b), random wiring: nine exact zeros and one small negative difference; mean −0.0025 bits; exact p = 1.000. At checkpoint 0 both contrasts are exactly zero because the arms have identical weights. Data source: experiments/results/phase_6/information_analysis.json (B_plasticity.contrasts).](figures/F16_phase6_paired.png)

The dissociation is the result. Phase 5F found a large, consistent improvement in designated-response success (0.795 → 0.945) and no supported improvement in cue-to-action information. The success increase is therefore not explained by an increase in the information the chosen action carries about the cue, at least at the resolution of a 4 × 4 table over 40 held-out episodes. It is consistent with a conditioned-response account in which the designated population becomes more likely to spike without the network representing the cue more informatively. That account was proposed before Phase 6 ran, and Phase 6 did not refute it.

## 10.4 Exploratory endpoints: sensory coding

Three exploratory analyses examined how much information the sensory code carries. The first used the Phase 3A.5 distance data. At the calibrated operating point, the four-neuron population produced three response vectors — 2 spikes at distance 0.15, 6 at 0.55, and 7 at 0.90 — and the same vectors appeared under all three mapping seeds. The exact-vector mutual information between distance and response is 1.5849625 bits, equal to log₂ 3, with a bias floor of 0.3206 bits and a corrected value of 1.2644 bits. The normalised MI is 1.0 because the response is a deterministic function of distance. The exact permutation test gives p = 0.0278 over 216 assignments.

Those numbers must be read with the sample size in front. There are 9 observations and 3 clusters, with about 1 observation per table cell. The endpoint is exploratory by the declared rules, and the identical response across seeds means the effective replication is three mapping seeds, not nine independent runs. The result says that the calibrated encoder maps three distances to three distinct population vectors. It does not say that the fly uses a distance code, and it does not generalise beyond the three distances tested.

The population-size sweep is descriptive. Joint distance-to-population MI stays at log₂ 3 = 1.585 bits for population sizes 4, 8, 12, 16, and 24, while the sum of individual-neuron MI rises from 2.755 to 18.366 bits. The sum double-counts information shared by neurons that repeat the same distance identity, and the plug-in bias is positive. The correct reading is that the joint code saturates at the three-level distance identity regardless of how many neurons are added, not that larger populations carry quadratically more information. All groups share one mapping seed, so the sweep is a sensitivity analysis, not an independent replication.

![Figure 23. Phase 6 population-size sweep for the Phase 3A.5 distance code. The joint population MI stays at log₂ 3 = 1.585 bits at every size, the best single-neuron MI stays at 0.918 bits, and the sum of individual MI grows with population size because the same distance identity is repeated across neurons. All groups share one mapping seed; the sweep is descriptive and carries no inference. Data source: experiments/results/phase_6/information_analysis.json (A_population_sweep).](figures/F17_phase6_population.png)

## 10.5 Exploratory endpoint: neural pools to decoded action

The neural-to-motor endpoint asks how much information the decoded action carries about which motor pools were active in the same window. It uses 330 decoder windows nested in 66 Phase 4F runs, five sequential 50 ms windows per run. The primary code marks each of the LEFT, RIGHT, and JUMP pools as active or not, giving eight predictor patterns and four decoded states.

The raw MI is 1.1841 bits, the bias floor is 0.0459 bits, and the corrected value is 1.1382 bits; normalised MI is 0.8128. The block permutation p-value is 0.0005 over 66 clusters. The result is descriptive and circular: the decoder thresholds the same pool activity that serves as the predictor. The estimate therefore quantifies the declared decoder map, not a biological transmission. It is an internal-consistency check, and the paper treats it as such. A gate sensitivity check with thresholds 0.10 and 0.20 produced identical code vectors, because no observed active fraction fell strictly between the two thresholds. That identity is a property of this synthetic drive set, not a general property of the decoder.

![Figure 24. Phase 4F neural-pool to decoded-action mutual information for the declared code and sensitivity variants. The primary any-active-pattern code gives 1.184 bits (bias-corrected 1.138; normalised 0.813) over 330 windows. The estimate is circular because the decoder thresholds the same pool activity used as the predictor; it is an internal-consistency check, not evidence that the brain transmits motor commands. Data source: experiments/results/phase_6/information_analysis.json (D_neural_motor).](figures/F18_phase6_decoder_mi.png)

## 10.6 Exploratory endpoints: reward ablation and conditional information

Phase 6 also estimated cue-to-action information in the Phase 5E conditions and contrasted the outcome-reward condition B against the fixed, zero-reward, shuffled-reward, and traces-disabled conditions. Only three matched replicates exist. The paired differences are small and inconsistent: B − A is −0.0605 bits with one of three differences positive (exact p = 0.5), B − D is −0.0486 bits (p = 0.5), B − C and B − F equal B − A because C and F never change weight. These contrasts are exploratory and underpowered; with three pairs, the smallest attainable two-sided p is 0.25, and no contrast approaches it. They do not support a claim that reward modulation increased task information.

The conditional analysis pools 2,880 training episodes across six conditions and 18 replicate clusters. Marginal cue-to-action MI is 0.3841 bits; conditional MI given condition is 0.6040 bits (bias floor 0.0135, corrected 0.5905; p = 0.0005 over 2,000 permutations). Conditioning raises the estimate because it removes between-condition composition. It does not identify a causal pathway, and the analysis says so in its own warning. The value is exploratory and is not used as evidence for a mechanism.

## 10.7 Endpoints that were not estimable

Seven endpoints were declared unavailable with recorded reasons. They are part of the result, not an appendix of excuses.

- U01, the real-replay sensory-to-neural MI: the Phase 3B.2C replay persists aggregate spike counts only, with no per-neuron or per-frame spike arrays. A sensory-event-to-neural-response table cannot be formed without re-running the simulation.
- U02, spike-train entropy: no archived run persists raw spike times at a scale that supports a per-neuron estimate. The available raw arrays are a 1,564-spike initial run over 800 neurons, a 74-spike propagation smoke test, and a Phase 3C.5 pilot with 64–72 spikes per condition — single trials with few spikes per neuron.
- U03, membrane-potential entropy: membrane potentials were never persisted by any phase.
- U04 and U05, neural-level plasticity and reward-modulation information: the Phase 5 real-BANC demonstration stores six named conditions but only three distinct spike hashes, five sequential decoder windows per condition, and the same decoded-state sequence in every condition. The repeat is deterministic, not an independent observation.
- U06 and U07, cue-to-neural-response and neural-to-reward: in every archived Phase 5E and 5F episode the per-episode cue spike count is the constant 8 and the total is 12 (11 or 12 in condition E). A constant neural response cannot carry information about the cue, and no neural predictor of reward exists without inventing an observation.

The unavailable list is the strongest evidence that the analysis did not fabricate its inputs. Each entry records the artifact that was inspected, the reason the endpoint cannot be formed, and, where relevant, the hash of the source.

## 10.8 What Phase 6 established

Phase 6 established that the archived corpus supports a small, well-defined information analysis, and that its only confirmatory contrasts are null. The Phase 5F success improvement is not accompanied by a supported increase in cue-to-action mutual information; on complete wiring the point estimate is negative. The sensory encoder produces a clean three-level distance code whose joint MI saturates at log₂ 3, but the estimate is exploratory with three effective clusters. The neural-to-motor MI is high by construction and circular. The reward-ablation contrasts are too small and too few to support inference. Seven endpoints that would have been informative cannot be estimated from the stored data.

The chapter therefore answers its question negatively and precisely: **Phase 6 did not find an information gain from plasticity.** It does not show that no such gain exists; it shows that the declared analysis on the archived data did not detect one, and that the success and information measures dissociate. That distinction carries into the Phase 8 design, which treats behavioural success and information as separate outcomes rather than assuming that one implies the other.

# Chapter 11. Phase 7: Closed-Loop Integration

## 11.1 What Phase 7 had to demonstrate

Phase 6 analysed tensors that earlier phases had already written to disk. Phase 7 was the first phase to connect the simulation to the game while the game was running: the current game state was encoded as sensory current, the BANC network advanced, the fixed decoder read the motor pools, and the resulting action was applied to the game before the next observation was taken. The purpose was integration, not learning. Weights were fixed, plasticity was disabled in the configuration, and no training was performed.

Five links had to work for the loop to close. The observation adapter had to convert a game frame into the declared observation schema. The sensory encoder had to turn that schema into per-feature currents on the 232 mapped neurons. The live simulator had to advance the BANC graph by exactly the game's elapsed time. The decoder had to be called on every update and produce a state even when no pool was active. The action adapter had to apply that state to the game and record what was requested separately from what was executed. A sixth link, reward and event provenance, had to preserve the game's own reward components without recomputing them.

Each link is an implementation claim, and each is checkable. None of them is a biological claim. A bridge that executes every step correctly establishes that the software chain is complete; it does not establish that the fly perceives the game, that the mapped neurons are a visual pathway, or that a decoded state is a motor command. The chapter keeps the implementation result and the scientific result separate because the phase produced a clear example of the first and a clear negative example of the second.

## 11.3 The controlled environment and the adapter contract

The environment is the standalone `endless-surfer` implementation described in Section 7.6. It has three lanes, a fixed timestep of 1/60 s (16.6667 ms), automatic forward running, obstacles of type barrier, overhead, and train, and actions LEFT, RIGHT, JUMP, ROLL, and NO_ACTION. The episode configuration used here declares a maximum of 900 steps, an initial speed of 7.0, a maximum speed of 16.0, a coin reward of +1.0, a collision penalty of −1.0, and a survival reward of +0.01 per step. All demonstration runs used the seeds 42, 7, and 123. The reward is a synthetic task reward defined by the game rules; it is not a dopamine measurement, and the paper does not treat it as one.

The observation adapter reports the nearest visible object of each kind — barrier, overhead, and train — with its lane and a distance normalised by a 25-unit horizon. Objects beyond the nearest of their kind are recorded as unrepresented. The adapter has no access to future obstacle positions, because the game observation contains only currently spawned and visible objects. Distances are game-world units divided by the horizon; they are not metric distances. The player-state mapping distinguishes jumping, rolling, and neither, and records a warning when the player has collided.

The action adapter passes LEFT, RIGHT, JUMP, ROLL, and NO_ACTION through unchanged. UNMAPPED and DUCK execute NO_ACTION with a recorded reason, and unknown or invalid outputs also execute NO_ACTION. The requested motor state and the executed game action are stored in separate fields, so no unsupported state can silently become a different action. Two asymmetries follow from the motor stage. The game itself supports ROLL, and the random demonstration agent used it, but the BANC decoder has no ROLL population and can never emit ROLL. The Phase 4 replay does contain ROLL requests, and those requests are mapped to NO_ACTION because the recorded decoder output is marked UNMAPPED. Both facts are recorded in the demonstration file rather than smoothed over.

A more consequential property of the sensory contract is what it omits. The seven BANC features are train lane, obstacle lane, obstacle type, train present, obstacle present, train distance, and obstacle distance. Player lane, player speed, jumping, rolling, and coin state are not among them. The network therefore receives no explicit signal about its own position, its own action, or the coins it is meant to collect. This was a declared property of the Phase 4H.4 mapping, not an omission introduced in Phase 7, and it bounds what any closed-loop result can mean: the loop closes at the level of obstacle appearance and decoded action, not at the level of a full sensorimotor state.

## 11.4 Open-loop demonstrations: validating the harness

Before the live loop was run, Phase 7 ran fixed-seed open-loop episodes with three agent types: a random agent, a rule-based agent, and a replay of recorded Phase 4 decoder outputs. The runs were headless, recorded, and replayed through the game's own strict replay function. The recorded checks `all_replays_ok`, `all_reproducible`, `all_headless`, and `all_rewards_match_phase5` are all true. Table 9 in Chapter 7 lists the nine runs; Figure 26 shows the game-level rewards of the eight open-loop runs.

![Figure 26. Phase 7 controlled-game runs for the random agent (three seeds), the rule-based agent (three seeds), and the Phase 4 decoder replay (two seeds). Bars are total game reward and annotations give the reward and the number of game steps. The rule-based agent reaches 432–531 steps and 10.31–12.30 reward; the random agent reaches 213–332 steps and 2.17–4.31; both Phase 4 replays are truncated at the 300-step limit. All runs are open loop: no BANC simulation ran during these episodes, and all replays and rewards were verified with the game's own replay function. Data source: experiments/results/phase_7/game_integration_demo.json (conditions).](figures/F20_phase7_demo.png)

The quantitative ordering is unsurprising and is not a neural result. The rule-based agent, which reacts to the nearest obstacle with a hand-written policy, survives longest: 432 steps at seed 42, 531 at seed 7, and 432 at seed 123, with rewards 10.31, 12.30, and 10.31. The random agent survives 213, 332, and 218 steps with rewards 3.12, 4.31, and 2.17. The Phase 4 replay is open loop: it plays back a fixed recorded action stream of 200 JUMP and 100 NO_ACTION, is truncated at the 300-step limit in both seeds, and scores 8.00 at seed 42 and 5.00 at seed 7. Because the replay is open loop, its performance measures the recorded stream and the harness, not a live decoder.

The value of these runs is that they exercise the environment, the observation adapter, the action adapter, the recording format, and the replay path under conditions where the correct behaviour is known. They also provide the baseline against which the live loop is usually compared: at seed 42, the random agent ends with 213 steps, 2 coins, 1 collision, score 5.55, and reward 3.12. The coincidence between that row and the live-loop row is examined in Section 11.8 and is not used as evidence.

## 11.5 The live closed-loop bridge

The live bridge subclasses the BANC simulator additively rather than modifying it. The graph is BANC v888 at the five-synapse threshold: 172,433 nodes, 1,535,710 directed edges, and 18,552,546 summed synapses. The sign policy is verified-only, so 683,100 edges and 8,426,168 synapses carry a sign and the remaining 852,610 edges contribute zero current. The neuron parameters are the frozen LIF values of Chapter 6: 200 pF, 10 nS leak, −65 mV rest, −50 mV threshold, −68 mV reset, 2 ms refractory, and 0.5 ms timestep. Background current and noise are both zero. The stepper seed is 20261116, the sensory mapping seed is 20261109, and the environment seed is 42.

Time is advanced by absolute game time, not by wall-clock time. For each update the bridge computes `target_step = round(absolute_game_time_ms / neural_dt_ms)` and calls `advance_to_step(target_step)`. With 16.6667 ms of game time per update and a 0.5 ms neural step, the target alternates between 33 and 34 steps, and the mean is 33.333 steps per update. Rounding error is bounded at half a neural step and does not accumulate. Sensory current is held constant across the neural steps inside one update (zero-order hold) and is recomputed from the new observation at the next update. The configuration declares `wall_clock_used = false`; the run is therefore independent of how fast the host executes it.

The decoder is the unchanged Phase 4F rule on 50 ms windows with activation threshold 0.20, minimum five spikes and three active neurons, and LEFT → RIGHT → JUMP tie order. The pool sizes are LEFT 185, RIGHT 186, and JUMP 20. Plasticity is off, and the recorded weight fingerprint is identical before and after the episode. The episode was allowed up to 300 updates and ended by collision at update 213. Wall time was 22.345 s.

## 11.6 One update end to end

The experiment records a seven-stage pipeline example in addition to the per-update records. At update 1 the observation contains player lane 1.0, player speed 0.4375, no jumping or rolling, and no visible obstacle, train, or coin. All seven feature currents are zero, so the network receives no input at all. The decoder window is `[0, 16.5)` ms, all three pools have zero spikes and zero active neurons, the state is NO_ACTION, and the recorded reason is `neutral_no_activation` with the per-pool detail `spikes_below_minimum+active_neurons_below_minimum`. The game advances one step, awards the 0.01 survival component, and the next observation begins at 16.6667 ms.

At update 119 an obstacle becomes visible and the currents are no longer zero. The recorded per-feature currents are 4,800 pA for obstacle present, 3,200 pA for obstacle lane, 3,076.670248 pA for obstacle distance, and 2,400 pA for obstacle type, for a total of 13,476.670248 pA. The train features remain zero because no train is visible. This is the maximum total sensory current of the episode. The first spike follows at 1,994.5 ms, inside the update-120 window, and 57 spikes are recorded in that update. The one-update offset between the first nonzero current and the first spike is the expected consequence of charging the membrane from rest: the current is applied during update 119, and the threshold is crossed only after the membrane has integrated for about 28 ms.

The pipeline example at update 1 also shows the action path. The requested state is NO_ACTION, the executed action is NO_ACTION, the mapping is marked supported, and the reason is that the motor state maps directly to the game action. The reward record preserves the game's own `reward_components` dictionary and states that FLY-SURFER did not recompute it. The example is not a special case: every update stores the same fields, and the checks confirm that the decoder was called on all 213 updates and that the game advanced on all 213.

## 11.7 The result: activity without motor recruitment

The live loop produced 2,852 spikes over 3,550 ms of game time. Every one of those spikes came from one of the 232 directly stimulated neurons: `non_stimulated_spikes` is 0. Seventy-one of the 232 stimulated neurons fired at least once, the remaining 161 did not, and no neuron outside the stimulated set fired. The activity record covers all 172,433 neurons and reports 172,362 silent neurons, an active fraction of 0.000412, a mean rate of 0.0047 Hz over the whole population, and a maximum single-neuron rate of 14.0845 Hz. The run recorded 10,215 transmitted spikes and no motor spike in any of the three decoded pools.

The temporal pattern follows the sensory input rather than an internal state. Sensory current is nonzero on 95 of the 213 updates, beginning at update 119. Spikes occur on 94 updates, beginning one update later, and the largest single-update count is 59. There are no spikes before the first nonzero sensory current, and no update that contains spikes has zero current. Over the episode the network collected two coins (updates 111 and 159) and collided once (update 213), with reward components +2.0 for coins, −1.0 for the collision, and +2.12 for survival, summing to 3.12. The figure reports the collision at the end of the run.

Figure 25 shows the closed-loop time series. The upper panel is the cumulative spike count and the lower panel is the per-update sensory current. The spike curve is flat until the first obstacle appears, rises in steps while obstacles are visible, and stops at the collision. The current trace is zero for the first 118 updates, jumps to its maximum at update 119, and varies thereafter with obstacle distance and type.

![Figure 25. Phase 7 closed-loop activity and sensory drive at environment seed 42. Upper panel: cumulative spikes over 213 game updates (3,550 ms); 2,852 spikes, all from the 232 directly stimulated neurons, 71 active neurons, and zero motor-population spikes. Lower panel: total per-update sensory current; it is zero for the first 118 updates, reaches 13,476.67 pA at update 119, and varies with the visible obstacle. Every one of the 213 decoded states is NO_ACTION. Data source: experiments/results/phase_7/neural_closed_loop.json (records).](figures/F19_phase7_timeseries.png)

The decoder never had a decision to make. Across 213 windows, LEFT, RIGHT, and JUMP each recorded zero spikes, zero active neurons, and an active fraction of 0.0. The state counts are NO_ACTION 213, with no UNMAPPED and no fallback. The check `decoder_received_motor_activity` is therefore false, and `decoded_action_supported` is false in the narrow sense that no decoded action existed to support; the adapter itself recorded no unsupported or invalid request. The distinction matters: the action adapter was not asked to reject anything, because the decoder never emitted anything but the neutral state.

The stronger statement is that activity did not leave the stimulated population at all. In the full-FAFB replay of Chapter 5, 15.65 million spikes were recorded and 99.976% of them came from non-stimulated neurons; propagation there was extensive. In the BANC closed loop, 2,852 spikes produced 10,215 transmitted spikes and zero postsynaptic spikes anywhere in the graph. The difference between the two runs is not the simulator. It is the graph and the sign policy: the FAFB replay used the early policy in which unlabeled edges were treated as excitatory, while the BANC run propagates only along the 683,100 verified signed edges and treats the other 852,610 edges as zero-current. The observation is consistent with the hypothesis that the verified-only policy leaves too few strong routes from the 232 stimulated neurons to recruit any downstream neuron within one update. The run does not test that hypothesis directly; it establishes the phenomenon that the hypothesis would have to explain.

The result also rules out one innocent explanation of the earlier motor silence. The network was not idle: 71 neurons fired, 2,852 spikes were recorded, and the decoder was called on every update. The failure is not a missing clock, a disconnected recorder, or a decoder that was never invoked. The run executed; the motor pools stayed silent.

## 11.8 Determinism, integrity, and the README baseline

The episode is deterministic. A repeat run produced the same spike fingerprint, `cca811f3…3d3b2fb`, and the same action-and-reward fingerprint, `ddfaa986…02164`, with 213 updates, 7,100 neural steps, 2,852 spikes, a collision termination, and unchanged weights. The weight fingerprint `4923f0cd…945d5` is identical before and after, which is required because plasticity is disabled. The configuration and every input artifact are hashed in the record.

Integrity checking compared 37 pinned files before and after the run. Thirty-six matched; README.md did not, because it had already been changed by commit `efd3a3e` before this experiment and the Phase 4H baseline pins the previous hash. The run records the same single failure before and after, `unchanged_during_run = true`, and an empty `non_readme_failures` list. The full suite at this point was 1,012 passed, 3 skipped, and 6 failed, and all six failures are the pre-existing README pins listed in Chapter 9. The Phase 7 focused tests were 19 passed, and the game repository's own tests were 19 passed. No frozen artifact, protocol pin, or test was modified to remove the discrepancy, and this paper reports it rather than silently correcting it.

## 11.9 An unexplained numerical equality

The live-loop row in Table 9 coincides exactly with the random-agent row at seed 42: 213 steps, 2 coins, 1 collision, score 5.55, and total reward 3.12. The coincidence is not explained by the source records. The two runs are not the same run. The random condition records 15 JUMP, 15 LEFT, 16 RIGHT, 16 ROLL, and 151 NO_ACTION actions, while the live loop records 213 NO_ACTION actions and zero motor spikes. Two agents with different action streams produced identical game-level summaries.

This paper does not resolve the coincidence. It does not assume that the random agent's actions failed to reach the game, that the two rows share a recording, or that the game is action-insensitive; each of those would be an inference beyond the archived evidence. The paper flags the equality as a documentation issue, uses neither row as evidence about the other, and bases the live-loop conclusion on the fields that are internal to the neural run: the per-update action counts, the spike attribution, the weight fingerprints, and the decoder evidence fields. Those fields establish that the loop emitted NO_ACTION 213 times and that no motor neuron spiked. The game-level comparison with the random baseline is not needed for that conclusion and is not used to support it.

The equality is also a reminder that a recorded summary is not a replication. The demonstration rows were generated by a different command from the live-loop record, at a different time on the same day, and the two outputs are separate files with different content. Agreement between two summaries is not agreement between two mechanisms. Chapter 19 lists this among the unresolved documentation issues.

## 11.10 What integration established and what it did not

Phase 7 established that the full chain executes. Game state becomes sensory current, current drives the simulated network, the decoder is called on every update, the action adapter records requested and executed actions separately, rewards and events keep their game-side provenance, and the episode replays deterministically. It established the timing rule: absolute game time, 33 or 34 neural steps per 16.6667 ms update, bounded rounding, no wall-clock dependence. It established that the run is reproducible at the level of spike and action fingerprints.

It did not establish perception, a sensory pathway, a motor command, or learning. The 232 neurons are a labelled hypothesis, not a measured visual pathway. The seven features omit the agent's own state and the coins. LEFT, RIGHT, and JUMP are decoder labels on annotation-defined populations, and no limb model exists. The weights are fixed, so the run measures control, not plasticity. The network never produced a non-neutral action, so the game was played by a fixed policy of inaction regardless of what the sensory stream contained.

The phase's scientific value is diagnostic. It shows that the failure seen in the Pilot 1 runs is not an artifact of a missing integration layer. When the loop is closed and every component is confirmed to execute, the motor pools remain silent and every decision is NO_ACTION. Chapter 14 takes that result apart at the level of individual first-hop synapses and identifies where the current stops.

## 11.11 Summary

Phase 7 connected the BANC simulation to the controlled game and ran the loop for 213 updates. The bridge is deterministic, time-synchronised, and fully recorded; every execution check passed except the two that describe the absence of motor activity. The network produced 2,852 spikes, all from directly stimulated sensory neurons, and zero spikes anywhere else. The decoder returned NO_ACTION on all 213 windows. The open-loop demonstrations validate the environment and the adapters but say nothing about the network. The live loop says something specific and negative: the integration works, and the motor channel is silent. The next chapter describes the protocol that was written to test learning once that channel could be made to speak, and the chapters after it report why the protocol could not be evaluated as designed.

# Chapter 12. Phase 8: Experimental Design and Pre-registration

## 12.1 Why a pre-registered campaign was written

By the end of Phase 7 the project had a working simulation, a working game bridge, and a clear negative result: the motor pools were silent in every closed-loop run. The natural next question was whether any learning mechanism could change that. Phase 8 was designed to answer it with a pre-registered campaign rather than an open-ended search. The protocol fixed the conditions, the hypotheses, the primary outcome, the statistical test, the sample size rule, the random-graph construction, and the integrity gates before any campaign data existed.

The design document is `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`, 1,915 lines, SHA-256 `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`. It supersedes REV3, REV2, and V1, each preserved byte-identical. A later Pilot 2-C amendment, SHA-256 `832ef485…667ad`, added a reduced pilot grid without changing the campaign design. The protocol was frozen with a separate hash record and was never edited to fit an outcome.

The status of the design must be stated plainly. The protocol was written and frozen; the supporting software was implemented and tested; two small pilots were executed; **the N = 16 confirmatory campaign was never run**. No contrast C1–C4 was estimated, no hypothesis H1–H3 was tested, and no confirmatory claim from Phase 8 exists. This chapter describes what was planned. Chapters 15 and 16 describe the training artifacts and the Pilot 2-C execution that did occur, and explain why neither can substitute for the campaign.

## 12.2 The six conditions

All six conditions share the same controlled environment, the same reward definition, the same action vocabulary, the same termination rules, the same 900-update cap, and the same evaluation-seed schedule. They differ only in what proposes the action and what, if anything, is allowed to change. Table 14 summarises the design, including the control arms that are not conditions.

**Table 14.** Phase 8 conditions and control arms. Conditions A–F are the six declared experimental conditions; A′, C′, Fβ, F-init, and floor are controls that produce no new scientific claim of their own but gate the interpretation of B, D, and F. "Changes" states what may change during an episode or during the condition's declared training phase. Data source: `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` sections 3.1–3.8 and `configs/phase_8/`.

| Arm | Topology | Weights | Action selection | What changes | Role |
|---|---|---|---|---|---|
| A | BANC v888 t5 biological | fixed structural | fixed threshold decoder | nothing | reference condition |
| B | BANC v888 t5 biological | plastic | fixed threshold decoder | synapses, three-factor rule | plasticity on biological substrate |
| C | randomized, degree- and sign-preserved | fixed structural | fixed threshold decoder | nothing | topology control |
| D | randomized, degree- and sign-preserved | plastic | fixed threshold decoder | synapses, three-factor rule | plasticity on random substrate |
| E | none (MLP) | trained | argmax over four logits | all parameters | conventional-learner reference |
| F | BANC v888 t5 biological | connectome fixed | trained linear readout | readout only | decoder-versus-network test |
| A′ | BANC v888 t5 biological | fixed through plastic path, η = 0 | fixed threshold decoder | nothing | exact-identity control for B |
| C′ | randomized graph | fixed through plastic path, η = 0 | fixed threshold decoder | nothing | exact-identity control for D |
| Fβ | BANC v888 t5 biological | fixed | bias-only readout | output biases only | constant-policy control for F |
| F-init | BANC v888 t5 biological | fixed | untrained F readout | nothing | unlearned-readout diagnostic |
| floor | none | none | constant NO_ACTION | nothing | substrate-free game baseline |

Condition A is the reference. It uses the BANC t5 graph with 172,433 nodes, 1,535,710 edges, the deterministic weight transform `min(5.0 · count^0.75, 300)` pA, verified-only signs, 232 mapped sensory neurons, 805 motor neurons, and the unchanged Phase 4F decoder. Reward is logged but never reaches the network. Condition B is identical except that weights change under the Phase 5 three-factor rule with η = 0.5, bounds 0.5–2.0× initial, a 5 pA per-update cap, τ_e = 20 ms, and the same verified-only edge set. Condition C replaces the biological topology with a signed, degree-preserving directed randomization of the same edge list, keeping the original weight multiset and annotations. Condition D applies B's plasticity rule on C's topology.

Condition E is a small multilayer perceptron with the same seven encoded features as the neural conditions, two 64-unit tanh hidden layers, and four output logits for LEFT, RIGHT, JUMP, and NO_ACTION. It is trained by REINFORCE with a learned value baseline and Adam, using the same reward scalar, with training seeds disjoint from evaluation seeds. A fourteen-feature variant, E-full, is exploratory. E is a reference point, not a matched control: it has direct credit assignment to its own parameters and the neural conditions do not. Its scientific role is to answer a prior question: if a conventional learner also sits at the floor on this observation interface, then the environment is not solvable from the interface and no neural failure can be attributed to the connectome.

Condition F keeps the connectome and the live stepper unchanged and replaces the fixed threshold decoder with a trainable linear readout over per-decision motor-population activity. The readout does not see the sensory features directly; it sees only what the motor populations did. This is what makes F a test of the network's output rather than a second controller. ROLL and DUCK are excluded because no motor population for them exists. The connectome is asserted unchanged five ways per episode, and the readout is checkpointed rather than written into the graph.

The design has one stated interface asymmetry. The neural conditions receive seven of the fourteen observation features because seven features have no mapped population. E-matched therefore receives the same seven, and E-full receives all fourteen as an exploratory ceiling. No condition receives pixels, future obstacle positions, hidden game state, or reward before the action is applied.

## 12.3 The control arms and what they certify

The controls are not decoration. Each one removes a specific way the main conditions could be misinterpreted.

A′ runs condition A through the same plastic code path that B uses, with η exactly 0.0. It exists because a B − A difference could otherwise arise from the plastic pipeline itself — different data structures, different accumulation order, different precision, different clamp bookkeeping — rather than from plasticity. A′ must reproduce A exactly on nineteen declared fields: spike times and indices, both episode fingerprints, the full serialised record sequence, survival and termination, action and decoder-state counts, rewards, neural and game time, per-decision motor activity, all four weight digests, maximum absolute weight change, changed-edge count, clamp hits, the stepper fingerprint, and resets. The comparison has zero tolerance. On the first mismatch the B arm is marked invalid, any B result is retained but excluded from every aggregate, and the campaign stops. There are no silent retries and no seed shopping. C′ is the same control on the random graph and certifies D.

Fβ is the constant-policy control for F. Its feature weights are fixed at zero and only its output biases train, so it can learn a fixed action but cannot use motor information. F − Fβ, contrast C4, is the only contrast that can support a motor-decoding claim; F − A alone is not enough, because a bias term can produce it with silent motor populations. F-init is the F architecture at its seeded initial parameters with no training, a diagnostic for whether any F result is merely the initial readout. The floor arm is a substrate-free constant NO_ACTION policy, scored on the same paired environment seeds, and it defines the game-side no-action baseline against which every condition is read.

The random-graph control is certified rather than assumed. Condition C is built by directed double-edge swaps that preserve per-node in-degree and out-degree, the global weight multiset, per-source outgoing weight profiles, node identities, annotations, and transmitter signs. The protocol requires at least 99% of original directed pairs to be rewired, an edge-set Jaccard of at most 0.01, exact degree preservation on both sides, exact sign preservation, an unchanged weight multiset, zero duplicate pairs, zero self-edges, valid CSR invariants, mean active-node neighbourhood overlap of at most 0.01, and a rewiring-distance plateau over the last 20% of accepted swaps. A graph that fails any gate is rejected; the campaign does not fall back to a less-random graph and does not relax a gate. Sixteen null graphs were constructed and certified, one per campaign seed, and each is shared by C, D, and C′ so that the paired contrasts use the same topology.

## 12.4 Hypotheses and the confirmatory family

Six hypotheses were declared. H1 is that reward-modulated three-factor plasticity changes survival on the biological substrate, tested by B − A. H2 is that the biological graph outperforms a degree- and sign-matched random graph, tested by A − C. H3 is that a trainable readout over the fixed biological substrate beats the fixed threshold decoder, tested by F − A. H4 is an explanatory reference: a conventional learner on the same seven-feature interface reaches above the no-action floor. H5 is exploratory: any plasticity benefit is not specific to biological topology, tested by the interaction (B − A) − (D − C). H6 is descriptive: every non-NO_ACTION action is preceded by at least one spike in the corresponding motor population within the decoding window.

The confirmatory family has four contrasts, Holm-corrected at a family-wise α = 0.05 (Table 15).

**Table 15.** Phase 8 confirmatory contrasts and their mapped hypotheses. C1–C4 are the four pre-registered differences; H1–H3 are the confirmatory hypotheses they test. H4–H6 are explanatory, exploratory, or descriptive and are outside the confirmatory family. Data source: `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` sections 5–7; Appendix Table F1.

| ID | Contrast | Hypothesis | Interpretation |
|---|---|---|---|
| C1 | F − A | H3 | contribution of a trainable readout on the biological substrate |
| C2 | B − A | H1 | contribution of three-factor synaptic plasticity |
| C3 | A − C | H2 | contribution of biological over random connectivity |
| C4 | F − Fβ | decoding gate | whether the readout uses motor information at all |

H1 maps to C2, H2 to C3, and H3 to C1. H5 and H6 are exploratory or descriptive and cannot be promoted after seeing data. The protocol also states the prior expectation for each confirmatory hypothesis: H1 was expected to fail because the Phase 6 contrast was negative and the Phase 7 loop never recruited a motor neuron; H2 was expected to be null because both arms were expected at the floor; H3 was expected to fail because a readout over silent populations cannot beat a constant policy. These expectations are part of the record and are not rewritten after the fact.

Two consequences of the design are worth stating. First, a significant C1 would not by itself establish motor decoding; C4 and the protocol's evidence bar are also required. Second, if all arms floor, the paired differences are exactly zero, the sign-flip test returns p = 1.0 by construction, and the correct report is that the design has no power against a difference between two floored conditions — not that the conditions are equivalent.

## 12.5 Primary outcome and smallest effect of interest

The primary outcome is the mean capped survival score per evaluation episode, in game updates, averaged over the K evaluation episodes within a seed. The capped score is `min(observed_updates, 900)`. It is defined for every episode, including episodes that collide on update 1 and episodes that reach the cap. The protocol distinguishes three quantities that are often conflated: observed termination time, which is undefined for cap-reaching episodes; the cap-reaching fraction, which is a floor diagnostic; and the capped score, which is the primary comparison.

A cap-reaching episode is not an ordinary right-censored observation. The 900-update horizon is an administrative cap, and the outcome is deliberately bounded, so the estimand is the cap-restricted score rather than a survival time. Kaplan–Meier curves and log-rank tests target a different quantity and cannot replace the primary. If a time-to-event analysis is reported at all, it must be declared separately as a sensitivity analysis with an explicit censoring model.

The declared smallest effect of interest is 100 updates, about 1.67 s of game time, about 11% of the cap, and about 1.5 times the three-seed random-agent standard deviation of 67.3 updates. It is a declared convention, not a derived quantity: the obstacle cadence was not measured, so the designers could not derive the distance at which a difference becomes behaviourally meaningful. The SEI enters the sample-size rule and is not used as a post hoc threshold.

## 12.6 Pairing, replication, and the sample-size rule

The design is paired within seed. Episode j of seed s uses environment seed `derive(master, s, j, "env")`, independent of the condition, so all conditions face the same initial layouts in the same episode index. Environment seeds, network seeds, learning seeds, and structure seeds are four separate streams derived from a master seed of 20261116. The environment and structure streams deliberately omit the condition, because pairing requires a shared environment and one graph per seed; the network and learning streams include it. Sharing one RNG across purposes is forbidden.

Each seed contributes K = 10 evaluation episodes per condition, each with a full reset and no state carried between episodes. Episode values are averaged within a seed before the primary test, so the seed remains the independent unit. Treating the 160 seed-episode cells as independent would overstate the evidence, because episodes within a seed share a network draw and, for E and F, a training trajectory.

The primary design is N = 16 paired seeds. N = 10 is available only as a pre-declared fallback, and only if the pilot's largest paired standard deviation among C1–C4 satisfies `2.8016 · σ_max / √10 ≤ 100`, which is equivalent to `σ_max ≤ 112.87`. The bound is computed from the normal-theory minimum detectable effect `MDE = 2.8016 · σ_max / √N`; it is an approximation, not exact power for the sign-flip test. The protocol is explicit that a three-seed standard deviation cannot establish this bound with the required precision, which is why N = 16 is the default and why the paired pilot had to include B, C, F, and Fβ rather than only A and F. The choice between N = 16 and N = 10 is made once, before the campaign, from the pilot's σ_max and its uncertainty. It is never revisited after a campaign outcome is seen. If the pilot cannot support N = 10 and the budget does not permit N = 16, the campaign does not start.

The normal-theory MDE at N = 16 with an assumed σ of 60 updates is about 42 updates. The Holm step-1 MDE, using α/4 = 0.0125, is about 50 updates. The assumed σ of 60 is not a measurement; it sits between the Phase 7 random-agent and rule-based between-seed standard deviations, and the protocol says so. The paired design is expected to have a smaller σ than an unpaired comparison, so 60 is conservative for the point estimate but not a defensible upper bound at three seeds.

## 12.7 The exact sign-flip test

The primary test is a two-sided exact sign-flip permutation test on the N paired per-seed differences. The statistic is the mean paired difference over sign assignments, and the p-value is the fraction of the 2^N sign vectors whose absolute statistic is at least the observed absolute statistic. There is no normal approximation, no Monte Carlo sampling, and no asymptotics. The test is applied to C1–C4 and followed by Holm correction over the four contrasts.

At N = 16 there are 65,536 sign vectors and the minimum attainable two-sided p is 2/65,536 = 0.0000305176. At N = 10 there are 1,024 vectors and the minimum is 2/1,024 = 0.001953125. The minimum is attained by the two extremal vectors `sign(d)` and `−sign(d)`, not by "all plus" and "all minus" unless all differences share a sign. The exactness rests on the paired differences being exchangeable under sign reversal; the design controls the shared-environment and shared-network sources of dependence by pairing, but it does not remove differences in dispersion between arms, and the protocol states that limitation.

A paired difference of exactly zero is kept, contributes zero to every sign vector, and cannot distinguish the arms. If every difference is zero, every sign vector has the same statistic, the p-value is 1.0 by definition, and the test is uninformative. Missing pairs are reported with reasons, dropped only when structurally undefined or invalid, and the thresholds are recomputed at the actual number of complete pairs. A whole cell that errors is handled with a pre-specified sensitivity analysis that scores the error at its last completed update, and asymmetric missingness is disclosed rather than hidden behind a complete-case result.

Figure 39 shows the attainable two-sided p as a function of N, with the α = 0.05 and Holm step-1 thresholds marked.

![Figure 39. Minimum attainable two-sided p-value of the exact sign-flip test as a function of the number of paired seeds N, from N = 6 to N = 20. The minimum is 2/2^N; at N = 10 it is 0.00195 and at N = 16 it is 0.0000305. The dashed line is α = 0.05 and the dotted line is the Holm step-1 threshold α/4 = 0.0125 for a family of four. This is a property of the permutation group, not a power calculation, and it says nothing about the probability of observing a given effect. Data source: docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md section 7.3.](figures/F33_statistical_design.png)

## 12.8 Integrity gates and the authorization chain

The protocol treats implementation integrity as a precondition for interpretation, not as a post hoc check. The A′ and C′ identity comparisons are the clearest example: η = 0 must be an exact identity, not a small effect, and "almost identical" does not establish identity. A tolerance would convert a correctness property into a similarity heuristic, so the protocol permits none. Eligibility traces are allowed to be nonzero because the trace machinery still runs; every weight delta must be exactly zero.

The campaign also requires the 37-file protected hash baseline to be checked before and after, with the known README drift reported as a pre-existing condition. The connectome fingerprint is recorded before and after every episode and asserted equal in A, C, and F. In B and D only the WeightState may differ, and the full digest chain from structural to initial to learned delta to effective weights is recorded. Phase 3–6 results, datasets, external repositories, and the standalone game are read-only.

Execution was gated by a sequence of dated owner decision records, D1–D6, each authorizing one stage rather than the whole program. The protocol itself required human approval before any confirmatory pilot, campaign, or training run. Implementation scaffolding was authorized separately and is not evidence that a condition ran. This separation is why the repository can contain a complete campaign runner, certified null graphs, trained artifacts, and a 54-row Pilot 2-C grid while still reporting that no confirmatory campaign was executed.

## 12.9 What the design could and could not establish

The design could establish a causal effect of three-factor plasticity on survival if B differed from A while A′ stayed exactly equal to A. It could establish a topology effect if A differed from C on paired seeds. It could establish that a readout uses motor information if F differed from Fβ and the protocol's evidence bar was met. It could establish that the environment is solvable from the seven-feature interface if E-matched beat the floor. Each of these is a bounded behavioural claim, not a claim about the fly.

The design could not establish that the connectome is a physiological model, that the mapped sensory neurons are a visual pathway, that LEFT, RIGHT, and JUMP are biological motor commands, or that any weight change is learning in the fly. It also could not rescue a floor: if A–D all produced NO_ACTION, the contrasts would be exactly zero and the test would return p = 1.0. The protocol anticipated that case, pre-specified a floor report, and forbade tuning the stimulus amplitude, decoder threshold, or mapping after seeing it. The floor result from Phase 7 was known when the protocol was written, and the design was built to report it rather than to engineer around it.

## 12.10 Summary

Phase 8 is a frozen, pre-registered design with six conditions, five control arms, four Holm-corrected contrasts, a bounded survival primary, paired environment seeds, four independent random streams, an exact sign-flip test, and a sample-size rule that cannot be changed after seeing an outcome. Its random-graph control is certified against the protocol's eighteen-item randomisation report, and its plasticity path is certified by an exact η = 0 identity on nineteen fields. The campaign itself was never executed. The next chapters report what was executed instead: a nine-episode Pilot 1 that established the motor floor, a mechanistic investigation of the first-hop current, six trained readout artifacts that were technically certified but behaviourally null, and a 54-row Pilot 2-C grid that could not estimate any campaign contrast. Those results are reported within their own scopes and are never presented as the confirmatory campaign.

# Chapter 13. Pilot 1: A Viability and the Motor Floor

## 13.1 What Pilot 1 was authorised to do

Pilot 1 was the first executable stage of the Phase 8 design. Its scope was deliberately narrow: condition A only, three seeds (9001, 9002, 9003), three episodes per seed, nine episodes total. It used the biological BANC substrate with fixed weights and the unchanged threshold decoder. It did not use a randomized graph, a trained artifact, plasticity, training, or any other condition. It did not estimate C1–C4, did not test H1–H6, and was not merged into the campaign dataset.

The narrow scope was enforced by the authorization layer, not merely stated in a plan. The owner decision record D2, dated 2026-11-20, records the exact grid and the negative capability flags: no randomized graph, no trained artifact, no parameter modification, and no weakening of random-graph certification. The stage authorization code hard-codes the nine-entry grid so that a changed configuration cannot widen it, validates D2's hash against the REV4 file on disk, and leaves every other stage blocked. Pilot 2, training, composition, and the campaign cannot inherit the exemption. The record is a stage gate, not a protocol amendment; REV4's hash is unchanged.

The purpose was to answer one question: does the A pipeline run end to end on the frozen substrate and produce a measurable behavioural result? It was not designed to estimate an effect. Three seeds and three episodes are a viability sample, and the report says so in its own terms.

## 13.2 Execution and provenance

The pilot executed through the production path on 2026-11-20, from 10:58:51Z to 11:04:48Z, with a wall time of 357.0 s. All nine planned episodes ran. The run summary records `executed = true`, `rows_stored = 9`, `rows_executed = 9`, `planned = 9`, `complete = true`, `evidence_kind = pilot`, `experimental_evidence = true`, `estimates_contrasts = false`, and `merged_into_campaign = false`. The episode rows are in `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`, SHA-256 `ee479e5b…68f9`; the driver record is `reports/PHASE_8_PILOT1_EXECUTION.json`, SHA-256 `d3392b9c…e1e`.

Each row carries condition A, role reference, `training = false`, status ok, seven frozen-input hashes, and three configuration hashes. The production runner loaded the BANC world lazily and recorded provenance before each episode. The run-start memory gate reported 5.745 GiB available against a 4.0 GiB gate. Passive sampling at 2 s intervals produced 177 samples, a maximum process RSS of 0.3725 GiB, and a minimum system-available value of 4.1997 GiB, so the memory gate held throughout.

The run did not exceed the 900-update cap in any episode: all nine terminated by collision, with `truncated = false`. No fallback, unmapped action, or invalid output was recorded. Every decision was the decoder's neutral state, produced by the threshold rule rather than by an error path.

## 13.3 Nine episode results

Table 16 reports the nine episodes. Figure 27 shows survival and spike counts.

**Table 16.** Pilot 1 nine-episode A-viability grid. All rows are condition A on the frozen BANC t5 substrate with fixed weights and the unchanged decoder. Survival is game updates completed before collision; neural steps are 0.5 ms simulation steps; motor spikes are the sum over the LEFT, RIGHT, and JUMP pools. Every episode ended by collision and none reached the 900-update cap. Data source: `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`; full machine-readable table in `tables/T10_pilot1_episodes.csv`.

| Seed | Episode | Environment seed | Game updates | Neural steps | Total spikes | Motor spikes | Reward | Termination |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 9001 | 0 | 563774599 | 323 | 10,767 | 4,764 | 0 | 5.22 | collision |
| 9001 | 1 | 2911696168 | 620 | 20,667 | 14,348 | 0 | 10.19 | collision |
| 9001 | 2 | 4240939637 | 323 | 10,767 | 4,764 | 0 | 4.22 | collision |
| 9002 | 0 | 2632356062 | 620 | 20,667 | 14,911 | 0 | 7.19 | collision |
| 9002 | 1 | 307060235 | 426 | 14,200 | 8,396 | 0 | 3.25 | collision |
| 9002 | 2 | 4241804999 | 620 | 20,667 | 13,139 | 0 | 8.19 | collision |
| 9003 | 0 | 2839813884 | 213 | 7,100 | 2,850 | 0 | 3.12 | collision |
| 9003 | 1 | 756850162 | 426 | 14,200 | 7,856 | 0 | 4.25 | collision |
| 9003 | 2 | 2981106662 | 213 | 7,100 | 2,852 | 0 | 2.12 | collision |

The totals are 3,784 game updates, 126,135 neural steps, and 47.75 total reward. Survival ranges from 213 to 620 updates, or about 3.55 s to 10.33 s of game time at 60 updates per second. Reward ranges from 2.12 to 10.19. The values are descriptive of this nine-episode sample; they are not an estimate of a condition effect and should not be compared as if the seeds were independent replicates of a campaign.

![Figure 27. Pilot 1 nine-episode outcomes on the frozen BANC substrate. Panel (a): game updates survived before collision for each seed and episode; all nine end by collision, with survival between 213 and 620 updates. Panel (b): total neural spikes per episode, between 2,850 and 14,911; motor-population spikes are zero in every episode. The row values sum to 3,784 updates and 73,880 spikes. Data source: experiments/results/phase_8/pilot1/pilot1/episodes.jsonl.](figures/F21_pilot1_episodes.png)

## 13.4 The spike total: 72,880 and 73,880

The nine episode rows sum to **73,880** total spikes. The execution report's prose totals state **72,880**, and the same figure appears again in the report's discussion of the zero-motor result. The difference is exactly 1,000 spikes, or about 1.35% of the row sum. It is a transcription error in the report's prose, not a difference between the data and the report about which episodes ran: all nine rows are present, their other fields are internally consistent with the summary, and the row values are the recorded measurements.

This paper uses **73,880** everywhere it reports the Pilot 1 total, including Table 16, the abstract, Chapter 17, and the consolidated tables. The original historical report is preserved unchanged and is not silently corrected. The discrepancy is disclosed here so that a reader comparing the paper with the report sees the same episode rows and understands why the prose totals differ. The figure's own source note records the same relationship between the rows and the report prose.

## 13.5 Zero motor output

Every one of the 3,784 decisions was NO_ACTION. The LEFT, RIGHT, and JUMP pools recorded zero spikes in every episode, `windows_with_motor_spikes` is 0 throughout, and the decoder fallback dictionary is empty. The zero is not an error fallback: the decoder was called, it evaluated the pools, no pool met the five-spike, three-active-neuron, 0.20-active-fraction gate, and it returned the neutral state by the declared rule.

The network was not silent or dead. Total spike counts range from 2,850 to 14,911 per episode, so the simulation was active and the recorder captured it. The weight fingerprint `4923f0cd…945d5` is identical before and after every episode, as required for a fixed-weight condition; the structural and initial digests also did not change. Condition A did what it was defined to do. It simply never produced a motor action.

This is a substantive negative result for the A configuration. It is consistent with the Phase 7 closed-loop result and with the earlier Phase 4 sensory-to-motor findings, but it is not evidence about a fly, and it must not be re-described as a biological motor result. It also does not identify which part of the chain failed. The next chapter takes the same run apart at the level of first-hop synapses and locates the current shortfall.

## 13.6 Integrity, freeze status, and documentation nuances

The pilot is **not freeze-ready**, and the reason is external to the episode measurements. A read-only post-run check of the 37-file protected baseline found 35 matching files and two drifts: README.md, whose drift was already present during Phase 7, and `motor/__init__.py`, whose current content was introduced by commit `3c74ae8` on 2026-11-19, before this execution. Because `motor/__init__.py` is a non-README failure, the integrity check returns `pass = false`, and the run manifest records `integrity.checked = false`. The drift was not created by the D2 implementation or by Pilot 1, and it was not changed to make the pilot pass. Resolving it requires an authorised amendment or a compliant restoration, neither of which was performed. The episode rows remain valid measurements of the model; the protocol's publication gate is not passed.

The pilot's test record is consistent with that reading. The D2 authorization tests were 18 passed, the affected Phase 8 modules were 284 passed, and the full suite was 1,503 passed, 3 skipped, and 6 failed. The six failures pre-date this work and are unrelated to Pilot 1: three protected-hash checks report the README drift, two smoke-mode labels report `SMOKE INVALID` instead of `SMOKE ONLY`, and one C0 cache assertion fails. No test executes a real episode.

Two documentation nuances are recorded rather than rewritten. First, `pilot_plan.json` is the pre-execution plan copy and still says `executed = false`; the authoritative records are `pilot_summary.json`, the manifest, and the nine rows, all of which record the run as executed. Second, the report's prose spike total is the 72,880 described in Section 13.4. Neither nuance changes an episode value, and neither is used to weaken or strengthen a scientific claim.

## 13.7 What Pilot 1 established and what it did not

Pilot 1 established software viability. The frozen BANC substrate loads and runs inside the controlled game environment; the provenance chain is complete and self-consistent; the fixed-weight condition holds its fingerprint; the recorder captures spikes, actions, rewards, survival, and terminations without fallbacks or errors. It also established the floor: in this configuration, on these seeds, the decoder never selected a motor action, and the game ended by collision in every episode.

It did not establish a sensory-to-motor transformation, a biological motor code, a learning effect, or a condition contrast. Three seeds and three episodes are not an inference sample; the pilot cannot estimate C1–C4 and cannot test H1–H6. It cannot say whether the floor is caused by the sensory mapping, the current scale, the verified-only sign policy, the decoder threshold, or some combination. Those are hypotheses for the bottleneck analysis in Chapter 14, and the protocol forbids tuning any of them after seeing this result without a new authorised analysis.

## 13.8 Summary

Pilot 1 ran the A condition nine times on the frozen BANC substrate. All nine episodes executed, all ended by collision between 213 and 620 updates, and all 3,784 decisions were NO_ACTION. The network produced 73,880 spikes by the row sum and zero motor spikes. The execution report's prose says 72,880; the rows are authoritative and the original report is preserved unchanged. The pilot is operationally viable and scientifically null on motor output, and it is not freeze-ready because of a pre-existing protected-baseline drift. The next chapter explains, synapse by synapse, why the current that produced those spikes did not reach a single motor neuron.

# Chapter 14. The Motor Bottleneck

## 14.1 The question and the method

Pilot 1 produced 73,880 spikes and zero motor spikes across nine episodes. Phase 7 produced 2,852 spikes and zero motor spikes in one 213-update closed loop. Phase 4H.4 produced 3,562 spikes and zero motor spikes in a two-segment sensory replay. The repetition makes the outcome robust, but it does not explain it. The bottleneck investigation asked where, along the sensory-to-motor chain, the signal stops.

The investigation was read-only. It analysed existing artifacts, re-derived signed reachability from the frozen BANC graph, and compared the recorded runs. It did not re-run a simulation, change a neural equation, weight, threshold, seed, or configuration, regenerate a graph, or touch the REV4 and D1/D2 records. Its conclusions are therefore about the same frozen model that produced the pilots, not about a modified model built to pass.

The analysis has one important limitation that is stated at the outset. Pilot 1's persisted rows do not contain the stimulated/non-stimulated spike split, the active-neuron count, the transmission count, or any membrane potential. The stage stores a reduced 21-field view with total spikes, motor spikes, per-population spikes, actions, rewards, weights, and hashes. The first-hop conclusion therefore rests on four convergent legs: Pilot 1 used the same frozen inputs as the instrumented Phase 4H.4 run, byte-identical across seven hashes; it used the same production loop with zero background and zero noise; the structural query of the frozen graph reproduces the same first-hop targets; and the same design was directly measured in Phase 7 and Phase 4H.4. The conclusion is a convergent inference, not a direct per-neuron measurement of Pilot 1, and the paper labels it that way.

## 14.2 The sensory layer is not the failure

The 232 mapped sensory neurons are driven at 200 pA per active feature, with zero-order hold and a 150 ms pulse decay. Their overlap with the 805 motor neurons is zero, and their overlap with the LEFT, RIGHT, and JUMP pools is zero. In the instrumented Phase 4H.4 run, 171 of the 232 fired over 3.3 s and produced 3,562 spikes; in Phase 7, 71 of 232 fired over 3.55 s and produced 2,852 spikes. In both runs every spike in the network lay inside the stimulated set. In Pilot 1, total spikes range from 2,850 to 14,911 per episode, so the sensory layer was active there too.

Recruitment is partial and depends on the duration and pattern of drive. That is a real observation, but it is not the stopping point. The stimulated neurons do spike, and their spikes are delivered to the graph. What fails is the conversion of that delivery into a postsynaptic spike.

## 14.3 The first hop

The frozen graph gives the stimulated set 662 signed outgoing edges to 608 distinct targets, of which 607 are non-stimulated and one is a recurrent stimulated neuron. None of the first-hop targets is a motor neuron. This is a property of the annotation graph under the verified-only sign policy, not a result of the simulation.

In the instrumented Phase 4H.4 run, 473 of the 607 non-stimulated first-hop targets received synaptic current. The current distribution is skewed: the median target receives 0 pA, the 95th percentile is 80.87 pA, and the maximum is 164.443 pA. The largest static signed sum in the graph is 167.041 pA to node 125949, so the recorded peak is close to the strongest route the graph can offer.

The decisive measurement is the membrane. Rest is −65 mV and threshold is −50 mV, so 15 mV of depolarisation is required. The strongest first-hop target reached −56.926 mV. That is 8.074 mV of depolarisation and 6.926 mV short of threshold. No first-hop neuron came within 2 mV or 5 mV of threshold, and zero of the 473 current-receiving targets fired.

![Figure 28. Pilot 1 first-hop signal funnel from the 232 stimulated sensory neurons. The 232 neurons have 662 signed outgoing edges to 608 distinct targets, of which 473 receive current in the instrumented Phase 4H.4 run and 0 cross threshold. The peak somatic depolarisation is −56.926 mV against a −50 mV threshold, and no second-hop current is delivered because no first-hop neuron spikes. Data source: reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md, a read-only analysis of the Pilot 1 run.](figures/F22_pilot1_firsthop.png)

![Figure 29. Peak membrane depolarisation at the first hop versus rest and spike threshold. Rest is −65 mV, the recorded peak is −56.926 mV, and threshold is −50 mV, leaving a 6.926 mV shortfall. This is a single recorded peak across the analysed first-hop targets, not a population distribution. Data source: reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md.](figures/F23_membrane_threshold.png)

## 14.4 Why a current above rheobase does not produce a spike

The peak current of 164.443 pA is above the steady-state rheobase of 150 pA, which is `(V_th − V_rest) × g = 15 mV × 10 nS`. That comparison can look like a contradiction: a current above rheobase should eventually drive the membrane to threshold. The resolution is that the current is transient, not a sustained step.

Excitatory synaptic current decays with τ_exc = 5 ms. A single exponential event of 164 pA carries roughly `I₀ · τ ≈ 0.82 pC`, which on a 200 pF membrane is about 4.1 mV. Overlapping events can bring the peak to about 8.1 mV, which is the recorded 8.074 mV. A sustained 150 pA step would charge the membrane to threshold; a 5 ms transient of the same peak amplitude does not. This charge calculation is an order-of-magnitude consistency check for interpretation, not a new measurement, and it is labelled as such in the source report.

The same arithmetic applies downstream. Descending neurons received a maximum of 67.208 pA and reached −62.158 mV, 12.158 mV short. Ascending neurons, second-hop neurons, and motor neurons received 0 pA and stayed at the −65 mV rest, 15 mV short.

## 14.5 The second hop and the motor layer

Because no first-hop neuron spikes, the spike-driven synapse model delivers no second-hop current at all. The structural query finds 5,259 signed outgoing edges from the first hop, 3,865 distinct second-hop targets, and 3,576 non-stimulated second-hop targets. Zero of them receive current. Four second-hop targets are motor neurons, two of them JUMP and none LEFT or RIGHT, but they are silent for the same reason: no presynaptic spike.

The motor layer itself is not isolated. Seven hundred thirty-five of the 805 motor neurons have at least one signed incoming edge from somewhere in the graph, and the Phase 4G positive control shows that the motor tissue can be recruited when it is driven directly. But from the 232 stimulated sensory neurons there is no direct signed synapse to any motor neuron, and the only two-hop routes reach four motor neurons, none in the LEFT or RIGHT pools. The sensory-to-motor route is absent at one hop and vanishingly thin at two.

The absence is not caused by inhibition. The signed outgoing weight from the stimulated set to its first-hop targets contains 0.0 pA of inhibitory weight, so the first hop is under-driven, not suppressed. It is also not caused by the decoder: Phase 4G.5 condition C drove 64 VNC intrinsic neurons at 300 pA and produced 492 motor spikes across 82 motor neurons and JUMP in four of five windows, with the same decoder, pools, and adapter. Direct descending drive produced 18 motor spikes in three unassigned motor neurons, none in the decoded pools. The decoder is compatible with the recorded motor populations; it simply receives no motor spikes from the sensory route.

## 14.6 What is not the cause, and what remains ambiguous

Three candidates can be ruled out as the sole cause. The sensory layer drives its neurons and produces spikes. The decoder fires under direct motor drive. The motor membrane is not suppressed by inhibition. The break is at the first-hop current-to-spike conversion.

Two structural properties remain ambiguous and cannot be separated by this analysis. First, the verified-only sign policy assigns current to 683,100 of 1,535,710 edges, or 44.48%, and excludes 852,610 structurally present edges. Some excluded edge could be part of a route that the connectome contains but this model does not propagate. Second, the weight transform `5.0 · count^0.75` pA with a 300 pA cap is a declared calibration, not a measured conductance. A different transform would change the first-hop current without changing the graph. Neither property is a bug, and neither was tuned. They are modelling choices whose consequences were not anticipated when the choices were made.

The investigation tested the robustness of the shortfall against the stimulus pattern. Phase 4H.4's controls — temporal shuffle, feature-identity shuffle, random matched mapping, constant matched charge, 50 pA background plus 50 pA noise, and the no-event baseline — all produced zero non-stimulated spikes. The closest neuron under added background was still 7.35 mV short. The exact timing, the exact mapping, and the total charge therefore do not rescue the first hop under the declared model. That is a stronger statement than a single failed pattern, but it is still a statement about this model and these controls.

## 14.7 The convergence argument and its limits

The first-hop numbers come from Phase 4H.4, not from Pilot 1's own rows. The argument that they apply to Pilot 1 has four legs. The frozen inputs are byte-identical across the seven hashes recorded in both runs: graph, node table, synapse policy, neuron configuration, sensory mapping, motor decoder, and plasticity configuration. The production loop is the same. The structural query reproduces the first-hop target set and the absence of motor targets from the frozen graph. And Phase 7, which persisted the split directly, records 2,852 stimulated spikes, 0 non-stimulated spikes, and 0 motor spikes on the same design.

The limits are equally clear. Phase 7 is a same-design replication, not an identical replica: Pilot 1 derives condition-A network seeds as `SeedSequence([20261116, 1, seed, 2])`, so its network draws differ from Phase 7's single seed. The first-hop membrane values were measured in Phase 4H.4, whose stimulus was an archived event stream of 3,300.5 ms, not the live game. Pilot 1's longer episodes could in principle produce a different first-hop pattern, but the design, graph, mapping, weights, and decoder are the same, and no episode produced a single non-neutral action. The paper reports the convergence and does not claim a per-neuron measurement that was not persisted.

## 14.8 What would be required to move the bottleneck

The investigation does not propose a fix, and this paper does not test one. Several changes could in principle move the first hop: increasing the sensory current, lengthening the drive, adding background excitation, changing the weight transform, admitting predicted transmitters into the sign policy, selecting a different sensory population, or lowering the decoder threshold. Each would change the model or the protocol. The Phase 8 design explicitly forbids tuning the stimulus amplitude, decoder threshold, or mapping after seeing the floor, because doing so would break the preregistration and convert a negative result into a search for a passing configuration.

The correct status of these options is therefore hypothesis, not recommendation. The verified-only policy is the most structurally consequential: it removes 55.52% of edges, and the earlier FAFB replay, which treated unlabeled edges as excitatory, propagated widely. That contrast is consistent with the sign policy being a major contributor, but it confounds the sign policy with the graph, the neuron scale, and the recording duration, so it does not isolate the cause. Testing the sign policy directly would require a new authorized experiment with its own preregistration. It is outside this paper's scope, which is to document what was run.

## 14.9 Summary

The sensory-to-motor chain stops at the first hop. The 232 stimulated neurons spike; 662 signed edges reach 608 targets; 473 targets receive current; the strongest reaches −56.926 mV against a −50 mV threshold and does not spike; no second-hop current is delivered; no motor neuron receives current; the decoder sees no motor spikes and returns NO_ACTION. The decoder, the motor membrane, and inhibition are not the cause. The cause is the current-to-spike conversion at the first hop under this graph, this sign policy, and this weight calibration. The result is a property of one declared model configuration, not of the living fly, and it is the mechanistic explanation for the motor silence reported in Chapters 7 and 13.

# Chapter 15. D5/D6: Training and Artifact Certification

## 15.1 Authorisation for exactly six artifacts

The training stage of Phase 8 required its own owner decision. Decision record D5, dated 2026-11-22, authorises the production of exactly six trained artifacts: conditions F and F_beta at evaluation seeds 9001, 9002, and 9003, twenty episodes each, 120 episodes in total. It binds the request to REV4, the Pilot 2-C amendment, D3, D4, and the approved proposal by hashes recomputed from disk, and it re-derives the B3 entry digest exactly rather than copying it forward. Decision record D6 accompanies it as a non-inheritable boundary: it grants no additional capability, authorises no graph access, construction, or substitution, leaves the G3 memory deviation recorded rather than discharged, and confirms that the sixteen certified randomisation seeds are unchanged.

Both records are narrow by construction. The implementation modules authorise each artifact through D5, not through the global training gate, and the global gate still refuses further training. The following remain outside D5's scope and were not performed: conditions E or E-full, any campaign step, any Pilot 2-C episode, any floor replay, any randomized graph, and any change to a frozen parameter or statistical constant. The distinction matters because the existence of trained artifacts can easily be misread as progress toward the confirmatory campaign. It is not. Six artifacts at a 20-episode budget are a pilot-scale training exercise, and no contrast C1–C4 is estimated from them.

## 15.2 What was trained, and what was not

Condition F keeps the connectome and every synaptic weight exactly as in condition A and trains only the readout that maps the declared motor-population block to an action. The readout sees three features — the active fraction of the LEFT, RIGHT, and JUMP pools — and produces four logits, one for each of LEFT, RIGHT, JUMP, and NO_ACTION. It has no access to the seven sensory features, the game state, or earlier actions. Its weight matrix is therefore four by three, twelve feature weights, plus a four-element output bias.

The initialisation is asymmetric in a way that later matters. The bias is initialised to zero for every artifact. The feature weights are drawn from a normal distribution with standard deviation 0.01 using the artifact's init seed. During a training episode the controller samples an action from the categorical softmax policy; at the end of the episode a single REINFORCE update is applied. Evaluation episodes use the argmax action and a frozen readout. Training and evaluation seeds are disjoint: the training seeds are 1008, 1014, and 1005, while the evaluation seeds that identify the artifacts are 9001, 9002, and 9003.

Control F_beta is the bias-only readout. Its forward pass never reads the feature vector, its feature weights are a constant zero buffer excluded from the optimizer, and its only trainable parameters are the four output biases. The action distribution of F_beta is therefore provably independent of motor activity, which is exactly what makes it a state-independence control.

Nothing in this stage changes the neural substrate. The training signal updates the readout parameters, not synaptic weights; no three-factor rule, eligibility trace, or structural change is applied. The substrate weight fingerprint is expected to be identical before and after every episode, and it is.

## 15.3 The six-artifact grid and its execution

Table 17 reports the six artifacts and their certification digests. Each artifact has twenty episodes, twenty exact checkpoints, and one checkpoint after every completed episode.

**Table 17.** D5 trained artifacts. All six run on the frozen biological BANC t5 substrate with fixed synaptic weights. Evaluation seed identifies the artifact; training seed drives the episode seeds and the REINFORCE sampling; checkpoints are per-episode schema-2 checkpoints. The equivalence column records the one interrupted artifact for which an uninterrupted reference run was compared. Init seeds are 1350278753, 3449218186, and 3297997184 for F at 9001–9003, and 1849113230, 992595534, and 56964545 for F_beta at 9001–9003. Data source: `experiments/results/phase_8/training/`; full machine-readable table in `tables/T11_d5_training_artifacts.csv`.

| Condition | Eval seed | Train seed | Checkpoints | Episodes | Trainable = state digest | Parameters SHA-256 | Equivalence |
|---|---:|---:|---:|---:|---|---|---|
| F | 9001 | 1008 | 20 | 20 | `bd50cc73…9a8883` | `35918eb7…42efb6` | demonstrated |
| F | 9002 | 1014 | 20 | 20 | `e1c25034…dadce` | `a71b47a3…5d95` | not required |
| F | 9003 | 1005 | 20 | 20 | `2e188b78…d9961` | `3ad5e6be…d0e17` | not required |
| F_beta | 9001 | 1008 | 20 | 20 | `0975693e…1f76e` | `1030fe14…15a5` | not required |
| F_beta | 9002 | 1014 | 20 | 20 | `5f03c88b…f5b9` | `41abbe4d…e6a8` | not required |
| F_beta | 9003 | 1005 | 20 | 20 | `b157ae1e…a120` | `b1cd7e70…6e85` | not required |

Every checkpoint is schema 2 and carries the parameters, optimizer state and moments, the Python, NumPy, and PyTorch random-number states, and the sampler state. The environment is reconstructed from its B4 episode seed at the start of each episode and is recorded as such, so the episode does not depend on the order in which artifacts were run. All 120 checkpoints verify, and every ledger entry records `retained = true`.

Figure 32 shows the artifact-by-checkpoint matrix. Its purpose is not to display a performance trend but to make the completeness visible: six artifacts, twenty episodes each, every cell present and verified. The one corrected provenance record, F/9001, is marked in the caption rather than hidden.

![Figure 32. D5 artifact and checkpoint matrix. Six artifacts (F and F_beta at evaluation seeds 9001, 9002, 9003), twenty per-episode checkpoints each, 120 in total. Every checkpoint verifies and every ledger entry is retained. The F/9001 provenance record was corrected with the original bytes preserved beside it. Data source: the six `training_run.json` files under `experiments/results/phase_8/training/`.](figures/F26_d5_checkpoint_matrix.png)

The artifacts were written under `experiments/results/phase_8/training/` with the fixed 22-key manifest, `origin = "trained"`, `stage = "trained"`, and `evidence_kind = "experimental"`. The writer rejects synthetic fixtures as experimental evidence, and the real-training-root guard requires that if real storage exists, every artifact in it must carry trained origin, trained stage, and experimental provenance. These checks are implementation safeguards, not scientific results; they exist so that a fixture cannot be mistaken for a trained artifact later.

## 15.4 Interruption, recovery, and equivalence

The first execution attempt failed after F/9001 episode 1 with a logging `KeyError`. The failure is preserved in the append-only log. The checkpoint itself was valid, so the run resumed from it with an unchanged seed, budget, and substrate. No episode was restarted under a different seed.

An uninterrupted reference run was executed separately. `verify_equivalence` compared the resumed and uninterrupted runs over twenty episodes and twelve fields and found no differences; the exactness claim is `demonstrated`. The certification later re-checked this independently from the preserved reference checkpoints: final parameter bytes are identical (`35918eb7…`), trainable and full-state digests are identical (`bd50cc73…`), environment seeds are identical, and all twenty episode metrics are identical.

The interruption exposed a real implementation defect. On resume, the training loop rebuilt its B5 ledger only for the episodes it had run itself, so a resumed artifact's provenance would have listed nineteen of twenty checkpoints; the checkpoint written before the interruption was missing. The runner now rebuilds the ledger for all earlier episodes from the verified checkpoints and refuses to resume if any earlier checkpoint is missing. A focused regression test, `test_resumed_run_ledger_retains_every_checkpoint`, covers the case. Equivalence is demonstrated for this one interrupted artifact only; the other five were never interrupted and no equivalence claim is made for them.

## 15.5 Provenance correction for F/9001

Because the defect was found after F/9001 had already been written, its `training_run.json` contained the incomplete ledger. The correction was performed transparently rather than by rewriting history. The original file is preserved as `training_run.incomplete_provenance.json` with SHA-256 `a385aabd…`. The corrected `training_run.json` has SHA-256 `fd30434b…` and lists all twenty checkpoints and all twenty optimizer digests. A `provenance_correction` block records the kind of correction, the original and corrected file, the twenty re-verified checkpoints, and the note that no parameter, digest, episode metric, or checkpoint byte changed. A `provenance_corrected` event was appended to the log. The prior execution summary is preserved as `execution_summary.pre_provenance_correction.json` (`6fea7e1c…`), and the current summary (`24aca2e5…`) records the corrected hash.

This is the only historical record altered during the training stage, and it was altered by adding a corrected copy beside a preserved original, not by overwriting. The distinction is the same one applied to the Pilot 1 spike-total discrepancy in Chapter 13: the paper reports the corrected state and discloses the original, because a reader must be able to reconstruct both what happened and what was repaired.

## 15.6 Certification of the six artifacts

Certification is a technical check of artifact identity, schema, pairing, and recovery. It is not a test of learning, and a passing certification is not evidence that anything was learned.

All six artifacts reload and verify. Each has the 22-key manifest, `origin = "trained"`, `stage = "trained"`, output width `n_features = 3`, the correct model kind (`linear` for F, `bias_only` for F_beta), one B4 schedule of twenty environment seeds, budget 20, twenty recorded episodes, twenty ledger checkpoints with `integrity_verified = true` and `retained = true`, and twenty matching optimizer digests. The per-artifact parameter, manifest, and provenance hashes are recorded in the certification evidence and were recomputed from disk during certification.

The pairing is exact. F and F_beta share the training seed at each evaluation seed — 1008, 1014, and 1005 — and each has its own distinct init seed, so all six init seeds differ. Each pair has a distinct trainable digest and a distinct manifest file, and the B3 per-entry digests are distinct per evaluation seed while D5's global B3 digest is `bc231c79…92a75a143a1f980`. One detail is worth recording: F_beta's initial parameter digest is identical at all three seeds (`f94b54c9…f058e`) because its bias-only readout starts from a fixed zero vector and its forward pass ignores features, so its initialisation is seed-independent by construction. Its trained digests and files still differ by seed, because the reward stream differs. Artifact identity is therefore `(condition, evaluation seed)`, never a parameter value.

None of this certifies a contrast. The certification report states explicitly that it certifies nothing about C1–C4, H1–H3, paired dispersion, or `sigma_max`. U7 remains open and `n_seeds_selected` remains null.

## 15.7 The training outcome is behaviourally null

The substantive result of the stage is that all 120 episodes are behaviourally null. Every episode ended by collision, recorded zero motor-population spikes, and changed no synaptic weight; `weights_before` equals `weights_after` in every record. This is consistent with Pilot 1 and with the bottleneck analysis of Chapter 14, and it is the expected consequence of a silent motor channel rather than a surprise.

The readout comparison sharpens the point. At each evaluation seed, F and F_beta produced identical action counts, rewards, and decision counts in all twenty episodes, and their trained biases are bit-identical. F's feature weights retained their random initial values; F_beta's fixed feature weights are all zero. The most direct explanation is mechanical. The readout sees only the three motor active fractions. With zero motor spikes, that feature vector is identically zero at every decision, so the logits reduce to the bias, and F and F_beta implement the same policy whenever they are driven by the same sampling seed. Because the features are always zero, the gradient with respect to the feature weights is zero and those weights never move. The biases start at zero in both conditions and receive the same update, so they remain identical. The two conditions collapse onto the same bias-only policy.

This is an observation, not a certification failure, and no extra episode was run to diagnose it, because D5 authorises exactly 120 episodes. Its consequence for the next stage is direct: the six artifacts are not behaviourally distinguishable between F and F_beta, so any F/F_beta-dependent certified property has little discriminating power in a future Pilot 2-C. That is a statement about the current world and sensory pipeline, not a reason to alter a frozen parameter or threshold.

Figure 31 shows the reward trajectories. The curves for F and F_beta coincide at every episode and every seed, which is the visual form of the identity just described.

![Figure 31. D5 training reward trajectories for F and F_beta across the three evaluation seeds. Each panel is one evaluation seed; the F and F_beta curves coincide because the two readouts produced identical actions and rewards in all twenty paired episodes. The flat coincidence is a consequence of a zero motor feature vector, not evidence that the readouts learned the same policy. Data source: `experiments/results/phase_8/training/{F,F_beta}/seed_{9001,9002,9003}/training_run.json`.](figures/F25_d5_trajectories.png)

## 15.8 Preflight and the execution boundary

A final Pilot 2-C preflight ran once with the explicit D5 pairing and the real memory gate. The D3 stage authorisation was valid for the exact grid; the amendment was bound to REV4; and there were no authorisation blockers. The plan contained 54 entries — 45 neural (A, B, F, F_beta, and A_prime at three seeds and three episodes each) plus 9 floor — with no randomized graph and no contrast estimate. All six artifacts loaded with `require_trained = true`, `complete = true`, `missing = []`, and `synthetic_allowed = false`. Seven frozen inputs and the configuration hash were recomputed and recorded. Memory reported 7.118 GB available of 15.342 GB against the unchanged 4.0 GB gate, and the destination `experiments/results/phase_8/pilot2c` was free. D6 non-inheritance and G3 preservation were confirmed.

The preflight nevertheless returned `executable = false`. The only blocker was the conservative global-training-gate statement, not a missing prerequisite. The report is careful about what that means: even a future preflight returning `executable = true` would not authorise execution, because Pilot 2-C execution requires the owner's separate explicit authorisation. None was given at that point, so no Pilot 2-C episode and no floor replay was executed. Chapter 16 describes what happened when that separate authorisation was later granted.

## 15.9 What the stage established and what it did not

The stage established the training infrastructure. It built a plan constrained to the six authorized artifacts, a production runner with a real campaign factory and a real closed loop, a trained-artifact writer with a fixed manifest and provenance, and a recovery-capable driver that never overwrites an artifact and verifies completeness before writing. It produced 120 exact checkpoints, demonstrated equivalence for the one interrupted run, corrected a provenance defect without discarding the original bytes, certified all six artifacts against schema, pairing, and recovery criteria, and executed a complete preflight. The focused D5/D6 tests passed 71, and the complete Phase 8 suite passed 530.

It did not establish learning. The substrate weights never changed, the motor pools never spiked, and the readout never saw a nonzero feature vector. It did not establish a benefit of the trained readout over its bias-only control, because the two were identical in behaviour. It did not estimate a contrast, test a hypothesis, estimate dispersion, select a seed count, or move toward the N=16 campaign. It is not evidence about a fly, and the certification pass must not be described as biological learning.

The stage is nevertheless informative in a negative direction. It shows that the motor bottleneck propagates through training: a readout cannot learn a state-dependent policy from a feature vector that is always zero, however correctly the training loop is implemented. That is the same structural boundary identified in Chapters 13 and 14, now observed at the learning stage rather than only at the decoding stage.

## 15.10 Summary

D5 authorised exactly six F/F_beta artifacts, twenty episodes each, on the frozen biological substrate; D6 granted nothing and preserved the G3 deviation record. All 120 episodes executed and all 120 checkpoints verify. One interrupted run was resumed, shown equivalent to an uninterrupted reference, and repaired by a documented provenance correction that preserves the original bytes. Certification passed for all six artifacts on identity, schema, pairing, and recovery, and the final preflight passed every technical check while remaining non-executable solely because of the global training gate. The scientific outcome is a behaviourally null training set: zero motor spikes, zero synaptic weight change, and F/F_beta behavioural identity explained by a permanently zero motor feature vector. The next chapter reports the 54-entry Pilot 2-C execution and the narrow set of descriptive claims that execution could certify.

# Chapter 16. Pilot 2-C: Floor and Identity Certification

## 16.1 Authorisation and the resolved preflight blocker

Pilot 2-C is the amended Phase 8 pilot defined by decision record D3 and the Pilot 2-C amendment, SHA-256 `832ef485…67ad`, bound to REV4 (`e4aa9e0f…1547c`). It is not the confirmatory campaign and is not campaign evidence. Its declared purpose is `floor_and_identity_certification`, and its evidence kind is `pilot`. It was executed on 2026-11-23 under an explicit owner authorisation covering exactly the 54-entry grid and nothing else.

The authorisation chain was verified before execution. D1 was approved and bound to REV4; D2 remained valid for Pilot 1 only; D3 was applicable and matched the amendment on disk; D4 was applicable; D5 and D6 were valid and all six trained artifacts were bound; the stage authorisation reported `authorized = true` with no blockers. Three gates nevertheless remained closed and were reported as closed: the global training gate still refused further training, the campaign gate still refused, and no randomized graph was constructed, read or substituted. Pilot 2-C trains nothing, so the training gate is not a precondition for it; the campaign gate is untouched by it.

One preflight blocker had to be resolved legitimately before execution. A training-stage refusal had been folded into the pilot's stage blockers, which made the pilot appear non-executable for a reason that does not apply to a stage that trains nothing. The refusal was moved to `training_blockers`, where it is still reported, D5/D6 applicability was made the real precondition, and the runner now injects the six loaded artifacts. Regression tests cover both the reporting and the refusal when D5 is not applicable. The global training gate and the campaign gate were not altered. The full Phase 8 suite passed after the change, 531 tests. This resolution is what separates the end-of-D5 preflight, which returned `executable = false`, from the execution preflight, which returned `executable = true` with an empty blocker list.

The execution preflight recorded `uses_randomized_graph = false`, `constructs_randomized_graph = false`, and a free destination. The six artifacts loaded with `origins = ["trained"]`, `complete = true`, `missing = []`, `require_trained = true`, and `synthetic_allowed = false`. The run-time memory gate reported 6.115 GB available against the frozen 4.00 GB gate, at 60.1% used, and was not waived. No C, C′, or D arm was run, no training occurred, and no `n_seeds_selected` value was written.

## 16.2 The 54-entry grid and its execution

Table 18 reports the design. There are 45 neural episodes — five conditions at three evaluation seeds and three episodes each — and nine substrate-free floor replays paired to the same environment seeds. The environment seed is derived from master seed 20261116 and the `(seed, episode)` pair, so the floor replay faces the same game trajectory as the five neural arms at that pair.

**Table 18.** Pilot 2-C design grid. The design is the D3 scope: five neural arms and a substrate-free floor, three evaluation seeds, three episodes per seed, 54 entries in total. No randomized-graph arm and no campaign condition are present. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` and `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/pilot_plan.json`; full machine-readable table in `tables/T12_pilot2c_design.csv`.

| Arm | Substrate | Weights | Readout | Seeds | Episodes per seed | Purpose |
|---|---|---|---|---|---|---|
| A | biological BANC t5 | fixed | none | 3 | 3 | reference |
| B | biological BANC t5 | three-factor plasticity (η = 0.5) | none | 3 | 3 | plasticity |
| F | biological BANC t5 | fixed substrate | trained linear readout | 3 | 3 | readout |
| F_beta | biological BANC t5 | fixed substrate | trained bias-only readout | 3 | 3 | readout control |
| A_prime | biological BANC t5 | three-factor with η = 0 | none | 3 | 3 | identity control |
| floor | none | none | constant NO_ACTION | 3 | 3 | substrate-free floor |

The run is `pilot2c_d3_20261123`. Its first row was written at 03:37:44Z and its last at 04:35:36Z, with a total episode wall time of 3,458.8 s. The summary records `planned = 54`, `rows_executed = 54`, `rows_stored = 54`, `complete = true`, `evidence_kind = pilot`, `experimental_evidence = true`, and `merged_into_campaign = false`. No row carries an error status, no episode was retried, and no substitution occurred. The episode file contains 54 schema-valid rows and has SHA-256 `a14fd3bb…778991`; the manifest is `43710d38…020534`, the plan `63d51f61…ddcab`, and the summary `44dc5c05…520c5`.

## 16.3 The nine distinct game trajectories

The 54 rows reduce to nine distinct game trajectories, because every arm made the same decision at every step. Table 19 reports those nine `(seed, episode)` outcomes; each row applies identically to all six arms.

**Table 19.** Pilot 2-C per-episode outcomes. Steps equal the survival score, which is the number of game updates completed before collision. The nine rows are identical for all six arms because every arm took NO_ACTION on every decision, so the trajectory is determined by the environment seed alone. The floor rows' action digests differ from the neural rows and are not compared as identical. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`; full machine-readable table in `tables/T13_pilot2c_outcomes.csv`.

| Seed | Episode | Environment seed | Steps | Reward | Termination | Motor spikes | NO_ACTION fraction | Survival score |
|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 9001 | 0 | 563774599 | 323 | 5.22 | collision | 0 | 1.0 | 323 |
| 9001 | 1 | 2911696168 | 620 | 10.19 | collision | 0 | 1.0 | 620 |
| 9001 | 2 | 4240939637 | 323 | 4.22 | collision | 0 | 1.0 | 323 |
| 9002 | 0 | 2632356062 | 620 | 7.19 | collision | 0 | 1.0 | 620 |
| 9002 | 1 | 307060235 | 426 | 3.25 | collision | 0 | 1.0 | 426 |
| 9002 | 2 | 4241804999 | 620 | 8.19 | collision | 0 | 1.0 | 620 |
| 9003 | 0 | 2839813884 | 213 | 3.12 | collision | 0 | 1.0 | 213 |
| 9003 | 1 | 756850162 | 426 | 4.25 | collision | 0 | 1.0 | 426 |
| 9003 | 2 | 2981106662 | 213 | 2.12 | collision | 0 | 1.0 | 213 |

Each arm therefore has nine episodes, a mean survival of 420.44 updates, zero motor spikes, and no error rows. The per-seed means are 422.00 at 9001, 555.33 at 9002, and 284.00 at 9003, with total rewards of 19.63, 18.63, and 9.49. Every arm produced 3,784 decisions and every decision was NO_ACTION. Figure 34 shows the six arms overlaid; the bars coincide exactly.

This is a measured property of the grid, not an assumption. The amendment anticipated a motor-silent substrate, and P2C-5 exists to verify that the silence is recorded rather than inferred. It reproduces Pilot 1's result on the same nine environment seeds, which is expected because the same condition A substrate and decoder are used. It is not a new biological finding.

![Figure 34. Pilot 2-C survival by arm and cell. All six arms — A, B, F, F_beta, A_prime, and floor — produce the same survival score at each of the nine `(seed, episode)` cells, because every arm takes NO_ACTION on every decision. Mean survival is 420.44 updates. The coincidence is a property of a motor-silent grid; it is not evidence of equivalent learning or equivalent decoding. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`.](figures/F28_pilot2c_outcomes.png)

Figure 33 shows the design grid as executed: six arms by nine cells, all present.

![Figure 33. Pilot 2-C design grid as executed. Rows are arms, columns are the nine evaluation-seed by episode cells, and every cell is filled: 45 neural episodes plus 9 floor replays, 54 entries in total. All 54 executed and none was retried or substituted. No campaign contrast is estimated from this grid. Data source: `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl`.](figures/F27_pilot2c_design.png)

## 16.4 A′ identity

The A_prime control is a three-factor rule executed with η = 0. It is not a disabled pathway: the rule runs, eligibility slots are touched, and the applied update is exactly zero. The identity requirement is that A_prime reproduce A exactly, and it does, in all nine pairs.

The comparison covers nineteen declared fields per cell, denoted P1–P19: spike times, spike indices, spike digest, action and reward digest, the full record sequence, the survival and termination summary, action and decoder counts, reward components, neural and game timing, per-decision motor activity, structural, initial, learned-delta, and effective weight digests, maximum absolute delta, changed edges, clamp and saturation counts, the weight fingerprint, and resets. Tolerance is none; the requirement is exact equality.

All nine pairs match on all nineteen fields with zero mismatches. Every A_prime episode has η = 0, `changed_edges = 0`, and `max_abs_delta_pa = 0.0`; each records `rule_executed_zero_delta`, meaning the rule executed and applied nothing. Each episode has exactly one opening stepper reset and zero in-episode resets, matching A. The store-level reduced comparison also reports no mismatch. The hard stop that would refuse an A_prime episode on identity failure was never triggered, and B's status was not invalidated.

Figure 35 plots A against A_prime survival; every point lies on the identity line, but the figure is weaker than the underlying comparison. The identity claim is exact on the nineteen declared fields, not on every stored byte; for example, the floor rows' action digests are not compared as identical to the neural rows. The paper states the narrower claim.

![Figure 35. Pilot 2-C A_prime identity check. Each point compares A and A_prime survival at one `(seed, episode)` cell; all nine lie on the identity line. The exact claim is stronger than the plot: equality on all nineteen declared fields P1–P19, zero weight delta at η = 0, one opening reset, and no in-episode reset. Identity is exact on the declared fields, not on every stored byte. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` (P2C-2) and the Pilot 2-C episode file.](figures/F29_pilot2c_a_prime.png)

## 16.5 The eight certification claims

Table 20 reports the eight claims, recomputed from the stored rows and the manifest by the certification evaluator. All eight pass. The claims concern machinery: floor execution, identity, control constancy, readout wiring, motor accounting, plasticity attribution, provenance, and viability.

**Table 20.** Pilot 2-C certification claims P2C-1 through P2C-8. The evaluator recomputes each claim from the 54 stored rows and the manifest and writes nothing else. A PASS certifies the experiment's machinery, not biological learning, behavioural competence, or motor decoding. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json`, SHA-256 `bc5effaa…aa357`; full machine-readable table in `tables/T14_pilot2c_certification.csv`.

| Claim | Title | Result | Evidence |
|---|---|---|---|
| P2C-1 | floor execution | PASS | 9/9 substrate-free replays take NO_ACTION; own no spike or weight |
| P2C-2 | A-prime identity | PASS | A′ reproduces A on P1–P19 in 9/9 (η = 0, zero delta) |
| P2C-3 | F-beta constancy | PASS | 0 feature weights; bias-only readout; state-independent logits |
| P2C-4 | F behaviour | PASS | 12 non-zero feature weights; weights unchanged within episodes |
| P2C-5 | motor accounting | PASS | every neural episode records a motor block; 0 reported as 0 |
| P2C-6 | plasticity attribution | PASS | A′ delta 0; B 683,100 eligible, 1 edge changed in 4/9, max 0.03265 pA |
| P2C-7 | provenance | PASS | 7 input hashes + 3 config hashes + evidence kind on every row |
| P2C-8 | viability | PASS | 54 planned, 54 stored, 0 error rows, survival score recorded |

The claims are worth reading individually, because each one is narrower than its title suggests.

**P2C-1, floor execution.** The nine substrate-free replays are schema-valid, take NO_ACTION on every decision, read no spike, and own no weights. The floor is not a neural arm: `neural_substrate = "none"`, `is_neural_arm = false`, and `spikes_read = false`. It provides the behavioural baseline for the same nine environment seeds, and it matches the neural arms' trajectories exactly.

**P2C-2, A′ identity.** The nine pairs are exact on P1–P19, with no tolerance, η = 0, zero changed edges, zero clamp hits, and one opening reset per episode. In episodes where eligibility slots were touched, between 12 and 45 slots, nothing was applied because η = 0. The rule executed; the delta was zero.

**P2C-3, F_beta constancy.** F_beta has zero non-zero feature weights, its only trainable parameter is the bias, its logits for a zero feature vector and a saturated feature vector are identical, and it selects one action on every decision. This is provable state independence, not an empirical tendency.

**P2C-4, F behaviour.** F is state-dependent: its readout has twelve non-zero feature-weight entries. Its weights are frozen during evaluation, and its parameter and feature-weight digests are identical before and after every episode. The claim certifies that F is wired to the motor features and frozen, not that the features carried information. In this grid the feature vector was always zero, so F's logits reduced to its bias and its behaviour coincided with F_beta's.

**P2C-5, motor accounting.** Every neural episode records a per-decision motor block with the decision count, the decisions with a motor spike, the per-population spike counts for LEFT, RIGHT, and JUMP, and a 50 ms window. The recorded motor-spike count is consistent with the row. Each arm has 3,784 decisions and zero with a motor spike; zero is reported as zero rather than omitted.

**P2C-6, plasticity attribution.** A′ reports zero delta in all nine episodes. B reports `eligible_edges = 683,100` at η = 0.5 and records changed edges, maximum absolute delta, update reports, and hook calls per episode. Four of the nine B episodes applied updates — 42, 45, 24, and 12 applied updates — and each changed exactly one edge. The maximum absolute delta is 0.03265 pA, the maximum applied update is 0.01022 pA, and there are zero clamp hits and zero sign violations. These are weight-level changes only. They produced no motor spikes and no behavioural difference in this grid, which is exactly the distinction P2C-6 exists to make attributable: the plastic rule can be shown to execute and change a weight without any behavioural consequence.

**P2C-7, provenance.** Every row carries the seven frozen-input hashes, the three configuration hashes, the seed plan, the evidence kind, the stage purpose, and the D3 and amendment bindings. Every F and F_beta row additionally records its artifact's condition, evaluation seed, training seed, parameter digest, and parameter-file SHA-256. The seven frozen-input hashes are graph `6d47f259…e2192`, nodes `144a2eb0…53e5f`, neuron config `9b652bde…8b77`, synapse policy `88f64492…dc399e`, plasticity `616288a4…9e5f70`, sensory mapping `64c716a4…cdfc4ff`, and motor decoder `525f25e9…0d9fae`; the three configuration hashes are campaign `b9a2d3d5…477e19`, conditions `9a93f047…42f671`, and environment `b391ecf7…3281dc`.

**P2C-8, viability.** Fifty-four rows were planned, fifty-four stored, none missing, no error rows, and every row is schema-valid with a survival score. Nothing was skipped, retried, or substituted.

Figure 36 displays the eight results. The figure's value is completeness, not effect size; all eight claims are machinery claims, and none is a measurement of learning.

![Figure 36. Pilot 2-C certification claims P2C-1 through P2C-8. All eight claims pass when recomputed from the 54 stored rows and the manifest. The claims certify floor execution, A_prime identity, F_beta constancy, F wiring, motor accounting, plasticity attribution, provenance, and viability. A passing certification is not evidence of biological learning or behavioural competence. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json` (claims).](figures/F30_certification_matrix.png)

## 16.6 C1–C4 and H1–H3: what Pilot 2-C could not evaluate

Pilot 2-C estimates no contrast and tests no hypothesis. The amendment declares this explicitly, and the data cannot support anything else. The status of each campaign quantity is as follows.

C1 = F − A is not estimated. The rows show a zero descriptive difference, because both arms execute NO_ACTION on every decision, but a zero difference on a motor-silent substrate is degenerate. The amendment declares C1 estimable but degenerate; three pilot seeds with three episodes are not the campaign design, and no inferential statement is made.

C2 = B − A is a structural zero and is not estimated. On a substrate that produces no motor output, the B/A difference has no behavioural channel. The observed row equality is expected and carries no information about plasticity.

C3 = A − C is undefined and is not estimated. Condition C is excluded from Pilot 2-C, and no randomized graph was constructed, read, or substituted.

C4 = F − F_beta is not estimated. The rows show a zero descriptive difference because both trained readouts selected NO_ACTION on every decision: F's feature vector was always zero on the motor-silent substrate, so its logits reduced to its bias, and F_beta is bias-only by construction. The pilot cannot support a decoding claim, and none is made.

The hypotheses inherit those statuses. H1 (B − A ≠ 0) is unevaluable because C2 is a structural zero here. H2 (A − C > 0) is unevaluable because C3 is undefined and C is absent. H3 (F − A > 0) is unevaluable because C1 is degenerate on this substrate; the absence of a difference is not a refutation of H3 at the campaign operating point. H4 (E-matched > floor) is not evaluated because E is not in the grid. H5, the difference-in-differences contrast involving C and D, is not evaluated because neither is in the grid. H6 has no subject, because no non-NO_ACTION update exists in the grid and its descriptive antecedent never occurs.

The dispersion and design quantities are also unestimated. σ_max, the paired dispersion, and the upper confidence limit were not computed; U7 remains open; N remains the predeclared 16 with `design.n_seeds_selected` unset. Bootstrap, Holm, α, and the smallest effect of interest were not used here and remain frozen for the campaign.

Any reading of Pilot 2-C as evidence for or against H1–H3 would contradict both the amendment and the information content of the data. The correct statement is that the pilot could not put those hypotheses at risk.

## 16.7 Deviations, failures, and the one run-time anomaly

No stop condition was triggered. There was no identity mismatch, no memory-gate failure, no refusal during execution, and no schema error. No entry failed or went missing, and there were no retries or substitutions.

One pre-execution deviation was resolved and recorded: the mis-scoped training refusal described in Section 16.1. It was corrected in the stage module with two regression tests before execution. The earlier final-preflight files were preserved unmodified, and the execution preflight supersedes them with the resolution recorded.

One run-time anomaly was recorded with no effect on any row. The episode `F_beta:9001:0` took 1,653.9 s of wall time, 47.8% of the total run, while the next longest episode took 304.8 s. All fields of that episode are internally consistent — 323 steps, NO_ACTION, collision, zero motor spikes — and the report classifies the delay as a host-scheduling observation rather than a behavioural or simulation deviation. The paper repeats that classification and draws no scientific inference from it.

Historical evidence was untouched. No original artifact, row, manifest, record, report, or README was modified or deleted, and no parameter, threshold, learning rate, statistical constant, N, U7 value, or frozen protocol was changed.

## 16.8 What Pilot 2-C established and what it did not

Pilot 2-C established that the authorised 54-entry grid executes exactly as declared, that the machinery the campaign depends on behaves as specified, and that the motor silence is measured rather than assumed. The floor takes NO_ACTION and owns no spike or weight; A′ at η = 0 is an exact in-process identity on the declared fields; F_beta is a provable bias-only readout; F is state-dependent and frozen during evaluation; plasticity is attributable to its declared rule, with A′ exactly zero and B reporting eligible edges, changed edges, and a maximum applied update; provenance is complete on every row; and every arm completes its planned episodes.

It did not establish a biological claim, a decoding claim, a contrast, a hypothesis conclusion, or a sample-size decision. Nothing in the pilot shows that the connectome learned, adapted, or is capable of behaviour. The readouts' biases chose NO_ACTION, and the substrate produced no motor spikes. C1–C4 are not estimated, C2 is a structural zero, and C3 is undefined. F and F_beta are behaviourally indistinguishable in this grid, so C4 is not estimated and H3 is neither supported nor refuted.

The defining fact is that every arm, including the floor, produced the same game trajectory for a given environment seed. The zero between-arm differences are a property of a motor-silent grid, not a result about learning, decoding, or connectivity. Pilot 2-C certifies a floor and an identity. It is infrastructure evidence that the experiment which will test H1–H3 can be built, paired, stored, and audited as declared. It is not behavioural evidence about a fly, and the eight PASS results must never be described as proof of biological learning or behavioural competence.

## 16.9 Summary

Pilot 2-C executed all 54 authorised entries on 2026-11-23: 45 neural episodes across five arms and 9 substrate-free floor replays, in 3,458.8 s of episode wall time. Every arm produced 3,784 NO_ACTION decisions, zero motor spikes, and collision termination; mean survival was 420.44 updates. A_prime reproduced A exactly on nineteen declared fields with η = 0 and zero weight delta. All eight certification claims passed, including the attribution result that B's plasticity changed one edge in four of nine episodes with a maximum delta of 0.03265 pA and no behavioural effect. No contrast C1–C4 was estimated, no hypothesis H1–H6 was evaluated, σ_max and dispersion were not computed, U7 remains open, and N remains the predeclared 16. The pilot certifies machinery and a floor; it does not certify learning.

# Chapter 17. Consolidated Results

## 17.1 How the consolidated results are stated

This chapter collects the recorded outcomes of the programme and answers the central and secondary questions at the level of evidence each phase actually supplies. It introduces no new measurement. Every value is a summary of a result reported in an earlier chapter, and every status is the status recorded by the phase that produced it.

Three distinctions govern the consolidation. First, an implementation test is not experimental evidence; a software check that a decoder maps a synthetic pattern to LEFT says nothing about a fly. Second, a pilot is not a campaign; it can certify machinery and expose a floor, but it cannot estimate a contrast. Third, structural connectivity is not physiological connectivity; a path in the connectome is a hypothesis about information flow, not a measurement of it. The consolidated table therefore mixes evidence kinds deliberately, with the kind stated for each row, rather than ranking all results on a single scale.

## 17.2 The central question

The central question was whether a connectome-derived fruit-fly neural network, implemented as a spiking simulation with learning mechanisms, can transform visual game information into functional motor commands in a controlled game environment.

The recorded answer is a qualified negative at the current operating point. The pipeline exists end to end and runs reproducibly: perception, sensory mapping, simulation, decoding, a closed-loop game bridge, plasticity, training, and a pre-registered evaluation design. It does not produce functional game-playing. In the Phase 7 closed loop the network emitted 2,852 spikes, all from directly stimulated sensory neurons, and zero motor-population spikes; the decoder returned NO_ACTION on all 213 decisions. Pilot 1 reproduced the outcome over nine episodes — 3,784 decisions, 126,135 neural steps, 73,880 spikes, zero motor spikes — and Pilot 2-C reproduced it over another 54 entries, with 3,784 NO_ACTION decisions per arm. The D5 training set added 120 episodes with the same result. No run in the programme produced a single motor-population spike in a closed loop.

The answer is qualified rather than absolute for three reasons. The failure is localised: Chapter 14 shows that first-hop current reaches 473 non-stimulated targets but peaks at −56.926 mV against a −50 mV threshold, a 6.926 mV shortfall, so the chain fails at the first post-sensory stage rather than everywhere at once. The failure is operating-point-specific: it is a property of this sensory convention, this LIF parameterisation, and this verified-only sign policy, not a proof that the connectome cannot support behaviour. And the positive control shows the decoder itself can act: when motor populations are driven directly in the Phase 4G condition C, the decoder returns JUMP four times from 492 motor spikes across 82 active neurons. The negative result is therefore about the drive reaching the motor pools, not about the decoder's ability to express an action.

A fifth observation belongs with the answer. The Phase 6 analysis found no confirmatory gain in cue-to-action information from plasticity: the mean paired difference on complete wiring was −0.0863 bits, with exact two-sided sign-flip p = 0.125 and Holm-adjusted p = 0.25. Phase 5F had found a large improvement in designated-response success on its synthetic task, 0.795 to 0.945, but that improvement was not accompanied by a supported increase in the information the chosen action carried about the cue. The programme therefore did not demonstrate the kind of learning that would explain a behavioural improvement by a representational gain.

## 17.3 The nine secondary questions

The nine secondary questions can now be answered individually, each with its scope and its evidence kind.

**Q1. Can the connectome be converted into a computational network?** Yes, computationally. The FAFB v783 graph was built at a five-synapse threshold with 139,255 neurons, 3,732,460 directed pairs, and 50,666,648 summed synapses, and the BANC v888 brain–ventral-nerve-cord graph supplies the motor stage with 172,433 endpoints and 1,535,710 edges at the same threshold, including 805 annotated motor neurons. The conversion is a declared computational construction, not a claim that the simulation reproduces the fly. The BANC graph is the one that matters for motor output, because FAFB contains no limb motor neurons.

**Q2. Can visual information be turned into sensory stimulation?** Yes, up to the declared mapping. A YOLO11n detector produces game features, and seven features are mapped onto identified BANC sensory populations of 232 neurons in total. The detector's published precision 0.937310, recall 0.810829, mAP50 0.897776, and mAP50-95 0.687726 are provenance from its training environment, not re-measured here. The seven assignments are computational hypotheses; the mapping omits player pose and coins. The commercial Subway Surfers game was never instrumented. The positive statement is that detected features can be converted into timed current injections on declared populations; the negative statement is that this conversion has not been shown to be the fly's.

**Q3. Does activity propagate?** Partly. Stimulation produces spikes in stimulated sensory neurons and first-hop synaptic current in many targets. In the Phase 4H.4 round trip, 232 neurons were stimulated, 171 were active, and 3,562 spikes were recorded, all in stimulated neurons; 473 of 607 non-stimulated first-hop targets received current. In the FAFB replay, 72 of 138 stimulated neurons were active and stimulated spikes dominated the record at a share of 0.999763. Propagation therefore exists at the first hop but does not reach the second hop in the BANC configuration: zero of 3,576 second-hop non-stimulated targets generated current, and zero of 805 motor neurons spiked.

**Q4. Is there motor-population activity?** No, in every executed closed-loop and pilot configuration. Phase 7 recorded zero motor spikes in 213 decisions; Pilot 1 recorded zero in 3,784; Pilot 2-C recorded zero in 3,784 decisions per arm across six arms; D5 recorded zero in 120 training episodes. The zero is measured, not inferred from the absence of an action, and the decoder's positive control shows the pools can produce an action when they are driven directly. The motor populations are therefore silent under the tested drive, not incapable of being read.

**Q5. Does the fixed decoder turn neural activity into game actions?** In synthetic tests, yes: the decoder implements a deterministic 50 ms window rule with a 0.20 activation threshold, a five-spike and three-neuron gate, exact tie ordering, and NO_ACTION otherwise. It returned JUMP from condition C's directly driven pools and LEFT from a uniform synthetic pattern. In the closed loop, no: every decision was NO_ACTION because no motor pool met the gate. The correct formulation is that the decoder maps motor activity to actions as specified, and the motor activity required by its gate did not occur.

**Q6. Does dopamine-inspired plasticity increase cue-to-action information?** No supported increase. The confirmatory Phase 6 family of two paired contrasts was not rejected: complete wiring −0.0863 bits (95% interval −0.1751 to 0.0052; exact p = 0.125; Holm p = 0.25) and random wiring −0.0025 bits (p = 1.000; Holm p = 1.000). The point estimate on complete wiring is negative, with six of ten seed differences negative. The Phase 5F success increase remains a real result on its synthetic task, but it is not explained by an information gain at the 4 × 4 resolution used. The plasticity experiments also showed weight-level changes without behaviour in Pilot 2-C's B arm: one edge changed in four of nine episodes, maximum delta 0.03265 pA, zero motor spikes.

**Q7. Does a trainable readout produce state-dependent decisions?** Not demonstrated. The readout is state-dependent by construction: its twelve feature-weight entries are non-zero and its logits depend on the three motor active fractions. But in all 120 D5 training episodes and all nine F episodes of Pilot 2-C, the motor feature vector was identically zero, so the logits reduced to the bias and F behaved exactly like its bias-only control. F and F_beta produced identical actions, rewards, and decision counts, with bit-identical trained biases. The wiring is certified; the state dependence was never exercised.

**Q8. How does the programme compare with alternative architectures?** Only within narrow, non-matched comparisons. On the Phase 5F synthetic task a conventional perceptron reached success 1.0, above the plastic spiking network's 0.945 and far above fixed wiring's 0.795. That perceptron is privileged and is not a matched control. On random versus complete wiring, the random graph had lower success, 0.1025 fixed and 0.1125 plastic, but higher measured cue-to-action mutual information, 1.3547 and 1.3522 bits against 0.6126 and 0.5262. The dissociation warns that measured information and task performance are not monotonically related, and no causal claim is made about why the random graph differs. No controlled architecture comparison was run at campaign scale, so the programme does not answer this question comparatively.

**Q9. What are the limitations of structural connectome models?** The programme exposes several. A structural graph does not supply physiological signs: on BANC t5 only 44.48% of edges, 683,100 of 1,535,710, receive a verified sign under the declared policy, and the rest are excluded from simulation. Annotation coverage bounds what can be identified: cell type is available for 68.2045% of endpoints and body-part effector for 0.5968%, though super-class coverage is 88.069%. A graph can contain a path that the model cannot drive above threshold, as the 6.926 mV shortfall shows. And a connectome constrains which neurons exist, not what they encode; the seven-feature sensory mapping is a hypothesis laid on top of the graph. These are limitations of the modelling enterprise, not defects that a larger simulation would automatically remove.

## 17.4 The cross-phase evidence ladder

Figure 37 places each phase on a qualitative ladder of the strongest evidence it supplies. The ladder is not a performance scale. It records what kind of claim a phase can support: software behaviour, benchmark throughput, synthetic-task result, perception result, experimental neural measurement, pilot, training, or archived analysis.

![Figure 37. Consolidated cross-phase evidence ladder. Each phase is placed at the strongest evidence kind it supplies: Phase 2 software, Phase 2.5 benchmark, Phase 3A/3C synthetic, Phase 3B perception, Phase 4D–4G experimental, Phase 5 synthetic, Phase 6 archived analysis, Phase 7 experimental, Pilot 1 pilot, D5 training, Pilot 2-C pilot. Red marks the late pilots and training, whose outcomes were null. The ladder is a qualitative classification, not a ranking of scientific importance. Data source: phase reports and execution records summarised in this chapter and Chapter 9.](figures/F31_evidence_ladder.png)

Two readings of the ladder matter. First, the programme's strongest neural evidence is experimental but narrow: the Phase 4 round trips measure spikes and currents on a declared substrate, yet they do not establish a biological motor code. Second, the late stages are classified as pilot and training precisely because their outcomes were null and their sample sizes were not inferential. The ladder makes visible that the programme accumulated a great deal of software and benchmark evidence and comparatively little behavioural evidence, which is the honest shape of the result.

## 17.5 Status of the pre-registered contrasts and hypotheses

Table 21 records the status of every pre-registered contrast and hypothesis, together with the Phase 6 confirmatory family.

**Table 21.** Status of the Phase 8 contrasts and hypotheses and the Phase 6 confirmatory contrast. "Not estimated" and "unevaluable" are distinct: a contrast can be unestimated because the campaign was not run, and a hypothesis can be unevaluable because its contrast is structurally zero or undefined in the executed grid. Data source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json`, `reports/PHASE_8_PILOT2C_EXECUTION_REPORT.md`, and `experiments/results/phase_6/information_analysis.json`; full machine-readable table in `tables/T16_hypothesis_status.csv`.

| ID | Statement | Status | Evidence |
|---|---|---|---|
| C1 = F − A | trainable readout on the biological substrate | not estimated | Pilot 2-C shows a descriptive zero difference on a motor-silent substrate; campaign not run |
| C2 = B − A | three-factor plasticity on the biological substrate | not estimated (structural zero) | no motor output channel in the pilot; H1 unevaluable |
| C3 = A − C | biological vs degree/sign-matched random graph | undefined | condition C excluded from Pilot 2-C; no randomized graph used |
| C4 = F − F_beta | readout uses motor information | not estimated | F and F_beta both choose NO_ACTION in every pilot episode |
| H1 | plasticity changes survival (B − A ≠ 0) | unevaluable | C2 structural zero |
| H2 | biological graph outperforms random (A − C > 0) | unevaluable | C3 undefined |
| H3 | readout beats fixed decoder (F − A > 0) | unevaluable | C1 degenerate; absence not refutation |
| H4 | E-matched above floor | not evaluated | E absent from Pilot 2-C |
| H5 | (B − A) − (D − C) ≈ 0 | not evaluated | C and D absent |
| H6 | motor activity precedes non-NO_ACTION | no subject | no non-NO_ACTION update exists |
| Phase 6 confirmatory | plasticity increases cue-to-action MI | not supported | mean −0.0863 bits; exact sign-flip p = 0.125; Holm 0.25 |

The table contains no rejected hypothesis and no estimated campaign contrast. That is not a gap in reporting; it is the state of the evidence. The confirmatory campaign with N = 16 was not executed, and no value of `n_seeds_selected` was written. The pre-registered family of four contrasts, the Holm correction at m = 4, the smallest effect of interest of 100 updates, the exact sign-flip test, and the seed-count rule all remain frozen for a future campaign. Reporting them as though they had been evaluated would be a fabrication of inference.

## 17.6 What the negative results jointly imply

Three negative results dominate the consolidation, and they are consistent with one another.

The first is the Phase 6 information result. Plasticity improved designated-response success on a synthetic task but did not increase cue-to-action information at the resolution tested. That result rules out one explanation of the Phase 5F success — that the network came to represent the cue more informatively — and leaves a conditioned-response account in which the designated population simply becomes more likely to spike. The account was proposed before Phase 6 ran and was not refuted.

The second is the motor silence. It appears in Phase 7, Pilot 1, Pilot 2-C, and D5, across 213, 3,784, 3,784-per-arm, and 120 episodes respectively. Chapter 14 localises the failure to the first post-sensory hop: 473 targets receive current, the peak somatic depolarisation is −56.926 mV, the threshold is −50 mV, and the shortfall is 6.926 mV. The mechanism is a transient synaptic current too small and too brief to charge the membrane to threshold, compounded by a sign policy that leaves 55.52% of BANC t5 edges unsimulated. This is a quantitative explanation of a measured null, not a speculation.

The third is the null training outcome. D5 produced 120 exact checkpoints and a fully certified set of artifacts, but the readout never saw a nonzero feature vector, so F and F_beta collapsed onto the same bias-only policy. This is the motor silence propagating into learning: a state-dependent readout cannot learn state dependence from a state vector that is always zero.

Together the three results describe a single boundary. The programme built a functioning perception-to-simulation chain, but the current injected by the mapped sensory populations does not drive the first post-sensory stage above threshold, so the motor pools stay silent; with silent motor pools, the behavioural readouts have nothing to read; and with nothing to read, neither plasticity nor readout training can produce a behavioural effect. Each phase's null is explained by the same upstream shortfall.

## 17.7 What is solid and what remains provisional

The solid results are software and measurement results. The graph constructions, the simulation engine, the decoder rule, the sensory mapping as implemented, the artifact schemas, the checkpoint and provenance machinery, the information estimators, and the statistical design all behaved as specified and are reproducible. The measurements of spike counts, currents, membrane potentials, weight changes, action counts, and survival are recorded values with file-level provenance.

The provisional results are the interpretive ones. The seven sensory assignments are hypotheses. The sign policy is a declared approximation. The calibrated encoder's three-level distance code rests on nine observations and three clusters. The LIF parameterisation is a modelling choice. The comparison with a perceptron is not matched. The random-graph mutual-information difference is descriptive and unexplained. None of these is presented as a biological finding.

The unavailable results are equally clear. There is no estimate of C1–C4, no test of H1–H3, no evaluation of H4–H6, no σ_max, no paired dispersion, no N selection, and no confirmatory campaign. The paper reports them as unavailable rather than substituting a proxy.

## 17.8 Summary

The programme answered its central question with a qualified negative. The connectome can be built into a simulation, visual features can be mapped to sensory current, and activity propagates at the first hop, but the current does not reach the motor pools: zero motor spikes in every closed-loop and pilot configuration, and NO_ACTION on every decision. Phase 6 found no supported gain in cue-to-action information from plasticity, and the D5 readouts could not learn from a permanently zero motor feature vector. The pre-registered contrasts and hypotheses remain unestimated or unevaluable, the N = 16 campaign was not run, and no result in the programme is evidence of biological learning or functional game-playing. The consolidated picture is a working pipeline stopped at a measured, localised, and quantitative motor bottleneck.

# Chapter 18. Discussion

## 18.1 The result in one paragraph

FLY-SURFER built a complete computational chain from a whole-brain connectome to a controlled game environment: a FlyWire FAFB brain graph, a BANC brain–ventral-nerve-cord graph with annotated motor neurons, a sparse LIF simulation, a detector-driven sensory mapping, a threshold motor decoder, reward-modulated plasticity, a trainable readout, a closed-loop bridge, a pre-registered Phase 8 design, and four executed pilot or training stages. The chain runs and is reproducible, but it does not produce behaviour. The network spikes when stimulated, the first-hop targets receive current, and the decoder can act when motor pools are driven directly; yet no motor pool crosses threshold under the tested drive, so every closed-loop decision is NO_ACTION and every episode ends by collision. The programme's scientific contribution is therefore a bounded negative result with a mechanistic explanation, not a demonstration of connectome-based game-playing.

## 18.2 Why the motor silence is the central finding

It would be easy to read the zero motor spikes as a decoder problem. That reading is excluded by the positive control. When Phase 4G condition C drove the motor populations directly, the decoder recorded 492 motor spikes across 82 active neurons and returned JUMP four times. Synthetic decoder tests likewise map declared activation patterns to LEFT, RIGHT, and JUMP deterministically, including an exact tie case resolved by the declared order. The decoder is capable of emitting an action. What it did not receive was a motor population that met its five-spike, three-neuron, 0.20-active-fraction gate.

The bottleneck analysis locates the failure one stage earlier. Of 662 signed first-hop edges from the stimulated sensory neurons, 473 targets received current, but the peak somatic depolarisation was −56.926 mV against a −50 mV threshold. The shortfall is 6.926 mV. No second-hop current was generated, and zero of 805 motor neurons spiked. The explanation is quantitative rather than vague: the synaptic current is transient, with a 5 ms excitatory decay, and the charge delivered per first-hop event is on the order of 0.82 pC, sufficient for roughly 4.1 mV on the 200 pF membrane; overlapping events might accumulate about 8.1 mV, which is still below the 6.926 mV shortfall when starting from rest and is further reduced by inhibition and by the fraction of unsigned edges that carry no modelled current. A static current above the 150 pA rheobase is not the relevant quantity, because the current is not static.

Two structural facts compound the shortfall. First, only 44.48% of BANC t5 edges, 683,100 of 1,535,710, receive a verified sign under the declared policy; the remaining 55.52% are excluded from simulation. A connectome path that exists anatomically may therefore carry no modelled current at all. Second, the sensory mapping drives 232 neurons across seven features, which is a convention rather than a receptive-field map. The silence is thus a joint property of the sign policy, the weight transform, the LIF parameters, and the sensory convention. The paper does not claim to know which single choice is responsible; Chapter 14 states that identifying it requires an authorised sensitivity study, not a post hoc adjustment.

## 18.3 Success without information: reading Phase 5F and Phase 6 together

Phase 5F produced a clear result on its synthetic 36-node task: plastic complete wiring raised designated-response success from 0.795 to 0.945, while fixed random wiring stayed near 0.10 and the fixed complete condition stayed at 0.795. Read alone, that looks like learning. Phase 6 tested the representational interpretation and did not support it. The paired difference in cue-to-action mutual information at checkpoint 160 was −0.0863 bits on complete wiring, with an exact sign-flip p of 0.125 and a Holm-adjusted p of 0.25; six of ten seeds were negative. The random-wiring contrast was essentially zero.

The dissociation matters because a network can increase a designated response by becoming more excitable, by shifting a threshold, or by repeating a stereotyped action without representing the cue more informatively. Phase 5F measured whether the designated population spiked before a deadline, not whether the chosen action carried more information about the cue. Phase 6 measured the latter at a declared resolution: a 4 × 4 cue-by-action table over 40 held-out episodes per arm, with the analytic bias floor reported rather than removed. At that resolution, the success gain was not accompanied by a supported information gain.

The claim must be stated at exactly that strength. The analysis does not show that no information gain exists at any resolution, in any variable, or under any estimator. It shows that no gain was detected at the pre-declared resolution with the declared estimator and sample size. The direction of the point estimate is negative, which is consistent with a conditioned-response account in which plasticity makes the designated population more likely to spike; it is not proof of that account. The account was proposed before Phase 6 ran, and Phase 6 did not refute it.

## 18.4 What a structural connectome can and cannot be

A connectome is a constraint on which neurons can talk to which, at what approximate multiplicity. It is not a controller. It does not specify conductance, reversal potential, short-term plasticity, neuromodulatory state, or the sign of a synapse in a given behavioural context. FLY-SURFER made a series of declared choices to turn the constraint into a dynamical model: predicted transmitter signs with modulators excluded, a calibrated weight transform, a single uniform LIF parameter set, exponential synapses with fixed time constants and a 1 ms delay, and a threshold decoder over annotation-defined pools. Each choice is defensible individually; together they define a specific operating point.

The negative result is a statement about that operating point. It is not a statement that the biological network cannot drive a leg, and it is not a statement that the connectome lacks the relevant paths. Indeed, 735 of 805 motor neurons have some signed input, and four motor neurons are reachable within two hops, two of them in the JUMP pool. The graph contains routes; the model does not drive them above threshold. The distinction between structural reachability and physiological drive is the central methodological lesson of the project, and the paper preserves it in every result.

This distinction also explains why the random graph carries more measured cue-to-action mutual information than the complete graph in the Phase 5F task, 1.3547 bits against 0.6126 bits, while performing much worse behaviourally. Measured information is a property of the joint distribution over the declared variables in a particular task, not a virtue. A graph can carry more information about a cue in a table and still fail to produce the designated response. The analysis makes no causal claim about the difference and does not treat higher random-wiring information as evidence of a better substrate.

## 18.5 The readout null and the logic of controls

The D5 training stage is the cleanest illustration of why controls matter. Condition F has a state-dependent readout with twelve non-zero feature weights; condition F_beta has a bias-only readout whose feature weights are fixed at zero. Certification confirmed that F is wired to the motor features and frozen during evaluation, and that F_beta is provably state-independent. Yet the two produced identical actions, rewards, and decision counts in all 120 paired episodes, with bit-identical trained biases.

The reason is visible once the feature vector is inspected. The readout sees three motor active fractions. On a motor-silent substrate those fractions are always zero, so the feature vector is identically zero, the logits reduce to the bias, and the gradient with respect to the feature weights is zero. F never moves its feature weights and behaves as a bias-only policy; F_beta is a bias-only policy by construction. The control did not fail. It did exactly what a control should do: it revealed that the treatment had no channel through which to act.

This is a general lesson for connectome-learning claims. A certification that a model is state-dependent, or that its weights are trainable, is a statement about wiring, not about use. Without a non-degenerate feature vector, the treatment and its control are behaviourally identical, and any claim of a readout benefit would be unsupported. The paper reports the F/F_beta identity as an observation and explicitly declines to describe the certification pass as evidence of learning.

## 18.6 Pre-registration, provenance, and the discipline of negative results

The programme's evidential discipline is part of its contribution. Phase 8 was governed by a frozen protocol, REV4, with a hash recorded on disk, and by a chain of owner decisions D1–D6, each binding specific stages and refusing capabilities outside its scope. The confirmatory campaign was never run. Pilots were authorised as pilots, with `evidence_kind = pilot` and `merged_into_campaign = false`. The Phase 6 analysis declared its two confirmatory contrasts before estimating them and labelled everything else exploratory. The Phase 8 design fixed its contrasts, hypotheses, Holm family, smallest effect of interest, seed-count rule, and exact test before any campaign data existed.

That discipline produced uncomfortable but useful records. Pilot 1's execution report contains a prose spike total of 72,880 while its nine stored rows sum to 73,880; the paper discloses the 1,000-spike transcription error, uses the row sum, and preserves the original report unchanged. The F/9001 training artifact required a provenance correction after a resume-ledger defect; the original bytes are preserved beside the corrected record, and no parameter or metric changed. The Pilot 2-C floor rows have different action digests from the neural rows while their outcomes are identical; the paper says the outcomes are identical and does not claim identical digests. The Phase 7 demonstration contains an unexplained equality between a neural run and a random-seed run with very different action streams; the paper flags it as a documentation issue and does not use it as evidence.

These are not incidental embarrassments to be smoothed away. They are the observable cost of doing provenance seriously, and they let a reader distinguish a data discrepancy from a scientific one. The alternative — silently correcting the report, overwriting the original artifact, or reporting the floor digest equality as identity — would have produced a cleaner document and a less trustworthy record.

## 18.7 Relation to alternative approaches

The programme's choice of a point-neuron LIF model over a detailed compartmental reconstruction was a deliberate trade. Detailed models can represent cell-type-specific conductances, morphology, and dendritic processing, but they are expensive and require physiological parameters that the connectome does not supply. A point-neuron model can run inside a closed game loop on a single machine and can be audited end to end, but it cannot capture the mechanisms that might make a first-hop input effective. The 6.926 mV shortfall is plausibly an artefact of that simplification; it is also a real property of the model, and the paper reports it as such rather than adjusting parameters until a spike appears.

A second alternative is to train an end-to-end agent on the game and treat the connectome as a prior or a regulariser. That approach could produce game-playing, but it would answer a different question: whether a trained controller can use connectome structure, not whether a structural connectome driven by a declared sensory convention can produce motor commands. FLY-SURFER's conventional perceptron comparison, which reached success 1.0 on the synthetic task, illustrates the gap. The perceptron is privileged and not a matched control; its success shows that the task is learnable, not that the connectome is unnecessary.

A third alternative is to compare biological and null topologies at campaign scale. The programme built the machinery for that comparison, including sixteen certified randomisation seeds, degree- and sign-matched exchange, and a pre-registered C3 contrast, but the G3 memory deviation left the random graphs unaccepted and the campaign was never authorised. The comparison therefore remains unperformed. The paper reports the certified graph construction as infrastructure, not as a result.

## 18.8 Implications for the central question

The central question receives a qualified negative. A connectome-derived network can be built, stimulated, simulated, decoded, and closed into a game loop; under the tested operating point it does not transform visual game information into functional motor commands. The qualification is mechanistic and local: the failure is a first-hop drive shortfall of 6.926 mV, compounded by an unsigned-edge fraction of 55.52% and a sensory convention that is not a receptive-field map.

This answer is more useful than a bare failure because it identifies what a next study would have to change and what it would have to measure. It also sets a bar for future positive claims. A demonstration that a connectome model plays the game would need to show motor-population spikes, a non-degenerate readout feature vector, a behavioural contrast against a matched control, and a pre-registered analysis that survives its own multiple-comparison correction. FLY-SURFER did not meet that bar, and it says so.

## 18.9 Summary

The discussion reduces to three points. The motor silence is a drive failure at the first post-sensory hop, not a decoder failure, and it is quantitatively explained. The Phase 5F success gain was not accompanied by a supported cue-to-action information gain at the declared resolution, so a representational interpretation is not warranted. And the training readouts collapsed onto a bias-only policy because the motor feature vector was always zero, which shows why wiring certification is not evidence of use. A structural connectome constrains possible paths; turning it into a controller requires physiological choices that this programme made explicitly and that its negative result now helps to locate.

# Chapter 19. Limitations and Threats to Validity

## 19.1 What this chapter covers

The limitations of FLY-SURFER are not a single list appended to the results. They operate at different levels: some concern whether the model measures the construct it claims to measure, some concern whether the comparisons are internally valid, some concern whether the findings generalise, some concern the statistical design, and some concern the documentation itself. This chapter separates those levels, then reports the recorded deviations and the consolidated limitations register. It does not propose fixes; the future questions in Chapter 21 state what would be required to address each limitation, and the execution boundaries of the programme forbid changing a frozen parameter or protocol in response to a result.

## 19.2 Construct validity: what the model measures

The most fundamental limitation is that structural connectivity is not physiological connectivity. An edge in FAFB or BANC reports synapses between identified neurons; it does not report conductance, reversal potential, short-term dynamics, or whether the synapse is excitatory or inhibitory in a particular behavioural state. Every propagation result in this paper is therefore a statement about a graph plus a declared model, not a measurement of information flow in a fly.

The sign policy makes the gap concrete. On BANC t5, only 44.48% of edges, 683,100 of 1,535,710, receive a verified sign under the declared policy; the remaining 55.52% are excluded from simulation. A structurally present path can therefore carry no modelled current, and the model's effective graph is sparser than the anatomical graph. The exclusion is conservative and declared, but it means that the measured first-hop current is a lower bound under this policy, not an estimate of biological current.

The weight transform is another declared choice. FAFB weights are 12 · count^0.75 pA and BANC weights are min(5.0 · count^0.75, 300) pA, with exponential synapses of 5 ms excitatory and 8 ms inhibitory decay and a uniform 1 ms delay. No measurement fixes the scale, the exponent, or the cap. The transform was chosen to place currents on a workable scale, not fitted to electrophysiology. The 164.443 pA peak first-hop current and the 6.926 mV shortfall are properties of this transform.

The neuron model is a single uniform LIF parameter set: C = 200 pF, g = 10 nS, τ = 20 ms, V_rest = −65 mV, V_th = −50 mV, V_reset = −68 mV, a 2 ms refractory period, a −90 mV floor, and a 0.5 ms timestep. It has no cell-type-specific physiology, no adaptation, no bursting, and no morphology. Inhibition is a hyperpolarising current rather than a conductance, so there is no shunting inhibition and no reversal potential. These choices make the simulation tractable and auditable, but they also mean that the first-hop shortfall could be an artefact of the parameterisation. The paper reports the shortfall as a property of the model, not as a fact about the fly.

The sensory mapping is a convention. Seven features are mapped onto 232 identified BANC sensory neurons, with 48 neurons for train lane, 48 for obstacle lane, 24 for obstacle type, 24 for train presence, 24 for obstacle presence, 32 for train distance, and 32 for obstacle distance. Player pose and coins are not mapped. The assignments are computational hypotheses, including those whose pools come from published annotations. There is no receptive-field map, and the mapping's adequacy has not been measured against optic-lobe physiology.

Finally, the motor labels are annotation-derived. LEFT, RIGHT, and JUMP are decoder-defined pools of 185, 186, and 20 neurons, with 414 unassigned motor neurons; ROLL and DUCK are unsupported. A decoder label is not an identified motor command, and the positive control that drives the pools directly is a test of the decoder, not a demonstration of a biological motor code.

## 19.3 Internal validity: whether the comparisons support their claims

The programme's strongest internal-validity safeguard is that its confirmatory family was declared before estimation. Phase 6 fixed two paired plastic-versus-fixed contrasts and applied an exact two-sided sign-flip test with Holm correction over that family. The result was not rejected, and the paper does not reinterpret an exploratory endpoint as confirmatory.

Sample size is the main internal limitation. The Phase 6 confirmatory contrasts use ten seeds and forty held-out episodes per arm. The exploratory sensory-coding endpoint uses nine observations in three clusters, with about one observation per table cell; the identical response across mapping seeds means the effective replication is three, not nine. The population-size sweep shares one mapping seed and is a sensitivity analysis, not an independent replication. The neural-to-motor endpoint uses 330 windows nested in 66 runs and is circular because the decoder thresholds the same pool activity used as the predictor. The reward-ablation contrasts have three matched replicates, and with three pairs the smallest attainable two-sided p is 0.25, so no contrast can approach significance. These design facts bound every conclusion, and the paper labels the endpoints exploratory or descriptive accordingly.

The Phase 8 pilots are not campaign evidence. Pilot 1 has three seeds and three episodes; Pilot 2-C has three seeds and three episodes per arm; D5 has twenty training episodes per artifact. None estimates a contrast, and the pilot grid's motor silence makes C1, C2, and C4 degenerate and C3 undefined. The N = 16 confirmatory campaign was not executed, no value of `n_seeds_selected` was written, and the exact sign-flip test's minimum p-value at N = 16, 2/65,536, remains a design property rather than an achieved result.

The F/F_beta identity is a further internal limitation. The two conditions were intended to differ in whether the readout uses motor information. In the executed grid they did not differ behaviourally, because the motor feature vector was always zero. The certification confirms the wiring difference, but the experiment cannot discriminate the conditions' behavioural consequences. This is not a flaw in the controls; it is a limitation of running them on a motor-silent substrate.

## 19.4 External validity: whether the findings generalise

The controlled environment is a standalone endless-runner implementation, not the commercial Subway Surfers game. The commercial game was never instrumented, controlled, or played. Results about collision timing, coin collection, and survival in this environment do not transfer to the commercial product, and the paper does not claim that they do.

The substrate is also specific. FAFB and BANC are separate reconstructions and were not merged; FAFB is brain-only and contains no limb motor neurons, which is why the motor stage uses BANC. The BANC graph was thresholded at five synapses, retaining 1,535,710 of 11,596,517 non-self edges and 18,552,546 of 34,310,230 synapses, or 13.2429% of pairs and 54.0729% of synapses. A different threshold would produce a different graph and possibly a different first-hop current.

The detector was trained outside the repository, and its published metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, mAP50-95 0.687726 — are provenance, not re-measured results. The dataset has no independent test set: the curated split provides 1,188 training and 1,128 validation images, and 554 of 1,724 adjacent pairs (32.1%) cross the official split, with 224 near-duplicates, 58 of them across splits. The perception results are therefore bounded by a validation set that is not fully independent of training.

The parameter set is uniform across all neurons and all phases. A different LIF parameterisation, a different weight exponent, or a conductance-based inhibitory model could change the first-hop result. The paper does not generalise the shortfall beyond the tested operating point, and it does not claim that the connectome is incapable of supporting behaviour.

## 19.5 Statistical validity

The statistical design is conservative. Phase 6 reports the analytic bias floor rather than removing it, uses cluster-preserving block permutation and a cluster bootstrap, and applies an exact sign-flip test to the ten-pair contrasts with Holm correction. The observational unit is the seed or run, never the timestep or episode. The paper does not treat deterministic repeats as independent replicates.

The limitations are those of the data, not the tests. A non-significant exact test does not establish the null; it fails to reject. The Phase 6 estimate of −0.0863 bits has a descriptive interval that includes zero, and the paper reports the point estimate and the interval rather than a binary verdict alone. The exploratory p-values, such as 0.0278 for the sensory-coding endpoint and 0.0005 for the neural-to-motor endpoint, are reported with their design caveats: one observation per cell in the first case, circularity in the second. The Holm correction applies only to the declared confirmatory family; it does not license inference on exploratory endpoints.

The Phase 8 design fixed a smallest effect of interest of 100 updates, an N = 16 primary sample with an N = 10 fallback if σ_max ≤ 112.87, four seed streams, K = 10, and a primary outcome of min(updates, 900). None of those quantities was estimated from data because the campaign did not run. The minimum attainable p-value and the MDE are design properties, not achieved power.

## 19.6 Documentation and evidence-status limitations

The programme maintains a strict evidence vocabulary, and several limitations follow from it. An implementation test checks software behaviour on fixtures or synthetic inputs; it is not biological evidence. A pilot is an authorised small execution, not a confirmatory campaign. A certification PASS concerns artifact identity, schema, pairing, and recovery; it is not evidence of biological learning. The paper applies those labels consistently, which means that many results that might be read as successes are explicitly not scientific successes.

The documentation also contains known discrepancies, disclosed rather than repaired. The Pilot 1 report's prose total is 72,880 spikes while the nine rows sum to 73,880. The original report is preserved; the paper uses 73,880. The F/9001 training artifact required a provenance correction; the original bytes are preserved beside the corrected record. The Pilot 2-C floor rows have different action digests from the neural rows while their outcomes are identical. The Pilot 1 plan copy still says `executed = false`; the summary, manifest, and rows record execution. The Phase 7 demonstration contains an unexplained equality between a neural seed-42 row and a random seed-42 row with very different action streams; the paper flags it and does not use it as evidence.

The Phase 7 full suite recorded six failures on README hash pins, and Pilot 1's protected-baseline check found two drifts, README.md and `motor/__init__.py`, so `check_integrity()` returned `pass = false` and Pilot 1 is not freeze-ready. The drift pre-dates Pilot 1 and was not created by it, but it remains unresolved. The G3 memory deviation is also open: sixteen random graphs were generated and certified while free memory was below the 4 GB gate, the gate was not weakened, and the graphs were not accepted for data collection. B7 is unaccepted. These are documentation and governance limitations, not measurement errors, but they bound what the programme can claim about readiness.

## 19.7 Deviations register

Table 22 records the nine deviations identified across the programme.

**Table 22.** Deviations register. Each entry states the recorded item, the source record, the nature of the deviation, its effect, and its resolution. "Open" means the deviation remains unresolved and no restoration or amendment was performed. Data source: the reports and execution records cited in each row; full machine-readable table in `tables/T15_deviations_register.csv`.

| ID | Item | Record | Nature | Effect | Resolution |
|---|---|---|---|---|---|
| DEV-1 | Pilot 1 execution report prose total | `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` §6 | report says 72,880; nine rows sum to 73,880 | 1,000-spike arithmetic typo in prose only; per-episode values correct | disclosed; original not edited; corrected total used |
| DEV-2 | G3 memory gate during randomisation | `reports/PHASE_8_G3_DEVIATION_RESOLUTION.md` | 16 graphs generated and certified below the 4 GB gate | deviation recorded; gate not weakened; graphs not accepted for data collection | open; B7 unaccepted; Pilot 2-C uses no random graphs |
| DEV-3 | F/9001 resume ledger provenance | `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md` §3.2 | resumed artifact listed 19 of 20 checkpoints | original preserved; corrected record; no parameter or metric changed | resolved; regression test added |
| DEV-4 | Protected baseline drift (README, `motor/__init__.py`) | `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` §7.1 | 2 of 37 protected files differ from pins | `check_integrity()` returns `pass = false`; Pilot 1 not freeze-ready | open; not caused by the pilot; no restoration performed |
| DEV-5 | Floor vs neural action digest | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl` | floor rows have a different `action_sha256` from neural arms | different recording path; outcomes, counts, and rewards identical | disclosed; paper says identical outcomes, not identical digests |
| DEV-6 | Pilot 2-C preflight blocker | `reports/PHASE_8_PILOT2C_EXECUTION_PREFLIGHT.md` | global training-gate refusal folded into pilot stage blockers | pilot trains nothing; blocker moved to `training_blockers` | resolved before execution; superseded preflight preserved |
| DEV-7 | F_beta 9001 episode 0 wall time | `reports/PHASE_8_PILOT2C_EXECUTION_REPORT.md` §8 | 1,653.9 s for one episode, 47.8% of run wall time | host-scheduling observation; row fields consistent | recorded; no behavioural or simulation deviation |
| DEV-8 | Phase 7 full-suite failures | `reports/PHASE_7_GAME_INTEGRATION.md` | 6 tests fail on README hash pins | pre-existing README drift, unrelated to Phase 7 | disclosed; pins not edited |
| DEV-9 | Pilot 1 plan label | `experiments/results/phase_8/pilot1/pilot1/pilot_plan.json` | plan copy still says `executed = false` / construction-only | pre-execution plan copy; summary, manifest, and rows record execution | recorded, not rewritten |

## 19.8 Consolidated limitations register

Table 23 consolidates the fifteen limitations that bound the programme's conclusions. It is organised by scope rather than by phase, because the same limitation often affects several results.

**Table 23.** Consolidated limitations register. Each row states a limitation, its scope, and its consequence for interpretation. The register is descriptive; it does not rank limitations by severity. Data source: the phase reports and configuration documents cited in Chapters 3–16; full machine-readable table in `tables/T17_limitations.csv`.

| ID | Limitation | Scope | Consequence |
|---|---|---|---|
| L1 | Structural connectivity is not physiological connectivity | all connectome results | edge existence and synapse counts do not establish conductance, sign, or function |
| L2 | Transmitter signs are predictions; 55.52% of BANC t5 edges are unsigned | BANC propagation | a structural path may carry no modelled current |
| L3 | Weights are an arbitrary calibrated transform | all simulations | no measurement fixes the scale, exponent, or cap |
| L4 | One uniform LIF parameter set | all simulations | no cell-type-specific physiology, adaptation, or bursting |
| L5 | Inhibition is a hyperpolarising current, not a conductance | all simulations | no shunting inhibition or reversal potential |
| L6 | Uniform 1 ms delay; no morphology | all simulations | conduction distance and dendritic filtering are absent |
| L7 | Sensory mapping is a convention | Phase 3A.5, 4H.4, 8 | 232 neurons for 7 features; no receptive-field map |
| L8 | The game is not Subway Surfers | Phases 7–8 | `endless-surfer` is a separate controlled implementation |
| L9 | Decoder labels are annotation-derived | Phases 4F–8 | LEFT/RIGHT/JUMP are not identified motor commands; ROLL/DUCK unsupported |
| L10 | Motor silence blocks the experimental chain | Phase 4H.4, 7, 8 | no motor spikes means no action, no reward channel, no behavioural contrast |
| L11 | Pilot evidence is not campaign evidence | Phase 8 | 3 seeds × 3 episodes; no C1–C4 estimate; N not selected |
| L12 | Synthetic calibration and decoder tests are not biological evidence | Phase 3C, 4F, 4G | they test machinery only |
| L13 | MI is descriptive and does not establish causation | Phase 6 | circular decoder estimate; small replicate counts; bias floor |
| L14 | Training was behaviourally null | D5/D6 | zero motor spikes, zero weight change, identical F/F_beta outcomes |
| L15 | FAFB is brain-only; the VNC comes from a different dataset | Chapter 3 | no limb motor neurons in FAFB; BANC is not merged with FAFB |

## 19.9 Unresolved documentation issues

Five documentation issues remain unresolved at the close of the programme, and the paper records them rather than resolving them editorially.

First, the protected-baseline drift (DEV-4) leaves Pilot 1 not freeze-ready. README.md drifted during Phase 7, and `motor/__init__.py` was changed by commit `3c74ae8` on 2026-11-19, before Pilot 1. Because `motor/__init__.py` is a non-README failure, the integrity check returns `pass = false`. Resolving it requires an authorised amendment or a compliant restoration, neither of which was performed.

Second, the G3 memory deviation (DEV-2) remains open. Sixteen random graphs were generated and certified below the 4 GB gate; the gate was not weakened, and the graphs were not accepted for data collection. B7 is unaccepted. This does not affect Pilot 2-C, which uses no random graph, but it blocks C3 and therefore H2.

Third, the Pilot 1 report's 72,880 prose total (DEV-1) is preserved unchanged. The paper uses 73,880, the row sum, and discloses the difference. A reader comparing the paper with the report will see different totals for the same nine episodes; the explanation is the transcription error, not a difference in data.

Fourth, the Pilot 1 plan copy still says `executed = false` (DEV-9). The pre-execution plan was not rewritten. The authoritative records are the summary, manifest, and nine episode rows, all of which record the run as executed.

Fifth, the Phase 7 demonstration contains an unexplained equality between the neural seed-42 run and the random seed-42 run. The two have very different action streams — the random run contains JUMP, LEFT, RIGHT, ROLL, and NO_ACTION, while the neural run is entirely NO_ACTION — yet they report the same 213 updates, 2 coins, 1 collision, reward 5.55, and survival 3.12. The equality was flagged during analysis and is not used as evidence. It remains a documentation issue, not a scientific result.

A sixth issue is not a discrepancy but a scope limitation that readers may mistake for one: the detector's validation metrics are provenance from its training environment, not re-measured here, and there is no independent test set. The paper states this wherever the metrics appear.

## 19.10 Summary

The limitations fall into five groups. Construct validity is bounded by the gap between structural and physiological connectivity, the unsigned-edge fraction, the calibrated weight transform, the uniform LIF model, and the conventional sensory mapping. Internal validity is bounded by small samples, pilots that are not campaigns, a degenerate motor-silent grid, and a readout control that could not discriminate. External validity is bounded by a single controlled game, a single substrate threshold, and a detector validation set that is not fully independent. Statistical validity is bounded by the difference between failing to reject and establishing a null. Documentation is bounded by two open governance deviations, a preserved prose typo, a stale plan label, an unexplained Phase 7 equality, and a protected-baseline drift that leaves Pilot 1 not freeze-ready. None of these limitations is hidden, and none is repaired by changing a frozen parameter after the fact.

# Chapter 20. Conclusion

## 20.1 The question and the answer

This paper asked whether a connectome-derived fruit-fly neural network, implemented as a spiking neural simulation with learning mechanisms, can transform visual game information into functional motor commands in a controlled game environment.

The answer recorded by the programme is a qualified negative. The pipeline was built and runs: the FlyWire FAFB v783 brain graph and the BANC v888 brain–ventral-nerve-cord graph were converted into sparse LIF simulations; a detector-driven sensory mapping injected current into identified populations; a fixed threshold decoder mapped motor-population activity to LEFT, RIGHT, JUMP, or NO_ACTION; reward-modulated plasticity and a trainable linear readout were implemented and trained; a closed-loop bridge connected the simulation to a controlled endless-runner; and a pre-registered Phase 8 design with a pilot ladder was executed through four stages. The chain is reproducible, auditable, and provenance-complete.

It does not produce behaviour. In every executed closed-loop and pilot configuration the motor pools remained silent. The Phase 7 closed loop emitted 2,852 spikes, all from directly stimulated sensory neurons, and zero motor spikes, so the decoder returned NO_ACTION on all 213 decisions. Pilot 1 reproduced the result over nine episodes with 3,784 decisions, 126,135 neural steps, and 73,880 spikes. Pilot 2-C reproduced it over 54 entries with 3,784 decisions per arm. D5 added 120 training episodes with zero motor spikes and no synaptic weight change.

## 20.2 Why the negative is qualified

The negative is qualified in three ways, each supported by a measurement rather than an interpretation.

First, it is localised. The bottleneck analysis found that 662 signed first-hop edges from the stimulated sensory neurons reach 608 targets, 607 of them non-stimulated, and 473 of those receive current. The peak somatic depolarisation is −56.926 mV against a −50 mV threshold, a shortfall of 6.926 mV. No second-hop current is generated, and zero of 805 motor neurons spike. The failure is therefore at the first post-sensory stage, not at the decoder or the game interface.

Second, it is operating-point-specific. The shortfall is a property of the declared sensory convention, the calibrated weight transform, the uniform LIF parameters, and the verified-only sign policy, under which 55.52% of BANC t5 edges carry no modelled current. The paper does not claim that the connectome cannot support behaviour, and it does not tune a frozen parameter after seeing the result.

Third, the decoder is not the limiting component. When motor populations were driven directly in Phase 4G condition C, the decoder recorded 492 motor spikes across 82 active neurons and returned JUMP four times. The decoder can express an action; the drive required by its gate did not arrive.

## 20.3 What the programme established

The programme established a reproducible connectome-to-game software chain and a set of measurement results: graph statistics for FAFB and BANC at three thresholds; a validated LIF simulation with measured throughput and memory; a detector and sensory mapping with recorded provenance; a deterministic decoder with a characterised rule; a three-factor plasticity rule with attributable weight changes; an information-theoretic analysis with a declared bias floor and exact paired tests; a certified random-graph construction that was not accepted for data collection because of an open memory deviation; a pre-registered Phase 8 design; and four executed pilot or training stages with complete checkpoints and provenance.

It also established a negative result with a mechanism. The first-hop current is too small and too brief to charge the membrane to threshold, and the missing second hop leaves the motor pools silent. The same silence propagates into learning: the F readout's motor feature vector was identically zero in all 120 training episodes, so its twelve feature weights received no gradient and it behaved exactly like its bias-only control. The Phase 6 analysis found no supported gain in cue-to-action information from plasticity at its declared resolution, so the Phase 5F success increase is not explained by a representational gain.

## 20.4 What the programme did not establish

The programme did not establish functional game-playing, a biological motor code, a decoding claim, a learning effect on the connectome substrate, a contrast C1–C4, or a hypothesis conclusion H1–H6. C2 is a structural zero, C3 is undefined, and C1 and C4 are degenerate on the motor-silent grid. H1–H3 are unevaluable, H4 and H5 were not evaluated, and H6 has no subject. σ_max, the paired dispersion, and the upper confidence limit were not estimated; U7 remains open; N remains the predeclared 16 with no `n_seeds_selected` value. The N = 16 confirmatory campaign was not executed.

The programme did not establish that the fruit-fly brain cannot play the game. It established that this structural graph, this sensory convention, and this LIF parameterisation do not drive the first post-sensory stage above threshold, and that no learning mechanism downstream of a silent motor channel can be evaluated behaviourally.

## 20.5 Contributions

The paper's contributions are methodological and empirical. Methodologically, it demonstrates a disciplined way to build and audit a connectome-to-behaviour pipeline: separate structural from physiological claims, pre-register the confirmatory family, label pilots and implementation tests correctly, preserve negative results, and disclose discrepancies rather than repairing them silently. Empirically, it provides a quantitative account of where a widely used modelling approach stops: a 6.926 mV first-hop shortfall, a 55.52% unsigned-edge fraction, a zero motor-spike record across four stages, a null training set with certified artifacts, and a null information result with a declared estimator and exact test.

The paper also contributes a reusable evidence structure. The Phase 8 design, the random-graph certification machinery, the trained-artifact schema, the checkpoint and recovery protocol, and the information-analysis adapters are implemented and tested. They are available for a future campaign that would need a new authorisation, a resolved G3 deviation, and a substrate that produces motor activity.

## 20.6 Closing statement

FLY-SURFER set out to teach a fruit-fly brain to play a runner game through connectome-based neural simulation. It built the brain, the senses, the muscles, the reward, and the game, and it connected them. The brain spiked, the first synapses delivered current, and the decoder waited for a motor signal that never crossed threshold. The result is not a failure of engineering but a measurement of a boundary: structural connectivity, a conventional sensory mapping, and a uniform point-neuron physiology were not sufficient to produce motor output at this operating point. Reporting that boundary precisely, with its mechanism, its provenance, and its unresolved questions, is the contribution this paper offers.

## 20.7 Summary

The central question receives a qualified negative. The pipeline is complete and reproducible; the motor output is zero; the failure is a measured 6.926 mV first-hop shortfall; the learning stages downstream of the silence are null; and the confirmatory campaign remains unexecuted. The programme's value lies in the precision of that negative and in the infrastructure it leaves for a better-instrumented attempt.

# Chapter 21. Future Research

## 21.1 How future work should be framed

The questions below are not recommendations to modify the frozen protocol. They are open scientific questions that a future study would have to address under a new pre-registration, with its own authorisation, its own declared endpoints, and its own evidence labels. The programme's execution boundaries forbid changing a frozen parameter, threshold, hypothesis, or contrast in response to a result, and nothing in this chapter weakens that rule. The point of stating the questions is to make the boundary of the present result explicit and to identify what evidence a positive claim would require.

Two principles follow from the programme's experience. First, a future study should separate the question of whether the substrate can produce motor activity from the question of whether a learning rule can improve behaviour. The present work shows that the second cannot be answered while the first is negative. Second, a future study should pre-register the resolution at which it claims an information gain. The Phase 6 result is a failure to detect a gain at a 4 × 4 cue-by-action resolution over forty held-out episodes, not a proof that no gain exists at any resolution.

## 21.2 The first-hop drive question

The most direct question is whether a first-hop neuron can be driven above threshold by a physiological input regime. The present model fails by 6.926 mV with a transient current that delivers roughly 0.82 pC per event. A future study would need a calibrated synapse model and a parameter-sensitivity analysis over weight scale, synaptic time constant, and the number of co-active first-hop inputs. It would have to declare in advance that it is not tuning a threshold to force a spike. The scientific question is not whether some parameter set can make a neuron fire; it is which parameter sets are consistent with measured physiology and whether any of them produces a second hop.

A related question is whether the verified-only sign policy is the binding constraint. With 55.52% of BANC t5 edges unsigned, a structural path may carry no modelled current. A future study could ask how the first-hop current distribution changes under alternative, explicitly declared sign policies, while keeping the structural graph fixed. That is a sensitivity question about the sign convention, not a licence to assign signs that make the model work.

## 21.3 Physiological validation

A second question is whether any motor pathway can be validated against electrophysiology. The present programme measures spikes and currents in a simulation; it does not compare them with recorded responses. Answering this would require paired recording and connectome data that are not in this repository. Until such a comparison exists, claims about biological information flow remain structural hypotheses.

This question also bears on the decoder. LEFT, RIGHT, and JUMP are annotation-defined pools, not identified motor commands. A physiological validation could ask whether the pools correspond to measurable motor units and whether their activity precedes a behavioural action. The positive control in Phase 4G shows that the decoder can act when the pools are driven; it does not show that the pools are the right units for a fly.

## 21.4 Readout, motor activity, and the logic of controls

A third question is whether a trainable readout helps once motor activity exists. The present D5 artifacts cannot answer it because their motor feature vector was always zero. A future study would need a substrate with non-zero motor spikes, a readout trained on those features, and a pre-registered C4 evidence bar. The F/F_beta identity in the present grid is a warning: certification that a readout is state-dependent does not establish that it uses state information. A future design should include a manipulation check that the feature vector is non-degenerate before interpreting any readout contrast.

## 21.5 Topology and null models

A fourth question is whether biological topology outperforms degree- and sign-matched nulls. The programme built sixteen certified randomisation seeds and the exchange machinery for C3, but the G3 memory deviation left the graphs unaccepted and the campaign was never run. A future study would need a resolved G3 gate, a certified null construction that satisfies the memory constraint, and a pre-registered C3 contrast. The present Phase 5F observation that the random graph carried more measured cue-to-action information while performing worse behaviourally is a caution: the outcome variable and the information variable need not agree, and the design should specify which one answers the question.

## 21.6 Parameter sensitivity and cell-type physiology

A fifth question is whether the model's conclusions are stable under a declared sensitivity grid over weight scale, synaptic time constants, delay, and membrane parameters. The programme used one uniform LIF parameter set and one calibrated weight transform. A pre-registered sensitivity campaign could report how the first-hop current, the second-hop current, and the motor-spike count vary across the grid, without selecting a favourable point after the fact.

A sixth question is whether cell-type-specific LIF parameters change the bottleneck. The connectome supplies cell-type annotations for a substantial fraction of neurons; it does not supply measured conductances, adaptation, or bursting behaviour. A future study would need measured parameter sets, not values chosen to produce a spike. The present model's uniformity is a limitation, and the 6.926 mV shortfall could narrow or widen under cell-type-specific physiology; the direction is an empirical question.

## 21.7 Conventional learners and observation sufficiency

A seventh question is whether a conventional learner can solve the same seven-feature task. The Phase 5F perceptron reached success 1.0 on its synthetic task, but it is privileged and not a matched control. A future E-matched condition could test whether the observation interface is sufficient to support the task at all, independently of the connectome. If a conventional learner also fails, the problem is the observation or the task, not the spiking substrate. If it succeeds, the comparison isolates what the connectome model adds or fails to add.

This question is logically prior to a learning claim. Before asking whether plasticity improves a connectome's behaviour, one should ask whether the features the network receives are sufficient for the behaviour. The present motor silence makes that question especially salient: a readout cannot learn from a feature vector that is always zero, and a sensory mapping that never produces a discriminable motor correlate cannot support a decoding claim.

## 21.8 Receptive-field mapping

An eighth question is whether the sensory mapping can be replaced by a measured receptive-field map. The present mapping assigns seven features to 232 neurons by convention, with no receptive-field characterisation. Optic-lobe data that would support a measured map are not in this repository. A future study would need such data and a pre-registered mapping procedure; otherwise the sensory convention remains an assumption, and a negative result cannot distinguish a bad convention from a bad substrate.

## 21.9 What would count as a positive result

The programme's negative result sets a bar for any future positive claim. A demonstration that a connectome-derived model plays the controlled game would need to show, at minimum: motor-population spikes in the closed loop; a non-degenerate readout feature vector; a behavioural contrast against a matched control, not only against a floor; a pre-registered analysis that survives its own multiple-comparison correction; and a clear separation between structural connectivity and physiological inference. A claim of learning would additionally need a paired design with a declared smallest effect of interest, an adequate seed count, and a control that cannot learn.

A claim of information gain would need a pre-declared resolution and estimator, a bias floor, a paired test that respects the observational unit, and a sample size that can detect the declared effect. The present Phase 6 design met the first four requirements and failed to detect a gain; a future study with a different resolution or sample size would be a new experiment, not a reanalysis of the same data.

## 21.10 The open-question register

Table 24 lists the eight questions, their prerequisites, and their design notes.

**Table 24.** Open questions for future research. Each row states a question, the prerequisite that does not currently exist or is unresolved, and a design note. These are questions, not approved protocols; any future execution would require a new pre-registration and authorisation. Data source: the limitations and results of this paper, summarised in Chapters 17–19; full machine-readable table in `tables/T18_future_questions.csv`.

| ID | Question | Prerequisite | Design note |
|---|---|---|---|
| Q1 | Can a first-hop neuron be driven above threshold by a physiological input regime? | calibrated synapse model | parameter-sensitivity study; no threshold tuning to force a spike |
| Q2 | Can a motor pathway be validated against electrophysiology? | paired recording/connectome data | requires external data not in this repository |
| Q3 | Does a trainable readout help once motor activity exists? | a substrate with non-zero motor spikes | C4 evidence bar; campaign design |
| Q4 | Does biological topology outperform degree/sign-matched nulls? | certified random graphs | C3; G3 gate must be resolved |
| Q5 | Are the model conclusions stable under weight/scale sensitivity? | declared parameter grid | pre-registered sensitivity campaign |
| Q6 | Can cell-type-specific LIF parameters change the bottleneck? | annotated physiology | requires measured parameter sets |
| Q7 | Can a conventional learner solve the same seven-feature task? | E-matched | tests whether the observation interface is sufficient |
| Q8 | Can the sensory mapping be replaced by a measured receptive-field map? | optic-lobe data | no such map is in this repository |

## 21.11 Summary

The programme leaves a clear research agenda defined by its own boundary. The first priority is not a larger campaign but a better-understood first hop: whether any physiologically defensible parameterisation drives a post-sensory neuron above threshold, and whether the sign policy is the binding constraint. The second is physiological validation of the motor pathway. The third is a substrate on which motor activity exists, without which readout learning and behavioural contrasts cannot be evaluated. The remaining questions — topology, sensitivity, cell-type physiology, conventional learners, and receptive-field mapping — are downstream of those three. None can be answered by reinterpreting the present data, and none should be pursued by changing a frozen parameter after the fact.

# References

[1] Z. Zheng, J. S. Lauritzen, E. Perlman, C. G. Robinson, M. Nichols, D. Milkie, O. Torrens, J. Price, C. B. Fisher, N. Sharifi, S. A. Calle-Schuler, L. Kmecova, I. J. Ali, B. Karsh, E. T. Trautman, J. Bogovic, P. Hanslovsky, G. S. X. E. Jefferis, M. Kazhdan, K. Khairy, S. Saalfeld, R. Fetter, and D. D. Bock, "A complete electron microscopy volume of the brain of adult *Drosophila melanogaster*," *Cell*, vol. 174, no. 3, pp. 730–743.e22, 2018, doi: 10.1016/j.cell.2018.06.019.

[2] S. Dorkenwald, A. Matsliah, A. R. Sterling, P. Schlegel, S.-C. Yu, C. E. McKellar, A. Lin, M. Costa, K. Eichler, Y. Yin, W. Silversmith, C. Baker, D. Deutsch, D. Bland, and the FlyWire Consortium, "Neuronal wiring diagram of an adult brain," *Nature*, vol. 634, pp. 124–138, 2024, doi: 10.1038/s41586-024-07558-y.

[3] P. Schlegel, Y. Yin, A. S. Bates, S. Dorkenwald, K. Eichler, P. Brooks, D. S. Han, and the FlyWire Consortium, "Whole-brain annotation and multi-connectome cell typing of *Drosophila*," *Nature*, vol. 634, pp. 139–152, 2024, doi: 10.1038/s41586-024-07686-5.

[4] FlyWire Consortium, "FlyWire whole-brain connectome connectivity data, version 783.0," Zenodo, 2024, doi: 10.5281/zenodo.10676866.

[5] BANC project, "BANC v888 brain and ventral nerve cord connectome, edgelist v2 materialisation," dataset, 2026. Local export and file hashes are documented in `datasets/processed/banc_v888/banc_manifest.json` (accessed Nov. 23, 2026).

[6] W. Gerstner, W. M. Kistler, R. Naud, and L. Paninski, *Neuronal Dynamics: From Single Neurons to Networks and Models of Cognition*. Cambridge, U.K.: Cambridge Univ. Press, 2014, doi: 10.1017/CBO9781107447615.

[7] N. Frémaux and W. Gerstner, "Neuromodulated spike-timing-dependent plasticity, and theory of three-factor learning rules," *Frontiers in Neural Circuits*, vol. 9, art. 85, 2016, doi: 10.3389/fncir.2015.00085.

[8] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed. Cambridge, MA, USA: MIT Press, 2018.

[9] T. M. Cover and J. A. Thomas, *Elements of Information Theory*, 2nd ed. Hoboken, NJ, USA: Wiley, 2006.

[10] S. Holm, "A simple sequentially rejective multiple test procedure," *Scandinavian Journal of Statistics*, vol. 6, no. 2, pp. 65–70, 1979.

[11] E. Maris and R. Oostenveld, "Nonparametric testing in EEG/MEG," *Journal of Neuroscience Methods*, vol. 164, no. 1, pp. 177–190, 2007, doi: 10.1016/j.jneumeth.2007.03.024.

[12] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Chapman & Hall, 1993.

[13] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once: Unified, real-time object detection," in *Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR)*, 2016, pp. 779–788, doi: 10.1109/CVPR.2016.91.

[14] Microsoft, "ONNX Runtime," 2026. [Online]. Available: https://onnxruntime.ai (accessed Nov. 23, 2026).

[15] T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Dollár, and C. L. Zitnick, "Microsoft COCO: Common objects in context," in *Computer Vision – ECCV 2014*, LNCS 8693. Cham, Switzerland: Springer, 2014, pp. 740–755, doi: 10.1007/978-3-319-10602-1_48.

[16] S. S. Bidaye, C. Machacek, Y. Wu, and B. J. Dickson, "Neuronal control of *Drosophila* walking direction," *Science*, vol. 344, no. 6179, pp. 97–101, 2014, doi: 10.1126/science.1249964.

[17] M. E. Chiappe, J. D. Seelig, M. B. Reiser, and V. Jayaraman, "Walking modulates speed sensitivity in *Drosophila* motion vision," *Current Biology*, vol. 20, no. 16, pp. 1470–1475, 2010, doi: 10.1016/j.cub.2010.06.072.

[18] H. Fotowat and F. Gabbiani, "Collision detection as a model for sensory-motor integration," *Annual Review of Neuroscience*, vol. 34, pp. 1–19, 2011, doi: 10.1146/annurev-neuro-061010-113632.

[19] A. Borst, J. Haag, and D. F. Reiff, "Fly motion vision," *Annual Review of Neuroscience*, vol. 33, pp. 49–70, 2010, doi: 10.1146/annurev-neuro-060909-153155.

[20] J. C. Tuthill and R. I. Wilson, "Mechanosensation and adaptive motor control in insects," *Current Biology*, vol. 26, no. 20, pp. R1022–R1038, 2016, doi: 10.1016/j.cub.2016.06.070.

[21] J. D. Seelig and V. Jayaraman, "Neural dynamics for landmark orientation and angular path integration," *Nature*, vol. 521, pp. 186–191, 2015, doi: 10.1038/nature14446.

[22] M. Heisenberg, "Mushroom body memoir: From maps to models," *Nature Reviews Neuroscience*, vol. 4, no. 4, pp. 266–275, 2003, doi: 10.1038/nrn1074.

[23] H. Markram, E. Muller, S. Ramaswamy, M. W. Reimann, M. Abdellah, C. A. Sanchez, A. Ailamaki, N. Alonso-Nanclares, A. Antille, S. Arsever, G. Kahou, et al., "Reconstruction and simulation of neocortical microcircuitry," *Cell*, vol. 163, no. 2, pp. 456–492, 2015, doi: 10.1016/j.cell.2015.09.029.

[24] G. T. Einevoll, A. Destexhe, M. Diesmann, S. Grün, V. Jirsa, M. de Kamps, M. Migliore, T. V. Ness, H. E. Plesser, and F. Schürmann, "The scientific case for brain simulations," *Neuron*, vol. 102, no. 4, pp. 735–744, 2019, doi: 10.1016/j.neuron.2019.03.027.

[25] A. Sherman and M. H. Dickinson, "Summation of visual and mechanosensory feedback in *Drosophila* flight control," *Journal of Experimental Biology*, vol. 207, no. 1, pp. 133–142, 2004, doi: 10.1242/jeb.00731.

[26] C. R. Harris, K. J. Millman, S. J. van der Walt, R. Gommers, P. Virtanen, D. Cournapeau, E. Wieser, J. Taylor, S. Berg, N. J. Smith, R. Kern, M. Picus, S. Hoyer, M. H. van Kerkwijk, M. Brett, A. Haldane, J. F. del Río, M. Wiebe, P. Peterson, P. Gérard-Marchant, K. Sheppard, T. Reddy, W. Weckesser, H. Abbasi, C. Gohlke, and T. E. Oliphant, "Array programming with NumPy," *Nature*, vol. 585, pp. 357–362, 2020, doi: 10.1038/s41586-020-2649-2.

[27] W. McKinney, "Data structures for statistical computing in Python," in *Proc. 9th Python in Science Conference (SciPy)*, 2010, pp. 56–61.

[28] J. D. Hunter, "Matplotlib: A 2D graphics environment," *Computing in Science & Engineering*, vol. 9, no. 3, pp. 90–95, 2007, doi: 10.1109/MCSE.2007.55.

[29] SYBO Games, *Subway Surfers*. Copenhagen, Denmark: SYBO Games, 2012.

[30] A. Paszke, S. Gross, F. Massa, A. Lerer, J. Bradbury, G. Chanan, T. Killeen, Z. Lin, N. Gimelshein, L. Antiga, A. Desmaison, A. Köpf, E. Yang, Z. DeVito, M. Raison, A. Tejani, S. Chilamkurthy, B. Steiner, L. Fang, J. Bai, and S. Chintala, "PyTorch: An imperative style, high-performance deep learning library," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, vol. 32, 2019, pp. 8024–8035.

[31] P. Virtanen, R. Gommers, T. E. Oliphant, M. Haberland, T. Reddy, D. Cournapeau, E. Burovski, P. Peterson, W. Weckesser, J. Bright, S. J. van der Walt, M. Brett, J. Wilson, K. J. Millman, N. Mayorov, A. R. J. Nelson, E. Jones, R. Kern, E. Larson, C. J. Carey, İ. Polat, Y. Feng, E. W. Moore, J. VanderPlas, D. Laxalde, J. Perktold, R. Cimrman, I. Henriksen, E. A. Quintero, C. R. Harris, A. M. Archibald, A. H. Ribeiro, F. Pedregosa, P. van Mulbregt, and SciPy 1.0 Contributors, "SciPy 1.0: Fundamental algorithms for scientific computing in Python," *Nature Methods*, vol. 17, pp. 261–272, 2020, doi: 10.1038/s41592-019-0686-2.

# Appendix A. Repository Map and Artifact Inventory

## A.1 Scope and the read-only rule

The appendix documents where the evidence used in this paper lives. It does not add evidence. The repository's data, model artifacts, reports, protocols, and records are treated as read-only inputs; this paper's own products are confined to the `research_paper/` directory. Where a historical record contains an inconsistency, the record is identified and the inconsistency is disclosed rather than repaired.

**Table A1.** Repository components and their roles. Each path is a directory in the repository root. The "evidence role" column states what the paper uses the component for, not what the component claims about biology. Source: repository tree at the time of writing.

| Path | Contents | Evidence role in this paper |
|---|---|---|
| `datasets/` | Raw, processed, and exported data; manifest and audit records | Structural inputs and provenance |
| `configs/` | Frozen YAML configuration for neurons, synapses, decoder, plasticity, sensory mapping, Phase 6, and Phase 8 | Declared parameter values |
| `brain/` | BANC graph construction, BANC sensory adapter, BANC simulation adapter, simulator | Connectome loading and simulation |
| `sensory/` | Game state, population encoder, input scheduler, sensory experiment | Sensory encoding (Phase 3A) |
| `perception/` | Detector pipeline, observation layer, tracking, event encoding | Perception (Phase 3B.2A–3B.2C) |
| `motor/` | Motor populations, threshold decoder, action selection | Motor decoding (Phase 4F) |
| `plasticity/` | Reward, modulation, eligibility traces, three-factor rule, checkpoints | Plasticity (Phase 5) |
| `learning/` | Dopamine and synaptic-plasticity scaffolding, mutual information helpers | Exploratory learning machinery |
| `information/` | Entropy, mutual information, bias correction, permutation, bootstrap | Phase 6 estimators |
| `environment/` | Standalone-game adapter, action mapping, closed-loop bridge | Phase 7 and Phase 8 game binding |
| `readout/` | Motor feature vector, linear and bias-only readouts, REINFORCE trainer | Phase 8 conditions F and Fβ |
| `evaluation/` | Conventional learner (condition E) and viability reporting | Phase 8 G7 machinery |
| `experiments/` | Phase runners and stored results, including `experiments/results/` | Executed measurements |
| `reports/` | Phase reports, audit records, owner approvals, certification JSON | Primary written evidence |
| `docs/` | Protocols, preregistrations, design audits, including REV4 | Declared design |
| `tests/` | Focused and integration test suites | Implementation verification |
| `models/` | Exported YOLO11n ONNX detector and registry | Perception model |
| `external/` | Third-party reference repositories, including `endless-surfer` | Controlled game code |
| `references/` | Reference index and provenance notes | Citation anchors |
| `research_paper/` | This paper, its figures, tables, and validation records | Paper products |

## A.2 Executed-evidence directories

**Table A2.** Executed-evidence directories and their authoritative records. Hashes are SHA-256 prefixes as recorded in the corresponding reports. "Scope" states what the directory may be used for in this paper.

| Evidence | Directory or file | Recorded hash | Scope |
|---|---|---|---|
| Pilot 1 episodes (9 rows) | `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl` | `ee479e5b…68f9` | A-condition viability; no contrast |
| Pilot 1 driver record | `reports/PHASE_8_PILOT1_EXECUTION.json` | `d3392b9c…e1e` | Execution provenance |
| D5/D6 trained artifacts (6) | `experiments/results/phase_8/training/{F,F_beta}/seed_{9001,9002,9003}/` | per-artifact digests in Table I4 | Certified, behaviourally null training |
| D5 recovery reference | `experiments/results/phase_8/training_recovery_reference/F/seed_9001/equivalence.json` | `f236d070…52bf8` | Interrupted-versus-resumed equivalence |
| Pilot 2-C episodes (54 rows) | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl` | `a14fd3bb…778991` | Floor and identity certification |
| Pilot 2-C manifest | `…/pilot2c_d3_20261123/manifest.json` | `43710d38…020534` | Run provenance |
| Pilot 2-C plan | `…/pilot2c_d3_20261123/pilot_plan.json` | `63d51f61…ddcab` | Authorised grid |
| Pilot 2-C summary | `…/pilot2c_d3_20261123/pilot_summary.json` | `44dc5c05…520c5` | Completion record |
| Pilot 2-C certification | `reports/PHASE_8_PILOT2C_CERTIFICATION.json` | `bc5effaa…aa357` | Recomputable claims P2C-1–P2C-8 |
| Certified null graphs (16) | `datasets/processed/banc_v888_random/` | certificates per seed | Constructed; not used in any executed arm |

## A.3 What the repository does not contain

The paper's negative and unavailable statements depend on absences that must be stated precisely. The repository contains no per-neuron Pilot 1 spike split, no Pilot 1 membrane-potential trace, no raw per-frame spike array from the 3B.2C replay, and no independent detector test set. It contains no recording from a living fly, no intracellular or extracellular physiology, and no measured synaptic conductance. The commercial Subway Surfers application was never instrumented or controlled. Where a figure would require one of these, it is marked unavailable rather than approximated.

---

# Appendix B. Data Provenance and Inventory

## B.1 FlyWire FAFB v783

The FAFB materialisation is the FlyWire adult female brain connectome. The audit records 15 complete datasets, four incomplete downloads, 29,231,539 total rows, 368,874,372 compressed bytes, and 1,598,217,407 uncompressed bytes. The filtered connection table has 5,342,446 rows and 3,732,460 unique directed pairs, each pair being the sum of `syn_count` across neuropils for one `(pre_root_id, post_root_id)` pair. The pair-level synapse total is 50,666,648, with minimum 5, median 8, mean 13.575, 95th percentile 38, 99th percentile 87, and maximum 2,633. There are 620,180 directed reciprocal pairs and 671 isolated nodes. The processed artifact `connectome.npz` is 28,013,212 bytes with SHA-256 `3f568f24…5f33d8`; it is treated as read-only.

The audit is explicit about provenance limits. The version is inferred as v783 from an incomplete download filename, not attested by the completed files; no download log or source URL is stored with the files; and the audit recommends confirming the release and DOI before publication. The paper therefore cites the dataset version [4] and reports the audit's caveat rather than presenting the version as independently confirmed.

**Table B1.** FAFB node composition by `super_class`, in neurons. These are annotation counts from the published node table, not functional assignments made here. Source: `datasets/processed/` node annotations summarised in the connectome reports.

| `super_class` | Neurons |
|---|---:|
| optic | 77,873 |
| central | 32,381 |
| sensory | 16,938 |
| visual_projection | 7,684 |
| ascending | 1,750 |
| descending | 1,305 |
| sensory_ascending | 612 |
| visual_centrifugal | 522 |
| motor | 110 |
| endocrine | 80 |

Of 139,255 neurons, 119,597 carry annotations and 19,658 have a missing neurotransmitter label. The FAFB volume is brain-only: it contains 110 neurons annotated as motor, but no limb motor neurons, so it cannot supply a brain-to-muscle pathway. This is why the motor stage was rebuilt on BANC.

## B.2 BANC v888

The BANC export begins with 188,508 metadata rows. Sixteen thousand and seventy-five metadata-only rows are excluded, leaving 172,433 endpoint nodes. The original edge table has 11,752,828 edges; 156,311 self-edges (carrying 1,422,866 self-loop synapses) are removed, leaving 11,596,517 non-self edges. Three synapse-count thresholds are materialised, and the five-synapse graph is the primary substrate.

**Table B2.** BANC v888 threshold sensitivity. "Retention" is relative to the non-self edge list. Source: `datasets/processed/banc_v888/banc_construction_report.json`.

| Threshold | Directed edges | Summed synapses | Isolated nodes | Mean synapses per edge | Max synapses per edge |
|---|---:|---:|---:|---:|---:|
| t1 (≥1) | 11,596,517 | 34,310,230 | 6,232 | 2.9587 | 913 |
| t5 (≥5) | 1,535,710 | 18,552,546 | 24,320 | 12.0808 | 913 |
| t10 (≥10) | 570,721 | 12,397,230 | 62,551 | 21.7220 | 913 |

The t5 graph retains 13.2429% of non-self directed pairs and 54.0729% of non-self synapses. Annotation coverage is uneven and is reported rather than filled: `super_class` 88.069%, `cell_type` 68.2045%, `side` 91.7429%, `body_part_effector` 0.5968%, and `proofread` 100%. A neurotransmitter label exists for 89.27% of nodes when predictions are admitted, but only 37.87% when restricted to verified labels. Under the primary verified-only policy, 683,100 of 1,535,710 t5 edges (44.48%, 8,426,168 synapses) carry a sign; 852,610 edges are excluded.

**Table B3.** BANC `super_class` composition, in nodes. Source: `datasets/processed/banc_v888/banc_nodes.csv.gz`.

| `super_class` | Nodes |
|---|---:|
| optic_lobe_intrinsic | 72,826 |
| central_brain_intrinsic | 31,347 |
| unannotated | 20,573 |
| sensory | 15,956 |
| ventral_nerve_cord_intrinsic | 12,850 |
| visual_projection | 7,284 |
| glia | 6,281 |
| ascending | 1,849 |
| descending | 1,316 |
| motor | 805 |
| sensory_ascending | 514 |
| visual_centrifugal | 470 |
| visceral_circulatory | 221 |
| trachea | 83 |
| not_a_neuron | 40 |
| sensory_descending | 13 |
| ascending_visceral_circulatory | 5 |

Sixteen degree- and sign-preserving null graphs were constructed and certified, one per campaign seed, sharing the same 1,535,710-edge count. They are recorded as constructed infrastructure. No automated arm used one; the G3 memory deviation is recorded because the graphs were generated below the 4 GB gate.

## B.3 Detector dataset and model

The detector dataset is Roboflow v15: 2,328 images, 2,328 label files, 8,666 bounding boxes, and 14 classes, drawn from five recording groups. The official split is 1,825 training and 503 validation images with no test split. Twelve label files are empty. Of 1,724 adjacent frame pairs, 554 (32.1%) cross the official split boundary, and 224 near-duplicate images exist, 58 of them across the boundary. A sequence-grouped re-split was therefore constructed at 1,188 training and 1,128 validation images; no independent test set exists in either split.

The deployed detector is a YOLO11n exported to ONNX, 10,636,871 bytes, SHA-256 `e6ad18f9…6aa77`, input `[1, 3, 640, 640]` float32 NCHW, output `[1, 18, 8400]`, with confidence 0.426 and NMS IoU 0.7. Its reported validation metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, mAP50-95 0.687726 — were produced during training outside this repository and are reported as provenance, not re-measured. The metrics are computed on the curated validation split, not on an independent test set.

## B.4 Controlled game

The game is the standalone `endless-surfer` implementation, not the commercial Subway Surfers application. Its declared constants are a 900-step cap, initial speed 7.0, maximum speed 16.0, coin reward +1.0, collision penalty −1.0, survival reward +0.01 per step, obstacle reward 0.0, and a 25.0-unit observation horizon in normalised game-world units. The reward is a synthetic task scalar, not a dopamine measurement.

## B.5 Dataset separation

FAFB v783 and BANC v888 are separate graphs with separate identifiers and separate annotations. They are never merged, joined, or cross-referenced at the level of individual neurons. FAFB supplies the brain graph used in the perception and propagation studies; BANC supplies the brain-plus-ventral-nerve-cord graph used from Phase 4 onward because it contains motor neurons. The Male CNS dataset is reference-only. The detector dataset and the game code are third-party materials with their own licences, recorded in `THIRD_PARTY_NOTICES.md`.

---

# Appendix C. Model and Simulation Parameters

Every value below is a declared modelling parameter. None is a measured membrane property, conductance, or biological learning constant.

## C.1 Neuron model

The membrane follows

C_m dV/dt = −g_L (V − E_L) + I(t),  (C.1)

integrated with the exact exponential-Euler step

V(t + dt) = E_L + (V(t) − E_L + I/g_L) e^{−dt/τ_m} − I/g_L,  (C.2)

with τ_m = C_m/g_L, followed by threshold, reset, refractory, and floor rules.

**Table C1.** Leaky integrate-and-fire parameters. All values are assumed, not measured in this project. Source: `configs/neuron_config.yaml`.

| Parameter | Symbol | Value | Unit |
|---|---|---:|---|
| Membrane capacitance | C_m | 200 | pF |
| Leak conductance | g_L | 10 | nS |
| Membrane time constant | τ_m | 20 | ms |
| Resting potential | E_L | −65 | mV |
| Threshold | V_th | −50 | mV |
| Reset potential | V_reset | −68 | mV |
| Refractory period | — | 2 | ms |
| Membrane floor | — | −90 | mV |
| Rheobase, steady state | — | 150 | pA |
| Timestep | dt | 0.5 | ms |

The rheobase is derived, not fitted: 15 mV × 10 nS = 150 pA. The floor at −90 mV represents unmodelled leak and voltage-gated currents and exists to keep the state finite under sustained inhibition.

## C.2 Synapses, signs, and weights

Synaptic events are exponential currents with separate excitatory and inhibitory time constants, a uniform delay rounded to whole timesteps, and a sparse CSR representation. The weight transformation is

w_FAFB = 12 · count^{0.75} pA,  (C.3)

w_BANC = min(5.0 · count^{0.75}, 300) pA,  (C.4)

where `count` is the integer pair-level synapse count. Equation (C.4) makes an edge with 20 synapses contribute about 47 pA, roughly one third of rheobase, so temporal summation is required to fire.

**Table C2.** Synapse and sign-policy parameters. Source: `configs/simulation_config.yaml`, `configs/banc_synapse_policy.yaml`.

| Item | Value | Status |
|---|---|---|
| FAFB weight transform | 12 · count^{0.75} pA | calibration |
| BANC weight transform | min(5.0 · count^{0.75}, 300) pA | calibration |
| Excitatory decay | 5 ms | assumed |
| Inhibitory decay | 8 ms | assumed |
| Uniform delay | 1 ms | assumed |
| Acetylcholine, glutamate | excitatory | predicted transmitter |
| GABA, glycine | inhibitory | predicted transmitter |
| Dopamine, serotonin, octopamine, tyramine, histamine, nitric oxide | unknown / excluded | declared |
| Edges with no verified sign | excluded, zero current | 55.52% of BANC t5 edges |
| Verified-sign edges | 683,100 of 1,535,710 | 44.48%, 8,426,168 synapses |

Three sensitivity transforms are declared for the BANC weight policy — linear-capped, log1p, half-power, unit-power, and uncapped power — and the calibration grid is {0.5, 1.0, 2.0, 5.0, 20.0, 50.0} pA. The selection rule forbids choosing a scale on the basis of a decoder label; no such tuning was performed.

## C.3 Motor decoder

The decoder scores each motor pool over a half-open 50 ms window. The score is the active fraction of the population,

a_P(t) = |{i ∈ P : neuron i spiked in [t, t+50 ms)}| / |P|,  (C.5)

and a pool is eligible when it has at least 5 spikes and at least 3 active neurons. If any pool is eligible, the highest active fraction wins; ties are broken in the fixed order LEFT, RIGHT, JUMP. Otherwise the decoder returns NO_ACTION.

**Table C3.** Motor pools and decoder constants. Pool sizes are annotation counts, not functional assignments. Source: `configs/motor_decoder.yaml`, `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md`.

| Item | Value | Basis |
|---|---|---|
| LEFT pool | 185 neurons | left leg effectors |
| RIGHT pool | 186 neurons | right leg effectors |
| JUMP pool | 20 neurons | tergotrochanter extensor candidates |
| Unassigned motor neurons | 414 | never decoded |
| Total motor neurons | 805 | annotation |
| Window | 50 ms, half-open | declared |
| Activation threshold | 0.20 active fraction | declared |
| Release threshold (hysteresis only) | 0.10 | declared |
| Eligibility gate | ≥5 spikes and ≥3 active neurons | declared |
| Tie order | LEFT → RIGHT → JUMP | declared |
| ROLL, DUCK | unsupported | no annotation |

## C.4 Plasticity and sensory drive

The three-factor rule is

Δw_ij = η · M(t) · e_ij(t),  (C.6)

with an eligibility trace

e_ij(t) = λ e_ij(t−1) + f(pre_i, post_j), λ = exp(−dt/τ_e),  (C.7)

a decaying modulation

M(t) = clip(M(t−dt) e^{−dt/τ_M} + gain · r(t), −5, +5),  (C.8)

and bounds 0.5–2.0 times the initial weight, a 5 pA per-update cap, and a sign-flip abort. Only verified-sign edges are plastic.

**Table C4.** Plasticity and sensory-drive parameters. Source: `configs/plasticity_banc.yaml`, `configs/banc_sensory_mapping.yaml`, `configs/phase_8/conditions.yaml`.

| Parameter | Value | Status |
|---|---|---|
| Learning rate η, Phase 8 arms B and D | 0.5 | declared |
| Identity learning rate η, A′ and C′ | 0.0 | declared |
| Learning rate η, Phase 5F plastic condition | 1.0 | declared |
| Eligibility time constant τ_e | 20 ms | assumed |
| Modulation decay τ_M | 50 ms | assumed |
| Modulation gain and clip | 1.0, ±5 | declared |
| Weight bounds | 0.5–2.0 × initial | assumed |
| Maximum absolute update | 5 pA | assumed |
| Sensory current per active feature | 200 pA | declared |
| Pulse decay | 150 ms | declared |
| Mapped sensory neurons | 232 across 7 features | convention |

The 232 mapped neurons are: train_lane 48, obstacle_lane 48, obstacle_type 24, train_present 24, obstacle_present 24, train_distance 32, and obstacle_distance 32. Player pose and coin features are unmapped because the v15 event schema has no such fields. The mapping is a declared convention; no receptive-field map exists in the repository.

---

# Appendix D. Phase-by-Phase Implementation and Validation Evidence

## D.1 Recorded outcomes

**Table D1.** Phase-by-phase outcomes. "Status" reproduces the status recorded in the phase reports; "evidence class" is the paper's classification of what the result can support. Source: `tables/T07_phase_validation_summary.csv` and the individual phase reports.

| Phase | Objective | Key recorded result | Status | Evidence class |
|---|---|---|---|---|
| 0 | Audit the raw FAFB export | 11/11 audit and 8/8 round-trip checks | PASS | Data provenance |
| 1 | Build the connectome artifact | 139,255 nodes; 3,732,460 edges; 50,666,648 synapses | PASS | Data construction |
| 2 | LIF simulation on 800 neurons | 1,564 spikes; 79/800 active | PASS | Implementation test |
| 2.5 | Scale to the full graph | Full graph 138.3 steps/s; 349,846 spikes | PASS WITH LIMITATIONS | Benchmark |
| 3A | Map 14 features to 138 sensory neurons | Driven neurons spike | PASS WITH LIMITATIONS | Implementation test |
| 3A.5 | Calibrate the sensory operating point | 200 pA, σ 0.20, 4 neurons; 2/6/7 spikes; d′ 2.357 | PASS WITH LIMITATIONS | Implementation test |
| 3B.1 | Curate the detector dataset | 2,328 images; 8,666 boxes; 5 groups | PASS WITH LIMITATIONS | Data audit |
| 3B.2A | Perception architecture | Screenshot to GameState contract | PASS | Implementation test |
| 3B.2B.3 | Integrate YOLO11n ONNX | 2 of 13 smoke detections rejected by bounds | PASS WITH LIMITATIONS | Implementation test |
| 3B.2C | Replay 100 frames through perception and FAFB | 15,654,631 spikes; 25.84% active; 99.976% stimulated | PASS WITH LIMITATIONS | Instrumented replay |
| 3C | Temporal features and event scheduler | 50 synthetic sequences; continuity 0.944 | PASS (synthetic) | Implementation test |
| 4A | Dataset compatibility | 139,241 shared root IDs; 14 FAFB-only; 7 annotation-only | PARTIALLY COMPATIBLE | Data audit |
| 4B | Locomotor pathway investigation | No VNC motor neurons in FAFB | COMPLETE | Data audit |
| 4C.5 | BANC integrity audit | 172,433 endpoints | PASS WITH LIMITATIONS | Data audit |
| 4D | Construct the BANC graph | t5: 1,535,710 edges; five source hashes match | PASS WITH LIMITATIONS | Data construction |
| 4E | Motor populations and pathways | 805 motor; 1,316 descending; 1,849 ascending; 17,745 DN→MN t1 edges | PASS WITH LIMITATIONS | Structural analysis |
| 4F | Fixed motor decoder | 11 scenarios × 6 amplitudes | PASS WITH LIMITATIONS | Implementation test |
| 4G | Propagate through BANC and decode | Condition C: 1,296 spikes, 492 motor, JUMP ×4 | PASS WITH LIMITATIONS | Controlled simulation |
| 4H.4 | Sensory-to-motor round trip | 3,562 spikes, all stimulated; 0 motor | PASS WITH LIMITATIONS | Instrumented experiment |
| 5 | Reward, eligibility, three-factor rule | Synthetic task: plastic 0.945 vs fixed 0.795 | PASS (software); INCONCLUSIVE (biology) | Model experiment |
| 6 | Information-theoretic evaluation | Plastic − fixed cue→action MI = −0.0863 bits; p = 0.125 | NOT SUPPORTED | Archived-data analysis |
| 7 | Closed-loop game integration | Seed 42: 213 updates, 2,852 spikes, 0 motor | INTEGRATION PASS | Controlled simulation |
| 8 Pilot 1 | A-condition viability | 9 episodes; 73,880 spikes; 0 motor | EXECUTED; NOT FREEZE-READY | Pilot |
| 8 D5/D6 | Train F and Fβ readouts | 6 artifacts; 120/120 episodes; null behaviour | CERTIFIED | Pilot training |
| 8 Pilot 2-C | Floor and identity certification | 54/54 rows; A′ exact ×9; all arms motor-null | EXECUTED AND CERTIFIED | Pilot |

## D.2 Test-suite record

**Table D2.** Cumulative test-suite counts recorded at each phase boundary. These counts verify software behaviour; they are not biological evidence, and a passing test says nothing about whether a model claim is true. Source: `tables/T20_test_suite_summary.csv`.

| Phase boundary | Tests | Result | Note |
|---|---:|---|---|
| Phase 2 | 68 | passed | LIF, synapses, sampling, recorder, simulator, configs |
| Phase 4D | 331 | passed | Cumulative at BANC graph construction |
| Phase 4E | 345 | passed | Cumulative at pathway analysis |
| Phase 4F | 397 | passed | Cumulative at decoder development |
| Phase 4G | 440 | passed | Cumulative at BANC propagation |
| Phase 5G | 683 | passed | Cumulative at plasticity validation |
| Phase 6C | 748 | passed | Cumulative at MI analysis |
| Phase 6 final | 999 | passed, 3 skipped | Information analysis and integration |
| Phase 7 | 1,012 | passed, 3 skipped, 6 failed | Six pre-existing README-hash failures |
| Phase 8 D5/D6 | 530 | passed | After the pilot training path |
| Phase 8 Pilot 2-C | 531 | passed | After preflight blocker resolution |

The six Phase 7 failures are pre-existing and unrelated to Phase 7: three protected-hash checks report the README drift, two smoke-mode labels report `SMOKE INVALID` instead of `SMOKE ONLY`, and one C0 cache assertion fails. They are disclosed in the paper's deviation register (DEV-8) and were not suppressed.

## D.3 Interpretation rule

Every row in Table D1 that concerns software is an implementation test, including the 4F decoder matrix, the 4G propagation conditions, and the 5F synthetic task. Rows that concern executed model runs on the connectome — 3B.2C, 4H.4, Phase 6, Phase 7, Pilot 1, D5/D6, Pilot 2-C — are model-experiment evidence. None is physiological evidence, and no row establishes that the model matches a living fly.

---

# Appendix E. Phase 6 Estimator Definitions and Declared Analysis

## E.1 Estimators

With log base 2, the plug-in entropy of a variable X over n complete observations is

Ĥ(X) = −Σ_x p̂(x) log₂ p̂(x),  (E.1)

and the plug-in mutual information is

Î(X;Y) = Σ_{x,y} p̂(x,y) log₂ [p̂(x,y) / (p̂(x) p̂(y))].  (E.2)

The first-order upward bias of Î for a table with k_x and k_y declared levels is reported, not removed:

B(k_x, k_y, N) = (k_x − 1)(k_y − 1) / (2 N ln 2).  (E.3)

The corrected value is max(0, Î − B) and is labelled a first-order correction, not a substitute for sample size. Normalised MI divides the raw Î by min(Ĥ(X), Ĥ(Y)) and is withheld when that denominator is at or below the declared entropy floor of 0.05 bits. The uncertainty coefficient divides by Ĥ(Y). Conditional MI is the sample-weighted mean of within-stratum estimates, with a minimum stratum size of 50 observations.

## E.2 Declared inference and support rules

**Table E1.** Phase 6 declared analysis constants. Source: `configs/phase_6_information.yaml`.

| Item | Value |
|---|---|
| Log base | 2 |
| Confirmatory minimum observations | 100 |
| Confirmatory minimum clusters | 10 |
| Minimum clusters for an interval | 3 |
| Minimum expected observations per cell | 5 |
| Minimum marginal entropy for normalised MI | 0.05 bits |
| Minimum observations per conditional-MI stratum | 50 |
| Confirmatory permutations | 5,000 |
| Exploratory permutations | 2,000 |
| Permutation scheme | Cluster-preserving block, when observations share a run, seed, or replicate |
| Bootstrap resamples | 2,000 |
| α | 0.05 |

The only confirmatory family is the pair of paired plastic-versus-fixed contrasts in Phase 5F, complete and random wiring, with Holm correction over m = 2. Everything else is exploratory or descriptive and is labelled as such in the results.

## E.3 Confirmatory and exploratory values

**Table E2.** Phase 6 recorded estimates. Confirmatory rows are the declared family; the remaining rows are exploratory or descriptive and carry no inferential claim. Source: `experiments/results/phase_6/information_analysis.json`; `tables/T08_phase6_information.csv`.

| Endpoint | Estimate | Uncertainty | Decision |
|---|---|---|---|
| Cue→action MI, complete wiring, plastic − fixed | −0.0863 bits | 95% CI [−0.1751, 0.0052]; exact p = 0.125 | Not rejected; Holm 0.250 |
| Cue→action MI, random wiring, plastic − fixed | −0.0025 bits | 95% CI [−0.0075, 0.0000]; exact p = 1.000 | Not rejected |
| Fixed complete wiring, checkpoint 160 | 0.6126 bits | descriptive | — |
| Plastic complete wiring, checkpoint 160 | 0.5262 bits | descriptive | — |
| Fixed random wiring, checkpoint 160 | 1.3547 bits | descriptive | — |
| Plastic random wiring, checkpoint 160 | 1.3522 bits | descriptive | — |
| Distance→population code, Phase 3A.5 | 1.5849625 bits (log₂ 3) | bias floor 0.3206; corrected 1.2644; p = 0.0278 | Exploratory |
| Neural pool→decoded action, Phase 4F | 1.1841 bits | floor 0.0459; corrected 1.1382; normalised 0.8128; p = 0.0005 | Descriptive, circular |
| Conditional cue→action MI, six conditions | 0.6040 bits | floor 0.0135; corrected 0.5905; p = 0.0005 | Exploratory |
| Marginal cue→action MI, pooled | 0.3841 bits | descriptive | Exploratory |
| Reward ablation B − A | −0.0605 bits | exact p = 0.5 | Exploratory, three pairs |
| Reward ablation B − D | −0.0486 bits | exact p = 0.5 | Exploratory, three pairs |

The checkpoint-0 paired contrast is exactly zero for both wiring conditions because the arms have identical weights at that checkpoint. That equality is a matched-control check, not a finding.

## E.4 Endpoints declared unavailable

**Table E3.** Phase 6 endpoints that could not be estimated from the archive, with the recorded reason. These are results about the archive, not failures to compute. Source: `configs/phase_6_information.yaml`.

| ID | Endpoint | Reason |
|---|---|---|
| U01 | Real-replay sensory→neural MI | The 3B.2C replay persists aggregate counts only; no per-neuron or per-frame arrays exist |
| U02 | Spike-train entropy | No archived run persists raw spike times at sufficient scale; available arrays are single trials with few spikes per neuron |
| U03 | Membrane-potential entropy | Membrane potentials were never persisted |
| U04 | Neural-level plasticity information | The Phase 5 BANC run stores three distinct spike hashes and one decoded-state sequence; repeats are deterministic, not independent |
| U05 | Neural-level reward modulation | No arm persists independent per-neuron activity |
| U06 | Cue→neural response | Per-episode cue spike count is the constant 8 and the total is 12 (11 or 12 in E); a constant cannot carry cue information |
| U07 | Neural→reward | Per-episode counts are constant in conditions A–F; no neural predictor of reward exists without inventing an observation |

---

# Appendix F. Phase 8 Statistical Design Details

## F.1 Contrasts and hypotheses

**Table F1.** Confirmatory contrasts, mapped hypotheses, and the interpretation each would license. Source: `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` sections 3, 5, and 7.

| ID | Contrast | Hypothesis | Licensed interpretation if significant |
|---|---|---|---|
| C1 | F − A | H3 | A readout over the fixed substrate beats the fixed decoder |
| C2 | B − A | H1 | Three-factor plasticity changes survival on the biological substrate |
| C3 | A − C | H2 | Biological topology outperforms a degree- and sign-matched random graph |
| C4 | F − Fβ | Decoding gate | The readout uses motor information rather than a constant bias |

H1 ↔ C2, H2 ↔ C3, H3 ↔ C1. H4 (E-matched above floor) is an explanatory reference and is not in the Holm family. H5, the interaction (B − A) − (D − C), is exploratory. H6, that every non-NO_ACTION action is preceded by a matching motor spike, is descriptive. Neither H5 nor H6 can be promoted to confirmatory status after seeing data.

## F.2 Primary outcome and smallest effect of interest

The primary outcome is the capped survival score

Y = min(observed updates, 900),  (F.1)

averaged over the K = 10 evaluation episodes within a seed, so the seed is the independent unit. The smallest effect of interest is 100 updates, about 11% of the cap and about 1.5 times the three-seed random-agent standard deviation of 67.3 updates. It is a declared convention: the obstacle cadence was not measured, so no behavioural distance was derivable.

## F.3 Pairing and random streams

Episode j of seed s uses the environment seed derived from master seed 20261116 and the `(s, j)` pair, independent of condition. Four separate streams — environment, network, learning, and structure — are derived from the same master seed. The environment and structure streams omit the condition because pairing requires a shared environment and one graph per seed; the network and learning streams include it. Reusing one stream across purposes is forbidden. Each episode performs a full reset with no state carried between episodes.

## F.4 Sample-size rule

The primary design is N = 16 paired seeds. The N = 10 fallback is permitted only if

2.8016 · σ_max / √10 ≤ 100,  (F.2)

equivalently σ_max ≤ 112.87 updates, where σ_max is the pilot's largest paired standard deviation among C1–C4. Equation (F.2) is the normal-theory minimum detectable effect rearranged,

MDE = 2.8016 · σ_max / √N,  (F.3)

and is an approximation, not exact power for the sign-flip test. At N = 16 with an assumed σ of 60, the normal-theory MDE is about 42 updates and the Holm step-1 MDE is about 50 updates. The value 60 is an assumption placed between the Phase 7 random-agent and rule-based between-seed standard deviations; it is not a measurement. The N decision is made once, before the campaign. `design.n_seeds_selected` remained null after both pilots, so the campaign could not start.

## F.5 Exact sign-flip test

Let d_1 … d_N be the paired per-seed differences. The two-sided exact sign-flip p-value is

p = (1 / 2^N) · Σ_{ε ∈ {−1,+1}^N} 1[ |mean(ε_i d_i)| ≥ |mean(d_i)| ].  (F.4)

There is no Monte Carlo sampling and no normal approximation. At N = 16 there are 65,536 sign vectors and the minimum attainable two-sided p is 2/65,536 = 0.0000305176; at N = 10 there are 1,024 vectors and the minimum is 2/1,024 = 0.001953125. The minimum is attained by the extremal vectors `sign(d)` and `−sign(d)`. Holm correction is applied over m = 4 for C1–C4, so the step-1 threshold is α/4 = 0.0125.

A paired difference of exactly zero is retained and contributes nothing to any sign vector. If every difference is zero, every sign vector has the same statistic, p = 1.0 by construction, and the test is uninformative. The protocol required that this case be reported as "no power against a difference between two floored conditions", not as equivalence.

## F.6 Identity and integrity gates

A′ and C′ must reproduce A and C exactly on nineteen declared fields at η = 0, with no tolerance. On a mismatch, the corresponding plastic arm is marked invalid, its result is retained but excluded from aggregates, and the campaign stops. The protected 37-file baseline is checked before and after; the connectome fingerprint is asserted unchanged in A, C, and F; in B and D only the weight state may change, and the full digest chain is recorded.

---

# Appendix G. Pilot 1 Checks and the 72,880 / 73,880 Disclosure

## G.1 Arithmetic from the stored rows

**Table G1.** Pilot 1 row sums. Values are the stored per-episode fields, summed without modification. Source: `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`.

| Quantity | Row values | Sum |
|---|---|---:|
| Game updates | 323, 620, 323, 620, 426, 620, 213, 426, 213 | 3,784 |
| Neural steps | 10,767, 20,667, 10,767, 20,667, 14,200, 20,667, 7,100, 14,200, 7,100 | 126,135 |
| Total spikes | 4,764, 14,348, 4,764, 14,911, 8,396, 13,139, 2,850, 7,856, 2,852 | **73,880** |
| Motor spikes | 0 in all nine rows | 0 |
| Reward | 5.22, 10.19, 4.22, 7.19, 3.25, 8.19, 3.12, 4.25, 2.12 | 47.75 |

## G.2 The discrepancy

The Pilot 1 execution report's prose states a total of **72,880** spikes, and repeats that figure in its discussion of the zero-motor result. The nine stored rows sum to **73,880**. The difference is exactly 1,000 spikes, or 1.3537% of the row sum. It is a transcription error in prose: all nine rows are present, the other row-level fields are consistent with the run summary, and no episode value is missing or duplicated.

This paper uses 73,880 everywhere the Pilot 1 total is reported, including the abstract, Chapter 13, Table 16, Chapter 17, and Table 21. The historical report is preserved unmodified and is not silently corrected. The discrepancy is registered as DEV-1 in Table 22 and repeated in Appendix G so that a reader comparing the paper with the report sees the same rows and understands why the totals differ. No scientific claim in this paper depends on the difference: the load-bearing quantities are the zero motor spikes, the 3,784 NO_ACTION decisions, and the per-episode spike counts, all of which are identical in both records.

## G.3 Execution and integrity checks

**Table G2.** Pilot 1 recorded checks. Source: `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md` and the pilot manifest.

| Check | Recorded value |
|---|---|
| Planned / executed / stored episodes | 9 / 9 / 9 |
| Complete | true |
| Evidence kind | pilot |
| Estimates contrasts | false |
| Merged into campaign | false |
| Wall time | 357.0 s, 10:58:51Z to 11:04:48Z on 2026-11-20 |
| Memory gate at start | 5.745 GiB available against 4.0 GiB |
| Passive memory samples | 177 at 2 s intervals |
| Maximum process RSS | 0.3725 GiB |
| Minimum system-available memory | 4.1997 GiB |
| Weight fingerprint | `4923f0cd…945d5`, identical before and after every episode |
| Truncated episodes | 0 |
| Protected-baseline match | 35 of 37 files |
| Protectable-baseline drifts | `README.md`; `motor/__init__.py` (commit `3c74ae8`, 2026-11-19) |
| Integrity result | `pass = false`; manifest `integrity.checked = false` |
| Freeze status | Not freeze-ready |

The drift was not created by the D2 implementation or by Pilot 1. It was not altered to make the pilot pass, and no restoration was performed. The episode rows remain valid measurements of the model; the protocol's publication gate is not passed.

---

# Appendix H. Motor-Bottleneck Measurements and Controls

## H.1 Structural funnel

**Table H1.** Signed structural reachability from the 232 stimulated sensory neurons under the verified-only sign policy. "First hop" counts targets of the stimulated set; "second hop" counts targets of the first hop. Source: `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`, a read-only analysis.

| Quantity | Count |
|---|---:|
| Stimulated sensory neurons | 232 |
| Signed outgoing first-hop edges | 662 |
| Distinct first-hop targets | 608 |
| Non-stimulated first-hop targets | 607 |
| Recurrent stimulated targets | 1 |
| First-hop targets that are motor neurons | 0 |
| Signed outgoing second-hop edges | 5,259 |
| Distinct second-hop targets | 3,865 |
| Non-stimulated second-hop targets | 3,576 |
| Second-hop targets that are motor neurons | 4 (2 JUMP; 0 LEFT/RIGHT) |
| Motor neurons with at least one signed incoming edge | 735 of 805 |

## H.2 Current and membrane at the first hop

**Table H2.** Recorded first-hop current and membrane values from the instrumented Phase 4H.4 run, which used the same seven frozen input hashes as Pilot 1. Source: `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`; Phase 4H.4 round-trip report.

| Quantity | Value |
|---|---:|
| Stimulated neurons that fired (Phase 4H.4) | 171 of 232 |
| Spikes recorded | 3,562, all from stimulated neurons |
| First-hop targets receiving current | 473 of 607 |
| Median first-hop current | 0 pA |
| 95th percentile first-hop current | 80.87 pA |
| Maximum first-hop current | 164.443 pA |
| Largest static signed first-hop sum | 167.041 pA (node 125949) |
| Rest potential | −65 mV |
| Threshold | −50 mV |
| Required depolarisation | 15 mV |
| Peak first-hop membrane | −56.926 mV |
| Peak depolarisation | 8.074 mV |
| Shortfall to threshold | 6.926 mV |
| First-hop neurons that fired | 0 of 473 |
| Second-hop current delivered | 0 pA |
| Descending-neuron maximum current | 67.208 pA |
| Descending-neuron peak membrane | −62.158 mV (12.158 mV short) |
| Ascending, second-hop, and motor neurons | 0 pA; −65 mV |
| Spike transmissions recorded | 25,332, of which 9,499 signed |

The current peak exceeds the 150 pA steady-state rheobase, but the current is transient: a 164 pA event with τ = 5 ms carries about 0.82 pC, or about 4.1 mV on a 200 pF membrane, and overlapping events reach the recorded 8.074 mV. That charge calculation is an order-of-magnitude consistency check, not a new measurement.

## H.3 Negative controls

**Table H3.** Phase 4H.4 control conditions. Every control produced zero non-stimulated spikes. Source: Phase 4H.4 report.

| Control | Result |
|---|---|
| Temporal shuffle | 0 non-stimulated spikes |
| Feature-identity shuffle | 0 non-stimulated spikes |
| Random matched mapping | 0 non-stimulated spikes |
| Constant matched charge | 0 non-stimulated spikes |
| 50 pA background + 50 pA noise | 0 non-stimulated spikes; closest neuron still 7.35 mV short |
| No-event baseline | 0 non-stimulated spikes |

## H.4 Positive controls on the decoder and motor tissue

**Table H4.** Positive controls showing that the decoder and motor populations can produce actions when driven directly. These demonstrate that the decoder is functional; they are not sensory pathways. Source: `reports/PHASE_4G_BANC_NEURAL_PROPAGATION.md`, `reports/PHASE_4G4_PROPAGATION_VALIDATION.md`.

| Condition | Total spikes | Motor spikes | Active motor neurons | Decoded action |
|---|---:|---:|---:|---|
| B, descending drive | 781 | 18 | — | NEUTRAL ×5 (all 18 in unassigned motor neurons) |
| C, 64 VNC intrinsic neurons at 300 pA | 1,296 | 492 | 82 | JUMP in 4 of 5 windows |
| D | 704 | 0 | 0 | NEUTRAL |
| E | 728 | 0 | 0 | NEUTRAL |

## H.5 What the bottleneck analysis does not establish

The first-hop values come from Phase 4H.4, not from Pilot 1's stored rows, which do not persist a per-neuron split or any membrane potential. The transfer rests on four convergent facts: byte-identical frozen inputs across seven hashes, the same production loop with zero background and zero noise, a structural query that reproduces the target set from the frozen graph, and a same-design replication in Phase 7 that persisted 2,852 stimulated spikes, zero non-stimulated spikes, and zero motor spikes. The values are a convergent inference about the same frozen model, not a per-neuron measurement of Pilot 1.

---

# Appendix I. D5/D6 Training and Checkpoint Record Schema

## I.1 Artifact layout

Each trained readout artifact occupies `experiments/results/phase_8/training/{condition}/seed_{evaluation_seed}/` and contains `training_run.json`, `manifest.json`, `parameters.npz`, and twenty checkpoint directories (`checkpoints/episode_001` … `episode_020`). For F/9001, the interrupted run's original provenance record is preserved as `training_run.incomplete_provenance.json`; the corrected record is `training_run.json`.

**Table I1.** Top-level sections of `training_run.json`. Source: `experiments/results/phase_8/training/F/seed_9001/training_run.json` and the D5/D6 report.

| Section | Contents |
|---|---|
| `kind`, `origin`, `evidence_kind` | `pilot_training_run`; `trained`; `experimental` |
| `condition_id`, `evaluation_seed`, `training_seed`, `pool_index` | Condition and B3 pairing identity |
| `identity` | Model kind, feature count (3), pool index, training seed |
| `authorisation` | D5/D6 paths and hashes, B3 digest, approval date, substrate, explicit non-authorisations |
| `frozen_inputs` | Seven frozen input paths |
| `master_seed`, `campaign_seed`, `init_seed` | Seed derivation record |
| `budget` | 20 episodes |
| `checkpoint_policy` | One checkpoint per completed episode; keep all intermediates and the final checkpoint; schema version 2 |
| `optimizer` | Optimizer state checkpointed; per-episode optimizer digests |
| `created` | UTC timestamp; Python 3.13.14, NumPy 2.3.4, PyTorch 2.10.0 |
| `digest` | Initial, state, and trainable parameter digests |
| `episodes`, `episodes_completed` | Twenty per-episode records |
| `checkpoints` | Twenty checkpoint ledger entries |
| `artifacts` | Manifest and parameter file names, sizes, SHA-256 |
| `provenance_correction` | Recovery ledger: equivalence report path and hash, re-verified checkpoints, corrected UTC |
| `limitations` | Declared scope limits |

## I.2 Episode record fields

**Table I2.** Fields recorded for each training episode. Source: `training_run.json` episode entries.

| Field | Meaning |
|---|---|
| `episode`, `steps`, `n_decisions` | Episode index, game updates, decoder decisions |
| `environment_seed`, `network_seed` | Derived seeds for the episode |
| `total_spikes`, `motor_spikes` | Network and motor-population totals |
| `action_counts` | Counts for LEFT, RIGHT, JUMP, NO_ACTION |
| `episode_reward`, `mean_return` | Reward scalar and mean return |
| `updates_applied`, `updates_after` | Readout updates applied and cumulative |
| `loss`, `policy_loss`, `value_loss`, `entropy`, `grad_norm` | Training diagnostics |
| `parameter_digest_before`, `parameter_digest_after` | Readout parameter digests |
| `state_digest_after` | Full readout state digest |
| `weights_before`, `weights_after` | Substrate weight fingerprint, unchanged |
| `behaviour_sha256` | Episode action/reward digest |
| `terminated`, `truncated`, `termination_reason` | Termination record |
| `substrate` | `biological_graph` |

## I.3 Checkpoint ledger

**Table I3.** Fields recorded for each checkpoint entry. Source: `training_run.json` checkpoint entries.

| Field | Meaning |
|---|---|
| `episode`, `directory` | Episode index and checkpoint path |
| `schema_version` | Checkpoint schema version (2) |
| `digest.state`, `digest.trainable`, `digest.optimizer` | State, trainable-parameter, and optimizer digests |
| `parameters_sha256`, `components_sha256`, `manifest_sha256` | File hashes for `parameters.npz`, `components.npz`, `checkpoint.json` |
| `rng_checkpointed`, `optimizer_state_checkpointed`, `environment_present` | State-capture flags |
| `integrity_verified`, `retained` | Verification and retention flags |

## I.4 Six artifacts and their pairing

**Table I4.** The six D5/D6 artifacts. Evaluation seeds are disjoint from training seeds and from the campaign seed list. Source: `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md`; `tables/T11_d5_training_artifacts.csv`.

| Condition | Evaluation seed | Training seed | Pool index | Init seed | Episodes | Parameter digest (state/trainable) |
|---|---:|---:|---:|---:|---:|---|
| F | 9001 | 1008 | 7 | 1350278753 | 20 | `bd50cc73…9a8883` |
| F | 9002 | 1014 | 13 | 3449218186 | 20 | `e1c25034…dadce` |
| F | 9003 | 1005 | 4 | 3297997184 | 20 | `2e188b78…d9961` |
| F_beta | 9001 | 1008 | 7 | 1849113230 | 20 | state `b9e5b6e3…7d712`; trainable `0975693e…1f76e` |
| F_beta | 9002 | 1014 | 13 | 992595534 | 20 | state `5842826f…a5b4e`; trainable `5f03c88b…ff5b9` |
| F_beta | 9003 | 1005 | 4 | 56964545 | 20 | state `409410cc…103f84`; trainable `b157ae1e…6ca120` |

All six are `origin = trained`, read-only, and were neither retrained nor substituted during Pilot 2-C.

## I.5 Recovery and equivalence

The F/9001 run was interrupted by a logging `KeyError` after episode 1. It was resumed, and the completed run was compared with an uninterrupted reference run at the same declared budget and seeds. The equivalence report records 20 compared episodes and 12 compared fields — `n_decisions`, `steps`, `updates_applied`, `updates_after`, `loss`, `mean_return`, `episode_reward`, `policy_loss`, `value_loss`, `entropy`, `grad_norm`, and `parameter_digest_after` — with zero differences and `equivalent = true`.

The original provenance record listed 19 of 20 checkpoints. It is preserved unmodified as `training_run.incomplete_provenance.json`, with SHA-256 `a385aabd…`. The corrected record `training_run.json`, SHA-256 `fd30434b…`, adds the missing ledger entry and re-verifies all twenty checkpoints. No parameter, digest, episode metric, or checkpoint byte changed. The correction is registered as DEV-3, and a regression test covers the ledger.

## I.6 Why the training was behaviourally null

The readout sees three motor active fractions. On a motor-silent substrate every feature is zero, so the feature vector is identically zero and the logits reduce to the bias. F's feature weights never receive a gradient because the input is zero, and Fβ's feature weights are fixed at zero by construction. Both biases start at zero and receive the same update under the same training seed, so the two conditions remain bit-identical in policy. Zero motor spikes were recorded in all 120 episodes, the substrate weight fingerprint never changed, and F and Fβ produced identical actions, rewards, and decision counts for every paired `(seed, episode)`.

---

# Appendix J. Pilot 2-C Claim Definitions and Identity Fields

## J.1 Authorisation binding

Pilot 2-C is bound to REV4 (`e4aa9e0f…1547c`), D3 (`74f11d2c…48df8`), and the Pilot 2-C amendment (`832ef485…67ad`). Its stage purpose is `floor_and_identity_certification`, its evidence kind is `pilot`, and its summary records `experimental_evidence = true` and `merged_into_campaign = false`. The grid is five neural arms and a substrate-free floor at three evaluation seeds and three episodes, 54 entries. No C, C′, or D arm was run; no randomized graph was read or substituted; no training occurred; `n_seeds_selected` was not written.

## J.2 Operational definition of each claim

**Table J1.** Pilot 2-C claims and the observation that would falsify each. All eight passed when recomputed from the 54 stored rows and the manifest. Source: `reports/PHASE_8_PILOT2C_CERTIFICATION.json`.

| Claim | Operational definition | Falsifier |
|---|---|---|
| P2C-1 | Nine floor replays present; every decision NO_ACTION; motor spikes 0; weights null; `neural_substrate = none`; `spikes_read = false` | Any floor row with a non-neutral action, a spike, or a weight |
| P2C-2 | A′ equals A exactly on P1–P19 in 9/9; η = 0; changed edges 0; max |Δw| 0.0; one opening reset; zero in-episode resets | Any mismatch on any field, or any nonzero delta |
| P2C-3 | Fβ has zero nonzero feature weights; trainable set exactly `["bias"]`; identical logits for zero and saturated feature vectors; one action on every decision | A nonzero feature weight or any feature-dependent logit |
| P2C-4 | F has 12 nonzero feature-weight entries; weights frozen; parameter and feature-weight digests identical before and after every episode | A digest change, or zero feature weights (which would make F an Fβ replica by construction) |
| P2C-5 | Every neural episode records a per-decision motor block and a consistent motor-spike count; zero reported as zero | A missing block or an inconsistent count |
| P2C-6 | A′ reports exactly zero delta in all nine; B reports eligible edges, changed edges, maximum absolute delta, update reports, and hook calls for every episode; zero clamp hits; zero sign violations | An A′ nonzero delta, or a B episode without its attribution record |
| P2C-7 | Every row records seven input hashes, three config hashes, seed plan, evidence kind, stage purpose, and D3/amendment binding; F/Fβ rows add artifact condition, seeds, digests, and parameter-file hash | A missing hash or binding |
| P2C-8 | 54 planned, 54 stored, 0 missing, 0 error rows, every row schema-valid with a survival score; nothing skipped, retried, or substituted | A missing or error row, a retry, or a substitution |

## J.3 The nineteen identity fields

**Table J2.** The P1–P19 exact-comparison fields used by the A′ and C′ controls. Tolerance is none. Source: `experiments/phase_8/controls/equivalence.py` (REV4 section 3.8.3).

| Field | Requirement |
|---|---|
| P1 | Spike times, exact array equality |
| P2 | Spike neuron indices, exact array equality |
| P3 | Spike SHA-256 |
| P4 | Action and reward SHA-256 |
| P5 | Full record sequence, canonical JSON |
| P6 | Survival and termination summary |
| P7 | Action and decoder-state counts |
| P8 | Reward total and every component |
| P9 | Neural steps, neural time, game time |
| P10 | Motor activity per decision |
| P11 | Structural weight digest |
| P12 | Initial weight digest |
| P13 | Learned-delta digest and exact zero delta |
| P14 | Effective weight digest equals the initial digest |
| P15 | Maximum absolute weight change exactly 0.0 |
| P16 | Changed edges exactly 0 |
| P17 | Clamp hits and saturation count exactly 0 |
| P18 | Stepper weight fingerprint equal before and after |
| P19 | Resets during the episode |

All nine A′ pairs matched on all nineteen fields. The store-level reduced comparison — P3, P4, P6, P7, P8, P10, P12, and P14 — also reported no mismatch. The hard stop that would refuse an A′ episode on mismatch was never triggered, and B was not invalidated.

## J.4 Recorded attribution values

B ran at η = 0.5 with 683,100 eligible edges. Four of its nine episodes applied updates — 42, 45, 24, and 12 applied updates — and each changed exactly one edge. The maximum absolute delta was 0.03265 pA, the maximum applied update 0.01022 pA, and there were zero clamp hits and zero sign violations. Each neural arm recorded 3,784 decisions and zero decisions with a motor spike; the 50 ms motor window block was present in every episode. These are weight-level and accounting facts. They are not a behavioural effect, and the amendment forbids reading them as one.

## J.5 What the certification does not license

A passing P2C-1–P2C-8 certifies that the floor executes, that the plastic path is an identity at η = 0, that Fβ is provably constant, that F is wired and frozen, that motor activity is accounted for, that plasticity is attributable, that provenance is complete, and that the grid is viable. It does not certify learning, decoding, or behavioural competence. C1–C4 were not estimated; C2 is a structural zero; C3 is undefined; H1–H3 are unevaluable; H4 and H5 were not evaluated; H6 has no subject. σ_max and dispersion were not estimated, U7 remains open, and N remains the predeclared 16.

---

# Appendix K. Reproduction, Environment, and Frozen Hashes

## K.1 Software environment

**Table K1.** Recorded software versions. The project dependencies are pinned; the training artifact records the interpreter and numerical-library versions used for D5/D6. Source: `requirements.txt`, `datasets/manifest.json`, `training_run.json` creation block.

| Component | Version | Role |
|---|---|---|
| Python | 3.13.14 | Interpreter |
| NumPy | 2.3.4 | Numerical arrays, simulation core |
| pandas | 2.3.3 | Tabular analysis |
| Matplotlib | 3.10.7 | Figures |
| PyYAML | 6.0.3 | Configuration parsing |
| psutil | 7.1.2 | Memory instrumentation and gate |
| Pillow | 12.0.0 | Image loading for perception |
| onnxruntime | 1.29.0 | CPU ONNX detector backend |
| PyTorch | 2.10.0 | Linear readout and REINFORCE training |
| pytest | 7.4.3 | Test runner; anyio plugin disabled in `pytest.ini` |
| Platform | Windows 11 x64 | Recorded host platform |

The ONNX backend is CPU-only; no GPU package is installed. The full-graph simulation reaches 138.3 steps/s on this host with 134.7 MB retained, and the Phase 2.5 benchmarks record the scaling curve from 800 to 139,255 neurons.

## K.2 Read-only verification commands

The following entry points exist and write nothing. They reproduce checks, not experiments.

```bash
python -m experiments.phase_8.run_campaign --pretty check
python -m experiments.phase_8.run_campaign --pretty seeds --seed 1
python -m experiments.phase_8.run_campaign --pretty graphs --seed 1 --verify
python -m experiments.phase_8.stages.run_stage --list
python -m experiments.phase_8.stages.pilot2c evaluate
python -m pytest
```

`run_campaign check` reports conformance, approval, design resolution, certified graph count, and the memory preflight; while the approval and memory gates are unmet it returns `executable = false` and exit code 1. `pilot2c evaluate` recomputes P2C-1–P2C-8 from the stored rows and manifest and writes nothing else. `pytest` runs the repository suite under `pytest.ini`.

Executing a pilot, training job, or campaign is a different matter. It requires the applicable dated owner authorisation, the frozen protocol and amendment, and the 4.0 GB free-memory gate, and it is outside the scope of this paper. The authoritative reproduction of the executed runs is the stored artifacts themselves: the episode rows, manifests, summaries, certification records, and hashes listed in Appendix A and below. Re-running a simulation to "check" a reported value would create a new result, not reproduce the recorded one.

## K.3 Frozen input and configuration hashes

**Table K2.** Frozen input and configuration hashes recorded in every Pilot 2-C row. Source: `reports/PHASE_8_PILOT2C_EXECUTION_REPORT.md` section 9.2.

| Input | SHA-256 prefix |
|---|---|
| BANC graph, t5 | `6d47f259…e2192` |
| BANC node table | `144a2eb0…53e5f` |
| Neuron configuration | `9b652bde…8b77` |
| Synapse policy | `88f64492…dc399e` |
| Plasticity configuration | `616288a4…9e5f70` |
| Sensory mapping | `64c716a4…cdfc4ff` |
| Motor decoder | `525f25e9…0d9fae` |
| Campaign configuration | `b9a2d3d5…477e19` |
| Conditions configuration | `9a93f047…42f671` |
| Environment configuration | `b391ecf7…3281dc` |

## K.4 Protocol and authorisation hashes

**Table K3.** Protocol and authorisation hashes. Source: `reports/phase_8_owner_approvals/`, the execution preflights, and `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md`.

| Record | SHA-256 prefix |
|---|---|
| REV4 protocol (1,915 lines) | `e4aa9e0f…1547c` |
| Pilot 2-C amendment | `832ef485…67ad` |
| D1 approval | `5c183c99…d489` |
| D2 decision | `b5b0c229…7327` |
| D3 amendment decision | `74f11d2c…48df8` |
| D5 approval | `015598e8…bfe3f` |
| D6 record | `6a342504…d8325` |
| B3 training pairing digest | `bc231c79…1f980` |

## K.5 Resource and timing record

**Table K4.** Recorded resource and timing facts for the executed stages. These are host observations, not model properties. Source: execution reports and the Pilot 2-C preflight.

| Stage | Record |
|---|---|
| Pilot 1 wall time | 357.0 s |
| Pilot 1 peak process RSS | 0.3725 GiB |
| Pilot 1 minimum system-available memory | 4.1997 GiB |
| Pilot 2-C episode wall time | 3,458.8 s total; first row 03:37:44Z, last 04:35:36Z on 2026-11-23 |
| Pilot 2-C memory gate | 6.115 GB available against 4.00 GB, 60.1% used |
| Pilot 2-C longest episode | `F_beta:9001:0`, 1,653.9 s (47.8% of run wall time) |
| Next longest Pilot 2-C episode | 304.8 s |
| Full-graph simulation throughput | 138.3 steps/s |
| Full-graph retained memory | 134.7317 MB |

## K.6 Closing note on reproducibility

The project's reproducibility claim is narrower than "anyone can rerun this and get the same numbers". It is that every reported value is stored with its provenance, that the identity and accounting claims can be recomputed from the stored rows, and that the code paths that produced the values are pinned by configuration hashes and test suites. Where a value cannot be recomputed — because the relevant per-neuron state was not persisted, or because no independent test set exists — the paper marks it unavailable rather than reconstructing it.
