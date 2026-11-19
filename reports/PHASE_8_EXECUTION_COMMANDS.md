# Phase 8 execution commands and configurations (prepared, non-executable)

**Date:** 2026-11-18
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`
**Status:** every execution command in this document is **refused or unavailable** in the present
tree. Nothing here may be run as a pilot, campaign, training job or data collection until the
preconditions of section 2 are recorded.

This document separates three things that are easy to confuse:

1. commands that **exist and are safe to run now** (read-only checks and synthetic tests);
2. commands that **exist but always refuse** because the authorisation gate is closed;
3. commands and stages that **do not exist yet** and must be built before the campaign can run at all.

The third category is a readiness finding, not a command list. It is stated explicitly in section 11.

---

## 1. Tool availability matrix

| Stage | REV4 | Entry point in the tree | State | Executable now |
|---|---|---|---|---|
| Read-only conformance / memory / certificate check | — | `python -m experiments.phase_8.run_campaign check` | implemented | **yes** (reports failure, exit 1) |
| Seed derivation inspection | §6.3 | `python -m experiments.phase_8.run_campaign seeds --seed N` | implemented | **yes** |
| Certificate inspection | §10.4 | `python -m experiments.phase_8.run_campaign graphs [--seed N --verify]` | implemented | **yes** |
| Run-directory status | §8.3 | `python -m experiments.phase_8.run_campaign status <run_dir>` | implemented | yes, if a run directory exists |
| Synthetic focused tests | — | `python -m pytest tests/test_phase_8_*.py` | implemented | **yes** |
| Condition modules (A–F, controls) | §3 | `experiments/phase_8/conditions/`, `controls/` | implemented as components | only via synthetic tests |
| Campaign harness | §8 | `experiments/phase_8/runner.py::CampaignRunner` | implemented as a component | only via synthetic tests |
| Campaign factory | §3.7 | `experiments/phase_8/campaign/factory.py::CampaignFactory` | implemented as a component | only via synthetic tests |
| Dispatcher | §3.7 | `experiments/phase_8/campaign/dispatcher.py::CampaignDispatcher` | implemented as a component | only via synthetic tests |
| **Production composition root** (factory + dispatcher + runner wired to real arm runners) | §10.10 | **absent** | **not implemented** | **no** |
| **Campaign `start` / `resume`** | §10.10 | `run_campaign.py` | **refusing stub**, exits 2 | **no** (by design, and incomplete) |
| **Pilot 1 runner** | §10.3 | **absent** | **not implemented** | **no** |
| **Pilot 2 runner** | §10.8 | **absent** | **not implemented** | **no** |
| **Training orchestration CLI** (F/Fβ/E/E-full artifacts) | §10.5, §10.9 | **absent**; engine and artifact modules exist | **not implemented as a runnable stage** | **no** |
| Statistical analysis | §10.11 | `python -m experiments.phase_8.analyse_phase_8` | implemented | only on an existing store; **no store exists** |
| Information analysis | §2 (reuse `information/`) | Phase 6 CLI only; **no Phase 8 adapter** | **not implemented for Phase 8** | **no** |
| Final report / freeze | §10.12 | **absent** (manual stage) | **not implemented** | **no** |

The distinction between "component" and "stage" is the central finding: the pieces exist and are
tested, but the executable stages that compose them are not present.

---

## 2. Preconditions (all must be recorded before any execution command)

| # | Precondition | Where it is checked | Current state |
|---|---|---|---|
| P1 | REV4 approved (stage 10.0) | `campaign/protocol.py::approval_status`, `training/gate.py` | **not approved** |
| P2 | U1–U18 decisions recorded | decision register | **none recorded** |
| P3 | `design.n_seeds_selected` recorded (U7, at 10.8) | `training/gate.py::assert_design_resolved`, `registry.evaluation_plan` | **null** |
| P4 | Campaign↔training pairing recorded (B3) | `training/seeding.py::validate_pairing` | **absent** |
| P5 | Training-episode environment-seed schedule recorded (B4) | `training/engine.py` caller input | **absent** |
| P6 | Checkpoint cadence/retention/format recorded (B5) | `training/checkpoint.py` caller input | **absent** |
| P7 | RNG/optimizer restore policy recorded (B6) | checkpoint flags | **false / undecided** |
| P8 | G3 deviation resolved: accepted by record or compliant rebuild (U18 approved) | `campaign/protocol.py` deviation block | **deviation_recorded** |
| P9 | ≥ 4.0 GiB free physical memory at the immediate preflight | `config.py::memory_preflight` | **below (2.5–2.7 GiB)** |
| P10 | Production composition root and pilot runners implemented | none | **absent** |

Commands must not be run "to see what happens" while any of P1–P10 is unmet. The gates are designed
to refuse; a refusal is a correct outcome, not a signal to bypass.

---

## 3. Commands that are safe to run now

These are read-only and do not produce experimental data.

### 3.1 Conformance and resource check

```bash
cd /c/Users/Hp/fruitfly/FLY-SURFER
python -m experiments.phase_8.run_campaign --pretty check
```

Expected today:

- `conformance.checks_passed = 69`, `checks_total = 69`, `conforms = true`;
- `approval.approved = false`, `decision_status = "PROPOSED - not approved"`;
- `design_resolved = false`, `n_seeds_selected = null`;
- `certified_graphs.certified = 16`, `not_certified = 0`;
- `memory_preflight.passed = false` (below 4.0 GiB);
- `executable = false`;
- exit code **1** (inconclusive: memory gate fails; conformance passes).

This command writes nothing.

### 3.2 Seed derivation

```bash
python -m experiments.phase_8.run_campaign --pretty seeds --seed 1
```

Checks that the environment stream is shared across arms, the structure stream is shared by
C/D/C′, and the floor has no neural stream. Writes nothing.

### 3.3 Certified graph inspection

```bash
python -m experiments.phase_8.run_campaign --pretty graphs
python -m experiments.phase_8.run_campaign --pretty graphs --seed 1
python -m experiments.phase_8.run_campaign --pretty graphs --seed 1 --verify
```

`--verify` fully loads one graph and re-checks its certificate. It is a verification, not a
randomisation; it may be run when memory permits, but **do not** use it as a substitute for the
§9.3 gate, and do not run `campaign_summary` regeneration below the gate.

### 3.4 Synthetic tests

```bash
python -m pytest tests/test_phase_8_analysis.py tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py tests/test_phase_8_conventional_learner.py \
  tests/test_phase_8_live_plastic_stepper.py tests/test_phase_8_readout.py \
  tests/test_phase_8_training_artifacts.py tests/test_phase_8_training_engine.py \
  tests/test_phase_8_viability.py tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py tests/test_phase_8_random_campaign.py -q
