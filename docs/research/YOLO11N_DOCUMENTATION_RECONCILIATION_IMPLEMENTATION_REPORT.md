# YOLO11n Documentation Reconciliation — Implementation Report

**Date:** 2026-11-25
**Status:** implementation and verification complete. **Nothing was staged,
committed, pushed, uploaded or published.** The owner will review and separately
authorise publication.
**Basis:** owner approval of the corrections proposed in
`docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md`.
**Primary evidence:** `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md`
(I1–I17) and the preserved notebook (SHA-256
`3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da`).

---

## 1. Constraints honoured

| Prohibition | Evidence |
|---|---|
| Do not modify `best.pt` or `best.onnx` | Both re-hashed after the edits; unchanged (§7.6) |
| Do not modify the original or preserved notebook | Both copies re-hashed; unchanged (§7.6) |
| Do not modify the dataset | No dataset file written; no dataset path appears in either repository's `git status` |
| Do not modify any licence file | `LICENSE` and `research_paper/LICENSE` identical to `HEAD` (§7.7) |
| Do not upload model weights | No network write of any kind was performed |
| Do not create or rename repositories | Two existing repositories only |
| Do not install or upgrade packages | No package command was run |
| Do not perform Git operations | Only read-only `git status`, `git diff`, `git log`, `git show` were used |
| Do not stage/commit/push/reset/rebase/checkout/stash/clean | None was run; working tree remains unstaged |
| Do not modify published paper files | No file under `research_paper/` was written by this task (§9) |
| Do not create or publish a Zenodo version | No Zenodo action was taken (§9) |

---

## 2. Applied corrections — I1–I17

Every item below was re-read in place after editing.

| ID | Severity | Location | Action taken | Status |
|---|---|---|---|---|
| I1 | S1 | `README.md` §3.3 | "How it was used" now states the 50-epoch fine-tune of a COCO-pretrained checkpoint on the 1,188-image training side, Colab 2026-11-06, Ultralytics 8.4.202, and evaluation on 1,128 images; weights not redistributed | Applied |
| I2 | S1 | `README.md` §4 | "fixed, externally trained … not retrained or fine-tuned" replaced by "fine-tuned once for this project … then frozen as a versioned ONNX artifact" | Applied |
| I3 | S1 | `README.md` limitations | "not trained or calibrated here" replaced by "trained outside this repository … consumed here as a fixed ONNX artifact … metrics not re-measured here" | Applied |
| I4 | S2 | `FLY-SURFER-DATA/documentation/MODEL_REGISTRY.md` §1.6 + §1.7 | §1.6 now attributes the metrics to a post-training ONNX Runtime CPU re-validation and states the stage-B precision difference (0.9373 vs 0.927); §1.7 lists stages A, B and C separately | Applied |
| I5 | S3 | readiness audit vs execution | Audit left unedited; new `docs/research/YOLO11N_TRAINING_AUTHORISATION_RECORD.md` records the execution-before-clearance gap and explicitly disclaims retroactive approval | Recorded |
| I6 | S4 | model card / registry | `MODEL_REGISTRY.md` §1.7 now states that any printed per-class value for the two zero-instance classes is an indexing artefact, not a measurement | Applied |
| I7 | S5 | `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` | Dated note added: `dataset.yaml` uses `path: '.'`; the recorded run used `dataset_colab.yaml` with an absolute path | Applied |
| I8 | S6 | notebook cells 3–9 | No repository edit (notebook-internal); already documented in the recovery report | No edit required |
| I9 | S6 | notebook metadata | No repository edit; citation caution already in the recovery report | No edit required |
| I10 | S5 | audit §10.3; export report §6 | Historical proposals left unedited; export report now carries a "Superseded by the executed run" note (50 epochs, Python 3.13.16, `dataset_colab.yaml`) | Applied |
| I11 | S4 | base checkpoint identity | `MODEL_REGISTRY.md` §1.10: local hash `0ebbc80d…4ee1` is identical, but the run-time download was never hashed and no upstream checksum exists | Applied |
| I12 | S4 | `best.pt` producing epoch | §1.10: mAP@0.5:0.95 peaked at 0.689 on epochs 48 and 49; `results.csv` not preserved | Applied |
| I13 | S4 | `exist_ok=True` | §1.10: an earlier run of the same name cannot be excluded | Applied |
| I14 | S4 | confidence 0.426 | §1.10: initial uncalibrated candidate; derivation not documented | Applied |
| I15 | S5 | notebook mtime vs run date | No edit; every new document cites **2026-11-06**, never the file mtime | No edit required |
| I16 | S4 | Colab attestation | §1.10: no Colab file id/provenance record; identity rests on SHA-256 agreement | Applied |
| I17 | S1 | integration report vs public prose | Resolved mechanically by I1–I3 and A9; all public documents now describe one provenance | Resolved |

