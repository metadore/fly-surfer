"""Production episode runner for Pilot 1 (REV4 §10.3).

SCIENTIFIC STATUS
    One call runs one Pilot 1 episode of condition A on the frozen biological
    substrate, through the existing Phase 7 controlled environment. It adds no
    biological parameter, substitutes no synthetic motor activity and no
    conventional policy: A is the fixed-weight biological graph, the Phase 4
    decoder and the game's own reward.

    This module is a *runner*, not an authorisation. It is reached only through
    :func:`experiments.phase_8.stages.common.drive_pilot`, which refuses unless
    every execution gate (notably B7, the G3 deviation) is resolved. A row
    produced here is evidence only when the driver labels the run ``pilot``;
    the synthetic-fixture path relabels every row ``synthetic_fixture``.

    Failures are recorded, not hidden. An exception raised while building the
    provenance (a missing frozen input, a wrong environment seed) is a
    configuration error and stops the run. An exception raised by the episode
    itself is written as a schema-valid ``status='error'`` row, which the store
    keeps and the summary counts.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from ..campaign.factory import CampaignFactory, FactoryError, FactorySettings
from ..conditions import a_fixed
from ..conditions.base import spec_for
from ..conditions.execute import error_row, utc_timestamp
from ..config import Phase8Config
from ..seeds import environment_seed
from .common import StageConfigurationError

PILOT1_CONDITION = "A"
RUNNER_ID = "phase_8.stages.pilot1_runner.Pilot1EpisodeRunner"


class Pilot1EpisodeRunner:
    """Run one A episode per call; the driver supplies the seed schedule.

    ``factory`` is injectable so tests can supply a synthetic 32-node substrate.
    The default builds the real :class:`CampaignFactory` against the declared
    frozen inputs; it loads the BANC world lazily and only when an episode is
    actually requested.
    """

    def __init__(self, config: Phase8Config, *, factory: Any | None = None) -> None:
        self.config = config
        self._factory = factory
        self._clock: Callable[[], float] = time.perf_counter

    @property
    def factory(self) -> Any:
        if self._factory is None:
            self._factory = CampaignFactory(
                frozen_inputs=self.config.campaign.frozen_inputs,
                settings=FactorySettings(
                    max_game_updates=int(self.config.campaign.max_game_updates)
                ),
            )
        return self._factory

    def input_hashes(self) -> dict[str, str]:
        hashes = dict(self.factory.input_hashes())
        if not hashes:
            raise FactoryError(
                "the factory returned no frozen-input hashes; an episode row "
                "cannot record an empty provenance map"
            )
        return hashes

    def __call__(
        self, arm: str, seed: int, episode: int, context: Mapping[str, Any]
    ) -> dict:
        if str(arm) != PILOT1_CONDITION:
            raise StageConfigurationError(
                f"Pilot 1 runs condition {PILOT1_CONDITION} only; the driver "
                f"asked for {arm!r}"
            )

        seed = int(seed)
        episode = int(episode)
        master_seed = int(context["master_seed"])
        env_seed = int(context["environment_seed"])
        max_updates = int(context["max_game_updates"])
        config_hashes = {
            str(name): str(digest)
            for name, digest in dict(context["config_hashes"]).items()
        }
        self._check_context(master_seed, seed, episode, env_seed, max_updates, config_hashes)

        # Provenance first: a failure here is not an episode failure and must
        # not be recorded as one.
        input_hashes = self.input_hashes()

        started_at = utc_timestamp()
        started = self._clock()
        metadata: dict = {}
        try:
            components = self.factory.neural_components(
                PILOT1_CONDITION,
                seed=seed,
                episode=episode,
                environment_seed=env_seed,
                master_seed=master_seed,
                training=False,
            )
            metadata = dict(getattr(components, "metadata", {}) or {})
            result = a_fixed.run(
                components,
                seed=seed,
                episode=episode,
                environment_seed=env_seed,
                config_hashes=config_hashes,
                input_hashes=input_hashes,
                max_game_updates=max_updates,
                training=False,
            )
        except (FactoryError, StageConfigurationError):
            raise
        except Exception as error:  # noqa: BLE001 - the row records the failure
            return self._failure_row(
                seed=seed,
                episode=episode,
                env_seed=env_seed,
                max_updates=max_updates,
                config_hashes=config_hashes,
                input_hashes=input_hashes,
                started_at=started_at,
                wall_time_s=self._clock() - started,
                error=error,
                metadata=metadata,
            )

        row = dict(result["row"])
        if row["condition"] != PILOT1_CONDITION:
            raise StageConfigurationError(
                f"the episode returned condition {row['condition']!r}, not "
                f"{PILOT1_CONDITION!r}"
            )
        notes = dict(row.get("notes") or {})
        notes.update(self._provenance(metadata))
        notes["game_loop"] = self._game_loop(result)
        row["notes"] = notes
        return row

    # ------------------------------------------------------------------
    def _check_context(
        self,
        master_seed: int,
        seed: int,
        episode: int,
        env_seed: int,
        max_updates: int,
        config_hashes: Mapping[str, str],
    ) -> None:
        campaign = self.config.campaign
        if master_seed != int(campaign.master_seed):
            raise StageConfigurationError(
                f"the driver master seed {master_seed} is not the declared "
                f"{campaign.master_seed}"
            )
        expected_env = int(environment_seed(master_seed, seed, episode))
        if env_seed != expected_env:
            raise StageConfigurationError(
                f"environment seed {env_seed} is not the declared stream value "
                f"{expected_env} for (seed {seed}, episode {episode})"
            )
        if max_updates != int(campaign.max_game_updates):
            raise StageConfigurationError(
                f"max_game_updates {max_updates} is not the declared "
                f"{campaign.max_game_updates}"
            )
        declared = {
            str(name): str(entry["sha256"]) for name, entry in self.config.hashes.items()
        }
        if dict(config_hashes) != declared:
            raise StageConfigurationError(
                "the driver config hashes do not match the loaded configuration"
            )

    def _provenance(self, metadata: Mapping[str, Any]) -> dict:
        return {
            "evidence_kind": "pilot",
            "runner": RUNNER_ID,
            "condition_source": "experiments.phase_8.conditions.a_fixed",
            "substrate": "biological_graph",
            "game_integration": (
                "environment.live_loop.NeuralClosedLoop over "
                "environment.environment_adapter.GameEnvironmentAdapter"
            ),
            "component_metadata": dict(metadata),
            "does_not_establish": (
                "Pilot 1 does not estimate C1-C4 and is not merged into the "
                "campaign design"
            ),
        }

    @staticmethod
    def _game_loop(result: Mapping[str, Any]) -> dict:
        summary = result["summary"]
        fallbacks = list(summary.get("fallbacks") or ())
        reasons: dict[str, int] = {}
        for entry in fallbacks:
            key = str(entry.get("reason"))
            reasons[key] = reasons.get(key, 0) + 1
        return {
            "game_updates": int(summary["updates"]),
            "neural_steps": int(summary["neural_steps"]),
            "mean_steps_per_update": float(summary["mean_steps_per_update"]),
            "neural_resets_during_episode": int(
                summary["neural_resets_during_episode"]
            ),
            "neural_time_ms": float(summary["neural_time_ms"]),
            "game_time_ms": float(summary["game_time_ms"]),
            "total_spikes": int(summary["total_spikes"]),
            "motor_spikes": int(summary["motor_spikes"]),
            "motor_population_spikes": dict(summary["motor_population_spikes"]),
            "action_counts": dict(summary["action_counts"]),
            "total_reward": float(summary["total_reward"]),
            "survival_score": float(result["row"]["survival_score"]),
            "terminated": bool(summary["terminated"]),
            "truncated": bool(summary["truncated"]),
            "termination_reason": summary["termination_reason"],
            "weights_before": summary["weights_before"]["sha256"],
            "weights_after": summary["weights_after"]["sha256"],
            "weights_unchanged": bool(summary["weights_unchanged"]),
            "unmapped_or_invalid": int(summary["unmapped_or_invalid"]),
            "fallback_reasons": reasons,
        }

    def _failure_row(
        self,
        *,
        seed: int,
        episode: int,
        env_seed: int,
        max_updates: int,
        config_hashes: Mapping[str, str],
        input_hashes: Mapping[str, str],
        started_at: str,
        wall_time_s: float,
        error: BaseException,
        metadata: Mapping[str, Any],
    ) -> dict:
        row = error_row(
            condition=PILOT1_CONDITION,
            role=spec_for(PILOT1_CONDITION).role,
            seed=seed,
            episode=episode,
            environment_seed=env_seed,
            training=False,
            max_game_updates=max_updates,
            config_hashes=config_hashes,
            input_hashes=input_hashes,
            started_at=started_at,
            wall_time_s=wall_time_s,
            error=f"{type(error).__name__}: {error}",
        )
        notes = dict(row.get("notes") or {})
        notes.update(self._provenance(metadata))
        notes["failure"] = {
            "error_type": type(error).__name__,
            "recorded_as": "status=error row; no update count is claimed",
        }
        row["notes"] = notes
        return row


__all__ = ["PILOT1_CONDITION", "Pilot1EpisodeRunner", "RUNNER_ID"]
