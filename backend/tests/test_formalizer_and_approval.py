"""Tests for Formalizer Agent and Safety Approval Gate (Rule 4, Rule 5, Rule 8, Rule 9).

Validates:
1. Formalizer converts Requirement into Rule in fixed Pydantic format {id, text, condition, action}.
2. Plain English back-translation is generated for each formalized rule.
3. Unformalizable requirements ('quickly') are marked 'not_formalizable' with a reason.
4. Approval record holds original text, rule, back-translation, and status (pending/approved/rejected).
5. Only approved rules go to Z3 formal checker and test generator.
6. Offline execution with mock Gemini client.
"""

import pytest
import uuid
from backend.app.models.domain import Requirement, Rule, RuleCondition, RuleAction
from backend.app.agents.formalizer import (
    RequirementFormalizerAgent,
    FormalizedRequirement,
    generate_back_translation,
)
from backend.app.agents.llm import GeminiClient, LLMResponse
from backend.app.safety.approval import (
    ApprovalRecord,
    ApprovalManager,
    filter_approved_rules,
)


def test_rule_fixed_pydantic_format():
    """Verify Rule 5 fixed Pydantic format for formalized rules."""
    cond = RuleCondition(var="speed", op=">", value=20.0)
    act = RuleAction(var="door", op="=", value="LOCKED")
    rule = Rule(
        id="REQ-050",
        text="The central door locking system shall lock all doors when speed exceeds 20.0 km/h.",
        condition=cond,
        action=act,
        asil="B",
    )

    d = rule.to_canonical_dict()
    assert d["id"] == "REQ-050"
    assert "condition" in d
    assert d["condition"] == {"var": "speed", "op": ">", "value": 20.0}
    assert "action" in d
    assert d["action"] == {"var": "door", "op": "=", "value": "LOCKED"}


def test_back_translation_generation():
    """Verify plain English back-translation generator produces unambiguous descriptions."""
    r_door = Rule(
        id="REQ-050",
        text="Lock doors when speed > 20.",
        condition=RuleCondition(var="speed", op=">", value=20.0),
        action=RuleAction(var="door", op="=", value="LOCKED"),
    )
    bt_door = generate_back_translation(r_door)
    assert "vehicle speed exceeds 20.0 km/h" in bt_door
    assert "central door lock shall be LOCKED" in bt_door

    r_beam = Rule(
        id="REQ-012",
        text="Oncoming vehicle beam switch.",
        condition=RuleCondition(var="oncoming_distance", op="<=", value=150.0),
        action=RuleAction(var="beam", op="=", value="LOW"),
    )
    bt_beam = generate_back_translation(r_beam)
    assert "oncoming vehicle distance is at most 150.0 m" in bt_beam
    assert "headlamp shall switch to LOW beam" in bt_beam


def test_formalizer_unclear_requirement_marked_not_formalizable():
    """Verify requirements with vague words ('quickly') are marked 'not_formalizable' with reason."""
    req_unclear = Requirement(
        id="REQ-023",
        text="The headlamp system shall quickly switch to low beam when an oncoming vehicle is detected.",
        ambiguity="HIGH",
        flags=["ambiguous"],
        terms=["quickly"],
        problem="Lacks measurable latency limit in milliseconds.",
        suggestion="Specify: switch within 200 ms.",
        asil="C",
    )

    agent = RequirementFormalizerAgent()
    res = agent.formalize_single(req_unclear)

    assert isinstance(res, FormalizedRequirement)
    assert res.status == "not_formalizable"
    assert res.is_formalizable is False
    assert res.rule is None
    assert res.back_translation is None
    assert res.reason is not None
    assert "latency" in res.reason.lower() or "quickly" in res.reason.lower()


def test_formalizer_converts_door_rule():
    """Verify formalizer converts door lock requirement into checkable Rule."""
    req_door = Requirement(
        id="REQ-050",
        text="The central door locking system shall automatically lock all doors when vehicle speed exceeds 20.0 km/h.",
        ambiguity="LOW",
        safety=True,
        asil="B",
    )

    agent = RequirementFormalizerAgent()
    res = agent.formalize_single(req_door)

    assert res.status == "formalized"
    assert res.is_formalizable is True
    assert res.rule is not None
    assert res.rule.condition.var == "speed"
    assert res.rule.condition.op == ">"
    assert res.rule.condition.value == 20.0
    assert res.rule.action.var == "door"
    assert res.rule.action.value == "LOCKED"
    assert res.back_translation is not None
    assert "vehicle speed exceeds 20.0 km/h" in res.back_translation


