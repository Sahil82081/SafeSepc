# SafeSpec: Autonomous Automotive Safety Specification & SMT Verification Platform

> **ISO 26262 ASIL D • Z3 Theorem Prover • CAN Bus Virtual ECU Simulation • LangGraph Agent Orchestration**

[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Z3 Solver](https://img.shields.io/badge/Z3%20SMT-4.13+-ff69b4.svg)](https://github.com/Z3Prover/z3)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178c6.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/tests-78%2F78%20passing-brightgreen.svg)](https://pytest.org/)

---

## 📌 Overview

**SafeSpec** is an autonomous safety specification, formal verification, and virtual validation platform for safety-critical automotive systems (ISO 26262, AUTOSAR, and UNECE regulations). 

Given an automotive requirements PDF specification (such as headlamp control, central locking, or electronic stability), SafeSpec:
1. **Extracts & Audits Requirements**: Parses unstructured natural language, scores semantic ambiguity (`LOW`, `MEDIUM`, `HIGH`), and flags vague engineering terms (e.g., *"quickly"* without an exact millisecond bound).
2. **Formalizes to Mathematical ASTs**: Converts natural text into standard Rule 5 Pydantic schemas `{id, text, condition:{var, op, value}, action:{var, op, value}}` and generates bi-directional plain-English back-translations.
3. **Enforces Safety Sign-Off Gates (Rule 9)**: Imposes human engineering review for high-risk ASIL C/D items before formal analysis or testing.
4. **Proves Contradictions with Z3 SMT**: Formally verifies cross-rule consistency, detecting overlapping conditions with contradictory actuator commands and synthesizing mathematical counter-examples.
5. **Generates Deterministic CAN Tests (Rule 4)**: Automatically produces boundary value tests ($value - 0.1$, $value$, $value + 0.1$), normal operational tests, and negative fault tests (dropped/delayed frames, invalid sensor signals) with plain-code expected values.
6. **Executes Virtual ECU Simulation**: Tests logic in real-time over virtual CAN bus channels, collecting telemetry traces and timing metrics.
7. **Diagnoses & Patches Faults (Rule 10)**: Iteratively isolates root causes, synthesizes code diffs with immutable versioning, and validates patches with full regression and mutation tests.
8. **Generates Compliance Reports**: Produces sign-off ready Markdown and PDF audit reports.

---

## 🏗️ Architecture

```
                                  [ Automotive Requirements PDF ]
                                                 │
                                                 ▼
                                   ┌───────────────────────────┐
                                   │  PDF Parser & Extractor   │
                                   │  (ISO 26262 Quality Audit)│
                                   └─────────────┬─────────────┘
                                                 │
                                                 ▼
                                   ┌───────────────────────────┐
                                   │ Rule 5 Formalizer Agent   │
                                   │ (ASTs + Back-Translation) │
                                   └─────────────┬─────────────┘
                                                 │
                                                 ▼
                                   ┌───────────────────────────┐
                                   │  Human Safety Gate (R9)   │
                                   │ (Approval & ASIL C/D Sign)│
                                   └─────────────┬─────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                 ▼
         ┌─────────────────────────────┐                   ┌─────────────────────────────┐
         │     Z3 SMT Solver Prover    │                   │   Deterministic CAN Tests   │
         │ (Contradictions & Overlaps) │                   │  (Boundary, Normal, Faults) │
         └──────────────┬──────────────┘                   └──────────────┬──────────────┘
                        │                                                 │
                        │                                                 ▼
                        │                                  ┌─────────────────────────────┐
                        │                                  │   Virtual ECU Simulation    │
                        │                                  │     (CAN Bus Telemetry)     │
                        │                                  └──────────────┬──────────────┘
                        │                                                 │
                        │                                                 ▼
                        │                                  ┌─────────────────────────────┐
                        │                                  │  Root-Cause Agent & Repair  │
                        │                                  │ (Immutable ECU v1->v2 Patch)│
                        │                                  └──────────────┬──────────────┘
                        │                                                 │
                        └────────────────────────┬────────────────────────┘
                                                 │
                                                 ▼
                                   ┌───────────────────────────┐
                                   │ Executive Report & UI DAG │
                                   │ (Interactive Traceability)│
                                   └───────────────────────────┘
```

---

## 🚀 Quickstart: One Command Starts Everything

### Option 1: Docker Compose (Full Stack)

To build and boot both the backend FastAPI service (port `8000`) and the React Vite UI (port `5173` & `80`):

```bash
docker compose up --build
```

- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option 2: Instant End-to-End Demo Script

To execute the entire verification pipeline on the pre-packaged `sample_requirements.pdf` directly from your terminal:

```bash
python run_demo.py
```

The script runs end-to-end, printing:
- Ingestion of 10 requirements with ISO 26262 quality flags (e.g. `REQ-023` flagged for *"quickly"*).
- Formalization into 9 AST rules with English back-translations.
- Z3 SMT solver proving the contradiction between `REQ-017` and `REQ-031` with counter-example speed $31.0\text{ km/h}$.
- 7 generated CAN bus boundary and negative test cases.
- Virtual ECU simulation results (100% pass rate).
- Full executive verification report excerpt.

---

### Option 3: Local Development (Without Docker)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
# In a new terminal, navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) in your browser.

---

## ⚡ One-Click "Demo Mode" in Frontend

SafeSpec includes a dedicated **Demo Mode** button in the web application:
- Located directly in the top **Navigation Header** (`⚡ Demo Mode`) on all pages.
- Also available as a prominent instant-start hero card on the **Upload Specification** page.

Clicking **Demo Mode**:
1. Triggers `POST /runs/demo` on the backend.
2. Automatically loads `backend/documents/sample_requirements.pdf`.
3. Dispatches the full LangGraph workflow in the background.
4. Switches the active workspace run and opens the real-time **Agent Activity Timeline (SSE)** to stream reasoning steps, tool invocations, and test outcomes live.

---

## 🧪 Testing & Validation

### Backend Test Suite
All 78 unit, integration, and property-based tests run with `pytest`:

```bash
# From the project root:
pytest backend -v
```

**Coverage includes**:
- OpenAPI schema validation & CORS compatibility.
- Gemini Extractor and Formalizer tool-calling agents.
- Z3 SMT contradiction detection and mathematical counter-examples.
- Deterministic boundary test generation ($value - 0.1$, $value$, $value + 0.1$).
- Virtual ECU simulation over CAN bus with message drop/delay fault injection.
- Safety gate approvals and ASIL C/D human sign-off enforcement.
- Root cause diagnosis, vector memory retrieval, and immutable ECU versioning.
- Defect detection benchmark evaluation (10 planted defects).

### Frontend TypeScript & Production Build
```bash
cd frontend
npm run build
```
Runs `tsc -b` with strict TypeScript typing (`noUnusedLocals`, `noUnusedParameters`) and outputs the production bundle.

### Defect Benchmark Evaluation
```bash
python -m backend.evaluation.run_eval
```
Runs SafeSpec against 10 planted defect scenarios (contradictory rules, threshold bugs, sensor timeout mutations) and prints the detection rate and mutation score.

---

## 📁 Repository Structure

```
SafeSpec/
├── backend/
│   ├── app/
│   │   ├── agents/          # Gemini tool-calling agents (Extractor, Formalizer, Root Cause)
│   │   ├── api/             # FastAPI REST endpoints, routers & SSE streaming
│   │   ├── config.py        # Centralized settings & LLM model name (Rule 3)
│   │   ├── db/              # SQLAlchemy SQLite models & session management
│   │   ├── ecu/             # Virtual ECU runtime & CAN bus communication
│   │   ├── formal/          # Z3 SMT invariant & contradiction solver
│   │   ├── memory/          # SQLite vector store with Gemini embeddings & cosine similarity
│   │   ├── models/          # Pydantic schemas (Rule 5 schema, Requirement, TestCase, Result)
│   │   ├── reports/         # Markdown and PDF compliance report generators
│   │   ├── safety/          # ISO 26262 ASIL risk scorer & approval gate (Rule 9)
│   │   ├── testing/         # Plain-code test generator (Rule 4), runner & mutator
│   │   ├── tools/           # Agent tools & registry with Gemini function declarations
│   │   └── workflows/       # LangGraph state machine & pipeline orchestrator
│   ├── documents/           # ISO 26262 requirements PDF documents (sample_requirements.pdf)
│   ├── evaluation/          # Benchmark suite with 10 planted defects
│   ├── tests/               # 78 comprehensive pytest test cases
│   ├── Dockerfile           # Python 3.12 slim backend container definition
│   └── requirements.txt     # Python package requirements
├── frontend/
│   ├── src/
│   │   ├── api/             # API client, OpenAPI TypeScript types & TanStack Query hooks
│   │   ├── components/      # UI components (Header, Sidebar, Cards, Drawers, Skeletons)
│   │   ├── context/         # RunContext (active run state) & ThemeContext (Dark/Light)
│   │   └── pages/           # 10 dedicated platform pages:
│   │       ├── DashboardPage.tsx     # KPI metrics & Recharts pass-rate charts
│   │       ├── UploadPage.tsx        # PDF dropzone, ECU selector, stage stepper & Demo Mode
│   │       ├── RequirementsPage.tsx  # Extracted requirements with ambiguity filters
│   │       ├── VerificationPage.tsx  # Side-by-side Z3 conflicts & counter-examples
│   │       ├── TestResultsPage.tsx   # Filterable CAN test telemetry & drawer
│   │       ├── FailuresPage.tsx      # Root cause explanation & code diff patch viewer
│   │       ├── ApprovalsPage.tsx     # Rule 9 safety engineer approval gate
│   │       ├── AgentActivityPage.tsx # Live SSE timeline (thoughts, tools, results)
│   │       ├── TraceabilityPage.tsx  # Interactive Cytoscape DAG (Req -> Rule -> Test)
│   │       └── ReportsPage.tsx       # Markdown & PDF compliance report viewer/export
│   ├── nginx.conf           # Production Nginx reverse proxy configuration
│   └── Dockerfile           # Multi-stage Node builder + Nginx production server
├── docker-compose.yml       # Root orchestration linking backend + frontend
├── run_demo.py              # Cross-platform CLI demonstration script
└── README.md                # Platform documentation
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/runs/upload` | Upload PDF specification and create a new verification run |
| `POST` | `/runs/{id}/start` | Start LangGraph verification workflow for a run |
| `POST` | `/runs/demo` | Instant demo run loading `sample_requirements.pdf` in the background |
| `GET` | `/runs` | List all historical verification runs and statuses |
| `GET` | `/runs/{id}` | Get run summary, current pipeline stage, and execution timestamps |
| `GET` | `/runs/{id}/requirements` | Get extracted requirements with ASIL and ambiguity ratings |
| `GET` | `/runs/{id}/rules` | Get formalized Rule 5 ASTs with English back-translations |
| `GET` | `/runs/{id}/conflicts` | Get Z3 SMT detected contradictions and counter-examples |
| `GET` | `/runs/{id}/tests` | Get deterministic boundary, normal, and negative test cases |
| `GET` | `/runs/{id}/results` | Get virtual ECU execution results and timing metrics |
| `GET` | `/runs/{id}/failures` | Get failed tests requiring root-cause analysis |
| `GET` | `/runs/{id}/fixes` | Get proposed ECU code patches and mutation verification scores |
| `GET` | `/runs/{id}/traceability` | Cytoscape graph nodes and edges (`Req -> Rule -> Test -> Result`) |
| `GET` | `/runs/{id}/report` | Get Markdown and download links for the verification report |
| `GET` | `/runs/{id}/events` | Real-time SSE stream of agent reasoning thoughts, tools, and results |
| `GET` | `/approvals/pending` | List pending human engineering approval items |
| `POST` | `/approvals/{id}/approve` | Approve a formalized rule (resumes LangGraph interrupt) |
| `POST` | `/approvals/{id}/reject` | Reject a rule with engineering feedback reason |
| `GET` | `/dashboard/stats` | Global metrics (total requirements, tests, pass rate, active runs) |
| `GET` | `/health` | Service health status check |

---

## 🛡️ Core Engineering Rules Followed

1. **Rule 3 (Centrally Defined Model)**: LLM model name (`gemini-2.5-flash`) lives exclusively in `backend/app/config.py`.
2. **Rule 4 (Deterministic Expected Values)**: Test generator computes all expected outputs using plain code logic from the formalized rules, never via LLM hallucination.
3. **Rule 5 (Fixed Pydantic Schema)**: Every rule complies with `{id, text, condition:{var,op,value}, action:{var,op,value}}`.
4. **Rule 7 (Agent Bounded Loops)**: Max 3 repair attempts and max 8 tool calls per attempt.
5. **Rule 8 (Audited Decisions)**: Every agent decision, thought, and tool execution is persisted in the `agent_log` SQLite table.
6. **Rule 9 (ASIL Safety Gate)**: ASIL C and D requirements and high-risk changes require human sign-off before entering formal verification and deployment.
7. **Rule 10 (Immutable Versioning)**: ECU code files are strictly never overwritten; repairs create explicit new versions (`v1_fixed_xxx.py`) with full regression testing.
