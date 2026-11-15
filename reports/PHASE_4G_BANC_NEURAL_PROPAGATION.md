# Phase 4G — BANC Neural Propagation

**Phase:** 4G
**Status:** Complete
**Verdict:** **PASS WITH LIMITATIONS**
**Date:** 2026-11-08
**Machine-readable summary:** `experiments/results/phase_4g/phase_4g_summary.json`

Phase 4G connects the BANC v888 connectome to the existing neuron and synapse
models, stimulates upstream candidate populations, measures directed synaptic
propagation, and passes the resulting spike activity to the unchanged Phase 4F
motor decoder. It does not demonstrate biological motor control. The one
positive decoded result is conditional on declared modelling choices, and the
most important finding is that it depends strongly on the transmitter-sign prior
and on the structural-to-current transform.

---

## 1. Executive summary and verdict

**Verdict: PASS WITH LIMITATIONS.**

All five subphases completed, all planned conditions and sensitivity variants
ran, and all required validation and integrity checks passed. The verdict is not
an unqualified PASS because the positive result is not robust to every declared
modelling choice:

- Propagation is observable in the simulated BANC network. Condition C produced
  1,296 spikes, of which 556 were non-stimulated; 82 motor neurons fired.
- The unchanged Phase 4F decoder returned **JUMP in 4 of 5 windows** for
  condition C and **NEUTRAL** for every matched control and baseline.
- The result is **not transform-invariant**. It survives the primary and
  uncapped power transforms but disappears under linear, log1p and power-0.5
  transforms.
- The result is **entirely sign-dependent**. Flipping the 64 stimulated neurons
  from verified excitatory to verified inhibitory leaves 605 directly driven
  spikes and zero downstream or motor spikes.
- Most of the connectome is excluded by the verified-only policy: 44.5 % of
  threshold-5 edges and 45.4 % of synapses are signed; 62.1 % of neurons have no
  transmitter annotation.
- LEFT, RIGHT and JUMP are annotation-derived decoder labels, not identified
  motor commands. A JUMP output is not a jump.

## 2. Scope, scientific questions and non-claims

The phase asks whether directed activity can be propagated through the BANC
structural graph, whether motor populations can be recruited without direct
motor stimulation, whether the decoder distinguishes the recruited populations,
and whether any observed signal survives controls and parameter variation.

Twelve questions were specified: propagation, motor activation, LEFT/RIGHT/JUMP
differences, decoder distinction, non-motor activity, baseline motor activity,
seed stability, threshold sensitivity, sign sensitivity, weight sensitivity,
distinguishability from matched random stimulation, and survival of shuffled
controls. Answers with evidence and caveats are in Section 16.

Explicit non-claims, declared before the experiments:

- LEFT, RIGHT and JUMP are decoder labels from published annotations, not
  identified motor commands.
- Stimulated neurons are upstream candidates; motor pools are never stimulated.
- A decoded action is not evidence of biological motor control.
- Structural connectivity and synapse counts are not physiological connectivity
  or conductance.

## 3. Repository and data context

BANC v888 threshold-5 graph (the Phase 4D primary graph):

| Property | Value |
| --- | ---: |
| Nodes | 172,433 |
| Edges | 1,535,710 |
| Structural synapses | 18,552,546 |
| Isolated nodes | 24,320 |
| Self-edges | 0 |
| Edge weight | integer `count` |
| Node order | ascending `banc_888_id` |

Alternative graphs used only for sensitivity: threshold 1 (11,596,517 edges,
34,310,230 synapses, 6,232 isolated) and threshold 10 (570,721 edges,
12,397,230 synapses, 62,551 isolated).

Annotation coverage:

| Quantity | Value |
| --- | ---: |
| Verified non-null transmitter labels | 65,292 |
| Predicted non-null labels | 153,927 |
| Neurons without any label | 107,141 (62.1 %) |
| Threshold-5 signed edges | 683,100 / 1,535,710 (44.5 %) |
| Threshold-5 signed synapses | 8,426,168 / 18,552,546 (45.4 %) |
| Verified excitatory / inhibitory neurons | 53,987 / 9,733 |

Phase 4E and 4F artefacts were reused without modification: 1,316 descending
neurons, 805 motor neurons, 12,850 VNC intrinsic neurons, and LEFT/RIGHT/JUMP
populations of 185/186/20 neurons (391 assigned, 414 unassigned motor neurons).

FAFB artefacts, the FAFB `BrainSimulator`, raw datasets, manifests, the Phase 4F
decoder and populations, and the root `README.md` were read-only throughout.

## 4. Phase 4G.1 — Interface audit

Report: `reports/PHASE_4G1_INTERFACE_AUDIT.md` (verdict **READY WITH
ADAPTERS**).

The audit reproduced the failure that prevented direct reuse:

```text
AttributeError: 'BancConnectome' object has no attribute 'vocabulary'
```

`BrainSimulator` constructs `SynapseModel`, which requires
`graph.vocabulary["nt_type"]` and `graph.nt_code`. The BANC graph has neither.
Two further differences are non-exceptional but material: BANC stores integer
synapse counts where the FAFB path expects pA-scaled weights, and
`BrainSimulator` emits FAFB-shaped summary fields. The CSR layout itself is
compatible.

Reusable unchanged: `LIFPopulation`, `SpikeRecorder`, the Phase 4F populations
and the Phase 4F decoder. New adapters were therefore confined to a separate
BANC simulation path; no existing interface was silently changed.

## 5. Phase 4G.2 — Transmitter sign and edge-weight policy

Report: `reports/PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.md`; declared policy:
`configs/banc_synapse_policy.yaml` (SHA-256
`88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e`).

Sign policy (primary):

| Class | Assignment |
| --- | --- |
| Verified acetylcholine, glutamate | Excitatory |
| Verified GABA, glycine | Inhibitory |
| Dopamine, serotonin, octopamine, tyramine, histamine, nitric oxide | Unknown (no fixed sign) |
| Conflicting labels | Unknown |
| Predicted-only labels | Not used in the primary policy |
| Edges from unknown-sign presynaptic neurons | Excluded (strategy A) |

Sign is a **modelling prior applied to the presynaptic neuron**, not an
established postsynaptic effect at every target.

Weight policy (primary):

```text
w = min(5.0 × count^0.75, 300 pA)
```

`count` is the integer structural synapse count. `norm` is never used. The cap
saturates at `count = (300/5)^(4/3) ≈ 234.89`. Weights are not conductances.

Three unknown-edge strategies were specified: A exclusion (primary), B predicted
fallback (sensitivity only), and C retained with zero weight. Strategy C is
numerically identical to A and was not run as a separate condition.

## 6. Phase 4G.3 — BANC simulation adapter

New, separate modules; no FAFB simulator changes:

| Module | Role |
| --- | --- |
| `brain/banc_synapse_policy.py` | Sign classes, verified/predicted policy, structural weight transform |
| `brain/banc_simulator.py` | Sparse time-stepped BANC simulation over the full graph |
| `brain/banc_simulation_adapter.py` | Exact spike hand-off to Phase 4F windowing and decoding |

Reused unchanged: `LIFPopulation` (C = 200 pF, g = 10 nS, τm = 20 ms, rest
−65 mV, threshold −50 mV, reset −68 mV, refractory 2 ms, rheobase 150 pA) and
exponential currents (τexc = 5 ms, τinh = 8 ms, 1.0 ms effective delay = 2 steps
at 0.5 ms).

The simulator is sparse: each step touches only the outgoing edges of neurons
that fired. It does not densify or sample the graph. The adapter reads the
exact `SpikeRecorder` arrays and applies no transformation before the decoder.

Focused tests: 14 policy tests, 21 simulator tests, 8 adapter tests.

## 7. Phase 4G.4 — Propagation validation

Report: `reports/PHASE_4G4_PROPAGATION_VALIDATION.md`.

Twenty synthetic checks passed 20/20 (suite runtime 0.376 s):

| Check | Result | Check | Result |
| --- | --- | --- | --- |
| Convergent chain ordering | PASS | Inhibitory-only target silent | PASS |
| Single-edge attenuation | PASS | Inhibitory mixed reduces target | PASS |
| Convergence required | PASS | Unknown sign excluded | PASS |
| Edge removal downstream | PASS | Predicted only excluded | PASS |
| Edge removal upstream | PASS | Predicted fallback enables propagation | PASS |
| Weight reduction below recruitment | PASS | No stimulation silence | PASS |
| Weight monotonicity | PASS | Current injection threshold | PASS |
| Cap saturation equivalence | PASS | Delay quantisation | PASS |
| Direction reversal | PASS | Refractory interval | PASS |
| Isolated nodes silent | PASS | Deterministic repeat | PASS |

Key quantitative findings:

- One capped 300 pA edge produces about **4.7 mV** at the target, below the
  15 mV threshold excursion. About **four coincident capped edges** are needed
  to fire a resting neuron. Propagation therefore requires convergence.
- The cap saturates at count ≈ 234.89; counts above this produce identical
  weights.
- Effective delay is exactly 2 simulation steps; refractory behaviour matches
  the Phase 2 model.

Full-graph smoke test (64 highest-out-degree neurons, threshold 5, 100 ms,
seed 20261108): 74 spikes, 64 active neurons, 0.69–0.73 s per run, RSS
197–200 MB, peak working set 265–269 MB. Two runs produced the identical
activity SHA-256
`b660f712d9490a7ff29b6d4326fdb36344cc7db7a67925f5b9a9aa2ce167a1d5`.

The smoke test demonstrates that a sparse full-graph run is feasible and
reproducible; it is not evidence of physiological propagation.

## 8. Phase 4G.5 — Integration design and candidate selection

Report: `reports/PHASE_4G5_MOTOR_DECODER_INTEGRATION.md`.

Pipeline:

```text
BANC v888 graph → signed edges → LIF / exponential synapses
→ SpikeRecorder → unchanged Phase 4F windows, populations and decoder
→ LEFT / RIGHT / JUMP / NEUTRAL
```

Fixed parameters across primary conditions:

| Parameter | Value |
| --- | --- |
| Graph threshold | 5 |
| Duration / step | 300 ms / 0.5 ms |
| Seed | 20261108 |
| Stimulus | 300 pA, 50–250 ms |
| Decode span | 50–300 ms |
| Decoder window / step | 50 ms / 50 ms |
| Activation / release threshold | 0.20 / 0.10 |
| Evidence gates | ≥ 5 spikes and ≥ 3 active neurons |
| Priority | LEFT, RIGHT, JUMP |
| Weight policy | `min(5.0 × count^0.75, 300 pA)` |

No motor neuron was stimulated. No decoder threshold, population rule, priority
or configuration was changed.

Candidate groups, each 64 non-motor verified-excitatory neurons, fixed before
any simulation output was inspected:

| Group | Rule | Eligible pool | Edges to motor | Synapses to motor |
| --- | --- | ---: | ---: | ---: |
| B — descending candidate | Top descending neurons by direct motor synapses | 141 | 645 | 9,832 |
| C — VNC intrinsic candidate | Top VNC intrinsic neurons by direct motor synapses | 5,622 | 1,767 | 64,986 |
| D — random matched | Random verified-excitatory non-motor neurons | 53,829 | 38 | 1,075 |
| E — shuffled assignment | Random descending neurons after removing B | 77 | 47 | 393 |

Group D is dominated by optic-lobe intrinsic neurons, so it is size-matched but
not region-matched. Group E samples almost the whole non-selected descending
pool. These are structural candidates, not identified command neurons.

## 9. Conditions and primary results

| Condition | Input | Background / noise | Spikes | Active neurons | Non-stimulated spikes | Motor spikes | Active motor neurons | Decoded states |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A — no stimulation | none | 0 / 0 pA | 0 | 0 | 0 | 0 | 0 | NEUTRAL ×5 |
| B — descending candidate | 64 × 300 pA | 0 / 0 pA | 781 | 77 | 61 | 18 | 3 | NEUTRAL ×5 |
| C — VNC intrinsic candidate | 64 × 300 pA | 0 / 0 pA | 1,296 | 164 | 556 | 492 | 82 | JUMP ×4, NEUTRAL ×1 |
| D — random matched | 64 × 300 pA | 0 / 0 pA | 704 | 64 | 0 | 0 | 0 | NEUTRAL ×5 |
| E — shuffled assignment | 64 × 300 pA | 0 / 0 pA | 728 | 69 | 16 | 0 | 0 | NEUTRAL ×5 |
| F — background / noise | none | 50 / 50 pA | 0 | 0 | 0 | 0 | 0 | NEUTRAL ×5 |

Only condition C recruited the decoder populations: 71 LEFT/RIGHT/JUMP motor
neurons (27 LEFT, 32 RIGHT, 12 JUMP) plus 11 unassigned motor neurons. Its 556
non-stimulated spikes comprise 492 motor and 64 non-motor spikes.

Condition B recruited only unassigned motor neurons (18 spikes, 3 neurons),
outside LEFT/RIGHT/JUMP. D and E produced no motor spikes at all. A and F were
silent.

## 10. Motor population recruitment and decoder output

Whole-span active fractions for condition C: LEFT 14.6 %, RIGHT 17.2 %, JUMP
60.0 %. Per-window decoder output:

| Window | LEFT | RIGHT | JUMP | State |
| --- | ---: | ---: | ---: | --- |
| 50–100 ms | 0.1297 | 0.1183 | 0.5500 | JUMP |
| 100–150 ms | 0.1351 | 0.1505 | 0.6000 | JUMP |
| 150–200 ms | 0.1351 | 0.1344 | 0.6000 | JUMP |
| 200–250 ms | 0.1297 | 0.1505 | 0.6000 | JUMP |
| 250–300 ms | 0.0000 | 0.0000 | 0.0000 | NEUTRAL |

LEFT and RIGHT clear the evidence gates but stay below the 0.20 activation
threshold. JUMP clears both with 11–12 active neurons out of 20. The last window
is silent because the stimulus ends at 250 ms. NEUTRAL is preserved, not
suppressed.

The JUMP pool is deliberately small (20 neurons versus 185 and 186), so an
active-fraction score favours it. The 0.20 threshold and gates were declared in
Phase 4F before this experiment and were not adjusted.

## 11. Controls and baselines

- **No-stimulation baseline (A):** zero spikes, all NEUTRAL. No spontaneous
  activity.
- **Background/noise control (F):** 50 pA background plus 50 pA noise produced
  zero spikes under seeds 20261108, 1 and 2. There is no baseline motor
  activity to suppress or explain.
- **Matched random control (D):** 704 directly driven spikes, zero downstream
  and zero motor spikes.
- **Shuffled descending assignment (E):** 728 spikes, 16 downstream, zero
  motor spikes.

The controls separate stimulation itself from connectivity-selected
stimulation: D and E receive the same current and fire, but do not recruit the
motor populations under this model. This is a matched negative control from
single seeded draws, not a distribution over random groups.

## 12. Sensitivity analysis

All variants keep populations, decoder thresholds, priority and arbitration
unchanged.

### 12.1 Graph threshold

| Threshold | Spikes | Motor spikes | Active motor neurons | States | Max JUMP |
| --- | ---: | ---: | ---: | --- | ---: |
| 1 | 1,399 | 564 | 96 | JUMP ×4, NEUTRAL ×1 | 0.65 |
| 5 (primary) | 1,296 | 492 | 82 | JUMP ×4, NEUTRAL ×1 | 0.60 |
| 10 | 1,253 | 456 | 75 | JUMP ×4, NEUTRAL ×1 | 0.60 |

The decoded action is stable across thresholds; counts vary by up to about
20 %. Threshold 1 has 7.5× the edges of threshold 5 (11.6M versus 1.5M), so it
is substantially more expensive to load and simulate; the count differences are
not a timing benchmark.

### 12.2 Stimulus intensity

| Current | Spikes | Motor spikes | States | Max LEFT / RIGHT / JUMP |
| --- | ---: | ---: | --- | --- |
| 100 pA | 0 | 0 | NEUTRAL ×5 | 0 / 0 / 0 |
| 300 pA (primary) | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 | 0.135 / 0.151 / 0.60 |
| 600 pA | 3,493 | 1,645 | JUMP ×5 | 0.292 / 0.333 / 0.90 |

At 100 pA the stimulus is below the 150 pA rheobase and nothing fires. At
600 pA all three populations cross 0.20; JUMP remains highest and primary. The
primary action is stable in this range, but the active-set size is not.

### 12.3 Weight transform

| Transform | Spikes | Motor spikes | States |
| --- | ---: | ---: | --- |
| power 0.75, cap 300 pA (primary) | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 |
| power 0.75, uncapped | 1,281 | 481 | JUMP ×4, NEUTRAL ×1 |
| linear, scale 0.5, cap 300 pA | 723 | 5 | NEUTRAL ×5 |
| power 1.0, scale 0.5, cap 300 pA | 723 | 5 | NEUTRAL ×5 |
| log1p, scale 10, uncapped | 755 | 0 | NEUTRAL ×5 |
| power 0.5, scale 5, cap 300 pA | 740 | 0 | NEUTRAL ×5 |

This is the most consequential sensitivity. The decoded action is a property of
the declared structural-to-current calibration, not of structure alone.

### 12.4 Unknown-edge policy and predicted labels

| Variant | Spikes | Motor spikes | States |
| --- | ---: | ---: | --- |
| Unknown edges retained with zero weight | 1,296 | 492 | JUMP ×4, NEUTRAL ×1 |
| Predicted-label fallback enabled | 1,271 | 471 | JUMP ×4, NEUTRAL ×1 |

Retaining unknown edges with zero weight is bit-identical to exclusion (same
spike hash). Predicted labels change counts slightly but not the decoded action.

### 12.5 Seed

Conditions A–E have no stochastic term. The noise control F was silent under all
three seeds. Seed-dependent variability is therefore zero because there is no
spontaneous activity, not because an active state was shown to be stable.

### 12.6 Decoder window

| Window / step | JUMP windows | NEUTRAL windows | Max JUMP |
| --- | ---: | ---: | ---: |
| 25 ms / 25 ms | 7 | 3 | 0.55 |
| 50 ms / 50 ms (primary) | 4 | 1 | 0.60 |
| 100 ms / 100 ms | 2 | 1 | 0.60 |

The primary action is JUMP at every window size; the number of windows and the
neutral fraction change as expected.

### 12.7 Sign

| Variant | Spikes | Non-stimulated spikes | Motor spikes | States |
| --- | ---: | ---: | ---: | --- |
| C, excitatory (primary) | 1,296 | 556 | 492 | JUMP ×4, NEUTRAL ×1 |
| C, inhibitory | 605 | 0 | 0 | NEUTRAL ×5 |

Direct current still drives the 64 stimulated neurons, but no downstream neuron
fires. The result depends entirely on the sign prior; sign is not a measured
postsynaptic effect.

## 13. Determinism

