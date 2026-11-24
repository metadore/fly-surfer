"""P3-3C.5 lane encoding — implementation of the amended preregistration.

IMPLEMENTATION ONLY. EXECUTION IS NOT AUTHORISED.

The module implements:

* the frozen 42-run-per-seed condition matrix and the exact 12-frame lane
  timelines (C1-C4, constants, no input, linear 200 ms, closed 150 ms,
  single-transition controls and the crossfade replay);
* deterministic schedule construction through the existing
  ``SensoryInputScheduler`` with ``active_features=["player_lane"]``;
* the M6' primary measurement and the pre-registered secondary values;
* the applicable execution gates E1-E10 and E12-E16. Gate E11 is withdrawn by
  the 2026-11-14 amendment; no E11' exists;
* an explicit execution guard. ``--execute`` requires a campaign selection and
  the ``--acknowledge-execution-authorised`` flag, and every execution is
  refused unless the operative preregistration hash matches.

Running this module without ``--execute`` performs planning, validation or
static arithmetic only. It never constructs a ``BrainSimulator`` and never
produces spike data.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import gc
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.brain_simulator import BrainSimulator  # noqa: E402
from brain.connectome_loader import load_connectome  # noqa: E402
from brain.neuron_model import LIFParameters  # noqa: E402
from brain.synapse_model import SynapseParameters  # noqa: E402
from sensory.game_state import GameState, PlayerState  # noqa: E402
from sensory.input_scheduler import SensoryInputScheduler  # noqa: E402
from sensory.population_encoder import build_encoders  # noqa: E402
from sensory.sensory_experiment import (  # noqa: E402
    SensorySetup,
    load_config,
)
from sensory.sensory_mapping import SensoryMapping  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "p3_3c5_lane_encoding.yaml"
PREREG_PATH = (
    PROJECT_ROOT / "docs" / "P3_3C5_LANE_ENCODING_PREREGISTRATION.md"
)
AMENDMENT_PATH = (
    PROJECT_ROOT / "docs" / "P3_3C5_PROTOCOL_AMENDMENT_RECORD.md"
)
SENSORY_CONFIG = PROJECT_ROOT / "configs" / "sensory_config.yaml"
SIMULATION_CONFIG = PROJECT_ROOT / "configs" / "simulation_config.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"

RESULTS_DIR = PROJECT_ROOT / "experiments" / "phase_3c" / "results"
JSON_PATH = RESULTS_DIR / "p3_3c5_lane_encoding.json"
SIDECAR_PATH = RESULTS_DIR / "p3_3c5_lane_encoding.sidecar.json"
REPORT_PATH = RESULTS_DIR / "p3_3c5_lane_encoding_report.md"
SPIKES_PATH = RESULTS_DIR / "p3_3c5_lane_encoding_spikes.npz"


def campaign_paths(campaign: str) -> dict:
    """Artifact paths per campaign; the pilot and determinism never share names."""
    if campaign == "main":
        return {
            "json": JSON_PATH,
            "sidecar": SIDECAR_PATH,
            "report": REPORT_PATH,
            "spikes": SPIKES_PATH,
        }
    base = RESULTS_DIR / f"p3_3c5_lane_encoding_{campaign}"
    return {
        "json": base.with_suffix(".json"),
        "sidecar": base.with_name(base.name + ".sidecar.json"),
        "report": base.with_name(base.name + "_report.md"),
        "spikes": (
            base.with_name(base.name + "_spikes.npz")
            if campaign != "determinism"
            else None
        ),
    }

SOURCE_FILES = (
    "sensory/input_scheduler.py",
    "sensory/population_encoder.py",
    "sensory/game_state.py",
    "sensory/sensory_mapping.py",
    "sensory/sensory_experiment.py",
    "brain/brain_simulator.py",
    "brain/neural_activity.py",
    "brain/neuron_model.py",
    "brain/synapse_model.py",
    "brain/connectome_loader.py",
    "experiments/phase_3c/p3_3c5_lane_encoding.py",
)

PROTECTED = {
    "README.md": (
        PROJECT_ROOT / "README.md",
        "15a17de886d29c8b325c00791d888934e207e8ab65fac7560e1fc954fad7a05b",
    ),
    "connectome.npz": (
        PROJECT_ROOT / "datasets" / "processed" / "connectome.npz",
        "3f568f24e3d77134a8d2d38f82856b8d685c310a1b0cfe941a1c95eeab5f33d8",
    ),
}

LANE_LETTERS = {"L": "left", "C": "center", "R": "right"}
LANE_CODES = {"left": 0, "center": 1, "right": 2}
LANE_ORDER = ("left", "center", "right")
CONDITION_GROUPS = {
    "core": 4,
    "linear_200": 4,
    "closed_150": 10,
    "constant": 3,
    "no_input": 1,
    "single_transition_200": 6,
    "single_transition_150": 6,
    "crossfade": 8,
}
APPLICABLE_GATES = (
    "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10",
    "E12", "E13", "E14", "E15", "E16",
)
OUTCOME_ORDER = (
    "INVALID_EXECUTION",
    "INCONCLUSIVE_SILENT_C",
    "INCONCLUSIVE_OUTSIDE",
    "INCONCLUSIVE_REFERENCE_DEGENERATE",
    "HISTORY_EFFECT_PRESENT",
    "HISTORY_EFFECT_DWELL_DEPENDENT",
    "NEGATIVE_PRIMARY_DWELL_DEPENDENT",
    "TRANSITION_ONSET_ONLY",
    "ROUTE_ONLY",
    "ENDPOINT_EXPLAINED",
    "NO_HISTORY_EFFECT",
)

EXPECTED = {
    "phase": "P3-3C.5",
    "version": "p3_3c5_lane_encoding_v1",
    "duration_ms": 600.5,
    "frame_interval_ms": 50.0,
    "n_frames": 12,
    "dt_ms": 0.5,
    "n_steps": 1201,
    "step_transition_ms": 0.0,
    "crossfade_transition_ms": 50.0,
    "current_pa": 200.0,
    "total_current_pa": 800.0,
    "stimulated_set_size": 12,
    "neurons_per_lane": 4,
    "background_current_pa": 0.0,
    "noise_std_pa": 0.0,
    "max_recorded_spikes": 5_000_000,
    "main_seeds": [20261104, 20261105, 20261106],
    "pilot_seed": 20261107,
    "center_onsets": {"C1": 200.0, "C2": 200.0, "C3": 150.0, "C4": 300.0, "K_C": 0.0},
    "replication_required": 2,
    "replication_total": 3,
    "distinct_runs_per_seed": 42,
    "main_instances": 126,
    "determinism_conditions": ["C1", "C2", "C3", "C4", "N0", "K_C"],
    "determinism_repeats_per_parent": 1,
    "determinism_instances": 18,
    "pilot_instances": 42,
    "planned_instances": 186,
    "prereg_sha256": "d6cdeea1424c11c008061da82a70d5fe2fac2f0cfcbd76dda4f2b3eaeebcbc1f",
    "amendment_sha256": "44096b3d16c31efa782396431aa5dba56ab9e642b38ff3f176c2e064af1b3cdd",
}

EXECUTION_CAMPAIGNS = ("main", "pilot", "determinism")

LIMITATIONS = (
    "Descriptive, not inferential: no p-value, confidence interval or significance claim is made.",
    "Three mapping seeds and four neurons per group support no population inference; exact per-seed values and the range are reported.",
    "The lane encoder is one-hot by construction; the experiment tests the spiking readout's history dependence, not how a fly encodes lane.",
    "Predecessor identity is confounded with predecessor annotation pool (LEFT, CENTER and RIGHT use different pools).",
    "The visual_any pool-matched control is excluded by decision D9 and is not run.",
    "K_C is matched in time since onset but not in absolute time; transition-onset attribution is caveated.",
    "R200 is a one-versus-one reference and cannot support a distributional interpretation.",
    "P2 (C3 vs C4) is a dwell replication, not a perfectly matched primary contrast.",
    "P3 (final LEFT block) is confounded with the last transition route R->L versus C->L.",
    "C3 and C4 are not matched on transition-type order or per-time lane; that is the order manipulation itself.",
    "There is no synapse-block control; outside activity is measured, not subtracted.",
    "Lane-only input is not the natural full-sensory regime and does not generalise to it.",
    "The model has no adaptation or short-term plasticity; any history effect is short-lived.",
    "T5 lane pulses are not implemented; T2/T3 encodings are out of scope.",
    "Structural data are not physiological; synapses and weights are computational approximations.",
    "The final 0.5 ms tail is excluded from binning and reported separately.",
    "The small reference sets cannot substitute for more sequences or more seeds.",
    "Determinism is not robustness; identical repeat hashes do not establish generalisation.",
    "The causal decomposition C1/C2 versus L->C/R->C is a correctness gate, not independent evidence.",
    "With n = 3, no standard deviation or standard error is reported.",
    "The crossfade is causal and one-sided, so it is not time-reversal equivariant.",
    "Frame-sequence reversal does not imply input-current-waveform reversal under the causal scheduler.",
    "Half-open frame boundaries produce endpoint mismatches; no continuous-time reversal is claimed.",
    "C3/C4 remain secondary route/order comparisons; no perfect matching is claimed.",
)


class ExecutionNotAuthorised(RuntimeError):
    """Raised when execution is requested without explicit authorisation."""


# --------------------------------------------------------------------------
# hashing, configuration loading and validation
# --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_state() -> dict:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PROJECT_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    lines = [
        line for line in subprocess.run(
            ["git", "status", "--porcelain"], cwd=PROJECT_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.splitlines() if line.strip()
    ]
    return {
        "head": head,
        "branch": branch,
        "working_tree_dirty": bool(lines),
        "n_status_entries": len(lines),
        "staged_changes": any(line[0] not in " ?" for line in lines),
        "status_porcelain": lines,
    }


RESULTS_RELATIVE = "experiments/phase_3c/results/"


def git_state_stable(before: dict, after: dict) -> bool:
    """E13: ignore the campaign's own outputs, which are intended new files."""
    def filtered(state):
        return [
            line
            for line in state.get("status_porcelain", [])
            if RESULTS_RELATIVE not in line.replace("\\", "/")
        ]

    return bool(
        before["head"] == after["head"]
        and before["branch"] == after["branch"]
        and filtered(before) == filtered(after)
    )


def environment_info() -> dict:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def source_hashes() -> dict:
    payload = {}
    for relative in SOURCE_FILES:
        path = PROJECT_ROOT / relative
        payload[relative] = sha256(path) if path.exists() else None
    return payload


def protected_hashes() -> dict:
    return {
        name: {"expected": expected, "actual": sha256(path)}
        for name, (path, expected) in PROTECTED.items()
    }


def assert_prereg_hashes(cfg: dict | None = None) -> dict:
    cfg = load_protocol() if cfg is None else cfg
    recorded = cfg["preregistration"]["operative_sha256"]
    actual = sha256(PREREG_PATH)
    if actual != recorded or actual != EXPECTED["prereg_sha256"]:
        raise ValueError(
            "operative preregistration hash mismatch: "
            f"file={actual}, config={recorded}, expected={EXPECTED['prereg_sha256']}"
        )
    amendment_recorded = cfg["amendment_record"]["sha256"]
    amendment_actual = sha256(AMENDMENT_PATH)
    if (
        amendment_actual != amendment_recorded
        or amendment_actual != EXPECTED["amendment_sha256"]
    ):
        raise ValueError("protocol amendment record hash mismatch")
    return {
        "preregistration": {"expected": recorded, "actual": actual},
        "amendment_record": {
            "expected": amendment_recorded,
            "actual": amendment_actual,
        },
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _assert_close(actual, expected, name: str, tolerance: float = 1e-9) -> None:
    if abs(float(actual) - float(expected)) > tolerance:
        raise ValueError(f"{name}={actual!r} != pre-registered {expected!r}")


def _sequence_predecessor(sequence: list[str]) -> str | None:
    if "C" not in sequence:
        return None
    index = sequence.index("C")
    if index == 0:
        return None
    return LANE_LETTERS[sequence[index - 1]]


def _validate_conditions(cfg: dict) -> None:
    conditions = cfg.get("conditions")
    _require(isinstance(conditions, list) and conditions, "conditions must be a list")
    _require(len(conditions) == 42, "exactly 42 distinct runs per seed are required")
    identifiers = [condition.get("id") for condition in conditions]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("condition identifiers must be unique")
    by_id = {condition["id"]: condition for condition in conditions}
    group_counts = {group: 0 for group in CONDITION_GROUPS}
    n0_count = 0
    for condition in conditions:
        group = condition.get("group")
        _require(group in CONDITION_GROUPS, f"unknown group {group!r}")
        group_counts[group] += 1
        mode = condition.get("mode")
        _require(mode in {"step", "crossfade", "none"}, f"bad mode {mode!r}")
        sequence = condition.get("sequence")
        if mode == "none":
            n0_count += 1
            _require(condition["id"] == "N0", "only N0 may have mode none")
            _require(sequence is None, "N0 must have sequence null")
            _require("replay_of" not in condition, "N0 cannot replay a sequence")
            continue
        _require(
            isinstance(sequence, list)
            and len(sequence) == EXPECTED["n_frames"]
            and all(value in LANE_LETTERS for value in sequence),
            f"condition {condition['id']} must be 12 lane letters",
        )
        if mode == "crossfade":
            _require(group == "crossfade", "crossfade mode requires crossfade group")
            replay = condition.get("replay_of")
            _require(replay in by_id, "crossfade replay_of must name a condition")
            _require(
                by_id[replay]["sequence"] == sequence,
                "crossfade sequence must equal its replay_of sequence",
            )
        else:
            _require(group != "crossfade", "crossfade group requires crossfade mode")
        if group.startswith("single_transition_"):
            pre = int(condition["pre_frames"])
            post = int(condition["post_frames"])
            _require(pre + post == 12, "single-transition frames must total 12")
            _require(
                sequence[:pre] == [sequence[0]] * pre
                and sequence[pre:] == [sequence[pre]] * post,
                "single-transition sequence must be one change",
            )
            _assert_close(
                condition["transition_ms_absolute"],
                pre * EXPECTED["frame_interval_ms"],
                "transition_ms_absolute",
            )
            _require(
                condition["route"]
                == f"{sequence[0]}->{sequence[pre]}",
                "route must match the sequence",
            )
            _require(
                LANE_LETTERS[sequence[pre]] == condition["new_lane"],
                "new_lane must match the sequence",
            )
    for group, expected in CONDITION_GROUPS.items():
        _require(
            group_counts[group] == expected,
            f"group {group} has {group_counts[group]} conditions, expected {expected}",
        )
    _require(n0_count == 1, "exactly one no-input condition is required")

    for focal, expected_onset in EXPECTED["center_onsets"].items():
        sequence = by_id[focal]["sequence"]
        onset = sequence.index("C") * EXPECTED["frame_interval_ms"]
        _assert_close(onset, expected_onset, f"{focal} CENTER onset")
    _require(
        by_id["C1"]["sequence"] == ["L"] * 4 + ["C"] * 4 + ["R"] * 4,
        "C1 sequence mismatch",
    )
    _require(
        by_id["C2"]["sequence"] == ["R"] * 4 + ["C"] * 4 + ["L"] * 4,
        "C2 sequence mismatch",
    )
    _require(
        by_id["C3"]["sequence"] == ["L"] * 3 + ["C"] * 3 + ["R"] * 3 + ["L"] * 3,
        "C3 sequence mismatch",
    )
    _require(
        by_id["C4"]["sequence"] == ["L"] * 3 + ["R"] * 3 + ["C"] * 3 + ["L"] * 3,
        "C4 sequence mismatch",
    )


def _validate_references(cfg: dict) -> None:
    by_id = {condition["id"]: condition for condition in cfg["conditions"]}
    r200 = cfg["references"]["r200"]
    _require(len(r200["all_condition_ids"]) == 6, "R200 must list six permutations")
    for key in ("pred_left", "pred_right", "no_predecessor"):
        for condition_id in r200[key]:
            _require(condition_id in by_id, f"R200 references unknown {condition_id}")
            expected = {
                "pred_left": "left",
                "pred_right": "right",
                "no_predecessor": None,
            }[key]
            _require(
                _sequence_predecessor(by_id[condition_id]["sequence"]) == expected,
                f"R200 classification mismatch for {condition_id}",
            )
    r150 = cfg["references"]["r150"]
    _require(len(r150["all_condition_ids"]) == 12, "R150 must list twelve sequences")
    for key in ("pred_left", "pred_right", "no_predecessor"):
        for condition_id in r150[key]:
            _require(condition_id in by_id, f"R150 references unknown {condition_id}")
            expected = {
                "pred_left": "left",
                "pred_right": "right",
                "no_predecessor": None,
            }[key]
            _require(
                _sequence_predecessor(by_id[condition_id]["sequence"]) == expected,
                f"R150 classification mismatch for {condition_id}",
            )
    _require(len(r150["pred_left"]) == 5, "R150 pred_left must have five entries")
    _require(len(r150["pred_right"]) == 2, "R150 pred_right must have two entries")
    _require(len(r150["no_predecessor"]) == 3, "R150 none must have three entries")
    _require("C3" in r150["all_condition_ids"], "R150 must include C3")
    _require("C4" in r150["all_condition_ids"], "R150 must include C4")
    _require("C1" in r200["all_condition_ids"], "R200 must include C1")
    _require("C2" in r200["all_condition_ids"], "R200 must include C2")


def load_protocol(path: Path = CONFIG_PATH) -> dict:
    cfg = load_yaml(path)
    _require(cfg.get("phase") == EXPECTED["phase"], "phase must be P3-3C.5")
    _require(cfg.get("version") == EXPECTED["version"], "version mismatch")
    _require(
        cfg.get("status") == "IMPLEMENTATION_ONLY_EXECUTION_NOT_AUTHORISED",
        "status must state that execution is not authorised",
    )

    protocol = cfg["protocol"]
    for key in (
        "duration_ms", "frame_interval_ms", "n_frames", "dt_ms", "n_steps",
        "stimulated_set_size", "neurons_per_lane", "background_current_pa",
        "noise_std_pa", "max_recorded_spikes",
    ):
        _assert_close(protocol[key], EXPECTED[key], f"protocol.{key}")
    _require(
        set(protocol["current_pa"]) == {"player_lane"},
        "only player_lane may carry a current amplitude",
    )
    _assert_close(
        protocol["current_pa"]["player_lane"], EXPECTED["current_pa"],
        "protocol.current_pa.player_lane",
    )
    _assert_close(
        protocol["total_sensory_current_pa"], EXPECTED["total_current_pa"],
        "protocol.total_sensory_current_pa",
    )
    _require(
        int(protocol["simulator_seed"]) in EXPECTED["main_seeds"],
        "simulator seed must be one of the recorded main seeds",
    )
    _assert_close(
        protocol["transition_ms"]["step"], EXPECTED["step_transition_ms"],
        "protocol.transition_ms.step",
    )
    _assert_close(
        protocol["transition_ms"]["crossfade"], EXPECTED["crossfade_transition_ms"],
        "protocol.transition_ms.crossfade",
    )
    _require(protocol["active_features"] == ["player_lane"], "only player_lane is active")
    _require(protocol["phase2_stimulus"] is None, "Phase 2 stimulus must be disabled")
    _require(protocol["lane_order"] == list(LANE_ORDER), "lane order must be L/C/R")
    _require(protocol["lane_codes"] == LANE_CODES, "lane codes must be 0/1/2")

    scheduler = cfg["scheduler"]
    _require(
        scheduler["backend"] == "sensory.input_scheduler.SensoryInputScheduler",
        "scheduler backend must be SensoryInputScheduler",
    )
    _assert_close(scheduler["onset_ms"], 0.0, "scheduler.onset_ms")
    _assert_close(scheduler["offset_ms"], EXPECTED["duration_ms"], "scheduler.offset_ms")
    _require(
        scheduler["temporal_activation_scheduler"] == "not_used",
        "TemporalActivationScheduler must not be used",
    )

    seeds = cfg["seeds"]
    _require(seeds["main"] == EXPECTED["main_seeds"], "main seeds mismatch")
    _require(seeds["pilot"] == EXPECTED["pilot_seed"], "pilot seed mismatch")
    _require(seeds["pilot_excluded_from_main"] is True, "pilot must be excluded")

    analysis = cfg["analysis"]
    _assert_close(analysis["bin_ms"], 50.0, "analysis.bin_ms")
    _require(analysis["absolute_bins"] == 12, "twelve absolute bins are required")
    _require(analysis["absolute_bins_coverage_ms"] == [0.0, 600.0], "bin coverage")
    _require(analysis["tail_ms"] == [600.0, 600.5], "tail must be 600-600.5 ms")
    _require(analysis["state_relative_bins"] == [0, 1, 2], "three state bins")
    _require(analysis["group_size"] == 4, "four neurons per group")
    for focal, expected_onset in EXPECTED["center_onsets"].items():
        _assert_close(
            analysis["center_onsets_ms"][focal], expected_onset,
            f"analysis.center_onsets_ms.{focal}",
        )
    _require(
        analysis["primary"] == {
            "condition_a": "C1", "condition_b": "C2",
            "population_lane": "center", "metric": "M6_prime",
        },
        "primary contrast must be C1 vs C2 on CENTER with M6'",
    )
    _require(
        analysis["dwell_replication"] == {
            "condition_a": "C3", "condition_b": "C4",
            "population_lane": "center", "metric": "M6_prime",
        },
        "dwell replication must be C3 vs C4 on CENTER with M6'",
    )
    _require(
        analysis["auxiliary"]["condition_reference"] == "K_C",
        "auxiliary reference must be K_C",
    )
    _require(
        analysis["auxiliary"]["comparisons"] == [["C1", "K_C"], ["C2", "K_C"]],
        "auxiliary comparisons must be C1/C2 against K_C",
    )

    measurement = cfg["measurement"]
    _require(measurement["primary_metric"] == "M6_prime", "metric must be M6'")
    _assert_close(
        measurement["per_neuron_rate_denominator_ms"], 50.0,
        "measurement.per_neuron_rate_denominator_ms",
    )
    _require(
        measurement["aggregation"]
        == "mean_over_state_relative_bins_then_center_neurons",
        "aggregation mismatch",
    )
    _require(measurement["baseline_subtraction"] is False, "no baseline subtraction")
    _require(measurement["normalization"] == "none", "no normalization")
    _require(
        measurement["cross_population_combination"] is False,
        "populations must not be combined",
    )
    _require(
        measurement["cosine_on_signed_or_sparse_rate_vectors"] is False,
        "cosine is forbidden for signed or sparse rate vectors",
    )
    _require(measurement["units"] == "Hz", "rates must be in Hz")

    decision = cfg["decision"]
    _require(decision["inference"] == "descriptive_only", "descriptive inference only")
    for key in (
        "p_values", "confidence_intervals", "standard_errors",
        "significance_claims", "dprime_used", "threshold_invented",
    ):
        _require(decision[key] is False, f"decision.{key} must be false")
    _require(
        tuple(decision["outcome_order"]) == OUTCOME_ORDER,
        "outcome order mismatch",
    )
    _require(
        decision["replication_required_seeds"] == EXPECTED["replication_required"]
        and decision["replication_total_seeds"] == EXPECTED["replication_total"],
        "replication rule must be 2 of 3",
    )

    determinism = cfg["determinism"]
    _require(
        determinism["set"] == EXPECTED["determinism_conditions"],
        "determinism subset mismatch",
    )
    _require(determinism["mode"] == "step", "determinism subset must be step mode")
    _require(
        determinism["repeats_per_parent"] == EXPECTED["determinism_repeats_per_parent"],
        "one repeat per parent",
    )
    _require(determinism["fresh_subprocess"] is True, "repeats must use subprocesses")
    _require(determinism["seeds"] == "main", "determinism subset uses main seeds")

    matrix = cfg["run_matrix"]
    _require(matrix["distinct_runs_per_seed"] == EXPECTED["distinct_runs_per_seed"], "42 runs")
    _require(matrix["main_instances"] == EXPECTED["main_instances"], "126 main instances")
    _require(
        matrix["determinism_instances"] == EXPECTED["determinism_instances"],
        "18 determinism instances",
    )
    _require(matrix["pilot_instances"] == EXPECTED["pilot_instances"], "42 pilot instances")
    _require(
        matrix["planned_instances"] == EXPECTED["planned_instances"],
        "186 planned instances",
    )
    _require(matrix["core"] == 4 and matrix["linear_200"] == 4, "matrix counts")
    _require(matrix["closed_150"] == 10 and matrix["constant"] == 3, "matrix counts")
    _require(matrix["no_input"] == 1 and matrix["crossfade"] == 8, "matrix counts")
    _require(
        matrix["single_transition_200"] == 6
        and matrix["single_transition_150"] == 6,
        "matrix counts",
    )
    _require(
        matrix["determinism_repeat_conditions"] == 6
        and matrix["determinism_repeats"] == 1,
        "determinism matrix counts",
    )

    gates = cfg["gates"]
    _require(tuple(gates["applicable"]) == APPLICABLE_GATES, "applicable gates mismatch")
    _require(gates["withdrawn"] == ["E11"], "E11 must be the only withdrawn gate")
    _require(gates["replacement_for_e11"] == "none", "no E11 replacement may exist")
    _require(gates["e11_withdrawal_date"] == "2026-11-14", "E11 withdrawal date")
    _require(
        gates["e2_per_step_nonzero"]
        == {"step": 4, "crossfade": [4, 8], "no_input": 0},
        "E2 per-step counts mismatch",
    )
    _assert_close(gates["e3_tolerance_pa"], 1e-9, "E3 tolerance")
    _require(gates["e5_requires_input_schedule_none"] is True, "E5 requires None")
    _assert_close(gates["e8_grid_ms"], 50.0, "E8 grid")
    _require(gates["e9_window_ms"] == [0.0, 150.0], "E9 window")
    _require(gates["e10_lists_conditions"] is True, "E10 must list conditions")
    _require(gates["e15_half_open"] is True, "E15 half-open bins")

    pilot = cfg["pilot_checks"]
    for key in ("runtime", "capacity", "reference_degeneracy", "metric_computability"):
        _require(key in pilot["checks"], f"pilot check {key} missing")
    _require(pilot["pilot_enters_main_result"] is False, "pilot excluded")
    _require(pilot["threshold_tuning"] is False, "no pilot tuning")

    _validate_conditions(cfg)
    _validate_references(cfg)
    return cfg


# --------------------------------------------------------------------------
# timelines and schedule construction
# --------------------------------------------------------------------------


def conditions_by_id(cfg: dict) -> dict:
    return {condition["id"]: condition for condition in cfg["conditions"]}


def condition_timeline(condition: dict, frame_interval_ms: float):
    sequence = condition["sequence"]
    if sequence is None:
        return None
    timeline = []
    for index, letter in enumerate(sequence):
        timestamp = index * float(frame_interval_ms)
        timeline.append(
            (
                timestamp,
                GameState(
                    player=PlayerState(lane=LANE_LETTERS[letter]),
                    time_ms=timestamp,
                ),
            )
        )
    return timeline


def sequence_hash(sequence: list[str] | None) -> str | None:
    if sequence is None:
        return None
    canonical = json.dumps(sequence, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(canonical)


def sequence_reverse(sequence: list[str]) -> list[str]:
    return list(reversed(sequence))


def center_onset_ms(sequence: list[str] | None) -> float | None:
    if not sequence or "C" not in sequence:
        return None
    return sequence.index("C") * 50.0


def expected_nonzero_counts(condition: dict) -> set[int]:
    if condition["mode"] == "none":
        return {0}
    if condition["mode"] == "crossfade":
        return {4, 8}
    return {4}


def build_base_sensory_config() -> dict:
    config = load_config(SENSORY_CONFIG)
    feature = config["features"]["player_lane"]
    _require(feature["kind"] == "lane", "player_lane must use lane coding")
    _require(feature["lanes"] == 3, "player_lane must have three lanes")
    _require(feature["neurons_per_lane"] == 4, "four neurons per lane")
    _assert_close(feature["amplitude"], 1.0, "lane amplitude")
    _assert_close(feature["baseline"], 0.0, "lane baseline")
    _assert_close(feature["current_pa"], EXPECTED["current_pa"], "lane current")
    settings = load_yaml(SIMULATION_CONFIG)
    _assert_close(
        settings["external_input"]["background_current_pa"], 0.0,
        "simulation background",
    )
    _assert_close(
        settings["external_input"]["noise_std_pa"], 0.0,
        "simulation noise",
    )
    return config


def build_mapping(graph, base_config: dict, seed: int):
    config = copy.deepcopy(base_config)
    config["mapping"]["seed"] = int(seed)
    mapping = SensoryMapping(graph, config["mapping"])
    lane_population = mapping.populations["player_lane"]
    _require(
        [name for name, _, _ in lane_population.plan.groups] == list(LANE_ORDER),
        "lane group order must be left, center, right",
    )
    return mapping, config


def mapping_signature(mapping) -> str:
    digest = hashlib.sha256()
    for feature, population in mapping.populations.items():
        digest.update(feature.encode("utf-8"))
        for name, indices in population.groups.items():
            digest.update(name.encode("utf-8"))
            digest.update(np.asarray(indices, dtype=np.int64).tobytes())
    return digest.hexdigest()


def lane_groups(mapping) -> dict[str, np.ndarray]:
    population = mapping.populations["player_lane"]
    if [name for name, _, _ in population.plan.groups] != list(LANE_ORDER):
        raise ValueError("lane group order is not left, center, right")
    groups = {
        name: np.asarray(population.groups[name], dtype=np.int64)
        for name in LANE_ORDER
    }
    all_indices = np.concatenate([groups[name] for name in LANE_ORDER])
    if np.unique(all_indices).size != 12:
        raise ValueError("lane groups must be disjoint and total 12 neurons")
    for name in LANE_ORDER:
        if groups[name].size != EXPECTED["neurons_per_lane"]:
            raise ValueError(f"lane group {name} does not have four neurons")
    return groups


def lane_root_ids(mapping) -> dict[str, list[int]]:
    population = mapping.populations["player_lane"]
    return {
        name: [int(value) for value in population.root_ids[name]]
        for name in LANE_ORDER
    }


def build_setup(mapping, base_config: dict) -> SensorySetup:
    encoders = build_encoders(base_config["features"])
    return SensorySetup(base_config, encoders, mapping)


def build_scheduler(setup, condition: dict, cfg: dict):
    if condition["mode"] == "none":
        return None
    transition = float(
        cfg["protocol"]["transition_ms"][condition["mode"]]
    )
    scheduler = SensoryInputScheduler(
        setup.mapping,
        setup.encoders,
        condition_timeline(condition, cfg["protocol"]["frame_interval_ms"]),
        dt_ms=float(cfg["protocol"]["dt_ms"]),
        duration_ms=float(cfg["protocol"]["duration_ms"]),
        current_pa=setup.amplitudes,
        transition_ms=transition,
        onset_ms=float(cfg["scheduler"]["onset_ms"]),
        offset_ms=float(cfg["scheduler"]["offset_ms"]),
        active_features=list(cfg["protocol"]["active_features"]),
    )
    expected = 0 if condition["mode"] == "none" else EXPECTED["stimulated_set_size"]
    if scheduler.stimulated_indices.size != expected:
        raise ValueError(
            f"{condition['id']}: stimulated set has "
            f"{scheduler.stimulated_indices.size} indices, expected {expected}"
        )
    return scheduler


def schedule_signature_hash(scheduler) -> str:
    if scheduler is None:
        return _sha256_bytes(b"no-input-schedule")
    signature = scheduler.signature()
    digest = hashlib.sha256()
    digest.update(np.asarray(signature["indices"], dtype=np.int64).tobytes())
    digest.update(np.asarray(signature["values"], dtype=np.float64).tobytes())
    digest.update(np.asarray(signature["starts"], dtype=np.float64).tobytes())
    for scalar in (
        scheduler.dt_ms,
        scheduler.duration_ms,
        scheduler.transition_ms,
        scheduler.onset_ms,
        scheduler.offset_ms,
    ):
        digest.update(np.float64(scalar).tobytes())
    return digest.hexdigest()


# --------------------------------------------------------------------------
# input-current audits (no simulation)
# --------------------------------------------------------------------------


def audit_input_current(scheduler, condition: dict, mapping, cfg: dict) -> dict:
    n_steps = int(cfg["protocol"]["n_steps"])
    dt_ms = float(cfg["protocol"]["dt_ms"])
    n_nodes = int(mapping.graph.n_nodes)
    stimulated = (
        np.array([], dtype=np.int64)
        if scheduler is None
        else np.asarray(scheduler.stimulated_indices, dtype=np.int64)
    )
    stimulated_mask = np.zeros(n_nodes, dtype=bool)
    stimulated_mask[stimulated] = True
    buffer = np.zeros(n_nodes, dtype=np.float64)
    totals = np.empty(n_steps, dtype=np.float64)
    nonzero_counts = np.empty(n_steps, dtype=np.int64)
    active_union = np.zeros(n_nodes, dtype=bool)
    outside_nonzero = 0
    outside_max = 0.0
    for step in range(n_steps):
        buffer.fill(0.0)
        if scheduler is not None:
            scheduler.apply(step, step * dt_ms, buffer)
        total = float(buffer.sum())
        totals[step] = total
        nonzero = buffer != 0.0
        active_union |= nonzero
        nonzero_counts[step] = int(np.count_nonzero(nonzero))
        outside = nonzero & ~stimulated_mask
        outside_nonzero += int(np.count_nonzero(outside))
        if outside.any():
            outside_max = max(outside_max, float(np.abs(buffer[outside]).max()))
    expected_total = (
        0.0 if scheduler is None else float(cfg["protocol"]["total_sensory_current_pa"])
    )
    tolerance = float(cfg["gates"]["e3_tolerance_pa"])
    total_ok = bool(np.all(np.abs(totals - expected_total) <= tolerance))
    allowed = expected_nonzero_counts(condition)
    counts_ok = set(int(value) for value in np.unique(nonzero_counts)).issubset(allowed)
    set_ok = True
    if scheduler is not None:
        set_ok = stimulated.size == EXPECTED["stimulated_set_size"]
    set_ok = set_ok and outside_nonzero == 0 and outside_max == 0.0

    alpha_half = None
    if scheduler is not None and condition["mode"] == "crossfade":
        sequence = condition["sequence"]
        changes = [
            index * float(cfg["protocol"]["frame_interval_ms"])
            for index in range(1, len(sequence))
            if sequence[index] != sequence[index - 1]
        ]
        if changes:
            t0 = changes[0]
            t_mid = t0 + float(cfg["protocol"]["transition_ms"]["crossfade"]) / 2.0
            buffer.fill(0.0)
            scheduler.apply(int(round(t_mid / dt_ms)), t_mid, buffer)
            active = buffer[stimulated]
            alpha_half = {
                "time_ms": t_mid,
                "nonzero_neurons": int(np.count_nonzero(active)),
                "per_neuron_pa": sorted(
                    round(float(value), 9) for value in active[active != 0.0]
                ),
                "total_pa": round(float(active.sum()), 9),
            }
    return {
        "mode": condition["mode"],
        "n_steps": n_steps,
        "duration_ms": n_steps * dt_ms,
        "stimulated_indices": sorted(int(value) for value in stimulated),
        "stimulated_set_size": int(stimulated.size),
        "total_current_min_pa": round(float(totals.min()), 6),
        "total_current_max_pa": round(float(totals.max()), 6),
        "expected_total_pa": expected_total,
        "total_current_tolerance_pa": tolerance,
        "total_current_ok": total_ok,
        "nonzero_counts_observed": sorted(
            int(value) for value in np.unique(nonzero_counts)
        ),
        "nonzero_counts_allowed": sorted(allowed),
        "nonzero_counts_ok": bool(counts_ok),
        "outside_nonzero_entries": int(outside_nonzero),
        "outside_max_abs_pa": round(outside_max, 9),
        "stimulated_set_ok": bool(set_ok),
        "active_indices": sorted(
            int(value) for value in np.flatnonzero(active_union)
        ),
        "alpha_half_check": alpha_half,
    }


def constant_group_ok(audit: dict, groups: dict[str, np.ndarray], lane: str) -> bool:
    return audit["active_indices"] == sorted(
        int(value) for value in groups[lane]
    )


# --------------------------------------------------------------------------
# measurement primitives
# --------------------------------------------------------------------------


def absolute_bin_edges(cfg: dict) -> np.ndarray:
    bins = int(cfg["analysis"]["absolute_bins"])
    width = float(cfg["analysis"]["bin_ms"])
    return np.arange(0.0, bins * width + width, width, dtype=np.float64)


def _bin_indices(times: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.searchsorted(edges, times, side="right") - 1


def bin_count_matrix(times, indices, neuron_ids, edges) -> np.ndarray:
    """Per-neuron, per-bin counts with half-open bins ``[edge_b, edge_{b+1})``."""
    times = np.asarray(times, dtype=np.float64)
    indices = np.asarray(indices, dtype=np.int64)
    neuron_ids = np.asarray(neuron_ids, dtype=np.int64)
    n_bins = len(edges) - 1
    matrix = np.zeros((neuron_ids.size, n_bins), dtype=np.int64)
    for position, neuron in enumerate(neuron_ids):
        selected = times[indices == neuron]
        if selected.size:
            bins = _bin_indices(selected, edges)
            valid = (bins >= 0) & (bins < n_bins)
            if valid.any():
                matrix[position] = np.bincount(
                    bins[valid], minlength=n_bins
                )[:n_bins]
    return matrix


def state_relative_counts(
    times, indices, neuron_ids, onset_ms: float, bins: int = 3,
    bin_ms: float = 50.0,
) -> np.ndarray:
    edges = float(onset_ms) + np.arange(0, bins + 1, dtype=np.float64) * float(bin_ms)
    return bin_count_matrix(times, indices, neuron_ids, edges)


def tail_count(times, indices, neuron_ids, duration_ms: float = 600.0) -> int:
    times = np.asarray(times, dtype=np.float64)
    indices = np.asarray(indices, dtype=np.int64)
    selected = np.isin(indices, np.asarray(neuron_ids, dtype=np.int64))
    return int(np.count_nonzero(times[selected] >= float(duration_ms)))


def rates_from_counts(counts: np.ndarray, bin_ms: float = 50.0) -> np.ndarray:
    return np.asarray(counts, dtype=np.float64) / (float(bin_ms) / 1000.0)


def m6_prime(counts: np.ndarray, bin_ms: float = 50.0) -> dict:
    rates = rates_from_counts(counts, bin_ms)
    per_bin = rates.mean(axis=0)
    return {
        "value_hz": float(per_bin.mean()),
        "per_bin_hz": [float(value) for value in per_bin],
        "per_neuron_hz": [[float(value) for value in row] for row in rates],
    }


def _validated_per_neuron_rows(measurement: dict, label: str) -> list:
    for key in ("value_hz", "per_bin_hz", "per_neuron_hz"):
        if key not in measurement:
            raise ValueError(f"{label} measurement is missing {key!r}")
    rows = measurement["per_neuron_hz"]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label} measurement has no per-neuron rows")
    width = len(rows[0])
    if width == 0:
        raise ValueError(f"{label} measurement has no state-relative bins")
    for row in rows:
        if not isinstance(row, list) or len(row) != width:
            raise ValueError(f"{label} per-neuron rows are ragged")
    if len(measurement["per_bin_hz"]) != width:
        raise ValueError(f"{label} per-bin and per-neuron bin counts disagree")
    return rows


def subtract_measurement(first: dict, second: dict) -> dict:
    first_rows = _validated_per_neuron_rows(first, "minuend")
    second_rows = _validated_per_neuron_rows(second, "subtrahend")
    if len(first_rows) != len(second_rows):
        raise ValueError("measurements disagree on neuron count")
    if len(first_rows[0]) != len(second_rows[0]):
        raise ValueError("measurements disagree on bin count")
    per_neuron = [
        [float(a - b) for a, b in zip(row_a, row_b)]
        for row_a, row_b in zip(first_rows, second_rows)
    ]
    return {
        "value_hz": float(first["value_hz"] - second["value_hz"]),
        "per_bin_hz": [
            float(a - b) for a, b in zip(first["per_bin_hz"], second["per_bin_hz"])
        ],
        "per_neuron_hz": per_neuron,
        "per_neuron_mean_hz": [float(np.mean(row)) for row in per_neuron],
    }


def window_counts(
    times, indices, neuron_ids, start_ms: float, end_ms: float
) -> int:
    times = np.asarray(times, dtype=np.float64)
    indices = np.asarray(indices, dtype=np.int64)
    selected = np.isin(indices, np.asarray(neuron_ids, dtype=np.int64))
    selected &= (times >= float(start_ms)) & (times < float(end_ms))
    return int(np.count_nonzero(selected))


def window_rate(
    times, indices, neuron_ids, start_ms: float, end_ms: float
) -> float:
    duration_s = (float(end_ms) - float(start_ms)) / 1000.0
    if duration_s <= 0:
        return 0.0
    return window_counts(times, indices, neuron_ids, start_ms, end_ms) / (
        len(neuron_ids) * duration_s
    )


def _array_to_list(values) -> list:
    return [int(value) for value in np.asarray(values, dtype=np.int64)]


# --------------------------------------------------------------------------
# per-condition and per-seed measurement
# --------------------------------------------------------------------------


def measure_condition(raw: dict, condition: dict, groups, cfg: dict) -> dict:
    times = raw["times"]
    indices = raw["indices"]
    edges = absolute_bin_edges(cfg)
    bin_ms = float(cfg["analysis"]["bin_ms"])
    lane_absolute = {}
    lane_active = {}
    for lane in LANE_ORDER:
        matrix = bin_count_matrix(times, indices, groups[lane], edges)
        counts = matrix.sum(axis=0)
        lane_absolute[lane] = {
            "counts": [int(value) for value in counts],
            "rates_hz": [
                float(value)
                for value in rates_from_counts(counts, bin_ms)
            ],
            "per_neuron_counts": [
                [int(value) for value in row] for row in matrix
            ],
        }
        lane_active[lane] = [
            int(np.count_nonzero(matrix[:, index]))
            for index in range(matrix.shape[1])
        ]
    all_stimulated = np.concatenate([groups[lane] for lane in LANE_ORDER])
    outside_mask = ~np.isin(
        indices, all_stimulated
    )
    outside_times = times[outside_mask]
    outside_indices = indices[outside_mask]
    outside = {
        "spikes": int(outside_times.size),
        "active_neurons": int(np.unique(outside_indices).size),
        "fraction": float(outside_times.size / max(1, times.size)),
    }

    onset = center_onset_ms(condition["sequence"])
    center = None
    extra = {}
    if onset is not None:
        counts = state_relative_counts(
            times, indices, groups["center"], onset,
            bins=len(cfg["analysis"]["state_relative_bins"]),
            bin_ms=cfg["analysis"]["state_relative_bin_ms"],
        )
        center = {
            "onset_ms": float(onset),
            "counts": [[int(value) for value in row] for row in counts],
            "rates_hz": [
                [float(value) for value in row]
                for row in rates_from_counts(counts, cfg["analysis"]["state_relative_bin_ms"])
            ],
            "m6_prime": m6_prime(counts, cfg["analysis"]["state_relative_bin_ms"]),
        }
        extra_bins = cfg["analysis"]["extra_state_relative_bins"].get(
            condition["id"], []
        )
        for extra_bin in extra_bins:
            extra[f"s{extra_bin}"] = {
                "counts": [
                    int(value) for value in state_relative_counts(
                        times, indices, groups["center"], onset,
                        bins=int(extra_bin) + 1,
                        bin_ms=cfg["analysis"]["state_relative_bin_ms"],
                    )[:, int(extra_bin)]
                ]
            }

    if condition["id"] in ("C1", "C2"):
        absorbed = state_relative_counts(
            times, indices, groups["center"], onset, bins=4,
            bin_ms=cfg["analysis"]["state_relative_bin_ms"],
        )
        extra["measured_window_and_s3_counts"] = [
            [int(value) for value in row] for row in absorbed
        ]

    new_lane = None
    if "new_lane" in condition:
        new_lane = {
            "lane": condition["new_lane"],
            "onset_ms": float(condition["transition_ms_absolute"]),
            "counts": [
                [int(value) for value in row]
                for row in state_relative_counts(
                    times, indices, groups[condition["new_lane"]],
                    float(condition["transition_ms_absolute"]),
                    bins=3, bin_ms=cfg["analysis"]["state_relative_bin_ms"],
                )
            ],
        }

    center_latency = None
    center_peak = None
    if onset is not None:
        center_spikes = times[np.isin(indices, groups["center"])]
        center_spikes = center_spikes[center_spikes >= onset]
        center_latency = (
            float(center_spikes.min() - onset) if center_spikes.size else None
        )
        counts = state_relative_counts(
            times, indices, groups["center"], onset, bins=3,
            bin_ms=cfg["analysis"]["state_relative_bin_ms"],
        )
        rates = rates_from_counts(counts, cfg["analysis"]["state_relative_bin_ms"]).mean(axis=0)
        peak_index = int(np.argmax(rates))
        center_peak = {
            "peak_rate_hz": float(rates[peak_index]),
            "peak_bin_start_ms": float(onset + peak_index * 50.0),
        }

    return {
        "condition_id": condition["id"],
        "group": condition["group"],
        "mode": condition["mode"],
        "seed": int(raw["seed"]),
        "sequence": condition["sequence"],
        "sequence_sha256": sequence_hash(condition["sequence"]),
        "timeline_ms": [
            index * float(cfg["protocol"]["frame_interval_ms"])
            for index in range(len(condition["sequence"] or []))
        ],
        "n_spikes": int(times.size),
        "n_steps": int(raw["n_steps"]),
        "duration_ms": float(raw["duration_ms"]),
        "stimulated_indices": sorted(
            int(value) for value in raw["stimulated_indices"]
        ),
        "absolute_bins": {
            "edges_ms": [float(value) for value in edges],
            "by_lane": lane_absolute,
            "active_neurons_by_lane": lane_active,
        },
        "tail_counts": {
            "center": tail_count(times, indices, groups["center"]),
            "left": tail_count(times, indices, groups["left"]),
            "right": tail_count(times, indices, groups["right"]),
            "all_stimulated": tail_count(times, indices, all_stimulated),
        },
        "outside": outside,
        "center_state_relative": center,
        "extra_state_relative": extra,
        "new_lane_state_relative": new_lane,
        "latency": {
            "first_center_spike_latency_ms": center_latency,
            "center_peak": center_peak,
        },
        "current_audit": raw["input_audit"],
        "spike_digest": raw["spike_digest"],
        "schedule_digest": raw["schedule_digest"],
        "wall_runtime_s": round(float(raw["wall_runtime_s"]), 6),
    }


def _mean(values) -> float:
    values = [float(value) for value in values]
    return float(np.mean(values)) if values else 0.0


def _range(values) -> dict:
    values = [float(value) for value in values]
    return {"min": min(values), "max": max(values), "range": max(values) - min(values)}


def sign_of(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def separated_pair(left: float, right: float) -> str | None:
    if left > right:
        return "pred_left_above_pred_right"
    if right > left:
        return "pred_right_above_pred_left"
    return None


def separated_ranges(left_values, right_values) -> str | None:
    left_values = [float(value) for value in left_values]
    right_values = [float(value) for value in right_values]
    if min(left_values) > max(right_values):
        return "pred_left_above_pred_right"
    if max(left_values) < min(right_values):
        return "pred_right_above_pred_left"
    return None


def focal_pair(
    left_value: float,
    right_value: float,
    focal_left: float,
    focal_right: float,
    difference: float,
    direction: str | None,
) -> bool:
    if direction is None:
        return False
    if direction == "pred_left_above_pred_right":
        return (
            focal_left >= left_value
            and focal_right <= right_value
            and difference > 0
        )
    return (
        focal_left <= left_value
        and focal_right >= right_value
        and difference < 0
    )


def focal_ranges(
    pred_left_values,
    pred_right_values,
    focal_left: float,
    focal_right: float,
    difference: float,
    direction: str | None,
) -> bool:
    if direction is None:
        return False
    left_values = [float(value) for value in pred_left_values]
    right_values = [float(value) for value in pred_right_values]
    if direction == "pred_left_above_pred_right":
        return (
            focal_left >= max(left_values)
            and focal_right <= min(right_values)
            and difference > 0
        )
    return (
        focal_left <= min(left_values)
        and focal_right >= max(right_values)
        and difference < 0
    )


def analyse_seed(raw_runs: dict, cfg: dict, groups) -> dict:
    by_id = conditions_by_id(cfg)
    measurements = {
        condition_id: measure_condition(raw, by_id[condition_id], groups, cfg)
        for condition_id, raw in raw_runs.items()
    }

    def center_metric(condition_id: str) -> dict:
        return measurements[condition_id]["center_state_relative"]["m6_prime"]

    primary = subtract_measurement(center_metric("C1"), center_metric("C2"))
    dwell = subtract_measurement(center_metric("C3"), center_metric("C4"))
    kc_metric = center_metric("K_C")
    auxiliary = {
        "K_C": kc_metric,
        "C1_minus_K_C": subtract_measurement(center_metric("C1"), kc_metric),
        "C2_minus_K_C": subtract_measurement(center_metric("C2"), kc_metric),
    }

    final_left = cfg["analysis"]["final_left"]
    final_bins = final_left["bins"]
    left_c3 = state_relative_counts(
        raw_runs["C3"]["times"], raw_runs["C3"]["indices"], groups["left"],
        final_left["onset_ms"], bins=max(final_bins) + 1,
    )
    left_c4 = state_relative_counts(
        raw_runs["C4"]["times"], raw_runs["C4"]["indices"], groups["left"],
        final_left["onset_ms"], bins=max(final_bins) + 1,
    )
    left_c3_rates = rates_from_counts(left_c3)
    left_c4_rates = rates_from_counts(left_c4)
    delta_l_bins = [
        float(left_c3_rates.mean(axis=0)[index] - left_c4_rates.mean(axis=0)[index])
        for index in final_bins
    ]
    delta_l = _mean(delta_l_bins)

    right = cfg["analysis"]["right_block"]
    right_bins = right["lanes_by_condition"]["C3"]["bins"]
    right_c3 = state_relative_counts(
        raw_runs["C3"]["times"], raw_runs["C3"]["indices"], groups["right"],
        right["lanes_by_condition"]["C3"]["onset_ms"], bins=max(right_bins) + 1,
    )
    right_c4 = state_relative_counts(
        raw_runs["C4"]["times"], raw_runs["C4"]["indices"], groups["right"],
        right["lanes_by_condition"]["C4"]["onset_ms"], bins=max(right_bins) + 1,
    )
    right_c3_rates = rates_from_counts(right_c3)
    right_c4_rates = rates_from_counts(right_c4)
    delta_r_bins = [
        float(right_c3_rates.mean(axis=0)[index] - right_c4_rates.mean(axis=0)[index])
        for index in right_bins
    ]
    delta_r = _mean(delta_r_bins)

    adjustment = cfg["analysis"]["route_adjustment"]
    minuend = center_metric(adjustment["minuend"])
    subtrahend = center_metric(adjustment["subtrahend"])
    route_difference = subtract_measurement(minuend, subtrahend)
    delta_adj = {
        "value_hz": float(dwell["value_hz"] - route_difference["value_hz"]),
        "per_bin_hz": [
            float(a - b) for a, b in zip(dwell["per_bin_hz"], route_difference["per_bin_hz"])
        ],
        "components": {
            "dwell_delta": dwell,
            "route_control_difference": route_difference,
        },
    }

    r200 = cfg["references"]["r200"]
    r200_values = {condition_id: center_metric(condition_id) for condition_id in r200["all_condition_ids"]}
    r200_primary_values = {
        condition_id: r200_values[condition_id]["value_hz"]
        for condition_id in r200["all_condition_ids"]
    }
    r200_left = r200_primary_values[r200["pred_left"][0]]
    r200_right = r200_primary_values[r200["pred_right"][0]]
    r200_none = [r200_primary_values[condition_id] for condition_id in r200["no_predecessor"]]
    separated_200 = separated_pair(r200_left, r200_right)

    r150 = cfg["references"]["r150"]
    r150_values = {condition_id: center_metric(condition_id) for condition_id in r150["all_condition_ids"]}
    r150_primary_values = {
        condition_id: r150_values[condition_id]["value_hz"]
        for condition_id in r150["all_condition_ids"]
    }
    r150_left = [r150_primary_values[condition_id] for condition_id in r150["pred_left"]]
    r150_right = [r150_primary_values[condition_id] for condition_id in r150["pred_right"]]
    r150_none = [r150_primary_values[condition_id] for condition_id in r150["no_predecessor"]]
    separated_150 = separated_ranges(r150_left, r150_right)
    r200_degenerate = r200_left == r200_right
    r150_degenerate = (
        max(r150_left) - min(r150_left) == 0
        and max(r150_right) - min(r150_right) == 0
    )

    focal_200 = focal_pair(
        r200_left,
        r200_right,
        measurements["C1"]["center_state_relative"]["m6_prime"]["value_hz"],
        measurements["C2"]["center_state_relative"]["m6_prime"]["value_hz"],
        primary["value_hz"],
        separated_200,
    )
    focal_150 = focal_ranges(
        r150_left,
        r150_right,
        measurements["C3"]["center_state_relative"]["m6_prime"]["value_hz"],
        measurements["C4"]["center_state_relative"]["m6_prime"]["value_hz"],
        dwell["value_hz"],
        separated_150,
    )
    dwell_consistency = (
        sign_of(dwell["value_hz"]) == sign_of(primary["value_hz"])
        and sign_of(primary["value_hz"]) != 0
    )

    routes = {}
    for contrast in cfg["analysis"]["route_contrasts"]:
        first = measurements[contrast["minuend"]]["new_lane_state_relative"]
        second = measurements[contrast["subtrahend"]]["new_lane_state_relative"]
        first_rates = rates_from_counts(np.asarray(first["counts"], dtype=np.int64))
        second_rates = rates_from_counts(np.asarray(second["counts"], dtype=np.int64))
        first_value = float(first_rates.mean(axis=0).mean())
        second_value = float(second_rates.mean(axis=0).mean())
        routes[contrast["id"]] = {
            "minuend": contrast["minuend"],
            "subtrahend": contrast["subtrahend"],
            "value_hz": first_value - second_value,
            "first_hz": first_value,
            "second_hz": second_value,
        }

    stationarity = {}
    for condition in cfg["conditions"]:
        if "new_lane" not in condition:
            continue
        onset = float(condition["transition_ms_absolute"])
        new_lane_group = groups[condition["new_lane"]]
        first_rate = window_rate(
            raw_runs[condition["id"]]["times"],
            raw_runs[condition["id"]]["indices"],
            new_lane_group,
            onset,
            onset + 150.0,
        )
        last_rate = window_rate(
            raw_runs[condition["id"]]["times"],
            raw_runs[condition["id"]]["indices"],
            new_lane_group,
            450.0,
            600.0,
        )
        stationarity[condition["id"]] = {
            "first_150ms_hz": first_rate,
            "last_150ms_hz": last_rate,
            "difference_hz": first_rate - last_rate,
        }

    reverse_time = None
    c3_profile = measurements["C3"]["center_state_relative"]["m6_prime"]["per_bin_hz"]
    c4_profile = measurements["C4"]["center_state_relative"]["m6_prime"]["per_bin_hz"]
    reverse_time = {
        "value_hz": _mean(
            [abs(c3_profile[index] - c4_profile[2 - index]) for index in range(3)]
        ),
        "C3_per_bin_hz": c3_profile,
        "C4_reversed_per_bin_hz": list(reversed(c4_profile)),
    }

    r200_union = sorted([r200_left, r200_right])
    kc_value = kc_metric["value_hz"]
    if kc_value > r200_union[1]:
        side = "above"
        transition_onset = (
            measurements["C1"]["center_state_relative"]["m6_prime"]["value_hz"] > r200_union[1]
            and measurements["C2"]["center_state_relative"]["m6_prime"]["value_hz"] > r200_union[1]
        )
    elif kc_value < r200_union[0]:
        side = "below"
        transition_onset = (
            measurements["C1"]["center_state_relative"]["m6_prime"]["value_hz"] < r200_union[0]
            and measurements["C2"]["center_state_relative"]["m6_prime"]["value_hz"] < r200_union[0]
        )
    else:
        side = "inside"
        transition_onset = False

    endpoint_confined = False
    differences = {}
    for lane in LANE_ORDER:
        c1_counts = np.asarray(
            measurements["C1"]["absolute_bins"]["by_lane"][lane]["counts"], dtype=np.int64
        )
        c2_counts = np.asarray(
            measurements["C2"]["absolute_bins"]["by_lane"][lane]["counts"], dtype=np.int64
        )
        difference = c1_counts - c2_counts
        differences[lane] = [int(value) for value in difference]
    nonzero_bins = sorted(
        index
        for lane in LANE_ORDER
        for index, value in enumerate(differences[lane])
        if value != 0
    )
    if nonzero_bins:
        endpoint_confined = all(index >= 8 for index in nonzero_bins)

    silent_center = any(
        measurements[condition_id]["center_state_relative"]["counts"] == [[0] * 3] * 4
        for condition_id in ("C1", "C2", "K_C")
    )

    outside_dominates = False
    outside_details = {}
    for condition_id in ("C1", "C2"):
        center_spikes = window_counts(
            raw_runs[condition_id]["times"],
            raw_runs[condition_id]["indices"],
            groups["center"],
            200.0,
            350.0,
        )
        stimulated_all = np.concatenate([groups[lane] for lane in LANE_ORDER])
        times = raw_runs[condition_id]["times"]
        indices = raw_runs[condition_id]["indices"]
        outside_spikes = int(
            np.count_nonzero(
                (~np.isin(indices, stimulated_all))
                & (times >= 200.0)
                & (times < 350.0)
            )
        )
        outside_details[condition_id] = {
            "center_group_spikes": center_spikes,
            "outside_spikes": outside_spikes,
        }
        if outside_spikes > center_spikes:
            outside_dominates = True

    return {
        "seed": int(next(iter(raw_runs.values()))["seed"]),
        "conditions": measurements,
        "primary": primary,
        "dwell_replication": dwell,
        "auxiliary": auxiliary,
        "delta_l": {"value_hz": delta_l, "per_bin_hz": delta_l_bins},
        "delta_r": {"value_hz": delta_r, "per_bin_hz": delta_r_bins},
        "route_adjusted": delta_adj,
        "references": {
            "r200": {
                "values_hz": r200_primary_values,
                "pred_left": r200_left,
                "pred_right": r200_right,
                "no_predecessor": r200_none,
                "separated": separated_200,
                "degenerate": r200_degenerate,
            },
            "r150": {
                "values_hz": r150_primary_values,
                "pred_left": r150_left,
                "pred_right": r150_right,
                "no_predecessor": r150_none,
                "separated": separated_150,
                "degenerate": r150_degenerate,
            },
        },
        "predicates": {
            "separated_200": separated_200,
            "separated_150": separated_150,
            "focal_200": bool(focal_200),
            "focal_150": bool(focal_150),
            "dwell_consistency": bool(dwell_consistency),
            "transition_onset_only_seed": bool(transition_onset),
            "transition_onset_side": side,
            "endpoint_confined": bool(endpoint_confined),
            "endpoint_bin_differences": differences,
            "silent_center": bool(silent_center),
            "outside_dominates": bool(outside_dominates),
            "outside_details": outside_details,
            "reference_degenerate": bool(r200_degenerate or r150_degenerate),
        },
        "routes": routes,
        "stationarity": stationarity,
        "reverse_time": reverse_time,
        "per_lane_trajectories": {
            condition_id: measurements[condition_id]["absolute_bins"]["by_lane"]
            for condition_id in cfg["references"]["r200"]["all_condition_ids"]
            + cfg["references"]["r150"]["all_condition_ids"]
            + ["K_C"]
        },
    }


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------


def _gate(passed: bool, detail) -> dict:
    return {"passed": bool(passed), "detail": detail}


def static_gates(cfg: dict, mapping, groups, graph, prereg_hashes: dict) -> dict:
    population = mapping.populations["player_lane"]
    order_ok = [name for name, _, _ in population.plan.groups] == list(LANE_ORDER)
    disjoint = int(np.unique(np.concatenate([groups[name] for name in LANE_ORDER])).size) == 12
    in_pools = True
    pool_detail = {}
    for name, pool, _ in population.plan.groups:
        mask = mapping.pools[pool].mask(graph)
        inside = bool(np.all(mask[groups[name]]))
        pool_detail[name] = {"pool": pool, "inside": inside}
        in_pools = in_pools and inside

    c1 = conditions_by_id(cfg)["C1"]["sequence"]
    c2 = conditions_by_id(cfg)["C2"]["sequence"]
    c3 = conditions_by_id(cfg)["C3"]["sequence"]
    c4 = conditions_by_id(cfg)["C4"]["sequence"]
    reversal_ok = (
        sequence_reverse(c1) == c2
        and sequence_reverse(c3) == c4
        and sequence_hash(c1) != sequence_hash(c2)
        and sequence_hash(c3) != sequence_hash(c4)
        and sorted(c1) == sorted(c2)
        and sorted(c3) == sorted(c4)
    )
    bins = absolute_bin_edges(cfg)
    bins_ok = (
        len(bins) == 13
        and bins[0] == 0.0
        and bins[-1] == 600.0
        and bool(np.all(np.diff(bins) == 50.0))
    )
    protected = protected_hashes()
    return {
        "E6": _gate(order_ok, {"lane_group_order": [name for name, _, _ in population.plan.groups]}),
        "E7": _gate(
            disjoint and in_pools,
            {
                "disjoint_total_12": disjoint,
                "groups": {
                    name: {
                        "indices": _array_to_list(groups[name]),
                        "root_ids": [int(value) for value in population.root_ids[name]],
                        "size": int(groups[name].size),
                    }
                    for name in LANE_ORDER
                },
                "pools": pool_detail,
            },
        ),
        "E8": _gate(
            reversal_ok,
            {
                "C2_reverse_C1": sequence_reverse(c1) == c2,
                "C4_reverse_C3": sequence_reverse(c3) == c4,
                "C1_sha256": sequence_hash(c1),
                "C2_sha256": sequence_hash(c2),
                "C3_sha256": sequence_hash(c3),
                "C4_sha256": sequence_hash(c4),
                "C1_multiset": sorted(c1),
                "C2_multiset": sorted(c2),
                "C3_multiset": sorted(c3),
                "C4_multiset": sorted(c4),
            },
        ),
        "E13": _gate(
            bool(prereg_hashes["preregistration"]["actual"]
                 == EXPECTED["prereg_sha256"])
            and bool(prereg_hashes["amendment_record"]["actual"]
                     == EXPECTED["amendment_sha256"])
            and all(
                item["expected"] == item["actual"]
                for item in protected.values()
            ),
            {
                "preregistration": prereg_hashes["preregistration"],
                "amendment_record": prereg_hashes["amendment_record"],
                "protected": protected,
                "source_hashes": source_hashes(),
            },
        ),
        "E15": _gate(
            bins_ok,
            {
                "edges_ms": [float(value) for value in bins],
                "half_open": True,
                "tail_ms": [float(value) for value in cfg["analysis"]["tail_ms"]],
            },
        ),
    }


def condition_gates(condition: dict, audit: dict, groups) -> dict:
    if condition["mode"] == "none":
        return {
            "E2": _gate(
                audit["stimulated_set_size"] == 0
                and audit["outside_nonzero_entries"] == 0,
                {"no_schedule": True, "stimulated_set_size": 0},
            ),
            "E3": _gate(True, {"no_schedule": True}),
            "E4": _gate(True, {"no_schedule": True}),
        }
    e2 = (
        audit["stimulated_set_size"] == EXPECTED["stimulated_set_size"]
        and audit["stimulated_set_ok"]
        and audit["nonzero_counts_ok"]
    )
    e3 = audit["total_current_ok"]
    if condition["group"] == "constant":
        lane = condition["sequence"][0]
        lane_name = LANE_LETTERS[lane]
        e4 = constant_group_ok(audit, groups, lane_name)
        e4_detail = {
            "lane": lane_name,
            "expected_indices": sorted(int(value) for value in groups[lane_name]),
            "active_indices": audit["active_indices"],
        }
    else:
        e4 = True
        e4_detail = {"not_a_constant": True}
    return {
        "E2": _gate(e2, audit),
        "E3": _gate(e3, {
            "min_pa": audit["total_current_min_pa"],
            "max_pa": audit["total_current_max_pa"],
            "expected_pa": audit["expected_total_pa"],
            "tolerance_pa": audit["total_current_tolerance_pa"],
        }),
        "E4": _gate(e4, e4_detail),
    }


def _window_spikes(raw: dict, end_ms: float) -> tuple[np.ndarray, np.ndarray]:
    mask = raw["times"] < float(end_ms)
    return raw["times"][mask], raw["indices"][mask]


def prefix_identical(first: dict, second: dict, end_ms: float) -> bool:
    times_a, indices_a = _window_spikes(first, end_ms)
    times_b, indices_b = _window_spikes(second, end_ms)
    return bool(
        np.array_equal(times_a, times_b) and np.array_equal(indices_a, indices_b)
    )


def e14_reported(measurements: dict) -> bool:
    required = {"spikes", "active_neurons", "fraction"}
    return bool(measurements) and all(
        isinstance(measurement.get("outside"), dict)
        and required <= set(measurement["outside"])
        for measurement in measurements.values()
    )


def run_gates(
    cfg: dict,
    seed: int,
    raw_runs: dict,
    condition_gate_map: dict,
    static: dict,
    determinism: dict,
    execution_context: dict,
    measurements: dict,
) -> dict:
    conditions = conditions_by_id(cfg)
    e1 = len(raw_runs) == EXPECTED["distinct_runs_per_seed"] and all(
        raw_runs[condition_id].get("completed", False)
        for condition_id in conditions
    )
    e2 = all(condition_gate_map[condition_id]["E2"]["passed"] for condition_id in conditions)
    e3 = all(condition_gate_map[condition_id]["E3"]["passed"] for condition_id in conditions)
    e4 = all(condition_gate_map[condition_id]["E4"]["passed"] for condition_id in conditions)
    n0 = raw_runs.get("N0")
    e5 = bool(
        n0 is not None
        and n0["schedule_digest"] == _sha256_bytes(b"no-input-schedule")
        and n0["n_spikes"] == 0
        and n0["stimulus"] is None
        and n0["background_current_pa"] == 0.0
        and n0["noise_std_pa"] == 0.0
    )
    e9 = prefix_identical(raw_runs["C3"], raw_runs["C4"], 150.0)
    if determinism:
        e10 = all(item["identical"] for item in determinism.values())
        e10_detail = determinism
    elif execution_context.get("campaign") == "pilot":
        e10 = True
        e10_detail = {"not_applicable_for_pilot": True}
    else:
        e10 = False
        e10_detail = {"missing_determinism_repeats": True}
    e12 = bool(execution_context.get("existing_tests_passed", False))
    e14 = e14_reported(measurements)
    e16_c1 = prefix_identical(raw_runs["C1"], raw_runs["T200_LC"], 400.0)
    e16_c2 = prefix_identical(raw_runs["C2"], raw_runs["T200_RC"], 400.0)
    gates = {
        "E1": _gate(e1, {"n_conditions": len(raw_runs)}),
        "E2": _gate(e2, {"all_conditions": e2}),
        "E3": _gate(e3, {"all_conditions": e3}),
        "E4": _gate(e4, {"all_conditions": e4}),
        "E5": _gate(
            e5,
            {
                "input_schedule_none": n0 is not None and n0["schedule_digest"] == _sha256_bytes(b"no-input-schedule"),
                "stimulus_none": n0 is not None and n0["stimulus"] is None,
                "n_spikes": None if n0 is None else n0["n_spikes"],
            },
        ),
        "E6": static["E6"],
        "E7": static["E7"],
        "E8": static["E8"],
        "E9": _gate(e9, {"window_ms": [0.0, 150.0]}),
        "E10": _gate(e10, e10_detail),
        "E12": _gate(e12, {"existing_tests_passed_declared": e12}),
        "E13": static["E13"],
        "E14": _gate(
            e14,
            {
                "outside_activity_reported_separately": e14,
                "n_conditions": len(measurements),
            },
        ),
        "E15": static["E15"],
        "E16": _gate(
            e16_c1 and e16_c2,
            {"C1_equals_T200_LC_before_400_ms": e16_c1, "C2_equals_T200_RC_before_400_ms": e16_c2},
        ),
    }
    failed = [gate_id for gate_id, gate in gates.items() if not gate["passed"]]
    return {"seed": int(seed), "gates": gates, "failed": failed, "passed": not failed}


# --------------------------------------------------------------------------
# outcome classification (descriptive, 2-of-3)
# --------------------------------------------------------------------------


def replicated_sign(values, required: int = 2) -> int:
    signs = [sign_of(float(value)) for value in values if value is not None]
    positives = sum(1 for value in signs if value > 0)
    negatives = sum(1 for value in signs if value < 0)
    if positives >= required and negatives == 0:
        return 1
    if negatives >= required and positives == 0:
        return -1
    if positives >= required:
        return 1
    if negatives >= required:
        return -1
    return 0


def replicated_direction(values, required: int = 2) -> str | None:
    values = [value for value in values if value is not None]
    for direction in ("pred_left_above_pred_right", "pred_right_above_pred_left"):
        if values.count(direction) >= required:
            return direction
    return None


def classify_campaign(seed_analyses: dict, gates_by_seed: dict, cfg: dict) -> dict:
    required = int(cfg["decision"]["replication_required_seeds"])
    seeds = sorted(seed_analyses)
    p1_values = [seed_analyses[seed]["primary"]["value_hz"] for seed in seeds]
    p2_values = [seed_analyses[seed]["dwell_replication"]["value_hz"] for seed in seeds]
    p1_sign = replicated_sign(p1_values, required)
    p2_sign = replicated_sign(p2_values, required)
    sep200_direction = replicated_direction(
        [seed_analyses[seed]["predicates"]["separated_200"] for seed in seeds],
        required,
    )
    sep150_direction = replicated_direction(
        [seed_analyses[seed]["predicates"]["separated_150"] for seed in seeds],
        required,
    )
    focal200 = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["focal_200"]
    ) >= required
    focal150 = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["focal_150"]
    ) >= required
    dwell_consistent = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["dwell_consistency"]
    ) >= required
    p1_core = bool(p1_sign != 0 and sep200_direction is not None and focal200)
    p1_pass = bool(p1_core and dwell_consistent)

    any_gate_failure = any(gates_by_seed[seed]["failed"] for seed in seeds)
    silent = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["silent_center"]
    ) >= required
    outside = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["outside_dominates"]
    ) >= required
    degenerate = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["reference_degenerate"]
    ) >= required
    transition_onset = sum(
        1 for seed in seeds
        if seed_analyses[seed]["predicates"]["transition_onset_only_seed"]
    ) >= required
    endpoint = sum(
        1 for seed in seeds if seed_analyses[seed]["predicates"]["endpoint_confined"]
    ) >= required

    delta_r_sign = replicated_sign(
        [seed_analyses[seed]["delta_r"]["value_hz"] for seed in seeds], required
    )
    route_ids = sorted(seed_analyses[seeds[0]]["routes"])
    route_signs = {
        route_id: replicated_sign(
            [seed_analyses[seed]["routes"][route_id]["value_hz"] for seed in seeds],
            required,
        )
        for route_id in route_ids
    }
    route_consistent = bool(
        delta_r_sign != 0 or any(sign != 0 for sign in route_signs.values())
    )

    checks = {
        "INVALID_EXECUTION": any_gate_failure,
        "INCONCLUSIVE_SILENT_C": silent,
        "INCONCLUSIVE_OUTSIDE": outside,
        "INCONCLUSIVE_REFERENCE_DEGENERATE": degenerate,
        "HISTORY_EFFECT_PRESENT": p1_pass,
        "HISTORY_EFFECT_DWELL_DEPENDENT": bool(p1_core and not dwell_consistent),
        "NEGATIVE_PRIMARY_DWELL_DEPENDENT": bool(not p1_pass and p2_sign != 0),
        "TRANSITION_ONSET_ONLY": bool(not p1_pass and transition_onset),
        "ROUTE_ONLY": bool(not p1_pass and route_consistent),
        "ENDPOINT_EXPLAINED": bool(not p1_pass and endpoint),
        "NO_HISTORY_EFFECT": bool(not p1_pass),
    }
    trace = []
    outcome = None
    for order, name in enumerate(cfg["decision"]["outcome_order"], start=1):
        triggered = bool(checks[name])
        trace.append({"order": order, "outcome": name, "triggered": triggered})
        if triggered and outcome is None:
            outcome = name
    if outcome is None:
        outcome = "NO_HISTORY_EFFECT"

    return {
        "outcome": outcome,
        "trace": trace,
        "basis": {
            "p1_values_hz": p1_values,
            "p2_values_hz": p2_values,
            "p1_sign_replication": p1_sign,
            "p2_sign_replication": p2_sign,
            "separated_200_direction": sep200_direction,
            "separated_150_direction": sep150_direction,
            "focal_200_seeds": int(focal200),
            "focal_150_seeds": int(focal150),
            "dwell_consistency_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["dwell_consistency"]
            ),
            "p1_core": p1_core,
            "p1_pass": p1_pass,
            "any_gate_failure": any_gate_failure,
            "silent_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["silent_center"]
            ),
            "outside_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["outside_dominates"]
            ),
            "degenerate_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["reference_degenerate"]
            ),
            "transition_onset_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["transition_onset_only_seed"]
            ),
            "endpoint_seeds": sum(
                1 for seed in seeds if seed_analyses[seed]["predicates"]["endpoint_confined"]
            ),
            "delta_r_sign": delta_r_sign,
            "route_signs": route_signs,
        },
        "inference": "descriptive_only",
        "significance_claim": False,
    }


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------


