# P3-3C.5 — Implementation Compliance Audit

**Status:** IMPLEMENTATION AUDIT — EXPERIMENT EXECUTION NOT AUTHORISED

**Date:** 2026-11-14 (UTC)
**Revision:** 2 — adds the per-neuron scalar `Δ_C(i)` required by §7.1/§13.2 and corrects the R150 description carried over from revision 1.
**Repository:** `C:\Users\Hp\fruitfly\FLY-SURFER`
**Baseline HEAD:** `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`)
**Scope:** implementation, non-simulation tests and this audit only. Zero simulations were executed for this task.

This document records compliance with the amended pre-registration. It is an implementation audit, not a scientific report and not authorisation to run the planned campaign. A passing unit test is not permission to execute an experiment.

**Historical record.** `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` is the earlier E11-blocker record. It is not modified by this revision and remains at SHA-256 `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194`.

---

## 1. Authority and baseline

| Document | SHA-256 | Role |
|---|---|---|
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` | Authoritative frozen protocol as amended |
| `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` | `44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd` | Amendment record; E11 withdrawn 2026-11-14 |

The original preregistration hash `1daa2439932c93538b22746bcc4c2443b8fe650266a9c347477ca3317ba08857` is historical and superseded. It is not restored. The amended pre-registration takes precedence over earlier drafts, proposals and reviews. Both authoritative documents were read only; neither was modified.

The baseline repository state at the start of this task was HEAD `62a64309cadc0db7353c856607cee5369993bd65` on branch `main`. The working tree already contained unrelated Phase 3B/3C/4/5/6 modifications and untracked files that predate this task. They were left untouched. No file was staged, committed, pushed, reset, cleaned, stashed, checked out or deleted. `README.md` (`8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563`), `datasets/processed/connectome.npz` (`3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`) and all existing model artifacts were not modified.

---

## 2. Files created or modified

| Path | Lines | SHA-256 (at audit time) | Role |
|---|---|---|---|
| `configs/p3_3c5_lane_encoding.yaml` | 533 | `21e4257d7022a7333fa84bef37df489e25e31b016080dfcd64ef0029498df638` | Frozen implementation configuration (unchanged in revision 2) |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | 2850 | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` | Runner, measurement, gates, reporting, execution guards |
| `tests/test_p3_3c5_lane_encoding.py` | 1392 | `e8281529f31a208709bd02d3ec59ef528c72c4fd7f5e9e034df92ade16995f73` | Non-simulation test suite (81 pass, 3 skipped) |
| `docs/P3_3C5_IMPLEMENTATION_COMPLIANCE_AUDIT.md` | this file | — | Compliance audit |

Revision-2 changes are confined to the runner (per-neuron scalar and its rendered column) and the test suite (non-simulation tests). No experimental parameter, condition, seed, gate or reference was changed. No result artifact exists: `experiments/phase_3c/results/` contains no `p3_3c5*` file, and the runner refuses to write results without explicit authorisation.

---

## 3. Verification-status taxonomy

Each requirement is marked with the strongest evidence obtained without execution:

- **Implemented** — the code path exists and is reachable.
- **Statically verified** — checked from the configuration, mapping, graph or constructed schedule without simulation.
- **Synthetically tested** — exercised on synthetic spike arrays or synthetic measurement dictionaries in the test suite.
- **Real-run unverified** — requires authorised execution; no claim is made.

No requirement below is marked real-run verified. No scientific or execution validation is claimed.

---

## 4. Requirement traceability matrix

