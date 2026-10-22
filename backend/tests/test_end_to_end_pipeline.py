"""End-to-End Verification Pipeline Test Suite (Rule 4, Rule 5, Rule 8, Rule 9, Rule 10).

Validates the full pipeline:
formalizer -> approval -> z3_checker -> test_generator -> test_runner

Done Criterion:
The sample PDF reaches test results and Z3 catches the conflict (REQ-017 vs REQ-031).
"""

import pytest
from pathlib import Path
import uuid

from backend.app.config import DOCUMENTS_DIR
from backend.app.models.domain import Requirement, Rule
from backend.app.agents.extractor import RequirementExtractorAgent
from backend.app.agents.formalizer import RequirementFormalizerAgent
from backend.app.safety.approval import ApprovalManager, ApprovalRecord
from backend.app.formal.z3_checker import find_conflicts, check_invariant
from backend.app.testing.test_generator import generate_tests
from backend.app.testing.test_runner import TestRunner
from backend.app.ecu.virtual_ecu import VirtualECU
from backend.app.workflows.pipeline import VerificationPipeline, run_pipeline
from backend.app.db.tables import AgentLogTable
from backend.app.db.session import SessionLocal


def test_end_to_end_pipeline_with_sample_pdf():
    """Verify end-to-end flow from sample PDF to ECU test results and Z3 conflict detection.

    Steps:
    1. Sample PDF parsed: 10 requirements extracted.
    2. Formalizer converts each Requirement into Rule with English back-translation.
    3. Unclear requirement (REQ-023 with 'quickly') is marked 'not_formalizable' with reason.
    4. Safety approval gate stores records; only approved rules pass to Z3 and test generator.
    5. Z3 catches the conflict between REQ-017 (speed > 30 -> HIGH) and REQ-031 (speed < 40 -> LOW).
    6. Test generator creates boundary, normal, and negative tests for REQ-050.
    7. Test runner executes tests against VirtualECU v1 and achieves 100% pass rate.
    8. Buggy versions fail appropriate tests.
    """
    sample_pdf_path = DOCUMENTS_DIR / "sample_requirements.pdf"
    assert sample_pdf_path.exists(), f"Sample PDF not found at {sample_pdf_path}"

    cycle_id = f"cycle-e2e-{uuid.uuid4().hex[:8]}"
    pipeline = VerificationPipeline(cycle_id=cycle_id)

    # Run complete pipeline on v1
    res = pipeline.run(
        pdf_path=str(sample_pdf_path),
        approve_all_formalized=True,
        target_test_req_id="REQ-050",
        ecu_version="v1",
    )

    # 1. Verification of Extractor output
    assert len(res.requirements) == 10
    req_ids = {r.id for r in res.requirements}
    assert "REQ-017" in req_ids
    assert "REQ-031" in req_ids
    assert "REQ-023" in req_ids
    assert "REQ-050" in req_ids

    # 2. Verification of Formalizer output
    assert len(res.formalized) == 10
    formalized_map = {f.req_id: f for f in res.formalized}

    # REQ-023 must be marked 'not_formalizable' with reason
    req_023 = formalized_map["REQ-023"]
    assert req_023.status == "not_formalizable"
    assert req_023.is_formalizable is False
    assert req_023.rule is None
    assert req_023.reason is not None
    assert "quickly" in req_023.reason.lower() or "measurable" in req_023.reason.lower() or "latency" in req_023.reason.lower()

    # Formalized rules must have valid Rule 5 format and back-translations
    req_050 = formalized_map["REQ-050"]
    assert req_050.status == "formalized"
    assert req_050.rule is not None
    assert req_050.rule.condition.var == "speed"
    assert req_050.rule.condition.value == 20.0
    assert req_050.rule.action.var == "door"
    assert req_050.rule.action.value == "LOCKED"
    assert req_050.back_translation is not None
    assert "20.0 km/h" in req_050.back_translation

    # 3. Verification of Approval Gate
    assert len(res.approval_records) == 10
    # Exactly 9 rules should be approved (10 total - 1 unformalizable)
    assert len(res.approved_rules) == 9
    approved_ids = {r.id for r in res.approved_rules}
    assert "REQ-023" not in approved_ids
    assert "REQ-017" in approved_ids
    assert "REQ-031" in approved_ids
    assert "REQ-050" in approved_ids

    # 4. Z3 Formal Verification catches the conflict between REQ-017 and REQ-031
    assert res.has_conflicts is True
    conflict_pairs = {(c.rule_a_id, c.rule_b_id) for c in res.conflicts}
    assert ("REQ-017", "REQ-031") in conflict_pairs or ("REQ-031", "REQ-017") in conflict_pairs

    matched_conflict = next(
        c for c in res.conflicts
        if (c.rule_a_id == "REQ-017" and c.rule_b_id == "REQ-031") or
           (c.rule_a_id == "REQ-031" and c.rule_b_id == "REQ-017")
    )
    assert "beam" in matched_conflict.description
    assert matched_conflict.counter_example is not None
    assert "speed" in matched_conflict.counter_example
    overlap_speed = float(matched_conflict.counter_example["speed"])
    assert 30.0 < overlap_speed < 40.0, f"Counter-example speed {overlap_speed} must be between 30 and 40"

    # 5. Deterministic Test Case Generation for REQ-050
    assert len(res.test_cases) >= 6
    test_types = {t.name for t in res.test_cases}
    assert any("Boundary" in name for name in test_types)
    assert any("Cruising" in name or "Normal" in name for name in test_types)
    assert any("Dropped" in name or "Negative" in name for name in test_types)

    # 6. Test Execution on VirtualECU v1
    assert len(res.test_results) == len(res.test_cases)
    assert res.all_tests_passed is True
    assert res.pass_count == len(res.test_cases)
    assert res.fail_count == 0

    # 7. Verification of audit trail in SQLite agent_log (Rule 8)
    session = SessionLocal()
    try:
        logs = session.query(AgentLogTable).filter_by(cycle_id=cycle_id).all()
        assert len(logs) >= 4, f"Expected audit logs for cycle {cycle_id}, found {len(logs)}"
        agent_names = {l.agent_name for l in logs}
        assert "extractor_agent" in agent_names or "orchestrator" in agent_names
        assert "formalizer_agent" in agent_names or "z3_checker" in agent_names
    finally:
        session.close()


