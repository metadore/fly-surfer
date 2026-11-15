# FLY-SURFER — Phase 4H.2 Population Size and Selection Sensitivity

Status: **PASS WITH LIMITATIONS**
Date: 2026-11-08
Phase: 4H.2
Parent protocol: `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`

Phase 4H.2 asks how the Phase 4G motor result depends on the **number** of
stimulated neurons and on the **rule used to select them**. It holds the world,
sign policy, weight transform, stimulation protocol, duration and decoder fixed
and varies only candidate-set size and selection rule. It is a sensitivity
analysis of a simulated decoder output, not evidence of biological motor
control. The result is a strong size dose-response under connectivity ranking,
a smaller and rule-dependent motor response under degree ranking, and a
near-silent response under size-matched random selection at every size tested.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4h/population_sensitivity.py` | Builds the surface, the reference and the JUMP pool null model |
| `experiments/phase_4h/common.py` | Shared world loader, candidate pools, simulator, metrics and hashing |
| `experiments/results/phase_4h/population_sensitivity.json` | All 175 run records, surface table, cell statistics, confirmatory test, integrity |
| `experiments/results/phase_4h/population_sensitivity.checkpoint.jsonl` | Append-only per-run checkpoint used for resume |
| `tests/test_phase_4h_runners.py` | Focused tests for endpoint statistics, Holm correction and family helpers |

Run:

```
python -m experiments.phase_4h.population_sensitivity
```

175 runs. Summed simulation time over the stored runs 460.15 s (7.7 min),
mean 2.63 s per run, 600 integration steps per run; assembly of the JSON from
the checkpoint takes 4.1 s.

## 1. Question and design

Phase 4G.5 stimulated the 64 highest-ranked verified-excitatory VNC intrinsic
neurons by motor-synapse count (condition C) and observed 1,296 spikes, 492
motor spikes and four JUMP windows. Phase 4H.1 showed that this result is
distinguishable from five matched random-control families. It did not answer
two prior questions:

1. Is the result a consequence of stimulating 64 neurons, or would any number
   of connectivity-ranked neurons do?
2. Is the result specific to connectivity ranking, or would other plausible
   selection rules produce the same decoder output?

4H.2 crosses seven candidate sizes with seven selection rules. Sizes are
8, 16, 32, 48, 64, 96 and 128. The rules are:

| Rule | Pool | Draws per size |
| --- | --- | --- |
| `connectivity_ranked` | VNC intrinsic verified-excitatory, ranked by motor-synapse score | 1 |
| `random_eligible` | Same pool with the 64 condition C neurons removed | 10 |
| `in_degree_ranked` | Same VNC pool, ranked by in-degree | 1 |
| `out_degree_ranked` | Same VNC pool, ranked by out-degree | 1 |
| `combined_degree_ranked` | Same VNC pool, ranked by in-degree + out-degree | 1 |
| `verified_excitatory_all_classes` | All verified-excitatory neurons, any super-class, ranked by motor-synapse score | 1 |
| `annotation_stratified_random` | Same pool as `random_eligible`, stratified by `cell_class` using the ranked composition at the same size | 10 |

The VNC intrinsic eligible pool is 5,622 neurons; removing the 64 condition C
neurons leaves 5,558, matching 4H.1 family A. The all-class verified-excitatory
pool is 53,957 neurons.

The replication unit is the candidate-set draw. Because the simulator uses zero
background and zero noise, two draws that select the same neurons are
bit-identical; variability is only reported for the two random rules, which
draw ten independent candidate sets per size. Ranked rules are deterministic
and run once, so their surface entries carry no sampling uncertainty.

The design was frozen in the parent protocol before execution. The runner
verifies the protocol SHA-256 at start-up.

## 2. Fixed conditions

| Item | Value |
| --- | --- |
| Graph | BANC v888, threshold 5, 172,433 nodes, 1,535,710 edges, 18,552,546 synapses, 24,320 isolated |
| Graph artifact | `datasets/processed/banc_v888/banc_graph_t5.npz`, SHA-256 `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Node table | `datasets/processed/banc_v888/banc_nodes.csv.gz`, SHA-256 `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Sign policy | verified-only; acetylcholine and glutamate excitatory, GABA and glycine inhibitory; modulators and conflicts unknown; predicted fallback off; unknown edges excluded |
| Weight transform | `min(5.0 * count^0.75, 300 pA)`, integer structural synapse count |
| Stimulation | 300 pA, 50–250 ms, all selected neurons |
| Integration | dt 0.5 ms, 300 ms duration, 600 steps |
| Decoder | Phase 4F, unchanged: 50 ms windows, step 50 ms, activation 0.20, release 0.10, ≥5 spikes and ≥3 active neurons, priority LEFT/RIGHT/JUMP |
| Background / noise | 0 pA / 0 pA |
| Spike recording cap | 5,000,000 |
| Seeds | `20261109 + 200000 + 1000*size + 10*rule_ordinal + draw_index` |

Rule ordinals follow the order in the table above. Ties in any ranking are
broken by ascending graph node index, so ranked selections are reproducible
from the graph alone.

## 3. Reference reconstruction and provenance

Condition C (the size-64 `connectivity_ranked` cell) was recomputed from the
graph and node table. Its spike hash is
`397e888ffb7f001e0509bdcfbc9121c09bafb1e2d355b555b298b5c2fed10a95`, equal to
the Phase 4G result file. Its decoded state sequence is
`JUMP, JUMP, JUMP, JUMP, NEUTRAL`, matching Phase 4G. The decision hash stored
here is over 4H `ActionDecision` dictionaries and is not byte-comparable with
the Phase 4G window-record hash; the state sequence is the comparable object.

The reference cell reproduces the Phase 4G metrics exactly: 1,296 total spikes,
740 stimulated and 556 non-stimulated, 164 active neurons, 492 motor spikes
across 82 active motor neurons, LEFT 176 spikes/27 active neurons, RIGHT 155/32,
JUMP 79/12 (active fraction 0.60), first motor spike at 68.5 ms, 2 spikes after
the 250 ms stimulus offset.

The 175 runs were executed in two segments. The first segment stored 129 runs
before a deliberate stop to fix an analysis-only key error in the confirmatory
block; no simulation code, seed or selection rule changed. The second segment
resumed from the checkpoint and completed the remaining 46 runs. The
checkpoint contains 175 records and 0 corrupt lines. The JSON therefore records
`sum_run_wall_time_s` across the stored runs and an `assembly_wall_time_s`
covering only the final assembly invocation.

## 4. Endpoints and statistics

Full endpoints are recorded for every run: total, stimulated and non-stimulated
spikes; active neurons; motor spikes, active motor neurons, active fraction and
peak motor window; LEFT/RIGHT/JUMP spikes, active neurons, active fraction,
peak-window fraction and decoded windows; NEUTRAL windows; time to first motor
spike; post-stimulation spikes; decoder states and scores; spike, decision and
selection hashes; memory and wall time.

Cell summaries report n, mean, SD, median, Q1, Q3, min and max. The only
confirmatory test is fixed at size 64: `connectivity_ranked` against the 100
Phase 4H.1 family A draws, on P1 = motor spikes and P2 = JUMP windows, with
Holm correction over the two endpoints. Every other size and rule comparison is
exploratory and reported descriptively. Exploratory rule contrasts compare each
ranked rule with the ten size-matched `random_eligible` draws; with ten draws
the smallest attainable one-sided p is 1/11 = 0.0909, so those contrasts can
describe separation but cannot reach conventional significance.

## 5. Surface results

Values are the cell mean. Ranked cells have one run; random cells have ten.
Reference (Phase 4G condition C) is the size-64 connectivity cell.

| Rule | Size | Total spikes | Motor spikes | JUMP windows | Runs with JUMP |
| --- | ---: | ---: | ---: | ---: | ---: |
| connectivity_ranked | 8 | 102 | 5 | 0 | 0 |
| connectivity_ranked | 16 | 214 | 14 | 0 | 0 |
| connectivity_ranked | 32 | 490 | 104 | 0 | 0 |
| connectivity_ranked | 48 | 915 | 334 | 3 | 1 |
| **connectivity_ranked** | **64** | **1,296** | **492** | **4** | **1** |
| connectivity_ranked | 96 | 2,155 | 863 | 4 | 1 |
| connectivity_ranked | 128 | 2,836 | 1,126 | 4 | 1 |
| random_eligible | 8 | 88 | 0 | 0 | 0 |
| random_eligible | 16 | 176 | 0 | 0 | 0 |
| random_eligible | 32 | 352.3 | 0 | 0 | 0 |
| random_eligible | 48 | 529 | 0 | 0 | 0 |
| random_eligible | 64 | 705.8 | 0 | 0 | 0 |
| random_eligible | 96 | 1,059.5 | 0.9 | 0 | 0 |
| random_eligible | 128 | 1,415.2 | 0.7 | 0 | 0 |
| in_degree_ranked | 8 | 90 | 0 | 0 | 0 |
| in_degree_ranked | 16 | 214 | 4 | 0 | 0 |
| in_degree_ranked | 32 | 466 | 21 | 0 | 0 |
| in_degree_ranked | 48 | 752 | 60 | 0 | 0 |
| in_degree_ranked | 64 | 1,014 | 92 | 0 | 0 |
| in_degree_ranked | 96 | 1,621 | 211 | 3 | 1 |
| in_degree_ranked | 128 | 2,201 | 373 | 4 | 1 |
| out_degree_ranked | 8 | 97 | 3 | 0 | 0 |
| out_degree_ranked | 16 | 256 | 18 | 0 | 0 |
| out_degree_ranked | 32 | 472 | 27 | 0 | 0 |
| out_degree_ranked | 48 | 701 | 39 | 0 | 0 |
| out_degree_ranked | 64 | 964 | 50 | 0 | 0 |
| out_degree_ranked | 96 | 1,495 | 98 | 0 | 0 |
| out_degree_ranked | 128 | 2,212 | 222 | 3 | 1 |
| combined_degree_ranked | 8 | 94 | 0 | 0 | 0 |
| combined_degree_ranked | 16 | 223 | 6 | 0 | 0 |
| combined_degree_ranked | 32 | 463 | 25 | 0 | 0 |
| combined_degree_ranked | 48 | 746 | 50 | 0 | 0 |
| combined_degree_ranked | 64 | 1,017 | 95 | 0 | 0 |
| combined_degree_ranked | 96 | 1,657 | 192 | 0 | 0 |
| combined_degree_ranked | 128 | 2,217 | 286 | 3 | 1 |
| verified_excitatory_all_classes | 8 | 102 | 5 | 0 | 0 |
| verified_excitatory_all_classes | 16 | 223 | 23 | 0 | 0 |
| verified_excitatory_all_classes | 32 | 548 | 158 | 0 | 0 |
| verified_excitatory_all_classes | 48 | 946 | 342 | 3 | 1 |
| verified_excitatory_all_classes | 64 | 1,378 | 553 | 4 | 1 |
| verified_excitatory_all_classes | 96 | 2,180 | 867 | 4 | 1 |
| verified_excitatory_all_classes | 128 | 3,001 | 1,219 | 4 | 1 |
| annotation_stratified_random | 8 | 88.4 | 0 | 0 | 0 |
| annotation_stratified_random | 16 | 177 | 0 | 0 | 0 |
| annotation_stratified_random | 32 | 353 | 0 | 0 | 0 |
| annotation_stratified_random | 48 | 533.8 | 1.0 | 0 | 0 |
| annotation_stratified_random | 64 | 721.3 | 1.7 | 0 | 0 |
| annotation_stratified_random | 96 | 1,083.6 | 3.0 | 0 | 0 |
| annotation_stratified_random | 128 | 1,457.8 | 5.8 | 0 | 0 |

### 5.1 Size effect under connectivity ranking

Motor spikes rise monotonically with size: 5, 14, 104, 334, 492, 863 and 1,126
at sizes 8, 16, 32, 48, 64, 96 and 128. The first JUMP window appears at size
48 (3 windows), and the count saturates at 4 from size 64 onward. The JUMP
active fraction rises from 0.00 (sizes 8–16) to 0.05 (32), 0.45 (48), 0.60 (64),
0.85 (96) and 0.85 (128), corresponding to 0, 0, 1, 9, 12, 17 and 17 active
JUMP neurons. Because the JUMP pool has only 20 neurons and the decoder needs
four active JUMP neurons (20%), a small absolute increase in JUMP recruitment
moves the pool across the threshold abruptly. The JUMP dose-response is
therefore a threshold effect on a small pool, not a smooth linear response.

### 5.2 Rule effect

At every size, connectivity ranking produces more motor spikes than the
size-matched random draws. At size 64 the separation is complete (492 observed
vs a random mean of 0; exploratory p = 0.0909, Cliff's delta 1.0). The
all-class verified-excitatory ranking is close to connectivity ranking in motor
output (553 vs 492 motor spikes at size 64) and identical in JUMP windows (4 at
sizes 48–128). In-degree, out-degree and combined-degree rankings produce much less
motor output at the same size: 92, 50 and 95 motor spikes at size 64, with no
JUMP windows; JUMP first appears for these rules only at size 96 (in-degree,
3 windows) or 128 (out-degree and combined degree, 3 windows).

`random_eligible` never produced a JUMP window at any size and reached at most
0.9 mean motor spikes (size 96). `annotation_stratified_random` also never
produced a JUMP window and reached 5.8 mean motor spikes at size 128. The
stratified rule reproduces the `cell_class` composition of the ranked pool at
the same size (at size 64: 12 missing, 2 `sequential_leg_neuromeres`,
42 `single_leg_neuromere`, 2 `ventral_nerve_cord_centrifugal`, 6
`ventral_nerve_cord_serially_convergent`), with no stratum shortages and no
top-up neurons.

Two conclusions follow. First, size alone is not sufficient: random sets of 128
neurons remain near-silent at the motor pool while a ranked set of 32 already
produces 104 motor spikes. Second, the specific ranking matters: connectivity
and all-class motor-synapse ranking produce the JUMP result at size 64, while
degree rankings require 96–128 neurons and random selection produces none up to
128. At size 64, JUMP is **not unique** to the VNC connectivity ranking among
these seven rules, because `verified_excitatory_all_classes` also yields four
JUMP windows.

## 6. JUMP pool imbalance

The decoder populations are LEFT 185, RIGHT 186, JUMP 20, motor 805, with 371
leg motor neurons (LEFT + RIGHT) and 414 unassigned motor neurons. At an
activation threshold of 0.20 the pools need 37 LEFT, 38 RIGHT and 4 JUMP active
neurons. One active neuron is 0.54% of LEFT, 0.54% of RIGHT and 5% of JUMP, so
the JUMP pool is structurally far easier to cross.

The reference activates 12/20 JUMP neurons (0.60), which is 3.0 times the 0.20
threshold. For comparison, its LEFT active fraction is 0.146 and RIGHT 0.172,
both below 0.20, so the decoded JUMP windows are not accompanied by a LEFT or
RIGHT crossing.

A null model tests whether this JUMP activity is more than a size effect. For
each run it compares the observed JUMP active fraction with 10,000 seeded
20-neuron subsets drawn without replacement from the 805 motor neurons, and
with 10,000 seeded 20-neuron subsets from the 371 leg motor neurons. The
percentile is the fraction of null subsets with an active fraction at or below
the observed value; `p_greater` is the complementary one-sided value.

| Cell | JUMP null percentile (motor) | p_greater | Leg null percentile |
| --- | ---: | ---: | ---: |
| connectivity_ranked, 48 | 1.0000 | 0.0001 | 0.9999 |
| connectivity_ranked, 64 | 1.0000 | 0.0001 | 1.0000 |
| verified_excitatory_all_classes, 48 | 0.9997 | 0.0004 | 0.9966 |
| verified_excitatory_all_classes, 64 | 0.9996 | 0.0005 | 0.9938 |
| in_degree_ranked, 96 | 0.9995 | 0.0006 | 0.9938 |
| in_degree_ranked, 128 | 1.0000 | 0.0001 | 1.0000 |
| out_degree_ranked, 128 | 0.9938 | 0.0063 | 0.9394 |
| combined_degree_ranked, 128 | 0.9997 | 0.0004 | 0.9908 |
| random_eligible, all sizes | 0.0000 | 1.0000 | 0.0000 |
| annotation_stratified_random, all sizes | 0.0000 | 1.0000 | 0.0000 |

When the rules produce JUMP windows, the active JUMP neurons are more active
than random motor subsets of the same size, including random leg-motor subsets.
When the random rules produce no JUMP windows, the observed JUMP fraction is
zero and the null percentile is zero. The null model tests pool size and
identity against the run's own motor spike pattern; it does not test biological
recruitment, and it reuses the observed run rather than an independent
simulation.

The decoder was not changed. The imbalance is a property of the Phase 4F
population definitions (JUMP 20, LEFT 185, RIGHT 186) and is reported, not
corrected.

## 7. Confirmatory comparison at size 64

The single pre-registered comparison is the size-64 connectivity cell against
the 100 Phase 4H.1 family A draws. Family A draws uniformly from the same
5,558-neuron VNC intrinsic eligible pool (condition C removed), so this is a
size- and pool-matched random null, not an independent replication.

| Endpoint | Observed | Control n | Control median | Control max | Percentile | p (one-sided) | Holm-adjusted | Rejected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| P1 motor spikes | 492 | 100 | 0 | 8 | 1.000 | 0.009901 | 0.019802 | yes |
| P2 JUMP windows | 4 | 100 | 0 | 0 | 1.000 | 0.009901 | 0.019802 | yes |

Both endpoints exceed every one of the 100 control draws, so the attainable p
is the n = 100 floor of 1/101 = 0.009901. Holm-Bonferroni over the two endpoints
gives 0.019802, below 0.05. The same comparison is reported in the 4H.1 result
file; it is repeated here for the size question and is not counted as a second
independent test.

This comparison says that the 64-neuron connectivity-ranked set is
distinguishable from random sets of the same size drawn from the same pool. It
does not say that connectivity ranking is the only rule that works: the
all-class verified-excitatory ranking reaches the same JUMP count at size 64.

## 8. Exploratory rule contrasts

Each rule other than `random_eligible` is compared descriptively with its ten
size-matched `random_eligible` draws. For almost every cell, total and motor
spikes lie at percentile 1.0 (all ten random draws lower), Cliff's delta 1.0,
with the p floor 0.0909 imposed by ten draws. The exceptions are the size-8
in-degree and combined-degree cells, where both observed and random motor
spikes are zero (percentile 0, p = 1.0), and the annotation-stratified cells at
sizes 8–32 (zero motor spikes in both) and at size 96 (3.0 observed vs 0.9 mean
control, percentile 0.8, p = 0.2727). JUMP windows are at percentile 1.0 with
p = 0.0909 only where the rule produces a JUMP window; where it produces none,
percentile and delta are 0 and p = 1.0.

These contrasts are not corrected and are not confirmatory. With ten draws per
cell they can show complete separation from the sampled random distribution but
cannot establish a conventional significance level. They are reported to make
the surface legible, not to multiply the evidence.

## 9. What 4H.2 shows and does not show

**Shows.** Under the fixed protocol, motor output increases monotonically with
candidate size under connectivity ranking. JUMP windows appear only once
recruitment reaches the four-neuron threshold in the 20-neuron JUMP pool, at
size 48 for connectivity and all-class ranking, 96 for in-degree ranking, and
128 for out-degree and combined-degree ranking. Size-matched random selection,
including annotation-stratified random selection, never produces JUMP up to
128 neurons and remains near-silent at the motor pool. At size 64 the
connectivity result is beyond all 100 same-pool random draws (p floor 0.009901,
Holm-rejected).

**Does not show.** It does not show that the result is specific to connectivity
ranking, because the all-class motor-synapse ranking matches it. It does not
show that JUMP is a biological jump command, only that the decoder crosses the
JUMP activation threshold. It does not show that 64 is a privileged size; 48,
96 and 128 also produce JUMP. It does not quantify variability for ranked rules,
which are deterministic single runs. It does not establish that any rule
generalises beyond this graph, this sign policy, this weight transform and this
decoder.

## 10. Integrity and reproducibility

Before and after execution the runner checked 37 protected paths covering the
root README, FAFB and BANC processed artifacts, dataset manifests, Phase 4D–4G
code and outputs, the Phase 3 sensory pipeline, and the parent protocol. All 37
passed before and after; `protected_unchanged` is true. No Phase 4G output was
overwritten. No file was staged, committed or pushed.

Reproducibility fields recorded in the JSON: protocol path and SHA-256
(`7c511c5a9cfb64262e424ab566743ff2b25d86e2c51a12f5a77057dd3e5e6b05`, matches the
frozen hash), mapping config SHA-256
(`a3d57abf1d2e3aad7f9a1fc33567b95ca62e065b6b20a7835e5e7988a51f6ebd`), graph
artifact and node-table SHA-256, graph threshold and counts, sign policy, weight
transform, stimulation amplitude and window, dt, duration, seed formula,
per-run seeds, candidate index hashes, spike and decision hashes, per-run
memory and wall time. Software: Python 3.13.14, NumPy 2.3.4, pandas 2.3.3,
Windows 11.

Runtime: summed 460.15 s over 175 runs, mean 2.63 s per run, 600 steps per run.
Maximum retained simulation arrays 109.19 MB. The run uses sparse graph
operations and a bounded 5,000,000-spike recorder; no dense matrices or graph
copies are created.

## 11. Limitations

1. Ranked rules are deterministic and run once, so the surface carries no
   sampling uncertainty for those rows; only the two random rules quantify
   variability (ten draws per size).
2. Degree is a structural property of the threshold-5 graph. No biological
   meaning is assigned to in-, out- or combined degree, and their ordering is
   not a claim about signal flow.
3. The eligible pool is fixed by the Phase 4F verified-excitatory policy.
   Unverified, inhibitory and unannotated neurons are outside this surface.
   That excludes most of the graph: 683,100 of 1,535,710 edges are signed under
   the verified-only policy.
4. The JUMP null model reuses the motor spike counts from one run and tests the
   size and identity of the 20-neuron JUMP pool against random motor subsets.
   It is not an independent replication and it does not test biological
   recruitment.
5. There is one confirmatory comparison, at size 64. The rest of the surface is
   exploratory and is not corrected for multiplicity; the exploratory p-values
   are descriptive and floor at 0.0909 with ten draws.
6. The 175 runs were executed in two segments because of an analysis-only key
   error. No simulation code, seed or rule changed between segments; the
   provenance is recorded in the JSON.
7. A simulated spike, a decoder state and a JUMP window are model outputs. They
   are not measured neural activity and not a biological motor command.

## 12. Reproduction

```
python -m experiments.phase_4h.population_sensitivity
```

The runner resumes from `population_sensitivity.checkpoint.jsonl`; use
`--fresh` to discard it, and `--sizes` / `--rules` to restrict the surface. The
output is written atomically to
`experiments/results/phase_4h/population_sensitivity.json`. Focused tests:

```
python -m pytest tests/test_phase_4h_runners.py -q -p no:anyio
```