Each condition was run twice with identical parameters. Spike hashes, decision
hashes, population-activity records, scores and activity counts matched in all
six conditions.

| Condition | Spike hash | Decision hash | Population activity | Scores |
| --- | --- | --- | --- | --- |
| A | `e3b0c442…` (empty) | `65cbcc1a…` | equal | equal |
| B | `408dcc55…` | `6d22ef07…` | equal | equal |
| C | `397e888f…` | `4380fc38…` | equal | equal |
| D | `3cd79339…` | `b82c0f33…` | equal | equal |
| E | `8a9d6d08…` | `0a3503c7…` | equal | equal |
| F | `e3b0c442…` (empty) | `9257c61c…` | equal | equal |

Configuration and input hashes were identical across runs:

| Item | SHA-256 |
| --- | --- |
| Threshold-5 graph | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Node table | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Synapse policy config | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |
| Decoder config | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| Combined configuration | `79004501019cf2fe6ed710310eb3acd19ce12e66b2ed7527b126a2d89632501d` |

No nondeterminism was observed. The simulation has no unseeded random draws;
conditions A–E contain no stochastic term at all, and F uses
`np.random.default_rng(seed)`.

## 14. Testing

Focused Phase 4G, Phase 4E, Phase 4F and BANC graph tests:

```text
python -m pytest tests/test_banc_graph_loader.py tests/test_banc_graph_audit.py \
  tests/test_banc_synapse_policy.py tests/test_banc_simulator.py \
  tests/test_banc_simulation_adapter.py tests/test_motor_populations.py \
  tests/test_motor_decoder.py tests/test_motor_decoder_experiment.py \
  tests/test_phase_4e_pathways.py -q -p no:anyio
```

Result: **140 passed, 0 failed, 0 skipped, 14.26 s**, no warnings reported.

Full suite:

```text
python -m pytest tests -q -p no:anyio
```

Result: **440 passed, 0 failed, 0 skipped, 29.63 s (exit 0)**, no warnings
reported.

The Phase 4G.4 propagation suite is a separate script, not a pytest module:
20/20 checks passed.

## 15. Integrity and change control

Baseline: `experiments/phase_4g/baseline_integrity.json`. Recheck:
`experiments/results/phase_4g/integrity_recheck.json` (verdict **PASS**).

| Check | Result |
| --- | --- |
| Protected files matching baseline | 26 / 26 |
| Protected files failed | none |
| BANC manifest verification | PASS |
| Raw BANC input hashes | PASS |
| Graph artefact hashes | PASS |
| Staged files | none |
| Model weights staged | none |
| Raw data staged | none |
| Root `README.md` unchanged | yes (`8ab6a8cc…`, 14,921 bytes) |

Protected and unchanged: FAFB connectome artefacts, FAFB `BrainSimulator`,
neuron and synapse models, Phase 4D BANC artefacts, Phase 4E pathway artefacts,
Phase 4F populations, decoder and configuration, sensory pipeline, raw FAFB and
BANC datasets, dataset manifests and checksums, and the root `README.md`.

No file was staged, committed or pushed. No earlier output was overwritten;
all Phase 4G outputs use versioned names.

## 16. Answers to the scientific questions

1. **Can neural propagation be observed?** Yes, in condition C: 556 of 1,296
   spikes were non-stimulated and 82 motor neurons fired. It is not universal;
   B, D, E and both baselines did not recruit the decoder populations.
2. **Are motor populations activated?** Yes, in C: 71 LEFT/RIGHT/JUMP motor
   neurons plus 11 unassigned motor neurons.
3. **Do LEFT, RIGHT and JUMP differ?** Yes: whole-span active fractions are
   14.6 %, 17.2 % and 60.0 %. Per-window LEFT and RIGHT stay below 0.20; JUMP
   exceeds it.
