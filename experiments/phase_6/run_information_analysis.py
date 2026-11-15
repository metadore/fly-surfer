"""Phase 6: information-theoretic analysis of archived FLY-SURFER artifacts.

SCIENTIFIC STATUS
    Every number in this analysis is estimated from artifacts written by
    Phases 3A.5, 4F, 5E and 5F. Nothing is simulated here and no archived
    result is modified. The estimators are plug-in discrete entropy and mutual
    information in bits, reported with their analytic bias floor.

    Mutual information does not establish causation, and information about a
    task label does not establish biological perception. The Phase 4F decoder
    thresholds the same pool activity used as its predictor, so that estimate
    is an internal-consistency check of a computational map. The Phase 5F
    contrast is task-level information in a synthetic conditioned-response
    task, not a connectome measurement.

Design
    A. Sensory distance -> four-neuron population response (Phase 3A.5).
    B. Population-size sensitivity of the same distance code.
    C. Baseline versus plastic task information, fixed versus random wiring
       (Phase 5F, the only confirmatory family).
    D. Reward-modulation ablation at task level (Phase 5E, exploratory).
    E. Neural pool activity -> decoded motor output (Phase 4F, descriptive).
    F. Cue -> action given condition (Phase 5E, exploratory).
    Every unsupported endpoint is recorded with its reason instead of a number.

Usage:
  python -m experiments.phase_6.run_information_analysis
  python -m experiments.phase_6.run_information_analysis --quick
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    PHASE_3B2C_SOURCE,
    PHASE_5_BANC_SOURCE,
    UnavailableEndpoint,
    load_decoder_window_details,
    load_phase5_banc_conditions,
    load_phase5e,
    load_phase5f,
    load_population_sweep,
    load_replay_neural_availability,
    load_sensory_population_stage,
    sha256_of,
)
from information.bias_correction import mi_bias_floor  # noqa: E402
from information.diagnostics import degeneracy, effective_sample_size, support_table  # noqa: E402
from information.matching import (  # noqa: E402
    match_keys,
    validate_cluster_coverage,
    validate_equal_lengths,
)
from information.mutual_information import (  # noqa: E402
    conditional_mutual_information_report,
    mutual_information,
    mutual_information_report,
)
from information.permutation import cluster_bootstrap_ci, permutation_null  # noqa: E402
from information.population import (  # noqa: E402
    level_pattern_codes,
    pattern_codes,
    population_information,
)
from information.statistics import holm, sign_flip_test, summarise  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "phase_6_information.yaml"
OUT_DIR = ROOT / "experiments" / "results" / "phase_6"
RESULTS_JSON = OUT_DIR / "information_analysis.json"

RAW_SPIKE_ARTIFACTS = (
    "experiments/results/initial/activity.npz",
    "experiments/results/phase_4g/phase_4g4_smoke_t5_seed20261108/activity.npz",
    "experiments/phase_3c/results/p3_3c5_lane_encoding_pilot_spikes.npz",
)

STATUS_EXPLORATORY = "exploratory"
STATUS_CONFIRMATORY = "confirmatory"
STATUS_DESCRIPTIVE = "descriptive"


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def json_safe(value):
    """Recursively convert numpy values and non-finite floats for strict JSON."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def contingency(x, y, kx: int, ky: int) -> list[list[int]]:
    table = np.zeros((kx, ky), dtype=np.int64)
    for a, b in zip(np.asarray(x, dtype=np.int64), np.asarray(y, dtype=np.int64)):
        table[int(a), int(b)] += 1
    return [[int(value) for value in row] for row in table]


def paired_bootstrap_mean(values, *, n_resamples: int, seed: int, alpha: float) -> dict:
    numbers = np.asarray(values, dtype=np.float64)
    if numbers.size == 0:
        return {"low": None, "high": None, "n_resamples": 0}
    rng = np.random.default_rng(seed)
    draws = np.empty(n_resamples, dtype=np.float64)
    for index in range(n_resamples):
        draws[index] = rng.choice(numbers, size=numbers.size, replace=True).mean()
    return {
        "low": round(float(np.quantile(draws, alpha / 2)), 8),
        "high": round(float(np.quantile(draws, 1 - alpha / 2)), 8),
        "mean": round(float(numbers.mean()), 8),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
    }


