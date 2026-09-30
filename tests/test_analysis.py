from pathlib import Path
from unittest.mock import patch

import pymupdf
from fastapi.testclient import TestClient

from app.main import app
from app.proposals.workspace_initializer import (
    ProposalWorkspaceInitializer,
)


client = TestClient(app)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_RFP = (
    PROJECT_ROOT
    / "data"
    / "sample_rfps"
    / "sample_rfp.pdf"
)

SAMPLE_CAPABILITY_PROFILE = (
    PROJECT_ROOT
    / "data"
    / "capabilities"
    / "secureops_africa.json"
)


def create_valid_pdf() -> bytes:
    """
    Create a small valid PDF for API tests.
    """

    document = pymupdf.open()

    try:
        page = document.new_page()

        page.insert_text(
            (72, 72),
            "Test RFP - Cybersecurity Monitoring Platform",
        )

        page.insert_text(
            (72, 100),
            "The bidder must provide security monitoring.",
        )

        page.insert_text(
            (72, 128),
            "The bidder must demonstrate cybersecurity experience.",
        )

        return document.tobytes()

    finally:
        document.close()


def create_valid_capability_profile() -> bytes:
    """
    Return the controlled SecureOps Africa capability profile.
    """

    return SAMPLE_CAPABILITY_PROFILE.read_bytes()


def fake_analysis_result() -> dict:
    """
    Deterministic result used to test the API without
    making a live Gemini request.
    """

    return {
        "rfp": {
            "filename": "test_rfp.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "character_count": 180,
        },
        "company": {
            "name": "SecureOps Africa",
            "type": "Cybersecurity Services Provider",
        },
        "requirements": {
            "total": 2,
            "items": [
                {
                    "requirement_id": "REQ-001",
                    "category": "technical",
                    "description": (
                        "Provide security monitoring."
                    ),
                    "mandatory": True,
                    "source_section": (
                        "Technical Requirements"
                    ),
                    "evidence": (
                        "The bidder must provide "
                        "security monitoring."
                    ),
                },
                {
                    "requirement_id": "REQ-002",
                    "category": "experience",
                    "description": (
                        "Demonstrate cybersecurity experience."
                    ),
                    "mandatory": True,
                    "source_section": "Experience",
                    "evidence": (
                        "The bidder must demonstrate "
                        "cybersecurity experience."
                    ),
                },
            ],
        },
        "compliance": {
            "company_name": "SecureOps Africa",
            "total_requirements": 2,
            "compliant_count": 1,
            "partial_count": 1,
            "gap_count": 0,
            "unknown_count": 0,
            "results": [
                {
                    "requirement_id": "REQ-001",
                    "status": "compliant",
                    "matched_capability_ids": [
                        "CAP-001"
                    ],
                    "evidence": [
                        (
                            "SecureOps Africa provides "
                            "security monitoring."
                        )
                    ],
                    "rationale": (
                        "Requirement is supported."
                    ),
                },
                {
                    "requirement_id": "REQ-002",
                    "status": "partial",
                    "matched_capability_ids": [
                        "CAP-008"
                    ],
                    "evidence": [
                        (
                            "SecureOps Africa has documented "
                            "cybersecurity experience."
                        )
                    ],
                    "rationale": (
                        "Experience evidence is partially "
                        "sufficient."
                    ),
                },
            ],
        },
        "decision": {
            "decision": "executive_review",
            "overall_score": 70,
            "compliance_score": 75,
            "capability_score": 75,
            "experience_score": 50,
            "resource_score": 75,
            "risk_score": 80,
            "mandatory_gaps": [],
            "partial_requirements": [
                "REQ-002"
            ],
            "factors": [],
            "rationale": "Test decision result.",
        },
    }


def test_extract_requirements_endpoint():
    """
    Verify the requirement extraction API endpoint.
    """

    class FakeExtractor:
        """
        Deterministic extractor for API testing.
        """

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
                requirements = [
                    FakeRequirement()
                ]
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
    assert data["character_count"] > 0
    assert data["total_requirements"] == 1
    assert len(data["requirements"]) == 1
    assert (
        data["requirements"][0]["requirement_id"]
        == "REQ-001"
    )


