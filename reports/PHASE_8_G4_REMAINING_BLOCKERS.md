# Phase 8 G4 — remaining blockers

**Date:** 2026-11-17
**Scope:** what still prevents an authorized G4 training run and a trained artifact, after the
training engine and checkpoints were implemented.
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` (unapproved), SHA-256
`e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`.

Nothing below is a coding gap that this task could close without a protocol decision. Each item
names the exact missing decision, the code point that currently enforces the refusal, and what
would unblock it.

---

## 1. Authorization blockers

### B1 — REV4 is unapproved

- **Missing:** approval of U1–U18 and of the protocol as a whole. Every U-entry is marked
  `PROPOSED — not approved`, and REV4's closing statement authorises no execution.
- **Enforced by:** `training/gate.py::assert_training_authorized` (always raises
  `TrainingNotAuthorized`); `training/plan.py::run_training`; and
  `training/engine.py::TrainingRunContext.__post_init__`, which calls the same function when
  `mode="authorized_protocol"`.
- **Unblocked by:** an approved protocol revision that authorises training. No flag or parameter
  can bypass the gate in the current code.

### B2 — `design.n_seeds_selected` is null

- **Missing:** the U7 pilot-1 decision that fixes the campaign seed count N.
- **Enforced by:** `training/gate.py::assert_design_resolved` (`DesignUnresolvedError`), called
  first in `build_training_plan` and `prepare_campaign_artifacts`.
- **Unblocked by:** recording a numeric `design.n_seeds_selected` in
  `configs/phase_8/campaign.yaml` under an approved protocol. No default exists.

---

## 2. Undeclared protocol inputs (caller-supplied, never invented)

### B3 — Campaign-to-training seed pairing

- **Missing:** a mapping `(condition, campaign_seed) → training_seed`. REV4 declares the seed
  *streams* only.
- **Enforced by:** `training/seeding.py::validate_pairing` requires a complete caller-declared
  map, per-condition uniqueness and a shared F/Fβ training seed; `training/loader.py` applies the
  same map when loading artifacts.
- **Unblocked by:** the protocol declaring or the experimenter preregistering the pairing.

### B4 — Training-episode environment-seed schedule

- **Missing:** how the environment seed is chosen for each training episode. REV4 §6.3 declares
  only the evaluation environment stream.
- **Enforced by:** `training/engine.py::train_readout` / `train_agent` require a caller-supplied
  `environment_seed_for_episode` callable or integer; there is no default.
- **Unblocked by:** a declared schedule (for example deriving it from the training seed and the
  episode index), recorded in the protocol.

### B5 — Checkpoint cadence, retention and format

- **Missing:** when checkpoints are written, how many are kept and where.
- **Enforced by:** `training/engine.py` requires `checkpoint_every` and `checkpoint_root` together;
  without them no checkpoint is written. `training/checkpoint.py` adds no default.
- **Unblocked by:** a declared checkpoint policy if resumability is required.

### B6 — Sampler RNG and optimizer-state checkpointing

- **Missing:** whether a resumed run must be bit-identical. The existing models do not expose
  sampler RNG or optimizer moments.
- **Enforced by:** every checkpoint payload records `rng.checkpointed=false` and
  `optimizer.state_checkpointed=false`; `restore_checkpoint` restores parameters and counters only.
- **Unblocked by:** a protocol decision that bit-exact resume is required, followed by exposing and
  serializing that state. Resume is currently parameter-continuous, not bit-identical.

---

## 3. Compliance and resource blockers

### B7 — G3 §9.3 memory-gate deviation

- **Missing:** a decision on the already-built Condition C graphs. They were constructed with
  1.628–2.747 GB free against the 4.00 GB gate; `campaign_seed_summary.json` records
  `compliance.status = "deviation_recorded"` and `gate_weakened: false`.
- **Enforced by:** the campaign and training readiness checks read the recorded compliance status;
  the gate itself was not weakened.
- **Unblocked by:** an approved amendment covering construction-time memory, or a rebuild with
  ≥ 4 GB free.

### B8 — Current free memory below the declared gate

- **Missing:** enough free memory to run BANC-scale training episodes under the 4.00 GB rule.
- **Enforced by:** the runner's §9.3 gate; no BANC-scale or multi-episode operation was attempted
  in this task.
- **Unblocked by:** running on a machine that satisfies the gate, or an approved amendment.

---

## 4. What is **not** a blocker

The following mechanisms now exist, are tested synthetically, and need no further implementation
work before a run can be executed once B1–B8 are resolved:

- artifact schema, validation, serialization, integrity verification and reload;
- deterministic initialization and separate seed recording;
- the F/Fβ episode loop with one REINFORCE update per episode and the 20-episode budget;
- the E/E-full loop to 2,000 gradient updates on the five-tuple game API;
- condition separation, Fβ state-independence re-checks and F state-dependence re-checks;
- resumable checkpoints with hash, shape/dtype and digest verification;
- loader and `CampaignFactory.TrainingArtifacts` compatibility;
- refusal paths, including the engine's protocol-mode constructor.

No trained artifact exists, no real-substrate update has been applied, and
`experiments/results/phase_8/training/` has never been created.