```

Last run: **352 passed in 24.36 s**. This is synthetic verification only.

---

## 4. Pilot 1 (REV4 §10.3): A viability

### 4.1 Design

| Item | Value |
|---|---|
| Arms | A only |
| Seeds | pilot seeds 9001, 9002, 9003 |
| Episodes per seed | 3 |
| Episodes total | 9 |
| Floor | replayed on the same environment seeds, substrate-free |
| What it establishes | whether the A pipeline runs and whether the floor is present; **no contrast** |
| What it must not do | estimate C1–C4; be merged into the campaign store |

### 4.2 Command status

**Not available.** There is no pilot runner, no pilot plan builder, and no pilot result root. The
campaign `evaluation_plan` cannot express a 3-seed, A-only grid, and `CampaignRunner` requires that
plan.

### 4.3 Required interface (to be implemented at 10.3, not implemented now)

A pilot entry point must satisfy:

```
python -m experiments.phase_8.run_pilot \
    --pilot 1 \
    --arms A \
    --seeds 9001 9002 9003 \
    --episodes 3 \
    --run-id pilot1-<date> \
    --results-root experiments/results/phase_8/pilot1
```

Required behaviour:

- refuse unless P1–P10 hold (a pilot is execution);
- build an explicit `(arm, pilot_seed, episode)` plan — never reuse campaign seeds;
- write to a separate root, with `pilot: true` in the manifest;
- pass the same environment seed to A and the floor replay;
- validate every row through `schema.validate_episode_row`;
- record the free-memory preflight and the protocol/config/input hashes;
- write no campaign-store row and never merge the two stores.

Acceptance checks after the run:

1. 9 A rows and 9 floor replays, all schema-valid;
2. A rows report survival, action counts, motor spikes and floor status;
3. the report states explicitly that no C1–C4 contrast was estimated;
4. the floor is measured, not analytic;
5. the run manifest records `pilot: true` and the memory reading;
6. no campaign directory was created.

### 4.4 Acceptance evaluation

Pilot 1 does not use the U1 five-case table as a verdict, because U1 needs F and E. It reports the
A-vs-floor classification only, as the A row of the §0/U1 gate. The full U1 decision is deferred to
10.8.

---

## 5. Pilot 2 (REV4 §10.8): variability and control certification

### 5.1 Design

| Item | Value |
|---|---|
| Arms | A, B, C, F, Fβ, A′, C′ |
| Seeds | 9001, 9002, 9003 |
| Episodes per seed | 3 |
| Episodes total | 63 |
| Required outputs | paired sds for C1–C4, `σ_max`, its upper confidence limit, A′≡A and C′≡C on all 3 seeds |
| Must not do | test hypotheses, estimate campaign effects, enter the campaign store |

### 5.2 Command status

**Not available.** Same reason as pilot 1: no pilot runner, no pilot plan, and the arms require
trained? — note: pilot 2 includes F and Fβ. F/Fβ require readout training artifacts for the pilot
seeds, which requires training to be authorised and executed first. That dependency is explicit in
REV4 §10.8 and is another reason the stage cannot run today.

### 5.3 Required interface (to be implemented at 10.8)

```
python -m experiments.phase_8.run_pilot \
    --pilot 2 \
    --arms A B C F F_beta A_prime C_prime \
    --seeds 9001 9002 9003 \
    --episodes 3 \
    --training-root experiments/results/phase_8/training_pilot \
    --run-id pilot2-<date> \
    --results-root experiments/results/phase_8/pilot2
