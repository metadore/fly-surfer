"""Focused synthetic tests for the Phase 8 G5 campaign runner assembly.

Every test here uses synthetic stubs: a stub component factory, stub arm
runners, a 2-node alignment fixture and a temporary certified-graph namespace.
No BANC-scale graph is loaded, no game episode is executed, no training run is
started and no campaign data is produced. These are infrastructure tests; they
are not experimental evidence (G5 brief §6-§7).

Covered areas: campaign/REV4 validation, the twelve declared arms, control
semantics, the episode-runner interface, factory construction and refusals,
certified-graph enforcement, seed pairing, row serialization, failure and
interruption handling, resume, run status, and the refusal to start.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.phase_8 import run_campaign as cli
from experiments.phase_8.campaign import (
    CampaignDispatcher,
    CampaignFactory,
    CampaignNotAuthorized,
    CampaignProtocolError,
    CertifiedGraph,
    CertifiedGraphSource,
    EpisodeFailure,
    FactoryError,
    GraphSelectionError,
    TrainingArtifacts,
    approval_status,
    assert_campaign_authorized,
    assert_target_exchange_alignment,
    protocol_identity,
    run_status,
    validate_campaign,
)
from experiments.phase_8.campaign import graphs as campaign_graphs
from experiments.phase_8.campaign.dispatcher import (
    ARM_ORDER,
    ARM_RUNNERS,
    CONTROL_MIRRORS,
    DispatcherError,
)
from experiments.phase_8.campaign.factory import STRUCTURE_ARMS, FactorySettings
from experiments.phase_8.conditions import requirements_for
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.controls.equivalence import EquivalenceMismatch
from experiments.phase_8.registry import build_registry, default_registry, evaluation_plan
from experiments.phase_8.runner import CampaignRunner
from experiments.phase_8.seeds import environment_seed, seed_plan
from experiments.phase_8.store import EpisodeStore
from experiments.phase_8_random import certification as cert
from readout.features import MotorFeatureSpec

MASTER = 20261116
SHA = "a" * 64
OTHER = "b" * 64

ROLES = {
    "A": "reference",
    "B": "condition",
    "C": "condition",
    "D": "condition",
    "E": "condition",
    "F": "condition",
    "A_prime": "control",
    "C_prime": "control",
    "F_beta": "control",
    "F_init": "control",
    "E_full": "exploratory",
    "floor": "floor",
}
WEIGHTLESS = {"E", "E_full", "floor"}


@pytest.fixture(scope="module")
def config():
    return load_phase8_config()


def context_for(seed=1, episode=0, arm="A"):
    plan = None if arm == "floor" else seed_plan(MASTER, arm, seed)
    return {
        "master_seed": MASTER,
        "environment_seed": environment_seed(MASTER, seed, episode),
        "seed_plan": plan,
        "config_hashes": {
            "environment": SHA,
            "campaign": SHA,
            "conditions": SHA,
        },
        "max_game_updates": 900,
        "episodes_per_seed": 10,
    }


def row_for(arm, seed, episode, environment_seed_value, config_hashes):
    digest = None if arm in WEIGHTLESS else SHA
    return {
        "schema_version": 1,
        "condition": arm,
        "role": ROLES[arm],
        "seed": int(seed),
        "episode": int(episode),
        "environment_seed": int(environment_seed_value),
        "training": False,
        "steps": 1,
        "observed_updates": 1,
        "survival_score": 1.0,
        "max_game_updates": 900,
        "total_reward": 0.01,
        "terminated": False,
        "truncated": True,
        "termination_reason": "max_game_updates",
        "action_counts": {"NO_ACTION": 1},
        "no_action_fraction": 1.0,
        "motor_spikes": 0,
        "spike_sha256": None,
        "action_sha256": SHA,
        "weights_before": digest,
        "weights_after": digest,
        "config_hashes": dict(config_hashes),
        "input_hashes": {"fixture": SHA},
        "started_at": "2026-11-17T00:00:00Z",
        "wall_time_s": 0.01,
    }


class StubFactory:
    """Records which component bundle the dispatcher asked for."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, dict]] = []

    def neural_components(self, arm, **kwargs):
        self.calls.append(("neural", arm, dict(kwargs)))
        return SimpleNamespace(kind="neural", arm=arm)

    def conventional_components(self, arm, *, seed):
        self.calls.append(("conventional", arm, {"seed": int(seed)}))
        return SimpleNamespace(kind="conventional", arm=arm)

    def floor_adapter(self):
        self.calls.append(("floor_adapter", None, {}))
        return SimpleNamespace(kind="floor")

    def input_hashes(self):
        return {"fixture": SHA}


