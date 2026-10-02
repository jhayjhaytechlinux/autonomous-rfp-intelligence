from pathlib import Path
import json

import pytest
import pymupdf

from app.analysis.rfp_analyzer import RFPAnalysisError, RFPAnalyzer
from app.compliance.schemas import (
    CapabilityProfile,
    ComplianceMatrix,
    ComplianceStatus,
)
from app.decision.schemas import DecisionResult
from app.extraction.schemas import (
    Requirement,
    RequirementCategory,
    RequirementExtractionResult,
)


class FakeRequirementExtractor:
    """Fake extractor used to test orchestration without Gemini."""

    def extract(self, rfp_text: str) -> RequirementExtractionResult:
        assert rfp_text.strip()

        requirements = [
            Requirement(
                requirement_id="REQ-001",
                category=RequirementCategory.TECHNICAL,
                description="Provide security monitoring.",
                mandatory=True,
                source_section="Technical Requirements",
                evidence="The bidder must provide security monitoring.",
            ),
            Requirement(
                requirement_id="REQ-002",
                category=RequirementCategory.EXPERIENCE,
                description="Demonstrate cybersecurity experience.",
                mandatory=True,
                source_section="Experience",
                evidence=(
                    "The bidder must demonstrate cybersecurity experience."
                ),
            ),
        ]

        return RequirementExtractionResult(
            requirements=requirements,
            total_requirements=len(requirements),
        )


class FakeComplianceEngine:
    """Fake compliance engine used to test orchestration."""

    def assess(
        self,
        requirements: list[Requirement],
        capability_profile: CapabilityProfile,
    ) -> ComplianceMatrix:
        assert len(requirements) == 2
        assert capability_profile.company_name == "SecureOps Africa"

        results = [
            {
                "requirement_id": "REQ-001",
                "status": ComplianceStatus.COMPLIANT,
                "matched_capability_ids": ["CAP-001"],
                "evidence": [
                    "SecureOps Africa provides security monitoring."
                ],
                "rationale": "Requirement is supported.",
            },
            {
                "requirement_id": "REQ-002",
                "status": ComplianceStatus.PARTIAL,
                "matched_capability_ids": ["CAP-008"],
                "evidence": [
                    (
                        "SecureOps Africa has documented "
                        "cybersecurity experience."
                    )
                ],
                "rationale": (
                    "Experience evidence is partially sufficient."
                ),
            },
        ]

        return ComplianceMatrix(
            company_name=capability_profile.company_name,
            total_requirements=2,
            compliant_count=1,
            partial_count=1,
            gap_count=0,
            unknown_count=0,
            results=results,
        )


class FakeDecisionEngine:
    """Fake decision engine used to test orchestration."""

    def evaluate(
        self,
        compliance_matrix: ComplianceMatrix,
        requirements: list[Requirement],
        resource_score: float = 50,
        historical_relevance_score: float = 0,
        matched_historical_proposals: list[str] | None = None,
    ) -> DecisionResult:
        assert compliance_matrix.total_requirements == 2
        assert len(requirements) == 2
        assert resource_score == 75

        assert historical_relevance_score == 50
        assert matched_historical_proposals == [
            "PROP-001",
            "PROP-003",
        ]

        return DecisionResult(
            decision="executive_review",
            overall_score=70,
            compliance_score=75,
            capability_score=75,
            experience_score=50,
            resource_score=75,
            risk_score=80,
            historical_relevance_score=historical_relevance_score,
            matched_historical_proposals=(
                matched_historical_proposals or []
            ),
            mandatory_gaps=[],
            partial_requirements=["REQ-002"],
            factors=[],
            rationale="Test decision result.",
        )


def create_test_rfp(tmp_path: Path) -> Path:
    """
    Create a valid PDF containing test RFP text.

    The analyzer uses the real document ingestion pipeline,
    so the test file must be a valid PDF.
    """
    rfp_path = tmp_path / "test_rfp.pdf"

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

        document.save(rfp_path)

    finally:
        document.close()

    return rfp_path


def create_test_capability_profile(tmp_path: Path) -> Path:
    """Create a valid capability profile for the analyzer test."""

    capability_path = tmp_path / "capabilities.json"

    capability_profile = {
        "company_name": "SecureOps Africa",
        "company_type": "Cybersecurity Services Provider",
        "description": (
            "A cybersecurity services provider specializing in "
            "security operations and security monitoring."
        ),
        "capabilities": [
            {
                "capability_id": "CAP-001",
                "name": "Security Monitoring",
                "description": "Security monitoring capability.",
                "categories": [
                    "technical",
                    "security_monitoring",
                ],
                "evidence": (
                    "SecureOps Africa provides security monitoring."
                ),
            },
            {
                "capability_id": "CAP-008",
                "name": "Cybersecurity Experience",
                "description": "Documented cybersecurity experience.",
                "categories": ["experience"],
                "evidence": (
                    "SecureOps Africa has documented "
                    "cybersecurity experience."
                ),
            },
        ],
    }

    capability_path.write_text(
        json.dumps(capability_profile),
        encoding="utf-8",
    )

    return capability_path


