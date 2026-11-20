# Phase 8 Pilot 1 — Motor-Bottleneck Investigation

**Date:** 2026-11-20
**Stage investigated:** REV4 §10.3 Pilot 1 (condition A viability grid)
**Mode:** read-only analysis of existing artifacts. No simulation was re-run, no
neural equation, weight, threshold, seed or configuration was changed, no graph
was regenerated, REV4 and the D1/D2 records were not touched, and neither Pilot 2
nor training was executed.
**Question:** why did Pilot 1 produce 73,880 total neural spikes and zero
motor-neuron spikes across all nine episodes?

---

## 1. Bottom line

Pilot 1 reproduces, on nine independent episodes, the controlled negative already
recorded in Phase 4 and Phase 7. Activity **stops at synaptic integration in the
first postsynaptic population**, one synapse downstream of the stimulated sensory
neurons:

- the 232 annotated sensory neurons are driven and spike;
- their spikes reach the first hop as synaptic current (473 of 607 targets in the
  instrumented Phase 4H.4 run, peak 164.443 pA);
- the strongest first-hop target peaks at **−56.926 mV against a −50 mV
  threshold — 6.926 mV short — and does not spike**;
- because no first-hop neuron spikes, **no second-hop current is delivered at
  all** (0 of 3,576 receivers);
- **no motor neuron receives any current** (0 of 805), so the decoder sees zero
  motor spikes, fails its evidence gate, and returns `NEUTRAL`;
- the adapter executes `NEUTRAL` as `NO_ACTION`.

The decoder is **not** broken. A positive control on the same decoder, motor
populations and adapter (Phase 4G.5 condition C) produced 492 motor spikes across
82 motor neurons and JUMP in four of five windows. Pilot 1 failed to feed the
decoder, rather than the decoder failing to act.

This is a result about **one declared model configuration**, not about the living
fly, and not a software defect that a threshold change can fix.

---

## 2. Correction to the spike total

The mission brief and §6/§7 of `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md`
state 72,880 total spikes. The nine stored rows sum to **73,880**:

| seed | ep | updates | neural steps | total spikes | motor spikes |
|---|---:|---:|---:|---:|---:|
| 9001 | 0 | 323 | 10,767 | 4,764 | 0 |
| 9001 | 1 | 620 | 20,667 | 14,348 | 0 |
| 9001 | 2 | 323 | 10,767 | 4,764 | 0 |
| 9002 | 0 | 620 | 20,667 | 14,911 | 0 |
| 9002 | 1 | 426 | 14,200 | 8,396 | 0 |
| 9002 | 2 | 620 | 20,667 | 13,139 | 0 |
| 9003 | 0 | 213 | 7,100 | 2,850 | 0 |
| 9003 | 1 | 426 | 14,200 | 7,856 | 0 |
| 9003 | 2 | 213 | 7,100 | 2,852 | 0 |
| **total** | | **3,784** | **126,135** | **73,880** | **0** |

Every per-episode value in the execution report is correct; only its totals line
is wrong, by exactly 1,000 spikes. The corrected total is used throughout this
report. The stored `episodes.jsonl` remains the authoritative record and was not
edited.

---

## 3. What Pilot 1 actually recorded, and what it did not

Records used (`experiments/results/phase_8/pilot1/pilot1/`):

- `episodes.jsonl` — nine A rows, one per episode;
- `manifest.json` — run identity, design, config and input hashes;
- `pilot_summary.json` — 9/9 rows executed, `estimates_contrasts = false`,
  `evidence_kind = pilot`;
- `pilot_plan.json` — pre-execution plan copy (still labelled construct-only; a
  known label nuance, not a result).

Verified invariants across all nine rows:

| Invariant | Value |
|---|---|
| Condition / role / evidence | `A` / `reference` / `pilot` |
| Termination | `terminated = true`, `truncated = false`, `collision` ×9 |
| Actions | `NO_ACTION` in every update (3,784 total) |
| Motor spikes | 0 in every episode |
| Windows with motor spike | 0 in every episode |
| Decisions with motor spike | 0 in every episode |
| Decoder fallbacks | `{}` in every episode |
| Unmapped / invalid actions | 0 in every episode |
| Neural resets during episode | 0 in every episode |
| Weights before vs after | identical in every episode |
| Weight fingerprint | `4923f0cd45d55fd4cd80d81392974dd5058ca988f18348734d10b45b06d945d5` |
| Edges / excitatory / inhibitory | 1,535,710 / 502,727 / 180,373 |
| Decoder population spikes | `LEFT 0, RIGHT 0, JUMP 0` ×9 |
| Total reward | 47.75 |
| Memory gate (4 GiB) | passed (minimum observed available 4.1997 GiB; 177 samples) |
| Integrity at run time | `integrity.checked = false` (see §12.4) |

### 3.1 Instrumentation gap specific to Pilot 1

