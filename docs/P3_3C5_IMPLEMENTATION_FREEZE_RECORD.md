# P3-3C.5 — Implementation Freeze Record

**Status: IMPLEMENTATION FROZEN — EXPERIMENT EXECUTION NOT AUTHORISED.**

**Freeze date.** 2026-11-14 (UTC).

**Scope.** The P3-3C.5 implementation set: runner, configuration, test suite and
implementation compliance audit, together with the E12 full-suite evidence. This
record documents integrity verification only. It does not execute, analyse or
authorise the experiment, and it is not a scientific report.

This is a separate record from `docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md`
(the earlier protocol freeze) and from both implementation audits. Neither audit
is modified or overwritten.

---

## 1. Authoritative protocol

| Document | SHA-256 | Role |
|---|---|---|
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` | Authoritative frozen protocol as amended |
| `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` | `44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd` | Approved amendment; E11 withdrawn 2026-11-14 |

The pre-amendment hash `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857`
recorded in `docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md` is historical and
superseded. It is not restored. The amended preregistration takes precedence.

---

## 2. Frozen implementation set

All hashes below were recomputed from the working tree on 2026-11-14 and match
the expected values exactly.

| File | SHA-256 | Role |
|---|---|---|
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` | Runner, measurement, gates, reporting, execution guards (2,850 lines) |
| `configs/p3_3c5_lane_encoding.yaml` | `21e4257d7022a7333fa84bef37df489e25e31b016080dfcd64ef0029498df638` | Frozen configuration (533 lines, 42 conditions) |
| `tests/test_p3_3c5_lane_encoding.py` | `e8281529f31a208709bd02d3ec59ef528c72c4fd7f5e9e034df92ade16995f73` | Non-simulation test suite (1,392 lines) |
| `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` | `db9fe075da5d5ace3cd6f183e7806dcab114d91c95a1e2470b8771d2eeed7f95` | Compliance audit, revision 2 |

Protected files verified unchanged:

| File | SHA-256 |
|---|---|
| `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` (historical E11-blocker record) | `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194` |
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |

Any later edit to a frozen file invalidates this record and requires a re-audit
and a new freeze record. This record is not itself part of the hash set, because
a file cannot contain its own hash.

---

## 3. E12 test evidence

E12 ("The existing test suite passes unchanged") was executed once against the
complete pre-existing suite at this frozen implementation state.

**Command (repository-established; `README.md:57`, `pytest.ini`):**

```
python -m pytest -q
```

| Metric | Value |
|---|---|
| Collected | 919 |
| Passed | 916 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 3 |
| Deselected | 0 |
| Duration | 104.32 s (0:01:44) |
| Exit code | 0 |
| Warnings | None reported |

The three skips are the intentional execution-boundary tests in
`tests/test_p3_3c5_lane_encoding.py`, each marked
`NOT RUN — EXECUTION NOT AUTHORISED`:

- `test_main_campaign_end_to_end_not_run` — requires 126 main instances.
- `test_pilot_campaign_end_to_end_not_run` — requires 42 pilot instances.
- `test_determinism_repeats_end_to_end_not_run` — requires 18 determinism repeats.

No test was modified, excluded or deselected to obtain this result. Inspection
confirmed that no file outside `tests/test_p3_3c5_lane_encoding.py` references the
runner, and that every non-skipped execution entry point in that file asserts
`ExecutionNotAuthorised` or `FileNotFoundError` before any simulation. No GPU,
network access, thread or background process is used by the suite. Neither the
repository status (224 pre-existing entries, unchanged) nor any protected hash
changed across the run.

**Result: E12 is SATISFIED.**

Reconciliation with the compliance audit, which is left unmodified at its frozen
hash: `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` §9 lists E12 as "full
pre-existing suite not run", and §12.2 limitation 2 describes E12 as partial.
Those statements were correct when the audit was written, before the E12 run.
They are superseded by this section. Updating the audit would have changed its
hash and contradicted §2, so the supersession is recorded here instead.

---

## 4. Requirement compliance summary

Statuses use the audit's taxonomy: implemented, statically verified,
synthetically tested, real-run unverified. No requirement is real-run verified.

