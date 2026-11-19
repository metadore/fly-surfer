# Phase 8 G5 — campaign runner assembly

**Date:** 2026-11-17
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`
**Status:** G5 is **assembled as a mechanism and tested synthetically**. No campaign may start:
REV4 §12 is not approved (U1–U18 remain `PROPOSED — not approved`) and the G3 §9.3 memory-gate
deviation is unresolved.

---

## 1. What this report claims

| Claim | Evidence |
|---|---|
| A BANC-scale component factory exists and is exercised on synthetic stubs | `experiments/phase_8/campaign/factory.py` (662 lines); factory tests in `tests/test_phase_8_campaign_runner.py` |
| An episode-runner interface connects the arms to `CampaignRunner` | `campaign/dispatcher.py` (377 lines); dispatcher and harness-integration tests |
| All twelve declared arms route to their existing implementations | registry plus `ARM_RUNNERS`; per-arm tests |
| C, D and C′ load only certified graphs, with no biological fallback | `campaign/graphs.py` (283 lines); eight refusal tests |
| A campaign CLI exists and can never start a campaign | `experiments/phase_8/run_campaign.py` (396 lines); `start`/`resume` tests |
| Configuration is validated against REV4 | `campaign/protocol.py`; 69 declared-constant checks, 69/69 pass |
| Resume, failure logging, torn-store detection and status reporting work | `campaign/status.py` (167 lines) plus dispatcher failure tests |
| No episode, pilot, training run or campaign was executed | recorded here and in `PHASE_8_IMPLEMENTATION_STATUS.md` §10 |

What this report does **not** claim: that a Phase 8 episode has run on the BANC substrate, that any
arm is scientifically valid, that the 16 certified graphs are protocol-compliant, or that G3 is
complete. Every test behind the G5 claims uses a stub factory, stub arm runners, a 2-node graph
fixture or a temporary certified-graph namespace. Synthetic tests are infrastructure evidence,
not experimental evidence.

---

## 2. Files

| File | Lines | SHA-256 |
|---|---|---|
| `experiments/phase_8/campaign/factory.py` | 662 | `984136c537b0431e600a47a6890433d6d24cd85417a2e4668b551cc64d58cb66` |
| `experiments/phase_8/campaign/dispatcher.py` | 377 | `76408e8c702b28694b7e5c096543789a376f5a994f1455df8d82fbe812f60656` |
| `experiments/phase_8/campaign/graphs.py` | 283 | `dbb8072e4c36ac6037325430bc3c4df076a6df11681cd51f4cd908f23fe42567` |
| `experiments/phase_8/campaign/protocol.py` | 554 | `fb22725689dc26bb98af7082dd95fb51dbf2f510c1bbf39d44881456e830df6e` |
| `experiments/phase_8/campaign/status.py` | 167 | `7fcf18e50fa8664156ae22b474fb51bb449fff0571021e5c338b514394000fcc` |
| `experiments/phase_8/campaign/__init__.py` | 52 | `35cec6c7abbe8f3ba451cc66b7f04ef33b8264d5addc4016e00d323c636f2f13` |
| `experiments/phase_8/run_campaign.py` | 396 | `5e672d6a911780084f7d052763b1cc8117abc43eb3743e2e59134705df7f2ff8` |
| `experiments/phase_8/runner.py` (modified) | — | `fe3603ac991d8e550669be2c2ac3f1904972660f176d73e20c198f4cf1212beb` |
| `experiments/phase_8/conditions/base.py` (modified) | — | — |
| `tests/test_phase_8_campaign_runner.py` | 902 | `77853f62c6a83b6bfd02b1a65fbf649b7c01f45fc28280a4b611275fdff3bf13` |

`campaign/` is new in this task. `runner.py` changed in one place (§6). `conditions/base.py` gained
the certificate re-verification hook (§5). All other condition, control, environment, readout,
evaluation and `experiments/phase_8_random/` code was left as it was.

---

## 3. Component factory (`campaign/factory.py`)

`CampaignFactory` builds one episode's components from the frozen artifacts. It adds no mechanism:
it assembles `LiveBancStepper`/`LivePlasticStepper`, the sensory drive, `GameEnvironmentAdapter`,
`GameActionDecoder`, `LinearReadout`/`BiasOnlyReadout` and the conventional agent that already
exist.

- `FactorySettings` holds only declared implementation constants (neural `dt` 0.5 ms, game `dt`
  1/60 s, 50 ms decoder window, 25 m distance horizon, 900-update cap). None is tuned.
- `neural_components(arm, …)` builds a fresh substrate, populations, adapter, stepper and decoder
  per episode. Arm-specific behaviour comes from the existing `conditions`/`controls` modules:
  A fixed, B plastic at η = 0.5, C on the certified graph, D certified + plastic, F readout,
  A′/C′ through the zero hook, Fβ bias-only, F-init seeded initial parameters.
- `conventional_components(arm, seed=…)` builds the E/E-full learner; `floor_adapter()` builds the
  adapter-only floor path.
- `TrainingArtifacts` is a caller-supplied provider. F, Fβ and E need trained artifacts; without a
  provider the factory raises `FactoryError` rather than evaluating an untrained model. The factory
  has no training code path.
- `input_hashes()` hashes the seven declared frozen inputs once; a missing file is an error and an
  empty hash set is not accepted. Rows carry the digests.
- `assert_environment(config)` rejects a mismatched `max_steps`, `distance_horizon` or game `dt`.

Every heavy object is rebuilt per episode so no membrane state, trace, readout weight or game
state leaks between episodes.

---

## 4. Episode-runner interface and dispatch (`campaign/dispatcher.py`)

`CampaignRunner` (unchanged) executes a plan of `(condition, seed, episode)` with an injected
`episode_runner`. `CampaignDispatcher` is that runner:

```
CampaignDispatcher(factory, *, input_hashes=None, arm_runners=None,
                   failure_log=None, training_seeds=None, evaluation_seeds=None)
    __call__(condition, seed, episode, context) -> row mapping
    execute(...) -> DispatchRecord(condition, seed, episode, row, arm, mirror)
