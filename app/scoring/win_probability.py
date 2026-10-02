from dataclasses import dataclass

from app.compliance.schemas import (
    ComplianceMatrix,
    ComplianceStatus,
)
from app.extraction.schemas import Requirement


@dataclass(frozen=True)
class WinProbabilityResult:
    """
    Explainable win-probability score.

    This is a decision-support score from 0 to 100.
    It is not a statistically calibrated probability.
    """

    score: float
    compliance_component: float
    capability_component: float
    experience_component: float
    historical_component: float


class WinProbabilityAnalyzer:
    """
    Calculates an evidence-based win-probability score.

    The model combines:

        Compliance             35%
        Capability Fit         30%
        Experience Fit         20%
        Historical Relevance   15%

    All component scores are normalized to 0-100.
    """

    COMPLIANCE_WEIGHT = 0.35
    CAPABILITY_WEIGHT = 0.30
    EXPERIENCE_WEIGHT = 0.20
    HISTORICAL_WEIGHT = 0.15

    def analyze(
        self,
        compliance_matrix: ComplianceMatrix,
        requirements: list[Requirement],
        historical_relevance_score: float = 0,
    ) -> WinProbabilityResult:
        if not 0 <= historical_relevance_score <= 100:
            raise ValueError(
                "historical_relevance_score must be between 0 and 100."
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

        score = (
            compliance_score * self.COMPLIANCE_WEIGHT
            + capability_score * self.CAPABILITY_WEIGHT
            + experience_score * self.EXPERIENCE_WEIGHT
            + historical_relevance_score * self.HISTORICAL_WEIGHT
        )

        return WinProbabilityResult(
            score=round(score, 2),
            compliance_component=round(
                compliance_score,
                2,
            ),
            capability_component=round(
                capability_score,
                2,
            ),
            experience_component=round(
                experience_score,
                2,
            ),
            historical_component=round(
                historical_relevance_score,
                2,
            ),
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
