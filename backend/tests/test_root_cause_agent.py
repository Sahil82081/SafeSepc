"""Tests for Root Cause Analysis Agent (Rule 4, Rule 7, Rule 8, Rule 9, Rule 10).

Validates:
1. When tests fail, agent calls search_memory for similar past failures.
2. Lists 2-3 possible candidate causes.
3. Chooses experiments with tools: run_single_test, inject_fault, read_ecu_code.
4. Reads experiment results and narrows to one root cause.
5. Calls create_ecu_version to propose a fix without overwriting (Rule 10).
6. Plain code runs: Z3 formal verification, full regression, mutation tests.
7. Risk assessment (no LLM) checks high risk.
8. On success, calls save_memory (failure, cause, fix).
9. Done criterion: v1_buggy_threshold and v1_buggy_timeout both get fixed,
   and a second run finds the failure in memory!
"""

import pytest
import uuid
from pathlib import Path

from backend.app.models.domain import Rule, RuleCondition, RuleAction, TestCase, Result
from backend.app.testing.test_generator import generate_tests
from backend.app.testing.test_runner import TestRunner
from backend.app.ecu.virtual_ecu import VirtualECU
from backend.app.agents.root_cause import RootCauseAnalysisAgent, DiagnosisReport
from backend.app.db.tables import AgentLogTable, MemoryTable
from backend.app.db.session import SessionLocal


@pytest.fixture
def door_rule():
    """Baseline REQ-050 door locking requirement rule."""
    return Rule(
        id="REQ-050",
        text="The central door locking system shall lock all doors when speed exceeds 20.0 km/h.",
        condition=RuleCondition(var="speed", op=">", value=20.0),
        action=RuleAction(var="door", op="=", value="LOCKED"),
        asil="B",
    )


@pytest.fixture
def door_tests(door_rule):
    """Generated test cases for REQ-050."""
    return generate_tests(door_rule)


def test_root_cause_fixes_v1_buggy_threshold(door_rule, door_tests):
    """Verify RootCauseAnalysisAgent diagnoses and fixes v1_buggy_threshold."""
    # 1. Run tests on buggy threshold version to confirm failures
    buggy_ecu = VirtualECU(initial_version="v1_buggy_threshold")
    runner = TestRunner(ecu=buggy_ecu)
    results = runner.run_suite(door_tests)
    failing = [r for r in results if not r.passed]
    assert len(failing) >= 1, "v1_buggy_threshold must fail some tests"

    # 2. Invoke RootCauseAnalysisAgent
    cycle_id = f"cycle-test-rca-thresh-{uuid.uuid4().hex[:8]}"
    agent = RootCauseAnalysisAgent(cycle_id=cycle_id)
    report = agent.diagnose_and_fix(
        ecu_version="v1_buggy_threshold",
        failing_results=failing,
        all_tests=door_tests,
        target_rule=door_rule,
    )

    # 3. Verify agent behavior
    assert isinstance(report, DiagnosisReport)
    assert report.success is True
    assert report.attempts_used <= 3
    assert report.tool_calls_used <= 8
    assert len(report.candidate_causes) in (2, 3)
    assert len(report.experiments_conducted) >= 3
    assert "80.0" in report.root_cause or "threshold" in report.root_cause.lower()

    # 4. Verify immutable version creation (Rule 10)
    assert report.proposed_version is not None
    assert report.proposed_version != "v1_buggy_threshold"

    # 5. Verify plain code validation passed
    assert report.z3_verified is True
    assert report.regression_passed is True

    # 6. Verify fix against live ECU
    fixed_ecu = VirtualECU(initial_version=report.proposed_version)
    fixed_runner = TestRunner(ecu=fixed_ecu)
    fixed_results = fixed_runner.run_suite(door_tests)
    assert all(r.passed for r in fixed_results), "Fixed ECU version must pass 100% of tests"

    # 7. Verify agent_log table contains tool calls and thoughts (Rule 8)
    session = SessionLocal()
    try:
        logs = session.query(AgentLogTable).filter_by(cycle_id=cycle_id).all()
        assert len(logs) >= 5
        tool_names = {l.tool_name for l in logs if l.tool_name}
        assert "search_memory" in tool_names
        assert "read_ecu_code" in tool_names
        assert "run_single_test" in tool_names
        assert "create_ecu_version" in tool_names
        assert "save_memory" in tool_names
    finally:
        session.close()


def test_root_cause_fixes_v1_buggy_timeout(door_rule, door_tests):
    """Verify RootCauseAnalysisAgent diagnoses and fixes v1_buggy_timeout."""
    # 1. Run tests on buggy timeout version to confirm failure on dropped signal
    buggy_ecu = VirtualECU(initial_version="v1_buggy_timeout")
    runner = TestRunner(ecu=buggy_ecu)
    results = runner.run_suite(door_tests)
    failing = [r for r in results if not r.passed]
    assert len(failing) >= 1, "v1_buggy_timeout must fail dropped signal test"

    # 2. Invoke RootCauseAnalysisAgent
    cycle_id = f"cycle-test-rca-timeout-{uuid.uuid4().hex[:8]}"
    agent = RootCauseAnalysisAgent(cycle_id=cycle_id)
    report = agent.diagnose_and_fix(
        ecu_version="v1_buggy_timeout",
        failing_results=failing,
        all_tests=door_tests,
        target_rule=door_rule,
    )

    # 3. Verify agent behavior
    assert report.success is True
    assert report.attempts_used <= 3
    assert report.tool_calls_used <= 8
    assert "timeout" in report.root_cause.lower() or "lost" in report.root_cause.lower()

    # 4. Verify immutable version creation & validation
    assert report.proposed_version is not None
    assert report.z3_verified is True
    assert report.regression_passed is True

    # 5. Verify fix passes on VirtualECU
    fixed_ecu = VirtualECU(initial_version=report.proposed_version)
    fixed_runner = TestRunner(ecu=fixed_ecu)
    fixed_results = fixed_runner.run_suite(door_tests)
    assert all(r.passed for r in fixed_results), "Fixed ECU version must pass 100% of tests"


def test_second_run_finds_failure_in_memory(door_rule, door_tests):
    """Done criterion: A second run on a previously fixed failure finds it in memory."""
    # 1. Execute initial run to diagnose, fix, and save memory for v1_buggy_threshold
    buggy_ecu = VirtualECU(initial_version="v1_buggy_threshold")
    runner = TestRunner(ecu=buggy_ecu)
    failing = [r for r in runner.run_suite(door_tests) if not r.passed]

    cycle_1 = f"cycle-rca-run1-{uuid.uuid4().hex[:8]}"
    agent_1 = RootCauseAnalysisAgent(cycle_id=cycle_1)
    rep_1 = agent_1.diagnose_and_fix(
        ecu_version="v1_buggy_threshold",
        failing_results=failing,
        all_tests=door_tests,
        target_rule=door_rule,
    )
    assert rep_1.success is True

    # 2. Second run on same failure symptom
    cycle_2 = f"cycle-rca-run2-{uuid.uuid4().hex[:8]}"
    agent_2 = RootCauseAnalysisAgent(cycle_id=cycle_2)
    rep_2 = agent_2.diagnose_and_fix(
        ecu_version="v1_buggy_threshold",
        failing_results=failing,
        all_tests=door_tests,
        target_rule=door_rule,
    )

    # 3. Assert second run finds previous failure in memory!
    assert rep_2.past_memory_found is True
    assert rep_2.past_memory_details is not None
    assert "failure:v1_buggy_threshold" in rep_2.past_memory_details.get("key", "")
    assert "threshold" in rep_2.past_memory_details.get("content", "").lower()
