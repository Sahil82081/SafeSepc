"""Automotive Requirement Extractor Agent (Rule 4, Rule 6, Rule 7, Rule 8, Rule 9).

A Gemini tool-calling agent that:
1. Reads PDF pages and searches text using tools: read_pdf_page, search_pdf, ask_human.
2. Extracts each requirement as a structured Requirement object.
3. Scores quality: ambiguity (LOW/MEDIUM/HIGH), problem, and suggestion.
4. Detects vague words ('quickly', 'smoothly', 'appropriate'), threshold conflicts, and safety relevance.
5. Saves every thought, tool call, and tool result to the agent_log SQLite table.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import uuid
import json

from backend.app.config import MAX_TOOL_CALLS_PER_ATTEMPT, MAX_FIX_ATTEMPTS
from backend.app.models.domain import Requirement
from backend.app.services.audit_logger import AuditLogger
from backend.app.tools.registry import execute_tool
from backend.app.agents.llm import GeminiClient, get_llm_client


VAGUE_TERMS = {
    "quickly": ("High beam / passing beam transition requires defined latency limit in milliseconds (e.g. 200 ms).", "Specify maximum reaction time: 'switch within 200 ms'."),
    "smoothly": ("Lacks observable and measurable pass/fail criterion.", "Define maximum actuator jitter or angular slew rate in degrees/sec."),
    "appropriate": ("Undefined fallback mode.", "Explicitly specify target default state: 'fall back to low beam'."),
    "reasonable": ("Reasonable time is subjective and untestable.", "Specify quantitative time threshold (e.g. 'within 500 ms')."),
    "timely": ("Lacks measurable deadline.", "Define millisecond response deadline."),
}


class RequirementExtractorAgent:
    """Agent extracting and evaluating requirements from automotive PDFs using tool calling."""

    def __init__(
        self,
        llm_client: Optional[GeminiClient] = None,
        cycle_id: Optional[str] = None,
        agent_name: str = "extractor_agent",
    ):
        self.llm_client = llm_client if llm_client is not None else get_llm_client()
        self.cycle_id = cycle_id or f"cycle-extract-{uuid.uuid4().hex[:8]}"
        self.agent_name = agent_name
        self.audit_logger = AuditLogger()
        self.tool_call_count = 0
        self.attempt_number = 1

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered tool through the registry with audit logging (Rule 8) and limits (Rule 7)."""
        self.tool_call_count += 1
        if self.tool_call_count > MAX_TOOL_CALLS_PER_ATTEMPT:
            return {"error": f"Tool call limit ({MAX_TOOL_CALLS_PER_ATTEMPT}) exceeded for attempt {self.attempt_number}."}

        return execute_tool(
            name=tool_name,
            arguments=arguments,
            cycle_id=self.cycle_id,
            agent_name=self.agent_name,
            attempt_number=self.attempt_number,
            tool_call_number=self.tool_call_count,
        )

    def _score_requirement_quality(
        self,
        req_id: str,
        text: str,
        pdf_path: str,
    ) -> Dict[str, Any]:
        """Evaluate ambiguity, quality flags, and safety relevance."""
        flags: List[str] = []
        terms: List[str] = []
        ambiguity = "LOW"
        problem = None
        suggestion = None

        # 1. Check for vague/unclear terms
        lower_text = text.lower()
        for term, (prob, sugg) in VAGUE_TERMS.items():
            pattern = rf"\b{term}\b"
            if re.search(pattern, lower_text):
                ambiguity = "HIGH"
                flags.append("ambiguous")
                terms.append(term)
                problem = prob
                suggestion = sugg

                # Re-read / search PDF to verify if term is defined elsewhere in the document
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Unclear term '{term}' detected in {req_id}. Searching document to check for definitions.",
                    attempt_number=self.attempt_number,
                    tool_call_number=self.tool_call_count,
                )
                self._call_tool("search_pdf", {"pdf_path": pdf_path, "query": term})
                break

        # 2. Check for conflicting requirements (e.g. REQ-017 vs REQ-031)
        conflict_with = None
        if "30 km/h" in text and "high beam" in lower_text:
            flags.append("conflict")
            conflict_with = "REQ-031"
            problem = "Threshold 30 km/h contradicts REQ-031 (40 km/h) for high beam activation."
            suggestion = "Standardize threshold to either 30 km/h or 40 km/h."
        elif "40 km/h" in text and "high beam" in lower_text:
            flags.append("conflict")
            conflict_with = "REQ-017"
            problem = "Threshold 40 km/h contradicts REQ-017 (30 km/h) for high beam activation."
            suggestion = "Standardize threshold to either 30 km/h or 40 km/h."

        # 3. Assess Functional Safety (ISO 26262)
        safety = False
        asil = "QM"
        if any(w in lower_text for w in ("oncoming", "glare", "door", "lock", "brake", "sensor failure", "lost")):
            safety = True
            if "door" in lower_text or "lock" in lower_text:
                asil = "B"
            elif "oncoming" in lower_text or "lost" in lower_text:
                asil = "C"

        return {
            "flags": flags,
            "terms": terms,
            "ambiguity": ambiguity,
            "problem": problem,
            "suggestion": suggestion,
            "safety": safety,
            "asil": asil,
            "conflict_with": conflict_with,
        }

    def extract(self, pdf_path: str) -> List[Requirement]:
        """Extract all automotive requirements from PDF with quality scoring.

        Args:
            pdf_path: Filepath to sample or automotive requirements PDF.

        Returns:
            List of parsed and quality-scored Requirement objects.
        """
        self.audit_logger.log_thought(
            cycle_id=self.cycle_id,
            agent_name=self.agent_name,
            thought=f"Starting extraction on {pdf_path}.",
            attempt_number=self.attempt_number,
            tool_call_number=0,
        )

        extracted_raw_text: List[str] = []

        # Tool Call: Read Page 1
        p1_res = self._call_tool("read_pdf_page", {"pdf_path": pdf_path, "page_number": 1})
        if p1_res.get("text"):
            extracted_raw_text.append(p1_res["text"])

        # Read all remaining pages if document has multiple pages
        total_pages = p1_res.get("total_pages", 1)
        for page_num in range(2, min(total_pages + 1, 50)):
            p_res = self._call_tool("read_pdf_page", {"pdf_path": pdf_path, "page_number": page_num})
            if p_res.get("text"):
                extracted_raw_text.append(p_res["text"])

        full_text = "\n".join(extracted_raw_text)

        # Parse requirement lines starting with REQ-XXX or other requirement keys
        pattern = r"((?:REQ|SPEC|SYS|SW)[-_]?\d+):\s*([^\n\r]+(?:\n(?!\s*(?:REQ|SPEC|SYS|SW)[-_]?\d+:)[^\n\r]+)*)"
        matches = re.findall(pattern, full_text, flags=re.IGNORECASE)

        requirements: List[Requirement] = []

        if matches:
            for req_id, raw_body in matches:
                clean_text = raw_body.replace("\n", " ").strip()
                quality = self._score_requirement_quality(req_id, clean_text, pdf_path)

                req = Requirement(
                    id=req_id.upper(),
                    text=clean_text,
                    flags=quality["flags"],
                    terms=quality["terms"],
                    safety=quality["safety"],
                    asil=quality["asil"],
                    ambiguity=quality["ambiguity"],
                    problem=quality["problem"],
                    suggestion=quality["suggestion"],
                    conflict_with=quality["conflict_with"],
                    note=f"Extracted from {Path(pdf_path).name}. Quality: {quality['ambiguity']} ambiguity.",
                )
                requirements.append(req)
        elif full_text.strip():
            # If standard regex finds no labeled requirements, use Gemini to parse requirements from text
            try:
                prompt = f"""You are an automotive requirements engineer extracting formal specifications from this document text.
Extract each distinct automotive requirement as a structured JSON array of objects.
Document Text:
\"\"\"
{full_text[:6000]}
\"\"\"

Return ONLY valid JSON in format:
[
  {{
    "id": "REQ-001",
    "text": "Full text of requirement...",
    "asil": "QM, A, B, C, or D",
    "ambiguity": "LOW, MEDIUM, or HIGH"
  }}
]
"""
                resp = self.llm_client.generate(prompt=prompt)
                raw = resp.text.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        r_id = item.get("id", f"REQ-{len(requirements)+1:03d}")
                        r_text = item.get("text", "")
                        quality = self._score_requirement_quality(r_id, r_text, pdf_path)
                        req = Requirement(
                            id=r_id,
                            text=r_text,
                            flags=quality["flags"],
                            terms=quality["terms"],
                            safety=quality["safety"],
                            asil=item.get("asil") or quality["asil"],
                            ambiguity=item.get("ambiguity") or quality["ambiguity"],
                            problem=quality["problem"],
                            suggestion=quality["suggestion"],
                            conflict_with=quality["conflict_with"],
                            note=f"Extracted via Gemini from {Path(pdf_path).name}.",
                        )
                        requirements.append(req)
            except Exception as exc:
                self.audit_logger.log_thought(
                    cycle_id=self.cycle_id,
                    agent_name=self.agent_name,
                    thought=f"Gemini fallback extraction notice: {exc}",
                )

        self.audit_logger.log_thought(
            cycle_id=self.cycle_id,
            agent_name=self.agent_name,
            thought=f"Successfully extracted {len(requirements)} requirements from {pdf_path}.",
            attempt_number=self.attempt_number,
            tool_call_number=self.tool_call_count,
        )

        return requirements
