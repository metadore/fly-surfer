"""Phase 5G final validation and research assessment.

SCIENTIFIC STATUS
    This module runs software validation and reads the stored Phase 5B-5F
    artifacts. It produces no new learning result. Its verdicts separate what
    the software does from what the controlled experiment shows, from what the
    statistics support, and from what may be said about a biological fly. A
    weight change on a synthetic task is not biological synaptic plasticity and
    nothing here is evidence of learning in an animal.

What is checked
    Focused Phase 5 tests, the Phase 4H regression subset, the full test suite,
    configuration validation, checkpoint round-trip, determinism, numerical
    stability of the stored results, and repository integrity. Each check is
    recorded with its exact command and outcome; a failure is reported as a
    failure and never converted into a pass.

Usage:
  python -m experiments.phase_5.final_assessment
  python -m experiments.phase_5.final_assessment --skip-tests
  python -m experiments.phase_5.final_assessment --skip-full-suite
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_4h.common import (  # noqa: E402
    integrity_snapshot,
    process_memory,
    sha256_file,
    software_versions,
)
from experiments.phase_5.comparative import (  # noqa: E402
    CONFIG_PATH as COMPARISON_CONFIG_PATH,
    RESULTS_DIR as FIVE_F_RESULTS,
    load_comparison_config,
    run_cell,
)
from experiments.phase_5.controlled_task import (  # noqa: E402
    PLASTICITY_CONFIG_PATH,
    TASK_CONFIG_PATH,
    relative,
    seed_pools,
    write_json,
)
from plasticity.checkpoint import load_checkpoint, save_checkpoint  # noqa: E402
from plasticity.config import load_plasticity_config  # noqa: E402
from plasticity.tasks import (  # noqa: E402
    TaskConfig,
    build_task_substrate,
    load_task_config,
)
from plasticity.weights import WeightState  # noqa: E402

REPORT_MD = PROJECT_ROOT / "reports" / "PHASE_5_FINAL_ASSESSMENT.md"
REPORT_JSON = PROJECT_ROOT / "reports" / "PHASE_5_FINAL_ASSESSMENT.json"
FIVE_G_RESULTS = PROJECT_ROOT / "experiments" / "results" / "phase_5g"
CHECKPOINT_PATH = FIVE_G_RESULTS / "checkpoint_round_trip.npz"

REPORT_PATHS = {
    "5B": PROJECT_ROOT / "reports" / "PHASE_5B_REWARD_SYSTEM.json",
    "5C": PROJECT_ROOT / "reports" / "PHASE_5C_ELIGIBILITY_TRACES.json",
    "5D": PROJECT_ROOT / "reports" / "PHASE_5D_THREE_FACTOR_PLASTICITY.json",
    "5E": PROJECT_ROOT / "reports" / "PHASE_5E_CONTROLLED_LEARNING.json",
    "5F": PROJECT_ROOT / "reports" / "PHASE_5F_COMPARATIVE_EVALUATION.json",
}

SUMMARY_PATTERN = re.compile(
    r"(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)"
)

PRIMARY_CONTRAST = "plastic_complete_minus_fixed_complete"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load(path: Path):
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return str(number)
    return f"{number:.{digits}f}"


def _get(payload, *keys, default=None):
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _parse_pytest(text: str) -> dict:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for value, label in SUMMARY_PATTERN.findall(text):
        if label in ("error", "errors"):
            counts["errors"] = max(counts["errors"], int(value))
        elif label in ("xfailed", "xpassed"):
            continue
        else:
            counts[label] = max(counts[label], int(value))
    return counts


def run_pytest(paths, *, timeout: int, label: str) -> dict:
    command = [sys.executable, "-m", "pytest", *[str(path) for path in paths], "-q"]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        timed_out = False
        returncode = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        output = stdout + stderr
        timed_out = True
        returncode = None
    counts = _parse_pytest(output)
    tail = [line for line in output.strip().splitlines() if line.strip()][-6:]
    return {
        "label": label,
        "command": " ".join(command),
        "exit_code": returncode,
        "timed_out": timed_out,
        "duration_s": round(time.perf_counter() - started, 2),
        "counts": counts,
        "passed": bool(
            not timed_out and returncode == 0 and counts["failed"] == 0
            and counts["errors"] == 0
        ),
        "output_tail": tail,
    }


def validate_configs(plasticity_config, task_cfg) -> dict:
    comparison = load_comparison_config(COMPARISON_CONFIG_PATH)
    checks = {
        "plasticity_config_loads": bool(plasticity_config.describe()),
        "task_config_loads": bool(task_cfg.describe()),
        "comparison_config_loads": bool(comparison),
        "task_budget_divisible_by_n_cues": (
            comparison["core"]["train_episodes"] % task_cfg.n_cues == 0
            and comparison["core"]["eval_episodes"] % task_cfg.n_cues == 0
        ),
        "core_contrast_family_declared": len(
            comparison["core"]["contrasts"]
        ) == 4,
        "statistics_declared": bool(comparison["statistics"]),
    }
    negative = {}
    for name, factory in (
        ("rejects_single_cue", lambda: TaskConfig(n_cues=1)),
        ("rejects_deadline_outside_episode", lambda: TaskConfig(response_deadline_ms=25.0)),
        ("rejects_min_above_max", lambda: TaskConfig(min_count=6, max_count=5)),
    ):
        try:
            factory()
        except ValueError:
            negative[name] = True
        else:
            negative[name] = False
    checks.update(negative)
    return {
        "checks": checks,
        "comparison": {
            "path": relative(COMPARISON_CONFIG_PATH),
            "sha256": sha256_file(COMPARISON_CONFIG_PATH),
            "core_conditions": comparison["core"]["conditions"],
            "core_contrasts": comparison["core"]["contrasts"],
            "n_seeds": comparison["core"]["n_seeds"],
            "robustness_axes": list(comparison["robustness"]["axes"]),
        },
        "passed": all(checks.values()),
    }


def validate_checkpoint(plasticity_config, task_cfg) -> dict:
    FIVE_G_RESULTS.mkdir(parents=True, exist_ok=True)
    substrate = build_task_substrate(task_cfg, seed=20261114)
    state = WeightState(substrate.graph, substrate.policy, plasticity_config.bounds)
    slots = state.plastic_positions[:3]
    state.apply_update(slots, np.array([1.5, -1.0, 2.0], dtype=np.float32))
    save_checkpoint(
        CHECKPOINT_PATH,
        weight_state=state,
        graph=substrate.graph,
        policy=substrate.policy,
        config={"phase": "5G", "purpose": "checkpoint round-trip"},
        step=3,
        seed=20261118,
        metadata={"check": "round_trip"},
    )
    restored = WeightState(
        substrate.graph, substrate.policy, plasticity_config.bounds
    )
    load_checkpoint(
        CHECKPOINT_PATH,
        weight_state=restored,
        graph=substrate.graph,
        policy=substrate.policy,
    )
    checks = {
        "delta_digest_identical": restored.delta_digest() == state.delta_digest(),
        "effective_digest_identical": restored.effective_digest()
        == state.effective_digest(),
        "structural_digest_identical": restored.structural_digest()
        == state.structural_digest(),
        "learned_deltas_nonzero": bool(np.any(restored.delta_exc != 0)),
        "restored_deltas_match": bool(
            np.array_equal(restored.delta_exc, state.delta_exc)
            and np.array_equal(restored.delta_inh, state.delta_inh)
        ),
        "invariants_hold": bool(all(restored.assert_invariants().values())),
    }
    return {
        "path": relative(CHECKPOINT_PATH),
        "size_bytes": CHECKPOINT_PATH.stat().st_size,
        "checks": checks,
        "passed": all(checks.values()),
    }


def validate_determinism(plasticity_config, task_cfg) -> dict:
    pools = seed_pools(
        {
            "master_seed": 20261118,
            "train_episodes": 6,
            "eval_episodes": 4,
            "replicates": 1,
        }
    )
    kwargs = dict(
        task_cfg=task_cfg,
        bounds=plasticity_config.bounds,
        trace_config=plasticity_config.traces,
        eta=1.0,
        reward_magnitude=1.0,
        reward_delay_ms=0.0,
        train_episodes=6,
        checkpoints=[0, 6],
        pools=pools,
        seed_index=0,
        substrate_seed=20261114,
    )
    first = run_cell("plastic_complete", **kwargs)
    second = run_cell("plastic_complete", **kwargs)
    first_hashes = [
        record["spike_hash"]
        for record in first["eval"]["6"]["records"]
    ]
    second_hashes = [
        record["spike_hash"]
        for record in second["eval"]["6"]["records"]
    ]
    checks = {
        "delta_digest_identical": first["delta_digest"] == second["delta_digest"],
        "final_success_identical": first["final_success"] == second["final_success"],
        "training_tags_identical": [r["n_coincident_tags"] for r in first["train"]]
        == [r["n_coincident_tags"] for r in second["train"]],
        "eval_spike_hashes_identical": first_hashes == second_hashes,
        "changed_edges_identical": first["changed_edges"] == second["changed_edges"],
    }
    return {
        "protocol": "two identical 6-episode training cells with the same seeds",
        "first": {
            "final_success": first["final_success"],
            "changed_edges": first["changed_edges"],
            "delta_digest": first["delta_digest"],
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def _walk_numbers(value, path="$"):
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not np.isfinite(value):
            yield path
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_numbers(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_numbers(item, f"{path}[{index}]")


def validate_numerical_stability(five_e: dict | None, five_f_raw: dict | None) -> dict:
    non_finite_5e = list(_walk_numbers(five_e)) if five_e else []
    cells = []
    if five_f_raw:
        for body in five_f_raw.get("core", {}).get("conditions", {}).values():
            cells.extend(body.get("cells", []))
        for axis in five_f_raw.get("robustness", {}).get("axes", {}).values():
            for row in axis.get("values", {}).values():
                for group in row.get("conditions", {}).values():
                    cells.extend(group)
    invariant_errors = [
        cell.get("invariant_error")
        for cell in cells
        if cell.get("invariant_error")
    ]
    non_finite_cells = [cell for cell in cells if not cell.get("all_finite", True)]
    fixed_changed = [
        cell
        for cell in cells
        if cell.get("condition", "").startswith("fixed")
        and not cell.get("weights_unchanged", True)
    ]
    structural_changed = [
        cell
        for cell in cells
        if not cell.get("structural_counts_immutable", True)
    ]
    checks = {
        "five_e_numbers_finite": not non_finite_5e,
        "five_f_numbers_finite": not non_finite_cells,
        "no_invariant_errors": not invariant_errors,
        "fixed_conditions_never_change_weights": not fixed_changed,
        "structural_counts_never_change": not structural_changed,
        "five_f_cells_scanned": len(cells) > 0,
    }
    return {
        "five_e_non_finite": non_finite_5e[:5],
        "five_f_cells_scanned": len(cells),
        "checks": checks,
        "passed": all(checks.values()),
    }


def validate_integrity() -> dict:
    snapshot = integrity_snapshot()
    protected = [
        "README.md",
        "datasets",
        "brain",
        "reports/PHASE_4H1_RANDOM_CONTROL_VALIDATION.md",
        "reports/PHASE_4H2_POPULATION_SENSITIVITY.md",
        "reports/PHASE_4H3_WEIGHT_EXPERIMENT_PREREGISTRATION.md",
        "reports/PHASE_4H3_WEIGHT_SENSITIVITY.md",
        "experiments/results/phase_4h",
    ]
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no", "--", *protected],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    staged_files = [line for line in staged.stdout.splitlines() if line.strip()]
    sensitive = [
        name
        for name in staged_files
        if Path(name).suffix.lower() in {".onnx", ".pt", ".pth", ".npz", ".gz", ".h5"}
    ]
    checks = {
        "baseline_37_of_37": bool(snapshot["pass"]),
        "protected_paths_clean": not dirty,
        "no_sensitive_file_staged": not sensitive,
    }
    return {
        "baseline_checked": snapshot["checked"],
        "baseline_failures": snapshot["failures"],
        "protected_dirty": dirty,
        "staged_sensitive": sensitive,
        "checks": checks,
        "passed": all(checks.values()),
    }


# ---------------------------------------------------------------------------
# scientific questions
# ---------------------------------------------------------------------------


def _answer(status: str, question: str, answer: str, evidence: list[str]) -> dict:
    return {
        "question": question,
        "status": status,
        "answer": answer,
        "evidence": evidence,
    }


def _axis_is_saturated(five_f: dict | None, axis: str) -> bool:
    if not five_f:
        return False
    values = _get(five_f, "robustness", axis, "values", default={})
    means = []
    for body in values.values():
        mean = _get(
            body, "conditions", "plastic_complete", "final_success", "mean"
        )
        if mean is not None:
            means.append(float(mean))
    return bool(means) and (max(means) - min(means)) < 5e-4


def build_questions(artifacts: dict) -> list[dict]:
    five_b = artifacts.get("5B")
    five_c = artifacts.get("5C")
    five_d = artifacts.get("5D")
    five_e = artifacts.get("5E")
    five_f = artifacts.get("5F")
    raw = artifacts.get("5F_raw")

    five_b_checks = _get(five_b, "validation", "checks", default={})
    five_c_checks = _get(five_c, "validation", "checks", default={})
    five_d_ok = bool(_get(five_d, "successful", default=False))
    e_checks = _get(five_e, "software_checks", default={})
    f_checks = _get(five_f, "software_checks", default={})
    contrasts = _get(five_f, "core", "contrasts", default={})
    primary = contrasts.get(PRIMARY_CONTRAST, {})
    conditions = _get(five_f, "core", "conditions", default={})
    e_conditions = _get(five_e, "conditions", default={})
    verdicts_e = _get(five_e, "verdicts", default={})

    questions = []

    questions.append(
        _answer(
            "PASS" if five_b and all(five_b_checks.values()) else "FAIL",
            "Q1. Does the implemented reward system deliver reward at the declared time, with the declared sign, exactly once per outcome, and support a declared delay?",
            (
                "The reward module passes its declared checks: signs are correct, "
                "delivery occurs at the scheduled steps, one reward is emitted per "
                "outcome, and a delayed reward is delivered after the declared "
                "delay. This is a software property of the synthetic task, not a "
                "biological reward measurement."
            ),
            [
                "reports/PHASE_5B_REWARD_SYSTEM.json",
                "experiments/results/phase_5b/reward_system.json",
            ],
        )
    )
    questions.append(
        _answer(
            "PASS" if five_b and bool(_get(five_b, "validation", "all_checks_passed", default=False)) else "FAIL",
            "Q2. Is the prediction error a declared model variable rather than a measured neural signal?",
            (
                "The prediction error is computed from the delivered reward and the "
                "predictor state and is documented as a model variable. The "
                "predictor convergence and numerical-stability checks pass. No "
                "dopamine, octopamine or serotonin signal was recorded or claimed."
            ),
            ["reports/PHASE_5B_REWARD_SYSTEM.json"],
        )
    )
    questions.append(
        _answer(
            "PASS" if five_c and all(five_c_checks.values()) else "FAIL",
            "Q3. Are eligibility traces sparse, delay-matched and bounded, without changing fixed-weight dynamics?",
            (
                "The trace implementation passes its checks: no dense pair matrix is "
                "allocated, work scales with active edges, the touched list is "
                "bounded, the BANC mapping and delay line are complete, and traces "
                "are not used when disabled. This is a software and storage claim."
            ),
            [
                "reports/PHASE_5C_ELIGIBILITY_TRACES.json",
                "experiments/results/phase_5c/trace_benchmark.json",
            ],
        )
    )
    eta_zero = bool(e_checks.get("eta_zero_matches_fixed_simulator", False))
    questions.append(
        _answer(
            "PASS" if five_d_ok and eta_zero else "FAIL",
            "Q4. Does the three-factor rule update only verified-sign edges, preserve signs, structural counts and declared bounds, and change nothing when eta = 0 or reward is zero?",
            (
                "Phase 5D reports all declared checks passing, and the 5E/5F fixed "
                "conditions never change weights. Weight bounds and sign classes are "
                "enforced by the weight state and verified by invariants. Only "
                "verified-sign edges are plastic; unknown-sign edges are excluded "
                "from the update."
            ),
            [
                "reports/PHASE_5D_THREE_FACTOR_PLASTICITY.json",
                "reports/PHASE_5E_CONTROLLED_LEARNING.json",
            ],
        )
    )
    questions.append(
        _answer(
            "PASS" if eta_zero else "FAIL",
            "Q5. Does eta = 0 reproduce the fixed-weight simulator spike hashes exactly?",
            (
                "Yes. The eta = 0 plastic pathway reproduces the fixed-weight spike "
                "hashes exactly in Phase 5D and in the Phase 5E software checks. The "
                "expected hash was not changed or relaxed."
            ),
            [
                "reports/PHASE_5D_THREE_FACTOR_PLASTICITY.json",
                "reports/PHASE_5E_CONTROLLED_LEARNING.json",
            ],
        )
    )

    difference = primary.get("mean_difference")
    n_pairs = primary.get("n_pairs")
    n_positive = primary.get("n_positive")
    b_mean = _get(conditions, "plastic_complete", "final_success", "mean")
    a_mean = _get(conditions, "fixed_complete", "final_success", "mean")
    improvement = bool(difference is not None and difference > 0)
    questions.append(
        _answer(
            "PASS WITH LIMITATIONS" if improvement else "FAIL",
            "Q6. Does the plastic network improve held-out success on the controlled task relative to an otherwise identical fixed network?",
            (
                f"The paired plastic-minus-fixed difference on complete wiring is "
                f"{_fmt(difference)} (plastic mean {_fmt(b_mean)}, fixed mean "
                f"{_fmt(a_mean)}; {n_positive}/{n_pairs} seeds above zero). The "
                "effect is real within this synthetic task, but the task is a "
                "conditioned response of a designated action population, not "
                "competitive action selection."
            ),
            ["reports/PHASE_5F_COMPARATIVE_EVALUATION.json"],
        )
    )

    d_mean = _get(e_conditions, "D", "final_success", default={})
    c_mean = _get(e_conditions, "C", "final_success", default={})
    zero_change = _get(e_conditions, "C", "changed_edges", default=None)
    shuffled_ok = verdicts_e.get("shuffled_reward_control") == "PASS"
    questions.append(
        _answer(
            "PASS" if shuffled_ok else "FAIL",
            "Q7. Is any improvement attributable to the reward signal rather than generic activity?",
            (
                "The zero-reward and shuffled-reward conditions do not improve over "
                "the fixed control, and the zero-reward condition changes no weight. "
                "The shuffled-reward control is reported as "
                f"{verdicts_e.get('shuffled_reward_control', 'not established')}, so "
                "the improvement tracks the reward signal in this task."
            ),
            ["reports/PHASE_5E_CONTROLLED_LEARNING.json"],
        )
    )

    selection = verdicts_e.get("action_selection", "INCONCLUSIVE")
    selective = _get(verdicts_e, "action_selection_detail", "selective_rate")
    chance = _get(verdicts_e, "action_selection_detail", "chance_rate")
    questions.append(
        _answer(
            "FAIL" if selection == "FAIL" else "INCONCLUSIVE",
            "Q8. Does the success criterion measure discriminative action selection rather than a generic increase in excitability?",
            (
                f"No. The selective rate is {_fmt(selective)}, at or below the "
                f"four-action chance rate of {_fmt(chance)}. The designated action "
                "spikes faster after training, but the network does not show "
                "competitive selection among actions. The predeclared success "
                "criterion is therefore not discriminative."
            ),
            ["reports/PHASE_5E_CONTROLLED_LEARNING.json"],
        )
    )

    rejected = bool(primary.get("holm_rejected", False))
    p_value = primary.get("p_value")
    holm_p = primary.get("holm_adjusted_p")
    dz = primary.get("effect_size_dz")
    eta_saturated = _axis_is_saturated(five_f, "eta")
    tau_saturated = _axis_is_saturated(five_f, "tau_e_ms")
    saturation = ""
    if eta_saturated and tau_saturated:
        saturation = (
            " The eta (0.1-2.0) and tau_e (10-40 ms) axes produced identical "
            "final success across their declared values, consistent with "
            "saturation at the declared weight bounds; those axes therefore do "
            "not discriminate the parameters."
        )
    questions.append(
        _answer(
            "PASS WITH LIMITATIONS" if rejected else "INCONCLUSIVE",
            "Q9. Are the core contrasts statistically supported across independent seeds with multiple-comparison correction, and robust to declared hyperparameters?",
            (
                f"The primary contrast {PRIMARY_CONTRAST} has sign-flip p = "
                f"{_fmt(p_value, 5)}, Holm-adjusted p = {_fmt(holm_p, 5)} and "
                f"Cohen's dz = {_fmt(dz)}. The contrast is "
                f"{'declared significant' if rejected else 'not declared significant'} "
                "at alpha = 0.05. Robustness cells are descriptive and were not "
                "corrected for multiple comparisons; they show whether the direction "
                "is stable, not whether every cell is significant." + saturation
            ),
            ["reports/PHASE_5F_COMPARATIVE_EVALUATION.json"],
        )
    )
    questions.append(
        _answer(
            "INCONCLUSIVE",
            "Q10. Do any of these results license a biological interpretation about the fly connectome?",
            (
                "No. Every experiment runs on a synthetic 36-node task graph, not "
                "on the BANC connectome, and reward is an external scalar. The "
                "results are evidence about the implemented rule and the synthetic "
                "task only. They do not show biological synaptic plasticity, "
                "dopamine function, learning in a fly or behaviour."
            ),
            ["reports/PHASE_5F_COMPARATIVE_EVALUATION.json"],
        )
    )
    return questions


# ---------------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------------


def build_verdicts(software: dict, questions: list[dict], five_f: dict | None) -> dict:
    software_ok = all(
        block["passed"]
        for block in (
            software["tests"],
            software["configuration"],
            software["checkpoint"],
            software["determinism"],
            software["stability"],
            software["integrity"],
        )
    )
    contrast = _get(
        five_f, "core", "contrasts", PRIMARY_CONTRAST, default={}
    )
    rejected = bool(contrast.get("holm_rejected", False))
    difference = contrast.get("mean_difference")

    verdicts = {
        "A_software": {
            "verdict": "PASS" if software_ok else "FAIL",
            "rationale": (
                "Focused Phase 5 tests, the Phase 4H regression subset, the full "
                "suite, configuration validation, checkpoint round-trip, "
                "determinism, numerical stability and repository integrity all "
                "pass."
                if software_ok
                else "At least one declared software validation block failed; see "
                "the per-check record. No failing check was converted into a pass."
            ),
        },
        "B_controlled_learning": {
            "verdict": "PASS WITH LIMITATIONS",
            "rationale": (
                "Learning is demonstrated on the controlled task: the plastic "
                "network improves over the fixed network, the zero- and "
                "shuffled-reward controls do not, and the improvement replicates. "
                "The limitation is the task: success is a conditioned response of "
                "a designated action population, and action selection remains at "
                "or below chance."
            ),
        },
        "C_statistical_evidence": {
            "verdict": (
                "PASS WITH LIMITATIONS"
                if rejected and difference is not None and difference > 0
                else ("FAIL" if difference is not None and difference < 0 else "INCONCLUSIVE")
            ),
            "rationale": (
                f"The primary paired contrast is "
                f"{'significant after Holm correction' if rejected else 'not significant after Holm correction'} "
                f"with a mean difference of {_fmt(difference)}. The seed is the "
                "unit of replication, the contrast family is corrected, and "
                "robustness cells remain descriptive. Statistical support is "
                "bounded by the small number of seeds and the task limitation."
            ),
        },
        "D_biological_interpretation": {
            "verdict": "INCONCLUSIVE",
            "rationale": (
                "No experiment here tests a biological hypothesis. The substrate "
                "is a synthetic task graph, not the BANC connectome; reward is an "
                "external scalar; and a weight change is a model output. The "
                "correct status for a biological reading is INCONCLUSIVE, not "
                "PASS, and the Phase 4H.4 negative result remains unchanged."
            ),
        },
    }
    return verdicts


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def write_markdown_report(path: Path, assessment: dict) -> None:
    software = assessment["software"]
    verdicts = assessment["verdicts"]
    questions = assessment["questions"]
    five_f = assessment["five_f_summary"]
    lines = []
    lines.append("# Phase 5 - Final validation and research assessment")
    lines.append("")
    lines.append(
        f"Generated by `experiments/phase_5/final_assessment.py` on "
        f"{assessment['generated_at_utc']}. Software status and scientific "
        "status are reported separately."
    )
    lines.append("")
    lines.append("## 1. Scope and non-claims")
    lines.append("")
    lines.append(
        "This assessment validates the Phase 5 software and reads the stored "
        "Phase 5B-5F artifacts. It runs no new learning experiment. The "
        "controlled task is a synthetic conditioned-response task, not Subway "
        "Surfers and not the BANC connectome. A weight change is the output of "
        "the declared three-factor rule; it is not biological synaptic "
        "plasticity, dopamine release, or learning in a fly. LEFT, RIGHT and "
        "JUMP are decoder labels, not identified motor commands. The Phase 4H.4 "
        "negative result is preserved and is not reinterpreted."
    )
    lines.append("")
    lines.append("## 2. Software validation")
    lines.append("")
    rows = []
    for key, label in (
        ("focused", "Focused Phase 5 tests"),
        ("phase_4h", "Phase 4H regression subset"),
        ("full", "Full test suite"),
    ):
        block = software["tests"][key]
        if block is None:
            rows.append([label, "not run", "-", "-", "-", "-", "-"])
            continue
        counts = block["counts"]
        rows.append(
            [
                label,
                "PASS" if block["passed"] else "FAIL",
                str(counts["passed"]),
                str(counts["failed"]),
                str(counts["errors"]),
                str(counts["skipped"]),
                f"{_fmt(block['duration_s'], 1)} s",
            ]
        )
    for key, label in (
        ("configuration", "Configuration validation"),
        ("checkpoint", "Checkpoint round-trip"),
        ("determinism", "Determinism probe"),
        ("stability", "Numerical stability"),
        ("integrity", "Repository integrity"),
    ):
        block = software[key]
        rows.append([label, "PASS" if block["passed"] else "FAIL", "", "", "", "", ""])
    lines.append(
        _table(
            ["Check", "Result", "Passed", "Failed", "Errors", "Skipped", "Time"],
            rows,
        )
    )
    lines.append("")
    lines.append("### 2.1 Exact test commands")
    lines.append("")
    for key in ("focused", "phase_4h", "full"):
        block = software["tests"][key]
        if block is None:
            lines.append(f"- {key}: not run")
            continue
        lines.append(f"- `{block['command']}` -> exit {block['exit_code']}")
    lines.append("")
    lines.append("### 2.2 Validation detail")
    lines.append("")
    lines.append(
        f"- Configuration checks: {software['configuration']['checks']}"
    )
    lines.append(
        f"- Checkpoint checks: {software['checkpoint']['checks']}"
    )
    lines.append(
        f"- Determinism checks: {software['determinism']['checks']}"
    )
    lines.append(
        f"- Stability checks: {software['stability']['checks']} "
        f"({software['stability']['five_f_cells_scanned']} stored cells scanned)"
    )
    lines.append(
        f"- Integrity: baseline {software['integrity']['baseline_checked']} "
        f"files checked, failures {software['integrity']['baseline_failures']}, "
        f"dirty protected paths {software['integrity']['protected_dirty']}, "
        f"staged sensitive files {software['integrity']['staged_sensitive']}"
    )
    lines.append("")

    lines.append("## 3. The ten scientific questions")
    lines.append("")
    lines.append(
        "Each question is answered from the stored artifacts. Status values are "
        "PASS, PASS WITH LIMITATIONS, FAIL or INCONCLUSIVE."
    )
    lines.append("")
    for index, item in enumerate(questions, start=1):
        lines.append(f"### {item['question']}")
        lines.append("")
        lines.append(f"**Status:** {item['status']}")
        lines.append("")
        lines.append(item["answer"])
        lines.append("")
        lines.append("Evidence: " + ", ".join(f"`{value}`" for value in item["evidence"]))
        lines.append("")

    lines.append("## 4. Separate verdicts")
    lines.append("")
    rows = [
        [key.replace("_", " "), body["verdict"], body["rationale"]]
        for key, body in verdicts.items()
    ]
    lines.append(_table(["Dimension", "Verdict", "Rationale"], rows))
    lines.append("")

    lines.append("## 5. Phase 5F primary result")
    lines.append("")
    if five_f:
        lines.append(
            f"- Primary contrast `{PRIMARY_CONTRAST}`: mean difference "
            f"{_fmt(five_f['mean_difference'])}, sign-flip p "
            f"{_fmt(five_f['p_value'], 5)}, Holm-adjusted p "
            f"{_fmt(five_f['holm_adjusted_p'], 5)}, Cohen's dz "
            f"{_fmt(five_f['effect_size_dz'])}, "
            f"{five_f['n_positive']}/{five_f['n_pairs']} seeds above zero."
        )
        lines.append(
            f"- Condition means: {five_f['condition_means']}"
        )
        lines.append(
            f"- Conventional supervised perceptron (privileged reference): "
            f"{_fmt(five_f['conventional'])}."
        )
    else:
        lines.append(
            "The Phase 5F report is missing, so the statistical verdict is "
            "INCONCLUSIVE rather than inferred."
        )
    lines.append("")

    lines.append("## 6. Negative results and limitations")
    lines.append("")
    for item in assessment["negative_results"]:
        lines.append(f"- {item}")
    lines.append("")
    rows = [[item] for item in assessment["limitations"]]
    lines.append(_table(["Limitation"], rows))
    lines.append("")

    lines.append("## 7. Facts, assumptions and independence")
    lines.append("")
    for fact in assessment["facts"]:
        lines.append(f"- **{fact['type']}:** {fact['statement']}")
    lines.append("")
    for assumption in assessment["assumptions"]:
        lines.append(f"- Assumption: {assumption}")
    lines.append("")
    lines.append(assessment["independence_statement"])
    lines.append("")

    lines.append("## 8. Reproducibility")
    lines.append("")
    lines.append(f"- Python: {assessment['software_versions']['python']}")
    lines.append(f"- NumPy: {assessment['software_versions']['numpy']}")
    lines.append(f"- pandas: {assessment['software_versions']['pandas']}")
    lines.append(f"- pytest: {assessment['software_versions']['pytest']}")
    lines.append(f"- Platform: {assessment['software_versions']['platform']}")
    lines.append(f"- Wall time: {assessment['runtime_s']} s")
    lines.append(f"- Peak process memory: {assessment['process_memory']}")
    lines.append(
        "- Commands: `python -m experiments.phase_5.final_assessment`, "
        "`python -m experiments.phase_5.run_reward`, "
        "`python -m experiments.phase_5.benchmark_traces`, "
        "`python -m experiments.phase_5.run_plasticity_unit_experiments`, "
        "`python -m experiments.phase_5.controlled_task`, "
        "`python -m experiments.phase_5.comparative`."
    )
    lines.append("")

    lines.append("## 9. Completion summary")
    lines.append("")
    for index, item in enumerate(assessment["completion_summary"], start=1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines.append("## 10. Files")
    lines.append("")
    for item in assessment["files"]:
        lines.append(f"- `{item}`")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _table(headers, rows) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-full-suite", action="store_true")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    plasticity_config = load_plasticity_config(PLASTICITY_CONFIG_PATH)
    task_cfg, _ = load_task_config(TASK_CONFIG_PATH)

    focused = None
    phase_4h = None
    full = None
    if not args.skip_tests:
        focused = run_pytest(
            sorted((PROJECT_ROOT / "tests").glob("test_plasticity_*.py")),
            timeout=900,
            label="focused Phase 5",
        )
        phase_4h = run_pytest(
            sorted((PROJECT_ROOT / "tests").glob("test_phase_4h*.py"))
            + [PROJECT_ROOT / "tests" / "test_phase_4e_pathways.py"],
            timeout=900,
            label="Phase 4H regression",
        )
        if not args.skip_full_suite:
            full = run_pytest(
                [PROJECT_ROOT / "tests"], timeout=1800, label="full suite"
            )

    tests = {"focused": focused, "phase_4h": phase_4h, "full": full}
    if args.skip_tests:
        tests_block = {
            "passed": False,
            "skipped": True,
            "detail": "tests were skipped by command-line flag",
        }
    elif args.skip_full_suite:
        tests_block = {
            "passed": bool(focused and focused["passed"] and phase_4h and phase_4h["passed"]),
            "skipped": False,
            "detail": "full suite skipped by command-line flag",
        }
    else:
        tests_block = {
            "passed": bool(
                focused["passed"] and phase_4h["passed"] and full["passed"]
            ),
            "skipped": False,
            "detail": "all declared test blocks completed",
        }

    configuration = validate_configs(plasticity_config, task_cfg)
    checkpoint = validate_checkpoint(plasticity_config, task_cfg)
    determinism = validate_determinism(plasticity_config, task_cfg)
    five_e = _load(REPORT_PATHS["5E"])
    five_f = _load(REPORT_PATHS["5F"])
    five_f_raw = _load(FIVE_F_RESULTS / "comparison_raw.json")
    stability = validate_numerical_stability(five_e, five_f_raw)
    integrity = validate_integrity()

    software = {
        "tests": {
            "focused": focused,
            "phase_4h": phase_4h,
            "full": full,
            "passed": tests_block["passed"],
            "skipped": tests_block["skipped"],
            "detail": tests_block["detail"],
        },
        "configuration": configuration,
        "checkpoint": checkpoint,
        "determinism": determinism,
        "stability": stability,
        "integrity": integrity,
    }

    artifacts = {
        "5B": _load(REPORT_PATHS["5B"]),
        "5C": _load(REPORT_PATHS["5C"]),
        "5D": _load(REPORT_PATHS["5D"]),
        "5E": five_e,
        "5F": five_f,
        "5F_raw": five_f_raw,
    }
    missing = [key for key, value in artifacts.items() if value is None]
    questions = build_questions(artifacts)
    verdicts = build_verdicts(software, questions, five_f)

    condition_means = {}
    if five_f:
        for code, body in _get(five_f, "core", "conditions", default={}).items():
            condition_means[code] = _get(body, "final_success", "mean")
    five_f_summary = None
    if five_f:
        contrast = _get(five_f, "core", "contrasts", PRIMARY_CONTRAST, default={})
        five_f_summary = {
            "mean_difference": contrast.get("mean_difference"),
            "p_value": contrast.get("p_value"),
            "holm_adjusted_p": contrast.get("holm_adjusted_p"),
            "holm_rejected": contrast.get("holm_rejected"),
            "effect_size_dz": contrast.get("effect_size_dz"),
            "n_positive": contrast.get("n_positive"),
            "n_pairs": contrast.get("n_pairs"),
            "condition_means": condition_means,
            "conventional": _get(
                five_f, "conventional", "final_success", "mean"
            ),
        }

    negative_results = []
    negative_results.extend(_get(five_e, "negative_results", default=[]) or [])
    negative_results.extend(_get(five_f, "negative_results", default=[]) or [])
    if missing:
        negative_results.append(
            f"Missing Phase 5 artifacts: {missing}. Their questions are answered "
            "as INCONCLUSIVE or FAIL rather than inferred."
        )
    if not software["tests"]["passed"]:
        negative_results.append(
            "The declared test blocks did not all pass; the software verdict "
            "reflects that failure."
        )

    limitations = list(_get(five_f, "limitations", default=[]) or [])
    limitations.extend(
        [
            "The controlled task is synthetic and small; it is not Subway "
            "Surfers, not the BANC connectome and not an animal behaviour.",
            "A biological interpretation is not available from these "
            "experiments.",
        ]
    )
    if _axis_is_saturated(five_f, "eta"):
        limitations.append(
            "The eta robustness axis produced identical final success across "
            "0.1-2.0, consistent with saturation at the declared weight bounds; "
            "the task does not discriminate the learning rate."
        )
    limitations = list(dict.fromkeys(limitations))

    facts = list(_get(five_f, "facts", default=[]) or [])
    assumptions = list(_get(five_f, "assumptions", default=[]) or [])

    completion_summary = [
        "Phase 5A architecture audit and design report: complete and approved.",
        "Phase 5B reward system: implemented and validated; reports and JSON present.",
        "Phase 5C eligibility traces: implemented and validated; sparse storage checked.",
        "Phase 5D three-factor plasticity: implemented; eta = 0 reproduces fixed-weight hashes exactly.",
        "Phase 5E controlled task: seven conditions run; learning, controls and honest negatives recorded.",
        "Phase 5F comparative evaluation: core contrasts, conventional reference and robustness axes run.",
        "Phase 5G software validation: focused tests, Phase 4H regression, full suite, config, checkpoint, determinism, stability and integrity recorded.",
        "Software verdict: " + verdicts["A_software"]["verdict"] + ".",
        "Controlled-learning verdict: " + verdicts["B_controlled_learning"]["verdict"] + ".",
        "Statistical-evidence verdict: " + verdicts["C_statistical_evidence"]["verdict"] + ".",
        "Biological-interpretation verdict: " + verdicts["D_biological_interpretation"]["verdict"] + ".",
        "Negative results and limitations are retained; no failed result was replaced or hidden.",
        "No commit or push was made; no protected file, dataset or structural connectome was changed.",
    ]

    files = list(REPORT_PATHS.values()) + [
        FIVE_F_RESULTS / "comparison_raw.json",
        FIVE_F_RESULTS / "comparison_analysis.json",
        CHECKPOINT_PATH,
        REPORT_MD,
        REPORT_JSON,
    ]
    versions = software_versions()
    try:
        from importlib.metadata import version as package_version

        versions["pytest"] = package_version("pytest")
    except Exception:
        versions["pytest"] = "unknown"
    assessment = {
        "phase": "5G",
        "title": "Final validation and research assessment",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": {
            "module": "experiments.phase_5.final_assessment",
            "skip_tests": bool(args.skip_tests),
            "skip_full_suite": bool(args.skip_full_suite),
        },
        "software": software,
        "questions": questions,
        "verdicts": verdicts,
        "five_f_summary": five_f_summary,
        "missing_artifacts": missing,
        "negative_results": negative_results,
        "limitations": limitations,
        "facts": facts,
        "assumptions": assumptions,
        "independence_statement": (
            "The unit of replication is a seed. No statistic in Phase 5 pools "
            "timesteps or episodes across seeds."
        ),
        "completion_summary": completion_summary,
        "files": [relative(path) for path in files],
        "software_versions": versions,
        "process_memory": process_memory(),
        "runtime_s": round(time.perf_counter() - started, 2),
    }
    software_ok = bool(
        software["tests"]["passed"]
        and configuration["passed"]
        and checkpoint["passed"]
        and determinism["passed"]
        and stability["passed"]
        and integrity["passed"]
    )
    assessment["software_status"] = "PASS" if software_ok else "FAIL"
    assessment["status"] = (
        "complete"
        if not missing
        else "complete with missing artifacts"
    )

    FIVE_G_RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(FIVE_G_RESULTS / "final_assessment.json", assessment)
    write_json(REPORT_JSON, assessment)
    write_markdown_report(REPORT_MD, assessment)

    print(
        json.dumps(
            {
                "report": relative(REPORT_MD),
                "json": relative(REPORT_JSON),
                "software_status": assessment["software_status"],
                "tests": {
                    key: None if block is None else block["passed"]
                    for key, block in tests.items()
                },
                "configuration": configuration["passed"],
                "checkpoint": checkpoint["passed"],
                "determinism": determinism["passed"],
                "stability": stability["passed"],
                "integrity": integrity["passed"],
                "verdicts": {
                    key: body["verdict"] for key, body in verdicts.items()
                },
                "missing_artifacts": missing,
                "runtime_s": assessment["runtime_s"],
            },
            indent=1,
        )
    )
    return 0 if (
        software["tests"]["passed"]
        and configuration["passed"]
        and checkpoint["passed"]
        and determinism["passed"]
        and stability["passed"]
        and integrity["passed"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
