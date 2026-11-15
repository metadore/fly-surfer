# Phase 4A — Resource Compatibility Audit

**Audit date:** 2026-11-07
**Scope:** Read-only inspection of the local connectome and annotation resources,
the current FlyWire annotation release, the BANC paper, and the two Male CNS
papers. No training, graph merging or plasticity was performed.
**Verdict:** **PARTIALLY COMPATIBLE**

The local FAFB v783 resources can support descending-neuron and head/neck motor
annotation work, and they contain a usable descending-to-motor interface inside
the brain. They cannot supply a complete brain-to-limb motor pathway, because
FAFB is a brain-only, adult-female dataset and contains no leg, wing, haltere or
abdominal motor neurons. BANC and Male CNS are available as external comparative
references with explicit FAFB match tables, but they are different specimens in
different image spaces and their root IDs cannot be merged into the local
connectome.

---

## 1. Scope, constraints and method

This audit answers one question:

> Can the existing FLY-SURFER resources support a Phase 4 that selects
> descending, premotor and motor neurons from the current annotations and, in a
> later approved phase, relates them to the existing simulation — without
> merging graphs, training a model or introducing plasticity?

The audit was read-only. The following were inspected but not modified:

- `datasets/processed/connectome.npz` and `datasets/processed/nodes.csv.gz`
- `datasets/raw/annotations/*.csv.gz` and the other raw tables
- `references/source_repositories/flywire_annotations/...`
- `references/papers/BANC/BANC-connectome.pdf`
- `references/connectomes/male_cns/Cell Press_20261106/*.pdf`
- the protected root `README.md`

No file under `datasets/`, `references/` or `models/` was written. The only
repository change is this report. No package was installed, no model was loaded,
and nothing was staged, committed or pushed.

Connectivity statements below are derived from the local thresholded graph:
directed edge, weight = summed synapse count across neuropils, threshold
`>= 5` synapses. "Monosynaptic" therefore means "a direct edge in that graph",
not a proofread synaptic contact and not a functional connection.

---

## 2. Local resource inventory and schemas

### 2.1 Connectome artifact

`datasets/processed/connectome.npz` (28,013,212 bytes; SHA-256
`3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`) is a
sparse CSR artifact, not a dense adjacency matrix.

| Property | Value |
|---|---|
| Neurons (nodes) | 139,255 |
| Directed edges | 3,732,460 |
| Summed synapses after threshold | 50,666,648 |
| Edge threshold | `>= 5` synapses, summed across neuropils |
| Isolated nodes | 671 |
| Self-connections | 0 |
| Node index rule | 0-based position in ascending `root_id` order |
| Positions | 139,255 rows; `position_mask` all true |
| Arrays | `root_ids`, `out_indptr`, `edge_src`, `edge_dst`, `edge_weight`, `in_indptr`, `in_edge_idx`, `positions`, `position_mask`, `nt_code`, `super_class_code`, `class_code`, `side_code`, `flow_code` |
| Source tables | `datasets/raw/connections/connections_princeton.csv.gz`, `datasets/raw/neurons/neurons.csv.gz` |
| Generated | 2026-11-04T08:39:26Z |

Provenance is explicitly qualified. `datasets/manifest.json` records:

- `inferred_version`: `v783`
- `version_evidence`: `fafb_v783_princeton_synapse_table.csv`
- `version_confidence`: "inferred from an incomplete download filename; not
  attested by the completed files"
- `scope`: "brain only (FAFB); no complete ventral nerve cord, so BANC or Male
  CNS is required for a complete brain-to-motor pathway"

That last line is the central compatibility constraint of this audit.

### 2.2 Local node table

`datasets/processed/nodes.csv.gz` has 139,255 rows and 30 columns:
`node_index`, `root_id`, `name`, `group`, `nt_type`, `nt_type_score`,
`da_avg`, `ser_avg`, `gaba_avg`, `glut_avg`, `ach_avg`, `oct_avg`, `flow`,
`super_class`, `class`, `sub_class`, `hemilineage`, `side`, `nerve`,
`primary_type`, `additional_types`, `length_nm`, `area_nm`, `size_nm`,
`connectivity_tag`, `label_count`, `labels`, `x`, `y`, `z`.

### 2.3 Local v783 classification

`datasets/raw/annotations/classification.csv.gz` has 139,255 rows and exactly
the same root-ID set as the connectome (0 IDs on either side of the comparison).
It carries eight coarse columns: `root_id`, `flow`, `super_class`, `class`,
`sub_class`, `hemilineage`, `side`, `nerve`. The gzip header modification time
is 2026-02-24, which places this bundle earlier than the current annotation
release.

