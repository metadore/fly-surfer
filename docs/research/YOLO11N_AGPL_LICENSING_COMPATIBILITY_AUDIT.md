# YOLO11n AGPL-3.0 Licensing Compatibility Audit

**Question (owner-selected Option A):** can the trained YOLO11n model and its
associated components be published under AGPL-3.0 while the broader FLY-SURFER
project retains its existing MIT licence?

**Date:** 2026-11-25
**Method:** read-only inspection of the repository, its recorded artifacts and
metadata, plus three official sources. No file was changed except this document.
No weights were uploaded, copied or redistributed. No Git operation was run.

> **Not legal advice.** This is a technical and licensing-evidence audit written
> by the project, not a legal opinion. Where the analysis turns on statutory
> interpretation it says so and identifies the question that counsel must
> answer. Nothing here should be read as a conclusion of law.

---

## 1. Executive verdict

| Question | Verdict |
|---|---|
| Can the MIT licence of the main repository be **preserved** while the model is published separately under AGPL-3.0? | **COMPATIBLE WITH CONDITIONS** |
| Can the trained model be **published today** with a defensible AGPL-3.0 compliance story? | **INSUFFICIENT EVIDENCE** |
| Does distributing the model alongside the MIT application make the application a single combined work? | **REQUIRES WRITTEN CLARIFICATION** (counsel and/or Ultralytics) |

**Bottom line.** The main repository, as published, contains no Ultralytics
source code and no model weights, and its Python code never imports
`ultralytics` (verified: zero matches outside untracked reference clones). Its
detector integration is a file-level runtime dependency on an ONNX artifact
loaded through ONNX Runtime, behind a model-agnostic `Detector` protocol with a
mock backend, a NanoDet backend and synthetic tests. On those facts the MIT
licence of the existing repository can plausibly be preserved while the model
is published in a **separate** AGPL-3.0 repository, because the current
distribution is an aggregate of independent works, not a single licensed work.

That answer is conditional and currently unearned in three ways:

1. **No recorded licence decision exists.** The project's own readiness audit
   marked "Accepted licence decision for YOLO11 training" as **BLOCKED — no
   record in the repository** (`reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:548`)
   and concluded "Final decision: BLOCKED — not ready to train" (`:742`).
2. **The Corresponding Source for the weights cannot be supplied.** There is no
   training script or notebook in the repository, no complete hyperparameter
   record, and the base checkpoint `yolo11n.pt` has no confirmed official
   checksum (`PHASE_3B2B1…:549`).
3. **The public licensing prose contradicts the recorded provenance.** Both
   `README.md:194` and `THIRD_PARTY_NOTICES.md:84` state the dataset was *not*
   used to train any project model, and `README.md:239–240` states the detector
   "was not retrained or fine-tuned". `model_config.json`, the ONNX metadata,
   `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` §1.3 and
   `reports/PHASE_3B2B3…:4` all record the opposite: a 14-class fine-tune run
   with Ultralytics 8.4.202.

Publishing an AGPL model repo now would make those statements demonstrably
false in a public MIT repository, and would convey AGPL weights without the
Corresponding Source that AGPL-3.0 §§5–6 require. Both must be fixed first.

---

## 2. Evidence base: what the repository actually contains

### 2.1 Licensing sources inspected

| Source | Content |
|---|---|
| `LICENSE` | MIT License, "Copyright (c) 2026 metadore" |
| `CITATION.cff:17` | `license: MIT` |
| `THIRD_PARTY_NOTICES.md:7–13` | MIT for original code in `brain/`, `perception/`, `sensory/`, `motor/`, `learning/`, `plasticity/`, `readout/`, `information/`, `evaluation/`, `experiments/` code, `configs/`, `tests/` |
| `THIRD_PARTY_NOTICES.md:15–27` | MIT does **not** cover `datasets/`, the Subway Surfers dataset, "external model weights and exported networks, including the YOLO11n checkpoint and ONNX export (AGPL-3.0), which are not distributed in this repository" |
| `THIRD_PARTY_NOTICES.md:95–105` | YOLO11n checkpoint + ONNX: AGPL-3.0, excluded by `.gitignore` |
| `README.md:42–45`, `355–365` | Licence table: code MIT; paper CC BY 4.0; FlyWire/BANC/Subway CC BY 4.0; "YOLO11n weights / ONNX export — AGPL-3.0, not redistributed" |
| `README.md:417–418` | Ultralytics YOLO11 documentation cited "(AGPL-3.0)" |
| `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:121,131–138` | "Ultralytics models are AGPL-3.0"; "Do not adopt Ultralytics AGPL code or weights without a deliberate licensing review" |
| `docs/PHASE_3_ROADMAP.md:400` | ONNX integration "requires an explicit decision and a licence review" |
| `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md:195–197,809` | AGPL network-use copyleft flagged as requiring "a licensing decision, not an implicit one" |
| `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md:548,566,738` | "Accepted licence decision for YOLO11 training — No record in the repository — BLOCKED"; official checksum for `yolo11n.pt` unavailable; overall BLOCKED |
| `reports/PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md:181,709` | Model licence AGPL-3.0, read from ONNX metadata |
| `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:1–16,136,370` | Integrates "the trained 14-class YOLO11n ONNX artifact"; `torch`, `ultralytics` and `best.pt` not needed for inference; no weights tracked |

