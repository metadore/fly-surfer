"""Pilot 2-C (D3, REV4 §10.8 as amended): floor-and-identity certification.

SCIENTIFIC STATUS
    Pilot 2-C certifies eight properties of the existing implementation: the
    substrate-free floor executes, A′ is an exact identity on P1–P19, Fβ is
    state-independent, F is state-dependent and frozen at evaluation, motor
    silence is reported as measured, plasticity changes are attributable, the
    provenance is complete, and every arm is viable. It tests no hypothesis,
    estimates no C1–C4, H1–H3, paired dispersion or ``sigma_max``, and selects
    no N. The report it supports may be valid but non-freeze (D3 OD-6).

    :func:`pilot2c_readiness` and :func:`evaluate_certification` are read-only.
    :func:`run_pilot2c` refuses unless every execution gate passes, and the
    stage gate itself refuses any grid other than the exact D3 scope. The
    certified-artifact requirement is real: with no trained F/Fβ artifact the
    stage is not executable, and no untrained or synthetic substitute is ever
    made.

AUTHORISATION
    The only path to execution is
    :func:`experiments.phase_8.campaign.protocol.assert_stage_authorized`
    called with the Pilot 2-C plan. D3 exempts this grid from B7 because it
    builds and reads no randomized graph; it accepts and weakens nothing.
    B2 and B3–B6 stay open and are reported, never resolved here.

    The global training gate keeps refusing every further training run. Pilot
    2-C runs no training, so that refusal is reported under
    ``training_blockers`` and is never folded into the stage's own
    ``blockers``. What the stage does require is that D5/D6 remain applicable
    (the six artifacts have a live authority) and that those six verified,
    trained artifacts load. Both are reported, and neither is inferred.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..campaign.protocol import (
    AMENDMENT_ID,
    AMENDMENT_PATH,
    OWNER_DECISION_D3_RECORD,
    PILOT2C_G3_SCOPE,
    pilot2c_applicability,
    stage_authorization,
)
from ..config import (
    PROJECT_ROOT,
    Phase8Config,
    load_phase8_config,
    memory_preflight,
)
from ..manifest import hash_inputs, load_manifest, phase8_input_paths
from ..registry import build_registry
from ..schema import SchemaError, validate_rows
from ..store import EpisodeStore
from ..training.artifacts import TRAINING_ROOT
from ..training.d5 import d5_applicability
from ..training.errors import TrainingError
from ..training.gate import training_authorization_status
from ..training.loader import (
    discover_artifact_directories,
    load_pilot_evaluation_artifacts,
)
from .common import (
    PilotPlan,
    StageConfigurationError,
    StageRefusal,
    drive_pilot,
    stage_root,
)
from .pilot2 import IDENTITY_FIELDS
from .pilot2c_runner import (
    PILOT2C_ARMS,
    PILOT2C_NEURAL_ARMS,
    PILOT2C_SEEDS,
    PILOT2C_STAGE,
    PILOT2C_STAGE_PURPOSE,
    Pilot2CEpisodeRunner,
)

PILOT2C_REV4_STEP = "10.8 (amended by D3)"
PILOT2C_EPISODES = 3
REQUIRED_CONFIG_KEYS = {"environment", "campaign", "conditions"}
EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2

def _training_blockers() -> tuple[str, ...]:
    """What the *training stage* still refuses, reported and never resolved.

    Pilot 2-C evaluates artifacts already produced under D5; it trains nothing.
    The global training gate's refusal of further training is therefore not an
    execution precondition for this stage and is never folded into the stage's
    ``blockers``. Loadability of the six artifacts is reported separately under
    ``training_artifacts`` and their authority under ``training_authorization``.
    """
    declarations = training_authorization_status()["training_declarations"]
    if declarations["applicable"]:
        return (
            "training: D4 declares B3-B6 and D5 authorises only the six "
            "F/F_beta pilot artifacts; the global training gate still refuses "
            "any further training, and loadability is reported under "
            "training_artifacts",
        )
    return tuple(
        declarations["undischarged"][decision]
        for decision in ("B3", "B4", "B5", "B6")
    )


def _artifact_root(training_root: str | Path | None) -> Path:
    return PROJECT_ROOT / (training_root or TRAINING_ROOT)


def _load_trained_artifacts(
    config: Phase8Config,
    pairing: Mapping[tuple[str, int], int],
    training_root: str | Path | None,
):
    return load_pilot_evaluation_artifacts(
        config,
        _artifact_root(training_root),
        pairing=pairing,
        evaluation_seeds=PILOT2C_SEEDS,
        require_trained=True,
    )


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def pilot2c_seeds(config: Phase8Config) -> tuple[int, ...]:
    seeds = tuple(int(seed) for seed in config.campaign.pilot_seeds)
    if len(seeds) < len(PILOT2C_SEEDS):
        raise StageRefusal(
            PILOT2C_STAGE,
            [
                f"Pilot 2-C needs {len(PILOT2C_SEEDS)} declared pilot seeds; "
                f"campaign.yaml declares {len(seeds)}"
            ],
        )
    return seeds[: len(PILOT2C_SEEDS)]


def pilot2c_plan(config: Phase8Config) -> PilotPlan:
    return PilotPlan(
        stage=PILOT2C_STAGE,
        rev4_step=PILOT2C_REV4_STEP,
        arms=PILOT2C_ARMS,
        seeds=pilot2c_seeds(config),
        episodes=PILOT2C_EPISODES,
        establishes=(
            "the floor executes substrate-free and constant, A' reproduces A "
            "exactly on P1-P19, F-beta is state-independent, F is "
            "state-dependent and frozen at evaluation, motor silence is "
            "reported, plasticity is attributable, provenance is complete and "
            "every arm is viable"
        ),
        does_not_establish=(
            "no hypothesis is tested; no C1-C4, H1-H3, paired dispersion or "
            "sigma_max is estimated; U7 is not discharged and N is not "
            "selected; pilot rows are never merged into the campaign dataset"
        ),
        estimates_contrasts=False,
        stage_purpose=PILOT2C_STAGE_PURPOSE,
    )


# ---------------------------------------------------------------------------
# readiness
# ---------------------------------------------------------------------------


def _scope_failures(config: Phase8Config, plan: PilotPlan) -> list[str]:
    """Local mirror of the gate's scope assertions, for the readiness report."""
    failures: list[str] = []
    if tuple(plan.arms) != PILOT2C_ARMS:
        failures.append(f"arms are {list(plan.arms)!r}")
    if tuple(plan.seeds) != PILOT2C_SEEDS:
        failures.append(f"seeds are {list(plan.seeds)!r}")
    if int(plan.episodes) != PILOT2C_EPISODES:
        failures.append(f"episodes_per_seed is {plan.episodes!r}")
    if len(plan.entries()) != PILOT2C_G3_SCOPE["n_episodes"]:
        failures.append(f"the grid has {len(plan.entries())} entries")
    registry = build_registry(config.conditions)
    for arm in PILOT2C_NEURAL_ARMS:
        if registry.spec(arm).requires_structure:
            failures.append(f"{arm} requires a certified structure record")
    if registry.spec("floor").substrate != "none":
        failures.append("the floor declares a substrate")
    return failures


