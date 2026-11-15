# P3-T12 network ignition and stability characterization

**Phase:** P3-T12
**Verdict:** VALID (0 invalidations; all gates passed)
**Preregistered protocol:** `docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md`
(sha256 `49c09424…b173`)
**Config:** `configs/p3_t12_characterization.yaml` (sha256 `18018b68…ea03`)
**Full artifact:** `experiments/phase_3c/results/p3_t12_network_characterization.json`
(sha256 `c1555968…465b`, 2,004,535 bytes)
**Analysis summary:** `experiments/phase_3c/results/p3_t12_analysis_summary.json`
(sha256 `da027296…a4d`)
**Preflight:** `p3_t12_preflight.json` (sha256 `3974bd00…7463`) and
`p3_t12_preflight_report.md`
**Runtime:** 497.1 s (seven conditions, two in-process repeats, two subprocess
repeats, full analysis).

---

## 1. Question and answer

The protocol asked how the configured network moves from localized current
injection into population-scale activity, and which measurements separate
bounded sparse discharge from the C3 regime. The characterization answers:

1. **C3 ignites as a fast recruitment avalanche.** Directly injected neurons
   first spike at 28 ms; the first spike outside the injected set follows at
   101.5 ms (+73.5 ms); 1 % of the graph is active by 240 ms, 10 % by 260 ms,
   and 90 % of the final active set by 300 ms. Peak recruitment is 7,168 newly
   active neurons per 10 ms bin.
2. **The ignited state is stationary, not a growing explosion.** Between
   1,210 ms and 3,300 ms the active count, population rate, membrane histogram
   and floor/refractory occupancy are essentially unchanged.
3. **The activity is self-sustaining without sensory drive.** In
   `C3-washout`, the 500 ms after the last possible drive step carry 2,568,015
   spikes at 36.88 Hz, versus 36.85 Hz in the equal-length pre-window — a ratio
   of 1.0008. There is no measurable decay.
4. **The system is numerically stable and bounded but strongly
   threshold-dominated.** All states are finite; the membrane never leaves
   [−90, −50]; 20.3 % of neuron-steps sit at the −90 mV floor and 5.1 % are
   refractory. Whether this regime is physiological is not established.
5. **The recruitment is graph-topological, not global.** Activity is present
   at hops 0–5 from the injected set; the 138 neurons at hops 6–10 and the
   10,637 neurons beyond 20 hops or unreachable fire zero spikes.

No claim about perception, learning, decisions, information routing or
behaviour is made. "Outside A_c" means "not eligible for current injection",
not "proven synaptically driven".

---

## 2. Gates and reproducibility

| Gate | Result |
| --- | --- |
| Loop equivalence, archived C3 | 9/9 checks true; spike hash `09611c7d…78305`, 15,654,631 spikes, 3,710 injected / 15,650,921 uninjected, first 28.0 ms, last 3,300.5 ms, min −90.0, max −50.000000069 mV |
| Scheduler signature | `1c3ab12d…8840`, matches the archived temporal and scheduler digests |
| Washout prefix (0–3,300.5 ms) | bit-identical counts, hash `09611c7d…78305`, 15,654,631 spikes |
| In-process repeats, 7/7 | identical |
| Subprocess repeats, C3 and C3-washout | identical, no differing hash keys |
| Condition checks | all conditions pass all applicable checks, nothing unevaluated |
| Invalidations | none of 11 rules triggered |
| Protected hashes | README, connectome, sensory config and the other fixed artifacts all match |
| Cache | `p3_t2_visual_frames.json`, 100 frames, file sha `9f950472…2154`, digest `2a857471…9166`, matches archived |

The archived-C3 equality is exact, including the 15,654,631 spike count and
the 3,710/15,650,921 injected/uninjected split. This establishes that the
instrumented stepper reproduces `BrainSimulator` at full duration, not only on
the synthetic test graph.

---

## 3. Headline measurements