```

Required behaviour:

- train F and Fβ on the declared 20 episodes per pilot seed using **pilot training seeds disjoint
  from 9001–9003 and from the campaign training seeds**, into a pilot training root;
- build C from the certified graphs (campaign seeds do not apply; the pilot structure stream must be
  declared, and the current certificates are keyed by campaign seeds 1–16 — this is an open
  integration point that must be resolved before pilot 2 can include C);
- run A′ and C′ as exact mirrors in the same process;
- compute `σ_paired` for C1–C4 from the three seeds, then `σ_max`, and report the 80% upper
  confidence limit with its method;
- apply the U7 rule of section 6 **without choosing N on the result**;
- write `pilot: true` and never merge into the campaign store.

> **Open dependency found by this audit:** C and D use certified graphs built for campaign seeds 1–16
> (`datasets/processed/banc_v888_random/seed_N`). No certificate exists for pilot seeds 9001–9003, and
> the generator's structure stream is `[master, seed, 4]`, so a pilot pilot-seed graph would be a
> different graph. Pilot 2 cannot include C (and therefore cannot estimate `σ_C3`) using the campaign
> certificates. This must be resolved by an explicit decision before 10.8: either pilot 2 uses
> campaign seeds for its C arm (making the pilot not fully disjoint) or new pilot certificates are
> built under the §9.3 gate. This is not resolved here and is not decided by this document.

### 5.4 Acceptance evaluation

| Check | Requirement |
|---|---|
| A′ ≡ A | 19-field P1–P19 exact equality, 3/3 seeds, at eta = 0 through the real pathway |
| C′ ≡ C | same, on the same graph |
| Fβ | feature weights exactly 0; logits identical on zero vs 1e6 features |
| σ | `σ_max` reported with point estimate and upper confidence limit |
| N decision | recorded before any campaign outcome; N = 16 unless the 112.87 bound is defended |
| Separation | pilot rows live in `pilot2`, never in the campaign store |
| No hypotheses | the report contains no p-value for C1–C4 |

---

## 6. N decision (U7) at 10.8

The rule is REV4 §7.1, restated exactly:

```
σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4)
N = 10 only if 2.8016 · σ_max / √10 ≤ 100  ⇔  σ_max ≤ 112.87
and only if the upper confidence limit supports that bound.
Otherwise N = 16, or no campaign.
```

Recommended record (advisory, not applied): **N = 16** unless the upper limit is ≤ 112.87. With a
3-seed pilot (df = 2, 80% upper limit ≈ 2.1× the point estimate), N = 10 requires a point estimate of
roughly ≤ 53.7. Do not select N = 10 from the point estimate alone.

When the value is recorded, the configuration change is exactly:

```yaml
# configs/phase_8/campaign.yaml (do not edit until the record exists)
design:
  n_seeds_selected: 16   # or 10, only on the predeclared condition
