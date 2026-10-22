"""Tests for Safety Risk Assessment Engine (Rule 9).

Validates:
1. Plain code scoring function (no LLM).
2. ASIL scaling (QM, A, B, C, D).
3. Impact of component criticality.
4. Regression failure penalty (+30 pts).
5. Fault injection failure penalty (+20 pts).
6. Rule 9 compliance: High risk / ASIL C/D stops for human engineer sign-off.
"""

import pytest
from backend.app.safety.risk import evaluate_risk, RiskAssessment


def test_evaluate_risk_low_risk_qm():
    """Verify QM with 1 passing test has low risk score and no mandatory human stop."""
    res = evaluate_risk(
        criticality="LOW",
        asil="QM",
        affected_tests_count=1,
        regression_passed=True,
        fault_injection_passed=True,
    )

    assert isinstance(res, RiskAssessment)
    assert res.score < 30.0
    assert res.level == "LOW"
    assert res.is_high_risk is False
    assert res.requires_human_signoff is False


def test_evaluate_risk_high_risk_asil_d():
    """Rule 9: ASIL D always requires human sign-off regardless of test count."""
    res = evaluate_risk(
        criticality="BRAKE",
        asil="D",
        affected_tests_count=2,
        regression_passed=True,
        fault_injection_passed=True,
    )

    assert res.score >= 60.0
    assert res.is_high_risk is True
    assert res.requires_human_signoff is True
    assert res.asil == "D"


def test_evaluate_risk_regression_failure_penalty():
    """Verify regression failure adds +30 points penalty and forces human sign-off."""
    res_clean = evaluate_risk(
        criticality="DOOR",
        asil="B",
        affected_tests_count=1,
        regression_passed=True,
        fault_injection_passed=True,
    )

    res_broken = evaluate_risk(
        criticality="DOOR",
        asil="B",
        affected_tests_count=1,
        regression_passed=False,
        fault_injection_passed=True,
    )

    assert pytest.approx(res_broken.score - res_clean.score, 0.1) == 30.0
    assert res_broken.requires_human_signoff is True


def test_evaluate_risk_fault_injection_failure_penalty():
    """Verify fault injection failure adds +20 points penalty."""
    res_clean = evaluate_risk(
        criticality="DOOR",
        asil="B",
        affected_tests_count=1,
        regression_passed=True,
        fault_injection_passed=True,
    )

    res_fault = evaluate_risk(
        criticality="DOOR",
        asil="B",
        affected_tests_count=1,
        regression_passed=True,
        fault_injection_passed=False,
    )

    assert pytest.approx(res_fault.score - res_clean.score, 0.1) == 20.0
