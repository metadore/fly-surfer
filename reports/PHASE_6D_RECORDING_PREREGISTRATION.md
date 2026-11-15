# Phase 6D — Recording Campaign Pre-Registration

**Status:** DESIGN ONLY — NOT EXECUTED  
**Phase:** 6D  
**Document type:** Pre-registration of a recording campaign, not a result  
**Project root:** `C:\Users\Hp\fruitfly\FLY-SURFER`  
**Date:** 2026-11-11  
**Machine-readable companion:** `reports/PHASE_6D_RECORDING_PREREGISTRATION.json`

## 0. Scope, authority and non-claims

This document specifies the smallest experiment that could collect the
neural-level data Phase 6B and 6C could not estimate. It is a design. Nothing
in it has been run: no simulation was executed, no recording was generated, no
model was trained, no neural architecture or parameter was changed, and no
archive was rewritten.

The protocol is binding only once approved under the gates in Section 13. Until
then this file is a proposal. It does **not** revise any Phase 4H, Phase 5 or
Phase 6B–6C statement, and it does not claim that any hypothesis below is true.

Non-claims carried into the protocol:

1. A mutual-information estimate is not causal influence. It measures shared
   information between two declared variables, not transmission, mechanism or
   direction.
2. A decoder label (LEFT, RIGHT, JUMP) is not a biological motor command.
   Decoder-mediated information is consistency with a declared decision rule.
3. A simulated spike is not a recorded biological spike. Any result from this
   protocol is evidence about the implemented model, at best at internal
   evidence grade E1–E2 as defined in Phase 4H.5.
4. A propagation-positive pilot would establish that the model can transmit the
   declared drive under a calibrated setting. It would not establish that a fly
   does so.
5. Structural connectivity does not imply functional transmission. Every
   hypothesis below is stated as a question about observed spikes, never as an
   inference from the adjacency matrix.

## 1. Executive summary

**What is missing, and why.** Phase 6B/6C estimated entropy and mutual
information only on aggregate archived variables because no completed
experiment persisted spike trains together with their sensory inputs. The four
declared-but-unavailable endpoints (6B U01–U04), the four structural gaps 6A
listed (MD-04 to MD-07), and the nine infeasible analyses 6A recorded
(IF-01 to IF-09) all reduce to one archival fact: there is no per-trial,
per-neuron recording paired with its stimulus. Phase 6D is the recording
campaign that would supply it.

**Recording strategy: A, not B.** The protocol instruments controlled
simulation runs to persist per-trial neural activity. Biological recording from
a fruit-fly preparation is **not** required and is **not** proposed. The
question is what this model computes; a biological preparation would answer a
different question and could not be connected to the simulation's neuron
identities, drive schedule or declared variables. Section 4 states exactly what
simulation instrumentation can and cannot establish.

**Blocking dependency, handled first.** Phase 6A marked 6D as blocked because
Phase 4H.4 recorded *zero* non-stimulated spikes: both arms of the intended
downstream contrast were empty, so any downstream information estimate would be
zero by construction. The protocol therefore starts with a small, cheap
**Propagation Pilot** whose only purpose is to decide whether a
propagation-positive configuration exists. If it does not, the full information
analysis does not proceed, and that negative outcome is the Phase 6D result.

**Design in one table.**

| Stage | Purpose | Runs | Gate to the next stage |
| --- | --- | ---: | --- |
| P | Propagation Pilot at four pre-registered drives | 240 + 84 controls | P1: first-hop spiking above controls |
| R | BANC recording campaign at the pilot-selected drive | 2,688 | recording-integrity criteria |
| S | Fixed-versus-plastic neural recording on the Phase 5 task substrate | 19,200 episodes | 5F effect reproduced, then E10 |
| A | Pre-registered information analysis and report | 0 new simulations | none |

**Minimum condition set.** Four BANC conditions — REAL, SHUFFLED_MASK,
MATCHED_CHARGE, NO_STIM — plus one descriptive stream check and a fixed-versus-
plastic pair on the Phase 5 substrate. Six of the seven Phase 4H conditions are
deliberately not repeated; Section 6 justifies each omission.

**Sample size, calculated not chosen.** 672 trials per condition. That number
is the smallest round count that keeps the analytic MI bias floor at or below
0.017 bits for the widest declared confirmatory table (6×4, floor 0.0161). The
minimum detectable effect is declared as 0.05 bits, so the worst-case floor is
32% of the MDE. The 40-episode 4×4 cell used in Phase 5F/6C (floor 0.162 bits)
is explicitly not reused as evidence of adequate power.

**Feasibility.** 2,688 runs of 300 ms at the measured median of 2.54 s per run
is about 1.9 h of single-process wall time for Stage R (≈2.2 h for all stages),
about 0.35 GB of mandatory retained output (≈1.8 GB if the optional panel
diagnostics are enabled), and 0.3–0.5 GiB of peak resident memory against the
0.97 GiB that was free at the Phase 6A audit. The required new code is additive
and lives only in `experiments/phase_6d/`; `brain/`, `sensory/`, `motor/`,
`plasticity/` and `information/` are read-only for this phase.

**Status: READY WITH LIMITATIONS.** Five limitations are load-bearing and are
not repairable by this design: the propagation-positive gate may fail at every
tested drive; the motor pools are structurally unreachable from the annotation
mapping, so H4 and H5 will probably be untestable; membrane and synaptic-current
recording is possible only through an instance-level wrapper on a declared
neuron panel; the archived stimulus corpus has few distinct obstacle events; and
H6 runs on a different substrate from H1–H5.

## 2. Existing evidence and limitations

Everything in this section is carried forward unchanged. Phase 6D does not
reinterpret it, does not re-grade it, and does not use it to make the proposed
experiment look promising.

### 2.1 Phase 4H — established findings

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

Phase 4H.5's own recommendation was a pre-registered **sensory-drive threshold
and propagation calibration** with a direct first-hop current-injection positive
control and a single-first-hop-spike test. Stage P implements exactly that
recommendation and nothing more.

### 2.2 Phase 5 — established findings

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
synthetic 36-node task graph, not the BANC connectome.

### 2.3 Phase 6A–6C — established findings

| ID | Finding (unchanged) |
| --- | --- |
| PF-6-1 | Archived-data entropy and mutual-information analyses are complete, with declared limitations. |
| PF-6-2 | Plasticity did **not** increase cue-to-action mutual information in C-06 (−0.086 bits, p = 0.125, Holm 0.25). |
| PF-6-3 | Decoder-mediated MI is **not** biological neural-to-motor information. |
| PF-6-4 | Existing archives do **not** support the missing neural-level analyses. |

Endpoints the archive could not support, recorded rather than proxied
(6B §10, 6C §7): spike-train entropy, population-response entropy,
membrane-potential entropy, cue-to-population-code MI, cue-to-spike-count MI,
and neural-to-reward MI. Reasons: no per-neuron spike trains except one 74-spike
smoke run; aggregate spike counts constant within conditions; membrane
potentials never serialised; no stored run pairing stimulus with spikes.

### 2.4 What the implementation actually records (verified, not assumed)

This table was produced by reading the source, not the reports. It is the only
basis for the schema in Section 5.

| Interface | File | What is available | What is persisted today |
| --- | --- | --- | --- |
| `SpikeRecorder` | `brain/neural_activity.py` | `(time_ms float32, neuron_index int32)` pairs for every neuron in the graph; `spike_counts()`; `population_rate()`; raises `SpikeCapacityExceeded` instead of dropping spikes | nothing, unless a runner calls `save()`; only the Phase 4G smoke run did |
| `SpikeRecorder.save` | `brain/neural_activity.py` | compressed npz with `spike_times_ms`, `spike_neuron_indices`, `n_neurons`, `duration_ms`, `capacity` | n/a |
| `LIFPopulation.membrane_potential` | `brain/neuron_model.py` | full per-neuron voltage vector, mV, in memory at every step | never serialised by any runner |
| `BancSignedSynapses.synaptic_current_pa` | `brain/banc_simulator.py` | per-neuron total synaptic current, plus `excitatory_current_pa` and `inhibitory_current_pa` separately, pA, in memory at every step | never serialised; Phase 4H.4 read only per-neuron maxima through an instance wrapper |
| `BancSimulator.run` | `brain/banc_simulator.py` | monolithic loop; no callback parameter | aggregate summary only |
| instance wrapper on `sim.neurons.step` | pattern used in `experiments/phase_4h/analyse_sensory_roundtrip.py` lines 816–832 | complete per-step access with **no source edit** | used in Phase 4H.4 for maxima only |
| `PlasticSimulator.step_callback` | `plasticity/plastic_simulator.py` line 303 | `step_callback(step, time_ms, spikes, simulator)`, so the callback can read neurons, synapses, engine traces and weight state | existing runners store reduced metrics |
| `WeightState.effective_magnitude` | `plasticity/weights.py` | current effective weight for every plastic edge | one checkpoint npz in Phase 5E |
| `EligibilityStore.value` and `active_edges` | `plasticity/traces.py` | sparse per-edge trace values at the current step | per-condition summaries only |
| `BancActivityAdapter.decode` | `brain/banc_simulation_adapter.py` | per-window decoder decisions from a spike recorder | decisions written into experiment JSON |

Two consequences follow directly and are the foundation of this protocol.

1. **Spike trains are already fully supported** by a production API. No new
   neural code is needed to persist them.
2. **Membrane potentials and synaptic currents are readable but only in
   memory.** They can be sampled from a per-step wrapper without editing any
   protected module, but they cannot be recorded for the whole 172,433-neuron
   graph: Phase 6A measured 4.55 GB per 3.3 s run for full-population
   potentials against 0.97 GiB of free RAM. They are therefore **optional
   diagnostics on a declared panel**, never mandatory fields.

## 3. Research hypotheses

Six hypothesis families are declared. Each is a question about observed spikes
in declared populations, not an inference from the structural graph. "Table"
gives the discretisation used for the confirmatory estimate; "N" is the number
of independent trials used in the design; it is set by the 6×4 sensitivity
table to keep the worst-case analytic bias floor at or below 0.017 bits
(Section 8.2).

Population and code definitions used throughout:

| Symbol | Population | Size |
| --- | --- | ---: |
| `STIM` | stimulation-mapped sensory input population (7 annotation features) | 232 |
| `H1` | first-hop signed targets of `STIM`, excluding `STIM` | 607 |
| `H2` | second-hop signed targets, excluding `STIM` and `H1` | 3,576 |
| `DESC` | `super_class == descending` | 1,316 |
| `MOT` | `super_class == motor` | 805 |
| `ACT` | LEFT 185 + RIGHT 186 + JUMP 20 | 391 |
| `CUE` / `ACTN` | Phase 5 substrate cue and action populations (4 cues × 8, 4 × 1) | 32 / 4 |