### 2.2 Model artifacts and their declared licence

| Artifact | Size | SHA-256 | Licence evidence |
|---|---:|---|---|
| `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx` | 10,636,871 | `e6ad18f9…6aa77` | ONNX metadata strings inside the file: `AGPL-3.0 License (https://ultralytics.com/license)`, `8.4.202`, `dataset_colab.yaml` |
| `…/best.pt` | 5,491,034 | `1b47a433…def8` | Same provenance; PyTorch checkpoint of the fine-tune |
| `…/model_config.json` | 1,249 | `b48710e5…a8c` | 14 classes; `training_images: 1188`; `epochs: 50`; `image_size: 640`; `seed: 20261106`; `ultralytics_version: 8.4.202` |
| `…/metrics_summary.json` | 216 | `57ba3ccb…d615` | mAP50 0.8978, mAP50-95 0.6877, P 0.9373, R 0.8108 (1,128 images, ONNX Runtime CPU) |
| `models/YOLO11/yolo11n.pt` | 5,613,764 | `0ebbc80d…4ee1` | Upstream base pretrained checkpoint (Ultralytics, AGPL-3.0); provenance checksum unconfirmed |

Two independent records state that the deployment artifact is a **fine-tune**:

- `model_config.json` records a training block (50 epochs, 14 classes, seed
  20261106, Ultralytics 8.4.202) and `training_images: 1188`.
- `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` §1.3 records
  "Framework: Ultralytics", version 8.4.202, training data root
  `datasets/exports/phase_3b2b1_yolo11n/`.
- `reports/PHASE_3B2B3…:4` calls it "the trained 14-class YOLO11n ONNX
  artifact", and `:32` calls `metrics_summary.json` "Training-run metrics".

The ONNX metadata additionally embeds the training path
`/content/FLY-SURFER/dataset_colab.yaml`, i.e. a Colab run performed for this
project. No such YAML, notebook or script exists in the repository.

### 2.3 Distribution status

| Check | Result |
|---|---|
| `git ls-files models` | **0** — nothing under `models/` is tracked |
| `git ls-files` for `*.pt`, `*.onnx`, `*.pth`, `*.zip` | **0** |
| `.gitignore:86–89` | `models/`, `*.onnx`, `*.pt`, `*.pth` |
| `git ls-files references` | **0** — reference clones are local only |
| `.gitignore:12–14,112–113` | `datasets/external/`, `datasets/exports/…` excluded |
| `.gitignore:10` | `datasets/raw/**` excluded |

The published MIT repository therefore **conveys no AGPL material at all**:
no Ultralytics code, no weights, no ONNX graph, no training script.

The only model-derived content in the repository is documentation and figures:
the paper's detection images (`research_paper/figures/F09_3b2c_perception.png`,
`figures/yolo11_visuals/Y04–Y06`) and the recorded metrics. See §9 for the
residual question about model outputs.

### 2.4 Contradictory provenance statements (must be resolved)

| Statement | Location | Conflicts with |
|---|---|---|
| "The dataset was **not** used to train, fine-tune or tune any project model." | `README.md:194` | `model_config.json` training block; MODEL_REGISTRY §1.3; `PHASE_3B2B3:4` |
| "The detector is used as a fixed, externally trained component and was not retrained or fine-tuned." | `README.md:239–240` | Same records |
| "The dataset is not used to train, fine-tune or tune any project model; the detector weights come from the third-party YOLO11n release" | `THIRD_PARTY_NOTICES.md:84–86` | Same records |

