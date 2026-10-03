from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolCall, ToolResult

class ToolRegistry:
    """Central registry and execution dispatcher for all agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema
            }
            for t in self._tools.values()
        ]

    def execute(self, tool_call: ToolCall) -> ToolResult:
        tool = self._tools.get(tool_call.tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status="error",
                error_message=f"Tool '{tool_call.tool_name}' is not registered. Available tools: {list(self._tools.keys())}",
                elapsed_ms=0.0
            )

        start_time = time.time()
        try:
            return tool.execute(**tool_call.parameters)
        except Exception as e:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status="error",
                error_message=f"Unhandled exception during tool execution: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )
