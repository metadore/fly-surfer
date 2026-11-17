"""Append-only episode store with resume, for the Phase 8 campaign.

REV3 §8.3: ``experiments/results/phase_8/episodes.jsonl`` holds one row per
episode, is never rewritten, and resume is by the ``(condition, seed,
episode)`` key. REV3 §8.8: an existing result directory is refused unless a
new run id is supplied, and previous runs are never deleted.

The store validates every row before writing it, detects a duplicate key
instead of overwriting, and refuses to analyse a file whose tail was torn by an
interrupted write. It never opens the JSONL for reading and writing in a way
that truncates it.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .schema import SchemaError, episode_key, validate_episode_row


EPISODES_FILE = "episodes.jsonl"

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class StoreError(RuntimeError):
    """The episode store is inconsistent or was used unsafely."""


class ExistingResultError(StoreError):
    """A result directory already exists and no new run id was supplied."""


class DuplicateEpisodeError(StoreError):
    """An episode key already exists; the store never overwrites it."""


def _check_run_id(value: Any, name: str = "run_id") -> str:
    if not isinstance(value, str) or not _RUN_ID.match(value):
        raise StoreError(
            f"{name} must match {_RUN_ID.pattern!r}, got {value!r}"
        )
    return value


def resolve_run_directory(
    base_dir: str | Path,
    run_id: str,
    *,
    new_run_id: str | None = None,
) -> Path:
    """Return a fresh run directory or refuse to touch an existing one.

    ``base_dir/run_id`` is created when absent. When it already exists a
    ``new_run_id`` is required and ``base_dir/new_run_id`` must not exist
    either. Nothing is ever deleted or reused (REV3 §8.8).
    """
    base = Path(base_dir)
    name = _check_run_id(run_id)
    target = base / name
    if target.exists():
        if new_run_id is None:
            raise ExistingResultError(
                f"result directory already exists: {target}; supply a new run id "
                "instead of overwriting or deleting it"
            )
        fresh = _check_run_id(new_run_id, "new_run_id")
        if fresh == name:
            raise ExistingResultError(
                "new_run_id must differ from the run id it replaces"
            )
        target = base / fresh
        if target.exists():
            raise ExistingResultError(
                f"result directory already exists: {target}; nothing is overwritten"
            )
    target.mkdir(parents=True, exist_ok=True)
    return target


class EpisodeStore:
    """One append-only JSONL file validated against the episode schema."""

    def __init__(
        self,
        run_dir: str | Path,
        *,
        filename: str = EPISODES_FILE,
        create: bool = True,
    ) -> None:
        self.run_dir = Path(run_dir)
        if create and not self.run_dir.is_dir():
            self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / filename
        self._keys: dict[tuple[str, int, int], int] = {}
        self._rows = 0
        self._load_index()

    # -- read -----------------------------------------------------------

    def _load_index(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        if lines and not lines[-1].endswith("\n"):
            raise StoreError(
                f"{self.path} ends with an unterminated line; a previous write "
                "was interrupted. The file is not rewritten."
            )
        for number, line in enumerate(lines, 1):
            if not line.strip():
                raise StoreError(f"{self.path}:{number} is blank; expected one JSON row")
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise StoreError(f"{self.path}:{number} is not valid JSON: {error}") from None
            try:
                row = validate_episode_row(payload)
            except SchemaError as error:
                raise StoreError(f"{self.path}:{number} fails validation: {error}") from None
            key = episode_key(row)
            if key in self._keys:
                raise StoreError(
                    f"{self.path}: duplicate episode key {key} on line {number}"
                )
            self._keys[key] = number
            self._rows += 1

    def __len__(self) -> int:
        return self._rows

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, tuple) or len(key) != 3:
            return False
        try:
            return (str(key[0]), int(key[1]), int(key[2])) in self._keys
        except (TypeError, ValueError):
            return False

    @property
    def keys(self) -> tuple[tuple[str, int, int], ...]:
        return tuple(self._keys)

    def has(self, condition: str, seed: int, episode: int) -> bool:
        return (str(condition), int(seed), int(episode)) in self._keys

    def rows(self) -> list[dict]:
        return list(self.iter_rows())

    def iter_rows(self):
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    yield validate_episode_row(json.loads(line))
                except (json.JSONDecodeError, SchemaError) as error:
                    raise StoreError(
                        f"{self.path}:{number} cannot be read back: {error}"
                    ) from None

    # -- write ----------------------------------------------------------

    def append(self, row: Mapping[str, Any]) -> tuple[str, int, int]:
        """Validate, then append exactly one row. Duplicate keys are refused."""
        checked = validate_episode_row(row)
        key = episode_key(checked)
        if key in self._keys:
            raise DuplicateEpisodeError(
                f"episode {key} already exists in {self.path}; the store is "
                "append-only and never rewrites a row"
            )
        line = json.dumps(checked, sort_keys=True, allow_nan=False)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._rows += 1
        self._keys[key] = self._rows
        return key

    def write_if_new(self, row: Mapping[str, Any]) -> bool:
        """Append unless the key exists; returns whether a row was written.

        This is the resume primitive: re-running an interrupted campaign skips
        completed episodes and is idempotent on ``(condition, seed, episode)``.
        """
        checked = validate_episode_row(row)
        if episode_key(checked) in self._keys:
            return False
        self.append(checked)
        return True

    def missing(self, plan: Iterable[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
        """The part of ``plan`` that is not yet stored, in plan order."""
        remaining = []
        for condition, seed, episode in plan:
            key = (str(condition), int(seed), int(episode))
            if key not in self._keys:
                remaining.append(key)
        return remaining


def read_store(path: str | Path) -> list[dict]:
    """Read and validate a standalone JSONL file, refusing a torn tail."""
    source = Path(path)
    if not source.is_file():
        raise StoreError(f"episode store not found: {source}")
    store = EpisodeStore(source.parent, filename=source.name, create=False)
    return store.rows()


__all__ = [
    "DuplicateEpisodeError",
    "EPISODES_FILE",
    "EpisodeStore",
    "ExistingResultError",
    "StoreError",
    "read_store",
    "resolve_run_directory",
]
