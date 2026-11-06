"""Phase 3A.5 calibration: factor conditions, metrics and selection rules.

The module reuses the Phase 3A encoders, mapping, scheduler and simulator.
It only changes configuration values for one factor at a time. Every reported
spike is simulated model activity; no value here is a biological measurement.
"""

from __future__ import annotations

import copy
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from sensory.game_state import (
    CoinState,
    GameState,
    ObstacleState,
    ObstacleType,
    parse_lane,
)
from sensory.sensory_experiment import prepare_setup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALIBRATION_CONFIG = PROJECT_ROOT / "configs" / "sensory_calibration.yaml"

REQUIRED_KEYS = (
    "base_config",
    "output_dir",
    "duration_ms",
    "feature",
    "current_amplitudes_pa",
    "sigma_fractions",
    "population_sizes",
    "baseline_activations",
    "transitions_ms",
    "distances",
    "mapping_seed",
    "extra_mapping_seeds",
    "default_amplitude_pa",
    "default_sigma_fraction",
    "default_population_size",
    "default_baseline",
    "additivity",
    "transition_sequence",
    "controls",
    "selection",
)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _positive(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def _non_negative(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def _unit(value, name: str) -> float:
    number = _non_negative(value, name)
    if number > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return number


def _unique_numbers(values, name: str) -> list[float]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    numbers = [float(value) for value in values]
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"{name} must not contain duplicates")
    return numbers


def load_calibration_config(path: str | Path = DEFAULT_CALIBRATION_CONFIG) -> dict:
    """Load and validate the calibration configuration and its base config."""
    path = resolve_path(path)
    if not path.exists():
        raise FileNotFoundError(f"calibration configuration not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict) or "calibration" not in payload:
        raise ValueError("calibration configuration must contain 'calibration'")
    config = payload["calibration"]
    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        raise ValueError(f"calibration configuration is missing {missing}")

    feature = str(config["feature"])
    amplitudes = [
        _positive(value, "current_amplitudes_pa")
        for value in _unique_numbers(config["current_amplitudes_pa"], "current_amplitudes_pa")
    ]
    sigmas = [
        _positive(value, "sigma_fractions")
        for value in _unique_numbers(config["sigma_fractions"], "sigma_fractions")
    ]
    if any(value > 1.0 for value in sigmas):
        raise ValueError("sigma_fractions must be in (0, 1]")
    raw_sizes = _unique_numbers(config["population_sizes"], "population_sizes")
    if any(not float(value).is_integer() for value in raw_sizes):
        raise ValueError("population_sizes must be integers")
    sizes = [int(value) for value in raw_sizes]
    if any(value < 1 for value in sizes):
        raise ValueError("population_sizes must be positive integers")
    baselines = [
        _unit(value, "baseline_activations")
        for value in _unique_numbers(config["baseline_activations"], "baseline_activations")
    ]
    transitions = [
        _non_negative(value, "transitions_ms")
        for value in _unique_numbers(config["transitions_ms"], "transitions_ms")
    ]
    distances = [
        _unit(value, "distances")
        for value in _unique_numbers(config["distances"], "distances")
    ]
    if len(distances) < 2:
        raise ValueError("at least two distances are required")
    if sorted(distances) != distances:
        raise ValueError("distances must be in ascending order")

    seeds = [int(config["mapping_seed"])] + [
        int(value) for value in config["extra_mapping_seeds"]
    ]
    if len(set(seeds)) != len(seeds):
        raise ValueError("mapping seeds must be unique")
    if len(seeds) != 3:
        raise ValueError("three mapping seeds are required")

    base_config_path = resolve_path(config["base_config"])
    if not base_config_path.exists():
        raise FileNotFoundError(f"base sensory configuration not found: {base_config_path}")
    with base_config_path.open("r", encoding="utf-8") as handle:
        base = yaml.safe_load(handle)
    if feature not in base.get("features", {}):
        raise ValueError(f"base configuration has no feature {feature!r}")
    if feature not in base.get("mapping", {}).get("populations", {}):
        raise ValueError(f"base mapping has no population {feature!r}")

    controls = config["controls"]
    if not isinstance(controls, dict) or "feature_controls" not in controls:
        raise ValueError("controls.feature_controls must be a mapping")
    for name, control in controls["feature_controls"].items():
        if name not in base["features"]:
            raise ValueError(f"control feature {name!r} is not in the base config")
        control_amplitudes = [
            _positive(value, f"{name} control amplitude")
            for value in control.get("amplitudes_pa", [])
        ]
        if not control_amplitudes:
            raise ValueError(f"control feature {name!r} has no amplitudes")

    selection = config["selection"]
    if not isinstance(selection, dict):
        raise ValueError("selection must be a mapping")
    _unit(selection.get("saturation_fraction"), "selection.saturation_fraction")

    return {
        "path": path,
        "feature": feature,
        "base_config_path": base_config_path,
        "base_config": base,
        "amplitudes_pa": amplitudes,
        "sigma_fractions": sigmas,
        "population_sizes": sizes,
        "baseline_activations": baselines,
        "transitions_ms": transitions,
        "distances": distances,
        "mapping_seeds": seeds,
        "default_amplitude_pa": _positive(
            config["default_amplitude_pa"], "default_amplitude_pa"
        ),
        "default_sigma_fraction": _positive(
            config["default_sigma_fraction"], "default_sigma_fraction"
        ),
        "default_population_size": int(config["default_population_size"]),
        "default_baseline": _unit(config["default_baseline"], "default_baseline"),
        "duration_ms": _positive(config["duration_ms"], "duration_ms"),
        "output_dir": str(config["output_dir"]),
        "additivity": dict(config["additivity"]),
        "transition_sequence": dict(config["transition_sequence"]),
        "controls": controls,
        "selection": selection,
    }


def build_setup(
    graph,
    base_config: dict,
    *,
    feature: str = "obstacle_distance",
    amplitude_pa: float | None = None,
    amplitudes: dict | None = None,
    sigma_fraction: float | None = None,
    population_size: int | None = None,
    baseline: float | None = None,
    mapping_seed: int | None = None,
    transition_ms: float | None = None,
    duration_ms: float | None = None,
):
    """Build a Phase 3A setup with one factor changed.

    Encoders, mapping, scheduler and simulator are otherwise unchanged.
    """
    config = copy.deepcopy(base_config)
    if amplitude_pa is not None:
        config["features"][feature]["current_pa"] = float(amplitude_pa)
    for name, value in (amplitudes or {}).items():
        if name not in config["features"]:
            raise ValueError(f"unknown amplitude feature {name!r}")
        config["features"][name]["current_pa"] = float(value)
    if sigma_fraction is not None:
        config["features"][feature]["sigma_fraction"] = float(sigma_fraction)
    if population_size is not None:
        size = int(population_size)
        config["features"][feature]["n_neurons"] = size
        config["mapping"]["populations"][feature]["n_neurons"] = size
    if baseline is not None:
        config["features"][feature]["baseline"] = float(baseline)
    if mapping_seed is not None:
        config["mapping"]["seed"] = int(mapping_seed)
    if transition_ms is not None:
        config["sensory"]["transition_ms"] = float(transition_ms)
    if duration_ms is not None:
        config["sensory"]["duration_ms"] = float(duration_ms)
    return prepare_setup(graph, config)


def _tag(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", "p")
    return str(value).replace(" ", "_")


def _baseline_state(base_config: dict) -> GameState:
    return GameState.from_dict(base_config["protocols"].get("baseline_state", {}))


def _obstacle_state(
    base_config: dict, distance: float, *, lane: str = "center"
) -> GameState:
    return replace(
        _baseline_state(base_config),
        obstacle=ObstacleState(
            present=True,
            lane=parse_lane(lane),
            distance=float(distance),
            obstacle_type=ObstacleType.LOW,
        ),
    )


def _coin_state(base_config: dict, distance: float, *, lane: str = "center") -> GameState:
    return replace(
        _baseline_state(base_config),
        coin=CoinState(
            present=True, lane=parse_lane(lane), distance=float(distance)
        ),
    )


def _speed_state(base_config: dict, speed: float) -> GameState:
    state = _baseline_state(base_config)
    return replace(state, player=replace(state.player, speed=float(speed)))


def _spec(
    *,
    name: str,
    stage: str,
    description: str,
    timeline: list,
    duration_ms: float,
    active_features: list[str],
    factors: dict,
) -> dict:
    return {
        "name": name,
        "stage": stage,
        "protocol": "calibration",
        "description": description,
        "timeline": timeline,
        "duration_ms": float(duration_ms),
        "active_features": list(active_features),
        "factors": dict(factors),
    }


def amplitude_groups(cal: dict) -> list[dict]:
    """3A.5.1: amplitude x distance at the standard tuning and mapping."""
    groups = []
    for amplitude in cal["amplitudes_pa"]:
        specs = []
        for distance in cal["distances"]:
            specs.append(
                _spec(
                    name=f"a5_1_amp{int(amplitude)}_dist{_tag(float(distance))}",
                    stage="amplitude",
                    description=(
                        f"obstacle distance {distance} at {amplitude} pA "
                        "in the obstacle-distance population"
                    ),
                    timeline=[(0.0, _obstacle_state(cal["base_config"], distance))],
                    duration_ms=cal["duration_ms"],
                    active_features=[cal["feature"]],
                    factors={"amplitude_pa": amplitude, "distance": distance},
                )
            )
        groups.append(
            {
                "setup": {
                    "feature": cal["feature"],
                    "amplitude_pa": amplitude,
                },
                "parameters": {"amplitude_pa": amplitude},
                "specs": specs,
            }
        )
    return groups


def tuning_groups(cal: dict, amplitudes: list[float]) -> list[dict]:
    """3A.5.3: tuning width at the best two amplitudes."""
    groups = []
    for sigma in cal["sigma_fractions"]:
        for amplitude in amplitudes:
            specs = []
            for distance in cal["distances"]:
                specs.append(
                    _spec(
                        name=(
                            f"a5_3_amp{int(amplitude)}_sigma{_tag(float(sigma))}"
                            f"_dist{_tag(float(distance))}"
                        ),
                        stage="tuning",
                        description=(
                            f"obstacle distance {distance} at {amplitude} pA "
                            f"and sigma_fraction {sigma}"
                        ),
                        timeline=[
                            (0.0, _obstacle_state(cal["base_config"], distance))
                        ],
                        duration_ms=cal["duration_ms"],
                        active_features=[cal["feature"]],
                        factors={
                            "amplitude_pa": amplitude,
                            "sigma_fraction": sigma,
                            "distance": distance,
                        },
                    )
                )
            groups.append(
                {
                    "setup": {
                        "feature": cal["feature"],
                        "amplitude_pa": amplitude,
                        "sigma_fraction": sigma,
                    },
                    "parameters": {
                        "amplitude_pa": amplitude,
                        "sigma_fraction": sigma,
                    },
                    "specs": specs,
                }
            )
    return groups


def population_groups(
    cal: dict, amplitude: float, sigma_fraction: float
) -> list[dict]:
    """3A.5.4: population size at the selected amplitude and width."""
    groups = []
    for size in cal["population_sizes"]:
        specs = []
        for distance in cal["distances"]:
            specs.append(
                _spec(
                    name=f"a5_4_size{int(size)}_dist{_tag(float(distance))}",
                    stage="population",
                    description=(
                        f"obstacle distance {distance} with {size} "
                        "obstacle-distance neurons"
                    ),
                    timeline=[(0.0, _obstacle_state(cal["base_config"], distance))],
                    duration_ms=cal["duration_ms"],
                    active_features=[cal["feature"]],
                    factors={
                        "amplitude_pa": amplitude,
                        "sigma_fraction": sigma_fraction,
                        "population_size": size,
                        "distance": distance,
                    },
                )
            )
        groups.append(
            {
                "setup": {
                    "feature": cal["feature"],
                    "amplitude_pa": amplitude,
                    "sigma_fraction": sigma_fraction,
                    "population_size": size,
                },
                "parameters": {"population_size": size},
                "specs": specs,
            }
        )
    return groups


def seed_groups(
    cal: dict, amplitude: float, sigma_fraction: float, population_size: int
) -> list[dict]:
    """3A.5.5: mapping-seed sensitivity at the selected configuration."""
    groups = []
    for seed in cal["mapping_seeds"]:
        specs = []
        for distance in cal["distances"]:
            specs.append(
                _spec(
                    name=f"a5_5_seed{seed}_dist{_tag(float(distance))}",
                    stage="seeds",
                    description=(
                        f"obstacle distance {distance} with mapping seed {seed}"
                    ),
                    timeline=[(0.0, _obstacle_state(cal["base_config"], distance))],
                    duration_ms=cal["duration_ms"],
                    active_features=[cal["feature"]],
                    factors={
                        "amplitude_pa": amplitude,
                        "sigma_fraction": sigma_fraction,
                        "population_size": population_size,
                        "mapping_seed": seed,
                        "distance": distance,
                    },
                )
            )
        groups.append(
            {
                "setup": {
                    "feature": cal["feature"],
                    "amplitude_pa": amplitude,
                    "sigma_fraction": sigma_fraction,
                    "population_size": population_size,
                    "mapping_seed": seed,
                },
                "parameters": {"mapping_seed": seed},
                "specs": specs,
            }
        )
    return groups


def additivity_groups(
    cal: dict,
    amplitude: float,
    sigma_fraction: float,
    population_size: int,
    mapping_seed: int,
) -> list[dict]:
    """3A.5.6: obstacle and coin separately and together."""
    settings = cal["additivity"]
    obstacle_distance = float(settings["obstacle_distance"])
    coin_distance = float(settings["coin_distance"])
    setup = {
        "feature": cal["feature"],
        "amplitude_pa": amplitude,
        "sigma_fraction": sigma_fraction,
        "population_size": population_size,
        "mapping_seed": mapping_seed,
    }
    base = _baseline_state(cal["base_config"])
    obstacle = replace(
        base,
        obstacle=ObstacleState(
            present=True,
            lane=parse_lane("center"),
            distance=obstacle_distance,
            obstacle_type=ObstacleType.LOW,
        ),
    )
    coin = replace(
        base,
        coin=CoinState(
            present=True, lane=parse_lane("center"), distance=coin_distance
        ),
    )
    both = replace(
        obstacle,
        coin=CoinState(
            present=True, lane=parse_lane("center"), distance=coin_distance
        ),
    )
    specs = [
        _spec(
            name="a5_6_obstacle",
            stage="additivity",
            description=f"obstacle alone at distance {obstacle_distance}",
            timeline=[(0.0, obstacle)],
            duration_ms=cal["duration_ms"],
            active_features=["obstacle_distance"],
            factors={"kind": "obstacle", "distance": obstacle_distance},
        ),
        _spec(
            name="a5_6_coin",
            stage="additivity",
            description=f"coin alone at distance {coin_distance}",
            timeline=[(0.0, coin)],
            duration_ms=cal["duration_ms"],
            active_features=["coin_distance"],
            factors={"kind": "coin", "distance": coin_distance},
        ),
        _spec(
            name="a5_6_both",
            stage="additivity",
            description=(
                f"obstacle at {obstacle_distance} and coin at {coin_distance}"
            ),
            timeline=[(0.0, both)],
            duration_ms=cal["duration_ms"],
            active_features=["obstacle_distance", "coin_distance"],
            factors={
                "kind": "both",
                "obstacle_distance": obstacle_distance,
                "coin_distance": coin_distance,
            },
        ),
    ]
    return [{"setup": setup, "parameters": {"kind": "additivity"}, "specs": specs}]


def transition_groups(
    cal: dict,
    amplitude: float,
    sigma_fraction: float,
    population_size: int,
    mapping_seed: int,
) -> list[dict]:
    """3A.5.7: linear activation crossfade between two distance states."""
    sequence = cal["transition_sequence"]
    far = float(sequence["far_distance"])
    near = float(sequence["near_distance"])
    switch_ms = float(sequence["switch_ms"])
    duration_ms = cal["duration_ms"]
    if switch_ms <= 0 or switch_ms >= duration_ms:
        raise ValueError("transition_sequence.switch_ms must be inside the run")
    groups = []
    for transition_ms in cal["transitions_ms"]:
        far_state = replace(
            _obstacle_state(cal["base_config"], far), time_ms=0.0
        )
        near_state = replace(
            _obstacle_state(cal["base_config"], near), time_ms=switch_ms
        )
        spec = _spec(
            name=f"a5_7_transition{_tag(float(transition_ms))}",
            stage="transition",
            description=(
                f"distance {far} to {near} at {switch_ms} ms with a "
                f"{transition_ms} ms crossfade"
            ),
            timeline=[(0.0, far_state), (switch_ms, near_state)],
            duration_ms=duration_ms,
            active_features=[cal["feature"]],
            factors={
                "amplitude_pa": amplitude,
                "sigma_fraction": sigma_fraction,
                "population_size": population_size,
                "mapping_seed": mapping_seed,
                "transition_ms": transition_ms,
            },
        )
        groups.append(
            {
                "setup": {
                    "feature": cal["feature"],
                    "amplitude_pa": amplitude,
                    "sigma_fraction": sigma_fraction,
                    "population_size": population_size,
                    "mapping_seed": mapping_seed,
                    "transition_ms": transition_ms,
                },
                "parameters": {"transition_ms": transition_ms},
                "specs": [spec],
            }
        )
    return groups


def baseline_groups(
    cal: dict, amplitude: float, sigma_fraction: float, population_size: int
) -> list[dict]:
    """3A.5.8: activation baseline at the selected configuration."""
    groups = []
    for baseline in cal["baseline_activations"]:
        specs = []
        for distance in cal["distances"]:
            specs.append(
                _spec(
                    name=(
                        f"a5_8_baseline{_tag(float(baseline))}"
                        f"_dist{_tag(float(distance))}"
                    ),
                    stage="baseline",
                    description=(
                        f"baseline activation {baseline} at distance {distance}"
                    ),
                    timeline=[(0.0, _obstacle_state(cal["base_config"], distance))],
                    duration_ms=cal["duration_ms"],
                    active_features=[cal["feature"]],
                    factors={
                        "amplitude_pa": amplitude,
                        "sigma_fraction": sigma_fraction,
                        "population_size": population_size,
                        "baseline": baseline,
                        "distance": distance,
                    },
                )
            )
        groups.append(
            {
                "setup": {
                    "feature": cal["feature"],
                    "amplitude_pa": amplitude,
                    "sigma_fraction": sigma_fraction,
                    "population_size": population_size,
                    "baseline": baseline,
                },
                "parameters": {"baseline": baseline},
                "specs": specs,
            }
        )
    return groups


def control_groups(cal: dict) -> list[dict]:
    """Sub-rheobase and saturation controls for coin and speed features.

    The obstacle-distance controls are the 100 pA and 300 pA rows of the
    amplitude sweep and are referenced rather than repeated.
    """
    groups = []
    for feature, control in cal["controls"]["feature_controls"].items():
        for amplitude in control["amplitudes_pa"]:
            if feature == "coin_distance":
                state = _coin_state(cal["base_config"], float(control["distance"]))
                description = (
                    f"coin distance {control['distance']} at {amplitude} pA"
                )
                factors = {"kind": "coin_control", "distance": control["distance"]}
                active = ["coin_distance"]
            elif feature == "player_speed":
                state = _speed_state(cal["base_config"], float(control["speed"]))
                description = f"player speed {control['speed']} at {amplitude} pA"
                factors = {"kind": "speed_control", "speed": control["speed"]}
                active = ["player_speed"]
            else:
                raise ValueError(f"unsupported control feature {feature!r}")
            spec = _spec(
                name=f"a5_control_{feature.split('_')[0]}_amp{int(amplitude)}",
                stage="controls",
                description=description,
                timeline=[(0.0, state)],
                duration_ms=cal["duration_ms"],
                active_features=active,
                factors={**factors, "amplitude_pa": amplitude},
            )
            groups.append(
                {
                    "setup": {
                        "feature": feature,
                        "amplitudes": {feature: amplitude},
                    },
                    "parameters": {"feature": feature, "amplitude_pa": amplitude},
                    "specs": [spec],
                }
            )
    return groups


def extract_calibration_metrics(
    run: dict, setup, feature_names: list[str]
) -> dict:
    """Per-feature spike counts, recruitment and latency for one run."""
    recorder = run["result"].recorder
    counts = recorder.spike_counts()
    spike_times = np.asarray(recorder.spike_times_ms)
    spike_indices = np.asarray(recorder.spike_neuron_indices)
    by_feature = {}
    for feature in feature_names:
        indices = setup.mapping.indices(feature)
        feature_counts = counts[indices]
        mask = np.isin(spike_indices, indices)
        latencies = np.sort(spike_times[mask])
        if latencies.size:
            latency = {
                "first_ms": round(float(latencies[0]), 4),
                "median_ms": round(float(np.median(latencies)), 4),
                "p95_ms": round(float(np.percentile(latencies, 95)), 4),
            }
        else:
            latency = {"first_ms": None, "median_ms": None, "p95_ms": None}
        size = int(indices.size)
        spikes = int(feature_counts.sum())
        by_feature[feature] = {
            "n_neurons": size,
            "spikes": spikes,
            "active_neurons": int(np.count_nonzero(feature_counts)),
            "recruitment_fraction": round(
                float(np.count_nonzero(feature_counts)) / max(1, size), 6
            ),
            "spikes_per_neuron": round(spikes / max(1, size), 6),
            "population_vector": [int(value) for value in feature_counts],
            "latency_ms": latency,
        }
    total_spikes = int(sum(item["spikes"] for item in by_feature.values()))
    return {
        "by_feature": by_feature,
        "total_feature_spikes": total_spikes,
        "total_active_feature_neurons": int(
            sum(item["active_neurons"] for item in by_feature.values())
        ),
    }


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(values.size, dtype=np.float64)
    # Average ranks for ties.
    for value in np.unique(values):
        positions = np.flatnonzero(values == value)
        if positions.size > 1:
            ranks[positions] = ranks[positions].mean()
    return ranks


def spearman(x, y) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size != y.size or x.size < 2:
        return 0.0
    if np.all(x == x[0]) or np.all(y == y[0]):
        return 0.0
    rx = _ranks(x)
    ry = _ranks(y)
    rx -= rx.mean()
    ry -= ry.mean()
    denominator = math.sqrt(float((rx * rx).sum() * (ry * ry).sum()))
    if denominator == 0.0:
        return 0.0
    return float((rx * ry).sum() / denominator)


def poisson_d_prime(low: float, high: float) -> float:
    """Signal-to-noise proxy using Poisson variance, not a biological d'."""
    low = float(low)
    high = float(high)
    if low < 0 or high < 0:
        raise ValueError("spike counts must be non-negative")
    denominator = math.sqrt(0.5 * (low + high))
    if denominator == 0.0:
        return 0.0
    return abs(high - low) / denominator


def group_analysis(rows: list[dict], feature: str) -> dict:
    if len(rows) < 2:
        return {
            "distances": [
                row["factors"].get("distance") for row in rows
            ],
            "spike_counts": [
                row["calibration"]["by_feature"][feature]["spikes"]
                for row in rows
            ],
            "spikes_per_neuron": [
                row["calibration"]["by_feature"][feature]["spikes_per_neuron"]
                for row in rows
            ],
            "recruitment_fractions": [
                row["calibration"]["by_feature"][feature][
                    "recruitment_fraction"
                ]
                for row in rows
            ],
            "max_recruitment_fraction": 0.0,
            "saturated": False,
            "responsive": False,
            "eligible": False,
            "ordered": False,
            "weakly_ordered": False,
            "direction": "insufficient_levels",
            "spearman_rho": 0.0,
            "d_prime_proxy": 0.0,
            "dynamic_range": 0,
            "distinct_levels": 0,
            "score_rank": (0, 0.0, 0, 0),
        }
    ordered_rows = sorted(rows, key=lambda row: row["factors"]["distance"])
    distances = [row["factors"]["distance"] for row in ordered_rows]
    counts = [
        row["calibration"]["by_feature"][feature]["spikes"] for row in ordered_rows
    ]
    vector_rates = [
        row["calibration"]["by_feature"][feature]["spikes_per_neuron"]
        for row in ordered_rows
    ]
    recruitment = [
        row["calibration"]["by_feature"][feature]["recruitment_fraction"]
        for row in ordered_rows
    ]
    strict = all(
        counts[i] < counts[i + 1] for i in range(len(counts) - 1)
    ) or all(counts[i] > counts[i + 1] for i in range(len(counts) - 1))
    weak = all(
        counts[i] <= counts[i + 1] for i in range(len(counts) - 1)
    ) or all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
    direction = "flat"
    if counts[-1] > counts[0]:
        direction = "increasing_with_distance"
    elif counts[-1] < counts[0]:
        direction = "decreasing_with_distance"
    saturation_fraction = 0.999
    # Complete saturation means every unit was recruited at every level, not
    # merely that one level recruited the whole population.
    saturated = all(value >= saturation_fraction for value in recruitment)
    responsive = max(counts) >= 1
    return {
        "distances": distances,
        "spike_counts": counts,
        "spikes_per_neuron": vector_rates,
        "recruitment_fractions": recruitment,
        "max_recruitment_fraction": round(max(recruitment), 6),
        "saturated": bool(saturated),
        "responsive": bool(responsive),
        "eligible": bool(responsive and not saturated),
        "ordered": bool(strict),
        "weakly_ordered": bool(weak),
        "direction": direction,
        "spearman_rho": round(spearman(distances, counts), 6),
        "d_prime_proxy": round(
            poisson_d_prime(counts[0], counts[-1]), 6
        ),
        "dynamic_range": int(max(counts) - min(counts)),
        "distinct_levels": int(len(set(counts))),
        "score_rank": (
            1 if strict else 0,
            poisson_d_prime(counts[0], counts[-1]),
            len(set(counts)),
            max(counts) - min(counts),
        ),
    }


def rank_ordered_groups(groups: list[dict]) -> list[dict]:
    eligible = [
        group
        for group in groups
        if group["analysis"]["eligible"] and group["analysis"]["ordered"]
    ]
    return sorted(
        eligible,
        key=lambda group: group["analysis"]["score_rank"],
        reverse=True,
    )


def select_amplitude(
    stage: dict, default: float
) -> tuple[float, list[dict], str]:
    ranked = rank_ordered_groups(stage["groups"])
    if ranked:
        return float(ranked[0]["parameters"]["amplitude_pa"]), ranked, "ordered"
    return float(default), [], "fallback_no_ordered_amplitude"


def select_tuning(
    stage: dict, default_amplitude: float, default_sigma: float
) -> tuple[float, float, list[dict], str]:
    ranked = rank_ordered_groups(stage["groups"])
    if ranked:
        best = ranked[0]["parameters"]
        return (
            float(best["amplitude_pa"]),
            float(best["sigma_fraction"]),
            ranked,
            "ordered",
        )
    return (
        float(default_amplitude),
        float(default_sigma),
        [],
        "fallback_no_ordered_tuning",
    )


def select_population(
    stage: dict, default_size: int
) -> tuple[int, list[dict], str]:
    ranked = rank_ordered_groups(stage["groups"])
    if ranked:
        return (
            int(ranked[0]["parameters"]["population_size"]),
            ranked,
            "ordered",
        )
    return int(default_size), [], "fallback_no_ordered_population"


def seed_summary(stage: dict, feature: str) -> dict:
    rows_by_seed = {}
    for group in stage["groups"]:
        analysis = group.get("analysis") or {}
        if not analysis.get("spike_counts"):
            continue
        seed = int(group["parameters"]["mapping_seed"])
        rows_by_seed[seed] = group
    if not rows_by_seed:
        return {
            "seeds": [],
            "ordered_seeds": [],
            "n_ordered_seeds": 0,
            "passed": False,
            "counts_by_distance": {},
        }
    ordered_seeds = [
        seed for seed, group in rows_by_seed.items() if group["analysis"]["ordered"]
    ]
    distances = next(iter(rows_by_seed.values()))["analysis"]["distances"]
    counts_by_distance = {}
    for index, distance in enumerate(distances):
        values = [
            group["analysis"]["spike_counts"][index]
            for group in rows_by_seed.values()
        ]
        counts_by_distance[str(distance)] = {
            "values": [int(value) for value in values],
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values, ddof=0)), 4),
        }
    return {
        "seeds": [int(seed) for seed in rows_by_seed],
        "ordered_seeds": [int(seed) for seed in ordered_seeds],
        "n_ordered_seeds": len(ordered_seeds),
        "passed": len(ordered_seeds) >= 2,
        "counts_by_distance": counts_by_distance,
    }


