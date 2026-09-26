from app.compliance.capability_matcher import CapabilityMatcher
from app.compliance.schemas import (
    CompanyCapability,
    ComplianceStatus,
)
from app.extraction.schemas import (
    Requirement,
    RequirementCategory,
)


def make_capability(
    capability_id: str,
    name: str,
    description: str,
    evidence: str,
    categories: list[str] | None = None,
) -> CompanyCapability:
    return CompanyCapability(
        capability_id=capability_id,
        name=name,
        description=description,
        categories=categories or ["technical"],
        evidence=evidence,
    )


def make_requirement(
    requirement_id: str,
    description: str,
    evidence: str,
    category: RequirementCategory = RequirementCategory.TECHNICAL,
    mandatory: bool = True,
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        category=category,
        description=description,
        mandatory=mandatory,
        source_section="Technical Requirements",
        evidence=evidence,
    )


def test_siem_requirement_matches_capability():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-001",
        "The bidder must provide SIEM implementation.",
        "The solution must include SIEM.",
    )

    capability = make_capability(
        "CAP-001",
        "Security Information and Event Management",
        "SIEM implementation and administration.",
        "SecureOps Africa provides SIEM implementation services.",
        ["technical", "security_monitoring"],
    )

    status, matches, rationale = matcher.match(
        requirement,
        [capability],
    )

    assert status == ComplianceStatus.COMPLIANT
    assert len(matches) == 1
    assert matches[0].capability_id == "CAP-001"
    assert "sufficient" in rationale


def test_unmatched_mandatory_requirement_is_gap():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-001",
        "The bidder must provide biometric hardware manufacturing.",
        "The bidder must manufacture biometric devices.",
    )

    capability = make_capability(
        "CAP-001",
        "Security Information and Event Management",
        "SIEM implementation and administration.",
        "SecureOps Africa provides SIEM implementation services.",
    )

    status, matches, rationale = matcher.match(
        requirement,
        [capability],
    )

    assert status == ComplianceStatus.GAP
    assert matches == []
    assert "mandatory requirement" in rationale


def test_unmatched_optional_requirement_is_unknown():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-001",
        "The bidder may provide biometric hardware.",
        "Biometric hardware is optional.",
        mandatory=False,
    )

    capability = make_capability(
        "CAP-001",
        "Security Information and Event Management",
        "SIEM implementation and administration.",
        "SecureOps Africa provides SIEM implementation services.",
    )

    status, matches, rationale = matcher.match(
        requirement,
        [capability],
    )

    assert status == ComplianceStatus.UNKNOWN
    assert matches == []
    assert "not mandatory" in rationale


def test_empty_capability_list_returns_unknown():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-001",
        "The bidder must provide SIEM.",
        "SIEM is required.",
    )

    status, matches, rationale = matcher.match(
        requirement,
        [],
    )

    assert status == ComplianceStatus.UNKNOWN
    assert matches == []
    assert "No company capabilities" in rationale


def test_rbac_requirement_matches_rbac_capability():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-005",
        "The system must support role-based access control.",
        "RBAC is required.",
    )

    capability = make_capability(
        "CAP-005",
        "Role-Based Access Control",
        "Implementation of role-based access controls.",
        "SecureOps Africa supports RBAC implementation.",
        ["technical", "identity_and_access"],
    )

    status, matches, _ = matcher.match(
        requirement,
        [capability],
    )

    assert status == ComplianceStatus.COMPLIANT
    assert matches[0].capability_id == "CAP-005"


def test_personnel_requirement_does_not_match_generic_cybersecurity_capabilities():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-010",
        "The bidder must provide qualified cybersecurity personnel.",
        "Qualified personnel are required.",
        category=RequirementCategory.PERSONNEL,
    )

    generic_capability = make_capability(
        "CAP-008",
        "Cybersecurity Experience",
        "Cybersecurity service delivery experience.",
        "SecureOps Africa has documented cybersecurity service delivery experience.",
        ["experience"],
    )

    personnel_capability = make_capability(
        "CAP-010",
        "Qualified Cybersecurity Personnel",
        "Qualified cybersecurity personnel.",
        "SecureOps Africa maintains qualified cybersecurity personnel.",
        ["personnel"],
    )

    status, matches, _ = matcher.match(
        requirement,
        [generic_capability, personnel_capability],
    )

    assert status == ComplianceStatus.COMPLIANT
    assert [capability.capability_id for capability in matches] == [
        "CAP-010"
    ]


def test_minimum_years_requirement_is_partial_without_duration_evidence():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-008",
        "The bidder must have at least 3 years of cybersecurity experience.",
        "At least 3 years of cybersecurity experience is required.",
        category=RequirementCategory.EXPERIENCE,
    )

    capability = make_capability(
        "CAP-008",
        "Cybersecurity Experience",
        "Cybersecurity service delivery experience.",
        "SecureOps Africa has documented cybersecurity service delivery experience.",
        ["experience"],
    )

    status, matches, rationale = matcher.match(
        requirement,
        [capability],
    )

    assert status == ComplianceStatus.PARTIAL
    assert matches[0].capability_id == "CAP-008"
    assert "does not fully establish" in rationale


def test_requirement_category_prevents_irrelevant_matches():
    matcher = CapabilityMatcher()

    requirement = make_requirement(
        "REQ-010",
        "The bidder must provide qualified cybersecurity personnel.",
        "Qualified personnel are required.",
        category=RequirementCategory.PERSONNEL,
    )

    experience_capability = make_capability(
        "CAP-008",
        "Cybersecurity Experience",
        "Cybersecurity service delivery experience.",
        "SecureOps Africa has documented cybersecurity service delivery experience.",
        ["experience"],
    )

    status, matches, _ = matcher.match(
        requirement,
        [experience_capability],
    )

    assert status == ComplianceStatus.GAP
    assert matches == []
