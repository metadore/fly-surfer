"""Phase 6C: mutual information between archived FLY-SURFER variables.

Every endpoint is estimated from artifacts written by earlier phases. Each
record carries the raw estimate, the analytic bias floor, the corrected value,
a cluster-preserving permutation null, a cluster bootstrap interval, the
effective sample count, the declared bin counts, the estimator name, the seed
and any warnings.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from information.artifact_readers import (  # noqa: E402
    DECODER_SOURCE,
    PHASE_5E_SOURCE,
    PHASE_5F_SOURCE,
    load_decoder_windows,
    load_phase5e,
    load_phase5f,
)
from information.bias_correction import mi_bias_floor  # noqa: E402
from information.diagnostics import degeneracy, effective_sample_size, support_table  # noqa: E402
from information.discretization import declared  # noqa: E402
from information.entropy import entropy  # noqa: E402
from information.mutual_information import (  # noqa: E402
    conditional_mutual_information_report,
    mutual_information,
    mutual_information_report,
)
from information.permutation import cluster_bootstrap_ci, permutation_null  # noqa: E402
from information.statistics import holm, sign_flip_test, summarise  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "information_theory.yaml"
OUT_DIR = ROOT / "experiments" / "results" / "phase_6c"
RESULTS_JSON = OUT_DIR / "mutual_information_results.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def contingency(x, y, kx: int, ky: int) -> list[list[int]]:
    table = np.zeros((kx, ky), dtype=np.int64)
    for a, b in zip(x, y):
        table[int(a), int(b)] += 1
    return [[int(v) for v in row] for row in table]


def mi_endpoint(
    x,
    y,
    *,
    label: str,
    provenance: str,
    clusters,
    levels: tuple[int, int],
    config: dict,
    seed: int,
    circularity: str | None = None,
    extra: dict | None = None,
) -> dict:
    """One MI endpoint with null, interval and every required diagnostic."""
    support = config["support"]
    perm_cfg = config["permutation"]
    boot_cfg = config["bootstrap"]
    x = np.asarray(x, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    clusters = np.asarray(clusters, dtype=np.int64)
    report = mutual_information_report(x, y, min_entropy_bits=support["min_entropy_bits"])
    sample = effective_sample_size(clusters)
    table = support_table(levels[0], levels[1], report["n"])

    warnings = list(report["warnings"])
    if report["n"] < support["min_n"]:
        warnings.append(f"n={report['n']} below minimum {support['min_n']}; exploratory")
    if table["sparse"]:
        warnings.append(
            f"expected {table['expected_per_cell']} observations per cell "
            f"({table['cells']} cells); table is sparse"
        )
    if sample["n_clusters"] < 10:
        warnings.append(f"only {sample['n_clusters']} clusters; inference is unstable")

    null = permutation_null(
        x,
        y,
        clusters=clusters,
        scheme=perm_cfg["default_scheme"],
        n_permutations=perm_cfg["n_permutations"],
        seed=seed,
    )
    null.pop("observed", None)
    if null.get("null_sd") in (0.0, None):
        warnings.append(
            "permutation null is degenerate under the block scheme: the permuted "
            "variable is constant within every cluster, so p carries no information"
        )
    interval = cluster_bootstrap_ci(
        x, y, clusters, n_resamples=boot_cfg["n_resamples"], seed=seed
    )
    block = {
        "label": label,
        "provenance": provenance,
        "levels": list(levels),
        "contingency": contingency(x, y, *levels),
        "n": report["n"],
        "n_missing": report["n_missing"],
        "effective_sample": sample,
        "support": table,
        "raw_mi_bits": report["I_plugin"],
        "bias_floor_bits": report["bias_floor"],
        "corrected_mi_bits": report["I_corrected"],
        "normalised_mi": report["normalised_mi"],
        "uncertainty_coefficient": report["uncertainty_coefficient"],
        "marginal_entropy_bits": {"x": report["H_x"], "y": report["H_y"]},
        "null": null,
        "bootstrap_ci": interval,
        "estimator": report["estimator"],
        "log_base": report["log_base"],
        "seed": seed,
        "warnings": warnings,
    }
    if circularity:
        block["circularity"] = circularity
    if extra:
        block.update(extra)
    return block


def endpoint_decoder_mediated(config: dict, seed: int) -> dict:
    """C-01: pool activity versus the state the same pool drives."""
    data = load_decoder_windows()
    left = data["left_active"].astype(np.int64)
    decoded_left = (data["state_codes"] == 1).astype(np.int64)
    block = mi_endpoint(
        left,
        decoded_left,
        label="decoder_mediated_neural_to_motor",
        provenance="simulated",
        clusters=data["run_clusters"],
        levels=(2, 2),
        config=config,
        seed=seed,
        circularity=(
            "The Phase 4F decoder declares LEFT when LEFT-pool activity clears "
            "its gates, so this MI is induced by the decoder definition. It "
            "measures internal consistency of a computational map, not biological "
            "motor information."
        ),
        extra={"source": DECODER_SOURCE, "source_sha256": data["source_sha256"]},
    )
    block["decoded_left_count"] = int(decoded_left.sum())
    block["left_pool_active_count"] = int(left.sum())
    return block


def endpoint_disjoint_control(config: dict, seed: int) -> dict:
    """C-02: leg-pool activity versus the disjoint JUMP label."""
    data = load_decoder_windows()
    leg = ((data["left_active"] | data["right_active"]) > 0).astype(np.int64)
    decoded_jump = (data["state_codes"] == 3).astype(np.int64)
    block = mi_endpoint(
        leg,
        decoded_jump,
        label="disjoint_pool_control",
        provenance="simulated",
        clusters=data["run_clusters"],
        levels=(2, 2),
        config=config,
        seed=seed,
        circularity=(
            "JUMP membership is disjoint from LEFT and RIGHT, so any association "
            "here comes from shared drive and arbitration rather than from the "
            "decoder's own membership rule."
        ),
    )
    block["decoded_jump_count"] = int(decoded_jump.sum())
    block["jump_pool_active_count"] = int(data["jump_active"].sum())
    return block


def endpoint_cue_to_action(config: dict, seed: int) -> dict:
    """C-03: task-level cue to chosen action, pooled per condition."""
    data = load_phase5f()
    per_condition = {}
    for condition, block in data["conditions"].items():
        per_checkpoint = {}
        for checkpoint in data["checkpoints"]:
            payload = block["per_checkpoint"][checkpoint]
            per_checkpoint[checkpoint] = mi_endpoint(
                payload["cue"],
                payload["action"],
                label=f"cue_to_action_{condition}",
                provenance="simulated",
                clusters=payload["seed_clusters"],
                levels=(4, 4),
                config=config,
                seed=seed,
                extra={"condition": condition, "checkpoint": checkpoint},
            )
        per_condition[condition] = {
            "label": block["label"],
            "eta": block["eta"],
            "connectivity": block["connectivity"],
            "per_checkpoint": per_checkpoint,
        }
    return {
        "label": "cue_to_action",
        "source": PHASE_5F_SOURCE,
        "source_sha256": data["source_sha256"],
        "n_seeds": data["n_seeds"],
        "checkpoints": data["checkpoints"],
        "per_condition": per_condition,
        "provenance_note": (
            "The cue and the chosen action are both outputs of the Phase 5 task "
            "harness. This is task-level information in a synthetic task, not a "
            "biological sensory-to-motor measurement."
        ),
    }


def endpoint_unavailable(config: dict) -> dict:
    """C-04 and C-05: record why the archived data cannot support these."""
    data = load_phase5e()
    cue_spikes = {}
    spike_counts = {}
    for condition, block in data["conditions"].items():
        cue_spikes[condition] = degeneracy(block["n_cue_spikes"], f"n_cue_spikes_{condition}")
        probe = block["n_spikes"]
        spike_counts[condition] = {
            "state": degeneracy(probe, f"n_spikes_{condition}")["state"],
            "levels": [int(v) for v in np.unique(probe[probe >= 0])],
        }
    reasons = {item["id"]: item for item in config["unavailable"] if item["id"] in {"U03", "U04"}}
    return {
        "C04": {
            "label": "cue_to_neural_spike_count",
            "status": "unavailable",
            "reason": "n_cue_spikes is the constant 8 in every archived 5E and 5F episode",
            "evidence": {
                condition: {
                    "state": block["state"],
                    "levels": block["levels"],
                }
                for condition, block in cue_spikes.items()
            },
        },
        "C05": {
            "label": "neural_to_reward",
            "status": "unavailable",
            "reason": (
                "Per-episode spike counts carry no variation in conditions A-F "
                "(constant 12, or 11/12 in E), so a neural predictor of reward "
                "cannot be formed without inventing an observation."
            ),
            "evidence": spike_counts,
        },
        "recorded_reasons": reasons,
    }


def per_seed_mi(payload: dict) -> dict:
    """MI(cue; action) inside each seed cluster of one condition."""
    values = {}
    for seed in np.unique(payload["seed_clusters"]):
        sel = payload["seed_clusters"] == seed
        values[int(seed)] = round(
            mutual_information(payload["cue"][sel], payload["action"][sel]), 8
        )
    return values


def endpoint_fixed_vs_plastic(config: dict, seed: int) -> dict:
    """C-06: paired per-seed task information, plastic minus fixed."""
    data = load_phase5f()
    conditions = data["conditions"]
    per_condition = {}
    for condition, block in conditions.items():
        entry = {}
        for checkpoint in data["checkpoints"]:
            values = per_seed_mi(block["per_checkpoint"][checkpoint])
            entry[checkpoint] = {
                "per_seed": values,
                "summary": summarise(list(values.values())),
                "bias_floor_bits": round(mi_bias_floor(4, 4, 40), 8),
                "observations_per_seed": 40,
            }
        per_condition[condition] = entry

    final = data["checkpoints"][-1]
    contrasts = {}
    pvalues = {}
    for name, plastic, fixed in (
        ("complete", "plastic_complete", "fixed_complete"),
        ("random", "plastic_random", "fixed_random"),
    ):
        plastic_values = per_condition[plastic][final]["per_seed"]
        fixed_values = per_condition[fixed][final]["per_seed"]
        differences = [
            round(plastic_values[s] - fixed_values[s], 8) for s in sorted(plastic_values)
        ]
        test = sign_flip_test(differences, exact_max_n=12, draws=10000, seed=seed)
        contrasts[name] = {
            "plastic_condition": plastic,
            "fixed_condition": fixed,
            "checkpoint": final,
            "paired_differences": differences,
            "n_pairs": len(differences),
            "mean_difference": round(float(np.mean(differences)), 8),
            "summary": summarise(differences),
            "sign_flip": test,
            "positive_pairs": int(sum(1 for d in differences if d > 0)),
            "bias_floor_bits_per_seed": round(mi_bias_floor(4, 4, 40), 8),
        }
        pvalues[name] = test["p_value"]
    adjusted = holm(pvalues, config["permutation"]["alpha"])
    return {
        "label": "fixed_vs_plastic_task_information",
        "source": PHASE_5F_SOURCE,
        "source_sha256": data["source_sha256"],
        "per_condition": per_condition,
        "contrasts": contrasts,
        "holm": adjusted,
        "caveat": (
            "Each seed contributes 40 evaluation episodes to a 4x4 table, whose "
            "analytic MI bias floor is 0.1623 bits. The per-seed contrast is "
            "therefore exploratory: the correction is first-order and does not "
            "repair the sample size."
        ),
    }


def endpoint_condition_controlled(config: dict, seed: int) -> dict:
    """C-07: cue to action holding the Phase 5E condition fixed."""
    data = load_phase5e()
    cues: list[int] = []
    actions: list[int] = []
    strata: list[int] = []
    clusters: list[int] = []
    labels = []
    for index, (condition, block) in enumerate(data["conditions"].items()):
        if condition == "G":
            continue
        valid = block["action"] >= 0
        cues.extend(block["cue"][valid].tolist())
        actions.extend(block["action"][valid].tolist())
        strata.extend([index] * int(valid.sum()))
        clusters.extend((index * 10 + block["replicate_clusters"][valid]).tolist())
        labels.append(condition)
    cue_array = np.asarray(cues, dtype=np.int64)
    action_array = np.asarray(actions, dtype=np.int64)
    stratum_array = np.asarray(strata, dtype=np.int64)
    cluster_array = np.asarray(clusters, dtype=np.int64)

    report = conditional_mutual_information_report(
        cue_array, action_array, stratum_array, min_stratum_n=50
    )
    cmi = report["I_conditional"]
    marginal = mutual_information(cue_array, action_array)
    floor = float(np.mean([row["bias_floor"] for row in report["strata"]]))

    rng = np.random.default_rng(seed)
    null = np.empty(config["permutation"]["n_permutations"], dtype=np.float64)
    for index in range(null.size):
        shuffled = action_array.copy()
        for stratum in np.unique(stratum_array):
            sel = stratum_array == stratum
            shuffled[sel] = rng.permutation(shuffled[sel])
        null[index] = conditional_mutual_information_report(
            cue_array, shuffled, stratum_array, min_stratum_n=50
        )["I_conditional"]
    exceed = int(np.count_nonzero(null >= cmi))
    p_value = (exceed + 1) / (null.size + 1)

    unique = np.unique(cluster_array)
    draws = np.empty(config["bootstrap"]["n_resamples"], dtype=np.float64)
    for index in range(draws.size):
        picked = rng.choice(unique, size=unique.size, replace=True)
        cue_draw = np.concatenate([cue_array[cluster_array == c] for c in picked])
        action_draw = np.concatenate([action_array[cluster_array == c] for c in picked])
        stratum_draw = np.concatenate([stratum_array[cluster_array == c] for c in picked])
        draws[index] = conditional_mutual_information_report(
            cue_draw, action_draw, stratum_draw, min_stratum_n=0
        )["I_conditional"]

    warnings = list(report["warnings"])
    if report["stratified_support_fraction"] < 1.0:
        warnings.append("some strata are below the minimum support")
    return {
        "label": "cue_to_action_within_condition",
        "provenance": "simulated",
        "levels": [4, 4],
        "n": report["n"],
        "effective_sample": effective_sample_size(cluster_array),
        "raw_mi_bits": cmi,
        "marginal_mi_bits": round(marginal, 8),
        "bias_floor_bits": round(floor, 8),
        "corrected_mi_bits": round(max(0.0, cmi - floor), 8),
        "marginal_entropy_bits": {"x": round(entropy(cue_array), 8), "y": round(entropy(action_array), 8)},
        "normalised_mi": round(
            cmi / min(entropy(cue_array), entropy(action_array)), 8
        ),
        "null": {
            "scheme": "stratified free permutation of action within condition",
            "n_permutations": int(null.size),
            "null_mean": round(float(null.mean()), 8),
            "null_sd": round(float(null.std(ddof=1)), 8),
            "null_q95": round(float(np.quantile(null, 0.95)), 8),
            "null_max": round(float(null.max()), 8),
            "p_value": round(float(p_value), 8),
            "seed": seed,
        },
        "bootstrap_ci": {
            "low": round(float(np.quantile(draws, 0.025)), 8),
            "high": round(float(np.quantile(draws, 0.975)), 8),
            "n_resamples": int(draws.size),
            "n_clusters": int(unique.size),
            "seed": seed,
        },
        "strata": report["strata"],
        "stratified_support_fraction": report["stratified_support_fraction"],
        "stratum_names": labels,
        "warnings": warnings,
        "estimator": report["estimator"],
        "log_base": report["log_base"],
        "seed": seed,
        "source": PHASE_5E_SOURCE,
        "source_sha256": data["source_sha256"],
        "note": (
            "Phase 5E condition G is excluded because it records no chosen action. "
            "Strata are the six neural-substrate conditions A-F and the resampling "
            "unit is the replicate, so only 18 clusters exist."
        ),
    }


def draw_figure(payload: dict, path: Path) -> None:
    """MI point estimates with intervals, plus the paired plastic contrast."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    entries: list[tuple[str, dict]] = [
        ("C-01 pool->LEFT", payload["C01_decoder_mediated"]),
        ("C-02 leg pool->JUMP", payload["C02_disjoint_control"]),
    ]
    final = payload["C03_cue_to_action"]["checkpoints"][-1]
    for condition, block in payload["C03_cue_to_action"]["per_condition"].items():
        entries.append((f"C-03 {condition} @{final}", block["per_checkpoint"][final]))
    entries.append(("C-07 within condition", payload["C07_within_condition"]))

    names = [name for name, _ in entries]
    values = [block["raw_mi_bits"] for _, block in entries]
    floors = [block["bias_floor_bits"] for _, block in entries]
    lows = [
        None if block["bootstrap_ci"]["low"] is None else block["raw_mi_bits"] - block["bootstrap_ci"]["low"]
        for _, block in entries
    ]
    highs = [
        None if block["bootstrap_ci"]["high"] is None else block["bootstrap_ci"]["high"] - block["raw_mi_bits"]
        for _, block in entries
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    positions = np.arange(len(entries))
    axes[0].barh(positions, values, color="#3d6fb4", height=0.55)
    for index, (low, high) in enumerate(zip(lows, highs)):
        if low is not None:
            axes[0].errorbar(values[index], index, xerr=[[low], [high]], fmt="none", ecolor="#222", capsize=3)
    axes[0].scatter(floors, positions, marker="|", color="#b4373d", s=120, label="analytic bias floor")
    axes[0].set_yticks(positions, names, fontsize=8)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("mutual information (bits)")
    axes[0].set_title("Archived MI endpoints")
    axes[0].legend(loc="lower right", fontsize=8)

    contrasts = payload["C06_fixed_vs_plastic"]["contrasts"]
    for offset, (name, block) in enumerate(contrasts.items()):
        values = block["paired_differences"]
        axes[1].scatter(
            np.full(len(values), offset) + np.linspace(-0.12, 0.12, len(values)),
            values,
            s=26,
            label=f"{name} (p={block['sign_flip']['p_value']:.4f})",
        )
        axes[1].hlines(
            block["mean_difference"], offset - 0.22, offset + 0.22, color="#b4373d", linewidth=2
        )
    axes[1].axhline(0.0, color="#555", linewidth=1)
    axes[1].set_xticks(range(len(contrasts)), list(contrasts))
    axes[1].set_ylabel("plastic minus fixed MI (bits per seed)")
    axes[1].set_title("C-06 paired per-seed contrast")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> dict:
    started = time.perf_counter()
    config = load_config()
    seed = int(config["seed"]["permutations"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    c01 = endpoint_decoder_mediated(config, seed)
    c02 = endpoint_disjoint_control(config, seed)
    c03 = endpoint_cue_to_action(config, seed)
    unavailable = endpoint_unavailable(config)
    c06 = endpoint_fixed_vs_plastic(config, seed)
    c07 = endpoint_condition_controlled(config, seed)

    payload = {
        "phase": "6C",
        "title": "Mutual information between archived FLY-SURFER variables",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "log_base": 2,
        "data_sources": "archived artifacts only; no new recording, no simulation",
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "config_sha256": sha256_file(CONFIG_PATH),
        "seed": seed,
        "per_endpoint_requirements": [
            "raw_mi_bits",
            "corrected_mi_bits",
            "null",
            "bootstrap_ci",
            "n",
            "effective_sample",
            "levels",
            "estimator",
            "seed",
            "warnings",
        ],
        "C01_decoder_mediated": c01,
        "C02_disjoint_control": c02,
        "C03_cue_to_action": c03,
        "C04_C05_unavailable": unavailable,
        "C06_fixed_vs_plastic": c06,
        "C07_within_condition": c07,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    draw_figure(payload, OUT_DIR / "figures" / "mutual_information.png")
    with open(RESULTS_JSON, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")
    return payload


if __name__ == "__main__":
    result = main()
    print(f"wrote {RESULTS_JSON}")
    print(f"C-01 raw MI = {result['C01_decoder_mediated']['raw_mi_bits']:.4f}")
    print(f"C-02 raw MI = {result['C02_disjoint_control']['raw_mi_bits']:.4f}")
    for condition, block in result["C03_cue_to_action"]["per_condition"].items():
        final = result["C03_cue_to_action"]["checkpoints"][-1]
        entry = block["per_checkpoint"][final]
        print(f"C-03 {condition}: {entry['raw_mi_bits']:.4f} p={entry['null']['p_value']:.4g}")
    for name, block in result["C06_fixed_vs_plastic"]["contrasts"].items():
        print(
            f"C-06 {name}: mean diff {block['mean_difference']:+.4f} "
            f"p={block['sign_flip']['p_value']:.4f}"
        )
    print(
        f"C-07 conditional MI = {result['C07_within_condition']['raw_mi_bits']:.4f} "
        f"p={result['C07_within_condition']['null']['p_value']:.4g}"
    )
