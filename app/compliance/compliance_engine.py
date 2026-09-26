from app.compliance.capability_matcher import CapabilityMatcher
from app.compliance.schemas import (
    CapabilityProfile,
    ComplianceMatrix,
    ComplianceStatus,
)
from app.extraction.schemas import Requirement


class ComplianceEngine:
    """
    Builds an automated compliance matrix by assessing every
    extracted RFP requirement against the company's capabilities.
    """

    def __init__(self, matcher: CapabilityMatcher | None = None):
        self.matcher = matcher or CapabilityMatcher()

    def assess(
        self,
        requirements: list[Requirement],
        capability_profile: CapabilityProfile,
    ) -> ComplianceMatrix:
        """
        Assess all RFP requirements against the company capability profile.
        """

        results = []

        for requirement in requirements:
            status, matched_capabilities, rationale = self.matcher.match(
                requirement,
                capability_profile.capabilities,
            )

            results.append(
                {
                    "requirement_id": requirement.requirement_id,
                    "status": status,
                    "matched_capability_ids": [
                        capability.capability_id
                        for capability in matched_capabilities
                    ],
                    "evidence": [
                        capability.evidence
                        for capability in matched_capabilities
                    ],
                    "rationale": rationale,
                }
            )

        compliant_count = sum(
            1
            for result in results
            if result["status"] == ComplianceStatus.COMPLIANT
        )

        partial_count = sum(
            1
            for result in results
            if result["status"] == ComplianceStatus.PARTIAL
        )

        gap_count = sum(
            1
            for result in results
            if result["status"] == ComplianceStatus.GAP
        )

        unknown_count = sum(
            1
            for result in results
            if result["status"] == ComplianceStatus.UNKNOWN
        )

        return ComplianceMatrix(
            company_name=capability_profile.company_name,
            total_requirements=len(requirements),
            compliant_count=compliant_count,
            partial_count=partial_count,
            gap_count=gap_count,
            unknown_count=unknown_count,
            results=results,
        )
