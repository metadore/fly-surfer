# P3-3C.5 — Protocol Amendment Record

**Status: RECORDED AMENDMENT — PROTOCOL AMENDED; NOT EXECUTED; IMPLEMENTATION AND EXECUTION NOT AUTHORISED.**

**Amendment date.** 2026-11-14.

**Authority.** The user explicitly approved the amendment decisions recorded in
§2 on 2026-11-14. This record documents the resulting edits to the frozen
preregistration. It does not implement, configure, execute or analyse P3-3C.5.

---

## 1. Protocol versions

| Version | Document | SHA-256 | Lines | Status |
|---|---|---|---|---|
| Original frozen protocol | `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857` | 1,127 | superseded by this amendment |
| **Amended protocol (operative)** | `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` | 1,177 | **operative** |
| Amendment proposal | `docs/P3_3C5_PROTOCOL_AMENDMENT_PROPOSAL.md` | `7e6d921a73ffc6ea7f09512eb95d06b628c0e434fe642cbdc12028e79cc17c90` | 688 | historical, unchanged |
| Freeze record | `docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md` | `99ac601534876f3d9e26a2a123d2fd7733a3c62338ee81c9c070a409f75d06fd` | 231 | historical, unchanged |
| Implementation audit | `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` | `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194` | 427 | historical, unchanged |

The original hash `1daa2439…8857` is **superseded, not reused**. The amended
hash `d6cdeea1…bc1f` is the operative protocol hash. Both are recorded here;
§11 states how far the original content remains recoverable.

The freeze record is not rewritten. Its §3 authorisation statement and its §5
hash table remain accurate for the original freeze; this record supplies the
amendment that the freeze record's §3 requires.

---

## 2. User-approved decisions

1. **E11 — withdraw.** E11 is withdrawn as an acceptance gate. No replacement
   gate E11′ is introduced. E12–E16 keep their identifiers and numbering. The
   protocol explains that reversing stimulus sequences does not imply reversal
   of current vectors produced by a causal one-sided scheduler. E3, E8, E9 and
   E16 are preserved.
2. **E2 — clarify.** The 12-neuron statement is a statement about the
   stimulated-index set. It does not mean that all 12 neurons receive nonzero
   current at every step. Step and constant conditions drive four neurons; a
   crossfade drives four or eight depending on the transition state; `N0`
   drives none; `K_C` drives four. The 800 pA total and all stimulus
   definitions are preserved.
3. **E10 — correct.** One fresh-subprocess repeat per main seed, six
   determinism conditions per seed, three main seeds: 18 repeats.
   126 main instances + 18 repeats + 42 pilot instances = 186 planned
   instances. Any wording implying two repeats is removed. The run matrix is
   not changed.
4. **§3.5 — clarify.** The 50 ms crossfade is a causal, one-sided blend,
   `(1 − α) × previous + α × current`. It is not time-reversal equivariant. The
   scheduler is not changed.
5. **§15 — add limitations.** Crossfade input-current vectors are not expected
   to be time-reversal symmetric; half-open frame boundaries add endpoint
   mismatches; C3/C4 remain secondary route/order comparisons; stimulus
   reversal does not establish current-waveform reversal. No perfect-matching
   claim is made.

---

## 3. Exact changes made to the preregistration

Only the locations below changed. No other section, table or formula was
rewritten.

