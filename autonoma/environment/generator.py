from __future__ import annotations
import os
import json
import sqlite3
import csv
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from autonoma.config import settings

def init_database(db_path: Path = settings.db_path) -> None:
    """Initializes the SQLite schema for the company ERP and support desk."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # ERP Invoices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS erp_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL,
        vendor TEXT NOT NULL,
        amount REAL NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending_review',
        source TEXT DEFAULT 'web_portal',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ERP Vendors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS erp_vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        payment_terms TEXT DEFAULT 'Net 30',
        contact_email TEXT,
        category TEXT
    );
    """)

    # System Audit Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS erp_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        details TEXT,
        actor TEXT DEFAULT 'autonomous_worker',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Customer Support Tickets & Ledger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        disputed_amount REAL DEFAULT 0.0,
        status TEXT DEFAULT 'open',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT UNIQUE NOT NULL,
        balance REAL DEFAULT 0.0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed baseline vendors
    vendors = [
        ("Acme Corp", "Net 30", "billing@acme.com", "Supplies"),
        ("Globex Corporation", "Net 45", "accounts@globex.com", "Logistics"),
        ("Initech Software", "Net 15", "finance@initech.com", "SaaS"),
        ("Umbrella Industries", "Net 30", "payables@umbrella.com", "Consulting"),
        ("Apex Systems", "Net 30", "billing@apexsystems.com", "Hardware")
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO erp_vendors (name, payment_terms, contact_email, category)
    VALUES (?, ?, ?, ?)
    """, vendors)

    # Seed support ticket & ledger
    cursor.execute("""
    INSERT OR IGNORE INTO support_tickets (ticket_id, customer_name, issue_type, disputed_amount, status, description)
    VALUES ('TICK-201', 'Globex Corporation', 'Billing Dispute', 350.00, 'open', 'Customer was double charged $350 for expedited freight service on invoice INV-772.')
    """)
    cursor.execute("UPDATE support_tickets SET status = 'open' WHERE ticket_id = 'TICK-201'")

    cursor.execute("""
    INSERT OR IGNORE INTO customer_ledger (customer_name, balance)
    VALUES ('Globex Corporation', 1250.00)
    """)
    cursor.execute("UPDATE customer_ledger SET balance = 1250.00 WHERE customer_name = 'Globex Corporation'")

    conn.commit()
    conn.close()

def generate_pdf_invoice(filepath: Path, vendor: str, inv_number: str, amount: float, due_date: str, date: str) -> None:
    """Generates a realistic business PDF invoice using ReportLab."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter

    # Header Banner
    c.setFillColor(colors.HexColor("#1e293b"))
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height - 55, f"{vendor.upper()} INVOICE")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 75, "Official Commercial Invoice & Payment Notice")

    # Invoice Details Block
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 130, "INVOICE DETAILS")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 150, f"Invoice Number: {inv_number}")
    c.drawString(40, height - 165, f"Issue Date:     {date}")
    c.setFillColor(colors.HexColor("#dc2626"))
    c.drawString(40, height - 180, f"Payment Due:    {due_date}")

    # Billed To
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 130, "BILLED TO:")
    c.setFont("Helvetica", 10)
    c.drawString(320, height - 150, "Internal Company Ltd")
    c.drawString(320, height - 165, "Department: Accounts Payable")
    c.drawString(320, height - 180, "finance@internal-corp.local")

    # Table Header
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(40, height - 230, width - 80, 25, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 220, "DESCRIPTION")
    c.drawString(380, height - 220, "QTY")
    c.drawString(440, height - 220, "RATE")
    c.drawString(500, height - 220, "TOTAL")

    # Table Item
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 250, "Enterprise Cloud & Operations Support Services")
    c.drawString(390, height - 250, "1")
    c.drawString(435, height - 250, f"${amount:,.2f}")
    c.drawString(495, height - 250, f"${amount:,.2f}")

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(40, height - 265, width - 40, height - 265)

    # Total Due Box
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.rect(360, height - 330, width - 400, 50, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(375, height - 305, "TOTAL DUE:")
    c.setFillColor(colors.HexColor("#16a34a"))
    c.drawString(470, height - 305, f"${amount:,.2f}")

    # Payment Instructions
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 370, "Payment Instructions: Wire Transfer to routing 021000021 / Account # 981240182")
    c.drawString(40, height - 385, f"Please reference invoice #{inv_number} in transfer memo.")

    c.showPage()
    c.save()

