"""Database Package for SafeSpec.

Exports:
- Base
- Table models:
  - RunTable (runs)
  - RequirementTable (requirements)
  - RuleTable (rules)
  - TestTable (tests)
  - ResultTable (results)
  - FixTable (fixes)
  - ApprovalTable (approvals)
  - AgentLogTable (agent_log)
  - MemoryTable (memories)
  - EcuVersionTable (ecu_versions)
- Engine, SessionLocal, init_db, get_db
"""

from backend.app.db.tables import (
    Base,
    RunTable,
    RequirementTable,
    RuleTable,
    TestTable,
    ResultTable,
    FixTable,
    ApprovalTable,
    AgentLogTable,
    MemoryTable,
    EcuVersionTable,
)
from backend.app.db.session import (
    engine,
    SessionLocal,
    init_db,
    get_db,
)

__all__ = [
    "Base",
    "RunTable",
    "RequirementTable",
    "RuleTable",
    "TestTable",
    "ResultTable",
    "FixTable",
    "ApprovalTable",
    "AgentLogTable",
    "MemoryTable",
    "EcuVersionTable",
    "engine",
    "SessionLocal",
    "init_db",
    "get_db",
]
