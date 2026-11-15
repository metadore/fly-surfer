# Phase 6D audit correction matrix

**Document ID:** `phase_6d_audit_correction_matrix`
**Date:** 2026-11-11
**Status:** DESIGN AND DOCUMENTATION ONLY — NO SIMULATION, RECORDING OR TRAINING PERFORMED
**Corrected protocol:** `reports/PHASE_6D_RECORDING_PREREGISTRATION_V2.md` and its
JSON companion
**Audit resolved:** `reports/PHASE_6D_INDEPENDENT_AUDIT.md`
**Audited protocol (unchanged):** `reports/PHASE_6D_RECORDING_PREREGISTRATION.md`
and `.json`

This matrix maps every issue in the independent audit to the exact correction in
revision 2, the protocol section where it now lives, how it can be verified, and
its resolution status. Nothing here is waived. Where a correction could not be
completed from available evidence, the row says so and §5 explains why.

**Status vocabulary used in this document**

| Status | Meaning |
| --- | --- |
| **Resolved** | The correction is written into revision 2, is complete, and has a verification method that does not require new simulation. |
| **Resolved, limitation retained** | The protocol defect is fixed, but an empirical uncertainty remains that only execution can settle; it is listed in V2 §14.3 with a pre-registered handling rule. |
| **Adopted with stated deviation** | The audit's recommended remedy was not adopted verbatim; a different remedy achieves the stated purpose, and the reason for the deviation is given. |
| **Not adopted, justified** | The audit's recommendation was considered and rejected on scientific grounds; the reason is given. |

## 1. Blocking findings A1–A7

The audit's §3 lists seven blocking findings. Each is a defect that prevents the
protocol from being implemented as written.

| # | Finding | What was wrong | Correction in revision 2 | Where | Verification |
| --- | --- | --- | --- | --- | --- |
| **A1** | `d*` is fixed at P1 and P2 is read only there | The protocol claimed P2 failed "at every drive" while only ever evaluating it at one pilot-selected drive. A false stop or false pass could not be distinguished from a sampling artefact. | P1a, P1, P2a and P2b are read at **all four drives** from the same 964 runs. `d*` is the lowest drive at which P1a, P1, P2a and P2b all pass, frozen before any downstream outcome. P2 failure is declared only after all four drives fail. The four-drive reading costs zero additional simulations. | V2 §8.3, §8.4, §12.5 | Gate-decision file contains four rows per gate; a unit test asserts `d*` equals the lowest passing drive (T-gate-4); §12.5 wording is "every tested drive (200, 400, 800, 1200 pA)". |
| **A2** | P2 conflates first and second hop and uses a zero-tolerance control rule | `H2 ∪ DESC` mixes a true second hop with 9 descending neurons that are first-hop targets. The "0 of 40 control" rule has an 18–55% chance of a spurious failure at a 0.5–2% control rate, so a pass would have meant "no control spiked by luck". | P2 is split into **P2a** (`H2` only), **P2b** (`DESC \ H1D`, 9 excluded), **P2c** (charge form, `PEAK_MATCHED_RECT`) and **P2s** (feature specificity, `SHUFFLED_MASK`). Presence gates are **screens** with effect-size floors and a stated sensitivity curve; the zero-tolerance rule is removed. Control bound is the Clopper–Pearson upper limit, recorded at G4 and used as E3's threshold. | V2 §8.4, §9 C2/C3, §11.1 E3 | Gate table has one row per gate with Pass/Fail/Inconclusive; screen operating characteristics are printed before the run; the 0/40 upper bound 0.0722 is stated. |
| **A3** | "2,688 unique seeds" contradicts the paired design | A paired design reuses one noise seed across conditions. Calling all condition-runs "seeds" overstates independence by 4×. | **672 unique seeds**; **2,688 condition-runs**; **672 trials per condition**; contrasts are paired by seed. Stage S has its own 134 substrate seeds. | V2 §8.6, §10.1, §11.3 | Independence-unit table lists each unit, its count and what it may and may not be used for; no analysis uses 2,688 as n. |
| **A4** | "43 distinct events" is 43 records from 24 tracks | Treating records as independent stimuli inflates the effective stimulus n by 1.8× and ignores that `OBST_NEAR` is a single track. | **43 event records from 24 distinct `(class, track)` pairs**; per-level records 20/15/2/6 and tracks 13/11/1/5; the union is 24 because six tracks appear in two levels. Resampling is at **track** level, recomputing the whole table; `OBST_NEAR` is not estimable at track level and cannot carry a direction. Trial allocation is track-balanced. | V2 §8.5, §10.1, §11.6 | The 24/43 ratio is recomputed from the archive, not asserted; the matrix in §8.5 sums to 30 per-level tracks and 24 distinct, with the six crossing tracks named; the bootstrap resamples 24 clusters. |
| **A5** | The Stage S 0.05-bit criterion is below the 40-cluster MDE | At 40 clusters the SD of 0.1581 bits gives an MDE of 0.070 bits at α = 0.05, so a 0.05-bit criterion could not be met even by a true 0.05-bit effect. | Stage S moves to **134 independent substrate clusters**, giving SE 0.0137, MDE 0.0383 bits at α = 0.05 and **0.0498 bits at α = 0.005 (Holm)** with power 0.803. The 0.1581-bit SD is declared a **proxy** with a pre-registered realized-MDE fallback: if the realized MDE exceeds 0.05 bits, E10 is demoted to exploratory before its result is examined. | V2 §8.7, §10.5, §12.7 | Power table lists SD, SE, MDE at two α values and power for 40/79/134 clusters; the fallback rule is a blockquote fixed before Stage S. |
| **A6** | The O2 panel samples post-step `_V`, which is −68 mV for a spiking neuron | `LIFPopulation.step` resets `_V[spikes]` to −68 mV at line 154 before returning. A recorder that samples after `step` records every spike as the reset potential, silently inverting the sign of the panel's most important events. | The instrumentation contract requires **threshold substitution or pre-reset sampling**, a `spiked` flag, copy-on-record, zero RNG consumption, one recorder, install/restore in `try/finally`, and a declared time base. Tests T1–T12 are mandatory; T6 is specific to the threshold artefact. | V2 §7.4 clause 4, §7.5 T1–T12 | T6 asserts that a spiking neuron is never recorded at −68 mV; T1 reproduces archived 4H condition-B **and** condition-C hashes; T2 compares recording-on and recording-off hashes. |
| **A7** | Archived event times cannot occur inside a 300 ms trial | Event times run 66.6667–3266.6667 ms and `BancEventDrive` uses the absolute time as onset, so most events would never fire inside the trial. | A declared **event-time transform**: every selected event is re-based to `trial_time_ms = 50.0`, with `decay_ms = 100.0` so injected current ends exactly at the declared offset of 150 ms. The original archive time, the transform string and the record index are written to field 11. | V2 §7.3 field 11, §8.5 | The transform is frozen before Stage P; the record contains both times; a test asserts that recorded onset equals 50.0 ms and that current is zero after 150.0 ms (T-time). |

