"""P3-T12: descriptive characterization of network ignition and stability.

The P3-T2/P3-T3 runners answer "how much activity" per condition. This module
answers "how the activity is organised": when it starts, how it recruits, where
it sits relative to the injected set, how the membrane population is
distributed, how much time is spent at the enforced bounds, whether activity
persists when drive stops, and how recruitment maps onto graph structure.

It does not modify the simulator, neuron model, synapse model, connectome,
mapping, scheduler, cached frames, seeds or recorder capacity. It reproduces
the exact step order of ``brain.brain_simulator`` in a dedicated stepper so
that per-step measurements can be taken, and it proves equivalence three ways:
against ``BrainSimulator`` on a small graph (tests), against the archived P3-T2
C3 spike-count hash on the full run, and through a prefix gate for the one
extension condition.

The ``C3-washout`` condition runs the archived C3 schedule for 750 ms longer
than the validated window. The scheduler's 250 ms hold ceiling and 150 ms pulse
decay mean no scheduled drive can reach the graph in the final 500 ms, which is
the only way to separate "sustained because driven" from "sustained after
drive". Its first 3,300.5 ms must be bit-identical to C3.

All outputs are descriptive. No significance, mechanism or information claim is
made anywhere in this module.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import psutil  # noqa: E402

from brain.neural_activity import SpikeCapacityExceeded, SpikeRecorder  # noqa: E402
from brain.neuron_model import LIFPopulation  # noqa: E402
from brain.synapse_model import SynapseModel  # noqa: E402
from experiments.phase_3c import causal_control as cc  # noqa: E402
from experiments.phase_3c import ignition_reporting as ir  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "p3_t12_characterization.yaml"
PHASE = "P3-T12"
BASELINE_NAME = "C3"
ABLATION_NAMES = ("no-player_lane", "no-train_lane")
WASHOUT_NAME = "C3-washout"

REPRODUCIBLE_KEYS = cc.REPRODUCIBLE_KEYS


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CharacterizationConfig:
    source_path: Path
    version: str
    description: str
    causal: cc.CausalControlConfig
    output: Path
    smoke_output: Path
    repeats: int
    conditions: tuple[str, ...]
    subprocess_conditions: tuple[str, ...]
    sampling: dict
    washout: dict
    limitations: tuple[str, ...]

    @property
    def base_duration_ms(self) -> float:
        return float(self.causal.reference["duration_ms"])

    def spec_for(self, name: str) -> cc.ConditionSpec:
        if name in ("C0", "C1", "C2", "C3"):
            return self.causal.condition(name)
        if name == WASHOUT_NAME:
            base = self.causal.condition(str(self.washout["base_condition"]))
            return cc.ConditionSpec(
                name=name,
                description=(
                    "archived C3 schedule run 750 ms past the validated window; "
                    "the last 500.5 ms cannot receive scheduled drive"
                ),
                frame_source=base.frame_source,
                active_features=base.active_features,
            )
        if name in ABLATION_NAMES:
            feature = name.removeprefix("no-")
            cc._require(
                feature in self.causal.all_features,
                f"unknown ablation feature {feature!r}",
            )
            return cc.ConditionSpec(
                name=name,
                description=f"full input with {feature!r} removed; 13 features active",
                frame_source="cached",
                active_features=tuple(
                    item for item in self.causal.all_features if item != feature
                ),
            )
        raise ValueError(f"unknown P3-T12 condition {name!r}")

    def removed_feature_of(self, name: str) -> str | None:
        return name.removeprefix("no-") if name in ABLATION_NAMES else None

    def duration_for(self, name: str, *, smoke_ms: float | None) -> float:
        base = float(smoke_ms) if smoke_ms is not None else self.base_duration_ms
        if name == WASHOUT_NAME:
            return base + float(self.washout["extra_ms"])
        return base

    def prefix_cutoff_for(self, *, smoke_ms: float | None) -> float:
        return float(smoke_ms) if smoke_ms is not None else self.base_duration_ms

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "CharacterizationConfig":
        raw = cc._load_yaml(path)
        version = raw.get("version")
        cc._require(
            isinstance(version, str) and bool(version),
            "version must be a non-empty string",
        )
        causal = cc.CausalControlConfig.load(
            PROJECT_ROOT / str(raw["causal_control_config"])
        )
        conditions = tuple(str(item) for item in raw.get("conditions", ()))
        expected = ("C0", "C1", "C2", "C3") + ABLATION_NAMES + (WASHOUT_NAME,)
        cc._require(
            conditions == expected,
            f"conditions must be exactly {list(expected)} in that order",
        )
        subprocess_conditions = tuple(
            str(item) for item in raw.get("subprocess_conditions", ())
        )
        cc._require(
            subprocess_conditions and set(subprocess_conditions) <= set(conditions),
            "subprocess_conditions must name configured conditions",
        )
        repeats = raw.get("repeats")
        cc._require(
            isinstance(repeats, int) and not isinstance(repeats, bool) and repeats >= 2,
            "repeats must be an integer >= 2",
        )
        sampling = raw.get("sampling")
        cc._require(isinstance(sampling, dict), "sampling must be a mapping")
        for key in (
            "bin_ms",
            "partition_bin_ms",
            "membrane_sample_interval_ms",
            "tail_window_ms",
        ):
            value = sampling.get(key)
            cc._require(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and float(value) > 0,
                f"sampling.{key} must be positive",
            )
        edges = sampling.get("membrane_histogram_edges_mv")
        cc._require(
            isinstance(edges, list)
            and len(edges) >= 3
            and all(second > first for first, second in zip(edges, edges[1:])),
            "membrane histogram edges must increase",
        )
        rate_edges = sampling.get("rate_histogram_edges_hz")
        cc._require(
            isinstance(rate_edges, list)
            and len(rate_edges) >= 3
            and all(second > first for first, second in zip(rate_edges, rate_edges[1:])),
            "rate histogram edges must increase",
        )
        buckets = sampling.get("distance_bucket_edges")
        cc._require(
            isinstance(buckets, list)
            and len(buckets) >= 2
            and all(second > first for first, second in zip(buckets, buckets[1:])),
            "distance bucket edges must increase",
        )
        margin = sampling.get("near_threshold_margin_mv")
        cc._require(
            isinstance(margin, (int, float))
            and not isinstance(margin, bool)
            and float(margin) > 0,
            "near_threshold_margin_mv must be positive",
        )
        washout = raw.get("washout")
        cc._require(isinstance(washout, dict), "washout must be a mapping")
        cc._require(
            str(washout.get("name")) == WASHOUT_NAME
            and str(washout.get("base_condition")) == BASELINE_NAME,
            "washout must extend C3 under the name C3-washout",
        )
        extra = float(washout.get("extra_ms", 0.0))
        silent = float(washout.get("silent_window_ms", 0.0))
        # 250 ms is the hard-coded scheduler max_hold_ms; the extra window must
        # cross it or the condition would not observe post-drive dynamics.
        cc._require(
            extra >= 250.0 + silent and silent > 0.0,
            "washout extra_ms must cover the 250 ms hold ceiling plus a silent window",
        )
        output = PROJECT_ROOT / str(raw["output"])
        smoke_output = PROJECT_ROOT / str(raw["smoke_output"])
        cc._require(output != smoke_output, "full and smoke outputs must differ")
        limitations = tuple(str(item) for item in raw.get("limitations", ()))
        cc._require(limitations, "limitations must be listed")
        return cls(
            source_path=path,
            version=str(version),
            description=str(raw.get("description", "")).strip(),
            causal=causal,
            output=output,
            smoke_output=smoke_output,
            repeats=int(repeats),
            conditions=conditions,
            subprocess_conditions=subprocess_conditions,
            sampling=sampling,
            washout=washout,
            limitations=limitations,
        )


# --------------------------------------------------------------------------
# measurement helpers
# --------------------------------------------------------------------------


def _percentiles(values: np.ndarray, points) -> dict[str, float]:
    if values.size == 0:
        return {str(int(point)): 0.0 for point in points}
    computed = np.percentile(values, [float(point) for point in points])
    return {
        str(int(point)): round(float(value), 6)
        for point, value in zip(points, computed)
    }


def membrane_snapshot(
    potential: np.ndarray,
    refractory_steps: np.ndarray,
    params,
    *,
    histogram_edges,
    percentiles,
    near_threshold_margin_mv: float,
) -> dict:
    """Summary of the whole membrane population at one sampled step.

    Histogram edges are fixed for comparability, so values outside the edge
    range are clipped into the terminal bins and counted separately.
    """
    edges = np.asarray(histogram_edges, dtype=np.float64)
    outside = int(
        np.count_nonzero((potential < edges[0]) | (potential > edges[-1]))
    )
    counts, _ = np.histogram(np.clip(potential, edges[0], edges[-1]), bins=edges)
    at_floor = int(np.count_nonzero(potential <= params.minimum_potential_mv))
    near_threshold = int(
        np.count_nonzero(potential >= params.threshold_mv - near_threshold_margin_mv)
    )
    refractory = int(np.count_nonzero(refractory_steps > 0))
    return {
        "n_neurons": int(potential.size),
        "min_mv": round(float(potential.min()), 6),
        "max_mv": round(float(potential.max()), 6),
        "mean_mv": round(float(potential.mean()), 6),
        "std_mv": round(float(potential.std()), 6),
        "percentiles_mv": _percentiles(potential, percentiles),
        "histogram_counts": [int(value) for value in counts],
        "histogram_out_of_range": outside,
        "at_floor": at_floor,
        "near_threshold": near_threshold,
        "refractory": refractory,
    }


def first_spike_times(
    spike_times: np.ndarray, spike_neurons: np.ndarray, n: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Earliest spike time per neuron; ``inf`` for silent neurons.

    Returns ``(first_times, unique_neurons, first_indices)``. Spike times are
    recorded in non-decreasing order, so the first occurrence of a neuron in
    the record is its earliest spike.
    """
    result = np.full(int(n), np.inf, dtype=np.float64)
    if spike_neurons.size == 0:
        return result, np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    unique, index = np.unique(spike_neurons, return_index=True)
    result[unique] = spike_times[index]
    return result, unique, index


