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

    The weighted decision model combines:

    - Compliance
    - Capability fit
    - Experience fit
    - Historical proposal relevance
    - Resource availability
    - Risk

    Win probability is calculated separately and returned as an
    explicit decision-support metric. It is not included in the
    existing overall-score weighting model.
    """

    COMPLIANCE_WEIGHT = 0.25
    CAPABILITY_WEIGHT = 0.20
    EXPERIENCE_WEIGHT = 0.15
    HISTORICAL_RELEVANCE_WEIGHT = 0.15
    RESOURCE_WEIGHT = 0.10
    RISK_WEIGHT = 0.15

    def __init__(
        self,
        bid_threshold: float = 80,
        review_threshold: float = 60,
    ):
        if not 0 <= review_threshold <= 100:
            raise ValueError(
                "review_threshold must be between 0 and 100."
            )

        if not 0 <= bid_threshold <= 100:
            raise ValueError(
                "bid_threshold must be between 0 and 100."
            )

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
        historical_relevance_score: float = 0,
        matched_historical_proposals: list[str] | None = None,
        win_probability_score: float = 0,
    ) -> DecisionResult:
        """
        Calculate the overall Bid/No-Bid decision.

        The existing weighted decision model remains unchanged.

        Win probability is an additional evidence-based metric
        calculated separately from the weighted overall score.
        """

        if not 0 <= resource_score <= 100:
            raise ValueError(
                "resource_score must be between 0 and 100."
            )

        if not 0 <= historical_relevance_score <= 100:
            raise ValueError(
                "historical_relevance_score must be between 0 and 100."
            )

        if not 0 <= win_probability_score <= 100:
            raise ValueError(
                "win_probability_score must be between 0 and 100."
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
            + historical_relevance_score
            * self.HISTORICAL_RELEVANCE_WEIGHT
            + resource_score * self.RESOURCE_WEIGHT
            + risk_score * self.RISK_WEIGHT
        )

        decision = self._determine_decision(
            overall_score
        )

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
                    "Measures the proportion of requirements "
                    "supported by documented company capabilities."
                ),
            ),
            DecisionFactor(
                name="Experience Fit",
                score=experience_score,
                weight=self.EXPERIENCE_WEIGHT,
                rationale=(
                    "Measures evidence available for "
                    "experience-related requirements."
                ),
            ),
            DecisionFactor(
                name="Historical Proposal Relevance",
                score=historical_relevance_score,
                weight=self.HISTORICAL_RELEVANCE_WEIGHT,
                rationale=(
                    "Measures how strongly previous successful "
                    "proposals relate to the current opportunity."
                ),
            ),
            DecisionFactor(
                name="Resource Availability",
                score=resource_score,
                weight=self.RESOURCE_WEIGHT,
                rationale=(
                    "Measures current resource availability "
                    "based on the configured resource input."
                ),
            ),
            DecisionFactor(
                name="Risk",
                score=risk_score,
                weight=self.RISK_WEIGHT,
                rationale=(
                    "Higher scores indicate lower "
                    "compliance-related risk from gaps "
                    "and partial requirements."
                ),
            ),
        ]

        rationale = self._build_rationale(
            decision=decision,
            overall_score=overall_score,
            compliance_matrix=compliance_matrix,
            historical_relevance_score=(
                historical_relevance_score
            ),
            matched_historical_proposals=(
                matched_historical_proposals or []
            ),
            win_probability_score=win_probability_score,
        )

        return DecisionResult(
            decision=decision,
            overall_score=round(
                overall_score,
                2,
            ),
            compliance_score=round(
                compliance_score,
                2,
            ),
            capability_score=round(
                capability_score,
                2,
            ),
            experience_score=round(
                experience_score,
                2,
            ),
            resource_score=round(
                resource_score,
                2,
            ),
            risk_score=round(
                risk_score,
                2,
            ),
            historical_relevance_score=round(
                historical_relevance_score,
                2,
            ),
            win_probability_score=round(
                win_probability_score,
                2,
            ),
            matched_historical_proposals=(
                matched_historical_proposals or []
            ),
            mandatory_gaps=mandatory_gaps,
            partial_requirements=partial_requirements,
            factors=factors,
            rationale=rationale,
        )

    @staticmethod
    def _calculate_compliance_score(
        matrix: ComplianceMatrix,
    ) -> float:
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

        return total / matrix.total_requirements

    @staticmethod
    def _calculate_capability_score(
        matrix: ComplianceMatrix,
    ) -> float:
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
        experience_requirement_ids = {
            requirement.requirement_id
            for requirement in requirements
            if requirement.category.value == "experience"
        }

        if not experience_requirement_ids:
            return 100.0

        scores = []

        for result in matrix.results:
            if result.requirement_id not in (
                experience_requirement_ids
            ):
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
        score = 100.0

        score -= matrix.gap_count * 15
        score -= matrix.partial_count * 7.5
        score -= matrix.unknown_count * 5

        return max(
            0.0,
            min(
                100.0,
                score,
            ),
        )

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
            f"{matrix.unknown_count} unknown requirements."
        )

    @staticmethod
    def _build_rationale(
        decision: BidDecision,
        overall_score: float,
        compliance_matrix: ComplianceMatrix,
        historical_relevance_score: float,
        matched_historical_proposals: list[str],
        win_probability_score: float,
    ) -> str:
        historical_proposal_text = (
            ", ".join(
                matched_historical_proposals
            )
            if matched_historical_proposals
            else "none"
        )

        return (
            f"Decision is {decision.value} with an overall score "
            f"of {overall_score:.2f}. The compliance assessment "
            f"found {compliance_matrix.compliant_count} compliant, "
            f"{compliance_matrix.partial_count} partial, "
            f"{compliance_matrix.gap_count} gap, and "
            f"{compliance_matrix.unknown_count} unknown "
            f"requirements. Historical proposal relevance is "
            f"{historical_relevance_score:.2f}, supported by "
            f"previous proposals: {historical_proposal_text}. "
            f"Evidence-based win-probability score is "
            f"{win_probability_score:.2f}."
        )
