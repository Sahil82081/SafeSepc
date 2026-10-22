"""FastAPI REST API & Endpoint Test Suite (Rule 4, Rule 8, Rule 9).

Validates:
1. /openapi.json returns valid schema.
2. CORS headers enabled for http://localhost:5173.
3. POST /runs/upload (PDF upload).
4. POST /runs/{id}/start (LangGraph workflow initiation).
5. GET /runs, GET /runs/{id}.
6. Domain inspection: /requirements, /rules, /conflicts, /tests, /results, /failures, /fixes.
7. GET /runs/{id}/traceability (DAG nodes + edges JSON).
8. Human review: GET /approvals/pending, POST /approvals/{id}/approve, POST /approvals/{id}/reject.
9. GET /runs/{id}/report (Markdown and PDF).
10. GET /dashboard/stats.
11. GET /runs/{id}/events (SSE real-time stream).
"""

import pytest
import io
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import DOCUMENTS_DIR
from backend.app.db.tables import ApprovalTable, AgentLogTable, RunTable
from backend.app.db.session import SessionLocal
from backend.app.api.routes import active_runs_data
from backend.evaluation.run_eval import evaluate_all_10_defects


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_openapi_json(client):
    """Verify /openapi.json is served and defines valid API schema."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "SafeSpec API"
    assert "/runs/upload" in schema["paths"]
    assert "/runs/{id}/start" in schema["paths"]
    assert "/approvals/pending" in schema["paths"]
    assert "/dashboard/stats" in schema["paths"]


def test_root_head_and_get(client):
    """Verify HEAD and GET requests for / return 200 OK."""
    # Test HEAD request for "/"
    head_resp = client.head("/")
    assert head_resp.status_code == 200
    assert "content-type" in head_resp.headers
    # Body in HEAD request must be empty
    assert head_resp.text == ""

    # Test GET request for "/"
    get_resp = client.get("/")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "online"
    assert get_resp.json()["service"] == "SafeSpec API"


def test_cors_headers(client):
    """Verify CORS is configured to permit http://localhost:5173."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    resp = client.options("/runs/upload", headers=headers)
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") in ("http://localhost:5173", "*")


