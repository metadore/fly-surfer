"""Trained-artifact writer for the D5 pilot runs.

SCIENTIFIC STATUS
    This module turns a completed :class:`~.pilot_training.PilotTrainingResult`
    into the two-file training artifact the rest of Phase 8 reads
    (``parameters.npz`` + ``manifest.json``), plus a separate
    ``training_run.json`` provenance record. The manifest carries
    ``origin = "trained"`` and ``stage = "trained"``; it is written only after
    the run actually completed its declared episode budget.

    Nothing here trains or authorises anything. Writing is refused when the
    result did not perform training, carries an unverified checkpoint history,
    is interrupted, is not one of the six D5 artifacts, or comes from a
    synthetic fixture while claiming to be experimental evidence. A fixture run
    can be written for tests only with ``evidence_kind = "synthetic_fixture"``,
    and that record says plainly that it is not experimental evidence.

    ``training_run.json`` is deliberately outside the artifact schema: the
    manifest forbids extra keys, so the provenance lives beside it. The reader
    re-checks the manifest and parameter hashes before returning anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from brain.banc_graph import sha256_file

from .artifacts import artifact_directory, build_manifest, read_artifact
from .config import TrainingConfig, canonical_json, validate_training_config
from .d5 import PILOT_TRAINING_EPISODES, assert_d5_training_authorized
from .errors import ArtifactIntegrityError, ArtifactSchemaError, TrainingConfigError, TrainingNotAuthorized
from .exact_checkpoint import EXACT_CHECKPOINT_NAME
from .pilot import PILOT_SUBSTRATE, PilotArtifactPlan, PilotTrainingPlan
from .state import (
    model_architecture,
    model_kind,
    model_state,
    save_state_npz,
    state_digest,
    trainable_digest,
)
from .validation import MANIFEST_NAME, PARAMETERS_NAME, created_record, validate_manifest

TOOL_NAME = "experiments.phase_8.training.pilot_artifact"
TRAINING_RUN_NAME = "training_run.json"
TRAINING_RUN_SCHEMA_VERSION = 1
EVIDENCE_KINDS = ("experimental", "synthetic_fixture")


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    raise TrainingConfigError(
        f"provenance of type {type(value).__name__} is not JSON-safe"
    )


@dataclass(frozen=True, eq=False)
class TrainedModelView:
    """The surface :func:`build_manifest` consumes for a trained model."""

    condition_id: str
    campaign_seed: int
    training_seed: int
    init_seed: int
    master_seed: int
    environment_seed: int
    kind: str
    architecture: dict
    state: dict
    parameter_digest: str
    state_digest: str
    stage: str = "trained"

    @property
    def n_features(self) -> int:
        return int(self.architecture["n_features"])


def _check_result(result: Any, entry: PilotArtifactPlan) -> None:
    for field in ("origin", "stage"):
        if str(getattr(result, field, None)) != "trained":
            raise ArtifactSchemaError(
                f"a trained artifact requires result.{field} == 'trained'; got "
                f"{getattr(result, field, None)!r}"
            )
    if getattr(result, "training_performed_here", False) is not True:
        raise ArtifactSchemaError(
            "the result records no training performed in this process; a "
            "fixture or deserialized state cannot stand in for a trained run"
        )
    if bool(getattr(result, "interrupted", True)):
        raise ArtifactSchemaError(
            "an interrupted run is not a finished artifact; resume it from its "
            "verified checkpoint first"
        )
    if str(result.condition_id) != str(entry.condition_id):
        raise ArtifactIntegrityError(
            "the run's condition does not match the plan entry"
        )
    for field, expected in (
        ("campaign_seed", entry.evaluation_seed),
        ("training_seed", entry.training_seed),
        ("init_seed", entry.init_seed),
    ):
        if int(getattr(result, field)) != int(expected):
            raise ArtifactIntegrityError(
                f"the run's {field} does not match the plan entry"
            )
    if int(result.episodes_completed) != int(entry.episodes):
        raise ArtifactSchemaError(
            f"the run completed {result.episodes_completed} of {entry.episodes} "
            "episodes; an incomplete artifact is refused"
        )
    if int(entry.episodes) != PILOT_TRAINING_EPISODES:
        raise TrainingNotAuthorized(
            f"D5 authorises exactly {PILOT_TRAINING_EPISODES} episodes per artifact"
        )
    if not getattr(result, "checkpoints", ()):
        raise ArtifactSchemaError(
            "the run records no checkpoints; B5 requires one per episode"
        )


def _authorisation(plan: PilotTrainingPlan | None) -> dict:
    from .d5 import d5_applicability

    report = d5_applicability()
    if not report.get("applicable"):
        raise TrainingNotAuthorized(report["reason"])
    d5_sha = (report.get("d6") or {}).get("sources", {}).get("d5", {}).get(
        "observed_sha256"
    )
    d6_sha = None
    d6_path = (report.get("d6") or {}).get("path")
    if isinstance(d6_path, str) and Path(d6_path).is_file():
        d6_sha = sha256_file(Path(d6_path))
    payload = {
        "owner_decision": "D5",
        "d6": "D6",
        "applicable": True,
        "approval_date": report.get("approval_date"),
        "d5_path": report.get("path"),
        "d5_sha256": d5_sha,
        "d6_path": d6_path,
        "d6_sha256": d6_sha,
        "does_not_authorise": list(report.get("does_not_authorise") or []),
        "substrate": PILOT_SUBSTRATE,
        "uses_randomized_graph": False,
    }
    if plan is not None:
        payload["d5_sha256"] = plan.d5_sha256
        payload["d6_sha256"] = plan.d6_sha256
        payload["config_sha256"] = plan.config_sha256
        payload["b3_sha256"] = plan.b3.get("sha256")
        payload["approval_date"] = plan.authorisation.get("approval_date")
        payload["does_not_authorise"] = list(
            plan.authorisation.get("does_not_authorise") or []
        )
    return payload


def _checkpoint_history(result: Any) -> list[dict]:
    history: list[dict] = []
    for record in result.checkpoints:
        item = _jsonable(dict(record))
        directory = Path(str(item["directory"]))
        manifest_path = directory / EXACT_CHECKPOINT_NAME
        if not manifest_path.is_file():
            raise ArtifactIntegrityError(
                f"the checkpoint manifest is missing: {manifest_path}"
            )
        if sha256_file(manifest_path) != item.get("manifest_sha256"):
            raise ArtifactIntegrityError(
                f"the checkpoint manifest changed after verification: {directory}"
            )
        item["retained"] = True
        history.append(item)
    return history


def write_trained_artifact(
    phase8_config: Any,
    result: Any,
    entry: PilotArtifactPlan,
    *,
    root: str | Path,
    plan: PilotTrainingPlan | None = None,
    config: TrainingConfig | None = None,
    evidence_kind: str = "experimental",
) -> dict:
    """Write one completed D5 artifact and its provenance; never overwrite."""
    if not isinstance(entry, PilotArtifactPlan):
        raise TrainingConfigError("write_trained_artifact requires a plan entry")
    kind = str(evidence_kind)
    if kind not in EVIDENCE_KINDS:
        raise TrainingConfigError(f"evidence_kind must be one of {EVIDENCE_KINDS}")
    if entry.substrate != PILOT_SUBSTRATE:
        raise TrainingNotAuthorized(
            "D5 authorises the frozen biological substrate only"
        )
    assert_d5_training_authorized(
        entry.condition_id, entry.evaluation_seed, episodes=entry.episodes
    )
    if config is None:
        config = validate_training_config(phase8_config)
    _check_result(result, entry)

    substrate = str(getattr(result, "substrate", PILOT_SUBSTRATE))
    if kind == "experimental" and substrate != PILOT_SUBSTRATE:
        raise TrainingNotAuthorized(
            f"a run on {substrate!r} cannot become experimental evidence; D5 "
            "authorises the frozen biological graph only"
        )

    directory = artifact_directory(root, entry.condition_id, entry.evaluation_seed)
    for name in (MANIFEST_NAME, PARAMETERS_NAME, TRAINING_RUN_NAME):
        if (directory / name).exists():
            raise ArtifactSchemaError(
                f"{directory / name} already exists; a trained artifact is never "
                "silently replaced"
            )

    model = result.model
    state = model_state(model)
    architecture = model_architecture(model)
    view = TrainedModelView(
        condition_id=entry.condition_id,
        campaign_seed=entry.evaluation_seed,
        training_seed=entry.training_seed,
        init_seed=entry.init_seed,
        master_seed=int(config.master_seed),
        environment_seed=int(entry.environment_seeds[0]),
        kind=model_kind(model),
        architecture=architecture,
        state=state,
        parameter_digest=trainable_digest(model),
        state_digest=state_digest(state),
    )

    directory.mkdir(parents=True, exist_ok=True)
    parameters = save_state_npz(directory / PARAMETERS_NAME, state)
    manifest = build_manifest(
        view, config=config, origin="trained", stage="trained"
    )
    manifest["parameters"] = {
        "file": PARAMETERS_NAME,
        "sha256": sha256_file(parameters),
        "bytes": int(parameters.stat().st_size),
    }
    validate_manifest(manifest)
    manifest_path = directory / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    artwork = read_artifact(
        directory, config=config, expected_condition=entry.condition_id
    )
    if artwork.manifest["origin"] != "trained" or artwork.manifest["stage"] != "trained":
        raise ArtifactIntegrityError(
            "the written artifact does not reload as a trained artifact"
        )
    if artwork.manifest["digest"]["trainable"] != view.parameter_digest:
        raise ArtifactIntegrityError(
            "the reloaded artifact digest differs from the trained parameters"
        )

    checkpoints = _checkpoint_history(result)
    limitations = [
        "training updates the readout parameters only; no synaptic weight is changed",
        "a readout action label is executed because the game accepts it, not "
        "because a biological motor command was identified",
        "this artifact is a trained parameter state; it is not evidence that a "
        "behaviour was learned and no analysis has been run on it",
        "exact resumption is claimed only where verify_equivalence demonstrates "
        "it; the checkpoints store every B6 component they can observe",
        "no environment RNG state is checkpointed: the controlled game is "
        "rebuilt from its B4 episode seed at each episode start",
    ]
    if kind == "synthetic_fixture":
        limitations.insert(
            0,
            "synthetic fixture substrate: this record is a test artifact and is "
            "not experimental evidence",
        )

    provenance = {
        "schema_version": TRAINING_RUN_SCHEMA_VERSION,
        "kind": "pilot_training_run",
        "tool": TOOL_NAME,
        "evidence_kind": kind,
        "experimental_evidence": bool(kind == "experimental"),
        "origin": "trained",
        "stage": "trained",
        "condition_id": entry.condition_id,
        "evaluation_seed": entry.evaluation_seed,
        "campaign_seed": entry.evaluation_seed,
        "training_seed": entry.training_seed,
        "pool_index": int(entry.pool_index),
        "init_seed": entry.init_seed,
        "master_seed": int(config.master_seed),
        "substrate": substrate,
        "uses_randomized_graph": False,
        "identity": {
            "condition_id": entry.condition_id,
            "evaluation_seed": entry.evaluation_seed,
            "training_seed": entry.training_seed,
            "pool_index": int(entry.pool_index),
            "n_features": view.n_features,
            "model_kind": view.kind,
        },
        "authorisation": _authorisation(plan),
        "training_config": {
            "sha256": config.sha256(),
            "protocol": {
                "id": config.protocol_id,
                "sha256": config.protocol_sha256,
                "path": config.protocol_path,
            },
            "campaign_config": {
                "path": config.campaign_path,
                "sha256": config.campaign_sha256,
            },
        },
        "seeds": {
            "b3": {
                "contract": "B3",
                "version": "D4-v1",
                "derivation_sha256": (
                    plan.b3.get("sha256") if plan is not None else None
                ),
                "entry": _jsonable(dict(entry.b3)),
            },
            "b4": {
                "contract": "B4",
                "schedule": [int(seed) for seed in entry.environment_seeds],
                "initialization_environment_seed": int(
                    entry.initialization_environment_seed
                ),
                "episodes": int(entry.episodes),
            },
            "network_seed": int(entry.network_seed),
            "sampling_seed": int(result.sampling_seed),
        },
        "budget": dict(result.budget),
        "episodes_completed": int(result.episodes_completed),
        "episodes": _jsonable([dict(item) for item in result.episodes]),
        "digest": {
            "initial_parameter": str(result.initial_parameter_digest),
            "trainable": str(result.parameter_digest),
            "state": str(result.state_digest),
        },
        "artifacts": {
            "parameters": {
                "file": PARAMETERS_NAME,
                "sha256": manifest["parameters"]["sha256"],
                "bytes": int(manifest["parameters"]["bytes"]),
            },
            "manifest": {
                "file": MANIFEST_NAME,
                "sha256": sha256_file(manifest_path),
                "bytes": int(manifest_path.stat().st_size),
            },
        },
        "checkpoints": checkpoints,
        "checkpoint_policy": {
            "cadence": "one checkpoint after every completed training episode",
            "retention": "every intermediate checkpoint and the final checkpoint",
            "schema_version": (
                int(checkpoints[0]["schema_version"]) if checkpoints else None
            ),
        },
        "resume": _jsonable(dict(result.resume)),
        "rng": {
            "components": ["python", "numpy", "torch", "sampler"],
            "environment": {
                "present": False,
                "reason": (
                    "the controlled game is rebuilt and reset from its B4 seed at "
                    "every episode start, so no environment RNG state survives "
                    "the episode boundary"
                ),
            },
        },
        "optimizer": {
            "state_checkpointed": True,
            "checkpoint_digests": [
                {
                    "episode": int(item["episode"]),
                    "optimizer": str(item["digest"]["optimizer"]),
                }
                for item in checkpoints
            ],
        },
        "frozen_inputs": _jsonable(
            dict(getattr(phase8_config.campaign, "frozen_inputs", {}) or {})
        ),
        "limitations": limitations,
        "created": created_record(TOOL_NAME),
    }
    provenance_path = directory / TRAINING_RUN_NAME
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return {
        "directory": directory.as_posix(),
        "condition_id": entry.condition_id,
        "evaluation_seed": entry.evaluation_seed,
        "origin": "trained",
        "stage": "trained",
        "evidence_kind": kind,
        "experimental_evidence": bool(kind == "experimental"),
        "parameter_digest": view.parameter_digest,
        "state_digest": view.state_digest,
        "parameters_sha256": manifest["parameters"]["sha256"],
        "manifest_sha256": provenance["artifacts"]["manifest"]["sha256"],
        "training_run_sha256": sha256_file(provenance_path),
        "training_run": provenance_path.as_posix(),
        "episodes_completed": int(result.episodes_completed),
        "checkpoints": len(checkpoints),
    }


def read_training_run(directory: str | Path) -> dict:
    """Load one provenance record and re-check it against its artifact."""
    directory = Path(directory)
    source = directory / TRAINING_RUN_NAME
    if not source.is_file():
        raise ArtifactIntegrityError(f"no training-run provenance at {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactSchemaError(
            f"{source} is not readable JSON: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ArtifactSchemaError("the training-run record must be a JSON object")
    if payload.get("kind") != "pilot_training_run":
        raise ArtifactSchemaError("the provenance record is not a pilot training run")
    if payload.get("origin") != "trained" or payload.get("stage") != "trained":
        raise ArtifactSchemaError(
            "the provenance record does not describe a trained artifact"
        )
    if payload.get("evidence_kind") not in EVIDENCE_KINDS:
        raise ArtifactSchemaError("the provenance evidence_kind is not declared")
    if 0 < int(payload.get("episodes_completed", 0)) < int(
        payload.get("budget", {}).get("value", 0)
    ):
        raise ArtifactIntegrityError(
            "the provenance records an incomplete episode budget"
        )

    manifest_path = directory / MANIFEST_NAME
    parameters_path = directory / PARAMETERS_NAME
    if not manifest_path.is_file() or not parameters_path.is_file():
        raise ArtifactIntegrityError(
            "the artifact files are missing beside the provenance record"
        )
    recorded = payload.get("artifacts") or {}
    if sha256_file(parameters_path) != (recorded.get("parameters") or {}).get("sha256"):
        raise ArtifactIntegrityError(
            "the parameter file does not match the provenance record"
        )
    if sha256_file(manifest_path) != (recorded.get("manifest") or {}).get("sha256"):
        raise ArtifactIntegrityError(
            "the manifest does not match the provenance record"
        )
    return payload


def verify_trained_artifact(
    directory: str | Path,
    *,
    config: TrainingConfig | None = None,
    expected_condition: str | None = None,
) -> dict:
    """Reload the artifact, verify it, and confirm its provenance agrees."""
    artifact = read_artifact(
        directory, config=config, expected_condition=expected_condition
    )
    if artifact.manifest["origin"] != "trained" or artifact.manifest["stage"] != "trained":
        raise ArtifactIntegrityError(
            f"{artifact.directory} is not a trained artifact"
        )
    provenance = read_training_run(directory)
    for name, manifest_name in (
        ("condition_id", "condition_id"),
        ("evaluation_seed", "campaign_seed"),
        ("training_seed", "training_seed"),
        ("init_seed", "init_seed"),
    ):
        if str(provenance.get(name)) != str(artifact.manifest[manifest_name]):
            raise ArtifactIntegrityError(
                f"the provenance {name} disagrees with the artifact manifest"
            )
    if str(provenance["digest"]["trainable"]) != str(
        artifact.manifest["digest"]["trainable"]
    ):
        raise ArtifactIntegrityError(
            "the provenance trainable digest disagrees with the manifest"
        )
    if str(provenance["digest"]["state"]) != str(
        artifact.manifest["digest"]["state"]
    ):
        raise ArtifactIntegrityError(
            "the provenance state digest disagrees with the manifest"
        )
    return {
        "directory": artifact.directory,
        "artifact": artifact.describe(),
        "provenance": {
            "evidence_kind": provenance["evidence_kind"],
            "experimental_evidence": bool(provenance["experimental_evidence"]),
            "episodes_completed": int(provenance["episodes_completed"]),
            "checkpoints": len(provenance.get("checkpoints") or []),
        },
        "verified": True,
    }


def describe_trained_interface() -> dict:
    return {
        "files": [PARAMETERS_NAME, MANIFEST_NAME, TRAINING_RUN_NAME],
        "origin": "trained",
        "stage": "trained",
        "evidence_kinds": list(EVIDENCE_KINDS),
        "authorised_by": "D5",
        "authorises_further_execution": False,
    }


__all__ = [
    "EVIDENCE_KINDS",
    "TOOL_NAME",
    "TRAINING_RUN_NAME",
    "TRAINING_RUN_SCHEMA_VERSION",
    "TrainedModelView",
    "describe_trained_interface",
    "read_training_run",
    "verify_trained_artifact",
    "write_trained_artifact",
]
