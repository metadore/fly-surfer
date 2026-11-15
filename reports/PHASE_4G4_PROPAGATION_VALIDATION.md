# Phase 4G.4 — Propagation Validation

Status: **PASS**
Date: 2026-11-08

This report validates that the Phase 4G BANC simulation pathway implements
directed synaptic propagation as specified. It tests the implementation, not
biology. Toy graphs are synthetic and the full-graph smoke test is a single
seeded run; neither establishes physiological propagation in BANC.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4g/run_propagation_validation.py` | Runs the 20-check toy suite and records the smoke runs |
| `reports/PHASE_4G4_PROPAGATION_VALIDATION.json` | Machine-readable observations, hashes and verdict |
| `experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108/` | First full-graph smoke run |
| `experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108_repeat/` | Identical repeat run for determinism |

Run: `python experiments/phase_4g/run_propagation_validation.py` (0.38 s).

## 1. What "propagation" means in this implementation

A stimulated neuron emits a spike. Every outgoing structural edge carries the
presynaptic neuron's sign and a weight derived from the integer synapse count.
The weight becomes an exponentially decaying current (5 ms excitatory, 8 ms
inhibitory) delivered after a quantised axonal delay. Postsynaptic neurons
integrate that current with the shared LIF model and fire when their membrane
potential reaches −50 mV.

Propagation is therefore a chain of structural edges whose summed, time-aligned
current crosses the 150 pA rheobase equivalent. A single edge is not enough.

## 2. Toy-graph suite

Twenty checks, all passed. Each check builds a small `BancConnectome` directly
from CSR arrays, so the real graph loader is not involved. The chain uses four
stimulated sources, four intermediates and one target, all acetylcholine.

### 2.1 Baseline chain

| Observation | Value |
| --- | --- |
| Source first spikes | 3.0 ms (all four) |
| Intermediate first spikes | 7.5 ms (all four) |
| Target first spike | 12.0 ms |
| Target spike count | 1 |
| Spike transmissions | 20 |

The ordering is source → intermediate → target with at least one delay step
between layers.

### 2.2 Check results

| # | Check | Expectation | Observed | Result |
| --- | --- | --- | --- | --- |
| 1 | `convergent_chain_ordering` | Every layer fires in order | 3.0 → 7.5 → 12.0 ms | PASS |
| 2 | `single_edge_attenuation` | One capped edge alone cannot fire a resting neuron | Source 1 spike, target 0, peak current 300 pA | PASS |
| 3 | `convergence_required` | Four 300 pA edges fire the target | Target 1 spike at 7.5 ms, peak 1200 pA | PASS |
| 4 | `edge_removal_downstream` | Removing intermediate→target edges silences only the target | Intermediate trains bit-identical; target 0 | PASS |
| 5 | `edge_removal_upstream` | Removing source→intermediate edges silences downstream | Sources spike; intermediates and target 0 | PASS |
| 6 | `weight_reduction_below_recruitment` | Count 10 edges do not recruit the target | Intermediates spike; target 0 | PASS |
| 7 | `weight_monotonicity` | Capped 500 (300 pA) is not later than uncapped 200 (266 pA) | 12.0 ms vs 13.0 ms | PASS |
| 8 | `cap_saturation_equivalence` | Counts above the cap are identical | Hash equal for 240 and 5000 | PASS |
| 9 | `direction_reversal` | Reversed edges cannot drive an unstimulated target | Intermediates spike; target 0 | PASS |
| 10 | `inhibitory_only_target_silent` | Inhibitory intermediates cannot drive the target | Target 0; inhibitory peak 1200 pA; minimum membrane −79.44 mV | PASS |
| 11 | `inhibitory_mixed_reduces_target` | One inhibitory input does not increase target recruitment | Baseline 1 spike at 12.0 ms; mixed 0 | PASS |
| 12 | `unknown_sign_excluded` | Unannotated presynaptic neurons contribute zero current | All four target edges weight 0; target 0 | PASS |
| 13 | `predicted_only_excluded` | Predicted labels are outside the primary policy | Declared policy `verified-only`; target 0 | PASS |
| 14 | `predicted_fallback_enables_propagation` | Fallback is a real sensitivity, not a no-op | Declared policy `verified-then-predicted`; target 1 | PASS |
| 15 | `no_stimulation_silence` | No drive, no spikes | 0 spikes | PASS |
| 16 | `current_injection_threshold` | 100 pA is sub-rheobase, 300 pA is supra | 0 vs 1 spike | PASS |
| 17 | `delay_quantisation` | Shortest latency respects the 1.0 ms delay | 4.5 ms including EPSP rise | PASS |
| 18 | `refractory_interval` | ISI never below 2 ms | 12 spikes, every ISI 2.5 ms | PASS |
| 19 | `isolated_nodes_silent` | Isolated nodes never spike | 0 spikes for isolated nodes | PASS |
| 20 | `deterministic_repeat` | Same seed identical, different seed different | Seed 7 hashes equal; seed 8 differs | PASS |

### 2.3 Mechanistic findings

**Attenuation.** A capped 300 pA edge is the maximum drive under the primary
policy. With a 10 nS leak and a 5 ms exponential current, that edge raises the
membrane by roughly 4.7 mV at its peak, far short of the 15 mV needed from rest.
Propagation in the full graph therefore requires convergence or repeated
spiking, not a single structural connection. This is a property of the declared
neuron and weight parameters, not an implementation defect.

**Cap saturation.** `weight = min(5.0 × count^0.75, 300 pA)` saturates at
`count = (300/5)^(4/3) ≈ 234.89`. Counts 240 and 5000 produced bit-identical
spike trains. Any structural weight above that count carries no additional
current; this must be stated whenever the weight policy is described.

**Delay is not the whole latency.** The configured 1.0 ms delay is quantised to
two 0.5 ms steps. The measured 4.5 ms source→intermediate latency includes
about 3.5 ms of EPSP rise time. The check asserts only the delay floor.

**Inhibition is real and sign-consistent.** An all-inhibitory intermediate layer
produced 1200 pA of inhibitory current, pushed the target to −79.44 mV, and
silenced it. A single inhibitory input among four was enough to remove the
baseline target spike. Sign is inherited from the presynaptic neuron only.

**Unknown and predicted labels behave as declared.** Unknown-sign edges carry
exactly zero weight, and predicted-only labels do nothing unless
`predicted_fallback` is enabled. Turning the fallback on changes the outcome,
which is why it is reported as a sensitivity condition rather than a default.

## 3. Full BANC smoke test

### 3.1 Selection and parameters

The stimulus set was chosen before any simulation output was inspected:
the 64 nodes with the largest out-degree at threshold 5, ties broken by
ascending node index (`highest_out_degree`). Out-degree is a structural
property of the graph, not a biological claim.

| Parameter | Value |
| --- | --- |
| Graph | BANC v888, threshold 5 |
| Nodes | 172,433 |
| Edges | 1,535,710 |
| Synapses | 18,552,546 |
| Stimulated neurons | 64 |
| Stimulus | 300 pA, 10–40 ms, square pulse |
| Duration | 100 ms |
| Time step | 0.5 ms |
| Seed | 20261108 |
| Background / noise | 0 pA / 0 pA |
| Neuron and synapse model | Unchanged Phase 2 LIF and exponential synapses |

### 3.2 Results

| Metric | First run | Repeat run |
| --- | --- | --- |
| Total spikes | 74 | 74 |
| Active neurons | 64 | 64 |
| Active fraction | 0.000371 | 0.000371 |
| Mean rate | 0.0043 Hz | 0.0043 Hz |
| Runtime | 0.7345 s | 0.6934 s |
| Steps per second | 272.3 | 288.4 |
| RSS after run | 197.25 MB | 200.32 MB |
| Peak working set | 264.80 MB | 268.93 MB |
| Activity SHA-256 | `b660f712d9490a7ff29b6d4326fdb36344cc7db7a67925f5b9a9aa2ce167a1d5` | `b660f712d9490a7ff29b6d4326fdb36344cc7db7a67925f5b9a9aa2ce167a1d5` |

The two runs produced identical spike times and neuron indices. The activity
hash covers the raw spike-time and neuron-index arrays. Runtime differs by
about 6 %, which is expected scheduling noise and does not affect results.

**No downstream recruitment.** All 74 spikes belong to the 64 stimulated
neurons; no unstimulated neuron crossed threshold. This is consistent with the
attenuation finding: the stimulated set was selected for high out-degree, not
for convergence onto targets, and one capped edge per connection is below
threshold. The smoke test demonstrates that the pathway runs, stays finite,
and is reproducible on the full graph. It does not demonstrate propagation
beyond the stimulated set, and must not be reported as such.

## 4. Determinism

| Comparison | Result |
| --- | --- |
| Toy seed 7, run 1 vs run 2 | Identical hash `7d48479a…` |
| Toy seed 7 vs seed 8 | Different hash (`7d48479a…` vs `b2e3e378…`) |
| Full-graph seed 20261108, run 1 vs repeat | Identical hash `b660f712…` |

No nondeterminism was observed. Timing measurements vary between runs; spike
content does not.

## 5. Interpretive limits

- Toy graphs prove that the code implements the declared rules. They do not
  prove that BANC propagates activity in vivo.
- The full-graph run is one seeded condition with a structural stimulus set.
  A single successful run is not evidence of a general propagation regime.
- The 300 pA cap and the attenuation result mean that recruitment depends on
  convergence. Any later claim of "network activation" must report active
  fractions and the number of unstimulated active neurons, not only spike
  totals.
- Verified-only signing excludes most edges (about 55 % at threshold 5). The
  smoke test therefore runs on the labelled subnetwork, not on the full
  structural graph.
- Structural connectivity, synapse counts and transmitter identity are not
  physiological connectivity, conductance or postsynaptic effect.

## 6. Verdict

**PASS.** All 20 controlled propagation checks passed, and the full-graph
smoke test ran deterministically on the complete threshold-5 graph. The
observed attenuation and cap saturation are documented as properties of the
declared model, and the absence of downstream recruitment in the smoke test is
recorded rather than interpreted as biological silence.
