# Phase 8 end-to-end integration audit (synthetic fixtures)

**Date:** 2026-11-18
**Protocol:** `docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`
**Protocol SHA-256:** `e4aa9e0f2f8f414523b1a552d9209ac7f92abcd384bea7656d2a85b4bcb1547c`
**Scope:** every declared arm — A, B, C, D, E, E-full, F, A′, C′, Fβ, F-init, floor — traced through the
campaign interfaces: construction, graph selection, artifact loading, seed pairing, environment
pairing, reward handling, result schema, provenance, deterministic replay, failure handling and
resume.
**Fixture boundary:** all execution in this audit used synthetic fixtures. No real game episode, no
BANC-scale simulation, no training run, no pilot and no campaign was executed. Nothing here is a
biological observation.

---

## 1. Audit result at a glance

| Dimension | Result | Basis |
|---|---|---|
| Arm construction and dispatch | pass | 12/12 arms routed by the real `CampaignDispatcher` |
| Graph selection for C/D/C′ | pass | certified-only source; no biological fallback; refusal paths tested |
| Trained-artifact loading | pass (blocked by approval, by design) | origin/width/state/trainable checks; trained origin refused while training is unauthorised |
| Seed pairing | pass | environment paired; network per condition; structure shared; training pairing explicit |
| Environment pairing | pass | identical environment seed across paired arms; A′/C′ reuse the mirror run |
| Reward handling | pass | reward delivered to the plastic hook and to the readout/agent update; non-finite refused |
| Result schema | pass | required/optional key validation, episode-key uniqueness, torn-tail detection |
| Provenance | pass | protocol/config/input hashes, seeds, manifests, row evidence |
| Deterministic replay | pass within declared scope | deterministic training loops, deterministic sign-flip, store round-trip; parameter-continuous resume only |
| Failure handling and resume | pass | failures recorded without fabricating rows; resume idempotent on the episode key; drift refused |
| **Uninterrupted six-condition campaign** | **not executed** | prohibited in this pass; verification is at real interface boundaries with synthetic fixtures |

No implementation defect was found in the audited path. The integration is **mechanically complete and
deliberately blocked**: approval, design resolution and the memory gate each refuse execution before a
row can be written. Six open inputs are *designed refusals*, not bugs (section 7).

---

## 2. Method

### 2.1 Executed

| Activity | Result |
|---|---|
| Read-only CLI `python -m experiments.phase_8.run_campaign check` | conformance **69/69**, certified graphs **16/16**, memory **2.529 / 4.0 GiB (failed)**, `design_resolved: false`, `executable: false` |
| Phase 8 focused synthetic suites (14 files) | **352 passed in 24.36 s** |
| Static trace of the campaign path | registry → factory → dispatcher → runner → store → analysis |
| Read-only integrity of G3 artifacts | 16/16 graph and certificate SHA-256 match; 0 markers |

Test command:

```
python -m pytest tests/test_phase_8_analysis.py tests/test_phase_8_campaign_runner.py \
  tests/test_phase_8_campaign_skeleton.py tests/test_phase_8_conditions.py \
  tests/test_phase_8_controls.py tests/test_phase_8_conventional_learner.py \
  tests/test_phase_8_live_plastic_stepper.py tests/test_phase_8_readout.py \
  tests/test_phase_8_training_artifacts.py tests/test_phase_8_training_engine.py \
  tests/test_phase_8_viability.py tests/test_phase_8_random_target_exchange.py \
  tests/test_phase_8_random_certification.py tests/test_phase_8_random_campaign.py -q
→ 352 passed
```

### 2.2 Not executed, and why

- No real game episode: §7 of the readiness brief forbids it; the condition tests use
  `ControlledGameEnvironment` with a 20–60 step cap as a deterministic fixture, not a data run.
- No BANC-scale simulation: the synthetic conditions use a 32-node test network.
- No training run: `training/gate.py::assert_training_authorized` always raises; synthetic training
  tests use `synthetic_context` only.
- No pilot or campaign: `n_seeds_selected` is null and the memory gate fails.
- No graph regeneration: free memory is below the gate (see `PHASE_8_G3_DEVIATION_RESOLUTION.md`).

### 2.3 Evidence types

- **Executed assertion:** a test or CLI run performed in this pass.
- **Static trace:** the code path was read; no dynamic execution was attempted because the path is
  gated.
