# Phase 4C.5 — BANC Graph Readiness Audit

**Phase:** 4C.5
**Status:** Complete, read-only audit
**Verdict:** **READY WITH LIMITATIONS**
**Canonical node identifier:** `banc_888_id`
**Machine-readable result:** `reports/PHASE_4C5_BANC_GRAPH_READINESS_AUDIT.json`
**Reproducible script:** `experiments/phase_4c/audit_banc_graph.py`
**Focused tests:** `tests/test_banc_graph_audit.py`

This audit evaluates whether the local BANC v888 export can be turned into a
separate, reproducible structural graph for FLY-SURFER. It does not merge BANC
with FAFB, does not modify any raw dataset, and does not introduce plasticity.
No physiological motor command is inferred from structure.

---

## 1. Executive verdict

**READY WITH LIMITATIONS.** Every audit block passed on the measured checks:
the graph has a clean canonical key, no null or duplicate edges, exact
`count`/`pre_count`/`post_count` identities, complete motor and descending
annotation coverage, and enough descending-to-motor structure to build
separate left/right and body-part motor-pool experiments. The graph is not a
whole-connectome graph: the v2 edgelist contains only links whose two partners
were both identified, self-loops are present in the local build despite the
published dictionary saying they were excluded, the effector neurotransmitter
predictions cannot be used as output signs, and no connection in this audit is
physiologically validated.

The recommended construction policy is in Section 9. Phase 4D should not begin
until that policy is explicitly accepted.

---

## 2. Scope and inputs

Only the main `FLY-SURFER` repository was used. Five local BANC files were read.
Each local file is byte-identical to the **current public Google Storage
object** (size and MD5 match exactly), although two of them differ from their
published data-dictionary snapshots (Section 10).

| Input | Rows | Bytes | SHA-256 (local) | GCS MD5 | GCS updated |
|---|---:|---:|---|---|---|
| `metadata/banc_888_meta.feather` | 188,508 × 81 | 57,503,026 | `86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098` | `jCuTpgjHFj7J2U1o4HVv9A==` | 2026-08-21 |
| `connectivity/banc_888_edgelist_simple_v2.feather` | 11,752,828 × 6 | 305,250,378 | `363fdef3813b72a5e45a42f17034cd5a544b654c838929cecf6e1ce5f60625cb` | `OUQG+Km98JPIlfla/09sSQ==` | 2026-06-02 |
| `annotations/backbone_proofread.parquet` | 211,947 × 10 | 10,316,976 | `9b553956c11558b9d5c7c9d3e66cea8af08f358ee897ab6e0e8ce91faa5c9a2d` | `arLs+/gLp6A9tknjNnP8+Q==` | 2026-05-13 |
| `annotations/banc_888_neurotransmitter_prediction_v2.csv` | 169,635 | 21,107,592 | `bb0f4afa48a05d90008c6d801e053ff2667fb1ba68e29501c92f49514540da1d` | `TrvR1uBdQZKtDG2ydzmo4w==` | 2026-05-13 |
| `cross_dataset_matches/banc_fafb_reviewed_matches.csv.gz` | 64,372 | 6,581,434 | `ecdbb43cd5d4586e92f0d92a6f1d2beeecd2f429dd5b3e5309c0edc2daa515c4` | `r513qdcrXyNjTaCwFQNqJg==` | 2026-06-07 |

Edgelist schema: `pre`, `post`, `count`, `norm`, `post_count`, `pre_count`
(all six columns have zero nulls). The metadata loader uses 24 of the 81
columns; the total is recorded in the JSON.

**Dataset identity.** BANC materialization v888 (April 16, 2026 snapshot),
v2 synapse model rolled up at postsynapse size ≥ 5. Paper: Bates et al.,
*Nature* 656, 957–970 (2026), DOI `10.1038/s41586-026-10735-w`.

**Separation from FAFB.** All counts below are BANC-only. No BANC edge was
projected onto FAFB neurons, and no FAFB edge was combined with BANC. The
reviewed FAFB match table is used only to describe annotation provenance.

---

## 3. Evidence classes used in this report