Local coarse counts:

| `super_class` | Count |
|---|---:|
| optic | 77,873 |
| central | 32,381 |
| sensory | 16,938 |
| visual_projection | 7,684 |
| ascending | 1,750 |
| **descending** | **1,305** |
| sensory_ascending | 612 |
| visual_centrifugal | 522 |
| **motor** | **110** |
| endocrine | 80 |

### 2.4 Current FlyWire annotation snapshot

`references/source_repositories/flywire_annotations/flywire_annotations-main/flywire_annotations-main/supplemental_files/Supplemental_file1_neuron_annotations.tsv`
has 139,248 unique root IDs and 31 columns:

`supervoxel_id`, `root_id`, `pos_x`, `pos_y`, `pos_z`, `soma_x`, `soma_y`,
`soma_z`, `nucleus_id`, `flow`, `super_class`, `cell_class`,
`cell_sub_class`, `supertype`, `cell_type`, `hemibrain_type`,
`ito_lee_hemilineage`, `hartenstein_hemilineage`, `top_nt`, `top_nt_conf`,
`known_nt`, `known_nt_source`, `side`, `nerve`, `vfb_id`, `fbbt_id`, `status`,
`dimorphism`, `matching_notes`, `fru_dsx`, `synonyms`.

Current annotation counts:

| `flow` | Count |
|---|---:|
| intrinsic | 118,497 |
| afferent | 19,262 |
| efferent | 1,489 |

| `super_class` | Count |
|---|---:|
| optic | 77,541 |
| central | 32,383 |
| sensory | 16,907 |
| visual_projection | 8,038 |
| ascending | 1,750 |
| **descending** | **1,303** |
| sensory_ascending | 612 |
| visual_centrifugal | 524 |
| **motor** | **110** |
| endocrine | 80 |

The companion non-neuron table
`Supplemental_file2_non_neuron_annotations.tsv` has 841 rows. It contains none
of the 14 or 7 discrepant IDs discussed in section 3.

---

## 3. ID reconciliation: the 14 and the 7

### 3.1 Method

Exact set comparison of `root_id` between:

- local connectome nodes: 139,255 unique IDs
- current FlyWire annotation dump: 139,248 unique IDs

Result:

| Quantity | Count |
|---|---:|
| Local connectome IDs | 139,255 |
| Current annotation IDs | 139,248 |
| Intersection | 139,241 |
| Connectome-only | **14** |
| Annotation-only | **7** |
| Union | 139,262 |

The local `classification.csv.gz` matches the connectome exactly, so the
discrepancy is **not** an artifact of the local connectome build. It is a
difference between the local v783 bundle (early 2026) and the newer annotation
release (3.x).

### 3.2 The 14 connectome-only IDs

These roots have connectivity and positions locally but no row in the current
annotation dump.

| root_id | Local super_class | Local class / sub_class | Local primary_type | Local name | Note |
|---|---|---|---|---|---|
| 720575940606792881 | sensory | visual / photo_receptor | R1-6 | NO_CONS.3454 | label: "Not an r cell. Glia.; Retinula axon; R1-6" |
| 720575940607862706 | optic | optic_lobe_intrinsic / transmedullary | Tm36 | LO.4965 | |
| 720575940613336473 | optic | optic_lobe_intrinsic / distal_medulla | Dm15 | ME.43630 | |
| 720575940613437206 | optic | — | — | LO.5417 | unclassified optic |
| 720575940619169349 | optic | optic_lobe_intrinsic / transmedullary | Tm36 | LO.5671 | |
| 720575940623450077 | optic | — | — | NO_CONS.3556 | unclassified optic |
| 720575940623913933 | optic | — | — | LO.5670 | unclassified optic |
| 720575940625523749 | optic | — | — | NO_CONS.1608 | label: "Not a neuron" |
| 720575940626741265 | sensory | mechanosensory / auditory | JO-B | AMMC.344 | |
| 720575940628159081 | sensory | mechanosensory / auditory | JO-B | AMMC.129 | |
| 720575940633242449 | central | CX / tangential | FB4Z | FB.601 | |
| 720575940636488667 | sensory | mechanosensory / auditory | JO-B | NO_CONS.2692 | |
| 720575940639387763 | optic | — | — | LOP.2545 | label: "Glia, putative Astrocyte" |
| 720575940642560987 | optic | optic_lobe_intrinsic / lamina_monopolar | L5 | ME.44275 | |

