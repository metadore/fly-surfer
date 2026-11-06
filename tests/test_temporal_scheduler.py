"""Phase 3C temporal scheduler tests.

The scheduler is exercised with synthetic temporal frames and a fake
population mapping. No connectome or real detector output is used.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from perception.config import ClassRole, GameStateRole
from perception.geometry import BoundingBox, NormalizedBox
from perception.observations import FrameObservations, VisualObservation
from perception.temporal import (
    Lifecycle,
    LifecycleEvent,
    TemporalConfig,
    TemporalFeatureConfig,
    TemporalFrame,
    TemporalSequenceProcessor,
)
from perception.tracking import TrackingConfig
from sensory.game_state import (
    GameState,
    Lane,
    ObstacleState,
    ObstacleType,
    PlayerState,
    TrainState,
)
from sensory.input_scheduler import SensoryInputScheduler
from sensory.population_encoder import build_encoders
from sensory.temporal_scheduler import (
    TemporalActivationScheduler,
    TemporalSchedulerConfig,
)

ENCODER_CONFIG = {
    "player_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "player_speed": {"kind": "gaussian", "n_neurons": 3},
    "jumping": {"kind": "boolean", "n_neurons": 1},
    "rolling": {"kind": "boolean", "n_neurons": 1},
    "obstacle_present": {"kind": "boolean", "n_neurons": 1},
    "obstacle_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "obstacle_distance": {"kind": "gaussian", "n_neurons": 4},
    "obstacle_type": {"kind": "boolean", "n_neurons": 1},
    "train_present": {"kind": "boolean", "n_neurons": 1},
    "train_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "train_distance": {"kind": "gaussian", "n_neurons": 4},
    "coin_present": {"kind": "boolean", "n_neurons": 1},
    "coin_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
    "coin_distance": {"kind": "gaussian", "n_neurons": 4},
}
ENCODERS = build_encoders(ENCODER_CONFIG)
CURRENTS = {feature: 200.0 for feature in ENCODERS}


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
    def __init__(self, features=None, *, offset=0) -> None:
        names = list(features or ENCODERS)
        self.populations = {}
        position = offset
        for name in names:
            size = ENCODERS[name].spec.output_size
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


STATE_A = GameState(
    player=PlayerState(lane=Lane.CENTER, speed=0.2),
    train=TrainState(present=True, lane=Lane.CENTER, distance=0.6),
    time_ms=0.0,
)
STATE_B = GameState(
    player=PlayerState(lane=Lane.RIGHT, speed=0.8),
    train=TrainState(present=True, lane=Lane.LEFT, distance=0.3),
    time_ms=100.0,
)
NEUTRAL = GameState.neutral()


def temporal_frame(index, time_ms, state, events=()):
    return TemporalFrame(
        frame_index=index,
        frame_id=f"frame-{index}",
        timestamp_ms=time_ms,
        time_ms=time_ms,
        dt_ms=0.0,
        is_gap=False,
        tracks=(),
        events=tuple(events),
        features=dict(state.features()),
        state=state,
        unrepresented_tracks=0,
    )


def pulse_event(time_ms, feature_values, *, kind=Lifecycle.APPEARED, track_id=1):
    return LifecycleEvent(
        track_id=track_id,
        frame_index=0,
        timestamp_ms=time_ms,
        time_ms=time_ms,
        event=kind,
        class_id=0,
        class_name="train",
        role=ClassRole.TRAIN,
        lane=1,
        confidence=0.9,
        distance_proxy=0.5,
        feature_values=dict(feature_values),
        is_pulse=True,
        detail="synthetic pulse",
    )


def scheduler(frames, *, config=None, active_features=None, mapping=None):
    options = dict(current_pa=CURRENTS)
    if config is not None:
        options["config"] = config
    if active_features is not None:
        options["active_features"] = active_features
    return TemporalActivationScheduler(
        mapping or FakeMapping(), ENCODERS, frames, **options
    )


def test_static_frame_matches_the_phase_3a_scheduler() -> None:
    frames = [temporal_frame(0, 0.0, STATE_A)]
    temporal = scheduler(
        frames, config=TemporalSchedulerConfig(max_hold_ms=1000.0)
    )
    reference = SensoryInputScheduler(
        FakeMapping(),
        ENCODERS,
        [(0.0, STATE_A)],
        dt_ms=0.5,
        duration_ms=500.0,
        current_pa=CURRENTS,
        transition_ms=0.0,
    )
    assert np.array_equal(
        temporal.stimulated_indices, reference.stimulated_indices
    )
    for time_ms in (0.0, 0.5, 10.0, 100.0, 499.5):
        expected = reference.feature_currents_at(time_ms)
        actual = temporal.feature_currents_at(time_ms)
        for feature in ENCODERS:
            assert actual[feature] == pytest.approx(expected[feature]), feature

    zeros = np.zeros(reference.stimulated_indices.max() + 1)
    temporal.apply(0, 10.0, zeros)
    expected = np.zeros_like(zeros)
    reference.apply(0, 10.0, expected)
    assert np.allclose(zeros, expected)


def test_sample_and_hold_follows_absolute_frame_times() -> None:
    frames = [
        temporal_frame(0, 0.0, STATE_A),
        temporal_frame(1, 100.0, STATE_B),
    ]
    schedule = scheduler(
        frames, config=TemporalSchedulerConfig(max_hold_ms=250.0)
    )
    at_a = schedule.feature_currents_at(0.0)
    before_b = schedule.feature_currents_at(99.0)
    at_b = schedule.feature_currents_at(100.0)
    held = schedule.feature_currents_at(200.0)
    stale = schedule.feature_currents_at(400.0)

    def vector(time_ms):
        values = np.zeros(45)
        schedule.apply(0, time_ms, values)
        return values

    train_lane = slice(24, 30)
    assert np.allclose(vector(0.0)[train_lane], vector(99.0)[train_lane])
    assert not np.allclose(vector(100.0)[train_lane], vector(0.0)[train_lane])
    assert np.allclose(vector(200.0)[train_lane], vector(100.0)[train_lane])
    assert at_a["player_lane"] == pytest.approx(before_b["player_lane"])
    assert at_b["train_present"] == pytest.approx(at_a["train_present"])
    assert held["player_lane"] == pytest.approx(at_b["player_lane"])
    assert all(value == 0.0 for value in stale.values())


def test_no_drive_before_the_first_frame() -> None:
    schedule = scheduler(
        [temporal_frame(0, 50.0, STATE_A)],
        config=TemporalSchedulerConfig(max_hold_ms=250.0),
    )
    assert all(value == 0.0 for value in schedule.feature_currents_at(0.0).values())
    assert schedule.feature_currents_at(50.0)["train_present"] == pytest.approx(200.0)


def test_pulse_adds_gain_and_decays_linearly() -> None:
    event = pulse_event(
        0.0,
        {"train_present": 1.0, "train_lane": 1, "train_distance": 0.5},
    )
    schedule = scheduler(
        [temporal_frame(0, 0.0, STATE_A, [event])],
        config=TemporalSchedulerConfig(
            max_hold_ms=1000.0, pulse_gain=1.0, pulse_decay_ms=100.0
        ),
    )
    present_at_onset = schedule.feature_currents_at(0.0)["train_present"]
    present_midway = schedule.feature_currents_at(50.0)["train_present"]
    present_settled = schedule.feature_currents_at(100.0)["train_present"]
    # Base drive from the held state is 200 pA; the full pulse adds 200 pA.
    assert present_at_onset == pytest.approx(400.0)
    assert present_midway == pytest.approx(300.0)
    assert present_settled == pytest.approx(200.0)

    lane_onset = schedule.feature_currents_at(0.0)["train_lane"]
    lane_midway = schedule.feature_currents_at(50.0)["train_lane"]
    assert lane_onset > lane_midway > 0.0


def test_pulses_from_separate_events_add() -> None:
    first = pulse_event(
        0.0, {"player_speed": 0.8}, kind=Lifecycle.APPROACHING, track_id=1
    )
    second = pulse_event(
        20.0, {"player_speed": 0.8}, kind=Lifecycle.RECEDING, track_id=2
    )
    schedule = scheduler(
        [temporal_frame(0, 0.0, NEUTRAL, [first, second])],
        config=TemporalSchedulerConfig(
            max_hold_ms=1000.0, pulse_gain=1.0, pulse_decay_ms=100.0
        ),
    )
    base = scheduler([temporal_frame(0, 0.0, NEUTRAL)])
    base_zero = base.feature_currents_at(0.0)["player_speed"]
    at_zero = schedule.feature_currents_at(0.0)["player_speed"]
    at_twenty = schedule.feature_currents_at(20.0)["player_speed"]
    at_forty = schedule.feature_currents_at(40.0)["player_speed"]
    at_rest = schedule.feature_currents_at(120.0)["player_speed"]
    assert at_zero > base_zero
    assert at_twenty > at_zero
    assert at_forty > base_zero
    assert at_rest == pytest.approx(
        base.feature_currents_at(120.0)["player_speed"]
    )


def test_non_pulse_events_do_not_add_drive() -> None:
    event = LifecycleEvent(
        track_id=1,
        frame_index=0,
        timestamp_ms=0.0,
        time_ms=0.0,
        event=Lifecycle.DISAPPEARED,
        class_id=0,
        class_name="train",
        role=ClassRole.TRAIN,
        lane=1,
        confidence=0.9,
        distance_proxy=0.5,
        feature_values={},
        is_pulse=False,
        detail="synthetic disappearance",
    )
    schedule = scheduler([temporal_frame(0, 0.0, NEUTRAL, [event])])
    base = scheduler([temporal_frame(0, 0.0, NEUTRAL)])
    assert schedule.describe()["n_pulse_events"] == 0
    actual = schedule.feature_currents_at(0.0)
    expected = base.feature_currents_at(0.0)
    for feature in ENCODERS:
        assert actual[feature] == pytest.approx(expected[feature]), feature


def test_apply_adds_and_never_overwrites() -> None:
    schedule = scheduler([temporal_frame(0, 0.0, STATE_A)])
    current = np.full(schedule.stimulated_indices.max() + 3, 3.0)
    schedule.apply(0, 0.0, current)
    train_present = schedule.describe()["features"]["train_present"]
    assert train_present["current_pa"] == 200.0
    assert current.max() > 3.0
    assert current[-1] == pytest.approx(3.0)
    assert current[-2] == pytest.approx(3.0)


def test_inactive_features_mask_state_and_pulses() -> None:
    event = pulse_event(
        0.0, {"train_present": 1.0, "train_lane": 1, "train_distance": 0.5}
    )
    schedule = scheduler(
        [temporal_frame(0, 0.0, STATE_A, [event])],
        active_features=["player_lane"],
    )
    assert schedule.stimulated_indices.tolist() == list(range(6))
    currents = schedule.feature_currents_at(0.0)
    assert currents["player_lane"] > 0.0
    assert currents["train_present"] == 0.0
    assert currents["train_lane"] == 0.0


def test_signature_and_describe_are_deterministic() -> None:
    event = pulse_event(
        0.0, {"train_present": 1.0, "train_lane": 1, "train_distance": 0.5}
    )
    frames = [
        temporal_frame(0, 0.0, STATE_A, [event]),
        temporal_frame(1, 100.0, STATE_B),
    ]
    first, second = scheduler(frames), scheduler(frames)
    for key in (
        "indices",
        "frame_values",
        "frame_times",
        "pulse_values",
        "pulse_onsets",
    ):
        assert np.array_equal(first.signature()[key], second.signature()[key])

    description = first.describe()
    assert description["kind"] == "temporal_sensory_schedule"
    assert description["version"] == "phase_3c_temporal_scheduler_v1"
    assert description["n_frames"] == 2
    assert description["n_pulse_events"] == 1
    assert description["pulse_events_by_kind"] == {"appeared": 1}
    assert description["n_stimulated_neurons"] == 45
    assert description["horizon_ms"] == pytest.approx(350.0)
    assert description["limitations"]
    assert first.memory_bytes > 0
    assert first.horizon_ms == pytest.approx(350.0)


def test_scheduler_consumes_sequence_processor_output() -> None:
    train = (0, "train", ClassRole.TRAIN, GameStateRole.TRAIN)

    def observation(y2):
        return VisualObservation(
            object_index=0,
            class_id=train[0],
            class_name=train[1],
            role=train[2],
            game_state_role=train[3],
            lane=1,
            bbox_screen=BoundingBox(120, 180, 180, y2 * 600),
            bbox_normalized=NormalizedBox(0.4, 0.3, 0.6, y2),
            confidence=0.9,
            frame_id="f",
            timestamp_ms=None,
            distance_proxy=round(1.0 - y2, 6),
        )

    def observations(y2, index):
        return FrameObservations(
            frame_id=f"frame-{index}",
            timestamp_ms=None,
            source_path=None,
            original_size=(300, 600),
            viewport_size=(300, 600),
            observations=(observation(y2),),
        )

    sequence = TemporalSequenceProcessor(
        TemporalConfig(
            tracking=TrackingConfig(min_hits=1, max_age=2),
            features=TemporalFeatureConfig(),
        )
    )
    frames = [
        sequence.process(observations(0.50, 0)),
        sequence.process(observations(0.62, 1)),
        sequence.process(observations(0.74, 2)),
    ]
    assert [item.time_ms for item in frames] == pytest.approx(
        [0.0, 1000.0 / 30.0, 2000.0 / 30.0]
    )
    schedule = scheduler(frames)
    assert schedule.describe()["n_frames"] == 3
    assert schedule.describe()["n_pulse_events"] >= 1
    assert (
        schedule.feature_currents_at(frames[1].time_ms)["train_present"] > 0.0
    )


def test_invalid_configuration_and_frames_are_rejected() -> None:
    with pytest.raises(ValueError, match="frames must be"):
        scheduler([])
    with pytest.raises(ValueError, match="TemporalFrame"):
        scheduler([object()])
    with pytest.raises(ValueError, match="increase strictly"):
        scheduler(
            [temporal_frame(0, 10.0, STATE_A), temporal_frame(1, 10.0, STATE_B)]
        )
    with pytest.raises(ValueError, match="non-negative"):
        scheduler([temporal_frame(0, -1.0, STATE_A)])
    with pytest.raises(ValueError, match="max_hold_ms"):
        TemporalSchedulerConfig(max_hold_ms=0.0)
    with pytest.raises(ValueError, match="pulse_gain"):
        TemporalSchedulerConfig(pulse_gain=1.5)
    with pytest.raises(ValueError, match="pulse_decay_ms"):
        TemporalSchedulerConfig(pulse_decay_ms=0.0)
    with pytest.raises(ValueError, match="version"):
        TemporalSchedulerConfig(version="")
    with pytest.raises(ValueError, match="unknown active features"):
        scheduler([temporal_frame(0, 0.0, STATE_A)], active_features=["missing"])
    with pytest.raises(ValueError, match="at least one feature"):
        scheduler([temporal_frame(0, 0.0, STATE_A)], active_features=[])
    with pytest.raises(ValueError, match="current_pa"):
        TemporalActivationScheduler(
            FakeMapping(),
            ENCODERS,
            [temporal_frame(0, 0.0, STATE_A)],
            current_pa={"player_lane": -1.0},
        )
    with pytest.raises(ValueError, match="mapping is missing"):
        TemporalActivationScheduler(
            FakeMapping(features=["player_lane"]),
            ENCODERS,
            [temporal_frame(0, 0.0, STATE_A)],
            current_pa=CURRENTS,
        )


def test_pulse_validation_rejects_unknown_and_empty_features() -> None:
    unknown = pulse_event(0.0, {"not_a_feature": 1.0})
    with pytest.raises(ValueError, match="unknown features"):
        scheduler([temporal_frame(0, 0.0, STATE_A, [unknown])])

    empty = pulse_event(0.0, {})
    with pytest.raises(ValueError, match="at least one feature value"):
        scheduler([temporal_frame(0, 0.0, STATE_A, [empty])])

    not_an_event = object()
    with pytest.raises(ValueError, match="LifecycleEvent"):
        scheduler([temporal_frame(0, 0.0, STATE_A, [not_an_event])])


def test_feature_currents_support_global_neuron_indices() -> None:
    frames = [temporal_frame(0, 0.0, STATE_A)]
    local = TemporalActivationScheduler(
        FakeMapping(), ENCODERS, frames, current_pa=CURRENTS
    )
    global_map = FakeMapping(offset=500)
    global_schedule = TemporalActivationScheduler(
        global_map, ENCODERS, frames, current_pa=CURRENTS
    )
    assert global_schedule.feature_currents_at(0.0) == pytest.approx(
        local.feature_currents_at(0.0)
    )
    current = np.zeros(600)
    global_schedule.apply(0, 0.0, current)
    assert current[:500].sum() == 0.0
    assert current[500:].sum() > 0.0
