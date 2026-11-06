"""Sensory input scheduling, masking, transitions and additivity."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from sensory.game_state import GameState, PlayerState
from sensory.input_scheduler import SensoryInputScheduler
from sensory.population_encoder import build_encoders


class FakePopulation:
    def __init__(self, indices) -> None:
        self._indices = np.asarray(indices, dtype=np.int64)
        self.plan = SimpleNamespace(
            groups=[("default", "pool", self._indices.size)]
        )
        self.root_ids = {"default": self._indices + 1000}

    def size(self) -> int:
        return int(self._indices.size)


class FakeMapping:
    def __init__(self) -> None:
        self.populations = {
            "player_lane": FakePopulation([0, 1, 2, 3, 4, 5]),
            "player_speed": FakePopulation([10, 11, 12]),
            "jumping": FakePopulation([20]),
        }

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


ENCODERS = build_encoders(
    {
        "player_lane": {"kind": "lane", "lanes": 3, "neurons_per_lane": 2},
        "player_speed": {"kind": "gaussian", "n_neurons": 3},
        "jumping": {"kind": "boolean", "n_neurons": 1},
    }
)
CURRENTS = {"player_lane": 200.0, "player_speed": 100.0, "jumping": 50.0}
STATE_A = GameState(
    player=PlayerState(lane="center", speed=0.2), time_ms=0.0
)
STATE_B = GameState(
    player=PlayerState(lane="right", speed=0.8), time_ms=100.0
)


def scheduler(**overrides) -> SensoryInputScheduler:
    options = dict(
        dt_ms=0.5,
        duration_ms=200.0,
        current_pa=CURRENTS,
        transition_ms=20.0,
    )
    options.update(overrides)
    timeline = options.pop("timeline", [(0.0, STATE_A), (100.0, STATE_B)])
    active_features = options.pop("active_features", None)
    return SensoryInputScheduler(
        FakeMapping(),
        ENCODERS,
        timeline,
        active_features=active_features,
        **options,
    )


def test_feature_currents_follow_the_encoded_state() -> None:
    schedule = scheduler()
    currents = schedule.feature_currents_at(0.0)
    assert currents["player_lane"] == pytest.approx(400.0)
    assert currents["player_speed"] == pytest.approx(
        float(ENCODERS["player_speed"].encode(0.2).sum()) * 100.0
    )
    assert currents["jumping"] == 0.0
    first = np.zeros(21)
    schedule.apply(0, 0.0, first)
    later = np.zeros(21)
    schedule.apply(0, 130.0, later)
    assert first[10] > first[12]
    assert later[12] > later[10]
    assert later[4] == pytest.approx(200.0)
    assert later[2] == pytest.approx(0.0)


def test_apply_adds_and_never_overwrites() -> None:
    schedule = scheduler()
    current = np.full(21, 3.0)
    schedule.apply(0, 0.0, current)
    lane_response = ENCODERS["player_lane"].encode(1) * 200.0
    assert np.allclose(current[:6], 3.0 + lane_response)
    speed = ENCODERS["player_speed"].encode(0.2) * 100.0
    assert np.allclose(current[10:13], 3.0 + speed)
    assert current[20] == pytest.approx(3.0)
    assert current[6] == pytest.approx(3.0)


def test_transition_blends_encoded_activations() -> None:
    schedule = scheduler()
    at_change = np.zeros(21)
    schedule.apply(0, 100.0, at_change)
    assert np.allclose(at_change[:6], [0, 0, 200, 200, 0, 0])

    midpoint = np.zeros(21)
    schedule.apply(0, 110.0, midpoint)
    assert np.allclose(midpoint[:6], [0, 0, 100, 100, 100, 100])

    settled = np.zeros(21)
    schedule.apply(0, 130.0, settled)
    assert np.allclose(settled[:6], [0, 0, 0, 0, 200, 200])


def test_onset_and_offset_gate_injection() -> None:
    schedule = scheduler(onset_ms=10.0, offset_ms=50.0)
    before = np.zeros(21)
    schedule.apply(0, 5.0, before)
    assert np.all(before == 0.0)
    during = np.zeros(21)
    schedule.apply(0, 20.0, during)
    assert during.sum() > 0.0
    after = np.zeros(21)
    schedule.apply(0, 50.0, after)
    assert np.all(after == 0.0)


def test_inactive_features_are_masked_out() -> None:
    schedule = scheduler(active_features=["player_lane"])
    assert schedule.stimulated_indices.tolist() == [0, 1, 2, 3, 4, 5]
    currents = schedule.feature_currents_at(0.0)
    assert currents["player_lane"] == pytest.approx(400.0)
    assert currents["player_speed"] == 0.0
    assert currents["jumping"] == 0.0
    current = np.zeros(21)
    schedule.apply(0, 0.0, current)
    assert current[2] == pytest.approx(200.0)
    assert current[20] == pytest.approx(0.0)
    assert current[10] == pytest.approx(0.0)


def test_signature_and_describe_are_deterministic() -> None:
    first, second = scheduler(), scheduler()
    for key in ("indices", "values", "starts"):
        assert np.array_equal(first.signature()[key], second.signature()[key])
    description = first.describe()
    assert description["kind"] == "sensory_population_schedule"
    assert description["n_stimulated_neurons"] == 10
    assert description["active_features"] == [
        "player_lane", "player_speed", "jumping"
    ]
    assert len(description["segments"]) == 2
    assert description["features"]["player_lane"]["root_ids"] == list(
        range(1000, 1006)
    )
    assert first.memory_bytes > 0


def test_timeline_validation() -> None:
    with pytest.raises(ValueError):
        scheduler(timeline=[])
    with pytest.raises(ValueError):
        scheduler(timeline=[(100.0, STATE_B), (50.0, STATE_A)])
    with pytest.raises(ValueError):
        scheduler(timeline=[(200.0, STATE_A)])
    with pytest.raises(ValueError):
        scheduler(timeline=[(0.0, "not a state")])
    with pytest.raises(ValueError):
        scheduler(active_features=["missing"])
    with pytest.raises(ValueError):
        scheduler(active_features=[])
    with pytest.raises(ValueError):
        scheduler(current_pa={"player_lane": -1.0})
    with pytest.raises(ValueError):
        scheduler(dt_ms=0.0)
    with pytest.raises(ValueError):
        scheduler(transition_ms=-1.0)


def test_timeline_accepts_state_timestamps() -> None:
    schedule = scheduler(timeline=[STATE_A, STATE_B])
    assert schedule.starts.tolist() == [0.0, 100.0]
    assert schedule.describe()["segments"][1]["start_ms"] == 100.0
