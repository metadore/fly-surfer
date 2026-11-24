"""Production episode runner for Pilot 2-C (D3, REV4 §10.8 as amended).

SCIENTIFIC STATUS
    One call runs one Pilot 2-C episode on the frozen biological substrate, or
    one substrate-free floor replay of the paired environment seed. It adds no
    biological parameter and estimates no contrast. A, B, F, Fβ and A′ are the
    unchanged Phase 8 conditions; the floor is the unchanged constant-NO_ACTION
    control. F and Fβ read pre-existing trained artifacts: this runner never
    trains, retrains or substitutes a model.

    The runner is not an authorisation. It is reached through
    :func:`experiments.phase_8.stages.common.drive_pilot`, which refuses unless
    the exact Pilot 2-C grid passes the D3 stage gate; the synthetic-fixture
    path relabels every row and may not write under the results root.

A′ IDENTITY
    A′ must reproduce A exactly on P1–P19 with no tolerance. The comparison
    needs the in-process A artefact, so A runs before A′ for every
    ``(seed, episode)``. On the first unequal field the A′ row is still
    produced and returned with the mismatch payload, the runner marks the
    identity failed, and any further A′ episode is refused. That is the
    §3.8.5 hard stop: artefacts are retained, B is invalidated by the
    certification evaluator, and no episode is retried.

    A resumed process has no in-process A artefact. A′ is then refused with an
    explicit error rather than silently re-running A.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Mapping

import numpy as np

from ..campaign.factory import (
    CampaignFactory,
    FactoryError,
    FactorySettings,
    TrainingArtifacts,
)
from ..conditions import a_fixed, b_plastic, f_readout
from ..conditions.base import spec_for
from ..conditions.execute import error_row, neural_episode, utc_timestamp
from ..config import PROJECT_ROOT, Phase8Config
from ..controls import a_prime, f_beta
from ..controls import floor as floor_control
from ..controls.equivalence import (
    EquivalenceMismatch,
    check_control_invariants,
    compare_runs,
)
from ..seeds import environment_seed
from .common import StageConfigurationError

PILOT2C_STAGE = "pilot2c"
PILOT2C_ARMS = ("A", "B", "F", "F_beta", "A_prime", "floor")
PILOT2C_NEURAL_ARMS = ("A", "B", "F", "F_beta", "A_prime")
PILOT2C_SEEDS = (9001, 9002, 9003)
PILOT2C_STAGE_PURPOSE = "floor_and_identity_certification"
RUNNER_ID = "phase_8.stages.pilot2c_runner.Pilot2CEpisodeRunner"

_CONDITION_SOURCES = {
    "A": "experiments.phase_8.conditions.a_fixed",
    "B": "experiments.phase_8.conditions.b_plastic",
    "F": "experiments.phase_8.conditions.f_readout",
    "F_beta": "experiments.phase_8.controls.f_beta",
    "A_prime": "experiments.phase_8.controls.a_prime",
    "floor": "experiments.phase_8.controls.floor",
}


def _tensor_digest(tensor: Any) -> str:
    array = np.ascontiguousarray(tensor.detach().cpu().numpy())
    return hashlib.sha256(array.tobytes()).hexdigest()


def _delta_block(state: Any) -> dict:
    if state is None:
        return {"available": False}
    delta = np.maximum(
        np.abs(state.delta_exc.astype(np.float64)),
        np.abs(state.delta_inh.astype(np.float64)),
    )
    return {
        "available": True,
        "eligible_edges": int(state.n_plastic),
        "changed_edges": int(np.count_nonzero(delta)),
        "max_abs_delta_pa": float(delta.max()) if delta.size else 0.0,
        "n_update_calls": int(state.n_update_calls),
        "clamp_hits": int(state.clamp_hits_total),
        "update_clip_hits": int(state.update_clip_hits_total),
    }


def _readout_snapshot(model: Any) -> dict:
    """Digest the readout parameters before and after an evaluation episode."""
    weights = getattr(model, "feature_weights", None)
    snapshot = {
        "kind": type(model).__name__,
        "state_independent": bool(getattr(model, "state_independent", False)),
        "n_features": int(getattr(model, "n_features", -1)),
        "trainable_parameters": list(model.parameter_names()),
        "feature_weight_sha256": None,
        "feature_weight_nonzero": None,
        "parameter_digest": None,
    }
    if weights is not None:
        snapshot["feature_weight_sha256"] = _tensor_digest(weights)
        snapshot["feature_weight_nonzero"] = int(np.count_nonzero(weights.detach().cpu().numpy()))
    try:
        from readout.linear import parameter_digest

        snapshot["parameter_digest"] = parameter_digest(model)
    except Exception:  # noqa: BLE001 - the snapshot must never fabricate a digest
        snapshot["parameter_digest"] = None
    return snapshot


class Pilot2CEpisodeRunner:
    """Run one Pilot 2-C episode per call; the driver supplies the seed grid.

    ``factory`` and ``artifacts`` are injectable for focused tests. The default
    factory is built against the declared frozen inputs and refuses F/Fβ
    without a loaded trained readout. ``pairing`` is the explicit A-2
    ``(condition, evaluation seed) -> training seed`` declaration; it is never
    inferred.
    """

    def __init__(
        self,
        config: Phase8Config,
        *,
        factory: Any | None = None,
        artifacts: Any | None = None,
        pairing: Mapping[tuple[str, int], int] | None = None,
    ) -> None:
        self.config = config
        self._factory = factory
        self.artifacts = artifacts
        self.pairing = {key: int(value) for key, value in (pairing or {}).items()}
        self._a_results: dict[tuple[int, int], dict] = {}
        self._identity_failed = False
        self._provenance_cache: dict | None = None
        self._clock: Callable[[], float] = time.perf_counter

    # -- factory ---------------------------------------------------------
    @property
    def factory(self) -> Any:
        if self._factory is None:
            training = None
            if self.artifacts is not None:
                training = getattr(self.artifacts, "training", self.artifacts)
            if not isinstance(training, TrainingArtifacts) and training is not None:
                raise StageConfigurationError(
                    "the supplied artifacts do not expose a TrainingArtifacts "
                    "provider"
                )
            self._factory = CampaignFactory(
                frozen_inputs=self.config.campaign.frozen_inputs,
                training=training,
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

    # -- call ------------------------------------------------------------
    def __call__(
        self, arm: str, seed: int, episode: int, context: Mapping[str, Any]
    ) -> dict:
        arm = str(arm)
        if arm not in PILOT2C_ARMS:
            raise StageConfigurationError(
                f"Pilot 2-C does not declare arm {arm!r}"
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
        self._check_context(
            arm, master_seed, seed, episode, env_seed, max_updates, config_hashes
        )
        if arm == "A_prime" and self._identity_failed:
            raise StageConfigurationError(
                "A′ stopped after an exact identity mismatch; REV4 §3.8.5 "
                "permits no retry and no further A′ episode"
            )

        # Provenance first: a failure here is not an episode failure.
        input_hashes = self.input_hashes()

        started_at = utc_timestamp()
        started = self._clock()
        metadata: dict = {}
        try:
            if arm == "floor":
                result = floor_control.run(
                    self.factory.floor_adapter(),
                    seed=seed,
                    episode=episode,
                    environment_seed=env_seed,
                    config_hashes=config_hashes,
                    input_hashes=input_hashes,
                    max_game_updates=max_updates,
                )
                readout = None
            else:
                components = self.factory.neural_components(
                    arm,
                    seed=seed,
                    episode=episode,
                    environment_seed=env_seed,
                    master_seed=master_seed,
                    training=False,
                )
                metadata = dict(getattr(components, "metadata", {}) or {})
                readout = self._run_neural(
                    arm,
                    components,
                    seed=seed,
                    episode=episode,
                    environment_seed=env_seed,
                    config_hashes=config_hashes,
                    input_hashes=input_hashes,
                    max_game_updates=max_updates,
                )
                result = readout["result"]
        except (FactoryError, StageConfigurationError):
            raise
        except Exception as error:  # noqa: BLE001 - the row records the failure
            return self._failure_row(
                arm=arm,
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
        if row["condition"] != arm:
            raise StageConfigurationError(
                f"the episode returned condition {row['condition']!r}, not {arm!r}"
            )
        notes = dict(row.get("notes") or {})
        notes.update(
            self._provenance(
                {"condition_id": arm, "environment_seed": env_seed, **metadata}
            )
        )
        if arm == "floor":
            notes["floor"] = {
                "substrate_free": True,
                "policy": "constant NO_ACTION",
                "evidence": dict(result.get("floor_evidence") or {}),
            }
        else:
            notes["game_loop"] = self._game_loop(result)
            if readout is not None:
                notes.update(readout["notes"])
        row["notes"] = notes
        return row

    # -- per-arm execution ------------------------------------------------
    def _run_neural(
        self,
        arm: str,
        components: Any,
        *,
        seed: int,
        episode: int,
        environment_seed: int,
        config_hashes: Mapping[str, Any],
        input_hashes: Mapping[str, Any],
        max_game_updates: int,
    ) -> dict:
        readout_before = None
        model = getattr(getattr(components, "neural", None), "decision_source", None)
        model = getattr(model, "model", None)
        if arm in ("F", "F_beta") and model is not None:
            readout_before = _readout_snapshot(model)

        common = {
            "seed": seed,
            "episode": episode,
            "environment_seed": environment_seed,
            "config_hashes": config_hashes,
            "input_hashes": input_hashes,
            "max_game_updates": max_game_updates,
            "training": False,
        }

        if arm == "A":
            result = a_fixed.run(components, **common)
            self._a_results[(seed, episode)] = result
        elif arm == "B":
            result = b_plastic.run(components, **common)
        elif arm == "F":
            result = f_readout.run(
                components,
                training_seeds=tuple(self.config.campaign.training_seeds),
                evaluation_seeds=tuple(self.config.campaign.pilot_seeds),
                **common,
            )
        elif arm == "F_beta":
            result = f_beta.run(
                components,
                training_seeds=tuple(self.config.campaign.training_seeds),
                evaluation_seeds=tuple(self.config.campaign.pilot_seeds),
                **common,
            )
        elif arm == "A_prime":
            result = self._run_a_prime(components, **common)
        else:  # pragma: no cover - guarded by the arm check
            raise StageConfigurationError(f"no neural path for arm {arm!r}")

        notes: dict = {}
        if arm in ("F", "F_beta") and readout_before is not None:
            notes["readout_certification"] = self._readout_certification(
                arm, model, readout_before, result
            )
        if arm in ("B", "A_prime"):
            notes["plasticity"] = self._plasticity_evidence(arm, result)
        if arm == "A_prime":
            notes["a_prime"] = {
                "mirror": "A",
                "fixed_result_present": True,
                "equivalence": dict(result.get("equivalence") or {}),
                "zero_pathway": dict(result.get("zero_pathway") or {}),
                "hard_stop": bool(
                    not (result.get("equivalence") or {}).get("all_equal", False)
                ),
                "invalidates_on_mismatch": ["B"],
            }
        return {"result": result, "notes": notes}

    def _run_a_prime(
        self, components: Any, *, seed: int, episode: int, **kwargs: Any
    ) -> dict:
        fixed = self._a_results.get((int(seed), int(episode)))
        if fixed is None:
            raise StageConfigurationError(
                "A′ needs the in-process A result for "
                f"(seed {seed}, episode {episode}); a resumed run has no such "
                "artefact, and A is never silently re-run to manufacture one"
            )
        a_prime.validate(components)
        # neural_episode is called here rather than through a_prime.run so the
        # produced artefact survives an EquivalenceMismatch (REV4 §3.8.5).
        result = neural_episode(
            "A_prime", components, seed=int(seed), episode=int(episode), **kwargs
        )
        invariants = check_control_invariants(result, control_id="A_prime")
        try:
            report = compare_runs(fixed, result, control_id="A_prime")
        except EquivalenceMismatch as error:
            self._identity_failed = True
            report = {
                "all_equal": False,
                "tolerance": "none",
                "mismatch": dict(error.payload),
            }
        result["equivalence"] = report
        result["zero_pathway"] = invariants
        return result

    def _readout_certification(
        self, arm: str, model: Any, before: Mapping[str, Any], result: dict
    ) -> dict:
        after = _readout_snapshot(model)
        block = {
            "condition": arm,
            "before": dict(before),
            "after": after,
            "weights_frozen": before["parameter_digest"] == after["parameter_digest"]
            and before["feature_weight_sha256"] == after["feature_weight_sha256"],
        }
        if arm == "F":
            block["state_dependent"] = not after["state_independent"]
            block["feature_weights_all_zero"] = (
                after["feature_weight_nonzero"] == 0
            )
        elif arm == "F_beta":
            checks = {}
            assert_state = getattr(model, "assert_state_independent", None)
            if callable(assert_state):
                try:
                    checks = dict(assert_state())
                except Exception as error:  # noqa: BLE001 - recorded, not hidden
                    checks = {"error": f"{type(error).__name__}: {error}"}
            width = int(after["n_features"])
            zero = np.zeros((1, width), dtype=np.float64)
            saturated = np.full((1, width), 1.0e6, dtype=np.float64)
            zero_logits = np.asarray(model.logits(zero), dtype=np.float64)
            saturated_logits = np.asarray(model.logits(saturated), dtype=np.float64)
            block["state_independent"] = after["state_independent"]
            block["feature_weights_all_zero"] = (
                after["feature_weight_nonzero"] == 0
            )
            block["invariant_checks"] = checks
            block["logits_zero_features"] = [float(v) for v in zero_logits.ravel()]
            block["logits_saturated_features"] = [
                float(v) for v in saturated_logits.ravel()
            ]
            block["logits_identical"] = bool(
                np.array_equal(zero_logits, saturated_logits)
            )
        artifact = self._artifact_block(arm)
        if artifact is not None:
            block["artifact"] = artifact
        return block

    def _plasticity_evidence(self, arm: str, result: dict) -> dict:
        state = getattr(result["stepper"], "weight_state", None)
        summary = result["summary"]
        weight_updates = list(result.get("weight_updates") or ())
        block = _delta_block(state)
        block.update(
            {
                "condition": arm,
                "n_update_reports": int(len(weight_updates)),
                "n_hook_calls": int(len(weight_updates)),
                "hook_modes": sorted(
                    {
                        str(entry.get("mode"))
                        for entry in weight_updates
                        if isinstance(entry, Mapping)
                    }
                ),
                "summary_plasticity": dict(summary.get("plasticity") or {}),
                "weights_before_sha256": summary["weights_before"]["sha256"],
                "weights_after_sha256": summary["weights_after"]["sha256"],
                "weights_unchanged": bool(summary["weights_unchanged"]),
            }
        )
        return block

    def _artifact_block(self, arm: str) -> dict | None:
        if self.artifacts is None:
            return None
        manifests = getattr(self.artifacts, "manifests", None) or {}
        keys = [
            key
            for key in manifests
            if str(key[0]) == arm and int(key[1]) in PILOT2C_SEEDS
        ]
        if not keys:
            return None
        entries = []
        for key in sorted(keys):
            manifest = dict(manifests[key])
            entries.append(
                {
                    "condition_id": str(manifest["condition_id"]),
                    "evaluation_seed": int(manifest["campaign_seed"]),
                    "training_seed": int(manifest["training_seed"]),
                    "origin": str(manifest["origin"]),
                    "stage": str(manifest["stage"]),
                    "parameter_file_sha256": str(
                        manifest["parameters"]["sha256"]
                    ),
                    "parameter_digest": manifest.get("digest"),
                }
            )
        return {"entries": entries}

    # -- context -----------------------------------------------------------
    def _check_context(
        self,
        arm: str,
        master_seed: int,
        seed: int,
        episode: int,
        env_seed: int,
        max_updates: int,
        config_hashes: Mapping[str, str],
    ) -> None:
        campaign = self.config.campaign
        if seed not in PILOT2C_SEEDS:
            raise StageConfigurationError(
                f"seed {seed} is not in the D3 Pilot 2-C scope {PILOT2C_SEEDS}"
            )
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
            str(name): str(entry["sha256"])
            for name, entry in self.config.hashes.items()
        }
        if dict(config_hashes) != declared:
            raise StageConfigurationError(
                "the driver config hashes do not match the loaded configuration"
            )

    # -- provenance --------------------------------------------------------
    def _provenance(self, metadata: Mapping[str, Any]) -> dict:
        if self._provenance_cache is None:
            from ..campaign.protocol import (
                AMENDMENT_ID,
                AMENDMENT_PATH,
                OWNER_DECISION_D3_RECORD,
            )

            def _sha(path: Any) -> str | None:
                from brain.banc_graph import sha256_file

                source = getattr(path, "path", path)
                return sha256_file(source) if source else None

            self._provenance_cache = {
                "owner_decision": "D3",
                "owner_decision_sha256": _sha(OWNER_DECISION_D3_RECORD),
                "amendment_id": AMENDMENT_ID,
                "amendment_sha256": _sha(AMENDMENT_PATH),
            }
        condition_id = str(metadata.get("condition_id"))
        if condition_id == "floor":
            # The floor owns no stream; only the paired environment seed exists.
            seed_plan_block: dict = {
                "environment_seed": metadata.get("environment_seed"),
                "seed_streams": "none (substrate-free; no network, learning or structure stream)",
            }
        else:
            seed_plan_block = {
                key: metadata.get(key)
                for key in (
                    "network_seed",
                    "learning_seed",
                    "structure_seed",
                    "environment_seed",
                )
                if key in metadata
            }
        return {
            "evidence_kind": "pilot",
            "runner": RUNNER_ID,
            "stage_purpose": PILOT2C_STAGE_PURPOSE,
            "substrate": (
                "none" if condition_id == "floor" else "biological_graph"
            ),
            "condition_source": _CONDITION_SOURCES.get(condition_id, "unknown"),
            "seed_plan": seed_plan_block,
            "provenance_binding": dict(self._provenance_cache),
            "does_not_establish": (
                "Pilot 2-C certifies a floor and an identity; it estimates no "
                "C1-C4, H1-H3, paired dispersion or sigma_max, selects no N and "
                "is never merged into the campaign dataset"
            ),
        }

    @staticmethod
    def _game_loop(result: Mapping[str, Any]) -> dict:
        summary = result["summary"]
        return {
            "game_updates": int(summary["updates"]),
            "neural_steps": int(summary["neural_steps"]),
            "neural_resets_during_episode": int(
                summary["neural_resets_during_episode"]
            ),
            "total_spikes": int(summary["total_spikes"]),
            "motor_spikes": int(summary["motor_spikes"]),
            "action_counts": dict(summary["action_counts"]),
            "total_reward": float(summary["total_reward"]),
            "survival_score": float(result["row"]["survival_score"]),
            "terminated": bool(summary["terminated"]),
            "truncated": bool(summary["truncated"]),
            "termination_reason": summary["termination_reason"],
            "weights_unchanged": bool(summary["weights_unchanged"]),
        }

    def _failure_row(
        self,
        *,
        arm: str,
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
            condition=arm,
            role=spec_for(arm).role,
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
        notes.update(
            self._provenance({"condition_id": arm, "environment_seed": env_seed})
        )
        notes["failure"] = {
            "error_type": type(error).__name__,
            "recorded_as": "status=error row; no update count is claimed",
        }
        row["notes"] = notes
        return row


__all__ = [
    "PILOT2C_ARMS",
    "PILOT2C_NEURAL_ARMS",
    "PILOT2C_SEEDS",
    "PILOT2C_STAGE",
    "PILOT2C_STAGE_PURPOSE",
    "Pilot2CEpisodeRunner",
    "RUNNER_ID",
]