- **Recorded at certification:** an artifact produced earlier and verified by hash this pass.

The report labels each claim with one of these.

---

## 3. Interface inventory

| Interface | Location | Role in the audit |
|---|---|---|
| `ConditionSpec`, `Registry`, `build_registry`, `default_registry` | `experiments/phase_8/registry.py:30,102,138,152` | declares the 12 arms and their requirements |
| `confirmatory_contrasts`, `assert_confirmatory_family`, `evaluation_plan` | `registry.py:188,199,210` | C1–C4; refuses while the design is null |
| Seed derivation | `experiments/phase_8/seeds.py:71,86,96,114,121` | environment/network/learning/structure streams |
| `CampaignFactory`, `FactorySettings`, `TrainingArtifacts` | `experiments/phase_8/campaign/factory.py:65,77,102,163` | builds components per arm; loads certified graphs and trained artifacts |
| `CampaignDispatcher`, `EpisodeFailure`, `DispatchRecord` | `experiments/phase_8/campaign/dispatcher.py:83,87,130,151` | routes each arm to its runner; mirrors A′/C′ |
| `CampaignRunner`, `_gate_report` | `experiments/phase_8/runner.py:36,48` | memory/design gates, plan iteration, store writes, manifest |
| `validate_episode_row`, `validate_rows`, `validate_manifest` | `experiments/phase_8/schema.py:188,336,367` | closed schema, key set, episode key |
| `EpisodeStore` | `experiments/phase_8/store.py:85` | append-only JSONL, resume, torn tail |
| `build_manifest`, `hash_inputs` | `experiments/phase_8/manifest.py:93,112` | provenance |
| `validate_campaign`, `approval_status` | `experiments/phase_8/campaign/protocol.py` | conformance and approval gate |
| Conditions A–F | `experiments/phase_8/conditions/` | one module per condition |
| Controls A′/C′/Fβ/F-init/floor | `experiments/phase_8/controls/` | mirrors, bias-only, init-only, substrate-free |
| Plastic hook | `experiments/phase_8/conditions/plasticity_hook.py` | reward delivery and zero-delta path |
| Training gate | `experiments/phase_8/training/gate.py:55,81` | design and authorisation refusal |
| Training engine / checkpoints / loader | `experiments/phase_8/training/{engine,checkpoint,loader}.py` | budgets, resume, artifact validation |
| Analysis | `experiments/phase_8/analysis.py`, `analyse_phase_8.py` | sign-flip, Holm, identity, floor, E1–E5 |
| Viability | `evaluation/viability.py` | U1-A…U1-E read-only classification |

---

## 4. Verification by requested dimension

### 4.1 Construction

| Arm | Declared route | Substrate | Plasticity | Controller | Evidence |
|---|---|---|---|---|---|
| A | `a_fixed` | biological | none | fixed decoder | `test_condition_a_runs_and_produces_a_schema_row` |
| B | `b_plastic` | biological | three-factor, eta 0.5 | fixed decoder | `test_condition_b_runs_learning_updates_through_the_live_stepper` |
| C | `c_random` | random degree/sign-preserving | none | fixed decoder | `test_random_conditions_require_a_passing_structure_record` |
| D | `d_plastic` | random degree/sign-preserving | three-factor, eta 0.5 | fixed decoder | `test_condition_d_runs_learning_on_the_exchanged_graph` |
| E | `e_conventional` | none | none | MLP policy | `test_condition_e_runs_on_the_game_api_and_trains_its_policy` |
| E-full | `e_conventional` | none | none | MLP, 14 features | `test_condition_e_full_declares_fourteen_features` |
| F | `f_readout` | biological | none | linear readout | `test_f_trains_only_the_readout_and_reports_the_motor_block` |
| A′ | `controls.a_prime` | biological | eta 0 mirror | fixed decoder | `test_a_prime_reproduces_a_exactly` |
| C′ | `controls.c_prime` | same random graph | eta 0 mirror | fixed decoder | `test_c_prime_reproduces_c_on_the_same_graph` |
| Fβ | `controls.f_beta` | biological | none | bias-only | `test_f_beta_readout_is_provably_state_independent` |
| F-init | `controls.f_init` | biological | none | readout at seeded init | `test_f_init_refuses_a_training_episode` |
| floor | `controls.floor` | none | none | constant `NO_ACTION` | `test_floor_runs_constant_no_action_without_a_substrate` |

