"""Phase 4H.2 — population size and selection sensitivity.

Executes the size x rule surface defined in
``reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`` section 4: driven-group sizes
8/16/32/48/64/96/128 under seven selection rules, plus the JUMP pool-imbalance
null model. One comparison is pre-registered as confirmatory: at size 64,
``connectivity_ranked`` against the 100 Phase 4H.1 family A draws. Every other
comparison is descriptive and labelled exploratory.

Usage:
    python -m experiments.phase_4h.population_sensitivity
    python -m experiments.phase_4h.population_sensitivity --sizes 8,64 --draws 2
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_4h import common  # noqa: E402
from experiments.phase_4h.control_draws import (  # noqa: E402
    decoder_scores,
    flat_metrics,
)

PROTOCOL = PROJECT_ROOT / "reports" / "PHASE_4H_EXPERIMENTAL_PROTOCOL.md"
PROTOCOL_SHA256 = "7c511c5a9cfb64262e424ab566743ff2b25d86e2c51a12f5a77057dd3e5e6b05"
OUTPUT = common.RESULTS / "population_sensitivity.json"
CHECKPOINT = common.RESULTS / "population_sensitivity.checkpoint.jsonl"
REFERENCE_RESULT = common.RESULTS / "control_draws.json"

SIZES = (8, 16, 32, 48, 64, 96, 128)
RULES = (
    "connectivity_ranked",
    "random_eligible",
    "in_degree_ranked",
    "out_degree_ranked",
    "combined_degree_ranked",
    "verified_excitatory_all_classes",
    "annotation_stratified_random",
)
RULE_ORDINAL = {name: index + 1 for index, name in enumerate(RULES)}
RANDOM_RULES = ("random_eligible", "annotation_stratified_random")
DRAWS_PER_CELL = 10
N_NULL_SUBSETS = 10_000
NULL_SUBSET_SIZE = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rule_seed(rule: str, size: int, draw_index: int) -> int:
    return (
        common.SEED_ROOT
        + 200_000
        + 1000 * int(size)
        + 10 * RULE_ORDINAL[rule]
        + int(draw_index)
    )


# ---------------------------------------------------------------------------
# selection rules
# ---------------------------------------------------------------------------


def ranked_selection(world: common.World, rule: str, size: int) -> np.ndarray:
    if rule in {"connectivity_ranked", "verified_excitatory_all_classes"}:
        scores = world.scores
    elif rule == "in_degree_ranked":
        scores = world.in_degree.astype(np.float64)
    elif rule == "out_degree_ranked":
        scores = world.out_degree.astype(np.float64)
    elif rule == "combined_degree_ranked":
        scores = (world.in_degree + world.out_degree).astype(np.float64)
    else:
        raise ValueError(f"unknown ranked rule {rule!r}")
    pool = (
        world.eligible_all_exc
        if rule == "verified_excitatory_all_classes"
        else world.eligible_vnc
    )
    return common.rank_top_from(np.flatnonzero(pool), scores, size)


def _labels(world: common.World) -> np.ndarray:
    values = world.nodes["cell_class"].to_numpy(dtype=object)
    return np.asarray(
        ["<missing>" if value is None or value != value else str(value) for value in values],
        dtype=object,
    )


def annotation_draw(
    world: common.World, size: int, rng: np.random.Generator
) -> tuple[np.ndarray, dict]:
    labels = _labels(world)
    ranked = ranked_selection(world, "connectivity_ranked", size)
    need: dict[str, int] = {}
    for value in labels[ranked]:
        need[value] = need.get(value, 0) + 1
    c_mask = np.zeros(world.n_nodes, dtype=bool)
    c_mask[world.candidate_c] = True
    pool = np.flatnonzero(world.eligible_vnc & ~c_mask)
    chosen: list[int] = []
    shortages: dict[str, int] = {}
    for key in sorted(need):
        members = pool[labels[pool] == key]
        take = min(need[key], members.size)
        if take < need[key]:
            shortages[key] = int(need[key] - take)
        if take:
            chosen.extend(int(v) for v in rng.choice(members, size=take, replace=False))
    top_up = 0
    if len(chosen) < size:
        used = set(chosen)
        refill = np.asarray([int(v) for v in pool if int(v) not in used], dtype=np.int64)
        shortfall = size - len(chosen)
        if refill.size < shortfall:
            raise RuntimeError("annotation-stratified pool cannot reach the size")
        chosen.extend(int(v) for v in rng.choice(refill, size=shortfall, replace=False))
        top_up = int(shortfall)
    return np.sort(np.asarray(chosen, dtype=np.int64)), {
        "stratum_allocation": {key: int(value) for key, value in sorted(need.items())},
        "stratum_shortages": shortages,
        "top_up_neurons": top_up,
    }


def random_eligible(world: common.World, size: int, rng: np.random.Generator) -> np.ndarray:
    c_mask = np.zeros(world.n_nodes, dtype=bool)
    c_mask[world.candidate_c] = True
    pool = np.flatnonzero(world.eligible_vnc & ~c_mask)
    if pool.size < size:
        raise RuntimeError("random_eligible pool cannot reach the size")
    return np.sort(np.asarray(rng.choice(pool, size=size, replace=False), dtype=np.int64))


def select(
    world: common.World, rule: str, size: int, draw_index: int
) -> tuple[np.ndarray, dict]:
    seed = rule_seed(rule, size, draw_index)
    rng = np.random.default_rng(seed)
    meta = {"rule": rule, "size": int(size), "draw_index": int(draw_index), "seed": seed}
    if rule in {"connectivity_ranked", "in_degree_ranked", "out_degree_ranked",
                "combined_degree_ranked", "verified_excitatory_all_classes"}:
        chosen = ranked_selection(world, rule, size)
        meta.update(
            {
                "pool": "vnc_intrinsic_eligible"
                if rule != "verified_excitatory_all_classes"
                else "all_verified_excitatory_non_motor",
                "tie_break": "ascending graph node index",
                "deterministic": True,
            }
        )
    elif rule == "random_eligible":
        chosen = random_eligible(world, size, rng)
        meta.update(
            {
                "pool": "vnc_intrinsic_eligible_excluding_c",
                "replacement": False,
                "deterministic": True,
            }
        )
    elif rule == "annotation_stratified_random":
        chosen, extra = annotation_draw(world, size, rng)
        meta.update(
            {
                "pool": "vnc_intrinsic_eligible_excluding_c",
                "stratified_by": "cell_class",
                "allocation": "ranked pool composition at the same size",
                "deterministic": True,
                **extra,
            }
        )
    else:
        raise ValueError(f"unknown rule {rule!r}")
    if chosen.size != size:
        raise RuntimeError(f"rule {rule} size {size} selected {chosen.size}")
    if np.unique(chosen).size != chosen.size:
        raise RuntimeError(f"rule {rule} size {size} selected duplicates")
    if np.any(world.populations.motor_mask[chosen]):
        raise RuntimeError(f"rule {rule} size {size} selected a motor neuron")
    if not np.all(world.eligible_all_exc[chosen]):
        raise RuntimeError(f"rule {rule} size {size} selected a non-excitatory neuron")
    return chosen, meta


# ---------------------------------------------------------------------------
# JUMP pool null model
# ---------------------------------------------------------------------------


def _null_summary(observed: float, null: np.ndarray) -> dict:
    return {
        "n_subsets": int(null.size),
        "subset_size": NULL_SUBSET_SIZE,
        "mean": round(float(null.mean()), 6),
        "median": round(float(np.median(null)), 6),
        "q95": round(float(np.quantile(null, 0.95)), 6),
        "q99": round(float(np.quantile(null, 0.99)), 6),
        "max": round(float(null.max()), 6),
        "p_greater": round(
            (1.0 + float(np.count_nonzero(null >= observed))) / (1.0 + null.size), 8
        ),
        "percentile": round(float(np.count_nonzero(null < observed)) / null.size, 6),
    }


def jump_null(
    world: common.World,
    motor_counts: np.ndarray,
    jump_active_neurons: int,
    jump_active_fraction: float,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed + 500_000)
    motor_n = motor_counts.size
    motor_index = np.argpartition(rng.random((N_NULL_SUBSETS, motor_n)), NULL_SUBSET_SIZE, axis=1)[
        :, :NULL_SUBSET_SIZE
    ]
    motor_fractions = (motor_counts[motor_index] > 0).mean(axis=1)

    motor_mask = np.asarray(world.populations.motor_mask, dtype=bool)
    leg_mask = np.asarray(world.populations.mask("LEFT"), dtype=bool) | np.asarray(
        world.populations.mask("RIGHT"), dtype=bool
    )
    leg_in_motor = leg_mask[np.flatnonzero(motor_mask)]
    leg_counts = np.asarray(motor_counts, dtype=np.int64)[leg_in_motor]
    leg_n = leg_counts.size
    if leg_n >= NULL_SUBSET_SIZE:
        leg_index = np.argpartition(
            rng.random((N_NULL_SUBSETS, leg_n)), NULL_SUBSET_SIZE, axis=1
        )[:, :NULL_SUBSET_SIZE]
        leg_fractions = (leg_counts[leg_index] > 0).mean(axis=1)
        leg_block = _null_summary(jump_active_fraction, leg_fractions)
    else:
        leg_block = {"note": "leg motor pool smaller than the subset size"}
    return {
        "observed_jump_active_fraction": round(float(jump_active_fraction), 6),
        "observed_jump_active_neurons": int(jump_active_neurons),
        "motor_null_20_neuron_subsets_of_805": _null_summary(
            jump_active_fraction, motor_fractions
        ),
        "leg_null_20_neuron_subsets_of_leg_motor_pool": leg_block,
        "pool_sizes": {
            "motor": int(motor_n),
            "leg_left_right": int(leg_n),
            "JUMP": int(world.populations.mask("JUMP").sum()),
        },
        "activation_neurons_required": {
            "JUMP": int(math.ceil(0.20 * int(world.populations.mask("JUMP").sum()))),
            "LEFT": int(math.ceil(0.20 * int(world.populations.mask("LEFT").sum()))),
            "RIGHT": int(math.ceil(0.20 * int(world.populations.mask("RIGHT").sum()))),
        },
    }


def pool_metrics(metrics: dict, duration_ms: float) -> dict:
    seconds = duration_ms / 1000.0
    out = {}
    for action in common.ACTION_POPULATIONS:
        block = metrics["actions"][action]
        size = int(block["size"])
        out[action] = {
            **block,
            "mean_rate_hz": round(block["spikes"] / size / seconds, 6) if size else 0.0,
            "peak_rate_hz": round(
                block["peak_window_active_fraction"] * size / 0.05 / 1.0, 6
            ),
            "required_active_neurons_at_0_20": int(math.ceil(0.20 * size)),
            "active_fraction_over_threshold": round(
                block["active_fraction"] / 0.20, 6
            ),
        }
    return out


# ---------------------------------------------------------------------------
# run and checkpoint
# ---------------------------------------------------------------------------


def run_cell_run(world: common.World, rule: str, size: int, draw_index: int) -> dict:
    chosen, meta = select(world, rule, size, draw_index)
    result = common.execute(
        world,
        chosen,
        seed=meta["seed"],
        label=f"4H2_{rule}_{size}_{draw_index}",
    )
    scores = decoder_scores(result)
    flat = flat_metrics(result["metrics"], scores)
    flat["motor_spikes"] = flat["P1_motor_spikes"]
    flat["jump_windows"] = flat["P2_jump_windows"]
    counts = np.asarray(result["motor_spike_counts"], dtype=np.int64)
    jump_fraction = result["metrics"]["actions"]["JUMP"]["active_fraction"]
    return {
        "kind": "run",
        "rule": rule,
        "size": int(size),
        "draw_index": int(draw_index),
        "seed": int(meta["seed"]),
        "selection": meta,
        "node_indices": [int(v) for v in chosen],
        "indices_sha256": common.digest_array(chosen),
        "metrics": result["metrics"],
        "flat": flat,
        "pool_metrics": pool_metrics(result["metrics"], common.DURATION_MS),
        "motor_spike_counts": [int(v) for v in counts],
        "jump_null": jump_null(
            world,
            counts,
            int(result["metrics"]["actions"]["JUMP"]["active_neurons"]),
            jump_fraction,
            meta["seed"],
        ),
        "spike_hash": result["spike_hash"],
        "decision_hash": result["decision_hash"],
        "decision_states": [
            {
                "window_start_ms": item["window_start_ms"],
                "decoded_state": item["decoded_state"],
            }
            for item in result["decisions"]
        ],
        "simulation": result["simulation"],
        "memory": result["memory"],
        "process_memory": result.get("process_memory"),
        "wall_time_s": result["wall_time_s"],
    }


def load_checkpoint(path: Path) -> tuple[list[dict], int]:
    if not path.is_file():
        return [], 0
    records, skipped = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            skipped += 1
    return records, skipped


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


SURFACE_ENDPOINTS = (
    "total_spikes",
    "stimulated_spikes",
    "non_stimulated_spikes",
    "active_neurons",
    "motor_spikes",
    "motor_active_neurons",
    "motor_active_fraction",
    "peak_motor_window_spikes",
    "left_spikes",
    "right_spikes",
    "jump_spikes",
    "left_active_fraction",
    "right_active_fraction",
    "jump_active_fraction",
    "left_peak_window_active_fraction",
    "right_peak_window_active_fraction",
    "jump_peak_window_active_fraction",
    "left_windows",
    "right_windows",
    "jump_windows",
    "neutral_windows",
    "non_neutral_windows",
    "time_to_first_motor_spike_ms",
    "post_stimulation_spikes",
)


def _stats(values: list) -> dict:
    present = [float(value) for value in values if value is not None]
    if not present:
        return {"n": 0, "n_missing": len(values)}
    block = common.summary_stats(present)
    block["n_missing"] = len(values) - len(present)
    return block


def cell_summary(runs: list[dict]) -> dict:
    block = {
        "n_runs": len(runs),
        "seeds": [run["seed"] for run in runs],
        "endpoints": {},
    }
    for key in SURFACE_ENDPOINTS:
        block["endpoints"][key] = _stats([run["flat"][key] for run in runs])
    pooled = {
        key: _stats([run["metrics"]["actions"][key]["active_neurons"] for run in runs])
        for key in common.ACTION_POPULATIONS
    }
    block["endpoints"]["jump_active_neurons"] = pooled["JUMP"]
    block["endpoints"]["left_active_neurons"] = pooled["LEFT"]
    block["endpoints"]["right_active_neurons"] = pooled["RIGHT"]
    block["jump_detected_runs"] = int(
        sum(1 for run in runs if run["metrics"]["jump_windows"] > 0)
    )
    block["jump_null_percentile"] = _stats(
        [
            run["jump_null"]["motor_null_20_neuron_subsets_of_805"]["percentile"]
            for run in runs
        ]
    )
    block["jump_null_p_greater"] = _stats(
        [
            run["jump_null"]["motor_null_20_neuron_subsets_of_805"]["p_greater"]
            for run in runs
        ]
    )
    block["leg_null_percentile"] = _stats(
        [
            run["jump_null"]["leg_null_20_neuron_subsets_of_leg_motor_pool"].get(
                "percentile"
            )
            for run in runs
            if "percentile"
            in run["jump_null"]["leg_null_20_neuron_subsets_of_leg_motor_pool"]
        ]
    )
    block["mean_wall_time_s"] = round(
        float(np.mean([run["wall_time_s"] for run in runs])), 4
    )
    return block


def contrast(observed: list[float], control: list[float], label: str) -> dict:
    observed_values = [float(v) for v in observed if v is not None]
    control_values = [float(v) for v in control if v is not None]
    if not observed_values or not control_values:
        return {"label": label, "note": "missing values"}
    observed_mean = float(statistics.fmean(observed_values))
    control_mean = float(statistics.fmean(control_values))
    bootstrap = common.bootstrap_ci(control_values)
    return {
        "label": label,
        "observed_mean": round(observed_mean, 6),
        "control_mean": round(control_mean, 6),
        "difference": round(observed_mean - control_mean, 6),
        "control_mean_ci": bootstrap,
        "empirical_percentile": round(
            common.empirical_percentile(observed_mean, control_values), 6
        ),
        "p_one_sided_greater": round(
            common.empirical_p_greater(observed_mean, control_values), 8
        ),
        "cliffs_delta": round(common.cliffs_delta(observed_mean, control_values), 6),
    }


def cell_contrasts(cells: dict, sizes) -> dict:
    out = {}
    for rule in RULES:
        if rule == "random_eligible":
            continue
        out[rule] = {}
        for size in sizes:
            cell = cells.get(rule, {}).get(size)
            control = cells.get("random_eligible", {}).get(size)
            if not cell or not control:
                continue
            out[rule][size] = {}
            for key in ("motor_spikes", "jump_windows", "total_spikes"):
                observed = [run["flat"][key] for run in cell["runs"]]
                controls = [run["flat"][key] for run in control["runs"]]
                out[rule][size][key] = contrast(
                    observed,
                    controls,
                    "exploratory: rule vs size-matched random_eligible draws",
                )
    return out


def confirmatory_block(cells: dict) -> dict:
    block = {
        "comparison": (
            "size 64 connectivity_ranked (the Phase 4G condition C candidate "
            "set) versus the 100 Phase 4H.1 family A draws"
        ),
        "control_family": "A_vnc_intrinsic_random (4H.1)",
        "control_source": str(REFERENCE_RESULT.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "alpha": 0.05,
        "multiple_comparison": "Holm-Bonferroni over the two endpoints",
    }
    ranked_runs = cells.get("connectivity_ranked", {}).get(64, {}).get("runs", [])
    if not ranked_runs:
        block["note"] = "size 64 connectivity_ranked run missing"
        return block
    ranked = ranked_runs[0]
    if not REFERENCE_RESULT.is_file():
        block["note"] = "4H.1 result file missing; confirmatory test unavailable"
        return block
    reference = json.loads(REFERENCE_RESULT.read_text(encoding="utf-8"))
    family_a_draws = [
        item
        for item in reference.get("draws", [])
        if item.get("family") == "A_vnc_intrinsic_random"
    ]
    if not family_a_draws:
        block["note"] = "4H.1 family A draws missing; confirmatory test unavailable"
        return block
    values = {
        "P1_motor_spikes": [
            int(item["flat"]["P1_motor_spikes"]) for item in family_a_draws
        ],
        "P2_jump_windows": [
            int(item["flat"]["P2_jump_windows"]) for item in family_a_draws
        ],
    }
    pvalues = {}
    for endpoint in ("P1_motor_spikes", "P2_jump_windows"):
        observed = (
            ranked["flat"]["P1_motor_spikes"]
            if endpoint == "P1_motor_spikes"
            else ranked["flat"]["P2_jump_windows"]
        )
        block[endpoint] = {
            "observed": int(observed),
            "control_n": len(values[endpoint]),
            "control_median": round(float(np.median(values[endpoint])), 6),
            "control_max": int(np.max(values[endpoint])),
            "empirical_percentile": round(
                common.empirical_percentile(observed, values[endpoint]), 6
            ),
            "p_one_sided_greater": round(
                common.empirical_p_greater(observed, values[endpoint]), 8
            ),
        }
        pvalues[endpoint] = block[endpoint]["p_one_sided_greater"]
    block["holm"] = common.holm(pvalues)
    block["any_confirmatory_difference"] = any(block["holm"]["rejected"].values())
    block["control_n_requested"] = 100
    block["control_complete"] = len(family_a_draws) == 100
    if not block["control_complete"]:
        block["note"] = (
            "4H.1 family A is incomplete; the comparison is reported but is "
            "not treated as the pre-registered confirmatory test"
        )
    else:
        block["note"] = (
            "The same test is also reported in the 4H.1 result file; it is "
            "repeated here for the size-sensitivity question and is not "
            "counted twice."
        )
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default=",".join(str(v) for v in SIZES))
    parser.add_argument("--draws", type=int, default=DRAWS_PER_CELL)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    sizes = [int(item) for item in args.sizes.split(",") if item.strip()]
    if any(size not in SIZES for size in sizes):
        parser.error(f"sizes must be drawn from {SIZES}")
    if not 1 <= args.draws <= DRAWS_PER_CELL:
        parser.error(f"--draws must lie in [1, {DRAWS_PER_CELL}]")
    checkpoint_path = Path(args.checkpoint).resolve()
    output_path = Path(args.output).resolve()

    started = utc_now()
    clock = time.perf_counter()
    protocol_hash = common.sha256_file(PROTOCOL)
    if protocol_hash != PROTOCOL_SHA256:
        raise SystemExit(
            "4H.2 stopped: the frozen protocol hash does not match "
            f"(expected {PROTOCOL_SHA256}, got {protocol_hash})"
        )
    before_integrity = common.integrity_snapshot()
    print("loading BANC world ...", flush=True)
    world = common.load_world()

    reference = None
    if REFERENCE_RESULT.is_file():
        payload = json.loads(REFERENCE_RESULT.read_text(encoding="utf-8"))
        reference = payload.get("reference")
    if reference is None:
        print("running condition C reference ...", flush=True)
        result = common.execute(
            world, world.candidate_c, seed=common.SEED_ROOT, label="4H2_reference_C"
        )
        reference = {
            "label": "4H2_reference_C",
            "spike_hash": result["spike_hash"],
            "flat": {
                **flat_metrics(result["metrics"], decoder_scores(result)),
                "motor_spikes": result["metrics"]["motor"]["spikes"],
                "jump_windows": result["metrics"]["jump_windows"],
            },
            "metrics": result["metrics"],
            "wall_time_s": result["wall_time_s"],
        }

    existing, corrupt_lines = load_checkpoint(checkpoint_path)
    completed = {
        (item["rule"], int(item["size"]), int(item["draw_index"]))
        for item in existing
        if item["kind"] in {"run", "failure"}
    }
    failures = [
        {
            "rule": item["rule"],
            "size": int(item["size"]),
            "draw_index": int(item["draw_index"]),
            "seed": item["seed"],
            "error": item.get("error"),
        }
        for item in existing
        if item["kind"] == "failure"
    ]
    total = sum(
        args.draws if rule in RANDOM_RULES else 1 for rule in RULES for _ in sizes
    )
    done = 0
    for rule in RULES:
        draws = args.draws if rule in RANDOM_RULES else 1
        for size in sizes:
            for draw_index in range(draws):
                done += 1
                if (rule, int(size), draw_index) in completed:
                    continue
                try:
                    record = run_cell_run(world, rule, size, draw_index)
                except Exception as exc:
                    failure = {
                        "kind": "failure",
                        "rule": rule,
                        "size": int(size),
                        "draw_index": int(draw_index),
                        "seed": rule_seed(rule, size, draw_index),
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
                    common.jsonl_append(checkpoint_path, failure)
                    failures.append(
                        {
                            key: failure[key]
                            for key in ("rule", "size", "draw_index", "seed", "error")
                        }
                    )
                    print(f"FAIL {rule} {size} {draw_index}: {exc}", flush=True)
                    continue
                common.jsonl_append(checkpoint_path, record)
                if done % 10 == 0:
                    print(
                        f"[{done}/{total}] {rule} size={size} draw={draw_index} "
                        f"motor={record['flat']['motor_spikes']} "
                        f"jump={record['flat']['jump_windows']} "
                        f"({record['wall_time_s']} s)",
                        flush=True,
                    )

    records, _ = load_checkpoint(checkpoint_path)
    selected = [
        item
        for item in records
        if item["kind"] == "run" and int(item["size"]) in sizes
    ]
    cells: dict[str, dict[int, dict]] = {}
    for rule in RULES:
        cells[rule] = {}
        for size in sizes:
            runs = [
                item for item in selected if item["rule"] == rule and item["size"] == size
            ]
            cells[rule][size] = {
                "summary": cell_summary(runs) if runs else {"n_runs": 0},
                "runs": runs,
                "n_failed": sum(
                    1
                    for item in records
                    if item["kind"] == "failure"
                    and item["rule"] == rule
                    and int(item["size"]) == size
                ),
            }

    for rule in RULES:
        for size in sizes:
            if rule == "connectivity_ranked" and size == 64 and cells[rule][size]["runs"]:
                chosen = np.asarray(
                    cells[rule][size]["runs"][0]["node_indices"], dtype=np.int64
                )
                cells[rule][size]["matches_condition_c"] = bool(
                    np.array_equal(np.sort(chosen), np.sort(world.candidate_c))
                )

    surface_table = {
        rule: [
            {
                "size": size,
                "n_runs": cells[rule][size]["summary"].get("n_runs", 0),
                "total_spikes": cells[rule][size]["summary"]
                .get("endpoints", {})
                .get("total_spikes", {})
                .get("mean"),
                "motor_spikes": cells[rule][size]["summary"]
                .get("endpoints", {})
                .get("motor_spikes", {})
                .get("mean"),
                "jump_windows": cells[rule][size]["summary"]
                .get("endpoints", {})
                .get("jump_windows", {})
                .get("mean"),
                "jump_detected_runs": cells[rule][size]["summary"].get(
                    "jump_detected_runs", 0
                ),
            }
            for size in sizes
        ]
        for rule in RULES
    }

    pooled_sizes = {
        action: int(np.asarray(world.populations.mask(action), bool).sum())
        for action in common.ACTION_POPULATIONS
    }
    motor_mask = np.asarray(world.populations.motor_mask, dtype=bool)
    leg_mask = np.asarray(world.populations.mask("LEFT"), bool) | np.asarray(
        world.populations.mask("RIGHT"), bool
    )
    pooled_sizes["motor"] = int(motor_mask.sum())
    pooled_sizes["leg_left_right"] = int(leg_mask.sum())
    assigned = np.zeros(world.n_nodes, dtype=bool)
    for action in common.ACTION_POPULATIONS:
        assigned |= np.asarray(world.populations.mask(action), bool)
    pooled_sizes["unassigned"] = int((motor_mask & ~assigned).sum())

    after_integrity = common.integrity_snapshot()
    payload = {
        "phase": "4H.2",
        "title": "Population size and selection sensitivity",
        "generated_at_utc": utc_now(),
        "started_at_utc": started,
        "protocol": {
            "path": str(PROTOCOL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": protocol_hash,
            "matches_frozen_hash": True,
        },
        "software": common.software_versions(),
        "world": world.describe(),
        "config_sha256": world.signature["config_sha256"],
        "design": {
            "sizes": sizes,
            "rules": list(RULES),
            "random_rules_draws": args.draws,
            "ranked_rules_draws": 1,
            "seed_rule": (
                "20261109 + 200000 + 1000*size + 10*rule_ordinal + draw_index; "
                "rule ordinals follow the order of RULES"
            ),
            "rule_ordinals": RULE_ORDINAL,
            "tie_break": "ascending graph node index",
            "pool_exclusion": (
                "random rules draw from the eligible VNC-intrinsic pool with the "
                "64 condition C neurons removed, matching 4H.1 family A"
            ),
            "fixed_conditions": {
                "graph": "BANC v888 threshold 5",
                "sign_policy": "verified-only, unknown excluded",
                "weight_transform": "min(5*count^0.75, 300 pA)",
                "stimulation_amplitude_pa": common.STIM_CURRENT_PA,
                "stimulation_window_ms": [common.STIM_START_MS, common.STIM_END_MS],
                "dt_ms": common.DT_MS,
                "duration_ms": common.DURATION_MS,
                "decoder": "Phase 4F unchanged",
            },
            "confirmatory_comparison": (
                "one: size 64 connectivity_ranked versus 100 family A draws"
            ),
            "exploratory_note": (
                "all other size and rule comparisons are descriptive; degree is "
                "a structural graph property and is not given a biological "
                "interpretation"
            ),
        },
        "reference": reference,
        "pool_sizes": pooled_sizes,
        "jump_pool_analysis": {
            "pool_imbalance": {
                "LEFT": pooled_sizes["LEFT"],
                "RIGHT": pooled_sizes["RIGHT"],
                "JUMP": pooled_sizes["JUMP"],
                "one_active_neuron_fraction": {
                    "LEFT": round(1 / pooled_sizes["LEFT"], 6),
                    "RIGHT": round(1 / pooled_sizes["RIGHT"], 6),
                    "JUMP": round(1 / pooled_sizes["JUMP"], 6),
                },
                "active_neurons_needed_at_0_20": {
                    "LEFT": int(math.ceil(0.20 * pooled_sizes["LEFT"])),
                    "RIGHT": int(math.ceil(0.20 * pooled_sizes["RIGHT"])),
                    "JUMP": int(math.ceil(0.20 * pooled_sizes["JUMP"])),
                },
            },
            "null_model": (
                "per run: JUMP active fraction against 10,000 seeded 20-neuron "
                "subsets of the 805 motor neurons, and against 10,000 seeded "
                "20-neuron subsets of the 371 leg (LEFT+RIGHT) motor neurons"
            ),
            "n_subsets": N_NULL_SUBSETS,
            "per_cell": {
                rule: {
                    str(size): {
                        "jump_null_percentile": cells[rule][size]["summary"].get(
                            "jump_null_percentile", {}
                        ),
                        "jump_null_p_greater": cells[rule][size]["summary"].get(
                            "jump_null_p_greater", {}
                        ),
                        "leg_null_percentile": cells[rule][size]["summary"].get(
                            "leg_null_percentile", {}
                        ),
                    }
                    for size in sizes
                }
                for rule in RULES
            },
        },
        "surface_table": surface_table,
        "cells": {
            rule: {
                str(size): {
                    "summary": cells[rule][size]["summary"],
                    "n_failed": cells[rule][size]["n_failed"],
                    **(
                        {"matches_condition_c": cells[rule][size]["matches_condition_c"]}
                        if "matches_condition_c" in cells[rule][size]
                        else {}
                    ),
                }
                for size in sizes
            }
            for rule in RULES
        },
        "runs": selected,
        "failures": failures,
        "exploratory_contrasts": cell_contrasts(cells, sizes),
        "confirmatory": confirmatory_block(cells),
        "checkpoint": {
            "path": str(checkpoint_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "records_loaded": len(existing),
            "corrupt_lines_skipped": corrupt_lines,
        },
        "runtime": {
            "assembly_wall_time_s": round(time.perf_counter() - clock, 3),
            "sum_run_wall_time_s": round(
                float(np.sum([run["wall_time_s"] for run in selected])), 3
            )
            if selected
            else None,
            "mean_run_wall_time_s": round(
                float(np.mean([run["wall_time_s"] for run in selected])), 4
            )
            if selected
            else None,
            "max_retained_memory_mb": round(
                float(np.max([run["memory"]["retained_arrays_mb"] for run in selected])), 4
            )
            if selected
            else None,
            "estimated_steps_per_run": int(common.DURATION_MS / common.DT_MS),
            "execution_note": (
                "the surface may be assembled from a resumed checkpoint; "
                "sum_run_wall_time_s is the summed duration of the 175 stored "
                "runs, while assembly_wall_time_s covers only this invocation"
            ),
        },
        "integrity": {
            "before": before_integrity,
            "after": after_integrity,
            "protected_unchanged": before_integrity["pass"] and after_integrity["pass"],
        },
        "limitations": [
            "Ranked rules are deterministic and run once, so they carry no "
            "sampling uncertainty; only random rules quantify variability.",
            "Degree is a structural property of the threshold-5 graph; no "
            "biological meaning is assigned to in-, out- or combined degree.",
            "The eligible pool is fixed by the Phase 4F verified-excitatory "
            "policy; unverified or inhibitory neurons are outside this surface.",
            "The JUMP null model reuses motor spike counts from one run and "
            "tests pool size and identity, not biological recruitment.",
            "A single pre-registered confirmatory comparison is made at size 64; "
            "the rest of the surface is exploratory and not corrected.",
        ],
    }
    common.write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "completed_runs": len(selected),
                "failed_runs": len(failures),
                "confirmatory": {
                    "P1": payload["confirmatory"]
                    .get("P1_motor_spikes", {})
                    .get("p_one_sided_greater"),
                    "P2": payload["confirmatory"]
                    .get("P2_jump_windows", {})
                    .get("p_one_sided_greater"),
                    "any": payload["confirmatory"].get("any_confirmatory_difference"),
                },
                "assembly_wall_time_s": payload["runtime"]["assembly_wall_time_s"],
                "sum_run_wall_time_s": payload["runtime"]["sum_run_wall_time_s"],
            },
            indent=1,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
