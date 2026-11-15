"""Phase 4H.3 — pre-registered weight transformation and sign-policy grid.

Executes the 22 configurations fixed in
``reports/PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md`` on the Phase 4G
condition C candidate set with 10 simulated repeats each, and writes
``experiments/results/phase_4h/weight_sensitivity.json``.

The pre-registration hash is checked at run time; the file is never edited
after results. Every cell is reported, including silent and NEUTRAL-only cells.
No configuration is selected as "best".

Usage:
    python -m experiments.phase_4h.weight_sensitivity
    python -m experiments.phase_4h.weight_sensitivity --configs D0_W0_S0,D0_W1_S0 --repeats 2
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from dataclasses import replace
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
PREREG = PROJECT_ROOT / "reports" / "PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md"
PREREG_SHA256 = "372ec71cd171431e4b7c4f1940eaf54dce9a19742c463373f1da39cdbece1994"
OUTPUT = common.RESULTS / "weight_sensitivity.json"
CHECKPOINT = common.RESULTS / "weight_sensitivity.checkpoint.jsonl"

REPEATS = 10
PRIMARY = ("P1_motor_spikes", "P2_jump_windows")
N_PERMUTATIONS = 10_000

WEIGHT_IDS = ("W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7")
SIGN_IDS = ("S0", "S1", "S2", "S3", "S4")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def weight_policies(world: common.World) -> dict:
    return {
        "W0": common.WeightPolicy("power", 0.75, 5.0, 300.0),
        "W1": common.WeightPolicy("linear", 1.0, 0.5, 300.0),
        "W2": common.WeightPolicy("log1p", 1.0, 10.0, None),
        "W3": common.WeightPolicy("power", 0.5, 5.0, 300.0),
        "W4": common.WeightPolicy("linear", 1.0, 0.5, 300.0),
        "W5": common.WeightPolicy("power", 0.75, 5.0, None),
        "W6": common.WeightPolicy("linear", 1.0, 5.0, 300.0),
        "W7": common.GraphLocalTargetNorm(world.graph, 150.0, 300.0),
    }


def sign_policies(world: common.World) -> dict:
    base = world.policy.sign_policy
    return {
        "S0": base,
        "S1": replace(base, predicted_fallback=True),
        "S2": replace(base, unknown_edge_policy="zero"),
        "S3": base,  # reversed after the weight policy is built
        "S4": base,
    }


CONFIGS: list[dict] = []
for _weight in WEIGHT_IDS:
    CONFIGS.append(
        {"id": f"D0_{_weight}_S0", "weight": _weight, "sign": "S0", "drive": "D0"}
    )
for _weight in ("W1", "W2", "W3"):
    CONFIGS.append(
        {"id": f"D0_{_weight}_S1", "weight": _weight, "sign": "S1", "drive": "D0"}
    )
for _sign in ("S2", "S3", "S4"):
    CONFIGS.append(
        {"id": f"D0_W0_{_sign}", "weight": "W0", "sign": _sign, "drive": "D0"}
    )
for _weight in WEIGHT_IDS:
    CONFIGS.append(
        {"id": f"D1_{_weight}_S0", "weight": _weight, "sign": "S0", "drive": "D1"}
    )
for _ordinal, _config in enumerate(CONFIGS):
    _config["ordinal"] = _ordinal
CONFIG_BY_ID = {config["id"]: config for config in CONFIGS}
REFERENCE_ID = "D0_W0_S0"


def config_seed(ordinal: int, draw_index: int) -> int:
    return common.SEED_ROOT + 300_000 + 100 * int(ordinal) + int(draw_index)


def build_policy(world: common.World, config: dict, weights: dict, signs: dict):
    weight = weights[config["weight"]]
    sign = signs[config["sign"]]
    policy = common.build_synapse_policy(world.graph, world.nodes, sign, weight)
    flipped = None
    if config["sign"] == "S3":
        policy, flipped = common.reversed_from_graph(
            world, policy, source_indices=world.candidate_c
        )
    elif config["sign"] == "S4":
        policy, flipped = common.reversed_from_graph(world, policy)
    return policy, {
        "weight": weight.describe(),
        "sign": signs[config["sign"]].describe(),
        "reversed_edges": flipped,
    }


def _stats(values: list) -> dict:
    present = [float(value) for value in values if value is not None]
    if not present:
        return {"n": 0, "n_missing": len(values)}
    block = common.summary_stats(present)
    block["n_missing"] = len(values) - len(present)
    return block


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


def config_summary(runs: list[dict]) -> dict:
    block = {
        "n_runs": len(runs),
        "seeds": [run["seed"] for run in runs],
        "current_pa": runs[0]["current_pa"],
        "aggregate_out_weight_pa": runs[0]["aggregate_out_weight_pa"],
        "spike_hashes": sorted({run["spike_hash"] for run in runs}),
        "decision_hashes": sorted({run["decision_hash"] for run in runs}),
        "all_spike_hashes_equal": len({run["spike_hash"] for run in runs}) == 1,
        "all_decision_hashes_equal": len({run["decision_hash"] for run in runs}) == 1,
        "endpoints": {},
        "policy": runs[0]["policy"],
    }
    for key in (
        "P1_motor_spikes",
        "P2_jump_windows",
        "total_spikes",
        "non_stimulated_spikes",
        "active_neurons",
        "motor_active_neurons",
        "neutral_windows",
        "left_windows",
        "right_windows",
        "time_to_first_motor_spike_ms",
        "post_stimulation_spikes",
        "left_active_fraction",
        "right_active_fraction",
        "jump_active_fraction",
        "left_peak_window_active_fraction",
        "right_peak_window_active_fraction",
        "jump_peak_window_active_fraction",
    ):
        block["endpoints"][key] = _stats([run["flat"][key] for run in runs])
    block["silent"] = all(run["flat"]["P1_motor_spikes"] == 0 for run in runs)
    block["neutral_only"] = all(
        run["flat"]["non_neutral_windows"] == 0 for run in runs
    )
    return block


def analyse(world: common.World, configs: dict, runs_by_config: dict) -> dict:
    reference_runs = runs_by_config.get(REFERENCE_ID)
    block = {
        "reference_config": REFERENCE_ID,
        "repeats_per_config": REPEATS,
        "replication_note": (
            "the simulator is deterministic at zero noise, so the 10 repeats "
            "per configuration are expected to be bit-identical; they measure "
            "that expectation and are not independent biological replicates"
        ),
    }
    if not reference_runs:
        block["note"] = "reference configuration did not run"
        return block
    w0 = {
        endpoint: [run["flat"][endpoint] for run in reference_runs]
        for endpoint in PRIMARY
    }
    for endpoint in PRIMARY:
        tests = {}
        for weight in WEIGHT_IDS[1:]:
            config_id = f"D0_{weight}_S0"
            if config_id not in runs_by_config:
                tests[weight] = {"note": "configuration not run"}
                continue
            values = [
                run["flat"][endpoint] for run in runs_by_config[config_id]
            ]
            result = common.permutation_test(
                w0[endpoint],
                values,
                n_permutations=N_PERMUTATIONS,
                seed=common.SEED_ROOT,
            )
            tests[weight] = {
                "reference_mean": round(float(np.mean(w0[endpoint])), 6),
                "config_mean": round(float(np.mean(values)), 6),
                "observed_difference": (
                    None
                    if result["observed_difference"] is None
                    else round(float(result["observed_difference"]), 6)
                ),
                "p_value": (
                    None
                    if result["p_value"] is None
                    else round(float(result["p_value"]), 8)
                ),
                "n_permutations": N_PERMUTATIONS,
                "interpretation": (
                    "numerical equivalence check over identical repeats; not "
                    "evidence of a distributional difference"
                ),
            }
        pvalues = {
            weight: tests[weight]["p_value"]
            for weight in WEIGHT_IDS[1:]
            if tests[weight].get("p_value") is not None
        }
        block[endpoint] = {
            "tests": tests,
            "holm": common.holm(pvalues)
            if pvalues
            else {"note": "no comparable configurations"},
        }

    s0_runs = runs_by_config.get("D0_W0_S0")
    s2_runs = runs_by_config.get("D0_W0_S2")
    block["s2_equals_s0"] = None
    if s0_runs and s2_runs:
        block["s2_equals_s0"] = {
            "spike_hash_equal": s0_runs[0]["spike_hash"] == s2_runs[0]["spike_hash"],
            "decision_hash_equal": s0_runs[0]["decision_hash"]
            == s2_runs[0]["decision_hash"],
            "metrics_equal": s0_runs[0]["flat"] == s2_runs[0]["flat"],
            "note": (
                "S2 retains unknown-sign edges with zero weight, which is "
                "numerically identical to excluding them; any difference would "
                "be a bug, not a scientific result"
            ),
        }

    w1_runs = runs_by_config.get("D0_W1_S0")
    w4_runs = runs_by_config.get("D0_W4_S0")
    block["w4_equals_w1"] = None
    if w1_runs and w4_runs:
        block["w4_equals_w1"] = {
            "spike_hash_equal": w1_runs[0]["spike_hash"] == w4_runs[0]["spike_hash"],
            "decision_hash_equal": w1_runs[0]["decision_hash"]
            == w4_runs[0]["decision_hash"],
            "note": (
                "power exponent 1.0 with scale 0.5 and cap 300 is the same "
                "transform as linear with scale 0.5 and cap 300"
            ),
        }

    counts = np.asarray(world.graph.edge_weight, dtype=np.float64)
    w0_weights = np.minimum(5.0 * np.power(counts, 0.75), 300.0)
    block["cap_saturation"] = {
        "edges": int(counts.size),
        "edges_at_cap_W0": int(np.count_nonzero(w0_weights >= 300.0 - 1e-9)),
        "fraction_edges_at_cap_W0": round(
            float(np.count_nonzero(w0_weights >= 300.0 - 1e-9)) / counts.size, 6
        ),
        "count_at_cap_threshold": round(float((300.0 / 5.0) ** (1.0 / 0.75)), 4),
        "interpretation": (
            "the W0 cap binds for an edge whose structural count reaches the "
            "threshold; above it W0 and W5 differ only by the cap"
        ),
    }
    block["unavailable_family"] = {
        "id": "target_normalized_dataset",
        "definition": "count / post_count using the dataset's post_count field",
        "status": "unavailable",
        "reason": (
            "the raw edge table with post_count is not present in the "
            "repository; datasets/processed/banc_v888/banc_edges.csv.gz is "
            "absent and datasets/external/banc_v888/raw is empty"
        ),
        "substitute": (
            "W7 target_normalized_graph_local uses the threshold-graph "
            "in-synapse sum and is reported as a separate, labelled "
            "approximation"
        ),
    }
    block["summary_table"] = [
        {
            "config": config["id"],
            "weight": config["weight"],
            "sign": config["sign"],
            "drive": config["drive"],
            "current_pa": configs[config["id"]]["current_pa"],
            "aggregate_out_weight_pa": configs[config["id"]][
                "aggregate_out_weight_pa"
            ],
            "motor_spikes": configs[config["id"]]["endpoints"]["P1_motor_spikes"].get(
                "mean"
            ),
            "jump_windows": configs[config["id"]]["endpoints"]["P2_jump_windows"].get(
                "mean"
            ),
            "total_spikes": configs[config["id"]]["endpoints"]["total_spikes"].get(
                "mean"
            ),
            "jump_active_fraction": configs[config["id"]]["endpoints"][
                "jump_active_fraction"
            ].get("mean"),
            "silent": configs[config["id"]]["silent"],
            "neutral_only": configs[config["id"]]["neutral_only"],
            "all_hashes_equal": configs[config["id"]]["all_spike_hashes_equal"],
        }
        for config in CONFIGS
        if config["id"] in configs
    ]
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configs",
        default=",".join(config["id"] for config in CONFIGS),
        help="comma-separated configuration ids, default all 22",
    )
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    configs = [item.strip() for item in args.configs.split(",") if item.strip()]
    unknown = [item for item in configs if item not in CONFIG_BY_ID]
    if unknown:
        parser.error(f"unknown configurations: {unknown}")
    if not 1 <= args.repeats <= REPEATS:
        parser.error(f"--repeats must lie in [1, {REPEATS}]")
    checkpoint_path = Path(args.checkpoint).resolve()
    output_path = Path(args.output).resolve()

    started = utc_now()
    clock = time.perf_counter()
    protocol_hash = common.sha256_file(PROTOCOL)
    if protocol_hash != PROTOCOL_SHA256:
        raise SystemExit(
            "4H.3 stopped: protocol hash mismatch "
            f"(expected {PROTOCOL_SHA256}, got {protocol_hash})"
        )
    prereg_hash = common.sha256_file(PREREG)
    if prereg_hash != PREREG_SHA256:
        raise SystemExit(
            "4H.3 stopped: pre-registration hash mismatch "
            f"(expected {PREREG_SHA256}, got {prereg_hash})"
        )
    before_integrity = common.integrity_snapshot()
    print("loading BANC world ...", flush=True)
    world = common.load_world()

    weights = weight_policies(world)
    signs = sign_policies(world)
    w0_policy = common.policy_with_weight(world, weights["W0"])
    reference_aggregate = common.aggregate_out_weight(
        world, w0_policy, world.candidate_c
    )
    amplitudes = {"D0": common.STIM_CURRENT_PA}
    drive_block = {
        "D0": {
            "definition": "300 pA into every candidate neuron, 50-250 ms",
            "amplitude_pa": common.STIM_CURRENT_PA,
        }
    }
    for weight in WEIGHT_IDS:
        policy = common.policy_with_weight(world, weights[weight])
        aggregate = common.aggregate_out_weight(world, policy, world.candidate_c)
        ratio = reference_aggregate / aggregate if aggregate else float("inf")
        raw = common.STIM_CURRENT_PA * ratio
        clipped = float(np.clip(raw, 100.0, 1000.0))
        amplitudes.setdefault("D1", {})[weight] = clipped
        drive_block.setdefault("D1_per_weight", {})[weight] = {
            "aggregate_out_weight_pa": round(aggregate, 6),
            "ratio_reference_to_config": round(ratio, 6),
            "unclipped_amplitude_pa": round(raw, 6),
            "amplitude_pa": round(clipped, 6),
            "clipped": bool(clipped != raw),
        }
    drive_block["D1"] = {
        "definition": "amplitude matched to the reference aggregate outgoing weight",
        "formula": "clip(300 * sum_out_W0 / sum_out_Wx, 100, 1000) pA",
        "reference_aggregate_out_weight_pa": round(reference_aggregate, 6),
        "clipped_configurations": [
            weight
            for weight, item in drive_block["D1_per_weight"].items()
            if item["clipped"]
        ],
    }

    existing, corrupt_lines = load_checkpoint(checkpoint_path)
    completed = {
        (item["config"], int(item["draw_index"]))
        for item in existing
        if item["kind"] in {"run", "failure"}
    }
    failures = [
        {
            "config": item["config"],
            "draw_index": int(item["draw_index"]),
            "seed": item["seed"],
            "error": item.get("error"),
        }
        for item in existing
        if item["kind"] == "failure"
    ]
    total = len(configs) * args.repeats
    done = 0
    for config_id in configs:
        config = CONFIG_BY_ID[config_id]
        # amplitude for D1 depends on the weight family
        current = (
            amplitudes["D0"]
            if config["drive"] == "D0"
            else amplitudes["D1"][config["weight"]]
        )
        outstanding = [
            index
            for index in range(args.repeats)
            if (config_id, index) not in completed
        ]
        if outstanding:
            policy, describe = build_policy(world, config, weights, signs)
            aggregate = common.aggregate_out_weight(world, policy, world.candidate_c)
            for draw_index in outstanding:
                done += 1
                seed = config_seed(config["ordinal"], draw_index)
                try:
                    result = common.execute(
                        world,
                        world.candidate_c,
                        policy=policy,
                        current_pa=current,
                        seed=seed,
                        label=f"4H3_{config_id}_{draw_index}",
                    )
                except Exception as exc:
                    failure = {
                        "kind": "failure",
                        "config": config_id,
                        "ordinal": int(config["ordinal"]),
                        "draw_index": int(draw_index),
                        "seed": seed,
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
                    common.jsonl_append(checkpoint_path, failure)
                    failures.append(
                        {
                            key: failure[key]
                            for key in ("config", "draw_index", "seed", "error")
                        }
                    )
                    print(f"FAIL {config_id} {draw_index}: {exc}", flush=True)
                    continue
                scores = decoder_scores(result)
                flat = flat_metrics(result["metrics"], scores)
                flat["motor_spikes"] = flat["P1_motor_spikes"]
                flat["jump_windows"] = flat["P2_jump_windows"]
                record = {
                    "kind": "run",
                    "config": config_id,
                    "ordinal": int(config["ordinal"]),
                    "weight": config["weight"],
                    "sign": config["sign"],
                    "drive": config["drive"],
                    "draw_index": int(draw_index),
                    "seed": int(seed),
                    "current_pa": float(current),
                    "aggregate_out_weight_pa": round(aggregate, 6),
                    "policy": describe,
                    "metrics": result["metrics"],
                    "flat": flat,
                    "decoder_scores": scores,
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
                common.jsonl_append(checkpoint_path, record)
                if done % 10 == 0 or draw_index == args.repeats - 1:
                    print(
                        f"[{done}/{total}] {config_id} {draw_index} "
                        f"motor={flat['motor_spikes']} jump={flat['jump_windows']} "
                        f"A={current:.1f} pA ({record['wall_time_s']} s)",
                        flush=True,
                    )

    records, _ = load_checkpoint(checkpoint_path)
    runs = [
        item
        for item in records
        if item["kind"] == "run" and item["config"] in configs
    ]
    runs_by_config: dict[str, list[dict]] = {}
    for config_id in configs:
        runs_by_config[config_id] = sorted(
            [item for item in runs if item["config"] == config_id],
            key=lambda item: item["draw_index"],
        )
    configs_summary = {
        config_id: config_summary(subset)
        for config_id, subset in runs_by_config.items()
        if subset
    }
    for config_id, subset in runs_by_config.items():
        requested = args.repeats
        if config_id in configs_summary:
            configs_summary[config_id]["requested_repeats"] = requested
            configs_summary[config_id]["pilot"] = requested < REPEATS
            configs_summary[config_id]["n_failed"] = sum(
                1
                for item in records
                if item["kind"] == "failure" and item["config"] == config_id
            )

    analysis = analyse(world, configs_summary, runs_by_config)

    after_integrity = common.integrity_snapshot()
    payload = {
        "phase": "4H.3",
        "title": "Pre-registered weight transformation and sign-policy experiment",
        "generated_at_utc": utc_now(),
        "started_at_utc": started,
        "protocol": {
            "path": str(PROTOCOL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": protocol_hash,
            "matches_frozen_hash": True,
        },
        "preregistration": {
            "path": str(PREREG.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": prereg_hash,
            "matches_frozen_hash": True,
            "amendment": None,
        },
        "software": common.software_versions(),
        "world": world.describe(),
        "config_sha256": world.signature["config_sha256"],
        "design": {
            "candidate_group": "Phase 4G condition C, fixed identities",
            "candidate_indices_sha256": common.digest_array(world.candidate_c),
            "configurations": [
                {
                    **config,
                    "seed_rule": (
                        "20261109 + 300000 + 100*config_ordinal + draw_index"
                    ),
                }
                for config in CONFIGS
            ],
            "repeats_per_config": args.repeats,
            "repeats_planned": REPEATS,
            "pilot": args.repeats < REPEATS,
            "replication_note": (
                "the 10 repeats are simulator-RNG seeds, not biological "
                "replicates; at zero noise the simulator is deterministic"
            ),
            "fixed_conditions": {
                "graph": "BANC v888 threshold 5",
                "sign_policy": "verified-only unless it is the factor under test",
                "dt_ms": common.DT_MS,
                "duration_ms": common.DURATION_MS,
                "stimulation_window_ms": [common.STIM_START_MS, common.STIM_END_MS],
                "decoder": "Phase 4F unchanged",
                "background_pa": 0.0,
                "noise_pa": 0.0,
            },
            "no_selection": (
                "the grid is executed once and every cell is reported; no "
                "configuration is selected as best"
            ),
        },
        "weight_families": {
            key: policy.describe() for key, policy in weights.items()
        },
        "sign_policies": {
            sign: policy.describe() for sign, policy in signs.items()
        },
        "drive_conditions": drive_block,
        "configs": {
            config_id: {
                "weight": CONFIG_BY_ID[config_id]["weight"],
                "sign": CONFIG_BY_ID[config_id]["sign"],
                "drive": CONFIG_BY_ID[config_id]["drive"],
                "summary": summary,
            }
            for config_id, summary in configs_summary.items()
        },
        "analysis": analysis,
        "runs": runs,
        "failures": failures,
        "checkpoint": {
            "path": str(checkpoint_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "records_loaded": len(existing),
            "corrupt_lines_skipped": corrupt_lines,
        },
        "runtime": {
            "wall_time_s": round(time.perf_counter() - clock, 3),
            "mean_run_wall_time_s": round(
                float(np.mean([run["wall_time_s"] for run in runs])), 4
            )
            if runs
            else None,
            "max_retained_memory_mb": round(
                float(np.max([run["memory"]["retained_arrays_mb"] for run in runs])), 4
            )
            if runs
            else None,
        },
        "integrity": {
            "before": before_integrity,
            "after": after_integrity,
            "protected_unchanged": before_integrity["pass"] and after_integrity["pass"],
        },
        "limitations": [
            "No transform is established as the correct model of synaptic strength.",
            "The result is conditional on the fixed Phase 4G condition C group.",
            "A JUMP decoder label is not a biological jump command.",
            "Sign policies are annotation assumptions, not measured biology.",
            "W7 is a labelled approximation of count/post_count; the dataset "
            "family is unavailable.",
            "The 10 repeats are deterministic and provide no inferential "
            "replication; permutation tests are numerical equivalence checks.",
        ],
    }
    common.write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "completed_runs": len(runs),
                "failed_runs": len(failures),
                "configs": len(configs_summary),
                "s2_equals_s0": analysis.get("s2_equals_s0"),
                "w4_equals_w1": analysis.get("w4_equals_w1"),
                "wall_time_s": payload["runtime"]["wall_time_s"],
            },
            indent=1,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