def _require_execution_authorisation(
    acknowledged: bool, campaign: str | None, existing_tests_passed: bool
) -> dict:
    cfg = load_protocol()
    if campaign not in EXECUTION_CAMPAIGNS:
        raise ExecutionNotAuthorised(
            "execution requires --campaign one of " + ", ".join(EXECUTION_CAMPAIGNS)
        )
    if not acknowledged:
        raise ExecutionNotAuthorised(
            "execution requires --acknowledge-execution-authorised; "
            "implementation alone does not authorise execution"
        )
    if campaign in ("main", "pilot") and not existing_tests_passed:
        raise ExecutionNotAuthorised(
            "E12 requires --existing-tests-passed before a main or pilot campaign"
        )
    hashes = assert_prereg_hashes(cfg)
    return {"config": cfg, "hashes": hashes, "campaign": campaign}


def _load_graph():
    settings = load_yaml(SIMULATION_CONFIG)
    return load_connectome(PROJECT_ROOT / settings["connectome"]["path"])


def _params():
    neuron = LIFParameters.from_config(load_yaml(NEURON_CONFIG)["neuron"])
    synapse = SynapseParameters.from_config(
        load_yaml(SIMULATION_CONFIG)["synapse"]
    )
    return neuron, synapse


def _run_single(
    graph,
    mapping,
    base_config: dict,
    cfg: dict,
    seed: int,
    condition: dict,
    neuron_params,
    synapse_params,
) -> dict:
    setup = build_setup(mapping, base_config)
    scheduler = build_scheduler(setup, condition, cfg)
    audit = audit_input_current(scheduler, condition, mapping, cfg)
    simulator = BrainSimulator(
        graph,
        neuron_params,
        synapse_params,
        dt_ms=float(cfg["protocol"]["dt_ms"]),
        duration_ms=float(cfg["protocol"]["duration_ms"]),
        seed=int(cfg["protocol"]["simulator_seed"]),
        background_current_pa=0.0,
        noise_std_pa=0.0,
        stimulus=None,
        input_schedule=scheduler,
        max_recorded_spikes=int(cfg["protocol"]["max_recorded_spikes"]),
        progress_interval_ms=0.0,
        diagnostics_interval_steps=200,
    )
    if simulator.stimulus is not None:
        raise RuntimeError("Phase 2 stimulus must be disabled")
    started = time.perf_counter()
    result = simulator.run(progress=False)
    wall = time.perf_counter() - started
    times = np.array(result.recorder.spike_times_ms, dtype=np.float64)
    indices = np.array(result.recorder.spike_neuron_indices, dtype=np.int64)
    digest = hashlib.sha256()
    digest.update(times.tobytes())
    digest.update(indices.tobytes())
    payload = {
        "condition_id": condition["id"],
        "seed": int(seed),
        "times": times,
        "indices": indices,
        "n_spikes": int(times.size),
        "n_steps": int(result.n_steps),
        "duration_ms": float(result.duration_ms),
        "stimulated_indices": (
            np.array([], dtype=np.int64)
            if scheduler is None
            else np.asarray(scheduler.stimulated_indices, dtype=np.int64)
        ),
        "input_audit": audit,
        "schedule_digest": schedule_signature_hash(scheduler),
        "spike_digest": digest.hexdigest(),
        "stimulus": simulator.stimulus,
        "background_current_pa": simulator.background_current_pa,
        "noise_std_pa": simulator.noise_std_pa,
        "wall_runtime_s": wall,
        "completed": True,
    }
    del simulator, setup, scheduler
    gc.collect()
    return payload


