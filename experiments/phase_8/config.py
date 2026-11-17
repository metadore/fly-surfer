"""Strict loaders for the Phase 8 configuration.

Three files under ``configs/phase_8/`` are the only source of Phase 8
constants (REV3 §8.1): ``environment.yaml`` (§6.1), ``campaign.yaml`` (design,
seeds, statistics, budget) and ``conditions.yaml`` (per-condition declarations).
This module validates them and records their SHA-256 so every episode row and
the run manifest can be traced to the exact configuration that produced it.

The protocol is **not approved** (REV3 §10.0, §12). Loading a configuration
does not authorise execution; :func:`memory_preflight` enforces the §9.3 gate
and :meth:`CampaignConfig.active_seeds` refuses to resolve a design whose pilot
decision (``n_seeds_selected``) is still null.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from brain.banc_graph import sha256_file

from .seeds import CONDITION_IDS, MASTER_SEED, describe_derivation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs" / "phase_8"

ENVIRONMENT_FILE = "environment.yaml"
CAMPAIGN_FILE = "campaign.yaml"
CONDITIONS_FILE = "conditions.yaml"

TRAINABLE_TARGETS = ("none", "synapses", "readout", "policy")


class ConfigError(ValueError):
    """A Phase 8 configuration file is missing, malformed or inconsistent."""


class MemoryGateError(RuntimeError):
    """Free physical memory is below the declared Phase 8 gate (REV3 §9.3)."""


# ---------------------------------------------------------------------------
# scalar validators
# ---------------------------------------------------------------------------


def _int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, (int,)):
        raise ConfigError(f"{name} must be an integer, got {value!r}")
    number = int(value)
    if minimum is not None and number < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {number}")
    return number


def _float(
    value: Any,
    name: str,
    *,
    positive: bool = False,
    unit_interval: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ConfigError(f"{name} must be finite, got {value!r}")
    if positive and number <= 0:
        raise ConfigError(f"{name} must be positive, got {number}")
    if unit_interval and not 0.0 <= number <= 1.0:
        raise ConfigError(f"{name} must lie in [0, 1], got {number}")
    return number


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _sequence(value: Any, name: str) -> list:
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{name} must be a list")
    return list(value)


def _unknown_keys(payload: Mapping[str, Any], allowed: set, name: str) -> None:
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ConfigError(f"{name} has unknown keys: {extra}")


def _required(payload: Mapping[str, Any], keys: set, name: str) -> None:
    missing = sorted(set(keys) - set(payload))
    if missing:
        raise ConfigError(f"{name} is missing required keys: {missing}")


def load_yaml(path: str | Path) -> dict:
    """Read one YAML mapping; a missing file or a non-mapping is an error."""
    source = Path(path)
    if not source.is_file():
        raise ConfigError(f"configuration file not found: {source}")
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ConfigError(f"{source} must contain a YAML mapping")
    return payload


def _record(source: Path) -> dict[str, str]:
    return {
        "path": _relative(source),
        "sha256": sha256_file(source),
    }


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


# ---------------------------------------------------------------------------
# environment.yaml
# ---------------------------------------------------------------------------

_ENVIRONMENT_KEYS = {
    "schema_version",
    "name",
    "max_steps",
    "initial_speed",
    "max_speed",
    "coin_reward",
    "collision_penalty",
    "survival_reward",
    "obstacle_reward",
    "distance_horizon",
    "render_mode",
    "observation_schema_version",
    "units",
    "reward_classification",
}


@dataclass(frozen=True)
class EnvironmentConfig:
    """The single controlled-game configuration (REV3 §6.1)."""

    schema_version: int
    max_steps: int
    initial_speed: float
    max_speed: float
    coin_reward: float
    collision_penalty: float
    survival_reward: float
    obstacle_reward: float
    distance_horizon: float
    render_mode: str | None
    observation_schema_version: int
    path: str
    sha256: str

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "max_steps": self.max_steps,
            "initial_speed": self.initial_speed,
            "max_speed": self.max_speed,
            "coin_reward": self.coin_reward,
            "collision_penalty": self.collision_penalty,
            "survival_reward": self.survival_reward,
            "obstacle_reward": self.obstacle_reward,
            "distance_horizon": self.distance_horizon,
            "render_mode": self.render_mode,
            "observation_schema_version": self.observation_schema_version,
            "path": self.path,
            "sha256": self.sha256,
        }


def load_environment_config(path: str | Path | None = None) -> EnvironmentConfig:
    source = Path(path) if path is not None else CONFIG_DIR / ENVIRONMENT_FILE
    raw = load_yaml(source)
    _unknown_keys(raw, _ENVIRONMENT_KEYS, "environment configuration")
    _required(raw, _ENVIRONMENT_KEYS - {"schema_version", "name", "units",
                                        "reward_classification"}, "environment configuration")
    if "schema_version" not in raw:
        raise ConfigError("environment configuration is missing schema_version")

    schema_version = _int(raw["schema_version"], "environment.schema_version", minimum=1)
    if schema_version != 1:
        raise ConfigError(f"unsupported environment schema_version {schema_version}")

    max_steps = _int(raw["max_steps"], "environment.max_steps", minimum=1)
    initial_speed = _float(raw["initial_speed"], "environment.initial_speed", positive=True)
    max_speed = _float(raw["max_speed"], "environment.max_speed", positive=True)
    if max_speed < initial_speed:
        raise ConfigError("environment.max_speed cannot be below initial_speed")

    render_mode = raw["render_mode"]
    if render_mode is not None:
        render_mode = _text(render_mode, "environment.render_mode")

    observation_schema_version = _int(
        raw["observation_schema_version"],
        "environment.observation_schema_version",
        minimum=1,
    )

    record = _record(source)
    return EnvironmentConfig(
        schema_version=schema_version,
        max_steps=max_steps,
        initial_speed=initial_speed,
        max_speed=max_speed,
        coin_reward=_float(raw["coin_reward"], "environment.coin_reward"),
        collision_penalty=_float(
            raw["collision_penalty"], "environment.collision_penalty"
        ),
        survival_reward=_float(
            raw["survival_reward"], "environment.survival_reward"
        ),
        obstacle_reward=_float(
            raw["obstacle_reward"], "environment.obstacle_reward"
        ),
        distance_horizon=_float(
            raw["distance_horizon"], "environment.distance_horizon", positive=True
        ),
        render_mode=render_mode,
        observation_schema_version=observation_schema_version,
        path=record["path"],
        sha256=record["sha256"],
    )


def assert_environment_matches_game(
    config: EnvironmentConfig, environment: Any
) -> dict:
    """Compare the declared game constants with a constructed environment.

    A mismatch is an error, never a silent override (REV3 §6.1). The check is
    optional at construction time so that the skeleton can be tested without
    launching the game; the campaign runner calls it once before any episode.
    """
    game_config = getattr(environment, "config", None)
    if game_config is None:
        raise ConfigError("environment has no game configuration to compare")
    expected = {
        "max_steps": config.max_steps,
        "initial_speed": config.initial_speed,
        "max_speed": config.max_speed,
        "coin_reward": config.coin_reward,
        "collision_penalty": config.collision_penalty,
        "survival_reward": config.survival_reward,
        "obstacle_reward": config.obstacle_reward,
    }
    observed: dict[str, Any] = {}
    mismatches: list[str] = []
    for name, value in expected.items():
        actual = getattr(game_config, name, None)
        if actual is None:
            mismatches.append(f"{name}: absent from the game configuration")
            continue
        observed[name] = actual
        if float(actual) != float(value):
            mismatches.append(f"{name}: declared {value!r}, game {actual!r}")
    adapter = getattr(environment, "observation_adapter", None)
    if adapter is not None:
        observed["distance_horizon"] = getattr(adapter, "distance_horizon", None)
        if observed["distance_horizon"] != config.distance_horizon:
            mismatches.append(
                "distance_horizon: declared "
                f"{config.distance_horizon!r}, adapter {observed['distance_horizon']!r}"
            )
    if mismatches:
        raise ConfigError(
            "phase_8/environment.yaml does not match the game: " + "; ".join(mismatches)
        )
    return {"expected": expected, "observed": observed, "match": True}


# ---------------------------------------------------------------------------
# campaign.yaml
# ---------------------------------------------------------------------------

_CAMPAIGN_KEYS = {
    "schema_version",
    "name",
    "master_seed",
    "design",
    "statistics",
    "seeds",
    "budget",
    "training",
    "paths",
    "frozen_inputs",
}
_DESIGN_KEYS = {
    "n_seeds_primary",
    "n_seeds_fallback",
    "n_seeds_selected",
    "fallback_max_paired_sd",
    "episodes_per_seed",
    "max_game_updates",
    "sei_updates",
    "conditions",
    "control_arms",
    "exploratory_arms",
    "floor_arm",
    "e_matched_id",
    "e_full_id",
}
_STATISTICS_KEYS = {
    "alpha",
    "holm_family_sizes",
    "bootstrap_resamples",
    "bootstrap_seed",
}
_SEEDS_KEYS = {"campaign", "training", "pilot"}
_BUDGET_KEYS = {"memory_gate_gb"}
_TRAINING_KEYS = {"readout_episodes_per_seed", "e_gradient_updates"}
_PATHS_KEYS = {"results_root", "run_manifest_name", "episode_store_name"}
_FROZEN_INPUT_KEYS = {
    "graph",
    "nodes",
    "synapse_policy",
    "neuron_config",
    "sensory_mapping",
    "motor_decoder",
    "plasticity",
}


def _int_list(value: Any, name: str) -> tuple[int, ...]:
    items = _sequence(value, name)
    if not items:
        raise ConfigError(f"{name} cannot be empty")
    numbers = tuple(_int(item, f"{name}[{index}]", minimum=0) for index, item in enumerate(items))
    if len(set(numbers)) != len(numbers):
        raise ConfigError(f"{name} contains duplicate seeds")
    return numbers


def _id_list(value: Any, name: str) -> tuple[str, ...]:
    items = _sequence(value, name)
    if not items:
        raise ConfigError(f"{name} cannot be empty")
    names = tuple(_text(item, f"{name}[{index}]") for index, item in enumerate(items))
    if len(set(names)) != len(names):
        raise ConfigError(f"{name} contains duplicate identifiers")
    unknown = sorted(set(names) - set(CONDITION_IDS))
    if unknown:
        raise ConfigError(f"{name} has unknown condition ids: {unknown}")
    return names


@dataclass(frozen=True)
class CampaignConfig:
    schema_version: int
    master_seed: int
    n_seeds_primary: int
    n_seeds_fallback: int
    n_seeds_selected: int | None
    fallback_max_paired_sd: float
    episodes_per_seed: int
    max_game_updates: int
    sei_updates: int
    conditions: tuple[str, ...]
    control_arms: tuple[str, ...]
    exploratory_arms: tuple[str, ...]
    floor_arm: str
    e_matched_id: str
    e_full_id: str
    alpha: float
    holm_family_sizes: tuple[int, ...]
    bootstrap_resamples: int
    bootstrap_seed: int
    campaign_seeds: tuple[int, ...]
    training_seeds: tuple[int, ...]
    pilot_seeds: tuple[int, ...]
    memory_gate_gb: float
    readout_episodes_per_seed: int
    e_gradient_updates: int
    results_root: str
    run_manifest_name: str
    episode_store_name: str
    frozen_inputs: dict
    path: str
    sha256: str

    @property
    def n_seeds_active(self) -> int:
        if self.n_seeds_selected is None:
            raise ConfigError(
                "n_seeds_selected is null: the 10.8 pilot decision (U7) is not "
                "recorded, so no campaign design exists yet"
            )
        return self.n_seeds_selected

    def active_seeds(self) -> tuple[int, ...]:
        """The first ``n_seeds_selected`` declared campaign seeds."""
        return self.campaign_seeds[: self.n_seeds_active]

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "master_seed": self.master_seed,
            "design": {
                "n_seeds_primary": self.n_seeds_primary,
                "n_seeds_fallback": self.n_seeds_fallback,
                "n_seeds_selected": self.n_seeds_selected,
                "fallback_max_paired_sd": self.fallback_max_paired_sd,
                "episodes_per_seed": self.episodes_per_seed,
                "max_game_updates": self.max_game_updates,
                "sei_updates": self.sei_updates,
                "conditions": list(self.conditions),
                "control_arms": list(self.control_arms),
                "exploratory_arms": list(self.exploratory_arms),
                "floor_arm": self.floor_arm,
                "e_matched_id": self.e_matched_id,
                "e_full_id": self.e_full_id,
            },
            "statistics": {
                "alpha": self.alpha,
                "holm_family_sizes": list(self.holm_family_sizes),
                "bootstrap_resamples": self.bootstrap_resamples,
                "bootstrap_seed": self.bootstrap_seed,
            },
            "seeds": {
                "campaign": list(self.campaign_seeds),
                "training": list(self.training_seeds),
                "pilot": list(self.pilot_seeds),
            },
            "budget": {"memory_gate_gb": self.memory_gate_gb},
            "training": {
                "readout_episodes_per_seed": self.readout_episodes_per_seed,
                "e_gradient_updates": self.e_gradient_updates,
            },
            "paths": {
                "results_root": self.results_root,
                "run_manifest_name": self.run_manifest_name,
                "episode_store_name": self.episode_store_name,
            },
            "frozen_inputs": dict(self.frozen_inputs),
            "path": self.path,
            "sha256": self.sha256,
        }


def load_campaign_config(path: str | Path | None = None) -> CampaignConfig:
    source = Path(path) if path is not None else CONFIG_DIR / CAMPAIGN_FILE
    raw = load_yaml(source)
    _unknown_keys(raw, _CAMPAIGN_KEYS, "campaign configuration")
    _required(
        raw,
        {"schema_version", "master_seed", "design", "statistics", "seeds",
         "budget", "training", "paths", "frozen_inputs"},
        "campaign configuration",
    )
    schema_version = _int(raw["schema_version"], "campaign.schema_version", minimum=1)
    if schema_version != 1:
        raise ConfigError(f"unsupported campaign schema_version {schema_version}")

    design = _mapping(raw["design"], "campaign.design")
    _unknown_keys(design, _DESIGN_KEYS, "campaign.design")
    _required(design, _DESIGN_KEYS, "campaign.design")

    primary = _int(design["n_seeds_primary"], "design.n_seeds_primary", minimum=1)
    fallback = _int(design["n_seeds_fallback"], "design.n_seeds_fallback", minimum=1)
    if fallback >= primary:
        raise ConfigError("the fallback N must be smaller than the primary N")
    selected = design["n_seeds_selected"]
    if selected is not None:
        selected = _int(selected, "design.n_seeds_selected", minimum=1)
        if selected not in (fallback, primary):
            raise ConfigError(
                "design.n_seeds_selected must be null, the predeclared fallback "
                f"({fallback}) or the primary N ({primary})"
            )

    conditions = _id_list(design["conditions"], "design.conditions")
    control_arms = _id_list(design["control_arms"], "design.control_arms")
    exploratory_arms = _id_list(design["exploratory_arms"], "design.exploratory_arms")
    declared = list(conditions) + list(control_arms) + list(exploratory_arms)
    if len(set(declared)) != len(declared):
        raise ConfigError("a condition id appears in more than one declared group")
    missing = sorted(set(CONDITION_IDS) - set(declared))
    if missing:
        raise ConfigError(f"condition ids missing from the campaign: {missing}")
    if design["floor_arm"] != "floor":
        raise ConfigError("design.floor_arm must be 'floor'")
    if design["e_matched_id"] != "E" or design["e_full_id"] != "E_full":
        raise ConfigError("design.e_matched_id/e_full_id must be 'E' and 'E_full'")

    statistics = _mapping(raw["statistics"], "campaign.statistics")
    _unknown_keys(statistics, _STATISTICS_KEYS, "campaign.statistics")
    _required(statistics, _STATISTICS_KEYS, "campaign.statistics")
    families = tuple(
        _int(value, "statistics.holm_family_sizes", minimum=1)
        for value in _sequence(statistics["holm_family_sizes"], "statistics.holm_family_sizes")
    )
    if families != (4, 3):
        raise ConfigError(
            "statistics.holm_family_sizes must declare both (4, 3) variants of U14"
        )

    seeds = _mapping(raw["seeds"], "campaign.seeds")
    _unknown_keys(seeds, _SEEDS_KEYS, "campaign.seeds")
    _required(seeds, _SEEDS_KEYS, "campaign.seeds")
    campaign_seeds = _int_list(seeds["campaign"], "seeds.campaign")
    training_seeds = _int_list(seeds["training"], "seeds.training")
    pilot_seeds = _int_list(seeds["pilot"], "seeds.pilot")
    overlaps = {
        "campaign/training": set(campaign_seeds) & set(training_seeds),
        "campaign/pilot": set(campaign_seeds) & set(pilot_seeds),
        "training/pilot": set(training_seeds) & set(pilot_seeds),
    }
    conflicts = {name: sorted(values) for name, values in overlaps.items() if values}
    if conflicts:
        raise ConfigError(f"declared seed ranges overlap: {conflicts}")
    if len(campaign_seeds) < primary:
        raise ConfigError(
            f"seeds.campaign declares {len(campaign_seeds)} seeds but the primary "
            f"design needs {primary}"
        )

    budget = _mapping(raw["budget"], "campaign.budget")
    _unknown_keys(budget, _BUDGET_KEYS, "campaign.budget")
    _required(budget, _BUDGET_KEYS, "campaign.budget")
    memory_gate = _float(budget["memory_gate_gb"], "budget.memory_gate_gb", positive=True)

    training = _mapping(raw["training"], "campaign.training")
    _unknown_keys(training, _TRAINING_KEYS, "campaign.training")
    _required(training, _TRAINING_KEYS, "campaign.training")

    paths = _mapping(raw["paths"], "campaign.paths")
    _unknown_keys(paths, _PATHS_KEYS, "campaign.paths")
    _required(paths, _PATHS_KEYS, "campaign.paths")

    frozen = _mapping(raw["frozen_inputs"], "campaign.frozen_inputs")
    _unknown_keys(frozen, _FROZEN_INPUT_KEYS, "campaign.frozen_inputs")
    _required(frozen, _FROZEN_INPUT_KEYS, "campaign.frozen_inputs")
    frozen_inputs = {}
    for name in sorted(frozen):
        value = _text(frozen[name], f"frozen_inputs.{name}")
        if Path(value).is_absolute():
            raise ConfigError(
                f"frozen_inputs.{name} must be relative to the repository root"
            )
        frozen_inputs[name] = value

    record = _record(source)
    return CampaignConfig(
        schema_version=schema_version,
        master_seed=_int(raw["master_seed"], "campaign.master_seed", minimum=0),
        n_seeds_primary=primary,
        n_seeds_fallback=fallback,
        n_seeds_selected=selected,
        fallback_max_paired_sd=_float(
            design["fallback_max_paired_sd"],
            "design.fallback_max_paired_sd",
            positive=True,
        ),
        episodes_per_seed=_int(
            design["episodes_per_seed"], "design.episodes_per_seed", minimum=1
        ),
        max_game_updates=_int(
            design["max_game_updates"], "design.max_game_updates", minimum=1
        ),
        sei_updates=_int(design["sei_updates"], "design.sei_updates", minimum=1),
        conditions=conditions,
        control_arms=control_arms,
        exploratory_arms=exploratory_arms,
        floor_arm="floor",
        e_matched_id="E",
        e_full_id="E_full",
        alpha=_float(statistics["alpha"], "statistics.alpha", unit_interval=True),
        holm_family_sizes=families,
        bootstrap_resamples=_int(
            statistics["bootstrap_resamples"], "statistics.bootstrap_resamples", minimum=1
        ),
        bootstrap_seed=_int(
            statistics["bootstrap_seed"], "statistics.bootstrap_seed", minimum=0
        ),
        campaign_seeds=campaign_seeds,
        training_seeds=training_seeds,
        pilot_seeds=pilot_seeds,
        memory_gate_gb=memory_gate,
        readout_episodes_per_seed=_int(
            training["readout_episodes_per_seed"],
            "training.readout_episodes_per_seed",
            minimum=1,
        ),
        e_gradient_updates=_int(
            training["e_gradient_updates"], "training.e_gradient_updates", minimum=1
        ),
        results_root=_text(paths["results_root"], "paths.results_root"),
        run_manifest_name=_text(paths["run_manifest_name"], "paths.run_manifest_name"),
        episode_store_name=_text(paths["episode_store_name"], "paths.episode_store_name"),
        frozen_inputs=frozen_inputs,
        path=record["path"],
        sha256=record["sha256"],
    )


# ---------------------------------------------------------------------------
# conditions.yaml
# ---------------------------------------------------------------------------

_CONDITION_FILE_KEYS = {
    "schema_version",
    "name",
    "plasticity",
    "sensory",
    "decoder",
    "readout",
    "e_learner",
    "conditions",
    "controls",
    "exploratory",
}
_SPEC_KEYS = {
    "role",
    "substrate",
    "plasticity",
    "controller",
    "trains",
    "eta",
    "requires_structure",
    "requires_exact_match_of",
    "state_independent",
    "init_only",
    "feature_set",
}


def _condition_spec(
    condition_id: str,
    payload: Any,
    *,
    plasticity_name: str,
    plasticity_eta: float,
) -> dict:
    spec = _mapping(payload, f"conditions.{condition_id}")
    _unknown_keys(spec, _SPEC_KEYS, f"conditions.{condition_id}")
    _required(
        spec,
        {"role", "substrate", "plasticity", "controller", "trains", "eta"},
        f"conditions.{condition_id}",
    )
    trains = tuple(_text(item, f"conditions.{condition_id}.trains") for item in _sequence(
        spec["trains"], f"conditions.{condition_id}.trains"
    ))
    if not trains or any(item not in TRAINABLE_TARGETS for item in trains):
        raise ConfigError(
            f"conditions.{condition_id}.trains must be a subset of {TRAINABLE_TARGETS}"
        )
    eta = spec["eta"]
    plasticity = _text(spec["plasticity"], f"conditions.{condition_id}.plasticity")
    if eta is None:
        if plasticity != "none":
            raise ConfigError(
                f"conditions.{condition_id} declares {plasticity} plasticity but no eta"
            )
    else:
        eta = _float(eta, f"conditions.{condition_id}.eta")
        if plasticity != plasticity_name:
            raise ConfigError(
                f"conditions.{condition_id}.eta is declared but plasticity is {plasticity!r}"
            )
        if condition_id in ("B", "D") and eta != plasticity_eta:
            raise ConfigError(
                f"conditions.{condition_id}.eta must equal the Phase 5 value {plasticity_eta}"
            )
        if condition_id in ("A_prime", "C_prime") and eta != 0.0:
            raise ConfigError(
                f"conditions.{condition_id}.eta must be exactly 0.0 (REV3 §3.8)"
            )
    if bool(spec.get("state_independent", False)) != (condition_id == "F_beta"):
        raise ConfigError("state_independent may be true only for F_beta")
    if bool(spec.get("init_only", False)) != (condition_id == "F_init"):
        raise ConfigError("init_only may be true only for F_init")
    return {
        "id": condition_id,
        "role": _text(spec["role"], f"conditions.{condition_id}.role"),
        "substrate": _text(spec["substrate"], f"conditions.{condition_id}.substrate"),
        "plasticity": plasticity,
        "controller": _text(spec["controller"], f"conditions.{condition_id}.controller"),
        "trains": list(trains),
        "eta": eta,
        "requires_structure": bool(spec.get("requires_structure", False)),
        "requires_exact_match_of": spec.get("requires_exact_match_of"),
        "state_independent": bool(spec.get("state_independent", False)),
        "init_only": bool(spec.get("init_only", False)),
        "feature_set": spec.get("feature_set"),
    }


@dataclass(frozen=True)
class ConditionsConfig:
    schema_version: int
    plasticity: dict
    sensory: dict
    decoder: dict
    readout: dict
    e_learner: dict
    conditions: dict
    controls: dict
    exploratory: dict
    path: str
    sha256: str

    @property
    def all_specs(self) -> dict[str, dict]:
        payload: dict[str, dict] = {}
        for group in (self.conditions, self.controls, self.exploratory):
            payload.update(group)
        return payload

    def spec(self, condition_id: str) -> dict:
        try:
            return self.all_specs[condition_id]
        except KeyError:
            raise ConfigError(f"condition {condition_id!r} is not declared") from None

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "plasticity": dict(self.plasticity),
            "sensory": dict(self.sensory),
            "decoder": dict(self.decoder),
            "readout": dict(self.readout),
            "e_learner": dict(self.e_learner),
            "conditions": {key: dict(value) for key, value in self.conditions.items()},
            "controls": {key: dict(value) for key, value in self.controls.items()},
            "exploratory": {
                key: dict(value) for key, value in self.exploratory.items()
            },
            "path": self.path,
            "sha256": self.sha256,
        }


def load_conditions_config(path: str | Path | None = None) -> ConditionsConfig:
    source = Path(path) if path is not None else CONFIG_DIR / CONDITIONS_FILE
    raw = load_yaml(source)
    _unknown_keys(raw, _CONDITION_FILE_KEYS, "conditions configuration")
    _required(
        raw,
        {"schema_version", "plasticity", "sensory", "decoder", "readout",
         "e_learner", "conditions", "controls", "exploratory"},
        "conditions configuration",
    )
    schema_version = _int(raw["schema_version"], "conditions.schema_version", minimum=1)
    if schema_version != 1:
        raise ConfigError(f"unsupported conditions schema_version {schema_version}")

    plasticity = dict(_mapping(raw["plasticity"], "conditions.plasticity"))
    if plasticity.get("eta") is None:
        raise ConfigError("conditions.plasticity.eta is required")
    eta = _float(plasticity["eta"], "conditions.plasticity.eta", positive=True)
    if plasticity.get("eta_identity") != 0.0:
        raise ConfigError("conditions.plasticity.eta_identity must be exactly 0.0")

    sensory = dict(_mapping(raw["sensory"], "conditions.sensory"))
    decoder = dict(_mapping(raw["decoder"], "conditions.decoder"))
    readout = dict(_mapping(raw["readout"], "conditions.readout"))
    e_learner = dict(_mapping(raw["e_learner"], "conditions.e_learner"))

    if _int(sensory.get("n_features"), "conditions.sensory.n_features", minimum=1) != 7:
        raise ConfigError("the neural interface is declared as 7 features (REV3 §6.6)")
    if _int(sensory.get("n_features_full"), "conditions.sensory.n_features_full", minimum=1) != 14:
        raise ConfigError("the full observation is declared as 14 features")

    groups = {}
    for name in ("conditions", "controls", "exploratory"):
        payload = _mapping(raw[name], f"conditions.{name}")
        if not payload:
            raise ConfigError(f"conditions.{name} cannot be empty")
        groups[name] = {
            _text(key, f"conditions.{name} id"): _condition_spec(
                _text(key, f"conditions.{name} id"),
                value,
                plasticity_name="three_factor",
                plasticity_eta=eta,
            )
            for key, value in payload.items()
        }

    declared = [key for group in groups.values() for key in group]
    if len(set(declared)) != len(declared):
        raise ConfigError("a condition is declared in more than one group")
    missing = sorted(set(CONDITION_IDS) - set(declared))
    if missing:
        raise ConfigError(f"condition ids missing from conditions.yaml: {missing}")

    for condition_id, spec in groups["conditions"].items():
        if spec["requires_exact_match_of"] is not None:
            raise ConfigError(
                f"{condition_id} is a condition but declares an exact-match target"
            )
    for condition_id, spec in groups["controls"].items():
        target = spec["requires_exact_match_of"]
        if target is not None and target not in groups["conditions"]:
            raise ConfigError(
                f"conditions.controls.{condition_id} refers to undeclared condition {target!r}"
            )

    record = _record(source)
    return ConditionsConfig(
        schema_version=schema_version,
        plasticity=plasticity,
        sensory=sensory,
        decoder=decoder,
        readout=readout,
        e_learner=e_learner,
        conditions=groups["conditions"],
        controls=groups["controls"],
        exploratory=groups["exploratory"],
        path=record["path"],
        sha256=record["sha256"],
    )


# ---------------------------------------------------------------------------
# the combined configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase8Config:
    environment: EnvironmentConfig
    campaign: CampaignConfig
    conditions: ConditionsConfig
    hashes: dict

    def describe(self) -> dict:
        return {
            "protocol": "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4",
            "approval": "not approved: REV4 §10.0/§12",
            "files": dict(self.hashes),
            "environment": self.environment.as_dict(),
            "campaign": self.campaign.as_dict(),
            "conditions": self.conditions.as_dict(),
            "seed_derivation": describe_derivation(self.campaign.master_seed),
            "memory_gate_gb": self.campaign.memory_gate_gb,
        }


def load_phase8_config(
    *,
    environment_path: str | Path | None = None,
    campaign_path: str | Path | None = None,
    conditions_path: str | Path | None = None,
) -> Phase8Config:
    environment = load_environment_config(environment_path)
    campaign = load_campaign_config(campaign_path)
    conditions = load_conditions_config(conditions_path)

    if campaign.master_seed != MASTER_SEED:
        raise ConfigError(
            f"campaign.master_seed {campaign.master_seed} differs from the declared "
            f"MASTER_SEED {MASTER_SEED}; change the declared constant, not the YAML alone"
        )

    campaign_ids = (
        set(campaign.conditions)
        | set(campaign.control_arms)
        | set(campaign.exploratory_arms)
    )
    spec_ids = set(conditions.conditions) | set(conditions.controls) | set(
        conditions.exploratory
    )
    if campaign_ids != spec_ids:
        raise ConfigError(
            "campaign.yaml and conditions.yaml disagree on the condition set: "
            f"only campaign {sorted(campaign_ids - spec_ids)}, "
            f"only conditions {sorted(spec_ids - campaign_ids)}"
        )
    if set(campaign.conditions) != set(conditions.conditions):
        raise ConfigError("campaign conditions and conditions.yaml 'conditions' differ")
    if set(campaign.control_arms) != set(conditions.controls):
        raise ConfigError("campaign control arms and conditions.yaml 'controls' differ")
    if set(campaign.exploratory_arms) != set(conditions.exploratory):
        raise ConfigError(
            "campaign exploratory arms and conditions.yaml 'exploratory' differ"
        )

    hashes = {
        "environment": {"path": environment.path, "sha256": environment.sha256},
        "campaign": {"path": campaign.path, "sha256": campaign.sha256},
        "conditions": {"path": conditions.path, "sha256": conditions.sha256},
    }
    return Phase8Config(
        environment=environment,
        campaign=campaign,
        conditions=conditions,
        hashes=hashes,
    )


# ---------------------------------------------------------------------------
# memory gate
# ---------------------------------------------------------------------------


def memory_preflight(gate_gb: float) -> dict:
    """Read free physical memory and compare it with the declared gate.

    The gate is not weakened (§9.3). If the measurement is unavailable the
    result counts as *not passed*; a campaign may not start on an unknown
    reading.
    """
    gate = _float(gate_gb, "memory_gate_gb", positive=True)
    try:
        import psutil
    except ImportError:  # pragma: no cover - psutil is present in this repo
        return {
            "available_gb": None,
            "total_gb": None,
            "percent_used": None,
            "gate_gb": gate,
            "passed": False,
            "source": "psutil unavailable",
            "reason": "free memory could not be measured; the gate is not assumed passed",
        }
    memory = psutil.virtual_memory()
    available = float(memory.available) / 1024.0**3
    return {
        "available_gb": round(available, 3),
        "total_gb": round(float(memory.total) / 1024.0**3, 3),
        "percent_used": round(float(memory.percent), 3),
        "gate_gb": gate,
        "passed": bool(available >= gate),
        "source": "psutil.virtual_memory().available",
        "reason": (
            "at or above the gate"
            if available >= gate
            else "below the 4 GB gate: no BANC-scale randomisation, campaign "
            "simulation or training may start (REV3 §9.3)"
        ),
    }


def require_memory_gate(config: Phase8Config) -> dict:
    """Raise :class:`MemoryGateError` when the §9.3 preflight fails."""
    report = memory_preflight(config.campaign.memory_gate_gb)
    if not report["passed"]:
        raise MemoryGateError(report["reason"] + f" (available {report['available_gb']} GB)")
    return report


__all__ = [
    "CONFIG_DIR",
    "CampaignConfig",
    "ConditionsConfig",
    "ConfigError",
    "ENVIRONMENT_FILE",
    "EnvironmentConfig",
    "MemoryGateError",
    "Phase8Config",
    "assert_environment_matches_game",
    "load_campaign_config",
    "load_conditions_config",
    "load_environment_config",
    "load_phase8_config",
    "load_yaml",
    "memory_preflight",
    "require_memory_gate",
]
