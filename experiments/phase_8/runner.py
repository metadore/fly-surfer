"""Campaign execution harness with the §9.3 gate and §8.3 resume.

The harness owns the things that must be identical across every arm: the
``(arm, seed, episode)`` plan, the paired environment seed, the configuration
hashes, the manifest, the memory preflight and the append-only store. The
per-arm work is supplied as an ``episode_runner`` callback, so conditions can be
implemented and reviewed independently of the harness.

Nothing here implements a condition. The runner refuses to start when the
protocol's pilot decision is unrecorded, when free memory is below the gate, or
when an existing result directory would be reused without a new run id.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .config import (
    ConfigError,
    MemoryGateError,
    Phase8Config,
    memory_preflight,
)
from .manifest import build_manifest, load_manifest, write_manifest
from .registry import evaluation_plan
from .schema import SchemaError, episode_key, validate_episode_row
from .seeds import environment_seed, seed_plan
from .store import EpisodeStore, StoreError, resolve_run_directory


EpisodeRunner = Callable[[str, int, int, dict], Mapping[str, Any]]


def _gate_report(preflight: Callable[[float], dict], gate_gb: float) -> dict:
    report = preflight(gate_gb)
    if not isinstance(report, Mapping) or "passed" not in report:
        raise ConfigError("the memory preflight must return a report with 'passed'")
    if not report["passed"]:
        raise MemoryGateError(
            f"{report.get('reason', 'memory preflight failed')} "
            f"(available {report.get('available_gb')} GB of {gate_gb} GB)"
        )
    return dict(report)


class CampaignRunner:
    """Drives one run directory; writes rows only through :class:`EpisodeStore`."""

    def __init__(
        self,
        config: Phase8Config,
        run_dir: Path,
        *,
        episode_runner: EpisodeRunner,
        manifest: Mapping[str, Any],
        store: EpisodeStore,
    ) -> None:
        self.config = config
        self.run_dir = Path(run_dir)
        self.episode_runner = episode_runner
        self.manifest = dict(manifest)
        self.store = store
        self.plan = evaluation_plan(config)

    # -- construction ----------------------------------------------------

    @classmethod
    def start(
        cls,
        config: Phase8Config,
        base_dir: str | Path,
        run_id: str,
        *,
        episode_runner: EpisodeRunner,
        preflight: Callable[[float], dict] = memory_preflight,
        new_run_id: str | None = None,
        input_hashes: Mapping[str, Any] | None = None,
        integrity: Mapping[str, Any] | None = None,
        capture: Mapping[str, Any] | None = None,
    ) -> "CampaignRunner":
        """Check the gate, refuse an existing directory, write the manifest."""
        evaluation_plan(config)  # refuse an unresolved design before any write
        report = _gate_report(preflight, config.campaign.memory_gate_gb)
        run_dir = resolve_run_directory(base_dir, run_id, new_run_id=new_run_id)
        manifest = build_manifest(
            config,
            run_id=run_dir.name,
            memory_preflight=report,
            input_hashes=input_hashes,
            integrity=integrity,
            capture=capture,
        )
        write_manifest(run_dir / config.campaign.run_manifest_name, manifest)
        store = EpisodeStore(run_dir, filename=config.campaign.episode_store_name)
        return cls(
            config,
            run_dir,
            episode_runner=episode_runner,
            manifest=manifest,
            store=store,
        )

    @classmethod
    def resume(
        cls,
        config: Phase8Config,
        run_dir: str | Path,
        *,
        episode_runner: EpisodeRunner,
        preflight: Callable[[float], dict] = memory_preflight,
    ) -> "CampaignRunner":
        """Reopen an interrupted run; never writes a second manifest."""
        directory = Path(run_dir)
        manifest_path = directory / config.campaign.run_manifest_name
        if not manifest_path.is_file():
            raise StoreError(f"no run manifest in {directory}")
        manifest = load_manifest(manifest_path)
        if manifest["run_id"] != directory.name:
            raise StoreError(
                f"manifest run_id {manifest['run_id']!r} does not match the "
                f"directory {directory.name!r}"
            )
        expected = {name: entry["sha256"] for name, entry in config.hashes.items()}
        recorded = {
            name: entry["sha256"] for name, entry in manifest["config_hashes"].items()
        }
        if expected != recorded:
            raise StoreError(
                "the configuration has changed since this run started; resume "
                "would mix two designs in one store"
            )
        _gate_report(preflight, config.campaign.memory_gate_gb)
        store = EpisodeStore(directory, filename=config.campaign.episode_store_name)
        return cls(
            config,
            directory,
            episode_runner=episode_runner,
            manifest=manifest,
            store=store,
        )

    # -- execution -------------------------------------------------------

    def context(self, condition: str, seed: int, episode: int) -> dict:
        """Everything an arm may need that the harness guarantees is shared."""
        return {
            "master_seed": self.config.campaign.master_seed,
            "environment_seed": environment_seed(
                self.config.campaign.master_seed, seed, episode
            ),
            "seed_plan": seed_plan(self.config.campaign.master_seed, condition, seed),
            "config_hashes": {
                name: entry["sha256"] for name, entry in self.config.hashes.items()
            },
            "max_game_updates": self.config.campaign.max_game_updates,
            "episodes_per_seed": self.config.campaign.episodes_per_seed,
        }

    def run(self, *, limit: int | None = None) -> dict:
        """Execute pending plan entries, resuming by key.

        ``limit`` exists for smoke checks and pilot harness tests; a campaign
        is complete only when every plan entry is stored.
        """
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError("limit must be a non-negative integer or None")

        pending = self.store.missing(self.plan)
        selected = pending if limit is None else pending[:limit]
        started = time.perf_counter()
        executed = 0
        for condition, seed, episode in selected:
            row = self.episode_runner(
                condition, seed, episode, self.context(condition, seed, episode)
            )
            if not isinstance(row, Mapping):
                raise SchemaError("an episode runner must return a row mapping")
            checked = validate_episode_row(row, expected_condition=condition)
            if (int(checked["seed"]), int(checked["episode"])) != (seed, episode):
                raise SchemaError(
                    "the row does not identify the episode it was asked to run: "
                    f"expected {(condition, seed, episode)}, got "
                    f"{episode_key(checked)}"
                )
            self.store.append(checked)
            executed += 1

        remaining = len(self.store.missing(self.plan))
        return {
            "planned": len(self.plan),
            "stored": len(self.store),
            "executed": executed,
            "remaining": remaining,
            "complete": remaining == 0,
            "wall_time_s": round(time.perf_counter() - started, 6),
            "run_dir": str(self.run_dir),
        }

    @property
    def complete(self) -> bool:
        return not self.store.missing(self.plan)


__all__ = ["CampaignRunner", "EpisodeRunner"]