def additivity_summary(stage: dict, baseline_spikes: int = 0) -> dict:
    by_kind = {}
    for group in stage["groups"]:
        for row in group["conditions"]:
            kind = row["factors"]["kind"]
            by_kind[kind] = row
    if not {"obstacle", "coin", "both"} <= set(by_kind):
        return {
            "baseline_spikes": int(baseline_spikes),
            "obstacle_spikes": 0,
            "coin_spikes": 0,
            "combined_spikes": 0,
            "obstacle_excess": 0,
            "coin_excess": 0,
            "combined_excess": 0,
            "expected_additive": 0,
            "additivity_index": None,
            "by_feature": {},
            "interpretation": "additivity could not be computed",
        }
    obstacle = int(by_kind["obstacle"]["calibration"]["total_feature_spikes"])
    coin = int(by_kind["coin"]["calibration"]["total_feature_spikes"])
    both = int(by_kind["both"]["calibration"]["total_feature_spikes"])
    obstacle_excess = max(0, obstacle - baseline_spikes)
    coin_excess = max(0, coin - baseline_spikes)
    both_excess = max(0, both - baseline_spikes)
    expected = obstacle_excess + coin_excess
    index = (
        round((both_excess - expected) / expected, 6) if expected > 0 else None
    )
    by_feature = {}
    for feature in ("obstacle_distance", "coin_distance"):
        single = by_kind["obstacle" if feature == "obstacle_distance" else "coin"]
        single_count = int(
            single["calibration"]["by_feature"][feature]["spikes"]
        )
        combined_count = int(
            by_kind["both"]["calibration"]["by_feature"][feature]["spikes"]
        )
        excess = max(0, single_count - baseline_spikes)
        by_feature[feature] = {
            "single_spikes": single_count,
            "combined_spikes": combined_count,
            "excess_single": excess,
            "shift": combined_count - single_count,
        }
    return {
        "baseline_spikes": int(baseline_spikes),
        "obstacle_spikes": obstacle,
        "coin_spikes": coin,
        "combined_spikes": both,
        "obstacle_excess": obstacle_excess,
        "coin_excess": coin_excess,
        "combined_excess": both_excess,
        "expected_additive": expected,
        "additivity_index": index,
        "by_feature": by_feature,
        "interpretation": (
            "index 0 is additive; positive means super-additive; negative "
            "means sub-additive. Network recurrence affects this value."
        ),
    }