---

## 3. Additional occurrences — A1–A9

| # | Location | Action | Status |
|---|---|---|---|
| A1 | `research_paper/src/05_perception.md:7`; complete paper `:760` | Proposed in `docs/research/RESEARCH_PAPER_V11_PROVENANCE_CORRECTION_PROPOSAL.md` | **Not applied — published paper protected** |
| A2 | `research_paper/src/03_data.md:5`; complete paper `:538` | Proposed in the same correction record | **Not applied — published paper protected** |
| A3 | `research_paper/src/05_perception.md:120`; complete paper `:873` | Proposed in the same correction record | **Not applied — published paper protected** |
| A4 | `research_paper/figures/yolo11_visuals/FIGURE_INDEX.md:13` | Proposed in the same correction record | **Not applied — published paper protected** |
| A5 | `docs/PHASE_3_ROADMAP.md:236` (and the same claim at `:42`) | Changed "taken from the training run" to "post-training ONNX CPU re-validation" | Applied |
| A6 | `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md:93, 203, 219, 339, 543` | All five attributions changed to post-training ONNX CPU re-validation | Applied |
| A7 | `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:32, 50–53, 336–337` | "Training-run metrics" replaced by "Post-training ONNX CPU re-validation metrics"; stages A/B/C distinguished | Applied |
| A8 | `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md:576` | Thresholds now "carried over from the deployment config produced in the training notebook" | Applied |
| A9 | `THIRD_PARTY_NOTICES.md:81–86` | Now states the dataset fine-tuned the project's detector (50 epochs, 2026-11-06); weights/ONNX not redistributed, AGPL-3.0 | Applied |

Two further occurrences of the same threshold-provenance error were corrected
alongside A7/A8 in `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md:12` and
`:320–321`; one further occurrence of the same metric-attribution error was
corrected in `reports/PHASE_3B_EVALUATION.md:12–13`.

---

## 4. Unresolved contradictions and deliberate non-edits

### 4.1 Published paper (A1–A4)

The version 1.1 paper is published on Zenodo. Its source files were **not**
modified. The four detector-provenance corrections are held in a separate
proposal (`RESEARCH_PAPER_V11_PROVENANCE_CORRECTION_PROPOSAL.md`), which also
lists the paper statements that are already correct and must not be changed.
Until the owner authorises a future version, the paper and the repository will
describe the detector's origin differently. This is an intentional, documented
contradiction, not a silent resolution.

### 4.2 Generated Phase 3C result documents

Two generated audit outputs still call the published metrics "training-run
numbers":

- `experiments/phase_3c/results/p3_t5_t11_acceptance_audit.md:62–63`;
- `experiments/phase_3c/results/p3_final_phase3_audit.md:155–157`.

They were **not edited**. They are frozen outputs of prior acceptance and final
audits, not narrative documentation, and editing them in place would break their
recorded integrity. If a future audit is regenerated, its generator's wording
should be changed to "post-training ONNX CPU re-validation metrics". Until then,
these two lines remain the only known stale metric attributions outside the
protected paper tree.

### 4.3 Items that required no repository edit

I8 (Drive-state inconsistency), I9 (non-contiguous execution counts) and I15
(notebook mtime) are notebook-internal or citation-hygiene issues. They remain
documented in the recovery report; no repository prose was changed.

### 4.4 Licensing

Unresolved by design; see §8.

### 4.5 Reproducibility

Bit-exact reproduction of `best.pt` is not claimed anywhere. The new registry
section states the procedure is documented but the weights are not promised to
be bit-reproducible (`deterministic=False`, auto-selected optimiser, unhashed
base download, unpreserved logs).

---

## 5. New documents created

| Document | Lines | Purpose |
|---|---:|---|
| `docs/research/YOLO11N_TRAINING_AUTHORISATION_RECORD.md` | 111 | I5 governance record; explicitly **not** retroactive approval |
| `docs/research/RESEARCH_PAPER_V11_PROVENANCE_CORRECTION_PROPOSAL.md` | 126 | A1–A4 proposed corrections for a future paper version; no version created |
| `docs/research/YOLO11N_DOCUMENTATION_RECONCILIATION_IMPLEMENTATION_REPORT.md` | this file | Implementation and verification record |

