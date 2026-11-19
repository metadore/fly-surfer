"""Parameter-state helpers for training artifacts.

A single, explicit conversion between a live model and the byte-level artifact:
named tensors in, named numpy arrays out, and the reverse. Both directions are
shape- and dtype-checked; nothing is coerced silently.

The digests are SHA-256 over ``(name, dtype, shape, bytes)`` in sorted name
order. ``parameter_digest`` from :mod:`readout.linear` covers trainable
parameters only — the quantity the F/Fβ comparison depends on — while
:func:`state_digest` covers every saved array, including Fβ's fixed zero
feature-weight buffer, so a stored zero cannot be changed unnoticed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import hashlib

import numpy as np
import torch

from evaluation.conventional import ConventionalAgent
from readout.linear import BiasOnlyReadout, LinearReadout, parameter_digest

from .errors import ArtifactIntegrityError, ArtifactSchemaError

MODEL_KINDS = {
    "LinearReadout": "linear_readout",
    "BiasOnlyReadout": "bias_only_readout",
    "ConventionalAgent": "conventional_actor_critic",
}


def model_kind(model: Any) -> str:
    try:
        return MODEL_KINDS[type(model).__name__]
    except KeyError:
        raise ArtifactSchemaError(
            f"{type(model).__name__} is not a declared trainable model; expected "
            "LinearReadout, BiasOnlyReadout or ConventionalAgent"
        ) from None


def model_state(model: Any) -> dict[str, np.ndarray]:
    """The artifact surface of a model: parameters plus fixed buffers."""
    if isinstance(model, (LinearReadout, BiasOnlyReadout, ConventionalAgent)):
        state = {
            str(name): np.array(value, dtype=value.dtype, copy=True)
            for name, value in model.numpy_state().items()
        }
    else:
        raise ArtifactSchemaError(
            f"{type(model).__name__} exposes no declared parameter state"
        )
    if not state:
        raise ArtifactSchemaError("the model has no parameters to store")
    for name, value in state.items():
        if not np.all(np.isfinite(value)):
            raise ArtifactIntegrityError(
                f"parameter {name!r} contains non-finite values"
            )
    return state


def model_architecture(model: Any) -> dict:
    """Architecture fields needed to rebuild the model before loading state."""
    kind = model_kind(model)
    if isinstance(model, LinearReadout):
        return {
            "kind": kind,
            "n_features": int(model.n_features),
            "init_std": float(model.init_std),
            "seed": int(model.seed),
        }
    if isinstance(model, BiasOnlyReadout):
        return {
            "kind": kind,
            "n_features": int(model.n_features),
            "seed": int(model.seed),
        }
    config = model.config
    return {
        "kind": kind,
        "n_features": int(model.n_features),
        "actions": list(model.describe()["actions"]),
        "e_learner": config.as_dict(),
    }


def state_digest(state: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        array = np.ascontiguousarray(np.asarray(state[name]))
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("utf-8"))
        digest.update(str(array.shape).encode("utf-8"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def trainable_digest(model: Any) -> str:
    if isinstance(model, ConventionalAgent):
        return model.parameter_digest()
    return parameter_digest(model)


def parameter_shapes(state: Mapping[str, np.ndarray]) -> dict[str, list[int]]:
    return {name: [int(size) for size in np.asarray(state[name]).shape] for name in sorted(state)}


def parameter_dtypes(state: Mapping[str, np.ndarray]) -> dict[str, str]:
    return {name: str(np.asarray(state[name]).dtype) for name in sorted(state)}


def load_state(model: Any, state: Mapping[str, np.ndarray]) -> None:
    """Copy saved arrays into a freshly built model, refusing any mismatch."""
    module = model.network if isinstance(model, ConventionalAgent) else model
    parameters = dict(module.named_parameters())
    buffers = dict(module.named_buffers())
    targets = {**parameters, **buffers}
    missing = sorted(set(targets) - set(state))
    extra = sorted(set(state) - set(targets))
    if missing or extra:
        raise ArtifactIntegrityError(
            "the stored parameter set does not match the model: "
            f"missing {missing}, unexpected {extra}"
        )
    with torch.no_grad():
        for name in sorted(targets):
            array = np.asarray(state[name])
            target = targets[name]
            if tuple(array.shape) != tuple(target.shape):
                raise ArtifactIntegrityError(
                    f"parameter {name!r} has shape {tuple(array.shape)}; the "
                    f"model expects {tuple(target.shape)}"
                )
            if not np.all(np.isfinite(array)):
                raise ArtifactIntegrityError(
                    f"parameter {name!r} contains non-finite values"
                )
            target.copy_(torch.as_tensor(array, dtype=target.dtype))


def save_state_npz(path: str | Path, state: Mapping[str, np.ndarray]) -> Path:
    destination = Path(path)
    if destination.suffix != ".npz":
        raise ArtifactSchemaError("parameter files must use the .npz suffix")
    if destination.exists():
        raise ArtifactSchemaError(
            f"{destination} already exists; artifacts are never overwritten"
        )
    np.savez_compressed(
        destination,
        **{name: np.ascontiguousarray(np.asarray(state[name])) for name in sorted(state)},
    )
    return destination


def load_state_npz(path: str | Path) -> dict[str, np.ndarray]:
    source = Path(path)
    if not source.is_file():
        raise ArtifactIntegrityError(f"the parameter file is missing: {source}")
    try:
        with np.load(source, allow_pickle=False) as data:
            return {name: np.array(data[name], copy=True) for name in data.files}
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError(
            f"{source} is not a readable, pickle-free npz archive: {error}"
        ) from error


def assert_state_keys(
    state: Mapping[str, np.ndarray],
    *,
    names: Iterable[str],
    shapes: Mapping[str, list[int]],
    dtypes: Mapping[str, str],
) -> None:
    expected = sorted(str(name) for name in names)
    actual = sorted(state)
    if actual != expected:
        raise ArtifactIntegrityError(
            "the stored parameter names do not match the manifest: "
            f"stored {actual}, manifest {expected}"
        )
    for name in expected:
        array = np.asarray(state[name])
        if [int(size) for size in array.shape] != [int(size) for size in shapes[name]]:
            raise ArtifactIntegrityError(
                f"parameter {name!r} has shape {list(array.shape)}; the manifest "
                f"records {shapes[name]}"
            )
        if str(array.dtype) != str(dtypes[name]):
            raise ArtifactIntegrityError(
                f"parameter {name!r} has dtype {array.dtype}; the manifest "
                f"records {dtypes[name]}"
            )


__all__ = [
    "MODEL_KINDS",
    "assert_state_keys",
    "load_state",
    "load_state_npz",
    "model_architecture",
    "model_kind",
    "model_state",
    "parameter_dtypes",
    "parameter_shapes",
    "save_state_npz",
    "state_digest",
    "trainable_digest",
]
