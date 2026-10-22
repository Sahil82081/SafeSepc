"""Gemini LLM Connection and Orchestration Service (Rule 3).

Strict compliance:
- Model name lives ONLY in backend/app/config.py (GEMINI_MODEL).
- API key loaded from environment / .env (GEMINI_API_KEY).
- Supports mock mode for running tests offline without API access.
- Logs LLM thoughts and function calls to agent_log (Rule 8).
"""

from typing import Dict, Any, List, Optional, Callable, Type
import json
import os
import time
import re
from pydantic import BaseModel

from backend.app.config import GEMINI_MODEL, GEMINI_API_KEY
from backend.app.services.audit_logger import AuditLogger

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class LLMResponse(BaseModel):
    """Normalized response envelope from LLM."""

    text: str
    tool_calls: List[Dict[str, Any]] = []
    finish_reason: Optional[str] = "STOP"
    raw_response: Optional[Any] = None


class GeminiClient:
    """Wrapper for Google Gemini API supporting tool calling and offline test mocking."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        mock_mode: bool = False,
        mock_responder: Optional[Callable[[str, List[Dict[str, Any]]], LLMResponse]] = None,
    ):
        self.api_key = api_key or GEMINI_API_KEY
        # Rule 3: The model name lives only in backend/app/config.py
        self.model_name = model_name or GEMINI_MODEL
        self.mock_mode = mock_mode or not bool(self.api_key)
        self.mock_responder = mock_responder
        self._client = None

        if not self.mock_mode and genai is not None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured in environment or .env file.")
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini Client: {e}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Generate content from Gemini."""
        if self.mock_responder is not None:
            return self.mock_responder(prompt, tools or [])

        if self._client is None or genai is None:
            raise RuntimeError("Gemini SDK not initialized. Set GEMINI_API_KEY in environment.")

        config_args: Dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_args["system_instruction"] = system_instruction
        if tools:
            config_args["tools"] = tools

        config = types.GenerateContentConfig(**config_args) if types else None

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                    wait_sec = 10.0 * (attempt + 1)
                    m = re.search(r"retry\s+(?:delay\s+)?in\s+(\d+(?:\.\d+)?)s?", err_str, re.IGNORECASE)
                    if m:
                        wait_sec = min(float(m.group(1)) + 1.0, 45.0)
                    time.sleep(wait_sec)
                else:
                    raise

        tool_calls = []
        if hasattr(response, "function_calls") and response.function_calls:
            for call in response.function_calls:
                tool_calls.append({
                    "name": call.name,
                    "arguments": dict(call.args) if hasattr(call, "args") else {},
                })

        return LLMResponse(
            text=response.text or "",
            tool_calls=tool_calls,
            raw_response=response,
        )


def get_llm_client(mock_responder: Optional[Callable] = None) -> GeminiClient:
    """Factory helper returning configured Gemini client instance."""
    return GeminiClient(mock_responder=mock_responder)
