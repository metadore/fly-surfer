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