**Recruitment code (declared, result-independent).** For any population of size
`n`, the count of active neurons in the readout window is coded into four
levels: `0` = zero spikes; `1` = 1 to ⌈n/100⌉; `2` = ⌈n/100⌉+1 to ⌈n/10⌉;
`3` = above ⌈n/10⌉. The edges come from the population size alone, so the code
cannot be chosen after seeing results. It reads as none / sparse / moderate /
broad recruitment.

### H1 — Sensory input to stimulated sensory-neuron activity

| Element | Definition |
| --- | --- |
| **Claim under test** | The declared stimulus code is reflected in the activity of the stimulated sensory population. |
| **Predictor** | `S`, a 4-level coarse stimulus code: entity {train, obstacle} × distance half split at the pooled archived median 0.653686. |
| **Response** | `R_STIM`, the recruitment code (4 levels) of `STIM` in `[50, 300)` ms. |
| **Table / N** | 4×4, floor 0.0097 bits at N = 672 |
| **Null** | `I(S; R_STIM) = 0`: the response distribution does not depend on stimulus identity. |
| **Alternative** | `I(S; R_STIM) > 0`: the response distribution differs across stimulus levels. |
| **Required observations** | Per trial: the stimulus identity and its encoded feature payload, stimulus onset and offset, every spike time and neuron index, the `STIM` spike count in the readout window. |
| **Controls** | NO_STIM (spontaneous rate), MATCHED_CHARGE (temporal concentration), SHUFFLED_MASK (identity vs charge), trial-level permutation null. |
| **Evidence needed to support** | Bias-corrected `I(S;R_STIM) > 0.05` bits, above the 95th percentile of the trial-level permutation null, with a trial-resampled bootstrap CI excluding zero, and with at least two observed levels in both variables. |
| **Would be inconclusive if** | `R_STIM` is constant across all trials (degenerate), or a stimulus level has fewer than 20 trials, or the cluster bootstrap cannot be formed because fewer than 20 trials are usable, or the two stimulus levels with the fewest distinct source events contribute more than half of the estimate. |
| **Stage** | R |

### H2 — Sensory-neuron activity to downstream first-hop populations

| Element | Definition |
| --- | --- |
| **Claim under test** | First-hop activity depends on the pattern of stimulated sensory activity, not merely on the presence of stimulation. |
| **Predictor** | `R_STIM`, 4-level recruitment code of `STIM`. |
| **Response** | `R_H1`, 4-level recruitment code of `H1` (607 neurons) in `[50, 300)` ms. |
| **Table / N** | 4×4, floor 0.0097 bits at N = 672 |
| **Null** | `I(R_STIM; R_H1) = 0`, and separately: the `H1` spike rate in REAL equals the rate in NO_STIM and MATCHED_CHARGE. |
| **Alternative** | `I(R_STIM; R_H1) > 0`, and the REAL downstream spike rate exceeds both controls. |
| **Required observations** | Per trial: `STIM` and `H1` per-neuron spike counts and spike times, first-hop peak synaptic current and peak membrane potential (optional diagnostics), and the stimulus identity. |
| **Controls** | NO_STIM; MATCHED_CHARGE; SHUFFLED_MASK; structural check that the first hop is defined only by signed edges, with the 662 signed edges of the annotation mapping reported. |
| **Evidence needed to support** | Both the information criterion of H1 applied to this table and the propagation criterion P2 of Section 6.2. Information without propagation, or propagation without information, is reported as a partial result. |
| **Would be inconclusive if** | `H1` is silent in every REAL trial (the pilot gate failed), or `H1` is active in NO_STIM at a rate that cannot be separated from REAL with N = 672, or the recruitment code has fewer than two observed levels. |
| **Stage** | P (presence), R (information) |

### H3 — Downstream activity to descending neurons

| Element | Definition |
| --- | --- |
| **Claim under test** | Descending-neuron activity depends on first-hop activity. |
| **Predictor** | `R_H1`, 4-level recruitment code of `H1`. |
| **Response** | `R_DESC`, 4-level recruitment code of `DESC` (1,316 neurons) in `[50, 300)` ms. |
| **Table / N** | 4×4, floor 0.0097 bits at N = 672 |
| **Null** | `I(R_H1; R_DESC) = 0`; `DESC` rate in REAL equals NO_STIM. |
| **Alternative** | `I(R_H1; R_DESC) > 0`; `DESC` rate in REAL exceeds NO_STIM. |
| **Required observations** | Per trial: `H1` and `DESC` per-neuron spike counts; descending peak membrane and current (optional); stimulus identity. |
| **Controls** | NO_STIM; MATCHED_CHARGE; the structural fact that only 9 of the 1,316 descending neurons are first-hop targets of `STIM` must be reported, because a null here is expected if propagation stops at the first hop. |
| **Evidence needed to support** | Corrected MI > 0.05 bits above the permutation q95 with CI excluding zero, and at least one descending spike in at least 15% of REAL trials (3 of 20 in the pilot, 100 of 672 in Stage R). |
| **Would be inconclusive if** | The pilot gate P2 fails, in which case H3 is declared **NOT TESTABLE** rather than negative; or fewer than 20 trials contain a descending spike. |
| **Stage** | P (gate), R (information) |

### H4 — Descending activity to motor-neuron populations

| Element | Definition |
| --- | --- |
| **Claim under test** | Motor-population activity depends on descending activity. |
| **Predictor** | `R_DESC`, 4-level recruitment code. |
| **Response** | `R_MOT`, 4-level recruitment code of `MOT` (805 neurons). |
| **Table / N** | 4×4, floor 0.0097 bits at N = 672 |
| **Null** | `I(R_DESC; R_MOT) = 0`; `MOT` rate in REAL equals NO_STIM. |
| **Alternative** | `I(R_DESC; R_MOT) > 0`; `MOT` rate in REAL exceeds NO_STIM. |
| **Required observations** | Per trial: `DESC` and `MOT` per-neuron spike counts; motor peak membrane and current (optional); LEFT/RIGHT/JUMP pool counts. |
| **Controls** | NO_STIM; MATCHED_CHARGE; the structural baseline that the annotation mapping has **zero** first-hop motor targets and only 4 motor neurons at two signed hops, which is why a null is the pre-declared expectation. |
| **Evidence needed to support** | Corrected MI > 0.05 bits above the permutation q95 with CI excluding zero, and at least one motor spike in at least 15% of REAL trials (3 of 20 in the pilot, 100 of 672 in Stage R). |
| **Would be inconclusive if** | Pilot gate P2 fails, in which case H4 is **NOT TESTABLE**; or no motor neuron spikes in any REAL trial, in which case the result is a bounded null (`< 1/672` trials with motor activity), not a test of information. |
| **Stage** | P (gate), R (information) |

### H5 — Neural population activity to decoder-mediated action

| Element | Definition |
| --- | --- |
| **Claim under test** | The decoder's per-window decision is a deterministic function of declared pool activity. This is a **consistency** claim about a decision rule, not a claim about motor control. |
| **Predictor** | `R_MOT`, 4-level recruitment code of `MOT`. |
| **Response** | `A`, 4-level decoder state: the last non-NEUTRAL state among the 50 ms windows in `[50, 300)` ms, else NEUTRAL. |
| **Table / N** | 4×4, floor 0.0097 bits at N = 672 |
| **Null** | `I(R_MOT; A) = 0`, which can only occur if the decoder gates are never met or the state never varies. |
| **Alternative** | `I(R_MOT; A) > 0`. Because the decoder reads the same spikes, a positive result is expected whenever the decoder fires at all. |
| **Required observations** | Per trial: every decoder window's start, end, raw score per pool, smoothed score, state, and the pool counts that produced it. |
| **Controls** | A **decoder-ablation baseline**: the same windows decoded with `activation_threshold` and `release_threshold` unchanged but with the decision applied to a **shuffled pool assignment** (seeded). The ablation must be run on the stored spikes after the fact and reported with the primary estimate. |
| **Evidence needed to support** | Nothing beyond a correctly labelled estimate. This endpoint can never support a motor-control or biological claim, because the decoder defines the mapping. Its only admissible interpretation is "the decision rule is internally consistent with pool activity". |
| **Would be inconclusive if** | Every window is NEUTRAL in every condition, which is the Phase 4H.4 outcome and would make the endpoint degenerate. |
| **Stage** | R |

### H6 — Neural activity and task outcome under fixed versus plastic weights

| Element | Definition |
| --- | --- |
| **Claim under test** | On the Phase 5 substrate, plastic training changes the neural code that carries cue identity relative to fixed weights. |
| **Substrate** | The Phase 5 synthetic 36-node task graph. **Not** the BANC connectome. No result from H6 may be transferred to H1–H5. |
| **Predictor** | `CUE`, 4 levels. |
| **Response** | `A_neural`, 5 levels: which of the four action neurons has the highest spike count in the evaluation episode, with a fifth level for "no action neuron spiked" and a declared tie rule (lowest action index). |
| **Table / N** | 4×5, floor 0.0014 bits at N = 6,400 rows; 40 independent seed clusters |
| **Null** | `I(CUE; A_neural)` is equal in `fixed_complete` and `plastic_complete`. |
| **Alternative** | The pooled `I(CUE; A_neural)` differs between conditions, in the direction of greater information after plasticity. |
| **Required observations** | Per episode: cue identity, every spike time and neuron index for the 36-node graph, per-neuron counts, the reward and prediction error, eligibility-trace summaries, the effective weight snapshot at checkpoint 160, the selected action and the task outcome. |
| **Controls** | Paired seeds; `eta = 0` reproduction of the fixed-weight spike hashes as an integrity check; the preserved Phase 5F success contrast must be reproduced before any H6 estimate is reported. |
| **Evidence needed to support** | The paired cluster-level difference in pooled MI has a bootstrap CI excluding zero and exceeds 0.05 bits in the predicted direction. A difference below 0.05 bits, or a CI containing zero, is reported as **no detectable neural-level change**, which extends the Phase 6C C-06 negative result rather than contradicting it. |
| **Would be inconclusive if** | The Phase 5F +0.150 success difference is not reproduced in the seed-paired design; or the per-seed action code is degenerate for more than 20% of seeds; or the row-level and cluster-level analyses disagree in sign. |
| **Stage** | S |

## 4. Recording strategy

### 4.1 The two options, stated plainly

| | **A. Instrumented simulation recording** | **B. Biological neural recording** |
| --- | --- | --- |
| What is measured | Per-trial spike times, neuron indices, and a declared diagnostic panel of membrane potentials and synaptic currents, produced by the existing BANC simulator on the BANC graph, or by `PlasticSimulator` on the Phase 5 substrate. | Extracellular or intracellular recordings from a living animal, paired with stimulus presentation and behavioural readout. |
| What it can establish | Internal computational information flow: given the declared model and the declared stimulus, does information about the stimulus reach downstream populations, and does it reach the decoder? | Whether the same flow exists in the animal. |
| What it cannot establish | Biological validity of any kind. A simulated spike is a numeric event in a LIF model, not a measurement of a neuron. | Anything about this simulator, except by analogy. |
| Cost | Hours of CPU; ~0.35 GB of mandatory storage (≈1.1 GB with optional panel diagnostics); no new hardware. | Animal ethics approval, surgical preparation, recording hardware, months of calendar time, and a species and preparation choice that nothing in this project has established. |
| Dependencies | A `experiments/phase_6d/` instrumentation layer (not yet written) and the pilot gate in §6. | None of the project's existing code is reusable; the whole pipeline would be new. |

