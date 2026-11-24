# Source and Evidence Register

**Paper:** *Teaching a Fruit Fly Brain to Play Subway Surfers Through Connectome-Based Neural Simulation: Architecture, Learning Mechanisms, Experimental Evaluation, and Motor-Output Limitations*
**Paper document version:** 1.1 — 24 November 2026 (author: metadore)
**Paper licence:** Creative Commons Attribution 4.0 International (CC BY 4.0), © 2026 metadore — https://creativecommons.org/licenses/by/4.0/. Applies to the original paper text, tables and figures only; third-party datasets and assets retain their own licences and attribution (see `LICENSE`).
**Register version:** 1.1 — 24 November 2026 (adds the YOLO11n visual-documentation figures 9–14 and the +6 renumbering of the former figures 9–33)
**Scope:** every substantive quantitative or factual claim in the manuscript, traced to a repository file and, where the file is structured, to a field, table, or record.

## How to read this register

Each row has six fields.

| Field | Meaning |
|---|---|
| **Claim ID** | Stable identifier. Prefixes group rows by chapter: `D3` data, `A4` architecture, `P5` perception, `S6` simulation, `M7` motor, `L8` plasticity, `C9` chronology, `I10` Phase 6, `G11` Phase 7, `E12` Phase 8 design, `P1` Pilot 1, `B14` bottleneck, `T15` training, `P2C` Pilot 2-C, `K17` consolidated, `X18`–`X21` discussion and outlook, `U` unavailable endpoints. |
| **Research claim** | The claim as it appears, or is directly implied, in the manuscript. |
| **Source file** | Path relative to the repository root. All paths were read-only inputs; none was modified. |
| **Exact evidence** | The value, field, key, row, or statement that supports the claim. Decimal values are quoted as stored. |
| **Evidence type** | `RM` recorded measurement from an executed run; `AS` artifact summary or derived aggregate; `IT` implementation test on fixtures or synthetic input, not biological evidence; `PD` pre-registered or frozen definition; `INT` interpretation stated by the paper and not itself a measurement; `NA` endpoint declared unavailable. |
| **Paper section** | Chapter and section where the claim is made. |

**Rules applied.** A claim is registered once, at the section where it is first and most fully stated; later restatements are not duplicated unless the paper adds a distinct number. Where the manuscript reports a discrepancy between two records, the register cites both records and the value the paper adopts. Where an endpoint could not be estimated, the register records the artifact that was inspected and the reason, under evidence type `NA`. No citation in the References list is used as evidence for a project result; references support background and method only.

**Reproduction.** The stored artifacts, not this register, are the authoritative record. Tables T01–T21 under `research_paper/tables/` restate the values used here in machine-readable form, and `research_paper/scripts/extract_tables.py` rebuilds them from the repository artifacts. Read-only entry points and environment versions are listed in Appendix K of the paper (`src/23_appendices.md`).

---

## 1. Data and connectome construction (Chapter 3)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| D3-01 | The FAFB graph contains 139,255 neurons, 3,732,460 directed pairs at the ≥5-synapse threshold, and 50,666,648 summed synapses | `datasets/processed/connectome_report.json`; `datasets/processed/connectome.npz` | node_count 139,255; edge_count 3,732,460; synapse sum 50,666,648; file 28,013,212 bytes | AS | 3.2, Table 2 |
| D3-02 | 671 neurons are isolated in the retained FAFB graph | `datasets/processed/connectome_report.json` | isolated_nodes = 671 | AS | 3.2, Table 2 |
| D3-03 | FAFB edge weight is heavy-tailed: min 5, median 8, mean 13.575, p95 38, p99 87, max 2,633 | `datasets/processed/connectome.npz` (`edge_weight`) | computed quantiles of `edge_weight`; mean 13.575; max 2,633 | AS | 3.2, Figure 3 |
| D3-04 | FAFB out-degree mean is 26.803 and maximum 6,523; in-degree maximum 6,261 | `datasets/processed/connectome.npz` (`out_indptr`, `in_indptr`) | degree arrays differenced along the index pointers; maxima 6,523 / 6,261 | AS | 3.2, Figure 3 |
| D3-05 | There are 620,180 directed reciprocal pairs (310,090 unordered) | `datasets/processed/connectome_report.json` | reciprocal_edges = 620,180 | AS | 3.2 |
| D3-06 | 119,597 FAFB neurons carry at least one annotation and 19,658 lack a predicted transmitter | `datasets/processed/nodes.csv.gz` | `nt_type` non-null count 119,597; missing 19,658 | AS | 3.3 |
| D3-07 | FAFB transmitter composition: 82,298 ACh, 19,605 GLUT, 16,017 GABA, 1,021 SER, 584 DA, 72 OCT | `datasets/processed/nodes.csv.gz` | value counts of `nt_type` | AS | 3.3 |
| D3-08 | FAFB super-class composition sums exactly to 139,255, from optic 77,873 to endocrine 80 | `datasets/processed/nodes.csv.gz` | value counts of `super_class`; sum 139,255 | AS | 3.3, Table B1 |
| D3-09 | The FAFB motor super-class has 110 neurons and none is a limb motor neuron | `datasets/processed/nodes.csv.gz`; `reports/PHASE_4A_*` compatibility audit | `super_class = motor` count 110; audit records no leg motor neuron | AS | 3.3, 3.6 |
| D3-10 | BANC v888 has 172,433 endpoints after excluding 16,075 metadata-only rows | `datasets/processed/banc_v888/banc_construction_report.json` | metadata_rows 188,508; excluded 16,075; endpoints 172,433 | AS | 3.4, Table 2 |
| D3-11 | BANC self-edges are removed before thresholding: 156,311 edges and 1,422,866 self-loop synapses | `datasets/processed/banc_v888/banc_construction_report.json` | self_edges 156,311; self_synapses 1,422,866; non-self edges 11,596,517 | AS | 3.4 |
| D3-12 | BANC threshold sensitivity: t1 = 11,596,517 edges / 34,310,230 synapses; t5 = 1,535,710 / 18,552,546; t10 = 570,721 / 12,397,230 | `datasets/processed/banc_v888/banc_construction_report.json` | per-threshold `edge_count`, `synapse_sum` | AS | 3.4, Table 2, Table B2 |
| D3-13 | t5 retains 13.2429% of pairs and 54.0729% of synapses; t10 retains 4.9215% and 36.1328% | `datasets/processed/banc_v888/banc_construction_report.json` | retention fields | AS | 3.4, Table B2 |
| D3-14 | Maximum summed synapses per edge is 913 at t1, t5, and t10 | `datasets/processed/banc_v888/banc_construction_report.json` | `weight_max` = 913 for each threshold | AS | 3.4, Table B2 |
| D3-15 | BANC super-class composition sums to 172,433, from optic_lobe_intrinsic 72,826 to ascending_visceral_circulatory 5 | `datasets/processed/banc_v888/banc_nodes.csv.gz` | value counts of `super_class`; sum 172,433 | AS | 3.5, Table B3 |
| D3-16 | BANC annotation coverage: super_class 88.069%, cell_type 68.2045%, side 91.7429%, body_part_effector 0.5968%, proofread 100% | `datasets/processed/banc_v888/banc_construction_report.json` | coverage fields | AS | 3.5, Figure 5 |
| D3-17 | BANC predicted transmitters cover 89.27% of nodes; 37.87% are verified | `datasets/processed/banc_v888/banc_construction_report.json` | nt predicted / verified coverage | AS | 3.5, 6.2 |
| D3-18 | Sixteen null graphs were built and certified, one per campaign seed | `experiments/results/phase_8_random/` certificate records; `reports/PHASE_8_*RANDOM*` | seeds 1–16, each with a certification record | AS | 12.3 |
| D3-19 | The game dataset v15 holds 2,328 images, 2,328 labels, and 8,666 boxes, split 1,825/503 with no test split | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` | image_count 2,328; box_count 8,666; split counts | AS | 5.3, Table 1 |
| D3-20 | 554 of 1,724 adjacent frame pairs (32.1%) cross the official split; 224 near-duplicates exist, 58 crossing | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` | adjacency and duplicate fields | AS | 5.3 |
| D3-21 | The detector is YOLO11n ONNX, 10,636,871 bytes, SHA-256 `e6ad18f9…6aa77` | `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx`; `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` | file size and hash; registry entry | AS | 5.2 |
| D3-22 | Published detector metrics: precision 0.937310, recall 0.810829, mAP50 0.897776, mAP50-95 0.687726 on 1,128 validation images | `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md`; `reports/PHASE_3B2B*` | metric table; recorded as external provenance, not re-measured | AS | 5.2 |
| D3-23 | The controlled environment is the standalone `endless-surfer` runner; commercial Subway Surfers was never instrumented | repository structure; `reports/PHASE_7_*` | no commercial-game integration exists; environment package is local | AS | 1.6, 5.2 |

