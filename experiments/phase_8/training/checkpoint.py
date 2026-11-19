"""Training checkpoints: a resumable state record, not a training artifact.

SCIENTIFIC STATUS
    A checkpoint stores parameters and progress counters from a training run so
    a run can be resumed. It is **not** a training artifact: it is never loaded
    by the campaign loader, it carries no ``origin = "trained"`` state and it
    cannot be passed to :func:`~.artifacts.write_artifact`. REV4 declares no
    checkpoint cadence, no retention rule and no checkpoint format, so the
    cadence and the directory are explicit caller inputs; this module adds no
    default.

    Two things are deliberately **not** restored, because the protocol does not
    declare them and the existing models do not expose them:

    * sampler RNG state — resuming continues from the stored parameters, not
      from the exact sampling stream, so a resumed run is parameter-continuous
      and not bit-identical to an uninterrupted one;
    * optimizer state — F/Fβ use stateless SGD, and E's Adam moments are not
      part of :meth:`evaluation.conventional.ConventionalAgent.numpy_state`.

    Both facts are written into every checkpoint so a resumed run cannot claim
    bit-exact reproducibility it does not have.

    Refusal is preserved: a payload whose origin is ``"trained"`` routes through
    :func:`~.gate.assert_training_authorized` and therefore always raises.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from brain.banc_graph import sha256_file

from .config import TrainingConfig
from .errors import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    ArtifactSchemaError,
    TrainingConfigError,
)
from .gate import assert_training_authorized
from .initialization import initialize
from .state import (
    assert_state_keys,
    load_state,
    load_state_npz,
    model_architecture,
    model_kind,
    model_state,
    parameter_dtypes,
    parameter_shapes,
    save_state_npz,
    state_digest,
    trainable_digest,
)
from .validation import (
    PARAMETERS_NAME,
    assert_condition_compatibility,
    created_record,
)

TOOL_NAME = "experiments.phase_8.training.checkpoint"
CHECKPOINT_SCHEMA_VERSION = 1
CHECKPOINT_NAME = "checkpoint.json"
CHECKPOINT_ORIGIN = "synthetic_fixture"
CHECKPOINT_STAGE = "training_checkpoint"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_KEYS = {
    "schema_version",
    "tool",
    "origin",
    "stage",
    "condition_id",
    "campaign_seed",
    "training_seed",
    "init_seed",
    "master_seed",
    "training_config_sha256",
    "protocol",
    "campaign_config",
    "model_kind",
    "architecture",
    "n_features",
    "parameter_names",
    "parameter_shapes",
    "parameter_dtypes",
    "digest",
    "parameters",
    "progress",
    "rng",
    "optimizer",
    "created",
}


@dataclass(frozen=True, eq=False)
class Checkpoint:
    directory: str
    manifest: dict
    state: dict = field(repr=False)

    @property
    def condition_id(self) -> str:
        return str(self.manifest["condition_id"])

    @property
    def campaign_seed(self) -> int:
        return int(self.manifest["campaign_seed"])

    @property
    def progress(self) -> dict:
        return dict(self.manifest["progress"])

    def describe(self) -> dict:
        progress = self.progress
        return {
            "directory": self.directory,
            "condition_id": self.condition_id,
            "campaign_seed": self.campaign_seed,
            "training_seed": int(self.manifest["training_seed"]),
            "model_kind": self.manifest["model_kind"],
            "episodes_completed": int(progress["episodes_completed"]),
            "updates_completed": int(progress["updates_completed"]),
            "parameter_digest": self.manifest["digest"]["trainable"],
            "state_digest": self.manifest["digest"]["state"],
            "rng_checkpointed": bool(self.manifest["rng"]["checkpointed"]),
            "optimizer_state_checkpointed": bool(
                self.manifest["optimizer"]["state_checkpointed"]
            ),
        }


@dataclass(frozen=True, eq=False)
class RestoredCheckpoint:
    checkpoint: Checkpoint
    model: Any = field(repr=False)
    state: dict = field(repr=False)
    parameter_digest: str
    state_digest: str
    rng_restored: bool = False
    optimizer_state_restored: bool = False

    @property
    def directory(self) -> str:
        return self.checkpoint.directory

    @property
    def manifest(self) -> dict:
        return self.checkpoint.manifest

    @property
    def condition_id(self) -> str:
        return self.checkpoint.condition_id

    @property
    def campaign_seed(self) -> int:
        return self.checkpoint.campaign_seed

    @property
    def progress(self) -> dict:
        return self.checkpoint.progress

    def describe(self) -> dict:
        return {
            **self.checkpoint.describe(),
            "resumed": True,
            "rng_restored": False,
            "optimizer_state_restored": False,
            "limitation": (
                "resume restores parameters and counters only; the sampler RNG "
                "and any optimizer momentum restart, so a resumed run is "
                "parameter-continuous and not bit-identical"
            ),
        }


def checkpoint_directory(
    root: str | Path, condition_id: str, campaign_seed: int, step: int
) -> Path:
    """Declared location, caller-relative: ``<root>/<condition>/seed_<n>/step_<k>``."""
    return (
        Path(root)
        / str(condition_id)
        / f"seed_{int(campaign_seed)}"
        / f"step_{int(step)}"
    )


def _positive_or_zero(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrainingConfigError(f"{name} must be an integer")
    if int(value) < 0:
        raise TrainingConfigError(f"{name} cannot be negative")
    return int(value)


def _check_origin_stage(origin: str, stage: str) -> None:
    if str(origin) == "trained":
        # Always raises: the protocol is unapproved and authorises no execution.
        assert_training_authorized()
    if str(origin) != CHECKPOINT_ORIGIN:
        raise ArtifactSchemaError(
            f"the only writable checkpoint origin is {CHECKPOINT_ORIGIN!r}"
        )
    if str(stage) != CHECKPOINT_STAGE:
        raise ArtifactSchemaError(
            f"the only writable checkpoint stage is {CHECKPOINT_STAGE!r}; a "
            "checkpoint is not a training artifact"
        )


def build_checkpoint_payload(
    model: Any,
    *,
    config: TrainingConfig,
    condition_id: str,
    campaign_seed: int,
    training_seed: int,
    init_seed: int,
    master_seed: int,
    progress: Mapping[str, Any],
    origin: str = CHECKPOINT_ORIGIN,
    stage: str = CHECKPOINT_STAGE,
) -> dict:
    """The manifest of one checkpoint, before the parameter hash is known."""
    _check_origin_stage(str(origin), str(stage))
    state = model_state(model)
    record = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "origin": str(origin),
        "stage": str(stage),
        "condition_id": str(condition_id),
        "campaign_seed": _positive_or_zero(int(campaign_seed), "campaign_seed"),
        "training_seed": _positive_or_zero(int(training_seed), "training_seed"),
        "init_seed": _positive_or_zero(int(init_seed), "init_seed"),
        "master_seed": _positive_or_zero(int(master_seed), "master_seed"),
        "training_config_sha256": config.sha256(),
        "protocol": {
            "id": config.protocol_id,
            "sha256": config.protocol_sha256,
        },
        "campaign_config": {"sha256": config.campaign_sha256},
        "model_kind": model_kind(model),
        "architecture": model_architecture(model),
        "n_features": int(getattr(model, "n_features", 0)),
        "parameter_names": sorted(state),
        "parameter_shapes": parameter_shapes(state),
        "parameter_dtypes": parameter_dtypes(state),
        "digest": {
            "trainable": trainable_digest(model),
            "state": state_digest(state),
        },
        "parameters": {"file": PARAMETERS_NAME, "sha256": "0" * 64, "bytes": 1},
        "progress": {
            "episodes_completed": _positive_or_zero(
                int(progress["episodes_completed"]), "episodes_completed"
            ),
            "updates_completed": _positive_or_zero(
                int(progress["updates_completed"]), "updates_completed"
            ),
            "budget": dict(progress.get("budget", {})),
            "environment_seeds_used": [
                int(seed) for seed in progress.get("environment_seeds_used", [])
            ],
            "sampling_seed": (
                None
                if progress.get("sampling_seed") is None
                else int(progress["sampling_seed"])
            ),
            "metrics_sha256": str(progress.get("metrics_sha256", "")),
        },
        "rng": {
            "checkpointed": False,
            "note": (
                "sampler RNG state is not stored: REV4 declares no RNG "
                "checkpoint, so a resumed run restarts the sampling stream"
            ),
        },
        "optimizer": {
            "state_checkpointed": False,
            "note": (
                "F/Fβ use stateless SGD; E's Adam moments are not part of the "
                "stored parameter array, so no optimizer state is restored"
            ),
        },
        "created": created_record(TOOL_NAME),
    }
    return record


def validate_checkpoint(payload: Mapping) -> dict:
    """Check a checkpoint manifest for completeness and internal consistency."""
    if not isinstance(payload, Mapping):
        raise ArtifactSchemaError("a checkpoint manifest must be a mapping")
    missing = sorted(REQUIRED_KEYS - set(payload))
    if missing:
        raise ArtifactSchemaError(f"the checkpoint manifest is missing {missing}")
    if int(payload["schema_version"]) != CHECKPOINT_SCHEMA_VERSION:
        raise ArtifactSchemaError(
            f"checkpoint schema_version is {payload['schema_version']}; expected "
            f"{CHECKPOINT_SCHEMA_VERSION}"
        )
    _check_origin_stage(str(payload["origin"]), str(payload["stage"]))
    condition_id = str(payload["condition_id"])
    if condition_id not in ("F", "F_beta", "E", "E_full"):
        raise ArtifactSchemaError(
            f"{condition_id!r} is not a trainable condition"
        )
    campaign = _positive_or_zero(int(payload["campaign_seed"]), "campaign_seed")
    training = _positive_or_zero(int(payload["training_seed"]), "training_seed")
    if campaign == training:
        raise ArtifactSchemaError(
            "a checkpoint records disjoint campaign and training seeds "
            "(REV4 §3.5 row 9, §3.6 row 9)"
        )
    digest = payload["digest"]
    for key in ("trainable", "state"):
        if not _SHA256.match(str(digest[key])):
            raise ArtifactSchemaError(f"digest.{key} is not a SHA-256 hex value")
    if dict(payload["parameters"]).get("file") != PARAMETERS_NAME:
        raise ArtifactSchemaError(
            f"checkpoint parameters must be stored in {PARAMETERS_NAME}"
        )
    if bool(payload["rng"]["checkpointed"]):
        raise ArtifactSchemaError(
            "this checkpoint format does not store RNG state; a record that "
            "claims it does cannot be trusted"
        )
    if bool(payload["optimizer"]["state_checkpointed"]):
        raise ArtifactSchemaError(
            "this checkpoint format does not store optimizer state"
        )
    progress = payload["progress"]
    _positive_or_zero(int(progress["episodes_completed"]), "episodes_completed")
    _positive_or_zero(int(progress["updates_completed"]), "updates_completed")
    if not isinstance(progress["budget"], Mapping):
        raise ArtifactSchemaError("progress.budget must be a mapping")
    seeds = progress["environment_seeds_used"]
    if not isinstance(seeds, list):
        raise ArtifactSchemaError("progress.environment_seeds_used must be a list")
    return dict(payload)


def write_checkpoint(
    directory: str | Path,
    model: Any,
    *,
    config: TrainingConfig,
    condition_id: str,
    campaign_seed: int,
    training_seed: int,
    init_seed: int,
    master_seed: int,
    progress: Mapping[str, Any],
    origin: str = CHECKPOINT_ORIGIN,
    stage: str = CHECKPOINT_STAGE,
) -> Path:
    """Write one checkpoint; never overwrite, never label it trained."""
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("write_checkpoint requires a TrainingConfig")
    destination = Path(directory)
    if destination.exists():
        raise ArtifactSchemaError(
            f"{destination} already exists; a checkpoint is never silently replaced"
        )
    payload = build_checkpoint_payload(
        model,
        config=config,
        condition_id=condition_id,
        campaign_seed=campaign_seed,
        training_seed=training_seed,
        init_seed=init_seed,
        master_seed=master_seed,
        progress=progress,
        origin=origin,
        stage=stage,
    )
    destination.mkdir(parents=True)
    parameters = save_state_npz(destination / PARAMETERS_NAME, model_state(model))
    payload["parameters"] = {
        "file": PARAMETERS_NAME,
        "sha256": sha256_file(parameters),
        "bytes": int(parameters.stat().st_size),
    }
    validate_checkpoint(payload)
    (destination / CHECKPOINT_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return destination


def read_checkpoint(
    directory: str | Path,
    *,
    config: TrainingConfig | None = None,
    expected_condition: str | None = None,
) -> Checkpoint:
    """Read and fully verify one checkpoint before returning its arrays."""
    directory = Path(directory)
    source = directory / CHECKPOINT_NAME
    if not source.is_file():
        raise ArtifactCompatibilityError(f"no checkpoint at {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactSchemaError(
            f"{source} is not readable JSON: {error}"
        ) from error
    manifest = validate_checkpoint(payload)
    if config is not None:
        if str(manifest["training_config_sha256"]) != config.sha256():
            raise ArtifactCompatibilityError(
                "the checkpoint was produced under a different training "
                "configuration"
            )
        if str(manifest["protocol"]["sha256"]) != str(config.protocol_sha256):
            raise ArtifactCompatibilityError(
                "the checkpoint was produced against a different REV4 document"
            )
    if expected_condition is not None and (
        manifest["condition_id"] != str(expected_condition)
    ):
        raise ArtifactCompatibilityError(
            f"{manifest['condition_id']} checkpoint requested as "
            f"{expected_condition}"
        )

    parameters = directory / str(manifest["parameters"]["file"])
    if not parameters.is_file():
        raise ArtifactIntegrityError(f"the parameter file is missing: {parameters}")
    observed = sha256_file(parameters)
    if observed != manifest["parameters"]["sha256"]:
        raise ArtifactIntegrityError(
            f"checkpoint parameters sha256 is {observed}; the manifest records "
            f"{manifest['parameters']['sha256']}"
        )
    if int(parameters.stat().st_size) != int(manifest["parameters"]["bytes"]):
        raise ArtifactIntegrityError(
            "the checkpoint parameter file length differs from the manifest"
        )
    state = load_state_npz(parameters)
    assert_state_keys(
        state,
        names=manifest["parameter_names"],
        shapes=manifest["parameter_shapes"],
        dtypes=manifest["parameter_dtypes"],
    )
    if state_digest(state) != manifest["digest"]["state"]:
        raise ArtifactIntegrityError(
            "the stored full-state digest differs from the checkpoint manifest"
        )
    return Checkpoint(
        directory=str(directory), manifest=manifest, state=state
    )


def restore_checkpoint(
    directory: str | Path,
    *,
    config: TrainingConfig,
    expected_condition: str | None = None,
    model: Any | None = None,
) -> RestoredCheckpoint:
    """Rebuild a model and load the checkpoint's parameters into it.

    ``model`` may be supplied (for example the model a run was already using);
    otherwise a fresh model is built from the manifest's declared seeds via the
    existing initializer. Either way the loaded state is re-digested and the
    condition compatibility check runs again.
    """
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("restore_checkpoint requires a TrainingConfig")
    checkpoint = read_checkpoint(
        directory, config=config, expected_condition=expected_condition
    )
    manifest = checkpoint.manifest
    target = model
    if target is None:
        target = initialize(
            str(manifest["condition_id"]),
            campaign_seed=int(manifest["campaign_seed"]),
            training_seed=int(manifest["training_seed"]),
            master_seed=int(manifest["master_seed"]),
        ).model
    if model_kind(target) != manifest["model_kind"]:
        raise ArtifactCompatibilityError(
            f"the checkpoint stores {manifest['model_kind']}, but the supplied "
            f"model is {model_kind(target)}"
        )
    if int(getattr(target, "n_features", -1)) != int(manifest["n_features"]):
        raise ArtifactCompatibilityError(
            "the supplied model's feature width differs from the checkpoint"
        )
    load_state(target, checkpoint.state)
    if trainable_digest(target) != manifest["digest"]["trainable"]:
        raise ArtifactIntegrityError(
            "the restored trainable-parameter digest differs from the manifest"
        )
    assert_condition_compatibility(manifest, target, checkpoint.state)
    return RestoredCheckpoint(
        checkpoint=checkpoint,
        model=target,
        state=checkpoint.state,
        parameter_digest=trainable_digest(target),
        state_digest=state_digest(checkpoint.state),
    )


def describe_checkpoint_interface() -> dict:
    """The declared checkpoint contract, including what it does not restore."""
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "file": CHECKPOINT_NAME,
        "parameters": PARAMETERS_NAME,
        "origin": CHECKPOINT_ORIGIN,
        "stage": CHECKPOINT_STAGE,
        "not_a_training_artifact": True,
        "loaded_by_campaign_loader": False,
        "cadence": "caller-supplied; REV4 declares none",
        "retention": "caller-supplied; REV4 declares none",
        "rng_restored": False,
        "optimizer_state_restored": False,
        "limitation": (
            "resume restores parameters and counters only, so a resumed run is "
            "parameter-continuous and not bit-identical to an uninterrupted run"
        ),
    }


__all__ = [
    "CHECKPOINT_NAME",
    "CHECKPOINT_ORIGIN",
    "CHECKPOINT_SCHEMA_VERSION",
    "CHECKPOINT_STAGE",
    "Checkpoint",
    "RestoredCheckpoint",
    "TOOL_NAME",
    "build_checkpoint_payload",
    "checkpoint_directory",
    "describe_checkpoint_interface",
    "read_checkpoint",
    "restore_checkpoint",
    "validate_checkpoint",
    "write_checkpoint",
]
