# FLY-SURFER

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24506776.svg)](https://doi.org/10.5281/zenodo.24506776)

Connectome-derived spiking neural simulation of a fruit fly brain driving a game
controller, with a fully documented negative result.

FLY-SURFER asks one question: can a connectome-derived *Drosophila melanogaster*
network, implemented as a spiking neural simulation with learning mechanisms,
transform visual game information into functional motor commands in a controlled
game environment?

The project built the whole chain: game-frame perception, sensory encoding,
leaky integrate-and-fire (LIF) simulation over the FlyWire FAFB and BANC sparse
connectomes, annotation-defined motor decoding, a closed-loop game bridge,
reward-modulated three-factor plasticity, trainable linear readouts, an
information-theoretic analysis, a pre-registered Phase 8 protocol, and two
executed pilots. The chain runs end to end and is reproducible.

It does not play the game. Across every closed-loop and pilot configuration the
motor populations produced **zero spikes**, so the decoder returned NO_ACTION on
every decision. The failure is localised: first-hop synaptic current reaches the
post-sensory targets but peaks at **−56.926 mV** against a **−50 mV** threshold,
a **6.926 mV** shortfall, and no second-hop current is generated. The Phase 6
information analysis found no confirmatory gain from plasticity (mean paired
difference **−0.0863 bits**, exact two-sided sign-flip p = 0.125, Holm-adjusted
p = 0.25). The recorded answer is therefore a **qualified negative at this
operating point**, not a claim about what the connectome can or cannot support.

The connectome supplies **measured structure**; the membrane, synapses,
transmitter signs and input protocol are **explicit model assumptions**.
Simulated activity is not a recording and does not reproduce real fly neural
activity.

| Document | Location |
|---|---|
| Research paper (PDF, 157 pages) | [`research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.pdf`](research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.pdf) |
| Research paper (Word / Markdown) | `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.docx`, `.md` |
| Claim-to-file evidence register | [`research_paper/SOURCE_AND_EVIDENCE_REGISTER.md`](research_paper/SOURCE_AND_EVIDENCE_REGISTER.md) |
| Paper validation report | [`research_paper/RESEARCH_PAPER_VALIDATION_REPORT.md`](research_paper/RESEARCH_PAPER_VALIDATION_REPORT.md) |
| Data provenance and audit | [`datasets/README.md`](datasets/README.md), `datasets/manifest.json` |
| Licences | [`LICENSE`](LICENSE) (MIT, code), `research_paper/LICENSE` (CC BY 4.0, paper), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) |

The paper is licensed CC BY 4.0, © 2026 metadore. Original source code is MIT.
Third-party datasets and model weights keep their own licences (see §8).

## Research Publication

The research paper accompanying this repository is published on Zenodo.

**Teaching a Fruit Fly Brain to Play Subway Surfers Through Connectome-Based
Neural Simulation: Architecture, Learning Mechanisms, Experimental Evaluation,
and Motor-Output Limitations**