def stub_runners(log=None):
    def make(arm):
        def run(components, **kwargs):
            if log is not None:
                log.append((arm, components, dict(kwargs)))
            result = {
                "row": row_for(
                    arm,
                    kwargs["seed"],
                    kwargs["episode"],
                    kwargs["environment_seed"],
                    kwargs["config_hashes"],
                )
            }
            if arm in CONTROL_MIRRORS:
                result["equivalence"] = {
                    "control_id": arm,
                    "all_equal": True,
                    "tolerance": "none",
                }
                result["zero_pathway"] = {"eta": 0.0, "zero_delta": True}
            return result

        return run

    return {arm: make(arm) for arm in ARM_ORDER}


def selected_config(config, *, seeds=1, episodes=1):
    return replace(
        config,
        campaign=replace(
            config.campaign,
            n_seeds_selected=seeds,
            episodes_per_seed=episodes,
        ),
    )


def passing_gate(gate_gb):
    return {"available_gb": 99.0, "gate_gb": gate_gb, "passed": True, "reason": "test"}


_FAKE_CAPTURE = {
    "python": "3.13",
    "platform": "test",
    "cpu_count": 1,
    "libraries": {},
}
_MANIFEST_INPUTS = {"fixture": {"path": "x", "sha256": SHA}}
_MANIFEST_INTEGRITY = {
    "checked": False,
    "baseline": None,
    "non_readme_failures": [],
}


def start_harness(config, tmp_path, dispatcher, run_id="run-1", **kwargs):
    return CampaignRunner.start(
        config,
        tmp_path,
        run_id,
        episode_runner=dispatcher,
        preflight=passing_gate,
        input_hashes=_MANIFEST_INPUTS,
        capture=_FAKE_CAPTURE,
        integrity=_MANIFEST_INTEGRITY,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# campaign configuration against REV4
# ---------------------------------------------------------------------------


def test_validate_campaign_reports_conformance_and_open_deviation(config):
    report = validate_campaign(config, strict=False)
    assert report["conforms"] is True
    assert report["checks_total"] == report["checks_passed"]
    assert report["design_resolved"] is False
    assert report["n_seeds_selected"] is None
    assert report["approval"]["approved"] is True
    assert (
        report["approval"]["decision_status"]
        == "APPROVED - recorded owner decision D1"
    )
    assert report["approval"]["approval_record"]["approval_id"] == "D1"
    deviation = report["randomization_deviation"]
    assert deviation["status"] == "deviation_recorded"
    assert deviation["gate_weakened"] is False


def test_validate_campaign_rejects_constant_drift(config):
    drifted = replace(
        config, campaign=replace(config.campaign, alpha=0.01)
    )
    with pytest.raises(CampaignProtocolError, match="campaign.alpha"):
        validate_campaign(drifted, strict=True)
    report = validate_campaign(drifted, strict=False)
    assert report["conforms"] is False
    names = {entry["name"] for entry in report["failures"]}
    assert "campaign.alpha" in names
    assert all(entry["pass"] is False for entry in report["failures"])


def test_protocol_identity_matches_the_frozen_document():
    identity = protocol_identity()
    assert identity["present"] is True
    assert identity["matches_expected"] is True
    assert len(identity["sha256"]) == 64
    assert identity["authorises_execution"] is False
    assert approval_status()["protocol_matches_expected"] is True


def test_authorisation_gate_refuses_while_b7_is_open():
    with pytest.raises(CampaignNotAuthorized, match="G3"):
        assert_campaign_authorized()


# ---------------------------------------------------------------------------
# arms, controls and the dispatcher contract
# ---------------------------------------------------------------------------


def test_dispatcher_declares_every_arm_in_registry_order(config):
    registry = build_registry(config.conditions)
    assert ARM_ORDER == registry.evaluation_arms
    assert set(ARM_RUNNERS) == set(ARM_ORDER)
    assert len(ARM_ORDER) == 12
    assert registry.conditions == ("A", "B", "C", "D", "E", "F")


def test_control_semantics_are_declared():
    assert CONTROL_MIRRORS == {"A_prime": "A", "C_prime": "C"}
    a_prime = requirements_for("A_prime")
    assert a_prime.stepper_kind == "plastic" and a_prime.eta == 0.0
    c_prime = requirements_for("C_prime")
    assert c_prime.requires_structure is True and c_prime.eta == 0.0
    assert requirements_for("B").eta == 0.5
    assert requirements_for("F").needs_decision_source is True
    floor = default_registry().spec("floor")
    assert floor.has_neural_substrate is False
    assert floor.controller == "constant_no_action"


def test_dispatcher_refuses_an_unknown_arm():
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=stub_runners())
    with pytest.raises(DispatcherError, match="not a campaign arm"):
        dispatcher.execute("Z", 1, 0, context_for())


