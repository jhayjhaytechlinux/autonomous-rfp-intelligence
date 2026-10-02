from dataclasses import dataclass

from app.resources.schemas import TeamBandwidthDataset


@dataclass(frozen=True)
class BandwidthAnalysisResult:
    total_available_hours: float
    total_allocated_hours: float
    total_remaining_hours: float
    utilization_percentage: float
    resource_score: float


class BandwidthAnalyzer:
    """
    Calculates an explainable resource availability score from
    team bandwidth data.

    The score represents available capacity relative to total
    available capacity.

    Formula:

        remaining_hours / available_hours * 100

    Higher scores indicate greater available team capacity.
    """

    def analyze(
        self,
        dataset: TeamBandwidthDataset,
    ) -> BandwidthAnalysisResult:

        available_hours = dataset.total_available_hours
        allocated_hours = dataset.total_allocated_hours
        remaining_hours = dataset.total_remaining_hours

        if available_hours <= 0:
            return BandwidthAnalysisResult(
                total_available_hours=0.0,
                total_allocated_hours=allocated_hours,
                total_remaining_hours=remaining_hours,
                utilization_percentage=100.0,
                resource_score=0.0,
            )

        utilization_percentage = (
            allocated_hours / available_hours
        ) * 100

        resource_score = (
            remaining_hours / available_hours
        ) * 100

        return BandwidthAnalysisResult(
            total_available_hours=round(available_hours, 2),
            total_allocated_hours=round(allocated_hours, 2),
            total_remaining_hours=round(remaining_hours, 2),
            utilization_percentage=round(
                utilization_percentage,
                2,
            ),
            resource_score=round(
                resource_score,
                2,
            ),
        )
