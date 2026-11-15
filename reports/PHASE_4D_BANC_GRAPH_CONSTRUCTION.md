# Phase 4D — BANC v888 Graph Construction

**Phase:** 4D
**Status:** Complete
**Verdict:** **PASS WITH LIMITATIONS**
**Canonical node identifier:** `banc_888_id`
**Loader / builder:** `brain/banc_graph.py`
**Focused tests:** `tests/test_banc_graph_loader.py`
**Output directory:** `datasets/processed/banc_v888/`
**Machine-readable report:** `datasets/processed/banc_v888/banc_construction_report.json`
**Manifest:** `datasets/processed/banc_v888/banc_manifest.json`

This phase turns the audited BANC v888 export into an independent,
reproducible structural graph. It does not replace, modify or merge with the
FAFB FlyWire graph, does not change the neural simulator, and does not infer
physiological function from connectivity.

---

## 1. Executive verdict

**PASS WITH LIMITATIONS.**

All required construction, validation and reproducibility checks passed. The
three threshold graphs are built from a single edge load, contain every
172,433 endpoint ID of the source edgelist, exclude self-edges by an explicit
simulation policy while leaving the source untouched, preserve all isolated
nodes, use integer synapse `count` as the weight, and verify byte-for-byte
against a manifest. All five source hashes match the Phase 4C.5 audit and the
FAFB artifacts and root README are unchanged.

The limitations are scientific rather than mechanical: BANC is a different
specimen from FAFB, the graph is only the exported v2 subset, edge weight is
synapse count and not conductance, adjacency does not establish excitation,
inhibition or a motor command, and the tergotrochanter candidates are
annotation-defined rather than functionally validated jump commands.

---

## 2. Scope and inputs

Work was confined to the main `FLY-SURFER` repository. The five BANC inputs
were read once and were not modified. Their SHA-256 values are identical to
the Phase 4C.5 audit.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `datasets/external/banc_v88/raw/metadata/banc_888_meta.feather` | 57,503,026 | `86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098` |
| `datasets/external/banc_v88/raw/connectivity/banc_888_edgelist_simple_v2.feather` | 305,250,378 | `363fdef3813b72a5e45a42f17034cd5a544b654c838929cecf6e1ce5f60625cb` |
| `datasets/external/banc_v88/raw/annotations/backbone_proofread.parquet` | 10,316,976 | `9b553956c11558b9d5c7c9d3e66cea8af08f358ee897ab6e0e8ce91faa5c9a2d` |
| `datasets/external/banc_v88/raw/annotations/banc_888_neurotransmitter_prediction_v2.csv` | 21,107,592 | `bb0f4afa48a05d90008c6d801e053ff2667fb1ba68e29501c92f49514540da1d` |
| `datasets/external/banc_v88/raw/cross_dataset_matches/banc_fafb_reviewed_matches.csv.gz` | 6,581,434 | `ecdbb43cd5d4586e92f0d92a6f1d2beeecd2f429dd5b3e5309c0edc2daa515c4` |

**Dataset identity.** BANC materialization v888 (April 16, 2026 snapshot),
v2 synapse model rolled up at postsynapse size ≥ 5. The edgelist is a subset:
only pairs whose pre- and post-partner were both identified are exported.

**Separation from FAFB.** No BANC node, edge or CSR index is shared with the
FAFB graph. The loader writes only under `datasets/processed/banc_v888/`. The
pre/post snapshots show `README.md`, `datasets/manifest.json`,
`datasets/processed/connectome.npz`, `datasets/processed/connectome_report.json`
and `datasets/processed/nodes.csv.gz` unchanged. A test also asserts that the
BANC and FAFB node sets are disjoint.

---

## 3. Implementation summary

`brain/banc_graph.py` implements the complete pipeline and a CLI
(`python -m brain.banc_graph`). The CLI accepts `--out-dir`, `--metadata`,
`--edgelist`, `--thresholds` and `--no-verify`.

Pipeline stages:

