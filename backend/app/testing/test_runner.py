"""Test Suite Runner executing TestCases on VirtualECU."""

import time
from typing import List, Optional
from datetime import datetime, timezone

from backend.app.models.domain import TestCase, Result
from backend.app.ecu.virtual_ecu import VirtualECU


class TestRunner:
    """Executes generated automotive test suites against the simulated ECU."""

    __test__ = False  # Instruct pytest not to treat this runner class as a test suite

    def __init__(self, ecu: Optional[VirtualECU] = None):
        self.ecu = ecu if ecu is not None else VirtualECU()

    def run_test(self, test: TestCase, ecu: Optional[VirtualECU] = None) -> Result:
        """Run a single TestCase and return detailed Result object.

        Returns Result with (test_id, requirement_id, inputs, expected, actual, status, logs).
        """
        target_ecu = ecu if ecu is not None else self.ecu
        logs: List[str] = [f"Starting execution of {test.id} ({test.name}) on ECU version {target_ecu.current_version}"]

        start_time = time.perf_counter()

        # Extract test inputs
        speed = float(test.given.get("speed", 0.0))
        is_lost = bool(test.given.get("is_lost", False))
        is_valid = bool(test.given.get("is_valid", True))
        if not is_valid:
            is_lost = True

        logs.append(f"Applying inputs: speed={speed}, is_lost={is_lost}, is_valid={is_valid}")

        # Execute on VirtualECU
        actual_state = target_ecu.handle_speed(speed=speed, is_lost=is_lost)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        passed = (str(actual_state).upper() == str(test.expected).upper())
        status = "PASSED" if passed else "FAILED"

        logs.append(f"Observed actual state: '{actual_state}' (Expected: '{test.expected}') -> {status}")
        if not passed:
            logs.append(f"FAIL DIAGNOSTIC: Mismatch on {test.id}. Expected '{test.expected}', received '{actual_state}'")

        return Result(
            test_id=test.id,
            requirement_id=test.req_id,
            inputs=dict(test.given),
            passed=passed,
            expected_value=test.expected,
            actual_value=actual_state,
            status=status,
            logs=logs,
            execution_time_ms=round(elapsed_ms, 3),
            error_message=None if passed else f"Expected {test.expected}, got {actual_state}",
            timestamp=datetime.now(timezone.utc),
        )

    def run_suite(self, tests: List[TestCase], ecu: Optional[VirtualECU] = None) -> List[Result]:
        """Execute a full list of TestCases sequentially."""
        results: List[Result] = []
        target_ecu = ecu if ecu is not None else self.ecu
        for test in tests:
            res = self.run_test(test, ecu=target_ecu)
            results.append(res)
        return results