**All seven blocking findings are resolved.** A1, A2 and A6 are resolved
completely. A3, A4, A5 and A7 are resolved in the protocol, but each leaves an
empirical item (paired seed reuse is a design fact, not an uncertainty; the other
three are RA-1/RA-2, RA-3 and RA-6 in V2 §14.3).

## 2. Complete issue matrix, U1–U36

### 2.1 Blocking issues, U1–U10

| ID | Original issue (audit wording, condensed) | Required correction | Revision 2 correction | Section | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **U1** | `d*` fixed at P1; P2 only at `d*`; §10.4 claims P2 fails at every drive | Read P2a/P2b at all four drives; `d*` = lowest drive where both pass; say "every tested drive" | Presence gates read at 200/400/800/1200 pA from existing runs; `d*` frozen after all four; failure declared only after all four fail | §8.3, §8.4, §12.5 | Gate-decision file has four rows per gate; unit test on synthetic tables | **Resolved** |
| **U2** | P2 uses `H2 ∪ DESC`; 9 DNs are first-hop | Split P2a (H2) and P2b (`DESC \ first_hop_DESC`), report both | P2a on `H2` (3,576), P2b on `DESC2` (1,316 − 9 first-hop DNs), both reported; H3 is defined on `H2 ∪ DESC2` | §5 H3, §8.4, §8.5 | Population labels 1/2/3 carry the split; E5's table is computed from `R_H2DESC` | **Resolved** |
| **U3** | P2 requires "0 of 40" controls; 18–55% chance of spurious failure | Use "≤ 2 of 40" or the Clopper–Pearson bound; record the bound at G4 and use it for E3 | Zero-tolerance rule removed; P2a/P2b are screens with effect-size floors; the control bound is recorded at G4 and becomes E3's threshold when non-zero | §8.4, §8.6, §11.1 E3, §12.5 | G4 artifact stores the bound; E3 reports the threshold actually used | **Resolved** |
| **U4** | No gate measures the 232 stimulated neurons; P1 measures H1 | Add P1a (STIM activation) before P1 | P1a: `REAL` `STIM` prevalence ≥ 20/40 and Fisher p < 0.0125 vs `NO_STIM`; P1a precedes P1 and `d*` requires it | §8.4, §5 H1, §11.1 E1/E2 | Gate table row P1a; E1/E2 are computed on `STIM` not `H1` | **Resolved** |
| **U5** | No `SHUFFLED_MASK` in Stage P; specificity first tested in Stage R | Add P2s with 20 trials per drive (80 runs) | `SHUFFLED_MASK` is a full Stage P arm at 40 trials per drive (160 runs); P2s is a paired specificity gate at `d*` | §8.2, §8.4, §9 C3 | 160 Stage P runs are enumerated in the design table; P2s row in the gate table | **Resolved** |
| **U6** | "2,688 unique seeds" contradicts the paired design | Seed = 672; condition-run = 2,688; trial = 672 per condition | 672 seeds, 2,688 condition-runs, paired by seed; stated in three places | §8.6, §10.1, §11.3 | Independence-unit table; no endpoint uses 2,688 as n | **Resolved** |
| **U7** | "43 distinct events" is 43 records from 24 tracks; `OBST_NEAR` is one track | Replace with 24 tracks (13/11/5/1); resample tracks; `OBST_NEAR` not estimable | 24 distinct tracks; per-level tracks 13/11/1/5; track-cluster bootstrap over 24; `OBST_NEAR` declared not estimable; track-balanced allocation | §8.5, §10.1, §11.6 | The counts are recomputed from `phase_3b2c_real_sequence_replay.json`; the six double-counted tracks are named | **Resolved, limitation retained** (RA-3) |
| **U8** | Stage S 0.05-bit criterion is below the 40-cluster MDE ≈ 0.07 bits | Use ≥ 79 seeds (α = 0.05) or ≥ 134 (Holm), or re-declare the MDE; state the SD proxy | 134 clusters; MDE 0.0498 bits at α = 0.005; SD 0.1581 declared a proxy with a realized-MDE fallback | §10.5, §8.7 | Power table; fallback rule fixed before data | **Resolved, limitation retained** (RA-6) |
| **U9** | Event times 66.7–3266.7 ms cannot fit the 300 ms trial; no transform | Re-base each event to 50 ms; record the original time | `trial_time_ms = 50.0`, `decay_ms = 100.0`; original time in field 11 | §8.5, §7.3 field 11 | Frozen before Stage P; record carries both times | **Resolved** |
| **U10** | O2 samples post-step `_V`, which is −68 mV for spiking neurons | Substitute threshold or sample pre-step; add a test | Clause 4 requires threshold substitution or pre-reset sampling with a `spiked` flag; T6 tests it | §7.4 clause 4, §7.5 T6 | T6 fails a recorder that yields −68 mV for a spike | **Resolved** |

