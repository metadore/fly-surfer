"""Phase 4H.1 — multiple random control draws.

Runs the Phase 4G condition C reference once, then 100 deterministic draws from
each of five control families (A-E) defined in
``reports/PHASE_4H_EXPERIMENTAL_PROTOCOL.md`` section 3, executes every draw
through the unchanged BANC simulator and Phase 4F decoder, checkpoints after
each draw, and writes ``experiments/results/phase_4h/control_draws.json``.

Primary confirmatory endpoints: P1 motor spikes and P2 JUMP windows, tested
one-sided against the reference and Holm-corrected across the five families.
Everything else is descriptive/exploratory.

Usage:
    python -m experiments.phase_4h.control_draws            # full run, resumable
    python -m experiments.phase_4h.control_draws --draws 5  # labelled pilot
"""

from __future__ import annotations

import argparse
import json
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

PROTOCOL = PROJECT_ROOT / "reports" / "PHASE_4H_EXPERIMENTAL_PROTOCOL.md"
PROTOCOL_SHA256 = "7c511c5a9cfb64262e424ab566743ff2b25d86e2c51a12f5a77057dd3e5e6b05"
OUTPUT = common.RESULTS / "control_draws.json"
CHECKPOINT = common.RESULTS / "control_draws.checkpoint.jsonl"
N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = common.SEED_ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# endpoint extraction
# ---------------------------------------------------------------------------


def flat_metrics(metrics: dict, scores: dict) -> dict:
    actions = metrics["actions"]
    return {
        "P1_motor_spikes": metrics["motor"]["spikes"],
        "P2_jump_windows": metrics["jump_windows"],
        "total_spikes": metrics["n_spikes"],
        "stimulated_spikes": metrics["stimulated_spikes"],
        "non_stimulated_spikes": metrics["non_stimulated_spikes"],
        "active_neurons": metrics["active_neurons"],
        "stimulated_active_neurons": metrics["stimulated_active_neurons"],
        "non_stimulated_active_neurons": metrics["non_stimulated_active_neurons"],
        "motor_active_neurons": metrics["motor"]["active_neurons"],
        "motor_active_fraction": metrics["motor"]["active_fraction"],
        "peak_motor_window_spikes": metrics["motor"]["peak_window_spikes"],
        "peak_motor_window_active_neurons": metrics["motor"][
            "peak_window_active_neurons"
        ],
        "peak_motor_window_active_fraction": metrics["motor"][
            "peak_window_active_fraction"
        ],
        "left_spikes": actions["LEFT"]["spikes"],
        "right_spikes": actions["RIGHT"]["spikes"],
        "jump_spikes": actions["JUMP"]["spikes"],
        "left_active_neurons": actions["LEFT"]["active_neurons"],
        "right_active_neurons": actions["RIGHT"]["active_neurons"],
        "jump_active_neurons": actions["JUMP"]["active_neurons"],
        "left_active_fraction": actions["LEFT"]["active_fraction"],
        "right_active_fraction": actions["RIGHT"]["active_fraction"],
        "jump_active_fraction": actions["JUMP"]["active_fraction"],
        "left_peak_window_active_fraction": actions["LEFT"][
            "peak_window_active_fraction"
        ],
        "right_peak_window_active_fraction": actions["RIGHT"][
            "peak_window_active_fraction"
        ],
        "jump_peak_window_active_fraction": actions["JUMP"][
            "peak_window_active_fraction"
        ],
        "left_peak_raw_score": scores["LEFT"]["peak_raw"],
        "right_peak_raw_score": scores["RIGHT"]["peak_raw"],
        "jump_peak_raw_score": scores["JUMP"]["peak_raw"],
        "left_mean_raw_score": scores["LEFT"]["mean_raw"],
        "right_mean_raw_score": scores["RIGHT"]["mean_raw"],
        "jump_mean_raw_score": scores["JUMP"]["mean_raw"],
        "left_peak_smoothed_score": scores["LEFT"]["peak_smoothed"],
        "right_peak_smoothed_score": scores["RIGHT"]["peak_smoothed"],
        "jump_peak_smoothed_score": scores["JUMP"]["peak_smoothed"],
        "left_windows": metrics["left_windows"],
        "right_windows": metrics["right_windows"],
        "neutral_windows": metrics["neutral_windows"],
        "non_neutral_windows": metrics["n_windows"] - metrics["neutral_windows"],
        "time_to_first_motor_spike_ms": metrics["time_to_first_motor_spike_ms"],
        "first_non_neutral_window_ms": metrics["first_non_neutral_window_ms"],
        "pre_stimulation_spikes": metrics["pre_stimulation_spikes"],
        "post_stimulation_spikes": metrics["post_stimulation_spikes"],
    }


