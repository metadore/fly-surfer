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
