"""Read-only status of a Phase 8 run directory.

SCIENTIFIC STATUS
    This module inspects a run; it never changes one. It reads the manifest and
    the append-only episode store, compares them with the plan of a supplied
    configuration, and reports what is stored, missing, torn or drifted. It
    writes nothing, deletes nothing and appends nothing.

Incomplete-run detection is deliberately conservative: an unreadable store, a
torn tail, a manifest that fails its schema or a plan that cannot be resolved
all count as *not complete*. ``complete`` is therefore never true by default.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..config import ConfigError, Phase8Config
from ..registry import evaluation_plan
from ..schema import SchemaError, validate_manifest
from ..store import EpisodeStore, StoreError

DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_STORE_NAME = "episodes.jsonl"


def _read_manifest(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"no run manifest at {path}"
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        return validate_manifest(payload), None
    except (OSError, ValueError, SchemaError) as error:
        return None, f"{path} cannot be read as a manifest: {error}"


def run_status(
    run_dir: str | Path,
    *,
    config: Phase8Config | None = None,
    plan: Iterable[tuple[str, int, int]] | None = None,
    manifest_name: str | None = None,
    store_name: str | None = None,
) -> dict:
    """Inspect a run directory without modifying it.

    When ``config`` is supplied the manifest hash drift is checked and the
    expected plan is resolved from it unless ``plan`` is given. An unresolved
    design (``n_seeds_selected`` is null) leaves the plan unavailable; it is
    not guessed.
    """
    directory = Path(run_dir)
    manifest_file = manifest_name or (
        config.campaign.run_manifest_name if config else DEFAULT_MANIFEST_NAME
    )
    store_file = store_name or (
        config.campaign.episode_store_name if config else DEFAULT_STORE_NAME
    )

    report: dict[str, Any] = {
        "run_dir": directory.as_posix(),
        "exists": directory.is_dir(),
        "manifest_path": (directory / manifest_file).as_posix(),
        "store_path": (directory / store_file).as_posix(),
        "read_only": True,
        "complete": False,
    }
    if not directory.is_dir():
        report["reason"] = "the run directory does not exist"
        return report

    manifest, manifest_error = _read_manifest(directory / manifest_file)
    report["manifest_present"] = manifest is not None
    if manifest is not None:
        report["run_id"] = manifest["run_id"]
        report["created_at"] = manifest["created_at"]
        report["memory_preflight"] = dict(manifest["memory_preflight"])
    else:
        report["manifest_error"] = manifest_error

    # -- plan -----------------------------------------------------------
    expected: tuple[tuple[str, int, int], ...] | None = None
    plan_error: str | None = None
    if plan is not None:
        expected = tuple((str(a), int(s), int(e)) for a, s, e in plan)
    elif config is not None:
        try:
            expected = evaluation_plan(config)
        except ConfigError as error:
            plan_error = str(error)
    else:
        plan_error = "no configuration or plan was supplied"
    report["plan_available"] = expected is not None
    if expected is None:
        report["plan_error"] = plan_error

    # -- store ----------------------------------------------------------
    store_error: str | None = None
    rows: list[dict] = []
    try:
        store = EpisodeStore(directory, filename=store_file, create=False)
        rows = store.rows()
    except StoreError as error:
        store_error = str(error)
    report["store_error"] = store_error
    report["rows"] = len(rows)

    per_arm: Counter = Counter(row["condition"] for row in rows)
    per_seed: Counter = Counter(int(row["seed"]) for row in rows)
    report["per_arm"] = dict(sorted(per_arm.items()))
    report["per_seed"] = {str(key): int(value) for key, value in sorted(per_seed.items())}
    report["failed_rows"] = int(sum(1 for row in rows if row.get("status") == "error"))
    report["training_rows"] = int(sum(1 for row in rows if row.get("training")))

    # -- completeness ---------------------------------------------------
    if expected is not None and store_error is None:
        expected_set = set(expected)
        stored = {(row["condition"], int(row["seed"]), int(row["episode"])) for row in rows}
        missing = [key for key in expected if key not in stored]
        unexpected = sorted(stored - expected_set)
        report["planned"] = len(expected)
        report["missing"] = len(missing)
        report["missing_keys"] = [list(key) for key in missing[:200]]
        report["unexpected_keys"] = [list(key) for key in unexpected[:200]]
        report["complete"] = not missing and not unexpected
        if missing or unexpected:
            report["reason"] = (
                f"{len(missing)} planned episodes are missing and "
                f"{len(unexpected)} stored episodes are outside the plan"
            )
    else:
        report["missing"] = None
        report["reason"] = store_error or plan_error or "the plan is unavailable"

    # -- drift ----------------------------------------------------------
    if config is not None and manifest is not None:
        expected_hashes = {
            name: entry["sha256"] for name, entry in config.hashes.items()
        }
        recorded_hashes = {
            name: entry["sha256"]
            for name, entry in manifest["config_hashes"].items()
        }
        mismatched = sorted(
            name
            for name in set(expected_hashes) | set(recorded_hashes)
            if expected_hashes.get(name) != recorded_hashes.get(name)
        )
        report["config_hash_drift"] = mismatched
        if mismatched:
            report["complete"] = False
            report.setdefault("reason", "")
            report["reason"] = (
                (report["reason"] + "; " if report["reason"] else "")
                + f"configuration changed since the run started: {mismatched}"
            )
    else:
        report["config_hash_drift"] = None

    return report


__all__ = ["DEFAULT_MANIFEST_NAME", "DEFAULT_STORE_NAME", "run_status"]