### 2.2 Required issues, U11–U33

| ID | Original issue (audit wording, condensed) | Required correction | Revision 2 correction | Section | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **U11** | `MATCHED_CHARGE` is subthreshold (≈20 pA vs 150 pA rheobase); 4H F = 0 spikes | Add a peak-matched rectangular control or demote `MATCHED_CHARGE`; do not use its zero as the charge control | `PEAK_MATCHED_RECT` added (672 Stage R runs, 160 Stage P runs); `MATCHED_CHARGE` retained in Stage P as a **descriptive floor only**, used in no gate or endpoint; not a Stage R condition | §8.2, §8.6, §9 C2 | C2 table row names `PEAK_MATCHED_RECT`; `MATCHED_CHARGE` appears in no gate row | **Resolved** |
| **U12** | `SHUFFLED_MASK` is mis-described; `shuffle_feature_identities` permutes payloads across events; per-trial charge changes | Re-describe; pair `REAL` with charge-matched `SHUFFLED` trials or add charge as a covariate | The function's actual behaviour is stated with line references; the permutation is a bijection on 43 records preserving the payload multiset; per-trial injected charge is recorded and enters E4/E5 **as a covariate** | §8.6, §11.1 | Description cites `banc_sensory_adapter.py:883–903`; E4/E5 report the charge covariate | **Resolved** |
| **U13** | `BancEventDrive` decays 150 ms, so "offset 150" is not a cutoff | Set `decay_ms = 100` or state that the drive decays beyond the offset | `decay_ms = 100.0`, so current ends exactly at 150 ms; "offset" is a physical end | §8.5, §7.3 field 11 | Test asserts zero current after 150.0 ms | **Resolved** |
| **U14** | C4 says 4 × 10 (40) while §6.2 says 4 × 20 (80) | Make C4 say 4 × 20 (80) | `DIRECT_INJECTION` is 4 drives × 40 trials = **160** runs, consistent with every other Stage P arm; C4 states 160 | §8.2, §9 C4 | Design table sums to 964 | **Adopted with stated deviation** (40 rather than 20 trials, for consistency with the other arms) |
| **U15** | The 0.803 P1 power is Fisher-only; the full gate is 0.318–0.588 per drive | Remove the "≥ 10 of 20" floor and define P1 by Fisher at α = 0.0025, or report the conjunction's operating characteristics | Both parts of the conjunction are kept and the **conjunction's** operating characteristics are reported: 0.99 at 50% vs 5%, 0.88 at 30% vs 2%, 0.49 at 20% vs 2% | §8.4 | Screen table lists conjunction probabilities; the 0.803 Fisher-only figure is not quoted as gate power | **Resolved** |
| **U16** | Four P1 drive tests have no multiplicity control | Fixed-sequence gate or Bonferroni α = 0.0025 | Bonferroni over four drives: **α = 0.0125** per drive, family-wise 0.05; stated for P1a/P1 and reused for the two specificity gates at 0.025 | §8.4, §11.5 | Each gate row states its α; §11.5 reconciles the family | **Resolved** |
| **U17** | E4/E5 test `REAL > SHUFFLED_MASK` with a stimulus-label permutation, which tests a different null | Paired condition-label permutation or seed-cluster bootstrap of the difference | Two nulls are separated: (a) label permutation for "MI > chance"; (b) **paired condition-label swap within seed**, 5,000 draws, for the direction. Fisher is used only for unpaired Stage P | §11.3 | E4/E5 name their null; the estimand is the paired difference | **Resolved** |
| **U18** | E8 uses 672 × 5 windows as n; E9 uses windows; E7 uses DESC spikes | Trial-level estimand or whole-trial cluster bootstrap; report effective n; no p-value at n = 3,360 | E7 is a per-trial indicator; E8 is one `A` value per trial; E9 is descriptive with **no p-value**; any window-level summary is descriptive with a trial-clustered interval and effective n = 672 | §5 H4/H5, §11.1, §11.6 | Endpoint table lists the unit for every row; no n = 3,360 appears | **Resolved** |
| **U19** | `max(0, I − floor)` is positively biased at the null; E5/E8/E9 use "> 0" | Compare the corrected statistic to its own permutation 95th percentile | Every MI endpoint compares its corrected value to the 95th percentile of `max(0, Î_perm − floor)` from its own null; "> 0" is used nowhere | §11.4 | Test that a null table does not pass at the nominal rate; report includes q95 | **Resolved** |
| **U20** | The 672 derivation says "multiple of 4 and 6"; 648 already is | Rewrite: multiple of 48 for integer cells; 672 = 48 × 14 | The false sentence is replaced by the lcm(16, 24) = 48 argument; 672 = 48 × 14; the 4×4 table alone needs only 389 rows | §10.2 | Arithmetic in the document; a test recomputes cell counts | **Resolved** |
| **U21** | The 4×5 Stage S table conflicts with 4-level discretisation | Make both 4×4 or define the fifth level | The **fifth level is defined**: action neuron with the highest evaluation spike count, fifth level for none, ties to the lowest index; the table stays 4×5 with df 12 and floor 0.000404 at 21,440 rows | §5 H6, §10.2 | Definition is in H6; the floor table uses df 12 at 21,440 | **Resolved** |
| **U22** | 0.017 and 0.0167 give 637 vs 648; both are used | Label the column and add a footnote; do not mix tolerances | The column is computed at 0.0167 and the footnote states that 0.017 would give 637 and is not used | §10.2 footnote | The single criterion value appears once | **Resolved** |
| **U23** | 80%-power 0.013/0.016 bits use α = 0.05 while the family uses Holm α = 0.005 | State α per row; use the Holm threshold for the confirmatory family | The power table has separate α = 0.05 and α = 0.005 columns; the confirmatory figure is 0.0166/0.0215 | §10.3 | Each row's α is in the column header | **Resolved** |
| **U24** | Stage S 40 "seeds" share substrate 20261114; the CI ignores substrate uncertainty | Use 40 substrate seeds or state the limitation | **134 independent substrate seeds**, each generating its own graph instance and initial weights; the 20261114 substrate is not reused | §8.7, §10.1, §10.5 | Substrate-seed count is an independence unit; Stage S cluster inference is on substrate | **Resolved** |
| **U25** | "Phase 5F contrast reproduced at 40 seeds" is a new replicate | Include the original 10 streams or relabel as a new replicate | Relabelled throughout as a **new replicate**: "the Phase 5F direction is re-estimated on the new replicate" | §8.7, §12.7, §12.8 | Wording check; no "reproduced" claim remains | **Resolved** |
| **U26** | Stage S `fixed_complete` is described as using the same seed list as 5F, which used 10/40 vs 40/80 | Say "same substrate and protocol family; 40 new streams, 80 evaluation episodes." | Exact wording adopted: same substrate and protocol family, **134 new streams**, 80 evaluation episodes each | §8.7 | Text check | **Resolved** |
| **U27** | 537 MB omits the repeats; 2.8 h is inconsistent with its components; 1,900 MB optional is low | 555 MB mandatory; 3.0–3.2 h; 2.0 GB optional; add repeat storage and the Stage S anchor | Mandatory **929 MB** and **4.08 h** for this design, optional **2.5 GB**; the delta from the audit's V1 figures is reconciled line by line in §3 | §13.2, §13.4 | Arithmetic table; each stage recomputed from its run count | **Resolved** (§3 reconciles the difference) |
| **U28** | §5.1 refers to a non-existent §9.9; §10.2 says "20/20" for Stage R; 99.5% presence vs 5% exclusion | Fix the cross-reference; 336/336 for Stage R; one missing-data threshold | All cross-references verified; seed split is **336/336**; one threshold: **exclusion ≤ 0.5%** (equivalently ≥ 99.5% presence) | §7.5, §11.7, §12.1–12.2 | Link check; a single number appears in both places | **Resolved** |
| **U29** | Six tests do not cover copy-on-record, RNG, the step contract, install/restore or the time base | Add T1–T12; make T1–T3 and T4 mandatory | **T1–T12** are specified with pass conditions; T1–T4 are mandatory before G2 | §7.5 | Test table; G2 requires them | **Resolved** |
| **U30** | `excitatory_current_pa` returns the live `_exc` array; the schema does not require a copy | Require `.copy()`; add T5 | Clause 3 requires a copy of every retained array; T5 mutates `_V`/`_exc` after recording and asserts the stored panel is unchanged | §7.4 clause 3, §7.5 T5 | T5 | **Resolved** |
| **U31** | The O2 panel "up to 200 first-hop" has no selection rule | Pre-register a rule (top 200 by mean input current, ties by index) and record it | Full rule: 232 `STIM` + top 200 `H1` by mean input current (ties by ascending index) + top 20 `DESC` + 6 pool neurons ≤ 458; recorded in fields 10 and 27 | §7.7 | Panel IDs written to the record; reproducible from the archived run | **Resolved** |
| **U32** | The 5 ms E7 window is short relative to `tau_m` = 20 ms and the 1 ms delay; no sensitivity | Pre-register 10 ms and 20 ms sensitivity; report per-trial proportions | **10 ms primary** (10 ms = delay + 3.6 `tau_exc`), 5 ms and 20 ms sensitivities; per-trial indicator is the unit | §5 H4, §11.1 E7 | Endpoint row states the windows; sensitivity reported | **Resolved** |
| **U33** | The P2 screen's sensitivity is reduced by the zero-control rule, and the protocol attributes a miss only to compute | State the effective pass probability with the control rule; use ≤ 2/40 | The rule is replaced by an effect-size floor with a **stated sensitivity curve** (0.99/0.83/0.56/0.20 at 30/20/15/10%), and the document says plainly that a 15% true rate is missed ~44% of the time | §8.4 | The curve is printed before the run | **Adopted with stated deviation** (an explicit screen with a published curve replaces "≤ 2 of 40" alone) |

