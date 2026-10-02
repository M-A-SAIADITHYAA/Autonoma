from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from autonoma.config import settings
from autonoma.core.models import ToolCall, SafetyDecision, RiskLevel

class SafetyPolicy:
    """
    Evaluates actions before execution against security, financial, and operational invariants.
    Protects against unauthorized high-value writes, destructive commands, and unhandled ambiguity.
    """
    def __init__(self, approval_amount_threshold: float = settings.approval_amount_threshold):
        self.approval_amount_threshold = approval_amount_threshold

    def evaluate_action(self, tool_call: ToolCall, memory_entities: Dict[str, Any]) -> SafetyDecision:
        name = tool_call.tool_name
        params = tool_call.parameters

        # Check 1: Explicit human approval tool
        if name == "request_human_approval":
            return SafetyDecision(
                requires_approval=True,
                risk_level=RiskLevel(params.get("risk_level", "medium")),
                reason=params.get("reason", "Action flagged for human verification"),
                approval_prompt=params.get("prompt", "Do you approve this action?")
            )

        # Check 2: Financial Threshold - Invoices, Payments, Credits
        if name in ("api_call", "erp_create_invoice", "browser_fill_form"):
            amount = None
            if "amount" in params:
                try:
                    amount = float(params["amount"])
                except (ValueError, TypeError):
                    pass
            elif "form_data" in params and isinstance(params["form_data"], dict):
                val = params["form_data"].get("amount") or params["form_data"].get("total_amount")
                if val:
                    try:
                        amount = float(val)
                    except (ValueError, TypeError):
                        pass

            if amount is not None and amount >= self.approval_amount_threshold:
                vendor = params.get("vendor", params.get("form_data", {}).get("vendor", "Unknown"))
                return SafetyDecision(
                    requires_approval=True,
                    risk_level=RiskLevel.HIGH,
                    reason=f"Financial transaction of ${amount:,.2f} exceeds automatic approval limit (${self.approval_amount_threshold:,.2f}).",
                    approval_prompt=f"Approve recording invoice for {vendor} with high amount ${amount:,.2f}?"
                )

        # Check 3: Destructive database or filesystem operations
        if name == "database_query":
            query = params.get("query", "").strip().upper()
            if any(k in query for k in ("DROP", "DELETE", "TRUNCATE", "ALTER")):
                return SafetyDecision(
                    requires_approval=True,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Potentially destructive SQL statement detected: {query[:50]}...",
                    approval_prompt=f"Allow execution of database modification: {query}?"
                )

        if name == "file_delete":
            return SafetyDecision(
                requires_approval=True,
                risk_level=RiskLevel.HIGH,
                reason=f"Attempting to delete file: {params.get('file_path')}",
                approval_prompt=f"Approve deleting file {params.get('file_path')}?"
            )

        return SafetyDecision(requires_approval=False, risk_level=RiskLevel.LOW)

class HumanInteractionHandler:
    """
    Handles presenting approvals and clarification prompts to human operators
    via console, callback, or UI event queue.
    """
    def __init__(self, interactive: bool = True, default_auto_approve: bool = False):
        self.interactive = interactive
        self.default_auto_approve = default_auto_approve
        self.custom_prompt_callback: Optional[Callable[[str, str], bool]] = None
        self.custom_clarification_callback: Optional[Callable[[str, list], str]] = None

    def request_approval(self, prompt: str, reason: str, risk_level: RiskLevel) -> bool:
        if self.custom_prompt_callback:
            return self.custom_prompt_callback(prompt, reason)

        if not self.interactive:
            return self.default_auto_approve

        print("\n" + "=" * 60)
        print(f"⚠️  HUMAN APPROVAL REQUIRED [{risk_level.value.upper()} RISK]")
        print(f"Reason: {reason}")
        print(f"Prompt: {prompt}")
        print("=" * 60)
        try:
            choice = input("Authorize this action? [y/N]: ").strip().lower()
            return choice in ("y", "yes")
        except EOFError:
            return self.default_auto_approve

    def request_clarification(self, question: str, options: Optional[list] = None) -> str:
        if self.custom_clarification_callback:
            return self.custom_clarification_callback(question, options or [])

        if not self.interactive:
            return options[0] if options else "Proceed with default"

        print("\n" + "-" * 60)
        print(f"❓ CLARIFICATION NEEDED: {question}")
        if options:
            for idx, opt in enumerate(options, 1):
                print(f"  [{idx}] {opt}")
        print("-" * 60)
        try:
            res = input("Your answer: ").strip()
            if options and res.isdigit() and 1 <= int(res) <= len(options):
                return options[int(res) - 1]
            return res
        except EOFError:
            return options[0] if options else ""
