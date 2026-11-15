# P3-3C.5 — Preregistration Review Report

**Status: REVIEW OF A DRAFT — NOT AN APPROVAL, NOT A RESULT.**

This report reviews the candidate freeze in
`docs/P3_3C5_LANE_ENCODING_PREREGISTRATION_DRAFT.md` against
`docs/P3_3C5_LANE_ENCODING_DESIGN_PROPOSAL.md`
(SHA-256 `24c6d87a4ff0a151605dedbe52ead48db8f70603993038020176cb3785db4284`),
the Phase 3C design, the Phase 3 roadmap, the configuration files and the
implementation modules. It records what is accepted, what is changed and why,
what stays unresolved, and whether the experiment can validly test its stated
question. Nothing here has been executed.

**Bottom line.** *Ready for user review; not yet ready for implementation.* The
research question is answerable with the delivered encoder and simulator. The
proposal's two most important quantitative constructs — the M6 residual
distance and the 95th-percentile rule — are not valid as written, and the draft
replaces them. The replacement is sound but descriptive; it cannot produce a
significance claim, and the draft says so. Three items require a user decision
before any implementation: D1 (what "four conditions" means), D9 (the
pool-matched control) and D10 (authorisation).

---

## 1. Verdict

| Question | Verdict |
|---|---|
| Can the experiment, as re-specified, test its stated question? | **Yes**, as a descriptive, within-model question. |
| Can it test the *original* 3C.5 question ("order sensitivity of lane changes")? | **Partially.** It tests predecessor dependence at one transition, not a perceptual order code. |
| Does the proposal's M6 measure order? | **No.** It is invalid on its chosen window (§2). |
| Does the proposal's 95th-percentile rule constitute a significance test? | **No.** Six deterministic permutations cannot support it (§3). |
| Is the three-seed plan a significance argument? | **No.** It is a replication description with n = 3 (§4). |
| Are C3 and C4 "perfectly matched"? | **No.** They are matched on every controllable property except transition-type order and per-time lane, which are the order manipulation itself (§5). |
| Does the draft overclaim anywhere? | **No claim beyond a descriptive within-model history effect is made.** |
| Is the document ready to be implemented? | **No.** D1, D9, D10 and the approval checklist are open (§8). |

The single sentence the experiment can support at most is stated in draft §0
and repeated in §16: under a fixed one-hot lane encoder, a fixed 12-neuron
mapping and a deterministic LIF network, the CENTER-group spike rate in the
first 150 ms after CENTER onset differs with the immediately preceding lane in
at least two of three mapping realisations, and the difference is not explained
by current lane, dwell, transition type, total current or mapping. No
perception, learning, code or biological claim follows.

---

## 2. Primary metric: the M6 flaw

### 2.1 What the proposal proposed

M6 was a Euclidean distance between two vectors of *state residuals*, where the
residual is the measured per-lane rate minus a constant-lane baseline, computed
over time bins 4–8 (the "interior" of the sequence). The claim was that a
larger distance for the reversed pair than for the six-permutation reference
indicated order sensitivity. A 95th percentile of the six-permutation pair
distances was to serve as a threshold.

### 2.2 Why it does not measure order

1. **Different lanes, different neurons.** In C3 (`L C R L`) and C4
   (`L R C L`) the interior bins 4–8 are, respectively, in CENTER then RIGHT
   (C3) and RIGHT then CENTER (C4). The two residual vectors therefore compare
   rates supported on **different neuron groups** in the same bin. Summing
   lane-specific residuals across lanes measures lane *occupancy offset*, not
   the effect of temporal order. A large distance can arise from two lanes
   simply being measured at different times.

2. **Steady-state baseline against a transient.** The constant-lane baseline is
   a steady-state rate. The sequence residual at a block onset is a transient
   (synaptic filtering 5/8 ms, refractory 2 ms, possible recruitment). The
   residual is therefore dominated by the onset transient, whose timing moves
   between conditions. The distance between residuals then reflects *when the
   transients fall in the bin grid*, not order.

3. **Cosine on signed residuals is invalid.** Rates and residuals are signed
   relative to a baseline and sparse. Cosine is undefined for zero vectors and
   unstable for near-zero ones, and it is not an order metric in this setting.
   The proposal used it as an auxiliary; it cannot be used at all here.

