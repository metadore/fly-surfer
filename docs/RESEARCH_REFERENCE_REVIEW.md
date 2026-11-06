# Research reference review — Phase 3A

Status: read-only inspection completed 2026-11-04. A FlyVis audit was added the
same day during Phase 3B planning (section 11). No reference code was executed,
no dependency was installed for inspection, no reference repository was
modified, moved into the tracked project or committed. The directories live
under `references/`, which is ignored by Git.

This note separates three kinds of statement:

- **External observation** — what a downloaded repository says or does.
- **FLY-SURFER** — what this project currently implements.
- **Recommendation** — a proposal for this project, not a result from either
  side.

Nothing in this review transfers results, neuron IDs, connectome mappings or
anatomical claims from an external project to FLY-SURFER.

## 1. Inventory

| Project | Local path | Upstream | Licence | Inspected state |
|---|---|---|---|---|
| Fly Hero | `references/fly-hero-master/fly-hero-master` | `bsgelman/fly-hero` | MIT | Complete source: Python simulator, browser port, tools, data, README, lab notebook |
| Eon fly-brain | `references/fly-brain-main/fly-brain-main` | `eonsystemspbc/fly-brain` | GPL-2.0-or-later (project); `code/paper-phil-drosophila` retains MIT | Complete source: Python entry points, backend runners, benchmark data, environments |
| Drosophila Brain Model | `references/Drosophila_brain_model-main` | attributed in the Phase 3A brief to `philshiu/Drosophila_brain_model` | Not present | **Empty directory — no files to review** |
| FlyVis | `references/flyvis-main/flyvis-main` | `TuragaLab/flyvis` | MIT | Complete Python source audited read-only: PyTorch connectome-constrained visual model, 45,669 cells, 65 cell types, Python `>=3.9,<3.13`; details in section 11 |

The three available repositories are conceptually useful, but none is a
drop-in component for FLY-SURFER. Their data, identifiers and model parameters
must not be substituted for the validated FAFB artifact.

## 2. Architecture comparison

| Dimension | FLY-SURFER | Fly Hero | Eon fly-brain |
|---|---|---|---|
| Connectome | FlyWire FAFB v783, adult female brain: 139,255 neurons, 3,732,460 directed edges, 50,666,648 summed synapses | Janelia/Google adult **male CNS** subgraph: 6,900 neurons (3,275 brain + 3,625 nerve cord), 6,419,481 synapses; earlier version used a FlyWire brain subgraph | FlyWire brain: ~138k–139k neurons, ~5M connections as described upstream |
| Scope | Brain only; no ventral nerve cord | Brain plus receive-only nerve cord | Brain only |
| Neuron model | Passive LIF, exact exponential-Euler update | LIF from Shiu et al., 1 ms steps | LIF with alpha synapse, 0.1 ms steps |
| Synapse model | Excitatory/inhibitory exponential currents, amplitude `12·w^0.75` pA, 1 ms delay | Signed weight per synapse, 0.275 mV scale, delay/refractory rounded to 2 ms | Alpha synapse (`tauSyn` 5 ms), 1.8 ms delay |
| Propagation | Sparse CSR, per-step scatter/bincount | Dense-per-step over a compact 6,900-neuron subgraph | Sparse matrix operations; multiple backends |
| Input | Experimenter current: Phase 2 fixed stimulus; Phase 3A game-state populations | Lane-specific eye VPN groups driven at 150 Hz by game events | Poisson activation of selected neuron sets at configured rates; optional silencing |
| Output | Spike times and counts; no action selection | Output-group spike counts choose a lane; dopamine learning | Spike times/rates; no behaviour |
| Learning | None | Reward prediction error with PAM/PPL1 dopamine and eligibility traces; a supervised Deep-RL readout is also compared | None |
| Implementation | NumPy/Python | NumPy/Python plus an equivalent JavaScript port | PyTorch, Brian2CUDA, NEST GPU, GeNN, Brian2GeNN |
| Validation style | Deterministic seeded tests; subprocess reproducibility hashes; artifact audit | Python/JS equivalence tests, wiring controls, blocked-dopamine controls | Cross-backend and cross-duration benchmark suite |

## 3. Sensory-input observations

**External observation — Fly Hero.** The game loop converts notes into
lane-tagged events and drives the corresponding visual-projection-neuron pool
with Poisson spikes. The fly “sees” a lane, not a screenshot. Input populations
are selected by connectivity rules in `tools/extract_subgraph.py`, and the
resulting male-CNS IDs are specific to that dataset.

**External observation — Eon fly-brain.** Input is optogenetic-style
activation of arbitrary neuron sets at a fixed Poisson rate, with optional
silencing of another set. It is a stimulation interface, not a model of a
sensory organ or a game scene.

**FLY-SURFER.** Phase 3A defines an explicit game-state schema (player lane,
speed, jump/roll, obstacle/train/coin presence, lane, distance and obstacle
type), converts each feature to a dimensionless population activation, and
converts activation to pA in the scheduler. No screenshots, computer vision or
game integration are present.

