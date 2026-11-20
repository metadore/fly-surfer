# Phase 8 Pilot 1 — GitHub Preservation Audit

**Date:** 2026-11-20
**Repository:** `C:\Users\Hp\fruitfly\FLY-SURFER`
**Branch:** `main`
**HEAD:** `3c74ae82435f95798d8170cc5faf16ba8bed39db` — 2026-11-19 17:10:16 +0530 — `feat(phase-8): add campaign harness, training engine and readiness reports`
**Remote:** `origin` = `https://github.com/metadore/fly-surfer.git`
**Status of this audit:** read-only inspection only. **Nothing was staged, committed, pushed, reset, checked out, cleaned or stashed. No file other than this audit report was created or modified. The protected baseline was not changed.**

---

## 0. Verdict

The Pilot 1 materials are internally coherent and form a small, self-contained preservation set: **55 files, about 1.5 MiB**, almost all source, records and Markdown. They can be staged with explicit per-file paths; no broad add is needed or permitted.

Two facts must be carried with any preservation commit:

1. **The protected baseline does not pass.** A read-only recheck of all 37 entries in `experiments/phase_4h/baseline_integrity.json` gives **35 matching, 2 mismatching, 0 missing** (§5). The failures are `README.md` and `motor/__init__.py`. Both are **already committed in `main`**, not working-tree edits, which is why `git status` is silent about them. This is the pre-existing blocker on any Phase 8 freeze or publishable report.
2. **Pilot 1 is not fully reproducible from a GitHub clone alone.** Its two biological inputs, `datasets/processed/banc_v888/banc_graph_t5.npz` (12.9 MiB) and `banc_nodes.csv.gz` (3.6 MiB), are **untracked** and are not proposed for Git (they belong in FLY-SURFER-DATA, §10). The manifest pins their SHA-256 values, so their identity is auditable even when the bytes live elsewhere.

In addition, the Pilot 1 execution report contains a totals-line arithmetic error (`72,880` where the nine stored rows sum to `73,880`). The correct aggregate is **73,880**; the correction is preserved in two later reports without rewriting any episode record (§6).

**Recommendation:** stage the Required manifest in §9 after owner approval, resolve the `.gitignore` decision in §8, and keep the G3 data files out of Git. Do not attempt a Phase 8 freeze until the 35/37 drift is resolved by an authorised decision.

---

## 1. Method and limits

### 1.1 What was inspected

- Full `git status --porcelain` (41 entries: 10 modified files, 31 untracked entries) and `git diff --cached` (empty — nothing staged).
- Full `git diff` of all 10 modified files (619 insertions, 65 deletions), plus `git diff --stat`.
- `git ls-files` for tracked/untracked classification; `git check-ignore -v` for `.gitignore` behaviour.
- Every Pilot 1 artifact, row, manifest, preflight, execution record and report totals table.
- An independent, in-memory SHA-256 + size recheck of all 37 protected-baseline entries.
- SHA-256 of REV4, all five input configs, all three Phase 8 campaign configs, D1 and D2.
- directory sizes and file counts for every large untracked tree.

### 1.2 What was deliberately **not** run

| Not run | Why |
|---|---|
| `experiments/phase_4g/verify_integrity.py` | It **writes** `experiments/results/phase_4g/integrity_recheck.json`. Running it would modify the working tree and create a new untracked result. The baseline was rechecked read-only with the same size + SHA-256 rule instead (§5). |
| `pytest` / any test suite | Test collection writes `.pytest_cache/` and `__pycache__/`. Both are ignored, but they are still working-tree writes; the mandate was no modification. Test correctness is therefore **not re-certified by this audit**; the existing test files and their recorded pass status are what is being inventoried. |
| Any Pilot 1 episode, training run, graph regeneration or campaign command | Out of scope; forbidden by the mandate. |
| `git add`, `commit`, `push`, `reset`, `checkout`, `clean`, `stash` | Forbidden by the mandate. |

### 1.3 Platform note

The environment is Git Bash on Windows 11 with Git 2.53.0. Paths in the records are absolute `C:/Users/Hp/...` paths; they are provenance, not repository content.

---

## 2. Complete Git inventory

### 2.1 Summary

| Category | Count |
|---|---|
| Modified tracked files | 10 |
| Untracked entries reported by Git | 31 (18 file paths + 13 directory placeholders) |
| Staged files | **0** |
| Deleted or renamed files | 0 |
| Merge conflicts / unresolved index | 0 |

`git status --porcelain` has 41 lines. No file is staged; the index is clean.

These counts describe the tree immediately before this audit report was written. This audit creates exactly one file, `reports/PHASE_8_GITHUB_PRESERVATION_AUDIT.md`; with it the working tree reports 42 porcelain lines. Nothing else in the inventory changes.

### 2.2 Modified tracked files (10)

```
 M experiments/phase_8/campaign/__init__.py           12 +-
 M experiments/phase_8/campaign/factory.py             4 +-
 M experiments/phase_8/campaign/protocol.py          534 +++-
 M experiments/phase_8/conditions/execute.py           2 +-
 M experiments/phase_8/config.py                      15 +-
 M experiments/phase_8/manifest.py                     7 +-
 M experiments/phase_8/run_campaign.py                38 +-
 M experiments/phase_8/training/gate.py               52 +-
 M tests/test_phase_8_campaign_runner.py              17 +-
 M tests/test_phase_8_campaign_skeleton.py             3 +-
```

All ten are Phase 8 authorization/runner changes made after the last commit. None is a protocol, config, dataset or result file.

**Purpose of each change (verified in the diff):**