def pilot2c_readiness(
    config: Phase8Config,
    *,
    pairing: Mapping[tuple[str, int], int] | None = None,
    preflight=memory_preflight,
    training_root: str | Path | None = None,
) -> dict:
    """Declare every execution requirement and the blockers that remain."""
    plan = pilot2c_plan(config)
    authorization = stage_authorization(PILOT2C_STAGE, config=config, plan=plan)
    applicability = pilot2c_applicability()

    blockers: list[str] = list(authorization["blockers"])
    if not applicability["applicable"]:
        blockers.append(
            "D3 binding: " + "; ".join(applicability["failures"] or ["unknown"])
        )

    scope_failures = _scope_failures(config, plan)
    blockers.extend(f"scope: {item}" for item in scope_failures)

    config_hashes = {
        str(name): str(entry["sha256"]) for name, entry in config.hashes.items()
    }
    if set(config_hashes) != REQUIRED_CONFIG_KEYS:
        blockers.append(
            f"configuration hashes are {sorted(config_hashes)}, not "
            f"{sorted(REQUIRED_CONFIG_KEYS)}"
        )
    try:
        input_hashes = hash_inputs(phase8_input_paths(config))
    except FileNotFoundError as error:
        input_hashes = {}
        blockers.append(f"frozen inputs: {error}")
    if len(input_hashes) != 7:
        blockers.append(
            f"{len(input_hashes)} frozen-input hashes are declared, not the "
            "seven the amendment requires"
        )

    memory = dict(preflight(config.campaign.memory_gate_gb))
    if not memory.get("passed"):
        blockers.append(
            "B8: free memory is below the declared §9.3 gate; available "
            f"{memory.get('available_gb')} GB of {config.campaign.memory_gate_gb} GB"
        )

    root = _artifact_root(training_root)
    directories = discover_artifact_directories(root)
    artifact_report: dict
    if pairing is None:
        artifact_report = {
            "root": root.as_posix(),
            "directories": len(directories),
            "loaded": False,
            "reason": "no explicit pilot evaluation pairing was supplied",
        }
        blockers.append(
            "artifacts: no explicit (condition, evaluation seed) -> training "
            "seed pairing was supplied; the loader never invents it"
        )
    else:
        try:
            loaded = _load_trained_artifacts(config, pairing, training_root)
            artifact_report = {"loaded": True, **loaded.describe()}
        except (TrainingError, OSError) as error:
            artifact_report = {
                "root": root.as_posix(),
                "directories": len(directories),
                "loaded": False,
                "reason": f"{type(error).__name__}: {error}",
            }
            blockers.append(f"artifacts: {error}")
    if not directories:
        blockers.append(
            "artifacts: no trained artifact directory exists under "
            f"{root.as_posix()}"
        )

    # D5/D6 are the live authority for the six trained artifacts. The global
    # training gate still refuses *further* training, but that refusal is a
    # training-stage restriction, not a precondition for an evaluation stage
    # that trains nothing; it is reported and never added to ``blockers``.
    training_blockers = _training_blockers()
    d5 = d5_applicability()
    if not d5["applicable"]:
        blockers.append("training artifacts: " + d5["reason"])

    destination = stage_root(config, PILOT2C_STAGE)
    destination_free = not destination.exists() or not any(destination.iterdir())
    if not destination_free:
        blockers.append(
            f"results destination {destination.as_posix()} is not free; an "
            "existing run is never overwritten"
        )

    return {
        "stage": PILOT2C_STAGE,
        "stage_purpose": PILOT2C_STAGE_PURPOSE,
        "plan": plan.as_dict(config.campaign.master_seed),
        "authorization": {
            "authorized": authorization["authorized"],
            "exemption": authorization["exemption"],
            "g3_applicability": authorization["g3_applicability"],
            "blockers": authorization["blockers"],
        },
        "d3": {
            "record": OWNER_DECISION_D3_RECORD.as_posix(),
            "amendment": AMENDMENT_PATH.as_posix(),
            "amendment_id": AMENDMENT_ID,
            "applicable": applicability["applicable"],
            "amendment_matches_disk": applicability.get("amendment_matches_disk"),
            "bound_to_rev4": applicability.get("bound_to_rev4"),
            "failures": applicability["failures"],
        },
        "config_hashes": config_hashes,
        "input_hashes": input_hashes,
        "memory_preflight": memory,
        "training_artifacts": artifact_report,
        "training_authorization": {
            "d5_d6_applicable": bool(d5["applicable"]),
            "d5_record": d5["path"],
            "d6_record": d5["d6"]["path"],
            "d5_valid": d5["valid"],
            "d6_valid": d5["d6"]["valid"],
            # D5 authorises exactly its six artifacts; the global training gate
            # still refuses every other training run (next key is False).
            "d5_scope_authorized": bool(d5["training_execution_authorized"]),
            "authorised_scope": dict(d5["authorised_scope"]),
            "frozen_sources": dict(d5["frozen_sources"]),
            "g3": dict(d5["g3"]),
            "does_not_authorise": list(d5["does_not_authorise"]),
            "global_training_gate_authorized": bool(
                training_authorization_status()["training_authorized"]
            ),
            "failures": list(d5["failures"]),
        },
        "training_blockers": list(training_blockers),
        "results_root": config.campaign.results_root,
        "results_destination": destination.as_posix(),
        "results_destination_free": destination_free,
        "uses_randomized_graph": False,
        "constructs_randomized_graph": False,
        "executable": not blockers,
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# certification evaluator
# ---------------------------------------------------------------------------


def _index(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, int, int], dict]:
    return {
        (str(row["condition"]), int(row["seed"]), int(row["episode"])): dict(row)
        for row in rows
    }