PRIMARY = ("P1_motor_spikes", "P2_jump_windows")

BINARY = {
    "any_motor_spike": lambda values: values["P1_motor_spikes"] > 0,
    "any_jump_window": lambda values: values["P2_jump_windows"] > 0,
    "any_non_neutral_window": lambda values: values["non_neutral_windows"] > 0,
}

SECONDARY_LABELS = {
    "total_spikes": "spikes over the whole recording",
    "stimulated_spikes": "spikes in the 64 stimulated neurons",
    "non_stimulated_spikes": "spikes outside the stimulated group",
    "active_neurons": "neurons with at least one spike",
    "motor_active_neurons": "motor neurons active over the recording",
    "peak_motor_window_spikes": "largest 50 ms motor spike count",
    "jump_active_fraction_metric": "JUMP pool active fraction",
    "jump_peak_window_active_fraction": "largest per-window JUMP fraction",
    "neutral_windows": "decoder windows returning NEUTRAL",
    "time_to_first_motor_spike_ms": "latency to first motor spike",
}


def decoder_scores(record: dict) -> dict:
    decisions = record["decisions"]
    block = {}
    for action in common.ACTION_POPULATIONS:
        block[action] = {
            "peak_raw": round(
                max((float(d["raw_scores"][action]) for d in decisions), default=0.0),
                6,
            ),
            "mean_raw": round(
                float(statistics.fmean(d["raw_scores"][action] for d in decisions))
                if decisions
                else 0.0,
                6,
            ),
            "peak_smoothed": round(
                max((float(d["scores"][action]) for d in decisions), default=0.0), 6
            ),
            "mean_smoothed": round(
                float(statistics.fmean(d["scores"][action] for d in decisions))
                if decisions
                else 0.0,
                6,
            ),
        }
    return block


def run_reference(world: common.World) -> dict:
    phase_4g = json.loads(common.PHASE_4G_RESULT.read_text(encoding="utf-8"))
    expected = phase_4g["conditions"]["C_vnc_intrinsic_candidate"]
    result = common.execute(
        world, world.candidate_c, seed=common.SEED_ROOT, label="4H1_reference_C"
    )
    if result["spike_hash"] != expected["spike_hash"]:
        raise SystemExit(
            "4H.1 stopped: the harness did not reproduce Phase 4G condition C "
            f"(expected {expected['spike_hash']}, got {result['spike_hash']})"
        )
    expected_states = [item["decoded_state"] for item in expected["window_records"]]
    actual_states = [item["decoded_state"] for item in result["decisions"]]
    if actual_states != expected_states:
        raise SystemExit(
            "4H.1 stopped: decoded state sequence differs from Phase 4G "
            f"condition C (expected {expected_states}, got {actual_states})"
        )
    scores = decoder_scores(result)
    record = {
        "kind": "reference",
        "label": "4H1_reference_C",
        "phase_4g_spike_hash": expected["spike_hash"],
        "phase_4g_decision_hash": expected["decision_hash"],
        "phase_4g_decision_hash_note": (
            "Phase 4G hashes its own window-record schema; the 4H decision "
            "hash is over ActionDecision dicts and is not byte-comparable"
        ),
        "spike_hash_matches_phase_4g": True,
        "state_sequence_matches_phase_4g": True,
        "decoded_state_sequence": actual_states,
        "node_indices": [int(v) for v in world.candidate_c],
        "root_ids": [int(v) for v in world.graph.root_ids[world.candidate_c]],
        "indices_sha256": common.digest_array(world.candidate_c),
        "matching": common.matching_diagnostics(world, world.candidate_c),
        "metrics": result["metrics"],
        "flat": flat_metrics(result["metrics"], scores),
        "decoder_scores": scores,
        "spike_hash": result["spike_hash"],
        "decision_hash": result["decision_hash"],
        "decision_states": [
            {
                "window_start_ms": item["window_start_ms"],
                "decoded_state": item["decoded_state"],
                "scores": item["scores"],
            }
            for item in result["decisions"]
        ],
        "simulation": result["simulation"],
        "memory": result["memory"],
        "process_memory": result.get("process_memory"),
        "wall_time_s": result["wall_time_s"],
    }
    return record


