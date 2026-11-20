"""Pilot 1 (REV4 §10.3): A viability only, never a contrast estimate.

SCIENTIFIC STATUS
    Pilot 1 asks whether the A pipeline runs and records survival, action
    counts, motor spikes and the floor status. It must not estimate C1–C4 and
    must not be described as doing so. The full three-case U1 decision needs F
    and is made at 10.8, not here.

    ``run_pilot1`` calls the stage authorisation gate first. Under D1 and D2
    the exact Pilot 1 grid may proceed; any other grid or stage still refuses.
    ``describe_pilot1`` and :func:`pilot1_plan` are read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from ..campaign.protocol import CampaignNotAuthorized
from ..config import (
    ConfigError,
    MemoryGateError,
    PROJECT_ROOT,
    Phase8Config,
    load_phase8_config,
    memory_preflight,
)
from .common import (
    NO_EXECUTION_NOTE,
    PilotPlan,
    StageConfigurationError,
    StageRefusal,
    authorization_snapshot,
    collect_blockers,
    design_snapshot,
    drive_pilot,
    memory_snapshot,
    stage_envelope,
)
from .pilot1_runner import Pilot1EpisodeRunner

PILOT1_STAGE = "pilot1"
PILOT1_REV4_STEP = "10.3"
PILOT1_ARMS = ("A",)
PILOT1_SEED_COUNT = 3
PILOT1_EPISODE_COUNT = 3
PILOT1_CONTRASTS = ()

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2


def pilot1_seeds(config: Phase8Config) -> tuple[int, ...]:
    seeds = tuple(int(seed) for seed in config.campaign.pilot_seeds)
    if len(seeds) < PILOT1_SEED_COUNT:
        raise StageRefusal(
            PILOT1_STAGE,
            [
                f"Pilot 1 needs {PILOT1_SEED_COUNT} declared pilot seeds; "
                f"campaign.yaml declares {len(seeds)}"
            ],
        )
    return seeds[:PILOT1_SEED_COUNT]


def pilot1_plan(config: Phase8Config) -> PilotPlan:
    return PilotPlan(
        stage=PILOT1_STAGE,
        rev4_step=PILOT1_REV4_STEP,
        arms=PILOT1_ARMS,
        seeds=pilot1_seeds(config),
        episodes=PILOT1_EPISODE_COUNT,
        establishes=(
            "whether the A pipeline runs, and records survival, action counts, "
            "motor spikes and the floor status"
        ),
        does_not_establish=(
            "no C1-C4 contrast is estimated; no hypothesis is tested; the full "
            "three-case U1 decision needs F and is made at 10.8"
        ),
        estimates_contrasts=False,
    )


def describe_pilot1(config: Phase8Config, *, preflight: Callable[[float], dict] = memory_preflight) -> dict:
    plan = pilot1_plan(config)
    authorization = authorization_snapshot(stage="pilot1", plan=plan, config=config)
    memory = memory_snapshot(config, preflight=preflight)
    blockers = [
        item
        for item in collect_blockers(
            config, preflight=preflight, stage="pilot1", plan=plan
        )
        if not item.startswith("B2:")  # Pilot 1 precedes the campaign design
    ]
    record = stage_envelope(PILOT1_STAGE)
    record.update(
        {
            "plan": plan.as_dict(config.campaign.master_seed),
            "authorization": authorization,
            "design": design_snapshot(config),
            "memory_preflight": memory,
            "readiness": {
                "a_baseline_module": "experiments.phase_8.conditions.a_fixed",
                "a_baseline_implemented": True,
                "certified_graph_needed": False,
                "trained_artifact_needed": False,
                "design_decision_needed": False,
                "note": (
                    "Pilot 1 uses the biological A substrate only; C/D/C' and "
                    "the trained arms are not part of this grid"
                ),
            },
            "contrasts_estimated": [],
            "hypothesis_tests": [],
            "merged_into_campaign": False,
            "executable": not blockers,
            "execution_blockers": blockers,
            "frozen_constants": {
                "pilot_seeds": list(plan.seeds),
                "episodes_per_seed": plan.episodes,
                "max_game_updates": config.campaign.max_game_updates,
            },
            "note": NO_EXECUTION_NOTE,
        }
    )
    return record


def run_pilot1(
    config: Phase8Config,
    *,
    base_dir: str | Path | None = None,
    run_id: str = "pilot1",
    episode_runner: Callable[..., Any] | None = None,
    preflight: Callable[[float], dict] = memory_preflight,
    synthetic_fixture: bool = False,
    **driver_kwargs: Any,
) -> dict:
    """Run Pilot 1 when the stage gate and the memory gate both pass.

    ``synthetic_fixture=True`` is the labelled harness path: it refuses the
    real results root and stamps every row ``synthetic_fixture``.
    """
    plan = pilot1_plan(config)
    directory = base_dir if base_dir is not None else (
        PROJECT_ROOT / config.campaign.results_root / PILOT1_STAGE
    )
    return drive_pilot(
        plan,
        config,
        base_dir=directory,
        run_id=run_id,
        episode_runner=episode_runner,
        preflight=preflight,
        synthetic_fixture=synthetic_fixture,
        **driver_kwargs,
    )


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
        prog="pilot1",
        description="Pilot 1 (REV4 §10.3): describe or run the A viability grid.",
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--describe", action="store_true", help="emit the read-only plan")
    parser.add_argument(
        "--run",
        action="store_true",
        help=(
            "gated: requires D1, D2 and the memory gate; writes under the "
            "Phase 8 results root only for the exact authorized A grid"
        ),
    )
    parser.add_argument("--base-dir", default=None)
    parser.add_argument("--run-id", default="pilot1")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load(args)
        if args.run:
            payload = describe_pilot1(config)
            payload["command"] = "run"
            try:
                summary = run_pilot1(
                    config,
                    base_dir=args.base_dir,
                    run_id=args.run_id,
                    episode_runner=Pilot1EpisodeRunner(config),
                )
            except (CampaignNotAuthorized, StageRefusal, MemoryGateError) as error:
                payload["refused"] = True
                payload["executed"] = False
                payload["reason"] = str(error)
                _emit(payload, args.pretty)
                return EXIT_REFUSED
            payload["refused"] = False
            payload["executed"] = True
            payload["summary"] = summary
            _emit(payload, args.pretty)
            return EXIT_OK
        payload = describe_pilot1(config)
        payload["command"] = "describe"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, StageConfigurationError) as error:
        sys.stderr.write(f"pilot1 configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "PILOT1_ARMS",
    "PILOT1_CONTRASTS",
    "PILOT1_EPISODE_COUNT",
    "PILOT1_SEED_COUNT",
    "PILOT1_STAGE",
    "describe_pilot1",
    "main",
    "pilot1_plan",
    "pilot1_seeds",
    "run_pilot1",
]
