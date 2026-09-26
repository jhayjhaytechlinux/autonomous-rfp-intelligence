from enum import Enum

from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    """Categories used to classify RFP requirements."""

    TECHNICAL = "technical"
    EXPERIENCE = "experience"
    PERSONNEL = "personnel"
    COMMERCIAL = "commercial"
    IMPLEMENTATION = "implementation"
    TRAINING = "training"
    LEGAL = "legal"
    SUBMISSION = "submission"
    OTHER = "other"


class Requirement(BaseModel):
    """Represents one structured requirement extracted from an RFP."""

    requirement_id: str = Field(
        description="Unique identifier for the requirement."
    )

    category: RequirementCategory = Field(
        description="Category of the RFP requirement."
    )

    description: str = Field(
        min_length=1,
        description="Clear description of what the bidder is required to provide or demonstrate."
    )

    mandatory: bool = Field(
        description="Whether the requirement is mandatory."
    )

    source_section: str = Field(
        min_length=1,
        description="RFP section where the requirement was identified."
    )

    evidence: str = Field(
        min_length=1,
        description="Relevant text from the RFP supporting the extracted requirement."
    )


class RequirementExtractionResult(BaseModel):
    """Complete result returned by the requirement extraction process."""

    requirements: list[Requirement] = Field(
        default_factory=list,
        description="List of requirements extracted from the RFP."
    )

    total_requirements: int = Field(
        default=0,
        ge=0,
        description="Total number of extracted requirements."
    )
