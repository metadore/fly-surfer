"""End-to-end sensory-to-neural integration boundaries.

The chain under test is::

    scripted RawDetection -> PerceptionPipeline -> GameState
    -> GameState.features() -> encoders -> SensoryInputScheduler
    -> BrainSimulator -> SpikeRecorder -> summarize_activity

Detections are scripted; no visual recognition is demonstrated here. The
scripted chain exercises the real production configs, the real encoders and
the real simulator. ``experiments/phase_3b/run_pipeline.py`` covers the same
chain with the trained ONNX detector on recorded gameplay frames.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from brain.brain_simulator import BrainSimulator
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_3b import run_pipeline
from perception.config import load_perception_config
from perception.detection import RawDetection
from perception.detector import MockDetector
from perception.image import ImagePreprocessor
from perception.pipeline import PerceptionPipeline
from perception.sensory_bridge import FEATURE_NAMES
from sensory.game_state import GameState, Lane
from sensory.input_scheduler import SensoryInputScheduler
from sensory.population_encoder import build_encoders, encode_state
from sensory.sensory_experiment import load_config

TRAIN_CLASS = 11  # v15 "train", game_state_role train
OBSTACLE_CLASS = 2  # v15 "jump-barrier", game_state_role obstacle_low
N_GRAPH_NODES = 160
SIM_DT_MS = 0.5
SIM_DURATION_MS = 150.0
SIM_SEED = 20261115


class FakePopulation:
    """Minimal population view over a contiguous index range."""

    def __init__(self, indices) -> None:
        self._indices = np.asarray(indices, dtype=np.int64)
        self.plan = SimpleNamespace(
            groups=[("default", "pool", self._indices.size)]
        )
        self.root_ids = {"default": self._indices + 100_000}

    def size(self) -> int:
        return int(self._indices.size)


class FakeMapping:
    """Disjoint per-feature index ranges laid out from the real encoders."""

    def __init__(self, encoders, *, offset: int = 0) -> None:
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
def encoders():
    config = load_config(run_pipeline.SENSORY_CONFIG)
    return build_encoders(copy.deepcopy(config["features"]))


@pytest.fixture(scope="module")
def perception():
    """Run the production pipeline on a synthetic frame and scripted boxes."""
    config = load_perception_config(run_pipeline.PERCEPTION_CONFIG)
    raws = [
        RawDetection(
            class_id=OBSTACLE_CLASS,
            confidence=0.9,
            x1=40,
            y1=350,
            x2=250,
            y2=620,
            class_name="jump-barrier",
        ),
        RawDetection(
            class_id=TRAIN_CLASS,
            confidence=0.9,
            x1=380,
            y1=300,
            x2=600,
            y2=600,
            class_name="train",
        ),
    ]
    pipeline = PerceptionPipeline(config, MockDetector(raws))
    frame = ImagePreprocessor(config.preprocess).from_image(
        Image.new("RGB", (640, 640), (16, 24, 40)),
        frame_id="scripted-gameplay",
        timestamp_ms=0.0,
    )
    return pipeline.run(frame)


@pytest.fixture(scope="module")
def scheduler(encoders, perception):
    setup = SimpleNamespace(
        mapping=FakeMapping(encoders),
        encoders=encoders,
        dt_ms=SIM_DT_MS,
        transition_ms=20.0,
        amplitudes={feature: 200.0 for feature in encoders},
    )
    state = perception.conversion.state
    neutral = GameState.neutral(time_ms=SIM_DURATION_MS)
    schedule = run_pipeline.build_schedule(
        setup,
        [(0.0, state), (SIM_DURATION_MS, neutral)],
        duration_ms=SIM_DURATION_MS + 50.0,
    )
    return schedule


@pytest.fixture
def simulation(scheduler, graph_factory):
    graph = graph_factory(N_GRAPH_NODES, [])
    setup = SimpleNamespace(dt_ms=SIM_DT_MS)
    return run_pipeline.run_simulation(
        graph,
        setup,
        scheduler,
        duration_ms=SIM_DURATION_MS,
        seed=SIM_SEED,
        neuron_params=LIFParameters(),
        synapse_params=SynapseParameters(),
        max_recorded_spikes=50_000,
        progress_interval_ms=50.0,
        diagnostics_interval_steps=100,
    )


def test_detector_output_becomes_game_state(perception):
    conversion = perception.conversion
    state = conversion.state

    assert len(perception.validation.accepted) == 2
    assert not perception.validation.rejected
    assert conversion.player_lane_known is False
    assert conversion.coins_available is False

    assert state.train is not None and state.train.present
    assert state.train.lane == Lane.RIGHT
    assert state.train.distance is not None
    assert 0.0 <= state.train.distance <= 1.0

    assert state.obstacle is not None and state.obstacle.present
    assert state.obstacle.lane == Lane.LEFT
    assert state.obstacle.distance is not None
    assert 0.0 <= state.obstacle.distance <= 1.0

    assert state.coin is None
    assert state.player.jumping is False and state.player.rolling is False


def test_game_state_emits_the_feature_contract(perception):
    state = perception.conversion.state
    features = state.features()

    assert tuple(features) == FEATURE_NAMES
    assert perception.spatial.features == features

    assert features["train_present"] == 1.0
    assert features["train_lane"] == int(Lane.RIGHT)
    assert features["obstacle_present"] == 1.0
    assert features["obstacle_lane"] == int(Lane.LEFT)
    assert features["coin_present"] == 0.0
    assert features["coin_lane"] is None
    assert features["coin_distance"] is None
    assert features["jumping"] == 0.0
    assert features["rolling"] == 0.0
    assert features["player_speed"] == pytest.approx(0.5)


def test_features_encode_into_population_activations(perception, encoders):
    features = perception.conversion.state.features()
    encoded = encode_state(features, encoders)

    assert tuple(encoded) == tuple(encoders)
    for name, encoder in encoders.items():
        values = np.asarray(encoded[name], dtype=np.float64)
        assert values.shape == (encoder.spec.output_size,)
        assert np.all(values >= 0.0)
        assert np.all(values <= encoder.spec.amplitude)

    assert np.all(encoded["train_present"] == 1.0)
    assert np.all(encoded["obstacle_present"] == 1.0)
    assert np.all(encoded["coin_present"] == 0.0)
    assert np.all(encoded["jumping"] == 0.0)
    assert np.all(encoded["coin_lane"] == 0.0)

    per_lane = encoders["train_lane"].spec.neurons_per_lane
    right = encoded["train_lane"][Lane.RIGHT * per_lane : (Lane.RIGHT + 1) * per_lane]
    assert np.all(right == 1.0)
    assert np.count_nonzero(encoded["train_lane"]) == per_lane

    assert np.count_nonzero(encoded["obstacle_distance"]) > 0


def test_encoded_signals_form_a_valid_current_schedule(scheduler, encoders):
    assert scheduler.dt_ms == SIM_DT_MS
    assert scheduler.transition_ms == 20.0
    assert tuple(scheduler.feature_currents_at(0.0)) == tuple(encoders)
    assert scheduler.stimulated_indices.size == 138

    start = scheduler.feature_currents_at(0.0)
    assert start["train_present"] == 6 * 200.0
    assert start["obstacle_present"] == 6 * 200.0
    assert start["coin_present"] == 0.0
    assert start["jumping"] == 0.0

    held = scheduler.feature_currents_at(scheduler.duration_ms - 0.5)
    assert held["train_present"] == 0.0
    assert held["player_lane"] == 4 * 200.0
    for name, value in held.items():
        assert 0.0 <= value <= encoders[name].spec.output_size * 200.0

    midpoint = scheduler.feature_currents_at(SIM_DURATION_MS + 10.0)
    assert midpoint["train_present"] == pytest.approx(3 * 200.0)
    after = scheduler.feature_currents_at(SIM_DURATION_MS + 20.0)
    assert after["train_present"] == 0.0
    assert scheduler.feature_currents_at(scheduler.duration_ms)["player_lane"] == 0.0

    current = np.zeros(N_GRAPH_NODES, dtype=np.float64)
    scheduler.apply(0, 0.0, current)
    assert current[scheduler.stimulated_indices].sum() > 0.0
    unmapped = np.setdiff1d(
        np.arange(N_GRAPH_NODES), scheduler.stimulated_indices
    )
    assert np.all(current[unmapped] == 0.0)


def test_schedule_drives_the_simulator(simulation, scheduler):
    result, wall = simulation
    assert wall >= 0.0
    assert result.duration_ms == pytest.approx(SIM_DURATION_MS)
    assert result.n_steps == int(round(SIM_DURATION_MS / SIM_DT_MS))
    assert result.seed == SIM_SEED

    counts = result.recorder.spike_counts()
    assert counts.shape == (N_GRAPH_NODES,)
    assert counts.sum() > 0
    stimulated = np.asarray(scheduler.stimulated_indices, dtype=np.int64)
    assert counts[stimulated].sum() > 0
    unmapped = np.setdiff1d(np.arange(N_GRAPH_NODES), stimulated)
    # No synapses are present, so neurons outside the schedule cannot spike.
    assert counts[unmapped].sum() == 0


def test_simulator_records_partitioned_activity(simulation, scheduler):
    result, _wall = simulation
    activity = run_pipeline.summarize_activity(
        result, scheduler.stimulated_indices
    )

    assert activity["spikes_total"] > 0
    assert (
        activity["spikes_total"]
        == activity["spikes_stimulated"] + activity["spikes_non_stimulated"]
    )
    assert activity["spikes_stimulated"] > 0
    assert activity["spikes_non_stimulated"] == 0
    assert activity["spiking_neurons_stimulated"] > 0
    assert activity["spiking_neurons_non_stimulated"] == 0
    assert activity["first_spike_ms"] is not None
    assert 0.0 <= activity["first_spike_ms"] < result.duration_ms
    assert activity["first_non_stimulated_spike_ms"] is None
    assert activity["spike_capacity"] == result.recorder.capacity

    recorded = result.recorder.spike_neuron_indices
    assert recorded.size == activity["spikes_total"]
    assert np.all(np.isin(recorded, scheduler.stimulated_indices))
    times = result.recorder.spike_times_ms
    assert np.all(times >= 0.0) and np.all(times < result.duration_ms)

    by_stimulation = activity["activity_by_stimulation"]
    assert by_stimulation["stimulated_spikes"] == activity["spikes_stimulated"]
    assert (
        by_stimulation["non_stimulated_spikes"]
        == activity["spikes_non_stimulated"]
    )