Dispatcher coverage: `test_dispatcher_declares_every_arm_in_registry_order` asserts 12 arms and the
six conditions; `test_control_semantics_are_declared` asserts A′/C′ mirrors, B eta, F decision source
and floor semantics; `test_dispatcher_refuses_an_unknown_arm` asserts no arm can be invented.

Result: **12/12 arms construct and dispatch; six conditions preserved; no arm merged or dropped.**

### 4.2 Graph selection

| Requirement | Evidence | Result |
|---|---|---|
| C/D/C′ use a certified graph | `test_structure_arms_never_fall_back_to_the_biological_graph` | pass |
| An uncertified seed is refused | `test_graph_source_rejects_an_uncertified_seed` | pass |
| A refused certificate is never a fallback | `test_refused_certificate_is_never_a_fallback` | pass |
| Invalid certificate records are fatal | `test_invalid_certificate_records_are_fatal` | pass |
| A missing graph file is fatal | `test_missing_graph_file_is_fatal` | pass |
| Marker/status inspection | `test_certificate_inspection_reports_marker_and_status` | pass |
| C/D/C′ share one structure stream | `test_structure_stream_is_shared_by_c_d_and_c_prime` | pass |
| Loader accepts 16/16 certified records | CLI `check` and `campaign_seed_summary.json` | pass (recorded at certification; file hashes re-verified this pass) |

The factory's `STRUCTURE_ARMS = ("C", "D", "C_prime")` and the `CertifiedGraphSource` make the
biological graph unreachable for these arms by construction: a failure to load is an error, not a
fallback. **No path was found by which C, D or C′ could silently use the original graph.**

### 4.3 Artifact loading

| Requirement | Evidence | Result |
|---|---|---|
| The factory never trains | `test_factory_describe_states_no_training_and_no_mechanism` | pass |
| Missing trained models are a hard error | `test_training_artifacts_refuse_absent_models` | pass |
| Readout width must match the motor interface | `test_factory_readout_width_must_match_the_motor_interface` | pass |
| Origin must be `trained` for the campaign | `test_loader_requires_trained_origin` | pass |
| Synthetic fixtures require explicit permission | `test_loader_requires_explicit_fixture_permission` | pass |
| State and trainable digests are re-verified | `test_state_digest_mismatch_is_rejected`, `test_manifest_records_provenance_and_digests` | pass |
| F and Fβ share a training run | `test_f_and_fbeta_must_share_their_training_run`, `test_readout_pair_check_requires_f_and_fbeta` | pass |
| Fβ remains state-independent after reload | `test_fbeta_state_independence_survives_reload` | pass |
| F-init has no training artifact | `test_f_init_never_has_a_training_artifact` | pass |

The trained-origin path is **correctly unusable today**: `training/gate.py::assert_training_authorized`
raises, so no genuine trained artifact can exist until approval. The loader's refusal is the intended
state, not a missing connection.

### 4.4 Seed pairing

| Stream | Derivation | Evidence |
|---|---|---|
| Environment | `[master, campaign_seed, episode, 1]`, condition-independent | `test_environment_seed_is_paired_across_conditions`, `test_dispatcher_drives_the_harness_and_rows_round_trip` |
| Network | `[master, condition_code, campaign_seed, 2]` | `test_describe_includes_seed_derivation_and_approval`, registry tests |
| Learning | `[master, condition_code, campaign_seed, 3]` | used by training initialization |
| Structure | `[master, campaign_seed, 4]`, shared by C/D/C′ | `test_structure_stream_is_shared_by_c_d_and_c_prime` |
| Training | disjoint from campaign/pilot; explicit map | `test_pairing_must_be_explicit_and_complete`, `test_initialization_refuses_a_shared_training_seed` |
| Seed-set disjointness | E/E-full training, campaign, pilot | `test_condition_e_refuses_overlapping_seed_sets`, `test_seed_sets_must_be_non_empty_and_disjoint` |

Environment pairing is the mechanical basis of every confirmatory contrast. The dispatcher passes the
same `environment_seed` to both arms of a pair, and the A′/C′ control reuses the exact mirror run
(`test_a_prime_reuses_the_paired_mirror_artefact` verifies the shared seed and the mirror result
object). No condition-specific environment reseeding was found.