4. **Does the decoder distinguish them?** It returns JUMP in 4 of 5 windows and
   NEUTRAL after the stimulus; every matched control returns NEUTRAL. The
   distinction exists in this sample and is not universal.
5. **Is there non-motor activity?** Yes: 82 of 164 active neurons are non-motor
   (64 stimulated plus 18 other non-motor), and 64 non-stimulated non-motor
   spikes occur.
6. **Is there baseline motor activity?** No. Conditions A and F produce zero
   spikes with and without 50 pA background and noise.
7. **Is the result stable across seeds?** Conditions A–E are deterministic. The
   noise-only control F is silent under three seeds, so seed variability is zero
   rather than demonstrated stability of an active state.
8. **Is it threshold-sensitive?** The decoded action is stable across graph
   thresholds 1, 5 and 10, but spike and motor counts change by up to about
   20 %.
9. **Is it sign-sensitive?** Yes, completely. Flipping the stimulated sign to
   inhibitory removes all downstream and motor activity and returns NEUTRAL.
10. **Is it weight-sensitive?** Yes, strongly. It survives the primary and
    uncapped power transforms but disappears under linear, log1p and power-0.5
    transforms.
11. **Is it distinguishable from matched random stimulation?** Yes in this
    sample: C produces 492 motor spikes, D produces 0, E produces 0. This is one
    seeded draw per control, not a distribution.
12. **Does it survive shuffled controls?** Yes in this sample: E, the shuffled
    descending assignment, is NEUTRAL. The signal is tied to the
    connectivity-ranked VNC intrinsic candidate, not to stimulation alone.

No single positive result is treated as sufficient evidence. The answers above
combine the positive condition, the matched controls, the negative baselines and
the parameter-sensitivity results.

## 17. Measurement, assumption, observation and hypothesis

| Category | Phase 4G content |
| --- | --- |
| Published biology | Transmitter identities from BANC annotations; motor neuron effector annotations; fly leg motor pools as annotated |
| Connectome-derived measurement | Node/edge/synapse counts; CSR structure; in/out degree; direct and two-hop pathway counts |
| Published annotations | Cell types, sides, effectors, neurotransmitter labels (verified vs predicted) |
| Simulation assumptions | LIF parameters; exponential synapses; 1 ms delay; weight transform; sign policy; verified-only edge inclusion |
| Experimental observation | Spike counts; active fractions; rates; decoder scores and states under the declared model |
| Hypothesis | That connectivity-ranked VNC intrinsic stimulation recruits leg motor pools more effectively than matched controls |

Structural connectivity is not physiological connectivity. Synapse count is not
conductance. Predicted transmitter is not verified transmitter. Transmitter
identity is not postsynaptic effect. A decodable output is not biological
perception or motor control. Reproducibility is not biological validity.
Simulated success is not gameplay ability.

## 18. Limitations and threats to validity

- **Annotation coverage.** Only 44.5 % of threshold-5 edges and 45.4 % of
  synapses are signed under the verified-only policy; 62.1 % of neurons are
  unannotated. The result describes a signed subnetwork, not the whole
  connectome.
- **Sign prior.** The entire positive result disappears when the stimulated
  neurons are treated as inhibitory. Sign is a declared prior, not a measured
  postsynaptic effect.
- **Weight calibration.** The decoded action disappears under several plausible
  monotone transforms. The primary transform, scale and cap are declared
  calibrations, not measured conductances.
- **Candidate selection.** Groups are 64 structurally ranked neurons, not
  identified command neurons. The descending top-64 is heavily unannotated;
  restricting to verified-excitatory neurons changes the candidate pool.
- **One positive condition.** Only the VNC intrinsic group recruited the
  decoder pools. A different group size, threshold or selection rule might
  change the result; this experiment does not establish robustness.
- **Single control draws.** D and E are one seeded draw each. "Zero motor
  spikes" is a matched negative control, not proof that random stimulation
  never recruits motor neurons.