Category summary:

- 3 are labelled non-neuronal or glia-like (R1-6 glia label, "Not a neuron",
  putative astrocyte), which plausibly explains their removal from a
  neuron-annotation dump.
- 7 are optic intrinsic or unclassified optic objects.
- 3 are JO-B auditory sensory neurons.
- 1 is a central FB4Z tangential neuron.
- **None is a descending or motor neuron.**

### 3.3 The 7 annotation-only IDs

These roots exist in the current annotation dump, with supervoxel IDs and cell
types, but have no row in the local v783 connectivity table.

| root_id | super_class | cell_class | cell_type | flow | side | nerve |
|---|---|---|---|---|---|---|
| 720575940616847814 | optic | LA>ME | L2 | intrinsic | left | — |
| 720575940618455453 | optic | ME | Mi9 | intrinsic | right | — |
| 720575940622062913 | optic | LA>ME | L2 | intrinsic | left | — |
| 720575940624154153 | optic | ME.LO | — | intrinsic | left | — |
| 720575940626850833 | sensory | optic_lobes | HBeyelet | intrinsic | right | — |
| 720575940628215433 | sensory | olfactory | ORN_DM4 | afferent | left | AN |
| 720575940637590670 | sensory | optic_lobes | HBeyelet | intrinsic | right | — |

Category summary:

- 4 optic intrinsic objects (L2 x2, Mi9, one ME.LO object).
- 3 sensory objects (2 HBeyelet, 1 ORN_DM4).
- **None is a descending or motor neuron.**

### 3.4 Consequences for any join

1. A root-ID join must be an **inner join** (139,241 rows). An outer join would
   create 14 unannotated simulated nodes and 7 annotated but unsimulatable
   rows.
2. The 7 annotation-only roots cannot be placed in the local connectome, have
   no local edges and no local position. They must be dropped from any
   simulated population and recorded as dropped.
3. The 14 connectome-only roots remain valid simulated nodes. At least 3 are
   non-neuronal or glia-like; the rest are optic/sensory/central objects. If a
   future phase requires a neuronal-only population, they should be filtered
   explicitly rather than silently retained.
4. The descending and motor candidate sets are unaffected: all 1,303 current
   descending neurons and all 110 current motor neurons are present in the
   local connectome.

---

## 4. Annotation version and provenance

### 4.1 What the snapshot says

The snapshot README states that the repository contains annotations for the
`783` public release of the FlyWire female adult brain connectome. Its
changelog top entry is `3.2.0` (gustatory receptor neuron retyping following
Tastekin et al., Cell 2026). The schema contains `dimorphism`,
`matching_notes`, `fru_dsx`, `synonyms` and `supertype`, which were introduced
in `3.0.0` when the annotations were cross-validated against the Janelia Male
CNS connectome. The snapshot therefore corresponds to the 3.x series, with
`3.2.0` as the latest changelog entry.

### 4.2 What cannot be attested

The local snapshot has **no `.git` directory**, so the exact release tag cannot
be verified locally. The nested repository path is a copied source snapshot.
The changelog, schema and file contents are consistent with `3.2.0`, but that
is an inference, not a signed tag.

Recorded hashes:

| File | SHA-256 |
|---|---|
| `Supplemental_file1_neuron_annotations.tsv` | `b214970b55d2fbe0853bba536fdcb9e28730f4eb7ab06f600491df795da683cd` |
| `Supplemental_file2_non_neuron_annotations.tsv` | `2349fd5b4b9e53fd1b4a84aa73230bb7bebe66faa5d6a7490155aa2128861de1` |
| snapshot `README.md` | `bf9cb228d4520641f96b82e299673846d73404fb69970f39d1b387eec25dbf87` |

### 4.3 Label drift is larger than ID drift

Among the 139,241 common roots, the local v783 coarse `super_class` and the
current annotation `super_class` disagree for **586 neurons (0.42%)**:

| Local -> current | Count |
|---|---:|
| optic -> visual_projection | 389 |
| sensory -> optic | 93 |
| optic -> sensory | 63 |
| visual_projection -> optic | 35 |
| optic -> visual_centrifugal | 3 |
| descending -> central | 2 |
| visual_centrifugal -> central | 1 |

The descending set changes from 1,305 local to 1,303 current. Exactly two local
descending neurons are reclassified as central/intrinsic:

