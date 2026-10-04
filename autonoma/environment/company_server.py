from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from autonoma.config import settings
from autonoma.environment.generator import init_database

app = FastAPI(title="Company Internal ERP & Operations Portal", version="1.0.0")

# State for chaos testing
chaos_state = {
    "flaky_api": False,
    "flaky_counter": 0,
    "ui_drift": False
}

def get_db():
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def on_startup():
    init_database()

# =========================================================================
# HTML UI Views (For browser_navigate and browser_fill_form)
# =========================================================================

@app.get("/", response_class=HTMLResponse)
@app.get("/erp", response_class=HTMLResponse)
def view_erp_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_invoices ORDER BY id DESC")
    invoices = cursor.fetchall()

    cursor.execute("SELECT * FROM erp_audit_log ORDER BY id DESC LIMIT 10")
    audit_logs = cursor.fetchall()
    conn.close()

    rows_html = "".join([
        f"""
        <tr class="border-b hover:bg-slate-50">
            <td class="p-3 font-mono text-sm">#{row['id']}</td>
            <td class="p-3 font-semibold">{row['invoice_number']}</td>
            <td class="p-3">{row['vendor']}</td>
            <td class="p-3 font-mono font-medium text-emerald-700">${row['amount']:,.2f}</td>
            <td class="p-3 text-slate-600">{row['due_date']}</td>
            <td class="p-3"><span class="px-2 py-1 text-xs rounded-full bg-amber-100 text-amber-800 font-medium">{row['status']}</span></td>
            <td class="p-3 text-xs text-slate-400">{row['created_at']}</td>
        </tr>
        """ for row in invoices
    ]) if invoices else """<tr><td colspan="7" class="p-6 text-center text-slate-500 italic">No invoices registered yet in the system. Use the form to record one.</td></tr>"""

    audit_html = "".join([
        f"""
        <li class="py-2 border-b border-slate-100 flex items-center justify-between text-xs">
            <span><strong class="text-indigo-600">[{log['action']}]</strong> {log['details']}</span>
            <span class="text-slate-400">{log['timestamp']}</span>
        </li>
        """ for log in audit_logs
    ]) if audit_logs else "<li class='py-2 text-xs text-slate-400'>No recent activity.</li>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Internal Company Portal - Finance ERP</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 text-slate-800 min-h-screen">
        <header class="bg-slate-900 text-white px-8 py-4 shadow-md flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <span class="text-2xl font-black tracking-wider text-indigo-400">CORP-NET</span>
                <span class="text-xs bg-slate-800 px-2.5 py-1 rounded border border-slate-700 text-slate-300">Internal Enterprise ERP</span>
            </div>
            <nav class="flex items-center space-x-6 text-sm font-medium">
                <a href="/erp" class="text-indigo-400 border-b-2 border-indigo-400 pb-1">Finance ERP</a>
                <a href="/erp/invoices/new" class="text-slate-300 hover:text-white transition">Record Invoice</a>
                <a href="/support/tickets" class="text-slate-300 hover:text-white transition">Support Desk</a>
                <a href="http://127.0.0.1:8080" class="bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-90 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow flex items-center transition">
                    🤖 AI Task Worker Dashboard (:8080) &rarr;
                </a>
            </nav>
        </header>

        <main class="max-w-6xl mx-auto p-8 space-y-8">
            <div class="flex justify-between items-center">
                <div>
                    <h1 class="text-2xl font-bold text-slate-900">Accounts Payable & Invoice Registry</h1>
                    <p class="text-sm text-slate-500">Live records in internal accounting ledger</p>
                </div>
                <div class="space-x-3">
                    <a href="/erp/invoices/new" id="btn-new-invoice" class="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2.5 rounded-lg shadow transition inline-flex items-center">
                        + Record New Invoice
                    </a>
                </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div class="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
                    <h2 class="font-semibold text-slate-700 text-sm">Registered Invoices ({len(invoices)})</h2>
                    <span class="text-xs text-slate-400">Refreshed live from SQLite ledger</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-50 text-xs font-semibold text-slate-500 uppercase border-b">
                            <tr>
                                <th class="p-3">ID</th>
                                <th class="p-3">Invoice #</th>
                                <th class="p-3">Vendor</th>
                                <th class="p-3">Amount</th>
                                <th class="p-3">Due Date</th>
                                <th class="p-3">Status</th>
                                <th class="p-3">Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
                <h3 class="font-semibold text-sm text-slate-700 uppercase tracking-wider">System Audit Trail</h3>
                <ul class="space-y-1">{audit_html}</ul>
            </div>
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/erp/invoices/new", response_class=HTMLResponse)
def view_invoice_form():
    csrf_token = f"csrf_{int(time.time())}_internal"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Record Invoice - Internal ERP</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 text-slate-800 min-h-screen">
        <header class="bg-slate-900 text-white px-8 py-4 shadow-md flex justify-between items-center">
            <a href="/erp" class="text-xl font-bold text-indigo-400">CORP-NET ERP</a>
            <a href="/erp" class="text-sm text-slate-300 hover:text-white">&larr; Back to Dashboard</a>
        </header>

        <main class="max-w-xl mx-auto p-8">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-6">
                <div>
                    <h1 class="text-xl font-bold text-slate-900">Record Incoming Invoice</h1>
                    <p class="text-xs text-slate-500">Enter invoice details for accounts payable review</p>
                </div>

                <form id="invoice-entry-form" action="/erp/invoices/new" method="POST" class="space-y-4">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">

                    <div>
                        <label class="block text-xs font-semibold text-slate-700 uppercase mb-1">Vendor / Company</label>
                        <input type="text" name="vendor" required placeholder="e.g. Acme Corp" class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-700 uppercase mb-1">Invoice Number</label>
                        <input type="text" name="invoice_number" required placeholder="e.g. ACME-9104" class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-slate-700 uppercase mb-1">Total Amount ($)</label>
                            <input type="number" step="0.01" name="amount" required placeholder="5240.00" class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-700 uppercase mb-1">Payment Due Date</label>
                            <input type="text" name="due_date" required placeholder="YYYY-MM-DD" class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-700 uppercase mb-1">Notes / Description</label>
                        <textarea name="notes" rows="2" placeholder="Extracted by autonomous agent..." class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"></textarea>
                    </div>

                    <button type="submit" id="btn-submit-invoice" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-lg shadow transition">
                        Submit Invoice Record
                    </button>
                </form>
            </div>
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/erp/invoices/new", response_class=HTMLResponse)
def handle_form_submit(
    vendor: str = Form(...),
    invoice_number: str = Form(...),
    amount: float = Form(...),
    due_date: str = Form(...),
    notes: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None)
):
    # Chaos failure check
    if chaos_state["flaky_api"]:
        chaos_state["flaky_counter"] += 1
        if chaos_state["flaky_counter"] % 2 == 1:
            raise HTTPException(status_code=503, detail="Simulated Flaky Service Glitch: 503 Service Unavailable")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO erp_invoices (invoice_number, vendor, amount, due_date, status, source, notes)
    VALUES (?, ?, ?, ?, 'pending_review', 'web_form', ?)
    """, (invoice_number, vendor, amount, due_date, notes or "Submitted via web form"))
    inv_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO erp_audit_log (action, entity_type, entity_id, details, actor)
    VALUES ('CREATE_INVOICE_FORM', 'erp_invoices', ?, ?, 'web_user')
    """, (inv_id, f"Registered invoice {invoice_number} for {vendor} (${amount:,.2f})"))
    conn.commit()
    conn.close()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice Registered - Success</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 flex items-center justify-center min-h-screen">
        <div class="bg-white p-8 rounded-xl shadow-md border border-slate-200 max-w-md text-center space-y-4">
            <div class="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto text-xl font-bold">✓</div>
            <h1 class="text-xl font-bold text-slate-800">Invoice Successfully Recorded</h1>
            <p class="text-sm text-slate-600">Invoice <strong class="text-indigo-600">{invoice_number}</strong> for <strong class="text-slate-800">{vendor}</strong> registered under ID <strong>#{inv_id}</strong>.</p>
            <div class="bg-slate-50 p-3 rounded text-xs font-mono text-slate-700 text-left">
                Amount: ${amount:,.2f}<br>
                Due Date: {due_date}<br>
                Status: pending_review
            </div>
            <a href="/erp" class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-6 py-2.5 rounded-lg transition">Back to Invoices</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# =========================================================================
