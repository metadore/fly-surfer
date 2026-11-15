# P3-3C.5 — Authorized 42-Instance Pilot: Execution Report

Generated: 2026-11-15
Campaign executed: **pilot only** (seed `20261107`, 42 instances)
Repository: `FLY-SURFER`, branch `main`, HEAD `62a64309cadc0db7353c856607cee5369993bd65`

> **Final pilot verdict: FAIL (execution valid; reference non-degeneracy check failed).**
> The 42-instance pilot executed cleanly and produced valid, hash-consistent artifacts, but the
> primary CENTER readout is **fully degenerate** on the pilot seed: every CENTER metric is
> 26.667 Hz and Δ_C(C1,C2) = 0.000 Hz. The 126-instance main campaign is **not** authorized by
> this report and was **not** executed. The 18-instance determinism campaign was **not** executed.

---

## 1. Authorization scope

The pilot was executed under an explicit, single-purpose authorization for 15 November 2026:

| Item | Authorized value | Executed |
|---|---|---|
| Campaign | P3-3C.5 pilot | pilot |
| Instances | exactly 42 | 42 |
| Seed | `20261107` | `20261107` |
| Determinism repeats | 0 | 0 |
| Main instances | 0 | 0 |
| Main campaign (126) | NOT AUTHORIZED | not run |
| Standalone determinism (18) | NOT AUTHORIZED | not run |

Pilot data do not enter the main result (`pilot.enters_main_result = false`,
`pilot_enters_main_result = false` in the frozen config).

## 2. Preflight and hash verification

Preflight was completed and recorded before launch.

- Git: branch `main`, HEAD `62a64309cadc0db7353c856607cee5369993bd65`, 226 `git status` entries, 0 staged.
- Disk on `C:`: 20 GB available, 96% used.
- Python 3.13.14; NumPy 2.3.4; platform `Windows-11-10.0.26200-SP0`.
- No pre-existing `p3_3c5*` result outputs were present in `experiments/phase_3c/results/`.
- The runner CLI was inspected (`--help`) and the pilot plan was confirmed from
  `plan_campaign(cfg, "pilot")`: seed `[20261107]`, 42 conditions, 42 distinct instances,
  0 determinism repeats, no parent-artifact requirement.
- The selected command cannot trigger the main or determinism campaigns (see §3).

Six frozen SHA-256 hashes were verified before execution and again after execution. All matched
on both occasions:

| Artifact | SHA-256 | Status |
|---|---|---|
| Preregistration | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` | MATCH |
| Amendment record | `44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd` | MATCH |
| Configuration | `21e4257d7022a7333fa84bef37df489e25e31b016080dfcd64ef0029498df638` | MATCH |
| Runner | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` | MATCH |
| Test suite | `e8281529f31a208709bd02d3ec59ef528c72c4fd7f5e9e034df92ade16995f73` | MATCH |
| Implementation freeze record | `7528ed55c576ed12a8df19fac96ac895897d268b4a04841081c119c8303ba835` | MATCH |

The superseded preregistration hash `1daa2439…` was **not** restored or used.

## 3. Exact command and execution window

```
python experiments/phase_3c/p3_3c5_lane_encoding.py --execute --campaign pilot --acknowledge-execution-authorised --existing-tests-passed
```

- UTC start: `2026-11-15T05:01:41Z`
- UTC end: `2026-11-15T05:05:14Z`
- Process exit code: `0`
- Runner-reported `runtime_s`: `211.3285`

`--campaign pilot` selects `seeds["pilot"]` only, skips per-seed analysis, and skips determinism
repeats (those require `campaign == "main"`). The `_require_execution_authorisation` guard
required `--acknowledge-execution-authorised` and an `--existing-tests-passed` declaration; both
were supplied as recorded in §2 and the frozen implementation freeze record (E12 evidence:
916 passed, 3 skipped, 104.32 s, exit 0).

## 4. Planned vs actual counts

| Metric | Planned | Actual |
|---|---|---|
| Pilot instances | 42 | **42** |
| Completed | 42 | **42** (`runs["20261107"]` has 42 entries; E1 detail `n_conditions = 42`) |
| Failed | 0 | **0** |
| Interrupted | 0 | **0** |
| Main instances | 0 | **0** |
| Determinism repeats | 0 | **0** |
| Deviations recorded by runner | 0 | **0** (`deviations = []`) |

The top-level pilot payload does not populate a scalar `n_instances` field (it is `null`); the
actual count is established by the 42 run entries and gate E1. This is an artifact-format
observation, not a count discrepancy (§11).

## 5. Per-instance results

All 42 seeded instances completed and are present. Per-condition spike totals and CENTER metric:

