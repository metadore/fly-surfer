"""Phase 5G: assessment helpers, config validation and verdict logic."""

from __future__ import annotations

import math

import pytest

from experiments.phase_5 import final_assessment as assessment
from plasticity.config import load_plasticity_config
from plasticity.tasks import load_task_config


@pytest.fixture(scope="module")
def configs():
    plasticity = load_plasticity_config(assessment.PLASTICITY_CONFIG_PATH)
    task, _ = load_task_config(assessment.TASK_CONFIG_PATH)
    return plasticity, task


def test_pytest_summary_parsing():
    parsed = assessment._parse_pytest(
        "2 failed, 10 passed, 3 skipped, 1 error in 2.0s"
    )
    assert parsed == {"passed": 10, "failed": 2, "skipped": 3, "errors": 1}
    assert assessment._parse_pytest("no tests ran") == {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
    }


def test_non_finite_scan_finds_float_and_numpy_values():
    payload = {"ok": 1.0, "bad": math.nan, "nested": {"inf": math.inf}}
    found = list(assessment._walk_numbers(payload))
    assert "$.bad" in found
    assert "$.nested.inf" in found
    assert len(found) == 2


def test_configuration_validation_passes(configs):
    result = assessment.validate_configs(*configs)
    assert result["passed"] is True
    assert result["checks"]["core_contrast_family_declared"] is True
    assert result["checks"]["rejects_single_cue"] is True


def test_verdicts_require_all_software_blocks():
    software = {
        key: {"passed": True}
        for key in (
            "tests",
            "configuration",
            "checkpoint",
            "determinism",
            "stability",
            "integrity",
        )
    }
    five_f = {
        "core": {
            "contrasts": {
                assessment.PRIMARY_CONTRAST: {
                    "holm_rejected": True,
                    "mean_difference": 0.1,
                }
            }
        }
    }
    verdicts = assessment.build_verdicts(software, [], five_f)
    assert verdicts["A_software"]["verdict"] == "PASS"
    assert verdicts["B_controlled_learning"]["verdict"] == "PASS WITH LIMITATIONS"
    assert verdicts["C_statistical_evidence"]["verdict"] == "PASS WITH LIMITATIONS"
    assert verdicts["D_biological_interpretation"]["verdict"] == "INCONCLUSIVE"

    software["tests"]["passed"] = False
    verdicts = assessment.build_verdicts(software, [], five_f)
    assert verdicts["A_software"]["verdict"] == "FAIL"


def test_verdicts_are_inconclusive_without_significance():
    software = {
        key: {"passed": True}
        for key in (
            "tests",
            "configuration",
            "checkpoint",
            "determinism",
            "stability",
            "integrity",
        )
    }
    five_f = {
        "core": {
            "contrasts": {
                assessment.PRIMARY_CONTRAST: {
                    "holm_rejected": False,
                    "mean_difference": 0.02,
                }
            }
        }
    }
    verdicts = assessment.build_verdicts(software, [], five_f)
    assert verdicts["C_statistical_evidence"]["verdict"] == "INCONCLUSIVE"