| Class | Meaning in this audit |
|---|---|
| **Published biological reconstruction** | Synapse counts and partner identities from the BANC v888 segmented connectome. Structural evidence only. |
| **Published annotation** | `super_class`, `cell_type`, `side`, `body_part_effector`, `super_cluster`, proofread flags, verified neurotransmitter. Curated, but not re-validated here. |
| **Computational prediction** | `neurotransmitter_predicted` and NBLAST matches. Treat as predictions, not ground truth. |
| **Computational assumption in this audit** | Canonical-key choice, threshold ≥ 5, self-edge exclusion, annotation-join rules. These are policy decisions, not findings about the fly. |
| **Hypothesis (not tested)** | That a BANC structural pathway corresponds to a game action such as jump, walk, or turn. Nothing in this audit establishes that. |

---

## 4. A. Canonical ID integrity

**Result: PASS. Canonical key is `banc_888_id`.**

| Column | Nulls | Unique non-null | Duplicate rows | Equals `banc_888_id` | Mismatch rows |
|---|---:|---:|---:|---:|---:|
| `banc_888_id` | 0 | 188,508 | 0 | — | — |
| `root_id` | 0 | 188,340 | 168 | 172,189 (91.34%) | 16,319 |
| `root_626` | 0 | 185,165 | 3,343 | 115,735 (61.40%) | 72,773 |
| `root_850` | 0 | 188,196 | 312 | 175,090 (92.88%) | 13,418 |
| `root_888` | 0 | 188,508 | 0 | 188,506 (99.9989%) | 2 |
| `root_890` | 274 | 188,197 | 310 | 180,390 (95.83%) | 7,844 |

- `banc_888_id` has 188,508 unique non-null values, no empty strings, and
  covers **100% of the 172,433 graph endpoints**. Joining the edgelist on
  `pre`/`post` → `banc_888_id` loses no node.
- `root_888` is the only near-equivalent column: two rows differ. Both are
  unproofread rows with no `super_class`:
  - `banc_888_id 720575941229247158` ↔ `root_888 147423687484661800`
  - `banc_888_id 720575940434812394` ↔ `root_888 150730400321262552`
- `root_id` is not interchangeable with `banc_888_id`: 168 duplicate rows and
  16,319 mismatches. This directly contradicts the metadata dictionary, which
  states `root_id` = `banc_888_id`.
- `root_890` is unsafe: 274 nulls and 310 duplicate rows.

**Decision:** use `banc_888_id`, stored as int64 in memory and as an 18-digit
decimal string on disk, for every node key, edge endpoint, and annotation join.
Never join on `root_id`, `root_626`, `root_850`, or `root_890`.

The initial float64 comparison in an early draft produced a wrong `root_890`
match share (52.97%) because 18-digit IDs lose precision as doubles. All final
comparisons are string-based.

---

## 5. B. Self-edge investigation

**Result: 156,311 self-loop rows. Exclude from the simulation graph; keep in
the raw file.**

| Measure | Value |
|---|---:|
| Self-edge rows | 156,311 |
| Share of edgelist rows | 1.33% |
| Unique affected nodes | 156,311 |
| Rows per affected node | 1.0 |
| Summed `count` | 1,422,866 |
| Share of summed synapses | 3.98% |
| Count quantiles | p50 5, p90 19, p99 77, max 1,103 |
| Affected share of graph nodes | 90.7% |

Distribution by `super_class` (top):

| `super_class` | Self-loops |
|---|---:|
| optic_lobe_intrinsic | 67,599 |
| central_brain_intrinsic | 30,170 |
| (missing) | 17,725 |
| ventral_nerve_cord_intrinsic | 12,767 |
| sensory | 12,169 |
| visual_projection | 7,122 |
| glia | 3,587 |
| ascending | 1,846 |
| descending | 1,311 |
| motor | 791 |
| other classes | 1,224 |

Interpretation:
- Exactly one self-loop per affected segment, present in nearly every graph
  node including glia and trachea, is more consistent with a systematic
  segmentation / synapse-assignment artifact than with biological autapses.
