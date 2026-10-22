"""Formal Verification Engine using Z3 SMT Solver.

Provides:
- find_conflicts(rules): Detects rule pairs that can trigger simultaneously with contradictory actions.
- check_invariant(rules, bad_state): Proves whether an unsafe/bad state is reachable under the rules.
Supports both numeric (Real) and enum/string variables with concrete counter-examples.
"""

from typing import List, Dict, Any, Optional, Set, Union
import re
import z3

from backend.app.models.domain import Rule, RuleCondition, RuleAction, Conflict


class Z3TypeManager:
    """Manages Z3 variable declarations, enum domains, and value conversions."""

    def __init__(self):
        self.vars: Dict[str, z3.ExprRef] = {}
        self.var_types: Dict[str, str] = {}  # "real", "bool", "string"
        self.enum_domains: Dict[str, Set[str]] = {}

    def register_value(self, var_name: str, value: Any) -> None:
        """Register variable name and infer its type from encountered values."""
        if isinstance(value, bool):
            if var_name not in self.var_types:
                self.var_types[var_name] = "bool"
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if var_name not in self.var_types or self.var_types[var_name] != "real":
                self.var_types[var_name] = "real"
        elif isinstance(value, str):
            if var_name not in self.var_types:
                self.var_types[var_name] = "string"
            if var_name not in self.enum_domains:
                self.enum_domains[var_name] = set()
            self.enum_domains[var_name].add(value)

    def get_or_create_var(self, var_name: str, fallback_type: str = "real") -> z3.ExprRef:
        """Retrieve or instantiate a Z3 variable based on registered type."""
        if var_name in self.vars:
            return self.vars[var_name]

        vtype = self.var_types.get(var_name, fallback_type)
        if vtype == "bool":
            var_expr = z3.Bool(var_name)
        elif vtype == "string":
            var_expr = z3.String(var_name)
        else:
            var_expr = z3.Real(var_name)

        self.vars[var_name] = var_expr
        return var_expr

    def to_z3_val(self, var_name: str, value: Any) -> z3.ExprRef:
        """Convert a Python literal value into an appropriate Z3 value expression."""
        if isinstance(value, bool):
            return z3.BoolVal(value)
        elif isinstance(value, (int, float)):
            return z3.RealVal(float(value))
        elif isinstance(value, str):
            return z3.StringVal(value)
        else:
            return z3.StringVal(str(value))

    def get_domain_constraints(self) -> List[z3.BoolRef]:
        """Generate domain constraint disjunctions for enum variables."""
        constraints = []
        for var_name, values in self.enum_domains.items():
            if len(values) >= 2:
                z3_var = self.get_or_create_var(var_name, fallback_type="string")
                disj = [z3_var == z3.StringVal(val) for val in values]
                constraints.append(z3.Or(*disj))
        return constraints


def _build_z3_comparison(z3_var: z3.ExprRef, op: str, z3_val: z3.ExprRef) -> z3.BoolRef:
    """Build a Z3 comparison predicate from operator string."""
    clean_op = op.strip().lower()
    if clean_op in ("==", "=", "eq"):
        return z3_var == z3_val
    elif clean_op in ("!=", "neq"):
        return z3_var != z3_val
    elif clean_op in (">", "gt"):
        return z3_var > z3_val
    elif clean_op in ("<", "lt"):
        return z3_var < z3_val
    elif clean_op in (">=", "gte"):
        return z3_var >= z3_val
    elif clean_op in ("<=", "lte"):
        return z3_var <= z3_val
    else:
        return z3_var == z3_val


def _extract_model_value(model: z3.ModelRef, var_expr: z3.ExprRef) -> Any:
    """Extract a native Python value from a Z3 model assignment."""
    val = model.eval(var_expr, model_completion=True)
    if z3.is_bool(val):
        return z3.is_true(val)
    elif z3.is_real(val):
        try:
            return float(val.as_fraction())
        except Exception:
            try:
                return float(val.as_decimal(4))
            except Exception:
                return float(str(val))
    elif z3.is_int(val):
        return val.as_long()
    elif z3.is_string(val):
        return val.as_string()
    else:
        s = str(val).strip('"')
        return s


