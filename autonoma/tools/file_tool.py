from __future__ import annotations
from pathlib import Path
import re
import json
import time
from typing import Any, Dict, List, Optional
from pypdf import PdfReader

from autonoma.config import settings
from autonoma.tools.base import BaseTool
from autonoma.core.models import ToolResult

def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    # Check drive_dir first, then project root
    in_drive = settings.drive_dir / p
    if in_drive.exists():
        return in_drive
    in_proj = settings.project_root / p
    if in_proj.exists():
        return in_proj
    # Default to drive_dir
    return in_drive

class FileListTool(BaseTool):
    name = "file_list"
    description = "Lists files in a directory matching an optional pattern (e.g. *.pdf, *.json)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Relative or absolute directory path"},
            "pattern": {"type": "string", "description": "Glob pattern like '*.pdf' or '*.*'", "default": "*"}
        },
        "required": ["directory"]
    }

    def execute(self, directory: str = "", pattern: str = "*", **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_dir = _resolve_path(directory) if directory else settings.drive_dir
            if not target_dir.exists() or not target_dir.is_dir():
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"Directory '{directory}' does not exist or is not a directory.",
                    elapsed_ms=(time.time() - start_time) * 1000
                )
            
            files = []
            for item in target_dir.glob(pattern):
                if item.is_file():
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item.relative_to(settings.project_root) if item.is_relative_to(settings.project_root) else item),
                        "size_bytes": stat.st_size,
                        "modified_at": stat.st_mtime
                    })

            # Sort by modified time descending (newest first)
            files.sort(key=lambda x: x["modified_at"], reverse=True)

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={"files": files, "count": len(files), "directory": str(target_dir)},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=str(e),
                elapsed_ms=(time.time() - start_time) * 1000
            )

