# Phase 4B — Locomotor Motor Pathway Investigation

**Investigation date:** 2026-11-07
**Scope:** Read-only investigation of the BANC resource and the local FlyWire
FAFB v783 connectome. No motor decoder was implemented, no graph was modified or
merged, no plasticity was introduced, no experiment was run and no dataset was
downloaded.
**Verdict:** **READY WITH LIMITATIONS**

The published BANC dataset contains the locomotor motor-neuron and
descending-pathway information that FAFB lacks: 805 annotated motor neurons
including leg, wing and haltere motor pools, 1,316 descending neurons with
complete brain-to-VNC axons, and a reconstructed VNC premotor network. The
local BANC download, however, is a single publication PDF and contains no
machine-readable connectivity or annotation tables. The information is usable
only by obtaining the public BANC tables and building a separately versioned
BANC graph. It is not drop-in compatible with the local FAFB connectome:
BANC is a different female fly, uses different root IDs, has different edge
semantics and is a mutable living dataset. No biological command for left lane,
right lane, jump or roll was identified. Candidate pathways exist for all four,
with the weakest evidence for roll.

---

## 1. Executive verdict

### 1.1 The question and the short answer

> Does the downloaded BANC resource provide usable locomotor motor-neuron and
> descending-pathway information missing from the existing FlyWire FAFB v783
> brain connectome?

**Yes for the published resource; no for the local download alone.**

- The local `references/papers/BANC/BANC-connectome.pdf` is the peer-reviewed
  paper. It describes the dataset, the annotations, the counts and the
  connectivity analyses, but it is not a data release. There are no BANC
  edgelists, annotation tables, match tables or synapse tables anywhere in the
  local tree.
- The published BANC resource does contain the missing material. It has
  805 annotated motor neurons, including leg, wing, haltere, neck and abdominal
  pools; 1,316 descending neurons (1,304 matched to 473 cell types); a
  reconstructed ventral nerve cord; and public edgelists, annotation metadata
  and FAFB match tables.
- The information is not a drop-in extension of FAFB. BANC is a different
  individual female fly in a different image space, with its own root IDs and a
  different connectivity threshold. It must be used either as an annotation
  reference (Approach A) or as a separate graph (Approach B). A neuron-level
  bridge (Approach C) is not scientifically defensible in the current state.

### 1.2 Readiness by sub-question

| Sub-question | Local answer | Published BANC answer | Readiness |
|---|---|---|---|
| Is there a released connectome behind the PDF? | Yes, described | Yes, v.888 and v.626 materializations | **READY** |
| Is machine-readable connectivity locally available? | No | Yes, public edgelists | **BLOCKED locally**, READY externally |
| Are locomotor motor neurons annotated? | No leg/wing/haltere/abdomen MNs in FAFB | Yes, 805 MNs across 24 body-part categories | **READY WITH LIMITATIONS** |
| Are descending pathways complete? | FAFB DNs truncated at the neck | 1,316 DNs across the neck connective | **READY WITH LIMITATIONS** |
| Are premotor identities validated? | No | Connectivity-derived candidates only | **PARTIALLY COMPATIBLE** |
| Can BANC and FAFB be merged? | — | Different specimen, IDs and edge rules | **NOT DEFENSIBLE** |
| Are the four game actions supported? | No | Candidate pathways only | **READY WITH LIMITATIONS** |

### 1.3 The decisive numbers

| Quantity | Local FAFB v783 | Published BANC |
|---|---:|---:|
| Neurons | 139,255 | ~160,000 expected; 155,916 proofread or roughly proofread |
| Directed edges in the public graph product | 3,732,460 | 13,507,098 (`edgelist_simple_v3`) |
| Synaptic links (summed weight for FAFB) | 50,666,648 | 218,460,852 (v2) / 259,409,001 (v3) |
| Annotated descending neurons | 1,303 | 1,316 (1,304 matched, 473 types) |
| Annotated motor neurons | 110 | 805 |
| Leg / wing / haltere / abdominal MNs | 0 | Present, annotated by body part |
| Ventral nerve cord | Absent | Present, including full female abdominal neuromere |
| Direct DN -> MN edges | 2,355 | Not computed locally; requires BANC tables |
| DNs with a motor target | 519 of 1,303 | Not computed locally |
| MNs with DN input | 90 of 110 | Not computed locally |

The local figures were recomputed from the protected artifact during this
investigation and match the Phase 4A audit exactly.

### 1.4 Why the verdict is not "READY"

Four limitations prevent a clean "ready":

1. **No local data.** The only BANC artifact in the repository is the paper.
   Phase 4C would have to download public tables (at minimum ~103 MB of
   annotation and match data, or ~446 MB including the simple edgelist).
2. **Different individual.** BANC and FAFB are both adult female
   *Drosophila melanogaster*, but they are different flies. Neuron-level
   correspondence is a matching problem, not an identity.
3. **Different connectivity semantics.** FAFB edges are summed synapse counts
   with a `>= 5`-synapse threshold. BANC edges are synapse counts filtered by a
   postsynapse size threshold (5 for v2 analyses, 10 for the v3 simple
   edgelist) and normalized by postsynaptic input. The two graphs are not
   numerically interchangeable.
4. **No command validation.** BANC supports candidate pathways, not validated
   motor commands. Influence scores in the paper are explicitly unsigned and
   "no substitute for experiments".

---

## 2. Resource provenance and release information

### 2.1 Publication identity

| Field | Value |
|---|---|
| Title | Distributed control circuits across a brain-and-cord connectome |
| First author | Alexander S. Bates |
| Journal | *Nature*, volume 656, pages 957–970 |
| Received | 1 August 2025 |
| Accepted | 29 May 2026 |
| Published online | 8 June 2026 |
| Issue date | 27 August 2026 |
| DOI | `10.1038/s41586-026-10735-w` |
| License | Open access, CC BY 4.0 |
| Local copy | `references/papers/BANC/BANC-connectome.pdf`, 28,182,454 bytes, SHA-256 `82082a02005c92441e7119a9cdcc3aacb209e77c81fd2667ca7712fea489df0d` |
| Preprint DOI | `10.1101/2025.07.31.667571` (bioRxiv, 31 July 2025) |
| Preprint data DOI | `10.7910/DVN/8TFGGB` (v.626) |
| Publication data DOI | `10.7910/DVN/7WTH1N` (v.3.0) |

The paper states that the BANC dataset has been an open-science project since
July 2023 and is a living dataset (Discussion; Data availability).

### 2.2 Materialization and version history

The BANC project distinguishes the **CAVE materialization** used for analysis
from the **compiled data dump** distributed in the bucket. This distinction
matters because the bucket files can change after the named snapshot.

| Label | Date | Role | Notes |
|---|---|---|---|
| v.626 | 21 July 2025 | Preprint analysis | Dataverse `10.7910/DVN/8TFGGB`; older compiled files |
| v.888 | 17 April 2026 | Final print analysis | Root IDs used for all connectivity and influence analyses |
| v.890 | after 17 April 2026 | Later proofreading | Some optic-lobe neurons are in the analysis pool but mapped to v.888 identifiers |
| Compiled updates | June–August 2026 | Bucket maintenance | Backups in the bucket show `meta.feather` edits on 2026-06-26, 2026-06-29 and 2026-08-12 |

Direct quote from the paper's methods: "We used CAVE materialization v.626
(21 July 2025) for our preprint, and v.888 (17 April 2026) for the final print
version." The paper also states that its analysis pool includes "a number of
optic lobe neurons marked as proofread/roughly_proofread since the v.888
snapshot on 17 April 2026, corresponding to v.890 of the dataset, but mapped to
a v.888 identifier".

**Consequence:** "BANC v.888" is not a frozen file set. Any Phase 4C work must
pin file-level SHA-256 hashes, not only the version string.

### 2.3 What is locally present

Only one BANC file exists locally:

```text
references/papers/BANC/BANC-connectome.pdf
```

Confirmed absent locally:

- BANC edgelists (`.feather`)
- BANC annotation metadata (`banc_888_meta.feather`, `codex_annotations.*`)
- BANC synapse tables (`.parquet`)
- NBLAST or reviewed-match tables
- Supplementary Data files
- Any CAVE/Codex cache or credential file

The PDF was converted to text for this audit with `pdftotext -layout`
(3,920 lines, 740,332 bytes, `/tmp/fly_audit/banc_4b.txt`). The conversion is a
derived temporary file outside the repository. The PDF itself was not modified.

### 2.4 Secondary comparative references

Two other papers in the local tree are relevant context but were not the
subject of this investigation:

| Paper | Local path | Relevance |
|---|---|---|
| Berg et al., "Sexual dimorphism in the complete connectome of the Drosophila male central nervous system", *Cell* 189, 5504–5526 (2026), DOI `10.1016/j.cell.2026.08.015` | `references/connectomes/male_cns/Cell Press_20261106/Sexual-dimorphism-in-the-complete-Drosophila-male-.pdf` | Alternative whole-CNS dataset; male, not female |
| Hoeller et al., "The organization of visual pathways in the Drosophila brain", *Cell* 189, 5552–5570 (2026), DOI `10.1016/j.cell.2026.08.014` | `references/connectomes/male_cns/Cell Press_20261106/The-organization-of-visual-pathways-in-the-Drosoph.pdf` | Visual projection types used by the local perception layer; uses FAFB v783b |

The BANC paper cites the Male CNS work as a preprint (bioRxiv
`10.1101/2025.10.09.680999`). The published *Cell* version is newer than the
citation in the BANC reference list. This is a citation-version mismatch to keep
in mind, not a data conflict.

---

## 3. BANC data availability

### 3.1 Is there an actual released connectome behind the PDF?

Yes. The paper describes a dense reconstruction of one adult female fly's brain
and ventral nerve cord, with 7,010 serial sections, automated segmentation,
synapse detection, and a large manual proofreading and annotation effort. The
same paper names the public distribution channels and the analysis
materialization. The dataset is not hypothetical and is not limited to the PDF.

Key dataset facts from the paper:

| Property | Value |
|---|---|
| Specimen | Adult female *D. melanogaster*, F1 of w1118 x Canton-S |
| Behavioural screen | Turned right in 70% of 582 Y-maze choices (97th percentile handedness) |
| Sections | 7,010 |
| Section thickness | 45–50 nm |
| EM voxel size | 4 x 4 x 45 nm^3 |
| Complete sections | 6,970 (99.43%) |
| Lost sections | 10 (0.14%) |
| Partially imaged sections | 30 (0.43%) |
| Proofread / roughly proofread neurons | 155,916 |
| Expected neurons | ~160,000 |
| Central brain | ~39,200 |
| Optic lobe | ~91,800 |
| VNC | ~24,600 |
| Motor neurons | ~800 (805 annotated) |
| Sensory neurons | ~15,600 |
| Ascending neurons | ~1,850 (1,849 annotated) |
| Descending neurons | ~1,320 (1,316 annotated) |
| Effector neurons | 1,031 |
| Pre-effector neurons | 8,824 |
| Pre-pre-effector neurons | 16,838 |
| VNC intrinsic neurons | Present; exact count not stated in the main text |