**Gap (declared, not a defect):** the campaign↔training map is a caller input
(`training/seeding.py::validate_pairing`). REV4 declares no mapping. This is B3 in the decision
register.

### 4.5 Environment pairing

| Requirement | Evidence | Result |
|---|---|---|
| A pair sees the same environment seed | `test_dispatcher_drives_the_harness_and_rows_round_trip`, `test_a_prime_reuses_the_paired_mirror_artefact` | pass |
| The floor replays the paired seeds | `test_floor_and_conventional_routes_use_the_declared_interface` | pass |
| Environment seeds are derived once and recorded | `seeds.py::environment_seed`; row field | pass |
| A row for a different episode is refused | `test_runner_rejects_a_row_for_another_episode` | pass |

**Gap (declared):** training-episode environment seeds are caller-supplied (B4). They are not the
evaluation seeds by construction only if the caller supplies a disjoint schedule; the engine records
every seed used.

### 4.6 Reward handling

| Requirement | Evidence | Result |
|---|---|---|
| B/D receive the step reward at delivery time | `test_condition_b_runs_learning_updates_through_the_live_stepper`, `test_condition_d_runs_learning_on_the_exchanged_graph` | pass |
| A zero-eta mirror still executes the rule | `test_zero_pathway_invariants_refuse_a_nonzero_eta`, `test_a_prime_cannot_run_without_the_zero_hook` | pass |
| Modulating reward is not reordered | `AppendedRewardStream` (time-ordered) and plastic hook tests | pass |
| Non-finite reward is refused | `training/engine.py` finite check; engine tests | pass (static + test) |
| Evaluation reward is recorded per episode | row schema; `PHASE_8_RECORD_FIELDS` | pass |

The plastic hook explicitly records that modulation is a computational variable, not a neurotransmitter
measurement; that limitation is preserved in `describe()`.

### 4.7 Result schema

| Check | Evidence | Result |
|---|---|---|
| Closed required-key set | `schema.py:REQUIRED_EPISODE_KEYS`; `test_malformed_row_is_rejected` | pass |
| Unknown keys rejected | `test_malformed_row_is_rejected` | pass |
| One update dummy row validates | `test_one_update_dummy_episode_validates` | pass |
| Floor and control rows are recordable | `test_floor_and_control_rows_are_recordable` | pass |
| Episode key `(condition, seed, episode)` unique | `test_duplicate_episode_keys_are_refused` | pass |
| Store round-trip | `test_episode_store_round_trip` | pass |
| Torn tail reported, not repaired | `test_torn_tail_is_reported_not_repaired` | pass |
| Invalid row never written | `test_invalid_row_is_never_written` | pass |

The schema is stricter than "enough fields": it rejects an unknown key rather than ignoring it, so a
new field cannot enter the store silently. Identity evidence for A′/C′ is carried in the row's
`evidence` block (`test_a_prime_reuses_the_paired_mirror_artefact`).

### 4.8 Provenance

| Requirement | Evidence | Result |
|---|---|---|
| Protocol hash bound into the run | CLI `protocol.sha256` = `e4aa9e0f…1547c`; `test_configuration_loads_and_records_hashes` | pass |
| Config hashes recorded | `config_files.{campaign,conditions,environment}.sha256`; `test_configuration_loads_and_records_hashes` | pass |
| Frozen-input hashes recorded | `manifest.py::hash_inputs`; `test_missing_frozen_input_is_an_error`; `test_factory_input_hashes_are_contract_bound_and_cached` | pass |
| Manifest refuses overwrite | `test_manifest_round_trip_and_refusal_to_overwrite` | pass |
| Manifest requires integrity | `test_manifest_rejects_missing_integrity` | pass |
| Structure record pins certificate, graph digest and protocol | `campaign_seed_summary.json`; loader tests | pass |
| Row carries seed derivation and input hashes | row schema; dispatcher tests | pass |
| Training artifact carries config hash, state digest, trainable digest | `test_manifest_records_provenance_and_digests` | pass |

### 4.9 Deterministic replay