def longest_interval_gap(times: np.ndarray) -> float:
    if times.size < 2:
        return 0.0
    largest = 0.0
    chunk = 1_000_000
    for start in range(0, times.size - 1, chunk):
        stop = min(start + chunk, times.size - 1)
        largest = max(largest, float(np.max(times[start + 1 : stop + 1] - times[start:stop])))
    return round(largest, 4)


def longest_active_run(occupied: np.ndarray) -> int:
    longest = current = 0
    for value in occupied:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return int(longest)


def bin_counts(values: np.ndarray, edges: np.ndarray) -> list[int]:
    if values.size == 0:
        return [0] * (edges.size - 1)
    return [int(value) for value in np.histogram(values, bins=edges)[0]]


def distance_from_sources(graph, sources: np.ndarray) -> np.ndarray:
    """Directed, unweighted hop distance from any source to every node."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra

    sources = np.asarray(sources, dtype=np.int64)
    if sources.size == 0:
        return np.full(graph.n_nodes, np.inf)
    adjacency = csr_matrix(
        (
            np.ones(graph.n_edges, dtype=np.int8),
            graph.edge_dst,
            graph.out_indptr,
        ),
        shape=(graph.n_nodes, graph.n_nodes),
    )
    distances = dijkstra(
        adjacency,
        directed=True,
        indices=sources,
        unweighted=True,
        min_only=True,
    )
    return np.asarray(distances, dtype=np.float64)


def distance_bucket_labels(distances: np.ndarray, edges) -> np.ndarray:
    edges = np.asarray(edges, dtype=np.float64)
    finite = np.where(np.isinf(distances), edges[-1], distances)
    labels = np.digitize(finite, edges[1:], right=False)
    # The last bucket means ">= last edge"; unreachable is labelled separately.
    labels = np.where(np.isinf(distances), edges.size - 1, labels)
    return labels.astype(np.int64)


def distance_bucket_name(position: int, edges) -> str:
    edges = [int(value) for value in edges]
    if position < len(edges) - 1:
        if edges[position + 1] - edges[position] == 1:
            return str(edges[position])
        return f"{edges[position]}-{edges[position + 1] - 1}"
    return "unreachable_or_far"


def distance_bucket_stats(
    distances: np.ndarray,
    first_times: np.ndarray,
    counts: np.ndarray,
    spike_times: np.ndarray,
    spike_neurons: np.ndarray,
    edges,
    *,
    duration_ms: float,
) -> dict:
    labels = distance_bucket_labels(distances, edges)
    n_buckets = len(edges)
    active = counts > 0
    result = {}
    for position in range(n_buckets):
        selected = labels == position
        n_neurons = int(np.count_nonzero(selected))
        if n_neurons == 0:
            result[distance_bucket_name(position, edges)] = {
                "n_neurons": 0,
                "active_neurons": 0,
                "spikes": 0,
                "firing_rate_hz": 0.0,
                "first_active_ms": None,
                "median_first_spike_ms": None,
            }
            continue
        bucket_active = selected & active
        spikes = int(counts[selected].sum())
        spike_mask = selected[spike_neurons]
        first = first_times[bucket_active]
        result[distance_bucket_name(position, edges)] = {
            "n_neurons": n_neurons,
            "active_neurons": int(np.count_nonzero(bucket_active)),
            "spikes": spikes,
            "firing_rate_hz": round(
                spikes / (n_neurons * duration_ms / 1000.0), 6
            ),
            "first_active_ms": (
                round(float(first.min()), 4) if first.size else None
            ),
            "median_first_spike_ms": (
                round(float(np.median(first)), 4) if first.size else None
            ),
            "last_spike_ms": (
                round(float(spike_times[spike_mask].max()), 4)
                if spike_mask.any()
                else None
            ),
        }
    return result


def last_drive_step(scheduler, n_nodes: int, n_steps: int, dt_ms: float) -> int | None:
    """Last step index at which the schedule adds any current at all."""
    if scheduler is None:
        return None
    buffer = np.zeros(int(n_nodes), dtype=np.float64)
    for step in range(n_steps - 1, -1, -1):
        buffer.fill(0.0)
        scheduler.apply(step, step * dt_ms, buffer)
        if buffer.any():
            return int(step)
    return None


# --------------------------------------------------------------------------
# instrumented run
# --------------------------------------------------------------------------


def _memory_breakdown(graph, neurons, synapses, recorder) -> dict:
    graph_bytes = sum(
        value.nbytes
        for value in vars(graph).values()
        if isinstance(value, np.ndarray)
    )
    retained = (
        graph_bytes
        + neurons.memory_bytes
        + synapses.memory_bytes
        + recorder.memory_bytes
    )
    return {
        "graph_arrays_bytes": int(graph_bytes),
        "neuron_state_bytes": int(neurons.memory_bytes),
        "synapse_state_bytes": int(synapses.memory_bytes),
        "spike_recorder_bytes": int(recorder.memory_bytes),
        "retained_arrays_bytes": int(retained),
        "recorder_capacity": int(recorder.capacity),
        "recorder_capacity_bytes": int(
            type(recorder).capacity_bytes(recorder.capacity)
        ),
    }


def run_instrumented(
    spec: cc.ConditionSpec,
    cfg: CharacterizationConfig,
    setup,
    neuron_params,
    synapse_params,
    cache,
    *,
    duration_ms: float,
    smoke_ms: float | None,
    window_start_ms: float | None = None,
    prefix_cutoff_ms: float | None = None,
) -> tuple[dict, dict]:
    """One run of the exact BrainSimulator step order with read-only sampling."""
    causal = cfg.causal
    sampling = cfg.sampling
    dt_ms = float(causal.reference["dt_ms"])
    n_steps = int(round(duration_ms / dt_ms))
    n = int(setup.mapping.graph.n_nodes)
    bin_ms = float(sampling["bin_ms"])
    partition_bin_ms = float(sampling["partition_bin_ms"])
    sample_steps = max(
        1, int(round(float(sampling["membrane_sample_interval_ms"]) / dt_ms))
    )
    edges = np.asarray(
        [float(value) for value in sampling["membrane_histogram_edges_mv"]],
        dtype=np.float64,
    )
    percentiles = tuple(sampling["membrane_percentiles"])
    near_margin = float(sampling["near_threshold_margin_mv"])

    frames = cc.resolve_frames(spec, causal, cache, smoke_ms=smoke_ms)
    scheduler = cc.build_scheduler(spec, setup, frames)
    active_features = cc.active_feature_names(spec, setup)
    active = cc.indices_for_features(setup, active_features)
    reference = cc.indices_for_features(setup, tuple(setup.encoders))
    feature_indices = cc.feature_index_map(setup)
    in_active = np.zeros(n, dtype=bool)
    in_active[active] = True
    in_reference = np.zeros(n, dtype=bool)
    in_reference[reference] = True

    cc._require(
        float(causal.reference["background_current_pa"]) == 0.0
        and float(causal.reference["noise_std_pa"]) == 0.0,
        "P3-T12 requires background and noise to be zero",
    )

    graph = setup.mapping.graph
    neurons = LIFPopulation(n, neuron_params, dt_ms)
    synapses = SynapseModel(graph, synapse_params, dt_ms)
    recorder = SpikeRecorder(n, int(causal.reference["max_recorded_spikes"]))
    current = np.zeros(n, dtype=np.float64)
    potential = neurons.membrane_potential
    refractory = neurons.refractory_steps

    floor_steps = 0
    refractory_steps = 0
    near_threshold_steps = 0
    exact_min = math.inf
    exact_max = -math.inf
    snapshots = []
    capacity_exceeded = False
    capacity_message = None

    process = psutil.Process()
    rss_before = process.memory_info().rss
    started = time.perf_counter()
    try:
        for step in range(n_steps):
            synapses.advance()
            current.fill(0.0)
            current += synapses.synaptic_current_pa
            if scheduler is not None:
                scheduler.apply(step, step * dt_ms, current)
            spikes = neurons.step(current)
            recorder.record(step, spikes, dt_ms)
            synapses.propagate(spikes)

            exact_min = min(exact_min, float(potential.min()))
            exact_max = max(exact_max, float(potential.max()))
            floor_steps += int(
                np.count_nonzero(potential <= neuron_params.minimum_potential_mv)
            )
            refractory_steps += int(np.count_nonzero(refractory > 0))
            near_threshold_steps += int(
                np.count_nonzero(
                    potential >= neuron_params.threshold_mv - near_margin
                )
            )
            if (step + 1) % 200 == 0:
                arrays = (
                    potential,
                    synapses.excitatory_current_pa,
                    synapses.inhibitory_current_pa,
                )
                if not all(np.isfinite(array).all() for array in arrays):
                    raise FloatingPointError("non-finite state detected")
            if (step + 1) % sample_steps == 0:
                snapshot = membrane_snapshot(
                    potential,
                    refractory,
                    neuron_params,
                    histogram_edges=edges,
                    percentiles=percentiles,
                    near_threshold_margin_mv=near_margin,
                )
                snapshot["time_ms"] = round((step + 1) * dt_ms, 4)
                snapshots.append(snapshot)
    except SpikeCapacityExceeded as exc:  # pragma: no cover - invalid run path
        capacity_exceeded = True
        capacity_message = str(exc)
    wall = time.perf_counter() - started
    rss_after = process.memory_info().rss

    times = np.asarray(recorder.spike_times_ms, dtype=np.float64)
    neuron_indices = np.asarray(recorder.spike_neuron_indices, dtype=np.int64)
    counts = np.asarray(recorder.spike_counts(), dtype=np.int64)
    duration_ms = n_steps * dt_ms

    partitions = cc._partition_block(
        counts,
        times,
        neuron_indices,
        reference=reference,
        active=active,
        duration_ms=duration_ms,
        bin_ms=partition_bin_ms,
    )
    activity = recorder.summary(duration_ms, bin_ms=10.0)

    first_times, unique_neurons, first_indices = first_spike_times(
        times, neuron_indices, n
    )
    bin_edges = cc._bin_edges(duration_ms, bin_ms)
    n_bins = bin_edges.size - 1
    bin_index = (
        np.minimum((np.floor(times / bin_ms)).astype(np.int64), n_bins - 1)
        if times.size
        else np.empty(0, dtype=np.int64)
    )
    active_mask_spikes = in_active[neuron_indices] if times.size else np.zeros(0, dtype=bool)

    total_bins = bin_counts(times, bin_edges)
    active_bins = bin_counts(times[active_mask_spikes], bin_edges)
    outside_active_bins = bin_counts(times[~active_mask_spikes], bin_edges)
    reference_mask_spikes = in_reference[neuron_indices] if times.size else np.zeros(0, dtype=bool)
    outside_reference_bins = bin_counts(times[~reference_mask_spikes], bin_edges)

    silent = np.isinf(first_times)
    active_neurons = ~silent
    first_bin = np.full(n, -1, dtype=np.int64)
    if times.size:
        first_bin[unique_neurons] = bin_index[first_indices]
    new_per_bin = np.bincount(
        first_bin[first_bin >= 0], minlength=n_bins
    ).astype(np.int64)
    cumulative_fraction = np.cumsum(new_per_bin) / float(n)
    checkpoints = {}
    for point in sampling["recruitment_checkpoints"]:
        hits = np.flatnonzero(cumulative_fraction >= float(point))
        checkpoints[str(point)] = (
            round(float(bin_edges[int(hits[0]) + 1]), 4) if hits.size else None
        )

    rates_all = counts / (duration_ms / 1000.0)
    rates_active = rates_all[active_neurons]
    tail_start = max(0.0, duration_ms - float(sampling["tail_window_ms"]))
    tail_mask = times >= tail_start if times.size else np.zeros(0, dtype=bool)
    tail_counts = (
        np.bincount(neuron_indices[tail_mask], minlength=n)
        if times.size
        else np.zeros(n, dtype=np.int64)
    )
    tail_duration_s = max(1e-9, (duration_ms - tail_start) / 1000.0)
    tail_rates = tail_counts / tail_duration_s
    rate_edges = np.asarray(
        [float(value) for value in sampling["rate_histogram_edges_hz"]],
        dtype=np.float64,
    )
    sorted_counts = np.sort(counts)[::-1]
    top_n = max(1, int(math.ceil(0.01 * n)))
    top_share = (
        float(sorted_counts[:top_n].sum()) / float(counts.sum())
        if counts.sum()
        else 0.0
    )

    partitions_bins = {
        "bin_ms": bin_ms,
        "edges_ms": [round(float(value), 4) for value in bin_edges],
        "total": total_bins,
        "active": active_bins,
        "outside_active": outside_active_bins,
        "outside_reference": outside_reference_bins,
        "new_active_neurons": [int(value) for value in new_per_bin],
        "cumulative_active_fraction": [
            round(float(value), 8) for value in cumulative_fraction
        ],
    }
    occupied = np.asarray(outside_active_bins) > 0
    persistence = {
        "bins": int(n_bins),
        "bins_with_any_spike": int(np.count_nonzero(np.asarray(total_bins) > 0)),
        "bins_with_outside_active_spike": int(np.count_nonzero(occupied)),
        "fraction_bins_outside_active": round(
            float(np.count_nonzero(occupied)) / max(1, n_bins), 6
        ),
        "longest_outside_active_run_bins": longest_active_run(occupied),
        "longest_outside_active_run_ms": round(
            longest_active_run(occupied) * bin_ms, 4
        ),
        "longest_gap_ms": {
            "total": longest_interval_gap(times),
            "active": longest_interval_gap(times[active_mask_spikes]),
            "outside_active": longest_interval_gap(times[~active_mask_spikes]),
            "outside_reference": longest_interval_gap(times[~reference_mask_spikes]),
        },
        "tail_window_ms": float(sampling["tail_window_ms"]),
        "tail_spikes": int(tail_counts.sum()),
        "tail_active_neurons": int(np.count_nonzero(tail_counts)),
        "tail_mean_rate_hz": round(float(tail_rates.mean()), 6),
        "tail_outside_active_spikes": int(
            tail_counts[~in_active].sum()
        ),
    }

    post_drive = None
    if window_start_ms is not None:
        start = float(window_start_ms)
        window_mask = times >= start
        pre_mask = (times >= start - float(sampling["tail_window_ms"])) & (
            times < start
        )
        window_edges = cc._bin_edges(duration_ms - start, 50.0) + start
        window_seconds = max(1e-9, (duration_ms - start) / 1000.0)
        pre_seconds = max(1e-9, min(float(sampling["tail_window_ms"]), start) / 1000.0)
        window_spikes = int(np.count_nonzero(window_mask))
        pre_spikes = int(np.count_nonzero(pre_mask))
        post_drive = {
            "start_ms": round(start, 4),
            "duration_ms": round(duration_ms - start, 4),
            "start_rule": (
                "first step after the last step on which the schedule adds "
                "any current"
            ),
            "bin_ms": 50.0,
            "bin_edges_ms": [round(float(value), 4) for value in window_edges],
            "spikes_per_bin": bin_counts(times[window_mask], window_edges),
            "outside_active_per_bin": bin_counts(
                times[window_mask & ~active_mask_spikes], window_edges
            ),
            "reference_per_bin": bin_counts(
                times[window_mask & reference_mask_spikes], window_edges
            ),
            "spikes": window_spikes,
            "outside_active_spikes": int(
                np.count_nonzero(window_mask & ~active_mask_spikes)
            ),
            "active_neurons": int(
                np.unique(neuron_indices[window_mask]).size
                if window_mask.any()
                else 0
            ),
            "first_spike_ms": (
                round(float(times[window_mask].min()), 4)
                if window_mask.any()
                else None
            ),
            "last_spike_ms": (
                round(float(times[window_mask].max()), 4)
                if window_mask.any()
                else None
            ),
            "window_rate_hz": round(window_spikes / (n * window_seconds), 6),
            "pre_window_rate_hz": round(pre_spikes / (n * pre_seconds), 6),
            "rate_ratio_vs_pre_window": (
                round(
                    (window_spikes / window_seconds) / (pre_spikes / pre_seconds), 6
                )
                if pre_spikes
                else None
            ),
        }

    prefix_counts = None
    if prefix_cutoff_ms is not None:
        prefix_mask = times <= float(prefix_cutoff_ms) + 1e-6
        prefix_counts = (
            np.bincount(neuron_indices[prefix_mask], minlength=n)
            if times.size
            else np.zeros(n, dtype=np.int64)
        )

    topology = None
    if active.size:
        distances = distance_from_sources(graph, active)
        topology = {
            "source_partition": "A_c",
            "definition": "directed unweighted hop distance from the injected set",
            "bucket_edges": [int(value) for value in sampling["distance_bucket_edges"]],
            "buckets": distance_bucket_stats(
                distances,
                first_times,
                counts,
                times,
                neuron_indices,
                sampling["distance_bucket_edges"],
                duration_ms=duration_ms,
            ),
        }

    source_mask = in_active[neuron_indices] if times.size else np.zeros(0, dtype=bool)
    propagation = {
        "first_spike_ms": float(times.min()) if times.size else None,
        "first_active_ms": (
            float(times[source_mask].min()) if source_mask.any() else None
        ),
        "first_outside_active_ms": (
            float(times[~source_mask].min()) if (~source_mask).any() else None
        ),
        "first_outside_reference_ms": (
            float(times[~reference_mask_spikes].min())
            if (~reference_mask_spikes).any()
            else None
        ),
        "last_spike_ms": float(times.max()) if times.size else None,
        "activations_reaching_checkpoints": checkpoints,
        "transmissions_per_spike": None,
        "outside_active_cascade_ratio_by_bin": [
            round(
                float(outside_active_bins[index])
                / max(1.0, float(outside_active_bins[index - 1])),
                6,
            )
            for index in range(1, n_bins)
        ],
    }
    if times.size:
        propagation["transmissions_per_spike"] = round(
            float(synapses.total_transmissions) / float(times.size), 6
        )

    memory = _memory_breakdown(graph, neurons, synapses, recorder)
    del neurons, synapses

    audit = cc.audit_currents(
        scheduler,
        n_nodes=n,
        n_steps=n_steps,
        dt_ms=dt_ms,
        feature_indices=feature_indices,
        active_indices=active,
        pulse_windows=cc.pulse_windows(scheduler),
    )

    digest = {
        "spike_counts_sha256": cc._digest_array(counts),
        "activity_summary_sha256": cc._digest_json(activity),
        "current_trace_sha256": audit["current_trace_sha256"],
        "scheduler_signature_sha256": cc.scheduler_signature_digest(scheduler),
        "cache_frames_digest": (
            cache.frames_digest if spec.frame_source == "cached" else None
        ),
        "spikes_total": int(counts.sum()),
        "first_spike_ms": float(times.min()) if times.size else None,
        "last_spike_ms": float(times.max()) if times.size else None,
    }

    item = {
        "condition": spec.name,
        "description": spec.description,
        "frame_source": spec.frame_source,
        "active_features": list(active_features),
        "n_active_features": len(active_features),
        "n_active_neurons": int(active.size),
        "n_reference_neurons": int(reference.size),
        "removed_feature": cfg.removed_feature_of(spec.name),
        "duration_ms": float(duration_ms),
        "n_steps": int(n_steps),
        "scheduler": {
            "present": scheduler is not None,
            "n_frames": len(frames),
            "n_stimulated_neurons": (
                int(scheduler.stimulated_indices.size) if scheduler is not None else 0
            ),
            "horizon_ms": scheduler.horizon_ms if scheduler is not None else None,
            "last_drive_step": last_drive_step(scheduler, n, n_steps, dt_ms),
            "signature_sha256": digest["scheduler_signature_sha256"],
        },
        "cache_frames_digest": digest["cache_frames_digest"],
        "spike_capacity_exceeded": capacity_exceeded,
        "spike_capacity_message": capacity_message,
        "spike_capacity": int(causal.reference["max_recorded_spikes"]),
        "partitions": partitions,
        "spikes_by_feature": {
            feature: int(counts[indices].sum())
            for feature, indices in feature_indices.items()
        },
        "simulation": {
            "duration_ms": float(duration_ms),
            "n_steps": int(n_steps),
            "wall_runtime_s": round(wall, 4),
            "steps_per_second_wall": round(n_steps / wall, 2) if wall > 0 else None,
            "spikes_total": int(counts.sum()),
            "activity": activity,
            "diagnostics_stepwise": {
                "finite_state": True,
                "min_membrane_mv": round(exact_min, 9) if math.isfinite(exact_min) else None,
                "max_membrane_mv": round(exact_max, 9) if math.isfinite(exact_max) else None,
                "at_floor_neuron_steps": int(floor_steps),
                "refractory_neuron_steps": int(refractory_steps),
                "near_threshold_neuron_steps": int(near_threshold_steps),
                "neuron_steps": int(n * n_steps),
                "at_floor_fraction": round(floor_steps / float(n * n_steps), 9),
                "refractory_fraction": round(refractory_steps / float(n * n_steps), 9),
                "near_threshold_fraction": round(
                    near_threshold_steps / float(n * n_steps), 9
                ),
            },
            "membrane_samples": snapshots,
            "memory": memory,
            "rss_before_mb": round(rss_before / 1024**2, 3),
            "rss_after_mb": round(rss_after / 1024**2, 3),
            "rss_delta_mb": round((rss_after - rss_before) / 1024**2, 3),
        },
        "activity_by_partition": {
            "graph_n_neurons": n,
            "graph_active_neurons": int(np.count_nonzero(counts)),
            "active_fraction": round(float(np.count_nonzero(counts)) / n, 8),
            "active_neurons": int(np.count_nonzero(counts)),
            "active_neurons_in_active_set": int(
                np.count_nonzero(counts[in_active])
            ),
            "active_neurons_outside_active_set": int(
                np.count_nonzero(counts[~in_active])
            ),
            "active_neurons_in_reference": int(np.count_nonzero(counts[in_reference])),
            "active_neurons_outside_reference": int(
                np.count_nonzero(counts[~in_reference])
            ),
        },
        "firing_rate_distribution": {
            "duration_s": round(duration_ms / 1000.0, 6),
            "all_neurons": {
                "mean_hz": round(float(rates_all.mean()), 6),
                "percentiles_hz": _percentiles(
                    rates_all, sampling["rate_percentiles"]
                ),
                "histogram_edges_hz": [float(value) for value in rate_edges],
                "histogram_counts": bin_counts(rates_all, rate_edges),
            },
            "active_neurons": {
                "n": int(rates_active.size),
                "mean_hz": round(float(rates_active.mean()), 6)
                if rates_active.size
                else 0.0,
                "percentiles_hz": _percentiles(
                    rates_active, sampling["rate_percentiles"]
                ),
            },
            "tail_window": {
                "window_ms": float(sampling["tail_window_ms"]),
                "start_ms": round(tail_start, 4),
                "mean_hz": round(float(tail_rates.mean()), 6),
                "percentiles_hz": _percentiles(
                    tail_rates, sampling["rate_percentiles"]
                ),
            },
            "top_one_percent_spike_share": round(top_share, 8),
        },
        "recruitment": {
            "bin_ms": bin_ms,
            "checkpoints_fraction_to_time_ms": checkpoints,
            "new_active_neurons_per_bin": [int(value) for value in new_per_bin],
            "cumulative_active_fraction": [
                round(float(value), 8) for value in cumulative_fraction
            ],
        },
        "binned_activity": partitions_bins,
        "persistence": persistence,
        "post_drive_window": post_drive,
        "propagation": propagation,
        "topology": topology,
        "reproducibility_hashes": digest,
    }

    item["current_audit"] = audit
    # P3-T3.1 reads the legacy activity-detection flag; reproduce its exact
    # definition so the quoted classification is internally consistent.
    item["ignition"] = {
        "ignited": bool(item["partitions"]["outside_reference"]["spikes"] > 0),
        "definition": (
            "legacy activity detection: true if at least one spike occurred "
            "outside the fixed reference set R; not a population-scale "
            "criterion"
        ),
    }
    item["ignition_classification"] = ir.classify_condition(item)
    internal = {
        "counts": counts,
        "prefix_counts": prefix_counts,
        "n_neurons": n,
    }
    return item, internal


def run_repeated(
    spec: cc.ConditionSpec,
    cfg: CharacterizationConfig,
    setup,
    neuron_params,
    synapse_params,
    cache,
    *,
    duration_ms: float,
    smoke_ms: float | None,
    repeats: int,
    window_start_ms: float | None = None,
    prefix_cutoff_ms: float | None = None,
) -> tuple[dict, dict]:
    """Run a condition ``repeats`` times; only the first run's arrays are kept."""
    first, internal = run_instrumented(
        spec,
        cfg,
        setup,
        neuron_params,
        synapse_params,
        cache,
        duration_ms=duration_ms,
        smoke_ms=smoke_ms,
        window_start_ms=window_start_ms,
        prefix_cutoff_ms=prefix_cutoff_ms,
    )
    hashes = [first["reproducibility_hashes"]]
    for _ in range(max(1, int(repeats)) - 1):
        item, _discarded = run_instrumented(
            spec,
            cfg,
            setup,
            neuron_params,
            synapse_params,
            cache,
            duration_ms=duration_ms,
            smoke_ms=smoke_ms,
            window_start_ms=window_start_ms,
            prefix_cutoff_ms=prefix_cutoff_ms,
        )
        hashes.append(item["reproducibility_hashes"])
    differences = [
        key
        for key in REPRODUCIBLE_KEYS
        if len({json.dumps(entry[key], sort_keys=True) for entry in hashes}) > 1
    ]
    first["reproducibility"] = {
        "n_runs": len(hashes),
        "identical": not differences,
        "differences": differences,
        "hashes": hashes,
    }
    return first, internal


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------


