import pytest

from app.compliance.schemas import (
    ComplianceMatrix,
    ComplianceResult,
    ComplianceStatus,
)
from app.extraction.schemas import (
    Requirement,
    RequirementCategory,
)
from app.scoring.win_probability import (
    WinProbabilityAnalyzer,
)


def create_requirements():
    return [
        Requirement(
            requirement_id="REQ-001",
            category=RequirementCategory.TECHNICAL,
            description="Provide security monitoring.",
            mandatory=True,
            source_section="Technical",
            evidence="Security monitoring is required.",
        ),
        Requirement(
            requirement_id="REQ-002",
            category=RequirementCategory.EXPERIENCE,
            description="Demonstrate cybersecurity experience.",
            mandatory=True,
            source_section="Experience",
            evidence="Cybersecurity experience is required.",
        ),
    ]


def create_compliance_matrix():
    return ComplianceMatrix(
        company_name="SecureOps Africa",
        total_requirements=2,
        compliant_count=2,
        partial_count=0,
        gap_count=0,
        unknown_count=0,
        results=[
            ComplianceResult(
                requirement_id="REQ-001",
                status=ComplianceStatus.COMPLIANT,
                matched_capability_ids=["CAP-001"],
                evidence=["Security monitoring capability."],
                rationale="Supported.",
            ),
            ComplianceResult(
                requirement_id="REQ-002",
                status=ComplianceStatus.COMPLIANT,
                matched_capability_ids=["CAP-008"],
                evidence=["Cybersecurity experience."],
                rationale="Supported.",
            ),
        ],
    )


def test_win_probability_calculates_score():
    analyzer = WinProbabilityAnalyzer()

    result = analyzer.analyze(
        compliance_matrix=create_compliance_matrix(),
        requirements=create_requirements(),
        historical_relevance_score=80,
    )

    assert result.compliance_component == 100
    assert result.capability_component == 100
    assert result.experience_component == 100
    assert result.historical_component == 80

    assert result.score == pytest.approx(
        97.0,
        abs=0.01,
    )


def test_win_probability_with_no_historical_relevance():
    analyzer = WinProbabilityAnalyzer()

    result = analyzer.analyze(
        compliance_matrix=create_compliance_matrix(),
        requirements=create_requirements(),
        historical_relevance_score=0,
    )

    assert result.score == pytest.approx(
        85.0,
        abs=0.01,
    )


def test_win_probability_handles_partial_and_gap():
    matrix = ComplianceMatrix(
        company_name="SecureOps Africa",
        total_requirements=4,
        compliant_count=1,
        partial_count=1,
        gap_count=1,
        unknown_count=1,
        results=[
            ComplianceResult(
                requirement_id="REQ-001",
                status=ComplianceStatus.COMPLIANT,
                matched_capability_ids=["CAP-001"],
                evidence=["Evidence"],
                rationale="Supported.",
            ),
            ComplianceResult(
                requirement_id="REQ-002",
                status=ComplianceStatus.PARTIAL,
                matched_capability_ids=["CAP-002"],
                evidence=["Partial evidence"],
                rationale="Partially supported.",
            ),
            ComplianceResult(
                requirement_id="REQ-003",
                status=ComplianceStatus.GAP,
                matched_capability_ids=[],
                evidence=[],
                rationale="No capability match.",
            ),
            ComplianceResult(
                requirement_id="REQ-004",
                status=ComplianceStatus.UNKNOWN,
                matched_capability_ids=[],
                evidence=[],
                rationale="Insufficient evidence.",
            ),
        ],
    )

    requirements = [
        Requirement(
            requirement_id="REQ-001",
            category=RequirementCategory.TECHNICAL,
            description="Technical requirement.",
            mandatory=True,
            source_section="Technical",
            evidence="Technical evidence.",
        )
    ]

    analyzer = WinProbabilityAnalyzer()

    result = analyzer.analyze(
        compliance_matrix=matrix,
        requirements=requirements,
        historical_relevance_score=50,
    )

    assert result.compliance_component == 43.75
    assert result.capability_component == 50
    assert result.experience_component == 100
    assert result.historical_component == 50

    assert result.score == pytest.approx(
        57.81,
        abs=0.01,
    )


def test_win_probability_rejects_invalid_historical_score():
    analyzer = WinProbabilityAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            compliance_matrix=create_compliance_matrix(),
            requirements=create_requirements(),
            historical_relevance_score=101,
        )


def test_win_probability_rejects_negative_historical_score():
    analyzer = WinProbabilityAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            compliance_matrix=create_compliance_matrix(),
            requirements=create_requirements(),
            historical_relevance_score=-1,
        )
