"""Deterministic Test Case Generator (Rule 4).

Generates executable test cases from structured automotive requirement Rules:
- Boundary tests: (threshold - 0.1, threshold, threshold + 0.1)
- Normal tests: (nominal idle and mid-range cruising values)
- Negative tests: (invalid sensor signals, dropped/missing CAN frames)

Expected test values are computed deterministically via plain Python code, NEVER from the LLM.
"""

from typing import List, Dict, Any, Optional
from backend.app.models.domain import Rule, TestCase


def compute_expected_value(
    rule: Rule,
    test_inputs: Dict[str, Any],
    default_safe_state: Optional[str] = None,
) -> str:
    """Compute expected outcome deterministically using plain code from the rule.

    Rule 4: Expected test values come from plain code, never from the LLM.
    """
    cond_var = rule.condition.var
    action_val = str(rule.action.value)

    # Determine default untriggered state
    if default_safe_state:
        safe_state = default_safe_state
    elif action_val == "LOCKED":
        safe_state = "UNLOCKED"
    elif action_val == "HIGH":
        safe_state = "LOW"
    elif action_val == "OFF":
        safe_state = "LOW"
    elif action_val == "FALLBACK":
        safe_state = "LOW"
    else:
        safe_state = "UNLOCKED"

    # Negative test handling: lost message or invalid signal must fail-safe to safe state
    is_lost = test_inputs.get("is_lost", False)
    is_valid = test_inputs.get("is_valid", True)
    if is_lost or not is_valid:
        # For door lock safety requirement, lost signal fails safe to LOCKED
        if rule.action.var == "door":
            return "LOCKED"
        elif rule.action.var == "beam":
            return "FALLBACK"
        return action_val

    # Evaluate rule condition against inputs
    if cond_var in test_inputs:
        val = test_inputs[cond_var]
        # Ignore negative speed if invalid
        if isinstance(val, (int, float)) and val < 0:
            return "LOCKED" if rule.action.var == "door" else safe_state

        if rule.condition.evaluate({cond_var: val}):
            return action_val

    return safe_state


def generate_tests(
    rule: Rule,
    default_safe_state: Optional[str] = None,
) -> List[TestCase]:
    """Generate boundary, normal, and negative test cases from a Rule.

    Args:
        rule: Automotive requirement Rule in fixed Pydantic format.
        default_safe_state: Optional fallback state when condition is not triggered.

    Returns:
        List of structured TestCase instances.
    """
    test_cases: List[TestCase] = []
    cond_val = rule.condition.value
    var_name = rule.condition.var
    counter = 1

    # 1. Boundary Tests (value - 0.1, value, value + 0.1)
    if isinstance(cond_val, (int, float)) and not isinstance(cond_val, bool):
        num_val = float(cond_val)
        boundary_candidates = [
            ("lower", round(num_val - 0.1, 2)),
            ("exact", round(num_val, 2)),
            ("upper", round(num_val + 0.1, 2)),
        ]

        for b_name, b_val in boundary_candidates:
            inputs = {var_name: b_val, "is_valid": True, "is_lost": False}
            expected = compute_expected_value(rule, inputs, default_safe_state)
            test_cases.append(TestCase(
                id=f"TC-{rule.id}-{counter:02d}",
                req_id=rule.id,
                rule_id=rule.id,
                name=f"Boundary test ({b_name}): {var_name}={b_val}",
                scenario=f"boundary_{b_name}",
                given=inputs,
                expected=expected,
            ))
            counter += 1

    # 2. Normal Tests (Nominal operational points)
    normal_points = [
        ("idle", 0.0),
        ("cruising", 50.0),
    ]
    for n_name, n_val in normal_points:
        inputs = {var_name: n_val, "is_valid": True, "is_lost": False}
        expected = compute_expected_value(rule, inputs, default_safe_state)
        test_cases.append(TestCase(
            id=f"TC-{rule.id}-{counter:02d}",
            req_id=rule.id,
            rule_id=rule.id,
            name=f"Normal test ({n_name}): {var_name}={n_val}",
            scenario=f"normal_{n_name}",
            given=inputs,
            expected=expected,
        ))
        counter += 1

    # 3. Negative Tests (Invalid values and missing/dropped messages)
    # Negative test A: Invalid signal flag
    neg_invalid_inputs = {var_name: 50.0, "is_valid": False, "is_lost": False}
    test_cases.append(TestCase(
        id=f"TC-{rule.id}-{counter:02d}",
        req_id=rule.id,
        rule_id=rule.id,
        name=f"Negative test (invalid signal): {var_name}=50.0, is_valid=False",
        scenario="negative_invalid_signal",
        given=neg_invalid_inputs,
        expected=compute_expected_value(rule, neg_invalid_inputs, default_safe_state),
    ))
    counter += 1

    # Negative test B: Missing / dropped message
    neg_lost_inputs = {var_name: 50.0, "is_valid": True, "is_lost": True}
    test_cases.append(TestCase(
        id=f"TC-{rule.id}-{counter:02d}",
        req_id=rule.id,
        rule_id=rule.id,
        name=f"Negative test (missing message): {var_name}=50.0, is_lost=True",
        scenario="negative_missing_message",
        given=neg_lost_inputs,
        expected=compute_expected_value(rule, neg_lost_inputs, default_safe_state),
    ))

    return test_cases