- `720575940613007729` (`DNg36_a`), now `central`, flow `intrinsic`
- `720575940631271235` (`DNge102`), now `central`, flow `intrinsic`

There are no current-only descending neurons. Side and nerve agree for all
1,303 shared descending neurons. The motor set is identical at 110.

A name-based selection is unreliable: 1,327 neurons carry `DN`, `oviDN` or
`MDN` names, but only 1,301 of them are in `super_class=descending`; 20 are
`central` (including the two reclassified above and several `DN1a`/`DN1pA`
types) and 6 are `sensory` (`DNx02`, afferent, nerve `ON`). Conversely, two
descending neurons carry `aSP` names that match none of those prefixes.
Candidate selection should use `super_class=descending`, not a name prefix.

---

## 5. Candidate descending, premotor and motor annotations

All counts in this section are from the current annotation dump, joined to the
local thresholded connectome. Every current descending and motor root is
present locally, so the join is complete for these two classes.

### 5.1 Descending neurons

| Property | Value |
|---|---:|
| Annotated descending neurons | 1,303 |
| Present in local connectome | 1,303 |
| Nerve | all `CV` |
| Side | 649 right, 646 left, 8 center |
| With a `cell_type` | 1,303 |
| With a predicted `top_nt` | 1,290 |
| With a non-empty `known_nt` | 259 (includes negative calls) |

Predicted transmitter (`top_nt`): acetylcholine 873, glutamate 182, GABA 148,
serotonin 65, dopamine 12, octopamine 10, blank 13.

Cell-type prefixes: `DNg` 845, `DNp` 326, `DNa` 52, `DNb` 41, `DNd` 22,
`oviDN` 6, `MDN` 4, `DNc` 4, `aSP` 2, `DNx` 1.

The transmitter values are predictions, not measured physiology. `known_nt`
coverage is partial and includes explicit negative statements (for example
"gaba-negative"), so it cannot be treated as a complete measured transmitter
table.

### 5.2 Motor neurons

| Property | Value |
|---|---:|
| Annotated motor neurons | 110 |
| Present in local connectome | 110 |
| `cell_class = brain_motor_neuron` | 105 |
| `cell_class = neck_motor_neuron` | 1 |
| `cell_class` blank | 4 |
| With a `cell_type` | 110 |
| With a predicted `top_nt` | 110 |
| With a non-empty `known_nt` | 0 |

Motor subclasses:

| `cell_sub_class` | Count |
|---|---:|
| ingestion_motor_neuron | 28 |
| neck_motor_neuron | 26 |
| proboscis_motor_neuron | 24 |
| antennal_motor_neuron | 10 |
| crop_motor_neuron | 8 |
| eye_motor_neuron | 4 |
| haustellum_motor_neuron | 4 |
| salivary_motor_neuron | 2 |
| blank | 4 |

Nerves: `PhN` 40, `MxLbN` 26, `CV` 20, `AN` 14, `ON` 10.

Predicted transmitter: acetylcholine 81, glutamate 14, serotonin 9, octopamine 3,
GABA 3.

The four blank-class neurons are all `cell_type = CB2748`, `flow = intrinsic`,
`nerve = ON`, with no `cell_sub_class`. They are anomalous in a motor class and
should be flagged or excluded from a motor output set until resolved.

**Critical coverage limit:** the 110 motor neurons are head, neck, crop,
proboscis, antennal, eye, salivary and haustellum motor neurons. There are **no
leg, wing, haltere or abdominal motor neurons** in FAFB. This is expected for a
brain-only dataset: those somata and dendrites lie in the ventral nerve cord.
A runner-style game requiring lane changes, jumping or rolling needs limb/body
motor output that this connectome does not contain.

### 5.3 Premotor neurons

FlyWire has **no explicit `premotor` annotation**. A regex search for
"premotor" returns 75 rows, but they are taste-peg mechanosensory types
(`TPMN1`/`TPMN2`), not premotor neurons. The label must therefore be derived
from connectivity, not read from the annotation.

Derivation used here:

- For every annotated motor neuron, collect all incoming edges in the local
  thresholded graph, excluding edges from other motor neurons.
- Sum edge weights across neuropils and deduplicate by presynaptic root ID.
- Repeat for every annotated descending neuron to obtain a pre-descending pool.

Results are **candidate pools**, not validated premotor identities.

Presynaptic partners of the 110 motor neurons:

| Quantity | Value |
|---|---:|
| Unique presynaptic partners | 2,596 |
| Annotated `central` partners | 1,174 |
| Central partners feeding >= 2 motor neurons | 756 |
| Central partners feeding >= 5 motor neurons | 375 |
| Annotated `descending` partners | 519 |
| Flow of central partners | all `intrinsic` |

