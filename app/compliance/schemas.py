from enum import Enum

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Possible compliance outcomes for an RFP requirement."""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    GAP = "gap"
    UNKNOWN = "unknown"


class CompanyCapability(BaseModel):
    """A documented capability belonging to a company."""

    capability_id: str = Field(
        min_length=1,
        description="Unique capability identifier.",
    )

    name: str = Field(
        min_length=1,
        description="Capability name.",
    )

    description: str = Field(
        min_length=1,
        description="Description of the capability.",
    )

    categories: list[str] = Field(
        default_factory=list,
        description="Capability categories.",
    )

    evidence: str = Field(
        min_length=1,
        description="Documented evidence supporting the capability.",
    )


class CapabilityProfile(BaseModel):
    """Company capability profile used for compliance analysis."""

    company_name: str = Field(
        min_length=1,
        description="Company name.",
    )

    company_type: str = Field(
        min_length=1,
        description="Type of organization.",
    )

    description: str = Field(
        min_length=1,
        description="Company capability profile description.",
    )

    capabilities: list[CompanyCapability] = Field(
        default_factory=list,
        description="Documented company capabilities.",
    )


class ComplianceResult(BaseModel):
    """Compliance assessment for one RFP requirement."""

    requirement_id: str = Field(
        min_length=1,
        description="RFP requirement identifier.",
    )

    status: ComplianceStatus = Field(
        description="Compliance status.",
    )

    matched_capability_ids: list[str] = Field(
        default_factory=list,
        description="Capabilities supporting the assessment.",
    )

    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting the compliance assessment.",
    )

    rationale: str = Field(
        min_length=1,
        description="Explanation of the compliance assessment.",
    )


class ComplianceMatrix(BaseModel):
    """Complete compliance matrix for an RFP."""

    company_name: str = Field(
        min_length=1,
        description="Company being assessed.",
    )

    total_requirements: int = Field(
        ge=0,
        description="Total number of RFP requirements assessed.",
    )

    compliant_count: int = Field(
        ge=0,
        description="Number of compliant requirements.",
    )

    partial_count: int = Field(
        ge=0,
        description="Number of partially compliant requirements.",
    )

    gap_count: int = Field(
        ge=0,
        description="Number of requirement gaps.",
    )

    unknown_count: int = Field(
        ge=0,
        description="Number of requirements with unknown compliance.",
    )

    results: list[ComplianceResult] = Field(
        default_factory=list,
        description="Requirement-level compliance results.",
    )
