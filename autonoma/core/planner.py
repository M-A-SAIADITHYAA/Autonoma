from __future__ import annotations
from typing import Any, Dict, List, Optional
import re
from autonoma.core.models import Plan, Milestone, MilestoneStatus

class Planner:
    """
    Decomposes high-level user instructions into structured milestones
    with success criteria and dynamic adaptation capabilities.
    """

    @classmethod
    def create_initial_plan(cls, goal: str) -> Plan:
        goal_lower = goal.lower()
        milestones: List[Milestone] = []
        success_criteria: List[str] = []

        # Case 1: Invoice Processing / ERP Data Entry
        if "invoice" in goal_lower:
            vendor_match = re.search(r"(?:from|for)\s+([A-Za-z0-9\s]+?)(?:,|\.|\sand\s|$)", goal, re.IGNORECASE)
            vendor = vendor_match.group(1).strip() if vendor_match else "specified company"

            milestones = [
                Milestone(
                    title="Locate Latest Invoice",
                    description=f"Search files and incoming document directory for latest invoice from {vendor}",
                    success_condition="Identified target invoice file path and metadata"
                ),
                Milestone(
                    title="Extract Financial Data",
                    description="Read invoice file and extract amount, due date, and invoice number",
                    success_condition="Amount and due date extracted and saved to working memory"
                ),
                Milestone(
                    title="Safety & Compliance Assessment",
                    description="Evaluate approval rules (e.g., threshold limits) and human approval requirements",
                    success_condition="Safety check passed or human approval obtained if required"
                ),
                Milestone(
                    title="Submit to Internal Company ERP",
                    description="Access internal ERP portal or API to record the extracted invoice",
                    success_condition="ERP record successfully submitted and status code OK"
                ),
                Milestone(
                    title="Verify Outcome & Compile Evidence",
                    description="Query ERP database/audit log to confirm record matches extracted values and generate receipt",
                    success_condition="Independent verification passed with cryptographic proof"
                )
            ]
            success_criteria = [
                f"Invoice for {vendor} located",
                "Amount and due date accurately parsed",
                "Invoice registered in internal ERP system",
                "Outcome independently verified in company records"
            ]

        # Case 2: Customer Support Ticket & Billing Resolution
        elif "ticket" in goal_lower or "dispute" in goal_lower:
            milestones = [
                Milestone(
                    title="Lookup Support Ticket",
                    description="Query support queue for customer dispute details",
                    success_condition="Ticket retrieved and discrepancy identified"
                ),
                Milestone(
                    title="Audit Customer Ledger",
                    description="Check customer billing balance and ledger history in company database",
                    success_condition="Ledger balances extracted"
                ),
                Milestone(
                    title="Apply Credit Memo or Adjustment",
                    description="Post adjustment in billing system and update ticket status",
                    success_condition="Credit adjustment posted"
                ),
                Milestone(
                    title="Verify Ledger & Notify Outcome",
                    description="Verify updated customer balance matches expected adjustment",
                    success_condition="Ledger verified"
                )
            ]
            success_criteria = [
                "Dispute ticket analyzed",
                "Customer ledger reviewed",
                "Adjustment recorded",
                "Outcome verified"
            ]

        # Case 3: Employee Onboarding / Access Provisioning
        elif "onboard" in goal_lower or "employee" in goal_lower:
            milestones = [
                Milestone(
                    title="Read Onboarding Request",
                    description="Extract employee info and designated department/role from directory",
                    success_condition="Employee record parsed"
                ),
                Milestone(
                    title="Provision Internal Services",
                    description="Submit user creation to HR portal and internal directory",
                    success_condition="User account created"
                ),
                Milestone(
                    title="Verify Access & Permissions",
                    description="Confirm active user profile in database",
                    success_condition="Account active in system"
                )
            ]
            success_criteria = [
                "Employee data parsed",
                "Account created with proper roles",
                "Verification completed"
            ]

        # Case 4: General Purpose Adaptive Goal
        else:
            milestones = [
                Milestone(
                    title="Explore & Gather Context",
                    description="Inspect environment, files, or applications to locate necessary data",
                    success_condition="Context gathered"
                ),
                Milestone(
                    title="Execute Core Action",
                    description="Perform requested modifications or data entry",
                    success_condition="Action executed"
                ),
                Milestone(
                    title="Verify Target Outcome",
                    description="Confirm target system reflects desired state",
                    success_condition="System state verified"
                )
            ]
            success_criteria = [
                "Target resources accessed",
                "Actions executed",
                "Outcome validated"
            ]

        # Set first milestone to IN_PROGRESS
        if milestones:
            milestones[0].status = MilestoneStatus.IN_PROGRESS

        return Plan(
            goal=goal,
            success_criteria=success_criteria,
            milestones=milestones,
            active_milestone_index=0
        )

    @classmethod
    def adapt_plan(cls, plan: Plan, trigger_reason: str, new_milestones: List[Milestone]) -> Plan:
        """Dynamically inserts or modifies milestones based on newly discovered execution facts."""
        curr_idx = plan.active_milestone_index
        plan.milestones = plan.milestones[:curr_idx + 1] + new_milestones + plan.milestones[curr_idx + 1:]
        return plan
