# Phase 4G.5 — Motor Decoder Integration

Status: **PASS (execution) with scientific limitations**
Date: 2026-11-08

This phase couples the separate BANC propagation pathway to the unchanged
Phase 4F motor decoder. It asks whether connectivity-selected upstream
stimulation can recruit motor populations and produce a decoded action that is
absent in matched controls. It does not establish biological motor control.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4g/run_phase_4g_experiments.py` | Runs conditions A–F and all sensitivity variants |
| `experiments/results/phase_4g/phase_4g_experiment.json` | Full records, hashes, per-window decoder output |
| `experiments/phase_4g/run_sign_sensitivity.py` | Sign-flip addendum for condition C |
| `experiments/results/phase_4g/phase_4g_sign_sensitivity.json` | Sign-sensitivity result |

## 1. Design

Pipeline: BANC v888 threshold-5 graph → signed edges → LIF/synapse simulation →
spike recorder → unchanged Phase 4F populations and decoder → LEFT / RIGHT /
JUMP / NEUTRAL.

Fixed parameters across the primary conditions:

| Parameter | Value |
| --- | --- |
| Graph threshold | 5 |
| Duration | 300 ms |
| Time step | 0.5 ms |
| Seed | 20261108 |
| Stimulus | 300 pA, 50–250 ms |
| Decode span | 50–300 ms |
| Decoder window / step | 50 ms / 50 ms |
| Activation threshold | 0.20 |
| Release threshold | 0.10 |
| Gates | ≥ 5 spikes and ≥ 3 active neurons |
| Neuron model | Unchanged Phase 2 LIF defaults |
| Synapse model | Unchanged exponential currents, 5 ms / 8 ms |
| Weight policy | `min(5.0 × count^0.75, 300 pA)` |

No motor neuron is stimulated. No decoder threshold, population rule or
priority order was changed. The decoder configuration and populations are read
from `configs/motor_decoder.yaml` and `motor/populations.py` without edits.

Scientific status: LEFT, RIGHT and JUMP are annotation-derived decoder labels;
they are not identified motor commands. Structural edges and synapse counts are
not conductances. A decoded action is not evidence of behaviour.

## 2. Candidate definitions

All candidates are non-motor, verified-excitatory neurons, so the comparison
isolates structural position rather than sign resolvability. Sixty-four neurons
per group, matching the Phase 4G.4 smoke test.

| Group | Rule | Eligible pool | Selected | Edges to motor | Synapses to motor | Motor overlap |
| --- | --- | --- | --- | --- | --- | --- |
| B — descending candidate | Top descending neurons ranked by direct motor synapses (Phase 4E direct pathway) | 141 | 64 | 645 | 9,832 | 0 |
| C — VNC intrinsic candidate | Top VNC intrinsic neurons ranked by direct motor synapses (Phase 4E intermediate population) | 5,622 | 64 | 1,767 | 64,986 | 0 |
| D — random matched | Random verified-excitatory non-motor neurons, excluding B and C | 53,829 | 64 | 38 | 1,075 | 0 |
| E — shuffled assignment | Random verified-excitatory descending neurons, excluding B | 77 | 64 | 47 | 393 | 0 |

Group D is dominated by optic-lobe intrinsic neurons (47/64), so it is a fair
matched-size random control but not a region-matched one. Group E is the
remaining descending pool after removing the connectivity-ranked 64; with 77
eligible neurons, it samples almost the entire non-selected descending pool.

Candidate groups were fixed before any simulation output was inspected. They
are structural candidates, not identified command neurons.

## 3. Conditions

| Condition | Input | Background / noise |
| --- | --- | --- |
| A — no stimulation | None | 0 / 0 pA |
| B — descending candidate | 64 neurons, 300 pA, 50–250 ms | 0 / 0 pA |
| C — VNC intrinsic candidate | 64 neurons, 300 pA, 50–250 ms | 0 / 0 pA |
| D — random matched | 64 neurons, 300 pA, 50–250 ms | 0 / 0 pA |
| E — shuffled assignment | 64 neurons, 300 pA, 50–250 ms | 0 / 0 pA |
| F — background / noise only | None | 50 / 50 pA |

Condition F is the only condition with a stochastic term. Conditions A–E are
deterministic by construction.

## 4. Primary results

| Condition | Total spikes | Active neurons | Non-stimulated spikes | Motor spikes | Active motor neurons | Decoded states (5 windows) |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0 | 0 | 0 | 0 | 0 | NEUTRAL ×5 |
| B | 781 | 77 | 61 | 18 | 3 | NEUTRAL ×5 |
| C | 1,296 | 164 | 556 | 492 | 82 | JUMP ×4, NEUTRAL ×1 |
| D | 704 | 64 | 0 | 0 | 0 | NEUTRAL ×5 |
| E | 728 | 69 | 16 | 0 | 0 | NEUTRAL ×5 |
| F | 0 | 0 | 0 | 0 | 0 | NEUTRAL ×5 |

**Only condition C recruited the decoder populations.** It produced 492 motor
spikes across 82 motor neurons. Of those, 71 neurons belong to LEFT (27), RIGHT
(32) and JUMP (12); the remaining 11 are unassigned motor neurons. All 556
non-stimulated spikes are downstream activity: 492 motor and 64 non-motor.

**Condition B produced no decoder-population activity.** Its 18 motor spikes
and 3 active motor neurons were all unassigned motor neurons, outside LEFT,
RIGHT and JUMP. The direct descending candidate therefore recruited some motor
tissue but not the annotated decoder pools.

**Conditions D and E produced no motor spikes at all.** D's 704 spikes are
entirely from the 64 stimulated neurons. E produced 712 stimulated spikes and
16 downstream spikes but none in motor neurons.

**Baselines are silent.** A and F produced zero spikes. There is no spontaneous
motor activity under this model and policy, even with 50 pA background and
50 pA noise.

## 5. Decoder output for condition C

| Window | LEFT | RIGHT | JUMP | State | Active actions |
| --- | --- | --- | --- | --- | --- |
| 50–100 ms | 0.1297 | 0.1183 | 0.5500 | JUMP | JUMP |
| 100–150 ms | 0.1351 | 0.1505 | 0.6000 | JUMP | JUMP |
| 150–200 ms | 0.1351 | 0.1344 | 0.6000 | JUMP | JUMP |
| 200–250 ms | 0.1297 | 0.1505 | 0.6000 | JUMP | JUMP |
| 250–300 ms | 0.0000 | 0.0000 | 0.0000 | NEUTRAL | none |

Scores are the gated active-neuron fractions. LEFT and RIGHT clear the evidence
gates (24–25 and 22–28 active neurons, respectively) but stay below the 0.20
activation threshold. JUMP clears both with 11–12 active neurons out of 20.

Over the whole 50–300 ms span, the unique active fractions are LEFT 0.1459
(27/185), RIGHT 0.1720 (32/186) and JUMP 0.6000 (12/20). The JUMP pool is small,
so a high fraction is easier to reach; the 0.20 threshold and gates were
declared in Phase 4F before this experiment, and were not adjusted.

The final window is neutral because the stimulus ends at 250 ms and activity
decays quickly. NEUTRAL is preserved and reported; it is not treated as an
error.

## 6. Determinism

Every condition was run twice with identical parameters. Both the spike hash
and the decision hash matched in all six conditions.

| Condition | Spike hash match | Decision hash match |
| --- | --- | --- |
| A | yes | yes |
| B | yes | yes |
| C | yes | yes |
| D | yes | yes |
| E | yes | yes |
| F | yes | yes |

Conditions A–E contain no stochastic term. Condition F is seeded and reproduced
exactly. No nondeterminism was observed.

## 7. Sensitivity

All variants keep the decoder thresholds, populations and priority unchanged.

### 7.1 Graph threshold

| Threshold | Spikes | Motor spikes | States | Max JUMP score |
| --- | --- | --- | --- | --- |
| 1 | 1,399 | 564 | JUMP ×4, NEUTRAL ×1 | 0.65 |
| 5 (primary) | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 | 0.60 |
| 10 | 1,253 | 456 | JUMP ×4, NEUTRAL ×1 | 0.60 |

The decoded action is stable across edge thresholds, although spike and motor
counts change. Threshold 1 took substantially longer to simulate because more
edges and more active neurons are present.

### 7.2 Stimulus intensity

| Current | Spikes | Motor spikes | States | Max LEFT / RIGHT / JUMP |
| --- | --- | --- | --- | --- |
| 100 pA | 0 | 0 | NEUTRAL ×5 | 0 / 0 / 0 |
| 300 pA (primary) | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 | 0.135 / 0.151 / 0.60 |
| 600 pA | 3,493 | 1,645 | JUMP ×5 | 0.292 / 0.333 / 0.90 |

At 100 pA the stimulated neurons do not fire because the current is below the
150 pA rheobase. At 600 pA all three populations cross the 0.20 threshold in at
least one window; JUMP still has the highest score and remains primary. The
decoded primary action is stable in this range, but the number of active
populations is not.

### 7.3 Weight transform

| Transform | Spikes | Motor spikes | States |
| --- | --- | --- | --- |
| power 0.75, cap 300 pA (primary) | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 |
| power 0.75, uncapped | 1,281 | 481 | JUMP ×4, NEUTRAL ×1 |
| linear, scale 0.5, cap 300 pA | 723 | 5 | NEUTRAL ×5 |
| power 1.0, scale 0.5, cap 300 pA | 723 | 5 | NEUTRAL ×5 |
| log1p, scale 10, uncapped | 755 | 0 | NEUTRAL ×5 |
| power 0.5, scale 5, cap 300 pA | 740 | 0 | NEUTRAL ×5 |

The result is **not transform-invariant**. The primary and uncapped power
transforms recruit motor pools; the weaker linear, log1p and power-0.5
transforms do not. This is the most important sensitivity in Phase 4G: the
decoded action depends on a declared structural-to-current calibration, not on
structure alone.

### 7.4 Unknown-edge policy and predicted labels

| Variant | Spikes | Motor spikes | States |
| --- | --- | --- | --- |
| Unknown edges retained with zero weight | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 |
| Predicted fallback enabled | 1,271 | 471 | JUMP ×4, NEUTRAL ×1 |

Retaining unknown-sign edges with zero weight produced a bit-identical spike
hash to exclusion, as documented in Phase 4G.2. Enabling predicted labels
changed the spike count slightly but not the decoded action.

### 7.5 Seed

Conditions A–E have no noise, so seed changes cannot affect them. The
background/noise control F produced zero spikes under seeds 20261108, 1 and 2.
Spike-count range 0, active-neuron range 0, and all five windows NEUTRAL under
every seed. No seed-dependent variability was observed, because there was no
spontaneous activity to vary.

### 7.6 Decoder window

| Window / step | JUMP windows | NEUTRAL windows | Max JUMP score |
| --- | --- | --- | --- |
| 25 ms / 25 ms | 7 | 3 | 0.55 |
| 50 ms / 50 ms (primary) | 4 | 1 | 0.60 |
| 100 ms / 100 ms | 2 | 1 | 0.60 |

The primary action is JUMP under every window size. The number of windows and
the neutral fraction change with window length, as expected.

### 7.7 Sign

The addendum flips the 64 stimulated condition-C neurons from verified
excitatory to verified inhibitory, changing nothing else.

| Variant | Spikes | Non-stimulated spikes | Motor spikes | States |
| --- | --- | --- | --- | --- |
| C, excitatory (primary) | 1,296 | 556 | 492 | JUMP ×4, NEUTRAL ×1 |
| C, inhibitory | 605 | 0 | 0 | NEUTRAL ×5 |

The stimulated neurons still fire under direct current (605 spikes), but no
downstream neuron fires. The decoded result therefore depends entirely on the
excitatory sign prior applied to the presynaptic candidate neurons. Sign is a
model prior, not a measured postsynaptic effect.

## 8. Answers to the Phase 4G scientific questions

1. **Can neural propagation be observed?** Yes, in condition C: 556 of 1,296
   spikes were non-stimulated and 82 motor neurons were active. It is not
   universal: B, D, E and the baselines did not recruit the decoder pools.
2. **Are motor populations activated?** Yes, in C: 71 LEFT/RIGHT/JUMP motor
   neurons and 11 unassigned motor neurons.
3. **Do LEFT, RIGHT and JUMP differ?** Yes. Unique active fractions over the
   decode span are 14.6 %, 17.2 % and 60.0 %. Per-window LEFT/RIGHT scores stay
   below the 0.20 threshold; JUMP is above it.
4. **Does the decoder distinguish them?** It returns JUMP in four of five
   windows and NEUTRAL after the stimulus. Every matched control returns
   NEUTRAL. The distinction exists in this sample and is not universal.
5. **Is there non-motor activity?** Yes: 82 of 164 active neurons are non-motor
   (64 stimulated plus 18 other non-motor), and 64 non-stimulated non-motor
   spikes occur.
6. **Is there baseline motor activity?** No. Conditions A and F produce zero
   spikes with and without background/noise.
7. **Is the result stable across seeds?** Conditions A–E are deterministic;
   the noise-only control F is silent under three seeds, so seed variability is
   zero rather than demonstrated stability of an active state.
8. **Is it threshold-sensitive?** The decoded action is stable across graph
   thresholds 1, 5 and 10, but counts change by up to about 20 %.
9. **Is it sign-sensitive?** Yes. Flipping the stimulated sign to inhibitory
   removes all downstream and motor activity and returns NEUTRAL.
10. **Is it weight-sensitive?** Yes, strongly. The action survives the primary
    and uncapped power transforms but disappears under linear, log1p and
    power-0.5 transforms.
11. **Is it distinguishable from matched random stimulation?** Yes in this
    sample: C produces 492 motor spikes, D produces 0, E produces 0.
12. **Does it survive shuffled controls?** Yes in this sample: E, the shuffled
    descending assignment, is NEUTRAL. The signal is tied to the
    connectivity-ranked VNC intrinsic candidate, not to stimulation alone.

## 9. Runtime and memory

Per-condition simulation runtime was 2.28–3.30 s for 300 ms (about 182–264
simulated steps per second). Retained arrays were about 86.3 MB per run:
graph 41.4 MB, policy 12.0 MB, neuron state 2.0 MB, synapse state 15.7 MB
(including 2.6 MB delay buffers) and a 15.3 MB preallocated spike recorder.

The full suite's recorded wall time was 5,795.5 s. This is wall-clock time under
background execution, not a benchmark: per-run simulation time was a few
seconds, and the threshold-1 sensitivity variant dominated because more edges
and neurons were active. Process RSS in the Phase 4G.4 smoke run was about
197–200 MB with a peak working set of about 265–269 MB.

## 10. Scientific interpretation and limitations

- The one positive result is conditional: 64 verified-excitatory VNC intrinsic
  neurons selected by direct motor synapses, a declared weight transform, and
  the primary sign policy. Changing the transform, the sign, or the intensity
  can remove it.
- The negative descending result is equally informative: connectivity-ranked
  descending neurons recruited only unassigned motor neurons, not the decoder
  populations. A larger or differently selected descending group might differ;
  this experiment does not establish that.
- Most BANC neurons are unannotated (about 62 %) and most edges are excluded by
  the verified-only policy. The result describes the signed subnetwork, not the
  whole connectome.
- The JUMP pool has 20 neurons while LEFT and RIGHT have 185 and 186. Active
  fraction favours small pools; the 0.20 threshold and gates were fixed in
  advance, but the imbalance remains an interpretation caveat.
- Conditions D and E are single seeded draws of 64 neurons. "Zero motor spikes"
  in one draw is not proof that random stimulation never recruits motor
  neurons; it is a matched negative control, not a distribution.
- The decoder is an abstract construct. LEFT, RIGHT and JUMP are not biological
  commands, and a JUMP output is not a jump.
- No model weight, raw dataset, Phase 4F file or decoder threshold was changed.

## 11. Verdict

**PASS (execution) with scientific limitations.** All six conditions and all
sensitivity variants ran; every condition reproduced bit-identically under
repeat; the unknown-edge equivalence held; and the decoder, populations and
config were unchanged. The positive JUMP result is real within the declared
model, but it is transform- and sign-dependent and does not demonstrate
biological motor control.
