from __future__ import annotations
from typing import Any, Dict, Optional
import time
import httpx
from urllib.parse import urljoin

from autonoma.config import settings
from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolResult

class ApiTool(BaseTool):
    name = "api_call"
    description = "Executes an HTTP REST API request (GET, POST, PUT, DELETE) against the company backend."
    parameters_schema = {
        "type": "object",
        "properties": {
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            "endpoint": {"type": "string", "description": "Relative endpoint (e.g. '/api/v1/erp/invoices') or full URL"},
            "payload": {"type": "object", "description": "JSON payload body (for POST/PUT)"},
            "headers": {"type": "object", "description": "Optional HTTP headers"}
        },
        "required": ["endpoint"]
    }

    def execute(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ToolResult:
        start_time = time.time()
        try:
            target_url = endpoint if endpoint.startswith("http") else urljoin(settings.company_base_url, endpoint)
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)

            with httpx.Client(timeout=10.0) as client:
                resp = client.request(
                    method=method.upper(),
                    url=target_url,
                    json=payload if payload is not None else None,
                    headers=req_headers
                )

            is_error = resp.status_code >= 400
            try:
                body = resp.json()
            except Exception:
                body = resp.text

            if is_error:
                status_category = "retryable_error" if resp.status_code in (500, 502, 503, 504, 429) else "error"
                return ToolResult(
                    tool_name=self.name,
                    status=status_category,
                    error_message=f"API request {method} {target_url} failed with HTTP {resp.status_code}: {str(body)[:300]}",
                    data={"status_code": resp.status_code, "response": body},
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={
                    "status_code": resp.status_code,
                    "response": body
                },
                side_effects={"api_executed": True, "method": method, "endpoint": target_url},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="retryable_error" if "connection" in str(e).lower() else "error",
                error_message=f"API request failed: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )
