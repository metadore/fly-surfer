# Phase 4E — Motor Population and Pathway Analysis

**Analysis date:** 2026-11-08
**Scope:** Read-only structural analysis of the BANC v888 descending, premotor-candidate and motor-neuron pathways. Phase 4D graphs were loaded, never rebuilt.
**Verdict:** **PASS WITH LIMITATIONS**

The analysis is complete and reproducible. Every Phase 4C.5 pathway figure reproduces exactly at threshold 1, the 16-neuron VNC-intrinsic discrepancy is resolved, and all required pathway, side, jump-candidate and threshold blocks are computed. The limitations are scientific, not computational: the graph is a structural export, weights are synapse counts rather than conductances, intermediates are candidates rather than validated premotor neurons, and no game action can be assigned to any neuron or pathway.

---

## 1. Inputs, method and rules

### 1.1 Inputs

All inputs were opened read-only. The Phase 4D manifest was verified before analysis.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `banc_888_meta.feather` | 57,503,026 | `86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098` |
| `banc_888_edgelist_simple_v2.feather` | 305,250,378 | `363fdef3813b72a5e45a42f17034cd5a544b654c838929cecf6e1ce5f60625cb` |
| `backbone_proofread.parquet` | 10,316,976 | `9b553956c11558b9d5c7c9d3e66cea8af08f358ee897ab6e0e8ce91faa5c9a2d` |
| `banc_888_neurotransmitter_prediction_v2.csv` | 21,107,592 | `bb0f4afa48a05d90008c6d801e053ff2667fb1ba68e29501c92f49514540da1d` |
| `banc_fafb_reviewed_matches.csv.gz` | 6,581,434 | `ecdbb43cd5d4586e92f0d92a6f1d2beeecd2f429dd5b3e5309c0edc2daa515c4` |

Phase 4D graph artifacts:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `banc_graph_t1.npz` | 79,829,070 | `fee8e5e7f7dbd9b6d43ef125695b1b11f6c9613088c8c04dd0d883ff12ecc01e` |
| `banc_graph_t5.npz` | 13,484,120 | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| `banc_graph_t10.npz` | 6,699,534 | `00b3f447e2755660c273a63e11bc60a8afd8247906bbe0576f3a27a6ee1dc7a0` |
| `banc_nodes.csv.gz` | 3,800,401 | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| `banc_id_map.csv.gz` | 1,098,539 | `ede93fa7f33f34d0b77b800a8714b401e6f8ab7dbac44e4ce882518231dbbb16` |

The Phase 4C.5 audit JSON (`022eab4480d5a137b5ccbffdce39930ff2d6cf2b5ab108abdfa8ac2dc158d8a8`) was used only as a comparison reference.

### 1.2 Definitions

| Term | Operational definition |
|---|---|
| Node | Canonical `banc_888_id`, int64 in memory, string on disk |
| Descending neuron (DN) | `super_class == "descending"` |
| Motor neuron (MN) | `super_class == "motor"` |
| VNC intrinsic (strict intermediate) | `super_class == "ventral_nerve_cord_intrinsic"` |
| VNC-region candidate (broad intermediate) | `region == "ventral_nerve_cord"` and `super_class` not in `{descending, motor, glia, trachea, not_a_neuron}` |
| Direct pathway | One graph edge DN → MN |
| Two-hop path | One `(DN, intermediate, MN)` triple |
| Unique two-hop pair | One distinct `(DN, MN)` pair reachable through any intermediate |
| Edge weight | Integer synapse `count`; `norm` is never used |
| Tergotrochanter candidate | `super_class == "motor"` and `peripheral_target_type == "tergotrochanter_extensor_muscle"` |

The primary threshold is 5 (FAFB-comparable). Thresholds 1 and 10 are sensitivity analyses. Phase 4C.5 used the unfiltered edgelist, which corresponds to threshold 1 after the built graph removes self-edges; its figures are therefore compared to threshold 1, not to the primary threshold.

No motor decoder, command model, plasticity or game-control mapping was implemented. BANC and FAFB were not merged.

---

## 2. Executive summary

1. **Populations.** The Phase 4D graph has **172,433 nodes**, including **1,316 descending neurons**, **805 motor neurons**, **1,849 ascending neurons**, **12,850 VNC intrinsic neurons** and **27,778 VNC-region neurons**. Motor neurons split **392 left / 413 right**; **20** are tergotrochanter-extensor candidates (10 left, 10 right).

2. **The VNC-intrinsic discrepancy is fully explained.** Phase 4C.5 counted **12,866** metadata rows; the graph has **12,850**. The difference is exactly **16 neurons** that have no endpoint in the exported v2 edgelist in either direction. All 16 IDs are listed in the JSON. Fifteen are not proofread; one is.

3. **Direct descending→motor connectivity is dense at threshold 1 and sparse at threshold 10.** Edges fall from **17,745** to **6,409** to **3,822**; summed structural synapses fall only from **154,914** to **134,551** to **117,496**. Most synapse weight survives, but most weak edges do not. At threshold 5, **753 DNs** contact **638 MNs**; **167 MNs** have no direct DN input.

4. **Two-hop reachability is broad.** With strict VNC-intrinsic intermediates, **2,370,840 paths** collapse to **384,677 unique DN→MN pairs** at threshold 1; at threshold 5 the figures are **213,658** and **94,928**. **1,298 DNs** and **699 MNs** participate at threshold 1. Multiple intermediates reaching the same MN are not independent routes.

5. **Motor pools are bilaterally fed.** At threshold 1, **710 of 805 MNs** receive both left- and right-side DN input, **46** contralateral only, **16** ipsilateral only and **33** none. Cross-side direct edges outnumber same-side edges at every threshold (54.3%, 58.1%, 60.6%). This rejects a simple one-DN-to-one-muscle ipsilateral command model; it does not establish a circuit function.

6. **The 20 tergotrochanter candidates reproduce exactly at threshold 1:** 10 left, 10 right, **350 direct DN edges**, **113 DNs**, **3,043 structural synapses**. At threshold 5 they retain **139 edges / 39 DNs / 2,654 synapses**; at threshold 10, **81 / 24 / 2,265**. All 20 receive two-hop input at every threshold; 19 retain direct input at threshold 10. They are **jump-associated candidates**, not confirmed jump commands.

7. **Phase 4C.5 reproduces exactly at threshold 1.** All 15 compared metrics and every per-body-part row match with zero delta (see section 10).

8. **No significance claim is made.** No random-graph null model was used. Threshold effects are descriptive.

---

## 3. Part A — Population statistics

### 3.1 Graph populations

| Population | Graph nodes | Phase 4C.5 metadata | Delta |
|---|---:|---:|---:|
| Total graph nodes | 172,433 | — | — |
| Descending | 1,316 | 1,316 | 0 |
| Motor | 805 | 805 | 0 |
| Ascending | 1,849 | 1,849 | 0 |
| VNC intrinsic | 12,850 | 12,866 | **−16** |
| VNC region | 27,778 | — | — |
| Left motor | 392 | — | — |
| Right motor | 413 | — | — |
| Tergotrochanter candidates | 20 | 20 | 0 |

The graph retains all 172,433 edge endpoints. The metadata table has 188,508 rows, so **16,075 metadata-only rows** are excluded from the graph by design; they remain annotated in the source.

### 3.2 Motor neurons by effector

| Body part | MNs | Left | Right |
|---|---:|---:|---:|
| abdomen | 168 | 73 | 95 |
| front_leg | 139 | 69 | 70 |
| hind_leg | 126 | 63 | 63 |
| middle_leg | 126 | 63 | 63 |
| wing | 64 | 32 | 32 |
| neck | 49 | 27 | 22 |
| proboscis | 35 | 17 | 18 |
| haltere | 27 | 14 | 13 |
| pharynx | 22 | 9 | 13 |
| spiracle | 18 | 9 | 9 |
| antenna, scape | 8 | 4 | 4 |
| crop | 7 | 4 | 3 |
| uterus | 6 | 3 | 3 |
| eye | 4 | 2 | 2 |
| antenna | 2 | 1 | 1 |
| salivary_gland | 2 | 1 | 1 |
| unknown | 2 | 1 | 1 |

These are direct expert annotations, not connectivity-derived counts. The 805 total includes non-locomotor effectors and must not be reported as a locomotor count.

### 3.3 Annotation completeness

| Field | Motor neurons with value | Share of 805 |
|---|---:|---:|
| `body_part_effector` | 805 | 100.0% |
| `side` | 805 | 100.0% |
| `cell_type` | 805 | 100.0% |
| `peripheral_target_type` | 608 | 75.5% |
| `proofread = TRUE` | 805 | 100.0% |
| `neurotransmitter_verified` | 30 | 3.7% |

For the whole graph, `super_class` is present on 151,860 of 172,433 nodes, `cell_class` on 89,343, `cell_type` on 117,607, `side` on 158,195, and `proofread = TRUE` on 150,311.

---

## 4. The 16-neuron VNC-intrinsic discrepancy

Phase 4C.5 reported **12,866** VNC-intrinsic metadata rows. The Phase 4D graph contains **12,850** VNC-intrinsic nodes. The difference is exactly **16**, and it is not a data loss.

The 16 `banc_888_id` values are recorded in `PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.json` under `vnc_intrinsic_discrepancy.missing_ids`. Each has no endpoint in the exported v2 edgelist in either direction, so no graph node can be created for it. Their metadata rows are unchanged.

Properties of the 16:

| Property | Count |
|---|---:|
| Left / right | 8 / 8 |
| `proofread = TRUE` | 1 (`720575941469397981`, IN09A025, left, GABA) |
| `roughly_proofread = TRUE` | 0 |
| Status `TOO_SMALL` | 6 |
| Status missing | 8 |
| Other status flags | 2 (`MANC_MATCH_WRONG_SIDE`; `LR_TYPE_CONFLICT,SIDE_CONFLICT`) |
| Verified transmitter acetylcholine / GABA / glutamate / missing | 6 / 6 / 2 / 2 |

Cell types are IN-series VNC interneurons (IN01, IN02, IN03, IN05, IN09, IN12, IN16, IN18, IN19, IN23). The practical consequence is small: 16 of 12,866 strict intermediates (0.12%) are absent from the graph, and they cannot contribute paths. The correct population to cite for graph work is **12,850**; the correct metadata count is **12,866**.

---

## 5. Part B — Direct descending→motor pathways

### 5.1 Totals by threshold

| Measure | t1 | t5 (primary) | t10 |
|---|---:|---:|---:|
| Direct DN→MN edges | 17,745 | 6,409 | 3,822 |
| Summed structural synapses | 154,914 | 134,551 | 117,496 |
| Unique DN sources | 1,095 | 753 | 599 |
| Unique MN targets | 772 | 638 | 525 |
| MNs without direct input | 33 | 167 | 280 |
| DNs without a motor target | 221 | 563 | 717 |

At threshold 5, 36.1% of threshold-1 edges survive and carry 86.9% of the synapse count. At threshold 10, 21.5% of edges survive and carry 75.8% of synapses.

### 5.2 Degree distributions

| Threshold | DN out-degree mean / median / p90 / p99 / max | MN in-degree mean / median / p90 / p99 / max |
|---|---|---|
| t1 | 13.48 / 6 / 34 / 119.1 / 228 | 22.04 / 15 / 53 / 91.96 / 149 |
| t5 | 4.87 / 1 / 12 / 66.7 / 144 | 7.96 / 4 / 22 / 44.96 / 58 |
| t10 | 2.90 / 0 / 7 / 38.85 / 112 | 4.75 / 2 / 13 / 29 / 46 |

Degrees are counted over all DNs or MNs, including zeros. Among connected nodes at threshold 5, DN out-degree mean is 8.51 and MN in-degree mean is 10.05.

### 5.3 Connectivity by effector across thresholds

| Effector | MNs | t1 edges | t1 synapses | t5 edges | t5 synapses | t10 edges | t10 synapses |
|---|---:|---:|---:|---:|---:|---:|---:|
| abdomen | 168 | 1,250 | 5,314 | 303 | 3,672 | 139 | 2,622 |
| front_leg | 139 | 3,615 | 30,988 | 1,282 | 26,811 | 768 | 23,411 |
| hind_leg | 126 | 2,046 | 23,445 | 872 | 21,249 | 554 | 19,154 |
| middle_leg | 126 | 2,204 | 21,930 | 837 | 19,450 | 534 | 17,436 |
| wing | 64 | 2,704 | 17,126 | 957 | 13,928 | 482 | 10,809 |
| neck | 49 | 3,457 | 42,579 | 1,523 | 39,011 | 988 | 35,463 |
| proboscis | 35 | 902 | 5,131 | 223 | 4,030 | 123 | 3,395 |
| haltere | 27 | 507 | 3,198 | 143 | 2,572 | 90 | 2,199 |
| pharynx | 22 | 24 | 49 | 1 | 12 | 1 | 12 |
| spiracle | 18 | 278 | 1,954 | 97 | 1,634 | 58 | 1,369 |
| antenna, scape | 8 | 445 | 2,025 | 104 | 1,420 | 60 | 1,125 |
| crop | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| uterus | 6 | 28 | 60 | 3 | 17 | 0 | 0 |
| eye | 4 | 93 | 506 | 25 | 393 | 12 | 299 |
| antenna | 2 | 116 | 398 | 23 | 245 | 10 | 169 |
| salivary_gland | 2 | 35 | 94 | 7 | 45 | 1 | 10 |
| unknown | 2 | 41 | 117 | 9 | 62 | 2 | 23 |

The limb, wing, haltere and neck pools retain most of their synapse weight. The crop pool receives no direct DN input in this build, and the uterus and pharynx pools are nearly empty at threshold 5.

### 5.4 Connectivity by DN annotation (threshold 5)

`cell_class` is uniform (`descending_neuron`) for all 1,095 connected DNs. The published `super_cluster` labels split as follows:

| `super_cluster` | Edges | Synapses | DNs | MNs |
|---|---:|---:|---:|---:|
| postural control | 2,306 | 58,482 | 98 | 489 |
| head orienting | 969 | 27,262 | 148 | 165 |
| flight steering 1 | 698 | 12,217 | 88 | 147 |
| probing | 604 | 10,617 | 68 | 226 |
| flight power | 384 | 5,188 | 109 | 102 |
| walking | 361 | 5,106 | 47 | 228 |
| reproduction | 307 | 4,694 | 31 | 179 |
| grooming | 282 | 4,526 | 71 | 83 |
| walking steering | 240 | 3,501 | 20 | 100 |
| flight steering 2 | 98 | 1,057 | 32 | 40 |
| tactile | 39 | 674 | 6 | 37 |
| visceral control | 48 | 583 | 10 | 38 |
| threat response | 62 | 558 | 16 | 34 |
| taste-touch | 4 | 44 | 4 | 2 |
| feeding | 7 | 42 | 5 | 6 |

These labels are published cluster names, not validated functions of individual neurons. They are suitable for stratifying experiments, not for asserting that a neuron drives a behavior.

---

## 6. Part C — Two-hop descending→VNC candidate→motor pathways

### 6.1 Strict VNC-intrinsic intermediates

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| Intermediate population | 12,850 | 12,850 | 12,850 |
| DN→intermediate edges | 162,871 | 33,111 | 14,542 |
| Intermediate→MN edges | 132,085 | 45,787 | 27,047 |
| Paths | 2,370,840 | 213,658 | 66,443 |
| Unique DN→MN pairs | 384,677 | 94,928 | 38,811 |
| Unique DN sources | 1,298 | 1,219 | 1,035 |
| Intermediates with paths | 10,157 | 5,066 | 2,788 |
| Unique MN targets | 699 | 690 | 633 |
| MNs without two-hop input | 106 | 115 | 172 |
| Paths per reached MN: mean / median / max | 3,391.76 / 2,869 / 11,914 | 309.65 / 236 / 1,454 | 104.97 / 84 / 532 |

The path-to-pair ratio rises from 6.2 paths per unique pair at threshold 1 to 2.25 at threshold 5 and 1.71 at threshold 10. Counting paths overstates independent reachability, especially at low thresholds.

### 6.2 Broad VNC-region intermediates

The broad mask adds VNC-region neurons that are not strict intrinsics. Its population is **24,647**; at threshold 1 its composition among intermediates with paths is 10,157 VNC intrinsic, 1,210 ascending, 612 sensory, 217 unknown, 99 sensory_ascending, 60 visceral_circulatory and 5 ascending_visceral_circulatory.

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| DN→intermediate edges | 215,279 | 43,241 | 19,201 |
| Intermediate→MN edges | 157,985 | 52,275 | 30,154 |
| Paths | 2,899,251 | 262,734 | 84,651 |
| Unique DN→MN pairs | 472,289 | 119,620 | 51,314 |
| Unique DN sources | 1,310 | 1,254 | 1,134 |
| Intermediates with paths | 12,360 | 5,682 | 3,086 |
| Unique MN targets | 775 | 750 | 679 |
| MNs without two-hop input | 30 | 55 | 126 |

The broad mask includes sensory and ascending neurons, so it must not be presented as a premotor population. It is a reachability sensitivity analysis only. The strict mask is the defensible "connectivity-derived premotor candidate" definition.

### 6.3 Path sides (strict intermediates)

| Threshold | Same-side paths | Cross-side paths | Missing-side paths | Same share of known |
|---|---:|---:|---:|---:|
| t1 | 1,172,621 | 1,193,793 | 4,426 | 0.4955 |
| t5 | 101,097 | 112,184 | 377 | 0.4740 |
| t10 | 30,579 | 35,742 | 122 | 0.4611 |

### 6.4 Paths by effector (strict, threshold 5)

| Effector | Paths | Motor targets | Same share | Cross share |
|---|---:|---:|---:|---:|
| front_leg | 69,566 | 139 | 0.5014 | 0.4986 |
| middle_leg | 51,088 | 126 | 0.4451 | 0.5549 |
| hind_leg | 38,632 | 126 | 0.4206 | 0.5794 |
| wing | 34,427 | 64 | 0.5029 | 0.4971 |
| abdomen | 8,162 | 166 | 0.5143 | 0.4857 |
| neck | 6,926 | 23 | 0.5313 | 0.4687 |
| haltere | 3,695 | 27 | 0.4426 | 0.5574 |

At threshold 1 the largest strict path pools are front_leg (708,112), middle_leg (526,814), hind_leg (403,099) and wing (396,473).

### 6.5 Highest-reach motor targets (strict, threshold 1)

| `banc_888_id` | Cell type | Side | Body part | Paths |
|---|---|---|---|---:|
| 720575941498960546 | tergopleural_promotor_pleural_promotor | left | front_leg | 11,914 |
| 720575941506261538 | tergopleural_promotor_pleural_promotor | left | front_leg | 11,678 |
| 720575941630940642 | iv4 | left | wing | 11,571 |
| 720575941513173763 | iv4 | right | wing | 11,233 |
| 720575941459347411 | iii4 | left | wing | 11,185 |

These are structural reach counts and do not identify command neurons.

### 6.6 Intermediate annotation coverage

| Threshold | Intermediates with paths | `proofread = TRUE` | `cell_type` present |
|---|---:|---:|---:|
| t1 | 10,157 | 10,148 | 10,157 |
| t5 | 5,066 | 5,062 | 5,066 |
| t10 | 2,788 | 2,787 | 2,788 |

Intermediate coverage is effectively complete for the strict mask. Proofread status is not a measure of premotor function.

---

## 7. Part D — Left/right motor organisation

### 7.1 All motor neurons

| Threshold | Edges | Same side | Cross side | Same share | No input | Ipsi only | Contra only | Bilateral |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| t1 | 17,745 | 8,105 | 9,611 | 0.4575 | 33 | 16 | 46 | 710 |
| t5 | 6,409 | 2,679 | 3,722 | 0.4185 | 167 | 51 | 120 | 467 |
| t10 | 3,822 | 1,503 | 2,314 | 0.3938 | 280 | 38 | 121 | 366 |

At every threshold, bilateral input is the dominant category. Cross-side edges exceed same-side edges, and the imbalance grows as weak edges are removed.

### 7.2 Locomotor effector pools

Threshold 1:

| Effector | MNs (L/R) | Edges | Same | Cross | No input | Ipsi | Contra | Bilateral |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| front_leg | 139 (69/70) | 3,615 | 1,632 | 1,963 | 0 | 1 | 3 | 135 |
| middle_leg | 126 (63/63) | 2,204 | 833 | 1,371 | 2 | 0 | 7 | 117 |
| hind_leg | 126 (63/63) | 2,046 | 758 | 1,288 | 2 | 3 | 3 | 118 |
| wing | 64 (32/32) | 2,704 | 1,416 | 1,288 | 0 | 0 | 0 | 64 |
| haltere | 27 (14/13) | 507 | 257 | 250 | 2 | 2 | 1 | 22 |
| abdomen | 168 (73/95) | 1,250 | 485 | 765 | 8 | 5 | 29 | 126 |
| neck | 49 (27/22) | 3,457 | 1,601 | 1,849 | 0 | 0 | 0 | 49 |

Threshold 5:

| Effector | Edges | Same | Cross | No input | Ipsi | Contra | Bilateral | Dominant |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| front_leg | 1,282 | 500 | 774 | 16 | 10 | 15 | 98 | bilateral |
| middle_leg | 837 | 259 | 578 | 24 | 7 | 19 | 76 | bilateral |
| hind_leg | 872 | 262 | 610 | 19 | 7 | 17 | 83 | bilateral |
| wing | 957 | 522 | 435 | 2 | 3 | 0 | 59 | bilateral |
| haltere | 143 | 73 | 70 | 11 | 5 | 3 | 8 | bilateral |
| abdomen | 303 | 94 | 209 | 62 | 12 | 61 | 33 | contralateral only |
| neck | 1,523 | 694 | 829 | 0 | 0 | 0 | 49 | bilateral |

At threshold 10 the abdomen pool is also dominated by contralateral-only input (47), with 105 MNs receiving none. That does not license a direction claim: the abdomen is not a limb steering pool, and asymmetry in structural input is not a movement direction.

### 7.3 Interpretation

- Every leg, wing, haltere and neck pool has balanced left/right populations and near-complete direct DN input at threshold 1.
- The wing and neck pools are 100% bilaterally fed at threshold 1; the legs are 93–97% bilaterally fed.
- The abdomen is the least balanced pool and loses the most input at threshold 5. Its contralateral dominance is a structural observation, not evidence of a contralateral motor command.
- No direction, turning sign or gait phase is inferred from these counts.

---

## 8. Part E — Tergotrochanter-associated candidates

### 8.1 Candidate pool

The pool is defined by direct annotation only: `super_class == "motor"` and `peripheral_target_type == "tergotrochanter_extensor_muscle"`.

| Property | Value |
|---|---:|
| Candidates | 20 |
| Left / right | 10 / 10 |
| Exact target annotation | 20 / 20 |
| Body part: front_leg / middle_leg / hind_leg | 8 / 6 / 6 |
| Cell types | 5 |
| `proofread = TRUE` | 20 |
| `neurotransmitter_verified` | 0 |
| Status contains `LR_TYPE_CONFLICT` | 8 |

Cell types are `tergotrochanter_extensor`, `tergotrochanter_extensor_MetaAN`, `tergotrochanter_extensor_PDMN`, `tergotrochanter_extensor_TT` and `tergotrochanter_extensor_TT_PDMN`. The `LR_TYPE_CONFLICT` flag in 8 of 20 means left/right type assignment is not fully settled even though the pool membership is.

### 8.2 Direct input

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| Candidates with direct input | 20 | 20 | 19 |
| Direct DN edges | 350 | 139 | 81 |
| Direct DN synapses | 3,043 | 2,654 | 2,265 |
| Direct DN sources | 113 | 39 | 24 |
| Left-target synapses | 1,515 | 1,326 | 1,116 |
| Right-target synapses | 1,528 | 1,328 | 1,149 |
| Left/right synapse ratio | 0.9915 | 0.9985 | 0.9713 |

Edge sides at threshold 1: left→left 58, left→right 127, right→left 117, right→right 48; same-side 106 (30.3%), cross-side 244 (69.7%). At threshold 5 the same-side share falls to 19.4%; at threshold 10 it is 22.2%. The surviving strong edges are predominantly cross-side.

### 8.3 Two-hop input

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| Candidates with two-hop input | 20 | 20 | 20 |
| Paths | 115,323 | 11,612 | 3,490 |
| Unique DN→MN pairs | 13,661 | 4,566 | 1,948 |
| Unique DNs | 1,298 | 1,219 | 1,035 |
| Unique intermediates | 2,883 | 836 | 391 |
| Sources direct only / two-hop only / both | 1 / 1,036 / 112 | 2 / 640 / 37 | 1 / 404 / 23 |

### 8.4 Strongest direct sources at threshold 1

| `banc_888_id` | Cell type | Side | Cluster | Edges | Synapses |
|---|---|---|---|---:|---:|
| 720575941480799395 | DNg105 | left | postural control | 10 | 405 |
| 720575941535975873 | DNg105 | right | postural control | 9 | 396 |
| 720575941658941264 | DNge079 | left | postural control | 9 | 293 |
| 720575941724607290 | DNge079 | right | postural control | 10 | 287 |
| 720575941640505375 | DNge035 | right | postural control | 10 | 177 |

These DNs are structurally positioned to influence the tergotrochanter pool. That is not evidence that they trigger jumping, escape or take-off. The candidate pool and its inputs are **jump-associated structural candidates** only.

---

## 9. Part F — Threshold sensitivity

### 9.1 Direct pathway retention

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| Edges | 17,745 | 6,409 (36.1%) | 3,822 (21.5%) |
| Synapses | 154,914 | 134,551 (86.9%) | 117,496 (75.8%) |
| Motor targets | 772 | 638 (82.6%) | 525 (68.0%) |

All 3,822 threshold-10 pairs are present at thresholds 1 and 5. They are 21.5% of threshold-1 pairs. **525 MNs** have input at all three thresholds; **33 / 167 / 280** have none at t1 / t5 / t10.

### 9.2 Effector retention

| Effector | t5 synapse retention | t10 synapse retention | MNs with input t1 / t5 / t10 |
|---|---:|---:|---|
| front_leg | 0.8652 | 0.7555 | 139 / 123 / 102 |
| middle_leg | 0.8869 | 0.7951 | 124 / 102 / 89 |
| hind_leg | 0.9063 | 0.8170 | 124 / 107 / 92 |
| wing | 0.8133 | 0.6311 | 64 / 62 / 57 |
| haltere | 0.8043 | 0.6876 | 25 / 16 / 10 |
| abdomen | 0.6910 | 0.4934 | 160 / 106 / 63 |
| neck | 0.9162 | 0.8329 | 49 / 49 / 49 |

The leg pools are the most threshold-stable; the wing and haltere lose a larger fraction of their weaker input; the abdomen is the least stable major pool. Pharynx retention is 0.2449 at both thresholds, and the uterus reaches zero at threshold 10. These differences are descriptive.

### 9.3 Motor neurons losing the most input between t1 and t5

| Cell type | Side | Effector | t1 synapses | t5 | t10 | Loss t1→t5 | Retention t5 |
|---|---|---|---:|---:|---:|---:|---:|
| CvN5 | left | neck | 1,165 | 988 | 825 | 177 | 0.8481 |
| CvN10 | left | neck | 884 | 717 | 606 | 167 | 0.8111 |
| CB0810 | left | antenna, scape | 561 | 413 | 307 | 148 | 0.7362 |
| CvN10 | right | neck | 917 | 774 | 606 | 143 | 0.8441 |
| CB0810 | right | antenna, scape | 451 | 326 | 266 | 125 | 0.7228 |