- The BANC paper reports about a 2.1% autapse rate in reviewed cubes, expects
  most autapses to be presynaptic misassignments, and recommends filtering.
- The published v2 dictionary says autapses are excluded at build time. The
  local/current object contradicts that statement.
- Individual loops cannot be classified as biology or artifact without
  synapse-level evidence. They are therefore **not deleted from the raw file**;
  they are excluded only when the simulation graph is constructed.
- `pre_count` and `post_count` include the self-loop. If absolute input
  fractions are needed after exclusion, those denominators must be recomputed
  from the filtered graph rather than reused from the edgelist.

---

## 6. C. Edge integrity

**Result: PASS. No cleaning or aggregation required.**

| Check | Result |
|---|---|
| Source rows / parsed rows | 11,752,828 / 11,752,828 |
| Nulls in `pre`, `post`, `count`, `norm`, `pre_count`, `post_count` | 0 |
| Unique nodes | 172,433 |
| Unique directed pairs | 11,752,828 |
| Duplicate pair rows | 0 |
| Aggregation needed | No |
| `count` ≤ 0 | 0 |
| `count` range | 1 – 1,103 |
| Non-finite `norm` | 0 |
| `norm` ≤ 0 | 0 |
| Edge endpoints missing from metadata | 0 |
| Endpoint coverage | 100% |

The edgelist is already one row per directed `(pre, post)` pair. If a future
source is aggregated again, sum `count`; never sum `norm`.

**Isolated metadata rows:** 16,075 metadata rows have no edge in either
direction. Of these, 641 are `proofread = TRUE` and 1,313 are annotated neurons
(non-null `super_class`, excluding glia/trachea/not_a_neuron). Isolated rows are
retained in the annotation table but are not graph nodes. Their absence is not
evidence that the neuron does not exist; it means no partner was identified in
this edgelist build.

---

## 7. D. Annotation quality

**Result: PASS. Motor and descending populations are complete and almost
entirely proofread.**

Overall metadata (188,508 rows):

| Measure | Value |
|---|---:|
| Annotated neurons | 146,769 |
| `proofread = TRUE` | 150,952 |
| `roughly_proofread = TRUE` | 5,060 |
| Proofread or roughly proofread | 156,012 |
| Missing `super_class` | 28,632 |
| — of which `proofread = TRUE` | 11,344 |
| Missing `cell_type` | 69,760 |
| Missing `side` | 14,901 |

Missing annotation is **unknown**, not absence: 11,344 fully proofread rows
still lack `super_class`. Graph nodes missing `super_class`: 20,573 of 172,433.

Population summaries:

| Population | Rows | Proofread | Roughly | Missing cell type | Missing side | Verified NT | Missing status |
|---|---:|---:|---:|---:|---:|---:|---:|
| motor | 805 | 805 | 0 | 0 | 0 | 30 | 0 |
| descending | 1,316 | 1,312 | 4 | 0 | 6 | 155 | 1 |
| ascending | 1,849 | 1,844 | 5 | 0 | 16 | 1,306 | 1 |
| VNC intrinsic | 12,866 | 12,821 | 14 | 27 | 82 | 9,974 | 9,553 |

Motor neurons:
- All 805 are proofread. Every motor neuron has a cell type and a side.
- Only 30 have a **verified** neurotransmitter, all glutamate. The remaining
  775 rely on prediction.
- Predicted top transmitters: GABA 444, acetylcholine 179, octopamine 71,
  glutamate 35, serotonin 11, dopamine 3; 59 have no prediction.
- The BANC prediction is evaluated on non-effector neurons because effector
  output synapses lie mostly outside the imaged volume. For motor neurons it is
  therefore dominated by input-site chemistry, not by the transmitter released
  at the neuromuscular junction. **Do not use it as an output sign.**
- FAFB matches exist for 105 motor neurons; 101 have NBLAST matches. By body
  part the matches are neck 26, proboscis 35, pharynx 21, antenna/scape 8,
  crop 7, eye 4, antenna 2, salivary gland 2, and **zero for front/middle/hind
  leg, wing, haltere, abdomen, and spiracle**. FAFB is brain-only, so limb motor
  neurons exist only in BANC. This is the main reason BANC is required for
  locomotor work.

