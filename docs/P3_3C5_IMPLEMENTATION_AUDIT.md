# P3-3C.5 — Implementation Audit

**Status: BLOCKED — NO IMPLEMENTATION PERFORMED.**

**Date.** 2026-11-14.

**Frozen protocol.**
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md`
SHA-256 `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857`
(1,127 lines), unchanged before and after this audit.

**Task scope.** Authorisation to implement P3-3C.5 only: configuration, runner,
tests and protocol-validation code. No execution of experiment conditions, no
scientific results, no change to the frozen protocol.

**Outcome.** The implementation was stopped before any code was written. Gate
**E11** (`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` line 769; also §5.7,
lines 385–387) cannot be satisfied by any implementation that obeys the
protocol's own crossfade definition, which is fixed in §3.5 (lines 265–272)
and cross-referenced to `sensory/input_scheduler.py` lines 162–174 in
Appendix B. The task instruction is explicit: a requirement the
implementation cannot satisfy is documented and work stops; the protocol is
not reinterpreted. That is what this document does.

This audit does **not** declare the protocol scientifically invalid and does
**not** propose a result. It records an unsatisfiable execution gate and three
smaller wording inconsistencies that must be resolved by a recorded amendment
with a new SHA-256 before implementation can resume. No configuration, runner,
test, validation script or result file was created.

---

## 1. The blocking requirement

### 1.1 Frozen text

E11, verbatim (line 769):

> Crossfade reversal: for the crossfade mode, the C4 input-current vector at
> time `t` equals the C3 vector at `600 − t` within `1e-9` pA on the
> simulation grid, excluding the 0.5 ms tail.

E11 is an execution-validity gate, not a scientific success criterion. §5.7
restates it as an implementation contract. §12 (line 788) makes a run that
fails E11 **invalid**:

> A run whose causal decomposition (E16) or crossfade reversal (E11) fails is
> invalid.

### 1.2 Frozen crossfade definition

§3.5 (lines 265–272) defines the crossfade that the implementation must use:

> **Robustness: T1 linear crossfade, `transition_ms = 50`.** During the first
> 50 ms after a change, `values = (1−α)·previous + α·current`, with
> `α = (t − t0)/50`.

The formula is not left to the implementer. Appendix B (line 1116) binds it to
`sensory/input_scheduler.py` lines 162–174, which implement exactly:

```python
index = searchsorted(starts, time_ms, side="right") - 1
values = self._values[index]
if transition_ms > 0 and index > 0 and time_ms < starts[index] + transition_ms:
    alpha = (time_ms - starts[index]) / transition_ms
    values = (1.0 - alpha) * self._values[index - 1] + alpha * values
```

The blend is causal and one-sided: it exists only in the 50 ms **after** each
change. `previous` is the outgoing lane. At `α = 0` the outgoing lane still
receives the full 200 pA; the incoming lane reaches 200 pA only at `α = 1`.

### 1.3 Why the two are incompatible

C3 and C4 are related by frame-index reversal:

- C3 frames: `L L L | C C C | R R R | L L L`
- C4 frames: `L L L | R R R | C C C | L L L`

§3.2 (line 210) and §14.4 (line 904) define the reversal on the **50 ms
frame grid**, `t'_i = (12 − 1 − i) × 50 ms`. E8 (line 766) checks exactly
that. E11 escalates the same relation to the **0.5 ms simulation grid** and
to the actual injected current vector.

Under the frozen crossfade, the relation fails for two independent reasons.

1. **Causality.** A crossfade ramps after a transition. Reversing the
   sequence turns every ramp-after-`t0` into a ramp-before the mirrored time.
   The mirrored vector at `600 − t` is then either fully in a steady block or
   in a different part of a different ramp. The one-sided blend is not
   time-reversal equivariant. This is not an implementation defect; it is a
   property of the formula the protocol mandates.

2. **Half-open frame boundaries.** Even with `transition_ms = 0`, a
   right-continuous piecewise-constant schedule satisfies
   `C4(t) = C3(600 − t)` everywhere except exactly at frame boundaries. At
   `t = 150 ms`, C4 has just entered its `R` block while C3 at `450 ms` has
   just entered its `L` block; at `t = 300 ms`, C4 is in `C` while C3 at
   `300 ms` is in `R`; at `t = 450 ms`, C4 is in `L` while C3 at `150 ms` is
   in `C`. The frame-index reversal maps intervals, not their shared
   endpoints. E11 excludes only the 0.5 ms tail, not the three transition
   instants.

