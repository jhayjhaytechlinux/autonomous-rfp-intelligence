from app.compliance.schemas import (
    ComplianceMatrix,
    ComplianceStatus,
)
from app.decision.schemas import (
    BidDecision,
    DecisionFactor,
    DecisionResult,
)
from app.extraction.schemas import Requirement


class DecisionEngine:
    """
    Calculates an explainable weighted Bid/No-Bid decision.

    This first implementation uses the compliance matrix plus explicit
    resource availability input. Additional evidence sources such as
    past proposals, pricing models, and team schedules will be added
    in later phases.
    """

    COMPLIANCE_WEIGHT = 0.30
    CAPABILITY_WEIGHT = 0.25
    EXPERIENCE_WEIGHT = 0.20
    RESOURCE_WEIGHT = 0.15
    RISK_WEIGHT = 0.10

    def __init__(
        self,
        bid_threshold: float = 80,
        review_threshold: float = 60,
    ):
        if not 0 <= review_threshold <= 100:
            raise ValueError("review_threshold must be between 0 and 100.")

        if not 0 <= bid_threshold <= 100:
            raise ValueError("bid_threshold must be between 0 and 100.")

        if review_threshold > bid_threshold:
            raise ValueError(
                "review_threshold cannot be greater than bid_threshold."
            )

        self.bid_threshold = bid_threshold
        self.review_threshold = review_threshold

    def evaluate(
        self,
        compliance_matrix: ComplianceMatrix,
        requirements: list[Requirement],
        resource_score: float = 50,
    ) -> DecisionResult:
        """
        Calculate the overall Bid/No-Bid decision.
        """

        if not 0 <= resource_score <= 100:
            raise ValueError(
                "resource_score must be between 0 and 100."
            )

        compliance_score = self._calculate_compliance_score(
            compliance_matrix
        )

        capability_score = self._calculate_capability_score(
            compliance_matrix
        )

        experience_score = self._calculate_experience_score(
            compliance_matrix,
            requirements,
        )

        risk_score = self._calculate_risk_score(
            compliance_matrix
        )

        overall_score = (
            compliance_score * self.COMPLIANCE_WEIGHT
            + capability_score * self.CAPABILITY_WEIGHT
            + experience_score * self.EXPERIENCE_WEIGHT
            + resource_score * self.RESOURCE_WEIGHT
            + risk_score * self.RISK_WEIGHT
        )

        decision = self._determine_decision(overall_score)

        mandatory_gaps = [
            result.requirement_id
            for result in compliance_matrix.results
            if result.status == ComplianceStatus.GAP
        ]

        partial_requirements = [
            result.requirement_id
            for result in compliance_matrix.results
            if result.status == ComplianceStatus.PARTIAL
        ]

        factors = [
            DecisionFactor(
                name="Compliance",
                score=compliance_score,
                weight=self.COMPLIANCE_WEIGHT,
                rationale=self._compliance_rationale(
                    compliance_matrix
                ),
            ),
            DecisionFactor(
                name="Capability Fit",
                score=capability_score,
                weight=self.CAPABILITY_WEIGHT,
                rationale=(
                    "Measures the proportion of requirements supported "
                    "by documented company capabilities."
                ),
            ),
            DecisionFactor(
                name="Experience Fit",
                score=experience_score,
                weight=self.EXPERIENCE_WEIGHT,
                rationale=(
                    "Measures evidence available for experience-related "
                    "requirements."
                ),
            ),
            DecisionFactor(
                name="Resource Availability",
                score=resource_score,
                weight=self.RESOURCE_WEIGHT,
                rationale=(
                    "Current resource availability input. This will "
                    "later be calculated from team bandwidth data."
                ),
            ),
            DecisionFactor(
                name="Risk",
                score=risk_score,
                weight=self.RISK_WEIGHT,
                rationale=(
                    "Higher scores indicate lower compliance-related "
                    "risk from gaps and partial requirements."
                ),
            ),
        ]

        rationale = self._build_rationale(
            decision=decision,
            overall_score=overall_score,
            compliance_matrix=compliance_matrix,
        )

        return DecisionResult(
            decision=decision,
            overall_score=round(overall_score, 2),
            compliance_score=round(compliance_score, 2),
            capability_score=round(capability_score, 2),
            experience_score=round(experience_score, 2),
            resource_score=round(resource_score, 2),
            risk_score=round(risk_score, 2),
            mandatory_gaps=mandatory_gaps,
            partial_requirements=partial_requirements,
            factors=factors,
            rationale=rationale,
        )

    @staticmethod
    def _calculate_compliance_score(
        matrix: ComplianceMatrix,
    ) -> float:
        """
        Calculate compliance using weighted status values.

        COMPLIANT = 100
        PARTIAL   = 50
        GAP       = 0
        UNKNOWN   = 25
        """

        if matrix.total_requirements == 0:
            return 0.0

        status_scores = {
            ComplianceStatus.COMPLIANT: 100,
            ComplianceStatus.PARTIAL: 50,
            ComplianceStatus.GAP: 0,
            ComplianceStatus.UNKNOWN: 25,
        }

        total = sum(
            status_scores[result.status]
            for result in matrix.results
        )

        return (total / matrix.total_requirements)

    @staticmethod
    def _calculate_capability_score(
        matrix: ComplianceMatrix,
    ) -> float:
        """
        Calculate capability fit from requirements with documented
        capability matches.
        """

        if matrix.total_requirements == 0:
            return 0.0

        supported = sum(
            1
            for result in matrix.results
            if result.matched_capability_ids
        )

        return (
            supported / matrix.total_requirements
        ) * 100

    @staticmethod
    def _calculate_experience_score(
        matrix: ComplianceMatrix,
        requirements: list[Requirement],
    ) -> float:
        """
        Calculate experience fit from experience-related requirements.
        """

        experience_requirement_ids = {
            requirement.requirement_id
            for requirement in requirements
            if requirement.category.value == "experience"
        }

        if not experience_requirement_ids:
            return 100.0

        scores = []

        for result in matrix.results:
            if result.requirement_id not in experience_requirement_ids:
                continue

            if result.status == ComplianceStatus.COMPLIANT:
                scores.append(100)
            elif result.status == ComplianceStatus.PARTIAL:
                scores.append(50)
            elif result.status == ComplianceStatus.UNKNOWN:
                scores.append(25)
            else:
                scores.append(0)

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    @staticmethod
    def _calculate_risk_score(
        matrix: ComplianceMatrix,
    ) -> float:
        """
        Calculate a risk score where higher means lower risk.

        Each mandatory gap has a larger negative effect than a partial
        requirement.
        """

        if matrix.total_requirements == 0:
            return 0.0

        gap_penalty = matrix.gap_count * 15
        partial_penalty = matrix.partial_count * 7.5
        unknown_penalty = matrix.unknown_count * 5

        risk_score = 100 - (
            gap_penalty
            + partial_penalty
            + unknown_penalty
        )

        return max(0.0, min(100.0, risk_score))

    def _determine_decision(
        self,
        overall_score: float,
    ) -> BidDecision:

        if overall_score >= self.bid_threshold:
            return BidDecision.BID

        if overall_score >= self.review_threshold:
            return BidDecision.EXECUTIVE_REVIEW

        return BidDecision.NO_BID

    @staticmethod
    def _compliance_rationale(
        matrix: ComplianceMatrix,
    ) -> str:
        return (
            f"{matrix.compliant_count} compliant, "
            f"{matrix.partial_count} partial, "
            f"{matrix.gap_count} gaps, and "
            f"{matrix.unknown_count} unknown requirements "
            f"out of {matrix.total_requirements}."
        )

    @staticmethod
    def _build_rationale(
        decision: BidDecision,
        overall_score: float,
        compliance_matrix: ComplianceMatrix,
    ) -> str:

        return (
            f"The calculated decision is "
            f"{decision.value.upper()} with an overall score of "
            f"{overall_score:.2f}/100. "
            f"The compliance assessment identified "
            f"{compliance_matrix.gap_count} gaps and "
            f"{compliance_matrix.partial_count} partial requirements."
        )
