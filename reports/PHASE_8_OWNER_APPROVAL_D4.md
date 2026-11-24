# Phase 8 Owner Approval D4 — Training-Operation Decisions B3–B6

Record: `reports/phase_8_owner_approvals/D4.json`
Approval date: **2026-11-21**
Owner decision: **D4** (depends on D3)

## 1. Decision

The owner approves and declares the four Pilot 2-C training-operation decisions
B3, B4, B5 and B6, and authorises their implementation as training contracts.
The decision fixes *how* F and Fβ training artifacts would be paired, seeded,
checkpointed and resumed. It authorises **no training execution**, generates
**no trained artifact**, and runs **no Pilot 2-C episode or floor replay**.

## 2. Hash binding

D4 is recognised only when it is bound to the exact documents it cites. The
record stores these values and the validator recomputes each hash from disk.

| Document | Path | SHA-256 |
| --- | --- | --- |
| REV4 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Pilot 2-C amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` |
| D3 record | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` |
| D1 record (transitive) | `reports/phase_8_owner_approvals/D1.json` | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| D2 record (unchanged) | `reports/phase_8_owner_approvals/D2.json` | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |

A changed REV4, amendment or D3 invalidates D4 rather than silently inheriting
its decisions.

## 3. Decisions, verbatim in substance

### B3 — Campaign-to-training seed pairing

Pair evaluation seeds 9001, 9002 and 9003 with training artifacts for F and Fβ.
Derive each training seed by a documented SHA-256 namespace-based derivation
from the master seed and the evaluation seed, mapping the digest
deterministically onto the declared `seeds.training` pool. Do not use arbitrary
offsets, evaluation randomness or an implicit default pairing. F and Fβ at one
evaluation seed share the derived training seed, as REV4 §3.6.2 requires, but
each condition receives its own independently traceable artifact directory,
manifest and parameter file.

Declared derivation: namespace `phase_8/training/B3/v1`, payload
`namespace|master_seed|evaluation_seed`, index = first four digest bytes as a
big-endian uint32 modulo the declared pool length, collisions resolved by
linear forward probing in declaration order. The derivation is
condition-independent, so F and Fβ share a training seed while producing
separate artifacts.

### B4 — Training environment seeds

Derive a deterministic, separate environment-seed stream for every training
seed and training episode. The training stream is not the evaluation
environment stream: it must never reproduce a Pilot 2-C evaluation episode seed,
and no training environment seed may equal a declared evaluation seed.

Declared derivation: namespace `phase_8/training/B4/v1`, payload
`namespace|master_seed|training_seed|episode`, seed = first four digest bytes as
a big-endian uint32. Every value is checked against the Pilot 2-C evaluation
environment seeds for seeds 9001–9003 and episodes 0–2.

### B5 — Checkpoint policy

Checkpoint after every completed training episode. Preserve the final
checkpoint and every intermediate checkpoint needed for recovery and audit,
together with complete provenance. No checkpoint is a training artifact and none
may be loaded by the campaign loader.

Declared policy: cadence 1; retain all intermediates and the final checkpoint;
exact-checkpoint schema 2 (`manifest.json`, `parameters.npz`,
`components.npz`); origin `synthetic_fixture`; stage `training_checkpoint`;
provenance includes condition, campaign seed, derived training seed, init seed,
master seed, protocol and training-config digest, environment seeds used,
progress counters and the derivation record.

### B6 — Exact resumption

Checkpoint and restore model parameters; optimizer state and moments; Python,
NumPy and framework (PyTorch) RNG state; sampler state; and applicable
environment RNG state. A checkpoint that claims exactness while any required
component is absent is refused. Define and run a verification procedure that
compares an uninterrupted run with an interrupted-and-resumed run. Exact
resumption is not claimed until that equivalence is demonstrated.

Declared verification: run the declared budget twice (uninterrupted; interrupted
after a checkpoint and resumed), then compare the final trainable-parameter
digest, final full-state digest, every per-episode metric, every environment
seed used, and the sampler state digest. Equivalence is claimed only when every
compared value is identical.

## 4. Boundary

D4 does not authorise, and the implementation must not perform:

- starting F or Fβ training;
- generating a real trained artifact;
- running a Pilot 2-C episode or any floor replay;
- constructing or reading a randomized graph;
- modifying frozen neural parameters, statistical constants, hypotheses or
  REV4;
- modifying D1, D2 or D3;
- changing the approved Pilot 2-C grid or adding an experimental condition;
- discharging U7 or setting `design.n_seeds_selected`.

D4 authorises only the declaration of B3–B6 and the implementation and focused
testing of their contracts. Training therefore remains unauthorised after D4.
