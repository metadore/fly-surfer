# flyverse-core compatibility audit against FLY-SURFER Phase 8

Status: research note, written 2026-11-20. Reference-only. No file in the
FLY-SURFER runtime, no frozen parameter, and no graph is changed by this
document.

## Question

Can `tel-0s/flyverse-core` serve as a reference — not a dependency — for the
parts of Phase 8 that touch FAFB v783, BANC v888, propagation and motor
recruitment, without compromising the experimental design frozen in REV4?

## Method

Source-level reading of the files in the retrieval cache. Nothing was built or
executed. Conclusions about runtime behaviour are conclusions about what the
code states, and are labelled as such. The cache did not include flyverse's
test tree, so test coverage is not assessed.

Files read:

- `flyverse/backends/fafb.py`, `flyverse/backends/banc.py`,
  `flyverse/backends/common.py`
- `flyverse/connectome.py` (915 lines)
- `flyverse/brain.py` (998 lines)
- `flyverse/docs/NT_INTEGRATION.md` (684 lines)
- `flyverse/pyproject.toml`, `flyverse/LICENSE`

Files **not** read (not retrieved): the test tree, any training code, the viewer.

---

## B.1 Dataset compatibility — FAFB v783

FLY-SURFER's Phase 2/3 pipeline loads the FAFB **v783** release. flyverse's
`backends/fafb.py` loads the same release. The comparison is therefore
release-aligned, which is the first hard requirement.

| Aspect | FLY-SURFER | flyverse-core (FAFB) | Compatible? |
|---|---|---|---|
| Release | FAFB v783 | FAFB v783 | Yes |
| Optic lobes | Yes | Yes ("both optic lobes") | Yes |
| VNC | No | No ("no VNC") | Yes |
| NT threshold | Per configured policy | 5 on `connections_princeton.csv.gz`; 1 on no-threshold variant | Partial — different theshold default |
| Photoreceptors | Histamine | Histamine | Yes |
| Retinotopy | Column mapping | Hex column mapping | Reference available |
| Output form | Signed conductance/current edges | `count * sign` CSR, Shiu weights | No — output weight law differs |
| Manifest | Receipt files | `finish()` writes SHA-256 manifest | Conceptually aligned |

**Finding.** The *pair extraction* is compatible and is the useful part. The
*weight law* that follows it is not: flyverse converts counts to Shiu
`0.275 mV * sign * count` conductances, whereas FLY-SURFER uses
`0.55 pA * count^0.75` currents. A backend import would silently change the
neuron's input scale. This is why the classification is **B**, not **A**.

## B.2 Dataset compatibility — BANC v888

FLY-SURFER's Phase 4 loads BANC **v888** and defines motor pools and a
verified-first transmitter policy. flyverse's `backends/banc.py` loads the same
release.

| Aspect | FLY-SURFER | flyverse-core (BANC) | Compatible? |
|---|---|---|---|
| Release | BANC v888 | BANC v888 | Yes |
| Dropped classes | glia / non-neuron / trachea excluded | `DROP_CLASSES = ("glia","not_a_neuron","trachea")` | Yes, same set |
| Pair threshold | Configured | 3 | Partial |
| NT rule | Verified-only; conflict/modulator→unknown; unknown edges excluded | "verified-first; first classical else first monoamine; unsupported verified NT → unknown" | **Close, not identical** |
| Motor subclasses | LEFT/RIGHT/JUMP pools from named motor neurons | front/middle/hind leg, wing power/steering/tension, haltere steering/power | Overlapping but different granularity |
| Proprioception | Not a Phase 4 pool input | chordotonal, hair plate, campaniform classes | Reference available |
| Output weight | `5.0 pA * count^0.75`, cap 300 pA | Shiu `0.275 mV * sign * count` | No |

**Finding.** The BANC **row selection** and the **motor-class vocabulary** are
directly comparable and are a useful cross-check for Phase 4 pool membership.
The **transmitter rule** is close enough to be a useful second opinion on the
verified-first policy, and its nuances are worth recording:

- flyverse's `verified_nt` returns the first **classical** else the first
  **monoamine** else unknown, and an *unsupported verified* label becomes
  unknown. FLY-SURFER's BANC policy similarly sends conflicts and
  modulator-only labels to unknown and then **excludes** unknown edges
  (`unknown_edge_policy="exclude"`).
- flyverse *silences* the resulting unknown edges too (`NT_SIGN["unknown"]=0`),
  so on this specific behaviour the two projects agree: an unverified
  transmitter does not drive the fast path.
- The difference is that flyverse additionally **drops monoamines to 0** even
  when verified, while FLY-SURFER's verified-only policy can keep a verified
  monoamine as a sign. This is a genuine semantic difference and is classified
  **C** in the comparison table.

## B.3 Equation-by-equation comparison

This is the mathematical core of the audit. FLY-SURFER values are from
`brain/neuron_model.py` and `brain/synapse_model.py` /
`brain/banc_synapse_policy.py`. flyverse values are from `brain.py` and
`connectome.py`.

### B.3.1 Membrane dynamics

| Quantity | FLY-SURFER | flyverse-core | Same? |
|---|---|---|---|
| Form | Current-based LIF, exact exponential integration | Conductance (`g`) LIF, exponential-Euler | **No** |
| Integration | Analytic subthreshold step per `dt` | `v ← v + dv/dt·dt` with Euler | **No** |
| Resting potential | −65 mV | −52 mV | **No** |
| Threshold | −50 mV | −45 mV | **No** |
| Reset | −68 mV | −52 mV | **No** |
| Refractory | 2 ms | 2.2 ms | **No** |
| Membrane time | 20 ms (`C/g`) | 20 ms | Yes |
| Synaptic time | τ_exc 5 ms / τ_inh 8 ms | τ_syn 5 ms (single) | **No** (we split by sign) |
| Delay | 1 ms | 1.8 ms | **No** |
| Drive | External current (pA) | Conductance `g` (mV) | **No** |
| Rheobase | 150 pA | n/a (conductance form) | — |

The two models are **not the same neuron**. They share a 20 ms membrane time
constant and a LIF shape, and nothing else that would let one validate the
other's absolute potentials.

### B.3.2 Synaptic weight law

| Quantity | FLY-SURFER | flyverse-core | Same? |
|---|---|---|---|
| Base form | `weight_pa = scale · count^exponent` | `w = w_syn · sign · count` (linear in count) | **No** |
| FAFB scale | 0.55 pA | 0.275 mV (`|W|` after receptor) | **No** |
| BANC scale | 5.0 pA | 0.275 mV | **No** |
| Exponent | 0.75 | 1.0 | **No** |
| Cap | BANC 300 pA | `conn_cap 60` (on `|W|`, sign re-applied) | **No** |
| Fan-in normalisation | None | `clip((5000/total)^1, 0.02, 1.0)` | **No** (flyverse normalises) |
| Path gains | None | descending→vnc 3.0, visual→descending 2.0, LC4/LPLC2→DNp01 3.0 | **No** |
| Same-type gain | None | 0.1 | **No** |
| Count source | Integer `count` only (`norm` never used) | `count` (summed across neuropils) | Yes (both use raw counts) |

**The single most important mathematical difference in the whole audit:** the
weight law. FLY-SURFER uses a **sub-linear power law** (`count^0.75`) with a
species-specific scale and a 300 pA BANC cap and **no** fan-in normalisation.
flyverse uses a **linear** count times a per-NT conductance, then applies a cap,
fan-in scaling and layered path gains. These produce different absolute inputs
and different saturation behaviour. They cannot be interchanged without changing
Phase 8's frozen dynamics.

### B.3.3 Transmitter sign policy

| Transmitter | FLY-SURFER FAFB (`SynapseModel`) | FLY-SURFER BANC (verified-only) | flyverse `NT_SIGN` |
|---|---|---|---|
| ACh | Excitatory | Excitatory | **+1** |
| Glutamate | Excitatory | Excitatory (verified) | **−1** |
| GABA | Inhibitory | Inhibitory | **−1** |
| Histamine | (photoreceptor) | — | **−1** |
| Dopamine | unknown → excitatory default | unknown / excluded | **0** |
| Serotonin | unknown → excitatory default | unknown / excluded | **0** |
| Octopamine | unknown → excitatory default | unknown / excluded | **0** |
| Tyramine | — | — | **0** |
| Glycine | — | Inhibitory (verified) | — (not in table) |
| Unknown | excitatory default (FAFB) / excluded (BANC) | excluded | **0** |