Neither cause can be removed without changing the frozen protocol:

- The crossfade formula cannot change: §3.5 fixes it and Appendix B binds it
  to the delivered scheduler; E12 also forbids changing scheduler semantics.
- The stimuli cannot change: C1–C4 are fixed in §3.2 and Appendix A.
- The crossfade block cannot be dropped: D3 (line 54) approves it, and the
  run matrix (§6.2) contains 24 main crossfade instances.
- E11 cannot be read as an approximate or frame-grid check: it says "on the
  simulation grid" at `1e-9` pA.

### 1.4 Numerical evidence

The check used the repository's own `LanePopulation` encoder (3 lanes × 4
neurons, amplitude 1.0), a 12-index mapping stub, and the delivered
`SensoryInputScheduler`. C3 and C4 were built as the 12 explicit
`(timestamp_ms, GameState(player=PlayerState(lane=...)))` frames. At every
grid time `t = 0, 0.5, …, 600 ms` (1,201 points, tail excluded) the vectors
`C4(t)` and `C3(600 − t)` were compared with `rtol=0`, `atol=1e-9` pA.

| Mode | Mismatching grid points | Interior | Frame boundaries |
|---|---|---|---|
| `transition_ms = 0` (step) | 3 / 1,201 | 0 | 150, 300, 450 ms |
| `transition_ms = 50` (crossfade) | **597 / 1,201** | 594 | 150, 300, 450 ms |

Representative crossfade values (neuron indices 0–3 LEFT, 4–7 CENTER, 8–11
RIGHT):

| `t` | C4 vector at `t` | C3 vector at `600 − t` |
|---|---|---|
| 100.5 | 200 pA on LEFT (4 neurons) | 198 pA LEFT + 2 pA RIGHT (8 neurons) |
| 150.5 | 198 pA LEFT + 2 pA RIGHT | 200 pA RIGHT (4 neurons) |
| 175.0 | 100 pA LEFT + 100 pA RIGHT (8 neurons) | 200 pA RIGHT (4 neurons) |
| 450.0 | 200 pA CENTER (4 neurons) | 200 pA LEFT (4 neurons) |

The first interior mismatch at `t = 100.5` arises because `600 − 100.5 =
499.5` lies in the crossfade that follows C3's transition at 450 ms, while
C4 at 100.5 ms is in its steady initial `L` block. The 597 count is a
consequence of the formula, not of a particular stub, encoder or mapping:
the encoder is one-hot and the crossfade operates on encoded activations.

Additional checks at the frame grid under crossfade confirm the failure is
not an artefact of off-grid times: the identity fails at 150, 300 and 450 ms,
and holds at 0, 50, 100, 200, 250, 350, 400, 500 and 550 ms.

### 1.5 Consequence if the protocol were executed as frozen

E11 is scoped to the C3/C4 pair, not to all eight crossfade sequences. Its
consequences are nevertheless structural:

- The **C3 and C4 crossfade runs** (2 per seed, 6 main runs and 2 pilot runs)
  fail E11 and are `INVALID_EXECUTION` under §12.
- The other six crossfade sequences (C1, C2, `C L R L`, `L C L R`, `R L C L`,
  `L R L C`) are not covered by any reversal check, so the crossfade block
  cannot be reported as a complete robustness panel: its two order-critical
  members are invalid and the remainder have no equivalent correctness gate.
- The frozen run matrix is 42 distinct runs per seed and 186 planned
  instances (§6.2). Six of the 24 main crossfade instances cannot be made
  valid by any implementation, so the matrix cannot be completed as a valid
  protocol.
- §14.5 step 2 requires E1–E16 to be verified on a smoke run before
  execution. E11 cannot be verified because it is false for the mandated
  stimulus, so the pre-execution gate cannot be passed.
- An implementation could still run the C3/C4 crossfade conditions and record
  the failure, but that would encode a gate that is false for the mandated
  stimulus, not a check that detects implementation error. It would also
  present the crossfade robustness block as executed while its order-critical
  members are invalid. That is a silent reinterpretation of what D3 requires,
  and the task forbids it.

