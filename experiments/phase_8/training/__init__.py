"""Phase 8 G4 training-artifact pipeline.

SCIENTIFIC STATUS
    This package implements the infrastructure that produces and loads
    validated training artifacts for F, Fβ and E. Importing it trains nothing,
    runs no episode and authorises no campaign. D1 approved REV4 §12 and
    U1-U18; D4 declares the B3-B6 training-operation contracts; D5 (2026-11-22)
    authorises exactly six F/Fβ pilot training artifacts at evaluation seeds
    9001-9003 and nothing else. D6 records that B7 has no subject in that plan
    and weakens no gate. ``design.n_seeds_selected`` stays null (U7).

    Stages are separate modules:

    * ``initialization`` — deterministic seeded model construction;
    * ``contracts`` — D4 B3 seed pairing and B4 training environment streams;
    * ``d4`` — the D4 record's validity and its binding to the frozen sources;
    * ``d5`` — the D5/D6 records and the narrow per-artifact training authority;
    * ``pilot`` — the exact six-artifact D5 plan and its refused scope;
    * ``pilot_training`` — the production F/Fβ training loop with per-episode
      exact checkpoints (reachable only through the D5 authority);
    * ``pilot_artifact`` — the trained-artifact writer and its provenance;
    * ``plan`` — the declared campaign training interface (still refused);
    * ``engine`` — the declared training loops, reachable only through a
      ``synthetic_fixture`` context; ``checkpoint`` — resumable
      parameter/counter state that is never a training artifact;
    * ``exact_checkpoint`` — D4 B5/B6 exact checkpoints (parameters, optimizer
      moments, every RNG stream) and the equivalence verifier;
    * ``validation`` — manifest schema, digests and condition compatibility;
    * ``artifacts`` — serialization, reload and SHA-256 integrity;
    * ``loader`` — verified loading into ``TrainingArtifacts`` for the existing
      campaign factory.

    Outside the D5-authorised pilot path, synthetic fixtures are the only
    artifacts this package can write. They are initialized, untrained state,
    marked ``origin = "synthetic_fixture"``, and rejected by the campaign
    loader unless a test explicitly overrides it.
"""

from __future__ import annotations

