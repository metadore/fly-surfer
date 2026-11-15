"""Phase 5: computational reward, eligibility traces and plasticity models.

Nothing in this package is a biological measurement. A reward is an external
task scalar, a prediction error is the error of a declared value model, an
eligibility trace is a short-lived model tag attached to a plastic edge, and a
learned weight is a model output of a declared computational rule.
"""

from __future__ import annotations

from .checkpoint import (
    graph_checksum,
    load_checkpoint,
    policy_digest,
    save_checkpoint,
)
from .config import PlasticityConfig, load_plasticity_config
from .diagnostics import (
    memory_breakdown,
    spike_hash,
    summarize_updates,
    trace_diagnostics,
    weight_diagnostics,
)
from .engine import PlasticityEngine
from .reward import (
    PredictorConfig,
    RewardConfig,
    RewardEvent,
    RewardLogger,
    RewardPrediction,
    RewardSchedule,
    RewardStatistics,
    RewardSystemConfig,
    ScriptedRewardProvider,
    TabularValuePredictor,
    load_reward_system_config,
    reward_statistics,
    shuffled_reward_schedule,
)
from .rules import RuleConfig, ThreeFactorRule, UpdateReport
from .traces import (
    EligibilityStore,
    SparseDelayLine,
    TraceConfig,
    coincident_edges,
    load_trace_config,
)
from .weights import WeightBounds, WeightState

__all__ = [
    "EligibilityStore",
    "PlasticityConfig",
    "PlasticityEngine",
    "PredictorConfig",
    "RewardConfig",
    "RewardEvent",
    "RewardLogger",
    "RewardPrediction",
    "RewardSchedule",
    "RewardStatistics",
    "RewardSystemConfig",
    "RuleConfig",
    "ScriptedRewardProvider",
    "SparseDelayLine",
    "TabularValuePredictor",
    "ThreeFactorRule",
    "TraceConfig",
    "UpdateReport",
    "WeightBounds",
    "WeightState",
    "coincident_edges",
    "graph_checksum",
    "load_checkpoint",
    "load_plasticity_config",
    "load_reward_system_config",
    "load_trace_config",
    "memory_breakdown",
    "policy_digest",
    "reward_statistics",
    "save_checkpoint",
    "shuffled_reward_schedule",
    "spike_hash",
    "summarize_updates",
    "trace_diagnostics",
    "weight_diagnostics",
]
