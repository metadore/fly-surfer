# Phase 8 Condition C randomized-graph campaign (campaign seeds 1–16)

**Date:** 2026-11-17
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (146,643 bytes)
**Scope:** build and independently certify the sixteen degree- and sign-preserving randomized BANC
graphs that Condition C requires, verify them as a set, and verify the Condition C loader.
**U18 status:** target exchange is **PROPOSED — not approved** (REV4 §12).
**What this report is not:** no episode, pilot, training run or campaign was executed. A
certificate is a statement about a graph file, not authorisation to collect data.

---

## 1. Status at a glance

| Item | Result |
|---|---|
| Seeds required | 16 (campaign seeds 1–16) |
| Seeds generated | **16** |
| Seeds individually certified against R1–R18 | **16** |
| Seeds that failed a mandatory gate | **0** |
| Seeds blocked by resources mid-run | **0** |
| Distinct graph digests / graph files / certificates | 16 / 16 / 16 |
| Deterministic regeneration reproduces the certified digest | **16 / 16** |
| Seed 1 artifacts unchanged | yes |
| Condition C loader accepts every certified record | **16 / 16** |
| Protocol-compliant with the REV4 §9.3 memory gate | **no — deviation recorded (§2)** |
| G3 complete | **no** (§12 states why) |

All sixteen graphs are real BANC-scale builds (172,433 nodes, 1,535,710 edges each), each one
derived independently from the frozen original graph, each certified by its own certificate.

---

## 2. Protocol compliance: the §9.3 memory gate (deviation recorded)

This section is first because it changes how every other number in this report must be read.

REV4 §9.3 states that the gate is **4 GB of free physical memory**, "not weakened, rounded down
or waived", and that while the machine is below it there may be

- **no BANC-scale graph randomisation**;
- no full campaign simulation;
- no training run;
- no memory-intensive test suite.

