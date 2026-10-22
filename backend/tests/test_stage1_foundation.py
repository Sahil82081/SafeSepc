"""Pytest suite for Stage 1: Foundation & Project Core.

Validates:
- Rule 1: Python environment and imports
- Rule 3: Config & Gemini model location
- Rule 5: Fixed Rule Pydantic schema {id, text, condition:{var,op,value}, action:{var,op,value}}
- Rule 7: Agent loop limits (max 3 fix attempts, max 8 tool calls)
- Rule 8: Every agent action (thought, tool, result) saved to agent_log
- Rule 9: High-risk ASIL C/D triggers human stop flag
- Rule 10: Never overwrite ECU files, keep versions and allow rollback
"""

import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import config
from backend.app.models.rule import Rule, RuleCondition, RuleAction
from backend.app.models.db import Base, AgentLog, EcuVersion, ApprovalItem
from backend.app.services.audit_logger import AuditLogger
from backend.app.services.ecu_store import EcuStore, BASELINE_ECU_CODE


@pytest.fixture
def test_db():
    """In-memory SQLite database session fixture."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def temp_ecu_dir(tmp_path):
    """Temporary directory for versioned ECU files."""
    ecu_dir = tmp_path / "ecu_versions"
    ecu_dir.mkdir(parents=True, exist_ok=True)
    return ecu_dir


def test_config_rules():
    """Rule 3 & 7: Model name lives only in config.py, loop limits are defined."""
    assert hasattr(config, "GEMINI_MODEL")
    assert isinstance(config.GEMINI_MODEL, str)
    assert len(config.GEMINI_MODEL) > 0

    # Rule 7 limits
    assert config.MAX_FIX_ATTEMPTS == 3
    assert config.MAX_TOOL_CALLS_PER_ATTEMPT == 8

    # Rule 9 ASIL levels
    assert "C" in config.HIGH_RISK_ASIL_LEVELS
    assert "D" in config.HIGH_RISK_ASIL_LEVELS


def test_rule_pydantic_schema_rule_5():
    """Rule 5: All rules use fixed Pydantic format {id, text, condition:{var,op,value}, action:{var,op,value}}."""
    raw_data = {
        "id": "REQ-012",
        "text": "The headlamp shall switch to low beam when an oncoming vehicle is detected within 150 m.",
        "condition": {
            "var": "oncoming_detected",
            "op": "==",
            "value": True
        },
        "action": {
            "var": "beam_state",
            "op": "=",
            "value": "LOW"
        }
    }

    rule = Rule(**raw_data)
    assert rule.id == "REQ-012"
    assert rule.condition.var == "oncoming_detected"
    assert rule.condition.op == "=="
    assert rule.condition.value is True
    assert rule.action.var == "beam_state"
    assert rule.action.value == "LOW"

    # Verify canonical dict output
    canonical = rule.to_canonical_dict()
    assert canonical == raw_data


def test_rule_condition_evaluation():
    """Test condition evaluation with comparison operators."""
    cond_gt = RuleCondition(var="speed", op=">", value=40)
    assert cond_gt.evaluate({"speed": 45}) is True
    assert cond_gt.evaluate({"speed": 40}) is False
    assert cond_gt.evaluate({"speed": 35}) is False

    cond_lte = RuleCondition(var="lux", op="<=", value=50)
    assert cond_lte.evaluate({"lux": 10}) is True
    assert cond_lte.evaluate({"lux": 50}) is True
    assert cond_lte.evaluate({"lux": 80}) is False

    cond_missing = RuleCondition(var="missing_var", op="==", value=1)
    assert cond_missing.evaluate({"speed": 50}) is False


def test_rule_action_apply():
    """Test applying rule action to a state dictionary."""
    action = RuleAction(var="beam_cmd", op="=", value="HIGH")
    initial_state = {"beam_cmd": "LOW", "vehicle_speed": 60}
    updated_state = action.apply(initial_state)

    assert updated_state["beam_cmd"] == "HIGH"
    assert updated_state["vehicle_speed"] == 60
    # Original should be untouched
    assert initial_state["beam_cmd"] == "LOW"


def test_high_risk_asil_rule_9():
    """Rule 9: ASIL C and D are high risk and must flag for human stop."""
    rule_qm = Rule(
        id="REQ-034",
        text="Turn off headlamp in daylight",
        condition={"var": "lux", "op": ">", "value": 1000},
        action={"var": "state", "op": "=", "value": "OFF"},
        asil="QM"
    )
    assert rule_qm.is_high_risk is False

    rule_asil_c = Rule(
        id="REQ-012",
        text="Switch to low beam with oncoming vehicle",
        condition={"var": "oncoming", "op": "==", "value": True},
        action={"var": "state", "op": "=", "value": "LOW"},
        asil="C"
    )
    assert rule_asil_c.is_high_risk is True

    rule_asil_d = Rule(
        id="REQ-099",
        text="Emergency brake beam safety cutoff",
        condition={"var": "fault", "op": "==", "value": True},
        action={"var": "state", "op": "=", "value": "FALLBACK"},
        asil="D"
    )
    assert rule_asil_d.is_high_risk is True


def test_audit_logger_rule_8(test_db):
    """Rule 8: Every agent action (thought, tool, result) is saved to the agent_log table."""
    logger = AuditLogger(db_session=test_db)
    cycle = "cycle-test-001"

    # 1. Thought
    t_log = logger.log_thought(
        cycle_id=cycle,
        agent_name="quality_agent",
        thought="Checking REQ-017 and REQ-031 for speed threshold contradiction.",
        attempt_number=1,
    )
    assert t_log.id is not None
    assert t_log.action_type == "thought"

    # 2. Tool call
    c_log = logger.log_tool_call(
        cycle_id=cycle,
        agent_name="quality_agent",
        tool_name="z3_check_conflict",
        tool_input={"rule_a": "REQ-017", "rule_b": "REQ-031"},
        attempt_number=1,
        tool_call_number=1,
    )
    assert c_log.action_type == "tool_call"
    assert "z3_check_conflict" in c_log.tool_name

    # 3. Tool result
    r_log = logger.log_tool_result(
        cycle_id=cycle,
        agent_name="quality_agent",
        tool_name="z3_check_conflict",
        tool_output={"conflict_found": True, "condition_overlap": "speed in [30, 40]"},
        result_summary="Detected contradiction on high beam threshold",
        attempt_number=1,
        tool_call_number=1,
    )
    assert r_log.action_type == "tool_result"

    # 4. Human gate log (Rule 9)
    g_log = logger.log_gate(
        cycle_id=cycle,
        agent_name="safety_gate",
        gate_reason="ASIL C requirement modification requires human approval.",
        attempt_number=1,
    )
    assert g_log.action_type == "gate"

    # Verify query
    all_logs = logger.get_cycle_logs(cycle)
    assert len(all_logs) == 4
    assert [l.action_type for l in all_logs] == ["thought", "tool_call", "tool_result", "gate"]


def test_ecu_store_never_overwrites_rule_10(temp_ecu_dir, test_db):
    """Rule 10: Never overwrite an ECU file. Keep versions and allow rollback."""
    store = EcuStore(storage_dir=temp_ecu_dir, db_session=test_db)

    # 1. Baseline initialization creates v1
    v1 = store.initialize_baseline()
    assert v1.version_tag == "v1"
    assert v1.is_active is True
    file_v1 = temp_ecu_dir / "ecu_v1.py"
    assert file_v1.exists()
    v1_content = file_v1.read_text(encoding="utf-8")
    assert "class HeadlampECU" in v1_content
    v1_hash = v1.code_hash

    # 2. Add modified ECU version v2 (e.g. proposed fix by agent)
    v2_code = v1_content.replace(
        "self.hi_speed_threshold = hi_speed_threshold",
        "self.hi_speed_threshold = 30.0  # Modified by fix_agent to resolve conflict with REQ-017"
    )
    v2 = store.save_new_version(
        code_content=v2_code,
        description="Fix high-beam threshold to 30 km/h per REQ-017",
        author="fix_agent",
        set_active=True,
    )
    assert v2.version_tag == "v2"
    assert v2.is_active is True

    file_v2 = temp_ecu_dir / "ecu_v2.py"
    assert file_v2.exists()
    assert file_v2.read_text(encoding="utf-8") == v2_code

    # Crucial Rule 10 assertion: ecu_v1.py MUST NOT be overwritten or touched
    assert file_v1.read_text(encoding="utf-8") == v1_content
    assert store._calculate_hash(file_v1.read_text(encoding="utf-8")) == v1_hash

    # 3. Check diff between v1 and v2
    diff = store.get_diff("v1", "v2")
    assert "+        self.hi_speed_threshold = 30.0" in diff

    # 4. Rollback to v1 (Rule 10)
    rolled_back = store.rollback("v1")
    assert rolled_back.version_tag == "v1"
    assert rolled_back.is_active is True

    # Check active version
    active = store.get_active_version()
    assert active.version_tag == "v1"

    # Both version files remain intact
    assert file_v1.exists()
    assert file_v2.exists()
    assert len(store.list_versions()) == 2
