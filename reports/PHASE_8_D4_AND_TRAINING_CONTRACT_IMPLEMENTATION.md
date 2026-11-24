# Phase 8 — Owner Decision D4 and B3–B6 Training-Contract Implementation

Status date: 2026-11-21
Scope: record owner decision D4, implement the B3–B6 training-operation
contracts in the existing Phase 8 training architecture, and add focused tests.

## 1. Scientific status (read first)

D4 approves and declares four training *contracts*. It authorises **no training
run**. Nothing in this task: started F or Fβ training, generated a real trained
artifact, ran a Pilot 2-C episode, ran a floor replay, built or read a
randomized graph, or modified a frozen parameter, statistical constant,
hypothesis or protocol document. Training remains refused by the gate.

`training_authorization_status()` reports `training_authorized: False`. B3–B6
are now **declared** (D4), but they are not the only training blockers. B2 (U7,
`design.n_seeds_selected` is null) and B7 (the G3 certified graphs carry a
recorded §9.3 memory-gate deviation) remain open. `assert_training_authorized()`
still raises unconditionally.

## 2. D4 owner approval and source-hash verification

D4 is recorded in `reports/phase_8_owner_approvals/D4.json` (record kind
`phase_8_owner_decision`, approval id `D4`, approval date `2026-11-21`,
`depends_on` D3), with the human-readable statement in
`reports/PHASE_8_OWNER_APPROVAL_D4.md`.

Frozen-source hashes were recomputed from disk and compared against the
`frozen_sources` block of `D4.json`:

| Source | Observed SHA-256 | Match |
| --- | --- | --- |
| `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` | yes |
| `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` | yes |
| `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` | yes |

Record hashes at time of writing:

| Record | SHA-256 |
| --- | --- |
| `reports/phase_8_owner_approvals/D4.json` | `1e15138cf76c11ab8c94ffd7299d6a3657fc407fe7c32a0f8a3c9efcca51a8cf` |
| `reports/PHASE_8_OWNER_APPROVAL_D4.md` | `a86b3e1cc7a1eaa22de9e5878138bf0772589484cb035bcb9de6a69148b37935` |

`d4_applicability()` re-reads the D4 record and returns `applicable: True`
only while: the record kind/approval id/date are correct, the approval date is
`2026-11-21`, `depends_on` binds to D3, all four decisions B3–B6 are present,
and every frozen-source hash still matches. Any drift makes D4 non-applicable
and re-blocks B3–B6.

D4 `scope` is all-false for every execution and modification flag, including
`authorises_training_execution`, `generates_trained_artifacts`,
`runs_training_episodes`, `runs_pilot2c_episodes`, `runs_floor_replays`,
`constructs_randomized_graph`, `reads_randomized_graph`,
`modifies_frozen_parameter`, `modifies_statistical_constant`,
`modifies_hypothesis`, `modifies_rev4`, `modifies_d1`, `modifies_d2`,
`modifies_d3`, `changes_pilot2c_grid`, `adds_experimental_condition`,
`discharges_u7`, `sets_n_seeds_selected`. `does_not_authorise` explicitly lists
"a training run".

## 3. The B3–B6 contracts as implemented

All four are declared by D4 verbatim in substance; the implementation is
condition-independent of the frozen scientific parameters and introduces no new
experimental condition.

### B3 — Campaign-to-training seed pairing (`experiments/phase_8/training/contracts.py`)

- Namespace `phase_8/training/B3/v1`, contract version `D4-v1`.
- Payload `namespace|master_seed|evaluation_seed`; SHA-256; first four digest
  bytes as a big-endian uint32, modulo the declared `seeds.training` pool;
  collisions resolved by a linear forward probe in declaration order.
- Derived once per evaluation seed and independent of condition, so F and Fβ at
  one evaluation seed share the training seed (as REV4 §3.6.2 requires) while
  each condition still gets a separate artifact directory, manifest and
  parameter file.
- Deterministic result on the declared pool `[1001..1020]`, master seed
  `20261116`:

  | Evaluation seed | Training seed | Pool index | Pairing digest |
  | --- | --- | --- | --- |
  | 9001 | 1008 | 7 | `bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980` (overall) |
  | 9002 | 1014 | 13 | — |
  | 9003 | 1005 | 4 | — |

- `validate_b3_pairing()` re-derives the mapping and refuses any altered,
  missing or duplicated pairing; `pairing_map()` yields the explicit
  `F:9001→1008`, `F_beta:9001→1008`, … table.

### B4 — Training environment seeds (`contracts.py`)

- Namespace `phase_8/training/B4/v1`; payload
  `namespace|master_seed|training_seed|episode`; SHA-256; first four digest
  bytes as a big-endian uint32.
- Example: `training_environment_schedule(20261116, 1001, 3)` =
  `(3329156124, 220369624, 2643509888)`.
- `assert_environment_stream_disjoint()` refuses any training environment seed
  that equals a Pilot 2-C evaluation episode seed or a declared evaluation seed.
  Training never reuses the evaluation environment stream.
- In `train_readout`, `environment_seed_for_episode=None` now selects this
  declared B4 schedule (previously an error); an explicit callable/int is still
  honoured so existing tests keep their declared sources.

### B5 — Checkpoint policy (`experiments/phase_8/training/exact_checkpoint.py`, `engine.py`)

- When an exact-checkpoint root is supplied, one checkpoint is written after
  **every** completed episode (`exact_step_<n>` under
  `<root>/<condition>/seed_<campaign_seed>/`). All intermediate checkpoints and
  the final checkpoint are retained.
- Each checkpoint carries complete provenance: episodes completed, updates
  completed, declared budget, environment seeds used, sampling seed, metrics
  digest, the full per-episode record list, and B3/B4 provenance blocks.
- Exact checkpoints are `origin = "synthetic_fixture"`, `stage =
  "training_checkpoint"`, schema version 2. They are **not** training artifacts
  and are never loaded by the campaign loader.

### B6 — Exact resumption (`exact_checkpoint.py`, `engine.py`)

- Captured and restored components: model parameters; optimizer state and
  moments (tensors in `components.npz`, scalars in JSON); Python `random`
  state; NumPy global state; PyTorch RNG state; the action-sampler generator
  state (via the new public `ReadoutController.sampler` accessor); and an
  environment RNG state when the caller supplies one.
- `validate_exact_checkpoint()` refuses a checkpoint that claims
  `rng.checkpointed`/`optimizer.state_checkpointed` while a required component
  is absent, and refuses a `progress.episodes` list that disagrees with
  `progress.episodes_completed`.
- `verify_equivalence()` / `assert_resumption_equivalent()` compare an
  uninterrupted run against an interrupted-and-resumed run (per-episode fields,
  final parameter digest, full-state digest, environment seeds used, budget).
  The exactness claim is `"demonstrated"` only when the comparison is empty;
  otherwise it is `"refused"`. The engine never asserts exact resumption on its
  own — `TrainingRun.rng_restored` / `optimizer_state_restored` only record what
  was restored, and `bit_identical_resume.claimed` stays `False` at the stage
  level.

## 4. Authorization-layer and stage integration

- `gate.training_authorization_status()` now reports B3–B6 as `declared` while
  D4 is applicable, and keeps B2 and B7 as blockers. `training_declarations()`
  and `TRAINING_OPERATION_DECISIONS` expose the declaration state.
  `assert_training_authorized()` still raises unconditionally.
- `stages/training_stage.py` describes the exact-checkpoint interface, the B3
  pairing, the B4 schedule and the B6 verification, and raises
  `execution_blockers` from the gate. It still refuses before any execution.
- `stages/pilot2c.py` readiness now states that D4 declares B3–B6 but no
  trained artifact exists, so no Pilot 2-C evaluation can load one. The Pilot
  2-C grid (arms, seeds 9001–9003, 3 episodes/seed, 54 rows) is unchanged.
