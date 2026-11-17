"""Versioned schemas and strict validators for Phase 8 artifacts.

REV3 §8.7 requires a versioned JSON schema for episode rows and for the run
manifest, with a validator that runs before any analysis. This module is that
validator. It rejects a malformed row rather than repairing it: a row that does
not validate is never written, and a store that contains one is not analysed.

Schema version 1 is deliberately strict about top-level keys. A new field is a
schema change and must bump :data:`EPISODE_SCHEMA_VERSION`; silently accepting
unknown keys would let a typo detach a measurement from the analysis.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from readout.features import ACTION_SPACE

from .seeds import ARM_IDS


EPISODE_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1

ROLES = ("reference", "condition", "control", "exploratory", "floor")

REQUIRED_EPISODE_KEYS = frozenset(
    {
        "schema_version",
        "condition",
        "role",
        "seed",
        "episode",
        "environment_seed",
        "training",
        "steps",
        "observed_updates",
        "survival_score",
        "max_game_updates",
        "total_reward",
        "terminated",
        "truncated",
        "termination_reason",
        "action_counts",
        "no_action_fraction",
        "motor_spikes",
        "spike_sha256",
        "action_sha256",
        "weights_before",
        "weights_after",
        "config_hashes",
        "input_hashes",
        "started_at",
        "wall_time_s",
    }
)

OPTIONAL_EPISODE_KEYS = frozenset(
    {
        "status",
        "error",
        "randomization_quality",
        "readout",
        "motor_summary",
        "decision_classes",
        "evidence",
        "connectome_unchanged",
        "weight_fingerprint",
        "training_update",
        "notes",
    }
)

EPISODE_STATUSES = ("ok", "error")

REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "run_id",
        "created_at",
        "protocol",
        "config_hashes",
        "seed_derivation",
        "environment",
        "design",
        "conditions",
        "memory_preflight",
        "environment_capture",
        "input_hashes",
        "integrity",
    }
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class SchemaError(ValueError):
    """An artifact does not satisfy its declared schema version."""


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX64.match(value))


def episode_key(row: Mapping[str, Any]) -> tuple[str, int, int]:
    """The resume key: ``(condition, seed, episode)`` (REV3 §8.3)."""
    try:
        return (str(row["condition"]), int(row["seed"]), int(row["episode"]))
    except (KeyError, TypeError, ValueError):
        raise SchemaError(
            "episode row has no usable (condition, seed, episode) key"
        ) from None


# ---------------------------------------------------------------------------
# episode rows
# ---------------------------------------------------------------------------


def _require_int(row: Mapping[str, Any], name: str, *, minimum: int = 0) -> int:
    value = row[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"{name} must be an integer, got {value!r}")
    if value < minimum:
        raise SchemaError(f"{name} must be >= {minimum}, got {value}")
    return int(value)


def _require_float(row: Mapping[str, Any], name: str) -> float:
    value = row[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"{name} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise SchemaError(f"{name} must be finite, got {value!r}")
    return number


def _require_bool(row: Mapping[str, Any], name: str) -> bool:
    value = row[name]
    if not isinstance(value, bool):
        raise SchemaError(f"{name} must be a bool, got {value!r}")
    return value


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{name} must be a non-empty string")
    return value


def _check_hash_map(value: Any, name: str, *, nested: bool = False) -> dict:
    if not isinstance(value, Mapping) or not value:
        raise SchemaError(f"{name} must be a non-empty mapping")
    result = {}
    for key in value:
        _require_text(key, f"{name} key")
        entry = value[key]
        if nested:
            if not isinstance(entry, Mapping):
                raise SchemaError(f"{name}[{key!r}] must be a mapping")
            if "path" not in entry or "sha256" not in entry:
                raise SchemaError(f"{name}[{key!r}] needs path and sha256")
            _require_text(entry["path"], f"{name}[{key!r}].path")
            digest = entry["sha256"]
        else:
            digest = entry
        if not is_sha256(digest):
            raise SchemaError(f"{name}[{key!r}] is not a SHA-256 hex digest")
        result[key] = entry
    return result


def _check_timestamp(value: Any, name: str) -> str:
    text = _require_text(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise SchemaError(f"{name} is not an ISO-8601 timestamp: {text!r}") from None
    if parsed.tzinfo is None:
        raise SchemaError(f"{name} must carry a timezone offset")
    return text


def validate_episode_row(
    row: Mapping[str, Any],
    *,
    expected_condition: str | None = None,
) -> dict:
    """Validate one episode row and return a plain copy.

    Raises :class:`SchemaError` on any structural, type or consistency
    violation. No value is coerced.
    """
    if not isinstance(row, Mapping):
        raise SchemaError("episode row must be a mapping")

    keys = set(row)
    missing = sorted(REQUIRED_EPISODE_KEYS - keys)
    if missing:
        raise SchemaError(f"episode row is missing required keys: {missing}")
    unknown = sorted(keys - REQUIRED_EPISODE_KEYS - OPTIONAL_EPISODE_KEYS)
    if unknown:
        raise SchemaError(f"episode row has unknown keys: {unknown}")

    if _require_int(row, "schema_version", minimum=1) != EPISODE_SCHEMA_VERSION:
        raise SchemaError(
            f"unsupported episode schema_version {row['schema_version']!r}"
        )

    condition = _require_text(row["condition"], "condition")
    if condition not in ARM_IDS:
        raise SchemaError(f"unknown condition {condition!r}")
    if expected_condition is not None and condition != expected_condition:
        raise SchemaError(
            f"condition {condition!r} does not match the expected {expected_condition!r}"
        )

    role = _require_text(row["role"], "role")
    if role not in ROLES:
        raise SchemaError(f"role must be one of {ROLES}, got {role!r}")

    _require_int(row, "seed", minimum=0)
    _require_int(row, "episode", minimum=0)
    _require_int(row, "environment_seed", minimum=0)
    _require_bool(row, "training")

    steps = _require_int(row, "steps", minimum=0)
    observed = _require_int(row, "observed_updates", minimum=0)
    if observed != steps:
        raise SchemaError(
            f"observed_updates ({observed}) must equal the recorded steps ({steps})"
        )
    cap = _require_int(row, "max_game_updates", minimum=1)
    score = _require_float(row, "survival_score")
    expected_score = float(min(observed, cap))
    if score != expected_score:
        raise SchemaError(
            "the primary outcome must be the capped survival score: "
            f"expected {expected_score}, got {score}"
        )

    _require_float(row, "total_reward")

    status = row.get("status", "ok")
    if status not in EPISODE_STATUSES:
        raise SchemaError(f"status must be one of {EPISODE_STATUSES}, got {status!r}")
    if status == "error":
        _require_text(row.get("error"), "error")
    elif "error" in row:
        raise SchemaError("error may be recorded only on a status='error' row")
    elif steps < 1:
        raise SchemaError("an ok episode must complete at least one update")

    terminated = _require_bool(row, "terminated")
    truncated = _require_bool(row, "truncated")
    if terminated and truncated:
        raise SchemaError("a step cannot be both terminated and truncated")
    if status == "ok" and not (terminated or truncated):
        raise SchemaError("a completed episode must be terminated or truncated")
    reason = row["termination_reason"]
    if reason is not None:
        _require_text(reason, "termination_reason")
    if status == "ok" and truncated and reason is None:
        raise SchemaError("a truncated episode needs a termination_reason")

    counts = row["action_counts"]
    if not isinstance(counts, Mapping) or not counts:
        raise SchemaError("action_counts must be a non-empty mapping")
    total_actions = 0
    for action, value in counts.items():
        if action not in ACTION_SPACE:
            raise SchemaError(f"action_counts has unknown action {action!r}")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SchemaError(f"action_counts[{action!r}] must be a non-negative int")
        total_actions += int(value)
    if total_actions != steps:
        raise SchemaError(
            f"action_counts sum to {total_actions}, but the episode has {steps} steps"
        )

    fraction = _require_float(row, "no_action_fraction")
    if not 0.0 <= fraction <= 1.0:
        raise SchemaError("no_action_fraction must lie in [0, 1]")
    if steps == 0:
        if fraction != 0.0:
            raise SchemaError(
                "no_action_fraction must be 0.0 when no update was completed"
            )
    else:
        computed = counts.get("NO_ACTION", 0) / steps
        if abs(fraction - computed) > 1e-6:
            raise SchemaError(
                f"no_action_fraction {fraction} is inconsistent with action_counts "
                f"({computed})"
            )

    _require_int(row, "motor_spikes", minimum=0)

    for name in ("spike_sha256", "action_sha256"):
        value = row[name]
        if value is not None and not is_sha256(value):
            raise SchemaError(f"{name} must be null or a SHA-256 hex digest")

    before, after = row["weights_before"], row["weights_after"]
    if (before is None) != (after is None):
        raise SchemaError("weights_before and weights_after must both be null or both set")
    for name, value in (("weights_before", before), ("weights_after", after)):
        if value is not None and not is_sha256(value):
            raise SchemaError(f"{name} must be null or a SHA-256 hex digest")

    config_hashes = _check_hash_map(row["config_hashes"], "config_hashes")
    required_configs = {"environment", "campaign", "conditions"}
    if not required_configs <= set(config_hashes):
        raise SchemaError(
            f"config_hashes must include {sorted(required_configs)}"
        )
    _check_hash_map(row["input_hashes"], "input_hashes")

    _check_timestamp(row["started_at"], "started_at")
    wall_time = _require_float(row, "wall_time_s")
    if wall_time < 0:
        raise SchemaError("wall_time_s cannot be negative")

    if "connectome_unchanged" in row and not isinstance(
        row["connectome_unchanged"], bool
    ):
        raise SchemaError("connectome_unchanged must be a bool")

    return dict(row)


def validate_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    allow_duplicate_keys: bool = False,
) -> list[dict]:
    """Validate every row and refuse duplicate resume keys by default."""
    validated: list[dict] = []
    seen: dict[tuple[str, int, int], int] = {}
    for index, row in enumerate(rows):
        try:
            checked = validate_episode_row(row)
        except SchemaError as error:
            raise SchemaError(f"row {index}: {error}") from None
        key = episode_key(checked)
        if key in seen:
            if not allow_duplicate_keys:
                raise SchemaError(
                    f"duplicate episode key {key} at rows {seen[key]} and {index}"
                )
            seen[key] += 1
        else:
            seen[key] = index
        validated.append(checked)
    return validated


# ---------------------------------------------------------------------------
# run manifest
# ---------------------------------------------------------------------------


def validate_manifest(manifest: Mapping[str, Any]) -> dict:
    if not isinstance(manifest, Mapping):
        raise SchemaError("manifest must be a mapping")
    keys = set(manifest)
    missing = sorted(REQUIRED_MANIFEST_KEYS - keys)
    if missing:
        raise SchemaError(f"manifest is missing required keys: {missing}")
    unknown = sorted(keys - REQUIRED_MANIFEST_KEYS)
    if unknown:
        raise SchemaError(f"manifest has unknown keys: {unknown}")

    if _require_int(manifest, "schema_version", minimum=1) != MANIFEST_SCHEMA_VERSION:
        raise SchemaError(
            f"unsupported manifest schema_version {manifest['schema_version']!r}"
        )
    _require_text(manifest["run_id"], "run_id")
    _check_timestamp(manifest["created_at"], "created_at")
    _require_text(manifest["protocol"], "protocol")

    _check_hash_map(manifest["config_hashes"], "config_hashes", nested=True)
    _check_hash_map(manifest["input_hashes"], "input_hashes", nested=True)

    derivation = manifest["seed_derivation"]
    if not isinstance(derivation, Mapping) or "master_seed" not in derivation:
        raise SchemaError("seed_derivation must be a mapping with master_seed")

    environment = manifest["environment"]
    if not isinstance(environment, Mapping) or "sha256" not in environment:
        raise SchemaError("environment must be a mapping with sha256")
    if not is_sha256(environment["sha256"]):
        raise SchemaError("environment.sha256 is not a SHA-256 hex digest")

    design = manifest["design"]
    if not isinstance(design, Mapping):
        raise SchemaError("design must be a mapping")
    for name in ("n_seeds", "episodes_per_seed", "max_game_updates", "conditions"):
        if name not in design:
            raise SchemaError(f"design is missing {name}")

    conditions = manifest["conditions"]
    if not isinstance(conditions, Mapping) or not conditions:
        raise SchemaError("conditions must be a non-empty mapping")

    preflight = manifest["memory_preflight"]
    if not isinstance(preflight, Mapping):
        raise SchemaError("memory_preflight must be a mapping")
    for name in ("available_gb", "gate_gb", "passed"):
        if name not in preflight:
            raise SchemaError(f"memory_preflight is missing {name}")
    if not isinstance(preflight["passed"], bool):
        raise SchemaError("memory_preflight.passed must be a bool")

    capture = manifest["environment_capture"]
    if not isinstance(capture, Mapping):
        raise SchemaError("environment_capture must be a mapping")
    for name in ("python", "platform", "cpu_count", "libraries"):
        if name not in capture:
            raise SchemaError(f"environment_capture is missing {name}")

    integrity = manifest["integrity"]
    if not isinstance(integrity, Mapping):
        raise SchemaError("integrity must be a mapping")
    if "non_readme_failures" not in integrity:
        raise SchemaError("integrity is missing non_readme_failures")
    if not isinstance(integrity["non_readme_failures"], list):
        raise SchemaError("integrity.non_readme_failures must be a list")

    return dict(manifest)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def config_hash_map(config_hashes: Mapping[str, Any]) -> dict[str, str]:
    """Flatten ``{name: {path, sha256}}`` into the row-level mapping."""
    return {
        name: entry["sha256"]
        for name, entry in config_hashes.items()
        if isinstance(entry, Mapping) and "sha256" in entry
    }


def utc_timestamp(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "EPISODE_SCHEMA_VERSION",
    "EPISODE_STATUSES",
    "MANIFEST_SCHEMA_VERSION",
    "OPTIONAL_EPISODE_KEYS",
    "REQUIRED_EPISODE_KEYS",
    "REQUIRED_MANIFEST_KEYS",
    "ROLES",
    "SchemaError",
    "config_hash_map",
    "episode_key",
    "is_sha256",
    "utc_timestamp",
    "validate_episode_row",
    "validate_manifest",
    "validate_rows",
]
