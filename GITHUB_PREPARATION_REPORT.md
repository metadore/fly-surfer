# GitHub preparation report

Project: **FLY-SURFER**  
Prepared: **2026-11-04**  
Scope: repository audit, documentation, Git initialization, staging and safety verification.  
Status: **staged locally; not committed or pushed.**

## 1. Executive summary

FLY-SURFER is ready for review as a reproducible research repository, with one
important blocker: the target GitHub repository already contains an unrelated
history and a different root README. No remote change, commit, merge or push was
performed.

- 64 project files are staged on local branch `main` (65 after this report).
- Staged project size: **38,967,971 bytes (37.16 MiB / 38.97 MB)**.
- Largest file: `datasets/processed/connectome.npz`, **28,013,212 bytes
  (26.72 MiB)**. No file reaches GitHub's 50 MiB warning or 100 MiB limit.
- All 68 automated tests pass.
- No raw FlyWire data, caches, runtime logs, credentials or API keys are staged.
- The root `README.md` was treated as read-only and is byte-for-byte unchanged
  (SHA-256 `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10`).
- Git LFS is **not** justified for the current tree.

## 2. Repository audit

### 2.1 Project contents

| Category | Count | Notes |
|---|---:|---|
| Python source modules | 21 | Brain, experiments, audit and architecture scaffolding |
| Test modules | 9 | `conftest.py` plus 8 test files; 68 tests |
| YAML configs | 3 | Simulation, neuron parameters, Phase 2.5 suite |
| Markdown documentation | 6 | Includes the unchanged root README |
| JSON metadata/results | 11 | Manifest, reconstruction report, benchmark and experiment reports |
| PNG figures | 6 | Phase 2 and Phase 2.5 plots |
| Processed artifacts | 3 | Connectome `.npz`, nodes `.csv.gz`, reconstruction report |
| Other reproducibility files | 5 | `.gitignore`, `.gitattributes`, `requirements.txt`, `pytest.ini`, `selected_neurons.csv` |

The implemented layers are:

- `dataset_audit.py` — Phase 0 audit and manifest generation.
- `brain/connectome_loader.py` — validated reconstruction and artifact loading.
- `brain/neuron_model.py` — vectorised LIF dynamics.
- `brain/synapse_model.py` — sparse CSR propagation, weights, signs and delays.
- `brain/neural_activity.py` — bounded spike recording, rates and plots.
- `brain/subgraph.py` — induced subgraphs and reproducible connected sampling.
- `brain/brain_simulator.py` — time-stepped simulation, stimulation and diagnostics.
- `experiments/baseline.py` — Phase 2 experiment, metadata, report and CLI.
- `experiments/phase_2_5/benchmark.py` and `run_all.py` — benchmark isolation,
  validation, plots and reports.
- `environment/`, `learning/`, `motor/` and `sensory/` — one-line architectural
  scaffolding for future phases; included for completeness, not presented as
  implemented functionality.

### 2.2 Verified research state

- **Phase 0:** 15 FlyWire files audited; schemas, checksums, ID coverage and
  connection semantics recorded in `datasets/manifest.json`.
- **Phase 1:** 139,255 neurons, 3,732,460 directed edges and 50,666,648 summed
  synapses; zero self-connections; artifact round-trip checks passed.
- **Phase 2:** LIF simulation, sparse synapses, activity recording, 800-neuron
  reproducible experiment and report.
- **Phase 2.5:** 800 to 139,255 neurons; full-connectome run completed in
  2.923 s for 400 steps at 138 steps/s with a 270.8 MB process peak.
- **Tests:** `python -m pytest -q` → **68 passed**.

The scientific limitations remain as documented in the root README: one seed
and one 200 ms protocol for the scalability suite, arbitrary weight transform,
coarse transmitter-sign assumptions, no sensory encoding, no motor decoding,
no learning and no game integration.

## 3. Git context and target remote

### 3.1 Local repository

The project did not have its own `.git` directory. It was nested inside an
existing home-directory Git worktree with an unrelated remote. To avoid touching
that worktree or its remote, a new independent repository was initialized:

