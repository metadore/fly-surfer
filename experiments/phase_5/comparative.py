"""Phase 5F comparative evaluation and robustness on the controlled task.

SCIENTIFIC STATUS
    Every number here is a model output of a synthetic conditioned-response
    task. The wiring factor is complete versus Bernoulli(0.5) cue -> action
    wiring inside that synthetic graph. It is not the BANC connectome; no
    connectome edge is read, modified or simulated. Reward is an external task
    scalar. A weight change is the output of the declared three-factor rule and
    is not evidence of biological synaptic plasticity.

Design (declared in ``configs/plasticity_comparison.yaml``)
    Core comparison: fixed and plastic weights on complete and random wiring,
    each with the same episode budget, the same training pool and the same
    held-out evaluation pool, across independent seeds. A supervised perceptron
    is reported separately as an information-privileged reference.

    Robustness: one declared parameter is varied at a time around the baseline
    (eta, tau_e, reward magnitude, weight bounds, initial weights, network size,
    structural threshold, reward delay). Every cell is retained, including
    cells with no spikes or no weight change.

Statistics
    The unit of replication is a seed, never a timestep. Episodes inside one
    seed share a weight trajectory and are not independent samples, so no
    statistic pools them. Conditions are summarised with mean, SD, median, range
    and a bootstrap confidence interval of the mean over seeds. Declared paired
    contrasts use the same seed index in both conditions and are tested with a
    two-sided exact sign-flip permutation test; the family of core contrasts is
    Holm-Bonferroni corrected. Robustness cells are descriptive and are not
    tested for significance.

Usage:
  python -m experiments.phase_5.comparative
  python -m experiments.phase_5.comparative --quick
  python -m experiments.phase_5.comparative --skip-robustness
"""

from __future__ import annotations

import argparse
import gc
import itertools
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

from experiments.phase_4h.common import (  # noqa: E402
    bootstrap_ci,
    integrity_snapshot,
    process_memory,
    software_versions,
    summary_stats,
)
from experiments.phase_5.controlled_task import (  # noqa: E402
    PLASTICITY_CONFIG_PATH,
    TASK_CONFIG_PATH,
    evaluate as evaluate_state,
    mean_sd,
    relative,
    run_conventional_condition,
    run_spiking_episode,
    seed_pools,
    sha256_file,
    weight_checkpoint,
    write_json,
)
from plasticity.config import load_plasticity_config  # noqa: E402
from plasticity.rules import RuleConfig, ThreeFactorRule  # noqa: E402
from plasticity.tasks import (  # noqa: E402
    TaskConfig,
    build_task_substrate,
    load_task_config,
)
from plasticity.traces import TraceConfig  # noqa: E402
from plasticity.weights import WeightBounds, WeightState  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity_comparison.yaml"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase_5f"
FIGURES_DIR = RESULTS_DIR / "figures"

