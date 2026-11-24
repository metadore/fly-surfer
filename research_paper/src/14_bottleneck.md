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
