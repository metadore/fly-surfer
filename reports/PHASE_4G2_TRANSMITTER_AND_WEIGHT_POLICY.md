# Phase 4G.2 — BANC Transmitter-Sign and Edge-Weight Policy

**Project:** FLY-SURFER
**Phase:** 4G.2 (BANC neural propagation)
**Date:** 2026-11-08
**Status:** Complete — policy declared, measured and reproducible
**Machine-readable result:** `reports/PHASE_4G2_TRANSMITTER_AND_WEIGHT_POLICY.json`
**Configuration:** `configs/banc_synapse_policy.yaml`
**Policy module:** `brain/banc_synapse_policy.py`
**Audit script:** `experiments/phase_4g/audit_synapse_policy.py`

---

## 1. Purpose and scientific status

Phase 4G.2 fixes, before any simulation is run, how BANC node annotations become
an explicit synaptic sign prior and how structural synapse counts become synaptic
current weights.

| Block | Status |
|---|---|
| Transmitter labels | published BANC v888 annotations |
| Sign classes | modelling priors derived from those annotations |
| Excitatory / inhibitory | assumed presynaptic release classes, not measured postsynaptic effects |
| Edge weights | monotone transformation of integer synapse counts, not conductances |
| Excluded edges | structural connections the declared policy cannot sign |

The statements below hold throughout Phase 4G:

- Structural connectivity is not physiological connectivity.
- Synapse count is not synaptic conductance.
- A predicted neurotransmitter is not a verified neurotransmitter.
- Neurotransmitter identity alone does not establish the physiological effect at
  a given postsynaptic target.
- Every reported coverage fraction refers to the BANC v888 structural graph, not
  to a measured functional circuit.

The policy was declared in `configs/banc_synapse_policy.yaml` before any
simulation or decoder output was generated. It was not tuned against decoder
labels.

---

## 2. Inputs

| Input | Path | SHA-256 |
|---|---|---|
| Node annotations | `datasets/processed/banc_v888/banc_nodes.csv.gz` | `144a2eb0…953e5f` |
| Threshold 1 graph | `datasets/processed/banc_v888/banc_graph_t1.npz` | `fee8e5e7…ecc01e` |
| Threshold 5 graph | `datasets/processed/banc_v888/banc_graph_t5.npz` | `6d47f259…3e2192` |
| Threshold 10 graph | `datasets/processed/banc_v888/banc_graph_t10.npz` | `00b3f447…1dc7a0` |
| Policy configuration | `configs/banc_synapse_policy.yaml` | `88f64492…dc399e` |

All four inputs were read-only. No dataset, manifest or Phase 4D artifact was
modified by this subphase.

---

## 3. Annotation fields

The BANC v888 node table contains 172,433 endpoint neurons and three transmitter
fields:

| Field | Meaning | Coverage |
|---|---|---|
| `neurotransmitter_verified` | transmitter label reported as verified by the BANC annotation source | 65,292 neurons (37.9 %), 35 distinct label strings |
| `neurotransmitter_predicted` | predicted transmitter label | 153,927 neurons (89.3 %), 8 distinct label strings |
| `neurotransmitter_score` | confidence score attached to the annotation | 171,690 non-null; median 0.76 overall, median 0.90 on verified labels |

Overlap: 64,459 neurons carry both a verified and a predicted label, and 17,673
carry neither.

Labels may name several transmitters at once, for example
`acetylcholine,nitric_oxide,dopamine`, `gaba,nitric_oxide` or
`histamine,acetylcholine`. The policy therefore classifies the label set, not a
single string.

**The predicted column is never used to supply a sign in the primary policy.**
Its role is a separate sensitivity condition (§5).

---

## 4. Sign classification

### 4.1 Classes

Nine mutually exclusive codes (stable because they are persisted in results):

| Code | Class | Definition |
|---:|---|---|
| 0 | unannotated | no verified label |
| 1 | verified excitatory prior | verified label contains acetylcholine and/or glutamate, no GABA/glycine |
| 2 | verified inhibitory prior | verified label contains GABA and/or glycine, no acetylcholine/glutamate |
| 3 | verified conflict | verified label contains both an excitatory and an inhibitory transmitter |
| 4 | verified modulator-only | verified label names only modulators (dopamine, serotonin, octopamine, tyramine, histamine, nitric oxide) |
| 5 | predicted excitatory | no verified label; predicted label gives an excitatory prior |
| 6 | predicted inhibitory | no verified label; predicted label gives an inhibitory prior |
| 7 | predicted conflict | no verified label; predicted label names both classes |
| 8 | predicted modulator-only | no verified label; predicted label names only modulators |

Only classes 1 and 2 carry a sign in the primary policy. Classes 0, 3, 4 are
unknown. Classes 5–8 are unused in the primary policy and exist only for the
predicted-fallback sensitivity run.