```

- Twelve arms, in registry order: A, B, C, D, E, F, A′, C′, Fβ, F-init, E-full, floor. An unknown
  arm is refused before any component is built.
- The context supplied by the harness (`master_seed`, paired `environment_seed`, `seed_plan`,
  `config_hashes`, `max_game_updates`, `episodes_per_seed`) is extended with `input_hashes` and
  passed to the arm.
- **A′/C′ mirror.** Before the control episode the dispatcher builds the declared mirror (A for A′,
  C for C′), runs it with the *same* paired environment seed, and passes the artefact as
  `fixed_result`. The control's own runner performs the P1–P19 equivalence check; C′ additionally
  asserts the mirror used the same `graph_digest`. A mismatch raises `EquivalenceMismatch` and the
  dispatcher does **not** retry — the failure is fatal for the seed.
- Evidence returned by the arms (`equivalence`, `zero_pathway`) is merged into `row["evidence"]`
  and the row is re-validated with the arm's expected condition. The dispatcher never fabricates a
  row on failure.
- Any exception is wrapped in `EpisodeFailure` carrying `condition`, `seed`, `episode`, `stage`
  (`components` → `mirror` → `episode` → `row`) and the cause, and is appended to the failure log
  as JSONL when a log is configured. The harness stops; `CampaignRunner.run()` is the resume path.

---

## 5. Certified graphs for C, D and C′ (`campaign/graphs.py`, `conditions/base.py`)

There is exactly one route from a seed to a structure: `CertifiedGraphSource.load(seed)` →
`experiments.phase_8_random.certification.load_structure`. It verifies the namespace marker, the
certificate status, the protocol hash, every mandatory gate, R14, R17 byte identity, the graph file
hash, the graph digest, the original-vs-output difference and the structure-seed derivation. The
source additionally checks `construction == "target_exchange"`, the master seed, the seed fields
and `randomization_quality.passed`.

A missing certificate, a refused certificate, an incomplete namespace, a failed quality gate, a
wrong construction, a foreign master seed or a missing graph file is a hard `GraphSelectionError`.
**There is no fallback to the biological graph** — `graph_and_policy` consults the certified source
only for C, D and C′.

`assert_target_exchange_alignment(biological, randomized)` re-checks on the arrays that the random
graph is a re-pairing of the biological edge set: identical threshold, node and edge counts,
`root_ids`, `edge_src`, `edge_weight`, out-degree and in-degree; only targets move.

`conditions/base.py` now re-verifies any structure record that carries a `certificate_path` through
`certification.verify_structure_record`, so a row that was assembled outside the campaign path
cannot smuggle in an unverified graph.

**The 16 existing certified graphs were not regenerated or modified.** Their certificates, graph
files and the generator code are untouched. The recorded §9.3 deviation stands (see §10).

---

## 6. Seed assignment, reproducibility records and serialization

The harness owns determinism and the dispatcher consumes it; nothing re-derives seeds.

- Environment: `SeedSequence([master, seed, episode, 1])` — condition-independent, so A–F, the
  controls and the floor see the same layout for a given `(seed, episode)`.
- Network: `[master, condition_code, seed, 2]`; learning: `[…, 3]`; structure:
  `[master, seed, 4]` shared by C, D and C′.
- The floor has no condition code and no network/learning/structure stream. `runner.context()`
  used to call `seed_plan()` for every arm, which raised for the floor; it now returns
  `seed_plan=None` for `FLOOR_ID` while still supplying the paired environment seed. This is the
  only change to `runner.py`.
- Every row records `schema_version`, `condition`, `role`, `seed`, `episode`, `environment_seed`,
  `training`, update counts, survival, rewards, termination, action counts and no-action fraction,
  motor-spike count, spike/action digests, before/after weight digests, the three config hashes,
  frozen-input hashes, UTC timestamp and wall time. The schema is closed-world: an unknown key,
  a missing required key, a duplicate `(condition, seed, episode)`, a naive timestamp or an
  inconsistent termination triple is rejected before anything is written.
- Manifests record the run id, design, config hashes, input hashes, memory preflight, environment
  capture and integrity status. A manifest is never overwritten, and resume refuses if the config
  hashes differ from the manifest.

---

## 7. Failure handling, resumability, incomplete-run detection

- The store is append-only JSONL keyed `(condition, seed, episode)`. `append` re-validates;
  `write_if_new` is idempotent; a duplicate is refused; an invalid row never reaches disk.
- A torn trailing line is reported as `StoreError("unterminated…")` and never silently repaired.
- `CampaignRunner.resume` refuses when the run id differs, the config hashes drifted or the memory
  gate fails, then continues only the missing plan entries.
- `run_status(run_dir)` is read-only. It reports plan availability, per-arm and per-seed counts,
  failed rows, training rows, planned/stored/missing counts, the first 200 missing keys, unexpected
  keys, store errors, config-hash drift and a `complete` flag that is true only when the plan
  resolved, the store is readable and nothing is missing or unexpected. Drift forces
  `complete=False`.

---

## 8. CLI (`experiments/phase_8/run_campaign.py`)

Exit codes: 0 ok, 1 incomplete/refused-by-precondition, 2 refused (no authorisation).

| Command | Behaviour |
|---|---|
| `check` | reads config, runs `validate_campaign(strict=False)`, the §9.3 memory preflight and the 16-certificate inspection; reports conformance, gate, graphs, approval and the G3 deviation; `executable` is always `false` |
| `seeds --seed N` | prints the four seed streams per arm and the floor's environment-only entry; verifies environment pairing, C/D/C′ structure sharing and the floor having no neural stream |
| `graphs [--seed N] [--verify]` | certificate-level inspection for all 16 or one seed; `--verify` performs the full `load_structure` checks |
| `status RUN_DIR` | `run_status`; exit 0 only when complete |
| `start --run-id ID` / `resume RUN_DIR` | collects preflight facts, then calls `assert_campaign_authorized()`, which always raises; prints `authorized: false, refused: true, executed: false, episodes_run: 0, rows_written: 0` and returns 2 |

There is no code path in the CLI that constructs a `CampaignRunner` or calls an arm runner.
`start`/`resume` exist so the refusal is explicit and testable rather than implied by absence.
The defensive `else` branch (only reachable if `assert_campaign_authorized` ever stopped raising)
is still gated on the memory preflight, the certified graphs and a resolved design.

Observed on this machine (2026-11-17):

```
$ python -m experiments.phase_8.run_campaign check     # exit 1
conformance 69/69, conforms true
approval: approved false, "PROPOSED - not approved"
protocol sha256 matches expected, authorises_execution false
memory gate: 2.738 GB available of 4.0 GB -> passed false
certified graphs: 16/16 certified, not_certified 0, no biological fallback
randomization deviation: deviation_recorded, gate_weakened false, min 1.628 GB
executable false