**Recommendation.** Keep the Phase 3A interface at the feature level. Fly
Hero's lane-event idea is structurally similar to the lane encoder, but its
selection rules, IDs and male-CNS graph must not be reused. Eon's activation
interface is closer to Phase 2 external current than to a sensory encoder.

## 4. Neural-output observations

**External observation — Fly Hero.** Activity is read from MBON/output groups
after Kenyon-cell and dopamine circuits; the action is the lane with the
strongest output, and dopamine updates plastic KC→MBON synapses. The published
scores belong to that male-CNS model and its game, not to FLY-SURFER.

**External observation — Eon fly-brain.** The model reports spike times and
rates of all affected neurons. It does not define a motor decoder or a
behavioural output.

**FLY-SURFER.** Phase 3A records spikes only. There is no motor decoding,
action selection, reward or plasticity. Spike counts in `experiments/phase_3/`
are simulated model output.

**Recommendation.** Do not import Fly Hero's action readout or dopamine rule
before Phase 3A's input side is characterised. Do not use its reported learning
scores as evidence about FAFB or about FLY-SURFER.

## 5. Simulation-model comparison

| Parameter | FLY-SURFER | Fly Hero | Eon fly-brain |
|---|---|---|---|
| Resting potential | −65 mV | −52 mV | −52 mV |
| Threshold | −50 mV | −45 mV | −45 mV |
| Reset | −68 mV | −52 mV | −52 mV |
| Membrane time constant | 20 ms (`C/g`) | 20 ms | 20 ms |
| Synaptic time constant | 5 ms excitatory, 8 ms inhibitory | 5 ms | 5 ms alpha |
| Refractory | 2 ms | 2 ms (rounded) | 2.2 ms |
| Delay | 1 ms | 2 ms (rounded) | 1.8 ms |
| Timestep | 0.5 ms | 1 ms | 0.1 ms |
| Rheobase | 150 pA by construction | Implied by its parameters | Implied by its parameters |
| Weight rule | `12·syn_count^0.75` pA, sign from predicted transmitter | 0.275 mV per synapse, signed | 0.275 scale, signed |

**FLY-SURFER** chose its membrane and synapse parameters for stable, readable
simulation on the FAFB artifact. They are model assumptions, not measured fly
physiology, and they are not copied from either project. The shared time
constant of 20 ms is a common LIF convention, not evidence of equivalence.

**Recommendation.** Do not switch to Eon's alpha synapse, 0.1 ms timestep or
1.8 ms delay as part of Phase 3A. That would change the validated simulator
and make Phase 2/2.5 results incomparable. If a cross-model comparison is ever
wanted, run it as a separate, explicitly labelled study.

## 6. Useful ideas

These are conceptual adoptions only; no source code or data was copied.

1. **Separate scene, encoding and simulation layers** (Fly Hero). Phase 3A
   mirrors this separation with `GameState` → encoders → scheduler →
   `BrainSimulator`.
2. **Lane-specific input populations** (Fly Hero). Phase 3A implements its own
   lane encoder with seeded, disjoint FAFB neuron selection.
3. **Deterministic equivalence checks across implementations** (Fly Hero
   Python/JS tests). Phase 3A uses a lighter version: two fresh subprocesses
   must produce equal input and spike hashes.
4. **Sparse propagation and batched trials** (Eon). FLY-SURFER already uses
   sparse CSR; batched GPU trials remain a possible future benchmark, not a
   Phase 3A requirement.
5. **Activation/silencing as an explicit external interface** (Eon). This
   reinforces keeping sensory drive separate from the neuron model, as the
   Phase 3A scheduler does.
6. **Cross-backend validation** (Eon). A future independent check of spike
   propagation could be valuable, but it requires matching inputs and
   parameters and is not part of Phase 3A.

## 7. Incompatible or rejected approaches

- **Fly Hero's male CNS graph and identifiers.** Different dataset, sex and
  scope. Merging it with FAFB or copying its IDs would break the validated
  artifact and the scientific boundary of this project.
- **Fly Hero's reward/dopamine/plasticity machinery.** Out of scope in Phase
  3A; the brief explicitly forbids plasticity and reward learning here.
- **Eon's alternative neuron/synapse discretisation.** Useful as a comparison,
  incompatible with keeping the Phase 2/2.5 simulator unchanged.
- **Poisson activation as a stand-in for sensory coding.** Phase 3A encodes
  structured features; a fixed-rate Poisson drive would discard the feature
  representation under study.
- **Reusing GPL-licensed source.** Not done; see licensing below.
- **Screenshots, OpenCV, MediaPipe, browser automation, keyboard control.**
  Explicitly deferred; not present in Phase 3A.
- **FlyVis.** Audited read-only during Phase 3B planning (section 11). It was
  not installed, executed or integrated, and it is outside Phase 3A.

## 8. Licensing