def _pilot2c_rows(
    rows: Sequence[Mapping[str, Any]], config: Phase8Config
) -> list[dict]:
    try:
        validated = validate_rows(rows)
    except SchemaError as error:
        raise StageConfigurationError(f"Pilot 2-C rows fail validation: {error}") from None
    foreign_seeds = sorted(
        {int(row["seed"]) for row in validated} - set(PILOT2C_SEEDS)
    )
    if foreign_seeds:
        raise StageConfigurationError(
            f"refusing non-pilot seed(s) {foreign_seeds}; pilot and campaign "
            "datasets are never merged"
        )
    foreign_arms = sorted(
        {str(row["condition"]) for row in validated} - set(PILOT2C_ARMS)
    )
    if foreign_arms:
        raise StageConfigurationError(
            f"Pilot 2-C does not declare arm(s) {foreign_arms}"
        )
    return validated


def _pairs() -> list[tuple[int, int]]:
    return [
        (seed, episode)
        for seed in PILOT2C_SEEDS
        for episode in range(PILOT2C_EPISODES)
    ]


def _claim(claim_id: str, claim: str, passed: bool, **evidence: Any) -> dict:
    return {
        "id": claim_id,
        "claim": claim,
        "passed": bool(passed),
        "descriptive_only": True,
        "is_hypothesis_test": False,
        **evidence,
    }


