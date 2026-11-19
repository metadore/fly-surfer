# Phase 4 — Missing-Resource Inventory

**Date:** 2026-11-17
**Rule followed:** every item below was checked against the local repository
before being called missing. No URL was invented; where the repository records
no download page, this report says so. Nothing was downloaded in this task.

---

## 1. Method

Local resources actually inspected:

| Resource | Location | Present? |
|---|---|---|
| BANC metadata (v888) | `datasets/external/banc_v88/raw/metadata/banc_888_meta.feather` | Yes |
| BANC edgelist (v888, `edgelist_simple_v2`) | `datasets/external/banc_v88/raw/connectivity/…v2.feather` | Yes |
| BANC backbone proofread annotations | `datasets/external/banc_v88/raw/annotations/backbone_proofread.parquet` | Yes |
| BANC neurotransmitter predictions | `datasets/external/banc_v88/raw/annotations/…prediction_v2.csv` | Yes |
| BANC↔FAFB reviewed matches | `datasets/external/banc_v88/raw/cross_dataset_matches/…csv.gz` | Yes |
| Derived BANC graphs t1/t5/t10 | `datasets/processed/banc_v888/banc_graph_t*.npz` | Yes |
| BANC paper | `references/papers/BANC/BANC-connectome.pdf` | Yes |
| FAFB v783 connectome + nodes | `datasets/processed/connectome.npz`, `nodes.csv.gz` | Yes |
| Phase 4 decoder, populations, selection, controller | `motor/`, `environment/` | Yes |
| Software dependencies | Python 3.13, numpy 2.3.4, pandas, pyarrow, pytest | Yes (test suite runs) |

Because all five BANC tables and the derived graph are present, the analysis in
Phase 4E/4F/4G/4H is reproducible locally. The gaps below are **scientific
evidence gaps**, not missing files for the existing pipeline.

---

## 2. Inventory

### R1 — Roll motor population / roll-command evidence

| Field | Value |
|---|---|
| Category | Neuron classification; behavioural evidence |
| Why needed | The ROLL channel has no annotation-derived population. Without it, ROLL cannot be decoded without inventing a mapping. |
| Requirement | §6 “whether ROLL/DUCK has sufficient evidence”; the optional ROLL game channel |
| Essential? | **Essential for ROLL only; optional for the nine Phase 4 requirements** (which name left/right/jump) |
| Authoritative source | No such annotation is present in BANC v888 metadata. The BANC paper (DOI `10.1038/s41586-026-10735-w`, cited locally in `reports/PHASE_4A_RESOURCE_COMPATIBILITY_AUDIT.md`) does not define a roll motor pool. A source would have to come from a future BANC release or a dedicated motor-program study. |
| Expected format | Node-level annotation with a rule that identifies roll/crouch motor neurons, plus a citation; ideally an effector or muscle-target field |
| Access | Unknown; no public release is documented for this specific mapping |
| Local substitute | **None.** Flexor pools are not a roll population and were not substituted. |

### R2 — Duck / crouch motor population

Same structure as R1. The controlled game has no duck action either
(`environment/action_adapter.py` maps DUCK to `NO_ACTION` with a recorded
reason). **Essential for DUCK only; optional for Phase 4. No substitute used.**

### R3 — Target-specific functional sign of descending and premotor synapses

| Field | Value |
|---|---|
| Category | Connectomic/physiological evidence |
| Why needed | The simulator assigns excitatory/inhibitory sign from the presynaptic predicted transmitter. 683,100 of 1,535,710 t5 edges are signed; unknown edges are **excluded**. Any claim that a structural path can drive a motor neuron depends on this assumption. |
| Requirement | Requirement 9 (sensory-to-motor function); Phase 7 failure analysis |
| Essential? | **Essential** to convert the current controlled negative into a statement about the connectome’s capacity |
| Authoritative source | No per-edge sign/conductance dataset exists locally. Candidate sources are the BANC transmitter predictions already present (predicted, not measured) and published physiology; neither supplies target-specific sign for all edges. |
| Expected format | Edge-level sign or conductance, keyed by `(pre_banc_id, post_banc_id)` or by cell type; units and measurement method recorded |
| Access | Not established; must be verified from the BANC paper’s data-availability statement before acquisition |
| Local substitute | Predicted transmitter only; already in use and explicitly labelled a prior |

### R4 — Physiological calibration for motor recruitment

| Field | Value |
|---|---|
| Category | Experimental evidence; model calibration data |
| Why needed | The first-hop peak depolarisation is 6.93 mV short of threshold. Whether that is realistic cannot be decided from structure alone: LIF capacitance, leak, threshold, synaptic time constant, weight transform (`count**0.75`, 5 pA scale, 300 pA cap) and 1 ms delay are model choices. |
| Requirement | Requirement 9, and any conclusion of the form “the pathway cannot recruit motor neurons” |
| Essential? | **Essential** for a biological conclusion; not needed for the software loop |
| Authoritative source | No dataset in the repository measures BANC neuron input resistance, rheobase, PSP amplitude or synapse conductance. Published Drosophila motor-neuron physiology would be the class of source. |
| Expected format | Per-cell-type passive properties and per-synapse/connection strength, with temperature and preparation metadata |
| Access | Must be selected and licensed explicitly; nothing was acquired |
| Local substitute | **None.** Tuning the existing parameters to make the circuit fire is explicitly forbidden and was not done. |

### R5 — Ground truth for game-feature → sensory-neuron mapping