### 4.2 Decision: Option A, for a stated and limited purpose

The experiment proposed here is **Option A**. It is not a substitute for B, and no result from it will be described as a biological finding. The reason A is the correct next step is that the Phase 6B and 6C analyses are missing *simulated* neural-level data, not missing *biological* data. The archive already contains the model's inputs, its graph, its weights and its decoder outputs; what it does not contain is the per-trial spike trains between the input and the decoder. Option A fills exactly that gap. Option B would answer a different and much larger question, and there is no basis in Phases 4H–6C for choosing a preparation, a brain region, or a stimulus protocol that would make such a recording interpretable.

The distinction matters for how the results will be worded. A positive Stage R result means: *within this declared model, information about the stimulus reached the descending population at a magnitude distinguishable from the tested controls.* It does **not** mean the fly's descending neurons carry that information. A decoder output means: *the decision rule fired.* It does not mean the animal moved.

### 4.3 Why simulation still cannot settle the biological question

Four specific gaps separate an A result from a B claim, and none of them can be closed by more simulation:

1. **Neuron model fidelity.** `LIFPopulation` is a single-compartment leaky integrate-and-fire model with fixed parameters for all 172,433 nodes. It has no dendritic geometry, no cell-type-specific conductances, and no adaptation. A spike threshold crossing in this model is a modelling decision, not a measured event.
2. **Synapse sign and weight provenance.** Signs come from `banc_synapse_policy`, which assigns a sign to 683,100 of 1,535,710 edges (44.48%) using a rule, not a measurement of transmitter identity on those specific synapses. Unassigned edges do not transmit at all in the model.
3. **Stimulation plausibility.** The drive is an injected current in picoamperes applied to a mapped set of 232 sensory neurons. Nothing in the project establishes that this current profile resembles what those neurons would receive from a real sensory organ.
4. **Decoder authority.** The motor decoder is a hand-written threshold rule over three named pools. A "decision" it emits is a statement about that rule, not about the fly's motor programme, and the project has no validated motor command (PF-4H-4).

### 4.4 The blocking dependency, and why the pilot comes first

Phase 6A declared the analysis that would use per-trial recordings infeasible because the archived 4H runs produced zero downstream events. Recording more trials does not fix that: if the drive never propagates, a larger sample only estimates information about an all-zero downstream response, which is degenerate and must be reported as inconclusive, not as a negative. The pilot in §6 is therefore a **gate**, not a preliminary. Its purpose is to establish that the readout channels carry non-zero, stimulus-coupled variation before 2,688 campaign runs and 19,200 Phase 5 episodes are committed. If the gate fails, the campaign does not run and the correct outcome is a documented stop with the Phase 4H/4H.5 conclusion left intact.

## 5. Recording schema

### 5.1 Per-trial record

One record per simulated trial. Every field below is written for every Stage R trial and every Stage S episode; Stage P writes the same record with `stage = "P"`. Fields marked **mandatory** are required for the trial to enter any analysis; a trial missing a mandatory field is excluded and counted in the missing-data table (§9.9), never silently dropped.

| # | Field | Type | Status | Source and exact provenance |
| --- | --- | --- | --- | --- |
| 1 | `trial_id` | string | mandatory | Assigned by `experiments/phase_6d/trial_schedule.py`; stable sort key. |
| 2 | `stage` | enum `P`,`R`,`S` | mandatory | Written by the runner. |
| 3 | `random_seed` | int | mandatory | Passed to `BancSimulator(seed=...)`; feeds `np.random.default_rng(seed)` for noise only. |
| 4 | `condition` | enum | mandatory | `REAL`, `SHUFFLED_MASK`, `MATCHED_CHARGE`, `NO_STIM`, and in Stage P `DIRECT_INJECTION` and `SINGLE_H1_SPIKE`; Stage S `fixed_complete`, `plastic_complete`. |
| 5 | `connectome_identity` | object | mandatory | `{"name":"banc_v888","graph_sha256":"6d47f259...e2192","node_sha256":"144a2eb0...3e5f","n_nodes":172433,"n_edges":1535710}`. Full digests: graph `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192`, nodes `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f`. |
| 6 | `threshold` | int | mandatory | 5. Read from `graph.threshold`; written, not inferred. |
| 7 | `root_ids` | int32 array | mandatory | `graph.root_ids` for every neuron touched by the trial (stimulated ∪ panel ∪ any spiking neuron); full list stored once per file, indexed by local index. |
| 8 | `population_labels` | uint8 array | mandatory | One label per local index: stimulated / first-hop / second-hop / descending / motor / other. Derived from `BancSensoryMapping` and the Phase 4H classification, not re-derived per run. |
| 9 | `stimulus_identity` | object | mandatory | For `REAL`: source event index in `phase_3b2c_real_sequence_replay.json`, `class`, `entity`, `time_ms`, `feature_values`. For synthetic conditions: the derived level and the rule that produced it. |
| 10 | `stimulus_onset_ms`, `stimulus_offset_ms` | float | mandatory | 50.0 and 150.0 ms for Stage R. |
| 11 | `spike_times_ms` | float32 array | mandatory | `SpikeRecorder.spike_times_ms`. Existing production API; one value per spike. |
| 12 | `spike_neuron_indices` | int32 array | mandatory | `SpikeRecorder.spike_neuron_indices`, parallel to field 11. |
| 13 | `n_neurons` | int | mandatory | `graph.n_nodes`. |
| 14 | `spike_counts` | int32 array, length = recorded node set | mandatory | `SpikeRecorder.spike_counts()` restricted to the recorded set. Sparse: only for nodes that appear in fields 7–8. |
| 15 | `population_counts` | int32 array, length ≤ 7 | mandatory | Spike counts summed over each population label, per 10 ms bin and whole-trial. |
| 16 | `binned_activity` | float32, shape `(n_populations, n_bins)` | mandatory | 10 ms bins over `[0, 300)` → 30 bins × 7 populations = 210 values. **Population-level only**; no neuron × bin matrix in the mandatory file. |
| 17 | `decoder_windows` | JSON array | mandatory | `BancActivityAdapter.decode` → `MotorDecoder.decode_recorder` → `ActionDecision.as_dict()`: `window_start_ms`, `window_end_ms`, `decoded_state`, `primary_action`, `active_actions`, `neutral`, `reason`, `raw_scores`, `scores`, `lateralization`. Per-pool evidence is nested, not flattened. |
| 18 | `task_outcome` | object | Stage S mandatory, Stage R `null` | Selected action, correct/incorrect, reward, prediction error. BANC has no task; `null` is written explicitly, not omitted. |
| 19 | `reward`, `prediction_error` | float | Stage S mandatory, Stage R `null` | `PlasticSimulator` `step_callback` return value and `update_reports` entries. |
| 20 | `plasticity_traces` | sparse object | Stage S mandatory, Stage R explicit `null` | `EligibilityStore.state_dict()` summary at checkpoint: number of active edges, sparsity fraction, per-feature aggregate. **No dense edge × time array.** Placing these seven independent fields in one file keeps them atomic; it does not imply that BANC supports plasticity. |
| 21 | `effective_weights` | sparse object | Stage S mandatory | `WeightState` digest plus `effective_magnitude` for plastic positions only (max 32 edges on the 36-node substrate); the full snapshot is written once per checkpoint, not per trial. |
| 22 | `config_hash` | string | mandatory | SHA-256 of the resolved condition + decoder + neuron-parameter mapping for the trial. |
| 23 | `software_version` | object | mandatory | `{"python":..., "numpy":..., "commit":..., "phase_6d_code_sha256":...}`. |
| 24 | `provenance` | object | mandatory | Runner script path, wall-clock start/end, host identifier, and the SHA-256 of the dependency files (`banc_graph.npz`, `banc_nodes.parquet`, the stimulus archive) read for the trial. |

### 5.2 Optional diagnostics, and what is actually available

These fields are **not** in the mandatory record. They are collected only for the declared diagnostic panel and only if the panel size is fixed before the campaign.

| # | Field | Availability, verified | Notes |
| --- | --- | --- | --- |
| O1 | `membrane_potential_mv` trajectory | **Available in memory only.** `LIFPopulation.membrane_potential` returns `self._V`, a live `float64` array of length 172,433. There is no production API that writes a trajectory. | Recording the full population for 600 steps costs 172,433 × 600 × 8 B ≈ 828 MB per run before compression, and Phase 6A measured ≈4.55 GB per 3.3 s run. Rejected. |
| O2 | Panel `membrane_potential_mv` | Available through the same property, subsampled. | Panel = the 232 stimulated + up to 200 first-hop + 20 descending + 6 pool neurons = ≤ 458 nodes. At 2 ms sampling over 300 ms: 458 × 150 × 4 B ≈ 275 kB per trial, ≈ 740 MB for Stage R. Optional. |
| O3 | `synaptic_current_pa` (exc, inh, net) | Available as properties of `BancSignedSynapses`. `synaptic_current_pa = exc − inh`. | Same panel and cost as O2. Currents are per-neuron aggregate, not per-synapse; no edge-resolved current is recorded. |
| O4 | `last_active_edges` | Exists on the synapse object during a step but is overwritten each step. | If needed, the wrapper can accumulate a sparse edge set. Not in the mandatory schema. |
| O5 | `spike_hash` | `spike_hash(result.recorder)` from `experiments/phase_4h/common.py`. | Mandatory in practice: every trial stores it and the campaign asserts it against a re-run of a 5% sample. |

Two consequences follow. First, spike trains are a supported production output and need no wrapper. Second, membrane potentials and synaptic currents are readable per step but only through an instance-level hook, and only for a small panel. The schema therefore records them as optional diagnostics and the mandatory record stays sparse. **No N × N matrix in any form is written**; population activity is aggregated to ≤ 7 rows × 30 bins.

### 5.3 Volume: anchored in the archived runs

The archived Phase 4H runs are the only measured anchor. Over the nine 300 ms diagnostic runs in `sensory_roundtrip.diagnostics.v2.checkpoint.jsonl`, spike totals were 0, 1,873–3,760, and 3,562 in the 3562-spike case; only stimulated neurons fired, so this is a **lower** bound for a propagating campaign. A propagating run adds first-hop (607), second-hop (3,576) and descending (1,316) activity that the archive never contained.