```bash
git init -b main
git remote add origin https://github.com/metadore/fly-surfer.git
git fetch origin main
```

- Local repository root: `FLY-SURFER/`.
- Branch: `main` (unborn; no commit created).
- Origin: `https://github.com/metadore/fly-surfer.git`.
- No upstream branch was configured.
- No parent-repository file was staged or modified.
- Do not run `git add` for this project from the parent home-directory worktree;
  it would see an embedded repository.

### 3.2 Remote repository conflict — action required

The target repository is **public and not empty**:

| Remote fact | Value |
|---|---|
| Default branch | `main` |
| Latest commit | `369a0a8` — "Document open-source repositories and research references" |
| Commit date | 2026-11-04T07:48:29Z |
| Files at root | `Readme.md` only |
| `Readme.md` size | 63,485 bytes, 408 lines |
| Repository size reported by GitHub | 42 KB |

The remote `Readme.md` is a different FLY-SURFER project-vision document. The
local finalized `README.md` is 14,935 bytes and is a different file. The names
differ only by case, which collides on Windows and macOS checkouts.

**No push, force-push, merge, rebase or remote edit was performed.** Before any
push, the histories and README naming must be reconciled. Recommended options:

1. **Preserve the remote document (recommended).** On a new branch or pull
   request, rename the remote `Readme.md` to a non-colliding path such as
   `docs/PROJECT_VISION.md`, preserving its full content, then add the local
   `README.md` and project tree.
2. **Use a fresh repository.** If `metadore/fly-surfer` is not the intended
   home for this codebase, create an empty repository and push there, leaving
   the existing repository untouched.
3. **Do not** force-push or delete the remote file. Either would overwrite
   existing work and is outside the approved scope.

Because the local repository has no commit, its future history is unrelated to
`origin/main`. A merge will require `--allow-unrelated-histories` or a
branch-with-PR workflow after the filename conflict is resolved.

## 4. Files included

### 4.1 Project metadata and documentation

- `.gitattributes` — LF policy and binary markers for `.npz`, `.gz`, `.png`.
- `.gitignore` — specific exclusions (full contents in section 7).
- `README.md` — unchanged, read-only project documentation.
- `requirements.txt` — pinned runtime and test dependencies.
- `REFERENCES.md` — FlyWire, FAFB, modelling and software citations.
- `THIRD_PARTY_NOTICES.md` — data attribution and dependency licences.
- `datasets/README.md` — audit plus repository data policy, reconstruction and
  licensing guidance.
- `datasets/manifest.json` — Phase 0 machine-readable audit.
- `datasets/processed/connectome.npz` — validated CSR connectome.
- `datasets/processed/nodes.csv.gz` — node annotations and positions.
- `datasets/processed/connectome_report.json` — reconstruction provenance and
  round-trip checks.

### 4.2 Source, configuration and tests

- `brain/` — six simulation modules.
- `dataset_audit.py`, `main.py`.
- `experiments/baseline.py`, `benchmark.py`, `run_all.py`, `evaluation.py`,
  `training.py`.
- `environment/`, `learning/`, `motor/`, `sensory/` scaffolding.
- `configs/neuron_config.yaml`, `configs/simulation_config.yaml`,
  `experiments/phase_2_5/configs/scalability_suite.yaml`.
- `tests/` — `conftest.py` and eight test modules.
- `pytest.ini` — test discovery and the environment-specific anyio workaround.

### 4.3 Research outputs

- Phase 2: `activity.npz`, `selected_neurons.csv`, `simulation_metadata.json`,
  `experiment_report.json`, `raster.png`, `firing_rates.png`.
- Phase 2.5: six benchmark JSONs (including the 800-neuron repeat), four plots,
  `scalability_report.json`, `scalability_report.md`, `memory_report.md`.

### 4.4 Full staged file list

The 64 staged project files are listed in Appendix A. This report is added as
the 65th staged file after the audit.

## 5. Files excluded

