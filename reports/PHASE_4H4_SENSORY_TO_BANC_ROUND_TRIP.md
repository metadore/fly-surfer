# FLY-SURFER — Phase 4H.4 Sensory-to-BANC Round-Trip

Status: **PASS WITH LIMITATIONS**
Date: 2026-11-08
Phase: 4H.4
Parent protocol: `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md` (SHA-256 `7c511c5a…e5e6b05`)

Phase 4H.4 completes the pre-registered sensory-to-BANC round-trip matrix and
asks what happens to the 232-neuron annotation-defined sensory input population
and its BANC targets when the archived perception events drive the unchanged
Phase 4G simulator. It is a completion and measurement exercise, not a search
for a parameter setting that produces motor activity.

The headline is a controlled negative result. All 27 runs completed with
verified hashes and deterministic repeats. The event drive produces
reproducible spikes in the stimulated sensory neurons (3,562 on the full
stream), but **no non-stimulated neuron spikes in any stream or condition**.
Signed synaptic current is delivered to 473 of the 607 downstream first-hop
targets, yet the closest first-hop neuron remains 6.93 mV below threshold and
the second hop receives no current. Descending and motor populations receive no
propagation from the annotation mapping. Every decoder window is NEUTRAL and
every motor-spike count is zero. Structural connectivity does not imply
effective downstream activation at this drive.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4h/analyse_sensory_roundtrip.py` | Reconciles the 27-run matrix, verifies configuration, replays every run with hash checks and computes all diagnostics |
| `experiments/phase_4h/run_sensory_roundtrip.py` | Original execution runner (unchanged) |
| `experiments/results/phase_4h/sensory_roundtrip.json` | Executed result: 27 run records, summaries, comparisons, determinism, integrity |
| `experiments/results/phase_4h/sensory_roundtrip.checkpoint.jsonl` | Append-only execution checkpoint (27 records) |
| `experiments/results/phase_4h/sensory_roundtrip.diagnostics.v2.checkpoint.jsonl` | Read-only replay diagnostics, one record per run (27 records) |
| `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | Full analysis output (condition tables, diagnostics, statistics) |
| `experiments/results/phase_4h/sensory_roundtrip.analysis.log` | Analysis console log |
| `tests/test_phase_4h4_analysis.py` | Focused tests: seed rule, reconciliation, aggregation, event-locked windows, threshold proximity, signed CSR helper |

Run:

```
python -m experiments.phase_4h.analyse_sensory_roundtrip
```

Execution completed in 5,712.06 s (27 runs). Analysis took 674.62 s, of which
671.30 s were 27 hash-verified replays. Software: Python 3.13.14, NumPy 2.3.4,
pandas 2.3.3, Windows 11 (10.0.26200).

An earlier diagnostics checkpoint
(`sensory_roundtrip.diagnostics.checkpoint.jsonl`) was produced by a
preliminary analysis version whose first-hop classification did not exclude a
stimulated target. It is invalid for interpretation, is not read by the final
analysis, and has been preserved rather than deleted.

---

## 1. Experimental design

The design was frozen before execution and is unchanged here. Seven conditions
are crossed with three event streams:

| Condition | Drive |
| --- | --- |
| A `A_no_events` | no events, no background, no noise |
| B `B_actual` | actual archived events through the annotation mapping |
| C `C_temporal_shuffle` | sorted event-time array permuted across event identities |
| D `D_feature_identity_shuffle` | feature payloads permuted across events |
| E `E_random_matched_mapping` | seeded size-matched non-motor random mapping |
| F `F_constant_matched_charge` | uniform constant current with the same total injected charge as B |
| G `G_background_noise` | 50 pA background plus 50 pA Gaussian noise, no events |

B and G are repeated with the same seed to check determinism: 7 conditions + 2
repeats = 9 runs per stream, 27 runs total.

The three streams are non-overlapping segments of one recording group, not
independent recordings:

| Stream | Frames | Events | Pulses | Duration |
| --- | --- | --- | --- | --- |
| `full_100_199` | 100–199 | 215 | 43 | 3,300.5 ms |
| `seg_0_99` | 0–99 | 148 | 27 | 3,300.5 ms |
| `seg_200_299` | 200–299 | 152 | 37 | 3,300.5 ms |

Timestamps are synthesized at an assumed 30 fps by the unchanged Phase 3B
pipeline because the source images carry no timestamps. Event ordering and
gaps therefore come from the perception pipeline, not from measured times.

Seeds are fixed by rule: `20,661,109` plus a stream offset (0, 100, 200) plus
the condition index (A = 0 … G = 6). The B and G repeats reuse the seed of
their base condition.

The replication unit for any comparison is one simulation run. The three
streams are not independent replicates; neurons and timesteps are never
treated as replicates. The analysis is descriptive: no confirmatory p-value or
confidence interval is claimed across non-independent segments.

## 2. Configuration and hash verification

Verification ran against the live repository and the stored result before any
diagnostic was accepted. All **47 checks passed, 0 failed**.

| Check | Observed |
| --- | --- |
| Protocol SHA-256 | `7c511c5a9cfb64262e424ab566743ff2b25d86e2c51a12f5a77057dd3e5e6b05` |
| Graph artifact SHA-256 | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Node table SHA-256 | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Policy config SHA-256 | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |
| Decoder config SHA-256 | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| Neuron config SHA-256 | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` |
| Mapping config SHA-256 | `64c716a42c44ded58c77fccdcd865b0a9732a06b86019d673e6fb4c902dfc4ff` |
| World signature SHA-256 | `a3d57abf1d2e3aad7f9a1fc33567b95ca62e065b6b20a7835e5e7988a51f6ebd` |

Frozen quantities:

- Graph: BANC v888, threshold 5, 172,433 nodes, 1,535,710 edges, 18,552,546 synapses.
- Sign policy: verified-only. ACh and glutamate excitatory; GABA and glycine inhibitory; modulators/conflicts unknown; predicted fallback disabled; unknown edges excluded. 683,100 signed edges (44.48% of t5 edges), 8,426,168 signed synapses.
- Weight policy W0: `min(5.0 × count^0.75, 300 pA)`, integer synapse count, `norm` never used.
- Neuron: LIF, C = 200 pF, g = 10 nS, rest −65 mV, threshold −50 mV, reset −68 mV, refractory 2 ms, minimum −90 mV, rheobase 150 pA. Synaptic tau 5 ms excitatory / 8 ms inhibitory, delay 1 ms (2 steps at dt 0.5 ms); weights are pA currents.
- Decoder: 50 ms half-open windows, 50 ms step, activation 0.20, release 0.10, minimum 5 spikes and 3 active neurons, priority LEFT/RIGHT/JUMP. Pools: LEFT 185, RIGHT 186, JUMP 20, motor 805 (leg 371, unassigned 414).
- Stimulated mapping: 232 unique neurons across 7 populations (train_lane 48, obstacle_lane 48, train_present 24, train_distance 32, obstacle_present 24, obstacle_distance 32, obstacle_type 24), mapping seed 20261109. Zero motor-neuron overlap and zero action-pool overlap.
- Sensory drive: 200 pA per feature, pulse gain 1.0, decay 150 ms, dt 0.5 ms, duration 3,300.5 ms. Condition G: 50 pA background, 50 pA noise standard deviation.
- Signed outgoing wiring: 1,519 all outgoing edges, 662 signed edges, 608 unique signed targets, 0 inhibitory weight, 0 motor targets.

Every replay was accepted only if its spike hash and decision hash equalled the
stored record. All 27 replays matched. The wrapper around
`LIFPopulation.step` changes no model code, graph artifact or stored result; it
accumulates per-neuron maxima in memory for analysis only.

## 3. Complete 27-run matrix

The executed result, the execution checkpoint and the analysis agree:

| Matrix check | Result |
| --- | --- |
| Expected runs | 27 |
| Stored runs | 27 |
| Unique runs | 27 |
| Missing | none |
| Duplicated | none |
| Unexpected | none |
| Seed mismatches | none |
| Event-metadata mismatches | none |
| Duration mismatches | none |
| Checkpoint records | 27, 27 unique keys, no duplicates |

Repeat determinism (B and G on all three streams, 6 pairs):

| Stream | Condition | Same seed | Spike hash | Decision hash | Drive hash | Metrics |
| --- | --- | --- | --- | --- | --- | --- |
| `full_100_199` | B | yes | equal | equal | equal | equal |
| `full_100_199` | G | yes | equal | equal | equal | equal |
| `seg_0_99` | B | yes | equal | equal | equal | equal |
| `seg_0_99` | G | yes | equal | equal | equal | equal |
| `seg_200_299` | B | yes | equal | equal | equal | equal |
| `seg_200_299` | G | yes | equal | equal | equal | equal |

Every run followed the original seed rule; no completed run was rerun and no
stored value was overwritten. The analysis recomputed every reported number
from the complete run records and the hash-verified replays, not from the
earlier smoke test.

## 4. Condition-level results

Per-stream values. "Active" is neurons with at least one spike. Decoder counts
are over 67 windows of 50 ms.

| Stream | Condition | Total spikes | Stimulated | Non-stimulated | Motor | Active neurons | Decoded states |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| full | A | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| full | B | 3,562 | 3,562 | 0 | 0 | 171 | NEUTRAL 67 |
| full | C | 3,760 | 3,760 | 0 | 0 | 154 | NEUTRAL 67 |
| full | D | 3,648 | 3,648 | 0 | 0 | 169 | NEUTRAL 67 |
| full | E | 3,561 | 3,561 | 0 | 0 | 171 | NEUTRAL 67 |
| full | F | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| full | G | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg0 | A | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg0 | B | 1,990 | 1,990 | 0 | 0 | 103 | NEUTRAL 67 |
| seg0 | C | 1,873 | 1,873 | 0 | 0 | 88 | NEUTRAL 67 |
| seg0 | D | 1,991 | 1,991 | 0 | 0 | 87 | NEUTRAL 67 |
| seg0 | E | 1,990 | 1,990 | 0 | 0 | 103 | NEUTRAL 67 |
| seg0 | F | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg0 | G | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg200 | A | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg200 | B | 2,374 | 2,374 | 0 | 0 | 151 | NEUTRAL 67 |
| seg200 | C | 2,266 | 2,266 | 0 | 0 | 155 | NEUTRAL 67 |
| seg200 | D | 2,080 | 2,080 | 0 | 0 | 126 | NEUTRAL 67 |
| seg200 | E | 2,374 | 2,374 | 0 | 0 | 151 | NEUTRAL 67 |
| seg200 | F | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |
| seg200 | G | 0 | 0 | 0 | 0 | 0 | NEUTRAL 67 |

Descriptive summaries across the three streams (mean ± SD; n = 3
non-independent streams):

| Condition | Total spikes | Active neurons | Motor spikes |
| --- | --- | --- | --- |
| A | 0 ± 0 | 0 ± 0 | 0 ± 0 |
| B | 2,642.00 ± 819.55 | 141.67 ± 34.95 | 0 ± 0 |
| C | 2,633.00 ± 995.59 | 132.33 ± 38.40 | 0 ± 0 |
| D | 2,573.00 ± 932.04 | 127.33 ± 41.02 | 0 ± 0 |
| E | 2,641.67 ± 818.99 | 141.67 ± 34.95 | 0 ± 0 |
| F | 0 ± 0 | 0 ± 0 | 0 ± 0 |
| G | 0 ± 0 | 0 ± 0 | 0 ± 0 |

Every spike in B, C, D and E lies inside the stimulated set. Every decoder
window in every condition is NEUTRAL; every motor-spike count is zero.

Stimulated-population classes and activity on the full stream, condition B
(class membership is anatomical; some stimulated neurons carry non-sensory
class labels because the mapping is annotation-defined):

| Class | Neurons | Spikes | Active | Receiving current |
| --- | ---: | ---: | ---: | ---: |
| visual_projection | 7,284 | 2,664 | 88 | 14 |
| optic_lobe_intrinsic | 72,826 | 722 | 48 | 357 |
| sensory | 15,956 | 176 | 35 | 17 |
| central_brain_intrinsic | 31,347 | 0 | 0 | 55 |
| descending | 1,316 | 0 | 0 | 9 |
| motor | 805 | 0 | 0 | 0 |
| all other classes | — | 0 | 0 | — |

The stimulated set itself has 171 of 232 neurons active on the full stream;
the closest non-spiking stimulated neuron ended 0.677 mV below threshold.

## 5. Sensory and downstream breakdown

Condition B, full stream. Group membership is anatomical and structural; the
first hop excludes the one stimulated neuron that is also a signed target of
another stimulated neuron.

| Group | n | Spikes | Active | Receiving current | Max synaptic current (pA) | Max membrane (mV) | Closest deficit (mV) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stimulated | 232 | 3,562 | 171 | 1 | 17.02 | −50.000 (spike) | 0.677 |
| First hop (downstream) | 607 | 0 | 0 | 473 | 164.44 | −56.926 | 6.926 |
| Second hop (downstream) | 3,576 | 0 | 0 | 0 | 0.00 | −65.000 | 15.000 |
| Descending | 1,316 | 0 | 0 | 9 | 67.21 | −62.158 | 12.158 |
| Ascending | 1,849 | 0 | 0 | 0 | 0.00 | −65.000 | 15.000 |
| Motor | 805 | 0 | 0 | 0 | 0.00 | −65.000 | 15.000 |
| Non-stimulated non-motor | 171,396 | 0 | 0 | 473 | 164.44 | −56.926 | 6.926 |

First-hop distribution on the full stream: median synaptic current 0 pA,
95th percentile 80.87 pA, maximum 164.44 pA; 473 of 607 targets receive any
current, 0 within 1 mV, 0 within 2 mV, 0 within 5 mV, 1 within 10 mV of
threshold. The closest first-hop neuron is a right-side central-brain
intrinsic neuron (index 125949, root ID 720575941585745503) that reaches
−56.93 mV, 6.93 mV short.

Per-stream first-hop values:

| Stream | Targets | Receiving | Max current (pA) | Max membrane (mV) | Closest deficit (mV) | Within 10 mV |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full | 607 | 473 | 164.44 | −56.926 | 6.926 | 1 |
| seg0 | 607 | 253 | 173.02 | −57.360 | 7.360 | 0 |
| seg200 | 607 | 434 | 165.42 | −56.876 | 6.876 | 1 |

Event-locked stimulated activity (B, full): 215 events, 17,246 spikes inside
the 50 ms half-open window after event onset, 67 events with zero spikes, 6
events with no subsequent spike in the run. Latency median 7.17 ms (IQR
1.33–68.33; n = 209). Event-spike alignment peaks at 70 ms lag with r = 0.224
on the full stream. There is no event-locked downstream activity: the
downstream spike series is empty, so all downstream alignment correlations are
undefined.

Firing rates on the full stream (3,300.5 ms): 3,562 spikes over the 232
stimulated neurons is 4.65 Hz per stimulated neuron, or 6.31 Hz per active
stimulated neuron (171 active; 20.83 spikes per active neuron). The first hop,
second hop, descending, ascending and motor populations all have a firing rate
of 0 Hz. Every spike is a threshold crossing; no neuron crossed threshold
without producing a recorded spike.

Per-run values, medians, quartiles, absolute and relative differences for every
endpoint are in `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` under
`condition_results`, `diagnostics` and `statistical_comparisons`. For the
headline endpoint (B total spikes) the across-stream median is 2,374 with IQR
2,182–2,968; the control medians are 3,760 (C), 2,080 (D), 2,374 (E) and 0
(A, F, G).

## 6. Propagation analysis

**Were outgoing currents delivered?** Yes. The 3,562 stimulated spikes produced
25,332 spike-to-edge transmissions on the full stream, of which 9,499 crossed
one of the 662 signed outgoing edges (37.5%). The remaining 15,833 crossed
unsigned or excluded edges and contributed no current. Per stream, signed
transmissions were 9,499 (full), 5,019 (seg0), 5,677 (seg200).

**Did postsynaptic currents change membrane voltage?** Yes, but
subthreshold. First-hop peak synaptic current was 164.44 pA (full), 173.02 pA
(seg0), 165.42 pA (seg200) — above the 150 pA steady-state rheobase on two of
three streams. The current is transient: excitatory synaptic tau is 5 ms and
each event contributes a brief pulse, so the integrated charge does not hold
the membrane at the steady-state asymptote. Peak first-hop depolarization was
8.07 mV (full), reaching −56.93 mV against a −50 mV threshold. The 150 pA
rheobase is the sustained current required at steady state; a short peak above
it is not sufficient.

**Did any downstream neuron approach threshold?** One first-hop neuron came
within 6.93 mV (full) and one within 4.87 mV under temporal shuffling (C
full). No first-hop neuron crossed threshold on any stream in any condition.
The closest non-spiking stimulated neuron ended 0.677 mV short, so the drive is
near the somatic threshold of some stimulated neurons but not of their
targets.

**Where did propagation stop?** At the first hop. Because no first-hop neuron
fired, the second hop received exactly zero current and no second-hop neuron
spiked in any condition. Structurally there are 9 first-hop descending targets
and 103 second-hop descending targets, plus 4 motor neurons two signed hops
from the stimulated set, but none is activated. Descending neurons that
receive first-hop current (9 per stream) peak at 67.21 pA and −62.16 mV, 12.16
mV short. Motor neurons receive no current from the annotation mapping and
stay at rest.

**Why did condition F produce zero spikes?** The matched charge is 35,756,120.8
pA·ms over 232 neurons and 3,300.5 ms, i.e. 46.696 pA per neuron. That is below
the 150 pA rheobase, and the LIF steady state is
−65 + 46.696/10 = −60.330 mV, exactly the observed maximum (−60.330368 mV).
The zero-spike result is a direct consequence of spreading the matched charge
uniformly over time and neurons, not a numerical failure. The event drive
spikes because it concentrates the same total charge into short pulses that
exceed threshold locally.

**Condition G** (50 pA background plus 50 pA noise) also produces zero spikes.
The full-stream maximum membrane voltage is −57.520 mV in the stimulated group
and −56.651 mV in the non-stimulated non-motor group. Noise peaks are large
(max instantaneous input 353.47 pA globally) but brief, and the mean drive
does not hold any neuron above threshold. Notably, G gets closer to threshold
in the general population (6.65 mV deficit) and in motor neurons (7.24 mV) than
B's event drive does in the same populations (6.93 mV in non-motor, 15.00 mV in
motor). At 200 pA per feature, the event drive is not a stronger motor
membrane driver than the background/noise condition.

**Condition E is not a propagation control in the same sense.** The random
mapping selects 232 non-motor neurons without regard to class, and its
stimulated set can include descending and ascending neurons. E shows 5, 0 and
4 descending spikes on the three streams and 35 ascending spikes on average,
but **all E spikes are inside the stimulated mask** (non-stimulated spikes = 0).
Those spikes are direct-drive spikes of randomly selected neurons that belong
to those anatomical classes, not propagated activity. E's random set also has
74 first-hop motor targets, so 50 motor neurons receive current (maximum 132.70
pA, −61.60 mV), but none spikes. E's first-hop maximum current is lower than
B's (132.70 vs 164.44 pA) and its first-hop maximum membrane is lower (−59.28
vs −56.93 mV).

**Why the earlier smoke test saw spikes only in stimulated sensory neurons.**
The smoke test result is reproduced and explained: the 662 signed edges carry
current to first-hop membranes, but the per-neuron charge is too small and too
brief to reach threshold; propagation stops before the first postsynaptic
spike. The smoke test's scope was correct, not an artifact of missing edges or
of an undelivered drive.

## 7. Statistical comparisons

All comparisons are B versus one control, with n = 3 streams (non-independent
segments of one recording group). Values are per-stream and summary statistics;
Hedges g uses the control SD and is descriptive only, not an inferential effect
size. Comparisons whose control is identically zero are degenerate.

| Comparison | Endpoint | B (mean ± SD) | Control (mean ± SD) | Difference (mean ± SD) | Hedges g | Sign pattern | Degenerate |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| B vs A | total spikes | 2,642.00 ± 819.55 | 0 ± 0 | 2,642.00 ± 819.55 | — | all positive | yes |
| B vs A | non-stimulated | 0 ± 0 | 0 ± 0 | 0 ± 0 | — | all zero | yes |
| B vs A | motor spikes | 0 ± 0 | 0 ± 0 | 0 ± 0 | — | all zero | yes |
| B vs C | total spikes | 2,642.00 ± 819.55 | 2,633.00 ± 995.59 | 9.00 ± 179.32 | 0.009 | mixed | no |
| B vs C | event-locked stimulated | 11,011.33 ± 5,470.78 | 13,023.00 ± 7,285.47 | −2,011.67 ± 1,815.23 | −0.276 | all negative | no |
| B vs C | first-hop receiving | 386.67 ± 117.39 | 393.67 ± 119.35 | −7.00 ± 25.24 | −0.059 | mixed | no |
| B vs C | first-hop closest deficit (mV) | 7.05 ± 0.27 | 6.85 ± 2.17 | 0.21 ± 2.24 | 0.096 | mixed | no |
| B vs C | motor spikes | 0 ± 0 | 0 ± 0 | 0 ± 0 | — | all zero | yes |
| B vs D | total spikes | 2,642.00 ± 819.55 | 2,573.00 ± 932.04 | 69.00 ± 199.44 | 0.074 | mixed | no |
| B vs D | event-locked stimulated | 11,011.33 ± 5,470.78 | 10,683.67 ± 5,853.58 | 327.67 ± 470.94 | 0.056 | mixed | no |
| B vs D | first-hop max membrane (mV) | −57.05 ± 0.27 | −57.63 ± 0.47 | 0.58 ± 0.66 | 1.222 | all positive | no |
| B vs D | first-hop closest deficit (mV) | 7.05 ± 0.27 | 7.63 ± 0.47 | −0.58 ± 0.66 | −1.222 | all negative | no |
| B vs D | motor spikes | 0 ± 0 | 0 ± 0 | 0 ± 0 | — | all zero | yes |
| B vs E | total spikes | 2,642.00 ± 819.55 | 2,641.67 ± 818.99 | 0.33 ± 0.58 | 0.0004 | all zero | no |
| B vs E | active neurons | 141.67 ± 34.95 | 141.67 ± 34.95 | 0 ± 0 | 0.000 | all zero | yes |
| B vs E | descending spikes | 0 ± 0 | 3.00 ± 2.65 | −3.00 ± 2.65 | −1.134 | all zero | yes |
| B vs E | first-hop max current (pA) | 167.63 ± 4.70 | 138.43 ± 9.94 | 29.20 ± 12.60 | 2.939 | all positive | no |
| B vs E | first-hop max membrane (mV) | −57.05 ± 0.27 | −59.37 ± 0.19 | 2.32 ± 0.08 | 12.256 | all positive | no |
| B vs E | motor closest deficit (mV) | 15.00 ± 0.00 | 11.54 ± 0.08 | 3.46 ± 0.08 | 42.48 | all positive | yes |
| B vs F | total spikes | 2,642.00 ± 819.55 | 0 ± 0 | 2,642.00 ± 819.55 | — | all positive | yes |
| B vs F | first-hop receiving | 386.67 ± 117.39 | 0 ± 0 | 386.67 ± 117.39 | — | all positive | yes |
| B vs F | motor spikes | 0 ± 0 | 0 ± 0 | 0 ± 0 | — | all zero | yes |
| B vs G | total spikes | 2,642.00 ± 819.55 | 0 ± 0 | 2,642.00 ± 819.55 | — | all positive | yes |
| B vs G | first-hop max membrane (mV) | −57.05 ± 0.27 | −57.29 ± 0.09 | 0.24 ± 0.24 | 2.813 | mixed | no |
| B vs G | non-stimulated non-motor deficit (mV) | 7.05 ± 0.27 | 6.66 ± 0.05 | 0.40 ± 0.31 | 8.304 | all positive | no |
| B vs G | motor closest deficit (mV) | 15.00 ± 0.00 | 7.25 ± 0.05 | 7.75 ± 0.05 | 163.69 | all positive | yes |

Reading the table:

- **B vs A (sensory-event effect).** The event drive adds 1,990–3,562 spikes,
  all in stimulated neurons. The comparison is degenerate because A is exactly
  silent; no downstream or motor effect exists to compare.
- **B vs C (temporal order).** Total stimulated spikes differ by −198, +117 and
  +108 across streams, a mixed sign and a small descriptive effect (g = 0.009).
  Event-locked stimulated counts are lower in C on all three streams, and C
  raises first-hop peak depolarization on the full and seg0 streams (−54.87 and
  −56.51 mV, versus −56.93 and −57.36 mV for B) while lowering it on seg200
  (−59.16 mV). There is no downstream spike or decoder difference. The sign of
  the total-spike difference is not stable across streams, so temporal order is
  not established as a reproducible determinant of output.
- **B vs D (feature identity).** Total-spike differences are −86, −1 and +294
  (mixed). The only consistent difference is that D's first-hop membrane peaks
  0.58 mV lower on all three streams — an exploratory, subthreshold difference
  with no spike consequence.
- **B vs E (mapping specificity).** Total spikes and active-neuron counts are
  virtually identical (difference 0.33 ± 0.58 spikes; active counts identical
  on all three streams). This is expected in a feed-forward model with 232
  independent, identically parameterised neurons: the same number of neurons
  receives the same number of pulses, so the total is nearly invariant to which
  identities receive them. The mapping changes the downstream wiring
  (607 vs 881 first-hop targets; 0 vs 74 first-hop motor targets) and hence
  where current goes, but it does not change the total sensory spike count.
  The E "descending spikes" are direct spikes of stimulated neurons, not
  propagation.
- **B vs F (temporal distribution vs matched charge).** The matched-charge
  condition is exactly silent. The comparison is degenerate but informative:
  the same charge delivered uniformly (46.70 pA/neuron) never approaches
  threshold.
- **B vs G (sensory vs background/noise).** The event drive produces spikes
  whereas G does not, but G's noise brings the general population and motor
  neurons closer to threshold than B does. The apparent advantage of the event
  drive is confined to the directly stimulated neurons.

Decoder-level comparison: the decoded state counts are identical in every
condition and every stream (67 NEUTRAL windows), so no decoder-level
distinguishability exists between B and any control.

No p-value or confidence interval is reported. The minimum attainable
two-sided permutation p-value for 100 draws would be 0.0099, but the three
streams are segments of one recording and the comparisons are not independent
tests; a p-value here would overstate the evidence.

## 8. Negative and null findings

1. No non-stimulated neuron spiked in any of the 27 runs. The 27-run
   non-stimulated spike total is zero.
2. The first hop receives current but never reaches threshold: 473 of 607
   downstream targets receive current on the full stream, maximum 164.44 pA,
   maximum membrane −56.93 mV, closest deficit 6.93 mV.
3. The second hop receives exactly zero current because the first hop does not
   fire; the 3,576 structurally reachable second-hop targets are silent.
4. The annotation mapping has no first-hop motor targets. The 4 motor neurons
   reachable at two signed hops receive no current.
5. Descending neurons receive first-hop current (9 per stream, maximum 67.21
   pA) but none spikes; the maximum descending membrane voltage is −62.16 mV.
6. Every decoder window is NEUTRAL and every motor-spike count is zero in every
   condition. There is no LEFT, RIGHT or JUMP output from the sensory round
   trip.
7. Actual event structure is not distinguishable from shuffled controls at any
   downstream or decoder endpoint. B-versus-C total-spike differences change
   sign across streams (−198, +117, +108).
8. Feature-identity shuffling changes first-hop peak membrane by only 0.58 mV
   and produces no spike.
9. The random matched mapping produces essentially the same total stimulated
   spike count as the annotation mapping (difference 0.33 ± 0.58), so total
   count cannot validate the mapping.
10. Condition E's descending and ascending spikes are direct spikes of
    stimulated neurons, not propagation; they must not be reported as evidence
    that a random mapping reaches descending populations through synapses.
11. Condition F is silent: 46.70 pA per neuron is below the 150 pA rheobase and
    the membrane settles at −60.33 mV.
12. Condition G is silent, and its noise brings motor neurons closer to
    threshold (7.25 mV deficit) than the event drive does (15.00 mV at rest).
13. No event-locked downstream response exists; downstream alignment is
    undefined and downstream spike count is zero.
14. The stimulated population itself is only partially active: 171 of 232
    neurons on the full stream, and one non-spiking stimulated neuron ends
    0.68 mV short of threshold.

## 9. Limitations

- Structural connectivity is not physiological connectivity. Transmitter sign,
  weight and delay are model priors applied to a structural graph.
- The verified-only sign policy covers 44.48% of threshold-5 edges; the
  remaining edges are excluded and may change propagation if annotated.
- Synaptic weights are monotone transforms of structural synapse counts, not
  measured conductances.
- The 232-neuron sensory mapping is an annotation-defined hypothesis, not a
  measured receptive-field or sensory pathway. The feature-to-population
  assignment is a labelled convention.
- Only 662 of 1,519 outgoing edges from the stimulated set carry a verified
  sign; 0 of the 608 signed targets are motor neurons.
- BANC is one specimen and one dataset export; annotation completeness and
  proofreading are limited. FAFB and BANC identities are never merged.
- Event timestamps are synthesized at 30 fps; event ordering and gaps come from
  the perception pipeline, not from measured times.
- The three streams are non-overlapping segments of one recording group, not
  independent recordings. n = 3 is not an independent replication.
- The drive amplitude (200 pA per feature), pulse decay (150 ms) and all other
  parameters are fixed. The absence of propagation at this drive does not prove
  that the network cannot propagate at another drive or weight.
- A motor spike or decoder label is not a biological motor command. No
  behavioural validation exists.
- The event drive is applied only when events carry feature values; the
  archived replay exposes events, not per-frame game state.

## 10. Verdict

**PASS WITH LIMITATIONS.**

The Phase 4H.4 matrix is complete (27/27 runs), deterministic (6/6 repeat pairs
identical on spike, decision and drive hashes), configuration-verified (47/47
checks) and integrity-verified (all protected files unchanged). The analysis
reproduces every stored run exactly.

Scientifically, the result is a controlled negative:

- The event drive produces reproducible spikes in the directly stimulated
  sensory neurons (3,562 on the full stream; 1,990 and 2,374 on the segments).
- The 662 signed outgoing edges deliver real synaptic current to the first hop,
  but no first-hop, second-hop, descending or motor neuron spikes.
- The actual event sequence is not distinguishable from temporal or
  feature-identity shuffles at any downstream or decoder endpoint.
- The annotation mapping produces no motor output at this drive, and its total
  sensory spike count is nearly identical to a random matched mapping.

This is not an execution failure and not a reason to tune parameters for motor
activity. It establishes the current model's effective propagation limit at the
pre-registered drive and provides the baseline for a pre-registered
drive-threshold experiment. It does not support E3 functional-pathway evidence
or any behavioural claim.
