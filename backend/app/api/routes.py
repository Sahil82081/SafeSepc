"""SafeSpec FastAPI REST API Routers (Rule 4, Rule 8, Rule 9, Rule 10).

Provides:
- Runs management: POST /runs/upload, POST /runs/{id}/start, GET /runs, GET /runs/{id}
- Domain inspectability: GET /runs/{id}/requirements, /rules, /conflicts, /tests, /results, /failures, /fixes
- Traceability graph: GET /runs/{id}/traceability
- Safety approvals: GET /approvals/pending, POST /approvals/{id}/approve, POST /approvals/{id}/reject
- Reporting: GET /runs/{id}/report
- Platform analytics: GET /dashboard/stats
- Real-time SSE streaming: GET /runs/{id}/events (streaming thoughts, tools, results from agent_log)
"""

from typing import List, Dict, Any, Optional
import os
import shutil
import uuid
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from langgraph.types import Command
from langgraph.errors import GraphInterrupt

from backend.app.config import DOCUMENTS_DIR, REPORTS_DIR
from backend.app.db.tables import (
    RunTable,
    RequirementTable,
    RuleTable,
    TestTable,
    ResultTable,
    FixTable,
    ApprovalTable,
    AgentLogTable,
    EcuVersionTable,
    MemoryTable,
)
from backend.app.db.session import SessionLocal
from backend.app.schemas import (
    RunUploadResponse,
    RunStartRequest,
    RunResponse,
    ApprovalActionRequest,
    ApprovalItemResponse,
    TraceabilityNode,
    TraceabilityEdge,
    TraceabilityGraphResponse,
    DashboardStatsResponse,
    ReportResponse,
)
from backend.app.workflows.safespec_graph import (
    build_safespec_graph,
    SafeSpecGraphState,
    MAX_GRAPH_STEPS,
)
from backend.app.reports.report_generator import create_verification_report

router = APIRouter()

# In-memory runtime cache for active runs and LangGraph instances
active_runs_data: Dict[str, Dict[str, Any]] = {}
active_graphs: Dict[str, Any] = {}
run_file_registry: Dict[str, Path] = {}


def _get_run_data(run_id: str) -> Dict[str, Any]:
    """Retrieve run data from memory cache or database tables with full state persistence."""
    if run_id in active_runs_data and active_runs_data[run_id].get("requirements"):
        return active_runs_data[run_id]

    session = SessionLocal()
    try:
        run_record = session.query(RunTable).filter_by(run_id=run_id).first()
        if not run_record:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

        # 1. Check if run_state_json is persisted on the run record
        if run_record.run_state_json:
            try:
                cached = json.loads(run_record.run_state_json)
                cached["run_id"] = run_id
                cached["status"] = run_record.status
                cached["pipeline_stage"] = run_record.pipeline_stage
                active_runs_data[run_id] = cached
                return cached
            except Exception:
                pass

        # 2. Return real empty state if workflow has not completed or has no data
        empty_state = {
            "run_id": run_id,
            "status": run_record.status,
            "pipeline_stage": run_record.pipeline_stage,
            "requirements": [],
            "rules": [],
            "approved_rules": [],
            "conflicts": [],
            "test_cases": [],
            "test_results": [],
            "failing_results": [],
            "fixes": [],
            "diagnosis_report": None,
            "risk_assessment": None,
        }
        active_runs_data[run_id] = empty_state
        return empty_state
    finally:
        session.close()


