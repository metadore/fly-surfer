# Phase 8 — REV3 → REV4 Correction Report

| field | value |
|---|---|
| scope | the seven residual REV3 ambiguities identified in `reports/PHASE_8_IMPLEMENTATION_STATUS.md` §6 |
| result | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`, a **complete** protocol |
| REV3 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV3.md`, SHA-256 `ad907827f861bf6021652bbcbf21d2fb45e8b4c1827db1be42d11b572d82b9cf`, 1,848 lines — **preserved byte-identical, not overwritten** |
| scientific parameters changed | **none.** No hypothesis, condition, contrast, outcome, α, SEI (100), K (10), episode cap (900), seed count (16/10), eta (0.5), bound, coefficient or dependency changes |
| execution | none. No episode, pilot, campaign, training, BANC randomisation or weight change was performed |

## 1. What this report is

REV4 changes only places where the REV3 text could not be executed as written, or where two
statements in REV3 contradicted each other. For every item the report states the conflicting text,
the interpretation chosen, the evidence that fixes it, and every location corrected. Nothing is
"reinterpreted" after data; no data exist.

The direction of every change is either neutral (an undefined quantity now has a denominator) or
**stricter** (the fallback bound is lowered). No acceptance criterion is weakened.

## 2. The seven corrections

### 2.1 R13 neighbourhood overlap — denominator for isolated nodes

**Conflicting statements.** §3.3.1 R13: "mean over nodes of Jaccard(out-neighbours_orig,
out-neighbours_new)". A node whose out-neighbourhood is empty in both graphs has `0/0`, which is
undefined. If read as `1.0`, the 24,320 nodes isolated in both graphs contribute `24,320/172,433 ≈
0.141` before any swap and the gate `≤ 0.01` is unsatisfiable.

**Intended interpretation.** Average over nodes with a non-empty out-neighbourhood in at least one
graph ("active nodes"); exclude nodes isolated in both from the denominator and count them. The
literal all-node value is reported beside the gated value but does not gate.

**Evidence.** `experiments/phase_8_random/target_exchange.py::_neighbour_overlap` already computes
both values and documents exactly this reasoning; it returns `mean_over_active_nodes` as
`statistic`. The implementation gate and the test `test_r13_gate_uses_nodes_with_a_neighbourhood`
already use it.

**REV4 change.** §3.3.1 R13 defines the active-node denominator, names the reported literal value,
and states that isolated nodes are counted.

### 2.2 §6.3 seed formula versus §6.2 and R18

**Conflicting statements.** §6.3: every stream is
`SeedSequence([MASTER_SEED, condition_id, seed, stream])`, `stream ∈ {environment, network,
learning, structure}`. §6.2: the environment seed is `derive(master, s, j, "env")` — independent of
condition and indexed by episode. R18: one structure graph `G_s` per campaign seed shared by C, D
and C′. The §6.3 formula makes the environment condition-dependent and gives C, D and C′ different
graphs. The heading also said "three" streams while four are listed.

**Intended interpretation.** Each stream has its own entropy vector:

| stream | entropy | condition-dependent |
|---|---|---|
| environment | `[master, seed, episode, 1]` | no |
| network | `[master, condition_code, seed, 2]` | yes |
| learning | `[master, condition_code, seed, 3]` | yes |
| structure | `[master, seed, 4]` | no |

**Evidence.** `experiments/phase_8/seeds.py` implements exactly this and states why the two streams
omit the condition. §6.2's pairing argument requires it; R18's shared-graph requirement requires it.

**REV4 change.** §6.3 retitled "Four independent seed streams", the single universal formula is
withdrawn, the per-stream entropy table replaces it, and the integer codes are declared a naming
convention. R18 and Appendix C replace the string `"structure"` (which cannot enter a
`SeedSequence`) with code 4.

### 2.3 §3.6.3 uncovered ablation cell

**Conflicting statements.** The four-row table covers (i) argmax changed and chosen population
spiked, (ii) argmax unchanged for a non-`NO_ACTION` choice, (iii) `NO_ACTION` with a motor spike,
(iv) `NO_ACTION` with no spike. The combination "argmax changed **and** chosen population had no
spike" matches no row.

**Intended interpretation.** It is not motor-driven (no spike in the chosen population) and it is
not the `NO_ACTION` case, so the honest label is `undefined` **with an audit reason recording the
uncovered cell**. It must not be counted as motor-driven, so E4's denominator (non-`NO_ACTION`
decisions) and numerator are unchanged.

**Evidence.** `readout/ablation.py::classify_decision` already implements this branch, labels it
`undefined`, and writes `label_reason = "ablation changed the argmax but the chosen population had
no spike; not defined by the §3.6.3 table"`.

**REV4 change.** A fifth table row defines the case. The recorded `label` stays `undefined`; the
reason distinguishes the branch. A note after the table states that the two `undefined` branches are
carried separately in the audit table and jointly under `undefined` in the four-name summary that
feeds E4.

### 2.4 113.05 versus 112.87

**Conflicting statements.** §7.1 writes `2.8016 · σ_max / √10 ≤ 100 ⇔ σ_max ≤ 113.05`. The declared
formula gives `100 · √10 / 2.801585 = 112.8718…`. §7.4 writes "≈ 113.1"; §10.8, U7 and Appendix C
repeat 113.05. The analysis computes 112.87 and the test asserted the declared constant 113.05.

**Intended interpretation.** The *formula* governs; 113.05 is not derivable from it and is a
transcription artefact. The bound is 112.87 (two decimals of the exact quotient).

**Evidence.** `experiments/phase_8/analysis.py` computes
`sei * sqrt(n_seeds_fallback) / MDE_COEFFICIENT` with `MDE_COEFFICIENT = 2.801585`, i.e. 112.8718,
and reports the declared constant separately. `test_phase_8_analysis.py` asserted the two values and
a deliberate discrepancy.