| Excluded category | Paths / reason |
|---|---|
| Raw FlyWire datasets | `datasets/raw/**` — 15 complete gzip files, 368,874,372 bytes (~352 MiB); immutable third-party data |
| Incomplete downloads | `*.crdownload`, `*.part`, `*.partial`, `*.download`; four partial downloads were left untouched outside the tracked tree |
| Python caches | `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.ipynb_checkpoints/` |
| Runtime logs | `*.log`; six benchmark logs (1.4 KB total) contain absolute local paths and are regenerated by `run_all.py` |
| Virtual environments | `.venv/`, `venv/`, `env/`, `ENV/` (none present) |
| Editor/OS files | `.idea/`, `.vscode/`, `.DS_Store`, `Thumbs.db`, swap files |
| Secrets and local env | `.env`, `.env.*` (except `.env.example`), keys, certificates, `id_rsa*`, `secrets/`, `credentials/` |
| Temporary arrays | `*.npy`, `*.h5`, `*.hdf5`, `experiments/**/tmp/`, `experiments/**/scratch/` |
| Source licence | `LICENSE` is absent because no project licence has been chosen |
| Remote `Readme.md` | Present only as `origin/main`; not copied into the working tree |

No file was deleted, moved, recompressed or renamed. The raw data remains in its
original local location.

## 6. Large-file analysis and GitHub limits

GitHub currently warns at **50 MiB**, blocks individual files over **100 MiB**,
and recommends repositories under **1 GB**. The largest staged files are:

| File | Bytes | MiB | Status |
|---|---:|---:|---|
| `datasets/processed/connectome.npz` | 28,013,212 | 26.72 | Below 50 MiB; commit directly |
| `datasets/processed/nodes.csv.gz` | 9,550,849 | 9.11 | Commit directly |
| `experiments/phase_2_5/plots/memory_vs_size.png` | 183,575 | 0.18 | Commit directly |
| `experiments/phase_2_5/plots/spike_count_vs_size.png` | 154,189 | 0.15 | Commit directly |
| `experiments/phase_2_5/plots/speed_vs_size.png` | 137,348 | 0.13 | Commit directly |
| `experiments/phase_2_5/plots/active_neurons_vs_size.png` | 118,552 | 0.11 | Commit directly |

- Files over 50 MiB: **0**.
- Files over 100 MiB: **0**.
- Git LFS: **not justified** for the current tree. A 26.7 MiB one-time binary
  artifact is simpler and cheaper to track directly than LFS, which adds client
  requirements and storage/bandwidth quotas.
- Estimated initial push: **~37 MiB / ~39 MB** (working-tree bytes; Git object
  compression may slightly reduce text and may not reduce the `.npz` much).
- If raw data or skeleton archives are ever versioned, they must use LFS or
  external storage, not ordinary Git. The 263 MiB unfiltered table alone would
  exceed the 100 MiB hard limit.

## 7. Final `.gitignore`

```gitignore
# ---------------------------------------------------------------------------
# FLY-SURFER Git exclusions
#
# The raw FlyWire downloads stay local. Derived connectome artifacts and
# research outputs are intentionally tracked; do not add broad rules for
# *.json, *.csv, *.gz, *.png or *.npz.
# ---------------------------------------------------------------------------

# Raw FlyWire source data (15 gzip files, ~388 MB compressed). Never commit.
datasets/raw/**

# Incomplete downloads and temporary archives
*.crdownload
*.part
*.partial
*.download
*.tmp
*.temp
*.bak
*~

# Python caches, bytecode and test/build artifacts
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.ipynb_checkpoints/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
build/
dist/
*.egg-info/

# Virtual environments
.venv/
venv/
env/
ENV/
.python-version

# Editor and OS metadata
.idea/
.vscode/
*.swp
*.swo
.DS_Store
Thumbs.db
desktop.ini

# Local environment files, credentials and keys
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
id_rsa*
secrets/
credentials/

# Runtime logs (regenerated by the experiment runners)
*.log

# Temporary simulation and intermediate array outputs
experiments/**/tmp/
experiments/**/scratch/
*.npy
*.h5
*.hdf5

# Intentionally tracked research artifacts (not ignored):
#   datasets/manifest.json
#   datasets/processed/connectome.npz
#   datasets/processed/nodes.csv.gz
#   datasets/processed/connectome_report.json
#   experiments/**/results/*.json
#   experiments/**/plots/*.png
#   experiments/**/reports/*.md
```

