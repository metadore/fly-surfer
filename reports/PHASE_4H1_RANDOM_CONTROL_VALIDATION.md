# FLY-SURFER — Phase 4H.1 Random Control Validation

Status: **PASS WITH LIMITATIONS**
Date: 2026-11-08
Phase: 4H.1
Parent protocol: `reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`

Phase 4H.1 asks whether the Phase 4G condition C result — 64 connectivity-ranked
verified-excitatory VNC intrinsic neurons — is distinguishable from five
families of matched random control selections. It is a statistical robustness
check on a simulated decoder output, not evidence of biological motor control.
Condition C is distinguishable from all five pre-declared control families on
both pre-registered endpoints. That statement is bounded by the families tested,
the minimum attainable p value at n = 100, and the fact that condition C was
selected on the same motor-synapse rank used here.

Artifacts:

| Artifact | Purpose |
| --- | --- |
| `experiments/phase_4h/control_draws.py` | Builds the reference, draws the five control families and writes the statistics |
| `experiments/phase_4h/common.py` | Shared world loader, candidate pools, matching diagnostics, simulator and hashing |
| `experiments/results/phase_4h/control_draws.json` | All 500 draw records, family statistics, confirmatory tests, integrity |
| `experiments/results/phase_4h/control_draws.checkpoint.jsonl` | Append-only per-draw checkpoint used for resume |
| `tests/test_phase_4h_runners.py` | Focused tests for endpoint statistics, Holm correction and family helpers |

Run:

```
python -m experiments.phase_4h.control_draws
```

Completed 2026-11-08T12:24:27Z in 1,517.27 s (25.3 min), 3.00 s per draw mean.

---

## 1. Question and design

The Phase 4G.5 result was a single deterministic run: condition C produced
1,296 spikes, 492 motor spikes, four JUMP windows and one NEUTRAL window. A
single run cannot distinguish a property of that particular 64-neuron set from
a property of the selection procedure, the motor decoder, or the stimulation
protocol.

Phase 4H.1 therefore holds the world, sign policy, weight transform, stimulation
protocol, duration, decoder and analysis fixed, and varies only **which
eligible neurons are stimulated**. The replication unit is the candidate-set
draw, not a simulation window. Because the simulator has zero background and
zero noise, two draws that select the same neurons would be bit-identical; only
distinct candidate sets carry information. All 500 candidate sets are distinct
inside and across families (§8).

The design was frozen in the parent protocol before execution. The run abort
logic checks the protocol hash at start-up.

## 2. Fixed conditions

| Item | Value |
| --- | --- |
| Graph | BANC v888, threshold 5, 172,433 nodes, 1,535,710 edges, 18,552,546 synapses, 24,320 isolated |
| Graph artifact | `datasets/processed/banc_v888/banc_graph_t5.npz`, SHA-256 `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Node table | `datasets/processed/banc_v888/banc_nodes.csv.gz`, SHA-256 `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Sign policy | verified-only; acetylcholine and glutamate excitatory, GABA and glycine inhibitory; modulators and conflicts unknown; predicted fallback off; unknown edges excluded |
| Weight transform | `min(5.0 * count^0.75, 300 pA)`, integer structural synapse count |
| Candidate size | 64 neurons |
| Stimulation | 300 pA, 50–250 ms, all 64 candidate neurons |
| Integration | dt 0.5 ms, 300 ms duration, 600 steps |
| Decoder | Phase 4F, unchanged: 50 ms windows, step 50 ms, activation 0.20, release 0.10, ≥5 spikes and ≥3 active neurons, priority LEFT/RIGHT/JUMP |
| Background / noise | 0 pA / 0 pA |
| Spike recording cap | 5,000,000 |
| Reference | Phase 4G condition C, 64 neurons, spike hash asserted equal |

The stimulus ends at 250 ms; the decoder window runs 50–300 ms and therefore
includes 50 ms after the stimulus. "Post-stimulation spikes" below means spikes
after 250 ms.

## 3. Reference reconstruction

Condition C was recomputed from the node table and graph, not copied from the
Phase 4G result file. Its selection, root IDs and spike hash were compared with
the Phase 4G record.

| Quantity | Value |
| --- | --- |
| Spike hash | `397e888ffb7f001e0509bdcfbc9121c09bafb1e2d355b555b298b5c2fed10a95` |
| Hash matches Phase 4G | yes |
| Decoded sequence | JUMP, JUMP, JUMP, JUMP, NEUTRAL |
| State sequence matches Phase 4G | yes |
| Total spikes | 1,296 |
| Stimulated / non-stimulated spikes | 740 / 556 |
| Active neurons | 164 |
| Motor spikes | 492 |
| Motor active neurons | 82 / 805 (0.1019) |
| LEFT | 176 spikes, 27 active / 185 |
| RIGHT | 155 spikes, 32 active / 186 |
| JUMP | 79 spikes, 12 active / 20 |
| Peak motor window | 140 spikes, 76 active |
| First motor spike | 68.5 ms |
| First non-neutral window | 50.0 ms |
| Post-stimulation spikes | 2 |
| Decoded windows | 4 JUMP + 1 NEUTRAL (5 windows) |

The reference candidate set has mean 1,015.4 motor synapses (SD 279.7), 100.8
in-degree (SD 37.7), 78.6 out-degree (SD 57.2), and 81.25% of neurons carry a
non-null `cell_class`. Because condition C was selected by motor-synapse rank,
these values sit at the extreme tail of every random family below. That is not
a flaw in the controls; it is the reason several families must be matched or
stratified.

## 4. Control families

Five families were pre-declared. Each draw chooses exactly 64 neurons, with no
duplicates, all verified-excitatory under the fixed sign policy, and none in
the 805-neuron motor population. Family membership was checked with the Phase
4F motor mask.

| Family | Pool | Pool size | Construction |
| --- | --- | --- | --- |
| A `vnc_intrinsic_random` | VNC intrinsic, verified-excitatory, excluding condition C | 5,558 | IID uniform draw without replacement |
| B `motor_projecting_random` | Motor-projecting eligible, verified-excitatory | 4,810 | IID uniform draw without replacement |
| C `all_verified_excitatory_random` | All verified-excitatory non-motor neurons | 53,957 | IID uniform draw without replacement |
| D `rank_stratum_shuffled` | VNC intrinsic eligible, ranks 65–256 by motor synapses, excluding condition C | 192 | IID uniform draw from the stratum immediately below the top 64 |
| E `connectivity_annotation_matched` | VNC intrinsic eligible, excluding condition C | 5,558 | Stratified draw |

Family D is a "near-miss" control: its neurons are close to condition C in
motor-synapse rank but not the selected 64.

Family E stratifies the condition C composition over four motor-synapse score
bins (quantile edges 20, 46, 85, 152) crossed with presence/absence of a
non-null `cell_class` label, and draws the same number of neurons from each
stratum. All 64 condition C neurons fall in the highest score bin: 12 without
a non-null `cell_class` and 52 with one. Family E therefore draws 12 and 52
neurons from those two cell-class strata inside the top bin. No other stratum
is required by the reference composition, and all strata had enough members:
across all 100 draws there were **no stratum shortages and no top-up neurons**.
E matches the categorical cell-class presence exactly (standardised difference
0.000) and the score bin, but samples uniformly inside the top bin; it
therefore approximates, but does not exactly match, the continuous
motor-synapse and degree distributions.

Family E is an approximation, not a matched-pairs design. It is the closest of
the five families to C, and its realised imbalance is reported rather than
hidden.

## 5. Draw generation and seeds

The draw seed is

```
seed = 20261109 + 1000 * family_ordinal + draw_index
```

with ordinals A = 1 … E = 5 and `draw_index` in 0…99. Seeds are therefore
contiguous per family:

| Family | Seed range | n |
| --- | --- | --- |
| A | 20262109 … 20262208 | 100 |
| B | 20263109 … 20263208 | 100 |
| C | 20264109 … 20264208 | 100 |
| D | 20265109 … 20265208 | 100 |
| E | 20266109 … 20266208 | 100 |

