# Phase 8 — Remaining Blockers B2 and B7: Decision Review

**Status:** read-only review. No owner-decision record has been created. No training
run, trained artifact, Pilot 2-C episode, floor replay, randomized graph or campaign
step has been executed. No Git operation has been performed.

**Date:** 2026-11-22
**Repository:** `C:/Users/Hp/fruitfly/FLY-SURFER`
**Branch:** `main`
**HEAD at review time:** `5f530bdbb1b6a9b1fcaf8017064f49b174d0f473`
(`2026-11-20 18:40:37 +0530`, *Preserve Phase 8 Pilot 1 evidence and readiness work*)

**Purpose.** Establish, from the recorded evidence and the current code, exactly what
B2 (the null `design.n_seeds_selected`, U7) and B7 (the G3 §9.3 deviation) block; what
the smallest scientifically defensible owner decisions are that would unblock F/Fβ
training for Pilot 2-C without changing N, without discharging U7, and without
accepting or weakening the G3 deviation; and what those decisions would and would not
grant. The exact proposed decision wording is in §9–§12. Nothing in §9–§12 is in
force.

---

## 1. Evidence reviewed

Documents and records read in full:

- `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` — §7.1 (design and the
  `σ_max ≤ 112.87` fallback), §9.3 (4.00 GB free-memory gate), §10 (10.5/10.8/10.10),
  U7 (number of seeds N), U5/U6/U8–U18.
- `docs/PHASE_8_PILOT2C_AMENDMENT.md` — A3 C-1…C-18, A4 scope, A4.1 prohibitions,
  A5 P2C-1…P2C-8, A6 σ_max/U7, A7 training dependency, A8 G3/B7, A9 authorisation
  model, A10 invariants, A11 non-authorisations.
- `reports/phase_8_owner_approvals/D1.json` … `D4.json`.
- `reports/PHASE_8_OWNER_APPROVAL_D4.md`,
  `reports/PHASE_8_D4_AND_TRAINING_CONTRACT_IMPLEMENTATION.md`,
  `reports/PHASE_8_PILOT2C_IMPLEMENTATION_AND_PREFLIGHT.md`.
- `configs/phase_8/campaign.yaml`, `environment.yaml`, `conditions.yaml`.
- `experiments/results/phase_8_random/campaign_seed_summary.json`,
  `certification_seed_1.json` … `certification_seed_16.json`.

Code read at the relevant points:

- `experiments/phase_8/campaign/protocol.py` — `PILOT1_G3_SCOPE`,
  `PILOT2C_G3_SCOPE`, `stage_authorization`, `randomization_deviation`,
  `pilot2c_applicability`, `g3_applicability`.
- `experiments/phase_8/training/gate.py` — `TRAINING_DECLARATION_BLOCKERS`,
  `training_declarations`, `training_authorization_status`,
  `assert_training_authorized`, `assert_design_resolved`.
- `experiments/phase_8/training/plan.py` — `build_training_plan`, `run_training`.
- `experiments/phase_8/training/artifacts.py` — `_check_origin_stage`,
  `write_artifact`, `TRAINING_ROOT`.
- `experiments/phase_8/training/loader.py` — `seed_scope`, A-2 pilot loader.
- `experiments/phase_8/training/contracts.py` — B3/B4 derivations and the
  `pilot2c_*` helpers.
- `experiments/phase_8/stages/training_stage.py` — `plan_training_stage`,
  `execute_training_stage`, `derived_pairing`.
- `experiments/phase_8/stages/pilot2c.py` — `pilot2c_plan`, `pilot2c_readiness`,
  `run_pilot2c`.
- `experiments/phase_8/stages/pilot2c_runner.py` — confirms the runner never trains.

Runtime facts were re-derived read-only with the project’s own functions
(`load_phase8_config`, `pilot2c_readiness`, `stage_authorization`,
`training_authorization_status`, `derive_b3_pairing`,
`training_environment_schedule`, `assert_environment_stream_disjoint`). The G3
certificate and graph hashes were re-computed from disk and compared with the values
recorded in `campaign_seed_summary.json` (16/16 certificates and 16/16 graphs match).

---

## 2. Exact hashes verified at review time

All values are SHA-256.

### 2.1 Frozen protocol, amendment and owner decisions

| Artefact | Path | SHA-256 |
|---|---|---|
| REV4 | `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md` | `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c` |
| Pilot 2-C amendment | `docs/PHASE_8_PILOT2C_AMENDMENT.md` | `832ef48579a3d056b85449498558286b86576ab86c15acd90786c8a2ca9667ad` |
| D1 | `reports/phase_8_owner_approvals/D1.json` | `5c183c992c7f68ed1e5756aab61b362b6eace1ec15871b7926982371f364d489` |
| D2 | `reports/phase_8_owner_approvals/D2.json` | `b5b0c229edded8347722e903bec134f9327a21eb4823fb3bdd4595e8c0c17327` |
| D3 | `reports/phase_8_owner_approvals/D3.json` | `74f11d2c599ceffb1a1a2be592d7ab903d9b2ba1c59941338283261b42948df8` |
| D4 | `reports/phase_8_owner_approvals/D4.json` | `1e15138cf76c11ab8c94ffd7299d6a3657fc407fe7c32a0f8a3c9efcca51a8cf` |
| D4 approval document | `reports/PHASE_8_OWNER_APPROVAL_D4.md` | `a86b3e1cc7a1eaa22de9e5878138bf0772589484cb035bcb9de6a69148b37935` |
| D4 implementation report | `reports/PHASE_8_D4_AND_TRAINING_CONTRACT_IMPLEMENTATION.md` | `c5617264b4eca072676d49679be4516ecfde6d0e7cc8b759278fa8d211b1128a` |
| Pilot 2-C implementation report | `reports/PHASE_8_PILOT2C_IMPLEMENTATION_AND_PREFLIGHT.md` | `502586373171c2e5eeaaf3856f282189330aff128053875df27596619cfe24e8` |