def baseline_summary(stage: dict, feature: str) -> dict:
    rows = []
    for group in stage["groups"]:
        analysis = group["analysis"]
        rows.append(
            {
                "baseline": float(group["parameters"]["baseline"]),
                "spike_counts": analysis["spike_counts"],
                "ordered": analysis["ordered"],
                "d_prime_proxy": analysis["d_prime_proxy"],
                "max_recruitment_fraction": analysis["max_recruitment_fraction"],
            }
        )
    return {
        "rows": rows,
        "ordered_baselines": [
            row["baseline"] for row in rows if row["ordered"]
        ],
    }


def transition_summary(stage: dict, feature: str) -> dict:
    rows = []
    for group in stage["groups"]:
        row = group["conditions"][0]
        calibration = row["calibration"]["by_feature"][feature]
        rows.append(
            {
                "transition_ms": float(group["parameters"]["transition_ms"]),
                "spikes": int(calibration["spikes"]),
                "active_neurons": int(calibration["active_neurons"]),
                "first_latency_ms": calibration["latency_ms"]["first_ms"],
                "max_total_current_pa": row["metrics"]["input"][
                    "max_total_current_pa"
                ],
            }
        )
    return {"rows": rows}


def controls_summary(stage: dict) -> dict:
    rows = []
    for group in stage["groups"]:
        for row in group["conditions"]:
            feature = row["metrics"]["active_features"][0]
            calibration = row["calibration"]["by_feature"][feature]
            rows.append(
                {
                    "condition": row["name"],
                    "feature": feature,
                    "amplitude_pa": float(row["factors"]["amplitude_pa"]),
                    "spikes": int(calibration["spikes"]),
                    "active_neurons": int(calibration["active_neurons"]),
                    "recruitment_fraction": calibration["recruitment_fraction"],
                }
            )
    return {"rows": rows}


