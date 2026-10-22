"""Formalizer Agent (Rule 4, Rule 5, Rule 8).

Converts natural language automotive Requirements into checkable Rules (Rule 5 format):
{id, text, condition:{var,op,value}, action:{var,op,value}}
and generates plain English back-translations.
Requirements that cannot be formalized (e.g. vague 'quickly') are marked 'not_formalizable' with a reason.
"""

from typing import List, Dict, Any, Optional, Literal
import json
import re
from pydantic import BaseModel, Field

from backend.app.models.domain import Requirement, Rule, RuleCondition, RuleAction
from backend.app.services.audit_logger import AuditLogger
from backend.app.agents.llm import GeminiClient, get_llm_client

OP_WORDING = {
    ">": "exceeds",
    ">=": "is at least",
    "<": "is less than",
    "<=": "is at most",
    "==": "is equal to",
    "=": "is equal to",
    "!=": "is not equal to",
}


class FormalizedRequirement(BaseModel):
    """Result of formalizing a Requirement into a checkable Rule."""

    req_id: str
    original_text: str
    status: Literal["formalized", "not_formalizable"]
    rule: Optional[Rule] = None
    back_translation: Optional[str] = None
    reason: Optional[str] = None
    asil: str = "QM"

    @property
    def is_formalizable(self) -> bool:
        """Convenience property for formalizability check."""
        return self.status == "formalized" and self.rule is not None


def generate_back_translation(rule: Rule) -> str:
    """Generate a clean, unambiguous plain English back-translation from a Rule."""
    c = rule.condition
    a = rule.action
    op_word = OP_WORDING.get(c.op, c.op)

    # Contextual wording for automotive signals
    if c.var == "speed":
        cond_str = f"vehicle speed {op_word} {c.value} km/h"
    elif c.var == "lux":
        cond_str = f"ambient light {op_word} {c.value} lux"
    elif c.var == "oncoming_distance":
        cond_str = f"oncoming vehicle distance {op_word} {c.value} m"
    elif c.var == "camera_lost_ms":
        cond_str = f"camera message loss duration {op_word} {c.value} ms"
    elif c.var == "latency_ms":
        cond_str = f"actuation latency {op_word} {c.value} ms"
    elif c.var == "sensor_failure":
        cond_str = f"sensor failure flag {op_word} {c.value}"
    elif c.var == "speed_valid":
        cond_str = f"speed validity flag {op_word} {c.value}"
    else:
        cond_str = f"{c.var} {op_word} {c.value}"

    if a.var == "door":
        action_str = f"central door lock shall be {a.value}"
    elif a.var == "beam":
        action_str = f"headlamp shall switch to {a.value} beam"
    elif a.var == "dtc_logged":
        action_str = f"diagnostic trouble code shall be logged ({a.value})"
    elif a.var == "speed_effective":
        action_str = f"effective speed shall be set to {a.value}"
    elif a.var == "latency_ms":
        action_str = f"maximum transition time shall be {a.value} ms"
    else:
        action_str = f"{a.var} shall be set to {a.value}"

    return f"If {cond_str}, the {action_str}."


def normalize_var_name(var: str) -> str:
    """Normalize signal/actuator names into canonical automotive domain variables."""
    v = var.lower().strip()
    if v in ("vehicle_speed", "vehiclespeed", "velocity", "speed_kmh", "speed"):
        return "speed"
    if v in ("central_door_lock", "door_lock", "door_state", "doorlock", "door"):
        return "door"
    if v in ("headlamp", "headlamp_beam", "passing_beam", "high_beam", "beam_state", "beam"):
        return "beam"
    if v in ("oncoming", "oncoming_dist", "oncoming_vehicle_distance", "oncoming_distance"):
        return "oncoming_distance"
    if v in ("ambient_light", "light_lux", "lux"):
        return "lux"
    if v in ("sensor_fault", "sensor_fail", "sensor_failure"):
        return "sensor_failure"
    if v in ("speed_validity", "speed_valid"):
        return "speed_valid"
    if v in ("camera_lost", "camera_loss", "camera_lost_ms"):
        return "camera_lost_ms"
    if v in ("latency", "reaction_time", "latency_ms"):
        return "latency_ms"
    if v in ("dtc", "dtc_log", "dtc_logged"):
        return "dtc_logged"
    if v in ("speed_effective", "effective_speed"):
        return "speed_effective"
    if v in ("pedal", "pedal_pct", "brake_pedal"):
        return "pedal_pct"
    if v in ("brake_pressure", "pressure", "pressure_bar"):
        return "pressure_bar"
    return v