| # | Condition | n_spikes | CENTER metric |
|---|---|---|---|
| 1 | C1 | 72 | 26.667 Hz |
| 2 | C2 | 72 | 26.667 Hz |
| 3 | C3 | 64 | 26.667 Hz |
| 4 | C4 | 64 | 26.667 Hz |
| 5 | K_C | 72 | 26.667 Hz |
| 6 | K_L | 72 | n/a (no CENTER block) |
| 7 | K_R | 72 | n/a (no CENTER block) |
| 8 | N0 | 0 | n/a (no CENTER block) |
| 9 | R150_CLLR | 68 | 26.667 Hz |
| 10 | R150_CLRL | 64 | 26.667 Hz |
| 11 | R150_CRLL | 68 | 26.667 Hz |
| 12 | R150_LCLR | 64 | 26.667 Hz |
| 13 | R150_LLCR | 68 | 26.667 Hz |
| 14 | R150_LLRC | 68 | 26.667 Hz |
| 15 | R150_LRLC | 64 | 26.667 Hz |
| 16 | R150_RCLL | 68 | 26.667 Hz |
| 17 | R150_RLCL | 64 | 26.667 Hz |
| 18 | R150_RLLC | 68 | 26.667 Hz |
| 19 | R200_CLR | 72 | 26.667 Hz |
| 20 | R200_CRL | 72 | 26.667 Hz |
| 21 | R200_LRC | 72 | 26.667 Hz |
| 22 | R200_RLC | 72 | 26.667 Hz |
| 23 | T150_CL | 72 | 26.667 Hz |
| 24 | T150_CR | 72 | 26.667 Hz |
| 25 | T150_LC | 72 | 26.667 Hz |
| 26 | T150_LR | 72 | n/a (no CENTER block) |
| 27 | T150_RC | 72 | 26.667 Hz |
| 28 | T150_RL | 72 | n/a (no CENTER block) |
| 29 | T200_CL | 72 | 26.667 Hz |
| 30 | T200_CR | 72 | 26.667 Hz |
| 31 | T200_LC | 72 | 26.667 Hz |
| 32 | T200_LR | 72 | n/a (no CENTER block) |
| 33 | T200_RC | 72 | 26.667 Hz |
| 34 | T200_RL | 72 | n/a (no CENTER block) |
| 35 | XF_C1 | 64 | 20.000 Hz |
| 36 | XF_C2 | 64 | 20.000 Hz |
| 37 | XF_C3 | 60 | 20.000 Hz |
| 38 | XF_C4 | 60 | 20.000 Hz |
| 39 | XF_CLRL | 60 | 26.667 Hz |
| 40 | XF_LCLR | 60 | 20.000 Hz |
| 41 | XF_LRLC | 60 | 20.000 Hz |
| 42 | XF_RLCL | 60 | 20.000 Hz |

Outside spikes (activity outside the 12 stimulated neurons) totalled **0** across all 42 runs.

## 6. Gate results

All 15 applicable gates passed for seed `20261107`; no gate failed.

| Gate | Passed | Detail (abridged) |
|---|---|---|
| E1 | yes | `n_conditions = 42` |
| E2 | yes | all conditions lane-only; per-step nonzero as configured |
| E3 | yes | all conditions |
| E4 | yes | all conditions |
| E5 | yes | `stimulus = none`, no schedule, `n_spikes = 0` for N0 |
| E6 | yes | lane order left, center, right |
| E7 | yes | 12 disjoint neurons; pools visual_left/center/right |
| E8 | yes | C2 = reverse(C1); C4 = reverse(C3) |
| E9 | yes | C3/C4 prefix identical for `[0, 150) ms` |
| E10 | yes | `{"not_applicable_for_pilot": true}` — **not** an experimental determinism result |
| E12 | yes | existing-tests-passed declared |
| E13 | yes | prereg/config hashes match |
| E14 | yes | outside activity reported separately; 42 conditions |
| E15 | yes | 12 half-open bins + 0.5 ms tail |
| E16 | yes | C1 ≡ T200_LC and C2 ≡ T200_RC before 400 ms |

**E10 must not be read as evidence of determinism from the pilot.** The pilot ran zero repeats;
the gate is marked not applicable.

## 7. Four pilot checks — independent evaluation

The frozen runner does not mechanically evaluate the four checks for the pilot: it records raw
measurements and emits `analysis = {}`. The verdicts below were computed independently from the
recorded pilot measurements.