`NeuralClosedLoop._summarise` (`environment/live_loop.py:828`) computes
`stimulated_spikes`, `non_stimulated_spikes`, `motor_spikes`, `active_neurons`,
`stimulated_neurons` and `transmitted_spikes` (`environment/live_loop.py:897–901`).
The Pilot 1 stage then persists a
reduced 21-field view (`experiments/phase_8/stages/pilot1_runner.py:201–229`;
the same reduction is applied when `conditions/execute.py:409–432` builds the
row). Consequently **Pilot 1's own artifacts do not contain the
stimulated/non-stimulated split, the active-neuron count, the transmission
count, or any membrane potential.** They contain total, motor and per-population
spikes, actions, rewards, weights and hashes.

The first-hop conclusion for Pilot 1 therefore rests on four independent legs:

1. Pilot 1 used the **same frozen inputs** as the instrumented runs — graph,
   node table, synapse policy, neuron config, sensory mapping, motor decoder and
   plasticity config hashes are byte-identical to the ones recorded in 4H.4
   (table in §13);
2. Pilot 1 used the **same production loop** (`NeuralClosedLoop` over
   `GameEnvironmentAdapter`) and the same 0 pA background / 0 pA noise;
3. the **frozen graph itself** shows no motor neuron at the first hop (§5.2,
   independently re-derived);
4. the **same design was directly measured** in Phase 7 (its summary records
   `stimulated_spikes = 2852`, `non_stimulated_spikes = 0`, `motor_spikes = 0`)
   and in 4H.4 (per-neuron groups, §6).

That is a convergent inference, not a direct per-neuron measurement of Pilot 1.
It is labelled as such in §9.

---

## 4. Sensory stimulation and recruitment (investigation item 1)

The sensory layer is not the failure.

| Fact | Value | Source |
|---|---|---|
| Stimulated neurons | 232 | `configs/banc_sensory_mapping.yaml`; 4H.4 `configuration_verification` |
| Per-feature sizes | 48 / 48 / 24 / 32 / 24 / 32 / 24 | mapping config |
| Overlap with motor neurons | 0 | 4H.4 check `motor_overlap = 0`; independent query |
| Overlap with LEFT/RIGHT/JUMP pools | 0 | independent query |
| Feature current | 200 pA per active feature | mapping config; 4H.4 check `feature_currents_200_pa` |
| Drive timing | zero-order hold, 0.5 ms resolution, 150 ms pulse decay | mapping config; `LiveSensoryDrive` |
| Peak simultaneous summed input, instrumented run | 687.78 pA | 4H.4 `B_actual` |
| Neurons that fired (4H.4, 3.3 s) | 171 / 232 | 4H.4 `stimulated` group |
| Neurons that fired (Phase 7, 3.55 s) | 71 / 232 | Phase 7 per-neuron recording |
| Spikes inside the stimulated set | 3,562 / 3,562 (4H.4); 2,852 / 2,852 (Phase 7) | 4H.4; Phase 7 summary |
| Spikes outside the stimulated set | 0 (both) | 4H.4; Phase 7 summary |

Recruitment is **partial** (71–171 of 232) and depends on drive duration and
pattern. That is a real observation, but it is not the stopping point: the
stimulated neurons do spike, and every spike in the network lies inside the
stimulated set.

An independent reconstruction from the frozen mapping YAML reproduced the same
232-neuron set and the same per-feature sizes; it is a consistency check, not a
new experiment.

---

## 5. Propagation through ascending and descending pathways (item 2)

### 5.1 Instrumented propagation (4H.4 condition `B_actual`, same design)

| Group | Neurons | Receive current | Max current | Max membrane | Deficit to −50 mV | Spikes |
|---|---:|---:|---:|---:|---:|---:|
| Stimulated | 232 | 1 (recurrent) | 17.02 pA | −50.000 mV | 0.000 | 3,562 |
| First hop (non-stimulated) | 607 | 473 | 164.443 pA | −56.926 mV | 6.926 mV | 0 |
| Second hop | 3,576 | **0** | 0 pA | −65.000 mV | 15.000 mV | 0 |
| Descending (all) | 1,316 | 9 | 67.208 pA | −62.158 mV | 12.158 mV | 0 |
| Ascending (all) | 1,849 | 0 | 0 pA | −65.000 mV | 15.000 mV | 0 |
| VNC intrinsic | 12,850 | 0 | 0 pA | −65.000 mV | 15.000 mV | 0 |
| Motor (all) | 805 | **0** | 0 pA | −65.000 mV | 15.000 mV | 0 |
| LEFT / RIGHT / JUMP | 185 / 186 / 20 | 0 / 0 / 0 | 0 pA | −65.000 mV | 15.000 mV | 0 |

The same run recorded 25,332 spike-edge transmissions, of which 9,499 used a
signed edge. Transmission therefore happened; it simply produced no postsynaptic
spike.

### 5.2 Independent structural query of the frozen graph

I re-derived signed reachability from the 232 stimulated neurons on the frozen
`banc_graph_t5.npz` (threshold 5, verified-only sign policy, using the edge
weights of the declared policy). The result reproduces 4H.4 exactly:

| Quantity | Value |
|---|---:|
| Signed outgoing edges from the stimulated set | 662 |
| Unique first-hop targets | 608 |
| Non-stimulated first-hop targets | 607 |
| First-hop targets that are motor neurons | **0** |
| First-hop targets annotated descending | 9 |
| Signed outgoing edges from the first hop | 5,259 |
| Unique second-hop targets | 3,865 |
| Non-stimulated second-hop targets | 3,576 |
| Second-hop targets that are motor neurons | **4** |
| — of those, JUMP / LEFT / RIGHT | 2 / 0 / 0 |
| Motor neurons with at least one signed incoming edge somewhere | 735 / 805 |
| Largest static first-hop signed sum | 167.041 pA (node 125949) |

Three consequences follow:

1. **No motor neuron is a first-hop target.** The sensory set has no direct
   signed synapse onto any of the 805 motor neurons. This is a property of the
   frozen annotation graph, not of the simulation.
2. Motor neurons are reachable, but distally. Only four are reachable at exactly
   two hops, and only two of those are JUMP. LEFT and RIGHT have no second-hop
   route from the sensory set at all.
3. The motor layer is not structurally isolated in general — 735 of 805 motor
   neurons have at least one signed incoming edge from somewhere in the graph.
   The missing route is sensory→motor, not motor→nothing.

The independent query was run against the same frozen artifact whose SHA-256 is
recorded in the Pilot 1 row (`6d47f259…2192`); it changed nothing.

### 5.3 Reading the pathway

```
232 sensory neurons (driven, ~71–171 active)
        │  662 signed edges → 608 targets
        ▼
607 first-hop neurons   ← 473 receive current, peak 164.4 pA
        │                  peak membrane −56.93 mV  (6.93 mV short)
        ✗ no spike
        │
        ▼
3,576 second-hop neurons ← 0 receive current (no presynaptic spikes upstream)
        ▼
805 motor neurons        ← 0 receive current
        ▼
decoder gate (≥5 spikes, ≥3 active)  → false
        ▼
NEUTRAL → NO_ACTION
```

The break is the first-hop current→spike conversion. Everything downstream is
silent by logical consequence, not by an independent second failure.

---

## 6. Synaptic weights, signs and conductance assumptions (item 3)

| Setting | Declared value | Status |
|---|---|---|
| Sign policy | verified-only; ACh/glutamate excitatory, GABA/glycine inhibitory; modulators and conflicts unknown; unknown edges excluded | declared, not measured |
| Signed edges, t5 | 683,100 of 1,535,710 (44.48 %) | structural fact |
| Signed synapses | 8,426,168 of 18,552,546 | structural fact |
| Excluded edges | 852,610 | structural fact |
| Excitatory / inhibitory signed edges | 502,727 / 180,373 | structural fact |
| Weight transform | `5.0 × count**0.75` pA, cap 300 pA | declared calibration |
| Synaptic kinetics | exponential current; τ_exc 5 ms, τ_inh 8 ms, delay 1 ms (effective 1.0 ms at 0.5 ms dt) | declared |
| Passive neuron | C 200 pF, g 10 nS (τ 20 ms), V_rest −65 mV, V_th −50 mV, V_reset −68 mV, refractory 2 ms | declared |
| Background / noise | 0 / 0 pA | declared control choice |

Relevant to the bottleneck:

- **Inhibition is not the cause here.** The signed outgoing weight from the
  stimulated set to its targets includes **0.0 pA of inhibitory weight** (4H.4
  check). The first hop is under-driven, not suppressed.
- **Sign coverage limits the path.** Only 44.48 % of edges carry a modelled
  current, and 852,610 structurally present edges are excluded. A path visible in
  the connectome may therefore carry no current in this model. This is a
  structural-versus-physiological ambiguity, not a bug.
- **Fan-out is low and skewed.** 662 signed edges from 232 neurons is ~2.85 per
  stimulated neuron. First-hop targets have median synaptic current 0 pA, p95
  80.87 pA and maximum 164.44 pA: current is concentrated in a few targets.
- **The weight value is a calibration, not a conductance.** The cap of 300 pA and
  the exponent 0.75 were chosen for the model; no measurement fixes them.

---

## 7. Membrane potentials and spike thresholds along the pathway (item 4)

The decisive measurement is the first hop.

- Resting −65 mV, threshold −50 mV, so 15 mV of depolarisation is required.
- The declared rheobase for a sustained current is `(V_th − V_rest) × g = 15 mV ×
  10 nS = 150 pA`.
- The largest first-hop synaptic current is **164.443 pA**, above the steady-state
  rheobase in magnitude, yet the membrane peaks at **−56.926 mV**: 8.074 mV of
  depolarisation, **6.926 mV short**.