| Location | Before (frozen) | After (amended) |
|---|---|---|
| Header status | "FROZEN PROTOCOL — APPROVED DECISIONS RECORDED" | "FROZEN PROTOCOL — AMENDED 2026-11-14" |
| Header, after freeze date | no amendment note | Amendment note recording the amendment record, the withdrawn E11, the E2/E10 clarifications, the §3.5/§15 statements, and the original hash |
| §3.5, after the crossfade bullet | no statement on reversal | Causal one-sided blend; not time-reversal equivariant; stimulus reversal does not reverse the current waveform; E8 and E3 are the operative checks |
| §5.3 item 3 | heading "Exactly 12 stimulated neurons"; no per-step count | heading "Stimulated set has exactly 12 indices"; set-level statement plus per-step counts (4 step/constant; 4 or 8 crossfade; 0 `N0`) |
| §5.7 item 7 | crossfade reversal at `1e-9` pA on the simulation grid (E11) | crossfade construction: frame-sequence reversal (E8), same causal blend, no input-current reversal requirement, 800 pA (E3), `α = 0.5` check (§14.4) |
| §6.1 second sentence | "A second run in a fresh subprocess for `C1`, `C2`, `C3`, `C4`, `N0` and `K_C`" | "One repeat run in a fresh subprocess for the step-mode `C1`, `C2`, `C3` and `C4`, plus `N0` and `K_C`" |
| §6.2 matrix row | "Determinism repeats (fresh subprocess; C1, C2, C3, C4, N0, K_C)" | "Determinism repeats (fresh subprocess; step-mode C1–C4, N0, K_C)"; count 6 / 3 / 18 unchanged |
| §10.1 step 1 | "Verify E1–E16" | "Verify the applicable gates E1–E10 and E12–E16 (E11 is withdrawn)" |
| §10.3 row 1 | "Any E1–E16 failure" | "Any applicable-gate failure (E1–E10, E12–E16; E11 withdrawn)" |
| §11 heading | "Execution validity E1–E16" | "Execution validity E1–E16 (E11 withdrawn)" |
| §11 E2 row | "Exactly 12 neurons receive nonzero sensory current" | set-level 12 indices plus per-step 4 / 4-or-8 / 0; 800 pA where a schedule is active; `stimulus=None`; background/noise 0 |
| §11 E10 row | "A parent run and two fresh-subprocess runs" | one repeat per parent; step-mode C1–C4, `N0`, `K_C`; 6 × 3 = 18 repeats; 126 + 18 + 42 = 186; not two samples |
| §11 E11 row | crossfade reversal gate | **withdrawn by the approved protocol amendment (2026-11-14)**; E8, E3 and §14.4 are the operative checks |
| §11 closing sentence | "E1–E16 are execution validity" | "The applicable gates E1–E10 and E12–E16 are execution validity. E11 is withdrawn" |
| §12 bullet | invalid if E16 **or E11** fails | invalid if E16 fails |
| §13.1 gate bullet | "the gate results E1–E16" | "the gate results for the applicable gates E1–E10 and E12–E16 (E11 withdrawn)" |
| §14.5 step 2 | "verify E1–E16 on a smoke run" | "verify the applicable gates E1–E10 and E12–E16 on a smoke run. E11 is withdrawn" |
| §15 | 20 limitations | 24 limitations; items 21–24 added (causal crossfade; stimulus reversal is not current reversal; half-open endpoint mismatches; C3/C4 secondary route/order comparisons) |
| §16 | no bullet on crossfade reversal | added: no claim that the C3/C4 crossfade input-current vectors are time reverses or that the crossfade block is a matched reversal control |

The amended file has 1,177 lines. The increase is the header note, the §3.5
paragraph, the §5.3 and §5.7 expansions, the longer E2/E10/E11 rows, the four
§15 limitations and the §16 bullet.

---

## 4. E11 numerical evidence

The evidence below is reproduced from
`docs/P3_3C5_IMPLEMENTATION_AUDIT.md` §1.4 and was independently re-derived
before the amendment proposal. It is an input-scheduler arithmetic result, not
a simulation result.

| Mode | Mismatching grid points | Interior | Frame boundaries |
|---|---|---|---|
| `transition_ms = 0` (step) | 3 / 1,201 | 0 | 150, 300, 450 ms |
| `transition_ms = 50` (crossfade) | **597 / 1,201** | 594 | 150, 300, 450 ms |

The crossfade mismatch set is exactly
`[100.5, 200) ∪ [250.5, 350) ∪ [400.5, 500)` on the 0.5 ms grid: three windows
of 199 points each. It is the analytic consequence of applying a causal,
one-sided ramp to a reversed frame sequence, not numerical noise.

Two independent causes:

1. **Causality.** The blend exists only after a change. Reversing the sequence
   maps a ramp-after-`t0` to a time before the mirrored transition, where the
   mirrored schedule is steady. At `α = 0` the outgoing lane still carries the
   full 200 pA, so the mirrored vectors differ.
2. **Half-open boundaries.** Even with `transition_ms = 0`, a right-continuous
   piecewise-constant schedule fails the identity at the three shared frame
   boundaries (150, 300, 450 ms). E8 is a 50 ms frame-grid statement and does
   not imply continuous-time equality.

E11 was scoped to the C3/C4 crossfade pair: 2 runs per seed, 6 main instances
and 2 pilot instances would have been `INVALID_EXECUTION` under §12. No
implementer could make them valid while obeying §3.5 and the delivered
scheduler.

---

## 5. E2 clarification

E2 now separates two claims that the frozen wording conflated:

- **Set level.** For every run with a lane schedule, `stimulated_indices` has
  exactly 12 entries (the `player_lane` population), and no neuron outside that
  set receives nonzero sensory current. This is the no-leakage condition.
- **Per step.** The number of neurons with nonzero current depends on the mode:
  4 for `K_L`, `K_C`, `K_R` and every step-mode schedule; 4 or 8 during a
  crossfade (4 at `α = 0` and at/after the 50 ms window, 8 for `0 < α < 1`);
  0 for `N0`, which has no input schedule. `K_C` drives four CENTER neurons.

Total injected sensory current remains 800 pA at every step where a schedule is
active, within the frozen `1e-9` pA tolerance (E3). No stimulus definition
changed.

---

## 6. E10 clarification

E10 now states one repeat, not two:

- Determinism subset: the **step-mode** `C1`, `C2`, `C3`, `C4`, plus `N0` and
  `K_C`.
- One fresh-subprocess repeat per parent run.
- Six conditions × three main seeds = **18 repeat instances**.
- 126 main instances + 18 repeats + 42 pilot instances = **186 planned
  instances**.
- The repeat is a determinism check, not an independent replicate; the parent
  and repeat are not two samples.

The `§6.2` matrix already implied the step-mode subset and the 18/186 totals.
The amended E10, §6.1 and §6.2 now agree exactly. No two-repeat wording
remains anywhere in the preregistration, and no run count changed.

---

## 7. Elements confirmed unchanged

- **E3** (800 pA total at every step within `1e-9` pA, holds and crossfades):
  unchanged.
- **E8** (C2 = reverse(C1), C4 = reverse(C3) on the 50 ms grid; sequence hashes
  differ; state multiset identical): unchanged.
- **E9** (C3/C4 produce identical spike trains for 0–150 ms): unchanged.
- **E16** (C1 ≡ `L→C`, C2 ≡ `R→C` for `t < 400 ms`): unchanged.
- **E1, E4–E7, E12–E15**: unchanged.
- **Primary contrast** P1 = `Δ_C(C1, C2)`: unchanged.
- **M6′** formula, Hz units, three state-relative bins, four CENTER neurons:
  unchanged.
- **C1–C4 stimulus sequences**, dwells, onsets and endpoints: unchanged.
- **Main seeds** 20261104/20261105/20261106 and **pilot seed** 20261107 with
  exclusion from inference: unchanged.
- **T1 step scheduler** (`transition_ms = 0`) and the **50 ms crossfade
  robustness** conditions: unchanged.
- **800 pA total-current specification**: unchanged.
- **Controls and descriptive reference methodology** (R200, R150,
  constant-lane, single-transition): unchanged.
- **No p-values, significance claims or confidence intervals**: unchanged.
- **2-of-3 seed consistency** remains descriptive only: unchanged.
- **Negative-result reporting rules**: unchanged.
- **Run matrix**: 42 distinct runs per seed, 126 main + 18 determinism repeats
  + 42 pilot = **186 planned instances**: unchanged.
- **No new thresholds, controls, conditions or scientific claims**: confirmed.
- **No E11′** was added.

---

## 8. Remaining scientific limitations

The amended §15 carries 24 limitations. The four added by this amendment are:

21. The crossfade is causal, not time-symmetric. The blend ramps only after a
    change; the C3/C4 crossfade input-current vectors are not expected to be
    time reverses; the crossfade contrast includes the ramp asymmetry and is
    descriptive.
22. Reversing the stimulus sequence does not reverse the current waveform.
    E8 is a frame-grid statement; it does not imply equality of injected
    current vectors at mirrored times.
23. Half-open frame boundaries add endpoint mismatches. Even in step mode the
    schedule is not exactly time-reversal symmetric at the three transition
    instants; no continuous-time reversal is claimed.
24. C3/C4 remain secondary route/order comparisons. They are not matched on
    transition-type order or per-time lane, and no claim of perfect matching is
    made.

These are properties of the frozen design, not defects to be corrected. They
must appear in the final report if the experiment is later executed.

The freeze record's §4 lists 18 limitations, while the amended §15 lists 24.
The freeze record is a historical record and is not rewritten. The operative
list is §15 of the amended preregistration.

---

## 9. Authorisation state

- **Implementation is not authorised** by this amendment. No configuration,
  runner, test, validation script or analysis code may be written without a
  separate implementation authorisation.
- **Execution is not authorised.** No run — pilot or main — may occur without a
  separate execution authorisation after implementation and gate verification.
- **The 186 planned run instances were not started.**
- **No E11′** or other replacement gate was introduced.
- No simulation was run, no spike was generated and no result or outcome class
  was produced.
- No Phase 3C.6, Phase 3C.8, Phase 4, 5 or 6 artifact was touched.

The correct state is: **protocol amended and operative, awaiting a separate
implementation authorisation.**

---

## 10. Repository integrity

Verified after the amendment and after this record was written.

| Item | Value |
|---|---|
| HEAD | `62a64309cadc0db7353c856607cee5369993bd65` |
| Branch | `main` |
| Staged files | 0 |
| `README.md` SHA-256 | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` SHA-256 | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |
| Design proposal SHA-256 | `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284` |
| Preregistration draft SHA-256 | `3ceda5ece8017fc753a0f3aa9360a963efb58393717a89505d6efd08c3372438` |
| Preregistration review SHA-256 | `f50fb2b7eec9a7577bbc28155ccd3e22d3b623d986fbc75b739311b89f3a973a` |
| Implementation audit SHA-256 | `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194` |
| Amendment proposal SHA-256 | `7e6d921a73ffc6ea7f09512eb95d06b628c0e434fe642cbdc12028e79cc17c90` |
| Freeze record SHA-256 | `99ac601534876f3d9e26a2a123d2fd7733a3c62338ee81c9c070a409f75d06fd` |
| Amended preregistration SHA-256 | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` |

- No Python source, scheduler, configuration, dataset, result or Phase 4–6
  artifact was modified **by this task**. The 21 pre-existing tracked
  modifications in the working tree are unchanged.
- No file was staged, committed, pushed, reset, cleaned, stashed, checked out,
  deleted or overwritten.
- The only files changed or created by this task are the amended
  preregistration and this record. The implementation audit, amendment
  proposal, freeze record, design proposal, draft and review are unchanged.
- Pre-existing tracked modifications and untracked files are preserved.

---

## 11. Auditability

The original frozen preregistration is identified by the hash
`1daa2439…8857`. The amendment was applied in place to the same path, so the
working tree now holds only the amended version. The file is untracked in the
current repository, so git history does not retain the original content. The
original hash, the exact superseded passages quoted in §3, and the full
amendment proposal (`7e6d921a…7c90`) preserve what changed for audit. If the
original 1,127-line file is required for a future audit, it must be obtained
from an external copy or reconstructed from those quotations; this record does
not claim that git history contains it.

The amended protocol is identified by `d6cdeea1…bc1f`. Both hashes appear in
this record. Any future implementation must record the amended hash, not the
superseded one, and must state that E11 is withdrawn.

If a further protocol change is required, it must be recorded in a new
amendment record with a further new SHA-256. This record is not edited in place
for later amendments.