The proposal document
`docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md`
was updated with an implementation-status note and one numeric typo corrected
(`0.9272` → `0.927`). No other content of that proposal was changed.

---

## 6. Changed-file inventory

### 6.1 Modified tracked files — main repository

`git diff --numstat` (read-only):

| File | Lines added | Lines removed |
|---|---:|---:|
| `README.md` | 16 | 8 |
| `THIRD_PARTY_NOTICES.md` | 5 | 4 |
| `docs/PHASE_3_ROADMAP.md` | 6 | 5 |
| `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` | 11 | 9 |
| `reports/PHASE_3B2B1_YOLO11N_DATASET_EXPORT.md` | 10 | 0 |
| `reports/PHASE_3B2B3_YOLO11N_ONNX_INTEGRATION.md` | 16 | 10 |
| `reports/PHASE_3B2C_REAL_SEQUENCE_REPLAY.md` | 2 | 2 |
| `reports/PHASE_3B_EVALUATION.md` | 3 | 2 |

### 6.2 Modified tracked file — data repository

| File | Lines added | Lines removed |
|---|---:|---:|
| `documentation/MODEL_REGISTRY.md` | 25 | 4 |

### 6.3 Edited untracked document

| File | Change |
|---|---|
| `docs/research/YOLO11N_RELEASE_READINESS_AND_DOCUMENTATION_RECONCILIATION.md` | Status note added; `0.9272` → `0.927` |

### 6.4 Created documents

Listed in §5. They are untracked.

### 6.5 Not changed by this task

- `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.docx` — already modified
  before this task began (§9); left untouched.
- `research_paper/~$Y_SURFER_COMPLETE_RESEARCH_PAPER.docx` — pre-existing Word
  lock file; left untouched.
- `docs/research/YOLO11N_TRAINING_PROVENANCE_RECOVERY.md`,
  `docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md` — read-only here.
- Every dataset, model, notebook and licence file.

---

## 7. Verification results

### 7.1 I1–I17 recheck

All 17 items were re-read in place. I1–I7, I10–I14, I16 and I17 are reflected in
the documents as described in §2. I8, I9 and I15 required no edit and carry their
documentation forward unchanged. I5 is recorded in a new document because editing
the historical audit would falsify it.

### 7.2 A1–A9 recheck

A5–A9 are applied and re-read. A1–A4 remain in the protected paper tree and are
captured in the correction proposal. No occurrence of "not used to train" or
"third-party YOLO11n release" remains outside the historical analysis documents
(the provenance report, the licensing audit and the reconciliation proposal,
where they are quoted as the errors being corrected).

### 7.3 Statements that must not be over-corrected

| Statement | Verification |
|---|---|
| Paper: "not retrained … to produce any of these panels/for this figure" | Paper source unchanged; verified in place |
| Paper: "produced in the training environment; not re-measured on this host" | Unchanged |
| `RESEARCH_PAPER_VALIDATION_REPORT.md:285` task-scoped claim | Unchanged |
| README licence row "YOLO11n weights / ONNX export — AGPL-3.0, not redistributed" | Present at `README.md:370` |
| `configs/detector_config.yaml` "starting points, not calibrated" | Unchanged at lines 46–47 |
| `MODEL_REGISTRY.md` zero-class / no-test-set limitations | Present at §1.7, now with the additional artefact sentence |

### 7.4 Markdown tables and links

A structural check over every changed and created Markdown file found:

- inconsistent table pipe counts: **0**;
- unresolved relative links: **0**.

### 7.5 Remaining contradictory training claims

Search over `README.md`, `THIRD_PARTY_NOTICES.md`, `docs/`, `reports/` and
`FLY-SURFER-DATA/documentation/` for "training-run metrics", "from the training
run", "training run's validation/numbers" returns **no matches** outside the
historical analysis documents. The two generated Phase 3C result files in §4.2
remain and are reported, not hidden.

### 7.6 Protected artifact hashes

