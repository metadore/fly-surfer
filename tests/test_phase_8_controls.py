"""Focused tests for the Phase 8 controls package (work package G2 controls).

The controls are internal-validity checks, not experimental arms. These tests
prove the declared contracts on small synthetic components:

* A′ reproduces A exactly on all nineteen comparison fields of REV4 §3.8.3,
  and a mismatch stops loudly with the hard-stop payload (§3.8.5);
* C′ reproduces C on the same target-exchange graph and refuses a different
  graph;
* the zero-rate hook refuses a fixed stepper or a nonzero eta;
* Fβ is provably state independent and F-init is the F architecture untrained.

No BANC-scale graph is loaded, the real connectome is never randomized, and no
campaign or training campaign runs. The synthetic graphs are test fixtures, not
biological claims.
"""

from __future__ import annotations

import copy
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
from environment.live_loop import ClockSync, LiveBancStepper, LiveSensoryDrive
from experiments.phase_8.conditions import (
    Components,
    ConditionError,
    NeuralComponents,
    a_fixed,
    c_random,
    f_readout,
    validate_components,
)
from experiments.phase_8.controls import (
    EquivalenceMismatch,
    a_prime,
    c_prime,
    check_control_invariants,
    compare_runs,
    f_beta,
    f_init,
    zero_hook,
)
from experiments.phase_8_random import rewire_target_exchange
from motor.action_decoder import GameActionDecoder
from motor.motor_decoder import DecoderConfig
from motor.populations import MotorPopulations
from plasticity.live_stepper import LivePlasticStepper
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.traces import TraceConfig
from plasticity.synthetic import synthetic_graph
from plasticity.weights import WeightState
from readout import LinearReadout, MotorFeatureSpec
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

#: 130 updates drives the LEFT population into spikes, so the A/A′ spike
#: arrays compared by P1–P3 are not empty.
UPDATES = 130
EPISODE = {"seed": 101, "episode": 0, "environment_seed": 3}


# ---------------------------------------------------------------------------
# synthetic worlds
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


@pytest.fixture(scope="module")
def world() -> SimpleNamespace:
    return build_world(make_graph())


@pytest.fixture(scope="module")
def random_world() -> SimpleNamespace:
    exchange = rewire_target_exchange(
        synthetic_graph(32, 160, seed=5), seed=11, swaps_per_edge=5.0
    )
    world = build_world(exchange.graph)
    world.exchange_summary = exchange.summary()
    return world


# ---------------------------------------------------------------------------
# per-episode builders
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
) -> Components:
    adapter = GameEnvironmentAdapter(
        environment=ControlledGameEnvironment(max_steps=400, render_mode=None)
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


def run_kwargs(**overrides) -> dict:
    payload = {
        "config_hashes": CONFIG_HASHES,
        "input_hashes": INPUT_HASHES,
        "max_game_updates": UPDATES,
    }
    payload.update(overrides)
    return payload


def structure_for(world) -> dict:
    return {
        "graph_digest": world.exchange_summary["graph_digest"],
        "randomization_quality": {"passed": True, "failures": []},
    }


def run_a(world, *, updates: int = UPDATES) -> dict:
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A"
    )
    return a_fixed.run(
        components, **EPISODE, **run_kwargs(max_game_updates=updates)
    )


def run_a_prime(world, *, fixed_result: dict, updates: int = UPDATES) -> dict:
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.0)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A_prime"
    )
    a_prime.install_hook(components)
    return a_prime.run(
        components,
        fixed_result=fixed_result,
        **EPISODE,
        **run_kwargs(max_game_updates=updates),
    )


def run_c(world, *, updates: int = UPDATES) -> dict:
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="C",
        structure=structure_for(world),
    )
    return c_random.run(
        components, **EPISODE, **run_kwargs(max_game_updates=updates)
    )


def c_prime_components(world, *, structure: dict | None = None) -> Components:
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.0)
    components = make_bundle(
        world,
        drive=drive,
        clock=clock,
        stepper=stepper,
        condition_id="C_prime",
        structure=structure or structure_for(world),
    )
    c_prime.install_hook(components)
    return components


def run_c_prime(world, *, fixed_result: dict, updates: int = UPDATES) -> dict:
    return c_prime.run(
        c_prime_components(world),
        fixed_result=fixed_result,
        **EPISODE,
        **run_kwargs(max_game_updates=updates),
    )


# ---------------------------------------------------------------------------
# A′ ≡ A
# ---------------------------------------------------------------------------


