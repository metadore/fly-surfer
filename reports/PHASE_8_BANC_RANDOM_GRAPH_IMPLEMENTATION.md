# Phase 8 BANC random graph implementation (Condition C substrate)

**Date:** 2026-11-17
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` (146,643 bytes)
**Scope:** implement, build and certify the degree- and transmitter-sign-preserving randomized graph
required by Phase 8 Condition C, and connect the certified graph to the Condition C/D substrate.
**U18 status:** the target-exchange parameterisation is **PROPOSED — not approved** (REV4 §12).
No Phase 8 pilot, episode, training run or campaign was executed.

---

## 1. Milestone status

The brief requires five milestones to be reported separately. They are not interchangeable.

| # | Milestone | Status |
|---|---|---|
| 1 | Implementation (generator, gates, certification, runner, loader) | **done** |
| 2 | Synthetic tests (Stage A fixtures, Stage B intermediate graph) | **done** — 37 tests pass |
| 3 | Actual BANC graph generated | **done for campaign seed 1** |
| 4 | Certified against R1–R18 | **done for campaign seed 1 only** |
| 5 | Integration into the Condition C campaign path | **wired and verified against the real certificate; no episode executed** |

**G3 is not marked complete.** The §10 criterion is that the actual BANC graph passes every
mandatory REV4 requirement; that is true for the one graph produced from campaign seed 1
(structure seed 1,258,589,452). It is not yet true for campaign seeds 2–16, which have not been
constructed. A single certified seed is not the campaign's set of per-seed graphs, and the
campaign itself remains blocked by the 4.00 GB memory gate and by U1–U18 being unapproved.

---

## 2. Authorities and immutable inputs

| Artifact | Path | Bytes | SHA-256 |
|---|---|---|---|
| REV4 protocol | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | 146,643 | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Original BANC graph | `datasets/processed/banc_v888/banc_graph_t5.npz` | 13,484,120 | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| BANC node table | `datasets/processed/banc_v888/banc_nodes.csv.gz` | 3,800,401 | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Synapse policy config | `configs/banc_synapse_policy.yaml` | 5,198 | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |
| BANC manifest | `datasets/processed/banc_v888/banc_manifest.json` | — | consulted for expected node/graph hashes |

The protocol hash was recomputed before use and matches the value frozen in the earlier
REV4 work. The runner refuses to start if any of these identities drift (`certify_banc.py`,
exit code 4).

Original graph structure, read-only:

- 172,433 nodes; 1,535,710 directed edges; 852,610 unsigned edges and 683,100 signed edges,
  carrying 8,426,168 signed synapses.
- CSR arrays `out_indptr`/`in_indptr` (int64, 172,434 entries), `edge_src`/`edge_dst` (int32,
  1,535,710), `edge_weight` (int32), `in_edge_idx` (int32), plus node metadata. Weights are
  positive integers 5…913, sum 18,552,546.
- Sign is not stored per edge: it is derived from the node table through the frozen synapse
  policy, from the transmitter identity of the source and the edge weight. The randomized graph
  therefore cannot change sign semantics without changing node identity, which target exchange
  does not do.
- Self-edges: zero in the original. Duplicate `(src, dst)` pairs: zero in the original.

---

## 3. Algorithm

Target exchange, U18 option (a), as declared in `experiments/phase_8_random/target_exchange.py`:

1. An edge slot keeps its **source** and its **weight**. Only targets move.
2. Each candidate swap draws two edges `(a, b)` from distinct sources with distinct targets and
   exchanges their targets: `(src_a, dst_b)` and `(src_b, dst_a)`.
3. A candidate is rejected if the swap would duplicate an existing `(src, dst)` pair (including
   the other new pair), create a self-edge, or change nothing.
4. The loop runs until `round(swaps_per_edge × n_edges) = 10 × 1,535,710 = 15,357,100` swaps are
   accepted, under a hard cap of `20 × target` attempts so the run stops safely.
5. The chain is sequential; order enters only through the network state, so the result is
   invariant to `batch_size` (verified: batches of 37 vs 10,000 produce an identical digest).

Randomness: a per-block stream `SeedSequence([seed, block_index])` with
`CANDIDATE_BLOCK = 4096`, so the chain does not depend on how many candidates a batch consumes.
The structure seed is the REV4 §6.3 structure-stream value

`SeedSequence([master_seed = 20261116, campaign_seed = 1, structure_stream_code = 4]) → 1,258,589,452`

which is exactly the seed used and is recorded as `R18.derivation_verified = true`.

Memory strategy (REV4 §9.3 untouched; no campaign step is run):

- The graph is loaded once; edge sets live as sorted packed `int64` keys (`src × n + dst`), not as
  Python sets of tuples.
- Each candidate batch materialises only its own candidate arrays (default 100,000).
- Duplicate detection is a sorted-intersection / `np.isin` test against the packed key array; the
  key array is rebuilt only when accepted positions change, and edge arrays are updated in place.
- R5 and R13 are computed by packed-key intersection and bincount, without adjacency matrices.
- Memory is sampled at explicit `psutil` checkpoints; the reported peak is the maximum of those
  samples, not a continuous peak measurement.

---

## 4. Memory and runtime

Preflight estimate (construction only, `certify_banc.py`):

| Component | MB |
|---|---|
| graph arrays | 26.1 |
| swap copies | 35.2 |
| duplicate key set | 140.6 |
| checkpoint transient | 35.2 |
| validation transient | 74.2 |
| signed policies | 15.7 |
| **estimated total** | **326.9** |

Floor used for this construction: **0.75 GB**; available at start: **2.445 GB**; allowed.
This construction floor is not the campaign gate: the REV4 §9.3 gate remains **4.00 GB** and no
campaign step was attempted.

Measured during the certified run (campaign seed 1):

| Measure | Value |
|---|---|
| Construction elapsed time | 53.531 s |
| Runner total elapsed time | 119.512 s (two independent builds + policies + validation + write) |
| Construction checkpoints | 157 |
| Construction peak RSS | 526.223 MB |
| Minimum free physical memory during construction | 2.184 GB |
| Runner peak RSS | 432.398 MB |
| Minimum free physical memory during the run | 2.210 GB |
| RSS at the second build | 429.371 MB |

The peak is roughly 1.6× the estimate; the estimate was not used to skip work — every gate ran on
the full graph. An earlier dry run (1 % of swaps) demonstrated the failure path at BANC scale:
R4, R5, R13 and R14 failed, `failure_report.json` was written, the `RUN_INCOMPLETE` marker was
kept and no certificate was produced.

---

## 5. R1–R18 results on the actual BANC graph (campaign seed 1)

Every value below is taken from `datasets/processed/banc_v888_random/seed_1/randomization_certificate.json`
at `report.gates.<ID>` and is mirrored in
`experiments/results/phase_8_random/certification_seed_1.json` at
`structure_record.randomization_quality.gates.<ID>`. The certificate also embeds recomputed
integrity evidence (`integrity.intersection_recomputed = 3,200`, equal to the reported value).

### 5.1 Gated requirements

| ID | Requirement (as implemented) | Measured | Threshold | Result |
|---|---|---|---|---|
| R4 | fraction of original edges whose target changed | 0.997916273 | ≥ 0.99 | **pass** |
| R5 | Jaccard similarity of original and new edge sets | 0.00104295 (intersection 3,200) | ≤ 0.01 | **pass** |
| R6 | exact per-node out-degree preservation | max change 0; sum 1,535,710 = expected | exact | **pass** |
| R7 | exact per-node in-degree preservation | max change 0; sum 1,535,710 = expected | exact | **pass** |
| R8 | transmitter sign preserved per node and per edge | per-node signed vectors equal; per-edge reordering equal; signed edges 683,100 → 683,100; signed synapses 8,426,168 → 8,426,168; unsigned edges 852,610 → 852,610 | exact | **pass** |
| R9 | global weight multiset | equal; sum 18,552,546; min 5; max 913 | exact | **pass** |
| R9b | per-source outgoing weight multiset and out-degree profile | both equal | exact | **pass** |
| R10 | duplicate `(src, dst)` pairs | 0 | 0 | **pass** |
| R11 | self-edges | 0 | 0 | **pass** |
| R12 | CSR invariants (`indptr`, index ranges, ordering) | true | true | **pass** |
| R13 | mean out-neighbour Jaccard over active nodes | 0.000336582 over 130,709 active nodes (41,724 isolated in both, excluded); literal all-node value 0.242227383 reported, not gated | ≤ 0.01 | **pass** |
| R14 | rewiring-distance plateau diagnostic | 31 tail samples; max absolute change 5.122432e-05; final Jaccard 0.001047843935 | < 1e-4 | **pass** |
| R17 | two independent same-seed builds byte-identical | both digests `e75c6ad78e5e55daa34fa7a58dc016d1aba3c9b017237ba03ab3ec8e66d5aa24`; all compared fields equal | identical | **pass** |

R14 is a **plateau diagnostic on the rewiring distance only**. It is not a proof of Markov-chain
mixing, and this report makes no mixing claim. Degree preservation plus a small residual
intersection does not establish that the chain has converged to a uniform distribution over the
degree-preserving ensemble.

The residual intersection of 3,200 pairs is not zero because a swap can later re-create an
original `(src, dst)` pair after its slot was swapped away. This is a property of the chain; the
number is reported, not interpreted, and it is not evidence for or against mixing.

### 5.2 Reported, not gated

| ID | Requirement | Measured |
|---|---|---|
| R1 | swaps attempted | 15,456,122 |
| R2 | swaps accepted vs target | 15,357,100 = target; complete |
| R3 | rejection accounting and progress | duplicate pair 96,480; self-loop 1,062; no-change 1,480; out-of-range 0; acceptance rate 0.993593348 |
| R15 | weak components, before → after | 24,470 → 24,350; largest 147,759 → 148,055; full size histograms recorded |
| R16 | reciprocity and degree assortativity | reciprocity 0.115203 → 0.001723; assortativity −0.061930 → −0.010169 |
| R18 | structure seed derivation | entropy `[20261116, 1, 4]`; derived = used = 1,258,589,452; `derivation_verified = true` |

No mandatory requirement failed. The certificate's `report.failures` is empty and its
`report.passed` is `true`.

**Rejection protocol.** Any failure of R4–R14 (including R9b) or R17 rejects the graph. The
permitted response is to rerun with a different seed; relaxing a gate is not permitted. This run
needed no rerun: seed 1,258,589,452 passed every mandatory gate on its first certified attempt.
The 1 % dry run described in §4 was a deliberate negative test of this protocol, not a relaxed
run.

---

## 6. Outputs, certification gate and Condition C integration

### 6.1 Produced artifacts (campaign seed 1)

| Artifact | Path | Bytes | SHA-256 |
|---|---|---|---|
| Randomized graph | `datasets/processed/banc_v888_random/seed_1/banc_graph_random_t5_seed_1.npz` | 13,554,641 | `d3644a70f36f3f962ed8a2a9b3157915320f1107ff511b431ed3a3dda4d8f768` |
| Certificate | `datasets/processed/banc_v888_random/seed_1/randomization_certificate.json` | 45,148 | `9873f4f17b6c7d18cc1ff25cb4f56e62550047cde88b5c7be11b3b77c60b7da3` |
| Manifest | `datasets/processed/banc_v888_random/seed_1/manifest.json` | 23,082 | `d85572a41d0343751234788aad9e815a449174cc9e6eda21514c6da80c0daea4` |
| Runner results | `experiments/results/phase_8_random/certification_seed_1.json` | 44,123 | `956580dc28430e3f2d476c322088de01b0abebd1303987b82e75bc39c4ae53e2` |

The original and randomized graph files are distinguishable by both path and SHA-256; the
certificate also records the graph digest (`e75c6ad7…d5aa24`), which is a digest of the arrays
and differs from the file hash. The output namespace is separate from the input namespace and
the original graph was opened read-only.

### 6.2 How the gate works

`certify_banc.py` refuses to write a certificate unless all mandatory gates pass. Refusal paths:

| Condition | Exit code |
|---|---|
| construction memory preflight fails | 2 |
| any mandatory gate fails | 3 |
| protocol / source identity drift | 4 |
| output namespace already occupied | 5 |

An output directory is marked with a `RUN_INCOMPLETE` file until the certificate, manifest and
results are all written; a run that stops leaves the marker in place and cannot be mistaken for a
certified output. Certificate loading re-checks: the marker, the protocol hash, the certificate's
own SHA-256 against the manifest, the recorded gate results, the graph file hash, and the graph
digest recomputed from the arrays. A forged or tampered record is refused.

### 6.3 Condition C and D hand-off

`certification.load_structure(certificate_path)` performs the full verification in one call and
returns the verified graph plus a `structure_record` containing `graph_digest`, `graph_path`,
`graph_sha256`, `certificate_path`, `certificate_sha256`, `protocol_sha256`, `master_seed`,
`campaign_seed`, `seed`, `construction` and `u18_status`.

`experiments/phase_8/conditions/base.py::_check_structure` now calls `verify_structure_record`
whenever a `certificate_path` is present, so a condition cannot start on an uncertified or
altered graph. Verified against the real seed-1 record: `_check_structure` accepts it; the loader
returns a graph of 172,433 nodes and 1,535,710 edges whose digest matches the certificate.

Condition C uses the randomized graph with fixed weights and unchanged signs. Condition A is
untouched. Condition D can consume the same certified graph without modifying C. The campaign
manifest fields for graph identity and seed are already carried by `structure_record`. **No
episode, pilot or training run was executed**, and an uncertified graph is refused before any
episode can start.

---

## 7. Tests

```
python -m pytest tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py -q
    -> 37 passed in 9.56 s
