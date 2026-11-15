# P3-3C.5 — Consolidated Pre-Execution Readiness Report

**Status:** READINESS REPORT — NO EXECUTION PERFORMED

**Date:** 2026-11-15 (UTC)

**Repository:** `C:\Users\Hp\fruitfly\FLY-SURFER`

**Baseline:** branch `main`, HEAD `62a64309cadc0db7353c856607cee5369993bd65`.

**Scope.** This is a new consolidated report. It replaces no existing document and does not modify any frozen file. It records read-only inspection of the frozen protocol, amendment record, implementation, configuration, tests and prior audits. No pilot, main or determinism simulation was run; no result artifact was generated; nothing was staged, committed, pushed, reset, cleaned, stashed, moved or deleted. The only file created by this task is this report.

---

## 1. Executive summary

**Verdict: READY WITH ACCEPTABLE LIMITATIONS.**

The frozen P3-3C.5 implementation is internally consistent, hash-stable, campaign-isolated and guard-protected. The 42-instance pilot is exactly defined, uses only seed 20261107, contains no main or determinism instances, writes to distinct output paths and cannot silently expand into another campaign. The main matrix is 126 distinct runs plus 18 planned determinism repeats; the preregistration's total of 186 distinct run instances reconciles exactly. No stop condition from the prior audit is triggered, and no frozen hash differs.

Three material limitations remain, none of which invalidates a scientifically valid pilot or main campaign:

1. **Pilot checks are not evaluated by the runner (D1).** Runtime, capacity, reference degeneracy and metric computability are valid constants in the configuration but are only echoed into the pilot JSON. The raw measurements needed to evaluate all four are recorded, so the checks are computable post hoc from the pilot artifact, but the runner emits no verdict.
2. **Failed attempts are not preserved as artifacts (D3).** Preregistration §6.2 requires failed attempts to be preserved and reported. The runner has no failure artifact and no resume path; an exception discards the in-memory campaign. This can be mitigated operationally by capturing the console log externally, but not by the frozen code.
3. **The standalone determinism campaign reads the unversioned main path (D5).** It is safe on a clean first run when the main result is written at `p3_3c5_lane_encoding.json`. After a versioned main rerun (`.v2.json`), the standalone determinism campaign would still read the older base file as parent, producing a mismatched provenance record.

The pilot is ready for a separate authorisation decision, conditional on an explicit agreement to perform the four pilot checks post hoc and record the result before the main campaign, and to capture failure logs externally. No frozen implementation correction is strictly necessary for a clean first run. Three corrections are recommended before any rerun or automated pilot certification.

---

## 2. Current frozen state

### 2.1 Authoritative documents

| Document | SHA-256 | Role |
|---|---|---|
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` | Authoritative amended protocol |
| `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` | `44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd` | Amendment record; E11 withdrawn 2026-11-14 |

The pre-amendment hash `1daa2439…` is superseded and is not used as authoritative. It is not restored.

### 2.2 Frozen implementation set

All hashes below were recomputed from the working tree for this report and match the freeze record.

| File | SHA-256 | Role |
|---|---|---|
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` | Runner, measurement, gates, reporting, guards (2,850 lines) |
| `configs/p3_3c5_lane_encoding.yaml` | `21e4257d7022a7333fa84bef37df489e25e31b016080dfcd64ef0029498df638` | Frozen configuration (533 lines, 42 conditions) |
| `tests/test_p3_3c5_lane_encoding.py` | `e8281529f31a208709bd02d3ec59ef528c72c4fd7f5e9e034df92ade16995f73` | Non-simulation test suite (1,392 lines) |
| `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` | `db9fe075da5d5ace3cd6f183e7806dcab114d91c95a1e2470b8771d2eeed7f95` | Compliance audit, revision 2 |
| `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` | `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194` | Historical E11-blocker audit |
| `docs/P3_3C5_IMPLEMENTATION_FREEZE_RECORD.md` | `7528ed55c576ed12a8df19fac96ac895897d268b4a04841081c119c8303ba835` | Implementation freeze record |

### 2.3 Protected files

| File | SHA-256 | Status |
|---|---|---|
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | MATCH |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | MATCH |

### 2.4 E12 existing-suite evidence

Recorded in the implementation freeze record; not re-run in this task.

| Metric | Value |
|---|---|
| Command | `python -m pytest -q` |
| Collected | 919 |
| Passed | 916 |
| Failed / errors | 0 / 0 |
| Skipped | 3 (the three end-to-end execution-boundary tests) |
| Duration | 104.32 s |
| Exit code | 0 |

The three skips are `test_main_campaign_end_to_end_not_run`, `test_pilot_campaign_end_to_end_not_run` and `test_determinism_repeats_end_to_end_not_run`, each explicitly marked as not run because execution is not authorised. No test was weakened or deselected.

### 2.5 Repository state at audit start

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `62a64309cadc0db7353c856607cee5369993bd65` |
| `git status --short` entries | 225 |
| Staged entries | 0 |
| P3-3C.5 result artifacts | none (`experiments/phase_3c/results/` contains no `p3_3c5*`) |

The 225 pre-existing entries are unrelated Phase 3B/3C/4/5/6 modifications and untracked files. They were not touched.

### 2.6 Freeze integrity

The implementation freeze record remains intact and unmodified. No frozen file was edited by this task. This report is the only new file.

---

## 3. D1–D4 assessment

### 3.1 Evaluation questions

Each discrepancy is assessed against seven questions:

1. What exactly is missing?
2. Does it violate the frozen preregistration?
3. Is it an implementation defect or a documented limitation?
4. Can it be evaluated from existing recorded measurements?
5. Does it prevent a scientifically valid pilot?
6. Does it prevent a scientifically valid main campaign?
7. Does resolving it require modifying frozen files?

### 3.2 Consolidated issue table