### 2.3 Recommended issues, U34–U36

| ID | Original issue (audit wording, condensed) | Required correction | Revision 2 decision | Section | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **U34** | The four-point drive series coarsely brackets the threshold | Add a 1.5× geometric sweep (100–1200 pA) if the four-point pilot fails | **G3b escalation to 1600 and 2000 pA**, 160 runs (40 `REAL` and 40 `NO_STIM` per drive), declared in advance and labelled exploratory. Downward resampling was rejected: 100 pA is below the 150 pA rheobase, so such an arm is guaranteed null, whereas 4H.4 measured a 6.926 mV first-hop shortfall at the top of the current range, which is the direction where information lies | §15 G3b | The escalation is a review gate with a fixed design; it cannot relabel a failed confirmatory gate | **Adopted with stated deviation** (upward rather than geometric sweep; reason given) |
| **U35** | Stage S is independent of H1–H5 and its power is the weakest part | Defer Stage S to its own phase unless H6 is required | **Not deferred.** H6 is a declared hypothesis of this phase, and the power defect that motivated the recommendation is fixed by 134 substrate clusters (power 0.803 at the 0.05-bit MDE). Deferring would leave H6 unresolved while the recording campaign runs; the Stage S verdict is reported independently so a failure cannot contaminate the Stage R verdict | §8.7, §12.9 | §12.9 keeps Stage S verdicts separate | **Not adopted, justified** |
| **U36** | `E_random_matched_mapping` was dropped; a descriptive random-mapping arm is cheap | Add a 20-trial random-mapping arm at `d*`, descriptive | `RANDOM_MAPPING` added at **40 trials** (paired on 40 of the 672 seeds), descriptive only, in no test. 40 rather than 20 because a descriptive proportion at n = 20 has a ±22-point 95% interval, which is too coarse to distinguish "mapping matters" from "it does not" | §8.6, §9 | The arm is outside the confirmatory family and cannot be promoted | **Adopted with stated deviation** (40 rather than 20 trials; reason given) |

