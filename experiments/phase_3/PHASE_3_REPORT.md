# Phase 3A — sensory encoding report

Generated 2026-11-04T12:56:31+00:00 from the configuration `configs/sensory_config.yaml`.

## Scientific status

This report contains simulated activity only. Game states are experimenter-defined scenes, Gaussian/lane/boolean coding is a computational choice, and the mapped neurons are drawn from predicted FlyWire annotations. No pathway here is anatomically verified and no firing pattern is a biological recording.

## Setup

- Graph: 139,255 neurons, 3,732,460 directed edges, 50,666,648 summed synapses.
- Simulation: dt 0.5 ms, 14 features, 138 mapped neurons, 50.0 ms transitions.
- Seed: 20261104.

## Mapping

| Feature | Neurons | Pool(s) |
|---|---:|---|
| `player_lane` | 12 | `visual_center`, `visual_left`, `visual_right` |
| `obstacle_lane` | 12 | `visual_center`, `visual_left`, `visual_right` |
| `train_lane` | 12 | `visual_center`, `visual_left`, `visual_right` |
| `coin_lane` | 12 | `visual_center`, `visual_left`, `visual_right` |
| `obstacle_type` | 12 | `visual_any` |
| `jumping` | 6 | `mechanosensory` |
| `rolling` | 6 | `mechanosensory` |
| `player_speed` | 12 | `visual_any` |
| `obstacle_present` | 6 | `visual_any` |
| `obstacle_distance` | 12 | `visual_any` |
| `train_present` | 6 | `visual_any` |
| `train_distance` | 12 | `visual_any` |
| `coin_present` | 6 | `visual_any` |
| `coin_distance` | 12 | `visual_any` |

All populations are experimental input populations drawn from predicted annotations. See `docs/PHASE_3_SENSORY_ENCODING.md` and the per-feature root IDs in `results/mapping_report.json`.

## Protocol results

| Condition | Protocol | Active features | Stimulated | Spikes | Active | Mean Hz | Max Hz | Runtime s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `single_obstacle_distance_0p90` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 167 | 19 | 0.004 | 30.0 | 1.903 |
| `single_obstacle_distance_0p55` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 167 | 19 | 0.004 | 30.0 | 2.017 |
| `single_obstacle_distance_0p15` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 168 | 20 | 0.004 | 30.0 | 2.393 |
| `single_obstacle_lane_left` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 172 | 20 | 0.004 | 36.7 | 2.208 |
| `single_obstacle_lane_center` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 169 | 20 | 0.004 | 30.0 | 2.171 |
| `single_obstacle_lane_right` | single | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 169 | 20 | 0.004 | 30.0 | 2.174 |
| `single_coin_distance_0p90` | single | coin_present, coin_lane, coin_distance | 30 | 113 | 13 | 0.003 | 30.0 | 1.837 |
| `single_coin_distance_0p55` | single | coin_present, coin_lane, coin_distance | 30 | 113 | 13 | 0.003 | 30.0 | 2.553 |
| `single_coin_distance_0p15` | single | coin_present, coin_lane, coin_distance | 30 | 114 | 14 | 0.003 | 30.0 | 3.153 |
| `single_player_speed_0p20` | single | player_lane, player_speed | 24 | 59 | 7 | 0.001 | 30.0 | 2.689 |
| `single_player_speed_0p50` | single | player_lane, player_speed | 24 | 60 | 8 | 0.001 | 30.0 | 2.731 |
| `single_player_speed_0p90` | single | player_lane, player_speed | 24 | 59 | 7 | 0.001 | 30.0 | 2.676 |
| `single_jumping_false` | single | jumping | 6 | 0 | 0 | 0.000 | 0.0 | 2.243 |
| `single_jumping_true` | single | jumping | 6 | 54 | 6 | 0.001 | 30.0 | 1.925 |
| `single_rolling_false` | single | rolling | 6 | 0 | 0 | 0.000 | 0.0 | 1.847 |
| `single_rolling_true` | single | rolling | 6 | 54 | 6 | 0.001 | 30.0 | 2.463 |
| `combined_obstacle_and_coin_other_lane` | combined | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type, coin_present, coin_lane, coin_distance | 72 | 285 | 33 | 0.007 | 36.7 | 2.333 |
| `combined_train_and_player_center` | combined | train_present, train_lane, train_distance, player_lane, player_speed | 54 | 203 | 29 | 0.005 | 30.0 | 2.258 |
| `combined_high_speed_obstacle_near` | combined | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type, player_lane, player_speed | 66 | 226 | 26 | 0.005 | 30.0 | 2.215 |
| `combined_obstacle_and_coin_same_lane` | combined | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type, coin_present, coin_lane, coin_distance | 72 | 283 | 32 | 0.007 | 36.7 | 2.203 |
| `combined_jumping_train_approach` | combined | train_present, train_lane, train_distance, player_lane, player_speed, jumping | 60 | 258 | 35 | 0.006 | 30.0 | 2.232 |
| `sequence_obstacle_approach` | sequence | obstacle_present, obstacle_lane, obstacle_distance, obstacle_type | 42 | 332 | 26 | 0.003 | 22.5 | 5.174 |
| `sequence_coin_approach` | sequence | coin_present, coin_lane, coin_distance | 30 | 224 | 20 | 0.002 | 22.5 | 5.239 |

## Observed response structure

- `single_obstacle_distance_`: `single_obstacle_distance_0p90`=167, `single_obstacle_distance_0p55`=167, `single_obstacle_distance_0p15`=168.
- `single_obstacle_lane_`: `single_obstacle_lane_left`=172, `single_obstacle_lane_center`=169, `single_obstacle_lane_right`=169.
- `single_coin_distance_`: `single_coin_distance_0p90`=113, `single_coin_distance_0p55`=113, `single_coin_distance_0p15`=114.
- `single_player_speed_`: `single_player_speed_0p20`=59, `single_player_speed_0p50`=60, `single_player_speed_0p90`=59.

Across these single-feature sweeps the spike count changed by at most 3 spikes. With a 200 pA drive and a 150 pA rheobase, a neuron tuned within a small fraction of the stimulus range can still cross threshold, so this readout is threshold-dominated. Near-identical counts do not demonstrate graded coding, and different counts would not demonstrate biological coding either.

## Performance

- Baseline (no sensory schedule): 1.933 s wall, 310.5 steps/s.
- Sensory condition mean: 2.296 s wall, 266.1 steps/s.
- Additional runtime per condition: 0.364 s (18.83% of baseline).
- Retained simulation arrays: 134.73 MB; mean RSS change during a run: -0.53 MB.

## Reproducibility

- Compared condition: `combined_obstacle_and_coin_other_lane`.
- Separate processes: 2.
- Input signature equal: True.
- Spike signature equal: True.
- Spike count: 285 in each run.

## Limitations

- Gaussian population coding is an experimental computational choice, not evidence for the fly's sensory code.
- Mapped neurons carry predicted annotations; feature assignment is artificial and may target cells that do not process that feature.
- A peak drive of 200 pA is a model calibration above the LIF rheobase, not a measured current.
- The connectome is a female adult FAFB brain without a ventral nerve cord; no motor pathway or behaviour is decoded in Phase 3A.
- One seed and one set of amplitudes were used; sensitivity to tuning width, population size and current amplitude is not yet characterised.

## Next step

Phase 3B should add screenshot-based visual perception as a separate layer, so perception errors can be measured independently of the neural encoding studied here.