**Direction.** The fallback is **tightened** by 0.18 (0.16 %). SEI = 100, N = 16/10, α and the
normal-theory coefficients are untouched, so no *scientific* parameter changes; only the arithmetic
consequence of the declared formula replaces an incorrect copy of it.

**Corrections made.**

- §7.1, §7.4, §10.8, U7 and Appendix C now say 112.87; "113.05" and "≈ 113.1" are withdrawn.
- Appendix C gains an explicit σ row (112.87).
- `configs/phase_8/campaign.yaml`: `fallback_max_paired_sd: 112.87`, with a comment recording the
  derivation and the withdrawal.
- `tests/test_phase_8_analysis.py` now asserts `declared == computed == 112.87`, `consistent is
  True`, and the "agree" note. This is the only test expectation changed in this sprint; it encoded
  the REV3 discrepancy, which REV4 removes. The testing invariant it enforces (declared constant
  must equal the formula) is unchanged — it is now actually satisfied.

### 2.5 U1 "three gate cases" versus five rows

**Conflicting statements.** §12's register entry and §10.13 say "three gate cases". The operative
U1 table defines U1-A … U1-E (five cases), and §12.1's own finding text writes "three gate cases
(U1-A to U1-E)".

**Intended interpretation.** Five cases. The "three" wording is a leftover from the pre-U1-E design
(both floor / A floors only / F floors only) and is stale.

**Evidence.** `evaluation/viability.py` implements five cases and labels the count in its case
table.

**REV4 change.** §10.13, the §12 register entry, the U1 prose and §12.1 all say five. The five rows
themselves are unchanged.

### 2.6 "At floor" had no numeric definition

**Conflicting statements.** §7.8 uses "at floor in ≥ 4 of 6 conditions" as a post-campaign
reporting trigger but never defines "at floor"; §7.8 also requires the confirmatory tests to be
reported regardless, so the rule is not a stopping rule.

**Intended interpretation.** A condition is at floor when its paired mean capped survival score
difference from the measured substrate-free floor is **≤ 0** (a tie is at floor: the condition is
not above the floor). The comparison uses the same capped score, paired seeds and seed-level
averaging as the primary. A missing floor makes the rule **not evaluable**, never satisfied.

**Evidence.** `experiments/phase_8/analysis.py::floor_decomposition` computes exactly
`mean_difference <= 0`, exposes the definition in its `note`, and sets `no_power_warning` at ≥ 4.

**REV4 change.** §7.8 gains the numeric definition, states that it is descriptive only, that it is
reported per condition, and that no condition leaves the confirmatory family because it is at
floor. The stop rule remains U1.

### 2.7 Error before the first completed update

**Conflicting statements.** §7.6 says the sensitivity analysis re-runs "with errors scored at their
last completed update". An episode that raises before update 1 has no completed update, yet the
schema stores such a row with `steps = 0` and `survival_score = 0.0`, so the sensitivity analysis
contributes 0.0 — a value the protocol did not authorise.

**Intended interpretation.** The sensitivity contribution is `min(observed_updates, 900)`, where
`observed_updates` is the number of completed updates. Before the first update this is **0.0**, the
minimum capped score (not an imputation and not a discarding rule). These cells are counted and
reported separately. The complete-case primary still excludes every `status: "error"` row.

**Evidence.** `experiments/phase_8/analysis.py::pair_series(include_errors=True)` includes error
rows and uses their recorded `survival_score`; `schema.py` requires
`survival_score == min(observed_updates, cap)` and `observed_updates == steps`.

**REV4 change.** §7.6 gains an explicit definition paragraph and the separate count for
before-first-update failures.

## 3. Code, config and test references updated

| file | change |
|---|---|
| `experiments/phase_8/config.py` | `Phase8Config.describe()` protocol id and approval note now name REV4 |
| `experiments/phase_8/manifest.py` | `PROTOCOL_ID` → REV4 |
| `experiments/phase_8/analysis.py` | `PROTOCOL_ID` → REV4 |
| `experiments/phase_8/__init__.py` | docstring points at REV4 and REV4 §10.0 |
| `configs/phase_8/campaign.yaml` | `fallback_max_paired_sd` 113.05 → **112.87**, with derivation comment |
| `tests/test_phase_8_analysis.py` | fallback-bound assertions now expect 112.87 / consistent |

Docstrings that cite "REV3 §x.y" are left as written where the cited section number and content are
unchanged in REV4; they describe the provenance of the implementation, not a scientific claim.

## 4. Items deliberately left unchanged

- U1–U18 status: still **PROPOSED — not approved**. REV4 does not approve anything.
- eta = 0.5 for B/D, eta = 0.0 for A′/C′, bounds 0.5–2.0×, 5 pA/update, τe = 20 ms, modulation
  constants, sensory current, decoder thresholds, K, N, α, SEI, Holm family, cap.
- All hypotheses, confirmatory contrasts C1–C4, evidence bar E1–E5 and forbidden statements.
- REV1, REV2 and REV3 documents, all frozen Phase 6/7 artifacts, BANC data and weights.

## 5. Unresolved

None of the seven required the "cannot be established" outcome. Each had a source implementation or
a governing equation that fixed the intended reading; no item was guessed.

## 6. Verification performed

- REV3 hash re-computed before and after: `ad907827…d82b9cf`, 1,848 lines, unchanged.
- `python -c` load of `configs/phase_8/campaign.yaml` through the strict loader and
  `design_summary` (focused, no episodes, no BANC graph).
- Focused Phase 8 analysis/campaign tests; results are recorded in
  `reports/PHASE_8_INTEGRATION_SPRINT_1.md`, including the RAM preflight at execution time.