| # | Requirement (brief §3) | Implementation | Evidence | Status |
|---|---|---|---|---|
| R1 | Exact C1–C4 stimuli | `configs/p3_3c5_lane_encoding.yaml` (C1 `L L L L|C C C C|R R R R`, C2 reverse, C3 `L L L|C C C|R R R|L L L`, C4 `L L L|R R R|C C C|L L L`); `build_scheduler` | `test_core_sequences_are_exact`, `test_condition_matrix_is_frozen` | Implemented; statically + synthetically tested |
| R2 | Primary C1-versus-C2 CENTER comparison | `analyse_seed` → `primary = subtract_measurement(center_metric("C1"), center_metric("C2"))` | `test_measurement_subtraction_is_per_neuron_and_per_bin`, `test_per_neuron_scalar_keeps_c1_minus_c2_direction` | Implemented; synthetically tested |
| R3 | Exact M6′ in Hz | `m6_prime` (runner:1014) | `test_m6_prime_aggregates_bins_then_neurons`, `test_m6_prime_is_units_consistent_for_uniform_counts`, `test_rates_use_twenty_hertz_per_spike_in_fifty_milliseconds` | Implemented; synthetically tested |
| R4 | Four-neuron CENTER measurement | `lane_groups`, `groups["center"]`, first axis of `per_neuron_hz` | `test_stimulated_set_is_exactly_the_twelve_lane_neurons`, `test_analyse_seed_exposes_four_per_neuron_scalars` | Implemented; statically + synthetically tested |
| R5 | Three state-relative bins | `state_relative_counts` (edges `onset + 50s`) | `test_state_relative_bins_start_at_center_onset`, `test_bin_indices_are_half_open` | Implemented; synthetically tested |
| R6 | K_C auxiliary onset reference | `center_onset_ms`, `auxiliary` in `analyse_seed` | `test_kc_is_the_constant_center_onset`, `test_kc_auxiliary_uses_center_population_only` | Implemented; synthetically tested |
| R7 | R200 and R150 reference conditions | `references.r200`/`r150`, `separated_pair`, `separated_ranges` | `test_r200_values_come_from_the_six_permutations`, `test_r150_values_come_from_the_twelve_sequences`, `test_reference_membership_matches_predecessor_class` | Implemented; statically + synthetically tested |
| R8 | T1 step scheduler | `build_scheduler` (`transition_ms = 0`) | `test_step_scheduler_follows_the_twelve_frames`, `test_amended_e2_per_step_counts` | Implemented; synthetically tested |
| R9 | 50 ms crossfade robustness conditions | `build_scheduler` (`transition_ms = 50.0`), causal blend | `test_crossfade_is_linear_and_causal`, `test_crossfade_alpha_half_audit_matches_eight_by_one_hundred`, `test_crossfade_replays_the_step_sequence` | Implemented; synthetically tested |
| R10 | Mandatory controls and seed handling | `load_protocol`, `build_mapping`, campaign guards | `test_protocol_matches_frozen_constants`, seed/path tests | Implemented; statically tested |
| R11 | Main seeds 20261104, 20261105, 20261106 | frozen `seeds.main`; `plan_campaign` | `test_protocol_matches_frozen_constants`; preflight plan | Implemented; statically tested |
| R12 | Pilot seed 20261107 separate from main inference | frozen `seeds.pilot`; distinct campaign paths | pilot separation tests | Implemented; statically tested |
| R13 | Determinism and reproducibility checks | `determinism_repeats`, `_run_determinism_campaign`, `plan_campaign` | `test_determinism_repeats_end_to_end_not_run` (skipped), guard tests | Implemented; guard-tested; real-run unverified |
| R14 | Run manifests and provenance | `campaign_paths`, hash/git blocks, sidecar schedule | hash-shape and git-block tests | Implemented; shape-tested; real artifact unverified |
| R15 | Protocol-compliance validation | within the runner (see §10) | `--preflight`; gate tests | Implemented; statically verified |

### 4.1 §7.1 and §13.2 per-neuron scalar

| Preregistration requirement | Implementation | Evidence | Status |
|---|---|---|---|
| §7.1 lines 502–503: report per-neuron `Δ_C(i) = (1/3) Σ_s [r_C1(i,s) − r_C2(i,s)]` for all four CENTER neurons | `subtract_measurement` (runner:1042) returns `per_neuron_mean_hz`, the mean over the three bins of each row of `per_neuron_hz`; `analyse_seed` exposes it as `analysis["primary"]["per_neuron_mean_hz"]`; `_primary_per_neuron_lines` (runner:2538) renders it as the `Delta_C(i) Hz` column | `test_per_neuron_scalar_matches_preregistered_equation`, `test_per_neuron_scalar_averages_three_state_relative_bins`, `test_per_neuron_scalar_units_are_hertz`, `test_per_neuron_scalar_is_independent_per_neuron`, `test_analyse_seed_exposes_four_per_neuron_scalars`, `test_rendered_report_shows_four_per_neuron_scalars` | Implemented; synthetically tested |
| §13.2 lines 849–851: per-seed analysis record must include per-neuron `Δ_C(i)` | same `per_neuron_mean_hz` inside `primary` in the analysis JSON returned by `analyse_seed` | `test_analyse_seed_exposes_four_per_neuron_scalars` | Implemented; synthetically tested; real-run unverified |

