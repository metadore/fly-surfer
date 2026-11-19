# Phase 4 — Anatomical Motor-Pathway Report

**Date:** 2026-11-17
**Scope:** Consolidated anatomical evidence for the original Phase 4 task set
(“Convert neural activity into game actions”), tasks 1–3: descending pathways,
neuronal populations and motor annotations.
**Status:** descriptive report only. No dataset, graph artifact, frozen result,
Phase 8 protocol or simulation parameter was modified to produce it.
**Upstream sources:** `reports/PHASE_4B_LOCOMOTOR_MOTOR_PATHWAY_INVESTIGATION.md`
(literature and resource audit), `reports/PHASE_4E_MOTOR_POPULATION_AND_PATHWAY_ANALYSIS.md`
and its JSON (recomputed graph analysis), `reports/PHASE_4D_BANC_GRAPH_CONSTRUCTION.md`
(graph construction and provenance).

---

## 1. What is measured and what is assumed

| Layer | Status in this project | Consequence for Phase 4 |
|---|---|---|
| Directed BANC adjacency at pair level | Measured structure, thresholded from exported synapse counts | Legitimate basis for “A projects to B” statements |
| Synapse count per pair | Measured, size-filtered at ≥ 5 (`edgelist_simple_v2`) | Used only as a monotone structural weight, never as a conductance |
| `super_class`, `side`, `body_part_effector`, `peripheral_target_type`, cell type | Published expert annotation | Basis for the LEFT/RIGHT/JUMP decoder populations |
| Predicted neurotransmitter | Prediction, not measurement | Supports a sign *prior*; 30 of 805 motor neurons have a verified transmitter |
| Excitatory/inhibitory effect at a given synapse | **Assumption** (`sign_policy`, unknown edges excluded) | Connectivity does not establish physiological sign |
| LIF membrane, synaptic time constants, current transform | **Model assumption** | Threshold crossing is model behaviour, not fly behaviour |
| Activity produced in simulation | **Model output** | Not a recording and not evidence of biological function |
| LEFT / RIGHT / JUMP labels | **Computational decoder labels** | Not identified biological motor commands |

**Structural connectivity does not prove physiological function.** Every numeric
statement below is structural unless it is explicitly labelled as an annotation
count.

---

## 2. Resource and separation facts

- BANC materialization **v888**, April 16 2026 snapshot, v2 synapse model rolled
  up at postsynapse size ≥ 5 (`datasets/processed/banc_v888/banc_manifest.json`).
- Local source tables (immutable, SHA-256 recorded in
  `reports/PHASE_4D_BANC_GRAPH_CONSTRUCTION.md`): metadata
  (`banc_888_meta.feather`), edgelist (`banc_888_edgelist_simple_v2.feather`),
  backbone proofread annotations, neurotransmitter predictions and
  BANC↔FAFB reviewed matches.
- BANC is a **different individual female fly** from the FAFB v783 brain used by
  the sensory layer. No node, edge or CSR index is shared; a test asserts the
  node sets are disjoint. No FAFB brain neuron is substituted for a BANC VNC
  neuron anywhere in Phase 4.
- The paper behind the resource is cited locally in
  `reports/PHASE_4A_RESOURCE_COMPATIBILITY_AUDIT.md` §6: *“Distributed control
  circuits across a brain-and-cord connectome”*, Nature 656 (27 Aug 2026),
  DOI `10.1038/s41586-026-10735-w`, open access, CC BY. The repository records
  the DOI, not a download URL; the acquisition route must be re-verified from
  that paper’s data-availability statement.

**Graph scale (threshold 5):** 172,433 nodes, 1,535,710 directed edges,
18,552,546 summed synapses.

---

## 3. Population counts

| Population | Count | Definition |
|---|---:|---|
| Descending neurons | 1,316 | Annotated brain-to-VNC projection neurons |
| Motor neurons | 805 | `super_class == motor` |
| Ascending neurons | 1,849 | VNC-to-brain projection neurons |
| VNC intrinsic | 12,850 | `super_class == intrinsic` within the VNC region |
| VNC region nodes | 27,778 | All nodes assigned to the VNC region |
| Left motor neurons | 392 | `side == left` |
| Right motor neurons | 413 | `side == right` |
| Tergotrochanter extensor candidates | 20 | `peripheral_target_type == tergotrochanter_extensor_muscle` |
| Unassigned to LEFT/RIGHT/JUMP | 414 | Motor neurons outside the three decoder rules |

Motor neurons by effector (top groups): abdomen 168, front leg 139, middle leg
126, hind leg 126, wing 64, neck 49, proboscis 35, haltere 27. All 805 are
`proofread_true`; **197 have no `peripheral_target_type`**; **30 have a verified
neurotransmitter**; every motor neuron has `body_part_effector` and `side`
populated.

---

## 4. Descending → motor direct connectivity

| Threshold | DN→MN edges | Synapses | DNs with a motor target | Motor neurons with DN input | MNs without DN input | DNs without motor target |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 17,745 | 154,914 | 1,095 | 772 | 33 | 221 |
| **5 (primary)** | **6,409** | **134,551** | **753** | **638** | **167** | **563** |
| 10 | 3,822 | 117,496 | 599 | 525 | 280 | 717 |

At threshold 5, 6,409 of the 1,535,710 t5 edges are DN→MN (0.42 %).
Out-degree of connected DNs is highly skewed: mean 8.5, median 4,
maximum 144. Consequently **563 of 1,316 DNs have no motor target at all**, and
**167 of 805 motor neurons receive no direct descending input**.

