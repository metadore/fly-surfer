"""Focused tests for the Phase 8 campaign skeleton (G5, REV3 §10.1).

The acceptance criteria are exercised directly: a malformed row is rejected, a
1-update dummy episode round-trips, resume is idempotent on
``(condition, seed, episode)``, and no result directory is overwritten. No
game, neural simulation, randomisation or training is started here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from experiments.phase_8 import (
    ARM_IDS,
    CONDITION_IDS,
    CampaignRunner,
    EpisodeStore,
    MemoryGateError,
    SchemaError,
    StoreError,
    build_manifest,
    build_registry,
    confirmatory_contrasts,
    default_registry,
    environment_seed,
    evaluation_plan,
    hash_inputs,
    load_manifest,
    load_phase8_config,
    memory_preflight,
    seed_plan,
    validate_episode_row,
    validate_manifest,
    validate_rows,
    write_manifest,
)
from experiments.phase_8.config import (
    CONFIG_DIR,
    ConfigError,
    load_campaign_config,
    load_conditions_config,
    load_environment_config,
)
from experiments.phase_8.seeds import condition_sequence, structure_sequence
from experiments.phase_8.store import (
    DuplicateEpisodeError,
    ExistingResultError,
    read_store,
    resolve_run_directory,
)

SHA = "a" * 64
OTHER = "b" * 64


# ---------------------------------------------------------------------------
# fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def config():
    return load_phase8_config()


def dummy_row(**overrides):
    row = {
        "schema_version": 1,
        "condition": "A",
        "role": "reference",
        "seed": 1,
        "episode": 0,
        "environment_seed": 123456,
        "training": False,
        "steps": 1,
        "observed_updates": 1,
        "survival_score": 1.0,
        "max_game_updates": 900,
        "total_reward": 0.01,
        "terminated": False,
        "truncated": True,
        "termination_reason": "rollout_step_cap",
        "action_counts": {"NO_ACTION": 1},
        "no_action_fraction": 1.0,
        "motor_spikes": 0,
        "spike_sha256": None,
        "action_sha256": SHA,
        "weights_before": SHA,
        "weights_after": SHA,
        "config_hashes": {
            "environment": SHA,
            "campaign": SHA,
            "conditions": SHA,
        },
        "input_hashes": {"graph": SHA},
        "started_at": "2026-11-17T00:00:00Z",
        "wall_time_s": 0.5,
    }
    row.update(overrides)
    return row


_MUTATIONS = {
    "campaign": (
        "campaign.yaml",
        lambda raw: raw["design"].__setitem__("n_seeds_selected", 12),
    ),
    "overlap": (
        "campaign.yaml",
        lambda raw: raw["seeds"].__setitem__(
            "training", raw["seeds"]["campaign"][:1]
        ),
    ),
    "unknown": ("campaign.yaml", lambda raw: raw.__setitem__("surprise", 1)),
    "fallback": (
        "campaign.yaml",
        lambda raw: raw["design"].__setitem__("n_seeds_fallback", 16),
    ),
    "missing_frozen": (
        "campaign.yaml",
        lambda raw: raw["frozen_inputs"].pop("graph"),
    ),
    "master": ("campaign.yaml", lambda raw: raw.__setitem__("master_seed", 1)),
    "speed": (
        "environment.yaml",
        lambda raw: raw.__setitem__("max_speed", 1.0),
    ),
    "eta": (
        "conditions.yaml",
        lambda raw: raw["controls"]["A_prime"].__setitem__("eta", 0.1),
    ),
    "state": (
        "conditions.yaml",
        lambda raw: raw["controls"]["F_beta"].__setitem__(
            "state_independent", False
        ),
    ),
    "missing_arm": (
        "conditions.yaml",
        lambda raw: raw["exploratory"].pop("E_full"),
    ),
    "f_drop": (
        "conditions.yaml",
        lambda raw: raw["conditions"].pop("F"),
    ),
}


def mutated_config_dir(tmp_path: Path, key: str) -> Path:
    filename, mutate = _MUTATIONS[key]
    raw = yaml.safe_load((CONFIG_DIR / filename).read_text(encoding="utf-8"))
    mutate(raw)
    target_dir = tmp_path / key
    target_dir.mkdir()
    for name in ("campaign.yaml", "environment.yaml", "conditions.yaml"):
        payload = raw if name == filename else yaml.safe_load(
            (CONFIG_DIR / name).read_text(encoding="utf-8")
        )
        (target_dir / name).write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
    return target_dir


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def test_configuration_loads_and_records_hashes(config):
    assert config.environment.max_steps == 900
    assert config.environment.distance_horizon == 25.0
    assert config.campaign.master_seed == 20261116
    assert config.campaign.n_seeds_primary == 16
    assert config.campaign.n_seeds_fallback == 10
    assert config.campaign.n_seeds_selected is None
    assert config.campaign.episodes_per_seed == 10
    assert config.campaign.memory_gate_gb == 4.0
    assert config.campaign.sei_updates == 100
    assert config.campaign.bootstrap_resamples == 10_000
    assert set(config.hashes) == {"environment", "campaign", "conditions"}
    for entry in config.hashes.values():
        assert len(entry["sha256"]) == 64
        assert entry["path"].startswith("configs/phase_8/")
    assert set(config.campaign.frozen_inputs) == {
        "graph",
        "nodes",
        "synapse_policy",
        "neuron_config",
        "sensory_mapping",
        "motor_decoder",
        "plasticity",
    }


def test_declared_design_cannot_start_before_the_pilot_decision(config):
    with pytest.raises(ConfigError, match="n_seeds_selected is null"):
        config.campaign.active_seeds()
    selected = replace(config.campaign, n_seeds_selected=16)
    assert selected.active_seeds() == config.campaign.campaign_seeds[:16]
    fallback = replace(config.campaign, n_seeds_selected=10)
    assert len(fallback.active_seeds()) == 10


def test_describe_includes_seed_derivation_and_approval(config):
    described = config.describe()
    assert described["approval"].startswith("not approved")
    assert described["seed_derivation"]["master_seed"] == 20261116
    assert described["seed_derivation"]["condition_codes"]["F_beta"] == 8


@pytest.mark.parametrize("key", sorted(_MUTATIONS))
def test_inconsistent_configuration_is_rejected(tmp_path, key):
    directory = mutated_config_dir(tmp_path, key)
    with pytest.raises(ConfigError):
        load_phase8_config(
            environment_path=directory / "environment.yaml",
            campaign_path=directory / "campaign.yaml",
            conditions_path=directory / "conditions.yaml",
        )


def test_environment_config_rejects_wrong_type(tmp_path):
    raw = yaml.safe_load(
        (CONFIG_DIR / "environment.yaml").read_text(encoding="utf-8")
    )
    raw["max_steps"] = True
    target = tmp_path / "environment.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="max_steps"):
        load_environment_config(target)


def test_campaign_config_rejects_absolute_input_path(tmp_path):
    raw = yaml.safe_load(
        (CONFIG_DIR / "campaign.yaml").read_text(encoding="utf-8")
    )
    raw["frozen_inputs"]["graph"] = str(tmp_path / "graph.npz")
    target = tmp_path / "campaign.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="relative"):
        load_campaign_config(target)


def test_conditions_config_declares_six_conditions(config):
    assert tuple(config.conditions.conditions) == ("A", "B", "C", "D", "E", "F")
    assert tuple(config.conditions.controls) == (
        "A_prime",
        "C_prime",
        "F_beta",
        "F_init",
    )
    assert tuple(config.conditions.exploratory) == ("E_full",)
    assert config.conditions.spec("B")["eta"] == 0.5
    assert config.conditions.spec("A_prime")["eta"] == 0.0
    assert config.conditions.spec("F_beta")["state_independent"] is True
    assert config.conditions.spec("A")["role"] == "reference"


# ---------------------------------------------------------------------------
# seeds
# ---------------------------------------------------------------------------


def test_environment_seed_is_paired_across_conditions():
    master = 20261116
    first = environment_seed(master, 3, 0)
    assert environment_seed(master, 3, 0) == first
    assert environment_seed(master, 3, 1) != first
    assert environment_seed(master, 4, 0) != first
    plan_a = seed_plan(master, "A", 3, episode=0)
    plan_b = seed_plan(master, "B", 3, episode=0)
    assert plan_a["environment"] == plan_b["environment"]
    assert plan_a["structure"] == plan_b["structure"]
    assert plan_a["network"] != plan_b["network"]
    assert plan_a["learning"] != plan_b["learning"]
    assert plan_a["environment"] == first


def test_structure_stream_is_shared_by_c_d_and_c_prime():
    master = 20261116
    seeds = [seed_plan(master, name, 7)["structure"] for name in ("C", "D", "C_prime")]
    assert len(set(seeds)) == 1
    assert structure_sequence(master, 7).entropy == [
        master,
        7,
        4,
    ]


def test_condition_stream_rejects_environment_and_structure():
    with pytest.raises(ValueError):
        condition_sequence(20261116, "A", 1, "environment")
    with pytest.raises(ValueError):
        condition_sequence(20261116, "A", 1, "structure")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def test_one_update_dummy_episode_validates():
    checked = validate_episode_row(dummy_row())
    assert checked["steps"] == 1
    assert checked["survival_score"] == 1.0
    checked["notes"] = "copy is mutable"
    assert "notes" not in dummy_row()


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"survival_score": 2.0}, id="not-capped-score"),
        pytest.param({"observed_updates": 2}, id="observed-vs-steps"),
        pytest.param({"action_counts": {"NO_ACTION": 2}}, id="count-sum"),
        pytest.param(
            {"action_counts": {"ROLL": 1}, "no_action_fraction": 0.0},
            id="unknown-action",
        ),
        pytest.param({"no_action_fraction": 0.5}, id="fraction"),
        pytest.param({"terminated": True}, id="terminated-and-truncated"),
        pytest.param({"termination_reason": None}, id="truncated-no-reason"),
        pytest.param({"action_sha256": "xyz"}, id="bad-digest"),
        pytest.param({"weights_after": None}, id="half-weight-pair"),
        pytest.param({"schema_version": 2}, id="wrong-version"),
        pytest.param({"condition": "Z"}, id="unknown-condition"),
        pytest.param({"role": "guess"}, id="unknown-role"),
        pytest.param({"started_at": "2026-11-17T00:00:00"}, id="naive-time"),
        pytest.param({"surprise": 1}, id="unknown-key"),
        pytest.param({"motor_spikes": -1}, id="negative-spikes"),
        pytest.param({"wall_time_s": -0.1}, id="negative-wall-time"),
        pytest.param({"config_hashes": {"environment": SHA}}, id="missing-config"),
    ],
)
def test_malformed_row_is_rejected(overrides):
    with pytest.raises(SchemaError):
        validate_episode_row(dummy_row(**overrides))


def test_missing_required_key_is_rejected():
    row = dummy_row()
    row.pop("input_hashes")
    with pytest.raises(SchemaError, match="missing"):
        validate_episode_row(row)


def test_floor_and_control_rows_are_recordable():
    assert validate_episode_row(
        dummy_row(condition="floor", role="floor", weights_before=None, weights_after=None)
    )["condition"] == "floor"
    assert validate_episode_row(
        dummy_row(condition="F_beta", role="control")
    )["condition"] == "F_beta"
    assert set(ARM_IDS) >= set(CONDITION_IDS)


def test_duplicate_episode_keys_are_refused():
    with pytest.raises(SchemaError, match="duplicate"):
        validate_rows([dummy_row(), dummy_row()])
    validate_rows([dummy_row(), dummy_row(episode=1)])


# ---------------------------------------------------------------------------
# store
# ---------------------------------------------------------------------------


def test_episode_store_round_trip(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    store = EpisodeStore(run_dir)
    key = store.append(dummy_row())
    assert key == ("A", 1, 0)
    assert len(store) == 1
    assert store.has("A", 1, 0)
    reopened = EpisodeStore(run_dir)
    rows = reopened.rows()
    assert len(rows) == 1
    assert rows[0]["condition"] == "A"
    assert read_store(run_dir / "episodes.jsonl")[0]["episode"] == 0


def test_resume_is_idempotent_on_the_episode_key(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    store = EpisodeStore(run_dir)
    assert store.write_if_new(dummy_row()) is True
    before = store.path.read_bytes()
    assert store.write_if_new(dummy_row()) is False
    assert store.path.read_bytes() == before
    assert len(EpisodeStore(run_dir)) == 1
    with pytest.raises(DuplicateEpisodeError):
        store.append(dummy_row())


def test_resume_plan_lists_only_missing_keys(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    store = EpisodeStore(run_dir)
    store.append(dummy_row(condition="A", seed=1, episode=0))
    plan = [
        ("A", 1, 0),
        ("A", 1, 1),
        ("B", 1, 0),
    ]
    assert store.missing(plan) == [("A", 1, 1), ("B", 1, 0)]


def test_invalid_row_is_never_written(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    store = EpisodeStore(run_dir)
    with pytest.raises(SchemaError):
        store.append(dummy_row(survival_score=99.0))
    assert not store.path.exists()
    assert len(store) == 0


def test_torn_tail_is_reported_not_repaired(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    store = EpisodeStore(run_dir)
    store.append(dummy_row())
    with store.path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"schema_version": 1')
    with pytest.raises(StoreError, match="unterminated"):
        EpisodeStore(run_dir)


def test_existing_result_directory_is_refused(tmp_path):
    run_dir = resolve_run_directory(tmp_path, "run-1")
    sentinel = run_dir / "keep.txt"
    sentinel.write_text("do not delete", encoding="utf-8")

    with pytest.raises(ExistingResultError, match="already exists"):
        resolve_run_directory(tmp_path, "run-1")
    assert sentinel.read_text(encoding="utf-8") == "do not delete"

    fresh = resolve_run_directory(tmp_path, "run-1", new_run_id="run-2")
    assert fresh == tmp_path / "run-2"
    assert sentinel.read_text(encoding="utf-8") == "do not delete"

    with pytest.raises(ExistingResultError):
        resolve_run_directory(tmp_path, "run-1", new_run_id="run-2")
    with pytest.raises(StoreError, match="must differ"):
        resolve_run_directory(tmp_path, "run-1", new_run_id="run-1")


def test_missing_store_and_bad_run_id_are_errors(tmp_path):
    with pytest.raises(StoreError, match="not found"):
        read_store(tmp_path / "absent.jsonl")
    with pytest.raises(StoreError, match="run_id"):
        resolve_run_directory(tmp_path, "../escape")


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def test_manifest_round_trip_and_refusal_to_overwrite(tmp_path, config):
    fixture = tmp_path / "input.bin"
    fixture.write_bytes(b"phase 8 fixture")
    inputs = hash_inputs({"fixture": fixture})
    assert inputs["fixture"]["sha256"] != SHA

    preflight = memory_preflight(config.campaign.memory_gate_gb)
    manifest = build_manifest(
        config,
        run_id="run-1",
        memory_preflight=preflight,
        input_hashes=inputs,
        integrity={"checked": False, "baseline": None, "non_readme_failures": []},
        capture={
            "python": "3.13",
            "platform": "test",
            "cpu_count": 1,
            "libraries": {},
        },
    )
    assert manifest["design"]["n_seeds"] is None
    assert manifest["memory_preflight"]["gate_gb"] == 4.0
    target = write_manifest(tmp_path / "manifest.json", manifest)
    assert load_manifest(target)["run_id"] == "run-1"
    with pytest.raises(FileExistsError):
        write_manifest(target, manifest)


def test_manifest_rejects_missing_integrity(tmp_path, config):
    manifest = build_manifest(
        config,
        run_id="run-1",
        memory_preflight=memory_preflight(config.campaign.memory_gate_gb),
        input_hashes={"fixture": {"path": "x", "sha256": SHA}},
        capture={
            "python": "3.13",
            "platform": "test",
            "cpu_count": 1,
            "libraries": {},
        },
    )
    manifest.pop("integrity")
    with pytest.raises(SchemaError, match="integrity"):
        validate_manifest(manifest)


def test_missing_frozen_input_is_an_error(tmp_path, config):
    with pytest.raises(FileNotFoundError):
        hash_inputs({**config.campaign.frozen_inputs, "absent": tmp_path / "nope"})


def test_memory_preflight_does_not_weaken_the_gate():
    tiny = memory_preflight(0.001)
    assert tiny["passed"] is True
    impossible = memory_preflight(1_000_000.0)
    assert impossible["passed"] is False
    if tiny["available_gb"] is not None:
        assert tiny["passed"] == (tiny["available_gb"] >= tiny["gate_gb"])
    with pytest.raises(ValueError):
        memory_preflight(0.0)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_declares_every_arm(config):
    registry = build_registry(config.conditions)
    assert registry.conditions == ("A", "B", "C", "D", "E", "F")
    assert registry.controls == ("A_prime", "C_prime", "F_beta", "F_init")
    assert registry.exploratory == ("E_full",)
    assert registry.evaluation_arms[-1] == "floor"
    assert len(registry.arms) == 12
    assert registry.spec("A_prime").exact_match_of == "A"
    assert registry.spec("C_prime").exact_match_of == "C"
    assert registry.spec("F_beta").state_independent is True
    assert registry.spec("F_init").init_only is True
    assert registry.spec("B").eta == 0.5
    assert registry.spec("floor").controller == "constant_no_action"
    assert default_registry().conditions == registry.conditions


def test_confirmatory_family_is_fixed():
    four = confirmatory_contrasts(4)
    assert [(item["id"], item["minuend"], item["subtrahend"]) for item in four] == [
        ("C1", "F", "A"),
        ("C2", "B", "A"),
        ("C3", "A", "C"),
        ("C4", "F", "F_beta"),
    ]
    assert [item["id"] for item in confirmatory_contrasts(3)] == ["C1", "C2", "C3"]
    with pytest.raises(ConfigError):
        confirmatory_contrasts(5)


def test_evaluation_plan_requires_the_pilot_decision(config):
    with pytest.raises(ConfigError):
        evaluation_plan(config)
    selected = replace(
        config, campaign=replace(config.campaign, n_seeds_selected=2)
    )
    plan = evaluation_plan(selected)
    assert len(plan) == 12 * 2 * selected.campaign.episodes_per_seed
    assert plan[0] == ("A", 1, 0)
    assert plan[1] == ("A", 1, 1)
    assert len(set(plan)) == len(plan)
    assert plan[-1][0] == "floor"


# ---------------------------------------------------------------------------
# campaign runner (the harness, not a condition)
# ---------------------------------------------------------------------------

_ARM_ROLES = {
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

_WEIGHTLESS = {"E", "E_full", "floor"}


def passing_gate(gate_gb):
    return {"available_gb": 99.0, "gate_gb": gate_gb, "passed": True, "reason": "test"}


def failing_gate(gate_gb):
    return {"available_gb": 0.5, "gate_gb": gate_gb, "passed": False, "reason": "test"}


def dummy_episode(condition, seed, episode, context):
    digest = None if condition in _WEIGHTLESS else SHA
    return dummy_row(
        condition=condition,
        role=_ARM_ROLES[condition],
        seed=seed,
        episode=episode,
        environment_seed=context["environment_seed"],
        weights_before=digest,
        weights_after=digest,
    )


def selected_config(config, seeds=10):
    return replace(
        config, campaign=replace(config.campaign, n_seeds_selected=seeds)
    )


def test_runner_refuses_below_the_memory_gate(config, tmp_path):
    target = tmp_path / "run-1"
    with pytest.raises(MemoryGateError):
        CampaignRunner.start(
            selected_config(config),
            tmp_path,
            "run-1",
            episode_runner=dummy_episode,
            preflight=failing_gate,
        )
    assert not target.exists()


def test_runner_refuses_an_unresolved_design(config, tmp_path):
    with pytest.raises(ConfigError):
        CampaignRunner.start(
            config,
            tmp_path,
            "run-1",
            episode_runner=dummy_episode,
            preflight=passing_gate,
        )
    assert not (tmp_path / "run-1").exists()


def test_runner_executes_resumes_and_writes_one_manifest(config, tmp_path):
    config = selected_config(config)
    runner = CampaignRunner.start(
        config,
        tmp_path,
        "run-1",
        episode_runner=dummy_episode,
        preflight=passing_gate,
        input_hashes={"fixture": {"path": "x", "sha256": SHA}},
        capture={
            "python": "3.13",
            "platform": "test",
            "cpu_count": 1,
            "libraries": {},
        },
        integrity={"checked": False, "baseline": None, "non_readme_failures": []},
    )
    first = runner.run(limit=1)
    assert first["executed"] == 1
    assert first["stored"] == 1
    assert first["complete"] is False
    assert (tmp_path / "run-1" / "manifest.json").is_file()
    assert (tmp_path / "run-1" / "episodes.jsonl").is_file()

    second = runner.run(limit=1)
    assert second["executed"] == 1
    assert second["stored"] == 2
    assert [row["episode"] for row in runner.store.rows()] == [0, 1]

    resumed = CampaignRunner.resume(
        config, tmp_path / "run-1", episode_runner=dummy_episode, preflight=passing_gate
    )
    assert resumed.run(limit=0)["executed"] == 0
    assert len(resumed.store) == 2
    assert resumed.complete is False
    with pytest.raises(ExistingResultError):
        CampaignRunner.start(
            config,
            tmp_path,
            "run-1",
            episode_runner=dummy_episode,
            preflight=passing_gate,
        )


def test_runner_rejects_a_row_for_another_episode(config, tmp_path):
    config = selected_config(config)

    def wrong_episode(condition, seed, episode, context):
        return dummy_row(condition=condition, role=_ARM_ROLES[condition], seed=seed + 1)

    runner = CampaignRunner.start(
        config,
        tmp_path,
        "run-1",
        episode_runner=wrong_episode,
        preflight=passing_gate,
        input_hashes={"fixture": {"path": "x", "sha256": SHA}},
        capture={
            "python": "3.13",
            "platform": "test",
            "cpu_count": 1,
            "libraries": {},
        },
    )
    with pytest.raises(SchemaError, match="does not identify"):
        runner.run(limit=1)
    assert len(runner.store) == 0


def test_resume_refuses_configuration_drift(config, tmp_path):
    config = selected_config(config)
    CampaignRunner.start(
        config,
        tmp_path,
        "run-1",
        episode_runner=dummy_episode,
        preflight=passing_gate,
        input_hashes={"fixture": {"path": "x", "sha256": SHA}},
        capture={
            "python": "3.13",
            "platform": "test",
            "cpu_count": 1,
            "libraries": {},
        },
    )
    drifted = replace(
        config,
        hashes={
            "environment": {"path": "configs/phase_8/environment.yaml", "sha256": OTHER},
            "campaign": {"path": "configs/phase_8/campaign.yaml", "sha256": SHA},
            "conditions": {"path": "configs/phase_8/conditions.yaml", "sha256": SHA},
        },
    )
    with pytest.raises(StoreError, match="configuration has changed"):
        CampaignRunner.resume(
            drifted,
            tmp_path / "run-1",
            episode_runner=dummy_episode,
            preflight=passing_gate,
        )
