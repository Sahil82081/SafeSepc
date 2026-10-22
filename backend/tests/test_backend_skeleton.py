"""Pytest suite verifying the /backend skeleton, Pydantic models, and SQLite tables.

Verifies:
1. Folder structure under backend/app and root backend directory.
2. config.py attributes (model name, retry limits, paths).
3. Pydantic models in models/: Requirement, Rule, Conflict, TestCase, Result, Fix, RiskReport.
4. SQLAlchemy SQLite tables in db/: runs, requirements, rules, tests, results, fixes, approvals, agent_log, memories.
5. Database table creation and insertion verification.
"""

from pathlib import Path
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.app import config
from backend.app.models import (
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
from backend.app.db import (
    Base,
    RunTable,
    RequirementTable,
    RuleTable,
    TestTable,
    ResultTable,
    FixTable,
    ApprovalTable,
    AgentLogTable,
    MemoryTable,
    init_db,
)


def test_skeleton_folders_exist():
    """Verify all requested directories exist under backend/app and backend root."""
    backend_dir = config.BACKEND_DIR
    app_dir = config.APP_DIR

    required_app_folders = [
        "api",
        "schemas",
        "models",
        "db",
        "formal",
        "simulation",
        "ecu",
        "testing",
        "tools",
        "agents",
        "memory",
        "safety",
        "workflows",
        "reports",
    ]

    for folder in required_app_folders:
        folder_path = app_dir / folder
        assert folder_path.is_dir(), f"Expected app folder '{folder}' does not exist at {folder_path}"
        assert (folder_path / "__init__.py").exists(), f"__init__.py missing in {folder_path}"

    required_backend_folders = ["evaluation", "documents", "tests"]
    for folder in required_backend_folders:
        folder_path = backend_dir / folder
        assert folder_path.is_dir(), f"Expected backend folder '{folder}' does not exist at {folder_path}"

    assert (backend_dir / "requirements.txt").exists(), "requirements.txt missing in backend/"
    assert (backend_dir / ".env.example").exists(), ".env.example missing in backend/"
    assert (backend_dir / "README.md").exists(), "README.md missing in backend/"


def test_config_attributes():
    """Verify config.py contains model name, retry limits, and paths."""
    # Model name
    assert hasattr(config, "GEMINI_MODEL")
    assert isinstance(config.GEMINI_MODEL, str)
    assert len(config.GEMINI_MODEL) > 0

    # Retry limits
    assert config.MAX_FIX_ATTEMPTS == 3
    assert config.MAX_TOOL_CALLS_PER_ATTEMPT == 8

    # Paths
    assert hasattr(config, "BACKEND_DIR") and isinstance(config.BACKEND_DIR, Path)
    assert hasattr(config, "APP_DIR") and isinstance(config.APP_DIR, Path)
    assert hasattr(config, "DOCUMENTS_DIR") and isinstance(config.DOCUMENTS_DIR, Path)
    assert hasattr(config, "EVALUATION_DIR") and isinstance(config.EVALUATION_DIR, Path)
    assert hasattr(config, "REPORTS_DIR") and isinstance(config.REPORTS_DIR, Path)
    assert hasattr(config, "DATABASE_URL") and isinstance(config.DATABASE_URL, str)


def test_pydantic_models():
    """Verify all 7 requested Pydantic models: Requirement, Rule, Conflict, TestCase, Result, Fix, RiskReport."""
    # 1. Requirement
    req = Requirement(
        id="REQ-012",
        text="The headlamp shall switch to low beam when oncoming vehicle is detected within 150 m.",
        flags=["safety_critical"],
        safety=True,
        asil="C",
        regulation="UNECE R48",
    )
    assert req.id == "REQ-012"
    assert req.asil == "C"

    # 2. Rule (Fixed format Rule 5: {id, text, condition:{var,op,value}, action:{var,op,value}})
    rule = Rule(
        id="REQ-012",
        text="The headlamp shall switch to low beam when oncoming vehicle is detected within 150 m.",
        condition={"var": "oncoming", "op": "==", "value": True},
        action={"var": "state", "op": "=", "value": "LOW"},
    )
    canonical = rule.to_canonical_dict()
    assert canonical == {
        "id": "REQ-012",
        "text": "The headlamp shall switch to low beam when oncoming vehicle is detected within 150 m.",
        "condition": {"var": "oncoming", "op": "==", "value": True},
        "action": {"var": "state", "op": "=", "value": "LOW"},
    }

    # 3. Conflict
    conflict = Conflict(
        id="CONF-001",
        rule_a_id="REQ-017",
        rule_b_id="REQ-031",
        description="Threshold contradiction: 30 km/h vs 40 km/h for darkness high beam.",
        overlap_condition={"speed_range": "[30, 40)", "lux": "< 50"},
        severity="HIGH",
    )
    assert conflict.id == "CONF-001"
    assert conflict.status == "open"

    # 4. TestCase
    tc = TestCase(
        id="T-01",
        req_id="REQ-012",
        name="Oncoming vehicle at 60 km/h",
        given={"speed": 60, "lux": 5, "oncoming": True},
        expected="LOW",
    )
    assert tc.id == "T-01"
    assert tc.expected == "LOW"

    # 5. Result
    res = Result(
        test_id="T-01",
        passed=True,
        expected_value="LOW",
        actual_value="LOW",
        execution_time_ms=1.2,
    )
    assert res.passed is True
    assert res.actual_value == "LOW"

    # 6. Fix
    fix = Fix(
        id="FIX-001",
        target_req_id="REQ-017",
        conflict_id="CONF-001",
        proposed_text="The high beam shall activate at or above 40 km/h in darkness.",
        grounding_score=88.0,
        critic_notes="Aligns with REQ-031 and simulator baseline.",
        status="pending",
    )
    assert fix.id == "FIX-001"
    assert fix.status == "pending"

    # 7. RiskReport
    report = RiskReport(
        req_id="REQ-012",
        asil="C",
        hazard_description="Glare dazzles oncoming drivers causing loss of control.",
        safety_goal="SG-01: Prevent dazzling oncoming road users within 150 m.",
    )
    assert report.req_id == "REQ-012"
    assert report.requires_human_signoff is True  # Auto-enforced for ASIL C


def test_sqlite_tables_created_and_functional():
    """Verify all 9 requested SQLite tables are created and functional:

    runs, requirements, rules, tests, results, fixes, approvals, agent_log, memories.
    """
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    required_tables = {
        "runs",
        "requirements",
        "rules",
        "tests",
        "results",
        "fixes",
        "approvals",
        "agent_log",
        "memories",
    }

    missing_tables = required_tables - existing_tables
    assert not missing_tables, f"Missing required SQLite tables: {missing_tables}"

    # Test Session Operations across the tables
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    now = datetime.now(timezone.utc)

    # 1. runs
    run = RunTable(
        run_id="run-001",
        pipeline_stage="ingest",
        status="completed",
        total_requirements=12,
        flagged_count=4,
        tests_passed=10,
        tests_failed=1,
    )
    session.add(run)

    # 2. requirements
    req = RequirementTable(
        id="REQ-012",
        text="Switch to low beam with oncoming vehicle",
        flags='["safety"]',
        terms='["oncoming"]',
        safety=True,
        asil="C",
        regulation="UNECE R48",
    )
    session.add(req)

    # 3. rules
    rule = RuleTable(
        id="REQ-012",
        text="Switch to low beam with oncoming vehicle",
        condition_json='{"var": "oncoming", "op": "==", "value": true}',
        action_json='{"var": "state", "op": "=", "value": "LOW"}',
        asil="C",
    )
    session.add(rule)

    # 4. tests
    test_case = TestTable(
        id="T-01",
        req_id="REQ-012",
        name="Oncoming test",
        given_json='{"speed": 60, "lux": 5, "oncoming": true}',
        expected="LOW",
    )
    session.add(test_case)

    # 5. results
    result = ResultTable(
        run_id="run-001",
        test_id="T-01",
        passed=True,
        expected_value="LOW",
        actual_value="LOW",
        execution_time_ms=0.5,
    )
    session.add(result)

    # 6. fixes
    fix = FixTable(
        id="FIX-001",
        target_req_id="REQ-017",
        proposed_text="Revised rule text",
        grounding_score=90.0,
        asil="QM",
        status="pending",
    )
    session.add(fix)

    # 7. approvals
    approval = ApprovalTable(
        id="A-101",
        req_id="REQ-023",
        kind="Rewrite",
        title="Make REQ-023 measurable",
        proposed_text="Switch within 200 ms",
        grounding_score=92,
        critic_notes="Grounding verified",
        status="pending",
    )
    session.add(approval)

    # 8. agent_log (Rule 8)
    log = AgentLogTable(
        cycle_id="cycle-001",
        agent_name="quality_agent",
        attempt_number=1,
        tool_call_number=1,
        action_type="thought",
        thought="Verifying rule consistency",
    )
    session.add(log)

    # 9. memories
    memory = MemoryTable(
        memory_type="rule_pattern",
        key="high_beam_speed",
        content="Contradiction observed between 30 and 40 km/h thresholds.",
    )
    session.add(memory)

    session.commit()

    # Query and assert each record
    assert session.query(RunTable).filter_by(run_id="run-001").first().status == "completed"
    assert session.query(RequirementTable).filter_by(id="REQ-012").first().asil == "C"
    assert session.query(RuleTable).filter_by(id="REQ-012").first().asil == "C"
    assert session.query(TestTable).filter_by(id="T-01").first().expected == "LOW"
    assert session.query(ResultTable).filter_by(test_id="T-01").first().passed is True
    assert session.query(FixTable).filter_by(id="FIX-001").first().status == "pending"
    assert session.query(ApprovalTable).filter_by(id="A-101").first().kind == "Rewrite"
    assert session.query(AgentLogTable).filter_by(cycle_id="cycle-001").first().agent_name == "quality_agent"
    assert session.query(MemoryTable).filter_by(key="high_beam_speed").first().memory_type == "rule_pattern"

    session.close()


def test_production_sqlite_file_creation(tmp_path):
    """Verify init_db creates the real SQLite database file on disk."""
    db_file = tmp_path / "test_production.db"
    file_engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    init_db(file_engine)

    assert db_file.exists()
    inspector = inspect(file_engine)
    tables = set(inspector.get_table_names())
    assert "runs" in tables
    assert "agent_log" in tables
    assert "requirements" in tables