One reading is that these sentences were written for the *narrow* tracked
artifacts (previews and documentation frames) and silently generalised. Another
is that they are simply stale. Either way they are factually wrong as written,
and a published AGPL model card that states "trained on Subway Surfers v15
using Ultralytics 8.4.202" would expose the contradiction. **This audit does not
choose between the readings; the owner must.**

---

## 3. Component-by-component licensing matrix

Legend for "U" (Ultralytics dependency): **none** = no import, no copied code,
no weights; **data** = consumes or produces YOLO-format labels/artifacts but
contains no Ultralytics code; **artifact** = is or loads the AGPL model.

| # | Component | Evidence | U | Distributed today | Licence that can apply | Basis |
|---|---|---|---:|---|---|---|
| 1 | `brain/` — connectome loader, LIF neurons, synapses, simulator | no `ultralytics` import anywhere in repo | none | yes | **MIT** | original code |
| 2 | `sensory/` — stimulus/observation encoders | same | none | yes | **MIT** | original code |
| 3 | `motor/` — motor selection and output | same | none | yes | **MIT** | original code |
| 4 | `learning/`, `plasticity/` — RPE, eligibility traces, three-factor rule | same | none | yes | **MIT** | original code |
| 5 | `readout/` — linear readout, trainer | imports `torch` for its own MLP, no Ultralytics | none | yes | **MIT** | original code |
| 6 | `information/` — entropy/MI estimators | no Ultralytics | none | yes | **MIT** | original code |
| 7 | `evaluation/` — harness, conventional PyTorch learner | `evaluation/conventional.py` imports `torch` for its own actor-critic; docstring: "no Gymnasium or Stable-Baselines3 dependency" | none | yes | **MIT** | original code |
| 8 | `experiments/` — phase runners, including `phase_3b/*` dataset curation, export, evaluation, replay | dataset/export/eval scripts use numpy, PIL, zipfile only; no `ultralytics` | data | yes (code + results) | **MIT** | original code; YOLO labels are a data format |
| 9 | `configs/`, `tests/` | `detector_config.yaml` describes the ONNX contract; tests use synthetic tensors and skip the real-model test when the artifact is absent | none | yes | **MIT** | original code |
| 10 | `perception/` — `Detector` protocol, MockDetector, letterbox, decode, NMS, tracking, bridge | no `ultralytics`; `onnxruntime` imported lazily at `inference.py:498`; NanoDet backend implemented | none | yes | **MIT is defensible**; **AGPL is a policy option** | independently written; model-agnostic by design |
| 11 | Deployment bundle `models/YOLO11/deployment/yolo11n_v1_deployment/` — `best.onnx`, `best.pt`, `model_config.json`, `metrics_summary.json`, `SHA256SUMS.json` | ONNX metadata declares AGPL-3.0; `dataset_attribution.txt`: "The YOLO11n model checkpoint is a separate work under AGPL-3.0" | artifact | **no** | **AGPL-3.0** for the weights; config/metrics are project-authored facts and may be MIT or AGPL | licensor's declared terms; see §7 |
| 12 | `models/YOLO11/yolo11n.pt` — base checkpoint | upstream Ultralytics release; no official checksum recorded (`PHASE_3B2B1:549`) | artifact | **no** | **AGPL-3.0** | upstream licence |
| 13 | `datasets/` — FlyWire-derived artifacts, Subway Surfers export and previews | `THIRD_PARTY_NOTICES.md:41–93` | data | partly (derived connectome, previews) | **CC BY 4.0** (with attribution); project-authored code MIT | upstream data licences |
| 14 | `research_paper/` — text, tables, figures | `research_paper/LICENSE` CC BY 4.0; includes model-output figures | data | yes | **CC BY 4.0** | owner's choice; see §9 |
| 15 | `references/`, `external/` — cloned repos (YOLOX, flyvis, SB3, Gymnasium, …) | 0 tracked files | n/a | **no** | their own licences | not distributed |
| 16 | `docs/`, `reports/` — design and audit prose | project-authored | none | yes | **MIT** | original text; measurements are facts |

**Key observation.** The only AGPL-3.0 components are the weights. Every
component that could make the main repository a "work based on" the model —
imports, copied code, linked libraries — is absent. The single integration
surface is `perception/inference.py`, which reads a documented tensor layout
from a SHA-verified file through ONNX Runtime.