| ID | Issue | Violates prereg? | Defect or limitation | Post-hoc evaluable | Pilot impact | Main impact | Frozen fix needed | Severity |
|---|---|---|---|---|---|---|---|---|
| D1 | Four pilot checks are validated but not evaluated; no verdict block | Partially: §14.5 step 3 verification is not implemented in the runner | Implementation gap, disclosed | Yes, from the pilot JSON | None on data validity; certification must be manual | None if the manual check is recorded before main | No for a manual check; yes to automate | **MAJOR** |
| D2 | Pilot E10 records `passed: true` with `not_applicable_for_pilot` | No: pilot has no repeats by design | Reporting choice | Not applicable | Risk of misreading as determinism evidence | None | No | **MINOR** |
| D3 | Failed attempts are not preserved; `deviations` always `[]`; no resume | Yes: §6.2 line 456 | Implementation gap | No artifact exists; only console output | Only if a run fails | Only if a run fails | Yes to automate; operational log capture mitigates | **MAJOR** |
| D4 | Only the JSON path is checked before writing; orphan `_spikes.npz` can be overwritten | Partially: §14.2 no-overwrite intent | Narrow edge case | Determined from code | Not in a completed run | Not in a completed run | Yes to fix; avoidable operationally | **MINOR** |
| D5 | Standalone determinism campaign reads `JSON_PATH` even after a versioned main rerun | No direct protocol violation | Implementation edge case | Determined from code | None | None | Yes to fix reruns; first run safe | **MAJOR (conditional)** |
| D6 | 186 planned instances versus 204 executions if the standalone determinism campaign is run | No: 186 counts distinct instances | Accounting ambiguity | Yes | None | Must be documented | No | **ACCEPTABLE LIMITATION** |
| D7 | Per-run "capacity" is not a separate JSON field | Partially: §13.1 wording | Reporting gap | Yes: `n_spikes` and `protocol.max_recorded_spikes` | None | None | No | **MINOR** |
| D8 | Per-neuron spike times are in the `.npz`, not inline JSON | Partially: §13.1 wording | Artifact layout choice | Yes | None | None | No | **ACCEPTABLE LIMITATION** |
| D9 | Hidden `--execute-single` does not require `--existing-tests-passed` | No | Documented residual in compliance audit §10.1 | Yes | Cannot launch a campaign | Cannot launch a campaign | No | **MINOR** |
| D10 | Compliance audit E12 row is stale | No | Documentation already reconciled in the freeze record | Yes | None | None | No | **ACCEPTABLE LIMITATION** |

No issue is classified **BLOCKER**.

### 3.3 D1 — pilot checks not evaluated

1. **Missing.** The runner validates that `pilot_checks.checks` contains `runtime`, `capacity`, `reference_degeneracy` and `metric_computability`, and echoes the whole `pilot_checks` block into `payload["pilot"]["checks"]`. It computes no result, no pass/fail and no summary for any of the four. `analyse_seed` is skipped for the pilot, and the rendered pilot report contains empty analysis tables.
2. **Pre-registration.** §14.5 step 3 requires the pilot to "verify runtime, capacity, reference non-degeneracy and metric computability". The runner does not perform that verification. It does record the raw measurements from which three of the four can be evaluated and the wall time for the fourth, so the protocol sequence can still be discharged by an authorised post-hoc step. This is partial non-conformance to the execution sequence, not a change to the scientific design.
3. **Defect or limitation.** Implementation gap. It is disclosed in the prior audit and in this report; it is not a hidden defect.
4. **Post-hoc evaluation.** Yes. Runtime is `payload["runtime_s"]` and per-run `runs[seed][condition]["wall_runtime_s"]`. Capacity is `runs[seed][condition]["n_spikes"]` against `protocol.max_recorded_spikes = 5,000,000`. Reference degeneracy is computable from the CENTER `center_state_relative.m6_prime.value_hz` of the R200 and R150 conditions. Metric computability is evident from the presence of the 4 × 3 CENTER count matrices and M6′ values for C1, C2, C3, C4 and K_C.
5. **Pilot validity.** Not prevented. The pilot executes all 42 conditions and records the measurements it is meant to inspect.
6. **Main validity.** Not prevented, provided the four checks are evaluated and recorded between the pilot and the main campaign, as step 3 requires.
7. **Frozen-file modification.** Automating the verdict would require a runner change (a frozen file). The manual post-hoc path requires no frozen-file change and is the recommended resolution for this authorisation cycle.

### 3.4 D2 — pilot E10 representation

1. **Missing.** A distinct "not applicable" gate state. The gate detail contains `{"not_applicable_for_pilot": true}`, but `passed` is `true`.
2. **Pre-registration.** No violation. E10 is defined over 6 conditions × 3 main seeds; the pilot has no repeats and no main seed.
3. **Defect or limitation.** Reporting choice. The detail field is explicit, and the report header renders `PILOT ONLY`.
4. **Post-hoc evaluation.** Not applicable; there are no repeat runs to compare.
5. **Pilot validity.** No effect.
6. **Main validity.** No effect; the main campaign evaluates E10 over the 18 real repeats.
7. **Frozen-file modification.** None needed.

### 3.5 D3 — failed attempts and incomplete campaigns

1. **Missing.** A persisted failure record, a populated `deviations` list and any resumption path. The campaign loop has no per-run exception handling; an exception propagates, and no JSON, sidecar, report or spike file is written.
2. **Pre-registration.** §6.2 line 456 states: "Failed attempts are preserved and reported; they are not replaced silently." The runner does not preserve a failed attempt as an artifact. This is a direct non-conformance for any failed attempt.
3. **Defect or limitation.** Implementation gap.
4. **Post-hoc evaluation.** No. Once the process exits, only console output remains unless it was captured externally.
5. **Pilot validity.** Only affected if a run fails. A clean 42-instance pilot is unaffected.
6. **Main validity.** Only affected if a run fails. An E10 subprocess failure inside the main campaign would discard 126 completed in-memory runs because the artifact is written only at the end.
7. **Frozen-file modification.** Automatic preservation would require a runner change. Operational mitigation: run under an external log capture, preserve the log and report any failure manually. This does not satisfy §6.2 automatically but keeps the record honest.

