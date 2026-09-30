import json

import pytest

from app.decision.schemas import BidDecision
from app.proposals.workspace_initializer import (
    ProposalWorkspaceError,
    ProposalWorkspaceInitializer,
)


def test_creates_bid_workspace(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    result = initializer.initialize(
        opportunity_id="RFP-2026-001",
        decision=BidDecision.BID,
        decision_score=82.5,
        win_probability_score=76.4,
        matched_historical_proposals=[
            "PROP-001",
            "PROP-003",
        ],
    )

    workspace = tmp_path / "proposal_workspaces" / "RFP-2026-001"

    assert result["workspace_id"] == "RFP-2026-001"
    assert result["workspace_status"] == "initialized"
    assert result["decision"] == "bid"
    assert result["decision_score"] == 82.5
    assert result["win_probability_score"] == 76.4

    assert workspace.exists()
    assert (workspace / "README.md").exists()
    assert (workspace / "decision.json").exists()

    for directory in initializer.WORKSPACE_DIRECTORIES:
        assert (workspace / directory).is_dir()


def test_writes_decision_metadata(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    initializer.initialize(
        opportunity_id="RFP-2026-002",
        decision="bid",
        decision_score=88,
        win_probability_score=81.5,
        matched_historical_proposals=["PROP-001"],
    )

    metadata_path = (
        tmp_path
        / "proposal_workspaces"
        / "RFP-2026-002"
        / "decision.json"
    )

    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    assert metadata["opportunity_id"] == "RFP-2026-002"
    assert metadata["decision"] == "bid"
    assert metadata["decision_score"] == 88
    assert metadata["win_probability_score"] == 81.5
    assert metadata["matched_historical_proposals"] == ["PROP-001"]
    assert metadata["workspace_status"] == "initialized"
    assert metadata["created_at"]


@pytest.mark.parametrize(
    "decision",
    [
        BidDecision.EXECUTIVE_REVIEW,
        BidDecision.NO_BID,
    ],
)
def test_rejects_non_bid_decisions(tmp_path, decision):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    with pytest.raises(
        ProposalWorkspaceError,
        match="requires a BID decision",
    ):
        initializer.initialize(
            opportunity_id="RFP-2026-003",
            decision=decision,
            decision_score=70,
        )

    assert not (
        tmp_path
        / "proposal_workspaces"
        / "RFP-2026-003"
    ).exists()


def test_rejects_invalid_decision_score(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    with pytest.raises(
        ProposalWorkspaceError,
        match="decision_score must be between 0 and 100",
    ):
        initializer.initialize(
            opportunity_id="RFP-2026-004",
            decision=BidDecision.BID,
            decision_score=101,
        )


def test_rejects_invalid_win_probability_score(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    with pytest.raises(
        ProposalWorkspaceError,
        match="win_probability_score must be between 0 and 100",
    ):
        initializer.initialize(
            opportunity_id="RFP-2026-005",
            decision=BidDecision.BID,
            decision_score=85,
            win_probability_score=-1,
        )


def test_rejects_empty_opportunity_id(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    with pytest.raises(
        ProposalWorkspaceError,
        match="opportunity_id must not be empty",
    ):
        initializer.initialize(
            opportunity_id="   ",
            decision=BidDecision.BID,
            decision_score=85,
        )


def test_workspace_initialization_is_idempotent(tmp_path):
    initializer = ProposalWorkspaceInitializer(
        root_path=tmp_path / "proposal_workspaces"
    )

    first = initializer.initialize(
        opportunity_id="RFP-2026-006",
        decision=BidDecision.BID,
        decision_score=84,
        win_probability_score=79,
    )

    second = initializer.initialize(
        opportunity_id="RFP-2026-006",
        decision=BidDecision.BID,
        decision_score=84,
        win_probability_score=79,
    )

    assert first["workspace_path"] == second["workspace_path"]

    workspace = (
        tmp_path
        / "proposal_workspaces"
        / "RFP-2026-006"
    )

    assert workspace.exists()
    assert (workspace / "decision.json").exists()
    assert (workspace / "README.md").exists()