Edges from other motor neurons were excluded from the pool by construction, so
this table does not claim that motor-to-motor edges are absent from the graph.

Top central partner cell types: `CB1937` (12), `SAD005,SAD006` (10), `CB2962`
(9), `CB2774` (9), `CB0961` (8), `SAD047` (8), `CB0727` (7), `PS118` (7),
`CB1563` (7), `CB4068` (7), `PS194` (7), `CB1265` (7). Most have only a CB
identifier, which means the candidate premotor identities are largely
uncharacterised.

Presynaptic partners of the 1,303 descending neurons:

| Quantity | Value |
|---|---:|
| Unique presynaptic partners | 18,592 |
| Annotated `central` partners | 11,078 |
| Central partners feeding >= 5 descending neurons | 4,775 |
| Central partners feeding >= 20 descending neurons | 761 |

Top central pre-descending cell types: `PFL3` (24), `PS008` (24), `PS005` (20),
`CB1479` (19), `CB1556` (18), `PVLP004,PVLP005` (18), `CB1469` (17),
`CB1786_a` (15), `SMP018` (15), `PS087` (15), `SMP381` (14), `CB1078` (14),
`AVLP190,AVLP191` (13), `LHAV1a3` (13), `WED103` (13), `CL090_c` (13), `PFL2`
(12), `LAL028,LAL029` (12), `CB1138` (12).

Descending-to-motor interface in the local graph:

| Quantity | Value |
|---|---:|
| Direct DN -> motor edges | 2,355 |
| Descending neurons with >= 1 motor target | 519 of 1,303 |
| Motor neurons with >= 1 DN input | 90 of 110 |
| Motor neurons with no DN input | 20 |
| DN -> motor edge weight range | 5 to 801 |
| Median / mean edge weight | 13 / 28.09 |
| Edges >= 20 synapses | 868 |
| Edges >= 50 synapses | 344 |

The 20 motor neurons without DN input are mostly pharyngeal ingestion and crop
motor neurons (`CEM` 6, `MNx01` 3, `MNx03` 2, `CB0708` 2, `CB0764` 2, `CB0904`
2, `CB0769` 1, `CB0700` 1) plus one `CB2748` object. This is consistent with
local reflex circuits in the pharynx rather than a missing annotation.

In the reverse direction, 43 motor neurons are presynaptic to at least one
descending neuron (13 ingestion, 12 proboscis, 11 neck, 4 haustellum, 2 eye,
1 antennal). These are candidate feedback or efference-copy pathways, not
validated ones. Five of these 43 also have no DN input.

### 5.4 Visual-to-descending interface

Because Phase 3 already produces visual features, the visual input to
descending neurons is directly relevant. 521 of 1,303 descending neurons
receive at least one direct edge from a `visual_projection` partner. Counting
descending neurons that receive from selected visual projection cell types:

| Visual projection type | Descending neurons receiving |
|---|---:|
| LPLC2 | 874 |
| LC4 | 612 |
| LPLC1 | 441 |
| LLPC2 | 369 |
| LC9 | 172 |
| LC11 | 123 |
| LC10d | 66 |
| LC16 | 3 |
| LC17 | 1 |

These are overlapping sets: one descending neuron can receive from several
visual projection types. The counts describe graph adjacency at the `>= 5`
threshold. They do not establish that a given visual feature drives a given
descending neuron, and they do not validate the Phase 3 feature definitions.

---

## 6. BANC: availability and coverage

**Paper:** "Distributed control circuits across a brain-and-cord connectome",
*Nature* 656 (27 August 2026), DOI `10.1038/s41586-026-10735-w`. Open access,
CC BY.

### 6.1 Coverage

BANC is an adult **female** whole brain-and-ventral-nerve-cord connectome. It
contains the central brain, neck connective, VNC, and the medulla, lobula and
lobula plate of the optic lobes. It lacks the lamina and the ocellar ganglion;
both are present in FAFB.

| Property | Value (from the paper) |
|---|---:|
| Expected neurons | approximately 160,000 |
| Proofread / roughly proofread | 155,916 |
| Central brain | approximately 39,200 |
| Optic lobe | approximately 91,800 |
| VNC | approximately 24,600 |
| Motor | approximately 800 |
| Sensory | approximately 15,600 |
| Ascending | approximately 1,850 |
| Descending | approximately 1,320 |
| Descending (specific count) | 1,316 |
| Ascending (specific count) | 1,849 |
| VNC intrinsic | 1,768 (527 cell types) |
| Effector neurons | 1,031 |
| Pre-effector neurons | 8,824 |
| Pre-pre-effector neurons | 16,838 |

"Effector" here includes motor neurons, endocrine cells and efferent neurons
targeting the viscera. The pre-effector and pre-pre-effector definitions are
the closest published analogue of a premotor class, and they are explicitly
body-part associated.

### 6.2 Data availability

- Harvard Dataverse: `https://doi.org/10.7910/DVN/7WTH1N`
- BANC portal: `https://banc.community`
- FlyWire Codex BANC browser: `https://codex.flywire.ai/banc`
- CAVE materialization `v.626` (21 July 2025) used for the preprint;
  `v.888` (17 April 2026) used for the final print version
- Influence scores: Zenodo `10.5281/zenodo.15999929`
- Neurotransmitter predictions: Zenodo `10.5281/zenodo.20818141` and
  `10.5281/zenodo.20818143`
- Code: Zenodo `10.5281/zenodo.20350642` and related deposits

Static downloads include the synaptic connectivity edgelist, NBLAST results of
BANC neurons against hemibrain, FAFB, FANC and MANC, BANC all-by-all NBLAST,
skeletons, colour MIPs, aligned metadata, template registrations and
behavioural data.

### 6.3 Compatibility mechanisms

BANC explicitly provides cross-dataset machinery:

- Cell metadata includes an **FAFB (v.783) match ID** and a **MANC (v.1.2.1)
  match ID**.
- 147,846 BANC neurons were linked to a cell-type label used in another
  connectomic dataset or the literature (93.1% in the central brain and VNC).
- The authors modified typology annotations (superclass, cell class, cell
  subclass, cell function, body part) for FAFB-FlyWire and MANC to facilitate
  comparison (Supplementary Data 1-5).
- Effector annotations include body-part association and peripheral target
  type, so leg/wing/haltere motor classes exist in BANC even though they do not
  exist in FAFB.

### 6.4 Limitations

- BANC is a different female specimen with its own segmentation, synapse calls
  and image space. Its root IDs are not FlyWire root IDs.
- The FAFB v783 match IDs are a cross-dataset label bridge, not a connectivity
  bridge. They do not provide BANC edges for FAFB neurons, and they do not make
  the two graphs mergeable.
- BANC lacks the lamina and ocellar ganglion, which FAFB contains. A union of
  labels would therefore not be symmetric.
- The `v.888` final-print materialization is later than the `v.783` FAFB bundle
  and later than the local annotation snapshot. Exact row-level agreement has
  not been checked here.

---

## 7. Male CNS papers: comparative references

### 7.1 Berg et al. — complete male CNS connectome

**Paper:** "Sexual dimorphism in the complete Drosophila male central nervous
system connectome", *Cell* 189, 5504-5526 (3 September 2026), DOI
`10.1016/j.cell.2026.08.015`. Open access, CC BY.

| Property | Value (from the paper) |
|---|---:|
| Neurons | 166,700 |
| Neuron types | 11,710 |
| Isomorphic types | 8,069 |
| Dimorphic types | 138 |
| Male-specific types | 289 |
| Female-specific types | 71 |
| Voxel size | 8 x 8 x 8 nm |
| Scope | whole male CNS (brain and nerve cord) |
| fruitless / doublesex | annotated |

Data and code:

- Google bucket `gs://flyem-male-cns`
- `https://male-cns.janelia.org`
- neuPrint
- Derived products: `https://github.com/flyconnectome/2025malecns`
- Updated FAFB annotations: `https://github.com/flyconnectome/flywire_annotations`

The paper cross-matched 96.1% of central-brain and 99.7% of optic-lobe neurons
to FAFB/FlyWire and/or hemibrain. It used FAFB v783 as the female comparison
dataset. This is the strongest available cross-sex, cross-dataset label bridge,
and the updated FAFB annotations it produced are the same 3.x series inspected
in section 4.

### 7.2 Hoeller et al. — visual pathways

**Paper:** "The organization of visual pathways in the Drosophila brain",
*Cell* 189, 5552-5570 (3 September 2026), DOI `10.1016/j.cell.2026.08.014`.

- Uses the male CNS and **FAFB v783b** through neuPrint
  (`flywire-fafb:v783b`).
