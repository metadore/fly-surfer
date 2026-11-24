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