# REST API Endpoints (For programmatic tool calls & verification assertions)
# =========================================================================

class InvoiceCreatePayload(BaseModel):
    vendor: str
    invoice_number: str
    amount: float
    due_date: str
    notes: Optional[str] = "Registered via API"

@app.get("/api/v1/erp/invoices")
def api_list_invoices(vendor: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if vendor:
        cursor.execute("SELECT * FROM erp_invoices WHERE LOWER(vendor) LIKE ? ORDER BY id DESC", (f"%{vendor.lower()}%",))
    else:
        cursor.execute("SELECT * FROM erp_invoices ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return {"status": "success", "count": len(rows), "invoices": [dict(r) for r in rows]}

@app.post("/api/v1/erp/invoices")
def api_create_invoice(payload: InvoiceCreatePayload):
    if chaos_state["flaky_api"]:
        chaos_state["flaky_counter"] += 1
        if chaos_state["flaky_counter"] % 2 == 1:
            raise HTTPException(status_code=503, detail="Simulated Flaky Service Glitch: 503 Service Temporarily Unavailable")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO erp_invoices (invoice_number, vendor, amount, due_date, status, source, notes)
    VALUES (?, ?, ?, ?, 'pending_review', 'rest_api', ?)
    """, (payload.invoice_number, payload.vendor, payload.amount, payload.due_date, payload.notes))
    inv_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO erp_audit_log (action, entity_type, entity_id, details, actor)
    VALUES ('CREATE_INVOICE_API', 'erp_invoices', ?, ?, 'api_agent')
    """, (inv_id, f"API Record invoice {payload.invoice_number} for {payload.vendor} (${payload.amount:,.2f})"))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "invoice_id": inv_id,
        "invoice_number": payload.invoice_number,
        "vendor": payload.vendor,
        "amount": payload.amount,
        "due_date": payload.due_date,
        "status_code": 201,
        "message": "Invoice successfully registered in ERP system"
    }