The four values are calculated independently per neuron. The code does not average across neurons before forming `Δ_C(i)`; the existing 4 × 3 per-bin matrix `per_neuron_hz` is preserved. The subtraction direction is C1 minus C2. Units are Hz (counts divided by 0.05 s). `m6_prime` is unchanged and no replacement metric was introduced; the aggregate scalar `value_hz` is unchanged.

Malformed measurement input fails explicitly: `_validated_per_neuron_rows` (runner:1024) raises `ValueError` for a missing key, empty rows, ragged rows, or a per-bin/per-neuron width disagreement; `subtract_measurement` raises on neuron-count or bin-count disagreement between operands. Covered by `test_subtract_measurement_rejects_*`.

### 4.2 R150 count reconciliation

The frozen protocol (§3.3, §3.4) defines a closed-150 set of **12** four-state sequences. C3 (`L C R L`) and C4 (`L R C L`) are two of them; the configuration holds the other **10** in the `closed_150` group and includes all 12 in `references.r150.all_condition_ids` (config lines 412–425).

The predecessor classification in §3.4 (lines 260–270) is:

| Set | pred-LEFT | pred-RIGHT | none | Total |
|---|---|---|---|---|
| All 12 sequences (incl. C3, C4) | 6 (incl. C3) | 3 (incl. C4) | 3 | 12 |
| Reference after excluding C3, C4 | 5 | 2 | 3 | 10 |

The configuration matches the reference split (lines 426–428): `pred_left` has 5, `pred_right` has 2, `no_predecessor` has 3. `SEPARATED_150` is computed from non-overlapping within-group ranges. This revision corrects revision 1, which described the `closed_150` group as "C3, C4 and eight additional" sequences and the R150 reference as including C3/C4; both statements were inaccurate. The implementation and configuration were not changed by this correction.

### 4.3 R200 verification

The six permutations are C1, C2 and four controls (config lines 406–411). CENTER is preceded by LEFT in `R L C` (`R200_RLC`, pred-LEFT) and by RIGHT in `L R C` (`R200_LRC`, pred-RIGHT); `C L R` (`R200_CLR`) and `C R L` (`R200_CRL`) have no predecessor. Values come from each condition's CENTER `M6′`. `SEPARATED_200` requires strict separation of the pred-LEFT and pred-RIGHT values. R200 is a weak descriptive cross-check, not a test. Covered by `test_r200_values_come_from_the_six_permutations` and `test_reference_membership_matches_predecessor_class`.

---

## 5. Deliverable traceability

| Required deliverable | Implementation | Verification |
|---|---|---|
| Frozen experiment configuration | `configs/p3_3c5_lane_encoding.yaml` | `load_protocol` rejects mutations; `test_protocol_matches_frozen_constants` |
| Reproducible runner | `run_campaign`, `plan_campaign`, `main` | 42 explicit conditions; plans reproduce 42/126/18/42/186 |
| M6′ measurement | `bin_count_matrix`, `state_relative_counts`, `rates_from_counts`, `m6_prime`, `subtract_measurement` | unit tests |
| Per-neuron `Δ_C(i)` (§7.1/§13.2) | `subtract_measurement` → `per_neuron_mean_hz`; `_primary_per_neuron_lines` | 14 new non-simulation tests |
| Controls and validity gates E1–E10, E12–E16 | `static_gates`, `condition_gates`, `run_gates` | synthetic gate tests; real-run checks not executed |
| E11 withdrawn, no replacement | `APPLICABLE_GATES` excludes E11; no `E11'` code path | `test_e11_is_absent_from_the_gate_set`, `test_run_gates_emits_no_e11` |
| Tests for the listed areas | 84 tests (81 pass, 3 skipped) | see §11 |
| Implementation compliance audit | this document | — |

---

## 6. Configuration verification

Frozen constants enforced by `load_protocol`:

| Parameter | Frozen value |
|---|---|
| Duration | 600.5 ms |
| Frame interval | 50.0 ms |
| Frames per sequence | 12 |
| `dt_ms` | 0.5 |
| Steps per run | 1201 |
| Current per stimulated neuron | 200 pA |
| Stimulated neurons | 12 (4 left, 4 centre, 4 right) |
| Sensory features | `player_lane` only |
| Background / noise | 0 / 0 |
| Stimulus | `None` |
| Spike capacity | 5,000,000 |
| Main seeds | 20261104, 20261105, 20261106 |
| Pilot seed | 20261107 (excluded from main) |
| Step mode | `transition_ms = 0` |
| Crossfade mode | `transition_ms = 50.0`; causal blend on activations |

