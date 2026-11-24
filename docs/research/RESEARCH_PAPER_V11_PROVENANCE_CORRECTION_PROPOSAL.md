# Research Paper v1.1 — Proposed Detector-Provenance Correction

**Date:** 2026-11-25
**Status:** **proposal only.** Nothing in the published paper tree was modified.
**Applies to:** the published research paper, version 1.1 (Zenodo,
DOI 10.5281/zenodo.24506776), and the files under `research_paper/`.
**Decision required from:** the paper's author/owner.

This document is a **separate correction record**, created because the published
paper is frozen and must not be silently edited. It is not a new paper version and
does not authorise one. No Zenodo version was created or published.

---

## 1. Why a separate record

The YOLO11n detector was fine-tuned **for this project** on 2026-11-06 (50 epochs,
1,188 group-held-out training images, Google Colab, Ultralytics 8.4.202). Parts of
the paper still describe it as "externally trained" and as "not retrained,
fine-tuned, or calibrated during this project". That wording is contradicted by
the recovered notebook (SHA-256
`3eb5fef6d00b7d38a4eb9c1c05894e20c49af9dbe1b3ee26cd6cff75fe1ec5da`).

Because version 1.1 is published, the correction cannot be applied in place. It is
proposed here for whichever future version the owner authorises. Most of the
paper's detector statements are already correctly scoped to figure generation or
to the validation task (see §4) and must **not** be changed.

---

## 2. Proposed corrections (A1–A4)

### A1 — Chapter 5 opening statement (S1, blocking for a future version)

- **Locations:** `research_paper/src/05_perception.md:7`;
  `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:760`.
- **Current text:** "The detector is used as a fixed, externally trained component
  and was not retrained, fine-tuned, or calibrated during this project. The
  detector's reported performance is therefore a property of the supplied
  deployment, not a result of the work reported here."
- **Why it is wrong:** the detector is a project fine-tune of a COCO-pretrained
  checkpoint. Its performance is a property of that training run, which was work
  done for this project (outside the repository), not of an unmodified supplied
  deployment.
- **Proposed replacement:**
  > The detector was fine-tuned once for this project, outside the repository,
  > before this paper's preparation; it was not retrained, fine-tuned, or
  > calibrated to produce any figure or result reported here. Its reported
  > performance is therefore a property of that training run and of the supplied
  > deployment, not a result of the connectome pipeline work reported here.

### A2 — Data chapter summary (S5, non-blocking)

- **Locations:** `research_paper/src/03_data.md:5`;
  `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:538`.
- **Current text:** "two published connectomes and one externally trained
  detector".
- **Proposed replacement:** "two published connectomes and one frozen detector,
  fine-tuned once outside this repository (Chapter 5)". If the phrase occurs in a
  list where the parenthetical is awkward, "one frozen detection model
  (Chapter 5)" is acceptable.
- **Reason:** "externally trained" implies no project involvement; the weights are
  a project fine-tune, frozen before use here.

### A3 — Perception chapter provenance note (S1, blocking for a future version)

- **Locations:** `research_paper/src/05_perception.md:120`;
  `research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.md:873`.
- **Current text:** "The detector is externally trained and its reported accuracy
  is not a result of this project."
- **Proposed replacement:**
  > The detector was fine-tuned once outside the repository; its reported accuracy
  > is a property of that training run and is not re-measured here.

### A4 — Figure index note (S5, non-blocking)

- **Location:** `research_paper/figures/yolo11_visuals/FIGURE_INDEX.md:13`.
- **Current text:** "The model was not retrained, fine-tuned or calibrated during
  this task."
- **Proposed replacement:** "The model was not retrained, fine-tuned or calibrated
  during this figure-generation task."
- **Reason:** the current sentence is defensible in context but reads as a
  project-wide claim. Making the task scope explicit removes the ambiguity
  without asserting anything new.

---

## 3. Statements that must NOT be changed

These are already correct. Changing them would introduce inaccuracy.

| Location | Text | Why it is correct |
|---|---|---|
| `research_paper/src/05_perception.md:29, 51`; complete paper `:782, :804` | "not retrained, fine-tuned, or calibrated to produce any of these panels/for this figure" | Figure generation used forward inference only. |
| `research_paper/src/05_perception.md:13`; complete paper `:766` | "These values were produced in the training environment; they were not re-measured on this host" | The published metrics are the stage-C ONNX CPU re-validation run in Colab. |
| `research_paper/RESEARCH_PAPER_VALIDATION_REPORT.md:285` | "No training … was executed. The YOLO11n detector was not retrained, fine-tuned, recalibrated, or modified" | Scoped to that validation task's actions. |

The published metric values themselves (precision 0.937310, recall 0.810829,
mAP@0.5 0.897776, mAP@0.5:0.95 0.687726) are correct. They are the **ONNX CPU
re-validation** results (evaluation stage C), not the in-training PyTorch
validation. The paper's statement that they "were produced in the training
environment" is accurate; a future version may, if the owner wishes, add that they
are an ONNX Runtime CPU re-validation rather than the epoch-50 training validation.

---

## 4. Application conditions (for any future version)

1. Apply to `research_paper/src/` first, then rebuild the assembled Markdown, DOCX
   and PDF with the recorded build scripts.
2. Re-run the paper validation and update `SOURCE_AND_EVIDENCE_REGISTER.md` only
   if the owner authorises a new version.
3. Do not alter the published version 1.1 files or the Zenodo record. Do not
   create or publish a new Zenodo version under this proposal.
4. Keep the paper's existing limitations and metric scope unchanged.
5. Do not claim bit-exact reproducibility of the detector.

---

## 5. What this record does not do

- It does not modify any file under `research_paper/`.
- It does not create, replace or publish a Zenodo version.
- It does not decide the model's licence or resolve the Ultralytics AGPL-3.0
  questions.
- It does not change any metric value or limitation.
