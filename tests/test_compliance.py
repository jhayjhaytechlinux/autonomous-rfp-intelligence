from app.compliance.schemas import (
    CapabilityProfile,
    CompanyCapability,
    ComplianceMatrix,
    ComplianceResult,
    ComplianceStatus,
)


def test_company_capability_schema():
    """Verify a company capability can be created."""

    capability = CompanyCapability(
        capability_id="CAP-001",
        name="SIEM",
        description="SIEM implementation and monitoring.",
        categories=["technical"],
        evidence="Documented SIEM implementation capability.",
    )

    assert capability.capability_id == "CAP-001"
    assert capability.name == "SIEM"
    assert "technical" in capability.categories


def test_capability_profile_schema():
    """Verify a company capability profile."""

    capability = CompanyCapability(
        capability_id="CAP-001",
        name="SIEM",
        description="SIEM implementation and monitoring.",
        categories=["technical"],
        evidence="Documented SIEM capability.",
    )

    profile = CapabilityProfile(
        company_name="SecureOps Africa",
        company_type="Cybersecurity Services Provider",
        description="Cybersecurity services company.",
        capabilities=[capability],
    )

    assert profile.company_name == "SecureOps Africa"
    assert len(profile.capabilities) == 1


def test_compliance_result_schema():
    """Verify an individual compliance result."""

    result = ComplianceResult(
        requirement_id="REQ-001",
        status=ComplianceStatus.COMPLIANT,
        matched_capability_ids=["CAP-001"],
        evidence=[
            "SecureOps Africa provides SIEM services."
        ],
        rationale="The documented capability directly satisfies the requirement.",
    )

    assert result.requirement_id == "REQ-001"
    assert result.status == ComplianceStatus.COMPLIANT
    assert result.matched_capability_ids == ["CAP-001"]


def test_compliance_matrix_schema():
    """Verify a complete compliance matrix."""

    result = ComplianceResult(
        requirement_id="REQ-001",
        status=ComplianceStatus.COMPLIANT,
        matched_capability_ids=["CAP-001"],
        evidence=[
            "Documented SIEM capability."
        ],
        rationale="Direct capability match.",
    )

    matrix = ComplianceMatrix(
        company_name="SecureOps Africa",
        total_requirements=1,
        compliant_count=1,
        partial_count=0,
        gap_count=0,
        unknown_count=0,
        results=[result],
    )

    assert matrix.company_name == "SecureOps Africa"
    assert matrix.total_requirements == 1
    assert matrix.compliant_count == 1
    assert len(matrix.results) == 1
