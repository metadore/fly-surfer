# P3-3C.5 — Pilot Degeneracy Investigation

**Status:** audit-only investigation. No simulation was executed and no frozen file was modified.
**Date:** 2026-11-15
**Subject:** the authorized 42-instance pilot of seed `20261107`
(`experiments/phase_3c/results/p3_3c5_lane_encoding_pilot*`), whose outcome is
`INCONCLUSIVE_REFERENCE_DEGENERATE` (see `reports/P3_3C5_PILOT_EXECUTION_REPORT.md`).
**Final classification:** **MULTIPLE CONTRIBUTING FACTORS** (see §6 and the closing line).

---

## 1. Executive summary

The pilot's invariance is real, reproducible in the recorded artifacts, and **not** a mapping,
preprocessing or scheduling bug. It is explained by three factors that act together in this one
mapping realization and this one input regime:

1. **Stimulation dominance (proximate).** In every condition the only external current in the
   139,255-neuron network is the lane schedule: 800 pA total at every step, carried by four full
   200 pA entries in step mode and by four-to-eight entries during a 50 ms crossfade ramp
   (`input_audit`). The four CENTER neurons are themselves directly stimulated at 200 pA for one
   contiguous block. With
   `C = 200 pF`, `g_L = 10 nS`, `V_rest = −65 mV`, `V_th = −50 mV` and no adaptation, that step
   produces a stereotyped LIF train: first spike 28.0 ms after block onset, then one spike every
   32.5 ms. The recorded CENTER trains are exactly this, in every step-mode condition.
2. **No active predecessor→CENTER pathway (structural, in this mapping).** All 9 ordered
   lane-pair synapse sums among the 12 stimulated neurons are **0**. CENTER's only presynaptic
   partners are three non-stimulated neurons (`54786`, `125168`, `134850`), and **no
   non-stimulated neuron fired in any of the 42 runs** (`outside = 0` everywhere). Therefore no
   synaptic current reached CENTER at any time, and the CENTER membrane state at its onset was
   identical in C1 and C2.
3. **Readout/design consequence.** M6′ measures the directly stimulated CENTER group over
   `onset + [0, 150) ms` in 3 × 50 ms bins. Because (1) and (2) make that response a fixed
   function of the CENTER block alone, M6′ is constant across every step-mode condition:
   `26.6667 Hz` for every step-mode condition with a CENTER block (28 of the 35 CENTER-bearing
   conditions). The seven crossfade
   conditions that ramp into CENTER (`XF_C1`, `XF_C2`, `XF_C3`, `XF_C4`, `XF_LCLR`, `XF_RLCL`,
   `XF_LRLC`) give `20.0000 Hz` — which shows the readout does respond to the *CENTER current
   waveform*, but never to predecessor identity.

Consequently `Δ_C(C1,C2) = 0.0000 Hz`, per-neuron `Δ_C(i) = [0,0,0,0]`, the R200 predicted
LEFT and RIGHT values are both `26.6667 Hz`, and both R150 reference ranges are zero width.

**Verified, not inferred:** the C1 and C2 CENTER spike trains are *bit-identical* (same 24 spike
times, onset-relative `28.0, 60.5, 93.0, 125.5, 158.0, 190.5` ms on each of the four neurons), so
the aggregate equality is not concealing sub-bin timing differences. The post-window bin (`s3`)
is also identical, so the window boundary is not concealing a divergence.

**Not established:** that the connectome cannot discriminate lanes, or that the main seeds
`20261104/20261105/20261106` will behave the same. This pilot used one mapping draw; three of the
four LEFT neurons have no directed path to any CENTER neuron at all in the connectome, and the
fourth's shortest path is 7 synapses, but that is a property of *this draw*, not of the graph.

---

## 2. Verified pilot artifact inventory and hashes

All hashes below were recomputed at the time of this investigation and match the values recorded
in `reports/P3_3C5_PILOT_EXECUTION_REPORT.md` §2 and §9.

### 2.1 Frozen inputs

| File | SHA-256 (verified) |
|---|---|
| `configs/p3_3c5_lane_encoding.yaml` | `21e4257d7022a7333fa84bef37df489e25e31b016080dfcd64ef0029498df638` |
| `experiments/phase_3c/p3_3c5_lane_encoding.py` | `c167adf758547440ce3366246cec06a44e75ec46262a8413f9e9eea6064f9c04` |
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md` | `d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f` |
| `docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md` | `44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd` |
| `docs/P3_3C5_IMPLEMENTATION_FREEZE_RECORD.md` | `7528ed55c576ed12a8df19fac96ac895897d268b4a04841081c119c8303ba835` |
| `tests/test_p3_3c5_lane_encoding.py` | `e8281529f31a208709bd02d3ec59ef528c72c4fd7f5e9e034df92ade16995f73` |

### 2.2 Pilot outputs and execution report

| Artifact | SHA-256 (verified) |
|---|---|
| `experiments/phase_3c/results/p3_3c5_lane_encoding_pilot.json` | `d3d9bd2de220bad0248e39f1b1ef82de94f92780432da4614b4d0c1358db40bd` |
| `..._pilot.sidecar.json` | `4eec36d22cda59df37bb50757421e4dec2e710968db1ec18cedecd131732f983` |
| `..._pilot_report.md` | `5fbb51306869b6de37d36798bcc437a327c888946d0818b12893da80d1e6384f` |
| `..._pilot_spikes.npz` | `1397be0779609dace64307bb58230f0f429794cc65d7ed2a121be04efb319bc3` |
| `reports/P3_3C5_PILOT_EXECUTION_REPORT.md` | `20ca5c774092447c306806b85ef606bbc066e951e007fcfd5956a0a69effcc2d` |

Cross-checks:

- `sidecar.output_sha256` equals the actual JSON hash → **MATCH**.
- `sidecar.spike_times_sha256` equals the actual `.npz` hash → **MATCH**.
- `sidecar.campaign = "pilot"`; the `.npz` holds 84 arrays (42 conditions × times/indices).
- Recomputed `mapping_signature` for seed `20261107` using the frozen runner is
  `a3c1aa1c4a83df38ed12e113e891caa260bee3d539764545d5e8f927946c56e8`, identical to
  `pilot_json.mappings["20261107"].mapping_sha256` → **MATCH**.
- `pilot_json.runs["20261107"]` has 42 entries; all applicable gates E1–E9 and E12–E16 pass and
  E10 is recorded as `not_applicable_for_pilot`; `analysis = {}` and `campaign_outcome = null`
  (the pilot checks are not computed by the runner).

---

## 3. Input-mapping trace (Investigation A)

### 3.1 Chain, with source references

1. **Condition → lane sequence.** Each condition is an explicit 12-frame lane list at 50 ms
   spacing (`configs/p3_3c5_lane_encoding.yaml`, `conditions` block, lines 74–324).
2. **Lane → population activation.** `LanePopulation.encode(lane)` returns a one-hot vector:
   the four neurons of the selected lane are set to the encoder `amplitude` (1.0) and all others
   to `baseline` (0.0) (`sensory/population_encoder.py:188-197`; spec `amplitude`/`baseline` at
   `:52-55`; config `configs/sensory_config.yaml` `player_lane` amplitude 1.0, baseline 0.0).
3. **Population → global neuron indices.** The `player_lane` mapping assigns four disjoint
   neurons per lane (`build_mapping` `experiments/phase_3c/p3_3c5_lane_encoding.py:762-771`;
   `lane_groups` `:784-798`). The pilot's E7 mapping is:

   | Lane | Graph indices | Root IDs |
   |---|---|---|
   | LEFT | 110026, 87844, 109398, 56659 | 720575940632675212, 720575940628307077, 720575940632528697, 720575940622684585 |
   | CENTER | 43929, 82831, 71067, 41234 | 720575940620491028, 720575940627436952, 720575940625291964, 720575940619930161 |
   | RIGHT | 56974, 33538, 134181, 132622 | 720575940622734853, 720575940618056916, 720575940644810184, 720575940642996365 |

   The 12 indices and the 12 root IDs are all distinct, and the indices resolve to exactly these
   root IDs on the loaded connectome (verified). Pools are `visual_left` / `visual_center` /
   `visual_right` (E7 detail; pool sizes 5,892 / 76 / 5,458 per preregistration line 304).
4. **Activation → current schedule.** `SensoryInputScheduler` encodes each segment, multiplies
   by the configured feature current (200 pA), and stores per-segment value vectors
   (`sensory/input_scheduler.py:127`, `_values_at` `:162-174`); `apply` adds them to the current
   vector (`:176-183`). `build_scheduler` (`experiments/phase_3c/p3_3c5_lane_encoding.py:814-835`)
   sets `transition_ms` 0 (step) or 50 (crossfade).
5. **Schedule → simulator.** `BrainSimulator.run` adds `input_schedule.apply(step, step*dt,
   current)` to the per-step input current (`brain/brain_simulator.py:252-253`) before
   `neurons.step(current)` (`:259`). Background current, noise and the Phase-2 stimulus are all
   disabled (`experiments/phase_3c/p3_3c5_lane_encoding.py:2071-2087`).

### 3.2 Reconstructed per-step current (read-only replay of the frozen scheduler)

Applying the frozen scheduler to a zero current vector yields these lane blocks (each active
lane = its four neurons at 200 pA):

| Condition | Block timeline (0 → 600 ms) |
|---|---|
| C1 | LEFT 0–200 · CENTER 200–400 · RIGHT 400–600 |
| C2 | RIGHT 0–200 · CENTER 200–400 · LEFT 400–600 |
| C3 | LEFT 0–150 · CENTER 150–300 · RIGHT 300–450 · LEFT 450–600 |
| C4 | LEFT 0–150 · RIGHT 150–300 · CENTER 300–450 · LEFT 450–600 |
| K_C | CENTER 0–600 |
| N0 | no scheduler (`None`), zero current |

Sampled checks: at t = 100 ms in C1 the nonzero entries are the four LEFT indices at 200 pA; at
t = 250 ms in both C1 and C2 they are the four CENTER indices at 200 pA; at t = 199.5 ms the
CENTER current is still zero in both. Every step-mode condition injects exactly four 200 pA
entries at every step (total 800 pA), as recorded in each run's `current_audit`
(`nonzero_counts_observed = [4]`, `total_current_min_pa = total_current_max_pa = 800.0`,
`outside_nonzero_entries = 0`, `stimulated_set_size = 12`). Crossfade conditions report
`nonzero_counts_observed = [4, 8]` and still conserve 800 pA
(`configs/p3_3c5_lane_encoding.yaml:511-514`). N0 has `stimulated_set_size = 0`,
`total_current_max_pa = 0.0`.

### 3.3 Do distinct conditions collapse to the same input? No.

- The 42 recorded `schedule_digest` values are all distinct.
- An independent reconstruction of the full 12-neuron, 1201-step current waveform also yields
  42 distinct profiles.
- The only identical CENTER profiles are the **intended matched blocks**:
  `{C1, C2}`, `{R200_LRC, R200_RLC}`, `{C3, R150_LCLR, R150_RCLL}`,
  `{C4, R150_LLCR, R150_RLCL}`, `{R150_LLRC, R150_LRLC, R150_RLLC}`, and the intended
  no-CENTER controls. C1 and C2 have identical CENTER current by design (the matched contrast)
  and differ only in the predecessor block (LEFT vs RIGHT).
- Per-condition charge confirms the design: e.g. `C1: Q_L = 160000, Q_C = 160000,
  Q_R = 160400` vs `C2: Q_L = 160400, Q_C = 160000, Q_R = 160000` pA·ms (the extra 400 pA·ms is
  the 0.5 ms trailing tail held by the last frame). The CENTER charge is identical.

**Conclusion A:** the input-to-network mapping is faithful. LEFT and RIGHT generate different
inputs, the intended neuron IDs receive them, the differences survive scheduling, and no condition
mapping collapses distinct inputs. There is **no mapping issue**.

---

## 4. Timing and stimulation analysis (Investigation B)

### 4.1 Frozen timing

Duration 600.5 ms, dt 0.5 ms, 1201 steps, 12 frames at 0, 50, …, 550 ms; step transitions are
0 ms, crossfade transitions 50 ms (`configs/p3_3c5_lane_encoding.yaml:31-41`). CENTER onsets are
200.0 (C1, C2), 150.0 (C3), 300.0 (C4), 0.0 (K_C), derived as `sequence.index("C") * 50`
(`center_onset_ms`, `experiments/phase_3c/p3_3c5_lane_encoding.py:727-731`).

### 4.2 Where the predecessor-dependent input occurs

- In C1 the predecessor input (LEFT) occupies 0–200 ms; in C2 (RIGHT) the same interval.
- The measurement window is 200–350 ms; the next transition is at 400 ms.
- The predecessor current never overlaps the window, and no predecessor-driven spike exists after
  200 ms: the 12 stimulated neurons' LAST spikes in their predecessor blocks are before the
  block boundary, and `outside = 0` means nothing else fires at all.
- Gate E16 independently confirms `C1 ≡ T200_LC` and `C2 ≡ T200_RC` before 400 ms.

### 4.3 The `4, 8, 4, 8` burst is identical only when the current waveform is identical

Per-50 ms-frame spike totals of the four CENTER neurons:

| Condition | CENTER per-frame counts (0…550 ms) |
|---|---|
| C1 | `[0,0,0,0,4,8,4,8,0,0,0,0]` |
| C2 | `[0,0,0,0,4,8,4,8,0,0,0,0]` |
| R200_LRC | `[0,0,0,0,0,0,0,0,4,8,4,8]` |
| R200_RLC | `[0,0,0,0,0,0,0,0,4,8,4,8]` |
| XF_C1 | `[0,0,0,0,0,8,4,8,0,0,0,0]` |
| XF_LCLR | `[0,0,0,0,8,4,4,0,0,0,0,0]` |
| XF_RLCL | `[0,0,0,0,0,0,0,8,4,4,0,0]` |

So the step-mode burst is identical across C1, C2 and the R200 pair (and every R150 step
condition), because the CENTER current step is identical. When the CENTER current ramps
(crossfade), the burst changes. This is the signature of a readout driven by its own input
waveform, not by predecessor identity.

### 4.4 The response is analytically the LIF response to a 200 pA step

With `C = 200 pF`, `g_L = 10 nS` (`tau_m = 20 ms`), `V_rest = −65 mV`, `V_th = −50 mV`,
`V_reset = −68 mV`, refractory 2 ms (`brain/neuron_model.py:7-12, 25-57`), a 200 pA step gives a
steady state of `−45 mV`. From rest the threshold is reached at `20·ln(20/5) ≈ 27.7 ms`, observed
as the first spike at **28.0 ms**. After reset the threshold is reached at `20·ln(23/5) + 2.0 ≈
32.5 ms`, observed as the **32.5 ms** period. All step-mode conditions record exactly this: first
CENTER spike latency `28.0 ms` relative to their own block onset (28 of 35 conditions; the seven
crossfade conditions that ramp in record `58.0 ms`; `XF_CLRL`, which starts with full CENTER
current at t = 0, records `28.0 ms`).

### 4.5 Firing follows external current timing, not predecessor identity

- First CENTER spike latency is 28.0 ms after each block onset in every step-mode condition, for
  onsets 0, 150, 200, 300, 400 and 450 ms (absolute first spikes 28.0, 178.0, 228.0, 328.0,
  428.0, 478.0 ms).
- The per-lane burst appears only inside that lane's own block and has the same shape in every
  block.
- `outside = 0` in 42/42 runs, so no other neuron's timing could carry information.

**Conclusion B:** stimulation dominance and timing explain the recorded response. The timing is
not "wrong" relative to the frozen protocol — it is exactly as specified — but the frozen design
leaves the readout with no condition-dependent input to reflect.

---

## 5. CENTER readout analysis (Investigation C)

### 5.1 What is measured

`measure_condition` (`experiments/phase_3c/p3_3c5_lane_encoding.py:1093-1246`) computes, for
conditions with a CENTER frame:

- `state_relative_counts(times, indices, groups["center"], onset, bins=3, bin_ms=50)`
  (`:1129-1137`), i.e. half-open bins `[onset, onset+50)`, `[+50, +100)`, `[+100, +150)`
  (`state_relative_counts` `:995-1000`; `bin_count_matrix` `:976-992`);
- per-neuron rates `counts / 0.05 s` (`rates_from_counts` `:1010-1011`);
- `m6_prime`: mean over the 3 bins and then over the 4 CENTER neurons (`:1014-1022`);
- the primary contrast `Δ_C(C1,C2) = M6′(C1) − M6′(C2)` (`:1338-1342`), which carries
  per-neuron rows (`subtract_measurement` `:1042-1060`).

The readout population is `groups["center"]` — **the same four neurons that receive the 200 pA
CENTER current**. This is the protocol's defined `G_C` (preregistration lines 473–534), not an
implementation mistake.

### 5.2 Recorded values

- All 35 CENTER-bearing conditions: 28 give counts `[[1,2,1]×4]` → `20/40/20 Hz` →
  `M6′ = 26.6667 Hz`; the 7 ramp-in crossfade conditions give `[[0,2,1]×4]` → `0/40/20 Hz` →
  `M6′ = 20.0000 Hz`.
- C1 and C2: `[[1,2,1]×4]`, `M6′ = 26.6667 Hz`, per-neuron Δ_C(i) = `[0,0,0,0]`.
- R200: `R200_RLC` (pred-LEFT) = `R200_LRC` (pred-RIGHT) = `R200_CLR` = `R200_CRL` =
  `26.6667 Hz`. R150: 5 pred-LEFT values and 2 pred-RIGHT values, all `26.6667 Hz`; both range
  widths 0.0.
- Post-window bin `s3` ([350, 400) ms) is also identical: C1 and C2 both `[2,2,2,2]`, and the
  4-bin arrays are both `[[1,2,1,2]×4]`.

### 5.3 Identical aggregates do not conceal timing differences

The recorded C1 and C2 CENTER spike lists are exactly equal, including absolute times: 24 spikes,
`228.0, 260.5, 293.0, 325.5, 358.0, 390.5` ms on each of the four neurons. The 3 × 50 ms window
therefore contains exactly `1 + 2 + 1` spikes per neuron in both conditions. There is no sub-bin
difference to hide, and no transient to miss: the train is periodic with constant latency and
period from the first spike onward.

### 5.4 Connectivity from the stimulated set to CENTER

Directed graph as loaded from `datasets/processed/connectome.npz` (139,255 nodes, 3,732,460
edges, 50,666,648 synapses; `brain/connectome_loader.py`):

- **Within the 12 stimulated neurons:** 0 synapses for every ordered lane pair
  (L→L, L→C, L→R, C→L, C→C, C→R, R→L, R→C, R→R are all 0).
- **Into CENTER:** only three presynaptic partners, all non-stimulated:
  `54786 → 82831 (10 syn)`, `54786 → 41234 (8 syn)`, `125168 → 71067 (5 syn)`,
  `134850 → 82831 (6 syn)`.
- **Two-hop:** zero `LEFT→X→CENTER` and zero `RIGHT→X→CENTER` paths for any non-stimulated `X`.
  The only two-hop paths are CENTER→intermediary→CENTER (`82831→134850→82831`,
  `82831→54786→82831`, `82831→54786→41234`, `71067→125168→71067`, `41234→54786→82831`,
  `41234→54786→41234`).
- **Multi-hop shortest paths (reverse BFS):** RIGHT neurons have shortest directed paths to a
  CENTER neuron of 5–6 synapses; three of the four LEFT neurons have **no directed path to any
  CENTER neuron**, and the fourth's shortest path is 7 synapses.
- **Why the relays stay silent:** the only drive the three intermediaries can receive from the
  stimulated set is from CENTER, totalling at most 127.0 pA (`54786`), 46.0 pA (`125168`) and
  67.5 pA (`134850`) at peak, computed with the frozen weight law `12.0 × syn^0.75`. All are below
  the 150 pA rheobase (`brain/neuron_model.py:54-57`), and the measured `outside = 0` confirms
  none crossed threshold. With no spiking relay, no multi-hop route is active.

### 5.5 Recording scope

The recorder covers all `graph.n_nodes` neurons (`brain/brain_simulator.py:129`,
`brain/neural_activity.py:19-72`), and the largest run recorded 72 spikes against a capacity of
5,000,000. `outside = 0` is therefore a network property, not a recording-scope artifact.

### 5.6 Could a different window help?

Within the frozen design, no: the CENTER train is constant in latency/period and the post-window
bin is identical across C1/C2, so every onset-aligned window over the CENTER block yields the same
values in both conditions. A window can only expose a difference that exists in the spike train.
Here none exists.

**Conclusion C:** the readout measures the intended population and interval and computes correctly,
but that population has **no condition-dependent drive** in this pilot. The limitation is in what
the readout can reflect, not in the binning arithmetic or the window boundaries.

---

## 6. Competing explanations and evidence (Investigation D)

### 6.1 Observations (recorded or directly computed)

- O1. 42/42 schedules distinct; 12/12 stimulated indices distinct and matched to E7.
- O2. Every step-mode condition injects only four 200 pA entries per step (800 pA total).
- O3. CENTER step-mode response: first spike 28.0 ms after onset, period 32.5 ms, counts
  `[[1,2,1]×4]` in the measured window, `M6′ = 26.6667 Hz`.
- O4. C1 and C2 CENTER spike trains are bit-identical; `Δ_C = 0`, per-neuron Δ_C(i) = `[0,0,0,0]`.
- O5. All R200 and R150 reference values are `26.6667 Hz`; both R150 ranges have width 0.
- O6. `outside = 0` in 42/42 runs; maximum total spikes 72.
- O7. Zero synapses among the 12 stimulated neurons; CENTER has 3 non-stimulated presynaptic
  partners; no L/R→X→C two-hop path; shortest structural L/R→C path is 5–7 synapses.
- O8. Crossfade ramp-in conditions shift the CENTER response (`[[0,2,1]]`, `20 Hz`, 58 ms latency).

### 6.2 Interpretations and classifications

| # | Candidate explanation | Classification | Evidence |
|---|---|---|---|
| 1 | Input-to-network mapping issue | **NOT SUPPORTED** | O1; E7 disjointness; indices↔root IDs verified; mapping signature matches; intended IDs stimulated; CENTER identity is a property of the graph (O7), not of the mapping code. |
| 2 | Input timing or stimulation dominance | **DIRECTLY SUPPORTED** | O2–O4, O8: the response is the analytic LIF response to the CENTER step; changing only the CENTER waveform changes the response; changing only the predecessor does not. |
| 3 | Readout or measurement-window limitation | **PARTIALLY SUPPORTED** | O3–O5: the readout is the directly stimulated population and is invariant for step inputs. But O4/O5 show no hidden transient or sub-bin difference, and the metric computes as specified, so the fault is in the available drive, not in the measurement arithmetic. |
| 4 | Another implementation or experimental-design explanation | **PARTIALLY SUPPORTED** | O6, O7: the preregistered mechanism for H2 was "synaptic filtering, spike reset/refractory nonlinearity or recurrent input" (prereg lines 147–153); in this pilot none was engaged — no synaptic input reached CENTER and the network stayed silent (H5's silent-network precondition held, with the consequence that the readout has no condition-dependent drive). No implementation defect identified. |
| 5 | Insufficient evidence to distinguish | **NOT SUPPORTED for this pilot** | The evidence distinguishes the factors: mapping is excluded, while stimulation dominance and readout scope are directly evidenced. Insufficiency applies only to generalization beyond this seed (§9). |

### 6.3 Direct answers to the brief's sub-questions

- **Do LEFT and RIGHT generate different inputs?** Yes (schedule distinct; Q_L/Q_R differ).
- **Do the intended IDs receive them?** Yes (`stimulated_indices` = the E7 set; E2/E3 pass).
- **Do differences survive preprocessing/scheduling?** Yes — but they are confined to the
  predecessor block; CENTER is not scheduled during 0–200 ms in C1/C2.
- **Does any condition mapping collapse distinct inputs?** No. The only shared profiles are the
  intended matched blocks.
- **Is the `4,8,4,8` burst identical across relevant conditions?** Yes in all step-mode
  conditions, because the CENTER current step is identical; no in crossfade conditions, whose
  current ramps differ.
- **Does predecessor-dependent input occur inside the measurement window?** No (0–200 ms only;
  window 200–350 ms; next transition 400 ms).
- **Could stimulation dominate the measured CENTER response?** Yes, and it demonstrably does:
  the response is fully determined by the CENTER step.
- **Does firing follow external current timing rather than predecessor identity?** Yes
  (28.0 ms latency after every block onset; identical periodic train).
- **Do the four CENTER neurons receive condition-dependent input?** No: no active presynaptic
  partner, identical membrane state at onset, identical current from onset.
- **Do recorded spikes vary across conditions?** In step-mode, no; only when the CENTER current
  waveform itself changes (crossfade).
- **Could windows hide a transient?** No: the trains are bit-identical, and the post-window bin is
  identical.
- **Does the readout measure the intended population/interval?** Yes — `groups["center"]`,
  `onset + [0,150)` ms, exactly as frozen.
- **Do identical aggregates conceal timing differences?** No.

### 6.4 Attribution

The invariance is **most consistent with a combination** of (2) stimulation dominance and
(3) readout scope, operating on a mapping realization that supplies (4) no active
predecessor→CENTER route. It is **not** consistent with (1) a mapping issue, and the evidence is
sufficient to distinguish this for the pilot (5).

---

## 7. Exact source references

| Reference | What it establishes |
|---|---|
| `experiments/phase_3c/p3_3c5_lane_encoding.py:727-731` | `center_onset_ms = sequence.index("C") * 50` |
| `...:741-759` | base sensory config assertions (lane coding, 4/lane, 1.0 amplitude, 0 pA background/noise) |
| `...:762-771` | mapping construction and lane group order |
| `...:784-798` | four disjoint neurons per lane, total 12 |
| `...:814-835` | scheduler build; step/crossfade transition; stimulated-set size check |
| `...:976-992` | per-neuron counts in half-open bins |
| `...:995-1000` | state-relative bin edges `onset + [0, bins] × 50 ms` |
| `...:1010-1022` | rates and `m6_prime` aggregation |
| `...:1093-1246` | `measure_condition`: lane absolute bins, outside activity, CENTER state-relative block, latency/peak |
| `...:1117-1127` | outside-spike definition (not in the 12 stimulated) |
| `...:1129-1146` | CENTER window and M6′ |
| `...:1185-1202` | first CENTER spike latency and peak |
| `...:1338-1342` | primary contrast C1 vs C2 on M6′ |
| `...:1401-1426` | R200/R150 reference extraction and degeneracy predicates |
| `...:2058-2117` | run configuration: `stimulus=None`, background 0, noise 0, seed 20261104, recording, digests |
| `brain/brain_simulator.py:237-269` | step loop: current assembly, `input_schedule.apply`, `neurons.step`, record, propagate |
| `brain/neuron_model.py:7-12, 25-57` | LIF equations, τ = C/g = 20 ms, rheobase = 150 pA |
| `brain/synapse_model.py:75-121` | weight = 12.0 × syn^0.75, delay 1 ms, exponential decay |
| `brain/synapse_model.py:177-190, 192-220` | current decay and delayed spike delivery |
| `brain/neural_activity.py:19-72` | global spike recorder over all n_nodes |
| `sensory/input_scheduler.py:127, 162-174, 176-183` | encoded values, crossfade interpolation, additive `apply` |
| `sensory/population_encoder.py:188-197` | one-hot lane encoding (amplitude on 4 neurons) |
| `configs/p3_3c5_lane_encoding.yaml:31-41` | duration, dt, n_steps, frame interval, transition durations |
| `configs/p3_3c5_lane_encoding.yaml:74-324` | the 42 condition sequences |
| `configs/p3_3c5_lane_encoding.yaml:326-345` | state-relative bins, frozen CENTER onsets |
| `configs/p3_3c5_lane_encoding.yaml:406-437` | R200/R150 reference definitions, causal decomposition |
| `configs/p3_3c5_lane_encoding.yaml:438-448` | M6′ measurement definition |
| `configs/p3_3c5_lane_encoding.yaml:505-525` | gates and pilot checks |
| `configs/simulation_config.yaml:25-49` | synapse weight law and time constants |
| `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md:119-136` | why C1/C2 at CENTER is primary; causality argument |
| `...:142-181` | H1–H6, including H2's mechanism assumption and H5's silent-network precondition |
| `...:473-534` | G_C definition, M6′ and Δ_C(i) arithmetic |
| `...:555-575` | order/history vs static-lane rationale; K_C caveat |
| `...:744-767` | outcome classes and `INCONCLUSIVE_REFERENCE_DEGENERATE` |
| `...:947-959` | pre-registration sequence: pilot must verify reference non-degeneracy before main |
| `...:963-980` | limitations, including predecessor-pool confounding |

---

## 8. What the pilot establishes

1. The implementation executed correctly on this seed: 42/42 runs, all applicable gates pass,
   mapping signature and E7 groups verified, inputs distinct, no mapping collapse.
2. In this mapping realization and this lane-only input regime, the CENTER readout is a
   deterministic function of the CENTER 200 pA block. Predecessor identity (LEFT vs RIGHT) does
   not modulate M6′ within 200–350 ms, and no condition-dependent synaptic input reaches CENTER.
3. All reference sets are degenerate on this seed: R200 predicted LEFT = RIGHT = 26.6667 Hz and
   both R150 ranges have width 0.0. The protocol's pre-main pilot gate (reference
   non-degeneracy) is therefore not satisfied.
4. The network produced no activity outside the 12 directly stimulated neurons in any run, so the
   pilot is a sparse direct-regime observation: the readout reflects its own stimulation, not a
   network-computed history signal.
5. The metric and window compute as specified; the equality is genuine at the spike-train level,
   not an aggregation or binning artifact.

## 9. What the pilot does not establish

1. **It does not establish that the connectome cannot discriminate lanes.** The shortest
   structural routes from RIGHT to CENTER are 5–6 synapses, and one LEFT neuron has a 7-synapse
   route; they were inactive, not absent. Three of four LEFT neurons have no directed path to
   CENTER *in this draw* — a property of the drawn four neurons, not of the graph.
2. **It does not establish the behavior of the main seeds** `20261104/20261105/20261106`.
   Different draws select different neurons, possibly with direct predecessor→CENTER edges or
   stronger relays, and `outside` activity on those seeds is unknown. No main-seed mapping was
   computed or simulated in this investigation.
3. **It does not establish that M6′, the 200–350 ms window or the 50 ms bins are wrong.** They
   compute exactly as frozen; the absence of signal is upstream of the metric.
4. **It does not establish that a history effect would be absent under a different input
   regime** (e.g. a regime that engages the network or drives the readout indirectly). That
   experiment has not been run.
5. **It does not establish any biological claim** about lane history coding, or that the encoder
   is sufficient, or that the model is a valid fly model.
6. **It does not authorize** any parameter change, timing change, readout change or protocol
   amendment.

## 10. Recommended protocol-owner decision

**Recommendation: do not proceed to the main matrix under the current frozen protocol.**

Grounds:

- The preregistration requires the pilot to verify reference non-degeneracy before the main run
  (lines 947–959). That check failed on the pilot seed.
- The outcome order (lines 750–755) assigns `INCONCLUSIVE_REFERENCE_DEGENERATE` to a degenerate
  reference and instructs "report the degeneracy; no separation claim". Running main now would
  most plausibly reproduce the same structure on more seeds, while the protocol's own gate says
  the pilot must pass first.

Decision options for the protocol owner (each requires a new amendment, freeze and hashes; none
is authorized or implemented here, and no parameter values are proposed):

1. **Accept and stop.** Record the pilot as a pre-main degeneracy finding and close P3-3C.5
   without a main run.
2. **Amend the protocol with a pre-registered mechanism precondition**, decided before looking at
   main data — e.g. a requirement that the readout receive some active input path from the
   predecessor (which would have to be defined and frozen), plus the action to take when it fails.
   This is a design change, not a bug fix.
3. **Redesign the readout or regime** (e.g. read a population not directly stimulated, or use a
   pre-registered input regime that engages the network), then re-freeze and repeat the pilot.
   This changes the scientific question and requires explicit approval.

The investigation does not choose among these; it only establishes that the current pilot cannot
serve as the pre-main gate as written.

## 11. No simulation executed; no frozen file modified

- **No simulation was run.** No `BrainSimulator.run` call, no main-campaign run, no determinism
  run, no replacement experimental output. The 42 recorded runs are the only runs that exist, and
  they were produced by the previously authorized pilot execution.
- **No frozen file was modified.** All six frozen hashes in §2.1 are unchanged; the pilot
  artifacts and execution report hashes in §2.2 are unchanged.
- **What this investigation did:**
  1. recomputed SHA-256 for the six frozen inputs, the four pilot artifacts and the execution
     report;
  2. read the frozen runner, simulator, neuron/synapse models, scheduler, encoder and configs;
  3. loaded the recorded pilot JSON, sidecar and spike NPZ and recomputed per-condition counts,
     rates, M6′, Δ_C and spike times from the recorded arrays;
  4. reconstructed the **input schedule only** with the frozen scheduler applied to a zero current
     vector (no neuron integration), to trace predecessor identity → neuron IDs → per-step
     current;
  5. inspected the loaded connectome adjacencies among the 12 stimulated neurons, into CENTER,
     and the two-hop and shortest directed paths, using the frozen weight law.
- **No preregistration or amendment was changed; no frozen configuration, runner or tests were
  modified; no neuron/synapse parameter, current, timing, readout neuron or window was tuned.**
- Working tree: this investigation adds exactly one file, this report. Before writing it,
  `git status --short` listed 231 entries (21 modified, 210 untracked) — those are the pre-existing
  changes from earlier authorized work. After writing, the count is 232 with this report as the
  only delta. Nothing was staged, committed, pushed, reset, cleaned, stashed, checked out or
  deleted.

---

## Final classification

**MULTIPLE CONTRIBUTING FACTORS.**

The pilot invariance is produced by (i) absence of an active predecessor→CENTER route in this
mapping realization (zero synapses among the 12 stimulated neurons, no two-hop L/R→CENTER path,
the only relays subthreshold, and `outside = 0` in all 42 runs), (ii) dominance of the readout by
its own 200 pA stimulation (a stereotyped 28.0 ms latency / 32.5 ms period LIF train), and
(iii) a readout that measures that directly stimulated population over an onset-aligned window,
so M6′ is a fixed function of the CENTER block. The mapping itself is correct and inputs are
distinct. The result is a pre-main degeneracy of the current design, not a proven property of the
connectome.