```

and the conformance check in `campaign/protocol.py` (which currently requires `null`) must be updated
in the same change. The analysis already accepts either value.

---

## 7. Training stages (10.5, 10.9)

### 7.1 Commands

**Not available.** There is no training CLI and `training/gate.py::assert_training_authorized` always
raises. The engine, checkpoint, artifact and validation modules exist and are tested synthetically.

### 7.2 Required interface (to be implemented at 10.5/10.9)

```
python -m experiments.phase_8.train_artifacts \
    --conditions F F_beta E E_full \
    --pairing experiments/results/phase_8/training_pairing.json \
    --environment-seeds <declared training schedule> \
    --checkpoint-every 1 \
    --checkpoint-root experiments/results/phase_8/training/checkpoints/<run-id> \
    --run-id training-<date>
```

Required behaviour:

- read the explicit pairing (B3) and refuse a partial map;
- derive init from the training seed's learning stream, never the campaign seed;
- use the declared budgets: 20 episodes for F/Fβ, 2,000 gradient updates for E/E-full;
- checkpoint at the declared cadence, retaining the declared set;
- write `origin = "trained"` artifacts under `experiments/results/phase_8/training` only;
- refuse overwrite; record config hash, state digest, trainable digest, seeds and resume flags;
- for Fβ, keep feature weights exactly 0 and verify it after reload;
- for F and Fβ at the same campaign seed, share the training seed and write a matching pair.

Acceptance checks:

1. every artifact reloads through `training/loader.py` and passes `assert_condition_compatibility`;
2. F/Fβ pair check passes;
3. no campaign seed equals a training seed;
4. no initialized-only model is presented as trained;
5. the run manifest records the resume policy and checkpoint layout.

### 7.3 Budgets and stopping

| Stage | Budget | Stop |
|---|---|---|
| F, Fβ | 20 episodes per seed | fixed episode count |
| E, E-full | 2,000 gradient updates | update budget; safety episode bound refuses rather than truncates |
| Evaluation | K = 10 episodes per seed | fixed count |
| Episode | 900 game updates | game termination or cap |

No early stopping, no validation-based model selection, no checkpoint chosen by performance.

---

## 8. Confirmatory campaign (10.10)

### 8.1 Current command and behaviour

```bash
python -m experiments.phase_8.run_campaign --pretty start --run-id campaign-<date>
```

**This always refuses** with exit code **2** and `executed: false`, `episodes_run: 0`,
`rows_written: 0`. The refusal payload records approval, conformance, memory, certificates and the
requested run id. This is the correct behaviour today.

`resume` behaves the same:

```bash
python -m experiments.phase_8.run_campaign --pretty resume <run_dir>
```

### 8.2 What must be true before `start` can execute

1. P1–P10 (section 2).
2. A production composition root that:
   - loads the real `CampaignFactory` with the real world, certified graphs and trained artifacts;
   - builds `CampaignDispatcher` with the real per-arm runners from `conditions/` and `controls/`;
   - passes it to `CampaignRunner.start` with the real memory preflight, input hashes, environment
     capture and integrity baseline;
   - refuses if any trained artifact is missing (the factory already does).
3. A campaign configuration with `n_seeds_selected` recorded and a recorded pairing.
4. A preflight that measures ≥ 4.0 GiB **immediately before start** and records it.

The composition root does not exist in the tree. Until it does, `start` cannot be made to run by
recording an approval; the stub must be replaced by a stage that constructs the above. This is a
required implementation step, not a configuration choice.

### 8.3 Intended invocation after implementation

```bash
# preflight (read-only)
python -m experiments.phase_8.run_campaign --pretty check