- No first-hop neuron is within 2 mV or 5 mV of threshold; there are zero
  threshold crossings.

Why a peak above 150 pA does not imply a spike: the current is **transient**
(τ_exc 5 ms), not a sustained step. As an order-of-magnitude consistency check,
one exponential event of 164 pA carries `I₀·τ ≈ 0.82 pC`, which on 200 pF is
≈ 4.1 mV; overlapping events bring the peak to ≈ 8.1 mV. A sustained 150 pA step
would eventually charge the membrane to threshold; a 5 ms transient of the same
peak amplitude does not. This check is an approximation for interpretation, not a
new measurement.

Downstream values are then:

- descending: max 67.208 pA → −62.158 mV (12.158 mV short);
- ascending, second hop, motor: 0 pA → −65 mV (15 mV short).

4H.4's controls show the shortfall is not an artefact of one stimulus pattern:

| Control | Non-stimulated spikes |
|---|---:|
| Temporal shuffle (C) | 0 |
| Feature-identity shuffle (D) | 0 |
| Random matched mapping (E) | 0 |
| Constant matched-charge control (F) | 0 |
| Background 50 pA + noise 50 pA (G) | 0 (closest neuron 7.35 mV short) |
| No events (A) | 0 |

So neither the exact timing, the exact mapping, the total charge nor added
background drive rescues the first hop under the declared model.

---

## 8. Motor-neuron input, recruitment and decoder compatibility (items 5–6)

### 8.1 Motor input

- 0 of 805 motor neurons receive synaptic current in 4H.4.
- 0 of 805 spike in 4H.4, Phase 7 and Pilot 1.
- LEFT 185, RIGHT 186, JUMP 20: all zero in every run and every episode.
- This is a strict consequence of the spike-driven synapse model: with no
  presynaptic spikes upstream, the synaptic current is identically zero. Motor
  silence is caused upstream, not at the motor membrane.

### 8.2 Population mapping

| Property | Value |
|---|---|
| Motor neurons (annotation-defined) | 805 |
| Assigned to LEFT / RIGHT / JUMP | 391 (185 / 186 / 20) |
| Unassigned motor neurons | 414 |
| Unsupported channels | ROLL, DUCK (reported, not invented) |
| Mapping basis | published BANC effector annotations; no hand-assigned neuron |

### 8.3 Decoder

| Property | Value |
|---|---|
| Window | 50 ms, half-open |
| Signal | active-neuron fraction per population |
| Gate | ≥ 5 spikes and ≥ 3 active neurons |
| Activation threshold | 0.20 |
| Priority | LEFT → RIGHT → JUMP |
| No qualifying population | `NEUTRAL` |
| Adapter mapping | `NEUTRAL` → `NO_ACTION` (`supported: true`, `unmapped: false`) |

Pilot 1 invoked the decoder on all 3,784 updates (one decision per update), received
zero motor spikes, and returned `NEUTRAL` every time. `NO_ACTION` is therefore the
**specified** output for that input, not an error path: the recorded
`fallback_reasons` are empty and no action was unmapped or invalid.

### 8.4 Positive control — the decoder does work

Phase 4G.5 drove 64 VNC-intrinsic neurons directly at 300 pA for 200 ms (a
one-synapse route to motor tissue) through the same decoder, populations and
adapter:

| Condition | Total spikes | Non-stimulated | Motor spikes | Active motor neurons | Decoded states |
|---|---:|---:|---:|---:|---|
| A no stimulation | 0 | 0 | 0 | 0 | NEUTRAL ×5 |
| B descending candidate | 781 | 61 | 18 | 3 (all unassigned) | NEUTRAL ×5 |
| **C VNC intrinsic** | **1,296** | **556** | **492** | **82** | **JUMP ×4, NEUTRAL ×1** |
| D random matched | 704 | 0 | 0 | 0 | NEUTRAL ×5 |
| E shuffled assignment | 728 | 16 | 0 | 0 | NEUTRAL ×5 |
| F background/noise only | 0 | 0 | 0 | 0 | NEUTRAL ×5 |

Condition C cleared both gates and produced JUMP four times (LEFT 0.1459, RIGHT
0.1720, JUMP 0.6000 over the active window). Threshold and weight sensitivity
tables in the same report (threshold 1/5/10; 300/600 pA; capped/uncapped; sign
fallbacks) all still produce JUMP under direct VNC drive, so the decoder is not a
knife-edge calibration.

Conversely, direct **descending** drive (condition B) produced 18 motor spikes in
only 3 motor neurons, all *unassigned* — none in LEFT/RIGHT/JUMP. The annotated
decoder pools sit distal to the descending layer, which is consistent with the
sensory route stopping even earlier.

**Conclusion for item 6:** the mapping and decoder are compatible with the
recorded motor populations; they are not the bottleneck. The bottleneck is the
absence of motor-spike input.