### 2.2 Configuration hashes (hashed into every episode record)

| Configuration | SHA-256 |
|---|---|
| `configs/phase_8/environment.yaml` | `b391ecf71fd7acac0517a677f9198d6a252a00428aabf8c58d3b6b343a3281dc` |
| `configs/phase_8/campaign.yaml` | `b9a2d3d5f9fc397af07e12cda97bb1ae854cb505edc304e5727c0e2d83477e19` |
| `configs/phase_8/conditions.yaml` | `9a93f04771a2489b09a14c2b74418ffb423ad9702d7bc3a47492a2012d42f671` |

### 2.3 The seven frozen scientific inputs

| Input | Path | SHA-256 |
|---|---|---|
| Graph | `datasets/processed/banc_v888/banc_graph_t5.npz` | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| Nodes | `datasets/processed/banc_v888/banc_nodes.csv.gz` | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| Motor decoder | `configs/motor_decoder.yaml` | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| Neuron config | `configs/neuron_config.yaml` | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` |
| Plasticity | `configs/plasticity_banc.yaml` | `616288a40bf864185c33f92a99742be8dd49e62773cbb58cb9287414ad9e5f70` |
| Sensory mapping | `configs/banc_sensory_mapping.yaml` | `64c716a42c44ded58c77fccdcd865b0a9732a06b86019d673e6fb4c902dfc4ff` |
| Synapse policy | `configs/banc_synapse_policy.yaml` | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |

### 2.4 G3 evidence

| Item | Value |
|---|---|
| `campaign_seed_summary.json` current SHA-256 | `d4e85db7787fea487a0e793ad9c87ca189f4332c34d6063165bd6c435f2ea0ef` |
| `carried_forward_summary_sha256` embedded in that file | `c3ad36889e4543a507804a9a0eadda73322485c87dd56ed1b9d269eeb79b98bd` |
| `certification_seed_1.json` SHA-256 | `956580dc28430e3f2d476c322088de01b0abebd1303987b82e75bc39c4ae53e2` |
| Seed 1 certificate (recorded) | `9873f4f17b6c7d18cc1ff25cb4f56e62550047cde88b5c7be11b3b77c60b7da3` |
| Seed 1 graph (recorded) | `d3644a70f36f3f962ed8a2a9b3157915320f1107ff511b431ed3a3dda4d8f768` |
| Certificates re-verified from disk | **16 / 16 match** |
| Graphs re-verified from disk | **16 / 16 match** |

The current summary hash differs from the `carried_forward_summary_sha256` it embeds
because the summary records its own regeneration provenance; the per-seed certificate
and graph hashes are unchanged and all 32 re-verified. This is recorded here so that
the difference is not mistaken for tampering. No G3 file was modified by this review.

### 2.5 D4 B3 derivation as it stands

| Evaluation seed | Derived training seed | Pool index |
|---|---|---|
| 9001 | 1008 | 7 |
| 9002 | 1014 | 13 |
| 9003 | 1005 | 4 |

- Namespace: `phase_8/training/B3/v1`
- Payload: `namespace|master_seed|evaluation_seed`
- Master seed: `20261116`
- Training pool: the 20 declared `seeds.training` values `1001…1020`
- Conditions sharing the training seed: `F` and `F_beta`
- B4 stream per training seed is disjoint from the nine Pilot 2-C evaluation
  environment seeds (verified by `assert_environment_stream_disjoint` for all three)
- Derivation-record SHA-256 under the current code: `bc231c796d7efb016c8de904c27921ec44a5c458a48d04f9992a75a143a1f980`

**Caveat for the record design.** That record hash currently covers the field
`training_execution_authorized: false`. The scientific pairing is the invariant part
(namespace, master seed, pool, entries). Any D5/D6 binding should be computed over the
invariant derivation fields so that authorising execution does not mutate the pairing
record’s identity. This is a recording detail, not a scientific change.

---

## 3. PART 1 — repository, working tree and protected inputs

### 3.1 Working-tree inventory (read-only)

`git rev-parse --show-toplevel` → `C:/Users/Hp/fruitfly/FLY-SURFER`
`git rev-parse --abbrev-ref HEAD` → `main`
`git log -1` → `5f530bdbb1b6a9b1fcaf8017064f49b174d0f473`
`git status --porcelain=v1` → **11 modified, 31 untracked** entries.

Modified tracked files:

```
 M experiments/phase_8/campaign/protocol.py
 M experiments/phase_8/manifest.py
 M experiments/phase_8/stages/common.py
 M experiments/phase_8/stages/training_stage.py
 M experiments/phase_8/training/__init__.py
 M experiments/phase_8/training/engine.py
 M experiments/phase_8/training/gate.py
 M experiments/phase_8/training/loader.py
 M experiments/phase_8/training/plan.py
 M readout/controller.py
 M tests/test_phase_8_stage_infrastructure.py