def test_rfp_analyzer_runs_complete_pipeline(tmp_path):
    """Test the complete RFP analysis orchestration."""

    rfp_path = create_test_rfp(tmp_path)
    capability_path = create_test_capability_profile(tmp_path)

    analyzer = RFPAnalyzer(
        requirement_extractor=FakeRequirementExtractor(),
        compliance_engine=FakeComplianceEngine(),
        decision_engine=FakeDecisionEngine(),
    )

    result = analyzer.analyze(
        rfp_path=rfp_path,
        capability_path=capability_path,
        resource_score=75,
    )

    # ---------------------------------------------------------
    # RFP metadata
    # ---------------------------------------------------------

    assert result["rfp"]["filename"] == "test_rfp.pdf"
    assert result["rfp"]["file_type"] == "pdf"
    assert result["rfp"]["page_count"] == 1
    assert result["rfp"]["character_count"] > 0

    # ---------------------------------------------------------
    # Company
    # ---------------------------------------------------------

    assert result["company"]["name"] == "SecureOps Africa"
    assert result["company"]["type"] == "Cybersecurity Services Provider"

    # ---------------------------------------------------------
    # Requirements
    # ---------------------------------------------------------

    assert result["requirements"]["total"] == 2
    assert len(result["requirements"]["items"]) == 2

    # ---------------------------------------------------------
    # Compliance
    # ---------------------------------------------------------

    assert result["compliance"]["total_requirements"] == 2
    assert result["compliance"]["compliant_count"] == 1
    assert result["compliance"]["partial_count"] == 1
    assert result["compliance"]["gap_count"] == 0
    assert result["compliance"]["unknown_count"] == 0

    # ---------------------------------------------------------
    # Historical proposal relevance
    # ---------------------------------------------------------

    assert (
        result["historical_proposals"]["dataset_type"]
        == "synthetic_demonstration"
    )

    assert (
        result["historical_proposals"]["total_proposals"]
        == 4
    )

    assert (
        result["historical_proposals"]["matched_proposal_ids"]
        == [
            "PROP-001",
            "PROP-003",
        ]
    )

    assert (
        result["historical_proposals"]["matched_capability_ids"]
        == ["CAP-001"]
    )

    assert (
        result["historical_proposals"]["relevance_score"]
        == 50
    )

    # ---------------------------------------------------------
    # Decision
    # ---------------------------------------------------------

    assert result["decision"]["decision"] == "executive_review"
    assert result["decision"]["overall_score"] == 70
    assert result["decision"]["resource_score"] == 75
    assert result["decision"]["historical_relevance_score"] == 50

    assert result["decision"]["matched_historical_proposals"] == [
        "PROP-001",
        "PROP-003",
    ]

    assert result["decision"]["partial_requirements"] == ["REQ-002"]


def test_rfp_analyzer_rejects_missing_rfp(tmp_path):
    """Test that a missing RFP file is rejected."""

    missing_rfp = tmp_path / "missing.pdf"

    capability_path = create_test_capability_profile(tmp_path)

    analyzer = RFPAnalyzer(
        requirement_extractor=FakeRequirementExtractor(),
        compliance_engine=FakeComplianceEngine(),
        decision_engine=FakeDecisionEngine(),
    )

    with pytest.raises(RFPAnalysisError):
        analyzer.analyze(
            rfp_path=missing_rfp,
            capability_path=capability_path,
            resource_score=75,
        )


def test_rfp_analyzer_rejects_missing_capability_profile(tmp_path):
    """Test that a missing capability profile is rejected."""

    rfp_path = create_test_rfp(tmp_path)

    missing_capability = tmp_path / "missing.json"

    analyzer = RFPAnalyzer(
        requirement_extractor=FakeRequirementExtractor(),
        compliance_engine=FakeComplianceEngine(),
        decision_engine=FakeDecisionEngine(),
    )

    with pytest.raises(RFPAnalysisError):
        analyzer.analyze(
            rfp_path=rfp_path,
            capability_path=missing_capability,
            resource_score=75,
        )


def test_rfp_analyzer_accepts_path_objects(tmp_path):
    """Test that Path objects are accepted by the analyzer."""

    rfp_path = create_test_rfp(tmp_path)

    capability_path = create_test_capability_profile(tmp_path)

    analyzer = RFPAnalyzer(
        requirement_extractor=FakeRequirementExtractor(),
        compliance_engine=FakeComplianceEngine(),
        decision_engine=FakeDecisionEngine(),
    )

    result = analyzer.analyze(
        rfp_path=Path(rfp_path),
        capability_path=Path(capability_path),
        resource_score=75,
    )

    assert result["company"]["name"] == "SecureOps Africa"
    assert result["rfp"]["page_count"] == 1
    assert result["rfp"]["file_type"] == "pdf"
    assert result["decision"]["decision"] == "executive_review"
    assert result["decision"]["overall_score"] == 70

    assert (
        result["historical_proposals"]["matched_proposal_ids"]
        == [
            "PROP-001",
            "PROP-003",
        ]
    )
