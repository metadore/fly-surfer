"""Episode execution and schema-row assembly for Phase 8 conditions.

SCIENTIFIC STATUS
    One episode is one recorded run of a declared condition. The row produced
    here is a measurement of a model, not of a fly. ``survival_score`` is the
    capped number of completed game updates as REV4 §7.6 defines it; it is not
    a biological endpoint.

Two execution paths exist and they share the row schema:

* neural (A, B, C, D, F) — ``environment.live_loop.NeuralClosedLoop``;
* conventional (E, E-full) and the substrate-free floor — the game's
  five-tuple ``reset``/``step`` API with no neural substrate at all.

The floor path is a replay control. It is recorded as rows because the
analysis compares every condition against it, but it is not a neural arm.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping

import numpy as np

from environment.live_loop import NeuralClosedLoop
from motor.populations import ACTION_POPULATIONS
from readout.ablation import ABLATION_LABELS

from ..schema import EPISODE_SCHEMA_VERSION, validate_episode_row
from .base import (
    Components,
    ConditionError,
    requirements_for,
    spec_for,
    validate_components,
)

NO_ACTION = "NO_ACTION"


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trace_digest(records: list[dict]) -> str:
    """Digest of the action/reward trace for rows without a spike recorder."""
    return _digest(
        [
            [
                record["update"],
                record["action"],
                record["reward"],
                bool(record["terminated"]),
                bool(record["truncated"]),
            ]
            for record in records
        ]
    )


def motor_summary(records: list[dict]) -> dict | None:
    """Aggregate the per-decision motor blocks for the analysis evidence."""
    blocks = [
        record["motor_activity"]
        for record in records
        if isinstance(record.get("motor_activity"), Mapping)
    ]
    if not blocks:
        return None
    per_population = {
        action: int(sum(block[action]["spikes"] for block in blocks))
        for action in ACTION_POPULATIONS
    }
    return {
        "decisions": len(blocks),
        "decisions_with_motor_spike": int(
            sum(1 for block in blocks if block["any_motor_spike"])
        ),
        "total_motor_spikes": int(
            sum(block["total_motor_spikes"] for block in blocks)
        ),
        "windows_with_motor_spikes": int(
            sum(1 for block in blocks if block["any_motor_spike"])
        ),
        "per_population_spikes": per_population,
        "window_ms": blocks[0]["window_ms"],
    }


def decision_classes(records: list[dict]) -> dict | None:
    """Counts of the four ablation labels across one episode (REV4 §3.6.3)."""
    counts = {name: 0 for name in ABLATION_LABELS}
    seen = 0
    for record in records:
        block = record.get("readout")
        if not isinstance(block, Mapping):
            continue
        ablation = block.get("ablation")
        if not isinstance(ablation, Mapping):
            continue
        label = ablation.get("label")
        if label not in counts:
            raise ConditionError(f"unknown ablation label {label!r}")
        counts[label] += 1
        seen += 1
    return counts if seen else None


def row_termination(
    summary: Mapping[str, Any], max_game_updates: int
) -> tuple[bool, bool, str | None]:
    """Row-level termination, flagging a cap stop as truncation (REV4 §5.1).

    ``NeuralClosedLoop`` stops at the update limit without rewriting its own
    summary. The row schema requires a completed episode to be terminated or
    truncated, and the protocol defines a cap-reaching episode as truncated:
    the survival score is recorded at the cap and the episode is flagged.
    """
    terminated = bool(summary["terminated"])
    truncated = bool(summary["truncated"])
    reason = summary["termination_reason"]
    if not terminated and not truncated and int(summary["updates"]) >= int(
        max_game_updates
    ):
        truncated = True
        reason = "max_game_updates"
    return terminated, truncated, reason


def build_row(
    *,
    condition: str,
    role: str,
    seed: int,
    episode: int,
    environment_seed: int,
    training: bool,
    steps: int,
    max_game_updates: int,
    total_reward: float,
    terminated: bool,
    truncated: bool,
    termination_reason: str | None,
    action_counts: Mapping[str, int],
    motor_spikes: int,
    spike_sha256: str | None,
    action_sha256: str | None,
    weights_before: str | None,
    weights_after: str | None,
    config_hashes: Mapping[str, Any],
    input_hashes: Mapping[str, Any],
    started_at: str,
    wall_time_s: float,
    status: str = "ok",
    error: str | None = None,
    optional: Mapping[str, Any] | None = None,
) -> dict:
    """Assemble one row and validate it before it can reach a store."""
    counts = {str(key): int(value) for key, value in action_counts.items()}
    row = {
        "schema_version": EPISODE_SCHEMA_VERSION,
        "condition": str(condition),
        "role": str(role),
        "seed": int(seed),
        "episode": int(episode),
        "environment_seed": int(environment_seed),
        "training": bool(training),
        "steps": int(steps),
        "observed_updates": int(steps),
        "survival_score": float(min(int(steps), int(max_game_updates))),
        "max_game_updates": int(max_game_updates),
        "total_reward": float(total_reward),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "termination_reason": termination_reason,
        "action_counts": counts,
        "no_action_fraction": (
            round(counts.get(NO_ACTION, 0) / int(steps), 9) if steps else 0.0
        ),
        "motor_spikes": int(motor_spikes),
        "spike_sha256": spike_sha256,
        "action_sha256": action_sha256,
        "weights_before": weights_before,
        "weights_after": weights_after,
        "config_hashes": dict(config_hashes),
        "input_hashes": dict(input_hashes),
        "started_at": str(started_at),
        "wall_time_s": round(float(wall_time_s), 6),
    }
    if status != "ok":
        row["status"] = str(status)
    if error is not None:
        row["error"] = str(error)
    if optional:
        for key, value in optional.items():
            if value is not None:
                row[key] = value
    return validate_episode_row(row, expected_condition=condition)


def error_row(
    *,
    condition: str,
    role: str,
    seed: int,
    episode: int,
    environment_seed: int,
    training: bool,
    max_game_updates: int,
    config_hashes: Mapping[str, Any],
    input_hashes: Mapping[str, Any],
    started_at: str,
    wall_time_s: float,
    error: str,
    steps: int = 0,
    action_counts: Mapping[str, int] | None = None,
) -> dict:
    """A valid row for an episode that failed; survival is the capped steps."""
    counts = dict(action_counts or {})
    if not counts:
        if steps:
            raise ConditionError(
                "an error row that completed steps must record its actions"
            )
        counts = {NO_ACTION: 0}
    return build_row(
        condition=condition,
        role=role,
        seed=seed,
        episode=episode,
        environment_seed=environment_seed,
        training=training,
        steps=int(steps),
        max_game_updates=max_game_updates,
        total_reward=0.0,
        terminated=False,
        truncated=False,
        termination_reason=None,
        action_counts=action_counts or {},
        motor_spikes=0,
        spike_sha256=None,
        action_sha256=None,
        weights_before=None,
        weights_after=None,
        config_hashes=config_hashes,
        input_hashes=input_hashes,
        started_at=started_at,
        wall_time_s=wall_time_s,
        status="error",
        error=error,
    )


# ---------------------------------------------------------------------------
# neural conditions
# ---------------------------------------------------------------------------


def neural_episode(
    condition_id: str,
    components: Components,
    *,
    seed: int,
    episode: int,
    environment_seed: int,
    config_hashes: Mapping[str, Any],
    input_hashes: Mapping[str, Any],
    max_game_updates: int,
    training: bool = False,
    spec: Any | None = None,
) -> dict:
    """Run one neural episode and return its row plus the run artefacts."""
    requirements = validate_components(condition_id, components, spec)
    if int(max_game_updates) < 1:
        raise ConditionError("max_game_updates must be positive")
    if training and condition_id not in ("F", "F_beta"):
        raise ConditionError(
            f"{condition_id} has no separate training episode; plasticity runs "
            "during evaluation (REV4 §3.4 row 9)"
        )
    declared = spec_for(condition_id, spec)
    neural = components.neural
    stepper = neural.stepper
    state = getattr(stepper, "weight_state", None)
    structure_before = None if state is None else state.structural_digest()
    initial_before = None if state is None else state.initial_digest()
    resets_before = int(getattr(stepper, "resets", 0))

    loop = NeuralClosedLoop(
        neural.adapter,
        stepper,
        neural.drive,
        neural.action_decoder,
        clock=neural.clock,
        window_ms=neural.window_ms,
        max_updates=int(max_game_updates),
        decision_source=neural.decision_source,
        # REV4 §3.6.1: the per-decision motor block is recorded for every
        # decision in every neural condition, independent of the fixed decoder.
        record_motor_activity=True,
        sufficiency=neural.sufficiency,
        post_update=neural.post_update,
    )
    started_at = utc_timestamp()
    started = time.perf_counter()
    run = loop.run(seed=int(environment_seed))
    wall_time = time.perf_counter() - started
    summary = run["summary"]
    records = run["records"]

    if int(summary["neural_resets_during_episode"]) != 0:
        raise ConditionError(
            "the network was reset between game updates; state continuity is "
            "broken (REV4 §3.8.2)"
        )
    if state is not None:
        if state.structural_digest() != structure_before:
            raise ConditionError("the structural weight layer changed")
        if state.initial_digest() != initial_before:
            raise ConditionError("the initial weight layer changed")
    if requirements.stepper_kind == "fixed" and not summary["weights_unchanged"]:
        raise ConditionError(
            f"{condition_id} must hold the effective weights fixed, but the "
            "before/after fingerprints differ"
        )

    training_update = None
    if condition_id in ("F", "F_beta") and training and hasattr(
        neural.decision_source, "update"
    ):
        training_update = neural.decision_source.update()

    structure = neural.structure
    evidence = {
        "stepper_kind": "plastic" if state is not None else "fixed",
        "stepper_resets_this_episode": int(getattr(stepper, "resets", 0))
        - resets_before,
        "structure_digest": structure_before,
        "initial_digest": initial_before,
        "delta_digest": None if state is None else state.delta_digest(),
        "effective_digest": None if state is None else state.effective_digest(),
        "weights_changed": not bool(summary["weights_unchanged"]),
        "structure_unchanged": True,
        "declared_trains": list(declared.trains),
        "feature_to_population_assignment": (
            "Phase 4H.4 hypothesis or convention, not a measured pathway"
        ),
    }
    if requirements.stepper_kind == "plastic":
        reports = tuple(getattr(stepper, "update_reports", ()))
        weight_updates = run["weight_updates"]
        evidence["plasticity_path"] = {
            "mode": (
                "rule_executed_zero_delta"
                if float(stepper.eta) == 0.0
                else "rule_executed"
            ),
            "eta": float(stepper.eta),
            "n_update_reports": len(reports),
            "n_hook_calls": len(weight_updates),
            "hook_modes": sorted(
                {
                    str(entry.get("mode"))
                    for entry in weight_updates
                    if isinstance(entry, Mapping)
                }
            ),
            "hook_reports_digest": _digest(weight_updates),
        }
    if structure is not None:
        evidence["structure"] = {
            "graph_digest": structure["graph_digest"],
            "randomization_passed": bool(
                structure["randomization_quality"]["passed"]
            ),
        }

    optional: dict[str, Any] = {
        "motor_summary": motor_summary(records),
        "decision_classes": decision_classes(records),
        "evidence": evidence,
        "weight_fingerprint": {
            "before": summary["weights_before"],
            "after": summary["weights_after"],
        },
        "randomization_quality": (
            None if structure is None else structure["randomization_quality"]
        ),
        "training_update": training_update,
        "connectome_unchanged": True,
    }
    if neural.decision_source is not None:
        optional["readout"] = neural.decision_source.describe()

    terminated, truncated, termination_reason = row_termination(
        summary, int(max_game_updates)
    )
    row = build_row(
        condition=condition_id,
        role=declared.role,
        seed=seed,
        episode=episode,
        environment_seed=environment_seed,
        training=training,
        steps=int(summary["updates"]),
        max_game_updates=max_game_updates,
        total_reward=float(summary["total_reward"]),
        terminated=terminated,
        truncated=truncated,
        termination_reason=termination_reason,
        action_counts=summary["action_counts"],
        motor_spikes=int(summary["motor_spikes"]),
        spike_sha256=run["fingerprint"]["spike_sha256"],
        action_sha256=run["fingerprint"]["action_reward_sha256"],
        weights_before=summary["weights_before"]["sha256"],
        weights_after=summary["weights_after"]["sha256"],
        config_hashes=config_hashes,
        input_hashes=input_hashes,
        started_at=started_at,
        wall_time_s=wall_time,
        optional=optional,
    )
    return {
        "condition": condition_id,
        "row": row,
        "records": records,
        "summary": summary,
        "fingerprint": run["fingerprint"],
        "run": run,
        "stepper": stepper,
        "decision_source": neural.decision_source,
        "structure": structure,
        "weight_updates": run["weight_updates"],
    }


# ---------------------------------------------------------------------------
# conventional condition E
# ---------------------------------------------------------------------------


def conventional_episode(
    condition_id: str,
    components: Components,
    *,
    seed: int,
    episode: int,
    environment_seed: int,
    config_hashes: Mapping[str, Any],
    input_hashes: Mapping[str, Any],
    max_game_updates: int,
    training: bool = False,
    spec: Any | None = None,
) -> dict:
    """Run E (or E-full) on the game's five-tuple API. No neural substrate."""
    validate_components(condition_id, components, spec)
    declared = spec_for(condition_id, spec)
    conventional = components.conventional
    environment = conventional.environment
    agent = conventional.agent
    encoder = conventional.encoder
    if int(max_game_updates) < 1:
        raise ConditionError("max_game_updates must be positive")
    if training and not getattr(agent, "training", False):
        agent.train()

    started_at = utc_timestamp()
    started = time.perf_counter()
    environment.reset(seed=int(environment_seed))
    agent.reset_episode()

    action_counts: Counter = Counter()
    records: list[dict] = []
    total_reward = 0.0
    terminated = truncated = False
    termination_reason: str | None = None
    while not (terminated or truncated) and len(records) < int(max_game_updates):
        update = len(records) + 1
        features = encoder.encode(environment.game_state)
        action_index, decision = agent.act(features, training=training)
        action = str(decision["action"])
        observation, reward, terminated, truncated, info = environment.step(action)
        del observation
        number = float(reward)
        if training:
            agent.record_reward(number)
        action_counts[action] += 1
        total_reward += number
        records.append(
            {
                "update": update,
                "action": action,
                "reward": number,
                "terminated": bool(terminated),
                "truncated": bool(truncated),
            }
        )
        reason = _conventional_termination_reason(info)
        if reason:
            termination_reason = reason
    wall_time = time.perf_counter() - started

    training_update = None
    if training:
        training_update = agent.finish_episode()

    optional: dict[str, Any] = {
        "evidence": {
            "neural_substrate": "none",
            "privileged_input": False,
            "feature_set": int(encoder.n_features),
            "agent": type(agent).__name__,
            "policy_parameter_digest": (
                agent.parameter_digest()
                if callable(getattr(agent, "parameter_digest", None))
                else None
            ),
            "declared_trains": list(declared.trains),
        },
        "training_update": training_update,
    }
    terminated, truncated, termination_reason = row_termination(
        {
            "updates": len(records),
            "terminated": terminated,
            "truncated": truncated,
            "termination_reason": termination_reason,
        },
        int(max_game_updates),
    )
    row = build_row(
        condition=condition_id,
        role=declared.role,
        seed=seed,
        episode=episode,
        environment_seed=environment_seed,
        training=training,
        steps=len(records),
        max_game_updates=max_game_updates,
        total_reward=total_reward,
        terminated=terminated,
        truncated=truncated,
        termination_reason=termination_reason,
        action_counts=dict(action_counts),
        motor_spikes=0,
        spike_sha256=None,
        action_sha256=trace_digest(records),
        weights_before=None,
        weights_after=None,
        config_hashes=config_hashes,
        input_hashes=input_hashes,
        started_at=started_at,
        wall_time_s=wall_time,
        optional=optional,
    )
    return {
        "condition": condition_id,
        "row": row,
        "records": records,
        "agent": agent,
        "encoder": encoder,
    }


