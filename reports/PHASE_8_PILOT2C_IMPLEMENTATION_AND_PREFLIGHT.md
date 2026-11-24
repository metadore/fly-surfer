# Phase 8 — Pilot 2-C implementation and execution preflight

**Date:** 2026-11-21
**Stage:** `pilot2c` — floor and identity certification (S1 re-scope)
**Status:** implementation and synthetic verification complete; **Pilot 2-C has
not been executed**. The readiness gate reports `executable = false`.

This report records only infrastructure and gate results. It contains no
experimental evidence. Every episode discussed below ran on the 32-node test
network inside `tests/`, or was a synthetic fixture; none is a Pilot 2-C row.

---

## 1. Owner decision and protocol amendment

| Document | Path | SHA-256 |
| --- | --- | --- |
| Formal amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` |
| Owner decision D3 | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` |
| Frozen protocol REV4 (unchanged) | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Owner decision D1 (unchanged) | `reports/phase_8_owner_approvals/D1.json` | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| Owner decision D2 (unchanged) | `reports/phase_8_owner_approvals/D2.json` | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |

D3 binds `PHASE_8_PILOT2C_AMENDMENT` at the hash above and binds REV4 at its
unchanged hash. `pilot2c_readiness` re-reads both files from disk and reports
`amendment_matches_disk = true`, `bound_to_rev4 = true`, `failures = []`.

The amendment lists every change from REV4 (A3), the retained confirmatory
design, hypotheses, contrasts, statistical constants and campaign requirements
(A2), the exact pilot scope (A4), the eight claims (A5), the σ_max/U7 position
(A6), the training dependency (A7), the B7 treatment (A8) and the authorisation
model (A9). REV4 itself was not edited.

---

## 2. Files created or modified

Created:

- `docs/PHASE_8_PILOT2C_AMENDMENT.md`
- `reports/phase_8_owner_approvals/D3.json`
- `experiments/phase_8/stages/pilot2c.py`
- `experiments/phase_8/stages/pilot2c_runner.py`
- `tests/test_phase_8_pilot2c.py`
- `reports/PHASE_8_PILOT2C_IMPLEMENTATION_AND_PREFLIGHT.md` (this report)

Modified:

- `experiments/phase_8/campaign/protocol.py` — `PILOT2C_G3_SCOPE`,
  `stage_authorization` (D3 exemption, exact-scope refusal, no inheritance),
  `pilot2c_applicability`.
- `experiments/phase_8/manifest.py` — optional `stage_purpose`, written into
  `design.stage_purpose`; no episode-row schema change.
- `experiments/phase_8/stages/common.py` — floor-aware `PilotPlan`, synthetic
  evidence stamping, `stage_purpose` carried into the manifest.
- `experiments/phase_8/training/loader.py` — A-2 pilot-scope loader
  (`seed_scope="pilot"`), explicit pairing only.
- `experiments/phase_8/training/__init__.py` — exports the A-2 loader.

Not modified: REV4, D1, D2, the protected README, the motor baseline files,
frozen neural parameters, game parameters, statistical constants, campaign
configuration, historical results. No Git operation was performed.

---

## 3. Implemented components

1. **Amendment and owner decision** — hash-bound, REV4-preserving (§1).
2. **Authorization gate** — `stage_authorization("pilot2c", ...)` authorizes
   exactly A, B, F, F_beta, A_prime and the floor at seeds 9001–9003, three
   episodes each (54 rows / 45 neural / 9 floor), `uses_randomized_graph =
   false`. Any other grid is refused with a B7 blocker; other stages do not
   inherit the exemption.
3. **Production runner** — `Pilot2CEpisodeRunner`: builds provenance before the
   episode, runs the floor substrate-free, runs A and caches the artefact, runs
   A′ in process against the cached A, routes B through `b_plastic`, F/F_beta
   through the readout decision source, records readout certification, motor
   summaries, plasticity attribution and artifact provenance, and turns an
   unexpected exception into a schema-valid failure row.
4. **A-2 loader** — pilot evaluation seeds are independent of campaign seeds;
   every `(condition, seed)` needs an explicit training-seed pairing; pilot
   seeds must be disjoint from campaign and training seeds; `require_trained`
   refuses initialized fixtures; A-3 is never used.
5. **Artifact verification** — manifest SHA-256, tensor shape, parameter digest
   and F/Fβ pairing are checked by the loader and by
   `check_readout_pair` before any episode.
6. **Execution paths** — all five neural arms plus the nine floor replays.
7. **In-process A′ identity** — `compare_runs` P1–P19, no tolerance, on the
   same cached A artefact; a mismatch sets a hard stop, the artefact is kept,
   and no retry is attempted.
8. **Evaluator** — `evaluate_certification` recomputes P2C-1 … P2C-8 from stored
   rows, rejects foreign seeds, arms and manifest stage purpose, and reports
   every claim as passed or failed with its evidence.
9. **Storage** — separate `experiments/results/phase_8/pilot2c` destination,
   append-only rows, resume by `(condition, seed, episode)`, refusal to reuse an
   existing run directory, `notes.evidence_kind = "pilot"` and manifest
   `design.stage_purpose = "floor_and_identity_certification"`.
10. **This report.**

Focused test correction made while verifying: `P2C-2` previously read
`evidence.stepper_resets_this_episode`, which also counts the single opening
reset of an episode and could therefore never be zero. The claim now requires
`notes.game_loop.neural_resets_during_episode == 0` (P19: no reset between game
updates) **and** exactly one opening reset. Both A′ and the fixture rows satisfy
it; the identity report itself is unchanged.

---

## 4. Training artifact status

Observed:

- `experiments/results/phase_8/training` does not exist; the loader discovers
  **0** artifact directories.
- No trained F or Fβ artifact exists anywhere in the repository, so no
  evaluation seed can be paired with a real training run.

Therefore the two readout arms cannot be executed. No artifact was created,
trained, retrained or substituted, and no synthetic or initialized state may be
persisted in a pilot row (A4.1 item 7).

---

## 5. B3–B6 status

The gates are open and were not invented or silently chosen:

```
B3: no campaign-to-training seed pairing is declared
B4: no training-episode environment-seed schedule is declared
B5: no checkpoint cadence, retention or format is declared
B6: sampler RNG and optimizer moments are not checkpointed, so resume is
    parameter-continuous and not bit-identical
```

Also open: U7 (`sigma_max` not evaluable). U7 was not discharged and
`design.n_seeds_selected` remains null.

---

## 6. Authorization and preflight status (real configuration)

`pilot2c_readiness(load_phase8_config())`, 2026-11-21:

| Item | Result |
| --- | --- |
| D3 authorization | `authorized = true`, exemption applied, exact scope |
| Amendment on disk | matches D3 hash; bound to REV4 |
| Randomized graph | `uses_randomized_graph = false`, `constructs_randomized_graph = false` |
| Frozen inputs | 7 hashes resolved (graph, nodes, neuron config, motor decoder, plasticity, sensory mapping, synapse policy) |
| Config hashes | environment `b391ecf7…`, campaign `b9a2d3d5…`, conditions `9a93f047…` |
| Memory gate | 4.499 GiB available ≥ 4.0 GiB, passed |
| Results destination | `experiments/results/phase_8/pilot2c`, free |
| Training artifacts | none discovered; no pairing supplied |
| Blockers | missing pairing; no trained artifacts; B3; B4; B5; B6 |
| `executable` | **false** |

Failing gates were reported, not weakened.

---

## 7. Focused test results

- `tests/test_phase_8_pilot2c.py`: **33 passed**, 0 failed.
- Controls, training artifacts, D2 authorization, stage infrastructure, Pilot 1
  runner: **138 passed**, 0 failed.
- All Phase 8 suites (`tests/test_phase_8*.py`): **466 passed**, 0 failed.

The new suite covers the 54-entry grid and all eight claims, exact A/A′
identity on 19 fields plus the hard stop and the resumed-process refusal, F's
frozen state-dependent readout, Fβ's provable state independence, motor-silence
accounting, plasticity attribution, provenance and manifest stage purpose,
schema-valid failure rows, the no-overwrite rule, pilot/campaign separation,
D3's exact scope and non-inheritance, and the A-2 pilot-scope refusals. All
episodes in the suite run on the 32-node test network; the only driver run is
the `synthetic_fixture` path, whose rows are asserted to be rejected as
experimental evidence.

---

## 8. Is Pilot 2-C executable?

**No.** The authorization and provenance gates pass, but two independent
requirements fail:

1. no trained F/Fβ artifacts exist and no explicit `(condition, evaluation
   seed) → training seed` pairing has been declared;
2. training decisions B3–B6 remain open.

---

## 9. Exact next action

1. The owner records decisions B3–B6 (campaign↔training seed pairing,
   training-episode environment-seed schedule, checkpoint cadence/retention/
   format, RNG and optimizer-moment restoration policy) and authorizes the
   training stage.
2. Real F and Fβ artifacts are produced under that authorization and stored
   under `experiments/results/phase_8/training`, with an explicit pairing for
   seeds 9001–9003.
3. Re-run `pilot2c_readiness`; every blocker must disappear before execution.
4. Present the resulting preflight and wait for explicit confirmation of the
   45-episode + 9-floor-replay run.

---

## A4.1 prohibitions, reproduced verbatim

Pilot 2-C may not, under any configuration:

1. add C, C′ or D;
2. construct, read or substitute a randomized graph;
3. accept, resolve or weaken the G3 §9.3 deviation;
4. estimate C1–C4, H1–H3, paired dispersion or `sigma_max`;
5. discharge U7 or set `design.n_seeds_selected`;
6. create, train, retrain or substitute a model artifact;
7. persist synthetic or initialized state in a pilot row;
8. write a row under the campaign results root;
9. merge a pilot row into the campaign dataset;
10. change an episode-row field, a frozen parameter or a statistical constant;
11. modify REV4, D1 or D2;
12. derive its own authorisation from its own output.

None of these was violated: no randomized graph was built or read, no campaign
row was written, no statistic was estimated, no seed count was selected and no
artifact was created.

## Observation and interpretation

Observation: the implementation, the eight claims and the gates behave as
specified under synthetic fixtures. Interpretation: that proves the pipeline is
wired as declared; it does not show that a neural arm produces motor spikes,
that A′ identity holds on the BANC graph, or that F/Fβ readouts trained on real
artifacts behave as the controls predict. Those questions require the real run
and are untested here.
