from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import copy

from autonoma.core.models import StepTrace, Plan, MilestoneStatus, TaskStatus

class AgentMemory(BaseModel):
    task_id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    plan: Optional[Plan] = None
    step_history: List[StepTrace] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    errors_encountered: List[Dict[str, Any]] = Field(default_factory=list)
    user_inputs: List[Dict[str, Any]] = Field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)

    def record_step(self, step: StepTrace) -> None:
        self.step_history.append(step)

    def set_entity(self, key: str, value: Any) -> None:
        self.entities[key] = value

    def get_entity(self, key: str, default: Any = None) -> Any:
        return self.entities.get(key, default)

    def set_scratchpad(self, key: str, value: Any) -> None:
        self.scratchpad[key] = value

    def get_scratchpad(self, key: str, default: Any = None) -> Any:
        return self.scratchpad.get(key, default)

    def record_error(self, step_number: int, tool_name: str, error_message: str, recovery_strategy: str) -> None:
        self.errors_encountered.append({
            "step": step_number,
            "tool": tool_name,
            "error": error_message,
            "recovery_strategy": recovery_strategy
        })

    def record_user_input(self, prompt: str, response: Any, input_type: str = "approval") -> None:
        self.user_inputs.append({
            "type": input_type,
            "prompt": prompt,
            "response": response
        })

    def advance_milestone(self, success: bool = True) -> None:
        if not self.plan:
            return
        curr = self.plan.current_milestone
        if curr:
            curr.status = MilestoneStatus.COMPLETED if success else MilestoneStatus.FAILED
        self.plan.active_milestone_index += 1
        new_curr = self.plan.current_milestone
        if new_curr:
            new_curr.status = MilestoneStatus.IN_PROGRESS

    def save_checkpoint(self, name: str) -> None:
        self.checkpoints.append({
            "name": name,
            "entities": copy.deepcopy(self.entities),
            "scratchpad": copy.deepcopy(self.scratchpad),
            "step_count": len(self.step_history),
            "plan_index": self.plan.active_milestone_index if self.plan else 0
        })

    def get_recent_history_summary(self, max_steps: int = 5) -> str:
        recent = self.step_history[-max_steps:]
        if not recent:
            return "No previous steps executed yet."
        summary = []
        for s in recent:
            status_desc = "SUCCESS" if (s.observation and s.observation.status == "success") else "FAILED"
            summary.append(
                f"- Step {s.step_number} [{s.action.tool_name}]: {status_desc} | "
                f"Thought: {s.thought[:90]}... | "
                f"Obs: {str(s.observation.data)[:100] if s.observation else 'None'}"
            )
        return "\n".join(summary)
