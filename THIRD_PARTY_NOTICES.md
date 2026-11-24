# Third-party notices and licensing

FLY-SURFER contains original research code and a derived representation of the
FlyWire FAFB connectome. It does not vendor third-party source code and does not
claim ownership of the FlyWire data or of the Python packages it uses.

## Project licence

Original source code written for this project — the contents of `brain/`,
`perception/`, `sensory/`, `motor/`, `learning/`, `plasticity/`, `readout/`,
`information/`, `evaluation/`, `experiments/` (code, not the recorded
outputs), `configs/` and `tests/` — is released under the MIT License; see
`LICENSE`. Copyright (c) 2026 metadore.

The MIT License does **not** apply to the following, which carry their own
terms described in this file:

- datasets and derived connectome artifacts under `datasets/`;
- third-party datasets used only for visual documentation (Subway Surfers
  Object Dataset, CC BY 4.0);
- external model weights and exported networks, including the YOLO11n
  checkpoint and ONNX export (AGPL-3.0), which are not distributed in this
  repository;
- Python and third-party libraries listed below;
- any third-party reference repository cloned under `external/` or
  `references/` (not distributed).

The research paper under `research_paper/` is a separate scholarly document,
licensed Creative Commons Attribution 4.0 International (CC BY 4.0), © 2026
metadore — <https://creativecommons.org/licenses/by/4.0/>. That licence covers
the author's original paper text, tables and figures only. Third-party material
reproduced or referenced in the paper (FlyWire FAFB, BANC, Subway Surfers,
third-party software, model weights and figures) retains its own licence and
attribution and is not relicensed by CC BY 4.0; see the sections above and
`research_paper/LICENSE`.

The author names, versions, hashes and derived measurements in the paper and
the evidence register are provenance records, not a grant of rights over the
underlying data.

## FlyWire FAFB data

- **Dataset:** FlyWire Whole-brain Connectome Connectivity Data, version 783.0.
- **Publisher:** FlyWire Consortium (Princeton University), Zenodo, 2 June 2024.
- **DOI:** <https://doi.org/10.5281/zenodo.10676866>
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0),
  <https://creativecommons.org/licenses/by/4.0/>.
- **Attribution:** credit the FlyWire Consortium and the primary publications
  listed in `REFERENCES.md` when using or redistributing the data or derived
  artifacts.
- **Scope:** adult female *Drosophila melanogaster* brain (FAFB). The dataset
  does not contain a complete ventral nerve cord.
- **Endorsement:** attribution does not imply that FlyWire or the dataset
  authors endorse this simulator or its conclusions.

The raw downloads are not redistributed in this repository. The tracked
`datasets/processed/connectome.npz`, `datasets/processed/nodes.csv.gz`,
`datasets/processed/connectome_report.json` and `datasets/manifest.json`
contain information derived from the FlyWire release. Redistribution and reuse
of that derived information remain subject to CC BY 4.0 attribution. The model
parameters, activity and scientific interpretations are this project's own and
are not part of the FlyWire dataset.

## BANC connectome

- **Dataset:** Brain And Nerve Cord (BANC) connectome, version 888.
- **Publisher:** BANC Consortium; see `REFERENCES.md` and
  `FLY-SURFER-DATA/documentation/LICENSES_AND_ATTRIBUTION.md`.
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Scope:** the derived BANC artifacts were examined for structural
  comparison only. They are regenerated from the raw download and are kept
  local; they are not redistributed in this repository.
- **Attribution:** credit the BANC Consortium and the primary publication when
  reusing the BANC data or derived artifacts.

## Subway Surfers Object Dataset

- **Dataset:** Subway Surfers Object Dataset, version 15.
- **Source:** Roboflow Universe, workspace `horizon-cgt2k`.
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Use here:** 12 preview frames are tracked under
  `experiments/phase_3b/previews/` for auditing, and 30 further frames from the
  curated dataset are used as illustration in the six visual-documentation
  figures (paper Figures 9–14). The dataset was used to fine-tune the project's
  YOLO11n detector (50 epochs, 2026-11-06); the weights and ONNX export are not
  redistributed and remain AGPL-3.0 (see below).
- **Attribution:** "Subway Surfers Object Dataset" by `horizon-cgt2k` on
  Roboflow Universe, licensed CC BY 4.0. The full attribution and modification
  record is reproduced in
  `FLY-SURFER-DATA/datasets/subway_surfers_v15/curated/provenance/attribution.txt`.
- **Trademark:** "Subway Surfers" is a trademark of its owners. The images are
  used for research documentation only; this project is not affiliated with or
  endorsed by the game's owners.

## YOLO11n detector weights

- **Component:** Ultralytics YOLO11n checkpoint and its ONNX export
  (`models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx`, SHA-256
  `e6ad18f9…6aa77`). The deployed files are a project fine-tune of the upstream
  YOLO11n release (50 epochs, 2026-11-06), not the upstream checkpoint itself.
- **Licence:** GNU Affero General Public License v3.0 (AGPL-3.0).
- **Distribution:** the weights and the ONNX file are **not** redistributed in
  this repository and are excluded by `.gitignore` (`models/`, `*.onnx`,
  `*.pt`). Their size, hash and deployment contract are recorded in
  `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md`. Anyone who obtains them
  separately is bound by the AGPL-3.0.

## Python runtime and libraries

The versions below are those used to produce the committed benchmark results.
They are pinned in `requirements.txt`.

| Component | Version | Licence | Project |
|---|---:|---|---|
| Python | 3.13.14 | Python Software Foundation License | <https://www.python.org/> |
| NumPy | 2.3.4 | BSD 3-Clause | <https://numpy.org/> |
| pandas | 2.3.3 | BSD 3-Clause | <https://pandas.pydata.org/> |
| Matplotlib | 3.10.7 | Matplotlib License (PSF-based) | <https://matplotlib.org/> |
| PyYAML | 6.0.3 | MIT | <https://pyyaml.org/> |
| psutil | 7.1.2 | BSD 3-Clause | <https://github.com/giampaolo/psutil> |
| Pillow | 12.0.0 | MIT-CMU (HPND) | <https://python-pillow.org/> |
| onnxruntime | 1.29.0 | MIT | <https://onnxruntime.ai/> |
| pytest | 7.4.3 | MIT | <https://pytest.org/> |

The full licence text for each package is distributed with that package and is
available from its project page. This notice is an attribution summary, not a
replacement for those licences.

## Data and figures produced by this project

The simulation results, benchmark tables, plots and reports in
`experiments/` were generated by this project's code from the FlyWire-derived
connectome and the model assumptions documented in `configs/` and the root
`README.md`. They are simulated outputs, not measurements of a living fly.