def parse_bad_state(bad_state: Any) -> List[RuleCondition]:
    """Normalize bad_state input into a list of RuleCondition predicates.

    Supports:
    - RuleCondition instance
    - List of RuleCondition or dicts
    - Dict of var: (op, value) or var: value
    - String such as 'speed > 20 and door != LOCKED'
    """
    if isinstance(bad_state, RuleCondition):
        return [bad_state]

    if isinstance(bad_state, list):
        parsed = []
        for item in bad_state:
            if isinstance(item, RuleCondition):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(RuleCondition(**item))
            elif isinstance(item, str):
                parsed.extend(parse_bad_state(item))
        return parsed

    if isinstance(bad_state, dict):
        if "var" in bad_state and "op" in bad_state and "value" in bad_state:
            return [RuleCondition(**bad_state)]
        parsed = []
        for k, v in bad_state.items():
            if isinstance(v, tuple) and len(v) == 2:
                op, val = v
                parsed.append(RuleCondition(var=k, op=op, value=val))
            else:
                parsed.append(RuleCondition(var=k, op="==", value=v))
        return parsed

    if isinstance(bad_state, str):
        parsed = []
        parts = re.split(r"\s+(?:and|AND)\s+|,\s*", bad_state.strip())
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^([A-Za-z0-9_]+)\s*(==|!=|>=|<=|>|<|=)\s*(.+)$", part)
            if m:
                var, op, raw_val = m.groups()
                if op == "=":
                    op = "=="
                clean_val = raw_val.strip().strip("'\"")
                if clean_val.lower() in ("true", "false"):
                    val: Any = clean_val.lower() == "true"
                else:
                    try:
                        val = int(clean_val)
                    except ValueError:
                        try:
                            val = float(clean_val)
                        except ValueError:
                            val = clean_val
                parsed.append(RuleCondition(var=var, op=op, value=val))
        return parsed

    return []


def find_conflicts(rules: List[Rule]) -> List[Conflict]:
    """Find pairs of rules whose conditions can both be true while commanding conflicting actions.

    Args:
        rules: List of automotive requirement rules.

    Returns:
        List of Conflict objects containing short reasons and concrete counter-examples.
    """
    conflicts: List[Conflict] = []
    n = len(rules)

    for i in range(n):
        for j in range(i + 1, n):
            r1 = rules[i]
            r2 = rules[j]

            # Rules can only conflict if their actions target the same variable
            if r1.action.var != r2.action.var:
                continue

            # Check if actions are mutually contradictory
            type_mgr = Z3TypeManager()
            type_mgr.register_value(r1.condition.var, r1.condition.value)
            type_mgr.register_value(r2.condition.var, r2.condition.value)
            type_mgr.register_value(r1.action.var, r1.action.value)
            type_mgr.register_value(r2.action.var, r2.action.value)

            action_solver = z3.Solver()
            act_var = type_mgr.get_or_create_var(r1.action.var)
            act_val1 = type_mgr.to_z3_val(r1.action.var, r1.action.value)
            act_val2 = type_mgr.to_z3_val(r2.action.var, r2.action.value)

            action_solver.add(_build_z3_comparison(act_var, r1.action.op, act_val1))
            action_solver.add(_build_z3_comparison(act_var, r2.action.op, act_val2))

            # If actions can co-exist without contradiction, no conflict
            if action_solver.check() == z3.sat:
                continue

            # Actions conflict! Now check if both trigger conditions can hold simultaneously
            cond_solver = z3.Solver()
            for domain_c in type_mgr.get_domain_constraints():
                cond_solver.add(domain_c)

            c1_var = type_mgr.get_or_create_var(r1.condition.var)
            c1_val = type_mgr.to_z3_val(r1.condition.var, r1.condition.value)
            cond_solver.add(_build_z3_comparison(c1_var, r1.condition.op, c1_val))

            c2_var = type_mgr.get_or_create_var(r2.condition.var)
            c2_val = type_mgr.to_z3_val(r2.condition.var, r2.condition.value)
            cond_solver.add(_build_z3_comparison(c2_var, r2.condition.op, c2_val))

            if cond_solver.check() == z3.sat:
                model = cond_solver.model()
                counter_example: Dict[str, Any] = {}
                for vname in (r1.condition.var, r2.condition.var):
                    if vname in type_mgr.vars:
                        counter_example[vname] = _extract_model_value(model, type_mgr.vars[vname])

                reason = (
                    f"Contradictory actions on '{r1.action.var}': {r1.id} sets '{r1.action.value}' "
                    f"while {r2.id} sets '{r2.action.value}' when conditions overlap at {counter_example}."
                )

                conflict = Conflict(
                    id=f"CONF-{r1.id}-{r2.id}",
                    rule_a_id=r1.id,
                    rule_b_id=r2.id,
                    description=reason,
                    overlap_condition=counter_example,
                    counter_example=counter_example,
                    severity="HIGH",
                    status="open",
                )
                conflicts.append(conflict)

    return conflicts


