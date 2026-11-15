"""P3-T4 audit: resolve the Phase 3A.5 four-vs-twelve neuron discrepancy.

This script is read-only with respect to every completed experiment. It

* hashes the original calibration config, results and the shipped sensory
  config, and records the provenance timeline;
* reconstructs the four-neuron and twelve-neuron mappings from the same
  configuration and seed, without running a simulation;
* re-applies the original Phase 3A.5 selection rule to the archived
  population-stage and seed-stage measurements;
* lists every shipped consumer of the twelve-neuron configuration;
* states whether the discrepancy is explained by the archived evidence or
  whether a new controlled calibration is required.

It does not modify the connectome, the calibration results, the sensory
config or any Phase 3B/3C result. Nothing is staged, committed or pushed.

Usage:
    python experiments/phase_3c/p3_t4_calibration_discrepancy.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.connectome_loader import load_connectome  # noqa: E402
from experiments.phase_3_5.calibration import group_analysis  # noqa: E402
from sensory.sensory_experiment import load_config, prepare_setup  # noqa: E402

SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
CALIBRATION_CONFIG = PROJECT_ROOT / "configs" / "sensory_calibration.yaml"
CONNECTOME = PROJECT_ROOT / "datasets" / "processed" / "connectome.npz"
RESULTS_3A5 = PROJECT_ROOT / "experiments" / "phase_3_5" / "results"
REPORT_3A = PROJECT_ROOT / "experiments" / "phase_3" / "PHASE_3_REPORT.md"
REPORT_3A5 = PROJECT_ROOT / "experiments" / "phase_3_5" / "PHASE_3_5_REPORT.md"
OUTPUT_DIR = PROJECT_ROOT / "experiments" / "phase_3c" / "results"
FEATURE = "obstacle_distance"
SIZES = (4, 12)

# Every shipped consumer of configs/sensory_config.yaml, with the mechanism by
# which it obtains the twelve-neuron count. Paths are verified for existence
# and hashed at run time.
CONSUMERS = (
    (
        "experiments/phase_3/run_all.py",
        "loads configs/sensory_config.yaml directly",
    ),
    (
        "experiments/phase_3b/real_sequence_replay.py",
        "loads configs/sensory_config.yaml directly",
    ),
    (
        "experiments/phase_3c/causal_control.py",
        "loads configs/sensory_config.yaml; counts pinned in "
        "configs/causal_control_config.yaml",
    ),
    (
        "experiments/phase_3c/feature_ablation.py",
        "inherits causal_control conditions and the pinned counts",
    ),
    (
        "experiments/phase_3c/network_characterization.py",
        "inherits causal_control conditions and the pinned counts",
    ),
    (
        "experiments/phase_3c/integration_check.py",
        "loads configs/sensory_config.yaml directly",
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return {
        "head": head,
        "branch": branch,
        "working_tree_dirty": bool(status),
        "n_status_entries": len(status),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mapping_indices(graph, config: dict) -> dict[str, list[int]]:
    setup = prepare_setup(graph, config)
    return {
        feature: sorted(int(value) for value in population.indices)
        for feature, population in setup.mapping.populations.items()
    }


def annotation_evidence(graph, config: dict) -> dict:
    setup = prepare_setup(graph, config)
    return setup.mapping.populations[FEATURE].report(graph)


def one_spike_sensitivity(counts: list[int]) -> dict:
    """How many single +/-1 spike changes keep the sequence strictly monotone.

    A five-spike dynamic range driven by one neuron is one spike away from
    losing its ordering; this counts the admissible perturbations directly
    instead of asserting fragility.
    """
    n = len(counts)
    if n < 2:
        return {"n_single_changes": 0, "admissible": 0, "fraction": 0.0}
    direction = 1 if counts[-1] > counts[0] else -1
    if not (all(counts[i] < counts[i + 1] for i in range(n - 1))
            or all(counts[i] > counts[i + 1] for i in range(n - 1))):
        direction = 0
    admissible = 0
    total = 0
    for index in range(n):
        for delta in (-1, 1):
            if counts[index] + delta < 0:
                continue
            total += 1
            trial = list(counts)
            trial[index] += delta
            strict = all(
                trial[i] < trial[i + 1] for i in range(n - 1)
            ) or all(trial[i] > trial[i + 1] for i in range(n - 1))
            if strict and (direction == 0 or (
                (direction > 0 and trial[-1] > trial[0])
                or (direction < 0 and trial[-1] < trial[0])
            )):
                admissible += 1
    return {
        "n_single_changes": total,
        "admissible": admissible,
        "fraction": round(admissible / total, 4) if total else 0.0,
    }


def population_group(stage: dict, size: int) -> dict:
    for group in stage["groups"]:
        if int(group["parameters"]["population_size"]) == size:
            return group
    raise KeyError(f"population size {size} not present in population stage")


def level_rows(group: dict) -> list[dict]:
    rows = []
    for condition in group["conditions"]:
        cal = condition["calibration"]["by_feature"][FEATURE]
        rows.append(
            {
                "name": condition["name"],
                "factors": condition["factors"],
                "calibration": {"by_feature": {FEATURE: cal}},
                "input": condition["input"],
                "activity": condition["activity"],
            }
        )
    return rows


def response_block(group: dict) -> dict:
    rows = level_rows(group)
    analysis = group_analysis(rows, FEATURE)
    per_level = []
    for condition in sorted(
        group["conditions"], key=lambda item: item["factors"]["distance"]
    ):
        cal = condition["calibration"]["by_feature"][FEATURE]
        per_level.append(
            {
                "distance": condition["factors"]["distance"],
                "spikes": cal["spikes"],
                "active_neurons": cal["active_neurons"],
                "recruitment_fraction": cal["recruitment_fraction"],
                "spikes_per_neuron": cal["spikes_per_neuron"],
                "first_spike_ms": cal["latency_ms"]["first_ms"],
                "median_spike_ms": cal["latency_ms"]["median_ms"],
                "peak_feature_current_pa": condition["input"][
                    "peak_feature_current_pa"
                ][FEATURE],
                "max_per_neuron_current_pa": condition["input"][
                    "max_per_neuron_current_pa"
                ],
                "network_spikes": condition["activity"]["n_spikes"],
                "network_active_neurons": condition["activity"][
                    "active_neurons"
                ],
            }
        )
    analysis["one_spike_sensitivity"] = one_spike_sensitivity(
        analysis["spike_counts"]
    )
    return {"analysis": analysis, "per_level": per_level}


def seed_block(stage: dict, size: int) -> dict:
    rows = []
    for group in stage["groups"]:
        factors = group["conditions"][0]["factors"]
        if int(factors["population_size"]) != size:
            continue
        analysis = group_analysis(level_rows(group), FEATURE)
        rows.append(
            {
                "mapping_seed": int(group["parameters"]["mapping_seed"]),
                "spike_counts": analysis["spike_counts"],
                "ordered": analysis["ordered"],
                "d_prime_proxy": analysis["d_prime_proxy"],
                "dynamic_range": analysis["dynamic_range"],
            }
        )
    return {
        "seeds": rows,
        "n_ordered": sum(1 for row in rows if row["ordered"]),
        "n_seeds": len(rows),
        "source": "seed_stage",
    }


def seed_coverage(
    stage_seeds: dict, stage_population: dict, size: int, default_seed: int
) -> dict:
    """Seed evidence per size, falling back to the single population-stage seed.

    The archived seed stage was run only at the selected size, so the other
    size has one measured seed, not three. Reporting 0/0 would hide that.
    """
    block = seed_block(stage_seeds, size)
    if block["n_seeds"]:
        return block
    group = population_group(stage_population, size)
    analysis = group_analysis(level_rows(group), FEATURE)
    seed = int(default_seed)
    return {
        "seeds": [
            {
                "mapping_seed": seed,
                "spike_counts": analysis["spike_counts"],
                "ordered": analysis["ordered"],
                "d_prime_proxy": analysis["d_prime_proxy"],
                "dynamic_range": analysis["dynamic_range"],
            }
        ],
        "n_ordered": 1 if analysis["ordered"] else 0,
        "n_seeds": 1,
        "source": "population_stage_single_seed",
    }


def compare_mappings(mapping_4: dict, mapping_12: dict) -> dict:
    set4 = set(mapping_4[FEATURE])
    set12 = set(mapping_12[FEATURE])
    shifted = {}
    for feature in mapping_12:
        left = set(mapping_4[feature])
        right = set(mapping_12[feature])
        if left != right:
            shifted[feature] = {
                "n_4": len(left),
                "n_12": len(right),
                "shared": len(left & right),
                "only_4": len(left - right),
                "only_12": len(right - left),
            }
    return {
        "feature": FEATURE,
        "indices_4": sorted(set4),
        "indices_12": sorted(set12),
        "size_4": len(set4),
        "size_12": len(set12),
        "four_is_subset_of_twelve": set4.issubset(set12),
        "shared": len(set4 & set12),
        "features_with_changed_indices": shifted,
        "n_features_with_changed_indices": len(shifted),
    }


def main() -> dict:
    config = load_config(SENSORY_CONFIG)
    graph = load_connectome(CONNECTOME)

    config4 = json.loads(json.dumps(config))
    config4["features"][FEATURE]["n_neurons"] = 4
    config4["features"][FEATURE]["current_pa"] = 200.0
    config4["features"][FEATURE]["sigma_fraction"] = 0.20
    config4["mapping"]["populations"][FEATURE]["n_neurons"] = 4
    config4["mapping"]["seed"] = 20261104

    mapping_12 = mapping_indices(graph, config)
    mapping_4 = mapping_indices(graph, config4)
    comparison = compare_mappings(mapping_4, mapping_12)

    stage_population = load_json(RESULTS_3A5 / "stage_population.json")
    stage_seeds = load_json(RESULTS_3A5 / "stage_seeds.json")
    selection = load_json(RESULTS_3A5 / "selection.json")

    responses = {
        str(size): response_block(population_group(stage_population, size))
        for size in SIZES
    }
    calibration_config = yaml.safe_load(
        CALIBRATION_CONFIG.read_text(encoding="utf-8")
    )
    default_seed = int(calibration_config["calibration"]["mapping_seed"])
    seeds = {
        str(size): seed_coverage(
            stage_seeds, stage_population, size, default_seed
        )
        for size in SIZES
    }

    evidence4 = annotation_evidence(graph, config4)
    evidence12 = annotation_evidence(graph, config)

    shipped_counts = {
        feature: (
            int(payload["lanes"]) * int(payload["neurons_per_lane"])
            if payload["kind"] == "lane"
            else int(payload["n_neurons"])
        )
        for feature, payload in config["features"].items()
    }

    consumers = []
    for relative, mechanism in CONSUMERS:
        path = PROJECT_ROOT / relative
        consumers.append(
            {
                "path": relative,
                "mechanism": mechanism,
                "sha256": sha256(path) if path.exists() else None,
                "exists": path.exists(),
            }
        )

    # Decision fields are derived from the archived evidence, not asserted.
    a4 = responses["4"]["analysis"]
    a12 = responses["12"]["analysis"]
    original_rule = {
        "eligible": "at least one spike and not fully saturated at every level",
        "ordered": "strictly monotone spike counts across 0.15/0.55/0.90",
        "seed_gate": "ordered in at least two of three mapping seeds",
    }
    comparison_outcome = {
        "four_neurons": {
            "eligible": a4["eligible"],
            "ordered": a4["ordered"],
            "ordered_seeds": seeds["4"]["n_ordered"],
            "seed_gate_met": seeds["4"]["n_ordered"] >= 2,
            "meets_original_rule": bool(
                a4["eligible"] and a4["ordered"] and seeds["4"]["n_ordered"] >= 2
            ),
        },
        "twelve_neurons": {
            "eligible": a12["eligible"],
            "ordered": a12["ordered"],
            "ordered_seeds": seeds["12"]["n_ordered"],
            "seed_gate_met": seeds["12"]["n_ordered"] >= 2,
            "meets_original_rule": bool(
                a12["eligible"] and a12["ordered"]
                and seeds["12"]["n_ordered"] >= 2
            ),
        },
        "original_rule": original_rule,
    }

    payload = {
        "phase": "P3-T4",
        "version": "p3_t4_calibration_discrepancy_v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "git": git_state(),
        "provenance": {
            "files": {
                "configs/sensory_config.yaml": {
                    "sha256": sha256(SENSORY_CONFIG),
                    "mtime_utc": dt.datetime.fromtimestamp(
                        SENSORY_CONFIG.stat().st_mtime, dt.timezone.utc
                    ).isoformat(timespec="seconds"),
                },
                "configs/sensory_calibration.yaml": {
                    "sha256": sha256(CALIBRATION_CONFIG),
                    "mtime_utc": dt.datetime.fromtimestamp(
                        CALIBRATION_CONFIG.stat().st_mtime, dt.timezone.utc
                    ).isoformat(timespec="seconds"),
                },
                "experiments/phase_3_5/results/selection.json": {
                    "sha256": sha256(RESULTS_3A5 / "selection.json"),
                },
                "experiments/phase_3_5/results/stage_population.json": {
                    "sha256": sha256(RESULTS_3A5 / "stage_population.json"),
                },
                "experiments/phase_3_5/results/stage_seeds.json": {
                    "sha256": sha256(RESULTS_3A5 / "stage_seeds.json"),
                },
                "experiments/phase_3/PHASE_3_REPORT.md": {
                    "sha256": sha256(REPORT_3A),
                },
                "experiments/phase_3_5/PHASE_3_5_REPORT.md": {
                    "sha256": sha256(REPORT_3A5),
                },
            },
            "shipped_gaussian_counts": shipped_counts,
            "selection": selection,
            "timeline": {
                "phase_3a_config_mtime_utc": dt.datetime.fromtimestamp(
                    SENSORY_CONFIG.stat().st_mtime, dt.timezone.utc
                ).isoformat(timespec="seconds"),
                "phase_3a_report_generated_utc": "2026-11-04T12:56:31+00:00",
                "phase_3a5_calibration_config_mtime_utc": dt.datetime.fromtimestamp(
                    CALIBRATION_CONFIG.stat().st_mtime, dt.timezone.utc
                ).isoformat(timespec="seconds"),
                "phase_3a5_report_generated_utc": "2026-11-04T14:27:29+00:00",
                "note": (
                    "the twelve-neuron count is present in the Phase 3A config "
                    "that the Phase 3A.5 calibration takes as its base; the "
                    "four-neuron selection was produced afterwards and was "
                    "never written back"
                ),
            },
            "documentation_of_mismatch": [
                "docs/PHASE_3_SENSORY_ENCODING.md (§Operating-point mismatch)",
                "docs/PHASE_3C_TEMPORAL_SENSORY_DESIGN.md (§6)",
                "docs/PHASE_3_ROADMAP.md (§4.2 and §3C protocol)",
            ],
        },
        "mapping": {
            "mapping_seed": 20261104,
            "comparison": comparison,
            "obstacle_distance_evidence_4": evidence4.get("evidence"),
            "obstacle_distance_evidence_12": evidence12.get("evidence"),
        },
        "responses": responses,
        "seeds": seeds,
        "outcome": comparison_outcome,
        "consumers": consumers,
        "notes": [
            "Spike counts are simulated model output at 300 ms, zero background "
            "current and zero noise; they are not biological measurements.",
            "The four-neuron mapping is a prefix of the twelve-neuron mapping, "
            "but shrinking the population releases eight visual_any neurons to "
            "the four features allocated after it, so a full-network 4-vs-12 "
            "comparison is not a single-factor change without a mapping "
            "override.",
        ],
    }
    return payload


def write_outputs(payload: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "p3_t4_calibration_discrepancy.json"
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(output)
    sidecar = {
        "output": output.name,
        "phase": "P3-T4",
        "version": payload["version"],
        "generated_at_utc": payload["generated_at_utc"],
        "config_sha256": payload["provenance"]["files"][
            "configs/sensory_config.yaml"
        ]["sha256"],
        "calibration_config_sha256": payload["provenance"]["files"][
            "configs/sensory_calibration.yaml"
        ]["sha256"],
        "git": payload["git"],
    }
    sidecar_path = OUTPUT_DIR / "p3_t4_calibration_discrepancy.sidecar.json"
    sidecar_tmp = sidecar_path.with_suffix(".json.tmp")
    sidecar_tmp.write_text(
        json.dumps(sidecar, indent=2) + "\n", encoding="utf-8"
    )
    sidecar_tmp.replace(sidecar_path)
    return output


def main_entry() -> None:
    payload = main()
    output = write_outputs(payload)
    comparison = payload["mapping"]["comparison"]
    print(f"wrote {output}")
    print(
        "four-neuron subset of twelve:",
        comparison["four_is_subset_of_twelve"],
        "| features remapped:",
        comparison["n_features_with_changed_indices"],
    )
    for size in ("4", "12"):
        analysis = payload["responses"][size]["analysis"]
        seeds = payload["seeds"][size]
        print(
            f"size {size:>2}: spikes {analysis['spike_counts']} "
            f"ordered={analysis['ordered']} dynamic_range="
            f"{analysis['dynamic_range']} d'={analysis['d_prime_proxy']} "
            f"ordered_seeds={seeds['n_ordered']}/{seeds['n_seeds']}"
        )
    print("outcome:", json.dumps(payload["outcome"], indent=2))


if __name__ == "__main__":
    main_entry()
