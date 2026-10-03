from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from autonoma.core.models import ToolCall, ToolResult

class ErrorClassifier:
    """Classifies tool execution errors to select optimal recovery policy."""
    
    @staticmethod
    def classify(tool_name: str, error_message: str) -> str:
        err_lower = error_message.lower()
        if any(term in err_lower for term in ("503", "timeout", "temporarily unavailable", "connection refused", "econnrefused")):
            return "TRANSIENT_NETWORK"
        if any(term in err_lower for term in ("element not found", "selector", "not clickable", "stale element", "ui changed")):
            return "UI_DRIFT"
        if any(term in err_lower for term in ("file not found", "no such file", "does not exist")):
            return "FILE_MISSING"
        if any(term in err_lower for term in ("approval denied", "rejected by user", "permission denied", "403")):
            return "PERMISSION_OR_APPROVAL_DENIED"
        if any(term in err_lower for term in ("validation", "invalid format", "schema mismatch")):
            return "VALIDATION_ERROR"
        return "GENERIC_ERROR"

class RecoveryEngine:
    """
    Decides adaptive next steps when a tool execution fails.
    Provides alternative tool mappings, parameter repairs, or retry directives.
    """
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def determine_recovery(
        self, 
        tool_call: ToolCall, 
        result: ToolResult, 
        attempt_count: int
    ) -> Tuple[str, Optional[ToolCall]]:
        """
        Returns (strategy_name, new_suggested_tool_call_or_none)
        """
        error_msg = result.error_message or "Unknown failure"
        category = ErrorClassifier.classify(tool_call.tool_name, error_msg)

        # 1. Transient failure -> Retry with backoff if attempts remain
        if category == "TRANSIENT_NETWORK":
            if attempt_count < self.max_retries:
                return f"RETRY_WITH_BACKOFF (attempt {attempt_count + 1}/{self.max_retries})", tool_call
            else:
                return "ESCALATE_TRANSIENT_EXHAUSTED", None

        # 2. UI failure -> Fallback to direct REST API
        if category == "UI_DRIFT" or tool_call.tool_name.startswith("browser_"):
            if tool_call.tool_name == "browser_fill_form":
                form_data = tool_call.parameters.get("form_data", {})
                return (
                    "FALLBACK_UI_TO_API: Web form interaction failed; falling back to direct ERP REST API endpoint",
                    ToolCall(
                        tool_name="api_call",
                        parameters={
                            "method": "POST",
                            "endpoint": "/api/v1/erp/invoices",
                            "payload": form_data
                        }
                    )
                )

        # 3. Missing file -> Broaden search pattern or search alternate directories
        if category == "FILE_MISSING":
            file_path = tool_call.parameters.get("file_path", "")
            return (
                f"FALLBACK_BROAD_SEARCH: File '{file_path}' not directly accessible; expanding search across entire drive",
                ToolCall(
                    tool_name="file_search",
                    parameters={
                        "query": file_path.split("/")[-1].split(".")[0],
                        "directory": "data/sample_drive"
                    }
                )
            )

        # 4. Permission / Approval Denied -> Abort or request clarification
        if category == "PERMISSION_OR_APPROVAL_DENIED":
            return "ABORT_OR_REQUEST_CLARIFICATION: User denied operation; reflecting on safe alternative", None

        # Generic retry once if first attempt
        if attempt_count < 2:
            return "RETRY_ONCE", tool_call

        return "NO_AUTOMATIC_FALLBACK", None
