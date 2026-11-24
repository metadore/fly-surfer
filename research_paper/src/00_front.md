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

[[TOC]]

<!-- pagebreak -->

## List of figures

[[LOF]]

<!-- pagebreak -->

## List of tables

[[LOT]]