| Quantity | Value | Derivation |
| --- | --- | --- |
| Spikes per trial, planning value | 15,000 | Between the 3,562 observed maximum and a 10% second-hop recruitment at 20 spikes per 300 ms |
| Bytes per spike | 8 | float32 time + int32 index |
| Spike payload per trial | 120 kB | 15,000 × 8 B |
| Metadata, binned activity, decoder windows, IDs per trial | ≈15 kB | Fields 7–10, 15–18, 22–24 |
| **Mandatory bytes per trial** | **≈135 kB** | |
| **Mandatory Stage R total** | **≈363 MB** | 2,688 × 135 kB |
| Optional O2+O3 panel per trial | ≈550 kB | 458 nodes × 150 samples × 2 signals × 4 B |
| **Total with optional diagnostics** | **≈1.8 GB** | 2,688 × (135 + 550) kB |
| Hard storage budget | 2.0 GB | Runner stops and reports if exceeded rather than degrading silently |

The optional-diagnostics figure in this table (≈1.8 GB) is larger than the 1.1 GB quoted in the executive summary because O2 and O3 are counted together here and only O2 there. If optional diagnostics are enabled, the stricter 1.8 GB number governs.

### 5.4 Storage formats and trade-offs

| Format | Suitability | Trade-offs |
| --- | --- | --- |
| **Per-trial `.npz`, uncompressed, plus a JSONL manifest** | **Recommended.** Matches the existing `SpikeRecorder.save` convention (fields `spike_times_ms`, `spike_neuron_indices`, `n_neurons`, `duration_ms`, `capacity`). | 2,688 small files; needs a manifest to avoid directory scans; uncompressed files are `mmap`-able and re-read quickly at analysis time. Resumability is trivial: a trial present in the manifest is skipped. |
| Consolidated `.npz` per condition with CSR-style `spike_offsets` | Good for final analysis, poor for writing. | One file per condition is fast to load, but any resumed or failed trial forces a rewrite of the whole array, and a crash loses the condition. Use it only as a post-campaign compaction step. |
| HDF5 / Zarr | Technically the best fit for ragged spike trains. | Neither `h5py` nor `zarr` is installed, and adding a dependency is out of scope for a design-only phase. Rejected. |
| Parquet | Excellent for the tabular per-trial summary (fields 1–6, 15, 19, 22–24). | Not suited to ragged spike arrays. Recommended **in addition** to npz for the summary table, because `pandas` and `pyarrow` are already available. |
| One JSON per trial | Simple and human-readable. | JSON floats inflate a 120 kB spike payload to several hundred kB and lose exact float32 bit patterns. Rejected for spikes; retained for metadata. |

**Dense formats are excluded by design.** No `n_neurons × n_time_bins` matrix is written, in any format, for either the full graph or a population panel. The largest array in the mandatory record is `(7 populations, 30 bins)`.

### 5.5 Determinism and integrity fields

Every trial stores `spike_hash` (O5), `config_hash`, `software_version` and `provenance`. The campaign re-runs a random 5% of trials in a separate process and asserts that `spike_hash` reproduces bit-for-bit. A mismatch invalidates the affected condition until explained; it is not overridden by dropping the trial. `max_recorded_spikes` is set per trial to 500,000 (4 MB), which is 33× the planning value and triggers `SpikeCapacityExceeded` rather than silent truncation if propagation is far denser than expected.

## 6. Experimental conditions

### 6.1 What the conditions must be able to separate

The condition set is built around six distinctions. Each condition below earns its place by separating exactly one of them; conditions that separate none, or that were already answered by Phase 4H.1–4H.4, are not repeated.

| Distinction | Separated by |
| --- | --- |
| Stimulated neurons respond to the drive | `REAL` at `d*` versus `NO_STIM` (both with identical noise and seed set) |
| The response propagates beyond the stimulated set | `REAL` versus `SHUFFLED_MASK` versus `MATCHED_CHARGE`, read at H1/H2/DESC |
| Downstream activity is not coincidental | `NO_STIM` and `MATCHED_CHARGE` false-positive rates |
| The response carries stimulus-specific information | MI of the 4-level stimulus code with H1/H2/DESC responses, against shuffled-label nulls |
| The stimulus selects an action through the decoder | Decoder windows in `REAL` versus all three controls |
| Plasticity changes the neural code | Stage S `fixed_complete` versus `plastic_complete`, paired by seed |

### 6.2 Stage P — propagation-positive pilot (gate)

Stage P is run first and is the only stage whose failure stops the programme.

| Element | Value |
| --- | --- |
| Conditions | `REAL`, `NO_STIM`, `MATCHED_CHARGE` |
| Drive series | 200, 400, 800, 1200 pA per stimulated neuron, applied through `BancEventDrive` with `pulse_gain = 1.0` (not the Phase 3C 0.5, so the injected current is the nominal value) |
| Design | 3 conditions × 4 drives × 20 trials = 240 runs |
| Positive control | 80 runs: direct current injection into the first-hop set (not through the sensory encoder) at the same 4 drives × 20 trials. This is the 4H.5 recommendation and it separates "the sensory drive is too weak" from "the synapse does not transmit". |
| Single-first-hop-spike test | 4 runs: inject a calibrated current into one first-hop neuron chosen by the declared rule (lowest local index that receives ≥ 99% of the maximum first-hop current in 4H.4) and step the amplitude until it emits exactly one spike; record whether any H2 neuron spikes within 5 ms. This tests transmission per spike rather than transmission per drive. |
| Trial length | 300 ms, onset 50 ms, offset 150 ms, readout `[50, 300)` ms |
| Noise / background | `noise_std_pa = 50.0`, `background_current_pa = 0.0`, both identical across conditions and matched by seed |
| Total | 324 runs, ≈14 min at 2.54 s/run |

Twenty trials per cell, not ten: the exact operating characteristics of the gates below require it. At n = 20 per group, a one-sided Fisher test of 50% versus 5% has power 0.80 at α = 0.01; at n = 10 the same test has power 0.28, which would make P1 a coin flip.

**Gates, evaluated in order and without substitution.**

| Gate | Pass condition | If it fails |
| --- | --- | --- |
| **P0 — integrity** | All 324 records complete every mandatory field; the 5% re-run reproduces `spike_hash`; no `SpikeCapacityExceeded`; all membrane arrays finite. | Stop. The instrumentation is not trustworthy and no scientific conclusion follows. |
| **P1 — first-hop spiking** | At some drive `d`, at least 10 of 20 `REAL` trials have ≥ 1 spike in H1, `NO_STIM` and `MATCHED_CHARGE` each have ≤ 1 of 20, and the one-sided Fisher exact test of `REAL` versus the pooled controls gives p < 0.01. `d*` is the **lowest** drive meeting this, fixed before looking at H2 or the decoder. | If no drive up to 1200 pA meets P1 and the direct-injection positive control also fails, **stop**: the simulated tissue does not spike under any tested drive and Phase 6D must not proceed. If `DIRECT_INJECTION` at 400 pA or above produces H1 spiking while `REAL` does not, report a drive/encoder failure and stop; do not raise the drive post hoc. |
| **P2 — propagation-positive (mandatory)** | At `d*`, at least **3 of 20** `REAL` trials have ≥ 1 spike in H2 ∪ DESC, and **0 of 40** control trials (`NO_STIM` + `MATCHED_CHARGE`, 20 each) has any downstream spike. | **Stop.** This is the gate the whole phase exists to satisfy. A failed P2 reproduces the Phase 4H.4/4H.5 negative finding at higher drive and must be written up as such; the Stage R campaign and all Phase 6D MI analyses are cancelled, not postponed. |
| **P3 — decoder reachability** | At `d*`, at least one post-stimulus decoder window in `REAL` is non-NEUTRAL, and no control window is non-NEUTRAL. | Not fatal. If P3 fails but P1 and P2 pass, H5 is declared untestable and removed from the confirmatory family; H1–H3 proceed. This is the expected Phase 4H.4 outcome and is recorded as a limitation, not a failure of the campaign. |

P2 is a **screen, not a hypothesis test**, and no p-value is attached to it. With controls expected to be exactly zero (Phase 4H.4 produced zero non-stimulated spikes in every control), a Fisher test against 0% is degenerate. Its operating characteristics are therefore stated directly: the probability of passing when the true per-trial propagation rate is 20% is 0.79; at 30% it is 0.97; at 5% it is 0.075. A miss at a true rate near 20% is a known cost of not spending more compute, and it is the reason P2's failure is reported as "no propagation detected under this design" rather than "propagation absent".

The gate order matters: `d*` is fixed at P1, before any downstream or decoder result is examined. This prevents selecting a drive that happens to maximise a downstream effect.

### 6.3 Stage R — condition matrix

Stage R runs only if P0–P2 pass. All conditions share the same 300 ms trial, the same seed list, the same noise draw schedule and the same decoder configuration; they differ **only** in the drive.

| ID | Condition | Drive | Purpose | n |
| --- | --- | --- | --- | --- |
| R1 | `REAL` | One archived feature-carrying event per trial, encoded by the unchanged `population_encoder`, at `d*` | The measurement of interest | 672 |
| R2 | `SHUFFLED_MASK` | Same events and timing, feature→population identity permuted by `shuffle_feature_identities` with a recorded permutation seed | Removes the specific feature-to-neuron mapping while preserving per-event timing and charge; tests whether any downstream response is feature-specific rather than generic | 672 |
| R3 | `MATCHED_CHARGE` | Constant total charge equal to the mean `REAL` charge at `d*`, delivered uniformly over the stimulated set (`ConstantChargeDrive`) | Controls for total current; a response that survives only `REAL` is not a charge artefact | 672 |
| R4 | `NO_STIM` | No events; identical noise | Spontaneous baseline and the false-positive rate for every downstream endpoint | 672 |
| **Total** | | | | **2,688** |

Two further features apply to all four rows rather than adding rows: each trial re-uses the same seed across conditions (a paired design at the noise level), and 134 trials (5%) are re-run in a separate process as the determinism check.

### 6.4 Stimulus code

The primary predictor is a **4-level stimulus code** built from the archived corpus, because only 43 of the 215 events in `phase_3b2c_real_sequence_replay.json` carry `feature_values` and `BancEventDrive` skips events with an empty payload. The code is the cross of entity and distance half at the pooled median:

| Level | Rule | Distinct archived events |
| --- | --- | --- |
| `TRAIN_NEAR` | entity = train, distance ≤ 0.653686 | 20 |
| `TRAIN_FAR` | entity = train, distance > 0.653686 | 15 |
| `OBST_NEAR` | entity = obstacle, distance ≤ 0.653686 | 2 |
| `OBST_FAR` | entity = obstacle, distance > 0.653686 | 6 |

Each level receives 168 trials (`REAL`, `SHUFFLED_MASK`, `MATCHED_CHARGE`) or 168 `NO_STIM` trials as its matched baseline. Event identity within a level is assigned by a declared round-robin rule from the sorted event list, so the design is fixed before any simulation. The consequence is stated plainly: `OBST_NEAR` has only 2 distinct events and will repeat them 84 times each, so a significant `OBST_NEAR` effect describes **those two events**, not obstacle proximity in general.

The wider 6-level code (entity × distance tertile) is retained as the **binding sample-size constraint** even though it is not the primary test: its estimator bias floor is the largest of the declared tables, and N is set so that floor stays below the MDE (§8).

### 6.5 Historical conditions deliberately not repeated