def _check_floor(index: Mapping[tuple[str, int, int], dict]) -> dict:
    entries = []
    for seed, episode in _pairs():
        row = index.get(("floor", seed, episode))
        if row is None:
            entries.append({"seed": seed, "episode": episode, "present": False})
            continue
        counts = {k: int(v) for k, v in dict(row["action_counts"]).items() if int(v)}
        evidence = dict(row.get("evidence") or {})
        passed = (
            row.get("status", "ok") == "ok"
            and counts == {"NO_ACTION": int(row["steps"])}
            and int(row["motor_spikes"]) == 0
            and row["weights_before"] is None
            and row["weights_after"] is None
            and evidence.get("neural_substrate") == "none"
            and evidence.get("is_neural_arm") is False
        )
        entries.append(
            {
                "seed": seed,
                "episode": episode,
                "present": True,
                "passed": passed,
                "steps": int(row["steps"]),
                "non_zero_actions": sorted(counts),
                "motor_spikes": int(row["motor_spikes"]),
                "weights": [row["weights_before"], row["weights_after"]],
            }
        )
    passed = len(entries) == len(_pairs()) and all(
        entry.get("passed") for entry in entries
    )
    return _claim(
        "P2C-1",
        "the nine floor replays execute, take NO_ACTION on every decision and "
        "own no spike or weight",
        passed,
        episodes=entries,
    )


