# Phase 8 — Pilot 2-C final preflight

Status: **not executable (`executable = false`); execution not attempted.**
Date: 2026-11-23.
Machine record: `reports/PHASE_8_PILOT2C_FINAL_PREFLIGHT.json`.
Inputs certified in: `reports/PHASE_8_PILOT2C_TRAINED_ARTIFACT_CERTIFICATION.md`.

This preflight ran `pilot2c_readiness(config, pairing=…, training_root=…)` once
with the explicit D5 pairing and the real memory preflight. It executed no
Pilot 2-C episode and no floor replay. `executable = false` is a report, not a
permission: a separate owner decision is still required before any Pilot 2-C
episode runs.

## 1. Verdict

| Item | Result |
|---|---|
| Stage | `pilot2c` (REV4 §10.8 as amended by D3) |
| D3 stage authorisation | authorised for this exact grid; exemption applied; blockers `[]` |
| Amendment / REV4 binding | `amendment_matches_disk = true`, `bound_to_rev4 = true` |
| Plan | 54 entries: 45 neural + 9 floor; arms A, B, F, F_beta, A_prime, floor; seeds 9001–9003; 3 episodes per seed |
| Trained artifacts | all six loaded and complete (`F/F_beta × 9001/9002/9003`) |
| Pairing | explicit: 9001→1008, 9002→1014, 9003→1005 for both conditions |
| Memory preflight (B8 / §9.3) | passed: 7.118 GB available of 15.342 GB, gate 4.0 GB |
| Results destination | `experiments/results/phase_8/pilot2c` is free (never overwritten) |
| Randomized graph | `uses_randomized_graph = false`, `constructs_randomized_graph = false` |
| D6 | non-inheritable; B7 has no subject in the D5 plan; G3 unchanged |
| `executable` | **false** |

The only blocker is:

> `training: D4 declares B3-B6 and D5 authorises only the six F/F_beta pilot
> artifacts; the global training gate still refuses any further training, and
> loadability is reported under training_artifacts`

This is a conservative statement of the global training-gate state, not a
missing prerequisite: the six artifacts are present, verified and loaded.
B2/U7 and B7/G3 remain open for every other stage, and D5 authorises no further
training. Independent of this flag, the controlling owner directive reserves
Pilot 2-C execution for a separate explicit authorisation, so execution was not
started.

## 2. Artifact load

`load_pilot_evaluation_artifacts(..., conditions=("F", "F_beta"),
require_trained=True)` reports:

* loaded keys: `F:9001, F:9002, F:9003, F_beta:9001, F_beta:9002, F_beta:9003`;
* `complete = true`, `missing = []`, `origins = ["trained"]`,
  `synthetic_allowed = false`, `pairing_source = "explicit"`,
  `seed_scope = "pilot"`, `ignored_seeds = []`;
* each readout pair is `paired = true` with the declared training seed;
* `training_config_sha256 = 1508a6a4…33df`;
* `training_performed_here = false` and `execution_authorized = false`.

## 3. Frozen inputs and configuration

Seven frozen inputs are hashed, as the amendment requires:

| Input | SHA-256 |
|---|---|
| `datasets/processed/banc_v888/banc_graph_t5.npz` | `6d47f2592a6d07f2c61318b87719039db21b460115143c0faedd3f20543e2192` |
| `datasets/processed/banc_v888/banc_nodes.csv.gz` | `144a2eb09aa1ed2be4f07eff589a6158e98cfe4f18b52db7feef4d2272953e5f` |
| `configs/neuron_config.yaml` | `9b652bde00a795da205cf22affe8690871670264a3718948f58f3b30583d8b77` |
| `configs/motor_decoder.yaml` | `525f25e9e0d334e58a38ce9d340fcd8fe3ebc148fe1bf9f08656eccc660d9fae` |
| `configs/plasticity_banc.yaml` | `616288a40bf864185c33f92a99742be8dd49e62773cbb58cb9287414ad9e5f70` |
| `configs/banc_sensory_mapping.yaml` | `64c716a42c44ded58c77fccdcd865b0a9732a06b86019d673e6fb4c902dfc4ff` |
| `configs/banc_synapse_policy.yaml` | `88f6449289492e79a919fafa56af93c5ac5e916cb50cc1658d7e14eed2dc399e` |

Configuration hashes: campaign `b9a2d3d5…77e19`, conditions
`9a93f047…2f671`, environment `b391ecf7…281dc`. The training configuration hash
is `1508a6a4733fbfc0431e19a91e3d62d76624fef5626e4bb683779d62340433df`.

`design.n_seeds_selected` remains `null`; U7 is not discharged and N is not
selected. The plan declares `campaign_effects_estimated = false`,
`hypothesis_tests = []`, `merged_into_campaign = false`.

## 4. D6 and G3

D6 is applied as a record, not an inheritance:

* B7 has no subject in the exact D5 plan; D6 grants no exemption.
* `authorises_training_execution = false`, `gate_weakened = false`,
  `graph_access_authorised = false`, `graph_substitution_authorised = false`.
* G3 summary is unchanged: `status = "deviation_recorded"`, `gate_weakened =
  false`, REV4 §9.3, gate 4.0 GB, 16 certified graph seeds, file SHA-256
  `d4e85db7787fea487a0e793ad9c87ca189f4332c34d6063165bd6c435f2ea0ef`.
* Graph-dependent stages (`pilot2`, campaign, C/D/C_prime and any
  certified-random-graph arm) remain blocked.

## 5. What this preflight did not do

* No Pilot 2-C episode and no floor replay.
* No E/E_full run, no campaign step, no randomized-graph access.
* No modification of REV4, D1–D4, Pilot 1 records, historical results, frozen
  parameters, statistical constants, hypotheses or contrasts.
* No Git operation.

## 6. Bottom line

Technically, everything Pilot 2-C consumes is in place: the stage is D3-
authorised for the exact 54-entry grid, the amendment is bound to REV4, all
seven frozen inputs and the configuration hash, the six trained artifacts load
and pair correctly, memory passes the 4 GB gate, and the results destination is
free. The readiness function nevertheless reports `executable = false` because
the global training gate still refuses further training. The sole remaining
step is the owner's explicit Pilot 2-C execution authorisation; until it is
given, no Pilot 2-C episode is executed.
