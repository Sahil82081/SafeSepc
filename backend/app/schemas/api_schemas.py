"""SafeSpec API Request and Response Schemas."""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

from backend.app.models.domain import (
    Requirement,
    Rule,
    RuleCondition,
    RuleAction,
    Conflict,
    TestCase,
    Result,
    Fix,
    RiskReport,
)


class RunUploadResponse(BaseModel):
    """Response returned upon successful PDF specification upload."""

    run_id: str
    filename: str
    filepath: str
    status: str
    message: str


class RunStartRequest(BaseModel):
    """Optional configuration for initiating a run."""

    ecu_version: str = Field(default="v1", description="Initial VirtualECU version to evaluate")
    target_req_id: str = Field(default="REQ-050", description="Target requirement to test")
    use_interrupt_for_human: bool = Field(default=False, description="Whether to interrupt for interactive human review")


class RunResponse(BaseModel):
    """Status and summary of an end-to-end verification run."""

    id: Optional[int] = None
    run_id: str
    pipeline_stage: str
    status: str
    total_requirements: int = 0
    flagged_count: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    """Payload for engineer sign-off decision."""

    note: Optional[str] = Field(default=None, description="Engineer justification or note")
    decided_by: str = Field(default="safety_engineer", description="Name/ID of the decision maker")


class ApprovalItemResponse(BaseModel):
    """Approval queue item."""

    id: str
    req_id: str
    kind: str
    title: str
    original_text: Optional[str] = None
    proposed_text: Optional[str] = None
    rule: Optional[Dict[str, Any]] = None
    back_translation: Optional[str] = None
    asil_level: str
    status: str
    decision_note: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    created_at: Optional[str] = None


class TraceabilityNode(BaseModel):
    """Node in the end-to-end requirement traceability DAG."""

    id: str
    label: str
    type: Literal["requirement", "rule", "test", "result", "fix", "conflict"]
    status: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TraceabilityEdge(BaseModel):
    """Directed link in the requirement traceability graph."""

    source: str
    target: str
    label: Optional[str] = None
    type: str = "verifies"


class TraceabilityGraphResponse(BaseModel):
    """Full traceability graph representing requirements to code and test proof."""

    run_id: str
    nodes: List[TraceabilityNode]
    edges: List[TraceabilityEdge]


class DashboardStatsResponse(BaseModel):
    """Aggregated platform KPI metrics."""

    total_runs: int
    total_requirements: int
    flagged_count: int
    tests_passed: int
    tests_failed: int
    pass_rate: float
    pending_approvals: int
    active_ecu_version: str


class ReportResponse(BaseModel):
    """Generated verification report paths and markdown content."""

    run_id: str
    markdown_content: str
    markdown_path: str
    pdf_path: Optional[str] = None
    generated_at: str