The threshold is not cosmetic. Moving from 1 to 5 retains 36.1 % of DN→MN edges
but 86.9 % of their synapses; moving to 10 retains 21.5 % of edges and 75.8 % of
synapses. The t5 graph is a sparse, high-synapse backbone. This is a simulation
policy, consistent with the FAFB layer, not a claim about real synaptic
efficacy.

---

## 5. Two-hop pathway structure

Intermediates were defined two ways; both are reported, neither is treated as a
validated premotor class.

| Intermediate set | Size | DN→intermediate edges | Intermediate→MN edges | Enumerated 2-hop paths | Unique DN→MN pairs |
|---|---:|---:|---:|---:|---:|
| VNC intrinsic only (`intrinsic`) | 12,850 | 33,111 | 45,787 | 213,658 | 94,928 |
| Broad VNC region | 24,647 | 43,241 | 52,275 | 262,734 | 119,620 |

Two-hop enumeration establishes that paths exist at the chosen structural
threshold. It does **not** establish that a given path is excitatory,
inhibitory, disynaptic in the living animal, or used for a particular movement.
Path counts depend on the intermediate definition and are reported as
descriptive, with no null model.

---

## 6. Lateral organisation

| Quantity (threshold 5) | Value |
|---|---:|
| Same-side DN→MN edges | 2,679 (41.9 % of known-side) |
| Cross-side DN→MN edges | 3,722 (58.1 %) |
| Edges with unknown side at one endpoint | 8 |
| Motor neurons with ipsilateral-only input | 51 (6.3 %) |
| Motor neurons with contralateral-only input | 120 (14.9 %) |
| Motor neurons with bilateral input | 467 (58.0 %) |
| Motor neurons with no direct input | 167 (20.7 %) |

Cross-side input is **more common than same-side input**, and the dominant input
pattern for every leg effector is bilateral. This is important negative
evidence for the simplest possible mapping: the descending drive to leg motor
neurons is not organised as a clean ipsilateral left-pool / right-pool command.
Any claim that the LEFT or RIGHT decoder population is the biological substrate
of a lateral turn would require evidence this analysis does not have.

---

## 7. Per-action anatomical evidence

| Game action | Structural support | Annotation support | Evidence class | What is missing |
|---|---|---|---|---|
| Left lane change | Leg motor pools exist on both sides; numerous DN→leg paths | `side == left` + leg effector | Anatomically identified neurons; candidate pathway | No identified left-command DN; left-pool specificity is not supported (cross-side majority) |
| Right lane change | Mirror of left | `side == right` + leg effector | Anatomically identified neurons; candidate pathway | Same |
| Jump | Tergotrochanter (jump-extending) motor neurons; giant-fibre DN candidates | `peripheral_target_type == tergotrochanter_extensor_muscle` | Anatomically identified motor neurons; candidate DN pathway | Escape-reflex biology, not a precision vault; bilateral coordination unresolved; 8 of 20 candidates carry `LR_TYPE_CONFLICT` |
| Roll / duck | Flexor pools exist; postural-control DNs exist | **No roll/duck annotation in this export** | Hypothesis only | No annotated roll/crouch motor population; game roll ≠ fly escape roll |

Tergotrochanter stability: at t1/t5/t10 the 20 candidates all retain direct and
two-hop DN input (direct DN edges 350 → 139 → 81). The pool is structurally
well connected; that is not functional validation.

---

## 8. Phase 7 sensory-entry point is not the anatomical weak point by itself

The 232 sensory neurons used by the game encoder were checked against the same
graph (`PHASE_4H4`): they have **662 signed outgoing edges** to **608 targets**,
of which 607 are non-stimulated. Nine first-hop targets are descending neurons;
four motor neurons appear at the second signed hop. The structural route from
the chosen sensory set toward the motor system exists but is thin and
polysynaptic. Section 5 of
`reports/PHASE_4_PHASE_7_MOTOR_OUTPUT_FAILURE_ANALYSIS.md` shows where the
simulated activity actually stops.

---

## 9. Findings that constrain the remaining Phase 4 work

1. **The motor neurons exist and are annotated.** BANC supplies precisely the
   limb motor material that FAFB lacks.
2. **The descending→motor graph is sparse and bilateral.** Direct input reaches
   638/805 motor neurons; 20.7 % have none; cross-side edges outnumber same-side
   edges.
3. **Annotation supports LEFT/RIGHT/JUMP labels only as pools**, not as commands.
4. **No annotation in this export supports ROLL or DUCK.** No proxy was invented.
5. **Sign is an assumption.** 683,100 of 1,535,710 edges are signed under the
   verified-only policy; unknown edges are excluded. This is the dominant reason
   a simulation can be structurally connected yet functionally silent.
6. **No physiological ground truth was acquired.** There is no dataset in the
   repository that maps these 5 game actions onto identified BANC neurons, and
   no dataset that supplies per-edge conductance.

---

## 10. Verdict for Phase 4 tasks 1–3

**COMPLETE WITH LIMITATIONS.**

- Descending pathways: investigated and quantified (4B, 4E).
- Neuronal populations: identified from published annotations, with explicit
  exclusions (4E, 4F).
- Motor annotations: audited; coverage and gaps quantified (4E).

The limitations are evidence limitations, not implementation gaps: the
annotation catalogue cannot distinguish a “lane-change command” from a motor
pool, and the structural tables carry no sign, conductance or physiological
validation. Those limits are carried forward unchanged into the decoder,
controller and the Phase 7 analysis.
