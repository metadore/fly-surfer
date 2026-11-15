# P3-T12 preflight report

**Status:** PASS — full characterization authorized.
**Protocol:** `docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md`
(sha256 `49c09424b15db3b09cfdef5b28afcf0cbcaa6dbc72a9f657de6b31a82201b173`).
**Smoke artifact:** `experiments/phase_3c/results/p3_t12_smoke.json`
(sha256 `ce0dd7c5187dcdcb6b557082868219859a7d2e9e94f09adf7c01515b4857f92e`, 521,254 bytes, verdict `SMOKE ONLY (infrastructure
validation)`, runtime 120.35 s).
**Measured preflight:** `experiments/phase_3c/results/p3_t12_preflight.json`
(sha256 `3974bd00bf95c4f5d1e5378bafe63dfc3a117caf1170a3c5efa0bbeac2287463`).

## 1. What was executed

```
python -m experiments.phase_3c.network_characterization --all \
    --smoke-ms 600 --reproduce-subprocess --overwrite
python -m experiments.phase_3c.p3_t12_preflight --overwrite
```

The smoke ran all seven preregistered conditions for 600 ms each (1,200 steps;
`C3-washout` 1,350 ms / 2,700 steps) with two in-process repeats, plus fresh
interpreter repeats of `C3` and `C3-washout`. The second command ran the
unmodified `causal_control.run_once` path on the identical 600 ms `C3` window to
measure instrumentation cost and to verify that the instrumented stepper and
`BrainSimulator` produce the same spikes.

## 2. Equivalence and reproducibility

| Check | Result |
| --- | --- |
| Instrumented vs `BrainSimulator`, 600 ms C3 | 1,791,252 spikes both; `spike_counts_sha256` `d47633f8…19421` both |
| Scheduler signature, both paths | `6265c03f…cbac` |
| In-process repeats, 7/7 conditions | identical |
| Subprocess repeats, C3 and C3-washout | identical, no differing hash keys |
| Washout prefix gate (0–600 ms) | identical counts, `d47633f8…19421` |
| Smoke invalidations | none; 11 rules evaluated, 0 triggered |
| Smoke equivalence gate | recorded as not applicable (archived C3 comparison is only valid at 3,300.5 ms) |

Every condition also passed its definition checks: C0 has no scheduler and no
current; C1–C3 and both ablations inject current only into their active set;
`C3` and `C3-washout` have reference == active set; ablations carry 13 features
and zero current in the removed feature.

## 3. Measured cost

| Condition | Duration | Spikes | % of 30 M | Step loop | Steps/s | RSS after |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | 600.0 ms | 0 | 0.00 % | 3.16 s | 379.9 | 198.1 MB |
| C1 | 600.0 ms | 124 | 0.0004 % | 3.30 s | 363.5 | 199.8 MB |
| C2 | 600.0 ms | 445 | 0.0015 % | 3.43 s | 349.9 | 218.4 MB |
| C3 | 600.0 ms | 1,791,252 | 5.97 % | 9.52 s | 126.0 | 241.6 MB |
| no-player_lane | 600.0 ms | 497 | 0.0017 % | 3.27 s | 366.9 | 221.8 MB |
| no-train_lane | 600.0 ms | 481 | 0.0016 % | 3.88 s | 309.4 | 220.5 MB |
| C3-washout | 1,350.0 ms | 5,642,635 | 18.81 % | 27.15 s | 99.4 | 273.0 MB |

**Instrumentation overhead:** measured twice on the same 600 ms C3 window.
First pass: 9.5213 s instrumented vs 9.3198 s unmodified = **+2.16 %**. Second
pass after the final runner build: 9.3513 s vs 8.1543 s = **+14.7 %**. The
spread is single-run wall-time variance on a shared machine, not a code change;
both passes are far below the pre-registered 50 % ceiling and both produced the
identical spike hash. The step order, recorder capacity and neuron/synapse
models are unchanged; the only addition is per-step measurement.

**Compute projection (from measured step rates, not spike extrapolation):**
6601 steps at ≈126 steps/s ≈ 52 s for full `C3` (the archived P3-T2 run took
55.4 s, so the rates agree); 8101 steps for `C3-washout` at ≤99 steps/s ≤ 82 s;
the five low-activity conditions ≈ 14 s each; two repeats plus two subprocess
repeats plus analysis stays inside the 10–15 minute budget with < 500 MB RSS.

**Output storage:** the 600 ms payload is 519 KB; at 5.5× the duration the full
payload is expected at a few MB, far below any practical limit.

## 4. Capacity risk

- Archived full-duration C3: 15,654,631 spikes = **52.18 %** of the 30 M
  recorder capacity (240 MB), hash `09611c7d…78305`.
- Smoke C3 is 5.97 % at 600 ms and smoke washout is 18.81 % at 1,350 ms.
- These numbers are **not extrapolated**. The smoke C3 count is 11.4 % of the
  archived full count while covering 18.2 % of the duration, so per-ms rates
  rise during recruitment; a linear projection from 600 ms would be wrong in
  either direction.
- Washout overflow remains possible only if the recruited population sustains
  more than roughly 1.5× the archived C3 rate for the entire extension. Per the
  protocol, overflow raises `SpikeCapacityExceeded`, is recorded as an INVALID
  measurement, and is not fixed by raising the recorded-spike budget.

## 5. Washout drive cutoff

In the smoke window the last step receiving scheduled current is step 1633
(816.5 ms). The post-drive window starts at 817.0 ms and runs 533.0 ms to the
end, with a window/pre-window rate ratio of 1.0011. In the full run the last
frame is at 3,300.0 ms, the 250 ms hold ceiling allows scheduled current up to
3,550.0 ms, and the first drive-free step is 3,550.5 ms. The 500 ms silent
window therefore runs 3,550.5–4,050.5 ms. The prefix gate confirms the extension
does not perturb the validated window.

## 6. Decision

All preflight checks passed: `ready_for_full_run = true`, no failures. The full
characterization (seven conditions, two repeats, subprocess repeats for C3 and
C3-washout, full 3,300.5/4,050.5 ms) is authorized.

## 7. What this preflight does not establish

- It does not establish equivalent behaviour over the full 3,300.5 ms; that is
  the job of the archived-C3 hash gate in the full run.
- It does not establish washout capacity, only that 1,350 ms fit comfortably.
- Timing is machine- and load-dependent and is used only to bound the run.
- It makes no scientific claim: the numbers describe cost and reproducibility,
  not network behaviour.

## 8. Post-run confirmation (added after execution)

The full run completed after this preflight with verdict `VALID` and zero
invalidations. Measured step loops: C3 63.09 s (104.6 steps/s), C3-washout
78.33 s (103.4 steps/s), low-activity conditions 13.8–18.9 s; peak RSS 343.9 MB
for C3 and 380.4 MB for the washout. Total runtime including subprocess repeats
was 497.1 s, inside the 10–15 minute budget. Washout used 19,503,284 recorded
spikes = 65.0 % of capacity; no overflow occurred. The archived-C3 hash and the
washout prefix both matched exactly, and the two subprocess repeats were
identical. These observations confirm the preflight projections; they do not
change any preflight criterion.
