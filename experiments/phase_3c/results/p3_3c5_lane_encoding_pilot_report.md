# P3-3C.5 lane encoding report

Generated: 2026-11-15T05:05:13.812542+00:00
Repository HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`)
Campaign: `pilot` — protocol `p3_3c5_lane_encoding_v1`
Outcome: **PILOT ONLY**

## 1. What the outcome does and does not mean

The outcome is a descriptive classification of a deterministic simulation under the configured model. It is not a significance test, not a biological claim and not a claim about a neural code.

## 2. Per-seed primary values

| Seed | P1 (C1-C2) Hz | P2 (C3-C4) Hz | K_C Hz |
|---|---|---|---|

## 3. Primary per-bin and per-neuron values

## 4. Reference values and predicates

| Seed | R200 pred-LEFT | R200 pred-RIGHT | SEPARATED_200 | R150 pred-LEFT range | R150 pred-RIGHT range | SEPARATED_150 |
|---|---|---|---|---|---|---|

## 5. Activity, outside fraction and current audit

| Seed | Gate failures | Outside fraction range | Active neurons per group/bin | Current min/max pA |
|---|---|---|---|---|

## 6. Gate results

- Seed 20261107: failed gates []

## 7. Limitations

- Descriptive, not inferential: no p-value, confidence interval or significance claim is made.
- Three mapping seeds and four neurons per group support no population inference; exact per-seed values and the range are reported.
- The lane encoder is one-hot by construction; the experiment tests the spiking readout's history dependence, not how a fly encodes lane.
- Predecessor identity is confounded with predecessor annotation pool (LEFT, CENTER and RIGHT use different pools).
- The visual_any pool-matched control is excluded by decision D9 and is not run.
- K_C is matched in time since onset but not in absolute time; transition-onset attribution is caveated.
- R200 is a one-versus-one reference and cannot support a distributional interpretation.
- P2 (C3 vs C4) is a dwell replication, not a perfectly matched primary contrast.
- P3 (final LEFT block) is confounded with the last transition route R->L versus C->L.
- C3 and C4 are not matched on transition-type order or per-time lane; that is the order manipulation itself.
- There is no synapse-block control; outside activity is measured, not subtracted.
- Lane-only input is not the natural full-sensory regime and does not generalise to it.
- The model has no adaptation or short-term plasticity; any history effect is short-lived.
- T5 lane pulses are not implemented; T2/T3 encodings are out of scope.
- Structural data are not physiological; synapses and weights are computational approximations.
- The final 0.5 ms tail is excluded from binning and reported separately.
- The small reference sets cannot substitute for more sequences or more seeds.
- Determinism is not robustness; identical repeat hashes do not establish generalisation.
- The causal decomposition C1/C2 versus L->C/R->C is a correctness gate, not independent evidence.
- With n = 3, no standard deviation or standard error is reported.
- The crossfade is causal and one-sided, so it is not time-reversal equivariant.
- Frame-sequence reversal does not imply input-current-waveform reversal under the causal scheduler.
- Half-open frame boundaries produce endpoint mismatches; no continuous-time reversal is claimed.
- C3/C4 remain secondary route/order comparisons; no perfect matching is claimed.

## 8. Claims not made

No p-value, significance claim, confidence interval, biological claim, learning claim, code claim or generalisation is made. A 2-of-3 pattern is written as '2 of 3 mapping realisations'. Descriptive effects are written as 'under the configured model'.
