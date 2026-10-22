"""SafeSpec End-to-End Verification Pipeline (Rule 4, Rule 5, Rule 8, Rule 9).

Connects:
formalizer -> approval -> z3_checker -> test_generator -> test_runner

Flow:
1. Extractor extracts requirements from PDF with quality scoring.
2. Formalizer converts requirements into Rules and English back-translations.
   Vague requirements ('quickly') are marked 'not_formalizable' with reason.
3. Approval gate holds approval records (original text, rule, back-translation, status).
   Strict gate: ONLY approved rules go to Z3 formal verification and test generator.
4. Z3 Formal Verification analyzes approved rules and catches conflicts (e.g. REQ-017 vs REQ-031).
5. Test Generator generates boundary, normal, and negative test cases from approved rule.
   Expected values are computed by plain code, never by LLM.
6. Test Runner executes test cases on VirtualECU and returns structured Result objects.
"""

from typing import List, Dict, Any, Optional, Set
import uuid
from pydantic import BaseModel, Field

from backend.app.models.domain import Requirement, Rule, Conflict, TestCase, Result
from backend.app.agents.extractor import RequirementExtractorAgent
from backend.app.agents.formalizer import RequirementFormalizerAgent, FormalizedRequirement
from backend.app.safety.approval import ApprovalManager, ApprovalRecord, filter_approved_rules, ApprovalGateError
from backend.app.formal.z3_checker import find_conflicts, check_invariant
from backend.app.testing.test_generator import generate_tests
from backend.app.testing.test_runner import TestRunner
from backend.app.ecu.virtual_ecu import VirtualECU
from backend.app.services.audit_logger import AuditLogger


class PipelineResult(BaseModel):
    """Encapsulates end-to-end execution outcomes across all verification stages."""

    cycle_id: str
    requirements: List[Requirement]
    formalized: List[FormalizedRequirement]
    unformalizable: List[FormalizedRequirement]
    approval_records: List[ApprovalRecord]
    approved_rules: List[Rule]
    conflicts: List[Conflict]
    test_cases: List[TestCase]
    test_results: List[Result]
    ecu_version: str

    @property
    def has_conflicts(self) -> bool:
        """True if Z3 solver caught one or more formal conflicts."""
        return len(self.conflicts) > 0

    @property
    def all_tests_passed(self) -> bool:
        """True if all generated simulation tests passed on VirtualECU."""
        return len(self.test_results) > 0 and all(r.passed for r in self.test_results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.test_results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.test_results if not r.passed)