### 3.6 D4 — orphan spike file overwrite

1. **Missing.** Existence checks for the sidecar, report and spike files. `_resolve_output` checks only the JSON path; the other three follow the resolved JSON name.
2. **Pre-registration.** §14.2 requires existing results not to be overwritten and reruns to receive a versioned name. The JSON satisfies this. The orphan case can overwrite a spikes file left by a crash between `np.savez_compressed` and the JSON write.
3. **Defect or limitation.** Narrow implementation edge case.
4. **Post-hoc evaluation.** Determined from code; not observable from a completed artifact.
5. **Pilot validity.** No effect in a completed run.
6. **Main validity.** No effect in a completed run.
7. **Frozen-file modification.** Yes to fix; operationally avoidable by ensuring no `p3_3c5_*_spikes.npz` exists before a run.

### 3.7 Additional findings

- **D5 — determinism parent resolution.** `_run_determinism_campaign` requires `JSON_PATH.exists()` and reads `JSON_PATH`, while a main rerun may write `p3_3c5_lane_encoding.v2.json`. The standalone determinism campaign would then compare repeats against the older base result. On a clean first run with no base file this cannot occur. After any main rerun, the standalone check is unsafe unless the base file is handled or the code is corrected. Severity: **MAJOR (conditional)**.
- **D6 — 186 versus 204 executions.** The main campaign executes its 18 repeats internally (126 + 18 = 144). The standalone determinism campaign re-executes the same 18, producing a second artifact. Running all three campaigns therefore executes 204 instances, while the frozen plan counts 186 distinct instances. The 186 figure is correct for distinct instances and is satisfied by pilot (42) + main (144). The standalone campaign is an implementation-added verification rerun, not a preregistration requirement. Severity: **ACCEPTABLE LIMITATION**, to be stated explicitly in the execution record.
- **D7 — per-run capacity field.** Capacity is a frozen constant (`5,000,000`) in `protocol.max_recorded_spikes`, and `n_spikes` is recorded per run. No separate `capacity` field is emitted. The information is present and evaluable. Severity: **MINOR**.
- **D8 — per-neuron spike times.** The `.npz` stores times and indices under `{seed}__{condition}__times_ms` and `{seed}__{condition}__neuron_indices`. The JSON stores per-neuron counts. This satisfies the spirit of §13.1 with a split artifact layout. Severity: **ACCEPTABLE LIMITATION**.
- **D9 — `--execute-single`.** The hidden single-run entry point requires `--acknowledge-execution-authorised` and a request whose config hash matches, but does not require `--existing-tests-passed`. It cannot launch a campaign. Severity: **MINOR**, already documented.
- **D10 — stale E12 row.** The compliance audit's E12 row predates the full-suite run. The freeze record supersedes it and the audit was intentionally left unmodified to preserve its hash. Severity: **ACCEPTABLE LIMITATION**.

---

## 4. Four pilot-check assessment

### 4.1 Summary

| Check | Exact definition in the frozen documents | Acceptance criterion | Recorded measurements | Post-hoc evaluable | Missing | Affects continuation or interpretation |
|---|---|---|---|---|---|---|
| Runtime | §14.5 step 3: "verify runtime"; §13.1: record wall time | **Not numerically defined** | `runtime_s` (campaign), `wall_runtime_s` per condition, environment | Yes | A numeric threshold or operational window | Operational only; no code gate |
| Capacity | Spike capacity 5,000,000; §12 capacity failure invalidates a run; E1 includes capacity failure | No `SpikeCapacityExceeded`; `n_spikes < 5,000,000` | `n_spikes` per condition; `protocol.max_recorded_spikes` | Yes | A separate capacity field (constant is in `protocol`) | A failure aborts the run and is recorded as invalid |
| Reference degeneracy | §10.1 class 4: R200 pred-LEFT equals pred-RIGHT, or R150 ranges degenerate, in ≥2/3 seeds | Exact equality / zero-width range | CENTER `m6_prime.value_hz` for R200 and R150 conditions | Yes | The ≥2/3 rule cannot apply to a one-seed pilot; only the per-seed property can be checked | On main, degeneracy in ≥2/3 seeds yields `INCONCLUSIVE_REFERENCE_DEGENERATE` |
| Metric computability | §14.5 step 3; §9.5 optional residual only if runs available and alignment implementable | **Not numerically defined**; structural presence of the metric inputs | 4 × 3 CENTER counts, rates, M6′ and per-neuron counts for every condition with an onset | Yes for M6′ and `Δ_C`; no for the optional residual | An explicit definition; the optional residual is not implemented | Without M6′ inputs the main analysis cannot run |

### 4.2 Runtime

- **Definition.** The preregistration requires the pilot to verify runtime but defines no numeric limit. The runner records the campaign total and each condition's wall time.
- **Criterion.** Ambiguous. This report does not invent one. The authorising decision should state the operational window, or accept the recorded values descriptively.
- **Data.** `payload["runtime_s"]` and `runs["20261107"][condition_id]["wall_runtime_s"]`, plus `environment`.
- **Post hoc.** Directly readable. The sum of per-run wall times will be less than the campaign total because mapping construction, gates, measurement and writing are outside the per-run timer.
- **Interpretation.** The pilot's runtime informs scheduling of the main campaign; it does not alter the scientific result.

### 4.3 Capacity

- **Definition.** Each run has a 5,000,000-spike recorder. Exceeding it raises `SpikeCapacityExceeded` rather than dropping spikes. A capacity failure invalidates the run (§12), and E1 covers completion.
- **Criterion.** No exception; every `n_spikes` is below 5,000,000.
- **Data.** `n_spikes` per condition; `protocol.max_recorded_spikes`.
- **Post hoc.** Yes, exactly.
- **Interpretation.** Capacity is a safety limit, not a scientific threshold. A failure would invalidate the affected run and would need to be reported, not imputed.

