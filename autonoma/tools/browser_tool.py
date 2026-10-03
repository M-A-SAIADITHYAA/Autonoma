from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from autonoma.config import settings
from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolResult

class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Navigates to a URL (e.g. internal ERP portal) and extracts page title, text, forms, and interactive elements."
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL or relative path (e.g. '/erp/invoices' or 'http://127.0.0.1:8000/erp')"}
        },
        "required": ["url"]
    }

    def execute(self, url: str, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_url = url if url.startswith("http") else urljoin(settings.company_base_url, url)
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(target_url)

            if resp.status_code >= 400:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"HTTP Error {resp.status_code} while navigating to {target_url}: {resp.text[:200]}",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else "No Title"

            # Extract forms
            forms = []
            for f in soup.find_all("form"):
                inputs = []
                for inp in f.find_all(["input", "select", "textarea"]):
                    inputs.append({
                        "name": inp.get("name"),
                        "type": inp.get("type", "text"),
                        "value": inp.get("value", ""),
                        "placeholder": inp.get("placeholder", "")
                    })
                forms.append({
                    "action": f.get("action", ""),
                    "method": f.get("method", "GET").upper(),
                    "inputs": inputs
                })

            # Extract links
            links = []
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text:
                    links.append({"text": text, "href": a["href"]})

            # Extract visible text summary
            # Strip script and style
            for s in soup(["script", "style"]):
                s.decompose()
            body_text = soup.get_text(separator=" ", strip=True)

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={
                    "url": str(resp.url),
                    "status_code": resp.status_code,
                    "title": title,
                    "forms": forms,
                    "links": links[:15],
                    "text_preview": body_text[:1200]
                },
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=f"Browser navigation failed: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )

class BrowserFillFormTool(BaseTool):
    name = "browser_fill_form"
    description = "Fills out and submits an HTML form on the company portal with specified fields."
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Page URL containing the form or action URL"},
            "form_data": {"type": "object", "description": "Key-value dictionary of form field names and values"}
        },
        "required": ["url", "form_data"]
    }

    def execute(self, url: str, form_data: Dict[str, Any], **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_url = url if url.startswith("http") else urljoin(settings.company_base_url, url)
            
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                # 1. First GET page to discover form action and hidden CSRF tokens if any
                get_resp = client.get(target_url)
                soup = BeautifulSoup(get_resp.text, "html.parser")
                form = soup.find("form")
                
                post_url = target_url
                payload = dict(form_data)
                
                if form:
                    action = form.get("action")
                    if action:
                        post_url = urljoin(str(get_resp.url), action)
                    # Include hidden inputs
                    for inp in form.find_all("input", type="hidden"):
                        name = inp.get("name")
                        val = inp.get("value", "")
                        if name and name not in payload:
                            payload[name] = val

                # 2. Submit form
                resp = client.post(post_url, data=payload)

            if resp.status_code >= 400:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"Form submission failed with HTTP {resp.status_code}: {resp.text[:300]}",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # Check if response is JSON or HTML
            try:
                res_data = resp.json()
            except Exception:
                res_soup = BeautifulSoup(resp.text, "html.parser")
                res_data = {
                    "title": res_soup.title.string if res_soup.title else "",
                    "text": res_soup.get_text(separator=" ", strip=True)[:500]
                }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={
                    "submitted_to": post_url,
                    "payload_keys": list(payload.keys()),
                    "response": res_data
                },
                side_effects={"form_submitted": True, "target": post_url},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=f"Form fill error: {str(e)}",
                elapsed_ms=(time.time() - start_time) * 1000
            )
