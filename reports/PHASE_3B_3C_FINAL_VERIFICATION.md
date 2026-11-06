# Phase 3B / 3C — Final Verification

**Date:** 2026-11-06

**Result:** Phase 3B is implemented through a scripted perception chain and
Phase 3C is implemented and calibrated on synthetic/scripted sequences. The
trained-detector acceptance is **BLOCKED**, not passed. No action selection,
motor decoding, learning or game automation was added.

---

## 1. Component status

| Component | Status | Evidence |
| --- | --- | --- |
| 3B.0 / 3B.0.2 dataset audit | PASS | `reports/PHASE_3B0_DATASET_AUDIT.md`, `reports/PHASE_3B02_V15_DATASET_AUDIT.md` |
| 3B.1 curation and grouped split | PASS | `reports/PHASE_3B1_DATASET_CURATION.md`, split manifest |
| 3B.1 dataset validation | PASS | `experiments/phase_3b/results/dataset_validation.json` |
| 3B.2A perception interface and pipeline | PASS | `reports/PHASE_3B2A_INFERENCE_ARCHITECTURE.md`, 38 perception tests |
| 3B.2B.0 detector selection and protocol | PASS (design) | `reports/PHASE_3B2B0_DETECTOR_FEASIBILITY.md` |
| 3B.2B.1 training and weights | **BLOCKED** | no approval, no weights, resource gates |
| 3B.4 observation and multi-object layer | PASS | `perception/observations.py`, 12 tests |
| 3B.5 connection to existing encoders | PASS | `perception/sensory_bridge.py`, unchanged mappings |
| 3B.6 evaluation harness | PASS | `perception/evaluation.py`, 13 tests |
| 3B.6 trained-detector metrics | **BLOCKED** | `detector_evaluation.json` status `blocked` |
| 3C tracking and temporal features | PASS | `perception/tracking.py`, `perception/temporal.py`, 32 tests |
| 3C activation scheduler | PASS | `sensory/temporal_scheduler.py`, 13 tests |
| 3C synthetic calibration | PASS | 50 sequences, 6/6 adversarial checks, deterministic |
| 3C real-sequence evaluation | **BLOCKED** | no trained detector to produce sequences |
| 3B + 3C end-to-end integration | PASS (scripted) | 16/16 checks, `integration.json` |
| Trained-detector acceptance | **BLOCKED** | see Section 5 |

## 2. Tests

```
python -m pytest -q
265 passed in 6.70s
```

Breakdown of Phase 3B/3C files:

| File | Tests |
| --- | ---: |
| `tests/test_dataset_interface.py` | 8 |
| `tests/test_detector_backend.py` | 12 |
| `tests/test_observations.py` | 12 |
| `tests/test_perception.py` | 38 |
| `tests/test_evaluation.py` | 13 |
| `tests/test_tracking.py` | 12 |
| `tests/test_curation.py` | 6 |
| `tests/test_temporal.py` | 20 |
| `tests/test_temporal_calibration.py` | 12 |
| `tests/test_temporal_scheduler.py` | 13 |
| `tests/test_integration_3b_3c.py` | 5 |
| **Subtotal** | **151** |

The remaining 114 tests are the pre-existing Phase 2 / 3A / 3A.5 suites.
No test was removed or weakened. The direction-hold rule was added to the
implementation and the regression test; one describe test still requires
exactly seven transition rules and passes.

## 3. Measurements

### 3.1 Dataset

2,316 curated images, 8,666 boxes, 14 classes, 5 groups, 0 cross-split groups,
5 LOGO folds. Fixed split: 1,188 train images / 4,704 boxes and 1,128 valid /
3,962. `boots-powerup` and `jump-electric` are unevaluable in the fixed split
(0 valid boxes).

### 3.2 Temporal calibration (synthetic, seed 20261106)

50 sequences, 10 families × 5 trials:

- event micro: 175 TP / 0 FP / 0 FN, F1 1.000 (rule consistency, not
  recognition);
- direction accuracy 0.9961 (1,011 / 1,015);
- continuity 0.9442 (1,015 / 1,075), 5 reported ID switches;
- adversarial checks 6/6;
- scheduler `apply`: n = 41,115, mean 5.195 µs, p50 3.5 µs, p95 9.5 µs,
  p99 15.7 µs;
- repeated run identical.

### 3.3 Scripted end-to-end integration

10 frames, 30 fps, seed 20261106:

- 0 rejected detections, 10 events, 4 track IDs, 14 features;
- 300.5 ms simulated (601 steps at 0.5 ms);
- 560 spikes total: 444 on 138 mapped neurons, 116 on 27 non-stimulated
  neurons (20.7%);
- 73 active neurons of 139,255;
- 1.23 s wall time, 489 steps/s, retained arrays 100.4 MB;
- second run: identical scheduler signature, spike counts and activity;
- 16/16 checks, 4/4 protected hashes match.