@pytest.mark.parametrize(
    "arm",
    ["A", "B", "C", "D", "F", "A_prime", "C_prime", "F_beta", "F_init"],
)
def test_neural_arms_build_a_fresh_component_bundle(arm):
    factory = StubFactory()
    dispatcher = CampaignDispatcher(factory, arm_runners=stub_runners())
    context = context_for(arm=arm)
    record = dispatcher.execute(arm, 1, 0, context)
    neural_calls = [call for call in factory.calls if call[0] == "neural"]
    built = [call[1] for call in neural_calls]
    assert built[0] == arm
    if arm in CONTROL_MIRRORS:
        assert built == [arm, CONTROL_MIRRORS[arm]]
    else:
        assert built == [arm]
    call = dict(neural_calls[0][2])
    assert call["seed"] == 1 and call["episode"] == 0
    assert call["environment_seed"] == context["environment_seed"]
    assert call["master_seed"] == MASTER
    assert call["training"] is False
    assert record.row["condition"] == arm


def test_floor_and_conventional_routes_use_the_declared_interface():
    factory = StubFactory()
    log: list = []
    dispatcher = CampaignDispatcher(factory, arm_runners=stub_runners(log))
    for arm in ("E", "E_full", "floor"):
        record = dispatcher.execute(arm, 1, 0, context_for(arm=arm))
        assert record.row["condition"] == arm
    assert ("conventional", "E", {"seed": 1}) in factory.calls
    assert ("conventional", "E_full", {"seed": 1}) in factory.calls
    assert ("floor_adapter", None, {}) in factory.calls
    floor_kwargs = [entry[2] for entry in log if entry[0] == "floor"][0]
    assert set(floor_kwargs) >= {
        "seed",
        "episode",
        "environment_seed",
        "config_hashes",
        "input_hashes",
        "max_game_updates",
    }
    assert floor_kwargs["environment_seed"] == context_for()["environment_seed"]


