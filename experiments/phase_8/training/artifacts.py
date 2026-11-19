"""Serialization, reload and integrity verification for training artifacts.

An artifact is a directory ``<root>/<condition_id>/seed_<campaign_seed>/``
containing exactly two files:

* ``parameters.npz`` — every saved tensor (parameters plus fixed buffers),
  pickle-free, named exactly as the model names them;
* ``manifest.json`` — the declared schema, seeds, architecture, embedded
  training configuration, provenance and SHA-256 of the parameter file.

Writing is refused for any ``origin = "trained"`` request: the protocol is
unapproved, so this task produces no trained artifact. The only writable
origin is ``"synthetic_fixture"`` with ``stage = "initialized"``, which exists
so tests can exercise serialization without a training run; the campaign
loader rejects that origin unless explicitly overridden.

Reading verifies the file hash, the stored shape/dtype table, the full-state
digest and the trainable-parameter digest before returning a rebuilt model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brain.banc_graph import sha256_file
from evaluation.conventional import ConventionalAgent, ConventionalConfig
from readout.linear import BiasOnlyReadout, LinearReadout

from .config import AGENT_CONFIG_FIELDS, TrainingConfig, canonical_json
from .errors import ArtifactCompatibilityError, ArtifactIntegrityError, ArtifactSchemaError
from .gate import assert_training_authorized
from .initialization import InitializedModel
from .state import (
    assert_state_keys,
    load_state,
    load_state_npz,
    parameter_dtypes,
    parameter_shapes,
    save_state_npz,
    state_digest,
    trainable_digest,
)
from .validation import (
    ARTIFACT_SCHEMA_VERSION,
    MANIFEST_NAME,
    ORIGINS,
    PARAMETERS_NAME,
    STAGES,
    assert_condition_compatibility,
    assert_expected_config,
    created_record,
    validate_manifest,
)

TOOL_NAME = "experiments.phase_8.training.artifacts"
#: Future declared location. Nothing in this task creates it.
TRAINING_ROOT = Path("experiments/results/phase_8/training")


@dataclass(frozen=True, eq=False)
class Artifact:
    directory: str
    manifest: dict
    model: Any = field(repr=False)
    state: dict = field(repr=False)
    compatibility: dict

    @property
    def condition_id(self) -> str:
        return str(self.manifest["condition_id"])

    @property
    def campaign_seed(self) -> int:
        return int(self.manifest["campaign_seed"])

    def describe(self) -> dict:
        return {
            "directory": self.directory,
            "condition_id": self.condition_id,
            "campaign_seed": self.campaign_seed,
            "training_seed": int(self.manifest["training_seed"]),
            "init_seed": int(self.manifest["init_seed"]),
            "origin": self.manifest["origin"],
            "stage": self.manifest["stage"],
            "model_kind": self.manifest["model_kind"],
            "parameter_digest": self.manifest["digest"]["trainable"],
            "state_digest": self.manifest["digest"]["state"],
            "parameters_sha256": self.manifest["parameters"]["sha256"],
            "compatibility": dict(self.compatibility),
        }


def artifact_directory(root: str | Path, condition_id: str, campaign_seed: int) -> Path:
    return Path(root) / str(condition_id) / f"seed_{int(campaign_seed)}"


def _check_origin_stage(origin: str, stage: str) -> None:
    if origin not in ORIGINS:
        raise ArtifactSchemaError(f"origin must be one of {ORIGINS}, got {origin!r}")
    if stage not in STAGES:
        raise ArtifactSchemaError(f"stage must be one of {STAGES}, got {stage!r}")
    if origin == "trained":
        # Always raises: the protocol is unapproved and authorises no execution.
        assert_training_authorized()
    if stage == "trained":
        raise ArtifactSchemaError(
            "a trained stage cannot be written: no authorized training run exists"
        )
    if origin != "synthetic_fixture":
        raise ArtifactSchemaError(
            "the only writable origin in this task is 'synthetic_fixture'"
        )


def build_manifest(
    initialized: InitializedModel,
    *,
    config: TrainingConfig,
    origin: str,
    stage: str,
) -> dict:
    training_config = config.as_dict()
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "condition_id": initialized.condition_id,
        "campaign_seed": int(initialized.campaign_seed),
        "training_seed": int(initialized.training_seed),
        "init_seed": int(initialized.init_seed),
        "master_seed": int(initialized.master_seed),
        "training_environment_seed": int(initialized.environment_seed),
        "n_features": int(initialized.n_features),
        "model_kind": initialized.kind,
        "architecture": dict(initialized.architecture),
        "origin": origin,
        "stage": stage,
        "training_config_sha256": config.sha256(),
        "training_config": training_config,
        "protocol": {
            "id": config.protocol_id,
            "sha256": config.protocol_sha256,
            "path": config.protocol_path,
            "matches_expected": True,
        },
        "campaign_config": {
            "path": config.campaign_path,
            "sha256": config.campaign_sha256,
        },
        "parameter_names": sorted(initialized.state),
        "parameter_shapes": parameter_shapes(initialized.state),
        "parameter_dtypes": parameter_dtypes(initialized.state),
        "digest": {
            "trainable": initialized.parameter_digest,
            "state": initialized.state_digest,
        },
        "parameters": {
            "file": PARAMETERS_NAME,
            "sha256": "0" * 64,
            "bytes": 1,
        },
        "created": created_record(TOOL_NAME),
    }


def write_artifact(
    root: str | Path,
    initialized: InitializedModel,
    *,
    config: TrainingConfig,
    origin: str = "synthetic_fixture",
    stage: str = "initialized",
) -> Path:
    """Write one initialized artifact; refuse to overwrite or to train."""
    if initialized.stage != "initialized":
        raise ArtifactSchemaError(
            "write_artifact accepts initialized state only; training is a "
            "separate, unauthorized stage"
        )
    _check_origin_stage(str(origin), str(stage))

    directory = artifact_directory(root, initialized.condition_id, initialized.campaign_seed)
    if directory.exists():
        raise ArtifactSchemaError(
            f"{directory} already exists; an artifact is never silently replaced"
        )
    directory.mkdir(parents=True)

    parameters = save_state_npz(directory / PARAMETERS_NAME, initialized.state)
    manifest = build_manifest(
        initialized, config=config, origin=str(origin), stage=str(stage)
    )
    manifest["parameters"] = {
        "file": PARAMETERS_NAME,
        "sha256": sha256_file(parameters),
        "bytes": int(parameters.stat().st_size),
    }
    validate_manifest(manifest)

    destination = directory / MANIFEST_NAME
    destination.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return directory


def read_manifest(directory: str | Path) -> dict:
    source = Path(directory) / MANIFEST_NAME
    if not source.is_file():
        raise ArtifactCompatibilityError(
            f"no training-artifact manifest at {source}"
        )
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactSchemaError(f"{source} is not readable JSON: {error}") from error
    return dict(validate_manifest(payload))


def verify_artifact_location(directory: str | Path, manifest: dict) -> None:
    directory = Path(directory)
    expected = artifact_directory(
        directory.parent.parent, manifest["condition_id"], manifest["campaign_seed"]
    )
    if directory.resolve() != expected.resolve():
        raise ArtifactCompatibilityError(
            f"the artifact at {directory} declares {manifest['condition_id']} "
            f"seed {manifest['campaign_seed']}; expected {expected}"
        )


def _rebuild(manifest: dict) -> Any:
    condition_id = str(manifest["condition_id"])
    architecture = dict(manifest["architecture"])
    width = int(manifest["n_features"])
    init_seed = int(manifest["init_seed"])
    if condition_id == "F":
        return LinearReadout(
            width, seed=init_seed, init_std=float(architecture["init_std"])
        )
    if condition_id == "F_beta":
        return BiasOnlyReadout(width, seed=init_seed)
    learner = architecture["e_learner"]
    config = ConventionalConfig(
        **{name: learner[name] for name in AGENT_CONFIG_FIELDS}
    )
    return ConventionalAgent(
        width, config=config, seed=init_seed, training=False
    )


def read_artifact(
    directory: str | Path,
    *,
    config: TrainingConfig | None = None,
    expected_condition: str | None = None,
) -> Artifact:
    """Load and fully verify one artifact before returning its model."""
    directory = Path(directory)
    manifest = read_manifest(directory)
    verify_artifact_location(directory, manifest)
    if expected_condition is not None and manifest["condition_id"] != expected_condition:
        raise ArtifactCompatibilityError(
            f"{manifest['condition_id']} artifact requested as {expected_condition}; "
            "conditions never borrow each other's artifacts"
        )
    if config is not None:
        assert_expected_config(manifest, config)

    parameters = directory / str(manifest["parameters"]["file"])
    if not parameters.is_file():
        raise ArtifactIntegrityError(f"the parameter file is missing: {parameters}")
    observed = sha256_file(parameters)
    if observed != manifest["parameters"]["sha256"]:
        raise ArtifactIntegrityError(
            f"parameter file sha256 is {observed}; the manifest records "
            f"{manifest['parameters']['sha256']}"
        )
    if int(parameters.stat().st_size) != int(manifest["parameters"]["bytes"]):
        raise ArtifactIntegrityError(
            "the parameter file length differs from the manifest"
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
            "the stored full-state digest differs from the manifest"
        )

    model = _rebuild(manifest)
    load_state(model, state)
    if trainable_digest(model) != manifest["digest"]["trainable"]:
        raise ArtifactIntegrityError(
            "the rebuilt trainable-parameter digest differs from the manifest"
        )
    compatibility = assert_condition_compatibility(manifest, model, state)
    if isinstance(model, ConventionalAgent):
        model.eval()
        model.reset_episode()
    return Artifact(
        directory=str(directory),
        manifest=manifest,
        model=model,
        state=state,
        compatibility=compatibility,
    )


def canonical_manifest(manifest: dict) -> str:
    """Stable serialization used when an artifact is cited by another record."""
    return canonical_json(manifest)


__all__ = [
    "Artifact",
    "TOOL_NAME",
    "TRAINING_ROOT",
    "artifact_directory",
    "build_manifest",
    "canonical_manifest",
    "read_artifact",
    "read_manifest",
    "verify_artifact_location",
    "write_artifact",
]