### 1.6 Why no workaround was applied

| Possible workaround | Why it is not permitted |
|---|---|
| Change the crossfade to a time-symmetric blend | Changes the frozen stimulus definition in §3.5; requires re-freezing and a new scientific justification. |
| Apply the crossfade before instead of after the transition | Contradicts "during the first 50 ms after a change" and the cited scheduler. |
| Compare only at frame starts | E11 says simulation grid; the frame-start comparison still fails at 150, 300 and 450 ms. |
| Exclude transition instants and interior ramp points | Would leave little content beyond E8 and would rewrite the gate. |
| Drop the crossfade block | Contradicts D3 and the 186-instance matrix. |
| Treat the failures as expected and ignore E11 | Prohibited reinterpretation; §12 makes the runs invalid. |
| Change `sensory/input_scheduler.py` | E12 forbids changing scheduler semantics; it is shared with Phase 3A/3B/3C. |

---

## 2. Secondary protocol inconsistencies

These do not independently stop the work, but they must be resolved in the
same amendment so that a later implementation does not have to choose a
reading silently.

### 2.1 E2: per-step versus set-level "12 neurons"

E2 (line 760) begins:

> Exactly 12 neurons receive nonzero sensory current (`player_lane` only);
> `stimulated_indices` has 12 entries; all other neurons receive 0 pA
> sensory current.

The first clause is false per step for two condition classes that the
protocol requires:

- `K_C` drives only the 4 CENTER neurons at every step.
- A crossfade at `α = 0.5` drives 8 neurons (4 at 100 pA outgoing, 4 at
  100 pA incoming); at `α = 0` it drives 4 (the outgoing lane).

The operative reading is unambiguous from E2's second and third clauses and
from §5.3 (lines 372–374): the **stimulated set** has 12 entries and no
neuron outside it receives current. The arithmetic checks out: total current
is 800 pA in every mode (200 pA × 4 for a hold, 200(1−α) × 4 + 200α × 4
during a crossfade). Proposed amendment: state the set-level condition
explicitly and add the per-step nonzero counts (4 for step and constant
schedules; 4 or 8 for crossfades).

### 2.2 E10: number of fresh-subprocess repeats

E10 (line 768) says:

> A parent run and two fresh-subprocess runs produce identical input-schedule
> signatures and spike hashes for the determinism subset.

§6.1 (lines 405–407) says "A second run in a fresh subprocess" — one repeat.
§6.2 gives **18** determinism repeats (6 conditions × 3 seeds × 1) and a
planned total of **186**. Two fresh repeats would give 36 repeats and 204
instances. The matrix and E10 cannot both be exact. Proposed amendment:
choose one repeat (consistent with §6.1 and 186) and reword E10, or raise the
matrix to 36 and 204.

### 2.3 E11 and the step-mode boundary identity

Recorded for completeness: even in step mode the literal E11 relation fails
at 3 of 1,201 grid points. E11 is scoped to the crossfade mode, so this does
not itself invalidate a step run, but it shows that the gate's premise —
continuous-time reversal of a right-continuous schedule — does not hold at
transition instants for any mode. Any replacement gate must state its
sampling convention.

### 2.4 Implementation note: spike-time boundary attribution

This is not an inconsistency, but a frozen-rule consequence that the report
must disclose. `SpikeRecorder.record` (`brain/neural_activity.py`) timestamps
a spike as `(step_index + 1) × dt_ms`. A spike produced by the last step
before a CENTER onset (input applied at `onset − 0.5 ms`) receives a
timestamp exactly equal to the onset. §3.1 assigns a spike at a bin boundary
to the bin that starts there, so that spike is counted in state-relative bin
`s = 0`. The effect is at most one 0.5 ms step and applies equally to every
condition; it is not corrected, because correcting it would depart from the
frozen binning rule. The implementation must state it rather than silently
shifting a bin edge.

---

## 3. Requirement readiness matrix

No row is "implemented": the table records whether the requirement is
implementable against the delivered interfaces and whether the frozen text is
consistent. "Planned" names are design intent, not files on disk.

### 3.1 Task implementation requirements

