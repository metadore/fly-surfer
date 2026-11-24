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
