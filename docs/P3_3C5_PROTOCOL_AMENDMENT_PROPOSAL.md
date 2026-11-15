# P3-3C.5 — Protocol Amendment Proposal

**Status: PROPOSAL ONLY — NOT APPROVED. The frozen preregistration is
unchanged.**

**Date.** 2026-11-14.

**Target document.**
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md`
SHA-256 `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857`
(1,127 lines).

**Related documents, unchanged by this proposal.**

| Document | SHA-256 |
|---|---|
| `docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md` | `99ac601534876f3d9e26a2a123d2fd7733a3c62338ee81c9c070a409f75d06fd` |
| `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` | `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194` |
| `docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md` | `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284` |
| `docs/P3_3C5_PREREGISTRATION_REVIEW.md` | `f50fb2b7eec9a7577bbc28155ccd3e22d3b623d986fbc75b739311b89f3a973a` |

**Scope.** Documentation and technical analysis only. No implementation code,
scheduler change, configuration change, simulation, result or edit to the
frozen preregistration, the freeze record or the implementation audit. The
experiment has not been implemented.

**Proposed changes at a glance.**

| Item | Proposal | Run-count effect |
|---|---|---|
| A — E11 | Withdraw the crossfade reversal gate; keep E8, E3, the stimuli and the causal scheduler | none |
| B — E2 | Clarify set-level versus per-step neuron counts | none |
| C — E10 | Align the determinism wording with §6.1 and §6.2 | none (186) or +18 (204), user decision |

---

## 1. Exact original requirements

### 1.1 E11 and its restatements

Gate table, line 769:

> | E11 | Crossfade reversal: for the crossfade mode, the C4 input-current
> vector at time `t` equals the C3 vector at `600 − t` within `1e-9` pA on the
> simulation grid, excluding the 0.5 ms tail. |

Implementation contract §5.7, lines 385–387:

> 7. **Crossfade reversal.** In crossfade mode, the C4 input-current vector at
>    time `t` must equal the C3 vector at `600 − t` within `1e-9` pA on the
>    simulation grid, excluding the 0.5 ms tail (E11).

Exclusion rule §12, lines 787–788:

> - A run whose causal decomposition (E16) or crossfade reversal (E11) fails
>   is invalid.

Pre-execution sequence §14.5, lines 921–922:

> 2. Implement the runner/config/tests in a separate authorised task; verify
>    E1–E16 on a smoke run.

E11 is also referenced in the freeze record's change log only indirectly: the
freeze record records E16 as a new gate but says nothing about E11. E11 is
present in the preregistration draft at line 730, and the preregistration
review does not mention E11 at all. E11 was therefore carried from the draft
into the freeze without a recorded review of its satisfiability.

### 1.2 E2

Gate table, line 760:

> | E2 | Exactly 12 neurons receive nonzero sensory current (`player_lane`
> only); `stimulated_indices` has 12 entries; all other neurons receive 0 pA
> sensory current; `simulator.stimulus is None`; background = 0; noise = 0. |

The operative clarification is §5.3, lines 372–374:

> 3. **Exactly 12 stimulated neurons.** `_stimulated_indices` is built from
>    `active_features` only (`sensory/input_scheduler.py` lines 126–131), so a
>    lane-only schedule has exactly 12 indices. Assert this (E2).

### 1.3 E10

Gate table, line 768:

> | E10 | A parent run and two fresh-subprocess runs produce identical
> input-schedule signatures and spike hashes for the determinism subset. |

The run plan is §6.1, lines 405–407:

> - One run per condition per seed. A second run in a fresh subprocess for
>   `C1`, `C2`, `C3`, `C4`, `N0` and `K_C` is a determinism check, not an
>   independent replicate.

The matrix is §6.2, lines 415–426: 42 distinct runs per seed, 126 main runs,
18 determinism repeats, 42 pilot runs, 186 planned instances.

### 1.4 Related frozen statements that constrain any amendment

| Statement | Location | Content |
|---|---|---|
| C3/C4 reversal | §3.2, line 210 | C2 is the exact time reverse of C1 and C4 of C3 under `t'_i = (12 − 1 − i) × 50 ms` |
| E8 | line 766 | C2 = reverse(C1), C4 = reverse(C3) on the 50 ms grid |
| Crossfade | §3.5, lines 265–272 | During the first 50 ms after a change, `values = (1−α)·previous + α·current`, `α = (t − t0)/50` |
| Crossfade binding | Appendix B, line 1116 | Formula is `sensory/input_scheduler.py` lines 162–174 |
| Crossfade local test | §14.4, line 909 | At `α = 0.5`, 100 pA on eight neurons |
| E3 | line 761 | 800 pA total at every step, holds and crossfades |
| D3 | line 54 | Step primary; 50 ms crossfade for C1–C4 plus four additional closed sequences |
| Frame-grid reversal test | §14.4, line 904 | C2 = reverse(C1), C4 = reverse(C3) on the 50 ms grid |
| Primary contrast | §7.1 | M6′ `Δ_C(C1, C2)` in Hz, CENTER group, three state-relative bins |
| Seeds | §6.1 | Main 20261104/5/6; pilot 20261107 excluded |