| Requirement | Evidence | Result |
|---|---|---|
| Readout training is deterministic | `test_readout_run_is_deterministic` | pass |
| Agent training is deterministic | `test_agent_loop_is_deterministic` | pass |
| Resumed readout is reproducible | `test_resumed_readout_is_reproducible` | pass |
| Sign-flip matches brute-force enumeration | `test_sign_flip_matches_brute_force_enumeration` | pass |
| Graph generation is deterministic | R17 per certificate; regeneration recorded 16/16 | pass (recorded at certification) |
| The store is append-only and idempotent on the episode key | `test_resume_is_idempotent_on_the_episode_key` | pass |
| Campaign resume continues an interrupted run | `test_resume_continues_an_interrupted_run`, `test_runner_executes_resumes_and_writes_one_manifest` | pass |
| Configuration drift is refused on resume | `test_resume_refuses_configuration_drift` | pass |

**Scope limit:** deterministic replay is verified for the training loops and the store. A **resume of
an interrupted training run is parameter-continuous, not bit-identical**, because torch RNG state and
Adam moments are not checkpointed (`rng_restored: false`, `optimizer_state_restored: false` in every
checkpoint). This is B6, an undeclared input, not a silent claim of bit identity.

### 4.10 Failure handling and resume

| Requirement | Evidence | Result |
|---|---|---|
| An episode failure produces a failure record, not a row | `test_episode_failure_is_recorded_and_no_row_is_invented` | pass |
| The failure carries stage and cause type | same test | pass |
| An equivalence mismatch survives the failure | `test_equivalence_mismatch_payload_survives_the_failure` | pass |
| The harness stops without a fabricated row | `test_harness_stops_on_failure_without_a_fabricated_row` | pass |
| Status distinguishes complete, incomplete and torn runs | `test_status_detects_complete_and_incomplete_runs`, `test_status_reports_configuration_drift_and_torn_store` | pass |
| The runner refuses below the memory gate | `test_runner_refuses_below_the_memory_gate` | pass |
| The runner refuses an unresolved design | `test_runner_refuses_an_unresolved_design` | pass |
| Existing result directories are never overwritten | `test_existing_result_directory_is_refused` | pass |
| The CLI cannot start or resume on the current state | `test_cli_start_and_resume_refuse_without_side_effects` | pass |

A′/C′ mismatches are hard stops: the dispatcher raises and the run stops; the analysis marks B and D
INVALID on an identity failure (`test_identity_failure_invalidates_b_and_d`). No silent retry, no
tolerance, no seed substitution was found.

---

## 5. Per-arm integration trace

Legend: **E** = executed synthetic test; **S** = static trace; **R** = recorded artifact verified by
hash; **B** = blocked by an approval/design/resource gate (intended).

| Arm | Build | Graph | Artifact | Seed | Reward | Row | Replay | Failure |
|---|---|---|---|---|---|---|---|---|
| A | E | biological | none | E | E | E | E | E |
| B | E | biological | none | E | E | E | E | E |
| C | E | E/R | none | E | E | E | E | E |
| D | E | E/R | none | E | E | E | E | E |
| E | E | none | B (train gate) | E | E | E | E | E |
| E-full | E | none | B (train gate) | E | E | E | E | E |
| F | E | biological | B (trained origin) | E | E | E | E | E |
| A′ | E | biological | none | E | E | E | E | E |
| C′ | E | E/R | none | E | E | E | E | E |
| Fβ | E | biological | B (trained origin) | E | E | E | E | E |
| F-init | E | biological | derived at init (no training) | E | E | E | E | E |
| floor | E | none | none | E | E (constant) | E | E | E |

The "B" entries are not gaps in wiring: they are the design's refusal to evaluate an untrained model
in a trained arm. The factory's `TrainingArtifacts.readout` / `.agent` raise rather than substituting
an initialized model.

---

## 6. What is verified end to end, and what is verified at boundaries

**Verified end to end with synthetic fixtures:**

- One condition episode through its module produces a validated row (A, B, D, F, floor; with C and E
  through their declared interfaces).
- The dispatcher routes every arm, applies the mirror policy for A′/C′, and records failures.
- The runner iterates a resolved plan, validates each row, writes the append-only store and a
  manifest, and resumes idempotently.
- The analysis consumes a synthetic store, computes the exact sign-flip family, withholds Holm below
  the floor, applies identity checks, the floor decomposition and E1–E5, and refuses to overwrite.
- The viability module classifies U1-A…U1-E from synthetic rows.