---

## 9. Consistency with Phase 4 and Phase 7 (item 7)

| | Phase 4H.4 `B_actual` | Phase 7 closed loop | Phase 8 Pilot 1 (A) |
|---|---|---|---|
| Stimulus | archived event pulses, 200 pA/feature | live game, zero-order hold, 200 pA/feature | live game, zero-order hold, 200 pA/feature |
| Duration | 3,300.5 ms | 3,550 ms | 3,550–10,333.5 ms |
| Updates | — | 213 | 213–620 |
| Total spikes | 3,562 | 2,852 | 2,850–14,911 |
| Stimulated spikes | 3,562 (100 %) | 2,852 (100 %) | not persisted |
| Non-stimulated spikes | 0 | 0 | not persisted |
| Motor spikes | 0 | 0 | 0 |
| First-hop receivers | 473 / 607 | — | — |
| First-hop peak current | 164.443 pA | — | — |
| First-hop peak membrane | −56.926 mV | — | — |
| Deficit to threshold | 6.926 mV | — | — |
| Second-hop receivers | 0 / 3,576 | — | — |
| Motor current | 0 / 805 | — | — |
| Decoder output | NEUTRAL ×67 | NO_ACTION ×213 | NO_ACTION ×3,784 |
| Weights unchanged | fixed | true | true |
| Determinism | 6/6 repeat pairs hash-equal | true | seeds fixed per row |

Phase 7 is the closest comparator: it used environment seed 42 and neural seed
20261116, whereas Pilot 1 derives condition-A network seeds as
`SeedSequence([20261116, 1, seed, 2])` (`experiments/phase_8/seeds.py`). It is a
**same-design replication**, not an identical replica. Phase 7's own summary
already records the split directly (`stimulated_spikes = 2852`,
`non_stimulated_spikes = 0`, `motor_spikes = 0`), so the first-hop conclusion does
not depend on re-analysing its NPZ. An independent per-neuron pass over that NPZ
agrees: 2,852 spikes, all in the stimulated set, 71 distinct firing neurons, all
stimulated, none motor.

Phase 4H.4 reports 47/47 configuration checks passing, its recorded input-hash
checks match the same frozen inputs Pilot 1 used, and it reports 6/6
deterministic repeat pairs. Its
qualitative result is the same as Phase 7's and Pilot 1's.

The earlier `reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md`
(2026-11-17) reached the same stop point for the single Phase 7 run. Pilot 1 does
not reveal a new mechanism; it shows the same mechanism persisting across three
seeds, three episodes each, and a 2.9× range of episode durations.

---

## 10. Exact point of failure, ranked

1. **Primary stop — first-hop current→spike conversion.** 473 of 607 first-hop
   targets receive current (peak 164.443 pA), the best membrane peak is
   −56.926 mV, and no first-hop neuron spikes. This is the exact point where
   propagated activity ends.
2. **Consequent stop — second hop.** Zero first-hop spikes ⇒ zero second-hop
   current (0/3,576). Not an independent failure.
3. **Consequent stop — motor input.** Zero current in 0/805 motor neurons; zero
   motor spikes; decoder gate false.
4. **Structural precondition — route depth.** No motor neuron is a first-hop
   target; only 4 are reachable at two hops (2 JUMP, 0 LEFT/RIGHT). Even a
   hypothetical first-hop rescue would not immediately reach a decodable
   LEFT/RIGHT population at hop 2; propagation beyond two hops is conditional and
   cannot be bounded from structure alone.
5. **Not failures:** sensory recruitment (real, though partial), synaptic
   transmission (25,332 transmissions), graph connectivity (608 first-hop
   targets), sign coverage *for this subset* (662 signed edges, 0 pA outgoing
   inhibition), decoder and adapter.

---

## 11. Structural versus physiological uncertainty

**Fixed by the frozen structure (facts about the graph):**

- no motor neuron is a first-hop target of the 232-neuron sensory set;
- 662 signed outgoing edges / 608 first-hop targets / 607 non-stimulated;
- 4 motor neurons at two hops (2 JUMP, 0 LEFT/RIGHT);
- 735/805 motor neurons have some signed incoming edge from elsewhere;
- 683,100 of 1,535,710 edges are signed; 852,610 are excluded;
- LEFT 185 / RIGHT 186 / JUMP 20 / 414 unassigned motor neurons.

**Dependent on declared physiological assumptions (not measured):**

- weight transform, scale (5 pA) and cap (300 pA);
- LIF capacitance, leak, threshold, reset, refractory;
- synaptic time constants and 1 ms delay;
- verified-only sign policy and exclusion of unknown edges;
- the sensory mapping and the 200 pA feature-current scale;
- 0 pA background and 0 pA noise.

The statement *"activity stops at the first hop"* is a fact **about this model
configuration**. The statement *"the fly's first hop would not spike"* is **not
established**. The 6.93 mV margin is model-specific and would move if any
physiological assumption above changed. What 4H.4's controls do support is that
within the declared model the stop is not specific to the timing, the random
mapping, the total charge, or the absence of background drive.

