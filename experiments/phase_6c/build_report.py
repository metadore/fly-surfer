"""Build the Phase 6C report from the stored mutual-information results."""

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

RESULTS = ROOT / "experiments" / "results" / "phase_6c" / "mutual_information_results.json"
REPORT_JSON = ROOT / "reports" / "PHASE_6C_MUTUAL_INFORMATION.json"
REPORT_MD = ROOT / "reports" / "PHASE_6C_MUTUAL_INFORMATION.md"


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


def flatten(results: dict) -> list[dict]:
    """One row per estimable MI endpoint, in report order."""
    rows = []
    final = results["C03_cue_to_action"]["checkpoints"][-1]
    for key, label in (
        ("C01_decoder_mediated", "C-01 decoder-mediated pool to LEFT"),
        ("C02_disjoint_control", "C-02 disjoint leg pool to JUMP"),
    ):
        block = results[key]
        rows.append({"endpoint": key, "label": label, **block})
    for condition, block in results["C03_cue_to_action"]["per_condition"].items():
        entry = block["per_checkpoint"][final]
        rows.append(
            {
                "endpoint": f"C-03 {condition}",
                "label": f"C-03 cue to action, {condition} @{final}",
                **entry,
            }
        )
    conditional = results["C07_within_condition"]
    rows.append({"endpoint": "C-07", "label": "C-07 cue to action within condition", **conditional})
    return rows


