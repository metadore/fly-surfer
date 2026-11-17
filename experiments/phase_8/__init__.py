"""Phase 8 campaign infrastructure (G5) and analysis (G6).

PROTOCOL STATUS
    ``docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md`` is a draft. Nothing
    in this package authorises a campaign: :func:`config.require_memory_gate`
    enforces the §9.3 gate, :meth:`config.CampaignConfig.active_seeds` refuses
    to resolve a design whose pilot decision is unrecorded, and the campaign
    runner is only safe once the protocol is approved (REV4 §10.0).

Modules
    ``config``    strict loaders for ``configs/phase_8/*.yaml``
    ``seeds``     declared seed derivation (REV3 §6.2, §6.3, R18)
    ``schema``    versioned episode-row and manifest schemas + validators
    ``store``     append-only JSONL store with resume-by-key
    ``manifest``  run manifest, frozen input hashes, environment capture
    ``registry``  arms and the C1–C4 confirmatory family
    ``analysis``  exact sign-flip, Holm, bootstrap, decompositions and E1–E5
"""

from .analysis import (
    ANALYSIS_VERSION,
    AnalysisError,
    analyse_campaign,
    analyse_store,
    design_summary,
    exact_sign_flip,
    exact_sign_test,
    holm_adjust,
    paired_bootstrap,
)
from .config import (
    CampaignConfig,
    ConditionsConfig,
    ConfigError,
    EnvironmentConfig,
    MemoryGateError,
    Phase8Config,
    load_phase8_config,
    memory_preflight,
    require_memory_gate,
)
from .manifest import build_manifest, hash_inputs, load_manifest, write_manifest
from .registry import (
    CONFIRMATORY_CONTRASTS,
    ConditionSpec,
    build_registry,
    confirmatory_contrasts,
    default_registry,
    evaluation_plan,
)
from .schema import (
    EPISODE_SCHEMA_VERSION,
    EPISODE_STATUSES,
    MANIFEST_SCHEMA_VERSION,
    SchemaError,
    episode_key,
    validate_episode_row,
    validate_manifest,
    validate_rows,
)
from .runner import CampaignRunner
from .seeds import (
    ARM_IDS,
    CONDITION_IDS,
    FLOOR_ID,
    MASTER_SEED,
    describe_derivation,
    environment_seed,
    seed_plan,
)
from .store import (
    DuplicateEpisodeError,
    EpisodeStore,
    ExistingResultError,
    StoreError,
    read_store,
    resolve_run_directory,
)

__all__ = [
    "ANALYSIS_VERSION",
    "ARM_IDS",
    "AnalysisError",
    "CONDITION_IDS",
    "CONFIRMATORY_CONTRASTS",
    "CampaignConfig",
    "CampaignRunner",
    "ConditionSpec",
    "ConditionsConfig",
    "ConfigError",
    "DuplicateEpisodeError",
    "EPISODE_SCHEMA_VERSION",
    "EPISODE_STATUSES",
    "EnvironmentConfig",
    "EpisodeStore",
    "ExistingResultError",
    "FLOOR_ID",
    "MANIFEST_SCHEMA_VERSION",
    "MASTER_SEED",
    "MemoryGateError",
    "Phase8Config",
    "SchemaError",
    "StoreError",
    "analyse_campaign",
    "analyse_store",
    "build_manifest",
    "build_registry",
    "confirmatory_contrasts",
    "default_registry",
    "describe_derivation",
    "design_summary",
    "environment_seed",
    "episode_key",
    "evaluation_plan",
    "exact_sign_flip",
    "exact_sign_test",
    "hash_inputs",
    "holm_adjust",
    "load_manifest",
    "load_phase8_config",
    "memory_preflight",
    "paired_bootstrap",
    "read_store",
    "require_memory_gate",
    "resolve_run_directory",
    "seed_plan",
    "validate_episode_row",
    "validate_manifest",
    "validate_rows",
    "write_manifest",
]
