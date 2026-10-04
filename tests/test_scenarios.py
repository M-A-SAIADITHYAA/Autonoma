import pytest
import threading
import time
import uvicorn

from autonoma.config import settings
from autonoma.environment.generator import seed_environment
from autonoma.environment.company_server import app, chaos_state
from autonoma.core.agent import AutonomousWorker
from autonoma.core.models import TaskStatus

@pytest.fixture(scope="module", autouse=True)
def run_company_server():
    seed_environment()
    # Run test server in daemon thread
    server = threading.Thread(
        target=lambda: uvicorn.run(app, host=settings.company_host, port=settings.company_port, log_level="error"),
        daemon=True
    )
    server.start()
    time.sleep(1.2)
    yield
    chaos_state["flaky_api"] = False

def test_scenario_1_baseline_invoice_entry():
    seed_environment()
    goal = "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=True)
    bundle = worker.run(goal)

    assert bundle.status == TaskStatus.COMPLETED
    assert "ACME-9104" in str(bundle.extracted_entities)
    assert bundle.extracted_entities["extracted_invoice"]["amount"] == 5240.00
    assert bundle.extracted_entities["extracted_invoice"]["due_date"] == "2024-11-20"
    assert len(bundle.verifications) >= 3
    assert all(c.passed for c in bundle.verifications)
    assert "PROOF-VERIFIED_SUCCESS" in bundle.receipt_id

def test_scenario_2_flaky_service_and_recovery():
    seed_environment()
    chaos_state["flaky_api"] = True
    chaos_state["flaky_counter"] = 0

    goal = "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=True)
    bundle = worker.run(goal)

    # Clean up chaos flag
    chaos_state["flaky_api"] = False

    assert bundle.status == TaskStatus.COMPLETED
    assert bundle.retries_attempted > 0 or "api_call" in [s["action"]["tool_name"] for s in bundle.audit_trail]
    assert all(c.passed for c in bundle.verifications)

def test_scenario_3_hitl_approval_granted():
    seed_environment()
    goal = "Find the invoice from Apex Systems, extract the amount and due date, and record it into our internal system."
    # Auto-approve simulated human response
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=True)
    bundle = worker.run(goal)

    assert bundle.status == TaskStatus.COMPLETED
    assert bundle.extracted_entities["extracted_invoice"]["amount"] == 14500.00
    # Verified that high value approval was requested and recorded
    assert bundle.extracted_entities.get("high_value_approved") is True

def test_scenario_3_hitl_approval_denied():
    seed_environment()
    goal = "Find the invoice from Apex Systems, extract the amount and due date, and record it into our internal system."
    # Human operator rejects high-value transaction
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=False)
    bundle = worker.run(goal)

    assert bundle.status == TaskStatus.FAILED
    assert "Human operator denied" in bundle.audit_trail[-1]["reflection"]

def test_scenario_4_generalization_support_dispute():
    seed_environment()
    goal = "Review customer ticket #201 for Globex Corporation, audit their account balance, apply the credit adjustment, and resolve the ticket."
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=True)
    bundle = worker.run(goal)

    assert bundle.status == TaskStatus.COMPLETED
    # Check that ledger balance was adjusted in database
    import sqlite3
    conn = sqlite3.connect(str(settings.db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM customer_ledger WHERE customer_name = 'Globex Corporation'")
    bal = cursor.fetchone()[0]
    conn.close()
    # Initial was 1250.00, disputed was 350.00 -> 1250 - 350 = 900.00
    assert bal == 900.00

def test_scenario_5_ambiguity_clarification():
    seed_environment()
    goal = "Find the invoice from Acme, extract amount and due date, and enter it into our internal system."
    worker = AutonomousWorker(interactive_human=False, default_auto_approve=True)
    bundle = worker.run(goal)

    assert bundle.status == TaskStatus.COMPLETED
    assert bundle.extracted_entities.get("clarification_done") is True
    assert "ask_user_clarification" in [s["action"]["tool_name"] for s in bundle.audit_trail]

