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
