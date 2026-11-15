# P3-T4.1 four-neuron calibration-point validation

Generated: 2026-11-14T03:03:34.360978+00:00
Repository HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`)
Protocol: `p3_t4_1_four_neuron_validation_v1` — `configs/p3_t4_1_four_neuron_validation.yaml`
Verdict: **PASS** — execution checks passed and primary metrics are defined

## 1. Question and design

Does the four-neuron obstacle-distance population selected in Phase 3A.5 produce a measurably different or better response than the frozen twelve-neuron population under the Phase 3C temporal stimulus framework? Only the obstacle-distance feature is active; all other features receive no current. The simulator, neuron model, synapse model and stimulus schedules are identical across populations.

| Population | Mapping | Encoder bank | Driven cells |
|---|---|---|---|
| P4 | 4 neurons | 4 units | all_mapped |
| P12 | 12 neurons | 12 units | all_mapped |
| P12S | 12 neurons | 12 units | four_neuron_mapping |

## 2. Exact populations (seed 20261104)

### Mapping seed 20261104

| Population | Indices | Root IDs |
|---|---|---|
| P4 | [87389, 108078, 64890, 107895] | [720575940628230223, 720575940632256015, 720575940624132095, 720575940632208971] |
| P12 | [87389, 108078, 64890, 107895, 104235, 52604, 87805, 91895, 7411, 88721, 91920, 125025] | [720575940628230223, 720575940632256015, 720575940624132095, 720575940632208971, 720575940631392220, 720575940621975206, 720575940628302609, 720575940629017606, 720575940609386251, 720575940628443947, 720575940629022961, 720575940638273758] |
| P12S | [87389, 108078, 64890, 107895, 104235, 52604, 87805, 91895, 7411, 88721, 91920, 125025] | [720575940628230223, 720575940632256015, 720575940624132095, 720575940632208971, 720575940631392220, 720575940621975206, 720575940628302609, 720575940629017606, 720575940609386251, 720575940628443947, 720575940629022961, 720575940638273758] |

### Mapping seed 20261105

| Population | Indices | Root IDs |
|---|---|---|
| P4 | [14480, 135717, 3324, 68984] | [720575940612538517, 720575940646382190, 720575940606492350, 720575940624887881] |
| P12 | [14480, 135717, 3324, 68984, 106520, 63388, 12735, 36976, 14892, 48939, 56757, 79823] | [720575940612538517, 720575940646382190, 720575940606492350, 720575940624887881, 720575940631904719, 720575940623881741, 720575940611945058, 720575940618850075, 720575940612668529, 720575940621351302, 720575940622701695, 720575940626970298] |
| P12S | [14480, 135717, 3324, 68984, 106520, 63388, 12735, 36976, 14892, 48939, 56757, 79823] | [720575940612538517, 720575940646382190, 720575940606492350, 720575940624887881, 720575940631904719, 720575940623881741, 720575940611945058, 720575940618850075, 720575940612668529, 720575940621351302, 720575940622701695, 720575940626970298] |

### Mapping seed 20261106

| Population | Indices | Root IDs |
|---|---|---|
| P4 | [128884, 100241, 49729, 1400] | [720575940639975733, 720575940630657792, 720575940621487195, 720575940605179360] |
| P12 | [128884, 100241, 49729, 1400, 116364, 68586, 55737, 38473, 62434, 102596, 70748, 93847] | [720575940639975733, 720575940630657792, 720575940621487195, 720575940605179360, 720575940634698009, 720575940624816637, 720575940622515188, 720575940619219525, 720575940623695896, 720575940631082358, 720575940625211400, 720575940629414897] |
| P12S | [128884, 100241, 49729, 1400, 116364, 68586, 55737, 38473, 62434, 102596, 70748, 93847] | [720575940639975733, 720575940630657792, 720575940621487195, 720575940605179360, 720575940634698009, 720575940624816637, 720575940622515188, 720575940619219525, 720575940623695896, 720575940631082358, 720575940625211400, 720575940629414897] |

## 3. Conditions and seeds

Seeds: [20261104, 20261105, 20261106]. Duration 600.5 ms, frame interval 50.0 ms, 200 pA per neuron, zero background and noise. Conditions: three constant distances, approach, retreat, 100 ms and 200 ms frame rates, no-input control.

## 4. Results

### 4.1 Static distance ordering (stimulated spikes)

| Population | Seed 20261104 | Seed 20261105 | Seed 20261106 | Ordered seeds |
|---|---|---|---|---|
| P4 | [5, 12, 14] | [5, 12, 14] | [5, 12, 14] | 3/3 |
| P12 | [51, 47, 47] | [51, 47, 47] | [51, 47, 47] | 0/3 |
| P12S | [51, 0, 0] | [51, 0, 0] | [51, 0, 0] | 0/3 |

Replication rule (str >= 2 of 3 seeds): P4 True, P12 False, P12S False.

### 4.2 Approach vs retreat

| Population | d' (20261104) | d' (20261105) | d' (20261106) | Separated seeds |
|---|---|---|---|---|
| P4 | 0.1183 | 0.1183 | 0.1183 | 0/3 |
| P12 | 0.0 | 0.0 | 0.0 | 0/3 |
| P12S | -0.184828 | -0.184828 | -0.184828 | 0/3 |

### 4.3 Total spikes by condition and seed

| Condition | P4 | P12 | P12S | P12-P4 consistent |
|---|---|---|---|---|
| constant_0.15 | [5, 5, 5] | [51, 51, 51] | [51, 51, 51] | True |
| constant_0.55 | [12, 12, 12] | [47, 47, 47] | [0, 0, 0] | True |
| constant_0.90 | [14, 14, 14] | [47, 47, 47] | [0, 0, 0] | True |
| approach | [13, 13, 13] | [48, 48, 48] | [9, 9, 9] | True |
| retreat | [12, 12, 12] | [48, 48, 48] | [12, 12, 12] | True |
| frame_rate_200 | [15, 15, 15] | [49, 49, 49] | [3, 3, 3] | True |
| frame_rate_100 | [15, 15, 15] | [50, 50, 50] | [8, 8, 8] | True |
| control_no_input | [0, 0, 0] | [0, 0, 0] | [0, 0, 0] | True |

### 4.4 Frame-rate comparison (stimulated profile cosine to 50 ms)

| Population | 100 ms | 200 ms | Rate above 0.01 in any seed |
|---|---|---|---|
| P4 | {'20261104': 0.198998, '20261105': 0.198998, '20261106': 0.198998} | {'20261104': 0.198998, '20261105': 0.198998, '20261106': 0.198998} | ['100', '200'] |
| P12 | {'20261104': 0.069728, '20261105': 0.069728, '20261106': 0.069728} | {'20261104': 0.060238, '20261105': 0.060238, '20261106': 0.060238} | ['100', '200'] |
| P12S | {'20261104': 0.066436, '20261105': 0.066436, '20261106': 0.066436} | {'20261104': 0.157299, '20261105': 0.157299, '20261106': 0.157299} | ['100', '200'] |

## 5. Hypothesis assessment

- H1 ordering replicates in P4 and not in P12: **True**
- H2 approach/retreat separation in P4 and not in P12: **False**
- H3 measurable difference: see the consistent-direction column in 4.3; a nonzero paired difference is exact, not statistical.
- H4 frame-rate sensitivity: descriptive; a cosine above 0.01 is the Phase 3C threshold, not evidence of a biological code.

## 6. Limitations

- The four-neuron point is a different encoder bank as well as a smaller population: the frozen Phase 3A gaussian encoder places n_neurons preferred stimuli on a linspace, so its four units are not a subset of the twelve units. The primary contrast is therefore configuration-level.
- The twelve-neuron configuration stimulates about three times the number of obstacle-distance cells and injects about three times the total current (per-neuron amplitude is held at 200 pA in both). No amplitude normalisation is applied.
- The P12S control keeps the twelve-neuron encoder and mapping but zeroes current in all but the four cells of the four-neuron mapping; it separates 'more driven cells' from 'four-cell retuning' descriptively.
- Sequences are synthetic GameState lists, not perceived scenes; no detector, tracker or recognition stage is involved.
- Only the mapping seed varies. The simulator is deterministic with zero background and zero noise, so seed spread is mapping-realisation spread.
- Distances are dimensionless image-geometry proxies used by the Phase 3A encoder, not metres.
- Bins within one run are not independent samples; d' is descriptive and the 1.0 threshold is copied from the Phase 3C pre-registration.
- Spikes are model output under configured assumptions, not measured biological activity; no biological superiority is implied by any count.
- No action is selected anywhere in this chain.

## 7. Deviations

- **attempt1_report_render_defect** — render_report read payload['populations'] instead of payload['protocol']['populations'] and raised KeyError after the campaign finished. Protocol effect: none: stimuli, seeds, metrics, thresholds and decision rules were unchanged; only report serialisation was affected Resolution: render_report corrected and the full campaign rerun from scratch; attempt 1 JSON preserved as p3_t4_1_four_neuron_validation_attempt1_report_defect.json

## 8. Artifacts

- `configs/p3_t4_1_four_neuron_validation.yaml`
- `experiments/phase_3c/results/p3_t4_1_preflight.json`
- `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.json`
- `experiments/phase_3c/results/p3_t4_1_four_neuron_validation_attempt1_report_defect.json`
- `experiments/phase_3c/results/p3_t4_1_four_neuron_validation.sidecar.json`
- `experiments/phase_3c/results/p3_t4_1_four_neuron_validation_report.md`
- `experiments/phase_3c/p3_t4_1_four_neuron_validation.py`
- `docs/P3_T4_1_FOUR_NEURON_VALIDATION_PREREGISTRATION.md`
- `tests/test_p3_t4_1_four_neuron_validation.py`