---

## 2. Why E11 is unsatisfiable

### 2.1 The objects being compared

Let `V_L`, `V_C`, `V_R` be the 12-neuron lane vectors produced by the
one-hot encoder at 200 pA: 200 pA on four neurons of the named lane and 0 pA
elsewhere. The scheduler's crossfade is

```
V(t) = (1 − α) · V_previous + α · V_current,    α = (t − t0) / 50
```

only for `t0 ≤ t < t0 + 50` and only when the frame segment at `t0` is not the
first segment. At `α = 0` the vector is still `V_previous`; at `α = 1` the
blend window has ended and the vector is `V_current`.

C3 frames: `L L L | C C C | R R R | L L L`
C4 frames: `L L L | R R R | C C C | L L L`

C4 is the frame-index reverse of C3 on the 50 ms grid. Both sequences change
lane at 150, 300 and 450 ms.

### 2.2 The formal contradiction

Consider a C4 transition at `t0` from lane `a` to lane `b`. Under
`t ↦ 600 − t`, the mirrored C3 transition is at `600 − t0` and runs from `b`
to `a`, because reversing a sequence reverses every transition.

At the exact transition time `t = t0`, the C4 crossfade has `α = 0` and
returns `V_a`. At the mirrored time `600 − t0`, the C3 crossfade also has
`α = 0` and returns `V_b`. E11 requires `V_a = V_b`, which is false for
distinct lanes.

For `u ∈ (0, 50)`:

```
C4(t0 + u)      = (1 − α) V_a + α V_b        (the C4 ramp)
C3(600 − t0 − u) = V_b                        (steady, before the C3 mirror)
```

The second line holds because `600 − t0 − u` lies inside the block that
precedes the C3 mirror transition; the previous C3 transition was 150 ms
earlier, so no crossfade is active there. Equality would require `α = 1`,
which is not reached for `u < 50`. At `u = 50` the C4 vector is `V_b` and the
C3 vector is `V_b`, so the two match again until the next transition.

The three C4 transitions give:

| C4 transition | C3 mirror | C4 at `t0` (α=0) | C3 at `600−t0` (α=0) | Mismatch window |
|---|---|---|---|---|
| 150: `L→R` | 450: `R→L` | L | R | (150, 200) |
| 300: `R→C` | 300: `C→R` | R | C | (300, 350) |
| 450: `C→L` | 150: `L→C` | C | L | (450, 500) |

The same argument applied from the C3 side adds the mirrored windows
`(400, 450)`, `(250, 300)` and `(100, 150)`. The union is

```
(100, 200) ∪ (250, 350) ∪ (400, 500)
```

On the 0.5 ms simulation grid this is exactly
`[100.5, 200) ∪ [250.5, 350) ∪ [400.5, 500)`: three windows of 199 points,
597 of 1,201 grid points.

This is a property of the frozen formula, not of a particular encoder, graph,
mapping or runner. A one-hot lane vector makes it easiest to see, but any
pair of distinct lane vectors would fail the same test.

### 2.3 The second, smaller contradiction