| Requirement | Confirmation | Status |
|---|---|---|
| Per-neuron `Δ_C(i)` = `(1/3) Σ_s [r_C1(i,s) − r_C2(i,s)]` (§7.1 lines 502–503; §13.2 line 851) | Implemented in `subtract_measurement` as `per_neuron_mean_hz`; four independent values; Hz; exposed in `analysis["primary"]` and rendered as four rows | Implemented; synthetically tested; real-run unverified |
| M6′ unchanged | `m6_prime` unchanged; aggregate `value_hz` unchanged; no replacement metric | Implemented; synthetically tested |
| R150 | 12 total sequences; 10 reference sequences after excluding C3/C4; pred-LEFT 5, pred-RIGHT 2, none 3 | Statically verified |
| R200 | Six permutations; pred-LEFT `R L C`, pred-RIGHT `L R C`, none `C L R`/`C R L`; strict `SEPARATED_200` | Statically verified |
| E11 withdrawn | `APPLICABLE_GATES` = E1–E10, E12–E16; E11 absent | Verified |
| No E11′ replacement | No `E11_prime`/`E11′` code path or gate; amendment record states no replacement | Verified |
| E12 | Full existing suite passes unchanged (see §3) | **SATISFIED** |
| E9, E10, E16 | Implemented and unit-tested on synthetic data; real-run evaluation requires authorised execution | Real-run unverified |
| S10, S11 | Partial: S10 lacks the pre-onset mean+SD threshold and decay measure; S11 lacks per-lane rank correlations | Disclosed limitations |
| No inferential statistics | Analysis payload contains no `p_value`, `confidence_interval`, `standard_error` or `significance` key | Verified |
| No unsupported scientific claims | No history effect, lane separation or negative result is claimed anywhere in the frozen documentation | Verified |

The analytical validation performed for this record was read-only inspection of
the preregistration, amendment record, compliance audit and configuration. No
implementation code, test, configuration or audit was modified.

---

## 5. Known limitations

1. **No real-run evidence.** E9 (C3/C4 prefix identity), E10 (subprocess repeat
   equality) and E16 (C1/`L→C`, C2/`R→C` causal decomposition) remain
   real-run unverified; they can only be evaluated during authorised execution.
2. **E12 evidence is one snapshot.** It certifies the full existing suite at this
   frozen state. Any later change to source, configuration or tests invalidates
   it.
3. **Secondary measures are partial.** S10 and S11 are incomplete as described
   in §4 and in the compliance audit; nothing partial is reported as computed.
4. **Per-neuron scalar is synthetically tested only.** Its formula, direction,
   bin averaging, units and independence are verified on synthetic arrays; its
   behaviour on real spike trains is real-run unverified.
5. **No scientific result exists.** This record says nothing about whether a
   history effect, lane separation or a negative result will occur.
6. **Hashes are snapshots.** The hashes in §2 identify the frozen implementation
   only at freeze time.
7. **Pre-existing working-tree changes.** Unrelated Phase 3B/3C/4/5/6
   modifications and untracked files predate this task. They were left untouched
   and were not audited.
8. **Freeze is not robustness.** Determinism repeats are defined but not
   executed; reproducibility of the same computation is not scientific
   robustness.

The compliance audit's verdict of **IMPLEMENTATION PASS WITH LIMITATIONS**
remains in force. This freeze record does not upgrade that verdict and does not
close the real-run limitations.

---

## 6. Implementation freeze versus execution authorisation

- **Implementation frozen.** The four hashed files in §2 are the frozen
  implementation. They may not be edited without a re-audit and a new freeze
  record.
- **Execution NOT authorised.** No main, pilot or determinism instance may start.
  This record is not an execution authorisation and cannot be cited as one.
- **E12 is a precondition, not a permission.** Passing the existing suite
  satisfies E12; it does not authorise a campaign.
- **Real-run gates remain open.** E9, E10 and E16 must be evaluated during
  execution under a separate explicit authorisation; a failure invalidates the
  affected run, which must be reported rather than imputed.
- **No result artifact exists.** `experiments/phase_3c/results/` contains no
  `p3_3c5*` file. The planned campaign (126 main + 18 determinism + 42 pilot =
  186 instances) remains entirely unexecuted.

---

## 7. Repository state at freeze time

- HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`).
- Working tree: 224 pre-existing modified/untracked entries, unchanged by this
  task. No new repository modification was introduced except this record.
- Staged changes: 0. Commits: 0. Pushes: 0. Resets/cleans/stashes/checkouts: 0.
- Deletions: 0.
- `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` remains at
  `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194`.
- `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` remains at
  `db9fe075da5d5ace3cd6f183e7806dcab114d91c95a1e2470b8771d2eeed7f95`.
- `experiments/phase_3c/results/`: no `p3_3c5*` artifact.
- Experiment simulations executed for this task: **0**.

---

## 8. Integrity statement

- Preregistration, amendment record, implementation code, tests, configuration,
  README and connectome were not modified; their hashes match §1 and §2.
- Both existing audit documents were not modified or overwritten.
- No Phase 4/BANC work was modified.
- No file was staged, committed, pushed, reset, cleaned, stashed or deleted.
- All pre-existing working-tree changes were preserved.
- The only file created by this task is this freeze record.
- No experiment was executed and no result was generated.

**P3-3C.5 remains unexecuted.** The correct state is: implementation frozen and
E12 satisfied, awaiting a separate explicit execution authorisation.