The configuration contains 42 explicit conditions, not generated code:

| Group | Count | Conditions |
|---|---|---|
| `core` | 4 | C1, C2, C3, C4 |
| `linear_200` | 4 | L→C, R→C, L→R, C→R |
| `closed_150` | 10 | the ten non-focal closed-150 sequences (C3 and C4 are core; the full set is 12) |
| `constant` | 3 | K_L, K_C, K_R |
| `no_input` | 1 | N0 |
| `single_transition_200` | 6 | six routes at 200 ms |
| `single_transition_150` | 6 | six routes at 150 ms |
| `crossfade` | 8 | XF_C1–XF_C4 and four replayed closed sequences |
| **Total** | **42** | |

Validation rejects: changes to duration, frame interval, `dt_ms`, current, stimulated count, seeds, condition count, group counts, target sequences, reversal, transition metadata, reference membership, gate list, withdrawn-gate replacements, and any inference flag (`p`, CI, SE, significance). C2 is the reverse of C1 and C4 the reverse of C3 on the 50 ms grid; their sequence hashes differ and state multisets match.

Campaign arithmetic is frozen:

| Campaign | Distinct runs | Repeats | Executions |
|---|---|---|---|
| Main | 126 (42 × 3 seeds) | 18 (6 conditions × 3 seeds) | 144 |
| Determinism (standalone re-check) | 0 | 18 | 18 |
| Pilot | 42 (42 × 1 seed) | 0 | 42 |
| **Planned total instances** | — | — | **186** |

The determinism repeat is a repeat, not an independent replicate, and the parent/repeat pair is not two samples.

---

## 7. Scheduler and stimulus verification (E2–E5)

The existing `sensory/input_scheduler.py` is used unchanged. The runner maps `mode: step` to `transition_ms = 0` and `mode: crossfade` to `transition_ms = 50.0`, with onset `0.0`, offset `600.5`, active feature `player_lane`, and 200 pA per stimulated neuron.

Static audits over all 42 conditions:

- **E2 (stimulated set):** exactly 12 indices, equal to the 12 `player_lane` neurons; all other neurons receive 0 pA; `stimulator.stimulus is None`; background 0; noise 0. Per-step nonzero counts are 4 for step mode, 4/8 during a crossfade (4 at α = 0 and at the end of the window, 8 for 0 < α < 1), and 0 for N0.
- **E3 (total current):** total injected sensory current is 800 pA at every step with an active schedule, within tolerance, for step and crossfade modes.
- **E4 (activation):** constant-lane conditions activate only their intended group; a silent group is recorded, never hidden.
- **E5 (N0):** `input_schedule=None`, no stimulus, zero background, zero noise, zero spikes.

Crossfade specifics checked on the scheduler: the blend is `(1 − α)·previous + α·current` with `α = (t − start)/50`; it is causal and one-sided; at α = 0.5, eight neurons receive 100 pA each (800 pA total); there is no anticipatory activity in the incoming lane. Step and crossfade schedules have distinct signature hashes, and the signature includes `dt_ms`, `duration_ms`, `transition_ms`, `onset_ms` and `offset_ms`.

---

## 8. Measurement verification

All measurement functions operate on synthetic or stored spike arrays; they do not construct a simulator.