Even with `transition_ms = 0`, a right-continuous piecewise-constant schedule
does not satisfy the identity at the exact frame boundaries. At `t = 150`,
C4 has entered its `R` block while C3 at 450 has entered its `L` block; at
`t = 300`, C4 is in `C` while C3 is in `R`; at `t = 450`, C4 is in `L` while
C3 is in `C`. The frame-index reversal maps intervals, not their shared
endpoints. E11 excludes only the 0.5 ms tail, not the three transition
instants, so it fails at 3 grid points even in the primary step mode.

This second issue is independent of the crossfade. It shows that E11's
premise — a continuous-time reversal identity — does not hold for any mode at
transition instants. E8 is the correct reversal statement because it is
defined on the 50 ms frame grid.

### 2.4 Numerical evidence

The verification used the delivered `LanePopulation` encoder (3 lanes × 4
neurons, amplitude 1.0), a 12-index mapping stub, the delivered
`SensoryInputScheduler`, and the 12 explicit C3/C4 frames. Every grid time
`t = 0, 0.5, …, 600 ms` was compared with `rtol=0`, `atol=1e-9` pA.

| Check | Result |
|---|---|
| E8: C2 = reverse(C1), C4 = reverse(C3) on the frame grid | true |
| E11 step mode mismatches | 3 / 1,201: exactly {150, 300, 450} ms |
| E11 crossfade mismatches | **597 / 1,201** |
| Crossfade mismatch set | exactly `[100.5,200) ∪ [250.5,350) ∪ [400.5,500)` |
| E3 total current, step | 800.0 pA at all 1,201 points |
| E3 total current, crossfade | 800.0 pA at all points within `1e-9` pA |
| E9 C3/C4 input prefix `t < 150` | identical |
| E16 C1 ≡ `L→C` for `t < 400` | identical |
| E16 C2 ≡ `R→C` for `t < 400` | identical |
| Crossfade nonzero-neuron count | 4 at α=0, 8 for 0<α<1, 4 after the window |

Representative crossfade values:

| `t` | C4 vector at `t` | C3 vector at `600 − t` |
|---|---|---|
| 100.5 | 200 pA LEFT | 198 pA LEFT + 2 pA RIGHT |
| 150.0 | 200 pA LEFT | 200 pA RIGHT |
| 150.5 | 198 pA LEFT + 2 pA RIGHT | 200 pA RIGHT |
| 175.0 | 100 pA LEFT + 100 pA RIGHT | 200 pA RIGHT |
| 300.0 | 200 pA RIGHT | 200 pA CENTER |
| 450.0 | 200 pA CENTER | 200 pA LEFT |

The exact match of the mismatch set to the six derived windows is the
strongest evidence: the disagreement is not numerical noise or an encoder
artefact, it is the analytic consequence of a one-sided ramp under time
reversal.

### 2.5 What E11 was intended to establish

E11 sits among the runner-correctness gates, next to E8 (frame reversal) and
E16 (causal decomposition). Its evident purpose was to catch a construction
error: if C4 were built from a different timeline, or if the crossfade were
applied asymmetrically to C3 and C4, the two input streams would not be
mirrors and a C3/C4 spiking difference could not be attributed to the order
manipulation.

That purpose is legitimate. The error is that E11 asserts the mirror property
on the **input-current vectors**, while the protocol only guarantees it on the
**frame sequences**. A causal, one-sided filter cannot preserve a global
time-reversal identity. E11 asks the implementation to satisfy a mathematical
property that the frozen scheduler does not have, so it cannot detect a
runner error: it fails for every correct runner.

### 2.6 What can honestly be claimed after removal

After withdrawing E11, the following remain true and reportable:

1. **Frame-sequence reversal (E8).** C2 is the exact reverse of C1 and C4 of
   C3 on the 50 ms grid; the state multisets are identical.
2. **Current conservation (E3).** Total injected lane current is 800 pA at
   every step, including crossfades.
3. **Local crossfade correctness (§14.4).** At `α = 0.5`, eight neurons
   receive 100 pA; the blend follows the §3.5 formula.
4. **Prefix identity (E9).** C3 and C4 share the `L` prefix for 0–150 ms.
5. **Causal decomposition (E16).** C1 and `L→C`, C2 and `R→C` share input for
   `t < 400 ms`.