4. **Time alignment.** The proposal compared the two sequences on absolute
   bins. Because the blocks sit at different absolute times (C3 CENTER at
   150 ms, C4 CENTER at 300 ms), the absolute-bin version *bakes in* the
   occupancy difference. A state-relative alignment removes it but then
   compares transients at matched times-since-onset; that is the correct
   alignment, and it was not the proposal's.

### 2.3 The replacement (M6′)

The draft defines, for the CENTER group `G_C` (four neurons) and state-relative
bin `s` after CENTER onset:

```
r_c(i,s)   = n_c(i,s) / 0.05                      # Hz, per neuron
r_c(C,s)   = (1/4) Σ_{i∈G_C} r_c(i,s)             # group mean
Δ_C(c1,c2) = (1/3) Σ_{s=0..2} [ r_c1(C,s) − r_c2(C,s) ]   # Hz
```

- **P1 = Δ_C(C1,C2)** is primary. C1 and C2 both enter CENTER at 200 ms; the
  measured window is 200–350 ms; the next transition is at 400 ms. The
  simulator is causal, so the future suffix cannot affect the window. In that
  window the two conditions differ only in the first 200 ms (LEFT vs RIGHT).
  Current lane, onset time, dwell (200 ms), transition type (adjacent), current
  (200 pA/neuron) and the four physical neurons are identical. This is the
  cleanest predecessor contrast the encoder admits.
- **P2 = Δ_C(C3,C4)** is the 150 ms-dwell replication. It is *not* the primary
  because the CENTER blocks occur at 150 vs 300 ms after different prefix
  lengths.
- **K_C** (CENTER from rest) is the auxiliary no-predecessor reference.

**Why M6′ is valid where M6 was not.** It compares the same lane, the same
neurons, the same current and the same time-since-onset; it involves no
cross-lane summation; it has no data-dependent denominator; and it is computed
from recorded spike times and known indices, so no simulator change is needed.
It is sensitive to rate magnitude (intended), insensitive to neuron identity
within a seed (same cells both sides), and reports per-neuron and per-bin
values so redistribution is not hidden. Its own limitation — a predecessor
effect is not separable from a *transition-onset* effect — is handled by `K_C`
and stated as a caveat, not removed.

**Residual weakness.** `Δ_C` is a raw rate difference in Hz, not a
standardised effect size; it is not comparable across operating points or
models. With n = 3 seeds there is no sampling distribution, so it cannot be
turned into a standardised effect size without importing an invalid noise model
(see §4). The draft reports Hz.

---

## 3. Null methodology: verdict

### 3.1 The proposal's construction is not a test

Six deterministic block permutations give 15 pairwise distances, 14 after
removing the focal pair. The 95th percentile of 14 numbers is effectively the
maximum. Beyond the count, the permutations are not exchangeable under any
null: they differ in endpoint, transition count and transition-type order.
Even with many permutations, the simulator is deterministic, so the
permutations are fixed numerical objects, not random draws; a permutation
p-value would have no meaning. Calling the resulting threshold a "95th
percentile" implies a tail probability that does not exist here.

### 3.2 What the draft uses instead

A **descriptive reference**, not a null:

1. **Predecessor-stratified reference (primary).** From the 12 closed
   sequences (150 ms blocks, multiset `{L,L,C,R}`), classify the CENTER block
   by its predecessor. Totals: predecessor LEFT 6, RIGHT 3, none 3. Excluding
   the focal C3 and C4 leaves 5 and 2. The focal values are located inside or
   outside these ranges. This is the most specific reference the design
   provides, and it is still small.
2. **Constant-lane reference** (`K_L`, `K_C`, `K_R`): steady-state and
   CENTER-from-rest onset.
3. **Single-transition reference** (six routes at 200/400 ms and six at
   150/450 ms): route characterization, route adjustment (`Δ_adj`) and a
   stationarity check.
4. **Linear reference** (six 200 ms permutations): qualitative check at a
   different dwell; only C1/C2 are onset-matched.
5. **Optional order-destroyed reference** (20 fixed frame permutations of
   `{L×6, C×3, R×3}`): secondary, not in the decision rule.

### 3.3 What the reference preserves