| File | Change | Classification |
|---|---|---|
| `campaign/__init__.py` | Exports `assert_stage_authorized`, `g3_applicability`, `stage_authorization`; docstring states D1/D2 recognition | D1/D2 authorization plumbing |
| `campaign/protocol.py` | Adds `DECISION_ITEM_IDS`, `PILOT1_G3_SCOPE`, `_read_approval_record`, `approval_status`, `_read_owner_decision`, `g3_applicability`, `_pilot1_scope_failures`, `stage_authorization`, `assert_stage_authorized`; B7 message for non-Pilot-1 stages | D1/D2 authorization plumbing |
| `config.py` | `describe()` reports approval/approval_basis via deferred import | D1/D2 authorization plumbing |
| `manifest.py` | Writes `approval`/`approval_basis` into the design block | D1/D2 authorization plumbing |
| `run_campaign.py` | Dynamic `execution_blockers` (B1/B7/B2) and docstring | D1/D2 authorization plumbing |
| `training/gate.py` | Adds unresolved blockers B2–B6 and B7, `blockers`, `approval_record`; `assert_training_authorized` still always raises | D1/D2 authorization plumbing |
| `campaign/factory.py` | `seed_plan(master_seed, arm, seed, episode=int(episode))` — environment stream is per-episode; network/learning/structure streams are not | Bug fix found during Pilot 1 wiring |
| `conditions/execute.py` | `error_row(..., action_counts=counts)` instead of `action_counts or {}` | Bug fix: do not discard a legitimately empty mapping |
| `tests/test_phase_8_campaign_runner.py` | Expectations updated to D1-approved / B7 refusal; blocker count 2 | Test alignment |
| `tests/test_phase_8_campaign_skeleton.py` | `describe()` approval assertions | Test alignment |

Neither bug-fix changes a scientific constant: `seed_plan` semantics in `experiments/phase_8/seeds.py` already define the environment stream as `[master, campaign_seed, episode, 1]` and the network/learning streams as episode-independent. `factory.py` now passes the episode into the plan; it does not redefine a seed. `execute.py` only stops substituting an empty dict for a real one.

### 2.3 Untracked entries (31)

```
?? datasets/external/
?? datasets/processed/banc_v888/
?? datasets/processed/banc_v888_random/
?? docs/PHASE_8_OWNER_DECISION_PACKAGE.md
?? docs/research/
?? experiments/phase_8/stages/
?? experiments/results/phase_4h/control_draws.checkpoint.jsonl
?? experiments/results/phase_4h/population_sensitivity.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.diagnostics.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.diagnostics.v2.checkpoint.jsonl
?? experiments/results/phase_4h/weight_sensitivity.checkpoint.jsonl
?? experiments/results/phase_7/neural_closed_loop_activity.npz
?? experiments/results/phase_8/
?? experiments/results/phase_8_random/
?? external/
?? reports/PHASE_8_EXECUTION_READINESS_AFTER_SOFTWARE_COMPLETION.md
?? reports/PHASE_8_EXTERNAL_INTEGRATION_RECOMMENDATIONS.md
?? reports/PHASE_8_GPU_READINESS_CHECKLIST.md
?? reports/PHASE_8_OWNER_APPROVAL_D1.md
?? reports/PHASE_8_OWNER_DECISION_D2.md
?? reports/PHASE_8_PILOT1_EXECUTION.json
?? reports/PHASE_8_PILOT1_EXECUTION_REPORT.md
?? reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md
?? reports/PHASE_8_PILOT1_PREFLIGHT.json
?? reports/PHASE_8_PILOT2_READINESS_DECISION.md
?? reports/_tmp_4h4_check.json
?? reports/phase_8_owner_approvals/
?? tests/test_phase_8_d2_authorization.py
?? tests/test_phase_8_pilot1_runner.py
?? tests/test_phase_8_stage_infrastructure.py
```

Expanded contents of the directory placeholders that matter:

| Directory | Files | Size |
|---|---|---|
| `experiments/phase_8/stages/` | `__init__.py`, `common.py`, `composition.py`, `information.py`, `pilot1.py`, `pilot1_runner.py`, `pilot2.py`, `reporting.py`, `run_stage.py`, `training_stage.py` (+ ignored `__pycache__/`) | 148 KiB |
| `experiments/results/phase_8/` | only `pilot1/pilot1/{episodes.jsonl, manifest.json, pilot_plan.json, pilot_summary.json}` | 60 KiB |
| `experiments/results/phase_8_random/` | `campaign_seed_summary.json`, `certification_seed_1..16.json`, `logs/` | 813 KiB (776 KiB in the 17 JSON files) |
| `reports/phase_8_owner_approvals/` | `D1.json`, `D2.json` | 4 KiB |
| `datasets/processed/banc_v888/` | 7 files | 101 MiB |
| `datasets/processed/banc_v888_random/` | 16 namespaces × 3 files | 209 MiB |
| `datasets/external/banc_v88/` | 5 raw files | 383 MiB |
| `datasets/external/banc_v888/` | empty tree (0 files) | 4 KiB |
| `external/endless-surfer-main/` | 90 files, third-party clone | 383 KiB |
| `docs/research/` | 3 Markdown files | 68 KiB |

### 2.4 Pre-existing modifications

There are **no uncommitted modifications to `README.md` or `motor/__init__.py`**. Both are clean in `git status`. The protected-baseline discrepancy (§5) is between the hash record and the **committed** tree:

- `README.md` last changed in `3bb2a4c` (2026-11-07), title line only, 14,921 → 14,938 bytes (+17).
- `motor/__init__.py` last changed in `3c74ae8` (2026-11-19), docstring only, 217 → 363 bytes, 4 insertions / 3 deletions.