The most load-bearing assumptions are the synaptic weight scale/cap and the
passive LIF threshold/leak, because they alone convert 164 pA of transient
current into an 8 mV rather than 15 mV depolarisation. Changing any of them
creates a different model and therefore a different experiment, which is why none
was changed here.

---

## 12. Confirmed facts, hypotheses, unknowns

### 12.1 Confirmed facts (measured in Pilot 1)

- 73,880 total spikes over nine episodes; 0 motor spikes; 0 windows and 0
  decisions with a motor spike; `NO_ACTION` on all 3,784 updates.
- Weights identical before and after every episode; fingerprint `4923f0cd…45d5`.
- No decoder fallbacks, no unmapped or invalid actions, no neural resets.
- All nine episodes terminated by collision (`terminated = true`,
  `truncated = false`), none reached the 900-update cap.
- All seven frozen input hashes and all three config hashes match the declared
  values.
- The execution report's 72,880 total is a totals-line arithmetic error; the
  per-row values and the store are correct.

### 12.2 Confirmed facts (measured in Phase 7 and Phase 4H.4, same design)

- Every spike lies in the stimulated set; 0 non-stimulated spikes.
- First-hop peak current 164.443 pA; peak membrane −56.926 mV; deficit 6.926 mV;
  0 threshold crossings; 473/607 receivers.
- Second hop: 0 receivers. Descending: 9 receivers, max −62.158 mV. Motor: 0
  receivers, 0 spikes.
- 0.0 pA signed inhibitory weight from the stimulated set.
- 25,332 transmissions (9,499 signed), so transmission is not the failure.
- 4H.4: 47/47 configuration checks pass; six input hashes match Pilot 1; 6/6
  repeat pairs hash-equal.

### 12.3 Confirmed by independent structural query (frozen graph)

- 662 signed edges → 608 targets → 607 non-stimulated → **0 motor**.
- 5,259 signed edges from the first hop → 3,865 second-hop targets → 3,576
  non-stimulated → **4 motor (2 JUMP, 0 LEFT/RIGHT)**.
- 735/805 motor neurons have at least one signed incoming edge somewhere.

### 12.4 Hypothesis (not measured in Pilot 1 itself)

- **H1 — Same first-hop mechanism in Pilot 1.** Because Pilot 1 used the same
  frozen inputs, the same production loop, and the same zero background/noise,
  and because it produced the same observable signature (0 motor spikes, 0
  fallbacks, fixed weights), its activity almost certainly stopped at the first
  hop exactly as Phase 7 and 4H.4 did. Directly verifying this would require
  re-running with the full summary persisted, which was not done.

### 12.5 Derived consequence for B (plasticity arm)

Under the declared eligibility convention, a trace is created only on edges whose
presynaptic packet arrives **while the postsynaptic cell spikes**
(`plasticity/traces.py:326–345`, `coincident_edges`, used at
`plasticity/engine.py:134`). With zero first-hop spikes, no eligibility is
created on sensory→first-hop edges. Therefore condition B cannot strengthen the
very synapses whose failure causes the block. This is a code-level deduction
about the model, not a hypothesis about biology. It predicts C2 = B − A will be
identically zero when the movement policy is constant (see §13).

### 12.6 Unknowns

- Pilot 1's own stimulated/non-stimulated split, per-neuron active fraction,
  transmission count and membrane traces (not persisted; §3.1).
- Whether any motor neuron received sub-threshold current in Pilot 1 (expected
  zero, because the synapse model is spike-driven, but not recorded).
- Whether a first-hop rescue, if it occurred, would propagate far enough to
  recruit LEFT/RIGHT; structure alone cannot bound hops beyond two.
- Whether F's readout could learn anything from an all-zero feature vector — it
  cannot learn feature weights (§13.2), but the realised constant policy under
  training has not been measured because Pilot 2 was not run.

---

## 13. Implications for Pilot 2

Pilot 2 is planned as arms A, B, C, F, F_beta, A_prime, C_prime; 3 seeds ×
3 episodes; contrasts C1 = F − A, C2 = B − A, C3 = A − C, C4 = F − F_beta.

### 13.1 Operational readiness

`experiments/phase_8/stages/pilot2.py::pilot2_readiness` returns
`ready = false` with three blockers:

1. **P2-G** — no certified random graph exists for pilot seeds 9001/9002/9003;
   certification covers the campaign seeds only, and a campaign graph may not be
   substituted. Blocks C and C′.
2. **P2-A (loader)** — the training-artifact loader accepts only seeds declared in
   `seeds.campaign`, and no pilot seed is declared there. Trained F, F_beta and E
   artifacts for the pilot seeds cannot be loaded.
3. **P2-A (artifacts)** — no trained artifact directory exists for the pilot
   seeds under the training root.

