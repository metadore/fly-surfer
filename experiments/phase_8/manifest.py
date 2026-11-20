"""Run manifest construction for the Phase 8 campaign.

The manifest records what the campaign ran on, not what it produced (REV3
§8.5–§8.6): configuration hashes, seed derivation, the frozen input hashes, the
environment capture, and the §9.3 memory preflight. It is written once per run
directory and validated by :func:`experiments.phase_8.schema.validate_manifest`.

Calling :func:`build_manifest` with ``memory_preflight.passed = False`` is
legitimate — a refused run should leave a manifest saying why it did not
start. It is not legitimate to describe such a run as complete.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from brain.banc_graph import sha256_file

from .config import PROJECT_ROOT, CampaignConfig, Phase8Config
from .schema import (
    MANIFEST_SCHEMA_VERSION,
    SchemaError,
    utc_timestamp,
    validate_manifest,
)
from .seeds import describe_derivation

PROTOCOL_ID = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"

_LIBRARIES = ("numpy", "pandas", "matplotlib", "PyYAML", "torch", "scipy", "psutil")


def environment_capture() -> dict:
    """Python, platform, library versions, CPU count, RAM and peak RSS."""
    from importlib import metadata

    libraries: dict[str, str | None] = {}
    for name in _LIBRARIES:
        try:
            libraries[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            libraries[name] = None

    memory: dict[str, Any] = {
        "total_gb": None,
        "available_gb": None,
        "percent_used": None,
        "peak_rss_mb": None,
        "peak_rss_source": None,
    }
    try:
        import psutil

        info = psutil.virtual_memory()
        memory["total_gb"] = round(float(info.total) / 1024.0**3, 3)
        memory["available_gb"] = round(float(info.available) / 1024.0**3, 3)
        memory["percent_used"] = round(float(info.percent), 3)
        process = psutil.Process()
        details = process.memory_info()
        peak = getattr(details, "peak_wset", None)
        if peak is None:
            peak = details.rss
            memory["peak_rss_source"] = "current RSS (this platform exposes no peak)"
        else:
            memory["peak_rss_source"] = "process peak working set"
        memory["peak_rss_mb"] = round(float(peak) / 1024.0**2, 3)
    except ImportError:  # pragma: no cover - psutil is present in this repo
        pass

    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "libraries": libraries,
        "memory": memory,
    }


def resolve_input(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def hash_inputs(paths: Mapping[str, str | Path]) -> dict[str, dict[str, str]]:
    """SHA-256 of every declared frozen input; a missing input is an error."""
    hashed: dict[str, dict[str, str]] = {}
    for name, path in paths.items():
        source = resolve_input(path)
        if not source.is_file():
            raise FileNotFoundError(f"declared Phase 8 input is missing: {source}")
        try:
            relative = source.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative = source.resolve().as_posix()
        hashed[str(name)] = {"path": relative, "sha256": sha256_file(source)}
    return hashed


def phase8_input_paths(config: Phase8Config) -> dict[str, str]:
    return dict(config.campaign.frozen_inputs)


def build_manifest(
    config: Phase8Config,
    *,
    run_id: str,
    memory_preflight: Mapping[str, Any],
    input_hashes: Mapping[str, Any] | None = None,
    integrity: Mapping[str, Any] | None = None,
    created_at: datetime | None = None,
    capture: Mapping[str, Any] | None = None,
) -> dict:
    """Assemble and validate the run manifest."""
    # Deferred import: the protocol module imports this package's config.
    from .campaign.protocol import approval_status

    campaign: CampaignConfig = config.campaign
    if input_hashes is None:
        input_hashes = hash_inputs(phase8_input_paths(config))

    approval = approval_status()
    design = {
        "n_seeds": campaign.n_seeds_selected,
        "n_seeds_primary": campaign.n_seeds_primary,
        "n_seeds_fallback": campaign.n_seeds_fallback,
        "episodes_per_seed": campaign.episodes_per_seed,
        "max_game_updates": campaign.max_game_updates,
        "conditions": list(campaign.conditions),
        "control_arms": list(campaign.control_arms),
        "exploratory_arms": list(campaign.exploratory_arms),
        "seed_indices": {
            "campaign": list(campaign.campaign_seeds),
            "training": list(campaign.training_seeds),
            "pilot": list(campaign.pilot_seeds),
        },
        "approval": approval["decision_status"],
        "approval_basis": approval["approval_basis"],
    }

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_timestamp(created_at),
        "protocol": PROTOCOL_ID,
        "config_hashes": dict(config.hashes),
        "seed_derivation": describe_derivation(campaign.master_seed),
        "environment": config.environment.as_dict(),
        "design": design,
        "conditions": {
            condition_id: dict(spec)
            for condition_id, spec in config.conditions.all_specs.items()
        },
        "memory_preflight": dict(memory_preflight),
        "environment_capture": dict(capture or environment_capture()),
        "input_hashes": dict(input_hashes),
        "integrity": dict(
            integrity
            or {
                "checked": False,
                "baseline": None,
                "non_readme_failures": [],
                "note": (
                    "the 37-file baseline was not checked for this manifest; a "
                    "report may not be published until it is"
                ),
            }
        ),
    }
    return validate_manifest(manifest)


def write_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    """Validate, then write once. An existing manifest is never replaced."""
    target = Path(path)
    checked = validate_manifest(manifest)
    if target.exists():
        raise FileExistsError(f"manifest already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(checked, indent=2, sort_keys=True, allow_nan=False)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return target


def load_manifest(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"manifest not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SchemaError(f"{source} is not valid JSON: {error}") from None
    return validate_manifest(payload)


__all__ = [
    "PROTOCOL_ID",
    "build_manifest",
    "environment_capture",
    "hash_inputs",
    "load_manifest",
    "phase8_input_paths",
    "resolve_input",
    "write_manifest",
]
