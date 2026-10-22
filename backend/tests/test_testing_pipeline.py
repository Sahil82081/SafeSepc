"""Pytest suite for Testing Engine (backend/app/testing).

Validates:
1. test_generator.py: Boundary (val-0.1, val, val+0.1), normal, and negative tests with plain code expectations.
2. test_runner.py: Returns Result objects with test_id, requirement_id, inputs, expected, actual, status, logs.
3. fault_injection.py: Message lost, message delayed, and sensor stuck faults.
4. mutation.py: Generates mutations and measures killed mutants.
5. Done Criteria: v1 passes all tests and both buggy versions fail some tests.
"""

from pathlib import Path
import pytest

from backend.app.models.domain import Rule, TestCase, Result
from backend.app.ecu.virtual_ecu import VirtualECU
from backend.app.testing.test_generator import generate_tests, compute_expected_value
from backend.app.testing.test_runner import TestRunner
from backend.app.testing.fault_injection import (
    MessageLostFault,
    MessageDelayedFault,
    SensorStuckFault,
    FaultInjector,
)
from backend.app.testing.mutation import run_mutation_analysis, EcuMutator


@pytest.fixture
def door_lock_rule() -> Rule:
    """Standard automotive door lock requirement rule."""
    return Rule(
        id="REQ-LOCK-01",
        text="When vehicle speed exceeds 20.0 km/h, the central door locking system shall lock all doors.",
        condition={"var": "speed", "op": ">", "value": 20.0},
        action={"var": "door", "op": "=", "value": "LOCKED"},
        asil="B",
    )


def test_test_generator_coverage(door_lock_rule):
    """Test 1: Verify test_generator produces boundary, normal, and negative tests with plain code expectations."""
    tests = generate_tests(door_lock_rule)

    assert len(tests) >= 7, f"Expected at least 7 generated test cases, got {len(tests)}"

    # Map scenarios
    scenarios = {t.scenario: t for t in tests}

    # Verify boundary tests
    assert "boundary_lower" in scenarios
    assert scenarios["boundary_lower"].given["speed"] == 19.9
    assert scenarios["boundary_lower"].expected == "UNLOCKED"

    assert "boundary_exact" in scenarios
    assert scenarios["boundary_exact"].given["speed"] == 20.0
    assert scenarios["boundary_exact"].expected == "UNLOCKED"

    assert "boundary_upper" in scenarios
    assert scenarios["boundary_upper"].given["speed"] == 20.1
    assert scenarios["boundary_upper"].expected == "LOCKED"

    # Verify normal tests
    assert "normal_idle" in scenarios
    assert scenarios["normal_idle"].given["speed"] == 0.0
    assert scenarios["normal_idle"].expected == "UNLOCKED"

    assert "normal_cruising" in scenarios
    assert scenarios["normal_cruising"].given["speed"] == 50.0
    assert scenarios["normal_cruising"].expected == "LOCKED"

    # Verify negative tests
    assert "negative_invalid_signal" in scenarios
    assert scenarios["negative_invalid_signal"].expected == "LOCKED"  # Fail-safe to LOCKED

    assert "negative_missing_message" in scenarios
    assert scenarios["negative_missing_message"].given["is_lost"] is True
    assert scenarios["negative_missing_message"].expected == "LOCKED"  # Fail-safe to LOCKED


def test_test_runner_result_format(door_lock_rule):
    """Test 2: Verify test_runner returns Result objects containing required fields."""
    tests = generate_tests(door_lock_rule)
    runner = TestRunner()

    result = runner.run_test(tests[0])

    assert isinstance(result, Result)
    assert result.test_id == tests[0].id
    assert result.requirement_id == door_lock_rule.id
    assert isinstance(result.inputs, dict)
    assert result.expected is not None
    assert result.actual is not None
    assert result.status in ("PASSED", "FAILED")
    assert isinstance(result.logs, list) and len(result.logs) > 0
    assert result.execution_time_ms >= 0.0


