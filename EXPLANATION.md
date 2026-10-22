# SafeSpec: Complete Engineering & Architecture Explanation

> **Comprehensive Guide for Project Understanding, System Architecture, and Technical Interview Preparation**

---

## 📑 Table of Contents
1. [Executive Summary ("Basically, What is SafeSpec?")](#1-executive-summary-basically-what-is-safespec)
2. [The Automotive Problem It Solves](#2-the-automotive-problem-it-solves)
3. [End-to-End System Workflow (Step-by-Step)](#3-end-to-end-system-workflow-step-by-step)
4. [Deep Dive: The 3 ECU Selectors on the Upload Page](#4-deep-dive-the-3-ecu-selectors-on-the-upload-page)
5. [Core Technologies & Libraries Used](#5-core-technologies--libraries-used)
6. [Complete Feature Matrix](#6-complete-feature-matrix)
7. [Interview Demo Script & Common Questions](#7-interview-demo-script--common-questions)

---

## 1. Executive Summary ("Basically, What is SafeSpec?")

### In Simple English:
**Basically**, automotive companies (like Tesla, BMW, or Ford) write vehicle safety rules in 300-page English PDF documents (e.g., *"Lock doors when the car moves"*, *"Turn on high beams at night unless another car is coming"*). 

Because these requirements are written by humans in natural language:
1. They often contain **vague words** like *"the car should react quickly"* (how many milliseconds is "quickly"?).
2. They often contain **hidden contradictions** (one engineer writes *"turn high beams on above 30 km/h"*, and another writes *"only enable high beam assist above 40 km/h"*—so what happens at 35 km/h?).
3. Engineers spend months writing manual tests and running them on physical test benches.

**SafeSpec** is an autonomous AI & formal verification system that:
- Reads the PDF specification.
- Audits the text for vague or unsafe wording under **ISO 26262**.
- Converts the English text into strict **mathematical formulas** (ASTs).
- Uses the **Microsoft Z3 SMT Solver** to mathematically **prove** whether any rules contradict each other before a single line of code is written.
- Creates test cases (boundary values, dropped signals) and tests a **Virtual Electronic Control Unit (ECU)** running over a simulated **CAN bus**.
- If a bug is detected in the ECU firmware, an **Autonomous AI Agent diagnoses the root cause, rewrites the code to fix the bug, and re-tests it until 100% pass rate is achieved**.

---

### In Formal Technical Terms:
> **SafeSpec** is an autonomous verification and validation (V&V) platform for safety-critical automotive embedded systems conforming to **ISO 26262 ASIL D** and **AUTOSAR** standards. It integrates **LangGraph** multi-agent state machines, **Google Gemini** structured reasoning, **Microsoft Z3 SMT theorem proving**, deterministic boundary-value CAN test synthesis, and software-in-the-loop (SIL) **Virtual CAN Bus ECU simulation** with autonomous root-cause diagnosis and self-healing firmware repair.

---

## 2. The Automotive Problem It Solves

| Traditional Automotive Verification | SafeSpec Autonomous Verification |
| :--- | :--- |
| **Ambiguous Requirements**: Human engineers use words like *"smoothly"* or *"quickly"*, leading to flawed firmware. | **Automated ISO 26262 Audit**: Extractor scores ambiguity (`LOW`, `MED`, `HIGH`) and flags missing millisecond thresholds. |
| **Undetected Contradictions**: Cross-document rule conflicts are discovered late during physical track testing. | **Mathematical Proof (Z3 SMT)**: Proves contradictions in milliseconds with concrete counter-example telemetry. |
| **Manual Test Writing**: Test engineers manually author test vectors for Hardware-In-The-Loop (HIL) rigs. | **Deterministic Boundary Generation**: Plain Python code deterministically generates $v - 0.1, v, v + 0.1$ and fault-injection vectors. |
| **Manual Bug Hunting**: When an ECU fails a test, software engineers spend days analyzing CAN trace logs. | **Autonomous Self-Healing (RCA Agent)**: Agent isolates the faulty line of code, generates an immutable patch (`v1` $\to$ `v2`), and verifies regression. |

---

## 3. End-to-End System Workflow (Step-by-Step)

```
[ 1. PDF Upload ] 
       │
       ▼
[ 2. Extractor Agent ] ──> ISO 26262 Ambiguity Audit & Quality Flags (e.g., flags "quickly")
       │
       ▼
[ 3. Formalizer Agent ] ──> Converts text to Rule 5 AST {condition, action} + Plain English Back-Translation
       │
       ▼
[ 4. Safety Gate (R9) ] ──> ASIL C/D High Risk Sign-Off (Human-in-the-loop review)
       │
       ▼
[ 5. Z3 SMT Solver ] ───> Proves mathematical contradictions & outputs counter-examples (e.g. 31 km/h)
       │
       ▼
[ 6. Deterministic CAN Tests ] ──> Generates boundary ($v\pm 0.1$) & fault-injection tests
       │
       ▼
[ 7. Virtual ECU Simulation ] ──> Executes tests over Virtual CAN Bus (python-can)
       │
       ├─── IF PASSED ───> [ 9. Compliance Report ] (Markdown & PDF Audit Trail)
       │
       └─── IF FAILED ───> [ 8. Root-Cause Agent ] ──> Diagnoses bug, patches ECU v1 ➔ v2, re-runs tests
```

### Stage 1: PDF Document Ingestion & Extractor Agent
- **File**: [`backend/app/parsers/pdf_parser.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/parsers/pdf_parser.py), [`backend/app/agents/extractor.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/extractor.py)
- **Library**: `pymupdf` (native C-speed PDF extraction) + Gemini.
- **What it does**: Reads the pages of the automotive specification. The Extractor extracts individual requirement statements and runs an **ISO 26262 quality audit**:
  - Scores semantic ambiguity: `LOW`, `MEDIUM`, or `HIGH`.
  - Flags vague, untestable engineering words (such as *"quickly"*, *"smoothly"*, *"appropriate"*).
  - Identifies associated ASIL ratings (QM, A, B, C, D) and regulatory clauses (e.g., UNECE R48).

### Stage 2: Rule 5 Formalizer Agent
- **File**: [`backend/app/agents/formalizer.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/formalizer.py)
- **What it does**: Converts natural language into a strict, machine-checkable **Abstract Syntax Tree (AST)**:
  $$\text{Rule} = \{ \text{id}, \text{text}, \text{condition}: \{\text{var}, \text{op}, \text{value}\}, \text{action}: \{\text{var}, \text{op}, \text{value}\} \}$$
- **Canonical Variables Whitelist**: Enforces strict domain variables (`speed`, `oncoming_distance`, `lux`, `door`, `beam`, `pressure_bar`) so the LLM cannot hallucinate imaginary signals.
- **Bi-directional Back-Translation**: Automatically translates the mathematical AST back into clear, unambiguous English so safety certifiers can verify what was formalized.

### Stage 3: Human Safety Gate (Rule 9)
- **File**: [`backend/app/safety/approval.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/safety/approval.py), [`backend/app/workflows/safespec_graph.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/workflows/safespec_graph.py)
- **What it does**: Under ISO 26262, high-risk systems (**ASIL C and ASIL D**) cannot be modified or tested without certified human sign-off. SafeSpec implements a LangGraph `interrupt()` that halts execution until an engineer clicks "Approve".

### Stage 4: Formal Verification with Microsoft Z3 SMT Solver
- **File**: [`backend/app/formal/z3_checker.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/formal/z3_checker.py)
- **Library**: `z3-solver` (Satisfiability Modulo Theories solver).
- **What it does**: Instead of guessing with an LLM, SafeSpec translates the rules into **First-Order Mathematical Logic**:
  - Formulates satisfiability queries: $\text{Condition}_A \land \text{Condition}_B \land (\text{Action}_A \neq \text{Action}_B)$.
  - If satisfiable, Z3 **proves** a contradiction exists and synthesizes an exact **counter-example assignment** (e.g., $\text{speed} = 31.0\text{ km/h}$).

### Stage 5: Deterministic CAN Test Generation
- **File**: [`backend/app/testing/test_generator.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/testing/test_generator.py)
- **What it does**: Automatically creates executable test vectors:
  - **Boundary Tests**: If threshold is $20.0\text{ km/h}$, generates inputs at $19.9\text{ km/h}$, $20.0\text{ km/h}$, and $20.1\text{ km/h}$.
  - **Normal Operation Tests**: Nominal cruising speeds (e.g., $50\text{ km/h}$).
  - **Negative / Fault Injection Tests**: Simulates sensor failure flags and dropped CAN telemetry frames.
  - **Deterministic Derivation**: Expected outputs are derived strictly using Python logic—not an LLM.

### Stage 6: Virtual ECU Simulation on Virtual CAN Bus
- **File**: [`backend/app/simulation/can_bus.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/simulation/can_bus.py), [`backend/app/ecu/virtual_ecu.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/ecu/virtual_ecu.py)
- **Library**: `python-can`
- **What it does**: Simulates an actual in-vehicle network:
  - Encodes telemetry into real **8-byte CAN frames** with standard arbitration IDs (`CAN_ID_SPEED = 0x1F0`, `CAN_ID_BRAKE = 0x200`, `CAN_ID_DOOR_CMD = 0x3A0`).
  - Broadcasts frames over a virtual CAN channel.
  - The `VirtualECU` listens to the bus, parses the frames, runs its control logic, and drives simulated physical actuators (`DoorLockActuator`, `BrakeActuator`).

### Stage 7: Autonomous Root-Cause Diagnosis & Self-Healing Repair
- **File**: [`backend/app/agents/root_cause.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/root_cause.py)
- **What it does**: If any test fails:
  1. Searches vector memory for similar past failure patterns.
  2. Formulates 2–3 candidate hypotheses for the failure.
  3. Uses tools (`read_ecu_code`, `inject_fault`, `run_single_test`) to isolate the root cause.
  4. Generates an **immutable new ECU version** (e.g., creates `ecu_v2.py` without overwriting historical files).
  5. Executes a full regression test suite and mutation analysis to prove the patch didn't introduce new bugs.

### Stage 8: Executive Verification & Audit Report
- **File**: [`backend/app/reports/report_generator.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/reports/report_generator.py)
- **What it does**: Compiles all extraction scores, Z3 mathematical proofs, CAN test telemetry, and repair diffs into an ISO 26262 sign-off report in Markdown and PDF.

---

## 4. Deep Dive: The 3 ECU Selectors on the Upload Page

On the frontend **Upload Page**, you will find the **"Target Virtual ECU Firmware Logic"** selector:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Target Virtual ECU Firmware Logic:                                     │
│ [ v1 (Nominal baseline: speed > 20 km/h locks door)                 ▼] │
│   - v1 (Nominal baseline: speed > 20 km/h locks door)                  │
│   - v1_buggy_threshold (Buggy threshold: 80 km/h)                      │
│   - v1_buggy_timeout (Buggy timeout: drops CAN telemetry)              │
└────────────────────────────────────────────────────────────────────────┘
```

### What is an ECU?
An **ECU (Electronic Control Unit)** is an embedded automotive computer (like the microcontroller inside a car door, brake module, or engine). In SafeSpec, we simulate this microcontroller in software.

Here is what each of the 3 selectors represents:

---

### Selector 1: `v1` (The Correct Baseline Controller)
- **Code**: [`backend/app/ecu/versions/v1.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/ecu/versions/v1.py)
- **Behavior**:
  ```python
  def evaluate(speed: float, is_lost: bool = False) -> str:
      if is_lost or speed > 20.0:
          return "LOCKED"
      return "UNLOCKED"
  ```
- **What happens when selected**:
  - The virtual ECU correctly locks doors whenever speed exceeds $20.0\text{ km/h}$.
  - If the speed sensor drops out (`is_lost = True`), it enters the safe state (`LOCKED`).
  - **Result in Demo**: **100% of test cases pass immediately.** Use this when you want to show a clean, green, passing baseline run to your interviewer.

---

### Selector 2: `v1_buggy_threshold` (The Threshold Bug — Showcases Self-Healing)
- **Code**: [`backend/app/ecu/versions/v1_buggy_threshold.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/ecu/versions/v1_buggy_threshold.py)
- **Behavior**:
  ```python
  def evaluate(speed: float, is_lost: bool = False) -> str:
      if speed > 80.0:  # <--- BUG! Configured to 80 km/h instead of 20 km/h!
          return "LOCKED"
      return "UNLOCKED"
  ```
- **What happens when selected**:
  - A test case inputs $20.1\text{ km/h}$. The specification expects `LOCKED`, but the ECU outputs `UNLOCKED`.
  - The test **FAILS**.
  - SafeSpec routes execution to the **Root Cause Analysis Agent**.
  - The AI agent inspects the Python code, diagnoses that the threshold was mistakenly hardcoded to `80.0`, writes a patch setting it to `20.0`, saves it as an immutable new version (`v2`), and re-runs the test suite until **100% PASS** is achieved.
  - **Result in Demo**: **This is the highest-impact demo feature.** It proves that SafeSpec does not just detect bugs—it autonomously diagnoses and repairs embedded software.

---

### Selector 3: `v1_buggy_timeout` (The Safety Fail-Safe Bug)
- **Code**: [`backend/app/ecu/versions/v1_buggy_timeout.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/ecu/versions/v1_buggy_timeout.py)
- **Behavior**:
  ```python
  def evaluate(speed: float, is_lost: bool = True) -> str:
      if is_lost:
          return "UNLOCKED"  # <--- DANGEROUS BUG! Leaves door unlocked when sensor dies!
      if speed > 20.0:
          return "LOCKED"
      return "UNLOCKED"
  ```
- **What happens when selected**:
  - Simulates a critical **ISO 26262 Part 5 Hardware Fault Injection**: what happens if the wheel speed sensor cable is severed while driving?
  - The safe state is `LOCKED`. However, this buggy firmware leaves the doors `UNLOCKED`.
  - SafeSpec's negative fault-injection test catches the safety violation immediately and triggers diagnosis.

---

## 5. Core Technologies & Libraries Used

### Backend Stack
| Technology / Library | Purpose in SafeSpec | Why It Was Chosen |
| :--- | :--- | :--- |
| **Python 3.12+** | Core backend language | Native support for modern typing, async, and scientific libraries. |
| **FastAPI** | REST API engine | Asynchronous high-throughput API with automatic interactive OpenAPI docs (`/docs`). |
| **LangGraph** | Multi-agent state orchestration | Stateful graph workflow with SQLite persistence and human-in-the-loop pause/resume (`interrupt`). |
| **Microsoft Z3 SMT (`z3-solver`)** | Formal mathematical verification | Unlike LLMs, Z3 never hallucinates. It provides 100% mathematical certainty when proving rule contradictions. |
| **python-can** | Automotive CAN bus simulation | Industry-standard library for CAN protocol handling, arbitration IDs, and binary frame packing. |
| **PyMuPDF (`fitz`)** | PDF document parsing | Native C-level PDF parsing capable of extracting tables, text, and structure with high fidelity. |
| **Pydantic v2** | Data modeling & AST schemas | Fast C-based validation enforcing the Rule 5 format `{condition, action}` across the platform. |
| **SQLAlchemy + SQLite** | Database & audit logging | Persists every agent thought, tool call, and state transition to guarantee a complete ISO 26262 audit trail. |
| **Google Gemini (`google-genai`)** | Reasoning engine | Powers the Extractor, Formalizer, and Root-Cause hypothesis agents with high-speed structured JSON generation. |

### Frontend Stack
| Technology / Library | Purpose in SafeSpec | Why It Was Chosen |
| :--- | :--- | :--- |
| **React 19** | Component UI framework | Modern reactive user interface. |
| **TypeScript 5.7+** | Type-safe frontend logic | Matches Pydantic backend schemas with frontend TypeScript interfaces. |
| **Vite** | Build tool and dev server | Sub-second Hot Module Replacement (HMR) and fast production builds. |
| **Tailwind CSS v4** | UI design & styling | High-contrast dark-mode theme tailored for automotive mission-control dashboards. |
| **Lucide React** | Icons | Clean, modern iconography for verification stages, CAN buses, and safety alerts. |
| **TanStack React Query** | Server state management | Seamless polling and real-time synchronization with background LangGraph pipeline runs. |

---

## 6. Complete Feature Matrix

| Feature | Description | File Reference |
| :--- | :--- | :--- |
| **Automated PDF Parsing** | Extracts raw requirements and tables from automotive specs. | [`pdf_parser.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/parsers/pdf_parser.py) |
| **ISO 26262 Quality Audit** | Identifies vague terms (*"quickly"*) and scores ambiguity (`LOW`, `MED`, `HIGH`). | [`extractor.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/extractor.py) |
| **Rule 5 AST Formalization** | Normalizes natural language to `{condition: {var, op, val}, action: {var, op, val}}`. | [`formalizer.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/formalizer.py) |
| **English Back-Translation** | Generates plain-English descriptions directly from formalized ASTs. | [`formalizer.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/formalizer.py) |
| **Z3 Contradiction Prover** | Finds overlapping conditions commanding contradictory actions. | [`z3_checker.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/formal/z3_checker.py) |
| **Counter-Example Synthesis** | Outputs exact numerical values proving where two rules conflict (e.g. 31 km/h). | [`z3_checker.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/formal/z3_checker.py) |
| **Deterministic CAN Test Gen** | Generates boundary ($v\pm 0.1$) and fault injection test vectors without LLM guesswork. | [`test_generator.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/testing/test_generator.py) |
| **Virtual CAN Simulation** | Encodes binary CAN frames and transmits them across virtual channels. | [`can_bus.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/simulation/can_bus.py) |
| **Virtual ECU Runtime** | Dynamic firmware loader driving door lock and brake actuators. | [`virtual_ecu.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/ecu/virtual_ecu.py) |
| **Root-Cause Analysis Agent** | Formulates hypotheses, executes experiments, and isolates bugs. | [`root_cause.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/root_cause.py) |
| **Immutable Patch Synthesis** | Writes versioned firmware patches (`ecu_v2.py`) and runs mutation testing. | [`root_cause.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/agents/root_cause.py) |
| **ASIL C/D Safety Gate** | Pauses workflow for required human engineering sign-off on safety-critical items. | [`safespec_graph.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/workflows/safespec_graph.py) |
| **Audit Trail Database** | Logs every agent thought, tool execution, and state checkpoint to SQLite. | [`audit_logger.py`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/backend/app/services/audit_logger.py) |
| **Interactive Web UI** | Real-time DAG workflow visualization, test execution charts, and diff viewer. | [`frontend/src`](file:///c:/Users/sahil/Projects/Signature%20Projects/SafeSpec/frontend/src) |

---

## 7. Interview Demo Script & Common Questions

### 30-Second Elevator Pitch
> *"SafeSpec is an autonomous verification platform for automotive safety systems. It reads requirement specifications from PDFs, audits them for ISO 26262 compliance, formalizes them into mathematical ASTs, and uses the Microsoft Z3 SMT theorem prover to detect logical contradictions before code is written. It then synthesizes CAN bus test vectors, runs them against a virtual ECU over a simulated CAN network, and autonomously diagnoses and patches firmware bugs if any test fails."*

---

### Recommended 3-Minute Live Interview Demonstration

1. **Step 1: Go to the Upload Page** ([http://localhost:5173/upload](http://localhost:5173/upload)).
2. **Step 2: Click "Use Sample Spec PDF"** (Loads `sample_requirements.pdf`).
3. **Step 3: Point out the settings**:
   - Explain to the interviewer: *"We are targeting the Door Control ECU (`REQ-050`). Notice the firmware selector: we can select `v1` for a clean pass, or `v1_buggy_threshold` to demonstrate autonomous self-healing."*
   - Choose **`v1`** (or `v1_buggy_threshold` if you want to show code patching).
4. **Step 4: Click "Launch SafeSpec Verification Pipeline"**:
   - **Show the Extractor**: Point out `REQ-023` flagged for using the unmeasurable word *"quickly"*.
   - **Show the Formalizer**: Show the conversion to `IF speed > 20.0 THEN door = LOCKED` and the English back-translation.
   - **Show the Z3 SMT Prover**: Point to the detected conflict between `REQ-017` (High beam above 30 km/h) and `REQ-031` (High beam only above 40 km/h), highlighting the mathematical counter-example at `31.0 km/h`.
   - **Show the Simulation & Tests**: Show the boundary tests ($19.9, 20.0, 20.1\text{ km/h}$) running over the Virtual CAN bus.

---

### Top 5 Interview Questions & How to Answer Them

#### Q1: "Why did you use Microsoft Z3 SMT instead of just asking an LLM if the rules contradict?"
> **Answer**: *"LLMs are probabilistic and suffer from hallucinations, non-determinism, and reasoning degradation on complex boundary mathematics. In automotive safety (ISO 26262 ASIL D), you cannot rely on probabilities. Z3 is an SMT theorem prover based on formal mathematical logic. When Z3 says UNSAT, it is a 100% mathematical guarantee that no contradiction exists in the state space. When it says SAT, it produces an exact, undeniable counter-example value."*

#### Q2: "How does the CAN bus simulation work without physical automotive hardware?"
> **Answer**: *"We use the `python-can` library running over virtual sockets. We implement the standard automotive CAN protocol, packaging vehicle speed and sensor telemetry into 8-byte binary payloads with standard 11-bit arbitration IDs (`0x1F0` for Speed, `0x200` for Brake, `0x3A0` for Door Lock). The Virtual ECU reads directly from this virtual bus, decodes the struct bytes, processes the logic, and commands the simulated actuators."*

#### Q3: "What prevents the autonomous coding agent from breaking existing code when it fixes a bug?"
> **Answer**: *"Three safety mechanisms: First, the agent never overwrites existing code—it produces an immutable new version (`v1` $\to$ `v2`). Second, after generating the patch, plain code runs a full regression test suite covering all historical requirements. Third, we run mutation testing to verify test suite quality. If any regression fails, SafeSpec automatically rolls back to the previous version."*

#### Q4: "Why were some requirements marked 'not_formalizable' on certain PDFs?"
> **Answer**: *"SafeSpec adheres to strict safety boundaries. If a requirement relies on temporal delay loops ('wait for 2 seconds'), multi-action compound triggers, or signals outside the registered canonical dictionary (like camera lens dirtiness or driver eye closure), the Formalizer deliberately refuses to invent unverified variables. It marks them `not_formalizable` with an explanation so human safety engineers can review them."*

#### Q5: "How does SafeSpec enforce ISO 26262 compliance?"
> **Answer**: *"Through three primary rules: Rule 4 mandates that all expected test outcomes are derived deterministically from plain Python code, not generative AI. Rule 9 mandates an approval gate using LangGraph interrupts for any high-risk ASIL C or D modifications. Rule 8 mandates that every agent thought, supervisor transition, and tool call is permanently recorded in an immutable SQLite audit log."*