| Check | Verdict | Evidence |
|---|---|---|
| Runtime | **PASS** | 211.33 s total; per-run wall 2.226–7.286 s (sum 150.86 s). No numeric threshold is defined in the protocol; operationally viable. |
| Capacity | **PASS** | Max `n_spikes = 72` (T150_CL) versus capacity 5,000,000; no capacity/numerical/validation failure in any run. |
| Metric computability | **PASS** | M6′ and per-neuron Δ_C(i) computable; 4×3 CENTER counts, rates and `m6_prime` present for all 35 CENTER-bearing conditions; `new_lane_state_relative` present for all 12 T200/T150 conditions. Seven conditions lack CENTER by design (K_L, K_R, N0, T200_LR, T200_RL, T150_LR, T150_RL). |
| Reference non-degeneracy | **FAIL** | R200 pred-LEFT (`R200_RLC`) = 26.6667 Hz equals pred-RIGHT (`R200_LRC`) = 26.6667 Hz; both "none" values = 26.6667 Hz. R150 pred-left (5 values) all 26.6667 Hz (range width 0.0); pred-right (2 values) all 26.6667 Hz (range width 0.0). Degenerate predicate = **true** on this seed. |

### 7.1 Evidence that the CENTER readout is condition-invariant

- Δ_C(C1,C2) = **0.0000 Hz**; per-neuron Δ_C(i) = `[0, 0, 0, 0]`.
- 28 of the 35 CENTER-bearing conditions share identical CENTER counts `[[1,2,1]×4]`
  (20/40/20 Hz); the other 7 (XF_C1, XF_C2, XF_C3, XF_C4, XF_LCLR, XF_RLCL, XF_LRLC) share
  `[[0,2,1]×4]` (0/40/20 Hz).
- Each lane's four neurons fire a stereotyped `4, 8, 4, 8` burst during that lane's own block,
  independent of position or preceding context (e.g. CENTER absolute bins for C1, C2, R200_RLC
  and R200_LRC are all `[0,0,0,0,4,8,4,8,0,0,0,0]` and `[0,0,0,0,0,0,0,0,4,8,4,8]` at the
  respective onsets).
- Outside spikes = 0 in every run: the only activity is in the 12 directly stimulated neurons,
  with no cross-lane recruitment.

Interpretation (descriptive, single seed): under the configured lane-only regime, the CENTER
firing readout on this mapping behaves as a fixed function of its own 200 ms (or 150 ms) input
block, so predecessor/sequence identity does not modulate it. This is exactly the outcome class
the frozen protocol anticipates as `INCONCLUSIVE_REFERENCE_DEGENERATE`.

## 8. Failures, deviations and interruptions

- Failed instances: **0**.
- Interrupted instances: **0**.
- Runner-recorded deviations: **0** (`deviations = []`).
- No instance was silently retried, replaced or discarded.
- No execution guard failed; no campaign boundary was crossed; no output was overwritten.
- No protocol discrepancy requiring a STOP occurred during execution.

## 9. Output artifacts and SHA-256

All artifacts are under `experiments/phase_3c/results/` and are readable.

| Artifact | SHA-256 |
|---|---|
| `p3_3c5_lane_encoding_pilot.json` | `d3d9bd2de220bad0248e39f1b1ef82de94f92780432da4614b4d0c1358db40bd` |
| `p3_3c5_lane_encoding_pilot.sidecar.json` | `4eec36d22cda59df37bb50757421e4dec2e710968db1ec18cedecd131732f983` |
| `p3_3c5_lane_encoding_pilot_report.md` | `5fbb51306869b6de37d36798bcc437a327c888946d0818b12893da80d1e6384f` |
| `p3_3c5_lane_encoding_pilot_spikes.npz` | `1397be0779609dace64307bb58230f0f429794cc65d7ed2a121be04efb319bc3` |

Sidecar cross-checks:

- `sidecar.output_sha256` = actual JSON hash → MATCH.
- `sidecar.spike_times_sha256` = actual `.npz` hash → MATCH.
- Both artifacts belong to the same campaign (`campaign = pilot`, seed `20261107`).
- The `.npz` contains 84 arrays (42 conditions × times/indices).

## 10. Frozen-artifact integrity and repository state

- The six frozen hashes are unchanged after execution (table in §2).
- `git status --short`: 226 entries before, 230 after. The only additions are the four pilot
  artifacts above; no pre-existing entry was modified, removed or overwritten.
- HEAD and branch are unchanged.
- No `p3_3c5_lane_encoding.json` (main result) and no determinism artifacts were created.
- The protected hashes embedded in the pilot JSON (`README.md`, `connectome.npz`) match their
  expected values.
- Nothing was staged, committed, pushed, reset, cleaned, stashed, checked out or deleted.

## 11. Artifact and metadata observations (non-blocking, not repaired)