## 3. Recalculated quantities

Everything the audit objected to numerically is recomputed here. No figure is
carried over from revision 1 without re-derivation.

### 3.1 Seeds, runs and independence

| Quantity | Revision 1 | Audit finding | Revision 2 | Derivation |
| --- | ---: | --- | ---: | --- |
| Stage P runs | 324 | 324 verified | **964** | 6 arms × 4 drives × 40 = 960, plus 4 `SINGLE_H1_SPIKE` |
| Stage R condition-runs | 2,688 | 2,688 verified | **2,688** | 672 seeds × 4 conditions |
| Stage R repeats | 134 | 134 verified | **136** | 68 recording-enabled + 68 recording-disabled |
| Stage R descriptive arm | 0 | U36 | **40** | `RANDOM_MAPPING`, paired on 40 seeds |
| Stage R total runs | 2,822 | 2,822 verified | **2,864** | 2,688 + 136 + 40 |
| BANC runs, all stages | 3,146 | 3,146 verified | **3,828** | 964 + 2,864 |
| Unique noise seeds | "2,688" | **wrong** (U6) | **672** | one seed per trial, reused across four conditions |
| Unique substrate seeds | 40 ("seeds") | share 20261114 (U24) | **134** | independent graph instance and initial weights per seed |
| Stage S episodes | 19,200 | 19,200 verified | **64,320** | 134 × 2 × 240 |
| Stage S evaluation rows | 6,400 | 6,400 verified | **21,440** | 134 × 2 × 80 |
| Stimulus event records | 43 | 43 records (U7) | **43** | unchanged count, corrected interpretation |
| Distinct stimulus tracks | "43" | **24** (U7) | **24** | per-level 13/11/1/5, union 24 because six tracks cross levels |

