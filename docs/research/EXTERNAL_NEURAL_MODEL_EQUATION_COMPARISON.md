# External neural-model equation comparison

Status: research note, written 2026-11-20. Reference-only. No runtime file, no
frozen parameter, no graph, and no learning rule is changed by this document.

## Scope

A side-by-side statement of the neuron, synapse, and sign mathematics in:

- **FLY-SURFER** (this repository): `brain/neuron_model.py`,
  `brain/synapse_model.py`, `brain/banc_synapse_policy.py`.
- **flyverse-core**: `flyverse/brain.py`, `flyverse/connectome.py`.
- **doomfly**: `doom/engine.py`, `doom_learning/brain.py`.
- **male-cns-fly-brain**: `lif_model.py` (numpy) and `shiu_model/model.py`
  (Brian2).
- **neurocraft-fly-public**: `neurocraft_neural/model.py`,
  `docs/adr/0002-neural-dynamics.md`, `program_policy.py`.

The goal is to answer two questions: where do these systems differ
mathematically, and can any of them independently validate FLY-SURFER's LIF
equations (PART C.6)?

All external values were read from source. None was executed. The Shiu constants
are recorded as published by Shiu et al. 2024, as reproduced by all three
MaleCNS-based projects.

---

## 1. The five neuron models

### 1.1 FLY-SURFER (this repository)

Current-based leaky integrate-and-fire with an exact exponential subthreshold
solve and a linear current synapse:

```
tau_m dV/dt = -(V - E_L) + R_m I(t)
V(t+dt) = E_L + (V(t) - E_L) exp(-dt/tau_m) + R_m I (1 - exp(-dt/tau_m))
V < V_min  -> V = V_min
V >= V_th  -> spike, V = V_reset, refractory
```

Parameters (`LIFParameters` defaults):

| Parameter | Value |
|---|---|
| Membrane capacitance `C_m` | 200 pF |
| Leak conductance `g_L` | 10 nS |
| Resting potential `E_L` | −65 mV |
| Threshold `V_th` | −50 mV |
| Reset `V_reset` | −68 mV |
| Floor `V_min` | −90 mV |
| Refractory | 2 ms |
| Membrane time `tau_m = C/g` | 20 ms |
| Rheobase `(V_th - E_L) g_L` | 150 pA |
| Integration | **exact** exponential (analytic) |
| Spike detection | end of step |

### 1.2 flyverse-core (and equivalent to doomfly, Shiu)

Conductance-style LIF in which the synaptic variable `g` is itself a voltage-like
quantity added to the membrane:

```
dv/dt = (v_rest - v + g + I_ext) / tau_m
dg/dt = -g / tau_syn
# on presynaptic spike after `delay`: g_post += w_syn * sign * count
v >= v_th -> spike; v = v_reset; refractory t_ref
```

Integration is **exponential-Euler** (flyverse) or a closed-form exponential
update of the same ODE (doomfly). Parameters (Shiu 2024, identical across the
three MaleCNS projects):

| Parameter | Value |
|---|---|
| `v_rest` / `v_reset` | −52 mV / −52 mV |
| `v_th` | −45 mV |
| `tau_m` | 20 ms |
| `tau_syn` | 5 ms |
| `t_ref` | 2.2 ms |
| `delay` | 1.8 ms |
| `w_syn` | 0.275 mV |
| `dt` | 0.5 ms (flyverse default); **0.1 ms only** (doomfly kernel) |

FLY-SURFER and this model share **only** `tau_m = 20 ms`. Resting, threshold,
reset, synaptic time, delay, refractory, units and integrator all differ.

### 1.3 doomfly (numba re-expression)

Same ODE as §1.2, expressed as an exact per-step update:

```python
av = exp(-dt/20);  ag = exp(-dt/5);  coupling = (av - ag)/3
v = -52 + (v + 52)*av + drive*(1-av) + g*coupling
g *= ag
```

The `coupling = (av - ag)/3` term is the analytic solution of the coupled
`(v, g)` linear system (the `1/3` is `tau_syn/(tau_m - tau_syn)`). It is
**mathematically the same neuron as flyverse's Euler step, solved exactly**, and
therefore **still not FLY-SURFER's neuron**.

### 1.4 male-cns-fly-brain — Brian2 reference

```python
dv/dt = (v_0 - v + g) / t_mbr  : volt (unless refractory)
dg/dt = -g / tau               : volt (unless refractory)
Synapses(..., 'w : volt', on_pre='g += w', delay=t_dly)
syn.w = Excitatory * Connectivity * w_syn
```

Constants identical to §1.2 (`v_0 = v_rst = -52`, `v_th = -45`, `t_mbr = 20`,
`tau = 5`, `t_rfc = 2.2`, `t_dly = 1.8`, `w_syn = 0.275`). This is an
**independent numerical solver** (Brian2's own integrator and code generation)
of the **Shiu** equations.

The numpy `lif_model.py` beside it uses **explicit Euler** on the same
equations — a second, cruder solver of the same model.

### 1.5 neurocraft-fly-public — leaky-rate, not LIF

```
z_i[n] = g_rec Σ_j W_ij a_j[n-d_ij] + g_sens (B u[n])_i + p_i[n] + b_i
a_i[n+1] = m_i ( λ_i a_i[n] + (1-λ_i) tanh(z_i[n]) )
W_ij = σ_ij C_ij / max(1, Σ_k C_ik)
```

There is no membrane potential, no spike, and no LIF ODE. `λ = exp(-10/50)`.
The state `a_i` is a dimensionless activity deviation. The output decoder is
linear: `y_k = clip(g_k Σ q_ki a_i / Σ|q_ki|, -1, 1)`.

This is a **different kind of model** and cannot be compared equation-for-
equation with a spiking neuron; it is listed for completeness and because its
normalisation (`incoming_raw_count_l1`) is the same family as the fan-in
normalisation flyverse adds.

---

## 2. Weight and synapse laws compared

| Property | FLY-SURFER | flyverse / doomfly | Shiu (Brian2) | neurocraft |
|---|---|---|---|---|
| Count → weight | `scale · count^0.75` | `w_syn · sign · count` (linear) | `w_syn · sign · count` | `σ · C_ij / max(1,Σ_k C_ik)` |
| FAFB scale | 0.55 pA | 0.275 mV | 0.275 mV | normalised (unitless) |
| BANC scale | 5.0 pA, cap 300 pA | 0.275 mV, `conn_cap 60` | n/a (MaleCNS) | normalised |
| Exponent | 0.75 (sub-linear) | 1.0 | 1.0 | 1.0 then L1-normalised |
| Synapse current form | exponential, τ_exc 5 / τ_inh 8 | exponential, τ_syn 5 | exponential, tau 5 | instantaneous rate |
| Delay | 1 ms | 1.8 ms | 1.8 ms | 1 step |
| Fan-in normalisation | none | `clip((5000/total)^1, 0.02, 1.0)` | none | L1 normalisation |
| Count source | integer `count` (`norm` never used) | summed `count` | `count` | raw `C_ij` |

**The decisive difference:** FLY-SURFER's `count^0.75` is sub-linear, which
compresses high-count (likely strong) connections relative to a linear law.
Linear law plus a cap plus fan-in scaling (flyverse) and L1 normalisation
(neurocraft) are three different ways to control the input magnitude that
FLY-SURFER deliberately does not use. FLY-SURFER's 300 pA BANC cap is the only
saturation in its law.

---

## 3. Transmitter-sign tables compared

| Transmitter | FLY-SURFER FAFB | FLY-SURFER BANC | flyverse | neurocraft |
|---|---|---|---|---|
| ACh | + | + | + | + |
| Glutamate | + | + (verified) | **−** | − |
| GABA | − | − | − | − |
| Histamine | (photoreceptor) | — | − | − |
| Dopamine | unknown→+ | unknown/excluded | 0 | **+** |
| Serotonin | unknown→+ | unknown/excluded | 0 | **+** |
| Octopamine | unknown→+ | unknown/excluded | 0 | **+** |
| Tyramine | — | — | 0 | **+** |
| Glycine | — | − (verified) | — | — |
| Unknown | + (default) / excluded (BANC) | excluded | 0 | 0 |

The three external tables **disagree with each other** on exactly the
transmitters where the data are weakest: glutamate (flyverse −, neurocraft −,
FLY-SURFER +) and monoamines (flyverse 0, neurocraft +, FLY-SURFER split).
flyverse's own `NT_INTEGRATION.md` concedes that uniformly-negative glutamate is
wrong for iGluR targets. This disagreement is the strongest single argument
*against* importing any one external sign table as authoritative: **the
projects do not agree, so none can be cited as ground truth.**

---

## 4. Plasticity compared

| Property | FLY-SURFER (Phase 5 / G4) | doomfly | neurocraft |
|---|---|---|---|
| Rule | per-edge three-factor `dw = η · δ_t · e` | per-neuron eligibility, **LTD only** | none (forbidden) |
| Eligibility | per edge, τ_e 20 ms (lazy decay) | per neuron, `eligibility_tau_ms 1000` | n/a |
| Modulation | decaying, τ 50 ms, clip ±5 | per-neuron `modulation`, τ 100 ms | n/a |
| Bounds | 0.5–2.0× initial, max Δ 5 pA | `minimum_efficacy_fraction 0.1` | n/a |
| `eta` | 0.5 (RuleConfig default 0.01; identity 0) | `eta_per_pair 0.001` | n/a |
| Sign flip | aborts (`FloatingPointError`) | not stated | n/a |
| eta=0 contract | bit-identical to fixed | n/a | n/a |
| Declared scope | `RuleConfig` defaults | "LTD-only; no consolidation, recovery, extinction or prediction-error circuit … not fitted to fly physiology" | forbidden |

doomfly's plasticity is a **different object**: per-neuron eligibility, LTD only,
declared phenomenological. It is **not** a candidate for Phase 5 or G4 and is
classified **E** (not scientifically justified as a substitute) in the
comparison table. Its *provenance-hashing* pattern, though, is a class-**A**
reporting idea.

---

## 5. PART C.6 — can the Brian2 implementation independently validate our LIF equations?

This is the most important question in the audit for scientific credibility, so
it is answered precisely and narrowly.

### What "independently validate" could mean

Three distinct claims:

1. **The LIF ODE family is solved correctly by an independent tool.**
2. **FLY-SURFER's specific parameter set produces the trajectories FLY-SURFER
   reports.**
3. **FLY-SURFER's implementation has no coding error** (indexing, ordering,
   delay, reset).