$ python -m experiments.phase_8.run_campaign start --run-id would-be-run   # exit 2
authorized false / refused true / executed false / episodes_run 0 / rows_written 0

$ python -m experiments.phase_8.run_campaign seeds --seed 1   # exit 0
environment_paired_across_arms true, structure_shared_by_C_D_Cprime true,
floor_has_no_neural_stream true
```

---

## 9. REV4 conformance (`campaign/protocol.py`)

`validate_campaign` compares the loaded configuration with the constants REV4 declares: master
seed, primary/fallback seed counts, episodes per seed, 900-update cap, 100 SEI updates, α = 0.05,
Holm family sizes (4, 3), 10,000 bootstrap resamples at seed 20261116, the 4 GB gate, 20 readout
episodes and 2,000 E updates; the condition/control/exploratory/floor arm sets; registry order;
per-arm η and training sets; the confirmatory contrasts; the plasticity η, control η, bounds,
5 pA update cap and τe = 20 ms; modulation gain/τ/clip; 200 pA sensory currents over 7 features;
decoder window, thresholds and priority; seed-range disjointness and coverage.

`n_seeds_selected` is reported, not failed: null is the legitimate pre-pilot state, and
`evaluation_plan` refuses to resolve until the pilot decides it. Confirmatory membership accepts
any registered arm, because C4's subtrahend is the control Fβ, not one of the six conditions.

Two facts are carried rather than resolved:

- `approval_status()` reports `approved: false` and `"PROPOSED - not approved"` for U1–U18.
- `randomization_deviation()` reads `campaign_seed_summary.json` and reports
  `deviation_recorded`, `gate_weakened: false` and the certified seeds 1–16.
- `assert_campaign_authorized()` always raises `CampaignNotAuthorized`.

Conformance to declared constants is neither scientific validity nor an authorisation.

---

## 10. G3 deviation and the memory gate

Unchanged and not weakened. The 16 graphs were built at 1.628–2.93 GB free, below the §9.3
4.00 GB gate; `campaign_seed_summary.json` still records `compliance.status =
"deviation_recorded"` and `gate_weakened: false`. G3 is **not complete**, no protocol compliance is
claimed, and the graphs may not be used for experimental data collection until an approved
amendment or a compliant rerun exists.

The live gate on 2026-11-17 reads 2.738 GB of 15.342 GB available, so the campaign, pilot and
training operations are blocked by the rule as written as well as by the missing approval.

---

## 11. Tests executed

```
python -m pytest tests/test_phase_8_campaign_runner.py -q
    -> 52 passed (3.78 s)

