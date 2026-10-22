"""Audit logging service for SafeSpec agent actions (Rule 8).

Ensures every agent thought, tool call, and tool result is persisted
to the SQLite agent_log table.
"""

from typing import Any, Optional, List
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.db import AgentLog, SessionLocal


class AuditLogger:
    """Service to record and query agent reasoning steps and tool execution."""

    def __init__(self, db_session: Optional[Session] = None):
        self._session = db_session

    def _get_session(self) -> Session:
        return self._session if self._session is not None else SessionLocal()

    def log_thought(
        self,
        cycle_id: str,
        agent_name: str,
        thought: str,
        attempt_number: int = 1,
        tool_call_number: int = 0,
    ) -> AgentLog:
        """Record an internal agent reasoning step (thought) to agent_log."""
        session = self._get_session()
        try:
            entry = AgentLog(
                timestamp=datetime.now(timezone.utc),
                cycle_id=cycle_id,
                agent_name=agent_name,
                attempt_number=attempt_number,
                tool_call_number=tool_call_number,
                action_type="thought",
                thought=thought,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            if self._session is None:
                session.close()

    def log_tool_call(
        self,
        cycle_id: str,
        agent_name: str,
        tool_name: str,
        tool_input: Any,
        attempt_number: int = 1,
        tool_call_number: int = 1,
    ) -> AgentLog:
        """Record an invocation of an agent tool before execution."""
        session = self._get_session()
        try:
            entry = AgentLog(
                timestamp=datetime.now(timezone.utc),
                cycle_id=cycle_id,
                agent_name=agent_name,
                attempt_number=attempt_number,
                tool_call_number=tool_call_number,
                action_type="tool_call",
                tool_name=tool_name,
                tool_input=json.dumps(tool_input, default=str),
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            if self._session is None:
                session.close()

    def log_tool_result(
        self,
        cycle_id: str,
        agent_name: str,
        tool_name: str,
        tool_output: Any,
        result_summary: Optional[str] = None,
        attempt_number: int = 1,
        tool_call_number: int = 1,
    ) -> AgentLog:
        """Record the output and result of an agent tool execution."""
        session = self._get_session()
        try:
            entry = AgentLog(
                timestamp=datetime.now(timezone.utc),
                cycle_id=cycle_id,
                agent_name=agent_name,
                attempt_number=attempt_number,
                tool_call_number=tool_call_number,
                action_type="tool_result",
                tool_name=tool_name,
                tool_output=json.dumps(tool_output, default=str),
                result=result_summary,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            if self._session is None:
                session.close()

    def log_gate(
        self,
        cycle_id: str,
        agent_name: str,
        gate_reason: str,
        attempt_number: int = 1,
    ) -> AgentLog:
        """Record when an execution cycle stops for human gate approval (Rule 9)."""
        session = self._get_session()
        try:
            entry = AgentLog(
                timestamp=datetime.now(timezone.utc),
                cycle_id=cycle_id,
                agent_name=agent_name,
                attempt_number=attempt_number,
                tool_call_number=0,
                action_type="gate",
                thought=f"STOP: Human gate required. Reason: {gate_reason}",
                result="WAITING_FOR_HUMAN",
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            if self._session is None:
                session.close()

    def get_cycle_logs(self, cycle_id: str) -> List[AgentLog]:
        """Fetch all audit logs for a specific execution cycle in chronological order."""
        session = self._get_session()
        try:
            return (
                session.query(AgentLog)
                .filter(AgentLog.cycle_id == cycle_id)
                .order_by(AgentLog.id.asc())
                .all()
            )
        finally:
            if self._session is None:
                session.close()
