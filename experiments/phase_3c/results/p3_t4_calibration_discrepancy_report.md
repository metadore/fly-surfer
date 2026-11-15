# P3-T4 — Four-versus-twelve neuron calibration discrepancy

**Status:** COMPLETE WITH LIMITATIONS
**Generated:** 2026-11-14 (machine-readable evidence in
`experiments/phase_3c/results/p3_t4_calibration_discrepancy.json`)
**Scope:** audit and decision only. No simulation was re-run for this report;
every measured number below is taken from the archived Phase 3A.5 results and
re-analysed with the original Phase 3A.5 rule. Nothing was staged, committed or
pushed. The connectome, the calibration results and every Phase 3B/3C artifact
were left byte-identical.

---

## 1. Question

Phase 3A.5 selected a **four-neuron** `obstacle_distance` population, but
Phase 3B, Phase 3C, P3-T2, P3-T3 and P3-T12 use **twelve**. Only the 200 pA
amplitude and `sigma_fraction` 0.20 were carried forward. This report
establishes what actually happened, quantifies the difference with the archived
data, and recommends whether to change the configuration.

**Answer in one paragraph.** The population size never changed from 4 to 12.
It was 12 in the Phase 3A configuration before calibration ran. Phase 3A.5
took that config as its base, selected 4 as the only strictly ordered group,
wrote the selection to a results file, and never wrote it back to the config.
No runner reads the selection file, so every downstream phase silently
continued with the Phase 3A design point. The mismatch is documented in three
places as an open discrepancy. The archived data already contain a matched
4-versus-12 measurement at the calibrated amplitude, tuning, duration and
distances: 4 meets the original pre-registered ordering rule in all three
mapping seeds; 12 does not meet it in its one measured seed. Neither point is a
credible graded distance code. A new calibration is **not** needed to explain
or document the discrepancy, but **would** be needed before claiming distance
decoding or switching the shipped operating point. The recommendation is to
retain 12 for the frozen Phase 3 evidence chain, stop calling it calibrated,
and treat distance decoding as an open question with a pre-registered
comparison.

---

## 2. What is actually shipped

`configs/sensory_config.yaml` (sha256 `26d782a3…f4e96db`, mtime
2026-11-04T12:31:42Z) defines 14 features and **138** mapped neurons. The
pinned causal-control config reproduces the counts exactly
(`n_reference_neurons: 138`, 36 player, 102 non-player), and the focused test
`tests/test_p3_t4_calibration.py` enforces that equality.

Gaussian distance features all use 12 neurons:

| Feature | Neurons | Mapping pool |
|---|---:|---|
| `obstacle_distance` | 12 | `visual_any` |
| `player_speed` | 12 | `visual_any` |
| `train_distance` | 12 | `visual_any` |
| `coin_distance` | 12 | `visual_any` |

The Phase 3A report already recorded the relevant limitation: *“sensitivity to
tuning width, population size and current amplitude is not yet
characterised.”* Phase 3A.5 exists to characterise exactly that.

---

## 3. Provenance timeline

| Time (UTC, 2026-11-04) | Artifact | Fact |
|---|---|---|
| 12:31:42 | `configs/sensory_config.yaml` (mtime) | 12 neurons for every Gaussian distance feature, including `obstacle_distance` |
| 12:56:31 | `experiments/phase_3/PHASE_3_REPORT.md` | Phase 3A reports the 12-neuron populations and states population size is not yet characterised |
| 14:10:05 | `configs/sensory_calibration.yaml` (mtime) | base config is the 12-neuron file; fallback population size is also 12; sweep sizes are 4/8/12/16/24 |
| 14:27:29 | `experiments/phase_3_5/PHASE_3_5_REPORT.md` | selection: 4 neurons, 200 pA, sigma 0.20, seed 20261104; described as the recommended Phase 3B input setting |

**No runnable code reads `experiments/phase_3_5/results/selection.json`.** The
calibration runner writes it; only documentation and tests mention it. There is
therefore no mechanism by which the four-neuron selection could have reached
the simulator, and no point at which the twelve-neuron value was re-chosen.

The mismatch is already documented, not hidden:

- `docs/PHASE_3_SENSORY_ENCODING.md`, “Operating-point mismatch (4 versus 12
  neurons)”: an open discrepancy, not a calibrated equivalence;
- `docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md` §6: the 3C runs are “not at the
  calibrated four-neuron operating point”;
- `docs/PHASE_3_ROADMAP.md` §4.2 and the 3C protocol: the shipped population is
  the 12 neurons, not the four calibrated in 3A.5.

