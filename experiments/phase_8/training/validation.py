"""Schema, integrity and condition-compatibility checks for artifacts.

Three layers, applied in this order when an artifact is read:

1. :func:`validate_manifest` — the JSON manifest is complete, typed and
   internally consistent. The embedded training configuration is re-hashed,
   so the recorded configuration cannot drift from the hash it claims.
2. :func:`assert_condition_compatibility` — the rebuilt model is the kind the
   condition declares (F linear and state-dependent, Fβ bias-only and
   provably state-independent, E/E-full conventional actor-critic) and its
   width is the declared 3/7/14 (motor populations / E-matched / E-full).
3. :func:`check_readout_pair` — F and Fβ artifacts at one campaign seed came
   from the same training run and therefore differ only in their readout
   definition, as REV4 §3.6.2 requires.

The checks are structural. They say nothing about whether a model learned
anything, and they do not authorise a campaign.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Mapping

import numpy as np

from evaluation.conventional import ConventionalAgent
from readout.features import MotorFeatureSpec
from readout.linear import BiasOnlyReadout, LinearReadout

from .config import (
    AGENT_CONFIG_FIELDS,
    TRAINABLE_CONDITIONS,
    canonical_json,
    sha256_text,
)
from .errors import ArtifactCompatibilityError, ArtifactSchemaError, TrainingConfigError
from .state import model_kind

ARTIFACT_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
PARAMETERS_NAME = "parameters.npz"
ORIGINS = ("trained", "synthetic_fixture")
STAGES = ("initialized", "trained")

#: Declared widths: four-way motor readout (REV4 §3.6 row 7), seven sensory
#: features for E-matched and fourteen for the exploratory E-full (§3.5 row 1).
EXPECTED_FEATURES = {
    "F": MotorFeatureSpec().n_features,
    "F_beta": MotorFeatureSpec().n_features,
    "E": 7,
    "E_full": 14,
}

MODEL_KIND_BY_CONDITION = {
    "F": "linear_readout",
    "F_beta": "bias_only_readout",
    "E": "conventional_actor_critic",
    "E_full": "conventional_actor_critic",
}

REQUIRED_KEYS = {
    "schema_version",
    "condition_id",
    "campaign_seed",
    "training_seed",
    "init_seed",
    "master_seed",
    "training_environment_seed",
    "n_features",
    "model_kind",
    "architecture",
    "origin",
    "stage",
    "training_config_sha256",
    "training_config",
    "protocol",
    "campaign_config",
    "parameter_names",
    "parameter_shapes",
    "parameter_dtypes",
    "digest",
    "parameters",
    "created",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _fail(message: str) -> None:
    raise ArtifactSchemaError(message)


def _mapping(value: Any, name: str, keys: set | None = None) -> Mapping:
    if not isinstance(value, Mapping):
        _fail(f"{name} must be a mapping")
    if keys is not None:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        if missing:
            _fail(f"{name} is missing keys: {missing}")
        if extra:
            _fail(f"{name} has unknown keys: {extra}")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{name} must be a non-empty string")
    return value


def _int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{name} must be an integer")
    if int(value) < minimum:
        _fail(f"{name} must be >= {minimum}")
    return int(value)


def _sha(value: Any, name: str) -> str:
    text = _string(value, name)
    if not _SHA256.match(text):
        _fail(f"{name} must be a 64-character lowercase SHA-256 hex digest")
    return text


def _architecture(payload: Any, condition_id: str) -> Mapping:
    arch = _mapping(payload, "architecture")
    kind = MODEL_KIND_BY_CONDITION[condition_id]
    if arch.get("kind") != kind:
        _fail(
            f"architecture.kind must be {kind!r} for {condition_id}, got "
            f"{arch.get('kind')!r}"
        )
    if condition_id in ("F", "F_beta"):
        _mapping(arch, "architecture", {"kind", "n_features", "seed", *(
            ("init_std",) if condition_id == "F" else ()
        )})
        _int(arch["n_features"], "architecture.n_features", minimum=1)
        _int(arch["seed"], "architecture.seed")
        if condition_id == "F":
            value = arch["init_std"]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                _fail("architecture.init_std must be a number")
            if not np.isfinite(float(value)) or float(value) < 0:
                _fail("architecture.init_std must be finite and non-negative")
    else:
        _mapping(arch, "architecture", {
            "kind", "n_features", "actions", "e_learner"
        })
        _int(arch["n_features"], "architecture.n_features", minimum=1)
        actions = arch["actions"]
        if not isinstance(actions, list) or len(actions) != 4:
            _fail("architecture.actions must list the four declared actions")
        learner = _mapping(arch["e_learner"], "architecture.e_learner")
        missing = [name for name in AGENT_CONFIG_FIELDS if name not in learner]
        if missing:
            _fail(f"architecture.e_learner is missing {missing}")
    return arch


def validate_manifest(payload: Any) -> Mapping:
    """Strict schema validation; unknown or missing keys are errors."""
    manifest = _mapping(payload, "manifest", REQUIRED_KEYS)

    if _int(manifest["schema_version"], "schema_version", minimum=1) != ARTIFACT_SCHEMA_VERSION:
        _fail(
            f"unsupported artifact schema_version {manifest['schema_version']}; "
            f"this harness reads {ARTIFACT_SCHEMA_VERSION}"
        )

    condition_id = _string(manifest["condition_id"], "condition_id")
    if condition_id not in TRAINABLE_CONDITIONS:
        _fail(
            f"{condition_id!r} has no training artifact; trainable conditions are "
            f"{list(TRAINABLE_CONDITIONS)}"
        )

    campaign_seed = _int(manifest["campaign_seed"], "campaign_seed")
    training_seed = _int(manifest["training_seed"], "training_seed")
    if campaign_seed == training_seed:
        _fail("campaign_seed and training_seed must be disjoint")
    _int(manifest["init_seed"], "init_seed")
    _int(manifest["master_seed"], "master_seed")
    _int(manifest["training_environment_seed"], "training_environment_seed")

    expected_width = EXPECTED_FEATURES[condition_id]
    width = _int(manifest["n_features"], "n_features", minimum=1)
    if width != expected_width:
        _fail(
            f"{condition_id} artifacts must carry {expected_width} features; "
            f"the manifest declares {width}"
        )

    if _string(manifest["model_kind"], "model_kind") != MODEL_KIND_BY_CONDITION[condition_id]:
        _fail(
            f"model_kind must be {MODEL_KIND_BY_CONDITION[condition_id]!r} for "
            f"{condition_id}"
        )
    _architecture(manifest["architecture"], condition_id)

    origin = _string(manifest["origin"], "origin")
    stage = _string(manifest["stage"], "stage")
    if origin not in ORIGINS:
        _fail(f"origin must be one of {ORIGINS}")
    if stage not in STAGES:
        _fail(f"stage must be one of {STAGES}")
    if origin == "synthetic_fixture" and stage != "initialized":
        _fail("a synthetic fixture is initialized state, never a trained artifact")
    if origin == "trained" and stage != "trained":
        _fail("a trained artifact must record stage='trained'")

    training_config = _mapping(manifest["training_config"], "training_config")
    config_hash = _sha(manifest["training_config_sha256"], "training_config_sha256")
    if sha256_text(canonical_json(training_config)) != config_hash:
        _fail("training_config_sha256 does not match the embedded training configuration")

    protocol = _mapping(manifest["protocol"], "protocol", {
        "id", "sha256", "path", "matches_expected",
    })
    _string(protocol["id"], "protocol.id")
    _sha(protocol["sha256"], "protocol.sha256")
    _string(protocol["path"], "protocol.path")
    if protocol["matches_expected"] is not True:
        _fail("the artifact was not built against the certified REV4 document")

    campaign = _mapping(manifest["campaign_config"], "campaign_config", {
        "path", "sha256",
    })
    _string(campaign["path"], "campaign_config.path")
    _sha(campaign["sha256"], "campaign_config.sha256")

    names = manifest["parameter_names"]
    if not isinstance(names, list) or not names:
        _fail("parameter_names must be a non-empty list")
    if any(not isinstance(name, str) or not name for name in names):
        _fail("parameter_names contains an invalid entry")
    if len(set(names)) != len(names):
        _fail("parameter_names contains duplicates")
    expected_names = sorted(names)
    shapes = _mapping(manifest["parameter_shapes"], "parameter_shapes")
    dtypes = _mapping(manifest["parameter_dtypes"], "parameter_dtypes")
    if sorted(shapes) != expected_names:
        _fail("parameter_shapes does not cover exactly the declared parameter names")
    if sorted(dtypes) != expected_names:
        _fail("parameter_dtypes does not cover exactly the declared parameter names")
    for name in expected_names:
        shape = shapes[name]
        if not isinstance(shape, list) or any(
            isinstance(size, bool) or not isinstance(size, int) or size < 0
            for size in shape
        ):
            _fail(f"parameter_shapes[{name!r}] must be a list of non-negative integers")
        _string(dtypes[name], f"parameter_dtypes[{name!r}]")

    digest = _mapping(manifest["digest"], "digest", {"trainable", "state"})
    _sha(digest["trainable"], "digest.trainable")
    _sha(digest["state"], "digest.state")

    parameters = _mapping(manifest["parameters"], "parameters", {
        "file", "sha256", "bytes",
    })
    if _string(parameters["file"], "parameters.file") != PARAMETERS_NAME:
        _fail(f"parameters.file must be {PARAMETERS_NAME!r}")
    _sha(parameters["sha256"], "parameters.sha256")
    _int(parameters["bytes"], "parameters.bytes", minimum=1)

    created = _mapping(manifest["created"], "created", {
        "utc", "tool", "python", "numpy", "torch",
    })
    for name in ("utc", "tool", "python", "numpy", "torch"):
        _string(created[name], f"created.{name}")

    return manifest


def assert_condition_compatibility(
    manifest: Mapping, model: Any, state: Mapping[str, np.ndarray]
) -> dict:
    """The rebuilt model must be exactly the condition's declared kind."""
    condition_id = str(manifest["condition_id"])
    required = int(manifest["n_features"])
    width = int(getattr(model, "n_features", -1))
    if width != required:
        raise ArtifactCompatibilityError(
            f"the rebuilt model has {width} features; the {condition_id} artifact "
            f"declares {required}"
        )
    if model_kind(model) != MODEL_KIND_BY_CONDITION[condition_id]:
        raise ArtifactCompatibilityError(
            f"{condition_id} must load as {MODEL_KIND_BY_CONDITION[condition_id]}"
        )

    checks: dict[str, Any] = {"condition_id": condition_id, "n_features": width}
    if condition_id == "F":
        if not isinstance(model, LinearReadout) or isinstance(model, BiasOnlyReadout):
            raise ArtifactCompatibilityError(
                "F must load as the state-dependent linear readout"
            )
        if bool(model.state_independent):
            raise ArtifactCompatibilityError(
                "F cannot be the bias-only control; that is Fβ"
            )
        checks["state_dependent"] = True
    elif condition_id == "F_beta":
        if not isinstance(model, BiasOnlyReadout):
            raise ArtifactCompatibilityError(
                "Fβ must load as BiasOnlyReadout; the linear readout is state-dependent"
            )
        checks.update(model.assert_state_independent())
        trainable = [name for name, _ in model.named_parameters()]
        if trainable != ["bias"]:
            raise ArtifactCompatibilityError(
                f"Fβ's trainable parameters must be exactly ['bias'], got {trainable}"
            )
        fixed = np.asarray(state["fixed_feature_weights"])
        if np.count_nonzero(fixed) != 0:
            raise ArtifactCompatibilityError(
                "Fβ's fixed feature weights are not exactly zero"
            )
        zero = np.zeros((1, width), dtype=np.float32)
        saturated = np.full((1, width), 1e6, dtype=np.float32)
        if not np.array_equal(model.logits(zero), model.logits(saturated)):
            raise ArtifactCompatibilityError(
                "the bias-only readout emitted different logits for different "
                "motor activity"
            )
        checks["constant_over_feature_vectors"] = True
        checks["trainable_parameters"] = trainable
    else:
        if not isinstance(model, ConventionalAgent):
            raise ArtifactCompatibilityError(
                f"{condition_id} must load as the conventional actor-critic"
            )
        expected = EXPECTED_FEATURES[condition_id]
        if width != expected:
            raise ArtifactCompatibilityError(
                f"{condition_id} must carry {expected} sensory features, got {width}"
            )
        checks["agent_updates"] = int(model.updates)
    return checks


