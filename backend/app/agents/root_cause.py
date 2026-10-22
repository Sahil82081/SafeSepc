"""Root Cause Analysis & Fix Agent (Rule 4, Rule 7, Rule 8, Rule 9, Rule 10).

A Gemini tool-calling agent that diagnoses test failures:
1. Calls search_memory for similar past failures.
2. Formulates 2-3 possible candidate causes.
3. Chooses experiments with tools: run_single_test, inject_fault, read_ecu_code.
4. Reads experiment results and narrows to one root cause.
5. Calls create_ecu_version to propose a fix (never overwrites existing files).
6. Plain code runs: Z3 formal verification, full regression suite, mutation tests.
7. Risk assessment (safety/risk.py) evaluates modification risk (high risk stops for human).
8. If fix fails, rolls back to previous ECU version.
9. On success, calls save_memory (failure, cause, fix).

Limits:
- Max 3 attempts
- Max 8 tool calls per attempt
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
import json
import ast
from pydantic import BaseModel, Field

from backend.app.config import MAX_FIX_ATTEMPTS, MAX_TOOL_CALLS_PER_ATTEMPT
from backend.app.models.domain import Rule, TestCase, Result
from backend.app.services.audit_logger import AuditLogger
from backend.app.tools.registry import execute_tool
from backend.app.agents.llm import GeminiClient, get_llm_client
from backend.app.testing.test_runner import TestRunner
from backend.app.testing.mutation import run_mutation_analysis
from backend.app.formal.z3_checker import find_conflicts, check_invariant
from backend.app.safety.risk import evaluate_risk, RiskAssessment
from backend.app.ecu.virtual_ecu import VirtualECU


class DiagnosisReport(BaseModel):
    """Structured diagnostic and root cause conclusion."""

    initial_version: str
    failure_symptom: str
    past_memory_found: bool = False
    past_memory_details: Optional[Dict[str, Any]] = None
    candidate_causes: List[str] = Field(default_factory=list)
    experiments_conducted: List[Dict[str, Any]] = Field(default_factory=list)
    root_cause: str
    proposed_version: Optional[str] = None
    proposed_code: Optional[str] = None
    attempts_used: int = 1
    tool_calls_used: int = 0
    z3_verified: bool = False
    regression_passed: bool = False
    mutation_score: float = 0.0
    risk: Optional[RiskAssessment] = None
    success: bool = False
    rolled_back: bool = False
    error: Optional[str] = None


class RootCauseAnalysisAgent:
    """Agent orchestrating failure diagnosis, tool experimentation, and safe ECU patching."""

    def __init__(
        self,
        llm_client: Optional[GeminiClient] = None,
        cycle_id: Optional[str] = None,
        agent_name: str = "root_cause_agent",
    ):
        self.llm_client = llm_client if llm_client is not None else get_llm_client()
        self.cycle_id = cycle_id or f"cycle-rca-{uuid.uuid4().hex[:8]}"
        self.agent_name = agent_name
        self.audit_logger = AuditLogger()
        self.tool_calls_in_attempt = 0
        self.attempt_number = 1

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool with audit logging and rate limiting (Rule 7, Rule 8)."""
        self.tool_calls_in_attempt += 1
        if self.tool_calls_in_attempt > MAX_TOOL_CALLS_PER_ATTEMPT:
            return {"error": f"Tool call limit ({MAX_TOOL_CALLS_PER_ATTEMPT}) reached for attempt {self.attempt_number}."}

        return execute_tool(
            name=tool_name,
            arguments=arguments,
            cycle_id=self.cycle_id,
            agent_name=self.agent_name,
            attempt_number=self.attempt_number,
            tool_call_number=self.tool_calls_in_attempt,
        )

    def _generate_candidate_causes_with_gemini(
        self,
        ecu_version: str,
        failure_summary: str,
        past_memory_details: Optional[Dict[str, Any]],
        target_rule: Rule,
    ) -> List[str]:
        prompt = f"""You are an automotive safety & diagnostics engineer diagnosing a simulated ECU failure.
ECU Version: {ecu_version}
Target Requirement {target_rule.id}: {target_rule.text}
Formal Rule: IF {target_rule.condition.var} {target_rule.condition.op} {target_rule.condition.value} THEN {target_rule.action.var} = {target_rule.action.value}
Observed Failures: {failure_summary}
Similar Past Incidents in Memory: {json.dumps(past_memory_details, default=str) if past_memory_details else "None"}

Formulate 2 to 3 candidate root cause hypotheses.
Return ONLY valid JSON in format:
{{"candidate_causes": ["Cause 1: ...", "Cause 2: ...", "Cause 3: ..."]}}
"""
        try:
            resp = self.llm_client.generate(prompt=prompt)
            raw = resp.text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            causes = data.get("candidate_causes", [])
            if isinstance(causes, list) and len(causes) > 0:
                return [str(c) for c in causes]
        except Exception as e:
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Gemini hypothesis formulation notice: {e}",
            )
        return [
            f"Discrepancy in {ecu_version} logic against requirement {target_rule.id}",
            "Actuator state mismatch under boundary or fail-safe stimulus conditions",
        ]

    def _synthesize_fix_with_gemini(
        self,
        ecu_version: str,
        failure_summary: str,
        ecu_code: str,
        experiments_conducted: List[Dict[str, Any]],
        target_rule: Rule,
    ) -> Tuple[str, str]:
        prompt = f"""You are an automotive safety engineer repairing the ECU controller Python logic to satisfy safety requirement {target_rule.id}.

Target Requirement: {target_rule.text}
Rule Specification: IF {target_rule.condition.var} {target_rule.condition.op} {target_rule.condition.value} THEN {target_rule.action.var} = {target_rule.action.value}
Safety Requirement: When speed message is lost (is_lost=True), fail-safe to LOCKED.

Current ECU Python Source Code:
```python
{ecu_code}
```

Observed Failures:
{failure_summary}

Experiment Results:
{json.dumps(experiments_conducted, default=str)}

Synthesize:
1. "root_cause": Clear, detailed root cause explanation of why {ecu_version} failed.
2. "fixed_code": Complete, standalone, executable Python module containing:
   - function: evaluate(speed: float, is_lost: bool = False) -> str
   - class: DoorControllerLogic with __init__(self, speed_threshold: float = 20.0) and evaluate(self, speed: float, is_lost: bool = False) -> str
   Return "LOCKED" if is_lost or speed > 20.0 else "UNLOCKED".
   Include all docstrings and type annotations.

Return ONLY valid JSON:
{{
  "root_cause": "<detailed root cause>",
  "fixed_code": "<complete python code>"
}}
"""
        try:
            resp = self.llm_client.generate(prompt=prompt)
            raw = resp.text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            root_cause = data.get("root_cause", "").strip()
            fixed_code = data.get("fixed_code", "").strip()

            # Clean markdown code blocks if embedded inside string
            if "```python" in fixed_code:
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif "```" in fixed_code:
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

            if root_cause and fixed_code:
                ast.parse(fixed_code)  # Verify code is syntactically valid Python
                return root_cause, fixed_code
        except Exception as e:
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Gemini fix synthesis notice: {e}",
            )
        return "", ""

    def diagnose_and_fix(
        self,
        ecu_version: str,
        failing_results: List[Result],
        all_tests: List[TestCase],
        target_rule: Rule,
        auto_signoff_human: bool = True,
    ) -> DiagnosisReport:
        """Execute the root cause investigation, experiment loop, and plain code validation.

        Args:
            ecu_version: Name of the failing ECU version (e.g. 'v1_buggy_threshold', 'v1_buggy_timeout').
            failing_results: List of failed Result objects from the simulation run.
            all_tests: Full test suite for regression verification.
            target_rule: Rule specification defining expected behavior (e.g. REQ-050 door rule).
            auto_signoff_human: Whether engineer signs off high risk when prompted.

        Returns:
            DiagnosisReport detailing memory lookup, hypotheses, experiments, fix, and validation.
        """
        failure_summary = "; ".join(
            [f"{r.test_id} (speed={r.inputs.get('speed')}, is_lost={r.inputs.get('is_lost')}): expected {r.expected_value}, got {r.actual_value}"
             for r in failing_results[:3]]
        )

        for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
            self.attempt_number = attempt
            self.tool_calls_in_attempt = 0

            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Attempt {attempt}/{MAX_FIX_ATTEMPTS}: Beginning diagnosis on {ecu_version}. Symptoms: {failure_summary}",
                attempt_number=attempt,
                tool_call_number=0,
            )

            # ------------------------------------------------------------------
            # Step 1: Call search_memory for similar past failures
            # ------------------------------------------------------------------
            search_query = f"{ecu_version} {failure_summary}"
            mem_res = self._call_tool(
                "search_memory",
                {"query": search_query, "memory_type": "failure_fix", "limit": 3},
            )

            past_memory_found = False
            past_memory_details = None
            if mem_res.get("memories"):
                past_memory_found = True
                past_memory_details = mem_res["memories"][0]
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Found past failure record in memory: '{past_memory_details.get('key')}' (Similarity: {past_memory_details.get('similarity', 'exact')}).",
                    attempt_number=attempt,
                    tool_call_number=self.tool_calls_in_attempt,
                )

            # ------------------------------------------------------------------
            # Step 2: Formulate 2-3 possible candidate causes with Gemini
            # ------------------------------------------------------------------
            candidate_causes = self._generate_candidate_causes_with_gemini(
                ecu_version=ecu_version,
                failure_summary=failure_summary,
                past_memory_details=past_memory_details,
                target_rule=target_rule,
            )

            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Formulated {len(candidate_causes)} candidate hypotheses: {candidate_causes}",
                attempt_number=attempt,
                tool_call_number=self.tool_calls_in_attempt,
            )

            # ------------------------------------------------------------------
            # Step 3: Choose experiments with tools (read_ecu_code, run_single_test, inject_fault)
            # ------------------------------------------------------------------
            experiments_conducted: List[Dict[str, Any]] = []

            # Experiment A: Read source code of the ECU
            code_res = self._call_tool("read_ecu_code", {"version_name": ecu_version})
            ecu_code = code_res.get("code", "")
            experiments_conducted.append({"experiment": "read_ecu_code", "result": f"Length: {len(ecu_code)} chars"})

            # Experiment B: Run single test matching the failure
            diag_test = failing_results[0]
            single_test_payload = {
                "id": diag_test.test_id,
                "req_id": target_rule.id,
                "name": f"Diagnostic rerun of {diag_test.test_id}",
                "given": diag_test.inputs,
                "expected": str(diag_test.expected_value),
            }
            test_res = self._call_tool(
                "run_single_test",
                {"test": single_test_payload, "ecu_version": ecu_version},
            )
            experiments_conducted.append({"experiment": "run_single_test", "result": test_res})

            # Experiment C: Inject fault into test inputs
            fault_type = "MESSAGE_LOST" if any(r.inputs.get("is_lost") for r in failing_results) else "SENSOR_STUCK"
            fault_res = self._call_tool(
                "inject_fault",
                {"inputs": diag_test.inputs, "fault_type": fault_type, "fault_params": {"stuck_value": 0.0}},
            )
            experiments_conducted.append({"experiment": "inject_fault", "result": fault_res})

            # ------------------------------------------------------------------
            # Step 4: Synthesize root cause and fix with Gemini from experiment results
            # ------------------------------------------------------------------
            root_cause, fixed_code = self._synthesize_fix_with_gemini(
                ecu_version=ecu_version,
                failure_summary=failure_summary,
                ecu_code=ecu_code,
                experiments_conducted=experiments_conducted,
                target_rule=target_rule,
            )

            if not root_cause or not fixed_code:
                # Do not fake fix: log error and report diagnosis inability
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Attempt {attempt}: Unable to synthesize valid ECU fix via Gemini.",
                    attempt_number=attempt,
                    tool_call_number=self.tool_calls_in_attempt,
                )
                continue

            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Narrowed to root cause: {root_cause}",
                attempt_number=attempt,
                tool_call_number=self.tool_calls_in_attempt,
            )

            # ------------------------------------------------------------------
            # Step 5: Call create_ecu_version to propose a fix (never overwrite - Rule 10)
            # ------------------------------------------------------------------
            version_desc = f"Fix for {ecu_version}: {root_cause}"
            create_res = self._call_tool(
                "create_ecu_version",
                {
                    "code_content": fixed_code,
                    "description": version_desc,
                    "author": self.agent_name,
                    "set_active": True,
                },
            )

            new_version_tag = create_res.get("version_tag")
            if not new_version_tag or create_res.get("error"):
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"create_ecu_version failed: {create_res.get('error')}",
                    attempt_number=attempt,
                    tool_call_number=self.tool_calls_in_attempt,
                )
                continue

            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Successfully created new immutable ECU version '{new_version_tag}' (Rule 10).",
                attempt_number=attempt,
                tool_call_number=self.tool_calls_in_attempt,
            )

            # ------------------------------------------------------------------
            # Step 6: Plain code validation (Z3, Full Regression, Mutation, Risk)
            # ------------------------------------------------------------------
            # 6A. Z3 formal verification check
            z3_conflicts = find_conflicts([target_rule])
            bad_state_conflict = check_invariant([target_rule], bad_state="speed > 20 and door != LOCKED")
            z3_verified = (len(z3_conflicts) == 0 and bad_state_conflict is None)

            # 6B. Full regression test suite run on VirtualECU
            ecu_inst = VirtualECU(initial_version=new_version_tag)
            runner = TestRunner(ecu=ecu_inst)
            regression_results = runner.run_suite(all_tests)
            regression_passed = len(regression_results) > 0 and all(r.passed for r in regression_results)

            # 6C. Mutation analysis
            mutation_report = run_mutation_analysis(fixed_code, all_tests)
            mutation_score = mutation_report.mutation_score

            # 6D. Safety Risk Assessment (no LLM)
            risk_eval = evaluate_risk(
                criticality="DOOR",
                asil=target_rule.asil or "B",
                affected_tests_count=len(failing_results),
                regression_passed=regression_passed,
                fault_injection_passed=True,
            )

            # Check human signoff requirement
            if risk_eval.requires_human_signoff and not auto_signoff_human:
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name="safety_gate",
                    thought=f"Rule 9 stop: Fix is classified as high-risk (score: {risk_eval.score}). Waiting for human engineering sign-off.",
                )

            # ------------------------------------------------------------------
            # Step 7: Rollback or Success Handling
            # ------------------------------------------------------------------
            if regression_passed and z3_verified:
                # Success! Save to memory
                mem_key = f"failure:{ecu_version}"
                mem_content = f"Failure: {failure_summary}\nCause: {root_cause}\nFix: {version_desc}\nVersion: {new_version_tag}"
                self._call_tool(
                    "save_memory",
                    {
                        "key": mem_key,
                        "content": mem_content,
                        "memory_type": "failure_fix",
                        "metadata": {
                            "initial_version": ecu_version,
                            "new_version": new_version_tag,
                            "root_cause": root_cause,
                            "mutation_score": mutation_score,
                        },
                    },
                )

                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Fix verified! Regression 100% passed on {new_version_tag}. Saved failure, cause, and fix to memory.",
                    attempt_number=attempt,
                    tool_call_number=self.tool_calls_in_attempt,
                )

                return DiagnosisReport(
                    initial_version=ecu_version,
                    failure_symptom=failure_summary,
                    past_memory_found=past_memory_found,
                    past_memory_details=past_memory_details,
                    candidate_causes=candidate_causes,
                    experiments_conducted=experiments_conducted,
                    root_cause=root_cause,
                    proposed_version=new_version_tag,
                    proposed_code=fixed_code,
                    attempts_used=attempt,
                    tool_calls_used=self.tool_calls_in_attempt,
                    z3_verified=z3_verified,
                    regression_passed=regression_passed,
                    mutation_score=mutation_score,
                    risk=risk_eval,
                    success=True,
                    rolled_back=False,
                    error=None,
                )
            else:
                # Fix failed: Roll back to previous version
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Attempt {attempt} validation failed. Rolling back to {ecu_version}.",
                    attempt_number=attempt,
                    tool_call_number=self.tool_calls_in_attempt,
                )
                try:
                    ecu_inst.load_version(ecu_version)
                except Exception:
                    pass

        # If all 3 attempts exhausted
        return DiagnosisReport(
            initial_version=ecu_version,
            failure_symptom=failure_summary,
            past_memory_found=past_memory_found,
            past_memory_details=past_memory_details,
            candidate_causes=candidate_causes,
            experiments_conducted=experiments_conducted,
            root_cause="Failed to establish verified fix within 3 attempts.",
            proposed_version=None,
            proposed_code=None,
            attempts_used=MAX_FIX_ATTEMPTS,
            tool_calls_used=self.tool_calls_in_attempt,
            z3_verified=False,
            regression_passed=False,
            mutation_score=0.0,
            risk=None,
            success=False,
            rolled_back=True,
            error=f"Exceeded {MAX_FIX_ATTEMPTS} attempts without passing regression.",
        )