from .artifacts import (
    TOOL_NAME,
    TRAINING_ROOT,
    Artifact,
    artifact_directory,
    build_manifest,
    read_artifact,
    read_manifest,
    verify_artifact_location,
    write_artifact,
)
from .checkpoint import (
    CHECKPOINT_NAME,
    CHECKPOINT_SCHEMA_VERSION,
    Checkpoint,
    RestoredCheckpoint,
    checkpoint_directory,
    describe_checkpoint_interface,
    read_checkpoint,
    restore_checkpoint,
    validate_checkpoint,
    write_checkpoint,
)
from .config import (
    AGENT_CONDITIONS,
    E_GRADIENT_UPDATES,
    READOUT_CONDITIONS,
    READOUT_EPISODES_PER_SEED,
    READOUT_INIT_STD,
    TRAINABLE_CONDITIONS,
    TrainingConfig,
    validate_training_config,
)
from .contracts import (
    B3_DERIVATION,
    B3_NAMESPACE,
    B4_DERIVATION,
    B4_NAMESPACE,
    CONTRACT_VERSION,
    PILOT2C_EVALUATION_SEEDS,
    assert_environment_stream_disjoint,
    derive_b3_pairing,
    describe_training_contracts,
    namespace_digest,
    namespace_seed,
    pairing_map,
    pilot2c_evaluation_environment_seeds,
    training_environment_schedule,
    training_environment_seed,
    validate_b3_pairing,
)
from .d4 import (
    D4_APPROVAL_DATE,
    D4_DECISION_IDS,
    D4_ID,
    D4_RECORD_PATH,
    assert_d4_declared,
    d4_applicability,
    describe_d4,
)
from .d5 import (
    D5_APPROVAL_DATE,
    D5_ID,
    D5_RECORD_PATH,
    D6_APPROVAL_DATE,
    D6_ID,
    D6_RECORD_PATH,
    PILOT_TRAINING_ARTIFACTS,
    PILOT_TRAINING_ARTIFACT_COUNT,
    PILOT_TRAINING_CONDITIONS,
    PILOT_TRAINING_EPISODE_COUNT,
    PILOT_TRAINING_EPISODES,
    PILOT_TRAINING_EVALUATION_SEEDS,
    assert_d5_training_authorized,
    d5_applicability,
    describe_d5,
)
from .errors import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    ArtifactSchemaError,
    DesignUnresolvedError,
    TrainingConfigError,
    TrainingError,
    TrainingNotAuthorized,
)
from .gate import (
    assert_design_resolved,
    assert_training_authorized,
    design_status,
    training_authorization_status,
    training_declarations,
)
from .engine import (
    MODES,
    PROTOCOL_MODE,
    SYNTHETIC_MODE,
    TrainingRun,
    TrainingRunContext,
    describe_engine,
    protocol_context,
    synthetic_context,
    train_agent,
    train_readout,
)
from .exact_checkpoint import (
    EXACT_CHECKPOINT_SCHEMA_VERSION,
    RestoredExactCheckpoint,
    apply_exact_restore,
    assert_resumption_equivalent,
    capture_optimizer_state,
    describe_exact_checkpoint_interface,
    read_exact_checkpoint,
    restore_exact_checkpoint,
    validate_exact_checkpoint,
    verify_equivalence,
    write_exact_checkpoint,
)
from .initialization import InitializedModel, initialize, initialize_all
from .loader import (
    DEFAULT_REQUIRED,
    LoadedArtifacts,
    check_factory_compatibility,
    discover_artifact_directories,
    load_pilot_evaluation_artifacts,
    load_training_artifacts,
    prepare_campaign_artifacts,
)
from .plan import (
    CONFIRMATORY_CONDITIONS,
    EXPLORATORY_CONDITIONS,
    TrainingEntry,
    TrainingPlan,
    build_training_plan,
    describe_interface,
    run_training,
)
from .pilot import (
    DEFAULT_SAMPLING_SEED,
    PILOT_SUBSTRATE,
    PilotArtifactPlan,
    PilotTrainingPlan,
    build_pilot_plan,
    describe_pilot_plan,
    validate_pilot_scope,
)
from .pilot_artifact import (
    EVIDENCE_KINDS,
    TRAINING_RUN_NAME,
    TrainedModelView,
    describe_trained_interface,
    read_training_run,
    verify_trained_artifact,
    write_trained_artifact,
)
from .pilot_training import (
    ENVIRONMENT_REASON,
    PINNED_EPISODE_FIELDS,
    RUNNER_ID,
    PilotEpisodeRunner,
    PilotTrainingResult,
    build_controller,
    run_pilot_artifact,
    run_pilot_plan,
    run_training_loop,
    verify_resume_equivalence,
)
from .seeding import artifact_seeds, validate_pairing
from .state import model_architecture, model_kind, model_state, state_digest
from .validation import (
    ARTIFACT_SCHEMA_VERSION,
    EXPECTED_FEATURES,
    MANIFEST_NAME,
    ORIGINS,
    PARAMETERS_NAME,
    STAGES,
    assert_condition_compatibility,
    assert_expected_config,
    check_readout_pair,
    validate_manifest,
)

