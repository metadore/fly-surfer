"""P3-T2: same-graph causal-control infrastructure and preregistered protocol.

The scientific question is causal: does external sensory current produce
neural activity beyond the directly stimulated sensory neurons, and is any
such activity attributable to the visual schedule rather than to the player
defaults that every Phase 3A-compatible ``GameState`` carries?

Four conditions share one graph, one duration, one timestep, one seed and one
initial state. Only the external current differs::

    C0  input_schedule=None; no external current
    C1  100 neutral TemporalFrames at 30 fps; player-default features only
    C2  the cached visual frames of C3; non-player features only
    C3  the cached visual frames; all fourteen features

Every reported count is partitioned two ways: against the fixed reference set
R (all 138 mapped sensory neurons) and against the condition-local stimulated
set A_c. Comparing only A_c between conditions would hide the fact that the
stimulated set itself differs, so both partitions are always reported.

The runner is infrastructure. It executes the simulator and records numbers;
it does not select actions, modify the connectome, change the LIF or synapse
model, or change scheduler semantics. It also does not decide what the numbers
mean: the preregistered analysis and its limitations live in
``docs/PHASE_3C_CAUSAL_CONTROL_PROTOCOL.md``.

The frozen input is a cache of ``TemporalFrame`` payloads produced once by the
existing Phase 3B.2C chain. Its canonical digest must equal the archived
``temporal_sha256``, and the C3 scheduler built from it must reproduce the
archived ``scheduler_sha256``; otherwise the run is invalid. Smoke mode
truncates the same input to a short window and never compares against the
full-duration archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neural_activity import SpikeCapacityExceeded  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from perception.config import ClassRole  # noqa: E402
from perception.temporal import Lifecycle, LifecycleEvent, TemporalFrame  # noqa: E402
from sensory.game_state import (  # noqa: E402
    CoinState,
    GameState,
    ObstacleState,
    PlayerState,
    TrainState,
)
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402
from sensory.temporal_scheduler import (  # noqa: E402
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "causal_control_config.yaml"
CACHE_SCHEMA = "p3_t2_visual_frame_cache_v1"
MANIFEST_SCHEMA = "p3_t2_visual_frame_cache_manifest_v1"

FEATURES = (
    "player_lane",
    "player_speed",
    "jumping",
    "rolling",
    "obstacle_present",
    "obstacle_lane",
    "obstacle_distance",
    "obstacle_type",
    "train_present",
    "train_lane",
    "train_distance",
    "coin_present",
    "coin_lane",
    "coin_distance",
)

REPRODUCIBLE_KEYS = (
    "spike_counts_sha256",
    "activity_summary_sha256",
    "current_trace_sha256",
    "scheduler_signature_sha256",
    "cache_frames_digest",
    "spikes_total",
    "first_spike_ms",
    "last_spike_ms",
)

LIMITATIONS = [
    "Spikes are model output under configured assumptions, not measured "
    "biological activity. The connectome is fixed and no plasticity is used.",
    "The mapped neurons are experimental input populations drawn from "
    "predicted FlyWire annotations, not an identified sensory pathway.",
    "Distance and lane are image geometry, not game measurements.",
    "C0 with zero background, zero noise and a resting initial potential is "
    "the no-input floor; any activity in C1-C3 is driven by injected current "
    "and its synaptic consequences.",
    "One deterministic run per condition is executed per repeat. There is no "
    "sampling distribution across seeds, so the preregistered analysis is "
    "descriptive; no p-value is computed and no significance is claimed.",
    "Subtracting conditions does not identify a linear contribution: the "
    "network is recurrent and nonlinear, so C3-C0 is a whole-schedule "
    "contrast, not a sum of C1-C0 and C2-C1.",
    "No action is selected anywhere in this experiment.",
]


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_json(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_sha(value, name: str) -> str:
    _require(
        isinstance(value, str) and len(value) == 64
        and all(char in "0123456789abcdef" for char in value),
        f"{name} must be a lowercase SHA-256 hex digest",
    )
    return value


def _positive_int(value, name: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        f"{name} must be a positive integer",
    )
    return value


@dataclass(frozen=True)
class CausalControlConfig:
    """Validated P3-T2 configuration; every field comes from the YAML file."""

    source_path: Path
    version: str
    reference: dict
    player_features: tuple[str, ...]
    non_player_features: tuple[str, ...]
    feature_neurons: dict[str, int]
    conditions: dict[str, dict]
    cache: dict
    archived: dict
    in_process_repeats: int
    subprocess_conditions: tuple[str, ...]
    progress_interval_ms: float
    diagnostics_interval_steps: int

    @property
    def all_features(self) -> tuple[str, ...]:
        return self.player_features + self.non_player_features

    def condition(self, name: str) -> "ConditionSpec":
        if name not in self.conditions:
            raise ValueError(f"unknown condition {name!r}")
        payload = self.conditions[name]
        active = payload["active_features"]
        return ConditionSpec(
            name=name,
            description=str(payload["description"]).strip(),
            frame_source=str(payload["frame_source"]),
            active_features=(
                None if active is None else tuple(str(item) for item in active)
            ),
        )

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "CausalControlConfig":
        raw = _load_yaml(path)
        version = raw.get("version")
        _require(
            isinstance(version, str) and bool(version),
            "version must be a non-empty string",
        )
        reference = raw.get("reference")
        _require(isinstance(reference, dict), "reference must be a mapping")
        for key in (
            "connectome_sha256",
            "readme_sha256",
            "sensory_config_sha256",
            "simulation_config_sha256",
            "neuron_config_sha256",
            "perception_config_sha256",
            "detector_config_sha256",
            "split_manifest_sha256",
            "detector_model_sha256",
        ):
            _require_sha(reference.get(key), f"reference.{key}")
        for key in ("mapping_seed", "simulation_seed", "n_steps", "n_features"):
            _positive_int(reference.get(key), f"reference.{key}")
        for key in (
            "dt_ms",
            "duration_ms",
            "initial_potential_mv",
            "threshold_mv",
            "minimum_potential_mv",
            "reset_potential_mv",
            "bin_ms",
            "fps",
            "n_frames",
        ):
            _require(
                isinstance(reference.get(key), (int, float))
                and not isinstance(reference.get(key), bool),
                f"reference.{key} must be a number",
            )
        _require(
            float(reference["background_current_pa"]) == 0.0,
            "background_current_pa must be 0.0 for this experiment",
        )
        _require(
            float(reference["noise_std_pa"]) == 0.0,
            "noise_std_pa must be 0.0 for this experiment",
        )
        _require(
            reference["n_features"] == len(FEATURES),
            f"n_features must be {len(FEATURES)}",
        )
        _require(
            math.isclose(
                float(reference["duration_ms"]),
                int(reference["n_steps"]) * float(reference["dt_ms"]),
                rel_tol=0.0,
                abs_tol=1e-6,
            ),
            "duration_ms must equal n_steps * dt_ms",
        )

        sets = raw.get("reference_sets")
        _require(isinstance(sets, dict), "reference_sets must be a mapping")
        player = tuple(str(item) for item in sets.get("player_features", ()))
        non_player = tuple(str(item) for item in sets.get("non_player_features", ()))
        _require(
            set(player) | set(non_player) == set(FEATURES),
            "player and non-player features must cover exactly the 14 features",
        )
        _require(
            not set(player) & set(non_player),
            "player and non-player features must be disjoint",
        )
        _require(len(player) == 4, "there are exactly four player fields")
        _require(
            len(non_player) == 10,
            "there are exactly ten non-player features (not eleven)",
        )
        _require(
            player + non_player == FEATURES,
            "reference_sets order must match the encoder order in "
            "configs/sensory_config.yaml",
        )
        feature_neurons = {
            str(name): _positive_int(count, f"feature_neuron_counts[{name!r}]")
            for name, count in reference["feature_neuron_counts"].items()
        }
        _require(
            set(feature_neurons) == set(FEATURES),
            "feature_neuron_counts must cover exactly the 14 features",
        )
        _require(
            sum(feature_neurons.values()) == int(reference["n_reference_neurons"]),
            "per-feature neuron counts must sum to n_reference_neurons",
        )
        _require(
            sum(feature_neurons[name] for name in player)
            == int(reference["n_player_neurons"]),
            "player neuron counts must sum to n_player_neurons",
        )
        _require(
            sum(feature_neurons[name] for name in non_player)
            == int(reference["n_non_player_neurons"]),
            "non-player neuron counts must sum to n_non_player_neurons",
        )
        expected_neutral = reference.get("expected_neutral_current_pa")
        _require(
            isinstance(expected_neutral, dict)
            and set(expected_neutral) == {"player_lane", "player_speed"},
            "expected_neutral_current_pa must define player_lane and player_speed",
        )

        conditions_raw = raw.get("conditions")
        _require(isinstance(conditions_raw, dict), "conditions must be a mapping")
        _require(
            list(conditions_raw) == ["C0", "C1", "C2", "C3"],
            "conditions must be C0, C1, C2, C3 in order",
        )
        conditions: dict[str, dict] = {}
        for name, payload in conditions_raw.items():
            _require(isinstance(payload, dict), f"conditions.{name} must be a mapping")
            source = payload.get("frame_source")
            _require(
                source in ("none", "neutral", "cached"),
                f"conditions.{name}.frame_source is invalid",
            )
            active = payload.get("active_features", "missing")
            _require(
                active is None or isinstance(active, list),
                f"conditions.{name}.active_features must be a list or null",
            )
            if active is not None:
                _require(
                    set(active) <= set(FEATURES),
                    f"conditions.{name}.active_features has unknown features",
                )
            if source == "none":
                _require(
                    active == [],
                    f"conditions.{name} has no schedule and must activate nothing",
                )
            else:
                _require(
                    active is None or len(active) > 0,
                    f"conditions.{name} must activate at least one feature",
                )
            conditions[name] = {
                "description": payload.get("description", ""),
                "frame_source": source,
                "active_features": active,
            }
        _require(
            conditions["C1"]["frame_source"] == "neutral"
            and conditions["C1"]["active_features"] == list(player),
            "C1 must use neutral frames with exactly the player features",
        )
        _require(
            conditions["C2"]["frame_source"] == "cached"
            and conditions["C2"]["active_features"] == list(non_player),
            "C2 must use cached frames with exactly the non-player features",
        )
        _require(
            conditions["C3"]["frame_source"] == "cached"
            and conditions["C3"]["active_features"] is None,
            "C3 must use cached frames with all features",
        )

        cache = raw.get("cached_frames")
        _require(isinstance(cache, dict), "cached_frames must be a mapping")
        for key in ("path", "manifest"):
            _require(
                isinstance(cache.get(key), str) and bool(cache.get(key)),
                f"cached_frames.{key} must be a path",
            )
        _require(
            int(cache["frame_end"]) - int(cache["frame_start"]) + 1
            == int(reference["n_frames"]),
            "cached frame range must match n_frames",
        )

        archived = raw.get("archived")
        _require(isinstance(archived, dict), "archived must be a mapping")
        for key in (
            "temporal_sha256",
            "detections_sha256",
            "scheduler_sha256",
            "spike_counts_sha256",
        ):
            _require_sha(archived.get(key), f"archived.{key}")

        reproducibility = raw.get("reproducibility")
        _require(
            isinstance(reproducibility, dict),
            "reproducibility must be a mapping",
        )
        repeats = _positive_int(
            reproducibility.get("in_process_repeats"),
            "reproducibility.in_process_repeats",
        )
        _require(repeats >= 2, "every condition must run at least twice")
        subprocess_conditions = tuple(
            str(item)
            for item in reproducibility.get("subprocess_conditions", ())
        )
        _require(
            set(subprocess_conditions) <= set(conditions),
            "subprocess_conditions must name existing conditions",
        )
        sensory = _load_yaml(PROJECT_ROOT / reference["sensory_config"])["sensory"]
        progress_interval_ms = float(sensory["progress_interval_ms"])
        diagnostics_interval_steps = _positive_int(
            sensory["diagnostics_interval_steps"],
            "sensory.diagnostics_interval_steps",
        )

        return cls(
            source_path=Path(path),
            version=version,
            reference=reference,
            player_features=player,
            non_player_features=non_player,
            feature_neurons=feature_neurons,
            conditions=conditions,
            cache=cache,
            archived=archived,
            in_process_repeats=repeats,
            subprocess_conditions=subprocess_conditions,
            progress_interval_ms=progress_interval_ms,
            diagnostics_interval_steps=diagnostics_interval_steps,
        )


@dataclass(frozen=True)
class ConditionSpec:
    name: str
    description: str
    frame_source: str
    active_features: tuple[str, ...] | None

    @property
    def label(self) -> str:
        if self.active_features is None:
            return "all features"
        return f"{len(self.active_features)} active features"


# --------------------------------------------------------------------------
# cached visual frames
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CausalFrameCache:
    path: Path
    file_sha256: str
    frames_digest: str
    frames: tuple[TemporalFrame, ...]
    scheduler_signature_sha256: str | None
    manifest: dict

    @property
    def last_time_ms(self) -> float:
        return float(self.frames[-1].time_ms)

    @property
    def n_pulse_events(self) -> int:
        return sum(1 for frame in self.frames for event in frame.events if event.is_pulse)


def neutral_frames(n_frames: int, fps: float) -> tuple[TemporalFrame, ...]:
    """The C1 input: neutral GameStates at the configured frame rate."""
    _require(n_frames > 0, "n_frames must be positive")
    _require(fps > 0, "fps must be positive")
    interval = 1000.0 / float(fps)
    frames = []
    for index in range(n_frames):
        time_ms = index * interval
        state = GameState.neutral(time_ms=time_ms)
        frames.append(
            TemporalFrame(
                frame_index=index,
                frame_id=f"p3t2-neutral-{index:04d}",
                timestamp_ms=time_ms,
                time_ms=time_ms,
                dt_ms=interval,
                is_gap=False,
                tracks=(),
                events=(),
                features=dict(state.features()),
                state=state,
                unrepresented_tracks=0,
            )
        )
    return tuple(frames)


def _state_from_features(features: dict, time_ms: float) -> GameState:
    """Invert ``GameState.features()`` exactly, or fail loudly."""
    _require(
        set(features) == set(FEATURES),
        "cached game state must carry exactly the 14 features",
    )
    player = PlayerState(
        lane=features["player_lane"],
        speed=features["player_speed"],
        jumping=bool(features["jumping"]),
        rolling=bool(features["rolling"]),
    )

    def absent(prefix: str) -> None:
        for field in ("lane", "distance"):
            _require(
                features[f"{prefix}_{field}"] is None,
                f"an absent {prefix} must not carry {field}",
            )
        if prefix == "obstacle":
            _require(
                features["obstacle_type"] is None,
                "an absent obstacle must not carry obstacle_type",
            )

    if bool(features["obstacle_present"]):
        obstacle = ObstacleState(
            present=True,
            lane=features["obstacle_lane"],
            distance=features["obstacle_distance"],
            obstacle_type=features["obstacle_type"],
        )
    else:
        absent("obstacle")
        obstacle = None
    if bool(features["train_present"]):
        train = TrainState(
            present=True,
            lane=features["train_lane"],
            distance=features["train_distance"],
        )
    else:
        absent("train")
        train = None
    if bool(features["coin_present"]):
        coin = CoinState(
            present=True,
            lane=features["coin_lane"],
            distance=features["coin_distance"],
        )
    else:
        absent("coin")
        coin = None
    state = GameState(
        player=player,
        obstacle=obstacle,
        train=train,
        coin=coin,
        time_ms=time_ms,
    )
    _require(
        state.features() == features,
        "cached game state does not round-trip through GameState.features()",
    )
    return state


def _event_from_dict(payload: dict) -> LifecycleEvent:
    return LifecycleEvent(
        track_id=int(payload["track_id"]),
        frame_index=int(payload["frame_index"]),
        timestamp_ms=payload["timestamp_ms"],
        time_ms=float(payload["time_ms"]),
        event=Lifecycle(payload["event"]),
        class_id=int(payload["class_id"]),
        class_name=str(payload["class_name"]),
        role=ClassRole(payload["role"]),
        lane=payload["lane"],
        confidence=float(payload["confidence"]),
        distance_proxy=payload["distance_proxy"],
        feature_values=dict(payload["feature_values"]),
        is_pulse=bool(payload["is_pulse"]),
        detail=str(payload["detail"]),
    )


def _frame_from_dict(payload: dict) -> TemporalFrame:
    state = _state_from_features(
        payload["game_state"]["features"], payload["game_state"]["time_ms"]
    )
    _require(
        dict(payload["features"]) == state.features(),
        "cached frame features disagree with its game state",
    )
    return TemporalFrame(
        frame_index=int(payload["frame_index"]),
        frame_id=payload["frame_id"],
        timestamp_ms=payload["timestamp_ms"],
        time_ms=float(payload["time_ms"]),
        dt_ms=float(payload["dt_ms"]),
        is_gap=bool(payload["is_gap"]),
        tracks=(),
        events=tuple(_event_from_dict(item) for item in payload["events"]),
        features=dict(payload["features"]),
        state=state,
        unrepresented_tracks=int(payload["unrepresented_tracks"]),
        notes=tuple(payload["notes"]),
    )


def load_cache(
    config: CausalControlConfig,
    path: Path | None = None,
    manifest_path: Path | None = None,
) -> CausalFrameCache:
    cache_path = Path(path) if path is not None else PROJECT_ROOT / config.cache["path"]
    if manifest_path is not None:
        manifest_file = Path(manifest_path)
    elif path is not None:
        manifest_file = cache_path.with_name(cache_path.stem + ".manifest.json")
    else:
        manifest_file = PROJECT_ROOT / config.cache["manifest"]
    _require(cache_path.is_file(), f"cached frames not found: {cache_path}")
    _require(
        manifest_file.is_file(), f"cache manifest not found: {manifest_file}"
    )
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    _require(
        manifest.get("schema") == MANIFEST_SCHEMA,
        "cache manifest schema mismatch",
    )
    file_sha = _sha256(cache_path)
    _require(
        file_sha == manifest["cache_sha256"],
        "cached frame file hash does not match its manifest",
    )
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    _require(payload.get("schema") == CACHE_SCHEMA, "cache schema mismatch")
    frames_digest = _digest_json(payload["frames"])
    _require(
        frames_digest == manifest["frames_digest"],
        "cached frame digest does not match its manifest",
    )
    frames = tuple(_frame_from_dict(item) for item in payload["frames"])
    _require(
        len(frames) == int(manifest["n_frames"]),
        "cached frame count does not match its manifest",
    )
    times = [frame.time_ms for frame in frames]
    _require(
        all(second > first for first, second in zip(times, times[1:])),
        "cached frame times must increase strictly",
    )
    _require(
        math.isclose(times[0], float(manifest["first_frame_ms"]), abs_tol=1e-9)
        and math.isclose(times[-1], float(manifest["last_frame_ms"]), abs_tol=1e-9),
        "cached frame times do not match its manifest",
    )
    return CausalFrameCache(
        path=cache_path,
        file_sha256=file_sha,
        frames_digest=frames_digest,
        frames=frames,
        scheduler_signature_sha256=manifest.get("scheduler_signature_sha256"),
        manifest=manifest,
    )


# --------------------------------------------------------------------------
# scheduler, current audit and partitions
# --------------------------------------------------------------------------


def scheduler_signature_digest(scheduler: TemporalActivationScheduler | None) -> str | None:
    """The Phase 3B.2C signature digest, byte-for-byte."""
    if scheduler is None:
        return None
    signature = scheduler.signature()
    digest = hashlib.sha256()
    for key in (
        "indices",
        "values",
        "starts",
        "frame_values",
        "frame_times",
        "pulse_values",
        "pulse_onsets",
    ):
        if key in signature:
            digest.update(np.ascontiguousarray(signature[key]).tobytes())
            digest.update(b"|")
    return digest.hexdigest()


def pulse_windows(
    scheduler: TemporalActivationScheduler | None,
) -> tuple[tuple[float, float], ...]:
    """Half-open windows [onset, onset + pulse_decay_ms) for each pulse event."""
    if scheduler is None:
        return ()
    onsets = np.asarray(scheduler.signature()["pulse_onsets"], dtype=np.float64)
    decay = float(scheduler.config.pulse_decay_ms)
    return tuple((float(onset), float(onset) + decay) for onset in onsets)


def resolve_frames(
    spec: ConditionSpec,
    config: CausalControlConfig,
    cache: CausalFrameCache | None,
    *,
    smoke_ms: float | None,
) -> tuple[TemporalFrame, ...]:
    if spec.frame_source == "none":
        return ()
    if spec.frame_source == "neutral":
        frames = neutral_frames(
            int(config.reference["n_frames"]), float(config.reference["fps"])
        )
    else:
        _require(cache is not None, f"{spec.name} requires the cached frames")
        frames = cache.frames
    if smoke_ms is not None:
        frames = tuple(frame for frame in frames if frame.time_ms < smoke_ms)
        _require(frames, f"{spec.name} has no frames inside the smoke window")
    return frames


def build_scheduler(
    spec: ConditionSpec,
    setup,
    frames: tuple[TemporalFrame, ...],
) -> TemporalActivationScheduler | None:
    if spec.frame_source == "none":
        return None
    _require(frames, f"{spec.name} has no frames")
    return TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        frames,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
        active_features=spec.active_features,
    )


def active_feature_names(spec: ConditionSpec, setup) -> tuple[str, ...]:
    if spec.frame_source == "none":
        return ()
    if spec.active_features is None:
        return tuple(setup.encoders)
    return spec.active_features


def indices_for_features(setup, features) -> np.ndarray:
    chunks = [setup.mapping.indices(feature) for feature in features]
    if not chunks:
        return np.empty(0, dtype=np.int64)
    return np.unique(np.concatenate(chunks).astype(np.int64))


def feature_index_map(setup) -> dict[str, np.ndarray]:
    return {
        feature: np.asarray(setup.mapping.indices(feature), dtype=np.int64)
        for feature in setup.encoders
    }


def audit_currents(
    scheduler: TemporalActivationScheduler | None,
    *,
    n_nodes: int,
    n_steps: int,
    dt_ms: float,
    feature_indices: dict[str, np.ndarray],
    active_indices: np.ndarray,
    pulse_windows: tuple[tuple[float, float], ...] = (),
) -> dict:
    """Inject this schedule step by step and audit exactly what reaches neurons.

    Each step the mapped indices are summarised (population and per-feature
    sums); a per-step elementwise maximum over the full buffer accumulates the
    peak any neuron ever received and catches current outside the intended
    active set. ``hold_only`` metrics sum the steps that fall outside every
    pulse window, i.e. the sample-and-hold component a pulses-only schedule
    could not produce.

    Units: ``*_step_current_pa`` and the per-feature peaks/means are
    instantaneous pA during one dt step. ``total/hold_only/pulse_*_pa_steps``
    sum those instantaneous values over neurons and steps, so they are
    neuron-step exposures in pA·steps (multiply by dt_ms to obtain pA·ms);
    they are not a per-step current.
    """
    features = list(feature_indices)
    per_feature = np.zeros((n_steps, len(features)), dtype=np.float64)
    injected = np.zeros(n_steps, dtype=np.float64)
    steps_with_current = 0
    active = np.asarray(sorted(int(index) for index in active_indices), dtype=np.int64)
    hold_mask = np.ones(n_steps, dtype=bool)
    for start_ms, end_ms in pulse_windows:
        first = max(0, int(math.ceil(start_ms / dt_ms)))
        last = min(n_steps, int(math.ceil(end_ms / dt_ms)))
        if last > first:
            hold_mask[first:last] = False
    seen = np.zeros(int(n_nodes), dtype=np.float64)
    if scheduler is not None:
        buffer = np.zeros(int(n_nodes), dtype=np.float64)
        for step in range(n_steps):
            buffer.fill(0.0)
            scheduler.apply(step, step * dt_ms, buffer)
            np.maximum(seen, buffer, out=seen)
            if active.size:
                injected[step] = float(buffer[active].sum())
            if injected[step] > 0.0:
                steps_with_current += 1
            for position, feature in enumerate(features):
                per_feature[step, position] = float(
                    buffer[feature_indices[feature]].sum()
                )
    nonzero = set(int(index) for index in np.flatnonzero(seen))
    max_per_neuron = float(seen.max()) if seen.size else 0.0
    outside = sorted(nonzero.difference(active.tolist()))
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(per_feature).tobytes())
    digest.update(np.ascontiguousarray(injected).tobytes())
    hold = injected[hold_mask]
    pulse = injected[~hold_mask]
    return {
        "n_steps": n_steps,
        "steps_with_current": steps_with_current,
        "total_injected_pa_steps": round(float(injected.sum()), 6),
        "min_step_current_pa": round(float(injected.min()) if n_steps else 0.0, 6),
        "max_step_current_pa": round(float(injected.max()) if n_steps else 0.0, 6),
        "max_per_neuron_current_pa": round(max_per_neuron, 6),
        "n_neurons_with_nonzero_current": len(nonzero),
        "n_indices_outside_active": len(outside),
        "indices_outside_active_first": outside[:20],
        "hold_only_steps": int(hold_mask.sum()),
        "hold_only_time_ms": round(float(hold_mask.sum()) * dt_ms, 6),
        "hold_only_pa_steps": round(float(hold.sum()), 6),
        "hold_only_max_step_current_pa": round(
            float(hold.max()) if hold.size else 0.0, 6
        ),
        "pulse_steps": int((~hold_mask).sum()),
        "pulse_pa_steps": round(float(pulse.sum()), 6),
        "peak_feature_current_pa": {
            feature: round(float(per_feature[:, position].max()), 6)
            for position, feature in enumerate(features)
        },
        "hold_only_peak_feature_current_pa": {
            feature: round(
                float(per_feature[hold_mask, position].max())
                if hold_mask.any()
                else 0.0,
                6,
            )
            for position, feature in enumerate(features)
        },
        "mean_feature_current_pa": {
            feature: round(float(per_feature[:, position].mean()), 6)
            for position, feature in enumerate(features)
        },
        "units": {
            "step_current_pa": (
                "instantaneous population current in pA delivered during one "
                f"{dt_ms} ms step"
            ),
            "injected_pa_steps": (
                "neuron-step exposure: instantaneous pA summed over neurons "
                "and steps; multiply by dt_ms to convert to pA·ms"
            ),
            "per_neuron_current_pa": "instantaneous per-neuron current in pA",
        },
        "current_trace_sha256": digest.hexdigest(),
    }


def _bin_edges(duration_ms: float, bin_ms: float) -> np.ndarray:
    edges = np.arange(0.0, duration_ms, bin_ms, dtype=np.float64)
    if edges.size == 0 or edges[-1] < duration_ms:
        edges = np.append(edges, duration_ms)
    return edges


def partition_metrics(
    counts: np.ndarray,
    spike_times: np.ndarray,
    spike_neurons: np.ndarray,
    mask: np.ndarray | None,
    *,
    duration_ms: float,
    bin_ms: float,
) -> dict:
    """Counts, rates, fixed-width bins and latencies inside one partition."""
    n_neurons = int(counts.size) if mask is None else int(np.count_nonzero(mask))
    spikes = int(counts.sum()) if mask is None else int(counts[mask].sum())
    active = (
        int(np.count_nonzero(counts))
        if mask is None
        else int(np.count_nonzero(counts[mask]))
    )
    rate = (
        spikes / (n_neurons * duration_ms / 1000.0)
        if n_neurons and duration_ms > 0
        else 0.0
    )
    edges = _bin_edges(duration_ms, bin_ms)
    if mask is None:
        selected = spike_times
    else:
        selected = spike_times[mask[spike_neurons]]
    binned = np.histogram(selected, bins=edges)[0] if selected.size else np.zeros(
        edges.size - 1, dtype=np.int64
    )
    return {
        "n_neurons": n_neurons,
        "spikes": spikes,
        "active_neurons": active,
        "firing_rate_hz": round(float(rate), 6),
        "bin_ms": float(bin_ms),
        "bins": [int(value) for value in binned],
        "first_spike_ms": float(selected.min()) if selected.size else None,
        "last_spike_ms": float(selected.max()) if selected.size else None,
    }


def _partition_block(
    counts: np.ndarray,
    spike_times: np.ndarray,
    spike_neurons: np.ndarray,
    *,
    reference: np.ndarray,
    active: np.ndarray,
    duration_ms: float,
    bin_ms: float,
) -> dict:
    reference_mask = np.zeros(counts.size, dtype=bool)
    reference_mask[reference] = True
    active_mask = np.zeros(counts.size, dtype=bool)
    active_mask[active] = True
    outside_reference = ~reference_mask
    outside_active = ~active_mask
    return {
        "total": partition_metrics(
            counts, spike_times, spike_neurons, None,
            duration_ms=duration_ms, bin_ms=bin_ms,
        ),
        "reference": partition_metrics(
            counts, spike_times, spike_neurons, reference_mask,
            duration_ms=duration_ms, bin_ms=bin_ms,
        ),
        "outside_reference": partition_metrics(
            counts, spike_times, spike_neurons, outside_reference,
            duration_ms=duration_ms, bin_ms=bin_ms,
        ),
        "active": partition_metrics(
            counts, spike_times, spike_neurons, active_mask,
            duration_ms=duration_ms, bin_ms=bin_ms,
        ),
        "outside_active": partition_metrics(
            counts, spike_times, spike_neurons, outside_active,
            duration_ms=duration_ms, bin_ms=bin_ms,
        ),
    }


# --------------------------------------------------------------------------
# one condition
# --------------------------------------------------------------------------


def _load_setup(config: CausalControlConfig):
    reference = config.reference
    simulation = _load_yaml(PROJECT_ROOT / reference["simulation_config"])
    neuron = _load_yaml(PROJECT_ROOT / reference["neuron_config"])
    neuron_params = LIFParameters.from_config(neuron["neuron"])
    synapse_params = SynapseParameters.from_config(simulation["synapse"])
    setup = prepare_setup(
        load_connectome(PROJECT_ROOT / reference["connectome"]),
        load_config(PROJECT_ROOT / reference["sensory_config"]),
    )
    if setup.mapping.seed != int(reference["mapping_seed"]):
        raise RuntimeError("mapping seed differs from the preregistered seed")
    if setup.dt_ms != float(reference["dt_ms"]):
        raise RuntimeError("sensory timestep differs from the preregistered value")
    if neuron_params.initial_potential_mv != float(reference["initial_potential_mv"]):
        raise RuntimeError("initial membrane potential differs from the protocol")
    for field in ("threshold_mv", "minimum_potential_mv", "reset_potential_mv"):
        if float(getattr(neuron_params, field)) != float(reference[field]):
            raise RuntimeError(f"{field} differs from the protocol")
    if tuple(setup.encoders) != config.all_features:
        raise RuntimeError(
            "encoder order does not match the preregistered feature order"
        )
    for feature, expected in config.feature_neurons.items():
        actual = int(setup.mapping.size(feature))
        if actual != expected:
            raise RuntimeError(
                f"population {feature!r} has {actual} neurons; protocol says "
                f"{expected}"
            )
    reference_indices = indices_for_features(setup, tuple(setup.encoders))
    if reference_indices.size != int(reference["n_reference_neurons"]):
        raise RuntimeError("reference population size differs from the protocol")
    player_indices = indices_for_features(setup, config.player_features)
    non_player_indices = indices_for_features(setup, config.non_player_features)
    if player_indices.size != int(reference["n_player_neurons"]):
        raise RuntimeError("player population size differs from the protocol")
    if non_player_indices.size != int(reference["n_non_player_neurons"]):
        raise RuntimeError("non-player population size differs from the protocol")
    return setup, neuron_params, synapse_params


def initial_conditions(
    config: CausalControlConfig,
    setup,
    neuron_params: LIFParameters,
    synapse_params: SynapseParameters,
    *,
    duration_ms: float,
) -> dict:
    graph = setup.mapping.graph
    mapping_digest = _digest_array(
        np.concatenate(
            [np.asarray(setup.mapping.indices(feature), dtype=np.int64)
             for feature in setup.encoders]
        )
    )
    return {
        "graph_n_nodes": int(graph.n_nodes),
        "graph_n_edges": int(graph.n_edges),
        "graph_n_synapses": int(graph.n_synapses),
        "mapping_sha256": mapping_digest,
        "mapping_seed": int(setup.mapping.seed),
        "simulation_seed": int(config.reference["simulation_seed"]),
        "dt_ms": float(config.reference["dt_ms"]),
        "duration_ms": float(duration_ms),
        "n_steps": int(round(duration_ms / float(config.reference["dt_ms"]))),
        "neuron": asdict(neuron_params),
        "synapse": asdict(synapse_params),
        "background_current_pa": 0.0,
        "noise_std_pa": 0.0,
        "max_recorded_spikes": int(config.reference["max_recorded_spikes"]),
    }


def run_once(
    spec: ConditionSpec,
    config: CausalControlConfig,
    setup,
    neuron_params: LIFParameters,
    synapse_params: SynapseParameters,
    cache: CausalFrameCache | None,
    *,
    duration_ms: float,
    smoke_ms: float | None,
) -> dict:
    frames = resolve_frames(spec, config, cache, smoke_ms=smoke_ms)
    scheduler = build_scheduler(spec, setup, frames)
    if spec.frame_source == "cached":
        _require(cache is not None, f"{spec.name} requires the cached frames")
        frames_digest = cache.frames_digest
    elif spec.frame_source == "neutral":
        frames_digest = _digest_json([frame.as_dict() for frame in frames])
    else:
        frames_digest = None
    setup_dt = float(config.reference["dt_ms"])
    n_steps = int(round(duration_ms / setup_dt))
    active_features = active_feature_names(spec, setup)
    active = indices_for_features(setup, active_features)
    reference = indices_for_features(setup, tuple(setup.encoders))
    feature_indices = feature_index_map(setup)

    if scheduler is not None:
        if not math.isclose(
            scheduler.horizon_ms, duration_ms, abs_tol=1e-9
        ) and scheduler.horizon_ms < duration_ms:
            raise RuntimeError("scheduler horizon does not cover the duration")

    simulator = BrainSimulator(
        setup.mapping.graph,
        neuron_params,
        synapse_params,
        dt_ms=setup_dt,
        duration_ms=duration_ms,
        seed=int(config.reference["simulation_seed"]),
        background_current_pa=0.0,
        noise_std_pa=0.0,
        stimulus=None,
        input_schedule=scheduler,
        max_recorded_spikes=int(config.reference["max_recorded_spikes"]),
        progress_interval_ms=config.progress_interval_ms,
        diagnostics_interval_steps=config.diagnostics_interval_steps,
    )
    if spec.frame_source == "none":
        if simulator.input_schedule is not None:
            raise RuntimeError("C0 must not have an input schedule")
    else:
        if simulator.input_schedule is not scheduler:
            raise RuntimeError("the simulator did not receive the built scheduler")

    process = psutil.Process()
    rss_before = process.memory_info().rss
    started = time.perf_counter()
    capacity_exceeded = False
    capacity_message = None
    try:
        result = simulator.run(progress=False)
    except SpikeCapacityExceeded as exc:  # pragma: no cover - invalid run path
        capacity_exceeded = True
        capacity_message = str(exc)
        result = None
    wall = time.perf_counter() - started
    rss_after = process.memory_info().rss

    if result is None:
        counts = np.zeros(int(setup.mapping.graph.n_nodes), dtype=np.int64)
        spike_times = np.empty(0, dtype=np.float64)
        spike_neurons = np.empty(0, dtype=np.int64)
        summary = {}
        diagnostics = {}
    else:
        counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
        spike_times = np.asarray(result.recorder.spike_times_ms, dtype=np.float64)
        spike_neurons = np.asarray(
            result.recorder.spike_neuron_indices, dtype=np.int64
        )
        summary = dict(result.summary["activity"])
        diagnostics = dict(result.summary["diagnostics"])

    audit = audit_currents(
        scheduler,
        n_nodes=int(setup.mapping.graph.n_nodes),
        n_steps=n_steps,
        dt_ms=setup_dt,
        feature_indices=feature_indices,
        active_indices=active,
        pulse_windows=pulse_windows(scheduler),
    )
    partitions = _partition_block(
        counts,
        spike_times,
        spike_neurons,
        reference=reference,
        active=active,
        duration_ms=duration_ms,
        bin_ms=float(config.reference["bin_ms"]),
    )
    spikes_by_feature = {
        feature: int(counts[indices].sum())
        for feature, indices in feature_indices.items()
    }

    memory = simulator.memory_breakdown() if result is not None else {}
    del simulator

    scheduler_digest = scheduler_signature_digest(scheduler)
    activity_digest = _digest_json(summary) if summary else None
    return {
        "condition": spec.name,
        "description": spec.description,
        "frame_source": spec.frame_source,
        "active_features": list(active_features),
        "n_active_features": len(active_features),
        "n_active_neurons": int(active.size),
        "n_reference_neurons": int(reference.size),
        "scheduler": {
            "present": scheduler is not None,
            "n_frames": len(frames),
            "n_stimulated_neurons": (
                int(scheduler.stimulated_indices.size) if scheduler is not None else 0
            ),
            "horizon_ms": scheduler.horizon_ms if scheduler is not None else None,
            "memory_bytes": int(scheduler.memory_bytes) if scheduler is not None else 0,
            "statistics": scheduler.input_statistics() if scheduler is not None else None,
            "signature_sha256": scheduler_digest,
        },
        "cache_frames_digest": frames_digest,
        "simulation": {
            "duration_ms": float(duration_ms),
            "n_steps": n_steps,
            "wall_runtime_s": round(wall, 4),
            "steps_per_second_wall": round(n_steps / wall, 2) if wall > 0 else None,
            "spikes_total": int(counts.sum()),
            "activity": summary,
            "activity_by_stimulation": (
                dict(result.summary["activity_by_stimulation"]) if result is not None else {}
            ),
            "synapses": (
                dict(result.summary["synapses"]) if result is not None else {}
            ),
            "diagnostics": diagnostics,
            "memory": memory,
            "rss_before_mb": round(rss_before / 1024**2, 3),
            "rss_after_mb": round(rss_after / 1024**2, 3),
            "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
            "spike_capacity": int(config.reference["max_recorded_spikes"]),
        },
        "spike_capacity_exceeded": capacity_exceeded,
        "spike_capacity_message": capacity_message,
        "partitions": partitions,
        "spikes_by_feature": spikes_by_feature,
        "current_audit": audit,
        "reproducibility_hashes": {
            "spike_counts_sha256": _digest_array(counts),
            "activity_summary_sha256": activity_digest,
            "current_trace_sha256": audit["current_trace_sha256"],
            "scheduler_signature_sha256": scheduler_digest,
            "cache_frames_digest": frames_digest,
            "spikes_total": int(counts.sum()),
            "first_spike_ms": float(spike_times.min()) if spike_times.size else None,
            "last_spike_ms": float(spike_times.max()) if spike_times.size else None,
        },
        "initial_conditions": initial_conditions(
            config,
            setup,
            neuron_params,
            synapse_params,
            duration_ms=duration_ms,
        ),
    }


def run_condition(
    spec: ConditionSpec,
    config: CausalControlConfig,
    setup,
    neuron_params: LIFParameters,
    synapse_params: SynapseParameters,
    cache: CausalFrameCache | None,
    *,
    duration_ms: float,
    smoke_ms: float | None,
    repeats: int,
) -> dict:
    runs = [
        run_once(
            spec,
            config,
            setup,
            neuron_params,
            synapse_params,
            cache,
            duration_ms=duration_ms,
            smoke_ms=smoke_ms,
        )
        for _ in range(repeats)
    ]
    first = runs[0]
    hashes = [run["reproducibility_hashes"] for run in runs]
    differences = [
        key
        for key in REPRODUCIBLE_KEYS
        if len({json.dumps(item[key], sort_keys=True) for item in hashes}) > 1
    ]
    first["reproducibility"] = {
        "n_runs": repeats,
        "identical": not differences,
        "differences": differences,
        "hashes": hashes,
    }
    return first


# --------------------------------------------------------------------------
# condition checks and invalidation
# --------------------------------------------------------------------------


def condition_checks(
    spec: ConditionSpec,
    item: dict,
    config: CausalControlConfig,
    setup,
    cache: CausalFrameCache | None,
    *,
    smoke_ms: float | None,
) -> dict:
    checks: dict[str, bool | None] = {}
    not_evaluated: list[str] = []
    audit = item["current_audit"]
    scheduler = item["scheduler"]
    smoke = smoke_ms is not None
    if spec.frame_source == "none":
        checks["no_scheduler"] = not scheduler["present"]
        checks["no_current_injected"] = audit["total_injected_pa_steps"] == 0.0
        checks["no_neurons_current"] = audit["n_neurons_with_nonzero_current"] == 0
    else:
        checks["scheduler_present"] = scheduler["present"]
        checks["scheduler_targets_active_set"] = (
            scheduler["n_stimulated_neurons"] == item["n_active_neurons"]
        )
        checks["no_current_outside_active"] = audit["n_indices_outside_active"] == 0
        checks["current_injected"] = audit["total_injected_pa_steps"] > 0.0
    if spec.name == "C1":
        neutral = [
            frame
            for frame in resolve_frames(spec, config, cache, smoke_ms=smoke_ms)
        ]
        checks["all_frames_neutral"] = all(
            frame.state.player == PlayerState()
            and frame.state.obstacle is None
            and frame.state.train is None
            and frame.state.coin is None
            and not frame.events
            for frame in neutral
        )
        peaks = audit["peak_feature_current_pa"]
        expected = config.reference["expected_neutral_current_pa"]
        checks["neutral_player_lane_current"] = math.isclose(
            peaks["player_lane"], float(expected["player_lane"]), abs_tol=1e-6
        )
        checks["neutral_player_speed_current"] = math.isclose(
            peaks["player_speed"], float(expected["player_speed"]), abs_tol=1e-6
        )
        checks["no_non_player_current"] = all(
            peaks[feature] == 0.0
            for feature in config.non_player_features
        )
        checks["no_pulse_events"] = scheduler["statistics"]["n_pulse_events"] == 0
        checks["neutral_current_is_constant"] = math.isclose(
            audit["min_step_current_pa"],
            audit["max_step_current_pa"],
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        checks["neutral_current_on_every_step"] = (
            audit["steps_with_current"] == audit["n_steps"]
        )
    if spec.name == "C2":
        checks["player_features_inactive"] = not (
            set(spec.active_features) & set(config.player_features)
        )
        checks["player_current_zero"] = all(
            audit["peak_feature_current_pa"][feature] == 0.0
            for feature in config.player_features
        )
        # The hold/pulse components are only observable in a window that
        # contains steps outside every pulse tail. In a short smoke window the
        # first seconds can be pulse-tiled or feature-free, so an unobservable
        # component is left unevaluated (None) rather than failed; the full run
        # requires it.
        if audit["pulse_steps"] > 0 and (
            audit["pulse_pa_steps"] > 0.0 or not smoke
        ):
            checks["pulses_included"] = (
                scheduler["statistics"]["n_pulse_events"] > 0
                and audit["pulse_pa_steps"] > 0.0
            )
        else:
            not_evaluated.append("pulses_included")
        if audit["hold_only_steps"] > 0 and (
            audit["hold_only_pa_steps"] > 0.0 or not smoke
        ):
            checks["hold_component_included"] = (
                audit["hold_only_pa_steps"] > 0.0
            )
            checks["not_pulses_only"] = any(
                value > 0.0
                for feature, value in audit[
                    "hold_only_peak_feature_current_pa"
                ].items()
                if feature in config.non_player_features
            )
        else:
            not_evaluated.extend(
                ["hold_component_included", "not_pulses_only"]
            )
    if spec.name == "C3":
        checks["all_features_active"] = (
            item["n_active_features"] == int(config.reference["n_features"])
        )
        checks["reference_equals_active"] = (
            item["n_active_neurons"] == item["n_reference_neurons"]
        )
    if cache is not None and spec.frame_source == "cached":
        checks["cache_digest_recorded"] = item["cache_frames_digest"] == cache.frames_digest
    checks["repeats_identical"] = item["reproducibility"]["identical"]
    return checks, not_evaluated


def evaluate_invalidations(
    items: dict[str, dict],
    checks: dict[str, dict],
    config: CausalControlConfig,
    *,
    mode: str,
    protected: dict,
) -> dict:
    triggered: list[dict] = []

    def trigger(rule: str, detail) -> None:
        triggered.append({"rule": rule, "detail": detail})

    for name, item in items.items():
        if item["spike_capacity_exceeded"]:
            trigger("spike_capacity_exceeded", {"condition": name})
        diagnostics = item["simulation"]["diagnostics"]
        if not diagnostics.get("finite_state", False):
            trigger("non_finite_state", {"condition": name})
        minimum = float(config.reference["minimum_potential_mv"])
        threshold = float(config.reference["threshold_mv"])
        if "min_membrane_mv" in diagnostics and (
            float(diagnostics["min_membrane_mv"]) < minimum - 1e-6
        ):
            trigger("membrane_below_floor", {"condition": name})
        if "max_membrane_mv" in diagnostics and (
            float(diagnostics["max_membrane_mv"]) > threshold + 1e-6
        ):
            trigger("membrane_above_threshold", {"condition": name})
        if item["reproducibility"]["differences"]:
            trigger(
                "repeated_runs_differ",
                {
                    "condition": name,
                    "differences": item["reproducibility"]["differences"],
                },
            )
        if item["current_audit"]["n_indices_outside_active"]:
            trigger(
                "current_outside_active_set",
                {
                    "condition": name,
                    "n": item["current_audit"]["n_indices_outside_active"],
                },
            )
        failed = sorted(
            key for key, value in checks[name].items() if value is False
        )
        if failed:
            trigger("condition_definition_violation", {"condition": name, "checks": failed})

    mismatched = sorted(
        name for name, entry in protected.items() if not entry["match"]
    )
    if mismatched:
        trigger("protected_hash_changed", {"inputs": mismatched})

    signatures = {
        name: json.dumps(item["initial_conditions"], sort_keys=True)
        for name, item in items.items()
    }
    if len(set(signatures.values())) > 1:
        trigger("initial_conditions_differ", {"conditions": sorted(items)})

    if any(name in items for name in ("C2", "C3")):
        digests = {
            items[name]["cache_frames_digest"]
            for name in ("C2", "C3")
            if name in items
        }
        if len(digests) > 1:
            trigger("cached_frames_differ_between_C2_and_C3", sorted(digests))
        if mode == "full" and "C3" in items:
            if config.archived["scheduler_sha256"] != items["C3"]["scheduler"][
                "signature_sha256"
            ]:
                trigger(
                    "c3_scheduler_signature_mismatch",
                    {
                        "expected": config.archived["scheduler_sha256"],
                        "actual": items["C3"]["scheduler"]["signature_sha256"],
                    },
                )
            if config.archived["spike_counts_sha256"] != items["C3"][
                "reproducibility_hashes"
            ]["spike_counts_sha256"]:
                trigger(
                    "c3_spike_counts_mismatch",
                    {
                        "expected": config.archived["spike_counts_sha256"],
                        "actual": items["C3"]["reproducibility_hashes"][
                            "spike_counts_sha256"
                        ],
                    },
                )
    archive_gate = (
        "evaluated" if mode == "full" else "not applicable in smoke mode"
    )
    return {
        "valid": not triggered,
        "triggered": triggered,
        "archive_gate": archive_gate,
        "rules_evaluated": [
            "spike_capacity_exceeded",
            "non_finite_state",
            "membrane_bounds",
            "repeated_runs_differ",
            "current_outside_active_set",
            "condition_definition_violation",
            "protected_hash_changed",
            "initial_conditions_differ",
            "cached_frames_differ_between_C2_and_C3",
            "c3_scheduler_signature_mismatch",
            "c3_spike_counts_mismatch",
        ],
    }


# --------------------------------------------------------------------------
# comparisons, protected inputs, git
# --------------------------------------------------------------------------


def _contrast(first: dict, second: dict, label: str) -> dict:
    def difference(key: str, partition: str) -> int:
        return (
            second["partitions"][partition][key]
            - first["partitions"][partition][key]
        )

    def latency(partition: str):
        values = [
            item["partitions"][partition]["first_spike_ms"]
            for item in (first, second)
        ]
        if any(value is None for value in values):
            return None
        return round(values[1] - values[0], 4)

    return {
        "contrast": label,
        "outside_reference_spikes_delta": difference("spikes", "outside_reference"),
        "outside_reference_active_neurons_delta": difference(
            "active_neurons", "outside_reference"
        ),
        "outside_active_spikes_delta": difference("spikes", "outside_active"),
        "total_spikes_delta": difference("spikes", "total"),
        "reference_spikes_delta": difference("spikes", "reference"),
        "outside_reference_first_spike_ms_delta": latency("outside_reference"),
    }


def comparisons(items: dict[str, dict]) -> dict:
    pairs = (("C0", "C1"), ("C0", "C2"), ("C0", "C3"), ("C1", "C2"), ("C1", "C3"))
    missing = [name for pair in pairs for name in pair if name not in items]
    if missing:
        return {"available": False, "missing": sorted(set(missing))}
    return {
        "available": True,
        "contrasts": {
            f"{second}_minus_{first}": _contrast(
                items[first], items[second], f"{second}-{first}"
            )
            for first, second in pairs
        },
        "note": (
            "These are whole-condition contrasts of a deterministic recurrent "
            "network. They are descriptive; subtracting conditions does not "
            "identify additive contributions."
        ),
    }


def protected_hashes(config: CausalControlConfig) -> dict:
    reference = config.reference
    files = {
        "readme": (reference["readme"], reference["readme_sha256"]),
        "connectome": (reference["connectome"], reference["connectome_sha256"]),
        "sensory_config": (
            reference["sensory_config"],
            reference["sensory_config_sha256"],
        ),
        "simulation_config": (
            reference["simulation_config"],
            reference["simulation_config_sha256"],
        ),
        "neuron_config": (
            reference["neuron_config"],
            reference["neuron_config_sha256"],
        ),
        "perception_config": (
            reference["perception_config"],
            reference["perception_config_sha256"],
        ),
        "detector_config": (
            reference["detector_config"],
            reference["detector_config_sha256"],
        ),
        "split_manifest": (
            reference["split_manifest"],
            reference["split_manifest_sha256"],
        ),
        "detector_model": (
            reference["detector_model"],
            reference["detector_model_sha256"],
        ),
    }
    result = {}
    for name, (relative, expected) in files.items():
        path = PROJECT_ROOT / relative
        actual = _sha256(path) if path.is_file() else None
        result[name] = {
            "path": relative,
            "expected": expected,
            "actual": actual,
            "match": actual == expected,
        }
    return result


def git_state() -> dict:
    def run(*args) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(PROJECT_ROOT), *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout

    head = run("rev-parse", "HEAD")
    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    status = run("status", "--porcelain")
    staged = run("diff", "--cached", "--stat")
    return {
        "head": head.strip() if head else None,
        "branch": branch.strip() if branch else None,
        "working_tree_dirty": bool(status and status.strip()),
        "n_status_entries": len(status.splitlines()) if status else None,
        "staged_changes": bool(staged and staged.strip()),
        "status": status.splitlines() if status else [],
    }


# --------------------------------------------------------------------------
# cache construction
# --------------------------------------------------------------------------


def build_cache(
    config: CausalControlConfig,
    *,
    cache_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    """Build the frozen C2/C3 input once from the existing Phase 3B.2C chain."""
    target = Path(cache_path) if cache_path else PROJECT_ROOT / config.cache["path"]
    if manifest_path:
        manifest_target = Path(manifest_path)
    elif cache_path:
        manifest_target = target.with_name(target.stem + ".manifest.json")
    else:
        manifest_target = PROJECT_ROOT / config.cache["manifest"]
    for path in (target, manifest_target):
        if path.exists():
            raise FileExistsError(
                f"{path} already exists; this runner never overwrites cached "
                "inputs. Remove it explicitly to rebuild."
            )

    from experiments.phase_3b import real_sequence_replay as replay
    from perception.pipeline import PerceptionPipeline

    if replay.GROUP != config.cache["group"]:
        raise RuntimeError("cached sequence group differs from the protocol")
    if (
        replay.FRAME_START != int(config.cache["frame_start"])
        or replay.FRAME_END != int(config.cache["frame_end"])
    ):
        raise RuntimeError("cached frame range differs from the protocol")
    if replay.BOUNDS_TOLERANCE_PIXELS != float(config.cache["bounds_tolerance_pixels"]):
        raise RuntimeError("cached bounds tolerance differs from the protocol")

    sequence = replay.discover_frames()
    detector, _detector_config = replay._build_detector()
    perception_config = replay._experiment_perception_config(
        replay.BOUNDS_TOLERANCE_PIXELS
    )
    pipeline = PerceptionPipeline(perception_config, detector)
    observations, _records = replay._process_frames(
        pipeline, sequence["frames"], replay.BOUNDS_TOLERANCE_PIXELS
    )
    temporal = replay._temporal_run(observations)
    if len(temporal) != int(config.reference["n_frames"]):
        raise RuntimeError("cache build produced the wrong number of frames")
    times = [frame.time_ms for frame in temporal]
    if not all(second > first for first, second in zip(times, times[1:])):
        raise RuntimeError("cache build produced non-increasing frame times")

    frames_payload = [frame.as_dict() for frame in temporal]
    frames_digest = _digest_json(frames_payload)
    setup, _neuron, _synapse = _load_setup(config)
    scheduler = TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        temporal,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
    )
    scheduler_digest = scheduler_signature_digest(scheduler)

    payload = {
        "schema": CACHE_SCHEMA,
        "group": sequence["group"],
        "frame_start": int(config.cache["frame_start"]),
        "frame_end": int(config.cache["frame_end"]),
        "bounds_tolerance_pixels": float(config.cache["bounds_tolerance_pixels"]),
        "sequence_sha256": sequence["sequence_sha256"],
        "detector_model_sha256": detector.model_sha256,
        "n_frames": len(temporal),
        "frames": frames_payload,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "cache_path": str(target.relative_to(PROJECT_ROOT))
        if target.is_relative_to(PROJECT_ROOT)
        else str(target),
        "cache_sha256": _sha256(target),
        "frames_digest": frames_digest,
        "n_frames": len(temporal),
        "n_events": sum(len(frame.events) for frame in temporal),
        "n_pulse_events": sum(
            1 for frame in temporal for event in frame.events if event.is_pulse
        ),
        "first_frame_ms": float(times[0]),
        "last_frame_ms": float(times[-1]),
        "scheduler_signature_sha256": scheduler_digest,
        "n_stimulated_neurons": int(scheduler.stimulated_indices.size),
        "active_features": list(scheduler.encoders),
        "archived": {
            key: config.archived[key]
            for key in (
                "temporal_sha256",
                "detections_sha256",
                "scheduler_sha256",
                "spike_counts_sha256",
            )
        },
        "matches_archived_temporal": (
            frames_digest == config.archived["temporal_sha256"]
        ),
        "matches_archived_scheduler": (
            scheduler_digest == config.archived["scheduler_sha256"]
        ),
        "sequence_sha256": sequence["sequence_sha256"],
        "detector_model_sha256": detector.model_sha256,
        "config_sha256": _sha256(config.source_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": git_state(),
        "input_hashes": protected_hashes(config),
    }
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_target.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


# --------------------------------------------------------------------------
# experiment driver
# --------------------------------------------------------------------------


def _smoke_frames_duration(
    config: CausalControlConfig, cache: CausalFrameCache | None, smoke_ms: float | None
) -> float:
    if smoke_ms is not None:
        return float(smoke_ms)
    if cache is not None:
        return cache.last_time_ms + float(config.reference["dt_ms"])
    return float(config.reference["duration_ms"])


def require_cache_matches_archive(
    config: CausalControlConfig, cache: CausalFrameCache | None
) -> None:
    """Full-mode gate: refuse to simulate on a cache that is not the archive."""
    _require(cache is not None, "full mode requires the cached frames")
    _require(
        cache.frames_digest == config.archived["temporal_sha256"],
        "cached frames do not match the archived Phase 3B.2C temporal digest",
    )
    _require(
        cache.scheduler_signature_sha256 == config.archived["scheduler_sha256"],
        "cached-frame scheduler signature does not match the archived value",
    )


def run_experiment(
    *,
    condition_names: list[str],
    config: CausalControlConfig,
    smoke_ms: float | None = None,
    repeats: int | None = None,
    cache_path: Path | None = None,
) -> dict:
    started = time.perf_counter()
    mode = "smoke" if smoke_ms is not None else "full"
    for name in condition_names:
        if name not in config.conditions:
            raise ValueError(f"unknown condition {name!r}")

    setup, neuron_params, synapse_params = _load_setup(config)
    needs_cache = any(
        config.condition(name).frame_source == "cached" for name in condition_names
    )
    cache = load_cache(config, cache_path) if needs_cache else None
    if smoke_ms is None and needs_cache:
        require_cache_matches_archive(config, cache)
    duration = _smoke_frames_duration(config, cache, smoke_ms)
    if smoke_ms is None:
        if not math.isclose(
            duration, float(config.reference["duration_ms"]), abs_tol=1e-6
        ):
            raise RuntimeError(
                "cached sequence duration differs from the preregistered duration"
            )
    n_steps = int(round(duration / float(config.reference["dt_ms"])))
    if smoke_ms is None and n_steps != int(config.reference["n_steps"]):
        raise RuntimeError("step count differs from the preregistered value")

    protected = protected_hashes(config)
    repeats = int(repeats if repeats is not None else config.in_process_repeats)
    items: dict[str, dict] = {}
    checks: dict[str, dict] = {}
    for name in condition_names:
        spec = config.condition(name)
        print(
            f"  {name}: {spec.frame_source} frames, {spec.label}, "
            f"{duration:.1f} ms, {repeats} repetition(s)",
            flush=True,
        )
        items[name] = run_condition(
            spec,
            config,
            setup,
            neuron_params,
            synapse_params,
            cache,
            duration_ms=duration,
            smoke_ms=smoke_ms,
            repeats=repeats,
        )
        checks[name], notes = condition_checks(
            spec, items[name], config, setup, cache, smoke_ms=smoke_ms
        )
        items[name]["condition_checks_not_evaluated"] = notes
        print(
            f"    spikes={items[name]['simulation']['spikes_total']} "
            f"outside_R={items[name]['partitions']['outside_reference']['spikes']} "
            f"outside_A={items[name]['partitions']['outside_active']['spikes']} "
            f"wall={items[name]['simulation']['wall_runtime_s']}s",
            flush=True,
        )

    invalidations = evaluate_invalidations(
        items, checks, config, mode=mode, protected=protected
    )
    for name, item in items.items():
        item["condition_checks"] = checks[name]

    payload = {
        "phase": "P3-T2",
        "version": config.version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "smoke_ms": smoke_ms,
        "runtime_s": round(time.perf_counter() - started, 3),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pid_rss_mb": round(psutil.Process().memory_info().rss / 1024**2, 3),
        },
        "git": git_state(),
        "protocol": {
            "question": (
                "Does external sensory current produce neural activity outside "
                "the directly stimulated neurons, and is that activity "
                "attributable to the visual schedule rather than player defaults?"
            ),
            "conditions": {
                name: {
                    "description": config.condition(name).description,
                    "frame_source": config.condition(name).frame_source,
                    "active_features": (
                        None
                        if config.condition(name).active_features is None
                        else list(config.condition(name).active_features)
                    ),
                }
                for name in condition_names
            },
            "condition_order": list(condition_names),
            "reference_set": {
                "definition": "all mapped sensory neurons",
                "n_neurons": int(items[condition_names[0]]["n_reference_neurons"]),
                "per_feature_neurons": dict(config.feature_neurons),
                "n_player_neurons": int(config.reference["n_player_neurons"]),
                "n_non_player_neurons": int(config.reference["n_non_player_neurons"]),
            },
            "fixed_constants": {
                key: config.reference[key]
                for key in (
                    "mapping_seed",
                    "simulation_seed",
                    "dt_ms",
                    "duration_ms",
                    "n_steps",
                    "initial_potential_mv",
                    "threshold_mv",
                    "minimum_potential_mv",
                    "reset_potential_mv",
                    "background_current_pa",
                    "noise_std_pa",
                    "max_recorded_spikes",
                )
            },
            "partitioning": [
                "R versus outside R",
                "A_c versus outside A_c",
            ],
            "bin_ms": float(config.reference["bin_ms"]),
            "repeats_in_process": repeats,
            "repeats_in_subprocess": list(config.subprocess_conditions),
        },
        "config": {
            "path": (
                str(config.source_path.relative_to(PROJECT_ROOT))
                if config.source_path.is_relative_to(PROJECT_ROOT)
                else str(config.source_path)
            ),
            "sha256": _sha256(config.source_path),
            "archived": dict(config.archived),
        },
        "cache": (
            {
                "path": str(cache.path.relative_to(PROJECT_ROOT))
                if cache.path.is_relative_to(PROJECT_ROOT)
                else str(cache.path),
                "file_sha256": cache.file_sha256,
                "frames_digest": cache.frames_digest,
                "n_frames": len(cache.frames),
                "scheduler_signature_sha256": cache.scheduler_signature_sha256,
                "matches_archived_temporal": cache.manifest.get(
                    "matches_archived_temporal"
                ),
                "matches_archived_scheduler": cache.manifest.get(
                    "matches_archived_scheduler"
                ),
                "n_pulse_events": cache.n_pulse_events,
            }
            if cache is not None
            else None
        ),
        "protected_hashes": protected,
        "conditions": items,
        "comparison": comparisons(items),
        "invalidations": invalidations,
        "verdict": (
            (
                "SMOKE ONLY (infrastructure validation)"
                if invalidations["valid"]
                else "SMOKE INVALID"
            )
            if mode == "smoke"
            else ("VALID" if invalidations["valid"] else "INVALID")
        ),
        "limitations": LIMITATIONS,
        "action_selection": "none; the chain ends at sensory current injection",
    }
    return payload


def _hash_subset(payload: dict, name: str) -> dict:
    item = payload["conditions"][name]
    keys = (
        "spike_counts_sha256",
        "activity_summary_sha256",
        "current_trace_sha256",
        "scheduler_signature_sha256",
        "cache_frames_digest",
        "spikes_total",
        "first_spike_ms",
        "last_spike_ms",
    )
    hashes = item["reproducibility_hashes"]
    return {key: hashes[key] for key in keys}


def subprocess_reproducibility(
    payload: dict,
    *,
    condition_names: list[str],
    config: CausalControlConfig,
    smoke_ms: float | None,
    cache_path: Path | None,
) -> dict:
    """Re-run selected conditions in fresh interpreters and compare hashes."""
    results = {}
    for name in condition_names:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"{name}.json"
            command = [
                sys.executable,
                "-m",
                "experiments.phase_3c.causal_control",
                "--condition",
                name,
                "--once",
                "--output",
                str(output),
            ]
            if smoke_ms is not None:
                command += ["--smoke-ms", str(smoke_ms)]
            if cache_path is not None:
                command += ["--cache", str(cache_path)]
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                results[name] = {
                    "ran": False,
                    "returncode": completed.returncode,
                    "stderr_tail": completed.stderr[-2000:],
                }
                continue
            child = json.loads(output.read_text(encoding="utf-8"))
            parent_hashes = _hash_subset(payload, name)
            child_hashes = _hash_subset(child, name)
            differences = sorted(
                key
                for key in parent_hashes
                if json.dumps(parent_hashes[key], sort_keys=True)
                != json.dumps(child_hashes[key], sort_keys=True)
            )
            results[name] = {
                "ran": True,
                "identical": not differences,
                "differences": differences,
                "hashes": child_hashes,
            }
    return {
        "conditions": results,
        "identical": all(
            item.get("ran") and item.get("identical")
            for item in results.values()
        ),
    }


def write_outputs(payload: dict, output: Path, *, overwrite: bool = False) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"{output} already exists; pass --overwrite to replace it"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8"
    )
    sidecar = output.with_name(output.stem + ".sidecar.json")
    if sidecar.exists() and not overwrite:
        raise FileExistsError(
            f"{sidecar} already exists; pass --overwrite to replace it"
        )
    sidecar.write_text(
        json.dumps(
            {
                "output": output.name,
                "phase": payload["phase"],
                "version": payload["version"],
                "verdict": payload["verdict"],
                "mode": payload["mode"],
                "generated_at_utc": payload["generated_at_utc"],
                "git": payload["git"],
                "config_sha256": payload["config"]["sha256"],
                "cache_sha256": (
                    payload["cache"]["file_sha256"]
                    if payload["cache"] is not None
                    else None
                ),
                "invalidations": payload["invalidations"]["triggered"],
            },
            indent=1,
            allow_nan=False,
        ),
        encoding="utf-8",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-cache", action="store_true")
    parser.add_argument(
        "--condition",
        action="append",
        choices=["C0", "C1", "C2", "C3"],
        help="condition to run; repeat for several",
    )
    parser.add_argument("--all", action="store_true", help="run C0-C3 in order")
    parser.add_argument("--smoke-ms", type=float, default=None)
    parser.add_argument("--once", action="store_true", help="one repetition only")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output file instead of refusing",
    )
    parser.add_argument(
        "--reproduce-subprocess",
        action="store_true",
        help="additionally re-run C0/C3 in fresh interpreters",
    )
    args = parser.parse_args(argv)
    config = CausalControlConfig.load()

    if args.build_cache:
        manifest = build_cache(config)
        print(
            f"wrote {config.cache['path']} | frames={manifest['n_frames']} "
            f"events={manifest['n_events']} pulses={manifest['n_pulse_events']} "
            f"temporal_matches={manifest['matches_archived_temporal']} "
            f"scheduler_matches={manifest['matches_archived_scheduler']}"
        )
        return 0

    if args.all:
        names = ["C0", "C1", "C2", "C3"]
    elif args.condition:
        names = args.condition
    else:
        parser.error("choose --condition, --all or --build-cache")

    repeats = 1 if args.once else None
    payload = run_experiment(
        condition_names=names,
        config=config,
        smoke_ms=args.smoke_ms,
        repeats=repeats,
        cache_path=args.cache,
    )
    if args.reproduce_subprocess:
        selected = [name for name in config.subprocess_conditions if name in names]
        if selected:
            payload["subprocess_reproducibility"] = subprocess_reproducibility(
                payload,
                condition_names=selected,
                config=config,
                smoke_ms=args.smoke_ms,
                cache_path=args.cache,
            )
            if not payload["subprocess_reproducibility"]["identical"]:
                payload["invalidations"]["triggered"].append(
                    {
                        "rule": "subprocess_runs_differ",
                        "detail": payload["subprocess_reproducibility"],
                    }
                )
                payload["invalidations"]["valid"] = False
                payload["verdict"] = "INVALID"

    output = args.output
    if output is None:
        suffix = "smoke" if args.smoke_ms is not None else "full"
        output = (
            PROJECT_ROOT
            / "experiments"
            / "phase_3c"
            / "results"
            / f"p3_t2_{suffix}.json"
        )
    write_outputs(payload, output, overwrite=args.overwrite)
    print(
        f"wrote {output} | verdict={payload['verdict']} | "
        f"conditions={list(payload['conditions'])} | "
        f"invalidations={len(payload['invalidations']['triggered'])}"
    )
    return 0 if payload["invalidations"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
