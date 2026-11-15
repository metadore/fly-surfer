# Phase 6D Independent Audit

**Verdict: APPROVED WITH REQUIRED CORRECTIONS**

| Item | Value |
| --- | --- |
| Phase | 6D — recording pre-registration |
| Audit date | 2026-11-11 |
| Documents audited | `reports/PHASE_6D_RECORDING_PREREGISTRATION.md` (SHA-256 `e27db60c1ba5c80cac033508610fc8d2e817aa3aef9d8a9f59f2c841ffbe748c`), `reports/PHASE_6D_RECORDING_PREREGISTRATION.json` (SHA-256 `c3fd6fad0ace629e293a7bb86fa5552dcae72a2f1e8410edf8f5bc45633e7036`) |
| Oracle in force | `README.md` SHA-256 `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| Method | Read-only source inspection, independent arithmetic re-derivation from archived artifacts, and recomputation of the exact binomial/Fisher and mutual-information quantities quoted in the protocol. No simulation, recording, training, model change, dataset change, or code change was made. No test suite was run. |
| Deliverable | This file only. The two Phase 6D reports were not modified. |
| Result | The protocol is scientifically well posed and its gating philosophy is sound, but **seven substantive corrections are required before G0 can be signed and no simulation may be run as written**. All seven are fixable inside the design; none requires new architecture, new data, or a new phase. |

## 1. Executive verdict

### 1.1 What the protocol gets right

The protocol is unusually honest for a recording design, and several of its choices should be preserved without weakening:

1. **The propagation-positive gate is placed before the campaign.** Stage P (324 runs, ≈14 min) is a cheap stop. A failed P2 does not spend 2,688 runs and 19,200 episodes. This is the correct architecture.
2. **The non-claims are explicit and repeated.** Structural edges are not functional transmission, a decoder label is not a motor command, a simulated spike is not a biological spike, and a positive propagation pilot is not fly behaviour. These are the right boundaries.
3. **Integrity is binary and is checked first.** P0 combines record completeness, the archived 4H condition-B spike hash, the 5% determinism re-run, capacity exceptions, and finite membrane arrays. A failed integrity check invalidates the phase rather than producing a hedged result.
4. **The estimator bias floor is acknowledged prospectively.** §8.2 uses `(kx−1)(ky−1)/(2N ln2)`, rejects the 40-episode Phase 5F/6C table as evidence of power, and sets N against the largest declared table. Phase 6C found the bias floor after the fact; Phase 6D correctly moves it before the run.
5. **The event-cluster guard exists.** §8.6 does not treat repeated trials of the same stimulus event as generalisation to the stimulus corpus. The implementation of that guard is wrong (see §2.5), but the intent is right.
6. **The instrumentation is not allowed to edit production modules.** §11.3 uses the instance-level wrapper already proven in `experiments/phase_4h/analyse_sensory_roundtrip.py:816–832`, and G2 requires the archived hash to reproduce with no production file changed.
7. **The analysis is frozen before prose.** §9.6 and G7 require the results JSON to be written and hashed before the report is written, and the analysis may be run only once.

### 1.2 What is not yet defensible

The independent audit found errors in all four requested dimensions. The most consequential are:

| # | Finding | Why it matters | Severity |
| --- | --- | --- | --- |
| A1 | `d*` is fixed at P1 and P2 is evaluated only at that one drive (§6.2, §6.3), while §10.4 claims P2 fails "at every drive". A propagation effect that appears at 800 or 1200 pA but not at the lowest P1-passing drive stops the programme falsely. | The programme's central go/no-go decision is made at a single, possibly subthreshold drive. The 240 Stage P runs already cover all four drives, so fixing this costs nothing. | **Blocking** |
| A2 | P2 is tested on `H2 ∪ DESC` with a zero-tolerance control rule. Nine descending neurons are direct first-hop targets (`reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md:216,303`), so a P2 pass can be first-hop, not second-hop. A true control rate of 0.5–2% gives an 18–55% chance of at least one control spike in 40 trials, mechanically failing the gate. | The gate does not test the stated hypothesis and stops on noise. | **Blocking** |
| A3 | The independence table says "2,688 unique seeds" (§8.1) while §6.3 pairs one seed across four conditions; the true count is 672 seeds × 4 conditions = 2,688 runs. | The permutation/bootstrap unit and the paired analysis are mis-specified, and the "trial has its own seed" justification is wrong for Stage R. | **Blocking** |
| A4 | The stimulus corpus is described as 43 distinct events. The archive contains 43 event records from **24 distinct tracks**; `OBST_NEAR` is **one track observed at two frames**, not two events. The event-cluster bootstrap resamples the 43 records and therefore treats repeated observations of one track as independent. | The generalisation guard is anti-conservative, and the `OBST_NEAR` endpoint has an effective stimulus sample of one. | **Blocking** |
| A5 | Stage S's declared 0.05-bit MDE is below the cluster-level minimum detectable effect. Using the between-seed SD measured in Phase 6C (0.1581 bits) and 40 seed clusters, the 80%-power MDE is ≈0.070 bits (α = 0.05) or ≈0.091 bits (Holm α = 0.005). | The endpoint cannot detect the effect it declares; the reported "positive" criterion is unreachable at the stated power. | **Blocking** |
| A6 | The recording panel does not account for the post-step reset. `LIFPopulation.step` sets spiking neurons to −68 mV before returning (`brain/neuron_model.py:154`), so a recorder that samples `membrane_potential` after `step` never sees threshold unless it substitutes it, as the 4H wrapper does at `experiments/phase_4h/analyse_sensory_roundtrip.py:828`. The protocol's O2 describes the property but not this requirement. | The optional membrane diagnostic would be systematically wrong, and the determinism contract is incomplete. | **Blocking** |
| A7 | The archived events are timestamped 66.7–3266.7 ms, but the Stage R trial is 300 ms with onset 50 ms. The protocol never specifies how event times are rebased or clipped. `BancEventDrive` uses the event's absolute `time_ms`, so most archived events would never fire in a 300 ms trial. | The stimulus cannot be constructed as described. | **Blocking** |

A8–A14 are required before the relevant gate but are not, by themselves, reasons to abandon the design. They are listed in §7 and in the final unresolved-issue table.

### 1.3 Operational meaning of the verdict

**APPROVED WITH REQUIRED CORRECTIONS** means:

- G0 may **not** be signed against the current text. The seven blocking corrections must be incorporated, the protocol re-frozen with a new SHA-256, and the JSON companion updated to match.
- After re-freezing, G1 (write instrumentation and tests only) may proceed. No simulation may be run under G1.
- G2 must reproduce the archived 4H condition-B spike hash with the recorder installed, and must demonstrate identical spike hashes with recording enabled and disabled for every archived condition used as a fixture.
- G3 (Stage P) may run only after G2 passes.
- G4 must freeze the full gate decision, including P1a, P1, P2a, P2b, P2s and P3, before any Stage R outcome is examined.
- G5 is reached only if P2a and P2b pass at some drive and P2s does not overturn specificity. A failed P2 at every drive is a legitimate, reportable negative outcome and leaves the Phase 4H findings intact.

The audit does **not** recommend NOT READY, because every defect is a specification defect rather than a scientific dead end, and the most important one (A1) is repaired at zero additional compute. The audit does **not** recommend APPROVED FOR IMPLEMENTATION, because A1–A7 would, as written, either stop the programme falsely, fail it on noise, or record the wrong membrane value.

## 2. Statistical audit

### 2.1 The 672-trial derivation, recomputed independently

The protocol's formula and arithmetic are correct:

| Table | df | N for floor ≤ 0.017 | Floor at N = 672 | Floor at N = 6,400 |
| --- | ---: | ---: | ---: | ---: |
| 4×4 primary | 9 | 382 | 0.009661 | 0.001014 |
| 4×3 | 6 | 255 | 0.006441 | 0.000676 |
| 4×5 Stage S | 12 | 510 | 0.012881 | 0.001353 |
| 6×4 sensitivity (binding) | 15 | 637 | 0.016102 | 0.001691 |

Recomputed with `(kx−1)(ky−1)/(2N ln 2)`: 9/(2·672·0.693147) = 0.009661; 6/931.6 = 0.006441; 12/931.6 = 0.012881; 15/931.6 = 0.016102. At N = 6,400: 0.001014, 0.000676, 0.001353, 0.001691. All match. Solving 15/(2N ln 2) ≤ 0.0167 gives N ≥ 647.9, so N ≥ 648. At N = 648 the floor is 15/(2·648·0.693147) = 0.016699, which still satisfies ≤ 0.0167. **The bias-floor conclusion is correct.**

Two things in the derivation are not correct:

1. **The stated reason for 672 is wrong.** §8.2 says "The smallest N that is a multiple of both 4 and 6, and therefore gives an integer number of trials per cell in both the 4-level primary and 6-level sensitivity tables, is 672." 648 is a multiple of 4 (162) and of 6 (108), and it is ≥ 648, so the sentence contradicts itself. The real constraint that forces 672 is **integer cell counts**, not integer level counts: the 4×4 table has 4 levels × 4 response levels = 16 cells, and the 6×4 table has 6 × 4 = 24 cells, so N must be a multiple of 48. The smallest multiple of 48 that is ≥ 648 is 672 (48 × 14); 648 is 13.5 × 48. **Exact correction:** replace the sentence with "N must be a multiple of 48 so that both the 4×4 primary and the 6×4 sensitivity tables have integer cell counts; the smallest multiple of 48 that satisfies N ≥ 648 is 672." The JSON `n_derivation` string needs the same change.
2. **The binding table is not the confirmatory table.** The confirmatory family in §9.1 is E1–E10; the 4×4 primary and 4×3 tables need 382 and 255 rows. The 6×4 table is a sensitivity analysis (§6.4 says it "is not the primary test"). So N = 672 is chosen by a **sensitivity** table plus an integer-cell convention, not by the confirmatory endpoints. That is a legitimate precision choice, but the protocol should say so. **Exact correction:** add one sentence: "The confirmatory 4×4 table requires only 382 rows; 672 is chosen to keep the 6×4 sensitivity table below the same floor and to give integer cells in both tables. It is a precision choice, not a requirement of the confirmatory family."
3. **The 4×5 Stage S row conflicts with the declared discretisation.** §9.2 defines the population code with **four** levels: `(0 active, 0 spikes)`, `(≥1 active, ≤ median)`, `(≥1 active, > median, ≤ 2× median)`, `(≥1 active, > 2× median)`. A 4×4 table has df = 9, not 12, and its floor at N = 6,400 is 0.001014, not 0.001353. Either the table is 4×4 and the row must be corrected, or a fifth level must be defined in §9.2. **Exact correction:** make the two sections agree. If the code is 4 levels, change the Stage S row to "4×4, df 9, 382, 0.009661 at 672, 0.001014 at 6,400" and change the JSON `tables[2]` accordingly.
4. **The 0.017/0.0167 rounding should be made explicit.** The table is calculated at 0.017 (which gives 637 for the 6×4), while the text uses 0.0167 (which gives 648). Both are defensible, but the table header should state the exact tolerance used and the text should not mix the two. **Exact correction:** label the column "N for floor ≤ 0.017" and add a footnote "the text criterion is 0.0167, which gives 648; 672 satisfies both."

### 2.2 Estimator bias is not statistical power

This is the distinction the audit was asked to enforce, and the protocol mostly makes it but not completely.

**What the bias floor guarantees.** It guarantees that the *expected upward bias* of the plug-in MI is at most one third of the declared MDE. It says nothing about the variance of the estimate, the probability of detecting a true effect, or the false-positive rate of a condition contrast. Passing the floor equation is necessary for a reportable estimate; it is not evidence of power.

**What the power calculation assumes.** §8.3 uses the asymptotic variance of the plug-in MI under independence: `SE = sqrt(2·df)/(2N ln2)`. At N = 672 the 4×4 SE is 4.243/931.6 = 0.004554 bits and the 6×4 SE is 5.477/931.6 = 0.005880 bits. The 0.05-bit MDE is 10.98 and 8.50 SEs, so the statement "power at α = 0.01 is effectively 1.0" is arithmetically true **for an iid multinomial table with 672 independent rows and no clustering**. Three corrections are needed:

1. **The rows are not all independent for the generalisation claim.** The trial-level rows are independent by construction (one noise draw per seed), but the event-cluster bootstrap exists precisely because the 672 rows are not 672 independent stimuli. A trial-level power calculation and an event-level generalisation claim are two different statements. The protocol should present the 11σ/8.5σ figure as the **trial-level** power and add a separate statement that the event-cluster CI can be much wider, with the cluster count and the per-level counts given correctly (see §2.5).
2. **The corrected estimator is not unbiased at the null.** The reported value is `max(0, Î − floor)`. At the null, `Î` is approximately half-normal around the floor with SD 0.004554, so `max(0, Î − floor)` has a positive mean of roughly 0.4 × 0.004554 ≈ 0.0018 bits. The endpoints that require "corrected MI > 0" (E5, E8, E9) would therefore pass at the null far more often than the nominal rate. **Exact correction:** for every endpoint whose criterion is "> 0", compare the corrected statistic to its own permutation null (the 95th percentile of `max(0, Î_perm − floor)`), not to zero. The corrected statistic may still be reported; it may not be used as a one-sided test against zero.
3. **The 80%-power figures use α = 0.05, not α = 0.01 or Holm.** §8.3 says "the smallest effect detectable with 80% power is about 0.013 bits (4×4) and 0.016 bits (6×4)". Those are 2.802 × SE, i.e. α = 0.05 two-sided. At α = 0.01 two-sided the 4×4 figure is 3.418 × 0.004554 = 0.0156 bits; at the Holm smallest threshold (α = 0.005) it is 3.649 × 0.004554 = 0.0166 bits. **Exact correction:** state the α used for each row and use the Holm threshold for the confirmatory family.

**Conclusion on 672.** The audit does **not** accept 672 as sufficient because it satisfies the bias-floor equation. It accepts 672 as sufficient for the **trial-level** 4×4 and 6×4 estimators, and rejects the implied claim that 672 trials buy generalisation to the stimulus corpus, because the corpus is 24 tracks, not 43 events, and one level has one track.

### 2.3 Independent seeds versus trials

The protocol's independence table (§8.1) and the Stage R design (§6.3) contradict each other:

- §8.1: "Seed (one stochastic simulation run) — 2,688 unique seeds."
- §6.3: "each trial re-uses the same seed across conditions (a paired design at the noise level)."
- §8.1: "Trial (one 300 ms simulation) — 2,688."
- §6.3: 672 trials per condition × 4 conditions = 2,688 runs.

If the same seed is reused across the four conditions, there are **672 unique seeds**, each contributing four condition-runs. The correct table is:

| Level | Stage R count | Stage S count | Valid as n for |
| --- | ---: | ---: | --- |
| **Seed** | **672** (reused across 4 conditions) | **40** (episode streams on one substrate) | Paired condition contrasts; cluster bootstrap |
| **Condition-run** | **2,688** (672 × 4) | 19,200 episodes | Descriptive run counts |
| **Trial** | **672 per condition** | 240 per seed per condition | Stimulus-locked response comparisons |
| **Stimulus track** | **24** (13 / 11 / 5 / 1 per level) | 4 cues | Generalisation of H2/H3 |
| **Neuron** | 232–5,731 | 36 | Descriptive only |
| **Time bin / decoder window** | 30 bins / 5 windows | — | Descriptive only |
| **Spike** | ≈15,000 per trial | varies | Descriptive only |

**Exact correction:** change the seed row to 672, add a condition-run row of 2,688, and change the "Not valid for" column for seed from "—" to "generalisation beyond the 672 simulated trials". The JSON `independence_units.seed.stage_r` must change from 2688 to 672, and `trial.stage_r` should be described as "672 per condition; 2,688 condition-runs".

**Stage S seeds are not independent substrates.** Phase 5F used `substrate_seed = 20261114` for all ten cells of both `fixed_complete` and `plastic_complete` (`experiments/results/phase_5f/comparison_raw.json`). The "seed" varies the episode seed stream, not the 36-node graph or its initial weights. Stage S's 40 "seed clusters" would therefore resample episode streams on **one** substrate. A cluster bootstrap over them does not cover substrate or initial-weight uncertainty. **Exact correction:** either (a) generate 40 independent substrate seeds for Stage S and say so, or (b) state in §6.6 and §12 that the 40 clusters resample episode-level stochasticity on one fixed substrate, and that substrate uncertainty is not covered by the CI. Option (a) is cheap on a 36-node graph and is the better choice if H6 is kept.

**"Reproduction" at 40 seeds is a new replicate.** Phase 5F's 10 seeds are 10 episode streams. Stage S's 40 seeds are not the same list unless the original 10 are included. §9.2 step 5 says "Phase 5F contrast reproduced at 40 seeds"; that is not a reproduction. **Exact correction:** either include the original 10 seed streams as a pre-registered subset and test the contrast on that subset, or relabel the check as "the Phase 5F direction is re-estimated on a new 40-stream replicate" and drop the word "reproduced". C6 should say "same seed list as `plastic_complete`" only within Stage S, which it already does.

### 2.4 Within-trial temporal dependence

The protocol's own rule is correct: §8.1 says a time bin is "never an independent replicate". Three endpoints violate it:

1. **E8** uses `672 trials × 5 windows` as its unit. The five 50 ms decoder windows are sequential summaries of the same trial and are strongly dependent. `n = 3,360` is not 3,360 independent observations. **Exact correction:** define the estimand at the trial level (e.g., the decoded state in the first post-stimulus window, or a single trial-level summary such as "any non-NEUTRAL window"), or keep the stacked 3,360-row estimate but compute the CI by resampling whole trials (all five windows together) and report the effective n as 672. Never report a p-value with n = 3,360.
2. **E9** uses "Decoder windows" as its unit. It is labelled descriptive, which is better, but the MI point estimate and its bias floor are still computed over 3,360 correlated rows. **Exact correction:** report the estimate descriptively with a trial-clustered bootstrap, state the effective n, and do not attach a p-value.
3. **E7** uses "DESC spikes" as its unit. A trial with 20 DESC spikes contributes 20 rows, so a single trial can dominate the proportion. The protocol says "trial-clustered proportion", which is the right instinct, but the unit column still says DESC spikes. **Exact correction:** make the unit the trial; compute a per-trial proportion (or a per-trial binary "any DESC→MOT pair within the window"), then compare across trials with a paired test. Report the spike-level count descriptively.

**Bin alignment.** `SpikeRecorder.record` stamps `(step_index + 1) * dt_ms` (`brain/neural_activity.py:59–73`), so the first step's spikes are at 0.5 ms, not 0. The 10 ms bins and the 50 ms decoder windows must state whether they start at 0 or 0.5 ms. The decoder's half-open 50 ms windows and the 10 ms bins are not aligned unless this is specified. **Exact correction:** state the time base in §9.2 and in field 16.

### 2.5 Clustered bootstrap and permutation requirements

**The stimulus corpus is 24 tracks, not 43 events.** The archive `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` has 215 events, 43 of which carry `feature_values`. Those 43 records come from **24 distinct `(class_name, track_id)` pairs**. Counts by the protocol's 4-level code:

| Level | Event records | Distinct tracks |
| --- | ---: | ---: |
| `TRAIN_NEAR` | 20 | 13 |
| `TRAIN_FAR` | 15 | 11 |
| `OBST_NEAR` | 2 | **1** (`jump-roll-barrier`, track 11) |
| `OBST_FAR` | 6 | 5 |
| **Total** | **43** | **24** |

Event times run from 66.6667 to 3266.6667 ms. The 43 records include repeated frames of the same track (one train track contributes 5 records). **Exact corrections:**

- §6.4: replace "only 43 of the 215 events ... carry `feature_values`" with "43 of the 215 event records (from 24 distinct tracks) carry `feature_values`".
- §6.4: replace "`OBST_NEAR` has only 2 distinct events and will repeat them 84 times each" with "`OBST_NEAR` is a single track observed at two frames; 168 `OBST_NEAR` trials repeatedly sample one track, so the effective stimulus sample for that level is one."
- §8.1: replace "43 distinct events (2 / 6 / 15 / 20 per level)" with "24 distinct tracks (1 / 5 / 11 / 13 per level)".
- §8.6: resample **tracks**, not event records: 24 clusters (13 `TRAIN_NEAR`, 11 `TRAIN_FAR`, 5 `OBST_FAR`, 1 `OBST_NEAR`). With one `OBST_NEAR` track the CI is not estimable; report that level descriptively and remove it from any generalisation claim.
- §8.7: replace "the corpus has 43" with "the corpus has 24 distinct tracks"; replace "repeating two obstacle-near events 84 times each has an effective stimulus sample of two" with "repeating one obstacle-near track 168 times has an effective stimulus sample of one."
- The JSON `sample_size.independence_units.stimulus_event` must gain `distinct_tracks: 24` and per-level track counts.

**The within-seed pairing requires paired tests.** Because Stage R reuses one seed across the four conditions, the condition contrasts (E3, E4, E5, and the P gates) are paired at the noise level. The protocol currently specifies unpaired Fisher and Mann–Whitney tests and a trial-level *stimulus-label* permutation. Those test different nulls:

- A trial-level permutation of the stimulus code answers "is the observed MI larger than expected under no stimulus-response association?" It does **not** answer "is `I_REAL` larger than `I_SHUFFLED_MASK`?"
- The condition contrast needs a **paired condition-label permutation** (swap `REAL` and `SHUFFLED_MASK` within each seed, 5,000 draws, recompute both MI estimates) or a **seed-cluster bootstrap of the difference** (resample the 672 seeds, recompute pooled MI in both conditions, take the difference).
- E3 and E1 are paired binary outcomes; McNemar's test (or a paired permutation) is the matched test, not Fisher against pooled controls.

**Exact correction:** in §9.1 and §9.2, separate the two nulls: (a) the label-permutation null for "MI > chance", and (b) the paired condition-label permutation or seed-cluster bootstrap for "condition A > condition B". E4/E5 must use (b) for their stated direction and (a) for the "> 0" component. E1/E3 should use a paired test; if the protocol wants to keep Fisher, it must pool only the independent control arms and state that the pairing is discarded, which costs power.

**The zero-control rule is brittle.** P2 requires "0 of 40" control trials with any downstream spike. If the true control rate is 0.5%, the probability of at least one control spike in 40 is 1 − 0.995^40 = 18.1%; at 1% it is 33.1%; at 2% it is 55.4%. A gate that fails on a single chance control spike is not a statistical test; it is a coincidence detector. The same applies at the four-drive level, where 160 control trials would give a 55% chance at 0.5%. **Exact correction:** replace "0 of 40" with a pre-registered tolerance, e.g. "≤ 2 of 40 control trials", and use the pooled control upper 95% bound (Clopper–Pearson) as E3's threshold. State the bound at the time of the gate decision. If the protocol wants a strict zero rule, it must justify why a 0.5% control rate is scientifically impossible; Phase 4H's controls were zero because they were subthreshold (see §3.2), not because the simulator is noise-free.

**The gate multiplicity is uncontrolled.** P1 is evaluated at four drives. Four one-sided Fisher tests at α = 0.01 give a family-wise false-positive rate of up to 4% if the tests were independent; they are positively correlated because the drive series is monotone, but the protocol does not state the control. The four tests are not in the Holm family. **Exact correction:** use a fixed-sequence gate (test 1200 pA first, then 800, then 400, then 200, stopping at the first pass) or Bonferroni α = 0.0025 per drive. The fixed-sequence version is preferable because the drives are ordered and it preserves the "lowest passing drive" logic.

### 2.6 The P1 power claim does not describe the P1 gate

§6.2 says "At n = 20 per group, a one-sided Fisher test of 50% versus 5% has power 0.80 at α = 0.01; at n = 10 the same test has power 0.28." The Fisher-only calculation is correct: exact enumeration (verified with `scipy.stats.fisher_exact`) gives 0.8029 at n = 20 and 0.281 at n = 10. **But the gate is not the Fisher test alone.** P1 requires all three of:

1. at least 10 of 20 `REAL` trials with ≥ 1 H1 spike;
2. each control arm at most 1 of 20;
3. the Fisher test p < 0.01.

Under 50% vs 5%, the exact probability of the full conjunction is P(Bin(20, 0.5) ≥ 10) × P(Bin(20, 0.05) ≤ 1)² = 0.5881 × 0.7358² = **0.318**, not 0.803. Under a 0% control rate (the expected case) it is 0.588. At a 2% control rate it is 0.520. At n = 10 the conjunction is 0.623 × 0.9139² = 0.520 — *higher* than at n = 20, because the fixed "≥ 10 of 20" floor is more stringent than the Fisher test at n = 20. The gate's power is therefore **non-monotonic in n** and is not the 0.803 quoted.

**Exact correction:** either (a) remove the fixed "≥ 10 of 20" floor and define P1 by the Fisher test plus a pre-registered minimum difference in proportions (which makes the power calculation match the gate), or (b) keep the floor and report the conjunction's operating characteristics, not the Fisher-only 0.803, and increase the number of trials if 0.32 is unacceptable. The cleanest fix is (a): P1 passes if the one-sided Fisher p < 0.0025 (Bonferroni over four drives) and the observed `REAL` proportion exceeds the pooled control proportion; the "≥ 3 of 20" style screen is retained for P2, where it is explicitly a screen.

The P2 screen's stated operating characteristics are correct: P(X ≥ 3) = 0.794 at q = 0.20, 0.965 at q = 0.30, 0.075 at q = 0.05. The audit accepts these as a screen, not a test. The audit does **not** accept the claim that a miss at q = 0.20 is solely "a known cost of not spending more compute": with the zero-control rule, the effective pass probability is 0.794 × P(0 control spikes) = 0.794 at a 0% control rate, 0.669 at 1%, 0.531 at 2%. The control rule materially reduces the screen's sensitivity, which is another reason to allow ≤ 2 of 40.

### 2.7 Stage S power is below the declared MDE

This is the most important statistical finding after the gate issues. Phase 6C measured the per-seed paired difference in `I(cue ; action)` between `plastic_complete` and `fixed_complete` over 10 seeds: mean −0.0863 bits, SD 0.1581 bits (`experiments/results/phase_6c/mutual_information_results.json`, `C06_fixed_vs_plastic.contrasts.complete.summary.sd`). Using that SD as the best available between-seed variability:

| Quantity | Value |
| --- | ---: |
| SD of the paired difference (Phase 6C, 10 seeds, 40 eval episodes/seed) | 0.1581 bits |
| SE of the mean difference at 40 clusters | 0.0250 bits |
| 80%-power MDE at 40 clusters, α = 0.05 two-sided | **0.0700 bits** |
| 80%-power MDE at 40 clusters, α = 0.005 (Holm smallest) | **0.0912 bits** |
| Seeds needed for a 0.05-bit MDE, α = 0.05 | **79** |
| Seeds needed for a 0.05-bit MDE, α = 0.005 | **134** |

The protocol's E10 criterion is "a paired cluster-level difference ... exceeds 0.05 bits in the plastic > fixed direction" (§10.7). At 40 seeds the design cannot detect 0.05 bits at 80% power; it can detect ≈0.07. The Stage S "positive" criterion is therefore below the design's own MDE. The observed Phase 6C direction was −0.086 bits, i.e. the wrong direction, and the sign-flip p was 0.125; the protocol is planning a 40-cluster study of an effect that has already been estimated as negative in the only available sample.

**Exact correction:** either (a) increase Stage S to at least 79 seed clusters (134 if the Holm threshold is used), or (b) re-declare the cluster-level MDE as 0.07 bits and change the E10 positive criterion to "> 0.07 bits", or (c) demote E10 to exploratory and remove it from the confirmatory family. Option (a) is preferred if H6 is in scope; option (c) is the honest choice if the 40-seed budget is fixed. The protocol must also state that the 0.1581-bit SD is a **proxy** from `I(cue ; action)`, not from `I(cue ; A_neural)`; the neural-code variability may be larger, so the 0.07 figure is a lower bound on the MDE. If the 80-eval-episode change reduces the within-seed sampling component, the SD may fall to ≈0.139 bits and the MDE to ≈0.061 bits; even then 40 seeds do not reach 0.05. The protocol should compute the SD from a pilot or from the 5F/6C archives before fixing the seed count, not assume 40 is enough because it is 4× 10.

### 2.8 What 672 trials do and do not buy

The protocol's own §8.7 is the right framing, and the audit endorses it with corrected numbers:

- 672 trials buy precision on the simulation-noise dimension and on the four stimulus levels: 168 rows per primary level, 42 rows per 4×4 cell, 28 rows per 6×4 cell.
- They do **not** buy 672 independent stimuli. The corpus has 24 distinct tracks, and `OBST_NEAR` has one. A `OBST_NEAR` effect describes one track, not obstacle proximity.
- They do **not** buy event-level generalisation for H2/H3. The event-cluster bootstrap must resample 24 tracks, and the `OBST_NEAR` cell is not estimable.
- They do **not** buy Stage S power. Stage S is a different substrate with 40 clusters and a different MDE (0.07 bits, not 0.05).
- They do **not** buy a valid "corrected MI > 0" test, because the corrected estimator is positively biased at the null (see §2.2).

## 3. Experimental design audit

### 3.1 The seven distinctions, one by one

The protocol's §6.1 lists six distinctions; the audit adds "direct sensory-neuron activation" as a seventh because H1 is stated as "sensory input to stimulated sensory-neuron activity" but no gate measures the 232 stimulated sensory neurons. (The 607-neuron H1 population is the first-hop target, not the stimulated set.)

| # | Distinction the design must separate | Condition(s) that separate it | Does the design do it? | Gap and exact correction |
| --- | --- | --- | --- | --- |
| 1 | **Direct sensory-neuron activation** — do the 232 stimulated neurons fire? | `REAL` vs `NO_STIM` at each drive | **No explicit gate.** P1 reads H1 (first-hop), not STIM. The `DIRECT_INJECTION` control bypasses the encoder and cannot answer this. | Add **P1a**: at some drive, ≥ 10/20 `REAL` trials have ≥ 1 STIM spike, each control ≤ 1/20, Fisher p < 0.0025 (four-drive corrected). If P1a fails but `DIRECT_INJECTION` succeeds, report a drive/encoder failure. |
| 2 | **First-hop propagation** — does the 607-neuron H1 population spike? | `REAL` vs `NO_STIM`/`MATCHED_CHARGE`; `DIRECT_INJECTION` positive control | **Partially.** P1 reads H1, but its power is misstated (§2.6) and the direct-injection arm is 80 runs in §6.2 but 40 in C4. | Fix the power claim; fix the 80-vs-40 inconsistency; keep `DIRECT_INJECTION` as a positive control only. |
| 3 | **Second-hop propagation** — does H2 spike? | P2 on `H2 ∪ DESC` | **No.** The union can pass on descending spikes, and 9 DNs are first-hop targets. | Split **P2a** (H2 only) from **P2b** (DESC). P2a is the second-hop gate. |
| 4 | **Descending recruitment** — do DNs spike beyond the first hop? | P2 union | **No.** The 9 first-hop DNs are included. | **P2b**: `DESC \ first_hop_DESC` (exclude the 9 directly innervated DNs; the other 1,307 are available). Require ≥ 1/20 `REAL`, controls ≤ 2/40. |
| 5 | **Motor recruitment** — do MOT neurons spike? | P3 decoder reachability | **No.** P3 is a decoder gate; the decoder can be non-NEUTRAL on 3 active neurons in a 50 ms window and is not a motor-spike measurement. The protocol itself says H4/H5 are likely untestable (0 first-hop motor targets, 4 motor neurons at two hops). | Add **P3a**: at least one MOT spike in `REAL`, none in controls, reported separately. Label P3 as decoder reachability, not motor recruitment. If P3a fails, H4/H5 are untestable regardless of P3. |
| 6 | **Stimulus-specific information** — is the response feature-specific rather than generic? | `SHUFFLED_MASK` in Stage R | **Not in the pilot.** Stage P has no `SHUFFLED_MASK`, so a non-specific P2 can pass before the campaign. In Stage R, the `SHUFFLED_MASK` description is wrong (see §3.2). | Add **P2s**: 20 `SHUFFLED_MASK` trials at each drive (80 runs), with the same seeds as `REAL`; require `REAL` > `SHUFFLED_MASK` (paired test) or report the propagation as non-specific and remove the specificity claim. |
| 7 | **Coincidental spontaneous activity** — is the response above baseline? | `NO_STIM` | **Yes, but the bound is not stated.** At `noise_std_pa = 50` and rheobase 150 pA, `NO_STIM` is expected to be silent; Phase 4H's `A_no_events` and `G_background_noise` produced 0 spikes. With 80 control trials, the rule-of-three upper 95% bound is 3/80 = 3.75%, not 0. | State the bound; use it to set E3's threshold; do not claim the control rate is exactly zero. |

### 3.2 Are the controls appropriately matched?

| Control | What it matches | What it does not match | Verdict |
| --- | --- | --- | --- |
| `NO_STIM` | Same seed, noise draw, background, decoder, trial length | Nothing relevant; it is the baseline | **Adequate** |
| `MATCHED_CHARGE` | Aggregate injected charge | **Peak current and temporal envelope.** `ConstantChargeDrive` sets `current_pa = total_charge / (n_neurons × duration_ms)` (`brain/banc_sensory_adapter.py:779–860`). With 232 neurons and 300 ms, a typical total charge gives ≈20 pA per neuron, far below the 150 pA rheobase. Phase 4H condition F (`F_constant_matched_charge`) produced 0 spikes over 3,300.5 ms. | **Not a charge control.** It is a "did we inject enough total charge to fire at all" floor. A zero result is guaranteed by construction and says nothing about whether a matched-charge *peak* would propagate. **Correction:** add a **peak-matched rectangular** control (200 pA for 100 ms on the same 232 neurons) or demote `MATCHED_CHARGE` to descriptive and remove it from the P2 control count. |
| `SHUFFLED_MASK` | Event timing and the multiset of feature payloads | **Per-trial charge** and the feature→population mapping. `shuffle_feature_identities` permutes feature-value payloads across events (`brain/banc_sensory_adapter.py:883–903`); it does not permute the feature→population mapping, and because each trial uses one event, the per-trial payload (and charge) changes. The protocol's description "feature→population identity permuted" is wrong. | **Partially matched.** It tests whether the *pairing of feature value to event time* matters, not whether the *mapping* matters. **Correction:** either re-describe R2 as "feature payloads permuted across event times" and adjust the interpretation, or implement a true feature-block permutation of the mapping (preserving per-trial charge) and use `shuffle_feature_identities` as a separate temporal-payload control. Pair each `REAL` trial with a `SHUFFLED` trial whose payload magnitude is matched. |
| `DIRECT_INJECTION` | Same drives, same H1 target set, same trial length | Bypasses the sensory encoder; injects into H1 rather than STIM; does not reproduce the spatial/temporal pattern of the encoder | **Adequate as a positive control, not as evidence of natural propagation.** This is the audit's most important design caution: a positive direct-injection result proves the H1→H2 synapse can transmit under artificial current; it does not prove that the natural sensory drive propagates. **P2a on `REAL` is the only propagation evidence.** If direct injection passes and `REAL` fails, the conclusion is a drive/encoder failure, not propagation. |
| `SINGLE_H1_SPIKE` | One H1 neuron, exactly one spike, 5 ms search | The choice of neuron is arbitrary ("lowest local index that receives ≥ 99% of the maximum first-hop current"); one neuron is not the population | **Calibration only.** A positive result calibrates the minimum transmissible event; a null is informative but not fatal. It cannot establish population propagation. The 5 ms window should be accompanied by 10 ms and 20 ms sensitivity because `tau_m = 20 ms` and the synaptic delay is 1 ms; a single synaptic event is far below threshold, and the 5 ms choice is a coincidence window, not a physiological latency. |
| `C8` archive replay | The archived 4H condition-B event stream and `spike_sha256` | Nothing; it is the strongest instrumentation check | **Adequate and mandatory.** Keep it. |

**The "conditions differ only in the drive" claim is false for `SHUFFLED_MASK`.** §6.3 says all four conditions "differ only in the drive". `SHUFFLED_MASK` also changes the payload and hence the per-trial charge; `MATCHED_CHARGE` changes the spatial and temporal current pattern; `NO_STIM` has no schedule. **Exact correction:** say "they share the trial length, seed list, noise schedule and decoder; they differ in the current schedule, and `SHUFFLED_MASK` additionally changes which feature payload occurs at which event time."

### 3.3 The `d*` stop rule is not safe

The current rule (§6.2) is: P1 is evaluated "at some drive"; `d*` is the **lowest** drive meeting P1, fixed before H2 is examined; P2 is evaluated **only at `d*`**; if P2 fails, the programme stops. §10.4 says P2 fails "at every drive up to 1200 pA", which the gate does not test. This is a false-negative machine:

- If the true propagation threshold is 800 pA but the H1 threshold is 200 pA, P1 passes at 200 pA, `d*` = 200 pA, P2 fails at 200 pA, and the programme stops — even though P2 would pass at 800 pA.
- The 240 Stage P runs already contain `REAL`, `NO_STIM` and `MATCHED_CHARGE` at all four drives. Reading H2/DESC from those same runs at 400, 800 and 1200 pA costs **zero additional simulations**.
- The negative result in §10.4 would then be true: "P2 fails at every tested drive".

**Exact correction:** evaluate P1a, P1, P2a, P2b and P2s at **all four drives**; set `d*` to the **lowest drive at which both P1a/P1 and P2a/P2b pass**; report P2 at every drive; stop only if no drive up to 1200 pA passes P2a/P2b. Change §10.4 to "P2 fails at every tested drive (200, 400, 800, 1200 pA)". This also removes the incentive to tune the drive to the downstream result, because the drive is selected by P1/P2 jointly and the whole series is reported.

### 3.4 The stimulus cannot be constructed as written

This is the feasibility defect that most directly blocks Stage P and Stage R:

- The archived events with feature values are timestamped 66.6667–3266.6667 ms (`experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`).
- The Stage R trial is 300 ms with `stimulus_onset_ms = 50.0` and `stimulus_offset_ms = 150.0` (§5.1 field 10; §6.2).
- `BancEventDrive` uses the event's `time_ms` as the onset and applies the pulse when `onset ≤ time_ms < onset + decay_ms` (`brain/banc_sensory_adapter.py:532–700`). An event at 1500 ms never fires in a 300 ms trial.
- The protocol does not say how the 43 event records are mapped into the 300 ms window.

**Exact correction:** add a declared event-time transform to §6.4 and field 9, e.g. "every selected event is re-based to `time_ms = 50.0`; the original archive time and the transform are recorded in field 9." Alternatively, use a 3,300.5 ms trial (which would change the runtime, storage and the 10 ms bin count) or clip the event stream to [0, 300] ms and declare how many events are lost. The first option is simplest and preserves the 300 ms trial. It must be frozen before Stage P.

**The "offset 150 ms" is not a cutoff.** `BancEventDrive` decays linearly over `decay_ms = 150` (the config has `duration_ms: 3300.5`, `decay_ms` default 150). An event at 50 ms therefore delivers current until 200 ms, not 150 ms. **Exact correction:** either set `decay_ms = 100` so the current ends at 150 ms, or define "offset" as the nominal event offset and state that the drive decays for 150 ms and the readout [50, 300) includes the tail. The audit prefers the former because it makes the stimulus description match the implementation.

**The 4-level code's per-level counts are event records, not tracks.** §6.4's "168 trials per level" and the round-robin over the "sorted event list" will assign 168 `OBST_NEAR` trials to two records from one track. The trial-level estimate is still computable, but the level's effective stimulus sample is one. **Exact correction:** state this in §6.4 and remove `OBST_NEAR` from any confirmatory stimulus-generalisation claim; report it descriptively.

### 3.5 Stage S design

The arithmetic is correct: 40 × 2 × (160 + 80) = 19,200 episodes; 40 × 2 × 80 = 6,400 evaluation rows. The `eta = 0` evaluation after the checkpoint is the right way to avoid the evaluation changing the weights, and C7's hash check is the right integrity test. The defects are:

1. **Power (A5, §2.7).** 40 clusters give an MDE of ≈0.07 bits, not 0.05.
2. **Substrate sharing (§2.3).** The 40 streams share one substrate; the cluster CI does not cover substrate uncertainty.
3. **Reproduction wording (§2.3).** 40 new streams are a new replicate, not a reproduction of Phase 5F.
4. **The `fixed_complete` description.** §6.6 says it is "the Phase 5F fixed-weight control with the same substrate, seed list and evaluation protocol." Phase 5F used 10 seeds and 40 eval episodes; Stage S uses 40 seeds and 80 eval episodes. It is the same *protocol family*, not the same seed list. **Exact correction:** say "same substrate and protocol family; 40 new episode streams, 80 evaluation episodes per stream."

## 4. Recording architecture audit

### 4.1 Verified interfaces and the facts that constrain the recorder

| Component | File:line | Verified behaviour | Consequence for the recorder |
| --- | --- | --- | --- |
| `LIFPopulation.step` | `brain/neuron_model.py:122–157` | Integrates, then `self._V[spikes] = params.reset_potential_mv` at line 154, then returns `np.flatnonzero(spikes).astype(np.int32)` at line 157. | After `step`, a spiking neuron's `membrane_potential` is **−68 mV**, not threshold. A recorder that samples `_V` after `step` must substitute `threshold_mv` for the spiking indices, exactly as `experiments/phase_4h/analyse_sensory_roundtrip.py:828` does (`max_v[spikes] = threshold_mv`), or sample before the reset. |
| `SpikeRecorder` | `brain/neural_activity.py:59–73` | Preallocated `float32` times and `int32` indices; `record` stamps `(step_index + 1) * dt_ms`; raises `SpikeCapacityExceeded` rather than truncating. | The first spike is at 0.5 ms, not 0. The 10 ms bins and 50 ms decoder windows must state their alignment. Capacity is a hard failure, not a silent drop. |
| `SpikeRecorder.spike_counts` | `brain/neural_activity.py:75–79` | Allocates a full `n_neurons` `int64` array (1.38 MB for 172,433). | Call it once per trial, not per step. |
| `BancSimulator.run` | `brain/banc_simulator.py:393–480` | Local `rng = np.random.default_rng(self.seed)` at 404; one `rng.normal` per step at 456; `input_schedule.apply` at 464; `neurons.step(current)` at 470; `recorder.record` at 475; `synapses.propagate(spikes)` at 480. **No callback.** | The only hook is an instance-level wrapper on `sim.neurons.step`. The wrapper must not consume the RNG or reorder these calls. The noise draw is one per step and is independent of the condition, so the paired-seed design is technically valid. |
| `BancSignedSynapses.excitatory_current_pa` | `brain/banc_simulator.py` (property) | Returns the live `_exc` array. | Any recorder that retains it must `.copy()`; otherwise it records a mutated trace. `synaptic_current_pa` computes `_exc − _inh` into a new array each call, so it is safer, but a retained reference to the result is still a new array (fine). |
| `BrainSimulator` | `brain/brain_simulator.py:264` | Calls `self.recorder.record(step, spikes, self.dt_ms)`; no callback. | Cannot be used on BANC (`BancConnectome` lacks `vocabulary`/`nt_code`). The BANC path must use the `BancSimulator` wrapper. |
| `PlasticSimulator.step_callback` | `plasticity/plastic_simulator.py:298–319` | Called **after** `engine.observe_step`; its return value, if not `None`, becomes the reward and bypasses `reward_provider`. | A recording callback must return `None`. It must not call `engine.learn` or mutate `WeightState`. It may read `self.neurons._V`, `self.synapses`, and `self.engine` traces, but must copy anything it retains. |
| `analyse_sensory_roundtrip` wrapper | `experiments/phase_4h/analyse_sensory_roundtrip.py:816–832` | Saves `original_step`; defines `step(current)`; calls `original_step(current)`; updates `max_v` with `np.maximum` and substitutes threshold; returns `spikes` unchanged; assigns `sim.neurons.step = step`. | This is the proven pattern and the basis for G2's hash check. It is a **maximum** recorder, not a trajectory recorder; O2 needs a different sampling rule. |

### 4.2 Required instrumentation contract

The new `experiments/phase_6d/recording.py` must satisfy all of the following. These are not suggestions; they are the conditions under which the recorder cannot change the simulation.

1. **Call the original step exactly once and return its result unchanged.** Do not re-run `step`, do not threshold, do not reset, do not alter `spikes`.
2. **Consume no random numbers.** No `np.random.*` global calls, no `sim` RNG access, no `default_rng` inside the per-step wrapper. The 5,000-permutation analysis has its own `default_rng(20261110)`; the simulation recorder must not touch it.
3. **Copy every array it retains.** `_V`, `_exc`, `_inh`, eligibility traces, and `last_active_edges` are mutated in place or overwritten each step. A reference is a bug.
4. **Substitute threshold for spiking neurons, or sample before the reset.** Record `threshold_mv` for the indices returned by `step`, not the post-step `_V[spikes]` = −68 mV. If the recorder samples a trajectory, state whether the sample is pre-step or post-step and how spikes are represented.
5. **Do not mutate the simulator's inputs or state.** No writes to `current`, `spikes`, `_V`, `_exc`, `_inh`, the synapse delay buffers, the weight state, or the RNG.
6. **Install and restore in `try/finally`.** Assert that `sim.neurons.step` is the wrapper before `run()`; restore the original in `finally`; refuse a double install; make a second install a loud error rather than a nested wrapper.
7. **Use one recorder.** `BancSimulator.run` already calls `sim.recorder.record` at line 475. The wrapper must not call `record` again or create a second recorder that consumes the same spikes. Read from the simulator's recorder after the run, or keep a separate bounded array that is not the simulator's.
8. **Respect capacity.** At the declared 500,000-spike cap the recorder is 4 MB (8 B per spike). The planning value is 15,000 spikes/trial; a runaway trial must raise `SpikeCapacityExceeded`, be recorded as a failed trial, and not be silently truncated. One `spike_counts()` call per trial.
9. **Stage S callback returns `None`.** Otherwise it silently replaces the reward. The callback must not call `engine.learn`, must not change `WeightState`, and must copy the traces it retains.
10. **State the time base.** Spikes are stamped at `(step + 1) × 0.5 ms`; bin 0 is [0, 10) or [0.5, 10.5) must be declared; the decoder's half-open 50 ms windows must be aligned to the same base.
11. **Pre-register the O2/O3 panel selection.** "Up to 200 first-hop" is not a selection rule. If O2/O3 are enabled, the panel must be chosen by a rule fixed before Stage P (e.g., the 200 first-hop neurons with the largest mean input current in the 4H archive, ties by local index) and written into field 8/24.
12. **No production module edits.** The wrapper lives in `experiments/phase_6d/`; G2 must show `git status` limited to the three new paths and the config, and the README hash unchanged.

### 4.3 Mandatory regression tests

The protocol's §11.3 lists six tests. Those are necessary but not sufficient. The audit requires the following twelve; the first three are the ones that make the recording trustworthy.

| # | Test | Pass condition |
| --- | --- | --- |
| T1 | **Recording on/off spike hash** | For an archived 4H condition (C8, condition B), `spike_hash(result.recorder)` with the wrapper enabled equals the archived hash and the no-wrapper hash. |
| T2 | **Recording on/off repeat** | Two runs with the wrapper enabled produce byte-identical records; one run with the wrapper disabled produces the same spike hash. |
| T3 | **Zero RNG consumption** | A run with a no-op recorder and a run with the real recorder, same seed, produce identical spike hashes; the recorder never calls `np.random.*` (assert by monkeypatching the global functions or by a seeded dummy that records calls). |
| T4 | **`LIFPopulation.step` contract** | A test asserts the signature is `(self, current_pa)` and the return is an integer index array; if the class changes, the test fails loudly with a message pointing to the wrapper. |
| T5 | **Copy-on-record** | Record `_V`/`_exc`; mutate the simulator arrays; the stored record is unchanged. |
| T6 | **Threshold representation** | A neuron that spikes is recorded at or above threshold (or the pre-step voltage is recorded); the stored value is not −68 mV for a spiking neuron. |
| T7 | **Capacity** | A synthetic over-capacity run raises `SpikeCapacityExceeded`; the trial is marked failed; no partial record is analysed. |
| T8 | **Time base** | The first spike's recorded time is 0.5 ms for a step-0 spike; the bin edges and decoder-window edges match the declared base. |
| T9 | **Plastic callback neutrality** | A Stage S run with a recording callback that returns `None` has the same reward, weight trajectory and spike hash as a no-callback run; a callback that returns a number changes the reward, proving the test is sensitive. |
| T10 | **Install/restore** | An exception inside `run()` restores `sim.neurons.step`; a second install raises; the wrapper is not left installed. |
| T11 | **No production edits** | `git diff --name-only` is restricted to `experiments/phase_6d/`, `configs/phase_6d_recording.yaml`, and `tests/test_phase_6d_recording.py`; the README hash is unchanged. |
| T12 | **Memory bound** | The O1 full-population trajectory is rejected by a guard; the O2 panel buffer is allocated once per run and is ≤ the declared size (458 × 150 × 4 B ≈ 275 kB per trial). |

**The 4H wrapper is not a sufficient template for O2.** It records per-neuron maxima over the whole run, not a trajectory. O2 says "At 2 ms sampling over 300 ms: 458 × 150 × 4 B". A 2 ms sample of `_V` can miss a one-step spike entirely and will record the reset value if it lands on a spiking step. The recorder must either (a) substitute threshold at the sampled step, or (b) record the pre-step `_V` and the spike indices, and document which. The protocol's O2 row must be amended accordingly.

### 4.4 Determinism risks the protocol does not yet address

1. **The monkeypatch is instance-level.** If `BancSimulator` ever creates a new `LIFPopulation`, or calls `LIFPopulation.step` through a class reference, the wrapper is bypassed silently. T4 is the guard.
2. **Float accumulation order.** The wrapper's `np.maximum` and any trajectory buffer add reads, not writes, but the order of reads must not force a copy or a dtype conversion that changes the simulator's arrays. Keep the recorder's buffers separate and of a declared dtype.
3. **The 4H wrapper uses `sim.synapses.synaptic_current_pa`, which allocates a new array each call.** That is safe for aliasing but adds an allocation per step; the new recorder should use the same property or copy `excitatory_current_pa`. Do not cache the live `_exc`.
4. **The archived 4H hash is the only end-to-end anchor.** The protocol should add at least one more archived condition (A, F, G are all-zero and are weak anchors; B is the strongest). Add a second non-zero condition (C or D) as a second hash fixture if the archive has it. The diagnostics JSONL has B, C, D, E for `full_100_199`; use B and C.
5. **The 5% determinism re-run is a sample, not a proof.** It catches non-determinism but not a systematic recorder bias. T1–T3 are the systematic checks; the 5% re-run is the operational check.

## 5. Pilot feasibility

### 5.1 What the pilot can and cannot establish

| Stage | Can establish | Cannot establish |
| --- | --- | --- |
| P0 integrity | The recorder reproduces the archived hash, records all mandatory fields, and does not truncate. | Anything scientific. |
| P1a (STIM) | The 232 stimulated sensory neurons spike under the drive. | That the drive is the natural sensory code; it is a synthetic pulse. |
| P1 (H1) | First-hop propagation from STIM to H1. | That the propagation is feature-specific (no `SHUFFLED_MASK` in Stage P as written). |
| `DIRECT_INJECTION` | The H1→H2 synapse can transmit under artificial current. | **Natural sensory propagation.** This is the audit's explicit caution: direct first-hop stimulation must not be treated as proof of natural sensory propagation. |
| P2a (H2) | Second-hop propagation, if H2 is read alone. | That the H2 spikes are not driven by the 9 first-hop DNs (they are not in H2, so P2a is clean) or that they are feature-specific (P2s is needed). |
| P2b (DESC) | Descending recruitment beyond the 9 first-hop DNs. | That the descending spikes reach motor neurons (P3a is needed) or that they are behaviourally meaningful. |
| P2s (`SHUFFLED_MASK`) | Whether the response is feature-specific rather than generic. | That the shuffled condition is a biologically plausible alternative; it is a null construction. |
| P3 (decoder) | The decoder can be driven out of NEUTRAL by the simulated activity. | **Motor control.** The decoder is a hand-written threshold rule; P3 is decoder reachability, not motor recruitment. |
| P3a (MOT) | Motor neurons spike. | That the spikes are the correct motor pattern; there is no behavioural ground truth. |
| `SINGLE_H1_SPIKE` | The minimum single-neuron event that transmits. | Population propagation; one neuron is not the population. |

### 5.2 Explicit pass / fail / inconclusive criteria

The protocol has P0–P3. The audit recommends the following expanded set. "Pass" means the stage's stated quantity is met; "fail" means it is not met and the stated consequence follows; "inconclusive" means the measurement is degenerate or underpowered and no directional claim is made.

| Gate | Pass | Fail | Inconclusive |
| --- | --- | --- | --- |
| **P0 — integrity** | All 324 records complete every mandatory field; the 5% re-run reproduces `spike_hash`; the archived 4H condition-B hash is reproduced; no `SpikeCapacityExceeded`; all recorded membrane arrays finite. | Any determinism mismatch not traceable to a declared code change; any silent truncation; > 5% of trials missing a mandatory field in any condition. | Not applicable; integrity is binary. |
| **P1a — STIM activation** | At some drive, ≥ 10/20 `REAL` trials have ≥ 1 spike in the 232 stimulated neurons, each control ≤ 1/20, Fisher p < 0.0025 (four-drive corrected). | No drive up to 1200 pA activates STIM, while `DIRECT_INJECTION` at ≥ 400 pA drives H1: a drive/encoder failure; stop and report. | `REAL` and controls both silent and `DIRECT_INJECTION` also silent: the tissue does not spike under any tested drive; stop and report as a model-regime limit. |
| **P1 — H1 first hop** | At some drive, the Fisher test of `REAL` vs pooled controls on the H1-spike proportion passes at α = 0.0025 (or the fixed-sequence equivalent), and `REAL` > controls. | No drive passes; `DIRECT_INJECTION` also fails: stop. `DIRECT_INJECTION` passes but `REAL` does not: drive/encoder failure; stop. | The Fisher test passes but the effect is carried by one drive and the seed-split halves disagree in sign: report as unstable, do not set `d*`. |
| **P2a — H2 second hop** | At some drive, ≥ 3/20 `REAL` trials have ≥ 1 H2 spike, controls ≤ 2/40, and a paired condition test (or Fisher if unpaired) passes. | No drive up to 1200 pA passes: stop; report "no propagation detected under this design", consistent with Phase 4H.4/4H.5. | H2 is degenerate (all zero) while P2b passes: report H2 as unobserved and P2b as the only propagation evidence; do not claim H2. |
| **P2b — DESC recruitment** | At some drive, ≥ 1/20 `REAL` trials has ≥ 1 spike in `DESC \ first_hop_DESC` (excluding the 9 directly innervated DNs), controls ≤ 2/40. | No drive passes: report descending recruitment not detected; H3/H4 untestable. This is not a stop if P2a passed; it is a limitation. | The only DESC spikes are in the 9 first-hop DNs: report first-hop descending activity, not second-hop recruitment. |
| **P2s — specificity** | At `d*`, `REAL` > `SHUFFLED_MASK` on the H2/DESC proportion (paired test, p < 0.05), and `SHUFFLED_MASK` does not exceed `REAL`. | `SHUFFLED_MASK` equals or exceeds `REAL`: the propagation is not feature-specific; H2/H3 become descriptive, not confirmatory. | Both are zero: not estimable; report the null as a failed observation, not as specificity. |
| **P3 — decoder reachability** | At `d*`, ≥ 1 post-stimulus `REAL` decoder window is non-NEUTRAL and no control window is non-NEUTRAL. | No `REAL` window is non-NEUTRAL: H5 untestable; H1–H3 proceed. This is not fatal. | `REAL` has one non-NEUTRAL window but the controls also have one: the decoder is not neutral; exclude the decoder endpoint from confirmatory claims. |
| **P3a — motor recruitment** | At `d*`, ≥ 1 `REAL` trial has ≥ 1 MOT spike and no control does. | No MOT spike: H4/H5 untestable; report as structurally expected (0 first-hop motor targets). | MOT spikes occur only in controls: report a baseline motor false-positive rate. |

The audit's verdict on the pilot is **feasible, but not as written**: the code path exists, the 324 runs are cheap, and the 4H wrapper proves the instrumentation technique. The pilot is not feasible as written because (a) the event-time rebasing is unspecified, so the stimulus may never fire; (b) P2 conflates first- and second-hop; (c) the zero-control rule will fail on chance; (d) there is no STIM gate and no specificity gate, so a "P2 pass" can be neither sensory nor specific. With the corrections in §7, the pilot is feasible.

## 6. Resource audit

### 6.1 Verified counts

| Quantity | Protocol | Audit | Check |
| --- | ---: | ---: | --- |
| Stage P runs | 324 | 324 | 240 (3 conditions × 4 drives × 20) + 80 direct injection (4 × 20) + 4 single-spike = 324. Correct. |
| Stage R runs | 2,688 + 134 repeats | 2,688 + 134 | 4 conditions × 672 = 2,688; 5% repeat = 134. Correct. |
| Total BANC runs | 3,146 | 3,146 | 324 + 2,688 + 134. Correct. |
| Stage S episodes | 19,200 | 19,200 | 40 × 2 × (160 + 80). Correct. |
| Stage S rows | 6,400 | 6,400 | 40 × 2 × 80. Correct. |
| Stage R trials per condition | 672 | 672 | 4 levels × 168. Correct. |
| Stage R unique seeds | 2,688 | **672** | One seed reused across four conditions. **Correction required.** |
| Stimulus events | 43 | **24 tracks** | 43 event records from 24 `(class, track)` pairs. **Correction required.** |

### 6.2 Runtime

The anchor is the median 2.54 s per 300 ms BANC run over 352 timings in `population_sensitivity.json` (min 1.66, max 4.30). Recomputed:

| Stage | Runs/episodes | Arithmetic | Wall time |
| --- | ---: | --- | ---: |
| P | 324 runs | 324 × 2.54 s = 823 s | 13.7 min (0.23 h) |
| R | 2,822 runs (2,688 + 134) | 2,822 × 2.54 s = 7,168 s | 1.99 h |
| S | 19,200 episodes | Phase 5F: ≥ 8,000 core episodes / 394.41 s = 20.3 episodes/s → 19,200 / 20.3 = 946 s | ≤ 15.8 min (0.26 h) |
| A | analysis | not measured | ≤ 30 min (declared estimate) |
| **Total, mandatory** | | 0.23 + 1.99 + 0.26 + 0.5 | **≈ 3.0 h** |

The protocol's 2.8 h is **inconsistent with its own components**: 0.23 + 1.98 + 0.5 (Stage S, JSON) + 0.5 (analysis) = 3.21 h. Its 3.0 h "with optional diagnostics" is also low, because the optional diagnostics add I/O but not analysis time; 3.0–3.2 h is the honest mandatory figure (3.0 h using the measured Stage S bound, 3.2 h using the protocol's own 0.5 h Stage S estimate), and 3.4 h with the optional panel. **Exact correction:** replace 2.8 h with ≈3.2 h, and 3.0 h with ≈3.4 h; add the Stage S anchor (Phase 5F: 394.41 s for the core plus conventional/robustness work, so ≥ 20 episodes/s and ≤ 16 min for 19,200 episodes). The 20–40 min Stage S range is conservative by 1.3–2.5×; it is acceptable as an upper bound but it is not derived in the document.

### 6.3 Storage

The 135 KB/run planning value is 15,000 spikes × 8 B = 120 KB plus 15 KB of fields. Recomputed:

| Item | Protocol | Audit | Check |
| --- | ---: | ---: | --- |
| P | 44 MB | 43.7 MB | 324 × 135 KB. Correct. |
| R mandatory | 363 MB | 362.9 MB | 2,688 × 135 KB. Correct **for the 2,688 runs only**. |
| R repeats | not listed | 18.1 MB | 134 × 135 KB. **Add this.** |
| R total | 363 MB | **381 MB** | 2,822 × 135 KB. |
| S | 120 MB | 120 MB | 19,200 × 6.25 KB; the 36-node substrate has few spikes. Plausible. |
| A | 10 MB | 10 MB | Declared. |
| **Total mandatory** | 537 MB | **555 MB** | 43.7 + 381 + 120 + 10. |
| Optional O2+O3 | 1,900 MB total | **≈2,035 MB** | 740 MB O2 + 740 MB O3 + 381 MB R + 44 + 120 + 10 = 2,035 MB; the report's 1.8 GB "R with O2+O3" is 1,843 MB, and the total is ≈2.0 GB. |

**Exact correction:** add the 18 MB repeat storage; change the mandatory total to ≈555 MB; change the optional total to ≈2.0 GB and the "R with O2+O3" row to ≈1.84 GB. The difference is not material to feasibility, but a storage budget that omits the determinism re-runs is internally inconsistent.

### 6.4 Memory

- BANC t5 arrays in memory: `root_ids` 1.38 MB, `out_indptr` 1.38 MB, `edge_src`/`edge_dst`/`edge_weight` 6.14 MB each, `in_indptr` 1.38 MB, `in_edge_idx` 6.14 MB, `banc_ids` 12.4 MB (`<U18` strings), `positions` 2.07 MB, `position_mask` 0.17 MB; total ≈43.4 MB. The simulator adds `_V` (1.38 MB float64), `_exc`/`_inh`, the synapse delay buffers, and the `SpikeRecorder` (4 MB at 500,000 spikes). The 0.3–0.5 GiB estimate is plausible with numpy and Python overhead.
- Phase 5F peak resident memory was 139.6 MB (`process_memory_end.peak_wset_mb`) on the 36-node substrate; that is not the BANC figure, but it shows the Stage S memory is small.
- Phase 6A measured 0.97 GiB free; the single-process rule and the "concurrency only above 1.5 GiB" rule are sound. The t1 graph is 5× larger (11.6 M edges, ≈186 MB of edge arrays), but Stage R uses t5 only; if a future sensitivity uses t1, the memory estimate must be raised.
- The O1 full-population trajectory is 172,433 × 600 × 8 B = 827 MB for 300 ms, and 4.55 GB for 3,300.5 ms (Phase 6A `RK-07`). The protocol's rejection of O1 is correct.

### 6.5 Estimates that lack a reproducible calculation

The audit flags these as **estimates**, not errors:

- Stage S 20–40 min: no worked calculation. The Phase 5F anchor gives ≤16 min; the 20–40 min range is a conservative upper bound.
- The 2.8 h total: wrong arithmetic (see §6.2).
- The 537 MB total: omits repeats (see §6.3).
- The 1,900 MB optional total: low by ≈100 MB (see §6.3).
- The 0.3–0.5 GiB peak: plausible but not derived from a measured BANC run in this document. Phase 6A's 0.97 GiB free is the constraint, not the peak.
- The 30 min analysis: a guess. 10 endpoints × 5,000 permutations × 672 rows is ≈50,000 MI evaluations; at sub-millisecond each that is < 1 min, but Python loop overhead and the 2,000-draw bootstraps could make it 10–30 min. Label it an estimate.
- The 135 KB/run: a planning value, not measured. The 4H condition-B run had 3,562 spikes over 3,300.5 ms; a 300 ms run at 200 pA will have fewer, so 15,000 is conservative. Label it.

## 7. Required protocol corrections

### 7.1 Blocking before G0

These seven must be incorporated and the protocol re-frozen before G0. They are the conditions of the verdict.

**B1. Evaluate P2 at every drive and fix `d*`.**
- In §6.2, change "At `d*`" to "At each drive d ∈ {200, 400, 800, 1200} pA"; change "If P2 fails" to "If P2 fails at every drive"; change the P2 gate to "at the lowest drive at which P1 and P2 both pass"; keep the gate order (P1 first, then P2), but do not fix `d*` until both have been read.
- In §10.4, change "P2 fails at every drive up to 1200 pA" to "P2 fails at every tested drive (200, 400, 800, 1200 pA)".
- In §6.2, add one sentence: "The 240 Stage P runs already contain all four drives, so evaluating P2 at every drive adds no simulations."
- In the JSON, add `p2_drives: [200, 400, 800, 1200]` and change the gate text.

**B2. Split P2 and fix the control rule.**
- Replace P2 with **P2a (H2 only)** and **P2b (DESC excluding the 9 first-hop DNs)**. The 9 are the first-hop targets reported in `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md:216,303`; the remaining 1,307 are available.
- Change "0 of 40" to "≤ 2 of 40" (or the pooled control upper 95% bound). State the bound at the time of the gate decision and use it for E3.
- Add **P1a (STIM activation)** before P1 and **P2s (`SHUFFLED_MASK` specificity)** after P2b.
- Add **P3a (MOT spikes)** after P3, and label P3 as decoder reachability, not motor recruitment.
- In §6.1, add the seventh distinction (direct sensory activation) and map P1a to it.
- In the JSON, add the new gates and their pass/fail criteria.

**B3. Correct the seed, trial and condition-run counts.**
- §8.1: seed = 672 (reused across 4 conditions); condition-run = 2,688; trial = 672 per condition. Change the "Not valid for" entry for seed to "generalisation beyond the simulated trials".
- §6.3: keep "each trial re-uses the same seed across conditions"; add "the 2,688 conditions are 672 seeds × 4 conditions".
- The JSON `independence_units.seed.stage_r` changes from 2688 to 672; add a `condition_run` unit with 2,688.
- §9.1/§9.2: use paired tests (McNemar for E1/E3, paired condition-label permutation or seed-cluster bootstrap for E4/E5), and keep the stimulus-label permutation only for the "MI > chance" component.

**B4. Correct the stimulus corpus and the cluster unit.**
- §6.4: 43 event records from 24 tracks; `OBST_NEAR` is one track at two frames.
- §8.1: 24 tracks (13/11/5/1); §8.6: resample tracks, not event records; `OBST_NEAR` is not estimable.
- §8.7: 24 tracks; `OBST_NEAR` effective sample one.
- §12 R3: "Only 43 of 215 archived events ... `OBST_NEAR` has 2" → "43 event records from 24 tracks; `OBST_NEAR` is one track."
- JSON: add `distinct_tracks: 24` and per-level track counts; change the event-cluster description.

**B5. Fix the Stage S power.**
- Increase Stage S to ≥ 79 seed clusters (α = 0.05) or ≥ 134 (Holm α = 0.005), or re-declare the E10 MDE as 0.07 bits and change the positive criterion to > 0.07.
- State that 0.1581 bits is the Phase 6C `I(cue ; action)` SD, a proxy for `I(cue ; A_neural)`, and that the neural-code SD may be larger.
- State whether the 40 clusters share one substrate (Phase 5F did) or use 40 substrate seeds; if they share, say the CI does not cover substrate uncertainty.
- Relabel the "Phase 5F contrast reproduced at 40 seeds" as a new replicate, or include the original 10 streams as a subset.

**B6. Specify the recording invariants.**
- Add §5.2 O2 note: the post-step `_V` for a spiking neuron is −68 mV (`brain/neuron_model.py:154`); the recorder must substitute threshold (as `analyse_sensory_roundtrip.py:828` does) or sample pre-step.
- Add to §11.3: copy-on-record for `_V`, `_exc`, `_inh`; no RNG consumption; return `None` from the Stage S callback; install/restore in `finally`; one recorder; one `spike_counts()` per trial; the time base `(step+1)×0.5 ms`.
- Add the twelve tests in §4.3 to `tests/test_phase_6d_recording.py`; in particular T1–T3 (identical hash, byte-identical repeat, zero RNG) and T4 (the `LIFPopulation.step` contract).
- Add a second archived non-zero condition (C or D) as a hash fixture alongside B.

**B7. Specify the event-time transform and the stimulus offset.**
- §6.4: re-base every selected event to `time_ms = 50.0` (or state the transform), and record the original time in field 9.
- §5.1 field 10: either set `decay_ms = 100` so the current ends at the declared offset of 150 ms, or state that "offset" is nominal and the drive decays for 150 ms beyond it.
- §6.4: state that `SHUFFLED_MASK` permutes feature payloads across event times (`shuffle_feature_identities`), not the feature→population mapping, and that per-trial charge is not preserved; pair each `REAL` trial with a charge-matched `SHUFFLED` trial or add the charge as a covariate.
- Add a "peak-matched rectangular" control (200 pA for 100 ms on the same 232 neurons) or demote `MATCHED_CHARGE` to descriptive. The current `MATCHED_CHARGE` is ≈20 pA per neuron and is below the 150 pA rheobase by construction; Phase 4H condition F produced 0 spikes.

### 7.2 Required before G1 (instrumentation)

**R1.** Implement the twelve tests in §4.3, not the six in the protocol.
**R2.** Add the O2/O3 panel selection rule (e.g., top 200 first-hop by mean input current) and record it in fields 8/24.
**R3.** Add the `LIFPopulation.step` contract test and a second archived hash fixture.
**R4.** Add a no-op recorder mode and a "recording off" mode to the runner, so T1/T2 can be run as part of the campaign, not only in a unit test.

### 7.3 Required before G3/G5

**C1.** Freeze the corrected event-time transform, the drive series and the panel rule before Stage P.
**C2.** Freeze the gate definitions (P0, P1a, P1, P2a, P2b, P2s, P3, P3a) and their pass/fail/inconclusive tables before Stage P.
**C3.** Freeze the paired tests and the cluster units before Stage R.
**C4.** Freeze the Stage S seed count and MDE before Stage S; if the count changes, re-freeze.
**C5.** Record the control upper bound at the gate decision and use it for E3.
**C6.** Report the Stage P results at all four drives, including the drives that fail, not only at `d*`.

### 7.4 Recommended, not blocking

- **Finer drive sweep.** A 1.5× geometric sweep from 100 to 1200 pA (≈10 points) would bracket the threshold better than the four-point series. It would add ≈10 × 20 × 3 = 600 runs (≈25 min) if only P1/P2a/P2b are read. The four-point series is acceptable if P2 is read at all four drives; the finer sweep is recommended if the first four-point pilot fails.
- **Stage S deferral.** If H6 is not essential to Phase 6D, defer Stage S to its own phase. It uses a different substrate, its power is the weakest part of the design, and it is independent of H1–H5. This also removes the 19,200 episodes and the 120 MB from the critical path.
- **Optional O2/O3.** Enable them only after B6 is implemented and T5/T6 pass. They have no confirmatory endpoint; their value is the descriptive check that the LIF integration behaved as assumed.
- **A negative-control mapping.** `E_random_matched_mapping` was dropped from Stage R. It is not needed for H1–H3, but a 20-trial random-mapping arm at `d*` would show whether the specific mapping matters. It is descriptive, not confirmatory.

## 8. Approval recommendations

### 8.1 Recommendation

**APPROVED WITH REQUIRED CORRECTIONS.**

The protocol should not be executed as written. It should be corrected, re-frozen, and then executed in the gate order it already defines. The corrections are specification corrections; none requires a new dataset, a new model, a new dependency, or a new phase.

### 8.2 Sequence

1. **Correct B1–B7** in the Markdown and JSON; re-run the MD/JSON consistency check; re-freeze both with new SHA-256 values.
2. **G0:** human review and signature against the corrected, re-frozen protocol.
3. **G1:** write `experiments/phase_6d/` and the twelve tests; no simulations.
4. **G2:** T1–T3 on archived 4H conditions B and C; full test suite; no production edits; README hash unchanged.
5. **G3:** Stage P with the expanded gates; read P1a/P1/P2a/P2b/P2s at all four drives.
6. **G4:** freeze the gate decision, including the control upper bound and `d*`.
7. **G5:** Stage R only if P2a/P2b pass and P2s does not overturn specificity.
8. **G6:** Stage S only if in scope and the corrected seed/MDE conditions are met.
9. **G7:** analysis once, results JSON hashed before prose.

### 8.3 The three open scope decisions

1. **Optional panel diagnostics.** Enable O2/O3 only with B6 (threshold substitution, copy-on-record) and a pre-registered panel rule. The storage cost is ≈1.48 GB, and there is no confirmatory endpoint. If the panel rule cannot be fixed, keep the mandatory sparse record only.
2. **Drive series.** The four-point series is acceptable **if** P2 is read at all four drives (B1). The finer sweep is recommended if the four-point pilot fails; it is not required before the first pilot.
3. **Stage S scope.** Defer it unless H6 is required for Phase 6D. If kept, use ≥ 79 seed clusters (or re-declare the MDE as 0.07), clarify substrate sharing, and relabel the 40-stream run as a new replicate, not a reproduction.

### 8.4 What would change the verdict

- To **NOT READY**: if the event-time transform cannot be specified without changing the 300 ms trial or losing most of the 24 tracks; if the Stage S seed count cannot be increased and the MDE cannot be re-declared; if the instrumentation cannot reproduce the archived hash with T1–T3. None of these is currently the case, but each is a hard stop if it emerges at G2/G3.
- To **APPROVED FOR IMPLEMENTATION**: if all seven blocking corrections are incorporated, the MD/JSON consistency check passes, and the corrected protocol is re-frozen with no new issue. The audit would then recommend G0 without further scientific objection.

## 9. Complete list of unresolved issues and exact corrections

Each row is an unresolved issue in the audited documents. "Blocking" means it must be fixed before G0. "Required" means it must be fixed before the named gate. "Recommended" means it improves the design but is not a condition of approval.

| ID | Severity | Issue (document location) | Exact correction |
| --- | --- | --- | --- |
| U1 | Blocking | `d*` fixed at P1; P2 only at `d*`; §10.4 claims P2 fails at every drive (§6.2, §10.4) | Read P2a/P2b at all four drives; set `d*` to the lowest drive where P1 and P2 both pass; change §10.4 to "every tested drive"; add the zero-cost sentence. |
| U2 | Blocking | P2 uses `H2 ∪ DESC`; 9 DNs are first-hop (§6.2) | Split P2a (H2) and P2b (`DESC \ first_hop_DESC`, 9 excluded); report both. |
| U3 | Blocking | P2 requires "0 of 40" controls; 0.5–2% control rate gives 18–55% chance of a spurious failure (§6.2) | Use "≤ 2 of 40" or the pooled Clopper–Pearson upper bound; record the bound at G4; use it for E3. |
| U4 | Blocking | No gate measures the 232 stimulated neurons; P1 measures H1 (§6.2, H1) | Add P1a (STIM activation) before P1; add it to §6.1 as the seventh distinction. |
| U5 | Blocking | No `SHUFFLED_MASK` in Stage P; specificity is first tested in Stage R (§6.2, §6.3) | Add P2s (20 `SHUFFLED_MASK` trials per drive, 80 runs); require `REAL` > `SHUFFLED_MASK` or report non-specific propagation. |
| U6 | Blocking | "2,688 unique seeds" contradicts the paired design (§8.1, §6.3) | Seed = 672; condition-run = 2,688; trial = 672 per condition; update the JSON. |
| U7 | Blocking | "43 distinct events" is 43 records from 24 tracks; `OBST_NEAR` is one track (§6.4, §8.1, §8.6, §8.7, R3) | Replace with 24 tracks (13/11/5/1); resample tracks; `OBST_NEAR` not estimable; update the JSON. |
| U8 | Blocking | Stage S 0.05-bit criterion is below the 40-cluster MDE ≈0.07 bits (§6.6, §10.7) | Use ≥ 79 seeds (α = 0.05) or ≥ 134 (Holm), or re-declare the MDE as 0.07 and change the criterion; state the SD proxy. |
| U9 | Blocking | Event times 66.7–3266.7 ms cannot fit the 300 ms trial; no transform (§6.2, §6.4, field 10) | Re-base each event to 50 ms (or state the transform); record the original time in field 9. |
| U10 | Blocking | O2 samples post-step `_V`, which is −68 mV for spiking neurons (§5.2, `brain/neuron_model.py:154`) | Substitute threshold (as `analyse_sensory_roundtrip.py:828`) or sample pre-step; add a test. |
| U11 | Required | `MATCHED_CHARGE` is subthreshold by construction (≈20 pA vs 150 pA rheobase); 4H F = 0 spikes (§6.3, C2) | Add a peak-matched rectangular control or demote `MATCHED_CHARGE` to descriptive; do not use its zero as the charge control. |
| U12 | Required | `SHUFFLED_MASK` description says "feature→population identity permuted"; `shuffle_feature_identities` permutes payloads across events; per-trial charge changes (§6.3, R2) | Re-describe R2; pair `REAL` with charge-matched `SHUFFLED` trials or add charge as a covariate. |
| U13 | Required | `BancEventDrive` decays 150 ms, so "offset 150" is not a cutoff (§6.2, field 10) | Set `decay_ms = 100` or state that the drive decays beyond the nominal offset and the readout includes the tail. |
| U14 | Required | C4 says 4 × 10 direct-injection trials (40); §6.2 says 4 × 20 (80) (§6.2, C4) | Make C4 say 4 × 20 (80), matching the 324 total. |
| U15 | Required | 80%-power P1 claim 0.803 is Fisher-only; the full gate is 0.318–0.588 per drive (§6.2, §8.4) | Remove the "≥ 10 of 20" floor and define P1 by the Fisher test at α = 0.0025, or report the conjunction's operating characteristics. |
| U16 | Required | Four P1 drive tests have no multiplicity control (§6.2) | Use a fixed-sequence gate (1200 → 800 → 400 → 200) or Bonferroni α = 0.0025. |
| U17 | Required | E4/E5 test "REAL > SHUFFLED_MASK" with a stimulus-label permutation, which tests a different null (§9.1) | Use a paired condition-label permutation (swap within seed) or a seed-cluster bootstrap of the difference; keep the label permutation for "MI > chance". |
| U18 | Required | E8 uses `672 × 5` windows as n; E9 uses decoder windows as n; E7 uses DESC spikes as n (§9.1, §8.1) | Trial-level estimand or whole-trial cluster bootstrap; report the effective n; no p-value with n = 3,360. |
| U19 | Required | `max(0, I − floor)` is positively biased at the null; E5/E8/E9 use "> 0" (§8.3, §9.2) | Compare the corrected statistic to its own permutation null (95th percentile); do not use "> 0" as a test. |
| U20 | Required | The 672 derivation says "multiple of 4 and 6"; 648 is a multiple of both; the real constraint is a multiple of 48 (§8.2) | Rewrite the sentence: multiple of 48 for integer cells; 672 = 48 × 14. |
| U21 | Required | The 4×5 Stage S table conflicts with the 4-level discretisation in §9.2 (§8.2, §9.2) | Make both 4×4 (df 9, floor 0.001014 at 6,400) or define the fifth level. |
| U22 | Required | The table's 0.017 and the text's 0.0167 give 637 vs 648; both are used (§8.2) | Label the column and add a footnote; do not mix the tolerances. |
| U23 | Required | 80%-power 0.013/0.016 bits use α = 0.05, while the confirmatory family uses Holm α = 0.005 (§8.3) | State the α for each row; use the Holm threshold for the confirmatory family. |
| U24 | Required | Stage S 40 "seeds" share substrate 20261114 (Phase 5F); the CI does not cover substrate uncertainty (§6.6) | Use 40 substrate seeds or state the limitation in §6.6 and §12. |
| U25 | Required | "Phase 5F contrast reproduced at 40 seeds" is a new replicate, not a reproduction (§6.6, §9.3) | Include the original 10 streams as a subset or relabel as a new replicate. |
| U26 | Required | Stage S `fixed_complete` is described as "same seed list and evaluation protocol" as Phase 5F; 5F used 10 seeds/40 eval, Stage S 40/80 (§6.6) | Say "same substrate and protocol family; 40 new streams, 80 evaluation episodes." |
| U27 | Required | 537 MB total omits the 134 repeats; 2.8 h total is inconsistent with its components; 1,900 MB optional is low (§11.1, §6.7) | 555 MB mandatory; 3.0–3.2 h mandatory; 2.0 GB optional; add the repeat storage and the Stage S anchor. |
| U28 | Required | §5.1 refers to "§9.9", which does not exist; §10.2 says "20/20" for Stage R (672 seeds); §10.1 99.5% presence vs §9.2 5% exclusion | Fix the cross-reference; say 336/336 for Stage R or restrict 20/20 to Stage S; use one missing-data threshold. |
| U29 | Required | The instrumentation section lists six tests; they do not cover copy-on-record, RNG, the step contract, install/restore, or the time base (§11.3) | Add T1–T12 from §4.3; make T1–T3 and T4 mandatory. |
| U30 | Required | `excitatory_current_pa` returns the live `_exc` array; the schema does not require a copy (§5.2 O3) | Require `.copy()` for any retained array; add T5. |
| U31 | Required | The O2 panel "up to 200 first-hop" has no selection rule (§5.2) | Pre-register the selection rule (e.g., top 200 by mean input current, ties by index) and record it. |
| U32 | Required | The 5 ms E7 window is short relative to `tau_m = 20 ms` and the 1 ms delay; E7 has no sensitivity window (§9.1) | Pre-register 10 ms and 20 ms sensitivity; report per-trial proportions. |
| U33 | Required | The P2 screen's sensitivity is reduced by the zero-control rule; the protocol attributes the miss only to compute (§6.2) | State the effective pass probability with the control rule; use ≤ 2/40. |
| U34 | Recommended | The four-point drive series coarsely brackets the threshold (§14.1) | Add a 1.5× geometric sweep (100–1200 pA) if the four-point pilot fails. |
| U35 | Recommended | Stage S is independent of H1–H5 and its power is the weakest part (§14.1) | Defer Stage S to its own phase unless H6 is required. |
| U36 | Recommended | `E_random_matched_mapping` is dropped; a descriptive random-mapping arm is cheap (§6.5) | Add a 20-trial random-mapping arm at `d*` as descriptive, not confirmatory. |

## 10. Audit method and limits

**What was inspected.** The two Phase 6D reports; `brain/neuron_model.py`; `brain/neural_activity.py`; `brain/banc_simulator.py`; `brain/brain_simulator.py`; `brain/banc_sensory_adapter.py`; `plasticity/plastic_simulator.py`; `experiments/phase_4h/analyse_sensory_roundtrip.py`; `experiments/phase_4h/sensory_roundtrip.diagnostics.v2.checkpoint.jsonl`; `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`; `experiments/results/phase_5f/comparison_raw.json`; `experiments/results/phase_6c/mutual_information_results.json`; `configs/banc_sensory_mapping.yaml`; `configs/plasticity_comparison.yaml`; `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md`; `reports/PHASE_6A_INFORMATION_THEORY_AUDIT.md`; `information/bias_correction.py`.

**What was recomputed.** The MI bias floors and the N derivation; the exact Fisher power (0.8029 at n = 20, 0.281 at n = 10) and the compound P1 gate power (0.318 at 5% controls, 0.588 at 0%); the P2 screen (0.794/0.965/0.075) and the control-zero spurious rate (18.1%/33.1%/55.4%); the Stage S MDE (0.070 at 40 clusters at α = 0.05, 0.091 at α = 0.005) and the seed counts (79/134); the per-level event and track counts (20/15/2/6 records; 13/11/5/1 tracks); the BANC t5 array sizes (43.4 MB); the storage totals (555 MB mandatory, ≈2.0 GB optional); the runtime (3.0–3.2 h mandatory) and the Stage S anchor (≥ 20.3 episodes/s, ≤ 16 min for 19,200).

**What was not done.** No simulation, recording, training, model change, dataset change, or code change. No test suite was run. The archived 4H condition-B hash was not recomputed; the audit relies on the archived `spike_sha256` and the 4H report. The BANC manifest internals were not re-verified beyond the cited graph and node hashes. The `information/` estimators were inspected only at `bias_correction.py`; the permutation and bootstrap helpers were not exercised. The Phase 5F runtime decomposition (core vs conventional vs robustness) was not re-run; the ≥ 20 episodes/s figure is a lower bound from the core 8,000 episodes in 394.41 s.

**Limits of the audit.** The between-seed SD 0.1581 bits is a proxy from Phase 6C's `I(cue ; action)`, not from `I(cue ; A_neural)`; the Stage S MDE is therefore an estimate, and the protocol should compute the SD from its own pilot or from the 5F archive before fixing the seed count. The 0.070-bit MDE assumes the 40 clusters are exchangeable; if the 40 streams share one substrate (as Phase 5F did), the effective number of independent clusters is smaller and the MDE is larger. The event-time archive was inspected at the event-record level; the audit did not reconstruct the track lifecycle, so the 24-track count is a lower bound on the number of distinct stimuli (a track may be re-identified after occlusion). The audit did not test the `BancSimulator` on the current hardware; the runtime and memory figures are from the archived measurements.

**No file other than this audit was written.** The two Phase 6D reports, `README.md`, and all protected baseline files are unchanged. Nothing was staged, committed, or pushed.
