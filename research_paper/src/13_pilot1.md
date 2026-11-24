# Chapter 13. Pilot 1: A Viability and the Motor Floor

## 13.1 What Pilot 1 was authorised to do

Pilot 1 was the first executable stage of the Phase 8 design. Its scope was deliberately narrow: condition A only, three seeds (9001, 9002, 9003), three episodes per seed, nine episodes total. It used the biological BANC substrate with fixed weights and the unchanged threshold decoder. It did not use a randomized graph, a trained artifact, plasticity, training, or any other condition. It did not estimate C1–C4, did not test H1–H6, and was not merged into the campaign dataset.

The narrow scope was enforced by the authorization layer, not merely stated in a plan. The owner decision record D2, dated 2026-11-20, records the exact grid and the negative capability flags: no randomized graph, no trained artifact, no parameter modification, and no weakening of random-graph certification. The stage authorization code hard-codes the nine-entry grid so that a changed configuration cannot widen it, validates D2's hash against the REV4 file on disk, and leaves every other stage blocked. Pilot 2, training, composition, and the campaign cannot inherit the exemption. The record is a stage gate, not a protocol amendment; REV4's hash is unchanged.

The purpose was to answer one question: does the A pipeline run end to end on the frozen substrate and produce a measurable behavioural result? It was not designed to estimate an effect. Three seeds and three episodes are a viability sample, and the report says so in its own terms.

## 13.2 Execution and provenance

The pilot executed through the production path on 2026-11-20, from 10:58:51Z to 11:04:48Z, with a wall time of 357.0 s. All nine planned episodes ran. The run summary records `executed = true`, `rows_stored = 9`, `rows_executed = 9`, `planned = 9`, `complete = true`, `evidence_kind = pilot`, `experimental_evidence = true`, `estimates_contrasts = false`, and `merged_into_campaign = false`. The episode rows are in `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`, SHA-256 `ee479e5b…68f9`; the driver record is `reports/PHASE_8_PILOT1_EXECUTION.json`, SHA-256 `d3392b9c…e1e`.

Each row carries condition A, role reference, `training = false`, status ok, seven frozen-input hashes, and three configuration hashes. The production runner loaded the BANC world lazily and recorded provenance before each episode. The run-start memory gate reported 5.745 GiB available against a 4.0 GiB gate. Passive sampling at 2 s intervals produced 177 samples, a maximum process RSS of 0.3725 GiB, and a minimum system-available value of 4.1997 GiB, so the memory gate held throughout.

The run did not exceed the 900-update cap in any episode: all nine terminated by collision, with `truncated = false`. No fallback, unmapped action, or invalid output was recorded. Every decision was the decoder's neutral state, produced by the threshold rule rather than by an error path.

## 13.3 Nine episode results

Table 16 reports the nine episodes. Figure 27 shows survival and spike counts.

**Table 16.** Pilot 1 nine-episode A-viability grid. All rows are condition A on the frozen BANC t5 substrate with fixed weights and the unchanged decoder. Survival is game updates completed before collision; neural steps are 0.5 ms simulation steps; motor spikes are the sum over the LEFT, RIGHT, and JUMP pools. Every episode ended by collision and none reached the 900-update cap. Data source: `experiments/results/phase_8/pilot1/pilot1/episodes.jsonl`; full machine-readable table in `tables/T10_pilot1_episodes.csv`.

| Seed | Episode | Environment seed | Game updates | Neural steps | Total spikes | Motor spikes | Reward | Termination |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 9001 | 0 | 563774599 | 323 | 10,767 | 4,764 | 0 | 5.22 | collision |
| 9001 | 1 | 2911696168 | 620 | 20,667 | 14,348 | 0 | 10.19 | collision |
| 9001 | 2 | 4240939637 | 323 | 10,767 | 4,764 | 0 | 4.22 | collision |
| 9002 | 0 | 2632356062 | 620 | 20,667 | 14,911 | 0 | 7.19 | collision |
| 9002 | 1 | 307060235 | 426 | 14,200 | 8,396 | 0 | 3.25 | collision |
| 9002 | 2 | 4241804999 | 620 | 20,667 | 13,139 | 0 | 8.19 | collision |
| 9003 | 0 | 2839813884 | 213 | 7,100 | 2,850 | 0 | 3.12 | collision |
| 9003 | 1 | 756850162 | 426 | 14,200 | 7,856 | 0 | 4.25 | collision |
| 9003 | 2 | 2981106662 | 213 | 7,100 | 2,852 | 0 | 2.12 | collision |

The totals are 3,784 game updates, 126,135 neural steps, and 47.75 total reward. Survival ranges from 213 to 620 updates, or about 3.55 s to 10.33 s of game time at 60 updates per second. Reward ranges from 2.12 to 10.19. The values are descriptive of this nine-episode sample; they are not an estimate of a condition effect and should not be compared as if the seeds were independent replicates of a campaign.

![Figure 27. Pilot 1 nine-episode outcomes on the frozen BANC substrate. Panel (a): game updates survived before collision for each seed and episode; all nine end by collision, with survival between 213 and 620 updates. Panel (b): total neural spikes per episode, between 2,850 and 14,911; motor-population spikes are zero in every episode. The row values sum to 3,784 updates and 73,880 spikes. Data source: experiments/results/phase_8/pilot1/pilot1/episodes.jsonl.](figures/F21_pilot1_episodes.png)