## 8. Security audit

Searched all 64 staged text files for private keys, AWS access keys, GitHub
tokens, OpenAI/Google/Slack tokens and credential assignments.

- **Credentials/secrets found: none.**
- **Sensitive filenames found: none** (`.env`, `.pem`, `.key`, `.p12`, `.pfx`,
  `id_rsa*`, private-key blocks).
- **Raw data staged: none.**
- **Caches or logs staged: none.**
- **Absolute local paths in Markdown, Python, YAML or `.gitignore`: none.**
- **Absolute paths in generated JSON provenance:** 37 string values across
  8 files:
  - `datasets/manifest.json`: 1 (`provenance.local_root`);
  - `experiments/phase_2_5/reports/scalability_report.json`: 18;
  - each of the six benchmark result JSONs: 3 (interpreter, suite path, output path).

These paths are provenance metadata, not credentials. They include the local
user-directory name. The excluded benchmark logs contain similar paths. If path
privacy is required before publication, regenerate the JSON artifacts on a
neutral path or add a reviewed redaction step to the result writer; do not edit
the raw data. No secret values were printed during this audit.

Additional operational concerns:

- The remote is public. Only the derived 28 MB connectome and small outputs
  would be published; the 352 MiB raw downloads remain local.
- The remote already contains an unrelated commit and a root `Readme.md`;
  pushing without reconciliation risks a case-collision or overwriting work.
- The project is nested inside a home-directory Git worktree. Always run Git
  commands from `FLY-SURFER/`, never stage this directory from the parent.
- `datasets/manifest.json` may include sample rows from public FlyWire
  annotation tables. No credentials or private records were found.
- No Git hooks, credentials, or global Git configuration were modified.

## 9. README preservation verification

The root `README.md` was treated as read-only.

| Check | Result |
|---|---|
| Original size | 14,935 bytes |
| Original SHA-256 | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` |
| Backup comparison | Byte-for-byte identical (`cmp` passed) |
| Checksum after documentation and staging | Same SHA-256 |
| Staged blob checksum | Same SHA-256 (`git show :README.md`) |
| Content edits | **None** |

The only README edited was `datasets/README.md`, which is a separate dataset
document. It gained repository data-policy, reconstruction, licensing and
attribution sections; its Phase 0 audit content is otherwise preserved. Note
that `dataset_audit.py` regenerates that file, so re-running the audit would
remove the hand-maintained sections unless the generator is updated in a
separate reviewed change.

## 10. Git staging verification

Commands run from `FLY-SURFER/`:

```bash
git status
git check-ignore -v <paths>
git ls-files
git diff --cached --stat
git diff --cached --name-only
```

Results:

- `git status --short` → **65 staged entries**, all beginning with `A`; no commit exists.
- `git diff --cached --name-only` → **65 files**.
- `git diff --cached --stat` → **65 files changed**; binary artifacts are reported
  separately by Git.
- Staged working-tree size → approximately **38.99 MB (37.18 MiB)**; largest
  file remains the 28,013,212-byte connectome.
- Exclusion grep for `datasets/raw/`, `__pycache__/`, `.pytest_cache/`, `*.log`,
  `*.crdownload`, `.env` → **no matches**.
- Required-file check → root README, requirements, references, notices,
  processed connectome, nodes, reconstruction report and `.gitignore` all
  present.
- `git check-ignore -v` → raw data, logs, caches and pytest cache correctly
  ignored; processed artifacts, plots, results and README correctly **not**
  ignored.
- `git show :README.md | sha256sum` → `6277ffbb...` (matches the original).
- `python -m pytest -q` → **68 passed**.
- Final index: **65 files, approximately 38.99 MB (37.18 MiB)**.
- No commit, no merge, no rebase, no push and no force operation was performed.

## 11. Proposed initial commit message

```text
Initial commit: FLY-SURFER connectome simulation and benchmarks