The reconstruction is continuous across the neck connective. This is the
property that makes it relevant to FLY-SURFER: a brain-only dataset ends at the
neck, while BANC continues into the leg, wing and abdominal neuromeres.

### 3.2 Official machine-readable distribution

There are four independent access paths.

| Channel | What it provides | Authentication |
|---|---|---|
| Harvard Dataverse, `10.7910/DVN/7WTH1N` | Static publication-version files and code archive | None; files marked unrestricted, CC BY 4.0 |
| Google Storage bucket `gs://lee-lab_brain-and-nerve-cord-fly-connectome` | Full compiled data: edgelists, metadata, synapses, NBLAST, meshes, skeletons | None for public objects |
| CAVE / FlyWire Codex (`codex.flywire.ai/banc`) | Live queries, connectivity traversal, metadata download | Google account for the web UI; CAVEclient token for programmatic use |
| BossDB, DOI `10.60533/boss-2025-941r` | Aligned image data and flat segmentation | Public |

Important distinction: the Dataverse publication version is **not** a mirror of
the full bucket. The Dataverse API for v.3.0 lists only:

- `2024-09-20_aelysia_synapse_sample_complete_v2.csv` (263,510 bytes)
- `2026-05-14_aelysia_synapse_sample_complete_v3.csv` (638,589 bytes)
- `251013_evaluation_links.csv`
- a short description of the manual synapse review

These are synapse-detector evaluation samples, not the connectome. The full
connectivity and annotation data live in the Google Storage bucket. This is the
single most important availability finding for Phase 4C: **do not treat the
Dataverse DOI as a complete data release.**

### 3.3 Google Storage bucket inventory

The bucket is organised into top-level folders:

```text
_archive/  behavior/  compiled_data/  documentation/  imported_meshes/
light_level/  microCT/  nblast/  neuron_annotations/  neuron_colormips/
neuron_connectivity/  neuron_meshes/  neuron_skeletons/  nuclei/
region_outlines/  registrations/  synapses/  templates/
```

The files most relevant to a locomotor investigation are:

| File | Size (bytes) | Role |
|---|---:|---|
| `compiled_data/banc_888/banc_888_meta.feather` | 57,503,026 | One-row-per-object annotation metadata, 188,162 rows |
| `compiled_data/banc_888/banc_888_edgelist_simple_v3.feather` | 359,161,658 | Simple pre/post edge list, 13,507,098 rows |
| `compiled_data/banc_888/banc_888_edgelist_simple_v2.feather` | 305,250,378 | Same, v2 synapse table |
| `compiled_data/banc_888/banc_888_edgelist_split_v3.feather` | 940,605,786 | Split edgelist with side/neuropil detail |
| `compiled_data/banc_888/banc_888_edgelist_split_v2.feather` | 847,546,546 | Same, v2 |
| `nblast/banc_fafb_783_nblast.feather` | 578,411,098 | NBLAST scores against FAFB v783 |
| `nblast/banc_fafb_reviewed_matches.csv` | 6,581,434 | Manually reviewed BANC–FAFB matches |
| `neuron_annotations/v888/codex_annotations.parquet` | 74,350,281 | Long-form Codex annotations |
| `neuron_annotations/v888/codex_annotations_flat_table_260520.csv` | 39,303,076 | Flat annotation table |
| `neuron_annotations/v888/backbone_proofread.parquet` | 10,316,976 | Strict proofread list at v.888 |
| `compiled_data/banc_888/banc_888_synapses_v2_enriched.parquet` | 17,146,564,854 | Full v2 synapse table (do not download casually) |
| `compiled_data/banc_888/banc_888_synapses_v3_enriched.parquet` | 19,733,123,829 | Full v3 synapse table (do not download casually) |

Additional resources mentioned in the paper or present in the bucket:

- `nblast/banc_manc_v1.2.1_nblast.feather`
- `nblast/banc_hemibrain_v1.2.1_nblast.feather`
- `nblast/banc_fanc_1116_nblast.feather`
- `nblast/banc_malecns_v0.9_nblast.feather`
- `nblast/banc_mirror_nblast.feather`
- `compiled_data/banc_888/banc_888_neurotransmitter_prediction_v2.csv`
- `compiled_data/banc_888/banc_888_proofread_influence.sqlite`
- `compiled_data/banc_888/banc_888_betweenness_*.csv`
- `compiled_data/banc_888/banc_888_cns_network_spectral_clustering_v*.csv`
- `behavior.zip`, `banc_microCT.zip`, `banc_neuropil_meshes.zip`,
  `banc_template_spaces.zip`, `bancpipeline_archive.zip`
- `neuron_annotations/banc_to_fafb_verified_png_matches.zip` (45 GB, visual
  match review images; not needed for a first pass)

The bucket has a `documentation/` folder with a data dictionary for essentially
every file. The dictionaries for `banc_888_meta`, `banc_888_edgelist_simple_v3`,
`banc_fafb_783_nblast`, `banc_fafb_reviewed_matches` and `fly_parts_body` were
read for this report.

### 3.4 Exact release and materialization identifiers

Use these identifiers together; none of them alone is sufficient:

| Identifier | Exact value |
|---|---|
| Paper DOI | `10.1038/s41586-026-10735-w` |
| Preprint DOI | `10.1101/2025.07.31.667571` |
| Publication data DOI | `10.7910/DVN/7WTH1N` (version 3.0, 2026-05-27) |
| Preprint data DOI | `10.7910/DVN/8TFGGB` (v.626) |
| CAVE materialization | v.888, snapshot 17 April 2026 |
| Later snapshot mapped to v.888 IDs | v.890 |
| Bucket prefix | `gs://lee-lab_brain-and-nerve-cord-fly-connectome/compiled_data/banc_888/` |
| Image data DOI | `10.60533/boss-2025-941r` |
| Neurotransmitter ground truth | `10.5281/zenodo.20818141` |
| Neuropeptide ground truth | `10.5281/zenodo.20818143` |
| Influence calculator code | `10.5281/zenodo.15999929` |
| Project code archive | `10.5281/zenodo.20350642` |

### 3.5 Identifier semantics: do BANC IDs equal FAFB v783 IDs?

**No.** BANC root IDs are CAVE identifiers in the BANC segmentation. FAFB v783
root IDs are identifiers in a different segmentation of a different specimen.
The numeric ranges can look similar because both are 64-bit FlyWire-style IDs,
but equality of value has no biological meaning across datasets.

The mapping options are:

| Mechanism | Field or file | Documented semantics |
|---|---|---|
| Metadata match | `fafb_match` in `banc_888_meta.feather` | "Match to FAFB-FlyWire v783" |
| Metadata cell type | `fafb_cell_type` | "Match to FAFB-FlyWire v783" |
| NBLAST score | `nblast/banc_fafb_783_nblast.feather` | Normalized NBLAST against FAFB v783 |
| Reviewed matches | `nblast/banc_fafb_reviewed_matches.csv` | `pt_root_id`, `match_id`, `valid`; documentation says "Use for mapping to FAFB, not v783" |
| Connectivity-alignment | `fafb_alignment_cell_type` | Type proposed by the alignment algorithm |

There is a documented inconsistency here that Phase 4C must resolve before
using IDs:

- The metadata dictionary labels `fafb_match` as a v783 match.
- The reviewed-match dictionary says the reviewed file should be used "for
  mapping to FAFB, not v783".

These statements can both be true if the reviewed table was regenerated against
a later FAFB annotation release while the metadata column retains v783 values.
They cannot be assumed equivalent. Any Phase 4C mapping must record which
mechanism produced which ID and must not mix them.

### 3.6 Does BANC represent brain and VNC together?

Yes. The reconstruction is a single continuous volume spanning the brain, neck
connective and VNC, including the full female abdominal neuromere. The paper
states that this is, to its knowledge, the only connectome with the full female
abdominal neuromere.

The neck connective is the critical join:

- 3,730 profiles were seeded in the two neck planes.
- 3,686 were proofread to backbone status.
- 49 efferent neurons of the neck leave through the cervical nerves and are not
  included in the 3,686 count.
- The 18 malformed or ambiguous profiles found during review are documented.

This is exactly the region where FAFB stops. FAFB descending neurons are
truncated at the neck; BANC recovers their axons into the VNC.

### 3.7 Does BANC provide synapses, annotations, or both?

Both, but they are separate products with separate thresholds.

**Annotations.** `banc_888_meta.feather` has 188,162 rows keyed by
`banc_888_id`. It includes hierarchical labels (`super_class`, `cell_class`,
`cell_sub_class`, `cell_type`), cross-dataset matches, body-part fields,
functional descriptors, cluster assignments, neurotransmitter predictions and
verification flags. The meta table is not a clean neuron list: it contains
fragments and non-neuronal objects. For a neuron-only analysis, filter on
`super_class` and cross-check against `backbone_proofread.parquet`.

Annotation coverage reported by the paper:

- Cell-type labels assigned to 94.4% of BANC neurons (147,846 neurons; 93.1%
  excluding optic lobes).
- Estimated cell-type error rate about 7%, based on review of 1,000 neurons.
- Effectors assigned to 1 of 24 body-part categories where possible (99.4%).
- Sensors assigned to 1 of 45 body-part categories where possible (99.8%).
- 1,169 orphan sensory neurons without a nerve annotation.

**Synapses.** Two synapse tables exist:

| Table | Links | Threshold used | Notes |
|---|---:|---|---|
| `synapses_v2` | 218,460,852 | Postsynapse size >= 5 voxels | Used for the paper's connectivity and influence analyses |
| `synapses_v3` | 259,409,001 | Postsynapse size >= 10 voxels | Newer table; reported to be improved for some neuropils |

The threshold is a **postsynapse size** threshold in voxels, not a synapse-count
threshold. This is a different quantity from the local FAFB `>= 5` summed
synapse threshold.

Connection composition reported by the paper:

- 48.1% axo-dendritic
- 19.3% axo-axonic
- 24.1% dendro-dendritic
- Autapses are present and should be filtered by users.

### 3.8 Connectivity completeness

The BANC paper reports synaptic completeness as the fraction of links attached
to proofread neurons:

| Dataset | Links with identified neurons on both sides |
|---|---:|
| BANC | 18% |
| FAFB | 41.9% |
| Hemibrain | 35.3% |
| MANC | 44.4% |
| Male CNS (within-neuropil) | 40.1% |

