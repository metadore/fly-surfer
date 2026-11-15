"""Phase 5B runner: reward representation, timing, delay and TD prediction.

This script exercises only ``plasticity/reward.py``. It does not import the
simulator, a synapse model, a graph or any motor decoder: reward here is an
external computational scalar, and ``delta_t`` is the prediction error of a
declared value model.

Writes:
  experiments/results/phase_5b/reward_system.json

Usage:
  python -m experiments.phase_5.run_reward
  python -m experiments.phase_5.run_reward --no-write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plasticity.reward import (  # noqa: E402
    REWARD_CLASSIFICATION,
    RewardLogger,
    RewardPrediction,
    ScriptedRewardProvider,
    TabularValuePredictor,
    load_reward_system_config,
    shuffled_reward_schedule,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase_5b"
RESULT_PATH = RESULTS_DIR / "reward_system.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def episode_entries(schedule) -> list[tuple[float, float, str]]:
    """Event magnitude and label ordered by delayed delivery time."""
    entries = [
        (schedule.due_time(event), event.magnitude, event.label)
        for event in schedule.events
    ]
    entries.sort(key=lambda item: item[0])
    return entries


def stage_name(index: int, n_events: int) -> str:
    return "terminal" if index >= n_events else f"stage_{index}"


def analytic_values(entries: list[tuple[float, float, str]], gamma: float) -> dict:
    """V(stage_i) = sum over later events of gamma**(k-i-1) * r_k."""
    values: dict[str, float] = {}
    future = 0.0
    for index in range(len(entries) - 1, -1, -1):
        future = entries[index][1] + gamma * future
        values[f"stage_{index}"] = future
    return values


def run_episode(
    schedule,
    predictor: TabularValuePredictor,
    *,
    dt_ms: float,
    duration_ms: float,
    logger: RewardLogger | None = None,
) -> dict:
    """One deterministic episode over the event chain of ``schedule``.

    A stage transition happens on the step whose time is the first at or after
    an event's delayed delivery time. Several events delivered in the same step
    are merged into one transition with their summed reward.
    """
    entries = episode_entries(schedule)
    n_events = len(entries)
    n_steps = int(round(duration_ms / dt_ms))
    if n_steps < 1:
        raise ValueError("duration_ms must cover at least one step")
    if entries and entries[-1][0] > n_steps * dt_ms + 1e-9:
        raise ValueError("schedule delivers reward after the episode ends")
    provider = ScriptedRewardProvider(schedule)
    stage = 0
    total_reward = 0.0
    deltas: list[float] = []
    deliveries: list[dict] = []

    for step in range(n_steps):
        time_ms = (step + 1) * dt_ms
        reward = provider.step(step, time_ms)
        new_stage = sum(1 for due, _, _ in entries if due <= time_ms + 1e-12)
        previous = stage_name(stage, n_events)
        previous_value = 0.0 if previous == "terminal" else predictor.value(previous)

        if new_stage != stage:
            next_label = (
                None if new_stage >= n_events else stage_name(new_stage, n_events)
            )
            next_value = predictor.next_value(next_label)
            delta = predictor.learn(previous, next_label, reward)
            stage = new_stage
            total_reward += reward
            deliveries.append(
                {
                    "step": step,
                    "time_ms": round(time_ms, 9),
                    "reward": round(float(reward), 9),
                }
            )
            state_label = previous
        else:
            next_label = None if previous == "terminal" else previous
            next_value = previous_value
            delta = 0.0
            state_label = previous

        deltas.append(delta)
        if logger is not None:
            logger.append(
                RewardPrediction(
                    step=step,
                    time_ms=time_ms,
                    reward=reward,
                    value=previous_value,
                    next_value=next_value,
                    prediction_error=delta,
                    state=state_label,
                    next_state=next_label,
                )
            )

    values = {
        f"stage_{index}": predictor.value(f"stage_{index}")
        for index in range(n_events)
    }
    return {
        "n_steps": n_steps,
        "total_reward": round(total_reward, 9),
        "deliveries": deliveries,
        "mean_abs_prediction_error": round(float(np.mean(np.abs(deltas))), 9),
        "final_values": {key: round(value, 9) for key, value in values.items()},
        "values_digest": hashlib.sha256(
            json.dumps(values, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def run_convergence(
    schedule,
    *,
    gamma: float,
    learning_rate: float,
    n_episodes: int,
    dt_ms: float,
    duration_ms: float,
    tolerance: float,
    sample_episodes: tuple[int, ...] = (0, 1, 2, 9, 49, 99, 199),
) -> dict:
    predictor = TabularValuePredictor(gamma=gamma, learning_rate=learning_rate)
    entries = episode_entries(schedule)
    analytic = analytic_values(entries, gamma)
    curve: list[dict] = []
    first_episode: dict | None = None
    for episode in range(n_episodes):
        summary = run_episode(
            schedule, predictor, dt_ms=dt_ms, duration_ms=duration_ms
        )
        if episode == 0:
            first_episode = summary
        if episode in sample_episodes or episode == n_episodes - 1:
            curve.append(
                {"episode": episode + 1, **summary["final_values"]}
            )
    learned = {
        key: predictor.value(key) for key in analytic
    }
    errors = {
        key: learned[key] - analytic[key] for key in analytic
    }
    max_abs_error = max(abs(value) for value in errors.values())
    return {
        "gamma": gamma,
        "learning_rate": learning_rate,
        "n_episodes": n_episodes,
        "analytic_values": {key: round(value, 9) for key, value in analytic.items()},
        "learned_values": {key: round(value, 9) for key, value in learned.items()},
        "errors": {key: round(value, 9) for key, value in errors.items()},
        "max_abs_error": round(max_abs_error, 9),
        "tolerance": tolerance,
        "converged": bool(max_abs_error <= tolerance),
        "first_episode": first_episode,
        "curve": curve,
        "values_digest": hashlib.sha256(
            json.dumps(learned, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def single_episode(schedule, *, dt_ms: float, duration_ms: float) -> dict:
    logger = RewardLogger()
    predictor = TabularValuePredictor(gamma=0.9, learning_rate=0.2)
    summary = run_episode(
        schedule,
        predictor,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        logger=logger,
    )
    log = logger.to_dict()
    head = log.pop("records")
    rewards = [item.reward for item in logger.records]
    return {
        "summary": summary,
        "log_summary": log,
        "log_digest": logger.digest(),
        "n_positive_steps": int(sum(1 for value in rewards if value > 0)),
        "n_negative_steps": int(sum(1 for value in rewards if value < 0)),
        "n_nonzero_steps": int(sum(1 for value in rewards if value != 0)),
        "records_head": head[:5],
    }


def stability_probes() -> dict:
    probes: dict = {}

    bounded = TabularValuePredictor(gamma=0.9, learning_rate=1.0, value_bound=10.0)
    delta = bounded.learn("s", None, 1.0e6)
    probes["bounded_large_reward"] = {
        "delta": delta,
        "value": bounded.value("s"),
        "finite": math.isfinite(bounded.value("s")),
        "within_bound": abs(bounded.value("s")) <= 10.0,
    }

    zero = TabularValuePredictor(gamma=0.9, learning_rate=1.0)
    zero.learn("x", "y", 0.0)
    zero.learn("y", None, 0.0)
    probes["zero_reward"] = {
        "value_x": zero.value("x"),
        "value_y": zero.value("y"),
        "all_zero": zero.value("x") == 0.0 and zero.value("y") == 0.0,
    }

    negative = TabularValuePredictor(gamma=0.0, learning_rate=1.0)
    negative.learn("s", None, -2.0)
    probes["negative_reward"] = {
        "value": negative.value("s"),
        "sign_preserved": negative.value("s") < 0.0,
    }

    cases = {}
    for label, reward in (("nan", float("nan")), ("inf", float("inf"))):
        predictor = TabularValuePredictor()
        try:
            predictor.learn("s", None, reward)
        except ValueError:
            cases[label] = "rejected"
        else:
            cases[label] = "accepted"
    probes["non_finite_reward"] = cases

    overflow = TabularValuePredictor(
        gamma=1.0, learning_rate=1.0, value_bound=1.7e308
    )
    overflow.learn("t", None, 5.0e307)
    try:
        overflow.learn("s", "t", 1.5e308)
    except FloatingPointError:
        overflow_result = "rejected"
    else:
        overflow_result = "accepted"
    probes["overflow_guard"] = {
        "result": overflow_result,
        "value_finite": math.isfinite(overflow.value("s")),
        "delta_finite": math.isfinite(overflow.value("t")),
    }
    return probes


def shuffled_control(schedule, *, seed: int) -> dict:
    shuffled = shuffled_reward_schedule(schedule, seed=seed)
    original_magnitudes = sorted(event.magnitude for event in schedule.events)
    shuffled_magnitudes = sorted(event.magnitude for event in shuffled.events)
    original_times = [event.time_ms for event in schedule.events]
    shuffled_times = [event.time_ms for event in shuffled.events]
    return {
        "seed": seed,
        "original_digest": schedule.digest(),
        "shuffled_digest": shuffled.digest(),
        "digest_changed": schedule.digest() != shuffled.digest(),
        "magnitudes_preserved": original_magnitudes == shuffled_magnitudes,
        "times_preserved": original_times == shuffled_times,
        "total_preserved": schedule.total() == shuffled.total(),
        "describe": shuffled.describe(),
    }


def build_result() -> dict:
    started = time.perf_counter()
    tracemalloc.start()
    config = load_reward_system_config(CONFIG_PATH)
    demo = config.raw.get("demonstration", {})
    convergence_cfg = config.raw.get("convergence", {})
    if not isinstance(demo, dict) or not isinstance(convergence_cfg, dict):
        raise ValueError("demonstration and convergence must be mappings")
    dt_ms = float(demo.get("dt_ms", 0.5))
    duration_ms = float(demo.get("episode_duration_ms", 500.0))
    if not config.reward.schedules:
        raise ValueError("no reward schedules declared")

    schedules = config.reward.describe()
    sign_checks: dict = {}
    for name in ("positive_single", "negative_single", "zero_reward"):
        schedule = config.reward.schedule(name)
        sign_checks[name] = {
            "total": schedule.total(),
            "counts": schedule.counts(),
            "sign_expected": (
                "positive"
                if name == "positive_single"
                else "negative"
                if name == "negative_single"
                else "zero"
            ),
        }

    mixed = config.reward.schedule(str(demo.get("schedule", "mixed")))
    delayed = config.reward.schedule(str(demo.get("delayed_schedule", "delayed_mixed")))
    immediate_episode = single_episode(mixed, dt_ms=dt_ms, duration_ms=duration_ms)
    delayed_episode = single_episode(delayed, dt_ms=dt_ms, duration_ms=duration_ms)

    expected_times = [round(due, 9) for due, _, _ in episode_entries(mixed)]
    delivered_times = [item["time_ms"] for item in immediate_episode["summary"]["deliveries"]]
    delayed_expected = [round(due, 9) for due, _, _ in episode_entries(delayed)]
    delayed_delivered = [item["time_ms"] for item in delayed_episode["summary"]["deliveries"]]

    n_episodes = int(convergence_cfg.get("n_episodes", 400))
    tolerance = float(convergence_cfg.get("tolerance", 0.001))
    schedule_name = str(convergence_cfg.get("schedule", "mixed"))
    convergence_schedule = config.reward.schedule(schedule_name)
    gamma_grid = [float(value) for value in config.raw["predictor"].get("gamma_grid", [])]
    if not gamma_grid:
        raise ValueError("predictor.gamma_grid must not be empty")

    convergence = [
        run_convergence(
            convergence_schedule,
            gamma=gamma,
            learning_rate=config.predictor.learning_rate,
            n_episodes=n_episodes,
            dt_ms=dt_ms,
            duration_ms=duration_ms,
            tolerance=tolerance,
        )
        for gamma in gamma_grid
    ]

    delayed_convergence = run_convergence(
        delayed,
        gamma=config.predictor.gamma,
        learning_rate=config.predictor.learning_rate,
        n_episodes=n_episodes,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        tolerance=tolerance,
    )
    immediate_convergence = run_convergence(
        mixed,
        gamma=config.predictor.gamma,
        learning_rate=config.predictor.learning_rate,
        n_episodes=n_episodes,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        tolerance=tolerance,
    )

    repeat = run_convergence(
        convergence_schedule,
        gamma=config.predictor.gamma,
        learning_rate=config.predictor.learning_rate,
        n_episodes=n_episodes,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        tolerance=tolerance,
    )
    determinism = {
        "first_digest": immediate_convergence["values_digest"],
        "repeat_digest": repeat["values_digest"],
        "identical": immediate_convergence["values_digest"]
        == repeat["values_digest"],
        "episode_log_digest": immediate_episode["log_digest"],
        "episode_log_digest_repeat": single_episode(
            mixed, dt_ms=dt_ms, duration_ms=duration_ms
        )["log_digest"],
    }
    determinism["episode_log_identical"] = (
        determinism["episode_log_digest"] == determinism["episode_log_digest_repeat"]
    )

    delay_shift_ms = delayed.delay_ms - mixed.delay_ms
    delay_steps = int(round(delay_shift_ms / dt_ms))
    delay_check = {
        "delay_ms": delayed.delay_ms,
        "expected_delivery_times_ms": delayed_expected,
        "observed_delivery_times_ms": delayed_delivered,
        "times_match": delayed_delivered == delayed_expected,
        "first_delivery_ahead_by_steps": (
            delayed_episode["summary"]["deliveries"][0]["step"]
            - immediate_episode["summary"]["deliveries"][0]["step"]
        ),
        "expected_shift_steps": delay_steps,
        "shift_matches": (
            delayed_episode["summary"]["deliveries"][0]["step"]
            - immediate_episode["summary"]["deliveries"][0]["step"]
            == delay_steps
        ),
        "total_preserved": (
            delayed_episode["summary"]["total_reward"]
            == immediate_episode["summary"]["total_reward"]
        ),
        "terminal_values_equal": all(
            abs(
                immediate_convergence["learned_values"][stage]
                - delayed_convergence["learned_values"][stage]
            )
            <= 1e-12
            for stage in immediate_convergence["learned_values"]
        ),
    }

    shuffled = shuffled_control(mixed, seed=int(demo.get("shuffle_seed", 20261110)))
    probes = stability_probes()

    runtime_s = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    checks = {
        "reward_signs": all(
            (item["total"] > 0 and item["sign_expected"] == "positive")
            or (item["total"] < 0 and item["sign_expected"] == "negative")
            or (item["total"] == 0 and item["sign_expected"] == "zero")
            for item in sign_checks.values()
        ),
        "reward_timing": delivered_times == expected_times,
        "single_emission": (
            immediate_episode["n_nonzero_steps"]
            == len(immediate_episode["summary"]["deliveries"])
        ),
        "delayed_reward": bool(
            delay_check["times_match"]
            and delay_check["shift_matches"]
            and delay_check["total_preserved"]
            and delay_check["terminal_values_equal"]
        ),
        "predictor_convergence": all(item["converged"] for item in convergence),
        "numerical_stability": bool(
            probes["bounded_large_reward"]["finite"]
            and probes["bounded_large_reward"]["within_bound"]
            and probes["zero_reward"]["all_zero"]
            and probes["negative_reward"]["sign_preserved"]
            and all(value == "rejected" for value in probes["non_finite_reward"].values())
            and probes["overflow_guard"]["result"] == "rejected"
        ),
        "determinism": bool(
            determinism["identical"] and determinism["episode_log_identical"]
        ),
        "logging": bool(
            immediate_episode["log_summary"]["n_steps"]
            == immediate_episode["summary"]["n_steps"]
            and immediate_episode["log_summary"]["total_reward"]
            == immediate_episode["summary"]["total_reward"]
        ),
        "shuffled_control": bool(
            shuffled["magnitudes_preserved"]
            and shuffled["times_preserved"]
            and shuffled["total_preserved"]
        ),
    }

    return {
        "phase": "5B",
        "title": "Reward signal and reward prediction error",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": "FLY-SURFER",
        "config": {
            "path": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(CONFIG_PATH),
            "reward": schedules,
            "predictor": config.predictor.describe(),
            "gamma_grid": gamma_grid,
            "convergence": {
                "schedule": schedule_name,
                "n_episodes": n_episodes,
                "tolerance": tolerance,
            },
            "demonstration": {
                "dt_ms": dt_ms,
                "episode_duration_ms": duration_ms,
                "schedule": demo.get("schedule", "mixed"),
                "delayed_schedule": demo.get("delayed_schedule", "delayed_mixed"),
                "shuffle_seed": demo.get("shuffle_seed", 20261110),
            },
        },
        "classification": REWARD_CLASSIFICATION,
        "sign_checks": sign_checks,
        "episode": {
            "schedule": demo.get("schedule", "mixed"),
            "expected_times_ms": expected_times,
            "immediate": immediate_episode,
            "delayed": delayed_episode,
        },
        "delay_check": delay_check,
        "convergence": convergence,
        "delayed_convergence": {
            "gamma": delayed_convergence["gamma"],
            "max_abs_error": delayed_convergence["max_abs_error"],
            "converged": delayed_convergence["converged"],
            "learned_values": delayed_convergence["learned_values"],
            "immediate_learned_values": immediate_convergence["learned_values"],
        },
        "shuffled_control": shuffled,
        "stability_probes": probes,
        "determinism": determinism,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "resources": {
            "runtime_s": round(runtime_s, 4),
            "peak_tracemalloc_bytes": int(peak_bytes),
            "peak_tracemalloc_mb": round(peak_bytes / (1024 * 1024), 3),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "limitations": [
            "Reward is a computational task scalar, not a measured neuromodulator.",
            "The tabular predictor is one declared model of value, not a biological reward prediction signal.",
            "A converged predictor demonstrates arithmetic and temporal credit assignment in this model only.",
            "No synapse, weight, trace or simulator state is touched by this runner.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = build_result()
    print(json.dumps({key: result[key] for key in ("checks", "all_checks_passed", "resources")}, indent=1))
    if not args.no_write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {RESULT_PATH}")
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
