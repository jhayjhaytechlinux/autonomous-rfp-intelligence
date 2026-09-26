from app.compliance.compliance_engine import ComplianceEngine
from app.compliance.schemas import (
    CapabilityProfile,
    CompanyCapability,
    ComplianceStatus,
)
from app.extraction.schemas import (
    Requirement,
    RequirementCategory,
)


def make_requirement(
    requirement_id: str,
    description: str,
    evidence: str,
    mandatory: bool = True,
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        category=RequirementCategory.TECHNICAL,
        description=description,
        mandatory=mandatory,
        source_section="Technical Requirements",
        evidence=evidence,
    )


def make_capability(
    capability_id: str,
    name: str,
    description: str,
    evidence: str,
) -> CompanyCapability:
    return CompanyCapability(
        capability_id=capability_id,
        name=name,
        description=description,
        categories=["technical"],
        evidence=evidence,
    )


def make_profile(
    capabilities: list[CompanyCapability],
) -> CapabilityProfile:
    return CapabilityProfile(
        company_name="SecureOps Africa",
        company_type="Cybersecurity Services Provider",
        description="Cybersecurity services provider.",
        capabilities=capabilities,
    )


def test_compliance_engine_assesses_all_requirements():
    engine = ComplianceEngine()

    requirements = [
        make_requirement(
            "REQ-001",
            "The bidder must provide SIEM.",
            "SIEM is required.",
        ),
        make_requirement(
            "REQ-002",
            "The bidder must provide network traffic analysis.",
            "Network traffic analysis is required.",
        ),
    ]

    capabilities = [
        make_capability(
            "CAP-001",
            "Security Information and Event Management",
            "SIEM implementation and administration.",
            "SecureOps Africa provides SIEM implementation.",
        ),
        make_capability(
            "CAP-004",
            "Network Traffic Analysis",
            "Analysis of enterprise network traffic.",
            "SecureOps Africa provides network traffic analysis.",
        ),
    ]

    matrix = engine.assess(
        requirements,
        make_profile(capabilities),
    )

    assert matrix.company_name == "SecureOps Africa"
    assert matrix.total_requirements == 2
    assert len(matrix.results) == 2
    assert matrix.compliant_count == 2
    assert matrix.partial_count == 0
    assert matrix.gap_count == 0
    assert matrix.unknown_count == 0


def test_compliance_engine_records_capability_ids_and_evidence():
    engine = ComplianceEngine()

    requirement = make_requirement(
        "REQ-001",
        "The bidder must provide SIEM.",
        "SIEM is required.",
    )

    capability = make_capability(
        "CAP-001",
        "Security Information and Event Management",
        "SIEM implementation and administration.",
        "SecureOps Africa provides SIEM implementation.",
    )

    matrix = engine.assess(
        [requirement],
        make_profile([capability]),
    )

    result = matrix.results[0]

    assert result.requirement_id == "REQ-001"
    assert result.status == ComplianceStatus.COMPLIANT
    assert result.matched_capability_ids == ["CAP-001"]
    assert result.evidence == [
        "SecureOps Africa provides SIEM implementation."
    ]
    assert result.rationale


def test_compliance_engine_counts_gaps():
    engine = ComplianceEngine()

    requirements = [
        make_requirement(
            "REQ-001",
            "The bidder must provide SIEM.",
            "SIEM is required.",
        ),
        make_requirement(
            "REQ-002",
            "The bidder must manufacture aircraft.",
            "Aircraft manufacturing is required.",
        ),
    ]

    capability = make_capability(
        "CAP-001",
        "Security Information and Event Management",
        "SIEM implementation and administration.",
        "SecureOps Africa provides SIEM implementation.",
    )

    matrix = engine.assess(
        requirements,
        make_profile([capability]),
    )

    assert matrix.total_requirements == 2
    assert matrix.compliant_count == 1
    assert matrix.gap_count == 1
    assert matrix.partial_count == 0
    assert matrix.unknown_count == 0


def test_compliance_engine_handles_no_requirements():
    engine = ComplianceEngine()

    matrix = engine.assess(
        [],
        make_profile([]),
    )

    assert matrix.company_name == "SecureOps Africa"
    assert matrix.total_requirements == 0
    assert matrix.compliant_count == 0
    assert matrix.partial_count == 0
    assert matrix.gap_count == 0
    assert matrix.unknown_count == 0
    assert matrix.results == []


def test_compliance_engine_handles_empty_capabilities():
    engine = ComplianceEngine()

    requirement = make_requirement(
        "REQ-001",
        "The bidder must provide SIEM.",
        "SIEM is required.",
    )

    matrix = engine.assess(
        [requirement],
        make_profile([]),
    )

    assert matrix.total_requirements == 1
    assert matrix.compliant_count == 0
    assert matrix.partial_count == 0
    assert matrix.gap_count == 0
    assert matrix.unknown_count == 1

    result = matrix.results[0]

    assert result.status == ComplianceStatus.UNKNOWN
    assert result.matched_capability_ids == []
    assert result.evidence == []