```

Untracked entries:

```
?? datasets/external/
?? datasets/processed/banc_v888/
?? datasets/processed/banc_v888_random/
?? docs/PHASE_8_PILOT2C_AMENDMENT.md
?? docs/PHASE_8_PILOT2_RESCOPING_AMENDMENT_PROPOSAL.md
?? docs/research/
?? experiments/phase_8/stages/pilot2c.py
?? experiments/phase_8/stages/pilot2c_runner.py
?? experiments/phase_8/training/contracts.py
?? experiments/phase_8/training/d4.py
?? experiments/phase_8/training/exact_checkpoint.py
?? experiments/results/phase_4h/control_draws.checkpoint.jsonl
?? experiments/results/phase_4h/population_sensitivity.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.diagnostics.checkpoint.jsonl
?? experiments/results/phase_4h/sensory_roundtrip.diagnostics.v2.checkpoint.jsonl
?? experiments/results/phase_4h/weight_sensitivity.checkpoint.jsonl
?? experiments/results/phase_7/neural_closed_loop_activity.npz
?? experiments/results/phase_8_random/logs/
?? external/
?? reports/PHASE_8_D4_AND_TRAINING_CONTRACT_IMPLEMENTATION.md
?? reports/PHASE_8_EXECUTION_READINESS_AFTER_SOFTWARE_COMPLETION.md
?? reports/PHASE_8_EXTERNAL_INTEGRATION_RECOMMENDATIONS.md
?? reports/PHASE_8_GPU_READINESS_CHECKLIST.md
?? reports/PHASE_8_OWNER_APPROVAL_D4.md
?? reports/PHASE_8_PILOT2C_IMPLEMENTATION_AND_PREFLIGHT.md
?? reports/_tmp_4h4_check.json
?? reports/phase_8_owner_approvals/D3.json
?? reports/phase_8_owner_approvals/D4.json
?? tests/test_phase_8_d4_contracts.py
?? tests/test_phase_8_pilot2c.py
```

No tracked file under `experiments/results/` is reported modified. The untracked
entries listed above are new or uncommitted files, not edits to tracked historical
results. No tracked historical result is reported modified.

### 3.2 Protected / frozen inputs

- REV4, the Pilot 2-C amendment, and D1–D4 — hashes in §2.1; unchanged.
- The seven frozen scientific inputs — hashes in §2.3; unchanged.
- The three configuration hashes — §2.2; unchanged. `design.n_seeds_selected`
  remains `null` (`configs/phase_8/campaign.yaml:25`).
- `README.md` and the `motor/` baseline files — not present in the modified list.
  They were not altered by this review.
- G3 certificates and graphs — re-verified 16/16; unchanged.
- Historical experiment results — no tracked modification reported.

The D3 record’s OD-6 already accepts that Pilot 2-C’s report may be valid but
non-freeze because of existing protected-baseline drift, and forbids restoring or
modifying protected files. Nothing here proposes to touch them.

---

## 4. U7 interpretation and what it means for B2

### 4.1 What U7 requires

REV4 §7.1 and U7 require one choice, made **before the campaign**:

- **N = 16 is the primary design.**
- N = 10 is available **only** as a predeclared fallback and only if the pilot shows
  `σ_max = max(σ_C1, σ_C2, σ_C3, σ_C4) ≤ 112.87` with an upper confidence limit
  strong enough to defend it.
- The governing statistic is the **largest** paired sd among C1–C4, so the pilot must
  include **B** so that `σ_C2` is estimable.
- A 3-seed sd has `df = 2`; its 80% upper confidence limit is ≈ 2.1× the point
  estimate, so a 3-seed pilot generally cannot support N = 10. A larger pilot (≥ 5
  seeds) or independent variance evidence is required for the fallback.
- The choice is **never revisited** after campaign outcomes are seen. If the pilot
  cannot support N = 10 and the budget cannot afford N = 16, the campaign does not
  start; it is not run at N = 10 with a weakened claim.

### 4.2 Why `design.n_seeds_selected` is null

- The 10.8 pilot decision has not been recorded, so the campaign design has not been
  fixed.
- The original 10.8 Pilot 2 (3 seeds × {A, B, C, F, Fβ, A′, C′} × 3 episodes) that
  would have estimated `σ_C1…σ_C4` including `σ_C2` is not executable: it requires
  the certified randomized graphs, and C/C′ are blocked by G3/B7.
- D3 replaced Pilot 2 with **Pilot 2-C**, which by A6 estimates **no** dispersion, no
  upper confidence limit and no `σ_max`. Therefore Pilot 2-C cannot discharge U7, and
  `n_seeds_selected` must stay null.
- `configs/phase_8/campaign.yaml` line 25 is `n_seeds_selected: null`; the campaign
  loader refuses a campaign while it is null.

### 4.3 Is U7 relevant to Pilot 2-C?

No. U7 is a **confirmatory sample-size** decision about how many campaign seeds the
campaign runs. Pilot 2-C is an exploratory floor-and-identity certification:

- A3 C-6: Pilot 2-C does not discharge U7, does not select N, and never writes
  `design.n_seeds_selected`.
- A6: three seeds cannot distinguish N = 16 from any larger N; N = 16 is the
  predeclared default, so the U7 decision rule has no remaining degree of freedom
  Pilot 2-C could inform.
- A9: B2 remains open; “Pilot 2-C does not read or write it”.
- The `pilot2c` stage-authorization branch does not consult B2 at all (confirmed in
  §7.1 below).

However, U7 **is** relevant to the current training interface:

- `build_training_plan` calls `assert_design_resolved(campaign)` and expands over
  `campaign.active_seeds()` (the first `n_seeds_selected` campaign seeds). This is
  the **campaign** training plan, not the pilot artifact plan.
- `training_authorization_status()` unconditionally includes the B2 blocker.
- Therefore B2 bites at **training**, not at the Pilot 2-C evaluation stage.

### 4.4 Does the N = 16 recommendation still stand?

Yes. Nothing observed in Pilot 2-C changes it, because Pilot 2-C produces no
dispersion estimate. N = 16 remains the primary design and the predeclared default;
N = 10 remains unavailable without a defensible `σ_max` upper bound from a larger
pilot or independent variance evidence. The correct action is to leave N and
`n_seeds_selected` untouched.

### 4.5 The minimal owner decision for B2

The minimal decision is **not** to set N. It is to record that the null
`n_seeds_selected` is not a precondition for **pilot-scoped F/Fβ training**, because:

- the pilot artifacts are keyed by the declared pilot evaluation seeds
  `9001–9003`, not by campaign seeds (`seeds.campaign` = `1…16`);
- D4 B3 already declares the exact pairing of those evaluation seeds to training
  seeds drawn from `seeds.training` (`9001→1008`, `9002→1014`, `9003→1005`);
- the pilot training plan does not expand over `seeds.campaign` and does not need a
  campaign design;
- the artifacts are consumed only by `load_pilot_evaluation_artifacts(...,
  seed_scope="pilot")`, which already refuses campaign seeds and requires an explicit
  pairing;
- nothing about this reads or writes `design.n_seeds_selected`, and U7 stays open.

This is the B2 proposal in §9. It authorises execution only of the exact pilot
training plan; it does not authorise campaign training, E/E-full training, a Pilot
2-C episode, a floor replay, a graph randomization or a campaign.

---

## 5. G3 deviation interpretation and what it means for B7

### 5.1 What was generated

G3 constructed 16 randomized graphs (seeds 1–16) with the target-exchange
construction. All mandatory gates R4–R12 and the additional requirement checks are
recorded as passing; the summary reports unique structure seeds, unique graph
digests, exact degree, exact weight multiset, per-source weight profile (R9b),
deterministic regeneration and a complete provenance record. The 16 certificates and
16 graph files re-verified byte-for-byte at review time.

### 5.2 What the resource measurements were

From `campaign_seed_summary.json`:

- Gate: **4.00 GB** free physical memory.
- Minimum observed free memory: **1.628 GB**.
- Maximum observed free memory: **2.747 GB**.
- Every construction run started **below** the gate
  (`construction_runs_below_gate: true`).
- The separate construction preflight floor was 0.75 GB and passed for every seed;
  peak RSS was about 527 MB; no build exhausted memory.

### 5.3 What the record says

```json
"compliance": {
  "rev4_section": "9.3",
  "gate_gb": 4.0,
  "gate_weakened": false,
  "min_observed_free_gb": 1.628,
  "max_observed_free_gb": 2.747,
  "construction_runs_below_gate": true,
  "status": "deviation_recorded",
  "note": "Every BANC-scale randomisation in this set started below the REV4 §9.3
           4.00 GB free-memory gate and therefore is a recorded deviation from the
           protocol's operational constraint, not a compliant run. ... the rule
           itself was not met and is not reported as met."
}
```

The record is explicit: this is a deviation, not a compliant run, and the gate is not
weakened.

### 5.4 What REV4 §9.3 requires

- The gate is 4 GB of **free physical** memory; it is “not weakened, rounded down or
  waived”.
- While below the gate: **no** BANC-scale graph randomisation, **no** full campaign
  simulation, **no** training run, **no** memory-intensive test suite.
- Safe implementation, static inspection, unit-level tests on synthetic graphs and
  document work may proceed.
- Any execution work skipped for this reason is recorded as **pending resource
  availability**, never as completed.
- The campaign must re-check free memory immediately before starting and record it.

### 5.5 What B7 blocks

B7 blocks every use of the **certified randomized graphs**:

- the original Pilot 2 (C and C′);
- the confirmatory campaign (C, D, C′ and any certified-random-graph arm);
- any BANC-scale randomisation;
- every stage that is not covered by a valid, hash-bound, exact-scope owner decision.

In the current code, `training_authorization_status()` additionally reports B7 as a
training blocker whenever `randomization_deviation().status != "compliant"`. That is
broader than the scientific subject of B7: F/Fβ training uses the frozen **biological**
BANC substrate and constructs or reads no randomized graph. This over-breadth is a
code-policy fact, not a scientific finding, and it must not be “fixed” by silently
weakening the gate.

### 5.6 What D3 already does for Pilot 2-C

D3 is a valid, hash-bound owner decision that adopts the Pilot 2-C amendment for the
exact grid:

- stage `pilot2c`, arms A, B, F, F_beta, A_prime and floor;
- seeds 9001–9003, three episodes per seed, 54 rows (45 neural + 9 floor);
- `uses_randomized_graph: false`, `constructs_randomized_graph: false`;
- `accepts_g3_deviation: false`, `weakens_graph_certification: false`.

`PILOT2C_G3_SCOPE` is hard-coded in `campaign/protocol.py` (not read from
configuration), and `stage_authorization("pilot2c", plan=...)` waives B7 only when the
plan matches that scope field-for-field. Confirmed at review time:

```
stage_authorization("pilot2c") -> authorized = True
                                  blockers = []
                                  exemption.applied = True
                                  "B2" appears nowhere in the result