# ---------------------------------------------------------------------------
# one mutual-information endpoint with every declared diagnostic
# ---------------------------------------------------------------------------


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
    status: str,
    scheme: str | None = None,
    circularity: str | None = None,
    exact_max_assignments: int = 0,
    extra: dict | None = None,
) -> dict:
    support = config["support"]
    perm_cfg = config["permutation"]
    boot_cfg = config["bootstrap"]
    x = np.asarray(x, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    clusters = np.asarray(clusters, dtype=np.int64)
    validate_equal_lengths(x=x, y=y, clusters=clusters)

    report = mutual_information_report(
        x, y, min_entropy_bits=support["min_entropy_bits"]
    )
    sample = effective_sample_size(clusters)
    table = support_table(levels[0], levels[1], report["n"])
    x_state = degeneracy(x, "x")
    y_state = degeneracy(y, "y")
    estimable = x_state["state"] == "variable" and y_state["state"] == "variable"

    warnings = list(report["warnings"])
    if not estimable:
        warnings.append(
            f"not estimable: x is {x_state['state']} and y is {y_state['state']}"
        )
    if report["n"] < support["min_n_confirmatory"]:
        warnings.append(
            f"n={report['n']} is below the confirmatory minimum "
            f"{support['min_n_confirmatory']}; status is {status}"
        )
    if sample["n_clusters"] < support["min_clusters_confirmatory"]:
        warnings.append(
            f"{sample['n_clusters']} clusters are below the confirmatory minimum "
            f"{support['min_clusters_confirmatory']}; status is {status}"
        )
    if table["sparse"]:
        warnings.append(
            f"expected {table['expected_per_cell']} observations per cell "
            f"across {table['cells']} cells; table is sparse"
        )

    if estimable:
        chosen = scheme or ("block" if sample["n_clusters"] < report["n"] else "free")
        n_permutations = perm_cfg[
            "n_permutations_confirmatory"
            if status == STATUS_CONFIRMATORY
            else "n_permutations_exploratory"
        ]
        null = permutation_null(
            x,
            y,
            clusters=clusters,
            scheme=chosen,
            n_permutations=n_permutations,
            seed=seed,
            exact_max_assignments=exact_max_assignments,
        )
        null.pop("observed", None)
        if null["null_sd"] in (0.0, None):
            warnings.append(
                "permutation null is degenerate; the reported p carries no information"
            )
    else:
        null = {
            "status": "not_estimable",
            "reason": "a constant or empty variable has no permutation distribution",
        }

    if estimable and sample["n_clusters"] >= support["min_clusters_interval"]:
        interval = cluster_bootstrap_ci(
            x,
            y,
            clusters,
            n_resamples=boot_cfg["n_resamples"],
            seed=seed,
            alpha=boot_cfg["alpha"],
        )
    else:
        interval = {
            "low": None,
            "high": None,
            "withheld": (
                f"fewer than {support['min_clusters_interval']} clusters "
                "or the endpoint is not estimable"
            ),
        }

    block = {
        "label": label,
        "status": status,
        "provenance": provenance,
        "levels": list(levels),
        "n": report["n"],
        "n_missing": report["n_missing"],
        "effective_sample": sample,
        "support": table,
        "contingency": (
            contingency(x[(x >= 0) & (y >= 0)], y[(x >= 0) & (y >= 0)], *levels)
            if report["n"]
            else []
        ),
        "state_x": x_state,
        "state_y": y_state,
        "estimable": bool(estimable),
        "marginal_entropy_bits": {"x": report.get("H_x"), "y": report.get("H_y")},
        "joint_entropy_bits": report.get("H_joint"),
        "raw_mi_bits": report["I_plugin"],
        "bias_floor_bits": report["bias_floor"],
        "corrected_mi_bits": report["I_corrected"],
        "normalised_mi": report["normalised_mi"],
        "uncertainty_coefficient": report["uncertainty_coefficient"],
        "null": null,
        "bootstrap_ci": interval,
        "estimator": report["estimator"],
        "log_base": report["log_base"],
        "seed": int(seed),
        "warnings": warnings,
    }
    if circularity:
        block["circularity"] = circularity
    if extra:
        block.update(extra)
    return block


# ---------------------------------------------------------------------------
# A. sensory distance -> population response
# ---------------------------------------------------------------------------


def _distance_codes(distances, order) -> np.ndarray:
    index = {round(float(value), 6): position for position, value in enumerate(order)}
    codes = []
    for distance in np.asarray(distances, dtype=np.float64):
        key = round(float(distance), 6)
        if key not in index:
            raise UnavailableEndpoint(f"distance {distance} is not in the declared order")
        codes.append(index[key])
    return np.asarray(codes, dtype=np.int64)


def analysis_sensory_population(config: dict, seed: int) -> dict:
    spec = config["sensory_population"]
    data = load_sensory_population_stage(spec["source"])
    distance_codes = _distance_codes(data["distances"], spec["distance_order"])

    variants = {
        "exact_vector": pattern_codes(data["vectors"], name="sensory_exact"),
        "binary": pattern_codes(data["vectors"], binary=True, name="sensory_binary"),
    }
    for cap in spec["count_caps"]:
        variants[f"cap_{int(cap)}"] = pattern_codes(
            data["vectors"], cap=int(cap), name=f"sensory_cap_{int(cap)}"
        )

    endpoints = {}
    for name, coded in variants.items():
        endpoints[name] = mi_endpoint(
            coded.codes,
            distance_codes,
            label=f"sensory_distance_to_pattern_{name}",
            provenance=data["provenance"],
            clusters=data["group_index"],
            levels=(3, 3),
            config=config,
            seed=seed,
            status=STATUS_EXPLORATORY,
            exact_max_assignments=10_000,
            extra={
                "code": coded.summary()["spec"],
                "n_code_levels": len(coded.labels),
                "missing_codes": int(np.count_nonzero(coded.codes < 0)),
            },
        )

    groups = []
    for group in data["groups"]:
        groups.append(
            {
                "group": int(group["group"]),
                "mapping_seed": group["parameters"].get("mapping_seed"),
                "population_size": group["parameters"].get("population_size"),
                "distances": [float(value) for value in group["distances"]],
            }
        )
    seeds = sorted({int(value) for value in data["mapping_seeds"] if value >= 0})

    def ordered_vectors(group):
        indices = np.flatnonzero(data["group_index"] == group)
        order = np.argsort([distance_codes[index] for index in indices])
        return data["vectors"][indices][order]

    ordered = [ordered_vectors(group) for group in np.unique(data["group_index"])]
    response_by_distance = ordered[0]
    identical = all(
        np.array_equal(response_by_distance, other) for other in ordered[1:]
    )

    return {
        "label": "sensory_distance_to_population_response",
        "status": STATUS_EXPLORATORY,
        "source": data["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "observational_unit": "simulation run (9), clustered by mapping seed (3)",
        "distances": [float(value) for value in spec["distance_order"]],
        "distance_labels": list(spec["distance_labels"]),
        "population_size": data["groups"][0]["parameters"].get("population_size"),
        "response_vector_by_distance": response_by_distance.tolist(),
        "per_group": groups,
        "mapping_seeds": seeds,
        "response_identical_across_seeds": bool(identical),
        "endpoints": endpoints,
        "interpretation": (
            "The four-neuron response is a deterministic one-to-one function of "
            "distance in every archived mapping seed. The plug-in estimate is "
            "therefore log2(3) by construction. It checks the declared encoding; "
            "it is not a statistical discovery, and three mapping seeds cannot "
            "support a confirmatory claim."
        ),
        "replication_note": (
            "The block permutation treats each mapping seed as one cluster. With "
            "three clusters of three distances the null has exactly 6^3 = 216 "
            "within-seed assignments and is enumerated exactly. The observed "
            "bijection is reproduced only by the six permutations applied "
            "consistently to all three clusters, so the exact p is 6/216 ~ 0.028."
        ),
        "bootstrap_note": (
            "The cluster bootstrap interval collapses to the point estimate "
            "because all three mapping seeds produce the identical response. It "
            "reflects zero observed between-seed variation and is not a measure "
            "of precision."
        ),
    }


def analysis_population_sweep(config: dict) -> dict:
    spec = config["sensory_population"]
    data = load_population_sweep(spec["population_sweep_source"])
    rows = []
    for group in data["groups"]:
        distance_codes = _distance_codes(group["distances"], spec["distance_order"])
        coded = pattern_codes(group["vectors"], name="sweep_pattern")
        joint = mutual_information_report(coded.codes, distance_codes)
        individual_reports = [
            mutual_information_report(group["vectors"][:, column], distance_codes)
            for column in range(group["vectors"].shape[1])
        ]
        individual = [report["I_plugin"] for report in individual_reports]
        decomposition = population_information(joint["I_plugin"], individual)
        active = [
            int(np.count_nonzero(group["vectors"][row] > 0))
            for row in range(group["vectors"].shape[0])
        ]
        rows.append(
            {
                "population_size": int(group["population_size"]),
                "n_runs": int(group["vectors"].shape[0]),
                "n_active_neurons_by_distance": active,
                "joint_mi_bits": joint["I_plugin"],
                "joint_bias_floor_bits": joint["bias_floor"],
                "joint_corrected_mi_bits": joint["I_corrected"],
                "individual_mi_bits": decomposition["individual_mi_bits"],
                "max_individual_mi_bits": decomposition["max_individual_mi_bits"],
                "sum_individual_mi_bits": decomposition["sum_individual_mi_bits"],
                "joint_minus_max_individual_bits": decomposition[
                    "joint_minus_max_individual_bits"
                ],
                "sum_individual_minus_joint_bits": decomposition[
                    "sum_individual_minus_joint_bits"
                ],
            }
        )
    return {
        "label": "population_size_sensitivity",
        "status": STATUS_DESCRIPTIVE,
        "source": data["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "mapping_seeds": list(data["mapping_seeds"]),
        "observational_unit": (
            "one simulation run per distance per population size (15 runs); "
            "all groups share one mapping seed"
        ),
        "rows": rows,
        "interpretation": (
            "The joint distance code stays at log2(3) bits at every population "
            "size. Single-neuron estimates sum far above the joint estimate "
            "because each active neuron repeats the same distance identity. The "
            "split is descriptive: the plug-in bias is positive and the summed "
            "term double-counts shared information."
        ),
        "note": data["note"],
    }


# ---------------------------------------------------------------------------
# B. baseline versus plasticity at task level (Phase 5F)
# ---------------------------------------------------------------------------


def per_seed_mi(payload: dict) -> dict:
    values = {}
    for seed in np.unique(payload["seed_clusters"]):
        selected = payload["seed_clusters"] == seed
        values[int(seed)] = round(
            mutual_information(payload["cue"][selected], payload["action"][selected]), 8
        )
    return values


def analysis_plasticity(config: dict, seed: int) -> dict:
    spec = config["plasticity_task_information"]
    data = load_phase5f()
    final = spec["final_checkpoint"]

    conditions = {}
    per_seed_by_condition: dict[str, dict[str, dict[int, float]]] = {}
    offset = 0
    for condition, block in data["conditions"].items():
        per_checkpoint = {}
        per_seed_by_condition[condition] = {}
        for checkpoint in spec["checkpoints"]:
            payload = block["per_checkpoint"][checkpoint]
            values = per_seed_mi(payload)
            per_seed_by_condition[condition][checkpoint] = values
            endpoint = mi_endpoint(
                payload["cue"],
                payload["action"],
                label=f"task_information_{condition}_checkpoint_{checkpoint}",
                provenance=data["provenance"],
                clusters=payload["seed_clusters"],
                levels=(4, 4),
                config=config,
                seed=seed + offset,
                status=STATUS_EXPLORATORY,
                extra={
                    "condition": condition,
                    "checkpoint": checkpoint,
                    "role": (
                        "descriptive per-condition estimate; the confirmatory "
                        "unit is the paired seed-level contrast"
                    ),
                },
            )
            offset += 1
            per_checkpoint[checkpoint] = {
                "per_seed_mi_bits": {str(key): value for key, value in values.items()},
                "summary": summarise(list(values.values())),
                "bias_floor_bits_per_seed": round(mi_bias_floor(4, 4, 40), 8),
                "observations_per_seed": int(spec["episodes_per_seed"]),
                "endpoint": endpoint,
            }
        conditions[condition] = {
            "label": block["label"],
            "eta": block["eta"],
            "connectivity": block["connectivity"],
            "per_checkpoint": per_checkpoint,
        }

    contrasts = {}
    pvalues = {}
    for index, contrast_spec in enumerate(spec["confirmatory_contrasts"]):
        plastic = contrast_spec["plastic"]
        fixed = contrast_spec["fixed"]
        plastic_values = per_seed_by_condition[plastic][final]
        fixed_values = per_seed_by_condition[fixed][final]
        keys = match_keys(
            sorted(plastic_values), sorted(fixed_values), label=f"{plastic} vs {fixed} seeds"
        )
        differences = [
            round(plastic_values[key] - fixed_values[key], 8) for key in keys
        ]
        control_plastic = per_seed_by_condition[plastic][spec["checkpoints"][0]]
        control_fixed = per_seed_by_condition[fixed][spec["checkpoints"][0]]
        control_keys = match_keys(
            sorted(control_plastic),
            sorted(control_fixed),
            label=f"{plastic} vs {fixed} checkpoint-0 seeds",
        )
        control_differences = [
            round(control_plastic[key] - control_fixed[key], 12) for key in control_keys
        ]
        max_control = float(np.max(np.abs(control_differences)))
        if max_control != 0.0:
            raise RuntimeError(
                f"matched checkpoint-0 control for {plastic} vs {fixed} is not "
                f"exactly zero (max |difference|={max_control})"
            )
        test = sign_flip_test(
            differences, exact_max_n=12, draws=10000, seed=seed + 100 + index
        )
        interval = paired_bootstrap_mean(
            differences,
            n_resamples=config["bootstrap"]["n_resamples"],
            seed=seed + 200 + index,
            alpha=config["bootstrap"]["alpha"],
        )
        contrasts[contrast_spec["name"]] = {
            "status": STATUS_CONFIRMATORY,
            "plastic_condition": plastic,
            "fixed_condition": fixed,
            "checkpoint": final,
            "observational_unit": (
                "seed (10); each seed contributes 40 evaluation episodes to both arms"
            ),
            "paired_differences": differences,
            "n_pairs": len(differences),
            "mean_difference": round(float(np.mean(differences)), 8),
            "summary": summarise(differences),
            "positive_pairs": int(sum(1 for value in differences if value > 0)),
            "negative_pairs": int(sum(1 for value in differences if value < 0)),
            "sign_flip": test,
            "bootstrap_ci_mean_difference": interval,
            "bias_floor_bits_per_seed": round(mi_bias_floor(4, 4, 40), 8),
            "bias_note": (
                "the first-order bias floor is common to both arms with equal "
                "episode counts and cancels in the paired difference"
            ),
            "matched_control": {
                "checkpoint": spec["checkpoints"][0],
                "max_abs_difference": max_control,
                "all_zero": True,
                "meaning": (
                    "at checkpoint 0 fixed and plastic weights are identical, so "
                    "the paired difference must be exactly zero"
                ),
            },
            "interval_note": (
                "the percentile bootstrap interval is descriptive. It can "
                "exclude zero while the exact sign-flip test does not, because "
                "the bootstrap does not impose the null. The exact test is the "
                "confirmatory decision."
            ),
        }
        pvalues[contrast_spec["name"]] = test["p_value"]

    comparison_roles = {
        "plastic_minus_fixed_complete": "plasticity versus baseline",
        "plastic_minus_fixed_random": "plasticity versus no-plasticity control",
    }
    adjusted = holm(pvalues, config["permutation"]["alpha"])
    return {
        "label": "baseline_vs_plasticity_task_information",
        "status": STATUS_CONFIRMATORY,
        "source": spec["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "source_note": (
            "Phase 5F core comparison on a synthetic conditioned-response task; "
            "not the BANC connectome and not a biological learning experiment"
        ),
        "observational_unit": (
            "seed (10 independent seeds); episodes inside a seed share one weight "
            "trajectory and are never treated as independent trials"
        ),
        "task_information_definition": (
            "I(cue; chosen action) in bits inside each seed's 40 evaluation episodes"
        ),
        "checkpoints": list(spec["checkpoints"]),
        "final_checkpoint": final,
        "conditions": conditions,
        "comparison_roles": comparison_roles,
        "contrasts": contrasts,
        "holm": adjusted,
        "caveats": [
            "A weight change is the output of the declared three-factor rule; it "
            "is not evidence of biological synaptic plasticity or learning.",
            "Each per-seed table has 40 observations in 16 cells; its analytic MI "
            "bias floor is 0.1623 bits. The paired difference removes the "
            "first-order bias but not the sampling variance.",
            "Ten seeds is the minimum declared for a confirmatory contrast; the "
            "exact sign-flip test over ten pairs cannot report p below 0.002.",
        ],
    }


# ---------------------------------------------------------------------------
# C. reward-modulation ablation at task level (Phase 5E)
# ---------------------------------------------------------------------------


def analysis_reward_ablation(config: dict, seed: int) -> dict:
    spec = config["reward_ablation"]
    data = load_phase5e()
    base = data["conditions"]["B"]
    base_keys = [
        f"{int(replicate)}-{int(episode)}"
        for replicate, episode in zip(base["replicate_clusters"], base["episode"])
    ]

    validation = {}
    per_replicate: dict[str, dict[int, float]] = {}
    endpoints = {}
    offset = 0
    for condition in spec["conditions"]:
        block = data["conditions"][condition]
        keys = [
            f"{int(replicate)}-{int(episode)}"
            for replicate, episode in zip(
                block["replicate_clusters"], block["episode"]
            )
        ]
        match_keys(base_keys, keys, label=f"B vs {condition} episodes")
        validate_equal_lengths(
            cue=block["cue"],
            action=block["action"],
            clusters=block["replicate_clusters"],
        )
        cue_equal = bool(np.array_equal(base["cue"], block["cue"]))
        if not cue_equal:
            raise RuntimeError(
                f"condition {condition} does not share the condition-B cue stream"
            )
        valid = block["action"] >= 0
        if not np.all(valid):
            raise UnavailableEndpoint(
                f"condition {condition} has {int(np.count_nonzero(~valid))} "
                "episodes without a chosen action"
            )
        values = {}
        for replicate in np.unique(block["replicate_clusters"]):
            selected = block["replicate_clusters"] == replicate
            values[int(replicate)] = round(
                mutual_information(
                    block["cue"][selected], block["action"][selected]
                ),
                8,
            )
        per_replicate[condition] = values
        endpoints[condition] = mi_endpoint(
            block["cue"],
            block["action"],
            label=f"task_information_{condition}",
            provenance=data["provenance"],
            clusters=block["replicate_clusters"],
            levels=(4, 4),
            config=config,
            seed=seed + offset,
            status=STATUS_EXPLORATORY,
            extra={
                "condition": condition,
                "condition_label": block["label"],
                "episode_set": spec["episode_set"],
            },
        )
        offset += 1
        validation[condition] = {
            "cue_stream_equal_to_B": cue_equal,
            "n_episodes": int(block["cue"].size),
            "n_replicates": int(np.unique(block["replicate_clusters"]).size),
            "cue_levels": sorted(int(value) for value in np.unique(block["cue"])),
            "action_levels": sorted(int(value) for value in np.unique(block["action"])),
        }

    contrasts = {}
    pvalues = {}
    for index, contrast_spec in enumerate(spec["paired_contrasts"]):
        left = per_replicate[contrast_spec["left"]]
        right = per_replicate[contrast_spec["right"]]
        keys = match_keys(sorted(left), sorted(right), label=contrast_spec["name"])
        differences = [round(left[key] - right[key], 8) for key in keys]
        test = sign_flip_test(
            differences, exact_max_n=12, draws=10000, seed=seed + 300 + index
        )
        contrasts[contrast_spec["name"]] = {
            "status": STATUS_EXPLORATORY,
            "left": contrast_spec["left"],
            "right": contrast_spec["right"],
            "paired_differences": differences,
            "n_pairs": len(differences),
            "mean_difference": round(float(np.mean(differences)), 8),
            "summary": summarise(differences),
            "positive_pairs": int(sum(1 for value in differences if value > 0)),
            "sign_flip": test,
            "bootstrap_ci_mean_difference": paired_bootstrap_mean(
                differences,
                n_resamples=config["bootstrap"]["n_resamples"],
                seed=seed + 400 + index,
                alpha=config["bootstrap"]["alpha"],
            ),
        }
        pvalues[contrast_spec["name"]] = test["p_value"]

    identical_groups = {}
    reference = contrasts[spec["paired_contrasts"][0]["name"]]["paired_differences"]
    for name, block in contrasts.items():
        identical_groups[name] = {
            "identical_to_first_contrast": block["paired_differences"] == reference
        }

    return {
        "label": "reward_modulation_ablation_task_information",
        "status": STATUS_EXPLORATORY,
        "source": spec["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "observational_unit": (
            "replicate (3), each contributing 160 training episodes; conditions "
            "A/B/C/D/F share the cue stream and substrate seed by replicate"
        ),
        "matched_validation": validation,
        "conditions": {
            condition: {
                "label": data["conditions"][condition]["label"],
                "per_replicate_mi_bits": {
                    str(key): value for key, value in per_replicate[condition].items()
                },
                "summary": summarise(list(per_replicate[condition].values())),
                "endpoint": endpoints[condition],
            }
            for condition in spec["conditions"]
        },
        "contrasts": contrasts,
        "holm": holm(pvalues, config["permutation"]["alpha"]),
        "identical_contrasts": identical_groups,
        "power_note": (
            "With three paired replicates the exact two-sided sign-flip test has "
            "eight assignments and cannot report p below 0.25. No significance "
            "claim is possible from this ablation."
        ),
        "caveats": [
            "A, C and F produce identical chosen actions in every replicate, so "
            "their contrasts with B coincide and are not independent evidence.",
            "The task information is I(cue; action) in a synthetic task. It does "
            "not measure information in neural activity or reward learning.",
        ],
    }


# ---------------------------------------------------------------------------
# D. neural pool activity -> decoded motor output (Phase 4F)
# ---------------------------------------------------------------------------


def analysis_neural_motor(config: dict, seed: int) -> dict:
    spec = config["neural_motor"]
    data = load_decoder_window_details()
    states = data["state_codes"]

    variants = {
        "any_active_pattern": pattern_codes(
            data["pool_active"], binary=True, name="pool_any_active"
        ),
        "pool_spike_cap_4": pattern_codes(
            data["pool_spikes"], cap=4, name="pool_spike_cap_4"
        ),
    }
    for threshold in spec["gate_thresholds"]:
        label = f"gate_{float(threshold):.2f}"
        variants[label] = level_pattern_codes(
            data["active_fraction"],
            [float(threshold)],
            name=label,
        )

    endpoints = {}
    offset = 0
    for name, coded in variants.items():
        endpoints[name] = mi_endpoint(
            coded.codes,
            states,
            label=f"pool_activity_to_decoded_state_{name}",
            provenance=data["provenance"],
            clusters=data["run_clusters"],
            levels=(len(coded.labels), len(data["state_names"])),
            config=config,
            seed=seed + offset,
            status=STATUS_DESCRIPTIVE,
            circularity=spec["circularity_warning"],
            extra={
                "code": coded.summary()["spec"],
                "n_code_levels": len(coded.labels),
                "declared_window_indices": list(spec["window_indices"]),
            },
        )
        offset += 1

    binary = variants["any_active_pattern"].codes
    per_window = {}
    for window_index in spec["window_indices"]:
        selected = data["window_index"] == window_index
        starts = sorted({float(value) for value in data["window_start_ms"][selected]})
        ends = sorted({float(value) for value in data["window_end_ms"][selected]})
        states_here = states[selected]
        patterns_here = binary[selected]
        state_state = degeneracy(states_here, "decoded_state")
        pattern_state = degeneracy(patterns_here, "pool_pattern")
        if state_state["state"] != "variable" or pattern_state["state"] != "variable":
            per_window[str(window_index)] = {
                "label": f"pool_activity_to_decoded_state_window_{window_index}",
                "status": "not_estimable",
                "window_index": int(window_index),
                "window_start_ms": starts,
                "window_end_ms": ends,
                "n": int(np.count_nonzero(selected)),
                "state": state_state["state"],
                "pattern_state": pattern_state["state"],
                "reason": (
                    "both the decoded state and the pool pattern are constant in "
                    "this window, so mutual information is zero for every run and "
                    "no permutation distribution exists"
                ),
            }
            continue
        per_window[str(window_index)] = mi_endpoint(
            patterns_here,
            states_here,
            label=f"pool_activity_to_decoded_state_window_{window_index}",
            provenance=data["provenance"],
            clusters=data["run_clusters"][selected],
            levels=(
                len(variants["any_active_pattern"].labels),
                len(data["state_names"]),
            ),
            config=config,
            seed=seed + 50 + window_index,
            status=STATUS_DESCRIPTIVE,
            scheme="free",
            circularity=spec["circularity_warning"],
            extra={
                "window_index": int(window_index),
                "window_start_ms": starts,
                "window_end_ms": ends,
            },
        )

    state_counts = np.bincount(states, minlength=4).tolist()
    pattern_counts = {
        "|".join(str(int(value)) for value in row): int(count)
        for row, count in zip(
            *np.unique(data["pool_active"], axis=0, return_counts=True)
        )
    }
    gate_groups: dict[tuple[int, ...], list[str]] = {}
    for threshold in spec["gate_thresholds"]:
        label = f"gate_{float(threshold):.2f}"
        gate_groups.setdefault(tuple(variants[label].codes.tolist()), []).append(
            label
        )
    duplicate_gate_codes = [names for names in gate_groups.values() if len(names) > 1]
    gate_code_note = None
    if duplicate_gate_codes:
        gate_code_note = (
            "these gate cuts yield identical code vectors because no observed "
            "active fraction lies strictly between them: "
            + "; ".join(" == ".join(names) for names in duplicate_gate_codes)
        )
    return {
        "label": "neural_population_to_decoded_motor_output",
        "status": STATUS_DESCRIPTIVE,
        "source": data["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "observational_unit": (
            "decoder window (330) nested in simulation run (66); each run "
            "contributes five sequential 50 ms windows"
        ),
        "pools": list(data["pool_names"]),
        "pool_sizes": data["pool_sizes"][0].tolist(),
        "declared_state_names": list(data["state_names"]),
        "state_counts": state_counts,
        "pool_active_pattern_counts": pattern_counts,
        "gate_code_note": gate_code_note,
        "endpoints": endpoints,
        "per_window": per_window,
        "circularity": spec["circularity_warning"],
        "interpretation": (
            "The decoder declares a state from thresholds on the same pool "
            "activity used as the predictor. High mutual information is expected "
            "and confirms that the decoder is internally consistent. It is not "
            "evidence that the brain transmits motor commands, and the sequential "
            "windows inside a run are not independent trials."
        ),
    }


# ---------------------------------------------------------------------------
# E. cue -> action given condition (Phase 5E)
# ---------------------------------------------------------------------------


def analysis_conditional(config: dict, seed: int) -> dict:
    spec = config["conditional_information"]
    data = load_phase5e()
    cues: list[int] = []
    actions: list[int] = []
    strata: list[int] = []
    clusters: list[int] = []
    labels: list[str] = []
    for index, condition in enumerate(spec["conditions"]):
        block = data["conditions"][condition]
        valid = block["action"] >= 0
        if not np.any(valid):
            raise UnavailableEndpoint(
                f"condition {condition} records no chosen action"
            )
        cues.extend(block["cue"][valid].tolist())
        actions.extend(block["action"][valid].tolist())
        strata.extend([index] * int(np.count_nonzero(valid)))
        clusters.extend(
            (index * 10 + block["replicate_clusters"][valid]).tolist()
        )
        labels.append(condition)

    cue_array = np.asarray(cues, dtype=np.int64)
    action_array = np.asarray(actions, dtype=np.int64)
    stratum_array = np.asarray(strata, dtype=np.int64)
    cluster_array = np.asarray(clusters, dtype=np.int64)
    validate_equal_lengths(
        cue=cue_array, action=action_array, stratum=stratum_array, cluster=cluster_array
    )
    expected_clusters = [
        index * 10 + replicate
        for index in range(len(spec["conditions"]))
        for replicate in range(int(data["n_replicates"]))
    ]
    coverage = validate_cluster_coverage(
        cluster_array, expected_clusters, label="replicate clusters"
    )

    report = conditional_mutual_information_report(
        cue_array,
        action_array,
        stratum_array,
        min_stratum_n=config["support"]["min_stratum_n"],
    )
    marginal_report = mutual_information_report(cue_array, action_array)
    marginal = marginal_report["I_plugin"]
    cmi = report["I_conditional"]
    floor = float(np.mean([row["bias_floor"] for row in report["strata"]]))
    entropy_x = marginal_report["H_x"]
    entropy_y = marginal_report["H_y"]

    unique_strata = np.unique(stratum_array)
    stratum_groups = [np.flatnonzero(stratum_array == value) for value in unique_strata]
    rng = np.random.default_rng(seed)
    n_permutations = config["permutation"]["n_permutations_exploratory"]
    null = np.empty(n_permutations, dtype=np.float64)
    for index in range(n_permutations):
        shuffled = action_array.copy()
        for group in stratum_groups:
            shuffled[group] = rng.permutation(shuffled[group])
        null[index] = conditional_mutual_information_report(
            cue_array,
            shuffled,
            stratum_array,
            min_stratum_n=config["support"]["min_stratum_n"],
        )["I_conditional"]
    exceed = int(np.count_nonzero(null >= cmi))
    p_value = (exceed + 1) / (null.size + 1)

    unique_clusters = np.unique(cluster_array)
    n_resamples = config["bootstrap"]["n_resamples"]
    draws = np.empty(n_resamples, dtype=np.float64)
    for index in range(n_resamples):
        picked = rng.choice(unique_clusters, size=unique_clusters.size, replace=True)
        cue_draw = np.concatenate([cue_array[cluster_array == value] for value in picked])
        action_draw = np.concatenate(
            [action_array[cluster_array == value] for value in picked]
        )
        stratum_draw = np.concatenate(
            [stratum_array[cluster_array == value] for value in picked]
        )
        draws[index] = conditional_mutual_information_report(
            cue_draw, action_draw, stratum_draw, min_stratum_n=0
        )["I_conditional"]

    warnings = list(report["warnings"])
    if report["stratified_support_fraction"] < 1.0:
        warnings.append("some strata are below the declared minimum support")
    warnings.append(
        "conditioning removes between-condition composition; it does not "
        "identify a causal pathway"
    )

    return {
        "label": "cue_to_action_given_condition",
        "status": STATUS_EXPLORATORY,
        "source": spec["source"],
        "source_sha256": data["source_sha256"],
        "provenance": data["provenance"],
        "observational_unit": (
            "training episode (2880) clustered by replicate (18 = 6 conditions x "
            "3 replicates)"
        ),
        "conditions": list(spec["conditions"]),
        "excluded": list(spec["excluded"]),
        "stratum_names": labels,
        "n": report["n"],
        "effective_sample": effective_sample_size(cluster_array),
        "cluster_coverage": coverage,
        "marginal_mi_bits": round(float(marginal), 8),
        "conditional_mi_bits": cmi,
        "bias_floor_bits": round(floor, 8),
        "corrected_mi_bits": round(max(0.0, cmi - floor), 8),
        "marginal_entropy_bits": {"x": entropy_x, "y": entropy_y},
        "normalised_mi": (
            None
            if min(entropy_x, entropy_y) <= config["support"]["min_entropy_bits"]
            else round(cmi / min(entropy_x, entropy_y), 8)
        ),
        "strata": report["strata"],
        "stratified_support_fraction": report["stratified_support_fraction"],
        "null": {
            "scheme": "stratified free permutation of action within condition",
            "n_permutations": int(n_permutations),
            "null_mean": round(float(null.mean()), 8),
            "null_sd": round(float(null.std(ddof=1)), 8),
            "null_q95": round(float(np.quantile(null, 0.95)), 8),
            "null_max": round(float(null.max()), 8),
            "p_value": round(float(p_value), 8),
            "seed": int(seed),
        },
        "bootstrap_ci": {
            "low": round(float(np.quantile(draws, config["bootstrap"]["alpha"] / 2)), 8),
            "high": round(
                float(np.quantile(draws, 1 - config["bootstrap"]["alpha"] / 2)), 8
            ),
            "n_resamples": int(n_resamples),
            "n_clusters": int(unique_clusters.size),
            "seed": int(seed),
        },
        "warnings": warnings,
        "estimator": report["estimator"],
        "log_base": report["log_base"],
        "note": (
            "Phase 5E condition G is excluded because it records no chosen "
            "action. Strata are conditions A-F and the resampling unit is the "
            "replicate, so only 18 clusters exist."
        ),
    }


# ---------------------------------------------------------------------------
# unavailable endpoints with archived evidence
# ---------------------------------------------------------------------------


def raw_spike_inventory() -> list[dict]:
    inventory = []
    for path in RAW_SPIKE_ARTIFACTS:
        full = ROOT / path
        entry = {"path": path, "exists": full.is_file()}
        if not full.is_file():
            inventory.append(entry)
            continue
        entry["sha256"] = sha256_of(path)
        with np.load(full, allow_pickle=False) as arrays:
            keys = list(arrays.keys())
            time_keys = [key for key in keys if key.endswith("times_ms")]
            entry["keys"] = keys
            entry["n_spike_arrays"] = len(time_keys)
            entry["spike_counts"] = {
                key: int(arrays[key].size) for key in time_keys
            }
            entry["total_spikes"] = int(
                sum(arrays[key].size for key in time_keys)
            )
            if "n_neurons" in keys:
                entry["n_neurons"] = int(arrays["n_neurons"])
            entry["has_membrane_potential"] = any(
                token in key.lower()
                for key in keys
                for token in ("voltage", "membrane", "potential")
            )
        inventory.append(entry)
    return inventory


def unavailable_registry(config: dict) -> dict:
    replay = load_replay_neural_availability()
    banc = load_phase5_banc_conditions()
    phase5e = load_phase5e()
    inventory = raw_spike_inventory()

    cue_spike_counts = {}
    spike_counts = {}
    for condition, block in phase5e["conditions"].items():
        valid = block["n_cue_spikes"][block["n_cue_spikes"] >= 0]
        cue_spike_counts[condition] = sorted({int(value) for value in valid})
        valid_total = block["n_spikes"][block["n_spikes"] >= 0]
        spike_counts[condition] = sorted({int(value) for value in valid_total})

    banc_window_states = {
        condition: [window["state"] for window in block["windows"]]
        for condition, block in banc["conditions"].items()
    }
    banc_evidence = {
        "n_conditions": banc["n_conditions"],
        "windows_per_condition": banc["windows_per_condition"],
        "n_distinct_spike_hashes": banc["n_distinct_spike_hashes"],
        "spike_hashes": sorted(
            {block["spike_hash"] for block in banc["conditions"].values() if block["spike_hash"]}
        ),
        "decoded_state_sequence": banc_window_states,
        "window_start_ms": [
            window["window_start_ms"]
            for window in banc["conditions"][sorted(banc["conditions"])[0]]["windows"]
        ],
        "source": banc["source"],
        "source_sha256": banc["source_sha256"],
    }
    raw_evidence = {
        "artifacts": inventory,
        "largest_total_spikes": max(
            (entry.get("total_spikes", 0) for entry in inventory), default=0
        ),
        "any_membrane_potential_array": any(
            entry.get("has_membrane_potential", False) for entry in inventory
        ),
        "replay": replay,
    }

    evidence = {
        "U01": {
            "replay_source": replay["source"],
            "source_sha256": replay["source_sha256"],
            "n_frames": replay["n_frames"],
            "n_events": replay["n_events"],
            "spikes_total": replay["spikes_total"],
            "stimulated_neuron_count": replay["stimulated_neuron_count"],
            "simulation_keys": replay["simulation_keys"],
            "raw_spike_markers": replay["raw_spike_markers"],
            "per_neuron_spikes_persisted": replay["per_neuron_spikes_persisted"],
        },
        "U02": raw_evidence,
        "U03": raw_evidence,
        "U04": banc_evidence,
        "U05": {**banc_evidence, "reward_providers": {
            condition: block["reward_provider"]
            for condition, block in banc["conditions"].items()
        }},
        "U06": {"n_cue_spikes_by_condition": cue_spike_counts},
        "U07": {
            "n_spikes_by_condition": spike_counts,
            "chosen_action_by_condition": {
                condition: sorted(int(value) for value in np.unique(block["action"]))
                for condition, block in phase5e["conditions"].items()
            },
        },
    }

    checks = {
        "U01": not replay["per_neuron_spikes_persisted"],
        "U02": raw_evidence["largest_total_spikes"] < 10_000,
        "U03": not raw_evidence["any_membrane_potential_array"],
        "U04": banc["n_conditions"] > banc["n_distinct_spike_hashes"],
        "U05": banc["n_distinct_spike_hashes"] < banc["n_conditions"],
        "U06": all(
            values == [8] for values in cue_spike_counts.values() if values
        ),
        "U07": all(
            values == [12] or values == [11, 12]
            for condition, values in spike_counts.items()
            if condition != "G"
        ),
    }
    entries = []
    for item in config["unavailable"]:
        identifier = item["id"]
        entries.append(
            {
                "id": identifier,
                "label": item["label"],
                "status": "unavailable",
                "reason": item["reason"],
                "evidence": evidence.get(identifier, {}),
                "evidence_supports_reason": bool(checks.get(identifier, False)),
            }
        )
    return {
        "status": "at least one endpoint is unavailable",
        "entries": entries,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------


def _figure_dir(config: dict) -> Path:
    return ROOT / config["figures"]["directory"]


def draw_figures(payload: dict, config: dict) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory = _figure_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    blue = "#3d6fb4"
    red = "#b4373d"
    grey = "#777777"
    green = "#2f7d5a"

    def save(fig, name):
        path = directory / name
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(str(path.relative_to(ROOT)))

    sensory = payload["A_sensory_population"]
    distances = sensory["distances"]
    vector = sensory["response_vector_by_distance"]
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    positions = np.arange(len(vector[0]))
    width = 0.26
    for index, distance in enumerate(distances):
        ax.bar(
            positions + (index - 1) * width,
            vector[index],
            width=width,
            label=f"distance {distance:g}",
        )
    ax.set_xticks(positions, [f"neuron {i + 1}" for i in positions])
    ax.set_ylabel("spikes per run")
    ax.set_title(
        "Distance -> 4-neuron population response\n"
        f"n=9 runs, {len(sensory['mapping_seeds'])} mapping seeds, identical in all"
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    save(fig, "sensory_population_response.png")

    labels = list(sensory["endpoints"])
    values = [sensory["endpoints"][name]["raw_mi_bits"] for name in labels]
    floors = [sensory["endpoints"][name]["bias_floor_bits"] for name in labels]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar(np.arange(len(labels)), values, color=blue, width=0.6)
    ax.axhline(
        math.log2(3), color=green, linestyle="--", linewidth=1.2, label="log2(3) bits"
    )
    ax.scatter(
        np.arange(len(labels)),
        floors,
        marker="_",
        color=red,
        s=180,
        label="analytic bias floor",
    )
    ax.set_xticks(np.arange(len(labels)), labels, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("mutual information (bits)")
    ax.set_ylim(0, math.log2(3) * 1.15)
    ax.set_title("Sensory MI under declared binning variants\nn=9 runs, 3 clusters")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    save(fig, "sensory_mi_binning.png")

    sweep = payload["A_population_sweep"]
    sizes = [row["population_size"] for row in sweep["rows"]]
    joint = [row["joint_mi_bits"] for row in sweep["rows"]]
    summed = [row["sum_individual_mi_bits"] for row in sweep["rows"]]
    maximum = [row["max_individual_mi_bits"] for row in sweep["rows"]]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(sizes, joint, marker="o", color=blue, label="joint pattern MI")
    ax.plot(sizes, maximum, marker="s", color=green, label="best single neuron")
    ax.plot(sizes, summed, marker="^", color=red, label="sum over neurons")
    ax.axhline(math.log2(3), color=grey, linestyle=":", linewidth=1.0)
    ax.set_xlabel("population size (neurons)")
    ax.set_ylabel("mutual information (bits)")
    ax.set_title(
        "Distance information versus population size\n"
        "one mapping seed, 3 distances per size (descriptive)"
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    save(fig, "population_size_sensitivity.png")

    plasticity = payload["B_plasticity"]
    contrast_names = list(plasticity["contrasts"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for axis, name in zip(axes, contrast_names):
        block = plasticity["contrasts"][name]
        plastic = block["plastic_condition"]
        fixed = block["fixed_condition"]
        plastic_values = plasticity["conditions"][plastic]["per_checkpoint"][
            plasticity["final_checkpoint"]
        ]["per_seed_mi_bits"]
        fixed_values = plasticity["conditions"][fixed]["per_checkpoint"][
            plasticity["final_checkpoint"]
        ]["per_seed_mi_bits"]
        keys = sorted(plastic_values, key=int)
        for key in keys:
            axis.plot(
                [0, 1],
                [fixed_values[key], plastic_values[key]],
                color=grey,
                alpha=0.55,
                linewidth=1.0,
            )
        axis.scatter(
            np.zeros(len(keys)),
            [fixed_values[key] for key in keys],
            color=blue,
            s=26,
            zorder=3,
        )
        axis.scatter(
            np.ones(len(keys)),
            [plastic_values[key] for key in keys],
            color=red,
            s=26,
            zorder=3,
        )
        axis.scatter(
            [0, 1],
            [np.mean([fixed_values[key] for key in keys]),
             np.mean([plastic_values[key] for key in keys])],
            color="black",
            marker="D",
            s=55,
            zorder=4,
        )
        axis.axhline(
            block["bias_floor_bits_per_seed"],
            color=green,
            linestyle=":",
            linewidth=1.0,
        )
        axis.set_xticks([0, 1], [f"fixed\n({fixed})", f"plastic\n({plastic})"], fontsize=8)
        axis.set_title(
            f"{name}\nmean difference {block['mean_difference']:+.4f} bits, "
            f"p={block['sign_flip']['p_value']:.4f}",
            fontsize=9,
        )
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("I(cue; action) per seed (bits)")
    first = plasticity["contrasts"][contrast_names[0]]
    per_seed_episodes = plasticity["conditions"][first["fixed_condition"]][
        "per_checkpoint"
    ][plasticity["final_checkpoint"]]["observations_per_seed"]
    axes[0].text(
        0.02,
        0.02,
        f"{first['n_pairs']} seeds x {per_seed_episodes} episodes\n"
        f"bias floor {first['bias_floor_bits_per_seed']:.4f} bits",
        transform=axes[0].transAxes,
        fontsize=7,
        color=grey,
    )
    save(fig, "plasticity_paired_mi.png")

    conditions = list(plasticity["conditions"])
    checkpoints = plasticity["checkpoints"]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    width = 0.35
    positions = np.arange(len(conditions))
    for offset, checkpoint in enumerate(checkpoints):
        means = [
            plasticity["conditions"][condition]["per_checkpoint"][checkpoint][
                "summary"
            ]["mean"]
            for condition in conditions
        ]
        errors = [
            plasticity["conditions"][condition]["per_checkpoint"][checkpoint][
                "summary"
            ]["se"]
            or 0.0
            for condition in conditions
        ]
        ax.bar(
            positions + (offset - 0.5) * width,
            means,
            width=width,
            yerr=errors,
            capsize=3,
            label=f"checkpoint {checkpoint}",
            alpha=0.85,
        )
        for condition_index, condition in enumerate(conditions):
            values = plasticity["conditions"][condition]["per_checkpoint"][
                checkpoint
            ]["per_seed_mi_bits"]
            ax.scatter(
                np.full(len(values), positions[condition_index] + (offset - 0.5) * width),
                list(values.values()),
                color="black",
                s=8,
                alpha=0.5,
                zorder=3,
            )
    ax.set_xticks(positions, [condition.replace("_", "\n") for condition in conditions], fontsize=8)
    ax.set_ylabel("mean I(cue; action) per seed (bits)")
    ax.set_title(
        "Task information by condition and checkpoint\n"
        "bars: mean +/- SE over 10 seeds; dots: seeds"
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    save(fig, "plasticity_condition_mi.png")

    neural = payload["D_neural_motor"]
    names = list(neural["endpoints"])
    values = [neural["endpoints"][name]["raw_mi_bits"] for name in names]
    lows = [
        neural["endpoints"][name]["raw_mi_bits"]
        - neural["endpoints"][name]["bootstrap_ci"]["low"]
        for name in names
    ]
    highs = [
        neural["endpoints"][name]["bootstrap_ci"]["high"]
        - neural["endpoints"][name]["raw_mi_bits"]
        for name in names
    ]
    floors = [neural["endpoints"][name]["bias_floor_bits"] for name in names]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(np.arange(len(names)), values, color=blue, width=0.6)
    ax.errorbar(
        np.arange(len(names)), values, yerr=[lows, highs], fmt="none",
        ecolor="black", capsize=4,
    )
    ax.scatter(np.arange(len(names)), floors, marker="_", color=red, s=180, label="bias floor")
    ax.set_xticks(np.arange(len(names)), names, rotation=15, fontsize=8)
    ax.set_ylabel("I(pool activity; decoded state) (bits)")
    ax.set_title(
        "Pool activity -> decoded motor state\n"
        f"n={neural['endpoints'][names[0]]['n']} windows, "
        f"{neural['endpoints'][names[0]]['effective_sample']['n_clusters']} runs "
        "(descriptive; decoder uses the same activity)"
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    save(fig, "neural_motor_mi.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    window_keys = list(neural["per_window"])
    window_values = []
    window_errors = []
    window_labels = []
    for key in window_keys:
        block = neural["per_window"][key]
        starts = block.get("window_start_ms") or [float("nan")]
        ends = block.get("window_end_ms") or [float("nan")]
        window_labels.append(
            f"window {int(key) + 1}\n{starts[0]:g}-{ends[0]:g} ms"
        )
        if block["status"] == "not_estimable":
            window_values.append(0.0)
            window_errors.append([0.0, 0.0])
        else:
            window_values.append(block["raw_mi_bits"])
            window_errors.append(
                [
                    block["raw_mi_bits"] - block["bootstrap_ci"]["low"],
                    block["bootstrap_ci"]["high"] - block["raw_mi_bits"],
                ]
            )
    colors = [
        grey if neural["per_window"][key]["status"] == "not_estimable" else blue
        for key in window_keys
    ]
    ax.bar(np.arange(len(window_keys)), window_values, color=colors, width=0.6)
    for index, key in enumerate(window_keys):
        if neural["per_window"][key]["status"] != "not_estimable":
            ax.errorbar(
                index,
                window_values[index],
                yerr=[[window_errors[index][0]], [window_errors[index][1]]],
                fmt="none",
                ecolor="black",
                capsize=4,
            )
        else:
            ax.text(
                index,
                0.05,
                "not estimable\n(all NEUTRAL,\nno pool activity)",
                ha="center",
                va="bottom",
                fontsize=7,
                color=grey,
            )
    ax.set_xticks(np.arange(len(window_keys)), window_labels, fontsize=8)
    ax.set_ylabel("I(pool activity; decoded state) (bits)")
    ax.set_title(
        "Information by post-stimulus window\n"
        "n=66 runs per window; bars are 95% run-bootstrap intervals"
    )
    ax.grid(axis="y", alpha=0.25)
    save(fig, "neural_motor_by_window.png")

    ablation = payload["C_reward_ablation"]
    ablation_conditions = list(ablation["conditions"])
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for index, condition in enumerate(ablation_conditions):
        values = list(
            ablation["conditions"][condition]["per_replicate_mi_bits"].values()
        )
        ax.scatter(
            np.full(len(values), index) + np.linspace(-0.12, 0.12, len(values)),
            values,
            color=blue,
            s=30,
            alpha=0.8,
        )
        ax.hlines(
            np.mean(values),
            index - 0.25,
            index + 0.25,
            color=red,
            linewidth=2,
        )
    ax.set_xticks(
        np.arange(len(ablation_conditions)),
        [
            f"{condition}\n{ablation['conditions'][condition]['label'].replace('_', ' ')}"
            for condition in ablation_conditions
        ],
        fontsize=7,
    )
    ax.set_ylabel("I(cue; action) per replicate (bits)")
    ax.set_title(
        "Reward-modulation ablation\n"
        "3 replicates x 160 train episodes per condition (exploratory)"
    )
    ax.grid(axis="y", alpha=0.25)
    save(fig, "reward_ablation_mi.png")

    expected = config["figures"]["files"]
    missing = [name for name in expected if name not in {Path(path).name for path in written}]
    if missing:
        raise RuntimeError(f"figures were not written: {missing}")
    return written


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def build_payload(config: dict, *, quick: bool = False) -> dict:
    started = time.perf_counter()
    seed = int(config["seed"]["root"])
    if quick:
        config = json.loads(json.dumps(config))
        config["permutation"]["n_permutations_confirmatory"] = 200
        config["permutation"]["n_permutations_exploratory"] = 200
        config["bootstrap"]["n_resamples"] = 200

    payload = {
        "phase": 6,
        "title": config["title"],
        "status": "complete",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": (
            "python -m experiments.phase_6.run_information_analysis"
            + (" --quick" if quick else "")
        ),
        "quick": bool(quick),
        "config": {
            "path": str(CONFIG_PATH.relative_to(ROOT)),
            "sha256": sha256_file(CONFIG_PATH),
            "seed": config["seed"],
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "guardrails": [
            "Mutual information does not establish causation.",
            "Information about a label does not establish biological perception.",
            "Neural decoding does not prove the brain uses that information.",
            "Structural connectivity does not establish physiological information flow.",
            "Direct stimulation responses are not downstream activity.",
            "Phase 5 weight changes are not evidence of learning without behavioural evidence.",
            "Deterministic repeats are never treated as independent replicates.",
            "No gameplay label or ground truth was fabricated.",
        ],
        "design_coverage": {
            "sensory_input_to_neural_activity": [
                "A_sensory_population",
                "A_population_sweep",
                "U01",
                "U02",
            ],
            "gameplay_conditions_to_neural_activity": ["U01", "U06"],
            "neural_activity_to_motor_output": ["D_neural_motor"],
            "baseline_versus_plasticity_information": ["B_plasticity"],
            "reward_modulation_effects": ["C_reward_ablation", "U04", "U05"],
            "conditional_information": ["E_conditional_information"],
        },
        "A_sensory_population": analysis_sensory_population(config, seed + 10),
        "A_population_sweep": analysis_population_sweep(config),
        "B_plasticity": analysis_plasticity(config, seed + 1000),
        "C_reward_ablation": analysis_reward_ablation(config, seed + 2000),
        "D_neural_motor": analysis_neural_motor(config, seed + 3000),
        "E_conditional_information": analysis_conditional(config, seed + 4000),
        "unavailable": unavailable_registry(config),
    }
    payload["source_artifacts"] = {
        "sensory_stage": {
            "path": payload["A_sensory_population"]["source"],
            "sha256": payload["A_sensory_population"]["source_sha256"],
        },
        "population_sweep": {
            "path": payload["A_population_sweep"]["source"],
            "sha256": payload["A_population_sweep"]["source_sha256"],
        },
        "phase_5f": {
            "path": payload["B_plasticity"]["source"],
            "sha256": payload["B_plasticity"]["source_sha256"],
        },
        "phase_5e": {
            "path": payload["C_reward_ablation"]["source"],
            "sha256": payload["C_reward_ablation"]["source_sha256"],
        },
        "phase_4f": {
            "path": payload["D_neural_motor"]["source"],
            "sha256": payload["D_neural_motor"]["source_sha256"],
        },
        "phase_5_banc": {
            "path": PHASE_5_BANC_SOURCE,
            "sha256": sha256_of(PHASE_5_BANC_SOURCE),
        },
        "phase_3b2c_replay": {
            "path": PHASE_3B2C_SOURCE,
            "sha256": sha256_of(PHASE_3B2C_SOURCE),
        },
    }
    payload["summary"] = {
        "confirmatory_contrasts": {
            name: {
                "mean_difference_bits": block["mean_difference"],
                "sign_flip_p": block["sign_flip"]["p_value"],
                "holm_adjusted_p": payload["B_plasticity"]["holm"]["adjusted"][name],
                "rejected": payload["B_plasticity"]["holm"]["rejected"][name],
                "matched_control_max_abs_difference": block["matched_control"][
                    "max_abs_difference"
                ],
            }
            for name, block in payload["B_plasticity"]["contrasts"].items()
        },
        "sensory_mi_bits": payload["A_sensory_population"]["endpoints"][
            "exact_vector"
        ]["raw_mi_bits"],
        "neural_motor_mi_bits": payload["D_neural_motor"]["endpoints"][
            "any_active_pattern"
        ]["raw_mi_bits"],
        "conditional_mi_bits": payload["E_conditional_information"][
            "conditional_mi_bits"
        ],
        "unavailable_endpoints": [
            entry["id"] for entry in payload["unavailable"]["entries"]
        ],
    }
    payload["runtime_s"] = round(time.perf_counter() - started, 3)
    return json_safe(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6 information analysis")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="reduce permutation and bootstrap draws; writes to a separate file",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="skip figure generation",
    )
    args = parser.parse_args(argv)

    config = load_config()
    payload = build_payload(config, quick=args.quick)
    if not args.no_figures:
        if args.quick:
            quick_dir = OUT_DIR / "quick"
            quick_dir.mkdir(parents=True, exist_ok=True)
            quick_config = json.loads(json.dumps(config))
            quick_config["figures"]["directory"] = str(
                (quick_dir / "figures").relative_to(ROOT)
            )
            payload["figures"] = draw_figures(payload, quick_config)
        else:
            payload["figures"] = draw_figures(payload, config)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "information_analysis_quick.json" if args.quick else RESULTS_JSON
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"runtime {payload['runtime_s']} s")
    for name, block in payload["summary"]["confirmatory_contrasts"].items():
        print(
            f"  {name}: {block['mean_difference_bits']:+.4f} bits, "
            f"p={block['sign_flip_p']:.4f}, Holm p={block['holm_adjusted_p']:.4f}, "
            f"rejected={block['rejected']}"
        )
    print(
        "  sensory MI {:.4f} bits | neural-motor MI {:.4f} bits | "
        "conditional MI {:.4f} bits".format(
            payload["summary"]["sensory_mi_bits"],
            payload["summary"]["neural_motor_mi_bits"],
            payload["summary"]["conditional_mi_bits"],
        )
    )
    print(
        "  unavailable: " + ", ".join(payload["summary"]["unavailable_endpoints"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
