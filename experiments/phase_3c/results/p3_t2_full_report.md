# P3-T2 Full Causal-Control Experiment — Results Report

- **Run**: 2026-11-13T10:07:45Z, mode `full`, duration 3300.5 ms, dt 0.5 ms, 6601 steps
- **Verdict**: **VALID** — 0 invalidations, all preregistered gates evaluated
- **Machine-readable payload**: `p3_t2_full.json` (+ `p3_t2_full.sidecar.json`)
- **First attempt**: INVALID (`p3_t2_full_attempt1_gate_defect.json`) — infrastructure defect only, see Limitations
- **Environment**: Python 3.13.14, Windows 11, numpy 2.3.4; graph 139,255 neurons / 3,732,460 edges / 50,666,648 synapses; simulation seed 20261106, mapping seed 20261104
- **Pre-run checks**: all 7 passed (protocol/config present; archive pre-gate active; cache digest `2a857471…` and scheduler signature `1c3ab12d…` equal to archived values; 9 protected hashes unchanged; recorder capacity 30,000,000; output path free; git HEAD `62a64309` / `main` / 0 staged)

## 1. Condition-by-condition results

| Metric | C0 (no input) | C1 (player only) | C2 (non-player only) | C3 (all features) |
|---|---|---|---|---|
| Total spikes | 0 | 702 | 2,560 | 15,654,631 |
| Spikes in R (138) | 0 | 702 | 2,560 | 3,710 |
| Spikes outside R | 0 | 0 | 0 | 15,650,921 |
| Spikes in A_c | 0 (A_c=0) | 702 (A_c=36) | 2,560 (A_c=102) | 3,710 (A_c=138) |
| Spikes outside A_c | 0 | 0 | 0 | 15,650,921 |
| Active neurons (all) | 0 | 8 | 61 | 35,979 |
| Active in R / outside R | 0 / 0 | 8 / 0 | 61 / 0 | 72 / 35,907 |
| Mean firing rate | 0 Hz | 0.0015 Hz | 0.0056 Hz | 34.06 Hz |
| Peak population rate | 0 Hz | 0.0057 Hz | 0.0223 Hz | 37.02 Hz |
| First spike in R (latency) | — | 28.0 ms | 81.5 ms | 28.0 ms |
| First spike outside R | — | — | — | 101.5 ms |
| Max step current (population, pA) | 0 | 1,896.36 | 13,976.33 | 15,872.69 |
| Min step current (pA) | 0 | 1,896.36 | 0.0 | 1,896.36 |
| Max per-neuron current (pA) | 0 | 200.0 | 543.89 | 543.89 |
| Exposure total (pA·steps) | 0 | 12,517,878.47 | 33,267,180.78 | 45,785,059.25 |
| — hold-only exposure | 0 | 12,517,878.47 | 2,290,447.43 | 5,197,568.73 |
| — pulse-window exposure | 0 | 0 | 30,976,733.35 | 40,587,490.52 |
| Current outside A_c (neuron-indices) | 0 | 0 | 0 | 0 |
| Wall time per run (s) | 13.05 | 13.42 | 13.57 | 55.44 |
| Steps/s | 505.7 | 491.8 | 486.5 | 119.1 |
| Recorder utilization (30M) | 0% | 0.002% | 0.009% | **52.182%** |
| RSS delta (MB) | −1.7 | −0.7 | −1.6 | +115.5 (315.1 after) |

All conditions: `finite_state = true`, membrane within [−90, −50] mV bounds.

### 100 ms binned spike counts (34 bins; bin 33 is the 0.5 ms remainder)

- **C0**: all zero.
- **C1**: near-uniform 18–26 spikes/bin (constant drive), last bin 0. No build-up over time — no recurrent growth.
- **C2**: event-structured (14, 110, 58, …; peak 183 at bin 10 = 1000–1100 ms; last bins 59, 54, 0). Tracks the pulse schedule; no build-up.
- **C3**: bin 0 = 34, bin 1 = 231, bin 2 (200–300 ms) = 248,689 → cascade onset ≈100–300 ms; peak 514,339 at bin 10; sustained ≈513,000/bin through bin 32; final half-bin 5,217. The regime is saturated, not oscillatory.