### 4.4 Reference degeneracy

- **Definition.** §10.1 defines `INCONCLUSIVE_REFERENCE_DEGENERATE` for the case where the R200 pred-LEFT and pred-RIGHT values are identical, or the R150 ranges are degenerate, in at least 2 of 3 seeds. The implemented predicate is exact: `r200_left == r200_right`, or both R150 within-group ranges have zero width.
- **Criterion.** Exact equality / zero width. No tolerance is defined.
- **Data.** `runs["20261107"]["R200_RLC"].center_state_relative.m6_prime.value_hz`, the same for `R200_LRC`, and the ten non-focal R150 condition values. C3 and C4 can also be read.
- **Post hoc.** Yes, with one constraint: a one-seed pilot cannot support the "≥2/3 seeds" part of the classification. It can report whether the single pilot seed is degenerate and can record the reference values and ranges for later comparison.
- **Ambiguity.** The preregistration does not define "degenerate range" numerically beyond the implemented zero-width reading. This report uses the implemented predicate and states the ambiguity rather than creating a tolerance.

### 4.5 Metric computability

- **Definition.** The pilot must show that the primary metric and its inputs are computable. §9.5 additionally gates the optional linear-superposition residual on the pilot confirming that the runs are available and the alignment is implementable.
- **Criterion.** Not numerically defined. Structurally: every condition with a CENTER onset has a 4 × 3 CENTER count matrix, rates on the 50 ms denominator, and an M6′ value; the per-neuron rows are present.
- **Data.** `runs[seed][condition]["center_state_relative"]` for C1, C2, C3, C4, K_C and every R200/R150 condition.
- **Post hoc.** Yes for M6′ and `Δ_C(i)`. The optional residual in §9.5 is not implemented, so it cannot be evaluated from the frozen runner and must not be reported.
- **Interpretation.** Metric computability is a precondition for the main analysis, not a scientific result.

### 4.6 Required post-hoc procedure (no thresholds invented)

Before the main campaign, an authorised post-pilot step should record:

1. `runtime_s` and the per-condition wall times, with the operational window chosen by the authoriser.
2. `max(n_spikes)` over the 42 pilot runs and the fact that no capacity exception occurred.
3. The R200 pred-LEFT and pred-RIGHT values, the R150 pred-LEFT and pred-RIGHT value lists and their ranges, and whether the implemented degeneracy predicate is true for seed 20261107.
4. The presence of a 4 × 3 CENTER count matrix and an M6′ value for every condition with a CENTER onset, including C1, C2, C3, C4 and K_C.
5. A statement that the optional §9.5 residual is not implemented and is not reported.
6. A statement that pilot data do not enter the main result and that no threshold was tuned.

This procedure discharges steps 3 and 4 of §14.5 without modifying any frozen file.

---

## 5. Exact campaign reconciliation

### 5.1 Frozen definitions

| Campaign | Seeds | Conditions | Distinct instances | Determinism repeats | Executions in campaign |
|---|---|---|---|---|---|
| Pilot | 20261107 | all 42 | 42 | 0 | 42 |
| Main | 20261104, 20261105, 20261106 | all 42 | 126 | 18 | 144 |
| Determinism (standalone) | 20261104, 20261105, 20261106 | C1, C2, C3, C4, N0, K_C | 0 new; 18 re-executions | 18 | 18 |
| **Distinct total** | — | — | **186** | — | — |

The preregistration's 186 is the sum of distinct instances: 42 pilot + 126 main + 18 determinism. The standalone determinism campaign does not add a distinct instance; it re-executes the 18 repeats already run inside main. Running pilot, main and standalone determinism executes 204 instances in total. See D6.

### 5.2 Seeds and conditions

- Main seeds: `[20261104, 20261105, 20261106]`.
- Pilot seed: `20261107`; `pilot_excluded_from_main: true`; the sets are disjoint.
- Conditions: exactly 42 unique IDs, in eight frozen groups: `core` 4, `linear_200` 4, `closed_150` 10, `constant` 3, `no_input` 1, `single_transition_200` 6, `single_transition_150` 6, `crossfade` 8.
- Determinism set: `[C1, C2, C3, C4, N0, K_C]`, step mode, one repeat per parent, fresh subprocess.

### 5.3 Instance identity

The runner does not emit a separate instance-ID field. Identity is the `(seed, condition_id)` pair:

- JSON: `payload["runs"][str(seed)][condition_id]`.
- Spike archive: key prefix `{seed}__{condition_id}__times_ms` and `{seed}__{condition_id}__neuron_indices`.
- Determinism: `payload["results"][str(seed)][condition_id]`.

This identity is deterministic and collision-free because both the seed list and the condition list are unique. There is no separate manifest file enumerating instances; the configuration and `plan_campaign` are the manifest.

### 5.4 Group-by-group pilot manifest (42)

| Group | Condition IDs | Count | Seed |
|---|---|---|---|
| core | C1, C2, C3, C4 | 4 | 20261107 |
| linear_200 | R200_CLR, R200_CRL, R200_LRC, R200_RLC | 4 | 20261107 |
| closed_150 | R150_CLLR, R150_CLRL, R150_CRLL, R150_LCLR, R150_RCLL, R150_LLCR, R150_RLCL, R150_LLRC, R150_LRLC, R150_RLLC | 10 | 20261107 |
| constant | K_L, K_C, K_R | 3 | 20261107 |
| no_input | N0 | 1 | 20261107 |
| single_transition_200 | T200_LC, T200_RC, T200_LR, T200_CR, T200_RL, T200_CL | 6 | 20261107 |
| single_transition_150 | T150_LC, T150_RC, T150_LR, T150_CR, T150_RL, T150_CL | 6 | 20261107 |
| crossfade | XF_C1, XF_C2, XF_C3, XF_C4, XF_CLRL, XF_LCLR, XF_RLCL, XF_LRLC | 8 | 20261107 |
| **Total** | — | **42** | — |

No condition appears twice; no condition is omitted; no main seed appears.

### 5.5 Overlap and output separation

| Campaign | JSON | Sidecar | Report | Spikes |
|---|---|---|---|---|
| Main | `p3_3c5_lane_encoding.json` | `p3_3c5_lane_encoding.sidecar.json` | `p3_3c5_lane_encoding_report.md` | `p3_3c5_lane_encoding_spikes.npz` |
| Pilot | `p3_3c5_lane_encoding_pilot.json` | `p3_3c5_lane_encoding_pilot.sidecar.json` | `p3_3c5_lane_encoding_pilot_report.md` | `p3_3c5_lane_encoding_pilot_spikes.npz` |
| Determinism | `p3_3c5_lane_encoding_determinism.json` | `p3_3c5_lane_encoding_determinism.sidecar.json` | none | none |

The three JSON names are distinct. The pilot and determinism paths never collide with the main paths; this is covered by `test_campaign_paths_do_not_collide`.

### 5.6 Campaign selection

- `run_campaign` receives the campaign as an explicit argument from `--campaign`.
- `--campaign` is restricted by argparse to `main`, `pilot`, `determinism`.
- `run_campaign("pilot")` uses `[pilot]` and never the main seeds.
- Determinism repeats are called only when `campaign == "main"`.
- `analyse_seed` and `classify_campaign` are skipped for pilot.
- There is no loop over campaigns, no fall-through and no post-run continuation.

### 5.7 Manifest summary

- 42 unique pilot instances on seed 20261107.
- 126 unique main instances over three main seeds.
- 18 determinism repeat instances, executed inside main and optionally re-executed by the standalone campaign.
- 186 distinct planned instances; 204 executions if the standalone determinism campaign is also run.
- No duplicates, no omissions, no cross-campaign seed overlap, no output collision.

---

## 6. Execution safeguards

### 6.1 Ten-point review

| # | Safeguard | Finding | Status |
|---|---|---|---|
| 1 | Explicit execution acknowledgement | `_require_execution_authorisation` requires `acknowledged` and, for main/pilot, `existing_tests_passed`; the CLI requires `--acknowledge-execution-authorised` | PASS |
| 2 | Campaign isolation | Pilot seeds are `[20261107]`; determinism is called only for main; the determinism campaign requires a main parent | PASS |
| 3 | Output overwrite protection | JSON and companions are versioned via `_resolve_output`; narrow orphan-spikes edge case (D4) | PASS WITH CAVEAT |
| 4 | Failure handling | Gate failures are recorded; an exception aborts without an artifact; no failure artifact or resume (D3) | PARTIAL |
| 5 | Incomplete-run handling | E1 requires all 42 runs `completed`; classification is `INVALID_EXECUTION` on any gate failure; exceptions abort before writing | PASS |
| 6 | Reproducibility metadata | Config, prereg, amendment and source hashes; git before/after; environment; mappings; schedule and spike digests | PASS |
| 7 | Checksum generation | Sidecar records `output_sha256` and `spike_times_sha256` | PASS |
| 8 | E9, E10, E16 evaluation | Implemented and unit-tested; E9/E16 evaluated on pilot and main; E10 real repeats on main only | IMPLEMENTED; REAL-RUN UNVERIFIED |
| 9 | Primary measurements, M6′, per-neuron Δ_C(i) | M6′ unchanged; `per_neuron_mean_hz` exposed for four CENTER neurons and rendered | IMPLEMENTED; SYNTHETICALLY TESTED |
| 10 | R150, R200, S10, S11 | R150/R200 membership verified; S10/S11 partial and disclosed | PASS WITH DISCLOSED LIMITATIONS |

### 6.2 Protocol immutability

The runner has no write path to the protocol, amendment record, configuration, tests or source files. It reads the configuration and asserts the preregistration and amendment hashes before execution. `git_state_stable` compares the repository state before and after a campaign, filtered to the results directory (E13). A pilot result cannot change the frozen protocol.

### 6.3 No automatic progression

The runner executes exactly one campaign per invocation. The pilot path does not call main or determinism. The main path calls determinism repeats as part of its own E10 evaluation, not as a separate campaign. The standalone determinism campaign requires a main artifact and an explicit invocation. There is no background task, thread, daemon or scheduled continuation.

### 6.4 Measurement safeguards

- **M6′.** `m6_prime` computes per-neuron rates on the 50 ms denominator, then the mean over the four CENTER neurons, then the mean over the three state-relative bins. It is unchanged.
- **Per-neuron Δ_C(i).** `subtract_measurement` returns `per_neuron_mean_hz`, the mean over three bins of each neuron's C1-minus-C2 rate. Four independent values in Hz; the 4 × 3 per-bin matrix is preserved.
- **R150.** Twelve closed-150 sequences; reference membership after excluding C3/C4 is 5 pred-LEFT, 2 pred-RIGHT, 3 none. Verified statically.
- **R200.** Six permutations; pred-LEFT `R200_RLC`, pred-RIGHT `R200_LRC`, none `R200_CLR`/`R200_CRL`. Verified statically.
- **E11.** Absent from `APPLICABLE_GATES`; no replacement exists; the configuration records it as withdrawn.
- **Inferential statistics.** No `p_value`, confidence interval, standard error or significance key is produced; `classify_campaign` records `inference: descriptive_only` and `significance_claim: false`.

### 6.5 Residual notes

- The pilot's E10 entry is `passed: true` with a `not_applicable_for_pilot` detail (D2). It is not determinism evidence.
- The pilot report's analysis tables are empty by design; the measurements are in the JSON `runs` block (D1).
- The `deviations` list is always empty; no deviation is ever appended (D3).

---

## 7. Real-run gate requirements

