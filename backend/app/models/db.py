"""SQLAlchemy database models and session setup.

Tables:
- agent_log: Comprehensive audit log of every thought, tool call, and result (Rule 8).
- ecu_versions: Immutable version history of ECU control logic supporting rollback (Rule 10).
- approvals: Safety-critical and agent proposals waiting for human sign-off (Rule 9).
"""

from datetime import datetime, timezone
from typing import Generator
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.config import DATABASE_URL

Base = declarative_base()


class AgentLog(Base):
    """Audit table logging every agent action (thought, tool call, tool result) - Rule 8."""

    __tablename__ = "agent_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    cycle_id = Column(String(64), index=True, nullable=False)
    agent_name = Column(String(64), index=True, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    tool_call_number = Column(Integer, default=0, nullable=False)
    action_type = Column(String(32), index=True, nullable=False)  # "thought", "tool_call", "tool_result", "gate"
    thought = Column(Text, nullable=True)
    tool_name = Column(String(128), nullable=True)
    tool_input = Column(Text, nullable=True)  # JSON-encoded input payload
    tool_output = Column(Text, nullable=True)  # JSON-encoded output payload
    result = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        """Convert log row to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cycle_id": self.cycle_id,
            "agent_name": self.agent_name,
            "attempt_number": self.attempt_number,
            "tool_call_number": self.tool_call_number,
            "action_type": self.action_type,
            "thought": self.thought,
            "tool_name": self.tool_name,
            "tool_input": json.loads(self.tool_input) if self.tool_input else None,
            "tool_output": json.loads(self.tool_output) if self.tool_output else None,
            "result": self.result,
        }


class EcuVersion(Base):
    """Immutable version log of simulated ECU files for safe rollback - Rule 10."""

    __tablename__ = "ecu_versions"

    version_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version_tag = Column(String(32), unique=True, index=True, nullable=False)  # e.g., "v1", "v2"
    code_hash = Column(String(64), nullable=False)  # SHA-256
    code_content = Column(Text, nullable=False)
    filename = Column(String(255), nullable=False)
    author = Column(String(64), default="system", nullable=False)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        """Convert ECU version row to dictionary."""
        return {
            "version_id": self.version_id,
            "version_tag": self.version_tag,
            "code_hash": self.code_hash,
            "filename": self.filename,
            "author": self.author,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ApprovalItem(Base):
    """Proposals and high-risk safety requirements requiring human gate sign-off - Rule 9."""

    __tablename__ = "approvals"

    id = Column(String(32), primary_key=True, index=True)  # e.g. "A-101"
    req_id = Column(String(32), index=True, nullable=False)
    kind = Column(String(32), nullable=False)  # "Rewrite", "Conflict", "Safety hint", "New test"
    title = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=True)
    proposed_text = Column(Text, nullable=False)
    grounding_score = Column(Integer, default=0, nullable=False)  # 0 to 100%
    critic_notes = Column(Text, nullable=False)
    asil_level = Column(String(8), default="QM", nullable=False)  # "QM", "A", "B", "C", "D"
    status = Column(String(32), default="pending", index=True, nullable=False)  # "pending", "approved", "rejected"
    decision_note = Column(Text, nullable=True)
    decided_by = Column(String(64), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        """Convert approval item to dictionary."""
        return {
            "id": self.id,
            "req_id": self.req_id,
            "kind": self.kind,
            "title": self.title,
            "original_text": self.original_text,
            "proposed_text": self.proposed_text,
            "grounding_score": self.grounding_score,
            "critic_notes": self.critic_notes,
            "asil_level": self.asil_level,
            "status": self.status,
            "decision_note": self.decision_note,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Database engine and session factory
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """Create all database tables if they do not exist."""
    e = target_engine or engine
    Base.metadata.create_all(bind=e)


def get_db() -> Generator[Session, None, None]:
    """Dependency helper yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