Duration-sensitivity probe (same drive, 400 ms): 233,203 spikes, of which
232,639 are non-stimulated. Stimulated spikes barely change (444 → 564). The
recurrent network enters a high-activity regime under sustained drive in this
configuration; the reported protocol stops at the scripted sequence length
and does not interpret the probe as a perception result.

## 4. Files

### 4.1 Pre-existing tracked modifications (preserved, not staged)

```
M .gitignore
M brain/brain_simulator.py
M sensory/game_state.py
```

### 4.2 New Phase 3B code and configuration

```
perception/                       (20 modules)
configs/perception_config.yaml
configs/detector_config.yaml
experiments/phase_3b/             audit_dataset.py, curate_dataset.py,
                                  evaluate_detector.py, run_inference.py,
                                  validate_dataset.py, results/
```

### 4.3 New Phase 3C code, configuration and results

```
sensory/temporal_scheduler.py
experiments/phase_3c/             integration_check.py,
                                  temporal_calibration.py,
                                  results/temporal_calibration.json,
                                  results/integration.json
```

### 4.4 Tests created for 3B/3C

```
tests/test_curation.py
tests/test_dataset_interface.py
tests/test_detector_backend.py
tests/test_integration_3b_3c.py
tests/test_observations.py
tests/test_perception.py
tests/test_evaluation.py
tests/test_tracking.py
tests/test_temporal.py
tests/test_temporal_calibration.py
tests/test_temporal_scheduler.py
```

### 4.5 Reports and documentation

```
reports/PHASE_3B_DATASET_AND_DETECTOR.md / .json
reports/PHASE_3B_EVALUATION.md / .json
reports/PHASE_3B_INTEGRATION.md / .json
reports/PHASE_3C_TEMPORAL_ARCHITECTURE.md / .json
reports/PHASE_3C_CALIBRATION.md / .json
reports/PHASE_3C_EVALUATION.md / .json
reports/PHASE_3B_3C_FINAL_VERIFICATION.md / .json
docs/PHASE_3_ROADMAP.md            (status and measured outcomes updated)
```

Pre-existing Phase 3A/3A.5 untracked work (`sensory/input_scheduler.py`,
`sensory/population_encoder.py`, `sensory/sensory_experiment.py`,
`sensory/sensory_mapping.py`, `configs/sensory_config.yaml`,
`configs/sensory_calibration.yaml`, `experiments/phase_3/`,
`experiments/phase_3_5/`, their tests and reports) remains in place and was
not modified except where listed in Section 4.1.

## 5. Blockers

1. No weight license approved and no weight downloaded.
2. New detector dependencies (torchvision, OpenCV, pycocotools or
   ultralytics) not approved.
3. NanoDet's pinned training stack conflicts with Python 3.13 / PyTorch 2.10.
4. 1.02 GiB available RAM and 2.19 GiB free disk at audit time, below the
   planning estimate of 1.5–4 GB training RSS.
5. No training run approved; the protocol is frozen but not executed.

The correct status for trained-detector acceptance is therefore **BLOCKED**.
No metric was fabricated to fill the gap.

## 6. Protected artifacts

| Artifact | SHA-256 | Match |
| --- | --- | --- |
| `README.md` | `6277ffbb3db8e0b1be9bb320d44ff0f894a07ff04d6ea698efd03fe5a9ef9b10` | yes |
| `reports/PHASE_3B1_SPLIT_MANIFEST.json` | `ff3f91192e59546798b725b1e2625b5911cf0eb6c5f69e3cc22efdfeadaa357d` | yes |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | yes |
| v15 `data.yaml` | `f6e51bf674b4dfbbb51866a0d56ad85c7cb55b51032cf0ec95a8d9aa2b7be423` | yes |

Raw dataset, manifests, README and connectome artifact were not modified.

## 7. Git state

- No staging: `git diff --cached` is empty.
- No commit and no push were performed.
- No file deletion: `git status --short` reports zero `D` entries.
- Tracked modifications remain exactly the three pre-existing ones listed in
  Section 4.1.
- New Phase 3B/3C work and the 3A/3A.5 work that preceded it remain
  uncommitted, as required.

## 8. Recommendation

1. Keep trained-detector acceptance **BLOCKED** until the approval and
   resource gates in Section 5 are resolved.
2. When approved, run the one-epoch/one-batch smoke test before any full
   training, then follow the frozen fixed-split and LOGO protocol.
3. Only after a detector exists should real sequences be replayed through
   Phase 3C; report detector error propagation and keep the synthetic
   calibration labelled as rule consistency.
4. Do not describe any current result as perception accuracy, complete game
   perception, biological coding or evidence about the fly's visual system.
5. A duration-sensitivity study of the recurrent high-activity regime is a
   separate question; do not extend the reported protocol without one.