| Historical condition | Why it is not repeated here |
| --- | --- |
| `E_random_matched_mapping` (Phase 4H.4) | It tests whether the specific mapping matters; H1–H3 test whether *any* information reaches downstream under the declared mapping. The random-mapping question is descriptive and already answered. |
| Weight sensitivity sweep (Phase 4H.3) | It established that propagation is weight- and sign-dependent. Repeating it would not add a confirmatory endpoint and would multiply the run count. |
| Threshold / population sensitivity (Phase 4H.2) | Threshold 5 is fixed by the BANC artifact and the graph hash. A threshold sweep changes the object under study; it belongs in a separate sensitivity phase, not in a confirmatory campaign. |
| `C_temporal_shuffle` full sweep | `SHUFFLED_MASK` already breaks the feature mapping while preserving timing; the temporal shuffle is reduced to the 3 descriptive `STREAM_CHECK` runs. |
| `fixed_random` / `plastic_random` | Phase 5F answered the complete-versus-random wiring question. Stage S tests fixed versus plastic on the **complete** substrate only. |
| `CORRECT_MAPPING` with reward | The task substrate in Stage S is the only substrate with a reward. BANC has none (field 18 is `null`). |

### 6.6 Stage S — fixed versus plastic, on the Phase 5 substrate

Stage S is a separate substrate and is not Stage R with different weights. It runs on the 36-node synthetic task graph because BANC has no reward signal, no task loop, and no established use of `PlasticSimulator` on its 1.5 M-edge graph. No estimate from Stage S is pooled with or compared to a Stage R estimate.

| Element | Value |
| --- | --- |
| Substrate | Phase 5 task graph: `TaskConfig(n_cues=4, cue_neurons=8, action_neurons=1)`, 36 nodes |
| Conditions | `fixed_complete`, `plastic_complete` (complete wiring, as in Phase 5F) |
| Seeds | 40 (Phase 5F used 10; this stage quadruples the seed count) |
| Episodes per seed × condition | 160 training + 80 evaluation = 240 |
| Total episodes | 40 × 2 × 240 = **19,200** |
| Rows in the H6 table | 40 × 2 × 80 evaluation episodes = **6,400** |
| Independent clusters | 40 seeds |
| Plasticity | `eta = 1.0`, checkpoint 160 for weights and traces; evaluation recorded at `eta = 0` after the checkpoint so the evaluation itself does not change weights |
| Reward / prediction error | `RewardProvider` and the Phase 5B RPE; field 19 is mandatory here |
| Integrity checks | Paired seeds; `eta = 0` reproduces fixed-weight spike hashes; the Phase 5F success contrast must reappear before any H6 estimate is reported |
| Runtime | Phase 5 episodes are sub-second; 19,200 episodes is estimated at 20–40 min, wall-clock bounded by the runner's checkpointing |

The `fixed_complete` condition is not literally "no plasticity": it is the Phase 5F fixed-weight control with the same substrate, seed list and evaluation protocol. Using the same seed list across both conditions is what makes the cluster-level paired analysis in §9 possible.

### 6.7 Condition count and run budget

| Stage | Runs | Wall time at measured rates | Depends on |
| --- | ---: | --- | --- |
| P | 324 | ≈14 min | nothing |
| R | 2,688 + 134 repeats | ≈2.0 h | P0–P2 pass; `d*` fixed at P1 |
| S | 19,200 episodes | ≈20–40 min | Phase 5F contrast reproduced |
| A | 0 | ≈30 min of analysis | P0–P3 and R complete |
| **Total** | **3,146 runs + 19,200 episodes** | **≈3 h** | |

## 7. Controls

### 7.1 Control set

Each control exists to cancel one named alternative explanation. A control that cancels nothing is not included.

| ID | Control | Implementation | Alternative it rules out | If the control fails |
| --- | --- | --- | --- | --- |
| C1 | **Spontaneous baseline** | `NO_STIM`: identical seeds, noise draw and background as `REAL`, no stimulus schedule | That downstream spikes are spontaneous rather than stimulus-locked | Baseline is non-zero: report the false-positive rate and require `REAL` to exceed it by the pre-registered margin before any propagation claim. |
| C2 | **Matched charge** | `MATCHED_CHARGE`: total charge equal to mean `REAL` charge at `d*`, uniform over the stimulated set | That any downstream response is driven by total current rather than by its pattern | If `MATCHED_CHARGE` propagates like `REAL`, H2's specificity claim is not supported; report a charge-driven result. |
| C3 | **Shuffled feature identity** | `SHUFFLED_MASK` via `shuffle_feature_identities` with a recorded permutation seed | That downstream activity is generic arousal to any sensory input | If `SHUFFLED_MASK` propagates like `REAL`, propagation is not feature-specific; H2 and H3 become descriptive only. |
| C4 | **Direct first-hop injection (positive)** | `DIRECT_INJECTION`: current injected into H1 neurons, bypassing the sensory encoder, 4 drives × 10 trials | That a null propagation result is caused by the sensory drive rather than by the H1→H2 synapse | If the positive control also fails to reach H2, report a transmission failure at the synapse and stop. If it succeeds while `REAL` fails, report a drive/encoder failure. |
| C5 | **Single first-hop spike (positive)** | `SINGLE_H1_SPIKE`: one H1 neuron driven to exactly one spike, then a 5 ms search for H2 spikes | That propagation requires many simultaneous H1 spikes by construction of the LIF model | Calibrates the minimum H1 event that transmits. A null is informative, not fatal, and is reported with the drive series. |
| C6 | **Fixed-weight paired condition** | Stage S `fixed_complete` with the same seed list as `plastic_complete` | That any Stage S neural difference is caused by plasticity rather than by seed or protocol | If the Phase 5F success contrast does not reappear, H6 is declared inconclusive before any MI is computed. |
| C7 | **`eta = 0` reproduction** | Stage S reruns the trained run with the learning rate set to zero at the checkpoint and compares spike hashes | That stored evaluation traces were altered by the evaluation itself | Hash mismatch invalidates the seed; the seed is reported and excluded only if the cause is identified. |
| C8 | **Archive replay** | Re-run the archived 4H condition B event stream and assert the recorded `spike_sha256` (`spike_hash` from `experiments/phase_4h/common.py`) | That the new instrumentation changed the simulator's behaviour | Mismatch means the wrapper altered the simulation; the entire campaign is invalid until reconciled. |
| C9 | **Decoder neutrality in controls** | Assert that no control trial produces a non-NEUTRAL decoder window | That the decoder fires on noise or on uniform charge | A control fires: report the decoder's false-positive windows and exclude the decoder endpoint from confirmatory claims. |
| C10 | **Label permutation null** | Trial-level permutation of the stimulus code, 5,000 draws, recomputing the same estimator | That observed MI is expected from the marginal distributions alone | Reported as part of every MI estimate; no separate pass/fail. |
| C11 | **Seed-pair reproducibility** | Split the 40 seeds into two halves of 20 and estimate every endpoint in each half | That an effect is carried by a small number of seeds | Sign disagreement between halves is reported as instability; the endpoint is not declared confirmatory. |
| C12 | **Blinded analysis** | The analysis reads condition codes as opaque hashes and maps them to labels only after every endpoint is frozen and written to disk | Analyst degrees of freedom in choosing which comparison to report | Any post hoc change to the mapping invalidates the pre-registration and is disclosed in the report. |
| C13 | **Decoder ablation** | Re-decode the stored spikes of every trial with a seeded permutation of which neuron belongs to which action pool, thresholds unchanged, and report the primary H5 estimate alongside the ablated one | That `I(pool activity; decision)` reflects something other than the decoder's own wiring | An ablated estimate as large as the primary one shows the H5 endpoint is a property of the rule, not of the pool assignment. |

### 7.2 Two controls the design cannot provide

1. **No biological ground truth.** There is no recorded animal response against which a simulated downstream response could be validated. C1–C5 establish that a pattern is not an artefact of the simulator's inputs or noise; they cannot establish that the pattern resembles anything in a fly.
2. **No independent implementation.** The simulator, the encoder and the decoder are all this project's code. A second implementation would catch coding errors; the design does not include one, and reproducibility (C11, C8) only catches non-determinism, not a shared conceptual mistake.

Both are recorded as limitations in §12 and are the reason no Stage R result can be promoted beyond evidence grade E1–E2 in the Phase 4H.5 scale.

## 8. Sample-size justification

### 8.1 What counts as an independent unit

The design has three nested levels, and the analysis never substitutes a lower level for a higher one.

| Level | Count in Stage R | Count in Stage S | Valid as n for | Not valid for |
| --- | ---: | ---: | --- | --- |
| **Seed** (one stochastic simulation run) | 2,688 unique seeds | 40 | Reproducibility, Stage S cluster inference | — |
| **Trial** (one 300 ms simulation) | 2,688 | 19,200 episodes | Stimulus-locked response comparisons (H1), trial-level permutation | Generalisation beyond the 43 archived events |
| **Stimulus event** | 43 distinct events (2 / 6 / 15 / 20 per level) | 4 cues | Generalisation of H2 and H3 to the stimulus corpus | Nothing larger — 43 is the whole corpus |
| **Neuron** | 232–5,731 in the declared sets | 36 | Descriptive only | **Never** an independent replicate |
| **Time bin** | 30 (10 ms) | — | Descriptive only | **Never** an independent replicate |
| **Spike** | ≈15,000 per trial | varies | Descriptive only | **Never** an independent replicate |

The consequence is explicit: a p-value computed with `n = number of spikes` or `n = number of neurons` is not computed anywhere in this protocol. Where a response is binned, the bin is a summary of a trial, and the trial is the unit.

### 8.2 N is set by the estimator's bias floor, not by convenience

The plug-in MI of a `kx × ky` table with N rows is biased upward by approximately

```
bias ≈ (kx − 1)(ky − 1) / (2 N ln 2)      bits
```

`information.bias_correction` implements this floor and `required_sample_size` solves it for N. The design criterion is that the worst-case floor across all declared tables must be at most one third of the declared MDE of 0.05 bits, i.e. ≤ 0.0167 bits.

| Table | df = (kx−1)(ky−1) | N for floor ≤ 0.017 | Floor at N = 672 | Floor at N = 6,400 |
| --- | ---: | ---: | ---: | ---: |
| 4×4 primary (stimulus level × H1 recruitment) | 9 | 382 | 0.009661 | 0.001014 |
| 4×3 (stimulus level × H2/DESC recruitment) | 6 | 255 | 0.006441 | 0.000676 |
| 4×5 (Stage S cue × action neural code) | 12 | 510 | 0.012881 | **0.001353** |
| **6×4 sensitivity (binding constraint)** | **15** | **637** | **0.016102** | 0.001691 |

The binding constraint is the 6×4 sensitivity table. Solving `15 / (2 N ln 2) ≤ 0.0167` gives N ≥ 648. The smallest N that is a multiple of both 4 and 6, and therefore gives an integer number of trials per cell in both the 4-level primary and 6-level sensitivity tables, is **672**. That yields 168 trials per primary stimulus level, 112 per sensitivity level, and a worst-case floor of 0.0161 bits — 32% of the MDE.