---

## 4. Cause classification

The programme asks whether the change was deliberate, experimental, accidental
or undocumented. None of those labels fits exactly, and forcing one would be
inaccurate:

- **Not a change.** 12 predates calibration. There is no 4→12 edit to explain.
- **Not experimental.** No experiment compared 4 and 12 with the intent of
  choosing between them for the full network. The 3A.5 sweep is a single-feature
  calibration, not a network comparison.
- **Not accidental in the sense of a typo.** The value is consistent across the
  config, the mapping plan and every pinned count. It was simply never updated.
- **Documented, but not resolved.** Three documents record the mismatch, and
  the roadmap calls it an open operating-point discrepancy.

**Classification:** an **unpropagated calibration recommendation** — a
report-only selection that was never applied, combined with an explicit,
documented decision to continue with the Phase 3A design point. It is a
provenance gap in the pipeline (calibration results are not machine-consumed),
not an undocumented scientific change.

---

## 5. Every shipped use of the twelve-neuron point

All consumers were verified to exist and hashed in the JSON record.

| Consumer | How it gets 12 | Consequence |
|---|---|---|
| `experiments/phase_3/run_all.py` | loads `sensory_config.yaml` | Phase 3A single-feature and sequence runs |
| `experiments/phase_3b/real_sequence_replay.py` | loads `sensory_config.yaml` | Phase 3B.2C 3,300.5 ms replay |
| `experiments/phase_3c/integration_check.py` | loads `sensory_config.yaml` | 3B/3C integration check |
| `experiments/phase_3c/causal_control.py` | loads `sensory_config.yaml`; counts pinned in `causal_control_config.yaml` | P3-T2 C0–C3, 138 reference neurons |
| `experiments/phase_3c/feature_ablation.py` | inherits causal-control conditions | P3-T3 15 conditions; removing a 12-neuron feature leaves 126 active neurons |
| `experiments/phase_3c/network_characterization.py` | inherits causal-control conditions | P3-T12 seven conditions; C3 15,654,631 spikes |

There is **no full-network measurement at four neurons** anywhere in the
archive. The four-neuron evidence is confined to 300 ms single-feature
simulations in Phase 3A.5.

---

## 6. Matched comparison from archived data

Both rows come from `stage_population.json`, same amplitude 200 pA, same
`sigma_fraction` 0.20, same mapping seed 20261104, same 300 ms duration, zero
background current and zero noise, distances 0.15 / 0.55 / 0.90.

| Quantity | 4 neurons | 12 neurons |
|---|---|---|
| Spike counts (near → far) | **2 / 6 / 7** | **24 / 23 / 23** |
| Strictly monotone | yes (increasing) | no (23 = 23 tie) |
| Active neurons | 1 / 1 / 1 | 4 / 3 / 3 |
| Spikes per neuron | 0.50 / 1.50 / 1.75 | 2.00 / 1.92 / 1.92 |
| Dynamic range | 5 spikes | 1 spike |
| d′ proxy (Poisson) | 2.357 | 0.206 |
| Total feature current, peak | 289.5 / 300.4 / 281.4 pA | 924.1 / 1,094.6 / 847.5 pA |
| Max per-neuron current | 151.0 / 168.7 / 176.5 pA | 197.5 / 199.9 / 199.8 pA |
| First spike | 101 / 44 / 38 ms | 29 / 28 / 28 ms |
| Network spikes (= feature spikes) | 2 / 6 / 7 | 24 / 23 / 23 |
| Network active neurons | 1 / 1 / 1 | 4 / 3 / 3 |

Three observations matter more than the ordering:

1. **The four-neuron ordering is one neuron's spike count.** Exactly one of the
   four neurons is active at each level; the sequence 2→6→7 is that neuron's
   threshold-crossing count. The adjacent margin between 0.55 and 0.90 is a
   single spike, and one additional spike at 0.55 (`2/7/7`) destroys the
   ordering. All three mapping seeds happen to reproduce `2/6/7`.
2. **The twelve-neuron point is not flat by lack of activity.** It produces
   several times the spikes (70 versus 15 across the three levels), recruits
   3–4 neurons, and still fails monotonicity because the two far levels tie at
   23.
3. **Neither point propagates.** In every 3A.5 condition the network spike
   count equals the feature spike count and network active neurons equal
   feature active neurons: at 300 ms with a single active feature, no activity
   leaves the stimulated population.

Seed coverage is asymmetric. The seed stage re-ran only the selected size: 4
neurons is measured at 20261104/05/06 and is ordered in 3/3; 12 neurons has one
measured seed (20261104) and is ordered 0/1. The original seed gate requires
ordering in at least two of three seeds, so 12 fails it by having no ordered
seed; it was not tested at the other two seeds.

---

## 7. Why “4 instead of 12” is not a clean single-factor change

The mapping allocates populations greedily in configuration order from a
seeded permutation, with duplicates forbidden. `obstacle_distance` is the tenth
population; four visual populations are allocated after it. Reconstructing both
mappings from the same graph and seed:

- The four indices (`64890, 87389, 107895, 108078`) are a subset of the twelve
  (`7411, 52604, 64890, 87389, 87805, 88721, 91895, 91920, 104235, 107895,
  108078, 125025`). They are the allocation-order prefix of the twelve; sorting
  hides that. The four-neuron set is therefore a strict subset, not a different
  selection principle.
- Shrinking the population releases eight `visual_any` neurons to the features
  allocated after it. **Five features change identity**, not one:
  `obstacle_distance`, `train_present` (0/6 overlap), `train_distance` (4/12),
  `coin_present` (0/6), `coin_distance` (4/12).
- The prefix is not transmitter-neutral. Four neurons: 3 unlabeled, 1 GABA, 0
  ACh. Twelve neurons: 7 unlabeled, 3 ACh, 1 GABA, 1 SER. The four-neuron
  subset excludes every cholinergic neuron in the twelve-neuron set. This is a
  consequence of an arbitrary permutation prefix, not a tuned selection, but it
  means the two populations differ in composition as well as size.

Consequently, a full-network 4-vs-12 comparison under the current config would
confound the intended factor with remapping of four other feature populations.
A controlled comparison requires an explicit index override or a mapping mode
that pins the other thirteen populations. The current configuration has no such
override. That is a design constraint, not a defect to fix silently.

---

## 8. Re-applying the original selection rule

The original Phase 3A.5 rule is used unchanged (no new criterion is introduced
to judge the archived data):

- eligible: at least one spike and not fully saturated at every level;
- ordered: strictly monotone spike counts across 0.15/0.55/0.90;
- seed gate: ordered in at least two of three mapping seeds.

| Size | Eligible | Ordered | Ordered seeds | Meets original rule |
|---|---|---|---|---|
| 4 | yes | yes | 3/3 | **yes** |
| 12 | yes | no | 0/1 measured | **no** |

This is the core finding: **12 does not satisfy the criterion that selected
4**, and it was never evaluated at two of the three seeds. The calibration
recommendation was therefore both unapplied and, at the measured point,
contrary to the shipped setting.

---

## 9. Is a new calibration necessary?

| Purpose | New calibration needed? | Reason |
|---|---|---|
| Explain or document the discrepancy | **No** | The archived sweep already contains a matched 4-vs-12 comparison at the calibrated amplitude, tuning, duration and distances, plus three seeds at 4. Re-running would reproduce the same numbers. |
| Decide the shipped operating point for the existing evidence chain | **No** | The decision is about continuity and validity of completed artifacts, not about missing measurements. |
| Claim graded distance coding | **Yes** | Neither size is a credible graded code: 4 is a single-neuron, one-spike-margin count; 12 is non-monotone; only three levels, one duration, one active feature, no full-network measurement at 4. |
| Switch the shipped default to 4 | **Yes** | A full-network comparison is required, and it needs a mapping override to avoid the remap confound in §7. |

---

## 10. Pre-registered comparison design (if distance coding is pursued)

This design is recorded so that any future comparison is fixed before data are
seen. It is **not executed** here, and it does not change any current config.

**Stage L — single-feature calibration (cheap, isolates the encoder).**

- Sizes 4, 8, 12, 16; amplitude 200 pA; `sigma_fraction` 0.20; zero background
  and noise; mapping seeds 20261104, 20261105, 20261106.
- Seven distances 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90; durations 300 ms and
  600 ms; one active feature only.
- Primary criterion: the original 3A.5 rule, unchanged.
- Additional robustness requirements, explicitly new and not from the original
  roadmap: adjacent-level margin at least 2 spikes, at least 2 active neurons at
  at least 2 levels, and replication in at least 2 of 3 seeds. Any size that
  fails these is not eligible for adoption even if it is strictly monotone.
- Report per-level spike counts, active neurons, latency and currents; no
  significance tests on single deterministic runs.

**Stage N — full-network effect (only if Stage L yields an adoptable size).**

- C3-style 3,300.5 ms replay with the archived frames, comparing 12 (control)
  and the candidate size.
- **Mapping override required:** the other thirteen populations must be pinned
  to their twelve-neuron indices so the only change is the
  `obstacle_distance` population. Without the override the comparison is
  confounded by §7.
- Report reference-set size, spikes inside/outside the new A_c, and the same
  partitions as P3-T2/P3-T3; the archived C3 at 12 remains untouched.
- Stage N runs only after Stage L passes; no source/config change before that.

**Preservation.** Original calibration config, results and reports stay
byte-identical; new files use new names; seeds are fixed and recorded; the
protocol is hashed before execution.

---

## 11. Recommendation

1. **Retain 12 as the shipped operating point** for the frozen Phase 3B/3C,
   P3-T2, P3-T3 and P3-T12 evidence chain. Switching to 4 would change the
   reference set from 138 to 130, remap four other features, and invalidate
   every published count without replacing it with a better-validated code.
2. **Stop describing 12 as calibrated.** It is the Phase 3A design point. The
   calibrated point is 4, and it was never shipped. This wording should be used
   in the Phase 3 completion audit and any future report.
3. **Do not adopt 4 now.** It is a single-neuron, one-spike-margin operating
   point measured only in 300 ms single-feature runs; it has no full-network
   evidence.
4. **Do not claim distance decoding at either size.** The Phase 3 sensory
   pipeline may be described as injecting a configured distance-dependent
   current; it may not be described as a validated distance code.
5. **If distance decoding is pursued**, execute Stage L and, only on success,
   Stage N exactly as pre-registered in §10. That work is outside this
   programme and requires a decision to change the shipped default.

---

## 12. Limitations

- All spike counts are simulated model output at 300 ms with zero background
  and noise; they are not biological measurements and not firing rates of real
  neurons.
- The comparison uses three distance levels and one duration, because those are
  the archived levels. It cannot establish the shape of a tuning curve.
- The d′ proxy is a Poisson signal-to-noise ratio on very small counts; it is
  descriptive, not an inferential statistic.
- The twelve-neuron seed gate was not measured at two of three seeds; the
  conclusion that 12 fails is based on its one measured seed and would not
  improve by adding seeds unless the far-level tie at 23 breaks in both.
- Mapping identity is reconstructed deterministically from the config and seed,
  not read from a stored index list; the reconstruction is checked against the
  archived report counts (138 total, 12 for `obstacle_distance`) and by test.
- No full-network four-neuron run exists, so nothing here says how a 4-neuron
  population would behave over 3,300.5 ms or under recurrent activity.

---

## 13. Artifacts

| File | sha256 |
|---|---|
| `experiments/phase_3c/p3_t4_calibration_discrepancy.py` | `59fa226058b504972767805de2fefe7cb2f2e910118b21ff471674dd3f302f04` |
| `experiments/phase_3c/results/p3_t4_calibration_discrepancy.json` | `265a3a6c9782b954802f2bb8cae679fbc669e86b72e675d94b1d27714e573585` |
| `experiments/phase_3c/results/p3_t4_calibration_discrepancy.sidecar.json` | `f87749f5cafcdb422d478ce2fc4a23014339948d2c727ff3676ba4851645d362` |
| `tests/test_p3_t4_calibration.py` | `970ca34adc141015b8373f35d877967ae047e95900b584ddf79ee019b145d941` |
| `configs/sensory_config.yaml` (unchanged) | `26d782a3b5910c05d433fa6678557f7c806dc9947ee8ad279e246fa34f4e96db` |
| `configs/sensory_calibration.yaml` (unchanged) | `e2f446a858e6a906e27d682a1958498c129c6367d5f42f6d103a7fd36a28e84d` |
| `experiments/phase_3_5/results/selection.json` (unchanged) | `e30559a531e871b9fbfc5f93f8d5c09445ca4be02ec491a8988fb72d534c5eae` |
| `experiments/phase_3_5/results/stage_population.json` (unchanged) | `c9695814f287675a5cb707249e60295e8a5049fa14adc142c7858c6e4c81abd7` |
| `experiments/phase_3_5/results/stage_seeds.json` (unchanged) | `3459b0f5202b17bd397859e3e924bc7c638b9b811a5962ae2c68aa42c2542b2a` |

Git HEAD at audit: `62a64309cadc0db7353c856607cee5369993bd65`, branch `main`,
working tree dirty with the programme's own new files. Nothing was staged,
committed or pushed.