Import the validated FlyWire FAFB connectome artifact, the sparse LIF
simulation layer, reproducible Phase 2 and Phase 2.5 experiments,
benchmark reports and plots, tests, and reproducibility documentation.
Raw FlyWire downloads remain local and are excluded from version control.
```

Because `origin/main` already has two unrelated commits, this message should be
used only after the remote reconciliation described in section 3.2. A
branch/PR workflow may use the same subject.

## 12. Remaining manual actions

1. **Resolve the remote conflict.** Decide whether `metadore/fly-surfer` is the
   intended target. If yes, preserve its `Readme.md` under a non-colliding path
   and reconcile the unrelated histories on a branch or PR. Do not force-push.
2. **Choose a source licence.** No `LICENSE` was created because no licence has
   been selected. Add it only after the authors decide; do not assume the code
   is open source before then.
3. **Decide on path redaction.** The generated JSON provenance contains 37
   absolute-path strings. If they should not be public, plan a reviewed
   redaction or regeneration step.
4. **Approve and commit.** Review the staged tree and approve the commit
   explicitly. Nothing has been committed.
5. **Push after reconciliation.** Push only after the remote history and README
   naming conflict are resolved. A normal push will otherwise be rejected or
   create a case-colliding tree.
6. **Optional citation metadata.** Add `CITATION.cff` and an archived release
   DOI after author and licence decisions.
7. **Regeneration caveat.** If `dataset_audit.py` is rerun, re-apply the
   repository-policy sections in `datasets/README.md` or update the generator.

## 13. Reproducibility commands

```bash
# Install pinned dependencies
python -m pip install -r requirements.txt

# Run the automated test suite
python -m pytest -q

# Reproduce the Phase 2 experiment
python main.py --no-progress

# Reproduce the Phase 2.5 suite
python -m experiments.phase_2_5.run_all

# Regenerate Phase 2.5 plots/reports from stored results
python -m experiments.phase_2_5.run_all --reports-only