def _check_identity(index: Mapping[tuple[str, int, int], dict]) -> dict:
    entries = []
    mismatches = []
    for seed, episode in _pairs():
        fixed = index.get(("A", seed, episode))
        control = index.get(("A_prime", seed, episode))
        if fixed is None or control is None:
            entries.append({"seed": seed, "episode": episode, "present": False})
            continue
        notes = dict(control.get("notes") or {})
        block = dict(notes.get("a_prime") or {})
        report = dict(block.get("equivalence") or {})
        evidence = dict(control.get("evidence") or {})
        plasticity = dict(evidence.get("plasticity_path") or {})
        game_loop = dict(notes.get("game_loop") or {})
        store_mismatch = [
            {"field_id": field_id, "field": field}
            for field_id, field in IDENTITY_FIELDS
            if json.dumps(fixed.get(field), sort_keys=True)
            != json.dumps(control.get(field), sort_keys=True)
        ]
        passed = (
            report.get("all_equal") is True
            and int(report.get("field_count", 0)) == 19
            and float(plasticity.get("eta", float("nan"))) == 0.0
            and plasticity.get("mode") in (
                "rule_executed_zero_delta",
                "short_circuited",
            )
            # P19: the neural state is cleared once at episode start and never
            # between game updates. ``stepper_resets_this_episode`` also counts
            # that opening reset, so it is exactly one, not zero.
            and int(game_loop.get("neural_resets_during_episode", -1)) == 0
            and int(evidence.get("stepper_resets_this_episode", -1)) == 1
            and control["weights_before"] == control["weights_after"]
            and not store_mismatch
            and control.get("status", "ok") == "ok"
        )
        if not passed:
            mismatches.append(
                {
                    "seed": seed,
                    "episode": episode,
                    "equivalence": report,
                    "store_level": store_mismatch,
                }
            )
        entries.append(
            {
                "seed": seed,
                "episode": episode,
                "present": True,
                "passed": passed,
                "fields_compared": int(report.get("field_count", 0)),
                "eta": plasticity.get("eta"),
                "store_level_mismatches": store_mismatch,
            }
        )
    passed = len(entries) == len(_pairs()) and all(
        entry.get("passed") for entry in entries
    )
    return _claim(
        "P2C-2",
        "A' reproduces A exactly on P1-P19 at eta=0 with a zero delta",
        passed,
        episodes=entries,
        mismatches=mismatches,
        invalidates_on_mismatch=["B"],
        b_status="INVALID" if not passed else "not invalidated",
    )


def _check_f_beta(index: Mapping[tuple[str, int, int], dict]) -> dict:
    entries = []
    for seed, episode in _pairs():
        row = index.get(("F_beta", seed, episode))
        if row is None:
            entries.append({"seed": seed, "episode": episode, "present": False})
            continue
        notes = dict(row.get("notes") or {})
        block = dict(notes.get("readout_certification") or {})
        checks = dict(block.get("invariant_checks") or {})
        counts = {k: int(v) for k, v in dict(row["action_counts"]).items() if int(v)}
        passed = (
            row.get("status", "ok") == "ok"
            and block.get("state_independent") is True
            and block.get("feature_weights_all_zero") is True
            and block.get("logits_identical") is True
            and block.get("weights_frozen") is True
            and checks.get("single_trainable_tensor") is True
            and checks.get("trainable_is_bias") is True
            and checks.get("feature_weights_exactly_zero") is True
            and checks.get("feature_weights_not_trainable") is True
            and len(counts) == 1
        )
        entries.append(
            {
                "seed": seed,
                "episode": episode,
                "present": True,
                "passed": passed,
                "actions_selected": sorted(counts),
                "trainable_parameters": block.get("after", {}).get(
                    "trainable_parameters"
                ),
            }
        )
    passed = len(entries) == len(_pairs()) and all(
        entry.get("passed") for entry in entries
    )
    return _claim(
        "P2C-3",
        "F-beta's feature weights are zero, its only trainable parameter is "
        "the bias, its logits ignore the features, and it is constant",
        passed,
        episodes=entries,
    )


def _check_f(index: Mapping[tuple[str, int, int], dict]) -> dict:
    entries = []
    for seed, episode in _pairs():
        row = index.get(("F", seed, episode))
        if row is None:
            entries.append({"seed": seed, "episode": episode, "present": False})
            continue
        notes = dict(row.get("notes") or {})
        block = dict(notes.get("readout_certification") or {})
        counts = {k: int(v) for k, v in dict(row["action_counts"]).items() if int(v)}
        passed = (
            row.get("status", "ok") == "ok"
            and block.get("state_dependent") is True
            and block.get("feature_weights_all_zero") is False
            and block.get("weights_frozen") is True
            and block.get("before", {}).get("parameter_digest")
            == block.get("after", {}).get("parameter_digest")
            and block.get("before", {}).get("feature_weight_sha256")
            == block.get("after", {}).get("feature_weight_sha256")
        )
        entries.append(
            {
                "seed": seed,
                "episode": episode,
                "present": True,
                "passed": passed,
                "actions_selected": sorted(counts),
                "weights_changed_during_evaluation": row["weights_before"]
                != row["weights_after"],
            }
        )
    passed = len(entries) == len(_pairs()) and all(
        entry.get("passed") for entry in entries
    )
    return _claim(
        "P2C-4",
        "F's readout is state-dependent and its weights are unchanged from "
        "episode start to end",
        passed,
        episodes=entries,
    )


