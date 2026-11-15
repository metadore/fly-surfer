# Phase 3 — remaining work packages P3-3C.6 and P3-3C.8

Generated: 2026-11-15
Repository HEAD: `62a64309cadc0db7353c856607cee5369993bd65`
Branch: `main`
Working tree before this report was written: 233 `git status --porcelain`
entries — 21 modified tracked files (all pre-existing in this session) and 212
untracked, 0 staged.
Role: requirement traceability and stop report. **No implementation was
performed.** No experiment was run. No dataset, model, config, result or
frozen P3-3C.5 artifact was modified.

---

## 0. Executive summary

| Work package | Verdict | Reason (one line) |
|---|---|---|
| **P3-3C.6** — jump and roll onset/offset intervals | **NEEDS DESIGN CLARIFICATION** (synthetic path); **BLOCKED** (perceived-scene path) | The six conditions, onset/duration/offset values, definition of "transient", frame-grid semantics and seed plan are all unspecified; perceived jump/roll are unobservable. |
| **P3-3C.8** — T1 vs T2 vs T3 encoding ablation | **BLOCKED** | T2 and T3 do not exist in code; `tau_enc`, the T3 specification, the mapping extension, the equivalence tests, the "same sequences" set and the primary separability contrast are undefined. |
| **Phase 3C** | **NOT ACCEPTED** | P3-T7 decision-rule criterion 3 fails (approach vs retreat d′ = 0.0), 3C.5/3C.6/3C.8 remain unexecuted, and the roadmap acceptance sentence is not satisfied. |