1. **Load once.** Metadata is read with the canonical ID, the retained
   annotation columns and `root_position_nm`; the edgelist is read with
   `pre`, `post`, `count`, `norm`, `post_count`, `pre_count`.
2. **Validate canonical IDs.** `validate_canonical_ids` rejects nulls, empty
   strings, duplicates and non-integer-representable values. The on-disk
   representation is an 18-digit decimal string; conversion is exact int64.
3. **Resolve node population.** `resolve_node_ids` takes every unique endpoint
   from the edgelist (not every metadata row) and fails if any endpoint is
   absent from metadata. The 16,075 metadata rows with no edge endpoint are
   excluded and reported.
4. **Prepare edges once.** `prepare_edges` maps IDs to dense int32 indices,
   records self-edge rows/synapses, sorts by the 64-bit `(pre, post)` key,
   fails on duplicate pairs, removes self-edges, and asserts strict
   lexicographic ordering.
5. **Build threshold graphs.** `build_threshold_graph` filters by
   `count >= threshold`, builds forward and reverse CSR, uses a stable argsort
   for `in_edge_idx`, retains every node (including zero-degree nodes), and
   verifies the artifact.
6. **Build node and ID tables.** `build_node_table` left-joins annotations by
   `banc_888_id`, keeps missing values unknown, and adds population flags.
   `banc_id_map.csv.gz` records the canonical ID ↔ CSR-index mapping.
7. **Manifest and report.** The manifest records dataset version, source
   paths and SHA-256, timestamp, canonical ID field, node count, original edge
   count, excluded self-edge count and synapse sum, retained counts for all
   thresholds, weight policy, software versions, configuration and the
   deterministic ordering policy.
8. **Verify.** `verify_graph` re-derives degrees and checks self-loops,
   thresholds, positive weights, CSR consistency and isolated-node counts.
   `verify_manifest` recomputes every input and output hash.

**Node ordering.** `node_index` is the 0-based position in ascending numeric
`banc_888_id` order over the unique endpoints of the edgelist. IDs are stored
as decimal strings in the CSV outputs and as exact int64 inside the artifact.

**Edge ordering.** Edges are sorted by `(pre_index, post_index)` before CSR
construction; `in_edge_idx` comes from a stable argsort of `post_index`.

**Weight policy.** Weight is the integer `count` field (summed synapses for
that pair). `norm` is never used as a weight, because it is
`count / post_count` and is not a physiological quantity.

**Self-edge policy.** `pre == post` rows are excluded from every graph and
retained in the raw source. This is a simulation policy, not a source
deletion. The excluded count and synapse sum are recorded in the manifest and
report.

---

## 4. Graph sizes

Every threshold graph contains all 172,433 endpoint nodes, including nodes
that become isolated after self-edge removal or thresholding.

| Threshold | Edges | Synapses | Weight min | Weight max | Isolated nodes | Pair share* | Synapse share* |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11,596,517 | 34,310,230 | 1 | 913 | 6,232 | 100.00% | 100.00% |
| 5 (primary) | 1,535,710 | 18,552,546 | 5 | 913 | 24,320 | 13.24% | 54.07% |
| 10 | 570,721 | 12,397,230 | 10 | 913 | 62,551 | 4.92% | 36.13% |

\* Share of the 11,596,517 non-self pairs and 34,310,230 non-self synapses.

Reference counts:

- Metadata rows: 188,508
- Endpoint nodes: 172,433
- Metadata-only rows excluded from the graph: 16,075
- Original edge rows: 11,752,828
- Excluded self-edges: 156,311 (1,422,866 synapses)
- Non-self edges: 11,596,517 (34,310,230 synapses)

Mean weight at thresholds 1/5/10 is 2.96 / 12.08 / 21.72. Mean out-degree is
67.25 / 8.91 / 3.31; max out-degree is 6,668 / 2,829 / 906.

---

## 5. Validation

### 5.1 Canonical IDs

