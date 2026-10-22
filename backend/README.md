# SafeSpec Backend

Automotive Requirements Verification & Simulation Research Prototype.
Reads automotive requirements PDFs, turns rules into checkable form, tests simulated ECUs via a virtual CAN bus, identifies root causes for test failures, proposes fixes, and maintains tamper-evident audit proof.

---

## Architecture Overview

```text
backend/app/
├── api/          # FastAPI REST endpoints & SSE streaming
├── schemas/      # API schemas and transport contracts
├── models/       # Pydantic models (Requirement, Rule, Conflict, TestCase, Result, Fix, RiskReport)
├── db/           # SQLite schema & SQLAlchemy tables (runs, requirements, rules, tests, results, fixes, approvals, agent_log, memories)
├── formal/       # Z3 SMT solver & formal consistency logic
├── simulation/   # Virtual vehicle dynamics & CAN bus telemetry
├── ecu/          # Electronic Control Unit controllers & immutable version store
├── testing/      # Deterministic test generator & test suite runner
├── tools/        # Gemini function-calling tools with typed input/output
├── agents/       # Quality, safety, triage, and fix agents
├── memory/       # Associative patterns & retrieval memories
├── safety/       # ISO 26262 ASIL risk classification & human gate enforcement
├── workflows/    # LangGraph pipeline orchestration
└── reports/      # Traceability matrix & verification audit reports
```

---

## Core Rules & Architectural Principles

1. **Rule 3**: The Gemini API key comes from `.env` (`GEMINI_API_KEY`). The model name lives **only** in `backend/app/config.py`.
2. **Rule 4**: The LLM reasons and invokes tools. Z3, pytest, and plain code decide correctness. Expected test values come from plain code, **never** from the LLM.
3. **Rule 5**: All rules use one fixed Pydantic format:
   `{id, text, condition:{var,op,value}, action:{var,op,value}}`
4. **Rule 6**: Agents use Gemini function calling. Every tool is a plain Python function with typed input/output that never crashes and returns an error field.
5. **Rule 7**: Agent loops have strict limits: maximum **3 fix attempts**, maximum **8 tool calls per attempt**.
6. **Rule 8**: Every agent action (thought, tool, result) is persisted to the `agent_log` table.
7. **Rule 9**: High-risk changes (ASIL C/D) stop and wait for a human sign-off.
8. **Rule 10**: Never overwrite an ECU file. Keep immutable versions and allow rollback.
9. **Rule 11**: Every module includes type hints, short docstrings, and a pytest test.
10. **Rule 12**: One stage at a time. Run tests, show results, then stop.

---

## Setup & Run Steps

### 1. Create and Activate Virtual Environment
```powershell
# From the SafeSpec/backend directory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and configure your Gemini API key:
```powershell
copy .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_google_gemini_api_key
DATABASE_URL=sqlite:///./safespec.db
```

### 4. Initialize Database Tables
```powershell
python -c "from backend.app.db import init_db; init_db(); print('Database tables created successfully.')"
```

### 5. Run Pytest Test Suite
```powershell
pytest -v
```

### 6. Start the Backend API Server
```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
