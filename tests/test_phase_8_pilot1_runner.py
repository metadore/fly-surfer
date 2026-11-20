"""Synthetic tests for the production Pilot 1 episode runner (REV4 §10.3).

Every episode here runs on the 32-node test network from
``test_phase_8_conditions`` through the existing controlled game. No BANC-scale
graph, no certified random graph and no trained artifact is loaded; the sites
are a fixture, not a biological claim. All stored rows are labelled
``evidence_kind: synthetic_fixture`` and ``experimental_evidence: False``.

Covered: the nine-entry grid, the declared seed schedule, reproducibility,
episode isolation, failure rows, schema and provenance, the episode-aware
factory seed check, and the refusal that keeps synthetic output from becoming
experimental evidence.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from experiments.phase_8.campaign.factory import CampaignFactory, FactoryError
from experiments.phase_8.campaign.protocol import CampaignNotAuthorized
from experiments.phase_8.config import load_phase8_config
from experiments.phase_8.schema import validate_episode_row
from experiments.phase_8.seeds import environment_seed, seed_plan
from experiments.phase_8.stages import pilot1
from experiments.phase_8.stages.common import PilotPlan, StageConfigurationError, drive_pilot
from experiments.phase_8.stages.pilot1_runner import (
    PILOT1_CONDITION,
    Pilot1EpisodeRunner,
)

from test_phase_8_conditions import (
    build_world,
    decoder_config,
    make_bundle,
    make_drive_clock,
    make_fixed_stepper,
    make_graph,
)

MASTER = 20261116
SHA = "a" * 64
UPDATES = 8
PILOT_SEEDS = (9001, 9002, 9003)
EPISODES = (0, 1, 2)

FIXTURE_INPUT_HASHES = {"fixture_graph": "b" * 64}
MANIFEST_INPUT_HASHES = {
    "fixture_graph": {"path": "fixture_graph.npz", "sha256": SHA}
}


def fake_preflight(gate_gb: float) -> dict:
    return {
        "available_gb": 999.0,
        "gate_gb": float(gate_gb),
        "passed": True,
        "reason": "synthetic preflight for the pilot runner tests",
    }


def small_config():
    config = load_phase8_config()
    campaign = replace(config.campaign, max_game_updates=UPDATES)
    return replace(config, campaign=campaign)


class ExplodingAdapter:
    """A real adapter whose first game update fails, to exercise error rows."""

    def __init__(self, inner):
        self._inner = inner
        self.game = inner.game

    def reset(self, seed=None):
        return self._inner.reset(seed)

    def step(self, decision):
        raise RuntimeError("synthetic adapter failure")


class SyntheticAFactory:
    """Build a fresh 32-node A bundle per call; records every request."""

    def __init__(self, world, *, max_steps: int = UPDATES, fail: bool = False) -> None:
        self.world = world
        self.max_steps = int(max_steps)
        self.fail = bool(fail)
        self.calls: list[dict] = []

    def input_hashes(self) -> dict[str, str]:
        return dict(FIXTURE_INPUT_HASHES)

    def neural_components(
        self,
        arm,
        *,
        seed,
        episode,
        environment_seed,
        master_seed,
        training=False,
    ):
        assert arm == PILOT1_CONDITION
        assert not training
        self.calls.append(
            {
                "arm": arm,
                "seed": int(seed),
                "episode": int(episode),
                "environment_seed": int(environment_seed),
                "master_seed": int(master_seed),
            }
        )
        plan = seed_plan(int(master_seed), arm, int(seed), episode=int(episode))
        drive, clock = make_drive_clock(self.world)
        stepper = make_fixed_stepper(self.world, drive, clock, seed=int(seed))
        components = make_bundle(
            self.world,
            drive=drive,
            clock=clock,
            stepper=stepper,
            condition_id=arm,
            max_steps=self.max_steps,
        )
        if self.fail:
            components.neural.adapter = ExplodingAdapter(components.neural.adapter)
        components.metadata = {
            "condition_id": arm,
            "seed": int(seed),
            "episode": int(episode),
            "environment_seed": int(environment_seed),
            "master_seed": int(master_seed),
            "network_seed": int(plan["network"]),
            "learning_seed": int(plan["learning"]),
            "structure_seed": int(plan["structure"]),
            "policy_source": "biological_graph",
            "training": False,
        }
        return components


@pytest.fixture(scope="module")
def world():
    return build_world(make_graph())


def read_rows(run_dir, config):
    lines = (run_dir / config.campaign.episode_store_name).read_text(
        encoding="utf-8"
    ).splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def drive(factory, *, base_dir, run_id="pilot1_synthetic"):
    config = small_config()
    summary = pilot1.run_pilot1(
        config,
        base_dir=base_dir,
        run_id=run_id,
        episode_runner=Pilot1EpisodeRunner(config, factory=factory),
        preflight=fake_preflight,
        synthetic_fixture=True,
        input_hashes=MANIFEST_INPUT_HASHES,
    )
    return config, summary, read_rows(base_dir / run_id, config)


# ---------------------------------------------------------------------------
# the nine-entry grid
# ---------------------------------------------------------------------------


def test_runner_records_all_nine_planned_episodes(world, tmp_path):
    factory = SyntheticAFactory(world)
    config, summary, rows = drive(factory, base_dir=tmp_path / "runs")

    assert summary["evidence_kind"] == "synthetic_fixture"
    assert summary["experimental_evidence"] is False
    assert summary["planned"] == 9 and summary["rows_stored"] == 9
    assert summary["rows_executed"] == 9 and summary["complete"] is True
    assert summary["estimates_contrasts"] is False
    assert summary["merged_into_campaign"] is False

    keys = {(row["condition"], row["seed"], row["episode"]) for row in rows}
    assert keys == {
        ("A", seed, episode) for seed in PILOT_SEEDS for episode in EPISODES
    }
    assert len(factory.calls) == 9
    assert all(call["arm"] == "A" for call in factory.calls)


def test_rows_carry_the_synthetic_labels_and_full_schema(world, tmp_path):
    _, _, rows = drive(SyntheticAFactory(world), base_dir=tmp_path / "runs")
    for row in rows:
        checked = validate_episode_row(row, expected_condition="A")
        assert checked["training"] is False
        assert checked["role"] == "reference"
        assert checked.get("status", "ok") == "ok"
        notes = checked["notes"]
        assert notes["evidence_kind"] == "synthetic_fixture"
        assert notes["experimental_evidence"] is False
        assert notes["not_experimental"] is True


def test_rows_record_updates_neurons_actions_rewards_and_survival(world, tmp_path):
    _, _, rows = drive(SyntheticAFactory(world), base_dir=tmp_path / "runs")
    for row in rows:
        loop = row["notes"]["game_loop"]
        assert loop["game_updates"] == row["steps"] == row["observed_updates"]
        assert loop["neural_steps"] >= loop["game_updates"]
        assert loop["mean_steps_per_update"] > 0.0
        assert loop["neural_resets_during_episode"] == 0
        assert loop["motor_spikes"] == row["motor_spikes"]
        assert loop["action_counts"] == row["action_counts"]
        assert loop["total_reward"] == row["total_reward"]
        assert loop["survival_score"] == row["survival_score"]
        assert loop["terminated"] == row["terminated"]
        assert loop["truncated"] == row["truncated"]
        assert loop["termination_reason"] == row["termination_reason"]
        assert row["weights_before"] == row["weights_after"]
        assert loop["weights_unchanged"] is True
        assert sum(row["action_counts"].values()) == row["steps"]
        assert row["motor_summary"]["decisions"] == row["steps"]


# ---------------------------------------------------------------------------
# deterministic seeds and episode isolation
# ---------------------------------------------------------------------------


def test_seed_schedule_and_episode_isolation(world, tmp_path):
    factory = SyntheticAFactory(world)
    config, _, rows = drive(factory, base_dir=tmp_path / "runs")

    expected = {
        (seed, episode): environment_seed(MASTER, seed, episode)
        for seed in PILOT_SEEDS
        for episode in EPISODES
    }
    by_key = {(row["seed"], row["episode"]): row for row in rows}
    assert set(by_key) == set(expected)
    assert len(set(expected.values())) == 9
    for key, env_seed in expected.items():
        assert by_key[key]["environment_seed"] == env_seed
        assert by_key[key]["notes"]["component_metadata"]["environment_seed"] == env_seed
        assert by_key[key]["notes"]["component_metadata"]["master_seed"] == MASTER

    # Every episode built its own components with its own environment seed.
    assert len({call["environment_seed"] for call in factory.calls}) == 9
    assert len({(call["seed"], call["episode"]) for call in factory.calls}) == 9


def test_identical_inputs_reproduce_identical_rows(world, tmp_path):
    _, _, first = drive(SyntheticAFactory(world), base_dir=tmp_path / "first", run_id="r")
    _, _, second = drive(SyntheticAFactory(world), base_dir=tmp_path / "second", run_id="r")

    def comparable(row):
        return {
            key: row[key]
            for key in (
                "condition",
                "seed",
                "episode",
                "environment_seed",
                "steps",
                "action_counts",
                "total_reward",
                "terminated",
                "truncated",
                "termination_reason",
                "motor_spikes",
                "spike_sha256",
                "action_sha256",
                "weights_before",
                "weights_after",
            )
        }

    assert [comparable(row) for row in first] == [comparable(row) for row in second]
    assert [
        row["notes"]["game_loop"]["neural_steps"] for row in first
    ] == [row["notes"]["game_loop"]["neural_steps"] for row in second]


# ---------------------------------------------------------------------------
# failures
# ---------------------------------------------------------------------------


def test_episode_failures_are_valid_error_rows(world, tmp_path):
    factory = SyntheticAFactory(world, fail=True)
    _, summary, rows = drive(factory, base_dir=tmp_path / "runs")

    assert summary["rows_stored"] == 9 and summary["complete"] is True
    assert len(factory.calls) == 9
    for row in rows:
        checked = validate_episode_row(row, expected_condition="A")
        assert checked["status"] == "error"
        assert "RuntimeError" in checked["error"]
        assert checked["steps"] == 0
        assert checked["action_counts"] == {"NO_ACTION": 0}
        assert checked["terminated"] is False and checked["truncated"] is False
        notes = checked["notes"]
        assert notes["failure"]["error_type"] == "RuntimeError"
        assert notes["evidence_kind"] == "synthetic_fixture"
        assert notes["experimental_evidence"] is False


def test_configuration_error_stops_before_any_row(world, tmp_path):
    factory = SyntheticAFactory(world)
    config = small_config()
    runner = Pilot1EpisodeRunner(config, factory=factory)
    context = {
        "master_seed": MASTER,
        "environment_seed": environment_seed(MASTER, 9001, 0) + 1,
        "config_hashes": {name: entry["sha256"] for name, entry in config.hashes.items()},
        "max_game_updates": UPDATES,
        "episodes_per_seed": 3,
    }
    with pytest.raises(StageConfigurationError, match="declared stream value"):
        runner("A", 9001, 0, context)
    assert factory.calls == []


def test_runner_refuses_an_arm_other_than_a(world):
    config = small_config()
    runner = Pilot1EpisodeRunner(config, factory=SyntheticAFactory(world))
    with pytest.raises(StageConfigurationError, match="condition A only"):
        runner("B", 9001, 0, {})


# ---------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------


def test_rows_preserve_configuration_and_component_provenance(world, tmp_path):
    config, _, rows = drive(SyntheticAFactory(world), base_dir=tmp_path / "runs")
    declared_hashes = {
        name: entry["sha256"] for name, entry in config.hashes.items()
    }
    for row in rows:
        assert row["config_hashes"] == declared_hashes
        assert row["input_hashes"] == FIXTURE_INPUT_HASHES
        notes = row["notes"]
        assert notes["runner"].endswith("Pilot1EpisodeRunner")
        assert notes["condition_source"] == "experiments.phase_8.conditions.a_fixed"
        assert notes["substrate"] == "biological_graph"
        metadata = notes["component_metadata"]
        assert metadata["policy_source"] == "biological_graph"
        assert metadata["training"] is False
        expected = seed_plan(MASTER, "A", row["seed"], episode=row["episode"])
        assert metadata["network_seed"] == expected["network"]
        assert metadata["learning_seed"] == expected["learning"]
        assert metadata["structure_seed"] == expected["structure"]


# ---------------------------------------------------------------------------
# the episode-aware factory seed check
# ---------------------------------------------------------------------------


def test_factory_accepts_each_episode_environment_seed(world, monkeypatch):
    from brain.neuron_model import LIFParameters
    from environment import ControlledGameEnvironment

    world.neuron_params = LIFParameters()
    world.decoder_config = decoder_config()
    drive, _ = make_drive_clock(world)
    factory = CampaignFactory(
        world=world,
        environment_factory=lambda: ControlledGameEnvironment(
            max_steps=UPDATES, render_mode=None
        ),
    )
    monkeypatch.setattr(factory, "_sensory", lambda: (None, drive))

    for episode in EPISODES:
        components = factory.neural_components(
            "A",
            seed=9001,
            episode=episode,
            environment_seed=environment_seed(MASTER, 9001, episode),
            master_seed=MASTER,
        )
        assert components.metadata["episode"] == episode
        assert components.metadata["environment_seed"] == environment_seed(
            MASTER, 9001, episode
        )

    with pytest.raises(FactoryError, match="paired environment stream"):
        factory.neural_components(
            "A",
            seed=9001,
            episode=1,
            environment_seed=environment_seed(MASTER, 9001, 2),
            master_seed=MASTER,
        )


# ---------------------------------------------------------------------------
# no accidental experimental execution
# ---------------------------------------------------------------------------


def test_forged_plan_cannot_exploit_the_pilot1_exemption(tmp_path):
    config = small_config()
    plan = PilotPlan(
        stage="pilot1",
        rev4_step="10.3",
        arms=("C",),
        seeds=PILOT_SEEDS,
        episodes=3,
        establishes="nothing: this is a forged plan",
        does_not_establish="nothing",
    )
    calls: list[tuple[str, int, int]] = []

    def spy(arm, seed, episode, context):
        calls.append((arm, seed, episode))
        raise AssertionError("the runner must not be reached by a forged plan")

    base = tmp_path / "forged"
    with pytest.raises(CampaignNotAuthorized, match="D2 Pilot 1 scope"):
        drive_pilot(
            plan,
            config,
            base_dir=base,
            run_id="forged",
            episode_runner=spy,
            preflight=fake_preflight,
            input_hashes=MANIFEST_INPUT_HASHES,
        )
    assert calls == []
    assert not base.exists()


def test_runner_factory_is_untouched_by_an_unauthorised_grid(tmp_path):
    config = small_config()
    runner = Pilot1EpisodeRunner(config)
    plan = PilotPlan(
        stage="pilot1",
        rev4_step="10.3",
        arms=("A",),
        seeds=(9001, 9002),
        episodes=3,
        establishes="nothing: this is a shortened grid",
        does_not_establish="nothing",
    )
    base = tmp_path / "must_not_exist"
    with pytest.raises(CampaignNotAuthorized, match="D2 Pilot 1 scope"):
        drive_pilot(
            plan,
            config,
            base_dir=base,
            run_id="short",
            episode_runner=runner,
            preflight=fake_preflight,
            input_hashes=MANIFEST_INPUT_HASHES,
        )
    assert runner._factory is None
    assert not base.exists()


def test_cli_describe_writes_nothing_and_reports_the_exemption(tmp_path):
    base = tmp_path / "cli_describe"
    code = pilot1.main(["--describe", "--base-dir", str(base)])
    assert code == pilot1.EXIT_OK
    assert not base.exists()
