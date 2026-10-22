"""Safety Risk Assessment Engine (Rule 9).

Plain deterministic scoring function (NEVER LLM) evaluating:
- Component criticality
- ISO 26262 ASIL level
- Number of affected / failing tests
- Regression test suite results
- Fault-injection testing results

Enforces safety constraint: High risk / ASIL C/D stops for human engineering sign-off.
"""

from typing import Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field

from backend.app.config import HIGH_RISK_ASIL_LEVELS

ASIL_WEIGHTS: Dict[str, float] = {
    "QM": 5.0,
    "A": 15.0,
    "B": 25.0,
    "C": 40.0,
    "D": 50.0,
}

CRITICALITY_WEIGHTS: Dict[str, float] = {
    "LOW": 5.0,
    "MEDIUM": 15.0,
    "HIGH": 25.0,
    "CRITICAL": 35.0,
    # Automotive sub-systems
    "LIGHTING": 15.0,
    "DOOR": 25.0,
    "LOCK": 25.0,
    "BRAKE": 35.0,
    "STEERING": 35.0,
}


class RiskAssessment(BaseModel):
    """Structured safety risk evaluation output."""

    score: float = Field(..., description="Overall risk score between 0.0 and 100.0")
    level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Categorical risk tier")
    is_high_risk: bool = Field(..., description="True if risk level is HIGH or CRITICAL")
    requires_human_signoff: bool = Field(..., description="Rule 9: Human engineer sign-off required")
    asil: str = Field(default="QM", description="Evaluated ASIL level")
    criticality: str = Field(default="MEDIUM", description="Evaluated component criticality")
    factors: Dict[str, Any] = Field(default_factory=dict, description="Factor-by-factor score breakdown")
    summary: str = Field(..., description="Summary explanation of the risk assessment")


def evaluate_risk(
    criticality: Union[str, float] = "MEDIUM",
    asil: str = "QM",
    affected_tests_count: int = 1,
    regression_passed: bool = True,
    fault_injection_passed: bool = True,
) -> RiskAssessment:
    """Evaluate automotive software modification risk using plain code scoring (no LLM).

    Args:
        criticality: System criticality rating ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') or component name.
        asil: Automotive Safety Integrity Level ('QM', 'A', 'B', 'C', 'D').
        affected_tests_count: Number of failing or touched test cases.
        regression_passed: True if full regression test suite passed without regression.
        fault_injection_passed: True if ECU survived fault-injection without unsafe state.

    Returns:
        Structured RiskAssessment with score, level, and human signoff flag.
    """
    clean_asil = asil.upper().strip() if isinstance(asil, str) else "QM"
    asil_score = ASIL_WEIGHTS.get(clean_asil, 5.0)

    # Resolve criticality score
    if isinstance(criticality, (int, float)):
        crit_score = float(criticality)
        crit_label = "CUSTOM"
    else:
        crit_label = str(criticality).upper().strip()
        crit_score = CRITICALITY_WEIGHTS.get(crit_label, 15.0)

    # Test count impact: 5 pts per affected test, capped at 25 pts
    test_score = min(float(max(0, affected_tests_count)) * 5.0, 25.0)

    # Regression penalty: +30 pts if regression suite broke
    reg_score = 0.0 if regression_passed else 30.0

    # Fault injection penalty: +20 pts if fault-injection failed
    fault_score = 0.0 if fault_injection_passed else 20.0

    raw_score = asil_score + crit_score + test_score + reg_score + fault_score
    final_score = round(min(100.0, max(0.0, raw_score)), 2)

    # Determine risk category
    if final_score >= 80.0:
        level = "CRITICAL"
    elif final_score >= 60.0:
        level = "HIGH"
    elif final_score >= 30.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    is_high = level in ("HIGH", "CRITICAL")

    # Rule 9: ASIL C and D, or High Risk, or failed regressions require human sign-off
    requires_human = (
        clean_asil in HIGH_RISK_ASIL_LEVELS
        or is_high
        or not regression_passed
    )

    factors = {
        "asil": {"value": clean_asil, "points": asil_score},
        "criticality": {"value": crit_label, "points": crit_score},
        "affected_tests": {"count": affected_tests_count, "points": test_score},
        "regression": {"passed": regression_passed, "points": reg_score},
        "fault_injection": {"passed": fault_injection_passed, "points": fault_score},
        "raw_total": raw_score,
    }

    summary_parts = [f"Risk score: {final_score}/100 ({level}) for ASIL {clean_asil}."]
    if not regression_passed:
        summary_parts.append("REGRESSION FAILURE DETECTED (+30).")
    if not fault_injection_passed:
        summary_parts.append("FAULT INJECTION FAILURE (+20).")
    if requires_human:
        summary_parts.append("Rule 9: Modification is high-risk; stops and waits for human engineering sign-off.")
    else:
        summary_parts.append("Risk level within automated approval boundaries.")

    return RiskAssessment(
        score=final_score,
        level=level,
        is_high_risk=is_high,
        requires_human_signoff=requires_human,
        asil=clean_asil,
        criticality=crit_label,
        factors=factors,
        summary=" ".join(summary_parts),
    )