| Check | Result |
|---|---|
| Rows | 188,508 |
| Nulls | 0 |
| Empty strings | 0 |
| Duplicate IDs | 0 |
| Unique IDs | 188,508 |
| ID range | 148,338,207,556,158,635 – 720,575,941,734,598,699 |
| Endpoint coverage | Every `pre`/`post` endpoint exists in metadata |

### 5.2 Edges

| Check | Result |
|---|---|
| Null values in the six source columns | 0 |
| Non-positive counts / norms / partner totals | 0 |
| Duplicate `(pre, post)` pairs | 0 |
| Self-edges | 156,311 rows / 1,422,866 synapses, excluded from graphs |
| Endpoints outside canonical set | 0 |
| Deterministic edge ordering | Strict lexicographic `(pre, post)` |

### 5.3 CSR artifacts

All of the following passed for thresholds 1, 5 and 10:

- node count equals the manifest node count;
- edge count and synapse sum equal the reported totals;
- no self-loops;
- every weight is positive and at least the threshold;
- forward CSR degrees match `diff(out_indptr)`;
- reverse CSR degrees match `diff(in_indptr)`;
- `in_edge_idx` yields non-decreasing destination order;
- `root_ids` are strictly ascending;
- isolated-node count matches the report.

### 5.4 Manifest and isolation

- `verify_manifest` recomputed 10 input/output hashes: **pass**, 0 failures.
- Phase 4C.5 audit cross-check (5 input hashes and 4 count checks): **pass**.
- FAFB isolation snapshot (README, FAFB manifest and three FAFB artifacts):
  **unchanged**, 0 failures.

---

## 6. Annotation coverage

Annotations are left-joined on `banc_888_id`. Missing values remain unknown
and are never inferred.

| Field | Present | Missing | Present share |
|---|---:|---:|---:|
| `super_class` | 151,860 | 20,573 | 88.07% |
| `cell_type` | 117,607 | 54,826 | 68.20% |
| `side` | 158,195 | 14,238 | 91.74% |
| `body_part_effector` | 1,029 | 171,404 | 0.60% |
| `proofread` | 172,433 | 0 | 100.00% |
| `root_position_nm` (position) | 154,064 | 18,369 | 89.35% |

The node table contains 30 columns: identity and index, 21 annotation fields,
seven population flags, and position is stored in the graph artifact with an
explicit `position_mask` rather than in the CSV.

Predicted and verified neurotransmitter columns are both retained as separate
fields. Verified neurotransmitter is metadata that may be used as a sign
prior; it is not a validated synaptic effect. No sign is applied to any edge
in this phase.

---

## 7. Population counts

Counts are recomputed from the built node table, never hard-coded. "Graph"
counts use only exported endpoints.

| Population | Metadata rows | Graph nodes | Delta | Audit expectation* |
|---|---:|---:|---:|---|
| Motor (`super_class == 'motor'`) | 805 | 805 | 0 | 805 |
| Descending (`super_class == 'descending'`) | 1,316 | 1,316 | 0 | 1,316 |
| Ascending (`super_class == 'ascending'`) | 1,849 | 1,849 | 0 | 1,849 |
| VNC intrinsic (`super_class == 'ventral_nerve_cord_intrinsic'`) | 12,866 | 12,850 | −16 | 12,866 |
| VNC region (`region == 'ventral_nerve_cord'`) | 31,688 | 27,778 | −3,910 | — |
| Tergotrochanter motor candidates | 20 | 20 | 0 | — |
| Left motor (`motor` and `side == 'left'`) | — | 392 | — | — |
| Right motor (`motor` and `side == 'right'`) | — | 413 | — | — |

\* Phase 4C.5 expectations, where stated.

Motor neurons grouped by `body_part_effector`:

| Effector | Motor neurons | Left | Right |
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
| **Total** | **805** | **392** | **413** |

Tergotrochanter candidates are defined as `super_class == 'motor'` and
`peripheral_target_type == 'tergotrochanter_extensor_muscle'`. They are
annotation-defined candidates, not functionally validated jump commands.

