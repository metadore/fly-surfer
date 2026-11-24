# Phase 8 — D5/D6 implementation and training report

Date: 2026-11-23. Scope: the owner's D5/D6 directive of 2026-11-22.
Status: **implementation, six-artifact training, B5/B6 recovery, certification
and the final Pilot 2-C preflight are complete. Execution stops at the Pilot
2-C execution authorisation boundary.**

Companion documents:

* `reports/PHASE_8_PILOT2C_TRAINED_ARTIFACT_CERTIFICATION.md` (evidence:
  `…_CERTIFICATION.json`)
* `reports/PHASE_8_PILOT2C_FINAL_PREFLIGHT.md` (evidence:
  `PHASE_8_PILOT2C_FINAL_PREFLIGHT.json`)
* append-only run log: `experiments/results/phase_8/training/pilot_training_log.jsonl`

## 1. Executive summary

* D5 and D6 are recorded and bound to REV4, the Pilot 2-C amendment, D3, D4 and
  the approved proposal by hashes recomputed from disk; D5 re-derives B3 exactly
  (`bc231c79…92a75a143a1f980`). G3 is unchanged (`deviation_recorded`,
  `gate_weakened = false`, 16 certified graph seeds); D6 grants nothing and is
  non-inheritable.
* The pilot training path was implemented and tested: plan builder, production
  runner, trained-artifact writer, and a recovery-capable driver.
* Exactly six F/F_beta artifacts were written under
  `experiments/results/phase_8/training/`: evaluation seeds 9001, 9002, 9003,
  training seeds 1008, 1014, 1005, 20 episodes each, **120 episodes total**, on
  the frozen biological substrate. Every artifact is `origin = "trained"`,
  `stage = "trained"`, `evidence_kind = "experimental"`, and retains all 20
  per-episode exact checkpoints (120 checkpoints).
* One execution attempt failed after F / 9001 episode 1. The run was resumed
  from the verified checkpoint, an uninterrupted reference was run, and the two
  runs were demonstrated equivalent (20 episodes, 12 fields, parameters
  byte-identical). No episode was restarted under a different seed.
* A resume-ledger provenance defect was found and fixed in code (with a
  regression test); the already-written F / 9001 record was corrected
  transparently, preserving the original bytes and appending a log event.
* The complete Phase 8 test suite passes: **530 passed**.
* Certification passes for all six artifacts. The final Pilot 2-C preflight
  loads all six artifacts and passes every technical check but reports
  `executable = false`, solely because the global training gate still refuses
  further training. **No Pilot 2-C episode or floor replay was executed.**
* Observation, not certification: the 120 episodes are behaviourally null.
  All ended by collision with zero motor spikes and no synaptic weight change,
  and F and F_beta produced identical actions/rewards/decision counts in all
  paired episodes with bit-identical trained biases. This limits what a future
  Pilot 2-C can discriminate; it does not invalidate the artifacts.

## 2. Implementation

New/changed modules under `experiments/phase_8/training/`:

* `pilot.py` — builds the exact six-artifact D5 plan, re-derives B3 and refuses
  any deviation from the D5 record.
* `pilot_training.py` — production episode runner and training loop: real
  `CampaignFactory`, real closed loop, one REINFORCE update per episode, B5
  checkpoint after every episode, B6 resume/equivalence. `run_pilot_artifact`
  authorises each artifact through D5, not through the global gate.
* `pilot_artifact.py` — writes `origin = "trained"` artifacts with the fixed
  22-key manifest, parameters and full provenance; rejects synthetic fixtures
  as experimental evidence.
* `execute_d5_pilot.py` — production driver: append-only JSONL log, never
  overwrites an artifact, verifies complete artifacts, resumes interrupted ones
  from the last verified checkpoint, runs an uninterrupted reference and
  writes the equivalence report before writing an artifact.
* `d5.py` — D5/D6 record parsing, scope enforcement and applicability.

D5 authority remains narrow. The global `assert_training_authorized` still
refuses; new modules never widen it. E/E_full, campaign, Pilot 2-C episodes,
floor replays, randomized graphs and frozen-parameter changes remain outside
D5's scope and were not performed.

### 2.1 Defect found and fixed

On resume, the training loop rebuilt its B5 ledger only for the episodes it ran
itself, so a resumed artifact's provenance would list 19 of 20 checkpoints
(episode 1, written before the interruption, was missing). The runner now
rebuilds the ledger for episodes `1..start` from the verified checkpoints and
refuses to resume if any earlier checkpoint is missing. The regression test
`test_resumed_run_ledger_retains_every_checkpoint` covers it.

The preflight's static training-blocker string also still claimed that no
trained artifact existed. It now states the accurate position: D4 declares
B3–B6, D5 authorises only the six artifacts, the global gate still refuses
further training, and loadability is reported under `training_artifacts`.

### 2.2 Tests

* Focused D5/D6 tests: 71 passed
  (`test_phase_8_training_artifacts.py`, `test_phase_8_d5_pilot_training.py`),
  including the new resume-ledger regression test.
* Complete Phase 8 suite: **530 passed** (20 files).
* The real-training-root guard was updated from "the directory must not exist"
  to the durable invariant: if real storage exists, every artifact there must
  have `origin/stage = "trained"` and experimental provenance, so a synthetic
  fixture can never leak into real evidence storage.

## 3. Training execution

