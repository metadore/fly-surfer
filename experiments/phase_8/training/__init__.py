"""Phase 8 G4 training-artifact pipeline.

SCIENTIFIC STATUS
    This package implements the infrastructure that would produce and load
    validated training artifacts for F, Fβ and E. It does not train anything,
    does not generate a trained artifact, runs no episode and authorises no
    campaign. REV4 §12 is unapproved, U1–U18 remain ``PROPOSED``, and
    ``design.n_seeds_selected`` is null.

    Stages are separate modules:

    * ``initialization`` — deterministic seeded model construction;
    * ``plan`` — the declared training interface (budget/seed expansion) and an
      unconditional refusal to run;
    * ``engine`` — the declared F/Fβ and E/E-full training loops, reachable only
      through a ``synthetic_fixture`` context; ``checkpoint`` — resumable
      parameter/counter state that is never a training artifact;
    * ``validation`` — manifest schema, digests and condition compatibility;
    * ``artifacts`` — serialization, reload and SHA-256 integrity;
    * ``loader`` — verified loading into ``TrainingArtifacts`` for the existing
      campaign factory.

    Synthetic fixtures are the only artifacts this task can write. They are
    initialized, untrained state, marked ``origin = "synthetic_fixture"``, and
    rejected by the campaign loader unless a test explicitly overrides it.
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
)
from .engine import (
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
from .initialization import InitializedModel, initialize, initialize_all
from .loader import (
    DEFAULT_REQUIRED,
    LoadedArtifacts,
    check_factory_compatibility,
    discover_artifact_directories,
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
    "CHECKPOINT_NAME",
    "CHECKPOINT_SCHEMA_VERSION",
    "CONFIRMATORY_CONDITIONS",
    "Checkpoint",
    "DEFAULT_REQUIRED",
    "DesignUnresolvedError",
    "E_GRADIENT_UPDATES",
    "EXPLORATORY_CONDITIONS",
    "EXPECTED_FEATURES",
    "InitializedModel",
    "LoadedArtifacts",
    "MANIFEST_NAME",
    "MODES",
    "ORIGINS",
    "PARAMETERS_NAME",
    "PROTOCOL_MODE",
    "READOUT_CONDITIONS",
    "READOUT_EPISODES_PER_SEED",
    "READOUT_INIT_STD",
    "RestoredCheckpoint",
    "STAGES",
    "SYNTHETIC_MODE",
    "TOOL_NAME",
    "TRAINABLE_CONDITIONS",
    "TRAINING_ROOT",
    "TrainingConfig",
    "TrainingConfigError",
    "TrainingEntry",
    "TrainingError",
    "TrainingNotAuthorized",
    "TrainingPlan",
    "TrainingRun",
    "TrainingRunContext",
    "artifact_directory",
    "artifact_seeds",
    "assert_condition_compatibility",
    "assert_design_resolved",
    "assert_expected_config",
    "assert_training_authorized",
    "build_manifest",
    "build_training_plan",
    "check_factory_compatibility",
    "check_readout_pair",
    "checkpoint_directory",
    "describe_checkpoint_interface",
    "describe_engine",
    "describe_interface",
    "design_status",
    "discover_artifact_directories",
    "initialize",
    "initialize_all",
    "load_training_artifacts",
    "model_architecture",
    "model_kind",
    "model_state",
    "prepare_campaign_artifacts",
    "protocol_context",
    "read_artifact",
    "read_checkpoint",
    "read_manifest",
    "restore_checkpoint",
    "run_training",
    "state_digest",
    "synthetic_context",
    "train_agent",
    "train_readout",
    "training_authorization_status",
    "validate_checkpoint",
    "validate_manifest",
    "validate_pairing",
    "validate_training_config",
    "verify_artifact_location",
    "write_artifact",
    "write_checkpoint",
]
