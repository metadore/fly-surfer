# Phase 8 Pilot 2-C — Execution Preflight (post-resolution)

**Stage:** `pilot2c` — REV4 §10.8 as amended by D3
**Record kind:** execution preflight
**Generated:** 2026-11-23
**Machine report:** `reports/PHASE_8_PILOT2C_EXECUTION_PREFLIGHT.json`
**Supersedes:** `reports/PHASE_8_PILOT2C_FINAL_PREFLIGHT.{md,json}` (preserved unmodified). That report's `executable=false` came from a single mis-scoped blocker; this report records its resolution.

**Owner authorization in force (2026-11-23):** execute the complete D3-approved Pilot 2-C grid exactly, after resolving the final preflight blocker legitimately. This is a Pilot 2-C execution authorization only. It is not a campaign authorization and does not extend to E/E-full, randomized graphs, G3 acceptance, N/U7/σ_max changes, frozen-parameter changes, Phase 9 or Git operations.

---

## 1. The blocker and its exact source

The earlier preflight reported exactly one blocker:

> `training: D4 declares B3-B6 and D5 authorises only the six F/F_beta pilot artifacts; the global training gate still refuses any further training, and loadability is reported under training_artifacts`

It was produced by `_training_blockers()` in `experiments/phase_8/stages/pilot2c.py`, whose value was appended unconditionally to the readiness `blockers` list. Every other readiness check already passed: D3 stage authorization authorized with an empty blocker list, scope exact, three config hashes, seven frozen-input hashes, memory above the gate, all six trained artifacts loaded, and the results destination free.

### Why it is stale rather than a genuine restriction

- **It describes the training stage, not this stage.** Pilot 2-C runs no training (amendment C-7). It evaluates artifacts already produced under D5. A refusal of *further training* cannot be a precondition for an evaluation stage that never enters the training gate.
- **The amendment's actual condition is satisfied.** §A7 of `docs/PHASE_8_PILOT2C_AMENDMENT.md` states Pilot 2-C is not executable "until D3's scope is satisfied **and** valid F/Fβ artifacts exist **and** B3–B6 are recorded". All three now hold: D3 is applicable, the six D5 artifacts are certified, and D4 declares B3–B6. The string was written when B3–B6 were undeclared and no artifact existed.
- **The genuine restriction it stood in for is already enforced elsewhere.** The artifacts must load as `origin=trained` with their exact manifests, digests, pairing and config/protocol binding — enforced by `load_pilot_evaluation_artifacts(..., require_trained=True)`, which fills `training_artifacts`. Without them the stage is still refused.
- **Nothing is weakened by dropping it.** `assert_training_authorized` still raises; `training_authorization_status()["training_authorized"]` is still `False`; `assert_campaign_authorized` is unchanged; B2 (U7) and B7 (G3) remain open; D5's `does_not_authorise` still excludes Pilot 2-C episodes (the owner, not D5, authorises them).

## 2. The correction (smallest scope-specific change)

In `experiments/phase_8/stages/pilot2c.py`:

1. `training_blockers` is still computed and still reported (under `training_blockers`), but is **no longer folded into the stage `blockers`**. It is a training-stage statement, reported and never resolved here.
2. A genuinely scoped precondition replaces it: `d5_applicability()` must be applicable (D5 valid and bound; D6 depends on the present D5; G3 record preserved). If not, readiness adds `training artifacts: <reason>` and refuses.
3. `pilot2c_readiness` now reports `training_authorization` with both authorities distinguished: `d5_d6_applicable`, `d5_scope_authorized` (D5's six-artifact scope) and `global_training_gate_authorized` (`False`).
4. `run_pilot2c` now loads the six qualified artifacts and injects them into `Pilot2CEpisodeRunner`, so F/Fβ evaluate the verified trained readouts. Without a pairing or artifacts it still refuses with an explicit `StageRefusal`.

Regression tests (`tests/test_phase_8_pilot2c.py`):

- `test_readiness_reports_the_training_refusal_without_blocking_evaluation` — the training refusal is present in `training_blockers`, absent from `blockers`, and the global training gate is still `False`.
- `test_readiness_refuses_without_a_live_d5_authority` — with D5 not applicable, readiness is non-executable with a `training artifacts:` blocker.

The complete Phase 8 suite was rerun after the change (see §6).

## 3. Owner-decision verification (recomputed from disk)

| Record | SHA-256 (prefix) | Status |
|---|---|---|
| D1 | `5c183c992c7f68ed…f364d489` | approved; §12/U1–U18 as written; `document_authorises_execution=false` |
| D2 | `b5b0c229edded834…c0c17327` | valid; Pilot 1-only G3 exemption; accepts/weakens nothing; bound to REV4 |
| D3 | `74f11d2c599ceffb…42948df8` | applicable; amendment matches disk; bound to REV4 |
| D4 | `1e15138cf76c11ab…cca51a8cf` | applicable; B3–B6 declared; authorises no run |
| D5 | `015598e82217b065…ca8bfe3f` | applicable; exactly six F/Fβ artifacts; G3 record preserved |
| D6 | `6a3425040f710917…61d8325` | present; valid; depends on the present D5 |

Frozen sources recomputed and matching their recorded values: REV4 `e4aa9e0f…b4bcb1547c`, amendment `832ef485…ca9667ad`, approved proposal `f8d441a4…e6d3771`.

G3 remains `deviation_recorded`, `gate_weakened=false`, 16 graphs and 16 certificates unchanged. D3 accepts nothing and weakens nothing.

## 4. Certified trained artifacts

All six load as `origin=trained`, `stage=trained`, `evidence_kind=experimental`, substrate `biological_graph`, `uses_randomized_graph=false`, with 20/20 retained and integrity-verified checkpoints.

| Artifact | Eval seed | Training seed | Pool index | Trainable digest (prefix) | Parameters SHA-256 (prefix) | Manifest SHA-256 (prefix) |
|---|---|---|---|---|---|---|
| F | 9001 | 1008 | 7 | `bd50cc734361` | `35918eb7bf8d9f2f` | `5fef4667620fb02b` |
| F | 9002 | 1014 | 13 | `e1c25034b0e6` | `a71b47a30f4992bb` | `26f453a57fcae84d` |
| F | 9003 | 1005 | 4 | `2e188b786436` | `3ad5e6be64cf7cb7` | `92876470923f10ea` |
| Fβ | 9001 | 1008 | 7 | `0975693e51a6` | `1030fe141f15f34d` | `83f27f46d3eaba93` |
| Fβ | 9002 | 1014 | 13 | `5f03c88b093e` | `41abbe4d215fda77` | `9609fadd72a4425b` |
| Fβ | 9003 | 1005 | 4 | `b157ae1e6091` | `b1cd7e70f3e1d518` | `20f352c5c189298e` |

Pairing is the B3 derivation, recomputed and equal to D5's recorded derivation (`bc231c796d7efb01…a143a1f980`): `F:9001→1008`, `F:9002→1014`, `F:9003→1005`, and the same for `F_beta` (condition-independent, so F and Fβ share the training seed per evaluation seed). Written as a new file `reports/PHASE_8_PILOT2C_PAIRING.json`.

## 5. Preflight result

| Check | Result |
|---|---|
| D3 stage authorization | authorized, exemption applied, blocker list empty |
| Pilot 2-C scope | 54 entries (5 neural arms × 3 seeds × 3 episodes = 45; floor 9) |
| Config hashes | exactly `environment`, `campaign`, `conditions` |
| Frozen-input hashes | 7 (`graph`, `nodes`, `neuron_config`, `motor_decoder`, `plasticity`, `sensory_mapping`, `synapse_policy`) |
| Memory (B8) | above the 4.0 GB gate (see the JSON for the run-time measurement) |
| Trained artifacts | all six loaded, `trained-artifacts`, complete |
| D5/D6 | both applicable |
| Global training gate | still `False` (reported, not a stage blocker) |
| Results destination | `experiments/results/phase_8/pilot2c` free |
| `executable` | **true**, blockers `[]` |

## 6. Tests

The complete Phase 8 suite was rerun after the change; the results are recorded with the execution report. Nothing was executed before the suite passed.

## 7. What remains blocked after Pilot 2-C

The confirmatory campaign, E/E-full, randomized-graph construction or access, G3 acceptance, any change to N/U7/σ_max/statistical constants or frozen neural parameters, Phase 9, and all Git operations. Pilot 2-C rows are never merged into the campaign dataset, and U7/`n_seeds_selected` stay null.