| Reference | Duration | Dwell | Occupancy | Transition count | Endpoint | Transition-type order |
|---|---|---|---|---|---|---|
| Linear permutations | yes | 200 ms | yes | 2 | no | no |
| Closed permutations | yes | 150 ms | yes | 3 | only C3/C4 | no |
| Single-transition | yes | pre only | no | 1 | n/a | one route |
| Constant | yes | n/a | one lane | 0 | n/a | n/a |
| Frame shuffles | yes | no | yes | no | no | no |

No reference preserves every property. This is precisely why none is called a
null and no p-value is computed. The draft also states what the reference
**cannot** do: it cannot assign a false-positive rate, a confidence interval or
a "significant" label, and it cannot substitute for replication.

**Verdict.** The null methodology is corrected: the invalid percentile test is
removed and replaced with a descriptive, stratified reference, with its
limitations stated up front. This is the correct resolution given the
deterministic simulator.

---

## 4. Three-seed rule: verdict

The proposal's three-seed plan is acceptable only as **replication
description**. The draft states:

- **What three seeds are:** three mapping realisations — different draws of
  which physical neurons form each lane group. Seed 20261104 is the delivered
  Phase 3A/3A.5 seed; 20261105/6 are P3-T4.1 draws; 20261107 is a pilot seed
  excluded from the main result.
- **What they are not:** a population, a variance estimate, a confidence
  interval, a standard error, a p-value or a robustness claim.
- **What is reported:** exact per-seed values and their range, never a
  standard deviation with n = 3.
- **What the 2-of-3 rule is:** a *descriptive* replication statement
  ("2 of 3 mapping realisations"), never "significant", "robust" or
  "confirmed".
- **Inconsistent seeds:** they are reported, not dropped. A sign change
  between seeds downgrades the outcome (e.g. `NO_HISTORY_EFFECT` or
  `INCONCLUSIVE_*`), and the exact values are shown.

A second run in a fresh subprocess for selected conditions is a **determinism
check**, not an independent sample. The draft explicitly forbids reporting
"3 seeds × 2 runs = 6 samples".

**Verdict.** Accepted with a stricter wording than the proposal. The
three-seed plan does not support any inferential statement and the draft says
so in §6, §10.2 and limitation 2.

---

## 5. C3/C4 confounds: verdict

### 5.1 What is matched

Duration and 50 ms grid (600.5 ms, 12 frames), per-block dwell (150 ms), lane
occupancy (same multiset `{L×6, C×3, R×3}`), start/end lane (L/L), transition
times (150/300/450 ms), transition count (3), per-transition current (4 off /
4 on = 800 pA), total current (800 pA every step), stimulated neurons (same 12
within a seed), background/noise (0/0), initial 0–150 ms input (L), and the
mapping.

### 5.2 What is not matched — and why it cannot be

- **Transition-direction/type order:** C3 is adjacent, adjacent, direct
  (`L→C, C→R, R→L`); C4 is direct, adjacent, adjacent (`L→R, R→C, C→L`).
- **Lane active at each time:** C3 is L, C, R, L; C4 is L, R, C, L.
- **Prior sequence at the final LEFT:** `L→C→R` vs `L→R→C`.

These are the **order manipulation itself**. With three one-hot lanes and four
blocks, no design that keeps endpoints, occupancy and transition count can also
match the per-time lane and the transition-type order while differing in
order. A claim of "perfectly matched" would be false.

### 5.3 How the design isolates order as far as the encoder permits

| Contrast | What is held fixed | What still differs | Status |
|---|---|---|---|
| P1 C1 vs C2, CENTER 200–350 ms | lane, neurons, current, onset, dwell, transition type | predecessor lane only | cleanest; primary |
| P2 C3 vs C4, CENTER | lane, neurons, current, dwell, transition type | absolute time (150 vs 300), prefix length | dwell replication; secondary |
| P3 C3 vs C4, final LEFT | lane, neurons, current, onset, absolute time | last transition route (`R→L` vs `C→L`) | longer-history; route-confounded; secondary |
| RIGHT block | lane, neurons, current | transition route (`C→R` vs `L→R`) | descriptive only |

**Verdict.** The confounds are correctly classified. The unavoidable ones are
**transition-type order** and **per-time lane**; the controllable ones (current,
dwell, onset, transition type, neurons, background, noise, initial prefix) are
all matched. The draft isolates temporal order to the extent the one-hot
encoder permits and does not claim perfect matching. It attributes a C3/C4
difference to "order" only under the stated route caveat.