Descending neurons:
- 1,312 of 1,316 are proofread; 4 roughly proofread. All have a cell type;
  6 lack a side.
- 155 have a verified transmitter: acetylcholine 113, glutamate 16,
  acetylcholine+glutamate 8, serotonin 6, GABA 4, glutamate+tyramine 2.
- Predicted top transmitters: acetylcholine 910, GABA 241, glutamate 102,
  serotonin 19, octopamine 13, dopamine 11; 20 have no prediction.
- 1,304 have any FAFB match; 1,277 have an NBLAST match.

Auxiliary tables:
- `backbone_proofread.parquet`: 211,947 append-only history rows, 150,507 unique
  `pt_root_id`, 150,506 present in metadata. `valid_id` is not the neuron root;
  only 79,080 of its values are metadata keys. Join on `pt_root_id`.
- `banc_fafb_reviewed_matches.csv.gz`: 64,372 rows, 64,372 unique
  `pt_root_id`, 33,147 unique `match_id`, 62,088 with `valid = t` and 2,284
  with `valid = f`. It covers 64,372 BANC neurons, not the full table.
- The file is named `.csv.gz` but is **plain CSV** (first bytes `pt_r`, no gzip
  magic). It must be read with `compression=None`.

---

## 8. E. Synaptic weight semantics

**Result: PASS. `count` is the defensible weight; `norm` is not
physiological.**

| Measure | Value |
|---|---:|
| Summed `count` | 35,733,096 |
| Summed `pre_count` | 35,733,096 |
| Summed `post_count` | 35,733,096 |
| `pre_count` = outgoing row sums | 100% of sources |
| `post_count` = incoming row sums | 100% of targets |
| `pre_count` constant per source | Yes |
| `post_count` constant per target | Yes |
| `norm` vs `count / post_count`, max relative error | 0.0106 |
| Rows within 0.1% of the identity | 97.96% |
| `count` quantiles | p50 1, p90 6, p99 27, max 1,103 |
| `count = 1` share of pairs | 54.94% |
| `count ≥ 5` share of pairs | 13.74% |
| `count ≥ 5` share of synapses | 55.40% |
| `norm` quantiles | p50 0.005548, p90 0.030303, p99 0.142857, max 1.0 |

Field meanings:
- `count` — synapses from `pre` to `post` after the v2 size ≥ 5 filter.
- `norm` — `count / post_count`, rounded to four significant figures. It is a
  **target-normalized fraction**, not a physiological synaptic weight.
- `pre_count` — total outgoing synapses of `pre` across all identified targets
  in this table.
- `post_count` — total incoming synapses of `post` across all identified
  sources in this table.

Caveat: the edgelist contains only pairs where both partners were identified,
roughly one fifth of all BANC synaptic links. `pre_count`, `post_count`, and
`norm` are therefore totals over identified partners only, and they include
self-loops. They are not whole-connectome totals.

**Weight policy:** integer `count`, with `count ≥ 5` as the primary
FAFB-comparable threshold. Run sensitivity at 1, 5, and 10. Do not use `norm`
as a synaptic weight and do not sum it.

---

## 9. F. Locomotor pathway readiness

**Result: PASS for graph construction. Not evidence of a motor command.**

### 9.1 Direct descending → motor connectivity

| Measure | Value |
|---|---:|
| Motor neurons | 805 |
| Descending neurons | 1,316 |
| Direct DN→MN edges | 17,745 |
| Direct DN→MN synapses | 154,914 |
| DNs with ≥1 motor target | 1,095 (83.2%) |
| MNs with ≥1 DN input | 772 (95.9%) |

Side structure of direct edges:

| Direction | Edges |
|---|---:|
| left → left | 3,830 |
| left → right | 4,826 |
| right → left | 4,785 |
| right → right | 4,275 |
| same side | 8,105 |
| cross side | 9,611 |