Both predate the Pilot 1 run (2026-11-20 10:58:51Z) and were not touched by it. The only working-tree modifications are the ten Phase 8 source/test files above.

### 2.5 Unrelated untracked artifacts

These are not part of Pilot 1 and should not be staged with it (§10):

- six Phase 4H `*.checkpoint.jsonl` files (8.8 MiB total, dated 2026-11-08);
- `experiments/results/phase_7/neural_closed_loop_activity.npz` (2.5 KiB);
- `reports/_tmp_4h4_check.json` (196 KiB, dated 2026-11-08);
- `datasets/processed/banc_v888/`, `datasets/processed/banc_v888_random/`, `datasets/external/`;
- `external/endless-surfer-main/`;
- `docs/research/` and `reports/PHASE_8_EXTERNAL_INTEGRATION_RECOMMENDATIONS.md` (external-repository research);
- `reports/PHASE_8_GPU_READINESS_CHECKLIST.md`, `reports/PHASE_8_EXECUTION_READINESS_AFTER_SOFTWARE_COMPLETION.md`, `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` (pre-D1 documents; see §4.6).

---

## 3. What is required to reproduce and audit Pilot 1

### 3.1 Entry point

The production runner is `experiments/phase_8/stages/pilot1_runner.py` (class `Pilot1EpisodeRunner`, identity recorded as `phase_8.stages.pilot1_runner.Pilot1EpisodeRunner`), constructed by `experiments/phase_8/stages/pilot1.py` at line 213 and reached through:

```
python -m experiments.phase_8.stages.run_stage pilot1 --run
```

`run_stage.py` routes to `stages.pilot1`; the stage gate in `campaign/protocol.py` must pass before an episode is built. All of this is new or modified working-tree code (§9, Groups 1–2).

### 3.2 Inputs pinned by the run

`experiments/results/phase_8/pilot1/pilot1/manifest.json` records seven input hashes. Five are tracked in Git and unmodified; two are untracked data:

| Input | Path | SHA-256 | In Git? |
|---|---|---|---|
| BANC graph | `datasets/processed/banc_v888/banc_graph_t5.npz` | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` | **No** (101 MiB tree) |
| BANC nodes | `datasets/processed/banc_v888/banc_nodes.csv.gz` | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` | **No** |
| Motor decoder | `configs/motor_decoder.yaml` | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` | Yes |
| Neuron model | `configs/neuron_config.yaml` | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` | Yes |
| Plasticity | `configs/plasticity_banc.yaml` | `616288a40bf864185c33f92a99742be8dd49e62773cbb58cb9287414ad9e5f70` | Yes |
| Sensory mapping | `configs/banc_sensory_mapping.yaml` | `64c716a42c44ded58c77fccdcd865b0a9732a06b86019d673e6fb4c902dfc4ff` | Yes |
| Synapse policy | `configs/banc_synapse_policy.yaml` | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` | Yes |

Campaign config hashes (all tracked, all matched at preflight and in every row):

| Config | SHA-256 |
|---|---|
| `configs/phase_8/campaign.yaml` | `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19` |
| `configs/phase_8/conditions.yaml` | `9a93f04771a2489b09a14c2b74418ffb423ad9702d7bc3a47492a2012d42f671` |
| `configs/phase_8/environment.yaml` | `b391ecf71fd7acac0517a677f9198d6a252a00428aabf8c58d3b6b343a3281dc` |

Execution environment recorded in the manifest: CPython **3.13.14**, Windows-11-10.0.26200-SP0, 12 CPUs, numpy 2.3.4, scipy 1.16.3, torch 2.10.0, pandas 2.3.3, PyYAML 6.0.3, psutil 7.1.2, matplotlib 3.10.7.

### 3.3 Design identity

- Master seed **20261116**; condition A; seeds **9001, 9002, 9003**; 3 episodes each.
- Environment seed stream `[master, campaign_seed, episode, 1]`; network `[master, 1, campaign_seed, 2]`; learning `[master, 1, campaign_seed, 3]`; structure `[master, campaign_seed, 4]`.
- `run_id = "pilot1"`, created `2026-11-20T10:58:51.829129Z`.
- Evidence kind `pilot`; every row carries `estimates_contrasts: false`-equivalent notes and `"Pilot 1 does not estimate C1-C4 and is not merged into the campaign design"`.

### 3.4 Authorisation chain

| Record | Path | SHA-256 |
|---|---|---|
| D1 (REV4 §12 / U1–U18 approved as written) | `reports/phase_8_owner_approvals/D1.json` | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| D2 (G3 deviation not applicable to Pilot 1 only) | `reports/phase_8_owner_approvals/D2.json` | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |
| Human-readable D1 | `reports/PHASE_8_OWNER_APPROVAL_D1.md` | referenced by the execution report §9 |
| Human-readable D2 | `reports/PHASE_8_OWNER_DECISION_D2.md` | referenced by the execution report §9 |

The preflight records `d1_approval.record_sha256 = 5c183c99…d489` and `d2_decision.record_sha256 = b5b0c229…7327`; both match the files byte-for-byte. Without these four files the code's `assert_stage_authorized` fails closed (the records are required inputs, not documentation).

---

## 4. Internal-consistency verification

### 4.1 Artifact hashes

The execution report's "Artifact hashes" table (`reports/PHASE_8_PILOT1_EXECUTION_REPORT.md:334–346`) matches the files exactly:

| Artifact | SHA-256 | Matches |
|---|---|---|
| `episodes.jsonl` | `ee479e5b1f4fe3cfe00ef170b0c2126dcdddc7b2b241343bf8736d6af9d468f9` | Yes |
| `manifest.json` | `58cde4cf11272b1b28a353b7678b3fcaa02d41488e069039ecd6720159d2e9cc` | Yes |
| `pilot_plan.json` | `99fb1385939d4506cd3c9f001dc7e66552c4dc1dd30878b34606302fd903646a` | Yes |
| `pilot_summary.json` | `76b68c2626d9733548c107dbb381b2ab660431ea029bae4b4c6b9bfde694351b` | Yes |
| Preflight record | `87bf60dca16d97323ed14dde1d2f9d1b360ef84bbe66f2eabf6abe68a3156566` | Yes |
| Execution record | `d3392b9c7132b5ee92652a69509d5ae43b57b9a66024178bed30e7af57c23e1e` | Yes |

### 4.2 Row-level aggregates

Recomputed independently from `episodes.jsonl`:

| Quantity | Value |
|---|---|
| Rows | 9 (3 seeds × 3 episodes) |
| Game updates / steps | **3,784** |
| Neural steps | **126,135** |
| Total neural spikes | **73,880** |
| Motor-population spikes | **0** |
| Total reward | **47.75** |
| Weight fingerprint (before = after, every episode) | `4923f0cd45d55fd4cd80d81392974dd5058ca988f18348734d10b45b06d945d5` |
| Terminations | 9 × `collision`; 0 truncated |

Per-episode spike totals: 4,764; 14,348; 4,764; 14,911; 8,396; 13,139; 2,850; 7,856; 2,852 — sum 73,880.

The execution report's §6 table is correct. Its **totals sentence is not**: §6 (`:194`) says `72,880 total spikes`, and §7.2 (`:236`) says `72,880 spikes`. Both are 1,000 low. See §6 below.

### 4.3 Preflight

`reports/PHASE_8_PILOT1_PREFLIGHT.json`: `passed = true`, every `required` check passed, no failed checks; the three config hashes, D1 record hash, D2 record hash, the condition-A-only declaration and the configuration constants all match current files. Memory preflight: 5.745 GB available against the 4.0 GB gate.

### 4.4 Run manifest and summary

- `manifest.json`: `protocol = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"`, 7 input hashes, 3 config hashes, the full design block, environment capture and memory preflight.
- `pilot_summary.json`: `executed = true`, `complete = true`, `planned = 9`, `rows_executed = 9`, `rows_stored = 9`, `estimates_contrasts = false`, `evidence_kind = "pilot"`, `merged_into_campaign = false`, `rev4_step = "10.3"`.
- `PHASE_8_PILOT1_EXECUTION.json`: `error = null`; `post_execution_verification` has `all_rows_A`, `all_rows_ok`, `all_evidence_pilot`, `all_weights_fixed` all true, `problems = []`; memory sampling 177 samples, RSS max 0.3725 GiB, available min 4.1997 GiB; wall time 357.046 s.