E11 is withdrawn and has no replacement. The table lists E1–E10 and E12–E16.

| Gate | Required evidence | Evaluation point | Failure consequence | Status |
|---|---|---|---|---|
| E1 | All 42 core, control and reference runs complete without numerical, capacity or validation failure | `run_gates` → `len(raw_runs) == 42` and every `completed` | `INVALID_EXECUTION` | Implemented; real-run unverified |
| E2 | Exactly 12 stimulated neurons; per-step nonzero counts 4 (step), 4/8 (crossfade), 0 (N0); no outside nonzero | `condition_gates` from `audit_input_current` | `INVALID_EXECUTION` | Implemented; statically and synthetically tested |
| E3 | Total sensory current 800 pA at every step, tolerance 1e-9 | `condition_gates` | `INVALID_EXECUTION` | Implemented; statically and synthetically tested |
| E4 | Constant-lane conditions activate only their intended group | `condition_gates` | `INVALID_EXECUTION` | Implemented; synthetically tested |
| E5 | N0 has no schedule, no stimulus, zero background/noise and zero spikes | `run_gates` E5 block | `INVALID_EXECUTION` | Implemented; synthetically tested |
| E6 | Lane group order is left, centre, right | `static_gates` | `INVALID_EXECUTION` | Implemented; statically tested |
| E7 | The three 4-neuron groups are disjoint and inside their annotation pools | `static_gates` | `INVALID_EXECUTION` | Implemented; statically tested |
| E8 | C2 is the reverse of C1 and C4 the reverse of C3 on the 50 ms grid; hashes differ; multisets match | `static_gates` | `INVALID_EXECUTION` | Implemented; statically tested |
| E9 | C3 and C4 spike trains are identical on `[0, 150)` ms | `run_gates` → `prefix_identical(C3, C4, 150.0)` | `INVALID_EXECUTION` | Implemented; synthetically tested; real-run unverified |
| E10 | 18 fresh-subprocess repeats over C1, C2, C3, C4, N0, K_C × 3 main seeds have identical schedule and spike digests | `determinism_repeats`; `run_gates` all `identical` | `INVALID_EXECUTION` | Implemented; synthetically tested; real-run unverified; not evidenced by the pilot |
| E12 | The existing test suite passes unchanged | External declaration `--existing-tests-passed` | `INVALID_EXECUTION` | SATISFIED by the recorded 916/3 run |
| E13 | Preregistration, amendment, protected and source hashes; git before/after stable outside the results directory | `static_gates` E13 and post-campaign `git_state_stable` | `INVALID_EXECUTION` | Implemented; shape-tested; real-run unverified |
| E14 | Outside activity is reported per condition | `e14_reported` | `INVALID_EXECUTION` | Implemented; synthetically tested |
| E15 | Half-open 50 ms bins cover `[0, 600)`; the 0.5 ms tail is excluded and reported | `static_gates` | `INVALID_EXECUTION` | Implemented; statically tested |
| E16 | C1 equals `T200_LC` and C2 equals `T200_RC` for `t < 400 ms` | `run_gates` → two `prefix_identical` checks | `INVALID_EXECUTION` | Implemented; synthetically tested; real-run unverified |

Pilot coverage: E1–E9, E12–E16 are evaluated on the single pilot seed. E10 cannot be evidenced by the pilot. E13's git comparison is performed at the end of the pilot campaign.

No gate is reported as real-run passed. The three gates that depend on actual spike trains (E9, E10, E16) remain **real-run unverified** until an authorised run.

---

## 8. Resource considerations

### 8.1 Execution model

- All runs are sequential. The campaign loops over seeds and conditions; determinism repeats spawn subprocesses one at a time and wait.
- No threads, multiprocessing, GPU, network or background process is used.
- The mapping is built once per seed and reused across conditions; encoders, scheduler and simulator are fresh per condition.

### 8.2 Memory

- Each simulator preallocates a spike recorder of `5,000,000 × (4 + 4)` bytes = **40,000,000 bytes (40 MB)**, released after each run (`del` plus `gc.collect()`).
- The campaign keeps a `store` of spike arrays for every condition across all seeds until the artifact is written: 42 arrays for the pilot and 126 arrays for main.
- The campaign also keeps per-condition measurement dictionaries for every seed in `runs_payload` and, for main, per-seed analyses.
- Exact peak memory is **not estimable** without execution. The structural fact is that main memory scales with 126 runs, not 42.

### 8.3 Storage

- Pilot: one JSON, one sidecar, one Markdown report, one compressed `.npz`.
- Main: the same four artifact types at the main names.
- Determinism: one JSON and one sidecar; no report and no spikes.
- The `.npz` stores times (`float64`) and indices (`int64`) per run before compression. File sizes depend on actual spike counts and are **not estimable** without execution.
- The JSON stores per-neuron per-bin counts plus per-lane aggregates for every condition; its size is also **not estimable** without execution.

### 8.4 Interruption and resume

- There is no checkpoint, no partial write and no resume. An interruption loses all in-memory results.
- A rerun starts from the beginning and, if a JSON already exists, writes a versioned `.v2` name.
- The main campaign holds its artifact until all seeds and all 18 repeats finish. A failure in the last repeat discards the 126 completed runs. This is an operational risk, not a scientific-validity defect.

### 8.5 Overwrite

- Existing JSON results are versioned, not overwritten. Companions follow the versioned name.
- An orphan `_spikes.npz` left by a crash can be overwritten (D4).
- The standalone determinism campaign reads the unversioned main JSON, which becomes a stale-parent risk after a versioned main rerun (D5).

### 8.6 Windows and environment

Determinable from code:

- Pure Python 3 with NumPy and PyYAML; no platform-specific extension is imported.
- `git` must be on `PATH` because `git_state()` invokes `git rev-parse` and `git status`.
- `sys.executable` is used for determinism subprocesses, so the interpreter must have the project dependencies.
- `tempfile.TemporaryDirectory` is used for single-run request and response files.
- All project paths are resolved from `Path(__file__).resolve().parents[2]`, so the working directory does not affect path resolution; the determinism subprocess explicitly runs with `cwd=PROJECT_ROOT`.
- No other platform restriction is visible in the code. No runtime or memory estimate is made.