def test_runs_upload_and_start_pipeline(client):
    """Verify PDF upload, run registration, and workflow start."""
    sample_pdf_path = DOCUMENTS_DIR / "sample_requirements.pdf"
    assert sample_pdf_path.exists()

    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. POST /runs/upload
    upload_resp = client.post(
        "/runs/upload",
        files={"file": ("sample_spec.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    assert "run_id" in data
    assert data["filename"] == "sample_spec.pdf"
    assert data["status"] == "pending"

    run_id = data["run_id"]

    # 2. GET /runs/{id} before start
    get_run = client.get(f"/runs/{run_id}")
    assert get_run.status_code == 200
    assert get_run.json()["run_id"] == run_id

    # 3. POST /runs/{id}/start
    start_resp = client.post(
        f"/runs/{run_id}/start",
        json={"ecu_version": "v1", "target_req_id": "REQ-050", "use_interrupt_for_human": False},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "running"


def test_domain_inspection_endpoints(client):
    """Verify /requirements, /rules, /conflicts, /tests, /results, /failures, /fixes."""
    test_run_id = "RUN-TEST-INSPECT"

    # Seed mock run data into memory cache
    active_runs_data[test_run_id] = {
        "run_id": test_run_id,
        "status": "completed",
        "pipeline_stage": "completed",
        "requirements": [
            {"id": "REQ-050", "text": "Lock doors > 20 km/h", "ambiguity": "LOW", "asil": "B"},
            {"id": "REQ-017", "text": "High beam > 30 km/h", "ambiguity": "LOW", "asil": "QM"},
        ],
        "approved_rules": [
            {"id": "REQ-050", "text": "Lock", "condition": {"var": "speed", "op": ">", "value": 20.0}, "action": {"var": "door", "op": "=", "value": "LOCKED"}},
        ],
        "conflicts": [
            {"id": "CONF-01", "rule_a_id": "REQ-017", "rule_b_id": "REQ-031", "description": "Contradiction", "counter_example": {"speed": 35.0}},
        ],
        "test_cases": [
            {"id": "TC-01", "req_id": "REQ-050", "name": "Boundary 20.1", "expected": "LOCKED"},
        ],
        "test_results": [
            {"test_id": "TC-01", "requirement_id": "REQ-050", "passed": True, "expected_value": "LOCKED", "actual_value": "LOCKED"},
            {"test_id": "TC-FAIL", "requirement_id": "REQ-050", "passed": False, "expected_value": "LOCKED", "actual_value": "UNLOCKED"},
        ],
        "diagnosis_report": {
            "initial_version": "v1_buggy_threshold",
            "root_cause": "Threshold 80 instead of 20",
            "proposed_version": "v2",
            "regression_passed": True,
        },
    }

    # Test GET /runs/{id}/requirements
    r_reqs = client.get(f"/runs/{test_run_id}/requirements")
    assert r_reqs.status_code == 200
    assert len(r_reqs.json()) == 2

    # Test GET /runs/{id}/rules
    r_rules = client.get(f"/runs/{test_run_id}/rules")
    assert r_rules.status_code == 200
    assert len(r_rules.json()) == 1

    # Test GET /runs/{id}/conflicts
    r_conf = client.get(f"/runs/{test_run_id}/conflicts")
    assert r_conf.status_code == 200
    assert len(r_conf.json()) == 1
    assert r_conf.json()[0]["id"] == "CONF-01"

    # Test GET /runs/{id}/tests
    r_tests = client.get(f"/runs/{test_run_id}/tests")
    assert r_tests.status_code == 200
    assert len(r_tests.json()) == 1

    # Test GET /runs/{id}/results
    r_res = client.get(f"/runs/{test_run_id}/results")
    assert r_res.status_code == 200
    assert len(r_res.json()) == 2

    # Test GET /runs/{id}/failures
    r_fail = client.get(f"/runs/{test_run_id}/failures")
    assert r_fail.status_code == 200
    assert len(r_fail.json()) == 1
    assert r_fail.json()[0]["test_id"] == "TC-FAIL"

    # Test GET /runs/{id}/fixes
    r_fixes = client.get(f"/runs/{test_run_id}/fixes")
    assert r_fixes.status_code == 200
    assert len(r_fixes.json()) == 1
    assert r_fixes.json()[0]["proposed_version"] == "v2"


def test_traceability_graph_endpoint(client):
    """Verify GET /runs/{id}/traceability returns complete node and edge DAG."""
    test_run_id = "RUN-TEST-TRACE"
    active_runs_data[test_run_id] = {
        "run_id": test_run_id,
        "requirements": [{"id": "REQ-050", "text": "lock doors", "ambiguity": "LOW", "asil": "B"}],
        "approved_rules": [{"id": "REQ-050", "condition": {}, "action": {}}],
        "conflicts": [],
        "test_cases": [{"id": "TC-01", "req_id": "REQ-050", "name": "speed 20.1", "expected": "LOCKED"}],
        "test_results": [{"test_id": "TC-01", "passed": True, "actual_value": "LOCKED"}],
        "diagnosis_report": None,
    }

    resp = client.get(f"/runs/{test_run_id}/traceability")
    assert resp.status_code == 200
    dag = resp.json()

    assert dag["run_id"] == test_run_id
    assert "nodes" in dag
    assert "edges" in dag

    node_types = {n["type"] for n in dag["nodes"]}
    assert "requirement" in node_types
    assert "rule" in node_types
    assert "test" in node_types
    assert "result" in node_types

    edge_labels = {e["label"] for e in dag["edges"]}
    assert "formalizes" in edge_labels
    assert "verifies" in edge_labels
    assert "produces" in edge_labels


def test_approvals_workflow_endpoints(client):
    """Verify GET /approvals/pending, POST /approvals/{id}/approve and /reject."""
    app_id = f"APP-TEST-{uuid.uuid4().hex[:6]}"
    session = SessionLocal()
    try:
        app_row = ApprovalTable(
            id=app_id,
            req_id="REQ-050",
            kind="Formalized Rule",
            title="Approve REQ-050",
            proposed_text="If speed > 20 km/h, central door lock shall be LOCKED.",
            critic_notes="Grounding verified",
            asil_level="B",
            status="pending",
        )
        session.add(app_row)
        session.commit()
    finally:
        session.close()

    # 1. GET /approvals/pending
    pending_resp = client.get("/approvals/pending")
    assert pending_resp.status_code == 200
    pending_ids = [p["id"] for p in pending_resp.json()]
    assert app_id in pending_ids

    # 2. POST /approvals/{id}/approve
    approve_resp = client.post(
        f"/approvals/{app_id}/approve",
        json={"note": "Signed off by safety engineer.", "decided_by": "lead_safety_engineer"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # 3. Create second approval and reject
    reject_id = f"APP-REJ-{uuid.uuid4().hex[:6]}"
    session = SessionLocal()
    try:
        rej_row = ApprovalTable(
            id=reject_id,
            req_id="REQ-HAZARD",
            kind="Formalized Rule",
            title="Approve Unsafe Rule",
            proposed_text="Do not lock doors",
            critic_notes="Unsafe",
            asil_level="D",
            status="pending",
        )
        session.add(rej_row)
        session.commit()
    finally:
        session.close()

    reject_resp = client.post(
        f"/approvals/{reject_id}/reject",
        json={"note": "Rejected due to safety violation.", "decided_by": "lead_safety_engineer"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


def test_report_generation_endpoint(client):
    """Verify GET /runs/{id}/report returns valid Markdown and PDF."""
    test_run_id = "RUN-REPORT-TEST"
    active_runs_data[test_run_id] = {
        "run_id": test_run_id,
        "requirements": [{"id": "REQ-050", "text": "lock doors", "ambiguity": "LOW"}],
        "formalized": [{"req_id": "REQ-050", "status": "formalized"}],
        "conflicts": [],
        "test_results": [{"test_id": "TC-01", "passed": True, "expected_value": "LOCKED", "actual_value": "LOCKED"}],
        "risk_assessment": {"score": 25.0, "level": "LOW", "asil": "B"},
    }

    resp = client.get(f"/runs/{test_run_id}/report")
    assert resp.status_code == 200
    data = resp.json()

    assert data["run_id"] == test_run_id
    assert "# SafeSpec Formal Verification & Safety Report" in data["markdown_content"]
    assert Path(data["markdown_path"]).exists()
    if data.get("pdf_path"):
        assert Path(data["pdf_path"]).exists()


def test_dashboard_stats_endpoint(client):
    """Verify GET /dashboard/stats returns aggregate metrics."""
    resp = client.get("/dashboard/stats")
    assert resp.status_code == 200
    stats = resp.json()

    assert "total_runs" in stats
    assert "total_requirements" in stats
    assert "tests_passed" in stats
    assert "pass_rate" in stats
    assert "pending_approvals" in stats
    assert "active_ecu_version" in stats


def test_sse_events_stream(client):
    """Verify GET /runs/{id}/events streams SSE events."""
    stream_run_id = f"RUN-SSE-{uuid.uuid4().hex[:6]}"

    # Add a mock log entry
    session = SessionLocal()
    try:
        log_entry = AgentLogTable(
            cycle_id=stream_run_id,
            agent_name="extractor_agent",
            action_type="thought",
            thought="Inspecting page 1 of requirements document.",
        )
        session.add(log_entry)
        session.commit()
    finally:
        session.close()

    # Query SSE endpoint with stream=True
    with client.stream("GET", f"/runs/{stream_run_id}/events") as response:
        assert response.status_code == 200
        # Read initial chunk
        chunks = []
        for line in response.iter_lines():
            if line:
                chunks.append(line)
            if len(chunks) >= 2:
                break

        assert any("agent_action" in c or "Inspecting" in c for c in chunks)


def test_evaluation_benchmark_all_10_defects():
    """Done criterion: Evaluation benchmark detects all 10 planted defects."""
    results = evaluate_all_10_defects()
    detected_count = sum(1 for r in results if r.detected)

    assert len(results) == 10
    assert detected_count == 10, f"Expected 10 detected defects, found {detected_count}"


def test_reset_workspace(client):
    """Verify POST /runs/reset cleans all database records and cache."""
    session = SessionLocal()
    try:
        session.add(RunTable(run_id="RUN-TO-RESET", pipeline_stage="completed", status="completed"))
        session.commit()
    finally:
        session.close()

    resp = client.post("/runs/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"

    session = SessionLocal()
    try:
        remaining = session.query(RunTable).filter_by(run_id="RUN-TO-RESET").first()
        assert remaining is None
    finally:
        session.close()