class VerificationPipeline:
    """Orchestrates the complete verification pipeline from PDF to ECU test results."""

    def __init__(
        self,
        cycle_id: Optional[str] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        self.cycle_id = cycle_id or f"cycle-pipe-{uuid.uuid4().hex[:8]}"
        self.approval_manager = approval_manager or ApprovalManager()
        self.audit_logger = AuditLogger()

    def run(
        self,
        pdf_path: str,
        approve_all_formalized: bool = True,
        approved_req_ids: Optional[Set[str]] = None,
        target_test_req_id: str = "REQ-050",
        ecu_version: str = "v1",
    ) -> PipelineResult:
        """Execute the end-to-end pipeline.

        Args:
            pdf_path: Path to specification PDF.
            approve_all_formalized: If True, engineer sign-off approves all valid formalized rules.
            approved_req_ids: Optional explicit set of requirement IDs to approve.
            target_test_req_id: Requirement ID to generate and run simulation tests for (e.g. REQ-050).
            ecu_version: Virtual ECU version ('v1', 'v1_buggy_threshold', 'v1_buggy_timeout').

        Returns:
            PipelineResult with requirements, formalized rules, approvals, Z3 conflicts, and ECU test results.
        """
        self.audit_logger.log_thought(
            cycle_id=self.cycle_id,
            agent_name="orchestrator",
            thought=f"Initiating end-to-end verification pipeline on {pdf_path} (ECU version: {ecu_version}).",
        )

        # ---------------------------------------------------------
        # Step 1: Extractor Agent
        # ---------------------------------------------------------
        extractor = RequirementExtractorAgent(cycle_id=self.cycle_id)
        requirements = extractor.extract(pdf_path)

        # ---------------------------------------------------------
        # Step 2: Formalizer Agent
        # ---------------------------------------------------------
        formalizer = RequirementFormalizerAgent(cycle_id=self.cycle_id)
        formalized_list = formalizer.formalize_all(requirements)

        unformalizable = [f for f in formalized_list if f.status == "not_formalizable"]

        # ---------------------------------------------------------
        # Step 3: Safety Approval Gate (Rule 9)
        # ---------------------------------------------------------
        approval_records: List[ApprovalRecord] = []
        for form_item in formalized_list:
            rec = self.approval_manager.create_from_formalized(form_item)
            approval_records.append(rec)

        # Apply approval decisions
        for rec in approval_records:
            if rec.rule is not None:
                should_approve = False
                if approved_req_ids is not None:
                    should_approve = rec.req_id in approved_req_ids
                elif approve_all_formalized:
                    should_approve = True

                if should_approve:
                    self.approval_manager.approve(
                        record_id=rec.id,
                        note=f"Approved formalization for {rec.req_id} ({rec.asil_level}).",
                        decided_by="safety_engineer",
                    )

        # RULE GATE: Only approved rules go to Z3 and test generator
        approved_rules = self.approval_manager.get_approved_rules()

        self.audit_logger.log_thought(
            cycle_id=self.cycle_id,
            agent_name="safety_gate",
            thought=f"Approval gate passed {len(approved_rules)} approved rules to formal verification and testing.",
        )

        # ---------------------------------------------------------
        # Step 4: Z3 Formal Verification
        # ---------------------------------------------------------
        conflicts = find_conflicts(approved_rules)

        if conflicts:
            conflict_descriptions = [f"{c.rule_a_id} vs {c.rule_b_id}: {c.description}" for c in conflicts]
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name="z3_checker",
                thought=f"Z3 solver detected {len(conflicts)} formal conflict(s): {conflict_descriptions}",
            )

        # ---------------------------------------------------------
        # Step 5: Deterministic Test Case Generator (Rule 4)
        # ---------------------------------------------------------
        target_rule = next((r for r in approved_rules if r.id == target_test_req_id), None)
        test_cases: List[TestCase] = []

        if target_rule is not None:
            test_cases = generate_tests(target_rule)
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name="test_generator",
                thought=f"Generated {len(test_cases)} deterministic test cases for {target_test_req_id}.",
            )
        else:
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name="test_generator",
                thought=f"Target requirement {target_test_req_id} was not among approved rules; skipped test generation.",
            )

        # ---------------------------------------------------------
        # Step 6: Test Suite Runner on VirtualECU
        # ---------------------------------------------------------
        test_results: List[Result] = []
        if test_cases:
            ecu = VirtualECU(version=ecu_version)
            runner = TestRunner(ecu=ecu)
            test_results = runner.run_suite(test_cases)
            pass_num = sum(1 for r in test_results if r.passed)
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name="test_runner",
                thought=f"Executed {len(test_results)} test cases on ECU {ecu_version}: {pass_num}/{len(test_results)} PASSED.",
            )

        return PipelineResult(
            cycle_id=self.cycle_id,
            requirements=requirements,
            formalized=formalized_list,
            unformalizable=unformalizable,
            approval_records=approval_records,
            approved_rules=approved_rules,
            conflicts=conflicts,
            test_cases=test_cases,
            test_results=test_results,
            ecu_version=ecu_version,
        )


def run_pipeline(
    pdf_path: str,
    approve_all_formalized: bool = True,
    approved_req_ids: Optional[Set[str]] = None,
    target_test_req_id: str = "REQ-050",
    ecu_version: str = "v1",
    cycle_id: Optional[str] = None,
) -> PipelineResult:
    """Convenience helper to run the verification pipeline."""
    pipe = VerificationPipeline(cycle_id=cycle_id)
    return pipe.run(
        pdf_path=pdf_path,
        approve_all_formalized=approve_all_formalized,
        approved_req_ids=approved_req_ids,
        target_test_req_id=target_test_req_id,
        ecu_version=ecu_version,
    )