# start (only after P1-P10)
python -m experiments.phase_8.run_campaign --pretty start --run-id campaign-2026xxxx

# after an interruption (same configuration; drift is refused)
python -m experiments.phase_8.run_campaign --pretty resume \
  experiments/results/phase_8/campaign-2026xxxx

# read-only status
python -m experiments.phase_8.run_campaign --pretty status \
  experiments/results/phase_8/campaign-2026xxxx
```

Expected plan size:

| N | Arms | K | Episodes |
|---|---|---|---|
| 16 | 12 | 10 | 1,920 |
| 10 | 12 | 10 | 1,200 |

(The 12 arms include the four controls, E-full and the floor. The six conditions and the confirmatory
family are unchanged.)

### 8.4 Campaign acceptance (first two seeds)

REV4 §10.10 requires two seeds complete with all artifacts valid before the rest is trusted. Check:

- every arm present for both seeds;
- A′/C′ identity reports present and exact for every completed seed;
- all rows schema-valid and no duplicate key;
- the manifest records ≥ 4.0 GiB at start;
- the run manifest records the G3 deviation if the certified set is used;
- no silent retry or row substitution.

---

## 9. Statistical analysis (10.11)

### 9.1 Command

The CLI exists and can analyse an existing store. It does not create a store and does not run
episodes.

```bash
python -m experiments.phase_8.analyse_phase_8 \
  --store experiments/results/phase_8/campaign-2026xxxx/episodes.jsonl \
  --output experiments/results/phase_8/campaign-2026xxxx/analysis.json \
  --family-size 4 \
  --n-seeds 16 \
  --sigma <pilot σ_max>
