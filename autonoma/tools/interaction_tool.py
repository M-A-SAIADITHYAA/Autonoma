from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolResult, RiskLevel

class AskUserClarificationTool(BaseTool):
    name = "ask_user_clarification"
    description = "Requests clarification from the user when an instruction or search result is ambiguous."
    parameters_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The specific question to ask the user"},
            "options": {"type": "array", "items": {"type": "string"}, "description": "Optional list of multiple choice options"}
        },
        "required": ["question"]
    }

    def __init__(self, interaction_handler=None):
        self.handler = interaction_handler

    def execute(self, question: str, options: Optional[List[str]] = None, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            if not self.handler:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message="Interaction handler not attached to tool.",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            answer = self.handler.request_clarification(question, options)
            return ToolResult(
                tool_name=self.name,
                status="success",
                data={"question": question, "user_response": answer},
                side_effects={"clarification_received": True, "answer": answer},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=f"Clarification request failed: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )

class RequestHumanApprovalTool(BaseTool):
    name = "request_human_approval"
    description = "Prompts the human operator for approval before executing high-risk, irreversible, or high-value actions."
    parameters_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Clear statement of the requested action"},
            "reason": {"type": "string", "description": "Why approval is needed (e.g. amount exceeds $10,000 threshold)"},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"}
        },
        "required": ["prompt", "reason"]
    }

    def __init__(self, interaction_handler=None):
        self.handler = interaction_handler

    def execute(self, prompt: str, reason: str, risk_level: str = "medium", **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            if not self.handler:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message="Interaction handler not attached.",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            approved = self.handler.request_approval(prompt, reason, RiskLevel(risk_level))
            return ToolResult(
                tool_name=self.name,
                status="success" if approved else "error",
                data={"prompt": prompt, "reason": reason, "approved": approved},
                error_message=None if approved else "Action was rejected by the human operator.",
                side_effects={"approval_checked": True, "approved": approved},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=f"Approval request failed: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )

class CompleteTaskTool(BaseTool):
    name = "complete_task"
    description = "Signals that the autonomous worker has fully achieved the user's objective, providing final evidence and summary."
    parameters_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Concise summary of actions taken and final state"},
            "evidence": {"type": "object", "description": "Key proof points (e.g. record ID, amount, date, verification status)"}
        },
        "required": ["summary"]
    }

    def execute(self, summary: str, evidence: Optional[Dict[str, Any]] = None, **kwargs) -> ToolResult:
        start_time = time.time()
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "task_completed": True,
                "summary": summary,
                "evidence": evidence or {}
            },
            side_effects={"terminal_step": True},
            elapsed_ms=(time.time() - start_time) * 1000
        )