- **Units:** one spike in a 50 ms bin is 20 Hz (`rates_from_counts`).
- **Bins:** absolute bins are half-open `[k·50, (k+1)·50)`; a spike exactly on an edge belongs to the later bin; edges cover `[0, 600]`; the `[600, 600.5)` tail is counted separately and excluded from binning.
- **M6′:** per-neuron per-state-relative-bin rate, mean over the four centre neurons, then mean over the three centre states: `Δ_C(C1,C2) = (1/3) Σ_{s=0..2} [r_C1(s) − r_C2(s)]`. The aggregate is unchanged.
- **Per-neuron scalar:** `Δ_C(i) = (1/3) Σ_s [r_C1(i,s) − r_C2(i,s)]` for each of the four CENTER neurons, in Hz, from `subtract_measurement` (`per_neuron_mean_hz`). It is independent per neuron and preserves the 4 × 3 per-bin matrix.
- **Centre onsets:** C1/C2 = 200 ms, C3 = 150 ms, C4 = 300 ms, K_C = 0 ms.
- **K_C:** reference rate from the constant-centre condition; the auxiliary contrasts are C1−K_C and C2−K_C. K_L and K_R are not used in the auxiliary. K_C has an absolute-time mismatch, as declared in the protocol.
- **R200:** pred-LEFT `R L C`, pred-RIGHT `L R C`, none `C L R` and `C R L` (1/1/2); `SEPARATED_200` from the pred-LEFT/pred-RIGHT pair. See §4.3.
- **R150:** 12 closed-150 sequences; pred-LEFT 6, pred-RIGHT 3, none 3 including C3/C4; the reference excluding C3/C4 is 5/2/3. `SEPARATED_150` from non-overlapping ranges. See §4.2.
- **Predicates:** all set-based; `FOCAL_200`, `FOCAL_150`, dwell consistency, reference degeneracy, silent centre, outside dominance, transition-onset and endpoint-confinement.
- **Analysis output:** `measure_condition` records per-lane per-bin counts, rates, per-neuron per-bin counts and active-neuron counts per lane per bin; `analyse_seed` also records per-bin and per-neuron primary values (including `per_neuron_mean_hz`), `Δ_L`, `Δ_R`, route contrasts, single-transition stationarity and latency/peak descriptors.
- **No inferential statistics:** the analysis payload contains no `p_value`, `confidence_interval`, `standard_error` or `significance` key (`test_analysis_contains_no_inferential_statistics`).

Secondary S1–S12 coverage:

| Item | Status |
|---|---|
| S1–S9 | Implemented |
| S10 | Partial: first-spike latency, peak rate and peak bin are recorded; the pre-onset mean+SD threshold and decay measure are not implemented |
| S11 | Partial: per-seed sign and ranges are recorded; per-lane rank correlations are not implemented |
| S12 | Implemented |

These partial items are declared as limitations in §12; nothing is reported as if it were computed.

---

## 9. Controls, validity gates and determinism

`APPLICABLE_GATES` contains E1–E10 and E12–E16 (15 gates). E11 is absent, and no E11 replacement exists.

| Gate | Implementation | Verified without execution |
|---|---|---|
| E1 | Run completion tracked; failures block analysis | Runner control flow; gate tests |
| E2 | Stimulated set, per-step counts, stimulus/background/noise checks | All 42 schedules |
| E3 | Per-step total current = 800 pA | All active schedules |
| E4 | Constant-lane group activation | K_L, K_C, K_R |
| E5 | N0 has no schedule and no spikes | N0 scheduler/audit |
| E6 | Lane order left, centre, right; fails loudly on change | Static gate |
| E7 | Disjoint 4-neuron groups inside annotation pools | Static gate |
| E8 | C2 = reverse(C1), C4 = reverse(C3); hashes differ | Static gate |
| E9 | C3/C4 prefix identity for 0–150 ms | Prefix comparison unit test; real-run check pending execution |
| E10 | 6 conditions × 3 seeds = 18 subprocess repeats | Matrix test; repeat execution not run |
| E12 | Existing suite unchanged | Focused regression suites pass; full pre-existing suite not run |
| E13 | Source/config/connectome/protected hashes plus git block in sidecar | Hash-shape tests; no sidecar produced (no execution) |
| E14 | Outside activity reported; recurrent-input caveat stated | Gate test |
| E15 | Half-open bins covering `[0, 600)`; tail excluded | Bin tests |
| E16 | C1 ≡ L→C and C2 ≡ R→C for t < 400 ms | Prefix comparison unit test; real-run check pending execution |

Gate E11 is withdrawn by the approved amendment and is not enforced anywhere. The crossfade is checked causally (E3 and the local blend formula), and frame reversal by E8.

Gates E6, E7, E8, E13 and E15 are evaluated statically from the configuration, mapping and graph and pass. E2, E3, E4 and E5 are evaluated from constructed schedules and pass for all 42 conditions. E1, E9, E10, E12, E14 and E16 require run data or a full-suite run; their logic is unit-tested on synthetic arrays, but no real-run evidence exists in this task.