- **Pool imbalance.** JUMP has 20 neurons versus 185 and 186 for LEFT and RIGHT.
  Active-fraction scoring favours small pools. The thresholds were fixed in
  Phase 4F before this experiment, but the imbalance remains an interpretation
  caveat.
- **Abstract decoder.** LEFT, RIGHT and JUMP are annotation-derived labels, not
  biological motor commands. A JUMP output is not a jump.
- **Model scope.** The LIF and exponential-synapse models are phenomenological.
  No plasticity, neuromodulation, sensory feedback, body mechanics or behaviour
  is simulated.
- **Runtime.** The primary conditions take 2.28–3.30 s each. The recorded
  5,795.5 s experiment-suite wall time includes all conditions, repeats and
  sensitivity variants under background execution; it is not a benchmark.

## 19. Verdict, artefacts and next milestone

**Verdict: PASS WITH LIMITATIONS.**

The engineering is complete and validated: the interface incompatibility is
explained, the sign and weight policy is declared, the BANC adapter is separate
and sparse, propagation is validated by 20 checks, the Phase 4F decoder is
reused unchanged, all conditions and sensitivity variants ran, all repeats were
bit-identical, the test suite passes, and integrity is intact.

The scientific result is a conditional observation, not a demonstrated motor
mechanism. Connectivity-selected VNC intrinsic stimulation recruits the decoder
populations and yields JUMP in this model; matched random and shuffled controls
do not. But the result is transform-dependent, sign-dependent, based on a
minority of annotated edges, and decoded by an abstract construct. It must not
be described as proof of biological motor control.

Principal artefacts:

| Artefact | SHA-256 |
| --- | --- |
| `reports/PHASE_4G1_INTERFACE_AUDIT.md` | `103497b2232e6f1b9d54cd5b67686a03a93e447024149100c3d09a81f4245acf` |
| `reports/PHASE_4G1_INTERFACE_AUDIT.json` | `65614c99876f8d58e68f531b4052c76f0bbc70f669edfc14f8dc564e47740b2c` |
| `reports/PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.md` | `5d123518f6266e24f7d138337a20c57031f26f229f05252886820c31a51064b4` |
| `reports/PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.json` | `3fd3a7fd0b429ee7b230a38beece84486812bbda9babb0e0c60213628d16f08e` |
| `reports/PHASE_4G4_PROPAGATION_VALIDATION.md` | `6657599f4fd9a644710ed1b626c2f801125fcad87636c913e2e8ba18dc3270e1` |
| `reports/PHASE_4G4_PROPAGATION_VALIDATION.json` | `f1e431fa93b6cf29607a7733554b9522270ca207004f6bfa730070bf162c3c38` |
| `reports/PHASE_4G5_MOTOR_DECODER_INTEGRATION.md` | `a4dd2fe64c633453348b2ca5fcbf9f0092b22e9b9e941ffe8d1a981c8dec7c57` |
| `experiments/results/phase_4g/phase_4g_experiment.json` | `ab04de266eb40c0f4abe6f27979797257448b35c546f8d1d2c699a7ba8aea717` |
| `experiments/results/phase_4g/phase_4g_sign_sensitivity.json` | `0418d0c3423ded1ff62f61537e233b04c1d3bad917d06a760ca3812a70f9e482` |
| `experiments/results/phase_4g/integrity_recheck.json` | `79c2b26ddd27e1ccc530e1fc99ad9989a4e49eeb218cb48a3703ef287a7c0b59` |

**Next recommended milestone:** Phase 4H should treat the JUMP result as a
hypothesis and test robustness before any gameplay integration — for example,
multiple random control draws, alternative candidate group sizes, a declared
family of weight transforms with a pre-registered selection rule, and a
round-trip check that BANC activity can be generated from sensory input rather
than artificial current injection. Until then, the Phase 4G result should be
reported as a model-conditional observation, not as motor control.