Each seed drives a single NumPy `default_rng` used only for candidate selection.
The simulation itself is unseeded in effect because noise is zero. The complete
seed list is reproduced in Appendix A and in the `seeds` array of each family
block in the JSON.

The checkpoint records every completed draw as one JSONL line. This run loaded
0 records and completed 500; resume would skip completed `(family, draw_index)`
pairs. No draw was excluded. `failures` is empty and every family records
`n_failed = 0`.

## 6. Endpoints and statistics

Two endpoints were pre-registered as confirmatory:

- **P1 — motor spikes:** total spikes in the 805-neuron motor population.
- **P2 — JUMP windows:** number of 50 ms windows decoded as JUMP.

The reference is a single deterministic value, so the comparison is between
one reference value and 100 control values per family. Report statistics:

- mean, SD, median, Q1, Q3, min, max, missing count;
- empirical percentile of the reference in the control distribution;
- one-sided empirical p = `(1 + #{control >= reference}) / (1 + n)`;
- two-sided empirical p;
- Cliff's delta with a 10,000-resample bootstrap CI;
- Hedges' g;
- reference-to-control-mean ratio with bootstrap CI;
- Holm–Bonferroni correction across the five families, separately per endpoint,
  at family-wise alpha 0.05.

All families report every endpoint, including values that are constant or
undefined. No endpoint was dropped after inspection. A null Hedges' g means
the control SD is zero (complete separation with a constant control value);
it is not silently replaced.

## 7. Results

### 7.1 Motor spikes (P1)

| Family | Mean | SD | Median | IQR | Min–max | Runs with ≥1 motor spike | Percentile | One-sided p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.08 | 0.80 | 0 | 0–0 | 0–8 | 1/100 | 1.000 | 0.009901 |
| B | 0.43 | 1.50 | 0 | 0–0 | 0–10 | 11/100 | 1.000 | 0.009901 |
| C | 0.00 | 0.00 | 0 | 0–0 | 0–0 | 0/100 | 1.000 | 0.009901 |
| D | 131.68 | 31.36 | 129 | 110.75–153.75 | 69–202 | 100/100 | 1.000 | 0.009901 |
| E | 40.54 | 16.85 | 38 | 26–51.25 | 10–92 | 100/100 | 1.000 | 0.009901 |
| Reference | 492 | — | — | — | — | — | — | — |

The reference exceeds every one of the 500 control draws. The minimum
attainable one-sided p at n = 100 is `1/101 = 0.009901`; every family reaches
it. This is complete separation on P1, not a precise estimate of how small the
tail probability is.

Effect sizes:

| Family | Cliff's delta | Delta CI | Hedges' g | Reference / control mean (CI) |
| --- | ---: | --- | ---: | --- |
| A | 1.000 | 1.000–1.000 | 614.9 | 6,150 (2,050–6,150) |
| B | 1.000 | 1.000–1.000 | 327.9 | 1,144.2 (647.4–2,894.1) |
| C | 1.000 | 1.000–1.000 | undefined (control SD 0) | undefined (control mean 0) |
| D | 1.000 | 1.000–1.000 | 11.49 | 3.736 (3.572–3.920) |
| E | 1.000 | 1.000–1.000 | 26.79 | 12.14 (11.22–13.18) |

Families D and E are the informative controls. They are not silent: D produces
a median 129 motor spikes, E a median 38. Condition C produces 492, or 3.7× D
and 12.1× E. The P1 result is therefore not "any stimulation produces motor
spikes"; it is a graded difference in how many motor spikes a candidate set
produces. Families A, B and C are near-silent at this stimulation amplitude:
no run in those families exceeded 10 motor spikes.

### 7.2 JUMP windows (P2)

No family A–D produced a single JUMP window. Family E produced **3 JUMP windows
in 2 of 100 runs** (one run with two windows, one with one); the other 98 runs
were all NEUTRAL. The reference produced 4 JUMP windows in one run.