6. **Descriptive crossfade comparison.** The crossfade block reports whether
   the step-mode pattern persists under the configured causal smoothing. It
   is a descriptive condition, not a matched reversal control.

After removal, these claims are **not** available:

1. That the C3/C4 crossfade input-current vectors are time reverses of each
   other.
2. That the crossfade C3/C4 contrast isolates order independently of the
   ramp asymmetry.
3. That the crossfade block is a clean symmetry control or a matched
   reversal replay.
4. That C3 and C4 are perfectly matched in any mode; they remain unmatched on
   transition-type order and per-time lane, and the crossfade adds the ramp
   asymmetry.

### 2.7 No replacement threshold

No new numeric acceptance threshold is proposed. The only numbers in the
proposed edits are:

- the frozen `1e-9` pA arithmetic tolerance already used by E3 and E11;
- the existing `α = 0.5` / 100 pA / eight-neuron test in §14.4.

Neither is a scientific success threshold. The crossfade block is not used to
accept or reject a hypothesis; it is reported descriptively under the outcome
classes in §10.

An optional non-threshold construction check is described in §4.1.3. It
reuses the §3.5 formula and the `1e-9` pA tolerance and would only check that
the runner built the input it says it built. It is not required by this
proposal.

---

## 3. Evidence and source references

### 3.1 Sources inspected

