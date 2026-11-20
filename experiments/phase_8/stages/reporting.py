"""Final report and freeze stage for Phase 8 (REV4 §10.12).

SCIENTIFIC STATUS
    A report may only be produced from an analysed, complete campaign store.
    This module builds the **report record** and the **freeze record** and
    refuses to write either while the preconditions fail. It adds no claim of
    its own:

    * the readout claim is permitted only when the E1–E5 checklist says so;
    * every REV4 §11 limitation is restated verbatim in substance;
    * the §3.6.5 forbidden statements are scanned for, and a body containing
      one is not publishable;
    * the 37-file protected baseline is re-hashed and only non-README failures
      block a freeze (the README drift is pre-existing, REV4 §6.10);
    * the Phase 6 result is recorded unchanged and no Phase 6 artefact is read
      for modification.

    Nothing here approves the protocol, resolves U1-U18, resolves the G3
    deviation, or turns a missing analysis into a result. ``describe_report_stage``
    is read-only; the writers are guarded by :class:`StageRefusal`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from brain.banc_graph import sha256_file

from ..analysis import identity_check
from ..campaign.protocol import approval_status, protocol_identity, randomization_deviation
from ..campaign.status import run_status
from ..config import ConfigError, PROJECT_ROOT, Phase8Config, load_phase8_config
from ..manifest import load_manifest
from ..schema import SchemaError, utc_timestamp
from ..store import EpisodeStore, StoreError
from .common import (
    NO_EXECUTION_NOTE,
    StageConfigurationError,
    StageRefusal,
    authorization_snapshot,
    design_snapshot,
    stage_envelope,
    write_json,
)

REPORT_STAGE = "report"
REPORT_REV4_STEP = "10.12"

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2

INTEGRITY_BASELINE = PROJECT_ROOT / "experiments" / "phase_4h" / "baseline_integrity.json"

#: REV4 §3.6.5. Each entry is a forbidden claim, the condition under which the
#: wording would misrepresent the experiment, and a fixed match pattern.
FORBIDDEN_STATEMENTS = (
    {
        "id": "FS1",
        "match": "the connectome learned",
        "note": (
            "the connectome is frozen; only the readout changed, and readout "
            "training is not synaptic plasticity"
        ),
    },
    {
        "id": "FS2",
        "match": "plasticity improved performance",
        "note": (
            "F contains no plasticity; a plasticity claim belongs to B or D "
            "and needs the corresponding contrast"
        ),
    },
    {
        "id": "FS3",
        "match": "the readout succeeded",
        "note": (
            "forbidden when F-beta scores the same; that is a constant action, "
            "not a decoder"
        ),
    },
    {
        "id": "FS4",
        "match": "f beat the baseline",
        "note": (
            "only acceptable when the named baseline (A, F-beta or the floor) "
            "is stated; the scanner cannot certify that, so the wording must "
            "be rewritten"
        ),
    },
)

#: REV4 §11, restated. Every limitation must appear in a report.
LIMITATIONS = (
    {"id": "L1", "area": "biological model", "statement": "BANC v888 is an adult female brain + VNC; it lacks the lamina and ocellar ganglion."},
    {"id": "L2", "area": "biological model", "statement": "The neuron is a single-compartment LIF unit with declared parameters; there is no morphology, dendritic computation, receptor kinetics or short-term plasticity."},
    {"id": "L3", "area": "biological model", "statement": "Weights are min(5*count^0.75, 300) pA from structural synapse counts; they are not conductances or measured synaptic strengths."},
    {"id": "L4", "area": "biological model", "statement": "683,100 of 1,535,710 edges (44.48%) have a verified transmitter sign; 852,610 are inert, so a neuron's sign is a coarse two-class proxy."},
    {"id": "L5", "area": "biological model", "statement": "65,292 of 172,433 neurons carry a verified transmitter annotation; 107,141 do not."},
    {"id": "L6", "area": "biological model", "statement": "24,320 nodes are isolated at threshold 5."},
    {"id": "L7", "area": "biological model", "statement": "Propagation delay is uniform at 1 ms; the delay-matched coincidence rule is a convention."},
    {"id": "L8", "area": "biological model", "statement": "One capped edge produces at most 4.7 mV; four coincident edges are needed to fire, so recruitment is synchronicity-gated, not rate-gated."},
    {"id": "L9", "area": "sensory interface", "statement": "7 of 14 game-state features have a mapped population; player lane, speed, jumping, rolling, coin presence, coin lane and coin distance are unmapped."},
    {"id": "L10", "area": "sensory interface", "statement": "The feature-to-population assignment is the Phase 4H.4 hypothesis/convention, not a measured sensory pathway."},
    {"id": "L11", "area": "sensory interface", "statement": "Distances are normalised game-world units, not metres."},
    {"id": "L12", "area": "sensory interface", "statement": "The drive is a fixed 200 pA per active feature with zero-order hold and no adaptation; Phase 7 injected 13,476.67 pA while 71 of 232 targeted neurons fired."},
    {"id": "L13", "area": "motor interface", "statement": "LEFT, RIGHT and JUMP are decoder labels from published effector annotations, not identified biological motor commands; 391 of 805 motor neurons are assigned and 414 are not."},
    {"id": "L14", "area": "motor interface", "statement": "ROLL and DUCK have no motor population; they are never inferred or proxied and execute NO_ACTION with an explicit reason."},
    {"id": "L15", "area": "motor interface", "statement": "The decoder is a fixed threshold rule (activation 0.20, release 0.10, at least 3 active and 5 spikes, 50 ms half-open window); the numbers were declared, not fitted."},
    {"id": "L16", "area": "task and environment", "statement": "The game is a synthetic 2D endless runner; it is not fly behaviour, a naturalistic stimulus or a biological measurement."},
    {"id": "L17", "area": "task and environment", "statement": "Reward is synthetic: coin +1, collision -1, survival +0.01/step, obstacle reward 0.0 and inert."},
    {"id": "L18", "area": "task and environment", "statement": "The observation contains only currently visible spawned objects; there is no future-obstacle information and none is inferred."},
    {"id": "L19", "area": "task and environment", "statement": "max_steps 900 is an administrative cap; the outcome is min(observed_updates, 900), cap-reaching rows are truncated and their true termination time is unknown."},
    {"id": "L20", "area": "task and environment", "statement": "Game and neural clocks are bridged by round(game_ms / 0.5); the residual is bounded at half a neural step but the clocks are not physically coupled."},
    {"id": "L21", "area": "design", "statement": "The primary outcome has one degree of freedom per seed at N = 16 (N = 10 only as the fallback); the attainable two-sided p is 2/65,536 = 0.0000305, and this design can detect large effects only."},
    {"id": "L22", "area": "design", "statement": "sigma = 60 is an assumption from a 3-seed pilot (sd 67.3); at df = 2 the 80% upper limit is about 2.1x the point estimate, which is why N = 16 is primary and N = 10 needs sigma_max <= 112.87 to be defended."},
    {"id": "L23", "area": "design", "statement": "The null uses target exchange: degrees, signs, identities, the weight multiset and the per-source profile are preserved, component structure is not; C is not a pure wiring null and the diagnostics are not a proof of mixing."},
    {"id": "L24", "area": "design", "statement": "E-matched is not a matched control for plasticity because it assigns credit directly to its own parameters; E comparisons are explanatory."},
    {"id": "L25", "area": "design", "statement": "F is expected to fail if the motor populations are silent; F-beta detects a constant policy, and while the motor populations are silent no neural-learning claim of any strength is permitted."},
    {"id": "L26", "area": "design", "statement": "Readout training is not synaptic plasticity and must never be summarised as such."},
    {"id": "L27", "area": "design", "statement": "The Phase 7 floor may make the confirmatory family uninformative by construction; that possibility was preregistered before the data."},
    {"id": "L28", "area": "design", "statement": "The Phase 6 confirmatory negative result stands unchanged; Phase 8 information measures are descriptive and cannot revise it."},
    {"id": "L29", "area": "design", "statement": "The attainable-p floor belongs to the design and N, not the data: no contrast can be reported below adjusted 8/65,536 (m = 4) or 6/65,536 (m = 3) at N = 16."},
    {"id": "L30", "area": "design", "statement": "A-prime, C-prime and F-beta are control arms with no claim of their own; the no-action floor is a substrate-free game-side control and never a neural arm."},
    {"id": "L31", "area": "design", "statement": "The motor-driven/bias-driven classification is a counterfactual on a frozen model; it does not establish biological meaning or causality in the fly."},
    {"id": "L32", "area": "design", "statement": "The exact sign-flip test assumes exchangeability under sign reversal; pairing removes shared environment and network draws but does not guarantee the assumption."},
    {"id": "L33", "area": "design", "statement": "A 3-seed pilot gives an unstable sigma and cannot certify N = 10; the N decision uses an upper confidence limit, is made before the campaign, and a limit above 142.8 requires N above 16."},
)


# ---------------------------------------------------------------------------
# §3.6.5 scanner
# ---------------------------------------------------------------------------


def scan_for_forbidden_statements(text: str) -> dict:
    """Find every §3.6.5 forbidden wording, case-insensitively.

    The scanner is deliberately literal: a disclaimer that repeats the
    forbidden wording still matches. Report bodies must avoid the wording
    rather than quote it.
    """
    if not isinstance(text, str):
        raise StageConfigurationError("the report body must be a string")
    lowered = text.lower()
    hits: list[dict] = []
    for item in FORBIDDEN_STATEMENTS:
        pattern = str(item["match"]).lower()
        start = 0
        while True:
            index = lowered.find(pattern, start)
            if index < 0:
                break
            line = lowered.count("\n", 0, index) + 1
            line_start = lowered.rfind("\n", 0, index) + 1
            line_end = lowered.find("\n", index)
            if line_end < 0:
                line_end = len(text)
            hits.append(
                {
                    "id": item["id"],
                    "line": line,
                    "column": index - line_start + 1,
                    "context": text[line_start:line_end].strip(),
                    "note": item["note"],
                }
            )
            start = index + len(pattern)
    return {
        "scanned": True,
        "characters": len(text),
        "hits": hits,
        "clean": not hits,
    }


# ---------------------------------------------------------------------------
# integrity baseline
# ---------------------------------------------------------------------------


def check_integrity(
    baseline: str | Path | None = None,
    *,
    root: str | Path = PROJECT_ROOT,
) -> dict:
    """Re-hash the protected baseline read-only.

    ``README.md`` is reported separately as a known pre-existing drift; only a
    non-README failure blocks a freeze (REV4 §6.10, §10.12).
    """
    source = Path(baseline) if baseline is not None else INTEGRITY_BASELINE
    if not source.is_file():
        raise StageConfigurationError(f"integrity baseline not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StageConfigurationError(
            f"{source} is not valid JSON: {error}"
        ) from None
    if not isinstance(payload, Mapping) or not payload:
        raise StageConfigurationError(f"{source} must be a non-empty mapping")

    base = Path(root)
    failures: list[dict] = []
    for relative in sorted(payload):
        expected = payload[relative]
        path = base / relative
        if not path.is_file():
            failures.append({"path": relative, "reason": "missing"})
            continue
        actual = sha256_file(path)
        expected_digest = (
            expected.get("sha256") if isinstance(expected, Mapping) else None
        )
        if actual != expected_digest:
            failures.append(
                {
                    "path": relative,
                    "reason": "sha256 mismatch",
                    "expected_sha256": expected_digest,
                    "actual_sha256": actual,
                }
            )
    non_readme = [item for item in failures if str(item["path"]) != "README.md"]
    readme = [item for item in failures if str(item["path"]) == "README.md"]
    try:
        baseline_label = source.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:  # pragma: no cover - an external baseline path
        baseline_label = source.resolve().as_posix()
    return {
        "checked": True,
        "baseline": baseline_label,
        "protected_total": len(payload),
        "matching": len(payload) - len(failures),
        "failures": failures,
        "non_readme_failures": non_readme,
        "readme_failure": readme[0] if readme else None,
        "pass": not non_readme,
        "note": (
            "the README.md pin drift is a reported pre-existing condition and "
            "is not re-litigated; only non-README failures block a freeze"
        ),
    }


# ---------------------------------------------------------------------------
# report construction
# ---------------------------------------------------------------------------


def _read_rows(run_dir: Path, config: Phase8Config) -> tuple[list[dict], str | None]:
    try:
        store = EpisodeStore(
            run_dir, filename=config.campaign.episode_store_name, create=False
        )
        return store.rows(), None
    except StoreError as error:
        return [], str(error)


def _manifest_facts(run_dir: Path, config: Phase8Config) -> dict:
    path = run_dir / config.campaign.run_manifest_name
    if not path.is_file():
        return {"present": False, "path": path.as_posix(), "error": "no manifest"}
    try:
        manifest = load_manifest(path)
    except (SchemaError, FileNotFoundError) as error:
        return {"present": False, "path": path.as_posix(), "error": str(error)}
    return {
        "present": True,
        "path": path.as_posix(),
        "run_id": manifest["run_id"],
        "created_at": manifest["created_at"],
        "protocol": manifest["protocol"],
        "config_hashes": dict(manifest["config_hashes"]),
        "memory_preflight": dict(manifest["memory_preflight"]),
        "integrity": dict(manifest["integrity"]),
        "input_hashes": dict(manifest["input_hashes"]),
    }


def build_final_report(
    run_dir: str | Path,
    config: Phase8Config,
    *,
    analysis: Mapping[str, Any] | None = None,
    report_markdown: str | None = None,
    integrity: Mapping[str, Any] | None = None,
    phase6_unchanged: bool = True,
    created_at: datetime | None = None,
) -> dict:
    """Assemble the §10.12 report record. It writes nothing."""
    directory = Path(run_dir)
    status = run_status(directory, config=config)
    manifest = _manifest_facts(directory, config)
    rows, store_error = _read_rows(directory, config)
    seeds = sorted({int(row["seed"]) for row in rows})

    identity = {}
    if rows:
        identity = {
            "A_prime": identity_check(
                rows,
                control="A_prime",
                target="A",
                seeds=seeds,
                episodes_per_seed=config.campaign.episodes_per_seed,
            ),
            "C_prime": identity_check(
                rows,
                control="C_prime",
                target="C",
                seeds=seeds,
                episodes_per_seed=config.campaign.episodes_per_seed,
            ),
        }

    checklist = (
        analysis.get("checklist")
        if isinstance(analysis, Mapping)
        else None
    )
    readout_allowed = bool(
        isinstance(checklist, Mapping)
        and checklist.get("decoding_claim_permitted") is True
    )
    analysis_block = {
        "provided": isinstance(analysis, Mapping),
        "blocked_reason": (
            None
            if isinstance(analysis, Mapping)
            else (
                "the 10.11 analysis needs a resolved design (U7) and a recorded "
                "Holm family size (U14); neither is defaulted here"
            )
        ),
        "checklist": checklist,
        "readout_claim_permitted": readout_allowed,
        "permitted_statements": (
            list(analysis.get("permitted_statements", []))
            if isinstance(analysis, Mapping)
            else []
        ),
        "confirmatory": (
            dict(analysis.get("confirmatory", {}))
            if isinstance(analysis, Mapping)
            else None
        ),
        "secondary": (
            list(analysis.get("secondary", []))
            if isinstance(analysis, Mapping)
            else None
        ),
        "warnings": (
            list(analysis.get("warnings", []))
            if isinstance(analysis, Mapping)
            else []
        ),
    }

    forbidden = (
        scan_for_forbidden_statements(report_markdown)
        if report_markdown is not None
        else {
            "scanned": False,
            "characters": None,
            "hits": [],
            "clean": None,
            "note": "no report body was supplied; a freeze needs a scanned, clean body",
        }
    )
    integrity_block = (
        dict(integrity)
        if isinstance(integrity, Mapping)
        else {
            "checked": False,
            "baseline": None,
            "non_readme_failures": [],
            "pass": False,
            "note": (
                "the 37-file baseline was not checked; a report may not be "
                "published or frozen until it is"
            ),
        }
    )

    coverage = {
        "rows": len(rows),
        "seeds": seeds,
        "per_arm": status.get("per_arm", {}),
        "failed_rows": status.get("failed_rows"),
        "training_rows": status.get("training_rows"),
        "store_error": store_error,
    }

    readout = {
        "claim_allowed": readout_allowed,
        "reason": (
            "E1-E5 all pass (REV4 §3.6.4)"
            if readout_allowed
            else (
                "E1-E5 do not all pass, are not evaluable, or no analysis was "
                "supplied; no motor-decoding claim may be made"
            )
        ),
    }

    publishable = bool(
        status.get("complete") is True
        and len(rows) > 0
        and isinstance(analysis, Mapping)
        and forbidden.get("clean") is True
        and integrity_block.get("checked") is True
        and integrity_block.get("pass") is True
        and bool(phase6_unchanged)
    )
    reasons: list[str] = []
    if status.get("complete") is not True:
        reasons.append("the run is not complete")
    if not rows:
        reasons.append("the store holds no rows")
    if not isinstance(analysis, Mapping):
        reasons.append("no 10.11 analysis was supplied")
    if forbidden.get("clean") is not True:
        reasons.append("no clean scanned report body was supplied")
    if integrity_block.get("checked") is not True:
        reasons.append("the protected integrity baseline was not checked")
    elif integrity_block.get("pass") is not True:
        reasons.append("the protected integrity baseline has non-README failures")
    if not phase6_unchanged:
        reasons.append("the Phase 6 result is not recorded unchanged")

    record = stage_envelope(
        REPORT_STAGE,
        executed=False,
        evidence_kind="analysis",
    )
    record.update(
        {
            "created_at": utc_timestamp(created_at),
            "run_dir": directory.as_posix(),
            "protocol": protocol_identity(),
            "approval": approval_status(),
            "authorization": authorization_snapshot(),
            "randomization_deviation": randomization_deviation(),
            "design": design_snapshot(config),
            "config_hashes": dict(config.hashes),
            "manifest": manifest,
            "run_status": status,
            "coverage": coverage,
            "identity_controls": identity,
            "analysis": analysis_block,
            "readout_claim": readout,
            "forbidden_scan": forbidden,
            "integrity": integrity_block,
            "limitations": list(LIMITATIONS),
            "phase_6": {
                "result_unchanged": bool(phase6_unchanged),
                "artefacts_modified": False,
                "note": (
                    "Phase 6's confirmatory negative stands; Phase 8 "
                    "information analyses are descriptive"
                ),
            },
            "g3_deviation": randomization_deviation(),
            "publishable": publishable,
            "publish_blockers": reasons,
            "note": (
                "report record only; no result is asserted by this record and "
                "no report file is written unless publishable"
            ),
        }
    )
    return record


def write_final_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    """Write the report once, refusing an unpublishable record."""
    if not isinstance(report, Mapping) or report.get("publishable") is not True:
        raise StageRefusal(
            REPORT_STAGE,
            [
                "the report is not publishable: "
                + "; ".join(report.get("publish_blockers", []) or ["unknown reason"])
            ],
        )
    return write_json(path, report)


# ---------------------------------------------------------------------------
# freeze record
# ---------------------------------------------------------------------------


def freeze_record(
    run_dir: str | Path,
    config: Phase8Config,
    *,
    report: Mapping[str, Any],
    created_at: datetime | None = None,
) -> dict:
    """Inventory the frozen artefacts. Building the record writes nothing."""
    directory = Path(run_dir)
    artefacts: dict[str, Any] = {}
    for name, filename in (
        (config.campaign.run_manifest_name, config.campaign.run_manifest_name),
        (config.campaign.episode_store_name, config.campaign.episode_store_name),
    ):
        path = directory / filename
        artefacts[name] = {
            "path": path.as_posix(),
            "present": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else None,
        }

    integrity_block = report.get("integrity") or (report.get("report") or {}).get("integrity")
    integrity_block = integrity_block if isinstance(integrity_block, Mapping) else {
        "checked": False,
        "pass": False,
    }
    eligible = bool(
        report.get("publishable") is True
        and integrity_block.get("checked") is True
        and integrity_block.get("pass") is True
    )
    reasons: list[str] = []
    if report.get("publishable") is not True:
        reasons.extend(report.get("publish_blockers") or ["report not publishable"])
    if integrity_block.get("checked") is not True:
        reasons.append("integrity not checked")
    elif integrity_block.get("pass") is not True:
        reasons.append("non-README integrity failures")
    return {
        "record_kind": "phase_8_freeze_record",
        "stage": REPORT_STAGE,
        "rev4_step": REPORT_REV4_STEP,
        "created_at": utc_timestamp(created_at),
        "run_dir": directory.as_posix(),
        "protocol": protocol_identity(),
        "approval": approval_status(),
        "config_hashes": dict(config.hashes),
        "artefacts": artefacts,
        "publishable": bool(report.get("publishable")),
        "eligible_to_freeze": eligible,
        "frozen": False,
        "blockers": reasons,
        "note": (
            "a freeze record is a file inventory; it approves no protocol and "
            "asserts no result. Frozen stays false until every precondition holds"
        ),
    }


def write_freeze_record(path: str | Path, record: Mapping[str, Any]) -> Path:
    """Write the freeze record once, refusing an ineligible record."""
    if not isinstance(record, Mapping) or record.get("eligible_to_freeze") is not True:
        blockers = (
            record.get("blockers")
            if isinstance(record, Mapping)
            else ["record is not a mapping"]
        )
        raise StageRefusal(
            REPORT_STAGE,
            ["not eligible to freeze: " + "; ".join(blockers or ["unknown reason"])],
        )
    return write_json(path, record)


# ---------------------------------------------------------------------------
# read-only description
# ---------------------------------------------------------------------------


def describe_report_stage(
    config: Phase8Config,
    *,
    run_dir: str | Path | None = None,
) -> dict:
    record = stage_envelope(REPORT_STAGE)
    record.update(
        {
            "requirements": {
                "analysis_supplied": False,
                "analysis_source": "the 10.11 analysis of the same store",
                "integrity_baseline": INTEGRITY_BASELINE.relative_to(
                    PROJECT_ROOT
                ).as_posix(),
                "integrity_rule": (
                    "36/37 non-README protected files must match; the README "
                    "drift is reported as pre-existing"
                ),
                "forbidden_statements": [
                    {"id": item["id"], "note": item["note"]}
                    for item in FORBIDDEN_STATEMENTS
                ],
                "limitations_count": len(LIMITATIONS),
                "readout_claim_rule": (
                    "permitted only when E1-E5 all pass; F-beta equality is "
                    "never a decoder"
                ),
                "phase_6": "result recorded unchanged; artefacts untouched",
            },
            "authorization": authorization_snapshot(),
            "design": design_snapshot(config),
            "g3_deviation": randomization_deviation(),
            "run_status": (
                run_status(Path(run_dir), config=config) if run_dir else None
            ),
            "publishable": False,
            "note": NO_EXECUTION_NOTE,
        }
    )
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
        prog="report",
        description=(
            "Phase 8 §10.12 report and freeze stage. A report is publishable "
            "only from a complete, analysed store with a clean body and a "
            "passing 36/37 non-README integrity check."
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    for name in ("--environment", "--campaign", "--conditions"):
        parser.add_argument(name, dest=name[2:], default=None)
    parser.add_argument("--describe", action="store_true", help="read-only stage status")
    parser.add_argument("--report", default=None, help="run directory to report on")
    parser.add_argument("--freeze", default=None, help="run directory to freeze")
    parser.add_argument("--markdown", default=None, help="report body to scan for §3.6.5")
    parser.add_argument("--analysis", default=None, help="analysis JSON from 10.11")
    parser.add_argument(
        "--integrity",
        action="store_true",
        help="re-hash the 37-file protected baseline",
    )
    parser.add_argument("--out", default=None, help="write the record once if eligible")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load(args)
        integrity = check_integrity() if args.integrity else None
        analysis = None
        if args.analysis:
            try:
                analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                sys.stderr.write(f"report cannot read the analysis: {error}\n")
                return EXIT_INCOMPLETE
            if not isinstance(analysis, Mapping):
                sys.stderr.write("the analysis file must contain a JSON object\n")
                return EXIT_INCOMPLETE
        markdown = (
            Path(args.markdown).read_text(encoding="utf-8")
            if args.markdown
            else None
        )

        if args.report or args.freeze:
            run_dir = args.report or args.freeze
            report = build_final_report(
                run_dir,
                config,
                analysis=analysis,
                report_markdown=markdown,
                integrity=integrity,
            )
            if args.freeze:
                record = freeze_record(run_dir, config, report=report)
                payload = {"command": "freeze", "report": report, "freeze": record}
                if args.out:
                    try:
                        write_freeze_record(args.out, record)
                    except StageRefusal as error:
                        payload["refused"] = True
                        payload["reason"] = str(error)
                        _emit(payload, args.pretty)
                        return EXIT_REFUSED
                _emit(payload, args.pretty)
                return EXIT_OK if record["eligible_to_freeze"] else EXIT_INCOMPLETE

            payload = {"command": "report", "report": report}
            if args.out:
                try:
                    write_final_report(args.out, report)
                except StageRefusal as error:
                    payload["refused"] = True
                    payload["reason"] = str(error)
                    _emit(payload, args.pretty)
                    return EXIT_REFUSED
            _emit(payload, args.pretty)
            return EXIT_OK if report["publishable"] else EXIT_INCOMPLETE

        payload = describe_report_stage(config)
        payload["command"] = "describe"
        _emit(payload, args.pretty)
        return EXIT_OK
    except (ConfigError, StageConfigurationError) as error:
        sys.stderr.write(f"report stage configuration error: {error}\n")
        return EXIT_INCOMPLETE


__all__ = [
    "FORBIDDEN_STATEMENTS",
    "INTEGRITY_BASELINE",
    "LIMITATIONS",
    "REPORT_REV4_STEP",
    "REPORT_STAGE",
    "build_final_report",
    "check_integrity",
    "describe_report_stage",
    "freeze_record",
    "main",
    "scan_for_forbidden_statements",
    "write_final_report",
    "write_freeze_record",
]