| Family | Total JUMP windows | Runs with any JUMP | Median | Max per run | Decision states (500 windows) |
| --- | ---: | ---: | ---: | ---: | --- |
| A | 0 | 0 | 0 | 0 | 500 NEUTRAL |
| B | 0 | 0 | 0 | 0 | 500 NEUTRAL |
| C | 0 | 0 | 0 | 0 | 500 NEUTRAL |
| D | 0 | 0 | 0 | 0 | 500 NEUTRAL |
| E | 3 | 2 | 0 | 2 | 497 NEUTRAL, 3 JUMP |

Every family reaches the p floor (0.009901 one-sided; 0.019802 two-sided) for
P2 because the reference value (4) exceeds every control value (0–2). As with
P1, this establishes separation from these five families at the resolution of
100 draws; it does not establish that E-like selections cannot ever produce a
JUMP.

The E result matters for interpretation. Two of 100 annotation-matched random
draws produced a total of three JUMP windows. The reference value of four
windows is above every draw, but the per-run JUMP rate under E is 2%, not 0%.
A claim that the JUMP output is *specific* to condition C therefore needs the
4H.5 assessment to weigh this non-zero background rate; the correct statement
from 4H.1 alone is "higher than every one of 100 matched draws", not "absent
under matched random selection".

Family D is the opposite case: it produces many motor spikes (median 129) but
no JUMP window. JUMP decoding requires a narrower condition than motor
spiking — at least five spikes in the 20-neuron JUMP pool and at least three
active JUMP neurons, with a smoothed score above 0.20. High motor activity
alone did not satisfy it.

### 7.3 Secondary activity profile

These endpoints were recorded for completeness and are not part of the
confirmatory correction.

| Family | Total spikes, median (min–max) | Motor active, median (max) | Stimulated active | First motor spike, median (missing) | Post-stim spikes, median (max) | Peak motor window spikes, median |
| --- | --- | --- | --- | --- | --- | --- |
| A | 704 (704–720) | 0 (2) | 64 | 87.0 ms (99 missing) | 0 (1) | 0 |
| B | 705 (704–715) | 0 (2) | 64 | 119.5 ms (89 missing) | 0 (1) | 0 |
| C | 704 (704–706) | 0 (0) | 64 | — (100 missing) | 0 (0) | 0 |
| D | 882 (815–968) | 27 (38) | 64 | 70.75 ms (0 missing) | 1 (6) | 43 |
| E | 781.5 (727–862) | 9 (18) | 64 | 83.0 ms (0 missing) | 1 (6) | 13 |
| Reference | 1,296 | 82 | 64 | 68.5 ms | 2 | 140 |

Three observations:

1. Every draw in every family fired all 64 stimulated neurons. Stimulation
   amplitude is above rheobase for a verified-excitatory neuron, so this is a
   property of the protocol, not of a family.
2. Non-stimulated activity differs substantially: a median 704 spikes for the
   broad random families, 882 for D, 782 for E, and 1,296 for the reference.
   The reference recruits more downstream activity, not just more motor spikes.
3. D and E show late activity (post-stimulation medians 1, maxima 6) that
   A–C mostly lack. The reference has 2 post-stimulation spikes. The network
   is not quiescent immediately after the 250 ms offset.

### 7.4 Confirmatory multiple-comparison result

Holm–Bonferroni over the five families, separately per endpoint:

| Endpoint | Raw p (all five) | Holm adjusted | Rejected at 0.05 |
| --- | ---: | ---: | --- |
| P1 motor spikes | 0.009901 | 0.049505 | A, B, C, D, E |
| P2 JUMP windows | 0.009901 | 0.049505 | A, B, C, D, E |

`any_confirmatory_difference` is true. All ten family–endpoint tests reject the
null of no excess over controls. Because all raw p values are tied at the
floor, Holm ordering does not change any decision.

## 8. Family separation and overlap

| Check | Result |
| --- | --- |
| Distinct candidate sets per family | 100/100 for A, B, C, D, E |
| Shared candidate sets between any two families | 0 |
| A draws containing a condition C neuron | 0 |
| B draws containing a condition C neuron | 73/100, max 3 neurons |
| C draws containing a condition C neuron | 7/100, max 1 neuron |
| D draws containing a condition C neuron | 0 |
| E draws containing a condition C neuron | 0 |