These are factual inconsistencies or format details in the frozen output. They were **not**
silently repaired because the runner and configuration are frozen.

1. **Stale embedded protocol status.** The pilot JSON embeds
   `protocol.status = "IMPLEMENTATION_ONLY_EXECUTION_NOT_AUTHORISED"` even though this campaign
   executed under explicit authorization. The field is informational and does not affect the
   measurements or gates.
2. **No scalar `n_instances` for pilot.** The top-level `n_instances` is `null`; the actual count
   is established by the 42 run entries and E1.
3. **Embedded `git.after` shows 226, external shows 230.** The runner snapshots `git.after`
   before writing the four output files, so its embedded count predates those writes. The
   external post-run check correctly sees 230.
4. **No per-run `completed` boolean.** Completion is implied by the presence of the measurement
   and by E1; the pilot payload does not store a per-run completion flag.
5. **Pilot analysis is empty by design.** `analysis = {}`, `campaign_outcome = null`; reference
   predicates are not computed for the pilot. The four checks in §7 are therefore an independent
   post-hoc evaluation, not a runner-emitted verdict.

## 12. What this pilot does and does not establish

**Establishes (for the pilot seed only):**

- The full 42-instance pilot runs end-to-end within the frozen implementation, with all
  applicable gates passing and hash-consistent artifacts.
- Runtime and capacity are operationally adequate.
- The planned primary and per-neuron metrics are numerically computable.
- On seed `20261107`, the CENTER readout is condition-invariant and the R200/R150 reference is
  fully degenerate; Δ_C(C1,C2) = 0 exactly.

**Does not establish:**

- It does **not** establish that the three main seeds (`20261104/5/6`) are degenerate. The
  protocol's degeneracy class uses a ≥2/3 rule across main seeds, and the pilot is excluded from
  the main result. A single pilot seed cannot assign the main campaign's outcome class.
- It does **not** provide determinism evidence (E10 not applicable; zero repeats).
- It does **not** test robustness, population inference, or biology; these are outside the
  protocol's claims.
- It does **not** authorize the main or determinism campaigns.

## 13. Final pilot verdict

**FAIL.**

Rationale: execution integrity passed (42/42, exit 0, gates pass, hashes consistent), but the
protocol's pilot step requires verifying *reference non-degeneracy*, and that check fails
unambiguously on the pilot seed. Three of four checks pass; the failed check directly undermines
the primary contrast (Δ_C = 0 exactly), so the pilot cannot be recorded as a pass or as a
pass-with-limitations.

## 14. Decision gate: 126-instance main campaign

The main campaign was **not** executed and remains unauthorized.

| Question | Answer |
|---|---|
| Is the pilot execution complete and valid? | Yes — 42/42, exit 0, gates pass, hashes consistent. |
| Did all four pilot checks pass? | No — reference non-degeneracy failed. |
| Is the main campaign authorized to proceed on the basis of this pilot? | **No.** The pilot did not clear its reference non-degeneracy gate. |
| Does the pilot prove the main seeds are degenerate? | No — one seed cannot decide a ≥2/3 main-seed rule. |
| Is the standalone determinism campaign ready? | Not authorized; requires its own authorization and preflight. |

Recommended next step before any main authorization (decision for the protocol owner, not taken
here): determine whether the observed condition-invariance is specific to the `20261107` mapping
or is a regime-level property of the frozen 200 pA lane-only configuration. Because the frozen
runner, config and protocol cannot be changed without a separate authorized decision, this is a
protocol-level judgment. Proceeding to main without that determination would risk producing a
campaign whose primary analysis is classified `INCONCLUSIVE_REFERENCE_DEGENERATE`.

Operational notes for any future authorized run: the consolidated readiness report's D5 remains
relevant (the standalone determinism runner reads the unversioned `JSON_PATH`, which is unsafe
after a versioned main rerun); the E12 declaration and `--acknowledge-execution-authorised` remain
required.

---

## Appendix A — External audit record

Independent execution log (outside the repository):
`C:\Users\Hp\Documents\Qoder\2026-11-03\0b165e9c\p3_3c5_pilot_execution.log`

Pre/post `git status` snapshots:
`C:\Users\Hp\Documents\Qoder\2026-11-03\0b165e9c\pilot_status_before.txt`,
`C:\Users\Hp\Documents\Qoder\2026-11-03\0b165e9c\pilot_status_after.txt`

## Appendix B — Confirmation of campaign boundaries

- Main instances executed: **0**.
- Determinism repeats executed: **0**.
- Main result artifact created: **no**.
- Determinism artifacts created: **no**.
- Only pilot artifacts were added to the working tree.