### 4.5 Two intentional label nuances (recorded, not defects)

1. `pilot_plan.json` is the pre-execution plan copy and still says `executed = false`. The authoritative records are the summary, the manifest and the nine rows, all of which say executed/experimental. The report §7.3 records this rather than rewriting the plan. Do not "fix" the plan file: it is a historical plan, and changing it would alter a hashed artifact.
2. `manifest.integrity = {baseline: null, checked: false, non_readme_failures: [], note: "the 37-file baseline was not checked for this manifest; a report may not be published until it is"}`. This is an honest statement, and it is correct: the run is **not** freeze-eligible while §5 is unresolved.

### 4.6 Stale approval status in antecedent documents

Three untracked documents predate D1 and still say U1–U18 are **not approved**:

- `docs/PHASE_8_OWNER_DECISION_PACKAGE.md` (header: "NOT APPROVED, NOT EXECUTABLE");
- `reports/PHASE_8_EXECUTION_READINESS_AFTER_SOFTWARE_COMPLETION.md` (header: "PROPOSED — not approved");
- `reports/PHASE_8_GPU_READINESS_CHECKLIST.md` (pre-run operational checklist).

They are accurate for their dates, but they are **not current statements** and must not be read alongside D1 as if they contradicted it. The decision package is referenced by `reports/PHASE_8_PILOT2_READINESS_DECISION.md:64` (Part E). The proposed manifest therefore includes the decision package (to avoid a dangling reference) but **not** the other two; see §9–§10.

---

## 5. The 35/37 protected-baseline discrepancy (explicit flag)

**Record:** `experiments/phase_4h/baseline_integrity.json`, tracked, unmodified, SHA-256 `f19acc9d7a0ebe349d43b64113c277bfc9f655a2c5af08902a31d5490d2bc049` (5,550 bytes). It contains **37** path → `{bytes, sha256}` entries.

**Independent read-only recheck (same size + SHA-256 rule):**

| Result | Count |
|---|---|
| Entries | 37 |
| Size and SHA-256 match | **35** |
| Mismatch | **2** |
| Missing | 0 |
| Entries not tracked in Git | **7** (all in `datasets/processed/banc_v888/`) |

**The two mismatches:**

| File | Expected bytes | Expected SHA-256 | Actual bytes | Actual SHA-256 |
|---|---|---|---|---|
| `README.md` | 14,921 | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | 14,938 | `8a79d44d4d5679333a99d475c419f790d3ad14d00c145645c55f6a45dac64164` |
| `motor/__init__.py` | 217 | `17ac008ce39627b20188ea662fc3358b86e6f6b02145af7976ca234865a3c8de` | 363 | `859b02a9c2875bfe0231e2d042cde7f1461e494c8ffee6207edf1a325061c40e` |

**Why this is subtle and why it matters:**

