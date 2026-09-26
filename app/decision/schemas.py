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
    decision: BidDecision = Field(
        description="Final bid/no-bid decision.",
    )

    overall_score: float = Field(
        ge=0,
        le=100,
        description="Overall weighted decision score.",
    )

    compliance_score: float = Field(
        ge=0,
        le=100,
        description="Compliance score.",
    )

    capability_score: float = Field(
        ge=0,
        le=100,
        description="Capability fit score.",
    )

    experience_score: float = Field(
        ge=0,
        le=100,
        description="Experience fit score.",
    )

    resource_score: float = Field(
        ge=0,
        le=100,
        description="Resource availability score.",
    )

    risk_score: float = Field(
        ge=0,
        le=100,
        description="Risk score where higher means lower risk.",
    )

    mandatory_gaps: list[str] = Field(
        default_factory=list,
        description="Mandatory requirements without sufficient evidence.",
    )

    partial_requirements: list[str] = Field(
        default_factory=list,
        description="Requirements assessed as partially compliant.",
    )

    factors: list[DecisionFactor] = Field(
        default_factory=list,
        description="Detailed decision factors.",
    )

    rationale: str = Field(
        min_length=1,
        description="Overall explanation of the decision.",
    )