For BANC, 74% of presynaptic ends and 23% of postsynaptic ends are connected to
a proofread neuron. The lower both-sides fraction is a real limitation: a BANC
edge list is sparser at the identified-neuron level than the FAFB artifact.

### 3.9 Access and authentication

- **Dataverse:** files are unrestricted and CC BY 4.0. The API metadata was
  read without authentication. The dataset-level `fileAccessRequest` flag is
  present, but the file entries inspected report `restricted: false`.
- **Google Storage:** the bucket is public. The JSON API returned object
  listings without credentials. The Cloud Console web UI redirects to Google
  login, which is a UI behaviour, not a data restriction.
- **FlyWire Codex:** the web interface requires a Google account login. This is
  an operational requirement, not a licence restriction.
- **CAVE programmatic access:** CAVEclient normally requires a token obtained
  through a Google account. The BANC paper does not document this step. Phase 4C
  should verify the current CAVE authentication procedure before relying on
  live queries.

For a read-only Phase 4C, the Dataverse and bucket downloads are sufficient and
require no credentials. CAVE would only be needed for live queries or for
objects not present in the static dumps.

### 3.10 Smallest relevant subset

The minimum useful acquisition for the questions in this report is:

| Purpose | File | Size |
|---|---|---:|
| Motor and DN annotations, body part, matches | `compiled_data/banc_888/banc_888_meta.feather` | 54.8 MiB |
| Flat annotation table as a fallback | `neuron_annotations/v888/codex_annotations_flat_table_260520.csv` | 37.5 MiB |
| Reviewed BANC–FAFB matches | `nblast/banc_fafb_reviewed_matches.csv` | 6.3 MiB |
| Connectivity | `compiled_data/banc_888/banc_888_edgelist_simple_v3.feather` | 342.5 MiB |

Annotation-only subset: about **98.6 MiB**.
Annotation plus connectivity: about **441 MiB**.

Not needed for a first pass:

- The enriched synapse parquets (16–18 GiB each).
- The 45 GB PNG match-review archive.
- The full mesh, skeleton and colorMIP archives.
- `banc_888_proofread_influence.sqlite` (690 MiB), unless influence scores are
  explicitly required.

The paper's own analyses used the v2 synapse table and the simple edgelist.
For a first Phase 4C, `edgelist_simple_v3` is enough to reproduce the topology;
the enriched synapse tables are only needed for per-synapse neuropil or
compartment analysis.

### 3.11 What is still unavailable

- The lamina, ocelli and ocellar ganglion are absent (about 9,390 cells).
- R1–R6 photoreceptors and lamina intrinsic cells are missing.
- There is dissection damage to both antennal nerves, affecting Johnston's organ
  sensory neurons and nearby central-brain intrinsic neurons.
- 531 FAFB cell types (6.92%) are absent from BANC, excluding ANs and DNs, which
  are truncated in FAFB and MANC.
- 171 MANC cell types (5.99%) are absent, partly because MANC is male.
- About 10% of unmatched neurons are expected to remain unmatchable because of
  reconstruction quality or developmental differences.
- Per-category motor-neuron counts are not published in the main text; they are
  derivable from `body_part_effector` but were not computed here.

---

## 4. Motor-neuron inventory

### 4.1 Direct annotation totals

The paper's annotation pipeline assigned effector identity using morphology,
connectivity and literature, and then split effectors into motor neurons and
endocrine/visceral neurons using literature and the presence or absence of large
dense core vesicles.

| Category | Count | Basis |
|---|---:|---|
| Effector neurons (all) | 1,031 | Direct annotation |
| Motor neurons | 805 | Direct annotation |
| Endocrine or viscera-targeting | 221 | Direct annotation |
| Effectors with a body-part category | 99.4% | Direct annotation |
| Body-part categories | 24 | Annotation taxonomy |

The 805 is an **expert annotation total**, not a connectivity-derived count. It
is the correct number to cite for "BANC motor neurons". It is not a count of
locomotor motor neurons: it includes head, neck, pharyngeal, crop, salivary,
antennal, eye and reproductive effectors as well.

### 4.2 Locomotor categories that are directly annotated

The paper identifies leg and wing motor neurons by morphology and connectivity,
using the exit nerve, primary-neurite trajectory, soma position and dendritic
morphology, and confirms them by comparing common synaptic input. It identifies
other effectors by morphological comparison to the literature.

| Category | Named examples in the paper | Annotation basis | Count status | FAFB counterpart |
|---|---|---|---|---|
| Front-leg motor neurons | Tergotrochanter (jump-extending) MN; trochanter flexors and extensors; sternal rotators; tergopleural promotors | Morphology, connectivity, nerve | "bulk of leg-muscle MNs"; exact number not in main text | None |
| Middle/hind-leg motor neurons | Tibia flexors and extensors; femur reductors; tarsus levators and depressors; long-tendon-muscle MNs | Morphology, connectivity, nerve | "bulk of leg-muscle MNs"; exact number not in main text | None |
| Wing-steering motor neurons | b1, b2, b3, i1, i2, iii1, iii3, iv1–iv4, tpn | Morphology, connectivity, nerve | Exact number not in main text | None |
| Wing-power motor neurons | DLM1–5, DVM1a–c, DVM2a–b, DVM3a–b | Morphology, connectivity, nerve | Exact number not in main text | None |
| Haltere motor neurons | MNhm03, MNhm42, MNhm43; power MNs hi1, hi2, hiii2 | Morphology, nerve, literature | 6 named; total not stated | None |
| Neck motor neurons | CvN1–CvN11, CvNA1/A2, VCvN1–VCvN3, DProN1–DProN9; 49 cervical efferent neurons | Morphology, nerve, literature | Named sets; total not stated | 1 local `neck_motor_neuron` plus cervical-nerve effectors |
| Abdominal motor neurons | Abdomen motor 1, abdomen motor 2, thoracic-abdominal; EFFabg28; ENXXX226 | Morphology, nerve, FAbG cross-match | Group-level, exact numbers not in main text | None |
| Head/eye/antenna | Retina MNs CB0901/CB0804; antenna MNs CB0886/CB0723; CB0750 | Morphology, literature | Named examples | Partial (eye, antennal MNs present) |
| Proboscis/pharynx/crop/salivary | MN1–MN9, MN3L/M, MN2Da/Db, MN2V, MN4a/b; MN10, MN11D, MN11V, MN12D; MN5; MN13; CEM228 | Morphology, literature | Named sets | Present in FAFB |
| Uterus/reproductive | Uterus MNs; oviDNa/oviDNb-related effectors | Literature, FAbG | Named examples | None |

**Do not turn category names into counts.** The paper gives named examples and
group descriptions, not a per-category table. A Phase 4C data pass can compute
exact counts by grouping `banc_888_meta.feather` on `body_part_effector` and
`cell_class`, but those counts do not exist in this report and must not be
invented.

### 4.3 Annotation fields available for motor neurons

The metadata dictionary documents these fields. Exact names are quoted because
they are the API contract for Phase 4C.

| Field | Meaning | Locomotor use |
|---|---|---|
| `banc_888_id` | Primary key | Neuron identity within BANC |
| `side` | Laterality | Left/right motor pool split |
| `region` | CNS region | Brain vs VNC localization |
| `nerve` | Entry/exit nerve | Target-nerve validation |
| `flow` | Afferent / intrinsic / efferent | Effector filtering |
| `super_class` | Coarse division (e.g. motor) | Motor-neuron selection |
| `cell_class` | Hierarchical class (e.g. leg motor neuron) | Locomotor category |
| `cell_sub_class` | Subclass (e.g. wing-steering) | Pool selection |
| `cell_type` | Specific type | Individual identity |
| `body_part_effector` | Body part targeted by an efferent neuron | Leg / wing / haltere / abdomen |
| `peripheral_target_type` | Sensor or effector structure or organ | Muscle / organ target |
| `cell_function` | Brief functional descriptor | Walking, flight, turning, etc. |
| `cell_function_detailed` | Finer functional descriptor | Turning vs forward walking |
| `nerve` | Exit nerve | Anatomical validation |
| `neurotransmitter_predicted` | Predicted transmitter | Excitatory/inhibitory prior |
| `neurotransmitter_score` | Prediction confidence | Sign confidence |
| `neurotransmitter_verified` | Literature-verified transmitter | Sign evidence |
| `fafb_cell_type` | FAFB v783 cell type | Cross-dataset type matching |
| `fafb_match` | FAFB v783 match | Candidate ID mapping |
| `fafb_nblast_match` | FAFB v783 NBLAST match | Candidate ID mapping |
| `fafb_alignment_cell_type` | Connectivity-alignment type | Independent type evidence |
| `cluster`, `manual_cluster`, `super_cluster` | AN/DN clustering | Functional module |
| `cns_network` | CNS network membership | Leg VNC / abdominal VNC / brain network |

Note that BANC has richer effector fields than the local FAFB annotation table.
The local table has `cell_class`, `cell_sub_class`, `cell_type`, `nerve`, `side`,
`flow`, `super_class`, `top_nt`, `known_nt` and `dimorphism`, but no
`body_part_effector` or `peripheral_target_type`.

### 4.4 Muscle and anatomical target information

The paper provides anatomical targets at three levels:

1. **Nerve-level.** Each motor neuron exits through a named nerve: prothoracic,
   accessory prothoracic, ventral prothoracic, mesothoracic, metathoracic,
   cervical, dorsal prothoracic, ventral cervical, antennal, maxillary-labial,
   pharyngeal, abdominal trunk, second/fourth abdominal.
2. **Muscle-group-level.** Named pools map to tergotrochanter, trochanter
   flexors/extensors, sternal rotators, tergopleural promotors, tibia
   flexors/extensors, femur reductors, tarsus levators/depressors, long-tendon
   muscles, indirect flight muscles (DLM/DVM), and haltere power muscles.
3. **Individual-muscle-level.** The paper names individual motor neuron types
   (e.g. DLM1–5, DVM1a–c) that correspond to identified muscles in the
   literature, but it does not provide a machine-readable muscle table in the
   main text.

The machine-readable target fields are `body_part_effector`,
`peripheral_target_type`, `nerve` and `cell_function`. A muscle-by-muscle table
would require Supplementary Data 2–5 or a query of the metadata plus literature
cross-referencing. It is not present in this report.

### 4.5 Direct annotations versus connectivity-derived candidates

This distinction is mandatory for the rest of the report.

| Identity class | Definition | BANC examples | Evidence level |
|---|---|---|---|
| Direct annotation | A human assigned the cell type and body part using morphology, nerve, literature and, for leg/wing MNs, connectivity confirmation | 805 motor neurons; leg, wing, haltere, neck, abdominal pools | Anatomically identified |
| Connectivity-derived candidate | A cell is called premotor or upstream because it is presynaptic to a motor neuron in the graph | 8,824 pre-effectors; 16,838 pre-pre-effectors; leg VNC intrinsic neurons | Candidate only |
| Influence-derived association | A cell has a high unsigned influence score onto an effector | DNs with high adjusted influence on leg/wing MNs | Candidate only, unsigned |
| Behavioural hypothesis | A cell type has a literature-documented behavioural role | DNa01 "turning"; DNg100 "leg CPG"; DNp06 "escape-takeoff" | Literature, not measured here |

