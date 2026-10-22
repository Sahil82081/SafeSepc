"""Pytest suite for Tools and Gemini Registry (backend/app/tools).

Validates:
1. Registry lists all 14 requested tools and generates valid Gemini function declarations.
2. Every tool has a dedicated test validating typed input/output and error-handling behavior.
3. execute_tool logs each tool call and result to the agent_log SQLite table (Rule 8).
"""

from pathlib import Path
import pytest
import pymupdf

from backend.app.config import DOCUMENTS_DIR
from backend.app.db.session import SessionLocal
from backend.app.db.tables import AgentLogTable, ApprovalTable, MemoryTable
from backend.app.tools import (
    TOOL_REGISTRY,
    list_tools,
    get_tool,
    get_gemini_declarations,
    execute_tool,
    read_pdf_page,
    search_pdf,
    ask_human,
    run_z3_conflicts,
    run_z3_invariant,
    generate_tests,
    run_tests,
    run_single_test,
    inject_fault,
    read_ecu_code,
    create_ecu_version,
    run_mutation_tests,
    search_memory,
    save_memory,
)


@pytest.fixture(scope="session")
def sample_pdf_path() -> str:
    """Fixture ensuring a sample PDF exists in documents directory for testing."""
    pdf_file = DOCUMENTS_DIR / "test_iso_spec.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "SafeSpec Automotive Requirements Specification")
    page.insert_text((50, 100), "REQ-012: The headlamp shall switch to low beam within 150 m.")
    page.insert_text((50, 130), "Door safety lock shall engage when vehicle speed exceeds 20 km/h.")
    doc.save(str(pdf_file))
    doc.close()
    return str(pdf_file)


def test_registry_lists_all_tools():
    """Verify registry lists all 14 required tools."""
    all_tools = list_tools()
    expected_tools = {
        "read_pdf_page",
        "search_pdf",
        "ask_human",
        "run_z3_conflicts",
        "run_z3_invariant",
        "generate_tests",
        "run_tests",
        "run_single_test",
        "inject_fault",
        "read_ecu_code",
        "create_ecu_version",
        "run_mutation_tests",
        "search_memory",
        "save_memory",
    }

    assert expected_tools.issubset(set(all_tools)), f"Missing tools: {expected_tools - set(all_tools)}"
    assert len(all_tools) == 14

    for tool_name in expected_tools:
        fn = get_tool(tool_name)
        assert callable(fn), f"Tool '{tool_name}' must be callable."


def test_gemini_function_declarations():
    """Verify Gemini function declarations format."""
    decls = get_gemini_declarations()
    assert len(decls) == 14

    for d in decls:
        assert "name" in d
        assert "description" in d
        assert "parameters" in d
        assert d["parameters"]["type"] == "OBJECT"
        assert "properties" in d["parameters"]


def test_tool_read_pdf_page(sample_pdf_path):
    """Test 1: read_pdf_page tool."""
    res = read_pdf_page(sample_pdf_path, 1)
    assert res["error"] is None
    assert res["page_number"] == 1
    assert "SafeSpec" in res["text"]

    # Negative error handling
    res_err = read_pdf_page("non_existent_file.pdf", 1)
    assert res_err["error"] is not None
    assert res_err["text"] == ""


def test_tool_search_pdf(sample_pdf_path):
    """Test 2: search_pdf tool."""
    res = search_pdf(sample_pdf_path, "headlamp")
    assert res["error"] is None
    assert res["count"] > 0
    assert len(res["matches"]) > 0

    # Negative error handling
    res_err = search_pdf(sample_pdf_path, "")
    assert res_err["error"] is not None


def test_tool_ask_human():
    """Test 3: ask_human tool (Rule 9)."""
    res = ask_human(
        question="Approve change to ASIL C speed sensor threshold?",
        req_id="REQ-012",
        proposal="Change threshold to 25 km/h",
        asil="C",
        kind="Rewrite",
    )
    assert res["error"] is None
    assert res["status"] == "pending"
    assert res["is_high_risk"] is True
    assert res["approval_id"] is not None

    # Check database persistence
    session = SessionLocal()
    saved = session.query(ApprovalTable).filter_by(id=res["approval_id"]).first()
    assert saved is not None
    assert saved.asil_level == "C"
    session.close()


def test_tool_run_z3_conflicts():
    """Test 4: run_z3_conflicts tool."""
    rules = [
        {
            "id": "REQ-017",
            "text": "Activate high beam above 30 km/h in darkness",
            "condition": {"var": "speed", "op": ">", "value": 30},
            "action": {"var": "beam", "op": "=", "value": "HIGH"},
        },
        {
            "id": "REQ-031",
            "text": "Stay in low beam below 40 km/h",
            "condition": {"var": "speed", "op": "<", "value": 40},
            "action": {"var": "beam", "op": "=", "value": "LOW"},
        },
    ]

    res = run_z3_conflicts(rules)
    assert res["error"] is None
    assert res["has_conflict"] is True
    assert res["count"] == 1
    assert "speed" in res["conflicts"][0]["counter_example"]


def test_tool_run_z3_invariant():
    """Test 5: run_z3_invariant tool."""
    rules = [
        {
            "id": "REQ-FLAWED",
            "text": "Unlock door at speed > 10",
            "condition": {"var": "speed", "op": ">", "value": 10},
            "action": {"var": "door", "op": "=", "value": "UNLOCKED"},
        }
    ]

    res = run_z3_invariant(rules, "speed > 20 and door != LOCKED")
    assert res["error"] is None
    assert res["is_reachable"] is True
    assert res["counter_example"]["speed"] > 20


