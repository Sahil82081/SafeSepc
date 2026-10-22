"""SafeSpec Formal Verification Package.

Exports:
- find_conflicts: Z3-based pair-wise contradiction detector
- check_invariant: Safety invariant reachable bad state checker
- Z3TypeManager: Variable and enum domain manager
"""

from backend.app.formal.z3_checker import (
    find_conflicts,
    check_invariant,
    Z3TypeManager,
    parse_bad_state,
)

__all__ = [
    "find_conflicts",
    "check_invariant",
    "Z3TypeManager",
    "parse_bad_state",
]