def test_a_prime_reuses_the_paired_mirror_artefact():
    factory = StubFactory()
    log: list = []
    sentinel = object()

    def a_run(components, **kwargs):
        log.append(("A", components, dict(kwargs)))
        return {"row": row_for("A", kwargs["seed"], kwargs["episode"], kwargs["environment_seed"], kwargs["config_hashes"]), "marker": sentinel}

    def a_prime_run(components, *, fixed_result, **kwargs):
        log.append(("A_prime", components, dict(kwargs)))
        assert fixed_result["marker"] is sentinel
        result = {
            "row": row_for("A_prime", kwargs["seed"], kwargs["episode"], kwargs["environment_seed"], kwargs["config_hashes"])
        }
        result["equivalence"] = {"control_id": "A_prime", "all_equal": True}
        result["zero_pathway"] = {"eta": 0.0}
        return result

    runners = stub_runners()
    runners["A"] = a_run
    runners["A_prime"] = a_prime_run
    dispatcher = CampaignDispatcher(factory, arm_runners=runners)
    record = dispatcher.execute("A_prime", 3, 1, context_for(seed=3, episode=1, arm="A_prime"))
    assert [entry[0] for entry in log] == ["A", "A_prime"]
    assert log[0][2]["environment_seed"] == log[1][2]["environment_seed"]
    assert log[0][2]["environment_seed"] == environment_seed(MASTER, 3, 1)
    assert record.mirror == "A"
    assert record.row["evidence"]["equivalence"]["all_equal"] is True
    assert record.row["evidence"]["zero_pathway"]["eta"] == 0.0


def test_episode_failure_is_recorded_and_no_row_is_invented(tmp_path):
    def failing(components, **kwargs):
        raise RuntimeError("synthetic episode failure")

    runners = stub_runners()
    runners["B"] = failing
    log_path = tmp_path / "failures.jsonl"
    dispatcher = CampaignDispatcher(
        StubFactory(), arm_runners=runners, failure_log=log_path
    )
    with pytest.raises(EpisodeFailure) as caught:
        dispatcher.execute("B", 1, 0, context_for(arm="B"))
    failure = caught.value
    assert failure.stage == "episode"
    assert failure.as_dict()["cause_type"] == "RuntimeError"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["condition"] == "B"
    assert payload["seed"] == 1 and payload["episode"] == 0
    assert payload["stage"] == "episode"


def test_equivalence_mismatch_payload_survives_the_failure():
    payload = {
        "kind": "a_prime_mismatch",
        "control_id": "A_prime",
        "field_id": "P3",
        "seed": 1,
        "episode": 0,
        "required_action": "hard stop",
    }

    def mismatch(components, **kwargs):
        raise EquivalenceMismatch(payload)

    runners = stub_runners()
    runners["A_prime"] = mismatch
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=runners)
    with pytest.raises(EpisodeFailure) as caught:
        dispatcher.execute("A_prime", 1, 0, context_for(arm="A_prime"))
    assert caught.value.as_dict()["equivalence_mismatch"]["field_id"] == "P3"


def test_a_malformed_row_fails_validation():
    def bad_row(components, **kwargs):
        row = row_for(
            kwargs.get("condition", "A"),
            kwargs["seed"],
            kwargs["episode"],
            kwargs["environment_seed"],
            kwargs["config_hashes"],
        )
        row["survival_score"] = 99.0
        return {"row": row}

    runners = stub_runners()
    runners["A"] = bad_row
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=runners)
    with pytest.raises(EpisodeFailure) as caught:
        dispatcher.execute("A", 1, 0, context_for())
    assert caught.value.stage == "row"
    assert caught.value.as_dict()["cause_type"] == "SchemaError"


def test_dispatcher_describe_records_the_mirror_policy():
    described = CampaignDispatcher(StubFactory()).describe()
    assert described["control_mirrors"] == {"A_prime": "A", "C_prime": "C"}
    assert "no retry" in described["mirror_policy"]
    assert described["failure_log"] is None


# ---------------------------------------------------------------------------
# component factory
# ---------------------------------------------------------------------------


def test_factory_settings_match_the_declared_constants():
    settings = FactorySettings()
    assert settings.neural_dt_ms == 0.5
    assert settings.game_dt_s == pytest.approx(1.0 / 60.0)
    assert settings.window_ms == 50.0
    assert settings.distance_horizon == 25.0
    assert settings.max_game_updates == 900
    assert settings.noise_std_pa == 0.0