Family B overlaps the reference more than any other family — 73% of draws
contain one to three of the 64 condition C neurons — yet no B draw produced a
JUMP window and the largest B draw produced 10 motor spikes. Sharing a few
neurons with C is not sufficient for the C result.

## 9. Realised matching quality

Standardised differences use the reference mean and SD as the standardiser;
0 means matched to C, negative means the control is lower than C.

| Family | Motor synapses | In-degree | Out-degree | Cell-class present |
| --- | ---: | ---: | ---: | ---: |
| A | −3.381 | −2.115 | −1.022 | −1.358 |
| B | −3.242 | −1.963 | −0.929 | −1.066 |
| C | −3.598 | −2.454 | −1.207 | +0.281 |
| D | −1.941 | −0.960 | −0.442 | −0.668 |
| E | −2.518 | −1.198 | −0.588 | 0.000 |

No family matches C on connectivity. E matches cell-class presence exactly and
is closest on in/out degree; D is closest on motor synapses among the
unstratified families. All families remain below C on motor synapses. The
controls are therefore not "equally matched alternatives"; the difference
between C and each family is partly a difference in connectivity, selection
rank and annotation composition. That is unavoidable when condition C is
defined by connectivity rank, and it is a limitation of causal attribution,
not of the separation test.

## 10. What 4H.1 does and does not show

Supported by this experiment:

- The condition C candidate set produces more motor spikes than every one of
  100 draws from each of five pre-declared control families.
- The condition C run produces more JUMP windows than every draw from those
  families.
- The result is not reproduced by 100 rank-stratum draws (D), which are closer
  to C in motor-synapse rank than any other unstratified family.
- The result is not reproduced by 100 annotation-matched draws (E), although
  2% of E draws produce a JUMP.

Not shown by this experiment:

- That condition C is optimal, unique, or superior to all possible 64-neuron
  sets. Only five families were tested.
- That the motor spikes or JUMP windows are biological motor commands. They are
  simulated decoder outputs under a structural, sign-prior model.
- That the p values are smaller than 0.0099. The design's resolution floor is
  1/101.
- That the reference effect is independent of the motor-synapse rank used to
  define C. The reference sits at the tail of the controls by construction.
- That the result survives changes to population size, weight transform or
  stimulation amplitude. Those are 4H.2 and 4H.3.

## 11. Integrity and reproducibility

| Item | Value |
| --- | --- |
| Protocol SHA-256 | `7c511c5a9cfb64262e424ab566743ff2b25d86e2c51a12f5a77057dd3e5e6b05` (matches frozen hash) |
| `config_sha256` | `a3d57abf1d2e3aad7f9a1fc33567b95ca62e065b6b20a7835e5e7988a51f6ebd` |
| Decoder config SHA-256 | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| Protected paths checked before / after | 37 / 37 |
| Failures | none |
| `protected_unchanged` | true |
| Checkpoint | `control_draws.checkpoint.jsonl`, 0 loaded, 500 completed this run |
| Wall time | 1,517.27 s |
| Mean draw time | 2.997 s |
| Max retained simulator memory | 109.19 MB |
| Max process working set | 247.21 MB |
| Software | Python 3.13.14, NumPy 2.3.4, pandas 2.3.3, Windows 11 10.0.26200 |

The reference spike hash is identical to the Phase 4G condition C hash, which
verifies that the control pipeline did not accidentally change the simulation.
The 37 protected paths include the Phase 4G results, graph artifacts, node
table, dataset manifests, the Phase 3 sensory pipeline and the root
`README.md`. The README was not read or rewritten by this phase.

## 12. Limitations

1. **Control families are not equally matched.** E is the closest and still
   differs on continuous connectivity; A–D differ more. A separation from a
   weakly matched control is weaker evidence than a separation from a matched
   one.
