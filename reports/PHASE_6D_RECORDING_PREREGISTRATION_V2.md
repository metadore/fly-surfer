# Phase 6D — Recording Campaign Pre-Registration, Revision 2

**Status:** DESIGN ONLY — REVISION 2 — NOT EXECUTED  
**Phase:** 6D  
**Document type:** Pre-registration of a recording campaign, not a result  
**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`  
**Date:** 2026-11-11  
**Supersedes:** `reports/PHASE_6D_RECORDING_PREREGISTRATION.md` (SHA-256 `e27db60c1ba5c80cac033508610fc8d2e817aa3aef9d8a9f59f2c841ffbe748c`) and `reports/PHASE_6D_RECORDING_PREREGISTRATION.json` (SHA-256 `c3fd6fad0ace629e293a7bb86fa5552dcae72a2f1e8410edf8f5bc45633e7036`)  
**Correction authority:** `reports/PHASE_6D_INDEPENDENT_AUDIT.md` (SHA-256 `19c75033c792a6e9e0d3ebee6fbc0a4b9f69236fc19bc68cb90d393f3503c622`), issues U1–U36 including blocking findings A1–A7  
**Correction matrix:** `reports/PHASE_6D_AUDIT_CORRECTION_MATRIX.md`  
**Machine-readable companion:** `reports/PHASE_6D_RECORDING_PREREGISTRATION_V2.json`

**Final verdict of this revision:** **READY WITH REMAINING LIMITATIONS** (§17).

## 0. Revision scope and non-claims

This revision responds to the independent audit of the original pre-registration.
It is a design document. Nothing in it has been run: no simulation was executed,
no recording was generated, no model was trained, no neural architecture or
parameter was changed, and no archive was rewritten. No file under `brain/`,
`sensory/`, `motor/`, `plasticity/` or `information/` was modified.

The original pre-registration and the independent audit are unchanged. This
revision does not delete any of their content; it corrects the specific defects
the audit identified and records every correction in the matrix.

**What Revision 2 changes, in one paragraph.** Propagation gates are split into
six presence and specificity gates that are read at all four drive strengths;
the mandatory propagation gate no longer conflates first-hop with second-hop
activity and no longer fails on a single chance control spike. Stimulated
sensory activation, second-hop activity, descending recruitment beyond the nine
directly innervated descending neurons, charge-form specificity, feature
specificity, decoder reachability and motor recruitment are now distinct
decisions with distinct criteria. Direct first-hop current injection is
retained **only** as a capability control and is not accepted anywhere as
evidence of natural sensory propagation. The stimulus corpus is described by
its actual structure — 24 distinct tracks, not 43 independent events — and
resampling is at the track level. The seed, condition-run and trial counts are
separated. Stage S is powered against a measured between-cluster variance
rather than declared at a criterion its design could not reach. The recording
contract is specified down to the post-step reset artefact, the event-time
rebasing transform, and records with recording enabled must hash-match records
with recording disabled. Run counts, runtime, storage and memory are
recomputed from measured anchors.

**Non-claims carried forward unchanged:**

1. A mutual-information estimate is not causal influence. It measures shared
   information between two declared variables, not transmission, mechanism or
   direction.
2. A decoder label (LEFT, RIGHT, JUMP) is not a biological motor command.
   Decoder-mediated information is consistency with a declared decision rule.
3. A simulated spike is not a recorded biological spike. Any result from this
   protocol is evidence about the implemented model, at best at internal
   evidence grade E1–E2 as defined in Phase 4H.5.
4. A propagation-positive pilot establishes that the model can transmit the
   declared drive under a calibrated setting. It does not establish that a fly
   does so.
5. Structural connectivity does not imply functional transmission. Every
   hypothesis is stated as a question about observed spikes, never as an
   inference from the adjacency matrix.
6. **Direct first-hop current injection is a capability control, not evidence
   of natural sensory propagation.** A positive direct-injection result shows
   that the H1→H2 synapse can transmit under an artificial rectangular current.
   It says nothing about whether the sensory encoder's drive propagates.

## 1. Executive summary

### 1.1 What is missing, and why

Phase 6B/6C estimated entropy and mutual information only on aggregate archived
variables because no completed experiment persisted spike trains together with
their sensory inputs. The four declared-but-unavailable endpoints (6B U01–U04),
the four structural gaps 6A listed (MD-04 to MD-07), and the nine infeasible
analyses 6A recorded (IF-01 to IF-09) all reduce to one archival fact: there is
no per-trial, per-neuron recording paired with its stimulus. Phase 6D is the
recording campaign that would supply it.

### 1.2 Design in one table

| Stage | Purpose | Runs / episodes | Gate to the next stage |
| --- | --- | ---: | --- |
| P | Propagation pilot: presence and specificity gates at four drives | 964 runs | P0, P1a, P1, P2a, P2b, P2c, P2s, P3, P3a |
| R | BANC recording campaign at the selected drive `d*` | 2,864 runs | recording-integrity criteria |
| S | Fixed-versus-plastic neural recording on the Phase 5 substrate | 64,320 episodes | Phase 5F direction re-estimated on a new replicate |
| A | Pre-registered information analysis and report | 0 new simulations | none |

### 1.3 Condition set

**Stage P (seven arms):** `REAL`, `NO_STIM`, `PEAK_MATCHED_RECT`,
`SHUFFLED_MASK`, `MATCHED_CHARGE` (descriptive only), `DIRECT_INJECTION`
(capability control only), `SINGLE_H1_SPIKE` (calibration only).

**Stage R (four conditions plus one descriptive arm):** `REAL`,
`SHUFFLED_MASK`, `PEAK_MATCHED_RECT`, `NO_STIM`; plus `RANDOM_MAPPING`
(40 descriptive trials).

### 1.4 Sample size, with bias and power separated

- **Estimator bias.** 672 trials per confirmatory condition keeps the worst-case
  analytic MI bias floor at 0.0161 bits for the 6×4 sensitivity table, which is
  32% of the declared 0.05-bit minimum detectable effect. This is a *bias*
  requirement. It is met.
- **Statistical power, trial level.** At 672 rows the 4×4 plug-in standard error
  is 0.00455 bits; the 0.05-bit MDE is 11.0 standard errors. Trial-level power
  is effectively 1.0. This holds only for the trial-level estimand.
- **Statistical power, corpus level.** The corpus is **24 distinct tracks**, and
  one level is a single track. 672 trials do **not** buy 672 independent
  stimuli, and the track-cluster interval is much wider than the trial-level
  interval. This is stated in §11.6 and §14.2, and no claim beyond the sampled
  tracks is made.
- **Gate power.** Stage P uses 40 trials per cell, not 20. The presence gates
  then have 0.99 power at a 50% vs 5% prevalence contrast and 0.88 at 30% vs
  2%, and the control rule is a test with a valid null rather than a
  zero-tolerance coincidence rule.
- **Stage S.** 134 independent substrate clusters, which is the number required
  for an 80%-power 0.05-bit MDE at the Holm smallest threshold (α = 0.005).
  At 40 clusters the MDE is 0.070 bits at α = 0.05 (power 0.52 at a 0.05-bit
  effect) and 0.091 bits at α = 0.005 (power 0.21), which is why 40 is rejected.

### 1.5 Feasibility

| Quantity | Value | Anchor |
| --- | --- | ---: |
| BANC runs, all stages | 3,828 | 964 + 2,864 |
| Phase 5 episodes | 64,320 | 134 × 2 × 240 |
| Mandatory wall time | ≈4.1 h | 2.54 s per BANC run; ≥20.3 episodes/s |
| Mandatory storage | ≈929 MB | 135 kB per BANC trial; 6.25 kB per episode |
| Storage with O2+O3 diagnostics | ≈2.5 GB | adds 550 kB per Stage R trial |
| Peak resident memory | 0.3–0.5 GiB (estimate) | 0.97 GiB free at the Phase 6A audit |

The required new code is additive and lives only in `experiments/phase_6d/`.

## 2. Corrections incorporated in this revision

Every correction is itemised in `reports/PHASE_6D_AUDIT_CORRECTION_MATRIX.md`
with its original issue, the corrected section, the verification method and its
status. The seven blocking findings are resolved as follows.

| Finding | Correction in this revision |
| --- | --- |
| **A1** — `d*` fixed at P1, P2 read only there | Presence gates are read at **all four drives**; `d*` is the lowest drive at which P1a, P1, P2a and P2b all pass; P2 failure is only declared after all four drives fail (§8.3). The four-drive reading costs zero additional simulations because the runs already exist. |
| **A2** — P2 conflates first and second hop; zero-control rule | P2 is replaced by **P2a (H2 only)**, **P2b (DESC excluding the nine first-hop DNs)**, **P2c (charge-form specificity)** and **P2s (feature specificity)**. The zero-tolerance control rule is removed; presence gates use a test with a valid null and a stated effect-size floor (§8.4). |
| **A3** — "2,688 unique seeds" | Seed = **672** (reused across four conditions); condition-run = 2,688; trial = 672 per condition; analyses are **paired by seed** (§10.1, §11.3). |
| **A4** — "43 distinct events" | **43 event records from 24 distinct tracks**; per-level records 20/15/2/6 and per-level tracks 13/11/1/5; the union is 24 because six tracks appear in two levels. Resampling is at track level; `OBST_NEAR` is not estimable (§8.5, §11.6). |
| **A5** — Stage S MDE unreachable | Stage S is increased to **134 independent substrate clusters**, giving an 80%-power 0.05-bit MDE at α = 0.005. The 0.1581-bit SD is declared a proxy with a pre-registered fallback rule (§10.5). |
| **A6** — post-step reset artefact | The recorder contract requires **threshold substitution or pre-reset sampling**, copy-on-record, zero RNG consumption, one recorder, and a declared time base, with tests T1–T12 (§7.4, §7.5). |
| **A7** — event times do not fit the trial | A declared **event-time transform**: every selected event is re-based to `time_ms = 50.0` and the drive decays over `decay_ms = 100.0`, so injected current ends at the declared offset of 150 ms. The original archive time is recorded (§8.5). |

## 3. Existing evidence and limitations, carried forward unchanged

Everything in this section is carried forward from Revision 1 and from the
historical phase reports without reinterpretation. Phase 6D does not re-grade
any of it and does not use it to make the proposed experiment look promising.

### 3.1 Phase 4H — established findings

| ID | Finding (unchanged) |
| --- | --- |
| PF-4H-1 | Sensory-to-BANC downstream propagation was **not** established. |
| PF-4H-2 | Actual sensory events did **not** produce a downstream response distinguishable from the tested controls. |
| PF-4H-3 | The highest evidence grade awarded was **E2**, and only for infrastructure, reproducibility and parameter sensitivity. |
| PF-4H-4 | No validated motor command was established. |

Supporting quantities, as recorded in `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md`
and `reports/PHASE_4H5_STATISTICAL_ASSESSMENT_AND_EVIDENCE_GRADING.md`:

- 27/27 runs complete, 47/47 configuration checks, 6/6 repeat pairs hash-equal.
- Condition B produced 3,562 spikes on the full stream, **all inside the 232
  stimulated neurons**; 171 of 232 stimulated neurons were active.
- Synaptic current reached 473 of 607 first-hop targets. The closest first-hop
  neuron ended at −56.926 mV, **6.926 mV below the −50 mV threshold**. Zero
  first-hop spikes.
- Second-hop current was exactly zero. Descending neurons received current
  (9 neurons, maximum 67.21 pA, −62.158 mV) and did not spike.
- Motor neurons received no current from the annotation mapping. All 67 decoder
  windows in condition B were NEUTRAL.
- Condition F (uniform matched charge, 46.696 pA/neuron) was silent: below the
  150 pA rheobase. Condition G (50 pA background + 50 pA noise) was silent.
- B versus C total-spike differences changed sign across streams (−198, +117,
  +108). No downstream or decoder endpoint distinguished B from any control.
- Nine descending neurons are direct first-hop targets of the stimulated
  sensory population (`reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md:216,303`);
  the remaining 1,307 descending neurons are not.

Phase 4H.5's own recommendation was a pre-registered **sensory-drive threshold
and propagation calibration** with a direct first-hop current-injection positive
control and a single-first-hop-spike test. Stage P implements that
recommendation and extends it with the gates the audit required.

### 3.2 Phase 5 — established findings

| ID | Finding (unchanged) |
| --- | --- |
| PF-5-1 | Controlled synthetic-task plasticity improved success relative to fixed complete wiring. |
| PF-5-2 | Biological interpretation of that improvement remains **INCONCLUSIVE**. |
| PF-5-3 | The selectivity criterion **failed**. |
| PF-5-4 | Task improvement must not be read as proof of biological learning. |

Recorded quantities: fixed_complete 0.795 ± 0.084, plastic_complete
0.945 ± 0.023, paired difference +0.150, sign-flip p = 0.00195, Holm-adjusted
p = 0.00781, Cohen's dz = 2.012, 10/10 seeds above zero. Action selectivity
0.192, at or below the four-action chance rate of 0.250. The substrate is a
synthetic 36-node task graph, not the BANC connectome. All ten Phase 5F cells
share `substrate_seed = 20261114`
(`experiments/results/phase_5f/comparison_raw.json`).

### 3.3 Phase 6A–6C — established findings

| ID | Finding (unchanged) |
| --- | --- |
| PF-6-1 | Archived-data entropy and mutual-information analyses are complete, with declared limitations. |
| PF-6-2 | Plasticity did **not** increase cue-to-action mutual information in C-06 (−0.086 bits, p = 0.125, Holm 0.25). |
| PF-6-3 | Decoder-mediated MI is **not** biological neural-to-motor information. |
| PF-6-4 | Existing archives do **not** support the missing neural-level analyses. |

Endpoints the archive could not support, recorded rather than proxied (6B §10,
6C §7): spike-train entropy, population-response entropy, membrane-potential
entropy, cue-to-population-code MI, cue-to-spike-count MI, and neural-to-reward
MI. Reasons: no per-neuron spike trains except one 74-spike smoke run; aggregate
spike counts constant within conditions; membrane potentials never serialised;
no stored run pairing stimulus with spikes. The Phase 6C between-seed SD of
`I(cue ; action)` is 0.15813337 bits over 10 seeds (SE 0.05000616), with the
bias floor at that sample 0.16230319 bits.

## 4. Verified implementation interfaces

This table was produced by reading the source, not the reports. It is the only
basis for the schema in §7. Line numbers refer to the audited revision.

| Interface | File:line | Verified behaviour | Consequence for the recorder |
| --- | --- | --- | --- |
| `LIFPopulation.step` | `brain/neuron_model.py:122–157` | Integrates, then `self._V[spikes] = params.reset_potential_mv` (line 154), then returns `np.flatnonzero(spikes).astype(np.int32)` (line 157). | After `step`, a spiking neuron reads **−68 mV**, not threshold. The recorder must substitute `threshold_mv` for the returned indices, or sample before the reset. |
| `SpikeRecorder.record` | `brain/neural_activity.py:59–73` | Preallocated float32 times, int32 indices; stamps `(step_index + 1) * dt_ms`; raises `SpikeCapacityExceeded` instead of truncating. | The first spike is stamped at 0.5 ms, not 0. Bin and window alignment must be declared (§7.6). |
| `SpikeRecorder.spike_counts` | `brain/neural_activity.py:75–79` | Allocates a full `n_neurons` int64 array (1.38 MB at 172,433). | Call once per trial. |
| `BancSimulator.run` | `brain/banc_simulator.py:393–480` | Local `rng = np.random.default_rng(self.seed)` (404); one `rng.normal` per step (456); `input_schedule.apply` (464); `neurons.step(current)` (470); `recorder.record` (475); `synapses.propagate(spikes)` (480). No callback. | The only hook is an instance-level wrapper on `sim.neurons.step`. It must not consume randomness or reorder these calls. |
| `BancSignedSynapses.excitatory_current_pa` | `brain/banc_simulator.py` (property) | Returns the live `_exc` array. | Any retained array must be copied. |
| `BancSignedSynapses.synaptic_current_pa` | same | Computes `_exc − _inh` into a new array each call. | Safe for aliasing; allocates per call. |
| `BancEventDrive` | `brain/banc_sensory_adapter.py:532–700` | Onset is the event's `time_ms`; current `= response * current_pa * pulse_gain`; decays linearly over `decay_ms` (default 150 ms); uses absolute timestamps. | Requires the event-time transform in §8.5, and `decay_ms` must be set explicitly. |
| `ConstantChargeDrive` | `brain/banc_sensory_adapter.py:779–860` | `current_pa = total_charge / (n_neurons * duration_ms)`, uniform over the stimulated set. | Peak current is much lower than a concentrated pulse; at the Phase 4H anchor it was 46.696 pA/neuron, below rheobase. |
| `shuffle_feature_identities` | `brain/banc_sensory_adapter.py:883–903` | Permutes feature-value payloads **across events**; preserves timestamps. | It is a payload permutation, not a feature→population remapping. §8.6 restates it correctly. |
| `BrainSimulator` | `brain/brain_simulator.py:264` | Calls `self.recorder.record(...)`; no callback. | Not usable on BANC (`BancConnectome` lacks `vocabulary`/`nt_code`). |
| `PlasticSimulator.step_callback` | `plasticity/plastic_simulator.py:298–319` | Called after `engine.observe_step`; a non-`None` return becomes the reward and bypasses `reward_provider`. | A recording callback **must return `None`** and must not call `engine.learn` or mutate `WeightState`. |
| 4H instance wrapper | `experiments/phase_4h/analyse_sensory_roundtrip.py:816–832` | Saves the original `step`, substitutes `max_v[spikes] = threshold_mv` (828), returns spikes unchanged, rebinds the attribute. | The proven pattern for G2's hash check. It records per-neuron **maxima**, not trajectories. |

Two consequences follow directly.

1. **Spike trains are already a supported production output.** No new neural
   code is needed to persist them.
2. **Membrane potentials and synaptic currents are readable only in memory**,
   through an instance-level hook, and only for a declared panel. Full-population
   recording would cost 172,433 × 600 × 8 B ≈ 828 MB per 300 ms run (≈4.55 GB
   for 3,300.5 ms, Phase 6A `RK-07`) against 0.97 GiB free. It is excluded.

## 5. Research hypotheses

Six hypothesis families are declared. Each is a question about observed spikes
in declared populations, not an inference from the structural graph.

Population and code definitions:

| Symbol | Population | Size | Definition |
| --- | --- | ---: | --- |
| `STIM` | stimulation-mapped sensory input population | 232 | Mapped by the 7-feature annotation mapping |
| `H1` | first-hop signed targets of `STIM` | 607 | Excludes `STIM` |
| `H1D` | first-hop signed targets that are descending neurons | 9 | Subset of `H1` |
| `H2` | second-hop signed targets | 3,576 | Excludes `STIM` and `H1` |
| `DESC` | `super_class == descending` | 1,316 | |
| `DESC2` | `DESC \ H1D` | 1,307 | Descending neurons not directly innervated by `STIM` |
| `MOT` | `super_class == motor` | 805 | |
| `ACT` | LEFT 185 + RIGHT 186 + JUMP 20 | 391 | Decoder pools |
| `CUE` / `ACTN` | Phase 5 cue and action populations (4 × 8, 4 × 1) | 32 / 4 | 36-node substrate |

**Recruitment code (declared, result-independent).** For a population of size
`n`, the number of active neurons in the readout window is coded into four
levels: `0` = zero active; `1` = 1 to ⌈n/100⌉; `2` = ⌈n/100⌉+1 to ⌈n/10⌉;
`3` = above ⌈n/10⌉. The edges depend on `n` alone. It reads as none / sparse /
moderate / broad recruitment. This four-level code is the **only**
discretisation used for BANC populations; the earlier three-level absolute-count
variant is withdrawn so that the declared tables and the declared
discretisation cannot disagree.

### H1 — Direct activation of the stimulated sensory population

| Element | Definition |
| --- | --- |
| **Claim under test** | The declared stimulus code is reflected in the activity of the 232 stimulated sensory neurons. |
| **Predictor** | `S`, 4-level stimulus code: entity {train, obstacle} × distance half at the pooled archived median 0.653686. |
| **Response** | `R_STIM`, recruitment code (4 levels) of `STIM` in `[50, 300)` ms. |
| **Table / n** | 4×4, df 9, floor 0.009661 bits at n = 672 |
| **Null** | `I(S; R_STIM) = 0`. |
| **Alternative** | `I(S; R_STIM) > 0`. |
| **Required observations** | Stimulus identity and encoded payload; onset and offset; every spike time and index; `STIM` counts per 10 ms bin. |
| **Controls** | `NO_STIM` (spontaneous), `PEAK_MATCHED_RECT` (charge form), `SHUFFLED_MASK` (feature identity), stimulus-label permutation. |
| **Evidence to support** | Corrected MI above the 95th percentile of its **own** permutation null, track-cluster bootstrap CI excluding zero, ≥2 observed levels in both variables. |
| **Inconclusive if** | `R_STIM` is constant; a stimulus level has < 20 trials; the estimate is not estimable after the missing-data rule. |
| **Stage** | P (gate P1a), R (E1, E2) |

### H2 — Stimulated sensory activity to first-hop populations

| Element | Definition |
| --- | --- |
| **Claim under test** | First-hop activity depends on the pattern of stimulated sensory activity, not merely on the presence of stimulation. |
| **Predictor** | `R_STIM`, 4-level recruitment code. |
| **Response** | `R_H1`, 4-level recruitment code of `H1` (607 neurons). |
| **Table / n** | 4×4, df 9, floor 0.009661 at n = 672 |
| **Null** | `I(R_STIM; R_H1) = 0`; separately, `H1` prevalence in `REAL` equals `NO_STIM`. |
| **Alternative** | `I(R_STIM; R_H1) > 0`; `REAL` prevalence exceeds `NO_STIM`. |
| **Required observations** | `STIM` and `H1` per-neuron counts and times; first-hop panel current and potential (optional). |
| **Controls** | `NO_STIM`; `PEAK_MATCHED_RECT`; `SHUFFLED_MASK`; the 662 signed mapping edges are reported. |
| **Evidence to support** | The information criterion and presence gate P1. Information without propagation, or propagation without information, is a partial result. |
| **Inconclusive if** | `H1` is silent in every `REAL` trial (P1 failed), or the code has fewer than two observed levels. |
| **Stage** | P (gate P1), R (E3, E4) |

### H3 — Downstream activity beyond the first hop

| Element | Definition |
| --- | --- |
| **Claim under test** | Second-hop and non-first-hop descending activity depend on the stimulus. |
| **Predictor** | `S`, 4-level stimulus code. |
| **Response** | `R_H2DESC`, 4-level recruitment code of `H2 ∪ DESC2`. |
| **Table / n** | 4×4, df 9, floor 0.009661 at n = 672 |
| **Null** | `I(S; R_H2DESC) = 0`; `REAL` prevalence equals `NO_STIM`. |
| **Alternative** | `I(S; R_H2DESC) > 0`; `REAL` prevalence exceeds `NO_STIM` and exceeds `PEAK_MATCHED_RECT`. |
| **Required observations** | `H2`, `DESC`, `H1D` per-neuron counts and times; stimulus identity; per-trial injected charge. |
| **Controls** | `NO_STIM`; `PEAK_MATCHED_RECT`; `SHUFFLED_MASK`. The nine `H1D` neurons are excluded from `DESC2` so that a descending spike cannot be first-hop. |
| **Evidence to support** | P2a and P2b presence, P2c and P2s specificity, and E5/E6 above their permutation nulls. |
| **Inconclusive if** | P2a and P2b both fail; or `H2` is degenerate while `DESC2` passes (then `DESC2` is the only propagation evidence and `H2` is reported unobserved). |
| **Stage** | P (gates P2a, P2b, P2c, P2s), R (E5, E6) |

### H4 — Descending activity to motor neurons

| Element | Definition |
| --- | --- |
| **Claim under test** | Motor-neuron spiking is preceded by descending spiking more often in `REAL` than in controls. |
| **Predictor** | Descending spiking in the same trial. |
| **Response** | Per-trial binary: the trial contains at least one `DESC` spike followed by a `MOT` spike within `w` ms. `w` = 10 ms primary; 5 ms and 20 ms sensitivities are pre-registered. |
| **Table / n** | 4×2 for the descriptive MI, df 3; the confirmatory statistic is the per-trial paired proportion (no bias floor applies) |
| **Null** | The paired proportion difference between `REAL` and `NO_STIM` is zero. |
| **Alternative** | `REAL` > `NO_STIM`. |
| **Required observations** | Per-trial `DESC` and `MOT` spike times; pool counts; per-trial spike-level counts reported descriptively. |
| **Controls** | `NO_STIM`; `PEAK_MATCHED_RECT`; the structural baseline of zero first-hop motor targets and only four motor neurons at two signed hops. |
| **Evidence to support** | P3a passed and the paired proportion difference excludes zero. |
| **Inconclusive if** | No motor neuron spikes in any `REAL` trial — reported as a bounded null (`< 1/672` trials), not as an information test. |
| **Stage** | P (gate P3a), R (E7) |

**Note on the `w` window.** 10 ms is chosen because `tau_m = 20 ms` and the
synaptic delay is 1 ms: a 5 ms window is shorter than one membrane time
constant and would miss a monosynaptic response whose onset is delayed by
integration. The 5 ms and 20 ms windows are reported as sensitivities and are
not used to select the primary.

**The unit is the trial, not the spike.** A trial with 20 descending spikes
contributes one observation. No p-value is computed with `n` = descending
spikes.

### H5 — Neural population activity to decoder-mediated action

| Element | Definition |
| --- | --- |
| **Claim under test** | The decoder's per-window decision is a deterministic function of declared pool activity. This is a **consistency** claim about a decision rule, not a claim about motor control. |
| **Predictor** | `R_MOT`, 4-level recruitment code. |
| **Response** | `A`, 4 levels: the last non-NEUTRAL decoder state in `[50, 300)` ms, else NEUTRAL. One value per trial. |
| **Table / n** | 4×4, df 9, floor 0.009661 at n = 672; unit = trial |
| **Null** | `I(R_MOT; A) = 0`, which occurs only if the decoder gates are never met or the state never varies. |
| **Alternative** | `I(R_MOT; A) > 0`. Because the decoder reads the same spikes, a positive result is expected whenever the decoder fires at all. |
| **Required observations** | Per window: bounds, raw scores, smoothed scores, state, pool counts. Per trial: the single response value. |
| **Controls** | Decoder ablation with a seeded permutation of neuron-to-pool assignment, thresholds unchanged, re-decoded from stored spikes. |
| **Evidence to support** | Nothing beyond a correctly labelled estimate. This endpoint can never support a motor-control or biological claim. |
| **Inconclusive if** | Every window is NEUTRAL in every condition. |
| **Stage** | R (E8, E9) |

**The five windows are not five observations.** E8 uses one value per trial. The
stacked 3,360-row estimate is reported descriptively with a trial-clustered
interval and the effective `n` of 672, and carries no p-value.

### H6 — Neural activity and task outcome under fixed versus plastic weights

| Element | Definition |
| --- | --- |
| **Claim under test** | On the Phase 5 substrate, plastic training changes the neural code that carries cue identity relative to fixed weights. |
| **Substrate** | The Phase 5 synthetic 36-node task graph. **Not** the BANC connectome. No H6 result is transferred to H1–H5. |
| **Predictor** | `CUE`, 4 levels. |
| **Response** | `A_neural`, **5 levels**: which of the four action neurons has the highest evaluation spike count, plus a fifth declared level "no action neuron spiked"; ties resolve to the lowest action index. The fifth level is a declared category, not a data-dependent bin, so the 4×5 table (df 12) is legitimate and does not conflict with the four-level BANC recruitment code, which applies only to BANC populations. |
| **Table / n** | 4×5, df 12, floor 0.000404 bits at n = 21,440 rows; 134 independent substrate clusters |
| **Null** | `I(CUE; A_neural)` is equal in `fixed_complete` and `plastic_complete`. |
| **Alternative** | The paired cluster-level difference is positive in the plastic direction. |
| **Required observations** | Per episode: cue, all spike times and indices, per-neuron counts, reward, prediction error, trace summary, weight snapshot at checkpoint 160, selected action, task outcome. |
| **Controls** | Paired substrate seeds; `eta = 0` hash reproduction; the Phase 5F direction re-estimated on the new replicate before E10 is reported. |
| **Evidence to support** | The paired difference exceeds the pre-registered MDE computed from the **observed** between-substrate SD at 134 clusters (planning value 0.05 bits) and its interval excludes zero. |
| **Inconclusive if** | The Phase 5F direction does not reappear; or > 20% of substrates are degenerate in the action code; or row-level and cluster-level analyses disagree in sign; or the observed SD implies an MDE above 0.05 bits (§10.5). |
| **Stage** | S (E10) |

## 6. Recording strategy

### 6.1 The two options

| | **A. Instrumented simulation recording** | **B. Biological neural recording** |
| --- | --- | --- |
| What is measured | Per-trial spike times, indices, and a declared diagnostic panel of membrane potentials and synaptic currents, from the existing BANC simulator or `PlasticSimulator`. | Extracellular or intracellular recordings from a living animal. |
| What it can establish | Internal computational information flow in the declared model. | Whether the same flow exists in the animal. |
| What it cannot establish | Biological validity of any kind. | Anything about this simulator except by analogy. |
| Cost | Hours of CPU; ≈0.93 GB mandatory storage; no new hardware. | Ethics approval, surgery, hardware, months of calendar time. |
| Dependencies | `experiments/phase_6d/` (not yet written) and the Stage P gates. | Nothing in the project is reusable. |

### 6.2 Decision: Option A

The experiment is **Option A**. It is not a substitute for B. The Phase 6B/6C
gap is missing *simulated* neural-level data, not missing biological data.

A positive Stage R result means: *within this declared model, information about
the stimulus reached the second-hop and descending populations at a magnitude
distinguishable from the tested controls.* It does not mean a fly's neurons
carry that information. A decoder output means *the decision rule fired*. It
does not mean the animal moved.

### 6.3 Four gaps that more simulation cannot close

1. **Neuron-model fidelity.** One single-compartment LIF model with fixed
   parameters for all 172,433 nodes; no dendritic geometry, cell-type
   conductances or adaptation. A threshold crossing is a modelling decision.
2. **Synapse sign and weight provenance.** Signs come from `banc_synapse_policy`
   for 683,100 of 1,535,710 edges (44.48%) by rule, not measurement. Unassigned
   edges do not transmit.
3. **Stimulation plausibility.** The drive is injected current in picoamperes on
   232 mapped neurons. Nothing establishes that it resembles a real sensory
   afferent.
4. **Decoder authority.** The decoder is a hand-written threshold rule over
   three named pools (PF-4H-4).

### 6.4 Why the pilot is a gate, not a preliminary

Phase 6A declared the analysis infeasible because the archived 4H runs produced
zero downstream events. More trials do not fix that: if the drive never
propagates, a larger sample estimates information about an all-zero response,
which is degenerate and must be reported as inconclusive, not negative. Stage P
therefore runs before the campaign.

## 7. Recording schema and instrumentation contract

### 7.1 Per-trial record

One record per simulated trial. Stage P writes the same schema with
`stage = "P"`. A trial missing a mandatory field is excluded and counted; an
exclusion rate above **0.5%** in any condition is an integrity failure (§12.1).
The 5% figure in this document refers **only** to the determinism re-run sample
and never to exclusions.

| # | Field | Type | Status | Provenance |
| --- | --- | --- | --- | --- |
| 1 | `trial_id` | string | mandatory | `experiments/phase_6d/trial_schedule.py`; stable sort key |
| 2 | `stage` | enum `P`,`R`,`S` | mandatory | Runner |
| 3 | `random_seed` | int | mandatory | Passed to `BancSimulator(seed=...)`; seeds noise only |
| 4 | `condition` | enum | mandatory | `REAL`, `SHUFFLED_MASK`, `PEAK_MATCHED_RECT`, `NO_STIM`, `RANDOM_MAPPING`; Stage P additionally `MATCHED_CHARGE`, `DIRECT_INJECTION`, `SINGLE_H1_SPIKE`; Stage S `fixed_complete`, `plastic_complete` |
| 5 | `recording_enabled` | bool | mandatory | `false` for the recording-off repeat arm (R8); the hash must still match |
| 6 | `connectome_identity` | object | mandatory | `{"name":"banc_v888","graph_sha256":"6d47f259…e2192","node_sha256":"144a2eb0…3e5f","n_nodes":172433,"n_edges":1535710}` |
| 7 | `threshold` | int | mandatory | 5, read from `graph.threshold` |
| 8 | `root_ids` | int32 array | mandatory | Every neuron touched by the trial (stimulated ∪ panel ∪ any spiking neuron) |
| 9 | `population_labels` | uint8 array | mandatory | stimulated / first-hop / first-hop-descending / second-hop / descending / motor / other |
| 10 | `panel_node_ids` | int32 array | optional | Present only when O2/O3 are enabled; the pre-registered panel (§7.7) |
| 11 | `stimulus_identity` | object | mandatory | For `REAL`: source record index, `class`, `entity`, `track_id`, **`archive_time_ms`**, **`rebase_transform`**, `feature_values` |
| 12 | `stimulus_onset_ms`, `stimulus_offset_ms` | float | mandatory | 50.0 and 150.0 ms; offset is the physical end of injected current under the declared `decay_ms` |
| 13 | `spike_times_ms` | float32 array | mandatory | `SpikeRecorder.spike_times_ms` |
| 14 | `spike_neuron_indices` | int32 array | mandatory | Parallel to 13 |
| 15 | `n_neurons` | int | mandatory | `graph.n_nodes` |
| 16 | `spike_counts` | int32 array, recorded node set | mandatory | `SpikeRecorder.spike_counts()` restricted to the set; called once per trial |
| 17 | `population_counts` | int32 array, ≤ 7 | mandatory | Per population label, per 10 ms bin and whole trial |
| 18 | `binned_activity` | float32 `(7, 30)` | mandatory | 10 ms bins; **population level only** |
| 19 | `decoder_windows` | JSON array | mandatory | `ActionDecision.as_dict()` per window |
| 20 | `task_outcome` | object or null | Stage S mandatory | BANC writes explicit `null` |
| 21 | `reward`, `prediction_error` | float or null | Stage S mandatory | `PlasticSimulator` callback return and `update_reports` |
| 22 | `plasticity_traces` | sparse object or null | Stage S mandatory | `EligibilityStore` summary; no dense edge × time array |
| 23 | `effective_weights` | sparse object | Stage S mandatory | `WeightState` digest plus plastic positions (≤ 32 edges) |
| 24 | `spike_hash` | string | mandatory | `spike_hash(result.recorder)` from `experiments/phase_4h/common.py` |
| 25 | `config_hash` | string | mandatory | SHA-256 of resolved condition + decoder + neuron parameters |
| 26 | `software_version` | object | mandatory | Python, numpy, commit, `phase_6d_code_sha256` |
| 27 | `provenance` | object | mandatory | Runner path, wall-clock, host, SHA-256 of the graph, node and stimulus files read |

### 7.2 Optional diagnostics

Not in the mandatory record; collected only for the declared panel and only if
the panel is fixed before Stage P.

| # | Field | Availability, verified | Cost |
| --- | --- | --- | --- |
| O1 | Full-population potential trajectory | Available only as the live `_V` array | 828 MB per 300 ms run. **Rejected by a guard (T12).** |
| O2 | Panel `membrane_potential_mv` | Same property, subsampled to the panel | Panel ≤ 458 × 150 samples × 4 B ≈ 275 kB per trial, ≈1,575 MB for Stage R including repeats. Optional. |
| O3 | Panel `synaptic_current_pa` (exc, inh, net) | Properties of `BancSignedSynapses`; per-neuron aggregate, not per-synapse | Same panel and cost as O2 |
| O4 | `last_active_edges` | Exists during a step, overwritten each step | Accumulate a sparse set only if needed; not in the schema |
| O5 | `spike_hash` | `experiments/phase_4h/common.py` | Promoted to mandatory field 24 |

**O2 and O3 sample a spiking neuron at −68 mV unless the recorder substitutes
threshold.** See §7.4 clause 4.

### 7.3 Volume

| Quantity | Value | Derivation |
| --- | --- | ---: |
| Spikes per trial, planning value | 15,000 | Between the 3,562 observed maximum and 10% second-hop recruitment |
| Bytes per spike | 8 | float32 time + int32 index |
| Spike payload per trial | 120 kB | 15,000 × 8 B |
| Metadata and aggregate fields | ≈15 kB | Fields 8–12, 17–19, 24–27 |
| **Mandatory bytes per trial** | **≈135 kB** | |
| Optional O2+O3 per trial | ≈550 kB | 458 × 150 × 2 signals × 4 B |
| Hard storage budget | 2.7 GB | The runner stops and reports rather than degrading |

No `n_neurons × n_time_bins` matrix is written in any format. The largest
mandatory array is `(7 populations, 30 bins)`.

### 7.4 The instrumentation contract

`experiments/phase_6d/recording.py` must satisfy all twelve conditions. They are
the conditions under which the recorder provably does not change the simulation.

1. **Call the original step exactly once and return its result unchanged.** No
   re-run, no thresholding, no reset, no alteration of `spikes`.
2. **Consume no random numbers.** No global `np.random.*`, no access to the
   simulator RNG, no `default_rng` inside the wrapper. The analysis has its own
   `default_rng(20261110)`; the recorder must never touch it.
3. **Copy every array it retains.** `_V`, `_exc`, `_inh`, eligibility traces and
   `last_active_edges` are mutated in place or overwritten each step. A retained
   reference is a bug.
4. **Represent spiking neurons correctly.** `LIFPopulation.step` writes
   −68 mV into `_V[spikes]` at `brain/neuron_model.py:154` before returning.
   The recorder must either substitute `threshold_mv` for the returned indices —
   as `experiments/phase_4h/analyse_sensory_roundtrip.py:828` does — or sample
   the potential **before** the reset. For the O2 trajectory the rule is:
   record the pre-step potential and, for the sampled step, record the
   post-reset value with a `spiked` flag. The report must state which convention
   was used. A recorder that samples `_V` after `step` without substitution
   records −68 mV for every spiking neuron and is wrong.
5. **Do not mutate simulator inputs or state.** No writes to `current`,
   `spikes`, `_V`, `_exc`, `_inh`, the delay buffers, the weight state or the RNG.
6. **Install and restore in `try/finally`.** Assert the wrapper is installed
   before `run()`; restore the original in `finally`; refuse a second install as
   a loud error rather than nesting wrappers.
7. **Use one recorder.** `BancSimulator.run` already calls `recorder.record` at
   line 475. The wrapper must not call `record` again or create a second
   recorder over the same spikes.
8. **Respect capacity.** 500,000 spikes per trial (4 MB). A runaway raises
   `SpikeCapacityExceeded`, is recorded as a failed trial, and is never
   truncated.
9. **The Stage S callback returns `None`.** Otherwise it silently replaces the
   reward. It must not call `engine.learn` or mutate `WeightState`.
10. **State the time base.** Spikes are stamped `(step + 1) × 0.5 ms`. Bin 0 is
    `[0.0, 10.0)` ms and a spike exactly on an edge falls in the later bin.
    Decoder windows are `[50, 100)`, `[100, 150)`, `[150, 200)`, `[200, 250)`,
    `[250, 300)`, lower-inclusive. Binning and windows use the same base.
11. **Pre-register the panel.** See §7.7.
12. **No production module edits.** G2 must show a `git status` limited to
    `experiments/phase_6d/`, `configs/phase_6d_recording.yaml` and
    `tests/test_phase_6d_recording.py`, and an unchanged README hash.

### 7.5 Mandatory regression tests

| # | Test | Pass condition |
| --- | --- | --- |
| T1 | **Recording on/off spike hash** | For archived 4H condition B, `spike_hash` with the wrapper enabled equals the archived hash and the no-wrapper hash. |
| T2 | **Recording-on/off repeat** | Two runs with the recorder produce identical records; a run with the recorder disabled produces the same spike hash. |
| T3 | **Zero RNG consumption** | No-op recorder and real recorder at the same seed produce identical hashes; `np.random.*` is never called from the recorder. |
| T4 | **`LIFPopulation.step` contract** | Signature `(self, current_pa)`, return an integer index array; a change fails loudly and names the wrapper. |
| T5 | **Copy-on-record** | Mutating `_V`/`_exc` after recording leaves the stored panel unchanged. |
| T6 | **Threshold representation** | A spiking neuron is recorded at or above threshold, or the pre-step value is recorded; never −68 mV as the spike value. |
| T7 | **Capacity** | A synthetic over-capacity run raises `SpikeCapacityExceeded` and the trial is marked failed. |
| T8 | **Time base** | A step-0 spike is stamped 0.5 ms; bin and window edges match the declared base. |
| T9 | **Plastic callback neutrality** | A callback returning `None` yields the same reward, weight trajectory and hash as no callback; a callback returning a number changes the reward (the test must be sensitive). |
| T10 | **Install/restore** | An exception inside `run()` restores `sim.neurons.step`; a second install raises. |
| T11 | **No production edits** | `git diff --name-only` restricted to the three permitted paths; README hash unchanged. |
| T12 | **Memory bound** | The O1 guard rejects full-population recording; the panel buffer is allocated once and is ≤ 275 kB per trial. |

T1–T4 are mandatory before G2. A second hash fixture is added: archived 4H
condition C, which is non-zero, alongside condition B. Conditions A, F and G are
all-zero and are weak anchors.

### 7.6 Recording-off equivalence in the campaign

The 136 determinism repeats in Stage R are split 68 / 68:

- **68 with recording enabled**: re-run in a separate process; the record and
  the spike hash must be identical to the original trial.
- **68 with recording disabled** (`recording_enabled = false`): the spike hash
  must equal the hash of the corresponding recording-enabled trial, and no
  panel or aggregate field may differ.

This is the operational form of T1/T2. T1–T3 are the systematic checks; the 68/68
split is the campaign-level check. A mismatch invalidates the affected condition
until explained; it is not overridden by dropping the trial.

### 7.7 Panel selection rule

If O2/O3 are enabled, the panel is fixed before Stage P and recorded in fields 10
and 27:

- the 232 `STIM` neurons;
- the 200 `H1` neurons with the largest mean input current in the archived 4H
  condition-B run, ties broken by ascending local index;
- the 20 `DESC` neurons with the largest mean input current in the same run,
  ties by ascending index;
- the 6 decoder pool neurons already declared in Phase 4F.

Total ≤ 458 nodes. The selection uses only archived data; no Stage P outcome
enters it. "Up to 200 first-hop" without a rule is withdrawn.

## 8. Experimental conditions

### 8.1 The seven distinctions

Each distinction has exactly one decision rule. No condition is included unless
it separates one of them.

| # | Distinction | Separated by | Decision rule |
| --- | --- | --- | --- |
| 1 | **Direct sensory-neuron activation** — do the 232 stimulated neurons fire? | `REAL` vs `NO_STIM` at each drive | P1a |
| 2 | **First-hop propagation** — does `H1` spike? | `REAL` vs `NO_STIM` | P1 |
| 3 | **Second-hop propagation** — does `H2` spike? | `REAL` vs `NO_STIM` | P2a |
| 4 | **Descending recruitment beyond the first hop** — do `DESC2` neurons spike? | `REAL` vs `NO_STIM`, nine `H1D` excluded | P2b |
| 5 | **Charge-form specificity** — is propagation more than uniform injected current? | `REAL` vs `PEAK_MATCHED_RECT` | P2c |
| 6 | **Feature specificity** — is propagation more than any permuted payload? | `REAL` vs `SHUFFLED_MASK` | P2s |
| 7 | **Motor recruitment** — do motor neurons spike? | `REAL` vs `NO_STIM` | P3a |
| (7b) | **Decoder reachability** — can the decoder leave NEUTRAL? | `REAL` vs `NO_STIM`, `PEAK_MATCHED_RECT` | P3, labelled separately |
| (7c) | **Coincidental spontaneous activity** — is the response above baseline? | `NO_STIM` at the same seed and noise | Bounds every presence gate; the Clopper–Pearson upper bound is recorded at G4 |

**Direct injection is not in this table.** `DIRECT_INJECTION` is a capability
control: it establishes that the `H1`→`H2` synapse can transmit when driven
artificially. It is never evidence of natural sensory propagation, and no gate
or endpoint is defined on it. Its only decision role is diagnostic: if it
succeeds while `REAL` fails, the result is a drive/encoder failure; if it fails
too, the tissue does not spike under any tested current.

### 8.2 Stage P — design

| Arm | Role | Trials per drive | Runs |
| --- | --- | ---: | ---: |
| `REAL` | measurement of interest | 40 | 160 |
| `NO_STIM` | spontaneous baseline | 40 | 160 |
| `PEAK_MATCHED_RECT` | charge-form control | 40 | 160 |
| `SHUFFLED_MASK` | feature-specificity control (P2s) | 40 | 160 |
| `MATCHED_CHARGE` | descriptive only; subthreshold floor | 40 | 160 |
| `DIRECT_INJECTION` | capability control only | 40 | 160 |
| `SINGLE_H1_SPIKE` | per-spike calibration | — | 4 |
| **Total** | | | **964** |

**Drives:** 200, 400, 800, 1200 pA per stimulated neuron through
`BancEventDrive` with `pulse_gain = 1.0`, so the injected current is the nominal
value.

**Seeds:** 40 noise seeds, reused across all arms at a given drive. Each seed is
run once per (arm, drive), so 960 condition-runs on 40 unique seeds. The pairing
is what makes the specificity tests valid.

**Trial:** 300 ms, onset 50 ms, offset 150 ms, readout `[50, 300)` ms;
`noise_std_pa = 50.0`, `background_current_pa = 0.0`, identical across arms and
matched by seed; `decay_ms = 100.0`.

**Peak-matched rectangular control.** At drive `d`, `d` pA is injected into all
232 `STIM` neurons as a rectangle from 50 to 150 ms. It matches the peak
amplitude and the duration of the concentrated drive but not its spatial
distribution or its decay shape. Total charge therefore differs from `REAL`; the
per-trial charge of both arms is recorded and reported as a covariate. This is
the control that the earlier `MATCHED_CHARGE` could not provide, because
`ConstantChargeDrive` spreads total charge over 232 neurons and 300 ms and is
below the 150 pA rheobase by construction (4H condition F: 46.696 pA/neuron,
zero spikes).

**`MATCHED_CHARGE` is retained for one purpose only:** to demonstrate the
subthreshold floor at each drive. It appears in no gate and no endpoint. Its
per-neuron amplitude is reported; if at some drive it exceeds rheobase it becomes
a genuine charge control and the report must say so.

**Why 40 trials per cell and not 20.** At 20 trials per group the earlier
presence gate had 0.32–0.80 power depending on how the controls behaved, and its
power was non-monotonic in `n` because a fixed "≥ 10 of 20" floor was more
stringent than the test. At 40 trials per group, against a 40-trial `NO_STIM`
arm, the one-sided Fisher test at α = 0.0125 has power 0.99 at 50% vs 5% and
0.88 at 30% vs 2%. The extra 640 runs cost ≈27 minutes.

### 8.3 Evaluation order and the `d*` rule

1. **P0 integrity** on all 964 records.
2. **P1a, P1, P2a, P2b at all four drives**, from the runs that already exist.
3. **Freeze `d*`** = the lowest drive in {200, 400, 800, 1200} pA at which P1a,
   P1, P2a and P2b all pass. Write the gate-decision file.
4. **P2c, P2s, P3, P3a at `d*`.** These are read only after `d*` is written and
   cannot change it.
5. Stage R proceeds only if P2a and P2b pass.

Reading the presence gates at all four drives costs **zero** additional
simulations: the 160 `REAL`, 160 `NO_STIM` and 160 `PEAK_MATCHED_RECT` runs
already contain every drive. The earlier design fixed `d*` at the first drive
that passed P1 and read propagation only there, which would have stopped the
programme at a drive where first-hop activity appears but second-hop activity
does not yet.

### 8.4 Gate definitions

Presence gates P1a and P1 use a one-sided Fisher exact test at **α = 0.0125**,
which is Bonferroni over four drives and controls the family-wise error at 0.05.
Every drive receives a valid test, which is required for the "lowest passing
drive" rule. P2a and P2b are **screens** with stated effect-size floors and no
p-value; the confirmatory inference happens in Stage R.

| Gate | Pass | Fail | Inconclusive |
| --- | --- | --- | --- |
| **P0 — integrity** | All 964 records complete every mandatory field (≤ 0.5% exclusion in each arm); the 5% re-run reproduces `spike_hash`; archived 4H condition B **and** condition C hashes reproduced; no `SpikeCapacityExceeded`; all recorded potential arrays finite. | Any determinism mismatch not traceable to a declared code change; silent truncation; > 0.5% exclusion in any arm. | Not applicable; integrity is binary. |
| **P1a — STIM activation** | At some drive: `REAL` `STIM` prevalence ≥ 20/40, and one-sided Fisher `REAL` vs `NO_STIM` p < 0.0125. | No drive activates `STIM` while `DIRECT_INJECTION` at ≥ 400 pA drives `H1`: drive/encoder failure; stop and report. `DIRECT_INJECTION` also silent: the tissue does not spike under any tested current; stop and report as a model-regime limit. | `REAL` passes the test but the effect is carried by one seed half with opposite sign in the other: report as unstable and do not proceed. |
| **P1 — first hop** | At some drive: `REAL` `H1` prevalence ≥ 10/40 and Fisher p < 0.0125 vs `NO_STIM`. | No drive passes. If `DIRECT_INJECTION` reaches `H2`, report a drive/encoder failure; otherwise report no first-hop propagation. Stop. | Test passes but `REAL` prevalence is < 10/40 (effect-size floor not met): report as a weak effect and do not stop. |
| **P2a — second hop** | `REAL` `H2` prevalence ≥ 6/40 **and** `REAL − NO_STIM` ≥ 4/40 (10 points). | No drive passes: stop; report "no second-hop propagation detected under this design". | `H2` degenerate while `DESC2` passes: `H2` reported unobserved; `DESC2` is the only propagation evidence. |
| **P2b — descending beyond first hop** | `REAL` `DESC2` prevalence ≥ 2/40 **and** `REAL − NO_STIM` ≥ 2/40. | No drive passes: descending recruitment not detected; H3/H4 untestable. Not a stop if P2a passed. | All `DESC` spikes are in the nine `H1D` neurons: report first-hop descending activity, not second-hop recruitment. |
| **P2c — charge form** | At `d*`: `REAL` > `PEAK_MATCHED_RECT` on `H2 ∪ DESC2` prevalence, paired by seed, one-sided p < 0.025. | `PEAK_MATCHED_RECT` equals or exceeds `REAL`: propagation is charge-driven, not pattern-driven. The H3 specificity claim is withdrawn and the result is reported as a charge/recruitment effect. | Both zero: not estimable; report the null as a failed observation. |
| **P2s — feature specificity** | At `d*`: `REAL` > `SHUFFLED_MASK` on `H2 ∪ DESC2` prevalence, paired by seed, one-sided p < 0.025. | `SHUFFLED_MASK` equals or exceeds `REAL`: propagation is not feature-specific; H2/H3 become descriptive, not confirmatory. | Both zero: not estimable. |
| **P3 — decoder reachability** | At `d*`: ≥ 1 post-stimulus `REAL` window non-NEUTRAL; every `NO_STIM` and `PEAK_MATCHED_RECT` window NEUTRAL. | No `REAL` window non-NEUTRAL: H5 untestable; H1–H4 proceed. Not fatal. | `REAL` non-NEUTRAL and a control also non-NEUTRAL: the decoder is not neutral; the decoder endpoints leave the confirmatory family. |
| **P3a — motor recruitment** | At `d*`: ≥ 1 `REAL` trial has ≥ 1 `MOT` spike; no `NO_STIM` trial does. | No `MOT` spike in any `REAL` trial: H4 untestable; reported as structurally expected (0 first-hop motor targets). | `MOT` spikes only in controls: report a baseline false-positive rate. |

**Screen operating characteristics, stated before the run.** These replace the
earlier "0 of 40" rule, which failed on a single chance control spike and was
therefore a coincidence detector rather than a test.

| Gate | Criterion | True rate | Pass probability |
| --- | --- | --- | ---: |
| P2a | ≥ 6/40 and ≥ 4/40 above control | 30% vs 5% | 0.99 |
| P2a | same | 20% vs 2% | 0.83 |
| P2a | same | 15% vs 2% | 0.56 |
| P2a | same | 10% vs 2% | 0.20 |
| P2b | ≥ 2/40 and ≥ 2/40 above control | 10% vs 2% | 0.92 |
| P2b | same | 5% vs 0% | 0.60 |
| P1 | Fisher α = 0.0125 | 50% vs 5% | 0.99 |
| P1 | same | 30% vs 2% | 0.88 |
| P1 | same | 20% vs 2% | 0.49 |

A failed P2a or P2b is written as **"no propagation detected under this design"**,
never as "propagation absent". At a true H2 prevalence of 15% the screen will
miss about 44% of the time; that is the measured cost of a 964-run pilot, and it
is stated here rather than discovered later.

### 8.5 Stimulus corpus and event-time transform

The corpus is `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`:
215 event records, **43 of which carry `feature_values`**. Those 43 records come
from **24 distinct `(class, track)` pairs**. Counts, recomputed from the archive:

| Level | Rule | Event records | Distinct tracks |
| --- | --- | ---: | ---: |
| `TRAIN_NEAR` | entity = train, distance ≤ 0.653686 | 20 | 13 |
| `TRAIN_FAR` | entity = train, distance > 0.653686 | 15 | 11 |
| `OBST_NEAR` | entity = obstacle, distance ≤ 0.653686 | 2 | **1** |
| `OBST_FAR` | entity = obstacle, distance > 0.653686 | 6 | 5 |
| **Total** | | **43** | **24** |

The per-level track counts sum to 30 while the union is 24 because **six tracks
appear in two levels**: five train tracks cross the 0.653686 median during their
lifetime and one barrier track (`jump-roll-barrier`, track 11) appears in both
obstacle halves. A track is therefore not owned by one level, and the track
bootstrap must resample whole tracks and recompute the whole table so that a
crossing track contributes to both levels in every resample.

**`OBST_NEAR` is one track at two frames 100 ms apart** (1066.6667 and
1166.6667 ms, distances 0.61655 and 0.483462). It is one stimulus, not two.

**Event-time transform (declared, frozen before Stage P).** Archived event times
run from 66.6667 to 3266.6667 ms and therefore cannot occur inside a 300 ms
trial: `BancEventDrive` uses the event's absolute `time_ms` as its onset. The
transform is:

```
archive_time_ms  ->  trial_time_ms = 50.0          (all selected events)
decay_ms         =  100.0                          (current ends at 150.0 ms)
stimulus_onset_ms = 50.0 ; stimulus_offset_ms = 150.0
```

The original `archive_time_ms`, the transform string and the record index are
written into field 11. With `decay_ms = 100.0` the injected current ends exactly
at the declared offset, so "offset 150 ms" is a physical end and not a nominal
label. This transform is fixed before Stage P and cannot be changed after seeing
P1.

**Trial allocation is track-balanced.** Within each level, the 168 scheduled
trials are assigned round-robin over the level's **distinct tracks**, then
round-robin over that track's records. `TRAIN_NEAR` therefore gives each of 13
tracks 12 or 13 trials rather than letting a five-record track dominate.
`OBST_NEAR` gives its single track all 168 trials (84 per record), which is why
that level carries no generalisation claim.

**The 6-level sensitivity code.** Entity × distance tertile is retained as the
binding sample-size table even though it is not the primary test; its bias floor
is the largest declared and N is chosen so that floor stays below the MDE. Its
allocation follows the same track-balanced rule.

### 8.6 Stage R — condition matrix

Stage R runs only after P0–P2b pass and `d*` is frozen. All conditions share the
trial length, seed list, noise schedule and decoder configuration. They differ
in the current schedule, and `SHUFFLED_MASK` additionally changes which payload
occurs at which event time.

| ID | Condition | Drive | Purpose | Trials |
| --- | --- | --- | --- | ---: |
| R1 | `REAL` | `d*`, one archived event per trial | measurement of interest | 672 |
| R2 | `SHUFFLED_MASK` | `d*`, one permutation of the payloads across the 43 records | feature specificity; tests whether the pairing of payload to event time matters | 672 |
| R3 | `PEAK_MATCHED_RECT` | `d*` pA rectangle, 50–150 ms, all 232 `STIM` neurons | charge-form control | 672 |
| R4 | `NO_STIM` | none | spontaneous baseline | 672 |
| R5 | `RANDOM_MAPPING` | `d*`, feature→population mapping permuted with per-trial charge preserved | descriptive only; not in any test | 40 |
| — | determinism repeats | as R1–R4 | 68 with recording enabled, 68 with recording disabled | 136 |
| **Total** | | | | **2,864** |

**672 seeds, 2,688 condition-runs.** Each seed is used once per condition. There
are **672 unique noise seeds**, not 2,688. The 2,688 figure is the number of
condition-runs. `RANDOM_MAPPING` reuses 40 of the same seeds, so it is paired.

**`SHUFFLED_MASK` corrected description.** `shuffle_feature_identities`
(`brain/banc_sensory_adapter.py:883–903`) permutes feature-value payloads
**across events**; it preserves each event's timestamp and changes which payload
is delivered there. It does not permute the feature→population mapping. The
permutation applied to the corpus is a bijection on the 43 records, so the
corpus-level multiset of payloads is preserved exactly while individual trials
differ in payload and therefore in charge. Trials are matched at the corpus
level, not at the trial level; per-trial injected charge is recorded for every
trial and enters E4/E5 as a covariate, and is reported with the estimate.

**`MATCHED_CHARGE` is not a Stage R condition.** It is below rheobase by
construction and its zero result is guaranteed, so it cannot control for charge.
`PEAK_MATCHED_RECT` replaces it.

**`RANDOM_MAPPING` is descriptive.** It answers "does the specific mapping
matter?" with 40 trials and no test statistic. It is not in the confirmatory
family and cannot be promoted after the fact.

### 8.7 Stage S — fixed versus plastic

Stage S is a separate substrate and is never pooled with Stage R.

| Element | Value |
| --- | --- |
| Substrate | Phase 5 task graph, `TaskConfig(n_cues=4, cue_neurons=8, action_neurons=1)`, 36 nodes |
| Conditions | `fixed_complete`, `plastic_complete` |
| **Substrate seeds** | **134**, each generating its own graph instance and initial weights |
| Episode streams | one per substrate seed per condition |
| Episodes per stream | 160 training + 80 evaluation = 240 |
| Total episodes | 134 × 2 × 240 = **64,320** |
| Evaluation rows | 134 × 2 × 80 = **21,440** |
| Independent clusters | **134 substrate seeds** |
| Plasticity | `eta = 1.0`, checkpoint at episode 160; evaluation at `eta = 0` |
| Reward / RPE | `RewardProvider` and the Phase 5B RPE; field 21 mandatory |
| Integrity | Paired substrate seeds; `eta = 0` reproduces fixed-weight hashes; the Phase 5F **direction** is re-estimated on this replicate before E10 |
| Runtime | ≤ 52.8 min at the measured ≥ 20.3 episodes/s |

**Why the substrate seed varies and not just the episode stream.** Phase 5F used
`substrate_seed = 20261114` for all ten cells. A cluster bootstrap over episode
streams on one substrate does not cover substrate or initial-weight uncertainty.
Stage S therefore generates 134 independent substrates. On a 36-node graph the
cost is negligible, and it is what makes the cluster interval mean something.

**The Phase 5F comparison is a new replicate, not a reproduction.** Phase 5F
used 10 streams and 40 evaluation episodes; Stage S uses 134 new substrates and
80 evaluation episodes. §12.7 says "the Phase 5F direction is re-estimated on a
new replicate"; the word "reproduced" is withdrawn.

`fixed_complete` is the fixed-weight control with **the same substrate and
protocol family** as `plastic_complete`: paired substrate seeds, 160 training
episodes (no weight change), 80 evaluation episodes. It is not the Phase 5F seed
list.

### 8.8 Conditions deliberately not repeated

| Historical condition | Why |
| --- | --- |
| Weight sensitivity sweep (4H.3) | Established that propagation is weight- and sign-dependent; no confirmatory endpoint is added by repeating it |
| Threshold / population sensitivity (4H.2) | Threshold 5 is fixed by the artifact and the graph hash; a sweep changes the object under study |
| `C_temporal_shuffle` full sweep | `SHUFFLED_MASK` already breaks payload-to-time pairing |
| `fixed_random` / `plastic_random` | Phase 5F answered complete-versus-random wiring |
| `CORRECT_MAPPING` with reward | BANC has no reward; field 20 is `null` |
| `E_random_matched_mapping` as a confirmatory arm | Retained only as the 40-trial descriptive `RANDOM_MAPPING` |
| `MATCHED_CHARGE` in Stage R | Subthreshold by construction; retained in Stage P as a descriptive floor |

## 9. Controls

| ID | Control | Implementation | Alternative ruled out | If the control fails |
| --- | --- | --- | --- | --- |
| C1 | Spontaneous baseline | `NO_STIM`, same seeds, noise and background | Downstream spikes are spontaneous | Its Clopper–Pearson upper bound, not zero, becomes E3's threshold |
| C2 | Peak-matched rectangular charge | `PEAK_MATCHED_RECT`, `d*` pA, 50–150 ms, all 232 `STIM` neurons | Propagation is driven by current magnitude rather than by the event's pattern | Charge-driven propagation; P2c fails and the specificity claim is withdrawn |
| C3 | Shuffled payload | `SHUFFLED_MASK`, bijective payload permutation across the 43 records | Propagation is generic to any payload | Not feature-specific; H2/H3 descriptive only |
| C4 | Direct first-hop injection (capability) | `DIRECT_INJECTION`, 4 drives × 40 trials | A null is caused by the sensory drive rather than the `H1`→`H2` synapse | Establishes only that the synapse can transmit; **never** evidence of natural propagation |
| C5 | Single first-hop spike (calibration) | One `H1` neuron to exactly one spike; search at 5, 10 and 20 ms | Propagation requires many simultaneous `H1` spikes by construction | Calibrates the minimum transmissible event; a null is informative, not fatal |
| C6 | Fixed-weight paired condition | Stage S `fixed_complete`, paired substrate seeds | A Stage S difference is caused by substrate or protocol | If the Phase 5F direction does not reappear, E10 is not reported |
| C7 | `eta = 0` reproduction | Rerun trained streams at `eta = 0`; compare hashes | Evaluation altered the stored traces | Hash mismatch invalidates that substrate |
| C8 | Archive replay | Re-run 4H conditions B and C; assert archived `spike_sha256` | The instrumentation changed the simulator | The entire campaign is invalid until reconciled |
| C9 | Decoder neutrality in controls | No control trial produces a non-NEUTRAL window | The decoder fires on noise or on uniform charge | The decoder endpoints leave the confirmatory family |
| C10 | Label permutation null | 5,000 trial-level permutations of the stimulus code | Observed MI is expected from marginals alone | Reported with every estimate; no separate pass/fail |
| C11 | Seed-split reproducibility | 672 seeds split 336/336; every endpoint estimated in each half | An effect is carried by a few seeds | Sign disagreement is reported as instability for that endpoint |
| C12 | Blinded analysis | Conditions read as opaque hashes; labels mapped after the results file is frozen | Analyst degrees of freedom | Any post hoc remapping invalidates the pre-registration |
| C13 | Decoder ablation | Re-decode stored spikes with a seeded permutation of neuron-to-pool assignment | The H5 estimate reflects the decoder's own wiring | An ablated estimate as large as the primary one shows H5 is a property of the rule |

**Two controls the design cannot provide.** No biological ground truth, and no
independent implementation. Both are recorded in §14.2 and are why no Stage R
result can be promoted beyond evidence grade E1–E2.

**Direct injection is explicitly demoted.** C4 is retained because it is the
4H.5 recommendation and because it separates "too weak" from "does not
transmit". It is not a member of any gate and cannot contribute to any
propagation claim.

## 10. Sample size

### 10.1 What counts as an independent unit

| Level | Stage R | Stage S | Valid as n for | Not valid for |
| --- | ---: | ---: | --- | --- |
| **Substrate seed** | — | **134** | Stage S cluster inference, substrate uncertainty | — |
| **Noise seed** | **672** (reused across four conditions) | — | Paired condition contrasts; seed-cluster bootstrap; seed-split halves | Generalisation beyond the simulated trials |
| **Condition-run** | **2,688** (672 × 4) + 40 + 136 | 64,320 episodes | Descriptive run counts | Any inference |
| **Trial** | **672 per condition** | 240 per substrate per condition | Stimulus-locked response comparisons; trial-level permutation | Generalisation beyond the 24 tracks |
| **Stimulus track** | **24** (13 / 11 / 1 / 5 per level, union 24) | 4 cues | Generalisation of H2/H3 | Anything larger: 24 is the whole corpus |
| **Episode** | — | 240 per substrate | Paired within-substrate comparison | Substrate-level inference (use the substrate) |
| **Neuron** | 232–5,731 in the declared sets | 36 | Descriptive only | **Never** an independent replicate |
| **Time bin / decoder window** | 30 bins / 5 windows | — | Descriptive only | **Never** an independent replicate |
| **Spike** | ≈15,000 per trial | varies | Descriptive only | **Never** an independent replicate |

No p-value in this protocol uses the number of spikes, neurons, bins or decoder
windows as `n`.

### 10.2 The bias floor, and what it does and does not buy

The plug-in MI of a `kx × ky` table with `N` rows is biased upward by
approximately `(kx−1)(ky−1)/(2N ln 2)` bits. `information.bias_correction`
implements the floor and `information.bias_correction.required_sample_size`
solves it for `N`. The design criterion is that the worst-case floor across the
declared tables is at most one third of the declared 0.05-bit MDE, i.e.
≤ 0.0167 bits.

| Table | df = (kx−1)(ky−1) | N for floor ≤ 0.0167 | Floor at N = 672 | Floor at N = 21,440 |
| --- | ---: | ---: | ---: | ---: |
| 4×4 primary (stimulus × recruitment) | 9 | 389 | 0.009661 | 0.000303 |
| 4×3 (stimulus × H2/DESC where a level collapses) | 6 | 260 | 0.006441 | 0.000202 |
| 4×5 Stage S (cue × 5-level action code) | 12 | 519 | 0.012881 | 0.000404 |
| **6×4 sensitivity (binding)** | **15** | **648** | **0.016102** | 0.000505 |

*The N column is computed at 0.0167 bits. Computed at 0.017 bits it would be
637 for the 6×4 table. The two differ by 11 trials and only the 0.0167 value is
used as the criterion; the table's N column is not a second criterion.*

**The stated derivation of 672 is corrected.** The earlier text said 672 was the
smallest multiple of both 4 and 6 above 648. That is false: 648 is already a
multiple of 4 and of 6. The binding requirement is **integer cell counts**: the
4×4 table has 16 cells and the 6×4 table has 24 cells, so `N` must be a multiple
of lcm(16, 24) = 48. The smallest multiple of 48 that is ≥ 648 is **672**
(48 × 14). At 672 each primary cell holds 42 rows (168 per level ÷ 4 response
levels) and each sensitivity cell holds 28 (112 per level ÷ 4).

**672 is a precision choice, not a power requirement.** The confirmatory 4×4
table needs only 389 rows. 672 is chosen to keep the 6×4 **sensitivity** table
below the same floor and to give integer cells in both. The protocol says so
rather than implying that the confirmatory family demands 672.

### 10.3 Estimator bias and statistical power are different requirements

Passing the bias-floor equation guarantees that the expected upward bias is at
most one third of the MDE. It says nothing about the variance of the estimate,
the probability of detecting a true effect, or the false-positive rate of a
condition contrast. Both requirements are stated separately here.

**Trial-level power.** Under independence, `2N ln2 · Î` is asymptotically χ² with
`df = (kx−1)(ky−1)`. At N = 672 the plug-in standard errors are:

| Table | SE at N = 672 | 80%-power MDE, α = 0.05 | 80%-power MDE, α = 0.005 (Holm) |
| --- | ---: | ---: | ---: |
| 4×4 | 0.004554 bits | 0.0128 bits | 0.0166 bits |
| 6×4 | 0.005880 bits | 0.0165 bits | 0.0215 bits |

The declared 0.05-bit MDE is 11.0 and 8.5 SEs respectively, so trial-level power
at α = 0.01 is effectively 1.0. **The α is stated for every row**: the 0.0128 and
0.0165 figures use α = 0.05 two-sided and are *not* the confirmatory threshold;
the confirmatory family uses Holm, whose smallest threshold is α = 0.005, giving
0.0166 and 0.0215. The earlier text quoted the α = 0.05 row without saying so.

**Corpus-level power is not the trial-level figure.** The 672 rows are not 672
independent stimuli. The track-cluster interval is computed over 24 tracks
(§11.6) and is much wider. The 11σ/8.5σ statement is a **trial-level**
statement about the multinomial table, and no generalisation claim rests on it.

### 10.4 Gate power

Exact binomial and Fisher calculations, not simulation:

| Gate | Contrast | n per group | True rates | Test | Power |
| --- | --- | ---: | --- | --- | ---: |
| P1a | `REAL` vs `NO_STIM` | 40 vs 40 | 50% vs 5% | Fisher one-sided α = 0.0125 | 0.99 |
| P1 | `REAL` vs `NO_STIM` | 40 vs 40 | 50% vs 5% | Fisher one-sided α = 0.0125 | 0.99 |
| P1 | same | 40 vs 40 | 30% vs 2% | same | 0.88 |
| P1 | same | 40 vs 40 | 20% vs 2% | same | 0.49 |
| P1 | same, at n = 20 (rejected) | 20 vs 20 | 50% vs 5% | same | 0.83 |
| P2a | effect-size screen | 40 | 20% vs 2% | ≥ 6/40 and ≥ 4/40 above control | 0.83 |
| P2a | same | 40 | 15% vs 2% | same | 0.56 |
| P2b | effect-size screen | 40 | 10% vs 2% | ≥ 2/40 and ≥ 2/40 above control | 0.92 |

The earlier claim of 0.803 for P1 described the Fisher test alone, while the gate
also required "≥ 10 of 20" and "each control ≤ 1 of 20". The conjunction's power
was 0.32–0.59 and was non-monotonic in `n`. The current gate is a single test
with a stated α, so its power is the number in the table. The fixed 20-trial
floor is gone; at 40 trials per group the effect-size floor is slack and cannot
bind before the test does.

**Multiplicity over the four drives.** Four Fisher tests at α = 0.01 would give a
family-wise error of up to 4%. Each presence family therefore uses
α = 0.0125 = 0.05/4, which controls the family at 0.05 and gives every drive a
valid test, which the "lowest passing drive" rule requires. The two presence
families (P1a, P1) are gates, not confirmatory endpoints, and their combined
false-positive rate is bounded by 0.10.

### 10.5 Stage S power

Phase 6C measured the per-seed paired difference in `I(cue ; action)` over 10
seeds: SD **0.15813337 bits**, SE 0.05000616
(`experiments/results/phase_6c/mutual_information_results.json`,
`C06_fixed_vs_plastic`). That SD is used as the best available between-cluster
variability.

| Clusters | SE | 80%-power MDE, α = 0.05 | 80%-power MDE, α = 0.005 | Power for a true 0.05 bits, α = 0.005 |
| ---: | ---: | ---: | ---: | ---: |
| 40 (rejected) | 0.0250 | 0.0700 | 0.0912 | 0.21 |
| 79 | 0.0178 | 0.0498 | 0.0649 | 0.54 |
| **134 (adopted)** | **0.0137** | **0.0383** | **0.0498** | **0.803** |

With 40 clusters the declared 0.05-bit criterion was below the design's own MDE
of 0.070 bits, and power for a 0.05-bit effect at the Holm threshold was 0.21.
The criterion was unreachable. Stage S is therefore increased to **134 substrate
clusters**, which is the smallest count giving an 80%-power 0.05-bit MDE at
α = 0.005.

**The SD is a proxy, and the revision says so.** 0.1581 bits is the SD of
`I(cue ; action)`, not of `I(cue ; A_neural)`; the neural code may vary more
across substrates than the decoder-mediated action code. The planning MDE is
therefore conditional. The pre-registered rule is:

> After Stage S runs, compute the observed between-substrate SD `s` of the
> paired difference. The realized MDE is `(z_{0.9975} + z_{0.80}) · s / √134`.
> E10 is confirmatory only if that value is ≤ 0.05 bits. If it is larger, E10 is
> reported with its realized MDE and **demoted to exploratory** before any
> direction is examined.

This rule is written before Stage S and is not adjustable after the SD is seen.

### 10.6 What 672 trials do not buy

- They do not buy 672 independent stimuli: the corpus has **24 distinct tracks**
  and one level has one track.
- They do not buy track-level generalisation for H2/H3; the track bootstrap
  interval will be much wider than the trial-level interval.
- They do not buy Stage S power; Stage S is a different substrate with 134
  substrates and its own MDE.
- They do not buy a valid "corrected MI > 0" test, because `max(0, Î − floor)` is
  positively biased at the null (§11.5).

## 11. Statistical analysis plan

### 11.1 Confirmatory endpoints

Ten endpoints. Each is unlocked only if its gate passed; a locked endpoint is
reported as **not evaluated**, never as non-significant.

| ID | H | Estimand | Unit / n | Test | Direction |
| --- | --- | --- | --- | --- | --- |
| E1 | H1 | Proportion of trials with ≥ 1 `STIM` spike | Trial; 672 per condition | Paired McNemar (or paired permutation) `REAL` vs `NO_STIM` | `REAL` > control |
| E2 | H1 | Median `STIM` spike count per trial | Trial | Wilcoxon signed-rank over paired seeds | `REAL` > control |
| E3 | H2 | Proportion of trials with ≥ 1 `H1` spike | Trial; 672 per condition | Paired McNemar | `REAL` > control |
| E4 | H2 | `I(S ; R_H1)` | 672 trials; 24 track clusters | Corrected MI vs its permutation q95; track-cluster bootstrap; paired condition permutation `REAL` vs `SHUFFLED_MASK` | `REAL` > `SHUFFLED_MASK`, corrected > q95 |
| E5 | H3 | `I(S ; R_H2DESC)` | 672 trials; 24 track clusters | As E4 | `REAL` > `SHUFFLED_MASK` and > `PEAK_MATCHED_RECT`; corrected > q95 |
| E6 | H3 | `I(S ; R_H2 ∣ H1 recruited)` | Trials with ≥ 1 `H1` spike | Conditional MI, per-stratum floor, permutation null | Corrected > q95 |
| E7 | H4 | Per-trial indicator "≥ 1 `DESC`→`MOT` pair within 10 ms" | Trial | Paired McNemar; 5 ms and 20 ms sensitivities reported | `REAL` > `NO_STIM` |
| E8 | H5 | `I(S ; decoded state)` | **Trial** (one `A` value per trial); 672 | Corrected MI vs permutation q95; trial-clustered interval | Corrected > q95 |
| E9 | H5 | `I(R_MOT ; decoded state)` | **Trial** | Descriptive only; trial-clustered interval; **no p-value** | Labelled decoder-mediated |
| E10 | H6 | Paired difference in `I(CUE ; A_neural)` | 134 substrate clusters; 21,440 rows | Cluster bootstrap on the paired difference | `plastic` > `fixed` |

**E9 carries no test.** `I(pool; decision)` is partly the decoder's own
definition; it is reported descriptively so that the circularity is visible.

### 11.2 Estimation constants, fixed before data

| Choice | Value | Rationale |
| --- | --- | --- |
| BANC response code | The 4-level recruitment code of §5 | Result-independent; the earlier 3-level absolute-count variant is withdrawn so that the code and the tables cannot disagree |
| Stage S response | 5 levels: argmax over 4 action neurons plus a declared "none" | The fifth level is a declared category, not a data bin |
| Time bin | 10 ms, 30 bins over `[0, 300)` | Resolves a 2 ms refractory interval |
| Time base | Spikes at `(step+1) × 0.5 ms`; edges lower-inclusive | §7.4 clause 10 |
| Entropy | Plug-in with Miller–Madow reported alongside | Consistent with Phase 6B |
| MI | Plug-in with floor `(kx−1)(ky−1)/(2N ln2)`; corrected `= max(0, Î − floor)` | Consistent with Phase 6C |
| NMI | Only when both entropies exceed 0.05 bits | Phase 6B/6C convention |
| Conditional MI | Sample-weighted mean of within-stratum MI with per-stratum floor | `information/` implementation |
| Permutations | 5,000, trial level, labels permuted within stage and condition | p floor 0.0002 |
| Bootstrap | 2,000, seed 20261110; tracks for H2/H3, seeds for H1, substrates for Stage S | Matches §10.1 |
| Multiple comparisons | Holm–Bonferroni over the unlocked family, α = 0.05 | Smallest threshold 0.005 |
| Missing data | No imputation; exclusion counted; > 0.5% in any condition is an integrity failure | One threshold, stated once |
| Minimum support | ≥ 20 rows per level, else collapse by the declared rule or declare not estimable | §11.6 |
| Degenerate variable | Single observed level → degenerate, never negative | Phase 6C C-02 lesson |

### 11.3 Two different nulls, and the paired tests

Stage R reuses one seed across the four conditions, so condition contrasts are
paired at the noise level. The protocol separates two nulls that the earlier
version conflated:

- **(a) Label-permutation null** — "is the observed MI larger than expected with
  no stimulus-response association?" Used for the "> chance" component of E4–E8
  and for every corrected-estimate comparison.
- **(b) Paired condition null** — "is `I_REAL` larger than `I_SHUFFLED_MASK`?"
  Computed by swapping condition labels within each seed (5,000 draws,
  recomputing both estimates) or by a seed-cluster bootstrap of the difference.
  Used for the stated direction of E4 and E5.

E1, E2, E3 and E7 are paired binary or paired continuous outcomes; McNemar and
the signed-rank test are the matched tests. Fisher's exact test is used only for
the unpaired Stage P comparisons, where pairing is not available because the
control arm differs in condition rather than in seed.

### 11.4 The corrected estimator is not tested against zero

`max(0, Î − floor)` is positively biased at the null: `Î` is approximately
half-normal around the floor with SE 0.004554, so the corrected value has a
positive mean of roughly 0.0018 bits even when there is no association. Endpoints
whose earlier criterion was "corrected MI > 0" would pass at the null far more
often than their nominal rate.

**Rule.** Every MI endpoint compares its corrected statistic to the 95th
percentile of `max(0, Î_perm − floor)` computed from its own permutation null.
The corrected value and its interval are still reported; they are never used as a
one-sided test against zero.

### 11.5 Multiplicity

The confirmatory family is fixed by the gates, not by the results: E1–E3 are
evaluated if P1a/P1 pass; E4–E6 if P2a/P2b pass and P2c/P2s do not overturn
specificity; E7 if P3a passes; E8–E9 if P3 passes; E10 if Stage S integrity
passes. The largest possible family is 10, so Holm at α = 0.05 gives a smallest
threshold of 0.005, which is above the permutation p floor of 0.0002. Endpoints
added after results are exploratory and are labelled so.

Specificity gates P2c and P2s are two tests at `d*`; each uses α = 0.025
(Bonferroni over two), controlling their combined false-positive rate at 0.05.

### 11.6 Clustering, tracks and degenerate variables

- **Track clusters.** Resample the **24 distinct tracks** with replacement,
  recompute the whole table, 2,000 draws. Because six tracks appear in two
  levels, a resample re-uses a track in every level it belongs to; this preserves
  the within-track dependence across levels, which is the point of clustering.
- **`OBST_NEAR` is not estimable.** One track yields no cluster interval. That
  level is reported descriptively, is excluded from the track-level generalisation
  claim, and cannot carry an E5 direction.
- **Support.** An estimate requires ≥ 20 rows per level. A level below 20 is
  collapsed by the rule declared in §8.5 or the endpoint is declared not
  estimable.
- **Bin-level dependence.** 10 ms bins are summaries of a trial. A 5 ms and a
  20 ms recomputation is reported as a sensitivity and is never used to select a
  result.
- **Degenerate responses.** A single observed level gives `I = 0` by
  construction and is reported as **degenerate / inconclusive**. This is the
  Phase 6C C-02 lesson applied prospectively.
- **Stacked-window estimates.** Any estimate computed over the 3,360
  trial × window rows is descriptive, carries a trial-clustered interval and
  reports the effective n of 672.

### 11.7 Missing data

No imputation. A trial failing a mandatory field is excluded and counted in the
missing-data table. Exclusions above **0.5%** in any condition are an integrity
failure (§12.1). The 5% figure refers only to the determinism re-run sample.

### 11.8 Execution order

1. Validate records and schema; count exclusions; run the 68/68 determinism
   sample.
2. Reproduce the archived 4H condition-B **and** condition-C spike hashes (C8).
   If either fails, stop.
3. Evaluate P1a and P1 at all four drives; then P2a and P2b at all four drives.
4. Freeze `d*` and write the gate-decision file, including the Clopper–Pearson
   control upper bound.
5. Read P2c, P2s, P3, P3a at `d*`; append to the gate file without altering `d*`.
6. Run Stage R analysis only on unlocked conditions.
7. Run the Stage S integrity check; compute the realized MDE (§10.5) before
   examining the E10 direction.
8. Compute E1–E10 with the fixed constants; apply Holm.
9. Write the results table with raw, floor, corrected, interval, permutation
   q95, Holm-adjusted p and support counts for every endpoint.
10. Freeze the results JSON (SHA-256) before writing any prose.

## 12. Success and failure criteria

Every criterion is operational: it can be evaluated from the frozen result file
without judgement.

### 12.1 Recording integrity

| Outcome | Criterion |
| --- | --- |
| **Pass** | ≥ 99.5% of trials complete every mandatory field in every condition (exclusion ≤ 0.5%); the 68 recording-enabled repeats reproduce `spike_hash`; the 68 recording-disabled repeats match their recording-enabled counterparts; archived 4H condition-B and condition-C hashes reproduced; no `SpikeCapacityExceeded`; all recorded potential arrays finite. |
| **Fail** | Any unexplained determinism mismatch; silent truncation; exclusion > 0.5% in any condition. |
| **Inconclusive** | Not applicable; integrity is binary. |

### 12.2 Reproducibility of the analysis

| Outcome | Criterion |
| --- | --- |
| **Pass** | Re-running the analysis on frozen inputs reproduces every number within 1e-9; both seed halves (336/336) agree in sign on every unlocked endpoint. |
| **Fail** | A number changes after freezing, or the halves disagree in sign on a confirmatory endpoint. |
| **Inconclusive** | Sign disagreement is reported as instability for that endpoint only. |

### 12.3 Direct sensory activation (H1)

| Outcome | Criterion |
| --- | --- |
| **Positive** | P1a passes and E1/E2 favour `REAL`. |
| **Negative** | `REAL` and `NO_STIM` are at the same floor while `DIRECT_INJECTION` drives `H1`: a drive/encoder failure, reported as such. |
| **Inconclusive** | `REAL` and control differ but `DIRECT_INJECTION` also fails; or the effect is carried by one seed half. |

### 12.4 First-hop propagation (H2)

| Outcome | Criterion |
| --- | --- |
| **Positive** | P1 passes and E3/E4 favour `REAL`. |
| **Negative** | P1 fails at every tested drive while P1a passed: no first-hop propagation under this design. |
| **Inconclusive** | P1 passes but E4 is degenerate (fewer than two recruitment levels). |

### 12.5 Downstream propagation and information (H3)

| Outcome | Criterion |
| --- | --- |
| **Positive** | P2a and P2b pass; E5 survives Holm with a corrected value above its permutation q95 and a track-cluster interval excluding zero. |
| **Negative** | P2a and P2b fail at **every tested drive (200, 400, 800, 1200 pA)**. Reported as "no propagation detected under this design", consistent with Phase 4H.4. |
| **Inconclusive** | `REAL` exceeds `NO_STIM` but not `PEAK_MATCHED_RECT` (charge-driven, P2c failed); or `SHUFFLED_MASK` equals `REAL` (P2s failed); or all downstream channels are degenerate; or the track-cluster interval includes zero while the trial-level result does not. |

### 12.6 Motor recruitment and decoder (H4, H5)

| Outcome | Criterion |
| --- | --- |
| **Positive** | P3a and P3 pass; E7 survives Holm; E8 is above its permutation q95. Labelled decoder-mediated even then. |
| **Negative** | P3 passed but E7 and E8 are at the null. |
| **Inconclusive** | P3 failed (decoder never left NEUTRAL) or P3a failed (no motor spike): the endpoints are untestable, which Phase 4H.4 suggests is the likely outcome. |

### 12.7 Plasticity-related neural change (H6)

| Outcome | Criterion |
| --- | --- |
| **Positive** | The Phase 5F **direction** is re-estimated on the new replicate; the realized MDE (§10.5) is ≤ 0.05 bits; the paired difference exceeds the realized MDE with an interval excluding zero. |
| **Negative** | The direction reappears but the difference is below the realized MDE or its interval contains zero. This extends the Phase 6C C-06 negative result and is reported as "no detectable neural-level change". |
| **Inconclusive** | The direction does not reappear; or > 20% of substrates are degenerate; or row-level and substrate-level signs disagree; or the realized MDE exceeds 0.05 bits (E10 demoted to exploratory). |

### 12.8 Task performance (reproduction check only)

| Outcome | Criterion |
| --- | --- |
| **Pass** | `plastic_complete` exceeds `fixed_complete` by a paired difference whose interval excludes zero, in the Phase 5F direction. |
| **Fail** | No difference, or a reversed difference. A reversal is reported, not reframed. |
| **Inconclusive** | Not applicable. Failure blocks E10 only. |

### 12.9 How the criteria combine into one phase verdict

| Combination | Phase verdict |
| --- | --- |
| Integrity fails | **Invalid** — no scientific conclusion. |
| Integrity passes, P2a/P2b fail at all four drives | **Negative on propagation**, consistent with Phase 4H.4/4H.5. Stage R and E4–E9 are not run. |
| P2a/P2b pass, P2c fails | **Charge-driven propagation.** Propagation exists but the pattern-specificity claim is withdrawn. |
| P2a/P2b pass, P2s fails | **Propagation without feature specificity.** H2/H3 descriptive. |
| P2 passes, E5 null above its permutation q95 | **Propagation without detectable stimulus-specific information.** |
| P2 and E5 pass, P3 fails | **Information reaches downstream populations; the decoder does not.** |
| All gates pass and endpoints survive Holm | **Computational information flow established in the model** (evidence grade at most E2). Not a biological claim. |
| Stage S integrity fails or E10 is underpowered | E10 skipped or demoted; the Stage R verdict stands independently. |

A statistically significant endpoint never by itself moves the verdict above
"computational information flow established in the model". Biological validity
is not an available conclusion of this phase under any combination.
## 13. Feasibility and resources

### 13.1 Measured anchors

Every figure below is derived from a measured constant, not from a benchmark of
unwritten code.

| Anchor | Value | Source |
| --- | --- | --- |
| BANC run wall time, 300 ms trial | 2.54 s median (1.66–4.30 s over 352 timings) | `population_sensitivity.json` |
| Phase 5 episode throughput | ≥ 20.3 episodes/s (394.41 s for ≥ 8,000 core episodes) | Phase 5F |
| Stage S bytes per episode | 6.25 kB | 21,440 rows × ≈0.312 kB, rounded up |
| BANC bytes per trial, mandatory | 135 kB | §7.3 |
| BANC bytes per trial, optional O2+O3 | 550 kB | §7.3 |

The Phase 4H round-trip median of 20.62 s is **not** used: it includes replay
instrumentation this campaign does not need. The single 5,057 s outlier in that
set is excluded from the anchor and is instead treated as a failure mode (R14).

### 13.2 Recalculated budget

| Stage | Work | Wall time | Mandatory storage |
| --- | --- | ---: | ---: |
| P | 964 BANC runs | 964 × 2.54 s = 2,449 s = **0.68 h** | 964 × 135 kB = **130 MB** |
| R | 2,864 BANC runs | 2,864 × 2.54 s = 7,275 s = **2.02 h** | 2,864 × 135 kB = **387 MB** |
| S | 64,320 episodes | 64,320 / 20.3 = 3,168 s = **0.88 h** | 64,320 × 6.25 kB = **402 MB** |
| A | 0 new simulations | **0.50 h** | **10 MB** |
| **Total, mandatory** | **3,828 BANC runs + 64,320 episodes** | **4.08 h** | **929 MB** |
| Optional O2+O3 on Stage R | same runs | +I/O, no new simulation | +1,575 MB → **≈2.5 GB** |

The hard budget in §7.3 is 2.7 GB; the optional configuration lands at ≈2.5 GB
and therefore fits only if the runner's pre-flight disk check passes. If it does
not, O2/O3 are dropped rather than partially written. **Optional diagnostics are
recorded for Stage R only**; Stage P records aggregate population counts, which
are mandatory fields, and does not need the panel.

Runtime is sequential. The three changes from revision 1 that drive the
increase — 964 rather than 324 Stage P runs, 2,864 rather than 2,822 Stage R
runs, and 64,320 rather than 19,200 Stage S episodes — are each traceable to a
corrected requirement (§8.2, §8.6, §8.7). Revision 1's 2.8 h figure was
inconsistent with its own components; 4.08 h is the arithmetic of this design.

### 13.3 Memory

Peak resident memory is estimated — not measured — at **0.3–0.5 GiB** with the
panel enabled: the graph and policy arrays dominate, neuron and synapse state
are two vectors of 172,433 elements, and the `SpikeRecorder` holds at most
500,000 spikes (4 MB at capacity). Phase 6A measured 0.97 GiB free.

Consequently:

- the campaign runs **one process at a time**;
- concurrency is enabled only if a pre-flight check reads more than 1.5 GiB
  free, and then at most two workers;
- a pre-flight check below 0.75 GiB free aborts before any run starts rather
  than failing mid-campaign.

This estimate is retained as an open empirical item (§14.3, RA-4). A memory
overrun is a resource failure, not a scientific result.

### 13.4 Analysis cost

Ten endpoints × 5,000 label permutations on a 672-row table is ≈50,000 MI
evaluations, each sub-millisecond with `numpy.bincount`. The track-cluster
bootstrap (1,000 resamples of 24 tracks, recomputing the whole table each time)
and the 134-substrate Stage S bootstrap are the dominant costs. The 0.5 h Stage
A allowance covers both with margin. Nothing in Stage A is parallelised, so the
0.5 h is a wall-clock figure.

### 13.5 Reusable modules (no modification)

| Module | What it provides | Used for |
| --- | --- | --- |
| `brain/banc_simulator.py` | `BancSimulator`, `BancStimulation`, `BancSignedSynapses`, `BancSimulationResult` | Every Stage R run |
| `brain/neuron_model.py` | `LIFPopulation`, `LIFParameters`, `membrane_potential` | Integration; O2 panel |
| `brain/neural_activity.py` | `SpikeRecorder.save`, `.spike_counts`, capacity | Spike storage |
| `brain/banc_sensory_adapter.py` | `BancSensoryMapping`, `BancEventDrive`, `ConstantChargeDrive`, `shuffle_feature_identities` | Stage P/R conditions |
| `brain/banc_simulation_adapter.py` | `BancActivityAdapter.decode` | Decoder windows |
| `motor/motor_decoder.py`, `motor/populations.py` | `MotorDecoder`, `DecoderConfig`, action pools | E8/E9 |
| `sensory/population_encoder.py` | `GaussianPopulation`, `EncoderSpec` | Stimulus encoding |
| `plasticity/*` | `PlasticSimulator.step_callback`, `EligibilityStore`, `WeightState`, Phase 5 tasks | Stage S |
| `information/*` | bias, entropy, MI, CMI, NMI, permutation, bootstrap, digest | Stage A |
| `experiments/phase_4h/common.py` | `load_world`, `spike_hash`, `integrity_snapshot` | C8 replay |

### 13.6 Code to be written after approval

| New file | Purpose | Size |
| --- | --- | ---: |
| `experiments/phase_6d/recording.py` | `TrialRecorder`: wraps `sim.neurons.step`, applies clause 4 threshold substitution, builds the sparse record, writes npz + manifest row | 350–450 |
| `experiments/phase_6d/trial_schedule.py` | Declared levels, track-balanced event allocation, seed lists, condition assignment, `d*` selection | 220–320 |
| `experiments/phase_6d/run_propagation_pilot.py` | Stage P runner, gate evaluation at all four drives, writes the gate decision to disk before Stage R can start | 260–360 |
| `experiments/phase_6d/run_recording_campaign.py` | Stage R runner, resume via manifest, 136 determinism repeats | 300–400 |
| `experiments/phase_6d/run_plasticity_recording.py` | Stage S runner on 134 substrates with a `None`-returning callback | 250–350 |
| `experiments/phase_6d/analyse_phase_6d.py` | E1–E10, Holm, permutation, track-cluster bootstrap, gate-aware family | 500–700 |
| `experiments/phase_6d/build_report.py` | Markdown + JSON from the frozen results | 200–300 |
| `configs/phase_6d_recording.yaml` | Every constant in §8, §10 and §13 | ≈120 |
| `tests/test_phase_6d_recording.py` | T1–T12 plus gate logic on synthetic tables and estimator agreement with `information/` | 500–700 |

**Total ≈ 2,580–3,700 lines.** The only object that touches the simulator is the
wrapper assigned to `sim.neurons.step`; no production module is edited, and G2
enforces that (§15).

## 14. Risks and limitations

### 14.1 Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Residual |
| --- | --- | --- | --- | --- | --- |
| R1 | Propagation never appears at any drive ≤ 1200 pA | High — 4H.4 measured zero second-hop current | Programme stops at Stage P | P1/P2a/P2b evaluated at all four drives before any stop; a stop is documented | A true propagation rate near 10% can be missed; the screen's sensitivity curve is stated in §8.4 |
| R2 | Descending and motor populations structurally unreachable | High — 9 `H1D`, 0 first-hop motor targets, 4 motor neurons at two hops | H4/H5 untestable | P3/P3a report untestable, not negative | None; property of the graph and mapping |
| R3 | Corpus carries 43 events on 24 tracks; `OBST_NEAR` is one track | Certain | Corpus-level generalisation limited | Track-cluster bootstrap; `OBST_NEAR` declared not estimable at track level; wording restricted to sampled tracks | Cannot be repaired without new perception output |
| R4 | The `sim.neurons.step` wrapper changes behaviour | Low | Invalidates all data | C8 archive replay of conditions B and C; 68/68 recording-on/off repeats; T1–T3 | A deterministic behavioural change would pass a hash test, so T2 uses two independent anchors |
| R5 | Memory pressure; 0.97 GiB free at audit | Medium | Run failures, swapping | Sequential execution, 500k cap, panel only, pre-flight checks | A larger graph load on a busy host could still fail |
| R6 | Float32 summation order varies across processes | Low | Determinism mismatch | Repeat in a separate process; compare hashes and parsed values | Cross-machine bit-exactness is not guaranteed |
| R7 | Bias floor is an approximation for sparse tables | Medium | Over- or under-correction | Report raw, floor, corrected, interval; never corrected alone | An estimate near the MDE can be materially off either way |
| R8 | Effective stimulus n is 24 tracks, not 672 trials | Certain | Wider corpus-level intervals | Both inference levels reported separately | Cannot be fixed within this corpus |
| R9 | `d*` is selected from pilot data | Certain | Data-dependent design parameter | P1a/P1/P2a/P2b are evaluated at **all** drives first and `d*` is frozen before any downstream outcome; the freeze is written to disk | A reader may still view the choice as adaptive |
| R10 | `MATCHED_CHARGE` at ≈46.7 pA/neuron is subthreshold | Certain | Cannot serve as a control | Demoted to descriptive; replaced by `PEAK_MATCHED_RECT` (C2) | `PEAK_MATCHED_RECT` tests charge *form*, not total charge |
| R11 | `NO_STIM` produced zero spikes in 4H | High | C1 has no variance | Presence gates are screens with a stated control bound (0/40 → 7.2% upper 95%) | The gates' discrimination comes mostly from `REAL` |
| R12 | Stage S is a different substrate from Stage R | Certain | No pooled inference | E10 reported separately; H6 wording restricted to the synthetic task | Reader over-generalisation; wording is the only control |
| R13 | Single implementation; no independent re-implementation | Certain | Shared conceptual errors | Archive replay, determinism, T1–T12 | Cannot be eliminated in this phase |
| R14 | One pathological run stalls the campaign | Low — one 5,057 s run observed | Schedule slip | Per-run timeout with an explicit failure record; resume from manifest | A timeout loses that trial and is reported as missing |
| R15 | Decoder endpoints are circular by construction | Certain | E8/E9 cannot support a motor claim | Labelled decoder-mediated; excluded from the verdict above E2; C13 ablation | None |
| R16 | Stimulus re-anchored to 50 ms | Certain | Latency not comparable to the archive | Latency descriptive only; no cross-archive latency claim | None |
| R17 | No neuromodulation, adaptation or cell-type conductances | Certain | Model cannot represent biological learning | Stated in every result section | Requires a different model |
| R18 | Recorder overhead is unmeasured | Medium | 4.08 h may be an underestimate | Budget is per-run anchored and each run is timed; if the median exceeds 3.5 s the campaign re-plans before continuing | The first 40 Stage R runs are the calibration sample |
| R19 | The 0.1581-bit Stage S SD is a proxy from a different design | Certain | E10's MDE may be mis-stated | Pre-registered realized-MDE rule (§10.5); E10 demoted if the realized MDE exceeds 0.05 bits | The proxy cannot be validated without running Stage S |

### 14.2 Limitations that survive every mitigation

1. **The propagation gate may fail, and that is a plausible outcome.** 4H.4
   measured second-hop current of exactly zero and a closest first-hop membrane
   potential of −56.926 mV, 6.926 mV below threshold. Nothing here guarantees
   that raising the drive changes that; the design guarantees only that failure
   is measured cleanly at four drives and reported as a stop.
2. **The motor pathway is very likely untestable.** With 0 first-hop motor
   targets and 9 descending neurons, H4 and H5 depend on an event not yet
   observed. The design makes them conditional instead of assuming them.
3. **Recording is panel-based, never full-population.** No dense
   `n_neurons × n_time_bins` array is produced in any format; O1 is rejected by
   a guard.
4. **Corpus-level inference rests on 24 tracks and 43 events**, with
   `OBST_NEAR` represented by a single track. No claim can exceed "these
   sampled tracks".
5. **No biological ground truth and no independent implementation.** No Stage R
   result can be promoted above evidence grade E1–E2.
6. **The model has no neuromodulation, adaptation or cell-type-specific
   conductances**, so "plasticity" here means a three-factor rule on a signed
   static graph, not biological learning.
7. **Memory and recorder overhead are estimates**, not measurements. The budget
   in §13.2 is an arithmetic consequence of anchors, not a benchmark.

### 14.3 Retained unresolved items

These are carried forward openly. None is waived, and each has a declared
handling rule so that it cannot be resolved post hoc in the results.

| ID | Unresolved item | Why it cannot be closed here | Declared handling |
| --- | --- | --- | --- |
| RA-1 | Whether any tested drive produces second-hop propagation | Requires the Stage P runs, which this phase does not execute | Stop rule P2a/P2b; failure reported as a stop, not a null campaign |
| RA-2 | Whether descending or motor populations are reachable at all | Requires Stage P outcome; 4H evidence is negative | P3/P3a gate; untestable is a reported outcome |
| RA-3 | Corpus-level generalisation beyond 24 tracks | The archived perception output contains 24 distinct tracks; no new perception is in scope | Track-level analysis declared descriptive; no claim beyond sampled tracks |
| RA-4 | True peak memory with the panel enabled | Not measured; depends on host and graph residency | Sequential execution, pre-flight checks, restart-from-manifest on failure |
| RA-5 | Recorder wall-time overhead | Not measured until the recorder exists | First 40 Stage R runs time the campaign; re-plan if median > 3.5 s |
| RA-6 | The Stage S between-substrate SD for `I(CUE; A_neural)` | 0.1581 bits is measured on a different design (Phase 6C, different substrate count) | Realized-MDE rule fixed in §10.5 before Stage S runs; E10 demoted if MDE > 0.05 bits |
| RA-7 | Behavioural validity of the decoder | The decoder is a hand-written rule, not a measured motor command | E8/E9 labelled decoder-mediated; excluded from the phase verdict above E2 |

## 15. Approval gates

These are review gates for the human supervisor. They are not experimental
outcomes, and none of them may be waived by the analyst. A gate that is skipped
is recorded as skipped in the results JSON.

| Gate | Question | Evidence required | Consequence if not passed |
| --- | --- | --- | --- |
| **G0** | Is this revision approved as the protocol of record? | This document, its JSON and the correction matrix, with hashes | No code is written |
| **G1** | Is the schedule and configuration fixed? | `configs/phase_6d_recording.yaml` reproducing every constant in §8/§10/§13; `trial_schedule.py` unit-tested against §8.5 | No instrumentation is written |
| **G2** | Does instrumentation leave the simulator unchanged? | T1–T12 pass; archived 4H B and C hashes reproduced; `git status` limited to the three permitted paths; README hash unchanged | Campaign does not start |
| **G3** | Does Stage P run to completion? | P0 passes on all 964 records; gate decision written to disk | Stages R and S do not start |
| **G3b** | *(Optional escalation)* Is the null driven by too-coarse sampling? | Only if P2a/P2b fail at every drive: 160 additional runs at 1600 and 2000 pA (40 `REAL` and 40 `NO_STIM` trials per drive), declared before running | If still null, the stop stands; if positive, the escalation is reported as exploratory and does not retroactively unlock the confirmatory family |
| **G4** | Is the gate decision frozen? | `d*`, P1a, P1, P2a, P2b, P2c, P2s, P3, P3a with their control bounds, SHA-256'd | Stage R does not start |
| **G5** | Is Stage R complete and valid? | 2,864 records; 136 repeats agree; exclusion ≤ 0.5% per condition | Analysis does not start |
| **G6** | Is Stage S complete and valid? | 64,320 episodes; 134 substrates; C7 `eta = 0` hashes agree | E10 is skipped; Stage R verdict stands |
| **G7** | Is the analysis frozen before prose? | Results JSON SHA-256 recorded, all ten endpoints present or explicitly marked not estimated | No report is written |

G3b is **optional and explicitly exploratory**. Its purpose is to distinguish
"too coarse a drive grid" from "no propagation", which is the single most
informative ambiguity left after a Stage P null. It is declared here, before
any outcome, and cannot be used to relabel a failed confirmatory gate as a pass.

## 16. Next actions, in order

1. Human review of this revision against §2 and the correction matrix. No code
   until G0.
2. Fix `configs/phase_6d_recording.yaml` from §8 and §10; add a test that every
   declared constant appears in the config and nowhere else. (G1)
3. Write `recording.py` and `trial_schedule.py`; run T1–T12. T1 must reproduce
   the archived 4H condition-B **and** condition-C hashes. (G2)
4. Run Stage P (964 runs, ≈0.68 h). If the campaign must be interrupted, resume
   from the manifest; do not restart from scratch. (G3)
5. Evaluate P1a, P1, P2a, P2b, P2c, P2s at all four drives and freeze `d*`
   together with the control bounds. If P2a/P2b fail everywhere, decide on G3b
   **before** running it. (G4)
6. Only then run Stage R (2,864 runs, ≈2.02 h). Record the 136 repeats. (G5)
7. Run Stage S (64,320 episodes, ≈0.88 h) with the `None`-returning callback and
   the `eta = 0` reproduction. (G6)
8. Compute E1–E10 on frozen inputs, write and hash the results JSON, then write
   the report. (G7)
9. Report the phase verdict using §12.9, including every endpoint that was not
   estimated and why.

Nothing in this list is authorised by this document. It is the sequence that
becomes available only after G0.

## 17. Final verdict

**READY WITH REMAINING LIMITATIONS.**

The revision addresses all 36 audit issues at the level of protocol design:
29 are closed outright and 7 carry a qualified status recorded in the matrix
(two leave an empirical item, four adopt a different but justified remedy, one
recommendation is not adopted). Every blocking finding A1–A7 has a specific
correction with a named verification method (matrix §1–§2), the sample-size
argument now separates estimator bias from statistical power (§10), the gates
separate first-hop from second-hop propagation and are evaluated across all four
drives before any stop (§8.4), the corpus is treated as 24 tracks rather than
672 independent stimuli (§8.5, §10.1), recording correctness is specified at the
level of the `_V` reset and the event-time rebase (§7.4), and every resource
figure is recomputed from a measured anchor (§13).

It is **not** "READY FOR HUMAN REVIEW" without qualification, because seven
items cannot be closed from the evidence available before execution. They are
listed in §14.3 and summarised here:

1. Whether any drive produces second-hop propagation is unknown until Stage P
   runs (RA-1).
2. Whether descending or motor populations are reachable is unknown until
   Stage P runs (RA-2).
3. Corpus-level generalisation is bounded by 24 tracks, and `OBST_NEAR` by one
   track; no further perception output is in scope (RA-3).
4. Peak memory with the panel enabled is estimated, not measured (RA-4).
5. Recorder overhead is unmeasured until the recorder exists (RA-5).
6. The Stage S SD is a proxy from a different design, so E10's MDE is
   provisional until the realized value is computed (RA-6).
7. The decoder is a hand-written rule and cannot support a motor claim (RA-7).

None of these is a defect of the protocol; they are empirical facts that only
execution can supply, and each has a pre-registered rule that applies whether
the outcome is positive or negative. Approving this revision means approving
Stage P as the instrument that resolves RA-1 and RA-2, not approving a
propagation, information-flow or plasticity conclusion.