---

## 9. Full operational execution plan

### 9.1 Preconditions for any campaign

1. A separate, written execution authorisation exists for the specific campaign.
2. The frozen hashes still match: preregistration `d6cdeea1…`, amendment `44096b3d…`, runner `c167adf7…`, configuration `21e4257d…`, tests `e8281529…`.
3. The existing suite result is current: 916 passed, 3 skipped, exit 0, with no source or test change since.
4. No `p3_3c5*` result artifact exists for the campaign, and no orphan `_spikes.npz` exists.
5. The repository state is recorded before the run.

The runner does not run the test suite. `--existing-tests-passed` is a declaration by the operator that precondition 3 holds.

### 9.2 Pilot (42 instances)

**Command** (from the repository root):

```
python experiments/phase_3c/p3_3c5_lane_encoding.py --execute --campaign pilot --acknowledge-execution-authorised --existing-tests-passed
```

**Acknowledgement mechanism.** `--acknowledge-execution-authorised` is required; without it `_require_execution_authorisation` raises `ExecutionNotAuthorised`. `--existing-tests-passed` is required for a pilot and is used as E12. The `--campaign` value must be exactly `pilot`.

**Expected outputs.**

- `experiments/phase_3c/results/p3_3c5_lane_encoding_pilot.json`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_pilot.sidecar.json`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_pilot_report.md`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_pilot_spikes.npz`

If the JSON name exists, all four receive `.v2` (or the next free version).

**Post-run checks.**

1. `runs` has exactly one seed key, `20261107`, with 42 condition keys.
2. `analysis == {}` and `campaign_outcome is None`; the report header reads `PILOT ONLY`.
3. `pilot.seed == 20261107`, `pilot.enters_main_result is False`, `pilot.threshold_tuning is False`.
4. `pilot.gate_failures == []` and every gate E1–E9, E12–E16 in `gates["20261107"]` passed. E10's `not_applicable_for_pilot` detail is noted, not treated as evidence.
5. The sidecar's `output_sha256` matches the JSON and `spike_times_sha256` matches the `.npz`.
6. The four pilot checks are evaluated post hoc per §4.6 and recorded.
7. The console log is preserved externally, in case a future failure must be reported.

### 9.3 Post-pilot decision gate

Before main: the four checks are recorded, the frozen hashes are re-verified, and the execution record states that pilot data do not enter the main result and that no threshold was tuned. If any check indicates a structural problem, the main campaign does not proceed; the issue is reported and a correction or amendment is requested.

### 9.4 Main (126 distinct instances plus 18 repeats)

**Command**:

```
python experiments/phase_3c/p3_3c5_lane_encoding.py --execute --campaign main --acknowledge-execution-authorised --existing-tests-passed
```

**Expected outputs.**

- `experiments/phase_3c/results/p3_3c5_lane_encoding.json`
- `experiments/phase_3c/results/p3_3c5_lane_encoding.sidecar.json`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_report.md`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_spikes.npz`

**Post-run checks.**

1. `runs` has seeds `20261104`, `20261105`, `20261106`, each with 42 condition keys.
2. `analysis` has the same three seeds; each contains `primary`, `dwell_replication`, `auxiliary`, `references`, `predicates` and per-neuron values.
3. `campaign_outcome.outcome` is not `INVALID_EXECUTION`; the classification trace and basis are present.
4. `determinism` has 18 entries across the three seeds, each `identical: true`.
5. All applicable gates passed for all three seeds; no seed is dropped for a negative or inconsistent outcome.
6. The sidecar's `output_sha256` and `spike_times_sha256` match their files.
7. The report contains the per-seed values, the reference predicates and the limitations, and uses the required descriptive wording.
8. E9 and E16 are read from the actual run pairs; no real-run gate result is assumed in advance.

### 9.5 Standalone determinism (18 re-executions, optional)

**Command**:

```
python experiments/phase_3c/p3_3c5_lane_encoding.py --execute --campaign determinism --acknowledge-execution-authorised
```

`--existing-tests-passed` is not required for this campaign and is not checked.

**Dependency.** This campaign requires `experiments/phase_3c/results/p3_3c5_lane_encoding.json` to exist and to contain `campaign == "main"`. It cannot create parent runs. It must run after a successful main campaign.

**Expected outputs.**

- `experiments/phase_3c/results/p3_3c5_lane_encoding_determinism.json`
- `experiments/phase_3c/results/p3_3c5_lane_encoding_determinism.sidecar.json`

**Equality checks.**

- `n_instances == 18`.
- `E10.passed is true`.
- For each seed and each of the six conditions, `parent_spike_digest == repeat_spike_digest` and `parent_schedule_digest == repeat_schedule_digest`.
- `parent_result` points to the main JSON actually used.

**Caveat (D5).** Do not run this after a versioned main rerun without handling the older base `p3_3c5_lane_encoding.json`. The campaign reads the base path, not the latest version. On a clean first run, the main JSON is the base file and the check is safe.

### 9.6 Dependencies

```
frozen hashes + E12
        |
        v
   pilot (42)  ->  post-hoc four-check record
        |
        v
   main (126 + 18 internal repeats)
        |
        v
   standalone determinism (18, optional; duplicate verification)