def test_extract_requirements_rejects_non_pdf():
    """
    Verify that non-PDF files are rejected.
    """

    response = client.post(
        "/api/analysis/extract-requirements",
        files={
            "file": (
                "test.txt",
                b"not a pdf",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only PDF files are supported."
    )


def test_extract_requirements_rejects_empty_pdf():
    """
    Verify that empty uploads are rejected.
    """

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


def test_analyze_endpoint_returns_complete_analysis():
    """
    Verify the complete RFP analysis endpoint.

    The RFPAnalyzer is mocked so the test does not call
    Gemini or consume API quota.
    """

    pdf_bytes = create_valid_pdf()
    capability_bytes = create_valid_capability_profile()
    expected_result = fake_analysis_result()

    class FakeAnalyzer:
        def analyze(
            self,
            rfp_path,
            capability_path,
            resource_score=50,
        ):
            assert rfp_path.exists()
            assert capability_path.exists()
            assert rfp_path.suffix == ".pdf"
            assert capability_path.suffix == ".json"
            assert resource_score == 75

            return expected_result

    with patch(
        "app.api.routes_analysis.RFPAnalyzer",
        return_value=FakeAnalyzer(),
    ):
        response = client.post(
            "/api/analysis/analyze",
            files={
                "rfp_file": (
                    "test_rfp.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
                "capability_file": (
                    "secureops_africa.json",
                    capability_bytes,
                    "application/json",
                ),
            },
            data={
                "resource_score": "75",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["message"] == (
        "RFP analysis completed successfully."
    )
    assert data["rfp_filename"] == "test_rfp.pdf"
    assert data["capability_filename"] == (
        "secureops_africa.json"
    )
    assert data["resource_score"] == 75
    assert data["analysis"] == expected_result
    assert (
        data["analysis"]["company"]["name"]
        == "SecureOps Africa"
    )
    assert (
        data["analysis"]["requirements"]["total"]
        == 2
    )
    assert (
        data["analysis"]["compliance"]["gap_count"]
        == 0
    )
    assert (
        data["analysis"]["decision"]["decision"]
        == "executive_review"
    )


def test_analyze_endpoint_rejects_non_pdf_rfp():
    """
    Verify that the complete analysis endpoint rejects
    a non-PDF RFP.
    """

    capability_bytes = create_valid_capability_profile()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "test.txt",
                b"not a pdf",
                "text/plain",
            ),
            "capability_file": (
                "secureops_africa.json",
                capability_bytes,
                "application/json",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The RFP file must be a PDF."
    )


def test_analyze_endpoint_rejects_non_json_capability():
    """
    Verify that the complete analysis endpoint rejects
    a non-JSON capability profile.
    """

    pdf_bytes = create_valid_pdf()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "test_rfp.pdf",
                pdf_bytes,
                "application/pdf",
            ),
            "capability_file": (
                "capabilities.txt",
                b"not json",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The capability profile must be a JSON file."
    )


def test_analyze_endpoint_rejects_invalid_resource_score():
    """
    Verify that resource_score must be between 0 and 100.
    """

    pdf_bytes = create_valid_pdf()
    capability_bytes = create_valid_capability_profile()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "test_rfp.pdf",
                pdf_bytes,
                "application/pdf",
            ),
            "capability_file": (
                "secureops_africa.json",
                capability_bytes,
                "application/json",
            ),
        },
        data={
            "resource_score": "150",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "resource_score must be between 0 and 100."
    )


def test_analyze_endpoint_rejects_negative_resource_score():
    """
    Verify that negative resource scores are rejected.
    """

    pdf_bytes = create_valid_pdf()
    capability_bytes = create_valid_capability_profile()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "test_rfp.pdf",
                pdf_bytes,
                "application/pdf",
            ),
            "capability_file": (
                "secureops_africa.json",
                capability_bytes,
                "application/json",
            ),
        },
        data={
            "resource_score": "-10",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "resource_score must be between 0 and 100."
    )


def test_analyze_endpoint_rejects_empty_rfp():
    """
    Verify that an empty RFP upload is rejected.
    """

    capability_bytes = create_valid_capability_profile()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "empty.pdf",
                b"",
                "application/pdf",
            ),
            "capability_file": (
                "secureops_africa.json",
                capability_bytes,
                "application/json",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The uploaded RFP PDF is empty."
    )