def test_factory_refuses_training_unknown_arms_and_wrong_seeds():
    factory = CampaignFactory()
    with pytest.raises(FactoryError, match="evaluation components only"):
        factory.neural_components("A", seed=1, episode=0, environment_seed=1, training=True)
    with pytest.raises(FactoryError, match="does not run the neural closed loop"):
        factory.neural_components("E", seed=1, episode=0, environment_seed=1)
    with pytest.raises(FactoryError, match="paired environment stream"):
        factory.neural_components("A", seed=1, episode=0, environment_seed=1)


def test_factory_uses_the_injected_registry(config):
    registry = build_registry(config.conditions)
    factory = CampaignFactory(registry=registry)
    assert factory.spec("A").role == "reference"
    assert factory.spec("A_prime").exact_match_of == "A"
    assert factory.spec("F_beta").state_independent is True


def test_training_artifacts_refuse_absent_models(config):
    artifacts = TrainingArtifacts()
    assert artifacts.empty is True
    with pytest.raises(FactoryError, match="no trained readout"):
        artifacts.readout("F", 1)
    with pytest.raises(FactoryError, match="no trained conventional agent"):
        artifacts.agent("E", 1)
    described = artifacts.describe()
    assert described["training_implemented_here"] is False
    assert described["readouts"] == [] and described["agents"] == []


def test_factory_input_hashes_are_contract_bound_and_cached(tmp_path):
    first = tmp_path / "alpha.bin"
    second = tmp_path / "beta.bin"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")
    factory = CampaignFactory(
        frozen_inputs={"alpha": str(first), "beta": str(second)}
    )
    digests = factory.input_hashes()
    assert set(digests) == {"alpha", "beta"}
    assert all(len(value) == 64 for value in digests.values())
    first.write_bytes(b"changed after the first hash")
    assert factory.input_hashes()["alpha"] == digests["alpha"]
    with pytest.raises(FactoryError, match="no frozen_inputs"):
        CampaignFactory().input_hashes()
    with pytest.raises(FactoryError, match="missing"):
        CampaignFactory(
            frozen_inputs={"alpha": str(tmp_path / "absent.bin")}
        ).input_hashes()


def test_factory_checks_the_game_timestep_and_adapter():
    class Game:
        dt = 1.0 / 60.0

    class Good:
        env = Game()
        observation_adapter = object()

    class Fast(Game):
        dt = 0.1

    class BadTimestep:
        env = Fast()
        observation_adapter = object()

    class BadAdapter:
        env = Game()
        observation_adapter = None

    assert CampaignFactory(environment_factory=Good).environment() is not None
    with pytest.raises(FactoryError, match="dt"):
        CampaignFactory(environment_factory=BadTimestep).environment()
    with pytest.raises(FactoryError, match="observation adapter"):
        CampaignFactory(environment_factory=BadAdapter).environment()


def test_factory_readout_width_must_match_the_motor_interface():
    factory = CampaignFactory()
    width = MotorFeatureSpec().n_features
    factory._check_readout_width(SimpleNamespace(n_features=width), "F")
    with pytest.raises(FactoryError, match="features"):
        factory._check_readout_width(SimpleNamespace(n_features=width + 1), "F")


class _RaisingGraphSource:
    def load(self, seed):
        raise GraphSelectionError(f"no certified graph for seed {seed}")

    def describe(self):
        return {"root": "synthetic", "required_seeds": [1]}

    def inspect_all(self):
        return []


def test_structure_arms_never_fall_back_to_the_biological_graph():
    assert STRUCTURE_ARMS == ("C", "D", "C_prime")
    world = SimpleNamespace(graph=object(), policy=object())
    factory = CampaignFactory(world=world, graphs=_RaisingGraphSource())
    graph, policy, structure = factory.graph_and_policy("A", 1)
    assert graph is world.graph and policy is world.policy and structure is None
    for arm in STRUCTURE_ARMS:
        with pytest.raises(GraphSelectionError):
            factory.graph_and_policy(arm, 1)


def test_factory_describe_states_no_training_and_no_mechanism():
    described = CampaignFactory().describe()
    assert described["training"]["training_implemented_here"] is False
    assert described["graphs"]["fallback_to_biological_graph"] is False
    assert set(described["structure_arms"]) == {"C", "D", "C_prime"}