All rates are per neuron over the stated window. `A_c` is the condition's
injected set.

| Condition | Spikes | Active | Active % graph | Outside A_c spikes | Outside A_c active | First spike | First outside A_c | Regime (P3-T3.1) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 0 | 0 | 0.00 % | 0 | 0 | — | — | none |
| C1 | 702 | 8 | 0.006 % | 0 | 0 | 28.0 ms | — | none |
| C2 | 2,560 | 61 | 0.044 % | 0 | 0 | 81.5 ms | — | none |
| C3 | 15,654,631 | 35,979 | 25.84 % | 15,650,921 | 35,907 | 28.0 ms | 101.5 ms | population_scale |
| no-player_lane | 2,858 | 65 | 0.047 % | 0 | 0 | 29.5 ms | — | none |
| no-train_lane | 2,802 | 59 | 0.042 % | 4 | 2 | 28.0 ms | 1,467.0 ms | sparse |
| C3-washout | 19,503,284 | 36,009 | 25.86 % | 19,499,327 | 35,937 | 28.0 ms | 101.5 ms | population_scale |

The P3-T3.1 classification is applied unchanged and remains **provisional**:
outside-R active neurons must exceed the size of R (138) and the outside-R rate
must be at least the reference rate. C3 satisfies both by three orders of
magnitude; the ablations do not. `no-train_lane` keeps its legacy
`ignited = true`, but its only outside activity is 4 spikes on 2 neurons at
hops 1 and 2 at 1,467–1,474 ms, which is why it is `sparse`, not
`population_scale`.

Partition detail for C3: 3,710 spikes (0.024 %) arise in the 138 injected
neurons and 15,650,921 (99.976 %) outside them; 72 of 138 injected neurons are
active versus 35,907 of 139,117 non-injected. The injected population is not
the engine of the steady state.

---

## 4. Ignition latency and recruitment

| Measurement | C3 | C3-washout |
| --- | --- | --- |
| First spike (injected) | 28.0 ms | 28.0 ms |
| First spike outside A_c | 101.5 ms | 101.5 ms |
| Delay, first injected → first outside | 73.5 ms | 73.5 ms |
| 1 % of graph active | 240 ms | 240 ms |
| 5 % of graph active | 250 ms | 250 ms |
| 10 % of graph active | 260 ms | 260 ms |
| 25 % of graph active | 350 ms | 350 ms |
| 25 / 50 / 90 % of final active count | 250 / 270 / 300 ms | 250 / 270 / 300 ms |
| Peak new active neurons per 10 ms | 7,168 | 7,168 |

Recruitment is not gradual. Newly active neurons per 10 ms stay in single
digits until roughly 200 ms, jump to 209, 944, 3,140, 6,212 and 7,168 between
210 and 230 ms, then fall back to double digits by 400 ms. The 10 % → 90 %
transition of the final active set takes about 40 ms.

The sparse conditions never approach this: C1, C2 and both ablations remain
below 0.05 % active and their 90 %-of-final times (60 ms, 1,350 ms, 1,350 ms,
1,470 ms) reflect a handful of neurons firing occasionally, not recruitment.

---

## 5. Firing-rate structure

| Measurement | C3 | C3-washout |
| --- | --- | --- |
| Population mean | 34.06 Hz | 34.58 Hz |
| Population peak (10 ms bin) | 37.02 Hz | 37.02 Hz |
| Active-neuron mean | 131.83 Hz | 133.72 Hz |
| Active-neuron median | 89.08 Hz | 90.36 Hz |
| Active-neuron p90 / p99 / max | 316.98 / 464.17 / 469.63 Hz | 321.49 / 470.81 / 475.25 Hz |
| Top 1 % share of spikes | 13.61 % | 13.61 % |
| Spikes per active neuron | 435.1 | 541.6 |