def seed_environment(drive_dir: Path = settings.drive_dir) -> None:
    """Populates test drive with sample invoices, PDFs, tickets, and directories."""
    init_database()

    inv_dir = drive_dir / "invoices"
    inv_dir.mkdir(parents=True, exist_ok=True)

    # 1. Older invoice from Acme Corp (August 2024)
    generate_pdf_invoice(
        filepath=inv_dir / "Acme_Corp_Invoice_2024_089.pdf",
        vendor="Acme Corp",
        inv_number="ACME-8901",
        amount=4850.00,
        due_date="2024-09-15",
        date="2024-08-15"
    )

    # 2. Latest invoice from Acme Corp (October 2024 - target of the primary prompt!)
    generate_pdf_invoice(
        filepath=inv_dir / "Acme_Corp_Invoice_2024_104.pdf",
        vendor="Acme Corp",
        inv_number="ACME-9104",
        amount=5240.00,
        due_date="2024-11-20",
        date="2024-10-02"
    )

    # 3. High-Value invoice from Apex Systems ($14,500.00 - triggers safety threshold!)
    apex_inv = {
        "invoice_number": "APEX-5542",
        "vendor": "Apex Systems",
        "amount": 14500.00,
        "due_date": "2024-12-10",
        "date": "2024-10-01",
        "currency": "USD",
        "items": [
            {"description": "Enterprise Server Cluster Migration & Hardware Leasing", "total": 14500.00}
        ],
        "notes": "Requires Tier 2 executive sign-off due to capital expenditure"
    }
    with open(inv_dir / "Apex_Systems_Invoice_2024_011.json", "w", encoding="utf-8") as f:
        json.dump(apex_inv, f, indent=2)

    # 4. Initech Software text invoice
    initech_text = """
    =======================================================
    INITECH SOFTWARE LLC - SUBSCRIPTION INVOICE
    =======================================================
    Invoice ID: INT-9921
    Vendor: Initech Software
    Date: 2024-09-28
    Due Date: 2024-10-28

    Service: Annual Enterprise Code Review License
    Total Amount: $2,400.00
    Payment Terms: Net 30
    Contact: billing@initech.com
    =======================================================
    """
    with open(inv_dir / "Initech_Invoice_INT-9921.txt", "w", encoding="utf-8") as f:
        f.write(initech_text)

    # 5. Ambiguous company invoices (for clarification demonstration)
    with open(inv_dir / "Acme_Widgets_Ltd_Invoice_OCT.txt", "w", encoding="utf-8") as f:
        f.write("Vendor: Acme Widgets Ltd\nInvoice: AW-101\nTotal: $1,200.00\nDue Date: 2024-11-01\n")

    with open(inv_dir / "Acme_Logistics_Inc_Invoice_OCT.txt", "w", encoding="utf-8") as f:
        f.write("Vendor: Acme Logistics Inc\nInvoice: AL-302\nTotal: $3,150.00\nDue Date: 2024-11-05\n")

    # 6. Customer Support Ticket
    support_dir = drive_dir / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    ticket_data = {
        "ticket_id": "TICK-201",
        "customer_name": "Globex Corporation",
        "issue_type": "Billing Dispute",
        "disputed_amount": 350.00,
        "status": "open",
        "description": "Customer was double charged $350 for expedited freight service on invoice INV-772."
    }
    with open(support_dir / "Globex_Support_Ticket_201.json", "w", encoding="utf-8") as f:
        json.dump(ticket_data, f, indent=2)

    # 7. HR Onboarding Queue
    hr_dir = drive_dir / "hr"
    hr_dir.mkdir(parents=True, exist_ok=True)
    with open(hr_dir / "onboarding_queue.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "full_name", "department", "role", "email", "status"])
        writer.writerow(["EMP-101", "Jane Doe", "Engineering", "Staff Software Engineer", "jane.doe@company.local", "pending"])
        writer.writerow(["EMP-102", "Alex Chen", "Product", "Product Manager", "alex.chen@company.local", "pending"])

if __name__ == "__main__":
    seed_environment()
    print("Simulated enterprise environment and database seeded successfully.")