def _conventional_termination_reason(info: Any) -> str | None:
    if not isinstance(info, Mapping):
        return None
    direct = info.get("termination_reason")
    if isinstance(direct, str) and direct:
        return direct
    block = info.get("fly_surfer")
    if isinstance(block, Mapping):
        reward = block.get("reward")
        if isinstance(reward, Mapping):
            reason = reward.get("termination_reason")
            if isinstance(reason, str) and reason:
                return reason
    return None


# ---------------------------------------------------------------------------
# substrate-free floor
# ---------------------------------------------------------------------------


def floor_episode(
    adapter: Any,
    *,
    seed: int,
    episode: int,
    environment_seed: int,
    config_hashes: Mapping[str, Any],
    input_hashes: Mapping[str, Any],
    max_game_updates: int,
) -> dict:
    """Replay the paired environment seed with a constant NO_ACTION policy.

    No substrate is built and no spikes are read. This is a floor, not a
    neural subtrate arm, and its row says so.
    """
    if int(max_game_updates) < 1:
        raise ConditionError("max_game_updates must be positive")
    started_at = utc_timestamp()
    started = time.perf_counter()
    adapter.reset(seed=int(environment_seed))
    records: list[dict] = []
    action_counts: Counter = Counter()
    total_reward = 0.0
    terminated = truncated = False
    termination_reason: str | None = None
    while not (terminated or truncated) and len(records) < int(max_game_updates):
        step = adapter.step(None)
        action = step.mapping.executed_action
        if action != NO_ACTION:
            raise ConditionError(
                f"the floor policy executed {action!r}; it must be constant "
                "NO_ACTION"
            )
        action_counts[action] += 1
        total_reward += float(step.step_reward.total)
        records.append(
            {
                "update": len(records) + 1,
                "action": action,
                "reward": float(step.step_reward.total),
                "terminated": bool(step.terminated),
                "truncated": bool(step.truncated),
            }
        )
        terminated = bool(step.terminated)
        truncated = bool(step.truncated)
        if step.step_reward.termination_reason:
            termination_reason = step.step_reward.termination_reason
    wall_time = time.perf_counter() - started

    terminated, truncated, termination_reason = row_termination(
        {
            "updates": len(records),
            "terminated": terminated,
            "truncated": truncated,
            "termination_reason": termination_reason,
        },
        int(max_game_updates),
    )
    row = build_row(
        condition="floor",
        role="floor",
        seed=seed,
        episode=episode,
        environment_seed=environment_seed,
        training=False,
        steps=len(records),
        max_game_updates=max_game_updates,
        total_reward=total_reward,
        terminated=terminated,
        truncated=truncated,
        termination_reason=termination_reason,
        action_counts=dict(action_counts),
        motor_spikes=0,
        spike_sha256=None,
        action_sha256=trace_digest(records),
        weights_before=None,
        weights_after=None,
        config_hashes=config_hashes,
        input_hashes=input_hashes,
        started_at=started_at,
        wall_time_s=wall_time,
        optional={
            "evidence": {
                "neural_substrate": "none",
                "policy": "constant NO_ACTION",
                "spikes_read": False,
                "is_neural_arm": False,
            }
        },
    )
    return {"condition": "floor", "row": row, "records": records}


__all__ = [
    "NO_ACTION",
    "build_row",
    "conventional_episode",
    "decision_classes",
    "error_row",
    "floor_episode",
    "motor_summary",
    "neural_episode",
    "trace_digest",
    "utc_timestamp",
]
