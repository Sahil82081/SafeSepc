"""SafeSpec Pydantic Domain Models.

Includes:
- Requirement: Natural language automotive requirement specification
- Rule: Fixed format rule {id, text, condition:{var,op,value}, action:{var,op,value}} (Rule 5)
- Conflict: Contradiction or overlap detected between two rules
- TestCase: Structured executable test case (expected values from plain code - Rule 4)
- Result: Test execution outcome and comparison
- Fix: Candidate modification proposal for conflicting/ambiguous requirements
- RiskReport: ISO 26262 ASIL assessment and human sign-off report (Rule 9)
"""

from typing import Any, Optional, List, Dict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


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
    """Actuator or state action triggered when condition holds."""

    var: str = Field(..., description="Target control or actuator variable name")
    op: str = Field(default="=", description="Action assignment operator, typically '=' or '=='")
    value: Any = Field(..., description="Commanded output state or value")

    def apply(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply action on state dictionary and return updated copy."""
        updated = dict(state)
        updated[self.var] = self.value
        return updated


class Rule(BaseModel):
    """Rule model adhering strictly to Rule 5 fixed Pydantic format.

    Format:
    {id, text, condition:{var,op,value}, action:{var,op,value}}
    """

    id: str = Field(..., description="Unique rule identifier (e.g. REQ-012)")
    text: str = Field(..., description="Requirement text")
    condition: RuleCondition = Field(..., description="Trigger condition")
    action: RuleAction = Field(..., description="Commanded action")
    asil: Optional[Literal["QM", "A", "B", "C", "D"]] = Field(
        default="QM",
        description="Automotive Safety Integrity Level"
    )
    regulation: Optional[str] = Field(
        default=None,
        description="Regulation clause reference (e.g. UNECE R48)"
    )

    @property
    def is_high_risk(self) -> bool:
        """Rule 9: ASIL C and D are classified as high risk."""
        return self.asil in ("C", "D")

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Export rule to canonical 4-key dict specified in Rule 5."""
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


class Requirement(BaseModel):
    """Automotive engineering requirement extracted from specifications."""

    id: str = Field(..., description="Requirement ID (e.g. REQ-012)")
    text: str = Field(..., description="Requirement statement")
    flags: List[str] = Field(default_factory=list, description="Quality flags (conflict, ambiguous, missing, untestable)")
    terms: List[str] = Field(default_factory=list, description="Specific terms highlighted by agent")
    safety: bool = Field(default=False, description="True if requirement has safety implications")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(default="QM", description="ISO 26262 ASIL level")
    regulation: Optional[str] = Field(default=None, description="Linked standard (e.g. UNECE R48)")
    chunk_id: Optional[str] = Field(default=None, description="Source chunk ID in vector/graph index")
    chunk_text: Optional[str] = Field(default=None, description="Grounding text excerpt from standard")
    tests: List[str] = Field(default_factory=list, description="IDs of linked test cases")
    note: Optional[str] = Field(default=None, description="Quality agent analytical note")
    conflict_with: Optional[str] = Field(default=None, description="Conflicting requirement ID if any")
    ambiguity: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(default="LOW", description="Ambiguity severity rating")
    problem: Optional[str] = Field(default=None, description="Identified quality problem or vague wording")
    suggestion: Optional[str] = Field(default=None, description="Proposed measurable clarification or fix")


class Conflict(BaseModel):
    """Detected formal contradiction or operational conflict between rules."""

    id: str = Field(..., description="Conflict identifier (e.g. CONF-001)")
    rule_a_id: str = Field(..., description="First conflicting rule ID")
    rule_b_id: str = Field(..., description="Second conflicting rule ID")
    description: str = Field(..., description="Explanation of conflict")
    overlap_condition: Dict[str, Any] = Field(default_factory=dict, description="State space where both conditions hold")
    counter_example: Optional[Dict[str, Any]] = Field(default=None, description="Concrete counter-example assignment")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(default="HIGH", description="Conflict severity")
    status: Literal["open", "resolved", "dismissed"] = Field(default="open", description="Resolution status")

    @property
    def reason(self) -> str:
        """Alias for short reason description."""
        return self.description

    def model_post_init(self, __context: Any) -> None:
        """Synchronize counter_example and overlap_condition."""
        if self.counter_example is None and self.overlap_condition:
            self.counter_example = dict(self.overlap_condition)
        elif self.counter_example is not None and not self.overlap_condition:
            self.overlap_condition = dict(self.counter_example)


class TestCase(BaseModel):
    """Executable test scenario generated from requirement rules (Rule 4)."""

    __test__ = False  # Instruct pytest not to treat this domain model as a test suite

    id: str = Field(..., description="Test identifier (e.g. T-01)")
    req_id: str = Field(..., description="Parent requirement ID")
    rule_id: Optional[str] = Field(default=None, description="Linked rule ID")
    name: str = Field(..., description="Human-readable scenario description")
    scenario: Optional[str] = Field(default=None, description="BDD Gherkin style scenario description")
    given: Dict[str, Any] = Field(default_factory=dict, description="Preconditions and telemetry input signals")
    expected: str = Field(..., description="Expected output state, derived deterministically from plain code")
    latency: Optional[float] = Field(default=None, description="Maximum permitted reaction latency in ms")
    is_assumed: bool = Field(default=False, description="True if test uses an unconfirmed assumption for an ambiguous rule")


class Result(BaseModel):
    """Outcome of test case execution against simulated ECU."""

    test_id: str = Field(..., description="ID of executed test case")
    requirement_id: Optional[str] = Field(default=None, description="Linked requirement ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Test input parameters")
    passed: bool = Field(..., description="Pass/fail status")
    expected_value: Any = Field(..., description="Expected deterministic value")
    actual_value: Any = Field(..., description="Observed value from ECU execution")
    status: Optional[str] = Field(default=None, description="Status label ('PASSED' or 'FAILED')")
    logs: List[str] = Field(default_factory=list, description="Execution logs / telemetry traces")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Diagnostic error details if failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Test completion timestamp")

    @property
    def expected(self) -> Any:
        """Alias for expected_value."""
        return self.expected_value

    @property
    def actual(self) -> Any:
        """Alias for actual_value."""
        return self.actual_value

    def model_post_init(self, __context: Any) -> None:
        """Synchronize status and expected/actual fields."""
        if self.status is None:
            self.status = "PASSED" if self.passed else "FAILED"


class Fix(BaseModel):
    """Proposed correction or rewrite generated for human engineering review."""

    id: str = Field(..., description="Fix proposal ID (e.g. A-101)")
    target_req_id: str = Field(..., description="Requirement ID targeted for fix")
    conflict_id: Optional[str] = Field(default=None, description="Associated conflict ID if resolving conflict")
    proposed_text: str = Field(..., description="Rewritten requirement text")
    proposed_rule: Optional[Rule] = Field(default=None, description="Structured rule corresponding to rewrite")
    diff: Optional[str] = Field(default=None, description="Unified text diff vs current requirement")
    grounding_score: float = Field(default=0.0, description="Critic grounding score (0.0 - 100.0%)")
    critic_notes: Optional[str] = Field(default=None, description="Critic verification evaluation")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(default="QM", description="ASIL risk classification")
    status: Literal["pending", "approved", "rejected"] = Field(default="pending", description="Human sign-off status")


class RiskReport(BaseModel):
    """Safety hazard and risk analysis report adhering to ISO 26262 (Rule 9)."""

    req_id: str = Field(..., description="Requirement ID analyzed")
    asil: Literal["QM", "A", "B", "C", "D"] = Field(..., description="Automotive Safety Integrity Level")
    hazard_description: str = Field(..., description="Potential operational hazard")
    safety_goal: str = Field(..., description="Prescribed functional safety goal")
    requires_human_signoff: bool = Field(default=False, description="True for ASIL C/D requiring engineer sign-off")
    status: Literal["pending", "approved", "rejected"] = Field(default="pending", description="Sign-off status")

    def model_post_init(self, __context: Any) -> None:
        """Enforce Rule 9: ASIL C and D always require human sign-off."""
        if self.asil in ("C", "D"):
            self.requires_human_signoff = True