def _execute_graph_background(
    run_id: str,
    pdf_path: Path,
    ecu_version: str = "v1",
    target_req_id: str = "REQ-050",
    use_interrupt: bool = False,
    resume_command: Optional[Any] = None,
) -> None:
    """Execute LangGraph workflow in background thread/task with live stage progression."""
    session = SessionLocal()
    try:
        run_record = session.query(RunTable).filter_by(run_id=run_id).first()
        if run_record:
            run_record.status = "running"
            if resume_command is None:
                run_record.pipeline_stage = "uploaded"
            session.commit()
    finally:
        session.close()

    if not pdf_path.exists():
        session = SessionLocal()
        try:
            r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
            if r_rec:
                r_rec.status = "failed"
                r_rec.pipeline_stage = "error"
                session.commit()
        finally:
            session.close()
        return

    graph = active_graphs.get(run_id) or build_safespec_graph()
    active_graphs[run_id] = graph

    config = {"configurable": {"thread_id": run_id}}
    
    if resume_command is not None:
        stream_input = resume_command
        state_acc = dict(active_runs_data.get(run_id, {}))
    else:
        initial_state: SafeSpecGraphState = {
            "pdf_path": str(pdf_path),
            "cycle_id": run_id,
            "ecu_version": ecu_version,
            "target_req_id": target_req_id,
            "use_interrupt_for_human": use_interrupt,
            "step_count": 0,
            "max_steps": MAX_GRAPH_STEPS,
        }
        stream_input = initial_state
        state_acc = dict(initial_state)

    try:
        stage_map = {
            "extractor": "extract",
            "formalizer": "formalize",
            "human_review": "safety_gate",
            "z3": "z3",
            "tester": "simulate",
            "diagnosis": "diagnosis",
        }

        # Stream node execution so pipeline stage visibly updates in real time
        for output in graph.stream(stream_input, config):
            for node_name, node_state in output.items():
                if node_name == "__interrupt__":
                    print(f"[*] LangGraph paused for Human Safety Gate: {run_id}")
                    state_acc["pipeline_stage"] = "safety_gate"
                    active_runs_data[run_id] = dict(state_acc)
                    session = SessionLocal()
                    try:
                        r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
                        if r_rec:
                            r_rec.status = "paused"
                            r_rec.pipeline_stage = "safety_gate"
                            session.commit()
                    finally:
                        session.close()
                    return

                if isinstance(node_state, dict):
                    state_acc.update(node_state)

                if node_name in stage_map:
                    current_stage = stage_map[node_name]
                    state_acc["pipeline_stage"] = current_stage
                    active_runs_data[run_id] = dict(state_acc)

                    session = SessionLocal()
                    try:
                        r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
                        if r_rec:
                            r_rec.pipeline_stage = current_stage
                            reqs = state_acc.get("requirements", [])
                            if reqs:
                                r_rec.total_requirements = len(reqs)
                            session.commit()
                    finally:
                        session.close()

        final_state = state_acc
        active_runs_data[run_id] = dict(final_state)

        # Update database with run results and full state snapshot
        session = SessionLocal()
        try:
            r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
            if r_rec:
                test_results = final_state.get("test_results", [])
                passed = sum(1 for r in test_results if r.get("passed"))
                failed = len(test_results) - passed

                r_rec.status = "completed"
                r_rec.pipeline_stage = "completed"
                r_rec.total_requirements = len(final_state.get("requirements", []))
                r_rec.flagged_count = len(final_state.get("unformalizable", [])) + len(final_state.get("conflicts", []))
                r_rec.tests_passed = passed
                r_rec.tests_failed = failed
                r_rec.completed_at = datetime.now(timezone.utc)
                r_rec.run_state_json = json.dumps(final_state, default=str)

                # Persist requirements to RequirementTable
                for req in final_state.get("requirements", []):
                    rid = req.get("id")
                    if rid and not session.query(RequirementTable).filter_by(id=rid).first():
                        session.add(RequirementTable(
                            id=rid,
                            text=req.get("text", ""),
                            flags=json.dumps(req.get("flags", [])),
                            terms=json.dumps(req.get("terms", [])),
                            safety=req.get("safety", False),
                            asil=req.get("asil", "QM"),
                            regulation=req.get("regulation"),
                        ))

                # Persist test results to ResultTable
                for res in test_results:
                    session.add(ResultTable(
                        run_id=run_id,
                        test_id=res.get("test_id", "T-unknown"),
                        passed=res.get("passed", False),
                        expected_value=str(res.get("expected_value", "")),
                        actual_value=str(res.get("actual_value", "")),
                        execution_time_ms=float(res.get("execution_time_ms", 0.0) or 0.0),
                        error_message=res.get("error_message"),
                    ))

                session.commit()
        finally:
            session.close()

    except GraphInterrupt as gi:
        print(f"[*] LangGraph GraphInterrupt caught for {run_id}: {gi}")
        session = SessionLocal()
        try:
            r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
            if r_rec:
                r_rec.status = "paused"
                r_rec.pipeline_stage = "safety_gate"
                session.commit()
        finally:
            session.close()

    except Exception as exc:
        print(f"[!] Graph execution error for {run_id}: {exc}")
        session = SessionLocal()
        try:
            r_rec = session.query(RunTable).filter_by(run_id=run_id).first()
            if r_rec:
                r_rec.status = "failed"
                r_rec.pipeline_stage = "error"
                session.commit()
        finally:
            session.close()


