from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


SAMPLE_RFP = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "sample_rfps"
    / "sample_rfp.pdf"
)


def test_extract_requirements_endpoint():
    """Verify the requirement extraction API endpoint."""

    class FakeExtractor:
        """Deterministic extractor for API testing."""

        def extract(self, text):
            class FakeRequirement:
                def model_dump(self):
                    return {
                        "requirement_id": "REQ-001",
                        "category": "technical",
                        "description": (
                            "Provide real-time security event "
                            "monitoring."
                        ),
                        "mandatory": True,
                        "source_section": (
                            "Technical Requirements"
                        ),
                        "evidence": (
                            "Real-time security event "
                            "monitoring."
                        ),
                    }

            class FakeResult:
                requirements = [FakeRequirement()]
                total_requirements = 1

            return FakeResult()

    pdf_bytes = SAMPLE_RFP.read_bytes()

    with patch(
        "app.api.routes_analysis.RequirementExtractor",
        return_value=FakeExtractor(),
    ):
        response = client.post(
            "/api/analysis/extract-requirements",
            files={
                "file": (
                    "sample_rfp.pdf",
                    pdf_bytes,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "sample_rfp.pdf"
    assert data["file_type"] == "pdf"
    assert data["page_count"] == 1
    assert data["character_count"] == 1071
    assert data["total_requirements"] == 1
    assert len(data["requirements"]) == 1

    assert (
        data["requirements"][0]["requirement_id"]
        == "REQ-001"
    )


def test_extract_requirements_rejects_non_pdf():
    """Verify non-PDF files are rejected."""

    response = client.post(
        "/api/analysis/extract-requirements",
        files={
            "file": (
                "sample.txt",
                b"not a PDF",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only PDF files are supported."
    )


def test_extract_requirements_rejects_empty_pdf():
    """Verify empty uploads are rejected."""

    response = client.post(
        "/api/analysis/extract-requirements",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The uploaded PDF is empty."
    )
