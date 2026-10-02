from enum import Enum

from pydantic import BaseModel, Field


class BidDecision(str, Enum):
    BID = "bid"
    EXECUTIVE_REVIEW = "executive_review"
    NO_BID = "no_bid"


class DecisionFactor(BaseModel):
    name: str = Field(
        min_length=1,
        description="Name of the decision factor.",
    )

    score: float = Field(
        ge=0,
        le=100,
        description="Normalized factor score from 0 to 100.",
    )

    weight: float = Field(
        gt=0,
        le=1,
        description="Weight assigned to the factor.",
    )

    rationale: str = Field(
        min_length=1,
        description="Explanation supporting the factor score.",
    )


class DecisionResult(BaseModel):
    decision: BidDecision

    overall_score: float = Field(
        ge=0,
        le=100,
    )

    compliance_score: float = Field(
        ge=0,
        le=100,
    )

    capability_score: float = Field(
        ge=0,
        le=100,
    )

    experience_score: float = Field(
        ge=0,
        le=100,
    )

    resource_score: float = Field(
        ge=0,
        le=100,
    )

    risk_score: float = Field(
        ge=0,
        le=100,
    )

    historical_relevance_score: float = Field(
        ge=0,
        le=100,
        default=0,
        description=(
            "Score representing the relevance of previous "
            "successful proposals to the current opportunity."
        ),
    )

    win_probability_score: float = Field(
        ge=0,
        le=100,
        default=0,
        description=(
            "Evidence-based win-probability score from 0 to 100. "
            "This is a decision-support score and is not a "
            "statistically calibrated probability."
        ),
    )

    matched_historical_proposals: list[str] = Field(
        default_factory=list,
        description="IDs of relevant previous successful proposals.",
    )

    mandatory_gaps: list[str] = Field(
        default_factory=list,
    )

    partial_requirements: list[str] = Field(
        default_factory=list,
    )

    factors: list[DecisionFactor] = Field(
        default_factory=list,
    )

    rationale: str = Field(
        min_length=1,
    )