The ignited state is broad rather than a small clique: 35,979 neurons are
active, the top 1 % carry only 13.6 % of spikes, and the median active neuron
fires at 89 Hz. The upper tail sits just below the structural 500 Hz ceiling
imposed by the 2.0 ms refractory period (maximum observed 469.6 Hz in C3), so a
subset of neurons is firing at close to the maximum rate the model permits.

The low-activity conditions have median active rates of 9–30 Hz on 8–65
neurons and no population-scale rate at all (peak population rate ≤ 0.025 Hz).

---

## 6. Membrane state and time at bounds

| Measurement | C0 | C2 | C3 | C3-washout |
| --- | --- | --- | --- | --- |
| Exact min / max | −65 / −65 mV | −72.53 / −50.0003 mV | −90.0 / −50.000000069 mV | −90.0 / −50.000000034 mV |
| Neuron-steps at −90 floor | 0 % | 0 % | 20.26 % | 20.58 % |
| Neuron-steps refractory | 0 % | 0.0008 % | 5.11 % | 5.19 % |
| Neuron-steps within 0.05 mV of threshold | 0 % | 0.00006 % | 0.065 % | 0.066 % |
| Finite state | yes | yes | yes | yes |

Two distinct bounds must not be conflated:

* **−90 mV is an enforced floor clamp** (`np.maximum(V, −90)` every step). It is
  reached by 20 % of neuron-steps in C3 and is a genuine state.
* **−50 mV is the spike threshold**, followed by reset to −68 mV and a 2.0 ms
  refractory period. There is no upper clamp. The reported maximum of
  −50.000000069 mV is a near-threshold value at the end of a step, not a
  saturated rail; the "−50.000" seen in P3-T2 is the same value rounded.
  Near-threshold occupancy while not spiking is only 0.065 % of neuron-steps.

Late-window membrane snapshots are essentially stationary. At 1,210, 1,810,
2,410 and 3,010 ms the C3 histogram counts on the fixed −90…−50 mV edges differ
by less than 0.7 % per bin; mean −71.69 mV and standard deviation 12.90 mV are
unchanged to two decimals. The washout at 4,050 ms has the same distribution
(mean −71.70, std 12.91, 30,642 at floor, 7,673 refractory). The occupancy
pattern is bimodal: a floor pile (≈30.5k neurons), a broad mid-range mass, and
a small near-threshold population.

---

## 7. Persistence, temporal evolution and propagation

| Measurement | C3 | C3-washout |
| --- | --- | --- |
| 10 ms bins with any spike | 319 / 331 (96.4 %) | 394 / 406 (97.0 %) |
| Longest run of active 10 ms bins | 3,150 ms | 3,900 ms |
| Longest outside-A_c gap | 18.0 ms | 18.0 ms |
| Tail (last 500 ms) mean rate | 36.89 Hz | 36.88 Hz |
| Tail active neurons | 33,708 | 33,694 |
| Transmissions per spike | 63.66 | 63.64 |
| Cascade ratio: peak / plateau median | 9.31 / 1.0002 | 9.31 / 1.0001 |

Final-second spikes in ten 100 ms groups: 513,541 / 513,342 / 512,708 /
512,952 / 513,329 / 512,994 / 513,447 / 513,299 / 513,144 / 466,826 for C3,
and 513,185 / 512,830 / 513,479 / 513,271 / 513,144 / 513,112 / 513,547 /
512,739 / 512,862 / 467,018 for the washout. The last group is short because the
window ends at 3,300.5 / 4,050.5 ms; the preceding groups vary by < 0.15 %.

The cascade ratio (outside-A_c spikes in a bin divided by the preceding bin) is
a descriptive propagation index, not a branching ratio. It peaks at 9.31 during
the recruitment avalanche, then settles at 1.000, meaning one-for-one
replacement rather than growth. Sixty-three synaptic transmissions per spike
sustain the state.

---

## 8. Graph-topological recruitment

Directed unweighted hop distance from the injected set, C3:

| Hop bucket | Neurons | Active | Spikes | Mean rate | First active | Median first spike |
| --- | --- | --- | --- | --- | --- | --- |
| 0 (injected) | 138 | 72 | 3,710 | 8.15 Hz | 28.0 ms | 411.75 ms |
| 1 | 745 | 296 | 97,563 | 39.68 Hz | 101.5 ms | 261.75 ms |
| 2 | 11,712 | 4,281 | 2,131,878 | 55.15 Hz | 105.0 ms | 251.5 ms |
| 3 | 87,304 | 24,124 | 9,928,798 | 34.46 Hz | 193.0 ms | 262.0 ms |
| 4 | 26,960 | 6,952 | 3,425,187 | 38.49 Hz | 233.5 ms | 269.0 ms |
| 5 | 1,621 | 254 | 67,495 | 12.62 Hz | 244.5 ms | 281.25 ms |
| 6–10 | 138 | 0 | 0 | 0 | — | — |
| 11–20 | 0 | 0 | 0 | 0 | — | — |
| > 20 or unreachable | 10,637 | 0 | 0 | 0 | — | — |

Three observations:

* Onset time increases monotonically with hop distance (101.5 → 105 → 193 →
  233.5 → 244.5 ms), consistent with a wavefront spreading through the
  directed graph.
* The injected neurons have the **latest** median first spike (411.75 ms):
  fewer than half of the 72 active injected neurons fire before 412 ms. After
  ignition the injected population is a small minority of the activity.
* Activity stops at a structural boundary. Hops 0–5 contain about 128,480
  neurons and account for every spike; the remaining 10,775 neurons (7.7 % of
  the graph) are silent. "Global" here means "the reachable 5-hop component",
  not "the whole connectome".

The washout preserves the same bucket structure with slightly higher rates and
30 more active neurons; `no-train_lane` has exactly 2 spikes at hop 1 and 2
spikes at hop 2, on one neuron each, at 1,467 and 1,474 ms.

---

## 9. Washout: sustained activity without drive

`C3-washout` extends C3 by 750 ms. The last frame is at 3,300.0 ms, the
250 ms hold ceiling permits scheduled current through 3,550.0 ms, and the
first drive-free step is 3,550.5 ms. The silent window is
3,550.5–4,050.5 ms (500 ms).

| Measurement | Value |
| --- | --- |
| Prefix (0–3,300.5 ms) vs C3 | bit-identical, hash `09611c7d…78305` |
| Spikes in extension (3,300.5–4,050.5) | 3,848,653 |
| Mean rate over extension | 36.85 Hz |
| Silent-window spikes (3,550.5–4,050.5) | 2,568,015 |
| Silent-window rate | 36.88 Hz |
| Pre-window (3,050.5–3,550.5) rate | 36.85 Hz |
| Silent/pre rate ratio | 1.0008 |
| Silent-window active neurons | 33,694 |
| Spikes per 50 ms bin in silent window | 256,557 / 256,681 / 256,593 / 256,815 / 256,395 / 256,425 / 256,525 / 256,341 / 256,397 / 259,286 |
| Active neurons gained over extension | +30 (35,979 → 36,009) |
| Recorder use | 19,503,284 = 65.0 % of capacity |

The 50 ms bins vary by ±0.5 % across the silent window and the last bin is
slightly higher, not lower. There is no decay signature at this resolution.
The activity is therefore **sustained recurrent activity**, not merely drive
held over: the network continues at the same rate and with the same active set
for 500 ms after no scheduled current can reach it.

This does not establish that the state is a true attractor. A 500 ms window, a
single deterministic run and no perturbation test cannot separate a stable
fixed point from a very slow transient, a limit cycle, or a state that would
eventually collapse. The protocol's negative outcome (collapse) did not occur;
the positive outcome is bounded to 500 ms.

---

## 10. Ignition, stability and what the measurements do and do not show

The programme asked to distinguish five concepts. The evidence supports these
statements and no stronger ones:

| Concept | Status in this experiment | Basis |
| --- | --- | --- |
| **Network ignition** | Observed in C3 and C3-washout, absent in C0/C1/C2 and both ablations | 25.8 % of the graph active within ~350 ms; outside-R rate 34.09 Hz vs reference 8.15 Hz; provisional P3-T3.1 `population_scale` |
| **Sustained recurrent activity** | Observed for 500 ms after drive ends, at unchanged rate | Washout silent-window rate ratio 1.0008; stable active count and bins |
| **Physiological stability** | **Not established.** Numerically stable and bounded, but high-rate and floor-dominated | Finite states, [−90, −50] bounds, stationary histograms; 20 % floor occupancy, 5 % refractory, p99 464 Hz near the 500 Hz ceiling |
| **Useful sensory propagation** | **Not established** | Structural spread and timing are measured; no decoder, no readout, no behavioural consequence |
| **Task-relevant information transmission** | **Not established, not tested** | No information-theoretic measurement is part of P3-T12 |

What separates stable sparse activity from ignition in these data is not a
single threshold but a conjunction: population size outside R, rate relative to
R, a recruitment avalanche, and persistence. Sparse conditions have activity
(702–2,858 spikes) and are numerically stable, but no recruitment and no
population rate. C3 has all four. The P3-T3.1 label remains a *provisional
relational criterion*, not a preregistered absolute threshold.

---

## 11. Cross-condition reading (descriptive only)

* **C0** is silent: zero spikes, all membranes at rest. The simulation adds no
  activity without input.
* **C1** (neutral frames, 4 default player features) produces 702 spikes in 8
  injected neurons, all inside A_c, spread across the full 3.3 s. No spread.
* **C2** (10 non-player features) produces 2,560 spikes in 61 injected
  neurons, still zero outside A_c. A ten-feature schedule does not ignite.
* **C3** (all 14 features) ignites. The difference between C2 and C3 is the
  four player-related features (including `player_lane` and `player_speed`).
* **no-player_lane** and **no-train_lane** both collapse to C2-like totals
  (2,858 and 2,802 spikes) even though each retains 13 of 14 features. Removing
  either lane is sufficient to prevent ignition in this schedule. This is a
  necessity observation, not proof that either feature is a trigger, and it is
  not an additive decomposition: the network is recurrent and nonlinear.
  These numbers reproduce the archived P3-T3 counts exactly.

P3-T3 and P3-T3.1 are quoted, not re-derived; the raw P3-T3 payload is
unchanged and its sha256 remains `6fbe3263…b8956`.

---

## 12. Limitations and unresolved mechanisms

1. **Descriptive, single deterministic run per condition.** Two repeats and
   subprocess repeats establish determinism, not a sampling distribution. No
   p-values, effect sizes or significance claims.
2. **"Outside A_c" is an eligibility partition, not causal attribution.** A
   spike outside A_c cannot be directly injected, but no per-spike current
   decomposition proves it was synaptic.
3. **Hop distance is structural.** The graph has no coordinates, axonal
   lengths or conduction delays. The 5-hop boundary is a property of this
   directed graph, not anatomy or space.
4. **Washout is outside the validated window.** The prefix gate protects
   comparability, but the last 750 ms extend beyond the archived 3,300.5 ms.
   Only 500 ms of that is drive-free.
5. **Membrane sampling is every 10 ms.** The 139,255-neuron population is
   summarised, not traced per neuron; individual trajectories are not retained.
   Exact min/max and rail occupancy are counted every step, but distribution
   shape is sampled.
6. **Threshold dominance.** Spikes reset the membrane to −68 mV, so the
   distribution reflects reset and floor dynamics, not a passive subthreshold
   distribution. This is a property of the configured LIF model, not a finding.
7. **No upper clamp exists.** The −50 mV maximum is a near-threshold value;
   any statement about "saturation at −50" would be wrong.
