from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time
import uuid

class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_CLARIFICATION = "waiting_clarification"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Milestone(BaseModel):
    id: str = Field(default_factory=lambda: f"m_{uuid.uuid4().hex[:6]}")
    title: str
    description: str = ""
    status: MilestoneStatus = MilestoneStatus.PENDING
    success_condition: str = ""

class Plan(BaseModel):
    goal: str
    success_criteria: List[str] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    active_milestone_index: int = 0

    @property
    def current_milestone(self) -> Optional[Milestone]:
        if 0 <= self.active_milestone_index < len(self.milestones):
            return self.milestones[self.active_milestone_index]
        return None

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    tool_name: str
    status: str = "success"  # "success", "error", "retryable_error"
    data: Any = None
    error_message: Optional[str] = None
    side_effects: Optional[Dict[str, Any]] = None
    elapsed_ms: float = 0.0

class SafetyDecision(BaseModel):
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    reason: str = ""
    approval_prompt: Optional[str] = None
    approved: Optional[bool] = None

class VerificationCheck(BaseModel):
    check_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:6]}")
    description: str
    expected_outcome: str
    actual_outcome: str
    passed: bool
    evidence: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

class StepTrace(BaseModel):
    step_number: int
    milestone_id: Optional[str] = None
    milestone_title: Optional[str] = None
    thought: str
    action: ToolCall
    safety: SafetyDecision = Field(default_factory=SafetyDecision)
    observation: Optional[ToolResult] = None
    reflection: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

class TaskEvidenceBundle(BaseModel):
    task_id: str
    goal: str
    status: TaskStatus
    started_at: float
    completed_at: Optional[float] = None
    total_steps: int = 0
    retries_attempted: int = 0
    receipt_id: str = Field(default_factory=lambda: f"RCPT-{uuid.uuid4().hex[:8].upper()}")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    verifications: List[VerificationCheck] = Field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    summary_text: str = ""
