"""Tests for the Phase 4H.5 evidence aggregation and grade assignment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_4h import assess_phase_4h as assess  # noqa: E402


def make_audit(
    *,
    non_stimulated_spikes: int = 0,
    first_hop_spikes: int = 0,
    descending_spikes: int = 0,
    motor_spikes: int = 0,
    confirmatory: bool = True,
    jump_windows: bool = True,
) -> dict:
    condition = {
        "total_spikes": 3562,
        "stimulated_spikes": 3562,
        "non_stimulated_spikes": non_stimulated_spikes,
        "motor_spikes": motor_spikes,
        "decoded_state_counts": {"NEUTRAL": 67},
    }
    return {
        "4H.1": {
            "available": True,
            "integrity_pass": True,
            "reference_motor_spikes": 492.0 if jump_windows else 0.0,
            "reference_jump_windows": 4.0 if jump_windows else 0.0,
            "p_values_p1": {"W0_random_matched": 0.00990099},
            "p_values_p2": {"W0_random_matched": 0.00990099},
            "holm_rejected_p1": ["W0_random_matched"],
            "holm_rejected_p2": ["W0_random_matched"],
            "any_confirmatory_difference": confirmatory,
            "spike_hash_matches_phase_4g": True,
            "families": ["W0_random_matched"],
        },
        "4H.2": {
            "available": True,
            "integrity_pass": True,
            "connectivity_size_curve": {64: {"motor_spikes": 492.0}},
            "confirmatory": {"any_confirmatory_difference": confirmatory},
        },
        "4H.3": {
            "available": True,
            "integrity_pass": True,
            "preregistration_matches": True,
            "config_summary": {
                "D0_W0_S0": {
                    "weight": "W0",
                    "sign": "S0",
                    "drive": "D0",
                    "current_pa": 300.0,
                    "motor_spikes": 492.0,
                    "jump_windows": 4.0,
                    "silent": False,
                },
                "D0_W1_S0": {
                    "weight": "W1",
                    "sign": "S0",
                    "drive": "D0",
                    "current_pa": 300.0,
                    "motor_spikes": 5.0,
                    "jump_windows": 0.0,
                    "silent": False,
                },
                "D0_W2_S0": {
                    "weight": "W2",
                    "sign": "S0",
                    "drive": "D0",
                    "current_pa": 300.0,
                    "motor_spikes": 0.0,
                    "jump_windows": 0.0,
                    "silent": True,
                },
            },
            "s2_equals_s0": True,
            "w4_equals_w1": True,
            "cap_saturation": {"edges_at_cap_W0": 643},
            "unavailable_family": {"status": "unavailable"},
        },
        "4H.4": {
            "available": True,
            "integrity_pass": True,
            "determinism": {
                stream: {
                    "B_actual": {
                        "spike_hash_equal": True,
                        "decision_hash_equal": True,
                    },
                    "G_background_noise": {
                        "spike_hash_equal": True,
                        "decision_hash_equal": True,
                    },
                }
                for stream in ("full_100_199", "seg_0_99", "seg_200_299")
            },
            "condition_tables": {
                stream: {
                    "A_no_events": dict(condition, total_spikes=0, stimulated_spikes=0),
                    "B_actual": dict(condition),
                    "C_temporal_shuffle": dict(condition, total_spikes=3760, stimulated_spikes=3760),
                    "D_feature_identity_shuffle": dict(condition, total_spikes=3648, stimulated_spikes=3648),
                    "E_random_matched_mapping": dict(condition, total_spikes=3561, stimulated_spikes=3561),
                    "F_constant_matched_charge": dict(condition, total_spikes=0, stimulated_spikes=0),
                    "G_background_noise": dict(condition, total_spikes=0, stimulated_spikes=0),
                }
                for stream in ("full_100_199", "seg_0_99", "seg_200_299")
            },
            "full_stream_B": {
                "total_spikes": 3562,
                "stimulated_spikes": 3562,
                "non_stimulated_spikes": non_stimulated_spikes,
                "motor_spikes": motor_spikes,
                "decoded_state_counts": {"NEUTRAL": 67},
                "event_locked_downstream_spikes": 0,
                "alignment_best_r": None,
            },
            "propagation_B_full": {
                "structure": {
                    "first_hop_downstream_targets": 607,
                    "second_hop_motor": 4,
                },
                "transmission": {"signed_transmissions": 9499},
                "first_hop": {
                    "n": 607,
                    "spikes": first_hop_spikes,
                    "receiving_neurons": 473,
                    "max_synaptic_current_pa": 164.44,
                    "max_membrane_mv": -56.926,
                    "closest_deficit_mv": 6.926,
                },
                "second_hop": {"n": 3576, "spikes": 0},
                "descending": {
                    "n": 1316,
                    "spikes": descending_spikes,
                    "receiving_neurons": 9,
                    "max_membrane_mv": -62.158,
                    "closest_deficit_mv": 12.158,
                },
                "motor": {
                    "n": 805,
                    "spikes": motor_spikes,
                    "receiving_neurons": 0,
                    "max_membrane_mv": -65.0,
                    "closest_deficit_mv": 15.0,
                },
                "non_stimulated_non_motor": {"n": 171628, "spikes": 0},
            },
        },
    }


def test_award_grade_selects_highest_satisfied_level():
    assert assess.award_grade({"e0": True}) == "E0"
    assert assess.award_grade({"e0": True, "e1": True, "e2": True}) == "E2"
    assert assess.award_grade(
        {"e0": True, "e1": True, "e2": True, "e3": True, "e4": True}
    ) == "E4"
    assert assess.award_grade({}) is None


def test_award_grade_gap_does_not_skip_levels():
    # A missing lower criterion must not let a higher criterion win.
    assert assess.award_grade({"e0": True, "e2": True}) == "E2"


def test_summarise_condition_endpoint_aggregates_streams():
    audit = make_audit()
    audit["4H.4"]["condition_tables"]["seg_0_99"]["B_actual"]["total_spikes"] = 1990
    audit["4H.4"]["condition_tables"]["seg_200_299"]["B_actual"]["total_spikes"] = 2001
    summary = assess.summarise_condition_endpoint(
        audit["4H.4"], "total_spikes", ("B_actual", "A_no_events")
    )
    b = summary["B_actual"]
    assert b["n"] == 3
    assert b["values"] == [3562.0, 1990.0, 2001.0]
    assert b["mean"] == pytest.approx(2517.6666667, rel=1e-6)
    assert b["sd"] is not None
    assert summary["A_no_events"]["mean"] == 0.0
    assert summary["A_no_events"]["sd"] == 0.0


def test_summarise_condition_endpoint_handles_missing_rows():
    audit = {"condition_tables": {"full_100_199": {}}}
    summary = assess.summarise_condition_endpoint(
        audit, "total_spikes", ("B_actual",)
    )
    assert summary["B_actual"] == {"n": 0, "mean": None, "sd": None, "values": []}


def test_nominal_weight_family_rows_excludes_matched_amplitude():
    rows = assess.nominal_weight_family_rows(
        {
            "D0_W0_S0": {"drive": "D0"},
            "D1_W1_S0": {"drive": "D1"},
            "D0_W1_S0": {"drive": "D0"},
        }
    )
    assert sorted(rows) == ["D0_W0_S0", "D0_W1_S0"]


def test_weight_sensitivity_is_observed():
    varied = {
        "a": {"drive": "D0", "motor_spikes": 492.0, "jump_windows": 4.0},
        "b": {"drive": "D0", "motor_spikes": 0.0, "jump_windows": 0.0},
    }
    identical = {
        "a": {"drive": "D0", "motor_spikes": 492.0, "jump_windows": 4.0},
        "b": {"drive": "D0", "motor_spikes": 492.0, "jump_windows": 4.0},
    }
    assert assess.weight_sensitivity_is_observed(varied) is True
    assert assess.weight_sensitivity_is_observed(identical) is False
    assert assess.weight_sensitivity_is_observed({}) is False


def test_claims_never_award_e3_or_e4_without_pathway_evidence():
    claims = assess.build_claims(make_audit(), assess.build_questions(make_audit()))
    grades = {claim["id"]: claim["grade"] for claim in claims}
    assert grades["C07_sensory_downstream_propagation"] is None
    assert grades["C08_actual_vs_shuffled_propagated_response"] is None
    assert grades["C09_descending_motor_recruitment"] is None
    assert grades["C10_decoder_is_validated_motor_command"] is None
    assert "E3" not in grades.values()
    assert "E4" not in grades.values()


def test_even_motor_spikes_do_not_raise_the_grade_of_pathway_claims():
    audit = make_audit(
        non_stimulated_spikes=12,
        first_hop_spikes=6,
        descending_spikes=3,
        motor_spikes=2,
    )
    claims = assess.build_claims(audit, assess.build_questions(audit))
    grades = {claim["id"]: claim["grade"] for claim in claims}
    # E3 is decided by the pre-specified pathway criterion, not by observed spikes.
    assert grades["C07_sensory_downstream_propagation"] is None
    assert grades["C09_descending_motor_recruitment"] is None
    assert grades["C10_decoder_is_validated_motor_command"] is None


def test_supported_claims_receive_their_highest_satisfied_grade():
    claims = assess.build_claims(make_audit(), assess.build_questions(make_audit()))
    grades = {claim["id"]: claim["grade"] for claim in claims}
    assert grades["C01_integrity_determinism"] == "E0"
    assert grades["C02_stimulated_sensory_spiking"] == "E1"
    assert grades["C03_condition_c_decoder_output"] == "E1"
    assert grades["C04_condition_c_vs_random_controls"] == "E2"
    assert grades["C06_weight_sign_drive_sensitivity"] == "E2"


def test_claims_carry_dimension_and_not_awarded_grade():
    claims = assess.build_claims(make_audit(), assess.build_questions(make_audit()))
    by_id = {claim["id"]: claim for claim in claims}
    assert by_id["C07_sensory_downstream_propagation"]["dimension"] == (
        "downstream_propagation"
    )
    assert by_id["C10_decoder_is_validated_motor_command"][
        "highest_grade_not_awarded"
    ] == "E4"
    assert by_id["C07_sensory_downstream_propagation"][
        "highest_grade_not_awarded"
    ] == "E3"
    assert all("grade_definition" in claim for claim in claims)


def test_questions_answers_follow_the_audited_values():
    audit = make_audit()
    questions = assess.build_questions(audit)
    assert questions["Q1_decoder_deterministic"]["answer"] == "yes"
    assert questions["Q5_sensory_downstream_propagation"]["answer"] == "no"
    assert questions["Q7_activity_reaches_descending_and_motor"]["answer"] == "no"
    assert questions["Q6_actual_vs_shuffled"]["answer"] == "partial_at_input_only"
    assert questions["Q4_stable_across_weight_transformations"]["answer"] == "no"


def test_dimensions_keep_reproducibility_separate_from_biology():
    audit = make_audit()
    dimensions = assess.build_dimensions(assess.build_questions(audit), audit)
    assert dimensions["reproducibility"]["grade"] == "E0"
    assert dimensions["downstream_propagation"]["grade"] is None
    assert dimensions["biological_plausibility"]["grade"] is None
    assert dimensions["motor_output"]["grade"] == "E2"
