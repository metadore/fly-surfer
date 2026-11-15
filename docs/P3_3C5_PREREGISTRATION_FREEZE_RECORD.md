# P3-3C.5 — Preregistration Freeze Record

**Status: FREEZE RECORD — PROTOCOL FROZEN; IMPLEMENTATION AND EXECUTION NOT AUTHORISED.**

**Freeze date.** 2026-11-14.

**Frozen document.**
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md`
SHA-256 `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857`
(1,127 lines).

This record documents the approved decisions, the changes from the draft, the
remaining limitations, the source-document hashes verified at freeze, and the
authorisation state. It does not implement, configure, execute or analyse
P3-3C.5.

---

## 1. Approved decisions

| Decision | Approved resolution | Reflected in |
|---|---|---|
| D1 | Four conditions = C1–C4; C1/C2 are primary | preregistration §0, §1.4, §3.2, §10 |
| D2 | Closed extension C3 `L→C→R→L`, C4 `L→R→C→L` | §3.2 |
| D3 | T1 step primary; 50 ms crossfade robustness for C1–C4 + four additional 3-transition closed sequences (8 distinct) | §3.3, §3.5, §6.2 |
| D4 | Main seeds 20261104/5/6; pilot 20261107 excluded | §6.1 |
| D5 | `player_lane` only; 12 stimulated neurons; 800 pA | §3.6 |
| D6 | Constants, no-input, 6 linear, 12 closed, 12 single-transition; 20-frame-shuffle reference dropped | §3.3 |
| D7 | No p-values, significance claims or 95th-percentile threshold | §9, §10, §13.4 |
| D8 | Pilot 20261107, excluded, no threshold tuning | §6.1, §14.5 |
| D9 | `visual_any` pool-matched mapping excluded | §0, §15.5 |
| D10 | Implementation and execution remain separate future authorisations | §17.2, §3 of this record |
| Seeds | 20261104/5/6 main; 20261107 pilot | §6 |
| Replication | 2-of-3 descriptive consistency only; exact values and range | §6.3, §10.2 |
| Negative results | Reported without reframing or threshold changes | §10.4 |
| Metric | M6′ retained: `Δ_C` = mean over 3 state-relative bins of the CENTER-group rate difference, Hz | §7 |
| Reference | Descriptive reference retained; no significance test | §9 |

---

## 2. Changes from the draft

The operative protocol is the frozen preregistration, not the draft. The
changes below are either the approved decisions or corrections required for
internal consistency. No change weakens a stated limitation.

### 2.1 Approved decisions applied

1. **D1 resolved.** The draft already used C1/C2 as primary; the freeze records
   that this is the approved interpretation of the unnamed `4`.
2. **D6 applied.** The optional 20-frame-shuffle reference is removed from the
   control block, the run matrix and the outcome rule.
3. **D9 applied.** The optional `visual_any` mapping is removed; the CENTER
   pool asymmetry is a stated limitation rather than an optional control.
4. **D7 confirmed.** The descriptive rule, the ban on p-values and the ban on
   the 95th-percentile threshold are recorded as approved, not proposed.
5. **D10 recorded as open.** Implementation and execution are not authorised.

### 2.2 Corrections to the draft

1. **Crossfade run count corrected from 10 to 8.** The draft said "C1–C4 plus
   the six 3-transition closed sequences | 10". C3 and C4 are two of those six,
   so the union has 8 distinct sequences: C1, C2, C3, C4 and the four
   additional closed sequences `C L R L`, `L C L R`, `R L C L`, `L R L C`.
   Running C3/C4 twice in the same mode would not add information. The frozen
   matrix uses 8.
2. **Reference assignment corrected.** The draft computed the
   predecessor-stratified range from the 12 closed sequences (150 ms) and then
   applied it to C1/C2 (200 ms), a dwell mismatch. The frozen protocol uses a
   dwell-matched reference for each contrast:
   - **R200** (six 200 ms permutations) for P1: non-focal pred-LEFT `R L C`
     (one value), pred-RIGHT `L R C` (one value);
   - **R150** (twelve 150 ms closed sequences) for P2: 5 pred-LEFT and 2
     pred-RIGHT non-focal values.
   The R200 reference is explicitly a one-versus-one descriptive cross-check,
   not a distribution; this is stated as a limitation.
3. **New gate E16 (causal decomposition).** C1 and `L→C` (200/400) have
   identical input for `t < 400 ms`; C2 and `R→C` likewise. Their spike trains
   must match exactly. This makes the causal cleanliness of the primary window
   an executable check and prevents the single-transition runs from being
   counted as independent evidence.
4. **Run matrix made explicit.** 42 distinct run instances per seed, 126 main
   runs over three seeds, 18 determinism repeats and 42 pilot runs: 186
   planned run instances. The draft gave no totals.
5. **Spike capacity sourced.** The value 5,000,000 is taken from
   `configs/sensory_config.yaml` line 19, not chosen ad hoc.
6. **Outcome classes grouped and ordered.** The eleven classes are assigned in
   a fixed order and grouped as positive, negative, ambiguous and invalid, so
   that a positive cannot be assigned to an invalid, silent or degenerate run.
   The attribution classes require an unambiguous set-based pattern; otherwise
   the outcome is `NO_HISTORY_EFFECT`.
7. **Input contract fixed.** The frozen protocol states the exact
   `GameState(player=PlayerState(lane=...), time_ms=...)` construction, the full
   mapping build, the `current_pa` dictionary, the `stimulus=None` requirement,
   the `active_features` list and the `N0` construction.
8. **Reporting and wording fixed.** The required JSON fields, report tables and
   prohibited wording are stated, so a later implementation cannot choose a
   weaker report.
9. **Draft-only wording removed.** The draft's optional dimensionless
   complement is retained only as a descriptive ratio outside the decision
   rule; it is not part of M6′.

### 2.3 What did not change

- The scientific question, the four conditions, the lane-only feature set, the
  step/crossfade logic, the three-seed plan, the execution-validity gates, the
  M6′ formula and the negative-result rules are unchanged in substance.
- No existing file, result, configuration, source file or protected artifact
  is modified by the freeze.

---

## 3. Authorisation state

- **Implementation is not authorised.** No configuration, runner, test or
  analysis code may be written under the frozen protocol without a separate
  task authorisation.
- **Execution is not authorised.** No main run may occur before (a) a separate
  execution authorisation, (b) the implementation has passed E1–E16 on a smoke
  run, and (c) the frozen protocol hash and implementation hashes are recorded.
- **Pilot is not authorised.** The pilot seed 20261107 is part of the frozen
  protocol but is also gated by the execution authorisation.
- **Protocol amendments.** Any change to the frozen preregistration requires a
  recorded amendment and a new SHA-256 before a main run. An amended protocol
  supersedes this hash explicitly; it does not silently reuse it.

No simulation was run for this freeze. No experiment result was generated. No
`configs/p3_3c5_*`, `experiments/phase_3c/results/*3c5*` or runner exists.

---

## 4. Remaining limitations

The frozen protocol carries these limitations. They are not unresolved
decisions and must appear in the final report.

1. The result is descriptive, not inferential. No p-value, confidence interval
   or significance claim is possible with deterministic permutations and three
   seeds.
2. Three mapping seeds and four neurons per group do not support population
   inference or a robustness claim. Exact per-seed values and range only.
3. The one-hot lane encoder makes lane identity trivial at the input. The
   experiment tests the spiking readout, not a fly lane code.
4. Predecessor lane is confounded with predecessor annotation pool (LEFT 5,892
   vs RIGHT 5,458), and the CENTER pool is only 76 neurons.
5. The `visual_any` pool-matched control is excluded (D9), so the pool
   asymmetry is not experimentally addressed.
6. `K_C` is matched in time since onset but not in absolute time (0–150 ms vs
   200–350 ms). The transition-onset attribution is caveated.
7. The R200 reference is one pred-LEFT value against one pred-RIGHT value. It
   is weak and cannot support a distributional interpretation.
8. P2 (C3/C4 CENTER) confounds absolute time (150 vs 300 ms) and prefix length.
9. P3 (final LEFT) confounds the last transition route (`R→L` vs `C→L`).
10. C3 and C4 are not perfectly matched on transition-type order or per-time
    lane; these are the order manipulation and cannot be matched by any
    4-block design over three lanes.
11. Direct and recurrent input cannot be causally separated; there is no
    synapse-block control. Outside activity is measured, not subtracted.
12. Lane-only input is not the natural full-feature regime, which ignites the
    network.
13. The model has no adaptation or short-term plasticity; any history effect is
    synaptic filtering, spike nonlinearity and recurrent dynamics.
14. The structural connectome is measured, but synapses, weights and pool
    annotations are computational or predicted, not physiological.
15. Determinism is not robustness; identical repeat hashes show runner
    determinism only.
16. The 0.5 ms tail is excluded from the bins and reported separately.
17. The reference sets are small and cannot substitute for more sequences or
    more mapping seeds.
18. The causal decomposition (E16) is a correctness check, not independent
    evidence.

---

## 5. Source-document hashes verified at freeze

All hashes below were recomputed from the working tree on 2026-11-14. The
proposal, draft and review hashes match the values recorded in the
preregistration provenance; they were not modified by this freeze.

| File | SHA-256 |
|---|---|
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857` |
| `docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md` | `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284` |
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION_DRAFT.md` | `3ceda5ece8017fc753a0f3aa9360a963efb58393717a89505d6efd08c3372438` |
| `docs/P3_3C5_PREREGISTRATION_REVIEW.md` | `f50fb2b7eec9a7577bbc28155ccd3e22d3b623d986fbc75b739311b89f3a973a` |
| `docs/PHASE_3C_REMAINING_EXPERIMENTS_DESIGN_AUDIT.md` | `b17feab8f1600bbeb0d9b6d711cccc24c5c8f1debdb22db11082bea5ba34bbb7` |
| `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` | `3b2430fad035c1089dd04272a12beb566469c7ed5c1ac57db940c9d248ec011c` |
| `docs/PHASE_3_ROADMAP.md` | `ab6d3e66f1c84946c44a94c9d6519f4d04a4419a0fdd82d046d035bee00c29e5` |
| `docs/PHASE_3_SENSORY_ENCODING.md` | `d1d9f659b4c2012c33f47175691dacee37e110079bfef1de5811f106cabae8d2` |
| `configs/sensory_config.yaml` | `26d782a3b5910c05d433fa6678557f7c806dc9947ee8ad279e246fa34f4e96db` |
| `configs/neuron_config.yaml` | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` |
| `configs/simulation_config.yaml` | `be0571b9d6ede75b752a79fce3d8136960034f78f2a961fa3c447e31b7d769e3` |
| `configs/temporal_sensory.yaml` | `ef68efb14e35e5ece1d4fb00e268064f4018fbbd801c81ecf8789471e6b8adf4` |
| `sensory/game_state.py` | `2562617f978c145af82ce8707210de577318de04c6749994df1edac078c7bb43` |
| `sensory/population_encoder.py` | `9b4594255935ef950ac639f24580dc85e174f54b95cc913addc2103b8b582134` |
| `sensory/sensory_mapping.py` | `c655c14a7831a968d56c0e5dc7f5dc85e4d6170118e6439caaa0999d3755aaa8` |
| `sensory/input_scheduler.py` | `223bce3738ac02f6f8de736209158df7aafa639cf1f05d9791f559a500e5cc07` |
| `sensory/temporal_scheduler.py` | `3be4ac9a7f04749cfcacdb62c47c254114e601579fd94b6ebc0f66ac3020641c` |
| `brain/brain_simulator.py` | `810dc5c7d4c321acecb4bc99177fb1a97e97ecc0fb59ffef6046065600c6ca07` |
| `perception/temporal.py` | `ed4b3de1f1c92edb81237b76d4b764aaceb876c74c83826dbfb1764531f91421` |
| `README.md` | `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563` |
| `datasets/processed/connectome.npz` | `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8` |

The preregistration hash is of the frozen file as written. Any later edit
invalidates it and requires a recorded amendment.

---

## 6. Integrity statement

- No Python source code was modified.
- No configuration was modified.
- No simulation was run.
- No experiment result was generated.
- No existing Phase 3 result was modified.
- No Phase 4, 5 or 6 artifact was modified.
- `README.md` and the connectome were not modified; their hashes match the
  protected values.
- Nothing was staged, committed or pushed.
- `git add .`, `git add -A`, `git reset`, `git clean`, `git stash` and
  `git checkout` were not used.
- No file was deleted, reset, cleaned, stashed or overwritten.
- The proposal, draft and review remain unchanged historical records.
- The only files created by this freeze are the frozen preregistration and
  this record.

**Implementation has not been authorised.** P3-3C.5 remains unexecuted, and
the correct state is: protocol frozen, awaiting a separate implementation
authorisation and, later, a separate execution authorisation.
