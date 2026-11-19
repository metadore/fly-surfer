# Phase 8 G4 — training-artifact pipeline and training engine

**Date:** 2026-11-17 (revised after the training-engine implementation)
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`
**Status:** the training-artifact **infrastructure** and the protocol-declared **training-loop code**
exist and are tested. **G4 is not complete in the protocol's operational sense.** No model on a
real substrate was trained, no trained artifact was generated, no episode or campaign was run, and
no hyperparameter was tuned. The only training-loop executions to date are synthetic fixtures
inside the test suite, and they prove loop mechanics, not learning.

> Naming note: this task's brief calls the work package **G4 — training artifact pipeline**. The
> existing status table also has a "G4 — matched conventional baseline" (the `evaluation/` package).
> They are different work items; this report uses "G4 training artifacts" to avoid confusing them.

---

## 1. What this report claims

| Claim | Evidence |
|---|---|
| An explicit artifact schema exists and is strictly validated | `training/validation.py`; schema, round-trip and refusal tests |
| Declared training constants are checked against REV4, never invented | `training/config.py`; 19 recorded checks, 19/19 pass |
| Initialization is deterministic and seed-derived | `training/initialization.py`, `training/seeding.py`; seeded-init tests |
| Training seeds are recorded separately from campaign and init seeds | manifest fields `training_seed`, `init_seed`, `campaign_seed`, `master_seed`; seed tests |
| F, Fβ and E artifacts cannot be substituted for one another | `validation.assert_condition_compatibility`; separation tests |
| Fβ remains provably state-independent after serialization and reload | `assert_condition_compatibility` re-runs `assert_state_independent` and the zero/saturated-vector logit check |
| Artifacts serialize, reload and re-verify | `training/artifacts.py`; round-trip tests |
| Corrupt, truncated or edited artifacts are rejected | SHA-256 file hash, shape/dtype table, full-state digest and trainable digest checks |
| Missing artifacts and undeclared seeds are rejected | `training/loader.py`; missing-artifact and seed tests |
| Loaded artifacts are compatible with `CampaignFactory` | `loader.check_factory_compatibility`; factory tests |
| **The protocol-declared training loop exists as code** | `training/engine.py`: one REINFORCE update per episode for F/Fβ; one `finish_episode` per episode until 2,000 updates for E/E-full |
| B and D are not converted into conventional training artifacts | `train_readout`/`train_agent` accept only `{F, Fβ}`/`{E, E_full}`; `describe_engine` names B, D, F-init, A′ and C′ under `not_trained_here` |
| Runs are deterministic given the same fixtures | `TrainingRun.sha256()` equality across two runs; parameter and state digests equal |
| Checkpoints serialize, verify and resume | `training/checkpoint.py`; checkpoint round-trip, tamper and resume tests |
| Checkpoints are not artifacts | filename `checkpoint.json`, origin `synthetic_fixture`, stage `training_checkpoint`; never discovered by the artifact loader |
| Checkpoint limitations are recorded, not hidden | every payload stores `rng.checkpointed=false` and `optimizer.state_checkpointed=false` |
| A null `design.n_seeds_selected` blocks artifact generation and campaign preparation | `training/gate.py`; gate tests |
| Training on a real substrate is refused unconditionally | `assert_training_authorized` always raises; `origin="trained"`/`stage="trained"` are unwritable; `plan.run_training` always raises; `TrainingRunContext(mode="authorized_protocol")` raises in its constructor |
| **No model on a real substrate was trained** | no artifact root exists; the only runs are synthetic fixtures in `tests/` |

What this report does **not** claim: that F, Fβ or E has been trained on the BANC substrate or on
the game; that any trained artifact exists; that the loop has been validated against a real run;
that the F/Fβ training seed pairing is scientifically decided; that checkpoint resume is
bit-identical (it is not: RNG and optimizer moments are not stored); or that the protocol
authorises any of this. REV4 remains unapproved (U1–U18 `PROPOSED — not approved`), and its closing
statement authorises no execution.

---

## 2. Files

| File | Lines | SHA-256 |
|---|---|---|
| `experiments/phase_8/training/__init__.py` | 203 | `17f199e300a600c3db221974f712a80c3921b023cc6581f1bf05b24292f99ffd` |
| `experiments/phase_8/training/errors.py` | 59 | `432dd72f7192ef9eeafb20abf20b8648aa80d2010a1822ef86d9fce2aa0aa49f` |
| `experiments/phase_8/training/gate.py` | 95 | `f0aca83c722c8749a19f883fd8d46ae892f07c07491add1b55b32eb80a901ff7` |
| `experiments/phase_8/training/config.py` | 324 | `cdc375c4f758d3957b68016f61aa5e0149ebd9b3a6379a50c4cd252812ff85d3` |
| `experiments/phase_8/training/seeding.py` | 157 | `9f64071e96c2c141553f7aab59d87d1fa06474b741d2f5a3bccf5095f60cb2fc` |
| `experiments/phase_8/training/state.py` | 215 | `c1dc9c232afab4d662dadb2fa142e491fb0621087e63ef91f5d4b1a35251f4ca` |
| `experiments/phase_8/training/initialization.py` | 163 | `56a2fdcaf3f1275c62542c2e0cb8af835ad20e5afb0cecf91ab1ade93e926c64` |
| `experiments/phase_8/training/validation.py` | 420 | `2d2f823cbebe7d688ca349c08c5223193abdd325ae509617c344e25756ba796d` |
| `experiments/phase_8/training/artifacts.py` | 333 | `cc26c5bb7f054226accb141bd1b2f34fc71f67c9724d6a2b14ee2ca0c7b728eb` |
| `experiments/phase_8/training/plan.py` | 242 | `50bcf84a2513d17376f3c4f881c5aaebc3c35437d3f1dc96886f654a58541b13` |
| `experiments/phase_8/training/loader.py` | 311 | `004f1867e0b83df64faa9a4f2148c2f51ee4f3967afc65d1661fa3246e857ae7` |
| `experiments/phase_8/training/engine.py` | 890 | `354290e9dee6a834b9a18f86674b96bf42f025af17fea13df9dff1276bd5216d` |
| `experiments/phase_8/training/checkpoint.py` | 553 | `bb66e5182b6c9de34a02550f5bd3d8abdaf39ec4b63cf5b0ca6f84d12afc3a68` |
| `tests/test_phase_8_training_artifacts.py` | 647 | `94a516834f5518ad0465a01c77a1d5ba11b8a5c610528b5d91a2ea92fcdc2347` |
| `tests/test_phase_8_training_engine.py` | 660 | `6d2c358f3aeec659f3318995fdbc586f5688b71e5c6839c00578952fa6b36165` |

The previous revision of this report claimed "no existing module was modified". That is still true
for this revision as well: `engine.py` and `checkpoint.py` are new, and the edits are confined to
`training/__init__.py` (exports) and `training/plan.py` (docstring and `describe_interface`
entries), both files of this package. The validated training-configuration digest remains
`1508a6a4733fbfc0431e19a91e3d62d76624fef5626e4bb683779d62340433df`.

---

## 3. Artifact schema

An artifact is a directory:

```
<root>/<condition_id>/seed_<campaign_seed>/
    parameters.npz     # every parameter and fixed buffer, pickle-free
    manifest.json      # 22 required keys, strictly validated