def archived_equivalence(item: dict, cfg: CharacterizationConfig) -> dict:
    """Full-duration C3 must reproduce the archived P3-T2 reference exactly."""
    causal = cfg.causal
    archive_path = PROJECT_ROOT / "experiments/phase_3c/results/p3_t2_full.json"
    reference = {}
    if archive_path.is_file():
        payload = json.loads(archive_path.read_text(encoding="utf-8"))
        entry = payload["conditions"]["C3"]
        reference = {
            "spikes_total": entry["simulation"]["spikes_total"],
            "spikes_stimulated": entry["simulation"]["activity_by_stimulation"][
                "stimulated_spikes"
            ],
            "spikes_unstimulated": entry["simulation"]["activity_by_stimulation"][
                "non_stimulated_spikes"
            ],
            "first_spike_ms": entry["reproducibility_hashes"]["first_spike_ms"],
            "last_spike_ms": entry["reproducibility_hashes"]["last_spike_ms"],
            "min_membrane_mv": entry["simulation"]["diagnostics"]["min_membrane_mv"],
            "max_membrane_mv": entry["simulation"]["diagnostics"]["max_membrane_mv"],
        }
    measured = {
        "spikes_total": int(item["simulation"]["spikes_total"]),
        "spikes_stimulated": int(item["partitions"]["active"]["spikes"]),
        "spikes_unstimulated": int(item["partitions"]["outside_active"]["spikes"]),
        "first_spike_ms": item["reproducibility_hashes"]["first_spike_ms"],
        "last_spike_ms": item["reproducibility_hashes"]["last_spike_ms"],
        "min_membrane_mv": item["simulation"]["diagnostics_stepwise"]["min_membrane_mv"],
        "max_membrane_mv": item["simulation"]["diagnostics_stepwise"]["max_membrane_mv"],
    }
    checks = {
        "spike_counts_sha256": (
            item["reproducibility_hashes"]["spike_counts_sha256"]
            == causal.archived["spike_counts_sha256"]
        ),
        "scheduler_signature_sha256": (
            item["scheduler"]["signature_sha256"]
            == causal.archived["scheduler_sha256"]
        ),
        "spikes_total": measured["spikes_total"] == int(causal.archived["spikes_total"]),
        "spikes_stimulated": measured["spikes_stimulated"]
        == int(causal.archived["spikes_stimulated"]),
        "spikes_unstimulated": measured["spikes_unstimulated"]
        == int(causal.archived["spikes_unstimulated"]),
    }
    if reference:
        checks["first_spike_ms"] = (
            measured["first_spike_ms"] == reference["first_spike_ms"]
        )
        checks["last_spike_ms"] = (
            measured["last_spike_ms"] == reference["last_spike_ms"]
        )
        # Step-wise extrema can be more extreme than the 100 ms diagnostics
        # sample; equality is required only when the diagnostic value binds.
        checks["min_membrane_mv"] = (
            measured["min_membrane_mv"] <= reference["min_membrane_mv"] + 1e-6
        )
        checks["max_membrane_mv"] = (
            measured["max_membrane_mv"] <= reference["max_membrane_mv"] + 1e-6
        )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "archived": {
            "spike_counts_sha256": causal.archived["spike_counts_sha256"],
            "scheduler_sha256": causal.archived["scheduler_sha256"],
            "spikes_total": int(causal.archived["spikes_total"]),
            "spikes_stimulated": int(causal.archived["spikes_stimulated"]),
            "spikes_unstimulated": int(causal.archived["spikes_unstimulated"]),
        },
        "measured": measured,
        "archive_payload": (
            str(archive_path.relative_to(PROJECT_ROOT))
            if archive_path.is_file()
            else None
        ),
        "reference": reference,
    }