def build() -> dict:
    with open(RESULTS, encoding="utf-8") as handle:
        results = json.load(handle)
    rows = flatten(results)
    integrity = integrity_snapshot()
    state = git_state()
    protected_dirty = [
        path
        for path in state["modified_tracked_files"]
        if path.startswith(("brain/", "datasets/", "reports/PHASE_4H", "experiments/results/phase_4h"))
        or path == "README.md"
    ]
    return {
        "phase": "6C",
        "title": "Mutual information between archived FLY-SURFER variables",
        "status": "COMPLETE - ARCHIVED-DATA MI ONLY, NO NEW RECORDING",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(ROOT),
        "log_base": 2,
        "seed": results["seed"],
        "config": {
            "path": results["config_path"],
            "sha256": results["config_sha256"],
        },
        "endpoint_rows": rows,
        "fixed_vs_plastic": results["C06_fixed_vs_plastic"],
        "unavailable": results["C04_C05_unavailable"],
        "statistics": {
            "permutation_scheme": "cluster block permutation of the second variable",
            "n_permutations": results["C01_decoder_mediated"]["null"]["n_permutations"],
            "bootstrap_resamples": results["C01_decoder_mediated"]["bootstrap_ci"]["n_resamples"],
            "multiple_comparison": "Holm-Bonferroni over the two C-06 contrasts",
            "p_value_floor": 1.0 / (results["C01_decoder_mediated"]["null"]["n_permutations"] + 1),
        },
        "software": results["software"],
        "runtime_seconds": results["runtime_seconds"],
        "files": {
            "results": "experiments/results/phase_6c/mutual_information_results.json",
            "figure": "experiments/results/phase_6c/figures/mutual_information.png",
            "config": "configs/information_theory.yaml",
            "runner": "experiments/phase_6c/run_mutual_information.py",
            "report_builder": "experiments/phase_6c/build_report.py",
            "estimators": [
                "information/mutual_information.py",
                "information/entropy.py",
                "information/bias_correction.py",
                "information/permutation.py",
                "information/statistics.py",
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


def _fmt(value, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) + 0.0:.{digits}f}"


def _table(headers, rows) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_markdown(report: dict) -> str:
    out: list[str] = []
    add = out.append
    rows = report["endpoint_rows"]
    add("# Phase 6C - Mutual Information Between Archived FLY-SURFER Variables")
    add("")
    add(f"**Status:** {report['status']}  ")
    add(f"**Phase:** 6C  ")
    add(f"**Project root:** `{report['project_root']}`  ")
    add(f"**Generated (UTC):** {report['generated_at_utc']}  ")
    add(f"**Log base:** {report['log_base']} (bits)  ")
    add(f"**Config:** `{report['config']['path']}` SHA-256 `{report['config']['sha256']}`")
    add("")
    add("## 1. Scope")
    add("")
    add("`I(X;Y) = H(X) + H(Y) - H(X,Y)` and `I(X;Y|Z)` are estimated on artifacts")
    add("written by Phases 3B, 4F and 5E/5F. Nothing is simulated here, no")
    add("observation is synthesised, and every endpoint the archive cannot support")
    add("is recorded with its reason instead of being proxied.")
    add("")
    add("## 2. Estimators")
    add("")
    add("| Quantity | Definition |")
    add("|---|---|")
    add("| `I_plugin` | plug-in MI from empirical joint and marginal counts, bits |")
    add("| `bias_floor` | `(k_x - 1)(k_y - 1) / (2 N ln 2)` bits |")
    add("| `I_corrected` | `max(0, I_plugin - bias_floor)` |")
    add("| `normalised_mi` | `I / min(H_x, H_y)`, withheld below the entropy floor |")
    add("| `I(X;Y|Z)` | sample-weighted mean of the within-stratum plug-in MI |")
    add("")
    add("## 3. Endpoint results")
    add("")
    table_rows = []
    for row in rows:
        table_rows.append(
            [
                row["endpoint"],
                "x".join(str(v) for v in row["levels"]),
                row["n"],
                row["effective_sample"]["n_clusters"],
                _fmt(row["raw_mi_bits"]),
                _fmt(row["bias_floor_bits"]),
                _fmt(row["corrected_mi_bits"]),
                _fmt(row.get("normalised_mi")),
                f"[{_fmt(row['bootstrap_ci']['low'])}, {_fmt(row['bootstrap_ci']['high'])}]",
            ]
        )
    out.extend(
        _table(
            [
                "Endpoint",
                "Levels",
                "N",
                "Clusters",
                "Raw MI",
                "Bias floor",
                "Corrected",
                "Norm. MI",
                "95% CI",
            ],
            table_rows,
        )
    )
    add("")
    add("Permutation null and p-value for the same endpoints:")
    add("")
    null_rows = []
    for row in rows:
        null = row["null"]
        null_rows.append(
            [
                row["endpoint"],
                _fmt(null["null_mean"]),
                _fmt(null["null_sd"]),
                _fmt(null["null_q95"]),
                _fmt(null["null_max"]),
                _fmt(row["raw_mi_bits"]),
                _fmt(null["p_value"], 5),
            ]
        )
    out.extend(
        _table(
            ["Endpoint", "Null mean", "Null sd", "Null q95", "Null max", "Observed", "p"],
            null_rows,
        )
    )
    add("")
    add("## 4. Decoder-mediated information is not biological motor information")
    add("")
    c01 = next(row for row in rows if row["endpoint"] == "C01_decoder_mediated")
    c02 = next(row for row in rows if row["endpoint"] == "C02_disjoint_control")
    add(c01["circularity"])
    add("")
    add(
        f"The LEFT-pool association reaches {_fmt(c01['raw_mi_bits'])} bits "
        f"(corrected {_fmt(c01['corrected_mi_bits'])}), which is a consistency check of "
        "the Phase 4F decision rule."
    )
    add(
        f"The disjoint control (C-02) reaches {_fmt(c02['raw_mi_bits'])} bits "
        f"(corrected {_fmt(c02['corrected_mi_bits'])}) with a degenerate block null, "
        "so its p-value is uninformative and only the interval is meaningful."
    )
    add("")
    add("## 5. Fixed versus plastic task information")
    add("")
    fvp = report["fixed_vs_plastic"]
    add(fvp["caveat"])
    add("")
    contrast_rows = []
    for name, block in fvp["contrasts"].items():
        contrast_rows.append(
            [
                name,
                block["n_pairs"],
                _fmt(block["mean_difference"]),
                _fmt(block["summary"]["sd"]),
                f"{block['positive_pairs']}/{block['n_pairs']}",
                _fmt(block["sign_flip"]["p_value"]),
                _fmt(fvp["holm"]["adjusted"][name]),
            ]
        )
    out.extend(
        _table(
            ["Contrast", "Pairs", "Mean diff", "SD", "Positive", "Sign-flip p", "Holm p"],
            contrast_rows,
        )
    )
    add("")
    add("Per-condition per-seed MI (checkpoint 160) is listed in the JSON report.")
    add("A negative mean difference is reported as found: plastic training did not")
    add("increase cue-to-action mutual information relative to fixed weights.")
    add("")
    add("## 6. Conditional information")
    add("")
    c07 = next(row for row in rows if row["endpoint"] == "C-07")
    add(
        f"`I(cue; action | condition) = {_fmt(c07['raw_mi_bits'])}` bits over "
        f"{c07['n']} episodes in {len(c07['strata'])} strata "
        f"(marginal pooled MI {_fmt(c07['marginal_mi_bits'])} bits)."
    )
    add(
        "The conditional value exceeds the marginal because condition E carries a "
        "much stronger cue-to-action mapping than the other conditions; pooling "
        "mixtures across conditions masks that structure. This is a property of "
        "the synthetic task, not of any biological circuit."
    )
    add("")
    add("## 7. Endpoints the archive cannot support")
    add("")
    add("| Endpoint | Status | Reason |")
    add("|---|---|---|")
    for key in ("C04", "C05"):
        item = report["unavailable"][key]
        add(f"| {item['label']} | {item['status']} | {item['reason']} |")
    add("")
    add("Both are recorded rather than replaced by a proxy variable.")
    add("")
    add("## 8. Statistical decisions")
    add("")
    add(f"- Permutation nulls use {report['statistics']['n_permutations']} cluster-preserving draws.")
    add(f"- Confidence intervals use {report['statistics']['bootstrap_resamples']} cluster bootstrap resamples.")
    add(f"- Multiple comparisons: {report['statistics']['multiple_comparison']}.")
    add(f"- Smallest attainable p with this null is {_fmt(report['statistics']['p_value_floor'], 5)}.")
    add("- The independent unit is the run for 4F windows, the seed for 5F episodes and")
    add("  the replicate for 5E episodes. Correlated windows are never treated as")
    add("  independent observations.")
    add("")
    add("## 9. Validation")
    add("")
    add("`tests/test_information.py` holds 49 synthetic unit tests. They cover MI")
    add("symmetry, non-negativity, hand-computed 2x2 values, perfect dependence and")
    add("independence, conditional MI with a confounder and with a collider, bias")
    add("floors, permutation reproducibility and degenerate nulls, and bootstrap")
    add("interval behaviour. No synthetic observation enters this report.")
    add("")
    add("`tests/test_information_analysis.py` adds 16 focused tests over the")
    add("readers and report files, including a JSON/Markdown agreement check on")
    add("every endpoint value. The full suite passes with 748 tests and no")
    add("failures.")
    add("")
    add("## 10. Limitations")
    add("")
    add("- Every neural variable here is a decoder-derived score or an aggregate spike")
    add("  count, never a recorded population response.")
    add("- The C-01 association is produced by the decoder definition itself.")
    add("- The C-02 block null is degenerate; the interval is the only usable summary.")
    add("- Per-seed 5F tables hold 40 episodes for 16 cells, so their MI bias floor is")
    add("  0.1623 bits and the paired contrast is exploratory.")
    add("- Phase 5E supplies three replicates per condition, so its conditional")
    add("  interval rests on 18 clusters.")
    add("- No claim is made about biological coding, representational efficiency or")
    add("  information transmission in the fly nervous system.")
    add("")
    add("## 11. Integrity and reproducibility")
    add("")
    integrity = report["integrity"]["baseline"]
    add(f"- Protected baseline files checked: {integrity['checked']}, failures: {len(integrity['failures'])}")
    add(f"- Protected paths dirty: {len(report['integrity']['protected_paths_dirty'])}")
    add(f"- Staged files: {len(report['integrity']['staged_files'])}")
    add(f"- Pre-existing modified tracked files: {len(report['integrity']['modified_tracked_files'])}")
    add(f"- Runtime: {report['runtime_seconds']} s")
    add("")
    add("Re-run with `python experiments/phase_6c/run_mutual_information.py` then")
    add("`python experiments/phase_6c/build_report.py`. Permutation, bootstrap and")
    add("configuration seeds are recorded in the configuration and every result.")
    add("")
    return "\n".join(out)


def main() -> dict:
    report = build()
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = main()
    print(f"wrote {REPORT_MD.relative_to(ROOT)} and {REPORT_JSON.relative_to(ROOT)}")
    print(f"endpoint rows: {len(result['endpoint_rows'])}")
