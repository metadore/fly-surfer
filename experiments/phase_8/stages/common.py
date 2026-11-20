"""Shared stage plumbing: refusals, snapshots, envelopes and the pilot driver.

SCIENTIFIC STATUS
    Nothing here decides anything scientific. The module centralises the facts
    every stage must report unchanged — approval, design, G3 deviation, memory —
    and the two ways a stage may refuse:

    * authorisation: :func:`..campaign.protocol.assert_stage_authorized` is
      applied per stage. The campaign-wide gate refuses while any recorded
      approval is missing or any independent gate (notably B7, the G3
      deviation) is open; only the exact Pilot 1 grid may pass B7 under D2.
      Nothing here wraps or bypasses that gate;
    * missing inputs: :class:`StageRefusal` names what a *later* stage lacks.

    :func:`drive_pilot` is a small append-only driver for the two pilots. It is
    gated per stage by :func:`..campaign.protocol.assert_stage_authorized`
    unless it is explicitly constructed as a ``synthetic_fixture``, in which
    case it refuses the real Phase 8 results root and stamps every row
    ``synthetic_fixture``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ..campaign.protocol import (
    approval_status,
    assert_campaign_authorized,
    assert_stage_authorized,
    protocol_identity,
    randomization_deviation,
    stage_authorization,
)
from ..config import (
    MemoryGateError,
    PROJECT_ROOT,
    Phase8Config,
    memory_preflight,
)
from ..manifest import build_manifest, write_manifest
from ..schema import validate_episode_row
from ..seeds import environment_seed, seed_plan
from ..store import EpisodeStore, resolve_run_directory
from ..training.gate import design_status

#: Stage -> the REV4 step it implements. Used in every emitted record.
STAGE_IDS = {
    "pilot1": {"rev4_step": "10.3", "title": "Pilot 1 — A viability"},
    "training": {"rev4_step": "10.5/10.9", "title": "F/Fβ and E training"},
    "campaign": {"rev4_step": "10.10", "title": "Confirmatory campaign"},
    "pilot2": {"rev4_step": "10.8", "title": "Pilot 2 — paired dispersion"},
    "information": {"rev4_step": "10.11 / §5.4", "title": "Information analyses"},
    "report": {"rev4_step": "10.12", "title": "Report and freeze"},
}

#: Every record says what kind of evidence it is. Only ``pilot``, ``training``
#: and ``campaign`` can ever be experimental, and only when ``executed``.
EVIDENCE_KINDS = (
    "construction",
    "synthetic_fixture",
    "pilot",
    "training",
    "campaign",
    "analysis",
)
EXPERIMENTAL_KINDS = ("pilot", "training", "campaign")

NO_EXECUTION_NOTE = (
    "construction-only: no game episode, training run, pilot episode or "
    "confirmatory episode is executed by this record"
)


class StageRefusal(RuntimeError):
    """A stage cannot proceed because a declared input or decision is absent."""

    def __init__(self, stage: str, blockers: list[str] | tuple[str, ...], **detail: Any):
        self.stage = str(stage)
        self.blockers = tuple(str(item) for item in blockers)
        self.detail = dict(detail)
        super().__init__(
            f"stage {self.stage!r} refused: " + "; ".join(self.blockers)
        )

    def as_dict(self) -> dict:
        return {
            "kind": "stage_refusal",
            "stage": self.stage,
            "blockers": list(self.blockers),
            "detail": dict(self.detail),
        }


class StageConfigurationError(RuntimeError):
    """A stage input is malformed; this is not an authorisation refusal."""


# ---------------------------------------------------------------------------
# stable serialisation
# ---------------------------------------------------------------------------


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: str | Path, payload: Mapping[str, Any], *, overwrite: bool = False) -> Path:
    """Write JSON without ever replacing an existing file by default."""
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite {target}; stage artefacts are write-once"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False)
    mode = "w" if overwrite else "x"
    with target.open(mode, encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return target


def read_json(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"required stage input is missing: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StageConfigurationError(f"{source} is not valid JSON: {error}") from None
    if not isinstance(payload, dict):
        raise StageConfigurationError(f"{source} must contain a JSON object")
    return payload


# ---------------------------------------------------------------------------
# snapshots, unchanged from the existing gates
# ---------------------------------------------------------------------------


def authorization_snapshot(
    *,
    stage: str | None = None,
    plan: Any = None,
    config: Phase8Config | None = None,
) -> dict:
    """Approval, protocol identity and G3 deviation, with the blocker list.

    With ``stage=None`` this is the campaign-wide snapshot: B7 is reported as
    blocking for every stage. A named stage is evaluated by
    :func:`..campaign.protocol.stage_authorization`, which applies the D2
    Pilot 1 exemption only to the exact Pilot 1 grid.
    """
    identity = protocol_identity()
    if stage is not None:
        report = stage_authorization(stage, config=config, plan=plan)
        approval = report["approval"]
        deviation = report["randomization_deviation"]
        return {
            "authorized": report["authorized"],
            "protocol": identity,
            "approval": approval,
            "randomization_deviation": deviation,
            "g3_applicability": report["g3_applicability"],
            "exemption": report["exemption"],
            "blockers": list(report["blockers"]),
        }
    approval = approval_status()
    deviation = randomization_deviation()
    blockers: list[str] = []
    if not approval["approved"]:
        blockers.append(
            "B1: REV4 §12 is unapproved; U1-U18 remain PROPOSED and the document "
            "authorises no execution"
        )
    if deviation.get("status") != "compliant":
        blockers.append(
            "B7: the G3 certified graphs carry a recorded §9.3 memory-gate "
            f"deviation (status {deviation.get('status')!r})"
        )
    return {
        "authorized": not blockers,
        "protocol": identity,
        "approval": approval,
        "randomization_deviation": deviation,
        "blockers": blockers,
    }


def design_snapshot(config: Phase8Config) -> dict:
    """The unresolved ``n_seeds_selected`` field, never defaulted."""
    snapshot = design_status(config.campaign)
    snapshot["blockers"] = [] if snapshot["resolved"] else [
        "B2: design.n_seeds_selected is null until the 10.8 pilot decision (U7)"
    ]
    return snapshot


def memory_snapshot(
    config: Phase8Config,
    *,
    preflight: Callable[[float], dict] = memory_preflight,
) -> dict:
    report = preflight(config.campaign.memory_gate_gb)
    report = dict(report)
    report["blockers"] = [] if report.get("passed") else [
        "B8: free memory is below the declared §9.3 gate; no BANC-scale work "
        "may start"
    ]
    return report


def collect_blockers(
    config: Phase8Config,
    *,
    preflight: Callable[[float], dict] = memory_preflight,
    include_training: bool = False,
    stage: str | None = None,
    plan: Any = None,
) -> list[str]:
    auth = authorization_snapshot(stage=stage, plan=plan, config=config)
    design = design_snapshot(config)
    memory = memory_snapshot(config, preflight=preflight)
    blockers = list(auth["blockers"]) + list(design["blockers"]) + list(memory["blockers"])
    if include_training:
        blockers.extend(
            [
                "B3: no campaign-to-training seed pairing is declared",
                "B4: no training-episode environment-seed schedule is declared",
                "B5: no checkpoint cadence, retention or format is declared",
                "B6: sampler RNG and optimizer moments are not checkpointed, so "
                "resume is parameter-continuous and not bit-identical",
            ]
        )
    return blockers


def stage_envelope(
    stage: str,
    *,
    executed: bool = False,
    evidence_kind: str = "construction",
    **detail: Any,
) -> dict:
    if stage not in STAGE_IDS:
        raise StageConfigurationError(f"unknown stage {stage!r}")
    if evidence_kind not in EVIDENCE_KINDS:
        raise StageConfigurationError(f"unknown evidence kind {evidence_kind!r}")
    meta = STAGE_IDS[stage]
    record = {
        "record_kind": "phase_8_stage_record",
        "stage": stage,
        "rev4_step": meta["rev4_step"],
        "title": meta["title"],
        "executed": bool(executed),
        "evidence_kind": evidence_kind,
        "experimental_evidence": bool(
            executed and evidence_kind in EXPERIMENTAL_KINDS
        ),
        "note": (
            "construction-only output; this is not experimental evidence"
            if not (executed and evidence_kind in EXPERIMENTAL_KINDS)
            else "executed under an authorised protocol"
        ),
    }
    record.update(detail)
    return record


def stage_root(config: Phase8Config, stage: str) -> Path:
    if stage not in STAGE_IDS:
        raise StageConfigurationError(f"unknown stage {stage!r}")
    return PROJECT_ROOT / config.campaign.results_root / stage


# ---------------------------------------------------------------------------
# pilot plan and gated driver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PilotPlan:
    """An explicit pilot grid. It never contains a contrast estimate."""

    stage: str
    rev4_step: str
    arms: tuple[str, ...]
    seeds: tuple[int, ...]
    episodes: int
    establishes: str
    does_not_establish: str
    estimates_contrasts: bool = False

    def entries(self) -> tuple[tuple[str, int, int], ...]:
        return tuple(
            (arm, int(seed), int(episode))
            for arm in self.arms
            for seed in self.seeds
            for episode in range(int(self.episodes))
        )

    def as_dict(self, master_seed: int) -> dict:
        entries = []
        for arm, seed, episode in self.entries():
            plan = seed_plan(master_seed, arm, seed)
            entries.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "episode": episode,
                    "environment_seed": environment_seed(master_seed, seed, episode),
                    "network_seed": int(plan["network"]),
                    "learning_seed": int(plan["learning"]),
                    "structure_seed": int(plan["structure"]),
                }
            )
        return {
            "stage": self.stage,
            "rev4_step": self.rev4_step,
            "arms": list(self.arms),
            "seeds": list(self.seeds),
            "episodes_per_seed": int(self.episodes),
            "n_entries": len(entries),
            "entries": entries,
            "estimates_contrasts": bool(self.estimates_contrasts),
            "hypothesis_tests": [],
            "campaign_effects_estimated": False,
            "merged_into_campaign": False,
            "establishes": self.establishes,
            "does_not_establish": self.does_not_establish,
        }


def _gate_report(
    preflight: Callable[[float], dict], gate_gb: float
) -> dict:
    report = preflight(gate_gb)
    if not isinstance(report, Mapping) or "passed" not in report:
        raise StageConfigurationError(
            "the memory preflight must return a report with 'passed'"
        )
    if not report["passed"]:
        raise MemoryGateError(
            f"{report.get('reason', 'memory preflight failed')} "
            f"(available {report.get('available_gb')} GB of {gate_gb} GB)"
        )
    return dict(report)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def drive_pilot(
    plan: PilotPlan,
    config: Phase8Config,
    *,
    base_dir: str | Path,
    run_id: str,
    episode_runner: Callable[[str, int, int, dict], Mapping[str, Any]],
    preflight: Callable[[float], dict] = memory_preflight,
    new_run_id: str | None = None,
    input_hashes: Mapping[str, Any] | None = None,
    integrity: Mapping[str, Any] | None = None,
    capture: Mapping[str, Any] | None = None,
    synthetic_fixture: bool = False,
) -> dict:
    """Run one pilot grid, or refuse.

    With ``synthetic_fixture=False`` this calls the stage authorisation gate
    first; only the exact Pilot 1 grid can pass B7 under D2, so every other
    stage still raises
    :class:`~experiments.phase_8.campaign.protocol.CampaignNotAuthorized`.
    With ``synthetic_fixture=True`` the driver refuses the real results root,
    stamps every row ``synthetic_fixture`` and cannot produce pilot evidence.
    """
    results_root = (PROJECT_ROOT / config.campaign.results_root).resolve()
    if synthetic_fixture:
        base = Path(base_dir).resolve()
        if _inside(base, results_root) or base == results_root:
            raise StageRefusal(
                plan.stage,
                [
                    "a synthetic-fixture run may not write under the Phase 8 "
                    f"results root {results_root}"
                ],
            )
        evidence_kind = "synthetic_fixture"
    else:
        assert_stage_authorized(plan.stage, config=config, plan=plan)
        evidence_kind = "pilot"

    if episode_runner is None:
        raise StageConfigurationError("drive_pilot requires an episode_runner")
    report = _gate_report(preflight, config.campaign.memory_gate_gb)
    run_dir = resolve_run_directory(base_dir, run_id, new_run_id=new_run_id)
    manifest = build_manifest(
        config,
        run_id=run_dir.name,
        memory_preflight=report,
        input_hashes=input_hashes,
        integrity=integrity,
        capture=capture,
    )
    write_manifest(run_dir / config.campaign.run_manifest_name, manifest)
    write_json(
        run_dir / "pilot_plan.json",
        stage_envelope(plan.stage, evidence_kind=evidence_kind, plan=plan.as_dict(config.campaign.master_seed)),
    )

    store = EpisodeStore(run_dir, filename=config.campaign.episode_store_name)
    executed = 0
    for arm, seed, episode in plan.entries():
        if store.has(arm, seed, episode):
            continue
        context = {
            "master_seed": config.campaign.master_seed,
            "environment_seed": environment_seed(
                config.campaign.master_seed, seed, episode
            ),
            "seed_plan": seed_plan(config.campaign.master_seed, arm, seed),
            "config_hashes": {
                name: entry["sha256"] for name, entry in config.hashes.items()
            },
            "max_game_updates": config.campaign.max_game_updates,
            "episodes_per_seed": int(plan.episodes),
        }
        row = episode_runner(arm, seed, episode, context)
        if not isinstance(row, Mapping):
            raise StageConfigurationError("an episode runner must return a mapping")
        checked = validate_episode_row(row, expected_condition=arm)
        if (int(checked["seed"]), int(checked["episode"])) != (seed, episode):
            raise StageConfigurationError(
                "the row does not identify the episode it was asked to run"
            )
        notes = dict(checked.get("notes") or {})
        notes["evidence_kind"] = evidence_kind
        notes["experimental_evidence"] = not synthetic_fixture
        if synthetic_fixture:
            notes["not_experimental"] = True
        checked["notes"] = notes
        store.append(checked)
        executed += 1

    summary = stage_envelope(
        plan.stage,
        executed=executed > 0,
        evidence_kind=evidence_kind,
        run_dir=run_dir.as_posix(),
        rows_stored=len(store),
        rows_executed=executed,
        planned=len(plan.entries()),
        complete=not store.missing(plan.entries()),
        estimates_contrasts=False,
        merged_into_campaign=False,
        memory_preflight=report,
    )
    write_json(run_dir / "pilot_summary.json", summary)
    return summary


__all__ = [
    "EVIDENCE_KINDS",
    "EXPERIMENTAL_KINDS",
    "NO_EXECUTION_NOTE",
    "PilotPlan",
    "STAGE_IDS",
    "StageConfigurationError",
    "StageRefusal",
    "authorization_snapshot",
    "canonical_json",
    "collect_blockers",
    "design_snapshot",
    "drive_pilot",
    "memory_snapshot",
    "read_json",
    "sha256_text",
    "stage_envelope",
    "stage_root",
    "write_json",
]