| Condition | Eval seed | Train seed | Init seed | Episodes | Checkpoints |
|---|---|---|---|---|---|
| F | 9001 | 1008 | 1350278753 | 20 | 20 |
| F | 9002 | 1014 | 3449218186 | 20 | 20 |
| F | 9003 | 1005 | 3297997184 | 20 | 20 |
| F_beta | 9001 | 1008 | 1849113230 | 20 | 20 |
| F_beta | 9002 | 1014 | 992595534 | 20 | 20 |
| F_beta | 9003 | 1005 | 56964545 | 20 | 20 |

Every checkpoint is schema 2 and carries parameters, optimizer state and
moments, Python/NumPy/PyTorch RNG and the sampler state; the environment is
reconstructed from its B4 episode seed at each episode start and is recorded as
such. All checkpoints verify; all ledger entries are `retained = true`.

### 3.1 Interruption and recovery

The first driver attempt failed after F / 9001 episode 1 with a logging
`KeyError`; the failure is preserved in the append-only log. The checkpoint was
valid, so the run resumed from it with unchanged seed, budget and substrate.
An uninterrupted reference ran separately. `verify_equivalence` compared 20
episodes over 12 fields with no differences
(`exactness_claim = "demonstrated"`).

This certification re-checked equivalence independently from the preserved
reference checkpoints: identical final parameter bytes (`35918eb7…`), identical
trainable and state digests (`bd50cc73…`), identical environment seeds, and
identical metrics in all 20 episodes.

### 3.2 Provenance correction (F / 9001 only)

* Original `training_run.json` preserved as
  `training_run.incomplete_provenance.json` (`a385aabd…`).
* Corrected `training_run.json` (`fd30434b…`) lists all 20 checkpoints and all
  20 optimizer digests; episodes 2–20 are byte-identical to the original
  records, and a `provenance_correction` block records why and what changed.
* Previous execution summary preserved as
  `execution_summary.pre_provenance_correction.json` (`6fea7e1c…`); the current
  summary (`24aca2e5…`) records the corrected hash.
* A `provenance_corrected` event was appended to the log. No parameter, digest,
  episode metric or checkpoint byte changed.

## 4. Certification

All six artifacts reload and verify; the full detail is in the certification
report. In brief:

* all six `origin/stage = trained`, 22-key manifest, width 3, correct model
  kind, one B4 schedule of 20 seeds, budget 20, 20 recorded episodes;
* F/F_beta share the training seed per evaluation seed and have distinct init
  seeds, distinct manifests and distinct trainable digests;
* per-artifact parameter, manifest and provenance hashes are recorded in the
  certification evidence;
* the F / 9001 correction is disclosed with preserved originals;
* the interruption/recovery/equivalence trail is complete and re-verifiable.

## 5. Final Pilot 2-C preflight

The preflight ran once with the explicit D5 pairing and the real memory gate:

* D3 stage authorisation: authorised for the exact grid; amendment bound to
  REV4; no authorization blockers.
* Plan: 54 entries (45 neural + 9 floor), correct arms, seeds and episodes;
  no randomized graph; no contrast estimate.
* All six artifacts load with `require_trained = true`, `complete = true`,
  `missing = []`, `synthetic_allowed = false`.
* Seven frozen inputs and the configuration hash recomputed and recorded.
* Memory: 7.118 GB available of 15.342 GB against the unchanged 4.0 GB gate.
* Results destination `experiments/results/phase_8/pilot2c` is free.
* D6 non-inheritance and G3 preservation confirmed.

`executable = false`. The only blocker is the conservative global-training-gate
statement, not a missing prerequisite. Even if a future preflight returned
`executable = true`, Pilot 2-C execution would still require the owner's
separate explicit authorisation; none was given, so nothing was executed.

## 6. Training-outcome observations and limitations

* **Behaviourally null training.** All 120 episodes ended by collision,
  recorded zero motor spikes, and changed no synaptic weight. At each
  evaluation seed F and F_beta produced identical action counts, rewards and
  decision counts in all 20 episodes, and their trained biases are
  bit-identical; F's feature weights retained their random initial values.
  The most direct reading is that the readout received a zero feature vector
  throughout, so both readouts behaved as bias-only policies. No extra episode
  was run to diagnose this, because D5 authorises exactly 120 episodes.
* **Consequence for Pilot 2-C.** The six artifacts are not behaviourally
  distinguishable between F and F_beta, so the F/F_beta-dependent certified
  properties would have little discriminating power. This is a scientific
  finding about the current world/sensory pipeline, not a certification failure
  and not a reason to alter frozen parameters or thresholds.
* These artifacts support no claim about C1–C4, H1–H3, paired dispersion or
  `sigma_max`; U7 stays open and `n_seeds_selected` stays `null`.
* Equivalence is demonstrated for the one interrupted artifact only.

## 7. Boundary compliance

* No E/E_full run, campaign step, Pilot 2-C episode or floor replay.
* No randomized graph regenerated, read or used; no graph-dependent stage.
* No modification of REV4, D1–D4, Pilot 1 records, historical results, frozen
  parameters, statistical constants, hypotheses or contrasts.
* No file deleted or historical evidence overwritten; new evidence is in new
  files or the append-only log, with originals preserved beside corrections.
* No Git operation performed.

## 8. Next boundary

The next action is a separate owner decision: whether to authorise Pilot 2-C
execution in light of (a) the certified artifacts and passing technical
preflight, and (b) the behaviourally null training outcome above. Until that
authorisation is given, no Pilot 2-C episode or floor replay will run.