# ---------------------------------------------------------------------------
# certified-graph enforcement
# ---------------------------------------------------------------------------


def _cert_record(tmp_path: Path, graph_path: Path, **overrides):
    record = {
        "construction": "target_exchange",
        "u18_status": "proposed",
        "master_seed": MASTER,
        "campaign_seed": 1,
        "seed": 1,
        "protocol_sha256": cert.EXPECTED_PROTOCOL_SHA256,
        "graph_path": graph_path.as_posix(),
        "graph_sha256": SHA,
        "graph_digest": OTHER,
        "randomization_quality": {"passed": True, "failures": []},
    }
    record.update(overrides)
    return record


def _namespace(tmp_path: Path) -> Path:
    namespace = tmp_path / "seed_1"
    namespace.mkdir()
    (namespace / cert.CERTIFICATE_NAME).write_bytes(b"synthetic certificate")
    graph = namespace / "graph_synthetic.npz"
    graph.write_bytes(b"synthetic graph")
    return namespace


def test_graph_source_rejects_an_uncertified_seed(tmp_path):
    source = CertifiedGraphSource(root=tmp_path, required_seeds=(1,))
    with pytest.raises(GraphSelectionError, match="no certified graph"):
        source.load(2)
    entry = source.inspect(1)
    assert entry["present"] is False
    assert entry["status"] == "missing"


def test_refused_certificate_is_never_a_fallback(tmp_path, monkeypatch):
    _namespace(tmp_path)

    def refuse(path):
        raise cert.CertificationError("mandatory gate R6 failed")

    monkeypatch.setattr(campaign_graphs.cert, "load_structure", refuse)
    source = CertifiedGraphSource(root=tmp_path, required_seeds=(1,))
    with pytest.raises(GraphSelectionError, match="refused"):
        source.load(1)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"randomization_quality": {"passed": False, "failures": ["R8"]}}, id="quality"),
        pytest.param({"construction": "degree_preserving"}, id="construction"),
        pytest.param({"master_seed": 1}, id="master"),
        pytest.param({"seed": 2}, id="seed"),
        pytest.param({"protocol_sha256": OTHER}, id="protocol"),
    ],
)
def test_invalid_certificate_records_are_fatal(tmp_path, monkeypatch, overrides):
    namespace = _namespace(tmp_path)
    graph = namespace / "graph_synthetic.npz"
    record = _cert_record(tmp_path, graph, **overrides)
    monkeypatch.setattr(
        campaign_graphs.cert, "load_structure", lambda path: (SimpleNamespace(n_nodes=2, n_edges=1), record)
    )
    source = CertifiedGraphSource(root=tmp_path, required_seeds=(1,))
    with pytest.raises(GraphSelectionError):
        source.load(1)


def test_missing_graph_file_is_fatal(tmp_path, monkeypatch):
    namespace = _namespace(tmp_path)
    missing = namespace / "absent.npz"
    record = _cert_record(tmp_path, missing)
    monkeypatch.setattr(
        campaign_graphs.cert, "load_structure", lambda path: (SimpleNamespace(n_nodes=2, n_edges=1), record)
    )
    with pytest.raises(GraphSelectionError, match="missing"):
        CertifiedGraphSource(root=tmp_path, required_seeds=(1,)).load(1)


def test_certificate_inspection_reports_marker_and_status(tmp_path, monkeypatch):
    namespace = _namespace(tmp_path)
    certificate = {
        "protocol": {"sha256": cert.EXPECTED_PROTOCOL_SHA256},
        "seed": {"structure_seed": 1, "campaign_seed": 1, "master_seed": MASTER},
        "output_graph": {"graph_digest": OTHER, "sha256": SHA},
        "construction": {"method": "target_exchange"},
    }
    monkeypatch.setattr(campaign_graphs.cert, "load_certificate", lambda path: certificate)
    monkeypatch.setattr(campaign_graphs.cert, "certificate_refusal_reason", lambda payload: None)
    source = CertifiedGraphSource(root=tmp_path, required_seeds=(1,))
    entry = source.inspect(1)
    assert entry["status"] == "certified"
    assert entry["graph_digest"] == OTHER

    monkeypatch.setattr(
        campaign_graphs.cert,
        "certificate_refusal_reason",
        lambda payload: "gate R14 not evaluated",
    )
    assert source.inspect(1)["status"] == "refused"

    (namespace / cert.MARKER_NAME).write_bytes(b"in progress")
    assert source.inspect(1)["status"] == "incomplete_namespace"


