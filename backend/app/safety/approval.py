"""Human Engineering Approval Gate Service (Rule 9).

Stores and manages approval records for formalized automotive requirements:
- Holds original text, structured Rule, plain English back-translation, and status (pending/approved/rejected).
- Enforces safety gate: ONLY approved rules go to Z3 formal verification and test generation.
- Supports database persistence in SQLite (approvals table) and in-memory management.
"""

from typing import List, Dict, Optional, Literal, Set, Any
from datetime import datetime, timezone
import uuid
import json
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.domain import Rule
from backend.app.agents.formalizer import FormalizedRequirement
from backend.app.db.tables import ApprovalTable
from backend.app.db.session import SessionLocal


class ApprovalGateError(Exception):
    """Raised when an unapproved or rejected rule violates the approval gate."""
    pass


class ApprovalRecord(BaseModel):
    """Approval record tracking human engineering sign-off on a requirement formalization."""

    id: str = Field(default_factory=lambda: f"APP-{uuid.uuid4().hex[:8]}")
    req_id: str = Field(..., description="Requirement ID (e.g. REQ-050)")
    original_text: str = Field(..., description="Original natural language requirement text")
    rule: Optional[Rule] = Field(default=None, description="Structured Rule in Rule 5 fixed format")
    back_translation: Optional[str] = Field(default=None, description="Plain English back-translation")
    status: Literal["pending", "approved", "rejected"] = Field(
        default="pending",
        description="Approval state: pending, approved, or rejected"
    )
    asil_level: str = Field(default="QM", description="ISO 26262 ASIL level (QM, A, B, C, D)")
    decision_note: Optional[str] = Field(default=None, description="Engineering comment or sign-off note")
    decided_by: Optional[str] = Field(default=None, description="Approver identifier (e.g. safety_engineer)")
    decided_at: Optional[datetime] = Field(default=None, description="Timestamp of approval decision")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp"
    )

    @property
    def is_approved(self) -> bool:
        """True if explicitly approved by an engineer."""
        return self.status == "approved"

    @property
    def is_pending(self) -> bool:
        """True if waiting for review."""
        return self.status == "pending"

    @property
    def is_rejected(self) -> bool:
        """True if rejected by an engineer."""
        return self.status == "rejected"

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "req_id": self.req_id,
            "original_text": self.original_text,
            "rule": self.rule.to_canonical_dict() if self.rule else None,
            "back_translation": self.back_translation,
            "status": self.status,
            "asil_level": self.asil_level,
            "decision_note": self.decision_note,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "created_at": self.created_at.isoformat(),
        }


def filter_approved_rules(records: List[ApprovalRecord]) -> List[Rule]:
    """Extract only approved rules from a list of approval records.

    Enforces rule: Only approved rules go to Z3 and the test generator.
    """
    return [
        rec.rule
        for rec in records
        if rec.status == "approved" and rec.rule is not None
    ]


