"""Agent-Callable Tool Functions (Rule 6).

All tools are plain Python functions with clear names, detailed docstrings,
and typed inputs/outputs.
Crucial Rule 6 principle: Tools never crash; they catch exceptions and return an error field.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import uuid
from datetime import datetime, timezone

from backend.app.config import DOCUMENTS_DIR
from backend.app.parsers.pdf_parser import (
    read_pdf_page as parser_read_pdf_page,
    search_pdf as parser_search_pdf,
)
from backend.app.models.domain import Rule, TestCase, Conflict
from backend.app.formal.z3_checker import (
    find_conflicts as z3_find_conflicts,
    check_invariant as z3_check_invariant,
)
from backend.app.testing.test_generator import generate_tests as gen_tests
from backend.app.testing.test_runner import TestRunner
from backend.app.testing.fault_injection import FaultInjector
from backend.app.testing.mutation import run_mutation_analysis
from backend.app.ecu.virtual_ecu import VirtualECU
from backend.app.services.ecu_store import EcuStore
from backend.app.db.session import SessionLocal
from backend.app.db.tables import ApprovalTable, MemoryTable


def read_pdf_page(pdf_path: str, page_number: int) -> Dict[str, Any]:
    """Read and extract text from a specific 1-indexed page of a PDF document.

    Args:
        pdf_path: Relative or absolute path to the PDF file.
        page_number: 1-indexed page number to read.

    Returns:
        Dict with text, page_number, total_pages, and error (None if successful).
    """
    try:
        target = Path(pdf_path)
        if not target.is_absolute():
            target = DOCUMENTS_DIR / pdf_path
        return parser_read_pdf_page(str(target), int(page_number))
    except Exception as exc:
        return {
            "text": "",
            "page_number": page_number,
            "total_pages": 0,
            "error": f"read_pdf_page failed: {str(exc)}",
        }


def search_pdf(pdf_path: str, query: str) -> Dict[str, Any]:
    """Search for keywords or phrases across all pages of a PDF document.

    Args:
        pdf_path: Relative or absolute path to the PDF file.
        query: Search string or keyword.

    Returns:
        Dict with matches (page, occurrences, snippet), count, and error.
    """
    try:
        target = Path(pdf_path)
        if not target.is_absolute():
            target = DOCUMENTS_DIR / pdf_path
        return parser_search_pdf(str(target), str(query))
    except Exception as exc:
        return {
            "matches": [],
            "count": 0,
            "error": f"search_pdf failed: {str(exc)}",
        }


def ask_human(
    question: str,
    req_id: Optional[str] = None,
    proposal: Optional[str] = None,
    asil: Optional[str] = "QM",
    kind: Optional[str] = "Review",
    critic_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Queue an item or question for human engineer review and approval (Rule 9).

    High-risk changes (ASIL C/D) stop and wait for human engineering sign-off.

    Args:
        question: Question or explanation of the decision requiring human sign-off.
        req_id: Linked requirement ID if applicable.
        proposal: Proposed text or action for engineering review.
        asil: Automotive Safety Integrity Level (QM, A, B, C, D).
        kind: Proposal category ('Rewrite', 'Conflict', 'Safety hint', 'New test').
        critic_notes: Justification or grounding context.

    Returns:
        Dict with approval_id, status, asil, message, and error.
    """
    try:
        session = SessionLocal()
        approval_id = f"A-{uuid.uuid4().hex[:6].upper()}"
        item = ApprovalTable(
            id=approval_id,
            req_id=req_id or "GENERAL",
            kind=kind or "Review",
            title=question[:250],
            proposed_text=proposal or question,
            critic_notes=critic_notes or "Submitted by agent for human gate approval.",
            asil_level=asil or "QM",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        session.add(item)
        session.commit()
        session.close()

        return {
            "approval_id": approval_id,
            "status": "pending",
            "asil": asil,
            "is_high_risk": asil in ("C", "D"),
            "message": f"Queued for human sign-off with ID {approval_id}.",
            "error": None,
        }
    except Exception as exc:
        return {
            "approval_id": None,
            "status": "failed",
            "asil": asil,
            "is_high_risk": asil in ("C", "D"),
            "message": "",
            "error": f"ask_human failed: {str(exc)}",
        }


def run_z3_conflicts(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute Z3 SMT solver to find conflicting pairs among requirement rules.

    Args:
        rules: List of rules in fixed Pydantic format {id, text, condition, action}.

    Returns:
        Dict with conflicts list (reason, counter_example), count, has_conflict, and error.
    """
    try:
        parsed_rules: List[Rule] = [Rule(**r) for r in rules]
        conflicts = z3_find_conflicts(parsed_rules)
        serialized = [c.model_dump() for c in conflicts]
        return {
            "conflicts": serialized,
            "count": len(serialized),
            "has_conflict": len(serialized) > 0,
            "error": None,
        }
    except Exception as exc:
        return {
            "conflicts": [],
            "count": 0,
            "has_conflict": False,
            "error": f"run_z3_conflicts failed: {str(exc)}",
        }


def run_z3_invariant(rules: List[Dict[str, Any]], bad_state: Any) -> Dict[str, Any]:
    """Execute Z3 SMT solver to check if an unsafe bad state is possible under rules.

    Args:
        rules: List of rules defining system behavior.
        bad_state: Unsafe state predicate (string, condition dict, or condition list).

    Returns:
        Dict with is_reachable, counter_example, reason, and error.
    """
    try:
        parsed_rules: List[Rule] = [Rule(**r) for r in rules]
        conflict = z3_check_invariant(parsed_rules, bad_state)

        if conflict is not None:
            return {
                "is_reachable": True,
                "counter_example": conflict.counter_example,
                "reason": conflict.description,
                "error": None,
            }
        else:
            return {
                "is_reachable": False,
                "counter_example": None,
                "reason": "Bad state is mathematically impossible under the provided rules.",
                "error": None,
            }
    except Exception as exc:
        return {
            "is_reachable": False,
            "counter_example": None,
            "reason": None,
            "error": f"run_z3_invariant failed: {str(exc)}",
        }


def generate_tests(rule: Dict[str, Any], default_safe_state: Optional[str] = None) -> Dict[str, Any]:
    """Deterministically generate boundary, normal, and negative test cases from a rule (Rule 4).

    Args:
        rule: Requirement rule dict {id, text, condition, action}.
        default_safe_state: Optional default state when condition is false.

    Returns:
        Dict with tests list, count, and error.
    """
    try:
        parsed_rule = Rule(**rule)
        test_cases = gen_tests(parsed_rule, default_safe_state=default_safe_state)
        serialized = [t.model_dump() for t in test_cases]
        return {
            "tests": serialized,
            "count": len(serialized),
            "error": None,
        }
    except Exception as exc:
        return {
            "tests": [],
            "count": 0,
            "error": f"generate_tests failed: {str(exc)}",
        }


def run_tests(tests: List[Dict[str, Any]], ecu_version: str = "v1") -> Dict[str, Any]:
    """Run a test suite against a specific ECU version on the simulated ECU.

    Args:
        tests: List of TestCase dicts.
        ecu_version: ECU version to test ('v1', 'v1_buggy_threshold', 'v1_buggy_timeout').

    Returns:
        Dict with results list, passed_count, failed_count, all_passed, and error.
    """
    try:
        parsed_tests = [TestCase(**t) for t in tests]
        ecu = VirtualECU(initial_version=ecu_version)
        runner = TestRunner(ecu=ecu)
        results = runner.run_suite(parsed_tests)

        passed_cnt = sum(1 for r in results if r.passed)
        failed_cnt = len(results) - passed_cnt

        return {
            "results": [r.model_dump() for r in results],
            "passed_count": passed_cnt,
            "failed_count": failed_cnt,
            "all_passed": (failed_cnt == 0),
            "error": None,
        }
    except Exception as exc:
        return {
            "results": [],
            "passed_count": 0,
            "failed_count": 0,
            "all_passed": False,
            "error": f"run_tests failed: {str(exc)}",
        }


def run_single_test(test: Dict[str, Any], ecu_version: str = "v1") -> Dict[str, Any]:
    """Run an individual TestCase against a specific ECU version.

    Args:
        test: TestCase dict.
        ecu_version: ECU version name.

    Returns:
        Dict with result dict, passed bool, and error.
    """
    try:
        parsed_test = TestCase(**test)
        ecu = VirtualECU(initial_version=ecu_version)
        runner = TestRunner(ecu=ecu)
        res = runner.run_test(parsed_test)

        return {
            "result": res.model_dump(),
            "passed": res.passed,
            "error": None,
        }
    except Exception as exc:
        return {
            "result": None,
            "passed": False,
            "error": f"run_single_test failed: {str(exc)}",
        }


def inject_fault(
    inputs: Dict[str, Any],
    fault_type: str,
    fault_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Inject an automotive sensor or CAN bus fault into test inputs.

    Args:
        inputs: Dictionary of nominal test inputs.
        fault_type: Fault model ('MESSAGE_LOST', 'MESSAGE_DELAYED', 'SENSOR_STUCK').
        fault_params: Optional fault parameters (e.g. delay_ms, stuck_value).

    Returns:
        Dict with mutated_inputs, fault_applied, and error.
    """
    try:
        params = fault_params or {}
        ft = fault_type.upper().strip()

        if ft in ("MESSAGE_LOST", "LOST", "DROP"):
            mutated = FaultInjector.inject_lost_message(inputs)
        elif ft in ("MESSAGE_DELAYED", "DELAY", "LATENCY"):
            delay = float(params.get("delay_ms", 300.0))
            mutated = FaultInjector.inject_delayed_message(inputs, delay_ms=delay)
        elif ft in ("SENSOR_STUCK", "STUCK", "FREEZE"):
            stuck_val = params.get("stuck_value", 0.0)
            stuck_var = params.get("stuck_var", "speed")
            mutated = FaultInjector.inject_stuck_sensor(inputs, var=stuck_var, value=stuck_val)
        else:
            return {
                "mutated_inputs": inputs,
                "fault_applied": "NONE",
                "error": f"Unknown fault_type '{fault_type}'. Choose MESSAGE_LOST, MESSAGE_DELAYED, or SENSOR_STUCK.",
            }

        return {
            "mutated_inputs": mutated,
            "fault_applied": ft,
            "error": None,
        }
    except Exception as exc:
        return {
            "mutated_inputs": inputs,
            "fault_applied": "NONE",
            "error": f"inject_fault failed: {str(exc)}",
        }


def read_ecu_code(version_name: str = "v1") -> Dict[str, Any]:
    """Read the source code and metadata of a specific ECU version.

    Args:
        version_name: Version identifier ('v1', 'v1_buggy_threshold', 'v1_buggy_timeout').

    Returns:
        Dict with version_name, code, filename, and error.
    """
    try:
        clean = version_name.replace(".py", "")
        store = EcuStore()
        file_path = store.storage_dir / f"{clean}.py"

        if not file_path.exists():
            return {
                "version_name": clean,
                "code": "",
                "filename": f"{clean}.py",
                "error": f"ECU version '{clean}' not found in {store.storage_dir}.",
            }

        code = file_path.read_text(encoding="utf-8")
        return {
            "version_name": clean,
            "code": code,
            "filename": f"{clean}.py",
            "error": None,
        }
    except Exception as exc:
        return {
            "version_name": version_name,
            "code": "",
            "filename": "",
            "error": f"read_ecu_code failed: {str(exc)}",
        }


def create_ecu_version(
    code_content: str,
    description: str,
    author: str = "agent",
    set_active: bool = False,
) -> Dict[str, Any]:
    """Save a new ECU version without overwriting existing files (Rule 10).

    Args:
        code_content: Python source code for the new ECU controller.
        description: Description of the fix or changes made.
        author: Identifier of author / agent proposing the version.
        set_active: Whether to immediately activate this version.

    Returns:
        Dict with version_tag, filename, code_hash, and error.
    """
    try:
        if not code_content.strip():
            return {
                "version_tag": None,
                "filename": None,
                "code_hash": None,
                "error": "code_content cannot be empty.",
            }

        store = EcuStore()
        new_version = store.save_new_version(
            code_content=code_content,
            description=description,
            author=author,
            set_active=set_active,
        )

        return {
            "version_tag": new_version.version_tag,
            "filename": new_version.filename,
            "code_hash": new_version.code_hash,
            "error": None,
        }
    except Exception as exc:
        return {
            "version_tag": None,
            "filename": None,
            "code_hash": None,
            "error": f"create_ecu_version failed: {str(exc)}",
        }


def run_mutation_tests(
    code_content: Optional[str] = None,
    ecu_version: Optional[str] = "v1",
    tests: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute mutation analysis against an ECU version or code string.

    Args:
        code_content: Optional source code to mutate.
        ecu_version: Optional ECU version to load if code_content not provided.
        tests: List of TestCase dicts to use as the regression test suite.

    Returns:
        Dict with total_mutants, killed_count, survived_count, mutation_score, and error.
    """
    try:
        # Determine source code
        source = code_content
        if not source and ecu_version:
            read_res = read_ecu_code(ecu_version)
            if read_res.get("error"):
                return {
                    "total_mutants": 0,
                    "killed_count": 0,
                    "survived_count": 0,
                    "mutation_score": 0.0,
                    "mutants": [],
                    "error": read_res["error"],
                }
            source = read_res["code"]

        if not source:
            return {
                "total_mutants": 0,
                "killed_count": 0,
                "survived_count": 0,
                "mutation_score": 0.0,
                "mutants": [],
                "error": "No source code available for mutation testing.",
            }

        # Build test cases if not provided
        test_cases: List[TestCase] = []
        if tests:
            test_cases = [TestCase(**t) for t in tests]
        else:
            # Default baseline door lock tests
            default_rule = Rule(
                id="REQ-LOCK-01",
                text="When speed > 20, lock door.",
                condition={"var": "speed", "op": ">", "value": 20.0},
                action={"var": "door", "op": "=", "value": "LOCKED"},
            )
            test_cases = gen_tests(default_rule)

        report = run_mutation_analysis(source, test_cases)
        return {
            "total_mutants": report.total_mutants,
            "killed_count": report.killed_count,
            "survived_count": report.survived_count,
            "mutation_score": report.mutation_score,
            "mutants": [m.model_dump() for m in report.mutants],
            "error": None,
        }
    except Exception as exc:
        return {
            "total_mutants": 0,
            "killed_count": 0,
            "survived_count": 0,
            "mutation_score": 0.0,
            "mutants": [],
            "error": f"run_mutation_tests failed: {str(exc)}",
        }


def search_memory(query: str, memory_type: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Search stored agent memories and pattern repository using vector cosine similarity and text matching.

    Args:
        query: Search string or key to look up.
        memory_type: Optional filter ('semantic', 'rule_pattern', 'fix_pattern', 'critic_feedback', 'failure_fix').
        limit: Maximum results to return.

    Returns:
        Dict with memories list, count, and error.
    """
    try:
        from backend.app.memory.vector_store import get_vector_store
        store = get_vector_store()
        results = store.search(query=query, memory_type=memory_type, top_k=limit, min_similarity=0.05)
        if results:
            return {
                "memories": results,
                "count": len(results),
                "error": None,
            }

        session = SessionLocal()
        q = session.query(MemoryTable)
        if memory_type:
            q = q.filter(MemoryTable.memory_type == memory_type)

        q = q.filter(
            (MemoryTable.key.contains(query)) | (MemoryTable.content.contains(query))
        )
        records = q.order_by(MemoryTable.id.desc()).limit(limit).all()
        serialized = [r.to_dict() for r in records]
        session.close()

        return {
            "memories": serialized,
            "count": len(serialized),
            "error": None,
        }
    except Exception as exc:
        return {
            "memories": [],
            "count": 0,
            "error": f"search_memory failed: {str(exc)}",
        }


def save_memory(
    key: str,
    content: str,
    memory_type: str = "semantic",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Save an associative pattern, lesson learned, or failure fix with vector embedding to SQLite.

    Args:
        key: Unique search key or topic.
        content: Text content or pattern description.
        memory_type: Memory classification ('semantic', 'rule_pattern', 'fix_pattern', 'critic_feedback', 'failure_fix').
        metadata: Optional dictionary of associated metadata.

    Returns:
        Dict with memory_id, key, saved, and error.
    """
    try:
        from backend.app.memory.vector_store import get_vector_store
        store = get_vector_store()
        mem_id = store.add_memory(
            key=key,
            content=content,
            memory_type=memory_type,
            metadata=metadata,
        )
        return {
            "memory_id": mem_id,
            "key": key,
            "saved": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "memory_id": None,
            "key": key,
            "saved": False,
            "error": f"save_memory failed: {str(exc)}",
        }
