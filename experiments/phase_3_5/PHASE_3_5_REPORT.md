# Phase 3A.5 — sensory-calibration report

Generated 2026-11-04T14:27:29+00:00 from `configs/sensory_calibration.yaml`.

## Scientific status

This report contains simulated activity only. The game states are experimenter-defined, the encoders are configured assumptions, and the mapped neurons come from predicted FlyWire annotations. No value here is a biological recording or a validated sensory pathway. Calibration selects a model operating point; it does not identify the fly's coding scheme.

## Setup

- Graph: 139,255 neurons, 3,732,460 directed edges, 50,666,648 summed synapses.
- Duration: 300 ms at 0.5 ms timesteps; zero background current and noise.
- Calibrated feature: `obstacle_distance`.
- Distances: 0.15, 0.55, 0.9.
- Conditions run: 84.

## Pre-registered selection rule

A factor group is eligible only if it produced at least one spike and did not recruit the entire stimulated population at every tested level. It is *ordered* only if the three distance levels produced a strictly monotone spike-count sequence; ties are not ordered. Among ordered eligible groups, the largest Poisson signal-to-noise proxy is selected. If no group is ordered, the Phase 3A reference values are retained (200 pA, sigma_fraction 0.20, 12 neurons) and the outcome is reported as a negative result.

## Selected operating point

- Current amplitude: **200 pA**.
- Gaussian sigma_fraction: **0.20**.
- Population size: **4 neurons**.
- Mapping seed: **20261104**.
- Baseline activation: **0**.
- Selection sources: {"amplitude": "fallback_no_ordered_amplitude", "tuning": "fallback_no_ordered_tuning", "population": "ordered"}.
- Fallbacks: ["amplitude", "tuning"].

## Decision rule

| Check | Result |
|---|---|
| `no_failures` | True |
| `reproducibility_passed` | True |
| `ordered_in_at_least_two_seeds` | True |
| `responsive_high_level` | True |
| `not_fully_saturated` | True |
| `avoids_sub_rheobase` | True |
| `additivity_reported` | True |
| `runtime_reported` | True |

**Overall: PASS**

An operating point met every pre-registered check. It is the recommended Phase 3B input setting, within the model's assumptions.

## Amplitude and recruitment

| Amplitude (pA) | Spikes at distances | Ordered | d' proxy | Max recruited |
|---:|---|---|---:|---:|
| 100 | 0 / 0 / 0 | False | 0.0 | 0.00 |
| 125 | 0 / 0 / 0 | False | 0.0 | 0.00 |
| 150 | 0 / 0 / 0 | False | 0.0 | 0.00 |
| 175 | 12 / 14 / 14 | False | 0.5547 | 0.25 |
| 200 | 24 / 23 / 23 | False | 0.206284 | 0.33 |
| 225 | 35 / 32 / 33 | False | 0.342997 | 0.33 |
| 250 | 43 / 46 / 41 | False | 0.308607 | 0.42 |
| 300 | 62 / 63 / 55 | False | 0.915209 | 0.42 |

## Tuning width

| Amplitude (pA) | Sigma | Spikes at distances | Ordered | d' proxy |
|---:|---:|---|---:|---:|
| 200 | 0.05 | 5 / 9 / 9 | False | 1.511858 |
| 200 | 0.10 | 14 / 9 / 9 | False | 1.47442 |
| 200 | 0.20 | 24 / 23 / 23 | False | 0.206284 |
| 200 | 0.30 | 36 / 36 / 31 | False | 0.863868 |
| 200 | 0.50 | 46 / 62 / 45 | False | 0.14825 |

## Population size

| Neurons | Spikes at distances | Spikes/neuron at distances | Ordered | d' proxy |
|---:|---|---|---|---:|
| 4 | 2 / 6 / 7 | 0.50 / 1.50 / 1.75 | True | 2.357023 |
| 8 | 15 / 14 / 15 | 1.88 / 1.75 / 1.88 | False | 0.0 |
| 12 | 24 / 23 / 23 | 2.00 / 1.92 / 1.92 | False | 0.206284 |
| 16 | 32 / 32 / 32 | 2.00 / 2.00 / 2.00 | False | 0.0 |
| 24 | 48 / 50 / 47 | 2.00 / 2.08 / 1.96 | False | 0.145095 |