| # | Requirement | Status | Planned source | Planned test | Issue |
|---|---|---|---|---|---|
| 1 | Exact C1–C4 stimuli | Ready | config timelines; `build_timeline` | exact frame equality and hashes | none |
| 2 | Primary C1-vs-C2 CENTER comparison | Ready | `delta_c` on CENTER group | synthetic-count metric test | none |
| 3 | Exact M6′ in Hz, three bins, four neurons | Ready | `delta_c`, `state_bins` | unit conversion and bin-edge test | §2.4 timing note |
| 4 | Four-neuron CENTER measurement from lane group 1 | Ready | `mapping.populations["player_lane"].plan.groups[1]` | group-order and size test | none |
| 5 | Three state-relative bins per onset | Ready | `state_bins(onset)` | edge table for 0/150/200/300 ms | none |
| 6 | `K_C` auxiliary onset reference | Ready | `delta_c(C1,K_C)`, `delta_c(C2,K_C)` | synthetic-count test | E2 wording (§2.1) |
| 7 | R200/R150 descriptive references | Ready | `reference_sets` from §3.4 | classification test over 6 + 12 sequences | R200 one-vs-one limitation stays |
| 8 | T1 step scheduler | Ready | `build_scheduler(transition_ms=0)` | per-step vector test | none |
| 9 | 50 ms crossfade robustness | **Blocked** | `build_scheduler(transition_ms=50)` | α=0.5 test would pass; E11 test fails | **E11** |
| 10 | Mandatory controls and runs | Partly ready | condition table from §3.3/§6.2 | matrix-completeness test | E10 repeat count (§2.2) |
| 11 | Main seeds 20261104/5/6; pilot 20261107 separate | Ready | config `seeds` block | seed-plan test | none |
| 12 | Determinism and reproducibility | Ready to code | parent/child digest | digest-equality test (execution-gated) | E10 count (§2.2) |
| 13 | Run manifests and provenance | Ready | sidecar builder following §14.3 | sidecar field test | none |
| 14 | Protocol-compliance validation | **Blocked** | `validate_protocol` would contain E11 | would fail on the mandated stimulus | **E11** |
| 15 | No `visual_any`, no shuffle block, no invented T2/T3 or lane pulses | Ready | condition table has none | exclusion test | none |

### 3.2 Execution gates E1–E16

| Gate | Status | Basis |
|---|---|---|
| E1 | Ready | runner completion accounting |
| E2 | Wording conflict | per-step count vs set-level count (§2.1) |
| E3 | Ready | scheduler preserves 800 pA: verified at 150.0, 150.5 and 175.0 ms crossfade steps |
| E4 | Ready | constant-lane runs target one group |
| E5 | Ready | `BrainSimulator` accepts `input_schedule=None`; zero background/noise gives zero spikes |
| E6 | Ready | lane groups are ordered left/center/right in the mapping plan |
| E7 | Ready | mapping exposes per-group indices and root IDs |
| E8 | Ready | frame-grid reversal holds for C1/C2 and C3/C4 |
| E9 | Ready | C3/C4 share the `L` prefix for 0–150 ms |
| E10 | Wording conflict | one vs two fresh repeats (§2.2) |
| E11 | **Unsatisfiable** | 597/1,201 crossfade grid mismatches (§1.4) |
| E12 | Ready | no source semantics need to change |
| E13 | Ready | sidecar records hashes and git block |
| E14 | Ready | outside activity is reported separately |
| E15 | Ready | half-open `[0,600)` bins plus reported tail |
| E16 | Ready | C1/`L→C` and C2/`R→C` share input for `t < 400 ms` |

### 3.3 Planned deliverables (not created)

| Path | Status |
|---|---|
| `configs/p3_3c5_lane_encoding.yaml` | not created |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | not created |
| `experiments/phase_3c/p3_3c5_protocol_validation.py` | not created |
| `tests/test_p3_3c5_lane_encoding.py` | not created |
| `experiments/phase_3c/results/p3_3c5_*` | not created |

---

## 4. Amendment options

