"""Pytest suite for Z3 Formal Verification Checker (backend/app/formal/z3_checker.py).

Tests required by specification:
1. One valid rule set (no conflicts, safety invariant holds).
2. One conflicting set (contradictory actions on overlapping conditions).
3. One set that allows the bad state (speed > 20 and door != LOCKED).
4. Numeric and enum variable support with concrete counter-examples.
"""

import pytest
from backend.app.models.domain import Rule, RuleCondition, RuleAction, Conflict
from backend.app.formal.z3_checker import find_conflicts, check_invariant, parse_bad_state


def test_valid_rule_set():
    """Test 1: A valid, non-conflicting rule set where safety invariant holds."""
    rule1 = Rule(
        id="REQ-LOCK-01",
        text="When speed exceeds 20 km/h, the vehicle door must be locked.",
        condition={"var": "speed", "op": ">", "value": 20},
        action={"var": "door", "op": "=", "value": "LOCKED"},
    )
    rule2 = Rule(
        id="REQ-LOCK-02",
        text="When speed is at or below 20 km/h, the vehicle door may be unlocked.",
        condition={"var": "speed", "op": "<=", "value": 20},
        action={"var": "door", "op": "=", "value": "UNLOCKED"},
    )

    rules = [rule1, rule2]

    # Verify no pairwise conflicts exist
    conflicts = find_conflicts(rules)
    assert len(conflicts) == 0, f"Expected 0 conflicts, got {conflicts}"

    # Verify safety invariant holds: bad state (speed > 20 and door != LOCKED) is IMPOSSIBLE
    violation_str = check_invariant(rules, "speed > 20 and door != LOCKED")
    assert violation_str is None, f"Expected invariant to hold, got violation: {violation_str}"

    violation_list = check_invariant(
        rules,
        [
            RuleCondition(var="speed", op=">", value=20),
            RuleCondition(var="door", op="!=", value="LOCKED"),
        ]
    )
    assert violation_list is None

    violation_dict = check_invariant(
        rules,
        {"speed": (">", 20), "door": ("!=", "LOCKED")}
    )
    assert violation_dict is None


def test_conflicting_rule_set():
    """Test 2: A conflicting rule set with overlapping conditions and contradictory actions."""
    # Automotive headlamp speed threshold contradiction (REQ-017 vs REQ-031)
    rule_a = Rule(
        id="REQ-017",
        text="The high beam shall activate above 30 km/h in darkness.",
        condition={"var": "speed", "op": ">", "value": 30},
        action={"var": "beam", "op": "=", "value": "HIGH"},
    )
    rule_b = Rule(
        id="REQ-031",
        text="The headlamp shall stay in low beam below 40 km/h.",
        condition={"var": "speed", "op": "<", "value": 40},
        action={"var": "beam", "op": "=", "value": "LOW"},
    )

    conflicts = find_conflicts([rule_a, rule_b])

    assert len(conflicts) == 1, f"Expected exactly 1 conflict, found {len(conflicts)}"
    conflict = conflicts[0]

    assert isinstance(conflict, Conflict)
    assert conflict.rule_a_id == "REQ-017"
    assert conflict.rule_b_id == "REQ-031"
    assert conflict.severity == "HIGH"
    assert "beam" in conflict.description
    assert conflict.reason == conflict.description

    # Counter-example verification
    assert conflict.counter_example is not None
    assert "speed" in conflict.counter_example
    overlap_speed = conflict.counter_example["speed"]
    assert 30 < overlap_speed < 40, f"Counter-example speed {overlap_speed} must be in (30, 40)"


def test_set_allowing_bad_state():
    """Test 3: A rule set that permits the bad state (speed > 20 and door != LOCKED)."""
    # Flawed rule: passenger unlock request unlocks door without verifying vehicle speed
    faulty_rule = Rule(
        id="REQ-DOOR-FLAWED",
        text="When passenger requests door unlock, the door shall be unlocked.",
        condition={"var": "speed", "op": ">", "value": 10},
        action={"var": "door", "op": "=", "value": "UNLOCKED"},
    )

    bad_state = "speed > 20 and door != LOCKED"
    violation = check_invariant([faulty_rule], bad_state)

    assert violation is not None, "Expected invariant violation for flawed door rule"
    assert isinstance(violation, Conflict)
    assert violation.severity == "CRITICAL"
    assert "Bad state is reachable" in violation.description
    assert violation.reason == violation.description

    # Verify counter-example state
    ce = violation.counter_example
    assert ce is not None
    assert "speed" in ce
    assert "door" in ce
    assert ce["speed"] > 20, f"Counter-example speed {ce['speed']} must be > 20"
    assert ce["door"] != "LOCKED", f"Counter-example door {ce['door']} must not be LOCKED"
    assert ce["door"] == "UNLOCKED"


def test_numeric_and_enum_variables():
    """Test 4: Mixed numeric (speed, lux) and enum (beam, door) variable reasoning."""
    # Test enum contradiction on ambient light
    r1 = Rule(
        id="REQ-LIGHT-01",
        text="Low ambient light commands high beam.",
        condition={"var": "lux", "op": "<", "value": 50},
        action={"var": "beam", "op": "=", "value": "HIGH"},
    )
    r2 = Rule(
        id="REQ-LIGHT-02",
        text="Ambient light below 80 lux commands low beam.",
        condition={"var": "lux", "op": "<", "value": 80},
        action={"var": "beam", "op": "=", "value": "LOW"},
    )

    conflicts = find_conflicts([r1, r2])
    assert len(conflicts) == 1
    assert "lux" in conflicts[0].counter_example
    assert conflicts[0].counter_example["lux"] < 50


def test_parse_bad_state_helpers():
    """Test parsing various bad state representation formats."""
    # String format
    conds = parse_bad_state("speed > 20 and door != LOCKED")
    assert len(conds) == 2
    assert conds[0].var == "speed" and conds[0].op == ">" and conds[0].value == 20
    assert conds[1].var == "door" and conds[1].op == "!=" and conds[1].value == "LOCKED"

    # Dict format
    conds_dict = parse_bad_state({"speed": (">", 20), "door": ("!=", "LOCKED")})
    assert len(conds_dict) == 2

    # Single RuleCondition
    rc = RuleCondition(var="temp", op=">=", value=100)
    assert parse_bad_state(rc) == [rc]