def test_a_prime_reproduces_a_exactly(world):
    fixed = run_a(world)
    control = run_a_prime(world, fixed_result=fixed)

    assert len(fixed["stepper"].recorder.spike_times_ms) > 0
    equivalence = control["equivalence"]
    assert equivalence["all_equal"] is True
    assert equivalence["field_count"] == 19
    assert equivalence["fields"] == list(equivalence["fields"])
    assert equivalence["invalidates_on_mismatch"] == ["B"]
    assert equivalence["tolerance"] == "none"

    invariants = control["zero_pathway"]
    assert invariants["eta"] == 0.0
    assert invariants["mode"] == "rule_executed_zero_delta"
    assert invariants["zero_delta"] is True
    assert invariants["n_update_reports"] >= 1

    state = control["stepper"].weight_state
    assert np.array_equal(state.effective_exc, state.initial_exc)
    assert np.array_equal(state.effective_inh, state.initial_inh)
    assert np.array_equal(state.delta_exc, np.zeros_like(state.delta_exc))
    pathway = control["row"]["evidence"]["plasticity_path"]
    assert pathway["mode"] == "rule_executed_zero_delta"
    assert pathway["n_hook_calls"] == control["summary"]["updates"]


def test_a_prime_mismatch_fails_loudly(world):
    fixed = run_a(world)
    control = run_a_prime(world, fixed_result=fixed)

    tampered = copy.deepcopy(fixed)
    tampered["records"][5]["executed_action"] = "TAMPERED"
    with pytest.raises(EquivalenceMismatch) as caught:
        compare_runs(tampered, control, control_id="A_prime")
    payload = caught.value.payload
    assert payload["field_id"] == "P5"
    assert payload["fields_checked_before_stop"] == ["P1", "P2", "P3", "P4"]
    assert payload["tolerance"] == "none (REV4 §3.8.4)"
    assert "hard stop" in payload["required_action"]
    assert payload["control_id"] == "A_prime"
    assert payload["seed"] == control["row"]["seed"]


def test_compare_runs_requires_the_declared_mirror_and_seed(world):
    fixed = run_a(world)
    control = run_a_prime(world, fixed_result=fixed)

    wrong_mirror = copy.deepcopy(fixed)
    wrong_mirror["condition"] = "B"
    with pytest.raises(ValueError, match="declared mirror"):
        compare_runs(wrong_mirror, control, control_id="A_prime")

    wrong_seed = copy.deepcopy(fixed)
    wrong_seed["row"]["seed"] += 1
    with pytest.raises(ValueError, match="not the same seed"):
        compare_runs(wrong_seed, control, control_id="A_prime")


def test_zero_pathway_invariants_refuse_a_nonzero_eta(world):
    fixed = run_a(world, updates=4)
    control = run_a_prime(world, fixed_result=fixed, updates=4)
    tampered = copy.deepcopy(control)
    tampered["summary"]["plasticity"]["eta"] = 0.5
    with pytest.raises(EquivalenceMismatch) as caught:
        check_control_invariants(tampered, control_id="A_prime")
    assert caught.value.payload["field_id"] == "ETA0_VALUE"


# ---------------------------------------------------------------------------
# zero-rate hook guards
# ---------------------------------------------------------------------------


def test_zero_hook_refuses_a_fixed_stepper(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A_prime"
    )
    with pytest.raises(ConditionError, match="plastic stepper"):
        zero_hook.install_hook(components, control_id="A_prime")


def test_zero_hook_refuses_a_nonzero_eta(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.5)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A_prime"
    )
    with pytest.raises(ConditionError, match="eta = 0.0 exactly"):
        zero_hook.install_hook(components, control_id="A_prime")


def test_a_prime_cannot_run_without_the_zero_hook(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.0)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A_prime"
    )
    with pytest.raises(ConditionError, match="requires post_update"):
        a_prime.run(
            components,
            fixed_result={},
            **EPISODE,
            **run_kwargs(max_game_updates=4),
        )


def test_zero_hook_is_installed_once_per_episode(world):
    drive, clock = make_drive_clock(world)
    stepper, _ = make_plastic_stepper(world, drive, clock, eta=0.0)
    components = make_bundle(
        world, drive=drive, clock=clock, stepper=stepper, condition_id="A_prime"
    )
    hook = zero_hook.install_hook(components, control_id="A_prime")
    assert components.neural.post_update is hook
    with pytest.raises(ConditionError, match="already has a post-update hook"):
        zero_hook.install_hook(components, control_id="A_prime")


# ---------------------------------------------------------------------------
# C′ ≡ C on the target-exchange graph
# ---------------------------------------------------------------------------