```

The manifest fixes:

- **identity** — `schema_version`, `condition_id`, `campaign_seed`, `training_seed`, `init_seed`,
  `master_seed`, `training_environment_seed`;
- **model** — `model_kind`, `architecture`, `n_features`, and the exact `parameter_names`,
  `parameter_shapes`, `parameter_dtypes`;
- **configuration** — the full training-configuration record, its canonical SHA-256, the REV4
  identity with `matches_expected: true`, and the campaign-config path/hash;
- **state** — `digest.state` (all tensors) and `digest.trainable` (optimizer-visible tensors);
- **files** — `parameters.file`, `parameters.sha256`, `parameters.bytes`;
- **provenance** — `origin`, `stage`, and a creation record naming the writing tool.

`origin ∈ {trained, synthetic_fixture}` and `stage ∈ {trained, initialized}`. Only
`synthetic_fixture` + `initialized` is writable in this task. `origin="trained"` routes through
`assert_training_authorized()` (always raises) and `stage="trained"` is refused outright. The
campaign loader requires `origin="trained"`/`stage="trained"` by default and rejects synthetic
fixtures unless a test explicitly enables them.

Expected widths are declared per condition: F = 3, Fβ = 3, E = 7, E-full = 14.

---

## 4. Configuration validation

`validate_training_config(load_phase8_config())` records 19 checks and raises on the first
mismatch. It reads only declared constants from REV4 and the existing modules:

- master seed `20261116`; 20 readout training episodes per seed; 2,000 E gradient updates;
- F/Fβ init standard deviation `0.01` (the existing `f_readout.DEFAULT_INIT_STD`, recorded rather
  than assumed);
- `MotorFeatureSpec` = one `active_fraction` field over three motor populations → 3 features;
- E features 7, E-full features 14; 2×64 tanh; `reinforce_with_value_baseline`; `adam`; 4 actions;
- per-condition `trains` declarations: F/Fβ = readout, E/E-full = policy, F-init = none;
- at least `n_seeds_primary` training seeds are declared;
- the REV4 document is present and matches the certified hash.

A mismatch raises `TrainingConfigError`. A missing or different value is never replaced with a
default. The configuration also embeds the existing `ReinforceConfig` and `ConventionalConfig`
values verbatim, so they cannot drift silently.

The engine consumes those validated values only: `ReinforceConfig(learning_rate=…, gamma=…)` is
built from the configuration, the agent's `ConventionalConfig` is checked field-by-field against it
before training, and the episode/update budgets come from `context` overrides only inside a
synthetic context (`budget.override = true` is recorded) — a protocol-mode run cannot override a
declared budget.

---

## 5. Initialization, seeding and pairing

`initialize(condition_id, campaign_seed=…, training_seed=…, master_seed=…)` builds a freshly
initialized model through the existing condition modules — `f_readout.build_readout` for F,
`f_beta.build_readout` for Fβ, `e_conventional.build_agent(..., training=False)` for E/E-full. It
never trains and refuses F-init: F-init is derived from F's learning stream by the factory and
never carries its own artifact.

`artifact_seeds` records, separately:

- `campaign_seed` — the paired evaluation unit;
- `training_seed` — the declared training seed;
- `init_seed` — the learning stream of the training seed;
- `network_seed` and `environment_seed` — the network stream and first-episode environment seed
  derived from the **training** seed, recorded for audit (the manifest stores the latter as
  `training_environment_seed`); they are not the evaluation episode's seeds;
- `master_seed`.

`init_seed` is a `SeedSequence` drawing; `campaign_seed` and `training_seed` must differ, and every
value is recorded in the manifest so initialization can be replayed.

**Pairing.** REV4 declares the seed *streams* but no campaign-to-training mapping. Rather than
invent one, `validate_pairing` requires an explicit `(condition, campaign_seed) → training_seed`
map. It enforces:

- every active seed has an entry for F, Fβ and E (and E-full when included);
- every training seed is declared in `seeds.training`;
- training seeds are unique per condition;
- **F and Fβ share the same training seed** for a given campaign seed, as §3.6.2's matched
  comparison requires.

The map's provenance is recorded as "caller-declared; REV4 declares no campaign-to-training
mapping". F-init is never paired.

---

## 6. Serialization, integrity and loading

Writing:

- refuses an existing directory (never silently replaces an artifact);
- refuses any state whose `stage` is not `initialized`;
- writes `parameters.npz` pickle-free, then the manifest with the real file SHA-256 and byte size;
- validates the finished manifest before returning.

Reading (`read_artifact`) verifies, in order:

1. manifest presence and schema (version, keys, condition, widths, model kind, architecture,
   origin/stage pairing, embedded config hash, REV4 identity, names/shapes/dtypes, digests);
2. `parameters.npz` SHA-256 and byte count against the manifest;
3. the NPZ keys, shapes and dtypes against the manifest;
4. the recomputed full-state digest;
5. a rebuilt model of the declared kind, loaded with the stored state;
6. the recomputed trainable-parameter digest;
7. condition compatibility — F linear/state-dependent; Fβ `BiasOnlyReadout` with trainable
   `["bias"]`, zero fixed weights and identical logits for zero and 1e6 feature vectors; E/E-full
   `ConventionalAgent`.

`load_training_artifacts` discovers directories, rejects duplicate keys, undeclared seeds and
unexpected conditions, verifies the F/Fβ pair, and packages the models into the existing
`CampaignFactory.TrainingArtifacts` provider. `prepare_campaign_artifacts` checks the unresolved
design **before** reading the artifact root. Checkpoints are invisible to discovery: they are
named `checkpoint.json`, not `manifest.json`.

`check_factory_compatibility` asks the real factory for every loaded key, checks object identity
and per-condition feature width, and builds no component, reads no graph and runs no episode.

---

## 7. Training engine (`training/engine.py`)

The engine implements exactly the loops REV4 declares and nothing more:

| Family | Episode body | Update | Budget | Substrate |
|---|---|---|---|---|
| F / Fβ | one training episode through the existing `ReadoutController`; the readout samples every decision and the environment returns the unshaped reward | exactly one `controller.update()` at episode end (REINFORCE, SGD, `ReinforceConfig` from the validated config) | 20 episodes per seed (REV4 Appendix C) | caller-supplied fixed substrate |
| E / E-full | `reset(seed)`; `encoder.encode` → `agent.act(training=True)` → `environment.step` → `agent.record_reward` until termination or the decision cap | exactly one `ConventionalAgent.finish_episode()` (Adam, value baseline) per episode | until `agent.updates == 2000` (REV4 Appendix C) | none; five-tuple game API |

Both loops:

- reuse the existing condition builders — `f_readout.build_decision_source`,
  `f_beta.build_decision_source`, `e_conventional.build_encoder` — rather than re-implementing
  them, and construct no substrate, read no graph and open no dataset;
- re-assert the condition invariant after every update: F must remain state-dependent
  (`f_readout.assert_state_dependent`), Fβ must remain state-independent
  (`f_beta.assert_state_independent`);
- record per-episode metrics (decisions, loss, mean return or per-episode reward, gradient norm,
  parameter digest after) in a deterministic `TrainingRun` record;
- stop only at the declared budget; the agent loop's `max_episodes` is a loop-safety bound, and
  hitting it raises rather than truncating silently;
- call `model.eval(); model.reset_episode()` at the end of an agent run.

**Safety seam.** `TrainingRunContext` is the only way into either loop. `mode="synthetic_fixture"`
is constructible and exists so tests can exercise the mechanics; `mode="authorized_protocol"`
calls `gate.assert_training_authorized()` inside `__post_init__`, which always raises while REV4
is unapproved. There is therefore no constructible protocol-mode context and no other entry point.
`plan.run_training` still refuses before reaching the engine, so the refusal chain is:
`plan` gate → `context` gate → `checkpoint`/`artifact` origin gates. No path bypasses `gate.py`.

**What the engine does not do.** It does not train B or D (their plasticity runs during
evaluation, REV4 §3.4 row 9), does not produce F-init/A′/C′ (derived or mirror arms), does not
write an artifact, does not choose a seed pairing, does not choose a training-episode environment
seed schedule and does not choose a checkpoint cadence. Those four gaps are explicit caller inputs
listed by `describe_engine()["unresolved_inputs"]`; none is defaulted.

`TrainingRun.as_dict()` declares `training_executed: true`, `training_authorized: false`,
`trained_artifact_written: false`, `rng_restored: false`, `optimizer_state_restored: false`, so a
synthetic run cannot be mistaken for an authorized or artifact-producing one.

---

## 8. Checkpoints and recovery (`training/checkpoint.py`)

A checkpoint is a resumable state record, **not** an artifact:

```
<checkpoint_root>/<condition_id>/seed_<campaign_seed>/step_<n>/
    parameters.npz      # parameters and fixed buffers
    checkpoint.json     # 24 required keys, strictly validated