- **Author:** Pratha Kharsan
- **Version:** 1.1
- **Publication date:** 24 November 2026
- **Publisher:** Zenodo
- **Resource type:** Preprint
- **Version-specific DOI:** [10.5281/zenodo.24506776](https://doi.org/10.5281/zenodo.24506776)
- **Concept DOI (all versions):** [10.5281/zenodo.24506775](https://doi.org/10.5281/zenodo.24506775)
- **Zenodo record and paper download:** <https://doi.org/10.5281/zenodo.24506776>
- **Licence (paper content):** CC BY 4.0

The version-specific DOI identifies this exact release (v1.1); the concept DOI
identifies the work across versions. Use the version-specific DOI when citing
these results.

### Citation

> Kharsan, P. (2026). *Teaching a Fruit Fly Brain to Play Subway Surfers Through
> Connectome-Based Neural Simulation: Architecture, Learning Mechanisms,
> Experimental Evaluation, and Motor-Output Limitations* (Version 1.1).
> Zenodo. <https://doi.org/10.5281/zenodo.24506776>

Publication does not change the recorded result: the simulated motor populations
produced zero spikes at the operating point, so this is a qualified negative
finding, not a demonstration of game-playing or of biological learning. See §11.

## 1. What the project did

| Phase | What was built | Principal recorded outcome |
|---|---|---|
| 0 | Audit of 15 FlyWire files: schemas, nulls, IDs, checksums | 29,231,539 rows; 139,255 IDs, 0 outside the reference; no self-connections; pair-level ≥5-synapse filter identified |
| 1 | Validated CSR connectome artifact | 139,255 neurons, 3,732,460 directed pairs, 50,666,648 summed synapses; treated read-only |
| 2 | LIF neuron, sparse synapse, sampler, recorder, engine, experiment | 800-neuron connected sample, 1,564 spikes, 79 active neurons, stability checks pass |
| 2.5 | Scalability and memory benchmark in isolated processes | 800 → 139,255 neurons; full connectome 400 steps in 2.92 s, 270.8 MB peak; all stability checks pass |
| 3A | Game state, population encoders, sensory mapping, calibration | 14-feature FAFB encoder; calibrated three-level distance code from nine observations |
| 3B | YOLO11n ONNX detector, tracking, temporal event encoder, replay | 14 classes, 2,328 images, 8,666 boxes; 100-frame replay emits 215 events; grouped split, no independent test set |
| 3C | Causal control, lane encoding, temporal acceptance, four-neuron validation | Controlled stimulus/analysis machinery; frozen pre-registration; recorded limitations |
| 4A–4H | BANC brain + VNC graph, motor inventory, decoder, propagation, random controls, sensory round trip | 172,433 endpoints, 1,535,710 edges, 805 motor neurons; first hop propagates, second hop does not |
| 5 | Reward, eligibility traces, three-factor plasticity, synthetic cued-response task | Success 0.795 (fixed) → 0.945 (plastic) on a synthetic task; not a connectome result |
| 6 | Information-theoretic analysis of archived runs (entropy, mutual information, permutation tests) | No supported cue-to-action information gain: −0.0863 bits, p = 0.125, Holm 0.25 |
| 7 | Closed-loop game bridge and demonstration | 213 decisions, 2,852 spikes, all from stimulated sensory neurons, 0 motor spikes, all NO_ACTION |
| 8 | REV4 pre-registered protocol, Pilot 1, D5/D6 training, Pilot 2-C | Pilot 1: 9 episodes, 3,784 decisions, 0 motor spikes. D5/D6: 6 artifacts, 120 episodes, 0 motor spikes, 0 weight change. Pilot 2-C: 54/54 rows, 8/8 descriptive claims certified, C1–C4 not estimated |
| Paper | 21 chapters, 39 figures, 24 main tables, 31 references, 189-row evidence register | Version 1.1, 24 November 2026 |

Two connectomes are used and never merged. FAFB supplies the brain-only graph
for perception, simulation, plasticity and information analysis. BANC supplies
the brain + ventral nerve cord graph with limb motor neurons for motor decoding
and every Phase 8 execution. No root identifier is transferred between them.

## 2. Principal recorded results

| Result | Value | Where |
|---|---|---|
| Phase 4G positive control (motor pools driven directly) | 1,296 spikes, 492 motor spikes, 82 motor neurons, JUMP ×4 | `experiments/results/phase_4g/` |
| Phase 4H.4 first hop (BANC) | 232 stimulated, 171 active, 3,562 spikes, 473/607 non-stimulated targets receive current | `reports/` Phase 4H.4 |
| Peak depolarisation vs threshold | −56.926 mV vs −50 mV, shortfall 6.926 mV; 0 second-hop targets; 0/805 motor neurons spike | bottleneck measurements |
| Signed BANC t5 edges under the declared sign policy | 683,100 / 1,535,710 (44.48%); the rest are not simulated | Phase 4G.2 |
| Phase 6 complete-wiring contrast | −0.0863 bits, 95% interval [−0.1751, 0.0052], exact p = 0.125, Holm 0.25 | `experiments/results/phase_6/` |
| Phase 7 closed loop | 213 decisions, 2,852 spikes, 0 motor spikes, reward 3.12 | Phase 7 record |
| Pilot 1 | 9 episodes, 3,784 decisions, 126,135 neural steps, 73,880 spikes, 0 motor spikes, reward 47.75 | `experiments/results/phase_8/pilot1/` |
| D5/D6 training | 6 artifacts, 120 episodes, 0 motor spikes, 0 weight change; F ≡ Fβ | `experiments/results/phase_8/training/` |
| Pilot 2-C | 54/54 rows executed, six arms, A′ exact identity ×9, all eight descriptive claims pass, C1–C4 not estimated | `experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/` |

The paper reports every negative result in full, including the Phase 6 null, the
Phase 7 motor silence, the Pilot 1 outcome, the behaviourally null training, and
the fact that the N = 16 confirmatory campaign was never executed.

## 3. Datasets, and where they came from

### 3.1 FlyWire FAFB v783 — brain connectome

- **What it is:** the Full Adult Fly Brain (FAFB) electron-microscopy volume of
  an adult female *Drosophila melanogaster*, materialised as the FlyWire
  connectome. Brain only; it contains no complete ventral nerve cord and no limb
  motor neurons.
- **What was used:** 15 gzip files — 6 annotation tables, 5 connectivity tables,
  4 neuron tables — totalling 368,874,372 bytes compressed and 29,231,539 rows.
  The structural input is the filtered pair table
  (`connections_princeton.csv.gz`, 5,342,446 rows); the 22,285,323-row unfiltered
  table was used only in the Phase 0 audit.
- **Where it came from:** the files were downloaded from the FlyWire/Princeton
  distribution before this repository existed. **No download log or source URL
  was stored with them.** The version is inferred as **v783** from an incomplete
  download filename (`fafb_v783_princeton_synapse_table.csv`); row counts and
  checksums are consistent with that release, but the completed files do not
  attest it. Verify the SHA-256 prefixes in `datasets/manifest.json` against any
  release you obtain before claiming exact provenance. Portal and citation
  requirements: <https://codex.flywire.ai/>.
- **What is tracked:** only the derived artifacts —
  `datasets/processed/connectome.npz` (28,013,212 bytes, SHA-256
  `3f568f24…5f33d8`), `datasets/processed/nodes.csv.gz`,
  `datasets/processed/connectome_report.json` and `datasets/manifest.json`. The
  raw downloads live under `datasets/raw/` and are excluded by `.gitignore`; they
  are **not redistributed** here.
- **Licence and attribution:** CC BY 4.0. Cite the FlyWire Consortium and the
  three primary publications listed in §9.

Verified structure: 139,255 neurons, 3,732,460 directed pairs at a pair-level
≥5-synapse threshold, 50,666,648 summed synapses, 671 isolated neurons, zero
self-connections, 620,180 reciprocal directed pairs, ascending root-ID order.

### 3.2 BANC v888 — brain and ventral nerve cord connectome

- **What it is:** an adult female *Drosophila* brain + ventral nerve cord
  reconstruction (Brain And Nerve Cord). It supplies the limb motor neurons that
  FAFB lacks. Coverage: central brain, neck connective, VNC, and the medulla,
  lobula and lobula plate; no lamina or ocellar ganglion.
- **What was used:** the v888 materialisation (edgelist v2, size ≥ 5) —
  172,433 endpoints, 1,535,710 directed edges, 18,552,546 summed synapses,
  24,320 isolated nodes, 805 motor neurons, 1,316 descending and 1,849 ascending
  neurons. Five source files and their SHA-256 values are recorded in
  `datasets/processed/banc_v888/banc_manifest.json`; the derived graphs are kept
  local and are **not redistributed**.
- **Where it came from:** the BANC distribution via Harvard Dataverse
  (<https://doi.org/10.7910/DVN/7WTH1N>) and the BANC portal
  (<https://banc.community>); browser at <https://codex.flywire.ai/banc>. The
  v888 materialisation (17 April 2026) is the final-print version.
- **Primary publication:** *Distributed control circuits across a brain-and-cord
  connectome*, *Nature* **656** (27 August 2026),
  doi:[10.1038/s41586-026-10735-w](https://doi.org/10.1038/s41586-026-10735-w),
  open access, CC BY. Influence scores: Zenodo
  doi:[10.5281/zenodo.15999929](https://doi.org/10.5281/zenodo.15999929);
  neurotransmitter predictions: Zenodo
  doi:[10.5281/zenodo.20818141](https://doi.org/10.5281/zenodo.20818141).
- **Licence:** CC BY 4.0. Credit the BANC Consortium and the paper above.

### 3.3 Subway Surfers Object Dataset v15 — perception data

- **What it is:** a Roboflow Universe object-detection dataset of Subway Surfers
  gameplay frames: 2,328 images, 2,328 label files, 8,666 boxes, 14 classes
  (`train`, `boxtrain`, `ramp`, `wall`, `ledge` and six barrier/power-up
  classes). It has **no player class and no coin class**, so player pose and
  coins are unmapped rather than inferred.
- **Where it came from:** Roboflow Universe, workspace `horizon-cgt2k`, project
  `subway-surfers-object-dataset`, version 15 —
  <https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset/dataset/15>.
  Licence: **CC BY 4.0**, as declared by the dataset.
- **How it was used:** as the perception input and evaluation data (YOLO label
  format, group-held-out curation by recording), and 30 frames as illustration
  in paper Figures 9–14. The 12 empty-label files were excluded after individual
  inspection. The dataset was used to train the project's YOLO11n detector — a
  50-epoch fine-tune of a COCO-pretrained checkpoint on the 1,188-image
  group-held-out training side, run in Google Colab on 2026-11-06 with
  Ultralytics 8.4.202 — and to evaluate it on the 1,128-image validation side.
  Raw images and the derived export are excluded by `.gitignore` and are not
  redistributed; only the six visual-documentation figures and their provenance
  index are tracked. The trained weights and ONNX export are likewise not
  redistributed (see §8).
- **Attribution:** "Subway Surfers Object Dataset" by `horizon-cgt2k` on
  Roboflow Universe, CC BY 4.0. "Subway Surfers" is a trademark of its owners;
  this project is not affiliated with or endorsed by them.

### 3.4 The game

The game is *Subway Surfers* (SYBO Games, 2012). **The commercial game was never
instrumented, controlled or modified.** Perception consumed recorded gameplay
frames; the closed loop ran against a local simulated game state that consumes
LEFT / RIGHT / JUMP / NO_ACTION decisions. No gameplay result in this repository
is a claim about the shipped game.

### 3.5 What is deliberately not in this repository

Raw FlyWire and BANC downloads, the Roboflow image tree, YOLO11n weights and the
ONNX export, cloned third-party repositories, virtual environments, caches,
credentials and machine-specific paths. They are excluded by `.gitignore`; see
§8 for licences and §9 for citations.

## 4. Software and other resources

Runtime and test dependencies are pinned in `requirements.txt`.

| Resource | Version | Role | Licence | Link |
|---|---:|---|---|---|
| Python | 3.13.14 | runtime | PSF | <https://www.python.org/> |
| NumPy | 2.3.4 | arrays, CSR simulation | BSD-3-Clause | <https://numpy.org/> |
| pandas | 2.3.3 | dataset audit, tabular I/O | BSD-3-Clause | <https://pandas.pydata.org/> |
| Matplotlib | 3.10.7 | figures | Matplotlib (PSF-based) | <https://matplotlib.org/> |
| PyYAML | 6.0.3 | configuration | MIT | <https://pyyaml.org/> |
| psutil | 7.1.2 | memory measurement | BSD-3-Clause | <https://github.com/giampaolo/psutil> |
| Pillow | 12.0.0 | image preprocessing | MIT-CMU | <https://python-pillow.org/> |
| onnxruntime | 1.29.0 | detector inference (CPU) | MIT | <https://onnxruntime.ai/> |
| pytest | 7.4.3 | test runner | MIT | <https://pytest.org/> |
| YOLO11n (ONNX) | deployment artifact | object detection | AGPL-3.0 | <https://docs.ultralytics.com/models/yolo11/> |
| python-docx / pypdf / Word automation | paper build only | DOCX and PDF rendering | MIT / BSD / proprietary app | — |

The YOLO11n checkpoint and ONNX export
(`models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx`, SHA-256
`e6ad18f9…6aa77`, 10,636,871 bytes) are **not redistributed**; their size, hash
and deployment contract are recorded in the model registry and
`THIRD_PARTY_NOTICES.md`. The detector was fine-tuned once for this project —
COCO-pretrained YOLO11n to 14 classes, in Colab on 2026-11-06 — outside this
repository, then frozen as a versioned ONNX artifact. It is not retrained or
fine-tuned by the simulation code.

External repositories were audited for architectural comparison only
(`docs/research/EXTERNAL_REPOSITORY_COMPARISON.md`,
`FLYVERSE_CORE_COMPATIBILITY_AUDIT.md`,
`EXTERNAL_NEURAL_MODEL_EQUATION_COMPARISON.md`): `tel-0s/flyverse-core`,
`flyvis`, Gymnasium, Stable-Baselines3, YOLOX and the Male CNS connectome
project. No code was adopted; the clones are not distributed.

## 5. Repository layout

```text
brain/                 FAFB connectome loader, LIF neuron, synapses, sampler,
                       recorder, simulator, BANC graph and BANC adapters
perception/            YOLO11n ONNX detector, preprocessing, tracking, bridge
sensory/               game state, population encoders, scheduler
motor/                 motor-population selection and activity recorder
learning/ plasticity/  reward, RPE, eligibility traces, three-factor rule
readout/               trainable linear readout and controller
information/           entropy, mutual information, permutation estimators
evaluation/            metrics and acceptance gates
environment/           game-state bridge used by the closed loop
configs/               frozen parameters, protocols and reference hashes
datasets/              audit manifest + tracked derived connectome artifacts
experiments/           phase_2 … phase_8 code and recorded results
reports/               phase reports, approvals, certification records
docs/                  designs, protocols, amendments, external audits
tests/                 automated test suite
research_paper/        paper source, figures, tables, build scripts, licences
```

## 6. Phase 2 simulation details

Each neuron is a point LIF unit:

```text
C_m dV/dt = -g_L (V - E_L) + I_syn + I_ext
```

The passive part uses the exact exponential-Euler update

```text
V(t+dt) = E_L + (V(t)-E_L) exp(-dt/tau_m) + I (1-exp(-dt/tau_m)) / g_L
```

so integration is stable for any positive timestep. Threshold crossing is checked
at the end of a step; spikes reset the membrane; the refractory period is rounded
up to whole timesteps; a configurable floor (−90 mV) represents unmodelled leak
and voltage-gated currents.

Synaptic propagation is sparse. A presynaptic spike indexes its outgoing CSR
rows and destination currents are accumulated with `numpy.bincount`; no dense
N × N matrix exists. Transmitter predictions set the assumed sign (ACH, GLUT
excitatory; GABA inhibitory; DA, SER, OCT and unlabelled configurable, excitatory
in the recorded runs). Currents decay exponentially (tau_exc 5 ms, tau_inh 8 ms),
with a uniform 1 ms delay. The structural synapse count `w` becomes
`12 * w ** 0.75` pA; this is an **approximation**, not a measured conductance.

Measured Phase 2 run (`experiments/results/initial/`): 800 sampled neurons,
7,500 internal edges, 124,693 internal synapses, 1 connected component, 1,564
spikes, 79 active neurons (9.88%), mean firing rate 1.96 Hz, 64/64 stimulated
neurons active, 15 non-stimulated neurons active (371 spikes, 23.7% of all
spikes). Recurrent recruitment is a property of the model, not a measurement of
the fly.

Full-connectome scalability (`experiments/phase_2_5/reports/scalability_report.json`):

| Neurons | Edges | Synapses | Simulation (s) | Steps/s | Peak WS (MB) | Spikes | Active | Stable |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 800 | 7,500 | 124,693 | 0.041 | 10,500 | 170.8 | 213 | 78 | yes |
| 5,000 | 121,092 | 1,931,167 | 0.057 | 7,343 | 171.7 | 145 | 96 | yes |
| 20,000 | 480,107 | 7,414,940 | 0.331 | 1,231 | 175.8 | 51,387 | 4,551 | yes |
| 50,000 | 1,620,531 | 23,785,918 | 1.060 | 382 | 222.3 | 151,855 | 11,837 | yes |
| 139,255 | 3,732,460 | 50,666,648 | 2.923 | 138 | 270.8 | 349,846 | 33,261 | yes |

"Stable" means finite state, membrane potentials inside the configured bounds,
refractory intervals respected, and recorded transmissions equal to the
out-degree sum of spiking neurons. Activity is not monotonic in size; the 5,000
neuron sample fired less than the 800 neuron sample, a composition effect.

## 7. Quick start and reproduction

Dependencies: Python 3.13, NumPy, pandas, PyYAML, matplotlib, psutil, Pillow,
onnxruntime and pytest. The validated artifact must exist at
`datasets/processed/connectome.npz`.

```bash
# Phase 0 audit (needs datasets/raw/ in place; rewrites datasets/README.md)
python dataset_audit.py

# Rebuild the processed FAFB artifact and run the round-trip checks
python -m brain.connectome_loader

# Phase 2 experiment (800 neurons, 1 s biological time)
python main.py --no-progress
python -m experiments.baseline

# Phase 2.5 scalability suite, plots and reports
python -m experiments.phase_2_5.run_all
python -m experiments.phase_2_5.run_all --reports-only

# Full test suite
python -m pytest -q
```

Later phases are executed through their phase runners and require the frozen
configurations and approval records in `configs/`, `docs/` and `reports/`; each
report states the exact command and the conditions under which it was run. Phase
8 executions are gated by the owner-approval records (D3–D6) and refuse to run
without them.

The paper is rebuilt from `research_paper/src/` with
`research_paper/scripts/assemble.py`, `build_docx.py` and `render_pdf.py` (the
last requires Microsoft Word for field refresh and PDF export).

## 8. Licences and citation

| Content | Licence |
|---|---|
| Original code (`brain/`, `perception/`, `sensory/`, `motor/`, `learning/`, `plasticity/`, `readout/`, `information/`, `evaluation/`, `experiments/` code, `configs/`, `tests/`) | MIT, © 2026 metadore |
| Research paper text, tables and figures (`research_paper/`) | CC BY 4.0, © 2026 metadore |
| FlyWire FAFB data and derived artifacts | CC BY 4.0 (FlyWire Consortium) |
| BANC data | CC BY 4.0 (BANC Consortium) |
| Subway Surfers Object Dataset v15 | CC BY 4.0 (`horizon-cgt2k`, Roboflow Universe) |
| YOLO11n weights / ONNX export | AGPL-3.0, not redistributed |
| Python and third-party libraries | their own licences |

Citation of this work: metadore, *Teaching a Fruit Fly Brain to Play Subway
Surfers Through Connectome-Based Neural Simulation: Architecture, Learning
Mechanisms, Experimental Evaluation, and Motor-Output Limitations*, version 1.1,
24 November 2026, plus the exact commit hash. The paper licence text is in
`research_paper/LICENSE`; full third-party notices are in
`THIRD_PARTY_NOTICES.md` and `REFERENCES.md`.

## 9. References

[1] Z. Zheng, J. S. Lauritzen, E. Perlman, et al., "A complete electron
microscopy volume of the brain of adult *Drosophila melanogaster*," *Cell*,
vol. 174, no. 3, pp. 730–743.e22, 2018.
doi:[10.1016/j.cell.2018.06.019](https://doi.org/10.1016/j.cell.2018.06.019).

[2] S. Dorkenwald, A. Matsliah, A. R. Sterling, et al. (FlyWire Consortium),
"Neuronal wiring diagram of an adult brain," *Nature*, vol. 634, pp. 124–138,
2024. doi:[10.1038/s41586-024-07558-y](https://doi.org/10.1038/s41586-024-07558-y).

[3] P. Schlegel, Y. Yin, A. S. Bates, et al. (FlyWire Consortium), "Whole-brain
annotation and multi-connectome cell typing of *Drosophila*," *Nature*,
vol. 634, pp. 139–152, 2024.
doi:[10.1038/s41586-024-07686-5](https://doi.org/10.1038/s41586-024-07686-5).

[4] FlyWire Consortium, "FlyWire whole-brain connectome connectivity data,
version 783.0," Zenodo, 2 June 2024.
doi:[10.5281/zenodo.10676866](https://doi.org/10.5281/zenodo.10676866). CC BY 4.0.

[5] *Distributed control circuits across a brain-and-cord connectome*, *Nature*,
vol. 656, 27 August 2026.
doi:[10.1038/s41586-026-10735-w](https://doi.org/10.1038/s41586-026-10735-w).
(BANC connectome, v888.) CC BY.

[6] BANC Consortium, "BANC v888 connectome data," Harvard Dataverse.
doi:[10.7910/DVN/7WTH1N](https://doi.org/10.7910/DVN/7WTH1N).

[7] FlyWire Consortium, "FlyWire Codex connectome browser and data portal,"
<https://codex.flywire.ai/> (BANC browser: <https://codex.flywire.ai/banc>;
BANC portal: <https://banc.community>).

[8] `horizon-cgt2k`, "Subway Surfers Object Dataset," version 15, Roboflow
Universe, 2024.
<https://universe.roboflow.com/horizon-cgt2k/subway-surfers-object-dataset/dataset/15>.
CC BY 4.0.

[9] SYBO Games, *Subway Surfers*. Copenhagen, Denmark: SYBO Games, 2012.

[10] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once:
Unified, real-time object detection," in *Proc. IEEE CVPR*, 2016, pp. 779–788.
doi:[10.1109/CVPR.2016.91](https://doi.org/10.1109/CVPR.2016.91).

[11] Ultralytics, "YOLO11 model documentation," <https://docs.ultralytics.com/models/yolo11/>
(AGPL-3.0).

[12] T.-Y. Lin, M. Maire, S. Belongie, et al., "Microsoft COCO: Common objects in
context," in *Computer Vision – ECCV 2014*, LNCS 8693, pp. 740–755.
doi:[10.1007/978-3-319-10602-1_48](https://doi.org/10.1007/978-3-319-10602-1_48).

[13] Microsoft, "ONNX Runtime," <https://onnxruntime.ai/>.

[14] W. Gerstner, W. M. Kistler, R. Naud, and L. Paninski, *Neuronal Dynamics:
From Single Neurons to Networks and Models of Cognition*. Cambridge Univ. Press,
2014. doi:[10.1017/CBO9781107447615](https://doi.org/10.1017/CBO9781107447615).

[15] N. Frémaux and W. Gerstner, "Neuromodulated spike-timing-dependent
plasticity, and theory of three-factor learning rules," *Frontiers in Neural
Circuits*, vol. 9, art. 85, 2016.
doi:[10.3389/fncir.2015.00085](https://doi.org/10.3389/fncir.2015.00085).

[16] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*,
2nd ed. MIT Press, 2018.

[17] T. M. Cover and J. A. Thomas, *Elements of Information Theory*, 2nd ed.
Wiley, 2006.

[18] S. Holm, "A simple sequentially rejective multiple test procedure,"
*Scandinavian Journal of Statistics*, vol. 6, no. 2, pp. 65–70, 1979.

[19] E. Maris and R. Oostenveld, "Nonparametric testing in EEG/MEG," *Journal of
Neuroscience Methods*, vol. 164, no. 1, pp. 177–190, 2007.
doi:[10.1016/j.jneumeth.2007.03.024](https://doi.org/10.1016/j.jneumeth.2007.03.024).

[20] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. Chapman &
Hall, 1993.

[21] C. R. Harris, K. J. Millman, S. J. van der Walt, et al., "Array programming
with NumPy," *Nature*, vol. 585, pp. 357–362, 2020.
doi:[10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2).

[22] W. McKinney, "Data structures for statistical computing in Python," in
*Proc. 9th Python in Science Conference*, 2010, pp. 56–61.

[23] J. D. Hunter, "Matplotlib: A 2D graphics environment," *Computing in Science
& Engineering*, vol. 9, no. 3, pp. 90–95, 2007.
doi:[10.1109/MCSE.2007.55](https://doi.org/10.1109/MCSE.2007.55).

The research paper carries the full 31-entry IEEE reference list, and
`REFERENCES.md` records the data-provenance caveats (including the missing FAFB
download log) and citation requirements.

## 10. Tests

`python -m pytest -q` reports **1,607 passed, 3 skipped, 0 failed** on
Python 3.13.14. Coverage spans LIF dynamics and reset/refractory rules, sparse
synapse transforms and sign policies, subgraph sampling, recording, full-connectome
artifact compatibility, Phase 2.5 benchmark validation, perception and temporal
encoding, Phase 3 gates and protected-hash integrity, BANC graph invariants,
motor decoding, plasticity and information estimators, the Phase 7 closed loop,
and the Phase 8 stage, training, artifact and Pilot 2-C contracts.

## 11. Known limitations and threats to validity

- The central behavioural result is negative: zero motor-population spikes in
  every executed closed-loop, pilot and training configuration. The cause is
  localised to a 6.926 mV first-hop shortfall under the current sensory
  convention and LIF parameters.
- 55.52% of BANC t5 edges have no verified transmitter sign and are excluded from
  simulation; the sign policy is a declared approximation.
- All neurons share one LIF parameter set; cell-type-specific physiology is absent.
- Synaptic weights are a calibrated power-law transform of structural counts,
  not measured conductances or reversal potentials.
- Delay is uniform; morphology, dendritic filtering, receptor saturation,
  short-term plasticity and neuromodulation are absent.
- The FAFB volume is brain-only; the BANC graph comes from a different specimen.
  The two graphs are never merged, and cross-dataset IDs are label bridges, not
  connectivity bridges.
- The perception dataset has no player or coin class, no independent test split,
  and only five recording groups; results are grouped-development estimates.
- The detector was trained outside this repository (a 50-epoch 14-class fine-tune
  in Colab, 2026-11-06) and is consumed here as a fixed ONNX artifact; it is not
  retrained or recalibrated by this repository's code. Its reported metrics are
  validation results from that training environment, not re-measured here.
- The commercial Subway Surfers game was never instrumented; game outcomes are
  properties of a local surrogate environment.
- Phase 8 did not estimate C1–C4 or test H1–H3; the N = 16 confirmatory campaign
  was not executed, and no campaign-scale inference exists.
- Structural connectivity is not physiological connectivity; a path in the
  connectome is a hypothesis about information flow, not a measurement of it.
- Simulated activity is model output, not recorded neural activity, and no result
  here is evidence of biological learning or functional game-playing.