def test_target_exchange_alignment_fixture():
    def make(dst):
        return SimpleNamespace(
            threshold=30,
            n_nodes=3,
            n_edges=2,
            root_ids=np.array([10, 11, 12]),
            edge_src=np.array([0, 1]),
            edge_dst=np.asarray(dst),
            edge_weight=np.array([1.0, 2.0]),
            out_indptr=np.array([0, 1, 2]),
            in_indptr=np.array([0, 1, 2]),
        )

    report = assert_target_exchange_alignment(make([1, 2]), make([2, 1]))
    assert report["passed"] is True
    broken = make([2, 1])
    broken.edge_weight = np.array([1.0, 3.0])
    with pytest.raises(GraphSelectionError, match="edge_weight"):
        assert_target_exchange_alignment(make([1, 2]), broken)


# ---------------------------------------------------------------------------
# the dispatcher as a harness episode runner
# ---------------------------------------------------------------------------


def test_dispatcher_drives_the_harness_and_rows_round_trip(config, tmp_path):
    config = selected_config(config)
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=stub_runners())
    runner = start_harness(config, tmp_path, dispatcher)
    summary = runner.run()
    assert summary["planned"] == 12
    assert summary["executed"] == 12
    assert summary["complete"] is True
    rows = EpisodeStore(tmp_path / "run-1").rows()
    assert {row["condition"] for row in rows} == set(ARM_ORDER)
    for row in rows:
        assert row["seed"] == 1 and row["episode"] == 0
    a_prime = next(row for row in rows if row["condition"] == "A_prime")
    assert a_prime["evidence"]["equivalence"]["all_equal"] is True
    floor_row = next(row for row in rows if row["condition"] == "floor")
    assert floor_row["weights_before"] is None


def test_harness_stops_on_failure_without_a_fabricated_row(config, tmp_path):
    def failing(components, **kwargs):
        raise RuntimeError("stop the campaign")

    runners = stub_runners()
    runners["B"] = failing
    config = selected_config(config)
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=runners)
    runner = start_harness(config, tmp_path, dispatcher)
    with pytest.raises(EpisodeFailure):
        runner.run()
    store = EpisodeStore(tmp_path / "run-1")
    assert len(store) == 1
    assert store.has("A", 1, 0)
    assert not store.has("B", 1, 0)


def test_resume_continues_an_interrupted_run(config, tmp_path):
    config = selected_config(config, episodes=2)
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=stub_runners())
    runner = start_harness(config, tmp_path, dispatcher)
    assert runner.run(limit=3)["executed"] == 3
    resumed = CampaignRunner.resume(
        config,
        tmp_path / "run-1",
        episode_runner=dispatcher,
        preflight=passing_gate,
    )
    assert len(resumed.store) == 3
    summary = resumed.run()
    assert summary["executed"] == 21
    assert summary["complete"] is True


# ---------------------------------------------------------------------------
# run status and incomplete-run detection
# ---------------------------------------------------------------------------


def test_status_detects_complete_and_incomplete_runs(config, tmp_path):
    config = selected_config(config, episodes=2)
    plan = evaluation_plan(config)
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=stub_runners())
    runner = start_harness(config, tmp_path, dispatcher)
    runner.run(limit=3)

    partial = run_status(tmp_path / "run-1", config=config)
    assert partial["plan_available"] is True
    assert partial["planned"] == len(plan)
    assert partial["rows"] == 3
    assert partial["missing"] == len(plan) - 3
    assert partial["complete"] is False
    assert partial["per_arm"] == {"A": 2, "B": 1}

    runner.run()
    complete = run_status(tmp_path / "run-1", config=config)
    assert complete["complete"] is True
    assert complete["missing"] == 0
    assert complete["store_error"] is None
    assert complete["config_hash_drift"] == []