The neck and antennal pools rely on many weak edges, but still retain most of their synapse weight.

### 9.4 Intermediate and jump stability

| Measure | t1 | t5 | t10 |
|---|---:|---:|---:|
| Strict intermediates with paths | 10,157 | 5,066 | 2,788 |
| Broad intermediates with paths | 12,360 | 5,682 | 3,086 |
| Jump direct edges | 350 | 139 | 81 |
| Jump direct DNs | 113 | 39 | 24 |
| Jump candidates with direct input | 20 | 20 | 19 |
| Jump two-hop paths | 115,323 | 11,612 | 3,490 |

The tergotrochanter pool is unusually robust at the two-hop level: all 20 candidates remain reachable at every threshold. That reflects dense VNC convergence, not a privileged jump circuit.

### 9.5 No null model

No random-graph control, permutation test or significance claim was made. The threshold comparisons above are descriptive. Any statement about whether a pathway is "more connected than expected" requires a pre-registered degree-preserving null model, which is deferred.

---

## 10. Reproducibility of Phase 4C.5

Phase 4C.5 read the unfiltered edgelist, which is equivalent to the threshold-1 graph after self-edge removal. All 15 comparison checks match with delta 0:

| Check | Phase 4C.5 | Phase 4E t1 |
|---|---:|---:|
| Direct DN→MN edges | 17,745 | 17,745 |
| Direct DN→MN synapses | 154,914 | 154,914 |
| Direct DNs | 1,095 | 1,095 |
| Direct MNs | 772 | 772 |
| DN→VNC-intrinsic edges | 162,871 | 162,871 |
| VNC-intrinsic→MN edges | 132,085 | 132,085 |
| Two-hop paths | 2,370,840 | 2,370,840 |
| Unique DN→MN pairs | 384,677 | 384,677 |
| Two-hop DNs | 1,298 | 1,298 |
| Two-hop MNs | 699 | 699 |
| Jump MNs | 20 | 20 |
| Jump direct edges | 350 | 350 |
| Jump DNs | 113 | 113 |
| Jump synapses | 3,043 | 3,043 |
| Jump left/right | 10 / 10 | 10 / 10 |

The per-body-part table also matches with no mismatches. This confirms that no count in the earlier audit was wrong; it was computed at a different edge threshold.

---

## 11. Scientific separation of claim types

| Category | Examples in this report | Status |
|---|---|---|
| Published annotations | 805 motor neurons; 12,866 metadata VNC intrinsics; `body_part_effector`; `peripheral_target_type`; tergotrochanter candidates | Author-supplied labels; not measured here |
| Observed connectivity | 17,745 direct edges; 350 jump edges; 2,370,840 two-hop paths; side counts | Derived from the exported v2 edgelist |
| Connectivity-derived candidates | VNC intermediates with paths; premotor candidates; DNs structurally upstream of the jump pool | Candidates only |
| Computational assumptions | Threshold 1/5/10; integer synapse weight; path = triple; broad-mask exclusions | Explicit and replayable |
| Biological hypotheses | Jump-associated role of the tergotrochanter pool; locomotor roles of DN clusters; bilateral coordination | Literature-informed, not tested here |

Mandatory qualifications:

- **BANC is a different specimen from FAFB.** Its root IDs, edges and cell instances are not interchangeable with the local FAFB graph, and no merge was performed.
- **The graph is an exported subset.** Only pairs present in the v2 edgelist are edges; 16,075 metadata rows and 16 VNC-intrinsic neurons are not graph nodes.
- **Structural adjacency is not sign or function.** Synapse count is not conductance, release probability, inhibition or excitation. Verified transmitter is available for only 30 of 805 motor neurons and 155 of 1,316 DNs.
- **Effector annotation is not a game command.** A `front_leg_motor_neuron` label does not map to "move left" or "jump".
- **The tergotrochanter pool is jump-associated, not a jump command.** No trigger DN, direction or motor program is identified.
- **No Subway Surfers action has been identified.** No neuron, pool or pathway in this analysis can be assigned to a game action.

---

## 12. Limitations

1. BANC is a separate specimen from FAFB; this analysis does not merge them.
2. The graph contains only exported v2 pairs with both partners identified.
3. Edge weight is synapse count, not conductance or release probability.
4. Structural adjacency does not establish synaptic sign or physiological function.
5. Every intermediate is a connectivity-derived premotor candidate, not a validated premotor neuron.
6. Two-hop paths are triples, not independent physiological routes.
7. Motor-effector annotations do not establish a specific game command.
8. The 20 tergotrochanter candidates are jump-associated, not confirmed jump commands.
9. No biological Subway Surfers action has been identified.
10. No random-graph null model or significance test was used.