8. **Mechanism is not identified.** Why C3 crosses into ignition while C2 does
   not is not resolved here. Candidate contributors that this experiment does
   not separate: total injected charge, the specific player-feature populations,
   coincidence timing across features, and the recurrent gain set by
   `12.0 × syn_count^0.75` with the configured transmitter signs.
9. **Physiological status is unknown.** Firing near the 500 Hz refractory
   ceiling and 20 % floor occupancy may be an artefact of the assumed LIF and
   synapse parameters. No parameter was changed to avoid ignition, and none
   should be read as biologically calibrated.
10. **No perception, learning, decision or behaviour is measured.** There is no
    action selection in this pipeline.

---

## 13. Acceptance criteria

| # | Criterion | Status |
| --- | --- | --- |
| 1 | Protocol, runner and focused tests exist | Met — 10 focused tests pass |
| 2 | Loop-equivalence gate passes (synthetic + archived C3) | Met — synthetic test and 9/9 archived checks |
| 3 | Seven conditions at full duration, two identical repeats, subprocess repeats for C3 and C3-washout | Met |
| 4 | No invalidation triggered, or every one reported | Met — 0 triggered |
| 5 | Items 1–11 of protocol §4 reported | Met — §3–§9 of this report; per-100 ms tail aggregates computed from the 10 ms bins |
| 6 | P3-T3.1 classification applied unchanged and quoted as provisional | Met |
| 7 | Report states results, stability analysis, limitations and unresolved mechanisms | Met — §9–§12 |
| 8 | P3-T2/P3-T3 artifacts byte-identical; README and protected hashes unchanged | Met — protected hashes match; archived artifacts untouched |

---

## 14. Artifacts

| File | sha256 |
| --- | --- |
| `experiments/phase_3c/results/p3_t12_network_characterization.json` | `c1555968258cc90fb731147543a032bc94f0a102d980c219b55319a4c60f465b` |
| `...sidecar.json` | `78b0eea7d209d264610fd5894144f0de388a0795b1dc1354efea153e63d75156` |
| `experiments/phase_3c/results/p3_t12_analysis_summary.json` | `da0272969fbfd97eab987124d9dcdd78edcf088f58e20ab36ed15ffee3536a4d` |
| `experiments/phase_3c/results/p3_t12_preflight.json` | `3974bd00bf95c4f5d1e5378bafe63dfc3a117caf1170a3c5efa0bbeac2287463` |
| `experiments/phase_3c/results/p3_t12_smoke.json` | `ce0dd7c5187dcdcb6b557082868219859a7d2e9e94f09adf7c01515b4857f92e` |
| `experiments/phase_3c/network_characterization.py` | `5eee47fb268d7fbb46c00d5ac28c52c04f595e7302123970a36b2de5176a2498` |
| `experiments/phase_3c/p3_t12_preflight.py` | `9a9aee690e47967a1cb56de04440d0e8d9964c9c5623914008c28c9d1f6de949` |
| `experiments/phase_3c/p3_t12_analysis.py` | `58c90ad9e8f6841a1167a24c62d99a0c76c39c2794b20b799b999293a03cbc74` |
| `tests/test_network_characterization.py` | `ed2f9584015a07fc63644d9b558a8e8005002c674a941c6d19d513ced41ba70f` |
| `configs/p3_t12_characterization.yaml` | `18018b686e38226b5f2bb126868e7ed67f66ad1d9be7bfa95a6f5ac91b52ea03` |
| `docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md` | `49c09424b15db3b09cfdef5b28afcf0cbcaa6dbc72a9f657de6b31a82201b173` |

Git HEAD at execution: `62a64309cadc0db7353c856607cee5369993bd65`, branch
`main`, working tree dirty (the programme's own untracked/modified work).
Nothing was staged, committed or pushed.

**Action selection:** none. The chain ends at sensory current injection.