- 352 right-side VPNs, each with a corresponding left-side type except for a
  few named exceptions (the paper describes approximately 350 VPN types).
- 5,527 VCBN instances in the main analysis (the broader count range is
  5,200-6,700 types).
- Analysis code and galleries: `https://github.com/reiserlab/visualpathways`.

The `v783b` label is a provenance caveat: the local bundle is inferred `v783`,
not `v783b`. Root IDs may be stable across these materializations, but the
synapse tables and some annotations are not guaranteed to be identical.

### 7.3 Limitations as local resources

- Both are different specimens (male CNS; male CNS plus FAFB v783b reference).
- Neither is installed locally, and neither is part of the validated local
  artifact.
- Their root IDs and image spaces are not the local ones. They can supply
  labels, match tables and comparative context, not local edges.
- The visual-pathways paper is a functional/anatomical analysis, not a
  connectivity release for the local graph.

---

## 8. Compatibility matrix

| Dimension | Local FAFB v783 | Current FlyWire annotations | BANC | Male CNS | Assessment |
|---|---|---|---|---|---|
| Specimen / sex | adult female, brain only | same female brain | adult female, brain + VNC | adult male, whole CNS | partial |
| Neurons | 139,255 | 139,248 | ~155,916 (~160,000 expected) | 166,700 | partial |
| ID system | FlyWire root IDs | same, with 14/7 drift | BANC IDs + FAFB v783 match ID | MaleCNS IDs + FAFB v783 cross-match | compatible only through match tables |
| Connectivity | local sparse edge list, `>= 5` | none | own edgelist (Dataverse) | own connectome and edgelist | not mergeable |
| Descending neurons | 1,305 local coarse / 1,303 current | 1,303, all present locally | ~1,320 (1,316 specific) | present | compatible for the FAFB subset |
| Motor neurons | 110, head/neck/visceral only | 110, same coverage | ~800, all body parts | full motor system | incompatible for limb motor output |
| Premotor label | none explicit | none explicit | pre-effector 8,824 / pre-pre-effector 16,838 | VNC motor circuitry; no explicit premotor label verified | partial; FAFB requires connectivity derivation |
| Taxonomy | 8-column coarse local classification | 31-column 3.x schema | modified FAFB typology (Supplementary Data 1-5) | cross-matched types | partial; 586 super_class conflicts |
| Spatial registration | FAFB space, 139,255 positions | FAFB positions | BANC space + template registrations | MaleCNS space | not directly comparable |
| Licence | FlyWire CC BY 4.0 | FlyWire CC BY 4.0 | CC BY (Nature open access; Dataverse terms) | CC BY 4.0 | compatible with attribution |
| Version control | inferred v783, not attested | no `.git`, changelog 3.2.0 | v888 final / v626 preprint | v1.0/2025 | partial; exact tags unverified |

---

## 9. Recommendation: partially compatible

### 9.1 What is compatible

- The current annotation dump and the local connectome share 139,241 root IDs
  (99.99% of the local set), and **all 1,303 descending and all 110 motor
  neurons are present locally**.
- The annotation schema provides explicit `descending` and `motor` classes,
  cell types, sides, nerves, hemilineages and predicted transmitters. This is
  enough to define candidate populations without a new model architecture.
- The local graph already contains a descending-to-motor interface: 2,355
  direct edges, 519 descending neurons with at least one motor target, and
  90 of 110 motor neurons with at least one descending input.
- BANC and Male CNS provide published FAFB v783 match tables and cross-dataset
  typology. They can be used to enrich labels or to compare candidate sets,
  subject to their own licences and versioning.
- The licences of the FAFB/FlyWire resources, BANC and Male CNS are compatible
  with research use provided attribution is preserved.

### 9.2 What is not compatible

- **No limb motor output.** FAFB is brain-only. There are no leg, wing, haltere
  or abdominal motor neurons, and no VNC premotor circuitry. A brain-to-limb
  motor pathway cannot be built from the local connectome alone.
- **No native premotor label.** The candidate premotor pool is a connectivity
  derivation under a `>= 5`-synapse threshold. It is not an annotated identity
  and it is not validated against physiology.
- **No graph merge.** BANC and Male CNS are different specimens with different
  root IDs, synapse calls and image spaces. Their match IDs bridge labels, not
  edges. Merging the graphs is out of scope and technically unsupported.
- **Residual annotation drift.** 14 local roots are absent from the current
  annotation dump, 7 annotation roots are absent locally, and 586 shared roots
  have a different `super_class`. The descending and motor sets are stable, but
  optic/sensory and optic/visual-projection boundaries are not.