Three concrete divergences:

1. **Glutamate.** flyverse sets it uniformly **−1** and then documents, in
   `NT_INTEGRATION.md`, that this is wrong for iGluR/KaiR1D targets — "this is a
   per-postsynaptic-type fact that the present scheme cannot express".
   FLY-SURFER treats glutamate as **excitatory** in FAFB. Neither is
   receptor-resolved; they are opposite coarse conventions.
2. **Monoamines.** flyverse sets them **0** (dropped from the fast path).
   FLY-SURFER FAFB defaults them to **excitatory**, and FLY-SURFER BANC excludes
   them unless verified.
3. **Unknown.** flyverse sets **0**; FLY-SURFER FAFB defaults to **excitatory**
   and FLY-SURFER BANC **excludes**.

The flyverse document quantifies the consequence for *its* policy: 2.2% of
synapses and 1.7% of presynaptic neurons are silenced by `NT_SIGN`. It does
**not** and cannot quantify FLY-SURFER's consequence, because the policies
differ.

### B.3.4 Receptor model and slow transmitters

flyverse adds a receptor tier/gain table and an optional slow (metabotropic or
monoamine) conductance class on top of the fast sign path. This has no analogue
in FLY-SURFER. It decides **29.7% of edges / 25.7% of |W|** in its own
accounting, but its non-default receptor choices move only **0.148% of |W|**.
The project's own document closes with "Do not start a round 6 of receptor
work." **Classification: C — requires substantial adaptation, and its own authors
decline to advance it.**

### B.3.5 Dynamics-regime differences that matter for Phase 8

- **Integration error.** FLY-SURFER integrates subthreshold dynamics
  analytically (exact for the linear ODE), so its trajectories are insensitive
  to `dt` below the threshold-check resolution. flyverse and doomfly use
  exponential-Euler; their trajectories depend on `dt`. This means a cross-check
  against flyverse cannot be used to validate FLY-SURFER's integration accuracy
  — they do not share an integrator.
- **Spike detection timing.** FLY-SURFER detects spikes at the end of a step.
  flyverse's `_step_inference` clamps refractory, updates `v`, then tests
  `v >= threshold`. Equivalent in intent, different in edge-case timing.
- **Determinism.** FLY-SURFER has no unseeded randomness in the frozen
  protocol. flyverse adds optional per-type `std_u` noise (defaults 0.0 for
  most types, 0.2 for ORN/LN). Any borrowed comparison must pin `std_u = 0`.

---

## C.1 Can flyverse's FAFB/BANC loading be used as reference code?

**Yes, as a reference for row selection and class vocabulary; no, as a
drop-in loader.**

- The row-selection logic (which release files, which threshold, which classes
  to drop, how to sum neuropils before thresholding, how to resolve ambiguous
  labels) is directly comparable and is a good second opinion on FLY-SURFER's
  own loaders.
- The *output* of that logic is a Shiu-weighted CSR, not a FLY-SURFER graph.
  Adopting it would change the weight scale and thus the frozen dynamics.
- Its manifest-with-SHA-256 (`finish()`) is the same discipline FLY-SURFER
  already uses in receipts.

**Verdict: B (useful independent reference).**

## C.2 Does its synaptic modelling differ mathematically?

**Yes, at every layer:**

| Layer | FLY-SURFER | flyverse | Consequence |
|---|---|---|---|
| Count → weight | `scale·count^0.75` | `w_syn·count` | Different absolute and relative edge strengths |
| Normalisation | None | Cap + fan-in + path + same-type | flyverse saturates; FLY-SURFER does not |
| Sign | FAFB excitatory-default / BANC verified-only | Uniform table with monoamine 0 | Opposite conventions for glutamate and unknown |
| Slow term | None | Optional metabotropic/monoamine | flyverse has a second timescale FLY-SURFER lacks |
| Receptor | None | Tier/gain table | flyverse resolves some per-type signs |