@app.get("/api/v1/erp/audit-log")
def api_audit_log(limit: int = 20):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_audit_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return {"status": "success", "audit_log": [dict(r) for r in rows]}

# =========================================================================
# Support Portal & Customer Ledger (For Generalization Test)
# =========================================================================

@app.get("/support/tickets", response_class=HTMLResponse)
def view_support_tickets():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_tickets ORDER BY id DESC")
    tickets = cursor.fetchall()
    cursor.execute("SELECT * FROM customer_ledger")
    ledgers = cursor.fetchall()
    conn.close()

    tickets_rows = "".join([
        f"""
        <tr class="border-b">
            <td class="p-3 font-mono font-bold text-indigo-600">{t['ticket_id']}</td>
            <td class="p-3">{t['customer_name']}</td>
            <td class="p-3 font-medium">{t['issue_type']}</td>
            <td class="p-3 text-red-600 font-semibold">${t['disputed_amount']:,.2f}</td>
            <td class="p-3"><span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">{t['status']}</span></td>
            <td class="p-3 text-xs text-slate-500">{t['description']}</td>
        </tr>
        """ for t in tickets
    ])

    ledger_rows = "".join([
        f"""
        <tr class="border-b">
            <td class="p-3 font-semibold">{l['customer_name']}</td>
            <td class="p-3 font-mono text-emerald-700 font-bold">${l['balance']:,.2f}</td>
            <td class="p-3 text-xs text-slate-400">{l['last_updated']}</td>
        </tr>
        """ for l in ledgers
    ])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Support & Disputes Desk</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 p-8">
        <div class="max-w-5xl mx-auto space-y-6">
            <a href="/erp" class="text-sm text-slate-500 hover:text-slate-800">&larr; Back to ERP</a>
            <h1 class="text-2xl font-bold">Customer Support Desk & Disputes</h1>
            <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <h2 class="font-bold text-sm text-slate-700 mb-4 uppercase">Open Tickets</h2>
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-50 text-xs text-slate-500 uppercase">
                        <tr><th class="p-3">Ticket ID</th><th class="p-3">Customer</th><th class="p-3">Issue</th><th class="p-3">Disputed</th><th class="p-3">Status</th><th class="p-3">Description</th></tr>
                    </thead>
                    <tbody>{tickets_rows}</tbody>
                </table>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <h2 class="font-bold text-sm text-slate-700 mb-4 uppercase">Customer Ledger Balances</h2>
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-50 text-xs text-slate-500 uppercase">
                        <tr><th class="p-3">Customer</th><th class="p-3">Current Balance</th><th class="p-3">Updated</th></tr>
                    </thead>
                    <tbody>{ledger_rows}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

class CreditResolutionPayload(BaseModel):
    ticket_id: str
    credit_amount: float
    notes: Optional[str] = "Adjustment credit applied"

@app.post("/api/v1/support/resolve-dispute")
def api_resolve_dispute(payload: CreditResolutionPayload):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_tickets WHERE ticket_id = ?", (payload.ticket_id,))
    ticket = cursor.fetchone()
    if not ticket:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticket {payload.ticket_id} not found")

    customer = ticket["customer_name"]
    # Update customer ledger
    cursor.execute("UPDATE customer_ledger SET balance = balance - ?, last_updated = CURRENT_TIMESTAMP WHERE customer_name = ?", (payload.credit_amount, customer))
    # Update ticket status
    cursor.execute("UPDATE support_tickets SET status = 'resolved' WHERE ticket_id = ?", (payload.ticket_id,))
    # Add audit log
    cursor.execute("""
    INSERT INTO erp_audit_log (action, entity_type, entity_id, details, actor)
    VALUES ('DISPUTE_CREDIT_APPLIED', 'support_tickets', ?, ?, 'support_worker')
    """, (ticket["id"], f"Applied ${payload.credit_amount:,.2f} credit to {customer} for ticket {payload.ticket_id}"))

    conn.commit()
    conn.close()
    return {"status": "success", "ticket_id": payload.ticket_id, "customer": customer, "adjusted_by": payload.credit_amount}

@app.get("/api/v1/support/ledger/{customer_name}")
def api_get_ledger(customer_name: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customer_ledger WHERE LOWER(customer_name) = LOWER(?)", (customer_name.strip(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found in ledger")
    return {"status": "success", "customer": row["customer_name"], "balance": row["balance"], "last_updated": row["last_updated"]}

# =========================================================================
# Chaos Simulation Control (For Testing Resilience & Retry)
# =========================================================================

@app.post("/api/v1/chaos/toggle")
def toggle_chaos(enable_flaky: bool = False, enable_ui_drift: bool = False):
    chaos_state["flaky_api"] = enable_flaky
    chaos_state["ui_drift"] = enable_ui_drift
    chaos_state["flaky_counter"] = 0
    return {"status": "updated", "chaos_state": chaos_state}