Additional caveats:

- Threshold 1 includes very weak edges (1–4 synapses) that dominate path counts. Threshold 5 is the recommended primary graph, with 1 and 10 as sensitivity bounds.
- The broad intermediate mask contains sensory and ascending neurons and should not be described as premotor.
- `super_cluster` and `cell_function` labels are published descriptors, not validated functions of individual cells.
- The 20 jump candidates include 8 with `LR_TYPE_CONFLICT`; pool membership is exact, but left/right type naming is not fully settled.
- Motor-neuron transmitters are predictions unless `neurotransmitter_verified` is populated. Thirty of 805 are verified.
- The graph cannot establish direction of movement, gait phase, turning sign or muscle force.

---

## 13. Recommended Phase 4F design

Phase 4F should be a **pathway validation and null-model phase**, not a motor decoder. Recommended scope:

1. **Pre-register a null model.** Define a degree-preserving or weight-preserving edge permutation for the threshold-5 graph and test whether the observed DN→MN, jump-pool and side-crossing counts exceed the null. Report effect sizes with confidence intervals.
2. **Define a high-confidence subgraph.** Restrict to `proofread = TRUE`, threshold 5, verified transmitters where available, and MNs with exact `peripheral_target_type`. Compare it to the full graph as a sensitivity analysis.
3. **Test the tergotrochanter hypothesis explicitly.** Ask whether the 20 candidates share stronger input from a specific DN subset than matched non-jump leg MNs, using the pre-registered null. Do not call any DN a jump command from structural data alone.
4. **Stratify by effector and side.** Compare front/middle/hind leg and wing pools on path counts, same/cross-side input and threshold retention. Use matched pools rather than global totals.
5. **Add sign only as a prior.** Use `neurotransmitter_verified` for the small verified subset; keep predicted transmitters descriptive and separate. Do not assign excitatory/inhibitory signs to unverified edges.
6. **Keep FAFB and BANC separate.** If cross-dataset comparison is needed, use the published match tables or NBLAST as a label bridge, never as an edge bridge.
7. **Acceptance criteria.** A Phase 4F result should be considered usable only if it survives: (a) the pre-registered null, (b) threshold 5 versus 10, (c) proofread-only restriction, and (d) a held-out or independently processed graph.
8. **Do not build a motor decoder or game controller.** The current data support structural hypotheses only. A decoder would require physiological sign, muscle-level innervation and behavioural validation that this dataset does not provide.

---

## 14. Reproducibility and verification

### 14.1 Commands

```bash
python experiments/phase_4e/analyze_motor_pathways.py
python -m pytest tests/test_phase_4e_pathways.py -q
```

The script accepts `--graph-dir`, `--nodes`, `--manifest`, `--audit` and `--output`. It records input SHA-256 values, row/column counts, thresholds, path semantics and software versions in the JSON.

### 14.2 Determinism

Two independent runs produced byte-identical JSON after excluding `generated_at_utc` and `runtime_seconds`. All ordered lists use explicit sort keys; no sampling or randomness is used.

### 14.3 Runtime

- Analysis: **35.8 s** (JSON-reported), 37.2 s and 39.1 s wall time on the two determinism runs.
- Focused tests: **14 passed in 3.55 s**.
- Full suite: **345 passed in 26.18 s** (331 pre-existing tests plus the 14 Phase 4E tests; exit code 0).

### 14.4 Integrity

- Manifest verification: **pass**, zero failures.
- Graph node IDs equal the node table for thresholds 1, 5 and 10.
- FAFB isolation snapshot: **unchanged**.
- Phase 4D graph artifacts, raw BANC inputs and the root README were not modified.
- No file was staged, committed or pushed.

### 14.5 Files

Created for Phase 4E:

- `experiments/phase_4e/analyze_motor_pathways.py`
- `reports/PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.json`
- `reports/PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.md`
- `tests/test_phase_4e_pathways.py`

No existing file was modified.

---

## 15. Verdict

**PASS WITH LIMITATIONS**

The Phase 4E analysis is complete, deterministic and reproducible. It reproduces every Phase 4C.5 figure at threshold 1, resolves the 16-neuron VNC discrepancy, and provides the required population, direct-pathway, two-hop, side-organisation, tergotrochanter and threshold-sensitivity analyses without rebuilding the graph or touching protected artifacts.

The limitations are substantive and must travel with any downstream use: the graph is a structural export, weights are not conductances, intermediates are candidates, the jump pool is not a command, and no Subway Surfers action has been identified. Phase 4F should add a pre-registered null model and a high-confidence subgraph before any motor decoder is considered.
