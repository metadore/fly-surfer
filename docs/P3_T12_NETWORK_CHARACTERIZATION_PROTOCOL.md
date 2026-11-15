# P3-T12 — Network ignition and stability: protocol and source audit

Phase: P3-T12 (Phase 3 completion programme, work package 2)
Status: pre-registered protocol. Written before the characterization runner was
implemented and before any P3-T12 simulation was executed.
Git HEAD at registration: `62a64309cadc0db7353c856607cee5369993bd65`
Protected inputs: all nine match `configs/causal_control_config.yaml`
(README, connectome, sensory, simulation, neuron, perception, detector configs,
split manifest, detector model).

## 1. Research question

How does the FLY-SURFER network move from localized sensory current injection
into population-scale recurrent activity, and which measurable properties
separate bounded, sparse off-target discharge from the 15.65 M-spike regime
recorded in P3-T2 C3?

The question is descriptive. It asks what the configured model does; it does
not ask whether the network has learned, perceived, decided or encoded
information, and no such claim is made anywhere in this protocol.

## 2. Source audit (read from code, not from summaries)

### 2.1 Membrane evolution

`brain/neuron_model.py` integrates a passive leaky membrane per neuron with the
exact exponential-Euler solution over each timestep:

```
V(t+dt) = E_L + (V(t) - E_L) * exp(-dt/tau_m) + I * (1 - exp(-dt/tau_m)) / g_L
```

with `tau_m = C_m / g_L = 200 pF / 10 nS = 20 ms`, `E_L = -65 mV`,
`dt = 0.5 ms`. The decay factor is therefore 0.97531 per step. The model has no
voltage-gated conductances, no adaptation and no membrane noise here
(`noise_std_pa = 0`, `background_current_pa = 0` in every P3-T2/P3-T3/P3-T12
condition).

### 2.2 Threshold crossing

At the end of each timestep, after the passive update and the floor clamp, a
neuron spikes iff `V >= threshold_mv (-50 mV)`. Spike times are quantised to
`dt`, recorded as `(step + 1) * dt`. There is **no upper clamp**: the upper
bound is structural, because a neuron at or above threshold is reset in the
same step. Consequently any sampled membrane maximum is strictly below
threshold, and a reported value of `-50.000` mV (seen in P3-T2 C3) is a
near-threshold state rounded to four decimals, not a clamped rail. P3-T12
measures this explicitly.

### 2.3 Reset and refractoriness

A spiking neuron is set to `reset_potential_mv = -68 mV` and its refractory
counter to `ceil(2.0 / 0.5) - 1 = 3` blocked steps. A blocked neuron is forced
to `-68 mV` during each blocked step, so the minimum inter-spike interval of a
single neuron is 2.0 ms and the maximum possible per-neuron rate is 500 Hz.
Refractory occupancy is a distinct state from "at rest" and is counted
separately.

### 2.4 Voltage floor

`np.maximum(V, minimum_potential_mv)` clamps every neuron to `-90 mV` after the
passive update and before the threshold test. This is a true clamp and the only
enforced rail. Because it is applied before the spike test, it can never create
a spike. P3-T2 C3 reaches `-90.000` mV; P3-T12 counts neuron-steps at the clamp
rather than only the minimum.

### 2.5 Synaptic current and recurrence

`brain/synapse_model.py` assigns each edge a weight
`12.0 * syn_count ** 0.75` pA (structural count transformed, not a measured
conductance) and a sign from the presynaptic predicted transmitter (ACH/GLUT
excitatory, GABA inhibitory, DA/SER/OCT and unlabelled unresolved → excitatory
by policy). Each spike adds its outgoing weights into a two-slot delay deque;
currents decay exponentially with `tau_exc = 5 ms` / `tau_inh = 8 ms`. The
effective transmission delay is one timestep (0.5 ms) rounded from
`delay_ms = 1.0`; a spike at step k first contributes to step k+2. Total
synaptic current is `I_exc - I_inh`, added to the external schedule.

### 2.6 Step order and recording

`brain/brain_simulator.py` runs, per step: (1) decay synaptic currents and
deliver the delayed packet, (2) build the current vector
`noise + background + synaptic + schedule`, (3) update membranes and detect
spikes, (4) record spikes, (5) route spikes into the delay buffer. Spikes are
stored in a preallocated `SpikeRecorder` (float32 times, int32 indices,
capacity 30,000,000 = 240 MB) that raises `SpikeCapacityExceeded` instead of
dropping data. Membrane diagnostics are sampled every 200 steps and at the end
only, and record only the minimum and maximum — no distribution, occupancy or
per-step history is currently retained. This is the gap P3-T12 must fill.

### 2.7 Features of the existing runner that are reused unchanged

`experiments/phase_3c/causal_control.py` provides the validated config loader,
graph/mapping setup, feature mapping, scheduler construction, current audit,
partition metrics, protected-hash check, git state and output writing. P3-T12
reuses those; it does not modify them. The P3-T3 ablation specs are reused for
the two ablations, again unchanged.

### 2.8 What the audit rules out

* No homeostatic or activity-dependent term exists, so "stability" in this
  protocol cannot mean biological homeostasis.
* No explicit upper rail exists, so "both rails reached" is not symmetric and
  must be restated (floor clamp vs threshold reset).
* Membrane distributions are not recorded by the existing runner, so all
  distributional claims require new instrumentation.
* Recurrence is delayed by one step and sign-assigned by policy; any
  "propagation" measured here is propagation in this graph under these weights.

## 3. Conditions and controls

Seven conditions, all sharing graph, mapping, seeds, initial state, dt and the
frozen cached frames. Only the input schedule or the observation window differs.

| Name | Source | Active features | Duration (ms) | Rationale |
| --- | --- | --- | ---: | --- |
| C0 | none | none | 3,300.5 | no-input floor; P3-T2 control |
| C1 | neutral frames | 4 player features | 3,300.5 | player defaults only |
| C2 | cached frames | 10 non-player features | 3,300.5 | visual drive without player |
| C3 | cached frames | all 14 | 3,300.5 | full input; archived reference |
| no-player_lane | cached frames | 13 (player_lane removed) | 3,300.5 | P3-T3 collapsed tail |
| no-train_lane | cached frames | 13 (train_lane removed) | 3,300.5 | P3-T3 four-spike tail |
| C3-washout | cached frames | all 14 | 4,050.5 | C3 plus 250 ms hold ceiling and 500 ms with no scheduled drive |

The first six are the controls named in the programme; they are executed with
their original definitions. `C3-washout` is the one additional condition. Its
rationale: with drive present for the whole 3,300.5 ms, "sustained activity"
cannot be separated from "driven activity". Extending the same C3 schedule by
750 ms crosses the scheduler's 250 ms `max_hold_ms` ceiling (measured from the
last frame at 3,300 ms) and leaves 500 ms in which no frame hold and no pulse
tail can deliver current. The extension changes only the simulated duration and
the number of recorded steps; the schedule itself is the archived one. Input
comparability is enforced by a prefix gate (§5.3), and no recorder capacity is
changed: the washout run uses the same 30,000,000-spike budget as P3-T2.

No other control is introduced. No neuron-model, synapse, connectome or
scheduler parameter is changed anywhere in P3-T12.

## 4. Instrumentation

A dedicated stepper in `experiments/phase_3c/network_characterization.py`
reuses `LIFPopulation`, `SynapseModel` and `SpikeRecorder` and reproduces the
exact step order of §2.6. It adds read-only measurements only; it does not
alter state. Equivalence with `BrainSimulator` is a hard gate (§5).

Recorded per condition:

1. **Spikes and partitions** — total, inside/outside reference R (fixed 138
   mapped neurons), inside/outside the condition's active set A_c, first and
   last spike per partition (reusing `causal_control._partition_block`).
2. **Recruitment over time** — 10 ms bins: spikes per partition, newly active
   neurons, cumulative active fraction; descriptive crossing times at 1, 5, 10
   and 25 % of the graph (checkpoints, not criteria).
3. **Ignition latency** — first spike overall, first in A_c, first outside A_c,
   first outside R, delay from first A_c spike to first outside-A_c spike, and
   the last spike.
4. **Propagation** — per-bin outside-A_c spikes relative to the preceding bin
   (descriptive cascade ratio, not a branching ratio), transmissions per spike
   from the simulator summary, and the first time each hop-distance ring from
   A_c becomes active.
5. **Firing-rate distribution** — per-neuron rates over the whole run and over
   the last 500 ms; percentiles (1, 5, 10, 25, 50, 75, 90, 95, 99, 100) over all
   neurons and over active neurons; histogram on fixed edges
   `[0, 0.1, 1, 5, 10, 20, 50, 100, 200, 400] Hz`; share of spikes carried by
   the top 1 % most active neurons (concentration).
6. **Active fractions** — whole graph, A_c, outside A_c, outside R, at the end
   of the run and per 100 ms bin.
7. **Membrane distributions** — every 10 ms: exact min/max, mean, standard
   deviation, percentiles (1, 5, 10, 25, 50, 75, 90, 95, 99), and counts on
   fixed edges `[-90, -85, -80, -75, -70, -65, -60, -55, -50]` mV.