The brief's stop condition is met: **"Original acceptance criteria cannot be
established."** Neither work package has an individual acceptance criterion in
any authoritative document, and the elements required to construct one are
absent. Implementing either package would require inventing condition
enumerations, filter parameters, a T3 edge specification, a neuron/current
budget and a separability metric. That is prohibited by Step 1 ("Do not infer
requirements from package names or later experimental extensions") and Step 3
("Do not implement requirements whose meaning or acceptance criteria are
ambiguous"). No PASS was forced.

---

## 1. Original requirement traceability

### 1.1 Source hierarchy and precedence

| Rank | Source | SHA-256 | Role |
|---|---|---|---|
| 1 | `docs/PHASE_3_ROADMAP.md` §4.4, lines 244–327 | `ab6d3e66f1c84946c44a94c9d6519f4d04a4419a0fdd82d046d035bee00c29e5` | Milestone objective, protocol, metrics, acceptance sentence |
| 2 | `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` | The only 3C experiment definition; explicitly *proposed* |
| 3 | `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md` | `b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7` | Prior audit; records what the original text does **not** define |
| 4 | `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` | Executed P3-T7 matrix; explicit `not_executed` list |
| 5 | `experiments/phase_3c/results/p3_final_phase3_audit.md` | `f813ed605ecf65fd7a4d302ebd62700f73254a7decbe9664f9403841f1ac1047` | Task-level verdicts P3-T2…P3-T12 |

There is **no pre-existing Phase 3C specification**. The roadmap states the
definition "is proposed because no prior 3C specification exists"
(`docs/PHASE_3_ROADMAP.md:247–248`). The design document is therefore a
proposal, not a frozen, accepted requirement set. The only frozen artifacts in
the 3C area are the P3-3C.5 preregistration and the P3-T2/T3/T12 protocols;
none of them defines 3C.6 or 3C.8.

### 1.2 P3-3C.6 — verbatim requirement

**Roadmap (§4.4, line ~270).** Experiments cover "jump/roll intervals" within
the 3C.1–3C.9 list; acceptance is the milestone sentence in §4.4 (see §1.4).

**Design experiment row** (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md:246`):

| ID | Comparison | Purpose | Conditions |
|---|---|---|---|
| 3C.6 | Jump and roll onset/offset intervals | Transient response to discrete events | 6 |

**Design data-availability row** (`...TEMPORAL_SENSORY_DESIGN.md:93`):

| Quantity | Definition from available data | Status |
|---|---|---|
| Jump / roll interval | Boolean onset, duration in ms, offset | Available |

**What the original text does define**

- The data source is `GameState`: `jumping` and `rolling` are Boolean player
  fields (`sensory/game_state.py:89–98`), mutually exclusive — "player cannot
  jump and roll in the same state" (`sensory/game_state.py:98`).
- Each is a 6-neuron mechanosensory feature at 200 pA
  (`configs/sensory_config.yaml:45–57`, `183–188`;
  `sensory/sensory_experiment.py:45–59`).
- The protocol context is 600 ms synthetic sequences, zero background, zero
  noise, 200 pA, `sigma_fraction` 0.20 (`...TEMPORAL_SENSORY_DESIGN.md:221–262`;
  roadmap §4.4 "Protocol").
- The general metric list is activation-trajectory range, event transients,
  windowed spike counts, latency, peak time, response duration, `d′`, cosine /
  nearest-centroid separability, runtime, memory and hashes
  (`...TEMPORAL_SENSORY_DESIGN.md:276–305`).
- The purpose is "transient response to discrete events" and there are **6**
  conditions.
- Persistence rule: a feature that leaves view must produce an explicit decay
  or OFF event, silence must not be confused with presence, and each run
  constructs a fresh encoder (`...TEMPORAL_SENSORY_DESIGN.md:212–219`).

**What the original text does not define** (also recorded by the prior audit
at `...REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:130–178`, `514–527`, `633–683`,
`818–830`, `980–1003`)

1. The six conditions. No enumeration exists anywhere.
2. Onset times, durations and offsets. The word "intervals" is never
   instantiated.
3. The mechanism meant by "transient": LIF step response, T5 event pulse, or
   T3 ON/OFF phasic channel. These are three different experiments.
4. Frame-grid semantics: whether events must land on the 50 ms grid and how
   off-grid onsets are reported.
5. Explicit `active_features` policy for the whole run. The current builder
   adds `jumping`/`rolling` only if the *initial* state is true
   (`sensory/sensory_experiment.py:156–171`), so a jump starting at frame *k*
   is masked to zero unless the feature is forced active.
6. Controls, window definitions, seed plan beyond the general "single mapping
   seed" note (`...REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:130–178`).
7. Whether the experiment is synthetic-only or must include perceived scenes.
8. A jump/roll lifecycle event. `Lifecycle` has only
   `APPEARED/APPROACHING/RECEDING/DISAPPEARED` (`perception/temporal.py:50–55`)
   and `PULSE_EVENTS` contains only appeared/approaching/receding
   (`perception/temporal.py:70–72`), so no jump/roll pulse can be emitted by
   the existing scheduler.
9. Any numeric acceptance threshold specific to 3C.6.

### 1.3 P3-3C.8 — verbatim requirement

**Design experiment row** (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md:248`):

| ID | Comparison | Purpose | Conditions |
|---|---|---|---|
| 3C.8 | Encoding ablation: T1 vs T2 vs T3 on the same sequences | Whether temporal encoding changes separability | 9 |

**Design representation table** (`...TEMPORAL_SENSORY_DESIGN.md:138–142`):

| ID | Representation | How it maps onto current code | Extra mapping neurons | Cost |
|---|---|---|---|---|
| T1 | Step + linear crossfade | Existing `SensoryInputScheduler(transition_ms=...)` | None | Already implemented |
| T2 | First-order smoothing of activations | Exponential low-pass on encoded activations with time constant `tau_enc` | None | Small CPU |
| T3 | Onset / offset (phasic) channels | Rising and falling activation changes drive separate ON and OFF sub-populations | Yes, doubles affected features | Medium |

**Design status table** (`...TEMPORAL_SENSORY_DESIGN.md:122–135`):
T1 implemented; **T2 not implemented; T3 not implemented**; T5 partially
implemented (lifecycle pulses only). Line 133–134 states explicitly that the
scheduler "does **not** implement T2 low-pass smoothing or T3 ON/OFF
sub-populations, and the 3C.8 T1/T2/T3 ablation has not been run."

**Design delivery rules** (`...TEMPORAL_SENSORY_DESIGN.md:175–198`):

- Two delivery options are proposed. Option 1 (timeline expansion) must not be
  used for exact T2, because "interpolating game states is not the same as
  filtering activations".
- Option 2 (activation scheduler) must be a class with the same
  `apply(step, time_ms, current_pa)` signature, built from precomputed
  per-feature activation trajectories and existing `SensoryMapping` indices,
  containing no neuron, synapse or time-step logic.
- Additive injection only; same `stimulated_indices` contract; deterministic
  `signature()`.
- **Equivalence test**: "with `tau_enc → 0` and no phasic channels, T2
  reproduces T1 exactly (same input hash) on a fixed sequence"
  (`...TEMPORAL_SENSORY_DESIGN.md:197–198`).

**What the original text does not define** (prior audit
`...REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:179–241`, `528–545`, `684–748`,
`831–847`)

1. Which sequences are "the same sequences". This depends on 3C.5 and 3C.6,
   both unexecuted/undefined.
2. The nine-condition matrix.
3. `tau_enc` value, units and whether a tau grid is required.
4. The full T3 specification: edge threshold, sign convention, gain, decay,
   ON/OFF symmetry, and whether ON and OFF share neurons.
5. The mapping extension for T3. T3 "doubles affected features", so the
   mapping must allocate new neurons and a capacity check is required.
6. The current/neuron budget policy. T3 changes total injected current and
   neuron count, so a difference cannot be attributed to "temporal encoding"
   alone without a normalization rule.
7. The primary separability contrast and metric ("separability" is ambiguous:
   `d′`, cosine, nearest-centroid, or a trajectory distance).
8. The T3 zero-gain equivalence/control test.
9. The seed plan and whether the T7 thresholds (d′ = 1.0, cosine 0.01) are
   re-approved.
10. Any numeric acceptance criterion specific to 3C.8.

### 1.4 Shared acceptance context

The roadmap acceptance sentence (`docs/PHASE_3_ROADMAP.md`, §4.4 "Acceptance")
requires, among other things:

- a causal deterministic encoder with explicit timestamps and a defined zero
  state;
- a static-equivalence test that passes;
- approach vs retreat separating above seed spread in at least two of three
  seeds **or** being reported as a negative result;
- onset/offset/persistence measured;
- frame-rate sensitivity quantified with an aliasing limit;
- simulator and 3A interfaces unchanged, all existing tests pass, sparse
  full-graph only, negative results not reframed.

P3-T7 executed the decision rule for 3C.1–3C.4, 3C.7 and 3C.9 (23 conditions)
and returned `NEGATIVE_RESULT`; criterion 3 (approach vs retreat) fails with
d′ = 0.0 and 460/460 spikes
(`experiments/phase_3c/results/temporal_acceptance.json`,
`4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc`).
3C.5, 3C.6 and 3C.8 are explicitly excluded from that matrix and described as
"characterize the encoder rather than the milestone decision rule"
(`configs/temporal_sensory.yaml:62–69`).

**No document assigns 3C.6 or 3C.8 a standalone pass/fail criterion.** They
are condition rows in a proposed matrix. A "PASS" for either cannot be
constructed without inventing the missing definitions.

---

## 2. Initial implementation status

Classification vocabulary: **COMPLETE** / **COMPLETE WITH LIMITATIONS** /
**IMPLEMENTATION REQUIRED** / **EVIDENCE REQUIRED** / **BLOCKED** /
**AMBIGUOUS**. A row is marked BLOCKED when the missing element is a
definition or unavailable dependency, not merely unwritten code.

### 2.1 P3-3C.6

| # | Original requirement | Implementation | Test | Result | Missing work | Classification |
|---|---|---|---|---|---|---|
| 6.1 | `jumping` and `rolling` Boolean features, 6 neurons, 200 pA | `configs/sensory_config.yaml:45–57`, `183–188`; `sensory/sensory_experiment.py:45–59` | `tests/test_sensory_experiment.py`, `tests/test_game_state.py` | Static True/False conditions build correctly | None | **COMPLETE** |
| 6.2 | Mutual exclusivity of jump and roll | `sensory/game_state.py:89–98` raises `ValueError` | `tests/test_game_state.py` | Enforced | None | **COMPLETE** |
| 6.3 | Boolean interval representation (onset, duration, offset) | None; only static schedules exist | — | — | Interval sequence builder | **IMPLEMENTATION REQUIRED** (definition absent) |
| 6.4 | Six-condition enumeration | None | — | — | Conditions, times, durations, offsets | **AMBIGUOUS** |
| 6.5 | "Transient response to discrete events" | T5 pulses exist only for `APPEARED/APPROACHING/RECEDING` (`perception/temporal.py:70–72`); no jump/roll event; T3 absent | `tests/test_temporal_scheduler.py` (other events only) | Jump/roll produce no pulse | Choice of mechanism; event layer | **AMBIGUOUS** |
| 6.6 | Explicit `active_features` for the whole run | `_active_for_payload` adds jump/roll only if initially true (`sensory/sensory_experiment.py:156–171`) | `tests/test_sensory_experiment.py` | A mid-sequence jump would be masked | Interval-aware activation policy | **IMPLEMENTATION REQUIRED** (definition absent) |
| 6.7 | Runner, metrics, tests | None | — | — | Runner + per-condition metrics | **IMPLEMENTATION REQUIRED** (blocked by 6.4–6.6) |
| 6.8 | Perceived-scene version | Not possible: v15 has no player/jump/roll class; `build_state` defaults them false; C3 jump/roll ablations changed 0 spikes | — | Unobservable | New annotations / observability | **BLOCKED** |

### 2.2 P3-3C.8

| # | Original requirement | Implementation | Test | Result | Missing work | Classification |
|---|---|---|---|---|---|---|
| 8.1 | T1 step + linear crossfade | `sensory/input_scheduler.py:33`, `45`, `162–174`, `176`, `221` | `tests/test_input_scheduler.py` | Works; used as 3A control | None | **COMPLETE** |
| 8.2 | T2 exponential low-pass on encoded activations | None | — | — | Class, `tau_enc`, trajectory precomputation | **BLOCKED** (parameter undefined) |
| 8.3 | T3 ON/OFF phasic sub-populations | None | — | — | Edge detector, sub-populations, mapping extension | **BLOCKED** (specification undefined) |
| 8.4 | Mapping capacity check for doubled features | Mapping exists and checks capacity for current features (`sensory/sensory_mapping.py`) | `tests/test_sensory_mapping.py` | Works for existing features only | T3 allocation policy | **BLOCKED** (budget undefined) |
| 8.5 | T2 equivalence test (`tau_enc → 0` ⇒ same input hash as T1) | Cannot exist without T2 | — | — | T2 first | **BLOCKED** |
| 8.6 | T3 zero-gain/control equivalence | Not specified anywhere | — | — | Definition | **AMBIGUOUS** |
| 8.7 | "Same sequences" set | None | — | — | Depends on 3C.5/3C.6 | **AMBIGUOUS** |
| 8.8 | Nine-condition matrix | None | — | — | Matrix | **AMBIGUOUS** |
| 8.9 | Primary separability contrast and metric | None | — | — | Metric + threshold | **AMBIGUOUS** |
| 8.10 | Current/neuron budget normalization | None | — | — | Per-condition budget rule | **AMBIGUOUS** |
| 8.11 | Runner and tests | None | — | — | Runner | **IMPLEMENTATION REQUIRED** (blocked by 8.2–8.10) |

**Summary.** For 3C.6, the only complete pieces are the input features and
their mutual-exclusivity validation; everything that constitutes the
experiment is missing or undefined. For 3C.8, T1 is complete; T2 and T3 — the
two arms that define the ablation — do not exist, and the mapping/budget
consequences of T3 are unresolved.

---

## 3. Files inspected

| Path | SHA-256 | Why inspected |
|---|---|---|
| `docs/PHASE_3_ROADMAP.md` | `ab6d3e66f1c84946c44a94c9d6519f4d04a4419a0fdd82d046d035bee00c29e5` | Milestone objective, protocol, metrics, acceptance, dependency table |
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` | Authoritative (proposed) 3C.6/3C.8 rows, T1/T2/T3 definitions, delivery and equivalence rules |
| `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md` | `b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7` | Prior audit of 3C.5/6/8 requirements, dependencies, confounds, verdicts and 13 required decisions |
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` | Executed P3-T7 matrix; `not_executed` list at lines 62–69 |
| `configs/sensory_config.yaml` | `26d782a3b5910c05d433fa6678557f7c806dc9947ee8ad279e246fa34f4e96db` | Jump/roll feature definitions, amplitudes, mapping |
| `perception/temporal.py` | `ed4b3de1f1c92edb81237b76d4b764aaceb876c74c83826dbfb1764531f91421` | `Lifecycle` enum and `PULSE_EVENTS` — no jump/roll event |
| `sensory/temporal_scheduler.py` | `3be4ac9a7f04749cfcacdb62c47c254114e601579fd94b6ebc0f66ac3020641c` | T5-style sample-and-hold/pulse scheduler; confirms no T2/T3 |
| `sensory/input_scheduler.py` | `223bce3738ac02f6f8de736209158df7aafa639cf1f05d9791f559a500e5cc07` | T1 crossfade implementation and `apply` contract |
| `sensory/sensory_experiment.py` | `01777500994b906bb026779aa6805c926f27250581405a7a6678df92293a6ef1` | Feature families; `_active_for_payload` masking behaviour |
| `sensory/game_state.py` | `2562617f978c145af82ce8707210de577318de04c6749994df1edac078c7bb43` | Jump/roll Boolean schema and mutual exclusion |
| `sensory/sensory_mapping.py` | `c655c14a7831a968d56c0e5dc7f5dc85e4d6170118e6439caaa0999d3755aaa8` | Deterministic allocation and capacity checks |
| `sensory/population_encoder.py` | `9b4594255935ef950ac639f24580dc85e174f54b95cc913addc2103b8b582134` | Encoding rates/activations used by schedulers |
| `experiments/phase_3c/temporal_acceptance.py` | `41f4b09effbed172502bcd06c8abc32f879b2a0168ced20bf0ec09838adc0543` | P3-T7 runner; limitations at lines 80–100 |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` | Frozen P3-3C.5 runner; line 203: "T2/T3 encodings are out of scope" |
| `experiments/phase_3c/results/temporal_acceptance.json` | `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc` | P3-T7 verdict and decision-rule items |
| `experiments/phase_3c/results/temporal_acceptance_report.md` | `610fc44e2b2ff02f66f7b96451b34916ad44ed95fe5ffd9304117ffb4824942c` | Human-readable P3-T7 result |
| `experiments/phase_3c/results/p3_final_phase3_audit.md` | `f813ed605ecf65fd7a4d302ebd62700f73254a7decbe9664f9403841f1ac1047` | Task-level verdicts and milestone matrix |
| `reports/P3_3C5_PILOT_EXECUTION_REPORT.md` | `20ca5c774092447c306806b85ef606bbc066e951e007fcfd5956a0a69effcc2d` | Frozen P3-3C.5 pilot outcome (FAIL) — context for "same sequences" |
| `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` | `e4f093ea41fbf5a44cf7fc5972521be372c009f0009a4d60d694ea12bb6a2017` | Prior work package audit in this session; unmodified |
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | Protected artifact integrity |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | Protected artifact integrity |

---

## 4. Files created or modified

| Path | Action |
|---|---|
| `reports/PHASE3_P3_3C6_3C8_COMPLETION_REPORT.md` | **Created** — this report |

No other file was created, modified or deleted. Specifically:

- No source file, config, test, dataset, model weight or result artifact was
  changed.
- Frozen P3-3C.5 artifacts (`reports/P3_3C5_*`,
  `experiments/phase_3c/results/p3_3c5_*`, the frozen preregistration) were
  read only.
- `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` remains byte-identical at
  `e4f093ea41fbf5a44cf7fc5972521be372c009f0009a4d60d694ea12bb6a2017`.
- `README.md` and `datasets/processed/connectome.npz` are unchanged.
- Nothing was staged, committed, pushed, reset, cleaned or stashed.

---

## 5. Tests executed and results

Environment: Python 3.13.14 (64-bit), pytest, repository HEAD
`62a64309cadc0db7353c856607cee5369993bd65`.

### 5.1 Focused temporal and sensory regression tests

```
python -m pytest tests/test_temporal.py tests/test_temporal_scheduler.py \
  tests/test_temporal_acceptance.py tests/test_game_state.py \
  tests/test_input_scheduler.py tests/test_sensory_experiment.py \
  tests/test_sensory_mapping.py tests/test_population_encoder.py -q
```

Result: **81 passed, 0 failed** in 3.01 s.

```
python -m pytest tests/test_temporal_calibration.py tests/test_tracking.py -q
```

Result: **24 passed, 0 failed** in 1.97 s.

### 5.2 Full suite (regression, no campaign)

```
python -m pytest -q
```

Result: **916 passed, 3 skipped, 0 failed** in 192.39 s.

The 3 skips are pre-existing platform/dependency skips, not new. This run
executed unit and integration tests only; it did not run the P3-3C.5 pilot,
main or determinism campaign, did not execute the 3C.6/3C.8 protocols (none
exist), and did not produce new research evidence.

### 5.3 What was not run

- No P3-3C.5 pilot, main or determinism campaign.
- No new 3C simulation, no 600 ms condition sweep, no connectome subgraph run
  beyond what the existing test suite already performs.
- No ONNX inference, no detector evaluation.
- No modification of any frozen artifact.

---

## 6. Evidence generated

**None experimental.** This work package produced no simulation output, no
metric, no hypothesis test and no condition result.

| Evidence type | Generated | Note |
|---|---|---|
| 3C.6 conditions | No | No condition enumeration exists to execute |
| 3C.8 T1/T2/T3 comparison | No | T2/T3 not implemented |
| New spike data | No | No simulation performed for this task |
| Test results | Yes | 916 passed / 3 skipped full suite; 105 focused |
| Integrity verification | Yes | Hashes in §3 and §10; git counts in §4 and §10 |

No evidence was manufactured, synthesized or substituted for the missing
experimental evidence. The absence of 3C.6/3C.8 results is reported as a
result of this audit.

---

## 7. Remaining blockers

### 7.1 Decisions required before 3C.6 can be implemented

From `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:980–1003`
(decisions 4–6 and shared 12–13):

4. Is the experiment synthetic-only, or must it use perceived scenes? If
   perceived, it is blocked.
5. Does "transient" mean LIF step response, T5 event pulse, or T3 phasic
   channel?
6. What are the six conditions and the exact intervals (onset, duration,
   offset)?
12. Is the original single-seed plan retained, or is a three-seed mapping
    extension approved?
13. Are the T7 thresholds (`d′ = 1.0`, cosine `0.01`) approved as new
    operationalizations, or is the result descriptive only?

Additional blockers:

- No jump/roll lifecycle event exists (`perception/temporal.py:50–55`,
  `70–72`). The scheduler cannot emit a jump/roll pulse.
- No Boolean-interval sequence builder and no interval-aware
  `active_features` policy (`sensory/sensory_experiment.py:156–171`).
- Perceived jump/roll are unobservable in the current dataset and replay
  pipeline; the C3 jump/roll ablation changed 0 spikes for this reason
  (prior audit `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:365–401`).
- No per-condition window definition for onset latency, peak and offset
  cessation.

### 7.2 Decisions required before 3C.8 can be implemented

From the same list (decisions 7–13):

7. Which sequences are "the same sequences"? Depends on 3C.5/3C.6.
8. What is the nine-condition matrix?
9. What is `tau_enc`, and is a tau grid required?
10. What is the full T3 specification (edge threshold, sign, gain, decay,
    mapping extension)?
11. What is the primary separability contrast and metric?
12. Single seed or three mapping seeds?
13. Are the T7 thresholds approved or is the result descriptive only?

Additional blockers:

- T2 and T3 do not exist (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md:125–127`;
  `sensory/temporal_scheduler.py` implements hold + pulses, not low-pass or
  phasic channels).
- T3 "doubles affected features" (`...TEMPORAL_SENSORY_DESIGN.md:140`) and
  requires extra mapping neurons; the capacity and current budget are
  unspecified. Implementing T3 could change the neuron count for existing
  features and therefore threaten evidence comparability with 3A/3C.1–3C.4.
- No T2 equivalence test can be written until T2 exists; no T3 control is
  specified.
- 3C.5 is unexecuted and its pilot failed on 2026-11-15
  (`reports/P3_3C5_PILOT_EXECUTION_REPORT.md`), so the "same sequences" input
  to 3C.8 is not established.

### 7.3 Dependency chain

```
3C.5 (unexecuted; pilot FAIL) ──┐
3C.6 (unexecuted) ──────────────┼──> "same sequences" for 3C.8
jump/roll event layer (missing) ┘

T2 (missing, tau_enc undefined) ──┐
T3 (missing, spec undefined) ─────┼──> 3C.8 ablation
mapping/budget policy (undefined) ┘
```

---

## 8. Limitations

1. **The definition is proposed, not accepted.** The roadmap says no prior 3C
   specification exists (`docs/PHASE_3_ROADMAP.md:247–248`). Any requirement
   traceability in this report therefore cites a proposal. This is a
   limitation of the project state, not of this audit.
2. **Repository documentation is stale.** The roadmap says the 3C.1–3C.9
   experiments "have **not** been run" (`docs/PHASE_3_ROADMAP.md:322–327`) and
   the design says "none of the 3C.1–3C.9 conditions has been run"
   (`docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md:258–262`). P3-T7 actually
   executed 23 conditions covering 3C.1–3C.4, 3C.7 and 3C.9. This report
   records the inconsistency; it does not edit the stale documents. The prior
   audit noted the same inconsistency
   (`docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:432–451`).
3. **The P3-T7 negative result stands.** Approach vs retreat remains d′ = 0.0
   with 460/460 spikes. 3C.6/3C.8 are explicitly encoder characterization and
   cannot rescue the milestone decision rule
   (`configs/temporal_sensory.yaml:62–69`; prior audit §8).
4. **3C.8 is not a single-factor ablation.** T1, T2 and T3 differ in scheduler
   class, filter state, neuron count, total injected current, mapping and
   input-side trajectory. Even if implemented, a separability difference could
   not be attributed to "temporal encoding" alone (prior audit §6.3).
5. **T3 carries an evidence-comparability risk.** Doubling affected features
   changes the neuron set and input budget. Implementing it without an
   approved budget and mapping policy could invalidate comparisons with
   existing 3A/3C evidence; this is why it was not attempted.
6. **Single-seed limitation.** The original 3C.6 plan is single-seed. One
   mapping realization is one draw of the mechanosensory allocation, and the
   3A.5 calibration already showed threshold-sensitive, mapping-dependent
   behaviour.
7. **No standalone acceptance criterion exists.** "PASS" for 3C.6 or 3C.8 is
   undefined by any authoritative text. This report does not invent one.
8. **This audit is documentary.** No simulation was run for this task, so the
   implementation status reflects code inspection and the existing test
   suite, not new runtime behaviour.

---

## 9. Final verdict for each work package

### 9.1 P3-3C.6 — jump and roll onset/offset intervals

**NEEDS DESIGN CLARIFICATION** for the synthetic path; **BLOCKED** for the
perceived-scene path.

- The input features exist and are tested; the mutual-exclusion rule is
  enforced.
- The experiment itself is undefined: no six-condition enumeration, no
  intervals, no definition of "transient", no event layer, no interval-aware
  activation policy, no runner, no criterion.
- Perceived jump/roll cannot be observed in the current dataset or replay
  pipeline.
- Implementing it now would require inventing the design; this was not done.

### 9.2 P3-3C.8 — T1 vs T2 vs T3 encoding ablation

**BLOCKED.**

- T1 exists and is tested.
- T2 and T3 do not exist. `tau_enc`, the T3 edge/gain/decay specification,
  the mapping extension, the capacity/current budget, the equivalence tests,
  the "same sequences" set, the nine-condition matrix and the separability
  metric are all undefined.
- Implementing T3 without an approved budget/mapping policy risks invalidating
  existing evidence, which the brief forbids.
- No implementation was attempted.

### 9.3 Phase 3C

**NOT ACCEPTED.** P3-T7 criterion 3 fails, 3C.5/3C.6/3C.8 are unexecuted and
this report does not change any of them. The milestone acceptance sentence is
not satisfied.

---

## 10. Updated Phase 3 completion matrix

### 10.1 Task-level matrix

P3-T1 is excluded: it has no task definition, protocol or artifact anywhere in
the repository and is not counted by the prior final audit
(`experiments/phase_3c/results/p3_final_phase3_audit.md:17`).

| Task | Criterion (abridged) | Verdict | Source of verdict |
|---|---|---|---|
| P3-T2 | Four same-graph conditions C0–C3; 11 invalidation rules; archive gate; subprocess repeats | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:51` |
| P3-T3 | 15-condition one-factor feature ablation; archive gate; contrasts | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:52` |
| P3-T3.1 | Additive ignition reclassification; raw payload unmodified | **COMPLETE** | `p3_final_phase3_audit.md:53` |
| P3-T4 | Explain the 4-vs-12 neuron discrepancy from archives | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:54` |
| P3-T5 | Frozen test split; measured detection/classification/localisation/distance errors | **BLOCKED** | `p3_final_phase3_audit.md:55`; `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` §10 |
| P3-T6 | Per-class P/R, mAP@0.5, classification, IoU, centre error, lane, distance | **PARTIALLY COMPLETE** | `p3_final_phase3_audit.md:56`; `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` §10 |
| P3-T7 | 3C decision rule 1–5 and acceptance sentence | **PARTIALLY COMPLETE** — 23 conditions; criterion 3 fails | `p3_final_phase3_audit.md:57` |
| P3-T8 | Deterministic replay and reproducibility hashes | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:58` |
| P3-T9 | p95 ≤ 50 ms if achievable, else report measured | **COMPLETE WITH LIMITATIONS** — 153.463 ms | `p3_final_phase3_audit.md:59` |
| P3-T10 | No unsupported feature claim; provenance labelling | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:60` |
| P3-T11 | Valid `GameState`; 3A interface unchanged; unrepresented objects reported | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:61` |
| P3-T12 | Eight pre-registered criteria; equivalence; 7 conditions × 2 repeats; invalidations | **COMPLETE WITH LIMITATIONS** | `p3_final_phase3_audit.md:62` |

Task summary: **1 complete, 9 complete with limitations, 2 partially complete,
1 blocked.** The two new work packages add no change to this summary.

### 10.2 Condition-level matrix

| Condition | Definition | Executed | Result | Verdict |
|---|---|---|---|---|
| 3C.1 | Constant sequence vs static schedule; T1 equivalence | Yes (P3-T7) | 0.0 pA differences; equivalence passes | **COMPLETE (executed)** |
| 3C.2 | Approach vs retreat, matched endpoints | Yes (P3-T7) | Negative: d′ = 0.0 in all seeds; 460/460 spikes | **EXECUTED — NEGATIVE RESULT** |
| 3C.3 | Entry timing 100/200/300 ms | Yes (P3-T7) | Measured | **COMPLETE (executed)** |
| 3C.4 | Exit timing 200/400 ms | Yes (P3-T7) | Measured | **COMPLETE (executed)** |
| 3C.5 | Lane sequence L→C→R and reversed | No | Frozen P3-3C.5 pilot FAIL (reference degenerate); main not run/unauthorized | **BLOCKED** |
| 3C.6 | Jump and roll onset/offset intervals | No | No runner; design undefined | **NEEDS DESIGN CLARIFICATION / BLOCKED (perceived)** |
| 3C.7 | Frame-rate sensitivity 200/100/50 ms | Yes (P3-T7) | Quantified | **COMPLETE (executed)** |
| 3C.8 | T1 vs T2 vs T3 encoding ablation | No | T2/T3 absent; design undefined | **BLOCKED** |
| 3C.9 | Controls: no input, shuffled, reversed, dropped | Yes (P3-T7) | no_input 0 / shuffled 453 / dropped 462 spikes | **COMPLETE (executed)** |

### 10.3 Milestone matrix

| Milestone | Verdict |
|---|---|
| Phase 3A — sensory encoding | **COMPLETE** |
| Phase 3A.5 — calibration | **COMPLETE WITH LIMITATIONS** |
| Phase 3B — visual perception | **PARTIALLY COMPLETE** |
| Phase 3C — temporal sensory | **PARTIALLY COMPLETE** — not accepted |
| **Phase 3 overall** | **NOT COMPLETE** — scientific gates unmet |

---

## 11. Stop condition and claims not made

The brief instructs: "Stop and report if: Original acceptance criteria cannot
be established." That condition is met. This report stops at the audit.

**Claims this report does not make:**

- It does not claim 3C.6 or 3C.8 was implemented.
- It does not claim any jump/roll or encoding-ablation result.
- It does not claim the current temporal encoder represents discrete events,
  phasic onsets/offsets, or encoding-dependent separability.
- It does not invent the six 3C.6 conditions, the nine 3C.8 conditions,
  `tau_enc`, a T3 specification, a threshold or a seed plan.
- It does not revise the P3-T7 negative result or any acceptance criterion.
- It does not claim Phase 3C is accepted, and it does not claim Phase 3 is
  complete.
- It does not modify frozen P3-3C.5 artifacts, datasets, model weights,
  configs or existing results.

**Recommended next action (for the user, not performed here):** answer decisions
4–6 for 3C.6 and 7–13 for 3C.8 in
`docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md:980–1003`. Only then can a
preregistration be written and implementation begun under the project's
freeze-before-execute rule.

---

## 12. Integrity appendix

### 12.1 Git state

| Check | Value |
|---|---|
| HEAD | `62a64309cadc0db7353c856607cee5369993bd65` |
| Branch | `main` |
| Porcelain entries before report | 233 |
| Modified tracked | 21 |
| Untracked | 212 |
| Staged | 0 |
| Porcelain entries expected after report | 234 (21 modified + 213 untracked) |

All 21 tracked modifications pre-date this work package and were preserved.
No `git add`, commit, push, reset, clean, checkout, restore or stash was run.

### 12.2 Protected artifacts

| Artifact | SHA-256 | State |
|---|---|---|
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` | Unchanged |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` | Unchanged |
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` | Unchanged |
| `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md` | `b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7` | Unchanged |
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` | Unchanged |
| `experiments/phase_3c/results/temporal_acceptance.json` | `4eda97fe8729f91257afdce4f255d3ceabf924f411408a74e35e036e6f27efdc` | Unchanged |
| `reports/PHASE3_T5_T6_EVIDENCE_RECOVERY_AUDIT.md` | `e4f093ea41fbf5a44cf7fc5972521be372c009f0009a4d60d694ea12bb6a2017` | Unchanged |

### 12.3 Test summary

| Suite | Result |
|---|---|
| 8 focused temporal/sensory files | 81 passed, 0 failed, 3.01 s |
| calibration + tracking | 24 passed, 0 failed, 1.97 s |
| Full suite | 916 passed, 3 skipped, 0 failed, 192.39 s |

Status: audit complete at the brief's stated stop condition. No implementation
performed. Stop here.
