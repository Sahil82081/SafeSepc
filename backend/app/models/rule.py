"""Rule models complying strictly with SafeSpec fixed Pydantic format.

Format specification:
{
    "id": str,
    "text": str,
    "condition": {"var": str, "op": str, "value": Any},
    "action": {"var": str, "op": str, "value": Any}
}
"""

from typing import Any, Optional, Literal, Dict
from pydantic import BaseModel, Field, model_validator


class RuleCondition(BaseModel):
    """Condition predicate for an automotive requirement rule."""

    var: str = Field(..., description="Telemetry, sensor, or state variable name")
    op: str = Field(..., description="Comparison operator (e.g. '==', '!=', '>', '<', '>=', '<=')")
    value: Any = Field(..., description="Comparison threshold or target constant")

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against a telemetry state dictionary."""
        if self.var not in context:
            return False

        actual = context[self.var]
        expected = self.value

        try:
            if self.op in ("==", "eq"):
                return actual == expected
            elif self.op in ("!=", "neq"):
                return actual != expected
            elif self.op in (">", "gt"):
                return float(actual) > float(expected)
            elif self.op in ("<", "lt"):
                return float(actual) < float(expected)
            elif self.op in (">=", "gte"):
                return float(actual) >= float(expected)
            elif self.op in ("<=", "lte"):
                return float(actual) <= float(expected)
            elif self.op in ("in",):
                return actual in expected
            else:
                return False
        except (ValueError, TypeError):
            return False


class RuleAction(BaseModel):
    """Actuator or state action triggered when a condition is met."""

    var: str = Field(..., description="Target control or actuator variable name")
    op: str = Field(default="=", description="Action assignment operator, typically '=' or '=='")
    value: Any = Field(..., description="Commanded output state or value")

    def apply(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply action on state dictionary and return updated copy."""
        updated = dict(state)
        updated[self.var] = self.value
        return updated


class Rule(BaseModel):
    """Automotive requirement in fixed SafeSpec Pydantic format."""

    id: str = Field(..., description="Unique requirement ID (e.g. REQ-012)")
    text: str = Field(..., description="Full requirement text")
    condition: RuleCondition = Field(..., description="Condition predicate")
    action: RuleAction = Field(..., description="Target action")

    # Metadata fields (optional, supporting ISO 26262 ASIL safety & traceability)
    asil: Optional[Literal["QM", "A", "B", "C", "D"]] = Field(
        default="QM",
        description="Automotive Safety Integrity Level (QM, A, B, C, D)"
    )
    regulation: Optional[str] = Field(
        default=None,
        description="Linked automotive regulation (e.g. UNECE R48)"
    )

    @property
    def is_high_risk(self) -> bool:
        """Rule 9: ASIL C and D are classified as high risk."""
        return self.asil in ("C", "D")

    def to_canonical_dict(self) -> dict[str, Any]:
        """Export rule to the exact canonical 4-key dict specified in Rule 5."""
        return {
            "id": self.id,
            "text": self.text,
            "condition": {
                "var": self.condition.var,
                "op": self.condition.op,
                "value": self.condition.value,
            },
            "action": {
                "var": self.action.var,
                "op": self.action.op,
                "value": self.action.value,
            },
        }
