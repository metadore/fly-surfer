# P3-T3.1 — Ignition reporting correction

Date: 2026-11-13
Git HEAD: `62a64309cadc0db7353c856607cee5369993bd65` (branch `main`)
Status: reporting correction delivered. No simulation was run and no Phase 3
result was altered.

## 1. Why the correction exists

The P3-T3 campaign records, for every condition, an `ignition` block produced by
`ignition_summary()` in `experiments/phase_3c/feature_ablation.py` (lines
386-401). That function defines the flag as:

```python
"ignited": outside_reference["first_spike_ms"] is not None
```

Any single spike anywhere outside the fixed 138-neuron reference set R sets
`ignited = True`. Under that definition `no-train_lane` is reported as
"ignited" even though the whole 3,300.5 ms run produced 2,802 spikes, of which
only 4 fell outside R, on 2 neurons, with the first at 1,467.0 ms and an
outside-R firing rate of 9 × 10⁻⁶ Hz. That is not comparable to the
15.65 M-spike, 35,907-active-neuron, 34.09 Hz regime seen in the baseline and in
the other 12 ablations, and the label makes the two look identical.

The defect is in the reporting layer only. It does not affect the simulation,
the recorded spike data, or any archived result.

## 2. Source and consumer audit

* Producer: `ignition_summary()` in `experiments/phase_3c/feature_ablation.py`,
  consumed by `run_ablation_experiment()` when it assembles each condition's
  `ignition` block.
* The block is stored verbatim in `experiments/phase_3c/results/p3_t3_ablation.json`
  and is read by `tests/test_feature_ablation.py` (smoke test asserts only that
  the block is present, `baseline["ignition"] is not None`) and described in
  prose in the Phase 3 reports.
* No other module computes, re-uses or depends on `ignited`. There is no
  simulator, scheduler, detector or audit code path that branches on it.
* No preregistered population-ignition threshold exists. Neither
  `docs/PHASE_3C_CAUSAL_CONTROL_PROTOCOL.md` nor `docs/PHASE_3_ROADMAP.md`
  defines one, and the P3-T2 protocol's analysis policy is descriptive only.
  Any numeric threshold introduced here would therefore be invented.

Conclusion: the legacy field cannot be redefined without silently changing
historical results, and there is no documentary basis for an absolute
threshold. The correction must be additive.

## 3. What was added

New module `experiments/phase_3c/ignition_reporting.py`
(`p3-t3.1-ignition-reporting-v1`) derives a separate classification from the
archived payload. It reads the raw file, hashes it, and writes a new artifact.
It never writes to the source.

Three regimes:

| Regime | Definition | Epistemic status |
| --- | --- | --- |
| `none` | zero spikes outside R | definitional (no free parameter) |
| `sparse` | outside-R spikes exist but the population criterion fails | provisional |
| `population_scale` | outside-R active neurons > 138 (|R|) **and** outside-R firing rate ≥ reference-partition firing rate | provisional |

`population_scale` is flagged provisional because the comparison is relational,
not absolute: it asks whether recruitment exceeds the size of R and whether the
off-target partition fires at least as fast as the driven one. Both quantities
come from the same run, so no external constant is chosen. The criterion is
reported alongside every classification and must be quoted whenever
`population_scale` is used.

Backward compatibility:

* `ignition.ignited` in the archived payload keeps its original meaning. The new
  artifact records it under `legacy_activity_detection` together with the note
  that it detects activity, not population ignition.
* The archived payload is not modified. Its sha256 was captured before and
  after generation
  (`6fbe3263de49d5a2db830f4118814a5e45889dd0698f05e070f46fe6566b8956`,
  259,091 bytes, unchanged).

## 4. Classification of the 15 P3-T3 conditions

Source verdict: VALID, 0 invalidations. Counts: `none` 1, `sparse` 1,
`population_scale` 13.

| Condition | Removed feature | Outside-R spikes | Outside-R active neurons | Outside-R rate (Hz) | Reference rate (Hz) | Total spikes | Legacy `ignited` | Regime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| full-input | — | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |
| no-player_lane | player_lane | 0 | 0 | 0 | 6.2749 | 2,858 | false | none |
| no-train_lane | train_lane | 4 | 2 | 0.000009 | 6.1431 | 2,802 | true | sparse |
| no-player_speed | player_speed | 15,650,909 | 35,916 | 34.0863 | 7.3199 | 15,654,243 | true | population_scale |
| no-jumping | jumping | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |
| no-rolling | rolling | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |
| no-obstacle_present | obstacle_present | 15,655,978 | 35,906 | 34.0973 | 7.4802 | 15,659,385 | true | population_scale |
| no-obstacle_lane | obstacle_lane | 15,652,500 | 35,882 | 34.0897 | 7.7173 | 15,656,015 | true | population_scale |
| no-obstacle_distance | obstacle_distance | 15,656,848 | 35,912 | 34.0992 | 7.8095 | 15,660,405 | true | population_scale |
| no-obstacle_type | obstacle_type | 15,655,728 | 35,937 | 34.0968 | 7.5790 | 15,659,180 | true | population_scale |
| no-train_present | train_present | 15,653,271 | 35,918 | 34.0914 | 6.2595 | 15,656,122 | true | population_scale |
| no-train_distance | train_distance | 15,657,365 | 35,922 | 34.1003 | 7.2650 | 15,660,674 | true | population_scale |
| no-coin_present | coin_present | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |
| no-coin_lane | coin_lane | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |
| no-coin_distance | coin_distance | 15,650,921 | 35,907 | 34.0863 | 8.1455 | 15,654,631 | true | population_scale |

Rates use the actual simulated duration (3.3 s) and divide by the respective
partition sizes (reference: 138 neurons; outside reference: graph size minus
138). The four zero-drive ablations are bit-identical to the baseline because
their features received no injected current in P3-T3.

Reading of the single corrected case: `no-train_lane` remains activity-positive
in the legacy sense — a real, if minute, off-target discharge exists — but it is
placed in `sparse`, not in the population-scale class. This is the substantive
change P3-T3.1 was opened for.

## 5. Interpretation rules

* `ignited = True` must not be quoted as "the network ignited". It means "at
  least one spike outside R".
* `population_scale` is provisional and is relative to this run's reference
  partition. It does not establish recurrent ignition, biological ignition, or
  any mechanism; it states that off-target recruitment in this model exceeded
  |R| and matched the driven partition in rate.
* `sparse` does not mean "almost ignited". `no-train_lane`'s 4 spikes at
  9 × 10⁻⁶ Hz are a different regime, not a small version of the baseline.
* `none` is definitional: zero spikes outside R. It is a measurement, not a
  claim that the network is silent inside R.

## 6. Regression tests

`tests/test_ignition_reporting.py` — 8 tests, all passing (0.06 s):

1. Zero outside-R spikes → `none` / definitional.
2. Four outside-R spikes on two neurons → `sparse` / provisional, legacy flag
   still true (the P3-T3 `no-train_lane` case).
3. Archived baseline condition → `population_scale` with both criterion
   components true.
4. Intermediate activity (100,000 spikes, 500 active, 3.0 Hz against an 8.145 Hz
   reference) → `sparse`, showing the rate component can veto the class.
5. High-rate but small recruitment (50,000 spikes, 100 active, 40 Hz) →
   `sparse`, showing the recruitment component can veto the class.
6. Source payload immutability (bytes and sha256 identical before/after).
7. Full archived payload → counts `{none: 1, sparse: 1, population_scale: 13}`,
   `no-train_lane` sparse with legacy true, `no-player_lane` none, every other
   condition population_scale, source verdict VALID and `unmodified` true.
8. Overwrite refusal on an existing output path.

The pre-existing `tests/test_feature_ablation.py` is unaffected: it asserts only
that the `ignition` block exists.

## 7. Artifacts

Created:

* `experiments/phase_3c/ignition_reporting.py` (new module; sha256
  `b48bf26a…4950a`)
* `tests/test_ignition_reporting.py` (sha256 `22e4ca25…e3daf`)
* `experiments/phase_3c/results/p3_t3_1_ignition_classification.json` (derived
  report; sha256 `6c84a884…0923b`, 29,191 bytes)
* `docs/PHASE_3C_IGNITION_REPORTING.md` (sha256 `58568a6e…c901`)
* this report

Preserved unmodified:

* `experiments/phase_3c/results/p3_t3_ablation.json` (sha256 `6fbe3263…b8956`,
  259,091 bytes) and its sidecar.
* `experiments/phase_3c/feature_ablation.py` — the producer was left unchanged so
  historical results and their meaning are preserved; the correction is
  additive in a separate module.
* All P3-T2 artifacts.

## 8. Limitations

* The `population_scale` criterion is provisional. It has no independent
  calibration and no external threshold. It is a descriptive relational test
  that separates the observed regimes at the resolution of |R| and rate
  parity; it has not been validated against any second dataset.
* The classification covers one campaign (P3-T3, seed set as archived). It has
  not been applied to P3-T2, C0–C3, or future runs.
* `sparse` is a residual class: any nonzero off-target activity that fails the
  criterion lands there, including regimes that differ from each other by
  orders of magnitude. The measurements are reported for exactly this reason.
* No full P3-T3 rerun was performed, as instructed.