def _single_request_payload(cfg: dict, seed: int, condition_id: str) -> dict:
    return {
        "phase": cfg["phase"],
        "version": cfg["version"],
        "seed": int(seed),
        "condition_id": condition_id,
        "config_sha256": sha256(CONFIG_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
    }


def run_execute_single(
    request_path: Path, response_path: Path, acknowledged: bool = False
) -> dict:
    if not acknowledged:
        raise ExecutionNotAuthorised(
            "single-run execution requires --acknowledge-execution-authorised"
        )
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    cfg = load_protocol()
    assert_prereg_hashes(cfg)
    if request["config_sha256"] != sha256(CONFIG_PATH):
        raise ValueError("single-run request config hash mismatch")
    by_id = conditions_by_id(cfg)
    condition = by_id[request["condition_id"]]
    graph = _load_graph()
    base_config = build_base_sensory_config()
    mapping, _ = build_mapping(graph, base_config, int(request["seed"]))
    neuron_params, synapse_params = _params()
    raw = _run_single(
        graph, mapping, base_config, cfg, int(request["seed"]), condition,
        neuron_params, synapse_params,
    )
    response = {
        "seed": int(request["seed"]),
        "condition_id": condition["id"],
        "spike_digest": raw["spike_digest"],
        "schedule_digest": raw["schedule_digest"],
        "n_spikes": raw["n_spikes"],
        "wall_runtime_s": raw["wall_runtime_s"],
    }
    Path(response_path).write_text(json.dumps(response, indent=1), encoding="utf-8")
    return response


def determinism_repeats(
    cfg: dict, seed: int, parents: dict, authorization_acknowledged: bool
) -> dict:
    if not authorization_acknowledged:
        raise ExecutionNotAuthorised(
            "determinism repeats require --acknowledge-execution-authorised"
        )
    results = {}
    with tempfile.TemporaryDirectory(prefix="p3_3c5_det_") as directory:
        directory = Path(directory)
        for condition_id in cfg["determinism"]["set"]:
            request_path = directory / f"{condition_id}_request.json"
            response_path = directory / f"{condition_id}_response.json"
            request_path.write_text(
                json.dumps(_single_request_payload(cfg, seed, condition_id), indent=1),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(Path(__file__)),
                "--execute-single",
                str(request_path),
                str(response_path),
                "--acknowledge-execution-authorised",
            ]
            completed = subprocess.run(
                command, cwd=PROJECT_ROOT, capture_output=True, text=True
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"determinism subprocess failed for {condition_id}: "
                    f"{completed.stderr.strip()}"
                )
            response = json.loads(response_path.read_text(encoding="utf-8"))
            parent = parents[condition_id]
            results[condition_id] = {
                "seed": int(seed),
                "parent_spike_digest": parent["spike_digest"],
                "repeat_spike_digest": response["spike_digest"],
                "parent_schedule_digest": parent["schedule_digest"],
                "repeat_schedule_digest": response["schedule_digest"],
                "identical": bool(
                    parent["spike_digest"] == response["spike_digest"]
                    and parent["schedule_digest"] == response["schedule_digest"]
                ),
                "parent_n_spikes": parent["n_spikes"],
                "repeat_n_spikes": response["n_spikes"],
            }
    return results


def _spike_artifact_arrays(raw_runs: dict, seed: int, store: dict) -> None:
    for condition_id, raw in raw_runs.items():
        key = f"{seed}__{condition_id}"
        store[f"{key}__times_ms"] = raw["times"]
        store[f"{key}__neuron_indices"] = raw["indices"]


def _resolve_output(base: Path) -> tuple[Path, str | None]:
    if not base.exists():
        return base, None
    index = 2
    while True:
        candidate = base.with_name(f"{base.stem}.v{index}{base.suffix}")
        if not candidate.exists():
            return candidate, f"supersedes {base.name}"
        index += 1


def _run_determinism_campaign(
    cfg: dict,
    context: dict,
    acknowledged: bool,
    write: bool,
) -> dict:
    """Re-run the 18 determinism instances against an existing main artifact.

    The main campaign already executes the 18 fresh-subprocess repeats (E10).
    This separate campaign is a verification re-run: it needs the parent
    digests from the main result and never creates new main or pilot data.
    """
    if not JSON_PATH.exists():
        try:
            location = JSON_PATH.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            location = str(JSON_PATH)
        raise FileNotFoundError(
            "a determinism campaign needs an existing main result at "
            f"{location}; it cannot create parent runs"
        )
    main_payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if main_payload.get("campaign") != "main":
        raise ValueError("the determinism parent artifact is not a main result")
    started = time.perf_counter()
    git_before = git_state()
    results = {}
    for seed in cfg["seeds"]["main"]:
        parents = main_payload["runs"][str(seed)]
        results[str(seed)] = determinism_repeats(cfg, int(seed), parents, acknowledged)
    identical = all(
        item["identical"]
        for seed_block in results.values()
        for item in seed_block.values()
    )
    git_after = git_state()
    payload = {
        "phase": cfg["phase"],
        "version": cfg["version"],
        "campaign": "determinism",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_s": round(time.perf_counter() - started, 4),
        "parent_result": JSON_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "config_sha256": sha256(CONFIG_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "amendment_record_sha256": sha256(AMENDMENT_PATH),
        "source_hashes": source_hashes(),
        "protected_hashes": protected_hashes(),
        "git": {
            "before": git_before,
            "after": git_after,
            "unchanged": git_state_stable(git_before, git_after),
        },
        "environment": environment_info(),
        "conditions": list(cfg["determinism"]["set"]),
        "seeds": list(cfg["seeds"]["main"]),
        "results": results,
        "n_instances": sum(len(block) for block in results.values()),
        "E10": _gate(
            identical,
            {
                "parent_and_repeat_identical": identical,
                "n_instances": sum(len(block) for block in results.values()),
            },
        ),
        "limitations": list(LIMITATIONS),
    }
    if payload["n_instances"] != EXPECTED["determinism_instances"]:
        payload["E10"] = _gate(
            False,
            {
                "expected_instances": EXPECTED["determinism_instances"],
                "observed_instances": payload["n_instances"],
            },
        )
    if write:
        paths = campaign_paths("determinism")
        json_path, supersession = _resolve_output(paths["json"])
        if supersession:
            payload["supersession_note"] = supersession
        if json_path != paths["json"]:
            sidecar_path = json_path.with_name(json_path.stem + ".sidecar.json")
        else:
            sidecar_path = paths["sidecar"]
        json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        sidecar_path.write_text(
            json.dumps(
                {
                    "output": json_path.name,
                    "output_sha256": sha256(json_path),
                    "campaign": "determinism",
                    "E10_passed": payload["E10"]["passed"],
                    "parent_result": payload["parent_result"],
                    "config_sha256": sha256(CONFIG_PATH),
                    "preregistration_sha256": sha256(PREREG_PATH),
                    "git": payload["git"],
                    "environment": payload["environment"],
                },
                indent=1,
            ),
            encoding="utf-8",
        )
    return payload


def run_campaign(
    campaign: str,
    acknowledged: bool,
    existing_tests_passed: bool,
    write: bool = True,
) -> dict:
    context = _require_execution_authorisation(
        acknowledged, campaign, existing_tests_passed
    )
    cfg = context["config"]
    if campaign == "determinism":
        return _run_determinism_campaign(cfg, context, acknowledged, write)
    started = time.perf_counter()
    git_before = git_state()
    graph = _load_graph()
    base_config = build_base_sensory_config()
    neuron_params, synapse_params = _params()
    by_id = conditions_by_id(cfg)
    seeds = (
        [cfg["seeds"]["pilot"]]
        if campaign == "pilot"
        else list(cfg["seeds"]["main"])
    )
    store: dict[str, np.ndarray] = {}
    runs_payload = {}
    analyses = {}
    gates_by_seed = {}
    determinism_by_seed = {}
    mappings = {}

    for seed in seeds:
        mapping, _ = build_mapping(graph, base_config, seed)
        groups = lane_groups(mapping)
        mappings[str(seed)] = {
            "mapping_sha256": mapping_signature(mapping),
            "groups": {
                lane: {
                    "indices": _array_to_list(groups[lane]),
                    "root_ids": lane_root_ids(mapping)[lane],
                }
                for lane in LANE_ORDER
            },
        }
        raw_runs = {}
        condition_gate_map = {}
        for condition in cfg["conditions"]:
            raw = _run_single(
                graph, mapping, base_config, cfg, seed, condition,
                neuron_params, synapse_params,
            )
            raw_runs[condition["id"]] = raw
            setup = build_setup(mapping, base_config)
            scheduler = build_scheduler(setup, condition, cfg)
            audit = audit_input_current(scheduler, condition, mapping, cfg)
            condition_gate_map[condition["id"]] = condition_gates(
                condition, audit, groups
            )
            del setup, scheduler
        determinism = {}
        if campaign == "main":
            determinism = determinism_repeats(
                cfg, seed, raw_runs, acknowledged
            )
        determinism_by_seed[str(seed)] = determinism
        static = static_gates(
            cfg, mapping, groups, graph, context["hashes"]
        )
        runs_payload[str(seed)] = {
            condition_id: measure_condition(raw, by_id[condition_id], groups, cfg)
            for condition_id, raw in raw_runs.items()
        }
        gate_summary = run_gates(
            cfg, seed, raw_runs, condition_gate_map, static, determinism,
            {
                "existing_tests_passed": existing_tests_passed,
                "campaign": campaign,
            },
            runs_payload[str(seed)],
        )
        gates_by_seed[str(seed)] = gate_summary
        if campaign != "pilot":
            analysis = analyse_seed(raw_runs, cfg, groups)
            analysis["gate_failures"] = gate_summary["failed"]
            analyses[str(seed)] = analysis
        _spike_artifact_arrays(raw_runs, seed, store)
        del raw_runs, groups, mapping
        gc.collect()

    classification = (
        classify_campaign(analyses, gates_by_seed, cfg)
        if analyses
        else None
    )
    git_after = git_state()
    e13_post = git_state_stable(git_before, git_after)
    if not e13_post:
        for seed_block in gates_by_seed.values():
            seed_block["gates"]["E13"] = _gate(
                False,
                {"git_before": git_before, "git_after": git_after},
            )
            if "E13" not in seed_block["failed"]:
                seed_block["failed"].append("E13")
            seed_block["passed"] = not seed_block["failed"]

    payload = {
        "phase": cfg["phase"],
        "version": cfg["version"],
        "campaign": campaign,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_s": round(time.perf_counter() - started, 4),
        "config_sha256": sha256(CONFIG_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "amendment_record_sha256": sha256(AMENDMENT_PATH),
        "source_hashes": source_hashes(),
        "protected_hashes": protected_hashes(),
        "git": {"before": git_before, "after": git_after, "unchanged": e13_post},
        "environment": environment_info(),
        "protocol": cfg,
        "mappings": mappings,
        "runs": runs_payload,
        "determinism": determinism_by_seed,
        "gates": gates_by_seed,
        "analysis": analyses,
        "campaign_outcome": classification,
        "pilot": (
            {
                "seed": cfg["seeds"]["pilot"],
                "checks": cfg["pilot_checks"],
                "gate_failures": gates_by_seed[str(cfg["seeds"]["pilot"])]["failed"],
                "enters_main_result": False,
            }
            if campaign == "pilot"
            else None
        ),
        "deviations": [],
        "limitations": list(LIMITATIONS),
        "artifacts": {
            "config": "configs/p3_3c5_lane_encoding.yaml",
            "preregistration": "docs/P3_3C5_LANE_ENCODING_PREREGISTRATION.md",
            "amendment_record": "docs/P3_3C5_PROTOCOL_AMENDMENT_RECORD.md",
            "result": campaign_paths(campaign)["json"].relative_to(
                PROJECT_ROOT
            ).as_posix(),
            "sidecar": campaign_paths(campaign)["sidecar"].relative_to(
                PROJECT_ROOT
            ).as_posix(),
            "report": campaign_paths(campaign)["report"].relative_to(
                PROJECT_ROOT
            ).as_posix(),
            "spike_times": campaign_paths(campaign)["spikes"].relative_to(
                PROJECT_ROOT
            ).as_posix(),
            "runner": "experiments/phase_3c/p3_3c5_lane_encoding.py",
            "tests": "tests/test_p3_3c5_lane_encoding.py",
        },
    }

    if write:
        paths = campaign_paths(campaign)
        json_path, supersession = _resolve_output(paths["json"])
        if json_path == paths["json"]:
            spikes_path = paths["spikes"]
            sidecar_path = paths["sidecar"]
            report_path = paths["report"]
        else:
            spikes_path = json_path.with_name(json_path.stem + "_spikes.npz")
            sidecar_path = json_path.with_name(json_path.stem + ".sidecar.json")
            report_path = json_path.with_name(json_path.stem + "_report.md")
        np.savez_compressed(spikes_path, **store)
        if supersession:
            payload["supersession_note"] = supersession
        json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        sidecar = {
            "output": json_path.name,
            "output_sha256": sha256(json_path),
            "phase": cfg["phase"],
            "version": cfg["version"],
            "campaign": campaign,
            "outcome": None if classification is None else classification["outcome"],
            "config_sha256": sha256(CONFIG_PATH),
            "preregistration_sha256": sha256(PREREG_PATH),
            "amendment_record_sha256": sha256(AMENDMENT_PATH),
            "source_hashes": payload["source_hashes"],
            "protected_hashes": payload["protected_hashes"],
            "spike_times_sha256": sha256(spikes_path),
            "git": payload["git"],
            "environment": payload["environment"],
        }
        sidecar_path.write_text(json.dumps(sidecar, indent=1), encoding="utf-8")
        report_path.write_text(render_report(payload), encoding="utf-8")
    del graph
    gc.collect()
    return payload


def _primary_per_neuron_lines(analysis: dict) -> list:
    lines = [
        "Per-neuron delta:",
        "",
        "| Neuron pin | s=0 | s=1 | s=2 | Delta_C(i) Hz |",
        "|---|---|---|---|---|",
    ]
    rows = analysis["primary"]["per_neuron_hz"]
    means = analysis["primary"]["per_neuron_mean_hz"]
    if len(means) != len(rows):
        raise ValueError("per-neuron scalar count disagrees with per-bin rows")
    for index, row in enumerate(rows):
        lines.append(
            f"| {index} | {row[0]:.6f} | {row[1]:.6f} | {row[2]:.6f} | "
            f"{means[index]:.6f} |"
        )
    return lines


def render_report(payload: dict) -> str:
    lines = []
    add = lines.append
    add("# P3-3C.5 lane encoding report")
    add("")
    add(f"Generated: {payload['generated_at_utc']}")
    add(
        f"Repository HEAD: `{payload['git']['before']['head']}` "
        f"(branch `{payload['git']['before']['branch']}`)"
    )
    add(f"Campaign: `{payload['campaign']}` — protocol `{payload['version']}`")
    outcome = payload.get("campaign_outcome")
    add(
        "Outcome: **"
        + ("PILOT ONLY" if outcome is None else outcome["outcome"])
        + "**"
    )
    add("")
    add("## 1. What the outcome does and does not mean")
    add("")
    add(
        "The outcome is a descriptive classification of a deterministic "
        "simulation under the configured model. It is not a significance test, "
        "not a biological claim and not a claim about a neural code."
    )
    add("")
    add("## 2. Per-seed primary values")
    add("")
    add("| Seed | P1 (C1-C2) Hz | P2 (C3-C4) Hz | K_C Hz |")
    add("|---|---|---|---|")
    for seed, analysis in sorted(payload.get("analysis", {}).items()):
        add(
            f"| {seed} | {analysis['primary']['value_hz']:.6f} | "
            f"{analysis['dwell_replication']['value_hz']:.6f} | "
            f"{analysis['auxiliary']['K_C']['value_hz']:.6f} |"
        )
    add("")
    add("## 3. Primary per-bin and per-neuron values")
    add("")
    for seed, analysis in sorted(payload.get("analysis", {}).items()):
        add(f"### Seed {seed}")
        add("")
        add(
            "Per-bin delta: "
            + str([round(value, 6) for value in analysis["primary"]["per_bin_hz"]])
        )
        add("")
        for line in _primary_per_neuron_lines(analysis):
            add(line)
        add("")
    add("## 4. Reference values and predicates")
    add("")
    add("| Seed | R200 pred-LEFT | R200 pred-RIGHT | SEPARATED_200 | R150 pred-LEFT range | R150 pred-RIGHT range | SEPARATED_150 |")
    add("|---|---|---|---|---|---|---|")
    for seed, analysis in sorted(payload.get("analysis", {}).items()):
        refs = analysis["references"]
        add(
            f"| {seed} | {refs['r200']['pred_left']:.6f} | "
            f"{refs['r200']['pred_right']:.6f} | {refs['r200']['separated']} | "
            f"{_range(refs['r150']['pred_left'])} | "
            f"{_range(refs['r150']['pred_right'])} | "
            f"{refs['r150']['separated']} |"
        )
    add("")
    add("## 5. Activity, outside fraction and current audit")
    add("")
    add(
        "| Seed | Gate failures | Outside fraction range | "
        "Active neurons per group/bin | Current min/max pA |"
    )
    add("|---|---|---|---|---|")
    for seed, analysis in sorted(payload.get("analysis", {}).items()):
        fractions = [
            measurement["outside"]["fraction"]
            for measurement in analysis["conditions"].values()
        ]
        audits = [
            measurement["current_audit"]
            for measurement in analysis["conditions"].values()
        ]
        active_counts = [
            count
            for measurement in analysis["conditions"].values()
            for lane_counts in measurement["absolute_bins"][
                "active_neurons_by_lane"
            ].values()
            for count in lane_counts
        ]
        add(
            f"| {seed} | {analysis['gate_failures']} | "
            f"{min(fractions):.6f} to {max(fractions):.6f} | "
            f"{min(active_counts)} to {max(active_counts)} | "
            f"{min(item['total_current_min_pa'] for item in audits)} / "
            f"{max(item['total_current_max_pa'] for item in audits)} |"
        )
    add("")
    add("## 6. Gate results")
    add("")
    for seed, block in sorted(payload.get("gates", {}).items()):
        add(f"- Seed {seed}: failed gates {block['failed']}")
    add("")
    add("## 7. Limitations")
    add("")
    for item in payload["limitations"]:
        add(f"- {item}")
    add("")
    add("## 8. Claims not made")
    add("")
    add(
        "No p-value, significance claim, confidence interval, biological claim, "
        "learning claim, code claim or generalisation is made. A 2-of-3 "
        "pattern is written as '2 of 3 mapping realisations'. Descriptive "
        "effects are written as 'under the configured model'."
    )
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# planning and preflight (no simulation)
# --------------------------------------------------------------------------


def plan_campaign(cfg: dict, campaign: str) -> dict:
    by_id = conditions_by_id(cfg)
    if campaign == "pilot":
        seeds = [cfg["seeds"]["pilot"]]
        conditions = list(by_id)
        instances = len(seeds) * len(conditions)
        repeats = 0
        parent_required = None
    elif campaign == "determinism":
        seeds = list(cfg["seeds"]["main"])
        conditions = list(cfg["determinism"]["set"])
        instances = 0
        repeats = len(seeds) * len(conditions)
        parent_required = JSON_PATH.relative_to(PROJECT_ROOT).as_posix()
    else:
        seeds = list(cfg["seeds"]["main"])
        conditions = list(by_id)
        instances = len(seeds) * len(conditions)
        repeats = len(seeds) * len(cfg["determinism"]["set"])
        parent_required = None
    return {
        "campaign": campaign,
        "seeds": seeds,
        "n_conditions": len(conditions),
        "conditions": conditions,
        "distinct_instances": instances,
        "determinism_repeat_instances": repeats,
        "fresh_subprocess_repeats": repeats > 0,
        "parent_result_required": parent_required,
        "executed_instances_in_campaign": (
            repeats if campaign == "determinism" else instances + repeats
        ),
        "execution_authorised_by_this_call": False,
    }


def preflight_report(cfg: dict | None = None) -> dict:
    cfg = load_protocol() if cfg is None else cfg
    hashes = assert_prereg_hashes(cfg)
    graph = _load_graph()
    base_config = build_base_sensory_config()
    seed = int(cfg["seeds"]["main"][0])
    mapping, _ = build_mapping(graph, base_config, seed)
    groups = lane_groups(mapping)
    static = static_gates(cfg, mapping, groups, graph, hashes)
    condition_checks = {}
    for condition in cfg["conditions"]:
        setup = build_setup(mapping, base_config)
        scheduler = build_scheduler(setup, condition, cfg)
        audit = audit_input_current(scheduler, condition, mapping, cfg)
        condition_checks[condition["id"]] = condition_gates(condition, audit, groups)
        del setup, scheduler
    failures = [
        condition_id
        for condition_id, checks in condition_checks.items()
        if not all(check["passed"] for check in checks.values())
    ]
    static_failures = [
        gate_id for gate_id, gate in static.items() if not gate["passed"]
    ]
    payload = {
        "phase": cfg["phase"],
        "version": cfg["version"],
        "mode": "static_preflight",
        "seed": seed,
        "mapping_sha256": mapping_signature(mapping),
        "lane_groups": {
            lane: {
                "indices": _array_to_list(groups[lane]),
                "root_ids": lane_root_ids(mapping)[lane],
            }
            for lane in LANE_ORDER
        },
        "static_gates": static,
        "condition_gates": condition_checks,
        "static_failures": static_failures,
        "condition_failures": failures,
        "passed": not static_failures and not failures,
        "execution": "NOT RUN — EXECUTION NOT AUTHORISED",
        "hashes": hashes,
        "git": git_state(),
    }
    del mapping, graph
    gc.collect()
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", action="store_true",
        help="print the campaign plan (default, no simulation)",
    )
    parser.add_argument(
        "--preflight", action="store_true",
        help="run static schedule and mapping checks without simulation",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="execute a campaign; requires explicit authorisation flags",
    )
    parser.add_argument(
        "--campaign", choices=EXECUTION_CAMPAIGNS,
        help="campaign to execute",
    )
    parser.add_argument(
        "--acknowledge-execution-authorised", action="store_true",
        help="explicitly acknowledge that a separate execution authorisation exists",
    )
    parser.add_argument(
        "--existing-tests-passed", action="store_true",
        help="E12 declaration: the existing test suite passes unchanged",
    )
    parser.add_argument(
        "--execute-single", nargs=2, metavar=("REQUEST", "RESPONSE"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if args.execute_single:
        response = run_execute_single(
            Path(args.execute_single[0]),
            Path(args.execute_single[1]),
            acknowledged=args.acknowledge_execution_authorised,
        )
        print(json.dumps(response, indent=1))
        return 0
    if args.execute:
        payload = run_campaign(
            args.campaign,
            acknowledged=args.acknowledge_execution_authorised,
            existing_tests_passed=args.existing_tests_passed,
            write=True,
        )
        if payload["campaign"] == "determinism":
            summary = {
                "campaign": "determinism",
                "E10": payload["E10"],
                "result": campaign_paths("determinism")["json"].relative_to(
                    PROJECT_ROOT
                ).as_posix(),
            }
        else:
            summary = {
                "campaign": payload["campaign"],
                "outcome": (
                    None if payload["campaign_outcome"] is None
                    else payload["campaign_outcome"]["outcome"]
                ),
                "result": campaign_paths(payload["campaign"])["json"].relative_to(
                    PROJECT_ROOT
                ).as_posix(),
            }
        print(json.dumps(summary, indent=1))
        return 0
    cfg = load_protocol()
    if args.preflight:
        payload = preflight_report(cfg)
        print(json.dumps({
            "passed": payload["passed"],
            "static_failures": payload["static_failures"],
            "condition_failures": payload["condition_failures"],
            "execution": payload["execution"],
        }, indent=1))
        return 0
    print(json.dumps(plan_campaign(cfg, "main"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