## 2. Model and architecture (Chapters 4 and 6)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| A4-01 | LIF parameters: C_m 200 pF, g_L 10 nS, V_rest −65 mV, V_th −50 mV, V_reset −68 mV, refractory 2 ms, floor −90 mV, dt 0.5 ms | `configs/neuron_config.yaml` | parameter entries | PD | 4.3, 6.1, Table 4, Table C1 |
| A4-02 | Membrane time constant is 20 ms and rheobase is 150 pA | `configs/neuron_config.yaml` | τ_m = C/g = 20 ms; (V_th − V_rest) × g = 150 pA | AS | 6.1 |
| A4-03 | Integration is the exact exponential-Euler update at dt = 0.5 ms | `simulation/` engine; `configs/simulation_config.yaml` | update rule in code; dt entry | PD | 6.1 |
| A4-04 | Synaptic decay is τ_exc 5 ms and τ_inh 8 ms with a uniform 1 ms delay | `configs/simulation_config.yaml` | tau_exc 5, tau_inh 8, delay 1 | PD | 6.2, Table C2 |
| A4-05 | FAFB weight transform is 12·count^0.75 pA; BANC is min(5.0·count^0.75, 300) pA | `configs/banc_synapse_policy.yaml`; `configs/simulation_config.yaml` | transform constants 12 / 5.0 / cap 300 | PD | 6.2 |
| A4-06 | The verified-only sign policy admits 44.48% of BANC t5 edges (683,100 of 1,535,710) and excludes 852,610 | `configs/banc_synapse_policy.yaml`; `experiments/results/phase_8/pilot2c/.../manifest.json` | signed_edges 683,100; total 1,535,710; excluded 852,610 | AS | 6.2, 14.6 |
| A4-07 | Signed BANC t5 edges carry 8,426,168 synapses | `datasets/processed/banc_v888/banc_construction_report.json`; sign-policy output | signed synapse sum | AS | 6.2 |
| A4-08 | FAFB replay classified 2,955,795 edges excitatory and 776,665 inhibitory | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | sign counts | AS | 6.2 |
| A4-09 | Motor decoder: 50 ms half-open windows; activation 0.20; release 0.10; gate ≥5 spikes and ≥3 active; highest fraction wins; LEFT→RIGHT→JUMP tie order; else NO_ACTION | `configs/motor_decoder.yaml` | decoder constants | PD | 7.2, Table C3 |
| A4-10 | Decoder pools are LEFT 185, RIGHT 186, JUMP 20, unassigned 414 | `configs/motor_decoder.yaml`; BANC motor annotations | pool sizes | AS | 7.2, Table 7 |
| A4-11 | Plasticity rule is Δw = η·M(t)·e(t), τ_e 20 ms, bounds 0.5–2.0×, max |Δw| 5 pA, τ_M 50 ms, clip ±5, gain 1.0 | `configs/plasticity_banc.yaml` | parameter entries | PD | 8.4, Table C4 |
| A4-12 | Phase 8 uses η = 0.5; the A′ control uses η = 0; Phase 5F used η = 1.0 | `configs/plasticity_banc.yaml`; `configs/phase_8/conditions.yaml`; `experiments/results/phase_5f/comparison_analysis.json` | eta values per arm | PD | 8.4, 12.2 |
| A4-13 | The simulation engine is pure NumPy on CPU with CSR storage | `simulation/` engine source | imports and adjacency structure | AS | 6.3 |