Free physical memory recorded in the sixteen builds ranged from **1.63 GB to 2.93 GB** (preflight
reading; the low-water marks during construction and the runner are 1.628 GB and 1.936 GB, and the
seed loop's pre-start check never exceeded 3.43 GB). It was below 4 GB at every preflight and during
every build. Graph construction is explicitly named in the blocked list, so **the sixteen
randomisations in this report did not satisfy §9.3**. They are a recorded deviation from the
protocol's operational constraint, not compliant runs.

What is and is not true about the runs:

| Question | Answer |
|---|---|
| Did any build exhaust memory or destabilise the machine? | No. Peak RSS was 527.3 MB (construction) / 433.3 MB (runner); the lowest free-memory sample was 1.628 GB. |
| Did the documented construction preflight pass every time? | Yes — `allowed: true` for all 16 seeds against the 0.75 GB construction floor recorded in each manifest. |
| Was the 4 GB figure redefined, relaxed or reported as met? | No. `campaign_seed_summary.json` records `compliance.status = "deviation_recorded"`, the observed range, and `gate_weakened: false`. |
| Does this report claim the seed set is campaign-ready? | No. §12 lists what is still missing. |

The distinction matters: the *safety* rationale behind §9.3 (do not start work the machine cannot
carry) held — the work fit in roughly 0.5 GB with at least 1.6 GB free — but the *rule as written*
was not met. Reporting the builds as compliant would require either a protocol amendment or a
rerun on a machine with ≥ 4 GB free, and one of those is the user's decision, not this report's.
Pending that decision the seed set is described as **certified, with a recorded §9.3 deviation**.

No threshold, gate, algorithm parameter or seed derivation was changed to accommodate the memory
situation; the builds were not made cheaper or shorter.

## 3. Authorities and frozen inputs

Every identity below was recomputed from the file on disk, not copied from an earlier report.

| Artifact | Bytes | SHA-256 |
|---|---|---|
| REV4 protocol | 146,643 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Original BANC graph `datasets/processed/banc_v888/banc_graph_t5.npz` | 13,484,120 | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| BANC node table `banc_nodes.csv.gz` | 3,800,401 | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Synapse policy `configs/banc_synapse_policy.yaml` | 5,198 | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |

`certify_banc.py` refuses to start if any of these drift (exit code 4). The original graph was
opened read-only and hashed before and after the campaign summary was built; it is unchanged.

### 3.1 Seed derivation

The structure seed for campaign seed *N* is the REV4 §6.3 structure-stream value

```
SeedSequence([master_seed = 20261116, campaign_seed = N, structure_stream_code = 4])
```

`master_seed` comes from `configs/phase_8/campaign.yaml`. Each certificate's `R18` block records
the entropy triple, the derived seed and the seed actually used, and `derivation_verified` is
`true` for all sixteen — checked independently here against the recorded seed.

| Campaign seed | Structure seed | Campaign seed | Structure seed |
|---|---|---|---|
| 1 | 1,258,589,452 | 9 | 2,234,464,388 |
| 2 | 3,374,522,250 | 10 | 3,077,258,373 |
| 3 | 3,857,339,379 | 11 | 1,595,021,147 |
| 4 | 524,041,369 | 12 | 2,823,895,210 |
| 5 | 2,156,741,586 | 13 | 1,879,306,153 |
| 6 | 1,071,266,342 | 14 | 3,185,680,544 |
| 7 | 1,410,933,494 | 15 | 2,692,053,485 |
| 8 | 1,319,366,095 | 16 | 3,709,422,021 |

### 3.2 What was frozen

Nothing in the generator was touched between seed 1 and seeds 2–16: same module
(`experiments/phase_8_random/target_exchange.py`), same U18 option (a) parameterisation, same
10 × `n_edges` = 15,357,100 accepted target swaps, same rejection rules (duplicate pair,
self-edge, no-change, out-of-range), same `CANDIDATE_BLOCK = 4096` candidate stream, same packed
`int64` key representation, same node set, same sign derivation through the frozen synapse policy,
same integer weight handling, same R1–R18 thresholds, same certification logic. No parameter was
tuned after seeing seed 1's result. No seed was started from another seed's randomized graph: every
seed rewires the original graph independently, and `R17` within each build compares two independent
builds of *that* seed.

---

## 4. Generation run

Seeds 2–16 were produced by one sequential loop
(`experiments/results/phase_8_random/logs/run_seeds_2_16.sh`), one `certify_banc` process at a
time, never concurrently, each writing to its own namespace:

```
python -m experiments.phase_8_random.certify_banc --campaign-seed <N>
```

The loop printed free physical memory before each seed, aborted if it fell below 1.0 GB (it never
did), and appended `=== seed <N> exit=<rc> ===`. Log:
`experiments/results/phase_8_random/logs/seeds_2_16.log`.

| Observation | Value |
|---|---|
| Seeds attempted by the loop | 15 (2–16) |
| Exit code 0 | 15 |
| Non-zero exit codes | 0 |
| Loop wall time | 11:56:03 → 12:26:13 (30 min 10 s) |
| Seed 1 namespace | never written; `certify_banc` refuses an occupied namespace (exit 5) |

`RUN_INCOMPLETE` markers were removed only after each seed's certificate, manifest and results were
written; `campaign_summary.json` reports `marker_present: false` for all sixteen.

## 5. Individual certification

Each seed was certified by `certify_banc.py`, which builds the graph twice, compares the builds
(R17), evaluates R1–R18, and refuses to write a certificate unless every mandatory gate passes.
Mandatory gates are R4, R5, R6, R7, R8, R9, R9b, R10, R11, R12, R13, R14 and R17.

| Seed | Swaps attempted | Accepted | R4 rewired | R5 Jaccard | R5 ∩ | R13 active mean | R14 max Δ | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | 15,456,122 | 15,357,100 | 0.997916 | 0.00104295 | 3,200 | 0.000336582 | 5.12e-05 | pass |
| 2 | 15,456,798 | 15,357,100 | 0.997927 | 0.00103740 | 3,183 | 0.000297476 | 5.84e-05 | pass |
| 3 | 15,455,835 | 15,357,100 | 0.997841 | 0.00108080 | 3,316 | 0.000329995 | 5.61e-05 | pass |
| 4 | 15,457,013 | 15,357,100 | 0.997944 | 0.00102892 | 3,157 | 0.000346996 | 6.43e-05 | pass |
| 5 | 15,455,462 | 15,357,100 | 0.997854 | 0.00107427 | 3,296 | 0.000342974 | 6.17e-05 | pass |
| 6 | 15,456,328 | 15,357,100 | 0.997895 | 0.00105339 | 3,232 | 0.000346592 | 6.92e-05 | pass |
| 7 | 15,456,448 | 15,357,100 | 0.997935 | 0.00103349 | 3,171 | 0.000307974 | 5.74e-05 | pass |
| 8 | 15,456,217 | 15,357,100 | 0.997875 | 0.00106351 | 3,263 | 0.000329794 | 3.00e-05 | pass |
| 9 | 15,456,607 | 15,357,100 | 0.997889 | 0.00105665 | 3,242 | 0.000347146 | 5.48e-05 | pass |
| 10 | 15,456,014 | 15,357,100 | 0.997887 | 0.00105763 | 3,245 | 0.000352877 | 4.99e-05 | pass |
| 11 | 15,456,917 | 15,357,100 | 0.997849 | 0.00107656 | 3,303 | 0.000333333 | 4.50e-05 | pass |
| 12 | 15,456,291 | 15,357,100 | 0.997904 | 0.00104915 | 3,219 | 0.000335539 | 4.70e-05 | pass |
| 13 | 15,456,097 | 15,357,100 | 0.997919 | 0.00104165 | 3,196 | 0.000341200 | 4.08e-05 | pass |
| 14 | 15,456,161 | 15,357,100 | 0.997830 | 0.00108635 | 3,333 | 0.000305521 | 5.32e-05 | pass |
| 15 | 15,456,106 | 15,357,100 | 0.997890 | 0.00105600 | 3,240 | 0.000349828 | 4.01e-05 | pass |
| 16 | 15,455,887 | 15,357,100 | 0.997859 | 0.00107166 | 3,288 | 0.000315306 | 5.64e-05 | pass |

Gates that are structurally identical for every seed, all verified per seed (not assumed):

| Gate | Result for all 16 |
|---|---|
| R4 (rewired fraction ≥ 0.99) | 0.997830 – 0.997944 |
| R5 (Jaccard ≤ 0.01) | 0.0010289 – 0.0010863; residual intersection 3,157 – 3,333 pairs |
| R6 / R7 (exact per-node out/in degree) | maximum change 0 on every node; sums 1,535,710 = expected |
| R8 (transmitter sign preserved) | 683,100 signed edges and 8,426,168 signed synapses unchanged; 852,610 unsigned edges unchanged; per-node sign vectors, per-node codes and per-edge reordering all equal |
| R9 (weight multiset) | exactly equal; sum 18,552,546; min 5; max 913 |
| R9b (per-source weight profile) | per-source weight multiset and out-degree profile exactly equal |
| R10 / R11 (duplicates / self-edges) | 0 / 0 |
| R12 (CSR invariants) | true |
| R13 (mean out-neighbour Jaccard ≤ 0.01) | 0.000297 – 0.000353 over 130,709 active nodes; 41,724 nodes isolated in both graphs are excluded from the gated statistic; the literal all-node value (about 0.24) is reported, not gated |
| R14 (rewiring-distance plateau < 1e-4) | 3.00e-05 – 6.92e-05 over 31 tail samples |
| R17 (two independent builds identical) | identical digest for every seed, every time |

Attempt and rejection accounting: accepted swaps were exactly 15,357,100 for all sixteen seeds;
acceptance rate 0.993536 – 0.993636. Rejections were duplicate pairs (95,809 – 97,401), self-loops
(1,005 – 1,100), no-change draws (1,394 – 1,522) and zero out-of-range. Per-seed counters are in
`campaign_seed_summary.json` (`seeds[i].rejected`).

**No seed failed a gate, so no seed needed a rerun and no threshold was reported as met on a
technicality.** R14 is a plateau diagnostic on the rewiring distance only; passing it is not a
mixing proof and no mixing claim is made anywhere in this report.

---

## 6. Structural consequences (reported, not gated)

These numbers follow from target exchange and are recorded as R15/R16 for transparency. They were
not used to tune anything and are not evidence for or against null-model validity.

| Measure | Original | Seeds 1–16 |
|---|---|---|
| Weak components | 24,470 | 24,332 – 24,350 |
| Largest component | 147,759 | 148,055 – 148,091 |
| Reciprocity | 0.115203 | 0.001624 – 0.001802 |
| Degree assortativity | −0.061930 | −0.010141 – −0.011304 |

The residual original-edge intersection (3,157 – 3,333 pairs) is non-zero because a swap can
re-create an original `(src, dst)` pair after its slot was swapped away. The implementation does
not instrument per-swap reversions, so their timing is not characterised.

## 7. Cross-seed validation

`experiments/phase_8_random/campaign_summary.py` was written for this check. It does not certify
anything: it loads each certificate through the same loader the campaign would use and then compares
the set. Its output is `experiments/results/phase_8_random/campaign_seed_summary.json`.

| Check | Result |
|---|---|
| Distinct structure seeds | 16 of 16 |
| Distinct graph digests (content digest) | 16 of 16 |
| Distinct graph file SHA-256 | 16 of 16 |
| Distinct certificate SHA-256 | 16 of 16 |
| Duplicated artifacts | none |
| Node counts, edge counts, accepted swaps | single-valued (172,433 / 1,535,710 / 15,357,100) |
| Signed edges, signed synapses, unsigned edges | single-valued (683,100 / 8,426,168 / 852,610) |
| Weight sum, min, max | single-valued (18,552,546 / 5 / 913) |
| Degree changes, duplicates, self-edges, CSR | single-valued (0 / 0 / 0 / true) |
| Weight-multiset, sign, R9b and R17 equality flags | true for every seed |
| R18 derivation verified | 16 of 16 |
| Provenance complete | 16 of 16 |
| Seed 1 unchanged | yes |
| Original graph distinct from every randomized graph | yes |
| Original graph unchanged during the summary run | yes |

Provenance completeness means, per seed: the manifest and results file hashes were recomputed and
recorded; `created_at` is present; the manifest's `source_check.pass` is true; the manifest's
protocol SHA-256 equals REV4's; and the manifest's declared structure seed and campaign seed equal
the certificate's seed and the seed directory it lives in.

Seed 1 was checked against the identities frozen when it was certified — graph
`d3644a70…8f768`, certificate `9873f4f1…7da3`, manifest `d85572a4…daea4`, results `956580dc…3e2`,
digest `e75c6ad7…d5aa24` — not merely "a seed 1 exists".

**What this does not establish.** Sixteen distinct graphs from sixteen distinct seeds show that the
derivation produced distinct objects and that the generator is not collapsing to one output. They do
**not** prove statistical independence between the sixteen randomizations, and they do not establish
that the degree-preserving ensemble is a valid null model for this connectome. R14 is a plateau
diagnostic, not a mixing proof. Those remain open questions for the campaign's own controls and the
protocol's approval process.

## 8. Deterministic regeneration

Independence of seed from build is necessary but not sufficient; reproducibility is the other half.
For every certified seed the summary rebuilt the graph from the frozen original graph with the same
function and the seed recorded in that seed's certificate:

```
rewire_target_exchange(original, seed=structure_seed, swaps_per_edge=10.0)
```

and compared `graph_digest` with the certified value.

| Result | Seeds |
|---|---|
| Regenerated digest identical to the certified digest | **16 of 16** |
| Regeneration attempted | 16 |
| Mismatch | 0 |

The full 16-seed rebuild ran once and its results are stored in the summary
(`regeneration_provenance.seeds_carried_forward` lists all sixteen; `rebuilt_in_this_run` is
`false` for the final artifact, which reused them only after re-checking that each graph and
certificate SHA-256 was unchanged). A fresh replant of seeds 1–3 on a separate output confirmed
`regenerated_matches: true` and the same regenerated digest for each, so the stored values are not
stale artefacts of an earlier file state.

This is a reproduction of each published graph from its two declared inputs (original graph +
structure seed), performed outside `certify_banc.py` and compared against the certificate rather
than against a remembered value.

---

## 9. Condition C and D integration

`load_structure(certificate_path)` performs the full verification in one call — marker absent,
protocol hash, certificate hash against the manifest, gate results, graph file hash, and the graph
digest recomputed from the arrays — and returns the verified graph plus a `structure_record`.

| Check | Result |
|---|---|
| `load_structure` + `structure_record` + `verify_structure_record` + `_check_structure` per seed | accepted 16 of 16 |
| Record's campaign seed, structure seed and graph SHA-256 match the seed directory | 16 of 16 |
| Record with `randomization_quality.passed = false` | refused (`ConditionError`) |
| Record with no `certificate_path` | refused (`CertificationError`) |
| Selected seed recorded in the record | `master_seed`, `campaign_seed`, `seed`, `graph_path`, `graph_sha256`, `graph_digest`, `certificate_path`, `certificate_sha256`, `protocol_sha256`, `u18_status` |
| Original and randomized graphs distinguishable | separate paths, separate namespaces, different SHA-256 for every seed |
| Condition C modifies the biological graph | never — the original graph is opened read-only; C reads the randomized arrays |
| Condition D can use the randomized representation | yes; C and D consume the same structure record |

**No episode, pilot or training run was executed.** C and D were verified at the hand-off only: the
loader accepts a certified record and refuses anything else. D's readout path is not exercised by
loading a graph, so that claim is not made.

## 10. Resources

Measurements come from the `memory` block each `certify_banc` run writes into its results file.
They are the maximum of explicit `psutil` checkpoints, not a continuous peak measurement.

| Measure | Value |
|---|---|
| Construction peak RSS | 525.8 – 527.3 MB per seed |
| Runner peak RSS (two builds + policies + validation + write) | 431.5 – 433.3 MB per seed |
| Lowest free physical memory during construction | 1.628 GB (seed 4) |
| Lowest free physical memory during the runner | 1.936 GB (seed 2) |
| Free memory at preflight | 1.941 – 2.932 GB |
| Construction preflight floor (per manifest) | 0.75 GB; `allowed: true` for all 16 |
| Runner wall time per seed | 115.2 – 127.4 s |
| Total runner time, 16 seeds | 1,903.0 s (31 min 42 s) |
| Seeds 2–16 loop wall time | 30 min 10 s |
| Concurrent seed builds | none |

Every seed was run sequentially with the free-memory check printed before it and a 1.0 GB abort
guard that never triggered. The 4 GB question is not resolved by any of these numbers: it is a
protocol rule, not a measurement, and §2 records that the rule was not met.

---

## 11. Tests executed

```
python -m pytest tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py \
  tests/test_phase_8_random_campaign.py -q
    48 passed
```

| Suite | Tests | Coverage |
|---|---|---|
| `test_phase_8_random_target_exchange.py` | 15 | swap accounting, degree/weight/source preservation, connectome invariants, gating, R13 denominator, R14 wording, R15/R16 reported, same-seed identity, different-seed difference, attempt cap, R8 policy, parameter validation |
| `test_phase_8_random_certification.py` | 22 | batch-size invariance, rejection counters, sign preservation, all R1–R18 present, no mixing claim, certificate round trip, one-call loader, manifest identities, failed gate blocks the certificate, eight refusal reasons, incomplete namespace, tampered file, forged digest |
| `test_phase_8_random_campaign.py` | 11 | seed parsing, seed-1 filename, invariant extraction, distinct-set pass, duplicated-artifact detection, changed-invariant detection, uncertified exclusion, regeneration outcome recording, provenance completeness, missing-namespace report, atomic summary write |

The campaign suite runs on synthetic entry dictionaries: it tests the set-level logic, and it makes
no assertion that any real seed is certified — that is the job of the 16 certificates and of
`campaign_seed_summary.json`.

## 12. Limitations and status

Recorded without softening. There were no failed seeds; the failures listed are of a different kind.

1. **§9.3 was not met (§2).** All sixteen BANC-scale randomisations started with 1.63 – 3.43 GB
   free physical memory, below the protocol's 4 GB gate, and §9.3 names BANC-scale graph
   randomisation among the operations blocked below it. The builds are real and certified; they are
   not protocol-compliant. Remediation is either an approved protocol amendment covering
   construction-time memory or a rerun on a machine with ≥ 4 GB free. This report does not choose
   between them.
2. **U18 is still PROPOSED.** The target-exchange parameterisation has not been approved. If U18
   changes, the sixteen graphs, certificates and manifests must be rebuilt under the approved
   parameterisation; they must not be edited.
3. **G3 is not complete.** Its acceptance criterion is that the actual BANC graph set passes every
   mandatory requirement in a state the protocol allows. The graphs pass R1–R18, but the set as
   produced is not §9.3-compliant, and U18 is unapproved. No campaign exists to consume the set.
   Marking G3 complete on sixteen certified files alone would overstate it.
4. **R14 passes with a modest margin** — 3.00e-05 to 6.92e-05 against a 1e-4 bound, the smallest
   margin about 1.4x (seed 6). R14 is a plateau diagnostic, not a mixing proof; a passing R14 does
   not establish that the chain converged to a uniform distribution over the degree-preserving
   ensemble.
5. **The residual intersection is non-zero** (3,157 – 3,333 pairs) because swaps can re-create
   original pairs. Per-swap reversions are not instrumented, so their timing and distribution are
   uncharacterised.
6. **Memory peaks are checkpoint maxima.** Transient allocation between checkpoints could have
   exceeded the reported 527 MB, though the 1.628 GB free-memory floor leaves room for that.
7. **Distinct seeds are not statistical independence** and not null-model validity. Sixteen distinct
   digests show the derivation works; nothing here shows the sixteen draws are independent or that a
   degree- and sign-preserving shuffle is the right null.
8. **Structural consequences are reported, not interpreted.** Reciprocity 0.1152 → 0.0016 – 0.0018,
   assortativity −0.0619 → −0.0101 – −0.0113, components 24,470 → 24,332 – 24,350. These are
   expected for target shuffling and were not used to tune anything.
9. **Condition C and D were verified at the hand-off only.** No condition, episode, pilot, training
   run or campaign was executed. A certification is not authorisation to collect data: U1–U18 remain
   unapproved and the 4 GB gate governs campaign execution.
10. **The construction floor and the campaign gate are different rules.** The 0.75 GB construction
    preflight is the mechanism recorded in each manifest; it does not authorise campaign work, and
    satisfying it did not satisfy §9.3.

## 13. Deliverables

| Artifact | Path |
|---|---|
| Randomized graphs (16) | `datasets/processed/banc_v888_random/seed_<N>/banc_graph_random_t5_seed_<N>.npz` |
| Certificates (16) | `datasets/processed/banc_v888_random/seed_<N>/randomization_certificate.json` |
| Manifests (16) | `datasets/processed/banc_v888_random/seed_<N>/manifest.json` |
| Runner results (16) | `experiments/results/phase_8_random/certification_seed_<N>.json` |
| Campaign summary | `experiments/results/phase_8_random/campaign_seed_summary.json` |
| Seed loop log | `experiments/results/phase_8_random/logs/seeds_2_16.log` |
| Campaign verifier | `experiments/phase_8_random/campaign_summary.py` |
| Campaign tests | `tests/test_phase_8_random_campaign.py` |
| This report | `reports/PHASE_8_BANC_RANDOM_GRAPH_CAMPAIGN.md` |
| Status report | `reports/PHASE_8_IMPLEMENTATION_STATUS.md` |

Seed 1 keeps its historical filename (`…seed_1.npz`) and its original byte content.

---

## 14. Reproduction

```bash
# focused tests
python -m pytest tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py \
  tests/test_phase_8_random_campaign.py -q

# build and certify any single seed (refuses an occupied namespace, exit 5)
python -m experiments.phase_8_random.certify_banc --campaign-seed <N>

# verify the set and write the campaign summary (--regenerate rebuilds every seed)
python -m experiments.phase_8_random.campaign_summary --seeds 1-16
```

Exit codes for `certify_banc`: 0 certified, 2 blocked by the memory preflight, 3 gate failure,
4 identity drift, 5 existing output. The verifier exits 1 if any required seed is not certified.

Before running this on a machine subject to REV4 §9.3, check the free-memory gate first. These
graphs were produced below it, and that is the one thing a reproduction must not repeat silently.