---

## 4. Dependency and integration analysis

### 4.1 What actually uses Ultralytics

| Stage | In this repository? | Evidence |
|---|---|---|
| Training code | **No** | no `import ultralytics`, no `train.py`, no notebook; `experiments/phase_3b/export_yolo11_dataset.py:8` states "no model, package or training run is involved" |
| Export pipeline | **No** | the ONNX file already exists; no export script is tracked; metadata records `8.4.202` and a Colab path |
| Model architecture | **Only inside the AGPL weights** | architecture is defined by the trained graph, not by repository code |
| Trained weights | **Present locally, not distributed** | `.gitignore:86–89`; `git ls-files models` = 0 |
| ONNX graph | **Present locally, not distributed** | same |
| Inference code | **No** | `perception/inference.py` is an independent NumPy/Pillow/ONNX-Runtime implementation; it contains no Ultralytics source |

The project did, however, *use* the Ultralytics package (8.4.202) outside the
repository to produce `best.pt` and `best.onnx`. That fact is recorded, not
reproducible from the repository, and is the origin of the AGPL obligation on
the weights.

### 4.2 What is independent

`brain/`, `sensory/`, `motor/`, `learning/`, `plasticity/`, `readout/`,
`information/`, `evaluation/`, `experiments/`, `configs/` and `tests/` have no
Ultralytics dependency and no requirement that the YOLO artifact be present:

- `perception/detector.py:1–6` defines `Detector` as a `Protocol` and provides
  a `MockDetector` for deterministic pipeline tests.
- `perception/detector_config.py` supports three output layouts
  (`yolo_raw`, `boxes_scores`, `nanodet_plus`).
- `tests/test_detector_backend.py` exercises decoding with synthetic tensors
  and **skips** `test_real_onnx_model_smoke` when the deployed artifact is not
  present (`:504–508`).
- `requirements.txt` pins `onnxruntime==1.29.0` (MIT) and does **not** list
  `ultralytics` or `torch`.

The only cross-cutting fact is that the *headline demonstration* in Phase 3B
used the real YOLO weights. Scientific dependence on the artifact is not the
same as code derivation, but it is the fact an aggressive licensor would cite.

### 4.3 Nature of the integration

- **Mechanism:** the application opens a local `.onnx` file path, verifies its
  SHA-256 against `configs/detector_config.yaml`, and calls ONNX Runtime.
- **No linking:** ONNX Runtime does not link, embed or import Ultralytics code.
- **No code copy:** letterbox, decoding and NMS are project implementations of
  a published output contract, not copies of Ultralytics `ops.py`.
- **Graceful absence:** without the artifact the detector construction fails
  explicitly; the rest of the project (simulation, tests, analysis) runs.
- **Direction of dependence:** the application depends on the artifact at
  runtime; the artifact does not depend on the application.

That pattern — interoperation through a documented file format between
separately authored programs — is the classic basis for treating them as
separate works rather than one combined work. It is strong evidence, not proof:
the AGPL contains no interoperation exception, so the characterisation remains
a legal question.

---

## 5. The five arrangements compared

### 5.1 Entire FLY-SURFER project under AGPL-3.0

- **What can remain MIT:** nothing in the new distribution; existing recipients
  keep their irrevocable MIT grants, and the owner may relicense their own code.
- **What must be AGPL:** the whole combined distribution, including `brain/`,
  the simulator and the paper build scripts if distributed together.
- **Does repository separation change anything:** no — this option deliberately
  abandons separation.
- **Integration effect:** maximal; the network clause (§13) would reach any
  hosted demonstration of the simulator, not just the detector.
- **Corresponding Source:** the whole repository, which is already public —
  the easiest obligation to satisfy.
- **Main-repository concern:** it would contradict the current README,
  `CITATION.cff` and `THIRD_PARTY_NOTICES.md`, and would impose copyleft on
  users who only want the connectome simulator.
- **Verdict:** lawful for the copyright owner, but disproportionate; the
  scientific value is in the simulator and analysis code, which has no AGPL
  trigger.

### 5.2 Main repository MIT + separate AGPL-3.0 model repository (Option A)

- **What can remain MIT:** everything in the existing repository unchanged.
  It already conveys no AGPL material (§2.3).
