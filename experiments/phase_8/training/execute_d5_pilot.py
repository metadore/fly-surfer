"""Execute the six D5-authorised F/F_beta pilot training artifacts.

SCIENTIFIC STATUS
    This is the production entry point for the only training execution D5
    authorises: F and F_beta at evaluation seeds 9001, 9002 and 9003, twenty
    episodes each, on the frozen biological substrate. It refuses any other
    root state, writes ``origin = "trained"`` artifacts into append-only
    storage, and never labels anything experimental that is not.

    Every episode is the real closed loop; one REINFORCE update is applied to
    the readout per episode and no synaptic weight changes. The evidence kind
    is fixed to ``experimental`` here so the driver cannot be misused to
    promote a synthetic fixture.

    Recovery is explicit. An artifact whose manifest already exists is reloaded
    and verified, never rewritten. An artifact that holds verified checkpoints
    but no manifest is resumed from its last checkpoint; before the artifact is
    written, an uninterrupted reference run of the same seeds is executed in a
    separate recovery root and the two runs are compared field by field (D4 B6).
    The interruption, the resumed run and the equivalence report are appended to
    the event log, and no episode is ever restarted under a different seed.

Usage::

    python -m experiments.phase_8.training.execute_d5_pilot
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.phase_8.campaign.factory import CampaignFactory, FactorySettings
from experiments.phase_8.config import load_phase8_config

from .artifacts import artifact_directory
from .config import canonical_json, validate_training_config
from .errors import TrainingError
from .pilot import PILOT_SUBSTRATE, build_pilot_plan
from .pilot_artifact import verify_trained_artifact, write_trained_artifact
from .pilot_training import run_pilot_artifact, verify_resume_equivalence

DEFAULT_ROOT = "experiments/results/phase_8/training"
LOG_NAME = "pilot_training_log.jsonl"
SUMMARY_NAME = "execution_summary.json"
REFERENCE_ROOT_NAME = "training_recovery_reference"
MANIFEST_NAME = "manifest.json"
CHECKPOINT_GLOB = "episode_*"


def _emit(log_path: Path, payload: dict) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(payload) + "\n")


def _checkpoint_directories(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob(CHECKPOINT_GLOB) if path.is_dir())


def _report(event: dict) -> None:
    print(
        "episode {episode}/{budget} {condition_id} seed {evaluation_seed} "
        "reward={episode_reward:.4f} motor_spikes={motor_spikes} "
        "checkpoint={checkpoint}".format(**event),
        flush=True,
    )


def _artifact_record(entry: Any, status: str, detail: dict) -> dict:
    return {
        "condition_id": entry.condition_id,
        "evaluation_seed": entry.evaluation_seed,
        "training_seed": entry.training_seed,
        "status": status,
        "evidence_kind": "experimental",
        **detail,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--reference-root", default=None)
    args = parser.parse_args(argv)

    phase8_config = load_phase8_config()
    config = validate_training_config(phase8_config)
    plan = build_pilot_plan(phase8_config, config=config)
    if plan.substrate != PILOT_SUBSTRATE:
        raise TrainingError(
            f"the plan substrate is {plan.substrate!r}; D5 authorises "
            f"{PILOT_SUBSTRATE!r} only"
        )

    root = Path(args.root)
    reference_root = (
        Path(args.reference_root)
        if args.reference_root
        else root.parent / REFERENCE_ROOT_NAME
    )
    summary_path = root / SUMMARY_NAME
    if summary_path.exists():
        raise TrainingError(f"{summary_path} already exists; evidence is append-only")
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / LOG_NAME

    factory = CampaignFactory(
        frozen_inputs=phase8_config.campaign.frozen_inputs,
        settings=FactorySettings(
            max_game_updates=int(phase8_config.campaign.max_game_updates)
        ),
    )

    _emit(
        log_path,
        {
            "event": "plan_resume" if log_path.exists() else "plan_start",
            "runner": "experiments.phase_8.training.pilot_training.PilotEpisodeRunner",
            "n_artifacts": len(plan.entries),
            "n_episodes": sum(entry.episodes for entry in plan.entries),
            "master_seed": plan.master_seed,
            "substrate": plan.substrate,
            "b3_sha256": plan.b3.get("sha256"),
        },
    )

    records: list[dict] = []
    equivalence_records: list[dict] = []
    for entry in plan.entries:
        directory = artifact_directory(root, entry.condition_id, entry.evaluation_seed)
        if (directory / MANIFEST_NAME).exists():
            verified = verify_trained_artifact(
                directory, config=config, expected_condition=entry.condition_id
            )
            record = _artifact_record(
                entry,
                "already_complete",
                {
                    "artifact_directory": directory.as_posix(),
                    "episodes_completed": verified["provenance"]["episodes_completed"],
                    "checkpoints": verified["provenance"]["checkpoints"],
                },
            )
            records.append(record)
            _emit(log_path, {"event": "artifact_already_complete", **record})
            continue

        checkpoint_directories = _checkpoint_directories(directory / "checkpoints")
        _emit(
            log_path,
            {
                "event": "artifact_start",
                "condition_id": entry.condition_id,
                "evaluation_seed": entry.evaluation_seed,
                "training_seed": entry.training_seed,
                "episodes": entry.episodes,
                "resume": bool(checkpoint_directories),
                "checkpoints_present": len(checkpoint_directories),
            },
        )

        equivalence: dict | None = None
        if checkpoint_directories:
            last_checkpoint = checkpoint_directories[-1]
            _emit(
                log_path,
                {
                    "event": "interruption_detected",
                    "condition_id": entry.condition_id,
                    "evaluation_seed": entry.evaluation_seed,
                    "training_seed": entry.training_seed,
                    "episodes_completed": len(checkpoint_directories),
                    "resume_from": last_checkpoint.as_posix(),
                    "note": (
                        "resuming from the last verified checkpoint; the seed, "
                        "budget and substrate are unchanged"
                    ),
                },
            )
            result = run_pilot_artifact(
                phase8_config,
                entry,
                root=root,
                config=config,
                factory=factory,
                resume_from=last_checkpoint,
                substrate=PILOT_SUBSTRATE,
                progress_callback=_report,
            )
            if result.resume.get("resumed") is not True:
                raise TrainingError(
                    "the recovery run did not record that it resumed a checkpoint"
                )
            _emit(
                log_path,
                {
                    "event": "recovery_completed",
                    "condition_id": entry.condition_id,
                    "evaluation_seed": entry.evaluation_seed,
                    "episodes_completed": result.episodes_completed,
                    "resume": dict(result.resume),
                },
            )

            reference_directory = artifact_directory(
                reference_root, entry.condition_id, entry.evaluation_seed
            )
            if _checkpoint_directories(reference_directory / "checkpoints"):
                raise TrainingError(
                    f"{reference_directory} already holds a recovery reference; "
                    "it is never regenerated silently"
                )
            reference = run_pilot_artifact(
                phase8_config,
                entry,
                root=reference_root,
                config=config,
                factory=factory,
                substrate=PILOT_SUBSTRATE,
            )
            equivalence = verify_resume_equivalence(reference, result)
            equivalence_path = reference_directory / "equivalence.json"
            equivalence_path.write_text(
                json.dumps(equivalence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            equivalence_records.append(
                {
                    "condition_id": entry.condition_id,
                    "evaluation_seed": entry.evaluation_seed,
                    "equivalent": equivalence["equivalent"],
                    "exactness_claim": equivalence["exactness_claim"],
                    "compared_episodes": equivalence["compared_episodes"],
                    "report": equivalence_path.as_posix(),
                }
            )
            _emit(
                log_path,
                {
                    "event": "equivalence_demonstrated",
                    "condition_id": entry.condition_id,
                    "evaluation_seed": entry.evaluation_seed,
                    "equivalent": equivalence["equivalent"],
                    "exactness_claim": equivalence["exactness_claim"],
                    "compared_episodes": equivalence["compared_episodes"],
                    "differences": equivalence["differences"],
                },
            )
            if not equivalence["equivalent"]:
                raise TrainingError(
                    "refusing to write an artifact whose resumed run is not "
                    "equivalent to the uninterrupted reference"
                )
        else:
            result = run_pilot_artifact(
                phase8_config,
                entry,
                root=root,
                config=config,
                factory=factory,
                substrate=PILOT_SUBSTRATE,
                progress_callback=_report,
            )

        written = write_trained_artifact(
            phase8_config,
            result,
            entry,
            root=root,
            plan=plan,
            config=config,
            evidence_kind="experimental",
        )
        record = _artifact_record(
            entry,
            "written",
            {
                "artifact_directory": written["directory"],
                "parameter_digest": written["parameter_digest"],
                "state_digest": written["state_digest"],
                "parameters_sha256": written["parameters_sha256"],
                "manifest_sha256": written["manifest_sha256"],
                "training_run_sha256": written["training_run_sha256"],
                "episodes_completed": written["episodes_completed"],
                "checkpoints": written["checkpoints"],
                "recovered": bool(result.resume.get("resumed")),
                "equivalence": (
                    None if equivalence is None else equivalence["exactness_claim"]
                ),
            },
        )
        records.append(record)
        _emit(log_path, {"event": "artifact_complete", **record})

    _emit(
        log_path,
        {
            "event": "plan_complete",
            "artifacts_completed": len(records),
            "episodes_completed": sum(item["episodes_completed"] for item in records),
            "evidence_kind": "experimental",
        },
    )
    summary = {
        "plan": plan.describe(),
        "artifacts": records,
        "equivalence": equivalence_records,
        "artifacts_completed": len(records),
        "episodes_completed": sum(item["episodes_completed"] for item in records),
        "evidence_kind": "experimental",
        "training_execution_authorized_by": "D5",
        "log": log_path.as_posix(),
        "reference_root": reference_root.as_posix(),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifacts_completed": summary["artifacts_completed"],
                "episodes_completed": summary["episodes_completed"],
                "evidence_kind": summary["evidence_kind"],
                "recovered_artifacts": sum(
                    1 for item in records if item.get("recovered")
                ),
                "log": summary["log"],
                "summary": summary_path.as_posix(),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if len(records) == len(plan.entries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
