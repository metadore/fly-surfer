"""Training orchestration (REV4 §10.5 and §10.9), gated and decision-free.

SCIENTIFIC STATUS
    The training *engine* already exists and is tested on synthetic fixtures.
    This module is the orchestration layer that a future authorised run would
    call. It adds no learner, no schedule and no default:

    * the campaign-to-training seed pairing (B3) is an explicit caller input;
    * the training-episode environment-seed schedule (B4) is an explicit
      caller input — REV4 declares none;
    * the checkpoint cadence, retention and format (B5) are explicit caller
      inputs, or checkpoints are simply not written;
    * bit-identical resume is not claimed (B6): the checkpoint interface
      restores parameters and counters only.

    ``plan_training_stage`` is read-only and currently refuses because
    ``design.n_seeds_selected`` is null. ``execute_training_stage`` calls
    :func:`..training.gate.assert_training_authorized` first, which always
    raises on the present approval state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from ..campaign.protocol import CampaignNotAuthorized
from ..config import ConfigError, MemoryGateError, Phase8Config, load_phase8_config
from ..training.checkpoint import describe_checkpoint_interface
from ..training.config import TRAINABLE_CONDITIONS, validate_training_config
from ..training.errors import (
    DesignUnresolvedError,
    TrainingConfigError,
    TrainingNotAuthorized,
)
from ..training.gate import (
    assert_training_authorized,
    design_status,
    training_authorization_status,
)
from ..training.plan import build_training_plan, describe_interface, run_training
from .common import (
    NO_EXECUTION_NOTE,
    StageConfigurationError,
    StageRefusal,
    authorization_snapshot,
    stage_envelope,
)

TRAINING_STAGE = "training"
EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2

DECLARATION_BLOCKERS = (
    "B3: no campaign-to-training seed pairing is declared; supply an explicit "
    "(condition, campaign_seed) -> training_seed map",
    "B4: no training-episode environment-seed schedule is declared; supply an "
    "explicit per-episode schedule",
    "B5: no checkpoint cadence, retention or format is declared; a resumable "
    "run needs an explicit policy",
    "B6: sampler RNG and optimizer moments are not checkpointed; resume is "
    "parameter-continuous and not bit-identical",
)


def describe_training_stage(config: Phase8Config) -> dict:
    training_config = validate_training_config(config)
    record = stage_envelope(TRAINING_STAGE)
    record.update(
        {
            "interface": describe_interface(),
            "design": design_status(config.campaign),
            "authorization": training_authorization_status(),
            "campaign_authorization": authorization_snapshot(),
            "checkpoint": describe_checkpoint_interface(),
            "training_config": {
                "sha256": training_config.sha256(),
                "readout_episodes_per_seed": training_config.readout_episodes_per_seed,
                "e_gradient_updates": training_config.e_gradient_updates,
                "trainable_conditions": list(TRAINABLE_CONDITIONS),
            },
            "declarations": {
                "seed_pairing": None,
                "environment_seed_schedule": None,
                "checkpoint_policy": None,
                "bit_identical_resume": False,
            },
            "execution_blockers": list(DECLARATION_BLOCKERS),
            "training_performed": False,
            "artifacts_written": 0,
            "note": NO_EXECUTION_NOTE,
        }
    )
    return record


def load_pairing(path: str | Path) -> dict[tuple[str, int], int]:
    """Read an explicit pairing map. Two accepted encodings, no defaults.

    Flat: ``{"F:1": 1001, ...}``. Nested: ``{"F": {"1": 1001}, ...}``.
    """
    source = Path(path)
    if not source.is_file():
        raise StageConfigurationError(f"pairing file not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StageConfigurationError(
            f"{source} is not valid JSON: {error}"
        ) from None
    if not isinstance(payload, Mapping):
        raise StageConfigurationError("the pairing file must contain a JSON object")

    pairing: dict[tuple[str, int], int] = {}
    for key, value in payload.items():
        if isinstance(value, Mapping):
            condition = str(key)
            items = value.items()
        elif isinstance(key, str) and ":" in key:
            condition, seed_text = key.split(":", 1)
            try:
                seed_value = int(seed_text)
            except ValueError:
                raise StageConfigurationError(
                    f"pairing key {key!r} has a non-integer campaign seed"
                ) from None
            items = ((str(seed_value), value),)
        else:
            raise StageConfigurationError(
                f"pairing entry {key!r} must be 'CONDITION:SEED' or a nested map"
            )
        if condition not in TRAINABLE_CONDITIONS:
            raise StageConfigurationError(
                f"pairing names {condition!r}; trainable conditions are "
                f"{list(TRAINABLE_CONDITIONS)}"
            )
        for seed_text, training_seed in items:
            try:
                campaign_seed = int(seed_text)
                training_seed = int(training_seed)
            except (TypeError, ValueError):
                raise StageConfigurationError(
                    f"pairing {condition}:{seed_text!r} is not an integer pair"
                ) from None
            if campaign_seed < 0 or training_seed < 0:
                raise StageConfigurationError("pairing seeds cannot be negative")
            key_tuple = (condition, campaign_seed)
            if key_tuple in pairing and pairing[key_tuple] != training_seed:
                raise StageConfigurationError(
                    f"pairing declares {condition}:{campaign_seed} twice"
                )
            pairing[key_tuple] = training_seed
    if not pairing:
        raise StageConfigurationError("the pairing map is empty")
    return pairing


def plan_training_stage(
    config: Phase8Config, *, pairing: Mapping[tuple[str, int], int]
) -> Any:
    """Build the explicit training plan; refuses while the design is unresolved."""
    training_config = validate_training_config(config)
    return build_training_plan(training_config, config.campaign, pairing)


def execute_training_stage(
    config: Phase8Config,
    *,
    pairing: Mapping[tuple[str, int], int],
    environment_seed_for_episode: Callable[[int], int] | int | None,
    checkpoint_policy: Mapping[str, Any] | None = None,
    require_bit_identical_resume: bool = False,
    root: str | Path | None = None,
) -> None:
    """Refuse to train until the protocol is approved.

    Every argument after ``pairing`` exists so a future authorised call cannot
    silently invent B4, B5 or B6. The authorisation gate runs first.
    """
    assert_training_authorized()
    if environment_seed_for_episode is None:
        raise StageRefusal(
            TRAINING_STAGE,
            [DECLARATION_BLOCKERS[1]],
        )
    if require_bit_identical_resume:
        raise StageRefusal(
            TRAINING_STAGE,
            [DECLARATION_BLOCKERS[3]],
        )
    plan = plan_training_stage(config, pairing=pairing)
    run_training(plan, root=root)


def _emit(payload: dict, pretty: bool) -> None:
    sys.stdout.write(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n"
    )


def _load(args: argparse.Namespace) -> Phase8Config:
    return load_phase8_config(
        environment_path=args.environment,
        campaign_path=args.campaign,
        conditions_path=args.conditions,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="training_stage",
        description=(
            "Phase 8 training orchestration. Status is read-only; plan and "
            "execute refuse while the design is unresolved and the protocol "
            "is unapproved."
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--status", action="store_true", help="emit the read-only status")
    parser.add_argument("--plan", action="store_true", help="build a plan, or refuse")
    parser.add_argument("--execute", action="store_true", help="refused while unapproved")
    parser.add_argument("--pairing", default=None, help="explicit pairing JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load(args)
        if args.plan or args.execute:
            if not args.pairing:
                sys.stderr.write("--pairing is required with --plan or --execute\n")
                return EXIT_INCOMPLETE
            pairing = load_pairing(args.pairing)
            if args.execute:
                payload = describe_training_stage(config)
                payload["command"] = "execute"
                try:
                    execute_training_stage(
                        config,
                        pairing=pairing,
                        environment_seed_for_episode=None,
                    )
                except (
                    CampaignNotAuthorized,
                    TrainingNotAuthorized,
                    StageRefusal,
                    MemoryGateError,
                ) as error:
                    payload["refused"] = True
                    payload["reason"] = str(error)
                    _emit(payload, args.pretty)
                    return EXIT_REFUSED
            try:
                plan = plan_training_stage(config, pairing=pairing)
            except DesignUnresolvedError as error:
                payload = describe_training_stage(config)
                payload["command"] = "plan"
                payload["blocked"] = True
                payload["reason"] = str(error)
                _emit(payload, args.pretty)
                return EXIT_INCOMPLETE
            payload = stage_envelope(TRAINING_STAGE)
            payload.update(
                {
                    "command": "plan",
                    "plan": plan.as_dict(),
                    "plan_describe": plan.describe(),
                    "execution_authorized": False,
                    "training_performed": False,
                    "note": NO_EXECUTION_NOTE,
                }
            )
            _emit(payload, args.pretty)
            return EXIT_OK

        payload = describe_training_stage(config)
        payload["command"] = "status"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, TrainingConfigError, StageConfigurationError) as error:
        sys.stderr.write(f"training stage configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "DECLARATION_BLOCKERS",
    "TRAINING_STAGE",
    "execute_training_stage",
    "load_pairing",
    "main",
    "plan_training_stage",
    "describe_training_stage",
]
