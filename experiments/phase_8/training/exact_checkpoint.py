"""Exact checkpoints: parameters, optimizer moments and every RNG stream.

SCIENTIFIC STATUS
    Owner decision D4 B5 fixes the checkpoint policy (after every completed
    training episode; keep every intermediate and the final checkpoint) and B6
    fixes what exact resumption means (parameters, optimizer state and moments,
    Python/NumPy/PyTorch RNG, sampler, and the applicable environment RNG). This
    module implements that contract; it trains nothing and writes a checkpoint
    only when a caller explicitly supplies a run's state.

    A checkpoint here is still **not a training artifact**. It carries
    ``origin = "synthetic_fixture"``, ``stage = "training_checkpoint"``, is
    never loaded by the campaign loader, and cannot be passed to
    :func:`~.artifacts.write_artifact`.

    Exactness is a claim that must be demonstrated, never assumed. A manifest
    that claims exactness while a required component is absent is refused by
    :func:`validate_exact_checkpoint`, and
    :func:`verify_equivalence` compares an uninterrupted run with an
    interrupted-and-resumed run field by field before the claim is made.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from brain.banc_graph import sha256_file

from .config import TrainingConfig, canonical_json, sha256_text
from .contracts import CONTRACT_VERSION
from .errors import (
    ArtifactIntegrityError,
    ArtifactSchemaError,
    TrainingConfigError,
    TrainingError,
)
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
from .validation import PARAMETERS_NAME, created_record

TOOL_NAME = "experiments.phase_8.training.exact_checkpoint"
EXACT_CHECKPOINT_SCHEMA_VERSION = 2
EXACT_CHECKPOINT_NAME = "checkpoint.json"
EXACT_COMPONENTS_NAME = "components.npz"
EXACT_ORIGIN = "synthetic_fixture"
EXACT_STAGE = "training_checkpoint"
TRAINABLE_CHECKPOINT_CONDITIONS = ("F", "F_beta", "E", "E_full")
REQUIRED_RNG_COMPONENTS = ("python", "numpy", "torch", "sampler")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPTIMIZER_PREFIX = "optimizer::"
_TORCH_RNG_KEY = "torch_rng"
_RNG_JSON_KEY = "rng_json"
_OPTIMIZER_SCALARS_KEY = "optimizer_scalars"


# ---------------------------------------------------------------------------
# JSON-safe conversion
# ---------------------------------------------------------------------------


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
    raise TrainingConfigError(
        f"checkpoint metadata of type {type(value).__name__} is not JSON-safe"
    )


def _tupleize(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tupleize(item) for item in value)
    return value


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.match(value))


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


def capture_rng_state(
    *,
    sampler: Any,
    environment_state: Any = None,
    environment_reason: str | None = None,
) -> dict:
    """Every declared B6 RNG component for one checkpoint boundary."""
    if sampler is None or not hasattr(sampler, "bit_generator"):
        raise TrainingConfigError(
            "B6 exact checkpointing requires the action sampler's NumPy generator"
        )
    if environment_reason is not None and (
        not isinstance(environment_reason, str) or not environment_reason.strip()
    ):
        raise TrainingConfigError(
            "environment_reason must be a non-empty string when supplied"
        )
    if environment_state is not None:
        reason = environment_reason or "caller-supplied environment RNG state"
    else:
        reason = environment_reason or (
            "the caller exposes no environment RNG state; the fixture must "
            "be deterministic in its environment seed for exact equivalence"
        )
    return {
        "python": _jsonable(random.getstate()),
        "numpy": _jsonable(np.random.get_state()),
        "torch": np.array(
            torch.get_rng_state().cpu().numpy(), dtype=np.uint8, copy=True
        ),
        "sampler": _jsonable(sampler.bit_generator.state),
        "environment": (
            None if environment_state is None else _jsonable(environment_state)
        ),
        "environment_present": environment_state is not None,
        "environment_reason": reason,
    }


def capture_optimizer_state(optimizer: Any) -> tuple[dict, dict]:
    """Flatten an optimizer ``state_dict`` into arrays plus JSON scalars."""
    if optimizer is None:
        raise TrainingConfigError("B6 exact checkpointing requires an optimizer")
    state = optimizer.state_dict()
    arrays: dict[str, np.ndarray] = {}
    scalars: dict[str, Any] = {"param_groups": [], "state": {}}
    for group in state.get("param_groups", []):
        scalars["param_groups"].append(
            {str(key): _jsonable(value) for key, value in group.items()}
        )
    for parameter_id, entries in state.get("state", {}).items():
        for key, value in entries.items():
            if torch.is_tensor(value):
                arrays[f"{_OPTIMIZER_PREFIX}{int(parameter_id)}::{key}"] = (
                    value.detach().cpu().numpy()
                )
            else:
                scalars["state"].setdefault(str(int(parameter_id)), {})[
                    str(key)
                ] = _jsonable(value)
    return arrays, scalars


def _optimizer_state_dict(arrays: Mapping[str, np.ndarray], scalars: Mapping) -> dict:
    state: dict = {"state": {}, "param_groups": list(scalars["param_groups"])}
    for name, array in arrays.items():
        _, parameter_id, key = name.split("::", 2)
        state["state"].setdefault(int(parameter_id), {})[key] = torch.as_tensor(
            np.asarray(array)
        )
    for parameter_id, entries in (scalars.get("state") or {}).items():
        for key, value in entries.items():
            state["state"].setdefault(int(parameter_id), {})[key] = value
    return state


def _rng_digests(rng: Mapping[str, Any]) -> dict:
    return {
        "python": sha256_text(canonical_json(rng["python"])),
        "numpy": sha256_text(canonical_json(rng["numpy"])),
        "torch": sha256_text(canonical_json(rng["torch"].tolist())),
        "sampler": sha256_text(canonical_json(rng["sampler"])),
        "environment": (
            sha256_text(canonical_json(rng["environment"]))
            if rng["environment_present"]
            else None
        ),
    }


def _optimizer_digest(arrays: Mapping[str, np.ndarray], scalars: Mapping) -> str:
    array_digest = state_digest(arrays) if arrays else "empty"
    return sha256_text(
        canonical_json({"arrays": array_digest, "scalars": _jsonable(scalars)})
    )


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def build_exact_payload(
    model: Any,
    *,
    config: TrainingConfig,
    condition_id: str,
    campaign_seed: int,
    training_seed: int,
    init_seed: int,
    master_seed: int,
    progress: Mapping[str, Any],
    optimizer: Any,
    sampler: Any,
    environment_state: Any = None,
    environment_reason: str | None = None,
    origin: str = EXACT_ORIGIN,
    stage: str = EXACT_STAGE,
) -> tuple[dict, dict, dict, dict]:
    """The manifest and its three encoded components, before file hashes."""
    if str(origin) == "trained":
        from .gate import assert_training_authorized

        assert_training_authorized()
    if str(origin) != EXACT_ORIGIN:
        raise ArtifactSchemaError(
            f"the only writable exact-checkpoint origin is {EXACT_ORIGIN!r}"
        )
    if str(stage) != EXACT_STAGE:
        raise ArtifactSchemaError(
            f"the only writable exact-checkpoint stage is {EXACT_STAGE!r}"
        )
    state = model_state(model)
    optimizer_arrays, optimizer_scalars = capture_optimizer_state(optimizer)
    rng = capture_rng_state(
        sampler=sampler,
        environment_state=environment_state,
        environment_reason=environment_reason,
    )
    rng_digests = _rng_digests(rng)

    payload = {
        "schema_version": EXACT_CHECKPOINT_SCHEMA_VERSION,
        "kind": "exact_checkpoint",
        "tool": TOOL_NAME,
        "origin": str(origin),
        "stage": str(stage),
        "contract_version": CONTRACT_VERSION,
        "owner_decision": "D4",
        "condition_id": str(condition_id),
        "campaign_seed": int(campaign_seed),
        "training_seed": int(training_seed),
        "init_seed": int(init_seed),
        "master_seed": int(master_seed),
        "training_config_sha256": config.sha256(),
        "protocol": {"id": config.protocol_id, "sha256": config.protocol_sha256},
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
            "optimizer": _optimizer_digest(optimizer_arrays, optimizer_scalars),
            **{f"rng_{name}": digest for name, digest in rng_digests.items()},
        },
        "parameters": {"file": PARAMETERS_NAME, "sha256": "0" * 64, "bytes": 1},
        "components": {
            "file": EXACT_COMPONENTS_NAME,
            "sha256": "0" * 64,
            "bytes": 1,
            "optimizer_arrays": sorted(optimizer_arrays),
        },
        "optimizer": {
            "state_checkpointed": True,
            "n_arrays": len(optimizer_arrays),
            "param_groups": _jsonable(optimizer_scalars["param_groups"]),
        },
        "rng": {
            "checkpointed": True,
            "python": {"present": True, "sha256": rng_digests["python"]},
            "numpy": {"present": True, "sha256": rng_digests["numpy"]},
            "torch": {"present": True, "sha256": rng_digests["torch"]},
            "sampler": {"present": True, "sha256": rng_digests["sampler"]},
            "environment": {
                "present": bool(rng["environment_present"]),
                "sha256": rng_digests["environment"],
                "reason": rng["environment_reason"],
            },
        },
        "progress": {
            "episodes_completed": int(progress["episodes_completed"]),
            "updates_completed": int(progress["updates_completed"]),
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
            "episodes": _jsonable(
                [dict(item) for item in progress.get("episodes", [])]
            ),
        },
        "b3": dict(progress.get("b3", {})),
        "b4": dict(progress.get("b4", {})),
        "b5": {
            "cadence": 1,
            "retention": "all intermediate checkpoints and the final checkpoint",
            "format": f"exact-checkpoint schema {EXACT_CHECKPOINT_SCHEMA_VERSION}",
        },
        "b6": {
            "components": list(REQUIRED_RNG_COMPONENTS)
            + (["environment"] if rng["environment_present"] else []),
            "exactness_claimed": False,
            "note": (
                "exactness is claimed only after verify_equivalence compares an "
                "uninterrupted run with this resumed run"
            ),
        },
        "created": created_record(TOOL_NAME),
    }
    components = {
        "arrays": optimizer_arrays,
        "scalars": optimizer_scalars,
        "rng": rng,
    }
    return payload, components, rng, rng_digests


def validate_exact_checkpoint(payload: Any) -> dict:
    """Schema and completeness checks; an incomplete exact claim is refused."""
    if not isinstance(payload, Mapping):
        raise ArtifactSchemaError("an exact checkpoint manifest must be a mapping")
    required = {
        "schema_version",
        "kind",
        "tool",
        "origin",
        "stage",
        "contract_version",
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
        "components",
        "optimizer",
        "rng",
        "progress",
        "b3",
        "b4",
        "b5",
        "b6",
        "created",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ArtifactSchemaError(f"the exact-checkpoint manifest is missing {missing}")
    if int(payload["schema_version"]) != EXACT_CHECKPOINT_SCHEMA_VERSION:
        raise ArtifactSchemaError(
            f"exact-checkpoint schema_version is {payload['schema_version']}; "
            f"expected {EXACT_CHECKPOINT_SCHEMA_VERSION}"
        )
    if payload.get("kind") != "exact_checkpoint":
        raise ArtifactSchemaError("kind must be 'exact_checkpoint'")
    if payload.get("origin") != EXACT_ORIGIN or payload.get("stage") != EXACT_STAGE:
        raise ArtifactSchemaError(
            f"an exact checkpoint is origin={EXACT_ORIGIN!r} stage={EXACT_STAGE!r}"
        )
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise ArtifactSchemaError(
            f"contract_version must be {CONTRACT_VERSION!r}"
        )
    condition_id = str(payload["condition_id"])
    if condition_id not in TRAINABLE_CHECKPOINT_CONDITIONS:
        raise ArtifactSchemaError(
            f"{condition_id!r} is not a trainable checkpoint condition"
        )
    if int(payload["campaign_seed"]) == int(payload["training_seed"]):
        raise ArtifactSchemaError(
            "campaign_seed and training_seed must stay disjoint (REV4 §3.5 row 9, "
            "§3.6 row 9)"
        )
    for key in ("trainable", "state", "optimizer"):
        if not _hex64((payload["digest"] or {}).get(key)):
            raise ArtifactSchemaError(f"digest.{key} is not a 64-hex digest")
    parameters = payload["parameters"]
    if parameters.get("file") != PARAMETERS_NAME:
        raise ArtifactSchemaError(f"parameters.file must be {PARAMETERS_NAME!r}")
    if not _hex64(parameters.get("sha256")):
        raise ArtifactSchemaError("parameters.sha256 is not a 64-hex digest")
    components = payload["components"]
    if components.get("file") != EXACT_COMPONENTS_NAME:
        raise ArtifactSchemaError(
            f"components.file must be {EXACT_COMPONENTS_NAME!r}"
        )
    if not _hex64(components.get("sha256")):
        raise ArtifactSchemaError("components.sha256 is not a 64-hex digest")

    if payload["rng"].get("checkpointed") is not True:
        raise ArtifactSchemaError(
            "B6 requires every RNG stream; a checkpoint that does not store "
            "RNG state cannot claim exact resumption"
        )
    for name in REQUIRED_RNG_COMPONENTS:
        entry = (payload["rng"] or {}).get(name)
        if not isinstance(entry, Mapping) or entry.get("present") is not True:
            raise ArtifactSchemaError(
                f"B6 requires the {name} RNG component, but the checkpoint "
                "records it as absent; exact resumption cannot be claimed"
            )
        if not _hex64(entry.get("sha256")):
            raise ArtifactSchemaError(f"rng.{name}.sha256 is not a 64-hex digest")
    environment = (payload["rng"] or {}).get("environment")
    if not isinstance(environment, Mapping):
        raise ArtifactSchemaError("rng.environment must be a mapping")
    if environment.get("present") is True:
        if not _hex64(environment.get("sha256")):
            raise ArtifactSchemaError("rng.environment.sha256 is not a 64-hex digest")
    elif not str(environment.get("reason") or "").strip():
        raise ArtifactSchemaError(
            "an absent environment RNG entry must record why it is not applicable"
        )
    if payload["optimizer"].get("state_checkpointed") is not True:
        raise ArtifactSchemaError(
            "B6 requires optimizer state and moments; the manifest records none"
        )
    progress = payload["progress"]
    for name in ("episodes_completed", "updates_completed"):
        if isinstance(progress.get(name), bool) or not isinstance(
            progress.get(name), int
        ):
            raise ArtifactSchemaError(f"progress.{name} must be an integer")
        if int(progress[name]) < 0:
            raise ArtifactSchemaError(f"progress.{name} cannot be negative")
    if not isinstance(progress.get("episodes"), list):
        raise ArtifactSchemaError(
            "progress.episodes must list every completed episode, so a resume "
            "can carry the full provenance"
        )
    if len(progress["episodes"]) != int(progress["episodes_completed"]):
        raise ArtifactSchemaError(
            "progress.episodes disagrees with progress.episodes_completed"
        )
    return dict(payload)


# ---------------------------------------------------------------------------
# write / read / restore
# ---------------------------------------------------------------------------


def write_exact_checkpoint(
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
    optimizer: Any,
    sampler: Any,
    environment_state: Any = None,
    environment_reason: str | None = None,
    origin: str = EXACT_ORIGIN,
    stage: str = EXACT_STAGE,
) -> Path:
    """Write one exact checkpoint; never overwrite and never label it trained."""
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("write_exact_checkpoint requires a TrainingConfig")
    destination = Path(directory)
    if destination.exists():
        raise ArtifactSchemaError(
            f"{destination} already exists; a checkpoint is never silently replaced"
        )
    payload, components, rng, _ = build_exact_payload(
        model,
        config=config,
        condition_id=condition_id,
        campaign_seed=campaign_seed,
        training_seed=training_seed,
        init_seed=init_seed,
        master_seed=master_seed,
        progress=progress,
        optimizer=optimizer,
        sampler=sampler,
        environment_state=environment_state,
        environment_reason=environment_reason,
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
    component_path = destination / EXACT_COMPONENTS_NAME
    np.savez_compressed(
        component_path,
        **{
            name: np.ascontiguousarray(np.asarray(value))
            for name, value in components["arrays"].items()
        },
        **{
            _TORCH_RNG_KEY: np.ascontiguousarray(rng["torch"]),
            _RNG_JSON_KEY: np.asarray(
                json.dumps(
                    {
                        "python": rng["python"],
                        "numpy": rng["numpy"],
                        "sampler": rng["sampler"],
                        "environment": rng["environment"],
                        "environment_present": rng["environment_present"],
                        "environment_reason": rng["environment_reason"],
                    },
                    sort_keys=True,
                    ensure_ascii=True,
                )
            ),
            _OPTIMIZER_SCALARS_KEY: np.asarray(
                json.dumps(
                    components["scalars"], sort_keys=True, ensure_ascii=True
                )
            ),
        },
    )
    payload["components"] = {
        "file": EXACT_COMPONENTS_NAME,
        "sha256": sha256_file(component_path),
        "bytes": int(component_path.stat().st_size),
        "optimizer_arrays": sorted(components["arrays"]),
    }
    validate_exact_checkpoint(payload)
    (destination / EXACT_CHECKPOINT_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return destination


@dataclass(frozen=True, eq=False)
class ExactCheckpoint:
    directory: str
    manifest: dict
    state: dict = field(repr=False)
    optimizer_arrays: dict = field(repr=False)
    optimizer_scalars: dict = field(repr=False)
    rng: dict = field(repr=False)

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
        return {
            "directory": self.directory,
            "condition_id": self.condition_id,
            "campaign_seed": self.campaign_seed,
            "training_seed": int(self.manifest["training_seed"]),
            "episodes_completed": int(self.progress["episodes_completed"]),
            "updates_completed": int(self.progress["updates_completed"]),
            "rng_checkpointed": bool(self.manifest["rng"]["checkpointed"]),
            "optimizer_state_checkpointed": bool(
                self.manifest["optimizer"]["state_checkpointed"]
            ),
            "schema_version": EXACT_CHECKPOINT_SCHEMA_VERSION,
        }


def read_exact_checkpoint(
    directory: str | Path,
    *,
    config: TrainingConfig | None = None,
    expected_condition: str | None = None,
) -> ExactCheckpoint:
    directory = Path(directory)
    source = directory / EXACT_CHECKPOINT_NAME
    if not source.is_file():
        raise ArtifactIntegrityError(f"no exact checkpoint at {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactSchemaError(
            f"{source} is not readable JSON: {error}"
        ) from error
    manifest = validate_exact_checkpoint(payload)
    if config is not None:
        if str(manifest["training_config_sha256"]) != config.sha256():
            raise ArtifactIntegrityError(
                "the checkpoint was produced under a different training configuration"
            )
        if str(manifest["protocol"]["sha256"]) != str(config.protocol_sha256):
            raise ArtifactIntegrityError(
                "the checkpoint was produced against a different REV4 document"
            )
    if expected_condition is not None and (
        manifest["condition_id"] != str(expected_condition)
    ):
        raise ArtifactIntegrityError(
            f"{manifest['condition_id']} checkpoint requested as {expected_condition}"
        )

    parameters = directory / str(manifest["parameters"]["file"])
    if not parameters.is_file():
        raise ArtifactIntegrityError(f"the parameter file is missing: {parameters}")
    if sha256_file(parameters) != manifest["parameters"]["sha256"]:
        raise ArtifactIntegrityError(
            "the checkpoint parameter file does not match the manifest hash"
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
            "the stored full-state digest differs from the exact-checkpoint manifest"
        )

    component_path = directory / str(manifest["components"]["file"])
    if not component_path.is_file():
        raise ArtifactIntegrityError(
            f"the checkpoint component file is missing: {component_path}"
        )
    if sha256_file(component_path) != manifest["components"]["sha256"]:
        raise ArtifactIntegrityError(
            "the checkpoint component file does not match the manifest hash"
        )
    if int(component_path.stat().st_size) != int(manifest["components"]["bytes"]):
        raise ArtifactIntegrityError(
            "the checkpoint component file length differs from the manifest"
        )
    with np.load(component_path, allow_pickle=False) as archive:
        raw = {name: np.array(archive[name], copy=True) for name in archive.files}
    expected_arrays = set(manifest["components"]["optimizer_arrays"])
    observed_arrays = {name for name in raw if name.startswith(_OPTIMIZER_PREFIX)}
    if observed_arrays != expected_arrays:
        raise ArtifactIntegrityError(
            "the checkpoint optimizer arrays do not match the manifest: "
            f"stored {sorted(observed_arrays)}, manifest {sorted(expected_arrays)}"
        )
    if _TORCH_RNG_KEY not in raw or _RNG_JSON_KEY not in raw:
        raise ArtifactIntegrityError(
            "the checkpoint component file is missing the RNG state"
        )
    rng_meta = json.loads(str(raw[_RNG_JSON_KEY].item()))
    rng = {
        "python": rng_meta["python"],
        "numpy": rng_meta["numpy"],
        "sampler": rng_meta["sampler"],
        "environment": rng_meta["environment"],
        "environment_present": bool(rng_meta["environment_present"]),
        "environment_reason": rng_meta["environment_reason"],
        "torch": raw[_TORCH_RNG_KEY],
    }
    digests = _rng_digests(rng)
    for name in REQUIRED_RNG_COMPONENTS:
        if str(digests[name]) != str(manifest["rng"][name]["sha256"]):
            raise ArtifactIntegrityError(
                f"the restored {name} RNG state differs from the manifest"
            )
    if rng["environment_present"]:
        if str(digests["environment"]) != str(
            manifest["rng"]["environment"]["sha256"]
        ):
            raise ArtifactIntegrityError(
                "the restored environment RNG state differs from the manifest"
            )
    optimizer_arrays = {
        name: raw[name] for name in sorted(observed_arrays)
    }
    optimizer_scalars = json.loads(str(raw[_OPTIMIZER_SCALARS_KEY].item()))
    if _optimizer_digest(optimizer_arrays, optimizer_scalars) != manifest["digest"][
        "optimizer"
    ]:
        raise ArtifactIntegrityError(
            "the restored optimizer state differs from the manifest digest"
        )
    return ExactCheckpoint(
        directory=str(directory),
        manifest=manifest,
        state=state,
        optimizer_arrays=optimizer_arrays,
        optimizer_scalars=optimizer_scalars,
        rng=rng,
    )


@dataclass(frozen=True, eq=False)
class RestoredExactCheckpoint:
    checkpoint: ExactCheckpoint
    model: Any = field(repr=False)
    state: dict = field(repr=False)
    optimizer_state: dict = field(repr=False)
    python_rng: Any = field(repr=False)
    numpy_rng: Any = field(repr=False)
    torch_rng: Any = field(repr=False)
    sampler_state: dict = field(repr=False)
    environment_state: Any = field(repr=False)
    parameter_digest: str
    state_digest: str
    rng_restored: bool = True
    optimizer_state_restored: bool = True

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

    @property
    def directory(self) -> str:
        return self.checkpoint.directory

    def describe(self) -> dict:
        return {
            **self.checkpoint.describe(),
            "resumed": True,
            "rng_restored": True,
            "optimizer_state_restored": True,
            "environment_state_present": bool(
                self.checkpoint.rng["environment_present"]
            ),
            "limitation": (
                "exactness is demonstrated only by verify_equivalence; the "
                "checkpoint itself makes no claim beyond storing every component"
            ),
        }


def restore_exact_checkpoint(
    directory: str | Path,
    *,
    config: TrainingConfig,
    expected_condition: str | None = None,
    model: Any | None = None,
) -> RestoredExactCheckpoint:
    if not isinstance(config, TrainingConfig):
        raise TrainingConfigError("restore_exact_checkpoint requires a TrainingConfig")
    checkpoint = read_exact_checkpoint(
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
        raise ArtifactIntegrityError(
            f"the checkpoint stores {manifest['model_kind']}, but the supplied "
            f"model is {model_kind(target)}"
        )
    if int(getattr(target, "n_features", -1)) != int(manifest["n_features"]):
        raise ArtifactIntegrityError(
            "the supplied model's feature width differs from the checkpoint"
        )
    load_state(target, checkpoint.state)
    if trainable_digest(target) != manifest["digest"]["trainable"]:
        raise ArtifactIntegrityError(
            "the restored trainable-parameter digest differs from the manifest"
        )
    return RestoredExactCheckpoint(
        checkpoint=checkpoint,
        model=target,
        state=checkpoint.state,
        optimizer_state=_optimizer_state_dict(
            checkpoint.optimizer_arrays, checkpoint.optimizer_scalars
        ),
        python_rng=checkpoint.rng["python"],
        numpy_rng=checkpoint.rng["numpy"],
        torch_rng=checkpoint.rng["torch"],
        sampler_state=dict(checkpoint.rng["sampler"]),
        environment_state=checkpoint.rng["environment"],
        parameter_digest=trainable_digest(target),
        state_digest=state_digest(checkpoint.state),
    )


def apply_exact_restore(
    target_optimizer: Any,
    target_sampler: Any,
    restored: RestoredExactCheckpoint,
    *,
    restore_global_rng: bool = False,
) -> dict:
    """Load optimizer moments and sampler state; optionally restore globals."""
    if not isinstance(restored, RestoredExactCheckpoint):
        raise TrainingError("apply_exact_restore requires a RestoredExactCheckpoint")
    target_optimizer.load_state_dict(restored.optimizer_state)
    target_sampler.bit_generator.state = dict(restored.sampler_state)
    if restore_global_rng:
        random.setstate(_tupleize(restored.python_rng))
        numpy_state = list(restored.numpy_rng)
        numpy_state[1] = np.asarray(numpy_state[1], dtype=np.uint32)
        np.random.set_state(tuple(numpy_state))
        torch.set_rng_state(
            torch.as_tensor(np.asarray(restored.torch_rng), dtype=torch.uint8)
        )
    return {
        "optimizer_state_restored": True,
        "sampler_state_restored": True,
        "python_rng_restored": bool(restore_global_rng),
        "numpy_rng_restored": bool(restore_global_rng),
        "torch_rng_restored": bool(restore_global_rng),
        "environment_state_present": bool(
            restored.checkpoint.rng["environment_present"]
        ),
    }


# ---------------------------------------------------------------------------
# B6 verification
# ---------------------------------------------------------------------------


_EPISODE_FIELDS = (
    "n_decisions",
    "steps",
    "updates_applied",
    "updates_after",
    "loss",
    "mean_return",
    "episode_reward",
    "policy_loss",
    "value_loss",
    "entropy",
    "grad_norm",
    "parameter_digest_after",
)


def verify_equivalence(
    uninterrupted: Any,
    resumed: Any,
    *,
    fields: Sequence[str] = _EPISODE_FIELDS,
) -> dict:
    """Compare an uninterrupted run with an interrupted-and-resumed run."""
    differences: list[str] = []
    for name in ("condition_id", "campaign_seed", "training_seed"):
        if getattr(uninterrupted, name) != getattr(resumed, name):
            differences.append(f"{name} differs")
    if uninterrupted.parameter_digest != resumed.parameter_digest:
        differences.append("final trainable-parameter digest differs")
    if uninterrupted.state_digest != resumed.state_digest:
        differences.append("final full-state digest differs")
    if tuple(uninterrupted.environment_seeds) != tuple(resumed.environment_seeds):
        differences.append("the environment seeds used differ")
    if int(uninterrupted.budget.get("value", -1)) != int(
        resumed.budget.get("value", -1)
    ):
        differences.append("the declared budget differs")

    left = {int(item["episode"]): dict(item) for item in uninterrupted.episodes}
    right = {int(item["episode"]): dict(item) for item in resumed.episodes}
    missing = sorted(set(left) - set(right))
    if missing:
        differences.append(f"the resumed run does not cover episodes {missing}")
    compared = 0
    for index in sorted(set(left) & set(right)):
        compared += 1
        for field in fields:
            if field not in left[index] or field not in right[index]:
                continue
            if left[index][field] != right[index][field]:
                differences.append(
                    f"episode {index} field {field} differs: "
                    f"{left[index][field]!r} vs {right[index][field]!r}"
                )
    return {
        "equivalent": not differences,
        "differences": differences,
        "compared_episodes": compared,
        "compared_fields": [name for name in fields],
        "method": (
            "uninterrupted versus interrupted-and-resumed run at the same "
            "declared budget and seeds"
        ),
        "exactness_claim": "demonstrated" if not differences else "refused",
    }


def assert_resumption_equivalent(uninterrupted: Any, resumed: Any) -> dict:
    report = verify_equivalence(uninterrupted, resumed)
    if not report["equivalent"]:
        raise TrainingError(
            "the resumed run is not equivalent to the uninterrupted run: "
            + "; ".join(report["differences"])
        )
    return report


def describe_exact_checkpoint_interface() -> dict:
    return {
        "schema_version": EXACT_CHECKPOINT_SCHEMA_VERSION,
        "files": [EXACT_CHECKPOINT_NAME, PARAMETERS_NAME, EXACT_COMPONENTS_NAME],
        "origin": EXACT_ORIGIN,
        "stage": EXACT_STAGE,
        "not_a_training_artifact": True,
        "loaded_by_campaign_loader": False,
        "b5": {
            "cadence": "one checkpoint after every completed training episode",
            "retention": "all intermediate checkpoints and the final checkpoint",
        },
        "b6": {
            "components": [
                "model parameters",
                "optimizer state and moments",
                "python random state",
                "numpy global state",
                "torch rng state",
                "sampler generator state",
                "environment rng state when the caller supplies one",
            ],
            "incomplete_claim": "refused by validate_exact_checkpoint",
            "verification": "verify_equivalence / assert_resumption_equivalent",
        },
        "training_execution_authorized": False,
    }


__all__ = [
    "EXACT_CHECKPOINT_NAME",
    "EXACT_CHECKPOINT_SCHEMA_VERSION",
    "EXACT_COMPONENTS_NAME",
    "EXACT_ORIGIN",
    "EXACT_STAGE",
    "ExactCheckpoint",
    "REQUIRED_RNG_COMPONENTS",
    "RestoredExactCheckpoint",
    "apply_exact_restore",
    "assert_resumption_equivalent",
    "build_exact_payload",
    "capture_optimizer_state",
    "capture_rng_state",
    "describe_exact_checkpoint_interface",
    "read_exact_checkpoint",
    "restore_exact_checkpoint",
    "validate_exact_checkpoint",
    "verify_equivalence",
    "write_exact_checkpoint",
]