```

- origin `synthetic_fixture`, stage `training_checkpoint`; `origin="trained"` routes through
  `assert_training_authorized` and raises;
- the payload records identity, validated config hash, REV4 identity, model kind/architecture,
  names/shapes/dtypes, state and trainable digests, file SHA-256/bytes, non-negative progress
  counters, the budget actually used, the environment seeds consumed and a metrics digest;
- reading verifies the file hash, the shape/dtype table and the state digest, then rebuilds the
  model through `initialize()` and reuses `assert_condition_compatibility`;
- `restore_checkpoint` re-checks the campaign/training seeds and condition and refuses a
  checkpoint budget that disagrees with the resumed run.

**Deliberate limitation, recorded in every payload:** sampler RNG state and optimizer moments are
not stored. F/Fβ resume from stored parameters with stateless SGD; E's Adam moments are not part
of `ConventionalAgent.numpy_state`. A resumed run is therefore parameter-continuous, not
bit-identical to an uninterrupted one, and the payload says so (`rng.checkpointed = false`,
`optimizer.state_checkpointed = false`). REV4 declares no checkpoint format or retention rule, so
the cadence and root are caller inputs.

---

## 9. Design gate and authorization

`design_status` reads `design.n_seeds_selected` from `configs/phase_8/campaign.yaml` and currently
returns:

```
value: None, resolved: False, active_seeds: []
reason: design.n_seeds_selected is null: the 10.8 pilot decision (U7) is not
        recorded, so no campaign design exists, no training artifact may be
        generated and no campaign may be prepared from these artifacts
```

`assert_design_resolved` raises `DesignUnresolvedError`. It is called at the top of
`build_training_plan` and `prepare_campaign_artifacts`, so neither a training plan nor a campaign
can proceed with an invented seed count. No value is defaulted.

`assert_training_authorized` always raises `TrainingNotAuthorized`, regardless of arguments.
`plan.run_training` calls it before doing anything, and the engine's protocol context calls the
same function from its constructor. Training authorization is therefore structurally absent, not
merely disabled by a flag.

`build_training_plan` (reachable only with a resolved design, which cannot currently be produced
from the frozen config) expands the four trainable conditions over the active seeds, assigns 20
episodes to F/Fβ and 2,000 gradient updates to E/E-full, and labels F/Fβ/E as confirmatory and
E-full as exploratory. Its own execution entry point refuses.

---

## 10. Tests

New focused files: `tests/test_phase_8_training_artifacts.py` (43 tests, previous task) and
`tests/test_phase_8_training_engine.py` (27 tests, this task). All use temporary directories,
tiny 3/7/14-feature fixture models, deterministic fake episode runners and a fake five-tuple game.
No BANC graph is loaded, no real game episode runs, and nothing is written under
`experiments/results`.

```
python -m pytest tests/test_phase_8_training_engine.py -q
    -> 27 passed (7.69 s)