A name such as `leg motor neuron` is a direct annotation. A name such as
`premotor candidate` is not. The BANC paper is careful about this; this report
must be equally careful.

### 4.6 Do BANC motor neurons map to FAFB?

At the **cell-type** level, many do, because BANC reused FAFB type names where
possible. At the **neuron-ID** level, no.

The mapping evidence is:

- `fafb_match`, `fafb_cell_type` and `fafb_nblast_match` are present in the
  metadata.
- NBLAST top-1 accuracy is 65.7% for central-brain neurons, 28.0% for VNC
  neurons that are not sex-specific, and 19.9% for optic-lobe neurons.
- 118,380 neurons were matched by NBLAST followed by manual review.
- 47% of cell types differ from the type of the max-NBLAST match, which is why
  manual review was required.
- The estimated cell-type error rate is about 7%.

For locomotor motor neurons, the FAFB side has no leg, wing, haltere or
abdominal MNs at all. There is therefore nothing to map those BANC neurons onto
inside FAFB. The mapping is only meaningful for shared head/neck motor pools and
for descending neurons.

### 4.7 Is connectivity available for BANC motor neurons?

Yes, in the public edgelists. It is not available locally.

The simple edgelist has these columns:

| Column | Meaning |
|---|---|
| `pre` | Presynaptic BANC root ID |
| `post` | Postsynaptic BANC root ID |
| `count` | Synapse count for the pair |
| `norm` | `count / post_count` |
| `post_count` | Total input synapses onto the postsynaptic neuron |
| `pre_count` | Total output synapses from the presynaptic neuron |

`edgelist_simple_v3` has 13,507,098 rows, uses a postsynapse size threshold of
10 voxels and excludes autapses. The v2 version uses the size-5 threshold.

### 4.8 Motor-neuron caveats

1. The 805 total includes non-locomotor effectors. Do not report it as a
   locomotor count.
2. Per-category counts are not in the paper.
3. One hundred and ten local FAFB motor neurons are head, neck, crop, proboscis,
   antennal, eye, salivary and haustellum MNs. They are not a subset of the
   BANC limb pools.
4. Four local `CB2748` objects are blank-class, `flow = intrinsic` and
   `nerve = ON`; they are anomalous in the motor class and should not be folded
   into a motor output population.
5. BANC motor-neuron transmitters are predictions unless
   `neurotransmitter_verified` is populated. The local FAFB `known_nt` field is
   empty for all 110 motor neurons.

---

## 5. Descending-pathway inventory

### 5.1 Counts

| Quantity | Value | Source |
|---|---:|---|
| Descending neurons identified | 1,316 | Paper, neck-connective section |
| DNs matched to a cell type | 1,304 | Paper |
| DN cell types | 473 | Paper |
| Ascending neurons identified | 1,849 | Paper |
| ANs matched | 1,768 (527 types) | Paper |
| Sensory DNs | 13 (5 types) | Paper |
| Female-specific DNs | 16 (8 types) | Paper |
| Descending neurons in Fig. 1 summary | ~1,320 | Figure 1 |
| Local FAFB DNs | 1,303 (473 types) | Local annotation table |

The local FAFB set has exactly the same number of DN cell types (473) as the
BANC matched set. That is consistent with BANC reusing FAFB DN type names, but it
is not proof that every type corresponds one-to-one. The local set is smaller by
13 neurons, and FAFB DNs are truncated at the neck.

### 5.2 Brain–VNC span

BANC resolves the full descending axon from the brain through the neck
connective into the VNC. This is the main structural advantage over FAFB.

| Feature | FAFB v783 | BANC |
|---|---|---|
| Brain | Yes | Yes |
| Neck connective | Truncated | Reconstructed |
| VNC | Absent | Present |
| Descending axon | Truncated | Complete to target neuromere |
| Leg/wing/haltere motor pools | Absent | Present |
| Abdominal neuromere | Absent | Full female abdominal neuromere |

The paper reviewed 3,730 seeded neck profiles and proofread 3,686 to backbone
status. It also identified 49 efferent neurons of the neck that leave through
cervical nerves and are not part of the 3,686 count.

### 5.3 Functional modules

The paper clustered ANs and DNs into 13 behaviour-centric modules. The locomotor
relevance is summarised below. Cluster membership is connectivity-derived; the
names are hypotheses assigned by the authors after inspecting sensory input,
effector output and literature.

| Cluster | Dominant input | Dominant output | Locomotor relevance |
|---|---|---|---|
| Walking | Leg bristles, leg hair plates | All three leg motor groups; neck MNs | Direct candidate for forward/backward walking and halting |
| Walking-steering | Leg bristles, leg hair plates | Neck MNs (all four neck-axis groups) | Steering and gaze stabilization |
| Postural control | Leg bristles, wing mechanosensors | Leg, abdomen and neck MNs | Posture, landing, abdomen curl |
| Flight steering 1 | Johnston's organ, prosternal hair plates, wing campaniform, eye bristles | Wing-steering MNs, neck-axis MNs | Turning and flight steering |
| Flight steering 2 | Haltere campaniform | Wing-steering MNs, neck-axis MNs | Haltere-mediated steering |
| Flight power | Johnston's organ, wing campaniform | Wing-steering and wing-power MNs | Wingbeat power |
| Head orienting | Eye bristles, prosternal hair plates, Johnston's organ | Neck-axis MNs | Head/eye orienting |
| Threat response | Body-surface bristles, taste pegs | Multi-leg motor output | Escape, backward walking, steering |
| Grooming | Labellum bristles, front-leg bristles, hair plates | Neck and front-leg MNs | Front-leg coordination |
| Probing | Labellum bristles, front-leg hair plates, taste sensilla | Proboscis MNs, prothoracic neurosecretory cells | Feeding-related, not locomotion |
| Feeding | Leg taste pegs | Proboscis MNs | Feeding |
| Taste–touch | Leg bristles, taste pegs, wing-margin bristles | Mixed | Mixed |
| Tactile | Bristles from all body parts | Broad motor | Whole-body tactile integration |
| Vibratory | Chordotonal organs | Broad motor | Vibration sensing |
| Proprioceptive | Hair plates across legs | Broad motor | Limb proprioception |
| Reproduction | Leg bristles, abdominal sensors | Neurosecretory effectors | Reproduction |
| Visceral control | Visceral and interoceptive sensors | Neurosecretory cells, thoracic-abdominal MNs | Internal state |

The table lists 17 rows because the paper describes sub-clusters and effector
groups in addition to the 13 top-level AN/DN clusters. The exact 13-cluster
assignment is in `cluster` / `super_cluster` in the metadata.

### 5.4 Named descending neurons with locomotor evidence

The table separates the paper's claims from the underlying literature. A
"documented role" is a citation in the BANC paper, not a measurement performed
for this report.

| DN | Paper's functional label | Connected motor output | Evidence level |
|---|---|---|---|
| DNa01 | Turning | Leg MNs (walking cluster) | Literature role + connectivity |
| DNg13 | Turning | Leg MNs | Literature role + connectivity |
| DNa03 | Turning | Wing/leg circuits | Literature role + connectivity |
| DNa04 | Flight turning | Wing MNs | Literature role + connectivity |
| DNa15 | Turning | Wing/leg circuits | Literature role + connectivity |
| DNae003 | Turning | Wing/leg circuits | Literature role + connectivity |
| DNb01 | Turning | Wing/leg circuits | Literature role + connectivity |
| DNp03 | Turning | Wing/leg circuits | Literature role + connectivity |
| DNb08 | Leg central pattern generator | Leg MNs | Literature role |
| DNg100 | Leg CPG; forward walking | Leg MNs | Literature role |
| DNg97 | Forward walking | Leg MNs | Literature role |
| AN17A026 | Backward walking | Leg MNs (ascending, not descending) | Literature role |
| DNp09 | Halting | Leg MNs | Literature role |
| DNp07 | Landing; backward walking | Leg MNs | Literature role |
| DNp06 | Escape takeoff | Multi-leg MNs | Literature role |
| DNp42 | Backward walking | Leg MNs | Literature role |
| DNg55 | Steering | Leg MNs | Literature role |
| DNge053 | Walking | Leg MNs | Literature role |
| DNge104 | Tibia extension | Excitatory onto tibial extensor; inhibitory onto tibial flexor | Connectivity + predicted sign |
| DNa06 | Eye/neck orienting | Eye and neck MNs; targets DNg89 | Connectivity |
| DNpe013 | Eye/neck/leg influence | Eye, neck and leg MNs | Connectivity |
| AN19B025 | Antenna/eye/neck/wing influence | Antenna, eye, neck and wing MNs | Connectivity (ascending) |
| DNp01, DNp02, DNp04 | Giant fibre escape | Escape-takeoff circuitry | Literature role; morphology caveat |
| DNp11 | Escape takeoff | Multi-leg MNs | Literature role |
| DNp10, DNp47 | Landing | Leg/neck MNs | Literature role |
| DNg14 | Abdomen curl | Abdominal MNs | Literature role |
| DNb05 | Turning | Leg/neck MNs | Literature role |
| DNg75 | Forward walking | Leg MNs | Literature role |
| DNge050 | Walking | Leg MNs | Literature role |
| DNp60 | Wing pump | Wing MNs | Literature role |

The paper adds an explicit caution about the giant-fibre DNs: their unusual
morphology causes a higher rate of false synaptic detections and registration
artefacts, so automatic cluster assignments for DNp01, DNp02 and DNp04 should be
interpreted cautiously.

**What this table does not show.** It does not show that any one DN commands a
left turn, a right turn, a jump or a roll. It shows that DNs with
literature-documented turning/walking/escape roles are connected, directly or
through VNC premotor cells, to the relevant motor pools.

### 5.5 Intervening premotor candidates

The pathway from a DN to a leg muscle is not usually monosynaptic. The paper
shows that VNC intrinsic neurons intervene and that the leg VNC network is the
largest CNS network in the dataset.

| Layer | Count | Definition | Status |
|---|---:|---|---|
| Effector neurons | 1,031 | Directly innervate muscle or viscera | Direct annotation |
| Pre-effectors | 8,824 | Directly presynaptic to an effector | Connectivity-derived candidate |
| Pre-pre-effectors | 16,838 | Directly presynaptic to a pre-effector | Connectivity-derived candidate |