Determinism is defined but not executed: the repeat set is C1, C2, C3, C4, N0 and K_C for each of the three main seeds (18 repeats). A determinism campaign refuses to run without a completed main result and refuses without authorisation. Determinism is reproducibility of the same computation, not robustness.

---

## 10. Protocol validation location

Protocol-compliance validation is implemented **within the runner**, not in a separate `experiments/phase_3c/p3_3c5_protocol_validation.py`:

- `load_protocol` and `_validate_conditions`/`_validate_references` reject any deviation from the frozen configuration.
- `assert_prereg_hashes` checks both authoritative document hashes.
- `static_gates` and `condition_gates` evaluate the static and schedule gates.
- `preflight_report` and the `--preflight` CLI run the static checks, construct all 42 schedules and audits, write nothing, and report `execution: NOT RUN — EXECUTION NOT AUTHORISED`.
- `run_gates` evaluates the run-time gates once execution is authorised.

A separate file would duplicate this logic without adding coverage, so none was created. This is a deliberate structural choice, not a missing requirement.

### 10.1 Execution guards

- `run_execute_single` and `determinism_repeats` require an explicit acknowledgement value; without it they raise.
- `run_campaign` requires a known campaign (`main`, `pilot`, `determinism`), an explicit acknowledgement, and, for main/pilot, a declaration that the existing suite was run unchanged.
- A determinism campaign requires an existing main result and cannot create parent runs.
- The CLI refuses `--execute` without the authorisation flag.
- Residual note: `--execute-single` checks the acknowledgement but not the `--existing-tests-passed` declaration; it is an internal per-instance mechanism used by the authorised parent campaign, not a campaign entry point.

---

## 11. Tests and commands

No test constructs a `BrainSimulator` or executes an experiment instance. Tests either load the frozen configuration, construct schedulers, audit injected current, or apply arithmetic to synthetic spike arrays and synthetic measurement dictionaries.

Commands run in revision 2:

```
python -m py_compile experiments/phase_3c/p3_3c5_lane_encoding.py tests/test_p3_3c5_lane_encoding.py
python -m pytest tests/test_p3_3c5_lane_encoding.py -q
python -m pytest tests/test_configs.py tests/test_game_state.py tests/test_input_scheduler.py tests/test_sensory_mapping.py tests/test_temporal_scheduler.py tests/test_population_encoder.py -q
python experiments/phase_3c/p3_3c5_lane_encoding.py --preflight
```

Results:

| Command | Result |
|---|---|
| `py_compile` | PASS |
| P3-3C.5 suite | **81 passed, 3 skipped** in ~26 s |
| Focused regressions (six simulation-free files) | **47 passed** |
| `--preflight` | `{"passed": true, "static_failures": [], "condition_failures": [], "execution": "NOT RUN — EXECUTION NOT AUTHORISED"}` |

New revision-2 tests:

- `test_per_neuron_scalar_matches_preregistered_equation` — four values, each equal to the mean over the three bins of the per-bin C1−C2 difference, with an exact expected vector.
- `test_per_neuron_scalar_averages_three_state_relative_bins` — one neuron with counts 1/2/3 gives 40 Hz.
- `test_per_neuron_scalar_keeps_c1_minus_c2_direction` — forward +20 Hz, reversed −20 Hz.
- `test_per_neuron_scalar_units_are_hertz` — one spike in one 50 ms bin contributes 20/3 Hz to the scalar.
- `test_per_neuron_scalar_is_independent_per_neuron` — four distinct per-neuron values, not a repeated global mean.
- `test_m6_prime_does_not_gain_a_per_neuron_scalar` — aggregate M6′ output is unchanged.
- `test_analyse_seed_exposes_four_per_neuron_scalars` — four scalars in `analysis["primary"]["per_neuron_mean_hz"]`, matrix still 4 × 3.
- `test_rendered_report_shows_four_per_neuron_scalars` — the rendered table has four `Delta_C(i) Hz` rows.
- `test_subtract_measurement_rejects_missing_per_neuron_rows`, `..._rejects_empty_rows`, `..._rejects_ragged_rows`, `..._rejects_bin_count_mismatch`, `..._rejects_neuron_count_mismatch`, `..._rejects_bin_width_mismatch_between_inputs` — malformed input fails explicitly with `ValueError`.

The 15 test areas from the brief are covered:

1. Configuration schema and parameter validation.
2. Condition construction.
3. Stimulus timing and frame boundaries.
4. Step scheduler integration.
5. Crossfade scheduler integration.
6. Stimulated set and per-step counts.
7. Total input current.
8. M6′ calculations, units and the per-neuron scalar.
9. K_C reference calculation.
10. R200 and R150 calculations.
11. Seed and metadata handling.
12. Determinism-repeat scheduling.
13. Pilot/main separation.
14. Withdrawn E11.
15. Experiment execution guard.

Three tests are skipped explicitly with reason `NOT RUN — EXECUTION NOT AUTHORISED`:

- `test_main_campaign_end_to_end_not_run` — requires 126 main instances.
- `test_pilot_campaign_end_to_end_not_run` — requires 42 pilot instances.
- `test_determinism_repeats_end_to_end_not_run` — requires 18 repeats.

They are skips, not fabricated substitutes; no simulated spike output is produced or imitated.

---

## 12. Execution boundary, artifact state and limitations

### 12.1 Execution boundary

- Simulations executed for this task: **0**.
- Main instances executed: **0 of 126**.
- Pilot instances executed: **0 of 42**.
- Determinism repeats executed: **0 of 18**.
- Planned campaign instances executed: **0 of 186**.
- Scientific result datasets generated: **0**.
- Background experiment processes started: **0**.
- Result artifacts under `experiments/phase_3c/results/`: **none** matching `p3_3c5*`.

`--preflight` loads the graph, builds the mapping and constructs all 42 schedulers and audits. It reports `execution: NOT RUN — EXECUTION NOT AUTHORISED` and writes no result file.

### 12.2 Limitations

1. **No real-run gate evidence.** E1, E9, E10, E12, E14 and E16 are implemented and unit-tested on synthetic arrays, but they have not been evaluated on real spike trains. In particular, real C3/C4 prefix identity (E9), real C1/`L→C` and C2/`R→C` prefix identity (E16) and subprocess repeat equality (E10) remain unverified until execution is authorised.
2. **E12 is partial.** The six focused simulation-free suites pass (`tests/test_configs.py`, `test_game_state.py`, `test_input_scheduler.py`, `test_sensory_mapping.py`, `test_temporal_scheduler.py`, `test_population_encoder.py`), but the full pre-existing suite was not run in this task because parts of it execute simulations. E12 requires the whole existing suite to pass unchanged before a campaign is valid.
3. **Secondary measures are partial.** S10 lacks the pre-onset mean+SD threshold and the decay measure; S11 lacks per-lane rank correlations. Both are declared here rather than reported as complete.
4. **No scientific result exists.** This audit says nothing about whether a history effect, lane separation or negative result will occur. Those questions require the authorised campaign.
5. **Hashes are snapshots.** The file hashes in §2 identify the audited implementation; any later edit invalidates them and requires a re-audit.
6. **Pre-existing working-tree changes.** Unrelated Phase 3B/3C/4/5/6 modifications and untracked files were present at baseline. They were left untouched and were not audited.
7. **Per-neuron scalar is synthetically tested only.** Its formula and units are verified on synthetic arrays; its behaviour on real spike trains is real-run unverified.

### 12.3 Blockers to execution

- Explicit, separate authorisation to run the campaign is absent. None of the 186 instances may start without it.
- Before a main campaign, E12 requires the full existing suite to pass unchanged and the implementation hashes to be frozen and recorded.
- The real-run gates E9, E10 and E16 must be evaluated during execution; if any fails, the affected run is invalid and is reported, not imputed.

### 12.4 Verdict

**IMPLEMENTATION PASS WITH LIMITATIONS.**

The configuration, runner, measurement functions (including the per-neuron `Δ_C(i)` required by §7.1/§13.2), control gates and non-simulation tests comply with the amended pre-registration in scope. The limitations in §12.2 are declared and none is concealed. This verdict is not a scientific result, not authorisation to execute, and not permission to relax any gate. Experiment execution remains unauthorised; the campaign awaits a separate explicit instruction.

### 12.5 Repository state at audit close

- HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`), unchanged from baseline.
- Staged changes: none. Commits: none. Pushes: none.
- New files from this task: the four listed in §2.
- `docs/P3_3C5_IMPLEMENTATION_AUDIT.md` unchanged at `f7ea9131a15ce26d5d8de655ea9142848076fbdd0f139c64414ec9f12638b194`.
- Pre-existing modified and untracked files: unchanged.
