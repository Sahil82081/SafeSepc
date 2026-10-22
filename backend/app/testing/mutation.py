"""Mutation Testing Engine for ECU Control Logic.

Generates syntactic and semantic mutations of ECU control files:
- Relational operator mutation (> to >=, < to <=, > to <)
- Numeric threshold mutation (e.g. 20.0 -> 30.0, 20.0 -> 10.0)
- Return state inversion ("LOCKED" <-> "UNLOCKED")
- Logical condition mutation (or <-> and)

Executes test suites against each mutant to verify if tests detect regressions (Killed vs Survived).
"""

from typing import List, Dict, Any, Callable
import ast
import types
from pydantic import BaseModel, Field

from backend.app.models.domain import TestCase
from backend.app.testing.test_runner import TestRunner
from backend.app.ecu.virtual_ecu import VirtualECU


class MutantResult(BaseModel):
    """Result of running tests against an individual mutant."""

    mutant_id: str
    description: str
    mutated_code: str
    killed: bool
    failing_test_ids: List[str] = Field(default_factory=list)


class MutationReport(BaseModel):
    """Summary of mutation testing run."""

    total_mutants: int
    killed_count: int
    survived_count: int
    mutation_score: float  # Percentage of killed mutants
    mutants: List[MutantResult] = Field(default_factory=list)


class EcuMutator:
    """Generates mutations for automotive ECU logic."""

    @staticmethod
    def generate_mutations(source_code: str) -> List[Dict[str, str]]:
        """Produce small, targeted code mutations from original source code."""
        mutations: List[Dict[str, str]] = []

        # 1. Invert threshold operator: > to >=
        if "> 20.0" in source_code:
            mutations.append({
                "id": "MUT-OP-GTE",
                "desc": "Operator mutated: > 20.0 changed to >= 20.0",
                "code": source_code.replace("> 20.0", ">= 20.0"),
            })

        # 2. Invert threshold operator: > to <
        if "> 20.0" in source_code:
            mutations.append({
                "id": "MUT-OP-LT",
                "desc": "Operator mutated: > 20.0 changed to < 20.0",
                "code": source_code.replace("> 20.0", "< 20.0"),
            })

        # 3. Mutate threshold constant: 20.0 to 30.0
        if "20.0" in source_code:
            mutations.append({
                "id": "MUT-CONST-30",
                "desc": "Threshold mutated: 20.0 changed to 30.0",
                "code": source_code.replace("20.0", "30.0"),
            })

        # 4. Mutate threshold constant: 20.0 to 10.0
        if "20.0" in source_code:
            mutations.append({
                "id": "MUT-CONST-10",
                "desc": "Threshold mutated: 20.0 changed to 10.0",
                "code": source_code.replace("20.0", "10.0"),
            })

        # 5. Invert return state: "LOCKED" to "UNLOCKED"
        if '"LOCKED"' in source_code:
            mutations.append({
                "id": "MUT-STATE-INV",
                "desc": "Return state mutated: First 'LOCKED' changed to 'UNLOCKED'",
                "code": source_code.replace('"LOCKED"', '"UNLOCKED"', 1),
            })

        # 6. Logical condition mutation: 'or' to 'and'
        if "is_lost or speed" in source_code:
            mutations.append({
                "id": "MUT-LOGIC-AND",
                "desc": "Logic mutated: 'is_lost or speed' changed to 'is_lost and speed'",
                "code": source_code.replace("is_lost or speed", "is_lost and speed"),
            })

        return mutations


def run_mutation_analysis(
    source_code: str,
    test_cases: List[TestCase],
) -> MutationReport:
    """Execute mutation analysis on source code using the provided test suite.

    Args:
        source_code: Python source code string of the ECU version.
        test_cases: List of TestCase instances generated from rules.

    Returns:
        MutationReport detailing killed vs surviving mutants and mutation score.
    """
    mutations = EcuMutator.generate_mutations(source_code)
    results: List[MutantResult] = []
    runner = TestRunner()

    for m in mutations:
        mut_id = m["id"]
        mut_desc = m["desc"]
        mut_code = m["code"]

        # Compile mutated code into dynamic module
        mod = types.ModuleType(f"mutant_{mut_id}")
        try:
            exec(mut_code, mod.__dict__)
            eval_func = getattr(mod, "evaluate")
        except Exception:
            # If mutant fails compilation or runtime setup, it is automatically killed
            results.append(MutantResult(
                mutant_id=mut_id,
                description=mut_desc,
                mutated_code=mut_code,
                killed=True,
                failing_test_ids=["SYNTAX_OR_IMPORT_ERROR"],
            ))
            continue

        # Instantiate VirtualECU with mutant's evaluate function
        mutant_ecu = VirtualECU()
        mutant_ecu._evaluate_func = eval_func
        mutant_ecu.door_controller.set_logic(eval_func)

        # Run test cases
        test_results = runner.run_suite(test_cases, ecu=mutant_ecu)
        failing_tests = [r.test_id for r in test_results if not r.passed]
        killed = len(failing_tests) > 0

        results.append(MutantResult(
            mutant_id=mut_id,
            description=mut_desc,
            mutated_code=mut_code,
            killed=killed,
            failing_test_ids=failing_tests,
        ))

    total = len(results)
    killed_cnt = sum(1 for r in results if r.killed)
    survived_cnt = total - killed_cnt
    score = (killed_cnt / total * 100.0) if total > 0 else 0.0

    return MutationReport(
        total_mutants=total,
        killed_count=killed_cnt,
        survived_count=survived_cnt,
        mutation_score=round(score, 1),
        mutants=results,
    )
