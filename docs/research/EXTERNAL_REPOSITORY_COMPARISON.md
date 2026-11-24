# External repository comparison for FLY-SURFER Phase 8

Status: research note, written 2026-11-20. Not part of the frozen Phase 8 REV4
protocol. Nothing in this document authorises a change to REV4, to the frozen
parameters, to the FAFB v783 or BANC v888 graphs, or to any existing experiment.

## Purpose and constraints

The question this document answers: **does any existing public implementation
genuinely improve Phase 8 without compromising the original experimental design?**

Working constraints, unchanged for every step that produced this audit:

- Do not modify REV4.
- Do not change frozen parameters, learning rules or thresholds.
- Do not replace FAFB/BANC with MaleCNS.
- Do not copy external code into the main repository yet.
- Do not install large dependencies or download large datasets.
- Do not run training or experimental campaigns.
- Do not perform Git operations.

This audit was performed by reading source files. The four repositories were
inspected from a working cache outside the repository
(`%LOCALAPPDATA%\Temp\flyext\`), 79 files retrieved by HTTP. No repository was
cloned into the project tree, no dependency was installed, no dataset was
downloaded, no experiment was run, and no Git command was issued.

## Method and what was and was not inspected

Files were read directly rather than summarised by an agent, so the quoted
constants below are taken from the files named beside them. The audit is
**source-level**, not execution-level: nothing here was built, imported or run.
A conclusion about runtime behaviour is therefore a conclusion about what the
code says it does, not a measurement.

Known gaps, recorded rather than papered over:

- `doomfly/doom_learning_v6/conditioning.py` returned HTTP 404 and does not
  exist at that path; 78 of the 79 requested files were retrieved.
- `male-cns-fly-brain` has **no root licence file**. Only
  `malecns/shiu_model/LICENSE` (MIT) exists, and it covers the vendored Shiu
  model, not necessarily the wrapper scripts beside it.
- No external repository was run, so none of the speed, spike-count or
  behavioural numbers quoted from their own documentation are independently
  verified here.

## The four repositories at a glance

| Repository | Stated target | Neural model | Datasets with first-class support | Licence | Relevance to Phase 8 |
|---|---|---|---|---|---|
| `tel-0s/flyverse-core` | Interactive fly-brain simulation across connectome releases | Shiu-style LIF, mV-conductance | **FAFB v783, BANC v888, MaleCNS** | MIT © 2026 tel0s | **Highest.** Only project with FAFB v783 and BANC v888 backends and a documented NT/sign policy for each. |
| `nftechie/doomfly` | Doom agent driven by MaleCNS spiking model | Shiu-style LIF (numba) | MaleCNS only | MIT © 2026 nftechie and DOOMFLY contributors | Medium. Sensory-to-action interface and knockout layout are instructive; the plasticity module is a declared LTD-only heuristic. |
| `evnsnclr/neurocraft-fly-public` | Minecraft demo of connectome-derived dynamics | Leaky-rate `tanh`, 10 ms step | MaleCNS only | MIT © 2026 Evan Smith | Medium. Its **separation of neural readouts from scripted body programs** is the clearest published statement of the boundary Phase 8 must respect. |
| `psmorph/male-cns-fly-brain` | Shiu model reproduction + escape probe | Shiu LIF, explicit Euler and Brian2 | MaleCNS only | **No root licence**; `shiu_model/` MIT © 2023 Shiu & Spiller | Medium for validation only. Its Brian2 implementation is a genuinely independent solver, but of a different parameter set. |

Only `flyverse-core` addresses the two graphs FLY-SURFER actually uses. The
other three are MaleCNS-only, and replacing FAFB/BANC with MaleCNS is explicitly
out of scope for this task.

---

## PART A — per-repository source inspection

### A.1 `tel-0s/flyverse-core`

**Licence and attribution.** `LICENSE` is "MIT License, Copyright (c) 2026
tel0s". `pyproject.toml` declares Python ≥ 3.12 and dependencies `numpy`,
`pandas`, `pyarrow`, `scipy`, `torch`, `pygame`, `imageio`, `pillow`. The
`torch` and `pygame` dependencies are for training and the interactive viewer
respectively and are not needed for the connectome backend the audit cares
about.

**Architecture.** Three-layer split: `flyverse/backends/` (dataset adapters that
emit a common pair table), `flyverse/connectome.py` (turn pairs into a signed
CSR weight matrix), `flyverse/brain.py` (simulate that matrix). This is the same
shape as FLY-SURFER's `brain/` + `motor/` split, which matters for readability
of any borrowed idea.

**Backends and dataset compatibility** (the decisive section for PART B):

- `flyverse/backends/fafb.py` reads FAFB **v783**. The declared rule is
  `NT_RULE = "nt_type when nt_type_score >= nt_threshold; photoreceptors
  histamine; no overrides"`, with threshold **5** for
  `connections_princeton.csv.gz` and threshold **1** for the
  `..._no_threshold` variant. It covers **both optic lobes and no VNC**, and
  uses a hex-column mapping for retinotopy. This is the same release and the
  same thesholding concept FLY-SURFER uses in Phase 2/3.
- `flyverse/backends/banc.py` reads BANC **v888**. The declared rule is
  `NT_RULE = "verified-first; first classical else first monoamine; unsupported
  verified NT -> unknown; photoreceptors histamine"`. It drops
  `DROP_CLASSES = ("glia", "not_a_neuron", "trachea")`, uses pair threshold
  **3**, and maps superclass/class/nerve plus motor subclasses (front/middle/
  hind leg, wing power/steering/tension, haltere steering/power) and
  proprioceptive classes (chordotonal, hair plate, campaniform). This is the
  same release FLY-SURFER loads in Phase 4, and the motor-class mapping overlaps
  FLY-SURFER's BANC motor-pool definitions.
- `flyverse/backends/common.py` holds the shared mechanics: `NT_NAMES`,
  `CLASSICAL = ("acetylcholine","gaba","glutamate","histamine")`,
  `MONOAMINES = ("dopamine","octopamine","serotonin","tyramine")`,
  `normalize_types` (exact label wins; ambiguous labels stay unresolved),
  `verified_nt` (first classical else first monoamine else unknown), `pairs()`
  (sums neuropils **before** the `min_weight` filter), and `finish()` (writes a
  manifest carrying SHA-256 of the source files). The manifest discipline is the
  same idea as FLY-SURFER's receipt files.

**Neural equations** (`flyverse/brain.py`, 998 lines):

```
dv/dt = (v_rest - v + g + I_ext) / tau_m     # v_rest = v_reset = -52 mV, v_th = -45 mV
dg/dt = -g / tau_syn                          # tau_m = 20 ms, tau_syn = 5 ms
# presynaptic spike, after 1.8 ms delay:  g_post += 0.275 mV * sign * synapse_count
# refractory 2.2 ms; exponential-Euler; dt = 0.5 ms default (Shiu/stonkfly use 0.1)
```

`LIFParams` (defaults): `v_rest -52, v_reset -52, v_th -45, tau_m 20,
tau_syn 5, t_ref 2.2, delay 1.8, w_syn 0.275, dt 0.5`, plus adaptation
(`adapt_jump 1.5`, `adapt_tau 200`), stochastic drive (`std_u 0.0`,
`std_tau 300`), fan-in normalisation (`input_norm_alpha 1.0`,
`input_norm_ref 5000.0`), `same_type_gain 0.1`, `conn_cap 60.0`, path gains,
receptor and slow-transmitter options, and `weight_dtype float32`. **These are
the Shiu et al. 2024 constants**, identical to those in `doomfly` and
`male-cns-fly-brain`.

**Weight shaping** (`_shaped_weights`), applied in this order: receptor
sign/gain on `abs(W.data)` → per-NT weight (`w_syn_by_nt`) → connection cap
(`sign * min(|W|, conn_cap)`) → path gain → type-path gain → same-type gain;
then a fan-in scale `clip((input_norm_ref / total) ** alpha, 0.02, 1.0)`; then
multiply by `w_syn`. Defaults of note:
`DEFAULT_PATH_GAIN = [(descending→vnc, 3.0), (visual_projection→descending,
2.0)]`, `DEFAULT_TYPE_PATH_GAIN = [(LC4|LPLC2→DNp01, 3.0)]`,
`DEFAULT_RECEPTOR_GAIN = {"none":1.0, "low":0.5, "mid":1.0, "high":1.5}`,
`SLOW_CLASSES = ["none","metabotropic_classical","monoamine"]`,
`DEFAULT_SLOW_GAIN_BY_CLASS = {"metabotropic_classical":0.0, "monoamine":None}`,
`DEFAULT_STD_U_BY_TYPE = {^ORN_:0.2, LN types:0.2}`,
`SLOW_THRESHOLD_MAX_FRAC = 0.9`. The **purpose** of the cap, fan-in scale and
path gains is to stop whole-graph runaway; that is the single most defensible
idea the project offers (see C.3).

**Synaptic modelling and neurotransmitters** (`flyverse/connectome.py`, 915
lines). The sign table is explicit:

```python
NT_SIGN = {"acetylcholine": +1.0,
           "gaba": -1.0, "glutamate": -1.0, "histamine": -1.0,
           "dopamine": 0.0, "octopamine": 0.0, "serotonin": 0.0,
           "tyramine": 0.0, "unknown": 0.0}
```

Plus `UNKNOWN_NT_OVERRIDE_REGEX = {r"^(lLN|v2LN|v3LN|il3LN|l2LN|vLN|LN)":
"gaba"}`, `TYPE_NT_OVERRIDE = {"TmY14":"glutamate", "Mi19":"serotonin",
"aMe8":"acetylcholine"}` (on by default), `PHOTORECEPTOR_TYPES`, `RECEPTOR_TIERS`,
`GAIN_CLASSES`, `RECEPTOR_NET_RULES = ("class","abs","nonmda")`,
`SLOW_CLASS_OF_TRANSMITTER`, a `ReceptorSigns` dataclass with `fast_factor` and
`slow_factor`, a `receptor_signs()` lookup, and `compile_connectome`, which
builds `W[post, pre] = count * sign[pre]` with `min_weight >= 1`. A BANC compile
yields a **157,789-cell** graph after exclusions. `load()`/`save()` write a
manifest and `sign0` counts.

The project's own `docs/NT_INTEGRATION.md` (684 lines) is the most candid source
document in any of the four repositories and is worth quoting precisely:

- `NT_SIGN` **silences** 2.2% of synapses (2.73M of 124.2M) originating from
  1.7% of presynaptic neurons, by reason: unknown 0.7%, dopamine 0.5%,
  octopamine 0.5%, serotonin 0.5%.
- **Glutamate is uniformly −1**, although glutamate is inhibitory only where
  the postsynaptic cell expresses GluCl; on iGluR/KaiR1D targets it is
  excitatory. The document states plainly: "this is a per-postsynaptic-type fact
  that the present scheme cannot express".
- **Monoamines are set to 0**, i.e. dropped from the fast path, rather than
  given a signed slow term.
- The receptor model decides **29.7% of edges and 25.7% of |W|**; the defaults
  `receptor_model='sign'` and `receptor_net_rule='abs'` change **0.148% of |W|**.
- The BANC transmitter predictor **over-calls dopamine** (8,072 predicted vs 584
  DA cells brain-wide; 4.4% vs 0.5% of synapses), so BANC-predicted monoamines
  are used only where verified data agrees.
- **Counts never cross releases unscaled**: synapse yield MaleCNS : FAFB : BANC
  ≈ **1 : 0.6 : 0.3**.
- FAFB v783 uses theshold nt ≥ 0.5 with photoreceptors as histamine; BANC v888
  has 65,369 verified source rows; Delta7 is verified `glutamate,serotonin` and
  PFL2 verified tyramine in BANC.
- The document closes with an explicit scope stop: **"Do not start a round 6 of
  receptor work."**

**Sensory encoding.** Retinal drive is a saturating function,
`drive_from_intensity(I, gain=30, half=0.02) = 30 * I / (0.02 + I)`, with a
per-type stochastic term (`DEFAULT_STD_U_BY_TYPE`, ORN and LN 0.2). Slow
transmitter classes can add a second, slower conductance term.

**Motor readout.** The project's separate Doom integration
(`doomfly`, below) and the interactive viewer consume named descending and motor
populations. Within `flyverse-core` itself the readout is a rate over named
populations; it is **not** a Phase-4-style action decoder.

**Plasticity.** `flyverse-core` is a forward simulator; there is no
differentiable or reward-modulated plasticity in the files inspected.

**Experimental controls.** The `docs/NT_INTEGRATION.md` work documents sign
ablations, receptor on/off and gain-tier comparisons. There is no mention of
degree-preserving randomisation or target-exchange nulls of the kind Phase 8 G3
builds.

**Tests.** The retrieved cache did not include the test tree, so test coverage
was **not** inspected and is not claimed.

### A.2 `nftechie/doomfly`

**Licence and attribution.** `LICENSE` is "MIT, Copyright (c) 2026 nftechie and
DOOMFLY contributors". `THIRD_PARTY.md` records: MaleCNS v1.0 **CC BY 4.0**
(DOI 10.1016/j.cell.2026.08.015); Huang et al. 2024 CC BY 4.0; ViZDoom 1.3.0 /
Freedoom2 **BSD-3-Clause**; and the LIF framework as Shiu et al. 2024 (MIT,
Philip Shiu & Nico Spiller, notice at `licenses/Shiu-model-MIT.txt`). The
attribution discipline is good, and it confirms the Shiu constants were
reproduced rather than re-derived.

**Architecture.** `doom/engine.py` is a **numba-compiled, all-edge LIF kernel**
operating on a CSR graph (`ptr`, `post`, `weight`, plus masks `retina`, `uv`,
`lamina`, `sugar`). `doom_learning/brain.py` is a separate plasticity layer.
`NeuralControls` converts readout rates to a joystick.

**Neural equations** (`doom/engine.py`, first 120 lines). The analytic
subthreshold update with `av = exp(-dt/20)`, `ag = exp(-dt/5)`,
`coupling = (av - ag)/3`:

```python
v[i] = -52 + (v[i] + 52) * av + drive[i] * (1 - av) + g[i] * coupling
g[i] *= ag
if v[i] > -45:            # spike
    ... 1.8 ms delay queue ...
refractory[i] = round(2.2 / dt)   # on reset
```

The kernel **refuses any `dt` other than 0.1 ms** (constructor raises
`"This audited kernel supports only dt=0.1 ms."`). It is mathematically the same
LIF as the Shiu reference, re-expressed as a closed-form exponential update and
checked out of numba. A comment documents a deliberate Brian2-compatibility
choice: "Brian2's `(unless refractory)` makes `g` read-only, including synaptic
writes. Do not save arrivals for a later release."

**Synaptic modelling and neurotransmitters.** Weights are the Shiu
`0.275 mV * sign * count` style, applied on `g`. The code carries per-cell
`retina`, `lamina` and `sugar` drive masks.

**Sensory encoding.** Retina: `drive = 30 * luminance / (0.02 + luminance)` with
a discrete low-pass (`alpha = 1 - exp(-steps*dt/10)`); lamina: a fixed tonic
bias `12.0`; sugar: a fixed `30`. The code explicitly states these are **not**
"a calibrated phototransduction or light-adaptation model".

**Motor readout** (`NeuralControls`). Docstring: "Fixed public BCI calibration;
no game state, reward, pixels or policy." Two modes, `biological` and `bci`:

```
turn    = clip((rate(DNa02,'R') - rate(DNa02,'L')) * 0.06, -6, 6)
forward = clip((rate(DNp09) - rate(MDN)) * 0.3, -20, 20)
attack  = any(MN9 spike this step)
```

with a first-order rate smoother. The comment notes the gains are "joystick
gains, not biology".

**Plasticity** (`doom_learning/brain.py`). Model `gamma1-eligibility-ltd-v1`
with declared parameters:

```
eligibility_tau_ms = 1000
eta_per_pair       = 0.001
minimum_efficacy_fraction = 0.1
dopamine_trace_tau_ms = 100
dt_ms              = 0.1
interpretation     = "Chosen phenomenological parameters, not fitted to fly
                     physiology or Doom performance. LTD-only; no consolidation,
                     recovery, extinction or prediction-error circuit."
```

`MemoryBrain` keeps per-neuron `eligibility`, `eligibility_last`, `modulation`,
`modulation_last`, per-circuit-edge `baseline_plastic`, and checkpoint
provenance hashes plus a `configuration_signature()`. This is a **per-neuron
eligibility with LTD only**, not a per-edge three-factor rule. The project's own
review document records that the base run makes **no learning claim**.

**Experimental controls.** The project ships knockout/ablation switches in its
review material; the retrieved files show analysis of no-learning baseline runs.
The learning module's provenance hashing is directly relevant to Phase 8's
identity discipline.

**Tests.** Not inspected.

### A.3 `evnsnclr/neurocraft-fly-public`

**Licence and attribution.** `LICENSE` is "MIT, Copyright (c) 2026 Evan Smith".
`THIRD_PARTY.md`: MIT project software; MaleCNS fixtures CC BY 4.0; no vendored
third-party source; `uv.lock` pins runtime deps `websockets 17.0.1` (BSD-3),
`numpy 2.2.5`, `pyarrow 21.0.0`, with a research group of matplotlib/nbformat/
nbclient/ipykernel; reference-only prior art includes
`philshiu/Drosophila_brain_model` (MIT code, data rights separate).

**Architecture.** A Python reference runtime, a controller runtime, a Minecraft
mod, and a research starter. The two modules that matter here are
`packages/neural-runtime/src/neurocraft_neural/model.py` and
`packages/controller-runtime/src/neurocraft_controller/program_policy.py`.

**Neural equations** (`model.py` and `docs/adr/0002-neural-dynamics.md`). This
project does **not** use LIF. It uses a leaky-rate recurrence:

```
z_i[n] = g_rec * Σ_j W_ij a_j[n-d_ij] + g_sens (B u[n])_i + p_i[n] + b_i
a_i[n+1] = m_i ( λ_i a_i[n] + (1 - λ_i) tanh(z_i[n]) )
W_ij = σ_ij C_ij / max(1, Σ_k C_ik)      # incoming raw-count L1 normalisation
```

`DynamicsConfig` defaults: `neural_step_ms 10.0, tau_ms 50.0, recurrent_gain 0.9,
sensory_gain 1.0, baseline 0.0, default_delay_steps 1, activation "tanh",
normalization "incoming_raw_count_l1", precision "float64",
backend "python_single_thread_reference", noise "none"`. ADR 0002's parameter
table matches: 10 ms step, 50 ms leak, 1-step delay, recurrent gain 0.9,
sensory gain 1.0, baseline 0, no noise. The decoder is
`y_k = clip(g_k Σ q_ki a_i / Σ|q_ki|, -1, 1)`.

**Synaptic modelling and neurotransmitters.** `SignOverlay`
(`coarse_presynaptic_consensus`): ACh/DA/OA/SER/TYR positive; GABA/Glu/His
negative; else 0. **Note that this differs from `flyverse`**: neurocraft makes
monoamines **positive**, whereas flyverse sets them to **0**. It also offers a
frozen `WeightOverlay` (`canonical` vs a `shuffled` permutation),
`TopologyOverlay` (directed-degree-preserving pairwise swap that preserves the
self-edge count), and `DelayOverlay` (integer 1–64).

**Sensory encoding.** `Stimulation` is a named sparse direct intervention,
documented as "never a motor command". There is no phototransduction model; the
input is an explicit engineered intervention.

**Motor readout** (`program_policy.py`). **This is the single most relevant
document in all four repositories to Phase 8's scientific framing.** Its module
docstring states: "Everything in this module is a hand-chosen engineering
mapping. It is not the fly deciding, it is not anatomy, and no constant here is
derived from any measurement of fly behaviour." The policy is a pure function of
three labelled readout scalars:

```
dna01_turn = (right - left) / (|left| + |right| + DNA01_FLOOR)   # clip [-1,1], deadband 0.10
wing_common = 0.5 * (left_motor + right_motor)
speed = SPEED_FLOOR + (1 - SPEED_FLOOR) * clip(max(0, wing_common)/SPEED_SPAN, 0, 1)
urgency = clip((ttmn_jump - ESCAPE_ON) / ESCAPE_URGENCY_SPAN, 0, 1)
```

with `ESCAPE_ON = 0.01138908104093503` (half the measured loom peak),
`ESCAPE_OFF` = half of that, `ESCAPE_HOLD_TICKS = 24`,
`ESCAPE_REFRACTORY_TICKS = 40`, `ESCAPE_URGENCY_SPAN = 0.01138908104093503`,
`DNA01_FLOOR = 1.0e-4`, `TURN_DEADBAND = 0.10`, `SPEED_FLOOR = 0.5`,
`SPEED_SPAN = 0.25`. `POLICY_VOCABULARY = (CRUISE, ESCAPE_JUMP)`; `HOVER` is the
authority's refusal fallback the policy never selects. Critically, the module
distinguishes a **declaration hash** from a behaviour hash: "`policy_hash` is a
DECLARATION hash … nothing machine-checks that `DNA01_TURN_FORMULA` describes
what `readout_values_from_step` computes." `ProgramSelectingController` wraps the
neural controller unchanged, records the raw motor projection as evidence, and
**never sends it**.

**Plasticity.** ADR 0002's "Forbidden learning" section forbids edge training,
topology edits, latent embeddings, MLP/GRU/attention, arbitrary all-neuron
readouts, imitation, reinforcement learning, and reward fitting. There is no
plasticity implementation.

**Experimental controls** (`docs/SCIENTIFIC_CLAIMS.md`). Five separate evidence
kinds (structural provenance, numerical dynamics, sensor/movement engineering,
observed behaviour, presentation). Rules directly applicable to Phase 8:

- "A failed or missed stimulus is an exclusion, not a zero neural response."
- "Weight shuffling changes counts on fixed endpoints and re-normalises incoming
  weights. It is not rewiring. One shuffle is not a null distribution."
- "No-input activity can remain zero while scripted baseline CRUISE moves the
  Minecraft body."
- 128-neuron fixture readout: raw held-out MSE 95.66× and projected MSE 403.70×
  the matched direct controller — scoped to the fixture, **not** to the full
  network or to closed-loop navigation.
- DNp01 response ≈ 300× the wing pool (a selectivity ratio); TTMn 35.1× in the
  blocked-front condition, **below** the receipt's expected 45–76× band;
  all-rays 59.7×.

**Tests.** Not inspected.

### A.4 `psmorph/male-cns-fly-brain`

**Licence and attribution.** **No root `LICENSE`.** The directory holds only
`README.md`, `brian_escape.py`, `build_brain.py`, `escape_test.py`,
`find_escape_neurons.py`, `inspect_connectome.py`, `lif_model.py`,
`requirements.txt`, `run_lif_test.py`, and `shiu_model/`.
`malecns/shiu_model/LICENSE` is "MIT, Copyright (c) 2023 Philip Shiu and Nico
Spiller". The wrapper scripts beside it are of **unclear licence**; this is the
single most important compatibility fact about this repository (see PART D).

**Architecture.** A direct reproduction of the Shiu et al. 2024 escape probe,
twice: once as a numpy explicit-Euler implementation (`lif_model.py`) and once
as a **Brian2** implementation (`shiu_model/model.py`, `brian_escape.py`).

**Neural equations** (`lif_model.py`). Shiu constants:
`V_REST = V_RESET = -52`, `V_THRESHOLD = -45`, `TAU_MEM = 20`, `TAU_SYN = 5`,
`REFRACTORY = 2.2`, `DELAY = 1.8`, `W_SYN = 0.275`, `DT = 0.5`. Explicit Euler:
`v[active] += ((V_REST - v[active] + g[active]) * DT / TAU_MEM)`; spike when
`v > V_THRESHOLD`; reset `v = V_RESET` and `g = 0`; a delay queue carries spikes;
LPLC2 Poisson drive drives DNp01 counts.

**Brian2 reference** (`shiu_model/model.py`). This is a genuinely independent
solver:

```python
eqs = '''
dv/dt = (v_0 - v + g) / t_mbr  : volt (unless refractory)
dg/dt = -g / tau               : volt (unless refractory)
'''
syn = Synapses(..., 'w : volt', on_pre='g += w', delay=t_dly)
syn.w = Excitatory * Connectivity * w_syn
# Poisson input weight = w_syn * f_poi,  f_poi = 250
```

with `v_0 = v_rst = -52`, `v_th = -45`, `t_mbr = 20`, `tau = 5`, `t_rfc = 2.2`,
`t_dly = 1.8`, `w_syn = 0.275`, `t_run = 1000 ms`, `n_run = 30`. `brian_escape.py`
uses `cpp_standalone`, 300 ms, LPLC2 rates 0/20/50/100/150 Hz,
`POISSON_SCALE = 250`, and monitors LPLC2→DNp01.

**Sensory encoding.** LPLC2 Poisson spike trains at a chosen rate.

**Motor readout.** None; the probe reports DNp01 spike counts.

**Plasticity.** None.

**Experimental controls.** Input-rate sweep, `n_run = 30` repetitions to report
spike-count distributions.

**Documented result** (`README.md`): 165,122 traced neurons, 25,563,197
connections, 124,025,046 synapses; DNp01 spikes rising 0→24/18→46/49→56/67→69/72
for LPLC2 rates 0/20/50/100/150 Hz. The README carries an explicit "Important
Scientific Note" disclaiming that this is a biological fly or consciousness.
These are the project's own reported numbers and were **not** independently
reproduced here.

---

## PART D — integration classification across all four repositories

Classes: **A** directly reusable (compatible licence and validated semantics);
**B** useful independent reference; **C** requires substantial adaptation;
**D** incompatible with architecture/datasets; **E** not scientifically
justified.

| Component | Repo | Class | Why |
|---|---|---|---|
| FAFB v783 pair/threshold/NT adapter | flyverse | **B** | Same release, same threshold concept; but it emits Shiu weights and its own sign law, so it is a cross-check, not a drop-in. |
| BANC v888 adapter with motor subclasses | flyverse | **B** | Same release and overlapping motor classes; useful to cross-check Phase 4 pool membership. |
| Cross-release synapse-yield scaling (M:F:B ≈ 1:0.6:0.3) | flyverse | **C** | Scientifically sensible, but adopting it would change BANC weights and hence frozen Phase 4–8 parameters. Reference only unless a pre-registered revision adopts it. |
| Fan-in cap + `conn_cap` + path gains (anti-runaway) | flyverse | **B/C** | The best-documented answer to whole-graph runaway; adopting the exact numbers would change frozen dynamics, so it is a reference design, not a patch. |
| Receptor sign table (`ReceptorSigns`, tiers, net rules) | flyverse | **C** | Richer than FLY-SURFER's coarse sign policy, but its own docs say it cannot express per-postsynaptic glutamate and that a "round 6" is out of scope. Adopting it changes the sign matrix that REV4 depends on. |
| Documented NT-integration accounting (% rows, % \|W\|, per-class coverage) | flyverse | **A (as a reporting pattern)** | The *discipline* — reporting how many rows and how much weight each choice silences — can be adopted in reports without touching code or parameters. |
| Manifest with source SHA-256 | flyverse | **A (as a pattern)** | Already close to FLY-SURFER's receipt discipline; no code copy needed. |
| numba all-edge LIF kernel | doomfly | **D** | MaleCNS all-edge Shiu constants; FLY-SURFER is sparse-only on FAFB/BANC with different constants. Not compatible without replacing both graph and parameters. |
| `NeuralControls` joystick mapping | doomfly | **B** | A clear, declared sensory-to-action interface; useful as a described interface, but the actual action mapping is Doom-specific and not Phase 4's decoder. |
| Declared LTD-only eligibility plasticity | doomfly | **E** | Its own parameter string says LTD-only, no consolidation/prediction-error, not fitted to physiology. Not a justified model to borrow and not the Phase 5 rule. |
| Learning-checkpoint provenance hashing | doomfly | **A (as a pattern)** | Good identity discipline for G4 checkpoints; adopt as a pattern in reports, not code. |
| Neural/scripted-body separation and declaration-hash caveat | neurocraft | **A (as a framing pattern)** | The clearest published statement of the boundary Phase 8 must keep; adopt the *wording and check* (declaration hash ≠ behaviour hash) in Phase 8 reports. |
| Five-evidence-kinds and exclusion rules | neurocraft | **A (as a reporting pattern)** | Directly matches FLY-SURFER's scientific-integrity rules; adopt as report structure. |
| Leaky-rate `tanh` dynamics | neurocraft | **D** | Different neuron model entirely; not LIF, not spiking; incompatible with Phase 2–8. |
| Degree-preserving `TopologyOverlay` idea | neurocraft | **B** | Conceptually the same family as G3 target-exchange; useful as an independent confirmation that degree-preserving nulls are standard, but G3 is already more specific. |
| Brian2 LIF solver | male-cns-fly-brain | **B** | Genuinely independent solver, but of a **different parameter set** (Shiu), so it validates LIF algebra, not FLY-SURFER's constants. See the equation comparison. |
| Shiu escape probe result table | male-cns-fly-brain | **B** | A useful external reference point for a DNp01/LPLC2 escape probe; not a validation of FLY-SURFER. |
| Root licence | male-cns-fly-brain | **D** | **No root licence.** Wrapper scripts cannot be reused; only `shiu_model/` (MIT) is clearly licensed. |

## Cross-repository observations that bear on Phase 8

1. **Nobody implements FLY-SURFER's neuron.** All four use the Shiu −52/−45 LIF
   or a leaky-rate model. FLY-SURFER's −65/−50/−68, 200 pF / 10 nS,
   current-based LIF is a different model. That is not a defect in either; it
   means **no external runtime can be dropped in without changing frozen
   parameters**, which this task forbids.
2. **The strongest transferable value is discipline, not code.** flyverse's
   NT-coverage accounting, doomfly's provenance hashing, and neurocraft's
   evidence-kinds and declaration-hash caveat are all *reporting* patterns that
   improve Phase 8's auditability without touching a single frozen number.
3. **The strongest transferable scientific idea is anti-runaway normalisation**
   (flyverse's cap + fan-in + path gains). Phase 7 already observed a
   zero-motor-spike failure; a documented normalisation rationale is worth
   recording as a reference, but adopting the numbers would violate the freeze.
4. **Glutamate sign is the one place the external projects say something
   FLY-SURFER does not fully express.** flyverse sets glutamate uniformly −1 and
   then says that is wrong for iGluR targets; FLY-SURFER's FAFB `SynapseModel`
   treats glutamate as excitatory and its BANC policy is verified-only. Both are
   coarse. Recording this explicitly is a reporting improvement, not a parameter
   change.
5. **Only one thing in these repositories is a true independent solver** —
   the Brian2 implementation — and it solves the *Shiu* equations. See
   `EXTERNAL_NEURAL_MODEL_EQUATION_COMPARISON.md` for exactly what that does and
   does not validate.

## Reflection against the project's scientific-integrity rules

- **No overclaiming.** Every "benefit" above is labelled as a reporting pattern
  or a reference design, never as a validated improvement. Nothing was run.
- **Limitations stated.** Test coverage was not inspected; `male-cns-fly-brain`
  has no root licence; one doomfly file is missing; no external number was
  reproduced.
- **Observation vs interpretation separated.** The quoted constants and counts
  are observations from source. The classifications are interpretation and are
  marked as such.
- **Existing decisions preserved.** This document changes no file inside the
  repository except itself; it does not touch REV4, the graphs, the frozen
  parameters, or Git state.

## Summary

`flyverse-core` is the only external project that speaks FLY-SURFER's two
datasets. It does not speak FLY-SURFER's neuron, and its sign/weight law differs.
Its value is as a **reference and a reporting standard**, not as a replacement
runtime. `doomfly` and `neurocraft` are valuable mainly for how they separate
neural decisions from scripted action and how they hash identity.
`male-cns-fly-brain` is the only independent solver, but of a different
equation set, and it has no root licence. None of the four should be merged into
the repository under the constraints of this task.