```

The preregistration permits no main run before steps 1–4 of §14.5. The pilot precedes main; main precedes the standalone determinism check.

### 9.7 Do not do

- Do not run main before the pilot and the post-pilot record.
- Do not use pilot data in the main result.
- Do not tune any threshold after the pilot.
- Do not delete, rename or overwrite an existing result to force a base-name write.
- Do not interpret E10's pilot entry as determinism evidence.
- Do not report the optional §9.5 residual; it is not implemented.

---

## 10. Scientific limitations

1. **Descriptive, not inferential.** No p-value, confidence interval, standard error or significance claim is made. Reference sets are deterministic and small.
2. **Three seeds, four neurons per group.** No population inference or generalisation. Exact per-seed values and ranges are reported; no standard deviation.
3. **One-hot lane input.** Lane identity is trivial at the input. The experiment tests the spiking readout's history dependence, not a fly lane code.
4. **Confounded references.** Predecessor identity is confounded with annotation pool; the CENTER pool is small; R200 is one value against one value; P2 and P3 have dwell, absolute-time and route confounds.
5. **No causal isolation of recurrent input.** Outside activity is measured, not subtracted; there is no synapse-block control. E16 is a correctness check, not independent evidence.
6. **Model scope.** No adaptation or short-term plasticity; synapses and weights are computational. Structural data are not physiological.
7. **S10 partial.** First-spike latency, peak rate and peak bin are recorded per condition. The pre-onset mean+SD threshold and the post-peak decay measure are not implemented.
8. **S11 partial.** Per-seed signs, values and ranges are recorded. Per-lane rank correlations are not implemented.
9. **Pilot-check ambiguity.** Runtime and metric computability have no numeric criteria in the frozen documents; reference degeneracy has an exact predicate but cannot be classified across seeds with a one-seed pilot. This report does not invent criteria.
10. **No real-run evidence.** E9, E10, E16 and the campaign-level behaviour are implemented and tested on synthetic data only. Determinism is not robustness.
11. **Failure preservation.** A failed attempt is not preserved as an artifact (D3); any failure must be reported from external logs.
12. **Pilot report.** The rendered pilot report has empty analysis tables; the pilot evidence is in the JSON `runs` block (D1).

---

## 11. Outstanding blockers

### 11.1 Classification

| Severity | Issues |
|---|---|
| BLOCKER | none |
| MAJOR | D1 (pilot checks not evaluated), D3 (failed attempts not preserved), D5 (determinism parent path after a rerun) |
| MINOR | D2 (pilot E10 representation), D4 (orphan spikes), D7 (capacity field), D9 (`--execute-single` E12) |
| ACCEPTABLE LIMITATION | D6 (186 vs 204 accounting), D8 (spike-time layout), D10 (stale audit row) |

### 11.2 Why none is a blocker

- The pilot's scientific validity does not depend on the runner emitting a verdict; the necessary measurements are recorded, and the checks can be evaluated and recorded before main.
- Failure preservation affects only the record of a failed attempt, not the validity of a successful one; external log capture keeps the record honest.
- The determinism parent path is safe on a clean first run. It becomes unsafe only after a versioned main rerun, which the operational plan avoids.

### 11.3 What would create a blocker

- An authorising decision that requires the runner itself to certify the four pilot checks, with no post-hoc step allowed.
- A need to rerun main after a base artifact already exists without correcting D5.
- Any change to a frozen hash.
- Any requirement that failed attempts be preserved automatically with no operational mitigation.

### 11.4 Campaign readiness conditions

- **Pilot:** ready, conditional on the authorisation accepting D1, D3, D4 and the post-hoc record.
- **Main:** ready after a successful pilot, the post-hoc record, and re-verification of the frozen hashes.
- **Determinism:** ready after a successful main run, on the base-named main artifact; conditional on D5 handling for any rerun.

---

## 12. Final recommendation

**Verdict: READY WITH ACCEPTABLE LIMITATIONS.**

The frozen implementation supports a scientifically valid 42-instance pilot and, after the pilot, a scientifically valid 126-instance main campaign with 18 internal determinism repeats. The campaign manifests reconcile exactly to 186 distinct instances. The execution guards, campaign isolation, output separation and measurement safeguards are intact. The limitations are documented and do not silently alter the protocol.

### Final decision gate

1. **Is the 42-instance pilot ready?** **Yes, conditionally.** It is well-defined, isolated and guarded. The authorisation must accept that the four pilot checks are evaluated post hoc and recorded before main, and that failure logs are captured externally.
2. **Is the 126-instance main campaign ready?** **Yes, after the pilot.** It requires a successful pilot, the post-hoc four-check record, and a hash re-verification. It executes 126 distinct runs plus 18 determinism repeats.
3. **Are the 18 determinism repeats ready?** **Yes, after main, on a clean base artifact.** The repeats are already executed inside main as E10. The standalone campaign is an optional duplicate verification and is unsafe only after a versioned main rerun (D5).
4. **Is any frozen implementation correction genuinely necessary?** **No for a clean first run.** Recommended, but not required for this cycle: add pilot-check results to the artifact; preserve failed attempts; resolve the determinism parent path through the versioned main artifact.
5. **What remains before scientific completion?** A separate pilot authorisation; the pilot run; the post-hoc four-check record; hash re-verification; a separate main authorisation; the main run; the optional standalone determinism check; analysis and the scientific report, including negative results and limitations.

**No campaign has been executed.** This report does not authorise execution. A separate, explicit execution authorisation is required, first for the pilot and later for the main campaign.

---

## Appendix A — Evidence basis

Read-only inspection of:

- `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` (sha256 `d6cdeea1…`)
- `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` (`44096b3d…`)
- `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` (`db9fe075…`)
- `docs/P3_3C5_IMPLEMENTATION_FREEZE_RECORD.md` (`7528ed55…`)
- `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` (`f7ea9131…`)
- `configs/p3_3c5_lane_encoding.yaml` (`21e4257d…`)
- `experiments/phase_3c/p3_3c5_lane_encoding.py` (`c167adf7…`)
- `tests/test_p3_3c5_lane_encoding.py` (`e8281529…`)

The configuration was parsed to enumerate the 42 conditions; hashes were recomputed; the working tree was compared before and after with `git status --short`. The runner was not invoked, the test suite was not re-run, and no simulation was performed.