- **Version uncertainty.** The local bundle is inferred v783 and is not
  attested. The annotation snapshot is consistent with 3.2.0 but has no local
  git tag. The visual-pathways paper uses v783b.

### 9.3 Conditions for any future approved phase

1. Join on `root_id` with an inner join, and record the 14 dropped local roots
   and 7 dropped annotation roots.
2. Select descending and motor neurons by `super_class`, not by a `DN`/`MN`
   name prefix, because 26 neurons with DN-family names are not in
   `super_class=descending` and 2 descending neurons have `aSP` names.
3. Treat the 1,174 central presynaptic partners of motor neurons and the 11,078
   central presynaptic partners of descending neurons as `>= 5`-synapse
   candidate pools, not as validated premotor identities. Report the threshold
   and the edge-weight distribution with any result.
4. Flag the four blank-class `CB2748` motor neurons and the 20 motor neurons
   without descending input. Do not silently fold them into a motor output
   population.
5. Keep predicted transmitters labelled as predictions. `known_nt` is empty for
   all 110 motor neurons and is only partially populated for descending
   neurons.
6. Do not claim locomotion, lane control, jumping, rolling or any behavioural
   capability from a brain-only connectome. A VNC connectome is required for
   that.
7. Use BANC and Male CNS only as external label references through their match
   tables or NBLAST, not as local connectivity, and preserve their attribution
   and version notes.
8. Do not merge graphs or introduce plasticity without a separately approved
   phase and a written design.

---

## 10. Limitations of this audit

- This is a static metadata and connectivity audit. No neuron was simulated, no
  activity was recorded and no behaviour was tested.
- All connectivity results depend on the `>= 5`-synapse threshold and on
  summed-across-neuropil edge weights. Lower thresholds would change the
  partner counts.
- The local v783 version is inferred, not attested. The annotation release tag
  is inferred from the changelog, not read from a signed tag.
- BANC and Male CNS counts are quoted from the papers; they were not
  re-measured locally.
- The 14 and 7 lists were checked against the neuron annotation dump and the
  non-neuron dump, but not against every auxiliary FlyWire table.
- No manual proofreading of the candidate premotor pools was performed.
- The audit does not establish that any candidate pathway is functional,
  behaviourally relevant or correctly signed.

---

## 11. Verification

Protected resources were re-hashed at the end of the audit and match the
previously recorded values; none was modified:

| Resource | SHA-256 |
|---|---|
| `README.md` (current committed baseline) | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |
| `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` |
| `Supplemental_file1_neuron_annotations.tsv` | `b214970b55d2fbe0853bba536fdcb9e28730f4eb7ab06f600491df795da683cd` |
| `Supplemental_file2_non_neuron_annotations.tsv` | `2349fd5b4b9e53fd1b4a84aa73230bb7bebe66faa5d6a7490155aa2128861de1` |

Git state after the audit:

- no staged files (`git diff --cached` empty)
- no commit, push or branch change
- the only new file is this report
- the pre-existing uncommitted Phase 3B/3C working-tree changes are untouched

No file under `datasets/`, `references/` or `models/` was written. No package
was installed. `best.pt` was not loaded or executed.

---

## Appendix A — exact ID lists

Connectome-only (14):

```text
720575940606792881
720575940607862706
720575940613336473
720575940613437206
720575940619169349
720575940623450077
720575940623913933
720575940625523749
720575940626741265
720575940628159081
720575940633242449
720575940636488667
720575940639387763
720575940642560987
```

Annotation-only (7):

```text
720575940616847814
720575940618455453
720575940622062913
720575940624154153
720575940626850833
720575940628215433
720575940637590670
```

## Appendix B — reproducibility notes

All analysis was performed with the Python standard library and the local
NumPy artifact. The comparison is deterministic:

1. Read `root_id` from `datasets/processed/nodes.csv.gz` (139,255 unique).
2. Read `root_id` from `Supplemental_file1_neuron_annotations.tsv`
   (139,248 unique).
3. Set difference in both directions gives 14 and 7.
4. Load `connectome.npz` and map `root_id -> node_index`.
5. For incoming partners, use `in_indptr[node]` and `in_edge_idx` to index
   `edge_src` and `edge_weight`.
6. For outgoing targets, use `out_indptr[node]` and `edge_dst`.
7. Sum weights by presynaptic/target root ID and deduplicate.

No random seed is involved. Re-running the comparison reproduces the counts in
this report.
