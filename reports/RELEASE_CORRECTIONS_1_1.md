# Release corrections for version 1.1 (2026-11-24)

Documentation-integrity and post-execution test maintenance applied before the
first public release. No frozen parameter, protocol value, historical evidence
file or scientific conclusion was changed, and the protected `README.md` itself
was not modified.

## 1. Stale protected README digest

### What was wrong

Five Phase 3 gate/testing locations pinned the README SHA-256 recorded when the
README last changed at commit `2745cf7`. Commit `3bb2a4c` then re-titled one
project section ("FLY-SURFER development plan"); the README content changed, the
digest constants were not updated, and every Phase 3 gate consequently reported
`protected_hash_changed` for `readme`. That produced `SMOKE INVALID` verdicts,
failed the protected-hash tests, and failed the E13 static gate.

### What changed

| File | Line | Old digest | New digest |
|---|---|---|---|
| `experiments/phase_3c/integration_check.py` | 93 | `8ab6a8cc…563` | `8a79d44d…164` |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | 115 | `8ab6a8cc…563` | `8a79d44d…164` |
| `experiments/phase_3c/p3_t4_1_four_neuron_validation.py` | 70 | `8ab6a8cc…563` | `8a79d44d…164` |
| `experiments/phase_3c/temporal_acceptance.py` | 72 | `8ab6a8cc…563` | `8a79d44d…164` |
| `configs/causal_control_config.yaml` | 26 | `8ab6a8cc…563` | `8a79d44d…164` |

Full new digest: `8a79d44d4d5679333a99d475c419f790d3ad14d00c145645c55f6a45dac64164`.

The digest is now the SHA-256 of the committed README in the working tree;
`git show HEAD:README.md` hashes to the same value. The `integration_check.py`
comment was updated to name commit `3bb2a4c`.

### Why this is not a scientific change

The README digest is a documentation baseline. `configs/causal_control_config.yaml`
records the digest under `reference`, which the file itself describes as "fixed
inputs and constants, hashed and pinned"; no experiment parameter, condition,
seed, duration, threshold or current changed. The file's own SHA-256 will differ
from the value recorded inside historical result files (for example the
`causal_control_config_sha256` field in `experiments/phase_3c/results/`), because
those files record the bytes that existed at run time and are left untouched.
Historical reports under `docs/` and `reports/` that quote `8ab6a8cc…` are
point-in-time records and were deliberately not edited.

## 2. Obsolete Pilot 2-C destination expectation

### What was wrong

`tests/test_phase_8_pilot2c.py::test_readiness_reports_the_training_refusal_without_blocking_evaluation`
asserted `results_destination_free is True`. That was correct before execution.
The authorised 54-entry Pilot 2-C run has since been executed into
`experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/`, so the readiness
report correctly reports the destination as occupied and keeps the no-overwrite
blocker. The old assertion no longer described the repository.

### What changed

The test now verifies the completed execution instead of assuming an empty
destination:

- `results_destination_free` is `False`, and the `is not free … never
  overwritten` blocker is present (the no-overwrite gate is retained, not
  weakened);
- exactly one run directory containing `manifest.json` exists under the stage
  root, with `manifest.json`, `pilot_plan.json`, `pilot_summary.json` and
  `episodes.jsonl`;
- the manifest's `run_id` matches its directory, `schema_version` is 1,
  `design.conditions` is the six REV4 conditions, `episodes_per_seed` is 10, the
  pilot seeds are `[9001, 9002, 9003]`, and no non-README integrity failures are
  recorded;
- the summary reports `complete` and `executed`, with `planned`,
  `rows_executed` and `rows_stored` all equal to 54, and `run_dir` resolving to
  the run directory;
- all 54 rows in `episodes.jsonl` validate against the episode schema and cover
  the six executed arms (`A`, `A_prime`, `B`, `F`, `F_beta`, `floor`).

The rest of the test is unchanged: the training gate still refuses further
training, that refusal is still reported only under `training_blockers`, and the
stage remains non-executable because the training artifacts are not loaded.

## 3. README expansion and Zenodo publication record

### What was wrong

After the re-pin recorded in section 1, `README.md` was intentionally rewritten
in commit `effa62d` into a full project and data-provenance document. That
revision changed the protected README digest to `9dab9dc4…ef54` but was not
recorded here at the time. The README has since been extended with a
"Research Publication" section and a DOI badge recording the Zenodo release.

### What changed

| File | Line | Old digest | New digest |
|---|---|---|---|
| `experiments/phase_3c/integration_check.py` | 95 | `8a79d44d…164` | `15a17de8…05b` |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | 115 | `8a79d44d…164` | `15a17de8…05b` |
| `experiments/phase_3c/p3_t4_1_four_neuron_validation.py` | 70 | `8a79d44d…164` | `15a17de8…05b` |
| `experiments/phase_3c/temporal_acceptance.py` | 72 | `8a79d44d…164` | `15a17de8…05b` |
| `configs/causal_control_config.yaml` | 30 | `8a79d44d…164` | `15a17de8…05b` |

Full new digest: `15a17de886d29c8b325c00791d888934e207e8ab65fac7560e1fc954fad7a05b`.

The intermediate value `9dab9dc47281261c6c60996764adaf951276c173e5c40acce91b6e2e9914ef54`
(commit `effa62d`) is recorded here only for completeness; it never appeared in
a public release.

### Why this is not a scientific change

As in section 1, this is documentation only. No experiment parameter, condition,
seed, duration, threshold or current changed, no experimental code or frozen
research artifact was modified, and no recorded result was altered. The
publication record states the same qualified negative result as the rest of the
repository. Historical result files that embed the configuration hash are left
untouched.