class FileReadTool(BaseTool):
    name = "file_read"
    description = "Reads content of a file (supports TXT, JSON, CSV, MD, and PDF)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative or absolute path to file"}
        },
        "required": ["file_path"]
    }

    def execute(self, file_path: str, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_file = _resolve_path(file_path)
            if not target_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"File not found: {file_path}",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # Handle PDF
            if target_file.suffix.lower() == ".pdf":
                reader = PdfReader(str(target_file))
                text_pages = [page.extract_text() or "" for page in reader.pages]
                full_text = "\n--- PAGE BREAK ---\n".join(text_pages)
                return ToolResult(
                    tool_name=self.name,
                    status="success",
                    data={
                        "type": "pdf",
                        "pages": len(reader.pages),
                        "content": full_text
                    },
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # Handle JSON
            if target_file.suffix.lower() == ".json":
                with open(target_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                return ToolResult(
                    tool_name=self.name,
                    status="success",
                    data={"type": "json", "content": content},
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # Handle Text / CSV / MD
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={"type": "text", "content": content},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=str(e),
                elapsed_ms=(time.time() - start_time) * 1000
            )

class FileSearchTool(BaseTool):
    name = "file_search"
    description = "Searches for query strings or vendor names across files in a directory."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword (e.g. vendor name, invoice)"},
            "directory": {"type": "string", "description": "Directory to search within", "default": "data/sample_drive"}
        },
        "required": ["query"]
    }

    def execute(self, query: str, directory: str = "data/sample_drive", **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_dir = _resolve_path(directory)
            matches = []
            query_lower = query.lower()

            for item in target_dir.rglob("*"):
                if not item.is_file():
                    continue

                # Check filename
                if query_lower in item.name.lower():
                    matches.append({
                        "file_name": item.name,
                        "path": str(item.relative_to(settings.project_root) if item.is_relative_to(settings.project_root) else item),
                        "match_type": "filename",
                        "snippet": item.name
                    })
                    continue

                # Check content for text / json / pdf
                try:
                    if item.suffix.lower() == ".pdf":
                        reader = PdfReader(str(item))
                        for idx, page in enumerate(reader.pages):
                            txt = page.extract_text() or ""
                            if query_lower in txt.lower():
                                matches.append({
                                    "file_name": item.name,
                                    "path": str(item.relative_to(settings.project_root) if item.is_relative_to(settings.project_root) else item),
                                    "match_type": "content_pdf",
                                    "page": idx + 1,
                                    "snippet": txt[:200]
                                })
                                break
                    elif item.suffix.lower() in (".txt", ".json", ".csv", ".md"):
                        with open(item, "r", encoding="utf-8", errors="ignore") as f:
                            txt = f.read()
                            if query_lower in txt.lower():
                                matches.append({
                                    "file_name": item.name,
                                    "path": str(item.relative_to(settings.project_root) if item.is_relative_to(settings.project_root) else item),
                                    "match_type": "content_text",
                                    "snippet": txt[:200]
                                })
                except Exception:
                    continue

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={"matches": matches, "count": len(matches), "query": query},
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=str(e),
                elapsed_ms=(time.time() - start_time) * 1000
            )

class InvoiceExtractTool(BaseTool):
    name = "invoice_extract"
    description = "Parses financial details from an invoice file (amount, due date, invoice number, vendor)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to invoice file (PDF, TXT, or JSON)"}
        },
        "required": ["file_path"]
    }

    def execute(self, file_path: str, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            target_file = _resolve_path(file_path)
            if not target_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    error_message=f"File not found: {file_path}",
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # JSON invoice format
            if target_file.suffix.lower() == ".json":
                with open(target_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ToolResult(
                    tool_name=self.name,
                    status="success",
                    data={
                        "invoice_number": data.get("invoice_number", data.get("id", "UNKNOWN")),
                        "vendor": data.get("vendor", data.get("company", "UNKNOWN")),
                        "amount": float(data.get("amount", data.get("total_amount", 0.0))),
                        "due_date": data.get("due_date", ""),
                        "issue_date": data.get("issue_date", data.get("date", "")),
                        "currency": data.get("currency", "USD"),
                        "raw_file": str(target_file.name)
                    },
                    elapsed_ms=(time.time() - start_time) * 1000
                )

            # PDF / Text format
            content = ""
            if target_file.suffix.lower() == ".pdf":
                reader = PdfReader(str(target_file))
                content = "\n".join([page.extract_text() or "" for page in reader.pages])
            else:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()

            # Robust Regex Extractors
            # Amount: e.g. Total: $4,850.00 or Amount Due: 4850.00 or $12,450.00
            amount = 0.0
            amount_matches = re.findall(r"(?:Total|Amount|Balance Due|Total Due)[\s:]*\$?([0-9,]+\.[0-9]{2})", content, re.IGNORECASE)
            if not amount_matches:
                amount_matches = re.findall(r"\$([0-9,]+\.[0-9]{2})", content)
            if amount_matches:
                amount = float(amount_matches[-1].replace(",", ""))

            # Due Date: e.g. Due Date: 2024-11-15 or Due: Nov 15, 2024
            due_date = ""
            due_match = re.search(r"(?:Due Date|Payment Due|Due)[\s:]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]+ \d{1,2}, \d{4}|\d{2}/\d{2}/\d{4})", content, re.IGNORECASE)
            if due_match:
                due_date = due_match.group(1).strip()

            # Invoice Number
            inv_num = "INV-UNKNOWN"
            inv_match = re.search(r"(?:Invoice\s*(?:#|Number|No\.|ID))[\s:]*([A-Za-z0-9\-]+)", content, re.IGNORECASE)
            if inv_match:
                inv_num = inv_match.group(1).strip()

            # Vendor
            vendor = "Unknown Vendor"
            # Check top header e.g. "ACME CORP INVOICE"
            top_header_match = re.search(r"^\s*([A-Za-z0-9\s]+?)\s+INVOICE", content, re.IGNORECASE | re.MULTILINE)
            if top_header_match and len(top_header_match.group(1).strip()) > 2:
                vendor = top_header_match.group(1).strip().title()
            else:
                vendor_match = re.search(r"(?:Vendor|Billed By|From)[\s:]*([A-Za-z0-9\s]+?)(?:\n|$)", content, re.IGNORECASE)
                if vendor_match:
                    vendor = vendor_match.group(1).strip()
                else:
                    # Infer from filename if possible
                    fn = target_file.stem.replace("_", " ")
                    vendor = fn.split("invoice")[0].strip() or "Acme Corp"

            return ToolResult(
                tool_name=self.name,
                status="success",
                data={
                    "invoice_number": inv_num,
                    "vendor": vendor,
                    "amount": amount,
                    "due_date": due_date,
                    "raw_file": str(target_file.name),
                    "confidence": "high" if (amount > 0 and due_date) else "medium"
                },
                elapsed_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                error_message=str(e),
                elapsed_ms=(time.time() - start_time) * 1000
            )