---

## 6. Ten decisions: summary

Full table in draft §15. Labels: original / supported / new.

| # | Decision | Resolution | Status |
|---|---|---|---|
| D1 | Meaning of "four conditions" | C1–C4; C1/C2 literal pair; C3/C4 endpoint-matched extension; primary = C1 vs C2 at CENTER | **open** — interpretation of an original count; user must confirm |
| D2 | Closed C3/C4 extension | Accept `L→C→R→L` / `L→R→C→L` | prepared |
| D3 | Scheduler | T1 step (`transition_ms=0`) primary; crossfade 50 ms robustness for C1–C4 + six 3-transition closed sequences | prepared |
| D4 | Seeds | 20261104/5/6 main; 20261107 pilot (excluded) | prepared |
| D5 | Active features | `player_lane` only; 12 stimulated neurons | prepared |
| D6 | Controls | constants, no-input, 6 linear, 12 closed, 12 single-transition, crossfade replay; optional 20 shuffles | prepared; optional block is a user choice |
| D7 | Threshold | **Revised:** no p-value, no 95th percentile; descriptive effect size + sign + reference range | prepared |
| D8 | Pilot | Yes; 20261107; excluded; no threshold tuning | prepared |
| D9 | Pool-matched control | **Unresolved** — optional `visual_any` mapping | **open** |
| D10 | Implementation authorisation | **Unresolved** — separate task, after frozen hash | **open** |

D1 is the decision with the largest scientific consequence: the design's `4`
is an unnamed count, and reading it as "four sequence conditions" is an
interpretation, not a quotation. If the user intended something else (for
example, four repetitions or two sequences × two seeds), the protocol changes.
The draft flags this rather than manufacturing certainty.

D9 remains open because the CENTER annotation pool is 76 neurons versus 5,892
and 5,458 for LEFT and RIGHT. A `visual_any` control would address the pool
asymmetry but requires a different mapping and its own runs. It is not
necessary for the core question and is not silently added.

---

## 7. Prior evidence: what is and is not carried forward

The draft cites prior results only as **prior evidence about a different
question**, never as lane-order evidence and never as thresholds:

- P3-T7 approach vs retreat: `d′ = 0.0` for all seeds; no input gives 0
  spikes.
- P3-T4.1: four-neuron coarse three-level ordering (P4 counts 5/12/14 at
  constant 0.15/0.55/0.90; `d′ = 0.1183`) versus twelve-neuron different
  identity-code pattern (P12 51/47/47, `d′ = 0.0`; P12S 51/0/0,
  `d′ = −0.184828`); H2 separation false for all; 72 runs with 0 outside
  spikes. Its `PASS` is a **protocol** verdict, not a positive lane-order
  finding.
- P3-T2 C1 player block: 702 spikes (404 lane, 298 speed), 8/36 active, 0
  outside, peak 800 pA.
- Full 14-feature input ignites the network (P3-T2 C3, 99.976% outside).

Neither P3-T7 nor P3-T4.1 distinguished approach from retreat; neither is
reinterpreted. `d′` is explicitly **not** used for the order contrast, because
with three deterministic seeds it would be a between-condition difference over
a seed spread that is not a sampling distribution.

**Correction carried into the draft.** P3-T7's `d′` is 0.0 (as the user stated);
the non-zero `d′` values belong to P3-T4.1 (`0.1183`, `0.0`, `−0.184828`). The
draft separates the two correctly and labels P3-T4.1's `PASS` as a protocol
verdict.

---

## 8. Remaining unresolved items

1. **D1** — Confirm that "four conditions" means C1–C4 with C1/C2 primary at
   the CENTER block. If not, the design changes materially.
2. **D9** — Decide whether to add the optional `visual_any` pool-matched
   mapping. Without it, a CENTER-specific effect cannot be separated from the
   CENTER pool's size/identity; with it, the run matrix grows and the mapping
   must be re-derived.
3. **D6 (optional block)** — Include or drop the 20 frame-shuffle reference.
   It is descriptive only and not in the decision rule.
4. **D10** — Authorise a **separate** implementation task and a **separate**
   execution task; execution may not precede the frozen preregistration hash.