- Both files are **clean in `git status`**. The drift is committed:
  - `README.md` — last changed in `3bb2a4c`, 2026-11-07; the title line changed from `# FLY-SURFER` to `# FLY-SURFER development plan` (+17 bytes).
  - `motor/__init__.py` — last changed in `3c74ae8`, 2026-11-19; docstring-only, 4 insertions / 3 deletions.
- Neither change was made by the D2 implementation or by Pilot 1; both predate the run.
- **`motor/__init__.py` is a non-README failure**, so `check_integrity()` returns `pass = false` and REV4's freeze condition ("refuses to publish a report if any non-README pinned file changed", `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` lines 1286–1287) is not met.
- REV4 §10.12 acceptance text says "integrity 36/37 non-README". Under either reading, the criterion fails: the literal non-README result is **35 of 36 matching**, and the total is **35 of 37**. The single non-README failure is `motor/__init__.py`.
- **Seven of the 37 entries are not in Git** (`banc_v888` graph, nodes, id map, manifest, construction report and the t1/t10 graphs). A GitHub clone can verify at most 30 entries; the remaining 7 are local-data checks. This is not a violation by itself, but it means "the baseline passes in a clone" is not a meaningful statement.
- The Pilot 1 manifest correctly records `integrity.checked = false`; this audit does **not** change that or the baseline. Resolving the discrepancy requires an owner-authorised amendment or a compliant restoration; it was not attempted here.

**Freeze implication:** no `reports/PHASE_8_RESULTS.md`, no "frozen" Pilot 1 report, and no claim of a passing integrity gate may be made while this stands.

---

## 6. The 73,880-spike correction, preserved without rewriting history

**Correct aggregate:** the nine stored episode rows sum to **73,880** total neural spikes (row values in §4.2). Every other aggregate is correct: 3,784 updates, 126,135 neural steps, 0 motor spikes, 47.75 reward.

**Where the error lives (do not edit these in place):**

- `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md:194` — "**72,880 total spikes**" in the §6 totals sentence.
- `reports/PHASE_8_PILOT1_EXECUTION_REPORT.md:236` — "**72,880 spikes**" in §7.2.

The per-episode table in the same report (§6, lines ~170–194) is correct and sums to 73,880; only the two prose totals are 1,000 low.

**Where the correction is documented (already, without touching the episode data):**

- `reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md:45` — states the totals line says 72,880 and the rows sum to 73,880; `:58` gives the corrected table; `:495` and `:690` call it a totals-line arithmetic error.
- `reports/PHASE_8_PILOT2_READINESS_DECISION.md:536–547` — states the correct aggregate is 73,880, identifies the two erroneous lines and confirms the §6 table is correct; `:683` records that no stored record was altered.

**Preservation rule for this commit:**

1. Do **not** rewrite any `episodes.jsonl` row, manifest or execution record.
2. Do **not** silently edit the execution report. Its hashes are recorded in its own artifact table; an edit would invalidate them unless the table is updated in the same authorised change.
3. Carry the correction forward as a documented correction: the two downstream reports above already do this, and this audit is the third record. If the owner later wants the execution report itself corrected, that should be a separate authorised erratum that restates the artifact hashes — not part of a preservation commit.

---

## 7. No REV4 or frozen-parameter modification

### 7.1 Protocol

| Item | Value |
|---|---|
| `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` SHA-256 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Bound in D1, D2, every certificate, the preflight and the run manifest | Yes — all record the same hash |
| Working-tree modification | **None** (`git status` shows nothing for this path) |
| REV4 self-status | Still says the document authorises no execution; approval is external via D1 |

### 7.2 Frozen configs

All eight runtime configs match the hashes pinned by the preflight/manifest/rows (see §3.2). `configs/phase_8/campaign.yaml` is tracked and unmodified; its `design.n_seeds_selected` remains `null` and `design.n_seeds_fallback` remains `10` (the Phase 8 design is still unresolved — correctly).

### 7.3 The ten modified files

- Eight are authorization plumbing or wiring; none declares, changes or hard-codes a scientific constant, threshold, weight, seed or learning rule.
- Two are bug fixes: `factory.py` passes the already-defined per-episode environment stream into `seed_plan`; `execute.py` stops discarding an empty `action_counts` mapping on error rows.
- No modified file is in the 37-entry protected baseline (the baseline covers Phase 4 brain/motor/dataset/report files, not `experiments/phase_8/`).

**Conclusion:** REV4 and every frozen experimental parameter are unchanged. Pilot 1 was executed under the hashes it records.

---

## 8. `.gitignore` audit and gaps

### 8.1 What the file says and does

`.gitignore` deliberately excludes raw FlyWire (`datasets/raw/**`), the Subway Surfers dataset, Python caches, virtualenvs, editor files, secrets, `*.log`, `experiments/**/tmp|scratch`, `*.npy`, `*.h5`, `references/`, `models/` and the YOLO export. Its header explicitly says **not** to add broad rules for `*.json`, `*.csv`, `*.gz`, `*.png` or `*.npz`, because derived research artifacts are intentionally tracked.

### 8.2 Verified behaviour

| Candidate | Ignored? | Consequence |
|---|---|---|
| `datasets/external/banc_v88/` (383 MiB) | **No** | A broad `git add` would try to commit 383 MiB of raw data |
| `datasets/external/banc_v888/` (empty tree) | **No** | Empty directories are not committed anyway |
| `datasets/processed/banc_v888/` (101 MiB) | **No** | Pilot 1 input graph/nodes would be committed |
| `datasets/processed/banc_v888_random/` (209 MiB) | **No** | 16 random graphs would be committed |
| `external/endless-surfer-main/` (383 KiB) | **No** | Third-party clone would be committed (only `references/` is ignored) |
| `experiments/results/phase_7/neural_closed_loop_activity.npz` | **No** | A Phase 7 output `.npz` is not ignored |
| six `experiments/results/phase_4h/*.checkpoint.jsonl` | **No** | 8.8 MiB of regenerable checkpoints |
| `reports/_tmp_4h4_check.json` | **No** | Temporary 196 KiB report |
| `experiments/results/phase_8_random/logs/*.log` | Yes (`*.log`) | Already excluded; the `.sh` is not |
| `experiments/phase_8/stages/__pycache__/` | Yes (`__pycache__/`) | Already excluded |
| `*.npz` generally | **No** (by design) | Cannot add a broad rule: it would drop tracked research `.npz` files |