The leg VNC network "comprises the single-leg-neuromere intrinsic neurons of the
prothoracic, mesothoracic and metathoracic leg circuits". The abdominal VNC
network covers the abdominal ganglion. The dorsal VNC network has the largest
brain contingent, reflecting haltere and wing campaniform feedback.

The paper's Fig. 5 explicitly notes "the role of VNC interneurons in recruiting
leg motor neurons". That is a statement about network architecture, not a
validated premotor identity for any individual cell.

### 5.6 Synaptic resolution

| Property | Value |
|---|---|
| EM voxel size | 4 x 4 x 45 nm^3 |
| Detection input | 8 x 8 x 45 nm^3 |
| Detection output | 16 x 16 x 45 nm^3 |
| Sections | 7,010 |
| Section thickness | 45–50 nm |
| Postsynapse size threshold, v2 | >= 5 voxels |
| Postsynapse size threshold, v3 | >= 10 voxels |
| Links with identified neurons on both sides | 18% |
| Axo-dendritic / axo-axonic / dendro-dendritic | 48.1% / 19.3% / 24.1% |
| Autapses | Present; filter them |

The resolution is sufficient for synapse-level connectivity between identified
neurons. It is not sufficient to guarantee that every edge is a functional
synapse, and the 18% both-sides-identified fraction means many edges involve
unidentified fragments.

### 5.7 What BANC adds over FAFB

| Missing in FAFB | BANC provision | Consequence for FLY-SURFER |
|---|---|---|
| Leg motor neurons | Annotated front, middle and hind leg pools | A candidate locomotor output layer exists |
| Wing motor neurons | Steering and power pools | Flight-related output exists, not needed for Subway Surfers |
| Haltere motor neurons | Named steering and power MNs | Flight stabilization, not needed for the game |
| Abdominal motor neurons | Abdomen motor 1/2, thoracic-abdominal | Body posture and bending |
| Complete DNs | 1,316 DNs through the neck | Brain-to-VNC pathways are reconstructable |
| VNC premotor network | VNC intrinsic neurons; 8,824 pre-effectors | Intervening layers are available as candidates |
| Full female abdominal neuromere | Present | Reproduction/visceral context, not locomotion |

### 5.8 What BANC does not establish

- It does not establish the sign of a connection from connectivity alone.
  Transmitters are predicted, and predictions are not measurements.
- It does not establish that an influence score is excitatory, inhibitory or
  functional. The paper states the scores are unsigned and "no substitute for
  experiments".
- It does not establish a command neuron for any behaviour.
- It does not establish that a pathway is used in a game-like task.
- It does not establish that a homologous FAFB neuron has the same connectivity.

---

## 6. Premotor candidate analysis

### 6.1 What "premotor" means here

FLY-SURFER has no `premotor` annotation in the local FAFB table. The Phase 4A
audit found 75 rows matching "premotor" by regex, all of them taste-peg
mechanosensory types (`TPMN1`/`TPMN2`). The label must be derived from
connectivity, never read from a name.

In this report:

- **Premotor candidate** = a neuron with a direct edge onto a motor neuron in the
  stated graph, excluding other motor neurons.
- **Pre-premotor candidate** = a neuron with a direct edge onto a premotor
  candidate.
- Neither label asserts a functional premotor role.

### 6.2 BANC's pre-effector layers

The paper defines a pre-effector as a neuron directly presynaptic to an effector,
and a pre-pre-effector as a neuron directly presynaptic to a pre-effector. The
counts are 8,824 and 16,838. These are graph-derived, not manually validated.

The paper uses these layers for an influence analysis, not for cell-type
assignment. The analysis threshold is 5 synapses for influence and no threshold
for the raw connectivity analysis. The resulting influence scores are
normalized, unsigned and computed over a rescaled weight matrix whose largest
real eigenvalue is 0.99.

### 6.3 The leg VNC network

The leg VNC network is the strongest structural candidate for a locomotor
premotor layer:

- It is the largest CNS network in the dataset.
- It comprises the single-leg-neuromere intrinsic neurons of the prothoracic,
  mesothoracic and metathoracic leg circuits.
- It receives descending influence from the walking, walking-steering and
  postural-control DN clusters.
- It outputs to the front-leg and middle-hind-leg motor groups.
- The front-leg and middle-hind-leg groups are the only effector groups that are
  bilaterally split.

This is a coherent candidate architecture for left/right leg control. It is not
a validated left/right command circuit. The bilateral split is a structural
precondition for differential steering, not evidence that a particular DN
produces it.

### 6.4 Candidate pools from the local FAFB graph

For comparison, Phase 4A computed candidate pools inside the brain-only graph:

| Quantity | Value |
|---|---:|
| Unique presynaptic partners of the 110 MNs | 2,596 |
| Annotated `central` partners | 1,174 |
| Central partners feeding >= 2 MNs | 756 |
| Central partners feeding >= 5 MNs | 375 |
| Annotated `descending` partners | 519 |
| Unique presynaptic partners of the 1,303 DNs | 18,592 |
| Annotated `central` partners of DNs | 11,078 |
| Central partners feeding >= 5 DNs | 4,775 |
| Central partners feeding >= 20 DNs | 761 |

These are brain-side candidates for head, neck and pharyngeal motor control.
They cannot be extended to limb motor control because FAFB has no limb motor
neurons. The 1,174 and 11,078 figures must not be presented as premotor pools
for walking.

### 6.5 Validation checklist for any premotor claim

A candidate should not be promoted to "premotor" without all of the following:

1. **Threshold sensitivity.** Recompute at more than one edge threshold and
   report the partner count and edge-weight distribution.
2. **Sign.** Use `neurotransmitter_predicted` and, where available,
   `neurotransmitter_verified`; report the confidence.
3. **Bilateral structure.** Check whether the candidate is left, right or
   bilateral and whether it contacts the appropriate side's motor pool.
4. **Muscle target.** Confirm the motor neuron's target muscle or muscle group
   through `peripheral_target_type`, `nerve` and literature.
5. **Convergence.** Check whether the candidate contacts multiple motor neurons
   in the same pool, as a real premotor interneuron should.
6. **Disambiguation.** Exclude edges that are likely fragments, autapses or
   misassigned synapses.
7. **Independent evidence.** Prefer candidates supported by both NBLAST/type
   matching and connectivity, not by connectivity alone.
8. **Behavioural grounding.** If a behavioural role is claimed, cite the
   experimental study; do not infer it from the graph.

### 6.6 Candidate classes and their current status

| Candidate class | Current evidence | What is missing | Status |
|---|---|---|---|
| Leg VNC intrinsic neurons | Network membership; output to leg MNs | Individual premotor identity; sign; muscle target | Candidate |
| Walking-cluster DNs | Literature roles; leg motor output | Side specificity; direct vs polysynaptic; sign | Candidate |
| Walking-steering DNs | Literature roles; neck motor output | Leg motor contact; side specificity | Candidate |
| Postural-control DNs | Literature roles; leg/abdomen/neck output | Direct leg contact; sign | Candidate |
| Flight-steering DNs | Literature roles; wing/haltere output | Not relevant to lane/jump/roll | Candidate |
| Giant-fibre DNs | Escape literature; multi-leg output | Artefact rate; direct vs polysynaptic | Candidate with caveat |
| Pre-effector neurons | Direct edge onto effectors | Identity; sign; pool specificity | Candidate |
| FAFB central MN partners | Direct edge onto head/neck MNs | Not limb-related | Candidate, brain-only |

---

## 7. FAFB–BANC compatibility assessment

### 7.1 Compatibility at a glance

| Dimension | FAFB v783 | BANC v.888 | Compatible? | Consequence |
|---|---|---|---|---|
| Species | *D. melanogaster* | *D. melanogaster* | Yes | Same species |
| Sex | Adult female | Adult female | Yes | Same sex |
| Individual | One fly | A different fly | No | No individual identity |
| Scope | Brain only | Brain + VNC | No | BANC has the missing tissue |
| Root IDs | FAFB IDs | BANC CAVE IDs | No | Mapping required |
| Cell-type names | FAFB taxonomy | Reuses FAFB names where possible | Partial | Type-level matching possible |
| Annotation release | Current FlyWire 3.x | v.888 / v.890 mixed | No | Version pinning required |
| Edge weight | Summed synapse count | Synapse count, size-filtered | No | Not numerically interchangeable |
| Edge threshold | >= 5 synapses | Postsynapse size >= 5 or 10 voxels | No | Different filtering |
| Edge normalization | None in the artifact | `count / post_count` available | No | Use raw `count` if comparing |
| Autapses | Filtered in the artifact | Present in raw tables | No | Filter before analysis |
| Connectivity completeness | 41.9% both-sides identified | 18% both-sides identified | No | BANC edges are sparser |
| Brain neuron count | 139,255 | ~131,000 brain + optic lobe | Partial | Similar scale, not equal |
| VNC neuron count | 0 | ~24,600 | No | BANC only |
| Motor neuron count | 110 | 805 | No | BANC only for limbs |
| DN count | 1,303 | 1,316 | Partial | Similar scale, different completeness |

### 7.2 Specimen and scope

Both datasets are adult female *Drosophila melanogaster*. BANC was selected from
an F1 cross of w1118 and Canton-S and behaviourally screened for handedness.
FAFB is the Full Adult Fly Brain volume used by FlyWire. They are not the same
animal and were not prepared identically.

BANC is a brain-and-cord dataset. FAFB is brain-only. This is the fundamental
asymmetry: BANC contains tissue that FAFB does not, so a merge would not be a
merge of peers. It would be an attachment of a VNC from one animal to a brain
from another.

### 7.3 Identifier compatibility

There is no direct ID equality. The mapping mechanisms are:

1. `fafb_match` / `fafb_cell_type` in the metadata, documented as v783 matches.
2. `banc_fafb_783_nblast.feather`, normalized NBLAST against v783.
3. `banc_fafb_reviewed_matches.csv`, manually reviewed matches with columns
   `pt_root_id`, `match_id`, `valid`, documented as "for mapping to FAFB, not
   v783".
4. `fafb_alignment_cell_type`, a connectivity-alignment type.

The match quality is not uniform:

| Region | Top-1 NBLAST correct | Mean normalized score for correct hits |
|---|---:|---:|
| Central brain | 65.7% | 0.48 |
| VNC (not sex-specific) | 28.0% | 0.53 |
| Optic lobe | 19.9% | 0.49 |

The VNC accuracy is the relevant number for locomotor work, and it is low. Manual
review is mandatory. The paper states that 47% of cell types differ from the
max-NBLAST match.

### 7.4 Cell-type compatibility

Positive evidence:

- Both datasets use FAFB-derived DN type names where possible.
- The local FAFB DN set has 473 cell types; the BANC matched DN set has 473.
- 39 of 41 DN names cited in the BANC paper are present in the local FAFB
  annotation table.