The Stage P growth from 324 to 964 is the sum of three corrections that each
require more trials: P1a needs 40 `STIM`-bearing trials per drive (U4), P2s needs
a `SHUFFLED_MASK` arm at every drive so specificity is gated before Stage R (U5),
and every presence arm moves from 20 to 40 trials so the gates are tests rather
than coincidence detectors (U3, U15, U33).

### 3.2 Estimator bias

| Table | df | N needed for floor ≤ 0.0167 | Floor at N = 672 | Floor at N = 21,440 |
| --- | ---: | ---: | ---: | ---: |
| 4×4 primary | 9 | 389 | 0.009661 | 0.000303 |
| 4×3 collapsed | 6 | 260 | 0.006441 | 0.000202 |
| 4×5 Stage S | 12 | 519 | 0.012881 | 0.000404 |
| 6×4 sensitivity (binding) | 15 | 648 | 0.016102 | 0.000505 |

**672 is derived, not asserted.** The binding constraint is integer cells in the
16-cell 4×4 and 24-cell 6×4 tables, so `N` must be a multiple of
lcm(16, 24) = 48. The smallest multiple of 48 at or above 648 is 672 = 48 × 14.
The earlier justification ("multiple of 4 and 6, above 648") was false because
648 already satisfies it (U20). The confirmatory 4×4 table alone needs only 389
rows, so **672 is a precision choice for the sensitivity table, not a power
requirement for the confirmatory family**.

### 3.3 Statistical power, separated from bias

| Requirement | Quantity | Value | Consequence |
| --- | --- | ---: | --- |
| Bias floor at N = 672, 4×4 | expected upward bias | 0.0097 bits | 19% of the 0.05-bit MDE |
| Bias floor at N = 672, 6×4 | expected upward bias | 0.0161 bits | 32% of the MDE; the binding table |
| Trial-level SE, 4×4 | plug-in standard error | 0.00455 bits | — |
| Trial-level MDE, 4×4, α = 0.05 | 80% power | 0.0128 bits | 11.0 SE |
| Trial-level MDE, 4×4, α = 0.005 | 80% power | 0.0166 bits | 13.6 SE |
| Trial-level MDE, 6×4, α = 0.005 | 80% power | 0.0215 bits | 8.5 SE |

The 0.05-bit MDE is 11 standard errors at trial level, so trial-level power is
effectively 1.0. **That is a statement about the multinomial table, not about the
corpus.** With 24 tracks the cluster interval is much wider, and §11.6 of V2
restricts every generalisation claim accordingly.

### 3.4 Gate operating characteristics

| Gate | Test | Contrast | Pass probability |
| --- | --- | --- | ---: |
| P1a / P1 | one-sided Fisher, α = 0.0125, 40 vs 40 | 50% vs 5% | 0.99 |
| P1a / P1 | same | 30% vs 2% | 0.88 |
| P1a / P1 | same | 20% vs 2% | 0.49 |
| P2a screen | ≥ 6/40 and ≥ 4/40 above control | 30% vs 5% | 0.99 |
| P2a screen | same | 20% vs 2% | 0.83 |
| P2a screen | same | 15% vs 2% | 0.56 |
| P2a screen | same | 10% vs 2% | 0.20 |
| P2b screen | ≥ 2/40 and ≥ 2/40 above control | 10% vs 2% | 0.92 |
| P2b screen | same | 5% vs 0% | 0.60 |
| Control upper bound | Clopper–Pearson, 0/40 | — | 0.0722 |