### Per-feature spikes (of the 3,710 / 2,560 / 702 in-R spikes)

| Feature | C1 | C2 | C3 |
|---|---|---|---|
| player_lane | 404 | 0 | 438 |
| player_speed | 298 | 0 | 373 |
| jumping / rolling | 0 | 0 | 0 |
| obstacle_present | 0 | 273 | 301 |
| obstacle_lane | 0 | 177 | 313 |
| obstacle_distance | 0 | 149 | 149 |
| obstacle_type | 0 | 270 | 254 |
| train_present | 0 | 852 | 855 |
| train_lane | 0 | 464 | 496 |
| train_distance | 0 | 375 | 396 |
| coin_present / coin_lane | 0 | 0 | 0 |
| coin_distance | 0 | 0 | **135** |

Note: the cached 100-frame window injects no current on `coin_present`/`coin_lane`/`coin_distance` (audit peaks 0.0 pA in C2 and C3), so the 135 C3 spikes on `coin_distance`-mapped neurons are **network-driven, not stimulated**.

## 2. Reproducibility and invalidations

- Every condition ran twice in-process; all recorded keys (`spike_counts`, `activity_summary`, `current_trace`, `scheduler_signature`, `cache_frames_digest`, `spikes_total`, first/last spike ms) identical → `repeated_runs_differ` not triggered.
- C0 and C3 re-ran in fresh subprocesses: identical to the parent report (C0 spike hash `8a37a655…`, C3 spike hash `09611c7d…`) → `subprocess_runs_differ` not triggered.
- No invalidation fired: no capacity overflow (C3 peaks at 52.182% of 30,000,000), finite state everywhere, membrane in bounds, no current outside any A_c, condition definitions satisfied, protected hashes unchanged, initial conditions identical, C2/C3 cache digests equal, archive checks equal.

## 3. C3 archive comparison

| Quantity | This run | Archived Phase 3B.2C reference | Match |
|---|---|---|---|
| Total spikes | 15,654,631 | 15,654,631 | exact |
| Stimulated (R) spikes | 3,710 | 3,710 | exact |
| Non-stimulated spikes | 15,650,921 | 15,650,921 | exact |
| First spike | 28.0 ms | 28.0 ms | exact |
| `spike_counts_sha256` | `09611c7dc5c3…305` | `09611c7dc5c3…305` | exact |
| `scheduler_signature_sha256` | `1c3ab12d2afb…840` | `1c3ab12d2afb…840` | exact |
| Cache frames digest | `2a85747165f9…166` | `2a85747165f9…166` | exact |

The runner's `c3_spike_counts_mismatch` and `c3_scheduler_signature_mismatch` gates were evaluated and did not fire. **C3 exactly reproduces the archived reference** under the preregistered equality checks.

## 4. Condition-by-condition comparison

| Contrast | Δ total spikes | Δ in-R spikes | Δ outside-R spikes | Δ outside-R active neurons |
|---|---|---|---|---|
| C1 − C0 | +702 | +702 | 0 | 0 |
| C2 − C0 | +2,560 | +2,560 | 0 | 0 |
| C2 − C1 | +1,858 | +1,858 | 0 | 0 |
| C3 − C0 | +15,654,631 | +3,710 | **+15,650,921** | **+35,907** |
| C3 − C1 | +15,653,929 | +3,008 | +15,650,921 | +35,907 |

In-R per-feature spike counts for the same cached frames differ between C2 and C3 (e.g. `obstacle_lane` 177 → 313; `obstacle_present` 273 → 301), i.e. the response to a given channel depends on which other channels are co-active.