def test_analyze_endpoint_rejects_empty_capability_profile():
    """
    Verify that an empty capability profile is rejected.
    """

    pdf_bytes = create_valid_pdf()

    response = client.post(
        "/api/analysis/analyze",
        files={
            "rfp_file": (
                "test_rfp.pdf",
                pdf_bytes,
                "application/pdf",
            ),
            "capability_file": (
                "empty.json",
                b"",
                "application/json",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The capability profile is empty."
    )


def test_proposal_workspace_endpoint_creates_bid_workspace(
    tmp_path,
):
    """
    Verify that the proposal workspace API creates a workspace
    for a BID decision.
    """

    workspace_root = tmp_path / "proposal_workspaces"

    with patch(
        "app.api.routes_proposals.ProposalWorkspaceInitializer",
        return_value=ProposalWorkspaceInitializer(
            root_path=workspace_root
        ),
    ):
        response = client.post(
            "/api/proposals/workspace",
            json={
                "opportunity_id": "RFP-2026-001",
                "decision": "bid",
                "decision_score": 85.5,
                "win_probability_score": 78.25,
                "matched_historical_proposals": [
                    "PROP-001",
                    "PROP-003",
                ],
                "company_name": "SecureOps Africa",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["message"] == (
        "Proposal workspace initialized successfully."
    )

    workspace = data["workspace"]

    assert workspace["workspace_id"] == "RFP-2026-001"
    assert workspace["workspace_status"] == "initialized"
    assert workspace["decision"] == "bid"
    assert workspace["decision_score"] == 85.5
    assert workspace["win_probability_score"] == 78.25

    workspace_path = workspace_root / "RFP-2026-001"

    assert workspace_path.exists()
    assert (workspace_path / "README.md").exists()
    assert (workspace_path / "decision.json").exists()

    for directory in (
        "requirements",
        "compliance",
        "historical",
        "pricing",
        "resources",
        "proposal",
    ):
        assert (workspace_path / directory).is_dir()


def test_proposal_workspace_endpoint_rejects_executive_review(
    tmp_path,
):
    """
    Verify that EXECUTIVE_REVIEW does not create a workspace.
    """

    workspace_root = tmp_path / "proposal_workspaces"

    with patch(
        "app.api.routes_proposals.ProposalWorkspaceInitializer",
        return_value=ProposalWorkspaceInitializer(
            root_path=workspace_root
        ),
    ):
        response = client.post(
            "/api/proposals/workspace",
            json={
                "opportunity_id": "RFP-2026-002",
                "decision": "executive_review",
                "decision_score": 70,
                "win_probability_score": 65,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Proposal workspace creation requires a BID decision."
    )

    assert not (
        workspace_root / "RFP-2026-002"
    ).exists()


def test_proposal_workspace_endpoint_rejects_no_bid(
    tmp_path,
):
    """
    Verify that NO_BID does not create a workspace.
    """

    workspace_root = tmp_path / "proposal_workspaces"

    with patch(
        "app.api.routes_proposals.ProposalWorkspaceInitializer",
        return_value=ProposalWorkspaceInitializer(
            root_path=workspace_root
        ),
    ):
        response = client.post(
            "/api/proposals/workspace",
            json={
                "opportunity_id": "RFP-2026-003",
                "decision": "no_bid",
                "decision_score": 35,
                "win_probability_score": 30,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Proposal workspace creation requires a BID decision."
    )

    assert not (
        workspace_root / "RFP-2026-003"
    ).exists()


def test_proposal_workspace_endpoint_rejects_invalid_decision_score():
    """
    Verify that the API validates the decision score.
    """

    response = client.post(
        "/api/proposals/workspace",
        json={
            "opportunity_id": "RFP-2026-004",
            "decision": "bid",
            "decision_score": 101,
        },
    )

    assert response.status_code == 422


def test_proposal_workspace_endpoint_rejects_invalid_win_probability():
    """
    Verify that the API validates the win-probability score.
    """

    response = client.post(
        "/api/proposals/workspace",
        json={
            "opportunity_id": "RFP-2026-005",
            "decision": "bid",
            "decision_score": 85,
            "win_probability_score": -1,
        },
    )

    assert response.status_code == 422


def test_proposal_workspace_endpoint_rejects_empty_opportunity_id():
    """
    Verify that an empty opportunity ID is rejected.
    """

    response = client.post(
        "/api/proposals/workspace",
        json={
            "opportunity_id": "",
            "decision": "bid",
            "decision_score": 85,
        },
    )

    assert response.status_code == 422