def _check_motor(index: Mapping[tuple[str, int, int], dict]) -> dict:
    per_arm: dict[str, dict] = {}
    failures = []
    for arm in PILOT2C_NEURAL_ARMS:
        total = 0
        zero = 0
        entries = 0
        for seed, episode in _pairs():
            row = index.get((arm, seed, episode))
            if row is None or row.get("status", "ok") != "ok":
                failures.append({"arm": arm, "seed": seed, "episode": episode})
                continue
            summary = row.get("motor_summary")
            if not isinstance(summary, Mapping):
                failures.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "episode": episode,
                        "reason": "no motor_summary",
                    }
                )
                continue
            entries += 1
            spikes = int(row["motor_spikes"])
            total += spikes
            zero += spikes == 0
            if int(summary.get("decisions", 0)) != int(row["steps"]) or int(
                summary.get("total_motor_spikes", -1)
            ) != spikes:
                failures.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "episode": episode,
                        "reason": "motor_summary is inconsistent with the row",
                    }
                )
        per_arm[arm] = {
            "episodes": entries,
            "total_motor_spikes": total,
            "episodes_with_zero_motor_spikes": zero,
        }
    expected = len(PILOT2C_NEURAL_ARMS) * len(_pairs())
    passed = (
        not failures
        and sum(item["episodes"] for item in per_arm.values()) == expected
    )
    return _claim(
        "P2C-5",
        "every neural episode records a per-decision motor block and a "
        "motor-spike count; zero is reported as zero",
        passed,
        per_arm=per_arm,
        failures=failures,
    )


def _check_plasticity(index: Mapping[tuple[str, int, int], dict]) -> dict:
    a_prime_entries = []
    b_entries = []
    failures = []
    for seed, episode in _pairs():
        control = index.get(("A_prime", seed, episode))
        if control is None:
            failures.append({"arm": "A_prime", "seed": seed, "episode": episode})
        else:
            block = dict((control.get("notes") or {}).get("plasticity") or {})
            passed = (
                int(block.get("changed_edges", -1)) == 0
                and float(block.get("max_abs_delta_pa", -1.0)) == 0.0
                and float(
                    (block.get("summary_plasticity") or {}).get("eta", float("nan"))
                )
                == 0.0
            )
            a_prime_entries.append(
                {
                    "seed": seed,
                    "episode": episode,
                    "passed": passed,
                    "changed_edges": block.get("changed_edges"),
                    "max_abs_delta_pa": block.get("max_abs_delta_pa"),
                }
            )
            if not passed:
                failures.append(
                    {"arm": "A_prime", "seed": seed, "episode": episode}
                )
        b_row = index.get(("B", seed, episode))
        if b_row is None:
            failures.append({"arm": "B", "seed": seed, "episode": episode})
        else:
            block = dict((b_row.get("notes") or {}).get("plasticity") or {})
            reported = {
                "eligible_edges": block.get("eligible_edges"),
                "changed_edges": block.get("changed_edges"),
                "max_abs_delta_pa": block.get("max_abs_delta_pa"),
                "n_update_reports": block.get("n_update_reports"),
                "n_hook_calls": block.get("n_hook_calls"),
            }
            passed = all(value is not None for value in reported.values())
            b_entries.append(
                {"seed": seed, "episode": episode, "passed": passed, **reported}
            )
            if not passed:
                failures.append({"arm": "B", "seed": seed, "episode": episode})
    passed = (
        not failures
        and len(a_prime_entries) == len(_pairs())
        and len(b_entries) == len(_pairs())
    )
    return _claim(
        "P2C-6",
        "A' reports an exactly zero delta and B reports its eligible and "
        "changed edges and maximum applied update",
        passed,
        a_prime=a_prime_entries,
        b=b_entries,
        failures=failures,
    )