def normalize_value(val: Any) -> Any:
    """Normalize string actions or numeric thresholds."""
    if isinstance(val, str):
        v_upper = val.upper().strip()
        if v_upper in ("LOCKED", "UNLOCKED", "LOW", "HIGH", "OFF", "FALLBACK", "TRUE", "FALSE"):
            if v_upper == "TRUE":
                return True
            if v_upper == "FALSE":
                return False
            return v_upper
        # If string represents a number e.g. "20.0 km/h" or "20"
        m = re.match(r"^[-+]?[0-9]*\.?[0-9]+", val.strip())
        if m:
            try:
                num = float(m.group(0))
                return num if "." in m.group(0) else int(num)
            except ValueError:
                pass
        return val
    return val


# Module-level formalization cache to avoid redundant API calls and rate-limiting
_formalization_cache: Dict[str, FormalizedRequirement] = {}


class RequirementFormalizerAgent:
    """Agent formalizing requirements into checkable rules and English back-translations."""

    def __init__(
        self,
        llm_client: Optional[GeminiClient] = None,
        cycle_id: Optional[str] = None,
        agent_name: str = "formalizer_agent",
    ):
        self.llm_client = llm_client if llm_client is not None else get_llm_client()
        self.cycle_id = cycle_id or "cycle-formalizer"
        self.agent_name = agent_name
        self.audit_logger = AuditLogger()

    def _formalize_with_gemini(self, req: Requirement) -> Optional[FormalizedRequirement]:
        """Formalize requirement using Gemini LLM structured generation (Rule 3)."""
        prompt = f"""You are an automotive safety engineer formalizing requirements into machine-checkable Rules (fixed format: {{id, text, condition:{{var, op, value}}, action:{{var, op, value}}}}).
Requirement ID: {req.id}
Text: {req.text}
ASIL: {req.asil}

Canonical automotive signal variables to use:
- Sensors/Conditions:
  * "speed" (in km/h, numeric float)
  * "oncoming_distance" (in m, numeric float)
  * "lux" (ambient light in lux, numeric float)
  * "camera_lost_ms" (loss duration in ms, numeric float)
  * "latency_ms" (latency in ms, numeric float)
  * "sensor_failure" (boolean True/False)
  * "speed_valid" (boolean True/False)
  * "detection_signal" (boolean True/False)
  * "pedal_pct" (brake pedal depression 0.0 - 100.0, float)
- Actuators/Actions:
  * "door" (values: "LOCKED", "UNLOCKED")
  * "beam" (values: "LOW", "HIGH", "OFF", "FALLBACK")
  * "dtc_logged" (boolean True)
  * "speed_effective" (numeric float, e.g. 0.0)
  * "pressure_bar" (hydraulic brake pressure in bar, float)

Guidelines:
1. If the requirement contains vague, untestable words (e.g. 'quickly', 'smoothly', 'appropriate') or lacks measurable numeric/enum thresholds, return:
{{"status": "not_formalizable", "reason": "Explanation of why requirement cannot be formalized"}}

2. For restrictive requirements stating 'only above X' or 'below X shall remain low beam/unlocked', formalize the restriction: condition: {{"var": "<var>", "op": "<", "value": X}}, action: {{"var": "<actuator>", "op": "=", "value": "LOW" or "UNLOCKED"}}.

3. For compound requirements specifying multiple conditions (e.g. 'above 30 km/h when ambient light is below 50 lux and no vehicle is ahead'), extract the primary automotive threshold condition ('speed' > 30.0) as the Rule condition so it can be formally analyzed for SMT conflicts against other speed-threshold rules. Do NOT reject requirements that contain clear, measurable quantitative thresholds.

4. If the requirement can be formalized, return:
{{
  "status": "formalized",
  "condition": {{"var": "<canonical_var_name>", "op": "<comparison op: >, >=, <, <=, ==, !=>", "value": <number, bool, or string>}},
  "action": {{"var": "<canonical_actuator_name>", "op": "=", "value": <target_val>}},
  "back_translation": "<plain English back-translation>"
}}
Return ONLY valid JSON with double quotes for all keys and strings.
"""
        try:
            resp = self.llm_client.generate(prompt=prompt)
            raw = resp.text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            try:
                data = json.loads(raw)
            except Exception:
                import ast
                try:
                    data = ast.literal_eval(raw)
                except Exception:
                    cleaned = re.sub(r",\s*([\}\]])", r"\1", raw)
                    data = json.loads(cleaned)

            status = data.get("status")
            if status == "not_formalizable":
                reason = data.get("reason", "Vague or untestable requirement.")
                return FormalizedRequirement(
                    req_id=req.id,
                    original_text=req.text,
                    status="not_formalizable",
                    rule=None,
                    back_translation=None,
                    reason=reason,
                    asil=req.asil,
                )
            elif status == "formalized" and "condition" in data and "action" in data:
                c_data = data["condition"]
                a_data = data["action"]
                norm_c_var = normalize_var_name(str(c_data["var"]))
                norm_c_val = normalize_value(c_data["value"])
                norm_a_var = normalize_var_name(str(a_data["var"]))
                norm_a_val = normalize_value(a_data["value"])

                cond = RuleCondition(var=norm_c_var, op=str(c_data["op"]), value=norm_c_val)
                act = RuleAction(var=norm_a_var, op=str(a_data.get("op", "=")), value=norm_a_val)
                rule = Rule(id=req.id, text=req.text, condition=cond, action=act, asil=req.asil)
                back_trans = generate_back_translation(rule)
                return FormalizedRequirement(
                    req_id=req.id,
                    original_text=req.text,
                    status="formalized",
                    rule=rule,
                    back_translation=back_trans,
                    reason=None,
                    asil=req.asil,
                )
        except Exception as exc:
            return FormalizedRequirement(
                req_id=req.id,
                original_text=req.text,
                status="not_formalizable",
                rule=None,
                back_translation=None,
                reason=f"Unable to formalize requirement: {str(exc)}",
                asil=req.asil,
            )
        return None

    def formalize_single(self, req: Requirement) -> FormalizedRequirement:
        """Formalize an individual requirement into a Rule using real Gemini LLM or mark not_formalizable."""
        cache_key = f"{req.id}:{req.text.strip()}"
        if cache_key in _formalization_cache:
            cached = _formalization_cache[cache_key]
            return FormalizedRequirement(
                req_id=cached.req_id,
                original_text=cached.original_text,
                status=cached.status,
                rule=cached.rule,
                back_translation=cached.back_translation,
                reason=cached.reason,
                asil=cached.asil,
            )

        # Check if requirement is ambiguous or flagged as non-formalizable (e.g. contains 'quickly')
        text_lower = req.text.lower()
        if (
            req.ambiguity == "HIGH"
            or "ambiguous" in req.flags
            or "untestable" in req.flags
            or "quickly" in text_lower
            or "smoothly" in text_lower
            or "appropriate" in text_lower
        ):
            reason = req.problem or (
                "Contains non-measurable or untestable term 'quickly' without quantitative threshold in milliseconds."
                if "quickly" in text_lower
                else "Contains non-measurable or untestable term without quantifiable threshold."
            )
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=f"Requirement {req.id} cannot be formalized: {reason}",
            )
            return FormalizedRequirement(
                req_id=req.id,
                original_text=req.text,
                status="not_formalizable",
                rule=None,
                back_translation=None,
                reason=reason,
                asil=req.asil,
            )

        # 1. Real Gemini LLM formalization
        llm_result = self._formalize_with_gemini(req)
        if llm_result is not None:
            if llm_result.status == "formalized":
                _formalization_cache[cache_key] = llm_result

            thought = (
                f"Gemini formalized {req.id} into Rule ({llm_result.status})."
                if llm_result.is_formalizable
                else f"Gemini marked {req.id} as not_formalizable: {llm_result.reason}"
            )
            self.audit_logger.log_thought(
                cycle_id=self.cycle_id,
                agent_name=self.agent_name,
                thought=thought,
            )
            return llm_result

        # No dummy fallback: report real inability to formalize
        reason = "Unable to extract formal trigger condition and action from requirement text."
        self.audit_logger.log_thought(
            cycle_id=self.cycle_id,
            agent_name=self.agent_name,
            thought=f"Requirement {req.id} could not be formalized: {reason}",
        )
        return FormalizedRequirement(
            req_id=req.id,
            original_text=req.text,
            status="not_formalizable",
            rule=None,
            back_translation=None,
            reason=reason,
            asil=req.asil,
        )

    def formalize_all(self, requirements: List[Requirement]) -> List[FormalizedRequirement]:
        """Formalize a list of requirements into Rules and back-translations."""
        results: List[FormalizedRequirement] = []
        for req in requirements:
            res = self.formalize_single(req)
            results.append(res)
        return results