def run_draw(world: common.World, family: str, draw_index: int) -> dict:
    draw = common.family_draw(world, family, draw_index)
    indices = np.asarray(draw["node_indices"], dtype=np.int64)
    result = common.execute(
        world, indices, seed=draw["seed"], label=f"4H1_{family}_{draw_index}"
    )
    scores = decoder_scores(result)
    return {
        "kind": "draw",
        "family": family,
        "draw_index": int(draw_index),
        "seed": int(draw["seed"]),
        "pool": draw["pool"],
        "pool_size": int(draw["pool_size"]),
        "strata": draw.get("strata"),
        "stratum_shortages": draw.get("stratum_shortages"),
        "top_up_neurons": draw.get("top_up_neurons", 0),
        "node_indices": [int(v) for v in indices],
        "root_ids": [int(v) for v in draw["root_ids"]],
        "indices_sha256": draw["indices_sha256"],
        "matching": common.matching_diagnostics(world, indices),
        "metrics": result["metrics"],
        "flat": flat_metrics(result["metrics"], scores),
        "decoder_scores": scores,
        "spike_hash": result["spike_hash"],
        "decision_hash": result["decision_hash"],
        "decision_states": [
            {
                "window_start_ms": item["window_start_ms"],
                "decoded_state": item["decoded_state"],
                "scores": item["scores"],
            }
            for item in result["decisions"]
        ],
        "simulation": result["simulation"],
        "memory": result["memory"],
        "process_memory": result.get("process_memory"),
        "wall_time_s": result["wall_time_s"],
    }


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def _resample(values: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return values[rng.integers(0, values.size, size=(N_BOOTSTRAP, values.size))]


def bootstrap_delta(reference: float, values: list[float]) -> dict | None:
    sample = np.asarray(values, dtype=np.float64)
    if sample.size < 2:
        return None
    draw = _resample(sample, BOOTSTRAP_SEED)
    less = (draw < reference).mean(axis=1)
    greater = (draw > reference).mean(axis=1)
    delta = less - greater
    return {
        "low": round(float(np.quantile(delta, 0.025)), 6),
        "high": round(float(np.quantile(delta, 0.975)), 6),
        "n_resamples": N_BOOTSTRAP,
    }


def bootstrap_ratio(reference: float, values: list[float]) -> dict | None:
    sample = np.asarray(values, dtype=np.float64)
    if sample.size < 2:
        return None
    means = _resample(sample, BOOTSTRAP_SEED + 1).mean(axis=1)
    usable = means > 0
    if not np.any(usable):
        return None
    ratio = reference / means[usable]
    return {
        "low": round(float(np.quantile(ratio, 0.025)), 6),
        "high": round(float(np.quantile(ratio, 0.975)), 6),
        "n_resamples": int(usable.sum()),
    }


def endpoint_block(reference, values: list, kind: str) -> dict:
    present = [float(value) for value in values if value is not None]
    block = {
        "kind": kind,
        "n": len(present),
        "n_missing": len(values) - len(present),
        "reference": None if reference is None else float(reference),
    }
    if not present:
        block["note"] = "no non-missing control values"
        return block
    block.update(common.summary_stats(present))
    if reference is not None:
        ref = float(reference)
        block.update(
            {
                "empirical_percentile": round(
                    common.empirical_percentile(ref, present), 6
                ),
                "p_one_sided_greater": round(
                    common.empirical_p_greater(ref, present), 8
                ),
                "p_two_sided": round(common.empirical_p_two_sided(ref, present), 8),
                "cliffs_delta": round(common.cliffs_delta(ref, present), 6),
                "cliffs_delta_ci": bootstrap_delta(ref, present),
                "hedges_g": common.hedges_g(ref, present),
                "ratio_reference_to_control_mean": (
                    round(ref / float(statistics.fmean(present)), 6)
                    if float(statistics.fmean(present)) > 0
                    else None
                ),
                "ratio_ci": bootstrap_ratio(ref, present)
                if float(statistics.fmean(present)) > 0
                else None,
            }
        )
    else:
        block["note"] = "reference value is missing (no motor spike or decision)"
    if kind == "binary":
        successes = int(sum(1 for value in present if value > 0))
        low, high = common.wilson_interval(successes, len(present))
        block["proportion_nonzero"] = round(successes / len(present), 6)
        block["wilson_95"] = [round(low, 6), round(high, 6)]
    return block


def _matching_summary(values: list) -> dict:
    if isinstance(values[0], dict):
        return {key: _matching_summary([item[key] for item in values]) for key in values[0]}
    return {
        "mean": round(float(np.mean(values)), 6),
        "sd": (
            round(float(np.std(values, ddof=1)), 6) if len(values) > 1 else 0.0
        ),
        "min": round(float(np.min(values)), 6),
        "max": round(float(np.max(values)), 6),
    }


def family_statistics(draws: list[dict], reference_flat: dict) -> dict:
    flat = [record["flat"] for record in draws]
    endpoints = {}
    for key in flat[0]:
        kind = "binary" if key in BINARY else (
            "time" if key.startswith(("time_", "first_")) else "number"
        )
        endpoints[key] = endpoint_block(
            reference_flat.get(key), [item.get(key) for item in flat], kind
        )
    for name, predicate in BINARY.items():
        endpoints[name] = endpoint_block(
            int(predicate(reference_flat)),
            [int(predicate(item)) for item in flat],
            "binary",
        )
    matching = {}
    for field in draws[0]["matching"]:
        matching[field] = _matching_summary(
            [record["matching"][field] for record in draws]
        )

    state_counts: dict[str, list[int]] = {}
    for record in draws:
        for state, count in record["metrics"]["decoded_state_counts"].items():
            state_counts.setdefault(state, []).append(int(count))
    pooled_states = {state: int(np.sum(values)) for state, values in state_counts.items()}

    return {
        "n_draws": len(draws),
        "pool": draws[0]["pool"],
        "pool_size": draws[0]["pool_size"],
        "seeds": [record["seed"] for record in draws],
        "matching_diagnostics": matching,
        "endpoints": endpoints,
        "decision_state_totals": pooled_states,
        "mean_wall_time_s": round(
            float(np.mean([record["wall_time_s"] for record in draws])), 4
        ),
        "max_retained_memory_mb": round(
            float(np.max([record["memory"]["retained_arrays_mb"] for record in draws])), 4
        ),
    }


def confirmatory(families: dict, reference_flat: dict) -> dict:
    out = {
        "alpha": 0.05,
        "method": (
            "Holm-Bonferroni across the five control families, applied "
            "separately to P1 and P2; one-sided empirical p "
            "= (1 + #{control >= C}) / (1 + n)"
        ),
        "direction": "positive effect size means condition C exceeds controls",
    }
    for endpoint in PRIMARY:
        pvalues = {
            family: data["endpoints"][endpoint]["p_one_sided_greater"]
            for family, data in families.items()
        }
        out[endpoint] = {
            "reference": reference_flat[endpoint],
            "p_values": pvalues,
            "holm": common.holm(pvalues),
            "effect_sizes": {
                family: {
                    "cliffs_delta": data["endpoints"][endpoint]["cliffs_delta"],
                    "cliffs_delta_ci": data["endpoints"][endpoint]["cliffs_delta_ci"],
                    "hedges_g": data["endpoints"][endpoint]["hedges_g"],
                    "empirical_percentile": data["endpoints"][endpoint][
                        "empirical_percentile"
                    ],
                }
                for family, data in families.items()
            },
        }
    out["any_confirmatory_difference"] = any(
        any(out[endpoint]["holm"]["rejected"].values()) for endpoint in PRIMARY
    )
    return out


# ---------------------------------------------------------------------------
# checkpointing
# ---------------------------------------------------------------------------


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
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draws", type=int, default=common.N_DRAWS)
    parser.add_argument(
        "--families",
        default=",".join(common.FAMILIES),
        help="comma-separated family names, default all five",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=CHECKPOINT,
        help="append-only JSONL checkpoint (default: the pre-registered path)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="result JSON (default: the pre-registered path)",
    )
    args = parser.parse_args(argv)
    checkpoint_path = Path(args.checkpoint).resolve()
    output_path = Path(args.output).resolve()
    if not 1 <= args.draws <= common.N_DRAWS:
        parser.error(f"--draws must lie in [1, {common.N_DRAWS}]")
    families = [item.strip() for item in args.families.split(",") if item.strip()]
    unknown = [item for item in families if item not in common.FAMILY_ORDINAL]
    if unknown:
        parser.error(f"unknown families: {unknown}")

    started = utc_now()
    clock = time.perf_counter()
    protocol_hash = common.sha256_file(PROTOCOL)
    if protocol_hash != PROTOCOL_SHA256:
        raise SystemExit(
            "4H.1 stopped: the frozen protocol hash does not match "
            f"(expected {PROTOCOL_SHA256}, got {protocol_hash})"
        )
    before_integrity = common.integrity_snapshot()

    print("loading BANC world ...", flush=True)
    world = common.load_world()

    existing, corrupt_lines = load_checkpoint(checkpoint_path)
    reference = next((item for item in existing if item["kind"] == "reference"), None)
    if reference is None:
        print("running condition C reference ...", flush=True)
        reference = run_reference(world)
        common.jsonl_append(checkpoint_path, reference)
        print(
            f"reference ok: {reference['spike_hash'][:12]} "
            f"motor={reference['flat']['P1_motor_spikes']} "
            f"jump={reference['flat']['P2_jump_windows']}",
            flush=True,
        )
    completed = {
        (item["family"], int(item["draw_index"]))
        for item in existing
        if item["kind"] in {"draw", "failure"}
    }
    failures = [
        {
            "family": item["family"],
            "draw_index": int(item["draw_index"]),
            "seed": item["seed"],
            "error": item.get("error"),
        }
        for item in existing
        if item["kind"] == "failure"
    ]

    total = len(families) * args.draws
    done = 0
    for family in families:
        for draw_index in range(args.draws):
            if (family, draw_index) in completed:
                done += 1
                continue
            done += 1
            try:
                record = run_draw(world, family, draw_index)
            except Exception as exc:  # recorded, never silently dropped
                failure = {
                    "kind": "failure",
                    "family": family,
                    "draw_index": int(draw_index),
                    "seed": common.draw_seed(family, draw_index),
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
                common.jsonl_append(checkpoint_path, failure)
                failures.append(
                    {key: failure[key] for key in ("family", "draw_index", "seed", "error")}
                )
                print(f"FAIL {family} {draw_index}: {exc}", flush=True)
                continue
            common.jsonl_append(checkpoint_path, record)
            if done % 10 == 0 or draw_index == args.draws - 1:
                print(
                    f"[{done}/{total}] {family} {draw_index} "
                    f"motor={record['flat']['P1_motor_spikes']} "
                    f"jump={record['flat']['P2_jump_windows']} "
                    f"({record['wall_time_s']} s)",
                    flush=True,
                )

    records, _ = load_checkpoint(checkpoint_path)
    draws = [
        item for item in records if item["kind"] == "draw" and item["family"] in families
    ]
    failed_records = [
        item for item in records if item["kind"] == "failure" and item["family"] in families
    ]
    if not draws:
        raise SystemExit("no completed draws; nothing to analyse")

    reference_flat = reference["flat"]
    family_blocks = {}
    for family in families:
        subset = [item for item in draws if item["family"] == family]
        if not subset:
            family_blocks[family] = {
                "n_draws": 0,
                "n_failed": sum(
                    1 for item in failed_records if item["family"] == family
                ),
                "note": "no completed draws",
            }
            continue
        family_blocks[family] = family_statistics(subset, reference_flat)
        family_blocks[family]["n_failed"] = sum(
            1 for item in failed_records if item["family"] == family
        )
        family_blocks[family]["requested_draws"] = args.draws
        family_blocks[family]["pilot"] = args.draws < common.N_DRAWS

    confirmatory_block = confirmatory(family_blocks, reference_flat)

    draw_membership = {}
    for family in families:
        indices = sorted(
            {
                tuple(item["node_indices"])
                for item in draws
                if item["family"] == family
            }
        )
        draw_membership[family] = {
            "distinct_candidate_sets": len(indices),
            "draws": sum(1 for item in draws if item["family"] == family),
        }
    overlaps = {}
    for i, first in enumerate(families):
        for second in families[i + 1 :]:
            sets_first = {
                tuple(item["node_indices"])
                for item in draws
                if item["family"] == first
            }
            sets_second = {
                tuple(item["node_indices"])
                for item in draws
                if item["family"] == second
            }
            shared = len(sets_first & sets_second)
            overlaps[f"{first}|{second}"] = {
                "shared_candidate_sets": shared,
                "families_separable": shared == 0,
            }

    c_set = set(int(v) for v in reference["node_indices"])
    reference_overlap = {
        family: {
            "draws_containing_a_c_neuron": sum(
                1
                for item in draws
                if item["family"] == family
                and c_set.intersection(item["node_indices"])
            ),
            "max_c_neurons_in_a_draw": max(
                (
                    len(c_set.intersection(item["node_indices"]))
                    for item in draws
                    if item["family"] == family
                ),
                default=0,
            ),
        }
        for family in families
    }

    after_integrity = common.integrity_snapshot()
    payload = {
        "phase": "4H.1",
        "title": "Multiple random control draws",
        "generated_at_utc": utc_now(),
        "started_at_utc": started,
        "protocol": {
            "path": str(PROTOCOL.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": protocol_hash,
            "matches_frozen_hash": True,
        },
        "preregistration_note": (
            "The protocol was frozen before execution; the file hash is checked "
            "at run time and the run aborts on mismatch."
        ),
        "software": common.software_versions(),
        "world": world.describe(),
        "config_sha256": world.signature["config_sha256"],
        "design": {
            "replication_unit": (
                "candidate-set draw (selection seed); the simulator is "
                "deterministic at zero noise, so repeated simulation seeds "
                "selecting the same neurons are bit-identical"
            ),
            "draws_requested_per_family": args.draws,
            "n_draws_planned": common.N_DRAWS,
            "pilot": args.draws < common.N_DRAWS,
            "families": families,
            "seed_rule": "20261109 + 1000*family_ordinal + draw_index, A=1..E=5",
            "primary_endpoints": list(PRIMARY),
            "multiple_comparison": (
                "Holm-Bonferroni over five families, separately per endpoint"
            ),
            "exclusions": "none; failed draws are recorded and counted",
            "fixed_conditions": {
                "graph": "BANC v888 threshold 5",
                "sign_policy": "verified-only, unknown excluded",
                "weight_transform": "min(5*count^0.75, 300 pA)",
                "stimulation": "64 neurons, 300 pA, 50-250 ms",
                "dt_ms": common.DT_MS,
                "duration_ms": common.DURATION_MS,
                "decoder": "Phase 4F unchanged",
                "background_pa": 0.0,
                "noise_pa": 0.0,
            },
        },
        "reference": reference,
        "draws": draws,
        "failures": failed_records,
        "checkpoint": {
            "path": str(checkpoint_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "records_loaded": len(existing),
            "corrupt_lines_skipped": corrupt_lines,
            "completed_draws_this_run": len(draws),
        },
        "families": family_blocks,
        "confirmatory": confirmatory_block,
        "family_separation": {
            "membership": draw_membership,
            "pairwise_shared_candidate_sets": overlaps,
            "reference_overlap": reference_overlap,
        },
        "runtime": {
            "wall_time_s": round(time.perf_counter() - clock, 3),
            "mean_draw_wall_time_s": round(
                float(np.mean([item["wall_time_s"] for item in draws])), 4
            ),
            "max_retained_memory_mb": round(
                float(np.max([item["memory"]["retained_arrays_mb"] for item in draws])), 4
            ),
            "max_process_peak_wset_mb": (
                round(
                    float(
                        np.max(
                            [
                                item["process_memory"]["peak_wset_mb"]
                                for item in draws
                                if item.get("process_memory")
                                and item["process_memory"].get("peak_wset_mb")
                            ]
                        )
                    ),
                    4,
                )
                if any(
                    item.get("process_memory")
                    and item["process_memory"].get("peak_wset_mb")
                    for item in draws
                )
                else None
            ),
            "memory_note": (
                "retained_arrays_mb is the simulator's retained array total; "
                "peak_wset_mb is the process peak working set"
            ),
        },
        "integrity": {
            "before": before_integrity,
            "after": after_integrity,
            "protected_unchanged": before_integrity["pass"] and after_integrity["pass"],
        },
        "limitations": [
            "The five families are not equally matched to C; family E is an "
            "approximation and the realised standardised differences are reported.",
            "A deterministic simulator makes repeated identical candidate sets "
            "identical; replication comes from distinct candidate sets only.",
            "A difference from these controls is not evidence of biological "
            "motor control; the motor response is a simulated decoder output.",
            "Zero noise means no spontaneous activity; background/noise "
            "conditions are outside 4H.1.",
            "Phase 4G condition C was selected on motor-synapse rank, so the "
            "reference lies at the extreme tail of families A-E by construction.",
        ],
    }
    common.write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "completed_draws": len(draws),
                "failed_draws": len(failed_records),
                "P1": confirmatory_block["P1_motor_spikes"]["holm"]["adjusted"],
                "P2": confirmatory_block["P2_jump_windows"]["holm"]["adjusted"],
                "any_confirmatory_difference": confirmatory_block[
                    "any_confirmatory_difference"
                ],
                "wall_time_s": payload["runtime"]["wall_time_s"],
            },
            indent=1,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
