"""Focused tests for the Phase 8 conditions package (work packages G1, G2, G4).

The tests exercise the declared contract of each condition A–F with small
synthetic components:

* the declaration (requirements, refusals, describe records) is checked
  directly;
* A, B and F run one short synthetic episode so the row schema, the fixed
  weight path, the three-factor path and the trainable readout are observed
  rather than asserted from the presence of files;
* E runs on the game's five-tuple API with no neural substrate;
* the substrate-free floor replays constant NO_ACTION.

No BANC-scale graph, no randomisation of the real connectome, no campaign and
no training campaign is started. The 32-node fixture is a test network, not a
biological claim (REV4 §3).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml

from brain.banc_graph import BancConnectome
from brain.banc_sensory_adapter import BancSensoryMapping
from brain.banc_synapse_policy import SignPolicy, WeightPolicy, build_synapse_policy
from brain.neuron_model import LIFParameters
from environment import ControlledGameEnvironment, GameEnvironmentAdapter
from environment.live_loop import (
    PHASE_8_RECORD_FIELDS,
    ClockSync,
    LiveBancStepper,
    LiveSensoryDrive,
)
from experiments.phase_8.conditions import (
    Components,
    ConditionError,
    ConventionalComponents,
    NeuralComponents,
    a_fixed,
    assert_seed_disjoint,
    b_plastic,
    c_random,
    d_plastic,
    describe_condition,
    e_conventional,
    f_readout,
    requirements_for,
    validate_components,
)
from experiments.phase_8.controls import f_init, floor
from experiments.phase_8_random.target_exchange import (
    graph_digest,
    rewire_target_exchange,
)
from motor.action_decoder import GameActionDecoder
from motor.motor_decoder import DecoderConfig
from motor.populations import MotorPopulations
from plasticity.live_stepper import LivePlasticStepper
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.synthetic import synthetic_graph
from plasticity.traces import TraceConfig
from plasticity.weights import WeightState
from readout import (
    BiasOnlyReadout,
    LinearReadout,
    MotorFeatureSpec,
    ReadoutController,
    ReinforceConfig,
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

TRACE_SECTION = {
    "traces": {
        "tau_e_ms": 20.0,
        "dt_ms": 0.5,
        "dtype": "float32",
        "prune_threshold": 1.0e-4,
        "prune_interval_steps": 50,
        "coincidence": "delay_matched",
    }
}

CONFIG_HASHES = {
    "environment": "a" * 64,
    "campaign": "a" * 64,
    "conditions": "a" * 64,
}
INPUT_HASHES = {"graph": "b" * 64}

#: 130 updates (0.18 s of game time) is long enough for the 200 pA sensory
#: drive to drive the LEFT population into spikes, so the A/A′ spike arrays are
#: not vacuous.
UPDATES = 130


# ---------------------------------------------------------------------------
# 32-node synthetic substrate
# ---------------------------------------------------------------------------


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
        unassigned_mask=np.zeros(N_NODES, dtype=bool),
        composition={},
        provenance={},
    )


def decoder_config() -> DecoderConfig:
    payload = yaml.safe_load(DECODER_CONFIG.read_text(encoding="utf-8"))
    return DecoderConfig.from_config(payload["decoder"])


@pytest.fixture(scope="module")
def world() -> SimpleNamespace:
    return build_world(make_graph())


def make_random_world() -> SimpleNamespace:
    """A recurrent 32-node fixture whose edge targets were exchanged.

    B and D need genuinely coincident pre/post activity: in the pure
    feedforward fixture a single delivered packet moves the membrane 9 mV, less
    than the 15 mV threshold gap, so the delay-matched convention never tags.
    The exchanged random graph carries the same contract (structures, weights,
    signs) and does produce coincidences. The quality flag below is a fixture
    assertion, not a U18 randomisation certification.
    """
    exchange = rewire_target_exchange(
        synthetic_graph(N_NODES, 224, seed=5), seed=11, swaps_per_edge=3.0
    )
    if not exchange.complete:
        raise AssertionError("the fixture exchange did not reach its target")
    random_world = build_world(exchange.graph)
    random_world.exchange = exchange
    random_world.structure = {
        "graph_digest": graph_digest(exchange.graph),
        "randomization_quality": {
            "passed": True,
            "failures": [],
            "certification": (
                "synthetic fixture; no U18 randomisation certification was run"
            ),
        },
    }
    return random_world


@pytest.fixture(scope="module")
def random_world() -> SimpleNamespace:
    return make_random_world()


def build_world(graph: BancConnectome) -> SimpleNamespace:
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
    return SimpleNamespace(
        graph=graph,
        nodes=nodes,
        policy=policy,
        populations=populations,
        mapping=mapping,
        encoders=build_encoders(ENCODER_CONFIG),
    )


# ---------------------------------------------------------------------------
# per-episode builders (fresh drive/stepper/adapter every time)
# ---------------------------------------------------------------------------


def make_drive_clock(world: SimpleNamespace):
    drive = LiveSensoryDrive(
        world.mapping, world.encoders, current_pa={"obstacle_present": 200.0}
    )
    clock = ClockSync(neural_dt_ms=0.5, game_dt_s=1.0 / 60.0)
    return drive, clock


def make_fixed_stepper(world, drive, clock, *, seed: int = 11) -> LiveBancStepper:
    return LiveBancStepper(
        world.graph,
        world.policy,
        neuron_params=LIFParameters(),
        dt_ms=clock.neural_dt_ms,
        duration_ms=60_000.0,
        seed=seed,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        input_schedule=drive,
    )


def make_plastic_stepper(world, drive, clock, *, eta: float, seed: int = 11):
    state = WeightState(world.graph, world.policy)
    stepper = LivePlasticStepper(
        world.graph,
        world.policy,
        weight_state=state,
        rule=ThreeFactorRule(RuleConfig(eta=eta), state),
        trace_config=TraceConfig(TRACE_SECTION),
        dt_ms=clock.neural_dt_ms,
        duration_ms=60_000.0,
        seed=seed,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        input_schedule=drive,
    )
    return stepper, state


def make_bundle(
    world,
    *,
    drive,
    clock,
    stepper,
    condition_id: str,
    structure: dict | None = None,
    decision_source=None,
    with_decoder: bool = True,
    max_steps: int = 400,
) -> Components:
    adapter = GameEnvironmentAdapter(
        environment=ControlledGameEnvironment(max_steps=max_steps, render_mode=None)
    )
    decoder = (
        GameActionDecoder(world.populations, decoder_config())
        if with_decoder
        else None
    )
    return Components(
        neural=NeuralComponents(
            adapter=adapter,
            stepper=stepper,
            drive=drive,
            clock=clock,
            action_decoder=decoder,
            decision_source=decision_source,
            window_ms=50.0,
            populations=world.populations,
            structure=structure,
        ),
        metadata={"condition_id": condition_id},
    )


def episode_kwargs(**overrides) -> dict:
    payload = {
        "seed": 101,
        "episode": 0,
        "environment_seed": 3,
        "config_hashes": CONFIG_HASHES,
        "input_hashes": INPUT_HASHES,
        "max_game_updates": UPDATES,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# declarations
# ---------------------------------------------------------------------------


def test_requirements_are_declared_for_every_condition():
    a = requirements_for("A")
    assert a.stepper_kind == "fixed" and a.trains == ("none",)
    b = requirements_for("B")
    assert b.stepper_kind == "plastic" and b.eta == 0.5
    assert b.needs_post_update and b.trains == ("synapses",)
    assert requirements_for("C").requires_structure
    assert requirements_for("D").eta == 0.5
    e = requirements_for("E")
    assert not e.uses_neural_loop and e.trains == ("policy",)
    f = requirements_for("F")
    assert f.needs_decision_source and f.trains == ("readout",)
    assert requirements_for("A_prime").eta == 0.0
    assert requirements_for("F_beta").stepper_kind == "fixed"

    with pytest.raises(ConditionError, match="not an implemented condition"):
        requirements_for("Q")


def test_describe_condition_records_the_limits():
    described = describe_condition("F")
    assert described["declared_spec"]["condition_id"] == "F"
    assert described["state_that_may_change"] == ["readout"]
    assert any(
        "not an identified biological motor command" in line
        for line in described["scientific_limitations"]
    )


def test_condition_rejects_wrong_metadata(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A"
    )
    wrong = replace(components, metadata={"condition_id": "B"})
    with pytest.raises(ConditionError, match="different condition"):
        validate_components("A", wrong, None)


# ---------------------------------------------------------------------------
# A — fixed pathway
# ---------------------------------------------------------------------------


def test_condition_a_refuses_a_plastic_stepper(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A"
    )
    with pytest.raises(ConditionError, match="fixed-weight stepper"):
        a_fixed.validate(components)


def test_condition_a_requires_the_decoder(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="A",
        with_decoder=False,
    )
    with pytest.raises(ConditionError, match="requires action_decoder"):
        a_fixed.validate(components)


def test_condition_a_runs_and_produces_a_schema_row(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A"
    )
    result = a_fixed.run(components, **episode_kwargs())
    row = result["row"]

    assert row["condition"] == "A" and row["role"] == "reference"
    assert row["steps"] == row["observed_updates"] >= 1
    assert row["survival_score"] == float(min(row["steps"], UPDATES))
    assert row["action_counts"] and sum(row["action_counts"].values()) == row["steps"]
    assert row["weights_before"] == row["weights_after"]
    assert result["summary"]["weights_unchanged"] is True
    assert result["summary"]["motor_spikes"] > 0
    assert result["weight_updates"] == []

    evidence = row["evidence"]
    assert evidence["stepper_kind"] == "fixed"
    assert evidence["weights_changed"] is False
    assert evidence["delta_digest"] is None
    assert row["motor_summary"]["decisions"] == row["steps"]

    for record in result["records"]:
        assert set(record) <= set(PHASE_8_RECORD_FIELDS)
        assert record["decoder"] is not None
        assert "readout" not in record
        assert record["motor_activity"]["window_rule"] == "[start, end)"


# ---------------------------------------------------------------------------
# B — three-factor plasticity through the live stepper (G1)
# ---------------------------------------------------------------------------


def test_condition_b_requires_the_hook_and_eta_half(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="B"
    )
    with pytest.raises(ConditionError, match="requires post_update"):
        b_plastic.validate(components)

    b_plastic.install_hook(components)
    assert b_plastic.validate(components).eta == 0.5
    with pytest.raises(ConditionError, match="already has a post-update hook"):
        b_plastic.install_hook(components)

    drive, clock = make_drive_clock(world)
    wrong, _ = make_plastic_stepper(world, drive, clock, eta=0.4)
    wrong_components = make_bundle(
        world, drive=drive, clock=clock, stepper=wrong, condition_id="B"
    )
    b_plastic.install_hook(wrong_components)
    with pytest.raises(ConditionError, match="requires eta = 0.5"):
        b_plastic.validate(wrong_components)


def test_condition_b_runs_learning_updates_through_the_live_stepper(random_world):
    world = random_world
    drive, clock = make_drive_clock(world)
    stepper, state = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="B"
    )
    hook = b_plastic.install_hook(components)
    result = b_plastic.run(components, **episode_kwargs())
    row = result["row"]

    assert row["condition"] == "B" and row["role"] == "condition"
    assert hook.calls == result["summary"]["updates"]
    assert stepper.resets == 1

    pathway = row["evidence"]["plasticity_path"]
    assert pathway["eta"] == 0.5
    assert pathway["mode"] == "rule_executed"
    assert pathway["n_hook_calls"] == result["summary"]["updates"]
    assert pathway["n_update_reports"] >= 1
    assert set(pathway["hook_modes"]) == {"rule_executed"}
    assert result["weight_updates"]
    for update in result["weight_updates"]:
        assert update["eta"] == 0.5
        assert update["mode"] == "rule_executed"
        assert update["applied"] is True

    assert stepper.engine.n_coincident_tags > 0
    assert row["evidence"]["weights_changed"] is True
    assert row["weights_before"] != row["weights_after"]
    assert state.structural_digest() == row["evidence"]["structure_digest"]
    assert not np.array_equal(state.effective_exc, state.initial_exc)

    for record in result["records"]:
        assert record["decoder"] is not None
        assert "readout" not in record
        assert "motor_activity" in record


# ---------------------------------------------------------------------------
# C and D — the per-seed random control graph
# ---------------------------------------------------------------------------


def structure_record(digest: str | None = None, *, passed: bool = True) -> dict:
    return {
        "graph_digest": "c" * 64 if digest is None else digest,
        "randomization_quality": {
            "passed": passed,
            "failures": [] if passed else ["R14"],
        },
    }


def test_random_conditions_require_a_passing_structure_record(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    missing = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="C"
    )
    with pytest.raises(ConditionError, match="structure record"):
        c_random.validate(missing)

    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    short_digest = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="C",
        structure={"graph_digest": "abc", "randomization_quality": {"passed": True}},
    )
    with pytest.raises(ConditionError, match="64-hex graph_digest"):
        c_random.validate(short_digest)

    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    failed = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="C",
        structure=structure_record(passed=False),
    )
    with pytest.raises(ConditionError, match="gates did not pass"):
        c_random.validate(failed)


def test_condition_d_requires_structure_eta_and_hook(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="D"
    )
    d_plastic.install_hook(components)
    with pytest.raises(ConditionError, match="structure record"):
        d_plastic.validate(components)

    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="D",
        structure=structure_record(),
    )
    with pytest.raises(ConditionError, match="requires post_update"):
        d_plastic.validate(components)
    d_plastic.install_hook(components)
    assert d_plastic.validate(components).eta == 0.5


def test_condition_d_runs_learning_on_the_exchanged_graph(random_world):
    world = random_world
    drive, clock = make_drive_clock(world)
    stepper, state = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="D",
        structure=world.structure,
    )
    d_plastic.install_hook(components)
    result = d_plastic.run(components, **episode_kwargs())
    row = result["row"]

    assert row["condition"] == "D" and row["role"] == "condition"
    assert row["evidence"]["structure"]["graph_digest"] == graph_digest(world.graph)
    assert row["evidence"]["structure"]["randomization_passed"] is True
    assert row["evidence"]["plasticity_path"]["mode"] == "rule_executed"
    assert stepper.engine.n_coincident_tags > 0
    assert row["evidence"]["weights_changed"] is True
    assert state.structural_digest() == row["evidence"]["structure_digest"]

    for record in result["records"]:
        assert record["decoder"] is not None
        assert "readout" not in record
        assert "motor_activity" in record


# ---------------------------------------------------------------------------
# F — fixed substrate, trainable readout (G2)
# ---------------------------------------------------------------------------


def test_f_refuses_the_bias_only_readout(world):
    controller = ReadoutController(
        BiasOnlyReadout(MotorFeatureSpec().n_features),
        populations=world.populations,
        training=False,
    )
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="F",
        decision_source=controller,
        with_decoder=False,
    )
    with pytest.raises(ConditionError, match="state-independent"):
        f_readout.validate(components)


def test_f_builder_refuses_a_state_independent_model(world):
    with pytest.raises(ConditionError, match="state-independent readout"):
        f_readout.build_decision_source(
            populations=world.populations,
            training=False,
            model=BiasOnlyReadout(MotorFeatureSpec().n_features),
        )
    with pytest.raises(ConditionError, match="must use the declared MotorFeatureSpec"):
        controller = f_readout.build_decision_source(
            populations=world.populations, training=False
        )
        controller.spec = object()
        f_readout.assert_motor_only_interface(controller)


def test_f_trains_only_the_readout_and_reports_the_motor_block(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    controller = f_readout.build_decision_source(
        populations=world.populations,
        training=True,
        seed=5,
        model=LinearReadout(
            MotorFeatureSpec().n_features, seed=5, init_std=f_readout.DEFAULT_INIT_STD
        ),
        reinforce=ReinforceConfig(learning_rate=0.05),
    )
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="F",
        decision_source=controller,
        with_decoder=False,
    )
    assert f_readout.validate(components).trains == ("readout",)

    result = f_readout.run(components, training=True, **episode_kwargs())
    row = result["row"]
    assert row["condition"] == "F" and row["role"] == "condition"
    assert row["training"] is True
    assert row["weights_before"] == row["weights_after"]
    assert row["evidence"]["weights_changed"] is False
    assert row["evidence"]["stepper_kind"] == "fixed"

    update = row["training_update"]
    assert update is not None
    assert update["n_decisions"] == row["steps"]
    assert update["parameter_digest_before"] != update["parameter_digest_after"]
    assert update["trainable_parameters"] == ["feature_weights", "bias"]

    for record in result["records"]:
        assert record["decoder"] is None
        assert record["readout"]["mode"] == "train"
        assert record["readout"]["state_independent"] is False
        assert "motor_activity" in record
        assert "ablation" in record["readout"]


def test_f_init_refuses_a_training_episode(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = f_init.build_components(
        adapter=GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(max_steps=20, render_mode=None)
        ),
        stepper=stepper,
        drive=drive,
        clock=clock,
        populations=world.populations,
        window_ms=50.0,
        seed=3,
    )
    f_init.validate(components)
    with pytest.raises(ConditionError, match="no training episode"):
        f_init.run(components, training=True, **episode_kwargs(max_game_updates=4))


# ---------------------------------------------------------------------------
# E — conventional REINFORCE on the five-tuple API (G4)
# ---------------------------------------------------------------------------


def test_condition_e_runs_on_the_game_api_and_trains_its_policy():
    environment = ControlledGameEnvironment(max_steps=60, render_mode=None)
    components = e_conventional.build_components(
        environment, condition_id="E", seed=5, training=True
    )
    assert isinstance(components.conventional, ConventionalComponents)
    assert components.neural is None

    result = e_conventional.run(
        components,
        seed=11,
        episode=0,
        environment_seed=22,
        config_hashes=CONFIG_HASHES,
        input_hashes=INPUT_HASHES,
        max_game_updates=6,
        training=True,
    )
    row = result["row"]
    assert row["condition"] == "E" and row["role"] == "condition"
    assert row["training"] is True
    assert row["weights_before"] is None and row["weights_after"] is None
    assert row["action_sha256"] is not None
    assert row["evidence"]["neural_substrate"] == "none"
    assert row["evidence"]["privileged_input"] is False
    assert row["evidence"]["feature_set"] == 7
    assert row["training_update"] is not None
    assert 1 <= row["steps"] <= 6

    described = e_conventional.describe_interface("E")
    assert "no gymnasium" in described["dependencies"]
    assert "no stable-baselines3" in described["dependencies"]
    assert described["additional_capacity"]["heads"] == [
        "policy(4 actions)",
        "value(1)",
    ]


def test_condition_e_full_declares_fourteen_features():
    assert e_conventional.spec_for_condition("E").n_features == 7
    assert e_conventional.spec_for_condition("E_full").n_features == 14
    with pytest.raises(ConditionError, match="not a conventional condition"):
        e_conventional.spec_for_condition("A")


def test_condition_e_refuses_overlapping_seed_sets():
    environment = ControlledGameEnvironment(max_steps=20, render_mode=None)
    components = e_conventional.build_components(environment, seed=5, training=True)
    with pytest.raises(ConditionError, match="overlap"):
        e_conventional.run(
            components,
            seed=11,
            episode=0,
            environment_seed=22,
            config_hashes=CONFIG_HASHES,
            input_hashes=INPUT_HASHES,
            max_game_updates=1,
            training=True,
            training_seeds=[1, 2, 3],
            evaluation_seeds=[3, 4],
        )


# ---------------------------------------------------------------------------
# seed policy
# ---------------------------------------------------------------------------


def test_seed_sets_must_be_non_empty_and_disjoint():
    assert assert_seed_disjoint([1, 2, 3], [4, 5]) == (4, 5)
    with pytest.raises(ConditionError, match="overlap"):
        assert_seed_disjoint([1, 2], [2, 3])
    with pytest.raises(ConditionError, match="non-empty"):
        assert_seed_disjoint([], [1])
    with pytest.raises(ConditionError, match="non-empty"):
        assert_seed_disjoint([1], [])


# ---------------------------------------------------------------------------
# floor — substrate-free NO_ACTION replay
# ---------------------------------------------------------------------------


def test_floor_runs_constant_no_action_without_a_substrate():
    adapter = GameEnvironmentAdapter(
        environment=ControlledGameEnvironment(max_steps=60, render_mode=None)
    )
    result = floor.run(
        adapter,
        seed=5,
        episode=0,
        environment_seed=17,
        config_hashes=CONFIG_HASHES,
        input_hashes=INPUT_HASHES,
        max_game_updates=5,
    )
    row = result["row"]
    assert row["condition"] == "floor" and row["role"] == "floor"
    assert row["evidence"]["neural_substrate"] == "none"
    assert row["evidence"]["is_neural_arm"] is False
    assert row["weights_before"] is None and row["weights_after"] is None
    assert {record["action"] for record in result["records"]} == {floor.NO_ACTION}
    assert result["floor_evidence"]["is_neural_arm"] is False
    assert floor.requirements()["is_neural_arm"] is False


def test_floor_refuses_a_row_that_claims_a_substrate():
    evidence = {"neural_substrate": "banc", "is_neural_arm": True}
    result = {
        "row": {
            "condition": "floor",
            "role": "floor",
            "weights_before": None,
            "weights_after": None,
            "evidence": evidence,
        },
        "records": [{"action": floor.NO_ACTION}],
    }
    with pytest.raises(ConditionError, match="neural substrate"):
        floor.assert_substrate_free(result)


def test_floor_adapter_must_expose_reset_and_step():
    class Incomplete:
        game = object()

    with pytest.raises(ConditionError, match="needs the environment adapter's"):
        floor.validate_adapter(Incomplete())