## 3. Perception and sensory encoding (Chapter 5)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| P5-01 | 12 of the 2,328 v15 images have empty labels | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` | empty_label_count 12 | AS | 5.3 |
| P5-02 | The curated split is 1,188 train / 1,128 validation and no independent test set exists | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` | curated split counts; `test = none` | AS | 5.3 |
| P5-03 | Detector confidence is 0.426 and NMS IoU 0.7, with 14 classes | `configs/perception*.yaml`; `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` | conf 0.426; iou 0.7; classes 14 | PD | 5.2 |
| P5-04 | The 3B.2C replay ran 100 frames (100–199) of `datasetfootage` over 3,300.5 ms and 6,601 steps | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | frame_start 100; frame_end 199; duration 3,300.5 ms; steps 6,601 | RM | 5.4 |
| P5-05 | The replay produced 15,654,631 spikes and 996,524,829 transmissions | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | total_spikes; transmission_count | RM | 5.4, 5.6 |
| P5-06 | 35,979 neurons were active (25.84%) | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | active_neurons 35,979 | RM | 5.6, Figure 16 |
| P5-07 | The 138 stimulated neurons produced 3,710 spikes, 0.0237% of the total; 72 fired (52.17%) | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` (`activity_by_stimulation`) | stimulated_spikes 3,710; share 0.000237 | RM | 5.6, Figure 16 |
| P5-08 | The replay ran the full 139,255-neuron FAFB graph at 81.93 steps/s | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | steps_per_second 81.93 | RM | 5.4, 6.3 |
| P5-09 | The FAFB sensory mapping uses 14 features over 138 neurons with 50 ms transitions, 200 pA, σ = 0.20 | `configs/sensory*.yaml`; `reports/PHASE_3A*` | mapping table | PD | 5.5 |
| P5-10 | The BANC mapping uses 7 features over 232 neurons: train_lane 48, obstacle_lane 48, obstacle_type 24, train_present 24, obstacle_present 24, train_distance 32, obstacle_distance 32 | `configs/banc_sensory_mapping.yaml`; `research_paper/tables/T05_sensory_features.csv` | per-feature neuron counts; sum 232 | PD | 5.5, Table 5 |
| P5-11 | BANC sensory drive is 200 pA with a 150 ms pulse decay; player pose and coins are unmapped | `configs/banc_sensory_mapping.yaml` | current 200 pA; decay 150 ms; unmapped fields | PD | 5.5 |
| P5-12 | The BANC mapping seed is 20261109 | `configs/banc_sensory_mapping.yaml` | seed entry | PD | 5.5 |
| P5-13 | The Phase 3A.5 four-neuron population produced spike counts 2 / 6 / 7 at distances 0.15 / 0.55 / 0.90 across three seeds, with d′ = 2.357 | `experiments/results/phase_3a5/` calibration summary; `reports/PHASE_3A5*` | per-distance counts; d-prime | RM | 5.5, 10.4 |
| P5-14 | Figures 9–10 show six unmodified curated training images and their label-file boxes | `research_paper/figures/yolo11_visuals/PROVENANCE.json`; `datasets/exports/phase_3b2b1_yolo11n/train` | six image SHA-256 values, label SHA-256 values and ground-truth boxes; labels converted class cx cy w h to pixels with the 606×1050 image size | AS | 5.3.1, Figures 9–10 |
| P5-15 | Per-class training support ranges from 14 to 883 images; four classes have fewer than 40 images | `research_paper/figures/yolo11_visuals/FIGURE_INDEX.md` | boots-powerup 24/24, boxtrain 482/625, jump-barrier 221/254, jump-electric 14/14, jump-hedge 17/18, jump-roll-barrier 359/407, jump-trash 33/34, ledge 57/87, pogstick-powerup 53/53, ramp 444/606, roll-barrier 141/147, train 883/1617, undercover-barrier 84/196, wall 279/622 (images/boxes) | AS | 5.3.1, Figure 11 |
| P5-16 | Figures 12–14 are genuine forward passes of the deployment ONNX model, not synthetic panels | `research_paper/figures/yolo11_visuals/PROVENANCE.json`; `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | model SHA-256 e6ad18f9…6aa77; confidence 0.426; NMS IoU 0.70; letterbox 640×640 pad 114; per-image predictions and confidences recorded | RM | 5.3.2, Figures 12–14 |
| P5-17 | The example-selection pool is 125 validation images (every ninth) and is not an evaluation sample | `research_paper/figures/yolo11_visuals/PROVENANCE.json` (`inference_pool`) | size 125; category counts clean 73, missed 25, extra 7, missed+extra 20; purpose "example selection only; no aggregate metric is computed or reported" | AS | 5.3.2 |
| P5-18 | GT–prediction matching is greedy one-to-one same-class at IoU ≥ 0.5 | `research_paper/figures/yolo11_visuals/PROVENANCE.json` (`matching_rule`) | rule text and per-pair matched/missed/extra counts | PD | 5.3.2, Figures 13–14 |
| P5-19 | Figure 14 includes a low-confidence match in the band 0.426–0.526 and discloses unobserved categories | `research_paper/figures/yolo11_visuals/PROVENANCE.json` | low_confidence_band [0.426, 0.526]; observed category counts 2/3/2/1 | AS | 5.3.2, Figure 14 |

## 4. Simulation performance (Chapter 6)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| S6-01 | Full FAFB graph benchmark: 138.3 steps/s for a 200 ms simulation | `experiments/phase_2_5/reports/scalability_report.json` | full-graph run steps_per_second 138.3 | RM | 6.3, 6.4 |
| S6-02 | The 800-neuron run produced identical spike output in two runs (213 spikes, 78 active) but different speed (10,499.8 vs 8,342.0 steps/s) | `experiments/phase_2_5/reports/scalability_report.json` | duplicate 800 runs | RM | 6.4, 6.5, Table 6 |
| S6-03 | 5,000-neuron subgraph produced 145 spikes from 96 active neurons | `experiments/phase_2_5/reports/scalability_report.json` | 5,000-neuron row | RM | 6.4, Table 6 |
| S6-04 | 20,000-neuron subgraph produced 51,387 spikes, 97.82% non-stimulated | `experiments/phase_2_5/reports/scalability_report.json` | row fields | RM | 6.4, Table 6 |
| S6-05 | 50,000-neuron subgraph produced 151,855 spikes at 382.2 steps/s | `experiments/phase_2_5/reports/scalability_report.json` | row fields | RM | 6.4, Table 6 |
| S6-06 | Full graph retained 134.7317 MB and peaked at 270.8 MB working set; 349,846 spikes, 33,261 active, 99.58% non-stimulated | `experiments/phase_2_5/reports/scalability_report.json` | row fields | RM | 6.4, Table 6, Figure 19 |
| S6-07 | The replay retained 341.3 MB with a 30-million-event spike buffer, and process RSS grew 163.8 MB | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | memory fields | RM | 6.4 |
| S6-08 | Maximum current in a single step was 178,691 pA; membrane stayed within [−90, −50] mV | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` (diagnostics) | current max; voltage bounds | RM | 6.5 |
| S6-09 | Transmissions per spike were 63.657; maximum out-degree 6,523; propagation buffer 48.1 MB | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json`; `simulation/` | derived ratio; degree max; buffer size | AS | 6.3 |
| S6-10 | The Phase 2.5 benchmark predates the verified-only sign policy | `experiments/phase_2_5/` configuration; `configs/banc_synapse_policy.yaml` | benchmark uses the early default sign rule | AS | 6.4 |

## 5. Motor decoding and game control (Chapter 7)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| M7-01 | Phase 4F characterised 11 scenarios at six amplitudes (120–220 pA) with and without ±25 pA jitter: 66 declared and 66 jitter runs | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | scenario and amplitude lists; run counts | RM | 7.3 |
| M7-02 | At 120 and 140 pA no driven neuron reaches the 150 pA rheobase | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | amplitude table | RM | 7.3 |
| M7-03 | The ambiguous 92 + 93 drive was decoded RIGHT because active fractions were 0.4973 vs 0.5000 | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | per-pool fractions | RM | 7.3 |
| M7-04 | Uniform 56 + 56 + 6 drive was decoded LEFT at fraction 0.3027 | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | per-pool fractions | RM | 7.3 |
| M7-05 | The weak-left and weak-jump scenarios returned NEUTRAL | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | decoded states | RM | 7.3 |
| M7-06 | Jitter changed the primary decoded state in 24 of 66 runs and left 42 identical | `reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md` | comparison table | RM | 7.3 |
| M7-07 | Phase 4G: B produced 781 total / 18 motor spikes, all unassigned, and NEUTRAL ×5 | `experiments/results/phase_4g/phase_4g_experiment.json` (`signal_overview`) | condition B fields | RM | 7.4, Table 8 |
| M7-08 | Phase 4G: C produced 1,296 total / 492 motor spikes across 82 motor neurons and JUMP ×4 | `experiments/results/phase_4g/phase_4g_experiment.json` (`signal_overview`) | condition C fields | RM | 7.4, Table 8, Figure 30 |
| M7-09 | Phase 4G: D produced 704 spikes and E 728, both with zero motor spikes and NEUTRAL ×5; A and F produced zero spikes | `experiments/results/phase_4g/phase_4g_experiment.json` | conditions A, D, E, F | RM | 7.4, Table 8 |
| M7-10 | Condition C motor spikes came from LEFT 27, RIGHT 32, JUMP 12, plus 11 unassigned | `experiments/results/phase_4g/phase_4g_experiment.json` | per-pool motor counts | RM | 7.4 |
| M7-11 | BANC has 17,745 direct descending-to-motor edges at t1 | `datasets/processed/banc_v888/banc_construction_report.json`; Phase 4B analysis | edge count query | AS | 7.4, 14.5 |
| M7-12 | Phase 4H.4 stimulated 232 neurons with 171 active and 3,562 spikes, all stimulated, over 3.3 s | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | active 171; spikes 3,562; stimulated share 1.0 | RM | 7.5, 14.2 |
| M7-13 | Phase 7 closed loop produced 2,852 spikes and zero motor spikes in 213 updates | `experiments/results/phase_7/neural_closed_loop.json` | totals; steps 213 | RM | 7.6, 11.x |
| M7-14 | Phase 7 demonstration runs: random agent 213 steps / score 5.55 / reward 3.12 at seed 42 | `experiments/results/phase_7/game_integration_demo.json` | random, seed 42 row | RM | 7.6, Table 9 |
| M7-15 | The live-loop row at seed 42 coincides with the random-agent row: 213 steps, 2 coins, 1 collision, score 5.55, reward 3.12 | `experiments/results/phase_7/neural_closed_loop.json`; `experiments/results/phase_7/game_integration_demo.json` | matching rows | RM | 11.x |

## 6. Plasticity and information theory (Chapter 8)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| L8-01 | The reward is the game score increment; RPE is the difference between consecutive rewards | `rewards/` implementation; `configs/*reward*` | reward definition; RPE computation | PD | 8.2 |
| L8-02 | The eligibility trace decays with τ_e = 20 ms and is bounded by the declared weight bounds | `configs/plasticity_banc.yaml` | tau_e 20 ms; bounds 0.5–2.0 | PD | 8.3 |
| L8-03 | The modulation signal is clipped to ±5 with τ_M = 50 ms and unit gain | `configs/plasticity_banc.yaml` | clip 5; tau_M 50; gain 1.0 | PD | 8.4 |
| L8-04 | The synthetic task is a 36-node cued-response network | `experiments/results/phase_5f/comparison_analysis.json`; `reports/PHASE_5F*` | network size 36 | PD | 8.5 |
| L8-05 | Phase 5F complete wiring: fixed success 0.795 (sd 0.083997), plastic η=1.0 success 0.945 (sd 0.022973) | `experiments/results/phase_5f/comparison_analysis.json` (`core.conditions`) | mean and sd per condition | RM | 8.6, Table 10, Figure 21 |
| L8-06 | Selective-response rates were 0.12 fixed vs 0.20 plastic on complete wiring | `experiments/results/phase_5f/comparison_analysis.json` | selective fields | RM | 8.6 |
| L8-07 | Random wiring: fixed 0.1025 (sd 0.043221), plastic 0.1125 (sd 0.051707); selective 0.2175 vs 0.22 | `experiments/results/phase_5f/comparison_analysis.json` | condition fields | RM | 8.6 |
| L8-08 | A conventional perceptron reaches success 1.00 on the same task | `experiments/results/phase_5f/comparison_analysis.json` | perceptron condition | RM | 8.6 |
| L8-09 | The MI bias floor is (k_x−1)(k_y−1)/(2N ln 2); for the Phase 5F 4×4 tables at 40 episodes it is 0.1623 bits | `information/bias_correction.py`; `experiments/results/phase_6/information_analysis.json` | formula; floor 0.1623 | AS | 8.8, 10.2 |
| L8-10 | Confirmatory inference uses 5,000 block permutations, 2,000 bootstrap resamples, and an exact sign-flip over 2^10 assignments | `configs/phase_6_information.yaml`; `experiments/results/phase_6/information_analysis.json` | permutation counts; family definition | PD | 8.8, 10.2 |
| L8-11 | Normalised MI is MI / min(H_x, H_y), withheld when the denominator is at or below 0.05 bits | `information/mutual_information.py` (`mutual_information_report`) | `_normalised`; `min_entropy_bits` 0.05 | PD | 8.8, 10.2 |

## 7. Chronology and test suite (Chapter 9)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| C9-01 | The phase-by-phase status table is reproduced from the project's validation summary | `reports/` phase reports; `research_paper/tables/T07_phase_validation_summary.csv` | 24-row status table | AS | 9.2, Table 11 |
| C9-02 | The cumulative suite was 1,503 passed, 3 skipped, 6 failed at the Phase 8 pilot gate | `reports/PHASE_8_PILOT1_EXECUTION.json` | test totals | RM | 9.x, 13.6 |
| C9-03 | The six failures pre-date the pilot: three protected-hash README drift checks, two smoke-label checks, one C0 cache assertion | `reports/PHASE_8_PILOT1_EXECUTION.json` | failing test names | RM | 13.6 |
| C9-04 | The D2 authorisation tests were 18 passed and the affected Phase 8 modules 284 passed | `reports/PHASE_8_PILOT1_EXECUTION.json` | test counts | RM | 13.6 |
| C9-05 | The retrospective status table records 24 phases and gates, with their recorded statuses | `research_paper/tables/T07_phase_validation_summary.csv`; Appendix Table D1 | 24 rows | AS | 9.2, Table 11, Table D1 |

## 8. Phase 6 information analysis (Chapter 10)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| I10-01 | Complete-wiring confirmatory contrast: mean paired difference −0.0863 bits, 95% CI [−0.1751, 0.0052], exact p 0.125, Holm p 0.250, not rejected | `experiments/results/phase_6/information_analysis.json` (`B_plasticity.contrasts`) | fields for complete wiring | RM | 10.3, Table 13, Figure 22 |
| I10-02 | Random-wiring contrast: −0.0025 bits, exact p 1.000, Holm p 1.000 | `experiments/results/phase_6/information_analysis.json` | fields for random wiring | RM | 10.3, Table 13 |
| I10-03 | At checkpoint 0 both contrasts are exactly zero | `experiments/results/phase_6/information_analysis.json` | checkpoint-0 contrast rows | RM | 10.3 |
| I10-04 | Fixed complete and fixed random means are 0.6126 and 1.3547 bits; plastic complete and plastic random end at 0.5262 and 1.3522 bits | `experiments/results/phase_6/information_analysis.json` (`B_plasticity.conditions`) | per-condition means | RM | 10.3 |
| I10-05 | Complete-wiring paired differences: four positive and six negative | `experiments/results/phase_6/information_analysis.json` | per-seed differences | RM | 10.3, Figure 20 |
| I10-06 | Random-wiring differences: nine exact zeros and one small negative | `experiments/results/phase_6/information_analysis.json` | per-seed differences | RM | 10.3, Figure 22 |
| I10-07 | The sensory distance code gives 1.5849625 bits (= log₂ 3), bias floor 0.3206, corrected 1.2644, normalised 1.0, exact p 0.0278 over 216 assignments | `experiments/results/phase_6/information_analysis.json` | distance-code block | RM | 10.4 |
| I10-08 | The population sweep keeps joint MI at 1.585 bits for sizes 4–24 while summed single-neuron MI rises from 2.755 to 18.366 bits | `experiments/results/phase_6/information_analysis.json` (`A_population_sweep`) | per-size rows | RM | 10.4, Figure 23 |
| I10-09 | Neural-to-motor MI is 1.1841 bits (floor 0.0459, corrected 1.1382, normalised 0.8128), p 0.0005 over 66 clusters | `experiments/results/phase_6/information_analysis.json` (`D_neural_motor`) | fields | RM | 10.5, Figure 24 |
| I10-10 | The conditional analysis pools 2,880 episodes in 18 clusters: marginal 0.3841 bits, conditional 0.6040 (floor 0.0135, corrected 0.5905) | `experiments/results/phase_6/information_analysis.json` | conditional block | RM | 10.6 |
| I10-11 | Reward-ablation contrasts B−A = −0.0605 and B−D = −0.0486 bits, each with exact p 0.5 over three pairs | `experiments/results/phase_6/information_analysis.json` | ablation block | RM | 10.6 |
| I10-12 | Seven endpoints U01–U07 are declared unavailable with recorded reasons | `configs/phase_6_information.yaml`; `experiments/results/phase_6/information_analysis.json` | unavailable list | NA | 10.7, Table E3 |

## 9. Phase 7 closed loop (Chapter 11)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| G11-01 | The live closed loop ran 213 updates with neural state advanced between updates | `experiments/results/phase_7/neural_closed_loop.json` | steps 213; per-update records | RM | 11.x, Figure 25 |
| G11-02 | All 213 decisions were NO_ACTION and no motor pool spiked | `experiments/results/phase_7/neural_closed_loop.json` | action sequence; motor spike totals | RM | 11.x |
| G11-03 | The closed loop used the BANC t5 graph with fixed weights and no plasticity | `experiments/results/phase_7/neural_closed_loop.json`; `configs/phase_7*` | condition metadata | RM | 11.x |
| G11-04 | Phase 7 ran fixed-seed demonstrations for random, rule-based, Phase 4 replay, and live-loop agents | `experiments/results/phase_7/game_integration_demo.json` | agent list | RM | 11.x, Table 9 |
| G11-05 | No BANC simulation ran during the open-loop demonstration games | `experiments/results/phase_7/game_integration_demo.json` | run metadata | AS | 11.x, Figure 26 |

## 10. Phase 8 design (Chapter 12)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| E12-01 | Six conditions A–F plus controls A′, C′, Fβ, F-init, and floor | `configs/phase_8/conditions.yaml`; `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | condition definitions | PD | 12.2, Table 14 |
| E12-02 | The four confirmatory contrasts are C1 = F−A (H3), C2 = B−A (H1), C3 = A−C (H2), C4 = F−Fβ | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`; `research_paper/tables/T16_hypothesis_status.csv` | contrast table | PD | 12.4, Table 15 |
| E12-03 | Holm correction is applied over a family of four at α = 0.05 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | correction rule | PD | 12.4 |
| E12-04 | The primary outcome is min(updates, 900), averaged over K episodes within a seed | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | outcome definition | PD | 12.5 |
| E12-05 | The smallest effect of interest is 100 updates | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | SEI 100 | PD | 12.5 |
| E12-06 | N = 16 is primary, with N = 10 permitted only if σ_max ≤ 112.87; K = 10 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`; `configs/phase_8/campaign.yaml` | sample-size rule and K | PD | 12.6 |
| E12-07 | The master seed is 20261116 | `configs/phase_8/campaign.yaml` | master_seed | PD | 12.6 |
| E12-08 | The exact two-sided sign-flip test has minimum p = 2/65,536 at N = 16 and 2/1,024 at N = 10 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` section 7.3 | minimum attainable p | AS | 12.7, Figure 39 |
| E12-09 | MDE = 2.8016·σ/√N, approximately 42 updates at N = 16 with σ = 60 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | MDE formula and value | AS | 12.6 |
| E12-10 | The protocol is frozen at SHA-256 `e4aa9e0f…1547c` | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | file hash | AS | 12.9, Table K3 |
| E12-11 | The N = 16 campaign was never run; no contrast C1–C4 was estimated | `docs/PHASE_8_*`; `reports/PHASE_8_*`; absence of campaign results | status statements; no campaign rows exist | AS | 12.1, 17.x |
| E12-12 | Sixteen degree- and sign-preserving null graphs were certified | `experiments/results/phase_8_random/`; certification records | seeds 1–16 | RM | 12.3 |

## 11. Pilot 1 (Chapter 13)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| P1-01 | Pilot 1 ran condition A, seeds 9001–9003, three episodes each, nine episodes total | `experiments/results/phase_8/pilot1/pilot1/pilot_summary.json`; `episodes.jsonl` | nine rows; executed = true | RM | 13.1, 13.2 |
| P1-02 | The nine episodes sum to 3,784 game updates, 126,135 neural steps, 73,880 spikes, 0 motor spikes, 47.75 reward | `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`; `research_paper/tables/T10_pilot1_episodes.csv` | column sums | RM | 13.3, Table 16, Figure 27 |
| P1-03 | Per-seed totals are 9001: 19.63, 9002: 18.63, 9003: 9.49 reward | `episodes.jsonl` | sum by seed | RM | 13.3 |
| P1-04 | Every episode terminated by collision and none reached the 900-update cap | `episodes.jsonl` | termination = collision ×9; truncated = false | RM | 13.3 |
| P1-05 | All 3,784 decisions were NO_ACTION; LEFT, RIGHT, and JUMP recorded zero spikes | `episodes.jsonl` | actions; motor spikes | RM | 13.5 |
| P1-06 | The weight fingerprint `4923f0cd…945d5` is identical before and after every episode | `episodes.jsonl` | structural and initial digests equal | RM | 13.5 |
| P1-07 | The execution report prose states 72,880 spikes while the row sum is 73,880, a difference of 1,000 (1.3535%) | `reports/PHASE_8_PILOT1_EXECUTION.json` | prose total vs row sum | AS | 13.4, 3.4 of Appendix G |
| P1-08 | Wall time was 357.0 s (10:58:51Z–11:04:48Z, 2026-11-20) | `reports/PHASE_8_PILOT1_EXECUTION.json` | start/end timestamps | RM | 13.2 |
| P1-09 | The memory gate reported 5.745 GiB available against 4.0 GiB; 177 samples; max RSS 0.3725 GiB; minimum available 4.1997 GiB | `reports/PHASE_8_PILOT1_EXECUTION.json` | resource block | RM | 13.2 |
| P1-10 | The integrity check found 35 of 37 protected files matching, with README and `motor/__init__.py` drifting; pass = false | `reports/PHASE_8_PILOT1_EXECUTION.json`; `reports/PHASE_8_PILOT1_*` | integrity block; commit `3c74ae8` | RM | 13.6 |
| P1-11 | The episode file hash is `ee479e5b…68f9` and the driver record `d3392b9c…e1e` | `episodes.jsonl`; `reports/PHASE_8_PILOT1_EXECUTION.json` | file hashes | AS | 13.2 |

## 12. Motor bottleneck (Chapter 14)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| B14-01 | The 232 stimulated neurons have 662 signed outgoing edges to 608 distinct targets, 607 non-stimulated | `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md`; frozen graph query | structural counts | AS | 14.3, Table H1 |
| B14-02 | None of the first-hop targets is a motor neuron | `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` | target-class query | AS | 14.3 |
| B14-03 | 473 of 607 non-stimulated targets received current in Phase 4H.4 | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | current-receiving count | RM | 14.3, Table H2 |
| B14-04 | First-hop current: median 0 pA, p95 80.87 pA, maximum 164.443 pA | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | current distribution | RM | 14.3, Table H2 |
| B14-05 | The largest static signed first-hop sum is 167.041 pA to node 125949 | frozen graph query in the bottleneck report | per-target sum | AS | 14.3 |
| B14-06 | The peak first-hop membrane potential was −56.926 mV, 8.074 mV above rest and 6.926 mV below threshold | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | peak membrane | RM | 14.3, Figure 29 |
| B14-07 | Zero of the 473 current-receiving targets spiked | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | first-hop spike count 0 | RM | 14.3, Figure 28 |
| B14-08 | No second-hop current was delivered; 0 of 3,576 non-stimulated second-hop targets received current | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | second-hop fields | RM | 14.5 |
| B14-09 | Four second-hop targets are motor neurons (two JUMP, none LEFT/RIGHT) | frozen graph query | two-hop motor targets | AS | 14.5 |
| B14-10 | Descending neurons received a maximum of 67.208 pA and reached −62.158 mV (12.158 mV short) | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json` | descending block | RM | 14.4 |
| B14-11 | The first hop carries 0.0 pA of inhibitory weight, so it is under-driven rather than suppressed | frozen graph query; bottleneck report | signed weight split | AS | 14.5 |
| B14-12 | All six Phase 4H.4 controls produced zero non-stimulated spikes; the closest neuron under background was 7.35 mV short | `reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json`; `reports/PHASE_4H5_*` | per-control results | RM | 14.6, Table H3 |
| B14-13 | The charge arithmetic gives about 0.82 pC and 4.1 mV for a single 164 pA, 5 ms event, consistent with the recorded 8.07 mV peak under overlap | `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md` | order-of-magnitude check, labelled as such | INT | 14.4 |
| B14-14 | The verified-only policy excludes 852,610 of 1,535,710 edges (55.52%) | `configs/banc_synapse_policy.yaml`; signed-edge count | arithmetic from signed count | AS | 14.6 |

## 13. D5/D6 training and artifacts (Chapter 15)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| T15-01 | Six artifacts were trained: F and Fβ at evaluation seeds 9001, 9002, 9003 | `experiments/results/phase_8/training/{F,F_beta}/seed_*/training_run.json` | six files | RM | 15.2, Table 17 |
| T15-02 | Training seeds are 1008, 1014, 1005; pool indices 7, 13, 4 | `training_run.json` | train_seed; pool_index | RM | 15.2, Table 17 |
| T15-03 | Each artifact has 20 episodes and checkpoints; 120 episodes total | `training_run.json` | episode count | RM | 15.2 |
| T15-04 | All training episodes ended by collision with zero motor spikes and no weight change | `training_run.json` | per-episode fields | RM | 15.4 |
| T15-05 | F and Fβ produced identical rewards, actions, and decision counts for each seed | six `training_run.json` records | paired comparison | RM | 15.5 |
| T15-06 | F's feature weights retained the random initialisation; Fβ is bias-only | `parameters.npz`; `training_run.json` | parameter digests; init seeds F 1350278753/3449218186/3297997184 | RM | 15.5 |
| T15-07 | The F/9001 run was interrupted by a logging `KeyError` at episode 1 and resumed | `training_run.json`; recovery records | interruption record | RM | 15.6 |
| T15-08 | The recovery reference matched the resumed run on 20 episodes × 12 fields with zero differences | `experiments/results/phase_8/training_recovery_reference/F/seed_9001/equivalence.json` | 240 field comparisons | IT | 15.6 |
| T15-09 | Final parameters file hash `35918eb7…42efb6`; digest `bd50cc73…9a8883`; original provenance preserved as `training_run.incomplete_provenance.json` | `training_run.json` | digest fields | AS | 15.6, Table I4 |
| T15-10 | Training used Python 3.13.14, NumPy 2.3.4, PyTorch 2.10.0; the preflight recorded 7.118/15.342 GB | `training_run.json`; `reports/PHASE_8_D5_D6_IMPLEMENTATION_AND_TRAINING_REPORT.md` | environment block | RM | 15.7, Table K1 |

## 14. Pilot 2-C (Chapter 16)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| P2C-01 | 54 of 54 planned rows executed: six arms × three seeds × three episodes | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl` | 54 rows | RM | 16.2, Table 18 |
| P2C-02 | Every arm produced the same survival sequence per seed: 323/620/323, 620/426/620, 213/426/213 | `episodes.jsonl` | survival fields | RM | 16.3, Table 19, Figure 34 |
| P2C-03 | Mean survival was 420.44 updates; per-seed means 422.00, 555.33, 284.00 | `episodes.jsonl` | arithmetic | RM | 16.3 |
| P2C-04 | Per-seed reward totals were 19.63, 18.63, 9.49 | `episodes.jsonl` | sum by seed | RM | 16.3 |
| P2C-05 | A′ reproduced A exactly on P1–P19 with η = 0 | `reports/PHASE_8_PILOT2C_CERTIFICATION.json` (P2C-2); `episodes.jsonl` | identity fields | RM | 16.4, Figure 35 |
| P2C-06 | B had 683,100 eligible edges and changed one edge in four of nine episodes, with 42/45/24/12 applied updates | `reports/PHASE_8_PILOT2C_CERTIFICATION.json`; `episodes.jsonl` | attribution block | RM | 16.5 |
| P2C-07 | Maximum |Δw| in B was 0.03265 pA and maximum applied change 0.01022 pA | `episodes.jsonl` | delta fields | RM | 16.5 |
| P2C-08 | F showed 12 non-zero feature weights; Fβ was bias-only; F and Fβ outcomes were identical | `episodes.jsonl`; certification record | weight counts; outcome comparison | RM | 16.6 |
| P2C-09 | All eight certification claims P2C-1–P2C-8 pass | `reports/PHASE_8_PILOT2C_CERTIFICATION.json` | claim statuses | IT | 16.7, Table 20, Figure 36 |
| P2C-10 | C1–C4 and H1–H3 remain unevaluable after Pilot 2-C | `reports/PHASE_8_PILOT2C_CERTIFICATION.json`; absence of campaign | statement and missing campaign rows | AS | 16.8 |
| P2C-11 | Pilot 2-C ran 2026-11-23 from 03:37:44Z to 04:35:36Z, 3,458.8 s, memory gate 6.115 GB | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/pilot_summary.json`; `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/manifest.json` | timestamps; memory | RM | 16.2, Table K4 |
| P2C-12 | The longest cell was F_beta:9001:0 at 1,653.9 s (47.8%) | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/pilot_summary.json` | per-cell timings | RM | 16.2 |
| P2C-13 | Episodes hash `a14fd3bb…778991`; manifest `43710d38…020534`; plan `63d51f61…ddcab`; summary `44dc5c05…520c5`; certification `bc5effaa…aa357` | files in the pilot2c directory | file hashes | AS | 16.9, Table K2 |

