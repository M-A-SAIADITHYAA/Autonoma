import pytest
from autonoma.core.verifier import OutcomeVerifier

def test_verifier_exact_match():
    verifier = OutcomeVerifier()
    db_records = [
        {"id": 1, "vendor": "Acme Corp", "amount": 5240.00, "due_date": "2024-11-20", "status": "pending_review"}
    ]
    checks = verifier.verify_invoice_record(
        expected_vendor="Acme Corp",
        expected_amount=5240.00,
        expected_due_date="2024-11-20",
        db_records=db_records
    )
    assert len(checks) == 4
    assert all(c.passed for c in checks)
    receipt = OutcomeVerifier.generate_proof_receipt("task-1", "Invoice Entry", checks, {})
    assert "VERIFIED_SUCCESS" in receipt

def test_verifier_amount_mismatch_detected():
    verifier = OutcomeVerifier()
    # Simulating fraudulent or incorrect entry in ERP
    db_records = [
        {"id": 1, "vendor": "Acme Corp", "amount": 9999.00, "due_date": "2024-11-20", "status": "pending_review"}
    ]
    checks = verifier.verify_invoice_record(
        expected_vendor="Acme Corp",
        expected_amount=5240.00,
        expected_due_date="2024-11-20",
        db_records=db_records
    )
    passed_map = {c.description: c.passed for c in checks}
    assert passed_map["Financial Amount Integrity"] is False
    receipt = OutcomeVerifier.generate_proof_receipt("task-2", "Invoice Entry", checks, {})
    assert "VERIFICATION_FAILED" in receipt

def test_verifier_empty_records():
    verifier = OutcomeVerifier()
    checks = verifier.verify_invoice_record(
        expected_vendor="Acme Corp",
        expected_amount=5240.00,
        expected_due_date="2024-11-20",
        db_records=[]
    )
    assert len(checks) == 1
    assert checks[0].passed is False