- The two missing names are `DNg25` and `DNd01`, which the BANC paper itself
  says are "not identifiable" (`DNg25`) or "not a DN but rather a central brain
  intrinsic neuron" (`DNd01`). This is a consistency check in favour of the
  type-level mapping.

Negative evidence:

- 531 FAFB cell types (6.92%) are absent from BANC, excluding ANs and DNs.
- The BANC cell-type error rate is about 7%.
- VNC top-1 NBLAST accuracy is 28.0%.
- The local FAFB annotations and BANC v.888 annotations are from different
  release dates.

### 7.5 Connectivity compatibility

The two graphs are not interchangeable.

| Property | Local FAFB artifact | BANC simple edgelist |
|---|---|---|
| Rows | 3,732,460 | 13,507,098 |
| Threshold | Summed synapse count >= 5 | Postsynapse size >= 10 voxels (v3) |
| Weight | Summed `syn_count` across neuropils | `count` synapses; `norm = count / post_count` |
| Autapses | Excluded | Excluded in simple edgelist; present in raw tables |
| Identified-both-sides | 41.9% | 18% |
| Normalization | None | `norm` column available |
| Neuropil detail | Not in the artifact | Available in split edgelist |

The local artifact has 3.7 million edges because it is a `>= 5` summed-synapse
graph. The BANC simple edgelist has 13.5 million rows because it is a
postsynapse-size-filtered graph at a lower effective connection threshold. The
row counts cannot be compared directly.

If a Phase 4C analysis needs a like-for-like comparison, it must impose its own
synapse-count threshold on the BANC `count` column and report it. It must not
describe the BANC graph as "the same graph at a different resolution".

### 7.6 Version compatibility

| Dataset | Version | Date | Frozen? |
|---|---|---|---|
| FAFB local artifact | v783, inferred | 2024 | Frozen locally by SHA-256 |
| FAFB annotations | Current FlyWire 3.x | 2026 snapshot | Frozen locally by SHA-256 |
| BANC analysis | v.888 | 17 April 2026 | Conceptually frozen, but bucket files updated |
| BANC later proofreading | v.890 | After 17 April 2026 | Mapped to v.888 IDs |
| BANC compiled data | Bucket files | June–August 2026 edits | Not frozen |

The bucket contains explicit backups:

- `banc_888_meta.feather.backup_pre_sidefill_2026-06-26`
- `banc_888_meta.feather.backup_pre_sidefill_2026-06-29`
- `banc_888_meta.feather.pre_l2patch_20260629`
- `banc_888_meta.feather.pre_shoreup_20260812`

This is a healthy provenance practice by the BANC team, but it means a Phase 4C
download must record the hash of the exact object it used.

### 7.7 Duplicate-neuron risk

| Scenario | Duplicate risk | Explanation |
|---|---|---|
| FAFB brain + BANC annotation reference only | Low | No neurons are added to the FAFB graph |
| Separate BANC graph | None | One graph, one ID space |
| FAFB brain + BANC VNC bridge at DNs | High | The same DN cell type exists on both sides as a different individual |
| FAFB brain + BANC brain + BANC VNC | Very high | Two brains, two sets of brain neurons, one VNC |
| Cell-type-level comparison only | Low | No ID duplication; type-level aggregation |

The bridge scenario is the dangerous one. A BANC DN and an FAFB DN with the same
name are not the same neuron. If you attach the BANC VNC to the FAFB brain using
the FAFB DN as the soma/dendrite and the BANC DN as the axon, you create a
chimeric cell that exists in neither animal. The synapse weights on the two
sides come from different individuals and different detection pipelines.

### 7.8 Evaluation of the four integration approaches

#### Approach A — FAFB brain graph, BANC as annotation reference

| Criterion | Assessment |
|---|---|
| Biological coverage | FAFB coverage unchanged; BANC adds labels and target categories |
| Neuron-ID compatibility | Type-level only; no IDs added |
| Connectivity compatibility | Not required |
| Duplicate-neuron risk | Low |
| Version risk | Moderate; pin the annotation and match files |
| Scientific defensibility | High, if labels are marked as cross-dataset inferences |
| Best use | Enrich FAFB DN and head/neck MN annotations; define candidate pools |
| Verdict | **Recommended for the first step** |

This is the safest way to use BANC. It answers "what type is this FAFB neuron
likely to be?" and "what body part does its BANC homolog target?" without
altering the FAFB graph. The limitation is that it does not add limb motor
neurons or VNC connectivity.

#### Approach B — separately versioned BANC brain-plus-VNC graph

| Criterion | Assessment |
|---|---|
| Biological coverage | Complete brain, neck and VNC; limb motor pools included |
| Neuron-ID compatibility | Coherent within BANC; separate from FAFB |
| Connectivity compatibility | Coherent within BANC; not comparable to FAFB without re-thresholding |
| Duplicate-neuron risk | None within the graph |
| Version risk | High; pin file hashes and document v.888/v.890 |
| Scientific defensibility | High, if presented as a separate animal |
| Best use | Locomotor pathway analysis and LIF simulation with limb output |
| Verdict | **Recommended as the Phase 4C architecture** |

This is the only approach that gives FLY-SURFER a complete brain-to-limb graph.
It requires a new loader and a new configuration, but it does not touch the FAFB
artifact, tests or baseline results.

#### Approach C — validated bridge between FAFB brain and BANC VNC

| Criterion | Assessment |
|---|---|
| Biological coverage | Chimera of two animals |
| Neuron-ID compatibility | Type-level mapping with 28% VNC top-1 accuracy |
| Connectivity compatibility | Two different pipelines joined at an unvalidated seam |
| Duplicate-neuron risk | High at the DN join |
| Version risk | High; two mutable datasets |
| Scientific defensibility | Low in the current state |
| Best use | None until a separately approved design exists |
| Verdict | **Not recommended** |

The bridge is not a technical problem that more code can solve. It is a
scientific-identity problem. A synapse-level bridge would need:
individual-animal correspondence (impossible), a validated one-to-one DN match
(not available at 28% VNC accuracy), and a demonstrated equivalence of edge
semantics (not present). Root-ID matches are not sufficient.

#### Approach D — BANC as a separate experimental network compared with FAFB

| Criterion | Assessment |
|---|---|
| Biological coverage | Two complete but different scopes |
| Neuron-ID compatibility | Not required for aggregate comparison |
| Connectivity compatibility | Aggregate statistics can be recomputed per graph |
| Duplicate-neuron risk | None |
| Version risk | Moderate; pin both |
| Scientific defensibility | High for comparative topology, not for individual pathways |
| Best use | Test whether FAFB brain-only conclusions hold in a whole-CNS graph |
| Verdict | **Recommended as a validation track** |

This is a good medium-term use. It lets the project ask whether a result is a
property of the FAFB brain or a property of the whole CNS, without claiming
neuron-level correspondence.

### 7.9 Recommendation among the four

1. **Approach B** is the Phase 4C architecture: a separate, versioned BANC graph
   with its own loader, configuration and reports.
2. **Approach A** is a parallel annotation track: use BANC labels to enrich FAFB
   DN and head/neck MN descriptions, clearly marked as cross-dataset inference.
3. **Approach D** is a later validation track: compare aggregate graph
   statistics between FAFB and BANC.
4. **Approach C** is rejected for now. It should only be reconsidered after a
   separately approved design that specifies how individual identity, edge
   semantics and the seam are validated.

---

## 8. Subway Surfers action feasibility matrix

### 8.1 The action space

The local `GameState` represents four player states relevant here:

- lane: left, centre, right
- jumping: boolean
- rolling: boolean
- speed: scalar

The game actions are lateral lane change, jump and roll (duck). They are
discrete, short-duration commands, not continuous locomotion.

### 8.2 Feasibility matrix

| Game action | What the body must do | FAFB support | BANC anatomical support | Connectivity-supported candidates | Evidence class | Main blocker | Phase 4C feasibility |
|---|---|---|---|---|---|---|---|
| Move left | Shift body left while running; asymmetric leg push | None at the motor level | Leg MNs on both sides; front and middle-hind pools | Turning/steering DNs -> VNC intrinsic -> leg MNs; left-side pool preference unproven | Anatomically identified MNs; candidate pathway | No identified left-command DN; no side-specific validation | Candidate-only experiment |
| Move right | Mirror of left | None at the motor level | Same | Same, mirrored | Anatomically identified MNs; candidate pathway | Same | Candidate-only experiment |
| Jump | Rapid bilateral leg extension; body launch | None | Tergotrochanter (jump-extending) MN; trochanter extensors; tibia extensors | Giant-fibre DNs (DNp01/02/04), DNp06, DNp11 -> leg MNs | Anatomically identified jump MN; candidate DN pathway | Escape reflex, not a precision vault; bilateral coordination unresolved | Candidate-only experiment |
| Roll / duck | Crouch, lower body, slide under obstacle | None | Tibia/trochanter/femur/tarsus flexor MNs; abdominal motor groups | Flexor MN pools; postural-control DNs; no identified roll command | Hypothetical mapping | The game's roll is not the fly's escape roll; no annotated roll motor neuron | Weakest; hypothesis only |

### 8.3 Evidence classification

**Anatomically identified.**

- Leg motor neurons exist and are annotated by body part, side and nerve.
- A tergotrochanter (jump-extending) motor neuron is explicitly named.
- Tibia flexors/extensors, trochanter flexors/extensors, femur reductors and
  tarsus levators/depressors are explicitly named.
- Wing and haltere motor pools exist, though they are not needed for the four
  game actions.

**Connectivity-supported candidate.**

- Turning/steering DNs are connected to leg motor pools through the VNC.
- Walking and walking-steering clusters output to all three leg motor groups.
- Giant-fibre and escape DNs output to multi-leg motor pools.
- Postural-control DNs output to leg, abdomen and neck motor neurons.

**Hypothetical.**

- That a specific DN or small population encodes "move left" or "move right".
- That the jump-extending motor neuron is the right output for a game vault.
- That any BANC pathway corresponds to the game's roll/duck action.
- That stimulating a pool will produce a useful, timed game action.

### 8.4 What a Phase 4C experiment could claim

A defensible Phase 4C experiment could claim:

- "We constructed a BANC-derived locomotor subgraph containing annotated leg
  motor neurons and their presynaptic partners."
- "We identified candidate descending and VNC-intrinsic pathways to left, right
  and jump-related motor pools."
- "Under a specified stimulation protocol, the candidate pathway produced
  activity in the selected motor pool."
- "The result is a structural and simulated candidate, not a validated motor
  command."

It could not claim:

- "The fly connectome chooses the left lane."
- "We found the jump command neuron."
- "The model plays Subway Surfers."
- "The pathway is biologically confirmed."
- "BANC and FAFB are the same network."

### 8.5 Why the roll action is weakest