- **What must be AGPL:** the model repository: `best.pt`, `best.onnx`, the
  licence text, notices, model card, and the Corresponding Source package.
- **Does repository separation change anything:** yes, and materially: it turns
  a potential "single work distributed together" into an aggregate of separate
  and independent works, which AGPL-3.0 §5/§6 expressly do **not** place under
  the licence (the "aggregate" paragraph). It also keeps the AGPL obligations —
  source offer, §13 — attached to the model repo alone.
- **Integration effect:** the MIT application still loads the artifact, but
  through an independent, model-agnostic interface. The risk is rhetorical and
  legal framing, not technical: don't advertise the MIT repo as "including" the
  detector or as "powered by" the weights.
- **Corresponding Source:** must be supplied with the model repo (see §6). This
  is the hard blocker (§8).
- **Main-repository concern:** the only AGPL content is the model; but the
  repo's documentation must stop claiming the model was not trained here
  (§2.4), or the two publications will contradict each other.
- **Verdict:** **COMPATIBLE WITH CONDITIONS** — the best fit for the stated
  goal.

### 5.3 Separate AGPL-3.0 perception component + MIT independent components

- **What can remain MIT:** simulation, connectome, learning, plasticity,
  readout, analysis, experiments.
- **What must be AGPL:** a perception package containing model loading,
  letterbox/decoding/NMS and the class map, plus the weights.
- **Does repository separation change anything:** it changes the *code*
  boundary, which is stronger than a file-format boundary — but only if the
  boundary is genuinely a process/API boundary. If the MIT simulator
  `import`s the AGPL perception package, a licensor can argue the import
  combines the works and the whole becomes AGPL.
- **Integration effect:** high; this is the arrangement most exposed to the
  "combined work" argument, because the AGPL code would be linked into the
  simulation process rather than merely reading a data file.
- **Corresponding Source:** the AGPL component plus the training materials.
- **Main-repository concern:** requires relicensing
  `perception/inference.py` (owner can) and re-architecting the interface; also
  shrinks the MIT surface for no licensing gain, since the decoder is
  independently written.
- **Verdict:** **NOT RECOMMENDED** as stated. It is more work, more risk, and it
  forfeits the aggregate argument that Option A already has. Only consider it
  if counsel concludes that reading the ONNX output is itself a derivative
  activity.

### 5.4 Publish ONNX weights and documentation only, without `best.pt`

- **What can remain MIT:** the main repository, as in 5.2.
- **What must be AGPL:** the ONNX graph and its documentation.
- **Does repository separation change anything:** no.
- **Integration effect:** none beyond 5.2.
- **Corresponding Source:** **worse, not better.** Under AGPL-3.0 §1,
  "Corresponding Source" is the form preferred for modification; for a trained
  network that is the training checkpoint (`best.pt`) plus the training
  materials. Conveying the ONNX "object code" while withholding the checkpoint
  invites a §6 incomplete-source objection. Ultralytics' own page says the
  obligation covers "code and weights".
- **Main-repository concern:** none new.
- **Verdict:** **NOT RECOMMENDED.** Withholding `best.pt` reduces compliance
  rather than reducing exposure, while giving up the reproducibility benefit
  that justifies publication at all.

### 5.5 Do not redistribute the trained model until written clarification

- **What can remain MIT:** everything; this is the status quo.
- **What must be AGPL:** nothing new — the weights stay local.
- **Does repository separation change anything:** not applicable.
- **Integration effect:** none; private use and internal experimentation do not
  trigger AGPL conveyance, and publishing *results* is not conveyance of the
  model.
- **Corresponding Source:** not triggered until conveyance.
- **Main-repository concern:** none; it is the only option with zero new
  exposure.
- **Verdict:** **SAFEST.** It costs reproducibility — a third party cannot rerun
  the detector — and leaves the paper's detector results unreproducible from
  published artifacts. Note the project already accepts this position in
  `THIRD_PARTY_NOTICES.md:101–105`.

### 5.6 Comparison summary

| | 5.1 whole AGPL | 5.2 MIT + AGPL model repo | 5.3 AGPL perception pkg | 5.4 ONNX only | 5.5 no redistribution |
|---|---|---|---|---|---|
| Main repo stays MIT | no | **yes** | partly | yes | yes |
| Weights published | yes | yes | yes | ONNX only | no |
| Corresponding Source satisfiable today | yes | **no** (no training source) | no | no | n/a |
| Aggregate/separate-works argument | lost | **available** | weakened (import) | available | n/a |
| §13 network exposure | whole project | model repo only | perception service | model repo | none |
| Reproducibility for third parties | full | good if source supplied | good | partial | none |
| New documentation corrections needed | extensive | **README/NOTICES/§2.4** | moderate | README/NOTICES | none |
| Overall | lawful but disproportionate | **preferred if conditions met** | not recommended | not recommended | safe fallback |

**Does merely separating repositories change anything?** Yes for distribution
fact and obligation scope, no for authorship or for the "is the app a
derivative" question. Separation is what makes the aggregate paragraph
available; it does not immunise genuinely derivative code. In this project the
code is demonstrably independent, so separation does the work it is supposed to
do.

**Does the model's integration with the main application affect the analysis?**
It is the central awkwardness. Technically it is a data dependency, not code
integration (§4.3), which supports MIT. Commercially and doctrinally, the MIT
artefacts' most prominent result needs the AGPL weights, which is why written
clarification is advisable before publishing rather than after.

**Does the existing main repository create a compatibility concern?** Not a
licensing one — it contains no AGPL material. It creates an **evidentiary**
one: its public prose asserts a training provenance that the model artifacts
contradict (§2.4), and it disclaims a licence decision the project's own audit
records as absent (§1). Both undermine any compliance narrative attached to a
future model repo.

---

## 6. Source-disclosure implications

### 6.1 What AGPL-3.0 requires (in substance; section numbers cited)

- **§0 definitions:** a "covered work" is the unmodified Program or a work
  based on it; "propagate" covers anything that would otherwise infringe;
  "convey" covers propagation that enables others to make or receive copies.
- **§4–§5:** whoever conveys the work must give recipients the licence text,
  keep notices intact, mark modifications, and license the conveyed work under
  AGPL-3.0.
- **§5 aggregate paragraph:** a compilation of separate and independent works
  that are not extensions of the covered work and are not combined into a
  larger program does not bring the other works under the licence. This is the
  clause that lets an MIT repository sit beside an AGPL model.
- **§6:** conveying object code requires conveying the Corresponding Source by
  one of the listed means (accompanying it, a written offer, or a network
  server at no charge).
- **§1 Corresponding Source:** "all the source code needed to generate,
  install, and (for an executable work) run the object code and to modify the
  work" — including scripts controlling those activities.
- **§13 Remote Network Interaction:** a modified version used to provide a
  service over a network must offer all remote users an opportunity to receive
  its Corresponding Source.

### 6.2 What "Corresponding Source" plausibly means for a trained network

The licence predates machine learning; the FSF has not published a definitive
interpretation for model weights. A defensible, conservative package for this
model would contain:

1. the Ultralytics AGPL-3.0 licence text and copyright notices;
2. the training notebook or script, with the exact command line;
3. the pinned environment (`ultralytics==8.4.202`, Python, PyTorch, CUDA/CPU);
4. the base checkpoint identity and checksum (`yolo11n.pt`, expected
   `0ebbc80d…4ee1` once confirmed against an official source);
5. the training data: the curated Subway Surfers v15 export — already published
   at `metadore/fly-surfer-yolo11n-dataset` under CC BY 4.0;
6. the export script or record that produced `best.onnx` (input shape, opset,
   simplification);
7. `model_config.json`, `metrics_summary.json` and the class map;
8. the trained checkpoint `best.pt` — the preferred form for modification.

### 6.3 What the project can and cannot supply today

| Item | Status |
|---|---|
| Licence text and notices | can supply |
| Dataset (CC BY 4.0) with attribution | can supply — already public |
| `model_config.json`, metrics, class map | can supply |
| `best.pt`, `best.onnx` | can supply (local, hash-verified) |
| Base checkpoint hash | local hash known; **official** checksum unconfirmed |
| Training notebook/script | **missing** |
| Full hyperparameters (optimizer, LR, batch, augmentation, freeze policy) | **missing**; only epochs 50, imgsz 640, seed, framework version recorded |
| Export command | **missing** (only the output contract is documented) |
| Recorded licence decision authorising the training | **missing** (§1) |

---

## 7. Ultralytics' stated interpretation vs the licence text