__all__ = [
    "AGENT_CONDITIONS",
    "ARTIFACT_SCHEMA_VERSION",
    "Artifact",
    "ArtifactCompatibilityError",
    "ArtifactIntegrityError",
    "ArtifactSchemaError",
    "B3_DERIVATION",
    "B3_NAMESPACE",
    "B4_DERIVATION",
    "B4_NAMESPACE",
    "CHECKPOINT_NAME",
    "CHECKPOINT_SCHEMA_VERSION",
    "CONFIRMATORY_CONDITIONS",
    "CONTRACT_VERSION",
    "Checkpoint",
    "D4_APPROVAL_DATE",
    "D4_DECISION_IDS",
    "D4_ID",
    "D4_RECORD_PATH",
    "D5_APPROVAL_DATE",
    "D5_ID",
    "D5_RECORD_PATH",
    "D6_APPROVAL_DATE",
    "D6_ID",
    "D6_RECORD_PATH",
    "DEFAULT_REQUIRED",
    "DEFAULT_SAMPLING_SEED",
    "DesignUnresolvedError",
    "E_GRADIENT_UPDATES",
    "ENVIRONMENT_REASON",
    "EVIDENCE_KINDS",
    "EXACT_CHECKPOINT_SCHEMA_VERSION",
    "EXPLORATORY_CONDITIONS",
    "EXPECTED_FEATURES",
    "InitializedModel",
    "LoadedArtifacts",
    "MANIFEST_NAME",
    "MODES",
    "ORIGINS",
    "PARAMETERS_NAME",
    "PINNED_EPISODE_FIELDS",
    "PILOT2C_EVALUATION_SEEDS",
    "PILOT_SUBSTRATE",
    "PILOT_TRAINING_ARTIFACTS",
    "PILOT_TRAINING_ARTIFACT_COUNT",
    "PILOT_TRAINING_CONDITIONS",
    "PILOT_TRAINING_EPISODE_COUNT",
    "PILOT_TRAINING_EPISODES",
    "PILOT_TRAINING_EVALUATION_SEEDS",
    "PilotArtifactPlan",
    "PilotEpisodeRunner",
    "PilotTrainingPlan",
    "PilotTrainingResult",
    "PROTOCOL_MODE",
    "READOUT_CONDITIONS",
    "READOUT_EPISODES_PER_SEED",
    "READOUT_INIT_STD",
    "RUNNER_ID",
    "RestoredCheckpoint",
    "RestoredExactCheckpoint",
    "STAGES",
    "SYNTHETIC_MODE",
    "TOOL_NAME",
    "TRAINABLE_CONDITIONS",
    "TRAINING_ROOT",
    "TRAINING_RUN_NAME",
    "TrainingConfig",
    "TrainingConfigError",
    "TrainingEntry",
    "TrainingError",
    "TrainingNotAuthorized",
    "TrainingPlan",
    "TrainingRun",
    "TrainingRunContext",
    "TrainedModelView",
    "apply_exact_restore",
    "artifact_directory",
    "artifact_seeds",
    "assert_condition_compatibility",
    "assert_d4_declared",
    "assert_d5_training_authorized",
    "assert_design_resolved",
    "assert_environment_stream_disjoint",
    "assert_expected_config",
    "assert_resumption_equivalent",
    "assert_training_authorized",
    "build_controller",
    "build_manifest",
    "build_pilot_plan",
    "build_training_plan",
    "capture_optimizer_state",
    "check_factory_compatibility",
    "check_readout_pair",
    "checkpoint_directory",
    "d4_applicability",
    "d5_applicability",
    "derive_b3_pairing",
    "describe_checkpoint_interface",
    "describe_d4",
    "describe_d5",
    "describe_engine",
    "describe_exact_checkpoint_interface",
    "describe_interface",
    "describe_pilot_plan",
    "describe_trained_interface",
    "describe_training_contracts",
    "design_status",
    "discover_artifact_directories",
    "initialize",
    "initialize_all",
    "load_pilot_evaluation_artifacts",
    "load_training_artifacts",
    "model_architecture",
    "model_kind",
    "model_state",
    "namespace_digest",
    "namespace_seed",
    "pairing_map",
    "pilot2c_evaluation_environment_seeds",
    "prepare_campaign_artifacts",
    "protocol_context",
    "read_artifact",
    "read_checkpoint",
    "read_exact_checkpoint",
    "read_manifest",
    "read_training_run",
    "restore_checkpoint",
    "restore_exact_checkpoint",
    "run_pilot_artifact",
    "run_pilot_plan",
    "run_training",
    "run_training_loop",
    "state_digest",
    "synthetic_context",
    "train_agent",
    "train_readout",
    "training_authorization_status",
    "training_declarations",
    "training_environment_schedule",
    "training_environment_seed",
    "validate_b3_pairing",
    "validate_checkpoint",
    "validate_exact_checkpoint",
    "validate_manifest",
    "validate_pairing",
    "validate_pilot_scope",
    "validate_training_config",
    "verify_artifact_location",
    "verify_equivalence",
    "verify_resume_equivalence",
    "verify_trained_artifact",
    "write_artifact",
    "write_checkpoint",
    "write_exact_checkpoint",
    "write_trained_artifact",
]