# Rebuild the processed connectome (requires the local raw files)
python -m brain.connectome_loader
```

## 14. Sources

- GitHub large-file limits: <https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>
- FlyWire v783 data release: <https://doi.org/10.5281/zenodo.10676866>
- FlyWire Codex and citation requirements: <https://codex.flywire.ai/>
- Dorkenwald et al. (2024): <https://doi.org/10.1038/s41586-024-07558-y>
- Schlegel et al. (2024): <https://doi.org/10.1038/s41586-024-07686-5>
- Zheng et al. (2018): <https://doi.org/10.1016/j.cell.2018.06.019>
- Target repository: <https://github.com/metadore/fly-surfer>

## Appendix A — staged project files

```text
.gitattributes
.gitignore
README.md
REFERENCES.md
THIRD_PARTY_NOTICES.md
brain/brain_simulator.py
brain/connectome_loader.py
brain/neural_activity.py
brain/neuron_model.py
brain/subgraph.py
brain/synapse_model.py
configs/neuron_config.yaml
configs/simulation_config.yaml
dataset_audit.py
datasets/README.md
datasets/manifest.json
datasets/processed/connectome.npz
datasets/processed/connectome_report.json
datasets/processed/nodes.csv.gz
environment/game_controller.py
environment/subway_environment.py
experiments/baseline.py
experiments/evaluation.py
experiments/phase_2_5/benchmark.py
experiments/phase_2_5/configs/scalability_suite.yaml
experiments/phase_2_5/plots/active_neurons_vs_size.png
experiments/phase_2_5/plots/memory_vs_size.png
experiments/phase_2_5/plots/speed_vs_size.png
experiments/phase_2_5/plots/spike_count_vs_size.png
experiments/phase_2_5/reports/memory_report.md
experiments/phase_2_5/reports/scalability_report.json
experiments/phase_2_5/reports/scalability_report.md
experiments/phase_2_5/results/benchmark_full.json
experiments/phase_2_5/results/benchmark_n20000.json
experiments/phase_2_5/results/benchmark_n5000.json
experiments/phase_2_5/results/benchmark_n50000.json
experiments/phase_2_5/results/benchmark_n800.json
experiments/phase_2_5/results/benchmark_n800_repeat.json
experiments/phase_2_5/run_all.py
experiments/results/initial/activity.npz
experiments/results/initial/experiment_report.json
experiments/results/initial/firing_rates.png
experiments/results/initial/raster.png
experiments/results/initial/selected_neurons.csv
experiments/results/initial/simulation_metadata.json
experiments/training.py
learning/dopamine.py
learning/mutual_information.py
learning/synaptic_plasticity.py
main.py
motor/action_decoder.py
pytest.ini
requirements.txt
sensory/game_state.py
sensory/visual_encoder.py
tests/conftest.py
tests/test_artifact_compatibility.py
tests/test_configs.py
tests/test_neural_activity.py
tests/test_neuron_model.py
tests/test_phase_2_5_benchmark.py
tests/test_simulator.py
tests/test_subgraph.py
tests/test_synapse_model.py
```

---

## Post-commit incident and recovery (2026-11-04)

### What happened

The initial commit `dec22bc` ("feat: add FlyWire connectome simulation and
benchmarks") was pushed to `origin/main`. It added 64 project files but **did
not contain the project `README.md`**. The repository instead still carries the
remote vision document at `Readme.md`.

Cause: at 16:39 the branch was moved with `git reset` to `origin/main`. On this
case-insensitive Windows filesystem, checking out the remote `Readme.md`
overwrote the local `README.md` with 63,485 bytes of vision-document text. The
subsequent `git add` therefore tracked `Readme.md` (vision document) and never
saw the 14,935-byte project README.

No backup of the README remained in the working tree. The original content was
recovered from the dangling blob `47519e08`, whose SHA-256 is
`6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` — identical
to the hash recorded before staging. The README was restored byte-for-byte and
has not been edited.

### Corrective change staged (not committed)

| Status | Path | Note |
|---|---|---|
| `A` | `README.md` | Original project README, restored byte-for-byte (SHA-256 verified) |
| `R100` | `Readme.md` → `docs/PROJECT_VISION.md` | Remote vision document preserved, content unchanged |
| `M` | `.gitignore` | Added `references/` |

This resolves the case collision that existed before the first push: the
repository can now hold `README.md` and the vision document in distinct,
non-colliding paths.

### New untracked directory: `references/`

The repository now contains 70 cloned third-party files totalling
**208,839,820 bytes (199.2 MiB)**, across `references/fly-brain-main/`,
`references/fly-hero-master/` and `references/Drosophila_brain_model-main/`.
The largest file is a 100,804,642-byte (96.1 MiB) Parquet table; the largest
archive is 86,630,944 bytes. Each clone carries its own `LICENSE`.

Handling: excluded via `references/` in `.gitignore`. These are reference
clones, not project source. The 96.1 MiB Parquet file sits just under GitHub's
100 MiB hard per-file limit, so a future `git add .` would risk a rejected push
and a large object in history. Nothing was deleted, moved or modified.

### Verification after recovery

- `git show :README.md | sha256sum` → `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10`
- `git check-ignore -v references/fly-brain-main/.../2025_Connectivity_783.parquet` → `.gitignore:78:references/`
- `git status --porcelain` → only the three staged corrective entries, no untracked files
- No raw dataset, cache, log or credential staged

### Proposed corrective commit message

```text
fix: restore project README and preserve vision document

The initial commit was created after a reset to origin/main; on a
case-insensitive checkout the remote Readme.md (vision document)
overwrote the local README.md, so the project README was never
committed.

- restore README.md byte-for-byte (SHA-256 6277ffbb...)
- move the existing Readme.md content to docs/PROJECT_VISION.md
- ignore references/ (208.8 MB of cloned third-party repositories)

Data, processed artifacts and experiment outputs are unchanged.
```

Commit and push still require explicit approval.
