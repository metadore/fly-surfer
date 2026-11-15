"""P3-T7 temporal acceptance: focused regression tests.

These tests cover the pre-registered matrix, sequence construction, the
descriptive statistics used by the runner, and exact equivalence between the
temporal scheduler and the Phase 3A static scheduler for a constant state.
They do not run the full experiment.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
import yaml

from brain.connectome_loader import load_connectome
from experiments.phase_3c import temporal_acceptance as ta
from sensory.input_scheduler import SensoryInputScheduler
from sensory.sensory_experiment import load_config, prepare_setup
from sensory.temporal_scheduler import (
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "temporal_sensory.yaml"


@pytest.fixture(scope="module")
def acceptance_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real_setup():
    graph = load_connectome(
        PROJECT_ROOT / "datasets" / "processed" / "connectome.npz"
    )
    return graph, prepare_setup(
        graph, load_config(PROJECT_ROOT / "configs" / "sensory_config.yaml")
    )


def test_matrix_covers_decision_rule_conditions(acceptance_config):
    conditions = acceptance_config["conditions"]
    for name in ("3C.1", "3C.2", "3C.3", "3C.4", "3C.7", "3C.9"):
        assert name in conditions
    assert set(acceptance_config["not_executed"]) >= {
        "3C.5",
        "3C.6",
        "3C.8",
    }
    assert acceptance_config["protocol"]["current_pa"] == 200.0
    assert acceptance_config["protocol"]["duration_ms"] == 600.5
    assert acceptance_config["conditions"]["3C.7"]["frame_rates_ms"] == [
        200,
        100,
        50,
    ]
    permutation = acceptance_config["conditions"]["3C.9"][
        "shuffle_permutation"
    ]
    assert sorted(permutation) == list(range(13))


def test_frame_times_and_endpoint_identity(acceptance_config):
    times = ta.frame_times(50.0, 600.0)
    assert times.size == 13
    assert times[0] == 0.0 and times[-1] == 600.0
    approach = ta.trajectory_timeline(0.90, 0.15, times)
    retreat = ta.trajectory_timeline(0.15, 0.90, times)
    assert approach[0][1].obstacle.distance == pytest.approx(0.90)
    assert approach[-1][1].obstacle.distance == pytest.approx(0.15)
    assert retreat[0][1].obstacle.distance == pytest.approx(0.15)
    assert retreat[-1][1].obstacle.distance == pytest.approx(0.90)
    assert [item[1].obstacle.distance for item in approach] == pytest.approx(
        [item[1].obstacle.distance for item in reversed(retreat)]
    )


def test_entry_timeline_has_no_object_before_onset(acceptance_config):
    times = ta.frame_times(50.0, 600.0)
    timeline = ta.entry_timeline(0.55, 200.0, times)
    assert timeline[0][1].obstacle is None
    assert timeline[3][1].obstacle is None
    assert timeline[4][1].obstacle.distance == pytest.approx(0.55)
    exit_timeline = ta.exit_timeline(0.55, 200.0, times)
    assert exit_timeline[3][1].obstacle.distance == pytest.approx(0.55)
    assert exit_timeline[4][1].obstacle is None


def test_frames_are_constructed_with_expected_metadata(acceptance_config):
    timeline = ta.constant_timeline(0.55, ta.frame_times(50.0, 600.0))
    frames = ta.make_frames(timeline, 50.0)
    assert len(frames) == 13
    assert frames[0].time_ms == 0.0
    assert frames[-1].time_ms == 600.0
    assert frames[1].dt_ms == pytest.approx(50.0)
    assert frames[3].features["obstacle_present"] == 1.0
    assert frames[3].events == ()


def test_dprime_is_directionless_and_reports_zero_variance():
    shifted = ta.dprime([0, 1, 0, 1], [10, 11, 10, 11])
    assert shifted["dprime"] is not None
    assert abs(shifted["dprime"]) > 1.0
    assert shifted["separated"] is True
    identical = ta.dprime([3, 4, 5], [3, 4, 5])
    assert identical["dprime"] == pytest.approx(0.0)
    assert identical["separated"] is False
    zero_variance = ta.dprime([5, 5, 5], [7, 7, 7])
    assert zero_variance["zero_variance"] is True
    assert zero_variance["separated"] is True


def test_nearest_centroid_loo_separates_two_conditions():
    profiles = {
        "approach": [[5, 0], [5.2, 0], [4.8, 0]],
        "retreat": [[0, 5], [0, 5.1], [0, 4.9]],
    }
    result = ta.nearest_centroid_loo(profiles)
    assert result["accuracy"] == pytest.approx(1.0)
    assert result["n_predictions"] == 6


def test_profile_and_onset_metrics_use_distance_population():
    times = np.array([10.0, 60.0, 110.0, 210.0])
    indices = np.array([0, 1, 1, 0])
    payload = {
        "times_ms": times,
        "neuron_indices": indices,
        "counts": np.array([2, 2, 0]),
    }
    mask = np.array([True, True, False])
    edges = np.arange(0.0, 301.0, 50.0)
    assert ta.profile(payload, mask, edges) == [1, 1, 1, 0, 1, 0]
    metrics = ta.onset_metrics(payload, mask, 100.0, edges)
    assert metrics["first_spike_latency_ms"] == pytest.approx(10.0)
    assert metrics["n_spiking_neurons"] == 2
    assert metrics["post_onset_50ms_count"] == 1


def test_cosine_distance_bounds():
    assert ta.cosine_distance([1, 0], [1, 0]) == pytest.approx(0.0)
    assert ta.cosine_distance([1, 0], [0, 1]) == pytest.approx(1.0)
    assert ta.cosine_distance([0, 0], [1, 0]) is None


def test_temporal_scheduler_matches_static_scheduler(real_setup):
    """3C.1: with a constant state and no events the paths are identical."""
    graph, setup = real_setup
    times = ta.frame_times(50.0, 600.0)
    timeline = ta.constant_timeline(0.55, times)
    frames = ta.make_frames(timeline, 50.0)
    temporal = TemporalActivationScheduler(
        setup.mapping,
        setup.encoders,
        frames,
        current_pa=setup.amplitudes,
        config=TemporalSchedulerConfig(),
    )
    direct = SensoryInputScheduler(
        setup.mapping,
        setup.encoders,
        [(0.0, timeline[0][1])],
        dt_ms=setup.dt_ms,
        duration_ms=600.5,
        current_pa=setup.amplitudes,
        transition_ms=0.0,
    )
    buffer_a = np.zeros(int(graph.n_nodes), dtype=np.float64)
    buffer_b = np.zeros(int(graph.n_nodes), dtype=np.float64)
    n_steps = int(round(600.5 / setup.dt_ms))
    for step in range(n_steps):
        buffer_a.fill(0.0)
        buffer_b.fill(0.0)
        temporal.apply(step, step * setup.dt_ms, buffer_a)
        direct.apply(step, step * setup.dt_ms, buffer_b)
        assert np.array_equal(buffer_a, buffer_b), step
    assert temporal.feature_currents_at(300.0) == pytest.approx(
        direct.feature_currents_at(300.0)
    )


def test_mapping_seed_changes_distance_population(real_setup):
    graph, base = real_setup
    config = copy.deepcopy(base.config)
    config["mapping"]["seed"] = 20261105
    other = prepare_setup(graph, config)
    assert base.mapping.seed == 20261104
    assert other.mapping.seed == 20261105
    assert not np.array_equal(
        base.mapping.indices("obstacle_distance"),
        other.mapping.indices("obstacle_distance"),
    )