The independent 4 GiB memory gate **passes** (Pilot 1 observed a 4.1997 GiB
minimum; the pilot summary reports 5.745 GiB available at start), so memory is not
a blocker.

### 13.2 Scientific degeneracy of the planned contrasts

Given the motor-null behaviour recorded in Pilot 1, the following are consequences
of the code and the stored result, not speculation:

- **A, B, C, A′, C′ all use `fixed_decoder`** (`configs/phase_8/conditions.yaml`).
  With zero motor spikes, each returns `NEUTRAL` → `NO_ACTION` on every update.
  Per paired environment seed the action sequence is therefore the same constant
  policy across those arms, and survival is determined by the game and that
  policy, not by neural computation.
- **A′ ≡ A is provably exact** when no eligibility is created (η = 0 anyway);
  the identity check passes trivially and does not test pipeline sensitivity.
  The same applies to C′ ≡ C on a randomized graph.
- **C2 = B − A is expected to be identically zero.** B's only change would be
  synaptic weights, but §12.5 shows no eligibility forms on the blocked edges,
  and with the same actions the game trajectory is the same. A null contrast
  cannot test H1.
- **C3 = A − C is policy-null.** If C's randomized graph is also motor-null (very
  likely — same sensory mapping, same first-hop problem), C3 compares two
  `NO_ACTION` policies and reflects game mechanics only.
- **F = linear readout on motor features.** The default feature is
  `active_fraction` for the four action populations
  (`readout/features.py`). With zero motor spikes the feature vector is **exactly
  zero** for every decision. Consequently:
  - logits = biases, constant across all decisions;
  - the REINFORCE gradient with respect to feature weights is
    `(onehot − p)·xᵀ = 0`, so the **feature weights never move**; only the output
    biases can change;
  - F reduces to a bias-only policy — which is precisely the declared definition
    of **F_beta** (`bias_only_readout`, `state_independent: true`, feature
    weights fixed at 0).
- **C1 = F − A** therefore compares a constant, reward-trained action policy
  against a constant `NO_ACTION` policy. It cannot demonstrate that the readout
  extracts motor information, which is the stated purpose of F and H3.
- **C4 = F − F_beta** compares two constant-bias policies. With identically zero
  inputs, it cannot isolate "use of motor information beyond biases" because
  there is no motor information to use.
- **U7 dispersion** is estimated from contrast values. If C1–C4 are null or
  constant, the dispersion endpoints are degenerate and cannot produce a
  meaningful one-sided upper confidence limit.

This is not an argument that Pilot 2 is useless: it can still exercise the
pipeline, the training loop and the identity checks. It is an argument that the
planned **motor-information contrasts would not test the hypotheses they are
written for** while the motor layer is silent.

### 13.3 Options that would change this (owner decisions, not taken here)

- a declared, pre-registered sensitivity study of the first-hop block (for
  example a declared and unchanged alternative sign/weight or passive-property
  policy, reported in full, not selected post hoc);
- measured sign/conductance, passive/synaptic properties, or a measured
  sensory→neuron / action→neuron map, none of which exists today;
- redefining Pilot 2's estimands so that the motor-null outcome is the object of
  inference (e.g. whether any arm produces non-zero motor activity at all),
  rather than a contrast in survival;
- explicitly accepting that Pilot 2 tests software viability only, and reporting
  the degeneracy alongside it.

None of these is a parameter change I may make, and none was made.

---

## 14. Pilot 2 readiness recommendation

**Pilot 2 should not be authorized in its current form. Recommendation: NOT
READY.**

Two independent reasons:

1. **Operational** — three blockers remain (P2-G certified graph, P2-A loader
   contract, P2-A trained artifacts). These are structural declarations, not
   things to work around by substituting a campaign seed or an untrained
   artifact.
2. **Scientific** — even if the operational blockers were cleared, the planned
   grid is degenerate on a motor-null substrate: A/B/C/A′/C′ are fixed-decoder
   arms whose movement policy is constant, and F/F_beta reduce to bias-only
   policies because their input vector is identically zero. C1–C4 would be null
   or uninterpretable, and U7 dispersion could not be formed as intended.

**Required before any Pilot 2 authorization:** an explicit owner decision on how
to handle the motor-null degeneracy (remediate the bottleneck under a new
pre-registered study, redefine the estimands, or accept viability-only scope and
report the degeneracy). That decision is outside this read-only investigation.

---

## 15. What would legitimately change the conclusion

Each requires external evidence and a new pre-registered experiment; none was
run and none is recommended as an ad-hoc change:

- target-specific functional sign and conductance (measured, not predicted);
- measured passive and synaptic properties for the relevant cell types;
- a measured sensory-feature→neuron map instead of the declared mapping;
- a validated action→neuron mapping instead of annotation-defined pools;
- a later BANC release with fuller transmitter/annotation coverage;
- a declared and unchanged alternative policy reported as a sensitivity
  condition, with every condition reported.

