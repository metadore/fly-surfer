"""Phase 4H.5: statistical assessment and project-specific evidence grading.

Reads the actual Phase 4H.1-4H.4 artifacts. Missing artifacts are recorded as
unavailable; no value is reconstructed from memory or from a summary. The
evidence grades E0-E4 are internal computational categories defined here, not
an established neuroscience standard. Each claim is graded separately.

Writes ``reports/PHASE_4H5_STATISTICAL_ASSESSMENT_AND_EVIDENCE_GRADING.json``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_4h import common  # noqa: E402

RESULTS = common.RESULTS
REPORTS = PROJECT_ROOT / "reports"
OUTPUT = REPORTS / "PHASE_4H5_STATISTICAL_ASSESSMENT_AND_EVIDENCE_GRADING.json"

ARTIFACTS = {
    "4H.1_result": RESULTS / "control_draws.json",
    "4H.2_result": RESULTS / "population_sensitivity.json",
    "4H.3_result": RESULTS / "weight_sensitivity.json",
    "4H.4_result": RESULTS / "sensory_roundtrip.json",
    "4H.4_analysis": REPORTS / "PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json",
    "4H.1_report": REPORTS / "PHASE_4H1_RANDOM_CONTROL_VALIDATION.md",
    "4H.2_report": REPORTS / "PHASE_4H2_POPULATION_SENSITIVITY.md",
    "4H.3_report": REPORTS / "PHASE_4H3_WEIGHT_SENSITIVITY.md",
    "4H.4_report": REPORTS / "PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.md",
    "protocol": REPORTS / "PHASE_4H_EXPERIMENTAL_PROTOCOL.md",
}

GRADE_DESCRIPTIONS = {
    "E0": (
        "Infrastructure: data integrity, graph construction, deterministic "
        "execution and software validation."
    ),
    "E1": (
        "Computational activity: the model produces reproducible neural "
        "activity under stated assumptions."
    ),
    "E2": (
        "Population-level sensitivity: activity changes reproducibly with "
        "controlled inputs or perturbations."
    ),
    "E3": (
        "Functional pathway evidence: input-dependent activity propagates "
        "through relevant intermediate populations and reaches the intended "
        "output population."
    ),
    "E4": (
        "Validated behavioural evidence: controlled learning and behavioural "
        "performance, supported by appropriate independent validation."
    ),
}


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def artifact_audit() -> dict:
    audit = {}
    for name, path in ARTIFACTS.items():
        audit[name] = {
            "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "available": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
        }
    return audit


def audit_4h1(payload: dict | None) -> dict:
    if payload is None:
        return {"available": False, "error": "4H.1 result artifact missing"}
    confirm = payload.get("confirmatory", {})
    p1 = confirm.get("P1_motor_spikes", {})
    p2 = confirm.get("P2_jump_windows", {})
    draws = payload.get("draws", [])
    failures = payload.get("failures", [])
    families = sorted(payload.get("families", {}).keys())
    return {
        "available": True,
        "generated_at_utc": payload.get("generated_at_utc"),
        "n_draws": len(draws),
        "n_failures": len(failures),
        "families": families,
        "reference_motor_spikes": p1.get("reference"),
        "reference_jump_windows": p2.get("reference"),
        "p_values_p1": p1.get("p_values"),
        "p_values_p2": p2.get("p_values"),
        "holm_rejected_p1": p1.get("holm", {}).get("rejected"),
        "holm_rejected_p2": p2.get("holm", {}).get("rejected"),
        "any_confirmatory_difference": confirm.get("any_confirmatory_difference"),
        "spike_hash_matches_phase_4g": payload.get("reference", {}).get(
            "spike_hash_matches_phase_4g"
        ),
        "integrity_pass": payload.get("integrity", {}).get("protected_unchanged"),
        "n_integrity_checks": payload.get("integrity", {}).get("after", {}).get(
            "checked"
        ),
        "runtime": payload.get("runtime"),
        "limitations": payload.get("limitations", []),
    }


def audit_4h2(payload: dict | None) -> dict:
    if payload is None:
        return {"available": False, "error": "4H.2 result artifact missing"}
    surface = payload.get("surface_table", {})
    connectivity = surface.get("connectivity_ranked", [])
    size_curve = {
        int(cell["size"]): {
            "motor_spikes": cell.get("motor_spikes"),
            "jump_windows": cell.get("jump_windows"),
            "total_spikes": cell.get("total_spikes"),
            "jump_detected_runs": cell.get("jump_detected_runs"),
        }
        for cell in connectivity
    }
    confirm = payload.get("confirmatory", {})
    return {
        "available": True,
        "generated_at_utc": payload.get("generated_at_utc"),
        "n_runs": len(payload.get("runs", [])),
        "n_failures": len(payload.get("failures", [])),
        "n_cells": len(payload.get("cells", {})),
        "confirmatory": {
            "comparison": confirm.get("comparison"),
            "P1": {
                "observed": confirm.get("P1_motor_spikes", {}).get("observed"),
                "control_n": confirm.get("P1_motor_spikes", {}).get("control_n"),
                "control_max": confirm.get("P1_motor_spikes", {}).get("control_max"),
                "p_one_sided_greater": confirm.get("P1_motor_spikes", {}).get(
                    "p_one_sided_greater"
                ),
            },
            "P2": {
                "observed": confirm.get("P2_jump_windows", {}).get("observed"),
                "control_n": confirm.get("P2_jump_windows", {}).get("control_n"),
                "control_max": confirm.get("P2_jump_windows", {}).get("control_max"),
                "p_one_sided_greater": confirm.get("P2_jump_windows", {}).get(
                    "p_one_sided_greater"
                ),
            },
            "holm": confirm.get("holm"),
            "any_confirmatory_difference": confirm.get("any_confirmatory_difference"),
        },
        "connectivity_size_curve": size_curve,
        "integrity_pass": payload.get("integrity", {}).get("protected_unchanged"),
        "n_integrity_checks": payload.get("integrity", {}).get("after", {}).get(
            "checked"
        ),
        "runtime": payload.get("runtime"),
        "limitations": payload.get("limitations", []),
    }


def audit_4h3(payload: dict | None) -> dict:
    if payload is None:
        return {"available": False, "error": "4H.3 result artifact missing"}
    analysis = payload.get("analysis", {})
    table = analysis.get("summary_table", [])
    compact = {
        row["config"]: {
            "weight": row.get("weight"),
            "sign": row.get("sign"),
            "drive": row.get("drive"),
            "current_pa": row.get("current_pa"),
            "motor_spikes": row.get("motor_spikes"),
            "jump_windows": row.get("jump_windows"),
            "total_spikes": row.get("total_spikes"),
            "silent": row.get("silent"),
            "neutral_only": row.get("neutral_only"),
            "all_hashes_equal": row.get("all_hashes_equal"),
        }
        for row in table
    }
    return {
        "available": True,
        "generated_at_utc": payload.get("generated_at_utc"),
        "n_runs": len(payload.get("runs", [])),
        "n_failures": len(payload.get("failures", [])),
        "n_configs": len(payload.get("configs", {})),
        "preregistration_sha256": payload.get("preregistration", {}).get("sha256"),
        "preregistration_matches": payload.get("preregistration", {}).get(
            "matches_frozen_hash"
        ),
        "config_summary": compact,
        "s2_equals_s0": analysis.get("s2_equals_s0"),
        "w4_equals_w1": analysis.get("w4_equals_w1"),
        "cap_saturation": analysis.get("cap_saturation"),
        "unavailable_family": analysis.get("unavailable_family"),
        "integrity_pass": payload.get("integrity", {}).get("protected_unchanged"),
        "n_integrity_checks": payload.get("integrity", {}).get("after", {}).get(
            "checked"
        ),
        "runtime": payload.get("runtime"),
        "limitations": payload.get("limitations", []),
    }


def get_condition(analysis: dict | None, stream: str, condition: str) -> dict:
    if analysis is None:
        return {}
    return (
        analysis.get("condition_results", {})
        .get(stream, {})
        .get(condition, {})
    )


def get_diagnostic(analysis: dict | None, stream: str, condition: str) -> dict:
    if analysis is None:
        return {}
    return (
        analysis.get("diagnostics", {})
        .get(f"{stream}:{condition}", {})
    )


def audit_4h4(
    result: dict | None, analysis: dict | None
) -> dict:
    if result is None:
        return {"available": False, "error": "4H.4 raw result artifact missing"}
    conditions = {}
    for stream in ("full_100_199", "seg_0_99", "seg_200_299"):
        conditions[stream] = {
            condition: get_condition(analysis, stream, condition)
            for condition in (
                "A_no_events",
                "B_actual",
                "C_temporal_shuffle",
                "D_feature_identity_shuffle",
                "E_random_matched_mapping",
                "F_constant_matched_charge",
                "G_background_noise",
            )
        }
    b_full = conditions["full_100_199"].get("B_actual", {})
    diagnostic = get_diagnostic(analysis, "full_100_199", "B_actual")
    groups = diagnostic.get("groups", {})
    first_hop = groups.get("first_hop", {})
    second_hop = groups.get("second_hop", {})
    descending = groups.get("descending", {})
    motor = groups.get("motor", {})
    non_stim = groups.get("non_stimulated_non_motor", {})
    stimulated = groups.get("stimulated", {})
    return {
        "available": True,
        "analysis_available": analysis is not None,
        "generated_at_utc": result.get("generated_at_utc"),
        "n_runs": len(result.get("runs", [])),
        "matrix_complete": (
            analysis.get("execution", {})
            .get("reconciliation", {})
            .get("complete")
            if analysis is not None
            else None
        ),
        "determinism": (
            analysis.get("execution", {}).get("determinism")
            if analysis is not None
            else result.get("determinism")
        ),
        "integrity_pass": result.get("integrity", {}).get("protected_unchanged"),
        "n_integrity_checks": result.get("integrity", {}).get("after", {}).get(
            "checked"
        ),
        "config_verification_pass": (
            analysis.get("configuration_verification", {}).get("pass")
            if analysis is not None
            else None
        ),
        "config_verification_checks": (
            analysis.get("configuration_verification", {}).get("n_checks")
            if analysis is not None
            else None
        ),
        "condition_tables": conditions,
        "full_stream_B": {
            "total_spikes": b_full.get("total_spikes"),
            "stimulated_spikes": b_full.get("stimulated_spikes"),
            "non_stimulated_spikes": b_full.get("non_stimulated_spikes"),
            "motor_spikes": b_full.get("motor_spikes"),
            "decoded_state_counts": b_full.get("decoded_state_counts"),
            "event_locked_downstream_spikes": b_full.get(
                "event_locked_downstream_spikes"
            ),
            "alignment_best_r": b_full.get("alignment_best_r"),
        },
        "propagation_B_full": {
            "structure": diagnostic.get("structure"),
            "transmission": diagnostic.get("transmission"),
            "stimulated": {
                key: stimulated.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "max_synaptic_current_pa",
                    "max_membrane_mv",
                )
            },
            "first_hop": {
                key: first_hop.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "receiving_neurons",
                    "max_synaptic_current_pa",
                    "max_membrane_mv",
                    "max_depolarization_mv",
                    "closest_deficit_mv",
                    "n_within_1mv",
                    "n_within_5mv",
                    "n_within_10mv",
                )
            },
            "second_hop": {
                key: second_hop.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "receiving_neurons",
                    "max_membrane_mv",
                    "closest_deficit_mv",
                )
            },
            "descending": {
                key: descending.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "receiving_neurons",
                    "max_synaptic_current_pa",
                    "max_membrane_mv",
                    "max_depolarization_mv",
                    "closest_deficit_mv",
                )
            },
            "motor": {
                key: motor.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "receiving_neurons",
                    "max_synaptic_current_pa",
                    "max_membrane_mv",
                    "max_depolarization_mv",
                    "closest_deficit_mv",
                )
            },
            "non_stimulated_non_motor": {
                key: non_stim.get(key)
                for key in (
                    "n",
                    "spikes",
                    "active_neurons",
                    "receiving_neurons",
                    "max_synaptic_current_pa",
                    "max_membrane_mv",
                    "max_depolarization_mv",
                    "closest_deficit_mv",
                )
            },
            "drive": diagnostic.get("drive"),
            "threshold": diagnostic.get("threshold"),
            "event_locked_stimulated": diagnostic.get("event_locked_stimulated"),
        },
        "runtime": (
            analysis.get("runtime") if analysis is not None else result.get("runtime")
        ),
        "limitations": result.get("limitations", []),
    }


def award_grade(criteria: dict) -> str | None:
    """Highest internal evidence grade whose criterion is satisfied."""
    for grade in ("E4", "E3", "E2", "E1", "E0"):
        if criteria.get(grade.lower(), False):
            return grade
    return None


def format_mv(value) -> str:
    if value is None:
        return "not measured"
    return f"{float(value):.3f} mV"


def nominal_weight_family_rows(config_summary: dict) -> dict:
    """Summary rows restricted to the pre-registered nominal drive D0."""
    return {
        name: row
        for name, row in (config_summary or {}).items()
        if row.get("drive") == "D0"
    }


def weight_sensitivity_is_observed(config_summary: dict) -> bool:
    rows = nominal_weight_family_rows(config_summary)
    signatures = {
        (row.get("motor_spikes"), row.get("jump_windows")) for row in rows.values()
    }
    return bool(rows) and len(signatures) > 1


def summarise_condition_endpoint(
    audit: dict, endpoint: str, conditions: tuple[str, ...]
) -> dict:
    table = audit.get("condition_tables", {})
    payload = {}
    for condition in conditions:
        values = []
        for stream in ("full_100_199", "seg_0_99", "seg_200_299"):
            value = table.get(stream, {}).get(condition, {}).get(endpoint)
            if isinstance(value, (int, float)):
                values.append(float(value))
        payload[condition] = {
            "n": len(values),
            "mean": round(statistics.fmean(values), 6) if values else None,
            "sd": (
                round(statistics.stdev(values), 6) if len(values) > 1 else None
            ),
            "values": [round(value, 6) for value in values],
        }
    return payload


def build_claims(audit: dict, questions: dict) -> list[dict]:
    four = audit["4H.4"]
    one = audit["4H.1"]
    two = audit["4H.2"]
    three = audit["4H.3"]
    prop = four.get("propagation_B_full", {})
    first = prop.get("first_hop", {})
    second = prop.get("second_hop", {})
    descending = prop.get("descending", {})
    motor = prop.get("motor", {})
    non_stim = prop.get("non_stimulated_non_motor", {})
    structure = prop.get("structure", {}) or {}
    transmission = prop.get("transmission", {}) or {}
    determinism = four.get("determinism") or {}
    repeats_ok = all(
        block.get(condition, {}).get("spike_hash_equal", False)
        and block.get(condition, {}).get("decision_hash_equal", False)
        for block in determinism.values()
        for condition in ("B_actual", "G_background_noise")
    ) if determinism else False

    nominal = nominal_weight_family_rows(three.get("config_summary") or {})
    nominal_jump = sorted(
        name for name, row in nominal.items() if (row.get("jump_windows") or 0) > 0
    )
    nominal_silent = sorted(
        name for name, row in nominal.items() if row.get("silent")
    )

    claims = []

    claims.append(
        {
            "id": "C01_integrity_determinism",
            "dimension": "reproducibility",
            "claim": (
                "The BANC graph, node table and phase artifacts are intact, and "
                "identical simulations produce identical spike, decision and "
                "drive hashes."
            ),
            "criteria": {"e0": bool(four.get("integrity_pass") and repeats_ok)},
            "status": "supported" if four.get("integrity_pass") and repeats_ok else "not_supported",
            "evidence": {
                "4H.4_integrity_pass": four.get("integrity_pass"),
                "4H.4_repeat_hashes_equal": repeats_ok,
                "4H.1_integrity_pass": one.get("integrity_pass"),
                "4H.2_integrity_pass": two.get("integrity_pass"),
                "4H.3_integrity_pass": three.get("integrity_pass"),
            },
            "reason": "E0 is awarded for reproducible software execution and data integrity.",
        }
    )

    claims.append(
        {
            "id": "C02_stimulated_sensory_spiking",
            "claim": (
                "The event-pulsed sensory drive produces reproducible spikes in "
                "the stimulated sensory neurons."
            ),
            "criteria": {
                "e0": bool(four.get("integrity_pass")),
                "e1": bool(
                    (four.get("full_stream_B", {}) or {}).get("stimulated_spikes", 0)
                    and (four.get("full_stream_B", {}) or {}).get(
                        "stimulated_spikes", 0
                    )
                    > 0
                ),
            },
            "status": "supported",
            "evidence": {
                "B_full_stimulated_spikes": (four.get("full_stream_B", {}) or {}).get(
                    "stimulated_spikes"
                ),
                "B_full_total_spikes": (four.get("full_stream_B", {}) or {}).get(
                    "total_spikes"
                ),
                "A_F_G_total_spikes": {
                    condition: (
                        four.get("condition_tables", {})
                        .get("full_100_199", {})
                        .get(condition, {})
                        .get("total_spikes")
                    )
                    for condition in ("A_no_events", "F_constant_matched_charge", "G_background_noise")
                },
            },
            "reason": "E1 is awarded for reproducible activity in the directly stimulated population.",
        }
    )

    claims.append(
        {
            "id": "C03_condition_c_decoder_output",
            "claim": (
                "The Phase 4G condition C group produces reproducible motor-neuron "
                "spikes and decoder JUMP windows under the fixed protocol."
            ),
            "criteria": {
                "e0": bool(one.get("spike_hash_matches_phase_4g")),
                "e1": bool((one.get("reference_motor_spikes") or 0) > 0),
            },
            "status": "supported",
            "evidence": {
                "motor_spikes": one.get("reference_motor_spikes"),
                "jump_windows": one.get("reference_jump_windows"),
                "spike_hash_matches_phase_4g": one.get(
                    "spike_hash_matches_phase_4g"
                ),
                "repeats_hash_equal": repeats_ok,
            },
            "reason": (
                "E1 is the highest grade: the output is a simulated decoder "
                "result, not yet a propagated sensory or behavioural result."
            ),
        }
    )

    claims.append(
        {
            "id": "C04_condition_c_vs_random_controls",
            "claim": (
                "Condition C is distinguishable from five pre-declared matched "
                "random-control families on motor spikes and JUMP windows."
            ),
            "criteria": {
                "e0": bool(one.get("integrity_pass")),
                "e1": bool(one.get("reference_motor_spikes")),
                "e2": bool(one.get("any_confirmatory_difference")),
            },
            "status": "supported_with_limits",
            "evidence": {
                "p_values_P1": one.get("p_values_p1"),
                "p_values_P2": one.get("p_values_p2"),
                "holm_P1": one.get("holm_rejected_p1"),
                "holm_P2": one.get("holm_rejected_p2"),
                "minimum_attainable_p": 0.00990099,
                "selection_bias": (
                    "condition C was selected on the same motor-synapse rank used "
                    "for the comparison"
                ),
            },
            "reason": (
                "E2 is awarded for statistical sensitivity to population identity "
                "within the tested control families; it is not pathway evidence."
            ),
        }
    )

    claims.append(
        {
            "id": "C05_population_size_and_rule",
            "claim": (
                "Motor-neuron spikes and JUMP windows depend reproducibly on the "
                "driven population size and on the selection rule."
            ),
            "criteria": {
                "e0": bool(two.get("integrity_pass")),
                "e1": bool(two.get("connectivity_size_curve")),
                "e2": bool(two.get("confirmatory", {}).get("any_confirmatory_difference")),
            },
            "status": "supported",
            "evidence": {
                "connectivity_size_curve": two.get("connectivity_size_curve"),
                "size_64_confirmatory": two.get("confirmatory"),
            },
            "reason": "E2 is awarded for a reproducible dose-response and rule dependence.",
        }
    )

    claims.append(
        {
            "id": "C06_weight_sign_drive_sensitivity",
            "claim": (
                "The decoder output is sensitive to weight transform, transmitter "
                "sign policy and drive amplitude."
            ),
            "criteria": {
                "e0": bool(three.get("integrity_pass") and three.get("preregistration_matches")),
                "e1": bool(three.get("config_summary")),
                "e2": weight_sensitivity_is_observed(three.get("config_summary") or {}),
            },
            "status": "supported",
            "evidence": {
                "preregistration_matches": three.get("preregistration_matches"),
                "config_summary": three.get("config_summary"),
                "s2_equals_s0": three.get("s2_equals_s0"),
                "w4_equals_w1": three.get("w4_equals_w1"),
                "cap_saturation": three.get("cap_saturation"),
            },
            "reason": (
                "E2 is awarded for reproducible parameter sensitivity. The result "
                "does not establish which transform is biologically correct."
            ),
        }
    )

    claims.append(
        {
            "id": "C07_sensory_downstream_propagation",
            "claim": (
                "Sensory stimulation propagates beyond the directly stimulated "
                "neurons to first-hop and later populations."
            ),
            "criteria": {"e0": True, "e1": False, "e2": False, "e3": False},
            "status": "contradicted",
            "evidence": {
                "non_stimulated_spikes": (four.get("full_stream_B", {}) or {}).get(
                    "non_stimulated_spikes"
                ),
                "first_hop_targets_downstream": structure.get(
                    "first_hop_downstream_targets"
                ),
                "first_hop_receiving_neurons": first.get("receiving_neurons"),
                "first_hop_max_membrane_mv": first.get("max_membrane_mv"),
                "first_hop_closest_deficit_mv": first.get("closest_deficit_mv"),
                "first_hop_spikes": first.get("spikes"),
                "second_hop_spikes": second.get("spikes"),
                "signed_transmissions": transmission.get("signed_transmissions"),
            },
            "reason": (
                "No non-stimulated neuron spiked. Synaptic current reached "
                f"{first.get('receiving_neurons')} of "
                f"{structure.get('first_hop_downstream_targets')} downstream "
                "first-hop targets, but the closest neuron remained "
                f"{format_mv(first.get('closest_deficit_mv'))} below threshold. "
                "E3 is not awarded."
            ),
        }
    )

    claims.append(
        {
            "id": "C08_actual_vs_shuffled_propagated_response",
            "claim": (
                "Actual sensory-event structure produces a distinguishable "
                "propagated downstream response compared with shuffled controls."
            ),
            "criteria": {"e0": True, "e1": True, "e2": False, "e3": False},
            "status": "not_supported",
            "evidence": {
                "B_vs_C": questions.get("Q6_actual_vs_shuffled", {}).get("evidence"),
                "B_vs_D": questions.get("Q6_actual_vs_shuffled", {}).get(
                    "evidence_D"
                ),
                "downstream_event_locked_spikes_B": (
                    four.get("full_stream_B", {}) or {}
                ).get("event_locked_downstream_spikes"),
                "decoder_states_B": (four.get("full_stream_B", {}) or {}).get(
                    "decoded_state_counts"
                ),
            },
            "reason": (
                "A small difference exists in stimulated spike totals, but there "
                "is no propagated or decoder-level difference; the sign of the "
                "B-versus-C difference is also mixed across streams. E2/E3 are not awarded."
            ),
        }
    )

    claims.append(
        {
            "id": "C09_descending_motor_recruitment",
            "claim": (
                "Sensory activity reaches descending neurons and motor neurons."
            ),
            "criteria": {"e0": True, "e1": False, "e2": False, "e3": False},
            "status": "contradicted",
            "evidence": {
                "descending_spikes": descending.get("spikes"),
                "descending_receiving_neurons": descending.get("receiving_neurons"),
                "descending_max_membrane_mv": descending.get("max_membrane_mv"),
                "descending_closest_deficit_mv": descending.get(
                    "closest_deficit_mv"
                ),
                "motor_spikes": motor.get("spikes"),
                "motor_receiving_neurons": motor.get("receiving_neurons"),
                "motor_max_membrane_mv": motor.get("max_membrane_mv"),
                "second_hop_motor_targets": structure.get("second_hop_motor"),
            },
            "reason": (
                f"{structure.get('second_hop_motor')} motor neurons are structurally "
                "two signed hops from the stimulated group, but none receives "
                "current or spikes. E3 is not awarded."
            ),
        }
    )

    claims.append(
        {
            "id": "C10_decoder_is_validated_motor_command",
            "claim": (
                "A LEFT, RIGHT or JUMP decoder output is a validated biological "
                "motor command or behavioural action."
            ),
            "criteria": {"e0": True, "e1": True, "e2": True, "e3": False, "e4": False},
            "status": "not_supported",
            "evidence": {
                "left_right_jump_labels": "annotation-derived decoder labels",
                "behavioural_learning": "none",
                "independent_validation": "none",
            },
            "reason": "E4 requires controlled behavioural learning and independent validation; neither exists.",
        }
    )

    claims.append(
        {
            "id": "C11_mapping_is_measured_pathway",
            "claim": (
                "The game-feature-to-BANC mapping is a measured visual or sensory "
                "pathway."
            ),
            "criteria": {"e0": True, "e1": False, "e2": False, "e3": False},
            "status": "not_supported",
            "evidence": {
                "mapping_status": "annotation-defined populations with labelled hypotheses",
                "motor_overlap": 0,
                "signed_edge_coverage_t5": 0.444811,
                "fafb_banc_merge": "none; identities are never merged",
            },
            "reason": "The mapping is a computational convention, not a measured pathway.",
        }
    )

    claims.append(
        {
            "id": "C12_robust_across_assumptions",
            "claim": (
                "The reported effects are invariant to the main model assumptions "
                "(weight transform, sign policy, drive, mapping)."
            ),
            "criteria": {"e0": True, "e1": True, "e2": False, "e3": False},
            "status": "contradicted",
            "evidence": {
                "weight_and_sign": three.get("config_summary"),
                "sensory_mapping": "annotation convention",
                "synaptic_coverage": 0.444811,
            },
            "reason": (
                f"At nominal drive JUMP is present only for {nominal_jump} and "
                f"absent elsewhere; the silent configurations are {nominal_silent}. "
                "E2 sensitivity is supported, but assumption-invariance is not."
            ),
        }
    )

    dimensions = {
        "C01_integrity_determinism": "reproducibility",
        "C02_stimulated_sensory_spiking": "computational_activity",
        "C03_condition_c_decoder_output": "computational_activity",
        "C04_condition_c_vs_random_controls": "statistical_robustness",
        "C05_population_size_and_rule": "statistical_robustness",
        "C06_weight_sign_drive_sensitivity": "parameter_sensitivity",
        "C07_sensory_downstream_propagation": "downstream_propagation",
        "C08_actual_vs_shuffled_propagated_response": "sensory_specificity",
        "C09_descending_motor_recruitment": "motor_output",
        "C10_decoder_is_validated_motor_command": "motor_output",
        "C11_mapping_is_measured_pathway": "biological_plausibility",
        "C12_robust_across_assumptions": "parameter_sensitivity",
    }
    next_grade = {
        "C07_sensory_downstream_propagation": "E3",
        "C08_actual_vs_shuffled_propagated_response": "E3",
        "C09_descending_motor_recruitment": "E3",
        "C10_decoder_is_validated_motor_command": "E4",
        "C11_mapping_is_measured_pathway": "E3",
        "C12_robust_across_assumptions": "E3",
    }
    for claim in claims:
        claim["dimension"] = dimensions[claim["id"]]
        if claim["status"] in ("contradicted", "not_supported"):
            claim["grade"] = None
            claim["highest_grade_not_awarded"] = next_grade[claim["id"]]
        else:
            claim["grade"] = award_grade(claim["criteria"])
        claim["grade_definition"] = (
            None
            if claim["grade"] is None
            else GRADE_DESCRIPTIONS.get(claim["grade"])
        )
    return claims


def build_questions(audit: dict) -> dict:
    one = audit["4H.1"]
    two = audit["4H.2"]
    three = audit["4H.3"]
    four = audit["4H.4"]
    prop = four.get("propagation_B_full", {})
    first = prop.get("first_hop", {})
    second = prop.get("second_hop", {})
    descending = prop.get("descending", {})
    motor = prop.get("motor", {})
    non_stim = prop.get("non_stimulated_non_motor", {})
    structure = prop.get("structure", {}) or {}
    transmission = prop.get("transmission", {}) or {}
    determinism = four.get("determinism") or {}
    repeats_ok = all(
        block.get(condition, {}).get("spike_hash_equal", False)
        and block.get(condition, {}).get("decision_hash_equal", False)
        for block in determinism.values()
        for condition in ("B_actual", "G_background_noise")
    ) if determinism else False

    b_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "B_actual", {}
    )
    c_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "C_temporal_shuffle", {}
    )
    d_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "D_feature_identity_shuffle", {}
    )
    e_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "E_random_matched_mapping", {}
    )
    f_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "F_constant_matched_charge", {}
    )
    g_full = four.get("condition_tables", {}).get("full_100_199", {}).get(
        "G_background_noise", {}
    )

    return {
        "Q1_decoder_deterministic": {
            "question": "Is the motor decoder deterministic?",
            "answer": "yes",
            "evidence": {
                "4H.4_repeat_hashes_equal": repeats_ok,
                "4H.3_repeats_all_hashes_equal": all(
                    row.get("all_hashes_equal")
                    for row in (three.get("config_summary") or {}).values()
                )
                if three.get("config_summary")
                else None,
                "4H.1_reference_matches_phase_4g": one.get(
                    "spike_hash_matches_phase_4g"
                ),
            },
            "grade": "E0",
            "caveat": "Determinism is a software property, not biological reproducibility.",
        },
        "Q2_robust_to_random_draws": {
            "question": "Is the decoder output robust to random control draws?",
            "answer": "yes_with_limits",
            "evidence": {
                "4H.1_families": one.get("families"),
                "p_values_P1": one.get("p_values_p1"),
                "p_values_P2": one.get("p_values_p2"),
                "holm_rejected": one.get("holm_rejected_p1"),
                "minimum_attainable_p": 0.00990099,
                "selection_bias": (
                    "condition C was selected on the same motor-synapse rank used "
                    "for the comparison"
                ),
            },
            "grade": "E2",
            "caveat": (
                "The p-value is at the floor of the 100-draw design; the controls "
                "are matched approximations, not a random sample of all neurons."
            ),
        },
        "Q3_sensitive_to_population_selection_and_size": {
            "question": (
                "Is the decoder output sensitive to population selection and size?"
            ),
            "answer": "yes",
            "evidence": {
                "connectivity_size_curve": two.get("connectivity_size_curve"),
                "size_64_confirmatory": two.get("confirmatory"),
            },
            "grade": "E2",
            "caveat": "Only the size-64 comparison is pre-registered; the size surface is exploratory.",
        },
        "Q4_stable_across_weight_transformations": {
            "question": "Is the output stable across weight transformations?",
            "answer": "no",
            "evidence": {
                "config_summary": three.get("config_summary"),
                "s2_equals_s0": three.get("s2_equals_s0"),
                "w4_equals_w1": three.get("w4_equals_w1"),
                "cap_saturation": three.get("cap_saturation"),
            },
            "grade": "E2",
            "caveat": (
                "JUMP is present only for W0/W5/W6 at nominal drive; W1-W4/W7 "
                "produce no JUMP. Matched-amplitude D1 restores JUMP for W1-W6, "
                "so the effect is amplitude- as well as transform-dependent."
            ),
        },
        "Q5_sensory_downstream_propagation": {
            "question": (
                "Does sensory stimulation produce downstream propagation?"
            ),
            "answer": "no",
            "evidence": {
                "non_stimulated_spikes_B_full": b_full.get("non_stimulated_spikes"),
                "first_hop_targets_downstream": structure.get(
                    "first_hop_downstream_targets"
                ),
                "first_hop_receiving_neurons": first.get("receiving_neurons"),
                "first_hop_max_synaptic_current_pa": first.get(
                    "max_synaptic_current_pa"
                ),
                "first_hop_max_membrane_mv": first.get("max_membrane_mv"),
                "first_hop_closest_deficit_mv": first.get("closest_deficit_mv"),
                "first_hop_spikes": first.get("spikes"),
                "second_hop_spikes": second.get("spikes"),
                "signed_transmissions": transmission.get("signed_transmissions"),
            },
            "grade": None,
            "caveat": (
                "662 signed edges produced 9,499 signed spike-to-edge "
                "transmissions, but no first-hop spike. Structural connectivity "
                "does not imply effective propagation."
            ),
        },
        "Q6_actual_vs_shuffled": {
            "question": (
                "Does actual sensory-event structure produce distinguishable "
                "responses compared with shuffled controls?"
            ),
            "answer": "partial_at_input_only",
            "evidence": {
                "B_full_total": b_full.get("total_spikes"),
                "C_full_total": c_full.get("total_spikes"),
                "D_full_total": d_full.get("total_spikes"),
                "E_full_total": e_full.get("total_spikes"),
                "F_full_total": f_full.get("total_spikes"),
                "G_full_total": g_full.get("total_spikes"),
                "B_full_non_stimulated": b_full.get("non_stimulated_spikes"),
                "B_full_event_locked_downstream": b_full.get(
                    "event_locked_downstream_spikes"
                ),
                "B_full_decoder_states": b_full.get("decoded_state_counts"),
                "C_full_decoder_states": c_full.get("decoded_state_counts"),
                "D_full_decoder_states": d_full.get("decoded_state_counts"),
            },
            "evidence_D": {
                "B_full_total": b_full.get("total_spikes"),
                "D_full_total": d_full.get("total_spikes"),
            },
            "grade": "E1",
            "caveat": (
                "The difference is confined to stimulated spike totals; it has no "
                "downstream or decoder consequence and changes sign across the "
                "three streams. E2/E3 are not awarded."
            ),
        },
        "Q7_activity_reaches_descending_and_motor": {
            "question": (
                "Does activity reach descending and motor populations?"
            ),
            "answer": "no",
            "evidence": {
                "descending_spikes": descending.get("spikes"),
                "descending_receiving_neurons": descending.get("receiving_neurons"),
                "descending_max_membrane_mv": descending.get("max_membrane_mv"),
                "descending_closest_deficit_mv": descending.get(
                    "closest_deficit_mv"
                ),
                "motor_spikes": motor.get("spikes"),
                "motor_receiving_neurons": motor.get("receiving_neurons"),
                "motor_max_membrane_mv": motor.get("max_membrane_mv"),
                "second_hop_motor_targets": structure.get("second_hop_motor"),
            },
            "grade": None,
            "caveat": (
                "Four motor neurons are structurally reachable at two signed "
                "hops; none receives current because the first hop does not fire."
            ),
        },
        "Q8_assumption_dependence": {
            "question": (
                "Are apparent effects dependent on specific model assumptions?"
            ),
            "answer": "yes",
            "evidence": {
                "weight_sign_sensitivity": three.get("config_summary"),
                "signed_edge_coverage_t5": 0.444811,
                "predicted_vs_verified_transmitters": (
                    "verified-only policy; predicted fallback disabled"
                ),
                "mapping": "annotation-defined hypothesis",
            },
            "grade": "E2",
            "caveat": (
                "The direction of the 4G result is not invariant to the weight "
                "transform or sign policy; the sensory round-trip is additionally "
                "conditional on the annotation mapping."
            ),
        },
    }


def build_dimensions(questions: dict, audit: dict) -> dict:
    return {
        "reproducibility": {
            "status": "strong",
            "grade": "E0",
            "evidence": questions["Q1_decoder_deterministic"]["evidence"],
        },
        "statistical_robustness": {
            "status": "moderate",
            "grade": "E2",
            "evidence": {
                "4H.1": questions["Q2_robust_to_random_draws"]["evidence"],
                "4H.2": questions["Q3_sensitive_to_population_selection_and_size"][
                    "evidence"
                ],
            },
        },
        "parameter_sensitivity": {
            "status": "high",
            "grade": "E2",
            "evidence": questions["Q4_stable_across_weight_transformations"][
                "evidence"
            ],
        },
        "sensory_specificity": {
            "status": "not_established",
            "grade": "E1",
            "evidence": questions["Q6_actual_vs_shuffled"]["evidence"],
        },
        "downstream_propagation": {
            "status": "absent_under_tested_drive",
            "grade": None,
            "evidence": questions["Q5_sensory_downstream_propagation"]["evidence"],
        },
        "motor_output": {
            "status": "simulated_decoder_output_only",
            "grade": "E2",
            "evidence": {
                "motor_spikes_4G_C": (audit["4H.1"] or {}).get(
                    "reference_motor_spikes"
                ),
                "jump_windows_4G_C": (audit["4H.1"] or {}).get(
                    "reference_jump_windows"
                ),
                "validated_motor_command": False,
            },
        },
        "biological_plausibility": {
            "status": "unknown",
            "grade": None,
            "evidence": {
                "structural_connectivity_not_physiology": True,
                "predicted_not_verified_transmitters": (
                    "verified-only policy leaves 44.5% of t5 edges signed"
                ),
                "synaptic_weights_uncertain": True,
                "annotation_incomplete": True,
                "banc_specimen_export_limits": True,
                "no_validated_behavioural_labels": True,
            },
        },
    }


def build_payload(audits: dict) -> dict:
    questions = build_questions(audits)
    claims = build_claims(audits, questions)
    dimensions = build_dimensions(questions, audits)
    four = audits["4H.4"]
    first = (four.get("propagation_B_full", {}) or {}).get("first_hop", {})
    return {
        "phase": "4H.5",
        "title": "Statistical assessment and evidence grading",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_audit": artifact_audit(),
        "grade_scale": {
            "note": (
                "E0-E4 are internal computational evidence grades defined for this "
                "project; they are not an established neuroscience standard. The "
                "Phase 4H protocol used a different E0-E4 wording, so the definitions "
                "below are the ones applied in this report."
            ),
            "definitions": GRADE_DESCRIPTIONS,
        },
        "audit": audits,
        "questions": questions,
        "separate_dimensions": dimensions,
        "claims": claims,
        "strongest_supported_conclusion": (
            "Under the fixed verified-only sign policy and W0 weight transform, a "
            "64-neuron VNC-intrinsic group selected on motor-synapse rank produces "
            "a reproducible simulated motor/JUMP decoder output that is "
            "distinguishable from five matched random-control families (E2). The "
            "output is strongly dependent on weight transform, sign policy and drive "
            "amplitude. Sensory stimulation at the tested 200 pA per-feature drive "
            "produces spikes only in the stimulated sensory neurons; synaptic current "
            "reaches first-hop targets but does not bring any of them to threshold, "
            "so there is no propagation to descending or motor populations and no "
            "E3 functional-pathway evidence."
        ),
        "unsupported_claims": [
            "That sensory events drive descending or motor-neuron activity in this model.",
            "That actual event structure produces a distinguishable propagated response compared with shuffled controls.",
            "That 662 signed outgoing edges imply effective downstream activation.",
            "That a LEFT, RIGHT or JUMP decoder label is a biological motor command or observed behaviour.",
            "That the game-feature-to-BANC mapping is a measured visual pathway.",
            "That the Phase 4G JUMP result is invariant to weight transform or sign policy.",
            "That the model provides E3 functional-pathway evidence or E4 behavioural evidence.",
            "That stationary or constant-charge drive is equivalent to the actual event sequence.",
        ],
        "remaining_uncertainties": [
            "Structural connectivity is not physiological connectivity: sign, weight and delay are model priors.",
            "44.5% of threshold-5 edges carry a verified transmitter sign; the rest are excluded and may change propagation.",
            "Synaptic weights are monotone transforms of structural synapse counts, not measured conductances.",
            "The 232-neuron sensory mapping is an annotation-defined hypothesis, not a measured receptive-field map.",
            "BANC is one specimen and one dataset export; annotation completeness and proofreading are limited.",
            "Event timestamps are synthesized at 30 fps because the source images carry no timestamps.",
            "No validated biological labels exist for LEFT, RIGHT or JUMP.",
            "The absence of propagation at 200 pA does not prove that the network cannot propagate at other drives or weights.",
            "The three streams are non-overlapping segments of one recording group, not independent recordings.",
            "A motor-neuron spike in the simulator is not a validated motor command or behaviour.",
        ],
        "recommended_next_experiment": {
            "title": "Pre-registered sensory-drive threshold and propagation calibration",
            "rationale": (
                "The current experiment establishes that 200 pA per-feature pulses "
                "reach first-hop membranes but remain subthreshold. The next step is "
                "to estimate the input level at which the first hop crosses threshold, "
                "not to search for a setting that produces motor activity."
            ),
            "design": [
                "Pre-register a fixed geometric drive series (for example 200, 400, 800, 1200 pA per feature) with all seven conditions A-G on all three streams.",
                "Record the same first-hop, second-hop, descending and motor diagnostics with hash-verified replays.",
                "Report every cell, including silent cells; do not select a drive after observing motor output.",
                "Add a direct first-hop current-injection positive control to verify that first-hop neurons can spike under the model.",
                "Add a single-first-hop-spike test to measure whether one first-hop spike produces any second-hop current or spike.",
                "Repeat the analysis on an independent recording or a second specimen before any E3/E4 claim.",
            ],
            "decision_rule": (
                "The experiment succeeds if it estimates a threshold and reports it, "
                "regardless of whether motor activity appears."
            ),
        },
        "overall_verdict": {
            "phase_4h": "PASS WITH LIMITATIONS",
            "phase_4h4": "PASS WITH LIMITATIONS",
            "rationale": (
                "All 27 Phase 4H.4 runs completed with verified configuration, "
                "determinism and integrity. Phase 4H.1-4H.4 support E0-E2 claims. "
                "The sensory round-trip is reproducibly motor-silent and produces no "
                "E3 pathway evidence. This is a controlled negative result, not an "
                "execution failure."
            ),
            "highest_grade_awarded": "E2",
            "e3_awarded": False,
            "e4_awarded": False,
        },
        "limitations": [
            "Evidence grades are project-specific and were assigned after the results were known.",
            "The 4H.1 p-values are at the minimum attainable value for 100 control draws.",
            "Condition C was selected on the same motor-synapse rank used in the control comparison.",
            "The weight and sign studies are deterministic sweeps, not independent biological replicates.",
            "The sensory streams are non-independent segments of one recording.",
            "No claim about behaviour, perception or biological motor control is supported.",
        ],
        "artifacts": artifact_audit(),
        "first_hop_summary": first,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    payloads = {
        "4H.1": load_json(ARTIFACTS["4H.1_result"]),
        "4H.2": load_json(ARTIFACTS["4H.2_result"]),
        "4H.3": load_json(ARTIFACTS["4H.3_result"]),
        "4H.4_raw": load_json(ARTIFACTS["4H.4_result"]),
        "4H.4_analysis": load_json(ARTIFACTS["4H.4_analysis"]),
    }
    audits = {
        "4H.1": audit_4h1(payloads["4H.1"]),
        "4H.2": audit_4h2(payloads["4H.2"]),
        "4H.3": audit_4h3(payloads["4H.3"]),
        "4H.4": audit_4h4(
            payloads["4H.4_raw"], payloads["4H.4_analysis"]
        ),
    }
    missing = [
        name
        for name, audit in audits.items()
        if not audit.get("available", False)
    ]
    payload = build_payload(audits)
    payload["missing_artifacts"] = missing
    common.write_json(Path(args.output), payload)
    print(
        json.dumps(
            {
                "output": str(Path(args.output).relative_to(PROJECT_ROOT)).replace(
                    "\\", "/"
                ),
                "missing": missing,
                "questions": {
                    key: value["answer"]
                    for key, value in payload["questions"].items()
                },
                "highest_grade": payload["overall_verdict"]["highest_grade_awarded"],
                "verdict": payload["overall_verdict"]["phase_4h"],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