def prefix_gate(
    washout: dict,
    c3: dict,
    washout_internal: dict,
    c3_internal: dict,
    *,
    cutoff_ms: float,
) -> dict:
    """The washout extension must be bit-identical to C3 up to the cutoff."""
    washout_counts = washout_internal["prefix_counts"]
    c3_counts = c3_internal["counts"]
    if washout_counts is None or c3_counts is None:
        return {"passed": None, "reason": "prefix counts unavailable"}
    equal = bool(np.array_equal(washout_counts, c3_counts))
    return {
        "passed": equal,
        "cutoff_ms": float(cutoff_ms),
        "n_neurons": int(c3_counts.size),
        "prefix_spikes": int(washout_counts.sum()),
        "c3_spikes": int(c3_counts.sum()),
        "prefix_counts_sha256": cc._digest_array(washout_counts),
        "c3_counts_sha256": cc._digest_array(c3_counts),
        "identical": equal,
    }


def condition_checks(
    spec: cc.ConditionSpec, item: dict, cfg: CharacterizationConfig
) -> tuple[dict, list[str]]:
    checks: dict[str, bool | None] = {}
    not_evaluated: list[str] = []
    audit = item["current_audit"]
    if spec.frame_source == "none":
        checks["no_scheduler"] = not item["scheduler"]["present"]
        checks["no_current_injected"] = audit["total_injected_pa_steps"] == 0.0
    else:
        checks["scheduler_present"] = item["scheduler"]["present"]
        checks["no_current_outside_active"] = audit["n_indices_outside_active"] == 0
        checks["current_injected"] = audit["total_injected_pa_steps"] > 0.0
    if spec.name in (BASELINE_NAME, WASHOUT_NAME):
        checks["reference_equals_active"] = (
            item["n_active_neurons"] == item["n_reference_neurons"]
        )
    if spec.name in ABLATION_NAMES:
        removed = cfg.removed_feature_of(spec.name)
        checks["thirteen_features_active"] = item["n_active_features"] == 13
        checks["removed_feature_zero_current"] = (
            audit["peak_feature_current_pa"][removed] == 0.0
        )
    checks["repeats_identical"] = item["reproducibility"]["identical"]
    return checks, not_evaluated