## Mapping seeds

- Seeds: [20261104, 20261105, 20261106].
- Ordered seeds: [20261104, 20261105, 20261106] (3/3).
- Criterion (at least two ordered seeds): True.

| Distance | Counts across seeds | Mean | SD |
|---|---:|---:|---:|
| 0.15 | [2, 2, 2] | 2.0 | 0.0 |
| 0.55 | [6, 6, 6] | 6.0 | 0.0 |
| 0.9 | [7, 7, 7] | 7.0 | 0.0 |

## Additivity

- Obstacle alone: 9 spikes.
- Coin alone: 23 spikes.
- Both: 32 spikes.
- Expected additive excess: 32.
- Additivity index: 0.0.

index 0 is additive; positive means super-additive; negative means sub-additive. Network recurrence affects this value.

## Transitions

| Crossfade (ms) | Spikes | Active neurons | First latency (ms) | Peak feature current (pA) |
|---:|---:|---:|---:|---:|
| 0 | 4 | 2 | 38.0 | 289.493025 |
| 10 | 4 | 2 | 38.0 | 289.493025 |
| 25 | 4 | 2 | 38.0 | 289.493025 |
| 50 | 4 | 2 | 38.0 | 289.493025 |
| 100 | 3 | 1 | 38.0 | 289.493025 |

## Activation baseline

| Baseline | Spikes at distances | Ordered | d' proxy | Max recruited |
|---:|---|---|---:|---:|
| 0 | 2 / 6 / 7 | True | 2.357023 | 0.25 |
| 0.1 | 4 / 6 / 7 | True | 1.279204 | 0.25 |
| 0.2 | 5 / 6 / 7 | True | 0.816497 | 0.25 |

## Controls

| Condition | Feature | Amplitude (pA) | Spikes | Active | Recruited |
|---|---|---:|---:|---:|---:|
| `a5_control_coin_amp100` | `coin_distance` | 100 | 0 | 0 | 0.00 |
| `a5_control_coin_amp300` | `coin_distance` | 300 | 63 | 5 | 0.42 |
| `a5_control_player_amp100` | `player_speed` | 100 | 0 | 0 | 0.00 |
| `a5_control_player_amp300` | `player_speed` | 300 | 64 | 6 | 0.50 |

The 100 pA and 300 pA obstacle-distance controls are the first and last rows of the amplitude table.

## Performance

- Baseline (no schedule): 1.175 s, 510.5 steps/s.
- Calibration mean: 1.421 s, 425.6 steps/s.
- Added runtime: 0.246 s (20.95% of baseline).
- Retained arrays: 134.73 MB; mean RSS change -2.23 MB.

A negative added runtime means the single no-input baseline ran slower than the calibrated conditions in this process; it is measurement noise, not a speedup.

## Reproducibility

- Condition: `a5_1_amp200_dist0p15`.
- Separate processes: 2.
- Input hash equal: True.
- Spike hash equal: True.
- Transmissions equal: True.
- Passed: True.

## Failures

- No condition or setup failures were recorded.

## Limitations

- A calibrated operating point is a model choice, not a biological finding.
- The strict monotonicity rule is deliberately conservative; a flat response is reported as flat.
- The Poisson d' proxy is a descriptive signal-to-noise ratio of simulated spike counts, not a behavioural discrimination measure.
- Additivity is affected by recurrent network activity and by shared downstream targets; it is not a property of the encoders alone.
- Only one feature, one duration, one game-state family and one connectome artifact were tested.
- No motor readout, reward, plasticity or perception is present.

## Next milestone

Phase 3B should use the selected operating point (or the documented reference fallback) when it integrates perceived scenes with the Phase 3A encoder. Perception errors must be reported separately from neural calibration.
