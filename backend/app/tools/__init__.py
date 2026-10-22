"""SafeSpec Agent Tools Package (Rule 6 & Rule 8).

Exports:
- Tool Registry & Execution:
  - TOOL_REGISTRY, list_tools, get_tool, get_gemini_declarations, execute_tool
- Agent Tools:
  - read_pdf_page, search_pdf
  - ask_human
  - run_z3_conflicts, run_z3_invariant
  - generate_tests, run_tests, run_single_test
  - inject_fault
  - read_ecu_code, create_ecu_version
  - run_mutation_tests
  - search_memory, save_memory
"""

from backend.app.tools.agent_tools import (
    read_pdf_page,
    search_pdf,
    ask_human,
    run_z3_conflicts,
    run_z3_invariant,
    generate_tests,
    run_tests,
    run_single_test,
    inject_fault,
    read_ecu_code,
    create_ecu_version,
    run_mutation_tests,
    search_memory,
    save_memory,
)
from backend.app.tools.registry import (
    TOOL_REGISTRY,
    list_tools,
    get_tool,
    get_gemini_declarations,
    execute_tool,
)

__all__ = [
    "TOOL_REGISTRY",
    "list_tools",
    "get_tool",
    "get_gemini_declarations",
    "execute_tool",
    "read_pdf_page",
    "search_pdf",
    "ask_human",
    "run_z3_conflicts",
    "run_z3_invariant",
    "generate_tests",
    "run_tests",
    "run_single_test",
    "inject_fault",
    "read_ecu_code",
    "create_ecu_version",
    "run_mutation_tests",
    "search_memory",
    "save_memory",
]