CONDITION_LABELS = {
    "fixed_complete": "fixed weights, complete wiring",
    "plastic_complete": "plastic weights, complete wiring",
    "fixed_random": "fixed weights, random wiring",
    "plastic_random": "plastic weights, random wiring",
    "conventional": "supervised perceptron (privileged reference)",
}
SPIKING_CONDITIONS = (
    "fixed_complete",
    "plastic_complete",
    "fixed_random",
    "plastic_random",
)
ROBUSTNESS_PLASTIC = "plastic_complete"
ROBUSTNESS_FIXED = "fixed_complete"
COMPACT_FIELDS = (
    "cue",
    "hit",
    "timed_out",
    "selective",
    "chosen_action",
    "response_step",
    "response_ms",
    "reward",
    "n_spikes",
    "n_cue_spikes",
    "n_reward_events",
    "n_slots",
    "n_updates",
    "sum_abs_applied_pa",
    "mean_eligibility",
    "n_coincident_tags",
    "n_pushed_edges",
    "weight_l1_pa",
    "n_changed_edges",
    "reward_delay_ms",
    "rewards_delivered",
    "rewards_dropped",
)


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def _integer(value, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    if int(value) < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _checkpoints(values, train_episodes: int, name: str) -> list[int]:
    checkpoints = [int(value) for value in values]
    if (
        not checkpoints
        or checkpoints[0] != 0
        or checkpoints[-1] != train_episodes
        or checkpoints != sorted(set(checkpoints))
    ):
        raise ValueError(
            f"{name} must start at 0, end at {train_episodes} and increase"
        )
    return checkpoints


def load_comparison_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("comparison config must be a mapping")
    core_block = raw.get("core")
    conventional_block = raw.get("conventional")
    robustness_block = raw.get("robustness")
    statistics = raw.get("statistics")
    seeds = raw.get("seeds")
    for name, block in (
        ("core", core_block),
        ("conventional", conventional_block),
        ("robustness", robustness_block),
        ("statistics", statistics),
        ("seeds", seeds),
    ):
        if not isinstance(block, dict):
            raise ValueError(f"{name} must be a mapping")

    core = {
        "conditions": [str(item) for item in core_block.get("conditions", [])],
        "contrasts": [
            [str(pair[0]), str(pair[1])]
            for pair in core_block.get("contrasts", [])
        ],
        "n_seeds": _integer(core_block.get("n_seeds", 10), "core.n_seeds", 2),
        "train_episodes": _integer(
            core_block.get("train_episodes", 160), "core.train_episodes"
        ),
        "eval_episodes": _integer(
            core_block.get("eval_episodes", 40), "core.eval_episodes"
        ),
        "eta": _number(core_block.get("eta", 1.0), "core.eta"),
    }
    if len(core["conditions"]) < 2:
        raise ValueError("core.conditions must contain at least two conditions")
    unknown = [code for code in core["conditions"] if code not in SPIKING_CONDITIONS]
    if unknown:
        raise ValueError(f"unknown core conditions: {unknown}")
    for pair in core["contrasts"]:
        if len(pair) != 2 or pair[0] not in core["conditions"] or pair[1] not in core["conditions"]:
            raise ValueError(f"contrast references an undeclared condition: {pair}")
        if pair[0] == pair[1]:
            raise ValueError("a contrast must compare two different conditions")
    core["eval_checkpoints"] = _checkpoints(
        core_block.get("eval_checkpoints", [0, core["train_episodes"]]),
        core["train_episodes"],
        "core.eval_checkpoints",
    )

    conventional = {
        "n_seeds": _integer(
            conventional_block.get("n_seeds", 10), "conventional.n_seeds"
        ),
        "train_episodes": _integer(
            conventional_block.get("train_episodes", 160),
            "conventional.train_episodes",
        ),
        "eval_episodes": _integer(
            conventional_block.get("eval_episodes", 40),
            "conventional.eval_episodes",
        ),
    }
    conventional["eval_checkpoints"] = _checkpoints(
        conventional_block.get(
            "eval_checkpoints", [0, conventional["train_episodes"]]
        ),
        conventional["train_episodes"],
        "conventional.eval_checkpoints",
    )

    axes_raw = robustness_block.get("axes")
    if not isinstance(axes_raw, dict) or not axes_raw:
        raise ValueError("robustness.axes must be a non-empty mapping")
    axes = {}
    for axis, body in axes_raw.items():
        if not isinstance(body, dict) or not isinstance(body.get("values"), list):
            raise ValueError(f"robustness.axes.{axis} must declare values")
        values = body["values"]
        if not values:
            raise ValueError(f"robustness.axes.{axis} has no values")
        labels = [str(item.get("label")) for item in values]
        if len(set(labels)) != len(labels):
            raise ValueError(f"robustness.axes.{axis} has duplicate labels")
        reference = str(body.get("reference"))
        if reference not in labels:
            raise ValueError(
                f"robustness.axes.{axis}.reference must name one declared label"
            )
        axes[str(axis)] = {
            "runs_control": bool(body.get("runs_control", False)),
            "reference": reference,
            "values": values,
        }
    robustness = {
        "n_seeds": _integer(
            robustness_block.get("n_seeds", 4), "robustness.n_seeds", 2
        ),
        "train_episodes": _integer(
            robustness_block.get("train_episodes", 120),
            "robustness.train_episodes",
        ),
        "eval_episodes": _integer(
            robustness_block.get("eval_episodes", 24),
            "robustness.eval_episodes",
        ),
        "axes": axes,
    }
    robustness["eval_checkpoints"] = _checkpoints(
        robustness_block.get(
            "eval_checkpoints", [0, robustness["train_episodes"]]
        ),
        robustness["train_episodes"],
        "robustness.eval_checkpoints",
    )

    declared = {
        "alpha": _number(statistics.get("alpha", 0.05), "statistics.alpha"),
        "bootstrap_resamples": _integer(
            statistics.get("bootstrap_resamples", 10000),
            "statistics.bootstrap_resamples",
        ),
        "bootstrap_seed": _integer(
            statistics.get("bootstrap_seed", 20261117),
            "statistics.bootstrap_seed",
            minimum=0,
        ),
        "exact_permutation_max_n": _integer(
            statistics.get("exact_permutation_max_n", 16),
            "statistics.exact_permutation_max_n",
        ),
        "monte_carlo_draws": _integer(
            statistics.get("monte_carlo_draws", 100000),
            "statistics.monte_carlo_draws",
        ),
    }
    if not 0.0 < declared["alpha"] < 1.0:
        raise ValueError("statistics.alpha must lie in (0, 1)")
    if declared["exact_permutation_max_n"] > 20:
        raise ValueError("an exact sign-flip enumeration above n = 20 is refused")

    seed_block = {
        "master_seed": _integer(
            seeds.get("master_seed", 20261118), "seeds.master_seed"
        ),
        "substrate_seed": _integer(
            seeds.get("substrate_seed", 20261114), "seeds.substrate_seed"
        ),
    }

    # Balanced cue order is required for every declared budget and size.
    for name, block in (("core", core), ("robustness", robustness)):
        for value in block["axes"].values() if name == "robustness" else [None]:
            sizes = (
                [int(item.get("n_cues", 4)) for item in value["values"]]
                if value
                else [4]
            )
            for size in sizes:
                if block["train_episodes"] % size:
                    raise ValueError(
                        f"{name}.train_episodes must be a multiple of n_cues {size}"
                    )
                if block["eval_episodes"] % size:
                    raise ValueError(
                        f"{name}.eval_episodes must be a multiple of n_cues {size}"
                    )

    return {
        "core": core,
        "conventional": conventional,
        "robustness": robustness,
        "statistics": declared,
        "seeds": seed_block,
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def holm(pvalues: dict, alpha: float) -> dict:
    items = sorted(pvalues.items(), key=lambda item: item[1])
    count = len(items)
    adjusted = {}
    running = 0.0
    for rank, (name, value) in enumerate(items):
        candidate = min(1.0, (count - rank) * float(value))
        running = max(running, candidate)
        adjusted[name] = round(running, 8)
    return {
        "method": "Holm-Bonferroni",
        "alpha": float(alpha),
        "adjusted": adjusted,
        "rejected": {name: bool(value <= alpha) for name, value in adjusted.items()},
    }


def sign_flip_test(
    differences, *, exact_max_n: int, draws: int, seed: int
) -> dict:
    values = np.asarray(list(differences), dtype=np.float64)
    if values.size == 0:
        return {"p_value": None, "method": "no data"}
    observed = abs(float(values.sum()))
    if values.size <= exact_max_n:
        signs = np.asarray(
            list(itertools.product((-1.0, 1.0), repeat=values.size)),
            dtype=np.float64,
        )
        statistics = np.abs(signs @ values)
        p_value = float(np.count_nonzero(statistics >= observed - 1e-12)) / statistics.size
        return {
            "p_value": round(p_value, 8),
            "method": f"exact two-sided sign flip ({statistics.size} assignments)",
        }
    rng = np.random.default_rng(int(seed))
    signs = rng.choice((-1.0, 1.0), size=(int(draws), values.size))
    statistics = np.abs(signs @ values)
    p_value = (1.0 + float(np.count_nonzero(statistics >= observed))) / (
        1.0 + int(draws)
    )
    return {
        "p_value": round(p_value, 8),
        "method": f"monte carlo two-sided sign flip ({int(draws)} draws)",
    }


def condition_summary(values, statistical: dict) -> dict:
    stats = summary_stats(values)
    stats["bootstrap_ci_mean"] = bootstrap_ci(
        values,
        n_resamples=statistical["bootstrap_resamples"],
        seed=statistical["bootstrap_seed"],
    )
    return stats


def paired_contrast(treatment, reference, statistical: dict) -> dict:
    left = np.asarray(list(treatment), dtype=np.float64)
    right = np.asarray(list(reference), dtype=np.float64)
    if left.size != right.size or left.size < 2:
        raise ValueError("a paired contrast needs equal, non-trivial samples")
    differences = left - right
    sd = float(differences.std(ddof=1))
    return {
        "n_pairs": int(differences.size),
        "mean_difference": round(float(differences.mean()), 6),
        "median_difference": round(float(np.median(differences)), 6),
        "sd_difference": round(sd, 6),
        "min_difference": round(float(differences.min()), 6),
        "max_difference": round(float(differences.max()), 6),
        "effect_size_dz": round(float(differences.mean() / sd), 6) if sd else None,
        "n_positive": int(np.count_nonzero(differences > 0)),
        "n_negative": int(np.count_nonzero(differences < 0)),
        "n_zero": int(np.count_nonzero(differences == 0)),
        "bootstrap_ci_mean_difference": bootstrap_ci(
            differences,
            n_resamples=statistical["bootstrap_resamples"],
            seed=statistical["bootstrap_seed"],
        ),
        **sign_flip_test(
            differences,
            exact_max_n=statistical["exact_permutation_max_n"],
            draws=statistical["monte_carlo_draws"],
            seed=statistical["bootstrap_seed"],
        ),
    }


# ---------------------------------------------------------------------------
# one cell
# ---------------------------------------------------------------------------


def _compact(record: dict, episode: int) -> dict:
    payload = {"episode": int(episode)}
    payload.update({key: record[key] for key in COMPACT_FIELDS if key in record})
    return payload


def _last_window_success(records, window: int) -> float | None:
    if not records:
        return None
    chunk = records[-window:]
    return round(float(np.mean([item["hit"] for item in chunk])), 6)


def run_cell(
    code: str,
    *,
    task_cfg: TaskConfig,
    bounds: WeightBounds,
    trace_config: TraceConfig,
    eta: float,
    reward_magnitude: float,
    reward_delay_ms: float,
    train_episodes: int,
    checkpoints,
    pools: dict,
    seed_index: int,
    substrate_seed: int,
    window: int = 20,
) -> dict:
    """Train one seed of one condition and evaluate at the declared points."""
    substrate = build_task_substrate(task_cfg, seed=int(substrate_seed))
    state = WeightState(substrate.graph, substrate.policy, bounds)
    initial_delta = state.delta_digest()
    rule = ThreeFactorRule(RuleConfig(eta=float(eta)), state)
    checkpoint_set = set(int(value) for value in checkpoints)

    train_records: list[dict] = []
    eval_results: dict[str, dict] = {}
    weight_records: list[dict] = []
    runtime = 0.0
    final_memory = None
    n_spikes_total = 0
    n_updates_total = 0
    n_tags_total = 0
    n_slots_total = 0
    n_delivered_total = 0
    n_dropped_total = 0

    for episode in range(train_episodes + 1):
        if episode in checkpoint_set:
            weight_records.append(weight_checkpoint(state, episode))
            eval_results[str(episode)] = evaluate_state(
                substrate,
                state,
                trace_config,
                task_cfg,
                pools,
                seed_index,
                episode,
            )
        if episode == train_episodes:
            break
        cue = episode % task_cfg.n_cues
        record, _ = run_spiking_episode(
            substrate,
            state,
            rule,
            trace_config,
            task_cfg,
            cue=cue,
            simulation_seed=pools["train_sim"][str(seed_index)][episode],
            jitter_seed=pools["train_jitter"][str(seed_index)][episode],
            reward_correct=task_cfg.reward_correct * float(reward_magnitude),
            reward_incorrect=task_cfg.reward_incorrect,
            reward_shuffler=None,
            enable_traces=True,
            reward_delay_ms=float(reward_delay_ms),
        )
        memory = record.pop("memory", None)
        if episode == train_episodes - 1:
            final_memory = memory
        runtime += record["runtime_s"]
        n_spikes_total += record["n_spikes"]
        n_updates_total += record["n_updates"]
        n_tags_total += record["n_coincident_tags"]
        n_slots_total += record["n_slots"]
        n_delivered_total += record["rewards_delivered"]
        n_dropped_total += record["rewards_dropped"]
        train_records.append(_compact(record, episode))

    invariant_error = None
    try:
        invariants = state.assert_invariants()
    except Exception as error:  # recorded, never hidden
        invariant_error = str(error)
        invariants = {"assertion": False, "error": invariant_error}
    structural_ok = bool(
        np.array_equal(state.structural_count, substrate.graph.edge_weight)
    )
    final_checkpoint = int(checkpoints[-1])
    final_eval = eval_results[str(final_checkpoint)]
    start_eval = eval_results["0"]
    description = state.describe()
    return {
        "condition": code,
        "label": CONDITION_LABELS[code],
        "seed_index": int(seed_index),
        "parameters": {
            "eta": float(eta),
            "reward_magnitude": float(reward_magnitude),
            "reward_delay_ms": float(reward_delay_ms),
            "bounds": bounds.describe(),
            "tau_e_ms": trace_config.tau_e_ms,
            "substrate_seed": int(substrate_seed),
            "connectivity": task_cfg.connectivity,
            "n_cues": task_cfg.n_cues,
            "threshold": task_cfg.threshold,
        },
        "substrate": substrate.describe(),
        "train": train_records,
        "eval": eval_results,
        "weight_checkpoints": weight_records,
        "final_weights": weight_checkpoint(state, final_checkpoint),
        "final_checkpoint": final_checkpoint,
        "final_success": final_eval["success_rate"],
        "start_success": start_eval["success_rate"],
        "final_selective": final_eval["selective_rate"],
        "final_timeout": final_eval["timeout_rate"],
        "final_mean_response_ms": final_eval["mean_response_ms_over_hits"],
        "train_last_window_success": _last_window_success(train_records, window),
        "weights_unchanged": bool(state.delta_digest() == initial_delta),
        "changed_edges": int(description["n_changed_edges"]),
        "structural_counts_immutable": structural_ok,
        "n_spikes_total": int(n_spikes_total),
        "n_updates_total": int(n_updates_total),
        "tags_total": int(n_tags_total),
        "slots_total": int(n_slots_total),
        "rewards_delivered": int(n_delivered_total),
        "rewards_dropped": int(n_dropped_total),
        "invariants": invariants,
        "invariant_error": invariant_error,
        "all_finite": bool(
            np.all(np.isfinite(state.delta_exc))
            and np.all(np.isfinite(state.delta_inh))
            and np.all(np.isfinite(state.effective_exc))
            and np.all(np.isfinite(state.effective_inh))
        ),
        "silent": bool(n_spikes_total == 0),
        "no_updates": bool(n_updates_total == 0),
        "runtime_s": round(runtime, 4),
        "delta_digest": state.delta_digest(),
        "memory": final_memory,
    }


def _pools_for(block: dict, master_seed: int) -> dict:
    return seed_pools(
        {
            "master_seed": int(master_seed),
            "train_episodes": int(block["train_episodes"]),
            "eval_episodes": int(block["eval_episodes"]),
            "replicates": int(block["n_seeds"]),
        }
    )


def _connectivity(code: str) -> str:
    return "random" if code.endswith("random") else "complete"


# ---------------------------------------------------------------------------
# core comparison
# ---------------------------------------------------------------------------


def run_core(
    cfg: TaskConfig,
    plasticity_config,
    settings: dict,
    master_seed: int,
    *,
    quick: bool,
) -> dict:
    core = settings["core"]
    pools = _pools_for(core, master_seed)
    results = {}
    for code in core["conditions"]:
        condition_cfg = replace(cfg, connectivity=_connectivity(code))
        eta = 0.0 if code.startswith("fixed") else float(core["eta"])
        cells = []
        for seed_index in range(core["n_seeds"]):
            cell = run_cell(
                code,
                task_cfg=condition_cfg,
                bounds=plasticity_config.bounds,
                trace_config=plasticity_config.traces,
                eta=eta,
                reward_magnitude=1.0,
                reward_delay_ms=0.0,
                train_episodes=core["train_episodes"],
                checkpoints=core["eval_checkpoints"],
                pools=pools,
                seed_index=seed_index,
                substrate_seed=settings["seeds"]["substrate_seed"],
            )
            cells.append(cell)
            if not quick:
                print(
                    f"{code} seed {seed_index}: final="
                    f"{cell['final_success']:.3f} changed={cell['changed_edges']}"
                )
            gc.collect()
        results[code] = {
            "label": CONDITION_LABELS[code],
            "connectivity": _connectivity(code),
            "eta": eta,
            "train_episodes": core["train_episodes"],
            "eval_episodes": core["eval_episodes"],
            "eval_checkpoints": list(core["eval_checkpoints"]),
            "cells": cells,
        }
    return {"pools": _pool_summary(pools), "conditions": results}


def run_conventional(
    cfg: TaskConfig, settings: dict, *, quick: bool
) -> dict:
    conventional = settings["conventional"]
    cells = []
    for seed_index in range(conventional["n_seeds"]):
        result = run_conventional_condition(
            cfg,
            {
                "train_episodes": conventional["train_episodes"],
                "eval_episodes": conventional["eval_episodes"],
                "eval_checkpoints": conventional["eval_checkpoints"],
            },
            seed_index,
        )
        final = result["eval"][str(conventional["eval_checkpoints"][-1])]
        start = result["eval"]["0"]
        cells.append(
            {
                "condition": "conventional",
                "label": CONDITION_LABELS["conventional"],
                "seed_index": int(seed_index),
                "final_checkpoint": int(conventional["eval_checkpoints"][-1]),
                "final_success": final["success_rate"],
                "start_success": start["success_rate"],
                "final_selective": final["selective_rate"],
                "final_timeout": 0.0,
                "final_mean_response_ms": None,
                "train_last_window_success": round(
                    float(np.mean([item["hit"] for item in result["train"]])), 6
                ),
                "changed_edges": None,
                "silent": False,
                "no_updates": False,
                "rewards_dropped": 0,
                "eval": result["eval"],
                "train": result["train"][-200:],
            }
        )
    if not quick:
        print(
            f"conventional: final={cells[0]['final_success']:.3f} "
            "(deterministic; seeds are identical by construction)"
        )
    return {
        "label": CONDITION_LABELS["conventional"],
        "spec": {
            "information": "supervised correct-action label (privileged)",
            "matched_control": False,
        },
        "train_episodes": conventional["train_episodes"],
        "eval_episodes": conventional["eval_episodes"],
        "eval_checkpoints": list(conventional["eval_checkpoints"]),
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# robustness
# ---------------------------------------------------------------------------


def _resolve_task_config(base: TaskConfig, value: dict) -> TaskConfig:
    fields = {}
    if "n_cues" in value:
        fields["n_cues"] = int(value["n_cues"])
    if "threshold" in value:
        threshold = int(value["threshold"])
        fields["threshold"] = threshold
        fields["min_count"] = max(base.min_count, threshold)
    if not fields:
        return base
    return TaskConfig(**{**base.__dict__, **fields})


def _resolve_bounds(plasticity_config, value: dict) -> WeightBounds:
    if "lower_factor" not in value and "upper_factor" not in value:
        return plasticity_config.bounds
    return WeightBounds(
        lower_factor=float(value.get("lower_factor", 0.5)),
        upper_factor=float(value.get("upper_factor", 2.0)),
        max_abs_update_pa=value.get("max_abs_update_pa"),
    )


def _resolve_traces(plasticity_config, value: dict) -> TraceConfig:
    if "tau_e_ms" not in value:
        return plasticity_config.traces
    payload = {"traces": dict(plasticity_config.raw["traces"])}
    payload["traces"]["tau_e_ms"] = float(value["tau_e_ms"])
    return TraceConfig(payload)


def run_robustness(
    cfg: TaskConfig,
    plasticity_config,
    settings: dict,
    master_seed: int,
    *,
    quick: bool,
) -> dict:
    robustness = settings["robustness"]
    pools = _pools_for(robustness, master_seed)
    results = {}
    for axis, body in robustness["axes"].items():
        axis_rows = {}
        for value in body["values"]:
            label = str(value["label"])
            conditions = {ROBUSTNESS_PLASTIC: float(settings["core"]["eta"])}
            if body["runs_control"]:
                conditions[ROBUSTNESS_FIXED] = 0.0
            payload = {
                "parameters": dict(value),
                "conditions": {},
            }
            for code, eta in conditions.items():
                cells = []
                for seed_index in range(robustness["n_seeds"]):
                    cell = run_cell(
                        code,
                        task_cfg=_resolve_task_config(cfg, value),
                        bounds=_resolve_bounds(plasticity_config, value),
                        trace_config=_resolve_traces(plasticity_config, value),
                        eta=eta,
                        reward_magnitude=float(value.get("reward_magnitude", 1.0)),
                        reward_delay_ms=float(value.get("reward_delay_ms", 0.0)),
                        train_episodes=robustness["train_episodes"],
                        checkpoints=robustness["eval_checkpoints"],
                        pools=pools,
                        seed_index=seed_index,
                        substrate_seed=int(
                            value.get(
                                "substrate_seed",
                                settings["seeds"]["substrate_seed"],
                            )
                        ),
                    )
                    cells.append(cell)
                    gc.collect()
                payload["conditions"][code] = cells
            axis_rows[label] = payload
            if not quick:
                plastic = payload["conditions"][ROBUSTNESS_PLASTIC]
                mean = float(np.mean([cell["final_success"] for cell in plastic]))
                print(f"{axis} {label}: final={mean:.3f}")
        results[axis] = {
            "reference": body["reference"],
            "runs_control": body["runs_control"],
            "values": axis_rows,
        }
    return {"pools": _pool_summary(pools), "axes": results}


def _pool_summary(pools: dict) -> dict:
    return {
        "streams": pools["streams"],
        "disjoint_train_eval": pools["disjoint_train_eval"],
        "unique_train": pools["unique_train"],
        "unique_eval": pools["unique_eval"],
        "unique_train_jitter": pools["unique_train_jitter"],
        "unique_eval_jitter": pools["unique_eval_jitter"],
        "train_overlap_count": pools["train_overlap_count"],
    }


# ---------------------------------------------------------------------------
# determinism probe
# ---------------------------------------------------------------------------


def determinism_probe(
    cfg: TaskConfig, plasticity_config, settings: dict, master_seed: int
) -> dict:
    block = {
        "train_episodes": 4,
        "eval_episodes": 4,
        "eval_checkpoints": [0, 4],
        "n_seeds": 1,
    }
    pools = _pools_for(block, master_seed + 1)
    runs = []
    for _ in range(2):
        runs.append(
            run_cell(
                "plastic_complete",
                task_cfg=cfg,
                bounds=plasticity_config.bounds,
                trace_config=plasticity_config.traces,
                eta=float(settings["core"]["eta"]),
                reward_magnitude=1.0,
                reward_delay_ms=0.0,
                train_episodes=block["train_episodes"],
                checkpoints=block["eval_checkpoints"],
                pools=pools,
                seed_index=0,
                substrate_seed=settings["seeds"]["substrate_seed"],
            )
        )
    left, right = runs
    return {
        "identical": bool(
            left["delta_digest"] == right["delta_digest"]
            and left["final_success"] == right["final_success"]
            and left["eval"]["0"]["success_rate"]
            == right["eval"]["0"]["success_rate"]
            and left["tags_total"] == right["tags_total"]
            and left["eval"]["4"]["records"][0]["spike_hash"]
            == right["eval"]["4"]["records"][0]["spike_hash"]
        ),
        "train_episodes": block["train_episodes"],
        "eval_episodes": block["eval_episodes"],
        "delta_digest_1": left["delta_digest"],
        "delta_digest_2": right["delta_digest"],
        "final_success_1": left["final_success"],
        "final_success_2": right["final_success"],
        "tags_1": left["tags_total"],
        "tags_2": right["tags_total"],
    }


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def _values(cells, field: str) -> list[float]:
    return [float(cell[field]) for cell in cells]


def analyse_core(raw: dict, settings: dict) -> dict:
    core = settings["core"]
    statistical = settings["statistics"]
    conditions = raw["core"]["conditions"]
    summaries = {}
    for code in core["conditions"]:
        cells = conditions[code]["cells"]
        summaries[code] = {
            "label": conditions[code]["label"],
            "connectivity": conditions[code]["connectivity"],
            "eta": conditions[code]["eta"],
            "n_seeds": len(cells),
            "final_success": condition_summary(
                _values(cells, "final_success"), statistical
            ),
            "start_success": condition_summary(
                _values(cells, "start_success"), statistical
            ),
            "final_selective": condition_summary(
                _values(cells, "final_selective"), statistical
            ),
            "train_last_window_success": condition_summary(
                _values(cells, "train_last_window_success"), statistical
            ),
            "changed_edges": summary_stats(_values(cells, "changed_edges")),
            "tags_total": summary_stats(_values(cells, "tags_total")),
            "n_spikes_total": summary_stats(_values(cells, "n_spikes_total")),
            "runtime_s": summary_stats(_values(cells, "runtime_s")),
            "weights_unchanged_all": bool(
                all(cell["weights_unchanged"] for cell in cells)
            ),
            "silent_seeds": int(sum(1 for cell in cells if cell["silent"])),
            "seeds_without_updates": int(
                sum(1 for cell in cells if cell["no_updates"])
            ),
        }
    contrasts = {}
    p_values = {}
    for treatment, reference in core["contrasts"]:
        left = _values(conditions[treatment]["cells"], "final_success")
        right = _values(conditions[reference]["cells"], "final_success")
        name = f"{treatment}_minus_{reference}"
        contrasts[name] = paired_contrast(left, right, statistical)
        p_values[name] = contrasts[name]["p_value"]
    corrected = holm(p_values, statistical["alpha"])
    for name, contrast in contrasts.items():
        contrast["holm_adjusted_p"] = corrected["adjusted"][name]
        contrast["holm_rejected"] = corrected["rejected"][name]
    return {
        "conditions": summaries,
        "contrasts": contrasts,
        "multiple_comparison": corrected,
        "family": list(p_values),
    }


def analyse_conventional(raw: dict, settings: dict) -> dict:
    conventional = settings["conventional"]
    statistical = settings["statistics"]
    cells = raw["conventional"]["cells"]
    return {
        "n_seeds": len(cells),
        "note": (
            "the perceptron is deterministic, so all seeds are identical; the "
            "per-seed dispersion is zero by construction"
        ),
        "final_success": condition_summary(
            _values(cells, "final_success"), statistical
        ),
        "start_success": condition_summary(
            _values(cells, "start_success"), statistical
        ),
        "final_selective": condition_summary(
            _values(cells, "final_selective"), statistical
        ),
        "train_last_window_success": condition_summary(
            _values(cells, "train_last_window_success"), statistical
        ),
        "spec": raw["conventional"]["spec"],
        "privileged": True,
    }


def analyse_robustness(raw: dict, settings: dict) -> dict:
    statistical = settings["statistics"]
    robustness = settings["robustness"]
    output = {}
    for axis, body in robustness["axes"].items():
        reference_label = body["reference"]
        reference_row = raw["robustness"]["axes"][axis]["values"][reference_label]
        axis_out = {
            "reference": reference_label,
            "runs_control": bool(body["runs_control"]),
            "unit": (
                "ms"
                if axis in ("reward_delay_ms", "tau_e_ms")
                else "declared units"
            ),
            "values": {},
        }
        for label, row in raw["robustness"]["axes"][axis]["values"].items():
            value_out = {"parameters": row["parameters"], "conditions": {}}
            for code, cells in row["conditions"].items():
                reference_cells = reference_row["conditions"][code]
                final = _values(cells, "final_success")
                reference_final = _values(reference_cells, "final_success")
                value_out["conditions"][code] = {
                    "final_success": condition_summary(final, statistical),
                    "delta_vs_reference": round(
                        float(np.mean(final) - np.mean(reference_final)), 6
                    ),
                    "changed_edges": summary_stats(_values(cells, "changed_edges")),
                    "tags_total": summary_stats(_values(cells, "tags_total")),
                    "silent_seeds": int(
                        sum(1 for cell in cells if cell["silent"])
                    ),
                    "seeds_without_updates": int(
                        sum(1 for cell in cells if cell["no_updates"])
                    ),
                    "rewards_dropped": int(
                        sum(cell["rewards_dropped"] for cell in cells)
                    ),
                    "weights_unchanged_all": bool(
                        all(cell["weights_unchanged"] for cell in cells)
                    ),
                }
            axis_out["values"][label] = value_out
        output[axis] = axis_out
    return output


def build_analysis(raw: dict, settings: dict, figure_files: list[str]) -> dict:
    core = analyse_core(raw, settings)
    conventional = analyse_conventional(raw, settings)
    robustness = analyse_robustness(raw, settings)

    silent = []
    without_updates = []
    dropped = []
    for axis, body in robustness.items():
        for label, row in body["values"].items():
            for code, item in row["conditions"].items():
                if item["silent_seeds"]:
                    silent.append(
                        {
                            "axis": axis,
                            "value": label,
                            "condition": code,
                            "seeds": item["silent_seeds"],
                        }
                    )
                if code == ROBUSTNESS_PLASTIC and item["seeds_without_updates"]:
                    without_updates.append(
                        {
                            "axis": axis,
                            "value": label,
                            "seeds": item["seeds_without_updates"],
                        }
                    )
                if item["rewards_dropped"]:
                    dropped.append(
                        {
                            "axis": axis,
                            "value": label,
                            "condition": code,
                            "rewards_dropped": item["rewards_dropped"],
                        }
                    )
    for code, item in core["conditions"].items():
        if item["silent_seeds"]:
            silent.append(
                {"axis": "core", "value": code, "condition": code, "seeds": item["silent_seeds"]}
            )
        if code.startswith("plastic") and item["seeds_without_updates"]:
            without_updates.append(
                {"axis": "core", "value": code, "seeds": item["seeds_without_updates"]}
            )

    software_checks = {
        "core_seed_pools_disjoint": bool(raw["core"]["pools"]["disjoint_train_eval"]),
        "core_seed_pools_unique": bool(
            raw["core"]["pools"]["unique_train"]
            and raw["core"]["pools"]["unique_eval"]
            and raw["core"]["pools"]["unique_train_jitter"]
            and raw["core"]["pools"]["unique_eval_jitter"]
        ),
        "robustness_seed_pools_disjoint": (
            True
            if raw["robustness"]["pools"] is None
            else bool(raw["robustness"]["pools"]["disjoint_train_eval"])
        ),
        "fixed_conditions_weights_unchanged": bool(
            all(
                cell["weights_unchanged"]
                for code, body in raw["core"]["conditions"].items()
                if code.startswith("fixed")
                for cell in body["cells"]
            )
            and all(
                cell["weights_unchanged"]
                for axis in raw["robustness"]["axes"].values()
                for row in axis["values"].values()
                for code, cells in row["conditions"].items()
                if code.startswith("fixed")
                for cell in cells
            )
        ),
        "all_invariants": bool(
            all(
                cell["invariant_error"] is None
                for body in raw["core"]["conditions"].values()
                for cell in body["cells"]
            )
            and all(
                cell["invariant_error"] is None
                for axis in raw["robustness"]["axes"].values()
                for row in axis["values"].values()
                for cells in row["conditions"].values()
                for cell in cells
            )
        ),
        "structural_counts_immutable": bool(
            all(
                cell["structural_counts_immutable"]
                for body in raw["core"]["conditions"].values()
                for cell in body["cells"]
            )
            and all(
                cell["structural_counts_immutable"]
                for axis in raw["robustness"]["axes"].values()
                for row in axis["values"].values()
                for cells in row["conditions"].values()
                for cell in cells
            )
        ),
        "all_values_finite": bool(
            all(
                cell["all_finite"]
                for body in raw["core"]["conditions"].values()
                for cell in body["cells"]
            )
            and all(
                cell["all_finite"]
                for axis in raw["robustness"]["axes"].values()
                for row in axis["values"].values()
                for cells in row["conditions"].values()
                for cell in cells
            )
        ),
        "determinism_probe": bool(raw["determinism"]["identical"]),
        "repository_integrity": bool(raw["integrity"]["pass"]),
    }

    negative_results = []
    if silent:
        negative_results.append(
            "Some cells produced no spikes and are retained with a silent "
            f"status: {json.dumps(silent)}"
        )
    if without_updates:
        negative_results.append(
            "Some plastic cells produced no weight change and are retained: "
            f"{json.dumps(without_updates)}"
        )
    if dropped:
        negative_results.append(
            "Some declared reward delays outlived the episode and the reward "
            f"was dropped: {json.dumps(dropped)}"
        )

    facts = [
        {
            "statement": (
                "The BANC t5 graph artifact contains 683,100 verified-sign "
                "edges out of 1,535,710 total (Phase 4D)."
            ),
            "type": "data fact (repository artifact)",
        },
        {
            "statement": (
                "With eta = 0 the plastic pathway reproduces the fixed-weight "
                "simulator spike hashes exactly (Phase 5D)."
            ),
            "type": "software fact (verified test)",
        },
        {
            "statement": (
                "The fixed-weight simulator is unchanged and remains the "
                "oracle for dynamics."
            ),
            "type": "software fact (architecture constraint)",
        },
        {
            "statement": (
                "This comparison runs on a synthetic 36-node task graph; it "
                "does not read, simulate or alter the BANC connectome."
            ),
            "type": "scope fact",
        },
    ]
    assumptions = [
        "The cue -> action mapping is arbitrary and was declared before the run.",
        "Reward is an external task scalar; its magnitude has no biological unit.",
        "The eligibility trace is a model of short-term tagging with a declared "
        "time constant tau_e.",
        "Weight bounds (relative factors and the update clip) are declared "
        "modelling choices, not fitted values.",
        "Complete versus Bernoulli(0.5) wiring is a synthetic topology "
        "manipulation, not a connectome manipulation.",
        "The structural threshold is the minimum synapse count for an edge to "
        "exist (as in the BANC t1/t5/t10 artifacts); it is not a neuronal "
        "firing threshold.",
        "A conventional supervised perceptron is an information-privileged "
        "reference and is not a matched biological control.",
    ]
    limitations = [
        "Success is a conditioned response of a designated action population, "
        "not competitive action selection; the selective rate stays near or "
        "below the n_cues chance level.",
        "Random wiring has fewer edges and lower total cue input than complete "
        "wiring, so the wiring contrast confounds topology with input strength.",
        "The network is small (tens of nodes); no result here tests the BANC "
        "connectome or a whole-brain simulation.",
        "Robustness cells are descriptive. They were not corrected for multiple "
        "comparisons and are not significance claims.",
        "The unit of replication is a seed; episodes within a seed share one "
        "weight trajectory and are not independent samples.",
        "The perceptron sees the correct action label and only bounds what a "
        "supervised method can do on this task.",
        "Evaluation uses the same held-out episodes at every checkpoint and "
        "does not test unseen cue mappings.",
        "Reward is delivered after a declared delay; no biological dopamine, "
        "octopamine or serotonin dynamics were simulated.",
    ]

    files = [
        relative(CONFIG_PATH),
        relative(TASK_CONFIG_PATH),
        relative(PLASTICITY_CONFIG_PATH),
        relative(RESULTS_DIR / "comparison_raw.json"),
        relative(RESULTS_DIR / "comparison_analysis.json"),
        relative(RESULTS_DIR / "comparison_report.json"),
        "reports/PHASE_5F_COMPARATIVE_EVALUATION.md",
        "reports/PHASE_5F_COMPARATIVE_EVALUATION.json",
    ] + figure_files

    return {
        "phase": "5F",
        "generated_at_utc": raw["generated_at_utc"],
        "settings": {
            "core": settings["core"],
            "conventional": settings["conventional"],
            "robustness": {
                key: value
                for key, value in settings["robustness"].items()
                if key != "axes"
            },
            "statistics": settings["statistics"],
            "seeds": settings["seeds"],
            "axes": {
                axis: {
                    "reference": body["reference"],
                    "runs_control": body["runs_control"],
                    "labels": [str(item["label"]) for item in body["values"]],
                }
                for axis, body in settings["robustness"]["axes"].items()
            },
        },
        "core": core,
        "conventional": conventional,
        "robustness": robustness,
        "determinism": raw["determinism"],
        "software_checks": software_checks,
        "negative_results": negative_results,
        "facts": facts,
        "assumptions": assumptions,
        "limitations": limitations,
        "independence_statement": (
            "The unit of replication is a seed. No statistic pools timesteps or "
            "episodes across seeds."
        ),
        "files": files,
        "software_status": "PASS" if all(software_checks.values()) else "FAIL",
    }


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------


def _plot_conditions(analysis: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    codes = list(analysis["core"]["conditions"])
    means = [
        analysis["core"]["conditions"][code]["final_success"]["mean"]
        for code in codes
    ]
    lows = [
        analysis["core"]["conditions"][code]["final_success"]["bootstrap_ci_mean"]["low"]
        for code in codes
    ]
    highs = [
        analysis["core"]["conditions"][code]["final_success"]["bootstrap_ci_mean"]["high"]
        for code in codes
    ]
    figure, axis = plt.subplots(figsize=(7.2, 4.0))
    positions = np.arange(len(codes))
    axis.errorbar(
        positions,
        means,
        yerr=[np.subtract(means, lows), np.subtract(highs, means)],
        fmt="o",
        capsize=4,
        color="#1f4e79",
    )
    conventional = analysis["conventional"]["final_success"]["mean"]
    axis.axhline(
        conventional,
        linestyle="--",
        color="#a33",
        label=f"conventional (privileged) = {conventional:.3f}",
    )
    axis.set_xticks(positions)
    axis.set_xticklabels(codes, rotation=20, ha="right")
    axis.set_ylabel("held-out success at final checkpoint")
    axis.set_ylim(0.0, 1.05)
    axis.set_title("Phase 5F core comparison (mean and bootstrap 95% CI)")
    axis.grid(alpha=0.25)
    axis.legend(loc="lower right", fontsize=8)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_paired(raw: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    contrasts = [
        ("plastic_complete", "fixed_complete"),
        ("plastic_random", "fixed_random"),
    ]
    figure, axes = plt.subplots(1, len(contrasts), figsize=(8.4, 3.6), squeeze=False)
    for axis, (treatment, reference) in zip(axes[0], contrasts):
        left = raw["core"]["conditions"][treatment]["cells"]
        right = raw["core"]["conditions"][reference]["cells"]
        for cell_left, cell_right in zip(left, right):
            axis.plot(
                [0, 1],
                [cell_right["final_success"], cell_left["final_success"]],
                marker="o",
                color="#7a7a7a",
                linewidth=0.8,
                alpha=0.8,
            )
        axis.set_xticks([0, 1])
        axis.set_xticklabels([reference, treatment], rotation=15)
        axis.set_ylim(0.0, 1.05)
        axis.set_ylabel("held-out success")
        axis.grid(alpha=0.25)
        axis.set_title(f"{treatment} vs {reference}", fontsize=9)
    figure.suptitle("Paired seed-level responses at the final checkpoint", fontsize=10)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_axes(analysis: dict, axes: list[str], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, panels = plt.subplots(
        1, len(axes), figsize=(3.4 * len(axes), 3.4), squeeze=False
    )
    for panel, axis_name in zip(panels[0], axes):
        body = analysis["robustness"][axis_name]
        labels = list(body["values"])
        for code, colour in (
            (ROBUSTNESS_PLASTIC, "#1f4e79"),
            (ROBUSTNESS_FIXED, "#777777"),
        ):
            if code not in body["values"][labels[0]]["conditions"]:
                continue
            means = []
            lows = []
            highs = []
            for label in labels:
                item = body["values"][label]["conditions"][code]["final_success"]
                means.append(item["mean"])
                lows.append(item["bootstrap_ci_mean"]["low"])
                highs.append(item["bootstrap_ci_mean"]["high"])
            positions = np.arange(len(labels))
            panel.errorbar(
                positions,
                means,
                yerr=[np.subtract(means, lows), np.subtract(highs, means)],
                marker="o",
                capsize=3,
                color=colour,
                label=code,
            )
        panel.set_xticks(np.arange(len(labels)))
        panel.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
        panel.set_ylim(0.0, 1.05)
        panel.set_title(axis_name, fontsize=9)
        panel.grid(alpha=0.25)
    panels[0][0].set_ylabel("held-out success")
    panels[0][0].legend(fontsize=7)
    figure.suptitle(title, fontsize=10)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)


def make_figures(raw: dict, analysis: dict, settings: dict, directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    path = directory / "core_conditions.png"
    _plot_conditions(analysis, path)
    files.append(relative(path))
    path = directory / "paired_seeds.png"
    _plot_paired(raw, path)
    files.append(relative(path))
    rule_axes = [
        axis
        for axis in ("eta", "tau_e_ms", "reward_magnitude", "reward_delay_ms")
        if axis in analysis["robustness"]
    ]
    if rule_axes:
        path = directory / "robustness_rule_axes.png"
        _plot_axes(
            analysis,
            rule_axes,
            path,
            "Robustness to rule and reward parameters (descriptive)",
        )
        files.append(relative(path))
    substrate_axes = [
        axis
        for axis in ("initial_weights", "network_size", "structural_threshold")
        if axis in analysis["robustness"]
    ]
    if substrate_axes:
        path = directory / "robustness_substrate_axes.png"
        _plot_axes(
            analysis,
            substrate_axes,
            path,
            "Robustness to substrate parameters (descriptive)",
        )
        files.append(relative(path))
    return files


# ---------------------------------------------------------------------------
# markdown report
# ---------------------------------------------------------------------------


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def write_markdown_report(path: Path, raw: dict, analysis: dict) -> None:
    settings = analysis["settings"]
    core = analysis["core"]
    lines = []
    lines.append("# Phase 5F - Comparative evaluation and robustness")
    lines.append("")
    lines.append(
        "Generated by `experiments/phase_5/comparative.py` on "
        f"{raw['generated_at_utc']}. Every number below is a model output of a "
        "synthetic task."
    )
    lines.append("")
    lines.append("## Scientific status")
    lines.append("")
    lines.append(
        "The wiring factor is complete versus Bernoulli(0.5) cue -> action "
        "wiring inside a synthetic graph of tens of nodes. It is not the BANC "
        "connectome and no connectome edge was read, modified or simulated. "
        "Reward is an external scalar in task units. A weight change is the "
        "output of the declared three-factor rule and is not evidence of "
        "biological synaptic plasticity, dopamine release or learning in a fly."
    )
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        f"- Core comparison: {settings['core']['n_seeds']} independent seeds per "
        f"condition, {settings['core']['train_episodes']} training episodes, "
        f"{settings['core']['eval_episodes']} held-out episodes at checkpoints "
        f"{settings['core']['eval_checkpoints']}."
    )
    lines.append(
        f"- Robustness: {settings['robustness']['n_seeds']} seeds per cell, "
        f"{settings['robustness']['train_episodes']} training episodes, "
        f"{settings['robustness']['eval_episodes']} held-out episodes at "
        f"checkpoints {settings['robustness']['eval_checkpoints']}."
    )
    lines.append(
        "- Training and evaluation seeds come from separate SeedSequence "
        "streams declared before the run; disjointness is checked and reported."
    )
    lines.append(
        "- Evaluation uses eta = 0 on the current learned state with traces "
        "disabled, on the same held-out episodes at every checkpoint."
    )
    lines.append("- " + analysis["independence_statement"])
    lines.append(
        "- Declared paired contrasts use the same seed index in both "
        "conditions. The family is Holm-Bonferroni corrected at alpha = "
        f"{settings['statistics']['alpha']}."
    )
    lines.append("")
    lines.append("## Core comparison")
    lines.append("")
    rows = []
    for code in settings["core"]["conditions"]:
        item = core["conditions"][code]
        final = item["final_success"]
        rows.append(
            [
                code,
                item["label"],
                _fmt(final["mean"]),
                _fmt(final["sd"]),
                _fmt(final["median"]),
                f"{_fmt(final['bootstrap_ci_mean']['low'])} - "
                f"{_fmt(final['bootstrap_ci_mean']['high'])}",
                _fmt(item["start_success"]["mean"]),
                _fmt(item["final_selective"]["mean"]),
                _fmt(item["changed_edges"]["mean"], 1),
            ]
        )
    lines.append(
        _table(
            [
                "ID",
                "Condition",
                "Final mean",
                "SD",
                "Median",
                "Bootstrap 95% CI",
                "Start mean",
                "Selective",
                "Changed edges",
            ],
            rows,
        )
    )
    lines.append("")
    lines.append(
        f"Conventional supervised perceptron (privileged, not a matched "
        f"control): final mean {_fmt(analysis['conventional']['final_success']['mean'])}."
    )
    lines.append("")
    lines.append("## Declared paired contrasts")
    lines.append("")
    rows = []
    for name, item in core["contrasts"].items():
        rows.append(
            [
                name,
                _fmt(item["mean_difference"]),
                f"{_fmt(item['bootstrap_ci_mean_difference']['low'])} - "
                f"{_fmt(item['bootstrap_ci_mean_difference']['high'])}",
                _fmt(item["effect_size_dz"]),
                f"{item['n_positive']}/{item['n_pairs']}",
                _fmt(item["p_value"], 5),
                _fmt(item["holm_adjusted_p"], 5),
                str(item["holm_rejected"]),
            ]
        )
    lines.append(
        _table(
            [
                "Contrast",
                "Mean diff",
                "Bootstrap 95% CI",
                "Cohen's dz",
                "Seeds > 0",
                "p (sign flip)",
                "Holm p",
                "Rejected",
            ],
            rows,
        )
    )
    lines.append("")
    lines.append(
        "The sign-flip test is exact for the declared seed count and is "
        "two-sided. No timestep or episode is treated as an independent sample."
    )
    lines.append("")
    lines.append("## Robustness (descriptive, not corrected)")
    lines.append("")
    for axis, body in analysis["robustness"].items():
        lines.append(f"### {axis}")
        lines.append("")
        rows = []
        for label, row in body["values"].items():
            plastic = row["conditions"][ROBUSTNESS_PLASTIC]
            fixed = row["conditions"].get(ROBUSTNESS_FIXED)
            rows.append(
                [
                    label,
                    _fmt(plastic["final_success"]["mean"]),
                    _fmt(plastic["final_success"]["sd"]),
                    _fmt(plastic["final_success"]["bootstrap_ci_mean"]["low"])
                    + " - "
                    + _fmt(plastic["final_success"]["bootstrap_ci_mean"]["high"]),
                    _fmt(plastic["delta_vs_reference"]),
                    _fmt(plastic["changed_edges"]["mean"], 1),
                    plastic["silent_seeds"],
                    plastic["seeds_without_updates"],
                    "n/a" if fixed is None else _fmt(fixed["final_success"]["mean"]),
                ]
            )
        lines.append(
            _table(
                [
                    "Value",
                    "Plastic mean",
                    "SD",
                    "Bootstrap 95% CI",
                    "Delta vs reference",
                    "Changed edges",
                    "Silent seeds",
                    "No-update seeds",
                    "Fixed mean",
                ],
                rows,
            )
        )
        lines.append("")
    lines.append("## Measured facts and declared assumptions")
    lines.append("")
    rows = [
        [item["statement"], item["type"]] for item in analysis["facts"]
    ]
    lines.append(_table(["Statement", "Type"], rows))
    lines.append("")
    for item in analysis["assumptions"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Software contract checks")
    lines.append("")
    lines.append(
        _table(
            ["Check", "Passed"],
            [[name, str(ok)] for name, ok in analysis["software_checks"].items()],
        )
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="reduced budgets")
    parser.add_argument(
        "--skip-robustness", action="store_true", help="core comparison only"
    )
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args(argv)

    settings = load_comparison_config(CONFIG_PATH)
    cfg, _ = load_task_config(TASK_CONFIG_PATH)
    plasticity_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)

    if args.quick:
        settings["core"].update(
            {
                "n_seeds": 3,
                "train_episodes": 24,
                "eval_episodes": 8,
                "eval_checkpoints": [0, 24],
            }
        )
        settings["conventional"].update(
            {
                "n_seeds": 3,
                "train_episodes": 24,
                "eval_episodes": 8,
                "eval_checkpoints": [0, 24],
            }
        )
        settings["robustness"].update(
            {
                "n_seeds": 2,
                "train_episodes": 16,
                "eval_episodes": 8,
                "eval_checkpoints": [0, 16],
            }
        )
    if args.skip_robustness:
        settings["robustness"]["axes"] = {}

    master = int(settings["seeds"]["master_seed"])
    started = time.perf_counter()
    raw = {
        "phase": "5F",
        "status": "running",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": {
            "quick": bool(args.quick),
            "skip_robustness": bool(args.skip_robustness),
            "module": "experiments.phase_5.comparative",
        },
        "software": software_versions(),
        "config": {
            "comparison_path": relative(CONFIG_PATH),
            "comparison_sha256": sha256_file(CONFIG_PATH),
            "task_path": relative(TASK_CONFIG_PATH),
            "task_sha256": sha256_file(TASK_CONFIG_PATH),
            "plasticity_path": relative(PLASTICITY_CONFIG_PATH),
            "plasticity_sha256": sha256_file(PLASTICITY_CONFIG_PATH),
        },
        "settings": {
            "core": settings["core"],
            "conventional": settings["conventional"],
            "robustness": settings["robustness"],
            "statistics": settings["statistics"],
            "seeds": settings["seeds"],
        },
        "task": cfg.describe(),
        "plasticity": plasticity_config.describe(),
        "process_memory_start": process_memory(),
    }

    raw["core"] = run_core(
        cfg, plasticity_config, settings, master, quick=args.quick
    )
    raw["conventional"] = run_conventional(cfg, settings, quick=args.quick)
    raw["robustness"] = (
        run_robustness(
            cfg, plasticity_config, settings, master, quick=args.quick
        )
        if settings["robustness"]["axes"]
        else {"pools": None, "axes": {}}
    )
    raw["determinism"] = determinism_probe(
        cfg, plasticity_config, settings, master
    )
    raw["integrity"] = integrity_snapshot()
    raw["process_memory_end"] = process_memory()

    analysis = build_analysis(raw, settings, figure_files=[])
    if not args.skip_figures:
        analysis["files"].extend(
            make_figures(raw, analysis, settings, FIGURES_DIR)
        )
    raw["status"] = "complete"
    raw["runtime_s"] = round(time.perf_counter() - started, 2)

    suffix = "_quick" if args.quick else ""
    raw_path = RESULTS_DIR / f"comparison_raw{suffix}.json"
    analysis_path = RESULTS_DIR / f"comparison_analysis{suffix}.json"
    report_json = RESULTS_DIR / f"comparison_report{suffix}.json"
    write_json(raw_path, raw)
    write_json(analysis_path, analysis)
    write_json(report_json, analysis)
    if not args.quick:
        write_markdown_report(
            PROJECT_ROOT / "reports" / "PHASE_5F_COMPARATIVE_EVALUATION.md",
            raw,
            analysis,
        )
        write_json(
            PROJECT_ROOT / "reports" / "PHASE_5F_COMPARATIVE_EVALUATION.json",
            analysis,
        )

    print(
        json.dumps(
            {
                "raw": relative(raw_path),
                "analysis": relative(analysis_path),
                "software_status": analysis["software_status"],
                "software_checks": analysis["software_checks"],
                "core": {
                    code: analysis["core"]["conditions"][code]["final_success"]["mean"]
                    for code in analysis["core"]["conditions"]
                },
                "contrasts": {
                    name: {
                        "mean_difference": item["mean_difference"],
                        "holm_p": item["holm_adjusted_p"],
                        "rejected": item["holm_rejected"],
                    }
                    for name, item in analysis["core"]["contrasts"].items()
                },
                "runtime_s": raw["runtime_s"],
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