def evaluate_invalidations(
    items: dict[str, dict],
    checks: dict[str, dict],
    cfg: CharacterizationConfig,
    *,
    mode: str,
    protected: dict,
    equivalence: dict | None,
    prefix: dict | None,
    enforce_equivalence: bool,
    enforce_prefix: bool,
) -> dict:
    triggered: list[dict] = []

    def trigger(rule: str, detail) -> None:
        triggered.append({"rule": rule, "detail": detail})

    if enforce_equivalence and (equivalence is None or not equivalence["passed"]):
        trigger(
            "loop_equivalence_failed",
            equivalence["checks"] if equivalence else "C3 not executed",
        )
    if enforce_prefix and (prefix is None or prefix.get("passed") is not True):
        trigger("prefix_mismatch", prefix)

    reference = cfg.causal.reference
    for name, item in items.items():
        if item["spike_capacity_exceeded"]:
            trigger("spike_capacity_exceeded", {"condition": name})
        diagnostics = item["simulation"]["diagnostics_stepwise"]
        if not diagnostics.get("finite_state", False):
            trigger("non_finite_state", {"condition": name})
        minimum = float(reference["minimum_potential_mv"])
        threshold = float(reference["threshold_mv"])
        if diagnostics["min_membrane_mv"] is not None and (
            diagnostics["min_membrane_mv"] < minimum - 1e-6
        ):
            trigger("membrane_below_floor", {"condition": name})
        if diagnostics["max_membrane_mv"] is not None and (
            diagnostics["max_membrane_mv"] > threshold + 1e-6
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

    for name, entry in checks.items():
        failed = sorted(key for key, value in entry.items() if value is False)
        if failed:
            trigger("condition_definition_violation", {"condition": name, "checks": failed})

    mismatched = sorted(
        name for name, entry in protected.items() if not entry["match"]
    )
    if mismatched:
        trigger("protected_hash_changed", {"inputs": mismatched})

    base_durations = {
        item["duration_ms"] for name, item in items.items() if name != WASHOUT_NAME
    }
    if len(base_durations) > 1:
        trigger("initial_conditions_differ", sorted(base_durations))
    graphs = {
        item["activity_by_partition"]["graph_n_neurons"] for item in items.values()
    }
    if len(graphs) > 1:
        trigger("initial_conditions_differ", {"graph_n_nodes": sorted(graphs)})
    if BASELINE_NAME in items and mode == "full":
        if (
            items[BASELINE_NAME]["scheduler"]["signature_sha256"]
            != cfg.causal.archived["scheduler_sha256"]
        ):
            trigger("scheduler_signature_mismatch", {"condition": BASELINE_NAME})
    return {
        "valid": not triggered,
        "triggered": triggered,
        "rules_evaluated": [
            "loop_equivalence_failed",
            "spike_capacity_exceeded",
            "non_finite_state",
            "membrane_bounds",
            "repeated_runs_differ",
            "current_outside_active_set",
            "condition_definition_violation",
            "protected_hash_changed",
            "initial_conditions_differ",
            "prefix_mismatch",
            "scheduler_signature_mismatch",
        ],
        "equivalence_enforced": bool(enforce_equivalence),
        "prefix_enforced": bool(enforce_prefix),
    }


# --------------------------------------------------------------------------
# experiment driver
# --------------------------------------------------------------------------


def _smoke_gate_note(mode: str) -> dict:
    return {
        "evaluated": mode == "full",
        "note": (
            "not applicable in smoke mode; the archived C3 comparison is only "
            "valid at the full 3,300.5 ms duration"
            if mode == "smoke"
            else "C3 compared against the archived P3-T2 reference"
        ),
    }


def run_characterization(
    *,
    condition_names: list[str],
    cfg: CharacterizationConfig,
    smoke_ms: float | None = None,
    repeats: int | None = None,
    cache_path: Path | None = None,
    require_gate: bool = True,
) -> dict:
    started = time.perf_counter()
    mode = "smoke" if smoke_ms is not None else "full"
    unknown = [name for name in condition_names if name not in cfg.conditions]
    if unknown:
        raise ValueError(f"unknown P3-T12 conditions {sorted(unknown)}")
    if mode == "full" and require_gate and BASELINE_NAME not in condition_names:
        raise ValueError("full mode requires C3 for the equivalence gate")
    if WASHOUT_NAME in condition_names and BASELINE_NAME not in condition_names:
        if require_gate:
            raise ValueError("C3-washout requires C3 for the prefix gate")

    causal = cfg.causal
    setup, neuron_params, synapse_params = cc._load_setup(causal)
    cache = cc.load_cache(causal, cache_path)
    if mode == "full":
        cc.require_cache_matches_archive(causal, cache)
    protected = cc.protected_hashes(causal)
    repeats = int(repeats if repeats is not None else cfg.repeats)
    dt_ms = float(causal.reference["dt_ms"])
    n = int(setup.mapping.graph.n_nodes)

    items: dict[str, dict] = {}
    internals: dict[str, dict] = {}
    checks: dict[str, dict] = {}
    for name in condition_names:
        spec = cfg.spec_for(name)
        duration = cfg.duration_for(name, smoke_ms=smoke_ms)
        n_steps = int(round(duration / dt_ms))
        window_start = None
        if name == WASHOUT_NAME:
            frames = cc.resolve_frames(spec, causal, cache, smoke_ms=smoke_ms)
            scheduler = cc.build_scheduler(spec, setup, frames)
            last = last_drive_step(scheduler, n, n_steps, dt_ms)
            window_start = (
                (last + 1) * dt_ms if last is not None else None
            )
            del scheduler
        prefix_cutoff = (
            cfg.prefix_cutoff_for(smoke_ms=smoke_ms)
            if name in (BASELINE_NAME, WASHOUT_NAME)
            else None
        )
        print(
            f"  {name}: {spec.frame_source} frames, "
            f"{len(spec.active_features) if spec.active_features is not None else 14}"
            f" active features, {duration:.1f} ms ({n_steps} steps), "
            f"{repeats} repetition(s)",
            flush=True,
        )
        item, internal = run_repeated(
            spec,
            cfg,
            setup,
            neuron_params,
            synapse_params,
            cache,
            duration_ms=duration,
            smoke_ms=smoke_ms,
            repeats=repeats,
            window_start_ms=window_start,
            prefix_cutoff_ms=prefix_cutoff,
        )
        items[name] = item
        internals[name] = internal
        checks[name], notes = condition_checks(spec, item, cfg)
        item["condition_checks"] = checks[name]
        item["condition_checks_not_evaluated"] = notes
        print(
            f"    spikes={item['simulation']['spikes_total']} "
            f"outside_A={item['partitions']['outside_active']['spikes']} "
            f"max_mV={item['simulation']['diagnostics_stepwise']['max_membrane_mv']} "
            f"regime={item['ignition_classification']['activity_regime']} "
            f"wall={item['simulation']['wall_runtime_s']}s",
            flush=True,
        )

    equivalence = None
    if BASELINE_NAME in items and mode == "full":
        equivalence = archived_equivalence(items[BASELINE_NAME], cfg)
    prefix = None
    if WASHOUT_NAME in items and BASELINE_NAME in items:
        prefix = prefix_gate(
            items[WASHOUT_NAME],
            items[BASELINE_NAME],
            internals[WASHOUT_NAME],
            internals[BASELINE_NAME],
            cutoff_ms=cfg.prefix_cutoff_for(smoke_ms=smoke_ms),
        )

    invalidations = evaluate_invalidations(
        items,
        checks,
        cfg,
        mode=mode,
        protected=protected,
        equivalence=equivalence,
        prefix=prefix,
        enforce_equivalence=(mode == "full" and require_gate),
        enforce_prefix=(prefix is not None),
    )

    regime_counts: dict[str, int] = {}
    for item in items.values():
        regime = item["ignition_classification"]["activity_regime"]
        regime_counts[regime] = regime_counts.get(regime, 0) + 1

    payload = {
        "phase": PHASE,
        "version": cfg.version,
        "description": cfg.description,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "smoke_ms": smoke_ms,
        "runtime_s": round(time.perf_counter() - started, 3),
        "verdict": (
            (
                "SMOKE ONLY (infrastructure validation)"
                if invalidations["valid"]
                else "SMOKE INVALID"
            )
            if mode == "smoke"
            else ("VALID" if invalidations["valid"] else "INVALID")
        ),
        "git": cc.git_state(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pid_rss_mb": round(psutil.Process().memory_info().rss / 1024**2, 3),
        },
        "config": {
            "path": str(cfg.source_path.relative_to(PROJECT_ROOT)),
            "sha256": cc._sha256(cfg.source_path),
            "causal_control_config_sha256": cc._sha256(
                PROJECT_ROOT / "configs" / "causal_control_config.yaml"
            ),
        },
        "protocol": {
            "question": (
                "How does the configured network move from localized sensory "
                "current injection into population-scale activity, and which "
                "measurable properties separate bounded sparse discharge from "
                "the P3-T2 C3 regime?"
            ),
            "conditions": {
                name: {
                    "description": cfg.spec_for(name).description,
                    "frame_source": cfg.spec_for(name).frame_source,
                    "active_features": (
                        None
                        if cfg.spec_for(name).active_features is None
                        else list(cfg.spec_for(name).active_features)
                    ),
                    "duration_ms": items[name]["duration_ms"],
                }
                for name in condition_names
            },
            "reference_set": {
                "definition": "all mapped sensory neurons (fixed R)",
                "n_neurons": items[condition_names[0]]["n_reference_neurons"],
            },
            "partitions": ["R versus outside R", "A_c versus outside A_c"],
            "sampling": dict(cfg.sampling),
            "washout": dict(cfg.washout),
            "repeats_in_process": repeats,
            "repeats_in_subprocess": list(cfg.subprocess_conditions),
            "classification_source": ir.VERSION,
        },
        "cache": {
            "path": str(cache.path.relative_to(PROJECT_ROOT)),
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
        },
        "protected_hashes": protected,
        "equivalence": {
            "full_duration_c3": equivalence,
            "smoke": _smoke_gate_note(mode),
        },
        "prefix_gate": prefix,
        "classification": {
            "version": ir.VERSION,
            "criterion": ir.POPULATION_CRITERION,
            "counts": regime_counts,
            "status": "provisional",
        },
        "conditions": items,
        "invalidations": invalidations,
        "limitations": list(cfg.limitations),
        "action_selection": "none; the chain ends at sensory current injection",
    }
    return payload


def _hash_subset(payload: dict, name: str) -> dict:
    item = payload["conditions"][name]
    keys = REPRODUCIBLE_KEYS
    return {key: item["reproducibility_hashes"][key] for key in keys}


def subprocess_reproducibility(
    payload: dict,
    *,
    condition_names: list[str],
    cfg: CharacterizationConfig,
    smoke_ms: float | None,
    cache_path: Path | None,
) -> dict:
    results = {}
    for name in condition_names:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"{name}.json"
            command = [
                sys.executable,
                "-m",
                "experiments.phase_3c.network_characterization",
                "--condition",
                name,
                "--once",
                "--no-equivalence-gate",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "P3-T12: descriptive network-ignition and stability "
            "characterization over the P3-T2 controls."
        )
    )
    parser.add_argument("--condition", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--smoke-ms", type=float, default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reproduce-subprocess", action="store_true")
    parser.add_argument(
        "--no-equivalence-gate",
        action="store_true",
        help=(
            "skip the archived C3 gate; only for fresh-subprocess reproduction "
            "of a single condition, where the parent checks equivalence"
        ),
    )
    args = parser.parse_args(argv)

    cfg = CharacterizationConfig.load()
    if args.all:
        names = list(cfg.conditions)
    elif args.condition:
        names = []
        for name in args.condition:
            if name not in cfg.conditions:
                parser.error(f"unknown condition {name!r}")
            if name not in names:
                names.append(name)
    else:
        parser.error("pass --all or at least one --condition")

    repeats = 1 if args.once else None
    payload = run_characterization(
        condition_names=names,
        cfg=cfg,
        smoke_ms=args.smoke_ms,
        repeats=repeats,
        cache_path=Path(args.cache) if args.cache else None,
        require_gate=not args.no_equivalence_gate,
    )
    if args.reproduce_subprocess:
        selected = [name for name in cfg.subprocess_conditions if name in names]
        if selected:
            payload["subprocess_reproducibility"] = subprocess_reproducibility(
                payload,
                condition_names=selected,
                cfg=cfg,
                smoke_ms=args.smoke_ms,
                cache_path=Path(args.cache) if args.cache else None,
            )
            if not payload["subprocess_reproducibility"]["identical"]:
                payload["invalidations"]["triggered"].append(
                    {
                        "rule": "subprocess_runs_differ",
                        "detail": "see subprocess_reproducibility",
                    }
                )
                payload["invalidations"]["valid"] = False
                payload["verdict"] = (
                    "SMOKE INVALID"
                    if payload["mode"] == "smoke"
                    else "INVALID"
                )

    output = (
        Path(args.output)
        if args.output
        else (cfg.smoke_output if args.smoke_ms is not None else cfg.output)
    )
    cc.write_outputs(payload, output, overwrite=args.overwrite)
    print(
        f"wrote {output} | verdict={payload['verdict']} | "
        f"conditions={names} | invalidations={len(payload['invalidations']['triggered'])}",
        flush=True,
    )
    return 0 if payload["invalidations"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
