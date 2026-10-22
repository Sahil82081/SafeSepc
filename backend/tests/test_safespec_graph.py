"""Tests for SafeSpec LangGraph Workflow & Supervisor (Rule 4, Rule 7, Rule 8, Rule 9, Rule 10).

Validates:
1. Supervisor node picks next node (extractor, formalizer, z3, tester, diagnosis, risk, human_review).
2. Supervisor only chooses next step; never marks rules or fixes correct (Rule 4).
3. Every decision and reason goes to agent_log (Rule 8).
4. Step limit prevents infinite loops (Rule 7).
5. Conditional edges:
   - Z3 conflict goes to human_review.
   - Test fail goes to diagnosis.
   - High risk goes to human_review using interrupt() (Rule 9).
6. SQLite checkpointer saves state across transitions.
7. Full flow runs from PDF to final result on sample PDF.
"""

import pytest
import sqlite3
import uuid
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from backend.app.config import DOCUMENTS_DIR
from backend.app.workflows.safespec_graph import (
    build_safespec_graph,
    SafeSpecGraphState,
    SafeSpecSupervisor,
    MAX_GRAPH_STEPS,
)
from backend.app.db.tables import AgentLogTable
from backend.app.db.session import SessionLocal


@pytest.fixture
def in_memory_checkpointer():
    """Create an in-memory SQLite checkpointer for isolated unit testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return SqliteSaver(conn)


def test_supervisor_decisions_and_logging():
    """Verify Supervisor only picks the next node and logs every decision to agent_log (Rule 4, Rule 8)."""
    supervisor = SafeSpecSupervisor()
    cycle_id = f"cycle-test-sup-{uuid.uuid4().hex[:8]}"

    # State 1: Empty state -> extractor
    state1: SafeSpecGraphState = {
        "cycle_id": cycle_id,
        "requirements": [],
        "step_count": 0,
        "max_steps": 10,
    }
    dec1 = supervisor.decide_next_node(state1)
    assert dec1["next_node"] == "extractor"
    assert "Requirements" in dec1["supervisor_reason"] or "Extractor" in dec1["supervisor_reason"]

    # State 2: Requirements present, formalized missing -> formalizer
    state2: SafeSpecGraphState = {
        "cycle_id": cycle_id,
        "requirements": [{"id": "REQ-050", "text": "lock doors"}],
        "step_count": 1,
        "max_steps": 10,
    }
    dec2 = supervisor.decide_next_node(state2)
    assert dec2["next_node"] == "formalizer"

    # State 3: Step limit exceeded -> halts to prevent infinite loop (Rule 7)
    state3: SafeSpecGraphState = {
        "cycle_id": cycle_id,
        "requirements": [{"id": "REQ-050", "text": "lock doors"}],
        "step_count": 10,
        "max_steps": 10,
    }
    dec3 = supervisor.decide_next_node(state3)
    assert dec3["next_node"] == "__end__"
    assert "Step limit" in dec3["supervisor_reason"]

    # Verify agent_log table contains supervisor thoughts and decisions (Rule 8)
    session = SessionLocal()
    try:
        logs = session.query(AgentLogTable).filter_by(cycle_id=cycle_id, agent_name="supervisor").all()
        assert len(logs) == 3
        assert any("extractor" in l.thought for l in logs)
        assert any("formalizer" in l.thought for l in logs)
        assert any("Step limit" in l.thought for l in logs)
    finally:
        session.close()


def test_conditional_edges_routing():
    """Verify conditional edge routing rules: Z3 conflict -> human_review, test fail -> diagnosis, high risk -> human_review."""
    from backend.app.workflows.safespec_graph import route_from_z3, route_from_tester, route_from_risk

    # 1. Z3 conflict routes to human_review
    state_conflict: SafeSpecGraphState = {
        "conflicts": [{"id": "CONF-01", "rule_a_id": "REQ-017", "rule_b_id": "REQ-031"}],
        "z3_reviewed": False,
    }
    assert route_from_z3(state_conflict) == "human_review"

    # Once reviewed, returns to supervisor
    state_conflict["z3_reviewed"] = True
    assert route_from_z3(state_conflict) == "supervisor"

    # 2. Test fail routes to diagnosis
    state_fail: SafeSpecGraphState = {
        "failing_results": [{"test_id": "TC-01", "passed": False}],
    }
    assert route_from_tester(state_fail) == "diagnosis"

    state_pass: SafeSpecGraphState = {
        "failing_results": [],
    }
    assert route_from_tester(state_pass) == "supervisor"

    # 3. High risk routes to human_review
    state_risk_high: SafeSpecGraphState = {
        "risk_assessment": {"score": 75.0, "requires_human_signoff": True},
        "risk_reviewed": False,
    }
    assert route_from_risk(state_risk_high) == "human_review"

    state_risk_low: SafeSpecGraphState = {
        "risk_assessment": {"score": 20.0, "requires_human_signoff": False},
        "risk_reviewed": False,
    }
    assert route_from_risk(state_risk_low) == "supervisor"


def test_sqlite_checkpointer_and_interrupt_resume(in_memory_checkpointer):
    """Verify state is preserved with SQLite checkpointer and resumes from interrupt() (Rule 9)."""
    graph = build_safespec_graph(checkpointer=in_memory_checkpointer)
    thread_id = f"thread-test-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # Provide state with high risk and enable interrupt
    initial_state: SafeSpecGraphState = {
        "pdf_path": str(DOCUMENTS_DIR / "sample_requirements.pdf"),
        "cycle_id": f"cycle-int-{uuid.uuid4().hex[:8]}",
        "ecu_version": "v1",
        "target_req_id": "REQ-050",
        "use_interrupt_for_human": True,
        # Seed state up to risk to test interrupt cleanly
        "requirements": [{"id": "REQ-050", "text": "lock doors"}],
        "formalized": [{"req_id": "REQ-050", "status": "formalized"}],
        "approved_rules": [{"id": "REQ-050", "text": "lock", "condition": {"var": "speed", "op": ">", "value": 20.0}, "action": {"var": "door", "op": "=", "value": "LOCKED"}, "asil": "D"}],
        "conflicts": [],
        "z3_reviewed": True,
        "test_results": [{"test_id": "T1", "passed": True}],
        "failing_results": [],
        "diagnosis_report": {"success": True, "regression_passed": True},
        "risk_assessment": {"score": 85.0, "requires_human_signoff": True, "asil": "D"},
        "risk_reviewed": False,
    }

    # First invoke runs until human_review interrupt
    state_before_resume = graph.invoke(initial_state, config)
    # Graph paused at human_review interrupt
    checkpoint = in_memory_checkpointer.get(config)
    assert checkpoint is not None, "SQLite checkpointer must persist state"

    # Resume graph execution by supplying engineer sign-off
    resumed_state = graph.invoke(Command(resume="Approved by lead safety engineer."), config)
    assert resumed_state.get("human_approved") is True
    assert "Approved" in resumed_state.get("human_feedback", "")
    assert resumed_state.get("completed") is True


def test_full_graph_flow_from_pdf_to_final_result(in_memory_checkpointer):
    """Done criterion: The full flow runs from sample PDF to final result."""
    sample_pdf = DOCUMENTS_DIR / "sample_requirements.pdf"
    assert sample_pdf.exists(), f"Sample requirements PDF not found at {sample_pdf}"

    graph = build_safespec_graph(checkpointer=in_memory_checkpointer)
    thread_id = f"thread-e2e-pdf-{uuid.uuid4().hex[:8]}"
    cycle_id = f"cycle-e2e-graph-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: SafeSpecGraphState = {
        "pdf_path": str(sample_pdf),
        "cycle_id": cycle_id,
        "ecu_version": "v1",
        "target_req_id": "REQ-050",
        "use_interrupt_for_human": False,  # Autonomous mode for non-blocking end-to-end run
        "step_count": 0,
        "max_steps": MAX_GRAPH_STEPS,
    }

    final_state = graph.invoke(initial_state, config)

    # 1. Extractor completed: all 10 requirements extracted
    assert len(final_state.get("requirements", [])) == 10
    req_ids = {r["id"] for r in final_state["requirements"]}
    assert "REQ-012" in req_ids
    assert "REQ-017" in req_ids
    assert "REQ-023" in req_ids
    assert "REQ-031" in req_ids
    assert "REQ-050" in req_ids

    # 2. Formalizer completed: unformalizable flagged
    assert len(final_state.get("formalized", [])) == 10
    unformalizable = final_state.get("unformalizable", [])
    assert len(unformalizable) == 1
    assert unformalizable[0]["req_id"] == "REQ-023"

    # 3. Z3 completed: conflict detected between REQ-017 and REQ-031
    conflicts = final_state.get("conflicts", [])
    assert len(conflicts) >= 1
    conflict_pairs = {(c["rule_a_id"], c["rule_b_id"]) for c in conflicts}
    assert ("REQ-017", "REQ-031") in conflict_pairs or ("REQ-031", "REQ-017") in conflict_pairs

    # 4. Human review completed (Z3 conflict reviewed)
    assert final_state.get("human_approved") is True

    # 5. Tester completed: tests executed on VirtualECU v1
    test_results = final_state.get("test_results", [])
    assert len(test_results) >= 6
    assert all(r["passed"] for r in test_results)
    assert len(final_state.get("failing_results", [])) == 0

    # 6. Workflow completed without exceeding step limit
    assert final_state.get("completed") is True
    assert final_state.get("step_count") < MAX_GRAPH_STEPS

    # 7. Verify SQLite checkpointer has stored state
    stored_checkpoint = in_memory_checkpointer.get(config)
    assert stored_checkpoint is not None