- `plan.describe_interface` and `engine.describe_engine` names updated to
  reflect D4 declares B3–B6 while training remains refused (U7 null, B7 open).

## 5. Files created or modified

Created:

- `reports/phase_8_owner_approvals/D4.json`
- `reports/PHASE_8_OWNER_APPROVAL_D4.md`
- `experiments/phase_8/training/contracts.py` (B3/B4 derivations and disjointness)
- `experiments/phase_8/training/d4.py` (D4 validity and source binding)
- `experiments/phase_8/training/exact_checkpoint.py` (B5/B6 checkpoints and verifier)
- `tests/test_phase_8_d4_contracts.py` (focused contracts tests)

Modified:

- `experiments/phase_8/training/gate.py` (D4-aware declaration status)
- `experiments/phase_8/training/engine.py` (B4 default, exact checkpoint/resume, provenance)
- `experiments/phase_8/training/plan.py` (interface reason)
- `experiments/phase_8/training/__init__.py` (exports)
- `experiments/phase_8/stages/training_stage.py` (contracts/declarations description)
- `experiments/phase_8/stages/pilot2c.py` (post-D4 training blockers)
- `readout/controller.py` (public `sampler` accessor)
- `tests/test_phase_8_stage_infrastructure.py` (post-D4 expectations)
- `tests/test_phase_8_pilot2c.py` (post-D4 readiness wording)

No frozen scientific document, parameter, statistical constant, hypothesis or
the Pilot 2-C grid was changed. No Git operation was performed.

## 6. Test results

- `tests/test_phase_8_d4_contracts.py`: **36 passed**.
  Covers all twelve required areas:
  1. deterministic B3 and B4 derivation;
  2. namespace separation (B3 vs B4 collision check);
  3. stable B3 pairing and rejection of an altered pairing;
  4. training/evaluation seed separation (B4 schedule disjoint from evaluation
     seeds; reuse of an evaluation seed refused);
  5. F / Fβ artifact separation (separate manifests, shared training seed);
  6. per-episode checkpoint creation;
  7. optimizer and RNG state persistence (manifest flags + momentum roundtrip);
  8. sampler restoration (`apply_exact_restore`);
  9. checkpoint corruption detection (corrupted parameter bytes, missing
     component file);
  10. uninterrupted vs resumed equivalence, plus a divergent resume that the
      verifier refuses;
  11. rejection of incomplete artifacts (parametrized manifest mutations);
  12. D4 hash binding and approval validation (validity, declared-but-not-
      authorised, altered records, changed protocol, missing record,
      amendment/D3 hash equality, checkpoint-is-not-an-artifact).
- Full Phase 8 suite (`pytest tests/ -k phase_8`): **502 passed**, 1079
  deselected.
- Pre-existing suites were updated only where D4 legitimately changes a
  declaration (B3–B6 are now declared rather than undischarged). All
  `training_authorized` / executable assertions remain false.

## 7. Remaining blockers

Training is still refused. Unresolved before any real training can be
authorised:

- **B2 / U7** — `design.n_seeds_selected` is null (the 10.8 pilot decision is
  not recorded).
- **B7** — the G3 certified graphs carry a recorded §9.3 memory-gate deviation
  (`status: deviation_recorded`).
- No trained F/Fβ artifact exists; the campaign loader would refuse to load a
  Pilot 2-C evaluation artifact because none has been produced.

D4 does not discharge U7, does not set `n_seeds_selected`, and does not
authorise a training run.

## 8. Is training ready to be explicitly authorized?

Not yet. The B3–B6 *contracts* are now declared and implemented, and exact
resumption is demonstrated on synthetic fixtures by `verify_equivalence`. But
the gate still refuses training because B2 (U7) and B7 are open, and no trained
artifact has been produced or could be loaded.

A further explicit owner decision would be required to: resolve U7 (set
`design.n_seeds_selected`), accept or clear B7, and then separately authorise a
training run that would generate real F/Fβ artifacts. This report makes no such
authorisation and begins no training.
