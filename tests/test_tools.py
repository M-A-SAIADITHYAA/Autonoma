import pytest
from pathlib import Path
from autonoma.config import settings
from autonoma.environment.generator import seed_environment
from autonoma.tools.file_tool import FileListTool, FileReadTool, InvoiceExtractTool
from autonoma.tools.db_tool import DatabaseQueryTool

@pytest.fixture(autouse=True)
def setup_env():
    seed_environment()

def test_file_list_tool():
    tool = FileListTool()
    res = tool.execute(directory="data/sample_drive/invoices")
    assert res.status == "success"
    assert res.data["count"] > 0
    names = [f["name"] for f in res.data["files"]]
    assert any("Acme_Corp_Invoice" in n for n in names)

def test_invoice_extract_pdf():
    tool = InvoiceExtractTool()
    pdf_path = "data/sample_drive/invoices/Acme_Corp_Invoice_2024_104.pdf"
    res = tool.execute(file_path=pdf_path)
    assert res.status == "success"
    data = res.data
    assert data["invoice_number"] == "ACME-9104"
    assert "Acme" in data["vendor"]
    assert data["amount"] == 5240.00
    assert data["due_date"] == "2024-11-20"

def test_database_query_tool():
    tool = DatabaseQueryTool()
    res = tool.execute(query="SELECT * FROM erp_vendors WHERE name = 'Acme Corp'")
    assert res.status == "success"
    assert res.data["row_count"] == 1
    assert res.data["rows"][0]["name"] == "Acme Corp"

def test_database_query_safety():
    tool = DatabaseQueryTool()
    # Dangerous write should be blocked
    res = tool.execute(query="DROP TABLE erp_vendors")
    assert res.status == "error"
    assert "Only SELECT" in res.error_message