```

Rules:

- `--family-size` is the recorded U14 decision (4 or 3); it has no default and must match the
  approved register.
- `--n-seeds` is the design N actually run, not the planned N; the analysis recomputes at the actual
  complete-pair N and withholds Holm below the predeclared floor.
- `--sigma` **must be supplied from the pilot**; the default 60.0 is a placeholder for the MDE table
  and must not be used silently. If the pilot's σ_max is recorded, pass that value and record it in
  the analysis output.
- The analysis refuses to overwrite an existing output unless `--overwrite` is supplied. Do not use
  `--overwrite` to replace a published analysis; write a new file and record the reason.
- `--replay-store` is used only for the E5 fresh-process replay comparison.

Expected outputs: exact sign-flip p at the actual N, sign test, Holm at m = 4/3, effect sizes
(mean difference, Cohen's dz), identity reports, floor decomposition, F/Fβ/A decomposition, E1–E5
checklist, design summary, warnings, missingness. No number may be typed by hand.

Acceptance: the output reproduces every §7 number from the JSONL; thresholds are recomputed at the
actual N; zero and missing pairs follow the declared rules; an identity failure marks B and D INVALID.

### 9.2 Current status

No campaign store exists, so the command has nothing to analyse. It is safe to run on a synthetic
fixture in tests; that is not an analysis of experimental data.

---

## 10. Information analysis and final reporting (10.11/10.12)

### 10.1 Information analysis

REV4 §2 lists "information analysis" as a **read-only reuse of `information/`** and states it is
descriptive only; it cannot upgrade the Phase 6 result. The Phase 6 entry point exists:

```bash
python -m experiments.phase_6.run_information_analysis [--quick] [--no-figures]
```

but it is wired to the **Phase 6** artifact configuration and output directory. **No Phase 8 adapter
exists**, and no Phase 8 command consumes `information/`. Therefore:

- there is no exact Phase 8 information-analysis command to give;
- the Phase 6 command must **not** be repurposed or pointed at Phase 8 stores by editing its config
  in place, because that would mix phases and overwrite Phase 6 outputs;
- the required stage is a new read-only adapter that maps Phase 8 episode fields to the declared
  information endpoints, writes under the Phase 8 results root, and reports the Phase 6 negative
  result unchanged.

This is a readiness gap. It is descriptive, so it does not block the confirmatory contrasts, but it is
part of REV4 §10.11 and must be implemented or explicitly deferred by the user.

### 10.2 Final report and freeze

No report generator exists. Stage 10.12 is manual and must produce:

- `reports/PHASE_8_RESULTS.md` and `.json`;
- a freeze record with the analysis hash and the protocol hash;
- the integrity check (36/37 non-README, as declared);
- every §11 limitation restated;
- no §3.6.5 forbidden statement (no "the connectome solves the game", no "plasticity causes
  improvement" without the contrast, no reward-based claim);
- the readout claim **only** if E1–E5 all pass;
- the Phase 6 result unchanged;
- the G3 deviation and any resume limitation recorded.

The commands for these are the analysis command above plus manual document preparation; there is no
script that writes the report.

---

## 11. Findings: stages that cannot be commanded today

| Stage | What is missing | Consequence |
|---|---|---|
| Pilot 1 (10.3) | pilot plan + pilot runner + pilot result root | A viability cannot be measured |
| Pilot 2 (10.8) | pilot plan + runner + pilot training artifacts + a decision on pilot-seed graphs for C | σ_max and the N decision cannot be produced |
| Training artifacts (10.5, 10.9) | training CLI/orchestration; the engine exists but the gate always raises | F/Fβ/E artifacts cannot exist, so F/Fβ/E cannot be evaluated |
| Campaign (10.10) | production composition root; `start` is a refusing stub | even with approvals and memory, the campaign cannot execute |
| Information analysis (10.11) | Phase 8 adapter over `information/` | descriptive endpoint missing |
| Report/freeze (10.12) | generator (manual stage) | reporting is procedural, not automated |
| G3 (10.4) | compliant rebuild or recorded deviation (user decision) | campaign inherits the deviation |
| Resource gate | machine below 4 GiB | nothing may start |

These are **not** commands to run; they are implementation and decision work that must precede any
command. The brief's restriction against building more infrastructure unnecessarily does not make
them disappear: they are the remaining work of the original Phase 8 plan.

---

## 12. Command traceability

| Stage | Today | After approvals and implementation |
|---|---|---|
| 10.0 approval | no command | record in the decision register / freeze record |
| 10.1 skeleton | tested synthetically | unchanged |
| 10.2 A | condition module only | pilot runner needed |
| 10.3 pilot 1 | **absent** | `run_pilot --pilot 1 …` |
| 10.4 C | certified graphs; deviation recorded | resolution decision |
| 10.5 F/Fβ | components + refusals | training CLI needed |
| 10.6 A′/C′ | components | available through the runner |
| 10.7 B/D | components | available through the runner |
| 10.8 pilot 2 | **absent** | `run_pilot --pilot 2 …` |
| 10.9 E/E-full | components + refusals | training CLI needed |
| 10.10 campaign | **refusing stub** | composition root + `start` |
| 10.11 analysis | `analyse_phase_8` exists | usable on a store |
| 10.11 information | **no Phase 8 adapter** | new adapter |
| 10.12 report | **no generator** | manual + freeze record |
| 10.13 viability | `evaluation/viability.py` | usable on a pilot/campaign store |

---

## 13. Prohibited in the present state

- Do not run `start` or `resume` expecting execution; they exit 2 by design.
- Do not bypass `assert_campaign_authorized`, `assert_training_authorized` or
  `assert_design_resolved`.
- Do not set `n_seeds_selected` to make a stage run.
- Do not run a pilot, training job, game episode or campaign to "test the command".
- Do not use the Phase 6 information CLI on Phase 8 data.
- Do not regenerate graphs while free memory is below 4 GiB.
- Do not overwrite the certified graph namespaces, the Phase 6 outputs or any existing analysis.
- Do not treat a synthetic test as an experimental observation.

The only commands that may be run now are those in section 3.
