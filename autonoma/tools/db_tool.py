from __future__ import annotations
import sqlite3
import time
from typing import Any, Dict, List, Optional

from autonoma.config import settings
from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolResult

class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = "Executes a SELECT query against the internal company SQLite database to inspect records and state."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "SQL SELECT query (e.g. 'SELECT * FROM erp_invoices ORDER BY id DESC LIMIT 5')"}
        },
        "required": ["query"]
    }

    def execute(self, query: str, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            db_path = settings.db_path
            if not db_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"Database file not found at {db_path}",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # Safety check: block unauthorized writes via raw query unless read-only
            cleaned = query.strip().upper()
            if not cleaned.startswith("SELECT") and not cleaned.startswith("PRAGMA"):
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message="Only SELECT or PRAGMA queries are allowed through database_query tool.",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            data = [dict(zip(columns, row)) for row in rows]
            conn.close()

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={
                    "row_count": len(data),
                    "rows": data
                },
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=f"Database query failed: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )
