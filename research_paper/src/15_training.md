# Chapter 15. D5/D6: Training and Artifact Certification

## 15.1 Authorisation for exactly six artifacts

The training stage of Phase 8 required its own owner decision. Decision record D5, dated 2026-11-22, authorises the production of exactly six trained artifacts: conditions F and F_beta at evaluation seeds 9001, 9002, and 9003, twenty episodes each, 120 episodes in total. It binds the request to REV4, the Pilot 2-C amendment, D3, D4, and the approved proposal by hashes recomputed from disk, and it re-derives the B3 entry digest exactly rather than copying it forward. Decision record D6 accompanies it as a non-inheritable boundary: it grants no additional capability, authorises no graph access, construction, or substitution, leaves the G3 memory deviation recorded rather than discharged, and confirms that the sixteen certified randomisation seeds are unchanged.

Both records are narrow by construction. The implementation modules authorise each artifact through D5, not through the global training gate, and the global gate still refuses further training. The following remain outside D5's scope and were not performed: conditions E or E-full, any campaign step, any Pilot 2-C episode, any floor replay, any randomized graph, and any change to a frozen parameter or statistical constant. The distinction matters because the existence of trained artifacts can easily be misread as progress toward the confirmatory campaign. It is not. Six artifacts at a 20-episode budget are a pilot-scale training exercise, and no contrast C1–C4 is estimated from them.

## 15.2 What was trained, and what was not

Condition F keeps the connectome and every synaptic weight exactly as in condition A and trains only the readout that maps the declared motor-population block to an action. The readout sees three features — the active fraction of the LEFT, RIGHT, and JUMP pools — and produces four logits, one for each of LEFT, RIGHT, JUMP, and NO_ACTION. It has no access to the seven sensory features, the game state, or earlier actions. Its weight matrix is therefore four by three, twelve feature weights, plus a four-element output bias.

The initialisation is asymmetric in a way that later matters. The bias is initialised to zero for every artifact. The feature weights are drawn from a normal distribution with standard deviation 0.01 using the artifact's init seed. During a training episode the controller samples an action from the categorical softmax policy; at the end of the episode a single REINFORCE update is applied. Evaluation episodes use the argmax action and a frozen readout. Training and evaluation seeds are disjoint: the training seeds are 1008, 1014, and 1005, while the evaluation seeds that identify the artifacts are 9001, 9002, and 9003.

Control F_beta is the bias-only readout. Its forward pass never reads the feature vector, its feature weights are a constant zero buffer excluded from the optimizer, and its only trainable parameters are the four output biases. The action distribution of F_beta is therefore provably independent of motor activity, which is exactly what makes it a state-independence control.

Nothing in this stage changes the neural substrate. The training signal updates the readout parameters, not synaptic weights; no three-factor rule, eligibility trace, or structural change is applied. The substrate weight fingerprint is expected to be identical before and after every episode, and it is.

## 15.3 The six-artifact grid and its execution

Table 17 reports the six artifacts and their certification digests. Each artifact has twenty episodes, twenty exact checkpoints, and one checkpoint after every completed episode.

**Table 17.** D5 trained artifacts. All six run on the frozen biological BANC t5 substrate with fixed synaptic weights. Evaluation seed identifies the artifact; training seed drives the episode seeds and the REINFORCE sampling; checkpoints are per-episode schema-2 checkpoints. The equivalence column records the one interrupted artifact for which an uninterrupted reference run was compared. Init seeds are 1350278753, 3449218186, and 3297997184 for F at 9001–9003, and 1849113230, 992595534, and 56964545 for F_beta at 9001–9003. Data source: `experiments/results/phase_8/training/`; full machine-readable table in `tables/T11_d5_training_artifacts.csv`.

| Condition | Eval seed | Train seed | Checkpoints | Episodes | Trainable = state digest | Parameters SHA-256 | Equivalence |
|---|---:|---:|---:|---:|---|---|---|
| F | 9001 | 1008 | 20 | 20 | `bd50cc73…9a8883` | `35918eb7…42efb6` | demonstrated |
| F | 9002 | 1014 | 20 | 20 | `e1c25034…dadce` | `a71b47a3…5d95` | not required |
| F | 9003 | 1005 | 20 | 20 | `2e188b78…d9961` | `3ad5e6be…d0e17` | not required |
| F_beta | 9001 | 1008 | 20 | 20 | `0975693e…1f76e` | `1030fe14…15a5` | not required |
| F_beta | 9002 | 1014 | 20 | 20 | `5f03c88b…f5b9` | `41abbe4d…e6a8` | not required |
| F_beta | 9003 | 1005 | 20 | 20 | `b157ae1e…a120` | `b1cd7e70…6e85` | not required |

Every checkpoint is schema 2 and carries the parameters, optimizer state and moments, the Python, NumPy, and PyTorch random-number states, and the sampler state. The environment is reconstructed from its B4 episode seed at the start of each episode and is recorded as such, so the episode does not depend on the order in which artifacts were run. All 120 checkpoints verify, and every ledger entry records `retained = true`.

Figure 32 shows the artifact-by-checkpoint matrix. Its purpose is not to display a performance trend but to make the completeness visible: six artifacts, twenty episodes each, every cell present and verified. The one corrected provenance record, F/9001, is marked in the caption rather than hidden.

![Figure 32. D5 artifact and checkpoint matrix. Six artifacts (F and F_beta at evaluation seeds 9001, 9002, 9003), twenty per-episode checkpoints each, 120 in total. Every checkpoint verifies and every ledger entry is retained. The F/9001 provenance record was corrected with the original bytes preserved beside it. Data source: the six `training_run.json` files under `experiments/results/phase_8/training/`.](figures/F26_d5_checkpoint_matrix.png)

The artifacts were written under `experiments/results/phase_8/training/` with the fixed 22-key manifest, `origin = "trained"`, `stage = "trained"`, and `evidence_kind = "experimental"`. The writer rejects synthetic fixtures as experimental evidence, and the real-training-root guard requires that if real storage exists, every artifact in it must carry trained origin, trained stage, and experimental provenance. These checks are implementation safeguards, not scientific results; they exist so that a fixture cannot be mistaken for a trained artifact later.

## 15.4 Interruption, recovery, and equivalence

The first execution attempt failed after F/9001 episode 1 with a logging `KeyError`. The failure is preserved in the append-only log. The checkpoint itself was valid, so the run resumed from it with an unchanged seed, budget, and substrate. No episode was restarted under a different seed.

An uninterrupted reference run was executed separately. `verify_equivalence` compared the resumed and uninterrupted runs over twenty episodes and twelve fields and found no differences; the exactness claim is `demonstrated`. The certification later re-checked this independently from the preserved reference checkpoints: final parameter bytes are identical (`35918eb7…`), trainable and full-state digests are identical (`bd50cc73…`), environment seeds are identical, and all twenty episode metrics are identical.

The interruption exposed a real implementation defect. On resume, the training loop rebuilt its B5 ledger only for the episodes it had run itself, so a resumed artifact's provenance would have listed nineteen of twenty checkpoints; the checkpoint written before the interruption was missing. The runner now rebuilds the ledger for all earlier episodes from the verified checkpoints and refuses to resume if any earlier checkpoint is missing. A focused regression test, `test_resumed_run_ledger_retains_every_checkpoint`, covers the case. Equivalence is demonstrated for this one interrupted artifact only; the other five were never interrupted and no equivalence claim is made for them.

## 15.5 Provenance correction for F/9001

Because the defect was found after F/9001 had already been written, its `training_run.json` contained the incomplete ledger. The correction was performed transparently rather than by rewriting history. The original file is preserved as `training_run.incomplete_provenance.json` with SHA-256 `a385aabd…`. The corrected `training_run.json` has SHA-256 `fd30434b…` and lists all twenty checkpoints and all twenty optimizer digests. A `provenance_correction` block records the kind of correction, the original and corrected file, the twenty re-verified checkpoints, and the note that no parameter, digest, episode metric, or checkpoint byte changed. A `provenance_corrected` event was appended to the log. The prior execution summary is preserved as `execution_summary.pre_provenance_correction.json` (`6fea7e1c…`), and the current summary (`24aca2e5…`) records the corrected hash.

This is the only historical record altered during the training stage, and it was altered by adding a corrected copy beside a preserved original, not by overwriting. The distinction is the same one applied to the Pilot 1 spike-total discrepancy in Chapter 13: the paper reports the corrected state and discloses the original, because a reader must be able to reconstruct both what happened and what was repaired.

## 15.6 Certification of the six artifacts

Certification is a technical check of artifact identity, schema, pairing, and recovery. It is not a test of learning, and a passing certification is not evidence that anything was learned.

All six artifacts reload and verify. Each has the 22-key manifest, `origin = "trained"`, `stage = "trained"`, output width `n_features = 3`, the correct model kind (`linear` for F, `bias_only` for F_beta), one B4 schedule of twenty environment seeds, budget 20, twenty recorded episodes, twenty ledger checkpoints with `integrity_verified = true` and `retained = true`, and twenty matching optimizer digests. The per-artifact parameter, manifest, and provenance hashes are recorded in the certification evidence and were recomputed from disk during certification.

The pairing is exact. F and F_beta share the training seed at each evaluation seed — 1008, 1014, and 1005 — and each has its own distinct init seed, so all six init seeds differ. Each pair has a distinct trainable digest and a distinct manifest file, and the B3 per-entry digests are distinct per evaluation seed while D5's global B3 digest is `bc231c79…92a75a143a1f980`. One detail is worth recording: F_beta's initial parameter digest is identical at all three seeds (`f94b54c9…f058e`) because its bias-only readout starts from a fixed zero vector and its forward pass ignores features, so its initialisation is seed-independent by construction. Its trained digests and files still differ by seed, because the reward stream differs. Artifact identity is therefore `(condition, evaluation seed)`, never a parameter value.

None of this certifies a contrast. The certification report states explicitly that it certifies nothing about C1–C4, H1–H3, paired dispersion, or `sigma_max`. U7 remains open and `n_seeds_selected` remains null.

## 15.7 The training outcome is behaviourally null

The substantive result of the stage is that all 120 episodes are behaviourally null. Every episode ended by collision, recorded zero motor-population spikes, and changed no synaptic weight; `weights_before` equals `weights_after` in every record. This is consistent with Pilot 1 and with the bottleneck analysis of Chapter 14, and it is the expected consequence of a silent motor channel rather than a surprise.

The readout comparison sharpens the point. At each evaluation seed, F and F_beta produced identical action counts, rewards, and decision counts in all twenty episodes, and their trained biases are bit-identical. F's feature weights retained their random initial values; F_beta's fixed feature weights are all zero. The most direct explanation is mechanical. The readout sees only the three motor active fractions. With zero motor spikes, that feature vector is identically zero at every decision, so the logits reduce to the bias, and F and F_beta implement the same policy whenever they are driven by the same sampling seed. Because the features are always zero, the gradient with respect to the feature weights is zero and those weights never move. The biases start at zero in both conditions and receive the same update, so they remain identical. The two conditions collapse onto the same bias-only policy.

This is an observation, not a certification failure, and no extra episode was run to diagnose it, because D5 authorises exactly 120 episodes. Its consequence for the next stage is direct: the six artifacts are not behaviourally distinguishable between F and F_beta, so any F/F_beta-dependent certified property has little discriminating power in a future Pilot 2-C. That is a statement about the current world and sensory pipeline, not a reason to alter a frozen parameter or threshold.

