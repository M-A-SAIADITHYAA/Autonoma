from __future__ import annotations
import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from autonoma.config import settings
from autonoma.core.models import ToolCall
from autonoma.core.memory import AgentMemory
from autonoma.llm.mock_engine import DeterministicReasoningEngine, ReActDecision
from autonoma.llm.prompts import AGENT_SYSTEM_PROMPT

class LLMClient:
    """
    Unified client supporting OpenAI, Gemini, Anthropic, Ollama, and built-in Deterministic engine.
    Ensures zero external dependency barriers while offering frontier model integration.
    """
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.llm_provider
        self.mock_engine = DeterministicReasoningEngine()
        self._detect_provider()

    def _detect_provider(self):
        if self.provider == "auto":
            if settings.openai_api_key:
                self.provider = "openai"
            elif settings.gemini_api_key:
                self.provider = "gemini"
            elif settings.anthropic_api_key:
                self.provider = "anthropic"
            else:
                self.provider = "deterministic"

    def decide(self, memory: AgentMemory, tool_schemas: List[Dict[str, Any]]) -> ReActDecision:
        if self.provider == "deterministic" or not self.provider:
            return self.mock_engine.decide_next_step(memory)

        try:
            if self.provider == "openai":
                return self._call_openai(memory, tool_schemas)
            elif self.provider == "gemini":
                return self._call_gemini(memory, tool_schemas)
            elif self.provider == "anthropic":
                return self._call_anthropic(memory, tool_schemas)
            elif self.provider == "ollama":
                return self._call_ollama(memory, tool_schemas)
            else:
                return self.mock_engine.decide_next_step(memory)
        except Exception as e:
            # Resilient fallback to deterministic engine
            print(f"⚠️ [LLM Warning] External provider '{self.provider}' encountered an error: {e}. Falling back to Deterministic Reasoning Engine.")
            return self.mock_engine.decide_next_step(memory)

    def _format_context(self, memory: AgentMemory) -> str:
        plan_desc = ""
        if memory.plan:
            curr = memory.plan.current_milestone
            plan_desc = f"Active Milestone: {curr.title if curr else 'None'}\n"
            plan_desc += "Milestones:\n" + "\n".join([f"- [{m.status.value}] {m.title}: {m.description}" for m in memory.plan.milestones])

        recent_history = memory.get_recent_history_summary(5)
        entities_str = json.dumps(memory.entities, indent=2)

        return (
            f"GOAL: {memory.goal}\n\n"
            f"PLAN:\n{plan_desc}\n\n"
            f"WORKING MEMORY ENTITIES:\n{entities_str}\n\n"
            f"RECENT STEP HISTORY:\n{recent_history}\n\n"
            "Analyze the state, determine whether the last action succeeded or failed, and decide the next action."
        )

    def _call_openai(self, memory: AgentMemory, tool_schemas: List[Dict[str, Any]]) -> ReActDecision:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        tools_str = json.dumps(tool_schemas, indent=2)
        system = AGENT_SYSTEM_PROMPT.format(tools_description=tools_str)
        user_content = self._format_context(memory)

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_llm_response(text)

    def _call_gemini(self, memory: AgentMemory, tool_schemas: List[Dict[str, Any]]) -> ReActDecision:
        key = settings.gemini_api_key
        model = settings.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        tools_str = json.dumps(tool_schemas, indent=2)
        system = AGENT_SYSTEM_PROMPT.format(tools_description=tools_str)
        user_content = self._format_context(memory)

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system}\n\n{user_content}"}]}
            ],
            "generationConfig": {"temperature": 0.2}
        }
        with httpx.Client(timeout=35.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_llm_response(text)

    def _call_anthropic(self, memory: AgentMemory, tool_schemas: List[Dict[str, Any]]) -> ReActDecision:
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        tools_str = json.dumps(tool_schemas, indent=2)
        system = AGENT_SYSTEM_PROMPT.format(tools_description=tools_str)
        user_content = self._format_context(memory)

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
            "temperature": 0.1
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
            return self._parse_llm_response(text)

    def _call_ollama(self, memory: AgentMemory, tool_schemas: List[Dict[str, Any]]) -> ReActDecision:
        url = f"{settings.ollama_base_url}/api/generate"
        tools_str = json.dumps(tool_schemas, indent=2)
        system = AGENT_SYSTEM_PROMPT.format(tools_description=tools_str)
        prompt = f"{system}\n\n{self._format_context(memory)}"

        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json()["response"]
            return self._parse_llm_response(text)

    def _parse_llm_response(self, text: str) -> ReActDecision:
        thought_match = re.search(r"THOUGHT:\s*(.*?)(?=\nACTION:|\Z)", text, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"ACTION:\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)

        thought = thought_match.group(1).strip() if thought_match else text[:250]
        action_name = action_match.group(1).strip() if action_match else "complete_task"

        params = {}
        params_match = re.search(r"PARAMETERS:\s*```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if not params_match:
            params_match = re.search(r"PARAMETERS:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)
        if params_match:
            try:
                params = json.loads(params_match.group(1).strip())
            except Exception:
                pass

        return ReActDecision(
            thought=thought,
            action=ToolCall(tool_name=action_name, parameters=params)
        )
