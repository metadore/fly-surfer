# Phase 4 — Phase 7 Motor-Output Failure Analysis

**Date:** 2026-11-17
**Question:** Why did the Phase 7 fixed-weight closed loop produce 213 updates,
2,852 spikes, zero motor-population spikes and 213 `NO_ACTION` outputs?
**Scope:** analysis of existing artifacts only. No simulation was re-run for this
report, no parameter was changed, and no threshold was moved.
**Primary artifacts:** `experiments/results/phase_7/neural_closed_loop.json`,
`reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json`,
`reports/PHASE_4G5_MOTOR_DECODER_INTEGRATION.md`,
`reports/PHASE_4H5_STATISTICAL_ASSESSMENT_AND_EVIDENCE_GRADING.md`.

---

## 1. Bottom line

Activity stops **one synapse downstream of the stimulated sensory neurons**.
The 232 stimulated neurons spike, and their spikes propagate as synaptic current
to 473 of 607 first-hop targets. The strongest first-hop target reaches
**−56.926 mV**, which is **6.926 mV below the −50 mV threshold**, and does not
spike. Because no first-hop neuron spikes, no second-hop current is delivered at
all. Descending neurons receive some current (9 neurons, best −62.158 mV) and
also do not spike. Motor neurons receive **zero** current. The decoder therefore
sees zero motor spikes, fails its evidence gate (≥ 5 spikes, ≥ 3 active neurons),
and returns `NEUTRAL`, which the adapter executes as `NO_ACTION`.

This is a **controlled negative result** about one model configuration. It is
not a bug in the decoder, selector, controller, game adapter or action timing,
and it is not evidence about the living fly.

---

## 2. Stages traced

| Stage | Phase 7 run | 4H4 condition B (same input design) | Interpretation |
|---|---:|---:|---|
| Game updates | 213 | 67 decoder windows | Loop ran to a game termination (collision) |
| Neural steps / time | 7,100 / 3,550 ms | 3,300.5 ms stream | Clock sync held (33.33 steps per update) |
| Stimulated sensory neurons | 232 | 232 | Fixed annotation-defined set |
| Spikes, total | 2,852 | 3,562 | Reproducible activity exists |
| Spikes in stimulated set | 2,852 | 3,562 | **100 %** |
| Spikes in non-stimulated neurons | **0** | **0** | No propagation past one hop |
| Motor-population spikes (LEFT/RIGHT/JUMP) | **0 / 0 / 0** | **0** | Decoder has no input |
| Active neurons | 71 (all stimulated) | — | 71 < 232: only part of the driven set fires |
| Spike-edge transmissions | 10,215 | 25,332 (9,499 signed) | Synapses did transmit |
| Decoder states | `NO_ACTION` × 213 | `NEUTRAL` × 67 | Gate never passed |
| Executed actions | `NO_ACTION` × 213 | — | Adapter honest |
| Weights unchanged | `true` | fixed weights | Control, not learning |
| Deterministic replay | `true` | 6/6 repeat pairs hash-equal | Result is stable |

The 4H4 stream is longer and driven differently, so its spike count is higher.
The qualitative result is identical: all spikes are inside the stimulated set.

---

## 3. Where exactly the propagation stops

The 232 stimulated neurons have **662 signed outgoing edges** at t5 to **608
unique targets**; 607 targets are non-stimulated. Signed criterion:
`exc_weight > 0 or inh_weight > 0` under the verified-only policy.

| Group | Neurons | Receive current | Max synaptic current | Max membrane | Deficit to −50 mV | Spikes |
|---|---:|---:|---:|---:|---:|---:|
| Stimulated | 232 | 1 (recurrent) | 17.02 pA | −50.000 mV | 0.000 | 3,562 |
| First hop | 607 | **473** | **164.443 pA** | **−56.926 mV** | **6.926 mV** | **0** |
| Second hop | 3,576 | **0** | 0 pA | −65.000 mV | 15.000 mV | 0 |
| Descending (all) | 1,316 | 9 | 67.208 pA | −62.158 mV | 12.158 mV | 0 |
| Motor (all) | 805 | **0** | 0 pA | −65.000 mV | 15.000 mV | 0 |
| LEFT / RIGHT / JUMP | 185 / 186 / 20 | 0 / 0 / 0 | 0 pA | −65.000 mV | 15.000 mV | 0 |

Key structural facts:

- **No motor neuron is a first-hop target** (`first_hop_targets_motor: 0`).
  Motor neurons are reachable only at the second hop (4 of them), and the second
  hop never fires.
- **9 first-hop targets are descending neurons**, but they are not among the 473
  that receive current strongly enough; the 9 that receive current peak at
  −62.158 mV.
- The first hop is not silent because the graph is disconnected: 473 neurons
  received current, up to 164 pA. It is silent because current-to-spike
  conversion falls short by ~7 mV.

**Stop point:** synaptic integration at the first postsynaptic population.

---

## 4. Why this is not a decoder or controller failure