In the earlier Phase 5F/6C work the 4×4 table rested on 40 evaluation episodes per condition, giving a floor of 0.162 bits, more than three times the MDE. **That sample is not reused as evidence of adequate power, and no Phase 6D estimate will be computed from it.** Stage S uses 6,400 rows, which reduces the 4×5 floor to 0.00135 bits.

### 8.3 Power for the confirmatory MI endpoints

Under independence, `2 N ln2 · Î` is asymptotically χ² with `df = (kx−1)(ky−1)` degrees of freedom, so the standard deviation of the plug-in estimate at N = 672 is `sqrt(2·df) / (2 N ln2)` = 0.004554 bits for the 4×4 table and 0.005880 bits for the 6×4 table. The declared MDE of 0.05 bits is 11.0 and 8.5 standard deviations respectively, so power at α = 0.01 is effectively 1.0. The MDE is deliberately conservative; the smallest effect detectable with 80% power is about 0.013 bits (4×4) and 0.016 bits (6×4), still far above the bias floor.

The estimates are not independent of the bias correction: the reported value is `max(0, Î − floor)`, and its uncertainty is dominated by the raw estimator's standard error. The analysis therefore reports the raw estimate, the floor, the corrected value, and a cluster bootstrap CI on the corrected value, rather than a single number.

### 8.4 Power for the Stage P gates

Exact binomial and Fisher calculations, not simulation:

| Gate | Comparison | n per group | True rates | α | Power |
| --- | --- | ---: | --- | ---: | ---: |
| P1 | 50% vs 5%, one-sided Fisher | 20 | 0.50 vs 0.05 | 0.01 | **0.803** |
| P1 | same, at n = 10 (rejected) | 10 | 0.50 vs 0.05 | 0.01 | 0.281 |
| P2 screen | ≥3 of 20 positive | 20 | q = 0.20 | — | **0.794** |
| P2 screen | ≥3 of 20 positive | 20 | q = 0.30 | — | **0.965** |
| P2 screen | ≥3 of 20 positive | 20 | q = 0.05 | — | 0.075 |

This is why Stage P uses 20 trials per cell rather than 10: at 10 the P1 gate would have 28% power and would frequently stop a programme that should continue.

### 8.5 Multiple comparisons and p-value resolution

The confirmatory family is fixed by the gates, not by the results: E1–E3 and E6–E7 are evaluated if P1–P2 pass; E10 is evaluated if Stage S reproduces the Phase 5F contrast; E4, E5 and E8 are evaluated if P3 passes. The largest possible family is 10 endpoints, so Holm–Bonferroni at α = 0.05 requires a smallest p of 0.005. The permutation null uses 5,000 draws at the trial level, giving a p-value floor of 1/5001 = 0.0002, comfortably below 0.005. Endpoints not unlocked by a gate are reported as **not evaluated**, never as non-significant.

### 8.6 Minimum support, clustering and degenerate variables

- **Minimum support.** An MI estimate is computed only if every level of both variables has at least 20 rows. A level below 20 is collapsed with its declared neighbour (fixed rule, written before the campaign) or the endpoint is declared **not estimable**. At N = 672 and four levels, the expected 168 rows per level makes this a guard rather than a routine event.
- **Trial-level vs event-level inference.** Trial-level permutation tests the stimulus-locked response and is valid because each trial has its own seed. Generalisation to the stimulus corpus is bounded by the 43 events, so H2 and H3 additionally report an **event-cluster bootstrap**: resample the 43 events (20 train-near, 15 train-far, 6 obstacle-far, 2 obstacle-near) with replacement, 2,000 draws, and recompute the estimate. With only 2 obstacle-near events that cell's CI is not estimable and is reported descriptively. An endpoint whose trial-level result is significant but whose event-cluster CI includes zero is reported as **stimulus-specific to the sampled events, not generalisable**.
- **Temporal autocorrelation.** Binned activity uses 10 ms bins, but no test treats bins as replicates. Where a trial-level summary depends on binning, the 10 ms choice is fixed in advance; a 5 ms and 20 ms recomputation is reported as a sensitivity, not used to select a result.
- **Degenerate variables.** A response variable with a single observed level produces `I = 0` by construction and is reported as **degenerate / inconclusive**, not as evidence of no information. This is the Phase 6C C-02 lesson applied prospectively: the 4H downstream channels may well be all-zero, and an all-zero channel is a failed observation, not a negative finding.

### 8.7 What 672 trials do not buy

672 trials buy precision on the simulation-noise dimension and on the four stimulus levels. They do **not** buy 672 independent stimuli: the corpus has 43. A result that depends on repeating two obstacle-near events 84 times each has an effective stimulus sample of two, and the protocol commits in advance to reporting it as such.

## 9. Statistical analysis plan

### 9.1 Confirmatory endpoints

Ten endpoints, each tied to one hypothesis. An endpoint is **unlocked** only if its stage completed and the stated gate passed; otherwise it is reported as not evaluated.

| ID | Hypothesis | Estimand | Unit / n | Test | Direction |
| --- | --- | --- | --- | --- | --- |
| E1 | H1 | Proportion of trials with ≥ 1 H1 spike | 20 trials per group in Stage P; 672 per condition in Stage R | One-sided Fisher exact, `REAL` vs pooled controls | `REAL` > control |
| E2 | H1 | Median H1 spike count per trial | Trial | Mann–Whitney U, trial as unit, cluster bootstrap CI over seeds | `REAL` > control |
| E3 | H2 | Proportion of trials with ≥ 1 H2 ∪ DESC spike | Trial | Fisher exact; degenerate-aware rule if controls are 0 | `REAL` > control |
| E4 | H2 | `I(stimulus level ; H1 recruitment code)` | 672 trials | Plug-in MI, bias-floor corrected, 5,000 trial permutations | `REAL` > `SHUFFLED_MASK` |
| E5 | H3 | `I(stimulus level ; H2/DESC recruitment code)` | 672 trials | Plug-in MI, bias-floor corrected, 5,000 permutations, 2,000 event-cluster bootstrap | `REAL` > `SHUFFLED_MASK` and > 0 |
| E6 | H3 | `I(stimulus level ; H2 response ∣ H1 recruited)` | Trials with ≥ 1 H1 spike | Conditional MI as sample-weighted mean of within-stratum MI, permutation null | > 0 after the free-flow constraint |
| E7 | H4 | Proportion of DESC spikes followed by a MOT spike within 5 ms | DESC spikes | Trial-clustered proportion, permutation of MOT timing | `REAL` > control |
| E8 | H5 | `I(stimulus level ; decoded state)` | 672 trials × 5 windows | Plug-in MI with degenerate guard, permutation | `REAL` > 0 |
| E9 | H5 | `I(pool activity code ; decoded state)` | Decoder windows | Plug-in MI, descriptive if P3 failed | > 0, labelled decoder-mediated |
| E10 | H6 | Paired difference in `I(cue ; A_neural)` between `plastic_complete` and `fixed_complete` | 40 seed clusters, 6,400 rows | Cluster bootstrap CI on the paired difference, Holm | `plastic` > `fixed` |

E9 can never support a motor claim even if significant: the decoder defines the mapping, so `I(pool; decision)` measures the decoder's own rule. It is listed to make that circularity explicit rather than to provide evidence.

### 9.2 Estimation constants, fixed before data

| Choice | Value | Rationale |
| --- | --- | --- |
| Response discretisation, H1/H2/DESC | 3 levels by absolute spike count per trial: `0`, `1–2`, `≥3` | Absolute thresholds are fixed in advance; sample tertiles would make the table data-dependent and inflate MI |
| Population-code discretisation | 4 levels: `(0 active, 0 spikes)`, `(≥1 active, ≤ median spikes)`, `(≥1 active, > median, ≤ 2× median)`, `(≥1 active, > 2× median)` with the median fixed from Stage P | Keeps the code ordinal and comparable across conditions |
| Time bin | 10 ms, 30 bins over 300 ms | Matches the decoder's 5-window readout at 50 ms; 10 ms resolves a 2 ms refractory interval |
| Spike-train distance | Not used | No metric-space estimator is needed; all endpoints are table-based |
| Entropy estimator | Plug-in `H = −Σ p log₂ p`, Miller–Madow correction `(K_obs−1)/(2N ln2)` reported alongside | Consistent with Phase 6B, which already used both |
| MI estimator | Plug-in `I`, bias floor `(kx−1)(ky−1)/(2N ln2)`, `I_corrected = max(0, I − floor)` | Consistent with Phase 6C C-03 and §8.2 |
| Normalised MI | Reported only when `H(x) > 0.05` bits and `H(y) > 0.05` bits | The Phase 6B/6C threshold, retained to avoid dividing by a near-zero entropy |
| Conditional MI | Sample-weighted mean of within-stratum MI, with the bias floor computed per stratum | The implementation in `information/`; no new estimator |
| Permutation count | 5,000, trial level, labels permuted within stage and condition | p floor 0.0002 |
| Bootstrap | 2,000 percentile resamples; event clusters for H2/H3; seed clusters for Stage S; trial resamples for H1/E2 | Matches the independence hierarchy in §8.1 |
| Bootstrap seed | 20261110 | Fixed, matching the Phase 6B/6C convention |
| Multiple comparisons | Holm–Bonferroni over the unlocked family, α = 0.05 | Fixed before gates are evaluated |
| Missing data | No imputation. A trial failing a mandatory field is excluded and counted. More than 5% exclusion in any condition is an integrity failure. | Prevents selective loss |
| Minimum support | ≥ 20 rows per level, else collapse by the declared rule or declare not estimable | §8.6 |
| Degenerate variable | Single observed level → report degenerate, not negative | §8.6 |

### 9.3 Execution order

1. Validate the record set (P0/schema, missing-data counts, determinism sample).
2. Reproduce the archived Phase 4H condition-B spike hash (C8). If it fails, stop.
3. Evaluate P1, fix `d*`, then P2, then P3, in that order, and write the gate decision to disk.
4. Run Stage R analysis only on the conditions the gates unlocked.
5. Run Stage S integrity check (Phase 5F contrast reproduced at 40 seeds). If it fails, skip E10 and record it.
6. Compute E1–E10 with the fixed constants, then the corrections.
7. Write the results table with raw estimate, floor, corrected estimate, CI, permutation p, Holm-adjusted p, and support counts for every endpoint.
8. Freeze the results file (SHA-256) before writing any prose.

### 9.4 Control of false positives

- The gates determine the family; the family determines the Holm correction. Endpoints added after seeing results are exploratory and are labelled as such.
- The `NO_STIM` and `MATCHED_CHARGE` conditions provide the empirical false-positive rate. If either control shows non-zero downstream activity, E3's threshold is raised to the observed control upper 95% bound rather than 0, and this is documented at the time of the gate decision.
- Every endpoint reports its null distribution summary (median and 95th percentile of the permuted statistic), not only the p-value, so a significant result floating just above a wide null is visible.