def decision_criteria(
    *,
    seed_stage: dict,
    amplitude_stage: dict,
    population_stage: dict,
    selection: dict,
    additivity: dict,
    reproducibility: dict | None,
    failures: list,
    performance: dict,
) -> dict:
    seeds = seed_summary(seed_stage, "obstacle_distance")
    selected_amplitude = float(selection["amplitude_pa"])
    amplitude_group = next(
        (
            group
            for group in amplitude_stage["groups"]
            if abs(float(group["parameters"]["amplitude_pa"]) - selected_amplitude)
            < 1e-9
        ),
        None,
    )
    amplitude_analysis = (
        amplitude_group["analysis"] if amplitude_group is not None else {}
    )
    selected_population = int(selection["population_size"])
    population_group = next(
        (
            group
            for group in population_stage["groups"]
            if int(group["parameters"]["population_size"]) == selected_population
        ),
        None,
    )
    population_analysis = (
        population_group["analysis"] if population_group is not None else {}
    )
    additivity_reported = "additivity_index" in additivity
    additivity_defined = additivity.get("additivity_index") is not None
    checks = {
        "no_failures": not failures,
        "reproducibility_passed": bool(
            reproducibility is not None and reproducibility.get("passed")
        ),
        "ordered_in_at_least_two_seeds": bool(seeds["passed"]),
        "responsive_high_level": bool(
            population_analysis.get("responsive")
            or amplitude_analysis.get("responsive")
        ),
        "not_fully_saturated": not bool(
            population_analysis.get("saturated")
            or amplitude_analysis.get("saturated")
        ),
        "avoids_sub_rheobase": selected_amplitude >= 150.0,
        "additivity_reported": additivity_reported,
        "runtime_reported": bool(performance.get("n_conditions_compared", 0) > 0),
    }
    return {
        "checks": checks,
        "additivity_defined": additivity_defined,
        "seed_summary": seeds,
        "selected_amplitude_analysis": amplitude_analysis,
        "selected_population_analysis": population_analysis,
        "passed": all(checks.values()),
    }