| Control | Result | What it proves |
|---|---|---|
| 4G5 condition C (direct 300 pA drive into a 64-neuron VNC-intrinsic group) | 492 motor spikes, 82 motor neurons, JUMP ×4, NEUTRAL ×1 | The same decoder, populations and adapter do produce valid actions when motor activity exists |
| Decoder thresholds | Declared before experiments; unchanged | No post-hoc tuning |
| Decoder gate | 0 motor spikes < 5 spikes and < 3 active neurons | `NEUTRAL` is the correct output for the input |
| Action selection/controller (new) | 42 focused tests, incl. conflict, hold, cooldown, invalid outputs, replay | Selection is not the cause; it was not in the Phase 7 path |
| Adapter | `NO_ACTION` with `supported: true`, `unmapped: false` | `NO_ACTION` is a decoded neutral state, not an error fallback |
| All 14 Phase 7 pipeline checks | 12 true; `decoder_received_motor_activity: false`, `decoded_action_supported: false` | The run self-reports the exact failure |

The Phase 7 record even shows the decoder being called on every update
(`decoder_called_every_update: true`). The decoder is not skipped; it is fed
nothing.

---

## 5. Why this is not a graph-construction artifact

- The t5 graph retains 1,535,710 edges and 18,552,546 synapses; the DN→MN
  subgraph alone has 6,409 edges.
- The sensory set is connected: 662 signed outgoing edges, 608 targets.
- Four motor neurons are reachable at the second signed hop.
- The first-hop current reaches 164 pA, which is above the declared 150 pA
  rheobase in 4H4’s reporting but still does not cross threshold because the
  current is synaptic and transient, not a sustained step (membrane peaks at
  −56.93 mV).
- A random matched mapping (4H4 condition E) also produces zero non-stimulated
  spikes, and a constant-charge control (F) produces none. The absence is not
  specific to the chosen mapping.

So “the graph is broken” and “the mapping is uniquely bad” are both excluded as
explanations of the *absence of any postsynaptic spike*, though the mapping’s
quantitative weakness is not excluded.

---

## 6. What the controls exclude

| Explanation | Excluded by |
|---|---|
| No sensory input delivered | 13,476.67 pA total sensory current at the pipeline probe; 2,852–3,562 stimulated spikes |
| Graph disconnected | 473 first-hop receivers; 608 targets |
| No transmission | 25,332 spike-edge transmissions, 9,499 signed |
| Shuffle-specific artefact | Temporal shuffle (C) has 3,760 stimulated spikes and still 0 downstream |
| Charge amount too low | Constant matched-charge control (F) delivers the same total charge and still 0 spikes |
| Only no background activity | Background 50 pA + noise 50 pA control (G) also produces 0 spikes; closest neuron 7.35 mV short |
| Decoder threshold too high | Lowering it was not done and would not help: the input is 0 motor spikes |
| Weights changed during the run | `weights_unchanged: true`; fixed-weight control |

---

## 7. What remains as the explanation

Under the project’s declared model assumptions, the sensory drive produces
subthreshold first-hop depolarisation, so the network’s activity is confined to
the directly stimulated set. The decisive variables are model assumptions, not
missing code:

1. **Sign coverage.** Only 683,100 of 1,535,710 t5 edges are signed under the
   verified-only policy; unknown edges are excluded. A path that is structurally
   present may carry no modelled current.
2. **Synaptic strength transform.** Structural counts → `count**0.75 × 5 pA`,
   capped at 300 pA. This is a calibration choice, not a measurement.
3. **Passive properties.** LIF capacitance, leak, threshold, reset and 1 ms
   delay determine how 164 pA of transient synaptic current maps to a membrane
   peak. The peak is 6.93 mV short.
4. **Network scale and fan-out.** 662 signed edges from 232 neurons is ~2.85
   signed edges per stimulated neuron; the average first-hop target receives
   little summed current.
5. **No spontaneous drive.** Phase 7 uses 0 pA background and 0 pA noise. This
   is a controlled choice, not a claim that the fly is silent.

None of these was changed to force activity. Changing any of them changes the
model, and the result would then be a different experiment requiring its own
pre-registration.

---

## 8. What would legitimately change the conclusion

Each requires external evidence (see `PHASE_4_MISSING_RESOURCES.md`) and a new
pre-registered experiment; none was run:

- target-specific functional sign/conductance (R3);
- measured passive/synaptic properties for the relevant cell types (R4);
- a measured sensory-feature→neuron map (R5);
- a validated action→neuron mapping (R6);
- a later BANC release with fuller annotation (R7–R9).

A future protocol could also test propagation with a **declared** and
**unchanged** alternative sign/weight policy as a sensitivity condition, but it
must report all conditions, not select the one that fires.

---

## 9. Evidence grade

Consistent with `PHASE_4H5`:

- **E0 infrastructure:** met — integrity, configuration checks, determinism.
- **E1 computational activity:** met only in directly stimulated populations.
- **E2 population-level sensitivity:** met — decoder output responds to pool
  identity, size, selection rule and drive amplitude under controlled drive.
- **E3/E4 (downstream propagation / functional motor recruitment): not
  supported.** No non-stimulated spike, no motor current, no decoder window
  above threshold.

---

## 10. Consequence for Phase 4

Requirement 9 (“test the complete sensory-to-motor loop”) is **implemented and
executed**. Its functional half is a reproduced negative. The correct Phase 4
status is therefore *partial*: the motor software is complete, the sensory-tomotor
function is not demonstrated, and the cause is a documented model-evidence gap
rather than a defect that can be fixed by changing thresholds or simulation
parameters.