### What the Brian2 code as shipped can and cannot do

- The Brian2 model (`shiu_model/model.py`) **solves the Shiu equations**
  (`v_rest = −52`, `v_th = −45`, conductance `g`, `tau_syn = 5`, `delay = 1.8`,
  `w_syn = 0.275`). It is **not** FLY-SURFER's current-based model
  (`E_L = −65`, `V_th = −50`, `C = 200 pA`, `g_L = 10 nS`). Running it as-is
  validates claim **(1)** for the Shiu system only.
- It therefore **cannot** validate claim **(2)** or **(3)** for FLY-SURFER
  without re-parameterisation, because a correct solver of the wrong equations
  says nothing about the right equations' numbers.
- The integrators also differ: FLY-SURFER uses an **exact** analytic subthreshold
  solve; Brian2 uses its own method-of-steps integrator. So even a
  re-parameterised comparison is a comparison at a **declared numerical
  tolerance**, not a bitwise match.

### What a genuine independent validation would require

A defensible side-by-side check, **if and only if a future protocol authorises
it**, would:

1. Build a Brian2 model with **FLY-SURFER's constants** (`E_L = −65`,
   `V_th = −50`, `V_reset = −68`, `C = 200 pF`, `g_L = 10 nS`, `tau_exc = 5`,
   `tau_inh = 8`, delay 1 ms, and the **same** weight law
   `scale · count^0.75`), i.e. a *current-based* Brian2 neuron, not the Shiu
   conductance neuron.
2. Drive both implementations with the **same frozen input spike history** (or
   the same current injection) over a fixed window.
3. Compare **spike times** and **subthreshold `V(t)` at sampled times** with an
   **explicitly declared tolerance** that accounts for the integrator
   difference, and report the tolerance, the hardware, and the Brian2 version.
4. Keep the comparison **outside** the Phase 8 protocol — a verification
   artefact, not a condition.

Under this task's constraints (no installs, no downloads, no runs), even that
re-parameterised check was **not performed** and is **not claimed**.

### Verdict

**No.** As shipped, the Brian2 implementation is an independent solver of the
**Shiu** LIF family, not of FLY-SURFER's model. It is a genuine independent
solver, and it is the only such thing among the four repositories, but it
**cannot** be said to validate FLY-SURFER's equations without re-parameterisation
that this task forbids. **Classification: B (useful independent reference for a
future, separately authorised verification), with the explicit caveat that it
does not currently validate FLY-SURFER's numbers.**

---

## 6. What the equations tell us about Phase 8 specifically

- **The frozen dynamics cannot be swapped.** Every external neuron differs in
  potentials, reset, units, sign or weight law. The smallest change — adopting
  flyverse's fan-in cap — changes every BANC input and therefore every Phase 4–8
  weight and threshold. Nothing external can be dropped into REV4 without
  breaking the freeze.
- **The Phase 7 zero-motor-spike failure is consistent with an unnormalised
  current-based model.** FLY-SURFER's weight law has no fan-in normalisation;
  the three external projects all add one (flyverse cap+fan-in+path, neurocraft
  L1, Shiu none but MaleCNS is smaller). This is a plausible *diagnosis* for
  future work, **not** a licence to change the frozen model. It should be
  recorded as a hypothesis, not acted upon inside G1–G7.
- **No external sign table is ground truth.** The projects disagree with each
  other on glutamate and monoamines, which is where the data are weakest.
  Importing one would replace FLY-SURFER's declared convention with a different
  declared convention, not with evidence.
- **The only credible validation path is re-parameterised Brian2.** If Phase 8
  ever needs an independent numerical check, a *current-based* Brian2 model with
  FLY-SURFER's constants and a declared tolerance is the defensible route — and
  it is a verification artefact, not a protocol condition.

## Reflection against the project's scientific-integrity rules

- No claim of validation is made where none was performed.
- Observation (quoted equations and constants) is separated from interpretation
  (which model is "right"); the interpretation explicitly notes the projects
  disagree.
- The known limitations are stated: nothing was run; test trees were not
  inspected; the Brian2 check would require re-parameterisation that this task
  forbids.
- No existing file, parameter, learning rule, threshold, or scientific decision
  is altered.