| Source | Licence | Implication for FLY-SURFER |
|---|---|---|
| Fly Hero | MIT | Code reuse would require copyright and permission notice. FLY-SURFER still does not reuse it: the data are a different connectome and the model differs. |
| Eon fly-brain (project) | GPL-2.0-or-later | Copying or linking project code would impose GPL obligations on distribution. **No code was copied or imported.** |
| `code/paper-phil-drosophila` inside Eon | MIT | Applies only to that subdirectory, not to the surrounding GPL project. Not used here. |
| Drosophila Brain Model | Unknown/absent | Directory is empty; no licence text to evaluate. |
| FlyVis | MIT | Reuse would require the copyright and permission notice. Not used here. It remains a separate decision because it is a PyTorch model with externally downloaded weights and an incompatible Python range. |
| FLY-SURFER itself | No project-wide licence selected | `THIRD_PARTY_NOTICES.md` and `REFERENCES.md` already state this. Do not assume reuse rights. |
| FlyWire FAFB data | CC BY 4.0 | Attribution required for data and derived artifacts; see `THIRD_PARTY_NOTICES.md`. |

**Recommendation.** Keep the reference directories ignored and untracked. If a
future phase wants to reuse any GPL code, treat it as a deliberate licensing
decision with a compatibility review, not as a copy-paste step.

## 9. Recommendations for FLY-SURFER

1. Keep Phase 3A's input interface feature-based and separate from perception.
2. Do not adopt external connectome IDs, neuron selections or performance
   numbers.
3. Use the reference projects for architectural comparison and benchmarking
   ideas, not as dependencies.
4. Do not treat FlyVis as a Phase 3B dependency. It is MIT and is now audited
   (section 11), but it is not an object detector, needs receptor-space input
   and a separate Python environment, and was not installed.
5. If cross-model validation is pursued later, define matched inputs and
   parameters first; otherwise differences cannot be interpreted.
6. Keep sensory mapping explicitly labelled as experimental predicted-annotation
   populations until an anatomical pathway is independently validated.

## 10. Claims this review does not make

- It does not claim that Fly Hero's or Eon's results reproduce in FLY-SURFER.
- It does not claim that the Phase 3A mapping is a real sensory pathway.
- It does not claim that the chosen encoders match Drosophila coding.
- It does not treat connection counts, summed synaptic contacts and
  physiological conductance as interchangeable quantities.
- It does not validate FlyVis as a component; section 11 covers only licensing,
  interface compatibility and a local source audit.

## 11. FlyVis audit (read-only, added during Phase 3B planning)

**External observation — local source.** FlyVis is present at
`references/flyvis-main/flyvis-main` (upstream `TuragaLab/flyvis`). Its
`license` file is the MIT License, Copyright (c) 2023 Lappalainen, Tschopp,
McGill, Macke, Turaga. No FlyVis code was executed, no dependency was
installed and no model weights were downloaded.

| Item | Finding |
|---|---|
| Model class | PyTorch deep mechanistic model of the *Drosophila* visual system, constrained by the FIB25–FIB19 connectome |
| Scale | 45,669 cells, 721 ommatidia, 65 cell types as stated in the project documentation |
| Local connectome artifact | `flyvis/connectome/fib25-fib19_v2.2.json`: 65 node types, 605 edges, input units R1–R8, 34 output units (T cells) |
| Input contract | `Stimulus.add_input` expects `(n_samples, n_frames, 1, n_input_elements)` in photoreceptor/hexagonal receptor space, not arbitrary RGB frames |
| Dynamics | Integration timestep is a researcher choice; the code warns above 1/50 s, and examples use 5–20 ms |
| Dependencies | PyTorch, torchvision, numba, Hydra, xarray, scikit-learn, UMAP, ffmpeg-python and others; optional pretrained extras pin older versions |
| Python range | `requires-python = ">=3.9,<3.13"`; the local interpreter is Python 3.13, outside the declared range |
| Pretrained weights | Downloaded separately from Google Drive by `flyvis_cli/download_pretrained_models.py`, with SHA-256 checksums; not present locally |
| Compute | A 45,669-cell PyTorch simulation is materially heavier than the NumPy LIF simulator and is not a screenshot object detector |

**Relevance to FLY-SURFER.** FlyVis is a biologically grounded visual
representation model, not a perception front-end for a game. Using it would
require a defined projection from screenshots into ommatidial receptor space,
a separate Python environment, external weights and a substantial compute
budget. It also would not by itself produce the object categories, lanes or
distances that `GameState` requires.

**Decision.** Do not install, execute or integrate FlyVis in Phase 3A, 3A.5 or
the Phase 3B MVP. It remains a candidate for a later, separately scoped study
of visual representations. Any such study must review the MIT notice, the
weight distribution terms and the environment constraints first.

**Licensing implication.** MIT permits reuse with the copyright and permission
notice, but no FlyVis code, weights, data or identifiers have been copied into
FLY-SURFER. The project-wide licence position is unchanged.
