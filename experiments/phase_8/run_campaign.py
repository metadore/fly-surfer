"""Phase 8 campaign entry point — read-only checks and a refusing start.

SCIENTIFIC STATUS
    Recorded owner decision D1 approves REV4 §12 and U1-U18 as written, but the
    certified G3 random graphs still carry a recorded §9.3 memory-gate deviation
    (B7) and the campaign design is unresolved. This entry point therefore
    cannot start a campaign: ``start`` and ``resume`` collect the blockers, call
    :func:`~experiments.phase_8.campaign.assert_campaign_authorized` and exit
    with code 2. No game episode, training run, pilot or confirmatory episode is
    executed by any subcommand.

The read-only subcommands exist so that the state of the configuration, the
seed assignment, the certified graphs and an interrupted run directory can be
inspected without writing anything:

* ``check``  — REV4 conformance, approval state, G3 deviation, memory gate,
  certified-graph certificates;
* ``seeds``  — the declared stream derivation and one seed's plan per arm;
* ``graphs`` — certificate and digest of every required random graph;
* ``status`` — manifest, store, missing/unexpected keys, configuration drift.

Exit codes: 0 success, 1 inconclusive/incomplete, 2 refused (no authorisation).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .campaign import (
    CampaignNotAuthorized,
    CampaignProtocolError,
    CertifiedGraphSource,
    approval_status,
    assert_campaign_authorized,
    protocol_identity,
    run_status,
    validate_campaign,
)
from .campaign.protocol import randomization_deviation
from .config import ConfigError, load_phase8_config, memory_preflight
from .seeds import (
    CONDITION_IDS,
    FLOOR_ID,
    describe_derivation,
    environment_seed,
    seed_plan,
)

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2

NO_EXECUTION_NOTE = (
    "this subcommand does not run any game episode, training run, pilot or "
    "confirmatory episode"
)


def _emit(payload: dict, pretty: bool) -> None:
    sys.stdout.write(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True, ensure_ascii=True)
        + "\n"
    )


def _load(args: argparse.Namespace):
    return load_phase8_config(
        environment_path=args.environment,
        campaign_path=args.campaign,
        conditions_path=args.conditions,
    )


def _graph_summary() -> dict:
    source = CertifiedGraphSource()
    entries = source.inspect_all()
    certified = [entry for entry in entries if entry.get("status") == "certified"]
    refused = [
        entry for entry in entries if entry.get("status") not in ("certified",)
    ]
    return {
        "required_seeds": list(source.required_seeds),
        "required": len(entries),
        "certified": len(certified),
        "not_certified": len(refused),
        "entries": entries,
        "fallback_to_biological_graph": False,
        "g3_note": (
            "certified under a recorded §9.3 memory-gate deviation; G3 is not "
            "complete and the graphs may not be used for data collection"
        ),
    }


# ---------------------------------------------------------------------------
# read-only subcommands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    config = _load(args)
    report = validate_campaign(config, strict=False)
    gate = memory_preflight(config.campaign.memory_gate_gb)
    graphs = _graph_summary()
    approval = report["approval"]
    deviation = report["randomization_deviation"]
    execution_blockers: list[str] = []
    if not approval["approved"]:
        execution_blockers.append(
            "B1: no valid recorded owner approval of §12/U1-U18"
        )
    if deviation.get("status") != "compliant":
        execution_blockers.append(
            "B7: the G3 §9.3 memory-gate deviation is unresolved"
        )
    if not report["design_resolved"]:
        execution_blockers.append(
            "B2: design.n_seeds_selected is null until the 10.8 pilot decision (U7)"
        )
    payload = {
        "command": "check",
        "protocol": report["protocol"],
        "approval": approval,
        "randomization_deviation": deviation,
        "config_files": config.hashes,
        "design_resolved": report["design_resolved"],
        "n_seeds_selected": report["n_seeds_selected"],
        "conformance": {
            "checks_total": report["checks_total"],
            "checks_passed": report["checks_passed"],
            "conforms": report["conforms"],
            "failures": report["failures"],
        },
        "memory_preflight": gate,
        "certified_graphs": graphs,
        "executable": False,
        "execution_blockers": execution_blockers,
        "note": NO_EXECUTION_NOTE,
    }
    _emit(payload, args.pretty)
    ok = (
        report["conforms"]
        and gate["passed"]
        and graphs["not_certified"] == 0
    )
    return EXIT_OK if ok else EXIT_INCOMPLETE


def cmd_seeds(args: argparse.Namespace) -> int:
    config = _load(args)
    seed = int(args.seed)
    if seed not in config.campaign.campaign_seeds:
        sys.stderr.write(
            f"seed {seed} is not a declared campaign seed; "
            f"declared: {list(config.campaign.campaign_seeds)}\n"
        )
        return EXIT_INCOMPLETE
    master = config.campaign.master_seed
    plans = {arm: seed_plan(master, arm, seed) for arm in CONDITION_IDS}
    paired = int(environment_seed(master, seed, 0))
    plans[FLOOR_ID] = {
        "environment": paired,
        "network": None,
        "learning": None,
        "structure": None,
    }
    payload = {
        "command": "seeds",
        "master_seed": master,
        "campaign_seed": seed,
        "derivation": describe_derivation(master),
        "plans": {
            arm: {
                "environment": plan["environment"],
                "network": plan["network"],
                "learning": plan["learning"],
                "structure": plan["structure"],
            }
            for arm, plan in plans.items()
        },
        "shared_checks": {
            "environment_paired_across_arms": len(
                {plan["environment"] for plan in plans.values()}
            )
            == 1,
            "structure_shared_by_C_D_Cprime": len(
                {
                    plans["C"]["structure"],
                    plans["D"]["structure"],
                    plans["C_prime"]["structure"],
                }
            )
            == 1,
            "floor_has_no_neural_stream": plans[FLOOR_ID]["network"] is None,
        },
        "note": NO_EXECUTION_NOTE,
    }
    _emit(payload, args.pretty)
    return EXIT_OK


def cmd_graphs(args: argparse.Namespace) -> int:
    source = CertifiedGraphSource()
    if args.seed is not None:
        seed = int(args.seed)
        if args.verify:
            try:
                certified = source.load(seed)
            except Exception as error:  # GraphSelectionError and certification
                _emit(
                    {
                        "command": "graphs",
                        "seed": seed,
                        "verified": False,
                        "error": f"{type(error).__name__}: {error}",
                        "note": NO_EXECUTION_NOTE,
                    },
                    args.pretty,
                )
                return EXIT_INCOMPLETE
            _emit(
                {
                    "command": "graphs",
                    "seed": seed,
                    "verified": True,
                    "record": certified.describe(),
                    "note": NO_EXECUTION_NOTE,
                },
                args.pretty,
            )
            return EXIT_OK
        entry = source.inspect(seed)
        _emit(
            {
                "command": "graphs",
                "seed": seed,
                "verified": False,
                "certificate": entry,
                "note": NO_EXECUTION_NOTE,
            },
            args.pretty,
        )
        return EXIT_OK if entry.get("status") == "certified" else EXIT_INCOMPLETE

    summary = _graph_summary()
    summary["command"] = "graphs"
    summary["note"] = NO_EXECUTION_NOTE
    _emit(summary, args.pretty)
    return EXIT_OK if summary["not_certified"] == 0 else EXIT_INCOMPLETE


def cmd_status(args: argparse.Namespace) -> int:
    config = _load(args)
    report = run_status(Path(args.run_dir), config=config)
    report["command"] = "status"
    report["note"] = NO_EXECUTION_NOTE
    _emit(report, args.pretty)
    return EXIT_OK if report["complete"] else EXIT_INCOMPLETE


# ---------------------------------------------------------------------------
# refusing subcommands
# ---------------------------------------------------------------------------


def _refusal_payload(command: str, args: argparse.Namespace) -> dict:
    payload: dict[str, Any] = {
        "command": command,
        "authorized": False,
        "executed": False,
        "episodes_run": 0,
        "rows_written": 0,
        "note": NO_EXECUTION_NOTE,
    }
    try:
        config = _load(args)
        report = validate_campaign(config, strict=False)
        payload["design_resolved"] = report["design_resolved"]
        payload["conformance"] = {
            "checks_total": report["checks_total"],
            "checks_passed": report["checks_passed"],
            "conforms": report["conforms"],
            "failures": [entry["name"] for entry in report["failures"]],
        }
        payload["memory_preflight"] = memory_preflight(
            config.campaign.memory_gate_gb
        )
        payload["certified_graphs"] = {
            "required": len(CertifiedGraphSource().required_seeds),
            "root": CertifiedGraphSource().root.as_posix(),
        }
        payload["results_root"] = config.campaign.results_root
    except ConfigError as error:
        payload["configuration_error"] = str(error)
    payload["approval"] = approval_status()
    payload["protocol"] = protocol_identity()
    payload["randomization_deviation"] = randomization_deviation()
    run_id = getattr(args, "run_id", None)
    if run_id is not None:
        payload["requested_run_id"] = run_id
    run_dir = getattr(args, "run_dir", None)
    if run_dir is not None:
        payload["requested_run_dir"] = str(run_dir)
    return payload


def _refuse(command: str, args: argparse.Namespace) -> int:
    payload = _refusal_payload(command, args)
    try:
        assert_campaign_authorized()
    except CampaignNotAuthorized as error:
        payload["refused"] = True
        payload["reason"] = str(error)
    except Exception as error:  # pragma: no cover - the gate must raise its own type
        payload["refused"] = True
        payload["reason"] = f"{type(error).__name__}: {error}"
    else:  # pragma: no cover - defensive; the gate always raises
        payload["refused"] = False
        payload["reason"] = (
            "the authorisation gate did not refuse; review before any use"
        )
    _emit(payload, args.pretty)
    return EXIT_REFUSED


def cmd_start(args: argparse.Namespace) -> int:
    return _refuse("start", args)


def cmd_resume(args: argparse.Namespace) -> int:
    return _refuse("resume", args)


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_campaign.py",
        description=(
            "Phase 8 campaign entry point. Read-only checks are available; "
            "start and resume always refuse while REV4 §12 is unapproved."
        ),
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(
            name,
            dest=name[2:],
            default=None,
            help=f"override the {name[2:]} configuration path",
        )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate configuration against REV4")
    check.set_defaults(func=cmd_check)

    seeds = sub.add_parser("seeds", help="show the seed derivation for one seed")
    seeds.add_argument("--seed", type=int, default=1)
    seeds.set_defaults(func=cmd_seeds)

    graphs = sub.add_parser("graphs", help="inspect certified random graphs")
    graphs.add_argument("--seed", type=int, default=None)
    graphs.add_argument(
        "--verify",
        action="store_true",
        help="fully load and verify one graph (requires --seed)",
    )
    graphs.set_defaults(func=cmd_graphs)

    status = sub.add_parser("status", help="read a run directory without writing")
    status.add_argument("run_dir")
    status.set_defaults(func=cmd_status)

    start = sub.add_parser("start", help="refused while the protocol is unapproved")
    start.add_argument("--run-id", default=None)
    start.set_defaults(func=cmd_start)

    resume = sub.add_parser("resume", help="refused while the protocol is unapproved")
    resume.add_argument("run_dir")
    resume.set_defaults(func=cmd_resume)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "graphs" and args.verify and args.seed is None:
        parser.error("--verify requires --seed")
    try:
        return int(args.func(args))
    except CampaignProtocolError as error:
        sys.stderr.write(f"protocol conformance failed: {error}\n")
        return EXIT_INCOMPLETE
    except ConfigError as error:
        sys.stderr.write(f"configuration error: {error}\n")
        return EXIT_INCOMPLETE


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