### 8.3 Gaps and the recommended (not-yet-applied) fix

Because this audit must not modify files, the following are **proposals for a separate, owner-approved edit**, to be made before any future broad add and not as part of this preservation commit:

```gitignore
# Large derived BANC data (kept in FLY-SURFER-DATA, hashes in phase_4h baseline)
datasets/processed/banc_v888/
datasets/processed/banc_v888_random/
datasets/external/banc_v88/
datasets/external/banc_v888/
# Third-party reference clones (only references/ is currently ignored)
external/
# Regenerable intermediate checkpoints and temporary reports
experiments/results/**/*.checkpoint.jsonl
reports/_tmp_*.json
```

Do **not** add `*.npz`, `*.json` or `*.gz` broad rules: the repository intentionally tracks research outputs and the protected `connectome.npz` / `nodes.csv.gz`.

**Until those rules exist, only explicit per-file staging is safe.** `git add .` and `git add -A` are prohibited by the mandate and would, in this working tree, attempt to stage more than 690 MiB of excluded data.

---

## 9. Exact proposed staging manifest

**Global preconditions (owner):**

1. Owner approves this manifest and the classification in §10.
2. Owner decides whether the Recommended tier is included.
3. Owner decides the `.gitignore` question in §8 (recommended before staging, so a later broad add is safe).
4. No `git add .` / `git add -A`; use the explicit commands below.
5. After staging, verify the index against this list before committing:
   `git status --porcelain` and `git diff --cached --name-only | sort`.

### 9.1 Required tier — 36 files + this audit (37 total), ~0.62 MiB plus this report

**Modified tracked files (10):**

```
experiments/phase_8/campaign/__init__.py
experiments/phase_8/campaign/factory.py
experiments/phase_8/campaign/protocol.py
experiments/phase_8/conditions/execute.py
experiments/phase_8/config.py
experiments/phase_8/manifest.py
experiments/phase_8/run_campaign.py
experiments/phase_8/training/gate.py
tests/test_phase_8_campaign_runner.py
tests/test_phase_8_campaign_skeleton.py
```

**New production/stage code (10):**

```
experiments/phase_8/stages/__init__.py
experiments/phase_8/stages/common.py
experiments/phase_8/stages/composition.py
experiments/phase_8/stages/information.py
experiments/phase_8/stages/pilot1.py
experiments/phase_8/stages/pilot1_runner.py
experiments/phase_8/stages/pilot2.py
experiments/phase_8/stages/reporting.py
experiments/phase_8/stages/run_stage.py
experiments/phase_8/stages/training_stage.py
```

**New tests (3):**

```
tests/test_phase_8_d2_authorization.py
tests/test_phase_8_pilot1_runner.py
tests/test_phase_8_stage_infrastructure.py
```

**Owner approval records (4):**

```
reports/phase_8_owner_approvals/D1.json
reports/phase_8_owner_approvals/D2.json
reports/PHASE_8_OWNER_APPROVAL_D1.md
reports/PHASE_8_OWNER_DECISION_D2.md
```

**Pilot 1 execution records and reports (9):**

```
reports/PHASE_8_PILOT1_PREFLIGHT.json
reports/PHASE_8_PILOT1_EXECUTION.json
reports/PHASE_8_PILOT1_EXECUTION_REPORT.md
reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md
reports/PHASE_8_PILOT2_READINESS_DECISION.md
experiments/results/phase_8/pilot1/pilot1/episodes.jsonl
experiments/results/phase_8/pilot1/pilot1/manifest.json
experiments/results/phase_8/pilot1/pilot1/pilot_plan.json
experiments/results/phase_8/pilot1/pilot1/pilot_summary.json
```

**This audit (1):**

```
reports/PHASE_8_GITHUB_PRESERVATION_AUDIT.md
```

**Exact command (Required tier):**

```bash
git add -- \
  experiments/phase_8/campaign/__init__.py \
  experiments/phase_8/campaign/factory.py \
  experiments/phase_8/campaign/protocol.py \
  experiments/phase_8/conditions/execute.py \
  experiments/phase_8/config.py \
  experiments/phase_8/manifest.py \
  experiments/phase_8/run_campaign.py \
  experiments/phase_8/training/gate.py \
  experiments/phase_8/stages/__init__.py \
  experiments/phase_8/stages/common.py \
  experiments/phase_8/stages/composition.py \
  experiments/phase_8/stages/information.py \
  experiments/phase_8/stages/pilot1.py \
  experiments/phase_8/stages/pilot1_runner.py \
  experiments/phase_8/stages/pilot2.py \
  experiments/phase_8/stages/reporting.py \
  experiments/phase_8/stages/run_stage.py \
  experiments/phase_8/stages/training_stage.py \
  tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py \
  tests/test_phase_8_d2_authorization.py \
  tests/test_phase_8_pilot1_runner.py \
  tests/test_phase_8_stage_infrastructure.py \
  reports/phase_8_owner_approvals/D1.json \
  reports/phase_8_owner_approvals/D2.json \
  reports/PHASE_8_OWNER_APPROVAL_D1.md \
  reports/PHASE_8_OWNER_DECISION_D2.md \
  reports/PHASE_8_PILOT1_PREFLIGHT.json \
  reports/PHASE_8_PILOT1_EXECUTION.json \
  reports/PHASE_8_PILOT1_EXECUTION_REPORT.md \
  reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md \
  reports/PHASE_8_PILOT2_READINESS_DECISION.md \
  experiments/results/phase_8/pilot1/pilot1/episodes.jsonl \
  experiments/results/phase_8/pilot1/pilot1/manifest.json \
  experiments/results/phase_8/pilot1/pilot1/pilot_plan.json \
  experiments/results/phase_8/pilot1/pilot1/pilot_summary.json \
  reports/PHASE_8_GITHUB_PRESERVATION_AUDIT.md
```

