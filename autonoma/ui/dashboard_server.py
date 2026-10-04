from __future__ import annotations
import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from autonoma.config import settings
from autonoma.core.agent import AutonomousWorker
from autonoma.core.models import StepTrace, TaskStatus
from autonoma.environment.generator import seed_environment, init_database
from autonoma.environment.company_server import chaos_state

dashboard_app = FastAPI(title="Autonoma Live Control Center & Demo Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Shared in-memory run tracking and approval coordination
active_runs: Dict[str, Dict[str, Any]] = {}
pending_approvals: Dict[str, Dict[str, Any]] = {}

@dashboard_app.get("/api/drive/files")
def list_drive_files():
    files = []
    for p in settings.drive_dir.rglob("*"):
        if p.is_file():
            files.append({
                "name": p.name,
                "rel_path": str(p.relative_to(settings.drive_dir)),
                "size": p.stat().st_size,
                "type": p.suffix.lower()
            })
    return {"files": files}

@dashboard_app.get("/api/drive/view/{filename:path}")
def view_drive_file(filename: str):
    target = settings.drive_dir / filename
    if not target.exists():
        target = settings.drive_dir / "invoices" / filename
    if not target.exists():
        target = settings.drive_dir / "support" / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "application/pdf" if target.suffix.lower() == ".pdf" else None
    return FileResponse(str(target), media_type=media_type)

PRESET_SCENARIOS = [
    {
        "id": "scenario_invoice_happy",
        "title": "Scenario 1: Baseline Invoice Entry & Self-Verification",
        "prompt": "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.",
        "description": "Standard prompt workflow. Discovers files, chooses latest (Oct vs Aug), extracts fields, fills ERP form, actively asserts ledger integrity, and issues proof receipt."
    },
    {
        "id": "scenario_error_recovery",
        "title": "Scenario 2: Flaky Service & Adaptive Fallback",
        "prompt": "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.",
        "chaos": True,
        "description": "Simulates 503 transient web error and UI drift. Agent detects failure, executes exponential backoff retry and falls back to backend REST API."
    },
    {
        "id": "scenario_hitl_approval",
        "title": "Scenario 3: High-Value Financial Safety Gate (HITL)",
        "prompt": "Find the invoice from Apex Systems, extract the amount and due date, and record it into our internal system.",
        "description": "Invoice amount is $14,500 (exceeds $10k threshold). Agent pauses and prompts human manager for explicit approval before writing."
    },
    {
        "id": "scenario_ambiguity",
        "title": "Scenario 4: Ambiguity Detection & Clarification",
        "prompt": "Find the invoice from Acme, extract amount and due date, and enter it into our internal system.",
        "description": "Multiple Acme entities exist (Acme Widgets Ltd vs Acme Logistics Inc). Agent halts, detects ambiguity, and queries human for clarification."
    },
    {
        "id": "scenario_generalization_support",
        "title": "Scenario 5: Generalization - Customer Dispute Resolution",
        "prompt": "Review customer ticket #201 for Globex Corporation, audit their account balance, apply the credit adjustment, and resolve the ticket.",
        "description": "Proves architectural generalization across a totally different domain (Customer Support Ledger & Credit Memos) without code changes."
    }
]

@dashboard_app.get("/api/scenarios")
def get_scenarios():
    return {"scenarios": PRESET_SCENARIOS}

class RunTaskRequest(BaseModel):
    goal: str
    scenario_id: Optional[str] = None
    chaos_mode: bool = False
    interactive: bool = False
    auto_approve: bool = True

@dashboard_app.post("/api/run")
def trigger_run(payload: RunTaskRequest):
    run_id = f"run_{uuid.uuid4().hex[:6]}"
    
    # Configure chaos mode if requested
    if payload.chaos_mode or payload.scenario_id == "scenario_error_recovery":
        chaos_state["flaky_api"] = True
        chaos_state["flaky_counter"] = 0
    else:
        chaos_state["flaky_api"] = False

    steps_recorded: List[Dict[str, Any]] = []

    def on_step(trace: StepTrace):
        steps_recorded.append({
            "step_number": trace.step_number,
            "milestone": trace.milestone_title,
            "thought": trace.thought,
            "action": trace.action.model_dump(),
            "safety": trace.safety.model_dump(),
            "observation": trace.observation.model_dump() if trace.observation else None,
            "reflection": trace.reflection,
            "timestamp": trace.timestamp
        })

    worker = AutonomousWorker(
        interactive_human=payload.interactive,
        default_auto_approve=payload.auto_approve,
        on_step_callback=on_step
    )

    bundle = worker.run(payload.goal, task_id=run_id)

    # Reset chaos state after run
    chaos_state["flaky_api"] = False

    return {
        "run_id": run_id,
        "bundle": bundle.model_dump(),
        "steps": steps_recorded
    }

@dashboard_app.post("/api/reset")
def reset_environment():
    import sqlite3
    conn = sqlite3.connect(str(settings.db_path))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM erp_invoices")
    cursor.execute("DELETE FROM erp_audit_log")
    conn.commit()
    conn.close()

    seed_environment()
    chaos_state["flaky_api"] = False
    chaos_state["flaky_counter"] = 0
    return {"status": "success", "message": "Environment re-seeded with fresh invoices and clean database"}

@dashboard_app.get("/api/erp/state")
def get_erp_state():
    import sqlite3
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_invoices ORDER BY id DESC")
    invoices = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM erp_audit_log ORDER BY id DESC LIMIT 15")
    logs = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM support_tickets ORDER BY id DESC")
    tickets = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM customer_ledger")
    ledger = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "invoices": invoices,
        "audit_logs": logs,
        "tickets": tickets,
        "ledger": ledger
    }

# Mount static files
dashboard_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@dashboard_app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Autonoma Dashboard Loading...</h1>")