The audit's objection (U15, U33) was that the quoted 0.803 was a Fisher-only
number applied to a conjunction. That is fixed by reporting the conjunction's own
probabilities and by not quoting the Fisher-only figure as gate power.

### 3.5 Stage S

| Clusters | SE | MDE, α = 0.05 | MDE, α = 0.005 | Power at 0.05 bits, α = 0.005 |
| ---: | ---: | ---: | ---: | ---: |
| 40 (revision 1) | 0.0250 | 0.0700 | 0.0912 | 0.21 |
| 79 | 0.0178 | 0.0498 | 0.0649 | — |
| **134 (adopted)** | **0.0137** | **0.0383** | **0.0498** | **0.803** |

The SD of 0.15813337 bits comes from the Phase 6C C-06 contrast
(`I(cue; action)`, SE 0.05000616, floor 0.16230319). It is a **proxy**: the
Phase 6C design differed in substrate count. The protocol therefore fixes a
realized-MDE rule before Stage S runs: if the observed between-substrate SD
implies an MDE above 0.05 bits at 134 clusters, E10 is demoted to exploratory
whether or not its point estimate looks favourable (V2 §10.5; retained as RA-6).

### 3.6 Resources

| Quantity | Revision 1 | Audit (for revision 1's design) | Revision 2 | Reconciliation |
| --- | ---: | ---: | ---: | --- |
| Stage P time | 0.23 h | 0.23 h | **0.68 h** | +640 runs × 2.54 s = +0.45 h |
| Stage R time | 1.98 h | 1.99 h | **2.02 h** | +42 runs × 2.54 s = +0.03 h |
| Stage S time | 0.5 h (est.) | 0.26–0.4 h | **0.88 h** | 64,320 / 20.3 episodes/s; +0.38 h over the 0.5 h estimate |
| Analysis | 0.5 h | 0.5 h | **0.5 h** | unchanged |
| **Total time** | 2.8 h (inconsistent) | 3.0–3.2 h | **4.08 h** | 3.22 + 0.45 + 0.03 + 0.38 |
| Stage P storage | 44 MB | 44 MB | **130 MB** | 964 × 135 kB |
| Stage R storage | 363 MB | 381 MB | **387 MB** | 2,864 × 135 kB, repeats included |
| Stage S storage | 120 MB | 120 MB | **402 MB** | 64,320 × 6.25 kB |
| Analysis storage | 10 MB | 10 MB | **10 MB** | unchanged |
| **Total storage** | 537 MB (omits repeats) | 555 MB | **929 MB** | 555 + 86 + 6 + 282 |
| Optional O2+O3 | 1,900 MB | 2,035 MB | **2,504 MB** | 929 + 2,864 × 550 kB = 2.5 GB |
| Peak memory | estimate | 0.97 GiB free measured | **0.3–0.5 GiB estimate** | retained as RA-4 |

The audit's own numbers (555 MB, 3.0–3.2 h, 2.0 GB) were correct **for revision
1's design**. Revision 2 is larger because the gates require it, so the honest
mandatory figure is 929 MB and 4.08 h. The arithmetic above reconciles the two
line by line rather than replacing one unexplained number with another.

## 4. Integrity of the originals and of protected files

Verified after the revision was written. The two audited documents and the audit
itself are byte-identical to the versions that were reviewed; nothing in
`brain/`, `sensory/`, `motor/`, `plasticity/`, `information/`, `datasets/` or
`README.md` was touched.

| File | SHA-256 | State |
| --- | --- | --- |
| `reports/PHASE_6D_RECORDING_PREREGISTRATION.md` | `e27db60c1ba5c80cac033508610fc8d2e817aa3aef9d8a9f59f2c841ffbe748c` | unchanged |
| `reports/PHASE_6D_RECORDING_PREREGISTRATION.json` | `c3fd6fad0ace629e293a7bb86fa5552dcae72a2f1e8410edf8f5bc45633e7036` | unchanged |
| `reports/PHASE_6D_INDEPENDENT_AUDIT.md` | `19c75033c792a6e9e0d3ebee6fbc0a4b9f69236fc19bc68cb90d393f3503c622` | unchanged |
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | unchanged |

Revision 2 is a **new** document set; it supersedes the audited files without
overwriting them:

| New file | Purpose |
| --- | --- |
| `reports/PHASE_6D_RECORDING_PREREGISTRATION_V2.md` | corrected protocol |
| `reports/PHASE_6D_RECORDING_PREREGISTRATION_V2.json` | machine-readable companion |
| `reports/PHASE_6D_AUDIT_CORRECTION_MATRIX.md` | this document |

Frozen hashes of the revision at the time of writing:

| New file | SHA-256 |
| --- | --- |
| `PHASE_6D_RECORDING_PREREGISTRATION_V2.md` | `22a57aedade89787fe5704d9e714dcd409dc6c6aa619647a09fa89b533d91efe` |
| `PHASE_6D_RECORDING_PREREGISTRATION_V2.json` | `a21b7b7bcb2aeaafa4a7bd5108a513fc2667b823db4a4230b6ecc6cf1765355c` |

The matrix itself is hashed and recorded at G0, after human review, so that the
protocol and its correction trail are frozen together.

Nothing was staged, committed or pushed. No simulation, recording, training or
instrumentation was executed or implemented.

## 5. Items retained as unresolved

Seven items cannot be settled from evidence that exists before execution. They
are listed in V2 §14.3 and repeated here because "resolved" would be false for
them at the level of empirical fact, even though each has a fixed handling rule.

| ID | Item | Why it stays open | Handling rule (pre-registered) |
| --- | --- | --- | --- |
| **RA-1** | Whether any tested drive produces second-hop propagation | Requires Stage P, which this revision does not execute | P2a/P2b screens; a failure is a documented stop, not a null campaign |
| **RA-2** | Whether descending or motor populations are reachable | Same; 4H evidence is negative | P3/P3a; "untestable" is a reported outcome |
| **RA-3** | Generalisation beyond 24 tracks, and `OBST_NEAR` beyond one track | The archived corpus is fixed; new perception is out of scope | Track-cluster intervals; `OBST_NEAR` descriptive; no cross-corpus claim |
| **RA-4** | Peak memory with the panel enabled | Estimated at 0.3–0.5 GiB, not measured | Single process, pre-flight free-memory check, resume from manifest |
| **RA-5** | Recorder wall-time overhead | Unmeasured until the recorder exists | First 40 Stage R runs are the calibration sample; re-plan if median > 3.5 s |
| **RA-6** | The Stage S between-substrate SD | 0.1581 bits is a proxy from a different design | Realized-MDE rule; E10 demoted if MDE > 0.05 bits |
| **RA-7** | Behavioural validity of the decoder | The decoder is a hand-written rule, not a motor command | E8/E9 labelled decoder-mediated; excluded from the verdict above E2 |

These are **not** protocol defects. They are facts that only running the
experiment can supply, and each has a rule that applies regardless of the
direction of the outcome. That distinction is the basis for the verdict in §7.

## 6. Cross-document consistency checks

| Check | Method | Result |
| --- | --- | --- |
| Every constant in V2 appears in exactly one place | Manual sweep of §8, §10, §13 | Pass; `configs/phase_6d_recording.yaml` is required to reproduce them at G1 |
| V2 MD and V2 JSON agree | Field-by-field comparison of counts, gates, seeds, resources | Pass; the JSON carries a `consistency` block |
| No stale cross-reference | All `§` references resolved against the heading list | Pass; two stale references repaired during this revision (H6 → §10.5, executive summary → §14.2) |
| Historical Phase 4H / 5 / 6B–6C numbers unchanged | Compared against V1 §3 and the audit's quotations | Pass; no historical figure was altered |
| No claim stronger than the evidence | Read of §0, §5, §12, §17 | Pass; non-claims and the E1–E2 ceiling are stated in all three |
| No protected file modified | SHA-256 before and after (§4) | Pass |
| Nothing staged | `git status --porcelain` inspected, no `git add` executed | Pass |

## 7. Verdict

**READY WITH REMAINING LIMITATIONS.**

All 36 issues are resolved at protocol level, and none is waived. Twenty-nine of
the thirty-six are closed outright. Seven carry a qualified status and are
recorded above with their reason:

- **U7 and U8** are resolved in the protocol but leave an empirical item
  (RA-3, RA-6) that only execution can close.
- **U14, U33, U34 and U36** are resolved by a remedy that differs from the
  audit's suggested remedy; the deviation and its justification are stated in
  the row.
- **U35** is the only recommendation not adopted: Stage S is retained because
  H6 is a declared hypothesis and 134 clusters fix the power defect that
  motivated the deferral.

The seven blocking findings A1–A7 are all resolved. The revision is not marked
"ready for human review" without qualification because RA-1 to RA-7 are facts
about the system that no document can supply, and three of them (RA-4, RA-5,
RA-6) can change the cost or the strength of the result. Approving this revision
approves the **design** and authorises **Stage P**; it does not approve any
propagation, information-flow, plasticity or biological conclusion.

### Status tally

| Status | Count | Issues |
| --- | ---: | --- |
| Resolved | 29 | U1–U6, U9–U13, U15–U32 |
| Resolved, limitation retained | 2 | U7, U8 |
| Adopted with stated deviation | 4 | U14, U33, U34, U36 |
| Not adopted, justified | 1 | U35 |
| **Total** | **36** | |
