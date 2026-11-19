"""Failure taxonomy for the Phase 8 training-artifact stage.

Each error names a distinct refusal so a caller can report *why* the pipeline
stopped rather than collapsing every problem into one generic exception:

* :class:`TrainingConfigError` — the declared training configuration does not
  match REV4 or the code constants it pins;
* :class:`DesignUnresolvedError` — ``design.n_seeds_selected`` is still null,
  so no training artifact may be generated and no campaign prepared;
* :class:`TrainingNotAuthorized` — REV4 §12 is unapproved and U1–U18 remain
  ``PROPOSED``; no training run may start;
* :class:`ArtifactSchemaError` — a manifest is malformed, incomplete or
  internally inconsistent;
* :class:`ArtifactIntegrityError` — a stored parameter file, digest or shape
  does not match the manifest;
* :class:`ArtifactCompatibilityError` — an artifact exists but does not fit
  the condition, seed pairing or campaign factory that asked for it.
"""

from __future__ import annotations


class TrainingError(RuntimeError):
    """Base class for every training-artifact failure."""


class TrainingConfigError(TrainingError, ValueError):
    """The training configuration disagrees with its declaration."""


class DesignUnresolvedError(TrainingConfigError):
    """``design.n_seeds_selected`` is null; no design exists yet."""


class TrainingNotAuthorized(TrainingError):
    """No training run may start on the present approval state."""


class ArtifactSchemaError(TrainingError, ValueError):
    """A training-artifact manifest violates the declared schema."""


class ArtifactIntegrityError(TrainingError):
    """Stored bytes, digests or shapes do not match the manifest."""


class ArtifactCompatibilityError(TrainingError):
    """An artifact does not fit the condition, seed or factory that requested it."""


__all__ = [
    "ArtifactCompatibilityError",
    "ArtifactIntegrityError",
    "ArtifactSchemaError",
    "DesignUnresolvedError",
    "TrainingConfigError",
    "TrainingError",
    "TrainingNotAuthorized",
]