### 9.5 Interpretation guardrails, fixed in advance

1. A significant MI does **not** establish a biological mechanism; it establishes that a table of simulated counts is not exchangeable with its permuted labels.
2. A decoder output does **not** establish motor control. E8 and E9 are decoder-mediated by construction.
3. A failed E3 or E5 with zero downstream spikes is **degenerate**, and the report must say "no downstream events were observed" rather than "no information flows downstream".
4. E10 is a statement about the Phase 5 synthetic substrate and is never pooled with Stage R.
5. Any inversion of the direction in E10 (plastic < fixed) is reported as found and is not reframed as a null.

### 9.6 Reproducibility of the analysis itself

The analysis imports the estimators from `information/` without modification, reads only files under `experiments/results/phase_6d/`, writes no random state outside `np.random.default_rng(20261110)`, and emits a JSON alongside the Markdown with every number traceable to one row. Re-running the analysis on the frozen inputs must reproduce the JSON byte-for-byte; if float formatting prevents this, the comparison is done on parsed values with a 1e-9 tolerance and the tolerance is stated in the report.

## 10. Success and failure criteria

Every criterion below is *operational*: it can be evaluated from the frozen result file without judgement. None of them is a claim about a fly.

### 10.1 Recording integrity

| Outcome | Criterion |
| --- | --- |
| **Pass** | All mandatory fields present in ≥ 99.5% of trials; the 5% determinism re-run reproduces `spike_hash` in every sampled trial; the archived 4H condition-B hash is reproduced; no `SpikeCapacityExceeded`; all membrane arrays finite. |
| **Fail** | Any determinism mismatch that cannot be traced to a declared code change, or any silent truncation, or > 5% of trials missing a mandatory field in any condition. |
| **Inconclusive** | Not applicable — integrity is binary. A failed integrity check is reported as a failed phase, not an inconclusive one. |

### 10.2 Reproducibility across the analysis

| Outcome | Criterion |
| --- | --- |
| **Pass** | Re-running the analysis on frozen inputs reproduces every number within 1e-9; seed-split halves (20/20) agree in sign on every unlocked endpoint. |
| **Fail** | A number changes after freezing, or the two seed halves disagree in sign on a confirmatory endpoint. |
| **Inconclusive** | Sign disagreement on an endpoint is reported as instability for that endpoint only; it does not invalidate the others. |

### 10.3 Stimulus encoding (H1)

| Outcome | Criterion |
| --- | --- |
| **Positive** | E1 passes (≥ 10/20 `REAL` with H1 spikes vs ≤ 1/20 controls, Fisher p < 0.01) and E2 shows a higher median H1 count in `REAL`. |
| **Negative** | `REAL` and both controls are at the same floor (≤ 1/20), while `DIRECT_INJECTION` proves H1 neurons can spike. This is a drive/encoder failure and is reported as such. |
| **Inconclusive** | Real and control differ but `DIRECT_INJECTION` also fails to drive H1; or the effect is carried entirely by one seed half. |

### 10.4 Downstream propagation (H2, H3)

| Outcome | Criterion |
| --- | --- |
| **Positive** | P2 passes and E3 shows a higher prevalence in `REAL` than in both `SHUFFLED_MASK` and `MATCHED_CHARGE`. |
| **Negative** | P2 fails at every drive up to 1200 pA, or E3 shows no difference from controls. Reported as "no propagation detected under this design", which is consistent with Phase 4H.4 and does not contradict it. |
| **Inconclusive** | `REAL` exceeds `NO_STIM` but not `MATCHED_CHARGE` (charge-driven), or the response exists but is not feature-specific (`SHUFFLED_MASK` equals `REAL`); or all downstream channels are degenerate. |

### 10.5 Population-level information (H2, H3)

| Outcome | Criterion |
| --- | --- |
| **Positive** | E5 (and E4) survive Holm with a corrected MI whose event-cluster CI excludes zero and whose support requirements are met. |
| **Negative** | E5 is estimable and its corrected MI is indistinguishable from the permutation null. |
| **Inconclusive** | E5 is not estimable (degenerate response, < 20 per level, or < 2 events in a cell); or E5 is significant at trial level but the event-cluster CI includes zero. |

### 10.6 Neural-to-motor information (H4, H5)

| Outcome | Criterion |
| --- | --- |
| **Positive** | E7 or E8 survives Holm with the declared support, **and** P3 passed. Labelled decoder-mediated even then. |
| **Negative** | P3 passed but E7/E8 are at the null. |
| **Inconclusive** | P3 failed (decoder never left NEUTRAL) — the endpoint is untestable, which Phase 4H.4 suggests is the likely outcome. |

Even a positive here does **not** establish biological motor control: the decoder is a hand-written threshold rule, and `I(pool; decision)` is partly the rule's own definition.

### 10.7 Plasticity-related neural change (H6)

| Outcome | Criterion |
| --- | --- |
| **Positive** | The Phase 5F success contrast reappears at 40 seeds, and the paired cluster-level difference in E10 has a CI excluding zero and exceeds 0.05 bits in the plastic > fixed direction. |
| **Negative** | The contrast reappears but the E10 difference is < 0.05 bits or its CI contains zero. This extends the Phase 6C C-06 negative result at higher power and is reported as "no detectable neural-level change". |
| **Inconclusive** | The 5F contrast does not reappear; or > 20% of seeds are degenerate in the action code; or row-level and cluster-level signs disagree. |

### 10.8 Behavioural / task performance (H6, integrity check only)

| Outcome | Criterion |
| --- | --- |
| **Pass** | `plastic_complete` success exceeds `fixed_complete` by a paired difference whose CI excludes zero, reproducing Phase 5F's +0.150 direction. |
| **Fail** | No difference, or a reversed difference. A reversal is reported, not reframed. |
| **Inconclusive** | Not applicable; this is a reproduction check, and failure blocks E10 only. |

### 10.9 How the eight combine into one phase verdict

| Combination | Phase verdict |
| --- | --- |
| Integrity fails | **Invalid** — no scientific conclusion. |
| Integrity passes, P2 fails | **Negative on propagation**, consistent with Phase 4H.4/4H.5. Stage R and E4–E9 are not run. |
| P2 passes, E5/E4 null | **Propagation without detectable stimulus-specific information.** Reported as a mechanistic finding with the degenerate/specificity caveat. |
| P2 and E5 pass, P3 fails | **Information reaches downstream populations in the model; the decoder does not reach it.** H4/H5 untestable. |
| P2, E5 and P3 pass, E7/E8 null | **Propagation and population information exist; no decoder-mediated consequence detected.** |
| All gates pass and endpoints survive Holm | **Computational information flow established in the model** (evidence grade at most E2). Not a biological claim. |
| Stage S integrity fails | E10 skipped; the Stage R verdict stands independently. |

A statistically significant endpoint never by itself moves the verdict above "computational information flow established in the model". Biological validity is not an available conclusion of this phase under any combination.

## 11. Feasibility and resource estimate

### 11.1 Compute, time and storage

All figures are derived from measured constants, not from a benchmark of unwritten code. The run-time anchor is the median 2.54 s per 300 ms BANC run over 352 timings in `population_sensitivity.json` (min 1.66 s, max 4.30 s). The Phase 4H round-trip median of 20.62 s is not used because it includes replay instrumentation that this campaign does not need; the single 5,057 s outlier in that set is likewise excluded and is a warning that a pathological run can stall the queue.

| Stage | Work | Sequential wall time | Storage |
| --- | --- | ---: | ---: |
| P | 324 BANC runs | 0.23 h | ≈44 MB |
| R | 2,688 + 134 repeats | 1.98 h | ≈363 MB |
| R with O2+O3 diagnostics | same runs | +20% I/O | ≈1.8 GB |
| S | 19,200 episodes on a 36-node graph | 20–40 min | ≈120 MB |
| A | analysis | < 30 min | < 10 MB |
| **Total, mandatory** | **3,146 runs + 19,200 episodes** | **≈2.8 h** | **≈537 MB (0.53 GB)** |
| **Total, with optional diagnostics** | same | **≈3.0 h** | **≈1,900 MB (1.9 GB)** |

**Memory.** The simulator's retained arrays are fixed by the graph, not by the trial: graph and policy arrays dominate, the neuron and synapse state is two `float64`/`float32` vectors of 172,433, and the `SpikeRecorder` grows with recorded spikes. At the declared 500,000-spike cap the recorder holds 4 MB. Peak resident memory is estimated at 0.3–0.5 GiB. Phase 6A measured 0.97 GiB free when the audit ran, so a **single process** is the safe configuration; two concurrent workers would exceed available memory if the graph is loaded twice. The campaign therefore runs sequentially by default and only enables concurrency if free memory is verified above 1.5 GiB at start.

Pure-Python permutation and bootstrap loops dominate the analysis, not the simulation: 10 endpoints × 5,000 permutations of a 672-row table is ≈50,000 MI evaluations, each sub-millisecond with `numpy.bincount`.

### 11.2 Reusable modules (no modification)

| Module | What it provides | Used for |
| --- | --- | --- |
| `brain/banc_simulator.py` | `BancSimulator`, `BancStimulation`, `BancSignedSynapses`, `BancSimulationResult` | Every Stage R run |
| `brain/neuron_model.py` | `LIFPopulation`, `LIFParameters`, `membrane_potential` | Integration; optional O2 panel |
| `brain/neural_activity.py` | `SpikeRecorder` with `save`, `spike_counts`, `capacity` | Spike storage |
| `brain/banc_sensory_adapter.py` | `BancSensoryMapping`, `BancEventDrive`, `ConstantChargeDrive`, `shuffle_feature_identities` | All four Stage R conditions |
| `brain/banc_simulation_adapter.py` | `BancActivityAdapter.decode` | Decoder windows |
| `motor/motor_decoder.py`, `motor/populations.py` | `MotorDecoder`, `DecoderConfig`, action pools | Fields 17, E8, E9 |
| `sensory/population_encoder.py` | `GaussianPopulation`, `EncoderSpec` | Stimulus encoding |
| `plasticity/plastic_simulator.py`, `engine.py`, `weights.py`, `traces.py`, `tasks.py` | `PlasticSimulator` with `step_callback`, `EligibilityStore`, `WeightState`, task substrate | Stage S |
| `information/` | `bias_correction.required_sample_size`, entropy, MI, CMI, NMI, permutation, bootstrap, digest | Stage A |
| `experiments/phase_4h/common.py` | `load_world`, `spike_hash`, `integrity_snapshot` | C8 replay, integrity baseline |

### 11.3 Instrumentation that must be written (not written in this phase)

