# Chapter 3. Biological Data and Connectome Construction

## 3.1 Data sources and governance

FLY-SURFER uses two published connectomes and one externally trained detector. The FlyWire FAFB v783 reconstruction of an adult female brain supplies the brain-only graph used for the simulation, perception, plasticity, and information analyses. The BANC v888 reconstruction of an adult female brain and ventral nerve cord supplies the graph used for motor decoding and all Phase 8 executions, because the FAFB volume does not contain the limb motor neurons that innervate the legs. The two graphs are kept separate. No FAFB root identifier is transferred to BANC, no BANC neuron is selected by FAFB connectivity, and no attempt is made to merge them into a single network. This separation is a design decision, not an implementation shortcut: the datasets come from different specimens, different reconstruction pipelines, and different annotation versions, and merging them would create unverifiable identities.

All datasets and processed artifacts are treated as read-only. The project did not download new data during this paper's preparation, did not regenerate graphs, and did not modify any stored artifact. The processed connectome file has SHA-256 `3f568f24…5f33d8` and is 28,013,212 bytes. The BANC artifacts are bound to five source hashes recorded in the Phase 4D report.

Table 1 summarises the datasets and artifacts used in the paper.

**Table 1.** Dataset inventory. Scale figures are the values recorded in the source artifacts. Data source: `datasets/processed/connectome_report.json`, `datasets/processed/banc_v888/banc_construction_report.json`, `reports/PHASE_3B02_V15_DATASET_AUDIT.json`, `models/YOLO11/deployment/yolo11n_v1_deployment/`; full machine-readable table in `tables/T01_dataset_inventory.csv`.

| Dataset | Version | Scale | Role | Provenance |
|---|---|---|---|---|
| FAFB (FlyWire) | v783 | 139,255 neurons; 3,732,460 directed pairs; 50,666,648 synapses | structural brain connectome | `datasets/processed/connectome.npz` |
| FAFB annotations | v783 | 119,597 annotated; 19,658 without transmitter | cell class, transmitter, side, position | `datasets/processed/nodes.csv.gz` |
| BANC | v888 | 172,433 endpoints; 1,535,710 edges at t5 | brain + VNC connectome; motor interface | `datasets/processed/banc_v888/` |
| BANC nulls | seeds 1–16 | 16 certified graphs, same edge count | degree/sign-preserving nulls | `datasets/processed/banc_v888_random/` |
| Detector dataset | v15 | 2,328 images; 8,666 boxes; 14 classes | detector supervision | `reports/PHASE_3B02_V15_DATASET_AUDIT.json` |
| YOLO11n weights | v1 deployment | 10,636,871 bytes; 1×3×640×640 input | visual perception | `models/YOLO11/deployment/…/best.onnx` |
| endless-surfer | standalone | 200/900-step episodes; 25-unit horizon | controlled game environment | `external/endless-surfer-main` (third-party clone, not distributed) |

## 3.2 The FAFB graph artifact

The FAFB artifact (`datasets/processed/connectome.npz`) stores the graph as flat arrays: `root_ids`, `out_indptr`, `edge_src`, `edge_dst`, `edge_weight`, `in_indptr`, `in_edge_idx`, `positions`, `position_mask`, `nt_code`, `super_class_code`, `class_code`, `side_code`, `flow_code`, a vocabulary object, and a metadata object. The graph retains directed pairs with at least five summed synapses. Applying that threshold yields 139,255 indexed neurons, 3,732,460 directed pairs, and 50,666,648 summed synapses. Figure 2 summarises the construction and Figure 3 shows the resulting weight and degree distributions.

![Figure 2. FlyWire FAFB v783 connectome construction summary. Bars show indexed neurons, annotated neurons, neurons without a predicted transmitter, retained directed pairs at the five-synapse threshold, summed synapses in retained pairs, and isolated neurons. Data source: datasets/processed/connectome_report.json.](figures/F02_flywire_construction.png)

![Figure 3. FlyWire FAFB v783 edge-weight and degree distributions computed from the stored edge arrays. (a) Summed synapses per retained directed pair on a log scale; the minimum is the threshold of 5. (b) Complementary cumulative distribution of out-degree. (c) Complementary cumulative distribution of in-degree. Data source: datasets/processed/connectome.npz.](figures/F03_fafb_distributions.png)

The weight distribution is heavy-tailed: the mean summed synapse count is 13.575, the minimum is 5 by construction, and the maximum is 2,633. Out-degree is also heavy-tailed, with a mean of 26.803 and a maximum of 6,523; in-degree reaches 6,261. There are 620,180 directed reciprocal pairs, corresponding to 310,090 unordered reciprocal connections. These statistics matter for simulation: the sparse matrix has 50.7 million non-zeros, but the degree distribution means that a small number of hub neurons can generate very large propagation bursts. The simulator's worst-case temporary allocation is sized for this, and the full-graph benchmark is discussed in Chapter 6.

**Table 2.** Graph statistics for the FAFB v783 graph and the three BANC v888 thresholds. Synapse counts are sums over retained directed pairs. Data source: `datasets/processed/connectome_report.json` and `datasets/processed/banc_v888/banc_construction_report.json`; full machine-readable table in `tables/T02_connectome_statistics.csv`.

| Graph | Threshold | Nodes | Directed edges | Summed synapses | Isolated | Mean weight | Max weight |
|---|---:|---:|---:|---:|---:|---:|---:|
| FAFB v783 | 5 | 139,255 | 3,732,460 | 50,666,648 | 671 | 13.575 | 2,633 |
| BANC v888 | 1 | 172,433 | 11,596,517 | 34,310,230 | 6,232 | 2.9587 | 913 |
| BANC v888 | 5 | 172,433 | 1,535,710 | 18,552,546 | 24,320 | 12.0808 | 913 |
| BANC v888 | 10 | 172,433 | 570,721 | 12,397,230 | 62,551 | 21.722 | 913 |

## 3.3 FAFB annotations and population inventory

Annotations are predictions [3]. The node table provides a super-class label for most neurons, a predicted transmitter for most, a side label, positions, and a mask indicating whether a position is valid. Of 139,255 neurons, 119,597 carry at least one annotation and 19,658 have no predicted transmitter. The transmitter composition at the five-synapse graph is 82,298 cholinergic, 19,605 glutamatergic, 16,017 GABAergic, 1,021 serotonergic, 584 dopaminergic, and 72 octopaminergic neurons. The super-class composition is dominated by optic-lobe neurons (77,873), followed by central neurons (32,381), sensory neurons (16,938), visual-projection neurons (7,684), ascending neurons (1,750), descending neurons (1,305), sensory-ascending neurons (612), visual-centrifugal neurons (522), motor-superclass neurons (110), and endocrine neurons (80). Side labels are available for 69,959 left, 69,093 right, and 173 centre neurons.

The FAFB motor super-class contains 110 neurons, none of which are the leg motor neurons required for a walking or jumping readout. This is the decisive compatibility finding of Phase 4A: the FAFB volume is brain-only, and the ventral nerve cord — where limb motor neurons reside — is absent. Table 3 lists the population inventory for both datasets and for the decoder-defined motor pools. The table is descriptive; a super-class label is not a functional identification, and a motor label does not establish that a neuron drives a particular leg movement.

**Table 3.** Neural population inventory for FAFB v783, BANC v888, and the decoder-defined motor pools. Counts are annotation-derived, not measured physiological populations. Data source: `datasets/processed/connectome_report.json`, `datasets/processed/banc_v888/banc_nodes.csv.gz`, and `configs/motor_decoder.yaml`; full machine-readable table in `tables/T04_population_inventory.csv`.

| Dataset | Population | Count | Basis |
|---|---|---:|---|
| FAFB v783 | optic | 77,873 | super_class |
| FAFB v783 | central | 32,381 | super_class |
| FAFB v783 | sensory | 16,938 | super_class |
| FAFB v783 | visual_projection | 7,684 | super_class |
| FAFB v783 | ascending | 1,750 | super_class |
| FAFB v783 | descending | 1,305 | super_class |
| FAFB v783 | sensory_ascending | 612 | super_class |
| FAFB v783 | visual_centrifugal | 522 | super_class |
| FAFB v783 | motor | 110 | super_class |
| FAFB v783 | endocrine | 80 | super_class |
| BANC v888 | optic_lobe_intrinsic | 72,826 | super_class |
| BANC v888 | central_brain_intrinsic | 31,347 | super_class |
| BANC v888 | unannotated | 20,573 | super_class |
| BANC v888 | sensory | 15,956 | super_class |
| BANC v888 | ventral_nerve_cord_intrinsic | 12,850 | super_class |
| BANC v888 | visual_projection | 7,284 | super_class |
| BANC v888 | glia | 6,281 | super_class |
| BANC v888 | ascending | 1,849 | super_class |
| BANC v888 | descending | 1,316 | super_class |
| BANC v888 | motor | 805 | super_class |
| BANC v888 | sensory_ascending | 514 | super_class |
| BANC v888 | visual_centrifugal | 470 | super_class |
| BANC v888 | visceral_circulatory | 221 | super_class |
| BANC v888 | trachea | 83 | super_class |
| BANC v888 | not_a_neuron | 40 | super_class |
| BANC v888 | sensory_descending | 13 | super_class |
| BANC v888 | ascending_visceral_circulatory | 5 | super_class |
| BANC v888 | LEFT pool | 185 | decoder annotation |
| BANC v888 | RIGHT pool | 186 | decoder annotation |
| BANC v888 | JUMP pool | 20 | decoder annotation |
| BANC v888 | motor unassigned | 414 | decoder annotation |
| BANC v888 | tergotrochanter candidates | 20 | annotation |
| BANC v888 | VNC intrinsic (graph) | 12,850 | is_vnc_intrinsic |
| BANC v888 | stimulated sensory neurons | 232 | experimental mapping |

## 3.4 The BANC graph and threshold sensitivity