def test_formalizer_with_mock_gemini():
    """Verify formalizer operates with GeminiClient in mock responder mode (Rule 3)."""
    def custom_gemini_responder(prompt: str, tools):
        payload = {
            "status": "formalized",
            "condition": {"var": "speed", "op": ">", "value": 25.0},
            "action": {"var": "door", "op": "=", "value": "LOCKED"},
            "back_translation": "If vehicle speed exceeds 25.0 km/h, the central door lock shall be LOCKED.",
        }
        import json
        return LLMResponse(text=json.dumps(payload))

    mock_client = GeminiClient(mock_responder=custom_gemini_responder)

    agent = RequirementFormalizerAgent(llm_client=mock_client)
    req = Requirement(id="REQ-CUSTOM", text="Lock doors at 25 km/h", asil="B")
    res = agent.formalize_single(req)

    assert res.status == "formalized"
    assert res.rule is not None
    assert res.rule.condition.value == 25.0
    assert res.rule.action.value == "LOCKED"


def test_approval_record_structure_and_gate():
    """Verify approval record stores original text, rule, back_translation, and status."""
    r = Rule(
        id="REQ-050",
        text="Lock doors when speed > 20.",
        condition=RuleCondition(var="speed", op=">", value=20.0),
        action=RuleAction(var="door", op="=", value="LOCKED"),
        asil="B",
    )
    bt = generate_back_translation(r)

    approval_mgr = ApprovalManager(auto_persist=False)
    rec = approval_mgr.create_record(
        req_id=r.id,
        original_text=r.text,
        rule=r,
        back_translation=bt,
        status="pending",
        asil_level="B",
    )

    # Initial state is pending
    assert rec.status == "pending"
    assert rec.original_text == r.text
    assert rec.rule == r
    assert rec.back_translation == bt

    # GATE CHECK: unapproved rules must NOT pass to Z3 or test generator
    approved_rules = approval_mgr.get_approved_rules()
    assert len(approved_rules) == 0

    # Engineer reviews and approves
    approved_rec = approval_mgr.approve(rec.id, note="Engineering sign-off complete.")
    assert approved_rec.status == "approved"
    assert approved_rec.is_approved is True
    assert approved_rec.decided_by == "safety_engineer"
    assert approved_rec.decided_at is not None

    # Now approved rule is released to downstream pipeline
    approved_rules = approval_mgr.get_approved_rules()
    assert len(approved_rules) == 1
    assert approved_rules[0].id == "REQ-050"


def test_approval_rejection_blocks_rule():
    """Verify rejected rule cannot pass to downstream verification."""
    r = Rule(
        id="REQ-REJECTED",
        text="Unsafe behavior rule",
        condition=RuleCondition(var="speed", op=">", value=120.0),
        action=RuleAction(var="door", op="=", value="UNLOCKED"),
        asil="D",
    )

    approval_mgr = ApprovalManager(auto_persist=False)
    rec = approval_mgr.create_record(
        req_id=r.id,
        original_text=r.text,
        rule=r,
        back_translation="Unsafe rule back-translation",
        status="pending",
        asil_level="D",
    )

    approval_mgr.reject(rec.id, note="Rejected due to severe ASIL D hazard.")
    assert rec.status == "rejected"
    assert rec.is_rejected is True

    # Gate strictly blocks rejected rule
    approved = approval_mgr.get_approved_rules()
    assert len(approved) == 0


def test_filter_approved_rules_standalone():
    """Verify standalone filter_approved_rules utility."""
    r1 = Rule(id="R1", text="r1", condition=RuleCondition(var="a", op="==", value=1), action=RuleAction(var="b", value=2))
    r2 = Rule(id="R2", text="r2", condition=RuleCondition(var="c", op="==", value=3), action=RuleAction(var="d", value=4))

    recs = [
        ApprovalRecord(req_id="R1", original_text="r1", rule=r1, status="approved"),
        ApprovalRecord(req_id="R2", original_text="r2", rule=r2, status="pending"),
        ApprovalRecord(req_id="R3", original_text="r3", rule=None, status="rejected"),
    ]

    filtered = filter_approved_rules(recs)
    assert len(filtered) == 1
    assert filtered[0].id == "R1"