None of these is a *correction* to FLY-SURFER. They are different declared
choices. flyverse's own document states the limits of its sign scheme
explicitly (glutamate per-postsynaptic-type is inexpressible; monoamines are
dropped; receptor work is stopped). So there is no mathematical result here that
FLY-SURFER is currently *getting wrong*; there are only alternative conventions.

**Verdict: the differences are real and well documented, but they are
alternative choices, not validated corrections. Classification C.**

## C.3 Does it offer a defensible improvement to propagation or motor recruitment?

**Propagation: yes, as a reference design; not as a parameter change.**

The defensible idea is flyverse's **layered anti-runaway normalisation** — a
connection cap (`conn_cap`), a fan-in scale
`clip((input_norm_ref/total)^alpha, 0.02, 1.0)`, per-path gains, and a
same-type gain. Its purpose is to keep a whole-connectome simulation from
saturating or dying, which is exactly the regime Phase 7 fell into (213/213
NO_ACTION, zero motor spikes). The rationale is well argued in `brain.py` and
`NT_INTEGRATION.md`.

But adoption would mean **changing frozen dynamics** (adding a cap, fan-in
scaling and path gains), which the task forbids and which would change every
Phase 4–8 weight and threshold. So this is a **documented answer to a real
problem that Phase 8 must not adopt under the freeze**. It becomes actionable
only if a future pre-registered protocol revision explicitly adopts a
normalisation, with its own condition labels and controls.

**Motor recruitment: limited.**

flyverse's motor vocabulary (leg/wing/haltere subclasses) is a useful
cross-check on Phase 4 pool membership, and its proprioceptive classes are a
reference FLY-SURFER does not use. But flyverse's readout is a rate over named
populations, not a Phase-4-style thresholded action decoder with
activation/release hysteresis and LEFT/RIGHT/JUMP priority. It does not offer a
better *decoder*; it offers a better *pool vocabulary*.

**Verdict: propagation — B (reference design, not adoptable under freeze);
motor recruitment — B (pool-vocabulary cross-check).**

## Cross-release synapse-yield scaling

`NT_INTEGRATION.md` states that synapse yields across releases are
MaleCNS : FAFB : BANC ≈ **1 : 0.6 : 0.3** and that "counts never cross releases
unscaled". This is a real and important observation: BANC counts and FAFB counts
are not on the same scale. FLY-SURFER already uses **different weight scales**
per graph (FAFB 0.55 pA vs BANC 5.0 pA), which is consistent with the idea that
counts differ by release, but the ratio is not something FLY-SURFER adopted
explicitly.

**Verdict: C.** Adopting the ratio would change BANC weights and hence frozen
parameters. It is worth **recording** as external corroboration that
per-release scaling is necessary — FLY-SURFER already scales per release, and
this confirms that choice was not arbitrary.

## What flyverse does NOT let us do

- It cannot validate FLY-SURFER's potentials, thresholds, or reset: different
  numbers.
- It cannot validate FLY-SURFER's integration accuracy: different integrator.
- It cannot validate FLY-SURFER's weight law: different law.
- It cannot validate FLY-SURFER's sign policy: different conventions.
- It cannot be run as a dependency under this task's constraints (no installs,
  no copying code).

## Verdict

`flyverse-core` is the **most relevant external repository** because it is the
only one with FAFB v783 and BANC v888 backends. Its value to Phase 8 is:

1. **As a reference** for FAFB/BANC row selection and motor-class vocabulary
   (class **B**).
2. **As a reporting standard** — the NT-coverage accounting (% rows, % |W|,
   per-class coverage) and the manifest discipline are patterns FLY-SURFER can
   adopt in reports without changing code or parameters (class **A as a
   pattern**).
3. **As a documented reference design** for anti-runaway normalisation, which
   names a real problem Phase 7 hit but which cannot be adopted under the freeze
   (class **B**).
4. **As external corroboration** that per-release weight scaling is necessary
   (class **C**, record-only).

It is **not** a source of validated corrections to FLY-SURFER's equations, and
it must not be merged, installed, or copied under this task's constraints.