The BANC source table contains 188,508 metadata rows, of which 16,075 are metadata-only rows that do not correspond to an endpoint node. Excluding them leaves 172,433 endpoint nodes. The original edge list contains 11,752,828 edges and 156,311 self-edges, which are excluded along with 1,422,866 self-loop synapses, leaving 11,596,517 non-self edges. Thresholding at one, five, and ten summed synapses produces the graphs in Figure 4. At threshold 1 the graph has 11,596,517 edges and 34,310,230 synapses with 6,232 isolated nodes; at threshold 5 it has 1,535,710 edges and 18,552,546 synapses with 24,320 isolated nodes; at threshold 10 it has 570,721 edges and 12,397,230 synapses with 62,551 isolated nodes. The five-synapse graph therefore retains 13.24% of pairs but 54.07% of synapses, a direct consequence of the heavy-tailed weight distribution; the mean weight rises from 2.959 at t1 to 12.081 at t5 and 21.722 at t10.

![Figure 4. BANC v888 graph construction and threshold sensitivity. (a) Directed edges and summed synapses retained at thresholds 1, 5, and 10. (b) Construction stages: metadata rows, endpoint nodes, original edges, and retained t5 edges. Data source: datasets/processed/banc_v888/banc_construction_report.json.](figures/F04_banc_construction.png)

The five-synapse threshold is used throughout because it matches the FAFB threshold and removes pairs supported by a single or very few synapses, which are the most likely to reflect segmentation or annotation error. This is a modelling convention, not a claim that five synapses is a biological criterion for a functional connection.

## 3.5 BANC annotations and coverage

BANC annotation coverage is uneven (Figure 5). A super-class label is present for 88.07% of endpoint nodes, a cell-type label for 68.20%, a side label for 91.74%, and a body-part-effector label for only 0.60%. A predicted neurotransmitter is present for 89.27% of nodes, and 37.87% carry a verified label. The composition is dominated by optic-lobe intrinsic neurons (72,826), central-brain intrinsic neurons (31,347), unannotated nodes (20,573), sensory neurons (15,956), VNC intrinsic neurons (12,850), visual-projection neurons (7,284), and glia (6,281), with 1,849 ascending, 1,316 descending, and 805 motor neurons. The low effector coverage is the key limitation for the decoder: the LEFT, RIGHT, and JUMP pools are built from whatever side and effector annotations exist, and 414 of the 805 motor neurons cannot be assigned to any of the three pools.

![Figure 5. BANC v888 annotation coverage and neuronal composition. (a) Coverage of super-class, cell-type, side, and body-part-effector annotations. (b) Super-class composition for the twelve largest populations. Data source: datasets/processed/banc_v888/banc_nodes.csv.gz.](figures/F05_banc_annotation.png)

Transmitter predictions are also incomplete. Under the verified-only sign policy, an edge is excitatory if its presynaptic transmitter is acetylcholine or glutamate, inhibitory if GABA or glycine, and excluded if the transmitter is a modulator or missing. At the five-synapse threshold only 44.48% of edges carry a usable sign (683,100 edges, 8,426,168 synapses). The rest are structurally present but electrically undefined in the model. Chapter 7 explains how the decoder and the simulation handle this.

## 3.6 Why the motor stage uses BANC

The FAFB and BANC datasets overlap in the brain but differ in coverage. Phase 4A compared them and found 139,241 shared root identifiers, 14 FAFB-only identifiers, and 7 annotation-only identifiers. The high overlap is expected because both reconstruct the same brain region, but the overlap does not make the graphs interchangeable: the annotation versions differ, the IDs are dataset-specific, and the BANC adds the VNC. The decisive difference is the presence of 805 motor neurons and 1,316 descending neurons in BANC versus 110 motor-superclass neurons and 1,305 descending neurons in FAFB. The FAFB descending count is similar, but the FAFB motor neurons do not include leg effectors. Using FAFB for the motor readout would therefore have required assuming that a brain motor neuron stands in for a leg motor neuron, which the project declined to do. BANC is used for every motor-relevant result; FAFB is used only where the question concerns the brain graph itself.

## 3.7 Dataset inventory and detector provenance

Table 1 (Section 3.1) lists the datasets, their versions, scales, roles, and provenance. The detector dataset is not duplicated in the repository; it is referenced by its audit reports. The YOLO11n weights are 10,636,871 bytes with SHA-256 `e6ad18f9…6aa77`, and the published validation metrics — precision 0.937310, recall 0.810829, mAP50 0.897776, and mAP50-95 0.687726 on 1,128 validation images — are recorded as provenance. They were not re-measured in this paper, and the repository does not contain an independent test split.

## 3.8 Summary

The programme has a large, well-annotated brain graph and a large brain–VNC graph with a usable motor interface, but the interfaces are not free. The FAFB graph lacks limb motor neurons; the BANC graph has sparse effector annotations and only 44.48% signed edges; both are structural. These constraints propagate into every later result and are therefore stated before any simulation result is reported.