## 15. Consolidated status and interpretation (Chapters 17–21)

| Claim ID | Research claim | Source file | Exact evidence | Type | Paper section |
|---|---|---|---|---|---|
| K17-01 | No result in the programme is evidence of learning in the fly | all Phase 5–8 records | no behavioural gain on the biological substrate; motor silence throughout | INT | 17.x, 18.x |
| K17-02 | C1–C4 are "not estimated" and H1–H3 "unevaluable", distinct statuses | `research_paper/tables/T16_hypothesis_status.csv` | status column | AS | 17.x, Table 21 |
| K17-03 | Pilot 1 and Pilot 2-C are pilots, not confirmatory campaigns | `experiments/results/phase_8/pilot1/pilot1/pilot_summary.json`; `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/pilot_summary.json` | evidence_kind = pilot | AS | 13.2, 16.2, 17.x |
| X18-01 | The Phase 6 success–information dissociation is the basis for treating behavioural success and information as separate outcomes | Chapter 10 results; `experiments/results/phase_5f/comparison_analysis.json` | 0.795→0.945 success vs −0.0863 bits MI | INT | 18.x |
| X19-01 | Nine deviations are recorded and resolved in the register | `research_paper/tables/T15_deviations_register.csv`; `reports/` deviation records | nine rows | AS | 19.x, Table 22 |
| X19-02 | Fifteen limitations bound the conclusions | `research_paper/tables/T17_limitations.csv` | fifteen rows | AS | 19.x, Table 23 |
| X20-01 | The central question receives a qualified negative answer at the current operating point | all recorded executions | motor silence in every biological-substrate run | INT | 20.x |
| X21-01 | Eight open questions structure future work | `research_paper/tables/T18_future_questions.csv` | eight rows | INT | 21.x, Table 24 |
| X21-02 | No follow-up experiment is proposed as a fix to the executed protocol | manuscript text | options are labelled hypothesis, not recommendation | INT | 21.x |