Any option below requires a recorded amendment to
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` and a **new SHA-256**. The
current hash `1daa2439…8857` cannot be reused after an edit.

### 4.1 Recommended: remove E11, keep the rest

- Delete E11 and its §5.7 restatement.
- Keep the frame-grid reversal gate E8 unchanged.
- Keep E3 (800 pA at every step) as the crossfade arithmetic check.
- Report the crossfade block descriptively, as a robustness condition whose
  input is not expected to be time-reversal symmetric.
- Add a sentence to §3.5 stating explicitly that the crossfade is causal and
  is not reversal-equivariant, so no future run treats E11's absence as a
  result.

This changes no stimulus, no run count and no metric. It removes a gate that
is false by construction. It is the smallest amendment consistent with the
delivered scheduler.

### 4.2 Alternatives, not recommended without scientific review

- **Restrict E11 to frame-start points.** Fails at 150, 300 and 450 ms for
  crossfade; would need to exclude the 50 ms ramp after every transition, at
  which point it adds little beyond E8.
- **Define a time-symmetric crossfade.** Changes §3.5, changes what "first
  50 ms after a change" means and weakens the α=0.5 rheobase arithmetic;
  requires re-freezing the stimulus and a new design note.
- **Drop the crossfade block.** Changes D3 and the 186-instance matrix; loses
  the robustness component the task explicitly requires.

### 4.3 Companion wording amendments

- E2: restate as set-level 12 indices plus zero outside current, with per-step
  counts of 4 (step/constant) and 4 or 8 (crossfade).
- E10: align with §6.1/§6.2 ("one fresh-subprocess repeat", 18 repeats, 186
  planned) or raise the matrix to two repeats (36, 204).

If the amendment is approved, implementation can proceed with the planned
deliverables in §3.3 and the matrix in §3.1. Until then the correct state is
**protocol frozen, implementation blocked**.

---

## 5. What was actually done

- Read the frozen preregistration, the freeze record, the proposal, the draft,
  the review, the sensory configuration, the game-state, encoder, mapping,
  input-scheduler, simulator, recorder and Phase 3C runner/test conventions.
- Ran one in-memory arithmetic check of `SensoryInputScheduler._values_at`
  with the repository encoder and a 12-index stub. It instantiated no
  `BrainSimulator`, read no connectome, generated no spikes, wrote no file
  and executed no experiment condition.
- Verified the protected hashes and the git block before writing this
  document.
- Wrote this document. Nothing else was created or modified.

---

## 6. No execution, no results

- No experiment condition was executed.
- No simulation was run.
- No spike train, rate, metric, reference value or outcome class was produced.
- No `experiments/phase_3c/results/p3_3c5_*` artifact exists.
- The 186 planned run instances were not started.
- Phase 3C.6 and 3C.8 were not started.
- No Phase 4, 5 or 6 artifact was touched.
- No scientific claim, positive or negative, is made about lane-order
  sensitivity.

The numerical table in §1.4 is an input-scheduler arithmetic result, not a
simulation result. It says nothing about neurons, spikes or perception.

---

## 7. Repository integrity

Verified immediately before writing this document.

| Item | Value |
|---|---|
| HEAD | `62a64309cadc0db7353c856607cee5369993bd65` |
| Branch | `main` |
| Staged files | 0 |
| Tracked modifications | 21 (pre-existing, preserved) |
| `git status --porcelain` entries | 217 (measured before this audit was written; pre-existing untracked entries; untracked directories are collapsed) |
| `README.md` SHA-256 | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` SHA-256 | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |
| Frozen preregistration SHA-256 | `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857` |
| Freeze record SHA-256 | `99ac601534876f3d9e26a2a123d2fd7733a3c62338ee81c9c070a409f75d06fd` |

- No file was staged, committed or pushed.
- `git add .`, `git add -A`, `git reset`, `git clean`, `git stash` and
  `git checkout` were not used.
- No existing file was deleted, reset, cleaned, stashed or overwritten.
- The only file created by this task is this audit.
- Pre-existing modifications and untracked files are unchanged.
- The frozen preregistration and freeze record are unchanged.

---

## 8. Readiness statement

P3-3C.5 is **not ready for execution authorisation**. It is not ready for
implementation completion either: gate E11 is unsatisfiable under the frozen
stimulus and scheduler, and E2 and E10 need wording amendments. The
implementation has not been written, no test has been run, and no scientific
result exists.

The next step is a recorded protocol amendment (recommended: §4.1 plus §4.3)
with a new preregistration SHA-256. After that, implementation can resume
under a separate task, and execution remains a further separate authorisation.