### 9.2 Recommended tier — 18 files, ~0.85 MiB

**G3 evidence (17).** Included because D2's meaning ("G3 remains blocking for everything else") rests on the recorded deviation, and because tracked reports (`PHASE_8_FINAL_READINESS_REPORT.md`) cite the 16/16 certification. These are small JSON records; the 209 MiB graphs they refer to stay out of Git.

```
experiments/results/phase_8_random/campaign_seed_summary.json
experiments/results/phase_8_random/certification_seed_1.json
experiments/results/phase_8_random/certification_seed_2.json
experiments/results/phase_8_random/certification_seed_3.json
experiments/results/phase_8_random/certification_seed_4.json
experiments/results/phase_8_random/certification_seed_5.json
experiments/results/phase_8_random/certification_seed_6.json
experiments/results/phase_8_random/certification_seed_7.json
experiments/results/phase_8_random/certification_seed_8.json
experiments/results/phase_8_random/certification_seed_9.json
experiments/results/phase_8_random/certification_seed_10.json
experiments/results/phase_8_random/certification_seed_11.json
experiments/results/phase_8_random/certification_seed_12.json
experiments/results/phase_8_random/certification_seed_13.json
experiments/results/phase_8_random/certification_seed_14.json
experiments/results/phase_8_random/certification_seed_15.json
experiments/results/phase_8_random/certification_seed_16.json
```

All 17 were checked: every certificate has `status = "certified"`, seeds 1–16, protocol hash `e4aa9e0f…b1547c`, and every mandatory gate (R4–R14, R17) true. `campaign_seed_summary.json` records `status`/`compliance` for the same set and the recorded §9.3 deviation.

**Decision package (1).** Included only because `reports/PHASE_8_PILOT2_READINESS_DECISION.md:64` cites its Part E; its "not approved" header is historical (§4.6).

```
docs/PHASE_8_OWNER_DECISION_PACKAGE.md
```

**Exact command (Recommended tier):**

```bash
git add -- \
  experiments/results/phase_8_random/campaign_seed_summary.json \
  experiments/results/phase_8_random/certification_seed_1.json \
  experiments/results/phase_8_random/certification_seed_2.json \
  experiments/results/phase_8_random/certification_seed_3.json \
  experiments/results/phase_8_random/certification_seed_4.json \
  experiments/results/phase_8_random/certification_seed_5.json \
  experiments/results/phase_8_random/certification_seed_6.json \
  experiments/results/phase_8_random/certification_seed_7.json \
  experiments/results/phase_8_random/certification_seed_8.json \
  experiments/results/phase_8_random/certification_seed_9.json \
  experiments/results/phase_8_random/certification_seed_10.json \
  experiments/results/phase_8_random/certification_seed_11.json \
  experiments/results/phase_8_random/certification_seed_12.json \
  experiments/results/phase_8_random/certification_seed_13.json \
  experiments/results/phase_8_random/certification_seed_14.json \
  experiments/results/phase_8_random/certification_seed_15.json \
  experiments/results/phase_8_random/certification_seed_16.json \
  docs/PHASE_8_OWNER_DECISION_PACKAGE.md
```

### 9.3 Totals

