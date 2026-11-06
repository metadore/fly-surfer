"""Phase 3B + 3C integration tests.

The chain under test is::

    scripted RawDetection -> PerceptionPipeline -> tracking/temporal features
    -> TemporalActivationScheduler

The connectome simulation is not run here; ``experiments/phase_3c/
integration_check.py`` covers that end to end against the real artifact. These
tests pin the plumbing, determinism and protected-artifact hashes.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.phase_3c import integration_check as integration
from sensory.population_encoder import build_encoders
from sensory.temporal_scheduler import (
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)


class FakePopulation:
    def __init__(self, indices) -> None:
        self._indices = np.asarray(indices, dtype=np.int64)
        self.plan = SimpleNamespace(
            groups=[("default", "pool", self._indices.size)]
        )
        self.root_ids = {"default": self._indices + 10_000}

    def size(self) -> int:
        return int(self._indices.size)


class FakeMapping:
    """Disjoint per-feature index ranges laid out from the real encoders."""

    def __init__(self, encoders, *, offset=0) -> None:
        self.populations = {}
        position = offset
        for name, encoder in encoders.items():
            size = encoder.spec.output_size
            self.populations[name] = FakePopulation(
                range(position, position + size)
            )
            position += size

    def indices(self, feature):
        return self.populations[feature]._indices

    def size(self, feature):
        return self.populations[feature].size()

    def stimulated_indices(self):
        return np.unique(
            np.concatenate(
                [population._indices for population in self.populations.values()]
            )
        )


@pytest.fixture(scope="module")
def sensory_config():
    return integration._load_yaml(integration.SENSORY_CONFIG)


@pytest.fixture(scope="module")
def encoders(sensory_config):
    return build_encoders(copy.deepcopy(sensory_config["features"]))


@pytest.fixture(scope="module")
def chain():
    pipeline = integration._build_pipeline()
    observations, audit = integration._process_frames(
        pipeline, integration.scripted_frames()
    )
    temporal = integration._temporal_run(observations)
    return observations, audit, temporal


@pytest.fixture(scope="module")
def scheduler(chain, encoders):
    _observations, _audit, temporal = chain
    return TemporalActivationScheduler(
        FakeMapping(encoders),
        encoders,
        temporal,
        current_pa={feature: 200.0 for feature in encoders},
        config=TemporalSchedulerConfig(),
    )


def _event_tuples(temporal):
    return [
        (event.event.value, event.class_name, event.lane, event.frame_index)
        for frame in temporal
        for event in frame.events
    ]


def test_scripted_chain_processes_every_frame(chain):
    _observations, audit, temporal = chain
    assert [item["frame_index"] for item in audit] == list(
        range(integration.N_FRAMES)
    )
    assert all(item["rejected"] == 0 for item in audit)
    assert all(item["accepted"] > 0 for item in audit)
    assert all(len(item["features"]) == 14 for item in audit)
    assert len(temporal) == integration.N_FRAMES


def test_tracking_and_lifecycle_events(chain):
    _observations, _audit, temporal = chain
    events = _event_tuples(temporal)
    assert ("appeared", "train", 1, 1) in events
    assert any(
        kind == "approaching" and name == "train" for kind, name, _, _ in events
    )
    assert ("occluded", "train", 1, integration.OCCLUDED_FRAME) in events
    # The one-frame right-lane flicker must never be confirmed.
    assert not any(
        kind == "appeared" and lane == 2 and frame == 3
        for kind, _name, lane, frame in events
    )
    track_ids = {
        track.track_id for frame in temporal for track in frame.tracks
    }
    assert len(track_ids) >= 2
    assert len(temporal[-1].state.features()) == 14
    assert any(frame.unrepresented_tracks > 0 for frame in temporal)


def test_scheduler_consumes_temporal_frames(scheduler, chain):
    _observations, _audit, temporal = chain
    statistics = scheduler.input_statistics()
    assert statistics["n_frames"] == integration.N_FRAMES
    assert statistics["n_active_features"] == 14
    assert statistics["n_pulse_events"] > 0
    assert statistics["max_per_neuron_current_pa"] <= 200.0
    assert scheduler.horizon_ms == pytest.approx(
        temporal[-1].time_ms + scheduler.config.max_hold_ms
    )
    assert scheduler.memory_bytes > 0

    n_neurons = int(scheduler.stimulated_indices.max()) + 1
    current = np.zeros(n_neurons, dtype=np.float64)
    scheduler.apply(0, float(temporal[0].time_ms), current)
    assert current[scheduler.stimulated_indices].sum() > 0.0
    unmapped = np.setdiff1d(np.arange(n_neurons), scheduler.stimulated_indices)
    assert np.all(current[unmapped] == 0.0)

    currents = scheduler.feature_currents_at(float(temporal[-1].time_ms))
    assert currents["train_present"] > 0.0
    assert currents["obstacle_present"] > 0.0
    assert currents["coin_present"] == 0.0


def test_scheduler_is_deterministic(chain, encoders):
    _observations, _audit, temporal = chain
    config = TemporalSchedulerConfig()
    currents = {feature: 200.0 for feature in encoders}
    first = TemporalActivationScheduler(
        FakeMapping(encoders), encoders, temporal,
        current_pa=currents, config=config,
    )
    second = TemporalActivationScheduler(
        FakeMapping(encoders), encoders, temporal,
        current_pa=currents, config=config,
    )
    assert integration._signature_digest(first) == integration._signature_digest(
        second
    )
    size = int(first.stimulated_indices.max()) + 1
    a = np.zeros(size, dtype=np.float64)
    b = np.zeros(size, dtype=np.float64)
    for step in range(8):
        time_ms = step * integration.FRAME_INTERVAL_MS
        first.apply(step, time_ms, a)
        second.apply(step, time_ms, b)
    assert np.array_equal(a, b)


def test_protected_artifacts_unchanged():
    mismatches = {}
    for name, (path, expected) in integration.PROTECTED.items():
        actual = integration._sha256(path)
        if actual != expected:
            mismatches[name] = {"path": str(path), "actual": actual}
    assert not mismatches, mismatches