| New file | Purpose | Approximate size |
| --- | --- | ---: |
| `experiments/phase_6d/recording.py` | `TrialRecorder`: wraps `sim.neurons.step` exactly as `analyse_sensory_roundtrip.py` does, accumulates per-step panel potentials and currents only when enabled, builds the sparse record, writes npz + manifest row | 350–450 lines |
| `experiments/phase_6d/trial_schedule.py` | Declared stimulus levels, event round-robin, seed list, condition assignment, `d*` selection logic | 200–300 lines |
| `experiments/phase_6d/run_propagation_pilot.py` | Stage P runner and gate evaluation, writes gate decisions to disk before Stage R can start | 250–350 lines |
| `experiments/phase_6d/run_recording_campaign.py` | Stage R runner, resume via manifest, determinism re-runs | 300–400 lines |
| `experiments/phase_6d/run_plasticity_recording.py` | Stage S runner on `PlasticSimulator` with `step_callback` | 250–350 lines |
| `experiments/phase_6d/analyse_phase_6d.py` | E1–E10, Holm, permutation, cluster bootstrap, gate-aware family | 500–700 lines |
| `experiments/phase_6d/build_report.py` | Markdown + JSON report from the frozen results | 200–300 lines |
| `configs/phase_6d_recording.yaml` | All declared constants in one file | ≈100 lines |
| `tests/test_phase_6d_recording.py` | Schema completeness, determinism, gate logic on synthetic tables, estimator agreement with `information/` | 400–600 lines |

**Total new code ≈ 2,550–3,650 lines**, of which the only part that touches the simulator is a wrapper object assigned to `sim.neurons.step` — the same technique already proven in `analyse_sensory_roundtrip.py`. No production module is edited. Tests must cover: (i) that the wrapper does not change the spike hash on an archived configuration, (ii) that a record missing any mandatory field is rejected, (iii) that the 6×4 bias floor matches `information.bias_correction.required_sample_size`, (iv) that `d*` is the lowest passing drive, (v) that P2 stops the runner, and (vi) that the analysis refuses to evaluate a locked endpoint.

## 12. Risks and limitations

### 12.1 Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Residual |
| --- | --- | --- | --- | --- | --- |
| R1 | Propagation never appears at any drive up to 1200 pA | High — Phase 4H.4 found none at ≈67 pA/neuron and second-hop current exactly 0 | Programme stops at Stage P | P0–P2 gate before the 2,688-run campaign; documented stop rather than a null campaign | A true propagation rate near 20% can still be missed (P2 sensitivity 0.79) |
| R2 | Descending and motor populations are structurally unreachable from the annotation mapping | High — 9 descending neurons receive current, 0 first-hop motor targets | H4 and H5 untestable | Gates P3 and E7/E8 report untestable, not negative | None; this is a property of the graph and mapping |
| R3 | Only 43 of 215 archived events carry feature values; `OBST_NEAR` has 2 | Certain | Stimulus-generalisation limited | Event-cluster bootstrap; explicit "describes these events" wording | Cannot be repaired without new perception output, which is out of scope |
| R4 | The `sim.neurons.step` wrapper changes simulator behaviour | Low — same technique already used in Phase 4H | Invalidates all data | C8 archive replay hash and 5% determinism re-runs | A behavioural change that is deterministic would pass the hash test |
| R5 | Memory pressure: 0.97 GiB free at audit | Medium | Run failures, swapping | Sequential execution, 500k spike cap, no full-population recording | A larger graph load on a busier machine could still fail |
| R6 | Float32 recorder summation order varies | Low | Determinism mismatch | Re-run in a separate process, compare hashes | Platform differences could break bit-exactness across machines |
| R7 | Bias floor is an approximation for sparse or skewed tables | Medium | Over- or under-correction | Report raw, floor, corrected, CI; never report corrected alone | An estimate near the MDE could be materially wrong in either direction |
| R8 | Effective stimulus n is 43, not 672 | Certain | Wider CIs than trial-level N suggests | Both inference levels reported; no claim beyond sampled events | Cannot be fixed within this corpus |
| R9 | `d*` is chosen from pilot data | Certain | Data-dependent design parameter | Rule fixed before downstream outcomes; disclosed | A reader may still view the choice as partially adaptive |
| R10 | `MATCHED_CHARGE` spreads the same total charge uniformly (≈46.7 pA/neuron at Phase 4H scale) and may be subthreshold | High | A weak control that cannot propagate, making `REAL` look specific | Report per-neuron amplitude; treat a `MATCHED_CHARGE` null as uninformative if peak current is below rheobase | A concentrated-charge control is not included |
| R11 | `NO_STIM` with 50 pA noise produced zero spikes in Phase 4H | Certain | Spontaneous baseline is degenerate; C1 has no variance | P2 uses "0 of 40" as a screen, not a test | The gate's discrimination comes almost entirely from `REAL` |
| R12 | Stage S is a different substrate from Stage R | Certain | No pooled inference | Explicit separation; H6 wording restricted to the synthetic task | A reader may over-generalise; wording is the only control |
| R13 | Single implementation; no independent re-implementation | Certain | Shared conceptual errors undetected | Archive replay, determinism, unit tests on estimators | Cannot be eliminated in this phase |
| R14 | One pathological run stalls the campaign (5,057 s observed once in 4H) | Low | Schedule slip | Per-run timeout with explicit failure record, resume from manifest | A timeout loses that trial; reported as missing data |
| R15 | Decoder endpoints are circular by construction | Certain | E8/E9 cannot support a motor claim | Labelled decoder-mediated; excluded from the overall verdict above E2 | None |
| R16 | Stimulus onset is re-anchored to 50 ms, changing timing relative to the archive | Certain | Latency comparisons to archived runs are not exact | Latency reported descriptively; no cross-archive latency claim | None |
| R17 | No neuromodulation, adaptation, or cell-type-specific conductances | Certain | Model cannot represent biological learning | Stated in every result section | Requires a different model |

### 12.2 The four limitations that survive every mitigation

1. **The propagation gate may fail, and that is the most probable outcome.** Phase 4H.4 measured second-hop current of exactly zero and closest first-hop membrane potential 6.926 mV below threshold. Nothing in this design guarantees that raising the drive changes that; it only guarantees that the failure is measured cleanly and reported as a stop rather than as a null campaign.
2. **The motor pathway is very likely untestable.** With 0 first-hop motor targets and 9 descending neurons reaching at most −62.158 mV in 4H, H4 and H5 depend on an event that has not yet been observed. The design makes them conditional rather than assuming them.
3. **Membrane and synaptic-current data exist only through a wrapper on a declared panel.** The protocol does not claim full-population recording, and no dense array is produced.
4. **No combination of results in this phase establishes biological validity.** The best available conclusion is that information flow is established *in the declared model*, at evidence grade no higher than E2 in the project's own scale.

### 12.3 What would change the design if it were re-scoped

If the Phase 4H.5 recommendation to calibrate a sensory-drive threshold is pursued first as a standalone step, it would replace Stage P's drive series with a finer geometric sweep (for example 1.5× steps between 100 and 1200 pA) and could identify a propagation threshold that the four-point series brackets only coarsely. That is not included here because it would double Stage P and because the four-point series was the pre-registered recommendation. It is listed in §14 as an optional prerequisite.

## 13. Explicit approval gates

No gate is crossed implicitly. Each gate has an artifact that records the decision, and a gate that has not been approved is treated as failed.

| Gate | What must be true before it | Approval needed | Artifact |
| --- | --- | --- | --- |
| **G0 — protocol** | This document and its JSON companion are reviewed and accepted, including the three open scope decisions in §14.1. | Human reviewer | Signed note in the phase record; the protocol SHA-256 is frozen |
| **G1 — instrumentation** | G0 passed. Approval to **write** the `experiments/phase_6d/` code and tests. No simulations run under G1. | Human reviewer | Code diff restricted to `experiments/phase_6d/`, `configs/phase_6d_recording.yaml`, `tests/test_phase_6d_recording.py` |
| **G2 — instrumentation validated** | G1 passed. The full test suite passes, the wrapper reproduces the archived 4H condition-B spike hash, and no production module changed. | Automated checks plus human sign-off | Test log, archive hash equality, `git status` showing only the three new paths |
| **G3 — pilot** | G2 passed. Approval to run Stage P (324 runs). | Human reviewer | Stage P run manifest |
| **G4 — gate decision** | Stage P complete. P0–P3 evaluated in order, `d*` fixed and written. | Human reviewer, because P1's outcome sets the rest of the programme | Frozen gate-decision JSON with `d*` and the pass/fail of each gate |
| **G5 — campaign** | G4 passed with P2 positive. Approval to run Stage R. | Human reviewer | Stage R manifest; if P2 failed, this gate is recorded as **not reached** and the programme stops |
| **G6 — plasticity stage** | G5 passed or explicitly waived. Approval to run Stage S. | Human reviewer | Stage S manifest |
| **G7 — analysis and report** | All runs complete and frozen. Analysis run once; results frozen before prose. | Human reviewer | Results JSON SHA-256, analysis report, and a discrepancy log if any number changed after freezing |

The gates deliberately place human approval between the pilot and the campaign (G4) and require that the gate decision be frozen before any downstream outcome is examined. That is the mechanism that prevents drive selection from being tuned to the result.

## 14. Recommended next actions

### 14.1 Three decisions for the reviewer before G0 is signed

1. **Optional panel diagnostics.** Enable O2/O3 (membrane and synaptic current on ≤ 458 nodes, ≈1.4 GB additional storage) or keep the campaign to the mandatory sparse record (≈363 MB)? Enabling them would allow a descriptive check that the LIF integration behaved as assumed, at a storage cost and with no confirmatory endpoint attached.
2. **Drive series.** Accept the four-point pre-registered series (200/400/800/1200 pA), or first run a finer threshold calibration as a separate prerequisite? The four-point series is what Phase 4H.5 recommended; a finer series would bracket the threshold more precisely at roughly double the Stage P cost.
3. **Stage S scope.** Is the fixed-versus-plastic neural recording on the Phase 5 substrate in scope for Phase 6D, or should it be deferred to its own phase? It uses a different substrate and answers H6 independently of H1–H5.

### 14.2 If the protocol is approved

1. **G0:** review and sign this protocol; freeze its SHA-256 into the phase record.
2. **G1:** write the instrumentation and tests listed in §11.3. Do not run simulations.
3. **G2:** validate against the archived 4H spike hash, run the full test suite, confirm that `brain/`, `sensory/`, `motor/`, `plasticity/`, `information/` are unmodified.
4. **G3–G4:** run Stage P (324 runs, ≈14 min), evaluate P0–P3, freeze `d*` and the gate decision.
5. **Stop here if P2 is not positive.** Write the negative report and leave Phase 4H/4H.5 conclusions intact.
6. **G5:** if P2 passed, run Stage R (2,688 + 134 runs, ≈2 h).
7. **G6:** run Stage S (19,200 episodes, ≈30 min) if in scope and if the Phase 5F contrast reproduces at 40 seeds.
8. **G7:** run the analysis once, freeze the results JSON, then write the report.

### 14.3 Explicitly out of scope for this document

No simulation has been run, no recording has been produced, no model has been trained, no neural architecture has been changed, and no instrumentation has been written. The two deliverables are this Markdown protocol and its JSON companion. Any execution requires G0 and G1 in that order.