2. **The reference is an extreme by construction.** Condition C was selected on
   motor-synapse rank, and P1 is motor spikes. The test asks whether the
   selection procedure picks a candidate set that outperforms random sets; it
   does not ask whether the neurons are causally necessary.
3. **The simulator is deterministic at zero noise.** Replication comes only
   from distinct candidate sets. All 500 sets are distinct, but repeated
   identical sets would be bit-identical.
4. **No spontaneous activity.** Background and noise are zero. The comparison
   is about stimulus-evoked activity, not about signal-to-noise under a
   physiological background.
5. **Decoder output is not behaviour.** LEFT/RIGHT/JUMP labels are outputs of
   the unchanged Phase 4F decoder; they are not observed motor behaviour.
6. **The minimum p value is a floor.** With n = 100, p cannot fall below
   0.0099 one-sided. The result is "complete separation in 100 draws", not a
   precise tail estimate.
7. **Family E's 2% JUMP rate is real.** It must be carried into the 4H.5
   evidence assessment. The reference is above every E draw, but E shows that
   an annotation-matched random set can occasionally produce JUMP.

## 13. Reproduction

```
python -m experiments.phase_4h.control_draws
```

To resume after interruption, rerun the same command; completed draws are read
from `control_draws.checkpoint.jsonl`. To rebuild from scratch, move the
checkpoint aside first. The runner refuses to start if the protocol hash
differs from the frozen value.

Focused tests:

```
python -m pytest tests/test_phase_4h_runners.py -p no:anyio
```

The tests cover endpoint percentiles and empirical p values, missing-value
handling, nested matching summaries, confirmatory Holm correction and family
statistics.

---

## Appendix A — complete seed list

Seeds are listed in draw order (index 0…99) for each family. They are exactly
the sequence `20261109 + 1000*ordinal + index`.

### A_vnc_intrinsic_random
20262109, 20262110, 20262111, 20262112, 20262113, 20262114, 20262115, 20262116, 20262117, 20262118
20262119, 20262120, 20262121, 20262122, 20262123, 20262124, 20262125, 20262126, 20262127, 20262128
20262129, 20262130, 20262131, 20262132, 20262133, 20262134, 20262135, 20262136, 20262137, 20262138
20262139, 20262140, 20262141, 20262142, 20262143, 20262144, 20262145, 20262146, 20262147, 20262148
20262149, 20262150, 20262151, 20262152, 20262153, 20262154, 20262155, 20262156, 20262157, 20262158
20262159, 20262160, 20262161, 20262162, 20262163, 20262164, 20262165, 20262166, 20262167, 20262168
20262169, 20262170, 20262171, 20262172, 20262173, 20262174, 20262175, 20262176, 20262177, 20262178
20262179, 20262180, 20262181, 20262182, 20262183, 20262184, 20262185, 20262186, 20262187, 20262188
20262189, 20262190, 20262191, 20262192, 20262193, 20262194, 20262195, 20262196, 20262197, 20262198
20262199, 20262200, 20262201, 20262202, 20262203, 20262204, 20262205, 20262206, 20262207, 20262208

### B_motor_projecting_random
20263109, 20263110, 20263111, 20263112, 20263113, 20263114, 20263115, 20263116, 20263117, 20263118
20263119, 20263120, 20263121, 20263122, 20263123, 20263124, 20263125, 20263126, 20263127, 20263128
20263129, 20263130, 20263131, 20263132, 20263133, 20263134, 20263135, 20263136, 20263137, 20263138
20263139, 20263140, 20263141, 20263142, 20263143, 20263144, 20263145, 20263146, 20263147, 20263148
20263149, 20263150, 20263151, 20263152, 20263153, 20263154, 20263155, 20263156, 20263157, 20263158
20263159, 20263160, 20263161, 20263162, 20263163, 20263164, 20263165, 20263166, 20263167, 20263168
20263169, 20263170, 20263171, 20263172, 20263173, 20263174, 20263175, 20263176, 20263177, 20263178
20263179, 20263180, 20263181, 20263182, 20263183, 20263184, 20263185, 20263186, 20263187, 20263188
20263189, 20263190, 20263191, 20263192, 20263193, 20263194, 20263195, 20263196, 20263197, 20263198
20263199, 20263200, 20263201, 20263202, 20263203, 20263204, 20263205, 20263206, 20263207, 20263208