5. **K_C absolute-time caveat** — The auxiliary transition-onset attribution
   compares `K_C` at 0–150 ms with C1/C2 at 200–350 ms. Matched on
   time-since-onset, not absolute time. This is stated as a limitation and
   cannot be removed with the current conditions; a constant-lane run starting
   at 200 ms would need a new condition. Not proposed silently.
6. **Outside/recurrent contribution** — There is no synapse-block control in
   the interface, so direct and recurrent input cannot be causally separated.
   Outside activity is measured and reported, not subtracted. If it dominates,
   the outcome is a network-regime observation (`INCONCLUSIVE_OUTSIDE`).

None of these blocks document review. Items 1–3 block *implementation*; item 4
blocks *execution*.

---

## 9. Validity of the stated question

**Can the proposed experiment validly test its stated research question?**

**Yes, within the limits it declares.** The primary contrast compares the same
lane, same neurons, same current, same onset, same dwell and same transition
type, and differs only in the predecessor lane, inside a causally protected
window. A nonzero `Δ_C` therefore cannot be a static-lane or endpoint effect.
That is a genuine, if narrow, order/history question.

The limits are real and are stated, not hidden:

- It tests **predecessor dependence at one transition**, not biological lane
  perception, not a sequence code and not a downstream task.
- It is **within one model** (a memoryless one-hot encoder and a LIF network
  with no adaptation or plasticity); any effect comes from synaptic filtering,
  spike nonlinearity and recurrent dynamics.
- It is **descriptive**: no p-value, no significance, no population inference
  from three seeds.
- Predecessor identity is **confounded with predecessor pool** (LEFT vs RIGHT
  annotation pools, and the 76-neuron CENTER pool), which D9 would only partly
  address.
- C3/C4 are matched on everything controllable but **not** on transition-type
  order or per-time lane, which are the manipulation.

Under those limits the experiment can return a defensible positive (a
descriptive predecessor/history effect that replicates in ≥2/3 seeds and sits
outside the same-predecessor reference range in the expected direction), a
defensible negative (`NO_HISTORY_EFFECT`, reported in full), or an inconclusive
class for silence, outside domination or reference degeneracy. It cannot return
a significance claim, and the draft's outcome classes and negative-result rule
prevent a negative from being reframed as a positive.

The one substantive design weakness that remains after the revision is that the
**cleanest** contrast (C1/C2 CENTER) is available only at 200 ms dwell, and the
endpoint-matched pair (C3/C4) is weaker on absolute-time and prefix matching.
That is a property of a three-lane, four-block design, not a drafting error;
the draft says so in §1.4, §4 and limitations 6–7.

---

## 10. Integrity and execution status

- **No simulation was run.** The P3-3C.5 runner does not exist; no condition
  was executed.
- **No source code, configuration, existing result, README, or Phase 4/5/6
  artifact was modified.** This review and the draft are the only new files.
- **No file was staged, committed or pushed.** `git add .` / `git add -A` were
  not used.
- **Pre-existing tracked modifications and untracked files were preserved.**
  Nothing was deleted, reset, cleaned, stashed or overwritten.
- **Protected hashes unchanged:** `README.md`
  `8ab6a8cc2d0316653e48c0fbb1c72b22b9d27b26799dde6bc71d38cd15590563`,
  `datasets/processed/connectome.npz`
  `3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8`.
- **Draft hash:** `docs/P3_3C5_LANE_ENCODING_PREREGISTRATION_DRAFT.md`
  `3ceda5ece8017fc753a0f3aa9360a963efb58393717a89505d6efd08c3372438`
  (1,012 lines).

---

## 11. Recommendation

1. **Accept** the scientific framing of the draft: the C1/C2 CENTER contrast
   as primary, the descriptive reference in place of the percentile test, the
   three-seed replication description, and the stated limitations.
2. **Resolve D1** before implementation. It is the only decision that can
   change the protocol's meaning.
3. **Decide D9** (pool control) and the optional shuffle block; neither is
   required for a valid core experiment, but both affect cost and scope.
4. **Approve D10 in two stages:** first a separate implementation/config/test
   task, then a separate execution task after the frozen preregistration hash.
5. **Do not treat this review or the draft as approval.** The draft remains a
   draft until the §17 checklist is checked by the user.

**Verdict: READY FOR USER REVIEW; NOT YET READY FOR IMPLEMENTATION.**
