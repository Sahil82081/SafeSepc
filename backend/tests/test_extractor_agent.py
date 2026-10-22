"""Pytest suite for RequirementExtractorAgent and Gemini tool calling.

Validates:
1. Gemini LLM client mocking allows offline testing without API keys.
2. Agent extracts all 10 requirements from sample_requirements.pdf.
3. The unclear requirement (REQ-023 with 'quickly') is detected and flagged with HIGH ambiguity.
4. The conflicting pair (REQ-017 and REQ-031) is detected.
5. The door-lock rule (REQ-050) is extracted and verified.
6. Every agent action and tool call is recorded in agent_log SQLite table (Rule 8).
"""

from pathlib import Path
import pytest

from backend.app.config import DOCUMENTS_DIR
from backend.app.models.domain import Requirement
from backend.app.agents.llm import GeminiClient, LLMResponse
from backend.app.agents.extractor import RequirementExtractorAgent
from backend.app.db.session import SessionLocal
from backend.app.db.tables import AgentLogTable


@pytest.fixture
def sample_pdf_path() -> str:
    """Path to generated sample_requirements.pdf."""
    path = DOCUMENTS_DIR / "sample_requirements.pdf"
    assert path.exists(), f"Sample PDF must exist at {path}"
    return str(path)


@pytest.fixture
def mock_gemini_client() -> GeminiClient:
    """Mock Gemini client running offline without API key."""
    def dummy_responder(prompt: str, tools: list) -> LLMResponse:
        return LLMResponse(
            text="Mocked agent extraction response",
            tool_calls=[],
            finish_reason="STOP",
        )
    return GeminiClient(mock_mode=True, mock_responder=dummy_responder)


def test_agent_extracts_all_10_requirements(sample_pdf_path, mock_gemini_client):
    """Core Done Criteria:

    The agent extracts all 10 requirements and flags the unclear one.
    """
    cycle_id = "cycle-test-extractor-10"
    agent = RequirementExtractorAgent(
        llm_client=mock_gemini_client,
        cycle_id=cycle_id,
    )

    requirements = agent.extract(sample_pdf_path)

    # 1. Total count must be 10
    assert len(requirements) == 10, f"Expected exactly 10 extracted requirements, got {len(requirements)}"

    req_map = {r.id: r for r in requirements}

    # Verify all 10 IDs are present
    expected_ids = {
        "REQ-012",
        "REQ-017",
        "REQ-023",
        "REQ-025",
        "REQ-028",
        "REQ-031",
        "REQ-034",
        "REQ-041",
        "REQ-050",
        "REQ-052",
    }
    assert set(req_map.keys()) == expected_ids

    # 2. Unclear requirement with word 'quickly' must be flagged
    req_unclear = req_map["REQ-023"]
    assert "quickly" in req_unclear.text
    assert req_unclear.ambiguity == "HIGH"
    assert "ambiguous" in req_unclear.flags
    assert "quickly" in req_unclear.terms
    assert req_unclear.problem is not None
    assert req_unclear.suggestion is not None
    assert "latency" in req_unclear.problem.lower() or "milliseconds" in req_unclear.suggestion.lower()

    # 3. Conflicting pair (REQ-017 and REQ-031)
    req_017 = req_map["REQ-017"]
    req_031 = req_map["REQ-031"]
    assert "conflict" in req_017.flags
    assert "conflict" in req_031.flags
    assert req_017.conflict_with == "REQ-031"
    assert req_031.conflict_with == "REQ-017"

    # 4. Door-lock rule (REQ-050)
    req_door = req_map["REQ-050"]
    assert "20.0 km/h" in req_door.text
    assert "door" in req_door.text.lower()
    assert req_door.safety is True
    assert req_door.asil == "B"
    assert req_door.ambiguity == "LOW"

    # 5. Verify agent_log table contains thoughts, tool calls, and tool results (Rule 8)
    session = SessionLocal()
    logs = session.query(AgentLogTable).filter_by(cycle_id=cycle_id).all()
    assert len(logs) >= 3, f"Expected at least 3 audit log entries, found {len(logs)}"

    action_types = {l.action_type for l in logs}
    assert "thought" in action_types
    assert "tool_call" in action_types
    assert "tool_result" in action_types

    # Ensure tool calls include read_pdf_page
    tool_names = {l.tool_name for l in logs if l.tool_name}
    assert "read_pdf_page" in tool_names
    session.close()
