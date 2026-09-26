from pathlib import Path

from fastapi.testclient import TestClient

from app.ingestion.document_loader import load_document
from app.ingestion.pdf_parser import extract_text_from_pdf
from app.main import app


SAMPLE_PDF = Path("data/sample_rfps/sample_rfp.pdf")

client = TestClient(app)


def test_extract_text_from_pdf():
    """Verify that PDF text extraction returns expected RFP content."""

    text = extract_text_from_pdf(SAMPLE_PDF)

    assert "REQUEST FOR PROPOSAL" in text
    assert "Enterprise Cybersecurity Monitoring Platform" in text
    assert "RFP-2026-001" in text


def test_load_document():
    """Verify document metadata and extracted text."""

    document = load_document(SAMPLE_PDF)

    assert document["filename"] == "sample_rfp.pdf"
    assert document["file_type"] == "pdf"
    assert document["page_count"] == 1
    assert document["character_count"] > 0
    assert "TECHNICAL REQUIREMENTS" in document["text"]


def test_rfp_upload_endpoint():
    """Verify the FastAPI RFP upload endpoint."""

    with SAMPLE_PDF.open("rb") as pdf_file:
        response = client.post(
            "/api/rfp/upload",
            files={
                "file": (
                    "sample_rfp.pdf",
                    pdf_file,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["filename"] == "sample_rfp.pdf"
    assert data["file_type"] == "pdf"
    assert data["page_count"] == 1
    assert data["character_count"] > 0
    assert "REQUEST FOR PROPOSAL" in data["text"]


def test_rfp_upload_rejects_non_pdf():
    """Verify that non-PDF uploads are rejected."""

    response = client.post(
        "/api/rfp/upload",
        files={
            "file": (
                "example.txt",
                b"This is not a PDF.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert "Only PDF documents are supported." in response.json()["detail"]
