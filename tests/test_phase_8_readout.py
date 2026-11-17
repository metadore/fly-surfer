"""Focused tests for Phase 8 work package G2.

Covers the per-decision motor block, the declared motor feature vector, the
linear and bias-only readouts, the frozen-parameter ablation labels, the
REINFORCE update, and the optional readout decision path of
``NeuralClosedLoop``. The integration case uses a 32-node synthetic network;
no BANC-scale artifact is loaded.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from brain.banc_graph import BancConnectome
from brain.banc_sensory_adapter import BancSensoryMapping
from brain.banc_synapse_policy import SignPolicy, WeightPolicy, build_synapse_policy
from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters
from environment import ControlledGameEnvironment, GameEnvironmentAdapter
from environment.live_loop import (
    PHASE_8_RECORD_FIELDS,
    ClockSync,
    LiveBancStepper,
    LiveSensoryDrive,
    NeuralClosedLoop,
)
from environment.motor_activity import motor_activity_window
from motor.populations import ACTION_POPULATIONS, MotorPopulations
from readout import (
    BiasOnlyReadout,
    LinearReadout,
    MotorFeatureSpec,
    ReadoutController,
    ReinforceConfig,
    ReinforceTrainer,
    ablated_logits,
    argmax_action,
    classify_decision,
)
from readout.ablation import summarise_labels
from readout.features import ACTION_SPACE
from sensory.population_encoder import build_encoders

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


def make_populations(n_neurons: int = 12) -> MotorPopulations:
    masks = {
        "LEFT": np.zeros(n_neurons, dtype=bool),
        "RIGHT": np.zeros(n_neurons, dtype=bool),
        "JUMP": np.zeros(n_neurons, dtype=bool),
    }
    masks["LEFT"][0:2] = True
    masks["RIGHT"][2:4] = True
    masks["JUMP"][4:6] = True
    motor = masks["LEFT"] | masks["RIGHT"] | masks["JUMP"]
    return MotorPopulations(
        n_neurons=n_neurons,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=np.zeros(n_neurons, dtype=bool),
        composition={},
        provenance={},
    )


def block(**kwargs) -> dict:
    values = {
        "LEFT": {"spikes": 1, "active_neurons": 1, "active_fraction": 1.0, "mean_rate_hz": 10.0},
        "RIGHT": {"spikes": 2, "active_neurons": 1, "active_fraction": 0.5, "mean_rate_hz": 20.0},
        "JUMP": {"spikes": 3, "active_neurons": 2, "active_fraction": 0.75, "mean_rate_hz": 30.0},
    }
    values.update(kwargs)
    values["any_motor_spike"] = any(
        values[action]["spikes"] > 0 for action in ACTION_POPULATIONS
    )
    return values


# -- motor activity block ---------------------------------------------------


def test_motor_activity_window_counts_and_half_open_boundary():
    recorder = SpikeRecorder(12, max_spikes=100)
    recorder.record(1, np.array([0]), 0.5)   # t = 1.0
    recorder.record(2, np.array([2, 4]), 0.5)  # t = 1.5
    recorder.record(5, np.array([1]), 0.5)   # t = 3.0
    recorder.record(8, np.array([0]), 0.5)   # t = 4.5 outside

    result = motor_activity_window(
        recorder, make_populations(), 3.5, 2.5, min_spikes=5, min_active_neurons=3
    )
    assert result["window_start_ms"] == pytest.approx(1.0)
    assert result["window_end_ms"] == pytest.approx(3.5)
    assert result["window_rule"] == "[start, end)"
    assert result["source"] == "recorder"
    assert result["total_spikes"] == 4
    assert result["any_motor_spike"] is True
    assert result["populations_with_spikes"] == ["LEFT", "RIGHT", "JUMP"]
    assert result["LEFT"]["spikes"] == 2
    assert result["LEFT"]["active_neurons"] == 2
    assert result["LEFT"]["active_fraction"] == 1.0
    assert result["LEFT"]["mean_rate_hz"] == pytest.approx(400.0)
    assert result["RIGHT"]["spikes"] == 1
    assert result["JUMP"]["spikes"] == 1
    assert result["LEFT"]["sufficient"] is False
    assert "spikes_below_minimum" in result["LEFT"]["reason"]


def test_motor_activity_window_silent_network():
    recorder = SpikeRecorder(12, max_spikes=10)
    result = motor_activity_window(recorder, make_populations(), 10.0, 5.0)
    assert result["total_spikes"] == 0
    assert result["any_motor_spike"] is False
    assert result["populations_with_spikes"] == []
    for action in ACTION_POPULATIONS:
        assert result[action]["spikes"] == 0
        assert result[action]["active_fraction"] == 0.0
        assert result[action]["mean_rate_hz"] == 0.0


def test_motor_activity_rejects_mismatched_neuron_counts():
    recorder = SpikeRecorder(8, max_spikes=10)
    with pytest.raises(ValueError, match="neuron counts differ"):
        motor_activity_window(recorder, make_populations(12), 1.0, 1.0)


# -- feature vector ---------------------------------------------------------


def test_feature_spec_default_and_declared_fields():
    spec = MotorFeatureSpec()
    vector = spec.vector(block())
    assert spec.fields == ("active_fraction",)
    assert spec.names == (
        "LEFT.active_fraction",
        "RIGHT.active_fraction",
        "JUMP.active_fraction",
    )
    assert np.array_equal(vector, np.array([1.0, 0.5, 0.75], dtype=np.float32))

    wide = MotorFeatureSpec(("spikes", "mean_rate_hz"))
    assert wide.n_features == 6
    assert np.array_equal(
        wide.vector(block()),
        np.array([1.0, 10.0, 2.0, 20.0, 3.0, 30.0], dtype=np.float32),
    )


def test_feature_spec_rejects_unknown_or_duplicate_fields():
    with pytest.raises(ValueError, match="unknown motor feature"):
        MotorFeatureSpec(("spikes", "velocity"))
    with pytest.raises(ValueError, match="must not repeat"):
        MotorFeatureSpec(("spikes", "spikes"))


# -- readouts ---------------------------------------------------------------


def test_linear_readout_is_seeded_and_deterministic():
    first = LinearReadout(3, seed=4)
    second = LinearReadout(3, seed=4)
    other = LinearReadout(3, seed=5)
    features = np.array([1.0, 0.5, 0.25], dtype=np.float32)
    assert np.array_equal(first.logits(features), second.logits(features))
    assert not np.array_equal(first.logits(features), other.logits(features))
    assert first.parameter_names() == ["feature_weights", "bias"]


def test_bias_only_readout_ignores_features_and_trains_only_biases():
    model = BiasOnlyReadout(3)
    checks = model.assert_state_independent()
    assert checks["single_trainable_tensor"]
    assert [parameter is model.bias for parameter in model.parameters()] == [True]
    first = model.logits(np.array([1.0, 2.0, 3.0]))
    second = model.logits(np.zeros(3))
    assert np.array_equal(first, second)
    assert np.array_equal(first, np.zeros((1, 4)))
    assert model.state_independent is True


# -- ablation ---------------------------------------------------------------


def set_linear(model: LinearReadout, weights: np.ndarray, bias: np.ndarray) -> None:
    with torch.no_grad():
        model.feature_weights.copy_(torch.as_tensor(weights, dtype=torch.float32))
        model.bias.copy_(torch.as_tensor(bias, dtype=torch.float32))


def test_ablation_labels_cover_the_declared_cases():
    features = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    motor = LinearReadout(3, seed=0)
    set_linear(
        motor,
        np.array([[1.0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]], dtype=np.float32),
        np.array([0.0, 0.5, 0.0, 0.0], dtype=np.float32),
    )
    driven = classify_decision(motor, features, "LEFT", block())
    assert driven["label"] == "motor-driven"
    assert driven["ablation_changed_argmax"] is True
    assert argmax_action(ablated_logits(motor, features)) == "RIGHT"

    biased = LinearReadout(3, seed=0)
    set_linear(
        biased,
        np.array([[1.0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]], dtype=np.float32),
        np.array([5.0, 0.0, 0.0, 0.0], dtype=np.float32),
    )
    driven_label = classify_decision(biased, features, "LEFT", block())
    assert driven_label["label"] == "bias-driven"
    assert driven_label["ablation_changed_argmax"] is False

    neutral_bias = LinearReadout(3, seed=0)
    set_linear(
        neutral_bias,
        np.zeros((4, 3), dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 5.0], dtype=np.float32),
    )
    incidental = classify_decision(
        neutral_bias, np.zeros(3, dtype=np.float32), "NO_ACTION", block()
    )
    assert incidental["label"] == "bias-driven (incidental)"

    silent = {
        action: {"spikes": 0, "active_neurons": 0, "active_fraction": 0.0, "mean_rate_hz": 0.0}
        for action in ACTION_POPULATIONS
    }
    silent["any_motor_spike"] = False
    undefined = classify_decision(
        neutral_bias, np.zeros(3, dtype=np.float32), "NO_ACTION", silent
    )
    assert undefined["label"] == "undefined"
    assert "no motor population spiked" in undefined["label_reason"]


def test_summarise_labels_uses_non_no_action_denominator():
    decisions = [
        {"label": "motor-driven", "chosen_action": "LEFT", "ablation_changed_argmax": True},
        {"label": "bias-driven", "chosen_action": "RIGHT", "ablation_changed_argmax": False},
        {"label": "bias-driven (incidental)", "chosen_action": "NO_ACTION", "ablation_changed_argmax": False},
        {"label": "undefined", "chosen_action": "NO_ACTION", "ablation_changed_argmax": False},
    ]
    summary = summarise_labels(decisions)
    assert summary["counts"]["motor-driven"] == 1
    assert summary["motor_driven_denominator"] == 2
    assert summary["motor_driven_fraction_of_non_no_action"] == 0.5
    assert summary["ablation_change_rate"] == 0.25


# -- trainer ----------------------------------------------------------------


def make_transitions():
    return [
        {"features": np.array([1.0, 0.0, 0.0], dtype=np.float32), "action_index": 0, "reward": 1.0},
        {"features": np.array([0.0, 1.0, 0.0], dtype=np.float32), "action_index": 1, "reward": -1.0},
        {"features": np.array([0.0, 0.0, 1.0], dtype=np.float32), "action_index": 0, "reward": 0.5},
    ]


def test_reinforce_update_changes_only_the_readout_and_is_reproducible():
    digests = []
    for _ in range(2):
        model = LinearReadout(3, seed=9)
        trainer = ReinforceTrainer(model, ReinforceConfig(learning_rate=0.1))
        before = model.logits(np.array([1.0, 0.0, 0.0], dtype=np.float32))
        report = trainer.update(make_transitions())
        after = model.logits(np.array([1.0, 0.0, 0.0], dtype=np.float32))
        assert report["n_decisions"] == 3
        assert report["parameter_digest_before"] != report["parameter_digest_after"]
        assert not np.array_equal(before, after)
        assert report["trainable_parameters"] == ["feature_weights", "bias"]
        digests.append(report["parameter_digest_after"])
    assert digests[0] == digests[1]


def test_reinforce_on_bias_only_keeps_feature_weights_zero():
    model = BiasOnlyReadout(3)
    trainer = ReinforceTrainer(model, ReinforceConfig(learning_rate=0.1))
    report = trainer.update(make_transitions())
    assert report["trainable_parameters"] == ["bias"]
    assert int(torch.count_nonzero(model.fixed_feature_weights).item()) == 0
    assert not torch.equal(model.bias, torch.zeros(4))
    assert model.assert_state_independent()["feature_weights_exactly_zero"]


def test_discounted_returns():
    from readout.trainer import discounted_returns

    returns = discounted_returns([1.0, 0.0, 2.0], 0.5)
    assert np.allclose(returns, [1.5, 1.0, 2.0])


# -- controller -------------------------------------------------------------


def test_controller_records_decisions_and_rewards():
    model = LinearReadout(3, seed=2)
    controller = ReadoutController(
        model,
        populations=make_populations(),
        training=True,
        seed=3,
        trainer=ReinforceTrainer(model, ReinforceConfig(learning_rate=0.1)),
    )
    action, record = controller.decide(block())
    assert action in ACTION_SPACE
    assert record["mode"] == "train"
    assert record["sampled_action"] == action
    assert record["ablation"]["label"] in (
        "motor-driven",
        "bias-driven",
        "bias-driven (incidental)",
        "undefined",
    )
    controller.record_reward(1.0)
    report = controller.update()
    assert report["n_decisions"] == 1


def test_controller_eval_is_argmax_and_does_not_sample():
    model = BiasOnlyReadout(3)
    controller = ReadoutController(
        model, populations=make_populations(), training=False
    )
    first, record = controller.decide(block())
    second, _ = controller.decide(block())
    assert first == second == "LEFT"
    assert record["mode"] == "eval"
    assert record["log_prob"] is None
    assert record["state_independent"] is True
    assert controller.update() is None


def test_controller_rejects_missing_motor_block():
    model = BiasOnlyReadout(3)
    controller = ReadoutController(model, populations=make_populations())
    with pytest.raises(ValueError, match="motor_activity"):
        controller.decide(None)


# -- closed-loop integration ------------------------------------------------


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


def make_loop_with_readout() -> SimpleNamespace:
    graph = make_graph()
    nodes = make_nodes(graph)
    policy = build_synapse_policy(graph, nodes, SignPolicy(), WeightPolicy())
    masks = {
        "LEFT": np.zeros(N_NODES, dtype=bool),
        "RIGHT": np.zeros(N_NODES, dtype=bool),
        "JUMP": np.zeros(N_NODES, dtype=bool),
    }
    masks["LEFT"][LEFT] = True
    masks["RIGHT"][RIGHT] = True
    masks["JUMP"][JUMP] = True
    motor = masks["LEFT"] | masks["RIGHT"] | masks["JUMP"]
    populations = MotorPopulations(
        n_neurons=N_NODES,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=np.zeros(N_NODES, dtype=bool),
        composition={},
        provenance={},
    )
    mapping = BancSensoryMapping(
        nodes,
        graph,
        MAPPING,
        motor_mask=populations.motor_mask,
        action_masks=populations.masks,
    )
    encoders = build_encoders(ENCODER_CONFIG)
    drive = LiveSensoryDrive(mapping, encoders, current_pa={"obstacle_present": 200.0})
    clock = ClockSync(neural_dt_ms=0.5, game_dt_s=1.0 / 60.0)
    stepper = LiveBancStepper(
        graph,
        policy,
        neuron_params=LIFParameters(),
        dt_ms=clock.neural_dt_ms,
        duration_ms=60_000.0,
        seed=11,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        input_schedule=drive,
    )
    controller = ReadoutController(
        BiasOnlyReadout(3), populations=populations, training=False
    )
    loop = NeuralClosedLoop(
        GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(max_steps=20, render_mode=None)
        ),
        stepper,
        drive,
        None,
        clock=clock,
        window_ms=50.0,
        max_updates=4,
        decision_source=controller,
        record_motor_activity=True,
    )
    return SimpleNamespace(loop=loop, controller=controller, populations=populations)


def test_closed_loop_with_readout_records_motor_block_and_readout_fields():
    world = make_loop_with_readout()
    result = world.loop.run(seed=3)
    assert result["records"]
    for record in result["records"]:
        assert set(record) == set(PHASE_8_RECORD_FIELDS)
        assert record["decoder"] is None
        assert record["motor_activity"]["window_rule"] == "[start, end)"
        assert record["readout"]["mode"] == "eval"
        assert record["readout"]["state_independent"] is True
        assert record["executed_action"] == "LEFT"


def test_closed_loop_readout_requires_motor_recording():
    world = make_loop_with_readout()
    with pytest.raises(ValueError, match="record_motor_activity"):
        NeuralClosedLoop(
            world.loop.adapter,
            world.loop.stepper,
            world.loop.drive,
            None,
            clock=world.loop.clock,
            window_ms=50.0,
            max_updates=4,
            decision_source=world.controller,
        )
