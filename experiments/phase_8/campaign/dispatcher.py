"""Route one ``(arm, seed, episode)`` plan entry to its declared implementation.

SCIENTIFIC STATUS
    The dispatcher owns no mechanism. It selects the arm module that declares
    the condition, injects the components the factory built, and hands back the
    validated episode row. A row produced here is a measurement of a model, not
    of a fly.

Three rules are enforced here rather than left to the caller:

* **paired A prime / C prime.** The mirrors A and C are re-derived in-process
  from the *same* paired environment seed and the same condition-independent
  structure seed, then compared field by field with zero tolerance
  (REV4 §3.8.3). A mismatch is an :class:`EpisodeFailure`; there is no retry
  with another seed.
* **no fabricated rows.** An episode that raised is not turned into a row with
  a made-up survival score. The failure is recorded in the failure log and
  re-raised so the harness stops.
* **control evidence stays inside ``evidence``.** The row schema is
  closed-world, so equivalence and zero-pathway reports are merged into the
  existing ``evidence`` block and the row is re-validated.

Nothing here trains. F, F beta and E are evaluated from artifacts the caller
supplied to :class:`~.factory.CampaignFactory`; the factory refuses to build
them otherwise.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ..conditions import (
    a_fixed,
    b_plastic,
    c_random,
    d_plastic,
    e_conventional,
    f_readout,
)
from ..controls import a_prime, c_prime, f_beta, f_init, floor
from ..schema import validate_episode_row
from .factory import CampaignFactory, FactoryError

#: Registry order, mirroring ``configs/phase_8/conditions.yaml``.
ARM_ORDER = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "A_prime",
    "C_prime",
    "F_beta",
    "F_init",
    "E_full",
    "floor",
)
NEURAL_ARMS = ("A", "B", "C", "D", "F", "A_prime", "C_prime", "F_beta", "F_init")
CONVENTIONAL_ARMS = ("E", "E_full")
CONTROL_MIRRORS = {"A_prime": "A", "C_prime": "C"}

#: Default arm implementations. Tests inject a mapping of stubs instead.
ARM_RUNNERS: dict[str, Callable[..., dict]] = {
    "A": a_fixed.run,
    "B": b_plastic.run,
    "C": c_random.run,
    "D": d_plastic.run,
    "E": e_conventional.run,
    "E_full": e_conventional.run,
    "F": f_readout.run,
    "A_prime": a_prime.run,
    "C_prime": c_prime.run,
    "F_beta": f_beta.run,
    "F_init": f_init.run,
    "floor": floor.run,
}


class DispatcherError(RuntimeError):
    """The dispatcher cannot run the requested arm as declared."""


class EpisodeFailure(RuntimeError):
    """One plan entry failed; the campaign must stop, not invent a row.

    The payload is what the failure log records. ``stage`` names where the
    failure happened: ``components``, ``mirror``, ``episode`` or ``row``.
    """

    def __init__(
        self,
        condition: str,
        seed: int,
        episode: int,
        cause: BaseException,
        *,
        stage: str,
    ) -> None:
        self.condition = str(condition)
        self.seed = int(seed)
        self.episode = int(episode)
        self.stage = str(stage)
        self.cause = cause
        super().__init__(
            f"{self.condition} seed={self.seed} episode={self.episode} "
            f"failed in {self.stage}: {type(cause).__name__}: {cause}"
        )

    def as_dict(self) -> dict:
        payload = {
            "kind": "episode_failure",
            "condition": self.condition,
            "seed": self.seed,
            "episode": self.episode,
            "stage": self.stage,
            "cause_type": type(self.cause).__name__,
            "cause": str(self.cause),
        }
        mismatch = getattr(self.cause, "payload", None)
        if isinstance(mismatch, dict):
            payload["equivalence_mismatch"] = mismatch
        return payload


@dataclass(frozen=True)
class DispatchRecord:
    """What one dispatch did; returned by :meth:`CampaignDispatcher.execute`."""

    condition: str
    seed: int
    episode: int
    row: dict
    arm: str
    mirror: str | None = None

    def describe(self) -> dict:
        return {
            "condition": self.condition,
            "seed": self.seed,
            "episode": self.episode,
            "arm": self.arm,
            "mirror": self.mirror,
            "row_keys": sorted(self.row),
        }


class CampaignDispatcher:
    """A ``CampaignRunner`` episode runner that builds components per arm.

    ``arm_runners`` replaces the default :data:`ARM_RUNNERS`; it is the seam
    the focused tests use, so no test needs a BANC-scale graph or a live game.
    """

    def __init__(
        self,
        factory: CampaignFactory,
        *,
        input_hashes: Mapping[str, str] | None = None,
        arm_runners: Mapping[str, Callable[..., dict]] | None = None,
        failure_log: str | Path | None = None,
        training_seeds: Any | None = None,
        evaluation_seeds: Any | None = None,
    ) -> None:
        self.factory = factory
        self.arm_runners = dict(ARM_RUNNERS if arm_runners is None else arm_runners)
        missing = sorted(set(ARM_ORDER) - set(self.arm_runners))
        if missing:
            raise DispatcherError(f"no runner for arms {missing}")
        self._input_hashes = (
            dict(input_hashes) if input_hashes is not None else None
        )
        self.failure_log = None if failure_log is None else Path(failure_log)
        self.training_seeds = training_seeds
        self.evaluation_seeds = evaluation_seeds
        if (training_seeds is None) != (evaluation_seeds is None):
            raise DispatcherError(
                "supply both training and evaluation seed sets, or neither"
            )

    # -- inputs -----------------------------------------------------------
    @property
    def input_hashes(self) -> dict:
        """Frozen-input digests; computed once and cached by the factory."""
        if self._input_hashes is None:
            compute = getattr(self.factory, "input_hashes", None)
            if not callable(compute):
                raise DispatcherError(
                    "the dispatcher has no input hashes and the factory cannot "
                    "compute them; every row must record its frozen inputs"
                )
            self._input_hashes = dict(compute())
        return dict(self._input_hashes)

    # -- public API -------------------------------------------------------
    def __call__(
        self, condition: str, seed: int, episode: int, context: dict
    ) -> Mapping[str, Any]:
        return self.execute(condition, seed, episode, context).row

    def execute(
        self, condition: str, seed: int, episode: int, context: Mapping[str, Any]
    ) -> DispatchRecord:
        arm = str(condition)
        if arm not in ARM_ORDER:
            raise DispatcherError(
                f"{arm!r} is not a campaign arm; declared: {list(ARM_ORDER)}"
            )
        seed = int(seed)
        episode = int(episode)
        if "environment_seed" not in context or "config_hashes" not in context:
            raise DispatcherError(
                "the episode context is missing environment_seed or config_hashes"
            )
        environment_seed = int(context["environment_seed"])
        if environment_seed < 0:
            raise DispatcherError("environment_seed cannot be negative")
        master_seed = int(context.get("master_seed", 0))
        if master_seed < 1:
            raise DispatcherError("the episode context has no positive master_seed")
        max_game_updates = int(context["max_game_updates"])
        if max_game_updates < 1:
            raise DispatcherError("max_game_updates must be positive")
        base: dict[str, Any] = {
            "seed": seed,
            "episode": episode,
            "environment_seed": environment_seed,
            "config_hashes": dict(context["config_hashes"]),
            "input_hashes": self.input_hashes,
            "max_game_updates": max_game_updates,
        }

        stage = "components"
        mirror: str | None = CONTROL_MIRRORS.get(arm)
        try:
            if arm == "floor":
                result = self._run_floor(base)
            elif arm in CONVENTIONAL_ARMS:
                result = self._run_conventional(arm, base)
            else:
                components = self._components(
                    arm, seed, episode, environment_seed, master_seed
                )
                fixed_result = None
                if mirror is not None:
                    stage = "mirror"
                    mirror_components = self._components(
                        mirror, seed, episode, environment_seed, master_seed
                    )
                    fixed_result = self.arm_runners[mirror](mirror_components, **base)
                stage = "episode"
                kwargs = dict(base, training=False)
                if fixed_result is not None:
                    result = self.arm_runners[arm](
                        components, fixed_result=fixed_result, **kwargs
                    )
                else:
                    result = self.arm_runners[arm](components, **kwargs)
            stage = "row"
            row = self._row(result, arm)
        except EpisodeFailure:
            raise
        except BaseException as cause:
            failure = EpisodeFailure(arm, seed, episode, cause, stage=stage)
            self._record_failure(failure)
            raise failure from cause
        return DispatchRecord(
            condition=arm,
            seed=seed,
            episode=episode,
            row=row,
            arm=arm,
            mirror=mirror,
        )

    # -- arm paths --------------------------------------------------------
    def _components(
        self,
        arm: str,
        seed: int,
        episode: int,
        environment_seed: int,
        master_seed: int,
    ) -> Any:
        return self.factory.neural_components(
            arm,
            seed=seed,
            episode=episode,
            environment_seed=environment_seed,
            master_seed=master_seed,
            training=False,
        )

    def _run_floor(self, base: Mapping[str, Any]) -> dict:
        adapter = self.factory.floor_adapter()
        kwargs = {key: value for key, value in base.items()}
        return self.arm_runners["floor"](adapter, **kwargs)

    def _run_conventional(self, arm: str, base: Mapping[str, Any]) -> dict:
        seed = int(base["seed"])
        components = self.factory.conventional_components(arm, seed=seed)
        kwargs = dict(base, condition_id=arm, training=False)
        if self.training_seeds is not None:
            kwargs["training_seeds"] = self.training_seeds
            kwargs["evaluation_seeds"] = self.evaluation_seeds
        return self.arm_runners[arm](components, **kwargs)

    def _row(self, result: Any, arm: str) -> dict:
        if not isinstance(result, Mapping) or "row" not in result:
            raise DispatcherError(
                f"{arm} did not return an episode artefact with a 'row'"
            )
        row = dict(result["row"])
        merged: dict[str, Any] = {}
        if "equivalence" in result:
            merged["equivalence"] = result["equivalence"]
        if "zero_pathway" in result:
            merged["zero_pathway"] = result["zero_pathway"]
        if merged:
            evidence = dict(row.get("evidence") or {})
            evidence.update(merged)
            row["evidence"] = evidence
        checked = validate_episode_row(row, expected_condition=arm)
        if (int(checked["seed"]), int(checked["episode"])) != (
            int(result["row"]["seed"]),
            int(result["row"]["episode"]),
        ):
            raise DispatcherError("the row was re-keyed while merging evidence")
        return checked

    # -- failure log ------------------------------------------------------
    def _record_failure(self, failure: EpisodeFailure) -> None:
        if self.failure_log is None:
            return
        try:
            self.failure_log.parent.mkdir(parents=True, exist_ok=True)
            with self.failure_log.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(failure.as_dict(), sort_keys=True) + "\n")
                handle.flush()
        except OSError as error:  # pragma: no cover - disk full / permissions
            raise DispatcherError(
                f"the episode failed and the failure log is unwritable: {error}"
            ) from error

    # -- description ------------------------------------------------------
    def describe(self) -> dict:
        return {
            "arms": list(ARM_ORDER),
            "neural_arms": list(NEURAL_ARMS),
            "conventional_arms": list(CONVENTIONAL_ARMS),
            "control_mirrors": dict(CONTROL_MIRRORS),
            "mirror_policy": (
                "A prime and C prime re-derive their declared mirror with the "
                "same paired environment seed; no retry on mismatch"
            ),
            "failure_log": (
                None if self.failure_log is None else self.failure_log.as_posix()
            ),
            "input_hashes_supplied": self._input_hashes is not None,
            "seed_sets_supplied": self.training_seeds is not None,
        }


__all__ = [
    "ARM_ORDER",
    "ARM_RUNNERS",
    "CONVENTIONAL_ARMS",
    "CONTROL_MIRRORS",
    "CampaignDispatcher",
    "DispatchRecord",
    "DispatcherError",
    "EpisodeFailure",
    "NEURAL_ARMS",
]
