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
