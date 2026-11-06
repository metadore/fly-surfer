"""Phase 3A experiment helpers: setup, runs, metrics, plots and reports.

The module keeps the scientific separation explicit:

* game states are experimenter-defined scenes;
* encoders turn features into dimensionless activations;
* the scheduler turns activations into pA;
* ``BrainSimulator`` produces the only neural activity reported here.

None of the reported firing is measured biological activity.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import psutil
import yaml

from brain.brain_simulator import BrainSimulator
from brain.neural_activity import plot_firing_rates, plot_raster
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from sensory.game_state import (
    CoinState,
    GameState,
    ObstacleState,
    ObstacleType,
    parse_lane,
    parse_obstacle_type,
)
from sensory.input_scheduler import SensoryInputScheduler
from sensory.population_encoder import (
    BooleanPopulation,
    GaussianPopulation,
    LanePopulation,
    build_encoders,
)
from sensory.sensory_mapping import SensoryMapping

FEATURE_FAMILIES = {
    "obstacle": (
        "obstacle_present",
        "obstacle_lane",
        "obstacle_distance",
        "obstacle_type",
    ),
    "train": ("train_present", "train_lane", "train_distance"),
    "coin": ("coin_present", "coin_lane", "coin_distance"),
    "player": ("player_lane", "player_speed"),
    "jumping": ("jumping",),
    "rolling": ("rolling",),
}


class SensorySetup:
    """Validated encoders, mapping and amplitudes for one graph."""

    def __init__(self, config: dict, encoders: dict, mapping: SensoryMapping) -> None:
        self.config = config
        self.encoders = encoders
        self.mapping = mapping
        sensory = config["sensory"]
        self.dt_ms = float(sensory["dt_ms"])
        self.duration_ms = float(sensory["duration_ms"])
        self.transition_ms = float(sensory["transition_ms"])
        self.default_current_pa = float(sensory.get("current_pa_default", 200.0))
        self.amplitudes = {
            feature: float(
                config["features"][feature].get(
                    "current_pa", self.default_current_pa
                )
            )
            for feature in encoders
        }
        self._validate()

    def _validate(self) -> None:
        encoder_features = set(self.encoders)
        mapping_features = set(self.mapping.populations)
        if encoder_features != mapping_features:
            raise ValueError(
                "encoder and mapping feature sets differ: "
                f"encoders={sorted(encoder_features)}, "
                f"mapping={sorted(mapping_features)}"
            )
        for feature, encoder in self.encoders.items():
            expected = encoder.spec.output_size
            actual = self.mapping.size(feature)
            if expected != actual:
                raise ValueError(
                    f"feature {feature!r} encoder has {expected} units but the "
                    f"mapping has {actual} neurons"
                )
            if isinstance(encoder, LanePopulation):
                groups = len(self.mapping.populations[feature].plan.groups)
                if groups != encoder.spec.lanes:
                    raise ValueError(
                        f"feature {feature!r} has {encoder.spec.lanes} lanes but "
                        f"{groups} mapping groups"
                    )

    def info(self) -> dict:
        return {
            "dt_ms": self.dt_ms,
            "duration_ms": self.duration_ms,
            "transition_ms": self.transition_ms,
            "n_features": len(self.encoders),
            "n_stimulated_neurons": int(self.mapping.stimulated_indices().size),
            "features": {
                feature: encoder.info()
                for feature, encoder in self.encoders.items()
            },
            "amplitudes_pa": dict(self.amplitudes),
        }


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"sensory configuration not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("sensory configuration must be a mapping")
    for key in ("sensory", "features", "mapping", "protocols"):
        if key not in config:
            raise ValueError(f"sensory configuration is missing {key!r}")
    return config


def prepare_setup(graph, config: dict) -> SensorySetup:
    encoders = build_encoders(config["features"])
    mapping = SensoryMapping(graph, config["mapping"])
    return SensorySetup(config, encoders, mapping)


def _tag(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", "p")
    return str(value).replace(" ", "_")


def _baseline_state(config: dict) -> GameState:
    return GameState.from_dict(config["protocols"].get("baseline_state", {}))


def _active_for_payload(payload: dict, state: GameState) -> list[str]:
    active: list[str] = []
    if "obstacle" in payload:
        active.extend(FEATURE_FAMILIES["obstacle"])
    if "train" in payload:
        active.extend(FEATURE_FAMILIES["train"])
    if "coin" in payload:
        active.extend(FEATURE_FAMILIES["coin"])
    if "player" in payload:
        active.extend(FEATURE_FAMILIES["player"])
    if state.player.jumping:
        active.append("jumping")
    if state.player.rolling:
        active.append("rolling")
    return list(dict.fromkeys(active))


def condition_specs(config: dict) -> list[dict]:
    """Expand the configured protocols into concrete, reproducible runs."""
    sensory = config["sensory"]
    protocols = config["protocols"]
    baseline = _baseline_state(config)
    specs: list[dict] = []

    single = protocols.get("single_feature", {})
    for value in single.get("obstacle_distance", []):
        state = replace(
            baseline,
            obstacle=ObstacleState(
                present=True,
                lane=baseline.player.lane,
                distance=float(value),
                obstacle_type=ObstacleType.LOW,
            ),
        )
        specs.append(
            {
                "name": f"single_obstacle_distance_{_tag(float(value))}",
                "protocol": "single",
                "description": f"obstacle at distance {value} in the player lane",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": list(FEATURE_FAMILIES["obstacle"]),
            }
        )
    for value in single.get("obstacle_lane", []):
        lane = parse_lane(value)
        state = replace(
            baseline,
            obstacle=ObstacleState(
                present=True,
                lane=lane,
                distance=0.40,
                obstacle_type=ObstacleType.LOW,
            ),
        )
        specs.append(
            {
                "name": f"single_obstacle_lane_{_tag(value)}",
                "protocol": "single",
                "description": f"obstacle at distance 0.40 in lane {value}",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": list(FEATURE_FAMILIES["obstacle"]),
            }
        )
    for value in single.get("coin_distance", []):
        state = replace(
            baseline,
            coin=CoinState(
                present=True, lane=baseline.player.lane, distance=float(value)
            ),
        )
        specs.append(
            {
                "name": f"single_coin_distance_{_tag(float(value))}",
                "protocol": "single",
                "description": f"coin at distance {value} in the player lane",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": list(FEATURE_FAMILIES["coin"]),
            }
        )
    for value in single.get("player_speed", []):
        state = replace(
            baseline, player=replace(baseline.player, speed=float(value))
        )
        specs.append(
            {
                "name": f"single_player_speed_{_tag(float(value))}",
                "protocol": "single",
                "description": f"player speed {value}",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": list(FEATURE_FAMILIES["player"]),
            }
        )
    for value in single.get("jumping", []):
        state = replace(
            baseline, player=replace(baseline.player, jumping=bool(value))
        )
        specs.append(
            {
                "name": f"single_jumping_{_tag(bool(value))}",
                "protocol": "single",
                "description": f"jumping={bool(value)}",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": ["jumping"],
            }
        )
    for value in single.get("rolling", []):
        state = replace(
            baseline, player=replace(baseline.player, rolling=bool(value))
        )
        specs.append(
            {
                "name": f"single_rolling_{_tag(bool(value))}",
                "protocol": "single",
                "description": f"rolling={bool(value)}",
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": ["rolling"],
            }
        )

    for entry in protocols.get("combinations", []):
        payload = entry["state"]
        state = GameState.from_dict(payload)
        specs.append(
            {
                "name": f"combined_{entry['name']}",
                "protocol": "combined",
                "description": entry.get("name", ""),
                "timeline": [(0.0, state)],
                "duration_ms": sensory["duration_ms"],
                "active_features": _active_for_payload(payload, state),
            }
        )

    for name, sequence in protocols.get("sequences", {}).items():
        step_ms = float(sequence["step_ms"])
        distances = sequence["distances"]
        timeline = []
        for index, distance in enumerate(distances):
            time_ms = index * step_ms
            if name.startswith("obstacle"):
                state = replace(
                    baseline,
                    obstacle=(
                        ObstacleState(present=False)
                        if distance is None
                        else ObstacleState(
                            present=True,
                            lane=parse_lane(sequence["lane"]),
                            distance=float(distance),
                            obstacle_type=parse_obstacle_type(
                                sequence.get("obstacle_type", "low")
                            ),
                        )
                    ),
                    time_ms=time_ms,
                )
                active = list(FEATURE_FAMILIES["obstacle"])
            elif name.startswith("coin"):
                state = replace(
                    baseline,
                    coin=(
                        CoinState(present=False)
                        if distance is None
                        else CoinState(
                            present=True,
                            lane=parse_lane(sequence["lane"]),
                            distance=float(distance),
                        )
                    ),
                    time_ms=time_ms,
                )
                active = list(FEATURE_FAMILIES["coin"])
            else:
                raise ValueError(f"unknown sequence protocol {name!r}")
            timeline.append((time_ms, state))
        specs.append(
            {
                "name": f"sequence_{name}",
                "protocol": "sequence",
                "description": f"{name} over {len(distances)} states",
                "timeline": timeline,
                "duration_ms": step_ms * len(distances),
                "active_features": active,
            }
        )
    if not specs:
        raise ValueError("no conditions were generated from the protocols")
    return specs


def run_condition(
    setup: SensorySetup,
    graph,
    neuron_params: LIFParameters,
    synapse_params: SynapseParameters,
    spec: dict,
    *,
    seed: int | None = None,
    progress: bool = False,
) -> dict:
    """Run one condition and return metrics, recorder and scheduler."""
    sensory = setup.config["sensory"]
    seed = int(sensory["seed"] if seed is None else seed)
    scheduler = SensoryInputScheduler(
        setup.mapping,
        setup.encoders,
        spec["timeline"],
        dt_ms=setup.dt_ms,
        duration_ms=float(spec["duration_ms"]),
        current_pa=setup.amplitudes,
        transition_ms=setup.transition_ms,
        active_features=spec["active_features"],
    )
    simulator = BrainSimulator(
        graph,
        neuron_params,
        synapse_params,
        dt_ms=setup.dt_ms,
        duration_ms=float(spec["duration_ms"]),
        seed=seed,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        stimulus=None,
        input_schedule=scheduler,
        max_recorded_spikes=int(sensory["max_recorded_spikes"]),
        progress_interval_ms=float(sensory["progress_interval_ms"]),
        diagnostics_interval_steps=int(sensory["diagnostics_interval_steps"]),
    )
    process = psutil.Process()
    rss_before = process.memory_info().rss
    started = time.perf_counter()
    result = simulator.run(progress=progress)
    wall = time.perf_counter() - started
    rss_after = process.memory_info().rss

    counts = result.recorder.spike_counts()
    per_feature = {
        feature: int(counts[setup.mapping.indices(feature)].sum())
        for feature in spec["active_features"]
    }
    memory = simulator.memory_breakdown()
    memory.update(
        {
            "rss_before_run_mb": round(rss_before / 1024**2, 3),
            "rss_after_run_mb": round(rss_after / 1024**2, 3),
            "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
            "sensory_arrays_bytes": int(scheduler.memory_bytes),
        }
    )
    metrics = {
        "condition": spec["name"],
        "protocol": spec["protocol"],
        "description": spec["description"],
        "duration_ms": float(spec["duration_ms"]),
        "dt_ms": setup.dt_ms,
        "n_steps": result.n_steps,
        "seed": seed,
        "active_features": list(spec["active_features"]),
        "n_stimulated_neurons": int(scheduler.stimulated_indices.size),
        "activity": result.summary["activity"],
        "activity_by_stimulation": result.summary["activity_by_stimulation"],
        "stimulated_spikes_by_feature": per_feature,
        "synapses": result.summary["synapses"],
        "diagnostics": result.summary["diagnostics"],
        "simulation": {
            **result.summary["simulation"],
            "wall_runtime_s": round(wall, 4),
            "steps_per_second_wall": round(result.n_steps / wall, 2),
        },
        "memory": memory,
        "input": scheduler.input_statistics(),
    }
    return {
        "metrics": metrics,
        "result": result,
        "scheduler": scheduler,
        "simulator": simulator,
    }


def write_json(path: str | Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_tuning_curves(encoders: dict, path: str | Path) -> Path:
    plt = _pyplot()
    gaussian = [
        (name, encoder)
        for name, encoder in encoders.items()
        if isinstance(encoder, GaussianPopulation)
    ][:4]
    lane = next(
        (encoder for encoder in encoders.values() if isinstance(encoder, LanePopulation)),
        None,
    )
    boolean = next(
        (encoder for encoder in encoders.values() if isinstance(encoder, BooleanPopulation)),
        None,
    )
    figure, axes = plt.subplots(3, 2, figsize=(12, 11))
    axes = axes.ravel()
    for axis, (name, encoder) in zip(axes, gaussian):
        values = np.linspace(
            encoder.spec.minimum, encoder.spec.maximum, 120
        )
        curves = encoder.tuning_curves(values)
        axis.plot(values, curves, color="#8faadc", linewidth=0.8)
        axis.plot(
            values, curves.max(axis=1), color="#1f4e79", linewidth=2.0,
            label="population peak",
        )
        axis.set_title(f"{name} (n={encoder.spec.output_size})")
        axis.set_xlabel("Feature value (normalised)")
        axis.set_ylabel("Activation (dimensionless)")
        axis.grid(alpha=0.2, linewidth=0.4)
        axis.legend(frameon=False, fontsize=8)
    next_axis = len(gaussian)
    if lane is not None:
        axis = axes[next_axis]
        matrix = np.stack(
            [lane.encode(code) for code in range(lane.spec.lanes)]
        )
        axis.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=1)
        axis.set_title("Lane coding (one sub-population per lane)")
        axis.set_xlabel("Neuron index within lane populations")
        axis.set_ylabel("Lane code")
        axis.set_yticks(range(lane.spec.lanes))
        next_axis += 1
    if boolean is not None:
        axis = axes[next_axis]
        axis.bar(
            [0, 1],
            [float(boolean.encode(False).mean()), float(boolean.encode(True).mean())],
            color=["#b4c6e7", "#1f4e79"],
        )
        axis.set_xticks([0, 1], ["inactive", "active"])
        axis.set_title("Boolean state coding")
        axis.set_ylabel("Activation (dimensionless)")
        next_axis += 1
    for axis in axes[next_axis:]:
        axis.axis("off")
    figure.suptitle("Phase 3A population tuning (configured assumptions)", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def plot_input_activity(
    scheduler: SensoryInputScheduler, path: str | Path, title: str
) -> Path:
    plt = _pyplot()
    steps = int(round(scheduler.duration_ms / scheduler.dt_ms))
    times = np.arange(steps) * scheduler.dt_ms
    features = [
        feature
        for feature in scheduler.encoders
        if feature in set(scheduler.active_features)
    ]
    matrix = np.zeros((len(features), steps))
    for step in range(steps):
        currents = scheduler.feature_currents_at(step * scheduler.dt_ms)
        matrix[:, step] = [currents[feature] for feature in features]
    figure, axis = plt.subplots(figsize=(12, 5.5))
    image = axis.imshow(
        matrix,
        aspect="auto",
        origin="lower",
        extent=(0, scheduler.duration_ms, -0.5, len(features) - 0.5),
        cmap="magma",
    )
    axis.set_yticks(range(len(features)), features, fontsize=8)
    axis.set_xlabel("Time (ms)")
    axis.set_ylabel("Sensory feature population")
    axis.set_title(title)
    figure.colorbar(image, ax=axis, label="Scheduled current per feature (pA)")
    figure.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def plot_condition_comparison(
    rows: list[dict],
    key: str,
    path: str | Path,
    title: str,
    ylabel: str,
) -> Path:
    plt = _pyplot()
    names = [row["metrics"]["condition"] for row in rows]
    values = [row["metrics"]["activity"].get(key) for row in rows]
    if any(value is None for value in values):
        raise KeyError(f"{key!r} is not an activity metric")
    figure, axis = plt.subplots(figsize=(max(10, 0.55 * len(names)), 5.5))
    axis.bar(range(len(names)), values, color="#2e75b6")
    axis.set_xticks(range(len(names)), names, rotation=60, ha="right", fontsize=8)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.25, linewidth=0.4)
    figure.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def plot_representative_activity(
    run: dict, out_dir: str | Path, title: str
) -> dict:
    out_dir = Path(out_dir)
    recorder = run["result"].recorder
    metrics = run["metrics"]
    raster = plot_raster(
        recorder,
        out_dir / f"raster_{metrics['condition']}.png",
        metrics["duration_ms"],
        title=title,
    )
    rates = plot_firing_rates(
        recorder,
        out_dir / f"firing_rates_{metrics['condition']}.png",
        metrics["duration_ms"],
        title=title,
    )
    return {"raster": str(raster), "firing_rates": str(rates)}


def environment_info() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "executable": sys.executable,
    }


def write_report(summary: dict, path: str | Path) -> Path:
    """Write the Phase 3A report from measured results."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conditions = summary["conditions"]
    performance = summary["performance"]
    mapping = summary["mapping"]
    reproducibility = summary.get("reproducibility") or {}
    lines = [
        "# Phase 3A — sensory encoding report",
        "",
        f"Generated {summary['generated_at_utc']} from the configuration "
        f"`{summary['config_path']}`.",
        "",
        "## Scientific status",
        "",
        "This report contains simulated activity only. Game states are "
        "experimenter-defined scenes, Gaussian/lane/boolean coding is a "
        "computational choice, and the mapped neurons are drawn from predicted "
        "FlyWire annotations. No pathway here is anatomically verified and no "
        "firing pattern is a biological recording.",
        "",
        "## Setup",
        "",
        f"- Graph: {summary['graph']['n_nodes']:,} neurons, "
        f"{summary['graph']['n_edges']:,} directed edges, "
        f"{summary['graph']['n_synapses']:,} summed synapses.",
        f"- Simulation: dt {summary['setup']['dt_ms']} ms, "
        f"{summary['setup']['n_features']} features, "
        f"{summary['setup']['n_stimulated_neurons']} mapped neurons, "
        f"{summary['setup']['transition_ms']} ms transitions.",
        f"- Seed: {summary['seed']}.",
        "",
        "## Mapping",
        "",
        "| Feature | Neurons | Pool(s) |",
        "|---|---:|---|",
    ]
    for feature, population in mapping["populations"].items():
        pools = sorted({group["pool"] for group in population["groups"].values()})
        lines.append(
            f"| `{feature}` | {population['selected_size']} | "
            f"{', '.join(f'`{pool}`' for pool in pools)} |"
        )
    lines += [
        "",
        "All populations are experimental input populations drawn from predicted "
        "annotations. See `docs/PHASE_3_SENSORY_ENCODING.md` and the per-feature "
        "root IDs in `results/mapping_report.json`.",
        "",
        "## Protocol results",
        "",
        "| Condition | Protocol | Active features | Stimulated | Spikes | "
        "Active | Mean Hz | Max Hz | Runtime s |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in conditions:
        metrics = row["metrics"]
        activity = metrics["activity"]
        lines.append(
            f"| `{metrics['condition']}` | {metrics['protocol']} | "
            f"{', '.join(metrics['active_features'])} | "
            f"{metrics['n_stimulated_neurons']} | {activity['n_spikes']:,} | "
            f"{activity['active_neurons']:,} | "
            f"{activity['mean_rate_hz']:.3f} | "
            f"{activity['rate_percentiles_hz']['100']:.1f} | "
            f"{metrics['simulation']['wall_runtime_s']:.3f} |"
        )

    sweep_prefixes = (
        "single_obstacle_distance_",
        "single_coin_distance_",
        "single_obstacle_lane_",
        "single_player_speed_",
    )
    sweeps: dict[str, list[tuple[str, int]]] = {}
    for row in conditions:
        name = row["metrics"]["condition"]
        for prefix in sweep_prefixes:
            if name.startswith(prefix):
                sweeps.setdefault(prefix, []).append(
                    (name, int(row["metrics"]["activity"]["n_spikes"]))
                )
    sweep_counts = [
        [count for _, count in values]
        for values in sweeps.values()
        if len(values) >= 2
    ]
    lines += [
        "",
        "## Observed response structure",
        "",
    ]
    for prefix, values in sweeps.items():
        if len(values) < 2:
            continue
        lines.append(
            f"- `{prefix}`: "
            + ", ".join(f"`{name}`={count}" for name, count in values)
            + "."
        )
    if sweep_counts:
        spread = max(max(counts) - min(counts) for counts in sweep_counts)
        lines += [
            "",
            f"Across these single-feature sweeps the spike count changed by at "
            f"most {spread} spikes. With a 200 pA drive and a 150 pA rheobase, "
            "a neuron tuned within a small fraction of the stimulus range can "
            "still cross threshold, so this readout is threshold-dominated. "
            "Near-identical counts do not demonstrate graded coding, and "
            "different counts would not demonstrate biological coding either.",
        ]
    else:
        lines += ["No repeated single-feature sweeps were available."]
    lines += [
        "",
        "## Performance",
        "",
        f"- Baseline (no sensory schedule): "
        f"{performance['baseline_runtime_s']:.3f} s wall, "
        f"{performance['baseline_steps_per_second']:.1f} steps/s.",
        f"- Sensory condition mean: "
        f"{performance['sensory_mean_runtime_s']:.3f} s wall, "
        f"{performance['sensory_mean_steps_per_second']:.1f} steps/s.",
        f"- Additional runtime per condition: "
        f"{performance['added_runtime_s']:.3f} s "
        f"({performance['added_runtime_fraction'] * 100:.2f}% of baseline).",
        f"- Retained simulation arrays: "
        f"{performance['retained_arrays_mb']:.2f} MB; "
        f"mean RSS change during a run: "
        f"{performance['mean_rss_delta_mb']:.2f} MB.",
        "",
        "## Reproducibility",
        "",
    ]
    if reproducibility:
        lines += [
            f"- Compared condition: `{reproducibility['condition']}`.",
            f"- Separate processes: {reproducibility['processes']}.",
            f"- Input signature equal: {reproducibility['input_equal']}.",
            f"- Spike signature equal: {reproducibility['spikes_equal']}.",
        ]
        if reproducibility.get("spike_count") is not None:
            lines.append(
                f"- Spike count: {reproducibility['spike_count']:,} in each run."
            )
    else:
        lines.append("- Reproducibility check was not run.")
    peak_current = max(float(value) for value in summary["setup"]["amplitudes_pa"].values())
    lines += [
        "",
        "## Limitations",
        "",
        "- Gaussian population coding is an experimental computational choice, "
        "not evidence for the fly's sensory code.",
        "- Mapped neurons carry predicted annotations; feature assignment is "
        "artificial and may target cells that do not process that feature.",
        f"- A peak drive of {peak_current:.0f} pA is a model calibration above "
        "the LIF rheobase, not a measured current.",
        "- The connectome is a female adult FAFB brain without a ventral nerve "
        "cord; no motor pathway or behaviour is decoded in Phase 3A.",
        "- One seed and one set of amplitudes were used; sensitivity to tuning "
        "width, population size and current amplitude is not yet characterised.",
        "",
        "## Next step",
        "",
        "Phase 3B should add screenshot-based visual perception as a separate "
        "layer, so perception errors can be measured independently of the "
        "neural encoding studied here.",
        "",
    ]
    path.write_text("\n".join(line for line in lines if line is not None), encoding="utf-8")
    return path
