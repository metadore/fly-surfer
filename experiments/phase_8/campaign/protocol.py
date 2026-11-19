"""REV4 conformance checks and the execution-authorisation gate.

SCIENTIFIC STATUS
    Validating a configuration against REV4 says that the declared constants
    match the protocol text. It says nothing about scientific validity and it
    does not authorise execution. REV4 §12 is **not approved**; U1-U18 are all
    ``PROPOSED - not approved``; the document's final paragraph states that it
    "authorises no execution". :func:`assert_campaign_authorized` therefore
    always raises, and the CLI has no code path that starts a campaign.

The G3 §9.3 deviation is reported here as a fact, not resolved:
``experiments/results/phase_8_random/campaign_seed_summary.json`` records
``compliance.status = "deviation_recorded"`` and ``gate_weakened: false``. The
16 graphs are certified, but G3 is not complete and the graphs may not be used
for experimental data collection until an approved amendment or a compliant
rerun exists (G5 brief §4-§5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from experiments.phase_8_random.certification import EXPECTED_PROTOCOL_SHA256

from ..config import PROJECT_ROOT, ConfigError, Phase8Config, load_yaml
from ..registry import build_registry, confirmatory_contrasts
from ..seeds import MASTER_SEED

PROTOCOL_PATH = PROJECT_ROOT / "docs" / "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md"
PROTOCOL_ID = "PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4"
#: Registry declaration order: conditions.yaml groups, then the floor.
ARMS_ACTIVE = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "A_prime",
    "C_prime",
    "F_beta",
    "F_init",
    "E_full",
    "floor",
)
CAMPAIGN_SUMMARY = (
    PROJECT_ROOT / "experiments" / "results" / "phase_8_random" / "campaign_seed_summary.json"
)

#: Appendix C and §6.3 declared constants, in the order the protocol lists them.
DECLARED = {
    "master_seed": 20261116,
    "n_seeds_primary": 16,
    "n_seeds_fallback": 10,
    "episodes_per_seed": 10,
    "max_game_updates": 900,
    "sei_updates": 100,
    "alpha": 0.05,
    "holm_family_sizes": (4, 3),
    "bootstrap_resamples": 10_000,
    "bootstrap_seed": 20261116,
    "memory_gate_gb": 4.0,
    "readout_episodes_per_seed": 20,
    "e_gradient_updates": 2000,
    "eta_plastic": 0.5,
    "eta_identity": 0.0,
    "weight_bounds": (0.5, 2.0),
    "max_abs_update_pa": 5.0,
    "tau_e_ms": 20.0,
    "modulation_gain": 1.0,
    "modulation_tau_ms": 50.0,
    "modulation_clip": (-5.0, 5.0),
    "sensory_current_pa": 200.0,
    "decoder_window_ms": 50.0,
    "decoder_min_active_neurons": 3,
    "decoder_min_spikes": 5,
    "decoder_activation": 0.20,
    "decoder_release": 0.10,
}

EXPECTED_CONDITIONS = ("A", "B", "C", "D", "E", "F")
EXPECTED_CONTROLS = ("A_prime", "C_prime", "F_beta", "F_init")
EXPECTED_EXPLORATORY = ("E_full",)
EXPECTED_ETA = {
    "A": None,
    "B": 0.5,
    "C": None,
    "D": 0.5,
    "E": None,
    "F": None,
    "A_prime": 0.0,
    "C_prime": 0.0,
    "F_beta": None,
    "F_init": None,
    "E_full": None,
}
EXPECTED_TRAINS = {
    "A": ("none",),
    "B": ("synapses",),
    "C": ("none",),
    "D": ("synapses",),
    "E": ("policy",),
    "F": ("readout",),
    "A_prime": ("none",),
    "C_prime": ("none",),
    "F_beta": ("readout",),
    "F_init": ("none",),
    "E_full": ("policy",),
}


class CampaignProtocolError(ConfigError):
    """The configuration disagrees with a constant declared in REV4."""


class CampaignNotAuthorized(RuntimeError):
    """No code path may start a Phase 8 campaign on the present approval state."""


def protocol_identity(path: str | Path = PROTOCOL_PATH) -> dict:
    """Hash and approval statement of the frozen REV4 document."""
    from brain.banc_graph import sha256_file

    source = Path(path)
    if not source.is_file():
        return {
            "path": source.as_posix(),
            "present": False,
            "sha256": None,
            "expected_sha256": EXPECTED_PROTOCOL_SHA256,
            "matches_expected": False,
            "authorises_execution": False,
        }
    digest = sha256_file(source)
    text = source.read_text(encoding="utf-8")
    return {
        "path": source.as_posix(),
        "present": True,
        "sha256": digest,
        "expected_sha256": EXPECTED_PROTOCOL_SHA256,
        "matches_expected": digest == EXPECTED_PROTOCOL_SHA256,
        "authorises_execution": "authorises no execution" not in text,
    }


def approval_status(protocol_path: str | Path = PROTOCOL_PATH) -> dict:
    """REV4 §12 is unapproved; every decision item is still proposed."""
    identity = protocol_identity(protocol_path)
    return {
        "protocol_id": PROTOCOL_ID,
        "approved": False,
        "decision_status": "PROPOSED - not approved",
        "decision_items": [f"U{index}" for index in range(1, 19)],
        "protocol_sha256": identity["sha256"],
        "protocol_matches_expected": identity["matches_expected"],
        "document_authorises_execution": identity["authorises_execution"],
        "reason": (
            "REV4 §12 is not approved; U1-U18 remain PROPOSED. The protocol's "
            "final paragraph authorises no execution. No campaign, training "
            "run, pilot or confirmatory data collection may start."
        ),
    }


def randomization_deviation(path: str | Path = CAMPAIGN_SUMMARY) -> dict:
    """The recorded G3 §9.3 deviation, carried unchanged."""
    source = Path(path)
    if not source.is_file():
        return {
            "summary_path": source.as_posix(),
            "present": False,
            "status": "summary_missing",
            "gate_weakened": False,
            "note": "the G3 campaign summary could not be read; the deviation is unresolved",
        }
    payload = json.loads(source.read_text(encoding="utf-8"))
    compliance = dict(payload.get("compliance") or {})
    seeds = list(payload.get("seeds") or [])
    return {
        "summary_path": source.as_posix(),
        "present": True,
        "status": compliance.get("status"),
        "gate_gb": compliance.get("gate_gb"),
        "gate_weakened": bool(compliance.get("gate_weakened")),
        "min_observed_free_gb": compliance.get("min_observed_free_gb"),
        "construction_runs_below_gate": compliance.get("construction_runs_below_gate"),
        "certified_seeds": [entry.get("seed") for entry in seeds if entry.get("status") == "certified"],
        "note": (
            "the certified graphs were built below the §9.3 4.00 GB gate; G3 is "
            "not complete and the graphs may not be used for experimental data "
            "collection until an approved amendment or a compliant rerun exists"
        ),
    }


def assert_campaign_authorized(*_args: Any, **_kwargs: Any) -> None:
    """Always refuse: the protocol is unapproved and the G3 deviation is open."""
    status = approval_status()
    deviation = randomization_deviation()
    raise CampaignNotAuthorized(
        status["reason"]
        + " The G3 randomization set has a recorded §9.3 deviation "
        f"(status {deviation['status']!r}, gate weakened: "
        f"{deviation['gate_weakened']}). "
        "This entry point does not start campaigns."
    )


# ---------------------------------------------------------------------------
# static conformance
# ---------------------------------------------------------------------------


def _resolve(relative: str) -> Path:
    source = Path(relative)
    return source if source.is_absolute() else PROJECT_ROOT / source


def _check(checks: list[dict], name: str, actual: Any, expected: Any, source: str) -> None:
    passed = actual == expected
    checks.append(
        {
            "name": name,
            "actual": actual,
            "expected": expected,
            "source": source,
            "pass": bool(passed),
        }
    )


def validate_campaign(
    config: Phase8Config,
    *,
    strict: bool = True,
    protocol_path: str | Path = PROTOCOL_PATH,
) -> dict:
    """Compare the loaded configuration with the constants REV4 declares.

    ``n_seeds_selected`` is reported, not failed: null is a legitimate
    pre-pilot state, but the evaluation plan refuses to resolve while it is
    null. Every other mismatch is a hard error in strict mode.
    """
    checks: list[dict] = []

    identity = protocol_identity(protocol_path)
    _check(checks, "protocol.present", identity["present"], True, "REV4")
    _check(
        checks,
        "protocol.sha256",
        identity["matches_expected"],
        True,
        "REV4 / Phase 8 protocol freeze",
    )

    campaign = config.campaign
    for name in (
        "master_seed",
        "n_seeds_primary",
        "n_seeds_fallback",
        "episodes_per_seed",
        "max_game_updates",
        "sei_updates",
        "alpha",
        "bootstrap_resamples",
        "bootstrap_seed",
        "memory_gate_gb",
        "readout_episodes_per_seed",
        "e_gradient_updates",
    ):
        _check(
            checks,
            f"campaign.{name}",
            getattr(campaign, name),
            DECLARED[name],
            "REV4 Appendix C / §6.3 / §9.3",
        )
    _check(
        checks,
        "campaign.holm_family_sizes",
        tuple(campaign.holm_family_sizes),
        DECLARED["holm_family_sizes"],
        "REV4 §7.5 / U14",
    )
    _check(
        checks,
        "campaign.n_seeds_selected",
        campaign.n_seeds_selected,
        None,
        "pre-pilot state (null until U7 is resolved)",
    )
    _check(
        checks,
        "campaign.conditions",
        tuple(campaign.conditions),
        EXPECTED_CONDITIONS,
        "REV4 §3",
    )
    _check(
        checks,
        "campaign.control_arms",
        tuple(campaign.control_arms),
        EXPECTED_CONTROLS,
        "REV4 §3.6 / §3.8",
    )
    _check(
        checks,
        "campaign.exploratory_arms",
        tuple(campaign.exploratory_arms),
        EXPECTED_EXPLORATORY,
        "REV4 §3.5 / U8",
    )
    _check(
        checks,
        "campaign.floor_arm",
        campaign.floor_arm,
        "floor",
        "REV4 §3.6.2 / U10",
    )

    registry = build_registry(config.conditions)
    _check(
        checks,
        "registry.evaluation_arms",
        tuple(registry.evaluation_arms),
        ARMS_ACTIVE,
        "REV4 §3 arms plus the substrate-free floor",
    )
    for arm, eta in EXPECTED_ETA.items():
        _check(
            checks,
            f"eta.{arm}",
            registry.spec(arm).eta,
            eta,
            "REV4 Appendix C",
        )
        _check(
            checks,
            f"trains.{arm}",
            tuple(registry.spec(arm).trains),
            EXPECTED_TRAINS[arm],
            "REV4 §6.7",
        )
    for contrast in confirmatory_contrasts(4):
        for member in (contrast["minuend"], contrast["subtrahend"]):
            # C4 compares F with its control arm F beta, so a contrast member
            # may be a registered control rather than a condition.
            _check(
                checks,
                f"confirmatory.{contrast['id']}.{member}",
                member in registry.arms,
                True,
                "REV4 §5.3",
            )

    # frozen input files carry the declared plasticity, sensory and decoder
    # constants; a changed file is a changed protocol constant.
    inputs = {name: _resolve(path) for name, path in campaign.frozen_inputs.items()}
    plasticity = load_yaml(inputs["plasticity"])
    body = dict(plasticity["plasticity"])
    _check(
        checks,
        "plasticity.eta",
        float(body["eta"]),
        DECLARED["eta_plastic"],
        "configs/plasticity_banc.yaml / REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.control_eta",
        float(body["control_eta"]),
        DECLARED["eta_identity"],
        "REV4 §3.8",
    )
    bounds = dict(body["bounds"])
    _check(
        checks,
        "plasticity.bounds",
        (float(bounds["lower_factor"]), float(bounds["upper_factor"])),
        DECLARED["weight_bounds"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.max_abs_update_pa",
        float(bounds["max_abs_update_pa"]),
        DECLARED["max_abs_update_pa"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "plasticity.traces.tau_e_ms",
        float(body["traces"]["tau_e_ms"]),
        DECLARED["tau_e_ms"],
        "REV4 Appendix C",
    )
    modulation = dict(plasticity["modulation"])
    _check(
        checks,
        "modulation.gain",
        float(modulation["gain"]),
        DECLARED["modulation_gain"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "modulation.decay_tau_ms",
        float(modulation["decay_tau_ms"]),
        DECLARED["modulation_tau_ms"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "modulation.clip_abs",
        (
            -float(modulation["clip_abs"]),
            float(modulation["clip_abs"]),
        ),
        DECLARED["modulation_clip"],
        "REV4 Appendix C",
    )

    mapping = load_yaml(inputs["sensory_mapping"])
    feature_currents = {
        float(payload.get("current_pa", 0.0))
        for payload in mapping["features"].values()
    }
    _check(
        checks,
        "sensory.current_pa",
        feature_currents,
        {DECLARED["sensory_current_pa"]},
        "REV4 Appendix C",
    )
    _check(
        checks,
        "sensory.n_features",
        len(mapping["features"]),
        7,
        "REV4 §6.6",
    )

    decoder = dict(load_yaml(inputs["motor_decoder"])["decoder"])
    _check(checks, "decoder.window_ms", float(decoder["window_ms"]), DECLARED["decoder_window_ms"], "REV4 Appendix C")
    _check(
        checks,
        "decoder.min_active_neurons",
        int(decoder["min_active_neurons"]),
        DECLARED["decoder_min_active_neurons"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.min_spikes",
        int(decoder["min_spikes"]),
        DECLARED["decoder_min_spikes"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.activation_threshold",
        float(decoder["activation_threshold"]),
        DECLARED["decoder_activation"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.release_threshold",
        float(decoder["release_threshold"]),
        DECLARED["decoder_release"],
        "REV4 Appendix C",
    )
    _check(
        checks,
        "decoder.priority",
        tuple(decoder["priority"]),
        ("LEFT", "RIGHT", "JUMP"),
        "REV4 Appendix C",
    )

    # seed ranges must remain disjoint and cover the primary design (the
    # loader already enforces this; the report restates it for the record).
    _check(
        checks,
        "seeds.disjoint",
        not (
            set(campaign.campaign_seeds) & set(campaign.training_seeds)
        )
        and not (set(campaign.campaign_seeds) & set(campaign.pilot_seeds))
        and not (set(campaign.training_seeds) & set(campaign.pilot_seeds)),
        True,
        "REV4 §6.3 / §6.7",
    )
    _check(
        checks,
        "seeds.campaign_count",
        len(campaign.campaign_seeds) >= campaign.n_seeds_primary,
        True,
        "REV4 §7.1",
    )

    failed = [entry for entry in checks if not entry["pass"]]
    report = {
        "protocol": identity,
        "approval": approval_status(protocol_path),
        "randomization_deviation": randomization_deviation(),
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failures": failed,
        "conforms": not failed,
        "n_seeds_selected": campaign.n_seeds_selected,
        "design_resolved": campaign.n_seeds_selected is not None,
        "note": (
            "conformance to declared constants is not scientific validity and "
            "is not an authorisation to execute"
        ),
    }
    if strict and failed:
        names = ", ".join(entry["name"] for entry in failed)
        raise CampaignProtocolError(
            "the campaign configuration disagrees with REV4 at: " + names
        )
    return report


def describe() -> dict:
    return {
        "protocol": protocol_identity(),
        "approval": approval_status(),
        "declared": dict(DECLARED),
        "expected_arms": list(ARMS_ACTIVE),
        "master_seed": MASTER_SEED,
    }


__all__ = [
    "CAMPAIGN_SUMMARY",
    "CampaignNotAuthorized",
    "CampaignProtocolError",
    "DECLARED",
    "EXPECTED_CONDITIONS",
    "EXPECTED_CONTROLS",
    "EXPECTED_EXPLORATORY",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "approval_status",
    "assert_campaign_authorized",
    "describe",
    "protocol_identity",
    "randomization_deviation",
    "validate_campaign",
]