| Point | Ultralytics' public position (as retrieved 2026-11-25 from `ultralytics.com/license`) | What AGPL-3.0 itself provides |
|---|---|---|
| Scope | "All Ultralytics YOLO trained models fall under the AGPL-3.0 License"; applies to trained/fine-tuned models | Whether weights are a "covered work" is a copyright question the licence does not answer explicitly; a fine-tune of an AGPL checkpoint is the strongest case for coverage |
| User obligation | Users must "open-source your entire project", including code and weights | §5/§6 require the **conveyed work** and works based on it under AGPL; §5's aggregate paragraph excludes separate independent works; "entire project" is broader than the text |
| Commercial route | Enterprise licence permits use "without open-sourcing" | Not part of AGPL; it is a separate contractual offer from the licensor |
| Network use | AGPL network copyleft applies | §13 applies to the Program and works based on it, not to every program that interacts with it |

**Distinction to keep explicit.** Ultralytics' "entire project" statement is the
licensor's declared interpretation and a practical condition of using their
artifacts. It is not the same thing as the AGPL-3.0 text, which is narrower for
separate works. A publisher who relies on the narrower reading is taking a
calculated position that the licensor may dispute; a publisher who follows
"entire project" must relicense everything. Option A sits between the two and
should be adopted with that tension acknowledged, not hidden.

Also note: the deployed ONNX embeds `license=AGPL-3.0 License
(https://ultralytics.com/license)` in its own metadata. That is an express
licence declaration travelling with the artifact; it cannot be argued away by
repository structure.

---

## 8. Missing evidence required for a defensible decision

1. **A recorded licence decision** authorising the YOLO11 training and its
   licence route. The repository's own audit records none
   (`PHASE_3B2B1…:548,738`).
2. **The training source**: notebook/script, exact command, optimiser, learning
   rate, batch size, augmentation, freeze policy, and whether training started
   from `yolo11n.pt` (and which release).
3. **The export source**: the command that produced `best.onnx` (opset, dynamic
   axes, simplification, `end2end` flag).
4. **Official checksum/provenance for `yolo11n.pt`** — only a local hash is
   recorded; `PHASE_3B2B1…:549` marks this BLOCKED.
5. **Correction of the contradictory provenance prose** (`README.md:194`,
   `README.md:239–240`, `THIRD_PARTY_NOTICES.md:84`), or a documented
   explanation of what those sentences were meant to describe.
6. **Written clarification from Ultralytics or counsel** on three questions:
   (a) are fine-tuned weights a covered work; (b) what constitutes Corresponding
   Source for them; (c) does a separately distributed, non-linked application
   fall inside "your entire project".
7. **A position on underlying game imagery rights.** The Roboflow uploader
   declares CC BY 4.0, but the screenshots depict a commercial game;
   `PHASE_3B2B1…:550` records this as BLOCKED (unresolved). This already affects
   the published dataset repository, and would affect weights trained on it.
8. **A decision on model outputs** (paper figures, metrics) — see §9.

---

## 9. Risks and unresolved questions

| # | Risk / question | Severity | Notes |
|---|---|---|---|
| R1 | Ultralytics' "entire project" position is broader than AGPL §5's aggregate clause | High | Requires counsel or written clarification; cannot be settled by repository layout alone |
| R2 | Whether fine-tuned weights are a "covered work" is legally unsettled | High | Mitigated by treating them as covered, as the project already does |
| R3 | Corresponding Source for weights is undefined; training source is missing | High | Blocks publication today |
| R4 | Public prose contradicts recorded training provenance | High (reputational, evidentiary) | Must be corrected before any model publication |
| R5 | No recorded licence decision | High (process integrity) | The project's own audit marks it BLOCKED |
| R6 | Game screenshot rights | Medium | Affects dataset and weights; uploader's CC BY 4.0 may not bind the game's rights-holders |
| R7 | Base checkpoint provenance (no official checksum) | Medium | Needed for the source package |
| R8 | §13 network clause if a hosted demo is added | Medium | Attach a source offer to any Space/API |
| R9 | Model-output figures in the MIT/CC BY 4.0 repositories | Low–medium | Common view is that program output is not automatically covered; the owner already licenses the paper CC BY 4.0 |
| R10 | Perception decoder characterised as YOLO-specific | Low | Independently written; NanoDet backend and mock show model-agnostic design |
| R11 | Mixed licensing invites user confusion | Low | Model card must state the separation explicitly |