def test_safety_gate_blocks_unapproved_rules():
    """Verify that unapproved rules NEVER reach Z3 or the test generator."""
    approval_mgr = ApprovalManager(auto_persist=False)

    # Create one rule approved, one unapproved/pending
    rule_approved = Rule(
        id="REQ-050",
        text="Speed > 20 -> door locked",
        condition={"var": "speed", "op": ">", "value": 20.0},
        action={"var": "door", "op": "=", "value": "LOCKED"},
    )
    rule_pending = Rule(
        id="REQ-017",
        text="Speed > 30 -> beam high",
        condition={"var": "speed", "op": ">", "value": 30.0},
        action={"var": "beam", "op": "=", "value": "HIGH"},
    )

    rec1 = approval_mgr.create_record(
        req_id=rule_approved.id,
        original_text=rule_approved.text,
        rule=rule_approved,
        status="pending",
    )
    rec2 = approval_mgr.create_record(
        req_id=rule_pending.id,
        original_text=rule_pending.text,
        rule=rule_pending,
        status="pending",
    )

    # Approve only rec1
    approval_mgr.approve(rec1.id, note="Sign-off REQ-050 only")

    # Gate check
    passed_rules = approval_mgr.get_approved_rules()
    assert len(passed_rules) == 1
    assert passed_rules[0].id == "REQ-050"
    assert "REQ-017" not in [r.id for r in passed_rules]

    # Z3 run with ONLY approved rules cannot see REQ-017
    conflicts = find_conflicts(passed_rules)
    assert len(conflicts) == 0


def test_ecu_buggy_versions_fail_pipeline_tests():
    """Verify that buggy ECU versions fail simulation tests generated from approved rules."""
    sample_pdf_path = DOCUMENTS_DIR / "sample_requirements.pdf"

    # Run pipeline with buggy threshold version (threshold 80 instead of 20)
    res_thresh = run_pipeline(
        pdf_path=str(sample_pdf_path),
        target_test_req_id="REQ-050",
        ecu_version="v1_buggy_threshold",
    )
    assert res_thresh.all_tests_passed is False
    assert res_thresh.fail_count >= 1

    # Run pipeline with buggy timeout version (ignores lost speed frame)
    res_timeout = run_pipeline(
        pdf_path=str(sample_pdf_path),
        target_test_req_id="REQ-050",
        ecu_version="v1_buggy_timeout",
    )
    assert res_timeout.all_tests_passed is False
    assert res_timeout.fail_count >= 1
