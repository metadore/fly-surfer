"""Phase 5E controlled learning experiments on a synthetic cued-response task.

SCIENTIFIC STATUS
    Every number produced here is a model output. Success on this task is not
    evidence of learning in a fly, not a biological experiment and not a
    measurement of any synaptic process. A reward is an external task scalar.
    The declared cue -> action mapping is arbitrary and was fixed before the
    experiment.

Protocol (declared in ``configs/plasticity_task.yaml``)
    Each episode stimulates one of four cue populations. Cue onsets are
    jittered per trial and per neuron. The four action populations receive a
    sub-rheobase priming current and then a constant holding current. An episode
    is successful when the designated action population spikes at or before the
    13.5 ms deadline. The reward (+1) is returned at that spike step; a miss
    returns the declared miss reward (0). Because the eligibility trace is
    delay-matched, only cue packets delivered in the same step as the response
    are tagged, so the update is selective in time.

Conditions (identical episode budget and seeds across conditions)
    A  fixed weights, outcome reward (eta = 0, traces on)
    B  plastic weights, outcome reward
    C  plastic weights, zero reward
    D  plastic weights, sign-shuffled reward
    E  plastic weights, random cue -> action connectivity
    F  plastic weights, traces disabled
    G  conventional perceptron baseline (supervised label; privileged baseline)

Train and evaluation seed pools are derived from separate SeedSequence streams
before any experiment runs and are verified disjoint. Evaluation is performed
with eta = 0 on the current learned state, at checkpoints fixed in the config,
using the same evaluation episodes at every checkpoint.

Usage:
  python -m experiments.phase_5.controlled_task
  python -m experiments.phase_5.controlled_task --quick
  python -m experiments.phase_5.controlled_task --conditions A,B
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_simulator import BancSimulator  # noqa: E402
from experiments.phase_4h.common import (  # noqa: E402
    integrity_snapshot,
    process_memory,
    software_versions,
)
from plasticity.checkpoint import (  # noqa: E402
    load_checkpoint,
    save_checkpoint,
)
from plasticity.config import load_plasticity_config  # noqa: E402
from plasticity.diagnostics import spike_hash  # noqa: E402
from plasticity.plastic_simulator import PlasticSimulator  # noqa: E402
from plasticity.rules import RuleConfig, ThreeFactorRule  # noqa: E402
from plasticity.tasks import (  # noqa: E402
    CueActionSchedule,
    DelayedReward,
    TargetResponseController,
    build_task_substrate,
    derive_seed,
    load_task_config,
)
from plasticity.weights import WeightBounds, WeightState  # noqa: E402

TASK_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity_task.yaml"
PLASTICITY_CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase_5e"
FIGURES_DIR = RESULTS_DIR / "figures"
CHECKPOINTS_DIR = RESULTS_DIR / "checkpoints"

CONDITIONS = ("A", "B", "C", "D", "E", "F", "G")
CONDITION_LABELS = {
    "A": "fixed_weights_outcome_reward",
    "B": "plastic_outcome_reward",
    "C": "plastic_zero_reward",
    "D": "plastic_shuffled_reward",
    "E": "plastic_random_connectivity",
    "F": "plastic_traces_disabled",
    "G": "conventional_perceptron",
}
# Independent SeedSequence stream codes. Train and evaluation pools never share
# a code, which is what makes the two pools separately derived and auditable.
STREAM_TRAIN_SIM = 1001
STREAM_EVAL_SIM = 2001
STREAM_TRAIN_JITTER = 3001
STREAM_EVAL_JITTER = 4001
STREAM_REWARD_SHUFFLE = 5001


# ---------------------------------------------------------------------------
# small JSON / statistics helpers
# ---------------------------------------------------------------------------


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=1, allow_nan=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def mean_sd(values) -> dict:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    return {
        "n": int(array.size),
        "mean": round(float(array.mean()), 6),
        "sd": round(float(array.std(ddof=1)), 6) if array.size > 1 else 0.0,
        "median": round(float(np.median(array)), 6),
        "min": round(float(array.min()), 6),
        "max": round(float(array.max()), 6),
    }


def block_success(records, window: int) -> list[dict]:
    blocks = []
    for start in range(0, len(records) - window + 1, window):
        chunk = records[start : start + window]
        blocks.append(
            {
                "start": int(start),
                "end": int(start + window),
                "success": round(float(np.mean([r["hit"] for r in chunk])), 6),
                "selective": round(
                    float(np.mean([r["selective"] for r in chunk])), 6
                ),
                "mean_response_ms": _mean_hit_latency(chunk),
            }
        )
    return blocks


def _mean_hit_latency(records) -> float | None:
    latencies = [
        r["response_ms"] for r in records if r["response_ms"] is not None
    ]
    return round(float(np.mean(latencies)), 6) if latencies else None


def episodes_to_criterion(blocks, threshold: float) -> int | None:
    for block in blocks:
        if block["success"] >= threshold:
            return int(block["end"])
    return None


# ---------------------------------------------------------------------------
# seeds and schedules
# ---------------------------------------------------------------------------


def train_seed(replicate: int, stream: int, episode: int, master: int) -> int:
    return derive_seed(master, int(replicate), int(stream), int(episode))


def eval_seed(replicate: int, stream: int, episode: int, master: int) -> int:
    return derive_seed(master, int(replicate), int(stream), int(episode))


def seed_pools(settings) -> dict:
    master = settings["master_seed"]
    n_train = settings["train_episodes"]
    n_eval = settings["eval_episodes"]
    replicates = settings["replicates"]
    train = {
        str(replicate): [
            train_seed(replicate, STREAM_TRAIN_SIM, episode, master)
            for episode in range(n_train)
        ]
        for replicate in range(replicates)
    }
    train_jitter = {
        str(replicate): [
            train_seed(replicate, STREAM_TRAIN_JITTER, episode, master)
            for episode in range(n_train)
        ]
        for replicate in range(replicates)
    }
    evaluate = {
        str(replicate): [
            eval_seed(replicate, STREAM_EVAL_SIM, episode, master)
            for episode in range(n_eval)
        ]
        for replicate in range(replicates)
    }
    eval_jitter = {
        str(replicate): [
            eval_seed(replicate, STREAM_EVAL_JITTER, episode, master)
            for episode in range(n_eval)
        ]
        for replicate in range(replicates)
    }
    all_train = [seed for values in train.values() for seed in values]
    all_eval = [seed for values in evaluate.values() for seed in values]
    all_train_jitter = [seed for values in train_jitter.values() for seed in values]
    all_eval_jitter = [seed for values in eval_jitter.values() for seed in values]
    return {
        "streams": {
            "train_sim": STREAM_TRAIN_SIM,
            "eval_sim": STREAM_EVAL_SIM,
            "train_jitter": STREAM_TRAIN_JITTER,
            "eval_jitter": STREAM_EVAL_JITTER,
            "reward_shuffle": STREAM_REWARD_SHUFFLE,
        },
        "train_sim": train,
        "train_jitter": train_jitter,
        "eval_sim": evaluate,
        "eval_jitter": eval_jitter,
        "disjoint_train_eval": bool(
            set(all_train).isdisjoint(all_eval)
            and set(all_train_jitter).isdisjoint(all_eval_jitter)
        ),
        "unique_train": len(set(all_train)) == len(all_train),
        "unique_eval": len(set(all_eval)) == len(all_eval),
        "unique_train_jitter": len(set(all_train_jitter)) == len(all_train_jitter),
        "unique_eval_jitter": len(set(all_eval_jitter)) == len(all_eval_jitter),
        "train_overlap_count": int(
            len(set(all_train) & set(all_eval))
            + len(set(all_train_jitter) & set(all_eval_jitter))
        ),
    }


def make_schedule(substrate, cfg, cue: int, onsets_ms: np.ndarray):
    all_actions = np.concatenate(substrate.action_indices).astype(np.int64)
    return CueActionSchedule(
        cue_indices=substrate.cue_indices[cue],
        action_indices=all_actions,
        onsets_ms=onsets_ms,
        pulse_duration_ms=cfg.pulse_duration_ms,
        cue_current_pa=cfg.cue_current_pa,
        action_prime_current_pa=cfg.action_prime_current_pa,
        action_prime_end_ms=cfg.action_prime_end_ms,
        action_background_pa=cfg.action_background_pa,
        duration_ms=cfg.duration_ms,
    )


def draw_onsets(cfg, jitter_seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(jitter_seed))
    return rng.uniform(
        cfg.pulse_onset_min_ms, cfg.pulse_onset_max_ms, cfg.cue_neurons
    )


# ---------------------------------------------------------------------------
# one spiking episode
# ---------------------------------------------------------------------------


def run_spiking_episode(
    substrate,
    weight_state: WeightState,
    rule: ThreeFactorRule,
    trace_config,
    cfg,
    *,
    cue: int,
    simulation_seed: int,
    jitter_seed: int,
    reward_correct: float,
    reward_incorrect: float,
    reward_shuffler=None,
    enable_traces: bool,
    reward_delay_ms: float = 0.0,
) -> tuple[dict, PlasticSimulator]:
    onsets = draw_onsets(cfg, jitter_seed)
    schedule = make_schedule(substrate, cfg, cue, onsets)
    controller = TargetResponseController(
        substrate.action_indices,
        cue,
        deadline_step=cfg.deadline_step,
        reward_correct=reward_correct,
        reward_incorrect=reward_incorrect,
        reward_shuffler=reward_shuffler,
        dt_ms=cfg.dt_ms,
    )
    delay_steps = int(round(float(reward_delay_ms) / cfg.dt_ms))
    step_callback = (
        controller
        if delay_steps == 0
        else DelayedReward(controller, delay_steps)
    )
    simulator = PlasticSimulator(
        substrate.graph,
        substrate.policy,
        weight_state=weight_state,
        rule=rule,
        trace_config=trace_config if enable_traces else None,
        enable_traces=enable_traces,
        step_callback=step_callback,
        dt_ms=cfg.dt_ms,
        duration_ms=cfg.duration_ms,
        seed=simulation_seed,
        noise_std_pa=cfg.noise_std_pa,
        input_schedule=schedule,
        tau_exc_ms=cfg.tau_exc_ms,
        tau_inh_ms=cfg.tau_inh_ms,
        delay_ms=cfg.delay_ms,
        max_recorded_spikes=10_000,
    )
    started = time.perf_counter()
    result = simulator.run()
    runtime = time.perf_counter() - started
    if isinstance(step_callback, DelayedReward):
        step_callback.finalize()
    outcome = controller.outcome()
    reports = result.update_reports
    spiked = result.recorder.spike_neuron_indices
    cue_set = np.asarray(substrate.cue_indices[cue], dtype=np.int64)
    record = {
        "cue": int(cue),
        "seed": int(simulation_seed),
        "jitter_seed": int(jitter_seed),
        "onset_min_ms": round(float(onsets.min()), 6),
        "onset_max_ms": round(float(onsets.max()), 6),
        "n_spikes": int(result.recorder.n_spikes),
        "n_cue_spikes": int(np.isin(spiked, cue_set).sum()),
        "hit": bool(outcome["hit"]),
        "timed_out": bool(outcome["timed_out"]),
        "selective": bool(outcome["chosen_action"] == cue),
        "chosen_action": outcome["chosen_action"],
        "response_step": outcome["response_step"],
        "response_ms": outcome["response_ms"],
        "reward": float(outcome["reward"]),
        "n_reward_events": len(reports),
        "reward_delay_ms": round(float(reward_delay_ms), 6),
        "rewards_delivered": (
            int(step_callback.n_delivered)
            if isinstance(step_callback, DelayedReward)
            else len(reports)
        ),
        "rewards_dropped": (
            int(step_callback.n_dropped)
            if isinstance(step_callback, DelayedReward)
            else 0
        ),
        "n_slots": int(sum(item.n_slots for item in reports)),
        "n_updates": int(sum(item.n_updates for item in reports)),
        "sum_abs_applied_pa": round(
            float(sum(item.sum_abs_applied_pa for item in reports)), 9
        ),
        "mean_eligibility": round(
            float(np.mean([item.mean_eligibility for item in reports]))
            if reports
            else 0.0,
            9,
        ),
        "n_coincident_tags": int(simulator.engine.n_coincident_tags),
        "n_pushed_edges": int(simulator.engine.n_pushed_edges),
        "weight_l1_pa": round(
            float(
                np.abs(weight_state.delta_exc).sum(dtype=np.float64)
                + np.abs(weight_state.delta_inh).sum(dtype=np.float64)
            ),
            9,
        ),
        "n_changed_edges": int(
            np.count_nonzero(weight_state.delta_exc)
            + np.count_nonzero(weight_state.delta_inh)
        ),
        "runtime_s": round(runtime, 6),
        "spike_hash": result.spike_hash,
        "memory": result.summary["memory"],
    }
    return record, simulator


def weight_checkpoint(state: WeightState, episode: int) -> dict:
    description = state.describe()
    return {
        "episode": int(episode),
        "n_changed_edges": int(description["n_changed_edges"]),
        "n_plastic_edges": int(description["n_plastic"]),
        "delta_l1_pa": round(
            float(
                np.abs(state.delta_exc).sum(dtype=np.float64)
                + np.abs(state.delta_inh).sum(dtype=np.float64)
            ),
            9,
        ),
        "delta_sum_pa": float(description["delta_sum_pa"]),
        "delta_max_abs_pa": float(description["delta_max_abs_pa"]),
        "saturated_edges": int(description["saturated_edges"]),
        "cumulative_clamp_hits": int(state.clamp_hits_total),
        "cumulative_update_clips": int(state.update_clip_hits_total),
        "n_update_calls": int(state.n_update_calls),
        "delta_digest": state.delta_digest(),
        "effective_digest": state.effective_digest(),
    }


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


def evaluate(
    substrate,
    weight_state: WeightState,
    trace_config,
    cfg,
    pools: dict,
    replicate: int,
    checkpoint: int,
) -> dict:
    """Evaluate the current learned state with eta = 0 and no traces."""
    rule = ThreeFactorRule(RuleConfig(eta=0.0), weight_state)
    records = []
    simulations = pools["eval_sim"][str(replicate)]
    jitters = pools["eval_jitter"][str(replicate)]
    for episode in range(len(simulations)):
        cue = episode % substrate.config.n_cues
        record, _ = run_spiking_episode(
            substrate,
            weight_state,
            rule,
            trace_config,
            cfg,
            cue=cue,
            simulation_seed=simulations[episode],
            jitter_seed=jitters[episode],
            reward_correct=0.0,
            reward_incorrect=0.0,
            reward_shuffler=None,
            enable_traces=False,
        )
        record["episode"] = int(episode)
        record.pop("memory", None)
        records.append(record)
    return {
        "checkpoint": int(checkpoint),
        "n_episodes": len(records),
        "success_rate": round(float(np.mean([r["hit"] for r in records])), 6),
        "selective_rate": round(
            float(np.mean([r["selective"] for r in records])), 6
        ),
        "timeout_rate": round(
            float(np.mean([r["timed_out"] for r in records])), 6
        ),
        "n_hits": int(sum(1 for r in records if r["hit"])),
        "mean_response_ms_over_hits": _mean_hit_latency(records),
        "mean_spikes": round(float(np.mean([r["n_spikes"] for r in records])), 6),
        "records": records,
    }


# ---------------------------------------------------------------------------
# condition execution
# ---------------------------------------------------------------------------


def condition_spec(code: str, settings: dict) -> dict:
    if code == "A":
        return {
            "eta": 0.0,
            "reward": "outcome",
            "connectivity": "complete",
            "traces": True,
        }
    if code == "B":
        return {
            "eta": float(settings["eta"]),
            "reward": "outcome",
            "connectivity": "complete",
            "traces": True,
        }
    if code == "C":
        return {
            "eta": float(settings["eta"]),
            "reward": "zero",
            "connectivity": "complete",
            "traces": True,
        }
    if code == "D":
        return {
            "eta": float(settings["eta"]),
            "reward": "shuffled",
            "connectivity": "complete",
            "traces": True,
        }
    if code == "E":
        return {
            "eta": float(settings["eta"]),
            "reward": "outcome",
            "connectivity": "random",
            "traces": True,
        }
    if code == "F":
        return {
            "eta": float(settings["eta"]),
            "reward": "outcome",
            "connectivity": "complete",
            "traces": False,
        }
    raise ValueError(f"unknown spiking condition: {code}")


def run_spiking_condition(
    code: str,
    substrate,
    plasticity_config,
    cfg,
    settings: dict,
    pools: dict,
    replicate: int,
    *,
    save_condition_checkpoint: bool,
) -> dict:
    spec = condition_spec(code, settings)
    state = WeightState(substrate.graph, substrate.policy, plasticity_config.bounds)
    initial_delta_digest = state.delta_digest()
    rule = ThreeFactorRule(
        RuleConfig(eta=spec["eta"], update_cadence="reward_event", normalization="none"),
        state,
    )
    shuffle_rng = np.random.default_rng(
        derive_seed(settings["master_seed"], replicate, STREAM_REWARD_SHUFFLE)
    )

    def shuffler() -> float:
        return float(shuffle_rng.choice(np.array([-1.0, 1.0])))

    reward_correct = 0.0 if spec["reward"] == "zero" else cfg.reward_correct
    reward_incorrect = 0.0
    reward_shuffler = shuffler if spec["reward"] == "shuffled" else None

    checkpoints = list(settings["eval_checkpoints"])
    checkpoint_set = set(checkpoints)
    train_records: list[dict] = []
    eval_results: dict[str, dict] = {}
    weight_records: list[dict] = []
    runtime = 0.0
    final_memory = None
    invariants = None
    invariant_error = None

    for episode in range(settings["train_episodes"] + 1):
        if episode in checkpoint_set:
            weight_records.append(weight_checkpoint(state, episode))
            eval_results[str(episode)] = evaluate(
                substrate, state, plasticity_config.traces, cfg, pools, replicate, episode
            )
        if episode == settings["train_episodes"]:
            break
        cue = episode % cfg.n_cues
        record, _ = run_spiking_episode(
            substrate,
            state,
            rule,
            plasticity_config.traces,
            cfg,
            cue=cue,
            simulation_seed=pools["train_sim"][str(replicate)][episode],
            jitter_seed=pools["train_jitter"][str(replicate)][episode],
            reward_correct=reward_correct,
            reward_incorrect=reward_incorrect,
            reward_shuffler=reward_shuffler,
            enable_traces=spec["traces"],
        )
        record["episode"] = int(episode)
        memory = record.pop("memory", None)
        if episode == settings["train_episodes"] - 1:
            final_memory = memory
        runtime += record["runtime_s"]
        train_records.append(record)

    try:
        invariants = state.assert_invariants()
    except Exception as error:  # recorded, never hidden
        invariant_error = str(error)
        invariants = {"assertion": False, "error": invariant_error}

    structural_ok = bool(
        np.array_equal(state.structural_count, substrate.graph.edge_weight)
    )
    changed = int(state.describe()["n_changed_edges"])
    tags_total = int(sum(r["n_coincident_tags"] for r in train_records))
    slots_total = int(sum(r["n_slots"] for r in train_records))

    checkpoint_path = None
    if save_condition_checkpoint:
        CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint_path = (
            CHECKPOINTS_DIR / f"condition_{code}_replicate_{replicate}.npz"
        )
        save_checkpoint(
            checkpoint_path,
            weight_state=state,
            graph=substrate.graph,
            policy=substrate.policy,
            config={
                "phase": "5E",
                "condition": code,
                "replicate": replicate,
                "task": cfg.describe(),
            },
            step=settings["train_episodes"],
            seed=settings["master_seed"],
            metadata={"condition": code, "replicate": replicate},
        )

    return {
        "condition": code,
        "label": CONDITION_LABELS[code],
        "spec": {
            **spec,
            "reward_correct": reward_correct,
            "reward_incorrect": reward_incorrect,
        },
        "replicate": int(replicate),
        "train": train_records,
        "eval": eval_results,
        "weight_checkpoints": weight_records,
        "final_weights": weight_checkpoint(state, settings["train_episodes"]),
        "initial_delta_digest": initial_delta_digest,
        "delta_digest": state.delta_digest(),
        "weights_unchanged": bool(state.delta_digest() == initial_delta_digest),
        "structural_counts_immutable": structural_ok,
        "changed_edges": changed,
        "tags_total": tags_total,
        "slots_total": slots_total,
        "n_update_calls": int(state.n_update_calls),
        "invariants": invariants,
        "invariant_error": invariant_error,
        "all_finite": bool(
            np.all(np.isfinite(state.delta_exc))
            and np.all(np.isfinite(state.delta_inh))
            and np.all(np.isfinite(state.effective_exc))
            and np.all(np.isfinite(state.effective_inh))
        ),
        "runtime_s": round(runtime, 4),
        "checkpoint_path": None if checkpoint_path is None else relative(checkpoint_path),
        "memory": final_memory,
        "process_memory": process_memory(),
    }


# ---------------------------------------------------------------------------
# conventional baseline
# ---------------------------------------------------------------------------


def run_conventional_condition(cfg, settings: dict, replicate: int) -> dict:
    """Online perceptron on the one-hot cue with the designated action as label.

    This baseline is supervised: it receives the correct action label, whereas
    the spiking conditions receive only a scalar reward. It is therefore an
    information-privileged reference, not a matched control.
    """
    n_cues = cfg.n_cues
    weights = np.zeros((n_cues, n_cues), dtype=np.float64)

    def predict(cue: int) -> int:
        return int(np.argmax(weights[:, cue]))

    records = []
    eval_results = {}
    checkpoints = set(settings["eval_checkpoints"])
    for episode in range(settings["train_episodes"] + 1):
        if episode in checkpoints:
            eval_records = []
            for eval_episode in range(settings["eval_episodes"]):
                cue = eval_episode % n_cues
                prediction = predict(cue)
                eval_records.append(
                    {
                        "episode": int(eval_episode),
                        "cue": int(cue),
                        "prediction": prediction,
                        "hit": bool(prediction == cue),
                        "selective": bool(prediction == cue),
                    }
                )
            eval_results[str(episode)] = {
                "checkpoint": int(episode),
                "n_episodes": len(eval_records),
                "success_rate": round(
                    float(np.mean([r["hit"] for r in eval_records])), 6
                ),
                "selective_rate": round(
                    float(np.mean([r["selective"] for r in eval_records])), 6
                ),
                "timeout_rate": 0.0,
                "n_hits": int(sum(1 for r in eval_records if r["hit"])),
                "mean_response_ms_over_hits": None,
                "mean_spikes": 0.0,
                "records": eval_records,
            }
        if episode == settings["train_episodes"]:
            break
        cue = episode % n_cues
        prediction = predict(cue)
        hit = prediction == cue
        if not hit:
            weights[cue, cue] += 1.0
            weights[prediction, cue] -= 1.0
        records.append(
            {
                "episode": int(episode),
                "cue": int(cue),
                "prediction": int(prediction),
                "hit": bool(hit),
                "selective": bool(hit),
                "reward": 1.0 if hit else 0.0,
                "n_spikes": 0,
                "response_ms": None,
                "n_coincident_tags": 0,
            }
        )
    final = np.abs(weights).sum(dtype=np.float64)
    return {
        "condition": "G",
        "label": CONDITION_LABELS["G"],
        "spec": {
            "algorithm": "online perceptron, one-hot cue -> action",
            "information": "supervised correct-action label (privileged)",
            "eta": None,
            "reward": "not used",
            "connectivity": "dense conventional weights",
            "traces": False,
        },
        "replicate": int(replicate),
        "train": records,
        "eval": eval_results,
        "weight_checkpoints": [],
        "final_weights": {
            "delta_l1_pa": round(float(final), 6),
            "n_changed_edges": int(np.count_nonzero(weights)),
            "delta_digest": hashlib.sha256(
                np.ascontiguousarray(weights, dtype=np.float64).tobytes()
            ).hexdigest(),
        },
        "initial_delta_digest": hashlib.sha256(
            np.zeros((n_cues, n_cues)).tobytes()
        ).hexdigest(),
        "delta_digest": hashlib.sha256(
            np.ascontiguousarray(weights, dtype=np.float64).tobytes()
        ).hexdigest(),
        "weights_unchanged": False,
        "structural_counts_immutable": True,
        "changed_edges": int(np.count_nonzero(weights)),
        "tags_total": 0,
        "slots_total": 0,
        "n_update_calls": int(sum(1 for r in records if not r["hit"])),
        "invariants": {"assertion": True},
        "invariant_error": None,
        "all_finite": bool(np.all(np.isfinite(weights))),
        "runtime_s": 0.0,
        "checkpoint_path": None,
        "memory": None,
        "process_memory": process_memory(),
    }


# ---------------------------------------------------------------------------
# software contract checks
# ---------------------------------------------------------------------------


def eta_zero_equivalence(substrate, plasticity_config, cfg, settings: dict) -> dict:
    """Fixed-weight oracle and eta = 0 plastic path on one task episode."""
    cue = 0
    seed = eval_seed(0, STREAM_EVAL_SIM, 0, settings["master_seed"])
    jitter = eval_seed(0, STREAM_EVAL_JITTER, 0, settings["master_seed"])
    onsets = draw_onsets(cfg, jitter)
    schedule = make_schedule(substrate, cfg, cue, onsets)
    common = {
        "dt_ms": cfg.dt_ms,
        "duration_ms": cfg.duration_ms,
        "seed": seed,
        "noise_std_pa": cfg.noise_std_pa,
        "input_schedule": schedule,
        "tau_exc_ms": cfg.tau_exc_ms,
        "tau_inh_ms": cfg.tau_inh_ms,
        "delay_ms": cfg.delay_ms,
        "max_recorded_spikes": 10_000,
    }
    fixed_started = time.perf_counter()
    fixed = BancSimulator(substrate.graph, substrate.policy, **common).run()
    fixed_runtime = time.perf_counter() - fixed_started
    fixed_hash = spike_hash(fixed.recorder)
    fixed_spikes = int(fixed.recorder.n_spikes)
    del fixed
    gc.collect()

    state = WeightState(substrate.graph, substrate.policy, plasticity_config.bounds)
    rule = ThreeFactorRule(RuleConfig(eta=0.0), state)
    plastic_started = time.perf_counter()
    plastic = PlasticSimulator(
        substrate.graph,
        substrate.policy,
        weight_state=state,
        rule=rule,
        trace_config=plasticity_config.traces,
        enable_traces=True,
        **common,
    ).run()
    plastic_runtime = time.perf_counter() - plastic_started
    return {
        "cue": cue,
        "seed": seed,
        "jitter_seed": jitter,
        "fixed_spike_hash": fixed_hash,
        "plastic_spike_hash": plastic.spike_hash,
        "hashes_identical": bool(fixed_hash == plastic.spike_hash),
        "fixed_spikes": fixed_spikes,
        "plastic_spikes": int(plastic.recorder.n_spikes),
        "fixed_runtime_s": round(fixed_runtime, 6),
        "plastic_runtime_s": round(plastic_runtime, 6),
        "delta_digest": state.delta_digest(),
        "effective_equals_initial": bool(
            np.array_equal(state.effective_exc, state.initial_exc)
            and np.array_equal(state.effective_inh, state.initial_inh)
        ),
    }


def determinism_check(substrate, plasticity_config, cfg, settings: dict) -> dict:
    """The same evaluation episode twice must produce the same spike hash."""
    state = WeightState(substrate.graph, substrate.policy)
    eta_zero_rule = ThreeFactorRule(RuleConfig(eta=0.0), state)
    hashes = []
    spikes = []
    for _ in range(2):
        record, _ = run_spiking_episode(
            substrate,
            state,
            eta_zero_rule,
            plasticity_config.traces,
            cfg,
            cue=0,
            simulation_seed=eval_seed(0, STREAM_EVAL_SIM, 3, settings["master_seed"]),
            jitter_seed=eval_seed(
                0, STREAM_EVAL_JITTER, 3, settings["master_seed"]
            ),
            reward_correct=0.0,
            reward_incorrect=0.0,
            enable_traces=False,
        )
        hashes.append(record["spike_hash"])
        spikes.append(record["n_spikes"])
    return {
        "spike_hashes": hashes,
        "n_spikes": spikes,
        "identical": bool(hashes[0] == hashes[1]),
    }


def checkpoint_round_trip(checkpoint_path: Path, substrate, plasticity_config) -> dict:
    restored = WeightState(
        substrate.graph, substrate.policy, plasticity_config.bounds
    )
    info = load_checkpoint(
        checkpoint_path,
        weight_state=restored,
        graph=substrate.graph,
        policy=substrate.policy,
    )
    with np.load(checkpoint_path, allow_pickle=False) as data:
        saved_digest = json.loads(str(data["metadata_json"]))["delta_digest"]
    return {
        "path": relative(checkpoint_path),
        "saved_delta_digest": saved_digest,
        "restored_delta_digest": restored.delta_digest(),
        "round_trip_ok": bool(saved_digest == restored.delta_digest()),
        "traces_restored": bool(info["restored_traces"]),
    }


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def summarise_replicate(result: dict, settings: dict) -> dict:
    train = result["train"]
    blocks = block_success(train, settings["criterion_window"])
    first_window = train[: settings["criterion_window"]]
    last_window = train[-settings["criterion_window"] :]
    return {
        "replicate": result["replicate"],
        "train_success": round(
            float(np.mean([r["hit"] for r in train])), 6
        ),
        "train_selective": round(
            float(np.mean([r["selective"] for r in train])), 6
        ),
        "first_window_success": round(
            float(np.mean([r["hit"] for r in first_window])) if first_window else 0.0,
            6,
        ),
        "last_window_success": round(
            float(np.mean([r["hit"] for r in last_window])) if last_window else 0.0,
            6,
        ),
        "blocks": blocks,
        "episodes_to_criterion": episodes_to_criterion(
            blocks, settings["criterion_success"]
        ),
        "eval_success": {
            checkpoint: payload["success_rate"]
            for checkpoint, payload in result["eval"].items()
        },
        "eval_selective": {
            checkpoint: payload["selective_rate"]
            for checkpoint, payload in result["eval"].items()
        },
        "final_weight_l1_pa": result["final_weights"]["delta_l1_pa"],
        "final_changed_edges": result["final_weights"]["n_changed_edges"],
        "tags_total": result["tags_total"],
        "slots_total": result["slots_total"],
        "runtime_s": result["runtime_s"],
        "weights_unchanged": result["weights_unchanged"],
        "all_finite": result["all_finite"],
        "invariants_ok": bool(
            isinstance(result["invariants"], dict)
            and all(bool(value) for value in result["invariants"].values())
        ),
        "structural_counts_immutable": result["structural_counts_immutable"],
    }


def aggregate_condition(replicates: list[dict], settings: dict) -> dict:
    summaries = [summarise_replicate(item, settings) for item in replicates]
    checkpoints = [str(value) for value in settings["eval_checkpoints"]]
    blocks = [summary["blocks"] for summary in summaries]
    n_blocks = min(len(item) for item in blocks) if blocks else 0
    block_curve = []
    for index in range(n_blocks):
        block_curve.append(
            {
                "start": blocks[0][index]["start"],
                "end": blocks[0][index]["end"],
                "success": mean_sd(item[index]["success"] for item in blocks),
                "selective": mean_sd(item[index]["selective"] for item in blocks),
            }
        )
    return {
        "n_replicates": len(summaries),
        "train_success": mean_sd(item["train_success"] for item in summaries),
        "train_selective": mean_sd(item["train_selective"] for item in summaries),
        "first_window_success": mean_sd(
            item["first_window_success"] for item in summaries
        ),
        "last_window_success": mean_sd(
            item["last_window_success"] for item in summaries
        ),
        "eval_success": {
            checkpoint: mean_sd(
                item["eval_success"][checkpoint] for item in summaries
            )
            for checkpoint in checkpoints
        },
        "eval_selective": {
            checkpoint: mean_sd(
                item["eval_selective"][checkpoint] for item in summaries
            )
            for checkpoint in checkpoints
        },
        "episodes_to_criterion": {
            "values": [item["episodes_to_criterion"] for item in summaries],
            "n_reached": int(
                sum(
                    1
                    for item in summaries
                    if item["episodes_to_criterion"] is not None
                )
            ),
        },
        "final_weight_l1_pa": mean_sd(
            item["final_weight_l1_pa"] for item in summaries
        ),
        "final_changed_edges": mean_sd(
            item["final_changed_edges"] for item in summaries
        ),
        "tags_total": mean_sd(item["tags_total"] for item in summaries),
        "slots_total": mean_sd(item["slots_total"] for item in summaries),
        "runtime_s": mean_sd(item["runtime_s"] for item in summaries),
        "weights_unchanged_all": bool(
            all(item["weights_unchanged"] for item in summaries)
        ),
        "all_finite": bool(all(item["all_finite"] for item in summaries)),
        "invariants_ok": bool(
            all(item["invariants_ok"] for item in summaries)
        ),
        "structural_counts_immutable": bool(
            all(item["structural_counts_immutable"] for item in summaries)
        ),
        "block_curve": block_curve,
        "replicates": summaries,
    }


def paired_differences(results: dict, base: str, other: str, settings: dict) -> dict:
    checkpoints = [str(value) for value in settings["eval_checkpoints"]]
    per_checkpoint = {}
    for checkpoint in checkpoints:
        deltas = []
        for replicate in range(settings["replicates"]):
            a = results[base]["replicates"][replicate]["eval"][checkpoint][
                "success_rate"
            ]
            b = results[other]["replicates"][replicate]["eval"][checkpoint][
                "success_rate"
            ]
            deltas.append(b - a)
        per_checkpoint[checkpoint] = mean_sd(deltas)
    return per_checkpoint


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------


def make_figures(raw: dict, analysis: dict, output_dir: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    conditions = [
        code for code in CONDITIONS if code in analysis["conditions"]
    ]
    colors = {
        "A": "#444444",
        "B": "#1f77b4",
        "C": "#7f7f7f",
        "D": "#d62728",
        "E": "#9467bd",
        "F": "#2ca02c",
        "G": "#ff7f0e",
    }

    # 1. training block success
    fig, axis = plt.subplots(figsize=(9, 5))
    for code in conditions:
        curve = analysis["conditions"][code]["aggregate"]["block_curve"]
        if not curve:
            continue
        centers = [(item["start"] + item["end"]) / 2 for item in curve]
        means = [item["success"]["mean"] for item in curve]
        sds = [item["success"]["sd"] for item in curve]
        axis.plot(centers, means, marker="o", color=colors[code], label=code)
        axis.fill_between(
            centers,
            np.clip(np.array(means) - np.array(sds), 0, 1),
            np.clip(np.array(means) + np.array(sds), 0, 1),
            color=colors[code],
            alpha=0.12,
        )
        for replicate in analysis["conditions"][code]["aggregate"]["replicates"]:
            replicate_curve = replicate["blocks"]
            axis.plot(
                [(item["start"] + item["end"]) / 2 for item in replicate_curve],
                [item["success"] for item in replicate_curve],
                color=colors[code],
                alpha=0.18,
                linewidth=0.8,
            )
    axis.set_xlabel("training episode (block centre)")
    axis.set_ylabel("success rate")
    axis.set_ylim(0, 1.05)
    axis.set_title("Phase 5E training success (mean +/- SD over replicates)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    path = output_dir / "training_success.png"
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    created.append(relative(path))

    # 2. evaluation success at checkpoints
    fig, axis = plt.subplots(figsize=(9, 5))
    for code in conditions:
        aggregate = analysis["conditions"][code]["aggregate"]["eval_success"]
        checkpoints = [int(value) for value in aggregate]
        means = [aggregate[str(value)]["mean"] for value in checkpoints]
        sds = [aggregate[str(value)]["sd"] for value in checkpoints]
        axis.errorbar(
            checkpoints,
            means,
            yerr=sds,
            marker="o",
            capsize=3,
            color=colors[code],
            label=code,
        )
    axis.set_xlabel("training episodes completed")
    axis.set_ylabel("evaluation success rate")
    axis.set_ylim(0, 1.05)
    axis.set_title("Phase 5E held-out evaluation success (mean +/- SD)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    path = output_dir / "eval_success.png"
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    created.append(relative(path))

    # 3. weight change
    fig, axis = plt.subplots(figsize=(9, 5))
    for code in conditions:
        aggregate = analysis["conditions"][code]["aggregate"]
        if code == "G":
            continue
        values = []
        checkpoints = []
        for replicate in raw["conditions"][code]["replicates"]:
            checkpoints = [item["episode"] for item in replicate["weight_checkpoints"]]
            values.append([item["delta_l1_pa"] for item in replicate["weight_checkpoints"]])
        if not values:
            continue
        mean = np.mean(np.asarray(values, dtype=float), axis=0)
        sd = (
            np.std(np.asarray(values, dtype=float), axis=0, ddof=1)
            if len(values) > 1
            else np.zeros_like(mean)
        )
        axis.plot(checkpoints, mean, marker="o", color=colors[code], label=code)
        axis.fill_between(
            checkpoints, mean - sd, mean + sd, color=colors[code], alpha=0.12
        )
    axis.set_xlabel("training episodes completed")
    axis.set_ylabel("L1 learned weight change (pA)")
    axis.set_title("Phase 5E learned weight change (model output)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    path = output_dir / "weight_change.png"
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    created.append(relative(path))

    # 4. eligibility tags per training block
    fig, axis = plt.subplots(figsize=(9, 5))
    window = int(analysis["settings"]["criterion_window"])
    for code in conditions:
        if code == "G":
            continue
        per_replicate = []
        for replicate in raw["conditions"][code]["replicates"]:
            tags = [record["n_coincident_tags"] for record in replicate["train"]]
            blocks = [
                float(np.sum(tags[start : start + window]))
                for start in range(0, len(tags) - window + 1, window)
            ]
            per_replicate.append(blocks)
        if not per_replicate:
            continue
        length = min(len(item) for item in per_replicate)
        mean = np.mean(
            np.asarray([item[:length] for item in per_replicate], dtype=float),
            axis=0,
        )
        centers = [
            start + window / 2
            for start in range(0, window * length, window)
        ]
        axis.plot(centers, mean, marker="o", color=colors[code], label=code)
    axis.set_xlabel("training episode (block centre)")
    axis.set_ylabel("coincident eligibility tags per block")
    axis.set_title("Phase 5E eligibility tags (delay-matched coincidences)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    path = output_dir / "eligibility_tags.png"
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    created.append(relative(path))
    return created


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def write_markdown_report(path: Path, raw: dict, analysis: dict) -> None:
    settings = analysis["settings"]
    conditions = [code for code in CONDITIONS if code in analysis["conditions"]]
    lines = []
    lines.append("# Phase 5E - Controlled learning on a synthetic cued-response task")
    lines.append("")
    lines.append(
        "Generated by `experiments/phase_5/controlled_task.py` on "
        f"{raw['generated_at_utc']}. Every number below is a model output."
    )
    lines.append("")
    lines.append("## Scientific status")
    lines.append("")
    lines.append(
        "This is a computational construct, not an animal experiment. The cue is "
        "a stimulated neuron population and the designated response is an "
        "arbitrary declared mapping. Reward is an external scalar in task units. "
        "A weight change is the output of a declared three-factor rule and is not "
        "evidence of biological learning, dopamine release or synaptic plasticity "
        "in a fly."
    )
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        f"- {settings['train_episodes']} training episodes and "
        f"{settings['eval_episodes']} held-out evaluation episodes per checkpoint, "
        f"{settings['replicates']} replicates per condition."
    )
    lines.append(
        f"- Cues: {raw['task']['n_cues']} populations of "
        f"{raw['task']['cue_neurons']} neurons; actions: "
        f"{raw['task']['n_cues']} single-neuron populations; "
        f"{raw['task']['n_nodes']} nodes, {raw['substrates']['complete']['graph']['n_edges']} "
        "cue -> action edges (complete connectivity)."
    )
    lines.append(
        f"- Cue onset jitter {raw['task']['pulse_onset_range_ms'][0]}-"
        f"{raw['task']['pulse_onset_range_ms'][1]} ms, pulse "
        f"{raw['task']['pulse_duration_ms']} ms, response deadline "
        f"{raw['task']['response_deadline_ms']} ms, episode "
        f"{raw['task']['duration_ms']} ms at dt {raw['task']['dt_ms']} ms."
    )
    lines.append(
        "- Success: the designated action population spikes at or before the "
        "deadline step. The reward is delivered at that step; a miss returns the "
        "declared miss reward (0)."
    )
    lines.append(
        "- Eligibility is delay-matched: a tag is created only when a "
        "presynaptic packet is delivered in the same step as the postsynaptic "
        "spike. There is no coincidence window."
    )
    lines.append(
        "- Evaluation uses eta = 0 on the current learned state, the same "
        "evaluation episodes at every checkpoint, and traces disabled."
    )
    lines.append(
        "- Train and evaluation seeds are drawn from separate SeedSequence "
        f"streams before the experiment. Disjoint: "
        f"`{analysis['seed_pools']['disjoint_train_eval']}`; overlap count "
        f"`{analysis['seed_pools']['overlap_count']}`."
    )
    lines.append("")
    lines.append("## Conditions")
    lines.append("")
    rows = []
    for code in conditions:
        spec = analysis["conditions"][code]["spec"]
        rows.append(
            [
                code,
                analysis["conditions"][code]["label"],
                spec.get("eta", "n/a"),
                spec.get("reward", "n/a"),
                spec.get("connectivity", "n/a"),
                spec.get("traces", "n/a"),
            ]
        )
    lines.append(_table(["ID", "Condition", "eta", "Reward", "Connectivity", "Traces"], rows))
    lines.append("")
    lines.append(
        "Condition G is an online perceptron that receives the correct action "
        "label. It is information-privileged and is not a matched control."
    )
    lines.append("")
    lines.append("## Training results")
    lines.append("")
    rows = []
    for code in conditions:
        aggregate = analysis["conditions"][code]["aggregate"]
        rows.append(
            [
                code,
                _fmt(aggregate["first_window_success"]["mean"]),
                _fmt(aggregate["last_window_success"]["mean"]),
                f"{_fmt(aggregate['last_window_success']['mean'])} +/- "
                f"{_fmt(aggregate['last_window_success']['sd'])}",
                f"{aggregate['episodes_to_criterion']['n_reached']}/"
                f"{aggregate['n_replicates']}",
                _fmt(aggregate["final_weight_l1_pa"]["mean"], 2),
                _fmt(aggregate["final_changed_edges"]["mean"], 1),
                _fmt(aggregate["tags_total"]["mean"], 1),
            ]
        )
    lines.append(
        _table(
            [
                "ID",
                "First window",
                "Last window",
                "Last window mean +/- SD",
                "Criterion reached",
                "Final L1 (pA)",
                "Changed edges",
                "Tags",
            ],
            rows,
        )
    )
    lines.append("")
    lines.append("## Held-out evaluation")
    lines.append("")
    header = ["ID"] + [f"{value} ep" for value in settings["eval_checkpoints"]]
    rows = []
    for code in conditions:
        aggregate = analysis["conditions"][code]["aggregate"]["eval_success"]
        rows.append(
            [code]
            + [
                f"{_fmt(aggregate[str(value)]['mean'])} +/- "
                f"{_fmt(aggregate[str(value)]['sd'])}"
                for value in settings["eval_checkpoints"]
            ]
        )
    lines.append(_table(header, rows))
    lines.append("")
    lines.append("## Key result")
    lines.append("")
    verdicts = analysis.get("verdicts", {})
    detail = verdicts.get("controlled_learning_detail")
    if detail:
        lines.append(
            f"- Controlled learning: **{verdicts['controlled_learning']}**. "
            f"Condition B held-out success moved from "
            f"{_fmt(detail['B_start_eval'])} at checkpoint 0 to "
            f"{_fmt(detail['B_final_eval'])} at checkpoint "
            f"{settings['train_episodes']}; the fixed-weight control A ended at "
            f"{_fmt(detail['A_final_eval'])}. The paired B - A difference is "
            f"{_fmt(detail['difference_mean'], 3)}."
        )
        lines.append(
            f"- Replicates in which B exceeded A at the final checkpoint: "
            f"{detail['B_replicates_above_A']}/{detail['n_replicates']}."
        )
    selection = verdicts.get("action_selection_detail")
    if selection:
        lines.append(
            f"- Action selection: **{verdicts['action_selection']}**. The first "
            f"action population to spike matched the designated action on "
            f"{_fmt(selection['selective_rate'])} of held-out episodes versus a "
            f"{_fmt(selection['chance_rate'])} chance rate for four actions. "
            "Success therefore measures a conditioned response, not a "
            "competitive choice between actions."
        )
    if "shuffled_reward_control_detail" in verdicts:
        item = verdicts["shuffled_reward_control_detail"]
        lines.append(
            f"- Shuffled-reward control D: **{verdicts['shuffled_reward_control']}**. "
            f"D ended at {_fmt(item['D_final_eval'])} versus A at "
            f"{_fmt(item['A_final_eval'])} "
            f"(difference {_fmt(item['difference_mean'], 3)})."
        )
    if "criterion_is_discriminative_detail" in verdicts:
        item = verdicts["criterion_is_discriminative_detail"]
        lines.append(
            f"- Predeclared criterion discriminative: "
            f"**{verdicts['criterion_is_discriminative']}**. "
            f"{item['A_replicates_reaching_criterion']}/"
            f"{item['n_replicates']} fixed-weight A replicates reached the "
            "criterion without any weight change, so the criterion alone is not "
            "evidence of learning; the held-out evaluation is."
        )
    lines.append("")
    lines.append("## Selection accuracy (first action population to spike)")
    lines.append("")
    rows = []
    for code in conditions:
        if code == "G":
            continue
        aggregate = analysis["conditions"][code]["aggregate"]["eval_selective"]
        rows.append(
            [code]
            + [
                _fmt(aggregate[str(value)]["mean"])
                for value in settings["eval_checkpoints"]
            ]
        )
    lines.append(_table(["ID"] + [f"{value} ep" for value in settings["eval_checkpoints"]], rows))
    lines.append("")
    lines.append("## Paired differences at held-out evaluation")
    lines.append("")
    rows = []
    for other in ("B", "C", "D", "E", "F", "G"):
        if other not in analysis["paired"]:
            continue
        item = analysis["paired"][other]
        rows.append(
            [f"{other} - A"]
            + [
                f"{_fmt(item[str(value)]['mean'])} +/- {_fmt(item[str(value)]['sd'])}"
                for value in settings["eval_checkpoints"]
            ]
        )
    lines.append(_table(["Contrast"] + [f"{value} ep" for value in settings["eval_checkpoints"]], rows))
    lines.append("")
    lines.append("## Software contract checks")
    lines.append("")
    software_rows = [
        [name, str(ok)] for name, ok in analysis["software_checks"].items()
    ]
    lines.append(_table(["Check", "Passed"], software_rows))
    lines.append("")
    lines.append("## Outcome checks (scientific, reported not gated)")
    lines.append("")
    outcome_rows = [
        [name, str(ok)] for name, ok in analysis["outcome_checks"].items()
    ]
    lines.append(_table(["Check", "Passed"], outcome_rows))
    lines.append("")
    lines.append("## Integrity")
    lines.append("")
    lines.append(
        f"- Repository integrity snapshot: passed = "
        f"`{raw['integrity']['pass']}` "
        f"({raw['integrity']['checked']} files checked, "
        f"{len(raw['integrity']['failures'])} failures)."
    )
    lines.append(
        f"- eta = 0 spike hashes identical to the fixed-weight simulator: "
        f"`{raw['eta_zero_equivalence']['hashes_identical']}`."
    )
    lines.append(
        f"- Repeated evaluation episode has identical spike hash: "
        f"`{raw['determinism']['identical']}`."
    )
    lines.append(
        f"- Checkpoint round trip: "
        f"`{(raw.get('checkpoint_round_trip') or {}).get('round_trip_ok')}`."
    )
    lines.append("")
    lines.append("## Negative and inconclusive results")
    lines.append("")
    if analysis["negative_results"]:
        for item in analysis["negative_results"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for item in analysis["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    for item in analysis["files"]:
        lines.append(f"- `{item}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def build_analysis(raw: dict, settings: dict, figure_files: list[str]) -> dict:
    results = raw["conditions"]
    conditions = {
        code: {
            "label": CONDITION_LABELS[code],
            "spec": results[code]["spec"],
            "aggregate": aggregate_condition(results[code]["replicates"], settings),
        }
        for code in CONDITIONS
        if code in results
    }
    paired = {}
    if "A" in results:
        for other in ("B", "C", "D", "E", "F", "G"):
            if other in results:
                paired[other] = paired_differences(results, "A", other, settings)

    software_checks = {
        "seed_pools_disjoint": bool(raw["seed_pools"]["disjoint_train_eval"]),
        "seed_pools_unique": bool(
            raw["seed_pools"]["unique_train"]
            and raw["seed_pools"]["unique_eval"]
            and raw["seed_pools"]["unique_train_jitter"]
            and raw["seed_pools"]["unique_eval_jitter"]
        ),
        "eta_zero_matches_fixed_simulator": bool(
            raw["eta_zero_equivalence"]["hashes_identical"]
        ),
        "eta_zero_keeps_initial_weights": bool(
            raw["eta_zero_equivalence"]["effective_equals_initial"]
        ),
        "evaluation_deterministic": bool(raw["determinism"]["identical"]),
        "checkpoint_round_trip": bool(
            (raw.get("checkpoint_round_trip") or {}).get("round_trip_ok", False)
        ),
        "all_invariants": bool(
            all(
                item["aggregate"]["invariants_ok"]
                for item in conditions.values()
            )
        ),
        "structural_counts_immutable": bool(
            all(
                item["aggregate"]["structural_counts_immutable"]
                for item in conditions.values()
            )
        ),
        "all_values_finite": bool(
            all(item["aggregate"]["all_finite"] for item in conditions.values())
        ),
        "repository_integrity": bool(raw["integrity"]["pass"]),
    }
    outcome_checks = {}
    if "A" in conditions:
        outcome_checks["A_weights_unchanged"] = bool(
            conditions["A"]["aggregate"]["weights_unchanged_all"]
        )
    if "C" in conditions:
        outcome_checks["C_weights_unchanged"] = bool(
            conditions["C"]["aggregate"]["weights_unchanged_all"]
        )
        outcome_checks["C_produced_no_weight_change"] = bool(
            conditions["C"]["aggregate"]["final_weight_l1_pa"]["mean"] == 0.0
        )
    if "F" in conditions:
        outcome_checks["F_weights_unchanged"] = bool(
            conditions["F"]["aggregate"]["weights_unchanged_all"]
        )
    if "B" in conditions:
        outcome_checks["B_changed_weights"] = bool(
            conditions["B"]["aggregate"]["final_changed_edges"]["mean"] > 0
        )
        outcome_checks["B_produced_eligibility_tags"] = bool(
            conditions["B"]["aggregate"]["tags_total"]["mean"] > 0
        )
        if "A" in conditions:
            outcome_checks["B_final_eval_above_A_final_eval"] = bool(
                conditions["B"]["aggregate"]["eval_success"][
                    str(settings["train_episodes"])
                ]["mean"]
                > conditions["A"]["aggregate"]["eval_success"][
                    str(settings["train_episodes"])
                ]["mean"]
            )
    if "D" in conditions:
        outcome_checks["D_changed_weights_under_shuffled_reward"] = bool(
            conditions["D"]["aggregate"]["final_changed_edges"]["mean"] > 0
        )
    if "E" in conditions:
        outcome_checks["E_changed_weights_under_random_connectivity"] = bool(
            conditions["E"]["aggregate"]["final_changed_edges"]["mean"] > 0
        )

    negative_results = []
    if outcome_checks.get("B_final_eval_above_A_final_eval") is False:
        negative_results.append(
            "Plastic condition B did not exceed the fixed-weight control A at the "
            "final held-out checkpoint. This is a negative result and is retained."
        )
    if outcome_checks.get("B_changed_weights") is False:
        negative_results.append(
            "Condition B produced no weight change; the declared rule or task "
            "timing did not generate eligibility-tagged updates."
        )
    if outcome_checks.get("B_produced_eligibility_tags") is False:
        negative_results.append(
            "Condition B produced no delay-matched eligibility tags."
        )
    for code in ("C", "F"):
        if outcome_checks.get(f"{code}_weights_unchanged") is False:
            negative_results.append(
                f"Condition {code} changed weights although it was declared a "
                "no-learning control."
            )

    final_checkpoint = str(settings["train_episodes"])
    first_checkpoint = str(settings["eval_checkpoints"][0])
    n_cues = int(raw["task"]["n_cues"])
    verdicts = {}
    if "B" in conditions and "A" in conditions:
        b_final = conditions["B"]["aggregate"]["eval_success"][final_checkpoint][
            "mean"
        ]
        a_final = conditions["A"]["aggregate"]["eval_success"][final_checkpoint][
            "mean"
        ]
        b_start = conditions["B"]["aggregate"]["eval_success"][first_checkpoint][
            "mean"
        ]
        b_reps = conditions["B"]["aggregate"]["replicates"]
        a_reps = conditions["A"]["aggregate"]["replicates"]
        wins = sum(
            1
            for b_rep, a_rep in zip(b_reps, a_reps)
            if b_rep["eval_success"][final_checkpoint]
            > a_rep["eval_success"][final_checkpoint]
        )
        verdicts["controlled_learning"] = (
            "PASS WITH LIMITATIONS"
            if b_final > a_final and wins == len(b_reps)
            else ("FAIL" if b_final <= a_final else "INCONCLUSIVE")
        )
        verdicts["controlled_learning_detail"] = {
            "B_start_eval": b_start,
            "B_final_eval": b_final,
            "A_final_eval": a_final,
            "difference_mean": round(b_final - a_final, 6),
            "B_replicates_above_A": int(wins),
            "n_replicates": len(b_reps),
        }
        if "eval_selective" in conditions["B"]["aggregate"]:
            selective = conditions["B"]["aggregate"]["eval_selective"][
                final_checkpoint
            ]["mean"]
            chance = 1.0 / n_cues
            verdicts["action_selection"] = (
                "PASS" if selective > chance else "FAIL"
            )
            verdicts["action_selection_detail"] = {
                "selective_rate": selective,
                "chance_rate": round(chance, 6),
                "definition": (
                    "first action population to spike equals the designated one"
                ),
            }
    if "D" in conditions and "A" in conditions:
        d_final = conditions["D"]["aggregate"]["eval_success"][final_checkpoint][
            "mean"
        ]
        a_final = conditions["A"]["aggregate"]["eval_success"][final_checkpoint][
            "mean"
        ]
        verdicts["shuffled_reward_control"] = (
            "PASS" if d_final <= a_final else "INCONCLUSIVE"
        )
        verdicts["shuffled_reward_control_detail"] = {
            "D_final_eval": d_final,
            "A_final_eval": a_final,
            "difference_mean": round(d_final - a_final, 6),
        }
    if "A" in conditions:
        a_reached = conditions["A"]["aggregate"]["episodes_to_criterion"][
            "n_reached"
        ]
        verdicts["criterion_is_discriminative"] = "NO" if a_reached > 0 else "YES"
        verdicts["criterion_is_discriminative_detail"] = {
            "A_replicates_reaching_criterion": int(a_reached),
            "n_replicates": conditions["A"]["aggregate"]["n_replicates"],
        }
    if verdicts.get("action_selection") == "FAIL":
        negative_results.append(
            "Action selection failed: the first action population to spike "
            "matched the designated action on "
            f"{verdicts['action_selection_detail']['selective_rate']:.3f} of "
            "held-out episodes, below the four-action chance rate of 0.25. The "
            "success metric measures a conditioned response, not competitive "
            "action selection."
        )
    if verdicts.get("criterion_is_discriminative") == "NO":
        negative_results.append(
            "The predeclared success criterion is not discriminative: the "
            f"fixed-weight control A reached it in "
            f"{verdicts['criterion_is_discriminative_detail']['A_replicates_reaching_criterion']}"
            f"/{verdicts['criterion_is_discriminative_detail']['n_replicates']} "
            "replicates without any weight change."
        )

    limitations = [
        "The task is a synthetic construct with an arbitrary cue -> action "
        "mapping; it is not a fly behaviour and not the Phase 4H pathway.",
        "Reward is an external scalar in task units; no dopamine, octopamine or "
        "serotonin quantity was measured.",
        "A weight change is a model output of the declared three-factor rule; it "
        "is not evidence of biological synaptic plasticity.",
        "The eligibility rule has no coincidence window: a tag exists only when a "
        "delayed presynaptic packet arrives in the same step as the postsynaptic "
        "spike. Learning therefore depends on precise spike timing.",
        "Success is measured only for the designated response population; the "
        "selective (competition) metric is reported separately and is not the "
        "primary criterion.",
        "Three replicates give a descriptive mean and standard deviation; no "
        "formal significance claim is made in Phase 5E.",
        "The conventional baseline receives the correct action label and only "
        "bounds what a supervised method can do on this task.",
        "Evaluation uses the same held-out episodes at each checkpoint; it does "
        "not test generalisation to unseen cue mappings.",
        "The synthetic graph is small (tens of nodes); nothing here tests the "
        "BANC connectome.",
        "Action selection (the first action population to spike) remained near "
        "or below the four-action chance rate; this task measures a conditioned "
        "response, not competitive action selection.",
        (
            "Condition E's Bernoulli(0.5) wiring has fewer edges and lower total "
            f"cue input than the complete graph "
            f"({raw['substrates']['random']['graph']['n_edges']} vs "
            f"{raw['substrates']['complete']['graph']['n_edges']} edges), so its "
            "impaired response cannot be attributed to topology alone."
        ),
    ]
    if verdicts.get("criterion_is_discriminative") == "NO":
        limitations.append(
            "The predeclared 0.75 success / 20-episode criterion was met by the "
            "fixed-weight control A without any weight change, so the criterion "
            "does not discriminate learning on this task; the held-out "
            "evaluation is the evidence used."
        )
    files = [
        relative(TASK_CONFIG_PATH),
        relative(PLASTICITY_CONFIG_PATH),
        relative(RESULTS_DIR / "controlled_learning_raw.json"),
        relative(RESULTS_DIR / "controlled_learning_analysis.json"),
        relative(RESULTS_DIR / "controlled_learning_report.json"),
        "reports/PHASE_5E_CONTROLLED_LEARNING.md",
        "reports/PHASE_5E_CONTROLLED_LEARNING.json",
    ] + figure_files
    round_trip = raw.get("checkpoint_round_trip") or {}
    if round_trip.get("path"):
        files.append(round_trip["path"])

    return {
        "phase": "5E",
        "generated_at_utc": raw["generated_at_utc"],
        "settings": {
            key: value
            for key, value in settings.items()
            if key != "raw"
        },
        "seed_pools": {
            "disjoint_train_eval": raw["seed_pools"]["disjoint_train_eval"],
            "overlap_count": raw["seed_pools"]["train_overlap_count"],
            "unique_train": raw["seed_pools"]["unique_train"],
            "unique_eval": raw["seed_pools"]["unique_eval"],
        },
        "conditions": conditions,
        "paired": paired,
        "software_checks": software_checks,
        "outcome_checks": outcome_checks,
        "negative_results": negative_results,
        "limitations": limitations,
        "verdicts": verdicts,
        "files": files,
        "software_status": (
            "PASS" if all(software_checks.values()) else "FAIL"
        ),
        "learning_status": verdicts.get(
            "controlled_learning",
            "PASS" if all(outcome_checks.values()) else "PASS WITH LIMITATIONS",
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="reduced budgets")
    parser.add_argument(
        "--conditions",
        default="A,B,C,D,E,F,G",
        help="comma-separated condition IDs",
    )
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args(argv)

    task_cfg, settings = load_task_config(TASK_CONFIG_PATH)
    plasticity_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)
    selected = [item.strip() for item in args.conditions.split(",") if item.strip()]
    unknown = [item for item in selected if item not in CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown conditions: {unknown}")

    if args.quick:
        settings = dict(settings)
        settings["train_episodes"] = 8
        settings["eval_episodes"] = 4
        settings["replicates"] = 1
        settings["criterion_window"] = 4
        settings["eval_checkpoints"] = [0, 4, 8]

    if settings["train_episodes"] % task_cfg.n_cues != 0:
        raise SystemExit(
            "train_episodes must be a multiple of n_cues for a balanced cue order"
        )
    if settings["eval_episodes"] % task_cfg.n_cues != 0:
        raise SystemExit(
            "eval_episodes must be a multiple of n_cues for a balanced cue order"
        )

    started = time.perf_counter()
    complete = build_task_substrate(task_cfg, seed=settings["master_seed"])
    random_cfg = replace(task_cfg, connectivity="random")
    random_substrate = build_task_substrate(
        random_cfg, seed=settings["master_seed"]
    )
    pools = seed_pools(settings)

    raw = {
        "phase": "5E",
        "status": "running",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": {
            "quick": bool(args.quick),
            "conditions": selected,
            "module": "experiments.phase_5.controlled_task",
        },
        "software": software_versions(),
        "config": {
            "task_path": relative(TASK_CONFIG_PATH),
            "task_sha256": sha256_file(TASK_CONFIG_PATH),
            "plasticity_path": relative(PLASTICITY_CONFIG_PATH),
            "plasticity_sha256": sha256_file(PLASTICITY_CONFIG_PATH),
        },
        "task": task_cfg.describe(),
        "plasticity": plasticity_config.describe(),
        "settings": {key: value for key, value in settings.items() if key != "raw"},
        "substrates": {
            "complete": complete.describe(),
            "random": random_substrate.describe(),
        },
        "seed_pools": pools,
        "conditions": {},
        "eta_zero_equivalence": None,
        "determinism": None,
        "checkpoint_round_trip": None,
        "integrity": None,
        "process_memory_start": process_memory(),
    }

    spiking_selected = [code for code in selected if code != "G"]
    for code in spiking_selected:
        substrate = random_substrate if code == "E" else complete
        replicates = []
        for replicate in range(settings["replicates"]):
            result = run_spiking_condition(
                code,
                substrate,
                plasticity_config,
                task_cfg,
                settings,
                pools,
                replicate,
                save_condition_checkpoint=(
                    code == settings["checkpoint_condition"] and replicate == 0
                ),
            )
            replicates.append(result)
            gc.collect()
            print(
                f"{code} replicate {replicate}: "
                f"train={np.mean([r['hit'] for r in result['train']]):.3f} "
                f"eval_final="
                f"{result['eval'][str(settings['train_episodes'])]['success_rate']:.3f} "
                f"changed={result['changed_edges']} tags={result['tags_total']}"
            )
        raw["conditions"][code] = {
            "label": CONDITION_LABELS[code],
            "spec": replicates[0]["spec"],
            "replicates": replicates,
        }

    if "G" in selected:
        replicates = [
            run_conventional_condition(task_cfg, settings, replicate)
            for replicate in range(settings["replicates"])
        ]
        raw["conditions"]["G"] = {
            "label": CONDITION_LABELS["G"],
            "spec": replicates[0]["spec"],
            "replicates": replicates,
        }
        print(
            "G conventional: "
            f"train={np.mean([r['hit'] for r in replicates[0]['train']]):.3f}"
        )

    raw["eta_zero_equivalence"] = eta_zero_equivalence(
        complete, plasticity_config, task_cfg, settings
    )
    raw["determinism"] = determinism_check(
        complete, plasticity_config, task_cfg, settings
    )
    checkpoint_code = settings["checkpoint_condition"]
    if checkpoint_code in raw["conditions"]:
        checkpoint_path = (
            CHECKPOINTS_DIR
            / f"condition_{checkpoint_code}_replicate_0.npz"
        )
        if checkpoint_path.is_file():
            raw["checkpoint_round_trip"] = checkpoint_round_trip(
                checkpoint_path,
                random_substrate if checkpoint_code == "E" else complete,
                plasticity_config,
            )
    raw["integrity"] = integrity_snapshot()
    raw["process_memory_end"] = process_memory()

    analysis = build_analysis(raw, settings, figure_files=[])
    if not args.skip_figures:
        figure_files = make_figures(raw, analysis, FIGURES_DIR)
        analysis["files"].extend(figure_files)
    raw["status"] = "complete"

    suffix = "_quick" if args.quick else ""
    raw_path = RESULTS_DIR / f"controlled_learning_raw{suffix}.json"
    analysis_path = RESULTS_DIR / f"controlled_learning_analysis{suffix}.json"
    write_json(raw_path, raw)
    write_json(analysis_path, analysis)
    report_json = RESULTS_DIR / f"controlled_learning_report{suffix}.json"
    write_json(report_json, analysis)

    if not args.quick:
        write_markdown_report(
            PROJECT_ROOT / "reports" / "PHASE_5E_CONTROLLED_LEARNING.md",
            raw,
            analysis,
        )
        write_json(
            PROJECT_ROOT / "reports" / "PHASE_5E_CONTROLLED_LEARNING.json",
            analysis,
        )

    print(
        json.dumps(
            {
                "raw": relative(raw_path),
                "analysis": relative(analysis_path),
                "software_status": analysis["software_status"],
                "learning_status": analysis["learning_status"],
                "software_checks": analysis["software_checks"],
                "outcome_checks": analysis["outcome_checks"],
                "runtime_s": round(time.perf_counter() - started, 2),
            },
            indent=1,
        )
    )
    failures = [
        name for name, ok in analysis["software_checks"].items() if not ok
    ]
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
