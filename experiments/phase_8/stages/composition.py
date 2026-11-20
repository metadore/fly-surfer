"""Production composition root for the Phase 8 campaign (REV4 §10.10).

SCIENTIFIC STATUS
    This module wires the existing pieces — registry, component factory,
    certified-graph source, training-artifact provider, dispatcher, campaign
    runner — into the single object a future authorised campaign would start.
    It adds no mechanism and no default:

    * all twelve arms must resolve exactly once from the registry;
    * A′ and C′ must be the plastic path at ``eta = 0``;
    * C, D and C′ must require a certified graph;
    * F, Fβ and F-init must require a readout;
    * E and E-full must be conventional;
    * the floor must own no substrate.

    ``start_campaign`` and ``resume_campaign`` call
    :func:`..campaign.protocol.assert_campaign_authorized` first. On the present
    state that always raises, so neither can construct a runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ..campaign import (
    CampaignDispatcher,
    CampaignFactory,
    CampaignNotAuthorized,
    CertifiedGraphSource,
    TrainingArtifacts,
    assert_campaign_authorized,
    validate_campaign,
)
from ..campaign.dispatcher import (
    ARM_ORDER,
    CONVENTIONAL_ARMS,
    CONTROL_MIRRORS,
    NEURAL_ARMS,
)
from ..campaign.factory import READOUT_ARMS, STRUCTURE_ARMS
from ..conditions import requirements_for
from ..config import (
    ConfigError,
    MemoryGateError,
    PROJECT_ROOT,
    Phase8Config,
    load_phase8_config,
    memory_preflight,
)
from ..registry import build_registry
from ..runner import CampaignRunner
from ..training.artifacts import TRAINING_ROOT
from ..training.gate import design_status
from ..training.loader import discover_artifact_directories
from .common import (
    NO_EXECUTION_NOTE,
    StageConfigurationError,
    StageRefusal,
    authorization_snapshot,
    collect_blockers,
    memory_snapshot,
    stage_envelope,
)


class CompositionError(RuntimeError):
    """The declared arms cannot be assembled without changing the design."""


@dataclass(frozen=True)
class ArmRoute:
    arm: str
    kind: str
    stepper_kind: str | None
    eta: float | None
    requires_structure: bool
    needs_readout: bool
    needs_agent: bool
    mirror: str | None
    trains: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "arm": self.arm,
            "kind": self.kind,
            "stepper_kind": self.stepper_kind,
            "eta": self.eta,
            "requires_structure": self.requires_structure,
            "needs_readout": self.needs_readout,
            "needs_agent": self.needs_agent,
            "mirror": self.mirror,
            "trains": list(self.trains),
        }


def _route(arm: str) -> ArmRoute:
    if arm == "floor":
        return ArmRoute(
            arm=arm,
            kind="floor",
            stepper_kind=None,
            eta=None,
            requires_structure=False,
            needs_readout=False,
            needs_agent=False,
            mirror=None,
            trains=("none",),
        )
    requirements = requirements_for(arm)
    if arm in CONVENTIONAL_ARMS:
        kind = "conventional"
    elif arm in NEURAL_ARMS:
        kind = "neural"
    else:  # pragma: no cover - the registry declares the twelve arms
        raise CompositionError(f"{arm!r} has no declared execution route")
    return ArmRoute(
        arm=arm,
        kind=kind,
        stepper_kind=requirements.stepper_kind,
        eta=requirements.eta,
        requires_structure=bool(requirements.requires_structure),
        needs_readout=arm in READOUT_ARMS,
        needs_agent=arm in CONVENTIONAL_ARMS,
        mirror=CONTROL_MIRRORS.get(arm),
        trains=tuple(requirements.trains),
    )


def arm_routes(config: Phase8Config) -> tuple[ArmRoute, ...]:
    registry = build_registry(config.conditions)
    return tuple(_route(arm) for arm in registry.evaluation_arms)


def verify_arm_routes(config: Phase8Config) -> dict:
    """Prove the twelve-arm partition before any runner is built."""
    registry = build_registry(config.conditions)
    expected = registry.evaluation_arms
    routes = arm_routes(config)
    by_arm = {route.arm: route for route in routes}

    checks: list[dict] = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    check(
        "registry.order",
        tuple(route.arm for route in routes) == tuple(expected),
        list(expected),
    )
    check("registry.exactly_once", len(by_arm) == len(routes) == len(expected))
    check(
        "registry.twelve_arms",
        len(expected) == len(ARM_ORDER) == 12,
        {"registry": list(expected), "dispatcher": list(ARM_ORDER)},
    )
    check(
        "dispatcher.parity",
        tuple(expected) == tuple(ARM_ORDER),
        {"registry": list(expected), "dispatcher": list(ARM_ORDER)},
    )
    check(
        "structure.arms",
        {arm for arm, route in by_arm.items() if route.requires_structure}
        == set(STRUCTURE_ARMS),
        sorted(STRUCTURE_ARMS),
    )
    for arm in ("A_prime", "C_prime"):
        route = by_arm[arm]
        check(f"{arm}.plastic_path", route.stepper_kind == "plastic", route.stepper_kind)
        check(f"{arm}.eta_zero", route.eta == 0.0, route.eta)
        check(f"{arm}.mirror", route.mirror == CONTROL_MIRRORS[arm], route.mirror)
    for arm in ("F", "F_beta", "F_init"):
        check(f"{arm}.readout", by_arm[arm].needs_readout is True)
    for arm in ("E", "E_full"):
        check(f"{arm}.conventional", by_arm[arm].kind == "conventional")
        check(f"{arm}.agent", by_arm[arm].needs_agent is True)
    for arm in ("B", "D"):
        check(f"{arm}.eta_positive", by_arm[arm].eta == 0.5, by_arm[arm].eta)
    check("floor.no_substrate", by_arm["floor"].kind == "floor")

    failed = [item for item in checks if not item["pass"]]
    if failed:
        raise CompositionError(
            "the arm composition disagrees with the declaration: "
            + ", ".join(item["name"] for item in failed)
        )
    return {
        "passed": True,
        "n_arms": len(routes),
        "arms": [route.arm for route in routes],
        "checks": checks,
        "routes": [route.as_dict() for route in routes],
    }


@dataclass(frozen=True)
class Composition:
    config: Phase8Config
    factory: CampaignFactory
    dispatcher: CampaignDispatcher
    routes: tuple[ArmRoute, ...]
    verification: dict

    def as_dict(self) -> dict:
        return {
            "arms": [route.arm for route in self.routes],
            "verification": dict(self.verification),
            "factory": self.factory.describe(),
            "dispatcher": self.dispatcher.describe(),
            "execution_authorized": False,
        }


def build_composition(
    config: Phase8Config,
    *,
    world: Any | None = None,
    graphs: CertifiedGraphSource | None = None,
    training: TrainingArtifacts | None = None,
    environment_factory: Callable[[], Any] | None = None,
    mapping_payload: Mapping[str, Any] | None = None,
    plasticity_payload: Mapping[str, Any] | None = None,
    frozen_inputs: Mapping[str, str] | None = None,
    failure_log: str | Path | None = None,
    input_hashes: Mapping[str, str] | None = None,
    training_seeds: Any | None = None,
    evaluation_seeds: Any | None = None,
) -> Composition:
    """Assemble the production objects; builds no graph and runs no episode."""
    verification = verify_arm_routes(config)
    factory = CampaignFactory(
        world=world,
        graphs=graphs,
        training=training,
        environment_factory=environment_factory,
        mapping_payload=mapping_payload,
        plasticity_payload=plasticity_payload,
        frozen_inputs=frozen_inputs,
        registry=build_registry(config.conditions),
    )
    dispatcher = CampaignDispatcher(
        factory,
        input_hashes=input_hashes,
        failure_log=failure_log,
        training_seeds=training_seeds,
        evaluation_seeds=evaluation_seeds,
    )
    return Composition(
        config=config,
        factory=factory,
        dispatcher=dispatcher,
        routes=arm_routes(config),
        verification=verification,
    )


def _artifact_inventory() -> dict:
    root = PROJECT_ROOT / TRAINING_ROOT
    directories = discover_artifact_directories(root)
    return {
        "root": root.as_posix(),
        "directories": len(directories),
        "keys": sorted(
            f"{path.parent.name}:{path.name}" for path in directories
        ),
        "verified": False,
        "note": "directory names only; no artifact is read or verified here",
    }


def preflight_report(
    config: Phase8Config,
    *,
    preflight: Callable[[float], dict] = memory_preflight,
) -> dict:
    """Read-only readiness report for the campaign composition root."""
    conformance = validate_campaign(config, strict=False)
    authorization = authorization_snapshot()
    design = design_status(config.campaign)
    memory = memory_snapshot(config, preflight=preflight)
    verification = verify_arm_routes(config)

    source = CertifiedGraphSource()
    certificates = source.inspect_all()
    certified = [entry for entry in certificates if entry.get("status") == "certified"]
    pilot_seed_graphs = {
        int(seed): int(seed) in source.required_seeds
        for seed in config.campaign.pilot_seeds
    }

    blockers = list(collect_blockers(config, preflight=preflight))
    if len(certified) != len(certificates):
        blockers.append(
            f"G3: {len(certificates) - len(certified)} certified graph(s) are not "
            "certified in the declared namespace"
        )
    if not design["resolved"]:
        blockers.append("B2: no campaign design is resolved, so no campaign plan exists")

    record = stage_envelope("campaign")
    record.update(
        {
            "conformance": {
                "checks_total": conformance["checks_total"],
                "checks_passed": conformance["checks_passed"],
                "conforms": conformance["conforms"],
                "failures": conformance["failures"],
            },
            "authorization": authorization,
            "design": design,
            "memory_preflight": memory,
            "composition": verification,
            "certified_graphs": {
                "root": source.root.as_posix(),
                "required_seeds": list(source.required_seeds),
                "certified": len(certified),
                "required": len(certificates),
                "fallback_to_biological_graph": False,
            },
            "pilot_seed_graphs": {
                "seeds": sorted(pilot_seed_graphs),
                "covered": pilot_seed_graphs,
                "note": (
                    "certification covers the campaign seeds only; a pilot run "
                    "that needs C/C' has no certified graph for pilot seeds"
                ),
            },
            "training_artifacts": _artifact_inventory(),
            "execution_ready": False,
            "execution_blockers": blockers,
            "note": NO_EXECUTION_NOTE,
        }
    )
    return record


def start_campaign(
    config: Phase8Config,
    base_dir: str | Path,
    run_id: str,
    *,
    composition: Composition | None = None,
    preflight: Callable[[float], dict] = memory_preflight,
    new_run_id: str | None = None,
    input_hashes: Mapping[str, Any] | None = None,
    integrity: Mapping[str, Any] | None = None,
    capture: Mapping[str, Any] | None = None,
    composition_kwargs: Mapping[str, Any] | None = None,
) -> CampaignRunner:
    """Refuse, or start the production campaign runner.

    The authorisation gate runs before composition is built, before a graph is
    loaded and before a run directory is created.
    """
    assert_campaign_authorized()
    assembled = composition or build_composition(
        config, **dict(composition_kwargs or {})
    )
    hashes = input_hashes if input_hashes is not None else assembled.factory.input_hashes()
    return CampaignRunner.start(
        config,
        base_dir,
        run_id,
        episode_runner=assembled.dispatcher,
        preflight=preflight,
        new_run_id=new_run_id,
        input_hashes=hashes,
        integrity=integrity,
        capture=capture,
    )


def resume_campaign(
    config: Phase8Config,
    run_dir: str | Path,
    *,
    composition: Composition | None = None,
    preflight: Callable[[float], dict] = memory_preflight,
    composition_kwargs: Mapping[str, Any] | None = None,
) -> CampaignRunner:
    """Refuse, or reopen an interrupted production campaign run."""
    assert_campaign_authorized()
    assembled = composition or build_composition(
        config, **dict(composition_kwargs or {})
    )
    return CampaignRunner.resume(
        config,
        run_dir,
        episode_runner=assembled.dispatcher,
        preflight=preflight,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2


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
        prog="campaign",
        description=(
            "Production composition root (REV4 §10.10): describe the assembled "
            "twelve-arm campaign; starting or resuming refuses."
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--start", action="store_true", help="refused while unapproved")
    parser.add_argument("--resume", default=None, help="run directory; refused while unapproved")
    parser.add_argument("--base-dir", default=None)
    parser.add_argument("--run-id", default="campaign")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load(args)
        if args.start or args.resume:
            payload = preflight_report(config)
            payload["command"] = "start" if args.start else "resume"
            try:
                if args.start:
                    base = args.base_dir or (
                        PROJECT_ROOT / config.campaign.results_root
                    )
                    start_campaign(config, base, args.run_id)
                else:
                    resume_campaign(config, Path(args.resume))
            except (
                CampaignNotAuthorized,
                StageRefusal,
                CompositionError,
                MemoryGateError,
            ) as error:
                payload["refused"] = True
                payload["reason"] = str(error)
                _emit(payload, args.pretty)
                return EXIT_REFUSED
            payload["refused"] = False
            _emit(payload, args.pretty)
            return EXIT_OK
        payload = preflight_report(config)
        payload["command"] = "describe"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, StageConfigurationError, CompositionError) as error:
        sys.stderr.write(f"campaign configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "ArmRoute",
    "Composition",
    "CompositionError",
    "arm_routes",
    "build_composition",
    "build_parser",
    "main",
    "preflight_report",
    "resume_campaign",
    "start_campaign",
    "verify_arm_routes",
]
