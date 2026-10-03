from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel
from autonoma.core.models import ToolResult

class BaseTool(ABC):
    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