def check_invariant(rules: List[Rule], bad_state: Any) -> Optional[Conflict]:
    """Check if an unsafe/bad state is possible under the given rules.

    Args:
        rules: List of automotive requirement rules defining system behavior.
        bad_state: Unsafe state specification (RuleCondition, list of conditions, dict, or string).

    Returns:
        Conflict object with short reason and counter-example if bad state is possible; None otherwise.
    """
    bad_conditions = parse_bad_state(bad_state)
    if not bad_conditions:
        return None

    type_mgr = Z3TypeManager()

    # Register all types across rules and bad state
    for r in rules:
        type_mgr.register_value(r.condition.var, r.condition.value)
        type_mgr.register_value(r.action.var, r.action.value)

    for bc in bad_conditions:
        type_mgr.register_value(bc.var, bc.value)

    # Ensure complementary enum values exist for realistic counter-examples
    for bc in bad_conditions:
        if type_mgr.var_types.get(bc.var) == "string":
            if bc.var not in type_mgr.enum_domains:
                type_mgr.enum_domains[bc.var] = set()
            type_mgr.enum_domains[bc.var].add(str(bc.value))
            if bc.value == "LOCKED":
                type_mgr.enum_domains[bc.var].add("UNLOCKED")
            elif bc.value == "UNLOCKED":
                type_mgr.enum_domains[bc.var].add("LOCKED")

    solver = z3.Solver()

    # Add domain constraints
    for domain_c in type_mgr.get_domain_constraints():
        solver.add(domain_c)

    # Encode rule semantics: for each rule, condition => action
    for r in rules:
        c_var = type_mgr.get_or_create_var(r.condition.var)
        c_val = type_mgr.to_z3_val(r.condition.var, r.condition.value)
        c_expr = _build_z3_comparison(c_var, r.condition.op, c_val)

        a_var = type_mgr.get_or_create_var(r.action.var)
        a_val = type_mgr.to_z3_val(r.action.var, r.action.value)
        a_expr = _build_z3_comparison(a_var, r.action.op, a_val)

        solver.add(z3.Implies(c_expr, a_expr))

    # Assert bad state predicates
    for bc in bad_conditions:
        b_var = type_mgr.get_or_create_var(bc.var)
        b_val = type_mgr.to_z3_val(bc.var, bc.value)
        b_expr = _build_z3_comparison(b_var, bc.op, b_val)
        solver.add(b_expr)

    if solver.check() == z3.sat:
        model = solver.model()
        counter_example: Dict[str, Any] = {}

        # Collect values for variables involved in bad state and rules
        monitored_vars = {bc.var for bc in bad_conditions}
        for r in rules:
            monitored_vars.add(r.condition.var)
            monitored_vars.add(r.action.var)

        for vname in sorted(monitored_vars):
            if vname in type_mgr.vars:
                counter_example[vname] = _extract_model_value(model, type_mgr.vars[vname])

        bad_desc = " and ".join(f"{bc.var} {bc.op} {bc.value}" for bc in bad_conditions)
        reason = f"Bad state is reachable: {bad_desc} with counter-example {counter_example}."

        return Conflict(
            id="INV-VIOLATION-BAD-STATE",
            rule_a_id="RULES",
            rule_b_id="BAD_STATE",
            description=reason,
            overlap_condition=counter_example,
            counter_example=counter_example,
            severity="CRITICAL",
            status="open",
        )

    return None