---

## 8. Output checksums

| Output | Bytes | SHA-256 |
|---|---:|---|
| `banc_graph_t1.npz` | 79,829,070 | `fee8e5e7f7dbd9b6d43ef125695b1b11f6c9613088c8c04dd0d883ff12ecc01e` |
| `banc_graph_t5.npz` | 13,484,120 | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| `banc_graph_t10.npz` | 6,699,534 | `00b3f447e2755660c273a63e11bc60a8afd8247906bbe0576f3a27a6ee1dc7a0` |
| `banc_nodes.csv.gz` | 3,800,401 | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| `banc_id_map.csv.gz` | 1,098,539 | `ede93fa7f33f34d0b77b800a8714b401e6f8ab7dbac44e4ce882518231dbbb16` |

`banc_manifest.json` and `banc_construction_report.json` are generated
alongside these five artifacts.

---

## 9. Runtime and memory

| Stage | Seconds |
|---|---:|
| Load metadata and edgelist | 2.06 |
| Construct all three graphs | 19.49 |
| Write artifacts and tables | 26.62 |
| **Total** | **48.75** |

Peak resident memory: **1,710.8 MB**. The edgelist is loaded once and all
thresholds are derived from one prepared representation.

Software: Python 3.13.14, NumPy 2.3.4, pandas 2.3.3, PyArrow 21.0.0,
Windows 11 (10.0.26200).

Reproduce with:

```bash
python -m brain.banc_graph
```

---

## 10. Tests

Focused suite:

```text
python -m pytest tests/test_banc_graph_loader.py -q
20 passed in 3.36s
```

The 20 tests cover canonical-ID uniqueness and round trips, missing
endpoints, duplicate-pair rejection, self-edge exclusion, the three
thresholds, structural weights, CSR directionality and degrees, isolated-node
retention, left-join and metadata-only exclusion, missing annotations staying
unknown, positions staying masked when absent, population queries,
determinism, artifact round trips, manifest tamper detection, FAFB isolation,
disjoint BANC/FAFB node sets, and built artifacts matching the manifest.

Full suite:

```text
python -m pytest -q
331 passed in 46.80s
```

The existing 311 tests were preserved; 20 Phase 4D tests were added.

---

## 11. Limitations

1. BANC is a different specimen from FAFB. The two graphs are not merged and
   no cross-dataset edge exists.
2. The graph contains only the exported v2 pairs for which both partners were
   identified. It is not a whole-connectome graph, and 16,075 metadata rows
   are not graph nodes.
3. Edge weight is synapse `count`, not conductance, release probability or
   effective current.
4. Structural adjacency does not establish excitation, inhibition, a
   command role, or a behavior.
5. Self-edges are excluded by simulation policy; the source file retains them.
6. Missing annotations remain unknown and are never inferred.
7. Positions are available for 89.35% of nodes; the rest stay masked.
8. Tergotrochanter candidates are annotation-defined, not functionally
   validated jump commands.
9. No Subway Surfers action is biologically identified with any BANC
   population in this phase.

---

## 12. Discrepancies

- **VNC intrinsic −16 (12,850 graph vs 12,866 audit).** Sixteen metadata rows
  with that label have no endpoint in the exported edgelist and therefore are
  not graph nodes.
- **VNC region −3,910 (27,778 graph vs 31,688 metadata).** The 16,075
  metadata-only rows are concentrated partly in the VNC region; graph counts
  intentionally include endpoints only.
- All audited populations with an explicit Phase 4C.5 expectation (motor,
  descending, ascending, VNC intrinsic) otherwise match their metadata and
  audit counts. No count was hard-coded in the builder.

---

## 13. Verdict

**PASS WITH LIMITATIONS.**

The loader and artifacts satisfy every structural, reproducibility and
isolation requirement of Phase 4D. The limitations above are properties of the
source data and of the deliberate structural-only scope, not construction
defects. Phase 4E was not started, the neural simulator was not modified, and
nothing was staged, committed or pushed.
