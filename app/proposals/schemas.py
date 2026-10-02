from pydantic import BaseModel, Field


class PastProposal(BaseModel):
    proposal_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    services: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    outcome: str = Field(min_length=1)
    relevance_evidence: str = Field(min_length=1)


class PastProposalDataset(BaseModel):
    dataset_name: str = Field(min_length=1)
    dataset_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    proposals: list[PastProposal] = Field(default_factory=list)
