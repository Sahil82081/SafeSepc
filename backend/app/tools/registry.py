"""Gemini Function Calling Tool Registry (Rules 6 & 8).

Converts all tools into Gemini function declarations and executes tool calls by name.
Every tool invocation and result is persisted to the agent_log SQLite table.
"""

from typing import Dict, Any, List, Callable, Optional
import inspect

from backend.app.services.audit_logger import AuditLogger
from backend.app.tools import agent_tools

# Master dictionary mapping tool names to plain Python functions
TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "read_pdf_page": agent_tools.read_pdf_page,
    "search_pdf": agent_tools.search_pdf,
    "ask_human": agent_tools.ask_human,
    "run_z3_conflicts": agent_tools.run_z3_conflicts,
    "run_z3_invariant": agent_tools.run_z3_invariant,
    "generate_tests": agent_tools.generate_tests,
    "run_tests": agent_tools.run_tests,
    "run_single_test": agent_tools.run_single_test,
    "inject_fault": agent_tools.inject_fault,
    "read_ecu_code": agent_tools.read_ecu_code,
    "create_ecu_version": agent_tools.create_ecu_version,
    "run_mutation_tests": agent_tools.run_mutation_tests,
    "search_memory": agent_tools.search_memory,
    "save_memory": agent_tools.save_memory,
}


def list_tools() -> List[str]:
    """Return list of all registered tool names."""
    return sorted(list(TOOL_REGISTRY.keys()))


def get_tool(name: str) -> Optional[Callable[..., Dict[str, Any]]]:
    """Retrieve a registered tool function by name."""
    return TOOL_REGISTRY.get(name)


def _python_type_to_gemini(py_type: Any) -> str:
    """Map Python type annotation to OpenAPI/Gemini schema type."""
    if py_type in (int,):
        return "INTEGER"
    elif py_type in (float,):
        return "NUMBER"
    elif py_type in (bool,):
        return "BOOLEAN"
    elif py_type in (list, List):
        return "ARRAY"
    elif py_type in (dict, Dict):
        return "OBJECT"
    else:
        return "STRING"


def get_gemini_declarations() -> List[Dict[str, Any]]:
    """Convert all registered tools into Gemini function declarations.

    Compatible with Google GenAI / Gemini Function Calling specification.
    """
    declarations: List[Dict[str, Any]] = []

    for name, func in TOOL_REGISTRY.items():
        doc = inspect.getdoc(func) or f"Execute {name}"
        sig = inspect.signature(func)

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for p_name, param in sig.parameters.items():
            ann = param.annotation
            gemini_type = _python_type_to_gemini(ann)

            prop_def: Dict[str, Any] = {"type": gemini_type}
            if gemini_type == "ARRAY":
                prop_def["items"] = {"type": "OBJECT"}

            properties[p_name] = prop_def

            if param.default == inspect.Parameter.empty:
                required.append(p_name)

        declarations.append({
            "name": name,
            "description": doc.split("\n\n")[0].strip(),
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            },
        })

    return declarations


def execute_tool(
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
    cycle_id: str = "cycle-interactive",
    agent_name: str = "gemini_agent",
    attempt_number: int = 1,
    tool_call_number: int = 1,
) -> Dict[str, Any]:
    """Execute a registered tool by name with audit logging (Rule 8).

    Guarantees:
    - Never crashes; returns an error field on failure.
    - Persists tool_call and tool_result into agent_log SQLite table.

    Args:
        name: Name of the registered tool to call.
        arguments: Keyword arguments dictionary for the tool.
        cycle_id: Active execution cycle identifier.
        agent_name: Name of calling agent.
        attempt_number: Current retry attempt (1 to 3).
        tool_call_number: Sequential tool call count in attempt (1 to 8).

    Returns:
        Dictionary returned by the tool function, including 'error' field.
    """
    args = arguments or {}
    logger = AuditLogger()

    # Log tool call to agent_log
    logger.log_tool_call(
        cycle_id=cycle_id,
        agent_name=agent_name,
        tool_name=name,
        tool_input=args,
        attempt_number=attempt_number,
        tool_call_number=tool_call_number,
    )

    func = get_tool(name)
    if func is None:
        err_msg = f"Tool '{name}' is not registered. Available tools: {list_tools()}"
        out = {"error": err_msg}
        logger.log_tool_result(
            cycle_id=cycle_id,
            agent_name=agent_name,
            tool_name=name,
            tool_output=out,
            result_summary="TOOL_NOT_FOUND",
            attempt_number=attempt_number,
            tool_call_number=tool_call_number,
        )
        return out

    try:
        result = func(**args)
        if not isinstance(result, dict):
            result = {"output": result, "error": None}

        # Log tool result to agent_log
        summary = "SUCCESS" if not result.get("error") else "ERROR"
        logger.log_tool_result(
            cycle_id=cycle_id,
            agent_name=agent_name,
            tool_name=name,
            tool_output=result,
            result_summary=summary,
            attempt_number=attempt_number,
            tool_call_number=tool_call_number,
        )
        return result

    except Exception as exc:
        err_dict = {"error": f"Exception executing {name}: {str(exc)}"}
        logger.log_tool_result(
            cycle_id=cycle_id,
            agent_name=agent_name,
            tool_name=name,
            tool_output=err_dict,
            result_summary="EXCEPTION",
            attempt_number=attempt_number,
            tool_call_number=tool_call_number,
        )
        return err_dict