## 13.4 The spike total: 72,880 and 73,880

The nine episode rows sum to **73,880** total spikes. The execution report's prose totals state **72,880**, and the same figure appears again in the report's discussion of the zero-motor result. The difference is exactly 1,000 spikes, or about 1.35% of the row sum. It is a transcription error in the report's prose, not a difference between the data and the report about which episodes ran: all nine rows are present, their other fields are internally consistent with the summary, and the row values are the recorded measurements.

This paper uses **73,880** everywhere it reports the Pilot 1 total, including Table 16, the abstract, Chapter 17, and the consolidated tables. The original historical report is preserved unchanged and is not silently corrected. The discrepancy is disclosed here so that a reader comparing the paper with the report sees the same episode rows and understands why the prose totals differ. The figure's own source note records the same relationship between the rows and the report prose.

## 13.5 Zero motor output

Every one of the 3,784 decisions was NO_ACTION. The LEFT, RIGHT, and JUMP pools recorded zero spikes in every episode, `windows_with_motor_spikes` is 0 throughout, and the decoder fallback dictionary is empty. The zero is not an error fallback: the decoder was called, it evaluated the pools, no pool met the five-spike, three-active-neuron, 0.20-active-fraction gate, and it returned the neutral state by the declared rule.

The network was not silent or dead. Total spike counts range from 2,850 to 14,911 per episode, so the simulation was active and the recorder captured it. The weight fingerprint `4923f0cd…945d5` is identical before and after every episode, as required for a fixed-weight condition; the structural and initial digests also did not change. Condition A did what it was defined to do. It simply never produced a motor action.

This is a substantive negative result for the A configuration. It is consistent with the Phase 7 closed-loop result and with the earlier Phase 4 sensory-to-motor findings, but it is not evidence about a fly, and it must not be re-described as a biological motor result. It also does not identify which part of the chain failed. The next chapter takes the same run apart at the level of first-hop synapses and locates the current shortfall.

## 13.6 Integrity, freeze status, and documentation nuances

The pilot is **not freeze-ready**, and the reason is external to the episode measurements. A read-only post-run check of the 37-file protected baseline found 35 matching files and two drifts: README.md, whose drift was already present during Phase 7, and `motor/__init__.py`, whose current content was introduced by commit `3c74ae8` on 2026-11-19, before this execution. Because `motor/__init__.py` is a non-README failure, the integrity check returns `pass = false`, and the run manifest records `integrity.checked = false`. The drift was not created by the D2 implementation or by Pilot 1, and it was not changed to make the pilot pass. Resolving it requires an authorised amendment or a compliant restoration, neither of which was performed. The episode rows remain valid measurements of the model; the protocol's publication gate is not passed.

The pilot's test record is consistent with that reading. The D2 authorization tests were 18 passed, the affected Phase 8 modules were 284 passed, and the full suite was 1,503 passed, 3 skipped, and 6 failed. The six failures pre-date this work and are unrelated to Pilot 1: three protected-hash checks report the README drift, two smoke-mode labels report `SMOKE INVALID` instead of `SMOKE ONLY`, and one C0 cache assertion fails. No test executes a real episode.

Two documentation nuances are recorded rather than rewritten. First, `pilot_plan.json` is the pre-execution plan copy and still says `executed = false`; the authoritative records are `pilot_summary.json`, the manifest, and the nine rows, all of which record the run as executed. Second, the report's prose spike total is the 72,880 described in Section 13.4. Neither nuance changes an episode value, and neither is used to weaken or strengthen a scientific claim.

## 13.7 What Pilot 1 established and what it did not

Pilot 1 established software viability. The frozen BANC substrate loads and runs inside the controlled game environment; the provenance chain is complete and self-consistent; the fixed-weight condition holds its fingerprint; the recorder captures spikes, actions, rewards, survival, and terminations without fallbacks or errors. It also established the floor: in this configuration, on these seeds, the decoder never selected a motor action, and the game ended by collision in every episode.

It did not establish a sensory-to-motor transformation, a biological motor code, a learning effect, or a condition contrast. Three seeds and three episodes are not an inference sample; the pilot cannot estimate C1–C4 and cannot test H1–H6. It cannot say whether the floor is caused by the sensory mapping, the current scale, the verified-only sign policy, the decoder threshold, or some combination. Those are hypotheses for the bottleneck analysis in Chapter 14, and the protocol forbids tuning any of them after seeing this result without a new authorised analysis.

## 13.8 Summary

Pilot 1 ran the A condition nine times on the frozen BANC substrate. All nine episodes executed, all ended by collision between 213 and 620 updates, and all 3,784 decisions were NO_ACTION. The network produced 73,880 spikes by the row sum and zero motor spikes. The execution report's prose says 72,880; the rows are authoritative and the original report is preserved unchanged. The pilot is operationally viable and scientifically null on motor output, and it is not freeze-ready because of a pre-existing protected-baseline drift. The next chapter explains, synapse by synapse, why the current that produced those spikes did not reach a single motor neuron.