```

Windows, Python 3.13.14, numpy 2.3.4, scipy 1.16.3, psutil 7.1.2. No GPU work, no training.

| Suite | Tests | What it covers |
|---|---|---|
| `test_phase_8_random_target_exchange.py` | 15 | completion and attempt accounting; degree/weight/source preservation; connectome invariants; gating; R13 denominator; R14 wording; R15/R16 reported; same-seed identity and different-seed difference; zero budget; attempt cap reported incomplete; R8 policy requirement; summary; parameter validation; contract wording |
| `test_phase_8_random_certification.py` | 22 | batch-size invariance; rejection counters; sign preservation; reported gates; all R1–R18 present; no mixing claim; certificate round trip; one-call loader; manifest identities; failed gate blocks the certificate; eight refusal reasons; incomplete namespace; tampered file; record must name a certificate; forged digest |

Stage A uses small synthetic graphs with planted structure. Stage B uses a 60,000-node /
60,000-edge synthetic graph, deliberately larger than needed for the structural gates. The
reason is R14: a single edge is 1/60,000 ≈ 1.7e-5 of the edge set, so a 600-edge fixture cannot
satisfy a 1e-4 plateau bound even for a correct implementation (one edge would be 1.7e-3 of the
set). At 60,000 edges a real run passes R14 with 5.0e-5. **No threshold was altered to make a
fixture pass**; the fixture size was chosen so that the declared threshold is evaluable.

Stage C is the actual BANC graph, run through `certify_banc.py` and reported in §5. The synthetic
suite and the BANC run are separate evidence: passing tests does not imply the BANC graph is
certified, and vice versa.

---

## 8. Failures and limitations

Recorded without softening:

1. **G3 is not complete.** Only campaign seed 1 has a certified graph. Campaign seeds 2–16 have
   not been built, and each needs its own certified graph because the structure seed is
   per-campaign-seed. Seeds cannot be inferred from seed 1 or reused across seeds.
2. **R14 passed with roughly 2× margin** (5.12e-5 against 1e-4). It is a plateau diagnostic, not
   a mixing proof; a passing R14 does not establish that the chain converged.
3. **The residual intersection is 3,200 pairs** because swaps can re-create original pairs. The
   number is reported; the implementation does not instrument per-swap reversions, so their
   timing and distribution are not characterised.
4. **U18 target exchange is PROPOSED, not approved.** If U18 changes, the graph, certificate and
   manifest must be rebuilt under the approved parameterisation; they must not be edited.
5. **Memory peaks are the maximum of explicit checkpoints**, not a continuous peak. Transient
   allocation between checkpoints could be higher than 526 MB (construction) or 432 MB (runner).
6. **Condition C/D integration was verified at the hand-off, not in an episode.** The real
   certificate is accepted by `load_structure` and `_check_structure`; no condition, episode,
   pilot, training run or campaign was executed, as the brief requires.
7. **No mixing claim and no anatomical claim.** Degree and sign preservation constrains the null
   model; it does not prove the null is valid, and randomized connectivity is not anatomy.
   Condition C remains a randomized structural control.
8. **Structural consequences are reported, not interpreted.** Reciprocity falls from 0.1152 to
   0.0017 and assortativity moves from −0.0619 to −0.0102; component count changes from 24,470 to
   24,350. These are structural consequences of target shuffling, recorded in R15/R16 and not
   used to tune anything.
9. **The 4.00 GB campaign gate was never approached or weakened.** The 0.75 GB construction floor
   is specific to this build step and does not authorise campaign work.

---

## 9. Reproduction

```bash
# focused tests (Stage A + Stage B)
python -m pytest tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py -q