(29 edges have a missing side on at least one endpoint and are not in the four
directional cells.) Cross-side edges outnumber same-side edges, so a
one-DN-to-one-muscle command model is not supported by the raw counts.

### 9.2 Two-hop descending → VNC intrinsic → motor

| Measure | Value |
|---|---:|
| DN → VNC intrinsic edges | 162,871 |
| VNC intrinsic → MN edges | 132,085 |
| Two-hop paths | 2,370,840 |
| Unique DN→MN pairs | 384,677 |
| DNs reaching an MN | 1,298 |
| MNs reached | 699 |

### 9.3 Motor neurons by effector

| Body part | MNs | With direct DN input | Left | Right | DN edges | DN synapses |
|---|---:|---:|---:|---:|---:|---:|
| abdomen | 168 | 160 | 73 | 95 | 1,250 | 5,314 |
| front_leg | 139 | 139 | 69 | 70 | 3,615 | 30,988 |
| hind_leg | 126 | 124 | 63 | 63 | 2,046 | 23,445 |
| middle_leg | 126 | 124 | 63 | 63 | 2,204 | 21,930 |
| wing | 64 | 64 | 32 | 32 | 2,704 | 17,126 |
| neck | 49 | 49 | 27 | 22 | 3,457 | 42,579 |
| proboscis | 35 | 35 | 17 | 18 | 902 | 5,131 |
| haltere | 27 | 25 | 14 | 13 | 507 | 3,198 |
| pharynx | 22 | 10 | 9 | 13 | 24 | 49 |
| spiracle | 18 | 18 | 9 | 9 | 278 | 1,954 |
| antenna, scape | 8 | 8 | 4 | 4 | 445 | 2,025 |
| crop | 7 | 0 | 4 | 3 | 0 | 0 |
| uterus | 6 | 6 | 3 | 3 | 28 | 60 |
| eye | 4 | 4 | 2 | 2 | 93 | 506 |
| antenna | 2 | 2 | 1 | 1 | 116 | 398 |
| salivary_gland | 2 | 2 | 1 | 1 | 35 | 94 |
| unknown | 2 | 2 | 1 | 1 | 41 | 117 |

The six limb/wing pools relevant to locomotion are all present with balanced
left/right counts and near-complete direct DN input. The crop motor neurons are
the only locomotion-adjacent pool with no direct DN input in this build.

### 9.4 Jump-associated pool

Twenty motor neurons are annotated to the tergotrochanter (jump) muscle:
10 left, 10 right. They receive 350 direct DN edges from 113 DNs, totaling
3,043 synapses. This establishes a structural substrate for a jump experiment.
It does **not** identify a jump command, a trigger DN, or a direction.

### 9.5 Descending super-cluster → leg motor neuron edges

| DN `super_cluster` | Edges to leg MNs |
|---|---:|
| postural control | 3,649 |
| walking | 1,161 |
| probing | 1,018 |
| grooming | 538 |
| walking steering | 473 |
| head orienting | 329 |
| flight steering 1 | 261 |
| reproduction | 159 |
| tactile | 83 |
| threat response | 68 |
| taste-touch | 53 |
| feeding | 27 |
| flight steering 2 | 25 |
| flight power | 19 |
| visceral control | 2 |

These labels are published cluster names, not validated functions of
individual neurons. They are useful for stratifying experiments, not for
asserting that a neuron drives a behavior.

### 9.6 What the graph does and does not support

Supported:
- A separate left and right motor pool for each leg, wing, haltere, neck, and
  abdominal pool.
- Direct and two-hop descending pathways to those pools.
- A jump-associated motor pool with same-side and cross-side candidates.
- Threshold and self-edge sensitivity analyses without touching raw data.

Not supported:
- Assigning a specific game action to a specific DN or pathway.
- Treating synapse count as physiological efficacy.
- Comparing absolute BANC weights to FAFB weights (different volumes,
  thresholds, and identified-pair coverage).
- Any claim that a structural path fires, inhibits, or commands a muscle.

---

## 10. G. Graph construction recommendation

**Recommended policy for Phase 4D.** The same policy is written into the JSON
under `G_graph_construction_policy`.