def _check_provenance(
    index: Mapping[tuple[str, int, int], dict],
    config: Phase8Config,
    manifest: Mapping[str, Any] | None,
) -> dict:
    expected_inputs = set(str(name) for name in config.campaign.frozen_inputs)
    expected_configs = {
        str(name): str(entry["sha256"]) for name, entry in config.hashes.items()
    }
    failures = []
    for key, row in index.items():
        arm, seed, episode = key
        if set(row["input_hashes"]) != expected_inputs:
            failures.append({"row": list(key), "reason": "input hashes"})
        if dict(row["config_hashes"]) != expected_configs:
            failures.append({"row": list(key), "reason": "config hashes"})
        notes = dict(row.get("notes") or {})
        if notes.get("evidence_kind") != "pilot":
            failures.append({"row": list(key), "reason": "evidence kind"})
        if notes.get("stage_purpose") != PILOT2C_STAGE_PURPOSE:
            failures.append({"row": list(key), "reason": "stage purpose"})
        if not notes.get("seed_plan"):
            failures.append({"row": list(key), "reason": "seed plan"})
        if arm in ("F", "F_beta"):
            artifact = (notes.get("readout_certification") or {}).get("artifact")
            entries = list((artifact or {}).get("entries") or ())
            match = [
                entry
                for entry in entries
                if int(entry.get("evaluation_seed", -1)) == int(seed)
            ]
            required = (
                "condition_id",
                "evaluation_seed",
                "training_seed",
                "parameter_digest",
                "parameter_file_sha256",
            )
            if not match or any(
                entry.get(field) in (None, "") for entry in match for field in required
            ):
                failures.append({"row": list(key), "reason": "artifact provenance"})
    manifest_purpose = (
        None if manifest is None else (manifest.get("design") or {}).get("stage_purpose")
    )
    if manifest is not None and manifest_purpose != PILOT2C_STAGE_PURPOSE:
        failures.append(
            {
                "row": "manifest",
                "reason": f"manifest stage_purpose is {manifest_purpose!r}",
            }
        )
    return _claim(
        "P2C-7",
        "every row records the seven input hashes, three config hashes, seed "
        "plan, evidence kind and stage purpose, and every F/F-beta row records "
        "its artifact provenance",
        not failures,
        manifest_stage_purpose=manifest_purpose,
        failures=failures,
    )


def _check_viability(
    index: Mapping[tuple[str, int, int], dict], config: Phase8Config
) -> dict:
    plan = pilot2c_plan(config)
    missing = [list(key) for key in plan.entries() if key not in index]
    errors = [
        list(key) for key, row in index.items() if row.get("status", "ok") != "ok"
    ]
    scores = {
        f"{condition}:{seed}:{episode}": float(row["survival_score"])
        for (condition, seed, episode), row in index.items()
    }
    passed = not missing and not errors
    return _claim(
        "P2C-8",
        "every arm completes its planned episodes with schema-valid rows and a "
        "recorded survival score; nothing is skipped or retried",
        passed,
        planned=len(plan.entries()),
        stored=len(index),
        missing=missing,
        error_rows=errors,
        survival_scores=scores,
    )


def evaluate_certification(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: Phase8Config,
    manifest: Mapping[str, Any] | None = None,
) -> dict:
    """Recompute P2C-1 … P2C-8 from stored rows. Writes nothing."""
    validated = _pilot2c_rows(rows, config)
    index = _index(validated)
    claims = [
        _check_floor(index),
        _check_identity(index),
        _check_f_beta(index),
        _check_f(index),
        _check_motor(index),
        _check_plasticity(index),
        _check_provenance(index, config, manifest),
        _check_viability(index, config),
    ]
    return {
        "stage": PILOT2C_STAGE,
        "stage_purpose": PILOT2C_STAGE_PURPOSE,
        "descriptive_only": True,
        "is_hypothesis_test": False,
        "estimates_contrasts": False,
        "merged_into_campaign": False,
        "n_seeds_selected_written": False,
        "rows": len(validated),
        "claims": claims,
        "all_passed": all(claim["passed"] for claim in claims),
        "amendment": {
            "id": AMENDMENT_ID,
            "path": AMENDMENT_PATH.as_posix(),
        },
        "owner_decision": OWNER_DECISION_D3_RECORD.as_posix(),
    }


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------