| Tier | Files | Bytes (approx.) |
|---|---|---|
| Required (incl. this report, excluding the report's own bytes) | 36 + 1 | 620,778 + report |
| Recommended | 18 | 888,397 |
| **All** | **55** | **about 1.5 MiB** |

No binary model weights, no graph `.npz`, no raw datasets and no third-party code are in either tier.

---

## 10. Files that must remain local or go to FLY-SURFER-DATA

No existing repository documentation refers to a `FLY-SURFER-DATA` location (a repository-wide search found none). The following layout is therefore a proposal; the owner must confirm the destination path and access method.

### 10.1 FLY-SURFER-DATA (large or externally sourced data)

| Local path | Size | Why not Git | Proposed destination |
|---|---|---|---|
| `datasets/processed/banc_v888/` (7 files: t1, t5, t10, nodes, id_map, manifest, construction report) | 101 MiB | Derived BANC substrate; `banc_graph_t1.npz` alone is 79.8 MiB, above GitHub's 50 MiB warning and close to the 100 MiB hard limit. The t5 graph and nodes are Pilot 1's pinned inputs. | `FLY-SURFER-DATA/banc_v888/`; verify each file against `experiments/phase_4h/baseline_integrity.json` and the Pilot 1 manifest hash |
| `datasets/processed/banc_v888_random/` (16 namespaces) | 209 MiB | 16 × ~13.5 MiB random graphs; the certificates that reference them are in Git (Recommended tier), the bytes are not | `FLY-SURFER-DATA/banc_v888_random/`; verify against `certification_seed_*.json` graph SHA-256 |
| `datasets/external/banc_v88/` (5 raw files) | 383 MiB | Raw external BANC download; `.gitignore` intends external data to stay local | `FLY-SURFER-DATA/banc_v88_raw/` or leave local |
| `datasets/external/banc_v888/` (empty tree) | 0 files | Nothing to preserve; empty directories are invisible to Git | Delete the empty tree locally at the owner's discretion |
| `external/endless-surfer-main/` (90 files) | 383 KiB | Third-party clone; no external code was adopted (`project-external-audit`), and only `references/` is ignored | Keep local, or `FLY-SURFER-DATA/external/`; add `external/` to `.gitignore` (§8) |

**Reproduction consequence:** a clone plus the Required/Recommended tiers reproduces all *code, records and hashes* of Pilot 1, but running it again requires the two `banc_v888` inputs from FLY-SURFER-DATA. This is expected and must be stated in any reproduction note; it is not a defect in the preservation set.

### 10.2 Keep local; do not preserve in Git at all

| Path | Size | Reason |
|---|---|---|
| `experiments/results/phase_4h/*.checkpoint.jsonl` (6 files) | 8.8 MiB | Regenerable Phase 4H intermediates, dated 2026-11-08, unrelated to Pilot 1 |
| `experiments/results/phase_7/neural_closed_loop_activity.npz` | 2.5 KiB | A Phase 7 demo output; prior-phase artifact, not Pilot 1 evidence |
| `reports/_tmp_4h4_check.json` | 196 KiB | Temporary Phase 4H check output; not a report |
| `experiments/results/phase_8_random/logs/` | 4 KiB | Operational logs (`*.log` already ignored). The `run_seeds_2_16.sh` script is small and could be included later if the owner wants the G3 regeneration command recorded; it is not required for Pilot 1 |
| `experiments/phase_8/stages/__pycache__/` | — | Ignored bytecode |

### 10.3 Hold for a separate decision (Phase 8-adjacent, not Pilot 1 preservation)

| Path | Size | Why hold |
|---|---|---|
| `reports/PHASE_8_GPU_READINESS_CHECKLIST.md` | 12 KiB | Pre-run checklist; not needed to reproduce or audit Pilot 1; time-stamped |
| `reports/PHASE_8_EXECUTION_READINESS_AFTER_SOFTWARE_COMPLETION.md` | 24 KiB | Written before D1; header still says U1–U18 "PROPOSED — not approved". Useful historical evidence of why D1 was needed, but stale if read as current |
| `reports/PHASE_8_EXTERNAL_INTEGRATION_RECOMMENDATIONS.md` + `docs/research/` (3 files) | 92 KiB | External-repository research; no external code adopted; separate topic |

If the owner wants a complete decision trail in Git, the execution-readiness report and the GPU checklist can be added later in a dated "pre-approval history" commit with a note. They should not be mixed into the Pilot 1 preservation commit without that note.

---

## 11. Risks and open decisions for the owner

1. **Protected-baseline drift (blocking).** `motor/__init__.py` fails a non-README pinned hash; `README.md` also fails. No Phase 8 freeze or publishable report until an authorised amendment or compliant restoration occurs. This audit records the failure and changes nothing.
2. **Data separation.** Pilot 1's graph and nodes are untracked. Confirm FLY-SURFER-DATA as their home and record its location/hashes in the data repository; otherwise a fresh clone cannot rerun the pilot.
3. **`.gitignore` gaps.** A future broad add would stage ~690 MiB of data. Either add the narrow rules in §8 before staging, or commit to explicit per-file staging permanently.
4. **Stale approval text.** Three antecedent documents say U1–U18 are unapproved. Including the decision package (Recommended tier) is justified only by the readiness-report reference; it must be read as a pre-D1 historical document.
5. **Scientific scope of the commit.** D2 exempts the **exact Pilot 1 grid only**. A preservation commit must not be described as authorization for Pilot 2, training, the campaign or any randomized-graph arm. The B7 deviation remains `deviation_recorded` and unaccepted.
6. **Execution-report totals error.** The `72,880` lines remain in a file whose hash is recorded. Preserve the correction as documented (this audit, the motor investigation and the Pilot 2 decision); do not edit the report without an authorised erratum and hash restatement.
7. **Tests were not run.** This audit certifies file identity and record consistency, not current test pass status. Run the Phase 8 suites in an authorised session before relying on the preservation commit as a tested state.

---

## 12. Limitations of this audit

- Read-only; no test suite, no integrity-verifier execution and no simulation was performed (§1.2).
- The 35/37 recheck reproduces the size + SHA-256 rule of `check_integrity()`; it does not call that function (which lives in a module whose verifier writes an output file). It does not evaluate the BANC manifest or any Phase 4G gate beyond the 37-entry list.
- File sizes and counts are as observed on 2026-11-20; they are not content hashes except where a SHA-256 is stated.
- The proposed destination layout for FLY-SURFER-DATA is a recommendation, not an existing configuration.
- `git status` was taken in a working tree whose content filters are configured, as noted at session start; the porcelain output and explicit `ls-files`/`check-ignore` checks were used to compensate.

---

## 13. Owner checklist

- [ ] Approve this audit and the Required/Recommended split.
- [ ] Decide on the Recommended tier (G3 certificates + decision package).
- [ ] Decide the `.gitignore` edit (§8) and whether it precedes staging.
- [ ] Decide the FLY-SURFER-DATA destination for `banc_v888` and `banc_v888_random`.
- [ ] Decide how to resolve the 35/37 baseline drift (authorised amendment or compliant restoration) — separately from this preservation commit.
- [ ] Authorise the explicit `git add -- …` commands in §9 (no `git add .` / `-A`).
- [ ] After staging, verify the index matches §9 exactly before committing.
- [ ] Do not describe the commit as authorising anything beyond Pilot 1, and do not claim a passing integrity gate.
