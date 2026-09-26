from app.compliance.schemas import (
    CompanyCapability,
    ComplianceStatus,
)
from app.extraction.schemas import Requirement


class CapabilityMatcher:
    """
    Matches RFP requirements against documented company capabilities.

    The matcher uses:
    1. Requirement category alignment.
    2. Requirement-specific keywords.
    3. Evidence sufficiency checks.

    The goal is to avoid treating a broadly related capability as
    sufficient evidence for a specific mandatory requirement.
    """

    CATEGORY_COMPATIBILITY = {
        "technical": {
            "technical",
            "security_monitoring",
            "network_security",
            "identity_and_access",
            "reporting",
            "incident_response",
        },
        "experience": {
            "experience",
        },
        "personnel": {
            "personnel",
        },
        "commercial": {
            "commercial",
        },
        "implementation": {
            "implementation",
            "technical",
        },
        "training": {
            "training",
        },
        "legal": {
            "legal",
        },
        "submission": {
            "submission",
        },
        "other": set(),
    }

    KEYWORD_GROUPS = {
        "siem": {
            "siem",
            "security information and event management",
        },
        "monitoring": {
            "security event monitoring",
            "real-time security event monitoring",
            "security monitoring",
        },
        "incident_detection": {
            "incident detection",
            "detection and alerting",
            "alerting",
        },
        "network_analysis": {
            "network traffic analysis",
            "traffic analysis",
        },
        "rbac": {
            "role-based access control",
            "rbac",
        },
        "audit_logging": {
            "audit logging",
            "audit monitoring",
            "security logging",
        },
        "reporting": {
            "security reporting",
            "security dashboards",
            "dashboards",
        },
        "experience": {
            "cybersecurity experience",
            "cybersecurity service delivery",
            "experience delivering cybersecurity",
        },
        "implementation": {
            "security monitoring implementation",
            "security monitoring solution implementation",
            "implementation of security monitoring",
        },
        "personnel": {
            "qualified cybersecurity personnel",
            "qualified personnel",
            "cybersecurity personnel",
        },
        "enterprise": {
            "enterprise client experience",
            "enterprise clients",
            "enterprise environments",
        },
        "training": {
            "training",
            "cybersecurity training",
            "security awareness",
        },
        "incident_response": {
            "incident response",
        },
    }

    def match(
        self,
        requirement: Requirement,
        capabilities: list[CompanyCapability],
    ) -> tuple[ComplianceStatus, list[CompanyCapability], str]:
        """
        Match one requirement against company capabilities.
        """

        if not capabilities:
            return (
                ComplianceStatus.UNKNOWN,
                [],
                "No company capabilities were provided for assessment.",
            )

        requirement_text = (
            f"{requirement.description} "
            f"{requirement.evidence}"
        ).lower()

        compatible_capabilities = [
            capability
            for capability in capabilities
            if self._category_matches(requirement, capability)
        ]

        matches = []

        for capability in compatible_capabilities:
            capability_text = (
                f"{capability.name} "
                f"{capability.description} "
                f"{capability.evidence}"
            ).lower()

            if self._keyword_match(requirement_text, capability_text):
                matches.append(capability)

        if not matches:
            if requirement.mandatory:
                return (
                    ComplianceStatus.GAP,
                    [],
                    (
                        "No documented company capability was found "
                        "to support this mandatory requirement."
                    ),
                )

            return (
                ComplianceStatus.UNKNOWN,
                [],
                (
                    "No documented company capability was found, "
                    "and the requirement is not mandatory."
                ),
            )

        evidence_sufficient = self._has_sufficient_evidence(
            requirement,
            matches,
        )

        if evidence_sufficient:
            return (
                ComplianceStatus.COMPLIANT,
                matches,
                (
                    f"Matched {len(matches)} compatible documented "
                    "company capability/capabilities with sufficient "
                    "supporting evidence."
                ),
            )

        return (
            ComplianceStatus.PARTIAL,
            matches,
            (
                "Relevant company capability was identified, but "
                "the available evidence does not fully establish "
                "all conditions of the requirement."
            ),
        )

    def _category_matches(
        self,
        requirement: Requirement,
        capability: CompanyCapability,
    ) -> bool:
        """
        Determine whether a capability belongs to a category compatible
        with the RFP requirement category.
        """

        requirement_category = requirement.category.value

        compatible_categories = self.CATEGORY_COMPATIBILITY.get(
            requirement_category,
            set(),
        )

        capability_categories = set(capability.categories)

        return bool(
            compatible_categories.intersection(capability_categories)
        )

    def _keyword_match(
        self,
        requirement_text: str,
        capability_text: str,
    ) -> bool:
        """
        Determine whether requirement-specific concepts appear in both
        the requirement and capability.
        """

        for keywords in self.KEYWORD_GROUPS.values():
            requirement_has_keyword = any(
                keyword in requirement_text
                for keyword in keywords
            )

            capability_has_keyword = any(
                keyword in capability_text
                for keyword in keywords
            )

            if requirement_has_keyword and capability_has_keyword:
                return True

        return False

    @staticmethod
    def _has_sufficient_evidence(
        requirement: Requirement,
        matches: list[CompanyCapability],
    ) -> bool:
        """
        Determine whether the available capability evidence appears
        sufficient to satisfy the requirement.

        Quantitative or explicitly constrained requirements require
        stronger evidence than a general capability statement.
        """

        requirement_text = (
            f"{requirement.description} "
            f"{requirement.evidence}"
        ).lower()

        combined_evidence = " ".join(
            capability.evidence.lower()
            for capability in matches
        )

        quantitative_indicators = [
            "at least",
            "minimum",
            "years",
            "months",
            "quantity",
            "number of",
            "within",
            "deadline",
            "budget",
            "cost",
            "price",
        ]

        requires_specific_evidence = any(
            indicator in requirement_text
            for indicator in quantitative_indicators
        )

        if not requires_specific_evidence:
            return True

        # The current controlled capability profile does not claim
        # specific quantitative values. Therefore, quantitative
        # requirements should not be marked fully compliant unless
        # the evidence explicitly contains the relevant information.
        return any(
            indicator in combined_evidence
            for indicator in quantitative_indicators
        )
