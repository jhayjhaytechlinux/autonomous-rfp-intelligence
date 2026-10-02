from dataclasses import dataclass

from app.compliance.schemas import ComplianceMatrix
from app.proposals.schemas import PastProposal


@dataclass(frozen=True)
class ProposalRelevanceResult:
    matched_proposal_ids: list[str]
    matched_capability_ids: list[str]
    relevance_score: float


class ProposalRelevanceAnalyzer:
    """
    Evaluates how strongly previous successful proposals relate to
    the current RFP using authoritative capability matches from the
    ComplianceMatrix.

    Architecture:

        RFP Requirements
              ↓
        Compliance Engine
              ↓
        Matched Capability IDs
              ↓
        Historical Proposal Relevance
              ↓
        Historical Relevance Score
    """

    def analyze(
        self,
        compliance_matrix: ComplianceMatrix,
        proposals: list[PastProposal],
    ) -> ProposalRelevanceResult:
        """
        Compare the capability IDs matched to the current RFP against
        capability IDs represented in previous successful proposals.

        The compliance matrix is the authoritative source for the
        current opportunity's matched capability IDs.
        """

        if not compliance_matrix.results:
            return ProposalRelevanceResult(
                matched_proposal_ids=[],
                matched_capability_ids=[],
                relevance_score=0.0,
            )

        if not proposals:
            return ProposalRelevanceResult(
                matched_proposal_ids=[],
                matched_capability_ids=[],
                relevance_score=0.0,
            )

        required_capability_ids = self._extract_matched_capability_ids(
            compliance_matrix
        )

        if not required_capability_ids:
            return ProposalRelevanceResult(
                matched_proposal_ids=[],
                matched_capability_ids=[],
                relevance_score=0.0,
            )

        matched_proposals: list[str] = []
        matched_capability_ids: set[str] = set()

        for proposal in proposals:
            proposal_capabilities = set(proposal.capability_ids)

            overlap = required_capability_ids.intersection(
                proposal_capabilities
            )

            if overlap:
                matched_proposals.append(proposal.proposal_id)
                matched_capability_ids.update(overlap)

        relevance_score = (
            len(matched_capability_ids)
            / len(required_capability_ids)
        ) * 100

        return ProposalRelevanceResult(
            matched_proposal_ids=matched_proposals,
            matched_capability_ids=sorted(matched_capability_ids),
            relevance_score=round(relevance_score, 2),
        )

    @staticmethod
    def _extract_matched_capability_ids(
        compliance_matrix: ComplianceMatrix,
    ) -> set[str]:
        """
        Extract the authoritative capability IDs matched by the
        compliance engine.

        Only documented capability matches are considered.
        """

        capability_ids: set[str] = set()

        for result in compliance_matrix.results:
            capability_ids.update(
                result.matched_capability_ids
            )

        return capability_ids
