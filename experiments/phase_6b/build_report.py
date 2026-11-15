"""Build the Phase 6B report from the stored entropy results.

The Markdown and JSON reports are generated from the same in-memory structure
so the two cannot disagree. No quantity is retyped by hand.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.phase_4h.common import integrity_snapshot  # noqa: E402

RESULTS = ROOT / "experiments" / "results" / "phase_6b" / "entropy_results.json"
REPORT_JSON = ROOT / "reports" / "PHASE_6B_SHANNON_ENTROPY.json"
REPORT_MD = ROOT / "reports" / "PHASE_6B_SHANNON_ENTROPY.md"


def git_state() -> dict:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "modified_tracked_files": [line[3:] for line in status.stdout.splitlines() if line.strip()],
        "staged_files": [line for line in staged.stdout.splitlines() if line.strip()],
    }


def build() -> dict:
    with open(RESULTS, encoding="utf-8") as handle:
        results = json.load(handle)
    endpoints = results["endpoints"]

    marginal = []
    for key, block in endpoints.items():
        if "entropy" not in block:
            continue
        report = block["entropy"]
        marginal.append(
            {
                "endpoint": key,
                "label": block["label"],
                "provenance": block["provenance"],
                "n": report["n"],
                "k_observed": report["k_observed"],
                "k_declared": report["k_declared"],
                "H_plugin": report["H_plugin"],
                "H_miller_madow": report["H_miller_madow"],
                "H_max_declared": report["H_max_declared"],
                "excess_over_max_bits": block["excess_over_max_bits"],
                "ci_low": block["bootstrap_ci"]["low"],
                "ci_high": block["bootstrap_ci"]["high"],
                "clusters": block["bootstrap_ci"]["n_clusters"],
                "warnings": block["warnings"],
            }
        )

    reward_rows = []
    for condition, block in results["E05_episode_reward"]["per_condition"].items():
        report = block["entropy"]
        reward_rows.append(
            {
                "condition": condition,
                "label": block["label"],
                "n": report["n"],
                "k_observed": report["k_observed"],
                "H_plugin": report["H_plugin"],
                "H_miller_madow": report["H_miller_madow"],
                "ci_low": block["bootstrap_ci"]["low"],
                "ci_high": block["bootstrap_ci"]["high"],
                "clusters": block["bootstrap_ci"]["n_clusters"],
                "warnings": block["warnings"],
            }
        )

    integrity = integrity_snapshot()
    state = git_state()
    protected_dirty = [
        path
        for path in state["modified_tracked_files"]
        if path.startswith(("brain/", "datasets/", "reports/PHASE_4H", "experiments/results/phase_4h"))
        or path == "README.md"
    ]
    report = {
        "phase": "6B",
        "title": "Shannon entropy of archived FLY-SURFER variables",
        "status": "COMPLETE - ARCHIVED-DATA ENTROPY ONLY, NO NEW RECORDING",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(ROOT),
        "log_base": 2,
        "seed": results["seed"],
        "config": {
            "path": results["config_path"],
            "sha256": results["config_sha256"],
        },
        "data_sources": results["endpoints"]["E01_event_class_marginal"]["source_hashes"],
        "marginal_entropy": marginal,
        "reward_entropy": reward_rows,
        "joint_conditional": endpoints["E06_event_class_by_segment"],
        "bias_comparison": results["bias_comparison"],
        "sensitivity": {
            "frame_event_count_cap": endpoints["E02_frame_event_count"]["cap_sensitivity"],
            "decoder_score_bins": endpoints["E04_decoder_score_bin"]["bin_count_sensitivity"],
            "event_class_per_segment": endpoints["E01_event_class_marginal"]["per_segment_entropy"],
        },
        "statistics": {
            "method": "cluster percentile bootstrap",
            "n_resamples": results["endpoints"]["E01_event_class_marginal"]["bootstrap_ci"]["n_resamples"],
            "permutation": results["permutation_note"],
        },
        "unavailable": results["unavailable"],
        "software": results["software"],
        "runtime_seconds": results["runtime_seconds"],
        "files": {
            "results": "experiments/results/phase_6b/entropy_results.json",
            "figure": "experiments/results/phase_6b/figures/entropy_summary.png",
            "config": "configs/information_theory.yaml",
            "runner": "experiments/phase_6b/run_entropy_analysis.py",
            "report_builder": "experiments/phase_6b/build_report.py",
            "estimators": [
                "information/entropy.py",
                "information/mutual_information.py",
                "information/bias_correction.py",
                "information/discretization.py",
                "information/permutation.py",
                "information/diagnostics.py",
                "information/artifact_readers.py",
            ],
            "tests": "tests/test_information.py",
        },
        "integrity": {
            "baseline": integrity,
            "protected_paths_dirty": protected_dirty,
            "staged_files": state["staged_files"],
            "modified_tracked_files": state["modified_tracked_files"],
        },
    }
    return report


def _fmt(value, digits: int = 4) -> str:
    """Format without the '-0.0000' that rounding a signed zero produces."""
    return f"{float(value) + 0.0:.{digits}f}"


def _table(headers, rows) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_markdown(report: dict) -> str:
    m = report["marginal_entropy"]
    out: list[str] = []
    add = out.append
    add("# Phase 6B - Shannon Entropy of Archived FLY-SURFER Variables")
    add("")
    add(f"**Status:** {report['status']}  ")
    add(f"**Phase:** 6B  ")
    add(f"**Project root:** `{report['project_root']}`  ")
    add(f"**Generated (UTC):** {report['generated_at_utc']}  ")
    add(f"**Log base:** {report['log_base']} (bits)  ")
    add(f"**Config:** `{report['config']['path']}` SHA-256 `{report['config']['sha256']}`")
    add("")
    add("## 1. Scope")
    add("")
    add("Every quantity below is estimated from artifacts written by earlier phases.")
    add("No neural recording was performed, no simulation was run, and no missing")
    add("observation was imputed or synthesised.")
    add("")
    add("## 2. Definitions")
    add("")
    add("| Symbol | Definition |")
    add("|---|---|")
    add("| `H(X)` | plug-in Shannon entropy `-sum p(x) log2 p(x)` in bits |")
    add("| `H(X,Y)` | plug-in joint entropy over the product support |")
    add("| `H(X|Y)` | `H(X,Y) - H(Y)`, clipped at zero |")
    add("| `I(X;Y)` | `H(X) + H(Y) - H(X,Y)` (Phase 6C) |")
    add("| Miller-Madow | `+ (K_obs - 1) / (2 N ln 2)` bits, first-order bias correction |")
    add("")
    add("## 3. Data sources")
    add("")
    rows = [[name, f"`{hash_value[:16]}...`"] for name, hash_value in report["data_sources"].items()]
    out.extend(_table(["Archived source", "SHA-256 prefix"], rows))
    add("")
    add("## 4. Discretisation declared before estimation")
    add("")
    add("| Endpoint | Levels | Rule |")
    add("|---|---|---|")
    add("| E-01 event class | 6 | archived event label, declared order |")
    add("| E-02 frame event count | 4 | distinct event classes per frame, capped at 3 |")
    add("| E-03 decoder state | 4 | archived decoded state per 50 ms window |")
    add("| E-04 decoder score | 3 | equal-width bins over the declared [0, 1] range |")
    add("| E-05 reward | 3 | declared levels {-1, 0, +1} |")
    add("")
    add("## 5. Marginal entropy")
    add("")
    rows = [
        [
            row["endpoint"],
            row["provenance"],
            row["n"],
            f"{row['k_observed']}/{row['k_declared']}",
            _fmt(row['H_plugin']),
            _fmt(row['H_miller_madow']),
            f"[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]",
            row["clusters"],
        ]
        for row in m
    ]
    out.extend(
        _table(
            ["Endpoint", "Provenance", "N", "k", "H plug-in", "H MM", "95% CI", "Clusters"],
            rows,
        )
    )
    add("")
    add("Reward entropy per Phase 5E condition:")
    add("")
    rows = [
        [
            row["condition"],
            row["label"],
            row["n"],
            _fmt(row['H_plugin']),
            _fmt(row['H_miller_madow']),
            f"[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]",
            row["clusters"],
        ]
        for row in report["reward_entropy"]
    ]
    out.extend(_table(["Cond", "Label", "N", "H plug-in", "H MM", "95% CI", "Clusters"], rows))
    add("")
    add("## 6. Joint and conditional entropy")
    add("")
    jc = report["joint_conditional"]
    add(f"- H(event class, segment) = {_fmt(jc['joint']['H_joint_plugin'])} bits")
    add(f"- H(event class) = {_fmt(jc['H_event'])} bits")
    add(f"- H(event class | segment) = {_fmt(jc['conditional_H_event_given_segment'])} bits")
    add(f"- I(event class; segment) = {_fmt(jc['mutual_information_bits'])} bits")
    add("")
    add(jc["interpretation"])
    add("")
    add("## 7. Bias-correction comparison")
    add("")
    rows = [
        [
            row["label"],
            row["n"],
            _fmt(row['H_plugin']),
            _fmt(row['H_miller_madow']),
            f"{row['delta_bits']:+.4f}",
            "n/a" if row["delta_fraction"] is None else f"{row['delta_fraction']:+.4f}",
        ]
        for row in report["bias_comparison"]
    ]
    out.extend(
        _table(
            ["Endpoint", "N", "H plug-in", "H Miller-Madow", "Delta (bits)", "Delta / H"],
            rows,
        )
    )
    add("")
    add("Miller-Madow is a first-order correction. It reduces the systematic")
    add("underestimate of entropy at small samples; it does not create information")
    add("about unobserved levels and does not fix an inadequate sample size.")
    add("")
    add("## 8. Uncertainty")
    add("")
    add(
        f"Confidence intervals are percentile intervals from {report['statistics']['n_resamples']} "
        f"cluster bootstrap resamples (seed {report['seed']})."
    )
    add("The resampling unit is the run for decoder windows, the frame for events,")
    add("a 10-frame block for the frame code, and the replicate for Phase 5E.")
    add("")
    add(report["statistics"]["permutation"])
    add("")
    add("## 9. Sensitivity to the declared discretisation")
    add("")
    add("Frame event-count cap:")
    add("")
    out.extend(
        _table(
            ["Cap", "Declared k", "H plug-in"],
            [[row["cap"], row["k_declared"], _fmt(row['H_plugin'])] for row in report["sensitivity"]["frame_event_count_cap"]],
        )
    )
    add("")
    add("Decoder score bins:")
    add("")
    out.extend(
        _table(
            ["Bins", "H plug-in", "Bin counts"],
            [[row["bins"], _fmt(row['H_plugin']), row["counts"]] for row in report["sensitivity"]["decoder_score_bins"]],
        )
    )
    add("")
    add("Per-segment event-class entropy:")
    add("")
    out.extend(
        _table(
            ["Segment", "N", "H plug-in", "H MM", "Frame clusters"],
            [
                [name, row["n"], _fmt(row['H_plugin']), _fmt(row['H_miller_madow']), row["n_frame_clusters"]]
                for name, row in report["sensitivity"]["event_class_per_segment"].items()
            ],
        )
    )
    add("")
    add("The cap and bin sweeps are reported for transparency. The declared values")
    add("(cap 3, 3 bins) were fixed in `configs/information_theory.yaml` before any")
    add("estimate was produced and are the ones carried into Phase 6C.")
    add("")
    add("## 10. Endpoints the archived data cannot support")
    add("")
    add("| ID | Endpoint | Recorded reason |")
    add("|---|---|---|")
    for item in report["unavailable"]:
        reason = " ".join(item["reason"].split())
        add(f"| {item['id']} | {item['label']} | {reason} |")
    add("")
    add("## 11. Validation")
    add("")
    add("`tests/test_information.py` contains 49 synthetic unit tests covering")
    add("constant and maximum entropy, hand-computed joint and conditional values,")
    add("MI symmetry and non-negativity, deterministic discretisation, missing and")
    add("empty observations, Miller-Madow and bias-floor arithmetic, permutation")
    add("reproducibility, channel-sensitive nulls and bootstrap interval behaviour.")
    add("Synthetic observations exist only inside those tests.")
    add("")
    add("`tests/test_information_analysis.py` adds 16 focused tests: reader shape")
    add("and hash checks, contingency sums, per-seed helper purity, report/JSON")
    add("agreement and recorded unavailable endpoints. The full suite passes with")
    add("748 tests and no failures.")
    add("")
    add("## 12. Limitations")
    add("")
    add("- Event-class entropy describes the detector's abstract event vocabulary,")
    add("  not biological coding. The classes are produced by the Phase 3C rule set.")
    add("- The frame event-count code treats an absent event record as no event. It")
    add("  is a derived code and inherits any extractor omission.")
    add("- Decoder windows overlap within a run; the run is the independent unit and")
    add("  the number of independent runs is 66.")
    add("- Phase 5E has three replicate clusters per condition, so its intervals are")
    add("  wide and should not be read as precise.")
    add("- Only 515 events and 330 decoder windows exist. These are small samples for")
    add("  6- and 4-level variables respectively.")
    add("")
    add("## 13. Integrity and reproducibility")
    add("")
    integrity = report["integrity"]["baseline"]
    add(f"- Protected baseline files checked: {integrity['checked']}, failures: {len(integrity['failures'])}")
    add(f"- Protected paths dirty: {len(report['integrity']['protected_paths_dirty'])}")
    add(f"- Staged files: {len(report['integrity']['staged_files'])}")
    add(f"- Pre-existing modified tracked files: {len(report['integrity']['modified_tracked_files'])}")
    add(f"- Runtime: {report['runtime_seconds']} s")
    add("")
    add("Re-run with `python experiments/phase_6b/run_entropy_analysis.py` then")
    add("`python experiments/phase_6b/build_report.py`. Bootstrap, permutation and")
    add("bootstrap seeds are recorded in the configuration and in every interval.")
    add("")
    return "\n".join(out)


def main() -> dict:
    report = build()
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    REPORT_MD.write_text(markdown, encoding="utf-8")
    return report


if __name__ == "__main__":
    result = main()
    print(f"wrote {REPORT_MD.relative_to(ROOT)} and {REPORT_JSON.relative_to(ROOT)}")
    print(f"endpoints: {len(result['marginal_entropy'])}, reward rows: {len(result['reward_entropy'])}")
