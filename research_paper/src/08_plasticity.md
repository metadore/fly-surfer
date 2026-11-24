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