## 5. Scientific interpretation

**Observations (directly recorded):**

1. C0 is completely silent over 3300.5 ms — the model with no external current produces nothing.
2. C1 and C2 produce activity strictly confined to the directly stimulated R neurons for the entire 3300.5 ms. Zero spikes outside R; zero active neurons outside R; zero current outside A_c.
3. C2 delivers ~7.4× C1's peak step current (13,976 vs 1,896 pA) including 43 pulse events, yet still does not spread beyond R.
4. C3 ignites: first outside-R spike at 101.5 ms, 248,689 outside-R spikes in the 200–300 ms bin, then a sustained ~513k spikes/100 ms (population ≈34 Hz) through 3300 ms. 99.976% of all C3 spikes occur outside the stimulated set; membrane potentials reach the −90/−50 mV rails; 63.7 spike transmissions per spike (≈997 million total).
5. In C3, 135 spikes occur on `coin_distance`-mapped neurons that received zero injected current — network-driven input to R.
6. Per-feature in-R responses to identical frames differ between C2 and C3.

**Interpretation (inference, flagged as such):**

- **The C3 avalanche is network ignition, not successful sensory routing.** Only 3,710 of 15,654,631 C3 spikes (0.024%) are in the stimulated set. The high non-stimulated spike count must not be described as evidence of functional sensory propagation.
- The C1/C2 confinement over the full duration shows that neither player-default drive alone nor visual drive alone develops recurrent self-sustaining activity in this model. Ignition in C3 therefore depends on the *joint* activation pattern — which neurons are co-active — rather than on total injected current magnitude, since C2's peak current exceeds C1's yet does not ignite. This experiment cannot localize the trigger (entry synapses, recruitment path); that would require targeted ablations outside the preregistered design.
- **Distinguishability from a task-related signal: not established.** The C3 outside-R activity is spatially diffuse (35,907 neurons), temporally saturated, and drives membranes to the rails — properties of a supercritical avalanche, not of a structured code. The within-R cross-channel interactions (point 6 above, and the network-driven `coin_distance` spikes) are consistent with signal interaction but are far too coarse to support a claim of task-related representation. No behavioural or decoder readout exists in this phase to test for one.

## 6. Limitations and invalidations

- **Attempt 1 (10:00 UTC) was INVALID** by `subprocess_runs_differ`: the C0 subprocess crashed because the archive pre-gate added in P3-T2.1 was invoked even for full-mode runs containing no cache-using condition. This was an infrastructure defect, not a simulation result. Fixed by scoping the gate to cache-using runs; regression test `test_c0_only_full_mode_requires_no_cache` added (33/33 tests pass). Attempt-1 artifacts are preserved as `p3_t2_full_attempt1_gate_defect.json` (+ sidecar). No seed, constant, protocol value or scientific parameter changed between attempts; the C3 in-process result (15,654,631 spikes, `09611c7d…`) was bit-identical in both attempts, as were C0–C2.
- Single seed, single graph, single initial state: determinism is exact, but robustness across seeds is not established by this design.
- The preregistered design includes no ignition negative controls (e.g. shuffled-frame or subset conditions beyond C1/C2).
- The mechanism of the C3 ignition and the source of the network-driven `coin_distance` spikes are not identified by this experiment.
- Point-neuron LIF model; the causal chain ends at sensory current injection — no motor output, no behaviour (per protocol).
- The final 100 ms bin is a 0.5 ms remainder and is near-empty by construction.

## 7. Artifacts

- `p3_t2_full.json` — machine-readable payload (verdict VALID)
- `p3_t2_full.sidecar.json` — reproducibility sidecar (git state, hashes)
- `p3_t2_full_report.md` — this report
- `p3_t2_full_attempt1_gate_defect.json` (+ sidecar) — preserved INVALID first attempt
- Pre-existing `p3_t2_smoke.json` and `p3_t2_preflight_600ms.json` untouched
