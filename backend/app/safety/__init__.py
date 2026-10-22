"""SafeSpec Functional Safety & Human Gate Package (Rule 9)."""

from backend.app.safety.approval import (
    ApprovalRecord,
    ApprovalManager,
    ApprovalGateError,
    filter_approved_rules,
)
from backend.app.safety.risk import (
    RiskAssessment,
    evaluate_risk,
)

__all__ = [
    "ApprovalRecord",
    "ApprovalManager",
    "ApprovalGateError",
    "filter_approved_rules",
    "RiskAssessment",
    "evaluate_risk",
]
