# P3-T7 — Phase 3C temporal acceptance experiments

Generated: 2026-11-13T19:31:25.513804+00:00
Verdict: **NEGATIVE_RESULT**

## Scope

Synthetic `GameState` sequences over the sparse full connectome, executing the milestone decision rule in `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` section 6.4. The stimuli were pre-registered in `configs/temporal_sensory.yaml` before execution because the design fixes the comparisons but not the exact sequences.

## Decision rule

| Item | Result |
|---|---|
| 1. No failure | True |
| 2. 3C.1 static equivalence | True |
| 3. 3C.2 approach vs retreat | False |
| 4. 3C.7 frame-rate quantified | True |
| 5. 3C.9 controls | measurable_difference |

## 3C.1 — constant sequence vs static schedule

| Distance | Max current difference (pA) | Steps above tolerance | Spike counts identical | Temporal spikes | Direct spikes |
|---:|---:|---:|---|---:|---:|
| 0.15 | 0.0 | 0 | True | 463 | 463 |
| 0.55 | 0.0 | 0 | True | 459 | 459 |
| 0.9 | 0.0 | 0 | True | 459 | 459 |

## 3C.2 — approach vs retreat

| Seed | d' (distance population) | d' (network) | Cosine distance | Difference norm | Seed spread | Ratio | Total spikes A/R |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261104 | 0.0 | 0.0 | 0.014517 | 2.44949 | 0.0 | None | 460 / 460 |
| 20261105 | 0.0 | 0.0 | 0.014517 | 2.44949 | 0.0 | None | 460 / 460 |
| 20261106 | 0.0 | 0.0 | 0.014517 | 2.44949 | 0.0 | None | 460 / 460 |

Leave-one-seed-out nearest-centroid accuracy: **1.0** over 6 predictions.

Reading: approach and retreat produced identical total spike counts and time-reversed distance-population profiles in every seed. The signed d' on binned totals is 0.0 because time reversal preserves the mean and variance. The nearest-centroid result reflects the order of the bins, not a difference in response magnitude. Under the pre-registered d' criterion, direction is not distinguished.

## 3C.3 / 3C.4 — entry and exit timing

| Entry (ms) | First-spike latency (ms) | Median onset latency (ms) | Post-onset 50 ms count | Peak bin (ms) |
|---:|---:|---:|---:|---:|
| 100 | 28.0 | 35.0 | 3 | 250.0 |
| 200 | 28.0 | 35.0 | 3 | 350.0 |
| 300 | 28.0 | 35.0 | 3 | 450.0 |

| Exit (ms) | Pre-offset 100 ms count | Post 50 ms | Post 100 ms | Post 250 ms | Persistence (ms) |
|---:|---:|---:|---:|---:|---:|
| 200 | 8 | 0 | 0 | 0 | 0.0 |
| 400 | 8 | 0 | 0 | 0 | 0.0 |

Reading: the scheduler applies the most recent frame. An absent frame therefore replaces the present state at the next frame boundary, so post-exit persistence is zero by construction; it is not a membrane after-discharge measurement.

## 3C.7 — frame-rate sensitivity

Membrane time constant: 20.0 ms.

| Frame interval (ms) | Frames | Current RMS diff (pA) | Current max diff (pA) | Cosine distance | Total spikes |
|---:|---:|---:|---:|---:|---:|
| 200 | 4 | 0.394752 | 105.665031 | 0.060238 | 461 |
| 100 | 7 | 0.1548 | 37.599625 | 0.069728 | 462 |
| 50 | 13 | 0.0 | 0.0 | -0.0 | 460 |

Reading: all tested intervals exceed the 20 ms membrane time constant, so each condition quantises the timing of distance steps to its interval (up to 200 ms). Network spike profiles changed only slightly across rates; the frame-rate comparison is quantified, not evidence that the network resolves the membrane timescale.

## 3C.9 — controls

| Control | Total spikes | Cosine distance to approach |
|---|---:|---:|
| no_input | 0 | None |
| shuffled | 453 | 0.000722 |
| dropped_frame | 462 | 0.000476 |

Shuffled distance-profile cosine distance: 0.073544; reversed: 0.014517. Measurable difference: True.

## Limitations

- Sequences are synthetic GameState lists, not perceived scenes; no detector, tracker or recognition accuracy is involved.
- The obstacle-distance population has twelve neurons, not the four selected in Phase 3A.5; this is not the calibrated operating point (see P3-T4).
- Only the mapping seed varies. The simulator is deterministic with zero background and noise, so 'seed spread' is a mapping-realisation spread, not biological or runtime variability.
- The pre-registered d' threshold of 1.0 is a new operationalisation: the design says 'above the seed-to-seed spread' but does not fix a numeric cut-off.
- Bins within one run are not independent samples; d' is descriptive.
- The implemented scheduler is sample-and-hold plus decaying lifecycle pulses. The design's T1 crossfade and T2 smoothing variants are not implemented, so 3C.1 tests equivalence of the implemented path only.
- Conditions 3C.5 (lane ordering), 3C.6 (jump/roll intervals) and 3C.8 (T1/T2/T3 ablation) are not executed.
- Spikes are model output under configured assumptions, not measured biological activity.
- No action is selected anywhere in this chain.

## Artifact hashes

- JSON: `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc`
- config: `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4`
- connectome: `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`