Figure 31 shows the reward trajectories. The curves for F and F_beta coincide at every episode and every seed, which is the visual form of the identity just described.

![Figure 31. D5 training reward trajectories for F and F_beta across the three evaluation seeds. Each panel is one evaluation seed; the F and F_beta curves coincide because the two readouts produced identical actions and rewards in all twenty paired episodes. The flat coincidence is a consequence of a zero motor feature vector, not evidence that the readouts learned the same policy. Data source: `experiments/results/phase_8/training/{F,F_beta}/seed_{9001,9002,9003}/training_run.json`.](figures/F25_d5_trajectories.png)

## 15.8 Preflight and the execution boundary

A final Pilot 2-C preflight ran once with the explicit D5 pairing and the real memory gate. The D3 stage authorisation was valid for the exact grid; the amendment was bound to REV4; and there were no authorisation blockers. The plan contained 54 entries — 45 neural (A, B, F, F_beta, and A_prime at three seeds and three episodes each) plus 9 floor — with no randomized graph and no contrast estimate. All six artifacts loaded with `require_trained = true`, `complete = true`, `missing = []`, and `synthetic_allowed = false`. Seven frozen inputs and the configuration hash were recomputed and recorded. Memory reported 7.118 GB available of 15.342 GB against the unchanged 4.0 GB gate, and the destination `experiments/results/phase_8/pilot2c` was free. D6 non-inheritance and G3 preservation were confirmed.

The preflight nevertheless returned `executable = false`. The only blocker was the conservative global-training-gate statement, not a missing prerequisite. The report is careful about what that means: even a future preflight returning `executable = true` would not authorise execution, because Pilot 2-C execution requires the owner's separate explicit authorisation. None was given at that point, so no Pilot 2-C episode and no floor replay was executed. Chapter 16 describes what happened when that separate authorisation was later granted.

## 15.9 What the stage established and what it did not

The stage established the training infrastructure. It built a plan constrained to the six authorized artifacts, a production runner with a real campaign factory and a real closed loop, a trained-artifact writer with a fixed manifest and provenance, and a recovery-capable driver that never overwrites an artifact and verifies completeness before writing. It produced 120 exact checkpoints, demonstrated equivalence for the one interrupted run, corrected a provenance defect without discarding the original bytes, certified all six artifacts against schema, pairing, and recovery criteria, and executed a complete preflight. The focused D5/D6 tests passed 71, and the complete Phase 8 suite passed 530.

It did not establish learning. The substrate weights never changed, the motor pools never spiked, and the readout never saw a nonzero feature vector. It did not establish a benefit of the trained readout over its bias-only control, because the two were identical in behaviour. It did not estimate a contrast, test a hypothesis, estimate dispersion, select a seed count, or move toward the N=16 campaign. It is not evidence about a fly, and the certification pass must not be described as biological learning.

The stage is nevertheless informative in a negative direction. It shows that the motor bottleneck propagates through training: a readout cannot learn a state-dependent policy from a feature vector that is always zero, however correctly the training loop is implemented. That is the same structural boundary identified in Chapters 13 and 14, now observed at the learning stage rather than only at the decoding stage.

## 15.10 Summary

D5 authorised exactly six F/F_beta artifacts, twenty episodes each, on the frozen biological substrate; D6 granted nothing and preserved the G3 deviation record. All 120 episodes executed and all 120 checkpoints verify. One interrupted run was resumed, shown equivalent to an uninterrupted reference, and repaired by a documented provenance correction that preserves the original bytes. Certification passed for all six artifacts on identity, schema, pairing, and recovery, and the final preflight passed every technical check while remaining non-executable solely because of the global training gate. The scientific outcome is a behaviourally null training set: zero motor spikes, zero synaptic weight change, and F/F_beta behavioural identity explained by a permanently zero motor feature vector. The next chapter reports the 54-entry Pilot 2-C execution and the narrow set of descriptive claims that execution could certify.