## 16. Endpoints declared unavailable

| Claim ID | Endpoint | Source file inspected | Reason recorded | Type | Paper section |
|---|---|---|---|---|---|
| U-01 | Real-replay sensory-to-neural MI | `experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json` | aggregate spike counts only; no per-neuron, per-frame arrays | NA | 10.7 |
| U-02 | Spike-train entropy | archived runs | no raw spike times at a scale supporting a per-neuron estimate (74-spike replay, 64–72-spike pilot) | NA | 10.7 |
| U-03 | Membrane-potential entropy | all phases | membrane potentials were never persisted | NA | 10.7 |
| U-04 | Neural-level plasticity information | Phase 5 BANC demonstration | three distinct spike hashes across six conditions; deterministic repeat | NA | 10.7 |
| U-05 | Neural-level reward-modulation information | Phase 5 BANC demonstration | five sequential windows; identical decoded-state sequence across conditions | NA | 10.7 |
| U-06 | Cue-to-neural-response MI | Phase 5E/5F episodes | per-episode cue spike count constant at 8 (total 12; 11 or 12 in E) | NA | 10.7 |
| U-07 | Neural-to-reward MI | Phase 5E/5F episodes | no neural predictor exists without inventing an observation | NA | 10.7 |

---

## 17. Register completeness

- **Rows:** 189 (D3 23, A4 13, P5 19, S6 10, M7 15, L8 11, C9 5, I10 12, G11 5, E12 12, P1 11, B14 14, T15 10, P2C 13, K17/X 9, U 7). Counts are of table rows, including rows that combine closely related values.
- **Distinct source files cited:** 50 repository artifact paths, counted from the backticked paths in the manuscript and in this register that resolve under `datasets/`, `experiments/`, `reports/`, `configs/`, `docs/`, `models/`, `src/`, or `tests/` (16 under `experiments/`, 16 under `reports/`, 10 under `configs/`, 5 under `datasets/`, and one each under `docs/`, `models/`, and `src/`). The `research_paper/tables/` CSVs are derived summaries of those artifacts, not independent sources.
- **Claims not registered as measurements:** statements about what the model is *not* (for example, that structural edges are not physiological connections) are classified `INT` and are supported by the absence of any measurement claiming otherwise, not by a data record.
- **Restatements:** values repeated in the abstract, Chapter 17, and the appendix tables point back to the rows above; the appendix tables are computed summaries of the same artifacts and are not independent evidence.
- **Unchanged sources:** every file listed here was read only. The historical Pilot 1 report retains its 72,880 prose total; the register records both values (P1-07).