def test_c_prime_reproduces_c_on_the_same_graph(random_world):
    assert random_world.exchange_summary["complete"] is True
    fixed = run_c(random_world)
    control = run_c_prime(random_world, fixed_result=fixed)

    equivalence = control["equivalence"]
    assert equivalence["all_equal"] is True
    assert equivalence["field_count"] == 19
    assert equivalence["invalidates_on_mismatch"] == ["D"]
    assert control["structure"]["graph_digest"] == random_world.exchange_summary[
        "graph_digest"
    ]
    assert control["row"]["evidence"]["structure"]["randomization_passed"] is True
    assert control["zero_pathway"]["mode"] == "rule_executed_zero_delta"
    assert control["zero_pathway"]["zero_delta"] is True


def test_c_prime_refuses_a_different_graph(random_world):
    fixed = run_c(random_world, updates=4)
    mismatched = copy.deepcopy(fixed)
    mismatched["structure"]["graph_digest"] = "0" * 64
    with pytest.raises(ConditionError, match="different random graphs"):
        c_prime.run(
            c_prime_components(random_world),
            fixed_result=mismatched,
            **EPISODE,
            **run_kwargs(max_game_updates=4),
        )


def test_c_prime_mismatch_is_a_hard_stop(random_world):
    fixed = run_c(random_world, updates=4)
    control = run_c_prime(random_world, fixed_result=fixed, updates=4)

    tampered = copy.deepcopy(fixed)
    tampered["records"][1]["executed_action"] = "TAMPERED"
    with pytest.raises(EquivalenceMismatch) as caught:
        compare_runs(tampered, control, control_id="C_prime")
    payload = caught.value.payload
    assert payload["kind"] == "c_prime_mismatch"
    assert payload["field_id"] == "P5"
    assert payload["fields_checked_before_stop"] == ["P1", "P2", "P3", "P4"]
    assert payload["tolerance"] == "none (REV4 §3.8.4)"
    assert "hard stop" in payload["required_action"]


# ---------------------------------------------------------------------------
# Fβ and F-init declarations
# ---------------------------------------------------------------------------


def test_f_beta_readout_is_provably_state_independent(world):
    model = f_beta.build_readout()
    checks = model.assert_state_independent()
    assert checks["single_trainable_tensor"] is True
    zero = np.zeros((1, MotorFeatureSpec().n_features), dtype=np.float32)
    saturated = np.full((1, MotorFeatureSpec().n_features), 1e6, dtype=np.float32)
    assert np.array_equal(model.logits(zero), model.logits(saturated))

    controller = f_beta.build_decision_source(
        populations=world.populations, training=True, seed=3
    )
    checks = f_beta.assert_state_independent(controller)
    assert checks["feature_weights_exactly_zero"] is True
    assert checks["constant_over_feature_vectors"] is True
    assert controller.trainer.trainable_parameter_names == ["bias"]
    assert controller.state_independent is True


def test_f_beta_refuses_a_state_dependent_readout(world):
    controller = f_readout.build_decision_source(
        populations=world.populations,
        training=False,
        model=LinearReadout(MotorFeatureSpec().n_features, seed=0),
    )
    with pytest.raises(ConditionError, match="BiasOnlyReadout"):
        f_beta.assert_state_independent(controller)


def test_f_beta_and_f_init_are_routed_to_the_right_declarations(world):
    drive, clock = make_drive_clock(world)
    stepper = make_fixed_stepper(world, drive, clock)
    f_components = f_readout.build_components(
        adapter=GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(max_steps=20, render_mode=None)
        ),
        stepper=stepper,
        drive=drive,
        clock=clock,
        populations=world.populations,
        window_ms=50.0,
        training=False,
        seed=1,
    )
    fb_components = f_beta.build_components(
        adapter=GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(max_steps=20, render_mode=None)
        ),
        stepper=stepper,
        drive=drive,
        clock=clock,
        populations=world.populations,
        window_ms=50.0,
        training=False,
        seed=1,
    )
    f_init_components = f_init.build_components(
        adapter=GameEnvironmentAdapter(
            environment=ControlledGameEnvironment(max_steps=20, render_mode=None)
        ),
        stepper=stepper,
        drive=drive,
        clock=clock,
        populations=world.populations,
        window_ms=50.0,
        seed=1,
    )

    validate_components("F", f_components)
    validate_components("F_beta", fb_components)
    validate_components("F_init", f_init_components)

    with pytest.raises(ConditionError, match="state-independent"):
        validate_components("F", fb_components)
    with pytest.raises(ConditionError, match="state-independent"):
        validate_components("F_beta", f_components)
    with pytest.raises(ConditionError, match="not the bias-only control"):
        validate_components("F_init", fb_components)

    source = f_init_components.neural.decision_source
    assert bool(getattr(source, "training", False)) is False
    assert getattr(source, "trainer", None) is None
    assert source.state_independent is False
