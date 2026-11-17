"""Focused tests for the Phase 7 live neural closed loop.

The unit tests use a 32-node synthetic network. The integration tests use the
real ``BancSimulator`` pathway (graph, synapse policy, LIF neuron model, spike
recorder) and the real ``GameActionDecoder`` with the frozen decoder config,
driven by the real controlled game. Nothing here replaces those components.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml

from brain.banc_graph import BancConnectome
from brain.banc_sensory_adapter import BancSensoryMapping
from brain.banc_simulator import BancSimulator
from brain.banc_synapse_policy import SignPolicy, WeightPolicy, build_synapse_policy
from brain.neuron_model import LIFParameters
from environment import ControlledGameEnvironment, GameEnvironmentAdapter
from environment.action_adapter import GameActionAdapter
from environment.live_loop import (
    RECORD_FIELDS,
    ClockSync,
    LiveBancStepper,
    LiveSensoryDrive,
    NeuralClosedLoop,
    decode_trailing_window,
    episode_fingerprint,
)
from environment.reward_function import REWARD_COMPONENTS
from motor.action_decoder import GameActionDecoder
from motor.motor_decoder import DecoderConfig
from motor.populations import MotorPopulations
from sensory.game_state import (
    GameState,
    ObstacleState,
    PlayerState,
)
from sensory.population_encoder import build_encoders

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECODER_CONFIG = PROJECT_ROOT / "configs" / "motor_decoder.yaml"

N_NODES = 32
LEFT = np.arange(0, 12)
RIGHT = np.arange(12, 16)
JUMP = np.arange(16, 20)
SENSORY = np.arange(20, 32)

MAPPING = {
    "seed": 7,
    "allow_duplicates": False,
    "pools": {"sensory": {"super_class": ["visual_projection"]}},
    "populations": {
        "obstacle_present": {
            "pool": "sensory",
            "n_neurons": int(SENSORY.size),
            "evidence": "synthetic test network",
            "hypothesis": "TEST-ONLY",
            "statement": "synthetic network, not a biological claim",
        }
    },
}
ENCODER_CONFIG = {
    "obstacle_present": {
        "kind": "boolean",
        "n_neurons": int(SENSORY.size),
        "amplitude": 1.0,
        "baseline": 0.0,
    }
}


def make_graph() -> BancConnectome:
    edges = [
        (int(source), int(target), 500)
        for source in SENSORY
        for target in LEFT
    ]
    order = sorted(edges)
    edge_src = np.array([edge[0] for edge in order], dtype=np.int32)
    edge_dst = np.array([edge[1] for edge in order], dtype=np.int32)
    edge_weight = np.array([edge[2] for edge in order], dtype=np.int32)
    out_indptr = np.zeros(N_NODES + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=N_NODES), out=out_indptr[1:])
    in_indptr = np.zeros(N_NODES + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=N_NODES), out=in_indptr[1:])
    return BancConnectome(
        root_ids=np.arange(1000, 1000 + N_NODES, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=np.argsort(edge_dst, kind="stable").astype(np.int32),
        threshold=5,
    )


def make_nodes(graph: BancConnectome) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "banc_888_id": [str(value) for value in graph.root_ids],
            "node_index": np.arange(graph.n_nodes),
            "neurotransmitter_verified": ["acetylcholine"] * graph.n_nodes,
            "neurotransmitter_predicted": [None] * graph.n_nodes,
            "super_class": ["visual_projection"] * graph.n_nodes,
            "cell_class": [""] * graph.n_nodes,
            "cell_function": [""] * graph.n_nodes,
            "body_part_sensory": [""] * graph.n_nodes,
            "peripheral_target_type": [""] * graph.n_nodes,
            "region": [""] * graph.n_nodes,
            "flow": [""] * graph.n_nodes,
            "side": [""] * graph.n_nodes,
        }
    )


def make_populations() -> MotorPopulations:
    masks = {name: np.zeros(N_NODES, dtype=bool) for name in ("LEFT", "RIGHT", "JUMP")}
    masks["LEFT"][LEFT] = True
    masks["RIGHT"][RIGHT] = True
    masks["JUMP"][JUMP] = True
    motor = masks["LEFT"] | masks["RIGHT"] | masks["JUMP"]
    return MotorPopulations(
        n_neurons=N_NODES,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=motor & ~(masks["LEFT"] | masks["RIGHT"] | masks["JUMP"]),
        composition={},
        provenance={},
    )


def decoder_config() -> DecoderConfig:
    payload = yaml.safe_load(DECODER_CONFIG.read_text(encoding="utf-8"))
    return DecoderConfig.from_config(payload["decoder"])


@pytest.fixture(scope="module")
def world() -> SimpleNamespace:
    graph = make_graph()
    nodes = make_nodes(graph)
    policy = build_synapse_policy(graph, nodes, SignPolicy(), WeightPolicy())
    populations = make_populations()
    mapping = BancSensoryMapping(
        nodes,
        graph,
        MAPPING,
        motor_mask=populations.motor_mask,
        action_masks=populations.masks,
    )
    encoders = build_encoders(ENCODER_CONFIG)
    return SimpleNamespace(
        graph=graph,
        nodes=nodes,
        policy=policy,
        populations=populations,
        mapping=mapping,
        encoders=encoders,
        current_pa={"obstacle_present": 200.0},
    )


def make_loop(
    world: SimpleNamespace,
    *,
    max_updates: int = 40,
    max_steps: int = 400,
    clock: ClockSync | None = None,
    decoder: GameActionDecoder | None = None,
) -> SimpleNamespace:
    drive = LiveSensoryDrive(
        world.mapping, world.encoders, current_pa=world.current_pa
    )
    clock = clock or ClockSync(neural_dt_ms=0.5, game_dt_s=1.0 / 60.0)
    stepper = LiveBancStepper(
        world.graph,
        world.policy,
        neuron_params=LIFParameters(),
        dt_ms=clock.neural_dt_ms,
        duration_ms=60000.0,
        seed=11,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        input_schedule=drive,
    )
    environment = ControlledGameEnvironment(max_steps=max_steps, render_mode=None)
    adapter = GameEnvironmentAdapter(environment=environment)
    decoder = decoder or GameActionDecoder(world.populations, decoder_config())
    loop = NeuralClosedLoop(
        adapter,
        stepper,
        drive,
        decoder,
        clock=clock,
        max_updates=max_updates,
    )
    return SimpleNamespace(
        drive=drive,
        clock=clock,
        stepper=stepper,
        environment=environment,
        adapter=adapter,
        decoder=decoder,
        loop=loop,
    )


def obstacle_state(time_ms: float = 0.0) -> GameState:
    return GameState(
        player=PlayerState(),
        obstacle=ObstacleState(present=True, lane="center", distance=0.5),
        time_ms=time_ms,
    )


# ---------------------------------------------------------------------------
# initialization and delivery
# ---------------------------------------------------------------------------


def test_stepper_initialises_the_existing_simulator(world):
    loop = make_loop(world)
    assert isinstance(loop.stepper, BancSimulator)
    assert loop.stepper.step_index == 0
    assert loop.stepper.n_neurons == N_NODES
    assert loop.stepper.recorder.n_neurons == N_NODES
    assert loop.stepper.resets == 0
    loop.stepper.reset()
    assert loop.stepper.resets == 1
    assert loop.stepper.input_schedule is loop.drive
    assert loop.stepper.advance_to_step(10) == 10
    assert loop.stepper.time_ms == 5.0
    with pytest.raises(ValueError):
        loop.stepper.advance_to_step(5)
    assert "once per episode" in loop.stepper.describe()["reset_policy"]


def test_sensory_drive_delivers_phase3_current(world):
    loop = make_loop(world)
    loop.drive.set_state(obstacle_state())
    current = np.zeros(N_NODES, dtype=np.float64)
    loop.drive.apply(0, 0.0, current)
    mapped = loop.drive.stimulated_indices
    assert np.allclose(current[mapped], 200.0)
    assert current.size == N_NODES
    assert np.all(current[world.populations.motor_mask] == 0.0)
    assert loop.drive.feature_currents()["obstacle_present"] == pytest.approx(
        SENSORY.size * 200.0
    )

    neutral = np.zeros(N_NODES, dtype=np.float64)
    loop.drive.set_state(obstacle_state())
    loop.drive.reset()
    loop.drive.apply(0, 0.0, neutral)
    assert np.all(neutral == 0.0)


class _FakePopulation:
    def __init__(self, indices):
        self.indices = np.asarray(indices, dtype=np.int64)


class _FakeMapping:
    def __init__(self, populations):
        self.populations = {
            name: _FakePopulation(indices)
            for name, indices in populations.items()
        }

    def size(self, feature):
        return int(self.populations[feature].indices.size)

    def indices(self, feature):
        return self.populations[feature].indices


def test_sensory_drive_rejects_overlapping_or_mismatched_targets():
    encoders = build_encoders(
        {
            "a": {"kind": "boolean", "n_neurons": 2},
            "b": {"kind": "boolean", "n_neurons": 2},
        }
    )
    overlap = _FakeMapping({"a": [0, 1], "b": [1, 2]})
    with pytest.raises(ValueError, match="overlap"):
        LiveSensoryDrive(overlap, encoders)

    mismatched = _FakeMapping({"a": [0, 1], "b": [2]})
    with pytest.raises(ValueError, match="mapping has"):
        LiveSensoryDrive(mismatched, encoders)


def test_clock_synchronises_game_and_neural_time(world):
    clock = ClockSync(neural_dt_ms=0.5, game_dt_s=1.0 / 60.0)
    assert clock.game_dt_ms == pytest.approx(1000.0 / 60.0)
    assert clock.target_step(1.0 / 60.0) == 33
    assert clock.target_step(2.0 / 60.0) == 67
    assert clock.target_step(3.0 / 60.0) == 100
    previous = 0
    for update in range(1, 601):
        target = clock.target_step(update / 60.0)
        assert 33 <= target - previous <= 34
        previous = target
    assert abs(previous - 20000) <= 1
    assert clock.describe()["wall_clock_used"] is False

    loop = make_loop(world)
    run = loop.loop.run(seed=42, max_updates=6)
    steps = [record["neural_steps"] for record in run["records"]]
    assert set(steps) <= {33, 34}
    last = run["records"][-1]
    assert run["summary"]["neural_steps"] == clock.target_step(
        last["update"] / 60.0
    )


# ---------------------------------------------------------------------------
# persistence and integration
# ---------------------------------------------------------------------------


def test_neural_state_persists_between_game_updates(world):
    loop = make_loop(world)
    run = loop.loop.run(seed=42, max_updates=30)
    assert run["summary"]["neural_resets_during_episode"] == 0
    assert loop.stepper.resets == 1
    assert loop.stepper.step_index == run["summary"]["neural_steps"]
    totals = [record["total_spikes"] for record in run["records"]]
    assert totals == sorted(totals)
    assert run["summary"]["mean_steps_per_update"] == pytest.approx(
        run["summary"]["neural_steps"] / 30, rel=1e-6
    )
    assert run["summary"]["neural_time_ms"] == pytest.approx(
        run["summary"]["neural_steps"] * 0.5
    )


def test_real_game_observation_drives_a_supported_action(world):
    """End-to-end: observation -> encoding -> BANC sim -> decoder -> game.

    The game only presents an obstacle after some updates, so the first part of
    the episode is deliberately silent. The test asserts the full pipeline once
    the observation carries an obstacle.
    """
    loop = make_loop(world, max_updates=130)
    run = loop.loop.run(seed=42, max_updates=130)
    records = run["records"]

    driven = [record for record in records if record["total_sensory_current_pa"] > 0]
    assert driven, "the game did not produce a mapped sensory feature"
    after = [record for record in records if record["update"] >= driven[0]["update"]]
    decoded = [record for record in after if record["decoder"]["state"] == "LEFT"]
    assert decoded, "neural activity never reached the LEFT decoder threshold"
    executed = [record for record in records if record["executed_action"] == "LEFT"]
    assert executed, "the decoded LEFT state never reached the game"
    assert run["summary"]["motor_population_spikes"]["LEFT"] > 0
    assert run["summary"]["neural_resets_during_episode"] == 0
    assert run["summary"]["weights_unchanged"] is True
    assert loop.environment.n_steps == len(records)


def test_neural_activity_reaches_the_real_decoder(world):
    loop = make_loop(world)
    loop.adapter.reset(seed=42)
    loop.stepper.reset()
    loop.drive.reset()
    loop.drive.set_state(obstacle_state())
    loop.stepper.advance_to_step(200)  # 100 ms of the live network
    assert loop.stepper.recorder.n_spikes > 0
    output = decode_trailing_window(
        loop.decoder, loop.stepper.recorder, 100.0, 50.0
    )
    assert output is not None
    assert output.state == "LEFT"
    assert output.supported
    assert "LEFT" in output.active_channels
    evidence = output.evidence["LEFT"]
    assert evidence["sufficient"]
    assert evidence["spikes"] >= 5
    assert evidence["active_neurons"] >= 3
    assert output.raw_activation_scores["LEFT"] >= 0.20


def test_decoder_output_reaches_the_environment(world):
    loop = make_loop(world)
    loop.adapter.reset(seed=42)
    loop.stepper.reset()
    loop.drive.reset()
    loop.drive.set_state(obstacle_state())
    loop.stepper.advance_to_step(200)
    output = decode_trailing_window(
        loop.decoder, loop.stepper.recorder, 100.0, 50.0
    )
    record = loop.adapter.step(output)
    assert record.mapping.requested_state == "LEFT"
    assert record.mapping.executed_action == "LEFT"
    assert record.mapping.supported and not record.mapping.unmapped
    assert record.observation["environment"]["step"] == 1
    assert int(record.game_state.player.lane) == 0
    assert record.terminated is False


# ---------------------------------------------------------------------------
# safe action handling
# ---------------------------------------------------------------------------


def test_unmapped_and_invalid_outputs_execute_no_action(world):
    adapter = GameActionAdapter()
    for value in ("UNMAPPED", "DUCK", "NOT_A_STATE", None, {"state": 5}, 17):
        mapping = adapter.map(value)
        assert mapping.executed_action == "NO_ACTION"
        assert mapping.supported is False
        assert mapping.reason

    loop = make_loop(world)
    no_spikes = np.array([])
    unmapped = loop.decoder.decode_requested(
        "ROLL", no_spikes, no_spikes.astype(int), 0.0, 50.0
    )
    assert unmapped.state == "UNMAPPED"
    assert unmapped.supported is False
    loop.adapter.reset(seed=42)
    record = loop.adapter.step(unmapped)
    assert record.mapping.executed_action == "NO_ACTION"
    assert record.mapping.unmapped is True
    assert "UNMAPPED" in record.mapping.reason
    assert record.reward >= 0.0


# ---------------------------------------------------------------------------
# rewards, fixed weights, determinism, termination, recording
# ---------------------------------------------------------------------------


def test_reward_provenance_is_preserved(world):
    loop = make_loop(world)
    run = loop.loop.run(seed=42, max_updates=5)
    assert run["records"]
    for record in run["records"]:
        assert set(record["reward_components"]) == set(REWARD_COMPONENTS)
        assert abs(
            sum(record["reward_components"].values()) - record["reward_total"]
        ) < 1e-9
        assert record["reward_provenance"]
        assert "not recomputed" in record["reward_provenance"]
        assert isinstance(record["reward_event_types"], list)
    reward = loop.environment.reward_function
    assert reward.stream.provenance == reward.provenance
    assert reward.n_steps == len(run["records"])
    if any(record["reward_total"] for record in run["records"]):
        assert len(reward.deliveries) > 0
        assert len(reward.schedule().events) == len(reward.events)


def test_synaptic_weights_are_unchanged(world):
    loop = make_loop(world)
    before_exc = loop.stepper.synapses.edge_exc_weight.copy()
    before_inh = loop.stepper.synapses.edge_inh_weight.copy()
    before = loop.stepper.weight_fingerprint()
    run = loop.loop.run(seed=42, max_updates=60)
    assert np.array_equal(loop.stepper.synapses.edge_exc_weight, before_exc)
    assert np.array_equal(loop.stepper.synapses.edge_inh_weight, before_inh)
    assert loop.stepper.weight_fingerprint() == before
    assert run["summary"]["weights_unchanged"] is True
    assert run["summary"]["weights_before"] == run["summary"]["weights_after"]


def test_episode_is_deterministic(world):
    loop = make_loop(world, max_updates=40)
    first = loop.loop.run(seed=42, max_updates=40)
    first_spikes = (
        loop.stepper.recorder.spike_times_ms.copy(),
        loop.stepper.recorder.spike_neuron_indices.copy(),
    )
    second = loop.loop.run(seed=42, max_updates=40)
    assert first["fingerprint"] == second["fingerprint"]
    assert np.array_equal(first_spikes[0], loop.stepper.recorder.spike_times_ms)
    assert np.array_equal(first_spikes[1], loop.stepper.recorder.spike_neuron_indices)
    for key in (
        "updates",
        "neural_steps",
        "total_spikes",
        "action_counts",
        "total_reward",
        "termination_reason",
    ):
        assert first["summary"][key] == second["summary"][key]


def test_episode_terminates_or_truncates(world):
    loop = make_loop(world, max_updates=400, max_steps=50)
    run = loop.loop.run(seed=42, max_updates=400)
    summary = run["summary"]
    assert summary["truncated"] is True
    assert summary["updates"] == 50
    assert len(run["records"]) == 50
    assert loop.environment.n_steps == 50

    short = make_loop(world, max_updates=5)
    limited = short.loop.run(seed=42, max_updates=5)
    assert limited["summary"]["updates"] == 5
    assert limited["summary"]["terminated"] is False
    assert limited["summary"]["truncated"] is False


def test_recording_is_complete(world):
    loop = make_loop(world)
    run = loop.loop.run(seed=42, max_updates=5)
    assert run["seed"] == 42
    for record in run["records"]:
        assert set(record) == set(RECORD_FIELDS)
        json.dumps(record)
    summary = run["summary"]
    for key in (
        "seed",
        "updates",
        "neural_steps",
        "neural_time_ms",
        "total_spikes",
        "motor_spikes",
        "motor_population_spikes",
        "action_counts",
        "decoder_state_counts",
        "unmapped_or_invalid",
        "total_reward",
        "reward_component_totals",
        "reward_event_counts",
        "coins_collected",
        "collisions",
        "termination_reason",
        "weights_unchanged",
        "neural_resets_during_episode",
        "limitations",
    ):
        assert key in summary
    fingerprint = episode_fingerprint(run["records"], loop.stepper.recorder)
    assert set(fingerprint) == {"spike_sha256", "action_reward_sha256"}
    assert all(len(value) == 64 for value in fingerprint.values())


def test_loop_rejects_inconsistent_configuration(world):
    loop = make_loop(world)
    wrong_clock = ClockSync(neural_dt_ms=1.0, game_dt_s=1.0 / 60.0)
    with pytest.raises(ValueError, match="clock"):
        NeuralClosedLoop(
            loop.adapter,
            loop.stepper,
            loop.drive,
            loop.decoder,
            clock=wrong_clock,
        )
    other = GameActionDecoder(make_other_populations(), decoder_config())
    with pytest.raises(ValueError, match="decoder"):
        NeuralClosedLoop(
            loop.adapter,
            loop.stepper,
            loop.drive,
            other,
            clock=loop.clock,
        )


def make_other_populations() -> MotorPopulations:
    masks = {name: np.zeros(N_NODES + 1, dtype=bool) for name in ("LEFT", "RIGHT", "JUMP")}
    masks["LEFT"][0] = True
    masks["RIGHT"][1] = True
    masks["JUMP"][2] = True
    motor = np.zeros(N_NODES + 1, dtype=bool)
    motor[:3] = True
    return MotorPopulations(
        n_neurons=N_NODES + 1,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=np.zeros(N_NODES + 1, dtype=bool),
        composition={},
        provenance={},
    )