The game's roll is a crouch/slide. The fly's "roll" in the literature is a
defensive escape behaviour, often a whole-body rotation, not a crouch. BANC has
flexor motor pools that could lower the body, but:

- No motor neuron is annotated as a roll command.
- No DN is annotated as a roll command.
- The behavioural literature cited by the paper covers escape, walking,
  steering, landing, halting and flight, not a game-style duck.
- The abdominal motor groups are more relevant to bending and posture than to a
  rapid crouch.

The roll mapping is therefore hypothetical, and should be labelled as such in
any Phase 4C design.

---

## 9. Missing information and limitations

1. **The local BANC resource is a paper, not a dataset.** No edgelist,
   annotation table, match table or synapse table exists locally.
2. **No per-category motor-neuron counts are published in the main text.** The
   805 total is reliable; the leg/wing/haltere/abdominal splits are not stated.
   They are derivable from `body_part_effector` but were not computed here.
3. **No muscle-level machine-readable table was read.** The paper names muscle
   groups and individual motor neuron types, but a muscle-by-muscle mapping
   requires Supplementary Data 2–5 or a metadata query.
4. **No functional validation.** No neuron was stimulated, no activity was
   recorded and no behaviour was tested.
5. **No sign validation.** Transmitters are predicted; only some are verified.
   Influence scores are unsigned.
6. **No individual-animal correspondence.** BANC and FAFB are different flies.
7. **No one-to-one ID mapping.** VNC top-1 NBLAST accuracy is 28.0%; manual
   review is required.
8. **Connectivity is sparser at the identified-neuron level.** Only 18% of BANC
   links have identified neurons on both sides, versus 41.9% in FAFB.
9. **The BANC annotation is not complete.** 531 FAFB cell types are absent;
   about 10% of unmatched neurons may be unmatchable.
10. **The BANC image is not complete.** The lamina, ocelli and ocellar ganglion
    are missing (about 9,390 cells), and the antennal nerves are damaged.
11. **The dataset is living.** Bucket files were edited after the v.888
    snapshot; version strings alone are not enough.
12. **The local FAFB version is inferred, not attested.** The manifest records
    v783 as inferred from an incomplete download filename.
13. **The Dataverse DOI is not the full dataset.** It contains only synapse
    review samples and evaluation links.
14. **No premotor identity is validated.** Pre-effector and pre-pre-effector are
    graph roles, not cell types.
15. **The influence metric is not a functional connection.** The paper says so
    explicitly.
16. **The four game actions are not biological commands.** They are game
    abstractions mapped onto candidate motor pools.
17. **No temporal motor calibration exists.** Phase 3A.5 calibrated sensory
    responses, not motor output timing.
18. **No behavioural benchmark exists for the BANC pathways.** There is no
    ground truth for "correct" left/right/jump/roll output.

---

## 10. Recommended Phase 4C architecture

### 10.1 Principle

**Do not merge BANC and FAFB.** Build a separately versioned BANC graph, keep the
FAFB artifact untouched, and compare the two only through aggregate statistics
or explicit cross-dataset annotation.

This follows the Phase 4A conclusion and the project's existing constraints:
read-only datasets, sparse graphs, no dense adjacency matrices, no plasticity,
no full-connectome experiment without approval.

### 10.2 Proposed components

| Component | Purpose | Reuses existing code? |
|---|---|---|
| `banc/` loader | Read the BANC edgelist and metadata into a sparse CSR `GraphView`-compatible object | Mirrors `brain/connectome_loader.py` and `brain/subgraph.py` |
| `banc/configs/` | Pin file hashes, thresholds, filters and version | New YAML |
| `banc/annotations.py` | Filter motor, descending, pre-effector and VNC-intrinsic populations | New; uses `banc_888_meta.feather` |
| `banc/mapping.py` | Cross-dataset type matching and FAFB ID candidate mapping | New; reads NBLAST/reviewed matches |
| `banc/motor_readout.py` | Aggregate activity in selected motor pools | New; replaces the empty `motor/action_decoder.py` stub |
| `banc/validation.py` | Count checks, bilateral checks, threshold sensitivity | New |
| `experiments/phase_4c/` | Scripted pathway probes and reports | New; reuses `BrainSimulator` |
| Tests | Deterministic loader, filter, readout and validation tests | New; does not modify existing tests |

The existing `motor/action_decoder.py` is only a docstring. Phase 4C would be its
first real implementation. That should be a separate, approved step.

### 10.3 Data acquisition plan

Minimum acquisition, with hashes to be recorded at download time:

| File | Size | Filter/use |
|---|---:|---|
| `banc_888_meta.feather` | 54.8 MiB | `super_class`, `cell_class`, `body_part_effector`, `fafb_match` |
| `banc_fafb_reviewed_matches.csv` | 6.3 MiB | Reviewed type/ID matches |
| `banc_888_edgelist_simple_v3.feather` | 342.5 MiB | Sparse graph construction |
| `backbone_proofread.parquet` | 9.8 MiB | Strict neuron list |
| `banc_888_neurotransmitter_prediction_v2.csv` | 20.1 MiB | Predicted sign prior |

Optional, only if needed:

- `banc_fafb_783_nblast.feather` (551.6 MiB) for score-level matching.
- `banc_888_edgelist_split_v3.feather` (897.0 MiB) for side/neuropil detail.
- `banc_888_proofread_influence.sqlite` (690 MiB) for influence scores.

Do not download the 16–18 GiB synapse parquets for a first pass.

### 10.4 Analysis sequence

1. **Load and validate the annotation table.**
   - Confirm row count and primary-key uniqueness.
   - Filter to neurons using `super_class` and `backbone_proofread.parquet`.
   - Report counts by `super_class`, `cell_class` and `body_part_effector`.
   - Confirm the 805 motor-neuron total and the 1,316 DN total.
2. **Load and validate the edgelist.**
   - Confirm 13,507,098 rows and no autapses.
   - Build a sparse CSR graph with `pre`, `post`, `count`.
   - Report degree and weight distributions.
3. **Select the locomotor subgraph.**
   - Motor neurons with `body_part_effector` in leg, wing, haltere, abdomen.
   - Descending neurons with `super_class = descending`.
   - Pre-effector candidates with a direct edge onto selected motor neurons.
   - VNC intrinsic neurons in the leg VNC network.
4. **Compute candidate pathways.**
   - Direct DN -> MN edges.
   - DN -> pre-effector -> MN paths.
   - Side-specific and bilateral counts.
   - Report thresholds and edge-weight distributions.
5. **Apply sign priors.**
   - Use `neurotransmitter_predicted` and `neurotransmitter_verified`.
   - Report the confidence and the fraction of unknown transmitters.
6. **Run a scripted probe.**
   - Use `BrainSimulator` with the same LIF parameters as the FAFB baseline.
   - Stimulate selected DN populations.
   - Record motor-pool activity.
   - Run twice for determinism.
7. **Report.**
   - Separate structural results from simulated results.
   - Do not call any result a behaviour.
   - Record the exact file hashes and thresholds.

### 10.5 Acceptance gates

Phase 4C should not proceed to a motor decoder unless all of the following pass:

- The BANC annotation counts reproduce the published 805 MNs and 1,316 DNs.
- The edgelist row count and autapse exclusion are confirmed.
- The selected motor pools contain the expected leg/wing/haltere categories.
- The DN -> MN pathway counts are stable across at least two thresholds.
- The candidate pools are bilateral where the anatomy requires it.
- The transmitter predictions are reported with confidence.
- A second run reproduces the first run exactly.
- The FAFB baseline and all existing tests still pass.
- No protected resource hash changes.

### 10.6 What would make Phase 4C blocked

- The metadata does not contain the expected `body_part_effector` values.
- The edgelist does not reproduce the published counts.
- The motor-neuron total cannot be reconciled with 805.
- The DN total cannot be reconciled with 1,316.
- The candidate pathways are unstable across thresholds.
- The download requires credentials that cannot be obtained.
- The file hashes do not match the documented v.888 objects.

### 10.7 Explicit non-goals

Phase 4C must not:

- Merge BANC and FAFB.
- Modify the FAFB artifact or annotations.
- Modify the BANC download.
- Train a model.
- Introduce plasticity.
- Run a full-connectome experiment without approval.
- Claim a biological motor command.
- Claim gameplay success.
- Claim that a candidate pathway is functional.

### 10.8 Verification of this Phase 4B investigation

This investigation was read-only. The following resources were hashed before and
after, and were not modified:

| Resource | SHA-256 |
|---|---|
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |
| `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` |
| `Supplemental_file1_neuron_annotations.tsv` | `b214970b55d2fbe0853bba536fdcb9e28730f4eb7ab06f600491df795da683cd` |
| `Supplemental_file2_non_neuron_annotations.tsv` | `2349fd5b4b9e53fd1b4a84aa73230bb7bebe66faa5d6a7490155aa2128861de1` |
| `references/papers/BANC/BANC-connectome.pdf` | `82082a02005c92441e7119a9cdcc3aacb209e77c81fd2667ca7712fea489df0d` |

Git state after the investigation:

- no staged files
- no commit, push or branch change
- the only new file is this report
- the pre-existing uncommitted Phase 3B/3C working-tree changes are untouched

No file under `datasets/`, `references/` or `models/` was written. No package was
installed. `best.pt` was not loaded or executed. No BANC dataset was downloaded.

---

## 11. Exact sources and citations

### 11.1 Primary BANC sources

1. Bates, A. S. et al. "Distributed control circuits across a brain-and-cord
   connectome." *Nature* 656, 957–970 (2026). DOI
   `10.1038/s41586-026-10735-w`. Open access, CC BY 4.0. Local copy:
   `references/papers/BANC/BANC-connectome.pdf`.
2. Bates, A. S. et al. "Distributed control circuits across a brain-and-cord
   connectome." bioRxiv preprint (2025). DOI `10.1101/2025.07.31.667571`.
3. Harvard Dataverse, "Publication version: Distributed control circuits across
   a brain-and-cord connectome", version 3.0, published 2026-05-27. DOI
   `10.7910/DVN/7WTH1N`. CC BY 4.0. Contains synapse review samples and
   evaluation links, not the full connectome.
4. Harvard Dataverse, preprint data version v.626. DOI `10.7910/DVN/8TFGGB`.
5. Google Storage bucket `gs://lee-lab_brain-and-nerve-cord-fly-connectome/`.
   Public. Key prefixes: `compiled_data/banc_888/`, `nblast/`,
   `neuron_annotations/v888/`, `documentation/`.
6. BossDB image data, DOI `10.60533/boss-2025-941r`.
7. BANC project portal, `https://banc.community`.
8. FlyWire Codex BANC interface, `https://codex.flywire.ai/banc`.
9. Neuroglancer BANC view, `https://ng.banc.community/view`.

### 11.2 BANC data dictionaries consulted