# certified build for campaign seed 1 (refuses an occupied output namespace)
python -m experiments.phase_8_random.certify_banc --campaign-seed 1
```

The runner derives the structure seed from frozen inputs: `master_seed` from
`configs/phase_8/campaign.yaml` (20261116), `campaign_seed` from the flag, and the structure
stream code 4. It verifies the protocol, graph and node-table hashes before loading, runs the
preflight, builds the graph twice, compares the builds (R17), builds the signed policies,
validates R1–R18, writes the certificate, manifest and results, then removes `RUN_INCOMPLETE`.
Exit codes: 0 certified, 2 blocked by memory, 3 gate failure, 4 identity problem, 5 existing
output. A dry run with `--swaps-per-edge 0.1 --output-root <fresh>` is the negative test; it is
expected to fail R4/R5/R13/R14 and to leave the marker.

---

## 10. Files added or changed

| File | Change |
|---|---|
| `experiments/phase_8_random/target_exchange.py` | rewritten: packed-key memory strategy, vectorized R5/R13, block-seeded candidates, R9b, honest R14 diagnostic |
| `experiments/phase_8_random/certification.py` | new: certificate/manifest schema, `RUN_INCOMPLETE` marker, refusal checks, `load_certified_graph`, `structure_record`, `verify_structure_record`, `load_structure` |
| `experiments/phase_8_random/certify_banc.py` | new: BANC preflight, identity checks, two builds, validation, atomic outputs, exit codes |
| `experiments/phase_8_random/__init__.py` | exports the package's public names |
| `experiments/phase_8/conditions/base.py` | `_check_structure` now verifies the certificate when `certificate_path` is present |
| `tests/test_phase_8_random_certification.py` | new: 22 tests (Stage A/B fixtures, refusals, tampering, hand-off) |
| `datasets/processed/banc_v888_random/seed_1/` | new output namespace: graph, certificate, manifest |
| `experiments/results/phase_8_random/certification_seed_1.json` | new: runner result record |
| `reports/PHASE_8_BANC_RANDOM_GRAPH_IMPLEMENTATION.md` | this report |
| `reports/PHASE_8_IMPLEMENTATION_STATUS.md` | updated G3 row, §10.4 row, test counts and next steps |

The original graph, node table, policy config, protocol and all frozen Phase 4–7 artifacts were
opened read-only. No Git state was changed: no staging, commit, push, reset, clean, stash or
checkout. No experiment or campaign was run, and no confirmatory claim is made.

<!-- END -->