8. **Time at bounds** — every step: exact global min/max, neuron-steps at the
   −90 mV clamp, neuron-steps in the refractory state, neuron-steps with
   `V >= threshold − 0.05 mV` while not spiking, all as counts and as fractions
   of neuron-steps.
9. **Persistence** — fraction of 10 ms bins with any spike and with any
   outside-A_c spike, longest inter-spike gap per partition, longest run of
   consecutive active 10 ms bins, and per-100 ms activity over the final second.
   For `C3-washout` the same quantities are computed in the 500 ms window after
   scheduled drive is impossible, plus the spike-count decay curve in 50 ms
   bins from the last possible drive step.
10. **Graph-topological recruitment** — directed hop distance from A_c to every
    node (scipy `dijkstra(min_only=True, unweighted=True)`), then per distance
    bucket `[0, 1, 2, 3, 4, 5, 6-10, 11-20, >20, unreachable]`: neuron count,
    active count, spikes, median first-spike time. This is structural distance,
    not conduction distance and not a spatial coordinate.
11. **Classification** — the P3-T3.1 regime classifier (`none` / `sparse` /
    `population_scale`) applied unchanged, plus its raw measurements.

**Directly stimulated vs network-driven.** Spikes in A_c and outside A_c are
the only clean partition available: a neuron's spike cannot be attributed
causally to injection versus synaptic input. "Outside A_c" therefore means
"not eligible for direct injection", not "proven network-driven". This wording
is used everywhere in the results.

## 5. Equivalence, determinism and invalidations

### 5.1 Loop-equivalence gate (prerequisite for full mode)

Before any characterization result is accepted, the instrumented C3 run over
3,300.5 ms must reproduce the archived P3-T2 C3 result exactly:
`spike_counts_sha256 = 09611c7dc5c37d435f7713f5b0ce42b9ab90bdf2b12efeb6c91125b0e0978305`,
15,654,631 spikes, 3,710 stimulated, 15,650,921 non-stimulated, first spike
28.0 ms, last spike 3,300.5 ms. A second, synthetic check compares the
instrumented stepper with `BrainSimulator` on a small graph and asserts
identical spike arrays. Failure of either gate makes the run INVALID and stops
the characterization.

### 5.2 Repeatability

Every condition runs twice in the same process; spike-count hash, spike total,
first/last spike, current trace and scheduler signature must match exactly.
C3 and C3-washout are also re-run in fresh subprocesses.

### 5.3 Washout prefix gate

The first 3,300.5 ms of `C3-washout` must be bit-identical to C3: the per-neuron
spike counts restricted to `time <= 3300.5` must equal C3's counts, and the
derived hash must match. Otherwise the extension is not comparable and the
condition is marked INVALID. Spike times are multiples of 0.5 ms; the boundary
is compared with a 1e-6 tolerance.

### 5.4 Invalidations

A run is INVALID if any of the following holds (each is evaluated and recorded):

1. `loop_equivalence_failed` — §5.1 gate fails.
2. `spike_capacity_exceeded` — the 30,000,000 recorder budget is hit.
3. `non_finite_state` — membrane or synaptic state is not finite.
4. `membrane_below_floor` / `membrane_above_threshold` — exact min/max outside
   `[-90, -50] mV` beyond 1e-6 (the same rule as P3-T2).
5. `repeated_runs_differ` — in-process repeats disagree on a recorded key.
6. `subprocess_runs_differ`.
7. `prefix_mismatch` — §5.3 fails.
8. `protected_hash_changed` — any of the nine protected inputs changed.
9. `initial_conditions_differ` — graph, mapping, seeds, dt, LIF/synapse
   parameters or capacity differ between conditions.
10. `condition_definition_violation` — e.g. C0 has no scheduler, C3 active set
    equals R, an ablation activates exactly 13 features, or any current reaches
    neurons outside its active set.
11. `scheduler_signature_mismatch` — C3's signature differs from the archived
    `1c3ab12d…` value.

Overflow is an invalidation, never a reason to raise the capacity mid-campaign.

## 6. Capacity and compute preflight (measured, not extrapolated)

Measured from the archived P3-T2 and P3-T3 runs at the same settings:

* Recorder: 15,654,631 spikes = 52.2 % of 30 M in C3; the worst P3-T3
  condition used 52.2 %. 213 MB headroom (7.7 M spikes) before the 75 % review
  mark of the P3-T3 campaign.
* Wall time per condition (two repeats, including load in P3-T3): C0/C1/C2 and
  the collapsed ablations 13.1–13.9 s per single run; C3 55.4 s per single run.
* Peak RSS: 315–324 MB for igniting conditions, 194–198 MB for collapsed ones.

P3-T12 estimates before execution: seven conditions × two repeats
≈ 2 × (13.1 + 13.4 + 13.6 + 55.4 + 13.1 + 13.1 + ~68) s ≈ 380 s of simulation,
plus instrumentation, current audit, distance computation and graph load;
budget 10–15 minutes and < 500 MB RSS. The washout adds ~3.5 M spikes at the
observed mean rate (21 % of capacity); overflow is possible only under a
sustained rate increase of more than ~60 % after drive ends, and would be
reported as an INVALID measurement rather than fixed by changing the budget.

Preflight is performed with a 600 ms smoke window over all seven conditions and
must report measured wall time, per-step instrumentation overhead, RSS, spike
counts, equivalence status (smoke equivalence is limited to the P3-T3 600 ms
smoke, which is not archived; only the synthetic small-graph check and the
full-duration gate are binding) and the washout drive cutoff. Short-run spike
counts are **not** extrapolated linearly to the full duration.

## 7. Analysis policy

* Descriptive only. Counts, rates, fractions, times, distributions. No p-values,
  no effect sizes, no significance language.
* Both partitions (R vs outside R, A_c vs outside A_c) are reported everywhere.
* C3 is not C1 + C2 and no contrast is treated as an additive decomposition.
* Silence is a result: C0 must be reported as measured.
* Rail occupancy is reported as counts and fractions, with the floor clamp and
  the threshold reset distinguished.
* No mechanism claim: hop distance is structural, "outside A_c" means "not
  injected", and no statement is made about information routing, biological
  pathways, perception, learning or behaviour.

## 8. Interpretation vocabulary

Five outcomes are kept separate and are never used interchangeably:

1. **Network ignition** — provisional, defined exactly as in P3-T3.1
   (`population_scale`: outside-R active neurons > 138 and outside-R rate ≥
   reference rate).
2. **Sustained recurrent activity** — activity that continues across most late
   bins and, for C3-washout, across the post-drive window. Reported as measured
   fractions and decay, not as a binary verdict.
3. **Numerical/physical stability** — finite state, no invalidation, bounded
   membrane values, and explicit rail occupancy. Not biological homeostasis.
4. **Useful sensory propagation** — not measured by P3-T12 and not claimed.
5. **Task-relevant information transmission** — not measured by P3-T12 and not
   claimed.

A condition can be ignited in the model and still carry no useful sensory
information; P3-T12 cannot distinguish the two.

## 9. Pre-registered acceptance criteria

P3-T12 is complete when:

1. The protocol, runner and focused tests exist.
2. The loop-equivalence gate passes (synthetic and archived C3).
3. All seven conditions run at full duration with two identical in-process
   repeats, plus fresh-subprocess repeats for C3 and C3-washout.
4. No invalidation is triggered, or every triggered invalidation is preserved
   and reported with its measurement.
5. Items 1–11 of §4 are each reported, or explicitly marked unmeasurable with a
   reason.
6. The P3-T3.1 classification is applied unchanged and quoted as provisional.
7. A P3-T12 report states results, stability analysis, limitations and
   unresolved mechanisms.
8. P3-T2 and P3-T3 artifacts are byte-identical before and after; README and all
   protected hashes are unchanged.

Negative outcomes are accepted outcomes: if C3-washout activity collapses within
a few tens of milliseconds, the measured decay is the result.

## 10. Risks

* Frame-rate aliasing is irrelevant here (frames define current, not spikes) but
  the 0.5 ms step and 2 ms refractory bound all temporal resolution.
* Threshold dominance: the spike-reset structure keeps almost all sampled
  membrane values far from threshold; distributions may be dominated by the
  floor clamp and refractory state rather than by a graded subthreshold
  distribution.
* The graph has no spatial coordinates, so "localized" can only mean
  graph-topological and partition-based.
* Washout extrapolates beyond the archived duration. The prefix gate protects
  comparability, but the last 750 ms are outside the validated window.
* Spike concentration and cascade ratios are descriptive and can be
  over-interpreted; they are labelled as such.
* Instrumentation adds work per step; measured overhead is reported so that
  runtime differences are not attributed to the dynamics.

## 11. Deliverables

* This protocol.
* `configs/p3_t12_characterization.yaml`.
* `experiments/phase_3c/network_characterization.py`.
* `tests/test_network_characterization.py`.
* `experiments/phase_3c/results/p3_t12_preflight.json` (+ sidecar).
* `experiments/phase_3c/results/p3_t12_network_characterization.json`
  (+ sidecar).
* `experiments/phase_3c/results/p3_t12_network_characterization_report.md`.