python -m pytest tests/test_phase_8_training_artifacts.py \
  tests/test_phase_8_training_engine.py tests/test_phase_8_readout.py \
  tests/test_phase_8_conventional_learner.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py -q
    -> 140 passed (9.63 s)

python -m pytest tests -q -k "phase_8"
    -> 352 passed, 1079 deselected (25.74 s)

python -m pytest tests/test_evaluation.py tests/test_motor_populations.py \
  tests/test_phase_7_environment.py -q
    -> 49 passed (7.52 s)

python -m pytest tests -q
    -> 1422 passed, 3 skipped, 6 failed (104.81 s)
```

The six full-suite failures are pre-existing and outside Phase 8: `README.md` hash drift against
`test_integration_3b_3c.py`'s protected-artifact table, the amended P3-3C.5 record in
`test_p3_3c5_lane_encoding.py`, and the Phase 4 motor-substrate smoke verdict ("SMOKE INVALID") in
`test_causal_control.py` and `test_feature_ablation.py`. None imports the training package; all six
were failing for reasons recorded in earlier phases.

The 27 engine tests cover:

- **safety seam** — only the synthetic context is constructible; `protocol_context` consults the
  gate and raises; `plan.run_training` still refuses; B and D are refused as training conditions;
- **loop mechanics** — one update per F/Fβ episode and exactly 20 episodes at the declared budget;
  reduced budgets allowed only in a synthetic context; the agent stops exactly at the requested
  update count and refuses to truncate at the loop-safety bound;
- **condition invariants** — Fβ remains state-independent and F remains state-dependent after
  updates; F uses `LinearReadout`, Fβ `BiasOnlyReadout`, E `ConventionalAgent`;
- **determinism** — two runs with identical fixtures produce the same `TrainingRun.sha256()`,
  parameter digest and state digest;
- **input refusal** — non-positive episode/decision counts, negative seeds, a half-specified
  checkpoint policy, wrong conditions, wrong encoder width, mismatched agent configuration;
- **checkpoints** — write/read round trip, resume from a mid-run step, parameter-continuous
  reproducibility, seed-mismatch refusal, `ArtifactIntegrityError` on a tampered `parameters.npz`,
  `ArtifactCompatibilityError` on a wrong condition, `ArtifactSchemaError` on overwrite,
  `TrainingNotAuthorized` on `origin="trained"`, and no checkpoint written without a policy;
- **integration** — run models are accepted by the factory provider, `factory.training` returns the
  same objects, and `factory.neural_components(..., training=True)` still raises `FactoryError`;
  `describe_engine` names the four unresolved inputs and records zero trained artifacts.

The 43 artifact tests (unchanged from the previous task) cover configuration, initialization,
condition separation, schema and integrity, loader behaviour, gate and pairing, and authorization.

Synthetic loops execute real gradient updates **inside the test process on tiny fixture models**
because that is the only way to test loop mechanics without a real run. They are not experimental
evidence, they are not persisted, and they are not reported as training.

---

## 11. What was not done

In accordance with the brief:

- **no model on a real substrate was trained** — no BANC substrate, no game environment, no
  dataset, no readout over real motor features; no update was applied to any frozen or trainable
  model outside a temporary test fixture;
- **no trained artifact was generated** — `experiments/results/phase_8/training/` was never
  created, and every checkpoint lives in a pytest temporary directory that is discarded;
- no real game episode, pilot or campaign was run;
- no experimental data were collected;
- no hyperparameter was tuned and no frozen parameter was changed; the loop uses only the validated
  REV4 constants;
- REV4, the original BANC data, the frozen artifacts and the 16 certified random-graph artifacts
  were not modified;
- nothing was staged, committed, pushed, reset, cleaned, stashed or deleted.

G4 is therefore **implementation-complete as a mechanism and incomplete as a protocol work
package**. The mechanism now includes both the artifact pipeline and the declared training loops;
execution remains structurally blocked by the approval gate, the unresolved design and the
caller-supplied inputs below.

---

## 12. Remaining blockers

The itemised, interface-level version of this list is `reports/PHASE_8_G4_REMAINING_BLOCKERS.md`.

1. **REV4 is unapproved.** U1–U18 remain `PROPOSED — not approved`; the document authorises no
   execution. No training can be authorized under it, and this task does not authorize any.
2. **`design.n_seeds_selected` is null.** U7 (the pilot-1 decision that fixes N) is not recorded.
   No campaign design, training plan or campaign-artifact preparation can proceed.
3. **The protocol-mode training entry point is unreachable by design.** The loops exist and are
   synthetically tested, but `TrainingRunContext(mode="authorized_protocol")` raises through
   `assert_training_authorized`. Reaching them requires an approved protocol that authorizes a run;
   that is a protocol decision, not a code change.
4. **No campaign-to-training seed pairing is declared by REV4.** The infrastructure requires an
   explicit caller-declared map (`validate_pairing`); choosing it is a protocol decision.
5. **No training-episode environment-seed schedule is declared by REV4.** The engine requires a
   caller-supplied `environment_seed_for_episode`; REV4 §6.3 declares only the evaluation
   environment stream.
6. **No checkpoint cadence, retention rule or format is declared by REV4.** The engine requires
   caller-supplied `checkpoint_every`/`checkpoint_root`; absent a policy, no checkpoint is written.
7. **Sampler RNG and optimizer moments are not checkpointed.** The models do not expose them, so
   resume is parameter-continuous, not bit-identical. This is recorded in every payload and would
   need a protocol decision if bit-exact resume were required.
8. **The G3 §9.3 memory-gate deviation is unresolved.** The 16 certified graphs were built with
   1.628–2.747 GB free against a 4.00 GB gate; `compliance.status = "deviation_recorded"` and the
   gate was not weakened.
9. **Resource gate.** Current free memory is below 4 GB, so no BANC-scale or multi-episode
   operation was attempted; all verification is synthetic.

---

## 13. G4 completeness

| Question | Answer |
|---|---|
| Is the training infrastructure implemented? | Yes — schema, configuration validation, initialization, seeding, serialization, integrity, loader, factory compatibility. |
| Is the protocol-declared training execution code implemented? | Yes — F/Fβ episode loop with one REINFORCE update per episode; E/E-full loop to 2,000 gradient updates; checkpoint write/verify/resume. |
| Has synthetic training verification been performed? | Yes — 27 engine tests execute the loops on tiny fixtures in temporary directories. |
| Has actual training been performed? | No. Zero updates on any real substrate, real readout over real motor features, or real game environment. |
| Have actual artifacts been generated? | No. No `manifest.json` artifact exists; checkpoint files exist only inside pytest temporary directories. |
| Is G4 implementation-complete? | Yes as a mechanism: every REV4-declared training and artifact operation now has code and focused tests. |
| Is G4 protocol-complete? | No. Execution is blocked by the unapproved protocol, four undeclared inputs, the null design and the recorded G3 deviation. |

---

## 14. Integrity

- No Git state was changed: no staging, commit, push, reset, clean, stash or checkout.
- No existing file outside `experiments/phase_8/training/__init__.py`,
  `experiments/phase_8/training/plan.py` and this report was modified; `engine.py`,
  `checkpoint.py` and `tests/test_phase_8_training_engine.py` are new and untracked.
- `experiments/results/phase_8/training/` does not exist; no checkpoint outside a temporary test
  directory exists.
- REV4's SHA-256 is unchanged at
  `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`.
- The BANC graph, node table, frozen Phase 4–7 artifacts and the 16 certified graph artifacts were
  not opened for writing or modified.
- No experimental data were collected and no confirmatory claim is made.