# ==============================================================================
# 1. Runs Endpoints
# ==============================================================================

@router.post("/runs/upload", response_model=RunUploadResponse, tags=["runs"])
async def upload_run_pdf(file: UploadFile = File(...)):
    """Upload automotive requirements specification PDF and register a new run."""
    run_id = f"RUN-{uuid.uuid4().hex[:8]}"
    clean_filename = f"{run_id}_{file.filename}"
    target_path = DOCUMENTS_DIR / clean_filename

    # Save uploaded bytes to documents directory
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if target_path.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Only load bundled sample PDF if the user explicitly uploaded sample_requirements.pdf
    sample_pdf = DOCUMENTS_DIR / "sample_requirements.pdf"
    if file.filename == "sample_requirements.pdf" and sample_pdf.exists():
        shutil.copyfile(sample_pdf, target_path)

    run_file_registry[run_id] = target_path

    session = SessionLocal()
    try:
        run_record = RunTable(
            run_id=run_id,
            pipeline_stage="uploaded",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        session.add(run_record)
        session.commit()
    finally:
        session.close()

    active_runs_data[run_id] = {
        "run_id": run_id,
        "pdf_path": str(target_path),
        "status": "pending",
        "pipeline_stage": "uploaded",
        "requirements": [],
        "formalized": [],
        "conflicts": [],
        "test_cases": [],
        "test_results": [],
        "failing_results": [],
    }

    return RunUploadResponse(
        run_id=run_id,
        filename=file.filename or clean_filename,
        filepath=str(target_path),
        status="pending",
        message="PDF specification uploaded successfully.",
    )


@router.post("/runs/demo", tags=["runs"])
async def run_demo_flow(background_tasks: BackgroundTasks):
    """Launch the full SafeSpec demo flow with sample_requirements.pdf in one click."""
    run_id = f"DEMO-{uuid.uuid4().hex[:8]}"
    sample_pdf = DOCUMENTS_DIR / "sample_requirements.pdf"

    session = SessionLocal()
    try:
        new_run = RunTable(
            run_id=run_id,
            pipeline_stage="running",
            status="running",
            total_requirements=0,
            flagged_count=0,
            tests_passed=0,
            tests_failed=0,
        )
        session.add(new_run)
        session.commit()
    finally:
        session.close()

    run_file_registry[run_id] = sample_pdf
    active_runs_data[run_id] = {
        "run_id": run_id,
        "pdf_path": str(sample_pdf),
        "status": "running",
        "pipeline_stage": "running",
        "requirements": [],
        "formalized": [],
        "conflicts": [],
        "test_cases": [],
        "test_results": [],
        "failing_results": [],
    }

    background_tasks.add_task(
        _execute_graph_background,
        run_id=run_id,
        pdf_path=sample_pdf,
        ecu_version="v1",
        target_req_id="REQ-050",
        use_interrupt=False,
    )

    return {
        "run_id": run_id,
        "status": "running",
        "message": "Demo mode launched with sample_requirements.pdf. Verification pipeline running in background.",
    }


@router.post("/runs/{id}/start", tags=["runs"])
async def start_run(
    id: str,
    background_tasks: BackgroundTasks,
    config_req: Optional[RunStartRequest] = None,
):
    """Initiate the SafeSpec LangGraph verification workflow for a run."""
    session = SessionLocal()
    try:
        run_record = session.query(RunTable).filter_by(run_id=id).first()
        if not run_record:
            raise HTTPException(status_code=404, detail=f"Run '{id}' not found.")
    finally:
        session.close()

    pdf_path = run_file_registry.get(id)
    if not pdf_path or not pdf_path.exists():
        matching_files = list(DOCUMENTS_DIR.glob(f"{id}_*"))
        if matching_files and matching_files[0].exists():
            pdf_path = matching_files[0]
            run_file_registry[id] = pdf_path
        elif id.startswith("DEMO-"):
            pdf_path = DOCUMENTS_DIR / "sample_requirements.pdf"
        else:
            raise HTTPException(status_code=404, detail=f"Specification document for run '{id}' not found.")

    cfg = config_req or RunStartRequest()
    background_tasks.add_task(
        _execute_graph_background,
        run_id=id,
        pdf_path=pdf_path,
        ecu_version=cfg.ecu_version,
        target_req_id=cfg.target_req_id,
        use_interrupt=cfg.use_interrupt_for_human,
    )

    return {
        "run_id": id,
        "status": "running",
        "message": "LangGraph verification workflow started in background task.",
    }


@router.get("/runs", response_model=List[RunResponse], tags=["runs"])
async def list_runs():
    """Retrieve all verification runs."""
    session = SessionLocal()
    try:
        records = session.query(RunTable).order_by(RunTable.id.desc()).all()
        return [
            RunResponse(
                id=r.id,
                run_id=r.run_id,
                pipeline_stage=r.pipeline_stage,
                status=r.status,
                total_requirements=r.total_requirements,
                flagged_count=r.flagged_count,
                tests_passed=r.tests_passed,
                tests_failed=r.tests_failed,
                created_at=r.created_at.isoformat() if r.created_at else None,
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
            )
            for r in records
        ]
    finally:
        session.close()


@router.get("/runs/{id}", response_model=RunResponse, tags=["runs"])
async def get_run_details(id: str):
    """Get status and metrics for a specific verification run."""
    session = SessionLocal()
    try:
        r = session.query(RunTable).filter_by(run_id=id).first()
        if not r:
            raise HTTPException(status_code=404, detail=f"Run '{id}' not found.")

        return RunResponse(
            id=r.id,
            run_id=r.run_id,
            pipeline_stage=r.pipeline_stage,
            status=r.status,
            total_requirements=r.total_requirements,
            flagged_count=r.flagged_count,
            tests_passed=r.tests_passed,
            tests_failed=r.tests_failed,
            created_at=r.created_at.isoformat() if r.created_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
    finally:
        session.close()


# ==============================================================================
# 2. Domain Data Inspectability Endpoints
# ==============================================================================

@router.get("/runs/{id}/requirements", tags=["domain"])
async def get_run_requirements(id: str):
    """Get extracted natural language requirements for a run."""
    data = _get_run_data(id)
    return data.get("requirements", [])


@router.get("/runs/{id}/rules", tags=["domain"])
async def get_run_rules(id: str):
    """Get formalized checkable rules (Rule 5 format) for a run."""
    data = _get_run_data(id)
    return data.get("approved_rules", data.get("rules", []))


@router.get("/runs/{id}/conflicts", tags=["domain"])
async def get_run_conflicts(id: str):
    """Get detected formal contradictions and conflicts from Z3 solver."""
    data = _get_run_data(id)
    return data.get("conflicts", [])


@router.get("/runs/{id}/tests", tags=["domain"])
async def get_run_tests(id: str):
    """Get generated test cases (boundary, normal, negative) for a run."""
    data = _get_run_data(id)
    return data.get("test_cases", [])


@router.get("/runs/{id}/results", tags=["domain"])
async def get_run_results(id: str):
    """Get simulation execution results on VirtualECU."""
    data = _get_run_data(id)
    return data.get("test_results", [])


@router.get("/runs/{id}/failures", tags=["domain"])
async def get_run_failures(id: str):
    """Get only failing test cases requiring diagnosis and repair."""
    data = _get_run_data(id)
    results = data.get("test_results", [])
    return [r for r in results if not r.get("passed", False)]


@router.get("/runs/{id}/fixes", tags=["domain"])
async def get_run_fixes(id: str):
    """Get proposed fixes and candidate ECU versions."""
    data = _get_run_data(id)
    diag = data.get("diagnosis_report")
    if diag:
        return [diag]
    return data.get("fixes", [])


# ==============================================================================
# 3. Traceability Graph Endpoint
# ==============================================================================

@router.get("/runs/{id}/traceability", response_model=TraceabilityGraphResponse, tags=["traceability"])
async def get_run_traceability(id: str):
    """Get requirement-to-code traceability DAG with nodes and edges."""
    data = _get_run_data(id)

    nodes: List[TraceabilityNode] = []
    edges: List[TraceabilityEdge] = []

    reqs = data.get("requirements", [])
    rules = data.get("approved_rules", data.get("rules", []))
    conflicts = data.get("conflicts", [])
    tests = data.get("test_cases", [])
    results = data.get("test_results", [])
    diag = data.get("diagnosis_report")

    # Requirement nodes
    for req in reqs:
        rid = req.get("id")
        nodes.append(TraceabilityNode(
            id=rid,
            label=f"Req: {rid}",
            type="requirement",
            status=req.get("ambiguity", "LOW"),
            metadata={"asil": req.get("asil", "QM"), "text": req.get("text")},
        ))

    # Rule nodes and edges from requirements
    for r in rules:
        rule_id = r.get("id")
        rule_node_id = f"RULE-{rule_id}"
        nodes.append(TraceabilityNode(
            id=rule_node_id,
            label=f"Rule: {rule_id}",
            type="rule",
            status="formalized",
            metadata={"condition": r.get("condition"), "action": r.get("action")},
        ))
        if rule_id in [rq.get("id") for rq in reqs]:
            edges.append(TraceabilityEdge(source=rule_id, target=rule_node_id, label="formalizes"))

    # Conflict nodes and edges
    for conf in conflicts:
        cid = conf.get("id", f"CONF-{uuid.uuid4().hex[:4]}")
        ra = conf.get("rule_a_id")
        rb = conf.get("rule_b_id")
        nodes.append(TraceabilityNode(
            id=cid,
            label=f"Conflict: {ra} vs {rb}",
            type="conflict",
            status="CRITICAL",
            metadata={"counter_example": conf.get("counter_example")},
        ))
        if ra:
            edges.append(TraceabilityEdge(source=f"RULE-{ra}", target=cid, label="conflicts_with"))
        if rb:
            edges.append(TraceabilityEdge(source=f"RULE-{rb}", target=cid, label="conflicts_with"))

    # Test nodes and edges from rules
    for t in tests:
        tid = t.get("id")
        parent_req = t.get("req_id")
        nodes.append(TraceabilityNode(
            id=tid,
            label=t.get("name", tid),
            type="test",
            status="generated",
            metadata={"expected": t.get("expected")},
        ))
        if parent_req:
            edges.append(TraceabilityEdge(source=f"RULE-{parent_req}", target=tid, label="verifies"))

    # Result nodes and edges from tests
    for res in results:
        rid = res.get("test_id")
        res_node_id = f"RES-{rid}"
        passed = res.get("passed", False)
        nodes.append(TraceabilityNode(
            id=res_node_id,
            label=f"Outcome: {rid}",
            type="result",
            status="PASS" if passed else "FAIL",
            metadata={"actual": res.get("actual_value")},
        ))
        edges.append(TraceabilityEdge(source=rid, target=res_node_id, label="produces"))

    # Fix node if diagnosis occurred
    if diag and diag.get("proposed_version"):
        fix_id = f"FIX-{diag['proposed_version']}"
        nodes.append(TraceabilityNode(
            id=fix_id,
            label=f"ECU Patch: {diag['proposed_version']}",
            type="fix",
            status="verified" if diag.get("regression_passed") else "pending",
            metadata={"root_cause": diag.get("root_cause")},
        ))
        # Connect failed results to fix
        for res in results:
            if not res.get("passed"):
                edges.append(TraceabilityEdge(source=f"RES-{res.get('test_id')}", target=fix_id, label="triggers_fix"))

    return TraceabilityGraphResponse(
        run_id=id,
        nodes=nodes,
        edges=edges,
    )


# ==============================================================================
# 4. Human Approval Gate Endpoints (Rule 9)
# ==============================================================================

@router.get("/approvals/pending", response_model=List[ApprovalItemResponse], tags=["approvals"])
async def list_pending_approvals():
    """Retrieve all pending human engineering approvals."""
    session = SessionLocal()
    try:
        items = session.query(ApprovalTable).filter_by(status="pending").order_by(ApprovalTable.id.desc()).all()
        return [
            ApprovalItemResponse(
                id=a.id,
                req_id=a.req_id,
                kind=a.kind,
                title=a.title,
                original_text=a.original_text,
                proposed_text=a.proposed_text,
                rule=json.loads(a.rule_json) if a.rule_json else None,
                back_translation=a.back_translation,
                asil_level=a.asil_level,
                status=a.status,
                decision_note=a.decision_note,
                decided_by=a.decided_by,
                decided_at=a.decided_at.isoformat() if a.decided_at else None,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )
            for a in items
        ]
    finally:
        session.close()


@router.post("/approvals/{id}/approve", tags=["approvals"])
async def approve_item(
    id: str,
    background_tasks: BackgroundTasks,
    action: Optional[ApprovalActionRequest] = None,
):
    """Approve a requirement formalization or safety change and resume LangGraph if interrupted."""
    session = SessionLocal()
    try:
        item = session.query(ApprovalTable).filter_by(id=id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Approval record '{id}' not found.")

        act = action or ApprovalActionRequest()
        item.status = "approved"
        item.decision_note = act.note or "Approved by safety engineer sign-off gate."
        item.decided_by = act.decided_by
        item.decided_at = datetime.now(timezone.utc)
        session.commit()
        req_id = item.req_id
    finally:
        session.close()

    # Resume interrupted LangGraph thread if active
    for r_id in list(active_graphs.keys()):
        try:
            resume_cmd = Command(resume=f"Approved {id} for {req_id}")
            pdf_path = run_file_registry.get(r_id, DOCUMENTS_DIR / "sample_requirements.pdf")
            background_tasks.add_task(
                _execute_graph_background,
                run_id=r_id,
                pdf_path=pdf_path,
                resume_command=resume_cmd,
            )
        except Exception as exc:
            print(f"[!] Error scheduling resume for {r_id}: {exc}")

    return {
        "id": id,
        "status": "approved",
        "message": f"Approval {id} confirmed. Resumed pipeline workflow.",
    }


@router.post("/approvals/{id}/reject", tags=["approvals"])
async def reject_item(
    id: str,
    background_tasks: BackgroundTasks,
    action: Optional[ApprovalActionRequest] = None,
):
    """Reject a requirement formalization and prevent downstream execution."""
    session = SessionLocal()
    try:
        item = session.query(ApprovalTable).filter_by(id=id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Approval record '{id}' not found.")

        act = action or ApprovalActionRequest()
        item.status = "rejected"
        item.decision_note = act.note or "Rejected by safety engineer sign-off gate."
        item.decided_by = act.decided_by
        item.decided_at = datetime.now(timezone.utc)
        session.commit()
        req_id = item.req_id
    finally:
        session.close()

    # Resume interrupted LangGraph thread with rejection note
    for r_id in list(active_graphs.keys()):
        try:
            resume_cmd = Command(resume=f"Rejected {id} for {req_id}")
            pdf_path = run_file_registry.get(r_id, DOCUMENTS_DIR / "sample_requirements.pdf")
            background_tasks.add_task(
                _execute_graph_background,
                run_id=r_id,
                pdf_path=pdf_path,
                resume_command=resume_cmd,
            )
        except Exception as exc:
            print(f"[!] Error scheduling resume for {r_id}: {exc}")

    return {
        "id": id,
        "status": "rejected",
        "message": f"Approval {id} rejected. Pipeline blocked from applying rule.",
    }


# ==============================================================================
# 5. Report & Dashboard Endpoints
# ==============================================================================

@router.get("/runs/{id}/report", response_model=ReportResponse, tags=["reports"])
async def get_run_report(id: str):
    """Generate or retrieve Markdown and PDF compliance reports for a run."""
    data = _get_run_data(id)
    report_dict = create_verification_report(data)

    return ReportResponse(
        run_id=id,
        markdown_content=report_dict["markdown_content"],
        markdown_path=report_dict["markdown_path"],
        pdf_path=report_dict.get("pdf_path"),
        generated_at=report_dict["generated_at"],
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse, tags=["dashboard"])
async def get_dashboard_stats(run_id: Optional[str] = Query(None)):
    """Retrieve aggregate or run-scoped KPI statistics for dashboard display."""
    session = SessionLocal()
    try:
        if run_id:
            r = session.query(RunTable).filter_by(run_id=run_id).first()
            if not r:
                return DashboardStatsResponse(
                    total_runs=0,
                    total_requirements=0,
                    flagged_count=0,
                    tests_passed=0,
                    tests_failed=0,
                    pass_rate=0.0,
                    pending_approvals=0,
                    active_ecu_version="v1",
                )

            run_data = _get_run_data(run_id)
            reqs = run_data.get("requirements", [])
            req_count = len(reqs) if reqs else (r.total_requirements or 0)

            test_results = run_data.get("test_results", [])
            if test_results:
                tests_passed = sum(1 for res in test_results if res.get("passed"))
                tests_failed = len(test_results) - tests_passed
            else:
                tests_passed = r.tests_passed or 0
                tests_failed = r.tests_failed or 0

            total_tests = tests_passed + tests_failed
            pass_rate = round((tests_passed / total_tests * 100), 1) if total_tests > 0 else 0.0
            flagged = r.flagged_count or 0

            pending_apps = session.query(ApprovalTable).filter_by(status="pending").count()
            active_ecu = session.query(EcuVersionTable).filter_by(is_active=True).first()
            active_version = active_ecu.version_tag if active_ecu else "v1"

            return DashboardStatsResponse(
                total_runs=1,
                total_requirements=req_count,
                flagged_count=flagged,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                pass_rate=pass_rate,
                pending_approvals=pending_apps,
                active_ecu_version=active_version,
            )

        total_runs = session.query(RunTable).count()
        req_count = session.query(RequirementTable).count()
        if req_count == 0:
            runs = session.query(RunTable).all()
            req_count = sum(r.total_requirements or 0 for r in runs)

        total_tests = session.query(ResultTable).count()
        if total_tests == 0:
            runs = session.query(RunTable).all()
            tests_passed = sum(r.tests_passed or 0 for r in runs)
            tests_failed = sum(r.tests_failed or 0 for r in runs)
            total_tests = tests_passed + tests_failed
        else:
            tests_passed = session.query(ResultTable).filter_by(passed=True).count()
            tests_failed = total_tests - tests_passed

        runs = session.query(RunTable).all()
        flagged_count = sum(r.flagged_count or 0 for r in runs)

        pass_rate = round((tests_passed / total_tests * 100), 1) if total_tests > 0 else 0.0
        pending_apps = session.query(ApprovalTable).filter_by(status="pending").count()

        active_ecu = session.query(EcuVersionTable).filter_by(is_active=True).first()
        active_version = active_ecu.version_tag if active_ecu else "v1"

        return DashboardStatsResponse(
            total_runs=total_runs,
            total_requirements=req_count,
            flagged_count=flagged_count,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            pass_rate=pass_rate,
            pending_approvals=pending_apps,
            active_ecu_version=active_version,
        )
    finally:
        session.close()


@router.post("/runs/reset", tags=["runs"])
@router.delete("/runs", tags=["runs"])
async def reset_workspace():
    """Clear all runs, requirements, test results, approvals, memories, and cache for a completely clean slate."""
    session = SessionLocal()
    try:
        session.query(ResultTable).delete()
        session.query(TestTable).delete()
        session.query(RuleTable).delete()
        session.query(RequirementTable).delete()
        session.query(ApprovalTable).delete()
        session.query(AgentLogTable).delete()
        session.query(FixTable).delete()
        session.query(MemoryTable).delete()
        session.query(RunTable).delete()
        session.commit()
    finally:
        session.close()

    active_runs_data.clear()
    active_graphs.clear()
    run_file_registry.clear()

    # Clean uploaded PDFs except bundled sample
    try:
        if DOCUMENTS_DIR.exists():
            for doc_path in DOCUMENTS_DIR.glob("*"):
                if doc_path.is_file() and doc_path.name != "sample_requirements.pdf":
                    doc_path.unlink(missing_ok=True)
    except Exception as exc:
        print(f"[!] Warning cleaning documents directory on reset: {exc}")

    # Clean generated verification reports (report_*.md and report_*.pdf)
    try:
        if REPORTS_DIR.exists():
            for rep_path in REPORTS_DIR.glob("report_*"):
                if rep_path.is_file() and rep_path.suffix in (".md", ".pdf"):
                    rep_path.unlink(missing_ok=True)
    except Exception as exc:
        print(f"[!] Warning cleaning reports directory on reset: {exc}")

    return {"status": "cleared", "message": "All workspace data reset to clean state."}



# ==============================================================================
# 6. Real-Time SSE Stream of Agent Log (Rule 8)
# ==============================================================================

@router.get("/runs/{id}/events", tags=["events"])
async def stream_run_events(id: str):
    """Real-time SSE event stream broadcasting agent thoughts, tools, and results from agent_log."""
    async def event_generator():
        last_seen_id = 0
        polls_without_events = 0

        while True:
            session = SessionLocal()
            try:
                # Query newer log rows for this cycle/run
                logs = (
                    session.query(AgentLogTable)
                    .filter(AgentLogTable.cycle_id == id, AgentLogTable.id > last_seen_id)
                    .order_by(AgentLogTable.id.asc())
                    .all()
                )

                if logs:
                    polls_without_events = 0
                    for entry in logs:
                        last_seen_id = entry.id
                        payload = {
                            "id": entry.id,
                            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                            "cycle_id": entry.cycle_id,
                            "agent_name": entry.agent_name,
                            "action_type": entry.action_type,  # thought, tool_call, tool_result
                            "action": entry.action_type,
                            "thought": entry.thought,
                            "tool_name": entry.tool_name,
                            "tool_input": json.loads(entry.tool_input) if entry.tool_input else None,
                            "tool_output": json.loads(entry.tool_output) if entry.tool_output else None,
                            "result": entry.result,
                        }
                        yield {
                            "event": "agent_action",
                            "data": json.dumps(payload),
                        }
                else:
                    polls_without_events += 1

                # Check if run has concluded
                run_rec = session.query(RunTable).filter_by(run_id=id).first()
                if run_rec and run_rec.status in ("completed", "failed") and polls_without_events >= 3:
                    yield {
                        "event": "run_completed",
                        "data": json.dumps({"run_id": id, "status": run_rec.status}),
                    }
                    break

            finally:
                session.close()

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/runs/{id}/logs", tags=["events"])
async def get_run_logs(id: str):
    """Retrieve full audit log trail for a run from agent_log table."""
    session = SessionLocal()
    try:
        logs = (
            session.query(AgentLogTable)
            .filter(AgentLogTable.cycle_id == id)
            .order_by(AgentLogTable.id.asc())
            .all()
        )
        return [
            {
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "cycle_id": entry.cycle_id,
                "agent_name": entry.agent_name,
                "action_type": entry.action_type,
                "action": entry.action_type,
                "thought": entry.thought,
                "tool_name": entry.tool_name,
                "tool_input": json.loads(entry.tool_input) if entry.tool_input else None,
                "tool_output": json.loads(entry.tool_output) if entry.tool_output else None,
                "result": entry.result,
            }
            for entry in logs
        ]
    finally:
        session.close()


@router.get("/documents/sample.pdf", tags=["documents"])
async def get_sample_pdf():
    """Download the bundled ISO 26262 sample_requirements.pdf."""
    sample_path = DOCUMENTS_DIR / "sample_requirements.pdf"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample PDF not found.")
    return FileResponse(
        path=str(sample_path),
        filename="sample_requirements.pdf",
        media_type="application/pdf",
    )