def run_pilot2c(
    config: Phase8Config,
    *,
    run_id: str,
    pairing: Mapping[tuple[str, int], int] | None = None,
    artifacts: Any | None = None,
    base_dir: str | Path | None = None,
    new_run_id: str | None = None,
    training_root: str | Path | None = None,
    preflight=memory_preflight,
    episode_runner: Any | None = None,
) -> dict:
    """Refuse unless every gate passes, then run the exact Pilot 2-C grid."""
    readiness = pilot2c_readiness(
        config, pairing=pairing, preflight=preflight, training_root=training_root
    )
    if not readiness["executable"]:
        raise StageRefusal(PILOT2C_STAGE, readiness["blockers"], readiness=readiness)
    plan = pilot2c_plan(config)
    if episode_runner is None:
        if artifacts is None:
            if pairing is None:
                raise StageRefusal(
                    PILOT2C_STAGE,
                    [
                        "artifacts: F and F_beta need an explicit pairing and "
                        "the six trained artifacts; neither is inferred"
                    ],
                )
            artifacts = _load_trained_artifacts(config, pairing, training_root)
        runner = Pilot2CEpisodeRunner(
            config, artifacts=artifacts, pairing=pairing
        )
    else:
        runner = episode_runner
    base = Path(base_dir or stage_root(config, PILOT2C_STAGE))
    return drive_pilot(
        plan,
        config,
        base_dir=base,
        run_id=run_id,
        episode_runner=runner,
        preflight=preflight,
        new_run_id=new_run_id,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _read_rows(run_dir: Path, config: Phase8Config) -> list[dict]:
    store = EpisodeStore(
        run_dir, filename=config.campaign.episode_store_name, create=False
    )
    return store.rows()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="experiments.phase_8.stages.pilot2c")
    sub = parser.add_subparsers(dest="command", required=True)

    readiness_parser = sub.add_parser("readiness", help="report blockers only")
    readiness_parser.add_argument("--pairing", type=Path, default=None)
    readiness_parser.add_argument("--json", type=Path, default=None)

    evaluate_parser = sub.add_parser("evaluate", help="recompute P2C-1..P2C-8")
    evaluate_parser.add_argument("--run-dir", type=Path, required=True)
    evaluate_parser.add_argument("--json", type=Path, default=None)

    run_parser = sub.add_parser("run", help="run the exact grid, or refuse")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--pairing", type=Path, default=None)
    run_parser.add_argument("--new-run-id", default=None)

    args = parser.parse_args(argv)
    config = load_phase8_config()

    if args.command == "readiness":
        pairing = _load_pairing(args.pairing)
        report = pilot2c_readiness(config, pairing=pairing)
        _emit(report, args.json)
        return EXIT_OK if report["executable"] else EXIT_INCOMPLETE

    if args.command == "evaluate":
        run_dir = args.run_dir
        rows = _read_rows(run_dir, config)
        manifest_path = run_dir / config.campaign.run_manifest_name
        manifest = load_manifest(manifest_path) if manifest_path.is_file() else None
        report = evaluate_certification(rows, config=config, manifest=manifest)
        _emit(report, args.json)
        return EXIT_OK if report["all_passed"] else EXIT_INCOMPLETE

    try:
        summary = run_pilot2c(
            config,
            run_id=args.run_id,
            pairing=_load_pairing(args.pairing),
            new_run_id=args.new_run_id,
        )
    except StageRefusal as error:
        _emit(error.as_dict(), None)
        return EXIT_REFUSED
    _emit(summary, None)
    return EXIT_OK


def _load_pairing(path: Path | None) -> dict[tuple[str, int], int] | None:
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    pairing: dict[tuple[str, int], int] = {}
    for key, value in payload.items():
        condition, seed = str(key).rsplit(":", 1)
        pairing[(condition, int(seed))] = int(value)
    return pairing


def _emit(payload: Mapping[str, Any], target: Path | None) -> None:
    text = json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False)
    if target is not None:
        target.write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text + "\n")


__all__ = [
    "PILOT2C_EPISODES",
    "PILOT2C_REV4_STEP",
    "evaluate_certification",
    "main",
    "pilot2c_plan",
    "pilot2c_readiness",
    "pilot2c_seeds",
    "run_pilot2c",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