| Decision | Recommendation |
|---|---|
| Canonical node ID | `banc_888_id` (int64), string on disk |
| Edge endpoints | join `pre`/`post` → `banc_888_id` only |
| Node inclusion | all 172,433 edge endpoints, annotated or not |
| Unannotated graph nodes | 20,573; keep, mark `super_class = unknown` |
| Isolated metadata rows | 16,075 excluded from graph; retained in annotation table |
| Edge aggregation | none — already one row per directed pair |
| Self-edges | exclude from the built graph; raw file unchanged |
| Edge weight | integer `count` |
| Primary threshold | `count ≥ 5` (FAFB-comparable) |
| Sensitivity thresholds | 1, 5, 10 |
| `norm` | never used as weight; never summed |
| Annotation join | left join; missing stays unknown |
| Proofread fields | `proofread`, `roughly_proofread`, `status` |
| Sign prior | verified neurotransmitter only (motor 30, descending 155) |
| Predicted transmitter | descriptive only; not a sign or weight |
| CSR construction | sort by `(pre, post)` before building |
| Output metadata | record all input SHA-256, row/column counts, threshold, self-edge policy |
| Dataset separation | BANC graph is independent; no FAFB merge |

Additional recommendations:
- Exclude non-neuronal classes (`glia`, `trachea`, `not_a_neuron`) from
  neuron-level analyses, but keep them in the raw node table. They account for
  3,636 self-loops and a small fraction of edges.
- Mark every node with `proofread`, `roughly_proofread`, and population flags
  so downstream experiments can restrict to high-confidence subsets.
- Keep `root_888` as a secondary column for cross-checking; do not key on it.
- Do not download the 16–20 GB enriched synapse parquets for Phase 4D. The
  simple edgelist is sufficient and far cheaper.
- Consider a later v3 comparison only as a separate sensitivity graph, never as
  a silent replacement: v3 has 13,507,098 pairs, uses size ≥ 10, and is the
  newer detection model, while the BANC paper's quantitative figures use v2.

---

## 11. Reproducibility

Run:

```bash
python experiments/phase_4c/audit_banc_graph.py
python experiments/phase_4c/audit_banc_graph.py --output reports/other.json
```

The script:
- reads the five inputs read-only and records byte size and SHA-256;
- records row/column counts and the edgelist schema;
- computes every block deterministically (sorted unique IDs, no sampling);
- writes JSON with `allow_nan=False`;
- prints the verdict, canonical key, node count, pair count, self-edge count,
  and DN→MN edge count.

Determinism was checked by running the audit twice and comparing full payloads
with only `generated_utc` and `duration_seconds` removed: **equal (True)**.

Raw data were not modified. The JSON and script are separate artifacts; the
edgelist and metadata files were only opened for reading.

---

## 12. Tests

| Suite | Command | Result |
|---|---|---|
| Phase 4C.5 focused | `python -m pytest tests/test_banc_graph_audit.py -q` | **11 passed** in 1.03 s |
| Full repository | `python -m pytest -q` | **311 passed** in 16.41 s |

The 11 focused tests cover:
1. canonical ID selection among six candidate columns;
2. duplicate primary-key detection;
3. self-edge row/synapse counting and super-class breakdown;
4. clean edge integrity;
5. duplicate-pair and missing-endpoint failure;
6. exact weight identity;
7. broken total detection;
8. missing annotation treated as unknown;
9. locomotor direct, two-hop, jump, and per-body-part counting;
10. policy values derived from measured audit values;
11. NumPy JSON serialization.

No test writes to `datasets/`.

---

## 13. Unresolved scientific and data-integrity concerns

1. **Stale metadata dictionary.** Published docs describe 188,162 rows and 79
   columns (51,450,978 bytes). Local/current object has 188,508 rows and 81
   columns (57,503,026 bytes). The extra build is the one currently served.
2. **Incorrect key statement in the dictionary.** The dictionary says
   `root_id` = `banc_888_id`. The data show 168 duplicate `root_id` rows and
   16,319 mismatches. Use `banc_888_id`.