def test_tool_generate_tests():
    """Test 6: generate_tests tool (Rule 4)."""
    rule = {
        "id": "REQ-LOCK-01",
        "text": "Lock door when speed > 20",
        "condition": {"var": "speed", "op": ">", "value": 20.0},
        "action": {"var": "door", "op": "=", "value": "LOCKED"},
    }

    res = generate_tests(rule)
    assert res["error"] is None
    assert res["count"] >= 7
    assert any("boundary" in t["scenario"] for t in res["tests"])


def test_tool_run_tests():
    """Test 7: run_tests tool."""
    rule = {
        "id": "REQ-LOCK-01",
        "text": "Lock door when speed > 20",
        "condition": {"var": "speed", "op": ">", "value": 20.0},
        "action": {"var": "door", "op": "=", "value": "LOCKED"},
    }
    gen_res = generate_tests(rule)
    tests = gen_res["tests"]

    # Run on v1 (All must pass)
    res_v1 = run_tests(tests, ecu_version="v1")
    assert res_v1["error"] is None
    assert res_v1["all_passed"] is True
    assert res_v1["failed_count"] == 0

    # Run on v1_buggy_threshold (Must fail some)
    res_buggy = run_tests(tests, ecu_version="v1_buggy_threshold")
    assert res_buggy["error"] is None
    assert res_buggy["all_passed"] is False
    assert res_buggy["failed_count"] > 0


def test_tool_run_single_test():
    """Test 8: run_single_test tool."""
    single_test = {
        "id": "TC-SAMPLE-01",
        "req_id": "REQ-LOCK-01",
        "name": "Cruising speed test",
        "given": {"speed": 50.0, "is_valid": True, "is_lost": False},
        "expected": "LOCKED",
    }

    res = run_single_test(single_test, ecu_version="v1")
    assert res["error"] is None
    assert res["passed"] is True
    assert res["result"]["actual_value"] == "LOCKED"


def test_tool_inject_fault():
    """Test 9: inject_fault tool."""
    base_inputs = {"speed": 45.0, "is_valid": True, "is_lost": False}

    res_lost = inject_fault(base_inputs, "MESSAGE_LOST")
    assert res_lost["error"] is None
    assert res_lost["mutated_inputs"]["is_lost"] is True

    res_delay = inject_fault(base_inputs, "MESSAGE_DELAYED", {"delay_ms": 250})
    assert res_delay["error"] is None
    assert res_delay["mutated_inputs"]["latency_ms"] == 250

    res_stuck = inject_fault(base_inputs, "SENSOR_STUCK", {"stuck_var": "speed", "stuck_value": 0.0})
    assert res_stuck["error"] is None
    assert res_stuck["mutated_inputs"]["speed"] == 0.0


def test_tool_read_ecu_code():
    """Test 10: read_ecu_code tool."""
    res = read_ecu_code("v1")
    assert res["error"] is None
    assert "class DoorControllerLogic" in res["code"]
    assert res["filename"] == "v1.py"


def test_tool_create_ecu_version(tmp_path):
    """Test 11: create_ecu_version tool (Rule 10)."""
    custom_code = '"""Test ECU Version"""\ndef evaluate(speed, is_lost=False):\n    return "LOCKED"\n'
    res = create_ecu_version(custom_code, description="Unit test new version proposal")

    assert res["error"] is None
    assert res["version_tag"] is not None
    assert res["filename"].endswith(".py")
    assert res["code_hash"] is not None


def test_tool_run_mutation_tests():
    """Test 12: run_mutation_tests tool."""
    res = run_mutation_tests(ecu_version="v1")
    assert res["error"] is None
    assert res["total_mutants"] > 0
    assert res["killed_count"] > 0
    assert res["mutation_score"] >= 70.0


def test_tool_save_and_search_memory():
    """Test 13 & 14: save_memory and search_memory tools."""
    key = "unece_r48_threshold_note"
    content = "Main passing beam must transition to dipped beam within 150m."
    save_res = save_memory(key=key, content=content, memory_type="rule_pattern")

    assert save_res["error"] is None
    assert save_res["saved"] is True
    assert save_res["memory_id"] is not None

    search_res = search_memory("dipped beam")
    assert search_res["error"] is None
    assert search_res["count"] > 0
    assert any(m["key"] == key for m in search_res["memories"])


def test_execute_tool_logs_to_agent_log():
    """Verify execute_tool invokes tool and logs to agent_log SQLite table (Rule 8)."""
    import uuid
    cycle_id = f"cycle-test-registry-log-{uuid.uuid4().hex[:8]}"
    arguments = {
        "rules": [
            {
                "id": "REQ-A",
                "text": "speed > 30 -> HIGH",
                "condition": {"var": "speed", "op": ">", "value": 30},
                "action": {"var": "beam", "op": "=", "value": "HIGH"},
            },
            {
                "id": "REQ-B",
                "text": "speed < 40 -> LOW",
                "condition": {"var": "speed", "op": "<", "value": 40},
                "action": {"var": "beam", "op": "=", "value": "LOW"},
            },
        ]
    }

    out = execute_tool(
        name="run_z3_conflicts",
        arguments=arguments,
        cycle_id=cycle_id,
        agent_name="quality_agent",
        attempt_number=1,
        tool_call_number=1,
    )

    assert out["error"] is None
    assert out["has_conflict"] is True

    # Verify audit persistence in agent_log
    session = SessionLocal()
    logs = session.query(AgentLogTable).filter_by(cycle_id=cycle_id).all()
    assert len(logs) == 2  # One tool_call, one tool_result
    action_types = {l.action_type for l in logs}
    assert "tool_call" in action_types
    assert "tool_result" in action_types

    call_entry = next(l for l in logs if l.action_type == "tool_call")
    assert call_entry.tool_name == "run_z3_conflicts"

    result_entry = next(l for l in logs if l.action_type == "tool_result")
    assert result_entry.result == "SUCCESS"
    session.close()
