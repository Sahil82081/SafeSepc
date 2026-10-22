"""SafeSpec Testing Package.

Exports:
- test_generator: generate_tests, compute_expected_value
- test_runner: TestRunner
- fault_injection: Fault, MessageLostFault, MessageDelayedFault, SensorStuckFault, FaultInjector
- mutation: EcuMutator, run_mutation_analysis, MutationReport, MutantResult
"""

from backend.app.testing.test_generator import generate_tests, compute_expected_value
from backend.app.testing.test_runner import TestRunner
from backend.app.testing.fault_injection import (
    Fault,
    MessageLostFault,
    MessageDelayedFault,
    SensorStuckFault,
    FaultInjector,
)
from backend.app.testing.mutation import (
    EcuMutator,
    run_mutation_analysis,
    MutationReport,
    MutantResult,
)

__all__ = [
    "generate_tests",
    "compute_expected_value",
    "TestRunner",
    "Fault",
    "MessageLostFault",
    "MessageDelayedFault",
    "SensorStuckFault",
    "FaultInjector",
    "EcuMutator",
    "run_mutation_analysis",
    "MutationReport",
    "MutantResult",
]
