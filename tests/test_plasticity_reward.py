"""Phase 5B: reward representation, delay and temporal-difference prediction."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

import plasticity
from experiments.phase_5 import run_reward
from plasticity.reward import (
    REWARD_CLASSIFICATION,
    RewardEvent,
    RewardLogger,
    RewardPrediction,
    RewardSchedule,
    ScriptedRewardProvider,
    TabularValuePredictor,
    load_reward_system_config,
    reward_statistics,
    shuffled_reward_schedule,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"
MIXED_EVENTS = [(80.0, 1.0, "correct"), (160.0, -1.0, "collision"), (240.0, 0.5, "partial")]


def mixed_schedule(delay_ms: float = 0.0) -> RewardSchedule:
    return RewardSchedule(MIXED_EVENTS, delay_ms=delay_ms)


def prediction(step: int, reward: float, pe: float = 0.0) -> RewardPrediction:
    return RewardPrediction(
        step=step,
        time_ms=(step + 1) * 0.5,
        reward=reward,
        value=0.0,
        next_value=0.0,
        prediction_error=pe,
        state="stage_0",
        next_state="stage_1",
    )


# -- reward events and schedules -------------------------------------------


def test_reward_event_validates_fields():
    with pytest.raises(ValueError):
        RewardEvent(-1.0, 1.0)
    with pytest.raises(ValueError):
        RewardEvent(1.0, float("nan"))
    with pytest.raises(ValueError):
        RewardEvent(1.0, float("inf"))
    with pytest.raises(ValueError):
        RewardEvent(1.0, 1.0, label=3)  # type: ignore[arg-type]


def test_reward_event_accepts_zero_time_and_zero_magnitude():
    event = RewardEvent(0.0, 0.0, "neutral")
    assert event.as_dict() == {"time_ms": 0.0, "magnitude": 0.0, "label": "neutral"}


def test_schedule_sorts_events_and_reports_counts():
    schedule = RewardSchedule(
        [(240.0, 0.5, "partial"), (80.0, 1.0, "correct"), (160.0, -1.0, "collision")]
    )
    assert [event.time_ms for event in schedule.events] == [80.0, 160.0, 240.0]
    assert schedule.total() == pytest.approx(0.5)
    assert schedule.counts() == {"positive": 2, "negative": 1, "zero": 0}
    assert schedule.describe()["classification"] == REWARD_CLASSIFICATION
    assert schedule.describe()["n_events"] == 3


def test_schedule_accepts_event_objects_and_rejects_bad_entries():
    schedule = RewardSchedule([RewardEvent(10.0, 2.0, "a")])
    assert schedule.total() == 2.0
    with pytest.raises(ValueError):
        RewardSchedule([(1.0,)])
    with pytest.raises(ValueError):
        RewardSchedule([42])


def test_schedule_delay_shifts_delivery_time_only():
    schedule = mixed_schedule(delay_ms=50.0)
    assert [schedule.due_time(event) for event in schedule.events] == [130.0, 210.0, 290.0]
    assert schedule.total() == 0.5
    assert schedule.delay_ms == 50.0


def test_due_between_uses_half_open_interval():
    schedule = mixed_schedule()
    assert schedule.due_between(-math.inf, 80.0) == 1.0
    assert schedule.due_between(79.5, 80.0) == 1.0
    assert schedule.due_between(80.0, 80.5) == 0.0
    assert schedule.due_between(80.0, 160.0) == -1.0
    assert schedule.due_between(-math.inf, math.inf) == pytest.approx(0.5)


def test_schedule_digest_is_deterministic_and_content_sensitive():
    first = mixed_schedule()
    second = mixed_schedule()
    assert first.digest() == second.digest()
    assert first.digest() != mixed_schedule(delay_ms=50.0).digest()
    assert first.digest() != RewardSchedule([(80.0, 1.0, "correct")]).digest()


def test_schedule_rejects_negative_delay():
    with pytest.raises(ValueError):
        RewardSchedule([(1.0, 1.0)], delay_ms=-0.5)


# -- reward provider --------------------------------------------------------


def test_provider_emits_each_event_once_at_its_due_step():
    schedule = mixed_schedule()
    provider = ScriptedRewardProvider(schedule)
    emitted = [provider.step(step, (step + 1) * 0.5) for step in range(600)]
    nonzero = [(index, value) for index, value in enumerate(emitted) if value != 0.0]
    assert nonzero == [(159, 1.0), (319, -1.0), (479, 0.5)]
    assert provider.emitted_reward == pytest.approx(0.5)


def test_provider_delivers_event_at_time_zero_on_first_step():
    provider = ScriptedRewardProvider(RewardSchedule([(0.0, 3.0)]))
    assert provider.step(0, 0.5) == 3.0
    assert provider.step(1, 1.0) == 0.0


def test_provider_delays_delivery_and_reset_replays():
    provider = ScriptedRewardProvider(RewardSchedule([(10.0, 2.0)], delay_ms=5.0))
    assert provider.step(0, 10.0) == 0.0
    assert provider.step(1, 15.0) == 2.0
    assert provider.emitted_reward == 2.0
    provider.reset()
    assert provider.emitted_reward == 0.0
    assert provider.step(0, 15.0) == 2.0


def test_provider_rejects_time_that_goes_backwards():
    provider = ScriptedRewardProvider(mixed_schedule())
    provider.step(0, 10.0)
    with pytest.raises(ValueError):
        provider.step(1, 9.5)


def test_provider_rejects_non_finite_time():
    provider = ScriptedRewardProvider(mixed_schedule())
    with pytest.raises(ValueError):
        provider.step(0, float("nan"))


def test_provider_requires_a_schedule():
    with pytest.raises(ValueError):
        ScriptedRewardProvider([(1.0, 1.0)])  # type: ignore[arg-type]


# -- predictor and reward prediction error ---------------------------------


def test_prediction_error_matches_the_declared_formula():
    predictor = TabularValuePredictor(gamma=0.9)
    predictor.load_state_dict({"s": 0.5, "n": 2.0})
    delta = predictor.prediction_error("s", "n", 1.0)
    assert delta == pytest.approx(1.0 + 0.9 * 2.0 - 0.5, abs=1e-12)


def test_terminal_transition_has_zero_future_value():
    predictor = TabularValuePredictor(gamma=0.99)
    predictor.load_state_dict({"s": 0.75})
    assert predictor.next_value(None) == 0.0
    assert predictor.prediction_error("s", None, 0.0) == pytest.approx(-0.75)


def test_learn_applies_learning_rate_and_returns_delta():
    predictor = TabularValuePredictor(gamma=0.9, learning_rate=0.5)
    delta = predictor.learn("s", None, 1.0)
    assert delta == pytest.approx(1.0)
    assert predictor.value("s") == pytest.approx(0.5)


def test_zero_learning_rate_leaves_values_unchanged_but_reports_error():
    predictor = TabularValuePredictor(learning_rate=0.0)
    delta = predictor.learn("s", None, -3.0)
    assert delta == pytest.approx(-3.0)
    assert predictor.value("s") == 0.0


def test_positive_negative_and_zero_reward_keep_their_sign():
    predictor = TabularValuePredictor(gamma=0.0, learning_rate=1.0)
    predictor.learn("pos", None, 2.0)
    predictor.learn("neg", None, -2.0)
    predictor.learn("zero", None, 0.0)
    assert predictor.value("pos") == pytest.approx(2.0)
    assert predictor.value("neg") == pytest.approx(-2.0)
    assert predictor.value("zero") == 0.0


def test_values_are_clipped_to_the_declared_bound():
    predictor = TabularValuePredictor(learning_rate=1.0, value_bound=1.0)
    predictor.learn("s", None, 5.0)
    assert predictor.value("s") == 1.0
    predictor.learn("t", None, -5.0)
    assert predictor.value("t") == -1.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"gamma": -0.1},
        {"gamma": 1.1},
        {"learning_rate": -0.1},
        {"learning_rate": 1.1},
        {"value_bound": 0.0},
        {"value_bound": -1.0},
        {"gamma": float("nan")},
    ],
)
def test_predictor_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        TabularValuePredictor(**kwargs)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "1.0", True])
def test_learn_rejects_non_numeric_or_non_finite_reward(value):
    predictor = TabularValuePredictor()
    with pytest.raises(ValueError):
        predictor.learn("s", None, value)


def test_predictor_rejects_unsupported_state_keys():
    predictor = TabularValuePredictor()
    with pytest.raises(ValueError):
        predictor.value({"x": 1})
    with pytest.raises(ValueError):
        predictor.value(True)
    predictor.learn(("cue", 3), None, 1.0)
    assert predictor.value("cue|3") == pytest.approx(0.2)


def test_state_round_trip_and_digest():
    predictor = TabularValuePredictor(gamma=0.5, learning_rate=0.5)
    predictor.learn("a", None, 1.0)
    predictor.learn("b", None, -1.0)
    state = predictor.state_dict()
    assert set(state) == {"a", "b"}
    clone = TabularValuePredictor(gamma=0.5, learning_rate=0.5)
    clone.load_state_dict(state)
    assert clone.state_dict() == state
    assert clone.digest() == predictor.digest()
    clone.learn("a", None, 1.0)
    assert clone.digest() != predictor.digest()


def test_load_state_dict_rejects_bad_keys_and_out_of_bound_values():
    predictor = TabularValuePredictor(value_bound=1.0)
    with pytest.raises(ValueError):
        predictor.load_state_dict({"": 0.5})
    with pytest.raises(ValueError):
        predictor.load_state_dict({1: 0.5})  # type: ignore[dict-item]
    with pytest.raises(ValueError):
        predictor.load_state_dict({"a": 2.0})
    with pytest.raises(ValueError):
        predictor.load_state_dict({"a": float("nan")})


def test_predictor_describe_declares_model_status():
    predictor = TabularValuePredictor(gamma=0.9)
    described = predictor.describe()
    assert described["model"] == "tabular_temporal_difference"
    assert "not a measured" in described["classification"]
    assert predictor.n_states == 0


# -- convergence and chain semantics ---------------------------------------


def test_analytic_values_match_hand_computation():
    entries = run_reward.episode_entries(mixed_schedule())
    values = run_reward.analytic_values(entries, 0.9)
    assert values["stage_2"] == pytest.approx(0.5)
    assert values["stage_1"] == pytest.approx(-1.0 + 0.9 * 0.5)
    assert values["stage_0"] == pytest.approx(1.0 + 0.9 * (-0.55))


def test_episode_delivers_reward_at_declared_times_and_totals():
    predictor = TabularValuePredictor(gamma=0.9, learning_rate=0.2)
    summary = run_reward.run_episode(
        mixed_schedule(), predictor, dt_ms=0.5, duration_ms=300.0
    )
    assert [item["time_ms"] for item in summary["deliveries"]] == [80.0, 160.0, 240.0]
    assert [item["reward"] for item in summary["deliveries"]] == [1.0, -1.0, 0.5]
    assert summary["total_reward"] == pytest.approx(0.5)
    assert summary["n_steps"] == 600


def test_episode_rejects_reward_beyond_the_episode_end():
    predictor = TabularValuePredictor()
    with pytest.raises(ValueError):
        run_reward.run_episode(
            mixed_schedule(), predictor, dt_ms=0.5, duration_ms=100.0
        )


def test_predictor_converges_to_analytic_values():
    result = run_reward.run_convergence(
        mixed_schedule(),
        gamma=0.9,
        learning_rate=0.2,
        n_episodes=300,
        dt_ms=1.0,
        duration_ms=300.0,
        tolerance=1e-3,
    )
    assert result["converged"] is True
    assert result["max_abs_error"] <= 1e-3
    assert result["learned_values"]["stage_0"] == pytest.approx(0.505, abs=1e-3)


def test_myopic_predictor_converges_to_immediate_rewards():
    result = run_reward.run_convergence(
        mixed_schedule(),
        gamma=0.0,
        learning_rate=0.2,
        n_episodes=200,
        dt_ms=1.0,
        duration_ms=300.0,
        tolerance=1e-3,
    )
    assert result["converged"] is True
    assert result["learned_values"] == {
        "stage_0": pytest.approx(1.0),
        "stage_1": pytest.approx(-1.0),
        "stage_2": pytest.approx(0.5),
    }


def test_delayed_reward_shifts_timing_but_not_value():
    immediate = run_reward.run_convergence(
        mixed_schedule(),
        gamma=0.9,
        learning_rate=0.2,
        n_episodes=300,
        dt_ms=1.0,
        duration_ms=300.0,
        tolerance=1e-3,
    )
    delayed_schedule = mixed_schedule(delay_ms=50.0)
    delayed = run_reward.run_convergence(
        delayed_schedule,
        gamma=0.9,
        learning_rate=0.2,
        n_episodes=300,
        dt_ms=1.0,
        duration_ms=300.0,
        tolerance=1e-3,
    )
    assert delayed["converged"] is True
    for stage, value in immediate["learned_values"].items():
        assert delayed["learned_values"][stage] == pytest.approx(value, abs=1e-12)
    first = run_reward.run_episode(
        delayed_schedule,
        TabularValuePredictor(gamma=0.9),
        dt_ms=0.5,
        duration_ms=300.0,
    )
    assert first["deliveries"][0]["time_ms"] == 130.0
    assert first["deliveries"][0]["step"] == 259


def test_episode_is_deterministic():
    schedule = mixed_schedule()
    first = run_reward.run_episode(
        schedule, TabularValuePredictor(gamma=0.9), dt_ms=0.5, duration_ms=300.0
    )
    second = run_reward.run_episode(
        schedule, TabularValuePredictor(gamma=0.9), dt_ms=0.5, duration_ms=300.0
    )
    assert first == second


def test_logger_records_every_step_and_summarises_rewards():
    logger = RewardLogger()
    summary = run_reward.run_episode(
        mixed_schedule(),
        TabularValuePredictor(gamma=0.9),
        dt_ms=0.5,
        duration_ms=300.0,
        logger=logger,
    )
    log = logger.to_dict()
    assert log["n_steps"] == summary["n_steps"] == 600
    assert log["total_reward"] == pytest.approx(0.5)
    assert log["positive_steps"] == 2
    assert log["negative_steps"] == 1
    assert log["zero_steps"] == 597
    assert len(log["records"]) == 600
    assert log["records"][0]["time_ms"] == 0.5
    assert log["records"][-1]["time_ms"] == 300.0


def test_logger_digest_depends_on_record_order():
    first = RewardLogger()
    second = RewardLogger()
    first.append(prediction(0, 1.0, 1.0))
    first.append(prediction(1, 0.0, 0.0))
    second.append(prediction(1, 0.0, 0.0))
    second.append(prediction(0, 1.0, 1.0))
    assert first.digest() != second.digest()


def test_logger_rejects_non_prediction_records():
    logger = RewardLogger()
    with pytest.raises(ValueError):
        logger.append({"reward": 1.0})  # type: ignore[arg-type]


def test_empty_logger_summary_is_zero():
    logger = RewardLogger()
    summary = logger.to_dict()
    assert summary["n_steps"] == 0
    assert summary["total_reward"] == 0.0
    assert summary["max_abs_prediction_error"] == 0.0
    assert summary["records"] == []


# -- statistics and controls -----------------------------------------------


def test_reward_statistics_matches_schedule():
    stats = reward_statistics(mixed_schedule().events)
    assert stats.as_dict() == {
        "n_events": 3,
        "total": 0.5,
        "positive": 2,
        "negative": 1,
        "zero": 0,
        "first_time_ms": 80.0,
        "last_time_ms": 240.0,
    }
    assert reward_statistics([]).first_time_ms is None


def test_shuffled_schedule_preserves_magnitudes_times_and_total():
    original = mixed_schedule()
    shuffled = shuffled_reward_schedule(original, seed=20261111)
    assert [event.time_ms for event in shuffled.events] == [
        event.time_ms for event in original.events
    ]
    assert sorted(event.magnitude for event in shuffled.events) == sorted(
        event.magnitude for event in original.events
    )
    assert shuffled.total() == original.total()
    assert shuffled.digest() != original.digest()
    shuffled_again = shuffled_reward_schedule(original, seed=20261111)
    assert shuffled.digest() == shuffled_again.digest()
    with pytest.raises(ValueError):
        shuffled_reward_schedule(original.events, seed=1)  # type: ignore[arg-type]


def test_shuffled_schedule_is_identity_for_single_event():
    original = RewardSchedule([(10.0, 2.0, "only")])
    shuffled = shuffled_reward_schedule(original, seed=3)
    assert shuffled.events[0].magnitude == 2.0


# -- numerical stability ----------------------------------------------------


def test_large_reward_stays_finite_and_bounded():
    predictor = TabularValuePredictor(gamma=0.9, learning_rate=1.0, value_bound=10.0)
    delta = predictor.learn("s", None, 1.0e6)
    assert math.isfinite(delta)
    assert predictor.value("s") == 10.0


def test_repeated_tiny_rewards_stay_finite_and_converge():
    predictor = TabularValuePredictor(gamma=0.0, learning_rate=0.5)
    for _ in range(10_000):
        predictor.learn("s", None, 1e-9)
    assert predictor.value("s") == pytest.approx(1e-9, rel=1e-6)
    assert math.isfinite(predictor.value("s"))


def test_overflow_in_the_value_update_is_rejected():
    predictor = TabularValuePredictor(gamma=1.0, learning_rate=1.0, value_bound=1.7e308)
    predictor.learn("next", None, 5.0e307)
    with pytest.raises(FloatingPointError):
        predictor.learn("s", "next", 1.5e308)
    assert math.isfinite(predictor.value("s"))


# -- configuration ----------------------------------------------------------


def test_config_declares_all_schedules_and_predictor():
    config = load_reward_system_config(CONFIG_PATH)
    assert set(config.reward.schedules) == {
        "positive_single",
        "negative_single",
        "zero_reward",
        "mixed",
        "delayed_mixed",
    }
    assert config.reward.delay_ms == 0.0
    assert config.reward.schedule("mixed").total() == pytest.approx(0.5)
    assert config.reward.schedule("delayed_mixed").delay_ms == 50.0
    predictor = config.predictor
    assert predictor.gamma == pytest.approx(0.9)
    assert predictor.learning_rate == pytest.approx(0.2)
    assert predictor.value_bound == pytest.approx(100.0)
    assert config.raw["predictor"]["gamma_grid"] == [0.0, 0.5, 0.9, 0.99]
    assert config.describe()["reward"]["classification"] == REWARD_CLASSIFICATION


def test_config_matches_the_declared_demo_schedule():
    config = load_reward_system_config(CONFIG_PATH)
    assert config.raw["demonstration"]["schedule"] == "mixed"
    assert config.raw["demonstration"]["delayed_schedule"] == "delayed_mixed"
    assert config.raw["convergence"]["schedule"] == "mixed"


def _write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _base_config() -> dict:
    return {
        "reward": {
            "schedules": {"s": {"events": [[1.0, 1.0, "a"]]}},
        },
        "predictor": {"defaults": {"gamma": 0.5}},
    }


def test_config_rejects_schedule_without_events(tmp_path):
    payload = _base_config()
    payload["reward"]["schedules"]["s"]["events"] = []
    with pytest.raises(ValueError):
        load_reward_system_config(_write_config(tmp_path, payload))


def test_config_rejects_empty_schedule_map(tmp_path):
    payload = _base_config()
    payload["reward"]["schedules"] = {}
    with pytest.raises(ValueError):
        load_reward_system_config(_write_config(tmp_path, payload))


def test_config_rejects_invalid_gamma(tmp_path):
    payload = _base_config()
    payload["predictor"]["defaults"]["gamma"] = 1.5
    with pytest.raises(ValueError):
        load_reward_system_config(_write_config(tmp_path, payload))


def test_config_rejects_missing_reward_section(tmp_path):
    with pytest.raises(ValueError):
        load_reward_system_config(
            _write_config(tmp_path, {"predictor": {"defaults": {}}})
        )


# -- independence from the plasticity engine and simulator -----------------


def test_reward_module_does_not_import_brain_graph_or_motor():
    source = Path(plasticity.reward.__file__).read_text(encoding="utf-8")
    imports = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    assert not any(
        token in line for line in imports for token in ("brain", "motor", "banc", "experiments")
    )


def test_package_does_not_import_simulator_or_brain():
    source = Path(plasticity.__file__).read_text(encoding="utf-8")
    assert "from .reward import" in source
    assert "brain." not in source
    assert "motor." not in source
    assert "plastic_simulator" not in source


def test_runner_episode_does_not_touch_simulator_state():
    predictor = TabularValuePredictor(gamma=0.9)
    before = predictor.state_dict()
    summary = run_reward.run_episode(
        mixed_schedule(), predictor, dt_ms=0.5, duration_ms=300.0
    )
    assert before == {}
    assert summary["n_steps"] == 600
    assert predictor.n_states == 3