```

So **Pilot 2-C’s B7 exemption already exists and is enforced in code**. What D3 does
not do is authorise F/Fβ training, and what the training gate does not do is recognise
that training has no randomized graph to certify.

### 5.7 What remains for training

Two scientifically clean routes exist:

1. **Narrow non-applicability (recommended).** Record that B7 has no subject in the
   exact pilot F/Fβ training plan, because the plan runs only on the frozen biological
   substrate and constructs, reads and substitutes no randomized graph. Enforce that
   in code with a hard-coded scope constant and a plan-level assertion. Accept and
   weaken nothing. This is the B7 proposal in §10.
2. **Leave training blocked.** Safe, but Pilot 2-C remains non-executable because it
   has no F/Fβ artifact to load.

Accepting or weakening the G3 deviation is not an option: it would set
`gate_weakened = true`, contradict REV4 §9.3 and D1’s non-authorisation list, and
invalidates the graph certification. Regenerating the graphs above the gate is also
outside this directive: it would construct new randomized graphs, take hours, require
≥ 4 GB free, and would not retroactively erase the recorded deviation.

---

## 6. Current readiness blockers (runtime-verified)

### 6.1 `pilot2c_readiness(config)` — `executable = false`

Exact blockers, in order:

```
B8: free memory is below the declared §9.3 gate; available 3.287 GB of 4.0 GB
artifacts: no explicit (condition, evaluation seed) -> training seed pairing was
  supplied; the loader never invents it