def test_core_criterion_v1_passes_and_buggy_versions_fail(door_lock_rule):
    """Core Done Criteria:

    v1 passes all tests and both buggy versions fail some tests.
    """
    tests = generate_tests(door_lock_rule)
    runner = TestRunner()

    # 1. Version v1 (Correct): MUST pass ALL generated tests
    ecu_v1 = VirtualECU(initial_version="v1")
    results_v1 = runner.run_suite(tests, ecu=ecu_v1)

    failing_v1 = [r for r in results_v1 if not r.passed]
    assert len(failing_v1) == 0, f"Expected v1 to pass ALL tests, but failed: {[r.test_id for r in failing_v1]}"
    assert all(r.passed for r in results_v1)
    assert all(r.status == "PASSED" for r in results_v1)

    # 2. Version v1_buggy_threshold (Threshold 80 instead of 20): MUST FAIL some tests
    ecu_buggy_thr = VirtualECU(initial_version="v1_buggy_threshold")
    results_thr = runner.run_suite(tests, ecu=ecu_buggy_thr)

    failing_thr = [r for r in results_thr if not r.passed]
    assert len(failing_thr) > 0, "Expected v1_buggy_threshold to FAIL tests on speeds between 20 and 80 km/h!"
    # Specifically, boundary_upper (20.1 km/h) and normal_cruising (50 km/h) must fail
    failing_scenarios_thr = [
        t.scenario for t in tests if any(r.test_id == t.id and not r.passed for r in results_thr)
    ]
    assert "boundary_upper" in failing_scenarios_thr
    assert "normal_cruising" in failing_scenarios_thr

    # 3. Version v1_buggy_timeout (Ignores lost speed message): MUST FAIL some tests
    ecu_buggy_to = VirtualECU(initial_version="v1_buggy_timeout")
    results_to = runner.run_suite(tests, ecu=ecu_buggy_to)

    failing_to = [r for r in results_to if not r.passed]
    assert len(failing_to) > 0, "Expected v1_buggy_timeout to FAIL on lost/invalid message tests!"
    failing_scenarios_to = [
        t.scenario for t in tests if any(r.test_id == t.id and not r.passed for r in results_to)
    ]
    assert "negative_missing_message" in failing_scenarios_to


def test_fault_injection_models():
    """Test 3: Verify MessageLostFault, MessageDelayedFault, and SensorStuckFault."""
    base_inputs = {"speed": 60.0, "is_valid": True, "is_lost": False}

    # Message lost
    lost_inputs = FaultInjector.inject_lost_message(base_inputs)
    assert lost_inputs["is_lost"] is True
    assert lost_inputs["is_valid"] is False
    assert lost_inputs["speed"] == 60.0

    # Message delayed
    delayed_inputs = FaultInjector.inject_delayed_message(base_inputs, delay_ms=450.0)
    assert delayed_inputs["is_delayed"] is True
    assert delayed_inputs["latency_ms"] == 450.0

    # Sensor stuck
    stuck_inputs = FaultInjector.inject_stuck_sensor(base_inputs, var="speed", value=0.0)
    assert stuck_inputs["speed"] == 0.0
    assert stuck_inputs["is_stuck"] is True


def test_mutation_analysis(door_lock_rule):
    """Test 4: Verify mutation analysis catches mutations on v1 logic."""
    v1_path = Path(__file__).resolve().parent.parent / "app" / "ecu" / "versions" / "v1.py"
    v1_code = v1_path.read_text(encoding="utf-8")

    tests = generate_tests(door_lock_rule)
    report = run_mutation_analysis(v1_code, tests)

    assert report.total_mutants > 0
    assert report.killed_count > 0
    # The generated test suite should achieve high mutation score (> 70%)
    assert report.mutation_score >= 70.0, f"Expected mutation score >= 70%, got {report.mutation_score}%"
    assert report.killed_count + report.survived_count == report.total_mutants