| Field | Value |
|---|---|
| Category | Annotations; scientific reference |
| Why needed | The 232-neuron sensory set is assigned to game features by a declared hypothesis (`PHASE_4H4`), not a measured visual pathway. Any biological claim about “the fly seeing a train” depends on this. |
| Requirement | Requirements 1–4 in the biological sense; Requirement 9’s interpretation |
| Essential? | **Essential for the biological claim; optional for the software pipeline** |
| Authoritative source | No measured feature→neuron map for these game features exists in the repository or, to the project’s knowledge, in public data. Fly visual-system cell typing exists, but not a mapping to this game. |
| Expected format | Table of BANC cell types → visual feature/location with a citation and confidence |
| Access | Research question, not a download |
| Local substitute | Annotation-based pools (e.g. `visual_projection`, `optic_lobe_intrinsic`), explicitly labelled a computational convention |

### R6 — Behavioural/functional validation of action labels

| Field | Value |
|---|---|
| Category | Experimental evidence |
| Why needed | Passing decoder tests does not show that LEFT/RIGHT/JUMP correspond to lane changes or jumps. No behaviour-linked neural dataset is available. |
| Requirement | Requirement 9 and the Phase 4 goal (“game actions” as opposed to “pool labels”) |
| Essential? | Optional for Phase 4’s software; essential to call the mapping biologically valid |
| Authoritative source | Would require a study linking identified BANC/Drosophila neurons to turning, jumping or rolling behaviour. Not present locally. |
| Expected format | Neuron/cell-type identifiers, behaviour, stimulation or recording protocol, effect sizes |
| Access | Not established |
| Local substitute | Literature-role statements in `PHASE_4B` are cited as **candidate** evidence only |

### R7 — Completeness of motor annotation

| Field | Value |
|---|---|
| Category | Neuron classification; annotations |
| Why needed | 197 of 805 motor neurons have no `peripheral_target_type`; 414 are outside the LEFT/RIGHT/JUMP rules; 8 of 20 tergotrochanter candidates carry `LR_TYPE_CONFLICT`; only 30/805 have a verified transmitter. |
| Requirement | Requirement 2 and 3 (population identification) — coverage, not existence |
| Essential? | Optional; the current mapping is complete for the neurons it claims |
| Authoritative source | A later BANC materialization or targeted annotation effort |
| Expected format | Same node-table columns, extended fill |
| Access | Would follow the same BANC release channel |
| Local substitute | None needed; gaps are reported, not filled |

### R8 — Premotor/VNC intrinsic cell-type labels

| Field | Value |
| Category | Neuron classification |
| Why needed | Two-hop pathway counts depend on how “VNC intrinsic” is defined (12,850 strict vs 24,647 broad). Cell-type labels would make “premotor” a classification rather than a region/`super_class` heuristic. |
| Requirement | Requirement 1 (pathway investigation), depth only |
| Essential? | Optional |
| Authoritative source | BANC cell typing / VNC cell-type work; not in this export |
| Expected format | Node-level cell type and neurotransmitter with provenance |
| Access | External release |
| Local substitute | `super_class`/region rules, reported with both definitions |

### R9 — Newer BANC edgelist materialization (`edgelist_simple_v3`)

| Field | Value |
|---|---|
| Category | Dataset version |
| Why needed | The local graph is built from `edgelist_simple_v2` (18,552,546 synapses at t5). `PHASE_4B` cites a v3 edgelist with 13,507,098 directed edges and 259,409,001 synaptic links. Results are pinned to v2 and cannot be claimed for v3 without rebuilding. |
| Requirement | Reproducibility; comparability with current releases |
| Essential? | Optional — v2 is internally consistent and hash-verified |
| Authoritative source | BANC release channel; download page not recorded in-repo |
| Expected format | Same edgelist schema (`pre`, `post`, `count`, `norm`, …) |
| Access | Must be re-verified; do not assume the v2 checksums apply |
| Local substitute | v2, used and pinned |

### Software dependencies

No Phase 4 software dependency is missing. The focused suite runs on the
installed environment (Python 3.13, numpy 2.3.4, pandas, pyarrow, pytest).
Phase 4 does not require PyTorch; the Phase 8 tests that do were run separately.

---

## 3. Essential vs optional

| Resource | Essential for | Optional for |
|---|---|---|
| R3 functional sign | Biological interpretation of the sensory→motor result | Software loop |
| R4 physiological calibration | Any “cannot recruit” / “can recruit” conclusion | Deterministic replay, decoder mechanics |
| R5 sensory ground truth | Biological sensory claim | End-to-end pipeline |
| R1 / R2 | ROLL / DUCK channels | The nine core requirements |
| R6 | Behavioural validity of labels | Decoder mechanics |
| R7 / R8 / R9 | Coverage/version depth | Current results within their stated version |

---

## 4. What acquisition would and would not change

Acquiring R3 and R4 would let the project test **whether** the connectome’s
sign and strength assumptions can recruit motor pools, without tuning. Until
then, the only honest statement is the controlled negative: *under the declared
sign policy, weight transform and LIF parameters, the chosen sensory drive does
not produce a postsynaptic spike.*

Acquiring R1/R2 would add ROLL/DUCK channels. It would not validate LEFT/RIGHT/
JUMP.

Acquiring R5 would let the project call the sensory mapping measured. It would
not by itself show that the motor output is a command.

---

## 5. Stop rule

Dependent work stops rather than substituting fabricated data:

- ROLL and DUCK remain unimplemented and execute `NO_ACTION` with a recorded
  reason.
- The sensory feature map remains a declared hypothesis.
- The Phase 7 result remains a controlled negative.
- No placeholder neurons, proxy populations or invented annotations were added
  to close any item in this inventory.