### C_all_verified_excitatory_random
20264109, 20264110, 20264111, 20264112, 20264113, 20264114, 20264115, 20264116, 20264117, 20264118
20264119, 20264120, 20264121, 20264122, 20264123, 20264124, 20264125, 20264126, 20264127, 20264128
20264129, 20264130, 20264131, 20264132, 20264133, 20264134, 20264135, 20264136, 20264137, 20264138
20264139, 20264140, 20264141, 20264142, 20264143, 20264144, 20264145, 20264146, 20264147, 20264148
20264149, 20264150, 20264151, 20264152, 20264153, 20264154, 20264155, 20264156, 20264157, 20264158
20264159, 20264160, 20264161, 20264162, 20264163, 20264164, 20264165, 20264166, 20264167, 20264168
20264169, 20264170, 20264171, 20264172, 20264173, 20264174, 20264175, 20264176, 20264177, 20264178
20264179, 20264180, 20264181, 20264182, 20264183, 20264184, 20264185, 20264186, 20264187, 20264188
20264189, 20264190, 20264191, 20264192, 20264193, 20264194, 20264195, 20264196, 20264197, 20264198
20264199, 20264200, 20264201, 20264202, 20264203, 20264204, 20264205, 20264206, 20264207, 20264208

### D_rank_stratum_shuffled
20265109, 20265110, 20265111, 20265112, 20265113, 20265114, 20265115, 20265116, 20265117, 20265118
20265119, 20265120, 20265121, 20265122, 20265123, 20265124, 20265125, 20265126, 20265127, 20265128
20265129, 20265130, 20265131, 20265132, 20265133, 20265134, 20265135, 20265136, 20265137, 20265138
20265139, 20265140, 20265141, 20265142, 20265143, 20265144, 20265145, 20265146, 20265147, 20265148
20265149, 20265150, 20265151, 20265152, 20265153, 20265154, 20265155, 20265156, 20265157, 20265158
20265159, 20265160, 20265161, 20265162, 20265163, 20265164, 20265165, 20265166, 20265167, 20265168
20265169, 20265170, 20265171, 20265172, 20265173, 20265174, 20265175, 20265176, 20265177, 20265178
20265179, 20265180, 20265181, 20265182, 20265183, 20265184, 20265185, 20265186, 20265187, 20265188
20265189, 20265190, 20265191, 20265192, 20265193, 20265194, 20265195, 20265196, 20265197, 20265198
20265199, 20265200, 20265201, 20265202, 20265203, 20265204, 20265205, 20265206, 20265207, 20265208

### E_connectivity_annotation_matched
20266109, 20266110, 20266111, 20266112, 20266113, 20266114, 20266115, 20266116, 20266117, 20266118
20266119, 20266120, 20266121, 20266122, 20266123, 20266124, 20266125, 20266126, 20266127, 20266128
20266129, 20266130, 20266131, 20266132, 20266133, 20266134, 20266135, 20266136, 20266137, 20266138
20266139, 20266140, 20266141, 20266142, 20266143, 20266144, 20266145, 20266146, 20266147, 20266148
20266149, 20266150, 20266151, 20266152, 20266153, 20266154, 20266155, 20266156, 20266157, 20266158
20266159, 20266160, 20266161, 20266162, 20266163, 20266164, 20266165, 20266166, 20266167, 20266168
20266169, 20266170, 20266171, 20266172, 20266173, 20266174, 20266175, 20266176, 20266177, 20266178
20266179, 20266180, 20266181, 20266182, 20266183, 20266184, 20266185, 20266186, 20266187, 20266188
20266189, 20266190, 20266191, 20266192, 20266193, 20266194, 20266195, 20266196, 20266197, 20266198
20266199, 20266200, 20266201, 20266202, 20266203, 20266204, 20266205, 20266206, 20266207, 20266208