| Source | Relevant content |
|---|---|
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | E2 (760), E3 (761), E8 (766), E10 (768), E11 (769), §5.3 (372–374), §5.7 (385–387), §12 (787–788), §3.2 (210), §3.5 (265–272), §6.1 (405–407), §6.2 (415–426), §14.4 (904, 909), §14.5 (921–922), §15 (935–997), Appendix B (1116) |
| `docs/P3_3C5_PREREGISTRATION_FREEZE_RECORD.md` | Decisions D1–D10; no mention of E11; change log records E16 as new |
| `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` | Blocking finding and readiness matrix; unchanged by this proposal |
| `docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md` | Crossfade rationale (lines 488–516); no E11 |
| `docs/P3_3C5_PREREGISTRATION_REVIEW.md` | No mention of E11 or the execution gates |
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION_DRAFT.md` | E11 first appears at line 730 |
| `sensory/input_scheduler.py` | `_values_at` 162–174; `apply` 176–183; active-feature masking 126–131 |
| `sensory/population_encoder.py` | `LanePopulation` one-hot encoding (3 × 4, amplitude, baseline) |
| `sensory/game_state.py` | `Lane`, `PlayerState`, `GameState` construction |
| `brain/brain_simulator.py` | `input_schedule` optional; `stimulus` optional; step loop and recording hook |
| `brain/neural_activity.py` | Spike timestamp `(step_index + 1) × dt_ms` |
| `configs/sensory_config.yaml` | Lane mapping, 200 pA, capacity 5,000,000 |
| `configs/simulation_config.yaml` | Zero background/noise; Phase 2 stimulus default must be disabled |
| `configs/neuron_config.yaml` | LIF parameters, rheobase context |

### 3.2 Independent verification

The source files above were read, and the E11 check was rerun independently of
the audit. The mismatch count, the mismatch set, E3, E8, E9, E16 and the
per-step nonzero counts all reproduce. No simulator was instantiated, no
connectome was read and no spike was generated.

---

## 4. Proposed replacement wording or deletion

### 4.1 A — E11

#### 4.1.1 Recommended disposition: withdraw, do not renumber

Replace the E11 row with an explicit withdrawal, and remove its other
references. Keeping the E12–E16 identifiers avoids renumbering every
cross-reference in the document, the tests and the audit.

**§11 table, line 769 — replace the E11 row with:**

> | E11 | **Withdrawn by the approved protocol amendment.** The crossfade is
> causal and one-sided; the C4 input-current vector is not required to equal
> the C3 vector at `600 − t`. Frame-sequence reversal is checked by E8, total
> current by E3, and the local crossfade formula by §14.4. See §5.7. |

**§5.7, lines 385–387 — replace item 7 with:**

> 7. **Crossfade construction (no reversal requirement).** In crossfade mode,
>    the C4 frame sequence is the exact reverse of the C3 frame sequence on
>    the 50 ms grid (E8), and the same §3.5 causal blend is applied after each
>    change. The injected vector at time `t` is not required to equal the C3
>    vector at `600 − t`; the one-sided ramp is not time-reversal
>    equivariant. Total current remains 800 pA (E3), and the `α = 0.5` local
>    check remains (§14.4).

**§12, lines 787–788 — replace the bullet with:**

> - A run whose causal decomposition (E16) fails is invalid.

**§14.5, lines 921–922 — replace step 2 with:**

> 2. Implement the runner/config/tests in a separate authorised task; verify
>    the applicable gates E1–E10 and E12–E16 on a smoke run. E11 is withdrawn.

**§3.5, after line 272 — add:**

> The blend is causal: it exists only after a change, never before it. As a
> consequence, the C4 input-current vector is not the time reverse of the C3
> vector, even though the C4 frame sequence is the reverse of the C3 frame
> sequence. No gate requires input-current reversal; E8 checks the frame
> sequences and E3 checks current conservation.

#### 4.1.2 What is preserved

- The causal scheduler (`sensory/input_scheduler.py` 162–174) is unchanged.
- E8 is unchanged.
- E3 is unchanged.
- The original C1–C4 stimuli are unchanged.
- The primary C1/C2 contrast and M6′ are unchanged.
- D3's crossfade block, its sequence list and its run count are unchanged.
- The run matrix remains 42 distinct runs per seed and 186 planned instances.

#### 4.1.3 Optional non-threshold construction check

If a direct runner check is wanted, add an optional gate that is not a
scientific threshold:

> **E11′ (construction).** For every crossfade run, at every grid time with an
> active schedule, the injected vector equals the §3.5 blend of the two
> adjacent frame vectors within `1e-9` pA; outside a 50 ms window it equals
> the current frame vector. This checks that the runner used the frozen
> crossfade formula; it does not compare C3 and C4 and does not gate the
> scientific outcome.

This check is optional. The proposal's default is to omit it, because the
runner is required to use the delivered scheduler and §14.4 already contains
the `α = 0.5` test. Adding it does not change any run, metric or claim.

### 4.2 B — E2

**§11 table, line 760 — replace the E2 row with:**

> | E2 | Stimulated set and per-step current. For every run with a lane
> schedule, `stimulated_indices` has exactly 12 entries (the `player_lane`
> population), all neurons outside that set receive 0 pA sensory current,
> `simulator.stimulus is None`, background = 0 and noise = 0. The number of
> neurons receiving nonzero sensory current at a step depends on the mode:
> 4 for `K_L`, `K_C`, `K_R` and every step-mode schedule; 4 or 8 during a
> crossfade (4 at `α = 0` and at/after the end of the 50 ms window, 8 for
> `0 < α < 1`); 0 for `N0`, which has no input schedule. Total injected
> sensory current is 800 pA at every step where a schedule is active (E3). |

**§5.3, lines 372–374 — append:**

> The 12-entry statement is a statement about the stimulated set, not about
> the number of neurons with nonzero current at a particular step. `K_C`
> drives four CENTER neurons; a crossfade drives four or eight neurons;
> `N0` has no schedule and drives none.

This preserves the no-leakage rule, the 12-index set, the 800 pA total and the
`stimulus=None` requirement. It removes the false per-step reading.

### 4.3 C — E10

**§11 table, line 768 — replace the E10 row with:**

> | E10 | Determinism. For the determinism subset — the step-mode runs of
> `C1`, `C2`, `C3` and `C4`, plus `N0` and `K_C` — each parent run is repeated
> once in a fresh subprocess. The parent and its repeat must produce identical
> input-schedule signatures and identical spike hashes; `N0` records an empty
> schedule signature. This is 6 conditions × 3 seeds = 18 repeat instances.
> With 126 main runs and 42 pilot runs, the planned total is 186 run
> instances. The repeat is a determinism check, not an independent replicate,
> and the two runs are not two samples. |

**§6.1, lines 405–407 — replace the second sentence with:**

> A second run in a fresh subprocess for the step-mode `C1`, `C2`, `C3` and
> `C4`, plus `N0` and `K_C`, is a determinism check, not an independent
> replicate.

This makes the mode explicit (step-mode C1–C4), which the 6-per-seed count
already implies: repeating both step and crossfade C1–C4 would be 8 + `N0` +
`K_C` per seed, not 6.

**§6.2 — no change.** The 18 repeats and 186 planned instances are correct
under this wording.

### 4.4 Supporting edits

**§15 — append two limitations after item 20:**

> 21. **The crossfade is causal, not time-symmetric.** The 50 ms blend ramps
>     only after a change. C3 and C4 crossfade input-current vectors are not
>     time reverses, and the crossfade C3/C4 contrast includes the ramp
>     asymmetry. It is a descriptive condition, not a matched reversal.
> 22. **Frame reversal is a 50 ms grid statement.** Even in step mode, the
>     C3/C4 input-current vectors are not exact time reverses at the three
>     transition instants under the half-open convention. E8 is the operative
>     reversal check; no continuous-time reversal is claimed.

**§3.2, after line 210 — optional clarification:**

> The reversal is a statement about the 50 ms frame sequence, not about the
> continuous-time input-current vectors. Under a causal crossfade the two
> differ.

### 4.5 Freeze record and amendment record

The historical freeze record should not be rewritten. After approval, the
amendment should be recorded in one of two ways, for the user to choose:

1. a new `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` containing the approved
   text, the old and new preregistration hashes, and the date; or
2. a clearly marked amendment appendix appended to the freeze record, leaving
   the original sections intact.

Either way, the amended preregistration gets a new SHA-256. The old hash
`1daa2439…8857` is superseded, not reused.

---

## 5. Impact on every affected experiment condition

The 42 distinct runs per seed are grouped below. "E11" means the withdrawn
gate; "E2" and "E10" mean the clarifications.

| Block | Runs/seed | Conditions | E11 impact | E2 impact | E10 impact |
|---|---|---|---|---|---|
| Core C1–C4, step | 4 | C1, C2, C3, C4 | none; E8 still checks frame reversal | per-step 4 neurons | step-mode C1–C4 are the determinism subset |
| C1, C2 crossfade | 2 | C1, C2 | none; E11 never applied to them | per-step 4 or 8 | none |
| C3, C4 crossfade | 2 | C3, C4 | no longer invalid by E11; subject to the other gates | per-step 4 or 8 | none |
| Additional crossfade | 4 | `C L R L`, `L C L R`, `R L C L`, `L R L C` | none; E11 never applied | per-step 4 or 8 | none |
| Constants | 3 | `K_L`, `K_C`, `K_R` | none | `K_C` is 4 per step, 12 in the set | `K_C` is in the determinism subset |
| No input | 1 | `N0` | none | 0 current, no schedule | `N0` is in the determinism subset |
| Linear 200 ms | 6 | `L C R` (C1), `R C L` (C2), `C L R`, `C R L`, `L R C`, `R L C` | none | per-step 4 | none |
| Closed 150 ms | 12 | C3, C4 and 10 non-focal arrangements | none | per-step 4 | none |
| Single-transition 200/400 | 6 | `L→C`, `R→C`, `L→R`, `C→R`, `R→L`, `C→L` | none | per-step 4 | E16 pairs C1/`L→C`, C2/`R→C` |
| Single-transition 150/450 | 6 | the same six routes | none | per-step 4 | none |

No condition is added, removed or redefined. The C3/C4 crossfade pair remains
confounded by transition-type order, per-time lane and now the ramp
asymmetry; it was already descriptive.

---

## 6. Impact on run counts

| Set | Before | After A+B | After C (recommended) | After C (alternative) |
|---|---|---|---|---|
| Main runs | 126 | 126 | 126 | 126 |
| Determinism repeats | 18 | 18 | 18 | 36 |
| Pilot runs | 42 | 42 | 42 | 42 |
| **Total** | **186** | **186** | **186** | **204** |

- A and B change no run count.
- C's recommended wording (one repeat per named step-mode run) preserves 18
  and 186, and matches §6.1 and §6.2.
- C's alternative (two fresh repeats) adds 18 repeat instances and changes
  the total to 204. That option requires editing §6.1, the §6.2 matrix and
  the `186` total; it is not recommended unless the user intends three runs
  per determinism condition.
- Failed attempts remain preserved and reported; no run is replaced.

---

## 7. Impact on scientific claims

### 7.1 Preserved without change

- The primary contrast P1 = `Δ_C(C1, C2)` in Hz, CENTER group, three
  state-relative bins, four neurons.
- M6′, its units, its bins and its sign convention.
- The main seeds 20261104/20261105/20261106 and the excluded pilot 20261107.
- The C1–C4 frame sequences, dwells, onsets and endpoints.
- The causal scheduler, its formula, its one-sided window and its current
  arithmetic.
- E3, E8, E9, E16 and the other unaffected gates.
- The descriptive, non-inferential reporting rule: no p-value, no
  significance claim, no confidence interval, no standard deviation with
  `n = 3`.
- The negative-result policy and the C3/C4 route/order caveats.

### 7.2 Changed

- The crossfade block is no longer described as a time-reversal-matched input
  pair. It is a descriptive condition under a causal filter.
- The sentence "C4 input-current vector equals C3 at `600 − t`" is removed
  from the protocol.
- The deterministic subset is stated as the step-mode C1–C4 plus `N0` and
  `K_C`, which the 6-per-seed matrix already implies.
- Two limitations are added: causal crossfade asymmetry and the frame-grid
  scope of reversal.

### 7.3 What can and cannot be claimed

**Can be claimed:**

- Under the configured model, the step-mode C1/C2 CENTER contrast is the
  primary descriptive result.
- The C3/C4 frame sequences are exact reverses on the 50 ms grid (E8).
- The crossfade applies the same causal blend after every change (E3,
  §14.4).
- The crossfade block reports whether the step-mode pattern persists under
  the configured smoothing, with the ramp as part of the condition.
- Every reported value is descriptive, with exact per-seed values and range.

**Cannot be claimed:**

- That the crossfade C3/C4 inputs are time mirrors.
- That the crossfade C3/C4 difference isolates order from the ramp.
- That C3 and C4 are perfectly matched; they differ in transition-type order
  and per-time lane, and the crossfade adds asymmetry.
- That three seeds establish generalisation or a population effect.
- That determinism is robustness.
- Any biological perception, learning or fly-lane-code claim.

### 7.4 The four distinctions the amendment must keep explicit

| Concept | Status |
|---|---|
| Time-reversed stimulus sequences | True for C2/C1 and C4/C3 on the 50 ms frame grid (E8) |
| Time-reversed input-current vectors | True in step mode except at the three transition instants; false under the causal crossfade |
| Causal scheduler behaviour | One-sided ramp after each change; `previous` is the outgoing lane; `α = 0` still carries the outgoing lane |
| Descriptive C3/C4 route/order comparison | C3 and C4 differ in transition-type order and per-time lane; any difference includes those differences and, in crossfade mode, the ramp asymmetry |

---

## 8. Remaining limitations

The 20 limitations in §15 remain. Two are added:

21. **The crossfade is causal, not time-symmetric.** The blend ramps only
    after a change; the C3/C4 crossfade inputs are not time reverses. The
    crossfade C3/C4 contrast includes the ramp asymmetry and is descriptive.
22. **Frame reversal is a 50 ms grid statement.** Even in step mode, the
    input-current vectors are not exact reverses at the three transition
    instants. E8 is the operative check; no continuous-time reversal is
    claimed.

These are properties of the frozen design, not defects to be corrected. They
must appear in the final report if the experiment is later executed.

A documentation observation, not part of A/B/C: the freeze record's §4 lists
18 remaining limitations, while the preregistration §15 has 20 numbered
items. This proposal does not change either list; if the user wants the
amendment record to reconcile the counts, that can be added separately.

---

## 9. Before/after amendment table

| Location | Before (frozen) | After (proposed) | Type |
|---|---|---|---|
| §11 E11 row (769) | Crossfade reversal at `1e-9` pA on the simulation grid | E11 withdrawn; frame reversal via E8, current via E3, local blend via §14.4 | Withdrawal |
| §5.7 item 7 (385–387) | C4 vector equals C3 at `600 − t` | C4 frame sequence is the reverse; no input-current reversal requirement | Withdrawal |
| §12 bullet (787–788) | Invalid if E16 **or E11** fails | Invalid if E16 fails | Consequential edit |
| §14.5 step 2 (921–922) | Verify E1–E16 | Verify E1–E10 and E12–E16; E11 withdrawn | Consequential edit |
| §3.5 (after 272) | No statement on reversal | Add: the blend is causal; input-current reversal is not claimed | Clarification |
| §11 E2 row (760) | "Exactly 12 neurons receive nonzero current" | Set-level 12 indices; per-step 4 (step/constant), 4 or 8 (crossfade), 0 (`N0`) | Clarification |
| §5.3 (372–374) | 12 stimulated neurons | Append the set-level versus per-step distinction | Clarification |
| §11 E10 row (768) | Parent plus two fresh-subprocess runs | Parent plus one repeat; step-mode C1–C4, `N0`, `K_C`; 18 repeats; 186 total | Correction |
| §6.1 (405–407) | "A second run" | State "step-mode C1–C4" explicitly | Clarification |
| §6.2 (415–426) | 18 repeats, 186 total | Unchanged under the recommended E10 wording | No change |
| §15 (after 997) | 20 limitations | Add 21 (causal crossfade) and 22 (frame-grid reversal) | Addition |
| D1–D10 | As frozen | Unchanged | No change |
| C1–C4 stimuli | As frozen | Unchanged | No change |
| M6′ | As frozen | Unchanged | No change |
| Seeds | As frozen | Unchanged | No change |
| Scheduler | As frozen | Unchanged | No change |
| E1, E3–E9, E12–E16 | As frozen | Unchanged | No change |
| Run matrix | 42/seed, 126 + 18 + 42 = 186 | Unchanged (recommended C) | No change |
| Preregistration hash | `1daa2439…8857` | New SHA-256 after the approved edit; old hash superseded | Required |

---

## 10. Explicit user decisions still required

1. **E11 disposition.** Approve withdrawal with the E12–E16 identifiers kept
   (recommended), or approve deletion with renumbering of E12–E16. Renumbering
   changes every cross-reference and is not recommended.
2. **Optional E11′.** Approve or decline the non-threshold construction check
   in §4.1.3. The default is to decline; E8, E3 and the §14.4 test already
   cover the relevant runner errors.
3. **E2 wording.** Approve the replacement text in §4.2, including the
   per-step counts of 4 (step/constant), 4 or 8 (crossfade) and 0 (`N0`).
4. **E10 wording.** Choose the one-repeat option (recommended; 18 repeats,
   186 total, matches §6.1/§6.2) or the two-repeat option (36 repeats, 204
   total, requires matrix edits). Also approve stating that the determinism
   subset is the step-mode C1–C4.
5. **Supporting edits.** Approve the §3.5 causal sentence and the two new
   §15 limitations (21–22).
6. **Amendment record.** Choose a new
   `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` or an amendment appendix to the
   freeze record. The historical freeze record should not be rewritten.
7. **Authorisation.** Authorise the edit to the frozen preregistration, the
   computation and recording of the new SHA-256, and the amendment record.
   This does not authorise implementation or execution; those remain
   separate.
8. **No other changes.** Confirm that no other protocol text, stimulus,
   metric, seed, run count or scheduler behaviour is to change.

After these decisions, the amended preregistration can be issued with a new
hash. Implementation would then require a fresh implementation authorisation
under the task rules, and execution a further separate authorisation.

---

## 11. Integrity of this proposal

- No implementation code was written.
- No scheduler code was modified.
- No configuration was modified.
- No simulation was run.
- No experiment result was generated or modified.
- `README.md`, the connectome, the frozen preregistration, the freeze record,
  the implementation audit and all Phase 3–6 artifacts are unchanged.
- No file was staged, committed, pushed, reset, cleaned, stashed, checked out,
  deleted or overwritten.
- The only file created by this task is this proposal.

The independent check described in §2.4 instantiated the encoder and input
scheduler in memory only. It read no connectome, instantiated no
`BrainSimulator`, generated no spikes and wrote no file.

The SHA-256 of this proposal is recorded in the delivery message, not inside
the file, because a file cannot contain its own hash.
