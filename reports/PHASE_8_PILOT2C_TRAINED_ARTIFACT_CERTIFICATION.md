# Phase 8 — Pilot 2-C trained-artifact certification

Status: **certification complete for the six D5-authorised artifacts.**
Date: 2026-11-23. Evidence: `reports/PHASE_8_PILOT2C_TRAINED_ARTIFACT_CERTIFICATION.json`.

This document certifies that the six F/F_beta artifacts written under
`experiments/results/phase_8/training/` are the artifacts D5 authorises, that
each one reloads and verifies against its schema and provenance, that the
pairs are the declared B3 pairings, and that the one interrupted artifact was
resumed and is equivalent to a preserved uninterrupted reference.

It certifies **nothing** about C1–C4, H1–H3, paired dispersion or `sigma_max`.
It executes no Pilot 2-C episode, no floor replay, no E/E_full run and no
campaign step, and it reads no randomized graph.

## 1. Sources and bindings

Every hash below was recomputed from disk during this certification.

| Source | Path | SHA-256 | Binding |
|---|---|---|---|
| REV4 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` | matches the frozen REV4 |
| Amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` | matches D3 |
| D3 | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` | Pilot 2-C scope |
| D4 | `reports/phase_8_owner_approvals/D4.json` | `1e15138cf76c11ab8c94ffd7299d6a3657fc407fe7c32a0f8a3c9efcca51a8cf` | B3–B6 contracts |
| D5 | `reports/phase_8_owner_approvals/D5.json` | `015598e82217b0655b0c4e851948b5c2fc08c16967023238f04c1389ca8bfe3f` | the six-artifact training authorisation |
| D6 | `reports/phase_8_owner_approvals/D6.json` | `6a3425040f71091748078055ba1d871a33ae3d39df8a9ed3ebb7b0aba61d8325` | B7 has no subject in the D5 plan |
| Approved proposal | `reports/PHASE_8_REMAINING_BLOCKERS_B2_B7_DECISION_REVIEW.md` | `f8d441a4e98bdc73ebcb7405acff02fc7221969a0aa1217ff7f88cfe2e6d3771` | the proposal D5 approves |
| Training config | `experiments/phase_8/config/training.yaml` | `1508a6a4733fbfc0431e19a91e3d62d76624fef5626e4bb683779d62340433df` | every checkpoint and artifact |

The D5 applicability check recomputed B3 from the declared pool:
`bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980`, matching
the D5 record. `design.n_seeds_selected` remains `null`; U7 remains open.

D6 is non-inheritable and changed nothing: the G3 summary is still
`status = "deviation_recorded"`, `gate_weakened = false`, REV4 §9.3, 4.0 GB,
16 graph seeds, and no graph file or certificate was written, regenerated or
read for this certification.

## 2. What was executed

The D5 plan contains exactly six artifacts and 120 episodes, on the frozen
biological substrate only:

| Condition | Evaluation seed | Training seed | Pool index | Episodes |
|---|---|---|---|---|
| F | 9001 | 1008 | 7 | 20 |
| F | 9002 | 1014 | 13 | 20 |
| F | 9003 | 1005 | 4 | 20 |
| F_beta | 9001 | 1008 | 7 | 20 |
| F_beta | 9002 | 1014 | 13 | 20 |
| F_beta | 9003 | 1005 | 4 | 20 |

Each episode is the real closed loop; one REINFORCE update is applied to the
readout per episode and no synaptic weight changes. `origin = "trained"`,
`stage = "trained"`, `evidence_kind = "experimental"` everywhere. Nothing
synthetic was promoted into the real training root; the
`test_real_training_storage_holds_only_authorized_trained_artifacts` guard now
enforces that invariant against the real directory.

## 3. Certified artifact inventory

All digests and hashes below were recomputed from disk; every artifact reloads
through `verify_trained_artifact` with its expected condition.

| Condition | Eval seed | Train seed | Init seed | Ep. | Ckpts | Trainable = state digest |
|---|---|---|---|---|---|---|
| F | 9001 | 1008 | 1350278753 | 20 | 20 | `bd50cc7343616dd3768b25291d2f3a25f2ae6d56b1c8825de2029ef7889a8883` |
| F | 9002 | 1014 | 3449218186 | 20 | 20 | `e1c25034b0e6896f9548fddabd41e4ca9df6d2bf732e816b02e71d25b33dadce` |
| F | 9003 | 1005 | 3297997184 | 20 | 20 | `2e188b78643612cbdc07570d829fe988c09f5ef29162edb7c419d438c08d9961` |
| F_beta | 9001 | 1008 | 1849113230 | 20 | 20 | `0975693e51a610ab9cc2524d08f3f461eed0d097eb18ae20db8aefbb5191f76e` |
| F_beta | 9002 | 1014 | 992595534 | 20 | 20 | `5f03c88b093e079ef2a1d87e20efb72b7cdc3566af78e74f2d5a4da4062ff5b9` |
| F_beta | 9003 | 1005 | 56964545 | 20 | 20 | `b157ae1e60912134f0132843f9036fa1ee2a653752aaad0c89eb36a98a6ca120` |

| Condition | Eval seed | Parameters SHA-256 | Manifest SHA-256 | Provenance SHA-256 |
|---|---|---|---|---|
| F | 9001 | `35918eb7bf8d9f2f8b631f1612519484dc845fca71d5c08e61918044ba42efb6` | `5fef4667620fb02b6c1708c4b8426fa00e61d35b4aedecae19d393d4c4998e95` | `fd30434b020593233969364409a7f000d39379455d5a4489a8b854643491fb47` |
| F | 9002 | `a71b47a30f4992bb1cad1d35241dfdbcfb5521fac72347654abcf213fd3d5d95` | `26f453a57fcae84d244ce6745812d66dfd97bf3f2a996ed849d36bd1f27b40da` | `2ca20d61e117d271dea864a4f4b0582227715033af8c90919754c330acb225c2` |
| F | 9003 | `3ad5e6be64cf7cb7cf912dece30c91fa51bc028950436534e7dea1ec982d0e17` | `92876470923f10ea8d486531eb017ce46e44af88c13142ec459793a87bf360fd` | `3c17d214a63ae1b90bbc3fc40cfe9043a660627f8d26901761c536de6db81089` |
| F_beta | 9001 | `1030fe141f15f34d9cc4e9f8b1b2140f0dbc7fc13f6759a6ccdd1574d14215a5` | `83f27f46d3eaba933151dc44e0a77e91c09e9e28ea091a440b6b832f551c9a14` | `bf076a269ee65173b10c7ff569807f9a4d4f9a15c0f86fe81a39eb659c522b3a` |
| F_beta | 9002 | `41abbe4d215fda77d29aa7904659f70219e2f570668c17cc463c7a3bae80e6a8` | `9609fadd72a4425b5b599a746cb017df6c8fd64ff06d1fa36b03bf1f9f2ceb53` | `ec46c723bef0d37969d234231e61e622a9b50360d41e3778b1d4cf80936bd888` |
| F_beta | 9003 | `b1cd7e70f3e1d5189e8e0d5708345f0ef588ea5eae4b6fddfbdcbe08d2f86e85` | `20f352c5c189298ede000bb01bfe7b25b1b93ecf1fff5f3e8a346fdf940cc80b` | `e32c627b2dd375b239b0b8f1960c0f3837b8ae0fa5a2fc6c16dd760b99a2a887` |

For every artifact: 22 manifest keys, `origin = "trained"`, `stage = "trained"`,
width `n_features = 3`, model kinds `linear` (F) and `bias_only` (F_beta), one
B4 schedule of 20 environment seeds, budget 20, 20 episode records, 20 ledger
checkpoints (all `integrity_verified = true`, `retained = true`, episode indices
1–20), and 20 matching optimizer digests.

F_beta's initial parameter digest is identical at all three seeds
(`f94b54c9e77efdbf4cc636c1f31b380b4d14fbbfdd168f76d502c691110f058e`): the
bias-only readout starts from a fixed zero vector and forward ignores features,
so its initialization is seed-independent by construction. Its trained digests
and files differ by seed because the reward stream differs. Artifact identity is
therefore `(condition, evaluation seed)`, never a parameter value.

## 4. Pairing and identity

* F and F_beta share the training seed at each evaluation seed (1008, 1014,
  1005), and each has its own init seed; all six init seeds are distinct.
* Each pair has a distinct trainable digest and a distinct manifest file. The
  B3 per-entry digests are distinct per evaluation seed; D5's global B3 digest
  is `bc231c79…92a75a143a1f980`.
* The Pilot 2-C plan is the exact D3 scope: 54 entries = 45 neural
  (A, B, F, F_beta, A_prime × 3 seeds × 3 episodes) + 9 floor; arms
  `(A, B, F, F_beta, A_prime, floor)`, seeds `(9001, 9002, 9003)`;
  `uses_randomized_graph = false`, `constructs_randomized_graph = false`.
* A/A′ identity is **structural only here**: every A entry has an A′ partner at
  the same seed and episode with the same environment seed, and A′ declares
  `eta = 0.0` with `exact_match_of = A`. The behavioural identity is evaluated
  only by executing Pilot 2-C episodes, which this certification does not do.

## 5. B5 checkpoint retention and a transparent provenance correction

All six artifacts retain every intermediate checkpoint and the final
checkpoint: `checkpoints/episode_001 … episode_020`, 120 checkpoint
directories in total.

One provenance defect was found and corrected after the run. For the one
interrupted artifact (F / 9001), the runner wrote its B5 ledger only for the
episodes it ran itself (2–20); episode 1, which predates the interruption and
was restored from its verified checkpoint, was missing from
`training_run.json` and from the optimizer-digest index. The correction:

* preserved the original record byte-for-byte as
  `training_run.incomplete_provenance.json`
  (`a385aabd120fda53e7c585d0b65129800d469fa91004b4cedbc16cc02ccd7a8e`);
* rebuilt the ledger from all 20 verified on-disk checkpoints; episodes 2–20
  are byte-identical to the pre-correction records, so only the missing entry
  was added;
* rewrote `training_run.json` (`fd30434b…`) with a self-describing
  `provenance_correction` block and the equivalence-report hash;
* preserved the previous execution summary as
  `execution_summary.pre_provenance_correction.json` (`6fea7e1c…`) and updated
  the F / 9001 record's provenance hash and checkpoint count in
  `execution_summary.json` (`24aca2e5…`);
* appended a `provenance_corrected` event to the append-only log
  (`pilot_training_log.jsonl`, `7656cf8e…`, 21 lines).

No parameter, digest, episode metric or checkpoint byte changed. The defect is
a ledger-completeness bug in resume; the runner now rebuilds the ledger for
episodes `1..start` on resume, and
`test_resumed_run_ledger_retains_every_checkpoint` guards it.

## 6. Interruption, recovery and B6 equivalence

The first execution attempt failed after F / 9001 episode 1 with a logging
`KeyError` (`artifact_failed` in the log). Per the B5/B6 protocol the run was
not restarted. It was resumed from the verified `episode_001` checkpoint with
the seed, budget and substrate unchanged (`interruption_detected`,
`recovery_completed`). These events are retained in the append-only log.

Equivalence was demonstrated twice:

1. **Recorded at recovery.** An uninterrupted reference of the same seeds was
   run separately; `verify_equivalence` compared 20 episodes across 12 fields
   and found no difference
   (`training_recovery_reference/F/seed_9001/equivalence.json`,
   `equivalent = true`, `exactness_claim = "demonstrated"`).
2. **Independently re-checked now** from the preserved reference checkpoints
   (`training_recovery_reference/F/seed_9001/checkpoints/episode_001…020`):
   * final parameters are byte-identical
     (`35918eb7…` in both runs);
   * final trainable and full-state digests are identical
     (`bd50cc73…`);
   * the 20 environment seeds are identical;
   * all 20 episodes agree on all 12 compared fields.

The other five artifacts ran uninterrupted and record `resume.resumed = false`.

## 7. Boundaries preserved

* No randomized graph was regenerated, read or used; no graph-dependent stage
  was accessed. D6 records B7 as having no subject in the D5 plan and stays
  non-inheritable.
* No E or E_full run, no campaign step, no Pilot 2-C episode and no floor
  replay was executed.
* No frozen parameter, statistical constant, hypothesis, contrast, REV4,
  D1–D4, Pilot 1 record or historical result was modified. New evidence was
  written only to new files or the append-only log.
* No Git operation was performed.
* The global training gate still refuses further training (B2/U7 and B7/G3
  remain open); D5 authority is narrow, per-artifact and explicit.

## 8. Training-outcome observations (not a certification criterion)

The certification above concerns artifact identity, schema, pairing and
recovery. Reading the recorded episodes also shows a behavioural limitation
that must not be mistaken for a certification pass:

* All 120 episodes ended by collision; every episode recorded
  `motor_spikes = 0`; no episode changed a synaptic weight (`weights_before =
  weights_after` in all records).
* At each evaluation seed, F and F_beta produced identical actions, episode
  rewards and decision counts in all 20 episodes. Their trained biases are
  bit-identical, although F's feature weights retained their random initial
  values, and F_beta's fixed feature weights are all zero.
* The most direct reading of those facts is that the feature vector the
  readout received was zero throughout these episodes, so F's feature weights
  received no gradient and both readouts behaved as bias-only policies. This
  explains the identical episodes and is consistent with the zero-motor,
  collision-terminated behaviour reported for Pilot 1.
* This is an **observation about the trained outcome**, not evidence that the
  artifacts are invalid. It does mean the six artifacts are not behaviourally
  distinguishable between F and F_beta, so Pilot 2-C's F/F_beta-dependent
  checks would currently have little or no discriminating power. No additional
  episode was run to diagnose the zero-feature stream, because D5 authorises
  exactly 120 training episodes and nothing here authorises more.

## 9. Limitations

* These are trained readouts, not confirmatory evidence; they support no
  scientific claim about C1–C4 or H1–H3 and select no N.
* The Pilot 2-C behavioural identity (A vs A′), the floor, motor silence and
  viability checks are not evaluated here; they belong to Pilot 2-C execution.
* Equivalence rests on one interrupted artifact; the other five were never
  interrupted, so no resume equivalence claim is made for them.
* The F / 9001 provenance record is a corrected record; the original bytes and
  the correction event are preserved beside it.
* The training outcome is behaviourally null with respect to features (section
  8); certification of the artifacts does not imply that Pilot 2-C can
  discriminate F from F_beta.

## 10. Certification statement

The six artifacts under `experiments/results/phase_8/training/` are certified
as the D5-authorised F/F_beta × {9001, 9002, 9003} trained artifacts: 120
episodes, 120 retained checkpoints, `origin/stage = trained`, experimental
evidence, frozen biological substrate, all reloading and verifying, correctly
paired, with the one interrupted artifact resumed from a verified checkpoint
and demonstrated equivalent to an uninterrupted reference. Certification does
**not** authorise Pilot 2-C execution; that remains a separate owner decision.
