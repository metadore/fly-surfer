"""Phase 6B: Shannon entropy of archived FLY-SURFER variables.

Reads only existing Phase 3B, 4F, 4H and 5E/5F artifacts. Computes marginal,
joint and conditional entropy in bits with plug-in and Miller-Madow
estimators, cluster bootstrap confidence intervals and an explicit record of
every discretisation. No simulation, no new recording, no imputation.
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
    load_decoder_windows,
    load_events,
    load_frame_event_counts,
    load_phase5e,
    sha256_of,
)
from information.bias_correction import entropy_bias_correction, mi_bias_floor  # noqa: E402
from information.diagnostics import effective_sample_size  # noqa: E402
from information.discretization import declared, equal_width  # noqa: E402
from information.entropy import (  # noqa: E402
    conditional_entropy,
    entropy_report,
    joint_entropy_report,
)
from information.mutual_information import mutual_information  # noqa: E402
from information.permutation import entropy_bootstrap_ci  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "information_theory.yaml"
OUT_DIR = ROOT / "experiments" / "results" / "phase_6b"
RESULTS_JSON = OUT_DIR / "entropy_results.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def entropy_block(
    codes,
    labels,
    *,
    name: str,
    label: str,
    provenance: str,
    clusters,
    seed: int,
    n_resamples: int,
    min_n: int,
    extra: dict | None = None,
) -> dict:
    """Entropy estimate with bias comparison, cluster CI and diagnostics."""
    coded = declared(codes, labels, name)
    report = entropy_report(coded)
    summary = coded.summary()
    bootstrap = entropy_bootstrap_ci(coded.codes, clusters, n_resamples=n_resamples, seed=seed)
    sample = effective_sample_size(clusters)
    warnings: list[str] = []
    if report["n_missing"]:
        warnings.append(f"{report['n_missing']} missing observations excluded")
    if report["k_observed"] < report["k_declared"]:
        warnings.append(
            f"{report['k_declared'] - report['k_observed']} declared level(s) never observed"
        )
    if report["n"] < min_n:
        warnings.append(f"n={report['n']} below minimum {min_n}; exploratory")
    if sample["n_clusters"] < 10:
        warnings.append(
            f"only {sample['n_clusters']} clusters; cluster bootstrap is unstable"
        )
    block = {
        "label": label,
        "variable": name,
        "provenance": provenance,
        "discretization": {
            "kind": summary["spec"]["kind"],
            "labels": list(labels),
            "counts": summary["counts"],
            "empty_bins": summary["empty_bins"],
        },
        "entropy": report,
        "bias": {
            "plugin_bits": report["H_plugin"],
            "miller_madow_bits": report["H_miller_madow"],
            "delta_bits": round(report["H_miller_madow"] - report["H_plugin"], 8),
            "analytic_correction_bits": round(
                entropy_bias_correction(report["k_observed"], report["n"]), 8
            ),
        },
        "excess_over_max_bits": (
            None
            if not np.isfinite(report["H_max_declared"])
            else round(report["H_max_declared"] - report["H_plugin"], 8)
        ),
        "bootstrap_ci": bootstrap,
        "effective_sample": sample,
        "warnings": warnings,
    }
    if extra:
        block.update(extra)
    return block


def endpoint_events(config: dict, seed: int) -> dict:
    """E-01: marginal entropy of the six abstract tracked-object event classes."""
    data = load_events()
    support = config["support"]
    block = entropy_block(
        data["class_codes"],
        data["class_names"],
        name="event_class",
        label="event_class_marginal",
        provenance="measured",
        clusters=data["frame_clusters"],
        seed=seed,
        n_resamples=config["bootstrap"]["n_resamples"],
        min_n=support["min_n"],
        extra={
            "source_hashes": data["source_hashes"],
            "per_segment": {
                name: {"n": info["n"], "class_counts": info["class_counts"]}
                for name, info in data["per_segment"].items()
            },
        },
    )
    per_segment = {}
    for index, name in enumerate(data["segment_names"]):
        sel = data["segment_codes"] == index
        coded = declared(data["class_codes"][sel], data["class_names"], "event_class")
        report = entropy_report(coded)
        per_segment[name] = {
            "n": report["n"],
            "k_observed": report["k_observed"],
            "H_plugin": report["H_plugin"],
            "H_miller_madow": report["H_miller_madow"],
            "n_frame_clusters": int(np.unique(data["frame_clusters"][sel]).size),
        }
    block["per_segment_entropy"] = per_segment
    return block


def endpoint_frame_counts(config: dict, seed: int) -> dict:
    """E-02: entropy of the coarse per-frame event-channel activity code."""
    support = config["support"]
    disc = config["discretization"]
    data = load_frame_event_counts(block_frames=disc["frame_block_frames"])
    labels = ["0", "1", "2", "3+"]
    block = entropy_block(
        data["counts"],
        labels,
        name="frame_event_count",
        label="frame_event_count",
        provenance="derived",
        clusters=data["block_clusters"],
        seed=seed,
        n_resamples=config["bootstrap"]["n_resamples"],
        min_n=support["min_n"],
        extra={
            "counts_histogram": [int(c) for c in np.bincount(data["counts"], minlength=4)],
            "block_frames": disc["frame_block_frames"],
            "n_frames_per_segment": data["n_frames_per_segment"],
        },
    )
    sensitivity = []
    for cap in (1, 2, 3, 5):
        recoded = np.minimum(data["counts"], cap)
        labels_at_cap = [str(v) for v in range(cap)] + [f"{cap}+"]
        coded = declared(recoded, labels_at_cap, "frame_event_count")
        report = entropy_report(coded)
        sensitivity.append(
            {"cap": cap, "k_declared": report["k_declared"], "H_plugin": report["H_plugin"]}
        )
    block["cap_sensitivity"] = sensitivity
    return block


def endpoint_decoder_state(config: dict, seed: int) -> dict:
    """E-03: entropy of the decoded motor state per analysis window."""
    data = load_decoder_windows()
    return entropy_block(
        data["state_codes"],
        data["state_names"],
        name="decoded_state",
        label="decoder_state",
        provenance="simulated",
        clusters=data["run_clusters"],
        seed=seed,
        n_resamples=config["bootstrap"]["n_resamples"],
        min_n=config["support"]["min_n"],
        extra={
            "source": DECODER_SOURCE,
            "source_sha256": data["source_sha256"],
            "n_runs": data["n_runs"],
            "window_note": "5 windows per run; runs are the independent unit",
        },
    )


def endpoint_decoder_score(config: dict, seed: int) -> dict:
    """E-04: entropy of the binned maximum raw decoder score per window."""
    data = load_decoder_windows()
    disc = config["discretization"]
    bins = disc["decoder_score_bins"]
    low, high = disc["decoder_score_range"]
    coded = equal_width(data["max_score"], bins, "decoder_max_score", low=low, high=high)
    block = entropy_block(
        coded.codes,
        coded.labels,
        name="decoder_max_score_bin",
        label="decoder_max_score_bin",
        provenance="simulated",
        clusters=data["run_clusters"],
        seed=seed,
        n_resamples=config["bootstrap"]["n_resamples"],
        min_n=config["support"]["min_n"],
        extra={
            "bin_edges": coded.summary()["spec"].get("edges"),
            "source_discretization": coded.summary()["spec"],
        },
    )
    sensitivity = []
    for count in (2, 3, 4, 5):
        recoded = equal_width(data["max_score"], count, "decoder_max_score", low=low, high=high)
        report = entropy_report(recoded)
        sensitivity.append(
            {
                "bins": count,
                "H_plugin": report["H_plugin"],
                "counts": recoded.summary()["counts"],
            }
        )
    block["bin_count_sensitivity"] = sensitivity
    return block


def endpoint_reward(config: dict, seed: int) -> dict:
    """E-05: entropy of the three-level episode reward in every 5E condition."""
    data = load_phase5e()
    labels = ["-1", "0", "+1"]
    support = config["support"]
    per_condition = {}
    for condition, block in data["conditions"].items():
        per_condition[condition] = entropy_block(
            block["reward"],
            labels,
            name="reward_level",
            label=block["label"],
            provenance="simulated",
            clusters=block["replicate_clusters"],
            seed=seed,
            n_resamples=config["bootstrap"]["n_resamples"],
            min_n=support["min_n"],
            extra={"condition": condition},
        )
    return {
        "label": "episode_reward",
        "source_sha256": data["source_sha256"],
        "n_replicates": data["n_replicates"],
        "reward_levels": data["reward_levels"],
        "per_condition": per_condition,
        "note": (
            "Each condition has only 3 replicate clusters, so the cluster bootstrap "
            "cannot separate replicate-level variation from episode-level noise."
        ),
    }


def endpoint_event_by_segment(config: dict, seed: int) -> dict:
    """E-06: joint and conditional entropy of event class and segment."""
    data = load_events()
    classes = declared(data["class_codes"], data["class_names"], "event_class")
    segments = declared(data["segment_codes"], data["segment_names"], "segment")
    joint = joint_entropy_report(classes, segments)
    conditional = conditional_entropy(classes, segments)
    return {
        "label": "event_class_by_segment",
        "provenance": "measured",
        "joint": joint,
        "conditional_H_event_given_segment": round(conditional, 8),
        "H_event": entropy_report(classes)["H_plugin"],
        "mutual_information_bits": round(mutual_information(classes, segments), 8),
        "interpretation": (
            "H(event) - H(event|segment) is the information the segment label "
            "carries about the event class; it is reported here as a descriptive "
            "quantity, not a hypothesis test."
        ),
        "segment_entropy": entropy_report(segments)["H_plugin"],
    }


def draw_figure(payload: dict, path: Path) -> None:
    """Two-panel entropy summary: main endpoints and reward conditions."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [(k, b) for k, b in payload["endpoints"].items() if "entropy" in b]
    names = [block["label"] for _, block in rows]
    values = [block["entropy"]["H_plugin"] for _, block in rows]
    low = [
        block["entropy"]["H_plugin"] - block["bootstrap_ci"]["low"] for _, block in rows
    ]
    high = [
        block["bootstrap_ci"]["high"] - block["entropy"]["H_plugin"] for _, block in rows
    ]
    maxima = [block["entropy"]["H_max_declared"] for _, block in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    positions = np.arange(len(rows))
    axes[0].barh(positions, values, color="#3d6fb4", height=0.55)
    axes[0].errorbar(values, positions, xerr=[low, high], fmt="none", ecolor="#222", capsize=3)
    axes[0].scatter(maxima, positions, marker="|", color="#b4373d", s=120, label="max for declared support")
    axes[0].set_yticks(positions, names)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("entropy (bits)")
    axes[0].set_title("Archived endpoints, cluster bootstrap 95% CI")
    axes[0].legend(loc="lower right", fontsize=8)

    reward = payload["E05_episode_reward"]["per_condition"]
    conditions = list(reward)
    rvalues = [reward[c]["entropy"]["H_plugin"] for c in conditions]
    rlow = [reward[c]["entropy"]["H_plugin"] - reward[c]["bootstrap_ci"]["low"] for c in conditions]
    rhigh = [reward[c]["bootstrap_ci"]["high"] - reward[c]["entropy"]["H_plugin"] for c in conditions]
    axes[1].bar(conditions, rvalues, color="#5f9e6e")
    axes[1].errorbar(
        conditions, rvalues, yerr=[rlow, rhigh], fmt="none", ecolor="#222", capsize=3
    )
    axes[1].axhline(np.log2(3), linestyle="--", color="#b4373d", linewidth=1, label="log2(3)")
    axes[1].set_ylabel("entropy (bits)")
    axes[1].set_title("Episode reward entropy, Phase 5E conditions")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def bias_comparison(endpoints: dict) -> list[dict]:
    """Side-by-side plug-in and Miller-Madow estimates for every marginal."""
    rows = []
    for key, block in endpoints.items():
        if "entropy" not in block:
            continue
        report = block["entropy"]
        rows.append(
            {
                "endpoint": key,
                "label": block["label"],
                "n": report["n"],
                "k_observed": report["k_observed"],
                "H_plugin": report["H_plugin"],
                "H_miller_madow": report["H_miller_madow"],
                "delta_bits": block["bias"]["delta_bits"],
                "delta_fraction": (
                    None
                    if not report["H_plugin"]
                    else round(block["bias"]["delta_bits"] / report["H_plugin"], 6)
                ),
            }
        )
    return rows


def unavailable_endpoints(config: dict) -> list[dict]:
    return [dict(item) for item in config["unavailable"]]


def main() -> dict:
    started = time.perf_counter()
    config = load_config()
    seed = int(config["seed"]["bootstrap"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    endpoints = {
        "E01_event_class_marginal": endpoint_events(config, seed),
        "E02_frame_event_count": endpoint_frame_counts(config, seed),
        "E03_decoder_state": endpoint_decoder_state(config, seed),
        "E04_decoder_score_bin": endpoint_decoder_score(config, seed),
        "E06_event_class_by_segment": endpoint_event_by_segment(config, seed),
    }
    reward = endpoint_reward(config, seed)
    payload = {
        "phase": "6B",
        "title": "Shannon entropy of archived FLY-SURFER variables",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "log_base": 2,
        "data_sources": "archived artifacts only; no new recording, no simulation",
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "config_sha256": sha256_file(CONFIG_PATH),
        "seed": seed,
        "permutation_note": (
            "Entropy has no exchangeability null, so no permutation test is "
            "performed in 6B. Uncertainty is reported with a cluster bootstrap."
        ),
        "endpoints": endpoints,
        "E05_episode_reward": reward,
        "bias_comparison": bias_comparison(endpoints),
        "unavailable": unavailable_endpoints(config),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    draw_figure(payload, OUT_DIR / "figures" / "entropy_summary.png")
    with open(RESULTS_JSON, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")
    return payload


if __name__ == "__main__":
    result = main()
    print(f"wrote {RESULTS_JSON}")
    for row in result["bias_comparison"]:
        print(
            f"{row['endpoint']:<28} n={row['n']:<4} k={row['k_observed']} "
            f"H={row['H_plugin']:.4f} MM={row['H_miller_madow']:.4f}"
        )
    for condition, block in result["E05_episode_reward"]["per_condition"].items():
        report = block["entropy"]
        print(f"reward {condition} n={report['n']} H={report['H_plugin']:.4f}")