---

## 16. Limits and non-claims

- This is a read-only analysis of existing artifacts. No simulation was re-run
  and no new measurement was produced. The independent structural query only
  recomputed reachability from the frozen graph, without writing to it.
- The first-hop mechanism is **directly measured** in Phase 4H.4 and Phase 7 and
  **inferred** for Pilot 1 itself, because Pilot 1 did not persist the split
  (§3.1). The inference is convergent but is not a per-neuron measurement of
  Pilot 1.
- The 6.926 mV margin and the 164.443 pA peak are values of the declared model.
  They are not measured fly conductances or voltages.
- `NO_ACTION`, LEFT, RIGHT and JUMP are decoder labels executed because the
  controlled game accepts them. They are not biological motor commands, and
  nothing here is evidence about a living fly.
- The 73,880 total corrects a totals-line arithmetic error in the execution
  report; the stored rows were not modified.
- Phase 7 is a same-design replication with different seeds, not an identical
  replica of any Pilot 1 episode.
- A pre-existing protected-baseline drift (`README.md`, and a docstring-only
  change in `motor/__init__.py` from commit `3c74ae8`, 2026-11-19, before
  Pilot 1) means the run manifest has `integrity.checked = false`. It is
  unrelated to the motor bottleneck and is recorded, not resolved, here.
- No file was staged, committed or pushed. This report is a new untracked file;
  all prior artifacts are preserved.

---

## 17. Reproduction metadata (read-only)

### 17.1 Frozen inputs shared by Pilot 1, Phase 7 and Phase 4H.4

| Input | SHA-256 |
|---|---|
| Graph `banc_graph_t5.npz` | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Node table | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Synapse policy | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |
| Neuron config | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` |
| Motor decoder | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| Sensory mapping | `64c716a42c44ded58c77fccdcd865b0a9732a06b86019d673e6fb4c902dfc4ff` |
| Plasticity | `616288a40bf864185c33f92a99742be8dd49e62773cbb58cb9287414ad9e5f70` |

Pilot 1 config hashes: environment `b391ecf7…81dc`, campaign `b9a2d3d5…7e19`,
conditions `9a93f047…f671`.

### 17.2 Pilot 1 run identity

- REV4 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`,
  SHA-256 `e4aa9e0f…1547c` (unchanged).
- D1 record `5c183c99…d489`; D2 record `b5b0c229…7327`
  (`accepts_g3_deviation = false`, `weakens_graph_certification = false`).
- Run directory: `experiments/results/phase_8/pilot1/pilot1/`.
- Master seed 20261116; campaign seeds 9001/9002/9003; three episodes each.
- 9 rows executed, 9 stored, 0 contrast estimates, not merged into the campaign.

### 17.3 Primary sources read

- `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`, `manifest.json`,
  `pilot_summary.json`, `pilot_plan.json`
- `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md`,
  `reports/PHASE_8_PILOT1_EXECUTION.json`
- `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json`
- `reports/PHASE_4G5_MOTOR_DECODER_INTEGRATION.md`
- `reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md`
- `experiments/results/phase_7/neural_closed_loop.json` and
  `neural_closed_loop_activity.npz`
- `environment/live_loop.py`, `environment/motor_activity.py`
- `experiments/phase_8/conditions/execute.py`,
  `experiments/phase_8/stages/pilot1_runner.py`,
  `experiments/phase_8/stages/pilot2.py`, `experiments/phase_8/seeds.py`
- `motor/populations.py`, `motor/motor_decoder.py`
- `readout/features.py`, `readout/controller.py`
- `brain/synapse_model.py`, `brain/banc_synapse_policy.py`
- `plasticity/traces.py`, `plasticity/engine.py`
- `configs/neuron_config.yaml`, `configs/banc_synapse_policy.yaml`,
  `configs/banc_sensory_mapping.yaml`, `configs/motor_decoder.yaml`,
  `configs/phase_7_closed_loop.yaml`, `configs/phase_8/environment.yaml`,
  `configs/phase_8/conditions.yaml`

---

## 18. Summary for the owner

Pilot 1 is a clean, deterministic, fully stored nine-episode run whose network is
alive (73,880 spikes) and whose motor layer is silent. The silence is not a
decoder, adapter, clock, weight-drift or fallback bug: it is the declared model's
first-hop under-excitation, measured at 6.926 mV short of threshold, with a
positive control proving the decoder acts when motor spikes exist. The same
result is already in Phase 4H.4 and Phase 7; Pilot 1 shows it persists across
seeds and episode lengths in the Phase 8 A arm.

Pilot 2 is **not ready**, operationally (P2-G, P2-A ×2) and scientifically (the
planned contrasts are degenerate on a motor-null substrate). An owner decision on
the motor-null degeneracy is required before any Pilot 2 authorization. No
parameter, graph, protocol or authorization record was changed to produce this
report.