### 4.2 Primary neuron-level result

| Class | Neurons | Share of 172,433 |
|---|---:|---:|
| Verified excitatory prior | 53,987 | 31.31 % |
| Verified inhibitory prior | 9,733 | 5.64 % |
| Verified conflict | 5 | 0.003 % |
| Verified modulator-only | 1,567 | 0.91 % |
| Unannotated | 107,141 | 62.13 % |
| **Signed in primary policy** | **63,720** | **36.95 %** |

The dominant limitation is explicit: 62 % of BANC endpoint neurons have no
verified transmitter, so they have no defensible sign under this policy.

### 4.3 Audit correction

The first audit pass treated missing annotations as a literal label and
classified 108,708 neurons as "verified modulator-only". Missing values are now
handled explicitly (`pd.NA`, `NaN`, `"unknown"` → unannotated), which reduced
the modulator-only class to 1,567 neurons and moved 107,141 neurons to
unannotated. All numbers in this report and in the JSON are post-correction. The
error was caught before any simulation used the policy.

---

## 5. Unknown-sign edges: strategies A, B, C

| Strategy | Description | Decision |
|---|---|---|
| **A. Exclude** | Edges from neurons in classes 0, 3, 4 are omitted from the primary simulation and counted explicitly | **Primary** |
| **B. Predicted-only sensitivity** | A repeated condition allows predicted labels to sign neurons that lack a verified label | **Sensitivity condition** |
| **C. Neutral / zero** | Retain unknown edges with zero weight | Documented; numerically identical to A |

Strategy C is retained in the documentation only to state the equivalence:
excluding an edge and retaining it with zero current produce identical spike
trains and currents. Running it as a separate condition would duplicate A.

No unknown edge is ever assigned a positive or negative sign. The primary result
is therefore conditional on the verified-sign subgraph and does not describe the
whole BANC connectome.

### 5.1 Predicted-fallback sensitivity coverage

| Threshold | Signed edges | Signed share | Signed synapses | Synapse share |
|---|---:|---:|---:|---:|
| t1 | 10,275,154 | 88.61 % | 30,945,843 | 90.19 % |
| t5 | 1,391,473 | 90.61 % | 16,986,382 | 91.56 % |
| t10 | 522,129 | 91.49 % | 11,438,091 | 92.26 % |

At threshold 5, predicted labels sign an additional 822,464 edges that the
primary policy excludes (515,599 predicted-excitatory, 192,774
predicted-inhibitory, 114,091 predicted-modulator-only). Any difference between
the primary and fallback conditions measures dependence on unverified annotation,
not a biological effect.

---

## 6. Edge-weight policy

### 6.1 Primary transformation

```
weight_pa = min(scale_pa * count ** exponent, cap_pa)
           = min(5.0 * count ** 0.75, 300.0)
```

- `count` is the integer edge-level synapse count from the Phase 4D graph.
- `norm` (`count / post_count`) is never used: it is a target-normalized
  fraction, not synaptic strength.
- The result is a synaptic current weight in pA. It is not a conductance.

**Why a power transform.** Structural synapse counts are heavy-tailed: at
threshold 5 the median edge has 8 synapses and the 99th percentile has 73, while
the largest signed edge has over 800. A linear transform makes the largest hubs
dominate every postsynaptic sum; a logarithmic transform compresses so far that
edge-to-edge differences become minor. The `count ** 0.75` transform keeps the
ordering, retains measurable differences across three orders of magnitude, and
matches the transform already used by the FAFB pathway, which keeps the two
simulation pathways comparable.

**Why scale 5.0 pA.** The assumed LIF neuron has a 150 pA rheobase. Under the
primary policy a count-20 edge contributes 47 pA, about one third of rheobase, so
firing requires temporal summation of several inputs. The 300 pA cap equals two
rheobase values and bounds hub edges.

**Calibration status.** The scale is a declared model choice, fixed before any
motor-decoder output was inspected. The configuration records a calibration grid
(0.5, 1, 2, 5, 20, 50 pA) and a selection rule: the scale may only be changed on
the basis of baseline quiescence and non-saturating recruitment, never on the
basis of a decoder label.

### 6.2 Transformation comparison (threshold 5, unit scale)

| Transform | Median | p99 | Max | Mean |
|---|---:|---:|---:|---:|
| Linear `count` | 8.00 | 73.00 | 913.00 | 12.08 |
| `log1p(count)` | 2.20 | 4.30 | 6.82 | 2.34 |
| `count ** 0.75` (primary) | 4.76 | 24.97 | 166.09 | 6.08 |

The primary weight (scale 5.0, cap 300) has median 23.78 pA, p99 117.09 pA and
maximum 300.00 pA on signed threshold-5 edges; 260 edges sit at the cap. The
uncapped maximum would be 755.64 pA.

### 6.3 Sensitivity transformations

| Name | Transform | Scale | Cap |
|---|---|---:|---:|
| `linear_capped` | linear | 0.5 | 300 pA |
| `log1p` | log1p | 10.0 | none |
| `power_half` | `count ** 0.5` | 5.0 | 300 pA |
| `power_1` | `count ** 1.0` | 0.5 | 300 pA |
| `uncapped_power` | `count ** 0.75` | 5.0 | none |

Each is a sensitivity condition. None silently replaces the primary policy.

---

## 7. Per-threshold coverage

The three Phase 4D graphs are kept as separate experimental conditions and are
never combined. All three retain the same 172,433 endpoint nodes; the thresholds
differ in which edges survive.

| Quantity | t1 | t5 (primary) | t10 |
|---|---:|---:|---:|
| Nodes | 172,433 | 172,433 | 172,433 |
| Edges | 11,596,517 | 1,535,710 | 570,721 |
| Structural synapses | 34,310,230 | 18,552,546 | 12,397,230 |
| Isolated nodes | 6,232 | 24,320 | 62,551 |
| Signed edges | 4,369,958 | 683,100 | 266,974 |
| Signed edge share | 37.68 % | 44.48 % | 46.78 % |
| Signed synapses | 14,302,117 | 8,426,168 | 5,756,325 |
| Signed synapse share | 41.68 % | 45.42 % | 46.43 % |
| Excluded edges | 7,226,559 | 852,610 | 303,747 |
| Excluded synapses | 20,008,113 | 10,126,378 | 6,640,905 |

Signed coverage rises with threshold because low-count edges are
disproportionately contributed by unannotated neurons. Even at threshold 10 more
than half of all structural synapses remain unsignable under verified-only
policy.

### 7.1 Per-class coverage at threshold 5

| Class | Neurons | Edges | Edge share | Synapses | Synapse share |
|---|---:|---:|---:|---:|---:|
| Verified excitatory | 53,987 | 502,727 | 32.74 % | 6,015,264 | 32.42 % |
| Verified inhibitory | 9,733 | 180,373 | 11.75 % | 2,410,904 | 13.00 % |
| Verified conflict | 5 | 96 | 0.006 % | 1,385 | 0.007 % |
| Verified modulator-only | 1,567 | 8,525 | 0.555 % | 83,155 | 0.448 % |
| Unannotated | 107,141 | 843,989 | 54.96 % | 10,041,838 | 54.13 % |
| **Total** | **172,433** | **1,535,710** | **100 %** | **18,552,546** | **100 %** |

The class totals equal the graph totals exactly (partition check recorded in the
JSON), so no edge or synapse is double-counted.

Per-threshold per-class tables for t1 and t10 are in the JSON
(`thresholds.tX.primary_policy.coverage.by_class`).

---

## 8. Resource measurements

| Threshold | Graph load | Policy build | Policy arrays | Graph edge arrays |
|---|---:|---:|---:|---:|
| t1 | 0.86 s | 3.44 s | 88.8 MiB | 176.9 MiB |
| t5 | 0.18 s | 2.01 s | 12.0 MiB | 23.4 MiB |
| t10 | 0.09 s | 1.82 s | 4.7 MiB | 8.7 MiB |

Graphs were released before the next threshold was loaded, so only one threshold
was resident at a time. The whole audit took 18.8 s. The signed edge arrays hold
two `float32` weights per edge (excitatory and inhibitory); this duplicates the
int32 `count` array, which is the dominant cost at threshold 1.

---

## 9. Interpretation and limitations

1. **The primary policy is a verified-only sign prior.** It is not a claim that
   BANC transmitters produce a fixed effect at every target, and it does not model
   receptor identity, chloride reversal, cotransmission or neuromodulation.
2. **Most of the network is unsignable.** 62 % of neurons and 54 % of
   threshold-5 edges carry no verified sign. Primary results describe the signed
   subgraph only.
3. **Conflicts and modulators stay unknown by construction.** Five conflict
   neurons and 1,567 modulator-only neurons are excluded rather than resolved
   arbitrarily.
4. **Predicted labels are a sensitivity axis, not evidence.** The fallback
   condition signs roughly twice as many edges; agreement between conditions
   would be more reassuring than disagreement, but neither is biological proof.
5. **Weights are structural.** No calibration to electrophysiology exists; the
   pA scale is a declared model parameter with a pre-registered calibration rule.
6. **Thresholds change sign coverage.** Signed edge share moves from 37.7 % (t1)
   to 46.8 % (t10), so threshold cannot be treated as a neutral detail.

---

## 10. Verdict

**PASS.** The transmitter-sign and edge-weight policies are explicit,
configurable, measured on all three thresholds, and reproducible. No simulation
was run before these numbers existed, and no unknown edge receives an arbitrary
sign. The verified-only limitation is the dominant scientific constraint for the
propagation experiments that follow.
