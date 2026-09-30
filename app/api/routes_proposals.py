from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.proposals.workspace_initializer import (
    ProposalWorkspaceError,
    ProposalWorkspaceInitializer,
)


router = APIRouter(
    prefix="/api/proposals",
    tags=["proposals"],
)


class ProposalWorkspaceRequest(BaseModel):
    opportunity_id: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    decision_score: float = Field(ge=0, le=100)
    win_probability_score: float = Field(
        default=0,
        ge=0,
        le=100,
    )
    matched_historical_proposals: list[str] = Field(
        default_factory=list
    )
    company_name: str = Field(
        default="SecureOps Africa",
        min_length=1,
    )


@router.post("/workspace")
def initialize_proposal_workspace(
    request: ProposalWorkspaceRequest,
):
    """
    Initialize a proposal workspace after a positive BID decision.

    This endpoint is intended to be called by the automation layer,
    including the n8n workflow.
    """

    initializer = ProposalWorkspaceInitializer(
        root_path=Path("proposal_workspaces")
    )

    try:
        result = initializer.initialize(
            opportunity_id=request.opportunity_id,
            decision=request.decision,
            decision_score=request.decision_score,
            win_probability_score=request.win_probability_score,
            matched_historical_proposals=(
                request.matched_historical_proposals
            ),
            company_name=request.company_name,
        )

    except ProposalWorkspaceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "success",
        "message": "Proposal workspace initialized successfully.",
        "workspace": result,
    }