3. **Autapse statement contradicted.** The v2 dictionary says autapses are
   excluded and lists 11,510,975 rows. The current object has 11,752,828 rows
   and 156,311 self-loops. Documentation predates the served object.
4. **Mislabelled file extension.** `banc_fafb_reviewed_matches.csv.gz` is plain
   CSV. Any gzip-inferring reader fails; read with `compression=None`.
5. **Effector neurotransmitter predictions are not usable as output signs.**
   Only 30 of 805 motor neurons have verified transmitters; the predictions are
   dominated by input chemistry.
6. **Partial connectivity.** Both-partners-identified links are roughly one
   fifth of all BANC synaptic links. Degrees, absolute weights, and fractions
   are relative to this subset, not the whole connectome.
7. **Self-loops are not individually adjudicated.** The policy excludes them
   from the graph, but some may be real autapses. This affects about 4% of
   summed synapses and 90.7% of nodes by at least one loop.
8. **No physiology.** Structural adjacency does not imply excitation,
   inhibition, sign, delay, or a behavioral command. The game mapping remains a
   hypothesis.
9. **Side imbalance is descriptive.** For example, abdominal MNs are 73 left /
   95 right. This audit does not test whether that asymmetry is biological,
   annotation-related, or sampling-related.
10. **Only 4 VNC-intrinsic neurons have an FAFB match**, and the FAFB artifact
    has no limb motor neurons. Cross-dataset comparison cannot validate limb
    circuits; BANC must stand alone for locomotion.
11. **`valid_id` in the backbone table is not a neuron key.** Only 79,080 of its
    values are metadata keys. Use `pt_root_id`.
12. **VNC-intrinsic `status` is missing for 9,553 rows.** Missing status is not
    evidence of low quality; the proofread flags are the usable quality signal.

---

## 14. Recommended next milestone

**Phase 4D — BANC graph loader (separate graph), contingent on accepting the
Section 10 policy.**

Suggested acceptance criteria:
1. Build a CSR graph keyed on `banc_888_id` with all 172,433 endpoints.
2. Exclude self-edges; verify the filtered edge count equals
   `11,752,828 − 156,311 = 11,596,517` before thresholding.
3. Apply `count ≥ 5` as primary, with 1 and 10 as sensitivity variants.
4. Attach annotations by left join; missing stays `unknown`.
5. Expose population masks for motor, descending, ascending, VNC intrinsic,
   and the six limb/wing pools.
6. Emit a manifest with input SHA-256 values, thresholds, self-edge policy, and
   node/edge counts.
7. Verify that the BANC graph shares no edge or node index with the FAFB graph.
8. Add regression tests for counts, determinism, and separation from FAFB.
9. Run no plasticity and no physiological calibration in Phase 4D.

Do not begin Phase 4D until this verdict and the Section 10 policy are
accepted. The jump, left/right, and body-part experiments should be designed
only after the loader exists, and they must be framed as
structural-candidate experiments, not identified motor commands.

---

## 15. Sources

1. Bates, A. S. et al. "Distributed control circuits across a brain-and-cord
   connectome." *Nature* 656, 957–970 (2026). DOI
   `10.1038/s41586-026-10735-w`.
2. BANC data dictionaries:
   `documentation/banc_888_meta.md`,
   `documentation/banc_888_edgelist_simple_v2.md`,
   `documentation/banc_888_edgelist_simple_v3.md`,
   `documentation/banc_fafb_reviewed_matches.md`,
   `documentation/backbone_proofread.md`.
3. Public bucket:
   `gs://lee-lab_brain-and-nerve-cord-fly-connectome/`.
4. Local artifacts: `datasets/external/banc_v88/raw/` (five files above).
5. Prior phases: `reports/PHASE_4A_RESOURCE_COMPATIBILITY_AUDIT.md`,
   `reports/PHASE_4B_LOCOMOTOR_MOTOR_PATHWAY_INVESTIGATION.md`.
6. Local implementation interfaces: `brain/subgraph.py`,
   `brain/connectome_loader.py`, `brain/brain_simulator.py`.
