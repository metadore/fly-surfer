# P3-T3.1 — Ignition reporting: activity detection vs population ignition

Status: implemented 2026-11-13 as an additive reporting layer. The raw P3-T3
payload (`experiments/phase_3c/results/p3_t3_ablation.json`) is unmodified;
its SHA-256 is recorded in the derived classification file.

## Why this correction exists

The P3-T3 runner writes a field `ignition.ignited` defined as:

> `outside_reference.first_spike_ms is not None`

That is an **activity-detection** flag: it asks whether any spike occurred
outside the fixed reference set R (the 138 mapped sensory neurons). It does not
distinguish a handful of late spikes from a population-scale avalanche. In the
P3-T3 campaign, `no-train_lane` produced 2,802 total spikes, 4 outside-R spikes
on 2 neurons, and a first outside-R spike at 1,467 ms — yet the legacy flag
reads `true`, exactly as it does for the baseline's 15,650,921 outside-R
spikes. The flag is not wrong for what it measures; it is too coarse to be
reported as "ignition" without qualification.

No preregistered absolute ignition threshold exists in the Phase 3 protocol or
roadmap. The P3-T2 protocol defines partitions, rates, bins and latency, and
explicitly limits analysis to descriptive quantities; "ignition" in the P3-T2
report is an interpretive description, not a thresholded metric. P3-T3.1
therefore does not invent a spike-count or rate cutoff.

## Definitions

| Term | Meaning | Basis |
|---|---|---|
| Outside-R activity detected | At least one spike outside R. | Definitional |
| Sparse outside-R activity | Outside-R spikes exist but do not meet the population-scale criterion. | Provisional |
| Population-scale recurrent ignition | Outside-R activity meets the provisional criterion below. | Provisional |

**Provisional population-scale criterion.** Both of the following must hold
inside the same condition:

1. outside-R active neurons **exceed the size of the entire fixed reference set
   R** (`outside_reference.active_neurons > n_reference_neurons`);
2. the outside-R firing rate is **at least the reference partition's firing
   rate** (`outside_reference.firing_rate_hz >= reference.firing_rate_hz`).

The criterion uses only measured quantities and the fixed structural size of R.
It contains no new absolute constants, but it is a post-hoc relational rule,
so the resulting label is explicitly `provisional`. All raw measurements
(spike counts, active neurons, rates, active fractions, bin occupancy, span,
first/last spike, spikes per active neuron) are reported alongside the label so
that any consumer can apply a different criterion.

## Backward compatibility

* The source payload and every historical field are preserved byte-for-byte.
* `ignition.ignited` keeps its original meaning (activity detection) and is
  never rewritten or relabelled.
* The classification is written to a new artifact:
  `experiments/phase_3c/results/p3_t3_1_ignition_classification.json`.
* New fields are additive: `activity_detected_outside_reference`,
  `activity_regime`, `activity_regime_status`, `population_scale_basis`,
  `population_scale_criterion`, `legacy_activity_detection`, `measurements`.

## Usage

```bash
python -m experiments.phase_3c.ignition_reporting
```

Options: `--source`, `--output`, `--overwrite`. The writer refuses to replace an
existing output unless `--overwrite` is passed.

Library use:

```python
from experiments.phase_3c import ignition_reporting as ir
item = ir.classify_condition(condition_payload)
report = ir.build_classification_report(source_path)
```

## Interpretation rules

* `activity_regime != "none"` means "at least one outside-R spike", not
  "the network ignited".
* `population_scale` is provisional. It is a descriptive operational label,
  not a preregistered criterion and not a mechanistic claim.
* `sparse` does not mean the activity is negligible or functionally
  irrelevant; it means the condition failed the provisional population-scale
  test, and the measurements should be read directly.
* None of these labels demonstrate sensory routing, perception, decision
  making, learning or biological equivalence.

## Tests

`tests/test_ignition_reporting.py` covers: zero outside-R spikes; four spikes
on two neurons (the P3-T3 `no-train_lane` pattern); the full P3-T3 baseline;
two intermediate cases that fail exactly one criterion; input immutability;
the archived-payload classification and source-hash preservation; and
no-overwrite behaviour.
