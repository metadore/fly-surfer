"""Load verified artifacts into the existing campaign factory's provider.

The loader is the only bridge between stored artifacts and
:class:`experiments.phase_8.campaign.factory.TrainingArtifacts`. It:

* discovers artifacts by directory, never by substituting one condition for
  another;
* fully re-verifies each artifact (manifest schema, file SHA-256, shapes,
  digests, condition kind and width) before exposing a model;
* requires ``origin = "trained"`` for campaign use. Synthetic fixtures are
  readable only with an explicit ``allow_synthetic_fixtures=True`` and
  ``require_trained=False``, which exists for tests and never for a campaign;
* checks the F/Fβ pair shares its training run;
* refuses a missing artifact for any required condition and seed.

:func:`prepare_campaign_artifacts` is the gated entry point. It refuses while
``design.n_seeds_selected`` is null, before touching the artifact root. The
lower-level :func:`load_training_artifacts` takes explicit campaign seeds and
is used by focused tests; it still performs every integrity and compatibility
check.

Loading performs no training, runs no episode and authorises no campaign.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from readout.features import MotorFeatureSpec

from ..campaign.factory import CampaignFactory, FactoryError, TrainingArtifacts
from .artifacts import Artifact, read_artifact, read_manifest
from .config import (
    AGENT_CONDITIONS,
    READOUT_CONDITIONS,
    TRAINABLE_CONDITIONS,
    TrainingConfig,
    validate_training_config,
)
from .errors import (
    ArtifactCompatibilityError,
    TrainingConfigError,
    TrainingError,
)
from .gate import assert_design_resolved
from .validation import EXPECTED_FEATURES, check_readout_pair

DEFAULT_REQUIRED = ("F", "F_beta", "E")


@dataclass(frozen=True, eq=False)
class LoadedArtifacts:
    training: TrainingArtifacts
    artifacts: dict
    manifests: dict
    report: dict

    def describe(self) -> dict:
        return dict(self.report)


def discover_artifact_directories(root: str | Path) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.glob("*/*")
        if path.is_dir() and (path / "manifest.json").is_file()
    )


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrainingConfigError(f"{name} must be an integer")
    if int(value) < 0:
        raise TrainingConfigError(f"{name} cannot be negative")
    return int(value)


def load_training_artifacts(
    root: str | Path,
    *,
    config: TrainingConfig,
    campaign_seeds: Sequence[int],
    conditions: Sequence[str] = DEFAULT_REQUIRED,
    pairing: Mapping[tuple[str, int], int] | None = None,
    require_trained: bool = True,
    allow_synthetic_fixtures: bool = False,
    require_complete: bool = True,
    include_exploratory: bool = True,
) -> LoadedArtifacts:
    """Read, verify and package every artifact needed by the factory."""
    if require_trained and allow_synthetic_fixtures:
        raise TrainingConfigError(
            "allow_synthetic_fixtures applies only when require_trained=False; "
            "a campaign may never load a fixture as a trained artifact"
        )
    seeds = tuple(_int(seed, "campaign_seed") for seed in campaign_seeds)
    if not seeds:
        raise TrainingConfigError("campaign_seeds cannot be empty")
    undeclared = sorted(set(seeds) - set(config.campaign_seeds))
    if undeclared:
        raise TrainingConfigError(
            f"campaign seeds {undeclared} are not declared in seeds.campaign"
        )

    required = tuple(str(condition) for condition in conditions)
    unknown = sorted(set(required) - set(TRAINABLE_CONDITIONS))
    if unknown:
        raise TrainingConfigError(f"unknown required conditions: {unknown}")
    allowed = set(required)
    if include_exploratory:
        allowed.update(AGENT_CONDITIONS)

    artifacts: dict[tuple[str, int], Artifact] = {}
    ignored: list[str] = []
    for directory in discover_artifact_directories(root):
        manifest = read_manifest(directory)
        key = (str(manifest["condition_id"]), int(manifest["campaign_seed"]))
        if key[1] not in seeds:
            ignored.append(f"{key[0]}:{key[1]}")
            continue
        if key[0] not in allowed:
            raise ArtifactCompatibilityError(
                f"{key[0]} has no artifact role in this campaign; found "
                f"{directory} (F-init and other untrained arms never carry one)"
            )
        if key in artifacts:
            raise ArtifactCompatibilityError(
                f"two artifacts claim {key[0]} campaign seed {key[1]}: "
                f"{artifacts[key].directory} and {directory}"
            )
        artifact = read_artifact(directory, config=config, expected_condition=key[0])
        origin = str(artifact.manifest["origin"])
        stage = str(artifact.manifest["stage"])
        if require_trained:
            if origin != "trained" or stage != "trained":
                raise ArtifactCompatibilityError(
                    f"{key[0]}:{key[1]} is origin={origin!r} stage={stage!r}; a "
                    "campaign requires a trained artifact and never substitutes "
                    "initialized or synthetic state"
                )
        elif origin == "synthetic_fixture" and not allow_synthetic_fixtures:
            raise ArtifactCompatibilityError(
                f"{key[0]}:{key[1]} is a synthetic fixture; pass "
                "allow_synthetic_fixtures=True only in a non-campaign test"
            )
        if int(artifact.manifest["training_seed"]) not in set(config.training_seeds):
            raise ArtifactCompatibilityError(
                f"{key[0]}:{key[1]} records training seed "
                f"{artifact.manifest['training_seed']}, which is not declared in "
                "seeds.training"
            )
        if pairing is not None:
            expected = pairing.get(key)
            if expected is None:
                raise ArtifactCompatibilityError(
                    f"the pairing does not declare {key[0]}:{key[1]}"
                )
            if int(expected) != int(artifact.manifest["training_seed"]):
                raise ArtifactCompatibilityError(
                    f"{key[0]}:{key[1]} was trained at seed "
                    f"{artifact.manifest['training_seed']}; the pairing declares "
                    f"{expected}"
                )
        artifacts[key] = artifact

    missing = [
        f"{condition}:{seed}"
        for seed in seeds
        for condition in required
        if (condition, seed) not in artifacts
    ]
    if require_complete and missing:
        raise ArtifactCompatibilityError(
            f"missing training artifacts: {missing}"
        )

    pairs: dict[int, dict] = {}
    for seed in seeds:
        forward = artifacts.get(("F", seed))
        beta = artifacts.get(("F_beta", seed))
        if forward is not None and beta is not None:
            pairs[seed] = check_readout_pair(forward.manifest, beta.manifest)

    readouts = {
        key: artifact.model
        for key, artifact in artifacts.items()
        if key[0] in READOUT_CONDITIONS
    }
    agents = {
        key: artifact.model
        for key, artifact in artifacts.items()
        if key[0] in AGENT_CONDITIONS
    }
    origins = {str(artifact.manifest["origin"]) for artifact in artifacts.values()}
    provenance = (
        "trained-artifacts" if origins == {"trained"} else "synthetic-fixture-artifacts"
    )
    training = TrainingArtifacts(
        readouts=readouts, agents=agents, provenance=provenance
    )

    report = {
        "root": str(Path(root)),
        "campaign_seeds": list(seeds),
        "required_conditions": list(required),
        "loaded": sorted(f"{key[0]}:{key[1]}" for key in artifacts),
        "ignored_seeds": sorted(ignored),
        "origins": sorted(origins),
        "require_trained": bool(require_trained),
        "synthetic_allowed": bool(allow_synthetic_fixtures),
        "complete": not missing,
        "missing": missing,
        "readout_pairs": {str(seed): pair for seed, pair in sorted(pairs.items())},
        "training_config_sha256": config.sha256(),
        "provenance": provenance,
        "training_performed_here": False,
        "execution_authorized": False,
    }
    return LoadedArtifacts(
        training=training,
        artifacts=artifacts,
        manifests={key: artifact.manifest for key, artifact in artifacts.items()},
        report=report,
    )


def prepare_campaign_artifacts(
    phase8_config: Any,
    root: str | Path,
    *,
    pairing: Mapping[tuple[str, int], int],
) -> LoadedArtifacts:
    """Gated campaign-preparation entry point.

    The unresolved-design refusal happens before configuration validation and
    before the artifact root is read.
    """
    assert_design_resolved(phase8_config.campaign)
    config = validate_training_config(phase8_config)
    active = list(phase8_config.campaign.active_seeds())
    return load_training_artifacts(
        root,
        config=config,
        campaign_seeds=active,
        pairing=pairing,
        require_trained=True,
    )


def check_factory_compatibility(
    loaded: LoadedArtifacts, factory: CampaignFactory
) -> dict:
    """Ask the real factory for every loaded key and verify widths.

    No component is built, no graph is read and no episode runs: this exercises
    ``factory.training`` only.
    """
    if not isinstance(factory, CampaignFactory):
        raise TrainingError("factory compatibility requires a CampaignFactory")
    readout_width = int(MotorFeatureSpec().n_features)
    checks: list[dict] = []
    for (condition_id, seed), artifact in sorted(loaded.artifacts.items()):
        try:
            if condition_id in READOUT_CONDITIONS:
                model = factory.training.readout(condition_id, seed)
                width = int(getattr(model, "n_features", -1))
                expected = readout_width
            else:
                model = factory.training.agent(condition_id, seed)
                width = int(getattr(model, "n_features", -1))
                expected = EXPECTED_FEATURES[condition_id]
        except FactoryError as error:
            raise ArtifactCompatibilityError(str(error)) from error
        if model is not artifact.model:
            raise ArtifactCompatibilityError(
                f"the factory returned a different {condition_id}:{seed} object"
            )
        if width != expected:
            raise ArtifactCompatibilityError(
                f"{condition_id}:{seed} carries {width} features; the factory "
                f"declares {expected}"
            )
        checks.append(
            {
                "condition_id": condition_id,
                "campaign_seed": seed,
                "n_features": width,
                "expected_features": expected,
                "same_object": True,
            }
        )
    return {
        "factory_training_provenance": factory.training.provenance,
        "checked": checks,
        "training_performed_here": False,
    }


__all__ = [
    "DEFAULT_REQUIRED",
    "LoadedArtifacts",
    "check_factory_compatibility",
    "discover_artifact_directories",
    "load_training_artifacts",
    "prepare_campaign_artifacts",
]