10. `documentation/banc_888_meta.md` — metadata columns and row count.
11. `documentation/banc_888_edgelist_simple_v3.md` — edge columns, row count,
    threshold and normalization.
12. `documentation/banc_fafb_783_nblast.md` — NBLAST reference version and
    caveats.
13. `documentation/banc_fafb_reviewed_matches.md` — reviewed match columns and
    the "not v783" caveat.
14. `documentation/fly_parts_body.md` — body-part categories.
15. `documentation/banc_supplemental_data.md` — Supplementary Data 1–10 list.
16. `README.txt` and `CHANGELOG.md` in the bucket root.
17. `documentation/codex_annotations.md`, `documentation/backbone_proofread.md`,
    `documentation/banc_v888_segmentation.md`,
    `documentation/neck_connective_y92500.md`,
    `documentation/neck_connective_y121000.md`.

### 11.3 Local FLY-SURFER sources

18. `datasets/processed/connectome.npz` — 139,255 nodes, 3,732,460 edges,
    50,666,648 summed synapses; SHA-256
    `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`.
19. `datasets/processed/nodes.csv.gz` — 139,255 local node rows.
20. `datasets/raw/annotations/classification.csv.gz` — 139,255 rows; fields
    `root_id`, `flow`, `super_class`, `class`, `sub_class`, `hemilineage`,
    `side`, `nerve`.
21. `references/source_repositories/flywire_annotations/flywire_annotations-main/flywire_annotations-main/supplemental_files/Supplemental_file1_neuron_annotations.tsv`
    — 139,248 rows, 31 columns; SHA-256
    `b214970b55d2fbe0853bba536fdcb9e28730f4eb7ab06f600491df795da683cd`.
22. `Supplemental_file2_non_neuron_annotations.tsv` — 841 rows; SHA-256
    `2349fd5b4b9e53fd1b4a84aa73230bb7bebe66faa5d6a7490155aa2128861de1`.
23. `datasets/manifest.json` — v783 inference, brain-only scope, file hashes.
24. `reports/PHASE_4A_RESOURCE_COMPATIBILITY_AUDIT.md` — prior audit and
    candidate-pool counts.
25. `sensory/game_state.py` — lane, jump and roll state model.
26. `brain/brain_simulator.py`, `brain/subgraph.py`,
    `brain/connectome_loader.py` — simulation and graph interfaces.
27. `motor/action_decoder.py` — currently a docstring stub.

### 11.4 Comparative and methodological citations

28. Dorkenwald, S. et al. "Neuronal wiring diagram of an adult brain." *Nature*
    634, 124–138 (2024). FAFB reference.
29. Schlegel, P. et al. "Whole-brain annotation and multi-connectome cell typing
    of Drosophila." *Nature* 634, 139–152 (2024). FAFB annotation reference.
30. Dorkenwald, S. et al. "FlyWire: online community for whole-brain
    connectomics." *Nature Methods* 19, 119–128 (2022).
31. Dorkenwald, S. et al. "CAVE: Connectome Annotation Versioning Engine."
    *Nature Methods* 22, 1112–1120 (2025).
32. Costa, M., Manton, J. D., Ostrovsky, A. D., Prohaska, S. & Jefferis, G. S.
    "NBLAST: rapid, sensitive comparison of neuronal structure and construction
    of neuron family databases." *Neuron* 91, 293–311 (2016).
33. Azevedo, A. et al. "Connectomic reconstruction of a female Drosophila
    ventral nerve cord." *Nature* 631, 360–368 (2024). FANC reference.
34. Lesser, E. et al. "Synaptic architecture of leg and wing premotor control
    networks in Drosophila." *Nature* 631, 369–377 (2024).
35. Phelps, J. S. et al. "Reconstruction of motor control circuits in adult
    Drosophila using automated transmission electron microscopy." *Cell* 184,
    759–774 (2021). MANC reference.
36. Takemura, S.-Y. et al. "A connectome of the male Drosophila ventral nerve
    cord." *eLife* 13, RP97769 (2024).
37. Marin, E. C. et al. "Systematic annotation of a complete adult male
    Drosophila nerve cord connectome reveals principles of functional
    organisation." *eLife* 13, RP97766 (2024).
38. Berg, S. et al. "Sexual dimorphism in the complete connectome of the
    Drosophila male central nervous system." *Cell* 189, 5504–5526 (2026). DOI
    `10.1016/j.cell.2026.08.015`.
39. Hoeller, S. et al. "The organization of visual pathways in the Drosophila
    brain." *Cell* 189, 5552–5570 (2026). DOI `10.1016/j.cell.2026.08.014`.
40. Braun, J., Hurtak, F., Wang-Chen, S. & Ramdya, P. "Descending networks
    transform command signals into population motor control." *Nature* 630,
    686–694 (2024).
41. Matsliah, A. et al. "Uncovering sex differences in the Drosophila ventral
    nerve cord through connectome alignment." bioRxiv (2026). DOI
    `10.64898/2026.06.14.732053`.
42. Bates, A. S. et al. "bancr: R client access to the Brain And Nerve Cord
    connectome." Cited in the BANC paper as reference 324.

### 11.5 Citation notes

- The BANC paper's reference list cites the Male CNS work as a 2025 bioRxiv
  preprint. The published *Cell* version is newer. Cite the published version
  when referring to the dataset, and note the preprint when quoting the BANC
  paper's own reference.
- Page numbers for the BANC paper are 957–970. The main text page numbers cited
  in this report were taken from the PDF footers.
- The Dataverse version is 3.0, published 2026-05-27. The paper's data
  availability statement points to the same DOI.
- The BANC paper describes analyses on v.888 but its bucket files have been
  updated after the snapshot. Do not cite a bucket file as "v.888" without its
  hash.

---

## Appendix A — BANC file inventory used in this investigation

The following files were identified through the public bucket listing and the
data dictionaries. None was downloaded.

| Path | Bytes | Used for |
|---|---:|---|
| `compiled_data/banc_888/banc_888_meta.feather` | 57,503,026 | Annotation fields and counts |
| `compiled_data/banc_888/banc_888_edgelist_simple_v3.feather` | 359,161,658 | Edge semantics and row count |
| `compiled_data/banc_888/banc_888_edgelist_simple_v2.feather` | 305,250,378 | v2 comparison |
| `compiled_data/banc_888/banc_888_edgelist_split_v3.feather` | 940,605,786 | Side/neuropil detail |
| `compiled_data/banc_888/banc_888_edgelist_split_v2.feather` | 847,546,546 | v2 detail |
| `nblast/banc_fafb_783_nblast.feather` | 578,411,098 | FAFB v783 NBLAST |
| `nblast/banc_fafb_reviewed_matches.csv` | 6,581,434 | Reviewed FAFB matches |
| `nblast/banc_manc_v1.2.1_nblast.feather` | 121,800,002 | MANC NBLAST |
| `nblast/banc_hemibrain_v1.2.1_nblast.feather` | 198,913,234 | Hemibrain NBLAST |
| `nblast/banc_fanc_1116_nblast.feather` | 144,112,498 | FANC NBLAST |
| `nblast/banc_malecns_v0.9_nblast.feather` | 912,369,066 | Male CNS NBLAST |
| `neuron_annotations/v888/backbone_proofread.parquet` | 10,316,976 | Strict proofread list |
| `neuron_annotations/v888/codex_annotations.parquet` | 74,350,281 | Long-form annotations |
| `neuron_annotations/v888/codex_annotations_flat_table_260520.csv` | 39,303,076 | Flat annotation fallback |
| `neuron_annotations/v888/somas_v1.parquet` | 5,350,459 | Soma positions |
| `neuron_annotations/v888/peripheral_nerves.parquet` | 629,173 | Nerve seeds |
| `neuron_annotations/v888/neck_connective_y92500.parquet` | 139,052 | Neck plane |
| `neuron_annotations/v888/neck_connective_y121000.parquet` | 85,778 | Neck plane |
| `compiled_data/banc_888/banc_888_neurotransmitter_prediction_v2.csv` | 21,107,592 | Predicted transmitters |
| `compiled_data/banc_888/banc_888_proofread_influence.sqlite` | 723,705,856 | Influence scores |
| `compiled_data/banc_888/banc_888_betweenness_all_to_all_v3.csv` | 7,027,171 | Betweenness |
| `compiled_data/banc_888/banc_888_betweenness_afferent_to_efferent_v3.csv` | 6,811,957 | Betweenness |
| `compiled_data/banc_888/banc_888_cns_network_spectral_clustering_v3.csv` | 6,062,964 | CNS network membership |
| `compiled_data/banc_888/banc_888_synapses_v2_enriched.parquet` | 17,146,564,854 | Not needed for first pass |
| `compiled_data/banc_888/banc_888_synapses_v3_enriched.parquet` | 19,733,123,829 | Not needed for first pass |

## Appendix B — local query reproducibility

The local FAFB baseline figures in this report were recomputed with the Python
standard library and NumPy, using the protected artifact:

1. Load `datasets/processed/connectome.npz`.
2. Read `root_id` and `super_class` from
   `Supplemental_file1_neuron_annotations.tsv`.
3. Map `root_id -> node index`.
4. Count `super_class == 'descending'` and `super_class == 'motor'`.
5. For DN -> MN edges, select edges where `edge_src` is descending and
   `edge_dst` is motor.
6. For central MN partners, index `in_indptr` and `in_edge_idx`, exclude motor
   sources, and select `super_class == 'central'`.

The recomputed values are:

```text
nodes                 139255
edges                 3732460
synapses              50666648
descending neurons    1303
motor neurons         110
DN -> MN edges        2355
DNs with motor target 519
MNs with DN input     90
central MN partners   1174
```

These match the Phase 4A audit. No random seed is involved. The comparison is
deterministic.

## Appendix C — glossary of BANC annotation fields

| Term | Meaning in this report |
|---|---|
| Effector | A neuron that leaves the CNS or targets a muscle, endocrine organ or viscera |
| Motor neuron | A directly annotated effector that innervates muscle |
| Endocrine/visceral | An effector that is not a classical motor neuron |
| Pre-effector | A neuron directly presynaptic to an effector (graph role) |
| Pre-pre-effector | A neuron directly presynaptic to a pre-effector (graph role) |
| Premotor candidate | A graph-derived candidate, not a validated identity |
| DN | Descending neuron, brain to VNC |
| AN | Ascending neuron, VNC to brain |
| VNC intrinsic | A neuron contained within the VNC |
| Body-part effector | The body part targeted by an effector |
| NBLAST | Morphological similarity score between neurons |
| Reviewed match | A manually reviewed cross-dataset match |
| Materialization | A CAVE snapshot that fixes IDs and annotations for analysis |
| Influence score | An unsigned, normalized graph-distance-derived score; not a functional connection |
