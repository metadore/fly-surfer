# Phase 8 Pilot 1 Execution Report — D2-authorized A viability grid

**Date:** 2026-11-20
**Stage:** REV4 §10.3 Pilot 1
**Evidence kind:** real production run (`evidence_kind = pilot`), 9/9 episodes
**Publication/freeze status:** **NOT publishable as a freeze report.** The run
manifest could not check the 37-file protected baseline at run time, and a
read-only post-run check found a pre-existing non-README drift
(`motor/__init__.py`, introduced by commit `3c74ae8` on 2026-11-19). The episode
rows are valid measurements of the model; the protocol's publication gate is not
passed.

---

## 1. D2 owner decision record

| Field | Value |
|---|---|
| Approval ID | **D2** |
| Date | 2026-11-20 |
| Decision | The G3 deviation is **not applicable to Pilot 1 only** |
| Record | `reports/phase_8_owner_approvals/D2.json` (SHA-256 `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327`) |
| Human-readable mirror | `reports/PHASE_8_OWNER_DECISION_D2.md` |
| Depends on | D1 (`reports/phase_8_owner_approvals/D1.json`, SHA-256 `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489`) |
| Bound to | REV4 `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`, SHA-256 `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |

Exact recorded scope:

- stage `pilot1`; condition `A` only;
- seeds `9001`, `9002`, `9003`; three episodes per seed; nine episodes;
- `uses_randomized_graph: false`; `uses_trained_artifact: false`;
- `g3_applicability: not_applicable_to_pilot1_only`;
- `accepts_g3_deviation: false`; `weakens_graph_certification: false`;
- `parameter_modifications_authorised: false`;
- G3 remains blocking for every experiment that requires randomized graphs.

D2 does **not** accept, amend or weaken the recorded G3 deviation. The deviation
in `experiments/results/phase_8_random/campaign_seed_summary.json` is unchanged:
`status = deviation_recorded`, `gate_weakened = false`,
`min_observed_free_gb = 1.628`, 16 certified seeds.

REV4 is unchanged (hash above). The stage gate, not the document, carries the
exemption.

---

## 2. Authorization implementation

The exemption is narrow, hard-coded and forgery-resistant.

`experiments/phase_8/campaign/protocol.py`

- `PILOT1_G3_SCOPE` fixes the only exempt grid (`pilot1`, `A`, seeds
  `9001/9002/9003`, 3 episodes, 9 entries). It is not read from configuration,
  so a changed configuration cannot widen it.
- `_read_owner_decision()` structurally validates D2 (`record_kind`,
  `approval_id = D2`, date, decision text, 64-hex document hash, D1 dependency,
  arms/seeds/episodes/`n_episodes`, and the three negative capability flags).
- `g3_applicability()` returns `pilot1_exempt = true` only when D2 is valid
  **and** its recorded document hash equals the REV4 file on disk.
- `_pilot1_scope_failures()` checks the requested plan field-by-field: stage,
  arms, seeds, episodes, 9 entries, no contrast estimation, and condition A's
  registry spec (`substrate = biological`, `requires_structure = false`,
  `trains = ("none",)`, `eta = null`) plus the configured pilot seeds.
- `stage_authorization()` applies the exemption only when the stage is `pilot1`
  **and** every scope check passes. Any mismatch, invalid D1, invalid D2, or an
  unreadable deviation record leaves the unchanged B7 refusal in place.
- `assert_campaign_authorized()` is deliberately **not** stage-aware. It still
  raises with D1 recorded and B7 open. Pilot 2, training, composition and the
  campaign therefore cannot inherit the exemption.

`experiments/phase_8/stages/common.py`

- `authorization_snapshot(stage=..., plan=..., config=...)` and
  `collect_blockers(..., stage=..., plan=...)` report the stage-specific gate.
- `drive_pilot()` calls `assert_stage_authorized(plan.stage, ...)` for real runs
  and then the independent 4 GiB memory gate (`_gate_report`). Authorization
  never replaces the memory gate; the gate is checked afterwards and before any
  directory is created.

`experiments/phase_8/stages/pilot1.py` / `pilot1_runner.py`

- Pilot 1 describes and runs the exact A grid.
- `Pilot1EpisodeRunner` is the production runner (condition `A` only,
  `RUNNER_ID = phase_8.stages.pilot1_runner.Pilot1EpisodeRunner`). It loads the
  BANC world lazily and records provenance before the episode. Its
  `input_hashes()` covers the seven frozen inputs.

---

## 3. Authorization tests and results

New file: `tests/test_phase_8_d2_authorization.py` (18 tests, synthetic fixtures
only, no episode executed):

- D1 is recognised; D2 is recognised and bound to REV4;
- Pilot 1 is authorized with the exemption applied while the deviation stays
  `deviation_recorded` / `gate_weakened = false`;
- `pilot1.run_pilot1` still raises `MemoryGateError` under a low-memory
  preflight and creates no directory;
- conditions C and D remain blocked (biological spec forgery, arms `C`, `D`,
  `("A","C")`, `C_prime`, and campaign stage);
- Pilot 2, training, composition and the campaign remain blocked; no
  inheritance;
- altered D2 (id, acceptance flag, certification flag, seeds, randomized graph,
  hash, record kind), missing D2, altered/missing D1, and an appended REV4 copy
  are all refused;
- unrelated gates are not bypassed (campaign snapshot keeps B7; composition
  preflight is not ready; other stages refuse).

Results:

- `tests/test_phase_8_d2_authorization.py`: **18 passed** (2.91 s).
- Affected Phase 8 modules: **284 passed** (13.57 s).
- Full suite: **1503 passed, 3 skipped, 6 failed** (96.44 s). The six failures
  pre-date this work and are unrelated to D2/Pilot 1: three protected-hash
  checks report the README pin drift, two smoke-mode labels report
  `SMOKE INVALID` instead of `SMOKE ONLY`, and one C0 cache assertion fails.
  No test executes a real episode.

---

## 4. Final preflight

Artifact: `reports/PHASE_8_PILOT1_PREFLIGHT.json`
(SHA-256 `87bf60dca16d97323ed14dde1d2f9d1b360ef84bbe66f2eabf6abe68a3156566`).
All 14 enumerated checks passed (`failed_checks: []`):

| Check | Result |
|---|---|
| REV4 identity/hash (`e4aa9e0f…b1547c`) | pass |
| D1 approval valid and bound | pass |
| D2 valid, bound, `pilot1_exempt`, both negative flags false | pass |
| G3 deviation preserved (`deviation_recorded`, not weakened, 1.628 GB, 16 seeds) | pass |
| `stage_authorization("pilot1", …)` authorized, blockers empty | pass |
| Exact 9-entry grid: A / 9001–9003 / 3 episodes / no contrasts | pass |
| Condition A spec: biological, no structure, trains none, eta null | pass |
| No randomized-graph dependency | pass |
| No trained-artifact dependency (`TrainingArtifacts().empty`) | pass |
| Production runner importable, 7 frozen-input hashes | pass |
| 4 GiB memory gate: **5.924 GiB available** (gate 4.0) | pass |
| Results/output paths free (`experiments/results/phase_8` absent) | pass |
| Config hashes (environment/campaign/conditions) match | pass |
| Constants: master seed 20261116, max updates 900, gate 4.0 | pass |

The preflight did **not** include the 37-file protected baseline. The stage
manifest records `integrity.checked = false` with the honest note that a report
may not be published until it is checked. A read-only post-run check is in
§7.1.

---

## 5. Did Pilot 1 execute?

**Yes.** The authorized nine-episode Pilot 1 executed through the production
path (`run_pilot1` → `drive_pilot` → `Pilot1EpisodeRunner` →
`a_fixed.run` → `NeuralClosedLoop`) on the frozen biological substrate.

- Run directory: `experiments/results/phase_8/pilot1/pilot1/`
- Summary: `executed = true`, `rows_stored = 9`, `rows_executed = 9`,
  `planned = 9`, `complete = true`, `evidence_kind = pilot`,
  `experimental_evidence = true`, `estimates_contrasts = false`,
  `merged_into_campaign = false`.
- Driver record: `reports/PHASE_8_PILOT1_EXECUTION.json`
  (SHA-256 `d3392b9c7132b5ee92652a69509d5ae43b57b9a66024178bed30e7af57c23e1e`).
- Wall time: 357.0 s (5 min 57 s), 2026-11-20T10:58:51Z → 11:04:48Z.
- Nothing else was run: no training, no Pilot 2, no confirmatory campaign, no
  randomized graph, no parameter change, no network intervention.

Run-start memory gate inside the driver: 5.745 GiB available (gate 4.0 GiB).

---

## 6. Nine episode results

Rows: `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`
(SHA-256 `ee479e5b1f4fe3cfe00ef170b0c2126dcdddc7b2b241343bf8736d6af9d468f9`).
All nine rows: condition `A`, role `reference`, `training = false`, status `ok`,
`evidence_kind = pilot`, `experimental_evidence = true`, 7 input hashes,
3 config hashes.

| seed | ep | env seed | game updates | neural steps | total spikes | motor spikes | actions | reward | survival | termination | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9001 | 0 | 563774599 | 323 | 10,767 | 4,764 | 0 | NO_ACTION ×323 | 5.22 | 323.0 | collision | 30.07 |
| 9001 | 1 | 2911696168 | 620 | 20,667 | 14,348 | 0 | NO_ACTION ×620 | 10.19 | 620.0 | collision | 72.81 |
| 9001 | 2 | 4240939637 | 323 | 10,767 | 4,764 | 0 | NO_ACTION ×323 | 4.22 | 323.0 | collision | 26.81 |
| 9002 | 0 | 2632356062 | 620 | 20,667 | 14,911 | 0 | NO_ACTION ×620 | 7.19 | 620.0 | collision | 59.27 |
| 9002 | 1 | 307060235 | 426 | 14,200 | 8,396 | 0 | NO_ACTION ×426 | 3.25 | 426.0 | collision | 38.41 |
| 9002 | 2 | 4241804999 | 620 | 20,667 | 13,139 | 0 | NO_ACTION ×620 | 8.19 | 620.0 | collision | 53.11 |
| 9003 | 0 | 2839813884 | 213 | 7,100 | 2,850 | 0 | NO_ACTION ×213 | 3.12 | 213.0 | collision | 18.04 |
| 9003 | 1 | 756850162 | 426 | 14,200 | 7,856 | 0 | NO_ACTION ×426 | 4.25 | 426.0 | collision | 36.84 |
| 9003 | 2 | 2981106662 | 213 | 7,100 | 2,852 | 0 | NO_ACTION ×213 | 2.12 | 213.0 | collision | 17.79 |

Totals: **3,784 game updates**, **126,135 neural steps**, **72,880 total
spikes**, **0 motor spikes**, **47.75 total reward**. No episode reached the
900-update cap; `terminated = true` and `truncated = false` for all nine.

Per-episode motor population spikes: `JUMP 0`, `LEFT 0`, `RIGHT 0` in every
episode. `motor_summary.windows_with_motor_spikes = 0` throughout. Decoder
fallbacks: `{}`; unmapped/invalid: `0`. The `NO_ACTION` output is the decoder's
thresholded output, not an error fallback.

Weight fingerprints: one value before and after every episode,
`4923f0cd45d55fd4cd80d81392974dd5058ca988f18348734d10b45b06d945d5`
(1,535,710 edges; 502,727 excitatory; 180,373 inhibitory). Weights are unchanged
and the structural/initial digests did not change.

Decoder output: every recorded decision is `NO_ACTION`; no `decision_classes`
(readout ablation labels) are present for A.

---

## 7. Failures and deviations

### 7.1 Protected baseline drift (pre-existing, blocks freeze)

A read-only post-run check of `experiments/phase_4h/baseline_integrity.json`
(37 protected files, 35 matching) found:

| File | Expected | Actual |
|---|---|---|
| `README.md` | `8ab6a8cc…5563` | `8a79d44d…4164` |
| `motor/__init__.py` | `17ac008c…3c8de` | `859b02a9…1c40e` |

`motor/__init__.py` is a **non-README** failure, so `check_integrity()`
returns `pass = false`. Its current content was introduced by commit `3c74ae8`
(2026-11-19), i.e. before this execution; it is not a change made by the D2
implementation or by Pilot 1. The run manifest still says
`integrity.checked = false`, so this pilot is **not** a freeze/publishable
report under REV4 §6.10/§10.12. Resolving it requires an authorised amendment or
a compliant restoration; it was not changed here.

### 7.2 Zero motor output

All nine episodes produced zero motor-population spikes and only `NO_ACTION`.
The network as a whole was active (72,880 spikes), so this is not a silent or
dead simulation. It is a substantive negative result for the A configuration:
the fixed decoder never selected a motor action. This is consistent with the
earlier negative Phase 4 sensory→motor finding, but it is not evidence about a
fly and must not be re-described as a biological motor result.

### 7.3 Other limitations

- Three seeds × three episodes is a viability sample, not an inference sample;
  no C1–C4 contrast is estimated and no hypothesis is tested.
- `pilot_plan.json` is the pre-execution plan copy and still says
  `executed = false` / "construction-only output". The authoritative records are
  `pilot_summary.json`, the manifest and the nine rows, all of which record the
  run as executed and experimental. This label nuance is recorded rather than
  rewritten.
- Memory was sampled passively at 2 s intervals in the driver: 177 samples,
  process RSS max **0.3725 GiB**, system available min **4.1997 GiB**, i.e. it
  stayed above the 4.0 GiB gate throughout. The gate is the protocol's
  independent condition; the historical B7 deviation (1.628 GiB during graph
  construction) remains recorded and unaccepted.
- No parameter, neural equation, randomized graph or REV4 file was modified.

---

## 8. Updated scientific interpretation

Pilot 1 establishes **software viability**, not a scientific effect:

1. The frozen BANC substrate (1,535,710 edges) loads and runs inside the
   controlled game environment. The complete provenance chain — manifest, plan,
   rows, 7 frozen-input hashes, 3 config hashes, D1/D2-bound authorization —
   is recorded and self-consistent.
2. The fixed-weight condition A holds its weight fingerprint constant and
   records spikes, actions, rewards, survival and terminations without
   fallbacks or errors.
3. It does **not** establish motor output. Every one of the 3,784 decisions was
   `NO_ACTION`; motor populations never spiked. A provides no evidence of a
   sensory-to-motor transformation in this configuration, and no contrast
   against any other arm.
4. All episodes ended by collision well before the 900-update cap. Survival
   (213–620) and reward (2.12–10.19) are descriptive of this run only.
5. The D2 exemption changed authorization only. Randomized-graph experiments
   remain blocked by the unchanged B7 deviation; Pilot 2 and the confirmatory
   campaign remain blocked; G3 is still unresolved and unaccepted.
6. The zero-motor outcome is a diagnostic signal for the A pipeline (sensory
   drive, population mapping or threshold selection), not a result that may be
   tuned away without a new authorized analysis. No tuning was performed.

The result is therefore: **Pilot 1 is operationally viable and scientifically
null on motor output.** It supports no claim about biological motor coding and
cannot be used to estimate C1–C4.

---

## 9. Git status

No commit and no push were made. Current working tree (read-only inspection):

Tracked files modified (prior work in this session included; none changed by the
Pilot 1 run itself):

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

New/untracked artifacts relevant to this mission:

```
 reports/phase_8_owner_approvals/D1.json
 reports/phase_8_owner_approvals/D2.json
 reports/PHASE_8_OWNER_APPROVAL_D1.md
 reports/PHASE_8_OWNER_DECISION_D2.md
 reports/PHASE_8_PILOT1_PREFLIGHT.json
 reports/PHASE_8_PILOT1_EXECUTION.json
 reports/PHASE_8_PILOT1_EXECUTION_REPORT.md
 experiments/phase_8/stages/
 tests/test_phase_8_d2_authorization.py
 tests/test_phase_8_pilot1_runner.py
 tests/test_phase_8_stage_infrastructure.py
 experiments/results/phase_8/pilot1/pilot1/{manifest.json,pilot_plan.json,pilot_summary.json,episodes.jsonl}
```

Other untracked datasets/external trees and earlier result artifacts pre-date
this mission. `README.md` and `motor/__init__.py` are unchanged by this mission;
`motor/__init__.py` is the pre-existing protected-baseline drift described in
§7.1.

---

## Artifact hashes

| Artifact | SHA-256 |
|---|---|
| REV4 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| D1 record | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| D2 record | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |
| `episodes.jsonl` | `ee479e5b1f4fe3cfe00ef170b0c2126dcdddc7b2b241343bf8736d6af9d468f9` |
| `manifest.json` | `58cde4cf11272b1b28a353b7678b3fcaa02d41488e069039ecd6720159d2e9cc` |
| `pilot_plan.json` | `99fb1385939d4506cd3c9f001dc7e66552c4dc1dd30878b34606302fd903646a` |
| `pilot_summary.json` | `76b68c2626d9733548c107dbb381b2ab660431ea029bae4b4c6b9bfde694351b` |
| Preflight record | `87bf60dca16d97323ed14dde1d2f9d1b360ef84bbe66f2eabf6abe68a3156566` |
| Execution record | `d3392b9c7132b5ee92652a69509d5ae43b57b9a66024178bed30e7af57c23e1e` |

Configuration hashes recorded in the run:

- `configs/phase_8/environment.yaml` — `b391ecf71fd7acac0517a677f9198d6a252a00428aabf8c58d3b6b343a3281dc`
- `configs/phase_8/campaign.yaml` — `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19`
- `configs/phase_8/conditions.yaml` — `9a93f04771a2489b09a14c2b74418ffb423ad9702d7bc3a47492a2012d42f671`

Frozen inputs (all present, all hashed; full list in `manifest.json`):

```
graph            datasets/processed/banc_v888/banc_graph_t5.npz
nodes            datasets/processed/banc_v888/banc_nodes.csv.gz
neuron_config    configs/neuron_config.yaml
synapse_policy   configs/banc_synapse_policy.yaml
motor_decoder    configs/motor_decoder.yaml
sensory_mapping  configs/banc_sensory_mapping.yaml
plasticity       configs/plasticity_banc.yaml
```

Seed derivation (from the manifest): master `20261116`; environment
`[master, seed, episode, 1]`; network `[master, condition_code, seed, 2]`;
learning `[master, condition_code, seed, 3]`; structure `[master, seed, 4]`.
Per-episode environment/network/learning/structure seeds are in
`pilot_plan.json` and the driver record.