| Artifact | Size (bytes) | SHA-256 | Result |
|---|---:|---|---|
| `best.onnx` | 10,636,871 | `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77` | Unchanged |
| `best.pt` | 5,491,034 | `1b47a43325b18c59b52b9a29cdd45c029d079ee134a7283b49cd0e86366bdef8` | Unchanged |
| `model_config.json` | 1,249 | `b48710e5dcc1f75cf02fc78920530e9dbeb6a1b15e7e2df2e23a64dadba22a8c` | Unchanged |
| `metrics_summary.json` | 216 | `57ba3ccb3fe7ffb882109775c3f76c092078f46bf7c9f82065f8b96bb18cd615` | Unchanged |
| `SHA256SUMS.json` | 734 | `1e02a81563633c330f117af41b54e4386b9b0a0dba156d63d2e27145298aeae1` | Unchanged |
| `dataset_attribution.txt` | 1,529 | `5290ac7664c662d71c255ade0edb88e49428e25a14228b81374de47381abfe0d` | Unchanged |
| base `yolo11n.pt` | 5,613,764 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | Unchanged |
| preserved notebook | 971,997 | `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da` | Unchanged |
| working notebook copy | 971,997 | `3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da` | Unchanged |

The dataset archive (`dataset.zip`, recorded size 211,529,060 bytes, recorded
SHA-256 `c04058ad49b6160e14b2fc20633b6929e5603fa72208996144f22238bcb39eff`) is
**not present in either local checkout**, so it could not be re-hashed. No
dataset file is written, deleted or listed as modified in either repository.

### 7.7 Licence verification

| Check | Result |
|---|---|
| `LICENSE` (main repository) | Identical to `HEAD`; SHA-256 `bf8e39924b3fe1d9dd8b3dc874b99e8657d4ce384ae6e126c326a90ae1df3144` |
| `research_paper/LICENSE` | Identical to `HEAD`; SHA-256 `52126412d29edc773dd90a1e4c11df181ba697dd318ada63fe0522104cfa4e59` |
| Licence files edited | None |
| Main repository licence | MIT — preserved, not replaced or supplemented with AGPL-3.0 |

### 7.8 Git diff summary (state not modified)

Main repository: 8 tracked files modified, 69 insertions and 40 deletions across
the documentation files in §6.1, plus the pre-existing binary DOCX change in
§6.5. Data repository: 1 tracked file modified, 25 insertions and 4 deletions.
Untracked: the three new documents, the two earlier research documents and the
Word lock file. Nothing was staged.

### 7.9 Unexpected protected-file state (owner attention required)

`git status` shows that

- `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.docx` differs from `HEAD`
  (23,781,493 bytes at `HEAD` vs 23,793,580 bytes on disk), with an mtime of
  **2026-11-24 22:00:02**, and
- `research_paper/~$Y_SURFER_COMPLETE_RESEARCH_PAPER.docx` (162 bytes, mtime
  **2026-11-24 21:59:08**) exists as an untracked Word lock file.

Both timestamps precede this task (2026-11-25) and this task did not open, edit,
rebuild or replace the paper. The drift is most consistent with the DOCX having
been opened in Word after the v1.1 commit. It is **reported, not reverted**: the
paper is protected and the owner must decide whether the change is intended.
It should not be bundled into the documentation-correction commit.

---

## 8. Licensing status

- **The main repository remains MIT.** No AGPL-3.0 licence was assigned to it.
- **No final model-licensing decision was made.** The registry records the
  stated AGPL-3.0 licence and points to the unresolved analysis; it does not
  decide the weights' licence.
- **The Ultralytics questions remain unresolved.** Whether AGPL-3.0 attaches to
  the trained weights, and what Corresponding Source would be, is still open
  (`docs/research/YOLO11N_AGPL_LICENSING_COMPATIBILITY_AUDIT.md`).
- **Repository separation is not claimed to resolve licensing obligations.** The
  registry now says explicitly that separation is a packaging choice, not a legal
  conclusion.
- **Model-licensing statements were corrected only where evidenced** (the
  weights are a project fine-tune, not the upstream checkpoint) and were not
  expanded into legal conclusions.

---

## 9. Research paper and Zenodo status

- The published paper is **version 1.1** (Zenodo,
  DOI 10.5281/zenodo.24506776).
- **No paper source file, figure, table, DOCX or PDF was modified by this task.**
  `git status` lists no `research_paper/*.md` or `*.pdf` change.
- **No new Zenodo version was created or published.** No upload occurred.
- A1–A4 corrections are recorded separately in
  `RESEARCH_PAPER_V11_PROVENANCE_CORRECTION_PROPOSAL.md` for a future version,
  if the owner authorises one.
- The pre-existing DOCX drift and Word lock file in §7.9 are **not** part of this
  task and must be resolved by the owner before any future paper release.

---

## 10. Termination

Implementation and verification are complete. The working tree is unstaged in
both repositories. **Nothing was pushed.** The owner will review this report and
separately authorise publication; until then, the documentation corrections
exist only in the local working tree.