**Unresolved legal questions (for counsel, not for this audit):** the status of
model weights under AGPL-3.0; the meaning of Corresponding Source for weights;
whether a separately distributed ONNX-consuming application is a work based on
the Program; and whether the licensor's "entire project" statement is an
enforceable licence condition or an interpretation.

---

## 10. Recommended next step

1. **Do not publish the weights yet.** The status quo (MIT repository, weights
   local) is the only arrangement currently free of new obligations.
2. **Correct the record first.** Amend `README.md:194`, `README.md:239–240` and
   `THIRD_PARTY_NOTICES.md:84` so they state the true provenance: a 14-class
   fine-tune of the Ultralytics YOLO11n checkpoint, produced outside the
   repository with Ultralytics 8.4.202, and never distributed. Record the
   licence decision in the repository.
3. **Recover the training and export provenance** (items 2–4 in §8). Without
   them the AGPL source obligation cannot be met even in principle.
4. **Obtain the two clarifications** (§8 item 6) — Ultralytics in writing, or
   counsel. Ask specifically whether a separate, non-linked application that
   only reads an ONNX file is outside "your entire project", and what they
   accept as Corresponding Source for fine-tuned weights.
5. **If the clarifications permit publication**, adopt arrangement **5.2**:
   a separate AGPL-3.0 model repository containing `best.pt`, `best.onnx`, the
   licence text, a model card (`license: agpl-3.0`, `base_model:
   Ultralytics/YOLO11`, `datasets: metadore/fly-surfer-yolo11n-dataset`) and the
   full source package from §6.2. Keep the MIT repository unchanged except for
   the provenance corrections; do not add weights to it, and do not describe it
   as including the detector.
6. **If the clarifications do not permit it**, adopt arrangement **5.5** and
   state in the paper and repository that the weights are withheld for
   licensing reasons, which is already close to the current position.
7. **Consider the permissive route** the project itself recommended in Phase 3B
   (`docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md:135–138`): a YOLOX or NanoDet
   fine-tune would remove the AGPL question entirely at the cost of retraining
   and re-evaluating.

**Answer to the owner's question.** Yes — the MIT licence of the main project
can potentially be preserved. The current repository distributes no AGPL
material and its code has no Ultralytics dependency, so publishing the model in
a separate AGPL-3.0 repository does not by itself relicense the MIT code.
Preservation is conditional on: no weights or Ultralytics code entering the MIT
repository; truthful provenance statements in both repositories; an AGPL model
repository that actually carries its Corresponding Source; and acceptance — with
counsel or written clarification — that the AGPL text, not the licensor's
"entire project" gloss, governs the relationship between the two works.

---

## 11. Sources

**Official**

- Ultralytics licensing page — <https://www.ultralytics.com/license> (retrieved
  2026-11-25)
- GNU Affero General Public License v3.0 — <https://www.gnu.org/licenses/agpl-3.0.html>
  (§0 definitions, §1 Corresponding Source, §§4–6 conveyance, §13 network use)
- Hugging Face Hub model cards — <https://huggingface.co/docs/hub/main/model-cards>
  (`license`, `license_name`/`license_link`, `base_model`, `datasets`,
  `pipeline_tag`; custom licences via `license: other`)
- Ultralytics YOLO11 documentation — <https://docs.ultralytics.com/models/yolo11/>

**Repository evidence**

- `LICENSE`, `CITATION.cff`, `THIRD_PARTY_NOTICES.md`, `README.md` §§3.3, 4, 8
- `configs/detector_config.yaml`, `requirements.txt`, `.gitignore` lines 10–14,
  86–89, 112–113
- `models/YOLO11/deployment/yolo11n_v1_deployment/{model_config.json,metrics_summary.json,dataset_attribution.txt}`
  and the embedded ONNX metadata strings
- `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` §§1.1–1.9
- `perception/detector.py`, `perception/inference.py`, `perception/detector_config.py`
- `tests/test_detector_backend.py`
- `experiments/phase_3b/export_yolo11_dataset.py`
- `docs/PHASE_3B_VISUAL_PERCEPTION_DESIGN.md`, `docs/PHASE_3_ROADMAP.md`
- `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md`,
  `reports/PHASE_3B2B1_PRETRAINING_READINESS_AUDIT.md`,
  `reports/PHASE_3B2B2_YOLO11N_ONNX_INTEGRATION_AUDIT.md`,
  `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md`