def check_readout_pair(forward: Mapping, beta: Mapping) -> dict:
    """F and Fβ at one campaign seed must share the declared training run."""
    if forward["condition_id"] != "F" or beta["condition_id"] != "F_beta":
        raise ArtifactCompatibilityError(
            "the readout pair must be (F, F_beta), got "
            f"({forward['condition_id']}, {beta['condition_id']})"
        )
    for field in ("campaign_seed", "training_seed", "master_seed"):
        if int(forward[field]) != int(beta[field]):
            raise ArtifactCompatibilityError(
                f"F and Fβ differ on {field}: {forward[field]} vs {beta[field]}"
            )
    return {
        "campaign_seed": int(forward["campaign_seed"]),
        "training_seed": int(forward["training_seed"]),
        "paired": True,
    }


def assert_expected_config(manifest: Mapping, config: Any) -> None:
    """The artifact must have been produced under this exact configuration."""
    if str(manifest["training_config_sha256"]) != config.sha256():
        raise ArtifactCompatibilityError(
            "the artifact was produced under a different training configuration"
        )
    protocol = manifest["protocol"]
    if str(protocol["sha256"]) != str(config.protocol_sha256):
        raise ArtifactCompatibilityError(
            "the artifact was produced against a different REV4 document"
        )
    campaign = manifest["campaign_config"]
    if str(campaign["sha256"]) != str(config.campaign_sha256):
        raise ArtifactCompatibilityError(
            "the artifact was produced from a different campaign configuration"
        )
    if int(manifest["master_seed"]) != int(config.master_seed):
        raise TrainingConfigError(
            "the artifact was produced under a different master seed"
        )


def created_record(tool: str) -> dict:
    from datetime import datetime, timezone
    from importlib import metadata

    def version(name: str) -> str:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:  # pragma: no cover - pinned deps
            return "absent"

    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool,
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "torch": version("torch"),
    }


__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "EXPECTED_FEATURES",
    "MANIFEST_NAME",
    "MODEL_KIND_BY_CONDITION",
    "ORIGINS",
    "PARAMETERS_NAME",
    "REQUIRED_KEYS",
    "STAGES",
    "assert_condition_compatibility",
    "assert_expected_config",
    "check_readout_pair",
    "created_record",
    "validate_manifest",
]