class ApprovalManager:
    """Manages the safety approval queue and enforces the verification gate."""

    def __init__(self, db_session: Optional[Session] = None, auto_persist: bool = True):
        self.records: Dict[str, ApprovalRecord] = {}
        self.db_session = db_session
        self.auto_persist = auto_persist

    def _persist_record(self, record: ApprovalRecord) -> None:
        """Persist or update approval record in the database if session is available."""
        if not self.auto_persist:
            return

        session = self.db_session
        close_session = False
        if session is None:
            try:
                session = SessionLocal()
                close_session = True
            except Exception:
                return

        try:
            existing = session.query(ApprovalTable).filter_by(id=record.id).first()
            rule_json_str = (
                json.dumps(record.rule.to_canonical_dict())
                if record.rule is not None
                else None
            )

            if existing:
                existing.status = record.status
                existing.decision_note = record.decision_note
                existing.decided_by = record.decided_by
                existing.decided_at = record.decided_at
                existing.rule_json = rule_json_str
                existing.back_translation = record.back_translation
            else:
                db_item = ApprovalTable(
                    id=record.id,
                    req_id=record.req_id,
                    kind="Formalized Rule",
                    title=f"Formalization Approval: {record.req_id}",
                    original_text=record.original_text,
                    proposed_text=record.back_translation or record.original_text,
                    rule_json=rule_json_str,
                    back_translation=record.back_translation,
                    grounding_score=100 if record.rule else 0,
                    critic_notes=record.decision_note or "",
                    asil_level=record.asil_level,
                    status=record.status,
                    decision_note=record.decision_note,
                    decided_by=record.decided_by,
                    decided_at=record.decided_at,
                    created_at=record.created_at,
                )
                session.add(db_item)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            if close_session:
                session.close()

    def create_record(
        self,
        req_id: str,
        original_text: str,
        rule: Optional[Rule] = None,
        back_translation: Optional[str] = None,
        status: Literal["pending", "approved", "rejected"] = "pending",
        asil_level: str = "QM",
        decision_note: Optional[str] = None,
        decided_by: Optional[str] = None,
    ) -> ApprovalRecord:
        """Create a new approval record and store in queue."""
        record = ApprovalRecord(
            req_id=req_id,
            original_text=original_text,
            rule=rule,
            back_translation=back_translation,
            status=status,
            asil_level=asil_level,
            decision_note=decision_note,
            decided_by=decided_by,
            decided_at=datetime.now(timezone.utc) if status != "pending" else None,
        )
        self.records[record.id] = record
        self._persist_record(record)
        return record

    def create_from_formalized(
        self,
        formalized: FormalizedRequirement,
        status: Literal["pending", "approved", "rejected"] = "pending",
        auto_approve_qm: bool = False,
    ) -> ApprovalRecord:
        """Create approval record directly from FormalizedRequirement."""
        initial_status: Literal["pending", "approved", "rejected"] = status
        # If unformalizable, it cannot be approved as a valid rule
        if formalized.status == "not_formalizable":
            initial_status = "rejected"

        # QM rules can optionally be pre-approved if requested
        elif auto_approve_qm and formalized.asil == "QM" and formalized.rule is not None:
            initial_status = "approved"

        note = formalized.reason if formalized.status == "not_formalizable" else None
        record = self.create_record(
            req_id=formalized.req_id,
            original_text=formalized.original_text,
            rule=formalized.rule,
            back_translation=formalized.back_translation,
            status=initial_status,
            asil_level=formalized.asil,
            decision_note=note,
            decided_by="system_auto_qm" if initial_status == "approved" else None,
        )
        return record

    def approve(
        self,
        record_id: str,
        note: Optional[str] = None,
        decided_by: str = "safety_engineer",
    ) -> ApprovalRecord:
        """Approve a formalized rule for downstream Z3 formal verification and testing."""
        if record_id not in self.records:
            raise KeyError(f"Approval record '{record_id}' not found.")

        rec = self.records[record_id]
        if rec.rule is None:
            raise ValueError(f"Cannot approve {rec.req_id}: requirement has no formalized rule.")

        rec.status = "approved"
        rec.decision_note = note or "Approved by safety engineering gate."
        rec.decided_by = decided_by
        rec.decided_at = datetime.now(timezone.utc)
        self._persist_record(rec)
        return rec

    def reject(
        self,
        record_id: str,
        note: Optional[str] = None,
        decided_by: str = "safety_engineer",
    ) -> ApprovalRecord:
        """Reject a rule from proceeding to Z3 or test generator."""
        if record_id not in self.records:
            raise KeyError(f"Approval record '{record_id}' not found.")

        rec = self.records[record_id]
        rec.status = "rejected"
        rec.decision_note = note or "Rejected by safety engineering gate."
        rec.decided_by = decided_by
        rec.decided_at = datetime.now(timezone.utc)
        self._persist_record(rec)
        return rec

    def get_record(self, record_id: str) -> Optional[ApprovalRecord]:
        """Fetch a specific record by ID."""
        return self.records.get(record_id)

    def get_record_by_req_id(self, req_id: str) -> Optional[ApprovalRecord]:
        """Fetch approval record by requirement ID."""
        for rec in self.records.values():
            if rec.req_id == req_id:
                return rec
        return None

    def list_records(self, status: Optional[str] = None) -> List[ApprovalRecord]:
        """List all records, optionally filtered by status."""
        if status:
            return [r for r in self.records.values() if r.status == status]
        return list(self.records.values())

    def get_approved_rules(self) -> List[Rule]:
        """Return ONLY approved rules.

        Strict safety constraint:
        Only approved rules go to Z3 and the test generator.
        """
        approved_rules: List[Rule] = []
        for rec in self.records.values():
            if rec.status == "approved" and rec.rule is not None:
                approved_rules.append(rec.rule)
        return approved_rules

    def clear(self) -> None:
        """Clear in-memory records."""
        self.records.clear()