def test_status_reports_configuration_drift_and_torn_store(config, tmp_path):
    config = selected_config(config)
    dispatcher = CampaignDispatcher(StubFactory(), arm_runners=stub_runners())
    runner = start_harness(config, tmp_path, dispatcher)
    runner.run()

    drifted = replace(
        config,
        hashes={
            **config.hashes,
            "environment": {"path": "configs/phase_8/environment.yaml", "sha256": OTHER},
        },
    )
    report = run_status(tmp_path / "run-1", config=drifted)
    assert report["config_hash_drift"] == ["environment"]
    assert report["complete"] is False

    with (tmp_path / "run-1" / "episodes.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"schema_version": 1')
    torn = run_status(tmp_path / "run-1", config=config)
    assert torn["complete"] is False
    assert "unterminated" in torn["store_error"]


def test_status_without_a_plan_or_directory(tmp_path):
    missing = run_status(tmp_path / "absent")
    assert missing["exists"] is False
    assert missing["complete"] is False
    assert "does not exist" in missing["reason"]

    directory = tmp_path / "empty"
    directory.mkdir()
    no_plan = run_status(directory)
    assert no_plan["plan_available"] is False
    assert no_plan["complete"] is False


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def test_cli_check_is_read_only_and_never_executable(capsys):
    code = cli.main(["check"])
    payload = json.loads(capsys.readouterr().out)
    assert code in (cli.EXIT_OK, cli.EXIT_INCOMPLETE)
    assert payload["executable"] is False
    assert payload["conformance"]["conforms"] is True
    assert len(payload["execution_blockers"]) == 2
    assert any(item.startswith("B7") for item in payload["execution_blockers"])
    assert payload["certified_graphs"]["required"] == 16


def test_cli_seeds_matches_the_seed_module(capsys):
    code = cli.main(["seeds", "--seed", "1"])
    payload = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_OK
    checks = payload["shared_checks"]
    assert all(checks.values())
    assert payload["plans"]["A"]["environment"] == environment_seed(MASTER, 1, 0)
    assert payload["plans"]["floor"]["network"] is None


def test_cli_start_and_resume_refuse_without_side_effects(tmp_path, capsys):
    before = set(tmp_path.iterdir())
    start_code = cli.main(
        ["--campaign", "configs/phase_8/campaign.yaml", "start", "--run-id", "would-be-run"]
    )
    start_payload = json.loads(capsys.readouterr().out)
    assert start_code == cli.EXIT_REFUSED
    assert start_payload["authorized"] is False
    assert start_payload["refused"] is True
    assert start_payload["executed"] is False
    assert start_payload["episodes_run"] == 0
    assert start_payload["rows_written"] == 0
    assert "G3" in start_payload["reason"]

    resume_code = cli.main(["resume", str(tmp_path / "absent")])
    resume_payload = json.loads(capsys.readouterr().out)
    assert resume_code == cli.EXIT_REFUSED
    assert resume_payload["refused"] is True
    assert set(tmp_path.iterdir()) == before


def test_cli_status_reports_an_incomplete_run(tmp_path, capsys):
    code = cli.main(["status", str(tmp_path / "absent")])
    payload = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_INCOMPLETE
    assert payload["complete"] is False
    assert payload["read_only"] is True


def test_cli_graphs_inspects_a_real_certificate(capsys):
    source = CertifiedGraphSource()
    if not source.certificate_path(1).is_file():
        pytest.skip("no certified graph for seed 1 in this checkout")
    code = cli.main(["graphs", "--seed", "1"])
    payload = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_OK
    assert payload["certificate"]["status"] == "certified"
    assert payload["certificate"]["construction"] == "target_exchange"