artifacts: no trained artifact directory exists under
  C:/Users/Hp/fruitfly/FLY-SURFER/experiments/results/phase_8/training
training: D4 declares B3-B6 but authorises no training run; no trained F/F_beta
  artifact exists, so a Pilot 2-C evaluation cannot load one
```

Other readiness fields at review time:

- `authorization.authorized: true`, `authorization.blockers: []`,
  `authorization.exemption.applied: true` (D3 B7 exemption).
- `uses_randomized_graph: false`, `constructs_randomized_graph: false`.
- `results_destination_free: true` (`experiments/results/phase_8/pilot2c`).
- `training_artifacts.root` does not exist; 0 artifact directories.
- Memory: 3.287 GB available of 15.342 GB (78.6% used), gate 4.0 GB.

### 6.2 `training_authorization_status()`

Exact blockers:

```
B2: design.n_seeds_selected is null until the 10.8 pilot decision (U7) is recorded
B7: the G3 certified graphs carry a recorded §9.3 memory-gate deviation
    (status 'deviation_recorded')
```

`training_authorized: false`.

### 6.3 What these blockers mean, separately

| Blocker | Blocks training? | Blocks Pilot 2-C evaluation? | Scientific subject |
|---|---|---|---|
| B2 / U7 | **Yes**, because the training gate always reports it and the campaign plan requires the design | **No**; the `pilot2c` branch never consults B2 | Confirmatory sample size N |
| B7 / G3 | **Yes**, by current policy | **No**; D3 already scopes the exact pilot grid | Use of the certified randomized graphs |
| B8 / memory | **Yes**, at run time | **Yes**, at run time | Free physical memory < 4.0 GB |
| Artifacts | **Yes**, none exist | **Yes**, none exist | Trained F/Fβ artifacts |
| Code paths | **Yes** | **No**, runner exists | Trained artifact writer + pilot training plan |

The distinction matters: **neither B2 nor B7 is a blocker of the Pilot 2-C stage
itself.** Both are blockers of the prerequisite training. B8 blocks both until the
machine has ≥ 4 GB free.

---

## 7. What the code already enforces, and what it does not

### 7.1 Already enforced

- D1 approves REV4 §12 and U1–U18, and explicitly does **not** bypass B2, B3–B6, B8
  or B7.
- D3’s B7 exemption is exact-scope and code-enforced: `PILOT2C_G3_SCOPE` is
  hard-coded; `_pilot2c_scope_failures` checks arms, seeds, episode count and that no
  neural arm requires a certified structure; the floor declares no substrate; any
  other stage gets a B7 refusal and cannot inherit the exemption.
- The A-2 pilot loader refuses campaign seeds, requires an explicit pairing, requires
  pilot seeds disjoint from campaign and training seeds, and refuses untrained or
  synthetic artifacts.
- The training gate refuses to run (`assert_training_authorized` always raises), and
  `run_training` refuses before touching a file.
- `build_training_plan` refuses while `n_seeds_selected` is null and expands only
  over `campaign.active_seeds()`.

### 7.2 Not enforced / not implemented (material gaps)

These are honest findings. An owner decision alone does not close them.

1. **No trained-artifact writer.** `write_artifact` accepts `stage="initialized"` only;
   `_check_origin_stage` calls `assert_training_authorized` for `origin="trained"` and
   rejects `stage="trained"` outright. Therefore no `origin="trained"` artifact can be
   produced today.
2. **No pilot-scoped training plan path.** `build_training_plan` is campaign-only:
   it calls `assert_design_resolved` and iterates campaign seeds. There is no plan
   builder for evaluation seeds 9001–9003.
3. **No production F/Fβ training episode runner.** `Pilot2CEpisodeRunner` evaluates
   and explicitly never trains; the engine’s `episode_runner` is a caller-supplied
   seam exercised only with synthetic fixtures. A production runner on the biological
   substrate is required.
4. **No D5/D6-aware authorization.** `training_authorization_status` has no concept of
   a pilot-scoped training record; it always emits B2 and B7.
5. **B7 enforcement for training is over-broad.** It blocks training without checking
   whether the plan touches a randomized graph. A narrow, plan-level assertion is
   required before any exemption can be claimed.

The directive’s later parts must implement (1)–(5) before training can run. The
proposals in §9–§10 are written to be enforceable through those changes, not merely
documented.

---

## 8. What approving B2/B7 would *not* do

Even if both decisions are approved exactly as proposed:

- they do **not** by themselves run anything;
- they do **not** satisfy B8 (memory); a fresh preflight with ≥ 4 GB free is still
  required immediately before any run;
- they do **not** create the trained-artifact writer, the pilot training runner or the
  pilot plan path — that implementation must precede execution;
- they do **not** authorise the nine floor replays or the 45 Pilot 2-C neural episodes;
  those remain governed by `assert_stage_authorized("pilot2c", plan=...)` under D3 and
  the directive’s execution-authorization step;
- they do **not** authorise the campaign, C/C′/D, E/E-full, any graph randomization,
  or any use of the certified random graphs;
- they do **not** change N, `design.n_seeds_selected`, U7, any hypothesis, contrast,
  statistical constant, frozen parameter, REV4, D1–D4 or any historical result.

---

## 9. Proposed B2 decision wording (decision identifier D5)

> **Identifier:** `D5` (proposed; the owner may assign a different identifier)
> **Status:** proposed only — **not created**
> **Record path (proposed):** `reports/phase_8_owner_approvals/D5.json`
> **Approval date:** 2026-11-22 (proposed)

**Title.** Pilot-scoped F/Fβ training execution for Pilot 2-C (B2).

**Decision.**

> Authorise execution of F and F_beta training for the exact Pilot 2-C evaluation
> seeds 9001, 9002 and 9003 only, using the B3–B6 contracts declared by D4 and the
> explicit pairing those contracts derive. This decision is scoped to the pilot
> provisioning that Pilot 2-C consumes. `design.n_seeds_selected` remains null; U7
> remains open and is not discharged; no N is selected. This decision authorises no
> campaign training, no E or E_full training, no artifact outside the pilot scope, no
> Pilot 2-C episode, no floor replay, no randomized graph, and no change to any
> frozen parameter, statistical constant, hypothesis, contrast, protocol document or
> historical result.

**Exact scope the wording would bind.**

| Field | Value |
|---|---|
| Stage | `pilot_training` (pilot provisioning for REV4 §10.5 → §10.8 as amended by D3) |
| Evaluation seeds | `[9001, 9002, 9003]` |
| Conditions | `["F", "F_beta"]` |
| Artifact instances | one per condition and evaluation seed: 6 directories |
| Pairing | `F:9001→1008`, `F:9002→1014`, `F:9003→1005`; `F_beta` identical |
| Pairing derivation | D4 B3, namespace `phase_8/training/B3/v1` |
| Training pool | the 20 declared `seeds.training` values (`1001…1020`) |
| Training budget | `training.readout_episodes_per_seed = 20` (REV4 Appendix C), unchanged |
| Environment schedule | D4 B4, namespace `phase_8/training/B4/v1`, 20 seeds per training seed |
| Checkpoint policy | D4 B5 — after every completed episode, all retained, exact-checkpoint schema 2 |
| Resumption | D4 B6 — exactness claimed only after `verify_equivalence` |
| Substrate | frozen biological BANC; no randomized graph |
| Artifact origin/stage | `origin = "trained"`, `stage = "trained"` |
| Artifact root | `experiments/results/phase_8/training` |
| `sets_n_seeds_selected` | `false` |
| `discharges_u7` | `false` |
| `authorises_campaign_training` | `false` |
| `authorises_e_training` | `false` |
| `authorises_pilot2c_episodes` | `false` |
| `constructs_randomized_graph` | `false` |
| `reads_randomized_graph` | `false` |

**Depends on.** D1 (protocol approval, unchanged), D3 (pilot scope, SHA-256
`74f1…48df8`), D4 (B3–B6 contracts, SHA-256 `1e15…8cf`). Bound to REV4
(`e4aa…1547c`) and the Pilot 2-C amendment (`832e…67ad`).

**Explicit prohibitions in the record.**

- Do not read or write `design.n_seeds_selected`.
- Do not discharge U7 or select N.
- Do not train E, E_full, or any condition other than F and F_beta.
- Do not train on campaign seeds or create campaign-keyed artifacts.
- Do not authorise a Pilot 2-C episode, a floor replay or the campaign.
- Do not construct, read or substitute a randomized graph.
- Do not modify REV4, D1, D2, D3 or D4.
- Do not modify a frozen parameter, statistical constant, hypothesis or contrast.
- Do not overwrite or delete a historical result.
- Do not treat a B5 checkpoint as a trained artifact.
- Do not claim exact resumption without `verify_equivalence`.
- Do not derive authorisation from the pilot’s own output.

**Code enforcement required before this decision can be acted on.**

1. A `PILOT_TRAINING_SCOPE` constant hard-coded in code (not configuration-read),
   mirroring `PILOT2C_G3_SCOPE`.
2. A `pilot_training_applicability()` that verifies the D5 record’s SHA-256 and binds
   it to REV4/amendment/D3/D4 field-for-field.
3. A pilot-scoped plan builder that expands only over the evaluation seeds and the
   explicit B3 pairing, never calls `assert_design_resolved`, and never reads
   `n_seeds_selected`.
4. A training authorization function that accepts D5 only for a plan matching the
   hard-coded scope and refuses every other plan with the unchanged B2 string.
5. A trained-artifact writer enabled only under that scope, recording the D5/D6
   hashes, the B3 derivation, the B4 schedule, the B5 checkpoints and the B6
   verification.
6. Focused tests proving that the exact plan passes, every widened plan refuses, and
   `n_seeds_selected` is neither read nor written.

---

## 10. Proposed B7 decision wording (decision identifier D6)

> **Identifier:** `D6` (proposed; the owner may assign a different identifier)
> **Status:** proposed only — **not created**
> **Record path (proposed):** `reports/phase_8_owner_approvals/D6.json`
> **Approval date:** 2026-11-22 (proposed)

**Title.** G3 §9.3 B7 non-applicability for the exact pilot F/Fβ training plan (B7).

**Decision.**

> Record that the G3 §9.3 deviation, which concerns the certified randomized graphs,
> has no subject in the exact pilot F/Fβ training plan authorised by D5, because that
> plan constructs, reads and substitutes no randomized graph and runs only on the
> frozen biological BANC substrate. This decision accepts nothing and weakens nothing:
> `compliance.status` remains `deviation_recorded`, `gate_weakened` remains `false`,
> all 16 certificates and graph files remain byte-identical, and B7 continues to block
> every graph-dependent stage. It applies only to the exact D5 plan and is not
> inherited by any other stage, plan, condition or seed.

**Exact scope the wording would bind.**

| Field | Value |
|---|---|
| Stage | `pilot_training`, D5 only |
| Conditions | `["F", "F_beta"]` |
| Evaluation seeds | `[9001, 9002, 9003]` |
| Training seeds | `[1008, 1014, 1005]` (D4 B3) |
| Substrate | frozen biological BANC only |
| Constructs randomized graph | `false` |
| Reads randomized graph | `false` |
| Substitutes randomized graph | `false` |
| Uses a certified structure record | `false` |
| Accepts G3 deviation | `false` |
| Weakens graph certification | `false` |
| Changes G3 records or hashes | `false` |
| `gate_weakened` | `false` (unchanged) |
| `compliance.status` | `deviation_recorded` (unchanged) |

**Still blocked by B7 after this decision (exhaustive list the record must carry).**

- the original Pilot 2 (C and C′);
- the confirmatory campaign;
- C, D and C′ and every certified-random-graph arm;
- any BANC-scale graph randomization;
- any training or evaluation plan that reads, constructs or substitutes a randomized
  graph;
- any stage other than the exact D5 pilot training plan.

**Depends on.** D1, D3, D4 and D5, with their exact hashes; bound to REV4, the
amendment, and the current G3 summary
(`d4e85db7787fea487a0e793ad9c87ca189f4332c34d6063165bd6c435f2ea0ef`).

**Code enforcement required before this decision can be acted on.**

1. A hard-coded `PILOT_TRAINING_G3_SCOPE` (arms, seeds, conditions, biological
   substrate, no structure record, no randomized graph).
2. A `training_g3_applicability()` that verifies D6’s SHA-256, binds it to
   REV4/amendment/D3/D4/D5, and matches the plan field-for-field.
3. A plan-level assertion that refuses any plan entry whose substrate is not the
   biological substrate, whose condition is outside `{F, F_beta}`, whose evaluation
   seed is outside `{9001, 9002, 9003}`, whose training seed is outside the D4 B3
   pairing, or whose budget/checkpoint policy is not D4’s.
4. `training_authorization_status()` must keep emitting the unchanged B7 blocker for
   every plan that does not match, and may report non-applicability only for a plan
   that does.
5. Tests proving: exact plan → B7 non-applicability; same plan without D6 → B7
   refusal; any randomized-graph plan, C/C′/D, E/E-full, campaign seed or widened
   grid → B7 refusal; G3 summary, certificate and graph hashes unchanged; the
   `pilot2c` D3 exemption unchanged.

**What this record must not do.** It must not edit `campaign_seed_summary.json`, any
certificate, any graph file, REV4 §9.3, D1–D4, or `PILOT2C_G3_SCOPE`. It must not
set `accepts_g3_deviation` or `weakens_graph_certification` to true. It must not
allow the exemption to be inherited.

---

## 11. Consequences of each option

### 11.1 B2 options

| Option | What it does | Consequences | Recommendation |
|---|---|---|---|
| **B2-A — pilot-scoped training only (D5)** | Authorises F/Fβ training for 9001–9003 under D4, leaves `n_seeds_selected` null | After the code changes and a ≥ 4 GB preflight, the 6 pilot artifacts can be produced; U7 stays open; campaign training and campaign remain refused; artifacts are usable only by the pilot loader | **Recommended** |
| B2-B — set `n_seeds_selected = 16` | Resolves B2 globally | Records the U7 choice without the `σ_max` analysis REV4 requires; makes the campaign training plan constructible over 16 seeds; is far beyond Pilot 2-C; invites a premature confirmatory claim; B7 still blocks the graph-dependent stages | Not recommended |
| B2-C — leave B2 open | No decision | No F/Fβ artifacts; Pilot 2-C remains non-executable; no false claim; directive’s goal not met | Safe status quo only |

### 11.2 B7 options

| Option | What it does | Consequences | Recommendation |
|---|---|---|---|
| **B7-A — exact non-applicability for pilot training (D6)** | Records that B7 has no subject in the exact D5 plan; accepts/weakens nothing | After code enforcement, training is unblocked for F/Fβ only; every graph-dependent stage still refuses; deviation record and hashes unchanged; no scientific weakening | **Recommended** |
| B7-B — accept/waive the G3 deviation | Sets `gate_weakened = true` conceptually | Would permit graph-dependent work; contradicts REV4 §9.3, D1 and D3; invalidates the certification claim; forbidden | **Forbidden** |
| B7-C — leave B7 as-is | No decision | Training stays blocked; Pilot 2-C non-executable; safe status quo | Safe status quo only |
| B7-D — compliant G3 rerun above the gate | Rebuilds and recertifies 16 graphs | Requires ≥ 4 GB and hours; constructs new randomized graphs (currently unapproved); does not retroactively erase the recorded deviation; out of scope today | Not available under this directive |

### 11.3 Combined consequence

Only the pair **B2-A + B7-A** unblocks the prerequisite training without changing N,
without discharging U7, and without accepting or weakening the G3 deviation. Both are
required: B2-A alone leaves B7 blocking training; B7-A alone leaves B2 blocking
training. Neither substitutes for B8, the trained-artifact writer, or the execution
authorization for the 54 Pilot 2-C entries.

---

## 12. Exact permissions each decision would grant

### 12.1 D5 would grant

- Execution of F training for evaluation seeds 9001, 9002 and 9003 (3 runs).
- Execution of F_beta training for evaluation seeds 9001, 9002 and 9003 (3 runs).
- Writing 6 trained artifacts under `experiments/results/phase_8/training`, each
  recording its condition, evaluation seed, derived training seed, init seed,
  parameter digest, parameter-file SHA-256, B3/B4 derivation and B5/B6 provenance.
- Writing D4 B5 checkpoints for those runs, all retained.
- The right for `load_pilot_evaluation_artifacts(..., seed_scope="pilot")` to load
  those 6 artifacts for Pilot 2-C.

### 12.2 D5 would not grant

- Any campaign training, campaign artifact or campaign seed.
- E or E_full training.
- Any Pilot 2-C episode or floor replay.
- Any randomized-graph construction, reading or substitution.
- Any change to N, `design.n_seeds_selected`, U7, hypotheses, contrasts, statistical
  constants, frozen parameters, REV4, D1–D4, or historical results.
- Any claim of exact resumption without `verify_equivalence`.
- Any authorization derived from the pilot’s own output.

### 12.3 D6 would grant

- Recognition that B7 has no subject in the exact D5 pilot training plan.
- Permission for the training gate to report B7 non-applicability **only** for a plan
  that matches the hard-coded pilot training scope field-for-field.

### 12.4 D6 would not grant

- Any acceptance, resolution or weakening of the G3 deviation.
- Any change to `gate_weakened`, `compliance.status`, the G3 summary, any certificate
  or any graph file.
- Any use of the certified random graphs.
- Any campaign, Pilot 2 (original), C, D, C′, E or E_full work.
- Any inheritance by another stage, plan, condition or seed.
- Any execution authority by itself.

---

## 13. Open points the owner should confirm before the decisions are recorded

1. **Decision identifiers.** The report proposes `D5` (B2) and `D6` (B7). If the owner
   prefers different identifiers, the wording is otherwise unchanged.
2. **Training budget.** The proposal uses the only declared F/Fβ budget,
   `training.readout_episodes_per_seed = 20` (REV4 Appendix C). A different pilot
   training budget would be a new decision, not an implementation detail.
3. **Artifact origin/stage.** The proposal requires `origin = "trained"` and
   `stage = "trained"`. The code currently cannot write either; implementing that is a
   prerequisite, and it must not reuse the B5 checkpoint format as an artifact.
4. **B3 binding fields.** The record should bind the invariant B3 derivation (namespace,
   master seed, pool, entries), not the current derivation record hash that includes
   `training_execution_authorized = false`.
5. **Memory.** D5/D6 do not touch B8. A fresh preflight with ≥ 4 GB free is still
   required immediately before training and again before Pilot 2-C.

---

## 14. STOP — exact decisions presented for approval

No approval has been inferred from the goal of completing the project today. No
record has been created. The two decisions below are presented for the owner’s
explicit approval or revision.

**Proposed decision D5 (B2).** Approve pilot-scoped F/Fβ training execution for
Pilot 2-C exactly as specified in §9: evaluation seeds 9001–9003, conditions F and
F_beta, D4 B3 pairing (`9001→1008`, `9002→1014`, `9003→1005`), D4 B4/B5/B6
contracts, 20 training episodes per seed, biological substrate, trained artifacts
under `experiments/results/phase_8/training`, with `design.n_seeds_selected` left
null, U7 left open, and no campaign, E/E-full, Pilot 2-C episode, floor replay,
graph randomization or frozen-input change authorised.

**Proposed decision D6 (B7).** Approve the exact-scope record that B7 has no subject
in the D5 pilot F/Fβ training plan because that plan constructs, reads and
substitutes no randomized graph and runs only on the frozen biological substrate, with
`deviation_recorded` and `gate_weakened = false` unchanged, all 16 certificates and
graphs unchanged, every graph-dependent stage still refused, and the exemption
enforced in code and not inheritable.

**Awaiting the owner’s explicit response.** Until then, the repository remains in the
state recorded in this report: training refused, Pilot 2-C not executable, no
approval record created, and no Git operation performed.