python -m pytest tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py tests/test_phase_8_conventional_learner.py \
  tests/test_phase_8_live_plastic_stepper.py tests/test_phase_8_random_campaign.py \
  tests/test_phase_8_random_certification.py tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_readout.py tests/test_phase_8_viability.py tests/test_phase_8_analysis.py -q
    -> 282 passed (20.88 s)
```

The 52 new tests cover: REV4 validation (69/69, deviation recorded, drift rejected), protocol
identity, the authorisation refusal, registry order and semantics, unknown-arm refusal, per-arm
component builds and A′/C′ mirror wiring, floor and conventional routes, failure logging and stage
reporting, `EquivalenceMismatch` payload preservation, malformed-row rejection, factory settings
and refusals (unknown arm, wrong seed, missing training artifacts, undeclared inputs), input-hash
caching and missing-file errors, environment checks, readout width, structure arms never falling
back, certificate enforcement (refused/quality/construction/master/seed/protocol/missing/namespace
states), target-exchange alignment on a 2-node fixture, harness integration (12 rows, floor rows
weightless, A′ evidence present), stop-on-failure (1 row, no fabricated second), resume (3 then 21
of 24), `run_status` complete/incomplete/per-arm/drift/torn-store/no-plan, and the CLI surfaces.

Synthetic-only. No game episode, no BANC simulation, no training and no campaign execution.

Windows, Python 3.13.14, numpy 2.3.4, torch 2.10.0+cpu, psutil 7.1.2.

---

## 12. G5 verdict and remaining blockers

**G5 is complete as a mechanism**: factory, dispatcher, certified-graph source, protocol
validation, status, CLI and tests all exist and pass. **G5 is not complete in the protocol's
operational sense**: no campaign has run, and it may not.

Still blocking a campaign:

1. **REV4 §12 approval.** U1–U18 are proposed. U1, U14, U15 and U18 change what the campaign
   computes or whether the existing graphs count.
2. **G3 §9.3 deviation.** Needs an approved amendment covering construction-time memory or a
   compliant rerun with ≥ 4 GB free. It is a compliance decision, not a build task.
3. **Pilot decision.** `n_seeds_selected` is null; the evaluation plan cannot resolve.
4. **Training artifacts.** F, Fβ and E require trained readouts/agents from a separate training
   stage. That stage is not implemented and could not legally run under the memory gate or the
   approval state anyway. The factory refuses to substitute an untrained model.
5. **Live gate.** 2.738 GB available on this machine, below 4.00 GB.
6. **End-to-end demonstration.** No real BANC episode has been executed through the dispatcher.
   Until one is authorised and runs, the assembly is verified only against stubs.

No experimental execution occurred in this task: zero episodes, zero training runs, zero pilots,
zero campaign rows. No config constant, preregistered parameter or frozen artifact was changed.
No staging, commit, push, reset, clean, stash or delete was performed; `git status` was read only.