**Verified at boundaries, not as one uninterrupted flow:**

- The real `CampaignFactory` constructing every arm and feeding the dispatcher in one process was not
  executed, because the factory's default world is the real game and constructing F/E assets requires
  approval. The factory's selection, hashing, refusal and graph-alignment paths are tested
  individually.
- A full six-condition campaign was not executed; it is prohibited and would be meaningless before
  the design and approval gates resolve.
- Training artifacts were never produced; the trained-origin path is therefore verified only by its
  refusals and by synthetic fixtures written under `origin = "synthetic_fixture"`.

This is the correct boundary for a readiness audit: the components are individually proven and the
joints are proven, but the assembled run is deliberately not performed.

---

## 7. Open inputs found by the audit

These are recorded so they cannot be mistaken for defects and cannot be silently filled in. All are
carried in `PHASE_8_PROTOCOL_DECISION_REGISTER.md`.

| ID | Open input | Enforcement point | Consequence if left open |
|---|---|---|---|
| B1 | REV4 §12 unapproved; U1–U18 proposed | `campaign/protocol.py::approval_status`, `training/gate.py::assert_training_authorized` | every execution path refuses |
| B2 | `n_seeds_selected` null | `training/gate.py::assert_design_resolved`, `registry.py::evaluation_plan`, runner | no plan, no artifact, no campaign |
| B3 | campaign↔training pairing | `training/seeding.py::validate_pairing` | no artifact can be addressed to a seed |
| B4 | training-episode environment seeds | `training/engine.py` callable/int parameter | training cannot be reproducibly scheduled |
| B5 | checkpoint cadence/retention/format | `training/checkpoint.py` caller inputs | no resume policy exists |
| B6 | RNG/optimizer restoration | checkpoint flags are false | resume is parameter-continuous, not bit-identical |
| G3 | §9.3 deviation unresolved | `campaign/protocol.py` deviation block; memory preflight | campaign inherits a recorded deviation |
| RES | machine below 4 GiB | `config.py::memory_preflight` | no graph randomisation, campaign or training |

Documentation-level observations (no behavioural effect):

1. The analysis and registry error messages refer to "REV3 U14" (`analysis.py:1414`,
   `registry.py:196`) although the governing protocol is REV4. The logic is correct; the label is
   stale.
2. The CLI blocker text names "the 10.7/10.8 pilot decision" while REV4 §10.8 is the single pilot-2
   stage. The logic is correct; the stage label is ambiguous.
3. The viability and analysis modules carry their own copies of the U1/E3/E4 constants. They agree
   with the config values now; a future config edit would not propagate automatically. This is
   acceptable for frozen constants but should be checked at the 10.11 stage.

None of these changes a result, and none is fixed in place during a readiness pass.

---

## 8. Residual risks

1. **Boundary composition.** Passing each boundary does not prove that a composed campaign produces
   identical rows under the real factory. The first two seeds of stage 10.10 are the declared
   integration proof; they are not replaced by this audit.
2. **Fixture-to-real gap.** The synthetic 32-node network and the 20–60 step game cap do not exercise
   BANC-scale memory, real sensory drift, or the 900-update cap. Performance and failure modes at
   scale remain unmeasured in this pass.
3. **Training artifact availability.** F, Fβ, E and E-full cannot be evaluated until genuine trained
   artifacts exist; the loader refuses substitutes, correctly.
4. **Resume semantics.** A resumed run is not bit-identical to an uninterrupted one (B6). Any plan
   that relies on resuming during the campaign must record this.
5. **G3 provenance.** The certified graphs carry a §9.3 deviation; a campaign run on them inherits it.

---

## 9. What this audit does not establish

- It does not demonstrate any biological performance, any effect of any condition, or the viability of
  the connectome as a controller. Every result above is synthetic.
- It does not approve any U-item or the protocol.
- It does not certify the campaign as executable, compliant or complete.
- It does not verify the real factory on the real game; that is stage 10.10's job.
- It does not claim that the six conditions have been run together.

**Audit conclusion:** the campaign path for all six conditions and every declared control is
implemented, connected, schema-validated, provenance-bound and failure-safe at the interface level.
No functional integration defect was found. Execution remains blocked by approval, design resolution,
the G3 deviation and the memory gate, exactly as the protocol requires.
